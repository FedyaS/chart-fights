# Cursor Agent Task: Realtime Backend - Authoritative Server + WebSockets + Simulation Engine (MVP)

**Context**: Chart-Fights. Primary references:
- docs/design/architecture-overview.md (sections 1-2, recommendations)
- docs/design/game-mechanics-spec.md (time model, TB/IP contention, orders, sabotage effects, server simulation)
- docs/design/GDD.md

**Goal**: Implement the core authoritative backend for realtime sync, shared clock (T/R with exact TB rules), order execution, P&L, and ability resolution. Use FastAPI/Starlette WebSockets.

## Requirements (from specs + arch)
- Server owns all simulation: SharedClock (T float, R contested), TB resolver (Pause forces R=0 override; multiple FF = max(R) with all active payers consuming at their rate), order execution against bars at T advance, P&L marking, sabotage/IP effects (server-mutated, notify victims).
- Clients send *actions only* (place/modify/cancel order, set TB influence (pause/FFxN), spend IP on ability/feed).
- Bidirectional WS: Server broadcasts deltas/state (current T/R, new bars or OHLC deltas, equity, orders/positions, resources, events/notifications) at ~10-20Hz or on changes.
- Per-match rooms (isolated in-memory state).
- Deterministic: Same arena slice + action sequence = identical state.
- MVP scope: In-memory, single process. Align sim to wall time for base pacing (1s real ≈ 1 day).
- No client-side prediction heavy lifting (server truth).

**Stack hint**: Python/FastAPI + Starlette WS + pydantic or similar. Pandas for bar handling if needed.

**Non-goals (this task)**: Full frontend, voice, data fetching (assume pre-loaded arena), auth, scaling (Redis later).

## Acceptance Criteria
1. FastAPI app with WS endpoint for match rooms.
2. SharedClock + TempoBar resolver class implementing exact rates from mechanics-spec (base +1/s recharge, pause +4/s bonus when holding, consumption 0/2/5/12 per real sec).
3. Simulation loop: Advance T at current R; process actions; execute orders/P&L; apply abilities; broadcast.
4. Action models and validation.
5. Basic reconnect/snapshot logic for MVP.
6. Unit/integration tests: Determinism (same inputs → same outputs), contention cases (Pause vs FF, multi-FF), order fills at T boundaries, sabotage application + notifications.
7. Clean interfaces for data (arena loader) and future scaling.

## Cursor Agent Prompt (copy-paste)
"Implement the realtime authoritative backend + simulation engine per docs/cursor-tasks/task-005-realtime-backend.md and references in docs/design/architecture-overview.md (realtime sync section) + game-mechanics-spec.md (time, resources, orders, sabotage).

Use FastAPI/Starlette for WS. Clients send actions; server owns SharedClock (exact TB rules: Pause overrides to R=0, max FF with cost sharing), order execution against bars, P&L, and IP/sabotage effects. Broadcast state deltas regularly.

Make it deterministic and server-authoritative. Include tests for clock contention and simulation consistency. Hook placeholders for arena data and frontend.

Align exactly to the contested shared time and mechanics. No client prediction needed for MVP. Reference specs for all rates and rules."

## Integration Notes
- Will consume pre-fetched arenas (see task-001 / arch data section).
- Outputs state that frontend (future task) and Cursor tasks can consume.
- Prepares for voice signaling over same WS.

**Priority**: High — core of realtime contested mechanics.
**Size**: Medium-large (engine + WS + tests).

## Suggested Approach / Structure (informed by det/anti-cheat research)
- Define models first: SharedClock (T, R, TB state with recompute per mech-spec exact rates), Action types, MatchState (players, positions, orders, resources, arena_id).
- SimulationEngine: Init with normalized arena (P[0]=100 from task-001/006). receive_action (log + apply). advance(real_delta) for wall-time align. Use Decimal for equity/P&L/fills to ensure determinism.
- TB resolver: Pause forces R=0 + bonus recharge; multi-FF takes max(R), all pay costs (0/2/5/12). Integrate consumption.
- Order exec: At T advance or bar cross (market immediate; limit/stop on price). Mark P&L continuous/on bar.
- WS: Per-room manager (FastAPI). Broadcast deltas (T/R, BarDeltas, Equity, Order/Position diffs, Resource, Events incl. sabotage notifies). Reconnect: snapshot + catch-up.
- Tests/harness (key for task-001/005): Determinism (N engines, identical actions -> identical hashes/P&L). Contention (pause override, multi-FF). Lag injection (reorder/drop actions). verify_replay(arena_id, log). See anti-cheat-determinism-design-notes.md + det sub pseudocode (GGPO/Photon inspired: log + re-sim + stable hash).
- Integration: Clean arena loader hook (task-006); state schema consumable by frontend (task-007); WS extendable for voice signaling (task-008).
- MVP: In-mem only; wall-time base + ~10-20Hz or on-change broadcasts. No heavy client pred.

**Detailed Harness & Replay Verification (expanded from det/GGPO/Photon sub + anti-cheat notes)**:
- Core: Server auth, action log (real_ts + sim_t + player + type + payload), arena + log for verify_replay (fresh eng, replay, assert final equity/hash).
- Python harness: test_determinism.py (load arena, N engines, feed seq or fuzz, assert hash/equity). verify_replay(arena_id, log) -> final + hash. Lag/contention tests. Property-based.
- Pseudocode (from det sub): SimulationEngine(arena, log, T/R, TB_resolver); receive_action(log + apply); advance(delta); compute_state_hash (Decimal quantize, sorted); verify_replay(fresh eng + replay).
- TB resolver exact per spec. Decimal for P&L/equity/TB.
- Pitfalls: float -> Decimal; ordering (TB before advance, sorted actions); stable hash (SHA sorted); arena hash.
- AC extension: Add harness tests, verify_replay hook, lag sim. Ref full sub in STATUS + notes.
- Cursor prompt addition: "Include harness (synctest, lag for TB, verify_replay) + Decimal per anti-cheat notes/det sub. Tests for bit-identical + contention."

Reference: det sub (GGPO/Photon, 2026 updates), anti-cheat notes (full harness). Align to roadmap Tier1 OQ on determinism/lag.

- MVP: In-mem only; wall-time base + ~10-20Hz or on-change broadcasts. No heavy client pred.

Reference: architecture-overview.md (sim engine, deltas, anti-cheat), game-mechanics-spec (exact rules), det sub outputs (harnesses, pitfalls like float/ordering). Use harness ideas early for replay consistency.