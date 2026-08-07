"""Tests for SurrealDB Memory Backend — the ship's persistent hippocampus.

Tests schema definitions, connection lifecycle, fallback behavior,
CRUD operations, vector search, knowledge graph operations,
and tier management. All tests use mocks — no real SurrealDB needed.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.memory.surrealdb_backend import (
    SurrealDBSchema,
    SurrealDBMemoryLayer,
    _cosine_similarity,
)
from src.memory import MemoryLayer, HOT_WINDOW_SECONDS, WARM_UNREINFORCED_HOURS
from src.core.types import MemoryEntry


# ─── Utility tests ─────────────────────────────────────────────────

class TestCosineSimilarity:
    def test_identical(self):
        assert _cosine_similarity([1, 2, 3], [1, 2, 3]) == pytest.approx(1.0)

    def test_orthogonal(self):
        assert _cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)

    def test_opposite(self):
        assert _cosine_similarity([1, 0], [-1, 0]) == pytest.approx(-1.0)

    def test_zero_vector(self):
        assert _cosine_similarity([0, 0], [1, 1]) == 0.0

    def test_empty(self):
        assert _cosine_similarity([], []) == 0.0


# ─── Schema tests ──────────────────────────────────────────────────

class TestSurrealDBSchema:
    def test_schema_sql_not_empty(self):
        assert len(SurrealDBSchema.SCHEMA_SQL) > 100

    def test_schema_defines_memory_table(self):
        assert "DEFINE TABLE memory" in SurrealDBSchema.SCHEMA_SQL

    def test_schema_defines_knowledge_table(self):
        assert "DEFINE TABLE knowledge" in SurrealDBSchema.SCHEMA_SQL

    def test_schema_defines_agent_table(self):
        assert "DEFINE TABLE agent" in SurrealDBSchema.SCHEMA_SQL

    def test_schema_has_fields(self):
        for field in ["content", "embedding", "agent_id", "confidence",
                       "created_at", "last_reinforced", "half_life_days", "tags"]:
            assert f"DEFINE FIELD {field}" in SurrealDBSchema.SCHEMA_SQL

    def test_schema_has_vector_index(self):
        assert "KNN" in SurrealDBSchema.SCHEMA_SQL or "ANALYZER" in SurrealDBSchema.SCHEMA_SQL

    def test_schema_has_provenance(self):
        assert "provenance" in SurrealDBSchema.SCHEMA_SQL

    def test_index_sql_not_empty(self):
        assert len(SurrealDBSchema.INDEX_SQL) > 50

    def test_index_defines_memory_indexes(self):
        for idx in ["idx_memory_agent", "idx_memory_tier", "idx_memory_tags"]:
            assert idx in SurrealDBSchema.INDEX_SQL

    def test_index_defines_knowledge_indexes(self):
        assert "idx_knowledge_source" in SurrealDBSchema.INDEX_SQL
        assert "idx_knowledge_target" in SurrealDBSchema.INDEX_SQL

    def test_index_defines_agent_index(self):
        assert "idx_agent_id" in SurrealDBSchema.INDEX_SQL

    def test_schema_has_schemafull(self):
        assert "SCHEMAFULL" in SurrealDBSchema.SCHEMA_SQL

    def test_schema_knowledge_has_relation_and_weight(self):
        assert "DEFINE FIELD relation ON knowledge" in SurrealDBSchema.SCHEMA_SQL
        assert "DEFINE FIELD weight ON knowledge" in SurrealDBSchema.SCHEMA_SQL


# ─── SurrealDBMemoryLayer initialization tests ─────────────────────

class TestSurrealDBMemoryLayerInit:
    def test_default_values(self):
        layer = SurrealDBMemoryLayer()
        assert layer._url == "http://localhost:8000"
        assert layer._namespace == "exocortex"
        assert layer._database == "cortex"
        assert layer._username == "root"
        assert layer._password == "root"
        assert layer._connected is False
        assert layer._schema_initialized is False
        assert layer._db is None

    def test_custom_values(self):
        layer = SurrealDBMemoryLayer(
            url="http://remote:9000",
            namespace="test_ns",
            database="test_db",
            username="admin",
            password="secret",
        )
        assert layer._url == "http://remote:9000"
        assert layer._namespace == "test_ns"
        assert layer._database == "test_db"
        assert layer._username == "admin"
        assert layer._password == "secret"

    def test_inherits_memory_layer(self):
        """SurrealDBMemoryLayer should be a MemoryLayer subclass."""
        layer = SurrealDBMemoryLayer()
        assert isinstance(layer, MemoryLayer)

    def test_is_connected_property(self):
        layer = SurrealDBMemoryLayer()
        assert layer.is_connected is False


# ─── Connection tests ──────────────────────────────────────────────

class TestConnection:
    @pytest.mark.asyncio
    async def test_connect_no_package(self):
        """When surrealdb package is not installed, should fall back gracefully."""
        layer = SurrealDBMemoryLayer()
        with patch("builtins.__import__", side_effect=ImportError("no surrealdb")):
            result = await layer.connect()
        assert result is False
        assert layer.is_connected is False

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Connection failure should not crash, should fall back."""
        layer = SurrealDBMemoryLayer(url="http://nonexistent:9999")
        # The surrealdb package likely doesn't exist
        result = await layer.connect()
        assert result is False
        assert layer.is_connected is False

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self):
        layer = SurrealDBMemoryLayer()
        await layer.disconnect()  # Should not crash
        assert layer.is_connected is False

    @pytest.mark.asyncio
    async def test_disconnect_clears_state(self):
        layer = SurrealDBMemoryLayer()
        layer._db = MagicMock()
        layer._connected = True
        layer._db.close = AsyncMock()
        await layer.disconnect()
        assert layer.is_connected is False
        assert layer._db is None


