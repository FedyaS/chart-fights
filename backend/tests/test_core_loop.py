"""Core-loop tests: P&L realization, win/lose, sabotage effects, two-player broadcast.

Uses synthetic arenas (controlled OHLC) so price direction is deterministic and the
asserts don't depend on real historical data movement.
"""
import sys
from decimal import Decimal
from pathlib import Path

root = str(Path(__file__).resolve().parents[1])
if root not in sys.path:
    sys.path.insert(0, root)

from app.sim.engine import MatchState, SimulationEngine, ABILITIES
from app.sim.deltas import build_delta_payload, build_resources_snapshot
from app.arena import get_available_arenas


def synth_state(prices, match_id="m", players=("p1", "p2")) -> MatchState:
    bars = [{"t": i, "open": float(p), "high": float(p), "low": float(p), "close": float(p)}
            for i, p in enumerate(prices)]
    arena = {"hash": "synthhash", "content_hash": "synthhash", "label": "Synthetic",
             "bars": bars, "num_bars": len(bars)}
    st = MatchState(match_id, "synth", arena)
    for p in players:
        st.add_player(p)
    return st


# --------------------------------------------------------------------------- P&L

def test_long_close_realizes_profit_and_grants_ip():
    st = synth_state([100, 110])
    p1 = st.players["p1"]
    base_ip = p1.ip
    st.queue_action("p1", "submit_order", {"type": "market", "instr": "X", "side": "long", "size": 10})
    st.queue_action("p1", "advance", {"real_delta": 1.0})       # T -> 1, price 110
    assert p1.realized_pnl == Decimal("0")                      # not closed yet
    assert p1.equity > Decimal("100")                          # marked up
    st.queue_action("p1", "close", {"instr": "X"})
    assert p1.realized_pnl > Decimal("0")                      # profit booked
    assert "X" not in p1.positions                            # flattened
    # IP must have grown beyond passive regen alone (the +10% profit grant)
    assert p1.ip > base_ip + Decimal("0.5")


def test_short_close_realizes_profit_when_price_falls():
    st = synth_state([100, 90])
    p1 = st.players["p1"]
    st.queue_action("p1", "submit_order", {"type": "market", "instr": "X", "side": "short", "size": 10})
    st.queue_action("p1", "advance", {"real_delta": 1.0})       # price 90
    assert p1.equity > Decimal("100")                          # short gains as price drops
    st.queue_action("p1", "close", {"instr": "X"})
    assert p1.realized_pnl > Decimal("0")


def test_losing_close_books_loss_and_no_ip_grant():
    st = synth_state([100, 90])
    p1 = st.players["p1"]
    base_ip = p1.ip
    st.queue_action("p1", "submit_order", {"type": "market", "instr": "X", "side": "long", "size": 10})
    st.queue_action("p1", "advance", {"real_delta": 1.0})       # price 90 -> long is down
    st.queue_action("p1", "close", {"instr": "X"})
    assert p1.realized_pnl < Decimal("0")
    # losing close grants no profit IP; only passive regen (small) should have accrued
    assert p1.ip <= base_ip + Decimal("0.6")


def test_partial_close_reduces_size_and_keeps_entry():
    st = synth_state([100, 120])
    p1 = st.players["p1"]
    st.queue_action("p1", "submit_order", {"type": "market", "instr": "X", "side": "long", "size": 10})
    entry = p1.positions["X"]["entry"]
    st.queue_action("p1", "advance", {"real_delta": 1.0})
    st.queue_action("p1", "close", {"instr": "X", "fraction": 0.5})
    assert abs(float(p1.positions["X"]["size"]) - 5.0) < 1e-9
    assert p1.positions["X"]["entry"] == entry                 # basis unchanged
    assert p1.realized_pnl > Decimal("0")


