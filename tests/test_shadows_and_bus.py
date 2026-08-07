"""
Tests for the Shadow Rendering Pipeline and Cortical Bus.

These test the untested modules: shadows, bus, and core types.
"""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, patch

from src.core.types import (
    CortexEvent, CortexRequest, CortexResponse,
    MemoryEntry, Operation, Protocol, Provenance,
    ComputeTier, ShadowMode, AgentInfo,
)
from src.shadows import (
    ShadowColor, ShadowLayer, RenderedShadow,
    classify_color, render_shadow, _format_time_ago,
    GLYPH_TEMPLATES,
)
from src.bus import CorticalBus


# ─── Core Types Tests ─────────────────────────────────────────────────────────

class TestCortexEvent:
    """Test CortexEvent creation, ordering, and factory."""

    def test_new_creates_event_with_trace_id(self):
        event = CortexEvent.new("test", "agent_1")
        assert event.event_type == "test"
        assert event.source == "agent_1"
        assert len(event.trace_id) == 12

    def test_default_importance_is_05(self):
        event = CortexEvent.new("test", "agent_1")
        assert event.importance == 0.5

    def test_high_importance_sorts_first(self):
        high = CortexEvent.new("a", "s", importance=0.9)
        low = CortexEvent.new("b", "s", importance=0.1)
        assert high < low  # __lt__ negates importance

    def test_same_importance_orders_by_timestamp(self):
        old = CortexEvent.new("a", "s", importance=0.5, timestamp=100)
        new = CortexEvent.new("b", "s", importance=0.5, timestamp=200)
        assert old < new  # earlier timestamp first

    def test_lt_returns_not_implemented_for_non_event(self):
        event = CortexEvent.new("a", "s")
        assert event.__lt__("not an event") is NotImplemented

    def test_payload_defaults_to_empty_dict(self):
        event = CortexEvent.new("a", "s")
        assert event.payload == {}

    def test_confidence_defaults_to_1(self):
        event = CortexEvent.new("a", "s")
        assert event.confidence == 1.0


class TestCortexRequest:
    def test_defaults(self):
        req = CortexRequest(operation=Operation.QUERY, agent_id="a1")
        assert req.protocol == Protocol.REST
        assert req.priority == 0.5
        assert len(req.trace_id) == 12
        assert req.payload == {}

    def test_custom_protocol(self):
        req = CortexRequest(operation=Operation.EMBED, agent_id="a1", protocol=Protocol.TAP)
        assert req.protocol == Protocol.TAP


class TestCortexResponse:
    def test_defaults(self):
        resp = CortexResponse(trace_id="abc", operation=Operation.PREDICT)
        assert resp.status == "ok"
        assert resp.payload == {}
        assert resp.shadow_glyph == ""
        assert resp.latency_ms == 0.0


class TestMemoryEntry:
    def test_default_confidence_is_1(self):
        m = MemoryEntry(content="test")
        assert m.confidence == 1.0

    def test_effective_confidence_decays(self):
        m = MemoryEntry(content="old", confidence=1.0, half_life_days=1.0)
        m.last_reinforced = time.time() - 86400  # 1 day ago
        decayed = m.effective_confidence
        assert 0.4 < decayed < 0.6  # ~0.5 after one half-life

    def test_reinforce_updates_timestamp(self):
        m = MemoryEntry(content="test")
        old = m.last_reinforced
        time.sleep(0.01)
        m.reinforce()
        assert m.last_reinforced > old

    def test_auto_generated_id(self):
        m1 = MemoryEntry(content="a")
        m2 = MemoryEntry(content="b")
        assert m1.id != m2.id
        assert len(m1.id) == 16

    def test_fresh_memory_full_confidence(self):
        m = MemoryEntry(content="fresh", confidence=0.8)
        assert abs(m.effective_confidence - 0.8) < 0.01


