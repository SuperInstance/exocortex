# SuperInstance Exocortex — Research: What Exists vs What's Novel

**Version:** 1.0 · **Date:** 2026-08-04 · **Status:** Active

> *We are not the first to imagine an exocortex. We are the first to build one that learns from its own mistakes, practices in a simulation, and grows character over months. Here's what the world has, what it doesn't, and where our contributions sit.*

---

## Table of Contents

1. [NVIDIA Molt](#1-nvidia-molt)
2. [Microsoft Agent Framework & Intelligent Edge](#2-microsoft-agent-framework--intelligent-edge)
3. [Existing Exocortex Projects](#3-existing-exocortex-projects)
4. [Sim-to-Real for Language Models](#4-sim-to-real-for-language-models)
5. [Voice Intent Caching](#5-voice-intent-caching--siri-alexa--what-exists)
6. [Knowledge Distillation](#6-knowledge-distillation--teacher-student-compression)
7. [Our Novel Contributions](#7-our-novel-contributions)
8. [Summary: The Gap Map](#8-summary-the-gap-map)

---

## 1. NVIDIA Molt

### What It Is

NVIDIA's NeMo team released **Molt** in August 2026 — a PyTorch-native agentic reinforcement learning framework. It is approximately 8,600 lines of RL code designed to make training long-running AI agents simpler and more comprehensible.

**Repository:** [github.com/NVIDIA-NeMo/labs-molt](https://github.com/NVIDIA-NeMo/labs-molt)

### Key Features

- **Compact codebase:** ~8,600 lines. Small enough for a researcher (or an AI coding assistant) to hold the entire framework in mind.
- **PyTorch-native:** Agents are ordinary Python programs, not special-cased abstractions.
- **Integrates existing tools:** Ray for distributed orchestration, vLLM for inference, NVIDIA AutoModel with FSDP2 for training. No new infrastructure invented.
- **Agent workflows:** Supports both environment-driven (Gymnasium-aligned) and chat-agent workflows. Agents can use standard OpenAI or Anthropic SDKs.
- **Scalable:** Ships with recipes for multi-node H100 setups (2 nodes × 8 GPUs). Scales from dense 4B models to 700B MoE.
- **On-policy distillation:** Supports distillation onto smaller student models — the feature most relevant to our work.

### What We Can Learn

| Molt Feature | Our Equivalent | Takeaway |
|-------------|---------------|---------|
| Compact, comprehensible codebase | thought-amplifier's core/adapter split | Small is beautiful. Our engine should fit in one head. |
| Agents as ordinary Python programs | Agents as ordinary orchestration patterns (subagents via OpenClaw) | Don't special-case the agent. It's a program. |
| Leverages existing tools (Ray, vLLM) | Leverages existing tools (Ollama, Vectorize, Cloudflare Workers) | Don't build infrastructure. Build on infrastructure. |
| On-policy distillation to students | Our distillation loop (GLM → Granite) | Validated. The industry is moving toward teacher-student as default. |
| Multi-node H100 training | Our single-GPU local training | Different scale, same principle. We do for one GPU what they do for sixteen. |
| Gymnasium-aligned environments | Our Roblox holodeck | The environment-driven workflow maps directly to our sim training. |

### What We Do Differently

1. **Scale and audience.** Molt targets institutions with H100 clusters. We target a single vessel with one GPU. Our constraint shapes our architecture: we can't throw compute at problems, so we compile knowledge into reflexes instead.

2. **The exocortex.** Molt trains agent weights. We train the *shell around the weights* — reflexes, vectors, prompts, bond state. Molt's improvement path runs through the GPU. Ours runs through accumulated experience that persists across model swaps.

3. **Embodiment.** Molt agents live in simulated environments. Our agent is designed to BE the vessel — wired to real sensors, real actuators, real consequences. Molt's sim-to-real is about transferring policies. Our sim-to-real is about transferring *character*.

4. **The holodeck protocol.** Molt uses environments for RL training. We use simulation as a *practice space* where the agent fails productively — every collision is a lesson, every success compiles into a reflex. The philosophy is different: Molt optimizes reward. We accumulate wisdom.

5. **Cost model.** Molt requires significant compute investment. Our system runs on a free local model (Granite 3.1 2B via Ollama) plus an unlimited cloud plan (Z.ai Max). The economics are democratized — anyone with a laptop and an internet connection can run this.

---

## 2. Microsoft Agent Framework & Intelligent Edge

### What It Is

Microsoft's approach to intelligent agents spans two layers:

- **Microsoft Agent Framework (MAF):** An open, multi-language framework for building, orchestrating, and deploying production-grade AI agents in .NET and Python. Multi-agent workflows, planning, Azure integration.
- **Intelligent Edge:** The vision of AI computing distributed across edge devices — factory robots, drones, smart home devices, industrial sensors — running inference close to the data source.

**Repository:** [github.com/microsoft/agent-framework](https://github.com/microsoft/agent-framework)

### Key Features

- **Multi-agent orchestration:** Planning module breaks tasks into steps, assigns to agents, manages collaboration.
- **Enterprise-grade:** Built-in observability, durability, compliance, Azure identity/security.
- **Cloud-edge synergy:** Train in Azure, deploy to edge devices via Azure IoT Edge. Single environment spanning cloud and edge.
- **Broad ecosystem:** Supports Azure OpenAI, OpenAI, GitHub Copilot SDK, MCP, Agent2Agent (A2A) protocol.
- **Operational flow:** Task definition → planning → execution → monitoring. Human-in-the-loop throughout.

### What We Can Learn

| MAF Feature | Our Equivalent | Takeaway |
|------------|---------------|---------|
| Multi-agent orchestration | Riker dispatching to senior staff | The hierarchical dispatch pattern is validated by industry. |
| Planning module | Riker's decomposition + dispatch | Task decomposition is a solved problem. Our contribution is the context isolation strategy. |
| Cloud-edge synergy | Cloud (GLM) ↔ Edge (Granite local) | The hybrid split is correct — validated independently by our multi-model panel discussion too. |
| Human-in-the-loop | The captain makes the final call | Industry agrees: autonomous agents still need human oversight for consequential actions. |
| Observability | Bottle ledger (full traceability) | Our DAG-based causal chain is actually more rigorous than MAF's observability — every action traces to its cause. |

### What We Do Differently

1. **Context isolation as architecture.** MAF's agents share a common orchestration context. Our stations operate in isolated context windows — each specialist sees only what it needs. This is a deliberate tradeoff: less shared state means less coordination overhead and better focus per agent.

2. **The exocortex vs. the orchestrator.** MAF's intelligence lives in the orchestration layer — the planner decides what agents do. Our intelligence lives in the exocortex — the compiled reflexes, vector index, and quality scores that surround the model. MAF gets smarter by improving orchestration. We get smarter by accumulating compiled experience.

3. **Character development.** MAF agents are stateless across sessions (unless explicitly configured with memory). Our agent accumulates character over months — defaults, preferences, a feel for the work. This is not a feature; it's an emergent property of the exocortex architecture.

4. **Cost model.** MAF is enterprise-focused, tied to Azure consumption. Our system runs on free tiers and unlimited plans. The economics are fundamentally different.

5. **Bond state.** No commercial agent framework we've found models trust as a first-class, tiered, slowly-growing relational state. MAF has "human-in-the-loop" as a binary switch. We have Tier 0→3 with explicit promotion/demotion criteria per domain.

---

## 3. Existing Exocortex Projects

### What Exists in the World

The concept of an "exocortex" — an external cognitive system that augments human intelligence — has been discussed in transhumanist circles since the early 2000s and is now being actively built by several projects:

#### Open-Source Projects

| Project | What It Does | Memory Model | Local-First? | Active? |
|---------|-------------|-------------|-------------|---------|
| **OwlCore.AI.Exocortex** (GitHub) | .NET library for building AI exocortex systems with multi-agent swarm architecture | Rolling context, remembrance agent | Yes | Moderate |
| **exocortex.sh** | CLI-based personal knowledge management with AI augmentation | Key-value + text search | Yes | Active |
| **Holger Woelfle's Exocortex** | Research-grade cognitive augmentation framework | LTM, episodic, semantic, procedural memory tiers | Yes | Research |
| **RSC Digital Biology (Towards a Science Exocortex)** | Academic framework for scientific computing exocortex | Knowledge graph + semantic | Hybrid | Academic |

#### Commercial Systems

| System | What It Does | Memory Model | Local-First? |
|--------|-------------|-------------|-------------|
| **ChatGPT Memory** | Persistent memory across conversations for Plus/Pro users | Key-value + semantic summaries | No (cloud) |
| **Claude Projects** | Shared context and documents for team collaboration | Document-grounded retrieval | No (cloud) |
| **Google Gemini Memory** | Persistent facts and preferences | Key-value + semantic | No (cloud) |
| **Notion AI** | Workspace-grounded AI assistant | Document retrieval | No (cloud) |
| **Apple Intelligence** | On-device AI with contextual awareness | Local semantic + cloud hybrid | Partial |

#### Academic/Research

| Direction | Key Insight | Relevance |
|-----------|------------|-----------|
| Remembrance Agent (MIT, 1990s) | Rolling context window that surfaces relevant memories based on current activity | Our vector index serves a similar function, but bidirectionally |
| Cognitive Prosthetics research | External systems that compensate for cognitive limitations | Our exocortex compensates for the 2B model's limitations |
| Personal Knowledge Graphs (Roam, Obsidian, Logseq) | Bidirectional linking creates emergent structure | Our vectorize index creates similar emergent associations |
| Rolling Context / "Remembrance Agent" pattern | Memory weighting balancing recency and relevance, with decay | Directly informs our reflex decay model |

### What's Common Across All Projects

Every exocortex project we found shares these features:
1. **Persistent memory** — some form of storage that survives session boundaries
2. **Retrieval** — the ability to find relevant past information
3. **Context awareness** — using environmental state to inform responses
4. **Local-first (for open-source)** — keeping personal data on the user's machine

### What NONE of Them Have

| Feature | Status in Other Projects | Status in Ours |
|---------|------------------------|----------------|
| **Distillation loop** (cloud teacher → local student → measure → compile) | Not found in any project | Core architecture |
| **Holodeck training** (sim practice before real deployment) | Not found in personal AI | Core architecture |
| **Bond state** (tiered trust with promotion/demotion criteria) | Binary trust at most | Core architecture |
| **Reflex compilation** (.nail files that bypass the model entirely) | Caching exists, but not as a learning system | Core architecture |
| **Cascade router** (three-gate cost optimization) | Some have fallback chains, none with our optimization targets | Core architecture |
| **Character development** (emergent personality from accumulated substrate) | Not modeled | Emergent property |
| **Tempo as first-class citizen** | Not found | Core architecture (from Slackwater) |
| **Multi-model orchestration with cost routing** | Some frameworks support multiple models, none optimize for cost the way we do | Core architecture |

---

## 4. Sim-to-Real for Language Models

### What Exists in the World

Sim-to-real transfer is a mature field in robotics. The core idea: train a policy in simulation, then transfer it to the real world. The "sim-to-real gap" — the discrepancy between simulated and real performance — is the central challenge.

### Current State of the Art (2025-2026)

| Approach | Description | Strengths | Limitations |
|----------|------------|-----------|-------------|
| **Domain Randomization** | Vary simulation parameters randomly during training so the policy becomes invariant to specific sim settings | Robust to real-world variation | Requires many sim iterations; doesn't capture structured gaps |
| **LLM-Guided Reward Design** (NVIDIA Eureka) | Use LLMs (e.g., GPT-4) to automatically generate reward functions for RL training, considering factors humans overlook | Better reward functions; energy-efficient policies | Still requires RL infrastructure (compute-heavy) |
| **Digital Twins** | Create high-fidelity digital replicas of real robots and environments | High transfer fidelity | Expensive to create; specific to one setup |
| **Zero-Shot Transfer** | Train entirely in sim, deploy to real world without fine-tuning | Eliminates real-world data collection | Works only for tasks where sim fidelity is sufficient |
| **Vibe Sim / Synthetic Data Generation** | LLM-powered sim co-pilots that generate on-demand training scenarios | Scales data generation | Sim-to-real gap remains; quality varies |
| **Task Coding** | LLMs translate natural language missions into executable task sequences for robots | Makes robots more predictable | Limited to predefined task vocabularies |

### How This Relates to Language Models (Not Robots)

Most sim-to-real work focuses on robotic control — manipulation, locomotion, navigation. Applying these ideas to *language model* training is newer and less explored:

- **LLM-as-judge:** Using LLMs to evaluate other LLMs' outputs (reward model)
- **Constitutional AI:** Training models against their own critiques (self-improvement loop)
- **RLHF in simulation:** Training reward models on simulated human preferences
- **On-policy distillation:** Training a student model on the teacher's live outputs (what NVIDIA Molt supports)

### What We Do That's Different

1. **The holodeck is experiential, not optimizational.** We're not optimizing a reward function through RL. We're giving the model *experiences* that compile into reflexes. The philosophy: learning by bumping into the dock, not by computing the optimal docking trajectory.

2. **Reflex compilation from sim outcomes.** A successful sim attempt doesn't update model weights — it compiles a `.nail` reflex. This is faster (no training cycle), cheaper (no GPU hours), and more interpretable (the reflex is readable).

3. **Sim → weakness map → distillation feedback loop.** Our sim doesn't just train; it *diagnoses*. Failures in the sim update the weakness map, which feeds back to the distillation loop, which targets the next lesson at the identified weakness. This closed loop between experiential learning and instructional learning is novel.

4. **Character, not just capability.** The holodeck doesn't just teach Wesley how to dock. It gives Wesley *experience* — the accumulated substrate that develops into preferences, defaults, and eventually character. No sim-to-real work we've found targets personality development as an outcome.

5. **Language model in a game engine.** We're putting a language model at the helm of a Roblox simulation. This is unusual — most sim-to-real work uses RL policies or specialized control networks, not general-purpose language models. The bet: a language model can reason about situations in ways that RL policies can't, and the compiled reflexes from sim experience will be richer for it.

---

## 5. Voice Intent Caching — Siri, Alexa & What Exists

### What Commercial Assistants Do

| Assistant | How They Handle Repeated Commands | What They Cache | What They Don't |
|-----------|----------------------------------|----------------|-----------------|
| **Siri** | Maintains "Siri Suggestions" based on patterns and time/location context. Does NOT cache exact responses — every command goes through cloud inference. | Pattern recognition for *when* to suggest. No response caching. | Does not bypass the model for known commands. Every "check weather" hits the server. |
| **Alexa** | "Hunches" detect routine patterns. "Routines" are user-programmed deterministic sequences. | User-created routines (manual). Some pattern detection for suggestions. | No automatic response caching. "Turn on the lights" always goes through intent classification → cloud → device command. |
| **Google Assistant** | "Routines" similar to Alexa. Context awareness from other Google services. | User-created routines. Cross-service context (calendar, location). | No reflex-style caching. Every command processes through the full NLU pipeline. |

### What They All Share

The commercial assistants all follow the same architecture:

```
Voice → STT → Intent Classification → Cloud NLU → Action → Response → TTS
```

Every command traverses the full pipeline. There is no shortcut for known patterns. "Turn on the lights" at 7 AM every day goes through intent classification every single time. The system *recognizes* the pattern (for suggestions) but doesn't *compile* it into a bypass.

### What's Missing in Commercial Assistants

1. **No reflex compilation.** Repeated commands don't get faster. The NLU pipeline runs every time.
2. **No temporal validity.** "Check weather" always hits the cloud, even if you asked 5 minutes ago.
3. **No context-vector reflex keying.** "Check depth" at the dock and "check depth" underway are processed identically.
4. **No urgency detection from voice.** Stressed "CHECK THE WEATHER" and calm "check the weather" take the same path.
5. **No self-training cache.** The system doesn't notice "you've asked this 10 times and gotten the same answer — let me cache that."

### What We're Building

Our architecture inserts a reflex gate *before* the model:

```
Voice → STT → [REFLEX LOOKUP: STT hash + context vector] → HIT? → Response (instant)
                                                            ↓ miss
                                                          [CASCADE: reflex → policy → local model → cloud]
```

This means:
- Common commands get faster over time (reflex cache grows)
- The same words in different contexts produce different responses (context-vector keying)
- Urgent commands route differently (acoustic pattern detection)
- Stale reflexes use the cached response as a prior and adjust (not discard + recompute)

### What's Novel

| Feature | Siri/Alexa/Google | Our System |
|---------|-------------------|------------|
| Repeated command handling | Full pipeline every time | Reflex bypass after 3 consistent responses |
| Context sensitivity | Time/location for suggestions | Full context vector (GPS, mode, environment, history) for response selection |
| Stale handling | N/A (no cache) | Temporal validity window + prior-based adjustment |
| Urgency routing | Not available | Acoustic pattern → fast-track to cloud |
| Self-training | Not available | Automatic reflex compilation from usage patterns |
| Marginal cost of repeat | Same as first call | ~$0 (reflex lookup, no model invocation) |

---

## 6. Knowledge Distillation — Teacher-Student Compression

### What Exists in the World

Knowledge distillation — training a small "student" model to mimic a large "teacher" model — is well-established in ML research. The teacher's soft probabilities (or generated outputs) serve as training signal for the student.

### Current Approaches

| Approach | Description | Limitations |
|----------|------------|-------------|
| **Standard KD (Hinton et al.)** | Student learns to match teacher's output distribution (soft targets) | Requires same task/domain; doesn't capture reasoning |
| **Sequence-Level KD** | Student learns to match teacher's full generated sequences | Better for generation tasks; still single-pass |
| **DPO (Direct Preference Optimization)** | Student learns from preference pairs (better/worse responses) | Requires high-quality preference data |
| **On-Policy Distillation** | Student generates, teacher critiques, student updates | Most similar to our approach; what NVIDIA Molt supports |
| **Constitutional AI / Self-Improvement** | Model critiques its own outputs using principles | Can reinforce biases without external ground truth |
| **LoRA Fine-Tuning** | Train small adapter weights on a frozen base model | Efficient but limited to what the adapter can express |

### What We Do That's Different

1. **Distill into the exocortex, not just the weights.** Standard distillation updates model parameters. Our primary output is `.nail` reflexes — compiled input→output mappings that bypass the model entirely. This is faster (no training cycle), more interpretable (reflexes are readable JSON), and reversible (reflexes can decay).

2. **Measure before promoting.** Every distillation iteration measures the delta between taught and baseline performance. Only positive deltas compile into reflexes. Only 3 consecutive positives promote to system prompt. This is A/B testing applied to distillation — the teacher doesn't just teach, the system *measures whether the teaching helped*.

3. **The sham intervention arm.** Placebo effect detection — the system periodically logs an intervention without applying it, and measures the window anyway. Real effect = treated − sham. This prevents the system from "learning" that any change is an improvement (the most likely failure mode of self-improvement loops).

4. **Multi-modal teaching.** The teacher provides lessons (text), the student applies them to real tasks (code review, analysis), and the outcome is measured (quality scoring). This is richer than "match the teacher's output distribution" — it's instruction → application → evaluation.

5. **The holodeck as experiential complement.** Distillation teaches theory. The holodeck teaches practice. Together, they produce an officer who both knows the rules and has felt the dock. No distillation system we've found includes simulation-based experiential learning as a complement.

---

## 7. Our Novel Contributions

### The Complete List

After surveying the landscape, here are the contributions that are genuinely novel — not found in any existing system we could identify:

### 1. The Distillation Loop as a Measured, A/B-Tested Self-Improvement System

**What's new:** Not distillation itself (that's well-established), but the specific architecture where:
- Teacher generates a lesson
- Student applies it to a real task (with and without teaching)
- Outcome is measured on 4 quality dimensions
- Only positive deltas compile into reflexes
- Only 3 consecutive positives promote to system prompt
- Sham intervention arm detects placebo effects
- Everything is logged, replayable, and measurable

**Why it matters:** This closes the feedback loop. Most distillation is fire-and-forget — you train and hope. We measure whether each lesson helped, for which dimensions, and by how much.

### 2. The Exocortex as a Portable, Model-Agnostic Cognitive Shell

**What's new:** Not persistent memory (many systems have it), but the specific layered architecture where:
- Six distinct layers (reflexes, vectors, prompts, quality scores, bond state, cascade config) work together
- The model is explicitly treated as a replaceable processor
- The entire accumulated wisdom can be exported as a `.nail` bundle and loaded onto a different model
- The system gets smarter without the model getting bigger

**Why it matters:** This decouples intelligence from the model. You're not locked into a provider. The exocortex persists across model upgrades, provider changes, even hardware migrations.

### 3. The Bond State as a Tiered Trust System

**What's new:** No personal AI system we found models trust as:
- A multi-tier system (Tier 0→3)
- Per-domain (Navigation-Wesley might be Tier 3 for code review but Tier 0 for game design)
- With explicit promotion criteria (10 consecutive passes → promote)
- With explicit demotion criteria (critical failure → demote)
- That determines what the agent can do autonomously

**Why it matters:** This is how trust actually works between humans. You don't trust someone with everything or nothing. You trust them with specific things, earned through demonstrated competence, lost through demonstrated failure. Modeling this in an AI system is new.

### 4. The Holodeck Protocol — Simulation as Experiential Learning

**What's new:** Not simulation itself (sim-to-real is mature), but:
- Using simulation to produce *experiential* data that complements instructional distillation
- Every sim attempt compiles — success into reflexes, failure into weakness map entries
- The weakness map feeds back to the distillation loop (closed loop between experience and instruction)
- The philosophy: "the bump is the lesson" — let the model fail, let the failure teach

**Why it matters:** This addresses the fundamental limitation of distillation: you can only teach what you know. The holodeck teaches what nobody knows — the specific, situational, embodied knowledge that emerges from interaction with a world that pushes back.

### 5. STT as Reflex Key — The Acoustic Gate

**What's new:** Not voice caching (Siri has routines), but:
- The STT output is a hash key for a reflex lookup that bypasses the model entirely
- The reflex key includes a context vector (not just the words)
- Temporal validity windows make cached responses stale-aware
- Urgency detection from voice characteristics routes to different processing tiers
- The cache self-trains: 3 consistent responses to the same STT+context → auto-compile

**Why it matters:** This makes the system *get faster as you use it*. After months of use, 70% of commands might be instant reflex lookups. No commercial assistant does this.

### 6. The Three-Gate Cascade as a Universal Pattern

**What's new:** Not fallback chains (many systems have them), but:
- The cascade is the *first* thing input hits, not the last
- The three-gate pattern (reflex → policy → LLM) recurs at every expensive decision point
- The optimization target is explicit: ≥50% of decisions at $0
- Each gate has a measured hit rate that feeds back into threshold tuning
- The cascade is testable: CI fails if the null-adapter loop drops below the 50% threshold

**Why it matters:** This is the economic engine. Without the cascade, every input costs a model invocation. With the cascade, the marginal cost of most inputs is zero. This makes the system economically sustainable in a way that "just call the LLM" systems aren't.

### 7. The Bottle Spine — Full Causal Traceability

**What's new:** Not logging (every system logs), but:
- Every inter-component message is a typed bottle with `caused_by` linking to its parent
- The entire system state forms a DAG — walk any output back to its root cause
- The ledger enables deterministic replay: same ledger + same adapters = identical output
- This makes a stochastic system testable like a deterministic one

**Why it matters:** "Why did the system do that?" is answerable in O(1) — walk the bottle chain. No other agent system we found offers this level of causal traceability as a first-class architectural property.

### 8. Character Development as an Emergent Property

**What's new:** No system explicitly models or targets this:
- The accumulated substrate (reflexes, quality scores, prompt history, bond state) produces emergent defaults, preferences, and a "feel for the work"
- Over months, the system develops something recognizable as personality — not because it was prompted to have one, but because it has history
- The measure: surprise reduction (how often do defaults match what the user would have requested?)

**Why it matters:** This is the difference between a tool and a companion. A tool is the same every time you pick it up. A companion knows you, has preferences, anticipates your needs. No commercial system develops this organically — they're reset every session, or their "memory" is explicit key-value pairs, not accumulated experiential substrate.

---

## 8. Summary: The Gap Map

```
                    WHAT EXISTS              WHAT'S NOVEL (OURS)
                    ───────────              ───────────────────
Distillation        Standard KD, LoRA,      Measured loop, A/B tested,
                    on-policy methods       sham arm, reflex compilation
                                             instead of weight update

Exocortex /         Persistent memory in    Six-layer exocortex, portable
Memory              ChatGPT/Claude,         across models, grows without
                    PKM tools               model growth

Agent               MAF, Molt,              Hierarchical context isolation,
Orchestration       AutoGen, CrewAI         bond-tiered trust, per-domain
                                            specialization

Sim-to-Real         Domain randomization,  Holodeck protocol: experiential
                    digital twins,          learning, reflex compilation from
                    LLM reward design       sim outcomes, weakness map
                                            feedback to distillation

Voice Assistants    Siri, Alexa, Google    STT as reflex key, context-vector
                    — full pipeline         keying, self-training cache,
                    every time              temporal validity, urgency routing

Trust / Safety      Binary human-in-loop   Tiered bond state, per-domain,
                                            promotion/demotion criteria

Traceability        Logging, observability  Bottle DAG, causal chain per
                                            action, deterministic replay

Character           Not modeled             Emergent from accumulated
Development                                 substrate, measured by
                                            surprise reduction
```

### The Bottom Line

No single existing system combines:
- A distillation loop that measures whether teaching helped
- An exocortex that persists and grows across model swaps
- A holodeck where the agent practices and fails productively
- A reflex system that makes the system faster over time
- A cascade that makes most decisions cost zero
- A bond system that models trust as earned, not given
- Full causal traceability of every decision
- Character that emerges from accumulated experience

**These are not eight separate features. They are one architecture, viewed from eight angles.** Each component feeds the others. The distillation loop feeds the reflex cache. The reflex cache feeds the cascade. The cascade feeds the cost model. The holodeck feeds the weakness map. The weakness map feeds the distillation loop. The bond state feeds the autonomy boundaries. The bottle spine traces all of it.

The novelty is not in any single component. It is in the integration — the way these systems form a single, self-reinforcing, self-improving cognitive architecture that treats the model as a processor and the experience as the mind.

---

*This document will be updated as the landscape evolves and as our system develops. The gap map is a snapshot, not a permanent claim. What's novel today may be standard tomorrow. The goal is not to be novel — it is to be correct. Novelty is just what correctness looks like before the world catches up.*

