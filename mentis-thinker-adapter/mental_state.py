"""
Mental State — extends the thinker's state representation to include mental variables.

This module adds a mental state layer on top of the existing physical game state.
The mental state tracks what agents in the scene believe, want, feel, and how they
relate to each other socially.

The mental state is designed to be:
  - Cacheable: can be stored and reused across ticks when the social situation hasn't changed
  - Serializable: can be embedded in .nail reflexes
  - Embeddable: can be converted to a vector for reflex matching
  - Lightweight: small enough to live alongside the physical state without bloating the context

Schema adapted from Mentis (mental-world-model) MentalState template.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ─── Mental State Schema ───────────────────────────────────────


@dataclass
class AgentMentalState:
    """
    The mental state of a single agent in the scene.

    Mirrors the Mentis MentalState individual template, simplified for
    the constant thinker's context window.
    """

    name: str = ""
    role: str = ""  # e.g., "captain", "ensign", "npc"

    # Epistemic: what do they know/believe?
    beliefs: list[str] = field(default_factory=list)
    attention_focus: str = ""

    # Motivational: what do they want?
    goals: list[str] = field(default_factory=list)
    intentions: list[str] = field(default_factory=list)

    # Affective: how do they feel?
    emotions: list[str] = field(default_factory=list)

    # Dispositional: what are their preferences?
    preferences: list[str] = field(default_factory=list)

    # Normative: what social rules are they following?
    norms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "beliefs": self.beliefs,
            "attention_focus": self.attention_focus,
            "goals": self.goals,
            "intentions": self.intentions,
            "emotions": self.emotions,
            "preferences": self.preferences,
            "norms": self.norms,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentMentalState:
        return cls(
            name=data.get("name", ""),
            role=data.get("role", ""),
            beliefs=data.get("beliefs", []),
            attention_focus=data.get("attention_focus", ""),
            goals=data.get("goals", []),
            intentions=data.get("intentions", []),
            emotions=data.get("emotions", []),
            preferences=data.get("preferences", []),
            norms=data.get("norms", []),
        )


@dataclass
class SocialRelation:
    """A relationship between two agents."""

    agent_a: str = ""
    agent_b: str = ""
    relation_type: str = ""  # e.g., "captain_ensign", "peer", "stranger"
    attitude: str = ""  # e.g., "trusting", "wary", "fond"
    trust_level: float = 0.5  # 0.0–1.0


@dataclass
class MentalState:
    """
    The full mental state of the scene.

    Contains:
      - agents: mental state of each agent present
      - relations: social relationships between agents
      - atmosphere: overall social atmosphere
      - timestamp: when this state was rendered
      - source: "cached" or "re-rendered"
    """

    agents: list[AgentMentalState] = field(default_factory=list)
    relations: list[SocialRelation] = field(default_factory=list)
    atmosphere: str = ""  # e.g., "calm", "tense", "playful", "focused"
    timestamp: str = ""
    source: str = "unknown"  # "cached" or "re-rendered"

    def to_dict(self) -> dict[str, Any]:
        return {
            "agents": [a.to_dict() for a in self.agents],
            "relations": [
                {
                    "agent_a": r.agent_a,
                    "agent_b": r.agent_b,
                    "relation_type": r.relation_type,
                    "attitude": r.attitude,
                    "trust_level": r.trust_level,
                }
                for r in self.relations
            ],
            "atmosphere": self.atmosphere,
            "timestamp": self.timestamp,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MentalState:
        return cls(
            agents=[AgentMentalState.from_dict(a) for a in data.get("agents", [])],
            relations=[
                SocialRelation(
                    agent_a=r.get("agent_a", ""),
                    agent_b=r.get("agent_b", ""),
                    relation_type=r.get("relation_type", ""),
                    attitude=r.get("attitude", ""),
                    trust_level=r.get("trust_level", 0.5),
                )
                for r in data.get("relations", [])
            ],
            atmosphere=data.get("atmosphere", ""),
            timestamp=data.get("timestamp", ""),
            source=data.get("source", "unknown"),
        )

    def is_empty(self) -> bool:
        return len(self.agents) == 0 and not self.atmosphere


# ─── Mental Signature (for reflex matching) ────────────────────


def build_mental_signature(mental_state: MentalState) -> str:
    """
    Build a compact, normalized mental state signature string.

    This is the text that gets embedded for vector matching.
    Format: "mood=X intent=Y role=Z atmosphere=W bond=B trust=T"

    Two situations with similar mental signatures will produce similar
    embeddings, enabling reflex matching on social context.
    """
    parts: list[str] = []

    for agent in mental_state.agents:
        if agent.role == "captain" or agent.name.lower() == "captain":
            if agent.emotions:
                parts.append(f"captain_mood={','.join(agent.emotions[:3])}")
            if agent.goals:
                parts.append(f"captain_intent={','.join(agent.goals[:2])}")
            if agent.attention_focus:
                parts.append(f"captain_focus={agent.attention_focus}")
        elif agent.role == "ensign" or agent.name.lower() == "wesley":
            if agent.goals:
                parts.append(f"wesley_intent={','.join(agent.goals[:2])}")

    if mental_state.atmosphere:
        parts.append(f"atmosphere={mental_state.atmosphere}")

    for rel in mental_state.relations:
        if "captain" in (rel.agent_a.lower(), rel.agent_b.lower()):
            parts.append(f"trust={rel.trust_level:.1f}")
            if rel.attitude:
                parts.append(f"attitude={rel.attitude}")

    return " ".join(parts) if parts else "mental=unknown"


def build_mental_keywords(mental_state: MentalState) -> dict[str, list[str]]:
    """Extract categorized mental keywords for reflex storage."""
    keywords: dict[str, list[str]] = {
        "captain_mood": [],
        "captain_intent": [],
        "atmosphere": [],
        "social_context": [],
    }

    for agent in mental_state.agents:
        if agent.role == "captain" or agent.name.lower() == "captain":
            keywords["captain_mood"].extend(agent.emotions[:3])
            keywords["captain_intent"].extend(agent.goals[:2])

    if mental_state.atmosphere:
        keywords["atmosphere"].append(mental_state.atmosphere)

    for rel in mental_state.relations:
        if rel.attitude:
            keywords["social_context"].append(rel.attitude)

    # Deduplicate
    for key in keywords:
        keywords[key] = list(set(keywords[key]))

    # Remove empty categories
    return {k: v for k, v in keywords.items() if v}


# ─── Mental Embedding ──────────────────────────────────────────


def embed_mental_state(mental_state: MentalState, dim: int = 384) -> list[float]:
    """
    Lightweight hash embedding of the mental signature.

    Same algorithm as the existing embed_hash in distillation_loop,
    applied to the mental signature instead of the physical one.
    """
    signature = build_mental_signature(mental_state)
    return embed_hash_text(signature, dim)


def embed_hash_text(text: str, dim: int = 384) -> list[float]:
    """Hash-based embedding for arbitrary text (mirrors distillation_loop.embed_hash)."""
    text = text.lower().strip()
    words = text.split()
    vec = [0.0] * dim

    # Trigram features
    padded = f"^{text}$"
    for i in range(len(padded) - 2):
        trigram = padded[i : i + 3]
        h = hashlib.sha256(trigram.encode()).digest()
        idx = int.from_bytes(h[:4], "big") % (dim * 2 // 3)
        weight = 0.5 + (int.from_bytes(h[4:8], "big") / 0xFFFFFFFF) * 0.5
        vec[idx] += weight

    # Word features
    stopwords = frozenset(
        {"the", "a", "an", "is", "are", "to", "of", "and", "or", "in", "for", "it", "that", "with"}
    )
    for word in words:
        w = word.strip(".,!?;:\"'()[]{}-").lower()
        if not w or w in stopwords:
            continue
        h = hashlib.sha256(w.encode()).digest()
        idx = (int.from_bytes(h[:4], "big") % (dim // 3)) + (dim * 2 // 3)
        vec[idx] += 1.0

    # L2 normalize
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


# ─── Social Delta Detection ────────────────────────────────────


@dataclass
class SocialDeltaDetector:
    """
    Detects whether the social situation has changed enough to warrant
    a mental state re-render.

    The detector compares cheap signals against cached values. If none
    of the signals have changed beyond threshold, the cached mental
    model is still valid and no LLM call is needed.

    Usage:
        detector = SocialDeltaDetector()
        if detector.has_social_delta(game_state, mental_state_cache):
            mental_state = re_render(game_state)
            detector.update_cache(game_state, mental_state)
        else:
            mental_state = mental_state_cache  # reuse
    """

    _last_agent_set: set[str] = field(default_factory=set)
    _last_captain_pos: tuple[float, float, float] = (0.0, 0.0, 0.0)
    _last_captain_message_hash: str = ""
    _last_bond_level: int = 0
    _last_activity: str = ""
    _last_render_time: float = 0.0
    _staleness_threshold_seconds: float = 300.0  # 5 minutes
    _position_threshold: float = 25.0  # squared distance

    def has_social_delta(
        self,
        game_state: dict[str, Any],
        cached_mental: MentalState | None,
        current_time: float | None = None,
    ) -> bool:
        """
        Returns True if the social situation has changed enough to
        warrant a mental state re-render.
        """
        import time as _time

        now = current_time or _time.time()

        # No cache → must render
        if cached_mental is None or cached_mental.is_empty():
            return True

        # Staleness check
        if self._last_render_time > 0:
            age = now - self._last_render_time
            if age > self._staleness_threshold_seconds:
                return True

        # Agent set change
        current_agents = set()
        nearby = game_state.get("nearby", [])
        for item in nearby:
            if isinstance(item, str) and item not in (
                "dock", "workshop", "ocean", "forest", "tower", "beach", "cliff", "garden"
            ):
                current_agents.add(item)
        # Also check for captain presence via game state
        if game_state.get("bond_level", 0) > 0:
            current_agents.add("captain")

        if current_agents != self._last_agent_set:
            return True

        # Bond level change
        bond = game_state.get("bond_level", 0)
        if bond != self._last_bond_level:
            return True

        # Captain position change (large movement = new social context)
        pos = game_state.get("position", {})
        captain_pos = (
            pos.get("x", 0),
            pos.get("y", 0),
            pos.get("z", 0),
        )
        dx = captain_pos[0] - self._last_captain_pos[0]
        dy = captain_pos[1] - self._last_captain_pos[1]
        dz = captain_pos[2] - self._last_captain_pos[2]
        dist_sq = dx * dx + dy * dy + dz * dz
        if dist_sq > self._position_threshold:
            return True

        # Captain message change (if we track messages)
        last_message = game_state.get("last_message", "")
        msg_hash = hashlib.sha256(last_message.encode()).hexdigest()[:16] if last_message else ""
        if msg_hash and msg_hash != self._last_captain_message_hash:
            return True

        # Activity change (including WHAT is being built)
        last_build = game_state.get("last_build", "")
        activity = last_build if (last_build and last_build != "none") else "idle"
        if activity != self._last_activity:
            return True

        # No significant change detected
        return False

    def update_cache(
        self,
        game_state: dict[str, Any],
        render_time: float | None = None,
    ) -> None:
        """Update the cached comparison values after a re-render."""
        import time as _time

        pos = game_state.get("position", {})
        self._last_captain_pos = (
            pos.get("x", 0),
            pos.get("y", 0),
            pos.get("z", 0),
        )
        self._last_bond_level = game_state.get("bond_level", 0)

        last_message = game_state.get("last_message", "")
        self._last_captain_message_hash = (
            hashlib.sha256(last_message.encode()).hexdigest()[:16] if last_message else ""
        )

        last_build = game_state.get("last_build", "")
        self._last_activity = last_build if (last_build and last_build != "none") else "idle"

        nearby = game_state.get("nearby", [])
        self._last_agent_set = set()
        for item in nearby:
            if isinstance(item, str) and item not in (
                "dock", "workshop", "ocean", "forest", "tower", "beach", "cliff", "garden"
            ):
                self._last_agent_set.add(item)
        if game_state.get("bond_level", 0) > 0:
            self._last_agent_set.add("captain")

        self._last_render_time = render_time or _time.time()


# ─── Partial Observation ────────────────────────────────────────


@dataclass
class PartialObservation:
    """
    What the target agent (Wesley) can actually perceive.

    This is NOT the full world state. Wesley doesn't have access to the
    captain's thoughts or feelings — only to observable cues:
    body language, speech, gaze direction, build speed, etc.

    Mirrors the Mentis Observation concept: filter the world state
    through the target agent's perceptual access.
    """

    visible_agents: list[str] = field(default_factory=list)
    visible_actions: list[str] = field(default_factory=list)
    inferred_moods: list[str] = field(default_factory=list)
    can_hear: bool = True
    can_see: bool = True
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "visible_agents": self.visible_agents,
            "visible_actions": self.visible_actions,
            "inferred_moods": self.inferred_moods,
            "can_hear": self.can_hear,
            "can_see": self.can_see,
            "notes": self.notes,
        }

    def to_context_string(self) -> str:
        """Render as a concise string for the LLM context window."""
        parts: list[str] = []
        if self.visible_agents:
            parts.append(f"You can see: {', '.join(self.visible_agents)}")
        if self.visible_actions:
            parts.append(f"Their actions: {', '.join(self.visible_actions)}")
        if self.inferred_moods:
            parts.append(f"Apparent mood: {', '.join(self.inferred_moods)}")
        if self.notes:
            parts.append(self.notes)
        return ". ".join(parts) + "." if parts else ""
