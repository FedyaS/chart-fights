"""HTTP integration tests for backend entrypoint (no live WS required)."""
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
BASE = "http://127.0.0.1:8001"
LOG_PATH = Path(r"C:\Users\fedse\AppData\Local\Temp\grok-goal-fd94c9f2e9b4\implementer\backend-launch.log")


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
            out = _http("GET", "/health")
            if out.get("status") == "ok":
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

    arenas = _http("GET", "/arenas")
    aid = arenas["arenas"][0]["id"]
    created = _http("POST", "/matches", {"arena_id": aid, "player_ids": ["p1", "p2"]})
    lines.append(f"create={created}")
    assert created.get("match_id")
    assert created.get("arena_hash")
    assert created.get("ws_url")
    mid = created["match_id"]

    snap = _http("GET", f"/matches/{mid}")
    lines.append(f"snapshot_keys={list(snap['match'].keys())}")
    assert snap["match"].get("content_hash")

    action = _http("POST", f"/matches/{mid}/action", {
        "player_id": "p1",
        "type": "submit_order",
        "payload": {"type": "market", "instr": "X", "side": "long", "size": 5},
    })
    lines.append(f"action={action}")
    assert action.get("ok") is True

    replay = _http("GET", f"/matches/{mid}/replay")
    lines.append(f"replay={replay}")
    assert replay.get("verify", {}).get("verified") is True
    assert replay.get("hash")

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")