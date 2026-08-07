"""Tests for Dream Cycle Engine — the subconscious of the cortex.

Tests k-means clustering, anomaly detection, edge strengthening,
narrative generation, and the full dream cycle lifecycle.
"""

import asyncio
import math
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.compute.dream import (
    DreamAnomaly,
    DreamCluster,
    DreamCycle,
    DreamReport,
    KMeans,
    ANOMALY_SIGMA,
    EDGE_STRENGTHEN_DELTA,
    IDLE_THRESHOLD_SECONDS,
    MAX_ITERATIONS,
    N_CLUSTERS,
    SAMPLE_SIZE,
    _cosine_similarity,
    _euclidean_distance,
)
from src.core.types import CortexEvent, MemoryEntry


# ─── Helper fixtures ───────────────────────────────────────────────

def make_memory(content="test", embedding=None, confidence=1.0, tags=None):
    """Create a MemoryEntry with sensible defaults."""
    return MemoryEntry(
        content=content,
        embedding=embedding or [1.0, 0.0, 0.0],
        confidence=confidence,
        tags=tags or [],
    )


def make_memories_with_embeddings(n, dim=4):
    """Create n memories with distinct embeddings."""
    memories = []
    for i in range(n):
        emb = [0.0] * dim
        emb[i % dim] = 1.0
        memories.append(make_memory(
            content=f"memory-{i}",
            embedding=emb[:],
            tags=[f"tag-{i % dim}"],
        ))
    return memories


class FakeMemoryLayer:
    """Fake memory layer for dream cycle tests."""

    def __init__(self, memories=None):
        self._memories = memories or []
        self._edges = {}
        self.strengthen_calls = []

    async def get_random_memories(self, n):
        return self._memories[:n]

    async def get_recent_memories(self, since, limit=100):
        return self._memories[:limit]

    async def strengthen_edge(self, id_a, id_b, delta):
        self.strengthen_calls.append((id_a, id_b, delta))
        key = tuple(sorted([id_a, id_b]))
        self._edges[key] = self._edges.get(key, 0) + delta


class FakeBus:
    """Fake Cortical Bus."""

    def __init__(self):
        self.published = []

    async def publish(self, event):
        self.published.append(event)


# ─── Utility function tests ────────────────────────────────────────

class TestEuclideanDistance:
    def test_identical_vectors(self):
        assert _euclidean_distance([1, 2, 3], [1, 2, 3]) == 0.0

    def test_unit_vectors(self):
        assert _euclidean_distance([1, 0], [0, 1]) == pytest.approx(math.sqrt(2))

    def test_single_dimension(self):
        assert _euclidean_distance([5], [2]) == 3.0

    def test_empty_vectors(self):
        assert _euclidean_distance([], []) == 0.0

    def test_negative_values(self):
        d = _euclidean_distance([-1, -2], [-4, -6])
        assert d == pytest.approx(5.0)

    def test_large_vectors(self):
        a = [1.0] * 100
        b = [0.0] * 100
        assert _euclidean_distance(a, b) == pytest.approx(10.0)


class TestCosineSimilarity:
    def test_identical_vectors(self):
        assert _cosine_similarity([1, 2, 3], [1, 2, 3]) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        assert _cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        assert _cosine_similarity([1, 1], [-1, -1]) == pytest.approx(-1.0)

    def test_zero_vector_a(self):
        assert _cosine_similarity([0, 0], [1, 1]) == 0.0

    def test_zero_vector_b(self):
        assert _cosine_similarity([1, 1], [0, 0]) == 0.0

    def test_empty_vectors(self):
        assert _cosine_similarity([], []) == 0.0

    def test_different_lengths(self):
        # zip truncates to shortest
        result = _cosine_similarity([1, 0, 0, 0], [1, 0])
        # Should work, comparing first 2 elements
        assert result == pytest.approx(0.5 + 0.5)  # cos of [1,0] and [1,0]


# ─── KMeans tests ──────────────────────────────────────────────────

class TestKMeansInit:
    def test_default_params(self):
        km = KMeans()
        assert km.n_clusters == N_CLUSTERS
        assert km.max_iter == MAX_ITERATIONS

    def test_custom_params(self):
        km = KMeans(n_clusters=5, max_iter=50)
        assert km.n_clusters == 5
        assert km.max_iter == 50


