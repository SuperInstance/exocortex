"""Tests for Phase 2: SurrealDB Backend, Dream Cycle, Resonance Engine."""

import asyncio
import math
import time

import pytest

from src.core.types import CortexEvent, MemoryEntry
from src.memory.surrealdb_backend import SurrealDBMemoryLayer, SurrealDBSchema, _cosine_similarity
from src.compute.dream import DreamCycle, DreamCluster, KMeans, DreamReport, _euclidean_distance
from src.core.resonance import ResonanceEngine, ResonanceHit, LearningEvent, ActiveQuery


# ============================================================================
# SurrealDB Backend Tests (using fallback in-memory mode)
# ============================================================================


@pytest.mark.asyncio
async def test_surrealdb_backend_fallback_init():
    """SurrealDBMemoryLayer should initialize with in-memory fallback."""
    layer = SurrealDBMemoryLayer()
    assert not layer.is_connected
    # Should work as regular MemoryLayer via inheritance
    assert layer.stats["total"] == 0


@pytest.mark.asyncio
async def test_surrealdb_backend_remember_recall():
    """SurrealDB backend (fallback mode) should store and recall memories."""
    layer = SurrealDBMemoryLayer()
    emb = [0.1] * 384

    entry = await layer.remember("test memory", emb, "agent-1", ["test"])
    assert entry.content == "test memory"
    assert entry.agent_id == "agent-1"

    results = await layer.recall(emb, top_k=5)
    assert len(results) >= 1
    assert results[0][0].content == "test memory"


@pytest.mark.asyncio
async def test_surrealdb_backend_tag_query():
    """SurrealDB backend should support tag-based queries."""
    layer = SurrealDBMemoryLayer()
    await layer.remember("garden data", [0.1] * 384, "agent-1", ["garden", "iot"])
    await layer.remember("server log", [0.2] * 384, "agent-2", ["devops"])

    results = await layer.query(["garden"])
    assert len(results) == 1
    assert results[0].content == "garden data"


@pytest.mark.asyncio
async def test_surrealdb_backend_get_by_id():
    """SurrealDB backend should retrieve memories by ID."""
    layer = SurrealDBMemoryLayer()
    entry = await layer.remember("unique memory", [0.3] * 384, "agent-1")

    retrieved = await layer.get(entry.id)
    assert retrieved is not None
    assert retrieved.content == "unique memory"


@pytest.mark.asyncio
async def test_surrealdb_backend_get_missing():
    """SurrealDB backend should return None for missing IDs."""
    layer = SurrealDBMemoryLayer()
    result = await layer.get("nonexistent-id")
    assert result is None


@pytest.mark.asyncio
async def test_surrealdb_backend_tick_cooling():
    """SurrealDB backend should cool memories from hot to cold."""
    layer = SurrealDBMemoryLayer()
    entry = await layer.remember("aging memory", [0.5] * 384, "agent-1")

    # Force age it beyond warm threshold
    for e in layer._warm.values():
        e.last_reinforced = time.time() - 86400 * 2

    stats = await layer.tick()
    assert stats["cooled_to_cold"] >= 1


@pytest.mark.asyncio
async def test_surrealdb_schema_sql():
    """Schema SQL should contain all required table definitions."""
    sql = SurrealDBSchema.SCHEMA_SQL
    assert "DEFINE TABLE memory SCHEMAFULL" in sql
    assert "DEFINE TABLE knowledge SCHEMAFULL" in sql
    assert "DEFINE TABLE agent SCHEMAFULL" in sql
    assert "embedding" in sql
    assert "agent_id" in sql


@pytest.mark.asyncio
async def test_surrealdb_connect_failure():
    """Connect should return False when SurrealDB is unavailable."""
    layer = SurrealDBMemoryLayer(url="http://localhost:99999")
    result = await layer.connect()
    assert result is False
    assert not layer.is_connected


@pytest.mark.asyncio
async def test_surrealdb_get_random_memories():
    """get_random_memories should sample from in-memory store."""
    layer = SurrealDBMemoryLayer()
    for i in range(10):
        await layer.remember(f"memory {i}", [float(i)] * 384, "agent-1")

    samples = await layer.get_random_memories(5)
    assert len(samples) <= 5
    assert len(samples) > 0


@pytest.mark.asyncio
async def test_surrealdb_get_recent_memories():
    """get_recent_memories should return only recent entries."""
    layer = SurrealDBMemoryLayer()
    old_time = time.time() - 7200  # 2 hours ago
    old_entry = MemoryEntry(content="old", embedding=[0.1] * 384, agent_id="a", created_at=old_time)
    layer._warm[old_entry.id] = old_entry

    await layer.remember("new memory", [0.2] * 384, "agent-1")

    recent = await layer.get_recent_memories(time.time() - 3600)
    assert len(recent) == 1
    assert recent[0].content == "new memory"


