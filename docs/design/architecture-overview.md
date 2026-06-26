# Chart-Fights Technical Architecture Overview

**Version**: 0.1 (2026-06-26, post GDD + Mechanics Spec)  
**Scope**: High-level design for MVP (1v1 matches) with path to scalability (tournaments). Prioritizes support for core mechanics: **shared contested clock (T + R)**, **Tempo Bar (TB) / Intel Points (IP)**, **server-authoritative simulation**, **sabotage effects**, **normalized historical daily bars**, **voice+text chat**, and **anti-cheat via private arenas + normalization**.  

No code; diagrams in Mermaid/text. Draws from specs (GDD.md, game-mechanics-spec.md), data research (yfinance/Stooq primary), similar products (ChartChamps/FXR Battles for fairness/voice), and external best practices.

**Key Constraints from Specs**:
- Fixed 5 real-min matches; base 1s real ≈ 1 simulated trading day.
- Shared `T` (day index) and rate `R` contested via TB (Pause/FFx2/3/5).
- IP for vision/sabotage/peek (server-mutated state, always notify victim).
- Orders executed server-side against bars at `T` advance.
- All players on identical normalized slice (P[0]=100; % returns only).
- Data: pre-fetched daily OHLC, no live external calls mid-match.

---

## 1. High-Level Architecture

```mermaid
graph TD
    subgraph Clients["Frontend Clients (React + TS)"]
        C1[Player 1 UI<br/>Charts + Orders + TB/IP + Chat]
        C2[Player 2 UI<br/>Symmetric]
        Voice[WebRTC or 3rd-party Voice]
    end

    subgraph Backend["Backend (Python/FastAPI recommended)"]
        WS[WebSocket Gateway<br/>Match Rooms + Auth]
        Sim[Simulation Engine<br/>SharedClock + TB Resolver + Order Exec + Ability Resolver]
        State[In-Memory Match State<br/>Players, Positions, Orders, Resources, Arena Data]
        Matchmaker[Matchmaking / Lobby Service]
    end

    subgraph DataLayer["Data & Storage"]
        ArenaDB[(Pre-fetched Arenas<br/>Parquet/CSV/SQLite + Metadata)]
        UserDB[(Postgres: Users, History, Replays)]
        Cache[(Redis: Pub/Sub, Temp State, Matchmaking Queues)]
    end

    subgraph External["External / Voice"]
        VoiceProv[3rd-party Voice (optional)<br/>Twilio/Agora]
        DataSrc[yfinance / Stooq / EODHD<br/>One-time Fetch Scripts]
    end

    C1 <-->|Actions: order, TB, IP spend, chat| WS
    C2 <-->|Actions| WS
    Voice <--> C1 & C2
    WS --> Sim
    Sim --> State
    State --> ArenaDB
    WS <--> Cache
    Matchmaker <--> Cache
    DataSrc --> ArenaDB
    Sim --> UserDB
    Voice <-->|Signaling| WS
    VoiceProv -.-> Voice
```

**Core Flow (Match Lifecycle)**:
1. Lobby/Matchmaking → Private or quickplay room created.
2. Match start: Server selects pre-loaded arena slice → normalizes (or pre-normalized) → loads into memory → broadcasts initial state + generic labels.
3. Game loop (server-driven, real-time or fixed tick): Advance shared `T` at `R`; process queued actions; execute orders/P&L; apply sabotage; update resources; broadcast deltas/state snapshots.
4. End (real-time 5:00): Compute final equity → persist replay log → reveal details (optional post-match).
5. Replay: Server replays from log or re-sim with full visibility.

**Communication**: Bidirectional WebSockets for low-latency sync of clock, bars, orders, resources, events. JSON or compact binary (e.g., msgpack) payloads. Deltas preferred over full snapshots for bandwidth.

---

## 2. Realtime Multiplayer Sync

**Recommendation**: **Authoritative server + WebSockets**. Clients send *inputs/actions only* (e.g., "place limit order at X on instrument Y", "set TB to FFx3", "cast sabotage Z"). Server owns simulation, validates, advances state, and broadcasts authoritative updates.

**Why Authoritative?**
- Supports contested shared clock (R resolution server-side).
- Sabotage/IP effects applied deterministically server-side.
- Prevents client cheating on P&L, orders, or clock.
- Matches specs (server simulation of state/P&L/orders).

