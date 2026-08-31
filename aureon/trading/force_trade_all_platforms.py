#!/usr/bin/env python3
"""Contained force-trade preflight and authorization boundary.

Importing this module is inert: it does not load dotenv, alter live/dry-run
environment flags, import exchange clients, inspect balances, write receipts,
or submit orders.  The command-line entry point is status-only and remains on
HOLD while the checked-in Magic-Star implementation is not production-ready.

Any future production adapter must call :func:`dispatch_authorized_force_trade`
with one opaque authorization per exact order plan.  The authorization is
atomically consumed immediately before the injected final dispatcher is called.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Mapping
from typing import Any, Sequence

from aureon.queen.queen_force_trade_governance import (
    ForceTradePlan,
    OpaqueForceTradeAuthorization,
    claim_queen_force_trade_authority,
    evaluate_queen_force_trade_authority,
)

CANONICAL_FORCE_TRADE_PLANS: tuple[ForceTradePlan, ...] = (
    ForceTradePlan(
        provider="kraken",
        symbol="XXBTZUSD",
        side="BUY",
        quantity="0.0001",
        quantity_kind="base_units",
    ),
    ForceTradePlan(
        provider="binance",
        symbol="BTCUSDT",
        side="BUY",
        quantity="0.0001",
        quantity_kind="base_units",
    ),
    ForceTradePlan(
        provider="alpaca",
        symbol="BTC/USD",
        side="BUY",
        quantity="5",
        quantity_kind="notional_usd",
        time_in_force="gtc",
    ),
    ForceTradePlan(
        provider="capital",
        symbol="EURUSD",
        side="BUY",
        quantity="0.1",
        quantity_kind="lots",
    ),
)


def _authorization_for_plan(
    authorizations: Mapping[str, OpaqueForceTradeAuthorization] | None,
    plan: ForceTradePlan,
) -> OpaqueForceTradeAuthorization | None:
    if not isinstance(authorizations, Mapping):
        return None
    candidate = authorizations.get(plan.commitment)
    return candidate if isinstance(candidate, OpaqueForceTradeAuthorization) else None


def preflight_force_trade_all_platforms(
    authorizations: Mapping[str, OpaqueForceTradeAuthorization] | None = None,
) -> dict[str, Any]:
    """Return a non-consuming, non-network status for every canonical plan."""

    plans: list[dict[str, Any]] = []
    for plan in CANONICAL_FORCE_TRADE_PLANS:
        decision = evaluate_queen_force_trade_authority(
            plan=plan,
            authorization=_authorization_for_plan(authorizations, plan),
        )
        plans.append(
            {
                "status": "READY" if decision.allowed else "HOLD",
                "plan": plan.public_dict(),
                "plan_sha256": plan.commitment,
                "capability_id": decision.capability_id,
                "reason": decision.reason,
                "missing_requirements": list(decision.missing_requirements),
            }
        )
    ready = sum(item["status"] == "READY" for item in plans)
    return {
        "status": "READY" if ready == len(plans) else "HOLD",
        "mode": "status_only_no_provider_construction",
        "plan_count": len(plans),
        "ready_count": ready,
        "hold_count": len(plans) - ready,
        "plans": plans,
    }


def dispatch_authorized_force_trade(
    *,
    plan: ForceTradePlan,
    authorization: OpaqueForceTradeAuthorization | None,
    final_dispatcher: Callable[[ForceTradePlan], Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """Claim one authorization and invoke one injected exact-plan dispatcher.

    This module intentionally contains no exchange-client factory.  Missing or
    invalid authorization, or a missing production dispatcher, returns HOLD
    before any provider object can be constructed.  Once claimed, authorization
    is never rolled back: the handler may have caused provider-side effects even
    when it raises or returns an invalid receipt.
    """

    if not isinstance(plan, ForceTradePlan):
        return {
            "status": "HOLD",
            "reason": "exact_force_trade_plan_required",
            "plan_sha256": None,
        }
    if not callable(final_dispatcher):
        return {
            "status": "HOLD",
            "reason": "production_force_trade_dispatcher_unavailable",
            "plan_sha256": plan.commitment,
        }

    decision = claim_queen_force_trade_authority(
        plan=plan,
        authorization=authorization,
    )
    if not decision.allowed:
        return {
            "status": "HOLD",
            "reason": decision.reason,
            "missing_requirements": list(decision.missing_requirements),
            "plan_sha256": plan.commitment,
        }

    try:
        provider_result = final_dispatcher(plan)
    except Exception:
        return {
            "status": "INDETERMINATE",
            "reason": "authorized_provider_dispatch_failed_after_claim",
            "plan_sha256": plan.commitment,
            "authorization_consumed": True,
        }
    if not isinstance(provider_result, Mapping):
        return {
            "status": "INDETERMINATE",
            "reason": "authorized_provider_dispatch_returned_invalid_receipt",
            "plan_sha256": plan.commitment,
            "authorization_consumed": True,
        }
    # The component that performs an effect cannot independently certify that
    # effect.  Callback-controlled status text, commitments, and receipt IDs are
    # only dispatch acknowledgements; a provider query/read-back must reconcile
    # the exact order before any EXECUTED/filled/accounting claim is possible.
    return {
        "status": "PENDING_RECONCILIATION",
        "reason": "independent_provider_readback_required",
        "plan_sha256": plan.commitment,
        "authorization_consumed": True,
        "submitted": None,
        "dispatcher_acknowledgement_untrusted": True,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
    }


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Show contained force-trade authorization status (no live action)."
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print the non-mutating authorization preflight (default).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    build_argument_parser().parse_args(argv)
    report = preflight_force_trade_all_platforms()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CANONICAL_FORCE_TRADE_PLANS",
    "build_argument_parser",
    "dispatch_authorized_force_trade",
    "main",
    "preflight_force_trade_all_platforms",
]