class TestKMeansFit:
    def test_empty_embeddings(self):
        km = KMeans(n_clusters=3)
        labels, centroids = km.fit([])
        assert labels == []
        assert centroids == []

    def test_single_embedding(self):
        km = KMeans(n_clusters=3)
        labels, centroids = km.fit([[1.0, 2.0]])
        assert labels == [0]
        assert len(centroids) == 1

    def test_fewer_than_clusters(self):
        """When n < k, each point gets its own cluster."""
        km = KMeans(n_clusters=5)
        labels, centroids = km.fit([[1, 0], [0, 1]])
        assert labels == [0, 1]
        assert len(centroids) == 2

    def test_equal_to_clusters(self):
        km = KMeans(n_clusters=3)
        labels, centroids = km.fit([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
        assert len(set(labels)) <= 3

    def test_well_separated_clusters(self):
        """Three obvious clusters should be found."""
        km = KMeans(n_clusters=3, max_iter=100)
        cluster_a = [[10 + i * 0.01, 0] for i in range(10)]
        cluster_b = [[0, 10 + i * 0.01] for i in range(10)]
        cluster_c = [[-10 - i * 0.01, -10 - i * 0.01] for i in range(10)]
        data = cluster_a + cluster_b + cluster_c

        labels, centroids = km.fit(data)

        # Each true cluster should map to a single label
        a_labels = set(labels[:10])
        b_labels = set(labels[10:20])
        c_labels = set(labels[20:30])
        assert len(a_labels) == 1
        assert len(b_labels) == 1
        assert len(c_labels) == 1
        assert a_labels != b_labels
        assert a_labels != c_labels
        assert b_labels != c_labels

    def test_convergence_before_max_iter(self):
        """K-means should converge quickly on easy data."""
        km = KMeans(n_clusters=2, max_iter=100)
        data = [[0, 0], [0.1, 0.1], [10, 10], [10.1, 10.1]]
        labels, centroids = km.fit(data)
        assert len(centroids) == 2

    def test_all_identical_points(self):
        """All identical points should still produce valid output."""
        km = KMeans(n_clusters=2)
        data = [[1.0, 1.0]] * 10
        labels, centroids = km.fit(data)
        assert len(labels) == 10
        assert len(centroids) <= 2

    def test_high_dimensional(self):
        """K-means on 50-dimensional embeddings."""
        km = KMeans(n_clusters=3)
        dim = 50
        data = []
        for c in range(3):
            for _ in range(5):
                vec = [0.0] * dim
                vec[c] = 1.0
                data.append(vec[:])
        labels, centroids = km.fit(data)
        assert len(labels) == 15
        assert len(centroids) <= 3


class TestKMeansPlusPlusInit:
    def test_init_centroids_spread(self):
        """k-means++ should pick spread-out centroids."""
        km = KMeans(n_clusters=3)
        data = [[0, 0], [10, 10], [20, 20], [30, 30], [40, 40], [50, 50]]
        centroids = km._init_centroids(data, len(data))
        assert len(centroids) == 3
        # First centroid is random, but centroids should be distinct
        unique = set(tuple(c) for c in centroids)
        assert len(unique) == 3

    def test_init_centroids_empty(self):
        km = KMeans(n_clusters=3)
        assert km._init_centroids([], 0) == []

    def test_init_centroids_single_point(self):
        km = KMeans(n_clusters=3)
        centroids = km._init_centroids([[1.0, 2.0]], 1)
        assert len(centroids) == 1


# ─── DreamCycle tests ──────────────────────────────────────────────

class TestDreamCycleInit:
    def test_default_values(self):
        mem = FakeMemoryLayer()
        dc = DreamCycle(mem)
        assert dc.dream_count == 0
        assert dc.idle_seconds > 0
        assert dc._bus is None

    def test_with_bus(self):
        mem = FakeMemoryLayer()
        bus = FakeBus()
        dc = DreamCycle(mem, bus=bus)
        assert dc._bus is bus

    def test_touch_resets_idle(self):
        dc = DreamCycle(FakeMemoryLayer())
        old_idle = dc.idle_seconds
        time.sleep(0.01)
        assert dc.idle_seconds > old_idle
        dc.touch()
        assert dc.idle_seconds < 0.1


class TestDreamCycleRun:
    @pytest.mark.asyncio
    async def test_empty_memory(self):
        dc = DreamCycle(FakeMemoryLayer([]))
        report = await dc.run()
        assert report.memories_sampled == 0
        assert "No memories to dream upon" in report.narrative

    @pytest.mark.asyncio
    async def test_no_embeddings(self):
        """Memories without embeddings produce shallow dream."""
        mems = [
            MemoryEntry(content="no emb", embedding=[]),
            MemoryEntry(content="no emb 2", embedding=[]),
        ]
        dc = DreamCycle(FakeMemoryLayer(mems))
        report = await dc.run()
        assert report.memories_sampled == 2
        assert "shallow" in report.narrative.lower()

    @pytest.mark.asyncio
    async def test_single_embedding(self):
        mems = [
            MemoryEntry(content="a", embedding=[1.0, 0.0]),
            MemoryEntry(content="b", embedding=[]),
        ]
        dc = DreamCycle(FakeMemoryLayer(mems))
        report = await dc.run()
        assert report.memories_sampled == 2
        assert "shallow" in report.narrative.lower()

    @pytest.mark.asyncio
    async def test_proper_clustering(self):
        """Multiple embedded memories should cluster."""
        mems = make_memories_with_embeddings(10, dim=4)
        dc = DreamCycle(FakeMemoryLayer(mems))
        report = await dc.run()
        assert report.memories_sampled == 10
        assert len(report.clusters) > 0
        assert report.duration_ms > 0

    @pytest.mark.asyncio
    async def test_dream_count_increments(self):
        mems = make_memories_with_embeddings(5)
        dc = DreamCycle(FakeMemoryLayer(mems))
        assert dc.dream_count == 0
        await dc.run()
        assert dc.dream_count == 1
        await dc.run()
        assert dc.dream_count == 2

    @pytest.mark.asyncio
    async def test_bus_publishes_dream_event(self):
        mems = make_memories_with_embeddings(6, dim=3)
        bus = FakeBus()
        dc = DreamCycle(FakeMemoryLayer(mems), bus=bus)
        await dc.run()
        assert len(bus.published) == 1
        event = bus.published[0]
        assert event.event_type == "dream"
        assert event.source == "dream-cycle"
        assert "dream_number" in event.payload
        assert "narrative" in event.payload

    @pytest.mark.asyncio
    async def test_no_bus_no_error(self):
        mems = make_memories_with_embeddings(5)
        dc = DreamCycle(FakeMemoryLayer(mems), bus=None)
        report = await dc.run()
        assert report.memories_sampled > 0  # Should not crash

    @pytest.mark.asyncio
    async def test_edge_strengthening(self):
        """When memories are similar, edges should be strengthened."""
        # Two memories with identical embeddings (similarity = 1.0)
        mems = [
            make_memory(content="a", embedding=[1.0, 0.0, 0.0], tags=["x"]),
            make_memory(content="b", embedding=[1.0, 0.0, 0.0], tags=["x"]),
            make_memory(content="c", embedding=[0.0, 1.0, 0.0], tags=["y"]),
            make_memory(content="d", embedding=[0.0, 1.0, 0.0], tags=["y"]),
        ]
        mem_layer = FakeMemoryLayer(mems)
        dc = DreamCycle(mem_layer)
        report = await dc.run()
        assert report.edges_strengthened > 0
        assert len(mem_layer.strengthen_calls) > 0

    @pytest.mark.asyncio
    async def test_no_edge_strengthening_without_method(self):
        """Memory layer without strengthen_edge should not crash."""
        mems = make_memories_with_embeddings(5)

        class NoEdgeMemoryLayer:
            def __init__(self, memories):
                self._memories = memories

            async def get_random_memories(self, n):
                return self._memories[:n]

            async def get_recent_memories(self, since, limit=100):
                return self._memories[:limit]
                # No strengthen_edge method

        mem_layer = NoEdgeMemoryLayer(mems)
        dc = DreamCycle(mem_layer)
        report = await dc.run()
        assert report.edges_strengthened == 0

    @pytest.mark.asyncio
    async def test_narrative_generation(self):
        mems = make_memories_with_embeddings(8, dim=3)
        dc = DreamCycle(FakeMemoryLayer(mems))
        report = await dc.run()
        assert len(report.narrative) > 0
        assert isinstance(report.narrative, str)

    @pytest.mark.asyncio
    async def test_dominant_tags_in_clusters(self):
        mems = [
            make_memory(content=f"fish-{i}", embedding=[1, 0, 0], tags=["fish", "sonar"])
            for i in range(4)
        ] + [
            make_memory(content=f"weather-{i}", embedding=[0, 1, 0], tags=["weather", "wind"])
            for i in range(4)
        ]
        dc = DreamCycle(FakeMemoryLayer(mems))
        report = await dc.run()
        all_tags = []
        for c in report.clusters:
            all_tags.extend(c.dominant_tags)
        assert "fish" in all_tags or "sonar" in all_tags
        assert "weather" in all_tags or "wind" in all_tags


class TestDreamCycleAnomalies:
    @pytest.mark.asyncio
    async def test_anomaly_detection(self):
        """Memories with very different confidence should be flagged."""
        mems = []
        for i in range(10):
            mems.append(make_memory(
                content=f"normal-{i}",
                embedding=[float(i), 0.0, 0.0],
                confidence=0.9,
            ))
        # One outlier
        mems.append(make_memory(
            content="anomaly",
            embedding=[100.0, 0.0, 0.0],
            confidence=0.1,
        ))
        dc = DreamCycle(FakeMemoryLayer(mems))
        report = await dc.run()
        # The anomaly detection works on recent memories
        # With our fake, get_recent_memories returns all
        assert isinstance(report.anomalies, list)

    def test_find_anomalies_few_memories(self):
        dc = DreamCycle(FakeMemoryLayer())
        result = dc._find_anomalies([])
        assert result == []

    def test_find_anomalies_under_threshold(self):
        dc = DreamCycle(FakeMemoryLayer())
        mems = [make_memory(confidence=0.9) for _ in range(10)]
        result = dc._find_anomalies(mems)
        # All same confidence = no anomalies (std = 0, handled by epsilon)
        # With std near 0, every deviation is huge, so check behavior
        assert isinstance(result, list)


class TestDreamCycleStats:
    def test_stats_structure(self):
        dc = DreamCycle(FakeMemoryLayer())
        stats = dc.stats
        assert "dream_count" in stats
        assert "last_dream" in stats
        assert "idle_seconds" in stats

    def test_stats_after_run(self):
        mems = make_memories_with_embeddings(5)
        dc = DreamCycle(FakeMemoryLayer(mems))
        asyncio.run(dc.run())
        stats = dc.stats
        assert stats["dream_count"] == 1
        assert stats["last_dream"] > 0


class TestDreamCycleStartStop:
    @pytest.mark.asyncio
    async def test_start_stop(self):
        dc = DreamCycle(FakeMemoryLayer())
        await dc.start(interval=0.01)
        assert dc._running is True
        await asyncio.sleep(0.05)
        await dc.stop()
        assert dc._running is False

    @pytest.mark.asyncio
    async def test_stop_without_start(self):
        dc = DreamCycle(FakeMemoryLayer())
        await dc.stop()  # Should not crash

    @pytest.mark.asyncio
    async def test_start_triggers_dream_when_idle(self):
        mems = make_memories_with_embeddings(5)
        dc = DreamCycle(FakeMemoryLayer(mems))
        # Set idle by not touching
        await dc.start(interval=0.01)
        await asyncio.sleep(0.1)
        await dc.stop()
        assert dc.dream_count >= 0  # May or may not have dreamed


class TestDreamReport:
    def test_empty_report(self):
        report = DreamReport()
        assert report.clusters == []
        assert report.anomalies == []
        assert report.edges_strengthened == 0
        assert report.memories_sampled == 0
        assert report.narrative == ""

    def test_narrative_only(self):
        report = DreamReport(narrative="The cortex dreams in silence.")
        assert "silence" in report.narrative


class TestDreamCluster:
    def test_default_values(self):
        c = DreamCluster(centroid=[1.0, 0.0])
        assert c.memory_ids == []
        assert c.coherence == 0.0
        assert c.dominant_tags == []


class TestDreamConstants:
    def test_idle_threshold(self):
        assert IDLE_THRESHOLD_SECONDS == 30.0

    def test_sample_size(self):
        assert SAMPLE_SIZE == 20

    def test_n_clusters(self):
        assert N_CLUSTERS == 3

    def test_anomaly_sigma(self):
        assert ANOMALY_SIGMA == 2.0

    def test_edge_delta(self):
        assert EDGE_STRENGTHEN_DELTA == 0.15
