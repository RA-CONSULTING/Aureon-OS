from __future__ import annotations

from copy import deepcopy
from decimal import Decimal

import pytest

from aureon.governance.capital_owner_authorization import (
    issue_capital_owner_live_authorization_from_approval,
    validate_capital_owner_live_authorization_receipt,
)

NOW = 2_000_000_000.0
ACCOUNT_HASH = "a" * 64


def _approval():
    return {
        "event": "decided",
        "id": "capital-approval-1",
        "kind": "trade",
        "summary": "one minimum-size live Capital GOLD proof",
        "params": {
            "venue": "capital",
            "account_environment": "live_cfd",
            "account_id_hash": ACCOUNT_HASH,
            "symbol": "GOLD",
            "epic": "GOLD",
            "side_scope": ["BUY", "SELL"],
            "quantity": "0.01",
            "stop_distance": "5",
            "profit_distance": "5",
            "max_margin_gbp": "5",
            "one_cycle": True,
            "max_open_positions": 1,
            "containment_exit_authorized": True,
            "margin_product_authorized": True,
            "protective_stop_required": True,
            "guaranteed_stop": False,
            "transfers_allowed": False,
            "economic_mutation": False,
            "provider_submission_authorized": False,
            "intent_id": "intent:capital:minimum-gold-proof",
        },
        "prepared_by": "aureon-druid-council-live-proof",
        "risk": "high",
        "requires_human": True,
        "status": "approved",
        "note": "approved",
        "approver": "gary-operator-admin",
        "created_at": NOW - 20.0,
        "decided_at": NOW - 10.0,
        "approval_auth": {
            "authenticated": True,
            "identity_kind": "admin",
            "authn_method": "operator_static_bearer",
        },
    }


def test_authenticated_capital_approval_issues_exact_short_lived_receipt():
    receipt = issue_capital_owner_live_authorization_from_approval(
        _approval(),
        now=NOW,
    )

    assert receipt["provider_submission_authorized"] is True
    assert receipt["quantity"] == "0.01"
    assert receipt["max_margin_gbp"] == "5"
    assert receipt["entry_cutoff_at"] == NOW + 900.0
    assert validate_capital_owner_live_authorization_receipt(
        receipt,
        now=NOW + 1.0,
        expected_account_id_hash=ACCOUNT_HASH,
        expected_side="BUY",
        expected_stop_distance=Decimal("5"),
        expected_profit_distance=Decimal("5"),
    ) == receipt


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("status",), "pending"),
        (("approver",), "forged"),
        (("approval_auth", "authenticated"), False),
        (("params", "provider_submission_authorized"), True),
        (("params", "quantity"), "0.02"),
        (("params", "max_margin_gbp"), "5.01"),
        (("params", "max_open_positions"), 2),
        (("params", "containment_exit_authorized"), False),
        (("params", "margin_product_authorized"), False),
    ],
)
def test_untrusted_or_expanded_capital_approval_cannot_issue(path, value):
    item = deepcopy(_approval())
    target = item
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    with pytest.raises(ValueError):
        issue_capital_owner_live_authorization_from_approval(item, now=NOW)


def test_capital_receipt_tamper_scope_mismatch_and_expiry_reject():
    receipt = issue_capital_owner_live_authorization_from_approval(
        _approval(),
        now=NOW,
    )
    tampered = dict(receipt)
    tampered["quantity"] = "0.02"

    with pytest.raises(ValueError):
        validate_capital_owner_live_authorization_receipt(tampered, now=NOW + 1.0)
    with pytest.raises(ValueError, match="account_scope"):
        validate_capital_owner_live_authorization_receipt(
            receipt,
            now=NOW + 1.0,
            expected_account_id_hash="b" * 64,
        )
    with pytest.raises(ValueError, match="expired"):
        validate_capital_owner_live_authorization_receipt(
            receipt,
            now=NOW + 3600.0,
        )
