# Chart-Fights: Phased Implementation Roadmap + Open Questions

**Version**: 0.1 (2026-06-26)  
**Sources**: All prior research (GDD, game-mechanics-spec, architecture-overview, data sources, similar products).

## Phased Roadmap (MVP First)

### Phase 0: Foundations (Prep)
- Set up repo, data fetch scripts (yfinance/Stooq), storage (Parquet).
- Define core data models (Arena, Bar, PlayerState, Order, etc.).
- Create .cursorrules / agent prompts for Cursor.
- Basic test harness for determinism.

See docs/cursor-tasks/TASK_MANIFEST.md for the canonical 8 tasks (Phase 0: 001 anti-cheat + 006 data).

### Phase 1: Core Simulation Loop (MVP Playable)
- SharedClock + TempoBar resolver (exact rates from mechanics-spec).
- In-memory match state.
- Order execution (Market/Limit/Stop + attached) against bars at T.
- P&L marking (realized + unrealized).
- Basic server simulation loop (advance T at R; process actions).
- Simple CLI or test harness to run a "match".

See docs/cursor-tasks/TASK_MANIFEST.md for the canonical 8 tasks (Phase 1: 002 time/tempo, 004 orders, 005 realtime).

**Deliverable**: Two "players" (test clients) can send actions and see consistent state/P&L over 5 simulated minutes.

### Phase 2: Realtime Multiplayer + Resources
- FastAPI/Starlette WS gateway + per-match rooms.
- Client action sending + server broadcast of state deltas (T/R, bars, equity, orders, resources).
- IP system (regen + P&L grants) + basic spend.
- Sabotage + Peek implementation (server-mutated, victim notifications).
- Resource UI sync.

See docs/cursor-tasks/TASK_MANIFEST.md for the canonical 8 tasks (Phase 2: 003 resources/sabotage, 004, 005).

**Deliverable**: Real 1v1 over WS with contested tempo, vision unlocks, and sabotage working deterministically.

### Phase 3: Frontend MVP + Polish
- React + TS + TradingView Lightweight Charts (streaming updates).
- Panels: Charts (multi-instrument), Orders, TB/IP bars, Notifications, Chat (text first).
- Match lobby / quickplay (in-memory matchmaking).
- Basic replay scrubber (post-match log replay).

See docs/cursor-tasks/TASK_MANIFEST.md for the canonical 8 tasks (Phase 3: 007 frontend).

**Deliverable**: Playable browser 1v1 with live updating charts, resource controls, and sabotage feedback.

### Phase 4: Voice, Anti-Cheat Hardening, Replays
- Voice: WebRTC signaling over WS or 3rd-party.
- Full private arena selection + normalization enforcement.
- Post-match replay system (full visibility or log replay).
- Basic auth / persistence (users, match history).

### Phase 5: Scale & Polish (Post-MVP)
- Redis pub/sub + queues for matchmaking.
- Multi-server / room affinity.
- Tournaments, spectator mode, more arenas.
- Intraday bars (optional).
- Production deployment, monitoring, testing harness (latency simulation, determinism checks).

**Timeline Estimate (rough, solo or small team)**:
- Phase 1: 1-2 weeks
- Phase 2: 1-2 weeks
- Phase 3: 1-2 weeks
- Phase 4: 1 week
- Total MVP: ~4-7 weeks focused.

## Open Questions & Risks (Consolidated)

**High Priority (resolve before or during Phase 1-2)**:
1. **Clock & Sync Details**
   - Preferred internal tick rate vs. wall time?
   - Broadcast frequency (fixed vs. event-driven)?
   - Client-side prediction level for own actions (orders, TB) to hide latency, or pure server-follow?
- **Determinism harness (new from 5m cycle sub)**: GGPO/Photon/Bevy-inspired synctest (multi-engine identical actions + checksum match), lag injection for TB contention (Pause/FF races), periodic Decimal state hashes, verify_replay(arena_id + sorted log) for post-match audit. Python: Decimal for equity/P&L/TB, stable SHA (sorted keys, quantize), snapshots for reconnect. Integrate early in 001/005 tests + anti-cheat-notes. See harness sub for pseudocode/strategies/2026 context (Quantum replays, DST). Ties OQ "How to prove determinism... lag simulation on clock contention?"

