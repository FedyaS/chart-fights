"""Pure delta payload builders for WS broadcast (no dictcomp pid shadowing)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .engine import MatchState


def build_resources_snapshot(state: "MatchState") -> Dict[str, Dict[str, Any]]:
    """Per-player ip/equity/tb for delta.resources — explicit loop, correct keys."""
    tb_tbs = state.clock.tb_resolver.snapshot().get("tbs", {})
    resources: Dict[str, Dict[str, Any]] = {}
    for player_id, ps in state.players.items():
        resources[player_id] = {
            "ip": float(ps.ip),
            "equity": float(ps.equity),
            "tb": tb_tbs.get(player_id),
        }
    return resources


def build_delta_payload(
    state: "MatchState",
    *,
    fills: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Full delta message for WS broadcast."""
    return {
        "type": "delta",
        "t": float(state.clock.T),
        "r": float(state.clock.get_r()),
        "current_bar": state.get_current_bar(),
        "resources": build_resources_snapshot(state),
        "tb": state.clock.tb_resolver.snapshot(),
        "fills": fills or [],
        "events": state.events[-5:],
        "content_hash": state.content_hash,
    }