"""
Mentis Adapter — wraps the Mentis engine as a layer in the constant thinker.

This is the integration point between the Mentis mental world model and
the existing Slackwater constant thinker (local_thinker/thinker.py).

The adapter provides:
  1. Mental state parsing (from game state → coupled physical-mental state)
  2. Partial observation rendering (what Wesley actually perceives)
  3. Social delta detection (has the social situation changed?)
  4. Branch simulation (how do actions update mental state?)
  5. Enriched context construction (physical + mental context for the LLM)

The adapter is designed to be drop-in: the existing thinker loop adds
two calls per tick:
  1. adapter.get_mental_state(game_state) → MentalState (cached or fresh)
  2. adapter.enrich_context(context, mental_state) → enriched context string

When social delta is detected, the adapter re-renders the mental state.
When it's not, the cached state is returned with zero LLM cost.

Usage:
    from mentis_adapter import MentisAdapter

    adapter = MentisAdapter()

    # In the thinker loop, after getting game state:
    mental_state = adapter.get_mental_state(game_state)
    mental_context = adapter.build_mental_context(mental_state, game_state)
    enriched = adapter.enrich_context(context, mental_context)

    # After thought generation, for branch simulation:
    branches = adapter.simulate_branches(
        actions=[explore, build, wait],
        mental_state=mental_state,
        bond_level=game_state.get("bond_level", 0),
    )
    best = adapter.select_best_action(branches)
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from typing import Any

from mental_state import (
    AgentMentalState,
    MentalState,
    PartialObservation,
    SocialDeltaDetector,
    SocialRelation,
    build_mental_keywords,
    build_mental_signature,
    embed_mental_state,
)
from branch_simulator import (
    Branch,
    BranchScore,
    BranchSimulator,
    ActionPlan,
    rank_branches,
)


# ─── Configuration ─────────────────────────────────────────────

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "granite3.1-dense:2b")

# Whether to use the LLM for mental state parsing.
# If False, uses heuristic parsing only (no LLM calls, lower quality).
USE_LLM_FOR_MENTAL_STATE = os.environ.get("MENTIS_USE_LLM", "false").lower() == "true"


# ─── HTTP ──────────────────────────────────────────────────────

def _curl_post(url: str, headers: dict[str, str], data: dict[str, Any], timeout: int = 10) -> dict[str, Any]:
    """POST JSON via curl subprocess (same pattern as thinker)."""
    cmd = [
        "curl", "-s", "-X", "POST", url,
        "--connect-timeout", str(timeout),
        "--max-time", str(timeout + 5),
        "-H", "Content-Type: application/json",
    ]
    for key, val in headers.items():
        cmd.extend(["-H", f"{key}: {val}"])
    cmd.extend(["-d", json.dumps(data)])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
        if result.returncode != 0:
            return {"error": f"curl failed: {result.stderr.strip()}"}
        return json.loads(result.stdout)
    except Exception as e:
        return {"error": str(e)}


# ─── Mentis Adapter ────────────────────────────────────────────


class MentisAdapter:
    """
    Wraps the Mentis mental world model as a layer in the constant thinker.

    The adapter manages:
      - A cached mental state (re-rendered only when social situation changes)
      - A social delta detector (determines when to re-render)
      - A branch simulator (evaluates actions on coupled physical-mental state)
      - Heuristic fallbacks (when LLM is unavailable)

    The adapter is stateful — it holds the cached mental state between ticks.
    """

    def __init__(
        self,
        use_llm: bool = False,
        max_branches: int = 3,
    ) -> None:
        """
        Args:
            use_llm: If True, use LLM for mental state parsing and branch simulation.
                     If False, use heuristics only (fast, no API calls).
            max_branches: Max actions to simulate in branch simulation.
        """
        self.use_llm = use_llm or USE_LLM_FOR_MENTAL_STATE
        self.max_branches = max_branches

        # Cached state
        self._mental_state: MentalState = MentalState()
        self._observation: PartialObservation = PartialObservation()
        self._delta_detector = SocialDeltaDetector()
        self._simulator = BranchSimulator(use_llm=self.use_llm, max_branches=max_branches)

        # Stats
        self._ticks = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._llm_calls = 0
        self._total_render_ms = 0.0

    # ─── Mental State ──────────────────────────────────────────

    def get_mental_state(self, game_state: dict[str, Any]) -> MentalState:
        """
        Get the current mental state, using cache when valid.

        This is the main entry point. Called every tick.

        Returns a MentalState object (either cached or freshly rendered).
        """
        self._ticks += 1

        # Check social delta
        if self._delta_detector.has_social_delta(game_state, self._mental_state):
            # Cache miss — re-render
            self._cache_misses += 1
            t0 = time.perf_counter()

            if self.use_llm:
                self._mental_state = self._llm_parse_mental_state(game_state)
            else:
                self._mental_state = self._heuristic_parse_mental_state(game_state)

            self._observation = self._render_observation(game_state, self._mental_state)
            self._delta_detector.update_cache(game_state)

            elapsed_ms = (time.perf_counter() - t0) * 1000
            self._total_render_ms += elapsed_ms
            self._mental_state.timestamp = datetime.now(timezone.utc).isoformat()
            self._mental_state.source = "re-rendered"
        else:
            # Cache hit
            self._cache_hits += 1
            self._mental_state.source = "cached"

        return self._mental_state

    def get_observation(self) -> PartialObservation:
        """Get Wesley's partial observation of the scene."""
        return self._observation

    # ─── Context Enrichment ────────────────────────────────────

    def build_mental_context(
        self,
        mental_state: MentalState,
        game_state: dict[str, Any],
    ) -> str:
        """
        Build a mental context string to append to the LLM prompt.

        This is what makes the thinker's thoughts mental-aware.
        The context is concise — a few lines, not paragraphs.
        """
        if mental_state.is_empty():
            return ""

        parts: list[str] = []

        # Observation line
        obs_str = self._observation.to_context_string()
        if obs_str:
            parts.append(f"## Social Context")
            parts.append(obs_str)

        # Captain's apparent state
        for agent in mental_state.agents:
            if agent.role == "captain" or agent.name.lower() == "captain":
                mood = ", ".join(agent.emotions) if agent.emotions else "unknown"
                goal = ", ".join(agent.goals) if agent.goals else "unclear"
                focus = agent.attention_focus or "unknown"
                parts.append(f"Captain appears: mood={mood}, goal={goal}, focus={focus}")
                break

        # Atmosphere
        if mental_state.atmosphere:
            parts.append(f"Atmosphere: {mental_state.atmosphere}")

        # Social guidance (what would be appropriate)
        guidance = self._social_guidance(mental_state, game_state)
        if guidance:
            parts.append(f"Social read: {guidance}")

        return "\n".join(parts)

    def enrich_context(
        self,
        physical_context: str,
        mental_context: str,
    ) -> str:
        """
        Append the mental context to the existing physical context.

        The mental context goes right before "## Your Turn" in the
        existing context builder output.
        """
        if not mental_context:
            return physical_context

        # Find the "Your Turn" section and insert before it
        if "## Your Turn" in physical_context:
            idx = physical_context.index("## Your Turn")
            return (
                physical_context[:idx]
                + mental_context
                + "\n\n"
                + physical_context[idx:]
            )
        else:
            # Just append
            return physical_context + "\n\n" + mental_context

    # ─── Branch Simulation ─────────────────────────────────────

    def simulate_branches(
        self,
        actions: list[dict[str, Any]],
        mental_state: MentalState | None = None,
        bond_level: int = 0,
    ) -> list[Branch]:
        """
        Simulate how each candidate action updates both physical and mental state.

        Returns branches sorted by weighted score (best first).
        """
        ms = mental_state or self._mental_state
        return self._simulator.simulate_batch(
            actions=actions,
            mental_state=ms,
            observation=self._observation,
            bond_level=bond_level,
        )

    def select_best_action(self, branches: list[Branch]) -> dict[str, Any] | None:
        """
        Select the best action from simulated branches.

        Returns the original action dict that produced the best branch,
        or None if all branches failed.
        """
        best = self._simulator.select_best(branches)
        if best is None or best.failed:
            return None

        return {
            "type": best.plan.option_id,
            "target": "",
            "params": {},
            "reason": f"mentis_simulated(score={best.scores.weighted_score:.3f})",
            "mental_outcome": best.mental_outcome,
            "scores": best.scores.to_dict() if best.scores else None,
        }

    # ─── Reflex Extension ──────────────────────────────────────

    def build_reflex_extension(
        self,
        mental_state: MentalState,
    ) -> dict[str, Any]:
        """
        Build the mental fields to add to a .nail reflex.

        Returns a dict with:
          - mental_match_key: normalized mental signature
          - mental_keywords: categorized mental keywords
          - mental_embedding: 384-dim vector for matching
        """
        return {
            "mental_match_key": build_mental_signature(mental_state),
            "mental_keywords": build_mental_keywords(mental_state),
            "mental_embedding": embed_mental_state(mental_state),
        }

    # ─── Heuristic Parsing (fallback) ──────────────────────────

    def _heuristic_parse_mental_state(self, game_state: dict[str, Any]) -> MentalState:
        """
        Parse mental state using heuristic rules, without an LLM call.

        This is the fallback parser. It infers mental state from
        observable game state signals.
        """
        bond_level = game_state.get("bond_level", 0)
        nearby = game_state.get("nearby", [])
        last_build = game_state.get("last_build", "none")
        time_of_day = game_state.get("time_of_day", "")
        weather = game_state.get("weather", "")

        # Captain's inferred mental state
        captain = AgentMentalState(
            name="Captain",
            role="captain",
        )

        # Infer mood from context
        moods: list[str] = []
        if last_build and last_build != "none":
            moods.append("focused")
            captain.goals.append(f"building {last_build}")
        elif time_of_day == "dawn":
            moods.append("calm")
        elif time_of_day == "night":
            moods.append("tired")
        else:
            moods.append("neutral")

        if weather == "storm":
            moods.append("alert")
        elif weather == "fog":
            moods.append("cautious")

        captain.emotions = moods[:2]
        captain.attention_focus = last_build if last_build != "none" else "general observation"

        # Wesley's inferred mental state
        wesley = AgentMentalState(
            name="Wesley",
            role="ensign",
            goals=["explore", "assist"],
            emotions=["curious"],
            attention_focus="general observation",
        )

        # Social relation
        relation = SocialRelation(
            agent_a="Captain",
            agent_b="Wesley",
            relation_type="captain_ensign",
            trust_level=min(1.0, bond_level / 5.0),
            attitude="trusting" if bond_level >= 3 else "wary" if bond_level <= 1 else "neutral",
        )

        # Atmosphere
        if weather == "storm":
            atmosphere = "tense"
        elif time_of_day in ("golden_hour", "dusk"):
            atmosphere = "contemplative"
        elif bond_level >= 4:
            atmosphere = "warm"
        else:
            atmosphere = "neutral"

        return MentalState(
            agents=[captain, wesley],
            relations=[relation],
            atmosphere=atmosphere,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="heuristic",
        )

    def _render_observation(
        self,
        game_state: dict[str, Any],
        mental_state: MentalState,
    ) -> PartialObservation:
        """
        Render what Wesley can actually perceive.

        Wesley can see:
        - Physical environment (biomes, structures)
        - Captain's position and gross actions (building, moving)
        - Captain's apparent mood (inferred from behavior speed, patterns)

        Wesley cannot see:
        - Captain's specific thoughts or beliefs
        - What the captain is planning
        - Information the captain has that Wesley doesn't
        """
        obs = PartialObservation()

        # Visible agents
        bond = game_state.get("bond_level", 0)
        if bond > 0:
            obs.visible_agents.append("Captain")

        # Visible actions
        last_build = game_state.get("last_build", "none")
        if last_build and last_build != "none":
            obs.visible_actions.append(f"building a {last_build}")
        else:
            obs.visible_actions.append("idle")

        # Inferred moods (from observation, not mind-reading)
        for agent in mental_state.agents:
            if agent.role == "captain":
                # Wesley can infer mood from behavior cues
                obs.inferred_moods = agent.emotions[:2]
                break

        obs.notes = f"Wesley perceives from position ({game_state.get('position', {}).get('x', 0):.0f}, {game_state.get('position', {}).get('z', 0):.0f})"

        return obs

    def _social_guidance(
        self,
        mental_state: MentalState,
        game_state: dict[str, Any],
    ) -> str:
        """
        Generate a one-line social guidance hint.

        This is NOT an action selection — it's a perception that
        informs the LLM's thought generation.
        """
        bond = game_state.get("bond_level", 0)
        captain = None

        for agent in mental_state.agents:
            if agent.role == "captain":
                captain = agent
                break

        if not captain:
            return ""

        captain_mood = captain.emotions[0].lower() if captain.emotions else "neutral"
        captain_goal = captain.goals[0].lower() if captain.goals else ""

        # Generate guidance based on social context
        if "focus" in captain_mood or "build" in captain_goal:
            if bond >= 3:
                return "captain is focused on a task; offer concrete help or observe quietly"
            else:
                return "captain is focused; maintain distance, gather materials"
        elif "frustrat" in captain_mood:
            if bond >= 3:
                return "captain seems frustrated; offer help directly"
            else:
                return "captain seems frustrated; be available but don't intrude"
        elif "calm" in captain_mood or "relax" in captain_mood:
            return "captain is relaxed; natural moment to share observations or explore"
        elif mental_state.atmosphere == "contemplative":
            return "moment of quiet; respect the pause, don't force activity"
        else:
            return "no strong social signal; default to curiosity"

    # ─── LLM Parsing (rich path) ───────────────────────────────

    def _llm_parse_mental_state(self, game_state: dict[str, Any]) -> MentalState:
        """
        Parse mental state using the LLM. This is the rich path.

        Calls Ollama with a state-parsing prompt adapted from the Mentis
        pipeline. Falls back to heuristic parsing on any error.
        """
        prompt = self._build_state_prompt(game_state)

        payload = {
            "model": OLLAMA_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.3, "top_p": 0.9},
        }

        result = _curl_post(OLLAMA_URL, {}, payload, timeout=10)
        if "error" in result:
            # Fall back to heuristic
            return self._heuristic_parse_mental_state(game_state)

        content = result.get("message", {}).get("content", "")
        if not content:
            return self._heuristic_parse_mental_state(game_state)

        self._llm_calls += 1

        # Parse JSON from response
        content = content.strip()
        if "```json" in content:
            start = content.index("```json") + 7
            end = content.index("```", start) if "```" in content[start:] else len(content)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.index("```") + 3
            end = content.index("```", start) if "```" in content[start:] else len(content)
            content = content[start:end].strip()

        try:
            data = json.loads(content)
            return MentalState.from_dict(data)
        except (json.JSONDecodeError, ValueError, KeyError):
            return self._heuristic_parse_mental_state(game_state)

    def _build_state_prompt(self, game_state: dict[str, Any]) -> str:
        """Build the mental state parsing prompt for the LLM."""
        return f"""Parse the social/mental state of this game scene. Return only JSON.

Game state:
- Nearby: {', '.join(game_state.get('nearby', []))}
- Time: {game_state.get('time_of_day', 'unknown')}
- Weather: {game_state.get('weather', 'unknown')}
- Last build: {game_state.get('last_build', 'none')}
- Bond level: {game_state.get('bond_level', 0)}
- Available material: {game_state.get('available_material', 'wood')}

Return JSON with this schema:
{{
  "agents": [
    {{
      "name": "Captain",
      "role": "captain",
      "beliefs": ["what they think is true"],
      "attention_focus": "what they're focused on",
      "goals": ["what they're trying to do"],
      "intentions": ["what they plan to do next"],
      "emotions": ["how they feel"],
      "preferences": ["what they like"],
      "norms": ["social rules they follow"]
    }},
    {{
      "name": "Wesley",
      "role": "ensign",
      ...
    }}
  ],
  "relations": [
    {{
      "agent_a": "Captain",
      "agent_b": "Wesley",
      "relation_type": "captain_ensign",
      "attitude": "trusting/wary/neutral",
      "trust_level": 0.0-1.0
    }}
  ],
  "atmosphere": "calm/tense/focused/playful/neutral"
}}

Infer mental state from observable cues only. Do not invent information
not supported by the game state. Keep all values concise."""

    # ─── Stats ─────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Return adapter statistics for logging."""
        cache_rate = (
            self._cache_hits / max(1, self._ticks)
        )
        return {
            "ticks": self._ticks,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": round(cache_rate, 3),
            "llm_calls": self._llm_calls,
            "avg_render_ms": round(self._total_render_ms / max(1, self._cache_misses), 1),
            "use_llm": self.use_llm,
            "max_branches": self.max_branches,
            "current_mental_source": self._mental_state.source,
            "current_atmosphere": self._mental_state.atmosphere,
        }
