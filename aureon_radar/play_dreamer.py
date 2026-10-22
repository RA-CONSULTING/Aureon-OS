#!/usr/bin/env python3
"""Play Dreamer — Queen Sero's play-dreaming simulation layer (owner decree 2026-09-06).

She DREAMS of plays that get her energy FASTER. Every play emitted here is:

    truth_status: "simulated"     action_eligible: false

PERCEPTION ONLY. Nothing here trades; capital stays gated. No fabricated data
is presented as live: every simulated number is labeled, estimates are labeled
estimates, and a dream with no real klines is not dreamt (fail-closed).

Mechanism:
  1. Candidate plays are generated from REAL inputs: symbols from
     state/global_energy_flow.json movers (top by flow_score, tie-broken by
     |change_pct|) crossed with archetypes:
       {momentum_burst, phase_crest_continuation, mean_revert_snap,
        cross_venue_spread, funding_flip}
  2. direction/entry/target/stop come from state/harmonic_phase.json phase
     hints (BTC/ETH) or kline-derived phase (everything else, labeled) plus
     REAL recent Binance public klines (15m).
  3. Each play is simulated:
       a. on the REAL recent price path (replays of the fetched kline window:
          every bar boundary is a hypothetical entry, walked forward with
          conservative stop-first bar resolution), and
       b. through the Internal Multiverse (10-9-1-10,
          aureon.simulation.aureon_internal_multiverse — same pattern as
          multiverse_outlook.py): all 10 worlds vote on the symbol
          (worlds_consensus) and each world runs the identical play on its own
          deterministic seeded path with volatility estimated from the REAL
          klines. p_reach = fraction of the 10 worlds hitting target before
          stop. SIMULATED, labeled.
  4. net_ev_usd uses state/juice_gate.json candidate costs when present,
     else a labeled venue-cost fallback constant. The 1% capture floor
     (state/capture_floor.json) applies to NET expectancy and is never
     weakened: plays that cannot clear floor+cost on a net basis are dropped.

Plays are ranked by expected_capture_min asc, then net_ev_usd desc, and each
is marked faster_than_current_median against state/time_to_capture.json
open-position implied_remaining_min values (null when no baseline exists —
null-not-0).

Writes aureon_radar/state/dreamt_plays.json (current cycle) AND appends every
dreamt play's falsifiable claim to aureon_radar/state/dreamt_play_history.jsonl
(bounded to the newest 500 lines) so dreamt plays stop being discarded.

    {
      "ts": float, "ts_iso": str,
      "truth_status": "simulated_layer",
      "capture_floor_pct": float|null,
      "cost_model": {"source": str, "round_trip_pct": float|null},
      "current_median_capture_min": float|null,
      "plays": [{
        "name", "archetype", "symbol", "direction",
        "entry", "target_pct", "stop_pct", "venue_hint",
        "truth_status": "simulated", "action_eligible": false,
        "simulated": {
            "worlds_consensus": {...}, "p_reach": float|null,
            "expected_capture_min": float|null, "net_ev_usd": float|null,
            "real_path": {...}, "meets_capture_floor_net": bool|null
        },
        "size_hint_usd": float|null, "faster_than_current": bool|null,
        "rank": int
      }],
      "inputs": {...}, "errors": [str]
    }

Usage:
  cd aureon_radar && set -a && . ./.env && set +a && \
    PYTHONUTF8=1 PYTHONPATH=<workspace>/aureon-os-upstream python play_dreamer.py [--print]
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import random
import statistics
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("play_dreamer")

_RADAR_ROOT = Path(__file__).resolve().parent
_STATE_DIR = _RADAR_ROOT / "state"
_STATE_PATH = _STATE_DIR / "dreamt_plays.json"
_PLAY_HISTORY_PATH = _STATE_DIR / "dreamt_play_history.jsonl"
_PLAY_HISTORY_MAX = 500     # bounded journal: keep the newest 500 dreamt claims

_BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
_REQUEST_TIMEOUT = 20.0
_BAR_MINUTES = 15
_KLINE_INTERVAL = "15m"
_KLINE_LIMIT = 96            # 24h of real 15m bars
_TOP_MOVERS = 5              # symbols dreamed about per pass
_REPLAY_STARTS = 24          # bar boundaries replayed on the real path
_MC_HORIZON_BARS = 64        # per-world simulated horizon
_MC_PATHS_PER_WORLD = 8      # seeded paths per world (variance reduction)

# Venue cost fallback when state/juice_gate.json is absent (sibling organ may
# create it later). Round-trip taker fee + slippage ESTIMATE — always labeled.
_VENUE_COST_FALLBACK_PCT = 0.20
_SIZE_FRACTION_OF_FREE_USD = 0.25
_SIZE_FALLBACK_USD = 100.0

_ARCHETYPES = (
    "momentum_burst",
    "phase_crest_continuation",
    "mean_revert_snap",
    "cross_venue_spread",
    "funding_flip",
)

_HARMONIC_SYMBOL_MAP = {"BTC": "BTCUSD", "BTCUSDT": "BTCUSD", "XBT": "BTCUSD",
                        "ETH": "ETHUSD", "ETHUSDT": "ETHUSD"}


# ── helpers ─────────────────────────────────────────────────────────────────

def _utc_iso(ts: Optional[float] = None) -> str:
    return datetime.fromtimestamp(ts if ts is not None else time.time(),
                                  timezone.utc).isoformat()


def _load_json(path: Path) -> Optional[Any]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def _fetch_klines(symbol: str, limit: int = _KLINE_LIMIT) -> Tuple[Optional[List[Dict[str, float]]], Optional[str]]:
    """Real public Binance 15m klines. Movers report bare base symbols (RAY),
    so the full pair (RAYUSDT) is tried first/second. None on any failure
    (fail-closed). Returns (candles|None, resolved_pair|None)."""
    for pair in (f"{symbol}USDT", symbol):
        try:
            resp = requests.get(
                _BINANCE_KLINES_URL,
                params={"symbol": pair, "interval": _KLINE_INTERVAL, "limit": limit},
                timeout=_REQUEST_TIMEOUT,
                headers={"User-Agent": "aureon-play-dreamer/1.0"},
            )
            if resp.status_code != 200:
                continue
            rows = resp.json()
            if not isinstance(rows, list) or len(rows) < 30:
                continue
            return ([{"open": float(c[1]), "high": float(c[2]), "low": float(c[3]),
                      "close": float(c[4]), "volume": float(c[5])} for c in rows], pair)
        except Exception:
            continue
    return None, None


def _klines_features(kl: List[Dict[str, float]]) -> Dict[str, Any]:
    closes = [k["close"] for k in kl]
    ranges = [(k["high"] - k["low"]) / k["open"] * 100.0 for k in kl if k["open"] > 0]
    rets = [(closes[i] - closes[i - 1]) / closes[i - 1] * 100.0
            for i in range(1, len(closes)) if closes[i - 1] > 0]
    last = closes[-1]
    change24 = (last - kl[0]["open"]) / kl[0]["open"] * 100.0 if kl[0]["open"] > 0 else 0.0
    mom4 = (last - closes[-5]) / closes[-5] * 100.0 if len(closes) >= 5 and closes[-5] > 0 else 0.0
    mean_close = statistics.fmean(closes)
    vol = statistics.pstdev(rets) if len(rets) >= 2 else 0.0
    avg_range = statistics.fmean(ranges) if ranges else 0.0
    # Kline-derived phase (labeled): position vs 24h mean + short momentum.
    if last >= mean_close and mom4 > 0:
        phase = "rising"
    elif last >= mean_close and mom4 <= 0:
        phase = "crest"
    elif last < mean_close and mom4 < 0:
        phase = "falling"
    else:
        phase = "trough"
    return {"last": last, "change24_pct": change24, "mom4_pct": mom4,
            "mean_close": mean_close, "vol_pct_per_bar": vol,
            "avg_range_pct": avg_range, "klines_derived_phase": phase}


def _kraken_cross_price(symbol: str) -> Tuple[Optional[float], Optional[str]]:
    """Kraken public price for cross-venue spread plays (fail-closed)."""
    ksym = None
    if symbol.startswith("BTC"):
        ksym = "XBTUSD"
    elif symbol.startswith("ETH"):
        ksym = "ETHUSD"
    else:
        ksym = f"{symbol}USD"
    try:
        from exchange_adapters.price_cache import get_shared_cache
        r = get_shared_cache().get_price(ksym, source="kraken")
        if r.get("price") is not None and not r.get("error"):
            return float(r["price"]), ksym
        return None, ksym
    except Exception:
        return None, ksym


# ── candidate play generation (real inputs only) ────────────────────────────

def _gen_candidates(movers: List[Dict[str, Any]], features: Dict[str, Dict[str, Any]],
                    harmonic: Dict[str, Any], ttc: Dict[str, Any],
                    cost_pct: float, floor_pct: Optional[float],
                    errors: List[str]) -> List[Dict[str, Any]]:
    """Cross top movers with archetypes; params from phase + real klines."""
    cands: List[Dict[str, Any]] = []
    funding_due = False
    try:
        nxt = (ttc.get("session") or {}).get("next_funding_utc")
        if nxt:
            due = datetime.fromisoformat(nxt.replace("Z", "+00:00")).timestamp()
            funding_due = 0 <= due - time.time() <= 24 * 3600
    except Exception:
        funding_due = False

    harmonic_syms = harmonic.get("symbols") or {}

    for mv in movers:
        sym = mv.get("symbol")
        if not sym:
            continue
        f = features.get(sym)
        if not f:
            continue  # no real klines -> this symbol is not dreamt (fail-closed)
        entry = f["last"]
        avg_range = max(f["avg_range_pct"], 0.05)
        # Stop: ~2 bars of real range, never below the capture floor.
        stop_pct = round(max(1.0, 2.0 * avg_range), 2)
        min_net_target = (floor_pct or 0.0) + cost_pct

        hkey = _HARMONIC_SYMBOL_MAP.get(sym)
        hphase = (harmonic_syms.get(hkey) or {}).get("phase_hint") if hkey else None
        phase = hphase or f["klines_derived_phase"]
        phase_source = "harmonic_phase.json" if hphase else "klines_derived"

        def _add(archetype: str, direction: str, ent: float, target_pct: float,
                 extra: Optional[Dict[str, Any]] = None) -> None:
            if target_pct < min_net_target:
                errors.append(f"{archetype}:{sym}: target {target_pct:.2f}% below "
                              f"floor+cost {min_net_target:.2f}% — play not dreamt "
                              f"(capture floor never weakened)")
                return
            cands.append({
                "name": f"{archetype}:{sym}", "archetype": archetype, "symbol": sym,
                "direction": direction, "entry": round(ent, 8),
                "target_pct": round(target_pct, 2), "stop_pct": stop_pct,
                "venue_hint": mv.get("venue_hint") or "binance",
                "phase_used": phase, "phase_source": phase_source,
                "_f": f, "_extra": extra or {},
            })

        # momentum_burst: real 4-bar momentum carries.
        if abs(f["mom4_pct"]) >= 0.75:
            d = "long" if f["mom4_pct"] > 0 else "short"
            _add("momentum_burst", d, entry, max(min_net_target, round(2.0 * stop_pct, 2)))

        # phase_crest_continuation: ride the harmonic phase direction.
        if phase in ("rising", "crest"):
            _add("phase_crest_continuation", "long", entry,
                 max(min_net_target, round(1.5 * stop_pct, 2)))
        elif phase in ("falling", "trough"):
            _add("phase_crest_continuation", "short", entry,
                 max(min_net_target, round(1.5 * stop_pct, 2)))

        # mean_revert_snap: extended 24h move fades back toward the mean.
        if abs(f["change24_pct"]) >= 8.0:
            d = "short" if f["change24_pct"] > 0 else "long"
            dist = abs(entry - f["mean_close"]) / entry * 100.0
            tgt = min(max(dist, min_net_target), 3.0 * stop_pct)
            _add("mean_revert_snap", d, entry, round(tgt, 2))

        # cross_venue_spread: real binance-vs-kraken price gap converges.
        kprice, ksym = _kraken_cross_price(sym)
        if kprice and kprice > 0 and entry > 0:
            spread_pct = abs(entry - kprice) / entry * 100.0
            if spread_pct >= 0.15:
                if entry < kprice:
                    d, ent = "long", entry       # binance is the cheap venue
                else:
                    d, ent = "short", entry      # binance is the rich venue
                _add("cross_venue_spread", d, ent, round(spread_pct, 2),
                     {"kraken_symbol": ksym, "kraken_price": kprice,
                      "spread_pct": round(spread_pct, 3)})
        else:
            errors.append(f"cross_venue_spread:{sym}: no real kraken price "
                          f"for {ksym or sym} — archetype skipped (fail-closed)")

        # funding_flip: extreme move faded into a real upcoming funding print.
        if funding_due and abs(f["change24_pct"]) >= 5.0:
            d = "short" if f["change24_pct"] > 0 else "long"
            _add("funding_flip", d, entry,
                 max(min_net_target, round(1.5 * stop_pct, 2)),
                 {"next_funding_utc": (ttc.get("session") or {}).get("next_funding_utc")})
    return cands


# ── simulation A: real recent price path replay ─────────────────────────────

def _replay_real_path(cand: Dict[str, Any], kl: List[Dict[str, float]]) -> Dict[str, Any]:
    """Replay the play at every recent bar boundary on the REAL kline path.

    Conservative bar resolution: if a bar's range covers both target and stop,
    the stop is assumed hit first. Returns honest counts + median minutes to
    target among winners (None when nobody reached — null-not-0).
    """
    d = cand["direction"]
    t_mult = 1.0 if d == "long" else -1.0
    starts = list(range(max(1, len(kl) - _REPLAY_STARTS), len(kl) - 1))
    hits = 0
    minutes_to_target: List[float] = []
    for i in starts:
        entry = kl[i]["close"]
        if entry <= 0:
            continue
        target = entry * (1 + t_mult * cand["target_pct"] / 100.0)
        stop = entry * (1 - t_mult * cand["stop_pct"] / 100.0)
        for j in range(i + 1, len(kl)):
            bar = kl[j]
            hit_t = (bar["high"] >= target) if d == "long" else (bar["low"] <= target)
            hit_s = (bar["low"] <= stop) if d == "long" else (bar["high"] >= stop)
            if hit_s:
                break  # stop first (conservative)
            if hit_t:
                hits += 1
                minutes_to_target.append((j - i) * _BAR_MINUTES)
                break
    n = len(starts)
    return {
        "replays": n, "hits": hits,
        "p_reach": round(hits / n, 4) if n else None,
        "median_min_to_target": round(statistics.median(minutes_to_target), 1)
        if minutes_to_target else None,
        "basis": "real_recent_price_path_replay",
    }


# ── simulation B: Internal Multiverse (10-9-1-10) ───────────────────────────

def _simulate_worlds(cand: Dict[str, Any], f: Dict[str, Any]
                     ) -> Tuple[Optional[Dict[str, Any]], Optional[float],
                                Optional[float], List[str]]:
    """Run the play through the Internal Multiverse.

    worlds_consensus: the ConsensusEngine's 10-world vote on the symbol.
    Each of the 10 worlds then runs the IDENTICAL play on its own
    deterministic seeded random paths, per-bar volatility estimated from the
    REAL klines (GBM, no drift — honest null hypothesis). p_reach = fraction
    of worlds with at least one path hitting target before stop; the world's
    bars-to-target are its fastest winning path. SIMULATED — labeled as such.
    """
    errors: List[str] = []
    sym = cand["symbol"]
    try:
        from aureon.simulation.aureon_internal_multiverse import InternalMultiverse
    except Exception as exc:
        return None, None, None, [f"multiverse import: {type(exc).__name__}: {exc}"]

    vol = max(f["vol_pct_per_bar"], 0.02) / 100.0   # fractional per bar
    market_data = {
        "prices": {sym: f["last"]},
        "changes": {sym: f["change24_pct"]},
        "volumes": {sym: 0.0},      # not claimed — no volume data on this path
        "momentum": {sym: f["mom4_pct"] / 100.0},
    }
    try:
        multiverse = InternalMultiverse(initial_equity=100.0)
        multiverse.update_market_data(market_data)
        cycle = multiverse.run_cycle()
        dec = (cycle.get("consensus") or {}).get(sym) or {}
        worlds_consensus = {
            "action": dec.get("action"),
            "agreement": dec.get("agreement"),
            "buy_votes": dec.get("buy_votes"),
            "sell_votes": dec.get("sell_votes"),
            "hold_votes": dec.get("hold_votes"),
            "basis": "internal_multiverse_10_worlds",
        }
    except Exception as exc:
        return None, None, None, [f"multiverse cycle: {type(exc).__name__}: {exc}"]

    # Per-world seeded Monte Carlo over the identical play (SIMULATED).
    # price=1.0 is a normalized synthetic starting point for the Monte-Carlo
    # exploration; it is NOT a market quote and never touches live trading.
    d = cand["direction"]
    t_mult = 1.0 if d == "long" else -1.0
    tgt_frac = cand["target_pct"] / 100.0
    stp_frac = cand["stop_pct"] / 100.0
    world_hits = 0
    world_best_bars: List[int] = []
    for w in multiverse.worlds:
        rng = random.Random((hash((cand["name"], w.id)) & 0xFFFFFFFF))
        hit = False
        best: Optional[int] = None
        for _ in range(_MC_PATHS_PER_WORLD):
            price = 1.0  # SIMULATED normalized starting price (Monte-Carlo only)
            for bar_i in range(1, _MC_HORIZON_BARS + 1):
                price *= math.exp(rng.gauss(0.0, vol))
                move = (price - 1.0) * t_mult
                if move <= -stp_frac:
                    break
                if move >= tgt_frac:
                    if not hit or bar_i < (best or bar_i):
                        best = bar_i
                    hit = True
                    break
        if hit:
            world_hits += 1
            world_best_bars.append(best or _MC_HORIZON_BARS)

    p_reach = world_hits / len(multiverse.worlds) if multiverse.worlds else None
    expected_capture_min = (round(statistics.median(world_best_bars) * _BAR_MINUTES, 1)
                            if world_best_bars else None)
    return worlds_consensus, p_reach, expected_capture_min, errors


# ── assembly ────────────────────────────────────────────────────────────────

def build_dreams() -> Dict[str, Any]:
    errors: List[str] = []
    now = time.time()

    gef = _load_json(_STATE_DIR / "global_energy_flow.json") or {}
    harmonic = _load_json(_STATE_DIR / "harmonic_phase.json") or {}
    ttc = _load_json(_STATE_DIR / "time_to_capture.json") or {}
    floor_doc = _load_json(_STATE_DIR / "capture_floor.json") or {}
    juice = _load_json(_STATE_DIR / "juice_gate.json") or {}
    prog = _load_json(_STATE_DIR / "trading_progress_state.json") or {}

    floor_pct = floor_doc.get("min_gain_pct")
    floor_pct = float(floor_pct) if isinstance(floor_pct, (int, float)) else None

    # Net-of-cost model: sibling juice_gate candidate costs if present,
    # else labeled venue fallback constant.
    cost_pct: Optional[float] = None
    cost_source = "venue_cost_fallback"
    for key in ("candidate_cost_pct", "round_trip_cost_pct", "cost_pct"):
        v = juice.get(key)
        if isinstance(v, (int, float)):
            cost_pct = float(v)
            cost_source = f"juice_gate.json:{key}"
            break
    if cost_pct is None:
        cost_pct = _VENUE_COST_FALLBACK_PCT

    # Current baseline: median implied remaining minutes of open positions.
    baseline: Optional[float] = None
    implied = [p.get("implied_remaining_min") for p in (ttc.get("open_positions") or [])
               if isinstance(p.get("implied_remaining_min"), (int, float))]
    if implied:
        baseline = round(statistics.median(implied), 1)

    # Size hint: a fraction of REAL free capital if known, else labeled fallback.
    free_usd = ((prog.get("capital") or {}).get("free_usd"))
    if isinstance(free_usd, (int, float)) and free_usd > 0:
        size_hint = round(float(free_usd) * _SIZE_FRACTION_OF_FREE_USD, 2)
        size_source = "trading_progress_state.json:capital.free_usd*0.25"
    else:
        size_hint = _SIZE_FALLBACK_USD
        size_source = "fallback_notional_usd (no real free capital on disk)"

    movers = sorted((gef.get("movers") or []),
                    key=lambda m: (m.get("flow_score") or 0.0,
                                   abs(m.get("change_pct") or 0.0)),
                    reverse=True)[:_TOP_MOVERS]

    # Real klines per mover — fail-closed per symbol.
    klines_map: Dict[str, List[Dict[str, float]]] = {}
    resolved_pairs: Dict[str, str] = {}
    features: Dict[str, Dict[str, Any]] = {}
    for mv in movers:
        sym = mv.get("symbol")
        if not sym:
            continue
        kl, pair = _fetch_klines(sym)
        if not kl:
            errors.append(f"{sym}: no real klines (fetch failed or too few) — "
                          f"symbol not dreamt (fail-closed)")
            continue
        klines_map[sym] = kl
        resolved_pairs[sym] = pair or sym
        features[sym] = _klines_features(kl)

    cands = _gen_candidates(movers, features, harmonic, ttc, cost_pct,
                            floor_pct, errors)

    plays: List[Dict[str, Any]] = []
    for cand in cands:
        f = cand["_f"]
        kl = klines_map[cand["symbol"]]
        real_path = _replay_real_path(cand, kl)
        worlds_consensus, p_reach, exp_min, werr = _simulate_worlds(cand, f)
        errors.extend(werr)

        # net_ev_usd (SIMULATED, labeled): expectancy net of venue costs on the
        # size hint. The 1% floor applies to this net figure — never weakened.
        net_ev = None
        meets_floor = None
        if p_reach is not None and size_hint:
            ev_pct = p_reach * cand["target_pct"] - (1 - p_reach) * cand["stop_pct"]
            net_pct = ev_pct - cost_pct
            net_ev = round(size_hint * net_pct / 100.0, 4)
            meets_floor = (floor_pct is not None) and (net_pct >= floor_pct)

        plays.append({
            "name": cand["name"],
            "archetype": cand["archetype"],
            "symbol": cand["symbol"],
            "direction": cand["direction"],
            "entry": cand["entry"],
            "target_pct": cand["target_pct"],
            "stop_pct": cand["stop_pct"],
            "venue_hint": cand["venue_hint"],
            "truth_status": "simulated",
            "action_eligible": False,
            "simulated": {
                "worlds_consensus": worlds_consensus,
                "p_reach": p_reach,
                "expected_capture_min": exp_min,
                "net_ev_usd": net_ev,
                "real_path": real_path,
                "meets_capture_floor_net": meets_floor,
                "cost_model_pct": cost_pct,
                "basis": "SIMULATED — internal multiverse seeded paths + real "
                         "recent price path replay; volatility from real klines",
            },
            "size_hint_usd": size_hint,
            "size_hint_source": size_source,
            "faster_than_current": (exp_min < baseline
                                    if (exp_min is not None and baseline is not None)
                                    else None),
            "rank": None,
            "detail": {
                "phase_used": cand["phase_used"],
                "phase_source": cand["phase_source"],
                "change24_pct": round(f["change24_pct"], 3),
                "mom4_pct": round(f["mom4_pct"], 3),
                **cand["_extra"],
            },
        })

    # Rank: expected_capture_min asc (None last), then net_ev_usd desc.
    plays.sort(key=lambda p: (
        p["simulated"]["expected_capture_min"] is None,
        p["simulated"]["expected_capture_min"] or 1e18,
        -(p["simulated"]["net_ev_usd"] or -1e18),
    ))
    for i, p in enumerate(plays, 1):
        p["rank"] = i

    return {
        "ts": now,
        "ts_iso": _utc_iso(now),
        "truth_status": "simulated_layer",
        "action_eligible": False,
        "capture_floor_pct": floor_pct,
        "cost_model": {"source": cost_source,
                       "round_trip_pct": cost_pct,
                       "label": "estimate" if cost_source == "venue_cost_fallback" else "sibling_state"},
        "current_median_capture_min": baseline,
        "plays": plays,
        "inputs": {
            "movers_considered": [m.get("symbol") for m in movers],
            "symbols_dreamt": sorted(klines_map),
            "archetypes": list(_ARCHETYPES),
            "size_hint_source": size_source,
            "klines": {"source": "binance_public", "interval": _KLINE_INTERVAL,
                       "bars": _KLINE_LIMIT, "resolved_pairs": resolved_pairs},
        },
        "errors": errors,
    }


def _write_state(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".dreamt_plays.", suffix=".tmp")
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


def _append_play_history(plays: List[Dict[str, Any]], ts: float) -> int:
    """Append each dreamt play's falsifiable claim to the bounded JSONL journal.

    One line per play: (name, symbol, direction, entry, target_pct, stop_pct,
    p_reach, expected_capture_min, ts) — today these claims were discarded
    every cycle. The journal is bounded to the newest _PLAY_HISTORY_MAX
    lines (older lines dropped). Fail-closed: a write failure logs a warning
    and changes nothing — dreams are never fabricated after the fact.
    """
    claims = []
    for p in plays:
        sim = p.get("simulated") or {}
        claims.append({
            "ts": ts,
            "name": p.get("name"),
            "symbol": p.get("symbol"),
            "direction": p.get("direction"),
            "entry": p.get("entry"),
            "target_pct": p.get("target_pct"),
            "stop_pct": p.get("stop_pct"),
            "p_reach": sim.get("p_reach"),
            "expected_capture_min": sim.get("expected_capture_min"),
            "truth_status": "simulated",
            "action_eligible": False,
        })
    if not claims:
        return 0
    try:
        existing: List[str] = []
        if _PLAY_HISTORY_PATH.exists():
            with open(_PLAY_HISTORY_PATH, "r", encoding="utf-8") as fh:
                existing = fh.read().splitlines()
        keep = max(0, _PLAY_HISTORY_MAX - len(claims))
        lines = existing[-keep:] if keep else []
        lines.extend(json.dumps(c, ensure_ascii=False) for c in claims)
        fd, tmp = tempfile.mkstemp(dir=str(_PLAY_HISTORY_PATH.parent),
                                   prefix=".dreamt_play_history.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
            os.replace(tmp, _PLAY_HISTORY_PATH)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
        return len(claims)
    except OSError as exc:
        logger.warning("dreamt play history write failed: %s", exc)
        return 0


def main() -> int:
    from aureon.utils.console_utf8 import ensure_utf8_stdout
    ensure_utf8_stdout()

    parser = argparse.ArgumentParser(description="Play Dreamer (simulation-only)")
    parser.add_argument("--print", dest="do_print", action="store_true",
                        help="print the full dream JSON to stdout")
    args = parser.parse_args()

    dreams = build_dreams()
    _write_state(_STATE_PATH, dreams)
    n_history = _append_play_history(dreams.get("plays") or [], dreams.get("ts") or time.time())

    if args.do_print:
        print(json.dumps(dreams, indent=2, ensure_ascii=False))
    else:
        print(f"play_dreamer: {len(dreams['plays'])} dreamt plays "
              f"({len(dreams['inputs']['symbols_dreamt'])} symbols with real klines) "
              f"| floor {dreams['capture_floor_pct']}% | "
              f"cost {dreams['cost_model']['round_trip_pct']}% ({dreams['cost_model']['source']}) "
              f"| history +{n_history} -> {_PLAY_HISTORY_PATH} "
              f"| errors: {len(dreams['errors'])} | wrote {_STATE_PATH}")
        for p in dreams["plays"][:3]:
            s = p["simulated"]
            print(f"  #{p['rank']} {p['name']} {p['direction']} "
                  f"entry={p['entry']} tgt={p['target_pct']}% stop={p['stop_pct']}% "
                  f"| p_reach={s['p_reach']} capture={s['expected_capture_min']}min "
                  f"net_ev=${s['net_ev_usd']} floor_net={s['meets_capture_floor_net']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
