"""
Tests for mentis_adapter.py — the integration point between Mentis and the thinker.
"""

import sys
import os
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mentis_adapter import MentisAdapter
from mental_state import MentalState, AgentMentalState


# ─── Fixtures ──────────────────────────────────────────────────

def make_game_state(bond=3, build="tower", pos=None):
    return {
        "position": pos or {"x": 10.0, "y": 5.0, "z": -20.0},
        "nearby": ["dock", "workshop"],
        "time_of_day": "midday",
        "weather": "clear",
        "last_build": build,
        "bond_level": bond,
        "available_material": "wood",
    }


# ─── MentisAdapter Tests ───────────────────────────────────────


class TestMentisAdapterBasic:
    def test_creation(self):
        adapter = MentisAdapter(use_llm=False)
        assert adapter.use_llm is False
        assert adapter.max_branches == 3

    def test_creation_with_llm(self):
        adapter = MentisAdapter(use_llm=True)
        assert adapter.use_llm is True

    def test_initial_state_empty(self):
        adapter = MentisAdapter(use_llm=False)
        ms = adapter._mental_state
        assert ms.is_empty()


class TestMentalStateParsing:
    def test_first_call_renders(self):
        adapter = MentisAdapter(use_llm=False)
        gs = make_game_state(bond=3)
        ms = adapter.get_mental_state(gs)
        assert not ms.is_empty()
        assert ms.source == "re-rendered"
        assert len(ms.agents) >= 1

    def test_second_call_uses_cache(self):
        adapter = MentisAdapter(use_llm=False)
        gs = make_game_state(bond=3)

        # First call: cache miss
        ms1 = adapter.get_mental_state(gs)
        assert ms1.source == "re-rendered"

        # Second call: same state → cache hit
        ms2 = adapter.get_mental_state(gs)
        assert ms2.source == "cached"
        # Should be the same object (cached)
        assert ms2 is ms1

    def test_changed_state_re_renders(self):
        adapter = MentisAdapter(use_llm=False)
        gs1 = make_game_state(bond=3)
        gs2 = make_game_state(bond=4)  # bond changed

        ms1 = adapter.get_mental_state(gs1)
        assert ms1.source == "re-rendered"

        ms2 = adapter.get_mental_state(gs2)
        assert ms2.source == "re-rendered"

    def test_heuristic_parses_captain(self):
        adapter = MentisAdapter(use_llm=False)
        gs = make_game_state(build="tower")
        ms = adapter.get_mental_state(gs)

        captain = None
        for agent in ms.agents:
            if agent.role == "captain":
                captain = agent
                break

        assert captain is not None
        assert len(captain.emotions) > 0
        assert captain.goals  # should have building goal

    def test_atmosphere_reflects_context(self):
        adapter = MentisAdapter(use_llm=False)
        gs = make_game_state()
        gs["weather"] = "storm"
        ms = adapter.get_mental_state(gs)
        assert ms.atmosphere == "tense"

    def test_bond_reflects_trust(self):
        adapter = MentisAdapter(use_llm=False)
        gs = make_game_state(bond=5)
        ms = adapter.get_mental_state(gs)

        assert len(ms.relations) > 0
        assert ms.relations[0].trust_level >= 0.9


class TestObservationRendering:
    def test_observation_has_agents(self):
        adapter = MentisAdapter(use_llm=False)
        gs = make_game_state(bond=3)
        adapter.get_mental_state(gs)
        obs = adapter.get_observation()
        assert "Captain" in obs.visible_agents

    def test_observation_has_actions(self):
        adapter = MentisAdapter(use_llm=False)
        gs = make_game_state(build="tower")
        adapter.get_mental_state(gs)
        obs = adapter.get_observation()
        assert any("build" in a for a in obs.visible_actions)


class TestContextEnrichment:
    def test_build_mental_context(self):
        adapter = MentisAdapter(use_llm=False)
        gs = make_game_state(bond=3, build="tower")
        ms = adapter.get_mental_state(gs)
        ctx = adapter.build_mental_context(ms, gs)

        assert "Social Context" in ctx or "Captain" in ctx

    def test_empty_mental_context(self):
        adapter = MentisAdapter(use_llm=False)
        ms = MentalState()  # empty
        gs = make_game_state()
        ctx = adapter.build_mental_context(ms, gs)
        assert ctx == ""

    def test_enrich_context_inserts_before_your_turn(self):
        adapter = MentisAdapter(use_llm=False)
        physical = "## Current State\nPosition: here\n\n## Your Turn\nWhat do you do?"
        mental = "## Social Context\nCaptain is focused."
        enriched = adapter.enrich_context(physical, mental)
        idx_social = enriched.index("Social Context")
        idx_turn = enriched.index("Your Turn")
        assert idx_social < idx_turn

    def test_enrich_context_appends_when_no_your_turn(self):
        adapter = MentisAdapter(use_llm=False)
        physical = "Some context without your turn section."
        mental = "## Social Context\nCaptain is calm."
        enriched = adapter.enrich_context(physical, mental)
        assert "Social Context" in enriched
        assert enriched.endswith(mental) or "Social Context" in enriched

    def test_enrich_context_empty_mental(self):
        adapter = MentisAdapter(use_llm=False)
        physical = "Some context."
        enriched = adapter.enrich_context(physical, "")
        assert enriched == physical


