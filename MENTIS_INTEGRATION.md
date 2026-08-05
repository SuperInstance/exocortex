# Mentis Integration — Mental World Modeling for the Constant Thinker

**Version:** 1.0 · **Date:** 2026-08-04 · **Status:** Design doc + prototype

> *Wesley stops being an autist and starts being a crew member who reads the room.*

---

## Table of Contents

1. [The Problem](#1-the-problem)
2. [What Mentis Adds](#2-what-mentis-adds)
3. [Pipeline Mapping](#3-pipeline-mapping)
4. [Mental State in the .nail Reflex Format](#4-mental-state-in-the-nail-reflex-format)
5. [The Caching Strategy — Compile, Don't Compute](#5-the-caching-strategy--compile-dont-compute)
6. [How the Distillation Loop Teaches Mental Modeling](#6-how-the-distillation-loop-teaches-mental-modeling)
7. [What the Captain Experiences Differently](#7-what-the-captain-experiences-differently)
8. [Five Scenarios Where Mental State Changes the Action](#8-five-scenarios-where-mental-state-changes-the-action)
9. [Performance Considerations](#9-performance-considerations)
10. [Architecture Diagram](#10-architecture-diagram)

---

## 1. The Problem

The current thinker loop is:

1. **Observe** physical state (sensors, game state)
2. **Generate** a thought (LLM lean)
3. **Select** an action from the thought
4. **Execute** the action

This produces an agent that is physically competent but socially blind. Wesley can explore, build, inspect, and wait — but he cannot read the room. He doesn't know what the captain believes about the current situation. He doesn't know whether his build request will be welcomed or seen as interrupting. He doesn't factor in what other agents in the scene can see, know, or want.

In the TWO_AGENTS_NOT_ONE framing: the ensign is competent within their training but lost without it. The ensign's training currently covers only physical patterns — when to explore vs build vs wait. It doesn't cover social patterns — when to speak vs stay silent vs defer.

The existing reflex system (.nail files) compounds this. Reflexes are compiled from physical game state: biome, time, weather, materials, position. Two situations with identical physical state but radically different social context (the captain is frustrated vs the captain is relaxed) produce the same situation signature, the same embedding, and the same reflex match. The agent treats all frustrated captains the same as relaxed ones.

**This is the layer that makes Wesley socially intelligent.**

---

## 2. What Mentis Adds

Mentis (from the paper *Mental World Modeling*, Fei & Zhao 2026) introduces a coupled physical-mental state representation. Instead of tracking only the physical scene, the model maintains:

- **Physical state** — objects, characters, spatial relations, environment (what the current thinker already tracks)
- **Mental state** — what each agent believes, wants, feels, attends to, intends, and considers socially permissible

The Mentis pipeline has five stages:

1. **State parsing** — parse the scene into coupled (physical, mental) world state `s_t`
2. **Observation rendering** — compute what the target agent can actually perceive `o_t` (partial, not omniscient)
3. **Action decomposition** — split each candidate action into physical and mental components
4. **Branch simulation** — for each action, predict how it updates BOTH physical AND mental state
5. **Branch evaluation** — score each branch on mental consistency, physical plausibility, and social appropriateness

The key insight: **actions have mental effects**. Saying "nice work" is physically just vibrations in air, but mentally it updates the listener's affective state, their belief about the speaker's attitude, and their willingness to cooperate in the future. A world model that only tracks the vibrations misses the entire point of the action.

---

## 3. Pipeline Mapping

Here is how the Mentis pipeline maps onto the existing thinker loop:

### Current Loop (4 stages)

```
┌─────────┐     ┌──────────┐     ┌──────────┐     ┌─────────┐
│ Observe │ ──▶ │  Think   │ ──▶ │  Select  │ ──▶ │ Execute │
│ (game   │     │ (LLM     │     │ (policy  │     │ (worker │
│  state) │     │  lean)   │     │  table)  │     │  API)   │
└─────────┘     └──────────┘     └──────────┘     └─────────┘
```

### Enhanced Loop (7 stages with Mentis)

```
┌─────────┐     ┌───────────┐     ┌───────────┐     ┌──────────┐
│ Observe │ ──▶ │  Parse    │ ──▶ │  Render   │ ──▶ │  Think   │
│ (game   │     │  Mental   │     │  Partial  │     │  (LLM,   │
│  state) │     │  State    │     │  Obs      │     │  now     │
│         │     │ (cached/  │     │ (what     │     │  mental- │
│         │     │  re-render│     │  Wesley   │     │  aware)  │
│         │     │  on Δ)    │     │  sees)    │     │          │
└─────────┘     └───────────┘     └───────────┘     └────┬─────┘
                                                         │
┌─────────┐     ┌───────────┐     ┌───────────┐          │
│ Execute │ ◀── │  Select   │ ◀── │  Evaluate │ ◀────────┘
│ (worker │     │  Best     │     │  Branches │
│  API)   │     │  Branch   │     │  (sim +   │
│         │     │           │     │   score)  │
└─────────┘     └───────────┘     └───────────┘
```

### Stage-by-Stage Mapping

| Step | Current Thinker | Mentis-Enhanced | What Changed |
|------|----------------|-----------------|--------------|
| 1. Observe | `get_game_state()` | `get_game_state()` | No change — still reads physical sensors |
| 2. Parse mental state | *(nothing)* | `MentisAdapter.parse_mental_state()` | **NEW**: What do agents believe, want, feel? |
| 3. Render partial observation | *(nothing)* | `MentisAdapter.render_observation()` | **NEW**: What does Wesley actually see/know? |
| 4. Generate thought | `call_llm(system_prompt, context)` | `call_llm(system_prompt, mental_context)` | Context now includes mental state |
| 5. Simulate candidate actions | *(nothing)* | `BranchSimulator.simulate(actions, state)` | **NEW**: How does each action update physical+mental? |
| 6. Evaluate branches | `ActionPolicy.select_action(lean, state)` | `BranchSimulator.score_branches(branches)` | Policy table → coupled physical-mental scoring |
| 7. Execute | `execute_action(action)` | `execute_action(action)` | No change |

**Steps 2, 3, and 5 are new. Step 4 is enriched. Step 6 is upgraded.**

---

## 4. Mental State in the .nail Reflex Format

The existing .nail reflex format stores physical situation signatures:

```
biome=dock time=dusk weather=fog material=wood action=explore bond=3 | thought excerpt
```

Mental modeling extends the situation signature with a **mental signature**:

```
biome=dock time=dusk weather=fog material=wood action=explore bond=3
| mental: captain_mood=focused captain_intent=building wesley_role=assist
| social_context=cooperative work_mode focus=task
| thought excerpt
```

### Extended .nail Schema

```json
{
  "id": "a1b2c3d4e5f67890",
  "match_key": "biome=dock time=dusk weather=fog action=explore bond=3 pos=NE",
  "situation": "biome=dock time=dusk ... | captain_mood=focused ...",
  "mental_match_key": "captain_mood=focused captain_intent=building social=cooperative mode=task",
  "situation_keywords": {
    "biomes": ["dock"],
    "times": ["dusk"],
    "weather": ["fog"],
    "actions": ["explore"],
    "emotions": ["focused", "calm"]
  },
  "mental_keywords": {
    "captain_mood": ["focused"],
    "captain_intent": ["building"],
    "social_context": ["cooperative"],
    "work_mode": ["task"]
  },
  "action": "explore nearby_materials",
  "outcome": "good",
  "outcome_quality": 0.72,
  "confidence": 0.65,
  "embedding": [...384 dims...],
  "mental_embedding": [...384 dims...],
  "metadata": {
    "beat": 42,
    "timestamp": "2026-08-04T17:00:00Z",
    "source": "local-thinker",
    "mental_source": "cached",  // or "re-rendered"
    "social_delta_detected": true,
    "prompt_version": "v3_mental"
  }
}
```

### Key Additions

| Field | Purpose |
|-------|---------|
| `mental_match_key` | Normalized mental state signature for deterministic matching |
| `mental_keywords` | Categorized mental state keywords |
| `mental_embedding` | Separate embedding vector for mental state matching |
| `mental_source` | Whether the mental state was cached or freshly rendered |
| `social_delta_detected` | Whether the social situation changed this tick |

The reflex matcher now does **two-stage matching**:
1. Match physical situation (existing behavior)
2. Among physical matches, match mental situation (new)
3. If both match above threshold → exact reflex hit (bypass LLM)
4. If physical matches but mental doesn't → re-render mental state, then re-match

This means reflexes accumulate social intelligence over time. After 100 interactions with a frustrated captain at the dock, Wesley has a dense cluster of reflexes for "frustrated captain + dock" that fire automatically.

---

## 5. The Caching Strategy — Compile, Don't Compute

**Key constraint:** Wesley (Granite 2B) cannot run the full Mentis pipeline on every tick. The pipeline involves 3-5 LLM calls (state parse, observation render, branch simulation per action, scoring). On a 2B model, each call takes 2-5 seconds. That's 10-25 seconds per tick — unacceptable for a 5-second think interval.

### The Solution: Social Delta Detection

The mental model is **cached** and only re-rendered when the social situation changes. This mirrors MOSTLY_SILENCE: the ensign only speaks when reality diverges from prediction. Here, the ensign only re-renders the mental model when the social reality diverges from the cached model.

```
┌─────────────────────────────────────────────────┐
│              EVERY TICK (5s loop)                │
│                                                  │
│  1. Get physical game state           [~50ms]    │
│  2. Check: has social situation      [~5ms]      │
│     changed? (social delta detector)             │
│     ├─ NO → Use cached mental model  [0ms]       │
│     └─ YES → Re-render mental model  [3-5s]      │
│  3. Build context (physical + mental) [~5ms]     │
│  4. Generate thought (LLM)           [2-3s]      │
│  5. Select action (reflex or policy) [~1ms-2s]   │
│  6. Execute                          [~500ms]    │
└─────────────────────────────────────────────────┘
```

### Social Delta Detection

How does Wesley know the social situation changed? By checking a set of cheap signals:

| Signal | How to Check | Cost | Sensitivity |
|--------|-------------|------|-------------|
| Captain's position changed significantly | Distance from last render > threshold | 0ms (math) | Low — captain moves constantly |
| New agent entered/left the scene | Compare agent list to cached | 0ms (set diff) | High — new people always matter |
| Captain's last message changed | Compare message hash to cached | 0ms (hash compare) | High — speech usually signals change |
| Bond level changed | Compare to cached | 0ms (int compare) | Medium — gradual changes matter |
| Time since last render > N minutes | Timestamp math | 0ms | Safety net — staleness check |
| Captain's activity type changed | Was building, now idle | 0ms (enum compare) | High — activity transitions matter |

The detector runs on every tick but costs essentially nothing — a few comparisons against cached values. If none of these fire, the mental model from N ticks ago is still valid.

### What Gets Compiled into Reflexes

Following the Pincher pattern (cloud learns → compiles into reflex → local executes), mental modeling knowledge gets compiled in three tiers:

**Tier 1: Mental situation signatures** (immediate)
- Every tick, the mental state signature is cached alongside the physical signature
- When a thought is journaled, both signatures are compiled into the .nail reflex
- The reflex matcher gains a second matching dimension

**Tier 2: Mental transition patterns** (after distillation)
- After enough samples, the distillation loop learns: "when the captain says X and the context is Y, the mental effect is Z"
- These patterns compile into `.nail.mental` reflexes — mappings from (observed behavior → mental state update)
- Eventually Wesley can predict mental effects without calling the LLM at all

**Tier 3: Social appropriateness policies** (after consistent distillation)
- After the distillation loop consistently confirms that certain social patterns help, they get promoted to the system prompt
- Example: "When the captain is focused on a build, do not initiate conversation unless the observation is urgent"
- These become permanent personality traits, not per-tick computations

---

## 6. How the Distillation Loop Teaches Mental Modeling

The existing distillation loop has 5 stages: Teacher → Student → Evaluate → Distill → Update. Here's how each stage extends for mental modeling:

### Stage 1: Teacher (GLM generates lessons about social intelligence)

New teaching topics added to the `TEACHING_TOPICS` dict:

```python
"social-cognition": [
    "Theory of mind: modeling what other agents believe, want, and feel",
    "Partial observability: reasoning about what others can and cannot see",
    "Conversational implicature: what is meant but not said",
    "Social appropriateness: reading normative context and adjusting behavior",
    "Emotional regulation: how to respond when the captain is frustrated",
    "Timing: when to speak vs when to stay silent vs when to act",
    "Deference and initiative: knowing when to lead and when to follow",
    "Reading build patterns: what the captain's construction reveals about intent",
    "Cooperative problem-solving: contributing without being asked",
    "Conflict de-escalation: how to reduce tension in social situations",
],
```

New task sources for social-cognition domain use transcripts of multi-agent interactions (captain + Wesley scenarios), annotated with mental state ground truth from the Mentis pipeline.

### Stage 2: Student (Granite applies social lessons)

The student prompt changes. Instead of reviewing code, Granite reviews interaction scenarios:

```
A teacher explains: [lesson about reading social cues]

Now apply this to the following scenario:

Scenario: The captain has been building a tower for 20 minutes.
You (Wesley) just found a rare copper deposit nearby. The captain
hasn't spoken in the last 5 ticks. Bond level is 3.

What should you do? Consider what the captain might be feeling,
thinking, and wanting. Consider whether interrupting would help
or hinder.
```

### Stage 3: Evaluate (score social intelligence)

Quality scoring adds new dimensions:

```python
def score_mental_response(text: str) -> dict[str, float]:
    return {
        "mental_awareness": ...,     # References to others' beliefs, goals, emotions
        "social_appropriateness": ..., # Norm-aware reasoning, deference, timing
        "perspective_taking": ...,   # Uses the target agent's viewpoint, not omniscient
        "behavioral_specificity": ..., # Concrete action proposals, not vague platitudes
    }
```

### Stage 4: Distill (compile social reflexes)

When teaching helps, it compiles into `.nail.mental` reflexes — mappings from social situation patterns to appropriate social actions. These are stored with a `domain: "social-cognition"` tag and matched at runtime using the mental embedding.

### Stage 5: Update (promote consistent social patterns)

After 3 consecutive positive deltas on a social-cognition topic, it promotes to the system prompt. Wesley's permanent personality grows social intelligence over time.

Example promoted directive:

```
[SOCIAL-COGNITION] When the captain is silently focused on a build
and bond level ≥ 3, do not initiate conversation. Wait for a natural
pause or until the build is complete. If you find something noteworthy,
note it in the journal rather than speaking aloud.
```

---

## 7. What the Captain Experiences Differently

### Before Mental Modeling (Current Wesley)

The captain experiences Wesley as:
- **Present but oblivious.** Wesley is there, doing things, but doesn't seem aware of the captain's state.
- **Timing-deaf.** Wesley speaks during builds, interrupts focused work, stays silent during natural pauses.
- **Literal.** Wesley takes everything at face value. Sarcasm, frustration, enthusiasm — all met with the same procedural response.
- **Self-centered.** Wesley's thoughts are about what Wesley sees and wants. The captain is part of the environment, not a mind to be considered.

### After Mental Modeling

The captain experiences Wesley as:
- **Reads the room.** Wesley adjusts behavior based on the captain's apparent state. When the captain is focused, Wesley works quietly. When the captain is exploring, Wesley suggests things to investigate.
- **Times interventions.** Wesley speaks when it matters and stays silent when it doesn't. This is the MOSTLY_SILENCE principle applied to social behavior — the social delta detector ensures Wesley only "speaks" mentally when the social situation changes.
- **Considers the captain's perspective.** Wesley's thoughts include what the captain might want, not just what Wesley wants. "The captain hasn't seen this copper deposit yet — they'd want to know, but they're focused on the tower. I'll note it."
- **Builds social reflexes.** Over time, Wesley develops cached responses to social patterns. "Captain frustrated + build failing" → reflex: offer to gather materials. This becomes automatic, not computed.

### The渐进 Development

This isn't instant. Wesley's social intelligence grows through the same distillation loop that teaches physical intelligence:

1. **Week 1-2:** Mental state is parsed but mostly wrong. Social delta fires constantly (everything is new). Wesley is awkward but trying.
2. **Week 3-4:** Social reflexes start forming. Common patterns (captain building, captain exploring, captain idle) get cached responses. Delta detection becomes more selective.
3. **Month 2-3:** Wesley has distinct social responses for dozens of situations. The mental model is re-rendered only a few times per session, not every tick.
4. **Month 6+:** Wesley's social behavior is mostly reflex-driven. The LLM is used only for genuinely novel social situations. The captain experiences Wesley as someone who "gets it."

---

## 8. Five Scenarios Where Mental State Changes the Action

### Scenario 1: The Frustrated Builder

**Physical state:** Dock, dusk, fog, wood. Captain is at position (10, 5, -20) near a half-built tower. Bond level 3.

**Without mental modeling:**
- Wesley's thought: "The fog is interesting. I want to explore the eastern cliff."
- Action: `explore` toward eastern cliff.
- Result: Wesley wanders off while the captain struggles alone with the tower.

**With mental modeling:**
- Mental state parse: Captain's body language suggests frustration (repeated build attempts, no progress). Captain's goal: complete the tower. Captain's attention: focused on joinery. Captain does NOT need exploration right now.
- Partial observation: Wesley can see the captain struggling but can't hear specific muttering.
- Thought: "The captain's been on that tower for a while. The fog makes it harder. I have wood — I could bring materials closer, or inspect the foundation for issues."
- Simulated branches:
  - Explore cliff: physically fine, mentally ignores captain's needs, socially inappropriate (abandoning a struggling partner)
  - Bring wood closer: physically useful, mentally supportive, socially appropriate ✓
  - Inspect foundation: physically useful, mentally helpful, socially appropriate ✓
  - Wait: physically passive, mentally dismissive, socially neutral
- Selected: Bring wood closer (highest combined score)

### Scenario 2: The Silent Pause

**Physical state:** Workshop, midday, clear, stone. Captain is idle at position (5, 3, 5). No build in progress. Bond level 4.

**Without mental modeling:**
- Wesley's thought: "I should build something. Let me start a wall."
- Action: `build wall with stone`
- Result: Wesley starts building without consultation, possibly disrupting the captain's planning time.

**With mental modeling:**
- Mental state parse: Captain is idle but not frustrated — appears to be thinking or enjoying the moment. No urgent goal detected. Atmosphere is calm.
- Partial observation: Wesley can see the captain standing still, looking at the horizon. This is a contemplative pause, not an action gap.
- Thought: "The captain is paused. Not frustrated, not building. This feels like a moment of appreciation. I don't want to break it with construction noise."
- Simulated branches:
  - Build wall: physically fine, mentally disruptive (breaks contemplation), socially inappropriate
  - Wait quietly: physically passive, mentally respectful, socially appropriate ✓
  - Explore: physically fine, mentally neutral, socially neutral
  - Speak: physically fine, mentally interrupts thought, socially inappropriate
- Selected: Wait quietly

### Scenario 3: The Shared Discovery

**Physical state:** Beach, dawn, clear, copper. A new cave entrance is visible at position (-30, 0, 15). Captain hasn't seen it yet (facing away). Bond level 5.

**Without mental modeling:**
- Wesley's thought: "A cave! I want to explore it."
- Action: `explore` toward cave
- Result: Wesley runs off into the cave alone. The captain misses the discovery moment.

**With mental modeling:**
- Mental state parse: Captain is relaxed, exploring the beach. Goal: casual exploration. Attention: facing the water, hasn't noticed the cave. Belief: beach is just sand and water (incomplete — doesn't know about cave).
- Partial observation: Wesley can see both the cave AND the captain's facing direction. Wesley knows the captain doesn't know about the cave.
- Thought: "There's a cave the captain hasn't seen. At bond 5, we share discoveries. The captain would want to know — this changes their beach exploration entirely."
- Simulated branches:
  - Explore cave alone: physically fine, mentally excludes captain from discovery, socially misses the moment
  - Speak ("cave!"): physically fine, mentally shares discovery, socially appropriate at bond 5 ✓
  - Wait: physically passive, mentally withholds information, socially inappropriate at bond 5
  - Inspect cave entrance: physically fine, mentally goes halfway — signals without fully exploring ✓
- Selected: Speak — call attention to the cave

### Scenario 4: The Interrupted Build

**Physical state:** Forest, night, storm, wood. Captain is building a shelter. Storm is intensifying. Bond level 2 (low — early relationship).

**Without mental modeling:**
- Wesley's thought: "The storm is getting worse. I feel anxious."
- Action: `wait` (defaulting to passive)
- Result: Wesley stands in the rain doing nothing while the captain builds desperately.

**With mental modeling:**
- Mental state parse: Captain is focused, urgent — building speed indicates stress. Goal: complete shelter before storm worsens. The captain's mental state does not include awareness of Wesley's presence as helpful (bond 2 — relationship is new, trust is low).
- Partial observation: Wesley can see the captain building urgently and the storm intensifying. Wesley cannot assume the captain wants help — bond is too low for uninvited collaboration.
- Thought: "The captain needs shelter fast. But at bond 2, I can't just start building — that might feel like intrusion. I can gather materials and leave them nearby. That helps without overstepping."
- Simulated branches:
  - Help build directly: physically helpful, mentally oversteps trust level, socially risky at bond 2
  - Gather materials and place nearby: physically helpful, mentally supportive without overstepping, socially appropriate ✓
  - Wait: physically passive, mentally unhelpful, socially inappropriate (storm emergency)
  - Speak: physically fine, mentally adds cognitive load to urgent task, socially inappropriate
- Selected: Gather materials and place near build site

### Scenario 5: The Captain's Mistake

**Physical state:** Cliff, golden_hour, clear, glass. Captain just placed a glass wall section in a structurally unsound position. The wall will collapse if weight is added. Bond level 5.

**Without mental modeling:**
- Wesley's thought: "The cliff edge has an interesting texture."
- Action: `inspect cliff edge`
- Result: Wesley examines rocks while the captain's build is about to fail.

**With mental modeling:**
- Mental state parse: Captain is satisfied with the placement — believes the wall is sound. Captain's goal: aesthetic glass structure. Captain does NOT know about the structural issue. Wesley can see the issue but the captain's back is to the weak point.
- Partial observation: Wesley sees the bad joinery and the captain's satisfied expression. Wesley knows something the captain doesn't — an information asymmetry.
- Thought: "The captain doesn't see what I see. At bond 5, I should speak up — they'd want to know before adding weight. But I should frame it as observation, not criticism."
- Simulated branches:
  - Inspect cliff: physically fine, mentally ignores known danger, socially inappropriate (withholds critical info at bond 5)
  - Speak ("that wall section looks unstable"): physically fine, mentally shares critical info respectfully, socially appropriate ✓
  - Build a support brace silently: physically helpful, mentally fixes without informing, socially mixed (undermines learning)
  - Wait: physically passive, mentally allows failure, socially inappropriate
- Selected: Speak — alert the captain to the structural issue

---

## 9. Performance Considerations

### The Cost Budget

The thinker runs on a 5-second interval. Current per-tick costs:

| Component | Time | LLM Calls |
|-----------|------|-----------|
| get_game_state | ~50ms | 0 |
| build_context | ~5ms | 0 |
| call_llm | ~2-3s | 1 |
| action_policy.select_action | ~1ms | 0 |
| execute_action | ~500ms | 0 |
| **Total** | **~3s** | **1** |

Mentis adds overhead. The naive cost of running the full pipeline every tick:

| Mentis Stage | Time (on Granite 2B) | LLM Calls |
|-------------|---------------------|-----------|
| parse_state | ~3s | 1 |
| render_observation | ~3s | 1 |
| decompose_actions | ~3s | 1 |
| simulate_branches (×5 actions) | ~15s | 5 (parallel: ~3s wall) |
| score_branches | ~3s | 1 |
| **Total naive** | **~27s serial / ~12s parallel** | **9** |

**This is unacceptable.** 12 seconds per tick on a 5-second interval. The caching strategy is what makes it feasible.

### The Cached Cost

With social delta detection, most ticks skip the expensive Mentis stages:

| Scenario | Frequency | Per-Tick Cost | LLM Calls |
|----------|-----------|---------------|-----------|
| Social situation unchanged (cache hit) | ~85% of ticks | +0ms | +0 |
| Social situation changed (cache miss) | ~10% of ticks | +6s (2 LLM calls) | +2 |
| Reflex match hits (bypass LLM entirely) | ~70% after maturity | -2.5s | -1 |
| Branch simulation needed (novel situation) | ~5% of ticks | +12s (spread over ticks) | +9 |

**Effective average per-tick cost at maturity:**

| Component | Avg Time | Avg LLM Calls |
|-----------|----------|---------------|
| Physical game state | 50ms | 0 |
| Social delta check | 5ms | 0 |
| Mental state (cached or re-rendered) | 450ms avg | 0.2 avg |
| Thought generation (or reflex hit) | 750ms avg | 0.3 avg |
| Action selection (policy or branch sim) | 600ms avg | 0.1 avg |
| Execute | 500ms | 0 |
| **Total** | **~2.4s** | **~0.6 avg** |

**The enhanced thinker is actually faster than the current one at maturity** because reflex hits bypass the LLM call entirely. Mental modeling pays for itself by improving reflex hit rates — more situations have cached responses because the mental dimension adds discriminative power.

### Keeping It Fast Enough During Development

During early operation (first 1-2 weeks, before reflexes accumulate):

1. **Run branch simulation asynchronously.** The thinker doesn't block on simulation. It picks the best available action immediately (from cache or policy), then simulates branches in the background for learning.
2. **Limit branch simulation to 3 actions** (not 6). The top 3 from the action policy's weighting are sufficient.
3. **Use Ollama for branch simulation, not GLM.** Local is free and has no rate limits. Quality is lower but acceptable for learning (not for action selection — the reflex/policy path handles that).
4. **Batch mental state renders.** If 3 ticks in a row trigger social delta, render once on the first and cache for the next 2.
5. **Fall back gracefully.** If Ollama is down or slow, skip Mentis entirely and run the original 4-stage loop. The thinker must never stall because the mental model is unavailable.

---

## 10. Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                    THE CONSTANT THINKER                               │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │  PHYSICAL LAYER (existing)                                    │    │
│  │                                                                │    │
│  │  ┌─────────┐   ┌──────────┐   ┌──────────┐   ┌─────────┐    │    │
│  │  │ Observe │──▶│  Think   │──▶│  Select  │──▶│ Execute │    │    │
│  │  │ (game   │   │ (LLM     │   │ (policy  │   │ (worker │    │    │
│  │  │  state) │   │  lean)   │   │  table)  │   │  API)   │    │    │
│  │  └─────────┘   └──────────┘   └──────────┘   └─────────┘    │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │  MENTAL LAYER (Mentis adapter — NEW)                          │    │
│  │                                                                │    │
│  │  ┌───────────────┐   ┌───────────────────┐                    │    │
│  │  │ Social Delta  │   │ Mental State      │                    │    │
│  │  │ Detector      │──▶│ Cache             │                    │    │
│  │  │ (cheap checks)│   │ (beliefs, goals,  │                    │    │
│  │  └───────┬───────┘   │  emotions, norms) │                    │    │
│  │          │           └────────┬──────────┘                    │    │
│  │    no Δ  │ Δ detected         │                                │    │
│  │     │    │                    │ re-render                      │    │
│  │     ▼    ▼                    ▼                                │    │
│  │  ┌───────────────┐   ┌───────────────────┐                    │    │
│  │  │ Use cached    │   │ Parse Mental      │                    │    │
│  │  │ mental model  │   │ State (LLM call)  │                    │    │
│  │  │ (0ms, 0 LLM)  │   │ + Render Partial  │                    │    │
│  │  └───────┬───────┘   │   Observation     │                    │    │
│  │          │           └────────┬──────────┘                    │    │
│  │          └────────────────────┘                                │    │
│  │                   │                                            │    │
│  │                   ▼                                            │    │
│  │  ┌───────────────────────────────────────────────────────┐    │    │
│  │  │  ENRICHED CONTEXT (physical + mental → LLM prompt)     │    │    │
│  │  │  "Dock, dusk, fog. Captain is frustrated with tower.  │    │    │
│  │  │   Bond 3. You can see they're struggling but can't    │    │    │
│  │  │   hear their muttering. You have wood."               │    │    │
│  │  └───────────────────────────────────────────────────────┘    │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │  REFLEX LAYER (existing, extended)                             │    │
│  │                                                                │    │
│  │  ┌────────────────┐   ┌────────────────┐                      │    │
│  │  │ Physical Match │   │ Mental Match   │                      │    │
│  │  │ (.nail files)  │──▶│ (.nail.mental) │                      │    │
│  │  │ cosine sim on  │   │ cosine sim on  │                      │    │
│  │  │ physical sig   │   │ mental sig     │                      │    │
│  │  └────────────────┘   └────────────────┘                      │    │
│  │           │                        │                          │    │
│  │           └──────────┬─────────────┘                          │    │
│  │                      ▼                                        │    │
│  │           ┌─────────────────────┐                             │    │
│  │           │ Both match? → EXACT │ → bypass LLM entirely       │    │
│  │           │ One match? → SIMILAR│ → use as hint, refine w/LLM │    │
│  │           │ Neither?  → NOVEL   │ → full LLM + branch sim     │    │
│  │           └─────────────────────┘                             │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │  BRANCH SIMULATION (background, only on NOVEL or SIMILAR)     │    │
│  │                                                                │    │
│  │  For each candidate action:                                   │    │
│  │    1. Predict physical state transition                       │    │
│  │    2. Predict mental state transition                         │    │
│  │    3. Score: mental_consistency × 0.45                       │    │
│  │          + physical_plausibility × 0.35                      │    │
│  │          + social_appropriateness × 0.20                     │    │
│  │    4. Safety veto on harmful actions                          │    │
│  │                                                                │    │
│  │  Winner → selected action (overrides policy table when active)│    │
│  │  All branches → compiled into .nail reflexes for future       │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Status

- **Prototype adapter:** `mentis-thinker-adapter/` (this repo)
- **Integration target:** `slackwater-cognition/local_thinker/thinker.py`
- **Distillation extension:** `thought-amplifier/distillation_loop.py` + social-cognition domain
- **Reflex extension:** `.nail` format gains `mental_match_key`, `mental_embedding`, `mental_keywords`

## Dependencies

- Mentis reference implementation (MIT license): https://github.com/SuperInstance/Mentis
- Existing thinker infrastructure (Slackwater Cognition)
- Existing distillation loop (Thought Amplifier)
- Pydantic v2 (for Mentis schema contracts)

## License

MIT. Same as Mentis. Same as the existing stack.

---

*This is the layer that makes Wesley stop being an autist and start being a crew member who reads the room. Not by being smarter — Wesley's weights never change — but by having a mental model cached, compiled, and reflex-matched the same way physical models are. The exocortex grows a social dimension. The ensign learns to read the room.*