**Shared Clock & Sync**:
- Server maintains `T` (float/int) and `R` (contested via TB rules: Pause=0 override, max(FF) with all payers consuming).
- Clients receive periodic state broadcasts: current `T`, active `R`, new/updated bars (OHLC deltas or full recent window), equity curves, open orders/positions, resource levels, events (fills, sabotage notifications).
- Clients render locally but treat server state as truth (interpolate visuals for smoothness).
- Tick model: Real-time driven (align to wall clock for 1s=1day base) or fixed sim ticks (e.g., 10-60Hz internal). Broadcast at ~10-20Hz or on significant events for MVP.
- Latency handling: Server timestamps actions; clients buffer/predict conservatively (orders resolve on server at bar advance). No heavy client prediction needed for pure replay sim vs. physics-heavy games.
- Desync mitigation: Deterministic engine (same arena + same action sequence = same state). Full state snapshots periodically or on reconnect. Heartbeats + reconnect logic.

**Alternatives Considered**:
- Client-authoritative or P2P: Rejected — violates fairness/contested mechanics and anti-cheat.
- Lockstep (deterministic lockstep): Overkill for variable R; adds complexity for resource contention.
- WebTransport (UDP-like): Promising future (lower latency than WS in lossy conditions per research), but WebSockets sufficient and more mature for MVP (broad browser support).

**Rooms**: Per-match isolated state. Broadcast to room participants only. Scale with pub/sub (Redis) later.

---

## 3. Data Pipeline & Storage for Historical Daily Bars

**Sources (per research)**: Primary **yfinance** (Python, easy bulk, decades for ^GSPC/^DJI/^IXIC + majors FX like EURUSD=X) or **Stooq** (free bulk ZIPs, no signup, world coverage). EODHD for paid global depth. FRED/others as supplements. Avoid live APIs mid-match.

**Pipeline Stages** (one-time or scheduled pre-fetch):
1. **Fetch**: Script (e.g., `scripts/fetch_arenas.py`) pulls full ranges per instrument (decades preferred). Pandas DataFrames.
2. **Clean/Normalize Prep**: Align dates across instruments. Skip/interpolate non-trading days consistently. Compute daily returns. Store raw + metadata (instrument, date range, vol profile for arena selection).
3. **Arena Curation**: Pre-select "maps" — contiguous slices representing regimes (trending, volatile, range-bound, crisis). Store as Parquet (efficient columnar, compressed, fast load) or SQLite/CSV. Each arena: list of instruments + aligned bar sequences (date offsets from T=0, OHLC or just closes + returns).
4. **Per-Match Load**: On match start, server loads chosen arena slice into memory (numpy/pandas arrays or simple lists; ~300-2000 bars tiny). Apply final normalization (P[0]=100 for all series; generic labels like "Broad Equities").
5. **Serving During Match**: Simulation engine indexes into pre-loaded array by integer `T`. New bars emitted on `T` advance. No external I/O. Volume optional (often 0 for indices).
6. **Updates/Refresh**: Periodic re-fetch for recent data; versioned arenas.

**Storage Recommendations**:
- **Primary for replay**: Parquet files (partitioned by arena or instrument) or in-memory on load. Fast sequential access.
- **Metadata/DB**: Postgres or SQLite for arena catalog (ID, instruments, start/end simulated days, characteristics for selection).
- **Alternatives**: HDF5/Feather for speed; simple JSON arrays for MVP prototyping. Avoid heavy TSDB (Influx etc.) unless scaling to intraday/future analytics.
- **Size**: Negligible for daily (thousands of instruments × decades still MBs compressed).

**Arena Selection**: Server-side (random or player prefs for private lobbies). Private per-match (no client exposure of real dates/symbols during play). Post-match reveal optional.

**Intraday Future**: Aggregate from tick sources (HistData/Stooq) or switch to higher-res providers; current daily sufficient per vision.

**Determinism**: Critical — same slice → identical replay sequence. Tests for identical output across "players".

---

## 4. Backend Requirements

