#!/usr/bin/env python3
"""Multiverse Outlook — Queen Sero's temporal sense over the quantum vacuum.

Owner decree 2026-09-06: phase in and out of the quantum vacuum (multiverse
simulation) to see best outcomes and quickest energy-capture paths.

This tool is PERCEPTION ONLY:
    • Prices come from the shared public PriceCache (real market data,
      fail-closed: any fetch error yields price=None + error, never synthetic).
    • The Internal Multiverse (10-9-1-10) runs consensus over those REAL
      prices/changes/momenta — no fabricated market inputs.
    • The Temporal Dialer probes the Global Harmonic Field for the vacuum
      phase. If the field is unreachable, vacuum_phase is fail-closed
      (in_vacuum=False, phase_hint=None, error recorded).
    • Nothing here trades. Capital stays gated.

Writes aureon_radar/state/multiverse_outlook.json:
    {
      "ts": <unix>, "ts_iso": <utc iso>,
      "worlds": [{"name", "strategy", "symbol", "consensus_bias",
                  "best_outcome_hint", "capture_speed_hint", "confidence"}],
      "omega": {"reaction_ms", "sweep_bias"},
      "vacuum_phase": {"in_vacuum", "phase_hint"},
      "field_regime": str|null, "field_regime_basis": str,
      "best_outcomes": [{symbol, world, direction, score, consensus_bias,
                         confidence, expectancy_usd, expected_capture_min,
                         price_at_birth, rank, derivation}],
      "prophecy": {"recorded", "claims", "horizon_min", "db"|"error"},
      "errors": [...],
      "inputs": {"prices": {...}, "changes_pct": {...}, "as_of": {...}}
                 (inputs is the raw real data the outlook was computed from)
    }

Prophecy recorder: each world's numeric claim is persisted into the
bitemporal forecasts table of aureon_fusion/state/aureon_global_history.sqlite
via the upstream insert_forecast() (target_ts_ms = as_of + 30min default).
field_regime/best_outcomes exist because temporal_cognition.extract_multiverse
expects that schema; both are derived honestly from the computed worlds
(dispersion/agreement regime; ranking by consensus*confidence) — null/empty
when the worlds carry no numeric claims, never fabricated.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_RADAR_ROOT = Path(__file__).resolve().parent
_STATE_PATH = _RADAR_ROOT / "state" / "multiverse_outlook.json"
_HISTORY_PATH = _RADAR_ROOT / "state" / "multiverse_outlook_history.json"
_WORKSPACE = _RADAR_ROOT.parent
_HISTORY_DB_PATH = _WORKSPACE / "aureon_fusion" / "state" / "aureon_global_history.sqlite"
_FORECAST_MODEL = "multiverse_outlook"
# Prophecy horizon for recorded world claims (target_ts_ms = as_of + horizon).
_PROPHECY_HORIZON_MIN = float(os.getenv("AUREON_PROPHECY_HORIZON_MIN", "30") or "30")

_SYMBOLS = ("BTCUSDT", "ETHUSDT")
# Kraken uses XBT; price_cache handles the mapping for BTCUSD/ETHUSD.
_KRAKEN_SYMBOLS = ("BTCUSD", "ETHUSD")

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("multiverse_outlook")


# ── data acquisition (fail-closed, real public data only) ──────────────────

def _fetch_prices(cache) -> Dict[str, Dict[str, Any]]:
    """Binance primary + Kraken cross-check through the shared price cache.

    Returns {symbol: {"price": float|None, "as_of": str|None,
                      "kraken_price": float|None, "errors": [str]}}.
    """
    out: Dict[str, Dict[str, Any]] = {}
    for sym in _SYMBOLS:
        out[sym] = {"price": None, "as_of": None, "kraken_price": None, "errors": []}

    for sym in _SYMBOLS:
        r = cache.get_price(sym, source="binance")
        if r.get("price") is not None and not r.get("error"):
            out[sym]["price"] = float(r["price"])
            out[sym]["as_of"] = r.get("as_of")
        else:
            out[sym]["errors"].append(f"binance {sym}: {r.get('error') or 'no price'}")

    for sym, ksym in zip(_SYMBOLS, _KRAKEN_SYMBOLS):
        r = cache.get_price(ksym, source="kraken")
        if r.get("price") is not None and not r.get("error"):
            out[sym]["kraken_price"] = float(r["price"])
        else:
            out[sym]["errors"].append(f"kraken {ksym}: {r.get('error') or 'no price'}")
    return out


def _load_history() -> Dict[str, List[Dict[str, float]]]:
    try:
        with open(_HISTORY_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if isinstance(v, list)}
    except (OSError, json.JSONDecodeError):
        pass
    return {s: [] for s in _SYMBOLS}


def _save_history(history: Dict[str, List[Dict[str, float]]]) -> None:
    try:
        _HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_HISTORY_PATH, "w", encoding="utf-8") as fh:
            json.dump(history, fh)
    except OSError as exc:
        logger.warning("history write failed: %s", exc)


def _snapshot() -> Dict[str, Optional[float]]:
    """One fresh price snapshot per symbol (dedicated cache: no stale/error state)."""
    from exchange_adapters.price_cache import PriceCache
    cache = PriceCache(ttl_seconds=0.0)
    out: Dict[str, Optional[float]] = {}
    for sym in _SYMBOLS:
        r = cache.get_price(sym, source="binance")
        out[sym] = float(r["price"]) if r.get("price") is not None and not r.get("error") else None
    return out


def _measure_momentum(errors: List[str], settle_seconds: float = 6.0) -> Dict[str, float]:
    """Real momentum: two live snapshots separated by a settle window.

    The intra-run pair proves momentum on a first-ever run; the persisted
    history widens the window on subsequent runs. Fail-closed: no real pair
    -> 0.0 with an explicit error (never fabricated).
    """
    first = _snapshot()
    time.sleep(max(1.0, settle_seconds))
    second = _snapshot()

    history = _load_history()
    now = time.time()
    momentum: Dict[str, float] = {}
    for sym in _SYMBOLS:
        p0, p1 = first.get(sym), second.get(sym)
        if p0 and p1 and p0 > 0:
            # Real window velocity: fractional change across the settle window.
            momentum[sym] = (p1 - p0) / p0
        else:
            # Fall back to the oldest persisted real snapshot vs now.
            hist = sorted((h for h in history.get(sym, []) if h.get("price")),
                          key=lambda h: h["ts"])
            ref = hist[0] if hist else None
            if ref and p1 and ref["price"] > 0:
                momentum[sym] = (p1 - ref["price"]) / ref["price"]
            else:
                momentum[sym] = 0.0
                errors.append(f"momentum {sym}: no real two-point window; neutral (fail-closed)")
        if p1:
            history.setdefault(sym, []).append({"ts": now, "price": p1})
            history[sym] = history[sym][-288:]
    _save_history(history)

    # changes_pct from the same real pair (or history fallback).
    changes: Dict[str, float] = {}
    for sym in _SYMBOLS:
        p0, p1 = first.get(sym), second.get(sym)
        if p0 and p1 and p0 > 0:
            changes[sym] = (p1 - p0) / p0 * 100.0
        else:
            hist = sorted((h for h in history.get(sym, []) if h.get("price")),
                          key=lambda h: h["ts"])
            if len(hist) >= 2 and p1:
                changes[sym] = (p1 - hist[0]["price"]) / hist[0]["price"] * 100.0
            else:
                changes[sym] = 0.0
    return momentum, changes, second, max(settle_seconds, 1.0)


# ── vacuum phase (temporal dialer → global harmonic field) ─────────────────

def _vacuum_phase(prices: Dict[str, Optional[float]],
                  changes: Dict[str, float],
                  errors: List[str]) -> Dict[str, Any]:
    """Phase into the quantum vacuum via the Temporal Dialer.

    The Global Harmonic Field is fed the REAL prices/changes observed above,
    so the dialer reads a genuinely live field (fail-closed if the feed or
    the read fails: in_vacuum False, phase_hint None, error recorded).
    """
    try:
        from aureon.intelligence.aureon_temporal_dialer import TemporalDialer, SCHUMANN_RESONANCE
        dialer = TemporalDialer("multiverse_outlook")
        field = dialer.field_connection
        btc = prices.get("BTCUSDT")
        if field is not None and hasattr(field, "update_all") and btc:
            try:
                field.update_all(
                    btc_price=float(btc),
                    btc_change=float(changes.get("BTCUSDT", 0.0)),
                )
            except Exception as exc:
                errors.append(f"vacuum_phase feed: {type(exc).__name__}: {exc}")
        dialer.calibrate()
        dialer.tune_frequency(SCHUMANN_RESONANCE, bandwidth=1.0)
        packet = dialer.pull_quantum_data()
        if packet is None:
            errors.append("vacuum_phase: harmonic field returned no live packet (fail-closed)")
            return {"in_vacuum": False, "phase_hint": None}
        payload = packet.payload or {}
        hint = payload.get("field_direction") or payload.get("omega_direction")
        return {"in_vacuum": True, "phase_hint": hint,
                "field_omega": payload.get("field_omega")}
    except Exception as exc:  # field module missing/broken — report, don't fabricate
        errors.append(f"vacuum_phase: {type(exc).__name__}: {exc}")
        return {"in_vacuum": False, "phase_hint": None}


# ── multiverse consensus over real data ────────────────────────────────────

def _run_multiverse(market_data: Dict[str, Dict[str, float]]):
    from aureon.simulation.aureon_internal_multiverse import (
        InternalMultiverse, CONVERTER_REACTION_MS, SWEEP_THRESHOLD_PCT,
    )
    multiverse = InternalMultiverse(initial_equity=100.0)
    multiverse.update_market_data(market_data)
    cycle = multiverse.run_cycle()
    omega = {
        "reaction_ms": CONVERTER_REACTION_MS,
        "sweep_bias": SWEEP_THRESHOLD_PCT,
        "sweeps_observed": len(cycle.get("sweeps", [])),
        "swept_total": cycle.get("converter_stats", {}).get("total_swept"),
    }
    return multiverse, cycle, omega


def _world_outlooks(multiverse, prices: Dict[str, Optional[float]]) -> List[Dict[str, Any]]:
    """Per-world outlook derived from REAL signals on REAL prices.

    Nulls (never fabricated numbers) when a world produced no signal.
    """
    worlds: List[Dict[str, Any]] = []
    for w in multiverse.worlds:
        sig = w.state.last_signal
        entry: Dict[str, Any] = {
            "name": f"{w.emoji} {w.name}".strip(),
            "strategy": w.strategy,
            "symbol": None,
            "consensus_bias": None,
            "best_outcome_hint": None,
            "capture_speed_hint": None,
            "confidence": None,
        }
        if sig is None or not any(prices.values()):
            worlds.append(entry)
            continue
        entry["consensus_bias"] = round(float(sig.strength), 4)
        entry["confidence"] = round(float(sig.confidence), 4)
        direction = {"BUY": "upside capture", "SELL": "downside protection",
                     "HOLD": "capital preservation", "CONVERT": "conversion sweep"}.get(
                         sig.signal_type, "neutral")
        sym = sig.symbol if sig.symbol in prices else None
        entry["symbol"] = sym
        if sym and prices.get(sym):
            entry["best_outcome_hint"] = f"{direction} on {sym} @ {prices[sym]:.2f}"
        else:
            entry["best_outcome_hint"] = f"{direction} (no live price for {sig.symbol})"
        speed = "immediate" if w.aggression >= 0.85 else (
            "fast" if w.aggression >= 0.7 else "measured")
        entry["capture_speed_hint"] = f"{speed} (aggression {w.aggression:.2f}, risk {w.risk_tolerance:.2f})"
        worlds.append(entry)
    return worlds


# ── multiverse-schema fields (temporal_cognition extract_multiverse) ────────

def _derive_field_regime(worlds: List[Dict[str, Any]]) -> Dict[str, Any]:
    """field_regime derived honestly from the numeric world biases.

    Derivation (documented): collect every world's consensus_bias that is a
    real number. Regime is a dispersion/agreement read on those biases:
      - no numeric biases            -> None (fail-closed, never fabricated)
      - |mean| near zero (< 0.05)    -> "neutral"   (worlds cancel out)
      - dispersion <= 25% of |mean|  -> "coherent_constructive" (mean > 0) /
                                        "coherent_destructive"  (mean < 0)
      - otherwise                    -> "mixed"     (high dispersion vs mean)
    Returns {"field_regime": str|None, "field_regime_basis": str}.
    """
    biases = [float(w["consensus_bias"]) for w in worlds
              if isinstance(w.get("consensus_bias"), (int, float))]
    if not biases:
        return {"field_regime": None,
                "field_regime_basis": "no numeric world biases — fail-closed null"}
    n = len(biases)
    mean = sum(biases) / n
    dispersion = (sum((b - mean) ** 2 for b in biases) / n) ** 0.5
    if abs(mean) < 0.05:
        regime = "neutral"
    elif dispersion <= 0.25 * abs(mean):
        regime = "coherent_constructive" if mean > 0 else "coherent_destructive"
    else:
        regime = "mixed"
    basis = (f"mean_bias={mean:.4f} dispersion={dispersion:.4f} over {n} numeric "
             f"world bias(es); regime=dispersion/agreement read (|mean|<0.05 -> "
             f"neutral; dispersion<=25%|mean| -> coherent; else mixed)")
    return {"field_regime": regime, "field_regime_basis": basis}


def _derive_best_outcomes(worlds: List[Dict[str, Any]],
                          prices: Dict[str, Optional[float]],
                          momentum: Dict[str, float],
                          window_s: float) -> List[Dict[str, Any]]:
    """best_outcomes ranked by consensus*confidence (documented derivation).

    Per world with a real numeric claim (symbol + consensus_bias + confidence
    + live price), score = consensus_bias * confidence (signed weighted
    strength in [-1, 1]). Expectancy is derived, never invented:
      - proj_frac = momentum_frac_per_window * (horizon_s / window_s):
        a LABELED linear extrapolation of the real measured settle-window
        momentum across the prophecy horizon.
      - expectancy_usd = 100 * confidence * sign(consensus_bias) * proj_frac
        on the Internal Multiverse's own initial_equity=100 reference basis.
        Negative when real momentum ran against the claim — kept negative so
        downstream gates can filter it out.
      - expected_capture_min = horizon when expectancy > 0 else None (the
        projection matures at the horizon; null-not-0).
    Sorted by expectancy_usd desc, ranked from 1. Empty -> [] (fail-closed).
    """
    horizon_s = _PROPHECY_HORIZON_MIN * 60.0
    claims: List[Dict[str, Any]] = []
    for w in worlds:
        bias, conf, sym = w.get("consensus_bias"), w.get("confidence"), w.get("symbol")
        if not (isinstance(bias, (int, float)) and isinstance(conf, (int, float)) and sym):
            continue
        if float(conf) <= 0 or float(bias) == 0.0:
            continue  # no real claim (zero confidence or zero bias) — fail-closed skip
        price = prices.get(sym)
        if not price:
            continue
        score = float(bias) * float(conf)
        mom_frac = float(momentum.get(sym) or 0.0)
        window = max(float(window_s or 1.0), 1.0)
        proj_frac = mom_frac * (horizon_s / window)
        expectancy_usd = round(100.0 * float(conf) *
                               (1.0 if score >= 0 else -1.0) * proj_frac, 6)
        claims.append({
            "symbol": sym,
            "world": w.get("name"),
            "direction": "up" if score >= 0 else "down",
            "score": round(score, 4),
            "consensus_bias": float(bias),
            "confidence": float(conf),
            "expectancy_usd": expectancy_usd,
            "expected_capture_min": (_PROPHECY_HORIZON_MIN
                                     if expectancy_usd > 0 else None),
            "price_at_birth": round(float(price), 8),
            "truth_status": "derived_estimate",
            "derivation": "score=consensus_bias*confidence; expectancy_usd on "
                          "multiverse initial_equity=100 basis = 100*confidence*"
                          "sign(score)*proj_frac; proj_frac = real settle-window "
                          "momentum linearly extrapolated across the prophecy "
                          "horizon (labeled estimate, null fields when inputs "
                          "absent — never fabricated)",
        })
    claims.sort(key=lambda c: c["expectancy_usd"], reverse=True)
    for i, c in enumerate(claims, 1):
        c["rank"] = i
    return claims


# ── prophecy recorder (forecasts -> bitemporal table) ──────────────────────

def _record_forecasts(outlook: Dict[str, Any]) -> Dict[str, Any]:
    """Persist each world's numeric claim into the forecasts table.

    One row per world claim: (symbol, direction=sign of consensus_bias,
    price_at_birth, consensus_bias, confidence, ts) with
    target_ts_ms = as_of + AUREON_PROPHECY_HORIZON_MIN (default 30 min).
    INSERT OR IGNORE + a forecast_id that is deterministic per
    (world, as-of minute) makes re-runs idempotent. Fail-closed: any DB or
    input problem yields inserted=0 + an explicit error — nothing fabricated.
    """
    import hashlib

    horizon_ms = int(_PROPHECY_HORIZON_MIN * 60_000)
    as_of_ms = int(outlook.get("ts", time.time()) * 1000)
    target_ms = as_of_ms + horizon_ms
    prices = (outlook.get("inputs") or {}).get("prices") or {}
    worlds = outlook.get("worlds") or []

    claims: List[Dict[str, Any]] = []
    for w in worlds:
        bias, conf, sym = w.get("consensus_bias"), w.get("confidence"), w.get("symbol")
        if not (isinstance(bias, (int, float)) and isinstance(conf, (int, float)) and sym):
            continue  # no numeric claim — nothing to record (fail-closed)
        if float(bias) == 0.0:
            continue  # zero bias carries no direction — not a claim
        price = prices.get(sym)
        if not isinstance(price, (int, float)) or not price:
            continue  # no real birth price — not recordable (fail-closed)
        claims.append({
            "name": w.get("name"), "strategy": w.get("strategy"), "symbol": sym,
            "direction": "up" if float(bias) > 0 else "down",
            "price_at_birth": round(float(price), 8),
            "consensus_bias": round(float(bias), 4),
            "confidence": round(float(conf), 4),
            "ts": outlook.get("ts"),
            "horizon_min": _PROPHECY_HORIZON_MIN,
        })

    if not claims:
        return {"recorded": 0, "claims": 0,
                "error": "no numeric world claims with live prices to record"}

    try:
        upstream = str(_WORKSPACE / "aureon-os-upstream")
        if upstream not in sys.path:
            sys.path.insert(0, upstream)
        os.environ.setdefault("AUREON_GLOBAL_HISTORY_DB", str(_HISTORY_DB_PATH))
        from aureon.core import aureon_global_history_db as ghdb

        conn = ghdb.connect(str(_HISTORY_DB_PATH))
        try:
            inserted = 0
            for c in claims:
                as_of_minute = as_of_ms // 60_000
                digest = hashlib.sha1(
                    f"{_FORECAST_MODEL}|{c['name']}|{as_of_minute}".encode("utf-8")
                ).hexdigest()[:16]
                raw = dict(c)
                raw["truth_status"] = "perception_claim"
                raw["note"] = ("future-claim; resolved honestly by the prophecy "
                               "resolver against price_cache_journal.jsonl — "
                               "outcome never assumed")
                if ghdb.insert_forecast(conn, {
                    "model": _FORECAST_MODEL,
                    "forecast_id": f"mv_{digest}",
                    "symbol": c["symbol"],
                    "venue": "binance",
                    "as_of_ts_ms": as_of_ms,
                    "target_ts_ms": target_ms,
                    "raw_json": json.dumps(raw, ensure_ascii=False),
                }):
                    inserted += 1
            conn.commit()
        finally:
            conn.close()
        return {"recorded": inserted, "claims": len(claims),
                "horizon_min": _PROPHECY_HORIZON_MIN, "db": str(_HISTORY_DB_PATH)}
    except Exception as exc:
        return {"recorded": 0, "claims": len(claims),
                "error": f"forecast recording failed: {type(exc).__name__}: {exc}"}


# ── main ────────────────────────────────────────────────────────────────────

def build_outlook() -> Dict[str, Any]:
    errors: List[str] = []
    now = time.time()

    from exchange_adapters.price_cache import get_shared_cache
    cache = get_shared_cache()

    # Real momentum + change from two live snapshots (intra-run pair).
    momentum, changes, snap2, window_s = _measure_momentum(errors)

    # Primary (binance) + cross-check (kraken) through the shared cache.
    fetched = _fetch_prices(cache)

    prices: Dict[str, Optional[float]] = {}
    as_of: Dict[str, Optional[str]] = {}
    for sym, rec in fetched.items():
        price = rec["price"] or rec["kraken_price"] or snap2.get(sym)  # real fallbacks only
        if not price:
            # Only surface source errors when every real source failed.
            errors.extend(rec["errors"])
        prices[sym] = price
        as_of[sym] = rec["as_of"]
        kp = rec["kraken_price"]
        bp = rec["price"]
        if bp and kp and bp > 0 and abs(bp - kp) / bp > 0.01:
            errors.append(f"crosscheck {sym}: binance {bp} vs kraken {kp} differ >1%")

    live_symbols = {s: p for s, p in prices.items() if p}
    market_data = {
        "prices": live_symbols,
        "changes": {s: changes[s] for s in live_symbols},
        "volumes": {s: 0.0 for s in live_symbols},   # not fetched; 0 = no volume claim
        "momentum": {s: momentum[s] for s in live_symbols},
    }

    vacuum = _vacuum_phase(prices, changes, errors)

    if live_symbols:
        try:
            multiverse, cycle, omega = _run_multiverse(market_data)
            worlds = _world_outlooks(multiverse, prices)
            consensus = cycle.get("consensus", {})
            for sym, decision in consensus.items():
                logger.info("consensus %s: %s (agreement %.2f)",
                            sym, decision.get("action"), decision.get("agreement", 0))
        except Exception as exc:
            errors.append(f"multiverse: {type(exc).__name__}: {exc}")
            omega = {"reaction_ms": None, "sweep_bias": None}
            worlds = []
    else:
        errors.append("multiverse: no live prices available; worlds not run (fail-closed)")
        omega = {"reaction_ms": None, "sweep_bias": None}
        worlds = []

    outlook = {
        "ts": now,
        "ts_iso": datetime.fromtimestamp(now, timezone.utc).isoformat(),
        "worlds": worlds,
        "omega": omega,
        "vacuum_phase": vacuum,
        **_derive_field_regime(worlds),
        "best_outcomes": _derive_best_outcomes(worlds, prices, momentum, window_s),
        "errors": errors,
        "inputs": {
            "prices": prices,
            "changes_pct": changes,
            "momentum": momentum,
            "momentum_window_s": window_s,
            "as_of": as_of,
            "symbols_skipped": [s for s, p in prices.items() if not p],
        },
    }
    return outlook


def _write_state(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".multiverse_outlook.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def main() -> int:
    from aureon.utils.console_utf8 import ensure_utf8_stdout
    ensure_utf8_stdout()

    parser = argparse.ArgumentParser(description="Multiverse Outlook (perception-only)")
    parser.add_argument("--print", dest="do_print", action="store_true",
                        help="print the outlook JSON to stdout")
    args = parser.parse_args()

    outlook = build_outlook()
    prophecy = _record_forecasts(outlook)
    outlook["prophecy"] = prophecy
    _write_state(_STATE_PATH, outlook)

    if args.do_print:
        print(json.dumps(outlook, indent=2, ensure_ascii=False))
    else:
        n_worlds = len(outlook["worlds"])
        live = [s for s, p in outlook["inputs"]["prices"].items() if p]
        print(f"multiverse_outlook: {n_worlds} worlds | live: {','.join(live) or 'none'} | "
              f"errors: {len(outlook['errors'])} | wrote {_STATE_PATH}")
        print(f"prophecy: {prophecy.get('recorded', 0)}/{prophecy.get('claims', 0)} "
              f"claims recorded -> forecasts table "
              f"({prophecy.get('horizon_min', _PROPHECY_HORIZON_MIN)}min horizon)"
              + (f" | ERROR: {prophecy['error']}" if prophecy.get("error") else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
