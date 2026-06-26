"""HTTP + WebSocket integration tests for backend entrypoint."""
import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import MATCHES, app

LOG_PATH = Path(r"C:\Users\fedse\AppData\Local\Temp\grok-goal-fd94c9f2e9b4\implementer\backend-launch.log")
RESPONSE_LOG = Path(r"C:\Users\fedse\AppData\Local\Temp\grok-goal-fd94c9f2e9b4\implementer\backend-api-responses.log")


def _ws_recv_until(ws, want_type: str = "ack", max_msgs: int = 30) -> dict:
    for _ in range(max_msgs):
        msg = ws.receive_json()
        if msg.get("type") == want_type:
            return msg
    raise AssertionError(f"no {want_type} within {max_msgs} WS messages")


def _run_ws_match_flow(client: TestClient, lines: list[str]) -> None:
    health = client.get("/health").json()
    lines.append(f"health={health}")
    assert health["status"] == "ok"

    aid = client.get("/arenas").json()["arenas"][0]["id"]
    created = client.post("/matches", json={"arena_id": aid, "player_ids": ["p1", "p2"]}).json()
    lines.append(f"create={json.dumps(created)}")
    mid = created["match_id"]
    assert created.get("ws_url") == f"/ws/{mid}"

    with client.websocket_connect(f"/ws/{mid}?player_id=p1") as ws:
        snap = ws.receive_json()
        lines.append(f"ws_connect snapshot type={snap.get('type')} T={snap.get('state', {}).get('T')}")
        assert snap["type"] == "snapshot"

        time.sleep(0.35)  # bg clock ticks → advance actions in actions_log

        ws.send_json({
            "type": "action",
            "action_type": "tb_influence",
            "player_id": "p1",
            "payload": {"level": "ff3"},
        })
        ack_tb = _ws_recv_until(ws, "ack")
        lines.append(f"ws_ack_tb_influence={json.dumps(ack_tb)}")

        ws.send_json({
            "type": "action",
            "action_type": "submit_order",
            "player_id": "p1",
            "payload": {"type": "market", "instr": "X", "side": "long", "size": 5},
        })
        ack_order = _ws_recv_until(ws, "ack")
        lines.append(f"ws_ack_submit_order={json.dumps(ack_order)}")
        assert ack_order.get("ok") is True

        time.sleep(0.25)

    eng = MATCHES[mid]
    eng.stop()
    time.sleep(0.05)

    advance_count = sum(1 for a in eng.state.actions_log if a.type == "advance")
    lines.append(f"actions_log_count={len(eng.state.actions_log)} advance_actions={advance_count}")
    lines.append(f"post_T={float(eng.state.clock.T)}")
    lines.append(f"post_equity_p1={float(eng.state.players['p1'].equity)}")
    lines.append(f"post_positions_p1={eng.state.players['p1'].positions}")

    assert advance_count > 0, "bg clock must record advance actions in actions_log"

    replay = client.get(f"/matches/{mid}/replay").json()
    lines.append(f"replay={json.dumps(replay)}")
    verify = replay["verify"]
    assert verify["verified"] is True, replay
    assert verify["final_equity"] == verify["original_equity"]
    assert verify["final_equity"]["p1"] != 100.0
    assert replay.get("hash")


@pytest.fixture
def client():
    return TestClient(app)


def test_ws_match_action_replay_flow(client):
    lines: list[str] = []
    _run_ws_match_flow(client, lines)
    RESPONSE_LOG.parent.mkdir(parents=True, exist_ok=True)
    RESPONSE_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_ws_flow_repeatable(client):
    """Second run must succeed identically (verification plan re-launch)."""
    lines: list[str] = []
    _run_ws_match_flow(client, lines)
    assert any("verified" in ln and "true" in ln.lower() for ln in lines if ln.startswith("replay="))