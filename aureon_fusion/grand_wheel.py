#!/usr/bin/env python3
"""The Grand Big Wheel — Pursuit of Happiness engine for the fused organism.

Pure-stdlib port of the upstream ``queen_pursuit_of_happiness.py`` math.
The upstream module is NEVER imported in the live path: it has an import-time
baton-relay side effect (``link_system(__name__)``, upstream line 32) and a
hard numpy dependency. Only the formulas below are ported.

PORTED FORMULA (source: aureon-os-upstream/aureon/queen/queen_pursuit_of_happiness.py)

- PHI = (1 + sqrt(5)) / 2                       (upstream line 66)
- Pillar weights: dream * phi^2, love * phi, gaia * 1, joy * 1, purpose * phi
  HQ = weighted_sum / (phi^2 + phi + 1 + 1 + phi)          (upstream lines 109-134)
  Upstream default anchors: love = 0.618 (line 96), purpose = 1.0 (line 99).
  Dream progress = min(1.0, current_value / 1e9)            (upstream line 266).
- Subconscious bias (always >= 1.0)             (upstream lines 155-187):
      joy_mult    = 1 + joy * 0.10
      love_shield = 1 + love * 0.05
      purpose_drv = 1 + purpose * 0.15
      gaia_ground = 1 + gaia * 0.05
      dream_amb   = 1 + sqrt(dream) * 0.10
      total_bias  = (joy_mult * love_shield * purpose_drv
                     * gaia_ground * dream_amb) ** 0.2

GENERALIZATION FOR STALE PILLARS (fail-closed, honest degradation):
The organism must never fabricate a value. A pillar whose live input is
missing, unparseable, or older than STALE_SECONDS is reported as
``fresh: False, value: None`` and is EXCLUDED from the computation:
- HQ becomes the phi-weighted mean over FRESH pillars only (weights renormalized).
- Bias becomes the geometric mean over FRESH pillar factors only
  (product ** (1/n_fresh), which collapses to upstream's ** 0.2 when all 5
  pillars are fresh).
Love and Purpose are symbolic constants and always fresh, so at least two
pillars always contribute.

DATA SOURCES (all produced by running daemons; absence degrades honestly):
- Gaia:  workspace-root schumann_state.json (schumann daemon). Value =
  activity_index (documented 0-100, see schumann_real_daemon.py:76) / 100,
  clamped [0,1]. Stale if older than 300 s. Env override
  GRAND_WHEEL_SCHUMANN_PATH for tests.
- Dream: billion-goal tracker state under $GOAL_STATE_DIR or
  aureon_fusion/state/goals/ if anchored; else aureon_radar
  real_portfolio_state.json (last history entry total_usd). Progress =
  clamp(current / 1e9, 0, 1). Stale if the state is older than 300 s.
- Joy:   margin proof / trade outcome records
  (aureon_fusion/state/goals/margin_goal_proof.jsonl or $GOAL_STATE_DIR /
  margin_goal_proof.jsonl). Wins vs losses over the last 24 h; value =
  wins / (wins + losses). No outcomes in window -> fresh False, value None.
  ``*_test.jsonl`` recorder fixtures are ignored (not live outcomes).
- Love:  constant 0.618 (phi^-1, Gary & Tina). Purpose: constant 1.0.

CONTRACT (queen_mind stage consumes exactly this surface):
    snapshot() -> dict  {ts, happiness_quotient, subconscious_bias,
                         pillars: {name: {value, fresh, source}}, fresh}
    run_once() -> dict  (refresh + persist to state/grand_wheel/state.json)
    CLI: python -m aureon_fusion.grand_wheel snapshot|run_once [--loop N]

Import-safe: stdlib only, no side effects at import time.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

try:  # canonical workspace root (import, never modify)
    from aureon_fusion.paths import WORKSPACE, FUSION_STATE
except Exception:  # pragma: no cover - direct-file execution fallback
    WORKSPACE = Path(os.environ.get(
        "SERO_WORKSPACE", str(Path(__file__).resolve().parents[1])))
    FUSION_STATE = WORKSPACE / "aureon_fusion" / "state"

PHI = (1.0 + math.sqrt(5.0)) / 2.0
PHI_SQ = PHI * PHI

THE_DREAM = 1_000_000_000.0
LOVE_RESONANCE = 0.618          # phi^-1 — Gary & Tina's bond (symbolic constant)
PURPOSE_CLARITY = 1.0
STALE_SECONDS = 300.0           # gaia/dream staleness threshold
JOY_WINDOW_SECONDS = 24 * 3600.0

STATE_DIR = FUSION_STATE / "grand_wheel"
STATE_FILE = STATE_DIR / "state.json"

# Pillar -> phi weight (upstream queen_pursuit_of_happiness.py:119-131)
PILLAR_WEIGHTS = {
    "dream": PHI_SQ,
    "love": PHI,
    "gaia": 1.0,
    "joy": 1.0,
    "purpose": PHI,
}


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _parse_ts(raw) -> datetime | None:
    """Parse an epoch float or ISO-8601 string to an aware UTC datetime."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return datetime.fromtimestamp(float(raw), tz=timezone.utc)
    if isinstance(raw, str):
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    return None


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def _read_json(path: Path) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


