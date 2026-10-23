#!/usr/bin/env python3
"""Harmonic phase probe — Queen Sero's non-linear temporal sense (owner decree 2026-09-06).

Writes aureon_radar/state/harmonic_phase.json:

    {
      "ts": float, "ts_iso": str,
      "field": {
        "global_coherence": float|null,
        "dominant_freq_cycles_per_day": float|null,
        "schumann_align": float|null,
        "regime": str|null,
        "source": str|null,            # provenance, never omitted when values exist
        "engine_cache_age_s": float|null,
        "symbol_count": int|null
      },
      "symbols": {
        "BTCUSD": {"phase_radians": float|null, "phase_hint": str|null,
                   "coherence": float|null, "resonance_score": float|null,
                   "dominant_freq_cycles_per_day": float|null, "error": str|null},
        "ETHUSD": { ... }
      },
      "qgita": {
        "golden_ratio_resonance": float|null,
        "source_law_entry": float|null,
        "source_law_exit": float|null,
        "error": str|null
      },
      "errors": [str]
    }

DATA PROVENANCE (fail-closed, no fabricated data presented as live):
  1. Real field state: the harmonic engine's seed cache (harmonic_cache/harmonic_seed.json,
     written by the running HarmonicWaveFusion engine, valid 6h). Used for field metrics
     and for any symbol present in it.
  2. Fallback: real public Binance hourly klines (api.binance.com, no auth — same public
     data path as exchange_adapters/price_cache) computed through the upstream
     HarmonicSeedLoader math (Hilbert phase, FFT dominant frequency, split-half coherence).
  3. Neither available -> null + error entry. Nothing synthetic is ever emitted.

phase_hint convention (sinusoid sin(theta), theta normalized to [0, 2pi)):
  crest |theta - pi/2| < pi/4 ; trough |theta - 3pi/2| < pi/4 ;
  else rising where d(sin)/dtheta = cos(theta) > 0, falling otherwise.

Usage:
  cd aureon_radar && set -a && . ./.env && set +a && \
    PYTHONUTF8=1 PYTHONPATH=<workspace>/aureon-os-upstream python harmonic_phase_probe.py
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger("harmonic_phase_probe")

_RADAR_ROOT = Path(__file__).resolve().parent
_STATE_PATH = _RADAR_ROOT / "state" / "harmonic_phase.json"
_SEED_CACHE_TTL_S = 6 * 3600.0  # matches HarmonicSeedLoader.load_seed validity
_BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
_REQUEST_TIMEOUT = 20.0
_SYMBOLS = {"BTCUSD": "BTCUSDT", "ETHUSD": "ETHUSDT"}  # radar name -> Binance pair
PHI = (1 + math.sqrt(5)) / 2
SCHUMANN_BASE = 7.83
_FIB_WINDOWS = (5, 8, 13, 21, 34, 55)  # QGITA fib time lattice (hours)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fetch_binance_klines(pair: str, limit: int = 168) -> List[Dict[str, float]]:
    """Real public Binance hourly klines. Raises on any failure (fail-closed)."""
    resp = requests.get(
        _BINANCE_KLINES_URL,
        params={"symbol": pair, "interval": "1h", "limit": limit},
        timeout=_REQUEST_TIMEOUT,
        headers={"User-Agent": "aureon-harmonic-phase-probe/1.0"},
    )
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code} from binance klines for {pair}")
    rows = resp.json()
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(f"binance returned no klines for {pair}")
    candles = []
    for c in rows:
        candles.append({
            "timestamp": float(c[0]) / 1000.0,
            "open": float(c[1]),
            "high": float(c[2]),
            "low": float(c[3]),
            "close": float(c[4]),
            "volume": float(c[5]),
        })
    return candles


def _load_engine_state(cache_dir: Path) -> Optional[Dict[str, Any]]:
    """Load the running engine's seed state if its cache is fresh.

    Returns {"state": GlobalHarmonicState, "age_s": float} or None.
    Does NOT rebuild the seed (no heavy network crawl from a probe); freshness
    is the engine's own liveness signal, mirroring load_seed's 6h validity.
    """
    try:
        from aureon.harmonic.aureon_harmonic_seed import (
            GlobalHarmonicState,
            _decode_harmonic_cache,
        )
    except Exception as exc:  # upstream unavailable -> caller falls back
        logger.warning("harmonic seed module unavailable: %s", exc)
        return None

    meta_path = cache_dir / "harmonic_seed_meta.json"
    cache_path = cache_dir / "harmonic_seed.json"
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        written = float(meta.get("timestamp", 0.0))
    except (OSError, ValueError, TypeError):
        return None
    age_s = time.time() - written
    if not written or age_s >= _SEED_CACHE_TTL_S:
        logger.info("engine seed cache missing/stale (age %.0fs) — using klines fallback", age_s)
        return None
    try:
        decoded = _decode_harmonic_cache(cache_path.read_bytes())
        state = GlobalHarmonicState.from_dict(decoded)
    except Exception as exc:
        logger.warning("engine seed cache unreadable: %s", exc)
        return None
    return {"state": state, "age_s": age_s}


def _engine_symbol_key(state_symbols: Dict[str, Any], radar_name: str) -> Optional[str]:
    """Find the engine's key for a radar symbol (e.g. BTCUSD -> BTCUSDT@binance)."""
    base = radar_name.upper().replace("USD", "")
    candidates = (
        f"{base}USDT@binance", f"{base}USD@binance",
        f"{base}USD@kraken", f"X{base}USD@kraken",
        f"X{base}ZUSD@kraken", f"XX{base}ZUSD@kraken",
        f"{base}USDC@binance",
    )
    for cand in candidates:
        if cand in state_symbols:
            return cand
    return None  # no fuzzy matching: a wrong symbol is worse than an honest fallback


