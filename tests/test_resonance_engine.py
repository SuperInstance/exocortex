"""Tests for Resonance Engine — cross-agent knowledge overlap detection.

Tests learning/query tracking, resonance detection at various thresholds,
pruning, stats, and bus emission.
"""

import math
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.resonance import (
    ActiveQuery,
    LearningEvent,
    ResonanceEngine,
    ResonanceHit,
    LEARNING_TTL_SECONDS,
    MAX_LEARNING_PER_AGENT,
    MAX_QUERIES_PER_AGENT,
    RESONANCE_THRESHOLD,
    _cosine_similarity,
)
from src.core.types import CortexEvent


# ─── Helpers ───────────────────────────────────────────────────────

def make_embedding(seed=0, dim=10):
    """Create a unit vector for testing."""
    vec = [0.0] * dim
    vec[seed % dim] = 1.0
    return vec


def similar_embedding(base_seed=0, dim=10, noise=0.01):
    """Create an embedding very similar to make_embedding(base_seed)."""
    vec = [0.0] * dim
    vec[base_seed % dim] = 1.0 - noise * (dim - 1)
    for i in range(dim):
        if i != base_seed % dim:
            vec[i] = noise
    return vec


class FakeBus:
    def __init__(self):
        self.published = []

    async def publish(self, event):
        self.published.append(event)


# ─── Utility function tests ────────────────────────────────────────

class TestCosineSimilarity:
    def test_identical_vectors(self):
        assert _cosine_similarity([1, 2, 3], [1, 2, 3]) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        assert _cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        assert _cosine_similarity([1, 0], [-1, 0]) == pytest.approx(-1.0)

    def test_empty_vector_a(self):
        assert _cosine_similarity([], [1, 2]) == 0.0

    def test_empty_vector_b(self):
        assert _cosine_similarity([1, 2], []) == 0.0

    def test_different_lengths(self):
        # resonance engine returns 0.0 for length mismatch
        result = _cosine_similarity([1, 0, 0, 0], [1, 0])
        assert result == 0.0

    def test_zero_magnitude(self):
        assert _cosine_similarity([0, 0], [0, 0]) == 0.0


# ─── Constants tests ───────────────────────────────────────────────

class TestConstants:
    def test_threshold(self):
        assert RESONANCE_THRESHOLD == 0.8

    def test_max_learning(self):
        assert MAX_LEARNING_PER_AGENT == 50

    def test_max_queries(self):
        assert MAX_QUERIES_PER_AGENT == 20

    def test_learning_ttl(self):
        assert LEARNING_TTL_SECONDS == 3600.0


# ─── Dataclass tests ───────────────────────────────────────────────

class TestLearningEvent:
    def test_creation(self):
        event = LearningEvent(
            agent_id="agent-a",
            content="learned about fish",
            embedding=[1.0, 0.0],
            timestamp=time.time(),
        )
        assert event.agent_id == "agent-a"
        assert event.metadata == {}

    def test_with_metadata(self):
        event = LearningEvent(
            agent_id="agent-a",
            content="test",
            embedding=[1.0],
            timestamp=0.0,
            metadata={"source": "experiment"},
        )
        assert event.metadata["source"] == "experiment"


class TestActiveQuery:
    def test_creation(self):
        query = ActiveQuery(
            agent_id="agent-b",
            content="what is a fish?",
            embedding=[0.9, 0.1],
            timestamp=time.time(),
        )
        assert query.agent_id == "agent-b"
        assert query.metadata == {}


class TestResonanceHit:
    def test_creation(self):
        hit = ResonanceHit(
            source_agent="a",
            target_agent="b",
            learning_content="fish are animals",
            query_content="what are fish?",
            similarity=0.92,
        )
        assert hit.source_agent == "a"
        assert hit.target_agent == "b"
        assert hit.similarity == 0.92
        assert hit.timestamp > 0  # auto-set


# ─── ResonanceEngine tests ─────────────────────────────────────────

class TestResonanceEngineInit:
    def test_default_threshold(self):
        engine = ResonanceEngine()
        assert engine._threshold == RESONANCE_THRESHOLD

    def test_custom_threshold(self):
        engine = ResonanceEngine(threshold=0.5)
        assert engine._threshold == 0.5

    def test_with_bus(self):
        bus = FakeBus()
        engine = ResonanceEngine(bus=bus)
        assert engine._bus is bus

    def test_initial_stats(self):
        engine = ResonanceEngine()
        stats = engine.stats
        assert stats["learnings_tracked"] == 0
        assert stats["queries_tracked"] == 0
        assert stats["resonances_detected"] == 0
        assert stats["active_agents_learning"] == 0
        assert stats["active_agents_querying"] == 0
        assert stats["recent_resonances"] == 0


