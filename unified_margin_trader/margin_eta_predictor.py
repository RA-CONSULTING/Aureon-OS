#!/usr/bin/env python3
"""
MARGIN ETA PREDICTOR - TIME-TO-PROFIT CALCULATOR
================================================

Reads YOUR REAL open Kraken margin positions (SOL, ETH - whatever is actually
live on Kraken) and estimates when each will turn profitable.

Data source priority:
  1. Kraken API -> /0/private/OpenPositions  (live, authoritative)
  2. kraken_margin_army_state.json           (local cache fallback)

Usage:
    python margin_eta_predictor.py          # Single snapshot
    python margin_eta_predictor.py --watch  # Live 60-second loop
"""

import os
import json
import time
import urllib.request
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BINANCE_TICKER_URL = "https://api.binance.com/api/v3/ticker/price"
BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
KRAKEN_TICKER_URL  = "https://api.kraken.com/0/public/Ticker"
ARMY_STATE_FILE    = "kraken_margin_army_state.json"


@dataclass
class PositionETA:
    symbol: str
    side: str
    leverage: float
    entry_price: float
    current_price: float
    breakeven_price: float
    volume: float
    cost_basis: float
    unrealized_pnl: float
    pct_to_breakeven: float
    pct_from_entry: float
    hourly_volatility_pct: Optional[float]
    eta_minutes: Optional[float]
    bullish_eta_minutes: Optional[float]
    bearish_eta_minutes: Optional[float]
    confidence: float
    # ── Unified system metrics (Nexus / Seer / Lyra) ──────────────────────
    coherence: float = 0.5
    clarity: float = 1.0
    chaos_trend: str = "stable"
    seer_grade: str = "UNKNOWN"
    seer_score: float = 0.5
    seer_action: str = "HOLD"
    lyra_action: str = "HOLD"
    lyra_score: float = 0.5
    lyra_exit_urgency: str = "none"
    eta_multiplier: float = 1.0   # how system alignment shifted raw ETA
    source: str = "unknown"
    price_source: str = "none"    # which venue supplied the live price probe
    error: str = ""               # non-empty => the ETA fields are null by fail-closed policy
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


# ── helpers ────────────────────────────────────────────────────────────────

def _fetch(url: str) -> Optional[dict]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MarginETA/2.0"})
        with urllib.request.urlopen(req, timeout=6) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        logger.debug(f"HTTP {url}: {e}")
        return None


def probe_current_price(symbol: str) -> Optional[dict]:
    """Probe live price with provenance. Returns None when no venue answers —
    never substitute a cached/stale value for a fresh observation."""
    b_sym = symbol.upper().replace("USD", "USDT")
    d = _fetch(f"{BINANCE_TICKER_URL}?symbol={b_sym}")
    if d and "price" in d:
        try:
            return {"price": float(d["price"]), "source": "binance"}
        except (TypeError, ValueError):
            pass
    # Kraken public fallback
    d = _fetch(f"{KRAKEN_TICKER_URL}?pair={symbol}")
    if d and d.get("result"):
        for ticker in d["result"].values():
            try:
                return {"price": float(ticker["c"][0]), "source": "kraken"}
            except (TypeError, ValueError, KeyError, IndexError):
                pass
    return None


def get_current_price(symbol: str) -> Optional[float]:
    """Live price only. None when no venue probe succeeds (no stale fallback)."""
    probe = probe_current_price(symbol)
    return probe["price"] if probe else None


def probe_hourly_vol(symbol: str) -> Optional[float]:
    """Average absolute hourly return (%) over last 24 candles, or None if the
    probe fails (no fabricated default — consumers must treat ETA as unknown)."""
    b_sym = symbol.upper().replace("USD", "USDT")
    data = _fetch(f"{BINANCE_KLINES_URL}?symbol={b_sym}&interval=1h&limit=24")
    if not data or len(data) < 2:
        return None
    try:
        closes = [float(c[4]) for c in data]
    except (TypeError, ValueError, IndexError):
        return None
    returns = [abs((closes[i] - closes[i-1]) / closes[i-1]) * 100 for i in range(1, len(closes))]
    if not returns:
        return None
    return max(sum(returns) / len(returns), 0.1)


def calc_breakeven(entry: float, open_fee: float = 0.00376, close_fee: float = 0.0035) -> float:
    return entry * (1 + open_fee + close_fee + 0.0001)


