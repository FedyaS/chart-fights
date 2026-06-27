# Cursor Agent Task: Implement Time Model + Tempo Bar (Shared Contested Clock)

**Context**: Part of Chart-Fights 1v1 historical chart PvP. See:
- docs/design/GDD.md
- docs/design/game-mechanics-spec.md (authoritative detailed spec, sections 1 and 2)
- docs/research/data-sources-initial.md

**Goal**: Build the core time simulation engine and Tempo Bar resource system exactly as specified. This is the foundation for pacing, interaction, and MOBA-like contention.

## Requirements (directly from spec)
- Core Rule: 1 real second = 1 simulated trading day (advance one daily bar).
- Fixed 5 real-minute matches (300 real seconds).
- Shared Market Clock `T` (simulated day index, integer + fractional).
- Clock rate `R` (days per real second), starts at 1.0.
- `R` is **globally shared and contested**.
- Tempo Bar (TB): 0-100 resource.
  - Base recharge +1.0 / real sec.
  - Pause recharge bonus +4.0/s when holding pause.
  - Consumption rates: Pause (0), FFx2 (2/s), FFx3 (5/s), FFx5 (12/s).
- Contention rules:
  - Any Pause forces R=0.
  - Multiple FF: R = max of active.
  - All active payers consume.
- UI/Feedback: Show current R, who is influencing, visual "Market Speed".
- Bar advances drive: new bars revealed, P&L marking, order triggers, events.

**MVP scope**: Deterministic simulation. No personal views yet. Skip non-trading days or interpolate at data layer.

**Non-goals (this task)**: IP resource, sabotage, full UI, data fetching (assume pre-loaded bars).

## Acceptance Criteria
1. Simulation loop: Given a list of pre-normalized daily bars + start T, advances T and R in real-time according to TB actions.
2. Tempo Bar class/system with recharge, consume, and influence logic.
3. Contention resolver for shared R (Pause overrides, max FF wins).
4. Clean API for higher layers: get_current_T(), get_R(), apply_bar(bar), is_match_over().
5. Tests: Determinism (same inputs → same sequence for "both players"), contention cases, exact consumption math.
6. No production code outside the agreed modules. Clear comments referencing spec sections.

## Suggested Structure
- `sim/time_engine.py` (or equivalent): class SharedClock, TempoBar.
- Config for rates, consumption table, match duration.
- Event hooks or callbacks when new bar arrives or R changes.
- Simple CLI test harness or unit tests that simulate 300s with players issuing FF/pause.

## Cursor Agent Prompt (copy-paste ready)
"Implement the Time Model and Tempo Bar exactly as described in docs/cursor-tasks/task-002-time-and-tempo.md and the linked game-mechanics-spec.md sections 1 and 2.

Create a deterministic shared clock simulation where 1 real second advances 1 trading day by default. Implement the contested R rate controlled by Tempo Bar (TB) resource with the exact recharge and consumption rates given. Support Pause forcing R=0 and multiple FF taking the max R while all pay.

Make it server-authoritative and deterministic so two players on the same bar sequence stay in sync. Include tests for contention rules and exact math. Reference the spec for all numbers and rules.

Do not implement orders, IP, sabotage, or UI yet — only time + tempo. Keep it clean and well-documented."

## Follow-ups
- task-003 will cover IP + sabotage once this is solid.
- Data pipeline task (task-001) provides the bars this consumes.

**Priority**: Critical foundation.
**Size**: Medium (core engine + tests).

Start by reading the spec and this task. Propose minimal module layout before coding.

## Additional Research Synthesis & Handoff Notes (bg sub 019f05f4-af39... 2026-06-26)
Ready-to-paste design notes for task-002 + architecture-overview.md (clock/realtime/LW sections). Synthesized from specs (mech §§1-2), arch, det-notes, LW subs, GGPO/Photon patterns. Exact TB rules preserved.

**Core Model (spec-aligned)**: 1 real second = 1 simulated trading day (base R=1.0). Fixed 5min (300 real-s) matches. Shared T (integer + fractional day index, starts 0). R (days/real-s) is globally contested via TB only. All bars, P&L marking, order triggers, and events driven by shared T. Visuals use generic "Sim Day NNN" (private arenas + P[0]=100 normalization).

