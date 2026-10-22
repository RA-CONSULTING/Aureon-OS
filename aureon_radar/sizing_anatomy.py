#!/usr/bin/env python3
"""SIZING ANATOMY — fully dynamic position sizing + risk anatomy for Queen Sero.

Owner decree 2026-09-06 (Gary Leckey): FULLY DYNAMIC sizing and risk — no
fixed fractions. This module audits each live candidate (energy-flow movers +
open positions) and answers, per symbol:

    size_usd   = f(equity, free capital per venue, real ATR volatility,
                   harmonic phase alignment, time-to-capture, conviction)
    risk_usd   = equity * risk_pct_of_equity            (conviction-driven)
    stop_pct   = 2 * vol_atr_pct                        (ATR-based, dynamic)
    size_usd   = risk_usd / (stop_pct / 100)            (risk-based, vol-normalized)
    margin_usd = size_usd * margin_factor_pct / 100     (venue/asset-class aware)

Hard constraints (stolen + fixed from the audited sizers):
  * free capital per venue is the hard source of truth — size NEVER exceeds
    deployable free cash at the candidate's venue (dynamic_margin_sizer.py).
  * aggregate new margin must keep projected margin level >= the safety floor
    (equity * 100 / entry_min_margin_pct, 250% — dynamic_margin_sizer.py).
  * below venue/pair minimum notional -> size_usd = null (fail-closed,
    null-not-0). No fabricated volatility: ATR unavailable -> size null.
  * 1% capture floor (state/capture_floor.json) is annotated, never weakened.

Inputs (all read-only, absence tolerated):
  state/global_energy_flow.json      movers (symbol, direction, confidence)
  state/trading_progress_state.json  open positions + free capital per venue
  real_portfolio_state.json          equity = last history total_usd
  state/harmonic_phase.json          per-symbol phase/coherence + field state
  state/time_to_capture.json         journaled minutes-to-1/2/3% capture
  state/capture_floor.json           owner capture floor (annotation only)
  state/price_cache_journal.jsonl    journaled marks (volatility fallback)
  exchange_adapters/price_cache.py   shared cache (prices + rate-limited klines)

Perception/decision layer ONLY: emits advisory numbers, never orders.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

RADAR_DIR = Path(__file__).resolve().parent
STATE_DIR = RADAR_DIR / "state"
OUT_PATH = STATE_DIR / "sizing_anatomy.json"

# ── dynamic configuration (env-overridable; defaults stolen from audited sizers) ──

def _env_float(name: str, default: float) -> float:
    try:
        raw = os.environ.get(name)
        return float(raw) if raw not in (None, "") else default
    except (TypeError, ValueError):
        return default


# Stolen from unified_margin_trader/dynamic_margin_sizer.py DynamicMarginConfig
DEPLOY_FRACTION = _env_float("SIZING_DEPLOY_FRACTION", 0.70)          # max free-margin fraction deployable
TINY_EQUITY_USD = _env_float("SIZING_TINY_EQUITY_USD", 50.0)          # tiny-account threshold
TINY_DEPLOY_FRACTION = _env_float("SIZING_TINY_DEPLOY_FRACTION", 0.90)
ENTRY_MIN_MARGIN_PCT = _env_float("SIZING_ENTRY_MIN_MARGIN_PCT", 250.0)  # projected margin-level floor
FALLBACK_MIN_NOTIONAL_USD = _env_float("SIZING_FALLBACK_MIN_NOTIONAL_USD", 5.0)
STRESS_SL_PCT = _env_float("SIZING_STRESS_SL_PCT", 2.0)               # SL move used for stress_impact_pct

# Sizing dynamics (no fixed position fractions anywhere below)
ATR_STOP_MULTIPLE = _env_float("SIZING_ATR_STOP_MULTIPLE", 2.0)       # stop distance = mult * ATR%
BASE_RISK_COEFF = _env_float("SIZING_BASE_RISK_COEFF", 0.02)          # risk% scale; final risk% = coeff * conviction^1.5 * harmonic * ttc
HARD_RISK_CAP_PCT = _env_float("SIZING_HARD_RISK_CAP_PCT", 10.0)      # absolute ceiling on risk_pct_of_equity
STRESS_CAP_PCT = _env_float("SIZING_STRESS_CAP_PCT", 3.0)             # max equity % lost at stress SL move
TINY_STRESS_CAP_PCT = _env_float("SIZING_TINY_STRESS_CAP_PCT", 5.0)

# Stolen from aureon_radar/capital_cfd_trader.py CAPITAL_MARGIN_FALLBACK_PCT
# (used for venue="capital"; other venues default to 100% = spot, leverage 1)
CAPITAL_MARGIN_FALLBACK_PCT = {
    "forex": 5.0, "indices": 10.0, "index": 10.0,
    "commodities": 10.0, "commodity": 10.0,
    "stocks": 20.0, "stock": 20.0, "shares": 20.0, "share": 20.0,
    "crypto": 50.0, "cryptocurrency": 50.0, "unknown": 20.0,
}

MAX_MOVERS = int(_env_float("SIZING_MAX_MOVERS", 10))
KLINES_LIMIT = int(_env_float("SIZING_KLINES_LIMIT", 50))
ATR_PERIOD = int(_env_float("SIZING_ATR_PERIOD", 14))

# Symbol alias maps for cross-file lookups
STABLE_SUFFIXES = ("USDT", "USDC", "USD", "EUR", "GBP")


# ── generic helpers ─────────────────────────────────────────────────────────

def _as_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _base(symbol: str) -> str:
    s = str(symbol or "").upper().replace("/", "").replace("-", "")
    for suf in STABLE_SUFFIXES:
        if s.endswith(suf) and len(s) > len(suf):
            return s[: -len(suf)]
    return s


def _read_json(path: Path) -> Optional[dict]:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── inputs ──────────────────────────────────────────────────────────────────

def load_equity(errors: List[str]) -> Optional[float]:
    """Equity = last history entry total_usd in real_portfolio_state.json."""
    data = _read_json(RADAR_DIR / "real_portfolio_state.json")
    if not data:
        errors.append("real_portfolio_state.json missing/unreadable; equity unknown")
        return None
    history = data.get("history") or []
    if not history:
        errors.append("real_portfolio_state.json has no history; equity unknown")
        return None
    equity = _as_float(history[-1].get("total_usd"))
    if equity is None or equity <= 0:
        errors.append("last history total_usd missing or non-positive; equity unknown")
        return None
    return equity


def load_free_by_venue() -> Dict[str, float]:
    """free_usd per venue from trading_progress_state.json capital.by_venue."""
    data = _read_json(STATE_DIR / "trading_progress_state.json") or {}
    by_venue = (data.get("capital") or {}).get("by_venue") or {}
    free: Dict[str, float] = {}
    for venue, info in by_venue.items():
        val = _as_float((info or {}).get("free_usd"))
        if val is not None:
            free[str(venue).lower()] = max(0.0, val)
    return free


def load_existing_margin(positions: List[dict]) -> float:
    """Estimated MARGIN-VENUE margin already used (Capital CFD positions only —
    spot positions consume free cash, not a margin-level budget), stealing
    capital_cfd_trader._position_margin_estimate."""
    total = 0.0
    for pos in positions:
        if str(pos.get("venue") or "").lower() != "capital":
            continue
        size_usd = _as_float(pos.get("size_usd"), 0.0) or 0.0
        asset_class = str(pos.get("asset_class") or _guess_asset_class(pos.get("symbol")) or "unknown")
        factor = CAPITAL_MARGIN_FALLBACK_PCT.get(asset_class, CAPITAL_MARGIN_FALLBACK_PCT["unknown"])
        total += size_usd * factor / 100.0
    return total


def _guess_asset_class(symbol: Any) -> str:
    base = _base(str(symbol or ""))
    if base in {"BTC", "ETH", "SOL", "XBT", "LTC", "XRP", "ADA", "DOT", "DOGE", "TAO", "ZEC",
                "RAY", "JUP", "ORCA", "TIA", "JTO", "ZAMA"}:
        return "crypto"
    return "unknown"


def load_movers(errors: List[str]) -> List[dict]:
    data = _read_json(STATE_DIR / "global_energy_flow.json")
    if not data:
        errors.append("global_energy_flow.json missing/unreadable; no movers")
        return []
    movers = []
    for m in (data.get("movers") or [])[:MAX_MOVERS]:
        sym = str(m.get("symbol") or "").upper().strip()
        if not sym:
            continue
        direction = "long" if str(m.get("direction") or "").lower() == "up" else "short"
        confidence = _clamp(_as_float(m.get("confidence"), 0.0) or 0.0, 0.0, 1.0)
        flow = _clamp(_as_float(m.get("flow_score"), 0.0) or 0.0, 0.0, 1.0)
        movers.append({
            "symbol": sym,
            "venue": str(m.get("venue_hint") or "binance").lower(),
            "direction": direction,
            "conviction": round(confidence * flow, 4),
            "price_hint": _as_float(m.get("price")),
            "change_pct": _as_float(m.get("change_pct")),
            "kind": "mover",
        })
    return movers


def load_open_position_candidates(errors: List[str]) -> List[dict]:
    data = _read_json(STATE_DIR / "trading_progress_state.json")
    if not data:
        return []
    cands = []
    for pos in data.get("positions") or []:
        sym = str(pos.get("symbol") or "").upper().strip()
        if not sym:
            continue
        criteria = pos.get("criteria") or {}
        conviction = _clamp(_as_float(criteria.get("expectancy_confidence"), 0.0) or 0.0, 0.0, 1.0)
        cands.append({
            "symbol": sym,
            "venue": str(pos.get("venue") or "").lower(),
            "direction": "long" if str(pos.get("direction") or "").lower() in ("buy", "long") else "short",
            "conviction": conviction,
            "price_hint": _as_float(pos.get("current")) or _as_float(pos.get("entry")),
            "size_usd_current": _as_float(pos.get("size_usd")),
            "entry": _as_float(pos.get("entry")),
            "kind": "open_position",
        })
    return cands


# ── volatility: real ATR ────────────────────────────────────────────────────

def _binance_pair(symbol: str) -> str:
    pair = str(symbol).replace("/", "").replace("-", "").upper()
    if pair.endswith("USD") and not pair.endswith(("USDT", "USDC")):
        pair += "T"
    if not pair.endswith(STABLE_SUFFIXES):
        # bare base (movers ship symbols like "HEMI") — default quote USDT
        pair += "USDT"
    return pair


def _kraken_pair(symbol: str) -> str:
    base = _base(symbol)
    kraken_map = {"BTC": "XBT", "XBT": "XBT"}
    return f"{kraken_map.get(base, base)}USD"


def _true_ranges(candles: List[Tuple[float, float, float]]) -> List[float]:
    """candles: [(high, low, close), ...] chronological."""
    trs = []
    prev_close: Optional[float] = None
    for high, low, close in candles:
        if close <= 0:
            continue
        if prev_close is None:
            tr = high - low
        else:
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        if tr >= 0:
            trs.append(tr)
        prev_close = close
    return trs


# Public kline mirrors (all serve /api/v3/klines, no auth). Binance's anycast
# intermittently answers spurious 400 "Invalid symbol." for valid pairs, so the
# fetch rotates through mirrors instead of trusting one host's verdict.
_BINANCE_KLINE_HOSTS = (
    "https://api.binance.com",
    "https://data-api.binance.vision",
    "https://api1.binance.com",
    "https://api2.binance.com",
)


def _fetch_binance_candles(cache, pair: str) -> Tuple[List[Tuple[float, float, float]], Optional[str]]:
    """1h klines for pair from the first public mirror that answers 200.
    Non-200 on one host is NOT proof the pair is unlisted — rotated past."""
    candles: List[Tuple[float, float, float]] = []
    for host in _BINANCE_KLINE_HOSTS:
        url = (f"{host}/api/v3/klines?symbol={pair}"
               f"&interval=1h&limit={KLINES_LIMIT}")
        try:
            if not cache.limiter.acquire():
                continue
            resp = cache._session.get(url, timeout=10)
            if resp.status_code == 200:
                rows = resp.json()
                candles = [(float(r[2]), float(r[3]), float(r[4])) for r in rows if len(r) >= 5]
                if len(candles) >= ATR_PERIOD + 1:
                    return candles, f"binance_klines:{pair}"
                candles = []  # too few rows on this host; try the next mirror
        except Exception:
            continue
    return [], None


def fetch_atr_from_klines(symbol: str, cache) -> Tuple[Optional[float], Optional[str]]:
    """Real ATR(14) % from public 1h klines, rate-limited through the shared
    price cache's limiter + session. Falls back to Kraken OHLC, then the
    caller falls back to journaled marks. Returns (atr_pct, source) or (None, None)."""
    pair = _binance_pair(symbol)
    candles, source = _fetch_binance_candles(cache, pair)
    if len(candles) < ATR_PERIOD + 1:
        # Kraken OHLC fallback (1h candles)
        kp = _kraken_pair(symbol)
        url = f"https://api.kraken.com/0/public/OHLC?pair={kp}&interval=60"
        try:
            if cache.limiter.acquire():
                resp = cache._session.get(url, timeout=10)
                data = resp.json()
                rows = None
                for key, val in (data.get("result") or {}).items():
                    if key != "last" and isinstance(val, list) and val:
                        rows = val
                        break
                if rows:
                    candles = [(float(r[2]), float(r[3]), float(r[4])) for r in rows[-KLINES_LIMIT:]]
                    source = f"kraken_ohlc:{kp}"
        except Exception:
            candles = []
    if len(candles) < ATR_PERIOD + 1:
        return None, None
    trs = _true_ranges(candles)
    if len(trs) < ATR_PERIOD:
        return None, None
    atr = sum(trs[-ATR_PERIOD:]) / ATR_PERIOD
    close = candles[-1][2]
    if close <= 0:
        return None, None
    return round(atr / close * 100.0, 4), source


def fetch_vol_from_journal(symbol: str) -> Tuple[Optional[float], Optional[str]]:
    """Fallback realized volatility from journaled marks in
    price_cache_journal.jsonl: mean |% change| between consecutive marks
    for this symbol (any venue alias). Labelled as an estimate."""
    path = STATE_DIR / "price_cache_journal.jsonl"
    marks: List[Tuple[float, float]] = []  # (epoch, price)
    aliases = {_base(symbol), str(symbol).upper().replace("/", "")}
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("event") not in ("fetch_ok", "cache_hit"):
                    continue
                rec_sym = str(rec.get("symbol") or "").upper().replace("/", "")
                price = _as_float(rec.get("price"))
                ts = rec.get("ts") or rec.get("as_of")
                if price is None or not ts or rec_sym not in aliases:
                    continue
                try:
                    epoch = datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
                except ValueError:
                    continue
                marks.append((epoch, price))
    except OSError:
        return None, None
    marks.sort()
    rets = []
    for (_, p0), (_, p1) in zip(marks, marks[1:]):
        if p0 > 0:
            rets.append(abs(p1 - p0) / p0 * 100.0)
    if len(rets) < 5:
        return None, None
    return round(sum(rets) / len(rets), 4), "journal_marks_estimate"


def get_volatility(symbol: str, cache) -> Tuple[Optional[float], Optional[str]]:
    atr, src = fetch_atr_from_klines(symbol, cache)
    if atr is not None:
        return atr, src
    return fetch_vol_from_journal(symbol)


# ── alignment inputs ────────────────────────────────────────────────────────

def load_harmonic() -> Dict[str, Any]:
    return _read_json(STATE_DIR / "harmonic_phase.json") or {}


def harmonic_multiplier(symbol: str, harmonic: dict) -> Tuple[float, str, Optional[float]]:
    """Crest/in-phase boosts conviction, trough reduces it (owner decree)."""
    symbols = harmonic.get("symbols") or {}
    key = f"{_base(symbol)}USD"
    entry = symbols.get(key) or symbols.get(_binance_pair(symbol)) or {}
    if not entry:
        return 1.0, "neutral_no_symbol_entry", None
    hint = str(entry.get("phase_hint") or "neutral").lower()
    coherence = _clamp(_as_float(entry.get("coherence"), 0.0) or 0.0, 0.0, 1.0)
    if hint == "crest":
        base = 1.25
    elif hint in ("in_phase", "in-phase", "rising"):
        base = 1.10
    elif hint == "trough":
        base = 0.50
    elif hint in ("falling", "out_of_phase"):
        base = 0.75
    else:
        base = 1.0
    # coherence modulates toward/away from neutral
    mult = 1.0 + (base - 1.0) * (0.5 + coherence)
    return round(_clamp(mult, 0.25, 1.75), 4), hint, round(coherence, 4)


def load_ttc() -> Dict[str, Any]:
    return _read_json(STATE_DIR / "time_to_capture.json") or {}


def ttc_multiplier(symbol: str, ttc: dict) -> Tuple[float, Optional[float], str]:
    """Faster journaled capture -> higher conviction multiplier."""
    symbols = ttc.get("symbols") or {}
    entry = symbols.get(_base(symbol)) or symbols.get(str(symbol).upper()) or {}
    if not entry:
        # try alias lists
        base = _base(symbol)
        for _, cand in symbols.items():
            aliases = [str(a).upper() for a in (cand.get("aliases") or [])]
            if base in {_base(a) for a in aliases}:
                entry = cand
                break
    if not entry:
        return 1.0, None, "no_ttc_entry"
    m1 = _as_float(entry.get("median_min_to_1pct"))
    if m1 is None:
        return 1.0, None, "no_win_capture_observed"
    if m1 <= 30:
        mult = 1.30
    elif m1 <= 120:
        mult = 1.15
    elif m1 <= 360:
        mult = 1.00
    else:
        mult = 0.80
    return mult, round(m1, 2), "journaled"


# ── the anatomy: sizing math ────────────────────────────────────────────────

def deploy_fraction(equity: float) -> float:
    """Stolen from DynamicMarginConfig: tiny accounts deploy more of free margin."""
    return TINY_DEPLOY_FRACTION if equity <= TINY_EQUITY_USD else DEPLOY_FRACTION


def margin_factor_pct(venue: str, symbol: str) -> float:
    if venue == "capital":
        return CAPITAL_MARGIN_FALLBACK_PCT.get(_guess_asset_class(symbol),
                                               CAPITAL_MARGIN_FALLBACK_PCT["unknown"])
    return 100.0  # spot venues: margin = notional at leverage 1 (conservative)


def size_candidate(
    cand: dict,
    *,
    equity: float,
    free_by_venue: Dict[str, float],
    harmonic: dict,
    ttc: dict,
    capture_floor_pct: Optional[float],
    margin_budget_remaining: float,
    cache,
) -> dict:
    symbol = cand["symbol"]
    venue = cand["venue"]
    direction = cand["direction"]
    conviction = _clamp(cand.get("conviction") or 0.0, 0.0, 1.0)
    reason_bits: List[str] = []

    # 1. price (fail-closed: no price -> no size)
    price = cand.get("price_hint")
    price_src = "mover_state" if price is not None else None
    if price is None or price <= 0:
        probe = cache.get_price(symbol, source="binance")
        if probe.get("price"):
            price, price_src = float(probe["price"]), f"price_cache:{probe['source']}"
    if price is None or price <= 0:
        return {
            "symbol": symbol, "venue": venue, "direction": direction,
            "conviction": conviction, "vol_atr_pct": None, "vol_source": None,
            "price_usd": None, "price_source": None,
            "harmonic_mult": None, "harmonic_hint": None, "harmonic_coherence": None,
            "ttc_mult": None, "ttc_min_to_1pct": None, "stop_pct": None,
            "size_usd": None, "risk_usd": None, "risk_pct_of_equity": None,
            "margin_usd": None, "stress_impact_pct": None,
            "max_size_allowed": None, "min_notional_usd": None,
            "meets_capture_floor": None, "tradable": False,
            "reason": "no live price from any source (fail-closed)",
        }

    # 2. real volatility (fail-closed: no ATR -> size null, never invented)
    vol_atr_pct, vol_source = get_volatility(symbol, cache)

    # 3. harmonic phase alignment (owner decree: crest/in-phase boosts, trough reduces)
    harmonic_mult, harmonic_hint, harmonic_coh = harmonic_multiplier(symbol, harmonic)

    # 4. time-to-capture
    ttc_mult, ttc_min, ttc_basis = ttc_multiplier(symbol, ttc)

    # 5. conviction -> dynamic risk budget
    adj_conviction = _clamp(conviction * harmonic_mult * ttc_mult, 0.0, 1.5)
    risk_pct = BASE_RISK_COEFF * 100.0 * (adj_conviction ** 1.5)
    stress_cap = TINY_STRESS_CAP_PCT if equity <= TINY_EQUITY_USD else STRESS_CAP_PCT
    risk_pct = _clamp(risk_pct, 0.0, min(HARD_RISK_CAP_PCT, stress_cap / STRESS_SL_PCT * 100.0))
    risk_usd = equity * risk_pct / 100.0

    # 6. venue minimum notional (stolen pair_min_notional fallback)
    min_notional = FALLBACK_MIN_NOTIONAL_USD

    # 7. dynamic stop from ATR
    stop_pct = (ATR_STOP_MULTIPLE * vol_atr_pct) if vol_atr_pct else None

    # 8. free cash + margin-level gate (stolen max_safe_notional bones).
    # Spot venues: binding constraint is deployable free cash. Margin venues
    # (capital CFD): also enforce the projected margin-level floor (250%).
    free_usd = free_by_venue.get(venue, 0.0)
    deploy_frac = deploy_fraction(equity)
    if venue == "capital":
        max_margin_this = min(free_usd * deploy_frac, margin_budget_remaining)
    else:
        max_margin_this = free_usd * deploy_frac
    mfactor = margin_factor_pct(venue, symbol) / 100.0
    max_size_allowed = max_margin_this / mfactor if mfactor > 0 else 0.0

    # 9. capture-floor annotation (never weakened — annotation only)
    meets_floor: Optional[bool] = None
    if capture_floor_pct is not None:
        if ttc_min is not None:
            meets_floor = True  # journaled 1% crossing observed (floor == 1.0)
        elif cand.get("change_pct") is not None:
            meets_floor = abs(cand["change_pct"]) >= capture_floor_pct

    if vol_atr_pct is None or stop_pct is None or stop_pct <= 0:
        return {
            "symbol": symbol, "venue": venue, "direction": direction,
            "conviction": round(adj_conviction, 4), "vol_atr_pct": None,
            "vol_source": vol_source, "price_usd": round(price, 6), "price_source": price_src,
            "harmonic_mult": harmonic_mult, "harmonic_hint": harmonic_hint,
            "harmonic_coherence": harmonic_coh,
            "ttc_mult": ttc_mult, "ttc_min_to_1pct": ttc_min,
            "stop_pct": None, "size_usd": None, "risk_usd": round(risk_usd, 4),
            "risk_pct_of_equity": round(risk_pct, 4), "margin_usd": None,
            "stress_impact_pct": None, "max_size_allowed": round(max_size_allowed, 4),
            "min_notional_usd": min_notional, "meets_capture_floor": meets_floor,
            "tradable": False,
            "reason": "volatility unavailable (no klines, insufficient journaled marks) — size null by fail-closed policy",
        }

    # 10. risk-based size, volatility-normalized (the fully dynamic core)
    size_risk = risk_usd / (stop_pct / 100.0)
    # stress cap: a -STRESS_SL_PCT% SL move may not lose more than stress_cap of equity
    size_stress = equity * stress_cap / 100.0 / (STRESS_SL_PCT / 100.0)
    size_usd = min(size_risk, size_stress, max_size_allowed)

    tradable = True
    if max_size_allowed <= 0:
        tradable = False
        reason_bits.append(
            f"no deployable free cash at venue '{venue}' "
            f"(free ${free_usd:.2f} x deploy {deploy_frac:.0%}); raw risk-based size "
            f"${size_risk:.2f} cannot be placed")
    elif size_usd < min_notional:
        tradable = False
        reason_bits.append(
            f"dynamic size ${size_usd:.2f} (raw risk-based ${size_risk:.2f}, "
            f"max allowed ${max_size_allowed:.2f}) below venue/pair minimum ${min_notional:.2f}")
    if not reason_bits:
        reason_bits.append(
            f"risk ${risk_usd:.2f} ({risk_pct:.2f}% equity) / stop {stop_pct:.2f}% "
            f"(= {ATR_STOP_MULTIPLE:g}x ATR {vol_atr_pct:.2f}%) "
            f"x conv {adj_conviction:.2f} (harmonic x{harmonic_mult:.2f} {harmonic_hint}, "
            f"ttc x{ttc_mult:.2f} {ttc_basis}); capped by "
            f"{'stress cap' if size_stress <= size_risk and size_stress <= max_size_allowed else 'free cash/margin gate' if max_size_allowed <= size_risk else 'risk budget'}"
        )

    margin_usd = size_usd * mfactor
    stress_impact_pct = size_usd * (STRESS_SL_PCT / 100.0) / equity * 100.0 if equity > 0 else None

    return {
        "symbol": symbol, "venue": venue, "direction": direction,
        "conviction": round(adj_conviction, 4),
        "vol_atr_pct": vol_atr_pct, "vol_source": vol_source,
        "price_usd": round(price, 6), "price_source": price_src,
        "harmonic_mult": harmonic_mult, "harmonic_hint": harmonic_hint,
        "harmonic_coherence": harmonic_coh,
        "ttc_mult": ttc_mult, "ttc_min_to_1pct": ttc_min,
        "stop_pct": round(stop_pct, 4),
        "size_usd": round(size_usd, 4) if tradable else None,
        "size_usd_raw_below_min": round(size_usd, 4),
        "risk_usd": round(risk_usd, 4),
        "risk_pct_of_equity": round(risk_pct, 4),
        "margin_usd": round(margin_usd, 4),
        "stress_impact_pct": round(stress_impact_pct, 4) if stress_impact_pct is not None else None,
        "max_size_allowed": round(max_size_allowed, 4),
        "min_notional_usd": min_notional,
        "meets_capture_floor": meets_floor,
        "tradable": tradable,
        "reason": "; ".join(reason_bits),
    }


# ── main ────────────────────────────────────────────────────────────────────

def build_anatomy() -> dict:
    errors: List[str] = []
    equity = load_equity(errors)
    free_by_venue = load_free_by_venue()
    harmonic = load_harmonic()
    ttc = load_ttc()
    floor_data = _read_json(STATE_DIR / "capture_floor.json") or {}
    capture_floor_pct = _as_float(floor_data.get("min_gain_pct"))

    movers = load_movers(errors)
    open_pos = load_open_position_candidates(errors)

    # existing margin used (for the margin-level gate budget)
    tps = _read_json(STATE_DIR / "trading_progress_state.json") or {}
    existing_margin = load_existing_margin(tps.get("positions") or [])
    if equity is not None:
        level_cap_total = max(0.0, equity * 100.0 / ENTRY_MIN_MARGIN_PCT - existing_margin)
    else:
        level_cap_total = 0.0

    sys.path.insert(0, str(RADAR_DIR))
    from exchange_adapters.price_cache import get_shared_cache
    cache = get_shared_cache()

    candidates: List[dict] = []
    margin_spent = 0.0
    # highest conviction first so the margin budget goes to the best plays
    all_cands = sorted(movers + open_pos, key=lambda c: -(c.get("conviction") or 0.0))
    for cand in all_cands:
        budget = max(0.0, level_cap_total - margin_spent)
        try:
            sized = size_candidate(
                cand, equity=equity or 0.0, free_by_venue=free_by_venue,
                harmonic=harmonic, ttc=ttc, capture_floor_pct=capture_floor_pct,
                margin_budget_remaining=budget, cache=cache,
            )
        except Exception as exc:  # never let one symbol kill the run
            sized = {
                "symbol": cand["symbol"], "venue": cand["venue"],
                "direction": cand["direction"], "conviction": cand.get("conviction"),
                "vol_atr_pct": None, "size_usd": None, "risk_usd": None,
                "risk_pct_of_equity": None, "margin_usd": None,
                "stress_impact_pct": None, "max_size_allowed": None,
                "tradable": False, "reason": f"sizing error: {type(exc).__name__}: {exc}",
            }
            errors.append(f"{cand['symbol']}: {type(exc).__name__}: {exc}")
        candidates.append(sized)
        if sized.get("margin_usd"):
            margin_spent += sized["margin_usd"]

    # positions_resized: advisory re-size of open positions vs dynamic target
    positions_resized = []
    for cand in open_pos:
        match = next((c for c in candidates if c["symbol"] == cand["symbol"]
                      and c["direction"] == cand["direction"]), None)
        current = cand.get("size_usd_current")
        if match is None or current is None:
            continue
        target = match.get("size_usd")
        if target is None:
            action, delta = "hold_fail_closed", 0.0
        else:
            delta = target - current
            action = "increase" if delta > 0.01 else "decrease" if delta < -0.01 else "hold"
        positions_resized.append({
            "symbol": cand["symbol"], "venue": cand["venue"],
            "direction": cand["direction"],
            "current_size_usd": round(current, 4),
            "dynamic_target_size_usd": target,
            "delta_usd": round(delta, 4) if target is not None else None,
            "action": action,
            "note": "advisory only — perception layer emits no orders",
        })

    return {
        "ts": time.time(),
        "ts_iso": _utc_now_iso(),
        "equity_usd": round(equity, 4) if equity is not None else None,
        "equity_source": "real_portfolio_state.json:last_history.total_usd",
        "free_by_venue": free_by_venue,
        "deploy_fraction": deploy_fraction(equity or 0.0),
        "margin_level_floor_pct": ENTRY_MIN_MARGIN_PCT,
        "existing_margin_used_usd": round(existing_margin, 4),
        "capture_floor_pct": capture_floor_pct,
        "capture_floor_source": floor_data.get("source"),
        "sizing_model": "risk_usd=equity*base_risk*conviction^1.5*harmonic*ttc; "
                        "stop=ATR_STOP_MULTIPLE*ATR%; size=risk/stop; "
                        "capped by free cash, stress cap, margin-level gate",
        "candidates": candidates,
        "positions_resized": positions_resized,
        "errors": errors,
    }


def main() -> int:
    try:
        from aureon.utils.console_utf8 import ensure_utf8_stdout
        ensure_utf8_stdout()
    except Exception:
        pass

    anatomy = build_anatomy()
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = OUT_PATH.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(anatomy, fh, indent=2)
    os.replace(tmp, OUT_PATH)

    print(f"sizing_anatomy -> {OUT_PATH}")
    print(f"equity_usd={anatomy['equity_usd']} free_by_venue={anatomy['free_by_venue']}")
    for c in anatomy["candidates"]:
        print(f"  {c['symbol']:<12} {c['direction']:<5} conv={c.get('conviction')} "
              f"atr%={c.get('vol_atr_pct')} size={c.get('size_usd')} "
              f"risk%={c.get('risk_pct_of_equity')} margin={c.get('margin_usd')} "
              f"tradable={c.get('tradable')} :: {str(c.get('reason'))[:110]}")
    if anatomy["errors"]:
        print(f"ERRORS: {anatomy['errors']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
