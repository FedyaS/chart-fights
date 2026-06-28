"""HTTP + WebSocket integration tests against real uvicorn (no TestClient)."""
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

try:
    import websockets.sync.client as ws_client
except ImportError:
    ws_client = None

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
PORT = 8013
BASE = f"http://127.0.0.1:{PORT}"
WS_BASE = f"ws://127.0.0.1:{PORT}"
RESPONSE_LOG = Path(r"C:\Users\fedse\AppData\Local\Temp\grok-goal-fd94c9f2e9b4\implementer\backend-api-responses.log")


def _http(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def _wait_health(timeout: float = 20.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE}/health", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


def _ws_recv_until(ws, want_type: str, max_msgs: int = 50) -> tuple[dict, list[dict]]:
    collected: list[dict] = []
    for _ in range(max_msgs):
        msg = json.loads(ws.recv())
        collected.append(msg)
        if msg.get("type") == want_type:
            return msg, collected
    raise AssertionError(f"no {want_type} within {max_msgs} WS messages")


def _ws_drain(ws, max_msgs: int = 12, want_deltas: int = 0) -> list[dict]:
    msgs: list[dict] = []
    for _ in range(max_msgs):
        try:
            msg = json.loads(ws.recv(timeout=0.2))
            msgs.append(msg)
            if want_deltas and sum(1 for m in msgs if m.get("type") == "delta") >= want_deltas:
                break
        except Exception:
            break
    return msgs


def _run_ws_match_flow(lines: list[str]) -> None:
    if not ws_client:
        pytest.skip("websockets not installed")

    health = _http("GET", "/health")
    lines.append(f"health={health}")
    assert health["status"] == "ok"

    aid = _http("GET", "/arenas")["arenas"][0]["id"]
    created = _http("POST", "/matches", {"arena_id": aid, "player_ids": ["p1", "p2"]})
    lines.append(f"create={json.dumps(created)}")
    mid = created["match_id"]
    assert created.get("match_id") and created.get("arena_hash") and created.get("ws_url")

    post_deltas: list[dict] = []
    with ws_client.connect(f"{WS_BASE}/ws/{mid}?player_id=p1") as ws:
        snap, _ = _ws_recv_until(ws, "snapshot", max_msgs=5)
        lines.append(f"ws_first_type={snap.get('type')} ws_snapshot_T={snap.get('state', {}).get('T')}")
        assert snap["type"] == "snapshot"

        clock_msgs = _ws_drain(ws, max_msgs=10, want_deltas=2)
        deltas = [m for m in clock_msgs if m.get("type") == "delta"]
        lines.append(f"ws_deltas_during_clock={len(deltas)}")
        assert len(deltas) >= 1, "bg clock must broadcast delta messages"
        for d in deltas:
            res = d.get("resources", {})
            assert "p1" in res and "p2" in res, f"delta missing per-player resources: {list(res.keys())}"
            assert isinstance(res["p1"].get("equity"), (int, float))
            assert isinstance(res["p2"].get("equity"), (int, float))

        ws.send(json.dumps({
            "type": "action",
            "action_type": "tb_influence",
            "player_id": "p1",
            "payload": {"level": "ff3"},
        }))
        ack_tb, collected_tb = _ws_recv_until(ws, "ack")
        lines.append(f"ws_ack_tb={json.dumps(ack_tb)}")

        ws.send(json.dumps({
            "type": "action",
            "action_type": "submit_order",
            "player_id": "p1",
            "payload": {"type": "market", "instr": "X", "side": "long", "size": 5},
        }))
        ack_order, collected_order = _ws_recv_until(ws, "ack")
        lines.append(f"ws_ack_order={json.dumps(ack_order)}")
        assert ack_order.get("ok") is True

        post_deltas = []
        # Paced live feed: wait until a bar crosses and equity moves off 100.
        deadline = time.time() + 8.0
        while time.time() < deadline:
            try:
                msg = json.loads(ws.recv(timeout=0.25))
                if msg.get("type") == "delta":
                    post_deltas.append(msg)
                    res = msg.get("resources", {})
                    if "p1" in res:
                        lines.append(
                            f"ws_delta p1_eq={res['p1'].get('equity')} p2_eq={res.get('p2', {}).get('equity')}"
                        )
                        if abs(float(res["p1"].get("equity", 100.0)) - 100.0) > 0.005:
                            break
            except Exception:
                break
        lines.append(f"ws_deltas_post_order={len(post_deltas)}")
        assert post_deltas, "expect delta after order with bg clock running"

    post = _http("GET", f"/matches/{mid}")
    post_p1 = float(post["match"]["players"]["p1"]["equity"])
    post_p2 = float(post["match"]["players"]["p2"]["equity"])
    post_pos = post["match"]["players"]["p1"].get("positions", {})
    lines.append(f"post_equity_p1={post_p1} post_equity_p2={post_p2}")
    assert post_pos.get("X"), "order must create position"

    last_delta = post_deltas[-1]
    delta_p1_eq = float(last_delta["resources"]["p1"]["equity"])
    lines.append(f"ws_last_delta_p1_equity={delta_p1_eq}")
    assert delta_p1_eq != 100.0, "clock deltas must reflect P&L after order"
    assert post_p1 != 100.0
    p1_eq = last_delta["resources"]["p1"]["equity"]
    p2_eq = last_delta["resources"]["p2"]["equity"]
    lines.append(f"ws_delta_p1_equity={p1_eq} http_p1_equity={post_p1}")
    lines.append(f"ws_delta_p2_equity={p2_eq} http_p2_equity={post_p2}")
    assert abs(float(p1_eq) - post_p1) < 0.02, "WS delta p1 equity must match HTTP snapshot"
    assert abs(float(p2_eq) - post_p2) < 0.02, "WS delta p2 equity must match HTTP snapshot"

    replay = _http("GET", f"/matches/{mid}/replay")
    lines.append(f"replay_verified={replay['verify']['verified']}")
    lines.append(f"replay_p1_equity={replay['verify']['final_equity']['p1']}")
    assert replay["verify"]["verified"] is True
    assert float(replay["verify"]["final_equity"]["p1"]) != 100.0


@pytest.fixture(scope="module")
def uvicorn_server():
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=str(ROOT / "backend"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert _wait_health(), "external uvicorn failed to start"
    yield proc
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def test_ws_delta_resources_and_replay(uvicorn_server):
    lines: list[str] = []
    _run_ws_match_flow(lines)
    RESPONSE_LOG.parent.mkdir(parents=True, exist_ok=True)
    RESPONSE_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_ws_flow_repeatable(uvicorn_server):
    lines: list[str] = []
    _run_ws_match_flow(lines)
    assert any("replay_verified=True" in ln for ln in lines)
    post_eq = None
    for ln in lines:
        m = re.search(r"post_equity_p1=([\d.]+)", ln)
        if m:
            post_eq = float(m.group(1))
    assert post_eq is not None and post_eq != 100.0