2. **Data / Arena Details**
   - Exact storage (full OHLC arrays vs. returns-only + on-demand indicators)?
   - Arena selection algorithm (random balanced, MMR-weighted, manual curation)?
   - Volume / extra fields handling in normalized data?

3. **Voice**
   - WebRTC self-hosted (STUN/TURN) vs. provider (Twilio/Agora) for reliability?
   - Priority: In-app voice vs. easy Discord integration fallback?
   - Recording / post-match voice log opt-in?

4. **Replays & Persistence**
   - Format: Event log + arena ID (for exact re-sim) vs. full state snapshots?
   - Storage: Postgres, files, object store?

5. **Anti-Cheat & Fairness Validation**
   - How to prove determinism across runs/players?
   - Testing strategy for lag simulation on clock contention?
   - Client reconnect mid-match catch-up (full snapshot + missed deltas)?

**Medium / Later**:
- Exact order model fidelity (close-only vs. high/low triggers within bar).
- IP economy tuning (regen rates, P&L % conversion, cap).
- Sabotage visibility / counters (e.g. "purge" ability?).
- UI chart efficiency (delta updates vs. windowed data).
- Scaling edge cases: Room migration, spectator mode, high concurrency.
- Stack hard constraints (any reason not Python backend?).
- Future: Intraday bars, options, real-money elements (legal).

**Risks & Pitfalls** (from architecture research):
- **Desync**: Mitigate with fully deterministic sim + periodic snapshots + good reconnect logic.
- **Voice NAT / latency**: Have fallback provider ready; test early.
- **Data staleness / gaps**: Script robust cleaning; use consistent source.
- **Cheating via external knowledge**: Normalization + private arenas + generic labels are primary; add mystery slice selection.
- **Performance (Python GIL)**: Fine for MVP 1v1; use async or separate processes per room early.
- **Over-engineering**: Stick to in-memory MVP; add Redis only when needed.
- **UX of contested time**: Make TB influence very visible and satisfying; tune costs so it's strategic not frustrating.

## Alignment with Existing Cursor Tasks
See docs/cursor-tasks/TASK_MANIFEST.md

This document + the Architecture Overview + Mechanics Spec + GDD form a complete design package ready for implementation agents (Cursor or otherwise).

**Next Steps Recommendation**: Review architecture + this doc. Start per docs/cursor-tasks/TASK_MANIFEST.md (e.g. 001/006 data+anti-cheat + 002 time in parallel). Use Cursor Agent on one task at a time with full spec context open. See manifest for full mapping.

**Recent Updates (10m self-check + prior 15m)**: 
- Architecture deepened with detailed LW ReplayController (pseudocode, logical sync, overlays, deltas, Mermaid, React patterns, pitfalls - see arch §5.1; from LW subs). Boosts task-007 handoff.
- GDD §8 Social/Psych enriched with FXR "mental warfare" quotes, specific sabo/TB bluff examples, VoicePanel integration, WebRTC details (from voice sub).
- Handoff sustains All hold (8/8, 35 TASK_MANIFEST refs, 0 legacy, verifs in scratch).
- Roadmap open Qs remain prioritized (anti-cheat, desync, voice NAT, etc.); recent research addresses some (determinism in arch notes, psych in GDD).
- Background sub spawned for open Qs consolidation/prioritize with latest.
See RESEARCH_STATUS.md for full logs/subs. Package ready; continue per manifest.


**Consolidated Open Questions (from background sub 019f0593-3c05-7c51-89f8-292ac2cf7e51, 2026-06-26)**:
Version 0.2 (post deepens: arch LW ReplayController §5.1, GDD voice psych §8, anti-cheat notes, STATUS subs/voice/LW/anti, tasks high readiness).