def _phase_hint(phase_rad: float) -> str:
    theta = phase_rad % (2 * math.pi)
    if abs(theta - math.pi / 2) < math.pi / 4:
        return "crest"
    if abs(theta - 3 * math.pi / 2) < math.pi / 4:
        return "trough"
    return "rising" if math.cos(theta) > 0 else "falling"


def _schumann_factor(freq_cycles_per_day: float) -> float:
    """Same math the engine uses: 1/(1 + min distance to Schumann harmonics)."""
    harmonics = [SCHUMANN_BASE * n for n in range(1, 15)]
    min_dist = min(abs(freq_cycles_per_day - h) for h in harmonics)
    return 1.0 / (1.0 + min_dist)


def _symbol_block_from_wave_state(ws: Any, source: str) -> Dict[str, Any]:
    coherence = max(0.0, min(1.0, float(ws.coherence)))
    schumann = _schumann_factor(float(ws.frequency))
    return {
        "phase_radians": round(float(ws.phase), 6),
        "phase_hint": _phase_hint(float(ws.phase)),
        "coherence": round(coherence, 6),
        "resonance_score": round(coherence * schumann, 6),
        "dominant_freq_cycles_per_day": round(float(ws.frequency), 6),
        "error": None,
        "source": source,
    }


def _golden_ratio_resonance(closes: List[float]) -> Optional[float]:
    """QGITA-flavoured golden-ratio resonance from REAL klines.

    For each Fibonacci hourly window, ratio = |sum(positive log returns) /
    sum(negative log returns)|; resonance per window = exp(-|ln(ratio/PHI)|).
    Windows are weighted 1/length (short cycles dominate, as in the QGITA lattice).
    """
    if len(closes) < max(_FIB_WINDOWS) + 1:
        return None
    logrets = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes)) if closes[i - 1] > 0]
    weighted = 0.0
    weight_sum = 0.0
    for length in _FIB_WINDOWS:
        window = logrets[-length:]
        gains = sum(r for r in window if r > 0)
        losses = abs(sum(r for r in window if r < 0))
        if losses > 0:
            ratio = gains / losses
        elif gains > 0:
            ratio = PHI  # one-way move: treat as perfectly golden-trending
        else:
            continue
        resonance = math.exp(-abs(math.log(ratio / PHI)))
        w = 1.0 / length
        weighted += resonance * w
        weight_sum += w
    return round(weighted / weight_sum, 6) if weight_sum > 0 else None


