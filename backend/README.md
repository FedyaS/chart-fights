# chart-fights — Backend (MVP playable prototype)

Authoritative FastAPI + WebSocket backend for the 1v1 PvP stock-chart fighting game.
Server owns all simulation: a shared contested clock (`T`/`R`), Tempo Bar (TB) and
Intel Point (IP) economies, order execution + P&L, sabotage abilities, and win
determination. Clients send **actions only**; the server broadcasts authoritative
state. Everything is deterministic (`Decimal` math, no live RNG, no wall-clock in the
audited state) so `verify_replay` can re-simulate a match from `(arena + action log)`.

See `docs/design/game-mechanics-spec.md` for the authoritative mechanics and
`docs/cursor-tasks/` for the task breakdown.

## Run

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

> Run with a **single worker** — match state is in-memory per process (MVP scope).

## Test

```bash
cd backend
python -m pytest -q
```

## Module map

| File | Responsibility |
|---|---|
| `app/main.py` | FastAPI app: HTTP endpoints + `/ws/{match_id}` room, broadcast, voice relay |
| `app/sim/engine.py` | `SimulationEngine`, `MatchState`, `SharedClock`, `TBResolver`, P&L, sabotage, win condition, `verify_replay` |
| `app/sim/deltas.py` | Pure builders for the `delta` broadcast payload |
| `app/arena.py` | Arena loader: reads `data/arenas_index.json` + `data/arenas/*.parquet`, normalizes `Close[0]=100` |

## Core mechanics (as implemented, per spec)