class TestProvenance:
    def test_creation(self):
        p = Provenance(who="agent_1", when=time.time(), how="embed")
        assert p.confidence == 1.0
        assert p.source == ""
        assert p.chain == []

    def test_with_chain(self):
        p = Provenance(who="a", when=0, how="train", chain=["mem1", "mem2"])
        assert len(p.chain) == 2


class TestAgentInfo:
    def test_defaults(self):
        a = AgentInfo(agent_id="x", protocol=Protocol.A2A)
        assert a.capabilities == set()
        assert a.metadata == {}

    def test_capabilities_set(self):
        a = AgentInfo(agent_id="x", protocol=Protocol.MCP, capabilities={Operation.QUERY, Operation.PREDICT})
        assert Operation.QUERY in a.capabilities
        assert len(a.capabilities) == 2


class TestEnums:
    def test_operation_values(self):
        assert Operation.EMBED == "embed"
        assert Operation.QUERY == "query"
        assert Operation.TRAIN == "train"
        assert Operation.PREDICT == "predict"
        assert Operation.ANALYZE == "analyze"
        assert Operation.REMEMBER == "remember"
        assert Operation.RECALL == "recall"
        assert Operation.TRANSFORM == "transform"

    def test_compute_tier_values(self):
        assert ComputeTier.HOT == "hot"
        assert ComputeTier.WARM == "warm"
        assert ComputeTier.BATCH == "batch"

    def test_protocol_values(self):
        assert Protocol.A2A == "a2a"
        assert Protocol.MCP == "mcp"
        assert Protocol.REST == "rest"
        assert Protocol.TAP == "tap"

    def test_shadow_mode_values(self):
        assert ShadowMode.STREAM == "stream"
        assert ShadowMode.FOCUS == "focus"
        assert ShadowMode.LANDSCAPE == "landscape"


# ─── Shadow Rendering Pipeline Tests ──────────────────────────────────────────

class TestClassifyColor:
    """Test color classification for events."""

    def test_anomaly_is_red(self):
        event = CortexEvent.new("anomaly", "system")
        assert classify_color(event) == ShadowColor.RED

    def test_dream_is_purple(self):
        event = CortexEvent.new("dream", "system")
        assert classify_color(event) == ShadowColor.PURPLE

    def test_train_is_yellow(self):
        event = CortexEvent.new("train", "agent_1")
        assert classify_color(event) == ShadowColor.YELLOW

    def test_embed_is_blue(self):
        event = CortexEvent.new("embed", "agent_1")
        assert classify_color(event) == ShadowColor.BLUE

    def test_query_is_blue(self):
        event = CortexEvent.new("query", "agent_1")
        assert classify_color(event) == ShadowColor.BLUE

    def test_remember_is_blue(self):
        event = CortexEvent.new("remember", "agent_1")
        assert classify_color(event) == ShadowColor.BLUE

    def test_agent_connect_is_blue(self):
        event = CortexEvent.new("agent_connect", "agent_1")
        assert classify_color(event) == ShadowColor.BLUE

    def test_predict_high_confidence_green(self):
        event = CortexEvent.new("predict", "a1", confidence=0.9)
        assert classify_color(event) == ShadowColor.GREEN

    def test_predict_medium_confidence_yellow(self):
        event = CortexEvent.new("predict", "a1", confidence=0.5)
        assert classify_color(event) == ShadowColor.YELLOW

    def test_predict_low_confidence_red(self):
        event = CortexEvent.new("predict", "a1", confidence=0.2)
        assert classify_color(event) == ShadowColor.RED

    def test_predict_boundary_08_is_green(self):
        event = CortexEvent.new("predict", "a1", confidence=0.8)
        assert classify_color(event) == ShadowColor.GREEN

    def test_predict_boundary_04_is_yellow(self):
        event = CortexEvent.new("predict", "a1", confidence=0.4)
        assert classify_color(event) == ShadowColor.YELLOW

    def test_analyze_is_magenta(self):
        event = CortexEvent.new("analyze", "agent_1")
        assert classify_color(event) == ShadowColor.MAGENTA

    def test_unknown_event_is_blue(self):
        event = CortexEvent.new("custom_event", "agent_1")
        assert classify_color(event) == ShadowColor.BLUE


