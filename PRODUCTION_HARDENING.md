# Production Hardening — Round 4 (2026-07-11)

This document tracks concrete production-readiness fixes for this round.
Each fix is verified independently (real test suite + ruff) before being pushed.

## Scope

Audit of actual source + tests (not just README) for:
- Bugs: wrong logic, off-by-one, untested error paths
- Fake-green tests (always pass regardless of code)
- README claims that don't match what the code actually does
- Missing but feasible test coverage for real branches

See git log on branch `production-round4-2026-07-11` for the per-fix commits.
