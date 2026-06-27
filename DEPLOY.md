# Deploying Chart-Fights

Two pieces, deployed separately:

| Piece | Stack | Host | What it serves |
|-------|-------|------|----------------|
| **Backend** | FastAPI + native WebSockets (Python 3.11) | **Fly.io** (Docker) | `/health`, `/arenas`, `/matches`, `/ws/{match_id}`, voice signaling. Ships the 1,710 normalized Parquet arenas inside the image. |
| **Frontend** | Next.js 16 + React 19 + TypeScript | **Vercel** | The game UI. Talks to the backend over HTTPS + WSS. |

> **Order matters: deploy the backend FIRST**, grab its public URL, set that URL as the
> frontend's `NEXT_PUBLIC_BACKEND_URL`, then deploy the frontend.

No API keys, database, or secrets are required. Match state is **in-memory**, so the
backend must run as a **single always-on machine** (see the note in `fly.toml`).

---

## Part 0 — Prerequisites & pre-flight (do this once)

1. Install the Fly CLI (`flyctl`) and log in: `fly auth login`.
2. Install the Vercel CLI (`npm i -g vercel`) **or** use the Vercel web dashboard (GitHub import).
3. **Commit your working tree.** Several game files are currently untracked/modified and
   are required for the builds. A Vercel deploy via Git will only include committed files.
   Make sure at least these are committed (they were previously untracked):
   - `frontend/src/lib/matchState.ts`  ← was being ignored by a `.gitignore` bug (now fixed)
   - `frontend/src/components/Scoreboard.tsx`, `frontend/src/components/EndScreen.tsx`
   - `frontend/src/hooks/useVoiceChat.ts`
   - the new `fly.toml`, `.dockerignore`, `frontend/.env.example`

   ```bash
   git add -A
   git status            # sanity-check that frontend/src/lib/matchState.ts is staged
   git commit -m "Add Fly/Vercel deploy config; fix lib/ gitignore"
   ```

---

## Part 1 — Backend → Fly.io

Run everything **from the repo root** (the directory that contains `fly.toml`), because the
Docker build context is the repo root so that both `backend/` and `data/` are copied into
the image (see `backend/Dockerfile`).

1. **Edit `fly.toml`** and choose your own values:
   - `app = "chart-fights-backend"` → a globally-unique name you own.
   - `primary_region = "iad"` → the region closest to your players (`fly platform regions` lists them).

2. **Create the app + machine** (this also does the first deploy). Because `fly.toml`
   already exists, use `fly launch` with `--copy-config` so it does **not** overwrite it,
   or just use `fly deploy` after creating the app:

   ```bash
   # Option A — one-shot create + deploy, reusing the committed fly.toml:
   fly launch --copy-config --no-deploy --name chart-fights-backend --region iad
   fly deploy

   # Option B — if the app already exists:
   fly deploy
   ```

   > Keep it to ONE machine. Do **not** run `fly scale count 2+`. `fly.toml` already sets
   > `min_machines_running = 1`, `auto_stop_machines = "off"`, `auto_start_machines = false`
   > so the single in-memory room server stays alive.

3. **Verify** it's up and healthy:

   ```bash
   fly status
   fly logs
   curl https://<your-app>.fly.dev/health     # -> {"status":"ok","matches":0}
   curl https://<your-app>.fly.dev/arenas      # -> {"arenas":[...],"total":1710}
   ```

4. **Copy the public URL**: `https://<your-app>.fly.dev`. You'll need it for the frontend.

The container listens on **port 8080** (`internal_port = 8080` in `fly.toml`,
`PORT=8080` + uvicorn `--port ${PORT:-8080}` in `backend/Dockerfile`). Fly terminates TLS and
forwards `:443 → :8080`, so `wss://<your-app>.fly.dev/ws/...` reaches the WebSocket endpoint.

---

## Part 2 — Frontend → Vercel

