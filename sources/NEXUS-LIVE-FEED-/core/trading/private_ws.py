"""Utilities for constructing Binance WebSocket API request frames.



This module streamlines both flows by normalising parameters, performing light
validation, and optionally serialising the payload to JSON. The helpers remain
dependency-free so they can be imported from tests or utility scripts without
pulling in heavy third-party modules.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from typing import Any, Mapping, MutableMapping, Sequence


def _validate_method(method: str) -> str:
    if not isinstance(method, str) or not method:
        raise ValueError("method must be a non-empty string")
    return method


def _ensure_mapping(params: Mapping[str, Any] | None) -> MutableMapping[str, Any]:
    if params is None:
        return {}
    if not isinstance(params, Mapping):
        raise TypeError("params must be a mapping or None")
    return dict(params)


def _apply_return_rate_limits(
    params: MutableMapping[str, Any],
    return_rate_limits: bool | None,
) -> None:
    if return_rate_limits is None:
        return
    if not isinstance(return_rate_limits, bool):
        raise TypeError("return_rate_limits must be a boolean or None")
    params["returnRateLimits"] = return_rate_limits


def build_public_request(
    method: str,
    params: Mapping[str, Any] | None = None,
    *,
    request_id: str | int | None = None,
    as_text: bool = False,
) -> dict[str, Any] | str:
    """Construct a JSON-RPC frame for public WebSocket API requests."""

    _validate_method(method)

    payload = _ensure_mapping(params)
    frame: MutableMapping[str, Any] = {
        "id": request_id if request_id is not None else str(uuid.uuid4()),
        "method": method,
    }
    if payload:
        frame["params"] = dict(payload)
    if as_text:
        return json.dumps(frame, separators=(",", ":"))
    return dict(frame)


def ping_request(
    *,
    request_id: str | int | None = None,
    return_rate_limits: bool | None = None,
    as_text: bool = False,
) -> dict[str, Any] | str:
    """Return a ``ping`` request frame used to test connection health."""

    params: MutableMapping[str, Any] = {}
    _apply_return_rate_limits(params, return_rate_limits)
    return build_public_request(
        "ping",
        params if params else None,
        request_id=request_id,
        as_text=as_text,
    )


def server_time_request(
    *,
    request_id: str | int | None = None,
    return_rate_limits: bool | None = None,
    as_text: bool = False,
) -> dict[str, Any] | str:
    """Return a ``time`` request frame to query the server timestamp."""

    params: MutableMapping[str, Any] = {}
    _apply_return_rate_limits(params, return_rate_limits)
    return build_public_request(
        "time",
        params if params else None,
        request_id=request_id,
        as_text=as_text,
    )


_VALID_SYMBOL_STATUSES = {"TRADING", "HALT", "BREAK"}


def exchange_info_request(
    *,
    symbol: str | None = None,
    symbols: Sequence[str] | None = None,
    permissions: Sequence[str] | str | None = None,
    show_permission_sets: bool | None = None,
    symbol_status: str | None = None,
    return_rate_limits: bool | None = None,
    request_id: str | int | None = None,
    as_text: bool = False,
) -> dict[str, Any] | str:
    """Return an ``exchangeInfo`` request frame with validation applied."""

    filters = [value is not None for value in (symbol, symbols, permissions)]
    if sum(filters) > 1:
        raise ValueError("Specify only one of symbol, symbols, or permissions")

    if symbol_status is not None:
        if not isinstance(symbol_status, str):
            raise TypeError("symbol_status must be a string or None")
        if symbol_status not in _VALID_SYMBOL_STATUSES:
            valid = ", ".join(sorted(_VALID_SYMBOL_STATUSES))
            raise ValueError(f"symbol_status must be one of: {valid}")
        if symbol is not None or symbols is not None:
            raise ValueError("symbol_status cannot be combined with symbol or symbols")

    params: MutableMapping[str, Any] = {}
    if symbol is not None:
        if not isinstance(symbol, str) or not symbol:
            raise ValueError("symbol must be a non-empty string when provided")
        params["symbol"] = symbol

    if symbols is not None:
        if isinstance(symbols, (str, bytes)):
            raise TypeError("symbols must be a sequence of symbol strings")
        materialised = list(symbols)
        if not materialised:
            raise ValueError("symbols must contain at least one symbol when provided")
        params["symbols"] = materialised

    if permissions is not None:
        if isinstance(permissions, (str, bytes)):
            params["permissions"] = permissions
        else:
            materialised = list(permissions)
            if not materialised:
                raise ValueError("permissions must contain at least one permission when provided")
            params["permissions"] = materialised

    if show_permission_sets is not None:
        if not isinstance(show_permission_sets, bool):
            raise TypeError("show_permission_sets must be a boolean or None")
        params["showPermissionSets"] = show_permission_sets

    if symbol_status is not None:
        params["symbolStatus"] = symbol_status

    _apply_return_rate_limits(params, return_rate_limits)
    return build_public_request(
        "exchangeInfo",
        params if params else None,
        request_id=request_id,
        as_text=as_text,
    )


def _stringify(value: Any) -> str:
    """Convert ``value`` to a string suitable for signature generation."""

    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        raise ValueError("Cannot sign parameters containing null values")
    if isinstance(value, (int, float)):
        # Normalise integers/floats to remove locale specific formatting.
        return ("%f" % value).rstrip("0").rstrip(".") if isinstance(value, float) else str(value)
    return str(value)


def _canonical_query(params: Mapping[str, Any]) -> str:
    """Return the canonical ``key=value`` string used for signing.

    The API specification notes that parameter order is not significant, so we
    sort keys lexicographically to guarantee a deterministic signature.
    """

    if not isinstance(params, Mapping):  # pragma: no cover - defensive guard
        raise TypeError("params must be a mapping")

    items = []
    for key in sorted(params):
        value = params[key]
        items.append(f"{key}={_stringify(value)}")
    return "&".join(items)


def sign_params(params: Mapping[str, Any], secret: str) -> str:
    """Return the HMAC SHA-256 signature for ``params`` using ``secret``."""

    if not secret:
        raise ValueError("API secret is required to sign WebSocket requests")
    canonical = _canonical_query(params)
    signature = hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256)
    return signature.hexdigest()


def build_request_frame(
    method: str,
    params: Mapping[str, Any] | None,
    *,
    api_key: str,
    api_secret: str,
    request_id: str | int | None = None,
    timestamp_ms: int | None = None,
    as_text: bool = False,
) -> dict[str, Any] | str:
    """Construct a signed WebSocket request frame.

    Parameters
    ----------
    method:
        API method name, e.g. ``"order.place"`` or ``"v3/order.place"``.
    params:
        Mapping with the method parameters. A shallow copy is taken so the
        original mapping remains untouched.
    api_key / api_secret:
        Credentials used to authenticate the request.
    request_id:
        Optional identifier echoed back by the server. A UUID4 string is used
        when omitted.
    timestamp_ms:
        Optional timestamp override. When omitted, the current time is used.
    as_text:
        When ``True`` the frame is returned as a JSON encoded string ready to
        send over a text WebSocket frame. Otherwise the Python ``dict`` is
        returned.
    """

    if not api_key:
        raise ValueError("API key is required for private WebSocket requests")

    payload = _ensure_mapping(params)
    if timestamp_ms is None:
        timestamp_ms = int(time.time() * 1000)
    payload.setdefault("timestamp", timestamp_ms)

    if "signature" in payload:
        raise ValueError("Signature must not be pre-populated in params")

    if "apiKey" in payload and payload["apiKey"] != api_key:
        raise ValueError("API key in params does not match provided api_key")
    payload.setdefault("apiKey", api_key)

    signature = sign_params(payload, api_secret)
    payload_with_signature = dict(payload)
    payload_with_signature["signature"] = signature

    frame = {
        "id": request_id if request_id is not None else str(uuid.uuid4()),
        "method": method,
        "params": payload_with_signature,
    }

    if as_text:
        return json.dumps(frame, separators=(",", ":"))
    return frame




