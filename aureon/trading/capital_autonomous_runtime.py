"""Composition root for the governed Capital evidence and lifecycle route."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aureon.governance.cognition_gate import (
    TrustedCouncilReceiptSupplier,
    TrustedCrownReceiptSupplier,
)
from aureon.governance.durable_contingency import (
    DurableContingencyRecovery,
    bind_durable_contingency_recovery,
)
from aureon.governance.economic_boundary import (
    EconomicGovernanceBoundary,
    bind_economic_governance_boundary,
)
from aureon.trading.bounded_capital_live_trade import (
    BoundedCapitalLiveTrade,
    CapitalLiveClient,
    CapitalTradePlan,
)
from aureon.trading.capital_autonomous_cycle import CapitalAutonomousCycle
from aureon.trading.capital_market_evidence_collector import (
    CapitalEvidenceReadClient,
    collect_capital_market_evidence,
)

CAPITAL_RECOVERY_ADAPTER_ID = "aureon:capital:durable-close"


@dataclass(frozen=True, slots=True)
class CapitalAutonomousRuntime:
    """One explicitly bound Capital client, evidence plane, and mutation plane."""

    client: CapitalLiveClient
    boundary: EconomicGovernanceBoundary
    recovery: DurableContingencyRecovery
    route: BoundedCapitalLiveTrade
    cycle: CapitalAutonomousCycle

    def collect_evidence(
        self,
        *,
        public_contexts: Sequence[Mapping[str, Any]],
        now: float,
        symbol: str = "GOLD",
        max_history_points: int = 100,
    ) -> dict[str, Any]:
        return collect_capital_market_evidence(
            client=self.client,
            public_contexts=public_contexts,
            now=now,
            symbol=symbol,
            max_history_points=max_history_points,
        )

    def execute(self, plan: CapitalTradePlan) -> dict[str, Any]:
        return self.cycle.execute(plan)


def bind_capital_autonomous_runtime(
    *,
    client: CapitalLiveClient | CapitalEvidenceReadClient,
    council_receipt_supplier: TrustedCouncilReceiptSupplier,
    crown_receipt_supplier: TrustedCrownReceiptSupplier,
    trusted_council_supplier_ids: frozenset[str],
    trusted_crown_supplier_ids: frozenset[str],
    recovery_store_path: Path | str,
    cycle_state_path: Path | str,
    clock: Callable[[], float] = time.time,
    sleeper: Callable[[float], None] = time.sleep,
) -> CapitalAutonomousRuntime:
    """Bind all trusted dependencies once; request data selects none of them."""

    if not callable(clock) or not callable(sleeper):
        raise TypeError("capital_runtime_clock_and_sleeper_required")
    boundary = bind_economic_governance_boundary(
        council_receipt_supplier=council_receipt_supplier,
        crown_receipt_supplier=crown_receipt_supplier,
        trusted_council_supplier_ids=trusted_council_supplier_ids,
        trusted_crown_supplier_ids=trusted_crown_supplier_ids,
        clock=clock,
        permit_ttl_s=2.0,
        warrant_ttl_s=86_400.0,
        provider_max_age_s=300.0,
        governance_max_age_s=300.0,
    )
    recovery = bind_durable_contingency_recovery(
        adapter_id=CAPITAL_RECOVERY_ADAPTER_ID,
        trusted_adapter_ids=frozenset({CAPITAL_RECOVERY_ADAPTER_ID}),
        boundary=boundary,
        store_path=recovery_store_path,
        clock=clock,
        claim_ttl_s=5.0,
    )
    route = BoundedCapitalLiveTrade(
        client=client,
        boundary=boundary,
        recovery=recovery,
        clock=clock,
    )
    cycle = CapitalAutonomousCycle(
        route=route,
        client=client,
        state_path=Path(cycle_state_path),
        clock=clock,
        sleeper=sleeper,
    )
    return CapitalAutonomousRuntime(
        client=client,
        boundary=boundary,
        recovery=recovery,
        route=route,
        cycle=cycle,
    )


__all__ = [
    "CAPITAL_RECOVERY_ADAPTER_ID",
    "CapitalAutonomousRuntime",
    "bind_capital_autonomous_runtime",
]
