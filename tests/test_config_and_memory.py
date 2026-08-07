"""
Tests for Configuration loader and Memory Layer.

Tests config parsing, duration parsing, defaults, and the three-tier
memory system (hot/warm/cold with LRU, decay, and similarity search).
"""

import time
import tempfile
import pytest
from pathlib import Path

from src.config import CortexConfig, _parse_duration_days
from src.memory import MemoryLayer
from src.core.types import MemoryEntry


# ─── Config: Duration Parsing ─────────────────────────────────────────────────

class TestParseDurationDays:
    def test_integer(self):
        assert _parse_duration_days(30) == 30.0

    def test_float(self):
        assert _parse_duration_days(30.5) == 30.5

    def test_string_number(self):
        assert _parse_duration_days("30") == 30.0

    def test_string_with_d_suffix(self):
        assert _parse_duration_days("30d") == 30.0

    def test_string_with_days_suffix(self):
        assert _parse_duration_days("30days") == 30.0

    def test_string_with_day_suffix(self):
        assert _parse_duration_days("1day") == 1.0

    def test_string_with_float_and_d(self):
        assert _parse_duration_days("30.5d") == 30.5

    def test_string_with_spaces(self):
        assert _parse_duration_days("  30d  ") == 30.0

    def test_case_insensitive_suffix(self):
        assert _parse_duration_days("30D") == 30.0
        assert _parse_duration_days("30DAYS") == 30.0


# ─── Config: CortexConfig ─────────────────────────────────────────────────────

class TestCortexConfig:
    def test_defaults(self):
        cfg = CortexConfig()
        assert cfg.name == "default-cortex"
        assert cfg.memory_backend == "memory"
        assert cfg.memory_retention_days == 30.0
        assert cfg.embedding_dims == 384
        assert cfg.host == "0.0.0.0"
        assert cfg.port == 9000
        assert cfg.default_shadow_mode == "stream"
        assert cfg.dream_idle_seconds == 30.0

    def test_default_cors(self):
        cfg = CortexConfig()
        assert cfg.rest_cors_origins == ["*"]

    def test_default_protocols_enabled(self):
        cfg = CortexConfig()
        assert cfg.a2a_enabled is True
        assert cfg.mcp_enabled is True

    def test_lru_max_default(self):
        cfg = CortexConfig()
        assert cfg.lru_max == 500

    def test_load_nonexistent_file_returns_defaults(self):
        cfg = CortexConfig.load("/nonexistent/path.toml")
        assert cfg.name == "default-cortex"

    def test_load_valid_toml(self):
        toml_content = b"""
[cortex]
name = "test-cortex"

[memory]
backend = "surrealdb"
retention = "60d"
embedding_dims = 768

[compute]
default_model = "custom"
max_training_ms = 10000.0

[server]
host = "127.0.0.1"
port = 8080

[tui]
default_shadow_mode = "focus"
dream_idle_seconds = 60.0
"""
        with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
            f.write(toml_content)
            f.flush()
            cfg = CortexConfig.load(f.name)

        assert cfg.name == "test-cortex"
        assert cfg.memory_backend == "surrealdb"
        assert cfg.memory_retention_days == 60.0
        assert cfg.embedding_dims == 768
        assert cfg.default_model == "custom"
        assert cfg.max_training_ms == 10000.0
        assert cfg.host == "127.0.0.1"
        assert cfg.port == 8080
        assert cfg.default_shadow_mode == "focus"
        assert cfg.dream_idle_seconds == 60.0

    def test_load_partial_toml_uses_defaults(self):
        toml_content = b"""
[cortex]
name = "partial"
"""
        with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
            f.write(toml_content)
            f.flush()
            cfg = CortexConfig.load(f.name)

        assert cfg.name == "partial"
        assert cfg.memory_backend == "memory"  # default
        assert cfg.port == 9000  # default


# ─── Memory Layer Tests ───────────────────────────────────────────────────────

