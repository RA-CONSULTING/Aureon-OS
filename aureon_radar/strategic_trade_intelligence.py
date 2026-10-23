"""
Strategic Trade Intelligence Layer

Porter's 5 Forces, SWOT, cash-cow tagging, Fourier spectrum of recent returns,
harmonic lidar-style resonance mapping, cross-asset correlation, QGITA truth sweep,
and capital-allocation suggestion for a target trade.

Outputs are written to aureon_radar/strategic_analysis.jsonl and are designed to
be consumed by the organism's metacognitive loop (queen_mind / phi-radar).
"""

import json
import math
import sys
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np

# Import the price-feed router's communion client for fresh, gated fetches
try:
    from aureon_fusion.api_communion import get_json as _communion_get_json
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from aureon_fusion.api_communion import get_json as _communion_get_json

WORKSPACE = Path("C:/Users/user/.kimi_openclaw/workspace")
RADAR_DIR = WORKSPACE / "aureon_radar"
ANALYSIS_LOG = RADAR_DIR / "strategic_analysis.jsonl"

# Yahoo-style symbol map (must match aureon_price_feed.YAHOO_MAP)
YAHOO_MAP = {
    "USDJPY": "USDJPY=X", "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X",
    "US100": "^NDX",
    "AAPL": "AAPL", "TSLA": "TSLA", "NVDA": "NVDA",
    "GOLD": "GC=F", "SILVER": "SI=F", "OIL_CRUDE": "CL=F", "NATURALGAS": "NG=F",
    "BTCUSD": "BTC-USD", "ETHUSD": "ETH-USD",
}


