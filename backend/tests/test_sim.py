"""Simulation engine tests — all drives via queue_action + verify_replay on actions_log."""
import sys
from pathlib import Path
from decimal import Decimal

root = str(Path(__file__).resolve().parents[1])
if root not in sys.path:
    sys.path.insert(0, root)

from app.arena import get_available_arenas
from app.sim.engine import SimulationEngine, CLOCK_PLAYER_ID


def _build_engine():
    aid = get_available_arenas(1)[0]["id"]
    eng = SimulationEngine("testmatch", aid)
    eng.state.add_player("p1")
    eng.state.add_player("p2")
    return eng, aid


def _drive_standard_sequence(eng: SimulationEngine) -> None:
    """Action-log-only sequence: TB, sabo, advance, order, advance."""
    eng.state.queue_action("p1", "tb_influence", {"level": "ff3"})
    eng.state.queue_action("p1", "ip_spend", {
        "ability": "delete_sl", "cost": 30, "cd": 60, "target_player": "p2",
    })
    eng.state.queue_action("p1", "advance", {"real_delta": 1.0})
    eng.state.queue_action("p1", "submit_order", {
        "type": "market", "instr": "X", "side": "long", "size": 5,
    })
    eng.state.queue_action("p1", "advance", {"real_delta": 0.5})


def main():
    eng, aid = _build_engine()
    print(f"Loaded arena id={aid}")
    assert eng.state.clock.get_r() == Decimal("1"), "default R before influence"

    eng.state.queue_action("p1", "tb_influence", {"level": "ff3"})
    assert eng.state.clock.get_r() == Decimal("3"), "R driven via tb_influence action"
    print("SharedClock + R drive: PASS")

    ok = eng.state.queue_action("p1", "ip_spend", {
        "ability": "delete_sl", "cost": 30, "cd": 60, "target_player": "p2",
    })
    assert ok and eng.state.players["p1"].ip < Decimal("50")
    print("TB/IP/sabo basic: PASS")

    eng.state.queue_action("p1", "advance", {"real_delta": 1.0})
    cur_bar = eng.state.get_current_bar()
    assert "open" in cur_bar and "close" in cur_bar
    print("Advance: T=", float(eng.state.clock.T), "bar_ohlc=", {
        k: cur_bar.get(k) for k in ["open", "high", "low", "close"]
    }, "PASS")

    price_before = eng.state.get_price()
    eng.state.queue_action("p1", "submit_order", {
        "type": "market", "instr": "X", "side": "long", "size": 5,
    })
    pos = eng.state.players["p1"].positions.get("X", {})
    assert abs(float(pos.get("size", 0)) - 5.0) < 0.1
    assert abs(float(pos.get("entry", 0)) - float(price_before)) < 1.0
    print("submit_order fill at close: PASS")

    eng.state.queue_action("p1", "advance", {"real_delta": 0.5})
    eq = float(eng.state.players["p1"].equity)
    print("Equity after trade:", eq, "PASS")

    snap = eng.get_snapshot()
    ver = eng.verify_replay(eng.state.actions_log)
    assert ver["verified"] is True
    assert ver["final_equity"] == ver["original_equity"]
    assert ver["final_hash"] == ver["original_hash"]
    print("verify_replay hash+equity match: PASS")
    print("All tests PASS.")


def test_shared_clock_and_r():
    eng, _ = _build_engine()
    eng.state.queue_action("p1", "tb_influence", {"level": "ff3"})
    assert eng.state.clock.get_r() == Decimal("3")


def test_tb_ip_sabo():
    eng, _ = _build_engine()
    ok = eng.state.queue_action("p1", "ip_spend", {
        "ability": "delete_sl", "cost": 30, "cd": 60, "target_player": "p2",
    })
    assert ok and eng.state.players["p1"].ip < Decimal("50")


def test_advance_real_bar_ohlc():
    eng, _ = _build_engine()
    eng.state.queue_action("p1", "tb_influence", {"level": "ff3"})
    eng.state.queue_action("p1", "advance", {"real_delta": 1.0})
    cur_bar = eng.state.get_current_bar()
    assert "open" in cur_bar and "close" in cur_bar


def test_submit_order_fill_at_close():
    eng, _ = _build_engine()
    eng.state.queue_action("p1", "tb_influence", {"level": "ff3"})
    eng.state.queue_action("p1", "advance", {"real_delta": 1.0})
    price_before = eng.state.get_price()
    eng.state.queue_action("p1", "submit_order", {
        "type": "market", "instr": "X", "side": "long", "size": 5,
    })
    pos = eng.state.players["p1"].positions.get("X", {})
    assert abs(float(pos.get("size", 0)) - 5.0) < 0.1
    assert abs(float(pos.get("entry", 0)) - float(price_before)) < 1.0


def test_snapshot_and_verify_replay():
    eng, _ = _build_engine()
    _drive_standard_sequence(eng)
    snap = eng.get_snapshot()
    assert snap.get("content_hash")
    ver = eng.verify_replay(eng.state.actions_log)
    assert ver["verified"] is True
    assert ver["final_equity"]["p1"] == ver["original_equity"]["p1"]
    assert ver["final_hash"] == ver["original_hash"]


def test_clock_advance_uses_system_player():
    eng, _ = _build_engine()
    eng.state.queue_action(CLOCK_PLAYER_ID, "advance", {"real_delta": 1.0})
    assert eng.state.actions_log[-1].player_id == CLOCK_PLAYER_ID
    assert eng.state.actions_log[-1].type == "advance"
    assert float(eng.state.clock.T) > 0


def test_verify_replay_deterministic_twice():
    results = []
    for _ in range(2):
        eng, _ = _build_engine()
        _drive_standard_sequence(eng)
        ver = eng.verify_replay(eng.state.actions_log)
        results.append((
            ver["final_hash"],
            ver["final_equity"]["p1"],
            ver["verified"],
        ))
    assert results[0] == results[1]
    assert results[0][2] is True


if __name__ == "__main__":
    main()