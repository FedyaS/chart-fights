"""Legacy shim: re-exports the enhanced engine from app/sim/engine.py (the canonical impl).
All focus items implemented in sim/engine.py + main rooms:
- real arena_loader + 1656 arenas
- SharedClock drives T (replay index) with R
- advance/receive: real current_bar + equity using bar prices
- full broadcast deltas w/ OHLC + TB/IP/events + content_hash
- 'submit_order' real fill at current close
- anti-cheat content_hash + deterministic verify
Per GDD + cursor-tasks + specs (TB/IP exact rates etc).
"""
from .sim.engine import SimulationEngine, SharedClock, TBResolver, MatchState, Action
from decimal import Decimal
try:
    from decimal import getcontext
    getcontext().prec = 28
except Exception:
    pass

# compat exports / consts (exact from specs)
TB_BASE_RECHARGE = Decimal("1.0")
TB_PAUSE_BONUS = Decimal("4.0")
TB_CONSUME = {"pause": Decimal("0"), "ff2": Decimal("2.0"), "ff3": Decimal("5.0"), "ff5": Decimal("12.0")}
DEFAULT_R = Decimal("1.0")
MATCH_DURATION_REAL = 300.0
IP_START = Decimal("50")
IP_REGEN = Decimal("0.5")
IP_PNL_GRANT_PCT = Decimal("0.10")
BASE_SPREAD_PCT = Decimal("0.0005")

__all__ = ["SimulationEngine", "Action", "SharedClock", "TBResolver", "MatchState"]
