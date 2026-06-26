# Anti-Cheat and Determinism Verification Design Notes for Chart-Fights

**Version**: 1.0 (2026-06-26)  
**Purpose**: Targeted research synthesis + actionable design recommendations + pseudocode for server-authoritative deterministic replay simulation in Chart-Fights (normalized historical daily bars, P[0]=100, generic labels, 5min fixed real-time matches, contested Tempo Bar clock (TB), server FastAPI sim).  

Focuses directly on the 7 requested areas. Draws from:
- Existing project docs (GDD.md, game-mechanics-spec.md, architecture-overview.md, roadmap-and-open-questions.md, task-001, RESEARCH_STATUS.md, chart-fights-research-notes.md).
- Game dev patterns (GGPO rollback, Photon Quantum deterministic sim, lockstep, GGRS/Bevy desync tools).
- Similar products (ChartChamps, FXR Battles/fxreplay, TraderFi, Hedgd, Trade Bots).
- Broader techniques (server referee re-sim, state checksums, input logging, lag comp/rollback).
- Tailored to chart sim specifics: bar sequences as deterministic "world", actions (orders + TB/IP + sabotage) at real/sim time, private arenas.

**Key Principle (project-aligned)**: Server owns canonical simulation. Clients send *actions only*. Determinism + private normalized arenas + full logs = core anti-cheat. External knowledge (real dates/symbols) neutralized. Contested shared clock resolved server-side.

**Citations/Links** (web results from targeted research; see tool logs for full queries):
- GGPO: https://www.ggpo.net/ , https://github.com/pond3r/ggpo (rollback + determinism requirement) [web:1][web:3 from initial searches].
- Photon Quantum: https://www.photonengine.com/quantum (inputs-only, deterministic rollback, replay validation + server referee sims for anti-cheat, built-in replays/spectating) [web:33][web:13].
- Bevy GGRS desync tools: https://johanhelsing.studio/posts/extreme-bevy-desync-detection/ (synctest sessions, component checksums) [web:39].
- Lockstep determinism paper context + checksums: various Unity/Reddit/GG discussions [web:45 etc.].
- Similar products: ChartChamps (random historical, replays, Elo) chartchamps.com [web:53][web:155]; FXR Battles (historical 1v1 + voice) fxreplay.com [web:55]; TraderFi historical replay multiplayer.
- Authoritative server + replay verification patterns: Photon docs, general server-authoritative anti-cheat analyses [web:14][web:18].
- Lag comp/rewind: Unity Netcode server rewind, Gabriel Gambetta series, Mirror [web:4][web:7].

All recommendations prioritize MVP 1v1, FastAPI + in-memory rooms, extensibility (Redis, spectators, tournaments).

## 1. Action + Input Logging + Exact Re-Simulation on Server for Verification

**Pattern**: Clients transmit minimal actions (e.g., "start_TB_influence level=3", "place_order instr=0 type=market size=10", "ip_spend ability=delete_sl"). Server timestamps (server receive wall time + current sim T), validates, applies to canonical state, logs. Post-match or on-demand: reload arena by ID + replay action sequence → identical final equity/P&L/positions.

**Concrete from research**:
- Photon Quantum: "Only inputs are exchanged... replay validation or server referee simulations which is the most effective anti-cheat measure." Full match replays to backend endpoint. [Photon docs]
- GGPO/P2P: Deterministic engine + input exchange; referee peer or spectator can re-sim. Issues with fake inputs addressed by input checksums.
- ChartChamps/FXR: Match replays for review + learning (historical segment same for fairness).
- Trading sims (e.g., backtesters): Action logs enable exact paper execution replay.

**Project Fit (5min fixed, FastAPI)**: Server drives by real wall time (1s real ≈ base R=1 day). Log compact sequence. Arena pre-fetched (Parquet/in-mem) → no variance.

**Pitfalls**:
- Non-deterministic apply order (simultaneous actions + bar cross + sabotage).
- Timestamp drift (use server monotonic time).
- Floating point in P&L (use decimal.Decimal or careful rounding to 2-4 decimals for equity).
- Missing reconnect logs.

