# Deployment Guide for Chart-Fights

## Overview (per architect notes)
- **Frontend**: Next.js → **Vercel** (static + client WS). Fast deploys, free tier great.
- **Backend**: FastAPI → **Fly.io** machine (WS support, Docker). Handles sim, arenas, voice signaling.
- **Data**: Pre-generated 1656+ normalized daily arenas (Parquet). ~ small size. Include in image or Fly volume. Script for refresh.
- **Voice**: WebRTC P2P (client) + signaling in backend. Optional Coturn TURN on separate Fly (cheap) or managed.
- **DB/Logs**: MVP in-memory. Add Supabase/Postgres (Vercel) for users/matches history. Fly volumes for persistent if needed.
- Scale: Arenas static. Matches short (5min). Stateless sim possible with log replay.

## Local Dev
```bash
# 1. Data (already generated 1656 arenas)
cd Documents/Github/chart-fights
# python scripts/fetch_historical_data.py  # re-run if needed

# 2. Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload   # or python main.py

# 3. Frontend (new shell)
cd frontend
npm install
npm run dev
```

- Open http://localhost:3000
- Start match → should connect WS (update URL in code if port diff).
- Sabo/TB actions send to backend.

## Vercel (Frontend)
1. `vercel` or GitHub import → root `frontend/`.
2. Set env: `NEXT_PUBLIC_WS_URL=wss://your-app.fly.dev/ws`
3. `vercel.json` already has framework + region.
4. Data: arenas not in FE; fetch from backend `/arenas`.

## Fly.io (Backend)
```bash
cd backend
fly launch  # or fly deploy if app exists
# Follow prompts. App name e.g. chart-fights-be
fly secrets set ... (if any)
```

- `Dockerfile` + `fly.toml` configured (port 8000, WS, min machines).
- Data: COPY data/ in Dockerfile if small, or `fly volumes` + mount, or pre-download in entry.
- Update `NEXT_PUBLIC_WS_URL` in Vercel to wss://your-app.fly.dev

Example Dockerfile addition for data:
```
COPY ../data /app/data
```

Or script in container to fetch if dynamic.

## Voice (Coturn)
- Deploy coturn as separate Fly app (turnserver).
- Or use free STUN + paid TURN initially.
- Client config in frontend for iceServers.

## Data Refresh / 1000s Games
- `python scripts/fetch_historical_data.py` generates more arenas (edit TICKERS/WINDOW in script).
- For prod: run at deploy, store in S3/volume, backend serves list + parquet bytes or paths.
- Games: each match picks one arena_id. 1656+ ready for variety.

## Other
- Anti-cheat: content_hash in loader, log in engine.
- Determinism: engine uses real bars + Decimal.
- Logs: Fly has them; add struct logging.
- DB: later - Postgres for match history, users.

See GDD.md, docs/ for full spec.
Update WS URL, test end-to-end before prod.
Vercel + Fly combo gives good DX + WS support.
