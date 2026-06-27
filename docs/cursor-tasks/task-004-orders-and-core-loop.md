# Cursor Agent Task: Orders, Positions & Core Player Loop (MVP)

**Context**: Chart-Fights. References:
- docs/design/game-mechanics-spec.md (sections 3, 4, 8)
- Previous tasks (time engine from task-002, IP/sabotage from task-003)

**Goal**: Implement the core player loop, order types, position management, P&L, and win condition integration on top of the time/tempo engine.

## Requirements
- Player actions: Place/modify/cancel Market, Limit, Stop orders on instruments.
- Long/Short supported.
- Attached SL/TP modifiable live.
- Execution against the current bar at T advance.
- Unrealized P&L marked continuously; realized on close.
- Starting capital normalized (100 units).
- Final win condition: higher equity at real-time end.

Integrate with:
- Shared clock (new bars trigger marking + potential order fills).
- Sabotage effects (e.g. widened spreads on fills, deleted SLs).

## Acceptance Criteria
1. Order model + execution engine.
2. Position tracking and P&L calculator (realized + unrealized).
3. Core loop skeleton: observe -> decide -> act -> react to fills/events.
4. Basic validation and state consistency.
5. Tests for fills, partial closes, P&L at end, sabotage interaction placeholders.
6. Clean hooks for future UI.

## Cursor Prompt
"Implement orders, positions, P&L and the core player action loop per task-004-orders-and-core-loop.md and game-mechanics-spec.md sections 3,4,8.

Build on the time engine (task-002). Support Market/Limit/Stop + attached orders. Calculate P&L correctly as T advances. Handle sabotage effects on fills and stops.

Keep MVP simple (no complex margin). Include tests for determinism and edge cases. Wire in placeholder hooks for IP/sabotage from task-003."

**Priority**: Completes the playable core once time + abilities are done.

## Deep Research Resolutions (sibling worker, 2026-06-26)

Resolves the **order fidelity / fills / sizing / spread** open questions from `game-mechanics-spec.md §4` ("Open"), `roadmap-and-open-questions.md` (Tier 2: "Order fidelity/fills/priority/sizing") and the sabotage fill-hook interaction with task-003. All resolutions keep the spec's daily-bar, server-authoritative, deterministic model and starting capital = 100 units. Everything below is the recommended MVP default with a tunable config name where relevant.

### Background: how real backtesting engines fill on a daily bar (research grounding)
A daily bar gives only Open/High/Low/Close — the **intra-bar path (did High or Low come first?) is unknown**. Engines pick a point on an optimistic↔pessimistic spectrum: optimistic = "fill at the limit/stop price the instant the bar's range touches it"; pessimistic = "fill next bar's open". TradingView/PyneCore use a **direction heuristic** ("if open is closer to high, high happened first") and only resolve the ambiguous SL-vs-TP-same-bar case correctly with lower-timeframe "bar magnifier" data. Backtrader checks Limit against the bar's low/high and **has no defined intra-bar priority between multiple pending orders** (it just walks them in internal reference order). We deliberately choose **conservative, fully-deterministic rules** below — fidelity matters less than the two players being treated *identically and reproducibly* on the same normalized slice.

### OQ-O1: Close-only vs high/low intra-bar triggers → **High/Low triggers for resting orders, Close for marking; pessimistic fill on ambiguity.**
MVP fill model, evaluated at each integer-`T` bar application (see task-002 OQ-T1; bars apply in ascending order even across an FF jump):
- **Limit (buy):** fills if `bar.low <= limit_price`. Fill price = `limit_price` (price came to you). **Limit (sell):** fills if `bar.high >= limit_price`, fill at `limit_price`.
- **Stop / Stop-entry (buy):** triggers if `bar.high >= stop_price`; **Stop (sell)** triggers if `bar.low <= stop_price`. A triggered Stop executes as a **Market at the stop price plus adverse slippage** (see OQ-O4) — stops do not get a guaranteed price.
- **Stop-Loss (SL):** same trigger logic as Stop (long SL = sell-stop below entry → triggers on `bar.low <= sl`; short SL = buy-stop above → `bar.high >= sl`). Fills at SL price + adverse slippage.
- **Take-Profit (TP):** same as Limit (long TP = sell-limit above → `bar.high >= tp`; short TP = buy-limit below → `bar.low <= tp`). Fills at TP price (favorable).
- **Gap handling:** if the bar **opens already through** a resting order's price (gap), fill at the **bar open**, not the order price (you can't get a better price than the market opened at). E.g. buy-stop at 105 but `bar.open = 108` → fill at 108 (+slippage). This is the realistic and conservative choice.
- **Marking (unrealized P&L):** always at `bar.close`. Triggers use High/Low; marks use Close.