- **Clock:** `T += real_delta * R`. `R` is contested: any **pause** → `R=0`; else `R = max` of active FF tiers (`ff2`=2, `ff3`=3, `ff5`=5); else `R=1`. Bars apply on every newly-crossed integer `T` in ascending order.
- **Tempo Bar (0–100):** recharge +1.0/s (pause +4.0/s); consume pause 0, ff2 2.0/s, ff3 5.0/s, ff5 12.0/s. An FF overridden by a pause delivers no speed and is not charged; an FF holder at TB 0 is force-released.
- **Intel Points (start 50, soft cap 200):** passive +0.5/s; **+10% of realized P&L on profitable closes** (losses grant nothing); spent on sabotage/peek.
- **Orders:** market (immediate fill at current bar close ± base spread), limit & stop (resting; evaluated against each crossed bar's OHLC, gap-aware). Long/short via `side`. `close` (full or `fraction`) flattens at market.
- **P&L:** per-instrument netted signed position with average entry. `unrealized = Σ size·(price−entry)/entry`; realized booked on reduce/close/flip; `equity = 100 + realized + unrealized`. Base spread `0.07%` adverse on market/stop fills.
- **Sabotage (IP cost / real-second cooldown):** `delete_sl` (30 / 60s) removes all victim stop orders; `widen_spread` (25 / 45s, 15s effect) adds 0.6% adverse slippage to the victim's fills; `fake_news` (40 / 90s) plants a headline in the victim's feed; `peek` (60 / 120s) reveals a headline to the caster. Cooldowns/durations use a deterministic match-time accumulator (real seconds), so replays reproduce them.
- **Win condition (spec §8):** higher final equity wins; equal equity → draw.

---

## WS / HTTP Contract

Frontend must align to these shapes. **Existing fields are stable** (never renamed or
removed); new fields may be added over time. Money/resource numbers are JSON numbers
(server quantizes equity/IP to 0.01, TB to 0.001).

### HTTP

#### `GET /health`
→ `{ "status": "ok", "matches": <int> }`

#### `GET /arenas`
→ `{ "arenas": [ { "id": str, "ticker": str, "bars": int, "start": str|null } ], "total": int }`

#### `POST /matches`
Request:
```jsonc
{ "arena_id": "string", "player_ids": ["p1","p2"] }   // player_ids optional, defaults ["p1","p2"]
```
Response:
```jsonc
{
  "match_id": "8charid",
  "arena_id": "string",
  "arena_label": "Broad Equities",
  "arena_hash": "sha256-16",
  "content_hash": "sha256-16",
  "num_bars": 312,
  "ws_url": "/ws/8charid"
}
```

#### `GET /matches/{match_id}`
→ `{ "match": <SNAPSHOT>, "is_over": bool }`  (see SNAPSHOT below)

#### `POST /matches/{match_id}/action`
Request: `{ "player_id": "p1", "type": "<action_type>", "payload": { ... } }`
→ `{ "ok": bool }`  (HTTP fallback for the same actions sent over WS)

#### `GET /matches/{match_id}/replay`
→ anti-cheat re-simulation result:
```jsonc
{
  "verify": {
    "verified": true,
    "final_hash": "…", "original_hash": "…",
    "final_equity": {"p1": 101.2, "p2": 98.7},
    "original_equity": {"p1": 101.2, "p2": 98.7},
    "final_t": 142.0, "original_t": 142.0,
    "content_hash": "…"
  },
  "hash": "…"
}
```

### WebSocket  `GET /ws/{match_id}?player_id=p1`

`player_id` query param identifies the player (`anon` → auto-assigned `p1`/`p2`).
The bg clock starts on the first connection.

#### Server → Client

**`snapshot`** (sent immediately on connect; full state):
```jsonc
{ "type": "snapshot", "you": "p1", "state": <SNAPSHOT> }
```

**`delta`** (broadcast ~15 Hz while the clock runs):
```jsonc
{
  "type": "delta",
  "t": 12.34,                 // fractional sim-day index
  "r": 3.0,                   // current contested rate
  "current_bar": { "t": 12, "open": 100.4, "high": 101.0, "low": 99.8, "close": 100.7 },
  "resources": {              // per-player; keys are player ids
    "p1": { "ip": 52.0, "equity": 101.23, "tb": 88.5 },
    "p2": { "ip": 49.5, "equity": 98.40,  "tb": 64.0 }
  },
  "tb": { "r": 3.0, "tbs": {"p1": 88.5, "p2": 64.0}, "influences": {"p1": "ff3", "p2": null} },
  "fills": [ <FILL>, ... ],   // fills produced since last broadcast (may be empty)
  "events": [ <EVENT>, ... ], // recent events (last 5)
  "content_hash": "sha256-16"
}
```

**`ack`** (reply to a client `action`):
```jsonc
{ "type": "ack", "ok": true }
```

**`match_end`** (broadcast once when the match ends):
```jsonc
{
  "type": "match_end",
  "winner": "p1" | null,      // null when draw
  "is_draw": false,
  "result": <RESULT>,
  "final": <SNAPSHOT>,
  "content_hash": "sha256-16"
}
```

**Voice relay** — any `voice_*` message is forwarded verbatim to the *other* peer:
```jsonc
{ "type": "voice_offer"|"voice_answer"|"voice_ice"|"voice_*", "from": "p1", "payload": { ... } }
```

#### Client → Server

**Action envelope:**
```jsonc
{ "type": "action", "action_type": "<type>", "player_id": "p1", "payload": { ... } }
```
Supported `action_type` values & payloads:

| action_type | payload | effect |
|---|---|---|
| `tb_influence` (alias `set_tb`) | `{ "level": "pause"|"ff2"|"ff3"|"ff5"|"none" }` | set/clear this player's tempo influence |
| `submit_order` (aliases `order`,`place_order`) | `{ "type":"market"|"limit"|"stop", "instr":"X", "side":"long"|"short", "size":Number, "price":Number? }` | market fills now; limit/stop rest until a bar crosses their trigger |
| `close` (alias `close_position`) | `{ "instr":"X", "fraction":0..1 }` | market-close full (default) or fraction of a position |
| `cancel_order` | `{ "id": <order_id> }` | remove a resting order |
| `modify_order` | `{ "id": <order_id>, "price":Number?, "size":Number? }` | adjust a resting order |
| `ip_spend` (aliases `sabotage`,`ability`) | `{ "ability":"delete_sl"|"widen_spread"|"fake_news"|"peek", "target_player":"p2"? }` | spend IP on an ability (cost/cooldown enforced; target defaults to the opponent) |

**Voice envelope (relayed to peer):** `{ "type": "voice_*", "player_id": "p1", "payload": { ... } }`

### Shared object shapes

**`SNAPSHOT`** (`state` in snapshot / `match` in HTTP / `final` in match_end):
```jsonc
{
  "match_id": "…", "arena_id": "…", "arena_hash": "…", "content_hash": "…",
  "label": "Broad Equities",
  "T": 12.34, "r": 3.0,
  "match_time": 11.2, "time_left": 288.8,        // real seconds elapsed / remaining (of 300)
  "tb": { "r": 3.0, "tbs": {...}, "influences": {...} },
  "current_bar": { "t":12, "open":…, "high":…, "low":…, "close":… },
  "players": {
    "p1": {
      "ip": 52.0, "equity": 101.23,
      "realized_pnl": 0.50, "unrealized_pnl": 0.73, "return_pct": 1.23,
      "positions": { "X": { "size": 10.0, "entry": 100.07 } },
      "orders": [ { "id":1, "type":"limit", "instr":"X", "side":"long", "size":5.0, "price":98.4 } ],
      "cooldowns": { "delete_sl": 12.0 },          // match-time of last cast
      "sabo_effects": { "widen_until": 26.0 },
      "news_feed": [ { "t": 12.0, "headline": "…", "fake": true } ]
    },
    "p2": { … }
  },
  "is_over": false,
  "winner": "p1" | null,
  "is_draw": false,
  "result": <RESULT>,
  "recent_events": [ <EVENT>, ... ]               // last 10
}
```

**`RESULT`**:
```jsonc
{
  "winner": "p1" | null, "is_draw": false,
  "players": {
    "p1": { "equity": 101.23, "realized_pnl": 0.50, "unrealized_pnl": 0.73, "return_pct": 1.23 },
    "p2": { "equity": 98.40,  "realized_pnl": -1.0, "unrealized_pnl": -0.6, "return_pct": -1.60 }
  }
}
```

**`FILL`**:
```jsonc
{ "player":"p1", "instr":"X", "price":100.07, "size":10.0, "side":"long",
  "type":"market", "t":12.0, "realized":0.0, "order_id":1 }
```

**`EVENT`** (`type` is one of):
- `fill` — same shape as FILL.
- `tb` — `{ "type":"tb", "player":"p1", "level":"ff3", "t":12.0 }`
- `sabo` — `{ "type":"sabo", "ability":"delete_sl", "from":"p1", "victim":"p2", "msg":"…", "t":12.0, ... }`
- `peek` — `{ "type":"peek", "from":"p1", "to":"p1", "private":true, "headline":"…", "t":12.0 }`
- `ability_rejected` — `{ "type":"ability_rejected", "player":"p1", "ability":"…", "reason":"cooldown"|"insufficient_ip", "t":12.0 }`

## Anti-cheat / determinism

- All money/clock/resource math uses `Decimal`; equity/IP quantized before hashing/broadcast.
- The audited state is a pure function of `(arena, ordered action log)`. The live loop logs every action (incl. `_clock` advances) with `real_ts` + `sim_t`; `verify_replay` replays them in canonical order and asserts identical `state_hash`, equity, and `T`.
- Cooldowns / sabotage durations use a deterministic match-time accumulator (sum of logged `real_delta`s), not wall-clock, so replays reproduce them exactly.
- Arena data is normalized to `Close[0]=100` and only `% / normalized` values are exposed during play (generic labels), neutralizing external date/symbol knowledge.
