# SuperInstance Exocortex — 6-Month Roadmap

**Version:** 1.0 · **Date:** 2026-08-04 · **Status:** Active plan

> *Build the shell, not the brain. The model is fixed; the exocortex grows.*

---

## Overview

Six phases, six months. Each phase builds on the previous one's success. Each has a clear deliverable, a measurable success criterion, and documented blockers. The phases are not strictly sequential — later phases begin development while earlier ones stabilize — but each has a gate that must be passed before the next is considered "achieved."

```
Month 1         Month 2         Month 3         Month 4         Month 5         Month 6
│               │               │               │               │               │
PHASE 1         PHASE 2         PHASE 3         PHASE 4         PHASE 5         PHASE 6
Distillation    Voice Reflex    Holodeck        Sensors         Multi-Station   Embodied
Loop            Caching         Training        Integration     Wesleys         Agent
│               │               │               │               │               │
Wesley learns   STT→deterministic Wesley in sim  Real vessel    Specialized     The ship
baseline skills response for     practicing     data feeding   local models    speaks
                common requests                 the exocortex  per department  as the vessel
```

---

## Phase 1: The Distillation Loop (Month 1)

### *Wesley goes to school*

**Goal:** The distillation loop runs nightly. Wesley (Granite 3.1 2B) completes baseline skill acquisition across four domains. The loop is measurable, observable, and producing compiled reflexes.

### What to Build

| Item | Description | Estimated Effort |
|------|-------------|-----------------|
| Stabilize `distillation_loop.py` | The script exists and runs. Make it run reliably as a nightly cron/heartbeat task. Handle API errors, Ollama downtime, and partial failures gracefully. | 2-3 days |
| Ollama stable on local GPU | Ensure Granite 3.1 2B runs reliably via Ollama on the local GPU. Verify it survives system sleep/wake. Set up auto-restart if the daemon dies. | 1 day |
| Domain task rotation | Implement the full rotation across `roblox`, `digital-twin`, `maritime`, `cognition` domains. Each night covers 2-3 domains, 5-10 iterations each. | 1 day |
| Reflex storage pipeline | Ensure `.nail.json` files are written reliably, indexed by domain, and discoverable by the cascade router. | 2 days |
| Prompt versioning | Implement the promotion logic: 3 consecutive positive deltas → permanent system prompt directive. Log all versions to JSONL with diffs. | 2 days |
| Metrics dashboard | A simple script/heartbeat that reports: iterations run, help rate, reflexes compiled, prompt promotions, average delta. | 1 day |
| Quality scorer validation | Compare the heuristic scorer against human judgment on 20-30 samples. Calibrate if needed. | 1-2 days |

### Success Criteria

- [ ] Distillation loop completes 100+ iterations across all 4 domains without manual intervention
- [ ] Help rate (percentage of iterations where teaching improved output) is ≥40%
- [ ] At least 10 reflexes compiled into `.nail.json` files
- [ ] At least 1 prompt promotion achieved (3 consecutive positive deltas in a domain)
- [ ] Average quality delta is positive across all domains
- [ ] Metrics are logged and observable in a single command

### What Blocks It

| Blocker | Mitigation |
|---------|-----------|
| Ollama instability on WSL2 | Set up watchdog script; consider native Linux install if WSL2 proves unreliable |
| GLM API rate limits or downtime | Add retry logic with exponential backoff; fall back to DeepSeek V3 via direct API if Z.ai is down |
| Quality scorer doesn't align with real quality | Manual calibration on sample outputs; adjust weighting if a dimension dominates spuriously |
| Code files referenced by tasks are missing/moved | Implement graceful fallback; keep a cached copy of each code file for distillation use |

### What This Unlocks

Phase 1 gives Wesley a baseline of compiled knowledge. The reflex cache is no longer empty. The cascade router has something to route to. This is the foundation for everything else — an empty exocortex can't grow through simulation, voice caching, or sensor integration, because there's nothing to cache, nothing to simulate with, nothing to contextualize.

---

## Phase 2: Voice Reflex Caching (Month 2)

### *The ship learns the sound of your voice*

**Goal:** Common voice commands are handled by reflex cache without model invocation. STT output serves as the first gate in the cascade. The system gets noticeably faster for routine requests.

### What to Build

