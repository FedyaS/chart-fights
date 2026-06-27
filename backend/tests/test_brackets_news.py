"""Tests for bracket orders (TP/SL + OCO + reduce-only), buying power, news
emission, quick-match, and the bot — the features added to finish the game."""
from decimal import Decimal

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.arena import get_available_arenas, sector_label
from app.sim.engine import SimulationEngine


def _engine():
    aid = get_available_arenas(1)[0]["id"]
    eng = SimulationEngine("t", aid)
    eng.state.add_player("p1")
    eng.state.add_player("p2")
    return eng


def _ps(eng, pid="p1"):
    return eng.state.players[pid]


# ---- bracket construction -------------------------------------------------

def test_long_bracket_legs_tp_above_sl_below():
    eng = _engine()
    px = float(eng.state.get_price())
    eng.state._apply_action("p1", "submit_order", {
        "type": "market", "side": "long", "size": 10, "tp": px * 1.03, "sl": px * 0.98,
    })
    orders = _ps(eng).orders
    assert len(orders) == 2
    tp = next(o for o in orders if o["kind"] == "tp")
    sl = next(o for o in orders if o["kind"] == "sl")
    assert tp["type"] == "limit" and tp["side"] == "short" and tp["reduce_only"]
    assert sl["type"] == "stop" and sl["side"] == "short" and sl["reduce_only"]
    assert tp["price"] > px > sl["price"]           # long: TP above, SL below
    assert tp["group"] == sl["group"]               # OCO siblings


def test_short_bracket_legs_tp_below_sl_above():
    eng = _engine()
    px = float(eng.state.get_price())
    eng.state._apply_action("p1", "submit_order", {
        "type": "market", "side": "short", "size": 10, "tp": px * 0.97, "sl": px * 1.02,
    })
    orders = _ps(eng).orders
    tp = next(o for o in orders if o["kind"] == "tp")
    sl = next(o for o in orders if o["kind"] == "sl")
    assert tp["side"] == "long" and sl["side"] == "long"
    assert tp["price"] < px < sl["price"]           # short: TP below, SL above (the user's concern)


# ---- OCO + reduce-only ----------------------------------------------------

def test_oco_tp_fill_cancels_sl_sibling():
    eng = _engine()
    px = float(eng.state.get_price())
    eng.state._apply_action("p1", "submit_order", {
        "type": "market", "side": "long", "size": 10, "tp": px * 1.02, "sl": px * 0.95,
    })
    ps = _ps(eng)
    # a bar that gaps through the TP (sell limit) but not the SL
    bar = {"open": px * 1.03, "high": px * 1.04, "low": px * 1.01, "close": px * 1.03}
    fills = eng.state._process_resting_orders("p1", ps, bar, 1)
    assert len(fills) == 1                            # only TP filled
    assert ps.orders == []                            # OCO removed the SL sibling
    assert "X" not in ps.positions or ps.positions["X"]["size"] == 0  # flat
    assert ps.realized_pnl > 0


def test_reduce_only_never_flips_after_partial_close():
    eng = _engine()
    px = float(eng.state.get_price())
    eng.state._apply_action("p1", "submit_order", {
        "type": "market", "side": "long", "size": 10, "tp": px * 1.02, "sl": px * 0.95,
    })
    ps = _ps(eng)
    # manually close half -> position now 5 long; brackets still sized 10
    eng.state._apply_action("p1", "close", {"instr": "X", "fraction": 0.5})
    assert abs(ps.positions["X"]["size"] - Decimal("5")) < Decimal("0.001")
    bar = {"open": px * 1.03, "high": px * 1.04, "low": px * 1.01, "close": px * 1.03}
    eng.state._process_resting_orders("p1", ps, bar, 1)
    # TP clamped to the live 5; position flat, NOT flipped short
    size = ps.positions.get("X", {}).get("size", Decimal("0"))
    assert size >= Decimal("0")


def test_orphaned_brackets_dropped_when_flat():
    eng = _engine()
    px = float(eng.state.get_price())
    eng.state._apply_action("p1", "submit_order", {
        "type": "market", "side": "long", "size": 10, "tp": px * 1.5, "sl": px * 0.5,
    })
    ps = _ps(eng)
    eng.state._apply_action("p1", "close", {"instr": "X", "fraction": 1.0})  # flat
    assert ps.orders == []                            # close retired the brackets


# ---- buying power ---------------------------------------------------------

def test_buying_power_rejects_oversize_order():
    eng = _engine()
    # equity 100, leverage 3 -> BP 300
    assert eng.state._apply_action("p1", "submit_order", {"type": "market", "side": "long", "size": 250}) is True
    ok = eng.state._apply_action("p1", "submit_order", {"type": "market", "side": "long", "size": 100})
    assert ok is False                                # 350 > 300
    assert any(e.get("type") == "order_rejected" and e.get("reason") == "insufficient_buying_power"
               for e in eng.state.events)


# ---- news emission --------------------------------------------------------

def test_news_emitted_on_crossed_bars():
    eng = _engine()
    eng.state.advance(Decimal("3"))                   # R=1 -> cross bars 1,2,3
    assert any(e.get("type") == "news" for e in eng.state.events)


def test_snapshot_has_indicators_and_sector_label():
    eng = _engine()
    snap = eng.get_snapshot()
    assert "indicators" in snap
    assert "·" in snap["label"]                       # sector · codename, not a raw ticker


# ---- sector obfuscation ---------------------------------------------------

def test_arena_listing_hides_ticker():
    arenas = get_available_arenas(5)
    for a in arenas:
        assert "ticker" not in a
        assert a["label"] == f"{a['sector']}" or a["sector"] in a["label"]


# ---- quick match + bot ----------------------------------------------------

def test_quick_match_registers_bot():
    import app.main as m
    mid, arena = m._new_match(get_available_arenas(1)[0]["id"], ["p1", "p2"], bot=True)
    assert m.MATCH_BOTS.get(mid) == "p2"
    assert mid in m.MATCHES


def test_bot_places_orders_on_trend():
    from app.bot import BotTrader
    eng = _engine()
    bot = BotTrader(eng, "p2", seed=1)
    # _step appends the current price (~100); seed an uptrend that survives that append
    bot._recent = [90.0, 95.0, 100.0]
    bot._step()
    ps = eng.state.players["p2"]
    assert ps.positions or ps.orders                  # acted (market fill or resting order)
