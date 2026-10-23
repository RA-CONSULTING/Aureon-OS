#!/usr/bin/env python3
"""_harmonic_seed_loop.py — live producer for the HarmonicWaveFusion seed cache.

Problem fixed: state/harmonic_phase.json reported
  "harmonic_engine_unavailable: seed cache missing/stale/unreadable"
because nothing refreshed harmonic_cache/ (6h TTL) after the upstream engine
stopped running. This script IS the producer:

  --once            Refresh the seed only if the cache is stale (> TTL edge),
                    then re-run harmonic_phase_probe.py so the phase file
                    immediately reflects the fresh engine state. Then refresh
                    seer counsel (harmonic_phase.json 'seer_counsel') via the
                    thin adapter. Exits — safe for one-shot verification.
  --force           With --once: rebuild the seed even if the cache is fresh.
  --daemon          Loop with SEED_LOOP_INTERVAL_S cadence (default 2400s =
                    40min, inside the 30-60min owner band). nohup-able.

The seed is built by the upstream producer, unmodified:
  aureon-os-upstream/aureon/harmonic/aureon_harmonic_seed.py
(HarmonicSeedLoader.load_seed writes harmonic_cache/harmonic_seed.json +
harmonic_seed_meta.json in exactly the canonical shape the probe's
_decode_harmonic_cache validates.)

Run from aureon_radar/ with the upstream on PYTHONPATH:
  PYTHONUTF8=1 PYTHONPATH=<workspace>/aureon-os-upstream python _harmonic_seed_loop.py --once
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

RADAR = Path(__file__).resolve().parent
WORKSPACE = RADAR.parent
UPSTREAM = WORKSPACE / "aureon-os-upstream"
CACHE_DIR = RADAR / "harmonic_cache"
META_PATH = CACHE_DIR / "harmonic_seed_meta.json"
SEED_TTL_S = 6 * 3600.0  # matches HarmonicSeedLoader.load_seed validity
DEFAULT_INTERVAL_S = int(os.getenv("SEED_LOOP_INTERVAL_S", "2400"))
MAX_SYMBOLS = int(os.getenv("SEED_LOOP_MAX_SYMBOLS", "150"))
# The Seer pulls a heavy upstream stack (MinerBrain -> HarmonicWaveFusion);
# first build can exceed 5 min, so the probe timeout is generous.
PROBE_TIMEOUT_S = 900
SEER_TIMEOUT_S = 900


def cache_age_s() -> float | None:
    """Age of the seed cache in seconds; None if meta missing/unreadable."""
    try:
        meta = json.loads(META_PATH.read_text(encoding="utf-8"))
        written = float(meta.get("timestamp", 0.0))
    except (OSError, ValueError, TypeError):
        return None
    if not written:
        return None
    return max(0.0, time.time() - written)


def refresh_seed() -> dict:
    """Rebuild the seed cache via the upstream producer. Raises on failure."""
    from aureon.harmonic.aureon_harmonic_seed import HarmonicSeedLoader

    loader = HarmonicSeedLoader(cache_dir=str(CACHE_DIR))
    state = loader.load_seed(max_symbols=MAX_SYMBOLS, force_refresh=True)
    return {
        "symbols": len(state.symbols),
        "regime": str(state.market_regime),
        "global_coherence": round(float(state.global_coherence), 6),
        "dominant_frequency": round(float(state.dominant_frequency), 6),
    }


def run_probe(script: str, timeout_s: int) -> tuple[bool, str]:
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONPATH"] = str(UPSTREAM) + os.pathsep + env.get("PYTHONPATH", "")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        p = subprocess.run(
            [sys.executable, str(RADAR / script)],
            cwd=str(RADAR), env=env, capture_output=True, text=True,
            timeout=timeout_s,
        )
        tail = (p.stdout or "").strip().splitlines()
        detail = tail[-1][:160] if tail else "(no output)"
        return p.returncode == 0, f"rc={p.returncode} {detail}"
    except subprocess.TimeoutExpired:
        return False, f"timeout({timeout_s}s)"
    except Exception as exc:  # noqa: BLE001 - loop must never die
        return False, f"{type(exc).__name__}: {exc}"


def one_round(force: bool = False) -> int:
    age = cache_age_s()
    stale = age is None or age >= SEED_TTL_S * 0.9  # refresh at 90% of TTL
    rc = 0
    if stale or force:
        why = "forced" if force and not stale else (
            "missing/unreadable meta" if age is None else f"stale (age {age/3600:.2f}h)")
        print(f"[seed] rebuilding harmonic seed ({why})...", flush=True)
        try:
            info = refresh_seed()
            print(f"[seed] rebuilt: {info}", flush=True)
        except Exception as exc:  # noqa: BLE001 - report, keep old cache
            print(f"[seed] FAIL: {type(exc).__name__}: {exc}", flush=True)
            rc = 1
    else:
        print(f"[seed] cache fresh (age {age/3600:.2f}h) — skipping rebuild", flush=True)

    ok, detail = run_probe("harmonic_phase_probe.py", PROBE_TIMEOUT_S)
    print(f"[probe] harmonic_phase_probe: {'ok' if ok else 'FAIL'} | {detail}", flush=True)
    if not ok:
        rc = 1

    ok, detail = run_probe("_seer_counsel_adapter.py", SEER_TIMEOUT_S)
    print(f"[seer] counsel adapter: {'ok' if ok else 'FAIL'} | {detail}", flush=True)
    # Seer counsel is fail-closed: a failure is logged and written as
    # seer_counsel:null with the reason; it does NOT fail the seed loop.
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(description="Harmonic seed cache producer loop")
    ap.add_argument("--once", action="store_true", help="single round, then exit")
    ap.add_argument("--force", action="store_true", help="rebuild seed even if fresh")
    ap.add_argument("--daemon", action="store_true", help="loop every SEED_LOOP_INTERVAL_S")
    args = ap.parse_args()

    if not (UPSTREAM / "aureon" / "harmonic" / "aureon_harmonic_seed.py").exists():
        print(f"[seed] FAIL: upstream producer not found at {UPSTREAM}", flush=True)
        return 1

    if args.daemon:
        print(f"[seed] daemon online (interval {DEFAULT_INTERVAL_S}s)", flush=True)
        while True:
            started = time.time()
            try:
                one_round(force=args.force)
            except Exception as exc:  # noqa: BLE001
                print(f"[seed] round error: {type(exc).__name__}: {exc}", flush=True)
            elapsed = time.time() - started
            time.sleep(max(30.0, DEFAULT_INTERVAL_S - elapsed))
    return one_round(force=args.force)


if __name__ == "__main__":
    sys.exit(main())
