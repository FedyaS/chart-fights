"""FastAPI app for chart-fights realtime backend.
WS endpoint for match rooms. Authoritative clock bg task.
Per GDD, game-mech-spec, arch, task-005 etc.
"""
import uuid
import asyncio
import random
from typing import Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
from .arena import load_arena, get_available_arenas, load_arena_index
from .sim.engine import SimulationEngine, Action  # enhanced engine in sim/ per task focus; supports real arenas, submit_order, full deltas + content_hash
from .bot import BotTrader

MATCHES: Dict[str, SimulationEngine] = {}
CONNECTIONS: Dict[str, Dict[str, WebSocket]] = {}
ACTION_LOGS: Dict[str, list] = {}
MATCH_BOTS: Dict[str, str] = {}      # match_id -> bot player_id (for quick-match fallback)
BOT_DRIVERS: Dict[str, BotTrader] = {}  # match_id -> running BotTrader

app = FastAPI(title="chart-fights-backend", version="0.1-mvp")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateMatchReq(BaseModel):
    arena_id: str
    player_ids: list[str] | None = None


class CreateMatchResp(BaseModel):
    match_id: str
    arena_id: str
    arena_label: str
    arena_hash: str
    content_hash: str
    num_bars: int
    ws_url: str
    bot: bool = False           # quick-match vs-bot fallback flag


class QuickMatchReq(BaseModel):
    vs_bot: bool = True         # quick-match defaults to a bot opponent if no human joins


class ActionReq(BaseModel):
    player_id: str
    type: str
    payload: dict


@app.get("/health")
async def health():
    return {"status": "ok", "matches": len(MATCHES)}


@app.get("/arenas")
async def list_arenas():
    return {"arenas": get_available_arenas(12), "total": len(load_arena_index())}


def _new_match(arena_id: str, player_ids: list[str] | None, *, bot: bool = False) -> tuple[str, dict]:
    arena = load_arena(arena_id)
    match_id = str(uuid.uuid4())[:8]
    engine = SimulationEngine(match_id, arena_id)
    MATCHES[match_id] = engine
    CONNECTIONS[match_id] = {}
    ACTION_LOGS[match_id] = []
    for pid in (player_ids or ["p1", "p2"]):
        engine.state.add_player(pid)
    if bot:
        MATCH_BOTS[match_id] = "p2"  # p2 is a bot unless a real human takes the slot
    # Clock starts on first WS connect so HTTP/harness actions stay replayable from actions_log.
    async def bc(payload): await broadcast_to_room(match_id, payload)
    engine.set_broadcast(bc)
    return match_id, arena


@app.post("/matches", response_model=CreateMatchResp)
async def create_match(req: CreateMatchReq):
    try:
        match_id, arena = _new_match(req.arena_id, req.player_ids)
    except Exception as e:
        raise HTTPException(400, f"Invalid arena: {e}")
    # arena["id"] is the opaque ref (never the ticker-bearing real id) — safe to return.
    return CreateMatchResp(match_id=match_id, arena_id=arena["id"], arena_label=arena["label"], arena_hash=arena["hash"], content_hash=arena.get("content_hash", arena["hash"]), num_bars=arena["num_bars"], ws_url=f"/ws/{match_id}")


@app.post("/matches/quick", response_model=CreateMatchResp)
async def quick_match(req: QuickMatchReq | None = None):
    """Front-page Quick Match (#6): pick a random arena (varied regimes) and create
    a match. p2 is a bot unless a real second player joins before/while it plays."""
    req = req or QuickMatchReq()
    idx = load_arena_index()
    if not idx:
        raise HTTPException(500, "no arenas available")
    arena_id = random.choice(idx)["id"]
    match_id, arena = _new_match(arena_id, ["p1", "p2"], bot=req.vs_bot)
    return CreateMatchResp(match_id=match_id, arena_id=arena["id"], arena_label=arena["label"], arena_hash=arena["hash"], content_hash=arena.get("content_hash", arena["hash"]), num_bars=arena["num_bars"], ws_url=f"/ws/{match_id}", bot=req.vs_bot)


@app.get("/matches/{match_id}")
async def get_match(match_id: str):
    if match_id not in MATCHES: raise HTTPException(404)
    return {"match": MATCHES[match_id].get_snapshot(), "is_over": MATCHES[match_id].state.is_over()}


