"""Dream Cycle Engine — offline memory consolidation when idle.

Runs automatically when the cortex has been idle >30s:
1. Sample random memories from all tiers
2. Run k-means clustering on embeddings (pure Python, no sklearn)
3. Find anomalies in recent memory data
4. Strengthen graph edges between related memories (same cluster)
5. Emit "dream" events to the Cortical Bus with atmospheric narrative

This is the subconscious — background work that strengthens connections
and surfaces patterns without conscious agent involvement.
"""

from __future__ import annotations

import asyncio
import logging
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any

from ..core.types import CortexEvent, MemoryEntry

logger = logging.getLogger(__name__)

# Dream cycle parameters
IDLE_THRESHOLD_SECONDS = 30.0
SAMPLE_SIZE = 20
N_CLUSTERS = 3
MAX_ITERATIONS = 20
ANOMALY_SIGMA = 2.0
EDGE_STRENGTHEN_DELTA = 0.15


@dataclass
class DreamCluster:
    """A cluster of memories discovered during dreaming."""
    centroid: list[float]
    memory_ids: list[str] = field(default_factory=list)
    coherence: float = 0.0  # avg similarity to centroid
    dominant_tags: list[str] = field(default_factory=list)


@dataclass
class DreamAnomaly:
    """An anomaly found during dream cycle."""
    memory_id: str
    metric: str
    value: float
    expected: float
    sigma: float


@dataclass
class DreamReport:
    """Full report from a dream cycle run."""
    clusters: list[DreamCluster] = field(default_factory=list)
    anomalies: list[DreamAnomaly] = field(default_factory=list)
    edges_strengthened: int = 0
    memories_sampled: int = 0
    narrative: str = ""
    duration_ms: float = 0.0


class KMeans:
    """Simple k-means clustering — no sklearn dependency.

    Works on lists of floats (embedding vectors).
    Uses Lloyd's algorithm with random initialization.
    """

    def __init__(self, n_clusters: int = N_CLUSTERS, max_iter: int = MAX_ITERATIONS) -> None:
        self.n_clusters = n_clusters
        self.max_iter = max_iter

    def _init_centroids(self, embeddings: list[list[float]], n: int) -> list[list[float]]:
        """K-means++ initialization for better cluster separation."""
        k = min(self.n_clusters, n)
        if k == 0:
            return []

        # Pick first centroid randomly
        first_idx = random.randint(0, n - 1)
        centroids = [embeddings[first_idx][:]]

        for _ in range(1, k):
            # Compute distance from each point to nearest existing centroid
            dists = []
            for emb in embeddings:
                min_dist = min(_euclidean_distance(emb, c) for c in centroids)
                dists.append(min_dist * min_dist)  # square for probability weighting
            total = sum(dists)
            if total == 0:
                # All points are the same as centroids
                idx = random.randint(0, n - 1)
            else:
                # Weighted random selection
                r = random.random() * total
                cumulative = 0.0
                idx = 0
                for i, d in enumerate(dists):
                    cumulative += d
                    if cumulative >= r:
                        idx = i
                        break
            centroids.append(embeddings[idx][:])

        return centroids

    def fit(self, embeddings: list[list[float]]) -> tuple[list[int], list[list[float]]]:
        """Cluster embeddings. Returns (labels, centroids)."""
        n = len(embeddings)
        if n == 0:
            return [], []
        if n <= self.n_clusters:
            # Fewer items than clusters — each gets its own
            labels = list(range(n))
            return labels, embeddings[:]

        dim = len(embeddings[0])
        # Initialize centroids using k-means++ for better convergence
        centroids = self._init_centroids(embeddings, n)
        # Fallback: if centroids still empty, just use random
        if not centroids:
            indices = random.sample(range(n), min(self.n_clusters, n))
            centroids = [embeddings[i][:] for i in indices]
        labels = [0] * n

        for _ in range(self.max_iter):
            # Assign each point to nearest centroid
            new_labels = []
            for emb in embeddings:
                best_cluster = 0
                best_dist = float("inf")
                for ci, centroid in enumerate(centroids):
                    dist = _euclidean_distance(emb, centroid)
                    if dist < best_dist:
                        best_dist = dist
                        best_cluster = ci
                new_labels.append(best_cluster)

            # Check convergence
            if new_labels == labels:
                break
            labels = new_labels

            # Update centroids
            for ci in range(len(centroids)):
                members = [embeddings[i] for i in range(n) if labels[i] == ci]
                if members:
                    centroids[ci] = [
                        sum(m[d] for m in members) / len(members)
                        for d in range(dim)
                    ]

        return labels, centroids


