"""Checkout seats for organs whose workspace scripts are not in this tree.

Each seat stays up, writes an honest state file, and does not place an order.
A public reading is recorded only when the source actually returned one.
A missed fetch is ``no_data``. Nothing here invents a measurement.
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
_INTERVAL_S = 30.0
_FETCH_TIMEOUT_S = 4.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def _base(name: str, note: str, reading: dict[str, Any] | None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "daemon": name,
        "timestamp": _now(),
        "live_trading": False,
        "orders": 0,
        "note": note,
    }
    if reading:
        inner = str(reading.get("truth_status") or "live")
        if reading.get("generated_values") is True or inner == "no_data":
            body["truth_status"] = "no_data"
        elif inner in {"live", "real_derived", "cached_real"}:
            body["truth_status"] = inner
        else:
            body["truth_status"] = "live"
        body["reading"] = reading
    else:
        body["truth_status"] = "no_data"
        body["reading"] = None
    return body


def _call(fn, timeout: float) -> Any:
    box: dict[str, Any] = {}

    def run() -> None:
        try:
            box["value"] = fn()
        except Exception as exc:
            box["error"] = exc.__class__.__name__

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive() or "error" in box:
        return None
    return box.get("value")


def _kraken_ticker() -> dict[str, Any] | None:
    request = urllib.request.Request(
        "https://api.kraken.com/0/public/Ticker?pair=XBTUSD",
        headers={"User-Agent": "aureon-checkout-daemon"},
    )
    with urllib.request.urlopen(request, timeout=_FETCH_TIMEOUT_S) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict) or payload.get("error"):
        return None
    result = payload.get("result")
    if not isinstance(result, dict) or not result:
        return None
    pair, row = next(iter(result.items()))
    if not isinstance(row, dict):
        return None
    close = row.get("c")
    if not isinstance(close, list) or not close or close[0] in (None, ""):
        return None
    return {"source": "kraken_public_ticker", "pair": str(pair), "last": str(close[0])}


def _schumann() -> dict[str, Any] | None:
    from aureon.harmonic.aureon_schumann_resonance_bridge import get_live_schumann_data

    reading = get_live_schumann_data(force_refresh=True)
    if reading is None:
        return None
    data = reading.to_dict() if hasattr(reading, "to_dict") else None
    if not isinstance(data, dict) or not data:
        return None
    return data


def _noaa_kp() -> dict[str, Any] | None:
    request = urllib.request.Request(
        "https://services.swpc.noaa.gov/json/planetary_k_index_1m.json",
        headers={"User-Agent": "aureon-checkout-daemon"},
    )
    with urllib.request.urlopen(request, timeout=_FETCH_TIMEOUT_S) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, list) or not payload:
        return None
    latest = payload[-1]
    if not isinstance(latest, dict):
        return None
    stamp = latest.get("time_tag")
    kp = latest.get("kp_index", latest.get("estimated_kp"))
    if not stamp or kp is None:
        return None
    return {"source": "noaa_swpc", "time_tag": str(stamp), "kp_index": kp}


_SEATS: dict[str, dict[str, Any]] = {
    "real_time_data_feeder": {
        "path": REPO / "real_time_data.json",
        "note": "public ticker when Kraken answers; otherwise no_data",
        "read": _kraken_ticker,
    },
    "schumann_real_daemon": {
        "path": REPO / "schumann_state.json",
        "note": "Schumann bridge reading when a source answers; otherwise no_data",
        "read": _schumann,
    },
    "planetary_monitor_daemon": {
        "path": REPO / "state" / "planetary_monitor.json",
        "note": "workspace planetary_monitor_daemon.py is not in this tree; no ephemeris sample is invented",
        "read": None,
    },
    "solar_system_collector": {
        "path": REPO / "state" / "solar_system_collector.json",
        "note": "workspace solar_system_collector.py is not in this tree; no positions are invented",
        "read": None,
    },
    "sero_space_weather": {
        "path": REPO / "state" / "sero_space_weather.json",
        "note": "NOAA SWPC planetary K when the public feed answers; otherwise no_data",
        "read": _noaa_kp,
    },
    "sero_autonomous_expansion": {
        "path": REPO / "state" / "sero_autonomous_expansion.json",
        "note": "workspace sero_autonomous_expansion.py is not in this tree; standing by, no expansion and no orders",
        "read": None,
    },
    "soul_protection_daemon": {
        "path": REPO / "state" / "soul_protection.json",
        "note": "workspace soul_protection_daemon.py is not in this tree; standing by, no mutation",
        "read": None,
    },
}


def sample(name: str) -> dict[str, Any]:
    seat = _SEATS[name]
    reader = seat.get("read")
    reading = _call(reader, _FETCH_TIMEOUT_S + 1.0) if reader else None
    if reading is not None and not isinstance(reading, dict):
        reading = None
    return _base(name, str(seat["note"]), reading)


def serve(name: str) -> int:
    """Write one honest sample immediately, then keep the seat alive."""
    if name not in _SEATS:
        print(f"unknown checkout daemon: {name}", flush=True)
        return 2
    path: Path = _SEATS[name]["path"]
    os.environ.setdefault("AUREON_LIVE_TRADING", "0")
    os.environ.setdefault("AUREON_DISABLE_REAL_ORDERS", "1")
    while True:
        payload = sample(name)
        _write(path, payload)
        print(
            f"{name} wrote {path.name} truth_status={payload['truth_status']} live_trading=false",
            flush=True,
        )
        time.sleep(_INTERVAL_S)


def main(name: str) -> int:
    return serve(name)
