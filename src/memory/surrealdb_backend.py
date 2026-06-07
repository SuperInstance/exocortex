"""SurrealDB Memory Backend — replaces in-memory dicts with real SurrealDB queries.

Provides the same MemoryLayer interface but persists to SurrealDB with:
- SCHEMAFULL tables: memory, knowledge, agent
- Vector search via KNN for recall operations
- Half-life decay computed in queries
- Full graph edges between related memories

The backend is designed to be a drop-in replacement for the in-memory MemoryLayer.
When SurrealDB is unavailable, it gracefully falls back to the in-memory layer.
"""

from __future__ import annotations

import logging
import math
import time
import uuid
from collections import OrderedDict
from typing import Any

from . import MemoryLayer, LRU_MAX, HOT_WINDOW_SECONDS, WARM_UNREINFORCED_HOURS, COLD_CONFIDENCE_THRESHOLD

logger = logging.getLogger(__name__)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


class SurrealDBSchema:
    """SurrealDB table definitions for the exocortex memory system.

    SCHEMAFULL tables enforce strict typing for data integrity.
    """

    SCHEMA_SQL = """
    -- Core memory table: stores all memories with embeddings
    DEFINE TABLE memory SCHEMAFULL;
    DEFINE FIELD content ON memory TYPE string;
    DEFINE FIELD embedding ON memory TYPE array;
    DEFINE FIELD agent_id ON memory TYPE string;
    DEFINE FIELD confidence ON memory TYPE float DEFAULT 1.0;
    DEFINE FIELD created_at ON memory TYPE float;
    DEFINE FIELD last_reinforced ON memory TYPE float;
    DEFINE FIELD half_life_days ON memory TYPE float DEFAULT 30.0;
    DEFINE FIELD tags ON memory TYPE array DEFAULT [];
    DEFINE FIELD tier ON memory TYPE string DEFAULT 'warm';
    DEFINE FIELD provenance ON memory TYPE object DEFAULT {};

    -- Knowledge graph: links between memories
    DEFINE TABLE knowledge SCHEMAFULL;
    DEFINE FIELD source_id ON knowledge TYPE string;
    DEFINE FIELD target_id ON knowledge TYPE string;
    DEFINE FIELD relation ON knowledge TYPE string;
    DEFINE FIELD weight ON knowledge TYPE float DEFAULT 1.0;
    DEFINE FIELD created_at ON knowledge TYPE float;
    DEFINE FIELD reinforced_at ON knowledge TYPE float;

    -- Agent registry: connected agents and their metadata
    DEFINE TABLE agent SCHEMAFULL;
    DEFINE FIELD agent_id ON agent TYPE string;
    DEFINE FIELD protocol ON agent TYPE string;
    DEFINE FIELD capabilities ON agent TYPE array DEFAULT [];
    DEFINE FIELD last_seen ON agent TYPE float;
    DEFINE FIELD metadata ON agent TYPE object DEFAULT {};

    -- Vector index for KNN search (SurrealDB >= 2.0)
    DEFINE ANALYZER memory_embedding FN @embedding USING KNN {
        DIMENSIONS: 384,
        DISTANCE: COSINE
    };
    """

    # Indexes for common queries
    INDEX_SQL = """
    DEFINE INDEX idx_memory_agent ON memory COLUMNS agent_id;
    DEFINE INDEX idx_memory_tier ON memory COLUMNS tier;
    DEFINE INDEX idx_memory_tags ON memory COLUMNS tags;
    DEFINE INDEX idx_knowledge_source ON knowledge COLUMNS source_id;
    DEFINE INDEX idx_knowledge_target ON knowledge COLUMNS target_id;
    DEFINE INDEX idx_agent_id ON agent COLUMNS agent_id;
    """