**Testing Strategies**:
- Unit: replay_log(arena_id, actions) == expected_final_state (bitwise or hash).
- Harness: Two "virtual players" issue identical action seqs → assert P&L/positions identical across runs/machines.
- Fuzz: Random valid action sequences over 300s; re-sim multiple times.
- Lag sim: Inject delays on action queue; verify same outcome.

**Pseudocode (Python/FastAPI style, for sim/time_engine.py + match_service)**:

```python
from decimal import Decimal
import time
from typing import List, Dict, Any
from dataclasses import dataclass
import hashlib

@dataclass
class Action:
    real_ts: float          # server wall time (monotonic)
    sim_t: float            # T at receipt/apply decision
    player_id: str
    type: str               # "tb_influence", "order", "ip_spend", ...
    payload: Dict[str, Any]

class MatchLog:
    arena_id: str
    start_real_ts: float
    actions: List[Action] = []
    # Optional: periodic state snapshots for quick verification

class SimulationEngine:
    def __init__(self, arena: List[Dict], config: dict):  # normalized bars
        self.arena = arena  # e.g. [{"t":0, "instr0": 100.0, ...}, ...] or returns
        self.T = 0.0
        self.R = 1.0
        # ... TB state, positions, orders, etc.
        self.log: List[Action] = []
        self.match_start = time.perf_counter()

    def receive_action(self, player_id: str, action_type: str, payload: dict):
        now = time.perf_counter()
        current_sim_t = self.get_current_T()  # based on elapsed * R
        act = Action(now, current_sim_t, player_id, action_type, payload)
        self.log.append(act)
        self._apply_action(act)  # immediate or queued per rules

    def _apply_action(self, act: Action):
        if act.type == "tb_influence":
            self._resolve_tempo_contention(act)
        elif act.type == "order":
            self._queue_or_exec_order(act)
        # ... sabotage etc. (server-mutated)

    def advance_sim(self, real_delta: float):
        # Called in loop or on timer
        self.T += real_delta * self.R
        self._process_bar_crossings()  # mark P&L, exec limits, etc.
        self._resolve_resources(real_delta)
        # Broadcast deltas

    def verify_replay(self, arena_id: str, action_log: List[Action]) -> Dict:
        """Exact re-simulation for post-match audit / AC."""
        engine = SimulationEngine(load_arena(arena_id), config)
        for act in sorted(action_log, key=lambda a: a.real_ts):  # or by intended sim_t
            engine._apply_action(act)  # or feed through receive
            engine.advance_sim(0)  # or step to act's ts if needed
        return {
            "final_equity_p1": engine.player_states[0].equity,
            "final_equity_p2": ...,
            "state_hash": engine.compute_state_hash(),
            # Or full final state
        }

    def compute_state_hash(self) -> str:
        # Stable serialization of critical state
        data = f"{self.T}|{self.R}|{sorted_positions}|{equities}"
        return hashlib.sha256(data.encode()).hexdigest()
```