Config: `FILL_MODEL = "ohlc_trigger"` (vs a simpler `"close_only"` fallback where everything triggers/fills at close — keep it available behind the flag for an ultra-deterministic sanity mode and for the determinism harness baseline).

### OQ-O2: Same-bar SL **and** TP both reachable → **pessimistic ("stop-first") rule.**
When a single bar's range would trigger **both** a position's SL and its TP (the classic ambiguity; we have no intra-bar order), **assume the Stop-Loss fills first** (worst case for the holder). This is the standard conservative assumption and, crucially, it is **deterministic and symmetric** for both players. Do not use the open-distance heuristic in MVP (it's a guess that's wrong ~50% of the time on exactly these bars per PyneCore). Document as `AMBIGUOUS_BAR_RULE = "stop_first"`. (Post-MVP: intraday "bar magnifier" data resolves true order — explicitly deferred.)

### OQ-O3: Fill priority for simultaneous orders → **deterministic canonical ordering, exits before entries.**
Within one bar application, multiple of a player's resting orders may trigger. Process in this fixed order so replays are bit-identical:
1. **Exits before entries** ("exit-first", matching real broker/ml4t behavior): SL/TP and closes resolve before new entry Limits/Stops. This frees capital/closes risk first and avoids a position being both stopped out and re-entered in a weird order.
2. Within the same class, order by **`(instrument_id, order_id)`** ascending (`order_id` = monotonic creation sequence). This is the tie-break; never rely on dict/hash iteration order.
3. **Cross-player:** the two players' books are independent (no shared liquidity in MVP — normalized index prices, not an order book), so resolve **player A fully then player B**, with player ordering fixed by `player_id`. There is no fill-competition between players, so this only matters for log/replay determinism, not economics.

```
for day in bars_to_apply:            # ascending, from task-002
    apply_bar_prices(day)
    for player in sorted(players, key=pid):
        process_exits(player, day)   # SL, TP, manual closes queued this tick
        process_entries(player, day) # Limit/Stop entries
        mark_to_market(player, day.close)
        grant_ip_on_realized_profit(player)   # ties to task-003 OQ-IP1/IP5
```

### OQ-O4: Base spread / slippage model → **fixed bps adverse offset on market-style fills; widen-spread sabotage stacks on top.**
- **Base spread/slippage:** apply a fixed adverse offset to all **market** fills and **stop-triggered** fills (which become market): `SPREAD_BPS` default **7 bps (0.07%)**, inside the spec's 0.05–0.10% band. Buys fill at `price * (1 + spread)`, sells/closes at `price * (1 - spread)`.
- **Limit/TP fills get NO base slippage** (you specified the price; the market reached it). This mirrors real limit semantics and the backtest sources.
- **Determinism:** use a *fixed* spread, not random, for the base. (If a randomized micro-slippage is ever desired, seed it from `(arena_seed, fill_event_index)` — never live RNG.)
- **Widen Spreads sabotage (task-003 OQ-SAB4):** when the victim's `widen_until` is active, **add** the 0.4–0.8% adverse offset *on top of* the base spread, and extend it to **limit fills too** (the whole point is to poison even resting orders). Caster unaffected. Stacking formula: `effective_adverse = base_spread + widen_pct` (widen_pct deterministic per OQ-SAB4).