| Item | Description | Estimated Effort |
|------|-------------|-----------------|
| STT pipeline | Local Whisper (or equivalent) running reliably. Captures voice input and produces text with low latency (<500ms). | 3-4 days |
| Reflex key constructor | Combine STT text output + context vector (GPS state, time of day, operational mode, recent history) into a hashable reflex key. | 2 days |
| Voice reflex store | Extend the reflex cache to handle voice-originated entries with temporal validity windows (weather: 30min, tide: 6hr, etc.). | 2-3 days |
| Self-training pipeline | Monitor cloud model responses. When the same STT+context produces the same response 3 times, auto-compile into a voice reflex. | 2 days |
| Urgency detection | Analyze STT patterns (pitch, rate, volume from the audio layer) to detect urgency. Urgent commands bypass local model, go straight to cloud fast-track. | 3-4 days |
| Context vector builder | Assemble real-time context (time, location, weather, recent commands, operational state) into a compact vector for reflex keying. | 2 days |
| Fallback to cascade | When a voice reflex misses or is stale, seamlessly fall through to the normal cascade (reflex → policy → local → cloud). | 1 day |

### Success Criteria

- [ ] STT pipeline running with <500ms latency for common commands
- [ ] Voice reflex cache handles ≥30% of voice commands without model invocation after 2 weeks of use
- [ ] Temporal validity windows work correctly (stale reflexes trigger re-evaluation, not silent failure)
- [ ] Urgency detection routes stressed-voice commands to cloud fast-track
- [ ] Self-training pipeline auto-compiles at least 5 new voice reflexes per week from natural usage
- [ ] System feels noticeably faster for routine requests ("check weather", "what's the tide", etc.)

### What Blocks It

| Blocker | Mitigation |
|---------|-----------|
| Local Whisper model too slow on available hardware | Use Whisper-tiny or distil-whisper; fall back to cloud STT if local is >1s latency |
| Context vector not discriminative enough (too many false hits) | Increase context resolution; add more dimensions (recent command hash, environmental state) |
| STT accuracy varies with ambient noise | Add noise gate; calibrate microphone; accept some misses as cascade fallthroughs |
| Urgency detection produces false positives | Start conservative (only flag very high pitch/rate); tune threshold based on real usage |

### What This Unlocks

Phase 2 makes the system *feel* alive. The captain says "check the weather" and gets an instant response — not because the AI is fast, but because the AI isn't invoked at all. This is the first time the system demonstrates the core thesis: a system that compiles its first encounter with any input into a reflex has a marginal cost of zero for every subsequent encounter.

---

## Phase 3: Holodeck Training (Month 3)

### *Wesley practices in the sim*

**Goal:** Wesley connects to the Roblox simulation and practices real tasks — docking, navigation, fishing operations. The holodeck produces experiential data that distillation cannot. Compiled reflexes from sim attempts complement the classroom knowledge.

### What to Build

| Item | Description | Estimated Effort |
|------|-------------|-----------------|
| Agent-to-sim bridge | Connect Wesley (Granite via Ollama) to the Roblox sim through the existing Worker relay. Wesley sends commands, receives outcomes. | 3-5 days |
| Sim task suite | Define 10-20 specific training tasks: dock at pier, navigate to waypoint, cast/fish/retrieve, respond to weather change, emergency stop. | 3-4 days |
| Outcome measurement | For each sim task, define what success looks like (position tolerance, speed threshold, no collision, fuel efficiency). Automate scoring. | 2-3 days |
| Sim→reflex pipeline | Successful sim attempts compile into `.nail` reflexes with sim-specific context tags. Failures update the weakness map. | 2 days |
| Weakness map → distillation feedback | Feed weakness map data back to the distillation loop. When Wesley fails at starboard approaches in the sim, the next distillation cycle targets crosswind docking. | 2-3 days |
| Sim logging and replay | Log every sim attempt as a bottle ledger entry. Enable replay for debugging and regression testing. | 1-2 days |
| Batch sim runner | Run N iterations of a task overnight. Wesley attempts docking 50 times while the captain sleeps. | 1-2 days |

### Success Criteria

- [ ] Wesley completes at least 500 sim attempts across 5+ task types
- [ ] At least 20 reflexes compiled from successful sim attempts
- [ ] Weakness map shows clear patterns (which tasks Wesley handles well vs poorly)
- [ ] Distillation loop uses weakness map to target specific gaps (measurable: post-distillation sim scores improve in targeted areas)
- [ ] Sim attempts are fully logged and replayable
- [ ] The "bump is the lesson" dynamic is observable: Wesley's docking improves after 20+ attempts at the same dock

