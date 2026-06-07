"""Core types and data models for the exocortex."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Operation(str, Enum):
    """The 8 canonical operations every cortex speaks."""
    EMBED = "embed"
    QUERY = "query"
    TRAIN = "train"
    PREDICT = "predict"
    ANALYZE = "analyze"
    REMEMBER = "remember"
    RECALL = "recall"
    TRANSFORM = "transform"


class ComputeTier(str, Enum):
    """Tiered compute — hot/warm/batch."""
    HOT = "hot"       # <5ms, sync, in-memory
    WARM = "warm"     # 5-500ms, Rust FFI / small model
    BATCH = "batch"   # >500ms, asyncio.to_thread


class Protocol(str, Enum):
    """Supported protocols."""
    A2A = "a2a"
    MCP = "mcp"
    REST = "rest"
    TAP = "tap"


class ShadowMode(str, Enum):
    """TUI rendering modes."""
    STREAM = "stream"     # "The River"
    FOCUS = "focus"       # "The Microscope"
    LANDSCAPE = "landscape"  # "The Map"


@dataclass
class Provenance:
    """Who/when/how for every memory. The 'nutrition label' for AI decisions."""
    who: str              # agent_id
    when: float           # unix timestamp
    how: str              # operation that created this
    confidence: float = 1.0
    source: str = ""
    chain: list[str] = field(default_factory=list)  # parent memory IDs


@dataclass
class CortexEvent:
    """Typed event on the Cortical Bus."""
    event_type: str           # operation name or "anomaly", "dream", "resonance"
    source: str               # agent_id or "system"
    trace_id: str             # links request → compute → memory → shadow
    timestamp: float = field(default_factory=time.time)
    payload: dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5   # 0-1, for priority queue
    novelty: float = 0.5      # 0-1, how new/unusual
    confidence: float = 1.0   # 0-1, model certainty
    provenance: Provenance | None = None

    def __lt__(self, other: CortexEvent) -> bool:
        """PriorityQueue needs ordering. Higher importance = higher priority."""
        if not isinstance(other, CortexEvent):
            return NotImplemented
        # Negate importance so high importance sorts first (min-heap)
        return (-self.importance, self.timestamp) < (-other.importance, other.timestamp)

    @staticmethod
    def new(event_type: str, source: str, **kwargs: Any) -> CortexEvent:
        return CortexEvent(
            event_type=event_type,
            source=source,
            trace_id=uuid.uuid4().hex[:12],
            **kwargs,
        )


@dataclass
class CortexRequest:
    """Canonical request format — all protocols normalize to this."""
    operation: Operation
    agent_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    protocol: Protocol = Protocol.REST
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    priority: float = 0.5    # 0=low, 1=critical


@dataclass
class CortexResponse:
    """Canonical response."""
    trace_id: str
    operation: Operation
    status: str = "ok"       # ok | error | partial
    payload: dict[str, Any] = field(default_factory=dict)
    shadow_glyph: str = ""   # rendered one-liner for TUI
    latency_ms: float = 0.0


@dataclass
class MemoryEntry:
    """A single memory in the cortex."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    content: str = ""
    embedding: list[float] = field(default_factory=list)
    agent_id: str = ""
    confidence: float = 1.0
    created_at: float = field(default_factory=time.time)
    last_reinforced: float = field(default_factory=time.time)
    half_life_days: float = 30.0
    provenance: Provenance | None = None
    tags: list[str] = field(default_factory=list)

    @property
    def effective_confidence(self) -> float:
        """Confidence after half-life decay."""
        import math
        age_days = (time.time() - self.last_reinforced) / 86400
        decay = math.exp(-0.693 * age_days / self.half_life_days)  # ln(2) ≈ 0.693
        return self.confidence * decay

    def reinforce(self) -> None:
        """Recall reinforces the memory (bumps last_reinforced)."""
        self.last_reinforced = time.time()


@dataclass
class AgentInfo:
    """Connected agent metadata."""
    agent_id: str
    protocol: Protocol
    capabilities: set[Operation] = field(default_factory=set)
    last_seen: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)
