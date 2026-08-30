"""Small official-source readers for Capital GOLD Council context."""

from __future__ import annotations

import datetime as dt
import math
import xml.etree.ElementTree as ET
from collections.abc import Callable, Mapping
from typing import Any, Protocol

import requests

CFTC_GOLD_URI = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
TREASURY_URI = (
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml"
)
NOAA_KP_URI = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"


class ReadOnlyHttpSession(Protocol):
    def get(self, url: str, **kwargs: Any) -> Any: ...


def _timestamp(value: str) -> float:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.UTC)
    return parsed.astimezone(dt.UTC).timestamp()


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"finite_{name}_required")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"finite_{name}_required") from exc
    if not math.isfinite(result):
        raise ValueError(f"finite_{name}_required")
    return result


def _integer(value: Any, name: str) -> int:
    result = _number(value, name)
    if not result.is_integer():
        raise ValueError(f"integer_{name}_required")
    return int(result)


def fetch_cftc_gold_context(
    *,
    session: ReadOnlyHttpSession = requests,
    clock: Callable[[], float],
) -> dict[str, Any]:
    """Read the newest exact COMEX GOLD futures-only COT row."""

    response = session.get(
        CFTC_GOLD_URI,
        params={
            "$limit": 1,
            "$order": "report_date_as_yyyy_mm_dd DESC",
            "$where": "contract_market_name='GOLD' AND futonly_or_combined='FutOnly'",
        },
        timeout=20,
    )
    response.raise_for_status()
    rows = response.json()
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], Mapping):
        raise ValueError("exact_latest_cftc_gold_row_required")
    row = rows[0]
    if row.get("contract_market_name") != "GOLD" or row.get("futonly_or_combined") != "FutOnly":
        raise ValueError("exact_comex_gold_futures_row_required")
    reported_at = _timestamp(str(row["report_date_as_yyyy_mm_dd"]))
    noncommercial_long = _integer(row.get("noncomm_positions_long_all"), "noncommercial_long")
    noncommercial_short = _integer(row.get("noncomm_positions_short_all"), "noncommercial_short")
    commercial_long = _integer(row.get("comm_positions_long_all"), "commercial_long")
    commercial_short = _integer(row.get("comm_positions_short_all"), "commercial_short")
    return {
        "source_kind": "cftc_cot",
        "source_id": f"cftc:legacy-futures-only:{row['id']}",
        "source_uri": CFTC_GOLD_URI,
        "source_timestamp": reported_at,
        "received_at": float(clock()),
        "payload": {
            "commercial_net_contracts": commercial_long - commercial_short,
            "contract_market_name": "GOLD",
            "market_and_exchange_names": str(row.get("market_and_exchange_names") or ""),
            "noncommercial_net_contracts": noncommercial_long - noncommercial_short,
            "open_interest_contracts": _integer(row.get("open_interest_all"), "open_interest"),
            "report_date": str(row["report_date_as_yyyy_mm_dd"]),
            "report_kind": "legacy_futures_only",
        },
    }


def fetch_treasury_yield_context(
    *,
    session: ReadOnlyHttpSession = requests,
    clock: Callable[[], float],
) -> dict[str, Any]:
    """Read the newest official daily Treasury par-yield row."""

    current = float(clock())
    year = dt.datetime.fromtimestamp(current, tz=dt.UTC).year
    response = session.get(
        TREASURY_URI,
        params={"data": "daily_treasury_yield_curve", "field_tdr_date_value": year},
        timeout=20,
    )
    response.raise_for_status()
    root = ET.fromstring(response.content)
    atom = {"a": "http://www.w3.org/2005/Atom"}
    data_ns = "{http://schemas.microsoft.com/ado/2007/08/dataservices}"
    rows: list[dict[str, str]] = []
    for entry in root.findall("a:entry", atom):
        properties = entry.find(".//{http://schemas.microsoft.com/ado/2007/08/dataservices/metadata}properties")
        if properties is None:
            continue
        rows.append({child.tag.removeprefix(data_ns): str(child.text or "") for child in properties})
    if not rows:
        raise ValueError("treasury_yield_rows_required")
    row = max(rows, key=lambda item: item.get("NEW_DATE", ""))
    reported_at = _timestamp(row["NEW_DATE"])
    return {
        "source_kind": "treasury_yield",
        "source_id": f"treasury:daily-par-yield:{row['NEW_DATE']}",
        "source_uri": TREASURY_URI,
        "source_timestamp": reported_at,
        "received_at": current,
        "payload": {
            "date": row["NEW_DATE"],
            "five_year_yield_pct": _number(row.get("BC_5YEAR"), "five_year_yield"),
            "ten_year_yield_pct": _number(row.get("BC_10YEAR"), "ten_year_yield"),
            "thirty_year_yield_pct": _number(row.get("BC_30YEAR"), "thirty_year_yield"),
            "two_year_yield_pct": _number(row.get("BC_2YEAR"), "two_year_yield"),
        },
    }


def fetch_noaa_kp_context(
    *,
    session: ReadOnlyHttpSession = requests,
    clock: Callable[[], float],
) -> dict[str, Any]:
    """Read the newest official NOAA planetary K-index observation."""

    response = session.get(NOAA_KP_URI, timeout=20)
    response.raise_for_status()
    rows = response.json()
    if not isinstance(rows, list) or not rows:
        raise ValueError("noaa_kp_rows_required")
    if all(isinstance(row, Mapping) for row in rows):
        parsed = [dict(row) for row in rows]
    elif len(rows) >= 2 and isinstance(rows[0], list):
        header = [str(value) for value in rows[0]]
        parsed = [
            dict(zip(header, row, strict=True))
            for row in rows[1:]
            if isinstance(row, list) and len(row) == len(header)
        ]
    else:
        parsed = []
    if not parsed:
        raise ValueError("noaa_kp_observation_required")
    row = max(parsed, key=lambda item: item.get("time_tag", ""))
    observed_at = _timestamp(str(row["time_tag"]))
    return {
        "source_kind": "noaa_kp",
        "source_id": f"noaa:planetary-k-index:{row['time_tag']}",
        "source_uri": NOAA_KP_URI,
        "source_timestamp": observed_at,
        "received_at": float(clock()),
        "payload": {
            "estimated_kp": _number(row.get("Kp"), "estimated_kp"),
            "observed_at": str(row["time_tag"]),
            "station_count": _integer(row.get("station_count"), "station_count"),
        },
    }


__all__ = [
    "CFTC_GOLD_URI",
    "NOAA_KP_URI",
    "TREASURY_URI",
    "fetch_cftc_gold_context",
    "fetch_noaa_kp_context",
    "fetch_treasury_yield_context",
]
