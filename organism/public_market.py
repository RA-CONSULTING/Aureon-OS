"""Sero market layer: one public price observation.

The call reads Binance's public market-data mirror. It does not sign a
request, open an account, or place an order.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Callable
from urllib.parse import urlparse

SOURCE = "https://data-api.binance.vision/api/v3/ticker/price?symbol=BTCUSDT"
_HOST = "data-api.binance.vision"
_SYMBOL = "BTCUSDT"


def _default_transport(url: str) -> bytes:
    if url != SOURCE or urlparse(url).hostname != _HOST:
        raise ValueError("public_market_source_rejected")
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "sero-public-market/1"},
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        if response.status != 200:
            raise ValueError("public_market_status_rejected")
        body = response.read(100_000)
    if len(body) >= 100_000:
        raise ValueError("public_market_body_rejected")
    return body


def observe_public_price(transport: Callable[[str], bytes] | None = None) -> dict:
    """Return the latest public BTCUSDT price and the raw payload hash."""

    raw = (transport or _default_transport)(SOURCE)
    if not isinstance(raw, bytes) or not raw:
        raise ValueError("public_market_body_required")
    payload = json.loads(raw)
    if not isinstance(payload, dict) or payload.get("symbol") != _SYMBOL:
        raise ValueError("public_market_symbol_required")
    try:
        price = Decimal(str(payload.get("price")))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("public_market_price_required") from exc
    if not price.is_finite() or price <= 0:
        raise ValueError("public_market_price_required")
    return {
        "schema": "sero.public-market.v1",
        "source": SOURCE,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "symbol": _SYMBOL,
        "price": format(price, "f"),
        "order_count": 0,
        "payload_sha256": hashlib.sha256(raw).hexdigest(),
        "generated_values": False,
        "may_act": False,
    }