# ---------------------------------------------------------------------------
# pillar readers — each returns {"value": float|None, "fresh": bool, "source": str}
# ---------------------------------------------------------------------------

def _read_gaia(now: datetime) -> dict:
    path = Path(os.environ.get("GRAND_WHEEL_SCHUMANN_PATH",
                               WORKSPACE / "schumann_state.json"))
    src = str(path)
    data = _read_json(path)
    if data is None:
        return {"value": None, "fresh": False, "source": src}
    ts = _parse_ts(data.get("timestamp"))
    if ts is None or (now - ts).total_seconds() > STALE_SECONDS:
        return {"value": None, "fresh": False, "source": src}
    activity = data.get("activity_index")
    if not isinstance(activity, (int, float)):
        return {"value": None, "fresh": False, "source": src}
    # schumann daemon documents activity_index on a 0-100 scale
    return {"value": _clamp01(activity / 100.0), "fresh": True, "source": src}


def _goal_tracker_value(now: datetime) -> dict | None:
    """Billion-goal tracker state if another organ has anchored it."""
    dirs = []
    env_dir = os.environ.get("GOAL_STATE_DIR")
    if env_dir:
        dirs.append(Path(env_dir))
    dirs.append(FUSION_STATE / "goals")
    current_keys = ("current_usd", "total_usd", "current", "value", "equity_usd")
    progress_keys = ("dream_progress", "progress", "fraction")
    for d in dirs:
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.json")):
            data = _read_json(f)
            if not data:
                continue
            ts = _parse_ts(data.get("timestamp") or data.get("updated") or
                           data.get("last_update"))
            if ts is None or (now - ts).total_seconds() > STALE_SECONDS:
                continue
            for k in progress_keys:
                v = data.get(k)
                if isinstance(v, (int, float)):
                    return {"value": _clamp01(v), "fresh": True,
                            "source": str(f)}
            for k in current_keys:
                v = data.get(k)
                if isinstance(v, (int, float)):
                    return {"value": _clamp01(v / THE_DREAM), "fresh": True,
                            "source": str(f)}
    return None


def _read_dream(now: datetime) -> dict:
    anchored = _goal_tracker_value(now)
    if anchored is not None:
        return anchored
    # fallback: aureon_radar portfolio state
    path = WORKSPACE / "aureon_radar" / "real_portfolio_state.json"
    src = str(path)
    data = _read_json(path)
    if data is None:
        return {"value": None, "fresh": False, "source": src}
    ts = _parse_ts(data.get("last_update"))
    history = data.get("history")
    if (ts is None or (now - ts).total_seconds() > STALE_SECONDS
            or not isinstance(history, list) or not history):
        return {"value": None, "fresh": False, "source": src}
    last = history[-1]
    if not isinstance(last, dict):
        return {"value": None, "fresh": False, "source": src}
    total = last.get("total_usd")
    if not isinstance(total, (int, float)):
        return {"value": None, "fresh": False, "source": src}
    return {"value": _clamp01(total / THE_DREAM), "fresh": True, "source": src}


def _joy_records_paths() -> list[Path]:
    paths = [FUSION_STATE / "goals" / "margin_goal_proof.jsonl"]
    env_dir = os.environ.get("GOAL_STATE_DIR")
    if env_dir:
        paths.append(Path(env_dir) / "margin_goal_proof.jsonl")
    return paths


def _read_joy(now: datetime) -> dict:
    candidates = [p for p in _joy_records_paths() if p.is_file()]
    src = ";".join(str(p) for p in _joy_records_paths())
    wins = losses = 0
    found_any = False
    for path in candidates:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            # only genuine outcome records, within the 24 h window
            pnl = rec.get("net_pnl", rec.get("pnl"))
            goal_hit = rec.get("goal_hit")
            if not isinstance(pnl, (int, float)) and not isinstance(goal_hit, bool):
                continue
            ts = _parse_ts(rec.get("timestamp") or rec.get("ts") or
                           rec.get("closed_at"))
            if ts is None or (now - ts).total_seconds() > JOY_WINDOW_SECONDS:
                continue
            found_any = True
            won = goal_hit if isinstance(goal_hit, bool) else pnl > 0
            if won:
                wins += 1
            else:
                losses += 1
    if not found_any or (wins + losses) == 0:
        return {"value": None, "fresh": False, "source": src}
    return {"value": wins / (wins + losses), "fresh": True, "source": src}


