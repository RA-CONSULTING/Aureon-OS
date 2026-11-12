"""Transactional Firestore effect and daily-budget custody for live orders."""
from __future__ import annotations

import base64
import math
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Protocol
from urllib.parse import quote

import requests


PROJECT = "aureon-trading"
DATABASE = "(default)"
BASE = f"https://firestore.googleapis.com/v1/projects/{PROJECT}/databases/{DATABASE}"
_HEX64 = re.compile(r"[0-9a-f]{64}")
_STATE = {"claimed", "submitting", "observed", "rejected", "uncertain"}


class LedgerError(RuntimeError):
    """Stable durable-ledger error."""


class HTTPResponse(Protocol):
    status_code: int

    def json(self) -> Any: ...


Request = Callable[..., HTTPResponse]
Token = Callable[[], str]


def _token() -> str:
    from google.auth import default as google_auth_default
    from google.auth.transport.requests import Request as GoogleAuthRequest

    credentials, _ = google_auth_default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    credentials.refresh(GoogleAuthRequest())
    token = credentials.token
    if not isinstance(token, str) or not 20 <= len(token) <= 8192:
        raise LedgerError("ledger_cloud_identity_unavailable")
    return token


def _value(value: Any) -> dict[str, Any]:
    if value is None:
        return {"nullValue": None}
    if type(value) is bool:
        return {"booleanValue": value}
    if type(value) is int:
        return {"integerValue": str(value)}
    if isinstance(value, float) and math.isfinite(value):
        return {"doubleValue": value}
    if isinstance(value, str) and len(value) <= 4096:
        return {"stringValue": value}
    raise LedgerError("ledger_field_value_invalid")


def _fields(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: _value(item) for key, item in value.items()}


def _decode_value(value: Mapping[str, Any]) -> Any:
    if "nullValue" in value:
        return None
    if "booleanValue" in value and type(value["booleanValue"]) is bool:
        return value["booleanValue"]
    if "integerValue" in value:
        return int(value["integerValue"])
    if "doubleValue" in value:
        return float(value["doubleValue"])
    if "stringValue" in value and isinstance(value["stringValue"], str):
        return value["stringValue"]
    raise LedgerError("ledger_document_field_invalid")