@app.websocket("/ws/{match_id}")
async def ws_match(websocket: WebSocket, match_id: str, player_id: str = "anon"):
    await websocket.accept()
    if match_id not in MATCHES:
        await websocket.send_json({"error": "no match"}); await websocket.close(); return
    eng = MATCHES[match_id]
    room = CONNECTIONS.setdefault(match_id, {})
    if player_id == "anon": player_id = f"p{len(room)+1}"
    # A real human taking the bot's slot cancels the bot fallback.
    if MATCH_BOTS.get(match_id) == player_id:
        MATCH_BOTS.pop(match_id, None)
        if match_id in BOT_DRIVERS:
            BOT_DRIVERS.pop(match_id).stop()
    eng.state.add_player(player_id)
    # Snapshot before room registration so bg-clock deltas cannot race ahead of it.
    # Redact opponent book (fog-of-war): you only see your own positions/orders.
    await websocket.send_json(_redact_for({"type": "snapshot", "state": eng.get_snapshot(), "you": player_id}, player_id))
    room[player_id] = websocket
    if eng._task is None:
        eng.start()
    # Spawn the bot opponent once the clock is live (quick-match fallback).
    bot_pid = MATCH_BOTS.get(match_id)
    if bot_pid and bot_pid != player_id and match_id not in BOT_DRIVERS:
        driver = BotTrader(eng, bot_pid)
        BOT_DRIVERS[match_id] = driver
        driver.start()
    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            at = msg.get("type", "action")
            if at == "action":
                pid = msg.get("player_id", player_id)
                action_type = msg.get("action_type", msg.get("type", "submit_order"))
                # normalize legacy 'order' to 'submit_order' for spec focus
                if action_type in ("order", "place_order"):
                    action_type = "submit_order"
                ok, r = eng.receive_action(pid, action_type, msg.get("payload", {}))
                ACTION_LOGS.setdefault(match_id, []).append({"player": pid, "type": action_type, "payload": msg.get("payload")})
                await websocket.send_json({"type": "ack", "ok": ok})
            elif at.startswith("voice_"):
                pid = msg.get("player_id", player_id)
                eng.receive_action(pid, at, msg.get("payload", {}))
                for op, ws in list(room.items()):
                    if op != pid:
                        try: await ws.send_json({"type": at, "from": pid, "payload": msg.get("payload")})
                        except: pass
    except WebSocketDisconnect:
        room.pop(player_id, None)


# Fields of a player's book that are private to that player (fog-of-war): the
# opponent only ever sees coarse ip/equity/tb, never exact positions/orders.
_PRIVATE_BOOK_FIELDS = ("positions", "orders", "realized_pnl", "unrealized_pnl", "buying_power", "exposure")


def _redact_for(payload: dict, viewer: str) -> dict:
    """Return a per-recipient copy of a delta/snapshot with other players' private
    book fields stripped, so a client can't read the opponent's exact positions."""
    if not isinstance(payload, dict):
        return payload
    # delta.resources[pid] and snapshot.state.players[pid]
    books = None
    if isinstance(payload.get("resources"), dict):
        books = payload["resources"]
    elif isinstance(payload.get("state"), dict) and isinstance(payload["state"].get("players"), dict):
        books = payload["state"]["players"]
    if not books:
        return payload
    import copy
    out = copy.deepcopy(payload)
    target = out.get("resources") if "resources" in out else out["state"]["players"]
    for pid, book in target.items():
        if pid != viewer and isinstance(book, dict):
            for f in _PRIVATE_BOOK_FIELDS:
                book.pop(f, None)
    return out


async def broadcast_to_room(mid: str, payload: dict):
    for pid, ws in list(CONNECTIONS.get(mid, {}).items()):
        try: await ws.send_json(_redact_for(payload, pid))
        except: pass


@app.post("/matches/{match_id}/action")
async def post_action(match_id: str, req: ActionReq):
    if match_id not in MATCHES: raise HTTPException(404)
    ok, r = MATCHES[match_id].receive_action(req.player_id, req.type, req.payload)
    return {"ok": ok}


@app.get("/matches/{match_id}/replay")
async def replay(match_id: str):
    eng = MATCHES.get(match_id)
    if not eng: raise HTTPException(404)
    return {"verify": eng.verify_replay(eng.state.actions_log), "hash": eng.state.compute_state_hash()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
