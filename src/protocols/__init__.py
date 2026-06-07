"""FastAPI server — REST + TAP protocol endpoints."""

from __future__ import annotations

import time
import uuid
import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Query as QueryParam
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..core.types import CortexRequest, CortexResponse, Operation, Protocol
from ..bus import CorticalBus
from ..compute import ComputeEngine
from ..memory import MemoryLayer
from ..shadows import render_shadow

logger = logging.getLogger(__name__)


# --- Request/Response models ---

class EmbedRequest(BaseModel):
    content: str
    dims: int = 384
    agent_id: str = "api"


class RememberRequest(BaseModel):
    content: str
    agent_id: str = "api"
    tags: list[str] = []


class RecallRequest(BaseModel):
    query: str
    top_k: int = 5
    agent_id: str = "api"


class PredictRequest(BaseModel):
    input: list[float]
    model: str = "default"
    agent_id: str = "api"


class TrainRequest(BaseModel):
    model: str = "default"
    epochs: int = 100
    input_dim: int = 384
    hidden_dim: int = 64
    output_dim: int = 12
    agent_id: str = "api"


class TapSenseRequest(BaseModel):
    data: str  # "t:28.5 h:62 z:3"


def create_app(bus: CorticalBus, compute: ComputeEngine, memory: MemoryLayer) -> FastAPI:
    """Create the FastAPI app with all routes."""
    app = FastAPI(title="Exocortex", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Core REST endpoints ---

    @app.post("/api/v1/embed")
    async def embed(req: EmbedRequest) -> dict[str, Any]:
        start = time.time()
        result = await compute.execute(Operation.EMBED, {
            "content": req.content, "dims": req.dims,
        })
        embedding = result.get("embedding", [])

        # Remember the embedded content
        entry = await memory.remember(
            content=req.content,
            embedding=embedding,
            agent_id=req.agent_id,
            tags=["embedded"],
        )

        # Emit event
        await bus.emit("embed", req.agent_id,
            payload={**result, "preview": req.content[:40], "dims": req.dims},
            trace_id=entry.id[:12],
        )

        return {"id": entry.id, "dims": len(embedding), "latency_ms": result["latency_ms"]}

    @app.post("/api/v1/remember")
    async def remember(req: RememberRequest) -> dict[str, Any]:
        # Auto-embed then store
        result = await compute.execute(Operation.EMBED, {"content": req.content, "dims": 384})
        embedding = result.get("embedding", [])

        entry = await memory.remember(
            content=req.content,
            embedding=embedding,
            agent_id=req.agent_id,
            tags=req.tags,
        )

        await bus.emit("remember", req.agent_id,
            payload={"preview": req.content[:40], "count": memory.stats["total"], "topic": req.tags[0] if req.tags else ""},
            trace_id=entry.id[:12],
        )

        return {"id": entry.id, "status": "remembered"}

    @app.post("/api/v1/recall")
    async def recall(req: RecallRequest) -> dict[str, Any]:
        # Embed the query
        result = await compute.execute(Operation.EMBED, {"content": req.query, "dims": 384})
        query_emb = result.get("embedding", [])

        results = await memory.recall(query_emb, top_k=req.top_k)
        memories = [
            {"id": e.id, "content": e.content[:100], "similarity": round(s, 3), "confidence": round(e.effective_confidence, 3)}
            for e, s in results
        ]

        await bus.emit("recall", req.agent_id,
            payload={"n": len(memories), "score": results[0][1] if results else 0, "preview": results[0][0].content[:40] if results else ""},
        )

        return {"results": memories, "n": len(memories)}

    @app.post("/api/v1/predict")
    async def predict(req: PredictRequest) -> dict[str, Any]:
        result = await compute.execute(Operation.PREDICT, {
            "input": req.input, "model": req.model,
        })
        await bus.emit("predict", req.agent_id,
            payload=result,
            confidence=result.get("confidence", 0),
        )
        return result

    @app.post("/api/v1/train")
    async def train(req: TrainRequest) -> dict[str, Any]:
        result = await compute.execute(Operation.TRAIN, {
            "model": req.model, "epochs": req.epochs,
            "input_dim": req.input_dim, "hidden_dim": req.hidden_dim,
            "output_dim": req.output_dim,
        })
        await bus.emit("train", req.agent_id, payload=result)
        return result

    @app.get("/api/v1/query")
    async def query(tags: str = QueryParam(""), top_k: int = 10) -> dict[str, Any]:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        results = await memory.query(tag_list, top_k=top_k)
        return {
            "results": [{"id": e.id, "content": e.content[:100], "confidence": round(e.effective_confidence, 3)} for e in results],
            "n": len(results),
        }

    @app.get("/api/v1/capabilities")
    async def capabilities() -> dict[str, Any]:
        return {
            "operations": [op.value for op in Operation],
            "protocols": ["rest", "a2a", "mcp", "tap"],
            "compute_tiers": ["hot", "warm", "batch"],
            "memory_tiers": ["hot", "warm", "cold"],
        }

    @app.get("/api/v1/stats")
    async def stats() -> dict[str, Any]:
        return {
            "memory": memory.stats,
            "compute": compute.stats,
        }

    # --- TAP: Tiny Agent Protocol (ESP32-friendly) ---

    @app.get("/tap/recall")
    async def tap_recall(q: str = QueryParam("")) -> str:
        """Plain text recall for microcontrollers. Response ≤200 bytes."""
        result = await compute.execute(Operation.EMBED, {"content": q, "dims": 384})
        query_emb = result.get("embedding", [])
        results = await memory.recall(query_emb, top_k=1)

        if not results:
            return f"no memories matching: {q}"

        entry, sim = results[0]
        response = f"{entry.content[:120]} (sim: {sim:.2f}, conf: {entry.effective_confidence:.2f})"
        return response[:200]  # Hard limit for ESP32

    @app.post("/tap/remember")
    async def tap_remember(req: RememberRequest) -> str:
        """Plain text remember."""
        result = await compute.execute(Operation.EMBED, {"content": req.content, "dims": 384})
        embedding = result.get("embedding", [])
        entry = await memory.remember(req.content, embedding, req.agent_id, req.tags)
        await bus.emit("remember", req.agent_id, payload={"preview": req.content[:40]})
        return "remembered"

    @app.get("/tap/predict")
    async def tap_predict(sensor: str = QueryParam(""), reading: str = QueryParam("")) -> str:
        """Plain text predict for microcontrollers."""
        try:
            value = float(reading)
        except ValueError:
            return "error: reading must be a number"

        # Reflex check
        anomaly = await compute.reflex_check(sensor, value)
        if anomaly:
            await bus.emit("anomaly", "reflex",
                payload=anomaly,
                importance=0.9,
                confidence=0.95,
            )
            return f"anomaly: {anomaly['detail']} ({anomaly['sigma']:.1f}σ)"

        return f"{sensor}: {value} (normal)"

    @app.post("/tap/sense")
    async def tap_sense(req: TapSenseRequest) -> str:
        """Log sensor reading. Plain text in/out."""
        # Parse simple key:value format: "t:28.5 h:62 z:3"
        readings = {}
        for part in req.data.split():
            if ":" in part:
                k, v = part.split(":", 1)
                try:
                    readings[k] = float(v)
                except ValueError:
                    readings[k] = v

        # Reflex check on numeric values
        for key, val in readings.items():
            if isinstance(val, float):
                anomaly = await compute.reflex_check(key, val)
                if anomaly:
                    await bus.emit("anomaly", "reflex", payload=anomaly, importance=0.9)

        await memory.remember(
            content=req.data,
            embedding=[0.0] * 384,  # placeholder embedding
            agent_id="tap",
            tags=["sensor"] + list(readings.keys()),
        )

        return "logged"

    return app
