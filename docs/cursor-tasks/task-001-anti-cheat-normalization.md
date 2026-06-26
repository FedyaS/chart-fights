# Cursor Agent Task: Anti-Cheat, Normalization, and Determinism Verification (MVP)

**Context**: Chart-Fights. References:
- docs/design/architecture-overview.md (anti-cheat section)
- docs/design/game-mechanics-spec.md (normalization P[0]=100, private arenas, generic labels)
- docs/design/roadmap-and-open-questions.md

**Goal**: Implement mechanisms for normalization, private arena handling, and determinism verification to ensure fairness and prevent external knowledge cheating in matches.

## Requirements (from specs + arch)
- For every match: reset all instrument series so first price = 100.00, use % returns only.
- Instrument labels generic during match (e.g. "Broad Equities"), real names optional post-match.
- Arena selection from pre-loaded private slices (server-side, not client).
- Determinism: same arena + action sequence must produce identical state/P&L for all players.
- Verification: unit tests or harness that replays action log and asserts identical outcomes.
- Logging: full action + arena ID for post-match re-sim or validation.
- Support mystery/randomized start dates if needed for extra anti-cheat.

**Non-goals**: Intraday, live data, real-money, full tournaments (MVP 1v1).

## Acceptance Criteria
1. Normalization function that takes raw OHLC slice and returns normalized to 100 with % deltas.
2. Arena loader that enforces private slices and generic labels.
3. Determinism test: replay same actions on same arena, assert bit-identical state for multiple "players".
4. Action logging sufficient for re-simulation.
5. Integration note for simulation engine to use normalized data.
6. Docs in README or inline explaining anti-cheat approach.

## Suggested Approach / Files to Touch or Create
- `data/normalization.py` or similar for the reset logic.
- Extend arena loader in data pipeline.
- `tests/test_determinism.py` or in existing test_replay.
- Update sim engine to log actions with arena ID.
- Reference in handoff and arch.

## Cursor Agent Prompt to Use (copy this)
"Implement anti-cheat, normalization, and determinism verification for Chart-Fights per docs/cursor-tasks/task-001-anti-cheat-normalization.md and references in docs/design/architecture-overview.md (anti-cheat), game-mechanics-spec.md (normalization section), roadmap-and-open-questions.md.

Create normalization to P[0]=100 using % returns, generic labels during play, private arena enforcement, action logging for re-sim, and tests asserting identical outcomes across players for same inputs. Follow exact rules from specs. No UI or full app code.

Reference research in docs/research/ for data. Ask only for hard blockers."

## Integration Notes
- Depends on data pipeline (task-006) for arenas.
- Used by backend sim (005) and frontend.
- Key for fairness per vision.

**Priority**: High — core to anti-cheat and MVP validity.
**Estimated size**: Small for MVP.
**Owner**: Coding agent (Cursor or other).

**Harness, Replay Verification & Testing Insights (from det/GGPO/Photon sub + anti-cheat notes)**
High-value integration for determinism (ties roadmap Tier1 OQ "prove determinism... lag sim on clock contention"):
- Patterns: Server-authoritative (clients actions-only). Log actions (real_ts + sim_t + player + type + payload). Arena + log = seed for verify_replay (re-init engine, replay sorted log, assert final equity/hash match reported).
- GGPO/Photon/Bevy: Synctest harness (multi-engine identical actions + periodic checksum match). Lag injection on action queue for TB contention (Pause override vs FF max+all-pay). Periodic Decimal state hashes (T/R/equities/positions/TB, sorted, quantized).
- Python harness recs: `tests/test_determinism.py` (load arena, N engines, feed same seq or fuzzed, assert hash/equity identical; property-based with hypothesis). `verify_replay(arena_id, log)` returns final state + hash. Lag/contention tests. Cross-env CI.
- Pitfalls (bar sim): Float -> always Decimal + quantize for P&L/equity/TB/R; consistent op order (TB resolve before advance, sorted simultaneous actions); stable hash (SHA sorted keys, no platform hash()); arena hash for norm data.
- Pseudocode (from sub): SimulationEngine with arena (norm bars), T/R, log, compute_state_hash (Decimal quantize), verify_replay (fresh eng + replay actions). TempoBarResolver exact per spec.
- Integration: Task-006 provides norm arena + hash. Task-005 uses in sim loop (log on receive, advance with TB, periodic cs, post-match verify). Update anti-cheat-determinism-design-notes.md if new.
- AC extension note: Add harness tests, verify_replay hook, lag sim for contention. Reference full sub output in STATUS + design notes.
- Cursor prompt addition: "Include harness (synctest, lag injection for TB, verify_replay) + Decimal hashes per anti-cheat notes and det sub. Tests assert bit-identical + contention cases."

**Sources/Refs**: det sub (GGPO/Photon pseudocode/harness/2026 updates), anti-cheat-determinism-design-notes.md (full details), roadmap OQs, task-005 ACs.

Start by reading the referenced specs and manifest.
