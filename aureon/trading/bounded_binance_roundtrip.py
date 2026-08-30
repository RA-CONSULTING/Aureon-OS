"""Receipt-gated, single-cycle Binance BTC/USDT validation.

Import and the default CLI are inert. A live caller must inject a configured
client and evidence suppliers, run read-only preflight, then advance one durable
stage at a time. Each advance performs at most one order mutation or readback.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
from decimal import ROUND_DOWN, Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

# The frontend package intentionally invokes this file by absolute path while
# its working directory is frontend/. Establish the checkout root before
# importing any aureon package so the inert CLI preflight remains runnable
# from every declared package-script location.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from aureon.governance.durable_contingency import (  # noqa: E402
    DurableContingencyRecordRef,
    DurableContingencyRecovery,
)
from aureon.governance.economic_boundary import (  # noqa: E402
    ContingencyWarrant,
    ContingencyWarrantScope,
    EconomicGovernanceBlocked,
    EconomicGovernanceBoundary,
    EconomicIntent,
    EconomicMutationPermit,
)
from aureon.governance.owner_live_authorization import (  # noqa: E402
    SCHEMA as OWNER_AUTH_SCHEMA,
)
from aureon.governance.owner_live_authorization import (
    validate_owner_live_authorization_receipt,
)

SYMBOL = "BTCUSDT"
BASE_ASSET = "BTC"
QUOTE_ASSET = "USDT"
VENUE = "binance"
MAX_QUOTE_CAP = Decimal("10")
MAX_RECEIPT_AGE_SECONDS = 300.0
FUTURE_SKEW_SECONDS = 5.0
ORDER_METHOD = 'POST'
ORDER_PATH = '/api/v3/order'
ECONOMIC_LINEAGE_SCHEMA = 'aureon.bounded_binance.economic_lineage.v1'
MIN_EXIT_NOTIONAL_BUFFER = Decimal("1.05")
STATE_SCHEMA = "aureon.bounded_binance_roundtrip.v1"
CONFIRMATION_PREFIX = "CONFIRM-BINANCE-BTCUSDT-ROUNDTRIP"
AUTH_ISSUED_AT = "2026-08-11T12:23:28.987Z"
AUTH_EXPIRES_AT = "2026-08-12T12:23:28.987Z"
ENTRY_CUTOFF_AT = "2026-08-12T08:23:28.987Z"
_FALSE_COGNITIVE_ALIASES = (
    "operational_eligible", "provider_eligible", "action_eligible",
    "actionable", "accounting_eligible", "learning_eligible",
    "eligible_for_action", "eligible_for_accounting", "eligible_for_learning",
)
_ACCOUNT_PERMISSION_TRUE_FLAGS = (
    "account_type_is_spot",
    "account_permissions_are_spot_only",
    "account_can_trade",
    "api_reading_enabled",
    "api_spot_trading_enabled",
    "api_trading_unlocked",
    "api_ip_restricted",
    "api_withdrawals_disabled",
    "api_internal_transfer_disabled",
    "api_universal_transfer_disabled",
    "api_margin_disabled",
    "api_futures_disabled",
    "api_options_disabled",
    "api_portfolio_margin_disabled",
    "client_is_mainnet",
    "client_is_live",
    "uk_guard_enabled",
)
_ORDER_SNAPSHOT_KEYS = {
    "symbol", "side", "orderId", "clientOrderId", "status",
    "updateTime", "transactTime", "workingTime", "time",
    "executedQty", "cummulativeQuoteQty", "cumulativeQuoteQty", "fills",
}
_ORDER_RECEIPT_KEYS = {
    "symbol", "side", "orderId", "provider_order_id", "clientOrderId",
    "provider_client_order_id", "status", "provider_status", "data_status",
    "truth_status", "reason", "submitted", "submission_acknowledged",
    "reconciliation_required", "source_id", "source_timestamp",
    "provider_timestamp", "received_at", "receipt_id", "executedQty",
    "filled_qty", "cummulativeQuoteQty", "filled_notional", "avgPrice",
    "avg_fill_price", "filled_avg_price", "fee", "fees", "fee_asset",
    "fee_currency", "fill_receipt_complete", "eligible_for_action",
    "eligible_for_accounting", "eligible_for_learning", "generated_values",
    "action", "accounting", "learning", "margin", "exchange",
    "provider_receipt_type", "readback_performed",
}
_FILL_KEYS = {
    "orderId", "tradeId", "qty", "price", "commission",
    "commissionAsset", "source_timestamp", "provider_timestamp",
    "truth_status", "generated_values",
}


class StateIntegrityError(RuntimeError):
    """A durable cycle file or journal cannot be trusted."""


def cycle_state_path(
    private_state_root: Path | str,
    *,
    intent_id: str,
    authorization_id: str,
) -> Path:
    intent = _identifier(intent_id)
    authorization = _identifier(authorization_id)
    if intent is None or authorization is None:
        raise ValueError("intent_and_authorization_ids_required")
    digest = hashlib.sha256(
        f"{authorization}|{intent}|{SYMBOL}|one_cycle".encode("utf-8")
    ).hexdigest()
    return (
        Path(private_state_root)
        / "bounded_binance_roundtrip"
        / f"{digest}.json"
    )


def _state_path_matches_scope(
    path: Path,
    authorization: Mapping[str, Any],
) -> bool:
    lowered_parts = {part.casefold() for part in path.parts}
    if "frontend" in lowered_parts or "public" in lowered_parts:
        return False
    if path.parent.name != "bounded_binance_roundtrip":
        return False
    expected = cycle_state_path(
        path.parent.parent,
        intent_id=str(authorization["intent_id"]),
        authorization_id=str(authorization["authorization_id"]),
    )
    return path.resolve() == expected.resolve()


def _events_path(state_path: Path) -> Path:
    return state_path.with_name(state_path.stem + ".events.jsonl")


def _lock_path(state_path: Path) -> Path:
    return state_path.with_name(state_path.stem + ".lock")


def _state_hash_payload(state: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value for key, value in state.items()
        if key not in {"state_hash", "latest_event_hash"}
    }


def _hash_mapping(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


def _verify_event_link(path: Path, expected_hash: str) -> None:
    events = _events_path(path)
    if not events.exists():
        raise StateIntegrityError("state_event_journal_missing")
    try:
        lines = [
            line for line in events.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        parsed = [json.loads(line) for line in lines]
    except (OSError, ValueError, TypeError, IndexError):
        raise StateIntegrityError("state_event_journal_unreadable")
    previous_hash: Optional[str] = None
    for sequence, event in enumerate(parsed, start=1):
        if not isinstance(event, dict):
            raise StateIntegrityError("state_event_journal_invalid")
        observed_hash = _identifier(event.get("event_hash"))
        material = {
            key: value for key, value in event.items() if key != "event_hash"
        }
        if (
            event.get("schema")
            != "aureon.bounded_binance_roundtrip.event.v1"
            or event.get("sequence") != sequence
            or event.get("previous_event_hash") != previous_hash
            or observed_hash is None
            or observed_hash != _hash_mapping(material)
        ):
            raise StateIntegrityError("state_event_journal_hash_mismatch")
        previous_hash = observed_hash
    if previous_hash != expected_hash:
        raise StateIntegrityError("state_event_journal_hash_mismatch")


def _read_verified_state(path: Path) -> Optional[dict[str, Any]]:
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        raise StateIntegrityError("state_unreadable")
    if not isinstance(raw, dict) or raw.get("schema") != STATE_SCHEMA:
        raise StateIntegrityError("state_schema_invalid")
    observed_hash = _identifier(raw.get("state_hash"))
    if (
        observed_hash is None
        or observed_hash != _hash_mapping(_state_hash_payload(raw))
    ):
        raise StateIntegrityError("state_hash_mismatch")
    latest_event_hash = _identifier(raw.get("latest_event_hash"))
    if latest_event_hash is None:
        raise StateIntegrityError("state_event_hash_missing")
    _verify_event_link(path, latest_event_hash)
    return raw


def _identifier(value: Any) -> Optional[str]:
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    if text.lower() in {"", "none", "null", "unknown", "n/a", "0", "-1"}:
        return None
    return text


def _finite_decimal(
    value: Any, *, positive: bool = False, nonnegative: bool = False,
) -> Optional[Decimal]:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not parsed.is_finite():
        return None
    if positive and parsed <= 0:
        return None
    if nonnegative and parsed < 0:
        return None
    return parsed


def _finite_timestamp(value: Any) -> Optional[float]:
    if isinstance(value, str) and "T" in value:
        try:
            value = datetime.fromisoformat(
                value.strip().replace("Z", "+00:00")
            ).timestamp()
        except (TypeError, ValueError):
            return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed) or parsed <= 0:
        return None
    return parsed / 1000.0 if parsed > 10_000_000_000 else parsed


def _json_digest(prefix: str, payload: Mapping[str, Any]) -> str:
    material = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False,
    )
    return f"{prefix}:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


def expected_confirmation_token(authorization_id: str) -> str:
    normalized = _identifier(authorization_id)
    if normalized is None:
        raise ValueError("authorization_id_required")
    return f"{CONFIRMATION_PREFIX}:{normalized}"


def _client_order_id(intent_id: str, leg: str) -> str:
    digest = hashlib.sha256(
        f"{intent_id}|{SYMBOL}|{leg}".encode("utf-8")
    ).hexdigest()[:24]
    return f"AUR{'B' if leg == 'entry' else 'S'}{digest}"


def _no_action(reason: str, **details: Any) -> dict[str, Any]:
    return {
        "status": "no_data", "data_status": "no_data",
        "truth_status": "no_data", "generated_values": False,
        "eligible_for_action": False, "eligible_for_accounting": False,
        "eligible_for_learning": False, "economic_mutation": False,
        "reason": reason, **details,
    }


def _live_receipt(
    raw: Any, *, now: float, truth_statuses: set[str],
    max_age_seconds: float = MAX_RECEIPT_AGE_SECONDS,
) -> Optional[dict[str, Any]]:
    if not isinstance(raw, Mapping):
        return None
    source_id = _identifier(raw.get("source_id"))
    receipt_id = _identifier(raw.get("receipt_id"))
    source_timestamp = _finite_timestamp(raw.get("source_timestamp"))
    received_at = _finite_timestamp(raw.get("received_at"))
    if (
        source_id is None or receipt_id is None or source_timestamp is None
        or received_at is None or raw.get("data_status") != "live"
        or str(raw.get("truth_status") or "") not in truth_statuses
        or raw.get("generated_values") is not False
        or source_timestamp > now + FUTURE_SKEW_SECONDS
        or received_at > now + FUTURE_SKEW_SECONDS
        or received_at < source_timestamp - FUTURE_SKEW_SECONDS
        or now - source_timestamp > max_age_seconds
    ):
        return None
    return {
        **dict(raw), "source_id": source_id, "receipt_id": receipt_id,
        "source_timestamp": source_timestamp, "received_at": received_at,
        "generated_values": False,
    }


def _receipt_provenance(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source_id": receipt["source_id"],
        "source_timestamp": receipt["source_timestamp"],
        "received_at": receipt["received_at"],
        "receipt_id": receipt["receipt_id"],
        "data_status": receipt["data_status"],
        "truth_status": receipt["truth_status"],
        "generated_values": False,
    }


def _safe_input_receipt_ids(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    output: list[str] = []
    for candidate in value:
        normalized = _identifier(candidate)
        if normalized is not None and normalized not in output:
            output.append(normalized)
    return output


def _safe_order_receipt(raw: Any) -> Optional[dict[str, Any]]:
    if not isinstance(raw, Mapping):
        return None
    safe = {
        key: raw[key] for key in _ORDER_RECEIPT_KEYS if key in raw
    }
    raw_fills = raw.get("fills")
    if isinstance(raw_fills, list):
        safe["fills"] = [
            {key: fill[key] for key in _FILL_KEYS if key in fill}
            for fill in raw_fills if isinstance(fill, Mapping)
        ]
    return safe


def _new_entry_window_open(
    now: float,
    authorization: Mapping[str, Any] | None = None,
) -> bool:
    cutoff = _finite_timestamp(
        authorization.get("entry_cutoff_at")
        if isinstance(authorization, Mapping) else ENTRY_CUTOFF_AT
    )
    return cutoff is not None and now < cutoff


def _authorization(
    raw: Any, *, now: float, max_quote: Decimal,
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    receipt = _live_receipt(
        raw,
        now=now,
        truth_statuses={"real_operator"},
        max_age_seconds=86_405.0,
    )
    if receipt is None:
        return None, "fresh_operator_authorization_receipt_required"
    if receipt.get("schema") == OWNER_AUTH_SCHEMA:
        try:
            verified = validate_owner_live_authorization_receipt(
                receipt,
                now=now,
                expected_max_quote=max_quote,
            )
        except (TypeError, ValueError):
            return None, "authenticated_owner_authorization_receipt_required"
        return {
            **verified,
            "source_timestamp": float(verified["source_timestamp"]),
            "received_at": float(verified["received_at"]),
            "issued_at_epoch": float(verified["issued_at"]),
            "expires_at_epoch": float(verified["expires_at"]),
        }, None
    authorization_id = _identifier(receipt.get("authorization_id"))
    intent_id = _identifier(receipt.get("intent_id"))
    owner = str(receipt.get("owner") or "").strip()
    authorized_quote = _finite_decimal(
        receipt.get("max_quote_notional"), positive=True,
    )
    side_scope = receipt.get("side_scope")
    normalized_sides = (
        {str(value).strip().upper() for value in side_scope}
        if isinstance(side_scope, list) else set()
    )
    expires_at = _finite_timestamp(receipt.get("expires_at"))
    issued_at = _finite_timestamp(receipt.get("issued_at"))
    expected_issued_at = _finite_timestamp(AUTH_ISSUED_AT)
    expected_expires_at = _finite_timestamp(AUTH_EXPIRES_AT)
    if (
        authorization_id is None or intent_id is None
        or owner.casefold() != "gary leckey".casefold()
        or str(receipt.get("venue") or "").strip().lower() != VENUE
        or str(receipt.get("account_environment") or "").strip().lower()
        != "live_spot"
        or str(receipt.get("symbol") or "").replace("/", "").upper() != SYMBOL
        or normalized_sides != {"BUY", "SELL"}
        or authorized_quote is None or authorized_quote != max_quote
        or max_quote > MAX_QUOTE_CAP
        or receipt.get("authorized") is not True
        or receipt.get("provider_submission_authorized") is not True
        or receipt.get("one_cycle") is not True
        or receipt.get("containment_exit_authorized") is not True
        or receipt.get("leverage_allowed") is not False
        or receipt.get("margin_allowed") is not False
        or receipt.get("transfers_allowed") is not False
        or receipt.get("issued_at") != AUTH_ISSUED_AT
        or receipt.get("expires_at") != AUTH_EXPIRES_AT
        or issued_at != expected_issued_at
        or expires_at != expected_expires_at
        or issued_at is None or expires_at is None
        or now < issued_at or now >= expires_at
    ):
        return None, "authorization_scope_mismatch"
    return {
        "data_status": "live",
        "truth_status": "real_operator",
        "generated_values": False,
        "source_id": receipt["source_id"],
        "source_timestamp": receipt["source_timestamp"],
        "received_at": receipt["received_at"],
        "receipt_id": receipt["receipt_id"],
        "receipt_type": str(
            receipt.get("receipt_type") or "owner_live_order_authorization"
        ),
        "input_receipt_ids": [],
        "authorization_id": authorization_id,
        "intent_id": intent_id, "owner": owner, "venue": VENUE,
        "account_environment": "live_spot", "symbol": SYMBOL,
        "side_scope": ["BUY", "SELL"],
        "max_quote_notional": format(max_quote, "f"),
        "issued_at": AUTH_ISSUED_AT, "expires_at": AUTH_EXPIRES_AT,
        "entry_cutoff_at": ENTRY_CUTOFF_AT,
        "issued_at_epoch": issued_at, "expires_at_epoch": expires_at,
        "leverage_allowed": False, "margin_allowed": False,
        "transfers_allowed": False,
        "authorized": True,
        "provider_submission_authorized": True,
        "one_cycle": True,
        "containment_exit_authorized": True,
        "eligible_for_action": False,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
    }, None


def _cognitive_chain(
    hnc_raw: Any, auris_raw: Any, *, now: float, require_open: bool,
) -> tuple[Optional[dict[str, Any]], Optional[dict[str, Any]], Optional[str]]:
    hnc = _live_receipt(
        hnc_raw, now=now, truth_statuses={"real_derived"},
    )
    auris = _live_receipt(
        auris_raw, now=now, truth_statuses={"real_derived"},
    )
    if hnc is None:
        return None, None, "fresh_raw_hnc_receipt_required"
    if auris is None:
        return None, None, "fresh_raw_auris_receipt_required"
    if any(hnc.get(alias) is not False for alias in _FALSE_COGNITIVE_ALIASES):
        return None, None, "raw_hnc_must_remain_action_ineligible"
    if any(auris.get(alias) is not False for alias in _FALSE_COGNITIVE_ALIASES):
        return None, None, "raw_auris_must_remain_action_ineligible"
    for receipt in (hnc, auris):
        for alias in ("action", "accounting", "learning"):
            if alias in receipt and receipt.get(alias) is not False:
                return None, None, "raw_cognitive_alias_must_be_false"
    if (
        hnc.get("receipt_type") != "hnc_live_field"
        or hnc.get("equation_inputs_complete") is not True
        or _finite_decimal(hnc.get("coherence_gamma"), nonnegative=True) is None
        or _finite_decimal(
            hnc.get("symbolic_life_score"), nonnegative=True,
        ) is None
    ):
        return None, None, "complete_hnc_equation_receipt_required"
    auris_links = auris.get("input_receipt_ids")
    if (
        auris.get("receipt_type") != "auris_cosmic_state"
        or auris.get("hnc_receipt_id") != hnc["receipt_id"]
        or not isinstance(auris_links, list)
        or hnc["receipt_id"] not in {str(value) for value in auris_links}
        or auris.get("equation_inputs_complete") is not True
    ):
        return None, None, "auris_must_link_exact_hnc_receipt"
    if require_open and (
        auris.get("gate_open") is not True
        or auris.get("advisory") != "TRADE"
    ):
        return None, None, "hnc_auris_cognitive_gate_closed"
    hnc_safe = {
        **_receipt_provenance(hnc),
        "receipt_type": "hnc_live_field",
        "input_receipt_ids": _safe_input_receipt_ids(
            hnc.get("input_receipt_ids")
        ),
        "equation_inputs_complete": True,
        "coherence_gamma": format(
            Decimal(str(hnc["coherence_gamma"])), "f",
        ),
        "symbolic_life_score": format(
            Decimal(str(hnc["symbolic_life_score"])), "f",
        ),
        "action": False, "accounting": False, "learning": False,
    }
    auris_safe = {
        **_receipt_provenance(auris),
        "receipt_type": "auris_cosmic_state",
        "input_receipt_ids": _safe_input_receipt_ids(
            auris.get("input_receipt_ids")
        ),
        "hnc_receipt_id": hnc["receipt_id"],
        "equation_inputs_complete": True,
        "gate_open": auris.get("gate_open") is True,
        "advisory": str(auris.get("advisory") or "").upper(),
        "action": False, "accounting": False, "learning": False,
    }
    for alias in _FALSE_COGNITIVE_ALIASES:
        hnc_safe[alias] = False
        auris_safe[alias] = False
    return hnc_safe, auris_safe, None


def _market_receipt(raw: Any, *, now: float) -> Optional[dict[str, Any]]:
    receipt = _live_receipt(
        raw, now=now, truth_statuses={"real_observed", "real_provider"},
    )
    if receipt is None:
        return None
    price = _finite_decimal(receipt.get("price"), positive=True)
    bid = _finite_decimal(receipt.get("bid"), positive=True)
    ask = _finite_decimal(receipt.get("ask"), positive=True)
    if (
        str(receipt.get("symbol") or "").replace("/", "").upper() != SYMBOL
        or None in (price, bid, ask) or bid > ask
        or receipt.get("eligible_for_action") is not True
    ):
        return None
    return {
        **_receipt_provenance(receipt),
        "receipt_type": str(
            receipt.get("receipt_type") or "binance_spot_ticker"
        ),
        "symbol": SYMBOL, "base_asset": BASE_ASSET,
        "quote_asset": QUOTE_ASSET, "price": format(price, "f"),
        "bid": format(bid, "f"), "ask": format(ask, "f"),
        "eligible_for_action": True,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
    }


def _account_receipt(
    raw: Any, *, now: float, asset: str,
) -> Optional[dict[str, Any]]:
    receipt = _live_receipt(
        raw, now=now, truth_statuses={"real_provider", "real_observed"},
    )
    free = (
        _finite_decimal(receipt.get("free"), nonnegative=True)
        if receipt is not None else None
    )
    if (
        receipt is None or str(receipt.get("asset") or "").upper() != asset
        or free is None or receipt.get("eligible_for_action") is not True
    ):
        return None
    return {
        **_receipt_provenance(receipt),
        "receipt_type": str(
            receipt.get("receipt_type") or "binance_spot_balance"
        ),
        "asset": asset, "free": format(free, "f"),
        "eligible_for_action": True,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
    }


def _account_permission_receipt(
    raw: Any, *, now: float,
) -> Optional[dict[str, Any]]:
    receipt = _live_receipt(
        raw,
        now=now,
        truth_statuses={"real_provider"},
        max_age_seconds=60.0,
    )
    if receipt is None:
        return None
    raw_permissions = receipt.get("permissions")
    if (
        not isinstance(raw_permissions, list)
        or not raw_permissions
        or any(
            not isinstance(value, str) or not value.strip()
            for value in raw_permissions
        )
    ):
        return None
    permissions = sorted({
        value.strip().upper() for value in raw_permissions
    })
    if raw_permissions != permissions:
        return None
    if (
        "SPOT" not in permissions
        or any(
            permission != "SPOT"
            and not (
                permission.startswith("TRD_GRP_")
                and len(permission) > len("TRD_GRP_")
            )
            for permission in permissions
        )
    ):
        return None
    server_time_value = _finite_decimal(
        receipt.get("server_time"), positive=True,
    )
    if (
        server_time_value is None
        or server_time_value != server_time_value.to_integral_value()
    ):
        return None
    server_time = int(server_time_value)
    provider_timestamp = _finite_timestamp(server_time)
    if (
        provider_timestamp is None
        or abs(provider_timestamp - float(receipt["source_timestamp"])) > 0.001
    ):
        return None
    safety_flags = {
        name: receipt.get(name) is True
        for name in _ACCOUNT_PERMISSION_TRUE_FLAGS
    }
    receipt_material = {
        "account_type": str(receipt.get("account_type") or ""),
        "permissions": permissions,
        "server_time": server_time,
        **safety_flags,
    }
    expected_receipt_id = "binance:account_permission:" + hashlib.sha256(
        json.dumps(
            receipt_material,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    if (
        receipt.get("provider_receipt_type")
        != "Account+ApiRestrictions+ApiTradingStatus+Time"
        or receipt.get("source_id") != (
            "binance:/api/v3/account"
            "+/sapi/v1/account/apiRestrictions"
            "+/sapi/v1/account/apiTradingStatus"
            "+/api/v3/time"
        )
        or receipt.get("account_type") != "SPOT"
        or any(value is not True for value in safety_flags.values())
        or receipt.get("safe_for_bounded_spot_buy") is not True
        or receipt.get("eligible_for_action") is not True
        or receipt.get("eligible_for_accounting") is not False
        or receipt.get("eligible_for_learning") is not False
        or receipt.get("action") is not False
        or receipt.get("accounting") is not False
        or receipt.get("learning") is not False
        or receipt["receipt_id"] != expected_receipt_id
    ):
        return None
    return {
        **_receipt_provenance(receipt),
        "provider_receipt_type": (
            "Account+ApiRestrictions+ApiTradingStatus+Time"
        ),
        "account_type": "SPOT",
        "permissions": permissions,
        "server_time": server_time,
        **safety_flags,
        "safe_for_bounded_spot_buy": True,
        "eligible_for_action": True,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
        "action": False,
        "accounting": False,
        "learning": False,
    }


def _filter_receipt(raw: Any, *, now: float) -> Optional[dict[str, Any]]:
    receipt = _live_receipt(raw, now=now, truth_statuses={"real_observed"})
    if receipt is None:
        return None
    step_size = _finite_decimal(receipt.get("step_size"), positive=True)
    min_qty = _finite_decimal(receipt.get("min_qty"), positive=True)
    max_qty = _finite_decimal(receipt.get("max_qty"), positive=True)
    min_notional = _finite_decimal(receipt.get("min_notional"), positive=True)
    try:
        base_precision = int(receipt.get("base_precision"))
        quote_precision = int(receipt.get("quote_precision"))
    except (TypeError, ValueError):
        return None
    if (
        receipt.get("provider_receipt_type") != "ExchangeInfo+Time"
        or str(receipt.get("base_asset") or "").upper() != BASE_ASSET
        or str(receipt.get("quote_asset") or "").upper() != QUOTE_ASSET
        or None in (step_size, min_qty, max_qty, min_notional)
        or not 0 <= base_precision <= 20
        or not 0 <= quote_precision <= 20
    ):
        return None
    return {
        **_receipt_provenance(receipt),
        "provider_receipt_type": "ExchangeInfo+Time",
        "symbol": SYMBOL,
        "base_asset": BASE_ASSET, "quote_asset": QUOTE_ASSET,
        "step_size": format(step_size, "f"),
        "min_qty": format(min_qty, "f"), "max_qty": format(max_qty, "f"),
        "min_notional": format(min_notional, "f"),
        "base_precision": base_precision, "quote_precision": quote_precision,
        "eligible_for_action": True,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
        "action": False, "accounting": False, "learning": False,
    }


def _trade_fee_receipt(raw: Any, *, now: float) -> Optional[dict[str, Any]]:
    receipt = _live_receipt(
        raw, now=now, truth_statuses={"real_provider"},
    )
    if receipt is None:
        return None
    maker = _finite_decimal(
        receipt.get("maker_commission"), nonnegative=True,
    )
    taker = _finite_decimal(
        receipt.get("taker_commission"), nonnegative=True,
    )
    if (
        receipt.get("provider_receipt_type") != "TradeFee+Time"
        or str(receipt.get("symbol") or "").replace("/", "").upper() != SYMBOL
        or maker is None or taker is None or maker >= 1 or taker >= 1
        or receipt.get("eligible_for_action") is not True
    ):
        return None
    return {
        **_receipt_provenance(receipt),
        "provider_receipt_type": "TradeFee+Time",
        "symbol": SYMBOL,
        "maker_commission": format(maker, "f"),
        "taker_commission": format(taker, "f"),
        "fee_currency_policy": "provider_fill_determines_asset",
        "eligible_for_action": True,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
        "action": False, "accounting": False, "learning": False,
    }


def _fee_policy_receipt(
    authorization: Mapping[str, Any],
    filters: Mapping[str, Any],
    fee_receipt: Mapping[str, Any],
    *,
    now: float,
) -> dict[str, Any]:
    input_ids = [
        str(authorization["receipt_id"]), str(filters["receipt_id"]),
        str(fee_receipt["receipt_id"]),
    ]
    payload = {
        "policy": "terminal_provider_fill_fee_only", "symbol": SYMBOL,
        "input_receipt_ids": input_ids,
    }
    source_timestamp = max(
        float(filters["source_timestamp"]),
        float(fee_receipt["source_timestamp"]),
    )
    return {
        "data_status": "live", "truth_status": "real_derived",
        "generated_values": False,
        "source_id": "aureon:bounded-binance-roundtrip:fee-policy:v1",
        "source_timestamp": source_timestamp, "received_at": now,
        "derived_at": now, "recorded_at": now,
        "receipt_id": _json_digest("binance_fee_policy", payload),
        "receipt_type": "provider_terminal_fee_policy",
        "input_receipt_ids": input_ids,
        "fee_policy": "exact_rate_cap_then_terminal_provider_fill_fee",
        "taker_commission": fee_receipt["taker_commission"],
        "estimated_fee": None, "eligible_for_action": False,
        "eligible_for_accounting": False, "eligible_for_learning": False,
        "action": False, "accounting": False, "learning": False,
    }


def _action_receipt(
    *, side: str, authorization: Mapping[str, Any],
    market: Mapping[str, Any], account: Mapping[str, Any],
    filters: Mapping[str, Any], fee_receipt: Mapping[str, Any],
    fee_policy: Mapping[str, Any],
    hnc: Mapping[str, Any], auris: Mapping[str, Any], now: float,
    permission_receipt: Optional[Mapping[str, Any]] = None,
    entry_receipt: Optional[Mapping[str, Any]] = None,
    containment: bool = False,
) -> dict[str, Any]:
    inputs = [
        str(authorization["receipt_id"]), str(market["receipt_id"]),
        str(account["receipt_id"]), str(filters["receipt_id"]),
        str(fee_receipt["receipt_id"]), str(fee_policy["receipt_id"]),
        str(hnc["receipt_id"]),
        str(auris["receipt_id"]),
    ]
    if side == "BUY":
        if permission_receipt is None:
            raise ValueError("account_permission_receipt_required_for_buy")
        inputs.append(str(permission_receipt["receipt_id"]))
    elif permission_receipt is not None:
        raise ValueError("account_permission_receipt_is_buy_only")
    if entry_receipt is not None:
        inputs.append(str(entry_receipt["receipt_id"]))
    inputs = list(dict.fromkeys(inputs))
    payload = {
        "intent_id": authorization["intent_id"], "side": side,
        "symbol": SYMBOL, "containment": containment,
        "input_receipt_ids": inputs,
    }
    linked_receipts = [
        authorization, market, account, filters, fee_receipt,
        fee_policy, hnc, auris,
    ]
    if permission_receipt is not None:
        linked_receipts.append(permission_receipt)
    if entry_receipt is not None:
        linked_receipts.append(entry_receipt)
    source_timestamp = max(
        float(receipt["source_timestamp"])
        for receipt in linked_receipts
    )
    action_receipt = {
        "data_status": "live", "truth_status": "real_derived",
        "generated_values": False,
        "source_id": "aureon:bounded-binance-roundtrip:action:v1",
        "source_timestamp": source_timestamp, "received_at": now,
        "derived_at": now, "recorded_at": now,
        "receipt_id": _json_digest("binance_action", payload),
        "receipt_type": "route_specific_action_authorization",
        "input_receipt_ids": inputs,
        "authorization_id": authorization["authorization_id"],
        "intent_id": authorization["intent_id"], "venue": VENUE,
        "symbol": SYMBOL, "side": side,
        "market_receipt_id": market["receipt_id"],
        "account_receipt_id": account["receipt_id"],
        "filter_receipt_id": filters["receipt_id"],
        "fee_receipt_id": fee_receipt["receipt_id"],
        "fee_policy_receipt_id": fee_policy["receipt_id"],
        "hnc_receipt_id": hnc["receipt_id"],
        "auris_receipt_id": auris["receipt_id"],
        "cognitive_gate_required": True,
        "cognitive_gate_open": bool(auris.get("gate_open")),
        "containment_exit": containment, "action_gate_passed": True,
        'economic_dual_voice_required': True,
        'contingency_warrant_required': containment,
        "entry_receipt_id": (
            entry_receipt["receipt_id"]
            if entry_receipt is not None else None
        ),
        "eligible_for_action": True, "eligible_for_accounting": False,
        "eligible_for_learning": False, "economic_mutation": False,
    }
    if permission_receipt is not None:
        action_receipt["account_permission_receipt_id"] = (
            permission_receipt["receipt_id"]
        )
    return action_receipt


def _terminal_fill(
    raw: Any, *, side: str, client_order_id: str, now: float,
) -> Optional[dict[str, Any]]:
    receipt = _live_receipt(raw, now=now, truth_statuses={"real_observed"})
    if receipt is None:
        return None
    filled_qty = _finite_decimal(receipt.get("filled_qty"), positive=True)
    filled_notional = _finite_decimal(
        receipt.get("filled_notional"), positive=True,
    )
    fill_price = _finite_decimal(
        receipt.get("filled_avg_price"), positive=True,
    )
    fee = _finite_decimal(receipt.get("fee"), nonnegative=True)
    fills = receipt.get("fills")
    trade_ids = [
        _identifier(row.get("tradeId"))
        for row in fills if isinstance(row, Mapping)
    ] if isinstance(fills, list) else []
    if (
        receipt.get("status") != "FILLED"
        or receipt.get("fill_receipt_complete") is not True
        or receipt.get("eligible_for_accounting") is not True
        or receipt.get("eligible_for_learning") is not True
        or receipt.get("reconciliation_required") is not False
        or str(receipt.get("symbol") or "").replace("/", "").upper() != SYMBOL
        or str(receipt.get("side") or "").upper() != side
        or receipt.get("clientOrderId") != client_order_id
        or _identifier(receipt.get("orderId")) is None
        or None in (filled_qty, filled_notional, fill_price, fee)
        or not str(receipt.get("fee_asset") or "").strip()
        or not trade_ids or any(value is None for value in trade_ids)
        or len(trade_ids) != len(set(trade_ids))
    ):
        return None
    return _safe_order_receipt(receipt)


class BoundedBinanceRoundTrip:
    """Durable one-cycle runner. Construction performs no external calls."""

    def __init__(
        self,
        client: Any,
        *,
        state_path: Path | str,
        hnc_receipt_supplier: Callable[[], Any],
        auris_receipt_supplier: Callable[[], Any],
        economic_boundary: EconomicGovernanceBoundary | None = None,
        contingency_recovery: DurableContingencyRecovery | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.client = client
        self.state_path = Path(state_path)
        self.hnc_receipt_supplier = hnc_receipt_supplier
        self.auris_receipt_supplier = auris_receipt_supplier
        self.economic_boundary = economic_boundary
        self.contingency_recovery = contingency_recovery
        self.clock = clock

    @property
    def account_environment(self) -> str:
        if bool(getattr(self.client, "use_testnet", False)):
            return "testnet"
        return "live_spot"

    @contextmanager
    def _state_lock(self):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = _lock_path(self.state_path)
        with lock_path.open("a+b") as handle:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
                os.fsync(handle.fileno())
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(
                    handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB,
                )
            try:
                yield
            finally:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _load(self) -> Optional[dict[str, Any]]:
        return _read_verified_state(self.state_path)

    def _save(self, state: dict[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        previous = _read_verified_state(self.state_path)
        previous_state_hash = (
            previous.get("state_hash") if previous is not None else None
        )
        previous_event_hash = (
            previous.get("latest_event_hash") if previous is not None else None
        )
        sequence = (
            int(previous.get("state_sequence", 0)) + 1
            if previous is not None else 1
        )
        next_state = {
            **dict(state),
            "state_sequence": sequence,
            "previous_state_hash": previous_state_hash,
        }
        next_state.pop("state_hash", None)
        next_state.pop("latest_event_hash", None)
        state_hash = _hash_mapping(_state_hash_payload(next_state))
        receipt_ids = []
        for key in (
            "entry_action_receipt", "entry_receipt",
            "exit_action_receipt", "exit_receipt", "completion_receipt",
        ):
            candidate = next_state.get(key)
            receipt_id = (
                _identifier(candidate.get("receipt_id"))
                if isinstance(candidate, Mapping) else None
            )
            if receipt_id is not None:
                receipt_ids.append(receipt_id)
        economic_lineage: dict[str, dict[str, Any]] = {}
        for leg in ('entry', 'exit'):
            lineage = next_state.get(f'{leg}_economic_governance')
            if isinstance(lineage, Mapping):
                economic_lineage[leg] = {
                    key: lineage.get(key)
                    for key in (
                        'intent_digest',
                        'proposal_digest',
                        'dual_receipt_id',
                        'permit_id',
                        'permit_kind',
                        'contingency_warrant_id',
                        'contingency_scope_digest',
                        'state_anchor_hash',
                        'consume_status',
                    )
                }
                dual_receipt_id = _identifier(
                    lineage.get('dual_receipt_id')
                )
                if (
                    dual_receipt_id is not None
                    and dual_receipt_id not in receipt_ids
                ):
                    receipt_ids.append(dual_receipt_id)
        event_material = {
            "schema": "aureon.bounded_binance_roundtrip.event.v1",
            "sequence": sequence,
            "recorded_at": self.clock(),
            "stage": next_state.get("stage"),
            "state_hash": state_hash,
            "previous_event_hash": previous_event_hash,
            "receipt_ids": receipt_ids,
        }
        event_material['economic_lineage'] = economic_lineage
        event_hash = _hash_mapping(event_material)
        next_state["state_hash"] = state_hash
        next_state["latest_event_hash"] = event_hash
        serialized = json.dumps(
            next_state, indent=2, sort_keys=True, allow_nan=False,
        ) + "\n"
        temporary_name: Optional[str] = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.state_path.parent,
                prefix=self.state_path.name + ".",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_name = temporary.name
                temporary.write(serialized)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_name, self.state_path)
            temporary_name = None
            event = {**event_material, "event_hash": event_hash}
            with _events_path(self.state_path).open(
                "a", encoding="utf-8",
            ) as event_stream:
                event_stream.write(json.dumps(
                    event, sort_keys=True, separators=(",", ":"),
                    allow_nan=False,
                ) + "\n")
                event_stream.flush()
                os.fsync(event_stream.fileno())
        finally:
            if temporary_name is not None:
                try:
                    Path(temporary_name).unlink()
                except OSError:
                    pass
        state.clear()
        state.update(next_state)

    def _window_open(self, authorization: Mapping[str, Any]) -> bool:
        now = self.clock()
        issued = _finite_timestamp(authorization.get("issued_at"))
        expires = _finite_timestamp(authorization.get("expires_at"))
        return (
            issued is not None and expires is not None
            and issued <= now < expires
        )

    def _authorized_call(
        self,
        authorization: Mapping[str, Any],
        callable_: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        if not self._window_open(authorization):
            raise RuntimeError("authorization_window_closed")
        return callable_(*args, **kwargs)

    @staticmethod
    def _canonical_economic_decimal(value: Any) -> str:
        try:
            number = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError('canonical_positive_decimal_required') from exc
        if not number.is_finite() or number <= 0:
            raise ValueError('canonical_positive_decimal_required')
        text = format(number, 'f')
        if '.' in text:
            text = text.rstrip('0').rstrip('.')
        return text

    def _economic_cycle_id(self, state: Mapping[str, Any]) -> str:
        intent_id = _identifier(state.get('intent_id'))
        if intent_id is None or len(self.state_path.stem) != 64:
            raise ValueError('durable_cycle_identity_required')
        return f'{intent_id}:{self.state_path.stem}'

    @staticmethod
    def _economic_account_hash(state: Mapping[str, Any]) -> str:
        authorization = state.get('authorization')
        permission = state.get('account_permission_receipt')
        if not isinstance(authorization, Mapping) or not isinstance(
            permission, Mapping,
        ):
            raise ValueError('account_scope_receipts_required')
        return _hash_mapping({
            'venue': VENUE,
            'environment': state.get('account_environment'),
            'authorization_id': authorization.get('authorization_id'),
            'authorization_source_id': authorization.get('source_id'),
            'permission_receipt_id': permission.get('receipt_id'),
            'permission_source_id': permission.get('source_id'),
        })

    @staticmethod
    def _economic_provider_receipts(
        state: Mapping[str, Any],
        *,
        leg: str,
    ) -> list[Mapping[str, Any]]:
        if leg == 'entry':
            keys = (
                'account_permission_receipt',
                'entry_market_receipt',
                'quote_account_receipt',
                'pre_entry_base_account_receipt',
                'entry_filter_receipt',
                'entry_fee_receipt',
            )
        else:
            keys = (
                'pre_entry_base_account_receipt',
                'post_entry_base_account_receipt',
                'entry_receipt',
                'exit_market_receipt',
                'exit_filter_receipt',
                'exit_fee_receipt',
            )
        receipts: list[Mapping[str, Any]] = []
        seen: set[str] = set()
        for key in keys:
            receipt = state.get(key)
            if not isinstance(receipt, Mapping):
                raise ValueError(f'{key}_required_for_economic_lineage')
            receipt_id = _identifier(receipt.get('receipt_id'))
            source_id = _identifier(receipt.get('source_id'))
            source_timestamp = _finite_timestamp(
                receipt.get('source_timestamp')
            )
            if (
                receipt_id is None
                or source_id is None
                or source_timestamp is None
                or receipt_id in seen
            ):
                raise ValueError('distinct_provider_receipt_lineage_required')
            receipts.append(receipt)
            seen.add(receipt_id)
        return receipts

    def _economic_provider_moment(
        self,
        state: Mapping[str, Any],
        *,
        leg: str,
        state_anchor_hash: str,
    ) -> tuple[tuple[str, ...], str, str]:
        if (
            len(state_anchor_hash) != 64
            or any(char not in '0123456789abcdef' for char in state_anchor_hash)
        ):
            raise ValueError('durable_submitting_state_anchor_required')
        receipts = self._economic_provider_receipts(state, leg=leg)
        rows = sorted(
            (
                {
                    'receipt_id': str(receipt['receipt_id']),
                    'source_id': str(receipt['source_id']),
                    'source_timestamp': receipt['source_timestamp'],
                    'received_at': receipt['received_at'],
                    'data_status': receipt['data_status'],
                    'truth_status': receipt['truth_status'],
                }
                for receipt in receipts
            ),
            key=lambda item: item['receipt_id'],
        )
        source_timestamp = max(
            float(receipt['source_timestamp']) for receipt in receipts
        )
        return (
            tuple(item['receipt_id'] for item in rows),
            _hash_mapping({
                'schema': 'aureon.binance.provider_moment.v1',
                'state_anchor_hash': state_anchor_hash,
                'provider_receipts': rows,
            }),
            self._canonical_economic_decimal(source_timestamp),
        )

    def _economic_wire_body(
        self,
        state: Mapping[str, Any],
        *,
        leg: str,
        side: str,
        quantity: Decimal | None,
        quote_qty: Decimal | None,
    ) -> tuple[dict[str, Any], dict[str, str], str | None, str | None]:
        body: dict[str, Any] = {
            'symbol': SYMBOL,
            'side': side,
            'type': 'MARKET',
            'newOrderRespType': 'FULL',
            'newClientOrderId': state[f'{leg}_client_order_id'],
        }
        bindings = {
            'symbol': '/symbol',
            'side': '/side',
            'order_type': '/type',
            'client_order_id': '/newClientOrderId',
        }
        quantity_text = (
            self._canonical_economic_decimal(quantity)
            if quantity is not None else None
        )
        quote_text = (
            self._canonical_economic_decimal(quote_qty)
            if quote_qty is not None else None
        )
        if (quantity_text is None) == (quote_text is None):
            raise ValueError('exactly_one_order_quantity_required')
        if quantity_text is not None:
            body['quantity'] = quantity_text
            bindings['quantity'] = '/quantity'
        else:
            body['quoteOrderQty'] = quote_text
            bindings['quote_quantity'] = '/quoteOrderQty'
        return body, bindings, quantity_text, quote_text

    def _build_economic_intent(
        self,
        state: Mapping[str, Any],
        *,
        leg: str,
        side: str,
        quantity: Decimal | None,
        quote_qty: Decimal | None,
        state_anchor_hash: str,
    ) -> EconomicIntent:
        body, bindings, quantity_text, quote_text = self._economic_wire_body(
            state,
            leg=leg,
            side=side,
            quantity=quantity,
            quote_qty=quote_qty,
        )
        provider_ids, provider_digest, provider_timestamp = (
            self._economic_provider_moment(
                state,
                leg=leg,
                state_anchor_hash=state_anchor_hash,
            )
        )
        position_key = (
            'pre_entry_base_account_receipt'
            if leg == 'entry' else 'post_entry_base_account_receipt'
        )
        position = state[position_key]
        hnc = state.get('hnc_receipt')
        auris = state.get('auris_receipt')
        authorization = state.get('authorization')
        if (
            not isinstance(position, Mapping)
            or not isinstance(hnc, Mapping)
            or not isinstance(auris, Mapping)
            or not isinstance(authorization, Mapping)
        ):
            raise ValueError('complete_economic_lineage_required')
        parent_intent_digest: str | None = None
        entry_receipt_id: str | None = None
        position_side: str | None = None
        observed_exposure: str | None = None
        if leg == 'exit':
            entry_lineage = state.get('entry_economic_governance')
            entry_receipt = state.get('entry_receipt')
            pre_entry = state.get('pre_entry_base_account_receipt')
            if (
                not isinstance(entry_lineage, Mapping)
                or not isinstance(entry_receipt, Mapping)
                or not isinstance(pre_entry, Mapping)
            ):
                raise ValueError('entry_economic_lineage_required')
            parent_intent_digest = str(entry_lineage['intent_digest'])
            entry_receipt_id = str(entry_receipt['receipt_id'])
            position_side = 'LONG'
            observed_exposure = self._canonical_economic_decimal(
                Decimal(str(position['free']))
                - Decimal(str(pre_entry['free']))
            )
        return EconomicIntent.build(
            venue=VENUE,
            environment=str(state['account_environment']),
            account_id_hash=self._economic_account_hash(state),
            method=ORDER_METHOD,
            path=ORDER_PATH,
            operation='MARKET_ORDER',
            purpose='ENTRY' if leg == 'entry' else 'CONTAINMENT_REDUCTION',
            symbol=SYMBOL,
            side=side,
            order_type='MARKET',
            quantity=quantity_text,
            quote_quantity=quote_text,
            limit_price=None,
            stop_price=None,
            take_profit=None,
            reduce_only=leg == 'exit',
            client_order_id=str(state[f'{leg}_client_order_id']),
            authorization_receipt_id=str(authorization['receipt_id']),
            cycle_id=self._economic_cycle_id(state),
            position_receipt_id=str(position['receipt_id']),
            parent_intent_digest=parent_intent_digest,
            entry_receipt_id=entry_receipt_id,
            position_side=position_side,
            observed_exposure_quantity=observed_exposure,
            hnc_receipt_id=str(hnc['receipt_id']),
            auris_receipt_id=str(auris['receipt_id']),
            provider_receipt_ids=provider_ids,
            provider_moment_digest=provider_digest,
            provider_source_timestamp=provider_timestamp,
            body=body,
            body_bindings=bindings,
        )

    def _build_entry_contingency_scope(
        self,
        state: Mapping[str, Any],
        intent: EconomicIntent,
    ) -> ContingencyWarrantScope:
        pre_entry = state.get('pre_entry_base_account_receipt')
        if (
            not isinstance(pre_entry, Mapping)
            or intent.purpose != 'ENTRY'
            or intent.quote_quantity is None
        ):
            raise ValueError('entry_contingency_lineage_required')
        max_reduce_quantity = self._canonical_economic_decimal(
            state.get('preflight_estimated_base_qty')
        )
        return ContingencyWarrantScope.build(
            venue=intent.venue,
            environment=intent.environment,
            account_id_hash=intent.account_id_hash,
            symbol=intent.symbol,
            exposure_side='LONG',
            reduction_side='SELL',
            method=intent.method,
            path=intent.path,
            order_type=intent.order_type,
            max_reduce_quantity=max_reduce_quantity,
            entry_intent_digest=intent.intent_digest,
            entry_client_order_id=str(state['entry_client_order_id']),
            containment_client_order_id=str(state['exit_client_order_id']),
            authorization_receipt_id=intent.authorization_receipt_id,
            cycle_id=intent.cycle_id,
            pre_entry_position_receipt_id=str(pre_entry['receipt_id']),
            provider_reduce_only_supported=False,
            hnc_receipt_id=intent.hnc_receipt_id,
            auris_receipt_id=intent.auris_receipt_id,
            provider_receipt_ids=intent.provider_receipt_ids,
            provider_moment_digest=intent.provider_moment_digest,
            provider_source_timestamp=intent.provider_source_timestamp,
        )

    @staticmethod
    def _recovery_reference(
        state: Mapping[str, Any],
    ) -> DurableContingencyRecordRef:
        lineage = state.get('entry_economic_governance')
        if not isinstance(lineage, Mapping):
            raise ValueError('entry_recovery_lineage_required')
        return DurableContingencyRecordRef(
            record_digest=str(
                lineage['contingency_recovery_record_digest']
            ),
            entry_state_anchor=str(
                lineage['contingency_recovery_entry_state_anchor']
            ),
            bound_route_state_anchor=str(
                lineage['contingency_recovery_route_binding_anchor']
            ),
        )

    def _economic_lineage(
        self,
        *,
        intent: EconomicIntent,
        permit: EconomicMutationPermit,
        state_anchor_hash: str,
        warrant: ContingencyWarrant | None = None,
        scope: ContingencyWarrantScope | None = None,
        recovery_reference: DurableContingencyRecordRef | None = None,
    ) -> dict[str, Any]:
        return {
            'schema': ECONOMIC_LINEAGE_SCHEMA,
            'intent_digest': intent.intent_digest,
            'method': intent.method,
            'path': intent.path,
            'body_digest': intent.body_digest,
            'provider_moment_digest': intent.provider_moment_digest,
            'state_anchor_hash': state_anchor_hash,
            'authorization_receipt_id': intent.authorization_receipt_id,
            'cycle_id': intent.cycle_id,
            'position_receipt_id': intent.position_receipt_id,
            'hnc_receipt_id': intent.hnc_receipt_id,
            'auris_receipt_id': intent.auris_receipt_id,
            'proposal_digest': permit.proposal_digest,
            'dual_receipt_id': permit.dual_receipt_id,
            'permit_id': permit.permit_id,
            'permit_kind': permit.permit_kind,
            'permit_expires_at': permit.expires_at,
            'contingency_warrant_id': (
                warrant.warrant_id if warrant is not None else None
            ),
            'contingency_scope_digest': (
                scope.scope_digest if scope is not None else None
            ),
            'contingency_warrant': (
                asdict(warrant) if warrant is not None else None
            ),
            'contingency_scope': (
                scope.payload() if scope is not None else None
            ),
            'contingency_recovery_record_digest': (
                recovery_reference.record_digest
                if recovery_reference is not None else None
            ),
            'contingency_recovery_entry_state_anchor': (
                recovery_reference.entry_state_anchor
                if recovery_reference is not None else None
            ),
            'contingency_recovery_route_binding_anchor': (
                recovery_reference.bound_route_state_anchor
                if recovery_reference is not None else None
            ),
            'consume_status': 'prepared',
            'prepared_at': self.clock(),
            'route_authorization_required': True,
            'economic_mutation': False,
            'eligible_for_action': False,
            'eligible_for_accounting': False,
            'eligible_for_learning': False,
        }

    def _economic_block(
        self,
        state: dict[str, Any],
        *,
        leg: str,
        reason: str,
        state_anchor_hash: str,
    ) -> dict[str, Any]:
        state['stage'] = (
            'entry_governance_blocked'
            if leg == 'entry' else 'containment_blocked'
        )
        state['failure_reason'] = reason
        state[f'{leg}_economic_governance_failure'] = {
            'schema': ECONOMIC_LINEAGE_SCHEMA,
            'reason': reason,
            'state_anchor_hash': state_anchor_hash,
            'route_authorization_required': True,
            'economic_mutation': False,
            'eligible_for_action': False,
            'eligible_for_accounting': False,
            'eligible_for_learning': False,
        }
        state['updated_at'] = self.clock()
        self._save(state)
        return _no_action(reason, stage=state['stage'])

    def _pending_snapshot(self, side: str) -> Optional[dict[str, Any]]:
        key = (SYMBOL, side, False)
        pending = getattr(self.client, "_pending_orders", None)
        row = pending.get(key) if isinstance(pending, dict) else None
        if not isinstance(row, dict):
            return None
        raw_order = dict(row.get("order") or {})
        safe_order = {
            key: value for key, value in raw_order.items()
            if key in _ORDER_SNAPSHOT_KEYS and key != "fills"
        }
        raw_fills = raw_order.get("fills")
        if isinstance(raw_fills, list):
            safe_order["fills"] = [
                {
                    fill_key: fill[fill_key]
                    for fill_key in _FILL_KEYS if fill_key in fill
                }
                for fill in raw_fills if isinstance(fill, Mapping)
            ]
        return {
            "order_id": _identifier(row.get("order_id")),
            "client_order_id": _identifier(row.get("client_order_id")),
            "order": safe_order,
            "is_isolated": "FALSE",
        }

    def _hydrate_pending(
        self,
        state: Mapping[str, Any],
        *,
        side: str,
        leg: str,
    ) -> None:
        pending = getattr(self.client, "_pending_orders", None)
        if not isinstance(pending, dict):
            pending = {}
            self.client._pending_orders = pending
        snapshot = state.get(f"{leg}_client_pending")
        receipt = state.get(f"{leg}_receipt")
        client_order_id = state[f"{leg}_client_order_id"]
        pending[(SYMBOL, side, False)] = {
            "order_id": (
                _identifier(snapshot.get("order_id"))
                if isinstance(snapshot, Mapping)
                else (
                    _identifier(receipt.get("orderId"))
                    if isinstance(receipt, Mapping) else None
                )
            ),
            "client_order_id": client_order_id,
            "order": (
                dict(snapshot.get("order") or {})
                if isinstance(snapshot, Mapping) else {}
            ),
            "params": {"symbol": SYMBOL, "side": side},
            "is_isolated": "FALSE",
        }

    def _read_evidence(
        self,
        *,
        authorization_raw: Any,
        max_quote: Decimal,
        require_cognitive_open: bool,
        account_asset: str,
    ) -> tuple[Optional[dict[str, Any]], Optional[str]]:
        now = self.clock()
        authorization, error = _authorization(
            authorization_raw, now=now, max_quote=max_quote,
        )
        if error is not None:
            return None, error
        try:
            hnc_raw = self._authorized_call(
                authorization, self.hnc_receipt_supplier,
            )
            auris_raw = self._authorized_call(
                authorization, self.auris_receipt_supplier,
            )
            permission_raw = self._authorized_call(
                authorization,
                self.client.get_account_permission_receipt,
            )
            market_raw = self._authorized_call(
                authorization, self.client.get_ticker, SYMBOL,
            )
            account_raw = self._authorized_call(
                authorization, self.client.get_asset_balance, account_asset,
            )
            filters_raw = self._authorized_call(
                authorization,
                self.client.get_symbol_filters,
                SYMBOL,
                force_refresh=True,
            )
            fee_raw = self._authorized_call(
                authorization, self.client.get_trade_fee_receipt, SYMBOL,
            )
        except Exception:
            return None, "read_only_preflight_provider_receipt_unavailable"
        hnc, auris, cognitive_error = _cognitive_chain(
            hnc_raw, auris_raw, now=now,
            require_open=require_cognitive_open,
        )
        permission = _account_permission_receipt(permission_raw, now=now)
        market = _market_receipt(market_raw, now=now)
        account = _account_receipt(
            account_raw, now=now, asset=account_asset,
        )
        filters = _filter_receipt(filters_raw, now=now)
        fee = _trade_fee_receipt(fee_raw, now=now)
        if cognitive_error is not None:
            return None, cognitive_error
        if permission is None:
            return None, (
                "fresh_safe_binance_account_permission_receipt_required"
            )
        if market is None:
            return None, "fresh_binance_market_receipt_required"
        if account is None:
            return None, (
                f"fresh_binance_{account_asset.lower()}_account_receipt_required"
            )
        if filters is None:
            return None, "fresh_binance_filter_receipt_required"
        if fee is None:
            return None, "fresh_binance_trade_fee_receipt_required"
        fee_policy = _fee_policy_receipt(
            authorization, filters, fee, now=now,
        )
        return {
            "authorization": authorization, "hnc": hnc, "auris": auris,
            "permission": permission,
            "market": market, "account": account, "filters": filters,
            "fee": fee, "fee_policy": fee_policy,
        }, None

    def read_only_preflight(
        self,
        *,
        authorization_receipt: Any,
        confirmation_token: str,
        max_quote: Any,
    ) -> dict[str, Any]:
        quote_cap = _finite_decimal(max_quote, positive=True)
        if quote_cap is None or quote_cap > MAX_QUOTE_CAP:
            return _no_action(
                "max_quote_must_be_positive_and_at_most_10_usdt"
            )
        authorization, error = _authorization(
            authorization_receipt,
            now=self.clock(),
            max_quote=quote_cap,
        )
        if error is not None:
            return _no_action(error)
        if confirmation_token != expected_confirmation_token(
            authorization["authorization_id"]
        ):
            return _no_action("exact_confirmation_token_required")
        if not _new_entry_window_open(self.clock(), authorization):
            return _no_action("new_entry_window_closed")
        if not _state_path_matches_scope(self.state_path, authorization):
            return _no_action("private_hashed_cycle_state_path_required")
        try:
            with self._state_lock():
                return self._read_only_preflight_locked(
                    authorization_receipt=authorization_receipt,
                    confirmation_token=confirmation_token,
                    max_quote=max_quote,
                )
        except (OSError, BlockingIOError, StateIntegrityError) as exc:
            return _no_action(
                "durable_cycle_state_unavailable",
                state_error=type(exc).__name__,
            )

    def _read_only_preflight_locked(
        self,
        *,
        authorization_receipt: Any,
        confirmation_token: str,
        max_quote: Any,
    ) -> dict[str, Any]:
        """Read and persist evidence; never call an order mutation endpoint."""
        quote_cap = _finite_decimal(max_quote, positive=True)
        if quote_cap is None or quote_cap > MAX_QUOTE_CAP:
            return _no_action(
                "max_quote_must_be_positive_and_at_most_10_usdt"
            )
        now = self.clock()
        authorization, auth_error = _authorization(
            authorization_receipt, now=now, max_quote=quote_cap,
        )
        if auth_error is not None:
            return _no_action(auth_error)
        if confirmation_token != expected_confirmation_token(
            authorization["authorization_id"]
        ):
            return _no_action("exact_confirmation_token_required")
        if not _new_entry_window_open(self.clock(), authorization):
            return _no_action("new_entry_window_closed")
        if self.account_environment != "live_spot":
            return _no_action("exact_live_spot_account_required")
        if bool(getattr(self.client, "dry_run", True)):
            return _no_action("explicit_live_binance_client_required")
        existing = self._load()
        if existing is not None:
            return _no_action(
                "one_cycle_state_already_exists",
                stage=existing.get("stage"),
                intent_id=existing.get("intent_id"),
            )
        evidence, error = self._read_evidence(
            authorization_raw=authorization_receipt,
            max_quote=quote_cap,
            require_cognitive_open=True,
            account_asset=QUOTE_ASSET,
        )
        if error is not None:
            return _no_action(error)
        quote_free = Decimal(str(evidence["account"]["free"]))
        if quote_free < quote_cap:
            return _no_action(
                "insufficient_observed_usdt_balance",
                observed_free=format(quote_free, "f"),
            )
        taker_rate = Decimal(str(evidence["fee"]["taker_commission"]))
        quote_precision = int(evidence["filters"]["quote_precision"])
        quote_scale = Decimal(1).scaleb(-quote_precision)
        entry_quote = (
            quote_cap / (Decimal(1) + taker_rate)
        ).quantize(quote_scale, rounding=ROUND_DOWN)
        reserved_quote_fee = entry_quote * taker_rate
        min_notional = Decimal(str(evidence["filters"]["min_notional"]))
        if (
            entry_quote <= 0
            or entry_quote + reserved_quote_fee > quote_cap
            or entry_quote < min_notional * MIN_EXIT_NOTIONAL_BUFFER
        ):
            return _no_action(
                "fee_inclusive_cap_cannot_support_buffered_entry_and_exit",
                entry_quote=format(entry_quote, "f"),
                reserved_quote_fee=format(reserved_quote_fee, "f"),
                provider_min_notional=format(min_notional, "f"),
            )
        ask = Decimal(str(evidence["market"]["ask"]))
        bid = Decimal(str(evidence["market"]["bid"]))
        step = Decimal(str(evidence["filters"]["step_size"]))
        min_qty = Decimal(str(evidence["filters"]["min_qty"]))
        estimated_base = (entry_quote / ask // step) * step
        if (
            estimated_base < min_qty
            or estimated_base * bid < min_notional
        ):
            return _no_action(
                "current_market_and_filters_cannot_support_containment_exit",
                estimated_base=format(estimated_base, "f"),
                estimated_exit_notional=format(estimated_base * bid, "f"),
            )
        try:
            base_before_raw = self._authorized_call(
                authorization,
                self.client.get_asset_balance,
                BASE_ASSET,
            )
        except Exception:
            return _no_action(
                "fresh_pre_entry_btc_balance_receipt_required"
            )
        base_before = _account_receipt(
            base_before_raw, now=self.clock(), asset=BASE_ASSET,
        )
        if base_before is None:
            return _no_action(
                "fresh_pre_entry_btc_balance_receipt_required"
            )
        action = _action_receipt(
            side="BUY", authorization=authorization,
            market=evidence["market"], account=evidence["account"],
            filters=evidence["filters"], fee_receipt=evidence["fee"],
            fee_policy=evidence["fee_policy"], hnc=evidence["hnc"],
            auris=evidence["auris"], now=self.clock(),
            permission_receipt=evidence["permission"],
        )
        state = {
            "schema": STATE_SCHEMA, "stage": "entry_reserved",
            "venue": VENUE, "account_environment": "live_spot",
            "symbol": SYMBOL, "spot_only": True,
            "leverage_allowed": False, "margin_allowed": False,
            "transfers_allowed": False,
            "max_quote_notional": format(quote_cap, "f"),
            "entry_cutoff_at": authorization["entry_cutoff_at"],
            "entry_quote_order_qty": format(entry_quote, "f"),
            "reserved_quote_fee": format(reserved_quote_fee, "f"),
            "preflight_estimated_base_qty": format(estimated_base, "f"),
            "authorization": authorization,
            "authorization_scope_id": authorization["authorization_id"],
            "intent_id": authorization["intent_id"],
            "entry_client_order_id": _client_order_id(
                authorization["intent_id"], "entry",
            ),
            "exit_client_order_id": _client_order_id(
                authorization["intent_id"], "exit",
            ),
            "entry_action_receipt": action,
            "account_permission_receipt": evidence["permission"],
            "entry_market_receipt": evidence["market"],
            "entry_filter_receipt": evidence["filters"],
            "entry_fee_receipt": evidence["fee"],
            "entry_fee_policy_receipt": evidence["fee_policy"],
            "hnc_receipt": evidence["hnc"],
            "auris_receipt": evidence["auris"],
            "quote_account_receipt": evidence["account"],
            "pre_entry_base_account_receipt": base_before,
            "created_at": self.clock(), "updated_at": self.clock(),
            "mutation_count": 0, "order_readback_count": 0,
        }
        self._save(state)
        return {
            "status": "prepared", "data_status": "live",
            "truth_status": "real_derived", "generated_values": False,
            "eligible_for_action": True, "economic_mutation": False,
            "stage": state["stage"], "state_path": str(self.state_path),
            "authorization_id": authorization["authorization_id"],
            "intent_id": authorization["intent_id"],
            "action_receipt_id": action["receipt_id"],
            "account_permission_receipt_id": (
                evidence["permission"]["receipt_id"]
            ),
            "entry_client_order_id": state["entry_client_order_id"],
            "max_quote_notional": state["max_quote_notional"],
            "entry_quote_order_qty": state["entry_quote_order_qty"],
            "reserved_quote_fee": state["reserved_quote_fee"],
        }

    def _authorization_for_state(
        self,
        state: Mapping[str, Any],
        authorization_receipt: Any,
        confirmation_token: str,
    ) -> tuple[Optional[dict[str, Any]], Optional[dict[str, Any]]]:
        if (
            self.account_environment != "live_spot"
            or bool(getattr(self.client, "dry_run", True))
        ):
            return None, _no_action("exact_live_spot_client_required")
        max_quote = Decimal(str(state["max_quote_notional"]))
        authorization, error = _authorization(
            authorization_receipt, now=self.clock(), max_quote=max_quote,
        )
        if error is not None:
            return None, _no_action(error, stage=state.get("stage"))
        if (
            not isinstance(state.get('authorization'), Mapping)
            or dict(authorization) != dict(state['authorization'])
            or authorization["authorization_id"]
            != state.get("authorization_scope_id")
            or authorization["intent_id"] != state.get("intent_id")
            or confirmation_token
            != expected_confirmation_token(authorization["authorization_id"])
        ):
            return None, _no_action(
                "persisted_authorization_scope_mismatch",
                stage=state.get("stage"),
            )
        if not _state_path_matches_scope(self.state_path, authorization):
            return None, _no_action(
                "private_hashed_cycle_state_path_required",
                stage=state.get("stage"),
            )
        return authorization, None

    def _record_order_result(
        self,
        state: dict[str, Any],
        *,
        leg: str,
        side: str,
        receipt: Any,
        readback: bool,
    ) -> dict[str, Any]:
        safe_receipt = _safe_order_receipt(receipt)
        state[f"{leg}_receipt"] = safe_receipt
        state[f"{leg}_client_pending"] = self._pending_snapshot(side)
        state["updated_at"] = self.clock()
        counter = "order_readback_count" if readback else "mutation_count"
        state[counter] = int(state.get(counter, 0)) + 1
        terminal = _terminal_fill(
            safe_receipt,
            side=side,
            client_order_id=state[f"{leg}_client_order_id"],
            now=self.clock(),
        )
        if terminal is not None:
            state[f"{leg}_receipt"] = terminal
            state[f"{leg}_client_pending"] = None
            state["stage"] = (
                "entry_filled" if leg == "entry" else "exit_filled"
            )
            if leg == "entry":
                quote_exposure = Decimal(str(terminal["filled_notional"]))
                if str(terminal["fee_asset"]).upper() == QUOTE_ASSET:
                    quote_exposure += Decimal(str(terminal["fee"]))
                state["observed_peak_quote_exposure"] = format(
                    quote_exposure, "f",
                )
                if quote_exposure > Decimal(
                    str(state["max_quote_notional"])
                ):
                    state["cap_breach_detected"] = True
                    state["cap_breach_reason"] = (
                        "provider_terminal_fee_exceeded_preflight_rate_cap"
                    )
        elif (
            isinstance(safe_receipt, Mapping)
            and safe_receipt.get("reconciliation_required") is False
            and safe_receipt.get("status")
            in {
                "not_submitted", "CANCELED", "CANCELLED",
                "EXPIRED", "REJECTED",
            }
        ):
            state["stage"] = (
                "aborted" if leg == "entry" else "containment_failed"
            )
            state["failure_reason"] = (
                "provider_terminal_without_complete_fill"
            )
        else:
            state["stage"] = f"{leg}_pending"
        self._save(state)
        submitted = (
            safe_receipt.get("submitted")
            if isinstance(safe_receipt, Mapping) else None
        )
        return {
            "status": state["stage"],
            "data_status": (
                safe_receipt.get("data_status")
                if isinstance(safe_receipt, Mapping) else "no_data"
            ),
            "mutation_attempted": not readback,
            "order_readback_performed": readback,
            "economic_mutation": submitted if isinstance(submitted, bool) else None,
            "provider_receipt": safe_receipt,
            "state_path": str(self.state_path),
        }

    def _submit_leg(
        self,
        state: dict[str, Any],
        authorization: Mapping[str, Any],
        *,
        leg: str,
        side: str,
        quantity: Optional[Decimal] = None,
        quote_qty: Optional[Decimal] = None,
    ) -> dict[str, Any]:
        boundary = self.economic_boundary
        if not isinstance(boundary, EconomicGovernanceBoundary):
            return _no_action(
                'trusted_economic_governance_boundary_required',
                stage=state.get('stage'),
            )
        recovery = self.contingency_recovery
        if (
            not isinstance(recovery, DurableContingencyRecovery)
            or recovery.boundary is not boundary
        ):
            return _no_action(
                'trusted_contingency_recovery_adapter_required',
                stage=state.get('stage'),
            )
        if leg == 'entry' and not _new_entry_window_open(self.clock(), authorization):
            return _no_action(
                'new_entry_window_closed', stage=state.get('stage'),
            )
        state['stage'] = f'{leg}_submitting'
        state['updated_at'] = self.clock()
        self._save(state)
        state_anchor_hash = str(state['state_hash'])
        warrant: ContingencyWarrant | None = None
        scope: ContingencyWarrantScope | None = None
        recovery_reference: DurableContingencyRecordRef | None = None
        recovered = None
        try:
            intent = self._build_economic_intent(
                state,
                leg=leg,
                side=side,
                quantity=quantity,
                quote_qty=quote_qty,
                state_anchor_hash=state_anchor_hash,
            )
            if leg == 'entry':
                permit = boundary.prepare_mutation(intent)
                scope = self._build_entry_contingency_scope(
                    state,
                    intent,
                )
                warrant = boundary.approve_contingency_warrant(scope)
                recovery_reference = recovery.register(
                    warrant,
                    scope,
                    entry_state_anchor=state_anchor_hash,
                )
            else:
                recovery_reference = self._recovery_reference(state)
                material = recovery.material_for_recovery(
                    recovery_reference
                )
                warrant = material.warrant
                scope = material.scope
                entry_lineage = state.get(
                    'entry_economic_governance'
                )
                if (
                    not isinstance(entry_lineage, Mapping)
                    or entry_lineage.get('contingency_warrant')
                    != asdict(warrant)
                    or entry_lineage.get('contingency_scope')
                    != scope.payload()
                ):
                    raise EconomicGovernanceBlocked(
                        'reciprocal_route_recovery_material_mismatch'
                    )
                recovered = recovery.prepare_reduction(
                    recovery_reference,
                    intent,
                )
                permit = recovered.permit
        except EconomicGovernanceBlocked:
            return self._economic_block(
                state,
                leg=leg,
                reason='strict_dual_economic_governance_required',
                state_anchor_hash=state_anchor_hash,
            )
        except Exception:
            return self._economic_block(
                state,
                leg=leg,
                reason='exact_economic_intent_lineage_required',
                state_anchor_hash=state_anchor_hash,
            )
        lineage = self._economic_lineage(
            intent=intent,
            permit=permit,
            state_anchor_hash=state_anchor_hash,
            warrant=warrant,
            scope=scope,
            recovery_reference=recovery_reference,
        )
        state[f'{leg}_economic_intent'] = intent.payload()
        state[f'{leg}_economic_governance'] = lineage
        state['updated_at'] = self.clock()
        self._save(state)
        if leg == 'entry':
            try:
                if recovery_reference is None:
                    raise EconomicGovernanceBlocked(
                        'durable_contingency_reference_required'
                    )
                recovery.bind_route_state(recovery_reference)
                recovery.verify_route_binding(recovery_reference)
            except Exception:
                return self._economic_block(
                    state,
                    leg=leg,
                    reason='reciprocal_contingency_binding_required',
                    state_anchor_hash=state_anchor_hash,
                )
        body = json.loads(intent.body_json)
        try:
            def transport() -> Any:
                return self._authorized_call(
                    authorization,
                    self.client.place_market_order,
                    SYMBOL,
                    side,
                    quantity=intent.quantity,
                    quote_qty=intent.quote_quantity,
                    client_order_id=intent.client_order_id,
                )

            if leg == 'entry':
                receipt = boundary.consume_and_call(
                    permit,
                    method=ORDER_METHOD,
                    path=ORDER_PATH,
                    body=body,
                    transport=transport,
                )
            else:
                if recovered is None:
                    raise EconomicGovernanceBlocked(
                        'recovered_contingency_permit_required'
                    )
                receipt = recovery.consume_and_call(
                    recovered,
                    method=ORDER_METHOD,
                    path=ORDER_PATH,
                    body=body,
                    transport=transport,
                )
            lineage['consume_status'] = 'consumed_transport_returned'
            lineage['consumed_at'] = self.clock()
        except EconomicGovernanceBlocked:
            lineage['consume_status'] = 'burned_without_provider_call'
            lineage['consumed_at'] = self.clock()
            return self._economic_block(
                state,
                leg=leg,
                reason='exact_last_mile_economic_binding_required',
                state_anchor_hash=state_anchor_hash,
            )
        except Exception:
            lineage['consume_status'] = 'burned_transport_ambiguous'
            lineage['consumed_at'] = self.clock()
            receipt = {
                'status': 'pending_reconciliation',
                'data_status': 'pending_reconciliation',
                'truth_status': 'no_data',
                'generated_values': False,
                'submitted': None,
                'reconciliation_required': True,
                'reason': 'submission_outcome_ambiguous',
                'clientOrderId': state[f'{leg}_client_order_id'],
            }
        return self._record_order_result(
            state, leg=leg, side=side, receipt=receipt, readback=False,
        )

    def _reconcile_leg(
        self,
        state: dict[str, Any],
        authorization: Mapping[str, Any],
        *,
        leg: str,
        side: str,
    ) -> dict[str, Any]:
        self._hydrate_pending(state, side=side, leg=leg)
        prior = state.get(f"{leg}_receipt")
        order_id = (
            _identifier(prior.get("orderId"))
            if isinstance(prior, Mapping) else None
        )
        try:
            receipt = self._authorized_call(
                authorization,
                self.client.get_order_status,
                order_id,
                state[f"{leg}_client_order_id"],
                symbol=SYMBOL,
                side=side,
                margin=False,
            )
        except Exception:
            receipt = {
                "status": "pending_reconciliation",
                "data_status": "pending_reconciliation",
                "truth_status": "no_data",
                "generated_values": False,
                "submitted": None,
                "reconciliation_required": True,
                "reason": "provider_readback_unavailable",
                "clientOrderId": state[f"{leg}_client_order_id"],
                "orderId": order_id,
            }
        return self._record_order_result(
            state, leg=leg, side=side, receipt=receipt, readback=True,
        )

    def _prepare_exit(
        self,
        state: dict[str, Any],
        authorization: Mapping[str, Any],
    ) -> dict[str, Any]:
        entry = state.get("entry_receipt")
        if not isinstance(entry, Mapping):
            return _no_action("complete_entry_receipt_required")
        now = self.clock()
        try:
            market_raw = self._authorized_call(
                authorization, self.client.get_ticker, SYMBOL,
            )
            account_raw = self._authorized_call(
                authorization, self.client.get_asset_balance, BASE_ASSET,
            )
            filters_raw = self._authorized_call(
                authorization,
                self.client.get_symbol_filters,
                SYMBOL,
                force_refresh=True,
            )
            fee_raw = self._authorized_call(
                authorization, self.client.get_trade_fee_receipt, SYMBOL,
            )
        except Exception:
            return _no_action(
                "fresh_containment_market_account_filter_fee_receipts_required"
            )
        market = _market_receipt(market_raw, now=now)
        account = _account_receipt(
            account_raw, now=now, asset=BASE_ASSET,
        )
        filters = _filter_receipt(filters_raw, now=now)
        fee_receipt = _trade_fee_receipt(fee_raw, now=now)
        if None in (market, account, filters, fee_receipt):
            return _no_action(
                "fresh_containment_market_account_filter_fee_receipts_required"
            )
        fee_policy = _fee_policy_receipt(
            authorization, filters, fee_receipt, now=now,
        )
        before_free = Decimal(str(
            state["pre_entry_base_account_receipt"]["free"]
        ))
        after_free = Decimal(str(account["free"]))
        observed_delta = after_free - before_free
        filled_qty = Decimal(str(entry["filled_qty"]))
        entry_fee = Decimal(str(entry["fee"]))
        expected_delta = (
            filled_qty - entry_fee
            if str(entry["fee_asset"]).upper() == BASE_ASSET
            else filled_qty
        )
        step = Decimal(str(filters["step_size"]))
        tolerance = max(step, Decimal("0.000000000001"))
        if (
            observed_delta <= 0 or expected_delta <= 0
            or abs(observed_delta - expected_delta) > tolerance
        ):
            state["stage"] = "containment_blocked"
            state["failure_reason"] = (
                "post_entry_btc_balance_delta_mismatch"
            )
            state["post_entry_base_account_receipt"] = account
            self._save(state)
            return _no_action(
                "post_entry_btc_balance_delta_mismatch",
                observed_delta=format(observed_delta, "f"),
                expected_delta=format(expected_delta, "f"),
            )
        try:
            adjusted = self._authorized_call(
                authorization,
                self.client.adjust_quantity,
                SYMBOL,
                format(observed_delta, "f"),
            )
            sell_quantity = _finite_decimal(adjusted, positive=True)
        except Exception:
            sell_quantity = None
        bid = Decimal(str(market["bid"]))
        min_notional = Decimal(str(filters["min_notional"]))
        min_qty = Decimal(str(filters["min_qty"]))
        if (
            sell_quantity is None or sell_quantity < min_qty
            or sell_quantity > observed_delta
            or observed_delta - sell_quantity > tolerance
            or sell_quantity * bid < min_notional
        ):
            state["stage"] = "containment_blocked"
            state["failure_reason"] = (
                "provider_filters_block_containment_exit"
            )
            self._save(state)
            return _no_action(
                "provider_filters_block_containment_exit"
            )
        action = _action_receipt(
            side="SELL", authorization=authorization,
            market=market, account=account, filters=filters,
            fee_receipt=fee_receipt, fee_policy=fee_policy,
            hnc=state["hnc_receipt"], auris=state["auris_receipt"],
            now=self.clock(), entry_receipt=entry, containment=True,
        )
        state.update({
            "stage": "exit_reserved",
            "sell_quantity": format(sell_quantity, "f"),
            "post_entry_base_account_receipt": account,
            "exit_market_receipt": market,
            "exit_filter_receipt": filters,
            "exit_fee_receipt": fee_receipt,
            "exit_fee_policy_receipt": fee_policy,
            "exit_action_receipt": action,
            "updated_at": self.clock(),
        })
        self._save(state)
        return {
            "status": "exit_prepared", "data_status": "live",
            "truth_status": "real_derived", "generated_values": False,
            "eligible_for_action": True, "economic_mutation": False,
            "stage": state["stage"],
            "sell_quantity": state["sell_quantity"],
            "action_receipt_id": action["receipt_id"],
            "cognitive_gate_required": True,
            'economic_dual_voice_required': True,
            'contingency_warrant_required': True,
            "state_path": str(self.state_path),
        }

    def _complete(
        self,
        state: dict[str, Any],
        authorization: Mapping[str, Any],
    ) -> dict[str, Any]:
        try:
            post_base_raw = self._authorized_call(
                authorization, self.client.get_asset_balance, BASE_ASSET,
            )
            post_quote_raw = self._authorized_call(
                authorization, self.client.get_asset_balance, QUOTE_ASSET,
            )
        except Exception:
            return _no_action(
                "fresh_post_exit_btc_and_usdt_balance_receipts_required"
            )
        observed_at = self.clock()
        post_base = _account_receipt(
            post_base_raw, now=observed_at, asset=BASE_ASSET,
        )
        post_quote = _account_receipt(
            post_quote_raw, now=observed_at, asset=QUOTE_ASSET,
        )
        if post_base is None or post_quote is None:
            return _no_action(
                "fresh_post_exit_btc_and_usdt_balance_receipts_required"
            )
        before_base = Decimal(str(
            state["pre_entry_base_account_receipt"]["free"]
        ))
        after_base = Decimal(str(post_base["free"]))
        step = Decimal(str(state["exit_filter_receipt"]["step_size"]))
        if abs(after_base - before_base) > step:
            state["stage"] = "containment_incomplete"
            state["post_exit_base_account_receipt"] = post_base
            state["post_exit_quote_account_receipt"] = post_quote
            state["failure_reason"] = (
                "post_exit_btc_balance_not_restored"
            )
            self._save(state)
            return _no_action(
                "post_exit_btc_balance_not_restored",
                before=format(before_base, "f"),
                after=format(after_base, "f"),
            )
        before_quote = Decimal(str(
            state["quote_account_receipt"]["free"]
        ))
        after_quote = Decimal(str(post_quote["free"]))
        observed_quote_delta = after_quote - before_quote
        entry_notional = Decimal(str(
            state["entry_receipt"]["filled_notional"]
        ))
        exit_notional = Decimal(str(
            state["exit_receipt"]["filled_notional"]
        ))
        entry_fee = Decimal(str(state["entry_receipt"]["fee"]))
        exit_fee = Decimal(str(state["exit_receipt"]["fee"]))
        entry_fee_asset = str(
            state["entry_receipt"]["fee_asset"]
        ).upper()
        exit_fee_asset = str(
            state["exit_receipt"]["fee_asset"]
        ).upper()
        quote_fee = Decimal(0)
        if entry_fee_asset == QUOTE_ASSET:
            quote_fee += entry_fee
        if exit_fee_asset == QUOTE_ASSET:
            quote_fee += exit_fee
        expected_quote_delta = (
            exit_notional - entry_notional - quote_fee
        )
        quote_precision = int(
            state["exit_filter_receipt"]["quote_precision"]
        )
        quote_tolerance = Decimal(1).scaleb(-quote_precision)
        if abs(observed_quote_delta - expected_quote_delta) > quote_tolerance:
            state["stage"] = "accounting_incomplete"
            state["post_exit_base_account_receipt"] = post_base
            state["post_exit_quote_account_receipt"] = post_quote
            state["failure_reason"] = (
                "post_exit_usdt_delta_does_not_match_terminal_receipts"
            )
            self._save(state)
            return _no_action(
                "post_exit_usdt_delta_does_not_match_terminal_receipts",
                observed_quote_delta=format(observed_quote_delta, "f"),
                expected_quote_delta=format(expected_quote_delta, "f"),
            )
        nonquote_fees = [
            {"leg": "entry", "amount": format(entry_fee, "f"),
             "asset": entry_fee_asset}
            for _ in [0] if entry_fee_asset != QUOTE_ASSET
        ] + [
            {"leg": "exit", "amount": format(exit_fee, "f"),
             "asset": exit_fee_asset}
            for _ in [0] if exit_fee_asset != QUOTE_ASSET
        ]
        quote_net_pnl = (
            format(expected_quote_delta, "f")
            if not nonquote_fees else None
        )
        inputs = [
            state["authorization"]["receipt_id"],
            state["entry_action_receipt"]["receipt_id"],
            state["entry_receipt"]["receipt_id"],
            state["exit_action_receipt"]["receipt_id"],
            state["exit_receipt"]["receipt_id"],
            post_base["receipt_id"], post_quote["receipt_id"],
        ]
        payload = {
            "intent_id": state["intent_id"], "symbol": SYMBOL,
            "entry_order_id": state["entry_receipt"]["orderId"],
            "entry_fee": format(entry_fee, "f"),
            "entry_fee_asset": entry_fee_asset,
            "exit_order_id": state["exit_receipt"]["orderId"],
            "exit_fee": format(exit_fee, "f"),
            "exit_fee_asset": exit_fee_asset,
            "observed_peak_quote_exposure": state.get(
                "observed_peak_quote_exposure"
            ),
            "post_exit_btc_delta": format(
                after_base - before_base, "f",
            ),
            "post_exit_usdt_delta": format(observed_quote_delta, "f"),
            "quote_net_pnl": quote_net_pnl,
            "quote_net_pnl_status": (
                "complete"
                if quote_net_pnl is not None
                else "no_data_nonquote_fee_conversion_receipt_required"
            ),
            "nonquote_fees": nonquote_fees,
            "cap_compliant": state.get("cap_breach_detected") is not True,
            "input_receipt_ids": inputs,
        }
        source_timestamp = max(
            float(state["entry_receipt"]["source_timestamp"]),
            float(state["exit_receipt"]["source_timestamp"]),
            float(post_base["source_timestamp"]),
            float(post_quote["source_timestamp"]),
        )
        recorded_at = self.clock()
        completion = {
            **payload, "status": "complete", "data_status": "live",
            "truth_status": "real_derived", "generated_values": False,
            "source_id": (
                "aureon:bounded-binance-roundtrip:completion:v1"
            ),
            "source_timestamp": source_timestamp,
            "received_at": recorded_at,
            "derived_at": recorded_at, "recorded_at": recorded_at,
            "receipt_id": _json_digest("binance_roundtrip", payload),
            "receipt_type": "bounded_live_roundtrip",
            "eligible_for_action": False,
            "eligible_for_accounting": True,
            "eligible_for_learning": True,
            "economic_mutation": False,
        }
        state["stage"] = "complete"
        state["post_exit_base_account_receipt"] = post_base
        state["post_exit_quote_account_receipt"] = post_quote
        state["completion_receipt"] = completion
        state["updated_at"] = self.clock()
        self._save(state)
        return {**completion, "state_path": str(self.state_path)}

    def advance(
        self,
        *,
        authorization_receipt: Any,
        confirmation_token: str,
    ) -> dict[str, Any]:
        if self.state_path.parent.name != "bounded_binance_roundtrip":
            return _no_action("private_hashed_cycle_state_path_required")
        try:
            with self._state_lock():
                return self._advance_locked(
                    authorization_receipt=authorization_receipt,
                    confirmation_token=confirmation_token,
                )
        except (OSError, BlockingIOError, StateIntegrityError) as exc:
            return _no_action(
                "durable_cycle_state_unavailable",
                state_error=type(exc).__name__,
            )

    def _advance_locked(
        self,
        *,
        authorization_receipt: Any,
        confirmation_token: str,
    ) -> dict[str, Any]:
        """Advance exactly one durable stage; never loop order operations."""
        state = self._load()
        if state is None:
            return _no_action("read_only_preflight_required")
        authorization, failure = self._authorization_for_state(
            state, authorization_receipt, confirmation_token,
        )
        if failure is not None:
            return failure
        stage = state.get("stage")
        if stage == "entry_reserved":
            if not _new_entry_window_open(self.clock(), authorization):
                return _no_action(
                    "new_entry_window_closed", stage=stage,
                )
            permission = _account_permission_receipt(
                state.get("account_permission_receipt"),
                now=self.clock(),
            )
            if permission is None:
                return _no_action(
                    "persisted_account_permission_receipt_required",
                    stage=stage,
                )
            action = _live_receipt(
                state.get("entry_action_receipt"),
                now=self.clock(),
                truth_statuses={"real_derived"},
            )
            if (
                action is None
                or action.get("eligible_for_action") is not True
                or action.get("side") != "BUY"
                or action.get("cognitive_gate_required") is not True
                or action.get("cognitive_gate_open") is not True
                or action.get('economic_dual_voice_required') is not True
                or action.get('contingency_warrant_required') is not False
            ):
                return _no_action("fresh_entry_action_receipt_required")
            permission_receipt_id = permission["receipt_id"]
            action_input_ids = action.get("input_receipt_ids")
            if (
                action.get("account_permission_receipt_id")
                != permission_receipt_id
                or not isinstance(action_input_ids, list)
                or [
                    str(value) for value in action_input_ids
                ].count(permission_receipt_id) != 1
            ):
                return _no_action(
                    "entry_action_must_link_account_permission_receipt"
                )
            return self._submit_leg(
                state, authorization, leg="entry", side="BUY",
                quote_qty=Decimal(str(state["entry_quote_order_qty"])),
            )
        if stage in {"entry_submitting", "entry_pending"}:
            return self._reconcile_leg(
                state, authorization, leg="entry", side="BUY",
            )
        if stage == "entry_filled":
            return self._prepare_exit(state, authorization)
        if stage == "exit_reserved":
            action = _live_receipt(
                state.get("exit_action_receipt"),
                now=self.clock(),
                truth_statuses={"real_derived"},
            )
            if (
                action is None
                or action.get("eligible_for_action") is not True
                or action.get("side") != "SELL"
                or action.get("containment_exit") is not True
                or action.get("cognitive_gate_required") is not True
                or action.get("cognitive_gate_open") is not True
                or action.get('economic_dual_voice_required') is not True
                or action.get('contingency_warrant_required') is not True
                or action.get("entry_receipt_id")
                != state["entry_receipt"]["receipt_id"]
            ):
                return _no_action(
                    "fresh_containment_action_receipt_required"
                )
            if (
                state["entry_receipt"]["receipt_id"]
                not in action.get("input_receipt_ids", [])
            ):
                return _no_action(
                    "containment_action_must_link_entry_receipt"
                )
            return self._submit_leg(
                state, authorization, leg="exit", side="SELL",
                quantity=Decimal(str(state["sell_quantity"])),
            )
        if stage in {"exit_submitting", "exit_pending"}:
            return self._reconcile_leg(
                state, authorization, leg="exit", side="SELL",
            )
        if stage == "exit_filled":
            return self._complete(state, authorization)
        if stage == "complete":
            return {
                **dict(state.get("completion_receipt") or {}),
                "status": "complete", "economic_mutation": False,
                "state_path": str(self.state_path),
            }
        return _no_action(
            "cycle_not_advanceable", stage=stage,
            state_path=str(self.state_path),
        )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inert interface for the bounded Binance round-trip runner."
        )
    )
    parser.add_argument("--inspect-state", type=Path)
    parser.add_argument("--state-path", type=Path)
    parser.add_argument("--confirmation-token")
    parser.add_argument("--max-quote")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if args.inspect_state:
        try:
            payload = _read_verified_state(args.inspect_state)
            if payload is None:
                payload = _no_action("state_unavailable")
        except (OSError, StateIntegrityError) as exc:
            payload = _no_action(
                "state_integrity_unavailable",
                state_error=type(exc).__name__,
            )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.execute:
        print(json.dumps(_no_action(
            "injected_client_and_evidence_suppliers_required",
            required={
                "state_path": bool(args.state_path),
                "confirmation_token": bool(args.confirmation_token),
                "max_quote_at_most_10": args.max_quote,
                "account_environment": "live_spot",
                "venue": VENUE,
                "symbol": SYMBOL,
            },
        ), indent=2, sort_keys=True))
        return 2
    print(json.dumps({
        "status": "inert", "provider_calls": 0, "order_calls": 0,
        "required_live_interface": [
            "injected BinanceClient",
            "explicit state_path",
            "fresh HNC receipt supplier",
            "fresh Auris receipt supplier",
            "exact operator authorization receipt",
            "exact confirmation token",
            "max_quote_notional <= 10 USDT including quote fee",
        ],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