Recent deepens equip: LW controller (ReplayController hook, scaled timer by R, logical master/slave, markers/priceLines/equity, WS deltas, pitfalls); voice psych (FXR "mental warfare" quotes + sabo/TB bluff exs like "Nice SLs... or were they?", "I'm holding pause—you're wasting IP"; VoicePanel + indicators); anti sub (logging/re-sim pseudocode/harness/GGPO/Photon); All hold verifs (8/8, 30+ MANIFEST refs).

**Tier 1 Critical (Phase 0-2; 001/002/005/006 core det/sim/fairness)**:
1. Determinism harness/logging/re-sim/hashes (anti sub): Action logging (server ts + sim T + arena_id); exact re-sim from log+arena (verify -> state_hash/equity); periodic checksums (Decimal for FP + arena hash); tests (bit-identical, fuzz, lag sim on contention). Persist log+arena.
2. Shared clock/TB contention edges + UI (fractional T, simul; Pause=0 override, R=max(FF) payers consume; who-influencing vis; client optimistic+lerp/snap; clear contested UI). (Roadmap #1; arch #7; mech; STATUS 005.)
3. Data/arena format + pipeline (OHLC vs returns+volume; selection/anonymization/prep; mystery offsets; P[0]=100 norm + generic labels). (Roadmap #2; arch #3.)
4. Reconnect mid-match: Snapshot + missed deltas/bars. (Roadmap #5; arch #8.)

**Tier 2 High (Phase 1-3; 003/004/005/007)**:
- Order fidelity/fills/priority/sizing (close-only vs H/L; sim prio; base spread). (mech #6; STATUS 004/005.)
- IP economy (regen +0.5/s +10% realized P&L; unrealized/neg?; cap; burst). (mech #3.)
- Sabo vis/gran/counters (always notify; instr-specific? purge?). (mech #4.)
- Client pred/optimism + R smoothing (conservative; LW). (arch #2.)
- Tick/broadcast rate (10-20Hz or on change). (arch #1.)
- LW specifics (client scrub action?; lerp R?; Current-T indicator?; equity sep pane?; overlays rebuild; sync loops). (arch LW open + §5; scratch/sub_lw; task-007.)
- Arena prep/selection (Tier 1 overlap).

**Tier 3 Medium-Later (Phase 3-4+; 007/008/replays/scale)**:
- Voice (WebRTC self STUN/TURN vs provider; NAT test/cross-net; WS sig reuse; <150ms; psych UX/trash/bluffs per FXR + exs tied to sabo/TB; fallback; text polish + indicators; recording opt-in deferred). (Roadmap #3; arch #4; GDD §8; STATUS voice + FXR; task-008.)
- Replays/persistence (event log + arena re-sim vs snapshots/video/scrubber; storage; post full vis). (Roadmap #4; arch #5.)
- Multi-server (Redis vs dedicated; mig; spectator). (arch #6.)
- Precise tuning (rates/costs/durs/spreads/IP). (mech #2.)
- Post-match (tiebreakers/surrender/reveal). (mech #8.)
- Future: Intraday; monetization; stack.

**Risks/Pitfalls (reiterated + LW)**: Desync (det + snapshots + reconnect + lag sim test); Voice NAT/quality (fallback + early test); Data gaps (robust clean); External cheat (norm+private+generic+mystery primary); GIL (async/proc-per-room); Over-eng (in-mem MVP); Contested UX (visible TB + psych feedback). LW: update() deltas only; master/slave; full marker replace; ref leaks; no extrap; server T truth.

**MVP Defaults (for Cursor agents)**: Bar-at-T + units (100 start); exact TB from mech-spec; server truth (no heavy pred); text-first + WebRTC; P[0]=100 + generic; in-mem single-proc. Agents: Paste task + full pkg (GDD/mech/arch w/ deepens) + STATUS (subs/excerpts + carried) + MANIFEST + anti-notes + scratch subs. Strict spec/MVP defaults. Update open Qs/STATUS on resolutions.

**Tier 1 early prototypes + LW controller from arch for 007 + psych exs for 008**. High value for handoff (equipped, prioritized, momentum from All hold).

See full in scratch/sub_roadmap_openqs_20260626.txt + STATUS for transcripts/excerpts.

