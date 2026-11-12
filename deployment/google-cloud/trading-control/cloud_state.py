"""Firestore custody for verified probes and signed live-release state."""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib.parse import quote

import requests

from contract import (
    ContractError,
    canonical_bytes,
    digest,
    periodic_readiness_probe,
    probe_runtime_measurement_sha256,
    provider_readback_commitment_sha256,
    validate_execution_budget_readiness,
    validate_readiness_envelope,
    validate_provider_probe_readback,
)
from firestore_ledger import LedgerError, _document, _fields, _token


PROJECT = "aureon-trading"
DATABASE = "(default)"
BASE = f"https://firestore.googleapis.com/v1/projects/{PROJECT}/databases/{DATABASE}"
PROBE_DOCUMENT = "aureon_trade_attestations/current_probe"
READINESS_DOCUMENT = "aureon_trade_attestations/current_readiness"
RELEASE_DOCUMENT = "aureon_trade_release/current"
_HEX64 = re.compile(r"[0-9a-f]{64}")
_REVISION = re.compile(r"[0-9a-f]{40,64}")


class CloudStateError(RuntimeError):
    """Stable cloud-state failure."""


@dataclass
class FirestoreControlState:
    requester: Callable[..., Any] = requests.request
    token_provider: Callable[[], str] = _token
    timeout_seconds: float = 8.0

    def _request(self, method: str, path: str, *, body: Mapping[str, Any] | None = None,
                 params: Mapping[str, Any] | None = None,
                 statuses: tuple[int, ...] = (200,)) -> tuple[int, Any]:
        try:
            token = self.token_provider()
        except LedgerError as exc:
            raise CloudStateError(str(exc)) from exc
        if not isinstance(token, str) or not 20 <= len(token) <= 8192:
            raise CloudStateError("cloud_state_identity_unavailable")
        response = self.requester(
            method, BASE + path,
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
            params=dict(params or {}), json=dict(body) if body is not None else None,
            timeout=self.timeout_seconds,
        )
        token = ""
        if response.status_code not in statuses:
            raise CloudStateError("cloud_state_http_status_" + str(response.status_code))
        if response.status_code == 404:
            return 404, None
        try:
            value = response.json()
        except (ValueError, TypeError) as exc:
            raise CloudStateError("cloud_state_response_invalid") from exc
        if not isinstance(value, Mapping):
            raise CloudStateError("cloud_state_response_invalid")
        return response.status_code, dict(value)

    def _read(self, document: str) -> dict[str, Any] | None:
        status, value = self._request(
            "GET", "/documents/" + quote(document, safe="/"), statuses=(200, 404),
        )
        if status == 404:
            return None
        try:
            return _document(value)
        except LedgerError as exc:
            raise CloudStateError(str(exc)) from exc

    def read_probe(self) -> dict[str, Any] | None:
        return self._read(PROBE_DOCUMENT)

    def read_readiness(self) -> dict[str, Any] | None:
        return self._read(READINESS_DOCUMENT)

    def read_release(self) -> dict[str, Any] | None:
        return self._read(RELEASE_DOCUMENT)

    def _write(self, document: str, fields: Mapping[str, Any], *,
               expected_update_time: str | None) -> dict[str, Any]:
        params: dict[str, Any] = {"updateMask.fieldPaths": list(fields)}
        if expected_update_time is None:
            params["currentDocument.exists"] = "false"
        else:
            params["currentDocument.updateTime"] = expected_update_time
        try:
            encoded = _fields(fields)
        except LedgerError as exc:
            raise CloudStateError(str(exc)) from exc
        _, value = self._request(
            "PATCH", "/documents/" + quote(document, safe="/"),
            body={"fields": encoded}, params=params,
        )
        try:
            return _document(value)
        except LedgerError as exc:
            raise CloudStateError(str(exc)) from exc

    def put_probe_attestation(self, terminal: Mapping[str, Any], *, source_revision: str,
                              stored_at_ms: int | None = None) -> dict[str, Any]:
        current = int(time.time() * 1000) if stored_at_ms is None else stored_at_ms
        try:
            executor = terminal["executor"]
            result = executor["result"]
            dispatch = result["dispatch"]
            intent = dispatch["review"]["intent"]
            outcome = result["outcome"]
            capabilities = outcome["executor_capabilities"]
            provider = outcome["provider_readback"]
        except (KeyError, TypeError) as exc:
            raise CloudStateError("probe_attestation_shape_invalid") from exc
        expected_capabilities = {
            "live_execution_release", "durable_budget_ledger", "order_adapter_ready",
            "live_result_binding_ready", "instrument_preflight_enforced",
        }
        if (intent.get("kind") != "control_plane_probe"
                or periodic_readiness_probe(intent)
                or set(capabilities) != expected_capabilities
                or any(type(value) is not bool for value in capabilities.values())
                or provider.get("provider_count") != 4
                or provider.get("all_authenticated") is not True
                or provider.get("instrument_preflight_enforced") is not True
                or not _HEX64.fullmatch(str(provider.get("readback_sha256") or ""))):
            raise CloudStateError("probe_attestation_shape_invalid")
        authorization = intent.get("authorization")
        measurement = intent.get("runtime_measurement_sha256")
        intent_revision = intent.get("source_revision")
        try:
            expected_measurement = probe_runtime_measurement_sha256(source_revision)
        except ContractError as exc:
            raise CloudStateError("probe_attestation_shape_invalid") from exc
        if (not isinstance(authorization, Mapping)
                or not _HEX64.fullmatch(str(authorization.get("event_sha256") or ""))
                or type(authorization.get("expires_at_ms")) is not int
                or not _REVISION.fullmatch(str(intent_revision or ""))
                or intent_revision != source_revision
                or measurement != expected_measurement):
            raise CloudStateError("probe_attestation_shape_invalid")
        try:
            provider = validate_provider_probe_readback(
                provider,
                source_revision=source_revision,
                now_ms=current,
            )
            readiness = provider["execution_budget_readiness"]
            readiness_json = canonical_bytes(readiness).decode("ascii")
        except (ContractError, UnicodeError) as exc:
            raise CloudStateError("probe_attestation_shape_invalid") from exc
        fields = {
            "schema": "aureon.cloud-trade-probe-attestation.v2",
            "receipt_sha256": digest(terminal),
            "intent_id": intent["intent_id"],
            "intent_created_at_ms": intent["created_at_ms"],
            "stored_at_ms": current,
            "authorization_event_sha256": authorization["event_sha256"],
            "authorization_expires_at_ms": authorization["expires_at_ms"],
            "provider_readback_sha256": provider["readback_sha256"],
            "provider_accounts_sha256": provider["provider_accounts_sha256"],
            "execution_budget_readiness_sha256": provider["execution_budget_readiness_sha256"],
            "execution_budget_readiness_json": readiness_json,
            "provider_count": 4,
            "all_authenticated": True,
            "durable_budget_ledger": capabilities["durable_budget_ledger"],
            "order_adapter_ready": capabilities["order_adapter_ready"],
            "live_result_binding_ready": capabilities["live_result_binding_ready"],
            "instrument_preflight_enforced": capabilities["instrument_preflight_enforced"],
            "runtime_measurement_sha256": measurement,
            "source_revision": source_revision,
        }
        existing = self.read_probe()
        return self._write(
            PROBE_DOCUMENT, fields,
            expected_update_time=existing.get("update_time") if existing else None,
        )

    def put_periodic_readiness_attestation(
        self,
        executor_attestation: Mapping[str, Any],
        receipt_endorsement: Mapping[str, Any],
        *,
        stored_at_ms: int | None = None,
    ) -> dict[str, Any]:
        """Store only two compact detached KMS-signed readiness envelopes."""

        current = int(time.time() * 1000) if stored_at_ms is None else stored_at_ms
        try:
            executor = validate_readiness_envelope(
                executor_attestation, role="executor", now_ms=current,
            )
            executor_sha256 = digest(executor)
            receipt = validate_readiness_envelope(
                receipt_endorsement,
                role="receipt",
                now_ms=current,
                executor_attestation_sha256=executor_sha256,
            )
            statement = executor["statement"]
            if (any(receipt[key] != statement[key] for key in (
                "source_revision", "release_generation", "release_state_sha256",
                "authorization_event_sha256", "authorization_expires_at_ms",
                "observed_at_ms", "expires_at_ms",
            )) or receipt["statement_sha256"] != digest(statement)):
                raise CloudStateError("periodic_readiness_endorsement_join_invalid")
            executor_json = canonical_bytes(executor).decode("ascii")
            receipt_json = canonical_bytes(receipt).decode("ascii")
            if len(executor_json) > 4096 or len(receipt_json) > 4096:
                raise CloudStateError("periodic_readiness_envelope_too_large")
        except (ContractError, KeyError, TypeError, UnicodeError) as exc:
            if isinstance(exc, CloudStateError):
                raise
            raise CloudStateError("periodic_readiness_attestation_invalid") from exc
        fields = {
            "schema": "aureon.cloud-trade-periodic-readiness-document.v1",
            "stored_at_ms": current,
            "source_revision": statement["source_revision"],
            "release_generation": statement["release_generation"],
            "release_request_id": statement["release_request_id"],
            "release_state_sha256": statement["release_state_sha256"],
            "authorization_event_sha256": statement["authorization_event_sha256"],
            "authorization_expires_at_ms": statement["authorization_expires_at_ms"],
            "observed_at_ms": statement["observed_at_ms"],
            "expires_at_ms": statement["expires_at_ms"],
            "provider_accounts_sha256": statement["provider_accounts_sha256"],
            "provider_readback_sha256": statement["provider_readback_sha256"],
            "execution_budget_readiness_sha256": statement[
                "execution_budget_readiness_sha256"
            ],
            "maximum_order_usd": statement["maximum_order_usd"],
            "provider_count": 4,
            "all_authenticated": True,
            "provider_mutation_attempted": False,
            "orders_attempted": 0,
            "orders_submitted": 0,
            "executor_attestation_sha256": executor_sha256,
            "executor_attestation_json": executor_json,
            "receipt_endorsement_sha256": digest(receipt),
            "receipt_endorsement_json": receipt_json,
        }
        existing = self.read_readiness()
        return self._write(
            READINESS_DOCUMENT,
            fields,
            expected_update_time=existing.get("update_time") if existing else None,
        )

    def put_release(self, fields: Mapping[str, Any], *,
                    expected_update_time: str | None) -> dict[str, Any]:
        if not isinstance(fields, Mapping) or len(fields) > 24:
            raise CloudStateError("release_state_invalid")
        return self._write(RELEASE_DOCUMENT, fields, expected_update_time=expected_update_time)


