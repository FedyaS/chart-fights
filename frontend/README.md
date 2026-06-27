This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://github.com/vercel/next.js/tree/canary/packages/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

## Chart-Fights MVP Skeleton (per task-007 + GDD + LW Replay research)

- Next.js 16 + TS + Tailwind + lightweight-charts ^5
- ReplayController hook (src/hooks/useReplayController.ts): series.update() for deltas, setData only preload, timeScale.setVisibleLogicalRange for replay, markers (createSeriesMarkers), priceLines, R-scaled play/pause/speed timer.
- Basic UI (app/page.tsx + components/): Lobby (select 3 hardcoded normalized arenas from data/arenas samples), main candlestick chart, TB/IP resource bars + controls, Sabo buttons, Order panel stub, Voice stub, Event log.
- All actions are stubs that log + apply visual overlays (player markers/priceLines for sabo/orders).
- Responsive duel layout. No full backend logic/WS (yet). Deployment friendly (static prerender + client replay).
- Start: `npm run dev` then select arena → PLAY. Follows "update not setData", logical ranges exactly from research.

See docs/design/GDD.md , docs/cursor-tasks/task-007-frontend-streaming.md and architecture for full spec + next (WS, Zustand, full overlays).

Next Cursor steps: integrate real WS from task-005, add multi-chart sync, voice WebRTC stub wiring, server T follow, polish.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.

---

## chart-fights Specifics

**Run locally:**
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:3000

**Flow implemented (GDD lobby → match):**
- Lobby: Arena list + "Start Match" (mock quickplay).
- Match: Full GameUI with Tempo Bar (TB) controls, IP display + Sabo buttons (mock logs + costs), ReplayController (lightweight-charts), voice mic stub, player markers.

**ReplayController key:**
- Uses `createChart` + `addSeries(CandlestickSeries)`.
- `series.setData(...)` on init (normalized candles).
- `setVisibleLogicalRange` for playback advance.
- `series.update(...)` for live candle simulation.
- R-scaled `setInterval` (base / speed) + pause clears timer.

**Vercel deploy (SPA / static friendly):**
- Default Next.js on Vercel works perfectly (no special config needed).
- Provided `vercel.json` declares framework explicitly for clarity.
- All client-side (static export possible later via `next export` if backend decoupled).
- Push to GitHub + import on vercel.com or `vercel --prod`.

**Next for real integration:**
- Wire to backend WS (task-005 deltas for Bar/Resource/Order/Equity/Event).
- Load real normalized parquet arenas (task-006) via API.
- Full ReplayController sync + master/slave for multi-instrument.
- Voice WebRTC + sabo real effects.
- Orders + P&L panels (task-004).

See docs/design/GDD.md + docs/cursor-tasks/task-007-frontend-streaming.md + task-002.