**Core Components**:
- **Simulation Engine**: 
  - `SharedClock` / `TempoBar` resolver (exact rates from spec: base R=1, TB recharge +1/s, Pause bonus +4/s, FF costs 2/5/12 per real-s).
  - Bar applicator: On integer `T` cross, reveal bar, mark-to-market all positions, trigger orders (market immediate; limit/stop on price cross at bar).
  - P&L: Unrealized continuous; realized on close. Equity = 100 units + P&L. Supports Long/Short.
  - Order Engine: Market/Limit/Stop + attached SL/TP. Modifiable/cancelable. Execution vs. current bar price (minor base spread).
- **State Management**: In-memory per-room (dict keyed by match_id). Player sub-states: positions (dict instr → size/dir), pending orders, TB (0-100), IP (start 50, regen +0.5/s + P&L grants), visible feeds, cooldowns.
- **Ability/IP Resolver**: Validate cost/cooldown/IP, apply effects (e.g., delete SLs from opponent's order list; widen spreads on future fills for X real-s; plant fake news event in victim's feed only), queue victim notifications.
- **Event System**: Hooks/callbacks for new bar, fill, sabotage, resource change, match end. Feeds into WS broadcasts.
- **Match Lifecycle**: Start (load arena, init states), Run loop (advance real-time or tick-driven), End (score, persist), Cleanup.

**Tech Choices**:
- **Python + FastAPI (or Starlette) + Uvicorn**: Strong fit (native WS support, async for I/O, Pydantic models, easy integration with pandas/yfinance for data). Use `websockets` lib or built-in.
  - Pros: Excellent data ecosystem (matches research), rapid dev for sim logic, type safety.
  - Cons: Python GIL (mitigate with async or multiprocessing per room for CPU-bound sims; low load for 1v1 MVP). Slightly higher latency vs. Node/Go in extreme scale.
- **Alternatives**:
  - **Node.js + ws/Socket.io or uWebSockets.js**: Better raw WS throughput/event-loop for high-concurrency I/O. Weaker native data tools (use JS libs or call Python microservice for data).
  - **Go or Rust (e.g., Tokio + Axum)**: High perf for sim + WS; deterministic lockstep easier. Steeper for finance data.
  - **Hybrid**: Python for data prep/serving + lightweight game server (or Colyseus/Photon for rooms if not building custom).
- **Supporting**: Redis (pub/sub for multi-server broadcast, matchmaking queues, temp state with TTL). Postgres for persistence (users, match history, replay metadata). Celery or background tasks for replay generation.
- **Sim Tick**: Align to real wall time for pacing. Internal deterministic updates faster if needed. Broadcast frequency tuned for responsiveness vs. bandwidth (e.g., full state every 500ms + events).

**Persistence**: Action log + initial arena ID + final state for replays (JSON or binary). Full bar data replayable from log.

---

## 5. Frontend/UI Considerations

**Stack Recommendation**: **React + TypeScript + Vite**. Modern, component-friendly for complex UI, excellent WS libs (e.g., `react-use-websocket` or native + Zustand/Redux Toolkit for state).

**Key UI Elements & Live Updates**:
- **Charts**: TradingView **Lightweight Charts** (top rec — tiny ~35-45KB, Canvas, excellent realtime `series.update()`, candlestick + volume, multiple panes, indicators hooks, streaming demos). Supports loading large historical + live appends perfectly. Alternatives: Custom Canvas/WebGL (D3/finplot-like or Chart.js) for full control; avoid heavy full TradingView library (licensing/cost).

**Deepened LW Replay (from sub 019f0577)**: Preload norm data (setData init); update() for deltas/stream (server T or R-scaled timer). Sync: timeScale visibleLogicalRange subs for multi-symbol/scrub/FF. Overlays: markers for trades, priceLines for levels, parallel series for equity. React: refs for live updates from WS/timer. Recs/pitfalls/sources in RESEARCH_STATUS LW dive. Suggested: ReplayController + Mermaid in full docs.
  - Multiple synced charts (core instruments). Live bar append as `T` advances. Zoom/pan with shared time axis (server `T` drives visible window).

