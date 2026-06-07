"""Tests for the exocortex core."""

import asyncio
import math
import time

import pytest

from src.core.types import (
    CortexEvent, CortexRequest, Operation, ComputeTier,
    Protocol, MemoryEntry, AgentInfo, Provenance,
)
from src.bus import CorticalBus
from src.compute import ComputeEngine
from src.memory import MemoryLayer
from src.shadows import render_shadow, ShadowColor, classify_color
from src.config import CortexConfig


# --- Core Types ---

def test_operation_enum():
    assert len(Operation) == 8
    assert Operation.EMBED.value == "embed"


def test_cortex_event_new():
    event = CortexEvent.new("embed", "test-agent", payload={"dims": 384})
    assert event.event_type == "embed"
    assert event.source == "test-agent"
    assert len(event.trace_id) == 12


def test_memory_entry_half_life():
    entry = MemoryEntry(confidence=1.0, half_life_days=30.0)
    assert abs(entry.effective_confidence - 1.0) < 0.01

    # Age 30 days → confidence should be ~0.5
    entry.last_reinforced = time.time() - 30 * 86400
    assert 0.45 < entry.effective_confidence < 0.55


def test_memory_entry_reinforce():
    entry = MemoryEntry(half_life_days=1.0)
    entry.last_reinforced = time.time() - 86400  # 1 day old
    old_conf = entry.effective_confidence
    entry.reinforce()
    assert entry.effective_confidence > old_conf


def test_provenance():
    p = Provenance(who="agent-1", when=time.time(), how="embed", chain=["mem_abc"])
    assert p.who == "agent-1"
    assert len(p.chain) == 1


# --- Cortical Bus ---

@pytest.mark.asyncio
async def test_bus_publish_subscribe():
    bus = CorticalBus()
    received = []

    async def subscriber(event):
        received.append(event)

    bus.subscribe(subscriber)
    await bus.start()

    event = CortexEvent.new("test", "unit", payload={"key": "val"})
    await bus.publish(event)
    await asyncio.sleep(0.1)

    await bus.stop()
    assert len(received) == 1
    assert received[0].event_type == "test"


@pytest.mark.asyncio
async def test_bus_backpressure():
    bus = CorticalBus(max_queue_size=5)
    await bus.start()

    # Fill the queue
    for i in range(10):
        event = CortexEvent.new("test", "unit", importance=i / 10.0)
        await bus.publish(event)

    await bus.stop()


# --- Compute Engine ---

@pytest.mark.asyncio
async def test_embed():
    engine = ComputeEngine()
    result = await engine.execute(Operation.EMBED, {"dims": 384})
    assert len(result["embedding"]) == 384
    assert result["tier"] == "hot"


@pytest.mark.asyncio
async def test_train():
    engine = ComputeEngine()
    result = await engine.execute(Operation.TRAIN, {
        "model": "test-model", "epochs": 10,
    })
    assert result["trained"] is True
    assert result["tier"] == "batch"


@pytest.mark.asyncio
async def test_predict():
    engine = ComputeEngine()
    # Train first
    await engine.execute(Operation.TRAIN, {"model": "p", "epochs": 10})
    result = await engine.execute(Operation.PREDICT, {
        "model": "p", "input": [0.5] * 384,
    })
    assert "label" in result
    assert result["tier"] == "warm"


@pytest.mark.asyncio
async def test_reflex_arc():
    engine = ComputeEngine()
    # Feed baseline
    for v in [20.0, 21.0, 19.0, 20.5, 20.0, 21.0, 19.5, 20.0]:
        await engine.reflex_check("temp", v)

    # Anomaly
    anomaly = await engine.reflex_check("temp", 100.0)
    assert anomaly is not None
    assert anomaly["sigma"] > 3.0


# --- Memory Layer ---

@pytest.mark.asyncio
async def test_remember_and_recall():
    memory = MemoryLayer()
    emb = [0.1] * 384

    await memory.remember("hello world", emb, "test", ["test"])
    results = await memory.recall(emb, top_k=5)
    assert len(results) == 1
    assert results[0][0].content == "hello world"


@pytest.mark.asyncio
async def test_memory_cooling():
    memory = MemoryLayer()
    await memory.remember("old memory", [0.0] * 384, "test")

    # Force age it
    for entry in memory._warm.values():
        entry.last_reinforced = time.time() - 86400 * 2  # 2 days old

    stats = await memory.tick()
    assert stats["cooled_to_cold"] >= 1


@pytest.mark.asyncio
async def test_memory_query_by_tags():
    memory = MemoryLayer()
    await memory.remember("garden data", [0.1] * 384, "test", ["garden", "iot"])
    await memory.remember("dev data", [0.2] * 384, "test", ["devops"])

    results = await memory.query(["garden"])
    assert len(results) == 1
    assert results[0].content == "garden data"


# --- Shadow Rendering ---

def test_render_embed():
    event = CortexEvent.new("embed", "test", payload={
        "dims": 384, "score": 0.87, "latency_ms": 3.2, "preview": "hello",
    })
    shadow = render_shadow(event)
    assert "🧮" in shadow.glyph
    assert shadow.color == ShadowColor.BLUE


def test_render_anomaly():
    event = CortexEvent.new("anomaly", "reflex", payload={
        "detail": "fire!", "sigma": 4.1,
    })
    shadow = render_shadow(event)
    assert "⚠️" in shadow.glyph
    assert shadow.color == ShadowColor.RED


def test_render_train():
    event = CortexEvent.new("train", "agent", payload={
        "model": "test", "epochs": 100, "before": 80, "after": 92,
    })
    shadow = render_shadow(event)
    assert "🏋️" in shadow.glyph
    assert shadow.color == ShadowColor.YELLOW


def test_render_dream():
    event = CortexEvent.new("dream", "system", payload={
        "memory": "temp", "pattern": "cycle", "activity": "consolidation",
    })
    shadow = render_shadow(event)
    assert shadow.color == ShadowColor.PURPLE


def test_render_predict_high_conf():
    event = CortexEvent.new("predict", "agent",
        payload={"label": "yes"},
        confidence=0.92,
    )
    shadow = render_shadow(event)
    assert shadow.color == ShadowColor.GREEN


def test_render_predict_low_conf():
    event = CortexEvent.new("predict", "agent",
        payload={"label": "maybe"},
        confidence=0.2,
    )
    shadow = render_shadow(event)
    assert shadow.color == ShadowColor.RED


# --- Config ---

def test_config_defaults():
    config = CortexConfig()
    assert config.name == "default-cortex"
    assert config.port == 9000
    assert config.embedding_dims == 384


def test_config_load_file():
    import pathlib
    config = CortexConfig.load(pathlib.Path(__file__).parent.parent / ".cortex.toml")
    assert config.name == "demo-cortex"