# ============================================================================
# Dream Cycle Tests
# ============================================================================


def test_kmeans_basic_clustering():
    """KMeans should cluster well-separated data."""
    # Create 3 clear clusters
    cluster_a = [[1.0, 0.0] for _ in range(5)]
    cluster_b = [[0.0, 1.0] for _ in range(5)]
    cluster_c = [[-1.0, 0.0] for _ in range(5)]
    all_data = cluster_a + cluster_b + cluster_c

    kmeans = KMeans(n_clusters=3, max_iter=50)
    labels, centroids = kmeans.fit(all_data)

    assert len(labels) == 15
    assert len(centroids) == 3
    # Should have 3 distinct labels
    assert len(set(labels)) == 3


def test_kmeans_fewer_points_than_clusters():
    """KMeans should handle fewer points than clusters."""
    data = [[1.0, 0.0], [0.0, 1.0]]
    kmeans = KMeans(n_clusters=5)
    labels, centroids = kmeans.fit(data)
    assert len(labels) == 2


def test_kmeans_empty():
    """KMeans should handle empty input."""
    kmeans = KMeans(n_clusters=3)
    labels, centroids = kmeans.fit([])
    assert labels == []
    assert centroids == []


def test_euclidean_distance():
    """Euclidean distance should compute correctly."""
    a = [3.0, 0.0]
    b = [0.0, 4.0]
    dist = _euclidean_distance(a, b)
    assert abs(dist - 5.0) < 0.001


@pytest.mark.asyncio
async def test_dream_cycle_basic():
    """Dream cycle should run and produce a report."""
    from src.memory import MemoryLayer

    memory = MemoryLayer()
    # Populate with some memories
    for i in range(10):
        emb = [float(i) / 10.0] * 384
        await memory.remember(f"memory {i}", emb, "agent-1", [f"tag{i%3}"])

    dream = DreamCycle(memory)
    report = await dream.run()

    assert isinstance(report, DreamReport)
    assert report.memories_sampled > 0
    assert len(report.narrative) > 0


@pytest.mark.asyncio
async def test_dream_cycle_with_clusters():
    """Dream cycle should find clusters in diverse data."""
    from src.memory import MemoryLayer

    memory = MemoryLayer()
    # Create 3 distinct groups of memories
    for i in range(5):
        await memory.remember(f"group-a-{i}", [1.0, 0.0] + [0.0] * 382, "agent-1", ["alpha"])
    for i in range(5):
        await memory.remember(f"group-b-{i}", [0.0, 1.0] + [0.0] * 382, "agent-2", ["beta"])
    for i in range(5):
        await memory.remember(f"group-c-{i}", [0.0, 0.0] + [1.0] * 382, "agent-3", ["gamma"])

    dream = DreamCycle(memory)
    report = await dream.run()

    assert report.memories_sampled > 0
    # Should find multiple clusters
    assert len(report.clusters) >= 2


@pytest.mark.asyncio
async def test_dream_cycle_idle_tracking():
    """Dream cycle should track idle time."""
    from src.memory import MemoryLayer

    dream = DreamCycle(MemoryLayer())
    assert dream.idle_seconds >= 0

    dream.touch()
    idle_after_touch = dream.idle_seconds
    assert idle_after_touch < 1.0


@pytest.mark.asyncio
async def test_dream_cycle_empty_memory():
    """Dream cycle should handle empty memory gracefully."""
    from src.memory import MemoryLayer

    dream = DreamCycle(MemoryLayer())
    report = await dream.run()

    assert report.memories_sampled == 0
    assert "silence" in report.narrative.lower()


@pytest.mark.asyncio
async def test_dream_cycle_emits_event():
    """Dream cycle should emit events to the bus."""
    from src.memory import MemoryLayer
    from src.bus import CorticalBus

    bus = CorticalBus()
    received = []

    async def subscriber(event):
        received.append(event)

    bus.subscribe(subscriber)
    await bus.start()

    memory = MemoryLayer()
    for i in range(5):
        await memory.remember(f"memory {i}", [float(i)] * 384, "agent-1")

    dream = DreamCycle(memory, bus=bus)
    await dream.run()

    # Wait for dispatch
    await asyncio.sleep(0.2)
    await bus.stop()

    dream_events = [e for e in received if e.event_type == "dream"]
    assert len(dream_events) >= 1
    assert "narrative" in dream_events[0].payload


# ============================================================================
# Resonance Engine Tests
# ============================================================================


def test_resonance_no_overlap():
    """No resonance when embeddings are orthogonal."""
    engine = ResonanceEngine(threshold=0.8)

    # Agent A learns about cats
    hits = engine.record_learning(
        "agent-a", "cats are furry",
        [1.0, 0.0, 0.0] + [0.0] * 381,
    )

    # Agent B queries about servers
    hits = engine.record_query(
        "agent-b", "server uptime",
        [0.0, 1.0, 0.0] + [0.0] * 381,
    )

    assert len(hits) == 0


