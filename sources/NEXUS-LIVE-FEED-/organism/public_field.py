"""Nexus field layer: one public planetary K-index observation.

The call reads NOAA SWPC's public planetary K-index product. It does not
open an account, sign a request, or place an order.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from typing import Any, Callable
from urllib.parse import urlparse

SOURCE = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
_HOST = "services.swpc.noaa.gov"


def _default_transport(url: str) -> bytes:
    if url != SOURCE or urlparse(url).hostname != _HOST:
        raise ValueError("public_field_source_rejected")
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "nexus-public-field/1"},
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        if response.status != 200:
            raise ValueError("public_field_status_rejected")
        body = response.read(2_000_000)
    if len(body) >= 2_000_000:
        raise ValueError("public_field_body_rejected")
    return body


def _last_row(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    if not isinstance(payload, list) or not payload:
        raise ValueError("public_field_row_required")
    head = payload[0]
    if isinstance(head, list):
        if len(payload) < 2:
            raise ValueError("public_field_row_required")
        header = [str(item) for item in head]
        row = payload[-1]
        if not isinstance(row, list):
            raise ValueError("public_field_row_required")
        return dict(zip(header, row))
    if isinstance(payload[-1], dict):
        return payload[-1]
    raise ValueError("public_field_row_required")


def _number(value: Any, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"public_field_{field}_required") from exc
    if number != number:  # NaN
        raise ValueError(f"public_field_{field}_required")
    return number


def observe_planetary_k_index(transport: Callable[[str], bytes] | None = None) -> dict[str, Any]:
    """Return the latest public K-index row and the raw payload hash."""

    raw = (transport or _default_transport)(SOURCE)
    if not isinstance(raw, bytes) or not raw:
        raise ValueError("public_field_body_required")
    row = _last_row(json.loads(raw))
    time_tag = row.get("time_tag")
    if not isinstance(time_tag, str) or not time_tag.strip():
        raise ValueError("public_field_time_required")
    return {
        "schema": "nexus.public-field.v1",
        "source": SOURCE,
        "time_tag": time_tag,
        "kp": _number(row.get("Kp"), "kp"),
        "a_running": _number(row.get("a_running"), "a_running"),
        "station_count": _number(row.get("station_count"), "station_count"),
        "payload_sha256": hashlib.sha256(raw).hexdigest(),
        "generated_values": False,
        "may_act": False,
    }
