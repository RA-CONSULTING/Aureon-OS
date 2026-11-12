"""Canonical contracts for the isolated Google Cloud trading authority chain.

The contract carries no credentials and performs no network I/O.  A message is
accepted only when it is small, current, exactly shaped, and joined to the same
intent through every stage.  Live orders remain unavailable until every service
is deployed with an explicit release state; the probe path can never mutate an
exchange.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Mapping


INTENT_SCHEMA = "aureon.cloud-trade-intent.v1"
REVIEW_SCHEMA = "aureon.cloud-trade-review.v1"
DISPATCH_SCHEMA = "aureon.cloud-trade-dispatch.v1"
EXECUTOR_SCHEMA = "aureon.cloud-trade-executor-result.v1"
RECEIPT_SCHEMA = "aureon.cloud-trade-terminal-receipt.v1"
PROBE_KIND = "control_plane_probe"
ORDER_KIND = "order"
MAX_MESSAGE_BYTES = 65_536
MAX_INTENT_LIFETIME_MS = 60_000
MAX_CLOCK_SKEW_MS = 5_000
_HEX64 = re.compile(r"[0-9a-f]{64}")
_OPAQUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{7,127}")
_SYMBOL = re.compile(r"[A-Z0-9][A-Z0-9./_-]{1,31}")
_REVISION = re.compile(r"[0-9a-f]{40,64}")
_VENUES = {"alpaca", "binance", "capital", "kraken"}
_EXECUTION_BUDGET_QUOTES = {
    "alpaca": {"USD"},
    "binance": {"FDUSD", "USD", "USDC", "USDT"},
    "capital": {"USD"},
    "kraken": {"FDUSD", "USD", "USDC", "USDT"},
}
EXECUTION_BUDGET_SCHEMA = "aureon.cloud-trade-execution-budget-readiness.v1"
PROVIDER_READBACK_COMMITMENT_SCHEMA = "aureon.cloud-trade-provider-readback-commitment.v1"
READINESS_RELEASE_BINDING_SCHEMA = "aureon.cloud-trade-readiness-release-binding.v1"
PERIODIC_READINESS_SCHEMA = "aureon.cloud-trade-periodic-readiness.v1"
EXECUTOR_READINESS_SCHEMA = "aureon.cloud-trade-executor-readiness-attestation.v1"
RECEIPT_READINESS_SCHEMA = "aureon.cloud-trade-receipt-readiness-endorsement.v1"
MAX_EXECUTION_BUDGET_USD = 5.0
MAX_EXECUTION_BUDGET_AGE_MS = 300_000
MAX_PERIODIC_READINESS_AGE_MS = 300_000
_RELEASE_STATE_FIELDS = {
    "schema", "state", "generation", "request_id", "requested_controls_sha256",
    "authorization_event_sha256", "authorization_expires_at_ms",
    "probe_receipt_sha256", "provider_readback_sha256", "source_revision",
    "signed_at_ms", "controller_key_version", "signature", "update_time",
}
_CONTROL_KEYS = {
    "AUREON_DEPLOYMENT_HOLD",
    "AUREON_DISABLE_REAL_ORDERS",
    "AUREON_DISABLE_EXCHANGE_MUTATIONS",
    "AUREON_LIVE_TRADING",
    "AUREON_ORDER_INTENT_PUBLISH",
    "AUREON_UNIFIED_ORDER_EXECUTOR",
}


class ContractError(ValueError):
    """Stable fail-closed contract error."""


def canonical_bytes(value: Mapping[str, Any]) -> bytes:
    try:
        data = json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ContractError("message_not_canonical_json") from exc
    if not 0 < len(data) <= MAX_MESSAGE_BYTES:
        raise ContractError("message_size_invalid")
    return data


def digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def provider_readback_commitment_sha256(
    provider_accounts_sha256: Any,
    execution_budget_readiness_sha256: Any,
) -> str:
    """Join account authentication and threshold-budget evidence without balances."""

    accounts = _hex(provider_accounts_sha256, "provider_accounts_digest_invalid")
    readiness = _hex(
        execution_budget_readiness_sha256,
        "execution_budget_readiness_digest_invalid",
    )
    return digest({
        "schema": PROVIDER_READBACK_COMMITMENT_SCHEMA,
        "provider_accounts_sha256": accounts,
        "execution_budget_readiness_sha256": readiness,
    })


def controller_release_state_sha256(value: Any) -> str:
    """Commit the exact controller-signed state, excluding Firestore metadata."""

    row = _exact(value, _RELEASE_STATE_FIELDS, "release_state_shape_invalid")
    if (
        row["schema"] != "aureon.cloud-trade-release-state.v1"
        or row["state"] not in {"active", "held"}
        or type(row["generation"]) is not int
        or row["generation"] < 1
        or any(not _HEX64.fullmatch(str(row[key] or "")) for key in (
            "request_id", "requested_controls_sha256", "authorization_event_sha256",
            "probe_receipt_sha256", "provider_readback_sha256",
        ))
        or type(row["authorization_expires_at_ms"]) is not int
        or type(row["signed_at_ms"]) is not int
        or _REVISION.fullmatch(str(row["source_revision"] or "")) is None
        or not isinstance(row["controller_key_version"], str)
        or not row["controller_key_version"].endswith("/cryptoKeyVersions/1")
        or not isinstance(row["signature"], str)
        or not 1 <= len(row["signature"]) <= 1024
        or not isinstance(row["update_time"], str)
    ):
        raise ContractError("release_state_invalid")
    return digest({key: row[key] for key in _RELEASE_STATE_FIELDS - {"update_time"}})


def build_readiness_release_binding(value: Any) -> dict[str, Any]:
    """Build the non-authoritative reference a periodic probe must carry."""

    row = _exact(value, _RELEASE_STATE_FIELDS, "release_state_shape_invalid")
    state_sha256 = controller_release_state_sha256(row)
    if row["state"] != "active":
        raise ContractError("periodic_readiness_requires_active_release")
    binding = {
        "schema": READINESS_RELEASE_BINDING_SCHEMA,
        "generation": row["generation"],
        "request_id": row["request_id"],
        "release_state_sha256": state_sha256,
        "authorization_event_sha256": row["authorization_event_sha256"],
        "authorization_expires_at_ms": row["authorization_expires_at_ms"],
        "source_revision": row["source_revision"],
    }
    return validate_readiness_release_binding(binding)


def validate_readiness_release_binding(value: Any) -> dict[str, Any]:
    row = _exact(value, {
        "schema", "generation", "request_id", "release_state_sha256",
        "authorization_event_sha256", "authorization_expires_at_ms",
        "source_revision",
    }, "readiness_release_binding_shape_invalid")
    if (
        row["schema"] != READINESS_RELEASE_BINDING_SCHEMA
        or type(row["generation"]) is not int
        or row["generation"] < 1
        or any(not _HEX64.fullmatch(str(row[key] or "")) for key in (
            "request_id", "release_state_sha256", "authorization_event_sha256",
        ))
        or type(row["authorization_expires_at_ms"]) is not int
        or row["authorization_expires_at_ms"] <= 0
        or _REVISION.fullmatch(str(row["source_revision"] or "")) is None
    ):
        raise ContractError("readiness_release_binding_invalid")
    return row


def periodic_readiness_probe(value: Mapping[str, Any]) -> bool:
    authorization = value.get("authorization") if isinstance(value, Mapping) else None
    return isinstance(authorization, Mapping) and "readiness_release" in authorization


def build_periodic_readiness_statement(
    intent: Mapping[str, Any],
    provider_readback: Any,
    capabilities: Any,
    *,
    now_ms: int,
) -> dict[str, Any]:
    """Reduce a read-only provider probe to a signed, balance-free statement."""

    if not periodic_readiness_probe(intent):
        raise ContractError("periodic_readiness_release_binding_missing")
    authorization = intent["authorization"]
    binding = validate_readiness_release_binding(authorization["readiness_release"])
    if (
        binding["source_revision"] != intent.get("source_revision")
        or binding["authorization_event_sha256"] != authorization.get("event_sha256")
        or binding["authorization_expires_at_ms"] != authorization.get("expires_at_ms")
    ):
        raise ContractError("periodic_readiness_release_binding_mismatch")
    provider = validate_provider_probe_readback(
        provider_readback,
        source_revision=binding["source_revision"],
        now_ms=now_ms,
    )
    required_capabilities = {
        "live_execution_release", "durable_budget_ledger", "order_adapter_ready",
        "live_result_binding_ready", "instrument_preflight_enforced",
    }
    if (
        not isinstance(capabilities, Mapping)
        or set(capabilities) != required_capabilities
        or any(capabilities[key] is not True for key in required_capabilities)
    ):
        raise ContractError("periodic_readiness_capabilities_invalid")
    readiness = provider["execution_budget_readiness"]
    observed_at_ms = readiness["observed_at_ms"]
    expires_at_ms = min(
        observed_at_ms + MAX_PERIODIC_READINESS_AGE_MS,
        binding["authorization_expires_at_ms"],
    )
    if expires_at_ms <= now_ms:
        raise ContractError("periodic_readiness_expired")
    providers = {
        venue: {
            "authenticated": True,
            "account_binding_sha256": provider["providers"][venue]["account_binding_sha256"],
        }
        for venue in sorted(_VENUES)
    }
    statement = {
        "schema": PERIODIC_READINESS_SCHEMA,
        "source_revision": binding["source_revision"],
        "release_generation": binding["generation"],
        "release_request_id": binding["request_id"],
        "release_state_sha256": binding["release_state_sha256"],
        "authorization_event_sha256": binding["authorization_event_sha256"],
        "authorization_expires_at_ms": binding["authorization_expires_at_ms"],
        "provider_accounts": providers,
        "provider_accounts_sha256": provider["provider_accounts_sha256"],
        "provider_readback_sha256": provider["readback_sha256"],
        "execution_budget_readiness": readiness,
        "execution_budget_readiness_sha256": provider["execution_budget_readiness_sha256"],
        "maximum_order_usd": readiness["maximum_order_usd"],
        "provider_count": 4,
        "all_authenticated": True,
        "provider_mutation_attempted": False,
        "orders_attempted": 0,
        "orders_submitted": 0,
        "observed_at_ms": observed_at_ms,
        "expires_at_ms": expires_at_ms,
    }
    return validate_periodic_readiness_statement(statement, now_ms=now_ms)


def validate_periodic_readiness_statement(
    value: Any,
    *,
    now_ms: int | None = None,
) -> dict[str, Any]:
    row = _exact(value, {
        "schema", "source_revision", "release_generation", "release_request_id",
        "release_state_sha256", "authorization_event_sha256",
        "authorization_expires_at_ms", "provider_accounts",
        "provider_accounts_sha256", "provider_readback_sha256",
        "execution_budget_readiness", "execution_budget_readiness_sha256",
        "maximum_order_usd", "provider_count", "all_authenticated",
        "provider_mutation_attempted", "orders_attempted", "orders_submitted",
        "observed_at_ms", "expires_at_ms",
    }, "periodic_readiness_shape_invalid")
    if (
        row["schema"] != PERIODIC_READINESS_SCHEMA
        or _REVISION.fullmatch(str(row["source_revision"] or "")) is None
        or type(row["release_generation"]) is not int
        or row["release_generation"] < 1
        or any(not _HEX64.fullmatch(str(row[key] or "")) for key in (
            "release_request_id", "release_state_sha256", "authorization_event_sha256",
            "provider_accounts_sha256", "provider_readback_sha256",
            "execution_budget_readiness_sha256",
        ))
        or any(type(row[key]) is not int for key in (
            "authorization_expires_at_ms", "provider_count", "orders_attempted",
            "orders_submitted", "observed_at_ms", "expires_at_ms",
        ))
        or row["provider_count"] != 4
        or row["all_authenticated"] is not True
        or row["provider_mutation_attempted"] is not False
        or row["orders_attempted"] != 0
        or row["orders_submitted"] != 0
        or row["authorization_expires_at_ms"] < row["expires_at_ms"]
        or row["expires_at_ms"] != min(
            row["observed_at_ms"] + MAX_PERIODIC_READINESS_AGE_MS,
            row["authorization_expires_at_ms"],
        )
    ):
        raise ContractError("periodic_readiness_invalid")
    providers = row["provider_accounts"]
    if not isinstance(providers, Mapping) or set(providers) != _VENUES:
        raise ContractError("periodic_readiness_provider_accounts_invalid")
    normalized_providers: dict[str, Any] = {}
    for venue in sorted(_VENUES):
        provider = _exact(
            providers[venue], {"authenticated", "account_binding_sha256"},
            "periodic_readiness_provider_account_shape_invalid",
        )
        if (
            provider["authenticated"] is not True
            or _HEX64.fullmatch(str(provider["account_binding_sha256"] or "")) is None
        ):
            raise ContractError("periodic_readiness_provider_account_invalid")
        normalized_providers[venue] = provider
    expected_provider_rows = {
        venue: {
            "venue": venue,
            "authenticated": True,
            "account_binding_sha256": normalized_providers[venue]["account_binding_sha256"],
        }
        for venue in sorted(_VENUES)
    }
    if row["provider_accounts_sha256"] != digest(expected_provider_rows):
        raise ContractError("periodic_readiness_provider_accounts_digest_mismatch")
    readiness = validate_execution_budget_readiness(
        row["execution_budget_readiness"],
        source_revision=row["source_revision"],
        now_ms=now_ms,
    )
    if (
        row["execution_budget_readiness_sha256"] != digest(readiness)
        or row["provider_readback_sha256"] != provider_readback_commitment_sha256(
            row["provider_accounts_sha256"], row["execution_budget_readiness_sha256"],
        )
        or row["maximum_order_usd"] != readiness["maximum_order_usd"]
        or float(row["maximum_order_usd"]) > MAX_EXECUTION_BUDGET_USD
        or row["observed_at_ms"] != readiness["observed_at_ms"]
    ):
        raise ContractError("periodic_readiness_commitment_mismatch")
    if now_ms is not None:
        current = _uint(now_ms, "periodic_readiness_time_invalid")
        if not -MAX_CLOCK_SKEW_MS <= current - row["observed_at_ms"] or current >= row["expires_at_ms"]:
            raise ContractError("periodic_readiness_stale")
    result = dict(row)
    result["provider_accounts"] = normalized_providers
    result["execution_budget_readiness"] = readiness
    canonical_bytes(result)
    return result


def validate_readiness_envelope(
    value: Any,
    *,
    role: str,
    now_ms: int | None = None,
    executor_attestation_sha256: str | None = None,
) -> dict[str, Any]:
    if role == "executor":
        row = _exact(value, {
            "schema", "statement", "statement_sha256", "authority_id",
            "key_version", "signed_at_ms", "signature",
        }, "executor_readiness_attestation_shape_invalid")
        statement = validate_periodic_readiness_statement(row["statement"], now_ms=now_ms)
        if (
            row["schema"] != EXECUTOR_READINESS_SCHEMA
            or row["authority_id"] != "gcp:aureon-trade-executor"
            or "/cryptoKeys/aureon-executor-signing/" not in str(row["key_version"])
            or row["statement_sha256"] != digest(statement)
            or type(row["signed_at_ms"]) is not int
            or not statement["observed_at_ms"] <= row["signed_at_ms"] <= statement["expires_at_ms"]
            or not isinstance(row["signature"], str)
            or not 40 <= len(row["signature"]) <= 1024
        ):
            raise ContractError("executor_readiness_attestation_invalid")
        return row
    if role != "receipt":
        raise ContractError("readiness_envelope_role_invalid")
    row = _exact(value, {
        "schema", "executor_attestation_sha256", "statement_sha256",
        "source_revision", "release_generation", "release_state_sha256",
        "authorization_event_sha256", "authorization_expires_at_ms",
        "observed_at_ms", "expires_at_ms", "authority_id", "key_version",
        "signed_at_ms", "signature",
    }, "receipt_readiness_endorsement_shape_invalid")
    if (
        row["schema"] != RECEIPT_READINESS_SCHEMA
        or not _HEX64.fullmatch(str(row["executor_attestation_sha256"] or ""))
        or executor_attestation_sha256 is not None
        and row["executor_attestation_sha256"] != executor_attestation_sha256
        or not _HEX64.fullmatch(str(row["statement_sha256"] or ""))
        or _REVISION.fullmatch(str(row["source_revision"] or "")) is None
        or type(row["release_generation"]) is not int
        or row["release_generation"] < 1
        or not _HEX64.fullmatch(str(row["release_state_sha256"] or ""))
        or not _HEX64.fullmatch(str(row["authorization_event_sha256"] or ""))
        or any(type(row[key]) is not int for key in (
            "authorization_expires_at_ms", "observed_at_ms", "expires_at_ms", "signed_at_ms",
        ))
        or not row["observed_at_ms"] <= row["signed_at_ms"] <= row["expires_at_ms"]
        or row["authorization_expires_at_ms"] < row["expires_at_ms"]
        or row["authority_id"] != "gcp:aureon-trade-receipt"
        or "/cryptoKeys/aureon-receipt-signing/" not in str(row["key_version"])
        or not isinstance(row["signature"], str)
        or not 40 <= len(row["signature"]) <= 1024
    ):
        raise ContractError("receipt_readiness_endorsement_invalid")
    if now_ms is not None and int(now_ms) >= row["expires_at_ms"]:
        raise ContractError("receipt_readiness_endorsement_stale")
    canonical_bytes(row)
    return row


def unsigned_readiness_envelope(value: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(value)
    result.pop("signature", None)
    return result


def validate_execution_budget_readiness(
    value: Any,
    *,
    source_revision: str,
    now_ms: int | None = None,
) -> dict[str, Any]:
    """Validate a source-bound, threshold-only execution budget attestation.

    Each quote allowance is deliberately binary: zero or the configured order
    cap.  The object therefore proves whether one capped order was fundable at
    observation time without disclosing a provider balance.
    """

    if not isinstance(source_revision, str) or _REVISION.fullmatch(source_revision) is None:
        raise ContractError("source_revision_invalid")
    row = _exact(value, {
        "schema", "source_revision", "observed_at_ms", "maximum_order_usd", "venues",
    }, "execution_budget_readiness_shape_invalid")
    if row["schema"] != EXECUTION_BUDGET_SCHEMA or row["source_revision"] != source_revision:
        raise ContractError("execution_budget_readiness_revision_mismatch")
    observed = _uint(row["observed_at_ms"], "execution_budget_readiness_time_invalid")
    if observed <= 0:
        raise ContractError("execution_budget_readiness_time_invalid")
    if now_ms is not None:
        current = _uint(now_ms, "execution_budget_readiness_time_invalid")
        if current <= 0 or not -MAX_CLOCK_SKEW_MS <= current - observed <= MAX_EXECUTION_BUDGET_AGE_MS:
            raise ContractError("execution_budget_readiness_stale")
    maximum = row["maximum_order_usd"]
    if not isinstance(maximum, str) or not 1 <= len(maximum) <= 32:
        raise ContractError("execution_budget_maximum_invalid")
    try:
        maximum_number = float(maximum)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ContractError("execution_budget_maximum_invalid") from exc
    if (
        not math.isfinite(maximum_number)
        or not 0 < maximum_number <= MAX_EXECUTION_BUDGET_USD
        or format(maximum_number, ".12f").rstrip("0").rstrip(".") != maximum
    ):
        raise ContractError("execution_budget_maximum_invalid")
    venues = row["venues"]
    if not isinstance(venues, Mapping) or set(venues) != _VENUES:
        raise ContractError("execution_budget_venues_invalid")
    normalized_venues: dict[str, Any] = {}
    for venue in sorted(_VENUES):
        venue_row = _exact(
            venues[venue], {"authenticated", "quotes"},
            "execution_budget_venue_shape_invalid",
        )
        if venue_row["authenticated"] is not True:
            raise ContractError("execution_budget_provider_not_authenticated")
        quotes = venue_row["quotes"]
        if not isinstance(quotes, Mapping) or set(quotes) != _EXECUTION_BUDGET_QUOTES[venue]:
            raise ContractError("execution_budget_quotes_invalid")
        normalized_quotes: dict[str, Any] = {}
        for asset in sorted(_EXECUTION_BUDGET_QUOTES[venue]):
            quote = _exact(
                quotes[asset], {"status", "allowance_usd"},
                "execution_budget_quote_shape_invalid",
            )
            if quote["status"] not in {"sufficient", "insufficient", "unavailable"}:
                raise ContractError("execution_budget_quote_status_invalid")
            allowance = quote["allowance_usd"]
            if allowance not in {"0", maximum}:
                raise ContractError("execution_budget_allowance_invalid")
            sufficient = quote["status"] == "sufficient"
            if sufficient != (allowance == maximum):
                raise ContractError("execution_budget_allowance_status_mismatch")
            normalized_quotes[asset] = dict(quote)
        normalized_venues[venue] = {
            "authenticated": True,
            "quotes": normalized_quotes,
        }
    result = {
        "schema": EXECUTION_BUDGET_SCHEMA,
        "source_revision": source_revision,
        "observed_at_ms": observed,
        "maximum_order_usd": maximum,
        "venues": normalized_venues,
    }
    canonical_bytes(result)
    return result


def validate_provider_probe_readback(
    value: Any,
    *,
    source_revision: str,
    now_ms: int | None = None,
) -> dict[str, Any]:
    """Validate the executor's credential-free four-provider probe result."""

    row = _exact(value, {
        "schema", "providers", "provider_count", "all_authenticated",
        "provider_mutation_attempted", "instrument_preflight_enforced",
        "provider_accounts_sha256", "execution_budget_readiness",
        "execution_budget_readiness_sha256", "readback_sha256",
    }, "provider_probe_readback_shape_invalid")
    providers = row["providers"]
    if (
        row["schema"] != "aureon.cloud-trade-provider-readback.v1"
        or row["provider_count"] != 4
        or row["all_authenticated"] is not True
        or row["provider_mutation_attempted"] is not False
        or row["instrument_preflight_enforced"] is not True
        or not isinstance(providers, Mapping)
        or set(providers) != _VENUES
    ):
        raise ContractError("provider_probe_readback_invalid")
    normalized_providers: dict[str, Any] = {}
    for venue in sorted(_VENUES):
        provider = _exact(
            providers[venue], {"venue", "authenticated", "account_binding_sha256"},
            "provider_probe_account_shape_invalid",
        )
        if (
            provider["venue"] != venue
            or provider["authenticated"] is not True
            or _HEX64.fullmatch(str(provider["account_binding_sha256"] or "")) is None
        ):
            raise ContractError("provider_probe_account_invalid")
        normalized_providers[venue] = dict(provider)
    accounts_sha256 = _hex(row["provider_accounts_sha256"], "provider_accounts_digest_invalid")
    if accounts_sha256 != digest(normalized_providers):
        raise ContractError("provider_accounts_digest_mismatch")
    readiness = validate_execution_budget_readiness(
        row["execution_budget_readiness"],
        source_revision=source_revision,
        now_ms=now_ms,
    )
    readiness_sha256 = _hex(
        row["execution_budget_readiness_sha256"],
        "execution_budget_readiness_digest_invalid",
    )
    if readiness_sha256 != digest(readiness):
        raise ContractError("execution_budget_readiness_digest_mismatch")
    readback_sha256 = _hex(row["readback_sha256"], "provider_readback_digest_invalid")
    if readback_sha256 != provider_readback_commitment_sha256(
        accounts_sha256, readiness_sha256,
    ):
        raise ContractError("provider_readback_digest_mismatch")
    return {
        "schema": row["schema"],
        "providers": normalized_providers,
        "provider_count": 4,
        "all_authenticated": True,
        "provider_mutation_attempted": False,
        "instrument_preflight_enforced": True,
        "provider_accounts_sha256": accounts_sha256,
        "execution_budget_readiness": readiness,
        "execution_budget_readiness_sha256": readiness_sha256,
        "readback_sha256": readback_sha256,
    }