class SurrealDBMemoryLayer(MemoryLayer):
    """SurrealDB-backed memory layer. Drop-in replacement for MemoryLayer.

    Falls back to in-memory dicts when SurrealDB is not available.
    Uses KNN vector search for recall when connected.
    """

    def __init__(
        self,
        url: str = "http://localhost:8000",
        namespace: str = "exocortex",
        database: str = "cortex",
        username: str = "root",
        password: str = "root",
    ) -> None:
        super().__init__()
        self._url = url
        self._namespace = namespace
        self._database = database
        self._username = username
        self._password = password
        self._db: Any = None
        self._connected = False
        self._schema_initialized = False

    async def connect(self) -> bool:
        """Connect to SurrealDB and initialize schema."""
        try:
            from surrealdb import Surreal

            self._db = Surreal(self._url)
            await self._db.signin({"user": self._username, "pass": self._password})
            await self._db.use(self._namespace, self._database)
            self._connected = True
            logger.info(f"Connected to SurrealDB at {self._url}")
            await self._init_schema()
            return True
        except ImportError:
            logger.warning("surrealdb package not installed, falling back to in-memory")
            self._connected = False
            return False
        except Exception as e:
            logger.warning(f"SurrealDB connection failed: {e}, falling back to in-memory")
            self._connected = False
            return False

    async def _init_schema(self) -> None:
        """Initialize SurrealDB schema (tables, indexes)."""
        if self._schema_initialized or not self._connected:
            return
        try:
            for stmt in SurrealDBSchema.SCHEMA_SQL.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    await self._db.query(stmt)
            for stmt in SurrealDBSchema.INDEX_SQL.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    await self._db.query(stmt)
            self._schema_initialized = True
            logger.info("SurrealDB schema initialized")
        except Exception as e:
            logger.warning(f"Schema init error (may already exist): {e}")
            self._schema_initialized = True  # Don't retry

    async def disconnect(self) -> None:
        """Disconnect from SurrealDB."""
        if self._db:
            try:
                await self._db.close()
            except Exception:
                pass
        self._connected = False
        self._db = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def remember(
        self,
        content: str,
        embedding: list[float],
        agent_id: str,
        tags: list[str] | None = None,
        **metadata: Any,
    ) -> Any:
        """Store a new memory in SurrealDB (and hot cache)."""
        # Always store in parent's in-memory layers as cache
        entry = await super().remember(content, embedding, agent_id, tags, **metadata)

        if self._connected:
            try:
                now = time.time()
                record = {
                    "content": content,
                    "embedding": embedding,
                    "agent_id": agent_id,
                    "confidence": 1.0,
                    "created_at": now,
                    "last_reinforced": now,
                    "half_life_days": 30.0,
                    "tags": tags or [],
                    "tier": "hot",
                    "provenance": {
                        "who": agent_id,
                        "when": now,
                        "how": "remember",
                    },
                }
                await self._db.create("memory", record)
                logger.debug(f"SurrealDB: stored memory '{content[:40]}...'")
            except Exception as e:
                logger.error(f"SurrealDB write error: {e}")

        return entry

    async def recall(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        min_confidence: float = 0.1,
    ) -> list[tuple[Any, float]]:
        """Recall memories using SurrealDB KNN vector search when available."""
        if self._connected:
            try:
                return await self._recall_knn(query_embedding, top_k, min_confidence)
            except Exception as e:
                logger.warning(f"KNN recall failed, falling back: {e}")

        # Fallback to in-memory
        return await super().recall(query_embedding, top_k, min_confidence)

    async def _recall_knn(
        self,
        query_embedding: list[float],
        top_k: int,
        min_confidence: float,
    ) -> list[tuple[Any, float]]:
        """Use SurrealDB KNN vector search for recall."""
        from ..core.types import MemoryEntry

        # SurrealDB KNN query with decay-adjusted confidence
        query = """
        SELECT *,
            confidence * exp(-0.693 * (time::now() - last_reinforced) / (half_life_days * 86400)) AS eff_conf,
            vector::similarity::cosine(embedding, $query_emb) AS similarity
        FROM memory
        WHERE confidence * exp(-0.693 * (time::now() - last_reinforced) / (half_life_days * 86400)) > $min_conf
        ORDER BY similarity DESC
        LIMIT $top_k
        """
        result = await self._db.query(
            query,
            {
                "query_emb": query_embedding,
                "min_conf": min_confidence,
                "top_k": top_k,
            },
        )

        entries: list[tuple[MemoryEntry, float]] = []
        if result and isinstance(result, list) and len(result) > 0:
            rows = result[0] if isinstance(result[0], list) else result[0].get("result", [])
            for row in rows:
                entry = MemoryEntry(
                    id=row.get("id", uuid.uuid4().hex[:16]),
                    content=row.get("content", ""),
                    embedding=row.get("embedding", []),
                    agent_id=row.get("agent_id", ""),
                    confidence=row.get("confidence", 1.0),
                    created_at=row.get("created_at", time.time()),
                    last_reinforced=row.get("last_reinforced", time.time()),
                    half_life_days=row.get("half_life_days", 30.0),
                    tags=row.get("tags", []),
                )
                similarity = row.get("similarity", 0.0)
                entries.append((entry, similarity))

        return entries

    async def query(self, tags: list[str], top_k: int = 10) -> list[Any]:
        """Tag-based query, SurrealDB-backed when connected."""
        if self._connected:
            try:
                return await self._query_tags(tags, top_k)
            except Exception as e:
                logger.warning(f"SurrealDB tag query failed, fallback: {e}")

        return await super().query(tags, top_k)

    async def _query_tags(self, tags: list[str], top_k: int) -> list[Any]:
        """Query by tags in SurrealDB."""
        from ..core.types import MemoryEntry

        query = """
        SELECT * FROM memory
        WHERE tags ANYINSIDE $tags
        ORDER BY confidence DESC
        LIMIT $top_k
        """
        result = await self._db.query(query, {"tags": tags, "top_k": top_k})

        entries = []
        if result and isinstance(result, list) and len(result) > 0:
            rows = result[0] if isinstance(result[0], list) else result[0].get("result", [])
            for row in rows:
                entry = MemoryEntry(
                    id=row.get("id", uuid.uuid4().hex[:16]),
                    content=row.get("content", ""),
                    embedding=row.get("embedding", []),
                    agent_id=row.get("agent_id", ""),
                    confidence=row.get("confidence", 1.0),
                    created_at=row.get("created_at", time.time()),
                    last_reinforced=row.get("last_reinforced", time.time()),
                    tags=row.get("tags", []),
                )
                entries.append(entry)
        return entries

    async def get(self, memory_id: str) -> Any | None:
        """Get by ID, SurrealDB-backed when connected."""
        if self._connected:
            try:
                result = await self._db.select(f"memory:{memory_id}")
                if result:
                    row = result[0] if isinstance(result, list) else result
                    from ..core.types import MemoryEntry
                    return MemoryEntry(
                        id=row.get("id", memory_id),
                        content=row.get("content", ""),
                        embedding=row.get("embedding", []),
                        agent_id=row.get("agent_id", ""),
                        confidence=row.get("confidence", 1.0),
                        created_at=row.get("created_at", time.time()),
                        last_reinforced=row.get("last_reinforced", time.time()),
                        tags=row.get("tags", []),
                    )
            except Exception as e:
                logger.warning(f"SurrealDB get failed, fallback: {e}")

        return await super().get(memory_id)

    async def tick(self) -> dict[str, int]:
        """Run cooling cycle. Moves tiers in SurrealDB + in-memory."""
        # Run in-memory tick first (cache layer)
        stats = await super().tick()

        if self._connected:
            try:
                now = time.time()
                # Hot → Warm: age > 60s
                await self._db.query("""
                    UPDATE memory SET tier = 'warm'
                    WHERE tier = 'hot'
                    AND last_reinforced < $cutoff
                """, {"cutoff": now - HOT_WINDOW_SECONDS})

                # Warm → Cold: unreinforced > 24h or low confidence
                await self._db.query("""
                    UPDATE memory SET tier = 'cold'
                    WHERE tier = 'warm'
                    AND (last_reinforced < $warm_cutoff
                         OR confidence * exp(-0.693 * (time::now() - last_reinforced) / (half_life_days * 86400)) < 0.1)
                """, {"warm_cutoff": now - WARM_UNREINFORCED_HOURS * 3600})

                # Prune: very low effective confidence
                await self._db.query("""
                    DELETE memory
                    WHERE tier = 'cold'
                    AND confidence * exp(-0.693 * (time::now() - last_reinforced) / (half_life_days * 86400)) < 0.05
                """)

            except Exception as e:
                logger.warning(f"SurrealDB tick error: {e}")

        return stats

    # --- Knowledge Graph Operations ---

    async def create_edge(
        self,
        source_id: str,
        target_id: str,
        relation: str = "related",
        weight: float = 1.0,
    ) -> None:
        """Create a knowledge graph edge between two memories."""
        if self._connected:
            try:
                now = time.time()
                await self._db.create("knowledge", {
                    "source_id": source_id,
                    "target_id": target_id,
                    "relation": relation,
                    "weight": weight,
                    "created_at": now,
                    "reinforced_at": now,
                })
            except Exception as e:
                logger.error(f"Failed to create edge: {e}")

    async def strengthen_edge(self, source_id: str, target_id: str, delta: float = 0.1) -> None:
        """Strengthen (increase weight of) an edge between memories."""
        if self._connected:
            try:
                await self._db.query("""
                    UPDATE knowledge SET weight = weight + $delta, reinforced_at = time::now()
                    WHERE source_id = $src AND target_id = $tgt
                """, {"src": source_id, "tgt": target_id, "delta": delta})
            except Exception as e:
                logger.error(f"Failed to strengthen edge: {e}")

    async def get_neighbors(self, memory_id: str, min_weight: float = 0.0) -> list[dict[str, Any]]:
        """Get neighboring memories via knowledge graph edges."""
        if not self._connected:
            return []
        try:
            result = await self._db.query("""
                SELECT * FROM knowledge
                WHERE (source_id = $mid OR target_id = $mid)
                AND weight >= $min_w
                ORDER BY weight DESC
            """, {"mid": memory_id, "min_w": min_weight})

            if result and isinstance(result, list) and len(result) > 0:
                rows = result[0] if isinstance(result[0], list) else result[0].get("result", [])
                return rows
            return []
        except Exception as e:
            logger.error(f"Failed to get neighbors: {e}")
            return []

    async def get_random_memories(self, n: int = 10) -> list[Any]:
        """Sample random memories for dream cycle processing."""
        if self._connected:
            try:
                from ..core.types import MemoryEntry

                result = await self._db.query("""
                    SELECT * FROM memory
                    ORDER BY RAND()
                    LIMIT $n
                """, {"n": n})

                entries = []
                if result and isinstance(result, list) and len(result) > 0:
                    rows = result[0] if isinstance(result[0], list) else result[0].get("result", [])
                    for row in rows:
                        entries.append(MemoryEntry(
                            id=row.get("id", ""),
                            content=row.get("content", ""),
                            embedding=row.get("embedding", []),
                            agent_id=row.get("agent_id", ""),
                            confidence=row.get("confidence", 1.0),
                            created_at=row.get("created_at", time.time()),
                            last_reinforced=row.get("last_reinforced", time.time()),
                            tags=row.get("tags", []),
                        ))
                return entries
            except Exception as e:
                logger.warning(f"SurrealDB random sample failed: {e}")

        # Fallback: sample from in-memory
        import random
        all_entries = list(self._warm.values()) + list(self._hot.values())
        return random.sample(all_entries, min(n, len(all_entries)))

    async def get_recent_memories(self, since: float, limit: int = 100) -> list[Any]:
        """Get memories created after a timestamp."""
        if self._connected:
            try:
                from ..core.types import MemoryEntry

                result = await self._db.query("""
                    SELECT * FROM memory
                    WHERE created_at >= $since
                    ORDER BY created_at DESC
                    LIMIT $limit
                """, {"since": since, "limit": limit})

                entries = []
                if result and isinstance(result, list) and len(result) > 0:
                    rows = result[0] if isinstance(result[0], list) else result[0].get("result", [])
                    for row in rows:
                        entries.append(MemoryEntry(
                            id=row.get("id", ""),
                            content=row.get("content", ""),
                            embedding=row.get("embedding", []),
                            agent_id=row.get("agent_id", ""),
                            confidence=row.get("confidence", 1.0),
                            created_at=row.get("created_at", time.time()),
                            last_reinforced=row.get("last_reinforced", time.time()),
                            tags=row.get("tags", []),
                        ))
                return entries
            except Exception as e:
                logger.warning(f"SurrealDB recent query failed: {e}")

        # Fallback from in-memory
        return [
            e for e in self._warm.values()
            if e.created_at >= since
        ][:limit]
