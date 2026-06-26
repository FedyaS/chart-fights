#!/usr/bin/env python3
"""Client for verification plan step 3: health → match → snapshot → actions → replay (+ WS)."""
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

    snap = http("GET", f"/matches/{mid}")
    lines.append(f"snapshot_content_hash={snap['match'].get('content_hash')}")
    assert snap["match"].get("content_hash")

    action = http("POST", f"/matches/{mid}/action", {
        "player_id": "p1",
        "type": "tb_influence",
        "payload": {"level": "ff3"},
    })
    lines.append(f"action_tb={action}")
    action2 = http("POST", f"/matches/{mid}/action", {
        "player_id": "p1",
        "type": "advance",
        "payload": {"real_delta": 2.0},
    })
    lines.append(f"action_advance={action2}")
    action3 = http("POST", f"/matches/{mid}/action", {
        "player_id": "p1",
        "type": "submit_order",
        "payload": {"type": "market", "instr": "X", "side": "long", "size": 5},
    })
    lines.append(f"action_order={action3}")
    assert action3.get("ok") is True

    post = http("GET", f"/matches/{mid}")
    lines.append(f"post_equity_p1={post['match']['players']['p1']['equity']}")

    replay = http("GET", f"/matches/{mid}/replay")
    lines.append(f"replay={json.dumps(replay)}")
    assert replay["verify"]["verified"] is True

    if ws_client:
        deltas_seen = 0
        with ws_client.connect(f"{WS_BASE}/ws/{mid}?player_id=p1") as ws:
            msg = json.loads(ws.recv())
            lines.append(f"ws_first_type={msg.get('type')}")
            time.sleep(0.3)
            ws.send(json.dumps({
                "type": "action",
                "action_type": "submit_order",
                "player_id": "p1",
                "payload": {"type": "market", "instr": "X", "side": "long", "size": 3},
            }))
            deadline = time.time() + 2.0
            while time.time() < deadline:
                try:
                    raw = ws.recv(timeout=0.5)
                    m = json.loads(raw)
                    if m.get("type") == "delta":
                        deltas_seen += 1
                        res = m.get("resources", {})
                        if "p1" in res and "p2" in res:
                            lines.append(f"ws_delta_resources p1_eq={res['p1'].get('equity')} p2_eq={res['p2'].get('equity')}")
                except Exception:
                    break
        lines.append(f"ws_deltas_seen={deltas_seen}")
    else:
        lines.append("ws_skipped=websockets not installed")


def main():
    scratch = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("backend-launch-client.log")
    label = sys.argv[2] if len(sys.argv) > 2 else "1"
    lines: list[str] = []
    run_once(label, lines)
    scratch.parent.mkdir(parents=True, exist_ok=True)
    if scratch.exists():
        prev = scratch.read_text(encoding="utf-8")
        scratch.write_text(prev + "\n".join(lines) + "\n", encoding="utf-8")
    else:
        scratch.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for ln in lines:
        print(ln)


if __name__ == "__main__":
    main()