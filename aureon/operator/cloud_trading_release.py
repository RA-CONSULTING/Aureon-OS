"""Publish owner release requests and verify the controller's cloud state."""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
import time
from datetime import datetime
from typing import Any, Callable, Mapping
from urllib.parse import quote

import requests
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

try:
    from vm_workload_identity import WorkloadIdentityError, broker_token
except ImportError:  # Local tests outside the cloud deployment closure.
    WorkloadIdentityError = RuntimeError
    broker_token = None

PROJECT = "aureon-trading"
REQUEST_TOPIC = "aureon-trade-release-requests-v1"
REQUEST_SCHEMA = "aureon.cloud-trade-release-request.v1"
RELEASE_SCHEMA = "aureon.cloud-trade-release-state.v1"
CONTROLLER_KEY = (
    "projects/aureon-trading/locations/europe-west1/keyRings/aureon-trading-prod/"
    "cryptoKeys/aureon-controller-signing/cryptoKeyVersions/1"
)
RELEASE_DOCUMENT = "aureon_trade_release/current"
LIVE_CONTROLS = {
    "AUREON_DEPLOYMENT_HOLD": False,
    "AUREON_DISABLE_REAL_ORDERS": False,
    "AUREON_DISABLE_EXCHANGE_MUTATIONS": False,
    "AUREON_LIVE_TRADING": True,
    "AUREON_ORDER_INTENT_PUBLISH": True,
    "AUREON_UNIFIED_ORDER_EXECUTOR": True,
}
HELD_CONTROLS = {
    "AUREON_DEPLOYMENT_HOLD": True,
    "AUREON_DISABLE_REAL_ORDERS": True,
    "AUREON_DISABLE_EXCHANGE_MUTATIONS": True,
    "AUREON_LIVE_TRADING": False,
    "AUREON_ORDER_INTENT_PUBLISH": False,
    "AUREON_UNIFIED_ORDER_EXECUTOR": False,
}
_HEX64 = re.compile(r"[0-9a-f]{64}")
_REVISION = re.compile(r"[0-9a-f]{40,64}")
_MESSAGE_ID = re.compile(r"[0-9]{1,32}")
_RELEASE_FIELDS = {
    "schema", "state", "generation", "request_id", "requested_controls_sha256",
    "authorization_event_sha256", "authorization_expires_at_ms", "probe_receipt_sha256",
    "provider_readback_sha256", "source_revision", "signed_at_ms",
    "controller_key_version", "signature", "update_time",
}


class CloudTradingReleaseError(RuntimeError):
    """Stable release boundary failure."""


def _canonical(value: Mapping[str, Any]) -> bytes:
    try:
        raw = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise CloudTradingReleaseError("release_message_invalid") from exc
    if not 0 < len(raw) <= 65_536:
        raise CloudTradingReleaseError("release_message_invalid")
    return raw


def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def probe_runtime_measurement_sha256(source_revision: str) -> str:
    """Match the authority contract's revision-bound held probe measurement."""
    if not isinstance(source_revision, str) or _REVISION.fullmatch(source_revision) is None:
        raise CloudTradingReleaseError("cloud_probe_source_revision_invalid")
    return _digest({
        "schema": "aureon.cloud-trade-probe-runtime-measurement.v1",
        "source_revision": source_revision,
        "requested_controls": HELD_CONTROLS,
    })


def _access_token() -> str:
    if broker_token is not None:
        try:
            token = broker_token()
        except WorkloadIdentityError as exc:
            raise CloudTradingReleaseError(str(exc)) from exc
        if token is not None:
            return token
    response = requests.get(
        "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
        headers={"Metadata-Flavor": "Google"}, timeout=3,
    )
    if response.status_code != 200:
        raise CloudTradingReleaseError("cloud_release_identity_unavailable")
    try:
        value = response.json()
    except (ValueError, TypeError) as exc:
        raise CloudTradingReleaseError("cloud_release_identity_unavailable") from exc
    token = value.get("access_token") if isinstance(value, Mapping) else None
    if not isinstance(token, str) or not 20 <= len(token) <= 8192:
        raise CloudTradingReleaseError("cloud_release_identity_unavailable")
    return token


def _cloud_json(response: Any, code: str) -> dict[str, Any]:
    if not 200 <= int(getattr(response, "status_code", 0)) < 300:
        raise CloudTradingReleaseError(code)
    try:
        value = response.json()
    except (ValueError, TypeError) as exc:
        raise CloudTradingReleaseError(code) from exc
    if not isinstance(value, Mapping):
        raise CloudTradingReleaseError(code)
    return dict(value)


