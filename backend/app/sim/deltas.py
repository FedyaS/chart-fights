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
    """Full delta message for WS broadcast.

    Drains only the events appended since the last broadcast (via a cursor) so
    each fill / news / sabotage event is delivered exactly once instead of the
    last-5 being resent every ~15Hz tick. Fill events are routed to `fills` (chart
    markers); everything else goes to `events` (log/news/indicators).
    """
    cursor = getattr(state, "_event_cursor", 0)
    new_events = state.events[cursor:]
    state._event_cursor = len(state.events)
    fill_events = [e for e in new_events if e.get("type") == "fill"]
    other_events = [e for e in new_events if e.get("type") != "fill"]
    return {
        "type": "delta",
        "t": float(state.clock.T),
        "r": float(state.clock.get_r()),
        "time_left": max(0.0, 300.0 - float(state.match_time)),
        "current_bar": state.get_current_bar(),
        "resources": build_resources_snapshot(state),
        "tb": state.clock.tb_resolver.snapshot(),
        "indicators": state.current_indicators(),
        "fills": fills if fills is not None else fill_events,
        "events": other_events,
        "content_hash": state.content_hash,
    }