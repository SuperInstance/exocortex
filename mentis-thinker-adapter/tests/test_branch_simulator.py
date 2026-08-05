"""
Tests for branch_simulator.py — action decomposition, simulation, and scoring.
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from branch_simulator import (
    ActionPlan,
    Branch,
    BranchScore,
    BranchSimulator,
    decompose_action,
    heuristic_score,
    rank_branches,
    SCORE_WEIGHTS,
)
from mental_state import (
    AgentMentalState,
    MentalState,
    SocialRelation,
    PartialObservation,
)


# ─── Fixtures ──────────────────────────────────────────────────

def make_focused_captain_state() -> MentalState:
    """Captain is focused on building — common test scenario."""
    captain = AgentMentalState(
        name="Captain",
        role="captain",
        emotions=["focused"],
        goals=["build tower"],
        attention_focus="tower construction",
    )
    wesley = AgentMentalState(
        name="Wesley",
        role="ensign",
        goals=["explore", "assist"],
        emotions=["curious"],
    )
    relation = SocialRelation(
        agent_a="Captain",
        agent_b="Wesley",
        relation_type="captain_ensign",
        trust_level=0.6,
        attitude="trusting",
    )
    return MentalState(
        agents=[captain, wesley],
        relations=[relation],
        atmosphere="focused",
    )


def make_frustrated_captain_state() -> MentalState:
    """Captain is frustrated — high-stakes test scenario."""
    captain = AgentMentalState(
        name="Captain",
        role="captain",
        emotions=["frustrated"],
        goals=["fix broken tower"],
        attention_focus="structural failure",
    )
    relation = SocialRelation(
        agent_a="Captain",
        agent_b="Wesley",
        relation_type="captain_ensign",
        trust_level=0.4,
        attitude="wary",
    )
    return MentalState(
        agents=[captain],
        relations=[relation],
        atmosphere="tense",
    )


def make_relaxed_captain_state() -> MentalState:
    """Captain is relaxed — low-stakes test scenario."""
    captain = AgentMentalState(
        name="Captain",
        role="captain",
        emotions=["calm", "content"],
        goals=[],
        attention_focus="enjoying the view",
    )
    return MentalState(
        agents=[captain],
        atmosphere="contemplative",
    )


def make_observation() -> PartialObservation:
    return PartialObservation(
        visible_agents=["Captain"],
        visible_actions=["building tower"],
        inferred_moods=["focused"],
        can_see=True,
        can_hear=True,
    )


# ─── Action Decomposition Tests ────────────────────────────────


class TestActionDecomposition:
    def test_explore(self):
        action = {"type": "explore", "target": "cliff", "params": {}}
        plan = decompose_action(action)
        assert plan.option_id == "explore"
        assert "move" in plan.physical_action.lower()
        assert "curiosity" in plan.mental_action.lower()

    def test_build(self):
        action = {"type": "build", "params": {"structure_type": "wall", "material": "stone"}}
        plan = decompose_action(action)
        assert plan.option_id == "build"
        assert "wall" in plan.physical_action
        assert "stone" in plan.physical_action

    def test_speak(self):
        action = {"type": "speak", "params": {"content": "look at this"}}
        plan = decompose_action(action)
        assert "speak" in plan.physical_action.lower() or "say" in plan.physical_action.lower()

    def test_wait(self):
        action = {"type": "wait"}
        plan = decompose_action(action)
        assert plan.option_id == "wait"
        assert "still" in plan.physical_action.lower() or "observe" in plan.physical_action.lower()


# ─── Branch Score Tests ────────────────────────────────────────


class TestBranchScore:
    def test_weighted_score_computation(self):
        score = BranchScore(
            mentally_consistent=0.8,
            physically_plausible=0.9,
            socially_appropriate=0.7,
        )
        weighted = score.compute_weighted()
        expected = (
            0.45 * 0.8 + 0.35 * 0.9 + 0.20 * 0.7
        )
        assert abs(weighted - expected) < 0.01

    def test_safety_veto_zeros_score(self):
        score = BranchScore(
            mentally_consistent=1.0,
            physically_plausible=1.0,
            socially_appropriate=1.0,
            safety_veto=True,
        )
        assert score.compute_weighted() == 0.0

    def test_clamping(self):
        """Values should work in [0, 1] range."""
        score = BranchScore(
            mentally_consistent=0.0,
            physically_plausible=1.0,
            socially_appropriate=0.5,
        )
        weighted = score.compute_weighted()
        assert 0.0 < weighted < 1.0


# ─── Heuristic Scoring Tests ───────────────────────────────────


class TestHeuristicScore:
    def test_build_during_focused_captain(self):
        """Building when captain is focused should score well."""
        action = {"type": "build", "params": {}}
        ms = make_focused_captain_state()
        obs = make_observation()
        score = heuristic_score(action, ms, obs, bond_level=3)
        assert score.mentally_consistent > 0.6
        assert score.physically_plausible > 0.7

    def test_speak_during_focused_captain_low_bond(self):
        """Speaking when captain is focused and bond is low should score poorly."""
        action = {"type": "speak", "params": {}}
        ms = make_focused_captain_state()
        obs = make_observation()
        score = heuristic_score(action, ms, obs, bond_level=2)
        assert score.mentally_consistent < 0.5
        assert score.socially_appropriate < 0.6

    def test_speak_during_focused_captain_high_bond(self):
        """Speaking when captain is focused but bond is high should be acceptable."""
        action = {"type": "speak", "params": {}}
        ms = make_focused_captain_state()
        obs = make_observation()
        score = heuristic_score(action, ms, obs, bond_level=5)
        # At high bond, speaking is more acceptable
        assert score.socially_appropriate >= 0.7

    def test_explore_during_frustrated_captain(self):
        """Exploring away when captain is frustrated should score poorly."""
        action = {"type": "explore", "params": {}}
        ms = make_frustrated_captain_state()
        obs = PartialObservation(
            visible_agents=["Captain"],
            visible_actions=["struggling with tower"],
            inferred_moods=["frustrated"],
        )
        score = heuristic_score(action, ms, obs, bond_level=3)
        assert score.socially_appropriate < 0.5

    def test_wait_during_frustrated_captain(self):
        """Waiting when captain is frustrated is unhelpful."""
        action = {"type": "wait"}
        ms = make_frustrated_captain_state()
        obs = PartialObservation(
            visible_agents=["Captain"],
            inferred_moods=["frustrated"],
        )
        score = heuristic_score(action, ms, obs, bond_level=3)
        assert score.mentally_consistent < 0.5

    def test_explore_during_relaxed_captain(self):
        """Exploring when captain is relaxed should score well."""
        action = {"type": "explore", "params": {}}
        ms = make_relaxed_captain_state()
        obs = PartialObservation(
            visible_agents=["Captain"],
            visible_actions=["idle"],
            inferred_moods=["calm"],
        )
        score = heuristic_score(action, ms, obs, bond_level=3)
        assert score.mentally_consistent > 0.6

    def test_no_safety_veto_for_normal_actions(self):
        """Normal thinker actions should never trigger safety veto."""
        for action_type in ["explore", "build", "inspect", "wait", "speak"]:
            action = {"type": action_type}
            ms = make_focused_captain_state()
            obs = make_observation()
            score = heuristic_score(action, ms, obs, bond_level=3)
            assert score.safety_veto is False


# ─── Branch Simulator Tests ────────────────────────────────────


class TestBranchSimulator:
    def test_simulate_single_branch(self):
        sim = BranchSimulator(use_llm=False)
        action = {"type": "build", "params": {}}
        ms = make_focused_captain_state()
        obs = make_observation()
        branch = sim.simulate(action, ms, obs, bond_level=3)
        assert not branch.failed
        assert branch.scores is not None
        assert branch.scores.weighted_score > 0

    def test_simulate_batch(self):
        sim = BranchSimulator(use_llm=False)
        actions = [
            {"type": "explore"},
            {"type": "build", "params": {}},
            {"type": "wait"},
        ]
        ms = make_focused_captain_state()
        obs = make_observation()
        branches = sim.simulate_batch(actions, ms, obs, bond_level=3)
        assert len(branches) == 3
        # Sorted by score (descending)
        assert branches[0].scores.weighted_score >= branches[-1].scores.weighted_score

    def test_select_best(self):
        sim = BranchSimulator(use_llm=False)
        actions = [
            {"type": "wait"},
            {"type": "build", "params": {}},
            {"type": "explore"},
        ]
        ms = make_focused_captain_state()
        obs = make_observation()
        branches = sim.simulate_batch(actions, ms, obs, bond_level=3)
        best = sim.select_best(branches)
        assert best is not None
        assert best.scores.weighted_score > 0

    def test_max_branches_limit(self):
        sim = BranchSimulator(use_llm=False, max_branches=2)
        actions = [
            {"type": "explore"},
            {"type": "build", "params": {}},
            {"type": "wait"},
            {"type": "speak", "params": {}},
        ]
        ms = make_focused_captain_state()
        obs = make_observation()
        branches = sim.simulate_batch(actions, ms, obs, bond_level=3)
        assert len(branches) == 2  # limited to max_branches

    def test_mental_outcome_predicted(self):
        sim = BranchSimulator(use_llm=False)
        action = {"type": "speak", "params": {}}
        ms = make_focused_captain_state()
        obs = make_observation()
        branch = sim.simulate(action, ms, obs, bond_level=4)
        assert branch.mental_outcome  # non-empty
        assert "captain" in branch.mental_outcome.lower()

    def test_focused_captain_build_beats_explore(self):
        """When captain is focused on building, build should beat explore."""
        sim = BranchSimulator(use_llm=False)
        actions = [
            {"type": "explore"},
            {"type": "build", "params": {}},
        ]
        ms = make_focused_captain_state()
        obs = make_observation()
        branches = sim.simulate_batch(actions, ms, obs, bond_level=3)
        best = branches[0]
        assert best.plan.option_id == "build"

    def test_relaxed_captain_explore_beats_wait(self):
        """When captain is relaxed, explore should beat wait."""
        sim = BranchSimulator(use_llm=False)
        actions = [
            {"type": "wait"},
            {"type": "explore"},
        ]
        ms = make_relaxed_captain_state()
        obs = PartialObservation(
            visible_agents=["Captain"],
            visible_actions=["idle"],
            inferred_moods=["calm"],
        )
        branches = sim.simulate_batch(actions, ms, obs, bond_level=3)
        best = branches[0]
        assert best.plan.option_id == "explore"


# ─── Rank Branches Tests ───────────────────────────────────────


class TestRankBranches:
    def test_ranking(self):
        sim = BranchSimulator(use_llm=False)
        actions = [
            {"type": "wait"},
            {"type": "build", "params": {}},
            {"type": "explore"},
        ]
        ms = make_focused_captain_state()
        obs = make_observation()
        branches = sim.simulate_batch(actions, ms, obs, bond_level=3)
        ranked = rank_branches(branches)
        assert len(ranked) == 3
        # Sorted by score descending
        assert ranked[0]["weighted_score"] >= ranked[-1]["weighted_score"]

    def test_includes_predicted_outcome(self):
        sim = BranchSimulator(use_llm=False)
        action = {"type": "build", "params": {}}
        ms = make_focused_captain_state()
        obs = make_observation()
        branch = sim.simulate(action, ms, obs, bond_level=3)
        ranked = rank_branches([branch])
        assert "predicted_mental_outcome" in ranked[0]
        assert ranked[0]["predicted_mental_outcome"]  # non-empty
