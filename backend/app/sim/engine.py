"""Authoritative simulation engine for chart-fights.

Implements per GDD, game-mechanics-spec.md (T/R/TB/IP, orders, P&L, sabotage, win
condition), task-001..005.

Key design points (all deterministic — Decimal everywhere, no live RNG, no
wall-clock in the audited state):
- Loads real arena data via arena loader (P[0]=100 normalized).
- SharedClock drives T (fractional bar index) using contested R (TBResolver, spec §2).
- ``advance(real_delta)`` integrates T, advances a deterministic ``match_time``
  accumulator (real seconds elapsed), applies every newly-crossed integer bar in
  ascending order (limit/stop OHLC triggers), and marks positions to the latest
  bar close.
- P&L (task-004 §OQ-O5): per-position signed size + average entry price.
  ``unrealized = Σ size * (price - entry) / entry``; realized is booked on every
  close/reduce/flip. ``equity = 100 + realized + unrealized``.
- Resources (spec §2): IP regen +0.5/s, +10% of realized P&L on profitable closes,
  soft cap 200; TB recharge/consume exact rates via TBResolver.
- Sabotage (spec §7 / task-003): delete_sl, widen_spread, fake_news, peek — exact
  IP costs + real-time cooldowns (measured against the deterministic match_time
  accumulator so replays reproduce them), opponent targeting, victim events.
- Win condition (spec §8): higher final equity wins; equal → draw.
- Anti-cheat: ``verify_replay`` re-sims from (arena + sorted action log) and asserts
  identical state hash / equity / T.

Contract note: WS/HTTP message shapes are documented in backend/README.md. Fields
may be ADDED here but existing fields are never renamed/removed.
"""

from __future__ import annotations
from decimal import Decimal, getcontext
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
import time
import asyncio
import hashlib
import json
try:
    from ..arena import load_arena
    from .deltas import build_delta_payload
except Exception:
    # fallback for direct test loads or non-package exec
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path: sys.path.insert(0, str(root))
    from app.arena import load_arena
    from app.sim.deltas import build_delta_payload

getcontext().prec = 28

# ----- Exact rates from game-mechanics-spec §2 -----
TB_BASE_RECHARGE = Decimal("1.0")
TB_PAUSE_BONUS = Decimal("4.0")
TB_CONSUME = {
    "pause": Decimal("0"),
    "ff2": Decimal("2.0"),
    "ff3": Decimal("5.0"),
    "ff5": Decimal("12.0"),
}
DEFAULT_R = Decimal("1.0")
MATCH_DURATION_REAL = 300.0
IP_START = Decimal("50")
IP_REGEN = Decimal("0.5")
IP_PNL_GRANT_PCT = Decimal("0.10")
IP_SOFT_CAP = Decimal("200")
TB_MAX = Decimal("100")

# ----- Order execution (task-004 §OQ-O4) -----
BASE_SPREAD_PCT = Decimal("0.0007")   # 7 bps adverse on market/stop fills
WIDEN_PCT = Decimal("0.006")          # 0.6% adverse, mid of spec's 0.4-0.8% band

# ----- Sabotage table (spec §7 / task-003): cost (IP), cooldown (real s), duration -----
ABILITIES: Dict[str, Dict[str, Any]] = {
    "delete_sl":    {"cost": Decimal("30"), "cd": Decimal("60")},
    "widen_spread": {"cost": Decimal("25"), "cd": Decimal("45"), "duration": Decimal("15")},
    "fake_news":    {"cost": Decimal("40"), "cd": Decimal("90")},
    "peek":         {"cost": Decimal("60"), "cd": Decimal("120")},
}
# Sabotage victim/caster messages (spec §7 exact wording where given).
SABO_MSG = {
    "delete_sl": "Your stop losses were deleted (sabotage).",
    "widen_spread": "Anomalous spreads detected on your trades.",
    "fake_news": "Possible misinformation in news feed.",
}

EQ_Q = Decimal("0.01")
IP_Q = Decimal("0.01")
TB_Q = Decimal("0.001")

CLOCK_PLAYER_ID = "_clock"  # system actor for bg advance actions (not a human player)


@dataclass
class Action:
    real_ts: float
    sim_t: Decimal
    player_id: str
    type: str
    payload: Dict[str, Any]


@dataclass
class TempoBar:
    level: Decimal = Decimal("100")
    influence: Optional[str] = None
    last_update: float = field(default_factory=time.perf_counter)