class TestRecordLearning:
    def test_basic_learning(self):
        engine = ResonanceEngine()
        hits = engine.record_learning("agent-a", "learned X", [1.0, 0.0])
        assert hits == []
        assert engine.stats["learnings_tracked"] == 1
        assert engine.stats["active_agents_learning"] == 1

    def test_learning_triggers_resonance(self):
        """Learning should trigger resonance if another agent has matching query."""
        engine = ResonanceEngine(threshold=0.5)
        # Agent B asks about fish
        engine.record_query("agent-b", "what are fish?", [1.0, 0.0, 0.0])
        # Agent A learns about fish — should resonate
        hits = engine.record_learning("agent-a", "fish are animals", [1.0, 0.0, 0.0])
        assert len(hits) == 1
        assert hits[0].source_agent == "agent-a"
        assert hits[0].target_agent == "agent-b"

    def test_no_self_resonance(self):
        """Agent learning should not resonate with own queries."""
        engine = ResonanceEngine(threshold=0.1)
        engine.record_query("agent-a", "query", [1.0, 0.0])
        hits = engine.record_learning("agent-a", "learning", [1.0, 0.0])
        assert hits == []

    def test_max_learning_trim(self):
        """Old learnings should be trimmed when max is exceeded."""
        engine = ResonanceEngine()
        for i in range(MAX_LEARNING_PER_AGENT + 10):
            engine.record_learning("agent-a", f"learn-{i}", [float(i)])
        # Should only keep last MAX_LEARNING_PER_AGENT
        assert len(engine._learnings["agent-a"]) == MAX_LEARNING_PER_AGENT

    def test_multiple_agents_learning(self):
        engine = ResonanceEngine()
        engine.record_learning("a", "x", [1.0])
        engine.record_learning("b", "y", [1.0])
        engine.record_learning("c", "z", [1.0])
        assert engine.stats["active_agents_learning"] == 3


class TestRecordQuery:
    def test_basic_query(self):
        engine = ResonanceEngine()
        hits = engine.record_query("agent-a", "what is X?", [1.0, 0.0])
        assert hits == []
        assert engine.stats["queries_tracked"] == 1

    def test_query_triggers_resonance(self):
        """Query should trigger resonance if another agent has matching learning."""
        engine = ResonanceEngine(threshold=0.5)
        engine.record_learning("agent-a", "fish live in water", [1.0, 0.0, 0.0])
        hits = engine.record_query("agent-b", "where do fish live?", [1.0, 0.0, 0.0])
        assert len(hits) == 1
        assert hits[0].source_agent == "agent-a"
        assert hits[0].target_agent == "agent-b"

    def test_no_self_resonance_query(self):
        engine = ResonanceEngine(threshold=0.1)
        engine.record_learning("agent-a", "x", [1.0, 0.0])
        hits = engine.record_query("agent-a", "x", [1.0, 0.0])
        assert hits == []

    def test_max_query_trim(self):
        engine = ResonanceEngine()
        for i in range(MAX_QUERIES_PER_AGENT + 5):
            engine.record_query("agent-a", f"q-{i}", [float(i)])
        assert len(engine._queries["agent-a"]) == MAX_QUERIES_PER_AGENT


class TestResonanceDetection:
    def test_high_similarity_resonates(self):
        engine = ResonanceEngine(threshold=0.8)
        emb = [1.0, 0.0, 0.0, 0.0]
        engine.record_query("b", "query", emb[:])
        hits = engine.record_learning("a", "learning", emb[:])
        assert len(hits) == 1
        assert hits[0].similarity == pytest.approx(1.0)

    def test_below_threshold_no_resonance(self):
        engine = ResonanceEngine(threshold=0.95)
        engine.record_query("b", "query", [1.0, 0.0])
        hits = engine.record_learning("a", "learning", [0.0, 1.0])
        assert hits == []

    def test_multiple_resonances(self):
        """One learning can resonate with multiple agents' queries."""
        engine = ResonanceEngine(threshold=0.5)
        emb = [1.0, 0.0, 0.0]
        engine.record_query("b1", "q1", emb[:])
        engine.record_query("b2", "q2", emb[:])
        engine.record_query("b3", "q3", emb[:])
        hits = engine.record_learning("a", "learn", emb[:])
        assert len(hits) == 3

    def test_resonance_hit_fields(self):
        engine = ResonanceEngine(threshold=0.5)
        engine.record_query("b", "what is sonar?", [1.0, 0.0])
        hits = engine.record_learning("a", "sonar uses sound waves", [1.0, 0.0])
        assert hits[0].learning_content == "sonar uses sound waves"
        assert hits[0].query_content == "what is sonar?"

    def test_resonance_increments_stats(self):
        engine = ResonanceEngine(threshold=0.5)
        engine.record_query("b", "q", [1.0, 0.0])
        engine.record_learning("a", "l", [1.0, 0.0])
        assert engine.stats["resonances_detected"] == 1


