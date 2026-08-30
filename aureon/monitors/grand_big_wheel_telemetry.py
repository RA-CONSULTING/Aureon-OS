#!/usr/bin/env python3
"""Read-only Grand Big Wheel market telemetry.

This diagnostic reports only fresh, two-sided provider quote receipts. It does
not create market observations, train a model, update Queen state, or persist
telemetry. Missing, stale, malformed, or one-sided evidence is returned as
explicit no_data.
"""

from __future__ import annotations

import json
import math
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional


DEFAULT_SYMBOLS = (
    "BTC/USD",
    "ETH/USD",
    "SOL/USD",
    "LINK/USD",
    "DOGE/USD",
)
REAL_TRUTH_STATUSES = frozenset({"real_observed", "real_derived"})
DEFAULT_MAX_QUOTE_AGE_SECONDS = 60.0
FUTURE_TOLERANCE_SECONDS = 5.0


def _finite_number(
    value: Any,
    *,
    positive: bool = False,
    nonnegative: bool = False,
) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    if positive and number <= 0.0:
        return None
    if nonnegative and number < 0.0:
        return None
    return number


def _epoch_seconds(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp /= 1000.0
        return timestamp if math.isfinite(timestamp) else None
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    numeric = _finite_number(text)
    if numeric is not None:
        return _epoch_seconds(numeric)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _no_data_receipt(
    symbol: str,
    reason: str,
    *,
    received_at: float,
    source_id: str,
) -> Dict[str, Any]:
    return {
        "symbol": symbol,
        "price": None,
        "bid": None,
        "ask": None,
        "volume": None,
        "change_pct": None,
        "source_id": source_id,
        "source_timestamp": None,
        "received_at": datetime.fromtimestamp(received_at, timezone.utc).isoformat(),
        "data_status": "no_data",
        "truth_status": "no_data",
        "reason": reason,
        "price_derivation": None,
        "generated_values": False,
        "eligible_for_analysis": False,
        "eligible_for_action": False,
    }


def normalize_quote_receipt(
    symbol: str,
    payload: Any,
    *,
    now: Optional[float] = None,
    max_age_seconds: float = DEFAULT_MAX_QUOTE_AGE_SECONDS,
    source_id: str = "alpaca.get_ticker",
) -> Dict[str, Any]:
    """Validate a provider quote without supplying absent market fields."""
    received_at = time.time() if now is None else float(now)
    max_age = _finite_number(max_age_seconds, positive=True)
    if max_age is None:
        raise ValueError("max_age_seconds must be a finite positive number")
    if not isinstance(payload, dict):
        return _no_data_receipt(
            symbol,
            "provider_quote_receipt_required",
            received_at=received_at,
            source_id=source_id,
        )

    if (
        payload.get("data_status") != "live"
        or payload.get("truth_status") not in REAL_TRUTH_STATUSES
        or payload.get("generated_values") is not False
        or payload.get("action_eligible") is not True
    ):
        return _no_data_receipt(
            symbol,
            "live_provider_quote_envelope_required",
            received_at=received_at,
            source_id=source_id,
        )

    bid = _finite_number(payload.get("bid"), positive=True)
    ask = _finite_number(payload.get("ask"), positive=True)
    if bid is None or ask is None or bid > ask:
        return _no_data_receipt(
            symbol,
            "valid_two_sided_provider_quote_required",
            received_at=received_at,
            source_id=source_id,
        )

    source_timestamp = _epoch_seconds(
        payload.get("source_timestamp") or payload.get("provider_timestamp")
    )
    if source_timestamp is None:
        return _no_data_receipt(
            symbol,
            "provider_source_timestamp_required",
            received_at=received_at,
            source_id=source_id,
        )
    age_seconds = received_at - source_timestamp
    if age_seconds < -FUTURE_TOLERANCE_SECONDS or age_seconds > max_age:
        return _no_data_receipt(
            symbol,
            "fresh_provider_quote_required",
            received_at=received_at,
            source_id=source_id,
        )

    volume = None
    if payload.get("volume") is not None:
        volume = _finite_number(payload.get("volume"), nonnegative=True)
        if volume is None:
            return _no_data_receipt(
                symbol,
                "observed_volume_must_be_finite",
                received_at=received_at,
                source_id=source_id,
            )

    change_pct = None
    if payload.get("change_pct") is not None:
        change_pct = _finite_number(payload.get("change_pct"))
        if change_pct is None:
            return _no_data_receipt(
                symbol,
                "observed_change_must_be_finite",
                received_at=received_at,
                source_id=source_id,
            )

    midpoint = (bid + ask) / 2.0
    return {
        "symbol": symbol,
        "price": midpoint,
        "bid": bid,
        "ask": ask,
        "volume": volume,
        "change_pct": change_pct,
        "source_id": source_id,
        "source_timestamp": datetime.fromtimestamp(
            source_timestamp, timezone.utc
        ).isoformat(),
        "received_at": datetime.fromtimestamp(received_at, timezone.utc).isoformat(),
        "data_status": "live",
        "truth_status": "real_derived",
        "reason": "fresh_two_sided_provider_quote",
        "price_derivation": "provider_bid_ask_midpoint",
        "generated_values": False,
        "eligible_for_analysis": True,
        "eligible_for_action": False,
    }


def collect_live_market_data(
    client: Any,
    symbols: Iterable[str] = DEFAULT_SYMBOLS,
    *,
    now: Optional[float] = None,
    max_age_seconds: float = DEFAULT_MAX_QUOTE_AGE_SECONDS,
) -> Dict[str, Any]:
    """Collect a visible receipt for every requested symbol."""
    received_at = time.time() if now is None else float(now)
    receipts: Dict[str, Dict[str, Any]] = {}
    for raw_symbol in symbols:
        symbol = str(raw_symbol).strip().upper()
        try:
            payload = client.get_ticker(symbol)
        except Exception as exc:
            receipts[symbol] = _no_data_receipt(
                symbol,
                f"provider_read_failed:{type(exc).__name__}",
                received_at=received_at,
                source_id="alpaca.get_ticker",
            )
            continue
        receipts[symbol] = normalize_quote_receipt(
            symbol,
            payload,
            now=received_at,
            max_age_seconds=max_age_seconds,
        )

    live_count = sum(
        receipt["data_status"] == "live" for receipt in receipts.values()
    )
    return {
        "data_status": "live" if live_count else "no_data",
        "truth_status": "real_derived" if live_count else "no_data",
        "reason": (
            "fresh_provider_quotes_available"
            if live_count
            else "no_fresh_provider_quotes"
        ),
        "received_at": datetime.fromtimestamp(received_at, timezone.utc).isoformat(),
        "requested_symbol_count": len(receipts),
        "live_symbol_count": live_count,
        "quotes": receipts,
        "generated_values": False,
        "eligible_for_action": False,
    }


def main() -> int:
    """Run the explicit provider-backed diagnostic."""
    from aureon.core.aureon_baton_link import link_system
    from aureon.exchanges.alpaca_client import AlpacaClient

    link_system(__name__)
    client = AlpacaClient()
    try:
        report = collect_live_market_data(client)
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            close()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["data_status"] == "live" else 1


if __name__ == "__main__":
    raise SystemExit(main())
