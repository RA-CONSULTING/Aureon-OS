"""Authenticated Approval Queue decision -> short-lived live-route authority.

The queue records a human decision but deliberately executes nothing.  This
module is the narrow bridge that can turn one *authenticated* approved event
into an evidence-only, route-scoped receipt.  It never contacts a provider and
never grants authority to a model, Council, or raw request body.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

SCHEMA = "aureon.owner_live_authorization.v1"
RECEIPT_PREFIX = "owner:live-authorization:"
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


def _causal(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {key: receipt[key] for key in sorted(receipt) if key != "receipt_id"}


def validate_owner_live_authorization_receipt(
    receipt: Mapping[str, Any],
    *,
    now: float | None = None,
    expected_max_quote: Decimal | None = None,
) -> dict[str, Any]:
    current = _finite(time.time() if now is None else now, "now")
    if not isinstance(receipt, Mapping) or receipt.get("schema") != SCHEMA:
        raise ValueError("owner_live_authorization_receipt_required")
    payload = dict(receipt)
    if (
        payload.get("receipt_type") != "owner_live_order_authorization"
        or payload.get("data_status") != "live"
        or payload.get("truth_status") != "real_operator"
        or payload.get("generated_values") is not False
        or payload.get("owner") != "Gary Leckey"
        or payload.get("venue") != "binance"
        or payload.get("account_environment") != "live_spot"
        or payload.get("symbol") != "BTCUSDT"
        or payload.get("side_scope") != ["BUY", "SELL"]
        or payload.get("authorized") is not True
        or payload.get("provider_submission_authorized") is not True
        or payload.get("one_cycle") is not True
        or payload.get("containment_exit_authorized") is not True
        or payload.get("leverage_allowed") is not False
        or payload.get("margin_allowed") is not False
        or payload.get("transfers_allowed") is not False
        or any(payload.get(flag) is not False for flag in _FALSE_FLAGS)
    ):
        raise ValueError("owner_live_authorization_scope_mismatch")
    approval_auth = payload.get("approval_auth")
    if approval_auth != {
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
    quote = _decimal(payload.get("max_quote_notional"), "max_quote_notional")
    if expected_max_quote is not None and quote != expected_max_quote:
        raise ValueError("owner_authorization_quote_mismatch")
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
        raise ValueError("owner_live_authorization_expired_or_misaligned")
    expected_id = f"{RECEIPT_PREFIX}{_sha(_causal(payload))}"
    if payload.get("receipt_id") != expected_id:
        raise ValueError("owner_live_authorization_hash_mismatch")
    return payload


def issue_owner_live_authorization_from_approval(
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
        raise ValueError("approved_trade_item_required")
    item = dict(approval_item)
    params = item.get("params")
    if not isinstance(params, Mapping):
        raise ValueError("approved_trade_params_required")
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
        raise ValueError("fresh_authenticated_approved_trade_required")
    quote = _decimal(params.get("max_quote_notional"), "max_quote_notional")
    if (
        params.get("venue") != "binance"
        or params.get("account_environment") != "live_spot"
        or params.get("symbol") != "BTCUSDT"
        or params.get("side_scope") != ["BUY", "SELL"]
        or params.get("one_cycle") is not True
        or params.get("containment_exit_authorized") is not True
        or params.get("leverage_allowed") is not False
        or params.get("margin_allowed") is not False
        or params.get("transfers_allowed") is not False
        or params.get("economic_mutation") is not False
        or params.get("provider_submission_authorized") is not False
    ):
        raise ValueError("approved_trade_scope_mismatch")
    item_id = _text(item.get("id"), "approval_item_id")
    intent_id = _text(params.get("intent_id"), "intent_id")
    event_digest = _sha(item)
    authorization_id = f"auth:approval:{_sha({'item': item_id, 'event': event_digest})[:24]}"
    causal = {
        "schema": SCHEMA,
        "receipt_type": "owner_live_order_authorization",
        "authorization_id": authorization_id,
        "intent_id": intent_id,
        "approval_item_id": item_id,
        "approval_event_digest": event_digest,
        "approval_auth": dict(approval_auth),
        "owner": "Gary Leckey",
        "venue": "binance",
        "account_environment": "live_spot",
        "symbol": "BTCUSDT",
        "side_scope": ["BUY", "SELL"],
        "max_quote_notional": format(quote, "f"),
        "issued_at": current,
        "expires_at": current + ttl,
        "entry_cutoff_at": current + entry_window,
        "authorized": True,
        "provider_submission_authorized": True,
        "one_cycle": True,
        "containment_exit_authorized": True,
        "leverage_allowed": False,
        "margin_allowed": False,
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
    return validate_owner_live_authorization_receipt(
        receipt,
        now=current,
        expected_max_quote=quote,
    )


__all__ = [
    "SCHEMA",
    "issue_owner_live_authorization_from_approval",
    "validate_owner_live_authorization_receipt",
]
