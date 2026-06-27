"""Lightweight bot trader for quick-match fallback (#6).

The bot drives the *same* `receive_action` path a human uses, so every move is
recorded in the action log and stays replay-verifiable. Its decisions may use
wall-clock/random timing — only the resulting actions are persisted, and replay
re-applies actions rather than re-running this logic, so determinism holds.

Strategy: simple momentum. Watch the revealed close, lean into the short-term
trend with a bracketed market order, take profits / cut losses, and occasionally
poke tempo or sabotage to feel alive. Intentionally beatable.
"""
from __future__ import annotations
import asyncio
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .sim.engine import SimulationEngine


class BotTrader:
    def __init__(self, engine: "SimulationEngine", player_id: str = "p2", seed: int | None = None):
        self.engine = engine
        self.pid = player_id
        self.rng = random.Random(seed if seed is not None else hash(engine.match_id) & 0xFFFFFFFF)
        self._task: asyncio.Task | None = None
        self._recent: list[float] = []

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self.run())

    def stop(self) -> None:
        if self._task:
            self._task.cancel()
            self._task = None

    def _has_position(self) -> bool:
        ps = self.engine.state.players.get(self.pid)
        if not ps:
            return False
        pos = ps.positions.get("X")
        return bool(pos and pos.get("size", 0) != 0)

    def _unrealized_pct(self) -> float:
        ps = self.engine.state.players.get(self.pid)
        if not ps:
            return 0.0
        try:
            price = self.engine.state.get_price()
            return float(self.engine.state.player_unrealized(ps, price))
        except Exception:
            return 0.0

    async def run(self) -> None:
        # let a bar or two reveal before trading
        await asyncio.sleep(1.0)
        while self.engine.state._active and not self.engine.state.is_over():
            try:
                self._step()
            except Exception:
                pass
            await asyncio.sleep(self.rng.uniform(1.5, 3.0))

    def _step(self) -> None:
        st = self.engine.state
        if self.pid not in st.players:
            return
        bar = st.get_current_bar()
        close = float(bar.get("close", 100.0))
        self._recent.append(close)
        self._recent = self._recent[-6:]

        # Manage an open position: bank wins / cut losses.
        if self._has_position():
            up = self._unrealized_pct()
            if up > 1.2 or up < -0.9 or self.rng.random() < 0.12:
                self.engine.receive_action(self.pid, "close", {"instr": "X", "fraction": 1.0})
            return

        # No position: lean into short-term momentum.
        if len(self._recent) < 2:
            return
        trend = self._recent[-1] - self._recent[0]
        if abs(trend) < close * 0.001 and self.rng.random() < 0.5:
            return  # flat / undecided — sit out sometimes
        side = "long" if trend >= 0 else "short"
        size = self.rng.choice([15, 20, 25, 30])
        tp_pct = self.rng.uniform(0.015, 0.035)
        sl_pct = self.rng.uniform(0.01, 0.02)
        if side == "long":
            tp, sl = close * (1 + tp_pct), close * (1 - sl_pct)
        else:
            tp, sl = close * (1 - tp_pct), close * (1 + sl_pct)
        self.engine.receive_action(self.pid, "submit_order", {
            "type": "market", "instr": "X", "side": side, "size": size,
            "tp": round(tp, 4), "sl": round(sl, 4),
        })

        # Occasionally spend IP on sabotage for flavor.
        if self.rng.random() < 0.15:
            ability = self.rng.choice(["widen_spread", "fake_news", "delete_sl"])
            self.engine.receive_action(self.pid, "ip_spend", {"ability": ability})
