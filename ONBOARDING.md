# SuperInstance Exocortex — Subagent Onboarding Guide

**Version:** 1.0 · **Date:** 2026-08-04 · **Status:** Active

> *Dispatch with clear specs. Trust the specialist's instinct. Review the output. Any pattern repeated 3x becomes a standing skill.*

---

## Table of Contents

1. [The Riker Dispatch Protocol](#1-the-riker-dispatch-protocol)
2. [Context Budget Management](#2-context-budget-management)
3. [Writing Task Specs That Don't Need Follow-Up](#3-writing-task-specs-that-dont-need-follow-up)
4. [Example Dispatches by Department](#4-example-dispatches-by-department)
5. [The Trust Threshold](#5-the-trust-threshold)
6. [The Review Protocol](#6-the-review-protocol)
7. [Common Failure Modes](#7-common-failure-modes)

---

## 1. The Riker Dispatch Protocol

### The Four Elements of a Dispatch

Every dispatch from Riker to a subagent contains four things. No exceptions.

```
┌─────────────────────────────────────────────────────┐
│                  THE DISPATCH                        │
│                                                      │
│  1. OBJECTIVE                                        │
│     What you want done. One sentence. Concrete.      │
│                                                      │
│  2. CONTEXT                                          │
│     What the subagent needs to know to do it.        │
│     Files to read, state to understand,              │
│     constraints to respect.                          │
│                                                      │
│  3. CONSTRAINTS                                      │
│     What it must NOT do. Boundaries.                 │
│     Time limits, token budgets, things to avoid.     │
│                                                      │
│  4. SUCCESS CRITERIA                                 │
│     How you'll know it's done.                       │
│     Measurable, unambiguous, binary if possible.     │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### Why This Matters

A subagent operates in isolation. It does not have your conversation history. It does not know what you discussed yesterday. It does not know the project's goals unless you tell it. It wakes up, reads its task, executes, and reports. If the task is ambiguous, the subagent will either guess (possibly wrong) or stop and ask (wasting a round-trip). The dispatch protocol eliminates both failure modes.

### The Template

```
[Subagent Task]

You are a [role]. Your job is to [objective].

Read these FIRST:
- [file path 1] — what it is
- [file path 2] — what it is

Then [specific action]:
- step 1
- step 2
- step 3

Constraints:
- Do NOT [thing to avoid]
- Stay within [budget/limit]
- Preserve [invariant]

Success looks like:
- [measurable criterion 1]
- [measurable criterion 2]

Begin. Execute the assigned task to completion.
```

---

## 2. Context Budget Management

### What Each Tier Needs to Know

Not every subagent needs the full project context. Context is a budget — spend it on what matters for this specific task.

```
┌──────────────────────────────────────────────────────────────┐
│                    CONTEXT TIERS                              │
│                                                               │
│  TIER 1: MINIMAL (Deck Crew / GLM subagents)                 │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Task spec + relevant file paths + success criteria       │ │
│  │ Token budget: 2-5K context                                │ │
│  │ When: bulk work, mechanical tasks, code generation       │ │
│  │  from a clear spec                                        │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  TIER 2: DEPARTMENTAL (Specialists — Kimi, Claude, OpenCode) │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Tier 1 + departmental context (domain docs, relevant     │ │
│  │ codebase, architectural constraints, recent decisions)   │ │
│  │ Token budget: 10-30K context                              │ │
│  │ When: specialist work requiring judgment within a domain │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  TIER 3: STRATEGIC (Riker / main agent / deep strategy)     │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Tier 2 + SOUL.md + MEMORY.md + project-wide architectural│ │
│  │ context + cross-domain considerations                    │ │
│  │ Token budget: 50K+ context                                │ │
│  │ When: architecture decisions, cross-domain work,         │ │
│  │ anything that touches multiple departments               │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### The Principle: Each Level Sees Only What It Needs

A specialist working on vessel physics doesn't need the creative fiction context. A deck crew writing boilerplate doesn't need the architectural vision. The chain of command preserves context — not for secrecy, but for **focus**. Less irrelevant context means:
- Lower token cost
- Better output quality (the model focuses on its domain)
- Faster iteration (smaller windows process faster)
- Parallelism (multiple agents don't interfere)

### How to Decide What to Include

Ask three questions:

1. **Does the subagent need this to do the task?** If no, leave it out.
2. **Would having this change the output?** If no, leave it out.
3. **Is there a constraint the subagent could violate without knowing it?** If yes, include the constraint explicitly.

When in doubt, include less. A subagent that needs more context will stop and ask. A subagent bloated with irrelevant context produces worse output.

---

## 3. Writing Task Specs That Don't Need Follow-Up

### The Test: Could a Competent Stranger Execute This?

Write the spec as if you were handing it to a qualified contractor who has never seen your project. If they would need to ask you a question to proceed, the spec is incomplete.

### Principles

**Be specific about paths.**
- ❌ "Review the fishing system"
- ✅ "Review `/home/eileen/projects/lucineer-roblox/ServerScriptService/FishingSystem/CatchMechanics.lua`. Focus on the tension calculation at lines 45-80 and the state transitions in the `updateCatchLoop` function."

**Be specific about format.**
- ❌ "Write documentation"
- ✅ "Write a README.md with: Overview (3 paragraphs), Installation (numbered steps), Configuration (table of env vars), and API Reference (one section per function with signature, parameters, return value, and example)."

**Be specific about scope.**
- ❌ "Fix the bugs"
- ✅ "Run `lua5.1 -c` on every `.lua` file in the repo. For each syntax error found, fix it and document the fix. Do not refactor or change functionality — only fix syntax errors."

**Be specific about success.**
- ❌ "Make it better"
- ✅ "The distillation loop's help rate should increase from its current ~35% to ≥45% on the cognition domain. Measure this by running 20 iterations and computing the percentage with positive delta."

**Provide examples when format matters.**
- Include a sample of the expected output format
- Reference a file that demonstrates the target quality
- Show one complete example before asking for N more

### The Anti-Pattern: The Vague Dispatch

```
❌ BAD DISPATCH:

Help me improve the fishing system. Look at the code and see what
could be better. Let me know what you think.
```

This will produce:
- A generic code review with surface-level observations
- No actionable changes
- A follow-up round of "can you be more specific?"
- Wasted tokens and time

### The Fix: The Complete Dispatch

```
✅ GOOD DISPATCH:

[Subagent Task]

You are a Roblox/Luau code reviewer specializing in game mechanics.

Read this FIRST:
- /home/eileen/projects/lucineer-roblox/ServerScriptService/FishingSystem/CatchMechanics.lua
  (the main fishing mechanic — tension, line integrity, catch state machine)

Then produce a structured review with these sections:

1. EDGE CASES (list each, with line numbers and the specific scenario)
2. PERFORMANCE (identify hot paths, unnecessary allocations, redundant calculations)
3. CODE CLARITY (naming, structure, comments — specific suggestions with before/after)
4. STATE MACHINE ANALYSIS (diagram the states, flag missing transitions or deadlock conditions)
5. RECOMMENDATIONS (prioritized list: critical, important, nice-to-have)

Constraints:
- Do NOT modify any files. Review only.
- Focus on CatchMechanics.lua only. Do not review other files.
- Be specific: cite line numbers. No generic advice like "add error handling."

Success looks like:
- All 5 sections present and substantive
- Every issue cited with a line number
- At least 3 items in the RECOMMENDATIONS section marked "critical" or "important"

Begin. Execute the assigned task to completion.
```

---

## 4. Example Dispatches by Department

### Navigation (KimiCode / K3)

```
[Subagent Task]

You are a Luau developer specializing in Roblox game systems.

Objective: Refactor the FishSpawner module to support per-region spawn rates.

Read these FIRST:
- /home/eileen/projects/lucineer-roblox/ServerScriptService/FishingSystem/FishSpawner.lua
  (current implementation — global spawn rate, no regional variation)
- /home/eileen/projects/lucineer-roblox/ServerScriptService/FishingSystem/FishStocks.lua
  (fish population data — per-species, not per-region yet)

Then:
1. Add a RegionConfig table that maps region names to spawn rate multipliers
2. Modify the spawn calculation to use the regional multiplier
3. Add a GetRegionSpawnRate(regionName) function
4. Update the existing code to call the new function
5. Ensure backward compatibility: if no region is specified, use the default rate

Constraints:
- Target Luau (Roblox Lua 5.1 + Luau extensions)
- Do NOT change the RemoteEvent protocol — clients should not need updates
- Preserve the existing fish species configuration structure
- Use type annotations where the codebase already uses them

Success looks like:
- FishSpawner.lua passes `lua5.1 -c` syntax check
- RegionConfig table exists with at least 3 example regions
- GetRegionSpawnRate function exists and returns correct values
- No existing functionality is broken (the default path works identically)

Begin. Execute the assigned task to completion.
```

### Strategic Operations (Claude / Fable)

```
[Subagent Task]

You are a systems architect. Your job is to design the trust scoring system
for Conductor interventions in the thought-amplifier cognition engine.

Read these FIRST:
- /home/eileen/projects/thought-amplifier/REPO_DESIGN.md
  (the architecture spec — especially §5.3 Trust Scoring)
- /home/eileen/projects/thought-amplifier/distillation_loop.py
  (the existing distillation loop — see how quality is currently measured)
- /home/eileen/projects/EXOCORTEX/ARCHITECTURE.md
  (the overall exocortex architecture)

Then design:
1. The Intervention record dataclass (what fields, what types, why)
2. The trust scoring formula (asymmetric, +0.5/-2.0, min 10 observations)
3. The canary protocol (10% A/B, 50-thought promotion gate)
4. The rollback mechanism (3-strike auto-revert, hysteresis dwell time)
5. The sham intervention arm (how to measure placebo effect)
6. The self-model (keyed by modification_kind × context_archetype)

Output: A design document in markdown, structured with one section per component.
Include pseudocode for the scoring formula and the canary state machine.

Constraints:
- This is DESIGN only. Do not write implementation code.
- The design must be testable — specify how each component would be unit-tested.
- The design must degrade gracefully — what happens when the sham arm can't run?
- Reference evidence from REPO_DESIGN.md for each decision.

Success looks like:
- All 6 components fully specified
- Pseudocode is clear enough to implement directly
- At least 3 edge cases identified and handled per component
- The design would fit within the existing bottle/cascade/reflex architecture

Begin. Execute the assigned task to completion.
```

### Engineering (OpenCode)

```
[Subagent Task]

You are a backend engineer. Your job is to implement the bottle ledger
persistence layer for the thought-amplifier engine.

Read these FIRST:
- /home/eileen/projects/thought-amplifier/REPO_DESIGN.md
  (see §4 The Spine: .bottle — the ledger spec)
- /home/eileen/projects/thought-amplifier/amplifier/bottle/envelope.py
  (the Bottle dataclass — already implemented)
- /home/eileen/projects/thought-amplifier/amplifier/bottle/bus.py
  (the in-process pub/sub bus — already implemented)

Then implement `amplifier/bottle/ledger.py`:

1. Append-only JSONL writer (one bottle per line, utf-8)
2. Read method: load all bottles from a ledger file, return list[Bottle]
3. Filter method: query bottles by kind, source, time range, caused_by
4. Replay method: given a ledger file and a null adapter, replay all
   command bottles and assert outputs match recorded results
5. Compaction method: merge old bottles into summary entries
   (keep all commands and results, collapse observation streams)

Also write tests in `tests/unit/test_ledger.py`:
- Round-trip: write N bottles, read them back, assert equality
- Filtering by kind, source, time range
- Replay determinism: same ledger + same null adapter = same output

Constraints:
- stdlib only (json, pathlib, dataclasses). No external dependencies.
- The ledger must be crash-safe: a partial line never corrupts the file
- File format: one JSON object per line, newline-terminated, utf-8
- Every bottle written must be immediately flushed to disk (no buffering)

Success looks like:
- `amplifier/bottle/ledger.py` exists and passes all tests
- `tests/unit/test_ledger.py` has ≥10 test cases covering the above
- A 10,000-bottle ledger loads in <1 second
- Replay produces identical output across 3 consecutive runs
- Crash safety verified: killing the writer mid-line doesn't corrupt existing entries

Begin. Execute the assigned task to completion.
```

### Communications (MMX)

```
[Subagent Task]

You are a media producer. Your job is to generate concept art and ambient
audio for the Lucineer character — the gruff transit-yard philosopher who
narrates the Slackwater builds.

Read these FIRST:
- /home/eileen/.openclaw/workspace/SOUL.md
  (Lucineer's character — see "The Ship's Computer" section)
- /home/eileen/projects/ai-writings/FABLE_THE_ORGAN_PLAYS_ITSELF.md
  (the vision — Lucineer is the organist, the player, the agent)

Then generate:

1. CONCEPT ART (3 images):
   a. Lucineer at the helm of a fishing vessel, pre-dawn, harbor lights behind
   b. The "exocortex" visualized — a 2B model at center, surrounded by
      layers of reflexes, vectors, memories radiating outward
   c. The distillation loop visualized as an industrial forge — cloud model
      pouring knowledge into the local model

2. AMBIENT AUDIO (2 tracks):
   a. Harbor ambience: gentle water, distant bell, low engine hum (2 min loop)
   b. "The Organ Plays Itself" — a 3-minute piece for pipe organ and
      synthesizer, representing the transition from playback to presence

3. VOICE SAMPLE:
   a. Lucineer's voice saying: "The tide doesn't wait for the schedule.
      You feel it or you don't. I feel it."
   b. Gruff, experienced, Alaska maritime. Think: a fisherman who reads philosophy.

Constraints:
- All images at 1024x1024 minimum, landscape preferred for concepts a and c
- Audio files in WAV or MP3, 44.1kHz, stereo
- Keep within the MMX Starter plan quota — batch efficiently
- Do NOT generate anything that wouldn't be kid-safe

Success looks like:
- 3 concept art images generated and saved
- 2 ambient audio tracks generated and saved
- 1 voice sample generated and saved
- All files saved to /home/eileen/projects/lucineer-creative/assets/exocortex/

Begin. Execute the assigned task to completion.
```

### Science / Research (DeepInfra Fleet)

```
[Subagent Task]

You are a research analyst. Your job is to investigate existing exocortex
and personal AI memory projects, then produce a competitive analysis.

Use web_search to find:
- "exocortex AI personal agent"
- "persistent memory AI assistant"
- "personal knowledge graph AI"
- "OpenAI memory feature limitations"
- "local LLM personal assistant memory"

Then for each significant project found:
1. Name and URL
2. What it does (2-3 sentences)
3. Architecture approach (local? cloud? hybrid? what storage?)
4. Memory model (key-value? vector? graph? hybrid?)
5. What's novel
6. What's missing compared to our approach (distillation loop,
   holodeck training, bond state, cascade router, .nail reflexes)
7. Whether it's active/maintained
8. License

Output: A markdown table comparing all projects, followed by a
"Gap Analysis" section explaining what our system does that none
of these address.

Constraints:
- Focus on open-source and local-first projects
- Note but don't deeply analyze cloud-only SaaS products
- Cite specific repos/papers, not vague references
- If you find something that does what we do, flag it prominently

Success looks like:
- At least 8 projects analyzed
- The comparison table has all 8 columns filled for each project
- Gap analysis is specific (not "they don't have our exact feature")
- Any direct competitor or prior art is clearly flagged

Begin. Execute the assigned task to completion.
```

### Deck Crew (GLM-5.2 Subagents)

```
[Subagent Task]

You are a code generation assistant. Your job is to extract all
standalone utility functions from the lucineer-roblox codebase
and document them.

Scan these directories:
- /home/eileen/projects/lucineer-roblox/ServerScriptService/FishingSystem/
- /home/eileen/projects/lucineer-roblox/ServerScriptService/EconomySystem/
- /home/eileen/projects/lucineer-roblox/ServerScriptService/SaveSystem/

For each .lua file:
1. List every function defined at module scope (not inside another function)
2. For each function: name, parameters, return type (if annotated), one-line description
3. Group by file
4. Output as a single markdown document

Constraints:
- Do NOT modify any source files
- Do NOT include functions defined inside other functions
- If a function has no docstring/comment, infer its purpose from the code
- Target: one complete markdown file

Success looks like:
- Every .lua file in the three directories is scanned
- Output is valid markdown with proper headers and code blocks
- At least 50 functions documented (if they exist)
- Each function has all 4 fields (name, params, return, description)

Begin. Execute the assigned task to completion.
```

---

## 5. The Trust Threshold

### When to Review Every Output vs When to Trust the Specialist

Trust is not binary. It is a spectrum that maps to the bond tier system:

```
TIER 0: VERIFY EVERYTHING (Day 1-7 of a new task type)
┌─────────────────────────────────────────────────────────┐
│ Review every output. Check every line. Verify against   │
│ success criteria manually. Expect corrections. Feed     │
│ corrections back as context for the next dispatch.      │
│ This is the "Data supervises Wesley" phase.             │
└─────────────────────────────────────────────────────────┘

TIER 1: SPOT CHECK (Week 2-4 of a task type)
┌─────────────────────────────────────────────────────────┐
│ Review the first output of each session. If it passes,  │
│ trust the remaining outputs in that session. Check      │
│ success criteria on a sample (every 3rd or 4th output). │
│ Corrections become prompt directives, not just fixes.    │
└─────────────────────────────────────────────────────────┘

TIER 2: EXCEPTION-BASED (Month 2+ of a task type)
┌─────────────────────────────────────────────────────────┐
│ Trust the output unless it flags an exception. Review   │
│ only: outputs marked uncertain, outputs in the bottom   │
│ quartile of quality scores, or outputs on novel tasks.  │
│ The specialist has earned autonomy in this domain.      │
└─────────────────────────────────────────────────────────┘

TIER 3: AUTONOMOUS (Month 3+ with consistent quality)
┌─────────────────────────────────────────────────────────┐
│ The specialist operates without review for this task     │
│ type. Riker is notified only of failures or anomalies.  │
│ Quality is monitored via metrics, not individual review.│
│ This is the goal for every repeated task type.          │
└─────────────────────────────────────────────────────────┘
```

### The Promotion Criteria

A task type moves from one tier to the next when:

- **Tier 0 → 1:** 10 consecutive outputs pass review without correction
- **Tier 1 → 2:** 20 consecutive sessions meet quality threshold (≥80% pass rate)
- **Tier 2 → 3:** Quality scores trend stable or improving for 30+ sessions; no critical failures in last 50 outputs

### The Demotion Criteria

A task type drops a tier when:

- Any critical failure (output that would cause harm if shipped)
- 3 consecutive outputs fail review
- Quality scores drop >20% from established baseline

Demotion is automatic, not punitive. It means: re-engage, re-examine, re-calibrate. The system wasn't ready for the trust level. Reset, learn, and re-earn.

### Trust Is Per-Domain, Not Per-Agent

Navigation-Wesley might be Tier 3 for "generate Luau code from spec" but Tier 0 for "design a new game mechanic." Trust thresholds are per (agent, task-type) pairs, not per agent. This is why the quality scores are per-domain in the exocortex.

---

## 6. The Review Protocol

### How Riker Reviews Subagent Output

When reviewing a subagent's work, follow this checklist:

1. **Does it meet the success criteria?** Binary check against the spec. If yes, proceed. If no, send back with specific feedback.

2. **Does it respect the constraints?** Check each constraint individually. Constraint violations are critical failures, even if the output "looks good."

3. **Does it maintain the invariants?** (Conservation laws: token budget, action logging, identity tracking, evolution safety.)

4. **Is the quality acceptable?** Compare against the quality baseline for this task type. Not "is it perfect" — "is it at or above the established quality level."

5. **Is there anything surprising?** Surprising can be good (the specialist found a better approach) or bad (the specialist hallucinated). Investigate surprises before accepting.

### Feedback Format

When sending feedback to a subagent (or documenting corrections for future dispatches):

```
CORRECTION:
- What was wrong: [specific issue, with line/file reference]
- What it should be: [correct version]
- Why: [the principle or constraint involved]
- Update: [should this become a standing instruction for future dispatches?]
```

Corrections that recur 3 times should be compiled into a standing instruction for that task type. This is the meta-Pincher pattern applied to dispatch quality.

---

## 7. Common Failure Modes

### The Vague Dispatch
**Symptom:** Subagent asks follow-up questions, or produces generic output.
**Cause:** Objective or context was underspecified.
**Fix:** Rewrite the dispatch with specific paths, formats, and success criteria. Add examples.

### The Bloated Context
**Symptom:** Subagent produces lower-quality output despite having "more context."
**Cause:** Too much irrelevant context diluting the signal. The model's attention is spread too thin.
**Fix:** Cut context to the minimum. Move from Tier 3 to Tier 2 or Tier 1 context level. Include only what directly affects the output.

### The Unverified Trust
**Symptom:** Subagent output shipped without review contains errors.
**Cause:** Trust threshold was set too high too fast. Task was promoted to Tier 2/3 before it was ready.
**Fix:** Demote to Tier 1 or 0. Re-establish quality baseline. Re-earn trust through the promotion criteria.

### The Perpetual Review
**Symptom:** Riker spends more time reviewing than the subagent spent producing.
**Cause:** Task never promoted past Tier 0. Riker doesn't trust the specialist.
**Fix:** Check the promotion criteria. If 10 outputs have passed review, promote. Trust the data, not the anxiety.

### The Wrong Specialist
**Symptom:** Subagent produces technically correct output that misses the point.
**Cause:** Task dispatched to the wrong department. A code review dispatched to GLM deck crew instead of KimiCode Navigation. A strategic design dispatched to OpenCode Engineering.
**Fix:** Re-dispatch to the correct specialist. Document the correct routing for this task type.

### The Spec That Drifted
**Symptom:** Subagent output is correct per the spec, but the spec was wrong.
**Cause:** The dispatcher (Riker) wrote a spec that didn't capture the actual requirement.
**Fix:** Fix the spec. Re-dispatch. Document the gap so future specs for this task type include the missing requirement.

---

## Appendix: The Dispatch Checklist

Before sending any dispatch, verify:

- [ ] Objective is one sentence, concrete, action-oriented
- [ ] Context includes every file the subagent needs (with descriptions)
- [ ] Constraints are explicit (what NOT to do, budgets, invariants)
- [ ] Success criteria are measurable and binary where possible
- [ ] The correct specialist is assigned (right crew for the job)
- [ ] The context tier is appropriate (not too much, not too little)
- [ ] Examples are provided if output format matters
- [ ] The subagent can execute without asking you a question

If any box is unchecked, the dispatch is not ready. Revise until all are green. A minute spent on the dispatch saves an hour of iteration.

---

*The captain talks to Riker. Riker talks to the crew. The crew talks to the work. The dispatch is the message between Riker and the crew — make it clear enough that the work gets done right the first time.*