def test_equity_is_100_plus_realized_plus_unrealized():
    st = synth_state([100, 110, 105])
    p1 = st.players["p1"]
    st.queue_action("p1", "submit_order", {"type": "market", "instr": "X", "side": "long", "size": 10})
    st.queue_action("p1", "advance", {"real_delta": 2.0})       # T -> 2, price 105
    price = st.get_price()
    unreal = st.player_unrealized(p1, price)
    expected = (Decimal("100") + p1.realized_pnl + unreal).quantize(Decimal("0.01"))
    assert p1.equity == expected


# ------------------------------------------------------------------- win / lose

def test_winner_is_higher_equity():
    st = synth_state([100, 130])
    st.queue_action("p1", "submit_order", {"type": "market", "instr": "X", "side": "long", "size": 20})
    st.queue_action("p1", "advance", {"real_delta": 1.0})       # p1 long gains; p2 flat
    result = st.determine_result()
    assert result["winner"] == "p1"
    assert result["is_draw"] is False
    assert result["players"]["p1"]["equity"] > result["players"]["p2"]["equity"]
    snap = st.snapshot()
    assert snap["winner"] == "p1"
    assert "result" in snap and "is_over" in snap


def test_draw_when_equal_equity():
    st = synth_state([100, 110])
    st.queue_action("p1", "advance", {"real_delta": 1.0})       # neither trades
    result = st.determine_result()
    assert result["is_draw"] is True
    assert result["winner"] is None
    assert result["players"]["p1"]["equity"] == result["players"]["p2"]["equity"] == 100.0


def test_short_beats_long_in_down_market():
    st = synth_state([100, 80])
    st.queue_action("p1", "submit_order", {"type": "market", "instr": "X", "side": "short", "size": 15})
    st.queue_action("p2", "submit_order", {"type": "market", "instr": "X", "side": "long", "size": 15})
    st.queue_action("p1", "advance", {"real_delta": 1.0})
    result = st.determine_result()
    assert result["winner"] == "p1"


# -------------------------------------------------------------------- sabotage

def test_delete_sl_removes_victim_stop_orders():
    st = synth_state([100, 101])
    st.queue_action("p2", "submit_order", {"type": "stop", "instr": "X", "side": "short", "size": 5, "price": 95})
    st.queue_action("p2", "submit_order", {"type": "limit", "instr": "X", "side": "long", "size": 5, "price": 90})
    assert any(o["type"] == "stop" for o in st.players["p2"].orders)
    ok = st.queue_action("p1", "ip_spend", {"ability": "delete_sl", "target_player": "p2"})
    assert ok
    assert not any(o["type"] == "stop" for o in st.players["p2"].orders)
    assert any(o["type"] == "limit" for o in st.players["p2"].orders)  # only stops removed
    assert st.players["p1"].ip == Decimal("50") - ABILITIES["delete_sl"]["cost"]
    assert any(e.get("type") == "sabo" and e.get("victim") == "p2" for e in st.events)


def test_widen_spread_worsens_victim_fills():
    base = synth_state([100, 100])
    base.queue_action("p2", "submit_order", {"type": "market", "instr": "X", "side": "long", "size": 10})
    clean_entry = base.players["p2"].positions["X"]["entry"]

    sab = synth_state([100, 100])
    sab.queue_action("p1", "ip_spend", {"ability": "widen_spread", "target_player": "p2"})
    sab.queue_action("p2", "submit_order", {"type": "market", "instr": "X", "side": "long", "size": 10})
    widened_entry = sab.players["p2"].positions["X"]["entry"]
    # buy fill should be MORE expensive (higher) under widen
    assert widened_entry > clean_entry
    assert sab._widen_active(sab.players["p2"]) is True


def test_fake_news_lands_in_victim_feed_only():
    st = synth_state([100, 101])
    st.queue_action("p1", "ip_spend", {"ability": "fake_news", "target_player": "p2"})
    assert any(n.get("fake") for n in st.players["p2"].news_feed)
    assert not st.players["p1"].news_feed
    assert st.players["p1"].ip == Decimal("50") - ABILITIES["fake_news"]["cost"]