def validate_probe_attestation(value: Any, *, now_ms: int) -> dict[str, Any]:
    required = {
        "schema", "receipt_sha256", "intent_id", "intent_created_at_ms", "stored_at_ms",
        "authorization_event_sha256", "authorization_expires_at_ms",
        "provider_readback_sha256", "provider_count", "all_authenticated",
        "provider_accounts_sha256", "execution_budget_readiness_sha256",
        "execution_budget_readiness_json",
        "durable_budget_ledger", "order_adapter_ready", "live_result_binding_ready",
        "instrument_preflight_enforced",
        "runtime_measurement_sha256", "source_revision", "update_time",
    }
    if not isinstance(value, Mapping) or set(value) != required:
        raise CloudStateError("probe_attestation_invalid")
    row = dict(value)
    if (row["schema"] != "aureon.cloud-trade-probe-attestation.v2"
            or any(not _HEX64.fullmatch(str(row[key] or "")) for key in (
                "receipt_sha256", "intent_id", "authorization_event_sha256",
                "provider_readback_sha256", "provider_accounts_sha256",
                "execution_budget_readiness_sha256", "runtime_measurement_sha256"))
            or not _REVISION.fullmatch(str(row["source_revision"] or ""))
            or any(type(row[key]) is not int for key in (
                "intent_created_at_ms", "stored_at_ms", "authorization_expires_at_ms"))
            or not 0 <= now_ms - row["stored_at_ms"] <= 300_000
            or row["authorization_expires_at_ms"] <= now_ms
            or row["provider_count"] != 4 or row["all_authenticated"] is not True
            or row["durable_budget_ledger"] is not True
            or row["order_adapter_ready"] is not True
            or row["live_result_binding_ready"] is not True
            or row["instrument_preflight_enforced"] is not True
            or not isinstance(row["update_time"], str)):
        raise CloudStateError("probe_attestation_invalid")
    try:
        expected_measurement = probe_runtime_measurement_sha256(row["source_revision"])
    except ContractError as exc:
        raise CloudStateError("probe_attestation_invalid") from exc
    if row["runtime_measurement_sha256"] != expected_measurement:
        raise CloudStateError("probe_attestation_invalid")
    try:
        readiness_json = row["execution_budget_readiness_json"]
        if not isinstance(readiness_json, str) or not 0 < len(readiness_json) <= 4096:
            raise CloudStateError("probe_attestation_invalid")
        readiness = json.loads(readiness_json)
        if canonical_bytes(readiness).decode("ascii") != readiness_json:
            raise CloudStateError("probe_attestation_invalid")
        readiness = validate_execution_budget_readiness(
            readiness,
            source_revision=row["source_revision"],
            now_ms=now_ms,
        )
        if row["execution_budget_readiness_sha256"] != digest(readiness):
            raise CloudStateError("probe_attestation_invalid")
        expected_readback = provider_readback_commitment_sha256(
            row["provider_accounts_sha256"],
            row["execution_budget_readiness_sha256"],
        )
    except (ContractError, ValueError, TypeError, UnicodeError) as exc:
        raise CloudStateError("probe_attestation_invalid") from exc
    if row["provider_readback_sha256"] != expected_readback:
        raise CloudStateError("probe_attestation_invalid")
    return row