class TestMemoryLayer:
    """Test the three-tier memory system."""

    def test_init_empty(self):
        ml = MemoryLayer()
        assert len(ml._hot) == 0
        assert len(ml._warm) == 0
        assert len(ml._cold) == 0

    @pytest.mark.asyncio
    async def test_remember_creates_entry(self):
        ml = MemoryLayer()
        entry = await ml.remember("test content", [1.0, 0.0], "agent_1")
        assert entry.content == "test content"
        assert entry.embedding == [1.0, 0.0]
        assert entry.agent_id == "agent_1"
        assert entry.id in ml._hot
        assert entry.id in ml._warm

    @pytest.mark.asyncio
    async def test_remember_with_tags(self):
        ml = MemoryLayer()
        entry = await ml.remember("tagged", [1.0], "a1", tags=["important", "test"])
        assert "important" in entry.tags
        assert "test" in entry.tags

    @pytest.mark.asyncio
    async def test_remember_default_tags_empty(self):
        ml = MemoryLayer()
        entry = await ml.remember("no tags", [1.0], "a1")
        assert entry.tags == []

    @pytest.mark.asyncio
    async def test_remember_stores_embedding(self):
        ml = MemoryLayer()
        entry = await ml.remember("test", [0.5, 0.5], "a1")
        assert ml._embed_cache[entry.id] == [0.5, 0.5]

    @pytest.mark.asyncio
    async def test_recall_finds_similar(self):
        ml = MemoryLayer()
        await ml.remember("cat", [1.0, 0.0], "a1")
        await ml.remember("dog", [0.0, 1.0], "a1")
        results = await ml.recall([1.0, 0.0], top_k=1)
        assert len(results) == 1
        assert results[0][0].content == "cat"
        assert results[0][1] > 0.99  # cosine similarity

    @pytest.mark.asyncio
    async def test_recall_top_k(self):
        ml = MemoryLayer()
        await ml.remember("a", [1.0, 0.0], "a1")
        await ml.remember("b", [0.9, 0.1], "a1")
        await ml.remember("c", [0.0, 1.0], "a1")
        results = await ml.recall([1.0, 0.0], top_k=2)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_recall_empty_returns_empty(self):
        ml = MemoryLayer()
        results = await ml.recall([1.0], top_k=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_recall_min_confidence_filters_decayed(self):
        """min_confidence filters by effective_confidence (decay), not similarity."""
        ml = MemoryLayer()
        # Fresh memory with high confidence
        await ml.remember("fresh", [1.0, 0.0], "a1")
        # Create a memory and manually decay it below threshold
        old_entry = await ml.remember("decayed", [0.0, 1.0], "a1")
        old_entry.confidence = 0.05  # Very low confidence
        # min_confidence=0.1 should filter out the decayed one
        results = await ml.recall([1.0, 0.0], top_k=5, min_confidence=0.1)
        contents = [r[0].content for r in results]
        assert "fresh" in contents
        assert "decayed" not in contents

    @pytest.mark.asyncio
    async def test_lru_eviction_on_hot(self):
        """When hot tier exceeds LRU_MAX, oldest should be evicted."""
        ml = MemoryLayer()
        from src.memory import LRU_MAX
        for i in range(LRU_MAX + 10):
            await ml.remember(f"item_{i}", [float(i)], "a1")
        assert len(ml._hot) == LRU_MAX
        # First 10 items should be evicted from hot
        for i in range(10):
            assert f"item_{i}" not in [e.content for e in ml._hot.values()]

    @pytest.mark.asyncio
    async def test_get_by_id(self):
        ml = MemoryLayer()
        entry = await ml.remember("find me", [1.0], "a1")
        result = await ml.get(entry.id)
        assert result is not None
        assert result.content == "find me"

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self):
        ml = MemoryLayer()
        result = await ml.get("nonexistent_id")
        assert result is None

    @pytest.mark.asyncio
    async def test_stats_empty(self):
        ml = MemoryLayer()
        stats = ml.stats  # stats is a property
        assert isinstance(stats, dict)
        assert stats["hot"] == 0
        assert stats["warm"] == 0
        assert stats["cold"] == 0
        assert stats["total"] == 0

    @pytest.mark.asyncio
    async def test_stats_after_inserts(self):
        ml = MemoryLayer()
        await ml.remember("a", [1.0], "a1")
        await ml.remember("b", [0.5], "a1")
        stats = ml.stats
        assert stats["warm"] == 2
        assert stats["total"] >= 2

    @pytest.mark.asyncio
    async def test_reinforce_on_recall(self):
        """Recalling a memory should reinforce it (update last_reinforced)."""
        ml = MemoryLayer()
        entry = await ml.remember("important", [1.0, 0.0], "a1")
        old_reinforced = entry.last_reinforced
        time.sleep(0.01)
        results = await ml.recall([1.0, 0.0], top_k=1)
        assert len(results) == 1
        # The entry object should have been reinforced
        assert results[0][0].last_reinforced >= old_reinforced

    @pytest.mark.asyncio
    async def test_different_agents_separate_memories(self):
        ml = MemoryLayer()
        await ml.remember("agent_a_memory", [1.0, 0.0], "agent_a")
        await ml.remember("agent_b_memory", [1.0, 0.0], "agent_b")
        results = await ml.recall([1.0, 0.0], top_k=5)
        agents = [r[0].agent_id for r in results]
        assert "agent_a" in agents
        assert "agent_b" in agents

    @pytest.mark.asyncio
    async def test_high_dimensional_embeddings(self):
        ml = MemoryLayer()
        import random
        for i in range(20):
            emb = [random.random() for _ in range(384)]
            await ml.remember(f"vec_{i}", emb, "a1")
        query = [0.5] * 384
        results = await ml.recall(query, top_k=5)
        assert len(results) <= 5
        assert len(results) > 0