**LW Replay Controller Details (added 2026-06-26 15m review, per LW sub 019f058c + official tutorials)**:
- **ReplayController (custom hook/component)**: Use React useEffect + setInterval (or requestAnimationFrame) scaled by R. Example: `const interval = setInterval(() => { /* advance or follow server T */ chart.timeScale().setVisibleLogicalRange(aroundCurrentT); series.update(newBar); rebuildMarkersAndPriceLines(); }, baseMs / R);`. On pause (R=0): clearInterval/freeze. On FF/scrub: adjust interval or set range directly. Server drives authoritative T/R via deltas; client follows + smooths.
- **Logical Range Sync**: `timeScale.subscribeVisibleLogicalRangeChange(range => { slaveChart.timeScale().setVisibleLogicalRange(range); });` (master/slave to avoid loops). Supports fractional for precise scrub/FF around T index. `fitContent()`, `setVisibleLogicalRange({from, to})`.
- **Overlays Implementation**:
  - Markers (orders/entries/exits): `createSeriesMarkers(series, markersArray)` or `setMarkers`. Rebuild array on changes (full replace). `{time, position: 'aboveBar'|'belowBar'|'inBar', shape, color, text}`.
  - PriceLines (SL/TP/levels): `series.createPriceLine({price, color, lineWidth, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title})`. Update with `applyOptions()`, remove via series.
  - Equity: Parallel Line/Area series (same chart or separate priceScaleId). `equitySeries.update({time, value: currentEquity})`.
- **Delta Types for WS (client consumes from task-005)**: BarDelta (new/updated OHLC), ResourceDelta {T, R, TB_level, influencers?}, OrderDelta (list or diff for open orders -> markers/priceLines), EquityDelta, EventDelta (fills, sabotage notifs, news). Snapshot on join/reconnect; deltas for streaming.

**LW ReplayController Flow (Mermaid from LW sub research + official time-scale docs)**:
```mermaid
graph TD
    WS[WS Deltas: T/R/BarDelta from task-005] --> RC[ReplayController<br/>React useEffect + scaled setInterval<br/>or follow server T]
    RC -->|R > 0| Timer[intervalMs = base / R<br/>advance or set range]
    RC -->|R == 0 / pause| Freeze[clearInterval / freeze visuals]
    Timer --> Sync[timeScale.setVisibleLogicalRange<br/>around current T<br/>master/slave for multi-chart]
    Timer --> Update[series.update(bar)<br/>for streaming deltas]
    Sync --> Overlays[rebuild markers/priceLines<br/>equitySeries.update]
    Update --> Overlays
    Overlays --> Chart[LW Chart render]
    WS --> Snapshot[on join/reconnect:<br/>full state + initial setData]
```
Pitfalls: Avoid setData for live (use update); master/slave guards for loops; no extrapolation on ranges; use Decimal in sim for determinism cross-ref. Sources: LW docs time-scale + realtime examples; sub 019f0577/019f058c. Ready for task-007.
- **React/TS Lifecycle**: `useRef<IChartApi>(null); useRef<ISeriesApi>(null); useEffect(() => { const chart = createChart(...); series = chart.addCandlestickSeries(...); series.setData(initialNorm); /* subs */ return () => chart.remove(); }, []);` WS onmessage: if (refs.current) { series.update(bar); updateOverlaysFromState(); }. Use forwardRef/Context for <SyncedChart> composables. Cleanup listeners.
- **Mermaid Flow (timer/WS - expanded from LW sub 019f058c + 019f0577 for full ReplayController)**:
```mermaid
graph TD
    subgraph Server["Server (task-005)"]
        S1[Advance T @ R<br/>TB resolver]
        S2[Process actions: orders/TB/IP/sabo]
        S3[Broadcast deltas: T/R/Bar/Equity/Order/Event]
    end
    S1 --> S2
    S2 --> S3
    S3 -->|WS deltas| WS[WS Room Handler<br/>task-005]
    WS --> C[Client WS onmessage]
    C --> RC[ReplayController<br/>useEffect + setInterval/raf<br/>scaled by R baseMs/R]
    RC -->|pause R=0| Clear[clearInterval<br/>freeze]
    RC -->|FF/scrub| Range[setVisibleLogicalRange<br/>{from: T-w, to: T+o}]
    RC --> Update[series.update(newBar)]
    Update --> Over[rebuildMarkers<br/>applyOptions PriceLines<br/>equitySeries.update]
    UI[UI Inputs: TB buttons/scrub<br/>Order place] -.->|send action| WS
    subgraph React["React Lifecycle"]
        Refs[useRef chart/series<br/>useEffect create/setData/cleanup chart.remove]
    end
    Refs --> RC
```
- **Pitfalls (confirmed from LW sub)**: update() only for latest (use setData for inserts); master/slave for sync to avoid loops; full marker replace on changes; ref leaks (strict cleanup + unsub); no extrapolation on ranges; server T truth + conservative client (no heavy pred).