def normalise_pair(pair: str) -> str:
    MAP = {
        "XETHZUSD": "ETHUSD", "XBTZUSD": "XBTUSD", "XXBTZUSD": "XBTUSD",
        "XSOLUSD":  "SOLUSD", "XLTCZUSD": "LTCUSD", "XXRPZUSD": "XRPUSD",
    }
    if pair in MAP:
        return MAP[pair]
    p = pair
    if p.startswith("X") and len(p) > 4 and p[1:4].isupper():
        p = p[1:]
    if p.endswith("ZUSD"):
        p = p[:-4] + "USD"
    return p


# ── position loaders ────────────────────────────────────────────────────────

def load_from_kraken_api() -> List[dict]:
    """Fetch ALL live open margin positions via Kraken private API."""
    try:
        from aureon.exchanges.kraken_client import KrakenClient
        client = KrakenClient()
        if client.dry_run:
            return []
        raw = client.get_open_margin_positions(do_calcs=True)
        if not raw:
            return []
        results = []
        for pos in raw:
            symbol  = normalise_pair(pos.get("pair", ""))
            vol     = float(pos.get("volume", 0))
            cost    = float(pos.get("cost", 0))
            fee     = float(pos.get("fee", 0))
            ep      = cost / vol if vol > 0 else 0
            lev_raw = pos.get("leverage", "1")
            lev     = float(lev_raw) if lev_raw else 1.0
            results.append({
                "symbol":          symbol,
                "side":            pos.get("side", "buy"),
                "volume":          vol,
                "cost":            cost,
                "fee":             fee,
                "entry_price":     ep,
                "leverage":        lev,
                "unrealized_pnl":  float(pos.get("unrealized_pnl", 0)),
                "breakeven_price": calc_breakeven(ep, fee / cost if cost > 0 else 0.00376),
                "source":          "kraken_api",
            })
        logger.info(f"Loaded {len(results)} live positions from Kraken API")
        return results
    except Exception as e:
        logger.warning(f"Kraken API unavailable ({e}), falling back to state file")
        return []


def load_from_state_files() -> List[dict]:
    """Read active positions from kraken_margin_army_state.json."""
    results = []
    try:
        with open(ARMY_STATE_FILE) as f:
            state = json.load(f)

        # Single active_trade field (army trader)
        trade = state.get("active_trade")
        if trade and trade.get("pair"):
            ep = float(trade.get("entry_price", 0))
            results.append({
                "symbol":          trade["pair"],
                "side":            trade.get("side", "buy"),
                "volume":          float(trade.get("volume", 0)),
                "cost":            float(trade.get("cost", 0)),
                "fee":             float(trade.get("entry_fee", 0)),
                "entry_price":     ep,
                "leverage":        float(trade.get("leverage", 1)),
                "unrealized_pnl":  0.0,
                "breakeven_price": float(trade.get("breakeven_price") or calc_breakeven(ep)),
                "source":          "army_state",
            })

        # active_trades dict (penny trader)
        for sym, t in state.get("active_trades", {}).items():
            ep = float(t.get("entry_price", 0))
            results.append({
                "symbol":          sym,
                "side":            t.get("side", "buy"),
                "volume":          float(t.get("volume", 0)),
                "cost":            float(t.get("cost", 0)),
                "fee":             float(t.get("entry_fee", 0)),
                "entry_price":     ep,
                "leverage":        float(t.get("leverage", 1)),
                "unrealized_pnl":  0.0,
                "breakeven_price": float(t.get("breakeven_price") or calc_breakeven(ep)),
                "source":          "army_state",
            })
    except Exception as e:
        logger.debug(f"State file load: {e}")

    return results


# ── Aureon system metric helpers ───────────────────────────────────────────

