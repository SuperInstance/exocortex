# exocortex

[![CI](https://github.com/SuperInstance/exocortex/actions/workflows/ci.yml/badge.svg)](https://github.com/SuperInstance/exocortex/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

🧠 Persistent cognitive substrate for multi-agent systems — tiered in-memory store with optional SurrealDB backend, shadow rendering, tiered compute, ESP32-friendly TAP protocol

---

## Quick Start

```bash
git clone https://github.com/SuperInstance/exocortex
cd exocortex
```

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

## License

MIT

---

*🦀 Part of the **SuperInstance Fleet** — The crab inherits the shell. The forge shapes the steel.*
