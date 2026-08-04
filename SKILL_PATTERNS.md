# SuperInstance Exocortex — Compiled Skill Patterns

**Version:** 1.0 · **Date:** 2026-08-04 · **Status:** Active

> *Any repeated job becomes a skill. If I find myself dispatching the same pattern three times, that pattern should be a subagent skill — a compiled reflex in the workflow layer. This is the Pincher pattern applied to my own operations.*

---

## Table of Contents

1. [Pattern: Extract Standalone Repo from Game Module](#1-extract-standalone-repo-from-game-module)
2. [Pattern: Creative Writing Batch](#2-creative-writing-batch)
3. [Pattern: Quality Audit a Repo](#3-quality-audit-a-repo)
4. [Pattern: Dispatch Ideation Across Multiple Models](#4-dispatch-ideation-across-multiple-models)
5. [Pattern: Research and Synthesize](#5-research-and-synthesize)
6. [The Meta-Pincher Pattern](#6-the-meta-pincher-pattern)

---

## 1. Extract Standalone Repo from Game Module

### *Done 12+ times. This is the most executed pattern in the system.*

### Trigger

A game module in `lucineer-roblox/` or `slackwater-cognition/` has grown complex enough to warrant its own repository. The module has external value — it could be reused in other projects, tested in isolation, or developed independently.

### Steps

```
1. ASSESS the module
   ├── What does it do? (1-2 sentences)
   ├── What are its dependencies? (internal modules, external libs)
   ├── Is the dependency graph clean enough to extract?
   └── Decision: extractable → proceed; too coupled → document and defer

2. CREATE the repo scaffold
   ├── mkdir /home/eileen/projects/<new-repo-name>/
   ├── Create README.md (purpose, installation, usage)
   ├── Create LICENSE (match parent project)
   ├── Create .gitignore (language-appropriate)
   └── git init && git remote add origin <url>

3. EXTRACT the code
   ├── Copy source files, preserving directory structure
   ├── Remove game-specific imports (Instance, game:GetService, etc.)
   ├── Replace with adapter interfaces (ports pattern)
   ├── Create a null/null_adapter for testing without the game
   └── Ensure zero game-specific imports in core/

4. ADD tests
   ├── Unit tests for each public function
   ├── Contract tests if ports are defined
   └── At least one integration test on the null adapter

5. ADD documentation
   ├── README.md (installation, usage, API)
   ├── DESIGN.md (architecture decisions, if non-trivial)
   └── CHANGELOG.md (initial version)

6. VERIFY
   ├── All tests pass
   ├── Syntax check passes (lua5.1 -c or equivalent)
   ├── No game-specific imports remain
   └── The repo works standalone (clone, install, test, run)

7. INTEGRATE
   ├── Update parent project to reference the new repo (git submodule or copy)
   ├── Verify parent project still works
   └── Document the extraction in both repos
```

### Expected Output

```
/home/eileen/projects/<new-repo>/
├── README.md
├── LICENSE
├── .gitignore
├── src/             (or equivalent)
├── tests/
├── docs/
│   └── DESIGN.md
└── .git/
```

### Success Criteria

- [ ] Repo exists with clean directory structure
- [ ] All source files pass syntax check
- [ ] Tests exist and pass
- [ ] Zero game-specific imports in core code
- [ ] README explains what it does and how to use it
- [ ] Git repo initialized with clean initial commit
- [ ] Parent project references the new repo correctly

### Common Failures

| Failure | Cause | Fix |
|---------|-------|-----|
| Game-specific imports remain | Module was tightly coupled to game context | Create adapter interfaces; move game-specific code to adapter/ |
| Tests are trivial (just "it loads") | Developer didn't identify testable units | Write tests for each public function's behavior, not just existence |
| Missing dependencies not documented | Forgot to list what the module needs externally | Check all `require()` / `import` statements; document each |
| Directory structure doesn't match conventions | Ad hoc structure instead of following the established pattern | Use the repo layout from REPO_DESIGN.md §3 as template |
| Extraction breaks parent project | Parent still imports from old location | Update all import paths in parent; use git submodule or copy script |

### Historical Executions

1. `batten-spline` (extracted from slackwater-cognition routing logic)
2. `roblox-beatclock` (extracted from slackwater-tempo)
3. `roblox-bond-system` (extracted from lucineer-roblox relationship system)
4. `roblox-builder-kit` (extracted from build command system)
5. `roblox-craftmind-agents` (extracted from agent logic)
6. `roblox-filtergate` (extracted from content filtering)
7. `roblox-world-scanner` (extracted from world scanning)
8. `slackwater-harmony` (extracted from music system)
9. `slackwater-lattice` (extracted from structural system)
10. `slackwater-perception` (extracted from sensor system)
11. `roblox-audio-suite` (extracted from audio system)
12. `roblox-build-animator` (extracted from animation system)

---

## 2. Creative Writing Batch

### *Done 5+ times. Production of essays, lore documents, character content, or narrative material.*

### Trigger

The captain requests a batch of creative writing — essays, lore documents, character backstories, narrative pieces. The work benefits from a specific model's voice (Hermes for warmth, Opus for depth, Seed-mini for creative novelty).

### Steps

```
1. DECOMPOSE the request
   ├── How many pieces? What length each?
   ├── What voice? (Lucineer's gruff, academic essay, poetic, technical)
   ├── What source material informs the writing?
   └── What's the output format? (markdown files, single document, sections)

2. SELECT the model
   ├── Hermes-3-405B → personality, warmth, character voice
   ├── Opus 5 → depth, precision, the hard passages
   ├── Seed-2.0-mini → creative ideation, novel angles
   ├── GLM-5.2 subagents → bulk generation from clear specs
   └── Multiple models → panel discussion format (different perspectives)

3. DISPATCH
   ├── Give each piece a specific spec (topic, length, voice, source material)
   ├── For batch: dispatch multiple subagents in parallel
   ├── For single piece: dispatch to one specialist
   └── For panel: dispatch same prompt to multiple models, synthesize

4. REVIEW and SYNTHESIZE
   ├── Read each output against the spec
   ├── Check voice consistency across pieces
   ├── Flag any contradictions between pieces
   ├── If batch: ensure pieces are distinct, not variations of each other
   └── Compile into final format

5. SAVE
   ├── Write to appropriate location (ai-writings/ESSAYS/, IDEATION/, etc.)
   ├── Follow naming convention (UPPERCASE_WITH_UNDERSCORES.md)
   └── Update any index files (README.md, etc.)
```

### Expected Output

N markdown files, each:
- Following the specified voice consistently
- Within ±20% of requested length
- Drawing from specified source material
- Structured with clear sections and headers
- Saved to the correct directory

### Success Criteria

- [ ] All requested pieces are present
- [ ] Voice is consistent with the character/style guide
- [ ] No piece is a thin rewrite of another
- [ ] Source material is reflected, not copied
- [ ] Files saved to correct location with correct naming
- [ ] Index files updated if they exist

### Common Failures

| Failure | Cause | Fix |
|---------|-------|-----|
| All pieces sound the same | Didn't vary the prompts enough | Give each piece a distinct angle, constraint, or perspective |
| Voice drifts mid-piece | Model lost the character context | Include voice samples / examples in the prompt; shorter pieces |
| Too generic / could be about anything | Source material not specific enough | Include concrete details, quotes, or events the piece must address |
| Pieces contradict each other | No cross-referencing between dispatches | Synthesize after first draft; flag contradictions; re-dispatch fixes |
| Overproduced (too flowery) | Model defaulting to creative-writing voice | Constrain: "plain prose, no adjectives for emotions, show don't tell" |

### Historical Executions

1. The Ideation series (8 pieces on exocortex architecture)
2. The Three Timescales of Learning essay
3. The Organ Plays Itself (fable)
4. The Body Is the Agent (ideation)
5. The Holodeck Protocol
6. Exocortex Architecture essay
7. Multiple Lucineer lore pieces

---

## 3. Quality Audit a Repo

### *Done 9+ times. Systematic review of a repository's code, structure, tests, and documentation.*

### Trigger

A repo needs review — either because it's been a while, because it was extracted and needs validation, or because quality issues are suspected.

### Steps

```
1. SURVEY
   ├── Read README.md (does it accurately describe the repo?)
   ├── List directory structure (tree -L 3 or find . -type f)
   ├── Count files by type
   └── Identify the "shape" of the repo (library? app? game module?)

2. CODE QUALITY
   ├── Run syntax check on every source file (lua5.1 -c, tsc, ruff, etc.)
   ├── Check for dead code (unused functions, unreferenced files)
   ├── Check for duplication (similar logic in multiple places)
   ├── Check naming consistency (file names, function names, variable names)
   └── Check error handling (do functions fail gracefully?)

3. TEST COVERAGE
   ├── Are there tests? How many?
   ├── What's covered? What's not?
   ├── Are tests meaningful (testing behavior) or trivial (testing existence)?
   ├── Do they all pass?
   └── Are there obvious untested paths?

4. DOCUMENTATION
   ├── README accuracy (does it match the actual repo?)
   ├── Are functions documented? (docstrings, comments)
   ├── Is there a DESIGN.md or architecture doc?
   ├── Are there obvious "why" questions the docs don't answer?
   └── Is the CHANGELOG up to date?

5. DEPENDENCIES
   ├── Are all dependencies documented?
   ├── Are there undeclared dependencies?
   ├── Are dependency versions pinned?
   └── Are there unused dependencies?

6. STRUCTURE
   ├── Does the directory structure follow conventions?
   ├── Are concerns properly separated?
   ├── Is there a core/adapter split where appropriate?
   └── Are there circular dependencies?

7. REPORT
   ├── Overall grade: A / B / C / D
   ├── Critical issues (must fix)
   ├── Important issues (should fix)
   ├── Nice-to-have improvements
   └── What's done well (preserve these)
```

### Expected Output

A structured report in markdown:

```markdown
# Quality Audit: <repo-name>

**Date:** YYYY-MM-DD
**Grade:** X

## Summary
[2-3 sentences]

## Critical Issues
1. [issue with file/line reference]
2. ...

## Important Issues
1. ...

## Nice-to-Have
1. ...

## What's Done Well
1. ...

## Recommendations
[Prioritized action list]
```

### Success Criteria

- [ ] Every source file checked for syntax
- [ ] Every function checked for documentation
- [ ] Test coverage assessed (not just "tests exist" but "what's tested")
- [ ] At least 3 specific issues identified (or "no issues found" with evidence)
- [ ] Grade assigned with justification
- [ ] Recommendations are actionable (specific file, specific change)

### Common Failures

| Failure | Cause | Fix |
|---------|-------|-----|
| Generic findings ("add more tests") | Didn't dig into specific files | Require line-number citations for every issue |
| Missed the big picture | Went file-by-file without understanding the architecture | Start with README + DESIGN.md before individual files |
| Findings are style preferences, not issues | Confusing personal taste with quality problems | Focus on: correctness, maintainability, testability. Not: "I'd name this differently." |
| Didn't run the tests | Only read them | Actually execute the test suite. Note failures. |

### Historical Executions

1. `slackwater-cognition` (11,533 lines — comprehensive audit)
2. `lucineer-roblox` (multiple audits as game evolved)
3. `lucineer-worker` (Cloudflare Worker audit)
4. `batten-spline` (post-extraction audit)
5. `thought-amplifier` (design audit against master prompt)
6. Multiple `study-*` repos during deep-dive analysis

---

## 4. Dispatch Ideation Across Multiple Models

### *Done 3+ times. Sending the same prompt to multiple models and synthesizing their responses into a panel discussion.*

### Trigger

A complex design question where no single model has the right answer. The question benefits from multiple perspectives — a "panel discussion" where different models bring different strengths.

### Steps

```
1. FRAME the question
   ├── Write the prompt carefully — same prompt goes to all models
   ├── Include context that all models need (architecture docs, constraints)
   ├── Specify output format so responses are comparable
   └── Number the questions for easy cross-referencing

2. SELECT the panelists
   ├── Choose models with complementary strengths:
   │   ├── Seed-2.0-mini: creative, fast, cheap
   │   ├── Qwen3-Max: deep reasoning, structured analysis
   │   ├── Hermes-3-405B: personality, character voice, warmth
   │   ├── Nemotron-Ultra: heavy reasoning, cathedral-scale
   │   └── DeepSeek-V3: cost-effective depth
   ├── 3-5 models is the sweet spot (fewer = not enough diversity; more = synthesis nightmare)
   └── Assign roles: "the pragmatist," "the philosopher," "the engineer"

3. DISPATCH
   ├── Send identical prompt to each model
   ├── Do NOT let them see each other's responses (parallel, not sequential)
   └── Collect all responses

4. SYNTHESIZE
   ├── Read all responses
   ├── Identify points of convergence (where models agreed — high confidence)
   ├── Identify points of divergence (where models disagreed — interesting)
   ├── Identify novel insights (each model's unique contribution)
   ├── Identify blind spots (what NO model addressed)
   └── Write synthesis: convergence → divergence → novel insights → blind spots

5. FORMAT
   ├── If presenting to captain: synthesis document with quoted excerpts
   ├── If feeding to another model: structured comparison table + synthesis
   └── If saving as artifact: panel discussion format with named participants
```

### Expected Output

Either:
- A **panel discussion document** with each model's perspective clearly attributed, followed by synthesis
- A **comparison table** with models as columns, questions as rows
- A **synthesis brief** that extracts the actionable insights

### Success Criteria

- [ ] All selected models responded (no API failures)
- [ ] Each model's response is substantive (not a one-liner)
- [ ] Synthesis identifies convergences and divergences
- [ ] At least one novel insight per model is highlighted
- [ ] Blind spots are documented
- [ ] The output enables a decision, not just a survey

### Common Failures

| Failure | Cause | Fix |
|---------|-------|-----|
| All models say the same thing | Prompt too constrained, or question is obvious | Ask a harder question, or relax constraints to invite creativity |
| Synthesis is just "model A said X, model B said Y" | Didn't actually synthesize | Find the WHY behind divergence. What assumption differs? |
| One model dominates the synthesis | That model's response was more structured/compelling | Give each model equal airtime in the synthesis; let the captain decide |
| Missing the obvious answer | No model thought of it | Document as a blind spot; may need a different prompting strategy |
| API costs too high | Used expensive models for a preliminary question | Start with cheap models (Seed-mini, DeepSeek); escalate to expensive only if needed |

### Historical Executions

1. Multi-Model Panel Discussion on browser-native AI architecture (3 models)
2. DeepInfra perspective pieces (Hermes, Qwen, Seed-mini on the same prompt)
3. Architecture validation across models for thought-amplifier design

---

## 5. Research and Synthesize

### *Done multiple times. Web research on a topic, synthesized into a structured document.*

### Trigger

The captain needs to understand a topic, evaluate a technology, or survey the competitive landscape. Requires searching the web, reading multiple sources, and producing a coherent synthesis.

### Steps

```
1. DEFINE the research question
   ├── What specific question are we answering?
   ├── What sub-questions naturally arise?
   ├── What sources are authoritative? (academic papers, official docs, GitHub repos)
   └── What's the output format? (essay, comparison table, technical brief)

2. SEARCH
   ├── web_search with 3-5 query variations to catch different angles
   ├── For each result: fetch the URL, extract content
   ├── Prioritize: official docs > academic papers > reputable blogs > random
   └── Note publication dates — prefer recent over old for tech topics

3. READ and EXTRACT
   ├── For each source: what's the core claim?
   ├── What evidence supports it?
   ├── What's the author's perspective/bias?
   ├── How does it relate to other sources? (confirm, contradict, extend)
   └── Take structured notes: { source, claim, evidence, relation }

4. SYNTHESIZE
   ├── What does the evidence say overall?
   ├── Where do sources agree? (high confidence findings)
   ├── Where do they disagree? (interesting tensions)
   ├── What's missing from the literature? (gaps)
   └── What does this mean for our project? (actionable insight)

5. WRITE
   ├── Structure: executive summary → detailed findings → analysis → recommendations
   ├── Cite sources with URLs
   ├── Distinguish facts from interpretations
   └── Include a "further reading" section

6. SAVE
   ├── Write to appropriate location (ai-writings/, docs/, EXOCORTEX/)
   └── Update indexes if applicable
```

### Expected Output

A structured research document with:
- Clear research question stated upfront
- Multiple cited sources (not just "according to the internet")
- Synthesis section that draws conclusions, not just surveys
- Relevance to our project explicitly stated
- Recommendations or next steps

### Success Criteria

- [ ] At least 5 sources consulted
- [ ] Sources include primary documentation (not just secondary commentary)
- [ ] Synthesis goes beyond summarization (draws conclusions)
- [ ] Relevance to our architecture/system is explicit
- [ ] Document is well-structured and scannable
- [ ] Sources cited with URLs and dates

### Common Failures

| Failure | Cause | Fix |
|---------|-------|-----|
| Source soup (list of sources without synthesis) | Didn't complete the synthesis step | Force yourself to answer: "so what does this mean for us?" |
| Outdated information | Didn't check publication dates | Add date checking to the search protocol; prefer last 12 months |
| Single-source dependence | Found one good article and stopped | Require at least 3 independent sources before synthesizing |
| No connection to our work | Treated it as an academic exercise | End with: "What this means for our system:" section |
| Too broad / unfocused | Research question wasn't specific enough | Narrow the question. "AI memory systems" → "how do local-first AI assistants persist context across sessions" |

### Historical Executions

1. Deep-dive analysis of Pincher (vector DB as runtime)
2. Deep-dive analysis of ZeroClaw Arena (action selection without neural nets)
3. Deep-dive analysis of Lever Runner (three-gate cascade)
4. Browser-native AI research (WebGPU, WebLLM, on-device inference)
5. Multi-model panel research for thought-amplifier design
6. Distillation approaches survey (teacher-student model compression)
7. Exocortex prior art survey (this document set)

---

## 6. The Meta-Pincher Pattern

### *The pattern of patterns.*

### Trigger

Riker notices that the same dispatch pattern has been used three times. Per SOUL.md: "Any repeated job becomes a skill."

### Steps

```
1. NOTICE the repetition
   ├── "I've dispatched this kind of task 3+ times"
   ├── "The dispatch structure is the same even when the content differs"
   └── "I'm copy-pasting from a previous dispatch and changing specifics"

2. EXTRACT the pattern
   ├── What are the fixed steps? (the parts I always do)
   ├── What are the variable parts? (the parts that change each time)
   ├── What are the common failures? (the things that go wrong)
   └── What are the success criteria? (how I know it worked)

3. COMPILE into a skill document
   ├── Write it as a structured pattern (like the ones above)
   ├── Include: trigger, steps, expected output, success criteria, common failures
   └── Save to the skills library

4. USE the compiled skill
   ├── Next time this pattern triggers, reference the compiled skill
   ├── The dispatch becomes: "Follow [Pattern X]. Here are the specifics: ..."
   ├── The subagent reads the pattern and executes the known steps
   └── Review focuses on the specifics, not the process (process is trusted)

5. REFINE over time
   ├── After each execution, note what was different
   ├── If the pattern didn't cover something, add it
   ├── If a step was unnecessary, remove it
   └── The skill evolves with use — just like .nail reflexes evolve
```

### The Deeper Principle

This is the Pincher pattern at the meta level. The Pincher gate compiles repeated inputs into reflexes that bypass the model. The meta-Pincher pattern compiles repeated dispatch patterns into skills that bypass the dispatch reasoning. When a pattern is compiled:

1. **Dispatch is faster** — Riker doesn't need to think about how to structure the task
2. **Output is more consistent** — the subagent follows known-good steps
3. **Quality is higher** — common failures are pre-documented and avoidable
4. **Trust threshold is higher** — the pattern has track record, so review can be lighter

### Current Candidate Patterns (Not Yet Compiled)

These patterns have been noticed but not yet formalized:

- **Pattern: Deploy and verify a Cloudflare Worker** — done 3+ times (lucineer-worker, lucineer-relay, various edge functions). Could be compiled.
- **Pattern: Write a Roblox Luau module from spec** — done 5+ times across the lucineer-roblox codebase. Could be compiled.
- **Pattern: Set up a study repo** — done 30+ times (the study-* repos). Already partially compiled in the form of templates and naming conventions. Could be fully formalized.
- **Pattern: Run the distillation loop and report results** — done multiple times. Could be compiled once the loop is stable.

### When NOT to Compile

Not every repeated task should become a skill. Don't compile when:

- The task is about to change fundamentally (compiling a pattern that's about to be obsolete)
- The task requires judgment that can't be captured in steps (creative decisions, nuanced tradeoffs)
- The task has only been done twice (wait for the third — the pattern needs to prove it's stable)
- The compiled skill would be so specific it only applies to one situation (skills should generalize)

---

*The captain's work patterns compile into reusable crew skills. The crew's work patterns compile into .nail reflexes. The .nail reflexes compile into faster response times. Each level of compilation makes the next level cheaper. This is how the system gets faster as it runs — not by getting smarter, but by needing to think less.*

