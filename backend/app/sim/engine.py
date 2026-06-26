"""Authoritative simulation engine for chart-fights.

Implements per GDD, game-mechanics-spec.md (T/R/TB/IP, orders, P&L), task-005 realtime, task-002/004, architecture.
- Loads real arena data using arena_loader (1656 arenas supported via index/parquet).
- SharedClock drives T (replay bar index, fractional) using R (contested rate).
- In advance/receive: update real current bar (full OHLC), apply basic trades to equity using real bar close prices (market fills at current close).
- Broadcast full deltas: current_bar OHLC (for LW series.update), TB/IP, events, equity, orders.
- receive handles 'submit_order' (market -> real fill at current close).
- content_hash for anti-cheat (from arena, used in snapshots/replay verify).
- Deterministic: Decimal everywhere for equity/TB/P&L, action log, re-sim verify.
- Basic trades: market orders fill immediately at close; positions track size + entry_price for correct mtm from entry (not hardcoded 100).
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

# Exact rates from game-mechanics-spec §2
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
BASE_SPREAD_PCT = Decimal("0.0005")  # for future spread on fills
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

    def set_influence(self, player_id: str, level: str) -> None:
        if player_id not in self.player_tb:
            self.player_tb[player_id] = TempoBar()
        self.player_tb[player_id].influence = level
        self._recompute_r()

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

    def get_r(self) -> Decimal:
        return self.current_r

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
            new_lvl = min(Decimal("100"), lvl + recharge)
            c_rate = TB_CONSUME.get(infl or "", Decimal("0"))
            consume_amt = c_rate * real_delta
            tb.level = max(Decimal("0"), new_lvl - consume_amt).quantize(Decimal("0.001"))
            consumed[pid] = consume_amt.quantize(Decimal("0.001"))
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
    T starts 0, advances T += real_delta * R , clamped to max_bars.
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
        # Ensure full OHLC
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
        crossed = int(self.T) > int(old_t)
        bar = self.get_current_bar()
        price = Decimal(str(bar["close"]))
        return {
            "t": float(self.T),
            "r": float(r),
            "crossed": crossed,
            "current_bar": bar,  # full OHLC for LW update
            "price": float(price),
            "tb_consumed": consumed,
        }


@dataclass
class PlayerState:
    ip: Decimal = IP_START
    equity: Decimal = Decimal("100")
    positions: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # instr -> {"size": dec, "entry": dec}
    orders: List[Dict[str, Any]] = field(default_factory=list)
    realized_pnl: Decimal = Decimal("0")
    cooldowns: Dict[str, float] = field(default_factory=dict)
    sabo_effects: Dict[str, Any] = field(default_factory=dict)
    news_feed: List[Dict[str, Any]] = field(default_factory=list)


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
        self._active = True

    def add_player(self, player_id: str):
        if player_id not in self.players:
            self.players[player_id] = PlayerState()
            if player_id not in self.clock.tb_resolver.player_tb:
                self.clock.tb_resolver.player_tb[player_id] = TempoBar()

    def get_current_bar(self) -> Dict[str, Any]:
        return self.clock.get_current_bar()

    def get_price(self) -> Decimal:
        return self.clock.get_current_price()

    def apply_ip_regen_and_pnl(self, real_delta: Decimal):
        for pid, ps in self.players.items():
            ps.ip = min(Decimal("200"), ps.ip + IP_REGEN * real_delta)
            # basic: IP also from realized later on close

    def _update_equity(self, ps: PlayerState, current_price: Decimal):
        """Apply basic trades equity using real prices: unrealized from entry price in bar closes."""
        mtm = Decimal("0")
        for instr, pos in ps.positions.items():
            size = pos.get("size", Decimal("0"))
            entry = pos.get("entry", current_price)
            mtm += size * (current_price - entry)
        ps.equity = (Decimal("100") + ps.realized_pnl + mtm).quantize(Decimal("0.01"))

    def advance(self, real_delta: Decimal) -> Dict[str, Any]:
        if not self._active:
            return {"delta_t": 0}
        deltas = self.clock.advance(real_delta, list(self.players.keys()))
        self.apply_ip_regen_and_pnl(real_delta)
        current_price = self.clock.get_current_price()
        current_bar = deltas["current_bar"]

        fills = []
        # Process any resting orders at bar update (basic: market already filled, limits/stops on close for MVP)
        for pid, ps in self.players.items():
            remaining = []
            for o in ps.orders:
                otype = o.get("type", "market")
                filled = False
                fill_price = current_price
                if otype == "market":
                    filled = True
                elif otype == "limit":
                    lim = Decimal(str(o.get("price", current_price)))
                    side = o.get("side", "long")
                    if (side == "long" and current_price <= lim) or (side == "short" and current_price >= lim):
                        filled = True
                elif otype == "stop":
                    stop = Decimal(str(o.get("price", current_price)))
                    side = o.get("side", "long")
                    if (side == "long" and current_price <= stop) or (side == "short" and current_price >= stop):
                        filled = True
                if filled:
                    # real fill at current close
                    instr = o.get("instr", "X")
                    size = Decimal(str(o.get("size", 1)))
                    side = o.get("side", "long")
                    eff_size = size if side == "long" else -size
                    # apply basic trade: record position or close
                    if instr not in ps.positions:
                        ps.positions[instr] = {"size": Decimal("0"), "entry": fill_price}
                    pos = ps.positions[instr]
                    old_size = pos["size"]
                    # simplistic net: average entry for now (MVP basic)
                    new_size = old_size + eff_size
                    if new_size != 0 and old_size != 0:
                        # weighted avg entry approx
                        pos["entry"] = ((old_size * pos["entry"] + eff_size * fill_price) / new_size) if new_size != 0 else fill_price
                    else:
                        pos["entry"] = fill_price
                    pos["size"] = new_size
                    if new_size == 0:
                        # closed, realize pnl? basic: keep realized separate on full close later
                        pass
                    fills.append({
                        "player": pid,
                        "instr": instr,
                        "price": float(fill_price),
                        "size": float(eff_size),
                        "side": side,
                        "type": otype,
                        "t": deltas["t"],
                    })
                    # grant IP on profitable? simplistic, defer detailed
                    if o.get("close", False):  # future
                        pass
                else:
                    remaining.append(o)
            ps.orders = remaining

        # mark to market all using real current price
        for pid, ps in self.players.items():
            self._update_equity(ps, current_price)

        deltas["fills"] = fills
        deltas["current_bar"] = current_bar  # ensure
        return deltas

    def queue_action(self, player_id: str, action_type: str, payload: Dict[str, Any], *, record: bool = True) -> bool:
        real_ts = time.perf_counter()
        sim_t = self.clock.T
        if record:
            act = Action(real_ts=real_ts, sim_t=sim_t, player_id=player_id, type=action_type, payload=payload)
            self.actions_log.append(act)
        return self._apply_action(player_id, action_type, payload, sim_t=sim_t)

    def _apply_action(self, player_id: str, action_type: str, payload: Dict[str, Any], sim_t: Optional[Decimal] = None) -> bool:
        sim_t = sim_t if sim_t is not None else self.clock.T

        if action_type == "advance":
            real_delta = Decimal(str(payload.get("real_delta", payload.get("delta", 1))))
            self.advance(real_delta)
            return True

        ps = self.players.get(player_id)
        if not ps:
            return False

        if action_type in ("tb_influence", "set_tb"):
            self.clock.tb_resolver.set_influence(player_id, payload.get("level", "ff2"))
            self.events.append({"type": "tb", "player": player_id, "level": payload.get("level"), "t": float(sim_t)})
            return True

        elif action_type in ("submit_order", "order"):
            # handle 'submit_order' as specified; support alias
            otype = payload.get("type", "market")
            instr = payload.get("instr", "X")
            side = payload.get("side", "long")
            size = Decimal(str(payload.get("size", 1)))
            price = payload.get("price")
            order = {
                "id": len(ps.orders) + 1,
                "type": otype,
                "instr": instr,
                "side": side,
                "size": float(size),
                "price": price,
            }
            ps.orders.append(order)
            # immediate market fill at current close (real price from bar)
            if otype == "market":
                current_price = self.get_price()
                eff_size = size if side == "long" else -size
                if instr not in ps.positions:
                    ps.positions[instr] = {"size": Decimal("0"), "entry": current_price}
                pos = ps.positions[instr]
                old_size = pos["size"]
                new_size = old_size + eff_size
                if new_size != 0 and old_size != 0:
                    pos["entry"] = ((old_size * pos["entry"] + eff_size * current_price) / new_size) if new_size != 0 else current_price
                else:
                    pos["entry"] = current_price
                pos["size"] = new_size
                fill_rec = {
                    "player": player_id, "instr": instr, "price": float(current_price),
                    "size": float(eff_size), "side": side, "type": "market", "t": float(sim_t)
                }
                self.events.append({"type": "fill", **fill_rec})
                self._update_equity(ps, current_price)
                # remove the order since filled in receive for instant market
                ps.orders.pop() if ps.orders else None
            return True

        elif action_type == "ip_spend":
            cost = Decimal(str(payload.get("cost", 0)))
            if ps.ip < cost:
                return False
            ps.ip -= cost
            target = payload.get("target_player") or next((p for p in self.players if p != player_id), None)
            if target and target in self.players:
                tps = self.players[target]
                ability = payload.get("ability", "")
                if ability == "delete_sl":
                    tps.orders = [o for o in tps.orders if o.get("type") != "stop"]
                    self.events.append({
                        "type": "sabo", "ability": ability, "victim": target,
                        "msg": f"SLs deleted at T~{float(sim_t):.0f}"
                    })
            return True

        elif action_type.startswith("voice_"):
            self.voice_signaling[action_type] = {"from": player_id, **payload}
            return True

        elif action_type == "cancel_order":
            oid = payload.get("id")
            ps.orders = [o for o in ps.orders if o.get("id") != oid]
            return True

        return False

    def snapshot(self, full: bool = False) -> Dict[str, Any]:
        cur_bar = self.get_current_bar()
        return {
            "match_id": self.match_id,
            "arena_id": self.arena_id,
            "arena_hash": self.arena_hash,
            "content_hash": self.content_hash,
            "label": self.label,
            "T": float(self.clock.T),
            "r": float(self.clock.get_r()),
            "tb": self.clock.tb_resolver.snapshot(),
            "current_bar": cur_bar,  # full OHLC for LW
            "players": {
                pid: {
                    "ip": float(ps.ip),
                    "equity": float(ps.equity),
                    "positions": {k: {"size": float(v.get("size", 0)), "entry": float(v.get("entry", 100))} for k, v in ps.positions.items()},
                    "orders": ps.orders,
                } for pid, ps in self.players.items()
            },
            "recent_events": self.events[-10:],
        }

    def compute_state_hash(self) -> str:
        # stable using Decimal friendly snapshot (content_hash included)
        snap = self.snapshot()
        # quantize for stable hash
        stable = json.dumps(snap, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(stable.encode()).hexdigest()[:12]

    def is_over(self) -> bool:
        return (time.perf_counter() - self.start_real) >= MATCH_DURATION_REAL


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
        last_broadcast_t = 0.0
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
            await self._broadcast_cb({"type": "match_end", "final": self.state.snapshot(full=True), "content_hash": self.state.content_hash})

    def start(self):
        if not self._task:
            self._task = asyncio.create_task(self.run_clock())

    def stop(self):
        self.state._active = False

    def receive_action(self, player_id: str, action_type: str, payload: Dict[str, Any]) -> Tuple[bool, str]:
        # receive handles submit_order with real fill
        ok = self.state.queue_action(player_id, action_type, payload)
        # immediate delta broadcast on action if possible (for responsiveness)
        if ok and self._broadcast_cb:
            try:
                snap = self.state.snapshot()
                # use asyncio to schedule if needed, but for sync path send via cb if loop allows
                # for simplicity, cb will get full on next tick; action acks separate
            except Exception:
                pass
        return ok, "ok" if ok else "rejected"

    def get_snapshot(self) -> Dict[str, Any]:
        snap = self.state.snapshot(full=True)
        return snap

    def verify_replay(self, actions: List[Action]) -> Dict[str, Any]:
        """Re-sim from arena + action log; verified only when state hash + equity + T match."""
        orig = self.state
        fresh = SimulationEngine(self.match_id, self.state.arena_id)
        for pid in orig.players:
            fresh.state.add_player(pid)

        for act in sorted(actions, key=lambda a: (a.real_ts, float(a.sim_t))):
            fresh.state._apply_action(act.player_id, act.type, act.payload, sim_t=act.sim_t)

        orig_hash = orig.compute_state_hash()
        fresh_hash = fresh.state.compute_state_hash()
        orig_equity = {pid: float(ps.equity) for pid, ps in orig.players.items()}
        fresh_equity = {pid: float(ps.equity) for pid, ps in fresh.state.players.items()}
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