def probe_runtime_measurement(source_revision: str) -> dict[str, Any]:
    """Return the exact held-runtime measurement committed by a probe intent."""

    if not isinstance(source_revision, str) or _REVISION.fullmatch(source_revision) is None:
        raise ContractError("source_revision_invalid")
    return {
        "schema": "aureon.cloud-trade-probe-runtime-measurement.v1",
        "source_revision": source_revision,
        "requested_controls": {
            "AUREON_DEPLOYMENT_HOLD": True,
            "AUREON_DISABLE_REAL_ORDERS": True,
            "AUREON_DISABLE_EXCHANGE_MUTATIONS": True,
            "AUREON_LIVE_TRADING": False,
            "AUREON_ORDER_INTENT_PUBLISH": False,
            "AUREON_UNIFIED_ORDER_EXECUTOR": False,
        },
    }


def probe_runtime_measurement_sha256(source_revision: str) -> str:
    return digest(probe_runtime_measurement(source_revision))


def _exact(value: Any, keys: set[str], code: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ContractError(code)
    return dict(value)


def _hex(value: Any, code: str) -> str:
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise ContractError(code)
    return value


def _opaque(value: Any, code: str) -> str:
    if not isinstance(value, str) or not _OPAQUE.fullmatch(value):
        raise ContractError(code)
    return value


def _uint(value: Any, code: str) -> int:
    if type(value) is not int or value < 0:
        raise ContractError(code)
    return value


def _number(value: Any, code: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(code)
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ContractError(code) from exc
    if not math.isfinite(result) or result < 0 or (positive and result <= 0):
        raise ContractError(code)
    return result


def validate_controls(value: Any, *, live: bool) -> dict[str, bool]:
    controls = _exact(value, _CONTROL_KEYS, "control_shape_invalid")
    if any(type(item) is not bool for item in controls.values()):
        raise ContractError("control_value_invalid")
    if live:
        required = {
            "AUREON_DEPLOYMENT_HOLD": False,
            "AUREON_DISABLE_REAL_ORDERS": False,
            "AUREON_DISABLE_EXCHANGE_MUTATIONS": False,
            "AUREON_LIVE_TRADING": True,
            "AUREON_ORDER_INTENT_PUBLISH": True,
            "AUREON_UNIFIED_ORDER_EXECUTOR": True,
        }
        if controls != required:
            raise ContractError("live_control_state_not_armed")
    else:
        if controls["AUREON_DEPLOYMENT_HOLD"] is not True:
            raise ContractError("probe_requires_deployment_hold")
        if controls["AUREON_DISABLE_REAL_ORDERS"] is not True:
            raise ContractError("probe_requires_real_orders_disabled")
        if controls["AUREON_DISABLE_EXCHANGE_MUTATIONS"] is not True:
            raise ContractError("probe_requires_exchange_mutations_disabled")
        if controls["AUREON_LIVE_TRADING"] is not False:
            raise ContractError("probe_requires_live_trading_disabled")
    return controls


def validate_order(value: Any, *, max_order_usd: float) -> dict[str, Any]:
    order = _exact(value, {
        "venue", "symbol", "side", "order_type", "quantity", "quote_value_usd",
        "limit_price", "client_order_id",
    }, "order_shape_invalid")
    venue = order["venue"]
    if venue not in _VENUES:
        raise ContractError("order_venue_invalid")
    if not isinstance(order["symbol"], str) or not _SYMBOL.fullmatch(order["symbol"]):
        raise ContractError("order_symbol_invalid")
    if order["side"] not in {"BUY", "SELL"}:
        raise ContractError("order_side_invalid")
    if order["order_type"] not in {"MARKET", "LIMIT"}:
        raise ContractError("order_type_invalid")
    quantity = _number(order["quantity"], "order_quantity_invalid", positive=True)
    quote = _number(order["quote_value_usd"], "order_quote_value_invalid", positive=True)
    if quote > max_order_usd:
        raise ContractError("order_budget_exceeded")
    limit_price = order["limit_price"]
    if order["order_type"] == "LIMIT":
        _number(limit_price, "order_limit_price_invalid", positive=True)
    elif limit_price is not None:
        raise ContractError("market_order_limit_price_forbidden")
    _opaque(order["client_order_id"], "client_order_id_invalid")
    return {**order, "quantity": quantity, "quote_value_usd": quote}


def validate_intent(value: Any, *, now_ms: int, max_order_usd: float,
                    live_release: bool) -> dict[str, Any]:
    intent = _exact(value, {
        "schema", "intent_id", "kind", "tenant_commitment", "account_scope",
        "created_at_ms", "expires_at_ms", "authorization", "requested_controls",
        "market_evidence_sha256", "runtime_measurement_sha256", "source_revision",
        "order", "dry_run",
    }, "intent_shape_invalid")
    if intent["schema"] != INTENT_SCHEMA:
        raise ContractError("intent_schema_invalid")
    _hex(intent["intent_id"], "intent_id_invalid")
    _hex(intent["tenant_commitment"], "tenant_commitment_invalid")
    if intent["account_scope"] != "owner":
        raise ContractError("account_scope_invalid")
    created = _uint(intent["created_at_ms"], "intent_created_at_invalid")
    expires = _uint(intent["expires_at_ms"], "intent_expires_at_invalid")
    if (expires <= created or expires - created > MAX_INTENT_LIFETIME_MS
            or created > now_ms + MAX_CLOCK_SKEW_MS or expires < now_ms):
        raise ContractError("intent_time_invalid")
    authorization_value = intent["authorization"]
    authorization_keys = {
        "active", "expires_at_ms", "event_sha256", "scope_sha256",
        "release_authority", "mutation_authority",
    }
    if isinstance(authorization_value, Mapping) and "readiness_release" in authorization_value:
        authorization_keys.add("readiness_release")
    authorization = _exact(
        authorization_value, authorization_keys, "authorization_shape_invalid",
    )
    if authorization["active"] is not True:
        raise ContractError("operator_authorization_inactive")
    lease_expires = _uint(authorization["expires_at_ms"], "authorization_expiry_invalid")
    if lease_expires < expires:
        raise ContractError("operator_authorization_expires_before_intent")
    _hex(authorization["event_sha256"], "authorization_event_invalid")
    _hex(authorization["scope_sha256"], "authorization_scope_invalid")
    if authorization["release_authority"] is not False or authorization["mutation_authority"] is not False:
        raise ContractError("operator_lease_claims_forbidden_authority")
    _hex(intent["market_evidence_sha256"], "market_evidence_invalid")
    _hex(intent["runtime_measurement_sha256"], "runtime_measurement_invalid")
    if (not isinstance(intent["source_revision"], str)
            or _REVISION.fullmatch(intent["source_revision"]) is None):
        raise ContractError("source_revision_invalid")
    kind = intent["kind"]
    dry_run = intent["dry_run"]
    if type(dry_run) is not bool or kind not in {PROBE_KIND, ORDER_KIND}:
        raise ContractError("intent_kind_or_mode_invalid")
    if kind == PROBE_KIND:
        if dry_run is not True or intent["order"] is not None:
            raise ContractError("probe_must_be_non_mutating")
        validate_controls(intent["requested_controls"], live=False)
        if intent["runtime_measurement_sha256"] != probe_runtime_measurement_sha256(
                intent["source_revision"]):
            raise ContractError("probe_runtime_measurement_revision_mismatch")
        if "readiness_release" in authorization:
            binding = validate_readiness_release_binding(authorization["readiness_release"])
            if (
                binding["source_revision"] != intent["source_revision"]
                or binding["authorization_event_sha256"] != authorization["event_sha256"]
                or binding["authorization_expires_at_ms"] != authorization["expires_at_ms"]
            ):
                raise ContractError("periodic_readiness_release_binding_mismatch")
    else:
        if "readiness_release" in authorization:
            raise ContractError("order_readiness_release_binding_forbidden")
        if dry_run is True:
            raise ContractError("order_dry_run_kind_invalid")
        if live_release is not True:
            raise ContractError("live_execution_release_held")
        validate_controls(intent["requested_controls"], live=True)
        validate_order(intent["order"], max_order_usd=max_order_usd)
    canonical_bytes(intent)
    return intent


def validate_stage(value: Any, *, schema: str, payload_key: str,
                   prior_digest: str | None = None) -> dict[str, Any]:
    stage = _exact(value, {
        "schema", "stage_id", "intent_id", "prior_sha256", payload_key,
        "authority_id", "key_version", "signed_at_ms", "signature",
    }, "stage_shape_invalid")
    if stage["schema"] != schema:
        raise ContractError("stage_schema_invalid")
    _hex(stage["stage_id"], "stage_id_invalid")
    _hex(stage["intent_id"], "stage_intent_id_invalid")
    actual_prior = _hex(stage["prior_sha256"], "stage_prior_digest_invalid")
    if prior_digest is not None and actual_prior != prior_digest:
        raise ContractError("stage_prior_join_invalid")
    _opaque(stage["authority_id"], "stage_authority_invalid")
    if not isinstance(stage["key_version"], str) or not stage["key_version"].endswith("/cryptoKeyVersions/1"):
        raise ContractError("stage_key_version_invalid")
    _uint(stage["signed_at_ms"], "stage_signed_at_invalid")
    if not isinstance(stage["signature"], str) or not 40 <= len(stage["signature"]) <= 1024:
        raise ContractError("stage_signature_invalid")
    canonical_bytes(stage)
    return stage


def unsigned_stage(stage: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(stage)
    result.pop("signature", None)
    return result


__all__ = [
    "ContractError", "DISPATCH_SCHEMA", "EXECUTOR_READINESS_SCHEMA",
    "EXECUTOR_SCHEMA", "INTENT_SCHEMA", "MAX_EXECUTION_BUDGET_AGE_MS",
    "MAX_EXECUTION_BUDGET_USD", "MAX_MESSAGE_BYTES",
    "MAX_PERIODIC_READINESS_AGE_MS", "ORDER_KIND", "PERIODIC_READINESS_SCHEMA",
    "PROBE_KIND", "READINESS_RELEASE_BINDING_SCHEMA", "RECEIPT_READINESS_SCHEMA",
    "RECEIPT_SCHEMA", "REVIEW_SCHEMA", "build_periodic_readiness_statement",
    "build_readiness_release_binding", "canonical_bytes",
    "controller_release_state_sha256", "digest", "periodic_readiness_probe",
    "probe_runtime_measurement", "probe_runtime_measurement_sha256",
    "unsigned_readiness_envelope", "unsigned_stage", "validate_controls",
    "validate_execution_budget_readiness", "validate_intent", "validate_order",
    "validate_periodic_readiness_statement", "validate_provider_probe_readback",
    "validate_readiness_envelope", "validate_readiness_release_binding",
    "validate_stage",
]