1. **Set the backend URL env var** to the Fly URL from Part 1, step 4. The app reads
   `NEXT_PUBLIC_BACKEND_URL` and derives the WebSocket URL by swapping `http→ws`
   (so `https://…` becomes `wss://…`). See `frontend/.env.example`.

   - **Vercel dashboard:** Project → Settings → Environment Variables →
     `NEXT_PUBLIC_BACKEND_URL = https://<your-app>.fly.dev` (Production, Preview, Development).
   - **Vercel CLI:**
     ```bash
     cd frontend
     vercel env add NEXT_PUBLIC_BACKEND_URL production
     # paste: https://<your-app>.fly.dev
     ```

2. **Set the Root Directory to `frontend/`.** This is a Vercel *project* setting, not part
   of `vercel.json`:
   - Dashboard (GitHub import): Project → Settings → **Root Directory** → `frontend`.
   - CLI: run the deploy from inside `frontend/` (below) so it becomes the project root.

   `frontend/vercel.json` already pins the framework to Next.js and the build/dev/install
   commands.

3. **Deploy:**

   ```bash
   cd frontend
   vercel          # first run links/creates the project (set root dir = . here)
   vercel --prod   # promote to production
   ```

   Or just push to the connected Git branch and let Vercel build automatically.

4. **Verify:** open the Vercel URL. The lobby footer/loading line shows the backend it's
   using; it should read your Fly URL (not `localhost`). If the backend is unreachable the
   app silently falls back to a local "offline practice" mode — so if you only ever see
   OFFLINE, the env var/URL is wrong.

---

## Part 3 — How two players start / join a match

1. **Player 1** opens the Vercel site, picks an arena in the lobby → this `POST`s `/matches`
   and connects to `wss://…/ws/{match_id}?player_id=p1`. A short **match id** is shown in the
   header.
2. Player 1 shares that match id with **Player 2**.
3. **Player 2** opens the same site → "Join an existing match" → paste the match id, choose
   **as p2**, click JOIN.
4. Both now share the same server-driven clock. The chart only reveals bars as the server
   advances time (anti-cheat: no future preload). Tempo (pause / 1× / ×2 / ×3 / ×5),
   orders, and sabotage all flow over the WebSocket.
5. **Voice:** click the mic in the Voice panel. It's browser-to-browser WebRTC (Google STUN),
   with offer/answer/ICE relayed through the backend WebSocket. It needs HTTPS/WSS, which
   Vercel + Fly provide automatically.

---

## Local dev (unchanged)

```bash
# Backend (listens on :8001 locally per app.main __main__)
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001

# Frontend (new shell)
cd frontend
echo NEXT_PUBLIC_BACKEND_URL=http://localhost:8001 > .env.local
npm install
npm run dev    # http://localhost:3000
```

To test the production Docker image locally (optional, from repo root):

```bash
docker build -t chart-fights-backend -f backend/Dockerfile .
docker run -p 8080:8080 chart-fights-backend
curl http://localhost:8080/health
```

---

## Remaining manual steps & caveats

- **Commit untracked files before deploying** (Part 0, step 3). The Vercel Git build only
  sees committed files. The previously-broken `.gitignore` `lib/` rule (which silently
  excluded `frontend/src/lib/matchState.ts`) has been fixed to `/lib/`, but you still must
  `git add` and commit that file.
- **Pick your own Fly app name and region** in `fly.toml`.
- **Single instance only.** Don't scale the Fly app to multiple machines — match state is
  in-memory and would be split/lost. If a machine restarts, in-flight matches are dropped
  (acceptable for 5-minute matches; persisting state would require a datastore — out of scope).
- **CORS** is currently wide open (`allow_origins=["*"]`) in `backend/app/main.py`. Fine for
  launch; tighten to your Vercel domain later if you want.
- **Voice on strict NATs:** the app uses STUN only. Most peer-to-peer connections work, but
  players behind symmetric NATs/corporate firewalls may fail to connect audio. If that
  happens, stand up a **TURN** server (e.g. `coturn` on a separate Fly app or a managed
  service) and add its `iceServers` config in `frontend/src/hooks/useVoiceChat.ts`.
- **Image size:** the 1,710 Parquet arenas (~`data/`) are baked into the backend image. The
  `.dockerignore` at the repo root keeps `frontend/`, docs, and caches out of the build
  context so builds stay fast.