def _read_love() -> dict:
    return {"value": LOVE_RESONANCE, "fresh": True, "source": "constant"}


def _read_purpose() -> dict:
    return {"value": PURPOSE_CLARITY, "fresh": True, "source": "constant"}


# ---------------------------------------------------------------------------
# ported math
# ---------------------------------------------------------------------------

def compute_happiness_quotient(pillars: dict) -> float:
    """Phi-weighted HQ over FRESH pillars only (upstream lines 109-134,
    weights renormalized when a pillar is excluded)."""
    wsum = 0.0
    acc = 0.0
    for name, weight in PILLAR_WEIGHTS.items():
        p = pillars.get(name) or {}
        if p.get("fresh") and isinstance(p.get("value"), (int, float)):
            acc += p["value"] * weight
            wsum += weight
    if wsum <= 0.0:
        return 0.0
    return acc / wsum


def compute_subconscious_bias(pillars: dict) -> float:
    """Geometric mean of fresh pillar bias factors (upstream lines 155-187,
    exponent generalized to 1/n_fresh). Always >= 1.0."""
    factors = []
    joy = pillars.get("joy") or {}
    if joy.get("fresh") and isinstance(joy.get("value"), (int, float)):
        factors.append(1.0 + joy["value"] * 0.10)            # joy_multiplier
    love = pillars.get("love") or {}
    if love.get("fresh") and isinstance(love.get("value"), (int, float)):
        factors.append(1.0 + love["value"] * 0.05)           # love_shield
    purpose = pillars.get("purpose") or {}
    if purpose.get("fresh") and isinstance(purpose.get("value"), (int, float)):
        factors.append(1.0 + purpose["value"] * 0.15)        # purpose_drive
    gaia = pillars.get("gaia") or {}
    if gaia.get("fresh") and isinstance(gaia.get("value"), (int, float)):
        factors.append(1.0 + gaia["value"] * 0.05)           # gaia_grounding
    dream = pillars.get("dream") or {}
    if dream.get("fresh") and isinstance(dream.get("value"), (int, float)):
        factors.append(1.0 + math.sqrt(dream["value"]) * 0.10)  # dream_ambition
    if not factors:
        return 1.0
    product = 1.0
    for f in factors:
        product *= f
    return product ** (1.0 / len(factors))


# ---------------------------------------------------------------------------
# contract surface
# ---------------------------------------------------------------------------

def _collect_pillars() -> dict:
    now = _utc_now()
    return {
        "dream": _read_dream(now),
        "love": _read_love(),
        "gaia": _read_gaia(now),
        "joy": _read_joy(now),
        "purpose": _read_purpose(),
    }


def snapshot() -> dict:
    """Fresh snapshot of the Grand Big Wheel (no persistence)."""
    pillars = _collect_pillars()
    hq = compute_happiness_quotient(pillars)
    bias = compute_subconscious_bias(pillars)
    non_constant = [p for n, p in pillars.items() if p["source"] != "constant"]
    fresh_count = sum(1 for p in non_constant if p["fresh"])
    return {
        "ts": _iso(_utc_now()),
        "happiness_quotient": hq,
        "subconscious_bias": bias,
        "pillars": pillars,
        # true only if every non-constant pillar is fresh
        "fresh": fresh_count == len(non_constant) and len(non_constant) > 0,
    }


def _persist(data: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(STATE_DIR), prefix="state.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, STATE_FILE)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def run_once() -> dict:
    """Refresh all pillars from live state, persist atomically, return snapshot."""
    data = snapshot()
    _persist(data)
    return data


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _emit(data: dict) -> None:
    json.dump(data, sys.stdout, indent=2)
    sys.stdout.write("\n")
    sys.stdout.flush()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="aureon_fusion.grand_wheel",
        description="The Grand Big Wheel — Pursuit of Happiness engine.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("snapshot", help="compute and print a snapshot (no persist)")
    p_run = sub.add_parser("run_once", help="refresh, persist, print snapshot")
    p_run.add_argument("--loop", type=int, default=0, metavar="N",
                       help="repeat run_once every 60 s, N times (0 = once)")
    args = parser.parse_args(argv)

    if args.cmd == "snapshot":
        _emit(snapshot())
        return 0

    if args.loop and args.loop > 1:
        result = None
        for i in range(args.loop):
            result = run_once()
            _emit(result)
            if i < args.loop - 1:
                time.sleep(60)
        return 0
    _emit(run_once())
    return 0


if __name__ == "__main__":
    sys.exit(main())