**Tempo Bar (TB) Rules (exact from spec)**:
- Capacity 0-100.
- Base recharge: +1.0 per real second.
- Pause bonus: +4.0/s while holding Pause (and R forced ≤0).
- Consumption (per real second while actively held): Pause=0 (denies opponent + enables own bonus), FFx2 (R=2)=2.0/s, FFx3 (R=3)=5.0/s, FFx5 (R=5)=12.0/s.
- Contention (server resolver): Any active Pause forces R=0 (override). Multiple FF: R = max(active levels). All payers consume their rate. No controls → R=1.0. Broadcast R + (optional anon) influencers.

**Server-Authoritative Realtime (best practice)**: Clients send actions only ("start TB influence level=X", "stop"). Server owns wall-time-aligned advance (monotonic/perf_counter for 1s=1day base), T += real_delta * R, TB recharge/consumption, contention recompute, and broadcasts (T, R, deltas). Aligns with 2026 patterns from Photon Quantum (inputs-only + referee sims) and authoritative WS servers. No client prediction for contested global state (pure follow + conservative smoothing); optimistic local for own actions only (reconcile on deltas).

**GGPO/Lockstep Adaptation for Contended Resources (Tempo Bar)**: Not full P2P lockstep (variable R makes strict frames awkward; arch notes overkill). Use "inputs-only" + server referee model (GGPO rollback concepts + Photon replay validation + Bevy GGRS synctest). Log every action with (real_ts, sim_t, player, type, payload). Server resolves contention deterministically at receipt/advance points. Post-match or on-demand: `verify_replay(arena_id, sorted_log)` → fresh engine + replay actions → assert equity/hash match. Periodic state checksums (during match) for desync detection.

**Tick Rates & Advance**:
- Wall-time base for pacing (1 real-s = 1 day at R=1).
- Internal: event-driven on actions + periodic wall advance (or fixed 20-60Hz sim ticks).
- Broadcast: ~10-20Hz or on significant R/T/bar/event change (deltas preferred).
- Client LW: R-scaled timer or direct WS T follow (see below).

**Contention Edge Cases + Lag Sim**:
- Pause force R=0: Immediate override; bonus applies only to holders.
- Multi-FF: R=max; exact consumption integrated over real_delta for each payer (e.g., two FFx2 payers each deduct 2*delta).
- Simult. Pause+FF: Pause wins (per spec "any active Pause").
- Late actions (lag): Apply from server receive time (or validated sim_t window); no retroactive "steal" of past R. Late Pause can instantly kill opponent FF burst from now forward.
- Lag sim test harness: Inject delays/reorders on action queue; assert identical final state across engines.
- Fractional T: Drives smooth advance; integer crossings trigger discrete bar apply. (Spec open: partial-bar interp for orders?)

**Determinism for Variable-Speed Replay**:
- Use `decimal.Decimal` (quantize consistently, e.g. 4 decimals) for T, R, TB, equity, consumption. Avoid float.
- Arena content_hash (normalized slice) + action log seed identical replay.
- Synctest harness (GGPO/Photon-inspired): N parallel engines fed identical action seq (or fuzzed); periodic checksums + final equity must match bitwise.
- `compute_state_hash()`: Stable string of sorted key state (T, R, equities, positions, TB levels, active influencers) → SHA256.
- 2026-relevant for 1s=1day accelerated historical: Parquet (pyarrow/snappy or zstd, partitioned) for fast load of long arenas + exact re-sim. LW Charts v5+ streaming supports it perfectly. ChartChamps (acq. ~2026) + FXR Battles validate historical same-segment replay + voice psych on accelerated timelines. Photon 2025/6 replay/checksum fixes + GGPO rollback concepts adapt cleanly to bar-index "frames."

