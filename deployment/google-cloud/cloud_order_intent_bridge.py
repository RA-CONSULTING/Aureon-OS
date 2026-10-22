"""Fail-closed owner order-intent bridge for the isolated cloud executor.

The bridge has one narrow authority: while the controller-signed release is
active, turn one fresh, strongly evidenced Unified Market Trader candidate into
the canonical ``aureon.cloud-trade-intent.v1`` message accepted by the private
Google Cloud authority chain.  It never loads exchange credentials and never
calls an exchange.  The Unified Market Trader's own publisher and executor must
remain held, which leaves the isolated cloud executor as the only mutation
boundary.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import math
import os
import re
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


ROOT = Path(__file__).resolve().parent
CONTRACT_ROOT = ROOT / "trading-control"
UPSTREAM_ROOT = ROOT.parents[1] / "aureon-os-upstream"
if str(UPSTREAM_ROOT) not in sys.path:
    sys.path.insert(0, str(UPSTREAM_ROOT))
if str(CONTRACT_ROOT) not in sys.path:
    sys.path.insert(0, str(CONTRACT_ROOT))

from contract import (  # noqa: E402
    ContractError,
    INTENT_SCHEMA,
    canonical_bytes,
    build_readiness_release_binding,
    controller_release_state_sha256,
    digest,
    unsigned_readiness_envelope,
    validate_execution_budget_readiness,
    validate_intent,
)
from cloud_state import (  # noqa: E402
    CloudStateError,
    validate_periodic_readiness_document,
)
from vm_workload_identity import (  # noqa: E402
    WorkloadIdentityError,
    broker_token,
)

from aureon.operator.authorization_lease import (  # noqa: E402
    MAX_LEASE_SECONDS,
    TRADING_CONTROL_SCOPE,
    build_operator_authorization_receipt,
)
from aureon.operator.cloud_trading_release import (  # noqa: E402
    CONTROLLER_KEY,
    LIVE_CONTROLS,
    read_controller_release,
)


PROJECT = "aureon-trading"
TOPIC = "aureon-trade-intents-v1"
TOPIC_RESOURCE = f"projects/{PROJECT}/topics/{TOPIC}"
PUBLISH_URL = f"https://pubsub.googleapis.com/v1/{TOPIC_RESOURCE}:publish"
METADATA_URL = (
    "http://metadata.google.internal/computeMetadata/v1/"
    "instance/service-accounts/default/token"
)
FIRESTORE_RELEASE_URL = (
    f"https://firestore.googleapis.com/v1/projects/{PROJECT}/databases/(default)/"
    "documents/aureon_trade_release/current"
)
FIRESTORE_READINESS_URL = (
    f"https://firestore.googleapis.com/v1/projects/{PROJECT}/databases/(default)/"
    "documents/aureon_trade_attestations/current_readiness"
)
KMS_PUBLIC_KEY_URL = "https://cloudkms.googleapis.com/v1/" + CONTROLLER_KEY + "/publicKey"
EXECUTOR_KEY = (
    "projects/aureon-trading/locations/europe-west1/keyRings/aureon-trading-prod/"
    "cryptoKeys/aureon-executor-signing/cryptoKeyVersions/1"
)
RECEIPT_KEY = (
    "projects/aureon-trading/locations/europe-west1/keyRings/aureon-trading-prod/"
    "cryptoKeys/aureon-receipt-signing/cryptoKeyVersions/1"
)
EXECUTOR_PUBLIC_KEY_URL = "https://cloudkms.googleapis.com/v1/" + EXECUTOR_KEY + "/publicKey"
RECEIPT_PUBLIC_KEY_URL = "https://cloudkms.googleapis.com/v1/" + RECEIPT_KEY + "/publicKey"

STATUS_SCHEMA = "aureon.cloud-order-intent-bridge-status.v1"
STATE_SCHEMA = "aureon.cloud-order-intent-bridge-state.v1"
EVIDENCE_SCHEMA = "aureon.owner-order-candidate-evidence.v2"
DEFAULT_RUNTIME = ROOT.parents[1] / "aureon-os-upstream" / "state" / "unified_runtime_status.json"
DEFAULT_STATE = Path("/var/lib/aureon-trade-bridge/order-intent-bridge-state.json")
DEFAULT_STATUS = Path(
    "/var/lib/aureon-control-exchange/trade-readback/latest-order-intent-bridge.json"
)

MAX_RUNTIME_BYTES = 16 * 1024 * 1024
MAX_RUNTIME_AGE_SECONDS = 30.0
MAX_OBSERVATION_AGE_SECONDS = 30.0
MAX_CLOCK_SKEW_SECONDS = 5.0
MIN_SIGNAL_CONFIDENCE = 0.70
MIN_CROSS_REFERENCES = 3
MAX_ORDER_USD = Decimal("5.00")
ROUTE_COOLDOWN_MS = 15 * 60 * 1000
STATE_RETENTION_MS = 24 * 60 * 60 * 1000
BRIDGE_INTERVAL_SECONDS = 10.0

LOCAL_EXECUTOR_HOLDS = {
    "AUREON_DEPLOYMENT_HOLD": "1",
    "AUREON_DISABLE_REAL_ORDERS": "1",
    "AUREON_DISABLE_EXCHANGE_MUTATIONS": "1",
    "AUREON_LIVE_TRADING": "0",
    "AUREON_ORDER_INTENT_PUBLISH": "0",
    "AUREON_UNIFIED_ORDER_EXECUTOR": "0",
}
LOCAL_PLAN_HOLDS = {
    "live_enabled": False,
    "real_orders_disabled": True,
    "exchange_mutations_disabled": True,
    "order_intent_publish_enabled": False,
    "executor_enabled": False,
}
SUPPORTED_ROUTE_TYPES = {
    "alpaca": "spot",
    "binance": "spot",
    "capital": "cfd",
    "kraken": "spot",
}
ROUTE_SYMBOL_FIELDS = {
    "alpaca": "alpaca_symbol",
    "binance": "binance_symbol",
    "capital": "capital_symbol",
    "kraken": "kraken_spot_symbol",
}
QUANTITY_DECIMALS = {"alpaca": 8, "binance": 8, "capital": 6, "kraken": 8}

_HEX64 = re.compile(r"[0-9a-f]{64}")
_MESSAGE_ID = re.compile(r"[0-9]{1,64}")
_REVISION = re.compile(r"[0-9a-f]{40,64}")
_SAFE_TEXT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}")
_SYMBOL = re.compile(r"[A-Z0-9][A-Z0-9./_-]{1,31}")
_STATE_FIELDS = {"schema", "entries"}
_ENTRY_FIELDS = {
    "intent_id", "client_order_id", "intent_sha256", "candidate_fingerprint",
    "route_key", "reserved_at_ms", "published_at_ms", "pubsub_message_id", "status",
}


class BridgeError(RuntimeError):
    """A stable fail-closed bridge failure."""


class CandidateUnavailable(BridgeError):
    """No currently safe candidate; the bridge itself can still be healthy."""


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise BridgeError("cloud_redirect_denied")


@dataclass(frozen=True)
class _Response:
    status_code: int
    content: bytes

    def json(self) -> Any:
        return json.loads(self.content)


def _fixed_http(
    url: str,
    *,
    method: str = "GET",
    headers: Mapping[str, str] | None = None,
    body: bytes | None = None,
    timeout: float = 8.0,
    accepted_statuses: tuple[int, ...] = (200,),
) -> _Response:
    """Use only the fixed Google endpoints, without proxies or redirects."""

    allowed = {
        ("GET", METADATA_URL),
        ("GET", FIRESTORE_RELEASE_URL),
        ("GET", FIRESTORE_READINESS_URL),
        ("GET", KMS_PUBLIC_KEY_URL),
        ("GET", EXECUTOR_PUBLIC_KEY_URL),
        ("GET", RECEIPT_PUBLIC_KEY_URL),
        ("POST", PUBLISH_URL),
    }
    verb = str(method or "").upper()
    if (verb, url) not in allowed:
        raise BridgeError("cloud_endpoint_not_allowlisted")
    if body is not None and len(body) > 131_072:
        raise BridgeError("cloud_request_too_large")
    opener = build_opener(ProxyHandler({}), NoRedirects())
    try:
        with opener.open(
            Request(url, data=body, headers=dict(headers or {}), method=verb),
            timeout=timeout,
        ) as response:
            status = int(response.status)
            raw = response.read(1_048_577)
    except HTTPError as exc:
        status = int(exc.code)
        try:
            raw = exc.read(1_048_577)
        except OSError:
            raw = b""
    except (URLError, TimeoutError, OSError) as exc:
        raise BridgeError("cloud_http_request_failed") from exc
    if len(raw) > 1_048_576:
        raise BridgeError("cloud_http_response_too_large")
    if status not in accepted_statuses:
        raise BridgeError("cloud_http_status_invalid")
    return _Response(status, raw)


def access_token(reader: Callable[..., _Response] = _fixed_http) -> str:
    try:
        token = broker_token()
    except WorkloadIdentityError as exc:
        raise BridgeError(str(exc)) from exc
    if token is not None:
        return token
    response = reader(
        METADATA_URL,
        headers={"Metadata-Flavor": "Google"},
        timeout=5.0,
        accepted_statuses=(200,),
    )
    try:
        value = response.json()
    except (ValueError, TypeError, UnicodeError) as exc:
        raise BridgeError("metadata_token_response_invalid") from exc
    token = value.get("access_token") if isinstance(value, Mapping) else None
    expires = value.get("expires_in") if isinstance(value, Mapping) else None
    if (
        not isinstance(token, str)
        or not 20 <= len(token) <= 8192
        or type(expires) is not int
        or expires < 30
    ):
        raise BridgeError("metadata_token_response_invalid")
    return token


def _controller_state(
    *,
    reader: Callable[..., _Response] = _fixed_http,
) -> tuple[dict[str, Any] | None, str | None]:
    """Call the existing signature verifier through a fixed-endpoint adapter."""

    def requester(method: str, url: str, *, headers=None, timeout=8, **_kwargs):
        statuses = (200, 404) if url == FIRESTORE_RELEASE_URL else (200,)
        return reader(
            url,
            method=method,
            headers=headers,
            timeout=float(timeout),
            accepted_statuses=statuses,
        )

    try:
        return read_controller_release(
            environ={"AUREON_CONTROLLER_KEY_VERSION": CONTROLLER_KEY},
            requester=requester,
            token_provider=lambda: access_token(reader),
        )
    except BridgeError as exc:
        return None, str(exc)


def _decode_firestore_scalar(value: Any) -> Any:
    if not isinstance(value, Mapping):
        raise BridgeError("execution_budget_attestation_invalid")
    if "nullValue" in value:
        return None
    if "booleanValue" in value and type(value["booleanValue"]) is bool:
        return value["booleanValue"]
    if "integerValue" in value:
        try:
            return int(value["integerValue"])
        except (TypeError, ValueError, OverflowError) as exc:
            raise BridgeError("execution_budget_attestation_invalid") from exc
    if "stringValue" in value and isinstance(value["stringValue"], str):
        return value["stringValue"]
    raise BridgeError("execution_budget_attestation_invalid")


def _probe_state(
    *,
    reader: Callable[..., _Response] = _fixed_http,
    now_ms: int,
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        token = access_token(reader)
        response = reader(
            FIRESTORE_READINESS_URL,
            method="GET",
            headers={"Authorization": "Bearer " + token, "Accept": "application/json"},
            timeout=8.0,
            accepted_statuses=(200, 404),
        )
        if response.status_code == 404:
            return None, "periodic_readiness_attestation_missing"
        value = response.json()
        if (
            not isinstance(value, Mapping)
            or not isinstance(value.get("fields"), Mapping)
            or not isinstance(value.get("updateTime"), str)
        ):
            raise BridgeError("execution_budget_attestation_invalid")
        row = {
            key: _decode_firestore_scalar(item)
            for key, item in value["fields"].items()
        }
        row["update_time"] = value["updateTime"]
        document = validate_periodic_readiness_document(row, now_ms=now_ms)
        executor_attestation = document["executor_attestation"]
        receipt_endorsement = document["receipt_endorsement"]
        for envelope, expected_key, url in (
            (executor_attestation, EXECUTOR_KEY, EXECUTOR_PUBLIC_KEY_URL),
            (receipt_endorsement, RECEIPT_KEY, RECEIPT_PUBLIC_KEY_URL),
        ):
            if envelope.get("key_version") != expected_key:
                raise BridgeError("periodic_readiness_key_pin_mismatch")
            public_response = reader(
                url,
                method="GET",
                headers={"Authorization": "Bearer " + token, "Accept": "application/json"},
                timeout=8.0,
                accepted_statuses=(200,),
            )
            public_value = public_response.json()
            if (
                not isinstance(public_value, Mapping)
                or public_value.get("name") != expected_key
                or public_value.get("algorithm") != "EC_SIGN_ED25519"
                or not isinstance(public_value.get("pem"), str)
            ):
                raise BridgeError("periodic_readiness_public_key_invalid")
            try:
                public = serialization.load_pem_public_key(public_value["pem"].encode("ascii"))
                signature = base64.b64decode(envelope["signature"], validate=True)
            except (ValueError, TypeError, UnicodeError, binascii.Error) as exc:
                raise BridgeError("periodic_readiness_signature_invalid") from exc
            if not isinstance(public, Ed25519PublicKey) or len(signature) != 64:
                raise BridgeError("periodic_readiness_signature_invalid")
            try:
                public.verify(
                    signature,
                    canonical_bytes(unsigned_readiness_envelope(envelope)),
                )
            except InvalidSignature as exc:
                raise BridgeError("periodic_readiness_signature_invalid") from exc
        token = ""
        return {
            key: value
            for key, value in document.items()
            if key not in {"executor_attestation", "receipt_endorsement"}
        }, None
    except (BridgeError, CloudStateError, ValueError, TypeError, UnicodeError) as exc:
        return None, (
            str(exc) if isinstance(exc, (BridgeError, CloudStateError))
            else "execution_budget_attestation_invalid"
        )


def _sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _finite_number(value: Any, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CandidateUnavailable("candidate_number_invalid")
    number = float(value)
    if not math.isfinite(number) or (positive and number <= 0):
        raise CandidateUnavailable("candidate_number_invalid")
    return number


def _timestamp_ms(value: Any, *, code: str) -> int:
    if isinstance(value, bool):
        raise CandidateUnavailable(code)
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str) and 1 <= len(value) <= 64:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise CandidateUnavailable(code) from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        number = parsed.timestamp()
    else:
        raise CandidateUnavailable(code)
    if not math.isfinite(number) or number <= 0:
        raise CandidateUnavailable(code)
    return int(number * 1000)


def _safe_text(value: Any, *, code: str) -> str:
    text = str(value or "")
    if not _SAFE_TEXT.fullmatch(text):
        raise CandidateUnavailable(code)
    return text


def _read_json_file(path: Path, *, limit: int, missing_code: str, invalid_code: str) -> tuple[dict[str, Any], bytes, os.stat_result]:
    if not path.is_absolute() or path.is_symlink():
        raise BridgeError(invalid_code)
    try:
        resolved = path.resolve(strict=True)
        stat = resolved.stat()
    except OSError as exc:
        raise BridgeError(missing_code) from exc
    if not resolved.is_file() or not 0 < stat.st_size <= limit or resolved != path.resolve():
        raise BridgeError(invalid_code)
    try:
        raw = resolved.read_bytes()
        value = json.loads(raw)
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        raise BridgeError(invalid_code) from exc
    if not isinstance(value, dict):
        raise BridgeError(invalid_code)
    return value, raw, stat


def _durable_write(path: Path, value: Mapping[str, Any], *, shared: bool = False) -> None:
    if not path.is_absolute() or path.is_symlink():
        raise BridgeError("bridge_output_path_invalid")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        parent = path.parent.resolve(strict=True)
    except OSError as exc:
        raise BridgeError("bridge_output_path_invalid") from exc
    if path.resolve().parent != parent:
        raise BridgeError("bridge_output_path_invalid")
    try:
        raw = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False,
        ).encode("ascii") + b"\n"
    except (TypeError, ValueError, UnicodeError) as exc:
        raise BridgeError("bridge_output_invalid") from exc
    handle, temporary = tempfile.mkstemp(prefix=".intent-bridge-", dir=parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o640 if shared else 0o600)
        os.replace(temporary, path)
        if os.name == "posix":
            directory = os.open(parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    except OSError as exc:
        raise BridgeError("bridge_output_write_failed") from exc
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _empty_state() -> dict[str, Any]:
    return {"schema": STATE_SCHEMA, "entries": []}


def _load_state(path: Path, *, now_ms: int) -> dict[str, Any]:
    if not path.exists():
        if path.is_symlink():
            raise BridgeError("bridge_state_invalid")
        return _empty_state()
    value, _raw, _stat = _read_json_file(
        path, limit=262_144, missing_code="bridge_state_missing", invalid_code="bridge_state_invalid",
    )
    entries = value.get("entries")
    if set(value) != _STATE_FIELDS or value.get("schema") != STATE_SCHEMA or not isinstance(entries, list) or len(entries) > 256:
        raise BridgeError("bridge_state_invalid")
    retained: list[dict[str, Any]] = []
    for item in entries:
        if not isinstance(item, Mapping) or set(item) != _ENTRY_FIELDS:
            raise BridgeError("bridge_state_invalid")
        row = dict(item)
        if (
            not _HEX64.fullmatch(str(row["intent_id"] or ""))
            or not _HEX64.fullmatch(str(row["client_order_id"] or ""))
            or not _HEX64.fullmatch(str(row["intent_sha256"] or ""))
            or not _HEX64.fullmatch(str(row["candidate_fingerprint"] or ""))
            or not _SAFE_TEXT.fullmatch(str(row["route_key"] or ""))
            or type(row["reserved_at_ms"]) is not int
            or row["reserved_at_ms"] <= 0
            or row["status"] not in {"pending", "published"}
            or (row["status"] == "pending" and (row["published_at_ms"] is not None or row["pubsub_message_id"] is not None))
            or (
                row["status"] == "published"
                and (
                    type(row["published_at_ms"]) is not int
                    or row["published_at_ms"] < row["reserved_at_ms"]
                    or not _MESSAGE_ID.fullmatch(str(row["pubsub_message_id"] or ""))
                )
            )
        ):
            raise BridgeError("bridge_state_invalid")
        if now_ms - row["reserved_at_ms"] <= STATE_RETENTION_MS:
            retained.append(row)
    return {"schema": STATE_SCHEMA, "entries": retained}


def _validate_local_holds(payload: Mapping[str, Any], environ: Mapping[str, str]) -> Mapping[str, Any]:
    if any(environ.get(key) != expected for key, expected in LOCAL_EXECUTOR_HOLDS.items()):
        raise BridgeError("bridge_service_local_holds_not_enforced")
    plan = payload.get("exchange_action_plan")
    if not isinstance(plan, Mapping) or any(plan.get(key) is not expected for key, expected in LOCAL_PLAN_HOLDS.items()):
        raise BridgeError("unified_market_trader_local_executor_not_held")
    blockers = plan.get("global_blockers")
    required = {
        "live_trading_not_enabled", "real_orders_disabled",
        "exchange_mutations_disabled", "order_intent_publish_disabled",
    }
    if not isinstance(blockers, list) or not required.issubset({str(item) for item in blockers}):
        raise BridgeError("unified_market_trader_local_executor_not_held")
    return plan


def _validate_authorization(value: Any, *, now_ms: int) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise BridgeError("operator_authorization_invalid")
    event = value.get("ledger_event_sha256")
    authorized = value.get("authorized_at")
    expires = value.get("expires_at")
    if (
        value.get("active") is not True
        or value.get("state") != "active"
        or value.get("account_scope") != "owner_cloud_account"
        or tuple(value.get("scope") or ()) != TRADING_CONTROL_SCOPE
        or not _HEX64.fullmatch(str(event or ""))
        or isinstance(authorized, bool)
        or not isinstance(authorized, (int, float))
        or isinstance(expires, bool)
        or not isinstance(expires, (int, float))
        or not math.isfinite(float(authorized))
        or not math.isfinite(float(expires))
        or int(float(authorized) * 1000) > now_ms
        or int(float(expires) * 1000) <= now_ms
        or float(expires) - float(authorized) > MAX_LEASE_SECONDS
    ):
        raise BridgeError("operator_authorization_invalid")
    return {
        "event_sha256": str(event),
        "expires_at_ms": int(float(expires) * 1000),
        "scope_sha256": hashlib.sha256(
            json.dumps(list(TRADING_CONTROL_SCOPE), separators=(",", ":")).encode("ascii")
        ).hexdigest(),
    }


def _validate_release(
    value: Any,
    *,
    authorization: Mapping[str, Any],
    revision: str,
    now_ms: int,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise BridgeError("controller_release_missing")
    row = dict(value)
    if (
        row.get("state") != "active"
        or row.get("requested_controls_sha256") != digest(LIVE_CONTROLS)
        or row.get("authorization_event_sha256") != authorization["event_sha256"]
        or row.get("authorization_expires_at_ms") != authorization["expires_at_ms"]
        or row.get("source_revision") != revision
        or row.get("controller_key_version") != CONTROLLER_KEY
        or type(row.get("signed_at_ms")) is not int
        or row["signed_at_ms"] > now_ms + int(MAX_CLOCK_SKEW_SECONDS * 1000)
        or row.get("authorization_expires_at_ms", 0) <= now_ms + 60_000
    ):
        raise BridgeError("controller_release_not_current_for_owner_runtime")
    return row


def _validate_execution_budget_attestation(
    value: Any,
    *,
    release: Mapping[str, Any],
    authorization: Mapping[str, Any],
    revision: str,
    now_ms: int,
) -> dict[str, Any]:
    try:
        row = validate_periodic_readiness_document(value, now_ms=now_ms)
        binding = build_readiness_release_binding(release)
    except CloudStateError as exc:
        raise BridgeError(str(exc)) from exc
    except ContractError as exc:
        raise BridgeError("execution_budget_attestation_release_join_invalid") from exc
    if (
        row["release_generation"] != release.get("generation")
        or row["release_request_id"] != release.get("request_id")
        or row["release_state_sha256"] != controller_release_state_sha256(release)
        or row["release_state_sha256"] != binding["release_state_sha256"]
        or row["authorization_event_sha256"] != authorization["event_sha256"]
        or row["authorization_expires_at_ms"] != authorization["expires_at_ms"]
        or row["source_revision"] != revision
        or row["source_revision"] != release.get("source_revision")
        or row["observed_at_ms"] < int(release.get("signed_at_ms") or 0) - 5_000
        or row["expires_at_ms"] > int(release.get("authorization_expires_at_ms") or 0)
    ):
        raise BridgeError("execution_budget_attestation_release_join_invalid")
    try:
        readiness = row["executor_attestation"]["statement"][
            "execution_budget_readiness"
        ]
        readiness = validate_execution_budget_readiness(
            readiness,
            source_revision=revision,
            now_ms=now_ms,
        )
    except (ContractError, ValueError, TypeError, UnicodeError) as exc:
        raise BridgeError("execution_budget_attestation_invalid") from exc
    if Decimal(readiness["maximum_order_usd"]) != MAX_ORDER_USD:
        raise BridgeError("execution_budget_cap_mismatch")
    return readiness


def _route_quote_asset(venue: str, symbol: str) -> str:
    if venue in {"alpaca", "capital"}:
        return "USD"
    normalized = symbol.upper().replace("-", "/").replace("_", "/")
    if "/" in normalized:
        quote = normalized.rsplit("/", 1)[-1]
    else:
        quote = next(
            (asset for asset in ("FDUSD", "USDT", "USDC", "USD") if normalized.endswith(asset)),
            "",
        )
    quote = {"ZUSD": "USD"}.get(quote, quote)
    if quote not in {"FDUSD", "USDT", "USDC", "USD"}:
        raise CandidateUnavailable("candidate_route_quote_asset_unsupported")
    return quote


def _runtime_payload(path: Path, *, now_ms: int) -> tuple[dict[str, Any], str, int]:
    payload, raw, stat = _read_json_file(
        path, limit=MAX_RUNTIME_BYTES,
        missing_code="unified_runtime_status_missing", invalid_code="unified_runtime_status_invalid",
    )
    generated_ms = _timestamp_ms(payload.get("generated_at"), code="unified_runtime_timestamp_invalid")
    file_age_ms = now_ms - int(stat.st_mtime * 1000)
    generated_age_ms = now_ms - generated_ms
    if (
        payload.get("ok") is not True
        or payload.get("source") != "unified-market-trader"
        or payload.get("partial") is True
        or file_age_ms < -5_000
        or file_age_ms > int(MAX_RUNTIME_AGE_SECONDS * 1000)
        or generated_age_ms < -5_000
        or generated_age_ms > int(MAX_RUNTIME_AGE_SECONDS * 1000)
    ):
        raise BridgeError("unified_runtime_status_not_fresh_complete")
    gate = payload.get("trading_gate_evidence")
    hnc = payload.get("hnc_cognitive_proof")
    if not isinstance(gate, Mapping) or gate.get("analysis_ready") is not True:
        raise CandidateUnavailable("trading_gate_analysis_not_ready")
    if (
        not isinstance(hnc, Mapping)
        or hnc.get("status") != "passing"
        or not isinstance(hnc.get("real_data"), Mapping)
        or hnc["real_data"].get("passed") is not True
        or type(hnc.get("passed_count")) is not int
        or type(hnc.get("step_count")) is not int
        or hnc["step_count"] < 1
        or hnc["passed_count"] != hnc["step_count"]
    ):
        raise CandidateUnavailable("hnc_cognitive_proof_not_passing")
    return payload, hashlib.sha256(raw).hexdigest(), generated_ms


def _candidate_evidence(
    candidate: Mapping[str, Any],
    route: Mapping[str, Any],
    *,
    runtime_generated_at_ms: int,
    now_ms: int,
    execution_budget_readiness: Mapping[str, Any],
) -> dict[str, Any]:
    symbol = str(candidate.get("symbol") or "").upper()
    side = str(candidate.get("side") or "").upper()
    venue = str(route.get("venue") or "").lower()
    route_symbol = str(route.get("symbol") or "").upper()
    market_type = str(route.get("market_type") or "").lower()
    if not _SYMBOL.fullmatch(symbol):
        raise CandidateUnavailable("candidate_symbol_invalid")
    if not _SYMBOL.fullmatch(route_symbol):
        raise CandidateUnavailable("candidate_route_symbol_invalid")
    if side not in {"BUY", "SELL"}:
        raise CandidateUnavailable("candidate_side_invalid")
    if SUPPORTED_ROUTE_TYPES.get(venue) != market_type:
        raise CandidateUnavailable("candidate_route_not_supported_by_cloud_adapter")
    binding_field = ROUTE_SYMBOL_FIELDS.get(venue)
    bound_route_symbol = (
        str(candidate.get(binding_field) or "").upper() if binding_field is not None else ""
    )
    if bound_route_symbol != route_symbol:
        raise CandidateUnavailable("candidate_route_symbol_binding_mismatch")
    # Spot sells need a fresh base-asset balance proof that the current runtime
    # candidate does not carry.  Capital CFDs can express either direction.
    if side == "SELL" and venue != "capital":
        raise CandidateUnavailable("spot_sell_asset_balance_evidence_missing")

    confidence = _finite_number(candidate.get("confidence"))
    support_count = candidate.get("support_count")
    scanner = candidate.get("scanner_fusion")
    if (
        confidence < MIN_SIGNAL_CONFIDENCE
        or type(support_count) is not int
        or support_count < 1
        or not isinstance(scanner, Mapping)
        or scanner.get("usable_for_decision") is not True
        or scanner.get("fed_to_decision_logic") is not True
        or type(scanner.get("cross_reference_count")) is not int
        or scanner["cross_reference_count"] < MIN_CROSS_REFERENCES
        or _finite_number(scanner.get("scanner_fusion_score")) <= 0
    ):
        raise CandidateUnavailable("candidate_signal_evidence_not_strong")
    if candidate.get("data_status") != "live" or candidate.get("actionable") is not True:
        raise CandidateUnavailable("candidate_not_live_actionable")
    if candidate.get("intent_publish_blockers") != []:
        raise CandidateUnavailable("candidate_has_publish_blockers")

    required_empty = ("blockers", "runtime_clearances", "guards", "clearance_required")
    if (
        route.get("ready") is not True
        or route.get("end_user_trade_available") is not True
        or route.get("trade_clearance_state") != "available"
        or route.get("guard_state") != "available"
        or any(route.get(key) != [] for key in required_empty)
        or route.get("model_coverage_ready") is not True
        or type(route.get("model_count")) is not int
        or route["model_count"] < 1
    ):
        raise CandidateUnavailable("candidate_route_evidence_not_ready")
    route_key = _safe_text(route.get("route_key"), code="candidate_route_key_invalid")
    expected_route_key = f"{venue}:{market_type}:{route_symbol}:{side}"
    if route_key != expected_route_key:
        raise CandidateUnavailable("candidate_route_key_binding_mismatch")

    venue_budget = execution_budget_readiness["venues"].get(venue)
    quote_asset = _route_quote_asset(venue, route_symbol)
    quote_budget = (
        venue_budget.get("quotes", {}).get(quote_asset)
        if isinstance(venue_budget, Mapping)
        else None
    )
    if (
        not isinstance(venue_budget, Mapping)
        or venue_budget.get("authenticated") is not True
        or not isinstance(quote_budget, Mapping)
        or quote_budget.get("status") != "sufficient"
        or Decimal(str(quote_budget.get("allowance_usd") or "0")) < MAX_ORDER_USD
    ):
        raise CandidateUnavailable("candidate_route_execution_budget_not_ready")

    reference_price = _finite_number(candidate.get("reference_price"), positive=True)
    source_prices = candidate.get("source_prices")
    observations = candidate.get("market_observations")
    if not isinstance(source_prices, Mapping) or not source_prices or len(source_prices) > 32:
        raise CandidateUnavailable("provider_price_evidence_missing")
    if not isinstance(observations, list) or not observations or len(observations) > 64:
        raise CandidateUnavailable("provider_timestamp_evidence_missing")
    prices: dict[str, float] = {}
    for key, value in source_prices.items():
        source_name = _safe_text(key, code="provider_price_source_invalid")
        prices[source_name] = _finite_number(value, positive=True)
    average = sum(prices.values()) / len(prices)
    if abs(reference_price - average) > max(1e-8, abs(average) * 1e-6):
        raise CandidateUnavailable("reference_price_not_bound_to_provider_prices")
    observation_rows: list[dict[str, Any]] = []
    feeds: set[str] = set()
    routed_provider_observations: list[dict[str, Any]] = []
    for value in observations:
        if not isinstance(value, Mapping):
            raise CandidateUnavailable("provider_timestamp_evidence_invalid")
        source = _safe_text(value.get("source"), code="provider_timestamp_source_invalid")
        feed = _safe_text(value.get("feed"), code="provider_timestamp_source_invalid")
        observation_symbol = str(value.get("symbol") or "").upper()
        if observation_symbol != symbol or not _SYMBOL.fullmatch(observation_symbol):
            raise CandidateUnavailable("provider_price_symbol_join_invalid")
        provider_symbol = str(value.get("provider_symbol") or "").upper()
        if not _SYMBOL.fullmatch(provider_symbol):
            raise CandidateUnavailable("provider_price_provider_symbol_invalid")
        observation_price = _finite_number(value.get("price"), positive=True)
        if feed not in prices or observation_price != prices[feed] or feed in feeds:
            raise CandidateUnavailable("provider_price_observation_join_invalid")
        source_ms = _timestamp_ms(value.get("source_timestamp"), code="provider_timestamp_invalid")
        max_age = _finite_number(value.get("max_age_sec"), positive=True)
        allowed_age = min(max_age, MAX_OBSERVATION_AGE_SECONDS)
        age_ms = now_ms - source_ms
        if age_ms < -int(MAX_CLOCK_SKEW_SECONDS * 1000) or age_ms > int(allowed_age * 1000):
            raise CandidateUnavailable("provider_timestamp_not_fresh")
        feeds.add(feed)
        row = {
            "feed": feed,
            "source": source,
            "symbol": observation_symbol,
            "provider_symbol": provider_symbol,
            "price": observation_price,
            "source_timestamp_ms": source_ms,
            "max_age_ms": int(allowed_age * 1000),
        }
        observation_rows.append(row)
        if source.lower() == venue or feed.lower() == venue:
            if provider_symbol != route_symbol:
                raise CandidateUnavailable("route_provider_price_symbol_join_invalid")
            routed_provider_observations.append(row)
    if set(prices) != feeds:
        raise CandidateUnavailable("provider_price_timestamp_join_missing")
    if not routed_provider_observations:
        raise CandidateUnavailable("route_provider_price_observation_missing")

    active_scanners = scanner.get("active_scanners")
    if not isinstance(active_scanners, list) or len(active_scanners) < MIN_CROSS_REFERENCES:
        raise CandidateUnavailable("candidate_scanner_evidence_missing")
    scanner_names = sorted({_safe_text(item, code="candidate_scanner_invalid") for item in active_scanners})
    evidence = {
        "schema": EVIDENCE_SCHEMA,
        "runtime_generated_at_ms": runtime_generated_at_ms,
        "candidate_id": _safe_text(candidate.get("candidate_id"), code="candidate_id_invalid"),
        "lifecycle_id": _safe_text(candidate.get("lifecycle_id"), code="candidate_lifecycle_id_invalid"),
        "symbol": symbol,
        "side": side,
        "confidence": confidence,
        "support_count": support_count,
        "reference_price": reference_price,
        "source_prices": dict(sorted(prices.items())),
        "market_observations": sorted(
            observation_rows,
            key=lambda row: (row["source_timestamp_ms"], row["feed"], row["source"]),
        ),
        "scanner_fusion": {
            "score": _finite_number(scanner["scanner_fusion_score"]),
            "cross_reference_count": scanner["cross_reference_count"],
            "active_scanners": scanner_names,
        },
        "route": {
            "venue": venue,
            "market_type": market_type,
            "symbol": route_symbol,
            "route_key": route_key,
            "model_count": route["model_count"],
            "cash_capability_state": _safe_text(
                route.get("cash_capability_state"), code="candidate_cash_capability_invalid",
            ),
            "execution_budget_quote_asset": quote_asset,
            "execution_budget_allowance_usd": float(quote_budget["allowance_usd"]),
            "execution_budget_readiness_sha256": digest(execution_budget_readiness),
            "candidate_symbol_binding_field": binding_field,
            "provider_observation_sha256": digest({
                "schema": "aureon.route-provider-price-observation-set.v1",
                "venue": venue,
                "candidate_symbol": symbol,
                "route_symbol": route_symbol,
                "observations": sorted(
                    routed_provider_observations,
                    key=lambda row: (
                        row["source_timestamp_ms"], row["feed"], row["source"],
                    ),
                ),
            }),
        },
    }
    canonical_bytes(evidence)
    return evidence


def select_candidate(
    payload: Mapping[str, Any],
    *,
    runtime_generated_at_ms: int,
    now_ms: int,
    execution_budget_readiness: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        execution_budget_readiness = validate_execution_budget_readiness(
            execution_budget_readiness,
            source_revision=str(execution_budget_readiness.get("source_revision") or ""),
            now_ms=now_ms,
        )
    except (AttributeError, ContractError) as exc:
        raise CandidateUnavailable("execution_budget_attestation_invalid") from exc
    flow = payload.get("shared_order_flow")
    if not isinstance(flow, Mapping):
        raise CandidateUnavailable("shared_order_flow_missing")
    generated_ms = _timestamp_ms(flow.get("generated_at"), code="shared_order_flow_timestamp_invalid")
    if abs(generated_ms - runtime_generated_at_ms) > int(MAX_RUNTIME_AGE_SECONDS * 1000):
        raise CandidateUnavailable("shared_order_flow_not_current_tick")
    candidates = flow.get("active_order_flow")
    if not isinstance(candidates, list):
        raise CandidateUnavailable("qualifying_candidate_unavailable")

    ranked: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    reason_codes: set[str] = set()
    for candidate in candidates[:20]:
        if not isinstance(candidate, Mapping):
            continue
        routes = candidate.get("execution_routes")
        if not isinstance(routes, list):
            continue
        for route in routes[:12]:
            if not isinstance(route, Mapping):
                continue
            try:
                evidence = _candidate_evidence(
                    candidate, route,
                    runtime_generated_at_ms=runtime_generated_at_ms,
                    now_ms=now_ms,
                    execution_budget_readiness=execution_budget_readiness,
                )
            except CandidateUnavailable as exc:
                reason_codes.add(str(exc))
                continue
            selection_rank = candidate.get("selection_rank")
            rank = selection_rank if type(selection_rank) is int and selection_rank > 0 else 1_000_000
            score = evidence["scanner_fusion"]["score"]
            ranked.append((
                (
                    rank,
                    -float(evidence["confidence"]),
                    -float(score),
                    evidence["route"]["venue"],
                    evidence["route"]["route_key"],
                ),
                evidence,
            ))
    if not ranked:
        if len(reason_codes) == 1:
            raise CandidateUnavailable(next(iter(reason_codes)))
        raise CandidateUnavailable("qualifying_candidate_unavailable")
    ranked.sort(key=lambda item: item[0])
    return ranked[0][1]


def _quantity(price: float, venue: str) -> tuple[float, float]:
    places = QUANTITY_DECIMALS[venue]
    try:
        price_decimal = Decimal(str(price))
        step = Decimal(1).scaleb(-places)
        quantity = (MAX_ORDER_USD / price_decimal).quantize(step, rounding=ROUND_DOWN)
        sized_notional = quantity * price_decimal
        quote = MAX_ORDER_USD
    except (InvalidOperation, ZeroDivisionError) as exc:
        raise CandidateUnavailable("venue_safe_quantity_unavailable") from exc
    if (quantity <= 0 or sized_notional <= 0 or sized_notional > MAX_ORDER_USD
            or quote <= 0 or quote > MAX_ORDER_USD or quantity > Decimal("1000000000")):
        raise CandidateUnavailable("venue_safe_quantity_unavailable")
    return float(quantity), float(quote)


def build_intent(
    evidence: Mapping[str, Any],
    *,
    authorization: Mapping[str, Any],
    release: Mapping[str, Any],
    revision: str,
    runtime_sha256: str,
    now_ms: int,
) -> tuple[dict[str, Any], str]:
    created_at_ms = int(evidence["runtime_generated_at_ms"])
    expires_at_ms = created_at_ms + 60_000
    if created_at_ms > now_ms + 5_000 or expires_at_ms < now_ms + 1_000:
        raise CandidateUnavailable("candidate_intent_lifetime_insufficient")
    if authorization["expires_at_ms"] < expires_at_ms:
        raise CandidateUnavailable("operator_authorization_expires_before_intent")
    market_sha = digest(evidence)
    route = evidence["route"]
    quantity, quote = _quantity(float(evidence["reference_price"]), str(route["venue"]))
    seed = {
        "schema": "aureon.cloud-order-intent-id-seed.v1",
        "source_revision": revision,
        "authorization_event_sha256": authorization["event_sha256"],
        "authorization_expires_at_ms": authorization["expires_at_ms"],
        "market_evidence_sha256": market_sha,
        "venue": route["venue"],
        "symbol": route["symbol"],
        "side": evidence["side"],
        "quantity": quantity,
        "quote_value_usd": quote,
    }
    seed_sha = digest(seed)
    intent_id = _sha_text("intent:" + seed_sha)
    client_order_id = _sha_text("client:" + seed_sha)
    release_measurement = {
        key: release[key]
        for key in (
            "schema", "state", "generation", "request_id", "requested_controls_sha256",
            "authorization_event_sha256", "authorization_expires_at_ms", "source_revision",
            "signed_at_ms", "controller_key_version", "signature", "update_time",
        )
    }
    runtime_measurement = {
        "schema": "aureon.cloud-order-runtime-measurement.v1",
        "source_revision": revision,
        "runtime_status_sha256": runtime_sha256,
        "controller_release_sha256": digest(release_measurement),
        "local_executor_held": True,
    }
    intent = {
        "schema": INTENT_SCHEMA,
        "intent_id": intent_id,
        "kind": "order",
        "tenant_commitment": _sha_text("owner_cloud_account"),
        "account_scope": "owner",
        "created_at_ms": created_at_ms,
        "expires_at_ms": expires_at_ms,
        "authorization": {
            "active": True,
            "expires_at_ms": authorization["expires_at_ms"],
            "event_sha256": authorization["event_sha256"],
            "scope_sha256": authorization["scope_sha256"],
            "release_authority": False,
            "mutation_authority": False,
        },
        "requested_controls": dict(LIVE_CONTROLS),
        "market_evidence_sha256": market_sha,
        "runtime_measurement_sha256": digest(runtime_measurement),
        "source_revision": revision,
        "order": {
            "venue": route["venue"],
            "symbol": route["symbol"],
            "side": evidence["side"],
            "order_type": "MARKET",
            "quantity": quantity,
            "quote_value_usd": quote,
            "limit_price": None,
            "client_order_id": client_order_id,
        },
        "dry_run": False,
    }
    validated = validate_intent(
        intent, now_ms=now_ms, max_order_usd=float(MAX_ORDER_USD), live_release=True,
    )
    if canonical_bytes(validated) != canonical_bytes(intent):
        raise BridgeError("intent_contract_normalization_changed_payload")
    return intent, digest(evidence)


def publish_intent(
    intent: Mapping[str, Any],
    *,
    reader: Callable[..., _Response] = _fixed_http,
    current_time: Callable[[], float] = time.time,
) -> str:
    try:
        now_ms = int(float(current_time()) * 1000)
    except (TypeError, ValueError, OverflowError) as exc:
        raise BridgeError("bridge_clock_invalid") from exc
    try:
        validated = validate_intent(
            intent, now_ms=now_ms, max_order_usd=float(MAX_ORDER_USD), live_release=True,
        )
        wire = canonical_bytes(validated)
    except Exception as exc:
        if isinstance(exc, BridgeError):
            raise
        raise BridgeError("intent_contract_validation_failed") from exc
    if wire != canonical_bytes(intent):
        raise BridgeError("intent_contract_normalization_changed_payload")
    token = access_token(reader)
    envelope = {
        "messages": [{
            "data": base64.b64encode(wire).decode("ascii"),
            "attributes": {
                "schema": INTENT_SCHEMA,
                "kind": "order",
                "intent_id": intent["intent_id"],
            },
            "orderingKey": intent["intent_id"],
        }],
    }
    response = reader(
        PUBLISH_URL,
        method="POST",
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
        body=json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("ascii"),
        timeout=15.0,
        accepted_statuses=(200,),
    )
    token = ""
    try:
        value = response.json()
    except (ValueError, TypeError, UnicodeError) as exc:
        raise BridgeError("intent_publish_response_invalid") from exc
    ids = value.get("messageIds") if isinstance(value, Mapping) else None
    if (
        not isinstance(ids, list)
        or len(ids) != 1
        or not isinstance(ids[0], str)
        or not _MESSAGE_ID.fullmatch(ids[0])
    ):
        raise BridgeError("intent_publish_response_invalid")
    return ids[0]


def _status(
    *,
    now_ms: int,
    revision: str,
    state: str,
    operational: bool,
    candidate_ready: bool,
    blockers: list[str],
    source: Mapping[str, Any] | None = None,
    release: Mapping[str, Any] | None = None,
    last_publish: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema": STATUS_SCHEMA,
        "observed_at": now_ms / 1000.0,
        "revision": revision,
        "state": state,
        "operational": operational,
        "candidate_ready": candidate_ready,
        "blockers": list(dict.fromkeys(blockers)),
        "source": dict(source) if isinstance(source, Mapping) else None,
        "controller_release": dict(release) if isinstance(release, Mapping) else None,
        "last_publish": dict(last_publish) if isinstance(last_publish, Mapping) else None,
        "release_authority": bool(release),
        "mutation_authority": False,
    }


@dataclass
class OrderIntentBridge:
    revision: str
    runtime_path: Path = DEFAULT_RUNTIME
    state_path: Path = DEFAULT_STATE
    status_path: Path = DEFAULT_STATUS
    environ: Mapping[str, str] | None = None
    current_time: Callable[[], float] = time.time
    authorization_builder: Callable[..., Mapping[str, Any]] = build_operator_authorization_receipt
    controller_reader: Callable[..., tuple[dict[str, Any] | None, str | None]] = _controller_state
    attestation_reader: Callable[..., tuple[dict[str, Any] | None, str | None]] = _probe_state
    publisher: Callable[..., str] = publish_intent
    http_reader: Callable[..., _Response] = _fixed_http

    def __post_init__(self) -> None:
        if not _REVISION.fullmatch(str(self.revision or "")):
            raise BridgeError("bridge_revision_invalid")

    def cycle(self) -> dict[str, Any]:
        try:
            now = float(self.current_time())
        except (TypeError, ValueError, OverflowError) as exc:
            raise BridgeError("bridge_clock_invalid") from exc
        if not math.isfinite(now) or now <= 0:
            raise BridgeError("bridge_clock_invalid")
        now_ms = int(now * 1000)
        env = os.environ if self.environ is None else self.environ
        source_summary: dict[str, Any] | None = None
        release_summary: dict[str, Any] | None = None
        operational = False
        try:
            payload, runtime_sha, generated_ms = _runtime_payload(self.runtime_path, now_ms=now_ms)
            _validate_local_holds(payload, env)
            source_summary = {
                "runtime_status_sha256": runtime_sha,
                "generated_at_ms": generated_ms,
                "age_ms": now_ms - generated_ms,
            }
            authorization = _validate_authorization(self.authorization_builder(now=now), now_ms=now_ms)
            release, release_error = self.controller_reader(reader=self.http_reader)
            if release is None:
                raise BridgeError(release_error or "controller_release_missing")
            release = _validate_release(
                release, authorization=authorization, revision=self.revision, now_ms=now_ms,
            )
            attestation, attestation_error = self.attestation_reader(
                reader=self.http_reader,
                now_ms=now_ms,
            )
            if attestation is None:
                raise BridgeError(attestation_error or "execution_budget_attestation_missing")
            execution_budget_readiness = _validate_execution_budget_attestation(
                attestation,
                release=release,
                authorization=authorization,
                revision=self.revision,
                now_ms=now_ms,
            )
            release_summary = {
                "state": "active",
                "generation": release["generation"],
                "request_id": release["request_id"],
                "source_revision": release["source_revision"],
                "authorization_event_sha256": release["authorization_event_sha256"],
                "authorization_expires_at_ms": release["authorization_expires_at_ms"],
            }
            operational = True
            evidence = select_candidate(
                payload,
                runtime_generated_at_ms=generated_ms,
                now_ms=now_ms,
                execution_budget_readiness=execution_budget_readiness,
            )
            intent, candidate_fingerprint = build_intent(
                evidence,
                authorization=authorization,
                release=release,
                revision=self.revision,
                runtime_sha256=runtime_sha,
                now_ms=now_ms,
            )
            route_key = evidence["route"]["route_key"]
            state = _load_state(self.state_path, now_ms=now_ms)
            if any(
                row["intent_id"] == intent["intent_id"]
                or row["candidate_fingerprint"] == candidate_fingerprint
                for row in state["entries"]
            ):
                raise CandidateUnavailable("intent_replay_blocked")
            if any(
                row["route_key"] == route_key
                and now_ms - row["reserved_at_ms"] < ROUTE_COOLDOWN_MS
                for row in state["entries"]
            ):
                raise CandidateUnavailable("route_cooldown_active")

            intent_sha = hashlib.sha256(canonical_bytes(intent)).hexdigest()
            pending = {
                "intent_id": intent["intent_id"],
                "client_order_id": intent["order"]["client_order_id"],
                "intent_sha256": intent_sha,
                "candidate_fingerprint": candidate_fingerprint,
                "route_key": route_key,
                "reserved_at_ms": now_ms,
                "published_at_ms": None,
                "pubsub_message_id": None,
                "status": "pending",
            }
            state["entries"].append(pending)
            _durable_write(self.state_path, state)
            try:
                message_id = self.publisher(intent, reader=self.http_reader)
            except Exception as exc:
                status = _status(
                    now_ms=now_ms, revision=self.revision, state="publish_outcome_unknown",
                    operational=False, candidate_ready=False,
                    blockers=[str(exc) if isinstance(exc, BridgeError) else "intent_publish_failed"],
                    source=source_summary, release=release_summary,
                )
                _durable_write(self.status_path, status, shared=self.status_path == DEFAULT_STATUS)
                return status
            pending.update(
                status="published", published_at_ms=now_ms, pubsub_message_id=message_id,
            )
            _durable_write(self.state_path, state)
            receipt = {
                "topic": TOPIC_RESOURCE,
                "intent_id": intent["intent_id"],
                "client_order_id": intent["order"]["client_order_id"],
                "intent_sha256": intent_sha,
                "market_evidence_sha256": intent["market_evidence_sha256"],
                "venue": intent["order"]["venue"],
                "symbol": intent["order"]["symbol"],
                "side": intent["order"]["side"],
                "quote_value_usd": intent["order"]["quote_value_usd"],
                "pubsub_message_id": message_id,
                "published_at_ms": now_ms,
            }
            status = _status(
                now_ms=now_ms, revision=self.revision, state="published",
                operational=True, candidate_ready=True, blockers=[],
                source=source_summary, release=release_summary, last_publish=receipt,
            )
            _durable_write(self.status_path, status, shared=self.status_path == DEFAULT_STATUS)
            return status
        except CandidateUnavailable as exc:
            status = _status(
                now_ms=now_ms, revision=self.revision, state="idle",
                operational=operational, candidate_ready=False, blockers=[str(exc)],
                source=source_summary, release=release_summary,
            )
        except BridgeError as exc:
            status = _status(
                now_ms=now_ms, revision=self.revision, state="blocked",
                operational=False, candidate_ready=False, blockers=[str(exc)],
                source=source_summary, release=release_summary,
            )
        _durable_write(self.status_path, status, shared=self.status_path == DEFAULT_STATUS)
        return status


__all__ = [
    "BRIDGE_INTERVAL_SECONDS", "BridgeError", "CandidateUnavailable",
    "DEFAULT_RUNTIME", "DEFAULT_STATE", "DEFAULT_STATUS", "LOCAL_EXECUTOR_HOLDS",
    "FIRESTORE_READINESS_URL", "OrderIntentBridge", "PUBLISH_URL", "PROJECT", "STATUS_SCHEMA", "TOPIC",
    "access_token", "build_intent", "publish_intent", "select_candidate",
]
