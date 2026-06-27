# Cursor Agent Task: Frontend - Realtime Streaming Charts + UI Panels (MVP)

**Context**: Chart-Fights. References:
- docs/design/architecture-overview.md (frontend section, stack recs)
- docs/design/game-mechanics-spec.md (UI needs: charts, TB/IP bars, orders, notifications, chat)
- docs/design/GDD.md (UI/UX flows)

**Goal**: Implement the React/TS frontend with TradingView Lightweight Charts for streaming historical replay, plus panels for orders, resources (TB/IP), notifications, and basic text chat. Use WebSocket client to consume backend state.

## Requirements (from arch + specs)
- Use TradingView Lightweight Charts (or equivalent Canvas-based) for multi-instrument candlestick charts with realtime `series.update()` for new bars.
- Panels:
  - Charts area (shared time, synced across instruments).
  - Orders/positions panel (place market/limit/stop, attach SL/TP, close).
  - Tempo Bar (TB) controls: Pause, FFx2/3/5 buttons or slider. Show current R and who is influencing.
  - Intel Points (IP) display + buy feeds/sabotage buttons (with costs).
  - Notifications feed (fills, sabotage, news).
  - Text chat.
- Connect to backend WS: Subscribe to match room, send actions (orders, TB influence, IP spends), receive state updates (T/R, bars, equity, orders, resources, events).
- Normalize display (prices start at 100, % changes).
- Basic lobby stub if time.
- Responsive, clean, focused on duel feel.

**Stack**: React + TS + Zustand (state) + LW Charts. Assume backend WS is available from task-005.

**Non-goals**: Voice (separate task), full auth, mobile polish, spectator mode.

## Acceptance Criteria
1. WS client hook for state subscription and action sending.
2. Live updating charts with new bars from server deltas.
3. Functional order panel that sends actions and reflects server state.
4. TB controls that send influence and show contested R.
5. IP spend UI for feeds/sabotage (mock effects if backend not ready).
6. Notification and basic chat panels.
7. Tests or stories for key components (e.g., chart update, order form).
8. Matches the "fast, tense, personal duel" feeling from GDD.

## Cursor Agent Prompt (copy-paste ready)
"Build the frontend for Chart-Fights per docs/cursor-tasks/task-007-frontend-streaming.md and architecture-overview.md + game-mechanics-spec.md.

Use React/TS + TradingView Lightweight Charts. Implement realtime streaming via WS client (consume deltas for T/R, bars, equity, orders, resources). Build panels for charts (multi-instrument synced), orders (market/limit/stop + SL/TP), Tempo Bar controls (Pause/FF with costs), IP actions, notifications, text chat.

Follow the UI/UX from GDD. Make it feel contested and psychological. Use Zustand or similar for state. Assume backend from task-005. Add clear visual feedback for shared clock and sabotage.

Create clean, reusable components. No heavy prediction needed for MVP."

## Integration
- Depends on task-005 (backend WS).
- Feeds into voice task later.

## LW Sub Insights (from 019f058c + 019f0577, appended 2026-06-26 15m review)
Key for task-007: Preload norm data (setData init); update() for deltas/stream (server T or R-scaled timer). Sync: timeScale visibleLogicalRange subs for multi-symbol/scrub/FF (master/slave to avoid loops). Overlays: markers (createSeriesMarkers/setMarkers for entries/exits), priceLines (createPriceLine for SL/TP/levels), parallel equity series (Line/Area). React: useRef + useEffect (create/add/setData/resize/cleanup); WS onmessage: series.update(bar); updateOverlaysFromState(). ReplayController (custom hook): useEffect + setInterval scaled by R (baseMs / R; clear on pause R=0; direct range on FF/scrub). Delta Types (from 005): BarDelta, ResourceDelta {T,R,TB_level}, OrderDelta (list/diff -> markers/priceLines), EquityDelta, EventDelta (fills/sabo notifs/news). Pitfalls: update() only latest; master/slave for sync; full marker replace; ref leaks (strict cleanup); no extrapolation; server T truth + conservative client. Sources: tradingview.github.io (realtime-updates, time-scale, react/advanced, how_to markers/price-line); scratch/sub_lw_controller_20260626.txt. Rec: reusable SyncedChart + useReplayController; follow official + sub patterns exactly for "fast tense duel" feel + contested visuals. High readiness.
- Use normalized data from data pipeline tasks.

