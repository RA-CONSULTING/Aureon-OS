"""EEG live patch — provides brainwave endpoints for the unified interface v4."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from auris_unified_interface_v4 import BIOSCAN_DIR, app

BANDS = ["delta", "theta", "alpha", "beta", "gamma"]


def _load_recent(limit: int = 240) -> List[Dict[str, Any]]:
    BIOSCAN_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(
        [path for path in BIOSCAN_DIR.glob("*.json") if path.is_file()],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    records: List[Dict[str, Any]] = []
    for path in files[:limit]:
        try:
            records.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            continue
    return records


def _get_bands(record: Dict[str, Any]) -> Dict[str, float]:
    eeg_section = (record.get("eeg") or {}).get("bands")
    if isinstance(eeg_section, dict):
        return eeg_section

    nfc_section = (record.get("layer_scores") or {}).get("nfc") or {}
    if isinstance(nfc_section, dict) and isinstance(nfc_section.get("bands"), dict):
        return nfc_section["bands"]

    ctx_section = (record.get("context") or {}).get("bands")
    if isinstance(ctx_section, dict):
        return ctx_section

    return {}


@app.get("/eeg/recent")
def eeg_recent(n: int = 120) -> Dict[str, Any]:
    records = _load_recent(n)
    series: Dict[str, List[float | None]] = {band: [] for band in BANDS}
    timestamps: List[Any] = []
    for record in records:
        bands = _get_bands(record)
        for band in BANDS:
            value = bands.get(band)
            try:
                series[band].append(float(value) if value is not None else None)
            except Exception:
                series[band].append(None)
        timestamps.append((record.get("context") or {}).get("timestamp_utc"))

    for band in BANDS:
        series[band] = list(reversed(series[band]))
    timestamps = list(reversed(timestamps))
    return {"t": timestamps, "bands": series}


@app.get("/eeg/current")
def eeg_current() -> Dict[str, Any]:
    records = _load_recent(1)
    if not records:
        return {"bands": {}, "ratios": {}}

    bands = _get_bands(records[0])
    values = []
    normalized: Dict[str, float] = {}
    for band in BANDS:
        value = bands.get(band)
        try:
            numeric = float(value) if value is not None else 0.0
        except Exception:
            numeric = 0.0
        values.append(numeric)
        normalized[band] = numeric

    total = sum(values)
    if total > 0:
        normalized = {band: (value / total) for band, value in normalized.items()}

    theta = normalized.get("theta", 0.0)
    alpha = normalized.get("alpha", 0.0)
    beta = normalized.get("beta", 0.0)
    gamma = normalized.get("gamma", 0.0)

    ratios: Dict[str, float] = {}
    if theta > 0:
        ratios["alpha_theta"] = alpha / theta
    if alpha > 0:
        ratios["beta_alpha"] = beta / alpha
        ratios["gamma_alpha"] = gamma / alpha

    return {"bands": normalized, "ratios": ratios}
