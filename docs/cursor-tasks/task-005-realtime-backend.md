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

---

## Deep Research Resolutions (sibling worker, 2026-06-26)

This section resolves the realtime-backend open questions tied to **Clock & Sync**, **Concurrency**, and **Reconnect**, grounded in 2026 best practices. It extends (does not duplicate) the notes above. **MVP scope is fixed**: in-memory single process, wall-time base (`1 real sec = 1 sim day` at `R=1`), server-authoritative, ~10–20 Hz broadcast. All numeric rules below are quoted verbatim from `game-mechanics-spec.md §1–2`.

### R1. Internal tick model: decoupled fixed sim tick + wall-time accumulator

**Resolution — run a single fixed-rate `asyncio` sim loop per room at an internal tick of 30 Hz, advancing `T` by an accumulated wall-time delta. Decouple the broadcast rate (10–20 Hz) from the sim tick.**

Rationale (from 2026 authoritative-server guidance): fixed tick rates of 20–64 Hz are the standard for real-time competitive games because they make state evolution smooth and reconciliation simple; you "pick the rate your game actually needs, not the highest number you can imagine," and most studios target ≤60 Hz to keep cost manageable ([crux](https://crux.supercraft.host/blog/what-is-an-authoritative-game-server/), [Metaplay 2026](https://www.metaplay.io/blog/server-authoritative-games)). Chart-Fights is **not** physics-heavy — the only continuously-evolving quantity is `T` (and derived mark-to-market P&L). A daily-bar sim only produces a *meaningful* discrete event when `T` crosses an integer (a new bar). So:

- **Sim tick (internal, 30 Hz / ~33 ms):** advance `T += dt_real * R` using a monotonic accumulator; resolve TB contention/consumption; detect integer-`T` bar crossings; trigger orders; mark P&L. 30 Hz gives smooth fractional-`T` motion for the client's chart timer even at `R=5` (a bar every ~200 ms) while leaving ample CPU headroom for 1v1.
- **Broadcast tick (12–15 Hz / every ~66–80 ms):** coalesce all state changes since the last broadcast into one delta frame. This matches the existing "~10–20 Hz or on change" guidance and the "send periodic full snapshots, more frequent deltas" snapshot/diff model.
- **Event-driven flush (immediate):** for low-latency-critical, discrete events — order fills, sabotage notifications, `R` changes from TB contention — emit an out-of-band event message immediately rather than waiting for the next broadcast tick. This is the "fixed tick loop for continuous state + event-based messaging for discrete interactions" hybrid that modern servers converge on ([Solana Garden](https://solana.garden/guides/game-networking-multiplayer-netcode-explained/)).

> **Why not pure event-driven?** `T` advances continuously, so a tick is needed to integrate it. **Why not a much higher tick?** No sub-millisecond duel resolution is needed; the contested quantity is a globally-shared scalar `R`, not per-entity hit detection. CS2-style subtick is **not** required, though we borrow its core idea (timestamp every action) for deterministic ordering — see R4.

**Determinism caveat (critical):** the *live* loop uses wall-clock `dt_real`, which is non-reproducible. Therefore the canonical state must be a pure function of the **action log + arena**, not of real timing jitter. Two options, pick **(b)** for MVP:
- (a) Quantize: snap each tick's `dt_real` to a fixed step before integrating `T`.
- (b) **Log the realized `T` at each action and each bar-crossing**, and make `verify_replay` re-integrate from those logged `T` values / the fixed step rather than from wall time. The live loop's `dt_real` jitter only affects *when* a bar reveal lands within a ~33 ms window; the *ordering and values* are pinned by logged sim-time. (See task-001 R-series for the audit contract.)

```python
TICK_HZ = 30
TICK_DT = 1.0 / TICK_HZ          # nominal; live loop uses measured dt, audit uses fixed step
BROADCAST_EVERY_TICKS = 2        # ~15 Hz broadcasts

async def room_loop(room: "MatchRoom"):
    last = time.monotonic()
    tick = 0
    while room.engine.match_real_elapsed() < 300.0 and room.open:
        now = time.monotonic()
        dt_real = now - last
        last = now
        room.engine.advance(dt_real)          # integrate T, resolve TB, cross bars, mark P&L
        tick += 1
        if tick % BROADCAST_EVERY_TICKS == 0:
            await room.flush_state_delta()     # coalesced delta frame
        await asyncio.sleep(max(0.0, TICK_DT - (time.monotonic() - now)))
    await room.end_match()                     # score, persist log+arena_id, verify_replay
```

### R2. Broadcast: deltas with periodic keyframe + immediate events

**Resolution — stream compact JSON deltas at ~12–15 Hz; send a full-state keyframe every ~2 s and on join/reconnect; push fills/sabotage/`R`-flips as immediate events.** Use the snapshot+diff model recommended for authoritative servers (periodic full snapshot, frequent deltas). Delta payload types (consumed by the LW `ReplayController` in `architecture-overview.md §5`):

| Type | Fields | Cadence |
|---|---|---|
| `clock` | `T`, `R`, `tb_level_by_player`, `influencers` (or anon) | every broadcast tick / on `R` change (immediate) |
| `bar` | `instr_id`, normalized OHLC for newly-crossed integer `T` | on bar crossing |
| `equity` | per-player marked equity (Decimal → string) | every broadcast tick |
| `orders` | open-order diff (added/modified/removed) | on change |
| `positions` | position diff (size/dir/avg) | on change |
| `resources` | `TB` (0–100), `IP`, regen/consume indicators | every broadcast tick |
| `event` | fill, sabotage-victim notice, fake-news, peek result | immediate |

Keep payloads compact (short keys; consider msgpack later). Cleanup dead sockets inside the broadcast loop to avoid one silent client blocking the room — the production-grade `ConnectionManager.broadcast` catches per-socket send failures and prunes them ([websocket.org](https://websocket.org/guides/frameworks/fastapi/)).

### R3. Concurrency: single-process asyncio, one task per room (no per-process rooms for MVV)

**Resolution — single Uvicorn process, `asyncio`, one `room_loop` task per match. Do NOT use process-per-room for MVP.** The 1v1 sim is trivially light (≤5 instruments, ≤2000 bars, two players, pure-Python Decimal arithmetic a few thousand ops/sec). The Python GIL is a non-issue at this load: each tick's CPU work is microseconds and the loop spends most of its time `await asyncio.sleep`-ing. An in-process `RoomManager` keyed by `match_id` is the standard FastAPI/Starlette pattern; the well-known caveat is that an **in-memory manager only works for a single process** — multiple Uvicorn workers each have isolated connection state, which is why Redis Pub/Sub is the documented path to multi-process scaling *later* ([FastAPI docs](https://fastapi.tiangolo.com/advanced/websockets/), [StackLesson](https://www.stacklesson.com/react-fastapi/fastapi-websockets/ch31-lesson-03-connection-manager/)).

Therefore, for MVP: **run with a single worker** (`uvicorn app:app --workers 1`) so the in-memory `RoomManager` is authoritative. Defer Redis Pub/Sub + room-affinity to Phase 5. If a future CPU-bound need arises (many concurrent rooms, or a heavier sim), move whole rooms to worker processes via `ProcessPoolExecutor` / a room-server pool — but that is explicitly out of MVP scope.

**RoomManager + WS endpoint pattern (FastAPI/Starlette):**

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

class MatchRoom:
    def __init__(self, match_id: str, arena: dict):
        self.match_id = match_id
        self.engine = SimulationEngine(arena, config)   # see task-001 pseudocode
        self.conns: dict[str, WebSocket] = {}           # player_id -> socket
        self.open = True

    async def connect(self, player_id: str, ws: WebSocket):
        await ws.accept()
        self.conns[player_id] = ws
        await ws.send_json(self.engine.build_snapshot())   # full state on join (R5)

    def disconnect(self, player_id: str):
        self.conns.pop(player_id, None)

    async def broadcast(self, msg: dict):
        dead = []
        for pid, ws in self.conns.items():
            try:
                await ws.send_json(msg)
            except Exception:
                dead.append(pid)            # prune silent/flaky sockets
        for pid in dead:
            self.disconnect(pid)

    async def flush_state_delta(self):
        await self.broadcast(self.engine.drain_pending_delta())

class RoomManager:
    def __init__(self):
        self.rooms: dict[str, MatchRoom] = {}
    def get_or_create(self, match_id, arena): ...
    def get(self, match_id): return self.rooms.get(match_id)

manager = RoomManager()
app = FastAPI()

@app.websocket("/ws/match/{match_id}/{player_id}")
async def match_ws(ws: WebSocket, match_id: str, player_id: str):
    room = manager.get(match_id)
    if room is None:
        await ws.close(code=4404); return
    await room.connect(player_id, ws)
    try:
        while True:
            action = await ws.receive_json()         # actions ONLY from client
            # validate (cost/cooldown/IP/order sanity) then log+apply server-side
            room.engine.receive_action(player_id, action["type"], action.get("payload", {}))
            # R-change / fill / sabotage produce immediate events flushed by engine hooks
    except WebSocketDisconnect:
        room.disconnect(player_id)
```

The `room_loop` (R1) is started as an `asyncio.create_task` when both players have joined (or at match-start countdown). Client messages mutate engine state on receipt; the loop owns time advance + broadcasts. This cleanly separates **input ingestion** from **simulation/broadcast**, the recommended "separate simulation ticks from network IO" structure.

### R4. TB contention under latency — exact resolver, deterministic ordering

**Resolution — server is the sole resolver; recompute `R` on every action receipt and every tick; resolve simultaneity by `(server_recv_monotonic_ts, player_id)` ordering; apply consumption by integrating over real time per active payer.** This implements `game-mechanics-spec.md §2` verbatim.

Exact rules encoded (do **not** deviate):
- Any active **Pause** ⇒ `R = 0.0` (Pause overrides all FF). Pausing player recharges TB at **+4.0/s**; pause consumption **0/s**.
- Else `R = max(level)` over active FF holders; **every** paying FF holder consumes at their own rate: FFx2 ⇒ `2.0/s`, FFx3 ⇒ `5.0/s`, FFx5 ⇒ `12.0/s`.
- No active controls ⇒ `R = 1.0`. Base TB recharge **+1.0/s** applies to any player not actively consuming (i.e., not holding FF; pausers get the +4.0 bonus instead).
- A player whose TB hits 0 while holding FF is force-released (R recomputed).

Because `R` is a single globally-shared scalar (not per-entity prediction), **latency handling is simple**: clients send influence `start`/`stop` (with heartbeats for held state), the server timestamps on receipt, recomputes `R`, and **immediately** broadcasts the new `clock` event. Ties between two near-simultaneous FF starts are decided by monotonic receive order; but since the rule is "`R = max`, all payers pay," the *outcome* is order-independent for the value of `R` — only consumption attribution depends on exact intervals, which the integrate-since-last-recompute approach handles deterministically.

```python
from decimal import Decimal

PAUSE_BONUS   = Decimal("4.0")    # /s TB recharge while holding pause
BASE_RECHARGE = Decimal("1.0")    # /s TB recharge when idle (not FF, not pause)
FF_CONSUME = {2: Decimal("2.0"), 3: Decimal("5.0"), 5: Decimal("12.0")}  # /s
TB_MAX = Decimal("100"); TB_MIN = Decimal("0")

class TempoBarResolver:
    def __init__(self):
        self.holds: dict[str, dict] = {}   # player_id -> {"mode": "pause"|"ff", "level": int}
        self.R = Decimal("1.0")

    def on_influence(self, player_id, mode, level, is_start, recv_ts):
        if is_start:
            self.holds[player_id] = {"mode": mode, "level": level}
        else:
            self.holds.pop(player_id, None)
        self.recompute_R()                 # then engine emits immediate `clock` event

    def recompute_R(self):
        if any(h["mode"] == "pause" for h in self.holds.values()):
            self.R = Decimal("0.0")
        else:
            ff = [h["level"] for h in self.holds.values() if h["mode"] == "ff"]
            self.R = Decimal(max(ff)) if ff else Decimal("1.0")

    def apply_resources(self, tb_by_player: dict, dt: Decimal):
        """Integrate TB recharge/consumption over a tick (dt real seconds)."""
        for pid, tb in tb_by_player.items():
            h = self.holds.get(pid)
            if h and h["mode"] == "ff":
                tb -= FF_CONSUME[h["level"]] * dt
                if tb <= TB_MIN:               # exhausted: force release
                    tb = TB_MIN; self.holds.pop(pid, None); self.recompute_R()
            elif h and h["mode"] == "pause":
                tb += PAUSE_BONUS * dt
            else:
                tb += BASE_RECHARGE * dt
            tb_by_player[pid] = min(TB_MAX, max(TB_MIN, tb))
```

**UX (per arch §9 pitfall "who controls R"):** broadcast `influencers` (or an anonymized "opponent is influencing tempo" flag) in the `clock` delta so the client can render the contested-objective feedback.

**Client prediction (resolves Clock-&-Sync open Q):** **pure server-follow for the shared clock; light optimism for own inputs only.** The client may optimistically drain *its own* TB bar and show a tentative `R` contribution, but must treat the server's `R`/`T` as truth and reconcile (lerp small deltas, hard-snap large ones). This avoids the "R flips late and feels unfair" frustration; heavy rollback/prediction (GGPO-style) is unnecessary because there is no per-entity remote prediction to hide — only a shared scalar that the server resolves authoritatively. Client-side **R smoothing**: interpolate the chart's playback timer toward server `T` (the LW `ReplayController` already scales its interval by `R`); never extrapolate past the latest server `T`.

### R5. Reconnect mid-match — snapshot + missed-delta catch-up

**Resolution — on (re)connect, server sends one full `snapshot` keyframe, then resumes deltas. No client-side replay needed; the snapshot is self-sufficient.** Because state is small, a full snapshot is cheaper and safer than diffing missed deltas. Snapshot schema:

```jsonc
{
  "type": "snapshot",
  "match_id": "…",
  "arena_hash": "sha256…",          // anti-cheat: client can't see real symbols/dates
  "labels": {"0": "Broad Equities", "1": "Tech Index", ...},
  "server_time_left": 184.2,         // real seconds remaining in the 5:00 match
  "clock": {"T": 142.0, "R": 3.0, "influencers": [...]},
  "bars": { "0": [/* normalized OHLC for T=0..floor(T) */], ... },  // or last window + you-have-up-to index
  "you": {                           // private to this player
     "tb": "57.50", "ip": "84.00",
     "positions": [{"instr": 0, "dir": "long", "size": "10", "avg": "103.21"}],
     "orders": [{"id": "o7", "type": "limit", "instr": 1, "px": "98.40", "sl": "96.0", "tp": "105.0"}],
     "feeds_unlocked": ["analytics"], "cooldowns": {"delete_sl": 12.0}
  },
  "opponent": { "equity_pct": 2.4 }, // only what spec allows opponent to see (fogged)
  "recent_events": [ /* last N fills/sabotage notices so reconnecting player isn't blind */ ]
}
```

Catch-up flow: client clears local chart, `setData` from `bars` (LW pitfall: use `setData` for bulk, `update` for live), restores overlays from `you.orders`/`positions`, then follows deltas. Because the engine keeps the canonical state in memory keyed by `match_id`, reconnect is "look up room, send `build_snapshot()`, re-register socket." Heartbeats (ping/pong) detect drops; held TB influence is **released on disconnect** (a disconnected player can't keep contesting tempo) and must be re-asserted on reconnect — document this as the contention policy.

### R6. Order execution & P&L marking at `T` boundaries (determinism-relevant)

Aligns with `game-mechanics-spec.md §4`:
- **Market** orders fill immediately at current bar price ± base spread (~0.05–0.1%), worsened if `Widen Spreads` sabotage is active on the victim.
- **Limit/Stop** orders are resting and evaluated **on each integer-`T` bar crossing** against that bar's OHLC (MVP fidelity decision: close-only vs high/low trigger is a Tier-2 open Q — default to **close-cross** for MVP determinism, note high/low as a later upgrade).
- **Apply order at each crossing (fixed, to keep determinism):** (1) resolve TB/`R` for the step, (2) advance `T`, (3) for each newly-crossed bar in ascending index: reveal bar → trigger resting orders (sorted by deterministic key) → apply market/sabotage effects → mark all positions to the new bar → grant IP on profitable realized closes (+10% realized P&L per §2) → accrue passive IP (+0.5/s) and TB recharge/consume. This canonical ordering is the contract `verify_replay` re-executes (see task-001).
- Use **`Decimal`** for every price/size/equity/TB/IP value; never float. Quantize equity/IP to a fixed scale before hashing/broadcast.

### Open questions now resolved (task-005 summary)

| Open Q (roadmap/arch) | Resolution |
|---|---|
| Internal tick vs wall time | 30 Hz fixed sim tick integrating wall-time `dt`; audit re-integrates from logged sim-time (R1) |
| Broadcast frequency (fixed vs event-driven) | Hybrid: 12–15 Hz coalesced deltas + immediate events for fills/sabotage/`R`-flips + ~2 s keyframes (R2) |
| Client prediction vs pure follow | Pure server-follow for shared clock; optimistic own-input UI only; reconcile lerp/snap (R4) |
| R smoothing on client | Interpolate chart timer toward server `T`, never extrapolate (R4) |
| Python GIL / async vs process-per-room | Single-process asyncio, one task per room for MVP; Redis Pub/Sub + workers deferred (R3) |
| FastAPI/Starlette WS room manager | In-memory `RoomManager` keyed by `match_id`, prune dead sockets, single worker (R3) |
| Reconnect mid-match catch-up | Full `snapshot` keyframe on (re)connect, then resume deltas; release TB on disconnect (R5) |

**Sources (2026 research):** FastAPI WebSockets docs <https://fastapi.tiangolo.com/advanced/websockets/>; production ConnectionManager pattern <https://websocket.org/guides/frameworks/fastapi/>; FastAPI+Redis Pub/Sub scaling <https://www.samadshaikh.dev/blog/scaling-stateful-websockets-fastapi-broadcast>; room-broadcast lesson <https://www.stacklesson.com/react-fastapi/fastapi-websockets/ch31-lesson-03-connection-manager/>; authoritative server tick guidance <https://crux.supercraft.host/blog/what-is-an-authoritative-game-server/>, Metaplay 2026 <https://www.metaplay.io/blog/server-authoritative-games>; tick-rate vs cost + CS2 subtick <https://edgegap.com/blog/game-server-tick-rate-explained-gameplay-precision-vs-infrastructure-cost>; netcode/prediction <https://solana.garden/guides/game-networking-multiplayer-netcode-explained/>. Cross-references: `anti-cheat-determinism-design-notes.md` (verify_replay, checksums), `game-mechanics-spec.md §1–4`, task-001 R-series.