**Data Pipeline Deepen (from completed data sub 019f05e3 + recs)**: Expand §3 with: Parquet best practices (pyarrow, partition, compression snappy/zstd for time-series OHLC); yfinance/Stooq fetch+clean; pandas_market_calendars for non-trading; norm+hash+generic; regime curation (rolling/vol or clustering); server-only loader; anti-cheat via private+norm+mystery; determinism (arena hash + log re-sim); pitfalls (float->Decimal, align); integration 001/005. See task-006 notes + sub transcript for sketches. Add to storage recs: metadata registry with content_hash for verify_replay.
- **Handoff**: See full in scratch/sub_lw_controller_20260626.txt + RESEARCH_STATUS LW dive + official realtime-updates + react/advanced. Follow exactly for task-007 SyncedChart + useReplayController. Expand as needed in impl.
- **Expanded from LW research**: Includes full delta flow, overlay rebuild, UI feedback loop, R scaling for pause/FF/scrub. Matches task-007 ACs and arch sync needs.
- Open Qs (note in arch): Client scrub sends action? Smoothing lerp for R? Current-T indicator plugin/marker? Equity separate pane?

Multiple synced charts (core instruments). Live bar append as `T` advances. Zoom/pan with shared time axis (server `T` drives visible window).
- **Resource Bars**: SVG or progress + animated (TB fill color by influence; IP numeric + regen indicator). Clear costs/tooltips for actions.
- **Order Panels**: Form (type, instr, size, price, SL/TP attach) + "place on chart" clicks (crosshair price capture). Live open orders list with modify/cancel. Portfolio/equity curve mini-chart.
- **Notifications**: Toasts/banners for fills, sabotage ("Your SLs deleted at T=XXX"), fake news, events. Timestamped log.
- **Tempo Controls**: Buttons/hotkeys for Pause/FF levels (visual "who is influencing" if spec allows or anonymous).
- **Chat**: Text textarea + log (persistent, match-scoped). Voice controls (mute, PTT, volume per player).
- **Other**: Opponent high-level status (fog? equity % delta), news feed (base flags + peek reveals), timer (real + sim T), arena name/generic.
- **State Sync**: Subscribe on connect → receive initial + deltas. Optimistic UI for own actions (reconcile on server confirm). Error handling for rejections (e.g., insufficient IP).
- **Performance**: Throttle renders; virtualize lists; efficient chart data (typed arrays if custom).

**Voice Chat Integration**:
- **Text First (MVP priority)**: Simple WS-broadcast chat.
- **Voice Options**:
  - **WebRTC (P2P recommended for 1v1)**: Native browser (getUserMedia + RTCPeerConnection). Low latency/cost. Signaling via existing WS (offer/answer/ICE via match room). Push-to-talk, per-player mute/volume. Pros: Free, direct, private. Cons: NAT traversal (STUN/TURN needed; fallback TURN server costs bandwidth); setup complexity; 1:1 easier than groups.
  - **Third-party**: Twilio Video/Voice, Agora RTC, 100ms, or MirrorFly. Easy SDKs (JS/React), built-in SFU/MCU for quality/scaling, recording, noise suppression. Pros: Reliable, features, global infra. Cons: Per-minute costs (scales with usage); vendor lock.
  - **Hybrid/Other**: Discord SDK (if community integration) or embed; avoid pure Discord for in-game seamlessness. Self-hosted SFU (e.g., LiveKit, Mediasoup) for control.
- **Requirements (per spec)**: <150ms target, reliable on match join, easy controls, text fallback. Opt-in post-match logs.
- **Integration**: Start with text + WebRTC signaling skeleton. Add provider if P2P flaky.

**Other**: Responsive (desktop primary; mobile stretch). Accessibility (ARIA, high contrast). Theming for "fight" feel (tension indicators).

---

## 6. Anti-Cheat & Fairness Tech

