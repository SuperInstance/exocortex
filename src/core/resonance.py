"""Resonance Engine v1 — detects when agents' knowledge overlaps.

When Agent A learns something that overlaps with Agent B's active queries,
the resonance engine detects this and emits a "resonance" event on the
Cortical Bus. This enables serendipitous cross-agent knowledge sharing.

Algorithm:
- Track recent learning events per agent (content + embedding)
- Track active queries per agent (content + embedding)
- Compute cosine similarity between learning embeddings and query embeddings
- When overlap > threshold (default 0.8), emit "resonance" event
"""

from __future__ import annotations

import logging
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from ..core.types import CortexEvent

logger = logging.getLogger(__name__)

# Resonance parameters
RESONANCE_THRESHOLD = 0.8
MAX_LEARNING_PER_AGENT = 50
MAX_QUERIES_PER_AGENT = 20
LEARNING_TTL_SECONDS = 3600.0  # 1 hour


@dataclass
class LearningEvent:
    """A learning event from an agent."""
    agent_id: str
    content: str
    embedding: list[float]
    timestamp: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ActiveQuery:
    """An active query from an agent."""
    agent_id: str
    content: str
    embedding: list[float]
    timestamp: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResonanceHit:
    """A detected resonance between two agents."""
    source_agent: str
    target_agent: str
    learning_content: str
    query_content: str
    similarity: float
    timestamp: float = field(default_factory=time.time)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


class ResonanceEngine:
    """Detects cross-agent knowledge resonance.

    Tracks what agents are learning and what they're querying.
    When one agent's learning overlaps another's active query,
    a resonance event is emitted.
    """

    def __init__(
        self,
        bus: Any = None,
        threshold: float = RESONANCE_THRESHOLD,
    ) -> None:
        self._bus = bus
        self._threshold = threshold
        # Per-agent learning events
        self._learnings: dict[str, list[LearningEvent]] = defaultdict(list)
        # Per-agent active queries
        self._queries: dict[str, list[ActiveQuery]] = defaultdict(list)
        # Track resonances to avoid spamming
        self._recent_resonances: list[ResonanceHit] = []
        self._stats = {
            "learnings_tracked": 0,
            "queries_tracked": 0,
            "resonances_detected": 0,
        }

    def record_learning(
        self,
        agent_id: str,
        content: str,
        embedding: list[float],
        **metadata: Any,
    ) -> list[ResonanceHit]:
        """Record a learning event and check for resonances.

        Returns list of resonance hits detected.
        """
        event = LearningEvent(
            agent_id=agent_id,
            content=content,
            embedding=embedding,
            timestamp=time.time(),
            metadata=metadata,
        )
        self._learnings[agent_id].append(event)
        self._stats["learnings_tracked"] += 1

        # Trim to max
        if len(self._learnings[agent_id]) > MAX_LEARNING_PER_AGENT:
            self._learnings[agent_id] = self._learnings[agent_id][-MAX_LEARNING_PER_AGENT:]

        # Check against all other agents' active queries
        hits = self._check_resonances(event)
        return hits

    def record_query(
        self,
        agent_id: str,
        content: str,
        embedding: list[float],
        **metadata: Any,
    ) -> list[ResonanceHit]:
        """Record an active query and check for resonances.

        Returns list of resonance hits detected.
        """
        query = ActiveQuery(
            agent_id=agent_id,
            content=content,
            embedding=embedding,
            timestamp=time.time(),
            metadata=metadata,
        )
        self._queries[agent_id].append(query)
        self._stats["queries_tracked"] += 1

        # Trim to max
        if len(self._queries[agent_id]) > MAX_QUERIES_PER_AGENT:
            self._queries[agent_id] = self._queries[agent_id][-MAX_QUERIES_PER_AGENT:]

        # Check this query against all other agents' learnings
        hits = []
        for other_agent, learnings in self._learnings.items():
            if other_agent == agent_id:
                continue
            for learning in learnings:
                sim = _cosine_similarity(query.embedding, learning.embedding)
                if sim >= self._threshold:
                    hit = ResonanceHit(
                        source_agent=other_agent,
                        target_agent=agent_id,
                        learning_content=learning.content,
                        query_content=query.content,
                        similarity=sim,
                    )
                    hits.append(hit)
                    self._stats["resonances_detected"] += 1

        self._recent_resonances.extend(hits)
        # Keep only last 100
        self._recent_resonances = self._recent_resonances[-100:]
        return hits

    def _check_resonances(self, learning: LearningEvent) -> list[ResonanceHit]:
        """Check a learning event against all agents' active queries."""
        hits = []
        for agent_id, queries in self._queries.items():
            if agent_id == learning.agent_id:
                continue
            for query in queries:
                sim = _cosine_similarity(learning.embedding, query.embedding)
                if sim >= self._threshold:
                    hit = ResonanceHit(
                        source_agent=learning.agent_id,
                        target_agent=agent_id,
                        learning_content=learning.content,
                        query_content=query.content,
                        similarity=sim,
                    )
                    hits.append(hit)
                    self._stats["resonances_detected"] += 1

        self._recent_resonances.extend(hits)
        self._recent_resonances = self._recent_resonances[-100:]
        return hits

    async def emit_resonances(self, hits: list[ResonanceHit]) -> None:
        """Emit resonance events to the Cortical Bus."""
        if not self._bus or not hits:
            return
        for hit in hits:
            event = CortexEvent.new(
                event_type="resonance",
                source="resonance-engine",
                payload={
                    "source_agent": hit.source_agent,
                    "target_agent": hit.target_agent,
                    "learning_content": hit.learning_content,
                    "query_content": hit.query_content,
                    "similarity": hit.similarity,
                },
                importance=0.7,
                novelty=0.8,
            )
            await self._bus.publish(event)
            logger.info(
                f"Resonance: {hit.source_agent} → {hit.target_agent} "
                f"(sim={hit.similarity:.3f})"
            )

    def prune_stale(self, max_age: float = LEARNING_TTL_SECONDS) -> dict[str, int]:
        """Remove stale learning events and queries."""
        now = time.time()
        pruned_learnings = 0
        pruned_queries = 0

        for agent_id in list(self._learnings.keys()):
            before = len(self._learnings[agent_id])
            self._learnings[agent_id] = [
                e for e in self._learnings[agent_id]
                if now - e.timestamp < max_age
            ]
            pruned_learnings += before - len(self._learnings[agent_id])
            if not self._learnings[agent_id]:
                del self._learnings[agent_id]

        for agent_id in list(self._queries.keys()):
            before = len(self._queries[agent_id])
            self._queries[agent_id] = [
                q for q in self._queries[agent_id]
                if now - q.timestamp < max_age
            ]
            pruned_queries += before - len(self._queries[agent_id])
            if not self._queries[agent_id]:
                del self._queries[agent_id]

        return {"learnings_pruned": pruned_learnings, "queries_pruned": pruned_queries}

    @property
    def stats(self) -> dict[str, Any]:
        return {
            **self._stats,
            "active_agents_learning": len(self._learnings),
            "active_agents_querying": len(self._queries),
            "recent_resonances": len(self._recent_resonances),
            "threshold": self._threshold,
        }

    @property
    def recent_resonances(self) -> list[ResonanceHit]:
        return self._recent_resonances[-10:]
