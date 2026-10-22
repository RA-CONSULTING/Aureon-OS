"""QGITA Autonomous Binance trading bot.

This module implements a minimal-but-complete version of the architecture
outlined in the repository docs for driving a Binance spot trading strategy.
The bot listens to kline data over a WebSocket feed, detects
Fibonacci-Tightened Curvature Points (FTCPs), validates them with a simplified
Lighthouse consensus routine, and places trades when the consensus passes a
configurable threshold.

The default configuration keeps the bot in paper-trading mode so it can be
safely experimented with. Live trading can be enabled via the command line or
environment variables after carefully reviewing the risk controls.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import logging
import os
import signal
import sys
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone

import numbers
from decimal import Decimal

import numpy as np

from typing import Any, Deque, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

try:  # pragma: no cover - optional dependency for live streaming
    import requests
except Exception:  # pragma: no cover - optional dependency
    requests = None  # type: ignore[assignment]


try:  # pragma: no cover - optional dependency for live streaming
    import websocket
except ImportError:  # pragma: no cover - websocket support is optional
    websocket = None  # type: ignore


LOGGER = logging.getLogger("qgita.bot")

DEFAULT_WS_URL = "wss://stream.binance.com:9443/ws"
DEFAULT_REST_URL = "https://api.binance.com"


def _timestamp_ms() -> int:
    """Return the current timestamp in milliseconds."""

    return int(time.time() * 1000)


def _hmac_signature(secret: str, params: Dict[str, str]) -> str:
    """Return the Binance-compatible HMAC SHA256 signature."""

    message = "&".join(f"{key}={value}" for key, value in params.items())
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def _parse_optional_bool(value: Optional[str]) -> Optional[bool]:
    """Parse an optional boolean value from a string."""

    if value is None:
        return None
    lowered = value.lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return None


def _normalize_streams(streams: Iterable[str]) -> List[str]:
    """Normalize and validate Binance stream identifiers."""

    normalized: List[str] = []
    for stream in streams:
        cleaned = stream.strip()
        if not cleaned:
            continue
        normalized.append(cleaned.lower())
    if not normalized:
        raise ValueError("At least one valid stream identifier must be provided")
    return normalized


def _parse_streams(value: Optional[str]) -> Optional[List[str]]:
    """Parse ``value`` into a list of normalized stream identifiers."""

    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None

    # Allow comma, semicolon, or whitespace separated values.
    parts = raw.replace(";", ",").replace("\n", " ").split(",")
    tokens: List[str] = []
    for part in parts:
        for token in part.strip().split():
            if token:
                tokens.append(token)

    if not tokens:
        return None

    try:
        return _normalize_streams(tokens)
    except ValueError:
        return None


def _float(value: Optional[str], default: float) -> float:
    """Return ``value`` parsed as a float or ``default`` if parsing fails."""

    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _float_optional(value: Optional[str], default: Optional[float] = None) -> Optional[float]:
    """Return ``value`` parsed as a float or ``default`` if unset/invalid."""

    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_symbol_status(value: Optional[str]) -> Optional[str]:
    """Normalize symbol status strings used in public ticker queries."""

    if value is None:
        return None
    candidate = value.strip().upper()
    return candidate or None


def _ensure_requests() -> None:
    """Ensure the optional ``requests`` dependency is available."""

    if requests is None:  # type: ignore[name-defined]
        raise RuntimeError(
            "The `requests` package is required for Binance REST calls. "
            "Install it with `pip install requests`."
        )





class BinanceAPIError(RuntimeError):
    """Exception raised when Binance returns an error payload."""

    def __init__(self, status: int, message: str, *, payload: Any | None = None):
        message = message or "Unknown Binance API error"
        super().__init__(f"Binance API error (status {status}): {message}")
        self.status = status
        self.payload = payload


@dataclass
class TradingConfig:
    """Runtime configuration for the trading bot."""

    api_key: str = ""
    api_secret: str = ""
    symbol: str = "BTCUSDT"
    symbol_status: Optional[str] = "TRADING"
    base_url: str = DEFAULT_REST_URL
    ws_url: str = DEFAULT_WS_URL
    position_size_usdt: float = 100.0
    max_position_size_usdt: float = 500.0
    stop_loss_percent: float = 2.0
    take_profit_percent: float = 4.0
    window_size: int = 144
    curvature_threshold: float = 0.75
    lighthouse_threshold: float = 0.7
    max_daily_loss_usdt: float = 200.0
    max_trades_per_day: int = 10
    paper_trading: bool = True
    price_precision: int = 2
    quantity_precision: int = 6
    momentum_window: int = 20
    volatility_window: int = 20
    ws_kline_interval: str = "1m"
    ws_streams: Optional[List[str]] = None
    ws_use_combined: Optional[bool] = None
    ws_time_unit: Optional[str] = None
    ws_ping_interval: Optional[float] = 20.0
    ws_ping_timeout: float = 10.0

    @classmethod
    def from_env(cls) -> "TradingConfig":
        """Create a configuration instance using environment variables."""

        def _bool(value: Optional[str], default: bool) -> bool:
            if value is None:
                return default
            lowered = value.lower()
            if lowered in {"1", "true", "yes", "on"}:
                return True
            if lowered in {"0", "false", "no", "off"}:
                return False
            return default


        raw_status = os.getenv("QGITA_SYMBOL_STATUS")
        _symbol_status = raw_status.upper() if raw_status else None

        return cls(
            api_key=os.getenv("BINANCE_API_KEY", ""),
            api_secret=os.getenv("BINANCE_API_SECRET", ""),
            symbol=os.getenv("QGITA_SYMBOL", "BTCUSDT").upper(),
            symbol_status=_parse_symbol_status(os.getenv("QGITA_SYMBOL_STATUS")),
            base_url=os.getenv("QGITA_BINANCE_URL", DEFAULT_REST_URL),
            ws_url=os.getenv("QGITA_BINANCE_WS", DEFAULT_WS_URL),
            position_size_usdt=float(os.getenv("QGITA_POSITION_SIZE", "100")),
            max_position_size_usdt=float(
                os.getenv("QGITA_MAX_POSITION_SIZE", "500")
            ),
            stop_loss_percent=float(os.getenv("QGITA_STOP_LOSS", "2")),
            take_profit_percent=float(os.getenv("QGITA_TAKE_PROFIT", "4")),
            window_size=int(os.getenv("QGITA_WINDOW_SIZE", "144")),
            curvature_threshold=float(
                os.getenv("QGITA_CURVATURE_THRESHOLD", "0.75")
            ),
            lighthouse_threshold=float(
                os.getenv("QGITA_LIGHTHOUSE_THRESHOLD", "0.7")
            ),
            max_daily_loss_usdt=float(os.getenv("QGITA_MAX_DAILY_LOSS", "200")),
            max_trades_per_day=int(os.getenv("QGITA_MAX_TRADES", "10")),
            paper_trading=_bool(os.getenv("QGITA_PAPER_TRADING"), True),
            price_precision=int(os.getenv("QGITA_PRICE_PRECISION", "2")),
            quantity_precision=int(os.getenv("QGITA_QUANTITY_PRECISION", "6")),
            momentum_window=int(os.getenv("QGITA_MOMENTUM_WINDOW", "20")),
            volatility_window=int(os.getenv("QGITA_VOLATILITY_WINDOW", "20")),
            ws_kline_interval=os.getenv("QGITA_WS_KLINE_INTERVAL", "1m"),
            ws_streams=_parse_streams(os.getenv("QGITA_WS_STREAMS")),
            ws_use_combined=_parse_optional_bool(os.getenv("QGITA_WS_COMBINED")),
            ws_time_unit=os.getenv("QGITA_WS_TIME_UNIT"),
            ws_ping_interval=_float_optional(
                os.getenv("QGITA_WS_PING_INTERVAL"), 20.0
            ),
            ws_ping_timeout=_float(os.getenv("QGITA_WS_PING_TIMEOUT"), 10.0),
        )






def resolve_streams(
    config: TradingConfig, streams: Optional[Iterable[str]] = None
) -> List[str]:
    """Return the effective Binance stream identifiers for ``config``."""

    if streams is not None:
        candidates = list(streams)
    elif config.ws_streams is not None:
        candidates = list(config.ws_streams)
    else:
        symbol = (config.symbol or "BTCUSDT").strip().lower()
        interval = (config.ws_kline_interval or "1m").strip()
        return [f"{symbol}@kline_{interval}"]

    return _normalize_streams(candidates)


def build_websocket_stream_url(
    config: TradingConfig, streams: Optional[Iterable[str]] = None
) -> str:
    """Construct the Binance WebSocket URL for the selected ``streams``."""

    resolved = resolve_streams(config, streams)
    use_combined = config.ws_use_combined
    if use_combined is None:
        use_combined = len(resolved) > 1

    base = config.ws_url.rstrip('/')

    def _strip_suffix(text: str, suffix: str) -> str:
        return text[: -len(suffix)] if text.endswith(suffix) else text

    if use_combined:
        base = _strip_suffix(base, '/ws').rstrip('/')
        if not base.endswith('/stream'):
            base = f"{base}/stream"
        query = f"streams={'/'.join(resolved)}"
        if config.ws_time_unit:
            query += f"&timeUnit={config.ws_time_unit}"
        return f"{base}?{query}"

    base = _strip_suffix(base, '/stream').rstrip('/')
    if not base.endswith('/ws'):
        base = f"{base}/ws"
    stream = resolved[0]
    url = f"{base}/{stream}"
    if config.ws_time_unit:
        separator = '&' if '?' in url else '?'
        url = f"{url}{separator}timeUnit={config.ws_time_unit}"
    return url


class BinanceAPIError(RuntimeError):
    """Exception raised when the Binance REST API returns an error."""

    def __init__(self, status: int, message: str, *, payload: Any | None = None):
        detail = message or "Binance API request failed"
        super().__init__(f"HTTP {status}: {detail}")
        self.status = status
        self.payload = payload


class BinanceRESTClient:

    """Lightweight REST client for interacting with Binance."""

    def __init__(self, config: TradingConfig):
        self.config = config
        self.last_rate_limits: List[dict] | None = None

    def _headers(self) -> Dict[str, str]:
        return {"X-MBX-APIKEY": self.config.api_key}

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        data: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Any:
        _ensure_requests()
        request_headers: Dict[str, str] = dict(self._headers())
        if headers:
            request_headers.update(headers)

        response = requests.request(
            method,
            f"{self.config.base_url}{path}",
            params=params,
            data=data,
            headers=request_headers,
            timeout=10,
        )
        return self._parse_response(response)

    def _parse_response(self, response: Any) -> Any:
        self.last_rate_limits = None
        try:
            payload = response.json()
        except ValueError as exc:
            text = getattr(response, "text", "")
            raise BinanceAPIError(
                response.status_code,
                "Invalid JSON response",
                payload=text or None,
            ) from exc

        if isinstance(payload, Mapping):
            rate_limits = payload.get("rateLimits")
            if isinstance(rate_limits, list):
                self.last_rate_limits = rate_limits
            elif "rateLimits" in payload:
                self.last_rate_limits = None

            is_enveloped = any(
                key in payload for key in ("result", "error", "status", "rateLimits", "id")
            )
            if is_enveloped:
                status_value = payload.get("status")
                status_code = response.status_code
                if isinstance(status_value, numbers.Integral):
                    status_code = int(status_value)
                elif isinstance(status_value, str):
                    try:
                        status_code = int(status_value)
                    except ValueError:
                        pass

                error_obj = payload.get("error")
                if status_code >= 400 or error_obj is not None:
                    message = ""
                    if isinstance(error_obj, Mapping):
                        for key in ("msg", "message", "error"):
                            value = error_obj.get(key)
                            if isinstance(value, str):
                                message = value
                                break
                        if not message and "code" in error_obj:
                            message = str(error_obj["code"])
                    elif isinstance(error_obj, str):
                        message = error_obj

                    if not message and isinstance(payload.get("msg"), str):
                        message = str(payload["msg"])
                    if not message and isinstance(payload.get("message"), str):
                        message = str(payload["message"])

                    raise BinanceAPIError(
                        status_code,
                        message or "Binance API request failed",
                        payload=payload,
                    )

                if "result" in payload:
                    return payload["result"]

        if response.status_code >= 400:
            message = ""
            if isinstance(payload, Mapping):
                for key in ("msg", "message", "error"):
                    value = payload.get(key)
                    if isinstance(value, str):
                        message = value
                        break
                if not message and "code" in payload:
                    message = str(payload["code"])
            else:
                message = str(payload)

            raise BinanceAPIError(
                response.status_code,
                message or "Binance API request failed",
                payload=payload,
            )

        return payload

    def _signed_request(
        self,
        method: str,
        path: str,
        params: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        if not self.config.api_secret:
            raise RuntimeError(
                "Binance API secret is required for signed requests"
            )

        query: Dict[str, Any] = {}
        if params:
            query.update(params)
        query.setdefault("timestamp", _timestamp_ms())
        query.setdefault("recvWindow", 5000)

        str_params: Dict[str, str] = {key: str(value) for key, value in query.items()}
        signature = _hmac_signature(self.config.api_secret, str_params)
        str_params["signature"] = signature
        return self._request(method, path, params=str_params)


    def _build_prefixed_params(
        self, prefix: str, options: Optional[Mapping[str, Any]]
    ) -> Dict[str, Any]:
        if not options:
            return {}

        suffix_map = {
            "client_order_id": "ClientOrderId",
            "iceberg_qty": "IcebergQty",
            "price": "Price",
            "stop_price": "StopPrice",
            "trailing_delta": "TrailingDelta",
            "time_in_force": "TimeInForce",
            "strategy_id": "StrategyId",
            "strategy_type": "StrategyType",
            "peg_price_type": "PegPriceType",
            "peg_offset_type": "PegOffsetType",
            "peg_offset_value": "PegOffsetValue",
            "side": "Side",
            "type": "Type",
            "quantity": "Quantity",
            "stop_limit_price": "StopLimitPrice",
            "stop_limit_time_in_force": "StopLimitTimeInForce",
        }

        formatted: Dict[str, Any] = {}
        for key, value in options.items():
            if value is None:
                continue
            suffix = suffix_map.get(key)
            if suffix is None:
                suffix = "".join(part.capitalize() for part in key.split("_"))
            formatted[f"{prefix}{suffix}"] = value
        return formatted

    def get_account(self) -> dict:
        """Return account information (signed endpoint)."""

        return self._signed_request("GET", "/api/v3/account", {})

    def get_price(
        self,
        symbol: Optional[str] = None,
        *,
        symbol_status: Optional[str] = None,
    ) -> float:
        """Return the latest spot price for ``symbol``."""


        symbol = symbol or self.config.symbol
        params: Dict[str, Any] = {"symbol": symbol}
        status = symbol_status
        if status is None:
            status = self.config.symbol_status
        if status:
            params["symbolStatus"] = status

        _ensure_requests()
        response = requests.get(
            f"{self.config.base_url}/api/v3/ticker/price",
            params=params,
            timeout=10,
        )
        payload = self._parse_response(response)
        if isinstance(payload, Mapping) and "price" in payload:
            return float(payload["price"])
        raise BinanceAPIError(
            response.status_code,
            "Missing price field in response",
            payload=payload,
        )

    def _new_order_payload(
        self,
        *,
        symbol: str,
        side: str,
        order_type: str,
        time_in_force: Optional[str] = None,
        quantity: Optional[float] = None,
        quote_order_qty: Optional[float] = None,
        price: Optional[float] = None,
        new_client_order_id: Optional[str] = None,
        strategy_id: Optional[int] = None,
        strategy_type: Optional[int] = None,
        stop_price: Optional[float] = None,
        trailing_delta: Optional[int] = None,
        iceberg_qty: Optional[float] = None,
        new_order_resp_type: Optional[str] = None,
        self_trade_prevention_mode: Optional[str] = None,
        peg_price_type: Optional[str] = None,
        peg_offset_value: Optional[int] = None,
        peg_offset_type: Optional[str] = None,
        recv_window: Optional[float] = None,
        extra_params: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
        }
        if time_in_force is not None:
            params["timeInForce"] = time_in_force
        if quantity is not None:
            params["quantity"] = quantity
        if quote_order_qty is not None:
            params["quoteOrderQty"] = quote_order_qty
        if price is not None:
            params["price"] = price
        if new_client_order_id is not None:
            params["newClientOrderId"] = new_client_order_id
        if strategy_id is not None:
            params["strategyId"] = strategy_id
        if strategy_type is not None:
            params["strategyType"] = strategy_type
        if stop_price is not None:
            params["stopPrice"] = stop_price
        if trailing_delta is not None:
            params["trailingDelta"] = trailing_delta
        if iceberg_qty is not None:
            params["icebergQty"] = iceberg_qty
        if new_order_resp_type is not None:
            params["newOrderRespType"] = new_order_resp_type
        if self_trade_prevention_mode is not None:
            params["selfTradePreventionMode"] = self_trade_prevention_mode
        if peg_price_type is not None:
            params["pegPriceType"] = peg_price_type
        if peg_offset_value is not None:
            params["pegOffsetValue"] = peg_offset_value
        if peg_offset_type is not None:
            params["pegOffsetType"] = peg_offset_type
        if recv_window is not None:
            params["recvWindow"] = recv_window
        if extra_params:
            params.update({str(k): v for k, v in extra_params.items()})
        return params

    def new_order(
        self,
        *,
        symbol: str,
        side: str,
        order_type: str,
        time_in_force: Optional[str] = None,
        quantity: Optional[float] = None,
        quote_order_qty: Optional[float] = None,
        price: Optional[float] = None,
        new_client_order_id: Optional[str] = None,
        strategy_id: Optional[int] = None,
        strategy_type: Optional[int] = None,
        stop_price: Optional[float] = None,
        trailing_delta: Optional[int] = None,
        iceberg_qty: Optional[float] = None,
        new_order_resp_type: Optional[str] = None,
        self_trade_prevention_mode: Optional[str] = None,
        peg_price_type: Optional[str] = None,
        peg_offset_value: Optional[int] = None,
        peg_offset_type: Optional[str] = None,
        recv_window: Optional[float] = None,
        extra_params: Optional[Mapping[str, Any]] = None,
    ) -> dict:
        params = self._new_order_payload(
            symbol=symbol,
            side=side,
            order_type=order_type,
            time_in_force=time_in_force,
            quantity=quantity,
            quote_order_qty=quote_order_qty,
            price=price,
            new_client_order_id=new_client_order_id,
            strategy_id=strategy_id,
            strategy_type=strategy_type,
            stop_price=stop_price,
            trailing_delta=trailing_delta,
            iceberg_qty=iceberg_qty,
            new_order_resp_type=new_order_resp_type,
            self_trade_prevention_mode=self_trade_prevention_mode,
            peg_price_type=peg_price_type,
            peg_offset_value=peg_offset_value,
            peg_offset_type=peg_offset_type,
            recv_window=recv_window,
            extra_params=extra_params,
        )
        return self._signed_request("POST", "/api/v3/order", params)

    def test_new_order(
        self,
        *,
        symbol: str,
        side: str,
        order_type: str,
        time_in_force: Optional[str] = None,
        quantity: Optional[float] = None,
        quote_order_qty: Optional[float] = None,
        price: Optional[float] = None,
        new_client_order_id: Optional[str] = None,
        strategy_id: Optional[int] = None,
        strategy_type: Optional[int] = None,
        stop_price: Optional[float] = None,
        trailing_delta: Optional[int] = None,
        iceberg_qty: Optional[float] = None,
        new_order_resp_type: Optional[str] = None,
        self_trade_prevention_mode: Optional[str] = None,
        peg_price_type: Optional[str] = None,
        peg_offset_value: Optional[int] = None,
        peg_offset_type: Optional[str] = None,
        recv_window: Optional[float] = None,
        compute_commission_rates: Optional[bool] = None,
        extra_params: Optional[Mapping[str, Any]] = None,
    ) -> dict:
        params = self._new_order_payload(
            symbol=symbol,
            side=side,
            order_type=order_type,
            time_in_force=time_in_force,
            quantity=quantity,
            quote_order_qty=quote_order_qty,
            price=price,
            new_client_order_id=new_client_order_id,
            strategy_id=strategy_id,
            strategy_type=strategy_type,
            stop_price=stop_price,
            trailing_delta=trailing_delta,
            iceberg_qty=iceberg_qty,
            new_order_resp_type=new_order_resp_type,
            self_trade_prevention_mode=self_trade_prevention_mode,
            peg_price_type=peg_price_type,
            peg_offset_value=peg_offset_value,
            peg_offset_type=peg_offset_type,
            recv_window=recv_window,
            extra_params=extra_params,
        )
        if compute_commission_rates is not None:
            params["computeCommissionRates"] = compute_commission_rates
        return self._signed_request("POST", "/api/v3/order/test", params)

    def place_order(
        self,
        *,
        symbol: Optional[str] = None,
        side: str,
        quantity: Optional[float] = None,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        time_in_force: Optional[str] = None,
        quote_order_qty: Optional[float] = None,
        extra_params: Optional[Mapping[str, Any]] = None,
    ) -> dict:
        """Convenience wrapper that mirrors the previous ``place_order`` API."""

        resolved_symbol = symbol or self.config.symbol
        return self.new_order(
            symbol=resolved_symbol,
            side=side,
            order_type=order_type,
            time_in_force=time_in_force,
            quantity=quantity,
            quote_order_qty=quote_order_qty,
            price=price,
            extra_params=extra_params,
        )

    def cancel_order(
        self,
        *,
        symbol: str,
        order_id: Optional[int] = None,
        orig_client_order_id: Optional[str] = None,
        new_client_order_id: Optional[str] = None,
        cancel_restrictions: Optional[str] = None,
        recv_window: Optional[float] = None,
        extra_params: Optional[Mapping[str, Any]] = None,
    ) -> dict:
        params: Dict[str, Any] = {"symbol": symbol}
        if order_id is not None:
            params["orderId"] = order_id
        if orig_client_order_id is not None:
            params["origClientOrderId"] = orig_client_order_id
        if new_client_order_id is not None:
            params["newClientOrderId"] = new_client_order_id
        if cancel_restrictions is not None:
            params["cancelRestrictions"] = cancel_restrictions
        if recv_window is not None:
            params["recvWindow"] = recv_window
        if extra_params:
            params.update({str(k): v for k, v in extra_params.items()})
        return self._signed_request("DELETE", "/api/v3/order", params)

    def cancel_all_open_orders(
        self,
        *,
        symbol: str,
        recv_window: Optional[float] = None,
        extra_params: Optional[Mapping[str, Any]] = None,
    ) -> dict:
        params: Dict[str, Any] = {"symbol": symbol}
        if recv_window is not None:
            params["recvWindow"] = recv_window
        if extra_params:
            params.update({str(k): v for k, v in extra_params.items()})
        return self._signed_request("DELETE", "/api/v3/openOrders", params)

    def cancel_replace_order(
        self,
        *,
        symbol: str,
        side: str,
        order_type: str,
        cancel_replace_mode: str,
        time_in_force: Optional[str] = None,
        quantity: Optional[float] = None,
        quote_order_qty: Optional[float] = None,
        price: Optional[float] = None,
        cancel_new_client_order_id: Optional[str] = None,
        cancel_orig_client_order_id: Optional[str] = None,
        cancel_order_id: Optional[int] = None,
        new_client_order_id: Optional[str] = None,
        strategy_id: Optional[int] = None,
        strategy_type: Optional[int] = None,
        stop_price: Optional[float] = None,
        trailing_delta: Optional[int] = None,
        iceberg_qty: Optional[float] = None,
        new_order_resp_type: Optional[str] = None,
        self_trade_prevention_mode: Optional[str] = None,
        cancel_restrictions: Optional[str] = None,
        order_rate_limit_exceeded_mode: Optional[str] = None,
        peg_price_type: Optional[str] = None,
        peg_offset_value: Optional[int] = None,
        peg_offset_type: Optional[str] = None,
        recv_window: Optional[float] = None,
        extra_params: Optional[Mapping[str, Any]] = None,
    ) -> dict:
        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "cancelReplaceMode": cancel_replace_mode,
        }
        if time_in_force is not None:
            params["timeInForce"] = time_in_force
        if quantity is not None:
            params["quantity"] = quantity
        if quote_order_qty is not None:
            params["quoteOrderQty"] = quote_order_qty
        if price is not None:
            params["price"] = price
        if cancel_new_client_order_id is not None:
            params["cancelNewClientOrderId"] = cancel_new_client_order_id
        if cancel_orig_client_order_id is not None:
            params["cancelOrigClientOrderId"] = cancel_orig_client_order_id
        if cancel_order_id is not None:
            params["cancelOrderId"] = cancel_order_id
        if new_client_order_id is not None:
            params["newClientOrderId"] = new_client_order_id
        if strategy_id is not None:
            params["strategyId"] = strategy_id
        if strategy_type is not None:
            params["strategyType"] = strategy_type
        if stop_price is not None:
            params["stopPrice"] = stop_price
        if trailing_delta is not None:
            params["trailingDelta"] = trailing_delta
        if iceberg_qty is not None:
            params["icebergQty"] = iceberg_qty
        if new_order_resp_type is not None:
            params["newOrderRespType"] = new_order_resp_type
        if self_trade_prevention_mode is not None:
            params["selfTradePreventionMode"] = self_trade_prevention_mode
        if cancel_restrictions is not None:
            params["cancelRestrictions"] = cancel_restrictions
        if order_rate_limit_exceeded_mode is not None:
            params["orderRateLimitExceededMode"] = order_rate_limit_exceeded_mode
        if peg_price_type is not None:
            params["pegPriceType"] = peg_price_type
        if peg_offset_value is not None:
            params["pegOffsetValue"] = peg_offset_value
        if peg_offset_type is not None:
            params["pegOffsetType"] = peg_offset_type
        if recv_window is not None:
            params["recvWindow"] = recv_window
        if extra_params:
            params.update({str(k): v for k, v in extra_params.items()})
        return self._signed_request("POST", "/api/v3/order/cancelReplace", params)

    def amend_order_keep_priority(
        self,
        *,
        symbol: str,
        new_qty: float,
        order_id: Optional[int] = None,
        orig_client_order_id: Optional[str] = None,
        new_client_order_id: Optional[str] = None,
        recv_window: Optional[float] = None,
        extra_params: Optional[Mapping[str, Any]] = None,
    ) -> dict:
        params: Dict[str, Any] = {"symbol": symbol, "newQty": new_qty}
        if order_id is not None:
            params["orderId"] = order_id
        if orig_client_order_id is not None:
            params["origClientOrderId"] = orig_client_order_id
        if new_client_order_id is not None:
            params["newClientOrderId"] = new_client_order_id
        if recv_window is not None:
            params["recvWindow"] = recv_window
        if extra_params:
            params.update({str(k): v for k, v in extra_params.items()})
        return self._signed_request(
            "PUT", "/api/v3/order/amend/keepPriority", params
        )

    def new_order_list_oco(
        self,
        *,
        symbol: str,
        side: str,
        quantity: float,
        above_type: str,
        below_type: str,
        list_client_order_id: Optional[str] = None,
        above_options: Optional[Mapping[str, Any]] = None,
        below_options: Optional[Mapping[str, Any]] = None,
        new_order_resp_type: Optional[str] = None,
        self_trade_prevention_mode: Optional[str] = None,
        recv_window: Optional[float] = None,
        extra_params: Optional[Mapping[str, Any]] = None,
    ) -> dict:
        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "aboveType": above_type,
            "belowType": below_type,
        }
        if list_client_order_id is not None:
            params["listClientOrderId"] = list_client_order_id
        params.update(self._build_prefixed_params("above", above_options))
        params.update(self._build_prefixed_params("below", below_options))
        if new_order_resp_type is not None:
            params["newOrderRespType"] = new_order_resp_type
        if self_trade_prevention_mode is not None:
            params["selfTradePreventionMode"] = self_trade_prevention_mode
        if recv_window is not None:
            params["recvWindow"] = recv_window
        if extra_params:
            params.update({str(k): v for k, v in extra_params.items()})
        return self._signed_request("POST", "/api/v3/orderList/oco", params)

    def new_order_list_oto(
        self,
        *,
        symbol: str,
        working_type: str,
        working_side: str,
        working_quantity: float,
        pending_type: str,
        pending_side: str,
        pending_quantity: float,
        list_client_order_id: Optional[str] = None,
        working_options: Optional[Mapping[str, Any]] = None,
        pending_options: Optional[Mapping[str, Any]] = None,
        new_order_resp_type: Optional[str] = None,
        self_trade_prevention_mode: Optional[str] = None,
        recv_window: Optional[float] = None,
        extra_params: Optional[Mapping[str, Any]] = None,
    ) -> dict:
        params: Dict[str, Any] = {
            "symbol": symbol,
            "workingType": working_type,
            "workingSide": working_side,
            "workingQuantity": working_quantity,
            "pendingType": pending_type,
            "pendingSide": pending_side,
            "pendingQuantity": pending_quantity,
        }
        if list_client_order_id is not None:
            params["listClientOrderId"] = list_client_order_id
        params.update(self._build_prefixed_params("working", working_options))
        params.update(self._build_prefixed_params("pending", pending_options))
        if new_order_resp_type is not None:
            params["newOrderRespType"] = new_order_resp_type
        if self_trade_prevention_mode is not None:
            params["selfTradePreventionMode"] = self_trade_prevention_mode
        if recv_window is not None:
            params["recvWindow"] = recv_window
        if extra_params:
            params.update({str(k): v for k, v in extra_params.items()})
        return self._signed_request("POST", "/api/v3/orderList/oto", params)

    def new_order_list_otoco(
        self,
        *,
        symbol: str,
        working_type: str,
        working_side: str,
        working_quantity: float,
        pending_side: str,
        pending_quantity: float,
        pending_above_type: str,
        pending_below_type: str,
        list_client_order_id: Optional[str] = None,
        working_options: Optional[Mapping[str, Any]] = None,
        pending_above_options: Optional[Mapping[str, Any]] = None,
        pending_below_options: Optional[Mapping[str, Any]] = None,
        new_order_resp_type: Optional[str] = None,
        self_trade_prevention_mode: Optional[str] = None,
        recv_window: Optional[float] = None,
        extra_params: Optional[Mapping[str, Any]] = None,
    ) -> dict:
        params: Dict[str, Any] = {
            "symbol": symbol,
            "workingType": working_type,
            "workingSide": working_side,
            "workingQuantity": working_quantity,
            "pendingSide": pending_side,
            "pendingQuantity": pending_quantity,
            "pendingAboveType": pending_above_type,
            "pendingBelowType": pending_below_type,
        }
        if list_client_order_id is not None:
            params["listClientOrderId"] = list_client_order_id
        params.update(self._build_prefixed_params("working", working_options))
        params.update(self._build_prefixed_params("pendingAbove", pending_above_options))
        params.update(self._build_prefixed_params("pendingBelow", pending_below_options))
        if new_order_resp_type is not None:
            params["newOrderRespType"] = new_order_resp_type
        if self_trade_prevention_mode is not None:
            params["selfTradePreventionMode"] = self_trade_prevention_mode
        if recv_window is not None:
            params["recvWindow"] = recv_window
        if extra_params:
            params.update({str(k): v for k, v in extra_params.items()})
        return self._signed_request("POST", "/api/v3/orderList/otoco", params)

    def cancel_order_list(
        self,
        *,
        symbol: str,
        order_list_id: Optional[int] = None,
        list_client_order_id: Optional[str] = None,
        new_client_order_id: Optional[str] = None,
        recv_window: Optional[float] = None,
        extra_params: Optional[Mapping[str, Any]] = None,
    ) -> dict:
        params: Dict[str, Any] = {"symbol": symbol}
        if order_list_id is not None:
            params["orderListId"] = order_list_id
        if list_client_order_id is not None:
            params["listClientOrderId"] = list_client_order_id
        if new_client_order_id is not None:
            params["newClientOrderId"] = new_client_order_id
        if recv_window is not None:
            params["recvWindow"] = recv_window
        if extra_params:
            params.update({str(k): v for k, v in extra_params.items()})
        return self._signed_request("DELETE", "/api/v3/orderList", params)

    def new_sor_order(
        self,
        *,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        time_in_force: Optional[str] = None,
        price: Optional[float] = None,
        new_client_order_id: Optional[str] = None,
        strategy_id: Optional[int] = None,
        strategy_type: Optional[int] = None,
        iceberg_qty: Optional[float] = None,
        new_order_resp_type: Optional[str] = None,
        self_trade_prevention_mode: Optional[str] = None,
        recv_window: Optional[float] = None,
        extra_params: Optional[Mapping[str, Any]] = None,
    ) -> dict:
        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }
        if time_in_force is not None:
            params["timeInForce"] = time_in_force
        if price is not None:
            params["price"] = price
        if new_client_order_id is not None:
            params["newClientOrderId"] = new_client_order_id
        if strategy_id is not None:
            params["strategyId"] = strategy_id
        if strategy_type is not None:
            params["strategyType"] = strategy_type
        if iceberg_qty is not None:
            params["icebergQty"] = iceberg_qty
        if new_order_resp_type is not None:
            params["newOrderRespType"] = new_order_resp_type
        if self_trade_prevention_mode is not None:
            params["selfTradePreventionMode"] = self_trade_prevention_mode
        if recv_window is not None:
            params["recvWindow"] = recv_window
        if extra_params:
            params.update({str(k): v for k, v in extra_params.items()})
        return self._signed_request("POST", "/api/v3/sor/order", params)

    def test_new_sor_order(
        self,
        *,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        time_in_force: Optional[str] = None,
        price: Optional[float] = None,
        new_client_order_id: Optional[str] = None,
        strategy_id: Optional[int] = None,
        strategy_type: Optional[int] = None,
        iceberg_qty: Optional[float] = None,
        new_order_resp_type: Optional[str] = None,
        self_trade_prevention_mode: Optional[str] = None,
        recv_window: Optional[float] = None,
        compute_commission_rates: Optional[bool] = None,
        extra_params: Optional[Mapping[str, Any]] = None,
    ) -> dict:
        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }
        if time_in_force is not None:
            params["timeInForce"] = time_in_force
        if price is not None:
            params["price"] = price
        if new_client_order_id is not None:
            params["newClientOrderId"] = new_client_order_id
        if strategy_id is not None:
            params["strategyId"] = strategy_id
        if strategy_type is not None:
            params["strategyType"] = strategy_type
        if iceberg_qty is not None:
            params["icebergQty"] = iceberg_qty
        if new_order_resp_type is not None:
            params["newOrderRespType"] = new_order_resp_type
        if self_trade_prevention_mode is not None:
            params["selfTradePreventionMode"] = self_trade_prevention_mode
        if recv_window is not None:
            params["recvWindow"] = recv_window
        if compute_commission_rates is not None:
            params["computeCommissionRates"] = compute_commission_rates
        if extra_params:
            params.update({str(k): v for k, v in extra_params.items()})
        return self._signed_request("POST", "/api/v3/sor/order/test", params)


def resolve_streams(config: TradingConfig) -> List[str]:
    """Return the WebSocket stream identifiers for ``config``."""

    if config.ws_streams:
        streams = _normalize_streams(config.ws_streams)
        if not streams:
            raise ValueError("At least one valid stream identifier must be provided")
        return streams

    symbol = (config.symbol or "BTCUSDT").lower()
    interval = config.ws_kline_interval or "1m"
    return [f"{symbol}@kline_{interval}"]


def _resolve_ws_endpoint(base_url: str, *, combined: bool) -> str:
    trimmed = (base_url or DEFAULT_WS_URL).rstrip("/")
    if combined:
        if trimmed.endswith("/ws"):
            trimmed = trimmed[:-3]
        if not trimmed.endswith("/stream"):
            trimmed = f"{trimmed}/stream"
        return trimmed

    if trimmed.endswith("/stream"):
        trimmed = trimmed[:-7]
    if not trimmed.endswith("/ws"):
        trimmed = f"{trimmed}/ws"
    return trimmed


def build_websocket_stream_url(
    config: TradingConfig, streams: Optional[Sequence[str]] = None
) -> str:
    """Build the Binance WebSocket URL respecting combined stream options."""

    if streams is None:
        resolved = resolve_streams(config)
    else:
        resolved = _normalize_streams(streams)

    if not resolved:
        raise ValueError("At least one stream is required")

    use_combined = config.ws_use_combined
    if use_combined is None:
        use_combined = len(resolved) > 1

    endpoint = _resolve_ws_endpoint(config.ws_url or DEFAULT_WS_URL, combined=use_combined)

    time_unit = config.ws_time_unit.strip() if config.ws_time_unit else ""

    if use_combined:
        query = "streams=" + "/".join(resolved)
        if time_unit:
            query += f"&timeUnit={time_unit}"
        return f"{endpoint}?{query}"

    url = f"{endpoint}/{resolved[0]}"
    if time_unit:
        url += f"?timeUnit={time_unit}"
    return url


class PaperExchange:
    """Simple in-memory ledger that emulates fills for testing."""

    def __init__(self, config: TradingConfig):
        self.config = config
        self.fills: List[dict] = []

    def place_order(
        self, *, symbol: Optional[str] = None, side: str, quantity: float, price: float
    ) -> dict:
        symbol = symbol or self.config.symbol
        fill = {
            "symbol": symbol,
            "side": side,
            "quantity": round(quantity, self.config.quantity_precision),
            "price": round(price, self.config.price_precision),
            "timestamp": _timestamp_ms(),
            "orderId": f"PAPER_{len(self.fills) + 1}",
            "status": "FILLED",
        }
        self.fills.append(fill)
        LOGGER.info(
            "📝 PAPER TRADE – %s %s %s @ %s",
            side,
            fill["quantity"],
            symbol,
            fill["price"],
        )
        return fill


class QGITADetector:
    """Detect FTCPs and derive Lighthouse consensus signals."""

    def __init__(self, config: TradingConfig):
        self.config = config
        self.price_buffer: Deque[float] = deque(maxlen=config.window_size)
        self.time_buffer: Deque[float] = deque(maxlen=config.window_size)
        self._fibonacci_lattice = self._build_fib_lattice()

    def _build_fib_lattice(self) -> List[int]:
        lattice = [1, 1]
        while lattice[-1] < self.config.window_size:
            lattice.append(lattice[-1] + lattice[-2])
        return [value for value in lattice if value < self.config.window_size]

    def add_price(self, price: float, timestamp: float) -> None:
        self.price_buffer.append(price)
        self.time_buffer.append(timestamp)

    def _curvature(self, prices: np.ndarray) -> np.ndarray:
        if prices.size < 3:
            return np.zeros_like(prices)
        dx = np.gradient(prices)
        ddx = np.gradient(dx)
        denominator = np.power(1 + np.square(dx), 1.5)
        denominator[denominator == 0] = np.finfo(float).eps
        return np.abs(ddx) / denominator

    def detect_ftcps(self) -> List[dict]:
        if len(self.price_buffer) < self.config.window_size:
            return []

        prices = np.asarray(self.price_buffer, dtype=float)
        curvature = self._curvature(prices)
        if not np.any(curvature):
            return []

        threshold = np.percentile(
            curvature, self.config.curvature_threshold * 100.0
        )
        ftcps: List[dict] = []
        for fib_idx in self._fibonacci_lattice:
            if fib_idx >= curvature.size:
                continue
            if curvature[fib_idx] <= threshold:
                continue
            ftcps.append(
                {
                    "index": fib_idx,
                    "curvature": float(curvature[fib_idx]),
                    "price": float(prices[fib_idx]),
                    "timestamp": float(self.time_buffer[fib_idx]),
                }
            )
        return ftcps

    def lighthouse_consensus(self, ftcps: Iterable[dict]) -> Optional[dict]:
        ftcps = list(ftcps)
        if not ftcps:
            return None

        prices = np.asarray(self.price_buffer, dtype=float)
        curvature = self._curvature(prices)
        latest = ftcps[-1]
        curvature_strength = float(latest["curvature"] / (np.max(curvature) or 1.0))

        momentum_window = min(self.config.momentum_window, len(prices) - 1)
        if momentum_window < 2:
            return None
        momentum = (prices[-1] - prices[-momentum_window]) / prices[-momentum_window]
        momentum_score = min(abs(momentum) * 10.0, 1.0)

        vol_window = min(self.config.volatility_window, len(prices))
        if vol_window < 3:
            return None
        window_slice = prices[-vol_window:]
        volatility = float(np.std(window_slice))
        mean_price = float(np.mean(window_slice)) or 1.0
        volatility_score = min(volatility / mean_price * 100.0, 1.0)

        consensus = (curvature_strength + momentum_score + volatility_score) / 3.0
        if consensus < self.config.lighthouse_threshold:
            return None

        signal_side = "BUY" if momentum >= 0 else "SELL"
        return {
            "signal": signal_side,
            "consensus": float(consensus),
            "price": float(prices[-1]),
            "timestamp": float(self.time_buffer[-1]),
        }


class Position:
    """Container tracking an open position."""

    def __init__(self, *, side: str, entry_price: float, quantity: float, config: TradingConfig):
        self.side = side
        self.entry_price = entry_price
        self.quantity = quantity
        self.stop_loss = (
            entry_price * (1 - config.stop_loss_percent / 100.0)
            if side == "LONG"
            else entry_price * (1 + config.stop_loss_percent / 100.0)
        )
        self.take_profit = (
            entry_price * (1 + config.take_profit_percent / 100.0)
            if side == "LONG"
            else entry_price * (1 - config.take_profit_percent / 100.0)
        )


class QGITATradingBot:
    """Trading bot that wraps the detector and exchange interface."""

    def __init__(self, config: TradingConfig):
        self.config = config
        self.detector = QGITADetector(config)
        self.rest_client = BinanceRESTClient(config)
        self.paper_exchange = PaperExchange(config) if config.paper_trading else None
        self.position: Optional[Position] = None
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.last_reset = datetime.now(timezone.utc).date()

    # ------------------------------------------------------------------
    # Risk management helpers
    # ------------------------------------------------------------------
    def _reset_daily_stats_if_needed(self) -> None:
        today = datetime.now(timezone.utc).date()
        if today != self.last_reset:
            LOGGER.info("📅 Daily stats reset for %s", today)
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.last_reset = today

    def _check_risk_limits(self) -> bool:
        self._reset_daily_stats_if_needed()
        if abs(self.daily_pnl) >= self.config.max_daily_loss_usdt:
            LOGGER.warning("🛑 Daily loss limit reached: %.2f", self.daily_pnl)
            return False
        if self.daily_trades >= self.config.max_trades_per_day:
            LOGGER.warning("🛑 Daily trade limit reached: %s", self.daily_trades)
            return False
        return True

    # ------------------------------------------------------------------
    # Exchange helpers
    # ------------------------------------------------------------------
    def _place_order(self, side: str, quantity: float, price: float) -> dict:
        if self.config.paper_trading:
            assert self.paper_exchange is not None
            return self.paper_exchange.place_order(
                side=side, quantity=quantity, price=price
            )
        return self.rest_client.place_order(side=side, quantity=quantity)

    def _current_price(self) -> float:
        return self.rest_client.get_price(self.config.symbol)

    # ------------------------------------------------------------------
    # Position management
    # ------------------------------------------------------------------
    def _position_value(self, price: float) -> float:
        if not self.position:
            return 0.0
        return price * self.position.quantity

    def _within_exposure_limits(self, price: float, quantity: float) -> bool:
        exposure = price * quantity
        if exposure > self.config.max_position_size_usdt:
            LOGGER.warning(
                "Exposure %.2f exceeds max %.2f", exposure, self.config.max_position_size_usdt
            )
            return False
        return True

    def _compute_quantity(self, price: float) -> float:
        quantity = self.config.position_size_usdt / price
        precision = self.config.quantity_precision
        return round(quantity, precision)

    def _record_trade(self, pnl: float) -> None:
        self.daily_pnl += pnl
        self.daily_trades += 1

    def _close_position(self, price: float) -> None:
        if not self.position:
            return
        exit_side = "SELL" if self.position.side == "LONG" else "BUY"
        self._place_order(exit_side, self.position.quantity, price)
        if self.position.side == "LONG":
            pnl = (price - self.position.entry_price) * self.position.quantity
        else:
            pnl = (self.position.entry_price - price) * self.position.quantity
        LOGGER.info(
            "🔒 Position closed: %s @ %.2f | PnL: %.2f",
            self.position.side,
            price,
            pnl,
        )
        self._record_trade(pnl)
        self.position = None

    def _open_position(self, signal: dict, price: float) -> None:
        quantity = self._compute_quantity(price)
        if not self._within_exposure_limits(price, quantity):
            return

        side = "BUY" if signal["signal"] == "BUY" else "SELL"
        self._place_order(side, quantity, price)

        side_label = "LONG" if side == "BUY" else "SHORT"
        self.position = Position(
            side=side_label, entry_price=price, quantity=quantity, config=self.config
        )
        LOGGER.info(
            "✅ %s opened: %s @ %.2f (consensus=%.2f)",
            side_label,
            quantity,
            price,
            signal["consensus"],
        )
        self.daily_trades += 1

    def _handle_stop_levels(self, price: float) -> None:
        if not self.position:
            return
        if self.position.side == "LONG":
            if price <= self.position.stop_loss:
                LOGGER.info("🛑 Stop loss triggered")
                self._close_position(price)
            elif price >= self.position.take_profit:
                LOGGER.info("🎯 Take profit hit")
                self._close_position(price)
        else:
            if price >= self.position.stop_loss:
                LOGGER.info("🛑 Stop loss triggered")
                self._close_position(price)
            elif price <= self.position.take_profit:
                LOGGER.info("🎯 Take profit hit")
                self._close_position(price)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    def on_price(self, price: float, timestamp: float) -> None:
        self.detector.add_price(price, timestamp)
        self._handle_stop_levels(price)

        ftcps = self.detector.detect_ftcps()
        if not ftcps:
            return
        signal = self.detector.lighthouse_consensus(ftcps)
        if not signal:
            return

        if not self._check_risk_limits():
            return

        if self.position and self.position.side == "LONG" and signal["signal"] == "SELL":
            self._close_position(price)
        elif self.position and self.position.side == "SHORT" and signal["signal"] == "BUY":
            self._close_position(price)

        if not self.position:
            self._open_position(signal, price)

    def account_report(self) -> Optional[dict]:
        if self.config.paper_trading:
            LOGGER.info("Paper trading mode – account report not available")
            return None
        report = self.rest_client.get_account()
        balances = [
            f"{balance['asset']}:{balance['free']}"
            for balance in report.get("balances", [])
            if float(balance.get("free", 0)) > 0
        ]
        LOGGER.info(
            "Account type=%s | canTrade=%s | balances=%s",
            report.get("accountType"),
            report.get("canTrade"),
            ", ".join(balances),
        )
        return report


class WebSocketRunner:
    """Wrapper around the Binance WebSocket stream."""

    def __init__(self, bot: QGITATradingBot):
        if websocket is None:  # pragma: no cover - runtime guard
            raise RuntimeError(
                "websocket-client is required for live streaming. Install it via "
                "`pip install websocket-client`."
            )
        self.bot = bot
        self.streams = resolve_streams(bot.config)
        self.url = build_websocket_stream_url(bot.config, self.streams)
        self._ws: Optional[websocket.WebSocketApp] = None

    def _on_open(self, ws: websocket.WebSocketApp) -> None:
        LOGGER.info(
            "🔌 WebSocket connected: %s | streams=%s",
            self.url,
            ",".join(self.streams),
        )

    def _on_close(self, ws: websocket.WebSocketApp, status_code: int, msg: str) -> None:
        LOGGER.warning("🔌 WebSocket closed (%s): %s", status_code, msg)

    def _on_error(self, ws: websocket.WebSocketApp, error: Exception) -> None:
        LOGGER.error("WebSocket error: %s", error)

    def _on_ping(self, ws: websocket.WebSocketApp, message: bytes) -> None:
        payload = message or b""
        try:
            ws.send(payload, opcode=websocket.ABNF.OPCODE_PONG)
            LOGGER.debug("Sent pong response (%d bytes)", len(payload))
        except Exception as exc:  # pragma: no cover - best effort pong
            LOGGER.warning("Failed to send pong: %s", exc)

    def _on_pong(self, ws: websocket.WebSocketApp, message: bytes) -> None:
        LOGGER.debug("Received pong (%d bytes)", len(message or b""))

    def _extract_price_event(self, payload: dict) -> Optional[Tuple[float, float]]:
        """Return a (price, timestamp) tuple if ``payload`` contains one."""

        try:
            kline = payload.get("k")
            if isinstance(kline, dict):
                if not kline.get("x"):
                    return None
                close_price = float(kline["c"])
                close_time = float(kline.get("T", payload.get("E", _timestamp_ms())))
                return close_price, close_time / 1000.0

            event_type = payload.get("e")
            if event_type in {"trade", "aggTrade"}:
                price = float(payload["p"])
                timestamp = float(payload.get("T", payload.get("E", _timestamp_ms())))
                return price, timestamp / 1000.0

            if event_type in {"24hrMiniTicker", "24hrTicker", "1hTicker", "4hTicker", "1dTicker"}:
                price = float(payload["c"])
                timestamp = float(payload.get("E", _timestamp_ms()))
                return price, timestamp / 1000.0

            if event_type == "avgPrice":
                price = float(payload["w"])
                timestamp = float(payload.get("T", payload.get("E", _timestamp_ms())))
                return price, timestamp / 1000.0

            if {
                "s",
                "b",
                "B",
                "a",
                "A",
            }.issubset(payload.keys()) and "e" not in payload:
                bid = float(payload["b"])
                ask = float(payload["a"])
                midpoint = (bid + ask) / 2.0
                timestamp = float(payload.get("E", _timestamp_ms()))
                return midpoint, timestamp / 1000.0
        except (KeyError, TypeError, ValueError):
            LOGGER.debug("Ignoring malformed payload: %s", payload)
        return None

    def _on_message(self, ws: websocket.WebSocketApp, message: str) -> None:
        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            LOGGER.debug("Ignoring non-JSON message: %s", message)
            return

        if isinstance(payload, dict) and {"stream", "data"}.issubset(payload.keys()):
            stream_name = payload.get("stream")
            payload = payload.get("data")
            LOGGER.debug("Combined stream update from %s", stream_name)

        if not isinstance(payload, dict):
            LOGGER.debug("Ignoring unexpected payload: %s", payload)
            return

        result = self._extract_price_event(payload)
        if result is None:
            LOGGER.debug("No price event extracted from payload: %s", payload)
            return

        price, timestamp = result
        self.bot.on_price(price, timestamp)

    def start(self) -> None:
        self._ws = websocket.WebSocketApp(
            self.url,
            on_open=self._on_open,
            on_close=self._on_close,
            on_error=self._on_error,
            on_message=self._on_message,
            on_ping=self._on_ping,
            on_pong=self._on_pong,
        )
        LOGGER.info("Starting price stream for %s", self.bot.config.symbol)
        ping_interval = self.bot.config.ws_ping_interval
        ping_timeout = self.bot.config.ws_ping_timeout
        if ping_interval is None or ping_interval <= 0:
            self._ws.run_forever(ping_interval=0, ping_timeout=ping_timeout)
        else:
            self._ws.run_forever(
                ping_interval=ping_interval,
                ping_timeout=ping_timeout,
            )


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the QGITA trading bot")
    parser.add_argument("--symbol", default=None, help="Trading pair, e.g., BTCUSDT")
    parser.add_argument("--live", action="store_true", help="Enable live trading")
    parser.add_argument(
        "--account-info",
        action="store_true",
        help="Fetch account info and exit (requires live credentials)",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Skip WebSocket streaming and fetch a single price update",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    configure_logging(args.verbose)

    config = TradingConfig.from_env()
    if args.symbol:
        config.symbol = args.symbol.upper()
    if args.live:
        config.paper_trading = False

    LOGGER.info("Starting QGITA bot | paper_trading=%s", config.paper_trading)
    bot = QGITATradingBot(config)

    if args.account_info:
        try:
            bot.account_report()
        except Exception as exc:  # pragma: no cover - network interaction
            LOGGER.error("Failed to fetch account info: %s", exc)
            return 1
        return 0

    if args.once:
        try:
            price = bot._current_price()
        except Exception as exc:  # pragma: no cover - network interaction
            LOGGER.error("Failed to fetch price: %s", exc)
            return 1
        now = datetime.now(timezone.utc).timestamp()
        bot.on_price(price, now)
        return 0

    runner: Optional[WebSocketRunner] = None

    def _handle_sigint(signum: int, frame) -> None:  # pragma: no cover - signal hook
        LOGGER.info("Received interrupt – shutting down")
        if runner and runner._ws is not None:
            try:
                runner._ws.close()
            except Exception:  # pragma: no cover - best effort close
                pass
        sys.exit(0)

    signal.signal(signal.SIGINT, _handle_sigint)

    runner = WebSocketRunner(bot)
    try:
        runner.start()
    except Exception as exc:  # pragma: no cover - runtime guard
        LOGGER.error("WebSocket runner stopped: %s", exc)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
