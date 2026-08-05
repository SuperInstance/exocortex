"""
Tests for mental_state.py — mental state representation and social delta detection.
"""

import json
import sys
import os
import time

import pytest

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mental_state import (
    AgentMentalState,
    MentalState,
    SocialRelation,
    SocialDeltaDetector,
    PartialObservation,
    build_mental_signature,
    build_mental_keywords,
    embed_mental_state,
    embed_hash_text,
)


# ─── Fixtures ──────────────────────────────────────────────────

def make_captain_mood(emotions: list[str], goals: list[str] = None) -> AgentMentalState:
    return AgentMentalState(
        name="Captain",
        role="captain",
        emotions=emotions,
        goals=goals or [],
        attention_focus="building tower",
    )


def make_mental_state(emotions=None, goals=None, atmosphere="neutral") -> MentalState:
    captain = make_captain_mood(emotions or ["neutral"], goals or [])
    return MentalState(
        agents=[captain],
        atmosphere=atmosphere,
        timestamp="2026-08-04T12:00:00Z",
    )


def make_game_state(bond=3, build="tower", nearby=None) -> dict:
    return {
        "position": {"x": 10.0, "y": 5.0, "z": -20.0},
        "nearby": nearby or ["dock", "workshop"],
        "time_of_day": "midday",
        "weather": "clear",
        "last_build": build,
        "bond_level": bond,
        "available_material": "wood",
    }


# ─── AgentMentalState Tests ────────────────────────────────────


class TestAgentMentalState:
    def test_creation(self):
        agent = AgentMentalState(name="Captain", role="captain", emotions=["happy"])
        assert agent.name == "Captain"
        assert agent.role == "captain"
        assert agent.emotions == ["happy"]

    def test_to_dict_roundtrip(self):
        agent = AgentMentalState(
            name="Wesley", role="ensign",
            beliefs=["the dock is sturdy"],
            goals=["explore", "assist"],
            emotions=["curious"],
        )
        d = agent.to_dict()
        restored = AgentMentalState.from_dict(d)
        assert restored.name == "Wesley"
        assert restored.goals == ["explore", "assist"]
        assert restored.emotions == ["curious"]

    def test_defaults(self):
        agent = AgentMentalState()
        assert agent.beliefs == []
        assert agent.goals == []
        assert agent.emotions == []
        assert agent.attention_focus == ""


# ─── MentalState Tests ─────────────────────────────────────────


class TestMentalState:
    def test_empty(self):
        ms = MentalState()
        assert ms.is_empty()

    def test_with_agents(self):
        captain = make_captain_mood(["focused"], ["build tower"])
        ms = MentalState(agents=[captain])
        assert not ms.is_empty()
        assert len(ms.agents) == 1

    def test_serialization_roundtrip(self):
        ms = make_mental_state(["focused"], ["build tower"], "tense")
        d = ms.to_dict()
        restored = MentalState.from_dict(d)
        assert restored.atmosphere == "tense"
        assert len(restored.agents) == 1
        assert restored.agents[0].emotions == ["focused"]

    def test_json_serializable(self):
        ms = make_mental_state(["calm"], ["relax"])
        json_str = json.dumps(ms.to_dict())
        assert "atmosphere" in json_str
        assert "calm" in json_str


# ─── Mental Signature Tests ────────────────────────────────────


class TestMentalSignature:
    def test_basic_signature(self):
        ms = make_mental_state(["focused", "calm"], ["build tower"])
        sig = build_mental_signature(ms)
        assert "captain_mood=focused" in sig
        assert "captain_intent=build" in sig or "captain_intent=build tower" in sig

    def test_atmosphere_in_signature(self):
        ms = make_mental_state(atmosphere="tense")
        sig = build_mental_signature(ms)
        assert "atmosphere=tense" in sig

    def test_empty_mental_state_signature(self):
        ms = MentalState()
        sig = build_mental_signature(ms)
        assert "mental=unknown" in sig

    def test_different_states_produce_different_signatures(self):
        ms1 = make_mental_state(["focused"], ["building"])
        ms2 = make_mental_state(["frustrated"], ["building"])
        sig1 = build_mental_signature(ms1)
        sig2 = build_mental_signature(ms2)
        assert sig1 != sig2

    def test_similar_states_produce_similar_signatures(self):
        ms1 = make_mental_state(["focused"], ["build tower"])
        ms2 = make_mental_state(["focused"], ["build wall"])
        sig1 = build_mental_signature(ms1)
        sig2 = build_mental_signature(ms2)
        # Should share the mood and be similar
        assert "captain_mood=focused" in sig1
        assert "captain_mood=focused" in sig2


# ─── Mental Keywords Tests ─────────────────────────────────────