class TestBranchSimulation:
    def test_simulate_branches(self):
        adapter = MentisAdapter(use_llm=False)
        gs = make_game_state(bond=3, build="tower")
        adapter.get_mental_state(gs)

        actions = [
            {"type": "explore"},
            {"type": "build", "params": {}},
            {"type": "wait"},
        ]
        branches = adapter.simulate_branches(actions, bond_level=3)
        assert len(branches) > 0
        assert all(not b.failed for b in branches)

    def test_select_best_action(self):
        adapter = MentisAdapter(use_llm=False)
        gs = make_game_state(bond=3, build="tower")
        adapter.get_mental_state(gs)

        actions = [
            {"type": "wait"},
            {"type": "build", "params": {}},
        ]
        branches = adapter.simulate_branches(actions, bond_level=3)
        best = adapter.select_best_action(branches)
        assert best is not None
        assert "type" in best
        assert "scores" in best

    def test_build_during_focused_captain_wins(self):
        """When captain is focused on building, build should be selected over wait."""
        adapter = MentisAdapter(use_llm=False)
        gs = make_game_state(bond=3, build="tower")
        adapter.get_mental_state(gs)

        actions = [
            {"type": "wait"},
            {"type": "build", "params": {}},
        ]
        branches = adapter.simulate_branches(actions, bond_level=3)
        best = adapter.select_best_action(branches)
        assert best["type"] == "build"


class TestReflexExtension:
    def test_build_reflex_extension(self):
        adapter = MentisAdapter(use_llm=False)
        gs = make_game_state(bond=3, build="tower")
        ms = adapter.get_mental_state(gs)

        ext = adapter.build_reflex_extension(ms)
        assert "mental_match_key" in ext
        assert "mental_keywords" in ext
        assert "mental_embedding" in ext
        assert len(ext["mental_embedding"]) == 384

    def test_mental_match_key_not_empty(self):
        adapter = MentisAdapter(use_llm=False)
        gs = make_game_state()
        ms = adapter.get_mental_state(gs)
        ext = adapter.build_reflex_extension(ms)
        assert ext["mental_match_key"]  # non-empty
        assert "mental=unknown" not in ext["mental_match_key"]


class TestStats:
    def test_stats_after_creation(self):
        adapter = MentisAdapter(use_llm=False)
        stats = adapter.get_stats()
        assert stats["ticks"] == 0
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert stats["use_llm"] is False

    def test_stats_after_ticks(self):
        adapter = MentisAdapter(use_llm=False)
        gs = make_game_state(bond=3)

        # First tick: cache miss
        adapter.get_mental_state(gs)
        assert adapter.get_stats()["ticks"] == 1
        assert adapter.get_stats()["cache_misses"] == 1
        assert adapter.get_stats()["cache_hits"] == 0

        # Second tick (same state): cache hit
        adapter.get_mental_state(gs)
        assert adapter.get_stats()["ticks"] == 2
        assert adapter.get_stats()["cache_hits"] == 1

    def test_cache_hit_rate(self):
        adapter = MentisAdapter(use_llm=False)
        gs = make_game_state()

        # 1 miss + 4 hits = 80% hit rate
        for _ in range(5):
            adapter.get_mental_state(gs)

        stats = adapter.get_stats()
        assert stats["cache_hit_rate"] == 0.8


class TestSocialGuidance:
    def test_focused_captain_guidance(self):
        adapter = MentisAdapter(use_llm=False)
        gs = make_game_state(bond=3, build="tower")
        ms = adapter.get_mental_state(gs)
        ctx = adapter.build_mental_context(ms, gs)
        # Should contain guidance about focused captain
        assert "focused" in ctx.lower() or "help" in ctx.lower() or "task" in ctx.lower()

    def test_storm_atmosphere(self):
        adapter = MentisAdapter(use_llm=False)
        gs = make_game_state()
        gs["weather"] = "storm"
        ms = adapter.get_mental_state(gs)
        assert ms.atmosphere == "tense"

    def test_golden_hour_atmosphere(self):
        adapter = MentisAdapter(use_llm=False)
        gs = make_game_state()
        gs["time_of_day"] = "golden_hour"
        gs["last_build"] = "none"
        ms = adapter.get_mental_state(gs)
        assert ms.atmosphere == "contemplative"
