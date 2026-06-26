"""HTTP integration tests for backend entrypoint."""
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
BASE = "http://127.0.0.1:8001"
LOG_PATH = Path(r"C:\Users\fedse\AppData\Local\Temp\grok-goal-fd94c9f2e9b4\implementer\backend-api-responses.log")


def _http(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{BASE}{path}", data=data,
        headers={"Content-Type": "application/json"}, method=method,
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def _wait_health(timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if _http("GET", "/health").get("status") == "ok":
                return True
        except Exception:
            time.sleep(0.3)
    return False


@pytest.fixture(scope="module")
def server():
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8001"],
        cwd=str(BACKEND),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert _wait_health(), "backend failed to start"
    yield proc
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def test_health_and_match_flow(server):
    lines: list[str] = []
    health = _http("GET", "/health")
    lines.append(f"health={health}")
    assert health["status"] == "ok"

    aid = _http("GET", "/arenas")["arenas"][0]["id"]
    created = _http("POST", "/matches", {"arena_id": aid, "player_ids": ["p1", "p2"]})
    lines.append(f"create={created}")
    mid = created["match_id"]
    assert created.get("arena_hash") and created.get("ws_url")

    snap = _http("GET", f"/matches/{mid}")
    lines.append(f"snapshot_T={snap['match'].get('T')}")
    assert snap["match"].get("content_hash")

    for action in [
        {"player_id": "p1", "type": "tb_influence", "payload": {"level": "ff3"}},
        {"player_id": "p1", "type": "advance", "payload": {"real_delta": 2.0}},
        {"player_id": "p1", "type": "submit_order", "payload": {
            "type": "market", "instr": "X", "side": "long", "size": 5,
        }},
        {"player_id": "p1", "type": "advance", "payload": {"real_delta": 1.0}},
    ]:
        resp = _http("POST", f"/matches/{mid}/action", action)
        lines.append(f"action_{action['type']}={resp}")
        assert resp.get("ok") is True

    post_snap = _http("GET", f"/matches/{mid}")
    lines.append(f"post_equity_p1={post_snap['match']['players']['p1']['equity']}")
    assert post_snap["match"]["players"]["p1"]["positions"].get("X")

    replay = _http("GET", f"/matches/{mid}/replay")
    lines.append(f"replay={replay}")
    verify = replay["verify"]
    assert verify["verified"] is True
    assert verify["final_equity"]["p1"] == verify["original_equity"]["p1"]
    assert verify["final_equity"]["p1"] != 100.0
    assert replay.get("hash")

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")