def main() -> int:
    try:
        from aureon.utils.console_utf8 import ensure_utf8_stdout
        ensure_utf8_stdout()
    except Exception:
        pass
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    errors: List[str] = []
    now = time.time()
    doc: Dict[str, Any] = {
        "ts": now,
        "ts_iso": _utc_iso(),
        "field": {
            "global_coherence": None,
            "dominant_freq_cycles_per_day": None,
            "schumann_align": None,
            "regime": None,
            "source": None,
            "engine_cache_age_s": None,
            "symbol_count": None,
        },
        "symbols": {},
        "qgita": {
            "golden_ratio_resonance": None,
            "source_law_entry": None,
            "source_law_exit": None,
            "error": None,
        },
        "errors": errors,
    }

    # ── Field state: engine seed cache if fresh, else honest nulls ──────────
    engine = _load_engine_state(_RADAR_ROOT / "harmonic_cache")
    engine_symbols: Dict[str, Any] = {}
    if engine is not None:
        st = engine["state"]
        engine_symbols = st.symbols
        doc["field"].update({
            "global_coherence": round(float(st.global_coherence), 6),
            "dominant_freq_cycles_per_day": round(float(st.dominant_frequency), 6),
            "schumann_align": round(float(st.schumann_alignment), 6),
            "regime": str(st.market_regime),
            "source": "harmonic_engine_seed_cache",
            "engine_cache_age_s": round(float(engine["age_s"]), 1),
            "symbol_count": len(engine_symbols),
        })
    else:
        errors.append("harmonic_engine_unavailable: seed cache missing/stale/unreadable")

    # ── Symbol phase: engine state first, real Binance klines otherwise ─────
    klines_cache: Dict[str, List[Dict[str, float]]] = {}
    seed_loader = None
    for radar_name, pair in _SYMBOLS.items():
        block: Dict[str, Any] = {
            "phase_radians": None, "phase_hint": None, "coherence": None,
            "resonance_score": None, "dominant_freq_cycles_per_day": None,
            "error": None, "source": None,
        }
        key = _engine_symbol_key(engine_symbols, radar_name) if engine_symbols else None
        if key is not None:
            block = _symbol_block_from_wave_state(engine_symbols[key], f"engine:{key}")
            doc["symbols"][radar_name] = block
            continue
        # Fallback: compute from real public Binance hourly klines.
        try:
            if pair not in klines_cache:
                klines_cache[pair] = _fetch_binance_klines(pair)
            candles = klines_cache[pair]
            if seed_loader is None:
                from aureon.harmonic.aureon_harmonic_seed import HarmonicSeedLoader
                # build_wave_state is pure math (no cache/exchange access); the
                # loader's cache_dir is only a mkdir(exist_ok=True) side effect.
                seed_loader = HarmonicSeedLoader(cache_dir=str(_RADAR_ROOT / "harmonic_cache"))
            ws = seed_loader.build_wave_state(f"{pair}@binance", candles)
            if ws is None:
                raise RuntimeError(f"build_wave_state returned None for {pair} ({len(candles)} candles)")
            block = _symbol_block_from_wave_state(ws, f"binance_klines:{pair}")
        except Exception as exc:
            block["error"] = f"{type(exc).__name__}: {exc}"
            errors.append(f"{radar_name}: {block['error']}")
        doc["symbols"][radar_name] = block

    # If the engine field is absent but klines worked, derive an honest field from
    # the two probed symbols and mark it partial — never presented as the engine.
    if doc["field"]["source"] is None:
        live = [b for b in doc["symbols"].values() if b.get("error") is None]
        if live:
            coh = sum(b["coherence"] for b in live) / len(live)
            freq = sum(b["dominant_freq_cycles_per_day"] for b in live) / len(live)
            doc["field"].update({
                "global_coherence": round(coh, 6),
                "dominant_freq_cycles_per_day": round(freq, 6),
                "schumann_align": round(_schumann_factor(freq), 6),
                "regime": None,
                "source": "binance_klines_partial(BTCUSD,ETHUSD only)",
                "symbol_count": len(live),
            })
        else:
            errors.append("field: no harmonic engine state and no klines — field left null")

    # ── QGITA layer: golden-ratio resonance (real klines) + source law gates ─
    try:
        from aureon.queen.queen_source_law import ENTRY_COHERENCE, EXIT_COHERENCE
        doc["qgita"]["source_law_entry"] = float(ENTRY_COHERENCE)
        doc["qgita"]["source_law_exit"] = float(EXIT_COHERENCE)
    except Exception as exc:
        doc["qgita"]["error"] = f"source_law import failed: {type(exc).__name__}: {exc}"
        errors.append(doc["qgita"]["error"])
    try:
        closes: Optional[List[float]] = None
        btc = doc["symbols"].get("BTCUSD") or {}
        if btc.get("error") is None and btc.get("source", "").startswith("binance_klines"):
            closes = [c["close"] for c in klines_cache.get(_SYMBOLS["BTCUSD"], [])]
        if closes is None:
            pair = _SYMBOLS["BTCUSD"]
            if pair not in klines_cache:
                klines_cache[pair] = _fetch_binance_klines(pair)
            closes = [c["close"] for c in klines_cache[pair]]
        doc["qgita"]["golden_ratio_resonance"] = _golden_ratio_resonance(closes)
        if doc["qgita"]["golden_ratio_resonance"] is None:
            raise RuntimeError("insufficient kline history for fib windows")
    except Exception as exc:
        doc["qgita"]["error"] = f"golden_ratio_resonance unavailable: {type(exc).__name__}: {exc}"
        errors.append(doc["qgita"]["error"])

    # ── Atomic write + stdout proof ──────────────────────────────────────────
    out = json.dumps(doc, indent=2, ensure_ascii=False, allow_nan=False)
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(_STATE_PATH.parent), prefix=".harmonic_phase_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(out)
        os.replace(tmp, _STATE_PATH)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
