"""HTTP + WebSocket integration tests — assert on received delta payloads."""
import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import MATCHES, app

RESPONSE_LOG = Path(r"C:\Users\fedse\AppData\Local\Temp\grok-goal-fd94c9f2e9b4\implementer\backend-api-responses.log")


def _ws_drain(ws, max_msgs: int = 12, want_deltas: int = 0) -> list[dict]:
    """Drain up to max_msgs; stop early once want_deltas delta messages seen."""
    msgs: list[dict] = []
    for _ in range(max_msgs):
        try:
            msg = ws.receive_json()
            msgs.append(msg)
            if want_deltas and sum(1 for m in msgs if m.get("type") == "delta") >= want_deltas:
                break
        except Exception:
            break
    return msgs


def _ws_recv_until(ws, want_type: str = "ack", max_msgs: int = 50) -> tuple[dict, list[dict]]:
    collected: list[dict] = []
    for _ in range(max_msgs):
        msg = ws.receive_json()
        collected.append(msg)
        if msg.get("type") == want_type:
            return msg, collected
    raise AssertionError(f"no {want_type} within {max_msgs} WS messages")


def _run_ws_match_flow(client: TestClient, lines: list[str]) -> None:
    health = client.get("/health").json()
    lines.append(f"health={health}")
    assert health["status"] == "ok"

    aid = client.get("/arenas").json()["arenas"][0]["id"]
    created = client.post("/matches", json={"arena_id": aid, "player_ids": ["p1", "p2"]}).json()
    lines.append(f"create={json.dumps(created)}")
    mid = created["match_id"]

    all_ws_msgs: list[dict] = []
    with client.websocket_connect(f"/ws/{mid}?player_id=p1") as ws:
        snap = ws.receive_json()
        all_ws_msgs.append(snap)
        lines.append(f"ws_snapshot T={snap.get('state', {}).get('T')}")

        clock_msgs = _ws_drain(ws, max_msgs=10, want_deltas=2)
        all_ws_msgs.extend(clock_msgs)
        deltas = [m for m in clock_msgs if m.get("type") == "delta"]
        lines.append(f"ws_deltas_during_clock={len(deltas)}")
        assert len(deltas) >= 1, "bg clock must broadcast delta messages"
        for d in deltas:
            res = d.get("resources", {})
            assert "p1" in res and "p2" in res, f"delta missing per-player resources: {list(res.keys())}"
            assert isinstance(res["p1"].get("equity"), (int, float))
            assert isinstance(res["p2"].get("equity"), (int, float))

        ws.send_json({
            "type": "action",
            "action_type": "tb_influence",
            "player_id": "p1",
            "payload": {"level": "ff3"},
        })
        ack_tb, collected_tb = _ws_recv_until(ws, "ack")
        all_ws_msgs.extend(collected_tb)
        lines.append(f"ws_ack_tb={json.dumps(ack_tb)}")

        ws.send_json({
            "type": "action",
            "action_type": "submit_order",
            "player_id": "p1",
            "payload": {"type": "market", "instr": "X", "side": "long", "size": 5},
        })
        ack_order, collected_order = _ws_recv_until(ws, "ack")
        all_ws_msgs.extend(collected_order)
        lines.append(f"ws_ack_order={json.dumps(ack_order)}")
        assert ack_order.get("ok") is True

        post_order_msgs = _ws_drain(ws, max_msgs=20, want_deltas=4)
        all_ws_msgs.extend(post_order_msgs)
        post_deltas = [m for m in post_order_msgs if m.get("type") == "delta"]
        lines.append(f"ws_deltas_post_order={len(post_deltas)}")
        assert post_deltas, "expect delta after order with bg clock running"

    eng = MATCHES[mid]
    eng.stop()
    time.sleep(0.05)

    state_p1_eq = float(eng.state.players["p1"].equity)
    state_p2_eq = float(eng.state.players["p2"].equity)
    assert eng.state.players["p1"].positions.get("X"), "order must create position"
    assert state_p1_eq != 100.0

    last_delta = post_deltas[-1]
    p1_eq = last_delta["resources"]["p1"]["equity"]
    p2_eq = last_delta["resources"]["p2"]["equity"]
    lines.append(f"ws_delta_p1_equity={p1_eq} state_p1_equity={state_p1_eq}")
    lines.append(f"ws_delta_p2_equity={p2_eq} state_p2_equity={state_p2_eq}")
    assert abs(p1_eq - state_p1_eq) < 0.02, "WS delta p1 equity must match authoritative state"
    assert abs(p2_eq - state_p2_eq) < 0.02, "WS delta p2 equity must match authoritative state"
    lines.append(f"state_p1_equity={float(eng.state.players['p1'].equity)}")
    lines.append(f"advance_actions={sum(1 for a in eng.state.actions_log if a.type == 'advance')}")

    replay = client.get(f"/matches/{mid}/replay").json()
    lines.append(f"replay_verified={replay['verify']['verified']}")
    assert replay["verify"]["verified"] is True
    assert replay["verify"]["final_equity"]["p1"] != 100.0


@pytest.fixture
def client():
    return TestClient(app)


def test_ws_delta_resources_and_replay(client):
    lines: list[str] = []
    _run_ws_match_flow(client, lines)
    RESPONSE_LOG.parent.mkdir(parents=True, exist_ok=True)
    RESPONSE_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_ws_flow_repeatable(client):
    lines: list[str] = []
    _run_ws_match_flow(client, lines)
    assert any("replay_verified=True" in ln for ln in lines)