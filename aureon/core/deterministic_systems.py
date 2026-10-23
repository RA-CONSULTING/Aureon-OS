"""Deterministic systems — replayable rules already living in the organism.

The name is the module Gary asked for. Each entry points at an existing
rule: the baton stage order, the council's active threshold, and the
φ² seat ring. Nothing here places an order.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeterministicSystem:
    name: str
    module: str
    rule: str


SYSTEMS: tuple[DeterministicSystem, ...] = (
    DeterministicSystem(
        "baton_stage_order",
        "aureon.core.baton_relay_monitor",
        "intent → plan → execute → confirm",
    ),
    DeterministicSystem(
        "council_active_threshold",
        "aureon.swarm.druidic_council",
        "ACTIVE_THRESHOLD = 0.80",
    ),
    DeterministicSystem(
        "phi_squared_ring",
        "aureon.swarm.druidic_council",
        "four_seat_golden_ring.v1",
    ),
    DeterministicSystem(
        "live_trading_default_off",
        "aureon.autonomous.aureon_master_launcher",
        "unset AUREON_LIVE_TRADING is 0",
    ),
)


def list_systems() -> list[dict[str, str]]:
    return [
        {"name": item.name, "module": item.module, "rule": item.rule}
        for item in SYSTEMS
    ]
