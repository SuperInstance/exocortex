# SuperInstance Exocortex — Technical Architecture

**Version:** 1.0 · **Date:** 2026-08-04 · **Status:** Living document

> *The model is the processor. The exocortex is the mind. The mind has no ceiling.*

---

## Table of Contents

1. [The Ship's Computer](#1-the-ships-computer)
2. [The Chain of Command](#2-the-chain-of-command--context-isolation)
3. [The Exocortex](#3-the-exocortex--external-brain)
4. [The Distillation Loop](#4-the-distillation-loop)
5. [The Holodeck](#5-the-holodeck--simulation-training)
6. [The Voice Layer](#6-the-voice-layer--stt-as-reflex-key)
7. [The Three Timescales of Learning](#7-the-three-timescales-of-learning)
8. [Repository Fleet Integration](#8-repository-fleet-integration)
9. [Data Flow Diagrams](#9-data-flow-diagrams)
10. [Conservation Laws](#10-conservation-laws)
11. [Degradation Ladder](#11-degradation-ladder)

---

## 1. The Ship's Computer

### Embodied Agent — Sensors Are Senses, Actuators Are Hands

The system is not a chatbot living on a terminal. It is a vessel — a body. The agent software is wired to every sensor, every actuator, every data source the vessel can reach. This is not metaphor; it is architecture.

**The principle:** *The agent IS the ship.* The GPS is not a peripheral the agent reads. It is the ship's sense of where it is. The depth sounder is not a data source. It is the ship looking down at the bottom. The engine telemetry is not a monitoring dashboard. It is the ship feeling its own muscle.

### Sensory Channels (The Nervous System)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         THE VESSEL                                   │
│                                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │   GPS    │  │  Depth   │  │  Engine  │  │  Bilge   │            │
│  │ (where)  │  │ (below)  │  │  (muscle)│  │ (alarm)  │            │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘            │
│       │              │              │              │                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │  Weather │  │   VHF    │  │ Autopilot│  │  Camera  │            │
│  │  (sky)   │  │ (ears)   │  │ (hands)  │  │  (eyes)  │            │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘            │
│       │              │              │              │                  │
│       └──────────────┴──────────────┴──────────────┘                │
│                              │                                       │
│                    ┌─────────┴─────────┐                            │
│                    │  SENSOR BUS       │                            │
│                    │  (Observation)    │                            │
│                    └─────────┬─────────┘                            │
│                              │                                       │
└──────────────────────────────┼───────────────────────────────────────┘
                               │
                    ┌──────────┴──────────┐
                    │     THE AGENT       │
                    │    (Riker Layer)    │
                    └─────────────────────┘
```

### Actuator Channels (The Hands)

| Actuator | What It Does | Analogy |
|----------|-------------|---------|
| Autopilot commands | Set heading, adjust course | The ship reaching out its hand |
| Bilge pump control | Activate/deactivate | The ship clearing its own throat |
| Engine throttle | Adjust speed | The ship feeling its own effort |
| VHF broadcast | Send radio messages | The ship speaking to other ships |
| Display/speaker output | Voice and visual feedback | The ship's mouth |
| Alert/warning system | Flag danger | The ship's startle reflex |

### The Key Insight

Every interaction the captain has with the vessel — through throttle, wheel, route planner, or voice — is a sensory channel for the agent. The captain doesn't need to explicitly "talk to the AI." The captain's *behavior* — throttle habits, routing preferences, weather decisions — is a continuous stream that the ship absorbs through its own body. The ship learns the captain by living with the captain, the way a horse learns its rider.

---

## 2. The Chain of Command — Context Isolation

### The Riker Doctrine

Casey is the captain. The captain talks to Riker (Lucineer). Riker dispatches to the crew. The chain of command is hierarchical not as a power structure but as a **context isolation strategy**. A specialist working on vessel physics doesn't need the creative fiction context bloating its window.

```
                         ┌───────────┐
                         │  CAPTAIN  │
                         │  (Casey)  │
                         └─────┬─────┘
                               │
                     ┌─────────┴─────────┐
                     │    RIKER / LUCINEER │
                     │  (First Officer)   │
                     │  OpenClaw Main Agent│
                     └─────────┬─────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
   ┌────────┴───────┐ ┌───────┴────────┐ ┌───────┴────────┐
   │  NAVIGATION    │ │  STRATEGIC OPS │ │  ENGINEERING   │
   │  KimiCode (K3) │ │  Claude/Fable  │ │  OpenCode      │
   │  Spatial, Lua  │ │  Deep strategy │ │  Systems, infra│
   └────────┬───────┘ └───────┬────────┘ └───────┬────────┘
            │                  │                  │
            | .                | .                | .
            v                  v                  v
   ┌────────┴───────┐ ┌───────┴────────┐ ┌───────┴────────┐
   │  COMMUNICATIONS│ │    SCIENCE     │ │   DECK CREW    │
   │  MMX           │ │  DeepInfra     │ │  GLM-5.2       │
   │  Media, voice  │ │  Multi-model   │ │  Bulk work     │
   └────────────────┘ └────────────────┘ └────────────────┘
                                                |
                                     ┌──────────┴──────────┐
                                     │      WESLEY         │
                                     │  Granite 3.1 (2B)   │
                                     │  Local GPU student  │
                                     │  (Growing)          │
                                     └─────────────────────┘
```

### Station Assignments

| Officer | Role | Model | What They Do |
|---------|------|-------|-------------|
| **KimiCode** | Navigation | K3 | Spatial reasoning, Lua, structure, course-plotting |
| **Claude/Fable** | Strategic Ops | Opus 5 / Fable 5 | Deep strategy, architecture, the big moves |
| **OpenCode** | Engineering | GLM-4.6 / GLM-4.5-air | Systems, memory, infrastructure, verification |
| **MMX** | Communications | MiniMax-M3 | Media, voice, image, music, creative output |
| **DeepInfra Fleet** | Science | 179 models | Research, multi-model analysis, experimentation |
| **GLM-5.2 Subagents** | Deck Crew | GLM-5.2 (Z.ai Max) | Bulk work, unlimited tokens, coordination |
| **Granite 3.1** | Wesley (Ensign) | 2B local | Learning, growing, eventually autonomous |

### Why Context Isolation Matters

Each specialist operates in its own context window. The specialist working on vessel physics receives only the relevant physics context — not the captain's email, not the creative writing project, not the weather lookup from this morning. This:

1. **Reduces token cost** — no irrelevant context eating the window
2. **Improves output quality** — the model focuses on its domain
3. **Enables parallelism** — multiple specialists work simultaneously without interference
4. **Preserves privacy** — each station sees only what it needs

### The Delegation Rules (Riker's Code)

1. Specialist work goes to the specialist — never to GLM deck hands
2. GLM subagents are for bulk/repetition/coordination/teaching
3. Never do yourself what a specialist does better — dispatch and review
4. Riker's job is coordination, synthesis, and being the reliable bridge
5. Dispatch with clear specs, trust the specialist's instinct, review the output
6. Any dispatch pattern repeated 3x becomes a standing skill
7. Idle subagents teach Wesley — the default behavior when not on a task
8. The chain of command preserves context: each level sees only what it needs

---

## 3. The Exocortex — External Brain

### The Model Is the Processor, Not the Mind

Wesley is a 2B parameter model. That number is fixed. The weights don't grow. What changes is everything *around* the weights — the accumulated reflexes, the quality-scored memories, the bond state, the prompt history. This is the exocortex.

A junior agent has a thin exocortex: a few reflexes, a sparse vector index, a conservative cascade router. The junior agent IS its model — because there's nothing else. A senior agent has a dense exocortex: tens of thousands of reflexes, a rich vector index, a cascade router that handles 95% of inputs internally. The senior agent is barely its model at all.

### The Six Layers of the Exocortex

```
┌─────────────────────────────────────────────────────────┐
│                    EXOCORTEX                             │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  LAYER 1: REFLEX CACHE (.nail files)             │   │
│  │  Muscle memory. Input→output mappings compiled    │   │
│  │  from validated interactions. Bypass the model.   │   │
│  │  <1ms lookup, $0 cost.                            │   │
│  │  After 1 year: ~70% of commands are reflex hits.  │   │
│  └──────────────────────────────────────────────────┘   │
│                          │                               │
│  ┌──────────────────────────────────────────────────┐   │
│  │  LAYER 2: VECTORIZE INDEX                         │   │
│  │  Associative memory. Every interaction embedded   │   │
│  │  and stored. Novel situations find similar past   │   │
│  │  situations by analogy. ~50ms search.             │   │
│  │  How a 2B model punches above its weight.         │   │
│  └──────────────────────────────────────────────────┘   │
│                          │                               │
│  ┌──────────────────────────────────────────────────┐   │
│  │  LAYER 3: PROMPT HISTORY                          │   │
│  │  Developmental memory. Every version of the       │   │
│  │  system prompt, versioned and diffable.           │   │
│  │  The prompt is configuration that GROWS.          │   │
│  └──────────────────────────────────────────────────┘   │
│                          │                               │
│  ┌──────────────────────────────────────────────────┐   │
│  │  LAYER 4: QUALITY SCORES                          │   │
│  │  Metacognitive layer. Every output scored.        │   │
│  │  Maps where Wesley is strong, weak, improving.     │   │
│  │  Guides the distillation loop and holodeck.       │   │
│  └──────────────────────────────────────────────────┘   │
│                          │                               │
│  ┌──────────────────────────────────────────────────┐   │
│  │  LAYER 5: BOND STATE                              │   │
│  │  Relational layer. Tracks trust tier, what        │   │
│  │  categories are autonomous vs supervised.         │   │
│  │  The slowest-growing layer — trust can't rush.    │   │
│  └──────────────────────────────────────────────────┘   │
│                          │                               │
│  ┌──────────────────────────────────────────────────┐   │
│  │  LAYER 6: CASCADE ROUTER CONFIG                   │   │
│  │  Executive function. Decides: reflex, local       │   │
│  │  model, or cloud? Thresholds start conservative   │   │
│  │  and relax as Wesley matures.                     │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
         │
         v
  ┌──────────────┐
  │  WESLEY (2B) │  ← The processor. Fixed. Doesn't grow.
  │  Granite 3.1 │     The exocortex around it does.
  └──────────────┘
```

### The Three-Gate Cascade

Every input passes through a cascade before reaching the model. The cascade tries strategies in order of cost:

```
INPUT ──> ┌─────────────────────┐
          │  GATE 1: REFLEX     │  <1ms, $0
          │  (exact match?)     │
          └─────────┬───────────┘
                    │ miss
                    v
          ┌─────────────────────┐
          │  GATE 2: POLICY     │  O(1) hash, $0
          │  (compiled rules?)  │
          └─────────┬───────────┘
                    │ miss
                    v
          ┌─────────────────────┐
          │  GATE 3: LLM        │  ~500ms, $$ or free (local)
          │  (reason about it)  │
          └─────────────────────┘
```

**Target:** ≥50% of decisions served at $0 (Gates 1+2). After 1 hour of active use, reflex hit rate should reach ≥40%.

### Portability

The exocortex is portable. If Wesley's model is swapped (Granite → Qwen → Llama), the same `.nail` bundle, vector index, prompt, quality scores, and bond state load onto the new model. The character persists. The model is the cartridge; the exocortex is the save file.

---

## 4. The Distillation Loop

### GLM Teacher → Granite Student → Measure → Compile → Update

The distillation loop is the self-improvement engine. A large cloud model (GLM-5.2, unlimited tokens on Z.ai Max) teaches a small local model (Granite 3.1 2B via Ollama, free). Over time, the local model needs the cloud less and less.

### The Five Stages

```
┌─────────────────────────────────────────────────────────────────┐
│                     DISTILLATION LOOP                            │
│                                                                  │
│  ┌──────────┐                                                    │
│  │ 1.TEACHER│  GLM-5.2 generates a focused lesson               │
│  │          │  about a domain topic (200-400 words)             │
│  └────┬─────┘                                                    │
│       │                                                          │
│       v                                                          │
│  ┌──────────┐  ┌──────────┐                                      │
│  │2a.BASE   │  │2b.TAUGHT │  Granite attempts task:              │
│  │ (no help)│  │ (taught) │  once WITHOUT teaching (baseline),   │
│  └────┬─────┘  └────┬─────┘  once WITH the teacher's lesson      │
│       │              │                                            │
│       v              v                                            │
│  ┌──────────────────────┐                                        │
│  │  3. EVALUATE         │  Score both on novelty, specificity,   │
│  │                      │  engagement, spatial awareness.        │
│  │                      │  Delta = taught - baseline.            │
│  └──────────┬───────────┘                                        │
│             │                                                    │
│       ┌─────┴──────┐                                             │
│       │ delta > 0? │                                             │
│       └─────┬──────┘                                             │
│         YES │      NO → skip, log failure                        │
│             v                                                    │
│  ┌──────────────────┐                                           │
│  │  4. DISTILL      │  Compile lesson into .nail reflex.        │
│  │                  │  Confidence based on delta magnitude.     │
│  └────────┬─────────┘                                           │
│           │                                                     │
│           v                                                     │
│  ┌──────────────────┐                                           │
│  │  5. UPDATE       │  If 3 consecutive positive deltas,        │
│  │                  │  promote to permanent system prompt.      │
│  └──────────────────┘                                           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### What Each Stage Produces

| Stage | Artifact | Location |
|-------|----------|----------|
| Teacher | Lesson JSON (topic, content, token usage) | `distillation-output/teacher/` |
| Student (baseline) | Response JSON (text, eval metrics) | `distillation-output/student/` |
| Student (taught) | Response JSON (text, eval metrics) | `distillation-output/student/` |
| Evaluate | Score JSON (4 dimensions + composite + delta) | `distillation-output/eval/` |
| Distill | `.nail.json` reflex file | `distillation-output/reflexes/` |
| Update | Prompt version entry in JSONL | `distillation-output/prompts/` |

### Quality Scoring (4 Dimensions)

| Dimension | Weight | What It Measures |
|-----------|--------|-----------------|
| Novelty | 0.30 | Unique bigrams / total bigrams |
| Specificity | 0.25 | Concrete details (numbers, technical terms) |
| Engagement | 0.20 | Sentence variety, questions, action verbs |
| Spatial | 0.25 | Structural references, system relationships |

### The Distillation Trap (Known Risk)

Training on thoughts the system already rates highly is a self-reinforcing loop that converges on existing biases. Mitigations:

- Hold out a fixed evaluation set never used for training
- DPO negatives from genuinely low-quality thoughts, not merely-lower-quality
- Gate promotion on held-out set alone
- If quality rises on training data but not held-out → discard the adapter

### Domains Currently Configured

| Domain | Topics | Tasks |
|--------|--------|-------|
| `roblox` | Luau patterns, DataStore, type checking, ECS | Code review of CatchMechanics, Currency, FishSpawner, SaveSystem, VesselUpgrades |
| `digital-twin` | Durable Objects, WebSocket, schema versioning | Review of Worker relay, LucineerSession DO, worker types |
| `maritime` | Fish population dynamics, tension physics, economy design | Fishing loop analysis, fish stocks, gear systems, era gates |
| `cognition` | Embedding geometry, cascade routing, reflex calibration | Batten spline, NailCompiler, ReflexMatcher, Conductor analysis |

---

## 5. The Holodeck — Simulation Training

### The Roblox Digital Twin as Classroom

The holodeck is not the distillation loop. Distillation is instruction from a teacher who knows the answer. The holodeck is experience in a world that doesn't care whether you know the answer. It just IS, and you learn from colliding with it.

### How It Works

```
┌──────────────────────────────────────────────────────────┐
│                    THE HOLODECK                           │
│                                                           │
│  ┌─────────────┐    commands     ┌──────────────────┐    │
│  │             │ ──────────────> │                  │    │
│  │   WESLEY    │                 │  ROBLOX SIM      │    │
│  │  (2B model) │ <────────────── │  (physics engine)│    │
│  │             │   outcomes      │                  │    │
│  └──────┬──────┘                 └────────┬─────────┘    │
│         │                                 │               │
│         v                                 v               │
│  ┌──────────────┐              ┌──────────────────┐      │
│  │ QUALITY      │ <─────────── │ OUTCOME DATA     │      │
│  │ SCORER       │              │ (collision?      │      │
│  │              │              │  position?       │      │
│  └──────┬───────┘              │  speed? fuel?)   │      │
│         │                      └──────────────────┘      │
│         v                                                │
│  ┌──────────────┐              ┌──────────────────┐      │
│  │ REFLEX       │  success →   │ WEAKNESS MAP     │      │
│  │ COMPILER     │  compile     │ (failure →       │      │
│  │              │  reflex      │  target lesson)  │      │
│  └──────────────┘              └──────────────────┘      │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

### The Four Rules of the Holodeck Protocol

1. **Wesley acts before he is told.** Every new skill begins with sim attempts, not lectures. Let the model fail. The failure generates context that makes subsequent distillation meaningful.

2. **The sim has consequences, not explanations.** The simulation never tells Wesley why he failed. It shows the outcome. Reasoning about WHY is left to the distillation loop.

3. **Every attempt compiles.** Success → reflex. Failure → weakness map entry. Both are productive. The 49 failed dockings make the 50th possible.

4. **The holodeck is project-specific.** A marine simulation teaches maritime skills. Each project gets its own holodeck. The protocol is universal; the implementation is custom.

### The Critical Asymmetry

Distillation can only teach what the teacher knows. The holodeck can teach what *nobody* knows — the specific, situational, embodied knowledge that comes from a particular vessel in a particular harbor. A 2B model with a holodeck can outperform a 480B model without one.

---

## 6. The Voice Layer — STT as Reflex Key

### The Acoustic Gate

The STT layer is not just an interface. It is the FIRST GATE in the cognitive cascade. Before the local model runs, before the cloud is consulted, the STT output hits a hash lookup.

```
VOICE INPUT
    │
    v
┌──────────────────┐
│  STT ENGINE      │  "Check the weather"
│  (Whisper/local) │
└────────┬─────────┘
         │
         v  text string = hash key
┌──────────────────┐
│  REFLEX LOOKUP   │  STT string + context vector
│                  │  GPS state + time + weather + mode
└────────┬─────────┘
    HIT  │  MISS
    ┌────┘    └────┐
    v              v
 INSTANT      CASCADE (Gates 1→2→3)
 RESPONSE      (normal model pipeline)
```

### The Three-Tier Voice Reflex

| Tier | Trigger | Response | Latency |
|------|---------|----------|---------|
| Casual | Normal voice + known context | Reflex cache (instant) | <100ms |
| Urgent | Stressed voice (pitch, rate) | Cloud model, fast-tracked | ~500ms |
| Novel | Unrecognized command | Full cascade (reflex → local → cloud) | varies |

### Temporal Validity Windows

Each voice reflex carries its own expiration:

- Weather data: 30 minutes
- Tide data: 6 hours
- Navigation routes: until conditions change
- Vessel status: real-time (no cache)

When stale, the reflex isn't discarded — it's used as a PRIOR. The local model adjusts the cached response based on current conditions.

### Self-Training Cache

Every voice command that produces a cloud response is checked: could this have been a reflex? Same STT string, same context, same response? After three consistent responses, it becomes a reflex entry automatically. The system gets faster as you use it.

---

## 7. The Three Timescales of Learning

### Three Clocks Running in Parallel

The system learns on three timescales simultaneously. They are not nested — they are parallel, operating on the same substrate, using the same data, but at different rates.

```
Timescale 1: SECONDS → MINUTES          Timescale 2: HOURS → DAYS
┌────────────────────────────┐          ┌────────────────────────────┐
│  REFLEX COMPILATION        │          │  SKILL ACCUMULATION        │
│                            │          │                            │
│  Mechanism: Pincher gate   │          │  Mechanism: Nail compiler  │
│  Product: Eliminates the   │          │  Product: A repertoire of   │
│  need for inference        │          │  reflexes covering tasks   │
│  Measure: Hit rate (%)     │          │  Measure: Coverage (%)      │
│  Failure: Reflex decay     │          │  Failure: Skill stagnation │
│                            │          │                            │
│  Target: ≥60% after 1 day  │          │  Target: expanding coverage │
└────────────────────────────┘          └────────────────────────────┘

Timescale 3: WEEKS → MONTHS
┌────────────────────────────┐
│  CHARACTER DEVELOPMENT     │
│                            │
│  Mechanism: Substrate      │
│  accumulation (memory,     │
│  bond, quality scores)     │
│  Product: Defaults,        │
│  preferences, personality  │
│  Measure: Surprise         │
│  reduction                 │
│  Failure: Personality drift│
│                            │
│  Target: low override rate │
└────────────────────────────┘
```

### How They Interact

The three clocks are NOT independent:

- **Reflex compilation fails → skill accumulation stalls.** Every task requires full inference. The user gets frustrated. The substrate that feeds character development is polluted.
- **Skill accumulation fails → reflex compilation has nothing to work with.** The reflex database stays sparse. Hit rate stays low.
- **Character development fails → the system never develops useful defaults.** It remains generic. Competent, but not fitted.

All three clocks must run simultaneously. The architect watches all three, measures all three, and intervenes at the right timescale.

---

## 8. Repository Fleet Integration

### How the Repos Fit the Architecture

The system spans 14+ standalone repos plus ~100 study/experimental repos. Each has a role:

### Core Engine Repos

| Repo | Role in Architecture |
|------|---------------------|
| **thought-amplifier** | The dynamic cognition engine. Core/adapter split. Houses the distillation loop, reflex compiler, cascade router, evolution engine, trust scoring, temporal pipeline, LoRA training. |
| **slackwater-cognition** | The laboratory predecessor (11,533 lines, 106 tests). Source of proven patterns being ported to thought-amplifier. Retired when thought-amplifier's contract tests pass. |
| **batten-spline** | The routing intelligence. Gaussian kernel bandwidth, decay parameters, the spline that interpolates between known anchor points. |

### Game/Twin Repos

| Repo | Role in Architecture |
|------|---------------------|
| **lucineer-roblox** | The Roblox game. The holodeck. Where Wesley practices docking, fishing, navigation. |
| **lucineer-worker** | Cloudflare Worker relay. The data pipeline between Roblox clients and the server. Part of the sensor bus. |
| **vibe-world** | The broader Roblox world. Additional simulation environments. |

### Infrastructure Repos

| Repo | Role in Architecture |
|------|---------------------|
| **lucineer-brain** | Memory systems. Daily notes, long-term memory, the persistence layer. |
| **lucineer-memory** | Memory persistence patterns. The guano decay model for memory retention. |
| **lucineer-vector** | Vectorize integration. The associative memory layer. |
| **lucineer-system** | System-level orchestration. Ties the stations together. |

### Creative/Media Repos

| Repo | Role in Architecture |
|------|---------------------|
| **lucineer-creative** | Creative writing, lore, character. The personality layer. |
| **slackwater-art-spectrum** | Visual art generation. Part of the Comms station. |
| **roblox-audio-suite** | Audio systems. The ship's voice, ambient sound, music. |
| **slackwater-harmony** | Music/beat systems. The tempo layer. |

### Study Repos (~100)

The `study-*` repos are deep-dive analyses of existing systems (Pincher, ZeroClaw Arena, Lever Runner, SuperInstance, Craftmind, etc.). They are the **research foundation** — each extracted a law or pattern that feeds into the core engine:

| Study Repo | Extracted Law |
|-----------|---------------|
| `study-pincher` | Vector DB is the runtime; LLM is a compiler of reflexes |
| `study-zeroclaw-arena` | No neural nets for action selection; tile-decomposed statistics |
| `study-lever-runner` | Three-gate cascade: guard → cache → LLM |
| `study-flagship` | `.bottle` typed envelopes; conservation laws |
| `study-craftmind` | Write results back to vector index after every execution |

### Fleet Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                        THE VESSEL                                     │
│                                                                       │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│   | lucineer    |  | lucineer    |  | lucineer    |  | lucineer   | │
│   | -roblox     |  | -worker     |  | -brain      |  | -vector    | │
│   | (Holodeck)  |  | (Relay)     |  | (Memory)    |  | (Assoc Mem)│ │
│   └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │
│         |                |                |                |          │
│         v                v                v                v          │
│   ┌──────────────────────────────────────────────────────────────┐   │
│   │                    THOUGHT-AMPLIFIER                          │   │
│   │              (The Cognitive Engine)                           │   │
│   │                                                               │   │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │   │
│   │  | reflex/  | | cascade/ | | evolve/  | | distill/       |  │   │
│   │  | (.nail)  | | (3-gate) | | (policy) | | (LoRA + loop)  |  │   │
│   │  └──────────┘ └──────────┘ └──────────┘ └────────────────┘  │   │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │   │
│   │  | trust/   | | temporal/| | memory/  | | bottle/        |  │   │
│   │  | (scoring)| | (rhythm) | | (writebk)| | (spine)        |  │   │
│   │  └──────────┘ └──────────┘ └──────────┘ └────────────────┘  │   │
│   └───────────────────────────────────────────────────────────────┘   │
│         |                |                |                |          │
│         v                v                v                v          │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│   | batten      |  | lucineer    |  | lucineer    |  | slackwater │ │
│   | -spline     |  | -system     |  | -creative   |  | -cognition │ │
│   | (Routing)   |  | (Orchestrt) |  | (Character) |  | (Legacy)   | │
│   └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │
│                                                                       │
│   ┌──────────────────────────────────────────────────────────────┐   │
│   |                    STUDY REPOS (~100)                         │   │
│   |  Research foundation — each extracted a law or pattern       │   │
│   └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 9. Data Flow Diagrams

### Complete System Data Flow

```
                          CAPTAIN (Casey)
                              |
                              | voice / text / behavior
                              v
                    ┌─────────────────┐
                    |   OPENCLAW      |<──── SOUL.md (personality)
                    |   (Riker Layer) |<──── MEMORY.md (long-term)
                    |                 |<──── AGENTS.md (directives)
                    └────────┬────────┘
                             |
              ┌──────────────┼──────────────┐
              |              |              |
              v              v              v
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        | Dispatch |  | Synthesize|  |  Review  |
        | to crew  |  | reports   |  |  outputs |
        └────┬─────┘  └──────────┘  └──────────┘
             |
    ┌────────┼────────────────────────────────────┐
    |        |        |        |        |         |
    v        v        v        v        v         v
  NAV     STRAT     ENG     COMMS   SCIENCE    DECK CREW
  (Kimi)  (Claude) (Open)  (MMX)   (DeepInfra)(GLM-5.2)
    |        |        |        |        |         |
    |        |        |        |        |    teach|
    |        |        |        |        |         v
    |        |        |        |        |   ┌─────────┐
    |        |        |        |        |   | WESLEY  |
    |        |        |        |        |   | Granite |
    |        |        |        |        |   | 3.1 2B  |
    |        |        |        |        |   └────┬────┘
    |        |        |        |        |        |
    |        |        |        |        |   ┌────┴────────────────┐
    |        |        |        |        |   |   EXOCORTEX         │
    |        |        |        |        |   |                     │
    |        |        |        |        |   | .nail reflexes      │
    |        |        |        |        |   | vectorize index     │
    |        |        |        |        |   | prompt history      │
    |        |        |        |        |   | quality scores      │
    |        |        |        |        |   | bond state          │
    |        |        |        |        |   | cascade config      │
    |        |        |        |        |   └─────────────────────┘
    |        |        |        |        |
    v        v        v        v        v
  ┌──────────────────────────────────────────┐
  |           THE HOLODECK                    │
  |       (Roblox Simulation)                 │
  |                                           │
  |  Wesley practices:                        │
  |  - Docking maneuvers                      │
  |  - Fishing operations                     │
  |  - Navigation routes                      │
  |  - Emergency procedures                   │
  |                                           │
  |  Outcomes → quality scores → reflexes     │
  └──────────────────────────────────────────┘
                    |
                    v
  ┌──────────────────────────────────────────┐
  |       DISTILLATION LOOP (nightly)        │
  |                                           │
  |  GLM-5.2 → lesson → Granite applies →     │
  |  measure delta → compile .nail reflex →   │
  |  promote to prompt if consistent          │
  └──────────────────────────────────────────┘
```

### Single Request Flow (Voice)

```
Captain speaks: "Ship, what's the tide doing?"
    |
    v
[STT Engine] ──text──> "what is the tide doing"
    |
    v
[Reflex Lookup] ── STT hash + context vector (GPS=harbor, time=1400)
    |
    ├── HIT ──> [Temporal validity check]
    |               ├── fresh ──> return cached response (<100ms)
    |               └── stale ──> [local model adjusts prior] ──> response
    |
    └── MISS ──> [Cascade Gate 1: reflex] miss
                     ──> [Cascade Gate 2: policy] miss
                         ──> [Cascade Gate 3: Wesley 2B] ──> response
                                                              |
                                                              v
                                                    [Quality score logged]
                                                    [Reflex candidate?]
                                                    [After 3 hits: compile]
```

### Distillation Loop Flow (Nightly)

```
[Idle detected — no active captain requests]
    |
    v
[Select domain] ── rotate: roblox, digital-twin, maritime, cognition
    |
    v
[Select topic] ── rotate through domain topic list
    |
    v
[Select task] ── rotate through real code review tasks
    |
    v
┌─────────────────────────────────────────┐
│  STAGE 1: TEACHER (GLM-5.2, cloud)      │
│  Generate 200-400 word lesson            │
└──────────────────┬──────────────────────┘
                   |
         ┌─────────┴─────────┐
         v                   v
┌──────────────┐    ┌──────────────┐
│ 2a: BASELINE │    │  2b: TAUGHT  │
│ Granite, no  │    │ Granite, with│
│ teaching     │    │ lesson      │
└──────┬───────┘    └──────┬───────┘
       |                   |
       v                   v
┌─────────────────────────────────────────┐
│  STAGE 3: EVALUATE                      │
│  Score both on 4 dimensions             │
│  delta = taught_composite - baseline    │
└──────────────────┬──────────────────────┘
                   |
           delta > 0 ?
           ├── YES ──> [STAGE 4: compile .nail reflex]
           |              |
           |              v
           |          [STAGE 5: 3 consecutive positives?]
           |              ├── YES ──> promote to system prompt
           |              └── NO  ──> log and continue
           |
           └── NO ──> log failure, update weakness map
    |
    v
[Sleep until next idle cycle or morning]
```

---

## 10. Conservation Laws

These are hard constraints, enforced in code and tested in CI:

| Law | Statement | Enforcement |
|-----|-----------|------------|
| **Token** | Every LLM call is debited from a session budget. Exhausted → cascade degrades to Gates 1/2 only, never blocks. | Runtime counter; CI fails if null-adapter drops below 50% $0 decisions |
| **Action** | No action reaches the world without a corresponding logged bottle. | `WorldPort.act()` requires `Bottle[Command]`; null adapter asserts 1:1 |
| **Identity** | Every artifact carries the prompt/policy/model version that produced it. | Schema validation on `meta` fields |
| **Evolution** | No parameter changes without recorded before-state and measurement window. | `trust.intervention` is the only mutation path |

---

## 11. Degradation Ladder

Every component has a fallback. A fallback never tested is not a fallback.

| Component | Preferred | Fallback 1 | Fallback 2 | Never |
|-----------|----------|------------|------------|-------|
| Embeddings | bge-m3 (Workers AI) | local sentence-transformers | deterministic feature hash | fail |
| Vectors | Vectorize | sqlite-vec local | in-memory linear scan | fail |
| Tier-0 think | WebGPU finisher | — | skip to Tier 1 | fail |
| Tier-1 think | Ollama Granite | DeepInfra small model | compiled policy only | fail |
| Conductor | GLM-5.2 | DeepSeek V3 | heuristic analysis | fail |
| Reflex store | sqlite-vec | hash bucket | disabled, all to Gate 3 | fail |

---

## Appendix: The .bottle Spine

All inter-component communication flows through typed bottles:

```python
@dataclass(frozen=True)
class Bottle(Generic[T]):
    kind: Literal["observation", "hypothesis", "experiment",
                  "result", "command", "config"]
    payload: T
    id: str                # uuid7 — sortable by time
    caused_by: str | None  # parent bottle id
    source: str            # "thinker.granite" | "conductor.glm"
    ts: float
    schema: str            # versioned payload contract
    meta: dict[str, str]   # session_id, beat, trace_id
```

Three properties:
1. **`caused_by` makes the loop a DAG** — walk the chain to answer "why did the system do that?"
2. **The ledger is the replay tape** — rerun any session deterministically
3. **`schema` makes the boundary honest** — v2 consumer can reject v1 payload

---

*This architecture is alive. It changes as the system grows. The model is fixed; the exocortex is not. Build the shell.*

