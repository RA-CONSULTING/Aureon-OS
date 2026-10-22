"""Live planetary band — REAL planetary signal state the organism computes.

Real-signal layer module (planetary band). Follows the binding conventions of
scanners/live_market_momentum_scanner.py:

  * module-level ``scan(symbol, price)`` — the hub probes planetary modules
    under this name and coerces the result.
  * SYMBOL_MAP for hub symbols; unmapped -> None.
  * REAL data only; stale/unparseable -> None. No directional content ->
    None, honestly. Never invent astrology.

Data source (found by tracing the heartbeat daemon / hnc_core wiring):
  aureon_radar/planetary_signals.jsonl  — append-only, written every ~5 min by
  aureon_radar/planetary_switchboard.py (NOAA space weather + Schumann +
  NASA DONKI). Each cycle appends one ``planetary_state`` record (always;
  explicitly NEUTRAL telemetry) plus zero or more directional records
  (signal_type space_weather / schumann / solar_event) only when storms
  occur. Rejected if file mtime age > 600 s.

Score mapping (documented, deterministic — same real input, same score):

  Priority 1 — explicit directional records in the freshest cycle (all lines
  sharing the last line's timestamp). The switchboard only emits these under
  space-weather stress and every one of them is a risk-off indicator
  (safe-haven GOLD LONG, flight-to-safety USDJPY SHORT, energy-influx
  NATURALGAS LONG). Crypto is a risk asset, so risk-off maps SHORT:
      score = -mean(confidence) of those records        in [-1, 0)

  Priority 2 — otherwise, derive a space-weather STRESS score from the real
  numbers in the freshest state record (parsed from planetary_narrative /
  reasoning, which carry Kp, solar wind, Bz, Schumann Hz, flare and CME
  counts):
      kp_n    = clamp(kp / 6, 0, 1)                     weight 0.300
      wind_n  = clamp((wind_kms - 450) / 350, 0, 1)     weight 0.200
      bz_n    = clamp(max(0, -bz_nt) / 10, 0, 1)        weight 0.200
      sch_n   = clamp(|hz - 7.83| / 1.0, 0, 1)          weight 0.150
      flr_n   = clamp(flares_24h / 20, 0, 1)            weight 0.075
      cme_n   = clamp(cmes_72h / 50, 0, 1)              weight 0.075
      stress  = weighted sum                            in [0, 1]
      score   = -1.2 * stress, bounded [-1, 1]
  Stress -> risk-off -> SHORT for crypto; a quiet sky gives stress ~ 0.

  Priority 3 — if narrative numbers cannot be parsed but the record carries a
  nonzero risk_modifier (-0.2..+0.2, negative = stress):
      score = clamp(risk_modifier * 3, -1, 1)

  Conviction floor 0.35 everywhere: quiet conditions (Kp 0-2, calm wind,
  Bz >= 0, Schumann on 7.83 Hz) score near 0 and return None. That is the
  doctrine working, not a failure.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import List, Optional

RADAR_DIR = Path(__file__).resolve().parents[1]  # .../workspace/aureon_radar
SIGNALS_PATH = RADAR_DIR / "planetary_signals.jsonl"

# ── symbol mapping (hub symbol -> planetary band) ───────────────────────────
SYMBOL_MAP = {
    "BTCUSD": "PLANET", "BTCUSDT": "PLANET", "BTC": "PLANET", "XBTUSD": "PLANET",
    "ETHUSD": "PLANET", "ETHUSDT": "PLANET", "ETH": "PLANET",
}

_MAX_AGE = 600.0
_RE_KP = re.compile(r"Kp=([0-9]+(?:\.[0-9]+)?)")
_RE_WIND = re.compile(r"Solar wind ([0-9]+(?:\.[0-9]+)?)\s*km/s")
_RE_BZ = re.compile(r"Bz=(-?[0-9]+(?:\.[0-9]+)?)nT")
_RE_SCH = re.compile(r"Schumann ([0-9]+(?:\.[0-9]+)?)Hz")
_RE_FLARE = re.compile(r"(\d+) solar flares")
_RE_CME = re.compile(r"(\d+) CMEs")


def _f(pattern: str, text: str) -> Optional[float]:
    m = re.search(pattern, text)
    return float(m.group(1)) if m else None


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _freshest_batch() -> Optional[List[dict]]:
    """Last cycle's records: trailing lines sharing the final line's timestamp."""
    try:
        st = SIGNALS_PATH.stat()
        if time.time() - st.st_mtime > _MAX_AGE:
            return None
        lines = SIGNALS_PATH.read_text(encoding="utf-8").strip().splitlines()
        records = []
        for ln in reversed(lines):
            ln = ln.strip()
            if not ln:
                continue
            try:
                rec = json.loads(ln)
            except Exception:
                if records:
                    break  # batch boundary reached
                return None
            if records and rec.get("timestamp") != records[-1].get("timestamp"):
                break
            records.append(rec)
        records.reverse()
        return records or None
    except Exception:
        return None


def _stress_score(state: dict) -> Optional[float]:
    text = " ".join(str(state.get(k, "")) for k in
                    ("planetary_narrative", "reasoning", "summary"))
    kp = _f(_RE_KP.pattern, text)
    if kp is None:
        return None
    wind = _f(_RE_WIND.pattern, text) or 0.0
    bz = _f(_RE_BZ.pattern, text) or 0.0
    sch = _f(_RE_SCH.pattern, text)
    flr = _f(_RE_FLARE.pattern, text) or 0.0
    cme = _f(_RE_CME.pattern, text) or 0.0

    kp_n = _clamp(kp / 6.0)
    wind_n = _clamp((wind - 450.0) / 350.0)
    bz_n = _clamp(max(0.0, -bz) / 10.0)
    sch_n = _clamp(abs(sch - 7.83) / 1.0) if sch is not None else 0.0
    flr_n = _clamp(flr / 20.0)
    cme_n = _clamp(cme / 50.0)

    stress = (0.300 * kp_n + 0.200 * wind_n + 0.200 * bz_n
              + 0.150 * sch_n + 0.075 * flr_n + 0.075 * cme_n)
    return max(-1.0, min(1.0, -1.2 * stress))


def scan(symbol: str, price: float = 0.0):
    """Hub probe entry — returns dict(direction, confidence) or None."""
    if SYMBOL_MAP.get(str(symbol).upper()) is None:
        return None
    batch = _freshest_batch()
    if not batch:
        return None

    directional = [r for r in batch
                   if r.get("signal_type") != "planetary_state"
                   and r.get("direction") in ("LONG", "SHORT")
                   and isinstance(r.get("confidence"), (int, float))]

    score: Optional[float] = None
    how = ""
    if directional:
        # every directional record the switchboard emits is risk-off; crypto
        # is a risk asset -> SHORT bias of the mean emitter confidence
        score = -sum(float(r["confidence"]) for r in directional) / len(directional)
        how = "directional_records"
    else:
        state = next((r for r in reversed(batch)
                      if r.get("signal_type") == "planetary_state"), batch[-1])
        score = _stress_score(state)
        how = "stress_formula"
        if score is None:
            rm = state.get("risk_modifier")
            if isinstance(rm, (int, float)) and rm != 0:
                score = max(-1.0, min(1.0, float(rm) * 3.0))
                how = "risk_modifier"

    if score is None:
        return None
    conf = abs(score)
    if conf < 0.35:
        return None  # quiet sky — omit, don't dilute fusion
    return {
        "direction": "LONG" if score > 0 else "SHORT",
        "confidence": round(conf, 4),
        "source": f"planetary_signals.jsonl:{how}",
    }


if __name__ == "__main__":
    import datetime
    st = SIGNALS_PATH.stat()
    print(f"file: {SIGNALS_PATH}")
    print(f"mtime: {datetime.datetime.fromtimestamp(st.st_mtime).isoformat()} "
          f"(age {time.time() - st.st_mtime:.0f}s)")
    batch = _freshest_batch()
    print("freshest batch:")
    for r in (batch or []):
        print(" ", json.dumps(r)[:300])
    for s in ("BTCUSD", "ETHUSD", "EURUSD"):
        print(s, "->", scan(s))