def get_nexus_metrics(symbol: str) -> dict:
    """
    Pull coherence / clarity / chaos_trend from SUBSYSTEM_STATE in
    aureon_probability_nexus.

    Uses sys.modules so this ONLY reads live data when the nexus is already
    imported (i.e. we are running inside the full ecosystem).  Standalone runs
    receive sane defaults without triggering a heavy boot sequence.
    """
    import sys
    defaults = {"coherence": 0.5, "clarity": 1.0, "chaos_trend": "stable"}
    try:
        mod = sys.modules.get("aureon_probability_nexus")
        if mod is None:
            return defaults
        SUBSYSTEM_STATE = getattr(mod, "SUBSYSTEM_STATE", {})
        for key in [
            symbol,
            symbol.upper(),
            symbol.upper().replace("USD", "USDT"),
            symbol[:3].upper() + "USD",
            symbol[:3].upper(),
        ]:
            if key in SUBSYSTEM_STATE:
                s = SUBSYSTEM_STATE[key]
                return {
                    "coherence":   float(s.get("avg_coherence", 0.5)),
                    "clarity":     float(s.get("avg_clarity",   1.0)),
                    "chaos_trend": str(s.get("chaos_trend",     "stable")),
                }
    except Exception as e:
        logger.debug(f"Nexus metrics unavailable for {symbol}: {e}")
    return defaults


# Shared per-run cache so Seer/Lyra are called only once
_seer_cache: dict = {}
_lyra_cache: dict = {}


def get_seer_vision() -> dict:
    """
    Get Seer's current vision grade + action.

    Reads from an already-running AureonTheSeer instance if 'aureon_seer'
    is in sys.modules (ecosystem running).  Returns neutral defaults for
    standalone runs — no ecosystem boot triggered.
    Caches result for 5 minutes.
    """
    import sys
    global _seer_cache
    now = time.time()
    if _seer_cache and (now - _seer_cache.get("_ts", 0)) < 300:
        return _seer_cache
    defaults = {"grade": "UNKNOWN", "score": 0.5, "action": "HOLD"}
    try:
        mod = sys.modules.get("aureon_seer")
        if mod is None:
            return defaults
        AureonTheSeer = getattr(mod, "AureonTheSeer", None)
        if AureonTheSeer is None:
            return defaults
        seer = AureonTheSeer()
        vision = seer.see()
        result = {
            "grade":  str(getattr(vision, "grade",         "UNKNOWN")),
            "score":  float(getattr(vision, "unified_score", 0.5)),
            "action": str(getattr(vision, "action",         "HOLD")),
            "_ts":    now,
        }
        _seer_cache = result
        return result
    except Exception as e:
        logger.debug(f"Seer unavailable: {e}")
    return defaults


def get_lyra_resonance() -> dict:
    """
    Get Lyra's current action + score + exit_urgency.

    Reads from an already-running AureonLyra instance if 'aureon_lyra'
    is in sys.modules (ecosystem running).  Returns neutral defaults for
    standalone runs.  Caches for 5 minutes.
    """
    import sys
    global _lyra_cache
    now = time.time()
    if _lyra_cache and (now - _lyra_cache.get("_ts", 0)) < 300:
        return _lyra_cache
    defaults = {"action": "HOLD", "score": 0.5, "exit_urgency": "none"}
    try:
        mod = sys.modules.get("aureon_lyra")
        if mod is None:
            return defaults
        AureonLyra = getattr(mod, "AureonLyra", None)
        if AureonLyra is None:
            return defaults
        lyra = AureonLyra()
        resonance = lyra.feel()
        result = {
            "action":       str(getattr(resonance, "action",        "HOLD")),
            "score":        float(getattr(resonance, "unified_score", 0.5)),
            "exit_urgency": str(getattr(resonance, "exit_urgency",  "none")),
            "_ts":          now,
        }
        _lyra_cache = result
        return result
    except Exception as e:
        logger.debug(f"Lyra unavailable: {e}")
    return defaults