def _document(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or not isinstance(value.get("name"), str):
        raise LedgerError("ledger_document_invalid")
    fields = value.get("fields")
    update_time = value.get("updateTime")
    if not isinstance(fields, Mapping) or not isinstance(update_time, str):
        raise LedgerError("ledger_document_invalid")
    result = {key: _decode_value(item) for key, item in fields.items() if isinstance(item, Mapping)}
    result["update_time"] = update_time
    return result


@dataclass
class FirestoreLedger:
    daily_budget_usd: float
    requester: Request = requests.request
    token_provider: Token = _token
    timeout_seconds: float = 8.0

    def __post_init__(self) -> None:
        if not math.isfinite(self.daily_budget_usd) or not 0 < self.daily_budget_usd <= 10_000:
            raise LedgerError("daily_budget_invalid")

    @staticmethod
    def _effect_name(intent_id: str) -> str:
        if not _HEX64.fullmatch(intent_id):
            raise LedgerError("ledger_intent_id_invalid")
        return f"projects/{PROJECT}/databases/{DATABASE}/documents/aureon_trade_effects/{intent_id}"

    @staticmethod
    def _budget_name(now_ms: int) -> str:
        if type(now_ms) is not int or now_ms <= 0:
            raise LedgerError("ledger_time_invalid")
        day = datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc).strftime("%Y%m%d")
        return f"projects/{PROJECT}/databases/{DATABASE}/documents/aureon_trade_budgets/{day}"

    def _request(self, method: str, path: str, *, body: Mapping[str, Any] | None = None,
                 params: Mapping[str, Any] | None = None, statuses: tuple[int, ...] = (200,)) -> tuple[int, Any]:
        token = self.token_provider()
        if not isinstance(token, str) or not 20 <= len(token) <= 8192:
            raise LedgerError("ledger_cloud_identity_unavailable")
        response = self.requester(
            method, BASE + path,
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
            params=dict(params or {}), json=dict(body) if body is not None else None,
            timeout=self.timeout_seconds,
        )
        token = ""
        if response.status_code not in statuses:
            raise LedgerError("ledger_http_status_" + str(response.status_code))
        if response.status_code == 404:
            return response.status_code, None
        try:
            value = response.json()
        except (ValueError, TypeError) as exc:
            raise LedgerError("ledger_http_response_invalid") from exc
        if not isinstance(value, Mapping):
            raise LedgerError("ledger_http_response_invalid")
        return response.status_code, dict(value)

    def _begin(self) -> str:
        _, value = self._request("POST", "/documents:beginTransaction", body={"options": {"readWrite": {}}})
        transaction = value.get("transaction")
        try:
            raw = base64.b64decode(transaction, validate=True)
        except (TypeError, ValueError) as exc:
            raise LedgerError("ledger_transaction_invalid") from exc
        if not raw or len(raw) > 4096:
            raise LedgerError("ledger_transaction_invalid")
        return transaction

    def _get(self, name: str, transaction: str | None = None) -> dict[str, Any] | None:
        path = "/documents/" + name.split("/documents/", 1)[1]
        status, value = self._request(
            "GET", path, params={"transaction": transaction} if transaction else None,
            statuses=(200, 404),
        )
        return None if status == 404 else _document(value)

    def get_effect(self, intent_id: str) -> dict[str, Any] | None:
        return self._get(self._effect_name(intent_id))

    def reserve(self, *, intent_id: str, order_sha256: str, authorization_sha256: str,
                instrument_preflight_sha256: str, venue: str, quote_value_usd: float,
                now_ms: int | None = None) -> dict[str, Any]:
        current = int(time.time() * 1000) if now_ms is None else now_ms
        if any(not _HEX64.fullmatch(value) for value in (
                order_sha256, authorization_sha256, instrument_preflight_sha256)):
            raise LedgerError("ledger_commitment_invalid")
        if venue not in {"alpaca", "binance", "capital", "kraken"}:
            raise LedgerError("ledger_venue_invalid")
        if not math.isfinite(quote_value_usd) or quote_value_usd <= 0:
            raise LedgerError("ledger_order_budget_invalid")
        effect_name = self._effect_name(intent_id)
        budget_name = self._budget_name(current)
        for _ in range(5):
            transaction = self._begin()
            existing = self._get(effect_name, transaction)
            if existing is not None:
                if (existing.get("order_sha256") != order_sha256
                        or existing.get("authorization_sha256") != authorization_sha256
                        or existing.get("instrument_preflight_sha256") != instrument_preflight_sha256):
                    raise LedgerError("ledger_effect_commitment_mismatch")
                return {**existing, "created": False}
            budget = self._get(budget_name, transaction)
            spent = float(budget.get("reserved_usd", 0.0)) if budget else 0.0
            if not math.isfinite(spent) or spent < 0 or spent + quote_value_usd > self.daily_budget_usd + 1e-9:
                raise LedgerError("daily_budget_exceeded")
            effect = {
                "schema": "aureon.cloud-trade-effect.v1", "intent_id": intent_id,
                "order_sha256": order_sha256, "authorization_sha256": authorization_sha256,
                "instrument_preflight_sha256": instrument_preflight_sha256,
                "venue": venue, "quote_value_usd": quote_value_usd,
                "state": "claimed", "claimed_at_ms": current, "updated_at_ms": current,
                "provider_order_id": None, "provider_client_order_id": None,
                "provider_status": None, "provider_readback_sha256": None,
            }
            budget_fields = {
                "schema": "aureon.cloud-trade-daily-budget.v1",
                "day": budget_name.rsplit("/", 1)[-1], "limit_usd": self.daily_budget_usd,
                "reserved_usd": spent + quote_value_usd, "updated_at_ms": current,
            }
            writes: list[dict[str, Any]] = [{
                "update": {"name": effect_name, "fields": _fields(effect)},
                "currentDocument": {"exists": False},
            }, {
                "update": {"name": budget_name, "fields": _fields(budget_fields)},
                "currentDocument": ({"updateTime": budget["update_time"]} if budget else {"exists": False}),
            }]
            try:
                _, committed = self._request(
                    "POST", "/documents:commit", body={"writes": writes, "transaction": transaction},
                )
            except LedgerError as exc:
                if str(exc) in {"ledger_http_status_409", "ledger_http_status_412"}:
                    continue
                raise
            results = committed.get("writeResults")
            if not isinstance(results, list) or len(results) != 2 or not isinstance(results[0], Mapping):
                raise LedgerError("ledger_commit_response_invalid")
            update_time = results[0].get("updateTime")
            if not isinstance(update_time, str):
                raise LedgerError("ledger_commit_response_invalid")
            return {**effect, "update_time": update_time, "created": True}
        raise LedgerError("ledger_transaction_contention")

    def transition(self, intent_id: str, *, expected_update_time: str, state: str,
                   now_ms: int | None = None, **evidence: Any) -> dict[str, Any]:
        if state not in _STATE or not isinstance(expected_update_time, str):
            raise LedgerError("ledger_transition_invalid")
        allowed = {"provider_order_id", "provider_client_order_id", "provider_status", "provider_readback_sha256"}
        if set(evidence) - allowed:
            raise LedgerError("ledger_transition_field_invalid")
        if "provider_readback_sha256" in evidence and evidence["provider_readback_sha256"] is not None and not _HEX64.fullmatch(evidence["provider_readback_sha256"]):
            raise LedgerError("ledger_provider_readback_invalid")
        fields = {"state": state, "updated_at_ms": int(time.time() * 1000) if now_ms is None else now_ms, **evidence}
        path = "/documents/aureon_trade_effects/" + quote(intent_id, safe="")
        params = {
            "currentDocument.updateTime": expected_update_time,
            "updateMask.fieldPaths": list(fields),
        }
        _, value = self._request("PATCH", path, body={"fields": _fields(fields)}, params=params)
        return _document(value)


__all__ = ["FirestoreLedger", "LedgerError"]