**Fresh LW sub 019f05bc-ed2b (78s complete)**: Official realtime demo: setData(initial); interval series.update(delta) + scrollToRealTime(). v5: addSeries(CandlestickSeries), createSeriesMarkers + .setMarkers(), createPriceLine/apply/remove. Logical master/slave: subscribeVisibleLogicalRangeChange(r => slave.setVisibleLogicalRange(r)). React strict: chart.remove() + unsubs in cleanup. Custom R-scaled controller + setVisibleLogicalRange around T. setData only init (save logical range); update for stream. Perf fine. Pitfalls: jumps on setData, alignment. URLs + full excerpts in sub. Integrate exact for ReplayController + overlays. High readiness.

**Fresh Official v5 Realtime + Replay/Scrub Controller Research (sub 019f05db-b957... 116s, 2026-06-26)**:
- URLs (official): realtime-updates https://tradingview.github.io/lightweight-charts/tutorials/demos/realtime-updates ; sync/crosshair https://tradingview.github.io/lightweight-charts/tutorials/how_to/set-crosshair-position ; markers https://tradingview.github.io/lightweight-charts/tutorials/how_to/series-markers ; price-line https://tradingview.github.io/lightweight-charts/tutorials/how_to/price-line ; react/advanced https://tradingview.github.io/lightweight-charts/tutorials/react/advanced ; time-scale https://tradingview.github.io/lightweight-charts/docs/time-scale ; GitHub skill https://github.com/tradingview/lightweight-charts/blob/master/.github/skills/lightweight-charts/SKILL.md .
- Core patterns (verbatim excerpts):
  - Realtime deltas: `const data = ...; series.setData(data.initialData); ... setInterval(() => { const update = ...; series.update(update.value); }, 100);` + `scrollToRealTime()`. WS: `ws.onmessage = ev => { const bar = JSON.parse...; series.update(bar); }`. "update() only handles the latest bar." "Do not recommend calling setData to update".
  - Logical sync master/slave: `chart1.timeScale().subscribeVisibleLogicalRangeChange(r => chart2.timeScale().setVisibleLogicalRange(r));` (guard loops). LogicalRange {from, to} fractional (e.g. 5.2). "setVisibleLogicalRange ... beyond the bounds of the available data ... chart margin".
  - Markers: `createSeriesMarkers(series, [{time: {..}, position: 'aboveBar', color:.., shape:.., text:'Buy'}]);` or setMarkers. Full replace on changes.
  - PriceLines: `const pl = series.createPriceLine({price:.., color:.., lineWidth:2, lineStyle: LineStyle.Dashed, title:'SL'}); pl.applyOptions(..); series.removePriceLine(pl);`.
  - React (advanced): useLayoutEffect + Context + forwardRef + useImperativeHandle for live api; cleanup `chart.remove();` + unsubs + isRemoved guard. useRef for series to .update() post-WS.
  - ReplayController: Custom (no built-in). useEffect + setInterval(baseMs / R); on tick `master.timeScale().setVisibleLogicalRange({from: currentT-w, to: currentT+o})`; clear on R<=0 (pause). Direct range for scrub/FF. Server T drives; conservative client.
