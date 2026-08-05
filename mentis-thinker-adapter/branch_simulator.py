"""
Branch Simulator — simulates how candidate actions update both physical AND mental state.

For each candidate action, the simulator predicts:
  1. Physical transition: how does the physical state change?
  2. Mental transition: how does each agent's mental state change?
  3. Combined score: mental_consistency × 0.45 + physical_plausibility × 0.35
     + social_appropriateness × 0.20

The simulator uses the Mentis scoring rubric but is designed to run on
the local model (Granite 2B) or even without an LLM (using heuristic
fallbacks for common patterns).

When the LLM is available, branch simulation produces rich predictions.
When it's not, heuristic scoring provides a reasonable fallback that's
better than no simulation at all.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from typing import Any

from mental_state import MentalState, AgentMentalState, PartialObservation


# ─── Scoring Weights (from Mentis config.yaml) ─────────────────

SCORE_WEIGHTS = {
    "mentally_consistent": 0.45,
    "physically_plausible": 0.35,
    "socially_appropriate": 0.20,
}


# ─── Action Decomposition ──────────────────────────────────────


@dataclass
class ActionPlan:
    """
    A candidate action decomposed into physical and mental components.

    Mirrors the Mentis ActionPlan schema. Every action has:
      - physical_action: what physically happens (movement, sound, etc.)
      - mental_action: the intended social/cognitive effect

    If mental_action is empty, the action is purely physical with no
    deliberate social intent (but may still have mental side effects).
    """

    option_id: str = ""
    description: str = ""
    physical_action: str = ""
    mental_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "option_id": self.option_id,
            "description": self.description,
            "physical_action": self.physical_action,
            "mental_action": self.mental_action,
        }


def decompose_action(action: dict[str, Any]) -> ActionPlan:
    """
    Decompose a thinker action dict into physical and mental components.

    Uses heuristic rules based on action type. When the LLM is available,
    the adapter can override this with richer decomposition.
    """
    action_type = action.get("type", "wait")
    target = action.get("target", "")
    params = action.get("params", {})

    physical_map = {
        "explore": "moves to a new location",
        "build": f"constructs a {params.get('structure_type', 'structure')} with {params.get('material', 'wood')}",
        "inspect": f"examines {target or 'nearest object'} closely",
        "wait": "stays still and observes",
        "speak": f"says: {params.get('content', target or 'greeting')}",
    }

    mental_map = {
        "explore": "satisfies curiosity, potentially discovers something new",
        "build": "",
        "inspect": "gathers information",
        "wait": "",
        "speak": "communicates with the target",
    }

    return ActionPlan(
        option_id=action_type,
        description=f"{action_type} {target}".strip(),
        physical_action=physical_map.get(action_type, "does nothing"),
        mental_action=mental_map.get(action_type, ""),
    )


# ─── Branch (one simulated future) ─────────────────────────────


@dataclass
class Branch:
    """
    A simulated branch: action → predicted physical and mental state transitions.

    Attributes:
        plan: The action plan being simulated
        physical_outcome: predicted physical state change description
        mental_outcome: predicted mental state changes for each agent
        scores: BranchScore with three dimensions + safety veto
        error: non-empty if simulation failed
    """

    plan: ActionPlan
    physical_outcome: str = ""
    mental_outcome: str = ""
    scores: BranchScore | None = None
    error: str = ""

    @property
    def failed(self) -> bool:
        return bool(self.error)


# ─── Branch Score ──────────────────────────────────────────────


@dataclass
class BranchScore:
    """
    Score for a single branch on three dimensions.

    Mirrors the Mentis BranchScore schema. Each dimension is [0.0, 1.0].
    The weighted_score is computed from the three dimensions and the
    SCORE_WEIGHTS. Safety veto zeroes the score.
    """

    option_id: str = ""
    mentally_consistent: float = 0.5
    physically_plausible: float = 0.5
    socially_appropriate: float = 0.5
    safety_veto: bool = False
    reasoning: str = ""
    weighted_score: float = 0.0

    def compute_weighted(self) -> float:
        """Compute the weighted score from dimensions and weights."""
        if self.safety_veto:
            self.weighted_score = 0.0
            return 0.0
        self.weighted_score = round(
            SCORE_WEIGHTS["mentally_consistent"] * self.mentally_consistent
            + SCORE_WEIGHTS["physically_plausible"] * self.physically_plausible
            + SCORE_WEIGHTS["socially_appropriate"] * self.socially_appropriate,
            4,
        )
        return self.weighted_score

    def to_dict(self) -> dict[str, Any]:
        return {
            "option_id": self.option_id,
            "mentally_consistent": round(self.mentally_consistent, 3),
            "physically_plausible": round(self.physically_plausible, 3),
            "socially_appropriate": round(self.socially_appropriate, 3),
            "safety_veto": self.safety_veto,
            "weighted_score": round(self.weighted_score, 3),
            "reasoning": self.reasoning,
        }


# ─── Heuristic Scoring (fallback when no LLM available) ────────


def heuristic_score(
    action: dict[str, Any],
    mental_state: MentalState,
    observation: PartialObservation,
    bond_level: int,
) -> BranchScore:
    """
    Score an action using heuristic rules, without any LLM call.

    This is the fallback scorer. It's not as nuanced as LLM-based scoring
    but it's instant and covers the most common patterns.
    """
    action_type = action.get("type", "wait")
    plan = decompose_action(action)

    # Find captain's mental state
    captain = None
    for agent in mental_state.agents:
        if agent.role == "captain" or agent.name.lower() == "captain":
            captain = agent
            break

    # --- Physical plausibility ---
    # All thinker actions are physically plausible by construction.
    # The thinker doesn't generate impossible actions.
    physical = 0.85

    # --- Mental consistency ---
    # Does this action align with Wesley's role and the captain's state?
    mental = 0.5  # default neutral

    if captain:
        captain_mood = captain.emotions[0].lower() if captain.emotions else ""
        captain_goal = captain.goals[0].lower() if captain.goals else ""

        # If captain is building/focused and Wesley speaks → lower mental consistency
        if "focus" in captain_mood or "build" in captain_goal:
            if action_type == "speak" and bond_level < 4:
                mental = 0.3
            elif action_type == "build":
                mental = 0.75  # helping with construction
            elif action_type == "inspect":
                mental = 0.7  # gathering info useful for build
            elif action_type == "wait":
                mental = 0.65  # respectfully waiting

        # If captain is frustrated and Wesley waits → lower mental consistency
        elif "frustrat" in captain_mood or "anger" in captain_mood:
            if action_type == "wait":
                mental = 0.35  # unhelpful when help is needed
            elif action_type == "build":
                mental = 0.7  # actively helping
            elif action_type == "inspect":
                mental = 0.6  # looking for solutions

        # If captain is relaxed/idle and Wesley explores → higher consistency
        elif not captain_goal or "relax" in captain_mood or "calm" in captain_mood:
            if action_type == "explore":
                mental = 0.8
            elif action_type == "speak" and bond_level >= 3:
                mental = 0.75
            elif action_type == "build":
                mental = 0.6

        # Bond level modifier
        if bond_level >= 4:
            mental += 0.1
        elif bond_level <= 1:
            mental -= 0.1

    mental = max(0.0, min(1.0, mental))

    # --- Social appropriateness ---
    social = 0.7  # default: most actions are socially acceptable

    if captain:
        captain_mood = captain.emotions[0].lower() if captain.emotions else ""

        # Speaking during frustration at low bond → socially risky
        if action_type == "speak":
            if "frustrat" in captain_mood and bond_level < 3:
                social = 0.3
            elif bond_level >= 4:
                social = 0.8
            else:
                social = 0.5

        # Exploring away while captain is in danger → socially inappropriate
        if action_type == "explore":
            if "frustrat" in captain_mood or "anger" in captain_mood:
                if bond_level >= 3:
                    social = 0.4  # abandoning a frustrated ally

    social = max(0.0, min(1.0, social))

    # --- Safety veto ---
    safety_veto = False  # The thinker doesn't generate dangerous actions

    score = BranchScore(
        option_id=action_type,
        mentally_consistent=mental,
        physically_plausible=physical,
        socially_appropriate=social,
        safety_veto=safety_veto,
        reasoning=f"heuristic_score(bond={bond_level}, captain_mood={captain.emotions[0] if captain and captain.emotions else 'unknown'})",
    )
    score.compute_weighted()
    return score


# ─── Branch Simulator ──────────────────────────────────────────


class BranchSimulator:
    """
    Simulates how candidate actions update both physical and mental state.

    Usage:
        simulator = BranchSimulator()
        branches = simulator.simulate_batch(
            actions=[explore_action, build_action, wait_action],
            mental_state=current_mental_state,
            observation=current_observation,
            bond_level=3,
        )
        best = simulator.select_best(branches)
    """

    def __init__(
        self,
        use_llm: bool = False,
        max_branches: int = 3,
    ) -> None:
        """
        Args:
            use_llm: If True, use the LLM for rich branch simulation.
                     If False, use heuristic scoring only (fast, no API calls).
            max_branches: Maximum number of branches to simulate.
        """
        self.use_llm = use_llm
        self.max_branches = max_branches

    def simulate(
        self,
        action: dict[str, Any],
        mental_state: MentalState,
        observation: PartialObservation,
        bond_level: int,
    ) -> Branch:
        """Simulate a single action branch."""
        plan = decompose_action(action)

        try:
            # Physical outcome (heuristic for now)
            physical_outcome = plan.physical_action

            # Mental outcome (heuristic)
            mental_outcome = self._predict_mental_outcome(plan, mental_state, bond_level)

            # Score
            if self.use_llm:
                score = self._llm_score(plan, mental_state, observation, bond_level)
            else:
                score = heuristic_score(action, mental_state, observation, bond_level)

            return Branch(
                plan=plan,
                physical_outcome=physical_outcome,
                mental_outcome=mental_outcome,
                scores=score,
            )
        except Exception as exc:
            return Branch(plan=plan, error=f"{type(exc).__name__}: {exc}")

    def simulate_batch(
        self,
        actions: list[dict[str, Any]],
        mental_state: MentalState,
        observation: PartialObservation,
        bond_level: int,
    ) -> list[Branch]:
        """Simulate multiple action branches and return them sorted by score."""
        branches: list[Branch] = []

        for action in actions[: self.max_branches]:
            branch = self.simulate(action, mental_state, observation, bond_level)
            branches.append(branch)

        # Sort by weighted score (descending)
        scored = [b for b in branches if b.scores is not None and not b.failed]
        scored.sort(key=lambda b: -(b.scores.weighted_score if b.scores else 0))

        return scored if scored else branches

    def select_best(self, branches: list[Branch]) -> Branch | None:
        """Select the best branch from a list of simulated branches."""
        scored = [b for b in branches if b.scores is not None and not b.failed]
        if not scored:
            return branches[0] if branches else None
        return max(scored, key=lambda b: b.scores.weighted_score if b.scores else 0)

    def _predict_mental_outcome(
        self,
        plan: ActionPlan,
        mental_state: MentalState,
        bond_level: int,
    ) -> str:
        """Predict how the action updates mental state (heuristic)."""
        action_type = plan.option_id

        outcomes: list[str] = []

        for agent in mental_state.agents:
            if agent.role == "captain":
                if action_type == "speak":
                    if bond_level >= 3:
                        outcomes.append("captain feels heard and appreciated")
                    else:
                        outcomes.append("captain mildly startled by direct address")
                elif action_type == "build":
                    if bond_level >= 3:
                        outcomes.append("captain appreciates the collaboration")
                    else:
                        outcomes.append("captain neutral about unasked help")
                elif action_type == "explore":
                    outcomes.append("captain may not notice Wesley's exploration")
                elif action_type == "wait":
                    outcomes.append("captain's mental state unchanged")
                elif action_type == "inspect":
                    outcomes.append("captain may become curious about what Wesley found")

        if not outcomes:
            outcomes.append("no significant mental state change predicted")

        return "; ".join(outcomes)

    def _llm_score(
        self,
        plan: ActionPlan,
        mental_state: MentalState,
        observation: PartialObservation,
        bond_level: int,
    ) -> BranchScore:
        """
        Score using the LLM. This is the rich path — only called when
        use_llm=True and the situation is novel enough to warrant it.

        NOTE: In the prototype, this falls back to heuristic scoring.
        The full LLM scoring prompt is in the Mentis prompts module
        and would be integrated via the adapter's LLM client.
        """
        # For the prototype, we use heuristic scoring.
        # The full implementation would call the LLM with the Mentis
        # scores_prompt and parse the response.
        action = {"type": plan.option_id, "target": "", "params": {}}
        return heuristic_score(action, mental_state, observation, bond_level)


# ─── Utility: Rank Branches ────────────────────────────────────


def rank_branches(branches: list[Branch]) -> list[dict[str, Any]]:
    """
    Produce a ranked summary of branches for logging.

    Returns a list of dicts sorted by weighted_score (descending),
    each with the action, score breakdown, and predicted outcome.
    """
    ranked: list[dict[str, Any]] = []

    for branch in branches:
        if branch.failed:
            ranked.append({
                "action": branch.plan.option_id,
                "error": branch.error,
                "weighted_score": 0.0,
            })
            continue

        score = branch.scores
        ranked.append({
            "action": branch.plan.option_id,
            "description": branch.plan.description,
            "weighted_score": round(score.weighted_score, 3) if score else 0.0,
            "mental": round(score.mentally_consistent, 2) if score else 0.0,
            "physical": round(score.physically_plausible, 2) if score else 0.0,
            "social": round(score.socially_appropriate, 2) if score else 0.0,
            "safety_veto": score.safety_veto if score else False,
            "predicted_mental_outcome": branch.mental_outcome,
        })

    ranked.sort(key=lambda x: -x["weighted_score"])
    return ranked