def load_recent_closes(symbol: str, days: int = 30) -> Optional[np.ndarray]:
    """Fetch recent daily closes from Yahoo Finance (fresh, no simulation)."""
    yahoo_sym = YAHOO_MAP.get(symbol)
    if not yahoo_sym:
        return None
    try:
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_sym}?"
            f"interval=1h&range={days}d"
        )
        data = _communion_get_json(
            url, ttl_s=300, timeout=8,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        result = data.get("chart", {}).get("result", [{}])[0]
        closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
        closes = [c for c in closes if c is not None]
        return np.array(closes, dtype=float) if closes else None
    except Exception:
        return None


def fourier_spectrum(prices: np.ndarray) -> Dict[str, any]:
    """Return dominant frequencies and amplitudes of log-return series."""
    if prices is None or len(prices) < 16:
        return {"available": False}
    returns = np.diff(np.log(prices))
    n = len(returns)
    fft = np.fft.rfft(returns)
    amps = np.abs(fft)
    freqs = np.fft.rfftfreq(n, d=1.0)
    # Exclude DC
    mask = freqs > 0
    freqs = freqs[mask]
    amps = amps[mask]
    if len(amps) == 0:
        return {"available": False}
    top = int(np.argmax(amps))
    return {
        "available": True,
        "dominant_frequency": float(freqs[top]),
        "dominant_period_bars": float(1.0 / freqs[top]) if freqs[top] > 0 else None,
        "dominant_amplitude": float(amps[top]),
        "mean_amplitude": float(np.mean(amps)),
        "spectral_entropy": float(-np.sum((amps / amps.sum()) * np.log(amps / amps.sum() + 1e-12))),
    }


def cross_asset_correlations(symbols: List[str], days: int = 30) -> Dict[str, Dict[str, float]]:
    """Pearson correlation matrix of daily returns across the watchlist."""
    series = {}
    for sym in symbols:
        closes = load_recent_closes(sym, days)
        if closes is not None and len(closes) > 2:
            series[sym] = np.diff(np.log(closes))
    corr = {}
    for a, ra in series.items():
        corr[a] = {}
        min_len = min(len(ra), 30)
        ra_trim = ra[-min_len:]
        for b, rb in series.items():
            rb_trim = rb[-min_len:]
            if len(ra_trim) == len(rb_trim) and len(ra_trim) > 1:
                c = np.corrcoef(ra_trim, rb_trim)[0, 1]
                corr[a][b] = float(c) if not math.isnan(c) else 0.0
    return corr


def porters_five_forces(symbol: str, corr: Dict[str, Dict[str, float]],
                        spectrum: Dict[str, any]) -> Dict[str, str]:
    """Qualitative Porter forces driven by market data."""
    peers = {k: v for k, v in corr.get(symbol, {}).items() if k != symbol}
    avg_corr = float(np.mean(list(peers.values()))) if peers else 0.0
    volatility = spectrum.get("mean_amplitude", 0.0)

    def _force(score: float, high: str, mid: str, low: str) -> str:
        if score > 0.6:
            return high
        if score > 0.25:
            return mid
        return low

    return {
        "rivalry": _force(abs(avg_corr),
                          "HIGH — moves tightly with peers, crowded trade",
                          "MODERATE — some peer independence",
                          "LOW — idiosyncratic path"),
        "new_entrants": "LOW — liquid, established market",
        "buyer_power": _force(volatility,
                               "HIGH — choppy, buyers/sellers wrestle",
                               "MODERATE — two-sided flow",
                               "LOW — directional, one side in control"),
        "supplier_power": "MODERATE — macro/central-bank flow dominant",
        "substitutes": _force(avg_corr,
                              "HIGH — many correlated alternatives",
                              "MODERATE — some alternatives",
                              "LOW — few substitutes"),
    }


def swot_analysis(symbol: str, returns: np.ndarray, spectrum: Dict[str, any]) -> Dict[str, List[str]]:
    """Data-grounded SWOT for the trade idea."""
    strengths, weaknesses, opportunities, threats = [], [], [], []
    if returns is not None and len(returns) > 0:
        sharpe = float(np.mean(returns) / (np.std(returns) + 1e-12) * np.sqrt(len(returns)))
        if sharpe > 0.3:
            strengths.append(f"Positive recent risk-adjusted drift (sharpe={sharpe:.2f})")
        elif sharpe < -0.3:
            weaknesses.append(f"Negative recent risk-adjusted drift (sharpe={sharpe:.2f})")
        if np.std(returns) > 0.005:
            opportunities.append("Elevated volatility creates scalp room")
        else:
            threats.append("Low volatility compresses profit potential")
    if spectrum.get("available"):
        period = spectrum.get("dominant_period_bars")
        if period and period < 12:
            strengths.append(f"Short-cycle harmonic resonance detected (period={period:.1f}h)")
        elif period and period > 48:
            opportunities.append(f"Long-cycle harmonic floor may support trend (period={period:.1f}h)")
    if not strengths:
        strengths.append("Liquid, tradeable instrument")
    threats.append("Macro surprise / gap risk")
    return {"strengths": strengths, "weaknesses": weaknesses,
            "opportunities": opportunities, "threats": threats}


PHI = 1.618033988749895


def cash_cow_score(returns: np.ndarray) -> Dict[str, any]:
    """BCG-style label: cash cow, star, question mark, or dog."""
    if returns is None or len(returns) < 10:
        return {"label": "UNKNOWN", "sharpe": None, "win_rate": None}
    sharpe = float(np.mean(returns) / (np.std(returns) + 1e-12) * np.sqrt(len(returns)))
    wins = float(np.sum(returns > 0) / len(returns))
    if sharpe > 1.0 and wins > 0.55:
        label = "STAR"
    elif sharpe > 0.3 and wins > 0.5:
        label = "CASH_COW"
    elif sharpe > 0.0:
        label = "QUESTION_MARK"
    else:
        label = "DOG"
    return {"label": label, "sharpe": sharpe, "win_rate": wins}


def harmonic_lidar_map(prices: np.ndarray) -> Dict[str, any]:
    """Find spectral peaks near phi-scaled cycles (harmonic nexus mapping)."""
    spectrum = fourier_spectrum(prices)
    if not spectrum.get("available"):
        return {"available": False}
    period = spectrum.get("dominant_period_bars")
    if period is None or period <= 0:
        return {"available": False}
    phi_periods = [period * (PHI ** i) for i in range(-2, 3)]
    # Resonance score: how close the dominant period is to a phi lattice point
    resonance = 1.0 - min(abs(math.log(period / (PHI ** k))) for k in range(-5, 6)) / math.log(PHI)
    resonance = max(0.0, min(1.0, resonance))
    return {
        "available": True,
        "dominant_period_bars": period,
        "phi_scaled_periods": [float(p) for p in phi_periods],
        "harmonic_resonance_score": float(resonance),
        "interpretation": "strong_phi_lock" if resonance > 0.7 else "weak_phi_lock" if resonance > 0.4 else "noise",
    }


def forecast_timeline(prices: np.ndarray, horizon: int = 5) -> Dict[str, any]:
    """Simple momentum + mean-reversion forecast for the next `horizon` bars."""
    if prices is None or len(prices) < horizon + 2:
        return {"available": False}
    recent = prices[-horizon:]
    slope = np.polyfit(np.arange(len(recent)), recent, 1)[0]
    last = float(prices[-1])
    trend_only = [last + slope * (i + 1) for i in range(horizon)]
    # Mean-reversion pull toward 20-bar moving average
    ma20 = float(np.mean(prices[-20:])) if len(prices) >= 20 else last
    blended = [t * (0.7 + 0.03 * i) + ma20 * (0.3 - 0.03 * i) for i, t in enumerate(trend_only)]
    return {
        "available": True,
        "method": "momentum_plus_mean_reversion",
        "horizon_bars": horizon,
        "forecast_prices": [float(p) for p in blended],
        "trend_slope": float(slope),
        "ma20": ma20,
    }


def roi_forecast(entry: float, stop: float, tp: float,
                 win_rate: float = 0.55, trades: int = 100) -> Dict[str, float]:
    """Expected return and expectancy over a batch of identical trades."""
    risk = abs(entry - stop)
    reward = abs(tp - entry)
    if risk <= 0:
        return {"expectancy_per_trade": 0.0, "expected_roi_pct": 0.0, "breakeven_win_rate": 0.0}
    loss = -risk
    gain = reward
    expectancy = win_rate * gain + (1 - win_rate) * loss
    # Assume risk of 1% of capital per trade
    risk_pct = 0.01
    expected_roi_pct = expectancy / entry * risk_pct * trades * 100
    breakeven = risk / (risk + reward)
    return {
        "expectancy_per_trade": float(expectancy),
        "expected_roi_pct_100trades": float(expected_roi_pct),
        "breakeven_win_rate": float(breakeven),
        "risk_reward": float(reward / risk),
    }


def capital_allocation(entry: float, stop: float, tp: float,
                       balance: float, win_rate: float = 0.55) -> Dict[str, float]:
    """Kelly-like fraction plus conservative cap."""
    risk = abs(entry - stop)
    reward = abs(tp - entry)
    if risk <= 0:
        return {"fraction": 0.0, "kelly": 0.0, "capped_fraction": 0.0}
    b = reward / risk
    kelly = (win_rate * b - (1 - win_rate)) / b if b > 0 else 0.0
    kelly = max(0.0, min(kelly, 0.25))
    capped = min(kelly, 0.10)  # never risk more than 10% of balance on one trade
    return {
        "risk_reward": float(b),
        "kelly_fraction": float(kelly),
        "capped_fraction": float(capped),
        "recommended_risk_currency": float(balance * capped),
    }


def qgita_sweep(claim: str) -> Dict[str, any]:
    """Run the Kundalini/QGITA truth gate over a single claim."""
    try:
        from aureon_fusion import truth_gate
        if not truth_gate.gate_available():
            return {"available": False, "reason": "gate_unavailable"}
        result = truth_gate.check_claim(
            text=claim,
            provenance={"source": "strategic_trade_intelligence"},
        )
        return {
            "available": True,
            "verdict": result.get("verdict"),
            "confidence": result.get("confidence"),
            "blockers": result.get("blockers", []),
        }
    except Exception as e:
        return {"available": False, "reason": str(e)}


def analyze_trade(symbol: str, direction: str, entry: float, stop: float,
                  tp: float, balance_gbp: float,
                  watchlist: Optional[List[str]] = None) -> Dict[str, any]:
    """Full strategic intelligence report for one trade hypothesis."""
    watchlist = watchlist or ["EURUSD", "USDJPY", "GBPUSD", "GOLD", "OIL_CRUDE",
                              "SILVER", "NATURALGAS", "AAPL", "TSLA", "NVDA"]
    closes = load_recent_closes(symbol, days=14)
    returns = np.diff(np.log(closes)) if closes is not None else None
    spectrum = fourier_spectrum(closes)
    corr = cross_asset_correlations([s for s in watchlist if s in YAHOO_MAP], days=14)
    porter = porters_five_forces(symbol, corr, spectrum)
    swot = swot_analysis(symbol, returns, spectrum)
    alloc = capital_allocation(entry, stop, tp, balance_gbp)
    cash_cow = cash_cow_score(returns)
    harmonic = harmonic_lidar_map(closes)
    timeline = forecast_timeline(closes)
    roi = roi_forecast(entry, stop, tp)
    claim = f"{direction.upper()} {symbol} at {entry:.4f} with stop {stop:.4f} and target {tp:.4f}"
    qgita = qgita_sweep(claim)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "direction": direction,
        "entry": float(entry),
        "stop": float(stop),
        "tp": float(tp),
        "balance_gbp": float(balance_gbp),
        "fourier_spectrum": spectrum,
        "correlations": corr.get(symbol, {}),
        "porters_five_forces": porter,
        "swot": swot,
        "cash_cow": cash_cow,
        "harmonic_lidar": harmonic,
        "forecast_timeline": timeline,
        "roi_forecast": roi,
        "capital_allocation": alloc,
        "qgita_sweep": qgita,
    }

    ANALYSIS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(ANALYSIS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(report, default=str) + "\n")
    return report


# ─── CLI DEMO / MANUAL TEST (HARDCODED DEFAULTS — NOT LIVE DATA) ─────────────
if __name__ == "__main__":
    import sys
    sym = sys.argv[1] if len(sys.argv) > 1 else "TSLA"
    direction = sys.argv[2] if len(sys.argv) > 2 else "SELL"
    entry = float(sys.argv[3]) if len(sys.argv) > 3 else 354.0   # DEMO default
    stop = float(sys.argv[4]) if len(sys.argv) > 4 else 360.0    # DEMO default
    tp = float(sys.argv[5]) if len(sys.argv) > 5 else 350.0      # DEMO default
    balance = float(sys.argv[6]) if len(sys.argv) > 6 else 179.64  # DEMO default; pass real balance for live use
    r = analyze_trade(sym, direction, entry, stop, tp, balance)
    print(json.dumps(r, indent=2, default=str))