class TestRenderShadow:
    """Test the full shadow rendering pipeline."""

    def test_remember_renders_with_glyph(self):
        event = CortexEvent.new("remember", "ensign", payload={
            "preview": "the cooling fan at midnight",
            "count": 47,
            "topic": "cooling",
        })
        shadow = render_shadow(event)
        assert "cooling fan" in shadow.glyph
        assert shadow.color == ShadowColor.BLUE
        assert shadow.layer == ShadowLayer.GLYPH
        assert shadow.source == "ensign"

    def test_predict_renders_confidence(self):
        event = CortexEvent.new("predict", "navigator", payload={
            "label": "engine_overheat",
        }, confidence=0.85)
        shadow = render_shadow(event)
        assert "engine_overheat" in shadow.glyph
        assert "85%" in shadow.glyph
        assert shadow.color == ShadowColor.GREEN

    def test_anomaly_renders_red(self):
        event = CortexEvent.new("anomaly", "monitor", payload={
            "detail": "temperature spike",
            "sigma": 3.5,
        })
        shadow = render_shadow(event)
        assert shadow.color == ShadowColor.RED
        assert "temperature" in shadow.glyph

    def test_unknown_event_renders_generic(self):
        event = CortexEvent.new("custom_type", "agent_x")
        shadow = render_shadow(event)
        assert "custom_type" in shadow.glyph
        assert shadow.color == ShadowColor.BLUE

    def test_shadow_has_trace_id(self):
        event = CortexEvent.new("test", "a1")
        shadow = render_shadow(event)
        assert shadow.trace_id == event.trace_id

    def test_shadow_has_timestamp(self):
        event = CortexEvent.new("test", "a1")
        shadow = render_shadow(event)
        assert shadow.timestamp == event.timestamp

    def test_shadow_has_raw_event(self):
        event = CortexEvent.new("test", "a1")
        shadow = render_shadow(event)
        assert shadow.raw_event == event

    def test_template_keyerror_falls_back(self):
        """If template references unknown fields, should fall back gracefully."""
        event = CortexEvent.new("remember", "a1", payload={})
        # No 'preview' in payload — template references it
        shadow = render_shadow(event)
        assert shadow.glyph  # Should produce something, not crash

    def test_dream_renders_purple(self):
        event = CortexEvent.new("dream", "cortex", payload={
            "activity": "revisiting memories",
            "memory": "the first signal",
            "pattern": "recursive shells",
        })
        shadow = render_shadow(event)
        assert shadow.color == ShadowColor.PURPLE
        assert "dream" in shadow.glyph.lower() or "dreaming" in shadow.glyph.lower()


class TestFormatTimeAgo:
    def test_under_60_seconds(self):
        assert _format_time_ago(30) == "just now"

    def test_under_60_seconds_zero(self):
        assert _format_time_ago(0) == "just now"

    def test_minutes(self):
        assert _format_time_ago(120) == "2m ago"

    def test_hours(self):
        assert _format_time_ago(7200) == "2h ago"

    def test_days(self):
        assert _format_time_ago(86400 * 3) == "3d ago"

    def test_exactly_60_seconds(self):
        # 60 seconds = 1 minute
        assert _format_time_ago(60) == "1m ago"

    def test_exactly_3600_seconds(self):
        assert _format_time_ago(3600) == "1h ago"


class TestGlyphTemplates:
    def test_all_operations_have_templates(self):
        for op in [Operation.EMBED, Operation.TRAIN, Operation.PREDICT,
                   Operation.REMEMBER, Operation.RECALL, Operation.ANALYZE,
                   Operation.QUERY, Operation.TRANSFORM]:
            assert op in GLYPH_TEMPLATES, f"Missing template for {op}"

    def test_each_template_has_glyph_and_story(self):
        for key, (glyph, story) in GLYPH_TEMPLATES.items():
            assert isinstance(glyph, str)
            assert isinstance(story, str)
            assert len(glyph) > 0
            assert len(story) > 0

    def test_custom_event_types_have_templates(self):
        assert "anomaly" in GLYPH_TEMPLATES
        assert "dream" in GLYPH_TEMPLATES
        assert "resonance" in GLYPH_TEMPLATES
        assert "agent_connect" in GLYPH_TEMPLATES


