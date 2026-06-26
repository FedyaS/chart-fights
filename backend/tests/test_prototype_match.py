"""Short prototype match harness: TB + orders + sabo through SimulationEngine."""
import sys
from pathlib import Path
from decimal import Decimal

root = str(Path(__file__).resolve().parents[1])
if root not in sys.path:
    sys.path.insert(0, root)

from app.arena import get_available_arenas
from app.sim.engine import SimulationEngine


def run_prototype_match() -> dict:
    aid = get_available_arenas(1)[0]["id"]
    eng = SimulationEngine("proto", aid)
    eng.state.add_player("p1")
    eng.state.add_player("p2")

    eng.state.clock.tb_resolver.set_influence("p2", "pause")
    assert eng.state.clock.get_r() == Decimal("0")
    eng.state.clock.tb_resolver.set_influence("p1", "ff3")
    assert eng.state.clock.get_r() == Decimal("0"), "pause contention holds R at 0"
    eng.state.clock.tb_resolver.set_influence("p2", "ff2")
    assert eng.state.clock.get_r() == Decimal("3"), "ff3 wins over ff2"

    eng.state.queue_action("p1", "ip_spend", {
        "ability": "delete_sl", "cost": 30, "cd": 60, "target_player": "p2",
    })
    assert eng.state.players["p1"].ip < Decimal("50")

    for _ in range(4):
        eng.state.advance(Decimal("1.0"))

    eng.state.queue_action("p1", "submit_order", {
        "type": "market", "instr": "X", "side": "long", "size": 10,
    })
    for _ in range(3):
        eng.state.advance(Decimal("1.0"))

    snap = eng.get_snapshot()
    eq_p1 = float(eng.state.players["p1"].equity)
    ver = eng.verify_replay(eng.state.actions_log)

    return {
        "arena_id": aid,
        "T": float(eng.state.clock.T),
        "equity_p1": eq_p1,
        "equity_p2": float(eng.state.players["p2"].equity),
        "content_hash": snap["content_hash"],
        "verified": ver.get("verified"),
        "verify_hash": ver.get("content_hash"),
        "sabo_events": [e for e in eng.state.events if "sabo" in str(e).lower() or "delete" in str(e).lower()],
    }


def test_prototype_match_completes_with_pnl_and_verify():
    r = run_prototype_match()
    assert r["verified"] is True
    assert r["content_hash"] == r["verify_hash"]
    assert r["equity_p1"] != 100.0
    assert r["T"] > 0


def test_prototype_match_deterministic_twice():
    a = run_prototype_match()
    b = run_prototype_match()
    assert a["content_hash"] == b["content_hash"]
    assert a["equity_p1"] == b["equity_p1"]


if __name__ == "__main__":
    for i in range(2):
        out = run_prototype_match()
        print(f"RUN{i+1}:", out)