"""Authenticated owner approval -> one exact bounded Capital CFD authority.

The approval queue records the human decision but executes nothing. This
module converts only a fresh bearer-authenticated decision for the minimum
GOLD route into a short-lived evidence receipt. It never calls Capital.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

SCHEMA = "aureon.owner_capital_live_authorization.v1"
RECEIPT_PREFIX = "owner:capital-live-authorization:"
DEFAULT_TTL_S = 3600.0
DEFAULT_ENTRY_WINDOW_S = 900.0
DEFAULT_APPROVAL_MAX_AGE_S = 900.0

_FALSE_FLAGS = (
    "action_eligible",
    "accounting_eligible",
    "learning_eligible",
    "eligible_for_action",
    "eligible_for_accounting",
    "eligible_for_learning",
    "economic_mutation",
)


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_required")
    return value.strip()


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}_must_be_finite")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{name}_must_be_positive_finite")
    return result


def _decimal(value: Any, name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{name}_must_be_decimal") from exc
    if not result.is_finite() or result <= 0:
        raise ValueError(f"{name}_must_be_positive_decimal")
    return result


def _digest(value: Any, name: str) -> str:
    result = _text(value, name)
    if len(result) != 64 or any(char not in "0123456789abcdef" for char in result):
        raise ValueError(f"{name}_must_be_sha256")
    return result


def _causal(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {key: receipt[key] for key in sorted(receipt) if key != "receipt_id"}


def validate_capital_owner_live_authorization_receipt(
    receipt: Mapping[str, Any],
    *,
    now: float | None = None,
    expected_account_id_hash: str | None = None,
    expected_side: str | None = None,
    expected_stop_distance: Decimal | None = None,
    expected_profit_distance: Decimal | None = None,
) -> dict[str, Any]:
    current = _finite(time.time() if now is None else now, "now")
    if not isinstance(receipt, Mapping) or receipt.get("schema") != SCHEMA:
        raise ValueError("capital_owner_authorization_receipt_required")
    payload = dict(receipt)
    if (
        payload.get("receipt_type") != "owner_live_order_authorization"
        or payload.get("data_status") != "live"
        or payload.get("truth_status") != "real_operator"
        or payload.get("generated_values") is not False
        or payload.get("owner") != "Gary Leckey"
        or payload.get("venue") != "capital"
        or payload.get("account_environment") != "live_cfd"
        or payload.get("symbol") != "GOLD"
        or payload.get("epic") != "GOLD"
        or payload.get("side_scope") != ["BUY", "SELL"]
        or payload.get("quantity") != "0.01"
        or payload.get("authorized") is not True
        or payload.get("provider_submission_authorized") is not True
        or payload.get("one_cycle") is not True
        or payload.get("max_open_positions") != 1
        or payload.get("containment_exit_authorized") is not True
        or payload.get("margin_product_authorized") is not True
        or payload.get("protective_stop_required") is not True
        or payload.get("guaranteed_stop") is not False
        or payload.get("transfers_allowed") is not False
        or any(payload.get(flag) is not False for flag in _FALSE_FLAGS)
    ):
        raise ValueError("capital_owner_authorization_scope_mismatch")
    if payload.get("approval_auth") != {
        "authenticated": True,
        "identity_kind": "admin",
        "authn_method": "operator_static_bearer",
    }:
        raise ValueError("authenticated_owner_approval_required")
    for name in (
        "authorization_id",
        "intent_id",
        "approval_item_id",
        "approval_event_digest",
        "source_id",
    ):
        _text(payload.get(name), name)
    account_hash = _digest(payload.get("account_id_hash"), "account_id_hash")
    if expected_account_id_hash is not None and account_hash != expected_account_id_hash:
        raise ValueError("capital_owner_account_scope_mismatch")
    if expected_side is not None and expected_side not in payload["side_scope"]:
        raise ValueError("capital_owner_side_scope_mismatch")
    stop = _decimal(payload.get("stop_distance"), "stop_distance")
    profit = _decimal(payload.get("profit_distance"), "profit_distance")
    max_margin = _decimal(payload.get("max_margin_gbp"), "max_margin_gbp")
    if max_margin > Decimal("5"):
        raise ValueError("capital_owner_margin_cap_exceeded")
    if expected_stop_distance is not None and stop != expected_stop_distance:
        raise ValueError("capital_owner_stop_distance_mismatch")
    if expected_profit_distance is not None and profit != expected_profit_distance:
        raise ValueError("capital_owner_profit_distance_mismatch")
    source_timestamp = _finite(payload.get("source_timestamp"), "source_timestamp")
    received_at = _finite(payload.get("received_at"), "received_at")
    issued_at = _finite(payload.get("issued_at"), "issued_at")
    expires_at = _finite(payload.get("expires_at"), "expires_at")
    entry_cutoff = _finite(payload.get("entry_cutoff_at"), "entry_cutoff_at")
    if (
        source_timestamp > received_at
        or received_at > issued_at
        or issued_at > current + 5.0
        or current >= expires_at
        or current >= entry_cutoff
        or entry_cutoff > expires_at
    ):
        raise ValueError("capital_owner_authorization_expired_or_misaligned")
    expected_id = f"{RECEIPT_PREFIX}{_sha(_causal(payload))}"
    if payload.get("receipt_id") != expected_id:
        raise ValueError("capital_owner_authorization_hash_mismatch")
    return payload


def issue_capital_owner_live_authorization_from_approval(
    approval_item: Mapping[str, Any],
    *,
    now: float | None = None,
    ttl_s: float = DEFAULT_TTL_S,
    entry_window_s: float = DEFAULT_ENTRY_WINDOW_S,
    approval_max_age_s: float = DEFAULT_APPROVAL_MAX_AGE_S,
) -> dict[str, Any]:
    current = _finite(time.time() if now is None else now, "now")
    ttl = _finite(ttl_s, "ttl_s")
    entry_window = _finite(entry_window_s, "entry_window_s")
    approval_age = _finite(approval_max_age_s, "approval_max_age_s")
    if entry_window > ttl:
        raise ValueError("entry_window_must_not_exceed_authorization_ttl")
    if not isinstance(approval_item, Mapping):
        raise ValueError("approved_capital_trade_item_required")
    item = dict(approval_item)
    params = item.get("params")
    if not isinstance(params, Mapping):
        raise ValueError("approved_capital_trade_params_required")
    approval_auth = item.get("approval_auth")
    decided_at = _finite(item.get("decided_at"), "decided_at")
    created_at = _finite(item.get("created_at"), "created_at")
    if (
        item.get("event") != "decided"
        or item.get("kind") != "trade"
        or item.get("status") != "approved"
        or item.get("requires_human") is not True
        or item.get("approver") != "gary-operator-admin"
        or approval_auth != {
            "authenticated": True,
            "identity_kind": "admin",
            "authn_method": "operator_static_bearer",
        }
        or created_at > decided_at
        or decided_at > current + 5.0
        or current - decided_at > approval_age
    ):
        raise ValueError("fresh_authenticated_capital_approval_required")
    account_hash = _digest(params.get("account_id_hash"), "account_id_hash")
    stop = _decimal(params.get("stop_distance"), "stop_distance")
    profit = _decimal(params.get("profit_distance"), "profit_distance")
    max_margin = _decimal(params.get("max_margin_gbp"), "max_margin_gbp")
    if (
        params.get("venue") != "capital"
        or params.get("account_environment") != "live_cfd"
        or params.get("symbol") != "GOLD"
        or params.get("epic") != "GOLD"
        or params.get("side_scope") != ["BUY", "SELL"]
        or params.get("quantity") != "0.01"
        or max_margin > Decimal("5")
        or params.get("one_cycle") is not True
        or params.get("max_open_positions") != 1
        or params.get("containment_exit_authorized") is not True
        or params.get("margin_product_authorized") is not True
        or params.get("protective_stop_required") is not True
        or params.get("guaranteed_stop") is not False
        or params.get("transfers_allowed") is not False
        or params.get("economic_mutation") is not False
        or params.get("provider_submission_authorized") is not False
    ):
        raise ValueError("approved_capital_trade_scope_mismatch")
    item_id = _text(item.get("id"), "approval_item_id")
    intent_id = _text(params.get("intent_id"), "intent_id")
    event_digest = _sha(item)
    authorization_id = (
        f"auth:capital-approval:{_sha({'item': item_id, 'event': event_digest})[:24]}"
    )
    causal = {
        "schema": SCHEMA,
        "receipt_type": "owner_live_order_authorization",
        "authorization_id": authorization_id,
        "intent_id": intent_id,
        "approval_item_id": item_id,
        "approval_event_digest": event_digest,
        "approval_auth": dict(approval_auth),
        "owner": "Gary Leckey",
        "venue": "capital",
        "account_environment": "live_cfd",
        "account_id_hash": account_hash,
        "symbol": "GOLD",
        "epic": "GOLD",
        "side_scope": ["BUY", "SELL"],
        "quantity": "0.01",
        "stop_distance": format(stop, "f"),
        "profit_distance": format(profit, "f"),
        "max_margin_gbp": format(max_margin, "f"),
        "issued_at": current,
        "expires_at": current + ttl,
        "entry_cutoff_at": current + entry_window,
        "authorized": True,
        "provider_submission_authorized": True,
        "one_cycle": True,
        "max_open_positions": 1,
        "containment_exit_authorized": True,
        "margin_product_authorized": True,
        "protective_stop_required": True,
        "guaranteed_stop": False,
        "transfers_allowed": False,
        "source_id": f"approval_queue:{item_id}",
        "source_timestamp": decided_at,
        "received_at": current,
        "input_receipt_ids": [f"approval:event:{event_digest}"],
        "data_status": "live",
        "truth_status": "real_operator",
        "generated_values": False,
        **dict.fromkeys(_FALSE_FLAGS, False),
    }
    receipt = {**causal, "receipt_id": f"{RECEIPT_PREFIX}{_sha(causal)}"}
    return validate_capital_owner_live_authorization_receipt(
        receipt,
        now=current,
        expected_account_id_hash=account_hash,
        expected_stop_distance=stop,
        expected_profit_distance=profit,
    )


__all__ = [
    "SCHEMA",
    "issue_capital_owner_live_authorization_from_approval",
    "validate_capital_owner_live_authorization_receipt",
]