**LW Charts timeScale + ReplayController R-Scaled Patterns (from sub 019f0577/019f058c + official realtime-updates + time-scale)**:
- Preload: `series.setData(initialNormBars); chart.timeScale().fitContent();` (only init).
- Streaming/replay advance: `series.update(bar);` (append or replace latest; "do not recommend setData for updates").
- Shared T/scrub/FF/pause: Logical ranges (fractional OK): `{from, to}` indices. `timeScale.subscribeVisibleLogicalRangeChange(range => slave.setVisibleLogicalRange(range));` (master/slave to prevent loops). Server T drives: `master.timeScale().setVisibleLogicalRange({from: currentT-w, to: currentT+o});`.
- ReplayController (custom hook, no built-in): 
  ```ts
  // useEffect / custom hook
  const baseMs = 1000; // 1s real ~1 bar @ R=1
  const intervalMs = Math.max(50, baseMs / R);
  const id = setInterval(() => {
    // follow server T (preferred) or local advance
    master.timeScale().setVisibleLogicalRange(aroundCurrentT);
    // series.update if client-driven preview; rebuild markers/priceLines
  }, intervalMs);
  if (R <= 0) { clearInterval(id); /* freeze */ }
  ```
- Overlays: `createSeriesMarkers(series, markersArray)` or `setMarkers` (full replace on change); `series.createPriceLine({price, ...}); pl.applyOptions/removePriceLine`; parallel Line/Area equity series `.update({time: T, value: equity})`.
- WS deltas (from 005): BarDelta → update(); ResourceDelta {T, R, TB_level}; OrderDelta (rebuild markers/priceLines); EquityDelta; EventDelta (sabo notifs).
- React: `useRef` for chart/series + `useEffect(() => { const c = createChart(...); ... return () => c.remove(); }, []);`. Strict cleanup (unsub timeScale, clear timers).

**Pitfalls (list for append)**:
- Float nondeterminism → force Decimal everywhere critical; quantize + sorted structures for hashes.
- Action ordering/timing races (simul Pause+FF, multi-FF) → server receive ts + explicit rules; document + fuzz test.
- LW sync loops/jumps: master/slave + guards; never setData on stream (use update); no extrapolation on ranges.
- Lag + variable R UX: Late TB influence feels unfair → clear "Market Speed" feedback + conservative client (no heavy pred for global clock). Test lag sim exhaustively.
- Reconnect mid-contention: Snapshot must include active influencers + current R/TB + recent log.
- Replay bloat/perf: Log compact (ts + minimal payload); periodic snapshots; re-sim only on audit.
- Non-trading days + fractional T: Consistent skip/interp in data layer (task-006); handle in logical ranges.
- 2026 note: Parquet + LW v5+ + authoritative referee (Photon-style) makes 1s=1day historical replay highly deterministic and scalable for post-match scrub/spectators.
- TB exact math: Integrate consumption over real_delta (not discrete ticks) to avoid drift with variable R.

**Recs/Pseudocode Sketches** (see full in anti-cheat-determinism-design-notes.md + sub_lw...):
- SharedClock/TempoBarResolver class with `_recompute_R()` (Pause check first → R=0 else max FF; track active_influences map; integrate costs in `advance(real_delta)`).
- `SimulationEngine.advance_sim(real_delta)` + `receive_action(...)` + `verify_replay(arena_id, log)`.
- Client: Server T truth; ReplayController follows deltas or scales local timer; lerp small diffs only.

**Handoff Tie-in**: Extends task-002 ACs (determinism/contention tests) + arch §2/§4/§5 (realtime sync, sim engine, LW). Add determinism harness + lag/contention tests early (task-001/005). 2026 patterns (GGPO/Photon referee replays, Parquet arenas, LW logical + update for accelerated historical, FXR/ChartChamps validation) directly support variable-speed shared clock without external variance.

(Full sub output integrated here for Cursor agent. Cross-ref STATUS for more excerpts. Update arch + STATUS when sub2 done.)

## Deep Research Resolutions (sibling worker, 2026-06-26)

