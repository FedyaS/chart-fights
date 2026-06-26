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