def compute_eta_multiplier(
    seer_grade: str,
    coherence: float,
    chaos_trend: str,
    lyra_action: str,
    lyra_exit_urgency: str,
) -> float:
    """
    Convert unified system state into an ETA multiplier.

    < 1.0  → system alignment says move will happen FASTER than raw vol implies
    > 1.0  → system misalignment / fog says SLOWER / less certain

    Grid:
      Seer DIVINE_CLARITY  → × 0.60  (strong tailwind)
      Seer CLEAR_SIGHT     → × 0.75
      Seer PARTIAL_VISION  → × 1.00  (neutral)
      Seer FOG             → × 1.40
      Seer BLIND           → × 1.80  (heavy headwind / uncertainty)

      Nexus coherence ≥ 0.80 + chaos falling → additional × 0.85
      Nexus coherence < 0.40               → additional × 1.50

      Lyra SELL_BIAS / DEFEND while holding long → × 1.25 (resistance)
      Lyra BUY_BIAS while holding long       → × 0.90  (tailwind)
      Lyra exit_urgency high/critical        → × 1.50  (danger zone)
    """
    mult = 1.0

    # Seer grade component
    seer_map = {
        "DIVINE_CLARITY":  0.60,
        "CLEAR_SIGHT":     0.75,
        "PARTIAL_VISION":  1.00,
        "PARTIAL_SIGHT":   1.00,
        "FOG":             1.40,
        "BLIND":           1.80,
        "UNKNOWN":         1.10,
    }
    mult *= seer_map.get(seer_grade, 1.10)

    # Nexus coherence + chaos component
    if coherence >= 0.80 and chaos_trend.lower() == "falling":
        mult *= 0.85
    elif coherence < 0.40:
        mult *= 1.50

    # Lyra component (long bias)
    if lyra_exit_urgency in ("high", "critical"):
        mult *= 1.50
    elif lyra_action == "BUY_BIAS":
        mult *= 0.90
    elif lyra_action in ("SELL_BIAS", "DEFEND"):
        mult *= 1.25

    return round(max(0.1, min(10.0, mult)), 3)


# ── ETA calculation ─────────────────────────────────────────────────────────

