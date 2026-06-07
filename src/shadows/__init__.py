"""Shadow Rendering Pipeline — translates machine events into human stories.

6 stages: Raw Event → Filter → Classify → Compress → Color → Render
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from enum import Enum

from ..core.types import CortexEvent, Operation, ShadowMode


class ShadowColor(str, Enum):
    GREEN = "green"      # high confidence, success
    YELLOW = "yellow"    # training, medium confidence
    RED = "red"          # anomaly, error, low confidence
    BLUE = "blue"        # information, memory, agent event
    MAGENTA = "magenta"  # Rust crate invocation
    PURPLE = "purple"    # dream cycle


class ShadowLayer(str, Enum):
    GLYPH = "glyph"          # reactive, one-line
    NARRATIVE = "narrative"  # compositional, multi-event
    PHILOSOPHICAL = "philosophical"  # cross-session patterns


@dataclass
class RenderedShadow:
    """A shadow ready for the TUI."""
    glyph: str           # emoji + one-liner
    story: str           # narrative version
    color: ShadowColor
    layer: ShadowLayer
    timestamp: float
    trace_id: str
    source: str
    raw_event: CortexEvent | None = None


# Glyph templates by operation
GLYPH_TEMPLATES: dict[str, tuple[str, str]] = {
    # (stream_template, story_template)
    Operation.EMBED: (
        "🧮 {dims}d embed → sim {score:.2f} ({ms}ms)",
        "🧮 Compressed \"{preview}\" into {dims} numbers — now any future question about {topic} will surface this",
    ),
    Operation.TRAIN: (
        "🏋️ {model} {epochs}ep, {before}%→{after}%",
        "🏋️ Learned for {epochs} rounds — got {before}% → {after}% right ({ms}ms). The model now knows {insight}.",
    ),
    Operation.PREDICT: (
        "🧠 predict: {label} (conf:{conf:.0%})",
        "🧠 Predicts: {label} ({conf:.0%} sure) based on {n} memories",
    ),
    Operation.REMEMBER: (
        "💾 remembered: \"{preview}\" [{agent}]",
        "📌 Remembered: \"{preview}\" — {count} things now known about {topic}",
    ),
    Operation.RECALL: (
        "🔍 recall: {n} results, top sim {score:.2f}",
        "🔍 Found {n} similar memories — closest: \"{preview}\" (sim: {score:.2f}). First stored {time_ago}.",
    ),
    Operation.ANALYZE: (
        "📊 {method} → {finding}",
        "📊 Analyzed with {method}: {finding}",
    ),
    Operation.QUERY: (
        "🔍 query: {n} results ({ms}ms)",
        "🔍 Searched for \"{query}\" — found {n} results in {ms}ms",
    ),
    Operation.TRANSFORM: (
        "🔄 {from_dims}→{to_dims} transform ({ms}ms)",
        "🔄 Transformed {from_dims}d → {to_dims}d representation ({ms}ms)",
    ),
    "anomaly": (
        "⚠️ anomaly: {detail} (σ={sigma:.1f})",
        "⚠️ Anomaly detected: {detail} is {sigma:.1f}σ from learned baseline. Last seen {time_ago}.",
    ),
    "dream": (
        "💭 dreaming: {activity}",
        "💭 The cortex is dreaming — revisiting \"{memory}\", finding \"{pattern}\"",
    ),
    "resonance": (
        "⚡ resonance: {agent_a} ↔ {agent_b}",
        "⚡ RESONANCE: {agent_a} learned \"{insight_a}\" → relevant to {agent_b}'s query about \"{query_b}\"",
    ),
    "agent_connect": (
        "📡 {name} joined ({lang}, {protocol})",
        "📡 Agent \"{name}\" joined the cortex ({lang}, {protocol}). Capabilities: {caps}.",
    ),
}


def classify_color(event: CortexEvent) -> ShadowColor:
    """Assign color based on event type and confidence."""
    etype = event.event_type
    if etype == "anomaly":
        return ShadowColor.RED
    if etype == "dream":
        return ShadowColor.PURPLE
    if etype in ("train",):
        return ShadowColor.YELLOW
    if etype in ("embed", "query", "recall", "remember", "agent_connect"):
        return ShadowColor.BLUE
    if etype == "predict":
        conf = event.confidence
        if conf >= 0.8:
            return ShadowColor.GREEN
        elif conf >= 0.4:
            return ShadowColor.YELLOW
        else:
            return ShadowColor.RED
    if etype == "analyze":
        return ShadowColor.MAGENTA
    return ShadowColor.BLUE


def render_shadow(event: CortexEvent) -> RenderedShadow:
    """Full pipeline: classify → compress → color → render."""
    templates = GLYPH_TEMPLATES.get(event.event_type, ("• {event_type}", "• {event_type}"))

    # Build context from payload + event metadata
    ctx = {
        "event_type": event.event_type,
        "source": event.source,
        "ms": event.payload.get("latency_ms", 0),
        "dims": event.payload.get("dims", 0),
        "score": event.payload.get("score", 0.0),
        "preview": event.payload.get("preview", "")[:40],
        "agent": event.source,
        "conf": event.confidence,
        "n": event.payload.get("n", 0),
        "count": event.payload.get("count", 0),
        "topic": event.payload.get("topic", ""),
        "time_ago": _format_time_ago(event.payload.get("age_seconds", 0)),
    }
    # Merge in remaining payload fields
    for k, v in event.payload.items():
        if k not in ctx:
            ctx[k] = v

    try:
        glyph = templates[0].format(**ctx)
    except (KeyError, IndexError):
        glyph = f"• {event.event_type} [{event.source}]"

    try:
        story = templates[1].format(**ctx)
    except (KeyError, IndexError):
        story = glyph

    return RenderedShadow(
        glyph=glyph,
        story=story,
        color=classify_color(event),
        layer=ShadowLayer.GLYPH,
        timestamp=event.timestamp,
        trace_id=event.trace_id,
        source=event.source,
        raw_event=event,
    )


def _format_time_ago(seconds: float) -> str:
    """Human-readable time ago."""
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{int(seconds // 60)}m ago"
    if seconds < 86400:
        return f"{int(seconds // 3600)}h ago"
    return f"{int(seconds // 86400)}d ago"