def validate_periodic_readiness_document(value: Any, *, now_ms: int) -> dict[str, Any]:
    required = {
        "schema", "stored_at_ms", "source_revision", "release_generation",
        "release_request_id", "release_state_sha256", "authorization_event_sha256",
        "authorization_expires_at_ms", "observed_at_ms", "expires_at_ms",
        "provider_accounts_sha256", "provider_readback_sha256",
        "execution_budget_readiness_sha256", "maximum_order_usd", "provider_count",
        "all_authenticated", "provider_mutation_attempted", "orders_attempted",
        "orders_submitted", "executor_attestation_sha256", "executor_attestation_json",
        "receipt_endorsement_sha256", "receipt_endorsement_json", "update_time",
    }
    if not isinstance(value, Mapping) or set(value) != required:
        raise CloudStateError("periodic_readiness_document_invalid")
    row = dict(value)
    try:
        if (
            row["schema"] != "aureon.cloud-trade-periodic-readiness-document.v1"
            or type(row["stored_at_ms"]) is not int
            or not isinstance(row["executor_attestation_json"], str)
            or not isinstance(row["receipt_endorsement_json"], str)
            or not 0 < len(row["executor_attestation_json"]) <= 4096
            or not 0 < len(row["receipt_endorsement_json"]) <= 4096
            or not isinstance(row["update_time"], str)
        ):
            raise CloudStateError("periodic_readiness_document_invalid")
        executor = json.loads(row["executor_attestation_json"])
        receipt = json.loads(row["receipt_endorsement_json"])
        if (
            canonical_bytes(executor).decode("ascii") != row["executor_attestation_json"]
            or canonical_bytes(receipt).decode("ascii") != row["receipt_endorsement_json"]
        ):
            raise CloudStateError("periodic_readiness_document_invalid")
        executor = validate_readiness_envelope(executor, role="executor", now_ms=now_ms)
        executor_sha256 = digest(executor)
        receipt = validate_readiness_envelope(
            receipt,
            role="receipt",
            now_ms=now_ms,
            executor_attestation_sha256=executor_sha256,
        )
        statement = executor["statement"]
        expected = {
            "source_revision": statement["source_revision"],
            "release_generation": statement["release_generation"],
            "release_request_id": statement["release_request_id"],
            "release_state_sha256": statement["release_state_sha256"],
            "authorization_event_sha256": statement["authorization_event_sha256"],
            "authorization_expires_at_ms": statement["authorization_expires_at_ms"],
            "observed_at_ms": statement["observed_at_ms"],
            "expires_at_ms": statement["expires_at_ms"],
            "provider_accounts_sha256": statement["provider_accounts_sha256"],
            "provider_readback_sha256": statement["provider_readback_sha256"],
            "execution_budget_readiness_sha256": statement[
                "execution_budget_readiness_sha256"
            ],
            "maximum_order_usd": statement["maximum_order_usd"],
            "provider_count": 4,
            "all_authenticated": True,
            "provider_mutation_attempted": False,
            "orders_attempted": 0,
            "orders_submitted": 0,
            "executor_attestation_sha256": executor_sha256,
            "receipt_endorsement_sha256": digest(receipt),
        }
        if any(row[key] != expected_value for key, expected_value in expected.items()):
            raise CloudStateError("periodic_readiness_document_join_invalid")
        if (any(receipt[key] != statement[key] for key in (
            "source_revision", "release_generation", "release_state_sha256",
            "authorization_event_sha256", "authorization_expires_at_ms",
            "observed_at_ms", "expires_at_ms",
        )) or receipt["statement_sha256"] != digest(statement)):
            raise CloudStateError("periodic_readiness_endorsement_join_invalid")
        if not statement["observed_at_ms"] <= row["stored_at_ms"] < statement["expires_at_ms"]:
            raise CloudStateError("periodic_readiness_document_time_invalid")
    except (ContractError, ValueError, TypeError, KeyError, UnicodeError) as exc:
        if isinstance(exc, CloudStateError):
            raise
        raise CloudStateError("periodic_readiness_document_invalid") from exc
    return {**row, "executor_attestation": executor, "receipt_endorsement": receipt}


__all__ = [
    "CloudStateError", "FirestoreControlState", "validate_periodic_readiness_document",
    "validate_probe_attestation",
]
