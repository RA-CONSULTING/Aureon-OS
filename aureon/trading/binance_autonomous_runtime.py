"""Composition root for the governed bounded Binance Spot round trip.

Construction is inert: it does not read credentials, contact Binance, issue a
Council/Crown decision, or mutate route state.  The owner-controlled bootstrap
injects the live client and the two independent governance suppliers.  Each
call to :meth:`advance` moves at most one hash-chained durable stage.
"""

from __future__ import annotations

import time
from collections.abc import Callable
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
from aureon.trading.bounded_binance_roundtrip import BoundedBinanceRoundTrip

BINANCE_RECOVERY_ADAPTER_ID = "aureon:binance:durable-containment"


@dataclass(frozen=True, slots=True)
class BinanceAutonomousRuntime:
    """One inseparable Binance client, governance boundary, and route."""

    client: Any
    boundary: EconomicGovernanceBoundary
    recovery: DurableContingencyRecovery
    route: BoundedBinanceRoundTrip

    def read_only_preflight(
        self,
        *,
        authorization_receipt: Any,
        confirmation_token: str,
        max_quote: Any,
    ) -> dict[str, Any]:
        return self.route.read_only_preflight(
            authorization_receipt=authorization_receipt,
            confirmation_token=confirmation_token,
            max_quote=max_quote,
        )

    def advance(
        self,
        *,
        authorization_receipt: Any,
        confirmation_token: str,
    ) -> dict[str, Any]:
        """Advance exactly one durable stage; never spin or blind-resubmit."""

        return self.route.advance(
            authorization_receipt=authorization_receipt,
            confirmation_token=confirmation_token,
        )


def bind_binance_autonomous_runtime(
    *,
    client: Any,
    hnc_receipt_supplier: Callable[[], Any],
    auris_receipt_supplier: Callable[[], Any],
    council_receipt_supplier: TrustedCouncilReceiptSupplier,
    crown_receipt_supplier: TrustedCrownReceiptSupplier,
    trusted_council_supplier_ids: frozenset[str],
    trusted_crown_supplier_ids: frozenset[str],
    recovery_store_path: Path | str,
    cycle_state_path: Path | str,
    clock: Callable[[], float] = time.time,
) -> BinanceAutonomousRuntime:
    """Bind trusted dependencies once without resolving evidence or acting."""

    if not callable(hnc_receipt_supplier) or not callable(auris_receipt_supplier):
        raise TypeError("binance_hnc_and_auris_receipt_suppliers_required")
    if not callable(clock):
        raise TypeError("binance_runtime_clock_required")
    state_path = Path(cycle_state_path)
    if state_path.parent.name != "bounded_binance_roundtrip":
        raise ValueError("private_hashed_cycle_state_path_required")
    if len(state_path.stem) != 64 or any(
        character not in "0123456789abcdef" for character in state_path.stem
    ):
        raise ValueError("private_hashed_cycle_state_path_required")

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
        adapter_id=BINANCE_RECOVERY_ADAPTER_ID,
        trusted_adapter_ids=frozenset({BINANCE_RECOVERY_ADAPTER_ID}),
        boundary=boundary,
        store_path=recovery_store_path,
        clock=clock,
        claim_ttl_s=5.0,
    )
    route = BoundedBinanceRoundTrip(
        client,
        state_path=state_path,
        hnc_receipt_supplier=hnc_receipt_supplier,
        auris_receipt_supplier=auris_receipt_supplier,
        economic_boundary=boundary,
        contingency_recovery=recovery,
        clock=clock,
    )
    return BinanceAutonomousRuntime(
        client=client,
        boundary=boundary,
        recovery=recovery,
        route=route,
    )


__all__ = [
    "BINANCE_RECOVERY_ADAPTER_ID",
    "BinanceAutonomousRuntime",
    "bind_binance_autonomous_runtime",
]
