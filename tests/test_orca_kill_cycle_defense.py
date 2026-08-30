"""Offline contracts for the Queen's current orca-defense policy."""

from __future__ import annotations

from aureon.queen.queen_eternal_machine import QueenEternalMachine


def _danger(level: str) -> dict[str, float | str]:
    return {
        "danger_level": level,
        "current_price": 90.0,
        "cost_basis_price": 100.0,
        "current_loss": 10.0,
    }


def test_orca_defense_maps_each_danger_band_to_non_selling_action() -> None:
    machine = object.__new__(QueenEternalMachine)
    machine.detect_orca_kill_cycle = lambda: {
        "BTC": _danger("CRITICAL"),
        "ETH": _danger("HIGH ALERT"),
        "SOL": _danger("WARNING"),
    }

    actions = QueenEternalMachine.apply_friend_protection_strategy(machine)

    assert actions == {
        "BTC": "CRITICAL_HOLD_STRONG",
        "ETH": "HIGH_ALERT_HOLD",
        "SOL": "WARNING_MONITOR",
    }
    assert all("SELL" not in action and "STOP" not in action for action in actions.values())


def test_orca_defense_is_empty_when_no_friend_is_in_danger() -> None:
    machine = object.__new__(QueenEternalMachine)
    machine.detect_orca_kill_cycle = lambda: {}

    assert QueenEternalMachine.apply_friend_protection_strategy(machine) == {}