def _decode_firestore_value(value: Any) -> Any:
    if not isinstance(value, Mapping):
        raise CloudTradingReleaseError("cloud_release_state_invalid")
    if "nullValue" in value:
        return None
    if "booleanValue" in value and type(value["booleanValue"]) is bool:
        return value["booleanValue"]
    if "integerValue" in value:
        return int(value["integerValue"])
    if "stringValue" in value and isinstance(value["stringValue"], str):
        return value["stringValue"]
    raise CloudTradingReleaseError("cloud_release_state_invalid")


def _decode_document(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or not isinstance(value.get("fields"), Mapping):
        raise CloudTradingReleaseError("cloud_release_state_invalid")
    update_time = value.get("updateTime")
    if not isinstance(update_time, str):
        raise CloudTradingReleaseError("cloud_release_state_invalid")
    decoded = {key: _decode_firestore_value(item) for key, item in value["fields"].items()}
    decoded["update_time"] = update_time
    return decoded


def read_controller_release(
    *, environ: Mapping[str, str] | None = None, requester: Callable[..., Any] = requests.request,
    token_provider: Callable[[], str] = _access_token,
) -> tuple[dict[str, Any] | None, str | None]:
    env = os.environ if environ is None else environ
    key_version = str(env.get("AUREON_CONTROLLER_KEY_VERSION") or "")
    if key_version != CONTROLLER_KEY:
        return None, "cloud_release_controller_unconfigured"
    try:
        token = token_provider()
        headers = {"Authorization": "Bearer " + token, "Accept": "application/json"}
        document = requester(
            "GET",
            "https://firestore.googleapis.com/v1/projects/"
            + PROJECT + "/databases/(default)/documents/" + quote(RELEASE_DOCUMENT, safe="/"),
            headers=headers, timeout=8,
        )
        if document.status_code == 404:
            return None, "cloud_release_state_missing"
        row = _decode_document(_cloud_json(document, "cloud_release_state_unavailable"))
        if set(row) != _RELEASE_FIELDS:
            raise CloudTradingReleaseError("cloud_release_state_invalid")
        unsigned = {key: row[key] for key in _RELEASE_FIELDS - {"signature", "update_time"}}
        if (row["schema"] != RELEASE_SCHEMA or row["state"] not in {"active", "held"}
                or type(row["generation"]) is not int or row["generation"] < 1
                or any(not _HEX64.fullmatch(str(row[key] or "")) for key in (
                    "request_id", "requested_controls_sha256", "authorization_event_sha256",
                    "probe_receipt_sha256", "provider_readback_sha256"))
                or type(row["authorization_expires_at_ms"]) is not int
                or type(row["signed_at_ms"]) is not int
                or not _REVISION.fullmatch(str(row["source_revision"] or ""))
                or row["controller_key_version"] != CONTROLLER_KEY
                or not isinstance(row["signature"], str)):
            raise CloudTradingReleaseError("cloud_release_state_invalid")
        public_response = requester(
            "GET", "https://cloudkms.googleapis.com/v1/" + CONTROLLER_KEY + "/publicKey",
            headers=headers, timeout=8,
        )
        public_value = _cloud_json(public_response, "cloud_release_public_key_unavailable")
        if (public_value.get("name") != CONTROLLER_KEY
                or public_value.get("algorithm") != "EC_SIGN_ED25519"
                or not isinstance(public_value.get("pem"), str)):
            raise CloudTradingReleaseError("cloud_release_public_key_invalid")
        public = serialization.load_pem_public_key(public_value["pem"].encode("ascii"))
        signature = base64.b64decode(row["signature"], validate=True)
        if not isinstance(public, Ed25519PublicKey) or len(signature) != 64:
            raise CloudTradingReleaseError("cloud_release_signature_invalid")
        public.verify(signature, _canonical(unsigned))
        return row, None
    except InvalidSignature:
        return None, "cloud_release_signature_invalid"
    except (CloudTradingReleaseError, ValueError, TypeError, UnicodeError, binascii.Error) as exc:
        return None, str(exc) if isinstance(exc, CloudTradingReleaseError) else "cloud_release_state_invalid"


def publish_release_request(
    action: str, control: Mapping[str, Any], *, environ: Mapping[str, str] | None = None,
    now: float | None = None, requester: Callable[..., Any] = requests.request,
    token_provider: Callable[[], str] = _access_token,
) -> dict[str, Any]:
    env = os.environ if environ is None else environ
    current = time.time() if now is None else float(now)
    now_ms = int(current * 1000)
    revision = str(env.get("AUREON_REVISION") or env.get("AUREON_OPERATOR_REVISION") or "")
    if action not in {"activate", "hold"} or not _REVISION.fullmatch(revision):
        raise CloudTradingReleaseError("cloud_release_request_config_invalid")
    requested_controls = LIVE_CONTROLS if action == "activate" else HELD_CONTROLS
    if action == "activate":
        probe = control.get("last_probe")
        authorization = control.get("authorization")
        capabilities = control.get("capabilities")
        if (control.get("operator_can_apply_live") is not True
                or control.get("desired_live_state") is not True
                or not isinstance(probe, Mapping) or probe.get("current") is not True
                or not isinstance(authorization, Mapping) or authorization.get("active") is not True
                or not isinstance(capabilities, Mapping)
                or any(capabilities.get(key) is not True for key in (
                    "durable_budget_ledger", "order_adapter_ready",
                    "all_four_provider_readback_pinned", "live_result_binding_ready",
                    "instrument_preflight_enforced", "controller_integrated",
                ))):
            raise CloudTradingReleaseError("cloud_release_prerequisites_not_ready")
        if (probe.get("source_revision") != revision
                or probe.get("runtime_measurement_sha256")
                != probe_runtime_measurement_sha256(revision)):
            raise CloudTradingReleaseError("cloud_release_probe_revision_mismatch")
        provider = probe.get("provider_readback")
        if not isinstance(provider, Mapping):
            raise CloudTradingReleaseError("cloud_release_provider_evidence_missing")
        auth_event = authorization.get("ledger_event_sha256")
        expires_iso = authorization.get("expires_at_iso")
        try:
            expires_ms = int(datetime.fromisoformat(
                str(expires_iso).replace("Z", "+00:00"),
            ).timestamp() * 1000)
        except (ValueError, TypeError) as exc:
            raise CloudTradingReleaseError("cloud_release_authorization_invalid") from exc
        probe_receipt = probe.get("receipt_sha256")
        provider_receipt = provider.get("readback_sha256")
        if (not _HEX64.fullmatch(str(auth_event or ""))
                or not _HEX64.fullmatch(str(probe_receipt or ""))
                or not _HEX64.fullmatch(str(provider_receipt or ""))
                or not now_ms < expires_ms <= now_ms + 259_200_000):
            raise CloudTradingReleaseError("cloud_release_authorization_invalid")
    else:
        auth_event = expires_ms = probe_receipt = provider_receipt = None
    unsigned = {
        "schema": REQUEST_SCHEMA,
        "action": action,
        "created_at_ms": now_ms,
        "expires_at_ms": now_ms + 60_000,
        "requested_controls": dict(requested_controls),
        "authorization_event_sha256": auth_event,
        "authorization_expires_at_ms": expires_ms,
        "probe_receipt_sha256": probe_receipt,
        "provider_readback_sha256": provider_receipt,
        "source_revision": revision,
    }
    value = {**unsigned, "request_id": _digest(unsigned)}
    token = token_provider()
    response = requester(
        "POST", f"https://pubsub.googleapis.com/v1/projects/{PROJECT}/topics/{REQUEST_TOPIC}:publish",
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
        json={"messages": [{
            "data": base64.b64encode(_canonical(value)).decode("ascii"),
            "attributes": {"schema": REQUEST_SCHEMA, "action": action, "request_id": value["request_id"]},
        }]}, timeout=8,
    )
    result = _cloud_json(response, "cloud_release_request_publish_failed")
    ids = result.get("messageIds")
    if (not isinstance(ids, list) or len(ids) != 1
            or not isinstance(ids[0], str) or not _MESSAGE_ID.fullmatch(ids[0])):
        raise CloudTradingReleaseError("cloud_release_request_publish_response_invalid")
    return {
        "schema": "aureon.operator.cloud-trading-release-request.v1",
        "action": action,
        "request_id": value["request_id"],
        "pubsub_message_id": ids[0],
        "requested_at": current,
        "controller_pending": True,
        "release_authority": False,
        "mutation_authority": False,
    }


__all__ = [
    "CloudTradingReleaseError", "CONTROLLER_KEY", "HELD_CONTROLS", "LIVE_CONTROLS",
    "probe_runtime_measurement_sha256", "publish_release_request", "read_controller_release",
]