class DreamCycle:
    """The subconscious mind of the cortex.

    Runs dream cycles when idle, consolidating memories,
    finding patterns, and strengthening graph connections.
    """

    def __init__(self, memory_layer: Any, bus: Any = None) -> None:
        self._memory = memory_layer
        self._bus = bus
        self._last_activity = time.time()
        self._last_dream = 0.0
        self._dream_count = 0
        self._running = False
        self._task: asyncio.Task | None = None
        self._kmeans = KMeans()

    @property
    def dream_count(self) -> int:
        return self._dream_count

    def touch(self) -> None:
        """Mark activity — resets the idle timer."""
        self._last_activity = time.time()

    @property
    def idle_seconds(self) -> float:
        return time.time() - self._last_activity

    async def start(self, interval: float = 10.0) -> None:
        """Start the dream cycle background loop."""
        self._running = True
        self._task = asyncio.create_task(self._loop(interval))
        logger.info("Dream Cycle started")

    async def stop(self) -> None:
        """Stop the dream cycle."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Dream Cycle stopped")

    async def _loop(self, interval: float) -> None:
        """Background loop: dream when idle."""
        while self._running:
            await asyncio.sleep(interval)
            if self.idle_seconds >= IDLE_THRESHOLD_SECONDS:
                try:
                    report = await self.run()
                    if report.memories_sampled > 0:
                        logger.info(
                            f"Dream #{self._dream_count}: "
                            f"{report.memories_sampled} memories, "
                            f"{len(report.clusters)} clusters, "
                            f"{report.edges_strengthened} edges strengthened, "
                            f"{len(report.anomalies)} anomalies"
                        )
                except Exception as e:
                    logger.error(f"Dream cycle error: {e}")

    async def run(self) -> DreamReport:
        """Run a single dream cycle."""
        start = time.time()
        self._dream_count += 1
        self._last_dream = time.time()

        # 1. Sample random memories
        memories = await self._memory.get_random_memories(SAMPLE_SIZE)
        if not memories:
            return DreamReport(narrative="The cortex rests in silence. No memories to dream upon.")

        # Filter to those with embeddings
        embedded = [m for m in memories if m.embedding and len(m.embedding) > 0]
        if len(embedded) < 2:
            return DreamReport(
                memories_sampled=len(memories),
                narrative=f"A shallow dream. Only {len(embedded)} memories have form.",
            )

        report = DreamReport(memories_sampled=len(memories))

        # 2. K-means clustering
        embeddings = [m.embedding for m in embedded]
        n_clusters = min(N_CLUSTERS, len(embedded))
        kmeans = KMeans(n_clusters=n_clusters)
        labels, centroids = kmeans.fit(embeddings)

        clusters: list[DreamCluster] = []
        for ci in range(n_clusters):
            member_indices = [i for i, l in enumerate(labels) if l == ci]
            if not member_indices:
                continue
            members = [embedded[i] for i in member_indices]
            coherence = 0.0
            if centroids[ci]:
                sims = [_cosine_similarity(m.embedding, centroids[ci]) for m in members]
                coherence = sum(sims) / len(sims) if sims else 0.0

            # Find dominant tags
            tag_counts: dict[str, int] = {}
            for m in members:
                for t in m.tags:
                    tag_counts[t] = tag_counts.get(t, 0) + 1
            dominant = sorted(tag_counts, key=tag_counts.get, reverse=True)[:3]

            cluster = DreamCluster(
                centroid=centroids[ci],
                memory_ids=[m.id for m in members],
                coherence=coherence,
                dominant_tags=dominant,
            )
            clusters.append(cluster)

        report.clusters = clusters

        # 3. Find anomalies in recent data
        recent_since = time.time() - 3600  # last hour
        recent = await self._memory.get_recent_memories(recent_since, limit=100)
        anomalies = self._find_anomalies(recent)
        report.anomalies = anomalies

        # 4. Strengthen edges between memories in the same cluster
        edges_strengthened = 0
        if hasattr(self._memory, "strengthen_edge"):
            for cluster in clusters:
                ids = cluster.memory_ids
                for i in range(len(ids)):
                    for j in range(i + 1, len(ids)):
                        sim = _cosine_similarity(
                            self._get_embedding(embedded, ids[i]),
                            self._get_embedding(embedded, ids[j]),
                        )
                        if sim > 0.7:
                            await self._memory.strengthen_edge(
                                ids[i], ids[j], EDGE_STRENGTHEN_DELTA
                            )
                            edges_strengthened += 1
        report.edges_strengthened = edges_strengthened

        # 5. Generate narrative and emit dream event
        report.narrative = self._generate_narrative(report)
        report.duration_ms = (time.time() - start) * 1000

        if self._bus:
            event = CortexEvent.new(
                event_type="dream",
                source="dream-cycle",
                payload={
                    "dream_number": self._dream_count,
                    "clusters": len(clusters),
                    "anomalies": len(anomalies),
                    "edges_strengthened": edges_strengthened,
                    "memories_sampled": len(memories),
                    "narrative": report.narrative,
                    "duration_ms": report.duration_ms,
                },
                importance=0.3,
            )
            await self._bus.publish(event)

        return report

    def _find_anomalies(self, memories: list[Any]) -> list[DreamAnomaly]:
        """Find anomalous memories based on confidence distribution."""
        if len(memories) < 5:
            return []

        confidences = [m.effective_confidence for m in memories]
        n = len(confidences)
        mean = sum(confidences) / n
        var = sum((c - mean) ** 2 for c in confidences) / n
        std = math.sqrt(var) if var > 0 else 0.001

        anomalies = []
        for m in memories:
            conf = m.effective_confidence
            sigma = abs(conf - mean) / std
            if sigma > ANOMALY_SIGMA:
                anomalies.append(DreamAnomaly(
                    memory_id=m.id,
                    metric="confidence",
                    value=conf,
                    expected=mean,
                    sigma=sigma,
                ))
        return anomalies

    def _get_embedding(self, memories: list[Any], mid: str) -> list[float]:
        """Get embedding for a memory by ID from a list."""
        for m in memories:
            if m.id == mid:
                return m.embedding
        return []

    def _generate_narrative(self, report: DreamReport) -> str:
        """Generate atmospheric dream narrative."""
        parts = []

        if report.clusters:
            n_total = sum(len(c.memory_ids) for c in report.clusters)
            parts.append(f"Dreaming over {report.memories_sampled} memories")
            parts.append(f"into {len(report.clusters)} islands of thought")

            for i, cluster in enumerate(report.clusters):
                if cluster.dominant_tags:
                    tags_str = ", ".join(cluster.dominant_tags)
                    parts.append(
                        f"Island {i+1} hums with {tags_str} "
                        f"(coherence: {cluster.coherence:.2f})"
                    )

        if report.anomalies:
            parts.append(f"{len(report.anomalies)} memories drift like ghosts outside the pattern")

        if report.edges_strengthened:
            parts.append(f"{report.edges_strengthened} threads woven between kindred thoughts")

        if not parts:
            return "The cortex dreams in silence, tracing invisible patterns."

        narrative = ". ".join(parts) + "."
        return narrative

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "dream_count": self._dream_count,
            "last_dream": self._last_dream,
            "idle_seconds": self.idle_seconds,
        }


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _euclidean_distance(a: list[float], b: list[float]) -> float:
    """Euclidean distance between two vectors."""
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