### What Blocks It

| Blocker | Mitigation |
|---------|-----------|
| Roblox sim doesn't expose enough state for outcome scoring | Add scoring hooks to the Roblox game; use position/velocity telemetry from the existing Worker relay |
| Agent-to-sim latency too high for real-time tasks | Start with non-real-time tasks (route planning, strategic decisions) before real-time control tasks |
| Sim physics don't match real vessel behavior | Accept the gap; the holodeck teaches patterns, not exact parameters. Domain randomization in later iterations. |
| Wesley's 2B model can't handle the reasoning load for complex tasks | Start with simple tasks (straight-line navigation, single-axis docking) and scale complexity gradually |

### What This Unlocks

Phase 3 is the first time Wesley learns something *nobody* knows — knowledge that comes from interaction with a world that pushes back, not from a teacher's lesson. This is the critical asymmetry: distillation teaches what the teacher knows; the holodeck teaches what nobody knows.

---

## Phase 4: Sensor Integration (Month 4)

### *The vessel feeds the exocortex*

**Goal:** Real vessel data flows into the exocortex. The system doesn't just learn from sim and from distillation — it learns from the actual boat, the actual weather, the actual captain's behavior patterns.

### What to Build

| Item | Description | Estimated Effort |
|------|-------------|-----------------|
| Sensor data ingest pipeline | Pull data from available sensors: GPS, depth sounder, engine telemetry, weather station, bilge alarms. Normalize to observation bottles. | 5-7 days |
| Captain behavior logger | Log the captain's actions: throttle changes, heading adjustments, route choices, weather decisions. These are implicit feedback signals. | 3-4 days |
| Environmental state tracker | Maintain a real-time environmental context: current position, heading, speed, weather, sea state, tide direction, time of day. | 2-3 days |
| Sensor-driven reflex context | Use real sensor data as context for reflex lookups. "Check depth" at the dock vs underway produces different responses because the context vector differs. | 2-3 days |
| Pattern detection on captain behavior | Identify recurring patterns: the captain always slows down at this point, always takes this route in this weather. These become candidate reflexes or prompt directives. | 3-4 days |
| Alert system | When sensor data crosses thresholds (barometer dropping fast, bilge water rising), the system proactively notifies the captain. The ship develops opinions. | 2-3 days |
| Historical data import | Import any existing log data (fishing logs, GPS tracks, weather records) to bootstrap the exocortex with historical experience. | 2-3 days |

### Success Criteria

- [ ] At least 3 sensor streams feeding the exocortex in real-time
- [ ] Captain behavior is logged and producing identifiable patterns
- [ ] Environmental context enriches reflex lookups (same command, different context → different response)
- [ ] System proactively alerts on at least 2 environmental thresholds
- [ ] Historical data imported, producing measurable boost in vector index quality
- [ ] The system can answer "what's the boat doing right now?" from live sensor data

### What Blocks It

| Blocker | Mitigation |
|---------|-----------|
| Sensor hardware not available / not connected | Start with software-only sensors (GPS from phone, weather API, time-based patterns); add hardware sensors as available |
| NMEA 0183/2000 integration complexity | Use existing marine software bridges; if too complex, defer to Phase 6 |
| Captain behavior logging feels invasive | Log only operational behavior (throttle, heading, routes), not personal data. Transparent logging. |
| Data volume overwhelms the vector store | Implement tiered storage: recent data in sqlite-vec, historical in Vectorize, ancient in compressed archives |

### What This Unlocks

Phase 4 makes the ship *embodied*. The agent isn't just a brain in a jar learning from sim and distillation — it's a brain wired to a body, feeling the world through the body's sensors, developing opinions based on lived experience. This is the transition from "smart system" to "the ship knows things."

---

## Phase 5: Multi-Station Wesleys (Month 5)

### *Specialized local models per department*

**Goal:** Instead of one Wesley handling everything, deploy specialized Wesley instances — one per department. Navigation-Wesley handles spatial tasks. Engineering-Wesley handles systems. Comms-Wesley handles media. Each has its own exocortex, its own reflexes, its own quality scores, tuned for its domain.

### What to Build