def test_peek_reveals_headline_to_caster():
    st = synth_state([100, 101, 102])
    st.players["p1"].ip = Decimal("100")
    ok = st.queue_action("p1", "ip_spend", {"ability": "peek"})
    assert ok
    assert any(n.get("peek") for n in st.players["p1"].news_feed)
    assert any(e.get("type") == "peek" and e.get("private") for e in st.events)


def test_ability_cooldown_blocks_immediate_recast():
    st = synth_state([100, 101])
    st.players["p1"].ip = Decimal("200")
    assert st.queue_action("p1", "ip_spend", {"ability": "delete_sl", "target_player": "p2"}) is True
    # match_time has not advanced -> still on cooldown
    assert st.queue_action("p1", "ip_spend", {"ability": "delete_sl", "target_player": "p2"}) is False


def test_ability_rejected_when_insufficient_ip():
    st = synth_state([100, 101])
    st.players["p1"].ip = Decimal("10")
    assert st.queue_action("p1", "ip_spend", {"ability": "delete_sl", "target_player": "p2"}) is False
    assert st.players["p1"].ip == Decimal("10")  # no spend on rejection


# ------------------------------------------------------------ resting orders

def test_limit_order_fills_on_crossing_bar():
    st = synth_state([100, 95, 105])
    st.queue_action("p1", "submit_order", {"type": "limit", "instr": "X", "side": "long", "size": 5, "price": 96})
    assert st.players["p1"].orders                              # resting
    st.queue_action("p1", "advance", {"real_delta": 1.0})       # bar1 low=95 <= 96 -> fill
    assert "X" in st.players["p1"].positions
    assert abs(float(st.players["p1"].positions["X"]["size"]) - 5.0) < 1e-9
    assert not st.players["p1"].orders                          # consumed


def test_stop_order_triggers_on_breakout():
    st = synth_state([100, 105])
    st.queue_action("p1", "submit_order", {"type": "stop", "instr": "X", "side": "long", "size": 5, "price": 104})
    st.queue_action("p1", "advance", {"real_delta": 1.0})       # bar1 high=105 >= 104 -> trigger
    assert "X" in st.players["p1"].positions


# ------------------------------------------------------------ two-player broadcast

def test_delta_broadcasts_both_players_resources():
    st = synth_state([100, 110])
    st.queue_action("p1", "submit_order", {"type": "market", "instr": "X", "side": "long", "size": 10})
    st.queue_action("p2", "submit_order", {"type": "market", "instr": "X", "side": "short", "size": 5})
    st.queue_action("p1", "advance", {"real_delta": 1.0})
    payload = build_delta_payload(st)
    res = payload["resources"]
    assert set(res.keys()) == {"p1", "p2"}
    for pid in ("p1", "p2"):
        assert isinstance(res[pid]["equity"], (int, float))
        assert isinstance(res[pid]["ip"], (int, float))
        assert res[pid]["tb"] is not None
    # p1 long should be up, p2 short should be down in a rising market
    assert res["p1"]["equity"] > 100.0
    assert res["p2"]["equity"] < 100.0


def test_real_arena_two_player_snapshot_has_winner_fields():
    aid = get_available_arenas(1)[0]["id"]
    eng = SimulationEngine("realmatch", aid)
    eng.state.add_player("p1")
    eng.state.add_player("p2")
    eng.state.queue_action("p1", "submit_order", {"type": "market", "instr": "X", "side": "long", "size": 8})
    for _ in range(3):
        eng.state.queue_action("p1", "advance", {"real_delta": 1.0})
    snap = eng.get_snapshot()
    assert "winner" in snap and "is_over" in snap and "result" in snap
    assert set(snap["players"].keys()) == {"p1", "p2"}
    ver = eng.verify_replay(eng.state.actions_log)
    assert ver["verified"] is True