class TestMemoryLayerAdvanced:
    """Test query, tick, random sampling, and recent memories."""

    @pytest.mark.asyncio
    async def test_query_by_tags(self):
        ml = MemoryLayer()
        await ml.remember("important data", [1.0], "a1", tags=["urgent"])
        await ml.remember("other data", [0.5], "a1", tags=["casual"])
        results = await ml.query(["urgent"], top_k=10)
        assert len(results) == 1
        assert results[0].content == "important data"

    @pytest.mark.asyncio
    async def test_query_multiple_tags_any_match(self):
        ml = MemoryLayer()
        await ml.remember("a", [1.0], "a1", tags=["x"])
        await ml.remember("b", [0.5], "a1", tags=["y"])
        await ml.remember("c", [0.3], "a1", tags=["z"])
        results = await ml.query(["x", "y"], top_k=10)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_query_no_match(self):
        ml = MemoryLayer()
        await ml.remember("a", [1.0], "a1", tags=["x"])
        results = await ml.query(["nonexistent"], top_k=10)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_tick_cools_hot_to_warm(self):
        ml = MemoryLayer()
        entry = await ml.remember("test", [1.0], "a1")
        entry.last_reinforced = time.time() - 120
        stats = await ml.tick()
        assert stats["cooled_to_warm"] >= 1
        assert entry.id not in ml._hot

    @pytest.mark.asyncio
    async def test_tick_returns_stats_dict(self):
        ml = MemoryLayer()
        stats = await ml.tick()
        assert "hot" in stats
        assert "warm" in stats
        assert "cold" in stats
        assert "cooled_to_warm" in stats

    @pytest.mark.asyncio
    async def test_get_random_memories(self):
        ml = MemoryLayer()
        for i in range(10):
            await ml.remember(f"item_{i}", [float(i) / 10], "a1")
        results = await ml.get_random_memories(n=3)
        assert len(results) == 3
        ids = [e.id for e in results]
        assert len(set(ids)) == 3

    @pytest.mark.asyncio
    async def test_get_random_memories_empty(self):
        ml = MemoryLayer()
        results = await ml.get_random_memories(n=5)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_get_recent_memories(self):
        ml = MemoryLayer()
        now = time.time()
        entry = await ml.remember("recent", [1.0], "a1")
        old_entry = await ml.remember("old", [0.5], "a1")
        old_entry.created_at = now - 3600
        results = await ml.get_recent_memories(since=now - 60)
        contents = [e.content for e in results]
        assert "recent" in contents
        assert "old" not in contents


class TestCosineSimilarity:
    def test_identical_vectors(self):
        from src.memory import _cosine_similarity
        assert abs(_cosine_similarity([1, 0], [1, 0]) - 1.0) < 0.001

    def test_orthogonal_vectors(self):
        from src.memory import _cosine_similarity
        assert abs(_cosine_similarity([1, 0], [0, 1]) - 0.0) < 0.001

    def test_opposite_vectors(self):
        from src.memory import _cosine_similarity
        assert abs(_cosine_similarity([1, 0], [-1, 0]) - (-1.0)) < 0.001

    def test_zero_vector_returns_zero(self):
        from src.memory import _cosine_similarity
        assert _cosine_similarity([0, 0], [1, 0]) == 0.0

    def test_45_degrees(self):
        from src.memory import _cosine_similarity
        import math
        sim = _cosine_similarity([1, 0], [1, 1])
        assert abs(sim - math.cos(math.pi / 4)) < 0.001