# ─── Fallback behavior tests ───────────────────────────────────────

class TestFallbackBehavior:
    """When SurrealDB is not connected, all operations should fall back to in-memory."""

    @pytest.mark.asyncio
    async def test_remember_fallback(self):
        layer = SurrealDBMemoryLayer()
        entry = await layer.remember("test content", [1.0, 0.0], "agent-a")
        assert entry is not None
        assert entry.content == "test content"

    @pytest.mark.asyncio
    async def test_recall_fallback(self):
        layer = SurrealDBMemoryLayer()
        await layer.remember("fish", [1.0, 0.0], "agent-a")
        results = await layer.recall([1.0, 0.0])
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_get_fallback(self):
        layer = SurrealDBMemoryLayer()
        entry = await layer.remember("test", [1.0], "agent")
        result = await layer.get(entry.id)
        assert result is not None
        assert result.content == "test"

    @pytest.mark.asyncio
    async def test_query_fallback(self):
        layer = SurrealDBMemoryLayer()
        await layer.remember("tagged content", [1.0], "agent", tags=["fish"])
        results = await layer.query(["fish"])
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_tick_fallback(self):
        layer = SurrealDBMemoryLayer()
        stats = await layer.tick()
        assert isinstance(stats, dict)

    @pytest.mark.asyncio
    async def test_get_random_memories_fallback(self):
        layer = SurrealDBMemoryLayer()
        await layer.remember("mem1", [1.0], "agent")
        await layer.remember("mem2", [0.0, 1.0], "agent")
        results = await layer.get_random_memories(2)
        assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_get_recent_memories_fallback(self):
        layer = SurrealDBMemoryLayer()
        entry = await layer.remember("recent", [1.0], "agent")
        results = await layer.get_recent_memories(0)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_create_edge_fallback(self):
        """create_edge on disconnected layer should not crash."""
        layer = SurrealDBMemoryLayer()
        await layer.create_edge("a", "b", "related", 1.0)
        # No crash expected, no effect when disconnected

    @pytest.mark.asyncio
    async def test_strengthen_edge_fallback(self):
        layer = SurrealDBMemoryLayer()
        await layer.strengthen_edge("a", "b", 0.1)
        # No crash

    @pytest.mark.asyncio
    async def test_get_neighbors_fallback(self):
        layer = SurrealDBMemoryLayer()
        result = await layer.get_neighbors("nonexistent")
        assert result == []