class TBResolver:
    """Resolves contested R from player TB influences. Exact rules §2."""
    def __init__(self):
        self.player_tb: Dict[str, TempoBar] = {}
        self.current_r: Decimal = DEFAULT_R

    def set_influence(self, player_id: str, level: Optional[str]) -> None:
        if player_id not in self.player_tb:
            self.player_tb[player_id] = TempoBar()
        # "none"/"" clears influence (player released the control)
        self.player_tb[player_id].influence = level if level not in ("", "none", None) else None
        self._recompute_r()

    def get_r(self) -> Decimal:
        return self.current_r

    def _recompute_r(self) -> None:
        pauses = any(tb.influence == "pause" for tb in self.player_tb.values())
        ffs = [tb.influence for tb in self.player_tb.values() if tb.influence and tb.influence.startswith("ff")]
        if pauses:
            self.current_r = Decimal("0")
        elif ffs:
            r_map = {"ff2": Decimal("2"), "ff3": Decimal("3"), "ff5": Decimal("5")}
            self.current_r = max((r_map.get(l, DEFAULT_R) for l in ffs), default=DEFAULT_R)
        else:
            self.current_r = DEFAULT_R

    def advance(self, real_delta: Decimal, players: List[str]) -> Dict[str, Decimal]:
        consumed: Dict[str, Decimal] = {}
        r = self.current_r
        for pid in players:
            if pid not in self.player_tb:
                self.player_tb[pid] = TempoBar()
            tb = self.player_tb[pid]
            lvl = tb.level
            infl = tb.influence
            recharge = (TB_PAUSE_BONUS if (infl == "pause" and r <= 0) else TB_BASE_RECHARGE) * real_delta
            new_lvl = min(TB_MAX, lvl + recharge)
            # FF that is overridden by a Pause (R==0) delivers no speed -> no cost (task-002 OQ-T2).
            c_rate = TB_CONSUME.get(infl or "", Decimal("0"))
            if infl and infl.startswith("ff") and r <= 0:
                c_rate = Decimal("0")
            consume_amt = c_rate * real_delta
            tb.level = max(Decimal("0"), new_lvl - consume_amt).quantize(TB_Q)
            consumed[pid] = consume_amt.quantize(TB_Q)
            # Force-release an FF holder whose TB is exhausted.
            if tb.level <= 0 and infl and infl.startswith("ff"):
                tb.influence = None
        self._recompute_r()
        return consumed

    def snapshot(self) -> Dict[str, Any]:
        return {
            "r": float(self.current_r),
            "tbs": {pid: float(tb.level) for pid, tb in self.player_tb.items()},
            "influences": {pid: tb.influence for pid, tb in self.player_tb.items()},
        }


