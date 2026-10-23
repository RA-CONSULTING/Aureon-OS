from fastapi import FastAPI, Query
from typing import Dict, Any

import numpy as np

try:
    # Import the running app from v4
    from auris_unified_interface_v4 import app as unified_app, clip01, load_recent_bioscans
except Exception as exc:  # pragma: no cover - module import is critical for runtime
    raise SystemExit(
        "This patch expects auris_unified_interface_v4.py to be importable. "
        f"Error: {exc}"
    )

app: FastAPI = unified_app  # alias for clarity when importing this module


@app.get("/bioscan/recent")
def bioscan_recent(n: int = Query(60, ge=1, le=1000)) -> Dict[str, Any]:
    """Return the most recent bioscan records (newest → oldest)."""
    return {"results": list(load_recent_bioscans(n))}


@app.get("/surge/uvc")
def surge_uvc(n: int = Query(120, ge=5, le=2000)) -> Dict[str, Any]:
    """Compute a UVC time series from the most recent bioscans."""
    recs = load_recent_bioscans(n)
    if not recs:
        return {"t": [], "uvc": [], "components": {}}

    def get_mu(record: Dict[str, Any], key: str, default: float = 0.8) -> float:
        layer_scores = record.get("layer_scores") or {}
        mu_value = (layer_scores.get(key) or {}).get("mu")
        try:
            return float(mu_value)
        except (TypeError, ValueError):
            return default

    c1_vals = []  # temporal coherence proxy from CRC change stability (1 - |ΔCRC|)
    c2i_vals = []  # inverse entropy proxy from NFC smoothness (1 - |ΔNFC|)
    c4_vals = []
    bqi_vals = []

    prev_crc = None
    prev_nfc = None
    for record in recs:
        crc = get_mu(record, "crc", 0.8)
        nfc = get_mu(record, "nfc", 0.8)
        peb = get_mu(record, "peb", 0.8)
        bhs = get_mu(record, "bhs", 0.9)
        pla = get_mu(record, "pla", 0.9)

        if prev_crc is None:
            c1_vals.append(0.95)
            c2i_vals.append(0.95)
        else:
            c1_vals.append(clip01(1.0 - abs(crc - prev_crc)))
            c2i_vals.append(clip01(1.0 - abs(nfc - prev_nfc)))

        c4_vals.append(pla)
        bqi_vals.append(float(np.sqrt((crc ** 2 + nfc ** 2 + peb ** 2 + bhs ** 2 + pla ** 2) / 5.0)))

        prev_crc = crc
        prev_nfc = nfc

    c1 = np.array(c1_vals)[::-1]  # oldest → newest
    c2inv = np.array(c2i_vals)[::-1]
    c4 = np.array(c4_vals)[::-1]
    bqi = np.array(bqi_vals)[::-1]

    uvc = (c1 ** 0.30) * (c2inv ** 0.20) * (c4 ** 0.20) * (bqi ** 0.30)
    t = list(range(len(uvc)))

    return {
        "t": t,
        "uvc": uvc.tolist(),
        "components": {
            "C1": c1.tolist(),
            "C2inv": c2inv.tolist(),
            "C4": c4.tolist(),
            "C5_BQI": bqi.tolist(),
        },
    }
