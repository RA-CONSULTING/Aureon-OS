#!/usr/bin/env python3
"""_seer_counsel_adapter.py — thin counsel bridge from upstream AureonTheSeer.

Reads aureon-os-upstream/aureon/intelligence/aureon_seer.py WITHOUT modifying
it, instantiates AureonTheSeer, calls see(), and writes a compact counsel
block into aureon_radar/state/harmonic_phase.json as 'seer_counsel':

  {
    "vision_grade": "CLEAR_SIGHT",
    "unified_score": 0.73,
    "action": "BUY_BIAS",
    "windows": {
      "session": "LONDON",
      "session_score": 0.7,
      "time_phase": "FAVORABLE",
      "kp": 0.0,
      "geomagnetic": "quiet",
      "solar_flare_class": "A1.0"
    },
    "ts": 1788765600.0,
    "ts_iso": "2026-09-07T...Z",
    "source": "aureon_seer_upstream",
    "error": null
  }

If import/instantiation/see() fails in this environment, the adapter writes
seer_counsel: null with the error reason — never fabricating a grade.

This script should be invoked from aureon_radar/ with the upstream repo on
PYTHONPATH. To avoid leaking a stray harmonic_cache at the workspace root,
the working directory is kept at aureon_radar/ so the Seer's internal
HarmonicWaveFusion uses the radar's harmonic_cache (which the seed loop
keeps warm).
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

RADAR = Path(__file__).resolve().parent
STATE_PATH = RADAR / "state" / "harmonic_phase.json"
UPSTREAM = (RADAR.parent / "aureon-os-upstream").resolve()


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _vision_to_counsel(vision) -> dict:
    """Extract compact, honest counsel from SeerVision."""
    win = {}
    tl = getattr(vision, "timeline", None)
    if tl and hasattr(tl, "details"):
        d = tl.details or {}
        win["session"] = d.get("session")
        win["session_score"] = d.get("session_score")
        win["time_phase"] = tl.phase
    cs = getattr(vision, "cosmos", None)
    if cs and hasattr(cs, "details"):
        d = cs.details or {}
        win["kp"] = d.get("kp_index")
        win["geomagnetic"] = d.get("geomagnetic_status") or d.get("storm_level")
        win["solar_flare_class"] = d.get("solar_flare_class")

    raw_score = getattr(vision, "unified_score", None)
    return {
        "vision_grade": getattr(vision, "grade", None),
        "unified_score": round(float(raw_score), 6) if raw_score is not None else None,
        "action": getattr(vision, "action", None),
        "tactical_mode": getattr(vision, "tactical_mode", None),
        "windows": win,
        "ts": time.time(),
        "ts_iso": _utc_iso(),
        "source": "aureon_seer_upstream",
        "error": None,
    }


def main() -> int:
    # Ensure upstream is importable (the loop sets PYTHONPATH, but be safe).
    upstream_str = str(UPSTREAM)
    if upstream_str not in (os.environ.get("PYTHONPATH") or ""):
        os.environ["PYTHONPATH"] = upstream_str + os.pathsep + (
            os.environ.get("PYTHONPATH", "")
        )
        sys.path.insert(0, upstream_str)

    doc: dict = {}
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[seer] warning: could not read harmonic_phase.json ({exc}); creating new", flush=True)
        doc = {}

    counsel = None
    reason = None
    try:
        from aureon.intelligence.aureon_seer import AureonTheSeer
        seer = AureonTheSeer()
        vision = seer.see()
        counsel = _vision_to_counsel(vision)
        print(f"[seer] counsel: grade={counsel['vision_grade']} "
              f"score={counsel['unified_score']} action={counsel['action']}", flush=True)
    except Exception as exc:  # noqa: BLE001
        reason = f"{type(exc).__name__}: {exc}"
        print(f"[seer] FAIL: {reason}", flush=True)

    doc["seer_counsel"] = counsel if counsel is not None else None
    if reason:
        doc.setdefault("errors", [])
        if isinstance(doc["errors"], list):
            doc["errors"].append(f"seer_counsel: {reason}")

    tmp = STATE_PATH.with_suffix(".seer.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
    tmp.replace(STATE_PATH)
    print(f"[seer] wrote seer_counsel to {STATE_PATH}", flush=True)
    return 0 if counsel is not None else 1


if __name__ == "__main__":
    sys.exit(main())