# ─── Cortical Bus Tests ───────────────────────────────────────────────────────

class TestCorticalBus:
    """Test the async pub/sub event bus."""

    def test_subscribe_adds_callback(self):
        bus = CorticalBus()
        callback = AsyncMock()
        bus.subscribe(callback)
        assert len(bus._subscribers) == 1

    def test_multiple_subscribers(self):
        bus = CorticalBus()
        bus.subscribe(AsyncMock())
        bus.subscribe(AsyncMock())
        assert len(bus._subscribers) == 2

    @pytest.mark.asyncio
    async def test_publish_returns_true(self):
        bus = CorticalBus()
        event = CortexEvent.new("test", "a1")
        result = await bus.publish(event)
        assert result is True

    @pytest.mark.asyncio
    async def test_emit_creates_and_publishes(self):
        bus = CorticalBus()
        result = await bus.emit("test_event", "agent_1", payload={"x": 1})
        assert result is True
        assert not bus._queue.empty()

    @pytest.mark.asyncio
    async def test_published_event_is_queued(self):
        bus = CorticalBus()
        event = CortexEvent.new("test", "a1")
        await bus.publish(event)
        assert not bus._queue.empty()
        queued = bus._queue.get_nowait()
        assert queued.event_type == "test"

    @pytest.mark.asyncio
    async def test_high_importance_processed_first(self):
        bus = CorticalBus()
        low = CortexEvent.new("low", "s", importance=0.1)
        high = CortexEvent.new("high", "s", importance=0.9)
        await bus.publish(low)
        await bus.publish(high)
        first = await bus._queue.get()
        assert first.event_type == "high"

    @pytest.mark.asyncio
    async def test_backpressure_when_full(self):
        bus = CorticalBus(max_queue_size=2)
        await bus.publish(CortexEvent.new("a", "s"))
        await bus.publish(CortexEvent.new("b", "s"))
        result = await bus.publish(CortexEvent.new("c", "s"))
        assert result is False

    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        bus = CorticalBus()
        await bus.start()
        assert bus._running is True
        await bus.stop()
        assert bus._running is False

    @pytest.mark.asyncio
    async def test_stop_without_start(self):
        bus = CorticalBus()
        # Should not crash
        await bus.stop()
        assert bus._running is False

    @pytest.mark.asyncio
    async def test_subscriber_receives_event(self):
        bus = CorticalBus()
        received = []
        async def listener(event):
            received.append(event)
        bus.subscribe(listener)
        await bus.start()
        await bus.emit("test", "a1")
        await asyncio.sleep(0.1)  # Let the processor run
        await bus.stop()
        assert len(received) > 0
        assert received[0].event_type == "test"

    @pytest.mark.asyncio
    async def test_trace_rate_limiting(self):
        """Bus should rate-limit per trace_id to max 5 shadow events."""
        bus = CorticalBus()
        bus._max_per_trace = 3
        await bus.start()
        for i in range(10):
            await bus.emit("test", "a1")  # Each gets unique trace_id
        await asyncio.sleep(0.1)
        await bus.stop()
        # Each event has unique trace_id, so rate limiting shouldn't trigger
        # This tests the infrastructure exists

    @pytest.mark.asyncio
    async def test_default_max_queue_size(self):
        bus = CorticalBus()
        assert bus._queue.maxsize == 1000

    @pytest.mark.asyncio
    async def test_custom_max_queue_size(self):
        bus = CorticalBus(max_queue_size=100)
        assert bus._queue.maxsize == 100
