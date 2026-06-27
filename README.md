# chart-fights
1v1 me in stocks bro — historical daily OHLC PvP with MOBA Tempo Bar / IP, sabotage, voice.

## Current Status (impl started)
- **Data**: 1656 normalized daily arenas (P[0]=100, Parquet) generated from 50+ tickers ~10y history via `scripts/fetch_historical_data.py`. Ready for 1000s of matches. Stored locally in `data/arenas/`.
- **Design**: Full GDD + 8 Cursor tasks in `docs/`. See GDD.md for vision, mechanics (TB +1/4s pause, IP, sabo), arch.
- **Frontend**: Next.js in `frontend/` (Vercel). LW Charts + basic ReplayController skeleton (agent working on full UI per task-007/GDD).
- **Backend**: FastAPI stub in `backend/` (Fly.io). WS, arena loader from Parquet, basic authoritative sim/tick, action stubs (TB/IP accrual, Decimal). Matches design tasks 004/006.
- **Deployment**:
  - Frontend: Vercel (npx vercel or connect repo). `frontend/vercel.json`.
  - Backend: Fly.io (`cd backend; fly deploy`). Includes Dockerfile, fly.toml (WS on 8000, auto scale).
  - Data: Pre-gen Parquet baked/volume. Script for refresh.
  - Voice: WS signaling in backend + client WebRTC. Coturn on separate Fly machine or managed (low cost).
  - DB/Logs: Start in-mem for MVP. Add Vercel Postgres or Supabase for matches/users. Fly volumes for logs if needed.
- Next: Wire FE<->BE WS, full mech (sabo effects, PnL), voice P2P, anti-cheat re-sim, lobby with real arenas, deploy.

## Quick Start (local)
```bash
# Data (already run)
cd Documents/Github/chart-fights
python scripts/fetch_historical_data.py  # if re-run (see below for 1000s of games)

# Frontend
cd frontend
npm install
npm run dev

# Backend (new terminal)
cd backend
python -m venv venv && source venv/bin/activate  # or .venv ; on Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000  # run from backend/ ; single process (--workers 1)
```

Open http://localhost:3000 , connect WS to ws://localhost:8000/ws/<match>

See docs/ for full Cursor handoff tasks, architecture, GDD.

## Running Data Pipeline for 1000s of Real Historical Games
The core of enabling thousands of fair, replayable, anti-cheat protected matches is the pre-generated normalized arenas (real US stock daily OHLC slices from history, P[0]=100, private server-side only, generic labels).

Run from repo root (requires internet for fetch):
```bash
# Install (once)
pip install yfinance pandas pyarrow   # yfinance primary; stooq uses pandas only

# Full generation (produces 1000-2000+ arenas; ~5-15min; uses ~50-60 tickers x ~10y)
python scripts/fetch_historical_data.py
# or alt source:
python scripts/fetch_historical_data.py --source stooq

# Test / validate without heavy run or writes:
python scripts/fetch_historical_data.py --test --dry-run
# Quick real small test set (writes ~100 arenas from 5 tickers):
python scripts/fetch_historical_data.py --test

# Customize slices (200-300 bars example):
python scripts/fetch_historical_data.py --window 220 --step 50
```

- Output: `data/arenas/*.parquet` + `data/arenas_index.json` (local only; commit index if desired, arenas are bulk).
- How it enables 1000s of games: 55+ stocks * ~30 slices each = 1600+ unique contiguous historical periods (bull, bear, chop, vol from 2014-2026). Each match loads one by id, normalizes (idempotent), uses generic label (e.g. "Asset AAPL"), computes hash for verify. Server randomly selects from index for quickplay/private; never leaks real dates/tickers to clients mid-game. Supports re-sim for anti-cheat (see task-001, backend/app/arena.py + sim/engine.py). Re-run periodically to add recent data.
- Robustness: retries/backoff/jitter, validation, handles partial histories, cross-platform paths, local storage (no DB needed).
- Per task-006 + GDD + arch: one-time bulk (yfinance/Stooq), Parquet, no mid-match external calls.
- After regen: restart backend (it hot-loads on arena requests); frontend samples are illustrative only.

See `scripts/fetch_historical_data.py` header + `docs/cursor-tasks/task-006-data-pipeline.md` + `docs/design/GDD.md` (data section) for full spec.

## Deploy
- Vercel: Import repo, set frontend/ as root or monorepo.
- Fly: `fly launch` in backend/, set secrets.
- Voice: Deploy Coturn separately if needed.
- Scale: Arenas static, sim stateless-ish (add Redis for rooms).

Architect notes: Separate FE/BE for WS/long lived. Pre-gen data for perf (no live scrape in prod). Use Decimal everywhere. Test determinism with log re-sim.

1v1 me in stocks bro. Use design spec. Max agents for parallel (data, FE, BE, deploy).