### OQ-O5: Position sizing model → **percent-of-starting-capital "units"; P&L%≈price%×size; no hard cap, no margin call (MVP).**
- Starting capital = **100 units** (per spec §4 / §8). Size is expressed in **units of capital allocated to the position** (a notional), e.g. "go long Tech Index, size 40" = 40 of your 100 units of exposure. Direction long/short.
- **P&L:** `position_pnl_units = size * direction * (current_price - entry_price) / entry_price` (prices are the normalized series, `P[0]=100`). So a +10% move on a size-40 long = +4 units. This makes "P&L% ≈ price% × size" hold exactly and is trivially deterministic.
- **Equity** = `100 + Σ realized_pnl + Σ unrealized_pnl(mark=close)`. Final score = equity at the 300s wall-clock end (task-002 OQ; match ends on real time, mark all open positions at the last applied bar's close).
- **No hard position limit, no margin calls** in MVP (spec §4 — equity may go deeply negative; final equity decides the winner). Add `MAX_GROSS_EXPOSURE = None` config hook for a future leverage cap, but leave unlimited for MVP per spec.
- Realized P&L on a close feeds task-003's +10%-on-profit IP grant (OQ-IP1).

### OQ-O6: Partial closes → **proportional realized P&L on the closed fraction; remainder keeps original entry (avg-price) basis.**
- Closing fraction `f` (0<f≤1) of a position realizes `f * unrealized_at_fill_price` and reduces `size` to `(1-f)*size`. The remaining position keeps the **same average entry price** (no basis reset).
- Multiple partial entries into the same instrument/direction use **weighted-average entry price**: `new_entry = (size*entry + add_size*fill)/(size+add_size)`. Opening the opposite direction first **closes existing size FIFO/netting** before flipping (MVP: net to a single position per instrument+direction; do not maintain separate lots).
- Each partial close that realizes a **profit** emits a realized-P&L event → +10% IP grant (task-003 OQ-IP5). Losing partials grant nothing and never subtract IP.
- Manual market close fills at `bar.close` (the latest applied bar) + base spread (OQ-O4) + active widen, if any.

### OQ-O7: How Market orders fill against a daily bar.
A Market order submitted between bars is **queued and filled at the next bar application**, at that bar's **open price + base spread** (adverse). Rationale: when the player clicks, the "current price" they see is the last applied close, but the next tradable price is the upcoming bar's open — filling at next-open + spread is the standard conservative, look-ahead-free rule (matches ml4t/code-vb "next-bar open" execution). For UX, show an optimistic preview at last-close but reconcile to the authoritative open-fill (server truth; client optimistic only, per task-002 OQ-T5). Config `MARKET_FILL = "next_open"` (alt `"same_close"` available for the close-only sanity mode).

### Core loop skeleton (observe → decide → act → react) — integration map
- **observe:** client renders bars/equity/orders from server `BarDelta`/`EquityDelta`/`OrderDelta`.
- **decide/act:** client sends order actions (place/modify/cancel/close) over WS (task-005); server validates and queues. Optimistic local markers/price-lines allowed; server reconciles.
- **react:** on each bar application the server runs the OQ-O3 pipeline, then broadcasts deltas (fills, new equity, SL-deleted/ widen events from task-003). Fills/sabotage produce victim notifications + voice/chat bait (GDD §15).
- **clock dependency:** all of the above is driven by task-002's integer-`T` bar applications; never fill on fractional `T` (task-002 OQ-T7).

### Determinism checklist for this task
- Prices, sizes, P&L, equity, spreads = `Decimal`, quantized consistently; never float.
- All ordering (orders within a bar, players, instruments) is canonical & explicit (OQ-O3) — no reliance on dict/set iteration order.
- Any slippage/widen magnitude is fixed or seeded from `(arena_seed, fill_event_index)`.
- `verify_replay(arena_id, sorted_action_log)` must reproduce identical fills, partial-close P&L, IP grants, and final equity hash (ties to task-001/005, and to task-002's bar-application determinism).

**Sources (web, 2026):**
- Intra-bar fill ambiguity, OHLC direction heuristic, SL-vs-TP-same-bar problem & "bar magnifier" (basis for OQ-O1/O2 conservative choice + deferred intraday upgrade): https://pynecore.org/docs/advanced/bar-magnifier/
- Same-bar vs next-bar execution modes, **exit-first** processing, stop-fill modes, "no intrabar stop simulation (uses bar OHLC)" limitation (basis for OQ-O3/O7): https://github.com/ml4t/backtest
- Practical OHLC limit/stop fill rules (buy-limit fills if `low ≤ L`; next-open market fill; bps slippage) (basis for OQ-O1/O4/O7): https://code-vb.com/paper-trading-simulators/
- Backtrader limit/stop trigger semantics & the fact it has **no realistic intra-bar multi-order priority** (motivates our explicit canonical ordering in OQ-O3): https://www.backtrader.com/docu/order-creation-execution/order-creation-execution/
- Price-time priority / queue position in higher-fidelity matching (context for why we *don't* need an order book at daily-bar granularity in MVP): https://medium.com/@DolphinDB_Inc/a-practical-order-matching-framework-for-high-frequency-strategy-backtesting-43e1eab3372b