**Core from Specs**:
- **Normalization + Private Arenas**: Server chooses/pre-loads slice; clients see only normalized % from 100 + generic labels. "I know the real date" useless. Mystery/randomized start offsets.
- **Authoritative Server**: All P&L, fills, effects, clock computed server-side. Clients cannot fake actions or states.
- **Data Isolation**: Pre-fetched local/private storage. No client fetches or external APIs during match. Arena data served only as needed (or full preload).
- **Visibility Controls**: Sabotage always notifies victim (timestamped). Premium feeds/IP purchases private (asymmetry intended, not hidden from server).
- **Rate Limits & Validation**: Cooldowns, IP/TB costs enforced server-side. Action throttling. Order validation (no invalid prices/sizes).
- **Replay Analysis**: Full logs for post-match review, leaderboards, manual/automated cheat detection (unusual timing, perfect foresight patterns).
- **Additional**:
  - Deterministic sim + seeded RNG (if any randomness).
  - Server-side only news/events tied to arena.
  - Optional: Slight randomization of news timing or arena variants.
  - Client integrity: Obfuscation/minification; but focus server-side (harder to cheat sim).
  - Behavior: Detect bots via input patterns (future).

**Fairness**: Same data + same start conditions. Resource economy rewards good trading (IP from P&L).

---

## 7. Scalability: MVP (1v1) vs Later (Tournaments)

**MVP (1v1, small concurrent matches)**:
- Single server instance (FastAPI + in-memory rooms).
- WebSocket connections per player (~2 per match).
- Data arenas pre-loaded or lazy from FS/DB.
- Simple matchmaking (queue or direct invite).
- Low resource: Hundreds of simultaneous 1v1 feasible on modest VPS.
- Replays: Local file storage or DB blobs.

**Growth Path (Multiplayer/Tournaments)**:
- **Horizontal**: Multiple WS/gateway servers behind load balancer (HAProxy/NGINX). Redis Pub/Sub for cross-server broadcast and shared queues (matchmaking, room state).
- **Dedicated Services**: 
  - Matchmaking service (Redis sorted sets for queues by MMR/Elo/bucket).
  - Game sim servers (stateless or stateful rooms; spin per match or pooled).
  - Data service (arena loader/cache).
- **State**: Redis for ephemeral (active matches, TB/IP snapshots); Postgres for durable (history, users, replay metadata).
- **Tournaments**: Bracket service; spectator mode (read-only WS subscriptions to match rooms); best-of series scoring.
- **Infra**: Containerized (Docker/K8s). Cloud: Fly.io/Render (easy WS), AWS (ECS/Lambda+API GW WS, ElastiCache Redis), or self-hosted.
- **Limits**: Start with in-memory; shard by region or match type. Monitor WS connection counts, broadcast volume.
- **Later Features**: Spectators, leaderboards (Elo), custom lobbies, progression (persistent IP/TB unlocks?).

**Bandwidth/Perf**: Compact payloads. Charts update incrementally. For N matches, O(N) broadcasts.

---

## 8. Tech Stack Recommendations

**Primary Recommendation: Python (FastAPI/Starlette + asyncio) Backend + React (TS) Frontend + Lightweight Charts**.

**Pros (aligns with research/data needs + realtime)**:
- Python: Seamless yfinance/Stooq/pandas/Parquet integration for pipeline + sim (bar arrays). FastAPI WS mature + examples for rooms/broadcast. Async perfect for I/O (DB, WS). Rich ecosystem.
- React: Mature realtime patterns (hooks + state mgmt), component reuse for panels/charts/notifs. Lightweight Charts native JS/TS integration.
- Overall: Rapid iteration for hackathon/MVP feel. Strong for historical replay determinism.
- Voice: WebRTC native or easy SDKs.

**Cons & Tradeoffs**:
- Python WS/sim: Acceptable for 1v1 (low CPU); may need process-per-room or Rust core for high-scale tournaments. Node often edges pure WS perf.
- Realtime + Replay: Excellent (preloaded data in mem + deterministic Python sim). Historical replay simpler than live market sync (no external variance).
- Alternatives:
  - **Node.js full-stack**: Faster WS (ws/uws), unified JS. Data: Use `node-fetch` or microservice for Python data. Good if frontend-heavy.
  - **Go backend**: Superior concurrency/perf for sim + many rooms. Pair with React FE.
  - **Full game engine (Unity/Unreal headless + Photon/Colyseus/Nakama)**: Overkill for 2D charts; adds complexity but provides battle-tested rooms/physics (not needed here). Nakama or custom for custom sim.
  - **Electron desktop**: If native perf/charts needed; web-first for accessibility/voice.