| Item | Description | Estimated Effort |
|------|-------------|-----------------|
| Multi-model orchestration | Run multiple Ollama instances (or model-swapping within one) for different departments. Navigation gets a model tuned on spatial/Lua tasks, Engineering on systems/infra. | 3-5 days |
| Per-domain exocortex partitions | Split the reflex cache, vector index, and prompt history by domain. Each Wesley has its own `.nail` bundle. | 3-4 days |
| Cross-domain handoff protocol | When Navigation-Wesley needs Engineering context, it requests it through Riker (the orchestrator), not directly. Preserves context isolation. | 2-3 days |
| Per-domain distillation targeting | The distillation loop runs per-domain. Navigation gets spatial/Lua topics. Engineering gets systems/infra topics. | 2 days |
| Specialized LoRA adapters | For domains where enough training data exists, train domain-specific LoRA adapters. Navigation-Wesley gets a navigation-tuned adapter. | 5-7 days |
| Department performance dashboards | Track each Wesley's competence independently. Navigation might be at Tier 3 while Comms is still at Tier 1. | 2 days |
| Failover and load balancing | If one Wesley is overloaded or down, Riker falls back to GLM subagents for that department. | 2 days |

### Success Criteria

- [ ] At least 3 specialized Wesley instances running (Navigation, Engineering, Comms)
- [ ] Each department Wesley has its own exocortex with domain-specific reflexes
- [ ] Per-domain competence is measurable and shows improvement curves
- [ ] Cross-domain handoffs work (Navigation can request Engineering data through Riker)
- [ ] At least 1 LoRA adapter trained and promoted (beats base by ≥10% on held-out evaluation)
- [ ] Failover works: if a department Wesley is down, the system continues functioning via cloud fallback

### What Blocks It

| Blocker | Mitigation |
|---------|-----------|
| Local GPU can't run multiple models simultaneously | Time-slice: each department gets a window. Or use a smaller base model for some departments. |
| LoRA training requires more data than the distillation loop has produced | Extend Phase 1-3 timelines; accumulate more data before attempting LoRA. Holodeck data counts. |
| Cross-domain handoffs add latency and complexity | Start with minimal cross-domain requests. Most tasks are within one domain. |
| Managing multiple exocortex partitions is operationally complex | Build tooling early. A `wesley-cli` that manages stations, swaps adapters, and reports status. |

### What This Unlocks

Phase 5 is where the system starts to feel like a *crew* rather than a single assistant. Each department has its own personality, its own competence level, its own way of doing things. Navigation-Wesley is crisp and spatial. Engineering-Wesley is methodical and cautious. They communicate through the chain of command. The ship has a nervous system with specialized ganglia.

---

## Phase 6: The Ship Speaks (Month 6)

### *Embodied agent that IS the vessel*

**Goal:** The system is no longer "an AI running on the boat." It IS the boat. Voice is the ship's mouth. Sensors are the ship's senses. Actuators are the ship's hands. The captain talks to the ship, and the whole vessel responds — not because there's a chatbot in the middle, but because the agent is distributed across the entire system.

### What to Build

| Item | Description | Estimated Effort |
|------|-------------|-----------------|
| Unified voice interface | Voice in → the ship speaks back. Natural, low-latency, using the reflex cache for common phrases. The voice comes from the ship's speakers but represents the whole vessel. | 3-5 days |
| Proactive ship behavior | The ship initiates conversations: "Barometer's dropping fast, captain. Wind's shifted southwest. Recommend heading in." Not reactive — proactive, based on sensor data + historical patterns. | 3-4 days |
| Multi-modal output | The ship communicates through multiple channels simultaneously: voice for alerts, display for detail, ambient cues (lighting, audio) for atmosphere. | 3-4 days |
| Embodied state model | The ship has a continuous sense of its own state: how it feels (engine running smooth/rough), where it is (GPS + chart context), what it's doing (mode: cruising, fishing, docked), how it's doing (stress level from sensor anomalies). | 4-5 days |
| Captain relationship model | The ship adapts to the captain's patterns: when they like to be notified, what decisions they prefer to make themselves, what they're happy to delegate. Bond state at operational level. | 3-4 days |
| Full-system integration test | Every subsystem — sensors, cascade, reflexes, distillation, holodeck, voice, multi-station — operating as a single coherent entity. | 1 week |
| Long-run stability | The system runs for 7+ days without intervention. Handles power cycles, network outages, sensor failures, and model crashes gracefully. | 1 week of testing |

