#!/usr/bin/env python3
"""External client for verification plan step 3: WS-first match flow, then HTTP snapshot/replay."""
import json
import sys
import time
import urllib.request
from pathlib import Path

try:
    import websockets.sync.client as ws_client
except ImportError:
    ws_client = None

BASE = "http://127.0.0.1:8001"
WS_BASE = "ws://127.0.0.1:8001"


def http(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def _ws_recv_type(ws, want: str, max_msgs: int = 40) -> dict:
    for _ in range(max_msgs):
        msg = json.loads(ws.recv())
        if msg.get("type") == want:
            return msg
    raise AssertionError(f"no WS message type={want} within {max_msgs}")


def run_once(label: str, lines: list[str]) -> None:
    lines.append(f"=== RUN {label} ===")
    health = http("GET", "/health")
    lines.append(f"health={health}")
    assert health["status"] == "ok"

    aid = http("GET", "/arenas")["arenas"][0]["id"]
    created = http("POST", "/matches", {"arena_id": aid, "player_ids": ["p1", "p2"]})
    lines.append(f"create={json.dumps(created)}")
    mid = created["match_id"]
    assert created.get("match_id") and created.get("arena_hash") and created.get("ws_url")

    pre = http("GET", f"/matches/{mid}")
    lines.append(f"pre_ws_T={pre['match'].get('T')} pre_equity_p1={pre['match']['players']['p1']['equity']}")

    if not ws_client:
        lines.append("ws_skipped=websockets not installed")
        return

    deltas_seen = 0
    last_p1_eq = 100.0
    with ws_client.connect(f"{WS_BASE}/ws/{mid}?player_id=p1") as ws:
        snap = _ws_recv_type(ws, "snapshot")
        lines.append(f"ws_first_type={snap.get('type')} ws_snapshot_T={snap.get('state', {}).get('T')}")
        assert snap["type"] == "snapshot"

        deadline = time.time() + 0.4
        while time.time() < deadline:
            try:
                raw = ws.recv(timeout=0.15)
                m = json.loads(raw)
                if m.get("type") == "delta":
                    deltas_seen += 1
                    res = m.get("resources", {})
                    if "p1" in res and "p2" in res:
                        last_p1_eq = res["p1"].get("equity", last_p1_eq)
            except Exception:
                break
        lines.append(f"ws_deltas_pre_action={deltas_seen}")

        ws.send(json.dumps({
            "type": "action",
            "action_type": "tb_influence",
            "player_id": "p1",
            "payload": {"level": "ff3"},
        }))
        ack_tb = _ws_recv_type(ws, "ack")
        lines.append(f"ws_ack_tb={ack_tb}")

        ws.send(json.dumps({
            "type": "action",
            "action_type": "submit_order",
            "player_id": "p1",
            "payload": {"type": "market", "instr": "X", "side": "long", "size": 5},
        }))
        ack_order = _ws_recv_type(ws, "ack")
        lines.append(f"ws_ack_order={ack_order}")
        assert ack_order.get("ok") is True

        deadline = time.time() + 0.5
        while time.time() < deadline:
            try:
                raw = ws.recv(timeout=0.15)
                m = json.loads(raw)
                if m.get("type") == "delta":
                    deltas_seen += 1
                    res = m.get("resources", {})
                    if "p1" in res and "p2" in res:
                        last_p1_eq = res["p1"].get("equity", last_p1_eq)
                        lines.append(f"ws_delta p1_eq={res['p1'].get('equity')} p2_eq={res['p2'].get('equity')}")
            except Exception:
                break

    lines.append(f"ws_deltas_total={deltas_seen} ws_last_p1_eq={last_p1_eq}")

    post = http("GET", f"/matches/{mid}")
    post_p1 = post["match"]["players"]["p1"]["equity"]
    post_pos = post["match"]["players"]["p1"].get("positions", {})
    lines.append(f"post_ws_snapshot_T={post['match'].get('T')} post_equity_p1={post_p1} positions={post_pos}")
    assert post_pos.get("X"), "order must leave position on p1"
    assert float(post_p1) != 100.0, f"post-WS equity must reflect P&L, got {post_p1}"

    replay = http("GET", f"/matches/{mid}/replay")
    lines.append(f"replay={json.dumps(replay)}")
    assert replay["verify"]["verified"] is True
    assert float(replay["verify"]["final_equity"]["p1"]) != 100.0
    lines.append(f"replay_p1_equity={replay['verify']['final_equity']['p1']}")


def main():
    scratch = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("backend-launch-client.log")
    label = sys.argv[2] if len(sys.argv) > 2 else "1"
    lines: list[str] = []
    run_once(label, lines)
    scratch.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if scratch.exists() and label != "1" else "w"
    with open(scratch, mode, encoding="utf-8") as f:
        if mode == "a":
            f.write("\n")
        f.write("\n".join(lines) + "\n")
    for ln in lines:
        print(ln)


if __name__ == "__main__":
    main()