def calculate_eta(pos: dict) -> Optional[PositionETA]:
    try:
        symbol    = pos["symbol"]
        ep        = pos["entry_price"]
        breakeven = pos["breakeven_price"]
        if ep <= 0:
            return None

        # ── Live price probe: fail closed, never reuse entry price as "current" ──
        price_probe = probe_current_price(symbol)
        if price_probe is None:
            logger.error(
                f"ETA {symbol}: no live price from any venue; "
                f"position reported with null price/ETA (no stale substitution)"
            )
            return PositionETA(
                symbol=symbol, side=pos.get("side", "buy"), leverage=pos["leverage"],
                entry_price=ep, current_price=None, breakeven_price=breakeven,
                volume=pos["volume"], cost_basis=pos["cost"],
                unrealized_pnl=pos.get("unrealized_pnl", 0),
                pct_to_breakeven=None, pct_from_entry=None,
                hourly_volatility_pct=None,
                eta_minutes=None, bullish_eta_minutes=None, bearish_eta_minutes=None,
                confidence=0.0,
                source=pos.get("source", "unknown"),
                error="live_price_unavailable",
            )
        current = price_probe["price"]
        price_source = price_probe["source"]

        pct_from_entry   = ((current - ep) / ep) * 100
        pct_to_breakeven = ((breakeven - current) / current) * 100

        hourly_vol_pct = probe_hourly_vol(symbol)
        vol_error = "hourly_volatility_unavailable" if hourly_vol_pct is None else ""

        # ── Pull unified system metrics ────────────────────────────────────
        nm        = get_nexus_metrics(symbol)
        coherence = nm["coherence"]
        clarity   = nm["clarity"]
        chaos     = nm["chaos_trend"]

        seer  = get_seer_vision()
        lyra  = get_lyra_resonance()

        eta_mult = compute_eta_multiplier(
            seer_grade       = seer["grade"],
            coherence        = coherence,
            chaos_trend      = chaos,
            lyra_action      = lyra["action"],
            lyra_exit_urgency= lyra["exit_urgency"],
        )

        if current >= breakeven:
            return PositionETA(
                symbol=symbol, side=pos.get("side", "buy"), leverage=pos["leverage"],
                entry_price=ep, current_price=current, breakeven_price=breakeven,
                volume=pos["volume"], cost_basis=pos["cost"],
                unrealized_pnl=pos.get("unrealized_pnl", 0),
                pct_to_breakeven=pct_to_breakeven, pct_from_entry=pct_from_entry,
                hourly_volatility_pct=hourly_vol_pct,
                eta_minutes=0, bullish_eta_minutes=0, bearish_eta_minutes=0,
                confidence=1.0,
                coherence=coherence, clarity=clarity, chaos_trend=chaos,
                seer_grade=seer["grade"], seer_score=seer["score"], seer_action=seer["action"],
                lyra_action=lyra["action"], lyra_score=lyra["score"],
                lyra_exit_urgency=lyra["exit_urgency"],
                eta_multiplier=eta_mult,
                source=pos.get("source", "unknown"),
                price_source=price_source,
                error=vol_error,
            )

        if hourly_vol_pct is None:
            # Price is live but volatility history is not: report position state,
            # keep every ETA estimate null rather than inventing a number.
            return PositionETA(
                symbol=symbol, side=pos.get("side", "buy"), leverage=pos["leverage"],
                entry_price=ep, current_price=current, breakeven_price=breakeven,
                volume=pos["volume"], cost_basis=pos["cost"],
                unrealized_pnl=pos.get("unrealized_pnl", 0),
                pct_to_breakeven=pct_to_breakeven, pct_from_entry=pct_from_entry,
                hourly_volatility_pct=None,
                eta_minutes=None, bullish_eta_minutes=None, bearish_eta_minutes=None,
                confidence=0.0,
                coherence=coherence, clarity=clarity, chaos_trend=chaos,
                seer_grade=seer["grade"], seer_score=seer["score"], seer_action=seer["action"],
                lyra_action=lyra["action"], lyra_score=lyra["score"],
                lyra_exit_urgency=lyra["exit_urgency"],
                eta_multiplier=eta_mult,
                source=pos.get("source", "unknown"),
                price_source=price_source,
                error=vol_error,
            )

        required = abs(pct_to_breakeven) / 100.0
        hv       = hourly_vol_pct / 100.0

        base_h    = min(required / hv, 999) if hv > 0 else 999
        bull_h    = max(0, (required - hv) / hv) if hv > 0 else 999
        bear_h    = min((required + hv) / hv, 999) if hv > 0 else 999

        # Apply system-alignment multiplier to raw volatility-based ETA
        eta_min   = base_h * 60 * 0.5 * eta_mult
        bull_min  = bull_h * 60 * 0.5 * eta_mult
        bear_min  = bear_h * 60 * 0.5 * eta_mult

        # Confidence blends raw vol ratio with system coherence
        raw_conf   = min(1.0, (hourly_vol_pct / max(abs(pct_to_breakeven), 0.01)) * 0.5)
        confidence = min(1.0, raw_conf * 0.6 + coherence * 0.4)

        return PositionETA(
            symbol=symbol, side=pos.get("side", "buy"), leverage=pos["leverage"],
            entry_price=ep, current_price=current, breakeven_price=breakeven,
            volume=pos["volume"], cost_basis=pos["cost"],
            unrealized_pnl=pos.get("unrealized_pnl", 0),
            pct_to_breakeven=pct_to_breakeven, pct_from_entry=pct_from_entry,
            hourly_volatility_pct=hourly_vol_pct,
            eta_minutes=eta_min, bullish_eta_minutes=bull_min, bearish_eta_minutes=bear_min,
            confidence=confidence,
            coherence=coherence, clarity=clarity, chaos_trend=chaos,
            seer_grade=seer["grade"], seer_score=seer["score"], seer_action=seer["action"],
            lyra_action=lyra["action"], lyra_score=lyra["score"],
            lyra_exit_urgency=lyra["exit_urgency"],
            eta_multiplier=eta_mult,
            source=pos.get("source", "unknown"),
            price_source=price_source,
            error=vol_error,
        )
    except Exception as e:
        logger.error(f"ETA calc {pos.get('symbol','?')}: {e}")
        return None


# ── main class ──────────────────────────────────────────────────────────────