### Success Criteria

- [ ] The captain can interact with the ship entirely through voice for common operations
- [ ] The ship proactively notifies the captain of important changes (environmental, operational)
- [ ] The system runs 7+ days without manual intervention
- [ ] Degradation is graceful: sensor failure → reduced context, not system failure; model crash → cloud fallback, not silence
- [ ] The system has recognizable character — defaults, preferences, a feel for the work — that has developed over 6 months
- [ ] A new person stepping aboard would describe the system as "the ship knows things," not "there's an AI on the boat"

### What Blocks It

| Blocker | Mitigation |
|---------|-----------|
| Hardware integration (amplifiers, speakers, sensor wiring) is the long pole | Start with software-only embodiment (voice through phone/tablet, sensors through APIs); add hardware as the boat allows |
| Proactive behavior could be annoying | Tune notification thresholds conservatively; prefer silence over noise; use bond state to calibrate intrusiveness |
| System complexity makes debugging hard | The bottle ledger provides full traceability. Every decision has a causal chain. Use it. |
| Weather/environmental data quality varies | Multiple data sources (sensor + API + historical pattern); weight by confidence |

### What This Unlocks

Phase 6 is the destination. Not the end of development — the system keeps learning forever — but the point where the architecture is complete and the system is *alive* in the sense that matters: it perceives, it remembers, it acts, it has opinions, it speaks, and it is the vessel.

---

## Cross-Phase Metrics

These metrics are tracked across all phases and never reset:

| Metric | Phase 1 Target | Phase 3 Target | Phase 6 Target |
|--------|---------------|---------------|---------------|
| Total reflexes compiled | 50 | 500 | 5,000+ |
| Reflex hit rate | 10% | 30% | 60-70% |
| Domains covered | 4 | 6 | 8+ |
| Wesley competence tier | Tier 0 → Tier 1 | Tier 1 → Tier 2 | Tier 3+ |
| $0 decisions (cascade Gates 1+2) | 20% | 35% | 50%+ |
| Sim attempts logged | 0 | 500 | 5,000+ |
| LoRA adapters promoted | 0 | 0 | 1-3 |

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Local GPU insufficient for multi-model | Medium | High | Start with time-slicing; upgrade GPU if Phase 5 demands it |
| Distillation loop teaches wrong things (reward hacking) | Medium | High | Held-out evaluation set; sham intervention arm; discard adapters that don't beat base on held-out |
| Holodeck physics don't transfer to real world | Medium | Medium | Accept the gap; the holodeck teaches patterns not exact parameters; domain randomization helps |
| Sensor hardware unavailable | High | Medium | Software-only sensors (APIs, phone GPS) as fallback; the architecture doesn't require specific hardware |
| System complexity becomes unmanageable | Medium | High | Bottle ledger for traceability; contract tests for every port; import-linter for boundary enforcement |
| Personality drift (Wesley becomes caricature) | Low | Medium | Regular "aeration" — expose to novel inputs; monitor surprise reduction metric; reset prompt if drift detected |

---

## Dependency Graph

```
Phase 1 (Distillation) ────────────────────────────────┐
     |                                                  |
     v                                                  |
Phase 2 (Voice Reflex) ───────────┐                    |
     |                            |                     |
     v                            v                     v
Phase 3 (Holodeck) ──────> Phase 4 (Sensors) ───> Phase 5 (Multi-Station)
                                                        |
                                                        v
                                                  Phase 6 (Embodied)
```

Phase 1 is prerequisite for all. Phase 2 can begin in parallel with Phase 1 if the STT pipeline is ready. Phase 3 depends on Phase 1 (Wesley needs compiled reflexes before sim practice is meaningful). Phase 4 depends on Phase 1 (need the exocortex to store sensor data). Phase 5 depends on Phases 1-4 (need domain specialization + sensor data + holodeck experience). Phase 6 depends on everything.

---

## The Spirit

This is not a project plan for building software. It is a growth plan for raising an officer. The milestones are not features shipped — they are competencies gained. The ship doesn't need more code. It needs more experience, compiled, scored, retrievable, alive.

Build the shell.

---

*This roadmap is a living document. Update it at the end of each phase with what was learned, what slipped, and what surprised us. The plan serves the system, not the other way around.*