def test_resonance_detects_overlap():
    """Resonance should fire when learning overlaps query."""
    engine = ResonanceEngine(threshold=0.8)

    # Agent B has an active query
    query_emb = [1.0, 0.0, 0.0] + [0.0] * 381
    engine.record_query("agent-b", "machine learning models", query_emb)

    # Agent A learns something very similar
    learning_emb = [0.99, 0.01, 0.0] + [0.0] * 381  # very similar
    hits = engine.record_learning("agent-a", "neural network training", learning_emb)

    assert len(hits) >= 1
    assert hits[0].similarity > 0.8
    assert hits[0].source_agent == "agent-a"
    assert hits[0].target_agent == "agent-b"


def test_resonance_cross_agent_only():
    """Resonance should not fire for same-agent learning/query."""
    engine = ResonanceEngine(threshold=0.8)

    emb = [1.0] * 384
    engine.record_query("agent-a", "my query", emb)

    hits = engine.record_learning("agent-a", "my learning", emb)
    # Same agent — should NOT resonate
    assert len(hits) == 0


def test_resonance_stats():
    """Resonance engine should track stats."""
    engine = ResonanceEngine()
    engine.record_learning("a", "test", [0.1] * 384)
    engine.record_query("b", "test", [0.2] * 384)

    stats = engine.stats
    assert stats["learnings_tracked"] == 1
    assert stats["queries_tracked"] == 1
    assert stats["active_agents_learning"] == 1
    assert stats["active_agents_querying"] == 1


def test_resonance_prune_stale():
    """Pruning should remove old events."""
    engine = ResonanceEngine()

    # Record a learning with a manually old timestamp
    event = LearningEvent(
        agent_id="a",
        content="old stuff",
        embedding=[0.1] * 384,
        timestamp=time.time() - 7200,  # 2 hours ago
    )
    engine._learnings["a"] = [event]

    pruned = engine.prune_stale(max_age=3600)
    assert pruned["learnings_pruned"] == 1
    assert "a" not in engine._learnings


def test_resonance_max_per_agent():
    """Engine should trim to max per agent."""
    engine = ResonanceEngine()

    for i in range(60):
        engine.record_learning("agent-a", f"learning {i}", [float(i)] * 384)

    # Should be capped at MAX_LEARNING_PER_AGENT (50)
    assert len(engine._learnings["agent-a"]) <= 50


@pytest.mark.asyncio
async def test_resonance_emit_to_bus():
    """Resonance should emit events to the Cortical Bus."""
    from src.bus import CorticalBus

    bus = CorticalBus()
    received = []

    async def subscriber(event):
        received.append(event)

    bus.subscribe(subscriber)
    await bus.start()

    engine = ResonanceEngine(bus=bus, threshold=0.8)

    # Set up a query first
    engine.record_query("agent-b", "neural networks", [1.0, 0.0] + [0.0] * 382)

    # Trigger resonance
    hits = engine.record_learning("agent-a", "deep learning", [0.99, 0.01] + [0.0] * 382)
    await engine.emit_resonances(hits)

    await asyncio.sleep(0.2)
    await bus.stop()

    resonance_events = [e for e in received if e.event_type == "resonance"]
    assert len(resonance_events) >= 1
    assert resonance_events[0].payload["source_agent"] == "agent-a"
    assert resonance_events[0].payload["target_agent"] == "agent-b"


def test_cosine_similarity_util():
    """Cosine similarity utility should compute correctly."""
    # Identical vectors
    assert abs(_cosine_similarity([1.0, 0.0], [1.0, 0.0]) - 1.0) < 0.001
    # Orthogonal
    assert abs(_cosine_similarity([1.0, 0.0], [0.0, 1.0])) < 0.001
    # Opposite
    assert abs(_cosine_similarity([1.0, 0.0], [-1.0, 0.0]) - (-1.0)) < 0.001
    # Empty
    assert _cosine_similarity([], []) == 0.0


def test_resonance_multiple_agents():
    """Resonance should detect overlaps across multiple agent pairs."""
    engine = ResonanceEngine(threshold=0.7)

    shared_emb = [1.0, 0.0] + [0.0] * 382

    # Multiple agents querying
    engine.record_query("agent-b", "topic X", shared_emb)
    engine.record_query("agent-c", "topic X", shared_emb)

    # Agent A learns matching content
    hits = engine.record_learning("agent-a", "about topic X", shared_emb)

    # Should resonate with both B and C
    assert len(hits) >= 2
    target_agents = {h.target_agent for h in hits}
    assert "agent-b" in target_agents
    assert "agent-c" in target_agents