class MarginETAPredictor:

    def predict_all(self) -> List[PositionETA]:
        raw = load_from_kraken_api()
        if not raw:
            raw = load_from_state_files()
        if not raw:
            logger.warning("No open margin positions found in any source")
            return []
        return [eta for pos in raw if (eta := calculate_eta(pos))]

    def print_report(self, etas: List[PositionETA]) -> None:
        print("\n" + "=" * 90)
        print("  MARGIN ETA REPORT — TIME-TO-PROFITABILITY  [UNIFIED AUREON METRICS]")
        print("=" * 90)
        print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        if not etas:
            print("  No active margin positions.\n")
            return

        # Print system-wide header once (same for all positions)
        first = etas[0]
        seer_icon = {
            "DIVINE_CLARITY": "🌟", "CLEAR_SIGHT": "👁",
            "PARTIAL_VISION": "🌤", "PARTIAL_SIGHT": "🌤",
            "FOG": "🌫", "BLIND": "🚫", "UNKNOWN": "❓",
        }.get(first.seer_grade, "❓")
        lyra_icon = {"BUY_BIAS": "🟢", "SELL_BIAS": "🔴", "DEFEND": "🛡", "HOLD": "🟡"}.get(first.lyra_action, "🟡")
        chaos_icon = {"falling": "📉", "rising": "📈", "stable": "➡"}.get(first.chaos_trend.lower(), "➡")

        print(f"  ╔══ SYSTEM ALIGNMENT ════════════════════════════════════════════════╗")
        print(f"  ║  Seer:    {seer_icon} {first.seer_grade:<18} (score {first.seer_score:.3f})  action: {first.seer_action}")
        print(f"  ║  Lyra:    {lyra_icon} {first.lyra_action:<18} (score {first.lyra_score:.3f})  urgency: {first.lyra_exit_urgency}")
        print(f"  ║  Nexus:   coherence {first.coherence:.3f}  clarity {first.clarity:.2f}  chaos {chaos_icon} {first.chaos_trend}")
        print(f"  ║  ETA mult: ×{first.eta_multiplier:.3f}  {'(tailwind — faster)' if first.eta_multiplier < 1.0 else '(headwind — slower)' if first.eta_multiplier > 1.0 else '(neutral)'}")
        print(f"  ╚═════════════════════════════════════════════════════════════════════╝\n")

        for eta in etas:
            src = "LIVE API" if eta.source == "kraken_api" else "STATE FILE"
            print(f"  [{src}] {eta.symbol}  |  {eta.side.upper()}  |  {eta.leverage:.0f}x leverage")
            print(f"    Entry:      {eta.entry_price:.4f}")
            if eta.current_price is None:
                print(f"    Current:    ⚠ no live price probe succeeded — null by fail-closed policy")
                if eta.error:
                    print(f"    Error:      {eta.error}")
                continue
            print(f"    Current:    {eta.current_price:.4f}  ({eta.pct_from_entry:+.2f}%)  [price source: {eta.price_source}]")
            print(f"    Breakeven:  {eta.breakeven_price:.4f}  ({eta.pct_to_breakeven:+.2f}% to go)")
            if eta.unrealized_pnl:
                print(f"    Live P&L:   ${eta.unrealized_pnl:+.2f}")
            print()
            if eta.eta_minutes == 0:
                print("    ✅  PROFITABLE NOW")
            elif eta.eta_minutes is None:
                print(f"    ⚠  ETA unknown: {eta.error or 'insufficient live data'}")
            else:
                print(f"    📊  Hourly vol:  {eta.hourly_volatility_pct:.2f}%")
                print(f"    ⏱   ETA (adj):   {eta.eta_minutes:.0f}m  ({eta.eta_minutes/60:.1f}h)  [×{eta.eta_multiplier:.2f}]")
                print(f"        Bullish:     {eta.bullish_eta_minutes:.0f}m  ({eta.bullish_eta_minutes/60:.1f}h)")
                print(f"        Bearish:     {eta.bearish_eta_minutes:.0f}m  ({eta.bearish_eta_minutes/60:.1f}h)")
                print(f"    🎯  Confidence:  {eta.confidence*100:.0f}%  (nexus coherence {eta.coherence:.2f})")
            print()

        tc  = sum(e.cost_basis for e in etas)
        tp  = sum(e.unrealized_pnl for e in etas)
        ok  = sum(1 for e in etas if e.eta_minutes == 0)
        err = sum(1 for e in etas if e.error)
        print("=" * 90)
        line = f"  {len(etas)} position(s)  |  {ok} profitable  |  Total cost: ${tc:.2f}"
        if tp:
            line += f"  |  Live P&L: ${tp:+.2f}"
        if err:
            line += f"  |  {err} with null fields (fail-closed)"
        print(line)
        print("=" * 90 + "\n")


# ── entry point ─────────────────────────────────────────────────────────────

def main():
    import sys
    p = MarginETAPredictor()
    etas = p.predict_all()
    p.print_report(etas)
    try:
        with open("margin_eta_report.json", "w") as f:
            json.dump({"timestamp": datetime.now().isoformat(),
                       "positions": [asdict(e) for e in etas]}, f, indent=2)
    except Exception:
        pass
    if "--watch" in sys.argv:
        print("📡 WATCH MODE — updating every 60s (Ctrl+C to stop)\n")
        try:
            while True:
                time.sleep(60)
                etas = p.predict_all()
                p.print_report(etas)
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