**Recommendations**:
- Persist log + arena_id + final reported score in Postgres (or file for MVP).
- On match end: auto-call verify_replay; flag mismatches.
- For spectators: serve log + arena metadata; client or server re-sim for scrubber (see #7).
- Extend task-001: add logging to sim engine (task-002/005).

## 2. Hashing or Checksums of Arena Data + Action Sequence to Prove Identical Outcome

**Pattern**: Hash initial arena (normalized slice ID + content hash) + running or periodic state hash (key fields: T, player equities, positions, open orders summary, TB/IP levels). Or hash entire action sequence + arena. Mismatch proves divergence/cheat attempt. Exchange periodic checksums during match (if P2P elements) or on reconnect.

**Concrete**:
- Bevy GGRS / GGPO-inspired: `checksum_component` (e.g. hash Transform bits); synctest runs sim, compares on rollback; P2P desync detection with interval checksums. Use stable hasher (avoid DefaultHasher platform variance); bit-cast floats. [johanhelsing post]
- Lockstep papers: Game state checksum (fast hash) every 20 turns; on mismatch resync snapshot. Must handle permutation (sorted data). [various]
- Photon: Implicit via deterministic inputs-only + replays.
- SHA256 discussions: Hash state as "truth" to match. [Reddit anti-cheat with SHA]
- For arenas: Hash of pre-normalized or normalized bar data (or just arena_id + version + slice hash).

**Project Fit**:
- Arena hash: On load, `hashlib.sha256(pickle.dumps(normalized_bars) or json of returns).hexdigest()`.
- During match: After each bar or every N real-seconds / major events, compute + log + broadcast "state_checksum".
- On verify: Compare re-sim hash to logged.
- Contention proof: Include active TB influencers + R in hash.

**Pseudocode**:

```python
def normalize_and_hash(arena_raw: dict) -> tuple[list, str]:
    normalized = {}
    for instr, prices in arena_raw.items():
        p0 = 100.0
        norm_prices = [p0]
        for ret in compute_returns(prices):
            norm_prices.append(norm_prices[-1] * (1 + ret))
        normalized[instr] = norm_prices
    arena_bytes = json.dumps(normalized, sort_keys=True).encode()
    return normalized, hashlib.sha256(arena_bytes).hexdigest()

def periodic_state_checksum(engine) -> str:
    # Careful with floats: use Decimal or quantize + str
    key = (
        f"T:{engine.T:.6f}|R:{engine.R:.2f}"
        f"|EQ:{engine.p1.equity.quantize(Decimal('0.01'))}"
        f"|POS:{sorted([ (k, v.size) for k,v in engine.positions.items() ])}"
        # + TB levels, IP, order hashes, etc.
    )
    return hashlib.sha256(key.encode()).hexdigest()[:16]  # short for broadcast

# In sim loop or after apply
if (tick % 30 == 0):  # ~every 1- few secs
    cs = engine.periodic_state_checksum()
    log.append(("checksum", engine.get_current_real_ts(), cs))
    broadcast_to_room({"type": "state_cs", "cs": cs, "t": engine.T})
```

**Pitfalls**: Float non-determinism (use Decimal for all P&L/equity/TB calcs; quantize consistently). Order-dependent structures (use sorted lists/dicts). NaN/inf. Versioning hashes (include sim code version or ruleset hash).

**Testing**: Synctest harness: run engine A and B on same log; assert checksums match at every checkpoint. Cross-platform (different Python? but pin env). Fuzz inputs.

## 3. Handling Shared State Contention (like Tempo Bar clock) under Latency

**Pattern**: Server is sole resolver. Clients send influence *start/stop* actions (or continuous "hold" with heartbeats). Server collects active at decision points (bar cross or fixed tick), applies rules exactly (Pause overrides all; R = max(FF) among actives; *all* payers consume). Use server receive timestamps + logical sim time for ordering. Broadcast authoritative R/T immediately.

**Concrete**:
- Project spec (mechanics-spec.md): "Any active Pause forces R=0. Multiple FF: R = max... All paying players pay."
- General: RTS lockstep/contention (shared objectives); MOBA dragon fights (server resolves).
- Latency: Clients experience delayed visibility of opponent's influence. Mitigate with clear UI ("Market Speed influenced by opponent?") or anonymous.
- Photon/rollback: Predict locally (e.g. your TB effect), rollback on authoritative correction.

**Project Fit (TB + shared T)**:
- Real-time wall-driven: `elapsed = now - last; self.T += elapsed * self.R`.
- Contention resolved on *every* advance or on action receipt (recompute R).
- Late actions: Apply at receive time (or intended sim T if validated within window). No "steal" past influence.

**Pseudocode (Tempo resolver in SharedClock)**:

```python
class TempoBarResolver:
    def __init__(self):
        self.active_influences = {}  # player_id -> {"level": 3, "start_ts": ...}
        self.R = 1.0
        self.pause_held = False

    def on_influence(self, player_id: str, level: int | None, is_start: bool, now: float):
        if is_start and level is not None:
            self.active_influences[player_id] = {"level": level, "start": now}
        else:
            self.active_influences.pop(player_id, None)
        self._recompute_R(now)

    def _recompute_R(self, now: float):
        has_pause = any( inf.get("level", 0) <= 0 for inf in self.active_influences.values() )  # or explicit pause flag
        if has_pause:
            self.R = 0.0
            # Bonus recharge logic per spec
        else:
            ff_levels = [inf["level"] for inf in self.active_influences.values() if inf["level"] > 1]
            self.R = max(ff_levels) if ff_levels else 1.0
        # Consumption: integrate over real time since last recompute for each payer
        # Broadcast new R + influencers (or anon)

    def get_consumption_costs(self, real_delta: float) -> Dict[str, float]:
        # Per spec rates: FFx2=2/s etc. Return player -> cost to deduct from TB
        ...
```

**Handling Latency Pitfalls**:
- Contention race: Two players FF close in time → server receive order decides (or max always + both pay). Document + test.
- Client prediction: Optimistic local R (own influence only); lerp/snap to server R on update. Pure follow for global T.
- Reconnect: Send current R + active summary + recent log.

**Recs**: Fixed internal sim ticks (e.g. 20-60Hz) or event-driven on actions + periodic advance. Broadcast R/T + deltas at 10-20Hz or on change. Tune costs per spec (task-002).

## 4. Private Arena Slices + Normalization to Prevent External Knowledge Advantage

**Pattern**: Server exclusively selects/loads "arena" (contiguous historical slice). Clients receive *only* normalized data + generic labels during match. Real symbols/dates = post-match reveal (optional). Mystery/random offsets or variants.

**Concrete**:
- Project: "P[0]=100; % returns only. ... Private arenas + normalization" (task-001, mechanics-spec §10, arch §6).
- ChartChamps: "randomly selected historical data spanning bull, bear and sideways". Replays.
- TraderFi/Trade Bots: Mystery historical + time accel.
- Fog-of-war analogs + private views in RTS/MMORTS.

**Implementation**:
- Pre-curate arenas (regimes, vol profiles) in catalog (DB + Parquet files keyed by ID).
- On match start: server picks (random balanced or curated), loads, normalizes (or pre-normalized), assigns generic names ("Broad Equities", "Tech Index", "EURUSD Pair").
- Serve: Initial window or streaming bars as T advances (normalized closes/OHLC %).
- Anti-leak: No client pre-load of raw; no external API calls; arena_id opaque during play.

**Pseudocode**:

```python
def load_private_arena(arena_id: str) -> dict:
    raw = load_from_parquet_or_db(arena_id)  # internal only
    normalized, h = normalize_and_hash(raw)
    labels = {instr: f"Instrument_{i}" for i, instr in enumerate(raw)}  # or curated generics
    return {"bars": normalized, "labels": labels, "hash": h, "arena_id": arena_id}  # hash for verify

# Match start
arena = load_private_arena(server_pick_id())
broadcast_to_players({
    "type": "match_start",
    "arena_hash": arena["hash"],
    "labels": arena["labels"],
    "initial_bars": arena["bars"][:window],
    # No real symbols/dates
})
```

**Pitfalls**: Incomplete normalization (volume? indicators?). Non-trading day handling (consistent skip/interp). Post-match reveal must be optional.

**Recs**: Implement in data pipeline (task-006) + task-001. Store raw + normalized? Prefer returns-only for compactness. Version arenas.

## 5. Client Prediction vs Pure Follow for Contested Mechanics

**Pattern**: Hybrid. Pure authoritative follow for *shared contested* state (global T, R, bar reveals, sabotage effects, opponent equity visibility if fogged). Optimistic local prediction + reconciliation for *own* actions (orders appear immediately; own TB drains visually; own P&L tentative).

**Concrete**:
- Authoritative servers (Unity/Mirror/Netcode, Photon): Prediction + reconcile (lerp or snap).
- GGPO rollback: Heavy local prediction of remotes + rollback re-sim.
- MMORTS hybrids: Server canon + client prediction "like a pianist playing half a beat ahead".
- For charts: TradingView streaming handles appends well; local optimistic chart updates on own orders.

**Project Fit**:
- Contested (TB clock, shared orders vs. same bars): Pure follow or conservative (e.g. don't assume your FF wins until server confirms R change).
- Own orders: Local queue visible, P&L estimate using current bars; correct on server fill/equity broadcast.
- TB: Local model of *your* TB + tentative R contribution; server authoritative global.

**Pseudocode (client side sketch, React/TS + WS)**:

```ts
// On action send
sendAction({type: 'tb_influence', level: 3, start: true});
// Optimistic
localTB.drain(rate);
tentativeR = computeLocalTentativeR(myInfluence, lastServerR);

// On server broadcast
if (msg.type === 'state_update') {
  serverT = msg.T; serverR = msg.R;
  reconcileTB(msg.resources);
  // For contested: always trust serverR/T for shared clock visuals
  // Lerp charts / equity if small delta; hard snap rare
  applyDeltas(msg);
  if (localOptimisticOrder && msg.fills) reconcileOrders();
}
```

**Recs** (from roadmap open Qs): Favor pure follow for clock contention to avoid frustration. Prediction mainly for UI snappiness on own inputs. Reconcile aggressively. Test with artificial lag.

## 6. Lag Compensation or Rollback for Time-Manip Mechanics

**Pattern**: Server rewind/history buffer for validation. Or timestamped actions applied at logical time. Client rollback for prediction errors. Since bar-based (not high-freq physics), lighter than FPS hitscan rewind.

**Concrete**:
- Lag compensation (Gambetta, Valve, Unity server rewind): Server keeps past states; on late input, rewind to shot time, validate, re-advance.
- Rollback (GGPO/Quantum): Client predicts, rewinds on correction.
- For time manip: Actions have "apply window"; server may "insert" effect at past T if within latency bound (rare for global clock).

**Project Fit**:
- Fixed 5min real-time: Server uses wall time. Late TB influence: Apply from receive time onward (or back-apply consumption if justified).
- Orders: Execute vs. bar at T when action processed or at trigger T.
- Buffer: Keep last N seconds of sim states (or just action history + re-advance from checkpoint).
- For TB: Contention resolved at application time; no deep rewind needed for global R usually.

**Pseudocode**:

```python
class HistoryBuffer:
    states: List[Snapshot]  # {t: , state_hash: , full_state? (or deltas)}
    MAX_AGE = 5.0  # real seconds

    def rewind_and_replay(self, target_real_ts: float, action: Action):
        snap = find_closest_snapshot_before(target_real_ts)
        temp_engine = restore(snap)
        # Advance temp to target_ts applying pending
        temp_engine.apply(action)
        # Re-advance to now, merge back or validate
        ...

# On late action receipt
if action.real_ts > now - MAX_AGE:
    self.history.rewind_and_replay(action.real_ts, action)
else:
    # Too late: ignore or apply from now (policy)
```

**Recs**: For MVP, simple queue + server receive time is often sufficient (low tick rate). Add rewind if order fills feel unfair. Client side uses GGPO-like rollback for own prediction errors. Test extensively with simulated latency (task from roadmap).

## 7. Post-Match Audit / Spectator Re-Sim

**Pattern**: Persist minimal (arena_id + action_log + metadata + reported outcome). Re-sim on server for canonical audit (score verification, cheat flagging). Spectators: live deltas or full re-sim (server streams or client replays locally if arena provided post-match or via hash).

**Concrete**:
- Photon: "Replays & Spectating... full match replays... server-provided replays." "In-game replays and built-in spectating."
- ChartChamps: Match replays + review trades.
- FXR/others: Replay mode + battles review.
- General: Referee sims; post-game audit trails.

**Project Fit**:
- End: Persist log + arena_id + final equities. Run verify_replay(); store result.
- Spectator mode (future): WS subscribe to room (read-only) or "replay" endpoint that re-simulates and emits events at accelerated rate.
- UI scrubber: Timeline of actions + state at T; re-sim locally or fetch snapshots.

**Pseudocode**:

```python
# Post match
audit_result = sim.verify_replay(arena_id, persisted_log)
if audit_result['final_equity_p1'] != reported['p1']:
    flag_cheat_or_bug(match_id)

# Spectator / replay endpoint (FastAPI)
@app.get("/replay/{match_id}")
async def get_replay(match_id: str, speed: float = 1.0):
    log = load_log(match_id)
    arena = load_arena(log.arena_id)  # or stream normalized
    # Generator yielding events at accelerated real time
    for event in simulate_and_yield(log, arena, speed):
        yield event
```

**Recs**: Start with server re-sim on end + log storage. For spectators (roadmap Phase 5): in-memory for live; persisted re-sim for after. Allow post-match reveal of real arena details. Integrate with voice logs (opt-in).

## Additional Patterns, Pitfalls, Libraries, Testing (Cross-Cutting)

**Libraries / Inspirations (adapt, don't copy wholesale)**:
- GGPO (MIT, C++): Core rollback ideas; port concepts or use as reference for input prediction/sticky.
- Photon Quantum principles (free tier?): Determinism by design, inputs-only, referee replays.
- GGRS / bevy_ggrs patterns: Synctest + checksums (implement equivalent Python test harness).
- Python ecosystem: pandas/Decimal for sim; FastAPI WS rooms (or Starlette); Redis for cross-server later. No native GGPO equivalent—build custom.
- Others: Colyseus (rooms), custom lockstep if ever P2P.

**Pitfalls (from arch + research)**:
- Desync sources: floats, ordering, side effects in "pure" functions, library nondet.
- Latency + TB UX: Feels unfair if R flips late.
- Replay storage: Compress logs; snapshot periodically.
- Cheats: Bots (rate limit + anomaly detect on actions); external knowledge (mitigated); memory hacks (server auth).
- Scale: In-mem fine for MVP; per-room process if Python GIL issue.
- Reconnects mid-TB: Snapshot + catch-up actions.

**Testing Strategies** (high priority per roadmap):
- **Determinism harness**: `test_determinism.py`: Load arena, two engines, feed same actions (synthetic or recorded), assert every periodic checksum + final identical. Run on CI across envs.
- **Synctest equivalent**: Run sim forward, rollback N frames (re-apply actions), assert state == before rollback.
- **Lag/contention tests**: Simulated network (delay, reorder, drop) on WS test clients; verify same final + no unfair advantage.
- **Normalization tests**: Raw slice → normalized P[0]=100 + returns match expected; hash stable.
- **Full match fuzz + audit**: Random arenas + action streams → re-sim → no exceptions + consistent.
- **Property-based**: Hypothesis or similar for "same inputs → same outputs".
- Periodic in-match: Exchange/broadcast checksums; on mismatch, log + optional resync snapshot.
- Manual: Record real play sessions; re-sim and diff equities.

**Tailored MVP Recommendations for Chart-Fights + FastAPI**:
- Prioritize: task-001 (norm + logging basics) + task-002 (TB with logging) + task-005 (WS + sim loop).
- Data: Pre-normalized arenas with embedded hash + generic labels.
- Sim: Pure Python deterministic (Decimal everywhere critical; no random unless seeded).
- Comms: WS deltas (T, R, new_bar window, resource deltas, event notifications). Compact (or msgpack).
- Anti-cheat MVP: Normalization + private + server auth + action logging + end-of-match verify.
- Hardening: Add periodic checksums, lag test harness, reconnect snapshot logic.
- Future: Server referee for tournaments; ML anomaly on action patterns for bots.

**Open/Next (aligns with roadmap)**:
- Exact tick model (wall vs fixed) + broadcast freq.
- Input delay / prediction depth for client.
- Arena format details (OHLC vs returns; volume).
- Re-sim perf for long logs.
- Full integration with sabotage/IP (task-003) and orders (task-004).

Update task-001, architecture-overview.md §6 (Anti-Cheat), roadmap §5 (Anti-Cheat validation), and add tests per this. This provides concrete patterns ready for implementation.

**References/Sources**:
- Internal: All chart-fights docs cited above.
- External: GGPO site/github, Photon Quantum site, Bevy desync post, Gabriel Gambetta lag series, various gamedev.stackexchange/Unity/Reddit on deterministic netcode, product sites for ChartChamps/FXR/TraderFi.
- Additional searches covered rollback vs lockstep, server rewind, state hashing, private data in sims.

Ready for docs updates or Cursor task-001 extension.
