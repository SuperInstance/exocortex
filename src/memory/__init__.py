"""Memory Layer — SurrealDB-backed storage with hot/warm/cold tiers.

For v1, uses in-memory dicts as SurrealDB stand-in. Swap to real SurrealDB later.
"""

from __future__ import annotations

import logging
import math
import time
from collections import OrderedDict
from typing import Any

from ..core.types import MemoryEntry, Operation

logger = logging.getLogger(__name__)

# Tier thresholds
HOT_WINDOW_SECONDS = 60.0
WARM_UNREINFORCED_HOURS = 24.0
COLD_CONFIDENCE_THRESHOLD = 0.1
LRU_MAX = 500


class MemoryLayer:
    """Three-tier memory: Hot (LRU) → Warm (active) → Cold (archive).

    Every memory has a half-life. Confidence decays. Recall reinforces.
    """

    def __init__(self) -> None:
        # Hot tier: in-memory LRU
        self._hot: OrderedDict[str, MemoryEntry] = OrderedDict()
        # Warm tier: all active memories (would be SurrealDB in production)
        self._warm: dict[str, MemoryEntry] = {}
        # Cold tier: archived (compressed, rarely accessed)
        self._cold: dict[str, MemoryEntry] = {}
        # Embedding cache for fast similarity
        self._embed_cache: OrderedDict[str, list[float]] = OrderedDict()

    async def remember(
        self,
        content: str,
        embedding: list[float],
        agent_id: str,
        tags: list[str] | None = None,
        **metadata: Any,
    ) -> MemoryEntry:
        """Store a new memory. Goes into hot + warm."""
        entry = MemoryEntry(
            content=content,
            embedding=embedding,
            agent_id=agent_id,
            tags=tags or [],
        )
        # Hot tier
        self._hot[entry.id] = entry
        if len(self._hot) > LRU_MAX:
            self._hot.popitem(last=False)  # evict oldest
        # Warm tier
        self._warm[entry.id] = entry
        # Embedding cache
        self._embed_cache[entry.id] = embedding
        if len(self._embed_cache) > LRU_MAX:
            self._embed_cache.popitem(last=False)

        logger.debug(f"Remembered: {content[:40]}... ({entry.id})")
        return entry

    async def recall(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        min_confidence: float = 0.1,
    ) -> list[tuple[MemoryEntry, float]]:
        """Find similar memories by embedding cosine similarity."""
        results: list[tuple[MemoryEntry, float]] = []

        for mid, emb in self._embed_cache.items():
            # Check all tiers
            entry = self._hot.get(mid) or self._warm.get(mid) or self._cold.get(mid)
            if not entry:
                continue
            eff_conf = entry.effective_confidence
            if eff_conf < min_confidence:
                continue
            sim = _cosine_similarity(query_embedding, emb)
            results.append((entry, sim))

        # Sort by similarity descending
        results.sort(key=lambda x: x[1], reverse=True)

        # Reinforce recalled memories (bumps last_reinforced)
        for entry, _ in results[:top_k]:
            entry.reinforce()

        return results[:top_k]

    async def query(self, tags: list[str], top_k: int = 10) -> list[MemoryEntry]:
        """Tag-based query."""
        results = []
        for entry in self._warm.values():
            if any(t in entry.tags for t in tags):
                results.append(entry)
        results.sort(key=lambda e: e.effective_confidence, reverse=True)
        return results[:top_k]

    async def get(self, memory_id: str) -> MemoryEntry | None:
        """Get by ID (checks all tiers, reheats if found)."""
        entry = self._hot.get(memory_id)
        if entry:
            return entry
        entry = self._warm.get(memory_id)
        if entry:
            # Reheat to hot
            self._hot[memory_id] = entry
            return entry
        entry = self._cold.get(memory_id)
        if entry:
            # Reheat cold → hot
            self._hot[memory_id] = entry
            return entry
        return None

    async def tick(self) -> dict[str, int]:
        """Run cooling cycle. Move hot→warm→cold based on age and confidence."""
        now = time.time()
        cooled_to_warm = 0
        cooled_to_cold = 0
        pruned = 0

        # Hot → Warm (age > 60s)
        to_cool = [
            mid for mid, e in self._hot.items()
            if now - e.last_reinforced > HOT_WINDOW_SECONDS
        ]
        for mid in to_cool:
            del self._hot[mid]
            cooled_to_warm += 1

        # Warm → Cold (unreinforced > 24h or low confidence)
        to_archive = [
            mid for mid, e in self._warm.items()
            if (
                now - e.last_reinforced > WARM_UNREINFORCED_HOURS * 3600
                or e.effective_confidence < COLD_CONFIDENCE_THRESHOLD
            )
        ]
        for mid in to_archive:
            entry = self._warm.pop(mid)
            self._cold[mid] = entry
            cooled_to_cold += 1

        # Prune cold (confidence < 0.05)
        to_prune = [
            mid for mid, e in self._cold.items()
            if e.effective_confidence < 0.05
        ]
        for mid in to_prune:
            del self._cold[mid]
            self._embed_cache.pop(mid, None)
            pruned += 1

        stats = {
            "hot": len(self._hot),
            "warm": len(self._warm),
            "cold": len(self._cold),
            "cooled_to_warm": cooled_to_warm,
            "cooled_to_cold": cooled_to_cold,
            "pruned": pruned,
        }
        if cooled_to_cold or pruned:
            logger.info(f"Memory tick: {stats}")
        return stats

    @property
    def stats(self) -> dict[str, int]:
        return {
            "hot": len(self._hot),
            "warm": len(self._warm),
            "cold": len(self._cold),
            "total": len(self._hot) + len(self._warm) + len(self._cold),
        }


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)