class TestEmitResonances:
    @pytest.mark.asyncio
    async def test_emit_with_bus(self):
        bus = FakeBus()
        engine = ResonanceEngine(bus=bus, threshold=0.5)
        engine.record_query("b", "q", [1.0, 0.0])
        hits = engine.record_learning("a", "l", [1.0, 0.0])

        await engine.emit_resonances(hits)

        assert len(bus.published) == 1
        event = bus.published[0]
        assert event.event_type == "resonance"
        assert event.importance == 0.7
        assert event.novelty == 0.8

    @pytest.mark.asyncio
    async def test_emit_without_bus(self):
        engine = ResonanceEngine(bus=None, threshold=0.5)
        engine.record_query("b", "q", [1.0, 0.0])
        hits = engine.record_learning("a", "l", [1.0, 0.0])
        # Should not crash
        await engine.emit_resonances(hits)

    @pytest.mark.asyncio
    async def test_emit_empty_hits(self):
        bus = FakeBus()
        engine = ResonanceEngine(bus=bus)
        await engine.emit_resonances([])
        assert len(bus.published) == 0


class TestPruneStale:
    def test_prune_old_learnings(self):
        engine = ResonanceEngine()
        old_time = time.time() - LEARNING_TTL_SECONDS - 100
        event = LearningEvent(
            agent_id="a",
            content="old",
            embedding=[1.0],
            timestamp=old_time,
        )
        engine._learnings["a"] = [event]
        result = engine.prune_stale()
        assert result["learnings_pruned"] == 1
        assert "a" not in engine._learnings

    def test_prune_old_queries(self):
        engine = ResonanceEngine()
        old_time = time.time() - LEARNING_TTL_SECONDS - 100
        query = ActiveQuery(
            agent_id="b",
            content="old query",
            embedding=[1.0],
            timestamp=old_time,
        )
        engine._queries["b"] = [query]
        result = engine.prune_stale()
        assert result["queries_pruned"] == 1
        assert "b" not in engine._queries

    def test_keep_recent(self):
        engine = ResonanceEngine()
        engine.record_learning("a", "recent", [1.0])
        engine.record_query("b", "recent", [1.0])
        result = engine.prune_stale()
        assert result["learnings_pruned"] == 0
        assert result["queries_pruned"] == 0

    def test_prune_mixed(self):
        engine = ResonanceEngine()
        old_time = time.time() - 7200  # 2 hours ago
        engine._learnings["a"] = [
            LearningEvent("a", "old", [1.0], old_time),
            LearningEvent("a", "new", [1.0], time.time()),
        ]
        result = engine.prune_stale()
        assert result["learnings_pruned"] == 1
        assert len(engine._learnings["a"]) == 1


class TestRecentResonances:
    def test_recent_resonances_property(self):
        engine = ResonanceEngine(threshold=0.1)
        engine.record_query("b", "q", [1.0, 0.0])
        engine.record_learning("a", "l", [1.0, 0.0])
        recent = engine.recent_resonances
        assert len(recent) == 1

    def test_recent_resonances_capped_at_10(self):
        engine = ResonanceEngine(threshold=0.1)
        emb = [1.0, 0.0]
        for i in range(15):
            engine.record_query(f"b{i}", f"q{i}", emb[:])
        engine.record_learning("a", "l", emb[:])
        recent = engine.recent_resonances
        assert len(recent) <= 10


class TestStatsAfterOperations:
    def test_stats_after_multiple_operations(self):
        engine = ResonanceEngine(threshold=0.5)
        engine.record_learning("a", "fish", [1.0, 0.0])
        engine.record_learning("a", "boat", [0.0, 1.0])
        engine.record_query("b", "fish?", [1.0, 0.0])
        engine.record_query("c", "boat?", [0.0, 1.0])

        stats = engine.stats
        assert stats["learnings_tracked"] == 2
        assert stats["queries_tracked"] == 2
        assert stats["active_agents_learning"] == 1  # only agent-a
        assert stats["active_agents_querying"] == 2  # b and c
        assert stats["resonances_detected"] >= 2

    def test_stats_threshold_included(self):
        engine = ResonanceEngine(threshold=0.65)
        assert engine.stats["threshold"] == 0.65
