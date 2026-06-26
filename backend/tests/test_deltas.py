"""Unit tests for shipped delta payload builders."""
import sys
from decimal import Decimal
from pathlib import Path

root = str(Path(__file__).resolve().parents[1])
if root not in sys.path:
    sys.path.insert(0, root)

from app.arena import get_available_arenas
from app.sim.deltas import build_delta_payload, build_resources_snapshot
from app.sim.engine import SimulationEngine


def test_build_resources_snapshot_per_player():
    eng = SimulationEngine("d", get_available_arenas(1)[0]["id"])
    eng.state.add_player("p1")
    eng.state.add_player("p2")
    eng.state.players["p1"].equity = Decimal("105.5")
    eng.state.players["p2"].equity = Decimal("98.25")
    eng.state.players["p1"].ip = Decimal("40")
    eng.state.players["p2"].ip = Decimal("55")

    resources = build_resources_snapshot(eng.state)
    assert set(resources.keys()) == {"p1", "p2"}
    assert resources["p1"]["equity"] == 105.5
    assert resources["p2"]["equity"] == 98.25
    assert resources["p1"]["ip"] == 40.0
    assert resources["p2"]["ip"] == 55.0


def test_build_delta_payload_resources_match_players():
    eng = SimulationEngine("d", get_available_arenas(1)[0]["id"])
    eng.state.add_player("p1")
    eng.state.add_player("p2")
    eng.state.players["p1"].equity = Decimal("112")
    eng.state.players["p2"].equity = Decimal("100")

    payload = build_delta_payload(eng.state)
    assert payload["type"] == "delta"
    assert len(payload["resources"]) == 2
    assert payload["resources"]["p1"]["equity"] == 112.0
    assert payload["resources"]["p2"]["equity"] == 100.0
    assert "current_bar" in payload
    assert payload["content_hash"] == eng.state.content_hash