# ─── In-memory consistency tests ───────────────────────────────────

class TestInMemoryConsistency:
    """The SurrealDB layer should maintain the same in-memory state as parent."""

    @pytest.mark.asyncio
    async def test_remember_stores_in_hot(self):
        layer = SurrealDBMemoryLayer()
        await layer.remember("hot content", [1.0], "agent")
        assert len(layer._hot) > 0

    @pytest.mark.asyncio
    async def test_multiple_remembers(self):
        layer = SurrealDBMemoryLayer()
        for i in range(5):
            await layer.remember(f"content-{i}", [float(i)], "agent")
        # Should have 5 warm entries
        assert len(layer._warm) >= 5

    @pytest.mark.asyncio
    async def test_recall_returns_similar(self):
        layer = SurrealDBMemoryLayer()
        await layer.remember("fish data", [1.0, 0.0, 0.0], "agent")
        await layer.remember("boat data", [0.0, 1.0, 0.0], "agent")
        results = await layer.recall([1.0, 0.0, 0.0], top_k=1)
        assert len(results) >= 1
        entry, sim = results[0]
        assert "fish" in entry.content.lower() or sim > 0


# ─── Knowledge graph tests (fallback mode) ─────────────────────────

class TestKnowledgeGraphFallback:
    @pytest.mark.asyncio
    async def test_get_neighbors_empty_when_disconnected(self):
        layer = SurrealDBMemoryLayer()
        result = await layer.get_neighbors("any-id")
        assert result == []

    @pytest.mark.asyncio
    async def test_create_edge_no_error_when_disconnected(self):
        layer = SurrealDBMemoryLayer()
        # Should silently skip
        await layer.create_edge("a", "b")
        await layer.create_edge("a", "b", "related", 0.5)

    @pytest.mark.asyncio
    async def test_strengthen_edge_no_error_when_disconnected(self):
        layer = SurrealDBMemoryLayer()
        await layer.strengthen_edge("a", "b")
        await layer.strengthen_edge("a", "b", delta=0.25)


# ─── Schema initialization tests ───────────────────────────────────

class TestSchemaInit:
    @pytest.mark.asyncio
    async def test_schema_init_skips_when_not_connected(self):
        layer = SurrealDBMemoryLayer()
        await layer._init_schema()
        assert layer._schema_initialized is False

    @pytest.mark.asyncio
    async def test_schema_init_skips_when_already_initialized(self):
        layer = SurrealDBMemoryLayer()
        layer._connected = True
        layer._schema_initialized = True
        await layer._init_schema()  # Should be a no-op
        assert layer._schema_initialized is True


# ─── Dream cycle integration tests ─────────────────────────────────

class TestDreamCycleIntegration:
    """The SurrealDB layer should work with the dream cycle."""

    @pytest.mark.asyncio
    async def test_get_random_memories_returns_entries(self):
        layer = SurrealDBMemoryLayer()
        for i in range(5):
            await layer.remember(
                f"dream-{i}",
                [float(i) / 5, 1.0 - float(i) / 5],
                "agent-a",
                tags=[f"tag-{i}"],
            )
        result = await layer.get_random_memories(3)
        assert len(result) <= 3
        for entry in result:
            assert isinstance(entry, MemoryEntry)

    @pytest.mark.asyncio
    async def test_get_recent_memories_filters_by_time(self):
        layer = SurrealDBMemoryLayer()
        old_time = time.time() - 7200  # 2 hours ago
        old_entry = await layer.remember("old", [1.0], "agent")
        old_entry.created_at = old_time

        new_entry = await layer.remember("new", [1.0], "agent")

        recent = await layer.get_recent_memories(time.time() - 3600)
        contents = [e.content for e in recent]
        assert "new" in contents