class TestMentalKeywords:
    def test_extracts_keywords(self):
        ms = make_mental_state(["focused", "determined"], ["build tower"])
        kw = build_mental_keywords(ms)
        assert "captain_mood" in kw
        assert "focused" in kw["captain_mood"]

    def test_empty_state(self):
        ms = MentalState()
        kw = build_mental_keywords(ms)
        assert kw == {}


# ─── Embedding Tests ───────────────────────────────────────────


class TestEmbedding:
    def test_dimension(self):
        ms = make_mental_state(["calm"])
        vec = embed_mental_state(ms)
        assert len(vec) == 384

    def test_normalized(self):
        ms = make_mental_state(["calm"])
        vec = embed_mental_state(ms)
        magnitude = sum(v * v for v in vec) ** 0.5
        assert 0.9 < magnitude < 1.1  # approximately normalized

    def test_deterministic(self):
        ms = make_mental_state(["calm"])
        vec1 = embed_mental_state(ms)
        vec2 = embed_mental_state(ms)
        assert vec1 == vec2

    def test_text_embedding_basic(self):
        vec = embed_hash_text("captain_mood=focused atmosphere=tense")
        assert len(vec) == 384
        magnitude = sum(v * v for v in vec) ** 0.5
        assert magnitude > 0.5  # non-trivial


# ─── Social Delta Detector Tests ───────────────────────────────


class TestSocialDeltaDetector:
    def test_first_call_always_delta(self):
        detector = SocialDeltaDetector()
        gs = make_game_state()
        assert detector.has_social_delta(gs, None) is True

    def test_empty_cache_triggers_delta(self):
        detector = SocialDeltaDetector()
        gs = make_game_state()
        empty = MentalState()
        assert detector.has_social_delta(gs, empty) is True

    def test_no_change_no_delta(self):
        detector = SocialDeltaDetector()
        gs = make_game_state(bond=3, build="tower")
        ms = make_mental_state()
        detector.update_cache(gs)
        # Second call with same state → no delta
        assert detector.has_social_delta(gs, ms) is False

    def test_bond_level_change_triggers_delta(self):
        detector = SocialDeltaDetector()
        gs1 = make_game_state(bond=3)
        ms = make_mental_state()
        detector.update_cache(gs1)

        gs2 = make_game_state(bond=4)  # bond changed
        assert detector.has_social_delta(gs2, ms) is True

    def test_position_change_triggers_delta(self):
        detector = SocialDeltaDetector()
        gs1 = make_game_state()
        ms = make_mental_state()
        detector.update_cache(gs1)

        gs2 = make_game_state()
        gs2["position"] = {"x": 100.0, "y": 0.0, "z": 100.0}  # big move
        assert detector.has_social_delta(gs2, ms) is True

    def test_small_position_change_no_delta(self):
        detector = SocialDeltaDetector()
        gs1 = make_game_state()
        gs1["position"] = {"x": 10.0, "y": 5.0, "z": -20.0}
        ms = make_mental_state()
        detector.update_cache(gs1)

        gs2 = make_game_state()
        gs2["position"] = {"x": 12.0, "y": 5.0, "z": -18.0}  # small move
        assert detector.has_social_delta(gs2, ms) is False

    def test_build_state_change_triggers_delta(self):
        detector = SocialDeltaDetector()
        gs1 = make_game_state(build="tower")
        ms = make_mental_state()
        detector.update_cache(gs1)

        gs2 = make_game_state(build="wall")  # different build
        assert detector.has_social_delta(gs2, ms) is True

    def test_going_idle_triggers_delta(self):
        detector = SocialDeltaDetector()
        gs1 = make_game_state(build="tower")
        ms = make_mental_state()
        detector.update_cache(gs1)

        gs2 = make_game_state(build="none")  # stopped building
        assert detector.has_social_delta(gs2, ms) is True

    def test_staleness_triggers_delta(self):
        detector = SocialDeltaDetector()
        detector._staleness_threshold_seconds = 0.1  # very short for testing
        gs = make_game_state()
        ms = make_mental_state()
        detector.update_cache(gs, render_time=0.0)

        time.sleep(0.15)
        assert detector.has_social_delta(gs, ms) is True


# ─── Partial Observation Tests ─────────────────────────────────


class TestPartialObservation:
    def test_empty(self):
        obs = PartialObservation()
        assert obs.to_context_string() == ""

    def test_with_data(self):
        obs = PartialObservation(
            visible_agents=["Captain"],
            visible_actions=["building tower"],
            inferred_moods=["focused"],
        )
        ctx = obs.to_context_string()
        assert "Captain" in ctx
        assert "building tower" in ctx
        assert "focused" in ctx

    def test_serialization(self):
        obs = PartialObservation(
            visible_agents=["Captain"],
            visible_actions=["idle"],
            can_hear=False,
        )
        d = obs.to_dict()
        assert d["visible_agents"] == ["Captain"]
        assert d["can_hear"] is False
