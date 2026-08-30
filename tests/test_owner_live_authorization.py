from __future__ import annotations

from decimal import Decimal

import pytest

from aureon.governance.owner_live_authorization import (
    issue_owner_live_authorization_from_approval,
    validate_owner_live_authorization_receipt,
)

NOW = 2_000_000_000.0


def _approval():
    return {
        "event": "decided",
        "id": "approval-1",
        "kind": "trade",
        "summary": "bounded proof",
        "params": {
            "venue": "binance",
            "account_environment": "live_spot",
            "symbol": "BTCUSDT",
            "side_scope": ["BUY", "SELL"],
            "max_quote_notional": "10",
            "one_cycle": True,
            "containment_exit_authorized": True,
            "leverage_allowed": False,
            "margin_allowed": False,
            "transfers_allowed": False,
            "economic_mutation": False,
            "provider_submission_authorized": False,
            "intent_id": "intent:bounded-binance:test",
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


def test_authenticated_approval_issues_short_lived_exact_receipt():
    receipt = issue_owner_live_authorization_from_approval(_approval(), now=NOW)
    assert receipt["provider_submission_authorized"] is True
    assert receipt["entry_cutoff_at"] == NOW + 900.0
    assert receipt["expires_at"] == NOW + 3600.0
    assert validate_owner_live_authorization_receipt(
        receipt, now=NOW + 1.0, expected_max_quote=Decimal("10")
    ) == receipt


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("status",), "pending"),
        (("approver",), "forged"),
        (("approval_auth", "authenticated"), False),
        (("params", "provider_submission_authorized"), True),
        (("params", "margin_allowed"), True),
    ],
)
def test_untrusted_or_expanded_approval_cannot_issue(path, value):
    item = _approval()
    target = item
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValueError):
        issue_owner_live_authorization_from_approval(item, now=NOW)


def test_receipt_tamper_and_expiry_reject():
    receipt = issue_owner_live_authorization_from_approval(_approval(), now=NOW)
    tampered = dict(receipt)
    tampered["max_quote_notional"] = "11"
    with pytest.raises(ValueError):
        validate_owner_live_authorization_receipt(tampered, now=NOW + 1.0)
    with pytest.raises(ValueError):
        validate_owner_live_authorization_receipt(receipt, now=NOW + 3600.0)