This section resolves the **Tempo Bar / shared-clock open questions** from `roadmap-and-open-questions.md` (Tier 1 #2) and `game-mechanics-spec.md §1` ("Open"). All resolutions preserve the exact TB rates (base recharge +1.0/s, pause bonus +4.0/s, consumption Pause=0 / FFx2=2.0/s / FFx3=5.0/s / FFx5=12.0/s) and the contention rules (Pause→R=0 override; multi-FF R=max with all payers paying; default R=1.0). These are concrete starting points, tunable via playtest.

### OQ-T1: Fractional `T` handling — continuous advance, discrete bar application
**Resolution:** `T` is a continuous `Decimal` accumulator (`T += R * real_delta`, quantized to a fixed precision such as 1e-6 days). Bars are **applied only on integer crossings** of `T`. The sim is event-driven on integer boundaries, not on the fractional value:
- Maintain `last_applied_day = floor(T)` before advance.
- After `advance(real_delta)`, compute `new_day = floor(T)`. For each integer `d` in `(last_applied_day, new_day]`, **apply bar `d` in ascending order** (reveal bar, mark-to-market, evaluate order triggers, fire events). This guarantees that even a large FFx5 jump that crosses several integers in one tick applies every intermediate bar in sequence — no skipped bars, fully deterministic.
- The fractional remainder of `T` is used **only** for smooth UI interpolation (chart logical range, clock animation) and is **never** used to fill orders. See OQ-T7 below.

```python
def advance(self, real_delta: Decimal) -> list[int]:
    self._recompute_R()                      # contention first (Pause override / max FF)
    self._apply_tb_recharge_and_consume(real_delta)
    prev_day = int(self.T)                    # floor
    self.T = (self.T + self.R * real_delta).quantize(Q_T)
    new_day = min(int(self.T), self.last_bar_index)   # clamp to data length
    return list(range(prev_day + 1, new_day + 1))     # bars to apply, in order
```

### OQ-T2: Simultaneous Pause + FF — Pause wins, deterministically, by rule (not by arrival time)
**Resolution:** Per spec, **any active Pause forces R=0** regardless of how many FF influences are active. This is resolved by *state*, not by message arrival order, so it is inherently deterministic and race-free: every tick, `_recompute_R()` first checks "is at least one Pause influence currently active?" → if yes, `R=0`; else `R = max(active FF levels)`; else `R=1.0`.
- **Cost accounting during a Pause that overrides FF:** the FF payer(s) keep paying their consumption only while they *hold* the FF input. Recommended rule (clearest for players + matches spec "all payers consume"): an FF influence that is being overridden by a Pause is **suspended (cost paused) while R is forced to 0**, because the FF is delivering no speed. Pause holders simultaneously receive the +4.0/s recharge bonus. This makes Pause a pure tempo-denial tool (cost 0, denies the opponent's FF value, and refills your own bar) exactly as the spec intends, and avoids the unfair outcome of an FF payer bleeding TB for zero benefit. Document this explicitly; alternative (keep charging overridden FF) is harsher and should only be used if playtests show pause-spam dominance.

### OQ-T3: Multi-FF `R = max(R)` with all payers consuming
**Resolution:** When two players both push FF (e.g. P1 FFx2, P2 FFx5), the shared `R = max = 5`, and **each payer consumes their own chosen tier's rate** (P1 pays 2.0/s, P2 pays 12.0/s) — *not* the max rate for everyone. Integrate cost continuously over `real_delta` per payer (`tb[p] -= rate[level_p] * real_delta`) to avoid drift under variable tick sizes. A player whose TB hits 0 has their influence auto-dropped that tick; `R` is then recomputed from remaining payers. Two players choosing the *same* tier both pay full rate (no split discount) — this keeps "fighting for speed" expensive and intentional (MOBA contested-objective parallel).

### OQ-T4: Who-is-influencing visibility — show the aggregate state, anonymize the attribution (MVP)
**Resolution:** Always broadcast the **resolved market state** to both players: `"Market Speed: 3.0x"` / `"PAUSED"` / `"1.0x"`, plus a boolean `contested` flag when ≥2 influences are active (e.g. `"3.0x (contested)"`). For MVP, **anonymize who is influencing** (do not label "opponent is pausing"). Rationale: hidden attribution preserves the bluff/mind-game layer (the opponent must read voice/chat tells to know if *you* are the one pausing, per GDD §15 "I'm holding pause — you're wasting IP"). Always show the player **their own** active influence and live TB drain unambiguously. (A post-MVP toggle could reveal attribution for a more "transparent" mode; keep the contested flag either way.)

### OQ-T5: Client optimistic vs server-follow for own TB actions
**Resolution:** **Server is authoritative for `R`, `T`, and all TB balances.** Hybrid prediction:
- **Own TB drain & own influence state:** optimistic — the instant the player presses Pause/FFx2/3/5, the client locally starts draining its own TB bar and shows its own influence as active (hides input latency, feels responsive). Reconcile against the server `ResourceDelta` (snap own TB to server value when it arrives; small diffs lerp, large diffs hard-snap).
- **Resolved `R` and `T` (shared/contested):** pure server-follow, **no client prediction**. The client never predicts the *outcome* of contention (it can't know the opponent's simultaneous inputs). It applies server `R`/`T` with conservative smoothing only. This matches the netcode-sub recommendation (authoritative referee à la Photon Quantum; optimistic local only for inputs you own).
- This split is the safe default: you can over-predict your *intent* (cheap to correct) but never the *contested result* (would cause visible desync/rubber-banding of the whole market).

### OQ-T6: "Market Speed" feedback (UX)
**Resolution:** Persistent HUD element driven by `ResourceDelta {T, R, TB_self, contested}`:
- Large speed readout: `1.0x` / `2.0x` / `3.0x` / `5.0x` / `PAUSED`, color-coded (neutral / accelerating / frozen).
- TB bar with live drain animation while you hold an influence and recharge "sparkle" while idle/pausing; show your consumption rate inline (e.g. `-5.0/s`) and recharge rate (`+4.0/s` while pausing).
- `contested` → subtle pulse/secondary marker so players feel the tug-of-war even without attribution.
- On `R` change, fire a brief toast/sound ("Market accelerating ×3", "Market frozen") for the urgency/"alive chart" feel (GDD §14).

### OQ-T7: Max `R` and partial-bar interpolation for orders
**Resolution (max R):** Cap the *chooseable* FF tiers at the spec's set: **5 is the maximum `R`** (FFx5). Do not add higher tiers in MVP — FFx5 already drains a full TB in ~8s and is the high-risk burst ceiling. (Keep a single config constant `MAX_R = 5` so playtest can tune.)
**Resolution (partial-bar interpolation):** **No intra-bar interpolation for order execution in MVP.** Orders are evaluated only at integer-`T` bar applications (see OQ-T1 and task-004's fill model). Fractional `T` advances the chart visually but does **not** create synthetic mid-bar prices that could trigger fills — doing so would (a) break determinism across variable `R`, and (b) let a player "scrub" a fill at a price that never existed in the normalized slice. The daily bar is the atomic execution unit. (Intraday/LTF bars are an explicit post-MVP fidelity upgrade, mirroring the "bar magnifier" pattern — see task-004 sources.)

### Determinism note tying T to fills
Because bars apply on integer crossings **in ascending order regardless of `R`**, the *sequence* of bars (and therefore the sequence of order triggers and P&L marks) is identical for any path of pause/FF inputs that ends at the same `T`. Only the *real-time pacing* differs. This is the property the replay/synctest harness asserts: `verify_replay(arena_id, sorted_action_log)` must reproduce the identical bar-application order and final equity hash. Quantize `T`, `R`, and all TB balances with `Decimal` to keep this bit-exact.

**Sources (web, 2026):**
- Intra-bar fill fidelity & "process every sub-step in order" rationale (bar magnifier): https://pynecore.org/docs/advanced/bar-magnifier/
- Same-bar vs next-bar execution modes & exit-first ordering (engine design): https://github.com/ml4t/backtest
- MOBA contested-objective / diminishing-return economy framing (informs "fighting over the clock" cost design): https://frequently-asking-questions.com/2026/04/04/the-5-minute-surrender-fallacy/