class SharedClock:
    """Drives T (replay bar index) using R from TB resolver. Server authoritative.
    T starts 0, advances T += real_delta * R, clamped to max_bars.
    Exposes current_bar with full OHLC for broadcast / LW update.
    """
    def __init__(self, bars: List[Dict[str, Any]]):
        self.bars = bars
        self.max_t = Decimal(len(bars) - 1) if bars else Decimal("0")
        self.T: Decimal = Decimal("0")
        self.tb_resolver = TBResolver()

    def get_r(self) -> Decimal:
        return self.tb_resolver.get_r()

    def get_current_bar(self) -> Dict[str, Any]:
        if not self.bars:
            return {"t": 0, "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0}
        idx = min(int(self.T), len(self.bars) - 1)
        bar = self.bars[idx]
        return {
            "t": bar.get("t", idx),
            "open": float(bar.get("open", bar.get("close", 100))),
            "high": float(bar.get("high", bar.get("close", 100))),
            "low": float(bar.get("low", bar.get("close", 100))),
            "close": float(bar.get("close", 100)),
        }

    def get_bar(self, idx: int) -> Dict[str, Any]:
        idx = max(0, min(idx, len(self.bars) - 1)) if self.bars else 0
        if not self.bars:
            return {"t": 0, "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0}
        bar = self.bars[idx]
        return {
            "t": bar.get("t", idx),
            "open": float(bar.get("open", bar.get("close", 100))),
            "high": float(bar.get("high", bar.get("close", 100))),
            "low": float(bar.get("low", bar.get("close", 100))),
            "close": float(bar.get("close", 100)),
        }

    def get_current_price(self) -> Decimal:
        return Decimal(str(self.get_current_bar()["close"]))

    def advance(self, real_delta: Decimal, players: List[str]) -> Dict[str, Any]:
        r = self.get_r()
        delta_t = real_delta * r
        old_t = self.T
        self.T = min(self.max_t, self.T + delta_t)
        consumed = self.tb_resolver.advance(real_delta, players)
        old_day = int(old_t)
        new_day = int(self.T)
        crossed_bars = list(range(old_day + 1, new_day + 1))
        bar = self.get_current_bar()
        price = Decimal(str(bar["close"]))
        return {
            "t": float(self.T),
            "r": float(r),
            "crossed": bool(crossed_bars),
            "crossed_bars": crossed_bars,
            "current_bar": bar,  # full OHLC for LW update
            "price": float(price),
            "tb_consumed": consumed,
        }


@dataclass
class PlayerState:
    ip: Decimal = IP_START
    equity: Decimal = Decimal("100")
    positions: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # instr -> {"size": dec(signed), "entry": dec}
    orders: List[Dict[str, Any]] = field(default_factory=list)
    realized_pnl: Decimal = Decimal("0")
    cooldowns: Dict[str, float] = field(default_factory=dict)  # ability -> match_time of last cast
    sabo_effects: Dict[str, Any] = field(default_factory=dict)  # e.g. {"widen_until": match_time}
    news_feed: List[Dict[str, Any]] = field(default_factory=list)
    next_order_id: int = 1


class MatchState:
    """Holds full authoritative state. Uses SharedClock for T/R/bar."""
    def __init__(self, match_id: str, arena_id: str, arena_data: Dict[str, Any]):
        self.match_id = match_id
        self.arena_id = arena_id
        self.arena_hash = arena_data["hash"]
        self.content_hash = arena_data.get("content_hash", arena_data["hash"])
        self.label = arena_data["label"]
        self.bars: List[Dict[str, Any]] = arena_data["bars"]
        self.clock = SharedClock(self.bars)
        self.start_real: float = time.perf_counter()
        self.end_real: Optional[float] = None
        self.players: Dict[str, PlayerState] = {}
        self.actions_log: List[Action] = []
        self.events: List[Dict[str, Any]] = []
        self.voice_signaling: Dict[str, Any] = {}
        self._last_advance: float = self.start_real
        self.match_time: Decimal = Decimal("0")  # deterministic real-seconds accumulator
        self._active = True

    # ---- player / accessors -------------------------------------------------
    def add_player(self, player_id: str):
        if player_id == CLOCK_PLAYER_ID:
            return
        if player_id not in self.players:
            self.players[player_id] = PlayerState()
            if player_id not in self.clock.tb_resolver.player_tb:
                self.clock.tb_resolver.player_tb[player_id] = TempoBar()

    def human_players(self) -> List[str]:
        return [p for p in self.players.keys() if p != CLOCK_PLAYER_ID]

    def opponent_of(self, player_id: str) -> Optional[str]:
        return next((p for p in self.players if p != player_id), None)

    def get_current_bar(self) -> Dict[str, Any]:
        return self.clock.get_current_bar()

    def get_price(self) -> Decimal:
        return self.clock.get_current_price()

    # ---- resources ----------------------------------------------------------
    def apply_ip_regen_and_pnl(self, real_delta: Decimal):
        for pid, ps in self.players.items():
            ps.ip = min(IP_SOFT_CAP, ps.ip + IP_REGEN * real_delta).quantize(IP_Q)

    def _grant_ip_on_profit(self, ps: PlayerState, realized: Decimal):
        """+10% of realized P&L on profitable closes (spec §2). Losses grant nothing."""
        if realized > 0:
            ps.ip = min(IP_SOFT_CAP, ps.ip + realized * IP_PNL_GRANT_PCT).quantize(IP_Q)

    # ---- P&L ----------------------------------------------------------------
    def _position_unrealized(self, pos: Dict[str, Any], price: Decimal) -> Decimal:
        size = pos.get("size", Decimal("0"))
        if size == 0:
            return Decimal("0")
        entry = pos.get("entry", price)
        if entry == 0:
            return Decimal("0")
        # task-004 OQ-O5: size * (price-entry)/entry  (size signed: long>0, short<0)
        return size * (price - entry) / entry

    def player_unrealized(self, ps: PlayerState, price: Decimal) -> Decimal:
        return sum((self._position_unrealized(p, price) for p in ps.positions.values()), Decimal("0"))

    def _update_equity(self, ps: PlayerState, current_price: Decimal):
        unrealized = self.player_unrealized(ps, current_price)
        ps.equity = (Decimal("100") + ps.realized_pnl + unrealized).quantize(EQ_Q)

    def _apply_fill(self, ps: PlayerState, instr: str, eff_size: Decimal, fill_price: Decimal) -> Decimal:
        """Apply a signed fill to a netted per-instrument position.

        Returns realized P&L booked by this fill (also grants IP on profit).
        Handles open / add (avg entry) / reduce / full close / flip.
        """
        realized = Decimal("0")
        pos = ps.positions.get(instr)
        if pos is None or pos.get("size", Decimal("0")) == 0:
            ps.positions[instr] = {"size": eff_size, "entry": fill_price}
            return realized

        old_size = pos["size"]
        entry = pos["entry"]
        same_dir = (old_size > 0) == (eff_size > 0)
        if same_dir:
            new_size = old_size + eff_size
            pos["entry"] = (old_size * entry + eff_size * fill_price) / new_size
            pos["size"] = new_size
        else:
            if abs(eff_size) <= abs(old_size):
                # pure reduction / exact close; entry basis unchanged
                realized = -eff_size * (fill_price - entry) / entry
                new_size = old_size + eff_size
                if new_size == 0:
                    del ps.positions[instr]
                else:
                    pos["size"] = new_size
            else:
                # flip: realize the whole old position, open remainder at fill price
                realized = old_size * (fill_price - entry) / entry
                remainder = old_size + eff_size  # sign of eff_size
                pos["size"] = remainder
                pos["entry"] = fill_price

        ps.realized_pnl = (ps.realized_pnl + realized)
        self._grant_ip_on_profit(ps, realized)
        return realized

    # ---- slippage / spread --------------------------------------------------
    def _widen_active(self, ps: PlayerState) -> bool:
        until = ps.sabo_effects.get("widen_until")
        return until is not None and self.match_time < Decimal(str(until))

    def _fill_with_slippage(self, ps: PlayerState, base_price: Decimal, eff_size: Decimal, otype: str) -> Decimal:
        adverse = BASE_SPREAD_PCT if otype in ("market", "stop") else Decimal("0")
        if self._widen_active(ps):
            adverse += WIDEN_PCT  # widen poisons market AND resting (limit) fills (task-003 OQ-SAB4)
        if eff_size > 0:   # buy fills higher
            return base_price * (Decimal("1") + adverse)
        return base_price * (Decimal("1") - adverse)  # sell/close fills lower

    # ---- resting order processing (per crossed bar) -------------------------
    def _trigger_and_base_price(self, o: Dict[str, Any], bar: Dict[str, Any]) -> Tuple[bool, Optional[Decimal]]:
        otype = o.get("type", "market")
        side = o.get("side", "long")
        price = o.get("price")
        if price is None:
            return False, None
        price = Decimal(str(price))
        op = Decimal(str(bar["open"]))
        hi = Decimal(str(bar["high"]))
        lo = Decimal(str(bar["low"]))
        if otype == "limit":
            if side == "long":   # buy limit: fill if price dips to limit (or gap below at open)
                if op <= price:
                    return True, op
                if lo <= price:
                    return True, price
            else:                # sell limit: fill if price rises to limit (or gap above at open)
                if op >= price:
                    return True, op
                if hi >= price:
                    return True, price
        elif otype == "stop":
            if side == "long":   # buy stop: triggers when price rises through stop
                if op >= price:
                    return True, op
                if hi >= price:
                    return True, price
            else:                # sell stop (incl. long stop-loss): triggers when price falls through
                if op <= price:
                    return True, op
                if lo <= price:
                    return True, price
        return False, None

    def _process_resting_orders(self, pid: str, ps: PlayerState, bar: Dict[str, Any], day: int) -> List[Dict[str, Any]]:
        fills: List[Dict[str, Any]] = []
        remaining: List[Dict[str, Any]] = []
        # deterministic order: by order id
        for o in sorted(ps.orders, key=lambda x: x.get("id", 0)):
            triggered, base_price = self._trigger_and_base_price(o, bar)
            if not triggered:
                remaining.append(o)
                continue
            side = o.get("side", "long")
            size = Decimal(str(o.get("size", 1)))
            otype = o.get("type", "market")
            eff_size = size if side == "long" else -size
            fill_price = self._fill_with_slippage(ps, base_price, eff_size, otype)
            realized = self._apply_fill(ps, o.get("instr", "X"), eff_size, fill_price)
            rec = {
                "player": pid, "instr": o.get("instr", "X"), "price": float(fill_price),
                "size": float(eff_size), "side": side, "type": otype,
                "t": float(self.clock.T), "realized": float(realized.quantize(EQ_Q)),
                "order_id": o.get("id"),
            }
            fills.append(rec)
            self.events.append({"type": "fill", **rec})
        ps.orders = remaining
        return fills

    # ---- advance ------------------------------------------------------------
    def advance(self, real_delta: Decimal) -> Dict[str, Any]:
        if not self._active:
            return {"t": float(self.clock.T), "r": float(self.clock.get_r()), "fills": [], "crossed_bars": []}
        players = self.human_players()
        self.match_time += real_delta
        deltas = self.clock.advance(real_delta, players)
        self.apply_ip_regen_and_pnl(real_delta)

        fills: List[Dict[str, Any]] = []
        for day in deltas.get("crossed_bars", []):
            bar = self.clock.get_bar(day)
            for pid in sorted(players):
                fills.extend(self._process_resting_orders(pid, self.players[pid], bar, day))

        current_price = self.clock.get_current_price()
        for pid in players:
            self._update_equity(self.players[pid], current_price)

        deltas["fills"] = fills
        return deltas

    # ---- action ingestion ---------------------------------------------------
    def queue_action(self, player_id: str, action_type: str, payload: Dict[str, Any], *, record: bool = True) -> bool:
        real_ts = time.perf_counter()
        sim_t = self.clock.T
        if record:
            act = Action(real_ts=real_ts, sim_t=sim_t, player_id=player_id, type=action_type, payload=payload)
            self.actions_log.append(act)
        return self._apply_action(player_id, action_type, payload, sim_t=sim_t, real_ts=real_ts)

    def _apply_action(self, player_id: str, action_type: str, payload: Dict[str, Any],
                      sim_t: Optional[Decimal] = None, real_ts: Optional[float] = None) -> bool:
        sim_t = sim_t if sim_t is not None else self.clock.T

        if action_type == "advance":
            real_delta = Decimal(str(payload.get("real_delta", payload.get("delta", 1))))
            self.advance(real_delta)
            return True

        ps = self.players.get(player_id)
        if not ps:
            return False

        if action_type in ("tb_influence", "set_tb"):
            level = payload.get("level", "ff2")
            self.clock.tb_resolver.set_influence(player_id, level)
            self.events.append({"type": "tb", "player": player_id, "level": level, "t": float(sim_t)})
            return True

        elif action_type in ("submit_order", "order", "place_order"):
            return self._handle_submit_order(player_id, ps, payload, sim_t)

        elif action_type in ("close", "close_position"):
            return self._handle_close(player_id, ps, payload, sim_t)

        elif action_type == "cancel_order":
            oid = payload.get("id", payload.get("order_id"))
            before = len(ps.orders)
            ps.orders = [o for o in ps.orders if o.get("id") != oid]
            return len(ps.orders) != before

        elif action_type == "modify_order":
            oid = payload.get("id", payload.get("order_id"))
            for o in ps.orders:
                if o.get("id") == oid:
                    if "price" in payload:
                        o["price"] = payload["price"]
                    if "size" in payload:
                        o["size"] = float(Decimal(str(payload["size"])))
                    return True
            return False

        elif action_type in ("ip_spend", "sabotage", "ability"):
            return self._handle_ability(player_id, ps, payload, sim_t)

        elif action_type.startswith("voice_"):
            self.voice_signaling[action_type] = {"from": player_id, **payload}
            return True

        return False

    def _handle_submit_order(self, player_id: str, ps: PlayerState, payload: Dict[str, Any], sim_t: Decimal) -> bool:
        otype = payload.get("type", "market")
        instr = payload.get("instr", "X")
        side = payload.get("side", "long")
        size = Decimal(str(payload.get("size", 1)))
        price = payload.get("price")
        oid = ps.next_order_id
        ps.next_order_id += 1

        if otype == "market":
            eff_size = size if side == "long" else -size
            base_price = self.get_price()
            fill_price = self._fill_with_slippage(ps, base_price, eff_size, "market")
            realized = self._apply_fill(ps, instr, eff_size, fill_price)
            rec = {
                "player": player_id, "instr": instr, "price": float(fill_price),
                "size": float(eff_size), "side": side, "type": "market",
                "t": float(sim_t), "realized": float(realized.quantize(EQ_Q)), "order_id": oid,
            }
            self.events.append({"type": "fill", **rec})
            self._update_equity(ps, base_price)
            return True

        # resting limit/stop order
        ps.orders.append({
            "id": oid,
            "type": otype,
            "instr": instr,
            "side": side,
            "size": float(size),
            "price": price,
        })
        return True

    def _handle_close(self, player_id: str, ps: PlayerState, payload: Dict[str, Any], sim_t: Decimal) -> bool:
        instr = payload.get("instr", "X")
        pos = ps.positions.get(instr)
        if not pos or pos.get("size", Decimal("0")) == 0:
            return False
        size = pos["size"]
        frac = Decimal(str(payload.get("fraction", 1)))
        frac = max(Decimal("0"), min(Decimal("1"), frac))
        close_size = size * frac           # signed amount we currently hold for this fraction
        eff_size = -close_size             # opposite to flatten
        base_price = self.get_price()
        fill_price = self._fill_with_slippage(ps, base_price, eff_size, "market")
        realized = self._apply_fill(ps, instr, eff_size, fill_price)
        self.events.append({
            "type": "fill", "player": player_id, "instr": instr, "price": float(fill_price),
            "size": float(eff_size), "side": "short" if eff_size < 0 else "long", "type_": "close",
            "t": float(sim_t), "realized": float(realized.quantize(EQ_Q)),
        })
        self._update_equity(ps, base_price)
        return True

    def _handle_ability(self, player_id: str, ps: PlayerState, payload: Dict[str, Any], sim_t: Decimal) -> bool:
        ability = payload.get("ability", "")
        spec = ABILITIES.get(ability)
        cost = Decimal(str(payload.get("cost", spec["cost"] if spec else 0)))
        cd = Decimal(str(payload.get("cd", spec["cd"] if spec else 0)))
        now = self.match_time

        # cooldown (real seconds via deterministic match_time accumulator)
        last = ps.cooldowns.get(ability)
        if last is not None and (now - Decimal(str(last))) < cd:
            self.events.append({"type": "ability_rejected", "player": player_id, "ability": ability,
                                "reason": "cooldown", "t": float(sim_t)})
            return False
        if ps.ip < cost:
            self.events.append({"type": "ability_rejected", "player": player_id, "ability": ability,
                                "reason": "insufficient_ip", "t": float(sim_t)})
            return False

        ps.ip = (ps.ip - cost).quantize(IP_Q)
        ps.cooldowns[ability] = float(now)

        target_id = payload.get("target_player") or self.opponent_of(player_id)
        target = self.players.get(target_id) if target_id else None

        if ability == "delete_sl":
            if target is not None:
                removed = [o for o in target.orders if o.get("type") == "stop"]
                target.orders = [o for o in target.orders if o.get("type") != "stop"]
                self.events.append({
                    "type": "sabo", "ability": ability, "from": player_id, "victim": target_id,
                    "removed": len(removed), "msg": SABO_MSG["delete_sl"], "t": float(sim_t),
                })
        elif ability == "widen_spread":
            if target is not None:
                dur = spec["duration"] if spec else Decimal("15")
                target.sabo_effects["widen_until"] = float((now + dur))
                self.events.append({
                    "type": "sabo", "ability": ability, "from": player_id, "victim": target_id,
                    "until": float(now + dur), "msg": SABO_MSG["widen_spread"], "t": float(sim_t),
                })
        elif ability == "fake_news":
            if target is not None:
                headline = self._fake_headline(sim_t)
                target.news_feed.append({"t": float(sim_t), "headline": headline, "fake": True})
                self.events.append({
                    "type": "sabo", "ability": ability, "from": player_id, "victim": target_id,
                    "msg": SABO_MSG["fake_news"], "t": float(sim_t),
                })
        elif ability == "peek":
            headline = self._peek_headline(sim_t)
            ps.news_feed.append({"t": float(sim_t), "headline": headline, "peek": True})
            self.events.append({
                "type": "peek", "from": player_id, "to": player_id, "private": True,
                "headline": headline, "t": float(sim_t),
            })
        else:
            # generic spend (e.g. feed unlock) — IP already deducted, just log.
            self.events.append({"type": "ip_spend", "player": player_id, "ability": ability, "t": float(sim_t)})
        return True

    # ---- deterministic placeholder news (no live RNG) -----------------------
    def _fake_headline(self, sim_t: Decimal) -> str:
        pool = [
            "Sources: surprise rate cut imminent — risk assets to rip.",
            "Leaked memo hints at major earnings miss across sector.",
            "Regulators reportedly preparing emergency liquidity facility.",
            "Whisper: large fund unwinding position into the close.",
        ]
        h = int(hashlib.sha256(f"{self.content_hash}:{int(sim_t)}".encode()).hexdigest(), 16)
        return pool[h % len(pool)]

    def _peek_headline(self, sim_t: Decimal) -> str:
        day = int(sim_t)
        bar = self.clock.get_bar(day)
        prev = self.clock.get_bar(max(0, day - 1))
        move = bar["close"] - prev["close"]
        if move > 0:
            tone = "rallies"
        elif move < 0:
            tone = "sells off"
        else:
            tone = "trades flat"
        return f"Arena Day {day}: market {tone} ({move:+.2f} normalized)."

    # ---- win condition (spec §8) -------------------------------------------
    def determine_result(self) -> Dict[str, Any]:
        price = self.get_price()
        per_player: Dict[str, Dict[str, Any]] = {}
        for pid in self.human_players():
            ps = self.players[pid]
            unrealized = self.player_unrealized(ps, price)
            equity = (Decimal("100") + ps.realized_pnl + unrealized).quantize(EQ_Q)
            per_player[pid] = {
                "equity": float(equity),
                "realized_pnl": float(ps.realized_pnl.quantize(EQ_Q)),
                "unrealized_pnl": float(unrealized.quantize(EQ_Q)),
                "return_pct": float((equity - Decimal("100")).quantize(EQ_Q)),
                "_equity_dec": equity,
            }
        winner: Optional[str] = None
        is_draw = False
        if per_player:
            best = max(p["_equity_dec"] for p in per_player.values())
            leaders = [pid for pid, p in per_player.items() if p["_equity_dec"] == best]
            if len(leaders) == 1:
                winner = leaders[0]
            else:
                is_draw = True
        for p in per_player.values():
            p.pop("_equity_dec", None)
        return {"winner": winner, "is_draw": is_draw, "players": per_player}

    # ---- snapshot / hash ----------------------------------------------------
    def snapshot(self, full: bool = False) -> Dict[str, Any]:
        cur_bar = self.get_current_bar()
        price = self.get_price()
        result = self.determine_result()
        players_out: Dict[str, Any] = {}
        for pid in self.human_players():
            ps = self.players[pid]
            unrealized = self.player_unrealized(ps, price)
            equity = (Decimal("100") + ps.realized_pnl + unrealized).quantize(EQ_Q)
            players_out[pid] = {
                "ip": float(ps.ip),
                "equity": float(equity),
                "realized_pnl": float(ps.realized_pnl.quantize(EQ_Q)),
                "unrealized_pnl": float(unrealized.quantize(EQ_Q)),
                "return_pct": float((equity - Decimal("100")).quantize(EQ_Q)),
                "positions": {k: {"size": float(v.get("size", 0)), "entry": float(v.get("entry", 100))}
                              for k, v in ps.positions.items()},
                "orders": ps.orders,
                "cooldowns": {k: float(v) for k, v in ps.cooldowns.items()},
                "sabo_effects": ps.sabo_effects,
                "news_feed": ps.news_feed[-10:],
            }
        return {
            "match_id": self.match_id,
            "arena_id": self.arena_id,
            "arena_hash": self.arena_hash,
            "content_hash": self.content_hash,
            "label": self.label,
            "T": float(self.clock.T),
            "r": float(self.clock.get_r()),
            "match_time": float(self.match_time),
            "time_left": max(0.0, MATCH_DURATION_REAL - float(self.match_time)),
            "tb": self.clock.tb_resolver.snapshot(),
            "current_bar": cur_bar,  # full OHLC for LW
            "players": players_out,
            "is_over": self.is_over(),
            "winner": result["winner"],
            "is_draw": result["is_draw"],
            "result": result,
            "recent_events": self.events[-10:],
        }

    def compute_state_hash(self) -> str:
        """Stable hash over canonical, quantized, sort-keyed state (anti-cheat)."""
        price = self.get_price()
        players = []
        for pid in sorted(self.human_players()):
            ps = self.players[pid]
            unrealized = self.player_unrealized(ps, price)
            equity = (Decimal("100") + ps.realized_pnl + unrealized).quantize(EQ_Q)
            positions = sorted(
                [[k, str(v.get("size", Decimal("0"))), str(v.get("entry", Decimal("0")))]
                 for k, v in ps.positions.items()]
            )
            orders = sorted(
                [[o.get("id"), o.get("type"), o.get("instr"), o.get("side"),
                  str(o.get("size")), str(o.get("price"))] for o in ps.orders],
                key=lambda x: (x[0] is None, x[0]),
            )
            players.append({
                "id": pid,
                "equity": str(equity),
                "ip": str(ps.ip.quantize(IP_Q)),
                "realized": str(ps.realized_pnl.quantize(EQ_Q)),
                "tb": str(self.clock.tb_resolver.player_tb.get(pid, TempoBar()).level),
                "positions": positions,
                "orders": orders,
            })
        state = {
            "T": str(self.clock.T.quantize(Decimal("0.000001"))),
            "R": str(self.clock.get_r()),
            "content_hash": self.content_hash,
            "players": players,
        }
        stable = json.dumps(state, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(stable.encode()).hexdigest()[:12]

    def is_over(self) -> bool:
        return self.match_time >= Decimal(str(MATCH_DURATION_REAL)) or self.clock.T >= self.clock.max_t


class SimulationEngine:
    """Main engine exposed to rooms/main. Drives clock, handles receive, broadcasts full deltas."""
    def __init__(self, match_id: str, arena_id: str):
        arena_data = load_arena(arena_id)  # real arena data via loader
        self.state = MatchState(match_id, arena_id, arena_data)
        self.match_id = match_id
        self._broadcast_cb = None
        self._task: Optional[asyncio.Task] = None

    def set_broadcast(self, cb):
        self._broadcast_cb = cb

    async def run_clock(self):
        self.state._last_advance = time.perf_counter()
        tick = 1.0 / 15  # ~15Hz internal, broadcast on change or rate
        while self.state._active and not self.state.is_over():
            now = time.perf_counter()
            delta = Decimal(str(now - self.state._last_advance))
            if delta > 0:
                self.state.queue_action(CLOCK_PLAYER_ID, "advance", {"real_delta": str(delta)})
                self.state._last_advance = now
                if self._broadcast_cb:
                    try:
                        await self._broadcast_cb(build_delta_payload(self.state))
                    except Exception:
                        pass
            await asyncio.sleep(tick)
        self.state._active = False
        if self._broadcast_cb:
            result = self.state.determine_result()
            try:
                await self._broadcast_cb({
                    "type": "match_end",
                    "final": self.state.snapshot(full=True),
                    "winner": result["winner"],
                    "is_draw": result["is_draw"],
                    "result": result,
                    "content_hash": self.state.content_hash,
                })
            except Exception:
                pass

    def start(self):
        if not self._task:
            self._task = asyncio.create_task(self.run_clock())

    def stop(self):
        self.state._active = False

    def receive_action(self, player_id: str, action_type: str, payload: Dict[str, Any]) -> Tuple[bool, str]:
        ok = self.state.queue_action(player_id, action_type, payload)
        return ok, "ok" if ok else "rejected"

    def get_snapshot(self) -> Dict[str, Any]:
        return self.state.snapshot(full=True)

    def verify_replay(self, actions: List[Action]) -> Dict[str, Any]:
        """Re-sim from arena + action log; verified only when state hash + equity + T match."""
        orig = self.state
        fresh = SimulationEngine(self.match_id, self.state.arena_id)
        for pid in orig.human_players():
            fresh.state.add_player(pid)

        for act in sorted(actions, key=lambda a: (a.real_ts, float(a.sim_t))):
            fresh.state._apply_action(act.player_id, act.type, act.payload,
                                      sim_t=act.sim_t, real_ts=act.real_ts)

        orig_hash = orig.compute_state_hash()
        fresh_hash = fresh.state.compute_state_hash()
        orig_equity = {pid: float(orig.players[pid].equity) for pid in orig.human_players()}
        fresh_equity = {pid: float(fresh.state.players[pid].equity) for pid in fresh.state.human_players()}
        orig_t = float(orig.clock.T)
        fresh_t = float(fresh.state.clock.T)
        verified = orig_hash == fresh_hash and orig_equity == fresh_equity and orig_t == fresh_t

        return {
            "final_hash": fresh_hash,
            "original_hash": orig_hash,
            "final_equity": fresh_equity,
            "original_equity": orig_equity,
            "final_t": fresh_t,
            "original_t": orig_t,
            "content_hash": fresh.state.content_hash,
            "verified": verified,
        }