- **Data/Replay Specific**: Parquet + pandas (or polars for speed) shines in Python. Replay engine easy to make deterministic. Live updating charts via incremental WS updates + LW Charts streaming = low friction.
- **Other Tools**: Tailwind + shadcn for UI; Zustand for lightweight state; Supabase/Auth0 for users (optional); Docker for deploys.

**MVP Minimal**: FastAPI (WS + REST for lobbies), React, in-memory sim + Parquet arenas, native browser WS + basic WebRTC text fallback.

---

## 9. Potential Pitfalls & Open Tech Questions

**Pitfalls**:
- **Clock/Desync**: Variable R + latency → clients see staggered bars. Mitigate with server T authoritative + client smoothing/interpolation. Test extensively with simulated lag.
- **Determinism**: Floating point, order of operations, non-trading day handling. Enforce identical code paths + tests (same inputs → bitwise-identical states).
- **Bandwidth/Latency for Charts**: Sending full OHLC every bar vs. deltas. LW Charts handles streaming well but tune payload size.
- **Voice NAT/Quality**: WebRTC P2P fails behind strict firewalls (need TURN relays → cost/latency). Test cross-network.
- **Resource Contention UI**: Clear "who controls R" feedback or risk confusion/frustration.
- **Cheat Vectors**: External lookups (mitigated); script bots (rate limits + anomaly detection); data leaks (private arenas).
- **Replay Bloat/Storage**: Log every action + bar? Compress or snapshot periodically.
- **Scalability Trap**: In-memory rooms work for MVP but forget Redis early → painful refactor.
- **Balance vs. Tech**: Sabotage costs tuned in spec but sim fidelity (bar OHLC vs. intra-bar) affects fills.
- **Legal/Hosting**: Historical data terms (personal use ok per sources); avoid real-money until regs clear.

**Open Tech Questions** (prioritize before impl):
1. Exact internal sim tick rate vs. broadcast rate? (e.g., 60Hz sim, 10Hz net?)
2. Client-side prediction/optimism level for orders and tempo (to hide latency)?
3. Data format for arena slices (full OHLC arrays vs. returns-only + base price)? Volume handling?
4. Voice signaling details + TURN server choice (self-hosted vs. provider)?
5. Replay format: full event log + arena vs. video export vs. state snapshots for scrubber?
6. Multi-server state sync strategy (Redis JSON vs. dedicated game servers)?
7. Edge cases for shared R contention (simultaneous Pause + FF; fractional T triggers)?
8. How to handle reconnects mid-match (catch-up snapshot + catch missed bars)?
9. Intraday bars viability and impact on engine (higher fidelity vs. perf)?
10. Monetization hooks (e.g., cosmetic abilities) — any backend implications early?

---

## 10. Phased Implementation Alignment

Aligns with existing cursor-tasks and specs:
See docs/cursor-tasks/TASK_MANIFEST.md for the canonical 8 tasks and mapping.
Core sim uses 002 (time/tempo), 003 (IP/sabotage), 004 (orders), 005 (realtime). Next: full WS, UI, voice (008), replays, matchmaking, persistence.

**MVP Deliverable Path**: Data load → Deterministic shared clock + TB → Basic orders/P&L → IP/abilities → WS multiplayer rooms → React UI + charts → Voice text-first + WebRTC → Polish + anti-cheat tests.

This architecture enables the "contested time + sabotage + psych" fantasy while being simple to start and extensible.

---

**Key Findings Summary** (from research + specs):
- Historical replay + normalization is battle-tested for fairness (ChartChamps, FXR, Trade Bots).
- Authoritative WS + server sim is standard and fits perfectly (many multiplayer game architectures).
- Lightweight Charts + FastAPI WS is a low-friction, high-perf combo for this exact use case (realtime financial viz + game sync).
- WebRTC viable for 1v1 voice; third-party for speed-to-market.
- In-memory + Redis pub/sub scales MVP to moderate load easily.
- Biggest risks: determinism/clock sync and voice reliability — address in early prototypes.

**References**: GDD.md, game-mechanics-spec.md, historical_data_sources_research.md, chart-fights-research-notes.md, data-sources-initial.md, cursor tasks, web research on WS architectures, LW Charts, WebRTC, data storage (Parquet/SQLite common for financial replay), authoritative server patterns.

Save this as primary tech reference. Update as prototypes validate assumptions.
