#!/usr/bin/env python3
"""End-to-end smoke test: quick-match vs bot, news/indicators flow, no ticker leak.

Starts an external uvicorn, hits POST /matches/quick, connects over WS as p1,
drains a few seconds of deltas, and asserts the new features work and that the
real (ticker-bearing) arena id never appears in any client payload.
"""
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import websockets.sync.client as ws_client

ROOT = Path(__file__).resolve().parents[1]
PORT = 8021
BASE = f"http://127.0.0.1:{PORT}"
WS = f"ws://127.0.0.1:{PORT}"
REAL_ID = re.compile(r"\b[A-Z]{1,5}_\d{5}\b")  # e.g. AAPL_00000 — must never leak


def http(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers={"Content-Type": "application/json"}, method=method)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def wait_health(timeout=20):
    end = time.time() + timeout
    while time.time() < end:
        try:
            with urllib.request.urlopen(f"{BASE}/health", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


def main():
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=str(ROOT / "backend"), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    try:
        assert wait_health(), "server did not start"
        checks = []

        arenas = http("GET", "/arenas")["arenas"]
        leak = [a for a in arenas if REAL_ID.search(a.get("id", "")) or "ticker" in a]
        checks.append(("/arenas hides ticker", not leak))
        checks.append(("/arenas has sector label", all("sector" in a for a in arenas)))

        created = http("POST", "/matches/quick", {"vs_bot": True})
        checks.append(("quick-match returns bot=True", created.get("bot") is True))
        checks.append(("quick-match arena_id is opaque", not REAL_ID.search(created.get("arena_id", ""))))
        checks.append(("arena_label is sector·codename", "·" in created.get("arena_label", "")))
        mid = created["match_id"]

        blob = json.dumps(created)
        deltas, news_seen, ind_seen, bot_fill = 0, False, False, False
        opp_leaked = False
        time_lefts = []
        with ws_client.connect(f"{WS}/ws/{mid}?player_id=p1") as ws:
            snap = json.loads(ws.recv())
            blob += json.dumps(snap)
            checks.append(("snapshot arena_id opaque", not REAL_ID.search(json.dumps(snap.get("state", {}).get("arena_id", "")))))
            checks.append(("snapshot has indicators key", "indicators" in snap.get("state", {})))
            # fast-forward so enough bars cross to fairly exercise the news feed
            ws.send(json.dumps({"type": "action", "action_type": "tb_influence", "player_id": "p1", "payload": {"level": "ff5"}}))
            deadline = time.time() + 14
            while time.time() < deadline:
                try:
                    msg = json.loads(ws.recv())
                except Exception:
                    break
                blob += json.dumps(msg)
                if msg.get("type") == "delta":
                    deltas += 1
                    opp = (msg.get("resources", {}) or {}).get("p2", {})
                    if "positions" in opp or "orders" in opp:
                        opp_leaked = True   # opponent book must be redacted for the viewer
                    if msg.get("time_left") is not None:
                        time_lefts.append(msg["time_left"])
                    if msg.get("indicators"):
                        ind_seen = True
                    for e in msg.get("events", []):
                        if e.get("type") == "news":
                            news_seen = True
                    for f in msg.get("fills", []):
                        if f.get("player") == "p2":
                            bot_fill = True

            # ---- close round-trip (issue #1): open then close, watch positions ----
            def drain_until(pred, secs=8.0):
                end = time.time() + secs
                last = None
                while time.time() < end:
                    try:
                        m = json.loads(ws.recv())
                    except Exception:
                        break
                    if m.get("type") == "delta":
                        last = (m.get("resources", {}) or {}).get("p1", {})
                        if pred(last):
                            return last, True
                return last, False

            ws.send(json.dumps({"type": "action", "action_type": "submit_order", "player_id": "p1",
                                "payload": {"type": "market", "side": "long", "size": 20}}))
            opened, ok_open = drain_until(lambda p: bool(p.get("positions")))
            checks.append(("delta carries positions after order", ok_open and bool(opened.get("positions"))))

            ws.send(json.dumps({"type": "action", "action_type": "close", "player_id": "p1",
                                "payload": {"instr": "X", "fraction": 1.0}}))
            closed, ok_close = drain_until(lambda p: not p.get("positions"))
            checks.append(("close flattens position (delta shows empty)", ok_close))

        # robust bot-traded signal: inspect p2's final state via HTTP
        post = http("GET", f"/matches/{mid}")["match"]["players"].get("p2", {})
        bot_traded = bot_fill or bool(post.get("positions")) or bool(post.get("orders")) \
            or abs(float(post.get("equity", 100)) - 100.0) > 1e-6
        bot_fill = bot_traded

        checks.append(("received deltas", deltas >= 1))
        checks.append(("time_left counts down", len(time_lefts) >= 2 and time_lefts[-1] < 300))
        checks.append(("news emitted", news_seen))
        checks.append(("indicators streamed", ind_seen))
        checks.append(("bot (p2) traded", bot_fill))
        checks.append(("opponent book redacted (fog-of-war)", not opp_leaked))
        checks.append(("NO real arena id leaked anywhere", not REAL_ID.search(blob)))

        print("\n=== quick-match smoke ===")
        ok = True
        for name, passed in checks:
            print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
            ok = ok and passed
        print(f"deltas={deltas} time_lefts={time_lefts[:3]}… news={news_seen} ind={ind_seen} botFill={bot_fill}")
        print("RESULT:", "ALL PASS" if ok else "FAILURES PRESENT")
        sys.exit(0 if ok else 1)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
