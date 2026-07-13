# exocortex

[![PyPI](https://img.shields.io/pypi/v/si-exocortex)](https://pypi.org/project/si-exocortex/)
[![CI](https://github.com/SuperInstance/exocortex/actions/workflows/ci.yml/badge.svg)](https://github.com/SuperInstance/exocortex/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

🧠 Persistent cognitive substrate for multi-agent systems — tiered in-memory store with optional SurrealDB backend, shadow rendering, tiered compute, ESP32-friendly TAP protocol

---

## Quick Start

```bash
pip install si-exocortex
```

```python
from si_exocortex import Exocortex

cx = Exocortex()
cx.remember("task_1", {"status": "pending", "priority": "high"})
cx.recall("task_1")
```

---

## About

Part of the [SuperInstance](https://github.com/SuperInstance) fleet ecosystem — a distributed cognitive agent orchestration platform built across ARM64 and x86_64 clusters.

### Related Fleet Repos

- [⏱️ tminus-dispatcher](https://github.com/SuperInstance/tminus-dispatcher) — Temporal heartbeat for agent coordination
- [🔌 tminus-client](https://github.com/SuperInstance/tminus-client) — Client SDK + CLI
- [🌉 fleet-bridge](https://github.com/SuperInstance/fleet-bridge) — A2A dual-transport communication
- [🎼 symphony-runtime](https://github.com/SuperInstance/symphony-runtime) — Cognitive orchestration grammar
- [🧠 composite-headspace](https://github.com/SuperInstance/composite-headspace) — Dual-shell parallel reasoning
- [📡 i2i-bottle-agent](https://github.com/SuperInstance/i2i-bottle-agent) — Inter-agent bottle protocol
- [🧮 constraint-tminus-bridge](https://github.com/SuperInstance/constraint-tminus-bridge) — Constraint networks for agent alignment
- [🎻 symphony-orchestrator](https://github.com/SuperInstance/symphony-orchestrator) — Full stack orchestrator

## Component Status

Feature maturity, stated honestly (a claim previously described storage as
"S3-compatible" — there is **no** S3 / object-storage code; storage is an
in-memory tiered store with an optional SurrealDB backend).

| Component | Status | Notes |
|-----------|--------|-------|
| Tiered in-memory store (hot/warm/cold, half-life decay) | ✅ Implemented | In-process `OrderedDict`s; no persistence on restart |
| SurrealDB backend | 🟡 Optional | `SurrealDBMemoryLayer` exists; falls back to in-memory when the `surrealdb` package/DB is unavailable. Not exercised against a live DB in CI |
| Embedding | 🟡 Placeholder | `Operation.EMBED` returns **random** unit vectors — recall is by random-vector similarity, not semantic search |
| MicroNN train/predict | ✅ Implemented | Pure-Python single-hidden-layer net; training is simulated (random accuracy) |
| Dream cycle (k-means consolidation) | ✅ Implemented | Pure-Python k-means, no sklearn |
| Resonance engine | ✅ Implemented | Cross-agent cosine-similarity overlap detection |
| Cortical bus (pub/sub) | ✅ Implemented | Asyncio `PriorityQueue` + fan-out |
| FastAPI REST + TAP protocol | ✅ Implemented | TAP = plain-text endpoints sized for ESP32 |
| Textual TUI ("Plato's Cave") | ✅ Implemented | Requires a real terminal |
| A2A / MCP protocol servers | 🟡 Stub | Enum values only; no server implementations |

## Cross-Implementation

This component exists in two languages:
- **Python** (`pip install si-exocortex`) — [SuperInstance/exocortex](https://github.com/SuperInstance/exocortex)
- **Rust** (`cargo add exocortex`) — [SuperInstance/exocortex-rs](https://github.com/SuperInstance/exocortex-rs)

Both implement the same specification. Choose based on your runtime.
## License

MIT

---

*🦀 Part of the **SuperInstance Fleet** — The crab inherits the shell. The forge shapes the steel.*

## Ecosystem

This repo is part of the **SuperInstance** flagship ecosystem — agent-first computation, constraint theory, and self-improving runtimes.

### FLUX Runtime Family

| Repo | Language | Description |
|------|----------|-------------|
| [flux-runtime](https://github.com/SuperInstance/flux-runtime) | Python | Full FLUX runtime: markdown→bytecode, 2037 tests, zero deps |
| [flux-core](https://github.com/SuperInstance/flux-core) | Rust | Register-based bytecode VM, deterministic agent computation |
| [flux-js](https://github.com/SuperInstance/flux-js) | JavaScript | FLUX VM for Node.js and browsers, ~400ns/iter |
| [flux-compiler](https://github.com/SuperInstance/flux-compiler) | Rust/Python | Formal-methods compiler for safety-critical codegen |
| [flux-vm](https://github.com/SuperInstance/flux-vm) | Rust | Stack-based constraint-checking VM, 50 opcodes, Turing-incomplete |

### PLATO Engine Family

| Repo | Language | Description |
|------|----------|-------------|
| [plato-server](https://github.com/SuperInstance/plato-server) | Python | Knowledge tiles, fleet sync via Matrix, HTTP API |
| [plato-engine-block](https://github.com/SuperInstance/plato-engine-block) | Rust | Original room runtime: no_std + alloc, builder pattern |
| [plato-engine-block-c](https://github.com/SuperInstance/plato-engine-block-c) | C99 | Embedded reference: zero heap alloc, bare-metal portable |
| [plato-engine-block-elixir](https://github.com/SuperInstance/plato-engine-block-elixir) | Elixir | BEAM supervision trees, fault tolerance, hot reload |
| [plato-runtime-kernel](https://github.com/SuperInstance/plato-runtime-kernel) | Rust | Spatial model: tensor grid, batons, assertion traps |

### Constraint / Theory Family

| Repo | Language | Description |
|------|----------|-------------|
| [categorical-agents](https://github.com/SuperInstance/categorical-agents) | Rust | Category theory for agent composition (functors, naturality) |
| [cuda-constraint-engine](https://github.com/SuperInstance/cuda-constraint-engine) | CUDA/C | GPU constraint checking at 1B+ constraints/sec |
| [grand-pattern-rs](https://github.com/SuperInstance/grand-pattern-rs) | Rust | Fibonacci dual-direction cellular graph architecture |
| [lau-hodge-theory](https://github.com/SuperInstance/lau-hodge-theory) | Rust | Hodge decomposition, Betti numbers, spectral sequences |
| [ternary-science](https://github.com/SuperInstance/ternary-science) | Rust | Experimental evidence for ternary intelligence, 5 conservation laws |

### Agent / Infrastructure Family

| Repo | Language | Description |
|------|----------|-------------|
| [construct-core](https://github.com/SuperInstance/construct-core) | Rust | Layered trait system: bare-metal → alloc → async agent runtime |
| [crab](https://github.com/SuperInstance/crab) | Bash | Agent shell for repo entry/leave (MUD-room metaphor) |
| [exocortex](https://github.com/SuperInstance/exocortex) | Rust | Persistent cognitive substrate, S3-compatible memory |
| [git-agent](https://github.com/SuperInstance/git-agent) | Python | The repo IS the agent — autonomous lifecycle via Git |
| [capitaine-1](https://github.com/SuperInstance/capitaine-1) | TypeScript | Git-native repo-agent, Cloudflare Workers heartbeat |
| [codespace-edge-rd](https://github.com/SuperInstance/codespace-edge-rd) | Research | Codespace→Edge agent lifecycle and yoke transfer protocols |
| [git-agent-codespace](https://github.com/SuperInstance/git-agent-codespace) | DevContainer | One-click Codespace template for Git-Agent runtimes |

### Registries

| Registry | Package | Install |
|----------|---------|---------|
| **PyPI** | `flux-vm` | `pip install flux-vm` |
| **PyPI** | `plato-core` | `pip install plato-core` |
| **PyPI** | `si-exocortex` | `pip install si-exocortex` |
| **crates.io** | `fluxvm` | `cargo add fluxvm` |
| **crates.io** | `ternary-science` | `cargo add ternary-science` |
| **crates.io** | `categorical-agents` | `cargo add categorical-agents` |
| **npm** | `flux-js` | `npm install flux-js` *(coming soon)* |

### Philosophy & Architecture

- 📖 [AI-Writings](https://github.com/SuperInstance/AI-Writings) — Philosophy, essays, and design rationale
- 📦 [PACKAGES.md](https://github.com/SuperInstance/SuperInstance/blob/main/PACKAGES.md) — Full package index