- Pitfalls: setData causes jumps (GitHub #1875/#549); sync loops (must master/slave or guard); React leaks (no remove); update only latest (middle needs setData).
- Actionable Cursor rec (for task-007): Preload norm via setData on mount (from task-006 snapshot). WS deltas (task-005) -> series.update + equity.update + rebuild markers/priceLines (from Order/Equity/EventDelta) + update controller state (T/R). Use logical for T-indexed scrub (no real dates). Master chart drives slaves. R-scaled timer or direct delta follow for contested clock (pause freeze, FF scale/direct). Strict React: chart.remove in cleanup. Reusable: SyncedMultiChart + useReplayController hook + Zustand. Follow exact official + arch §5 Mermaid. Test with simulated R/lag. "fast tense duel" visuals via overlays + contested R indicators.
Full sub transcript + excerpts for handoff paste in scratch/sub equiv + STATUS. High readiness. Integrate with normalized P[0]=100 + generic labels.

**Priority**: High for playable MVP.
**Size**: Medium (UI heavy).

---

## Deep Research Resolutions (sibling worker, 2026-06-26)

This section **extends** (does not duplicate) the LW notes above. It resolves the open frontend
questions with concrete, MVP-scoped recommendations grounded in the **current (2026) Lightweight
Charts v5 API** (verified against official docs + the upstream agent SKILL), and stays consistent
with the architecture's authoritative-server / conservative-client stance (server owns `T`/`R`;
client follows + smooths; optimistic only for the player's own actions).

### 0. v5 API verification + one correction to earlier notes (IMPORTANT)

Verified against the v4→v5 migration guide and the official API (LW v5.2, 2026):

- **Series creation is unified**: `chart.addSeries(CandlestickSeries, options, paneIndex?)`.
  The v4 helpers `addCandlestickSeries` / `addLineSeries` / `addAreaSeries` **no longer exist**.
  Series types must be **imported** for tree-shaking (ESM). ([migration][lw-mig], [skill][lw-skill])
- **Markers are now a primitive** — `series.setMarkers(...)` **does not exist on `ISeriesApi` in v5**.
  Earlier notes in this file say "createSeriesMarkers/setMarkers"; the correct v5 usage is:
  `const m = createSeriesMarkers(series, markers); m.setMarkers(newArray); m.markers(); m.detach();`
  `setMarkers([])` clears. `color` is **required** on every marker. ([migration][lw-mig], [createSeriesMarkers][lw-markers], [issue #1665][lw-1665])
- **Price lines are unchanged** and remain methods on the series: `series.createPriceLine({...})`,
  `priceLine.applyOptions({...})`, `series.removePriceLine(priceLine)`. ([price-line][lw-priceline])
- **Realtime**: `series.update(point)` appends if `point.time > lastTime`, replaces if `===`.
  `setData()` **replaces the dataset and resets the visible range** → never call it per tick. ([realtime][lw-realtime], [skill][lw-skill])
- **Sync**: `timeScale.subscribeVisibleLogicalRangeChange(cb)` + `setVisibleLogicalRange({from,to})`
  (logical = fractional bar indices, not time). `setVisibleRange` is time-based; `fitContent()` resets. ([time-scale][lw-timescale], [skill][lw-skill])
- **Panes (v5, single chart)**: `chart.addSeries(Type, opts, paneIndex)` auto-creates a pane one
  past the current count; size via `chart.panes()[i].setHeight(px)`. Keep the `IPaneApi` ref if panes
  can move (`pane.paneIndex()`). ([skill][lw-skill])
- **Resize**: v5 supports `createChart(el, { autoSize: true })` (uses `ResizeObserver`). ([skill][lw-skill])

### Q1. Should the client allow scrub, and how does it map to server-authoritative `T`?

**Resolution (MVP): Decouple scrubbing from the shared clock.** The shared `T` is contested and
server-authoritative (mech-spec §1); letting the client "scrub" the shared clock would either be a
no-op or fight the server. Two distinct interactions:

1. **Live timeline (master)** — always tracks server `T`. The newest revealed bar sits at the right
   edge. The player cannot drag this backward to change the game.
2. **Local analysis pan/zoom (read-only)** — purely client-side inspection of already-revealed
   history. Panning left to study old bars sets a local flag `isInspecting = true` and **pauses
   auto-follow**. A persistent **"⟶ Return to Live"** button snaps back (`scrollToRealTime()` or
   `setVisibleLogicalRange` around current `T`) and clears the flag. No action is sent to the server.

This matches the mech-spec note that a *personal analysis scrub* is a future low-cost secondary
action — for MVP it is **local-only and free**, never mutating shared `T`. If a true "personal
rewind that costs IP" is added later, it becomes a server action returning a private windowed view;
do **not** build that for MVP.

```ts
// auto-follow guard inside the rAF tick (see useReplayController, Q7)
function onTick(estT: number) {
  if (store.isInspecting) return;            // user is studying history → don't yank the view
  master.timeScale().setVisibleLogicalRange({ from: estT - WINDOW, to: estT + RIGHT_OFFSET });
}
// user starts panning:
master.timeScale().subscribeVisibleLogicalRangeChange(() => {
  if (userInitiated) store.setInspecting(true);
});
// "Return to Live" button:
function returnToLive() { store.setInspecting(false); master.timeScale().scrollToRealTime(); }
```

### Q2. Lerp/smooth `R` changes vs snap?

**Resolution: Smooth the *scroll velocity*, snap the *bar reveal*.**

- **Bar reveal is discrete and snaps**: a new candle appears exactly when the server emits a
  `BarDelta` on an integer-`T` crossing → `series.update(bar)`. Never interpolate fake OHLC.
- **Scroll/scrub is continuous and eased**: between server `ResourceDelta` snapshots, advance the
  visible logical range with `requestAnimationFrame` using the server's `R` as the velocity, and
  **ease `R` transitions over ~150–250 ms** so a jump from 1×→5× (or →pause) does not look jarring.
- **Pause (`R ≤ 0`) freezes immediately** (no easing needed; freeze is the desired tactile feel).
  When unpausing, ease velocity back up.
- Always **reconcile to the server's authoritative `T`** on each snapshot (correct accumulated
  drift by lerping the estimate toward `serverT`, don't hard-jump unless drift is large).

Rationale: the architecture explicitly wants "server `T` truth + conservative client" with light
visual smoothing only — no predictive bar generation.

### Q3. "Current-T" indicator design

LW v5 has **no built-in vertical "now" line** (`createPriceLine` is horizontal only). Three options,
recommended in order of MVP simplicity:

1. **Right-edge convention + label (MVP default)**: keep the newest bar pinned at the right edge
   (it *is* current `T`). Show "Sim Day NNN · R=3.0×" in a HUD chip above the chart (driven by
   Zustand, not the chart). Cheap, unambiguous, zero chart plumbing.
2. **A marker on the latest bar**: `createSeriesMarkers` with one marker at the current bar
   (`position:'aboveBar'`, `text:'NOW'`). Rebuild only when `T` advances.
3. **A vertical-line pane primitive** (if you want a literal playhead inside the chart): attach a
   small custom primitive that draws a 1px vertical line at the x-pixel of the current logical index.
   Use `timeScale().logicalToCoordinate()` / `timeToCoordinate()` in the renderer.

```ts
// Option 3 sketch — minimal vertical "playhead" pane primitive (v5 primitives API)
class CurrentTLine {                       // implements ISeriesPrimitive / IPanePrimitive
  constructor(private getLogicalIndex: () => number) {}
  paneViews() {
    return [{
      renderer: () => ({
        draw: (target) => target.useBitmapCoordinateSpace(({ context, bitmapSize }) => {
          const x = chart.timeScale().logicalToCoordinate(this.getLogicalIndex() as Logical);
          if (x == null) return;
          context.strokeStyle = 'rgba(255,200,0,0.9)';
          context.beginPath(); context.moveTo(x, 0); context.lineTo(x, bitmapSize.height); context.stroke();
        }),
      }),
    }];
  }
}
chart.panes()[0].attachPrimitive(new CurrentTLine(() => store.currentT));
```

**Recommendation: ship Option 1 for MVP**, add Option 3 in polish if playtests want a stronger
"contested clock" feel.

### Q4. Equity in a separate pane vs an overlay series?

**Resolution: separate pane in the *same chart*** via `addSeries(AreaSeries, {}, 1)` (paneIndex 1).

- Equity (start = 100 *units* of capital) and normalized price (start = 100 *index*) share the
  number 100 but are **different quantities/scales** → overlaying them on the price scale is
  confusing and forces awkward autoscale. A dedicated pane keeps its own price scale.
- A pane in the **same chart automatically shares the time axis** → free synchronization with the
  price panes (no manual master/slave needed for equity). Size with `chart.panes()[1].setHeight(120)`.
- Drive it from `EquityDelta`: `equitySeries.update({ time: tToTime(T), value: equity })`.

### Q5. Rebuilding markers/priceLines efficiently on each delta

**Markers (entries/exits/fills)** — the v5 API is full-replace via the primitive, so:
- Create the primitive **once** per series and keep the ref.
- Maintain the marker array in the Zustand store keyed off `OrderDelta`/`EventDelta`; **only call
  `m.setMarkers(arr)` when the set actually changed** (guard with a version counter / shallow hash),
  not on every render or tick.

**Price lines (SL/TP/levels)** — these are individually mutable, so **diff instead of rebuild**:
- Keep `Map<orderId, IPriceLine>`. On `OrderDelta`: create new ones (`series.createPriceLine`),
  `applyOptions` for changed prices, `series.removePriceLine` for gone orders. Never tear down all
  lines each tick (avoids flicker + GC churn).

```ts
function reconcilePriceLines(series: ISeriesApi<'Candlestick'>, orders: Order[]) {
  const seen = new Set<string>();
  for (const o of orders) {
    seen.add(o.id);
    const existing = priceLineMap.get(o.id);
    const opts = { price: o.level, color: o.kind === 'SL' ? '#e53935' : '#26a69a',
                   lineStyle: LineStyle.Dashed, lineWidth: 2, title: `${o.kind} ${o.id}` };
    if (existing) existing.applyOptions(opts);
    else priceLineMap.set(o.id, series.createPriceLine(opts));
  }
  for (const [id, pl] of priceLineMap) if (!seen.has(id)) { series.removePriceLine(pl); priceLineMap.delete(id); }
}

// markers: rebuild array only when fills/orders version changes
function reconcileMarkers(markersApi: ISeriesMarkersPluginApi<Time>, fills: Fill[], version: number) {
  if (version === lastMarkerVersion) return;
  lastMarkerVersion = version;
  markersApi.setMarkers(fills.map(f => ({
    time: tToTime(f.t), position: f.side === 'buy' ? 'belowBar' : 'aboveBar',
    color: f.side === 'buy' ? '#26a69a' : '#e53935',
    shape: f.side === 'buy' ? 'arrowUp' : 'arrowDown', text: f.label,
  })));
}
```

### Q6. Avoiding sync loops (master/slave logical ranges)

**Resolution: prefer one chart with multiple panes** (free time-axis sync). Use **separate charts
only when instruments need independent price scales side-by-side**; then sync with the official
guarded master/slave pattern:

```ts
let syncing = false;
function link(a: IChartApi, b: IChartApi) {
  a.timeScale().subscribeVisibleLogicalRangeChange(r => {
    if (!r || syncing) return; syncing = true;
    b.timeScale().setVisibleLogicalRange(r); syncing = false;
  });
}
link(master, slave); link(slave, master);   // guard flag prevents the feedback loop
```

For N instruments, designate **one master** and make all others slaves of it (avoid N×N
subscriptions). The `syncing` boolean guard is the canonical loop-breaker from the official docs.

### Q7. `useReplayController` hook scaled by `R` (clear on `R ≤ 0`)

The controller is a **custom React hook** (no built-in replay in LW). It does **not** generate bars;
it interpolates the *visible window position* between authoritative server snapshots and snaps to
freeze on pause.

```ts
function useReplayController(master: IChartApi | null) {
  const { currentT, R, serverTs, isInspecting } = useStore();   // last server snapshot
  useEffect(() => {
    if (!master) return;
    if (R <= 0) return;                       // PAUSE: no rAF → frozen view (clear/freeze)
    let raf = 0;
    const base = { t: currentT, ts: performance.now(), serverTs };
    const loop = () => {
      const dtSec = (performance.now() - base.ts) / 1000;
      const estT = base.t + R * dtSec;        // R = simulated days per real second
      if (!isInspecting) {
        master.timeScale().setVisibleLogicalRange({ from: estT - WINDOW, to: estT + RIGHT_OFFSET });
      }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);   // STRICT cleanup on R/T change + unmount
  }, [master, currentT, R, serverTs, isInspecting]);
}
```

Notes: easing of `R` (Q2) can wrap the `R` used inside `loop` with a ramp; reconciliation toward
`serverT` happens naturally because each new `ResourceDelta` re-seeds `base`. On pause the effect
returns early so the timeline freezes instantly; FF just increases `R` (faster scroll) while bars
still arrive only on real `BarDelta`s.

### Q8. Delta message shapes + Zustand mapping

Authoritative shapes consumed from task-005 (snapshot on join/reconnect, deltas while streaming).
Time is **synthetic** (no real dates during play — see Q9):

```ts
type Delta =
  | { type: 'snapshot'; t: number; r: number; bars: Record<string, Bar[]>;
      orders: Order[]; equity: number; resources: Resources; events: GameEvent[] }
  | { type: 'bar';      symbol: string; bar: Bar }                  // BarDelta (on integer-T cross)
  | { type: 'resource'; t: number; r: number; tbLevel: number; ip: number; influencer?: 'self'|'opp'|'both'|null } // ResourceDelta
  | { type: 'order';    orders: Order[] }                          // OrderDelta (full open list or diff)
  | { type: 'equity';   t: number; equity: number; oppEquity?: number } // EquityDelta
  | { type: 'event';    event: GameEvent };                        // EventDelta (fill, sabotage, news, peek)

interface Bar { time: number; open: number; high: number; low: number; close: number }
interface Resources { tb: number; ip: number }
```

Zustand store is the **single source of truth for React UI**; the **chart refs are updated
imperatively** (never via React state re-render) for performance:

```ts
ws.onmessage = (ev) => {
  const d: Delta = JSON.parse(ev.data);
  const s = store.getState();
  switch (d.type) {
    case 'snapshot':                          // join/reconnect: full rebuild
      for (const sym in d.bars) seriesRefs[sym].setData(d.bars[sym].map(toLwBar));
      s.setResources({ tb: d.resources.tb, ip: d.resources.ip });
      s.setClock(d.t, d.r); s.setOrders(d.orders); break;
    case 'bar':    seriesRefs[d.symbol].update(toLwBar(d.bar)); break;     // imperative, no setState
    case 'resource': s.setClock(d.t, d.r); s.setResources({ tb: d.tbLevel, ip: d.ip }); break;
    case 'order':  s.setOrders(d.orders); reconcilePriceLines(mainSeries, d.orders); break;
    case 'equity': equitySeries.update({ time: tToTime(d.t), value: d.equity }); s.setEquity(d.equity); break;
    case 'event':  s.pushNotification(d.event); maybeRebuildMarkers(d.event); break;
  }
};
```

**Rule of thumb**: high-frequency, chart-bound data (`bar`, `equity`) → imperative `.update()` on
refs; UI-bound data (resources, orders list, notifications, clock chips) → Zustand. This keeps React
re-renders off the hot path.

### Q9. Time axis with no real dates (normalized arenas)

LW requires `Time = UTCTimestamp(seconds) | BusinessDay | string`, unique & ascending. Since arenas
hide real dates, **map the integer day index `T` to a synthetic monotonic timestamp** and relabel
the axis generically:

```ts
const tToTime = (t: number) => (t * 86400) as UTCTimestamp;   // 1 sim day = 86400 synthetic seconds
createChart(el, {
  timeScale: {
    tickMarkFormatter: (time) => `Day ${Math.round((time as number) / 86400)}`,  // "Day 137", never a date
  },
  localization: { timeFormatter: (time) => `Sim Day ${Math.round((time as number) / 86400)}` },
});
```

This keeps the anti-cheat "generic labels / no calendar dates" guarantee while satisfying LW's
ascending-time requirement and keeping logical-range scrubbing exact.

### React lifecycle & pitfalls (consolidated, v5)

- `useEffect(() => { const chart = createChart(el, { autoSize:true }); const s = chart.addSeries(CandlestickSeries, {}); ... return () => { unsub(); chart.remove(); }; }, [])` — **always `chart.remove()` + unsubscribe** in cleanup (React 18 StrictMode double-invokes effects; guard with an `isRemoved` flag).
- Store `IChartApi` / `ISeriesApi` / `ISeriesMarkersPluginApi` / `IPriceLine` in `useRef`, **not state**.
- `setData` only on mount/snapshot/reconnect; `update()` for every live tick.
- Don't put marker objects inside `setData()` points (v5 will ignore/break them).

### Sources (verified 2026-06-26)

- LW v4→v5 migration (addSeries, markers primitive): [tradingview.github.io/lightweight-charts/docs/migrations/from-v4-to-v5][lw-mig]
- LW upstream agent SKILL (v5 gotchas, realtime, panes, sync): [github.com/tradingview/lightweight-charts .../SKILL.md][lw-skill]
- `createSeriesMarkers` API (v5.2): [tradingview.github.io/lightweight-charts/docs/api/functions/createSeriesMarkers][lw-markers]
- Clearing/detaching markers in v5 (issue #1665): [github.com/tradingview/lightweight-charts/issues/1665][lw-1665]
- Realtime updates tutorial: [tradingview.github.io/lightweight-charts/tutorials/demos/realtime-updates][lw-realtime]
- Time scale docs (logical range, sync): [tradingview.github.io/lightweight-charts/docs/time-scale][lw-timescale]
- Price line how-to (unchanged in v5): [tradingview.github.io/lightweight-charts/tutorials/how_to/price-line][lw-priceline]

[lw-mig]: https://tradingview.github.io/lightweight-charts/docs/migrations/from-v4-to-v5
[lw-skill]: https://github.com/tradingview/lightweight-charts/blob/master/.github/skills/lightweight-charts/SKILL.md
[lw-markers]: https://tradingview.github.io/lightweight-charts/docs/api/functions/createSeriesMarkers
[lw-1665]: https://github.com/tradingview/lightweight-charts/issues/1665
[lw-realtime]: https://tradingview.github.io/lightweight-charts/tutorials/demos/realtime-updates
[lw-timescale]: https://tradingview.github.io/lightweight-charts/docs/time-scale
[lw-priceline]: https://tradingview.github.io/lightweight-charts/tutorials/how_to/price-line