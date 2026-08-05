# mentis-thinker-adapter

> Mental World Modeling layer for the [SuperInstance](https://github.com/SuperInstance) constant thinker.

## What This Is

This adapter integrates [Mentis](https://github.com/SuperInstance/Mentis) — the Mental World Modeling reference implementation — into the Slackwater constant thinker's observe → think → act loop.

The constant thinker runs on a 5-second loop. Previously, it only tracked **physical** game state (position, nearby objects, weather, materials). Mentis adds a **mental** state layer: what do the agents in the scene believe, want, feel? What can each agent actually see? How do actions update mental state, not just physical state?

This is the layer that makes Wesley stop being an autist and start being a crew member who reads the room.

## How It Fits

```
┌─────────┐   ┌───────────┐   ┌───────────┐   ┌──────────┐
│ Observe │──▶│  Parse    │──▶│  Render   │──▶│  Think   │
│ (game   │   │  Mental   │   │  Partial  │   │  (LLM,   │
│  state) │   │  State    │   │  Obs      │   │  mental- │
│         │   │ (cached!) │   │           │   │  aware)  │
└─────────┘   └───────────┘   └───────────┘   └────┬─────┘
                                                    │
┌─────────┐   ┌───────────┐   ┌───────────┐         │
│ Execute │◀──│  Select   │◀──│  Evaluate │◀────────┘
│         │   │  Best     │   │  Branches │
│         │   │           │   │  (sim)    │
└─────────┘   └───────────┘   └───────────┘
```

**New stages** (2, 3, 5, 6) are in this adapter. Existing stages (1, 4, 7) are in `slackwater-cognition/local_thinker/thinker.py`.

## The Caching Strategy

Wesley (Granite 2B) can't run the full Mentis pipeline every tick — it would add 10-25 seconds of LLM calls. The solution: **social delta detection**.

A `SocialDeltaDetector` checks cheap signals every tick:
- Has the captain moved significantly?
- Has the bond level changed?
- Has the captain started/stopped building?
- Has a new agent entered/left?
- Is the cached mental model stale (>5 min)?

If none fire → use cached mental model (0ms, 0 LLM calls). If any fire → re-render (~3-5s, 1-2 LLM calls). In practice, ~85% of ticks are cache hits after the first few minutes.

## Installation

```bash
pip install -e .
```

Python 3.10+. No external dependencies beyond `pytest` for tests.

## Usage

```python
from mentis_adapter import MentisAdapter

# Create adapter (heuristic mode — no LLM needed)
adapter = MentisAdapter(use_llm=False)

# In the thinker loop:
game_state = get_game_state()

# 1. Get mental state (cached or fresh)
mental_state = adapter.get_mental_state(game_state)

# 2. Build enriched context
mental_ctx = adapter.build_mental_context(mental_state, game_state)
enriched_ctx = adapter.enrich_context(physical_context, mental_ctx)

# 3. Generate thought with enriched context
thought = call_llm(system_prompt, enriched_ctx)

# 4. (Optional) Simulate branches for novel situations
branches = adapter.simulate_branches(
    actions=[explore_action, build_action, wait_action],
    bond_level=game_state["bond_level"],
)
best = adapter.select_best_action(branches)
```

## Running Tests

```bash
pytest tests/ -v
```

## Modules

| Module | Purpose |
|--------|---------|
| `mentis_adapter.py` | Main integration: wraps Mentis for the thinker loop |
| `mental_state.py` | Mental state representation + social delta detection |
| `branch_simulator.py` | Simulates how actions update physical + mental state |

## Key Types

- **`MentalState`** — full scene mental state (agents, relations, atmosphere)
- **`AgentMentalState`** — one agent's beliefs, goals, emotions, norms
- **`PartialObservation`** — what Wesley can actually perceive
- **`SocialDeltaDetector`** — cheap check for "has the social situation changed?"
- **`BranchSimulator`** — predicts physical + mental transitions for candidate actions
- **`BranchScore`** — three-dimension scoring (mental, physical, social) + safety veto

## Scoring Weights

From the Mentis paper:

| Dimension | Weight |
|-----------|--------|
| Mental consistency | 0.45 |
| Physical plausibility | 0.35 |
| Social appropriateness | 0.20 |

Safety veto overrides all — vetoes set weighted score to 0.0.

## Design Doc

Full architecture and rationale: [`../MENTIS_INTEGRATION.md`](../MENTIS_INTEGRATION.md)

## License

MIT — same as Mentis and the SuperInstance stack.
