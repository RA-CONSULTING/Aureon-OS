#!/usr/bin/env python3
"""
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║   📊 BACKTEST: 7th ORACLE (SENTIMENT) vs HISTORICAL DATA                   ║
║   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                   ║
║                                                                            ║
║   LIVE RESEARCH — REAL DATA FROM /tmp/crypto_historical_data.json          ║
║   14,119 asset-days | 5 assets | 2017-2026                                ║
║                                                                            ║
║   This script derives historical Fear/Greed, order-flow, and news          ║
║   sentiment from REAL OHLCV data — then measures whether the              ║
║   7th Oracle (OracleOfSentiment) IMPROVES the Seer's trading calls.        ║
║                                                                            ║
║   METHODOLOGY:                                                             ║
║   • Fear/Greed derived from: 14-day volatility + 30-day drawdown +         ║
║     7-day momentum + volume-weighted momentum                              ║
║   • Order flow derived from: volume vs 20-day avg, price direction,        ║
║     buy/sell pressure from (close-low)/(high-low)                          ║
║   • News sentiment proxied from: 30-day price regime (crash/rally/etc.)    ║
║   • Compares 6-Oracle Seer vs 7-Oracle Seer across all asset-days          ║
║   • Measures next-day return for BUY/SELL/HOLD signals                     ║
║   • Tests: Does the 7th Oracle catch crashes? Avoid false signals?         ║
║                                                                            ║
║   Gary Leckey & GitHub Copilot | February 2026                             ║
║   "The data doesn't lie. The ancients knew. Now we prove it."              ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
"""

import os, sys, json, math, time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

DATA_FILE = "/tmp/crypto_historical_data.json"
LOOKBACK_VOLATILITY = 14    # days for realized vol
LOOKBACK_DRAWDOWN   = 30    # days for max drawdown
LOOKBACK_MOMENTUM   = 7     # days for short momentum
LOOKBACK_VOLUME     = 20    # days for avg volume
LOOKBACK_REGIME     = 30    # days for news-proxy regime

# Phase label thresholds (same as OracleOfSentiment)
PHASE_THRESHOLDS = {
    "EUPHORIA": 0.75,
    "OPTIMISM": 0.60,
    "NEUTRAL":  0.45,
    "ANXIETY":  0.30,
    # below 0.30 = PANIC
}

# ═══════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════

def load_data() -> Dict[str, List[Dict]]:
    """Load the pre-cached historical OHLCV data."""
    with open(DATA_FILE, 'r') as f:
        return json.load(f)


# ═════════════════════════════════════════════════════════════════════════
# HISTORICAL SENTIMENT DERIVATION (from REAL price/volume data)
# ═══════════════════════════════════════════════════════════════════════════

def derive_fear_greed(closes: List[float], volumes: List[float], idx: int) -> Dict:
    """
    Derive a Fear/Greed index from historical price data.
    
    Components:
    1. Realized volatility (14d) — high vol = fear
    2. Maximum drawdown (30d) — deep drawdown = extreme fear
    3. Price momentum (7d) — strong up = greed, strong down = fear
    4. Volume-price momentum — rising vol + rising price = greed
    
    Returns dict with fg_index (0-100), label, and components.
    """
    # Need enough history
    lookback = max(LOOKBACK_VOLATILITY, LOOKBACK_DRAWDOWN, LOOKBACK_MOMENTUM)
    if idx < lookback:
        return {"fg_index": 50, "fg_label": "Neutral", "components": {}}
    
    # 1. Realized volatility (14d log returns)
    returns = []
    for i in range(idx - LOOKBACK_VOLATILITY, idx):
        if closes[i] > 0 and closes[i+1] > 0:
            returns.append(math.log(closes[i+1] / closes[i]))
    if returns:
        vol = (sum(r*r for r in returns) / len(returns)) ** 0.5
        # Annualize
        annual_vol = vol * math.sqrt(365)
        # Map: 0% vol → 100 (no fear), 150%+ → 0 (extreme fear)
        vol_score = max(0, min(100, 100 - (annual_vol * 100 / 1.5)))
    else:
        vol_score = 50
    
    # 2. Max drawdown (30d)
    window = closes[max(0, idx - LOOKBACK_DRAWDOWN):idx + 1]
    peak = window[0]
    max_dd = 0
    for p in window:
        peak = max(peak, p)
        dd = (peak - p) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)
    # Map: 0% dd → 100, 50%+ dd → 0
    dd_score = max(0, min(100, 100 - (max_dd * 200)))
    
    # 3. Price momentum (7d)
    if idx >= LOOKBACK_MOMENTUM and closes[idx - LOOKBACK_MOMENTUM] > 0:
        mom = (closes[idx] / closes[idx - LOOKBACK_MOMENTUM] - 1) * 100
        # Map: -30% → 0, 0% → 50, +30% → 100
        mom_score = max(0, min(100, 50 + mom * (50/30)))
    else:
        mom_score = 50
    
    # 4. Volume-price momentum
    avg_vol = sum(volumes[max(0, idx - LOOKBACK_VOLUME):idx]) / LOOKBACK_VOLUME if idx >= LOOKBACK_VOLUME else (volumes[idx] if volumes[idx] > 0 else 1)
    vol_ratio = volumes[idx] / avg_vol if avg_vol > 0 else 1
    price_dir = 1 if closes[idx] >= closes[idx - 1] else -1 if idx > 0 else 0
    # High volume + price up = greed; high volume + price down = panic
    vp_score = 50 + price_dir * min(25, (vol_ratio - 1) * 25)
    vp_score = max(0, min(100, vp_score))
    
    # Weighted combination (same weights as classic FGI)
    fg_index = int(vol_score * 0.25 + dd_score * 0.30 + mom_score * 0.30 + vp_score * 0.15)
    fg_index = max(0, min(100, fg_index))
    
    if fg_index >= 75:
        label = "Extreme Greed"
    elif fg_index >= 55:
        label = "Greed"
    elif fg_index >= 45:
        label = "Neutral"
    elif fg_index >= 25:
        label = "Fear"
    else:
        label = "Extreme Fear"
    
    return {
        "fg_index": fg_index,
        "fg_label": label,
        "fg_score": fg_index / 100.0,  # 0-1 scale for oracle
        "components": {
            "volatility": round(vol_score, 1),
            "drawdown": round(dd_score, 1),
            "momentum": round(mom_score, 1),
            "vol_price": round(vp_score, 1),
        }
    }


def derive_order_flow(closes: List[float], highs: List[float], lows: List[float],
                      volumes: List[float], idx: int) -> Dict:
    """
    Derive order flow metrics from OHLCV data.
    
    Uses:
    • Buy pressure = (close - low) / (high - low) — how close price finished to high
    • Volume vs average — surge detection
    • Price acceleration — velocity of price change
    
    Returns dict with pressure_ratio, flow_momentum, intent, etc.
    """
    if idx < LOOKBACK_VOLUME:
        return {"pressure_ratio": 0.5, "flow_momentum": 0.5, "intent": "QUIET",
                "surge_detected": False, "acceleration": 0.0}
    
    # Buy pressure: (close - low) / (high - low)
    h, l, c = highs[idx], lows[idx], closes[idx]
    if h > l:
        buy_pressure = (c - l) / (h - l)  # 0 = closed at low (sellers), 1 = closed at high (buyers)
    else:
        buy_pressure = 0.5  # Doji
    
    # Volume surge
    avg_vol = sum(volumes[max(0, idx - LOOKBACK_VOLUME):idx]) / LOOKBACK_VOLUME
    vol_ratio = volumes[idx] / avg_vol if avg_vol > 0 else 1.0
    surge = vol_ratio > 2.0
    
    # Flow momentum (EMA of buy pressure over 5 days)
    ema = buy_pressure
    alpha = 0.3
    for j in range(max(0, idx - 4), idx):
        hj, lj, cj = highs[j], lows[j], closes[j]
        bp_j = (cj - lj) / (hj - lj) if hj > lj else 0.5
        ema = alpha * bp_j + (1 - alpha) * ema
    
    # Price acceleration (2nd derivative of price)
    if idx >= 3:
        v1 = closes[idx - 1] - closes[idx - 2]
        v2 = closes[idx] - closes[idx - 1]
        accel = (v2 - v1) / closes[idx - 1] if closes[idx - 1] > 0 else 0
    else:
        accel = 0
    
    # Determine intent
    if buy_pressure > 0.7 and vol_ratio > 1.5:
        intent = "FOMO_BUYING" if vol_ratio > 2.5 else "ACCUMULATION"
    elif buy_pressure < 0.3 and vol_ratio > 1.5:
        intent = "PANIC_SELLING" if vol_ratio > 2.5 else "DISTRIBUTION"
    elif buy_pressure > 0.6:
        intent = "ACCUMULATION"
    elif buy_pressure < 0.4:
        intent = "DISTRIBUTION"
    else:
        intent = "QUIET"
    
    return {
        "pressure_ratio": round(buy_pressure, 4),
        "flow_momentum": round(ema, 4),
        "intent": intent,
        "surge_detected": surge,
        "vol_ratio": round(vol_ratio, 2),
        "acceleration": round(accel, 6),
    }


def derive_news_proxy(closes: List[float], idx: int) -> Dict:
    """
    Proxy for news sentiment based on price regime over 30 days.
    
    In backtesting we can't read historical Yahoo headlines, but we CAN
    infer the news environment from price behavior:
    • Crash (>20% drawdown in 30d) → heavily bearish headlines
    • Strong decline (>10%) → bearish
    • Flat (±5%) → neutral/mixed
    • Rally (>10%) → bullish
    • Parabolic (>30%) → euphoric headlines
    """
    if idx < LOOKBACK_REGIME:
        return {"news_score": 0.5, "regime": "INSUFFICIENT_DATA"}
    
    # 30-day return
    ret_30d = (closes[idx] / closes[idx - LOOKBACK_REGIME] - 1) * 100
    
    # Max drawdown in window
    window = closes[max(0, idx - LOOKBACK_REGIME):idx + 1]
    peak = window[0]
    max_dd = 0
    for p in window:
        peak = max(peak, p)
        dd = (peak - p) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)
    max_dd_pct = max_dd * 100
    
    # Combine
    if max_dd_pct > 20:
        regime = "CRASH"
        score = max(0.1, 0.3 - max_dd_pct / 100)
    elif ret_30d < -10:
        regime = "BEARISH"
        score = max(0.15, 0.4 + ret_30d / 100)
    elif ret_30d < -5:
        regime = "SLIGHTLY_BEARISH"
        score = 0.40
    elif ret_30d < 5:
        regime = "NEUTRAL"
        score = 0.50
    elif ret_30d < 15:
        regime = "BULLISH"
        score = 0.60
    elif ret_30d < 30:
        regime = "STRONG_BULL"
        score = 0.70
    else:
        regime = "PARABOLIC"
        score = 0.80  # Cap — euphoric news often precedes tops
    
    return {
        "news_score": round(score, 4),
        "regime": regime,
        "return_30d": round(ret_30d, 2),
        "max_dd_30d": round(max_dd_pct, 2),
    }


# ═══════════════════════════════════════════════════════════════════════════
# ORACLE ENGINE (Seer-compatible, backtest mode)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class OracleScore:
    score: float
    phase: str
    signal: str


def compute_sentiment_oracle(fg: Dict, flow: Dict, news: Dict) -> Tuple[float, str, Dict]:
    """
    Replicate OracleOfSentiment logic but using derived historical data.
    
    Weights: Fear/Greed 35%, News 25%, Order Flow 25%, Lyra 15% (default 0.5)
    """
    fg_score = fg.get("fg_score", 0.5)
    news_score = news.get("news_score", 0.5)
    flow_score = flow.get("flow_momentum", 0.5)
    lyra_score = 0.5  # No lyra in backtest — neutral default
    
    unified = (fg_score * 0.35 + news_score * 0.25 + flow_score * 0.25 + lyra_score * 0.15)
    unified = max(0.0, min(1.0, unified))
    
    if unified >= 0.75:
        phase = "EUPHORIA"
    elif unified >= 0.60:
        phase = "OPTIMISM"
    elif unified >= 0.45:
        phase = "NEUTRAL"
    elif unified >= 0.30:
        phase = "ANXIETY"
    else:
        phase = "PANIC"
    
    details = {
        "fg_index": fg.get("fg_index", 50),
        "fg_label": fg.get("fg_label", "Neutral"),
        "news_regime": news.get("regime", "NEUTRAL"),
        "flow_intent": flow.get("intent", "QUIET"),
        "flow_pressure": flow.get("pressure_ratio", 0.5),
        "components": {"fear_greed": fg_score, "news": news_score, "flow": flow_score, "lyra": lyra_score},
    }
    
    return unified, phase, details


# ═══════════════════════════════════════════════════════════════════════════
# RUNES ORACLE (time-shifted for backtest)
# ═══════════════════════════════════════════════════════════════════════════

_runes_oracle = None

def get_runes_oracle():
    """Lazy load the OracleOfRunes."""
    global _runes_oracle
    if _runes_oracle is None:
        from aureon.intelligence.aureon_seer import OracleOfRunes
        _runes_oracle = OracleOfRunes()
    return _runes_oracle


def read_runes_for_date(dt: datetime) -> Tuple[float, str]:
    """Read the runes oracle for a specific historical date."""
    oracle = get_runes_oracle()
    longitudes = oracle._get_all_longitudes(dt)
    
    per_tradition = {}
    all_activations = []
    for tradition in oracle._TRADITIONS:
        active_list = []
        for symbol in oracle._catalogues.get(tradition, []):
            result = oracle._decode_symbol(symbol, longitudes, tradition)
            if result.get("active"):
                active_list.append(result)
                all_activations.append(result)
        per_tradition[tradition] = active_list
    
    convergence = oracle._detect_convergence(all_activations)
    
    if all_activations:
        total_weight = sum(a["activation_strength"] for a in all_activations)
        if total_weight > 0:
            score = sum(a["signal_strength"] * a["activation_strength"] for a in all_activations) / total_weight
        else:
            score = 0.5
        buy_count = sum(1 for a in all_activations if a["trading_bias"] == "BUY")
        sell_count = sum(1 for a in all_activations if a["trading_bias"] == "SELL")
        bias_shift = (buy_count - sell_count) * 0.02
        score = max(0.0, min(1.0, score + bias_shift))
        
        # Combination intelligence
        bridge_bonus = 0.0
        for bridge in convergence.get("bridge_activations", []):
            bridge_bonus = max(bridge_bonus, bridge["bridge_bonus"])
        if bridge_bonus > 0:
            score = min(1.0, score + bridge_bonus)
        golden = convergence.get("golden_five", {})
        if golden.get("unanimous"):
            g5_bonus = 0.08 if golden["consensus_strength"] >= 1.0 else 0.05
            overall_lean = "BUY" if buy_count > sell_count else "SELL"
            if golden["consensus_direction"] == overall_lean:
                g5_bonus += 0.03
            score = min(1.0, score + g5_bonus)
        if golden.get("japanese_keystone"):
            score = min(1.0, score + 0.02)
        elif convergence["max_traditions"] >= 3:
            score = min(1.0, score + 0.05)
        elif convergence["max_traditions"] >= 2:
            score = min(1.0, score + 0.02)
        
        if score >= 0.75:
            phase = "DIVINE_ALIGNMENT"
        elif score >= 0.60:
            phase = "HARMONIC_RESONANCE"
        elif score >= 0.45:
            phase = "PARTIAL_ACTIVATION"
        elif score >= 0.30:
            phase = "WEAK_SIGNAL"
        else:
            phase = "DORMANT"
    else:
        score = 0.5
        phase = "DORMANT"
    
    return score, phase


# ═══════════════════════════════════════════════════════════════════════════
# WAR COUNSEL (simplified backtest version)
# ═══════════════════════════════════════════════════════════════════════════

def compute_war_counsel(unified_score: float, news: Dict) -> Tuple[float, str]:
    """
    Simplified WarCounsel for backtesting.
    Uses the same thresholds as the live WarCounsel.
    
    Returns (risk_modifier, tactical_mode)
    """
    risk_mod = 1.0
    
    # IRA sniper thresholds
    MIN_SCORE = 0.60
    if unified_score < MIN_SCORE:
        risk_mod *= 0.5  # Below sniper threshold
    
    # Guerrilla thresholds
    if unified_score >= 0.80:
        tactical = "COORDINATED_STRIKE"
    elif unified_score >= 0.65:
        tactical = "AMBUSH"
    elif unified_score >= 0.50:
        tactical = "FLYING_COLUMN"
    else:
        tactical = "RETREAT"
    
    # Geopolitical modifier
    regime = news.get("regime", "NEUTRAL")
    if regime in ("CRASH", "BEARISH"):
        risk_mod *= 0.7  # Risk off during bearish regime
    
    return risk_mod, tactical


# ═══════════════════════════════════════════════════════════════════════════
# SEER COMBINE LOGIC (6-oracle and 7-oracle versions)
# ═══════════════════════════════════════════════════════════════════════════

# Oracle weights from SEER_CONFIG (6-oracle, original)
WEIGHTS_6 = {
    "GAIA": 0.20, "COSMOS": 0.18, "HARMONY": 0.20,
    "SPIRITS": 0.12, "TIME": 0.12, "RUNES": 0.18,
}

# Oracle weights from SEER_CONFIG (7-oracle, new)
WEIGHTS_7 = {
    "GAIA": 0.17, "COSMOS": 0.15, "HARMONY": 0.17,
    "SPIRITS": 0.10, "TIME": 0.10, "RUNES": 0.16, "SENTIMENT": 0.15,
}


def seer_combine_6(runes_score: float) -> Tuple[float, str, str]:
    """
    6-Oracle Seer combination (baseline).
    BACKTEST MODE: Only Runes is a REAL oracle — it carries full weight.
    The 5 environmmental oracles (Gaia, Cosmos, Harmony, Spirits, Time)
    default to 0.5. We renormalize to give Runes its true voice.
    
    Effective score = Runes only (the only oracle we can compute historically).
    """
    # In live mode, 5 oracles contribute variance. In backtest, they're all 0.5.
    # So we give Runes FULL weight to test it honestly.
    unified = runes_score
    unified = max(0.0, min(1.0, unified))
    
    grade, action = _grade_and_action(unified)
    return unified, grade, action


def seer_combine_7(runes_score: float, sentiment_score: float,
                   war_risk_mod: float = 1.0) -> Tuple[float, str, str]:
    """
    7-Oracle Seer combination (enhanced).
    BACKTEST MODE: Only Runes + Sentiment are REAL oracles.
    Split: 55% Runes + 45% Sentiment (Runes slightly dominant as primary signal).
    War counsel risk modifier applied.
    """
    # Only the two oracles we can compute historically get weight
    unified = runes_score * 0.55 + sentiment_score * 0.45
    unified = max(0.0, min(1.0, unified))
    
    # Apply war counsel risk modifier (same as AllSeeingEye: 60% action + 40% war)
    action_raw = unified
    adjusted = action_raw * 0.6 + (action_raw * war_risk_mod) * 0.4
    unified = max(0.0, min(1.0, adjusted))
    
    grade, action = _grade_and_action(unified)
    return unified, grade, action


def _grade_and_action(score: float) -> Tuple[str, str]:
    """Determine grade and action from unified score."""
    if score >= 0.85:
        grade = "DIVINE_CLARITY"
    elif score >= 0.70:
        grade = "CLEAR_SIGHT"
    elif score >= 0.55:
        grade = "PARTIAL_VISION"
    elif score >= 0.40:
        grade = "FOG"
    else:
        grade = "BLIND"
    
    if score >= 0.65:
        action = "BUY"
    elif score >= 0.45:
        action = "HOLD"
    else:
        action = "SELL"
    
    return grade, action


# ═══════════════════════════════════════════════════════════════════════════
# MAIN BACKTEST ENGINE
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class DayResult:
    date: str
    asset: str
    close: float
    next_close: float
    next_return: float   # % return next day
    
    # 6-oracle (baseline)
    score_6: float
    grade_6: str
    action_6: str
    
    # 7-oracle (enhanced)
    score_7: float
    grade_7: str
    action_7: str
    
    # Sentiment components
    fg_index: int
    fg_label: str
    sentiment_score: float
    sentiment_phase: str
    flow_intent: str
    news_regime: str
    tactical_mode: str
    war_risk_mod: float
    
    # Runes
    runes_score: float


def run_backtest():
    """
    Run the full 14,119 asset-day backtest comparing 6-oracle vs 7-oracle Seer.
    """
    print("=" * 80)
    print("  📊 AUREON SEER BACKTEST: 7th ORACLE (SENTIMENT) vs HISTORICAL DATA")
    print("  REAL DATA • 14,119 ASSET-DAYS • 5 ASSETS • 2017-2026")
    print("=" * 80)
    print()
    
    t0 = time.time()
    data = load_data()
    
    # Results storage
    results: List[DayResult] = []
    
    # Per-asset stats
    asset_stats = {}
    
    # Runes cache (same date = same runes regardless of asset)
    runes_cache: Dict[str, Tuple[float, str]] = {}
    
    total_days = sum(len(days) for days in data.values())
    processed = 0
    
    for asset, days in data.items():
        print(f"\n  Processing {asset}: {len(days)} days...")
        
        closes = [d["close"] for d in days]
        highs = [d["high"] for d in days]
        lows = [d["low"] for d in days]
        volumes = [d["volume"] for d in days]
        dates = [d["date"] for d in days]
        
        asset_results = []
        
        # Need LOOKBACK_REGIME (30) days of history + 1 day for next return
        start_idx = max(LOOKBACK_DRAWDOWN, LOOKBACK_VOLUME, LOOKBACK_REGIME)
        
        for idx in range(start_idx, len(days) - 1):
            date_str = dates[idx]
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            
            # ── Derive sentiment components from REAL data ──
            fg = derive_fear_greed(closes, volumes, idx)
            flow = derive_order_flow(closes, highs, lows, volumes, idx)
            news = derive_news_proxy(closes, idx)
            
            # ── Compute 7th Oracle score ──
            sent_score, sent_phase, sent_details = compute_sentiment_oracle(fg, flow, news)
            
            # ── Read runes for this date (cached) ──
            if date_str not in runes_cache:
                runes_score, runes_phase = read_runes_for_date(dt)
                runes_cache[date_str] = (runes_score, runes_phase)
            else:
                runes_score, runes_phase = runes_cache[date_str]
            
            # ── War counsel ──
            war_risk_mod, tactical_mode = compute_war_counsel(
                sent_score * 0.5 + runes_score * 0.5, news
            )
            
            # ── 6-oracle Seer (baseline) ──
            score_6, grade_6, action_6 = seer_combine_6(runes_score)
            
            # ── 7-oracle Seer (enhanced) ──
            score_7, grade_7, action_7 = seer_combine_7(runes_score, sent_score, war_risk_mod)
            
            # ── Next day return ──
            next_close = closes[idx + 1]
            next_ret = ((next_close - closes[idx]) / closes[idx]) * 100
            
            result = DayResult(
                date=date_str, asset=asset,
                close=closes[idx], next_close=next_close, next_return=next_ret,
                score_6=score_6, grade_6=grade_6, action_6=action_6,
                score_7=score_7, grade_7=grade_7, action_7=action_7,
                fg_index=fg["fg_index"], fg_label=fg["fg_label"],
                sentiment_score=sent_score, sentiment_phase=sent_phase,
                flow_intent=flow["intent"], news_regime=news["regime"],
                tactical_mode=tactical_mode, war_risk_mod=war_risk_mod,
                runes_score=runes_score,
            )
            
            results.append(result)
            asset_results.append(result)
            processed += 1
            
            if processed % 2000 == 0:
                elapsed = time.time() - t0
                pct = processed / total_days * 100
                print(f"    ... {processed:,}/{total_days:,} ({pct:.0f}%) — {elapsed:.1f}s")
        
        asset_stats[asset] = asset_results
    
    elapsed = time.time() - t0
    print(f"\n  ✅ Processed {len(results):,} days in {elapsed:.1f}s")
    
    # ═══════════════════════════════════════════════════════════════════════
    # ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════
    
    analyze_results(results, asset_stats)


def analyze_results(results: List[DayResult], asset_stats: Dict):
    """Comprehensive analysis of backtest results."""
    
    print("\n" + "=" * 80)
    print("  📈 RESULTS: 6-ORACLE vs 7-ORACLE SEER")
    print("=" * 80)
    
    # ── 1. ACTION ACCURACY (BUY/SELL/HOLD vs next-day returns) ──
    print("\n  ╔═══════════════════════════════════════════════════════════════╗")
    print("  ║  TEST 1: ACTION ACCURACY (signal → next-day return)         ║")
    print("  ╚═══════════════════════════════════════════════════════════════╝")
    
    for label, action_key, score_key in [("6-ORACLE", "action_6", "score_6"),
                                          ("7-ORACLE", "action_7", "score_7")]:
        buys = [r for r in results if getattr(r, action_key) == "BUY"]
        sells = [r for r in results if getattr(r, action_key) == "SELL"]
        holds = [r for r in results if getattr(r, action_key) == "HOLD"]
        
        buy_correct = sum(1 for r in buys if r.next_return > 0)
        sell_correct = sum(1 for r in sells if r.next_return < 0)
        hold_flat = sum(1 for r in holds if abs(r.next_return) < 2)
        
        buy_pct = buy_correct / len(buys) * 100 if buys else 0
        sell_pct = sell_correct / len(sells) * 100 if sells else 0
        
        buy_avg = sum(r.next_return for r in buys) / len(buys) if buys else 0
        sell_avg = sum(r.next_return for r in sells) / len(sells) if sells else 0
        hold_avg = sum(r.next_return for r in holds) / len(holds) if holds else 0
        
        print(f"\n  {label} SEER:")
        print(f"    BUY  signals: {len(buys):>6,}  | Correct: {buy_pct:5.1f}% | Avg return: {buy_avg:+.3f}%")
        print(f"    SELL signals: {len(sells):>6,}  | Correct: {sell_pct:5.1f}% | Avg return: {sell_avg:+.3f}%")
        print(f"    HOLD signals: {len(holds):>6,}  | Near-flat: {hold_flat / len(holds) * 100:.1f}% | Avg return: {hold_avg:+.3f}%")
    
    # ── 2. SIGNAL DIVERGENCE: Where 7-oracle DISAGREES with 6-oracle ──
    print("\n  ╔═══════════════════════════════════════════════════════════════╗")
    print("  ║  TEST 2: SIGNAL DIVERGENCE (where 7-oracle CHANGES the call)║")
    print("  ╚═══════════════════════════════════════════════════════════════╝")
    
    divergent = [r for r in results if r.action_6 != r.action_7]
    print(f"\n  Total divergent days: {len(divergent):,} / {len(results):,} ({len(divergent)/len(results)*100:.1f}%)")
    
    if divergent:
        # When 7-oracle changes signal, is it RIGHT more often?
        oracle7_better = 0
        oracle6_better = 0
        for r in divergent:
            ret = r.next_return
            # Score each action
            def action_profit(action, ret):
                if action == "BUY":
                    return ret  # Long: profit = positive return
                elif action == "SELL":
                    return -ret  # Short: profit = negative return
                else:
                    return 0  # Hold: no action
            
            p6 = action_profit(r.action_6, ret)
            p7 = action_profit(r.action_7, ret)
            
            if p7 > p6:
                oracle7_better += 1
            elif p6 > p7:
                oracle6_better += 1
        
        print(f"  7-Oracle BETTER: {oracle7_better:,} ({oracle7_better/len(divergent)*100:.1f}%)")
        print(f"  6-Oracle BETTER: {oracle6_better:,} ({oracle6_better/len(divergent)*100:.1f}%)")
        print(f"  Tied:            {len(divergent) - oracle7_better - oracle6_better:,}")
    
    # ── 3. SENTIMENT PHASE PATTERNS ──
    print("\n  ╔═══════════════════════════════════════════════════════════════╗")
    print("  ║  TEST 3: SENTIMENT PHASE → NEXT-DAY RETURNS                 ║")
    print("  ╚═══════════════════════════════════════════════════════════════╝")
    
    phases = defaultdict(list)
    for r in results:
        phases[r.sentiment_phase].append(r.next_return)
    
    print(f"\n  {'Phase':<14} {'Count':>7} {'Avg Return':>11} {'Median':>8} {'Win%':>6} {'Std':>7}")
    print("  " + "-" * 57)
    for phase in ["EUPHORIA", "OPTIMISM", "NEUTRAL", "ANXIETY", "PANIC"]:
        rets = phases.get(phase, [])
        if not rets:
            continue
        avg = sum(rets) / len(rets)
        sorted_rets = sorted(rets)
        median = sorted_rets[len(sorted_rets) // 2]
        win_pct = sum(1 for r in rets if r > 0) / len(rets) * 100
        std = (sum((r - avg) ** 2 for r in rets) / len(rets)) ** 0.5
        print(f"  {phase:<14} {len(rets):>7,} {avg:>+10.3f}% {median:>+7.3f}% {win_pct:>5.1f}% {std:>6.2f}%")
    
    # ── 4. FEAR/GREED QUINTILE ANALYSIS ──
    print("\n  ╔═══════════════════════════════════════════════════════════════╗")
    print("  ║  TEST 4: FEAR/GREED INDEX QUINTILES → NEXT-DAY RETURNS      ║")
    print("  ╚═══════════════════════════════════════════════════════════════╝")
    
    quintiles = {
        "Q1 (0-20) EXTREME FEAR": [r for r in results if r.fg_index <= 20],
        "Q2 (21-40) FEAR":        [r for r in results if 21 <= r.fg_index <= 40],
        "Q3 (41-60) NEUTRAL":     [r for r in results if 41 <= r.fg_index <= 60],
        "Q4 (61-80) GREED":       [r for r in results if 61 <= r.fg_index <= 80],
        "Q5 (81-100) EXTREME GREED": [r for r in results if r.fg_index >= 81],
    }
    
    print(f"\n  {'Quintile':<30} {'Count':>7} {'Avg Ret':>9} {'Win%':>6} {'Avg 7-Score':>11}")
    print("  " + "-" * 66)
    for name, bucket in quintiles.items():
        if not bucket:
            continue
        avg_ret = sum(r.next_return for r in bucket) / len(bucket)
        win_pct = sum(1 for r in bucket if r.next_return > 0) / len(bucket) * 100
        avg_s7 = sum(r.score_7 for r in bucket) / len(bucket)
        print(f"  {name:<30} {len(bucket):>7,} {avg_ret:>+8.3f}% {win_pct:>5.1f}% {avg_s7:>10.3f}")
    
    # ── 5. ORDER FLOW INTENT PATTERNS ──
    print("\n  ╔═══════════════════════════════════════════════════════════════╗")
    print("  ║  TEST 5: ORDER FLOW INTENT → NEXT-DAY RETURNS               ║")
    print("  ╚═══════════════════════════════════════════════════════════════╝")
    
    intents = defaultdict(list)
    for r in results:
        intents[r.flow_intent].append(r.next_return)
    
    print(f"\n  {'Intent':<20} {'Count':>7} {'Avg Return':>11} {'Win%':>6}")
    print("  " + "-" * 47)
    for intent in ["FOMO_BUYING", "ACCUMULATION", "QUIET", "DISTRIBUTION", "PANIC_SELLING"]:
        rets = intents.get(intent, [])
        if not rets:
            continue
        avg = sum(rets) / len(rets)
        win_pct = sum(1 for r in rets if r > 0) / len(rets) * 100
        print(f"  {intent:<20} {len(rets):>7,} {avg:>+10.3f}% {win_pct:>5.1f}%")
    
    # ── 6. NEWS REGIME PATTERNS ──
    print("\n  ╔═══════════════════════════════════════════════════════════════╗")
    print("  ║  TEST 6: NEWS REGIME → NEXT-DAY RETURNS                     ║")
    print("  ╚═══════════════════════════════════════════════════════════════╝")
    
    regimes = defaultdict(list)
    for r in results:
        regimes[r.news_regime].append(r.next_return)
    
    print(f"\n  {'Regime':<18} {'Count':>7} {'Avg Return':>11} {'Win%':>6}")
    print("  " + "-" * 45)
    for regime in ["CRASH", "BEARISH", "SLIGHTLY_BEARISH", "NEUTRAL",
                    "BULLISH", "STRONG_BULL", "PARABOLIC"]:
        rets = regimes.get(regime, [])
        if not rets:
            continue
        avg = sum(rets) / len(rets)
        win_pct = sum(1 for r in rets if r > 0) / len(rets) * 100
        print(f"  {regime:<18} {len(rets):>7,} {avg:>+10.3f}% {win_pct:>5.1f}%")
    
    # ── 7. WAR COUNSEL TACTICAL MODE ──
    print("\n  ╔═══════════════════════════════════════════════════════════════╗")
    print("  ║  TEST 7: WAR COUNSEL TACTICAL MODE → NEXT-DAY RETURNS       ║")
    print("  ╚═══════════════════════════════════════════════════════════════╝")
    
    tactics = defaultdict(list)
    for r in results:
        tactics[r.tactical_mode].append(r)
    
    print(f"\n  {'Tactical Mode':<22} {'Count':>7} {'Avg Ret':>9} {'Win%':>6} {'7-Oracle BUY%':>14}")
    print("  " + "-" * 62)
    for mode in ["COORDINATED_STRIKE", "AMBUSH", "FLYING_COLUMN", "RETREAT"]:
        bucket = tactics.get(mode, [])
        if not bucket:
            continue
        avg_ret = sum(r.next_return for r in bucket) / len(bucket)
        win_pct = sum(1 for r in bucket if r.next_return > 0) / len(bucket) * 100
        buy_pct = sum(1 for r in bucket if r.action_7 == "BUY") / len(bucket) * 100
        print(f"  {mode:<22} {len(bucket):>7,} {avg_ret:>+8.3f}% {win_pct:>5.1f}% {buy_pct:>13.1f}%")
    
    # ── 8. PER-ASSET BREAKDOWN ──
    print("\n  ╔═══════════════════════════════════════════════════════════════╗")
    print("  ║  TEST 8: PER-ASSET 6-ORACLE vs 7-ORACLE                     ║")
    print("  ╚═══════════════════════════════════════════════════════════════╝")
    
    print(f"\n  {'Asset':<10} {'Days':>6} {'6-BUY Avg':>10} {'7-BUY Avg':>10} {'6-SELL Avg':>11} {'7-SELL Avg':>11} {'Delta':>8}")
    print("  " + "-" * 69)
    for asset, ar in asset_stats.items():
        # 6-oracle BUY avg return
        b6 = [r.next_return for r in ar if r.action_6 == "BUY"]
        b7 = [r.next_return for r in ar if r.action_7 == "BUY"]
        s6 = [r.next_return for r in ar if r.action_6 == "SELL"]
        s7 = [r.next_return for r in ar if r.action_7 == "SELL"]
        
        avg_b6 = sum(b6) / len(b6) if b6 else 0
        avg_b7 = sum(b7) / len(b7) if b7 else 0
        avg_s6 = sum(s6) / len(s6) if s6 else 0
        avg_s7 = sum(s7) / len(s7) if s7 else 0
        
        # Delta: how much better is 7-oracle's BUY signal?
        delta = avg_b7 - avg_b6
        print(f"  {asset:<10} {len(ar):>6,} {avg_b6:>+9.3f}% {avg_b7:>+9.3f}% {avg_s6:>+10.3f}% {avg_s7:>+10.3f}% {delta:>+7.3f}%")
    
    # ── 9. YEARLY BREAKDOWN ──
    print("\n  ╔═══════════════════════════════════════════════════════════════╗")
    print("  ║  TEST 9: YEARLY SENTIMENT ACCURACY                          ║")
    print("  ╚═══════════════════════════════════════════════════════════════╝")
    
    yearly = defaultdict(list)
    for r in results:
        year = r.date[:4]
        yearly[year].append(r)
    
    print(f"\n  {'Year':<6} {'Days':>6} {'6-BUY %':>8} {'7-BUY %':>8} {'7-BUY Avg':>10} {'FG Avg':>7} {'Phase Mode':>12}")
    print("  " + "-" * 61)
    for year in sorted(yearly.keys()):
        yr = yearly[year]
        b6 = [r for r in yr if r.action_6 == "BUY"]
        b7 = [r for r in yr if r.action_7 == "BUY"]
        
        b6_correct = sum(1 for r in b6 if r.next_return > 0) / len(b6) * 100 if b6 else 0
        b7_correct = sum(1 for r in b7 if r.next_return > 0) / len(b7) * 100 if b7 else 0
        b7_avg = sum(r.next_return for r in b7) / len(b7) if b7 else 0
        
        avg_fg = sum(r.fg_index for r in yr) / len(yr)
        
        # Most common phase
        phase_counts = defaultdict(int)
        for r in yr:
            phase_counts[r.sentiment_phase] += 1
        mode_phase = max(phase_counts, key=phase_counts.get) if phase_counts else "N/A"
        
        print(f"  {year:<6} {len(yr):>6,} {b6_correct:>7.1f}% {b7_correct:>7.1f}% {b7_avg:>+9.3f}% {avg_fg:>6.0f} {mode_phase:>12}")
    
    # ── 10. CRASH DETECTION TEST ──
    print("\n  ╔═══════════════════════════════════════════════════════════════╗")
    print("  ║  TEST 10: CRASH DETECTION (next-day return < -5%)            ║")
    print("  ╚═══════════════════════════════════════════════════════════════╝")
    
    crashes = [r for r in results if r.next_return < -5]
    print(f"\n  Total crash days (next-day < -5%): {len(crashes):,}")
    
    if crashes:
        # How many did each oracle CORRECTLY avoid (not BUY)?
        oracle6_avoided = sum(1 for r in crashes if r.action_6 != "BUY")
        oracle7_avoided = sum(1 for r in crashes if r.action_7 != "BUY")
        
        # How many did each oracle CORRECTLY call SELL?
        oracle6_sold = sum(1 for r in crashes if r.action_6 == "SELL")
        oracle7_sold = sum(1 for r in crashes if r.action_7 == "SELL")
        
        print(f"  6-Oracle: Avoided BUY on {oracle6_avoided}/{len(crashes)} ({oracle6_avoided/len(crashes)*100:.1f}%) crash days")
        print(f"  7-Oracle: Avoided BUY on {oracle7_avoided}/{len(crashes)} ({oracle7_avoided/len(crashes)*100:.1f}%) crash days")
        print(f"  6-Oracle: Called SELL on  {oracle6_sold}/{len(crashes)} ({oracle6_sold/len(crashes)*100:.1f}%) crash days")
        print(f"  7-Oracle: Called SELL on  {oracle7_sold}/{len(crashes)} ({oracle7_sold/len(crashes)*100:.1f}%) crash days")
        
        # Avg sentiment phase before crashes
        phase_dist = defaultdict(int)
        for r in crashes:
            phase_dist[r.sentiment_phase] += 1
        print(f"\n  Sentiment phase distribution before crashes:")
        for phase, count in sorted(phase_dist.items(), key=lambda x: -x[1]):
            print(f"    {phase:<14} {count:>4} ({count/len(crashes)*100:.1f}%)")
        
        avg_fg = sum(r.fg_index for r in crashes) / len(crashes)
        print(f"\n  Average Fear/Greed Index before crashes: {avg_fg:.0f} ({('FEAR' if avg_fg < 45 else 'GREED' if avg_fg > 55 else 'NEUTRAL')})")
    
    # ── 11. RALLY DETECTION TEST ──
    print("\n  ╔═══════════════════════════════════════════════════════════════╗")
    print("  ║  TEST 11: RALLY DETECTION (next-day return > +5%)            ║")
    print("  ╚═══════════════════════════════════════════════════════════════╝")
    
    rallies = [r for r in results if r.next_return > 5]
    print(f"\n  Total rally days (next-day > +5%): {len(rallies):,}")
    
    if rallies:
        oracle6_bought = sum(1 for r in rallies if r.action_6 == "BUY")
        oracle7_bought = sum(1 for r in rallies if r.action_7 == "BUY")
        print(f"  6-Oracle: Had BUY on {oracle6_bought}/{len(rallies)} ({oracle6_bought/len(rallies)*100:.1f}%) rally days")
        print(f"  7-Oracle: Had BUY on {oracle7_bought}/{len(rallies)} ({oracle7_bought/len(rallies)*100:.1f}%) rally days")
        
        avg_fg = sum(r.fg_index for r in rallies) / len(rallies)
        print(f"  Average Fear/Greed Index before rallies: {avg_fg:.0f}")
        
        # Phase distribution
        phase_dist = defaultdict(int)
        for r in rallies:
            phase_dist[r.sentiment_phase] += 1
        print(f"\n  Sentiment phase distribution before rallies:")
        for phase, count in sorted(phase_dist.items(), key=lambda x: -x[1]):
            print(f"    {phase:<14} {count:>4} ({count/len(rallies)*100:.1f}%)")
    
    # ── 12. CONTRARIAN SIGNAL ANALYSIS ──
    print("\n  ╔═══════════════════════════════════════════════════════════════╗")
    print("  ║  TEST 12: CONTRARIAN ANALYSIS (buy fear, sell greed?)        ║")
    print("  ╚═══════════════════════════════════════════════════════════════╝")
    
    extreme_fear = [r for r in results if r.fg_index <= 15]
    extreme_greed = [r for r in results if r.fg_index >= 85]
    
    if extreme_fear:
        avg_ret_fear = sum(r.next_return for r in extreme_fear) / len(extreme_fear)
        # Forward 7-day return (approximate: sum next 7 daily returns from index)
        print(f"\n  EXTREME FEAR (FGI ≤ 15): {len(extreme_fear):,} days")
        print(f"    Next-day avg return: {avg_ret_fear:+.3f}%")
        win_pct = sum(1 for r in extreme_fear if r.next_return > 0) / len(extreme_fear) * 100
        print(f"    Next-day win rate:   {win_pct:.1f}%")
    
    if extreme_greed:
        avg_ret_greed = sum(r.next_return for r in extreme_greed) / len(extreme_greed)
        print(f"\n  EXTREME GREED (FGI ≥ 85): {len(extreme_greed):,} days")
        print(f"    Next-day avg return: {avg_ret_greed:+.3f}%")
        win_pct = sum(1 for r in extreme_greed if r.next_return > 0) / len(extreme_greed) * 100
        print(f"    Next-day win rate:   {win_pct:.1f}%")
    
    # ── FINAL VERDICT ──
    print("\n" + "=" * 80)
    print("  🏆 FINAL VERDICT")
    print("=" * 80)
    
    # Overall edge: average return when following each oracle's BUY signal
    b6_all = [r.next_return for r in results if r.action_6 == "BUY"]
    b7_all = [r.next_return for r in results if r.action_7 == "BUY"]
    s6_all = [r.next_return for r in results if r.action_6 == "SELL"]
    s7_all = [r.next_return for r in results if r.action_7 == "SELL"]
    
    avg_b6 = sum(b6_all) / len(b6_all) if b6_all else 0
    avg_b7 = sum(b7_all) / len(b7_all) if b7_all else 0
    avg_s6 = sum(s6_all) / len(s6_all) if s6_all else 0
    avg_s7 = sum(s7_all) / len(s7_all) if s7_all else 0
    
    win_b6 = sum(1 for r in b6_all if r > 0) / len(b6_all) * 100 if b6_all else 0
    win_b7 = sum(1 for r in b7_all if r > 0) / len(b7_all) * 100 if b7_all else 0
    
    print(f"\n  6-ORACLE SEER:")
    print(f"    BUY signals:  {len(b6_all):>6,} | Win rate: {win_b6:.1f}% | Avg return: {avg_b6:+.4f}%")
    print(f"    SELL signals: {len(s6_all):>6,} | Avg return: {avg_s6:+.4f}%")
    
    print(f"\n  7-ORACLE SEER:")
    print(f"    BUY signals:  {len(b7_all):>6,} | Win rate: {win_b7:.1f}% | Avg return: {avg_b7:+.4f}%")
    print(f"    SELL signals: {len(s7_all):>6,} | Avg return: {avg_s7:+.4f}%")
    
    delta_win = win_b7 - win_b6
    delta_ret = avg_b7 - avg_b6
    
    print(f"\n  DELTA (7-Oracle - 6-Oracle):")
    print(f"    Win rate change:  {delta_win:+.1f}%")
    print(f"    Avg return change: {delta_ret:+.4f}%")
    
    if delta_win > 0:
        print(f"\n  ✅ 7-ORACLE SEER WINS — Sentiment improves win rate by {delta_win:.1f}%")
    elif delta_win < 0:
        print(f"\n  ⚠️ 6-ORACLE SEER WINS — Sentiment reduces win rate by {abs(delta_win):.1f}%")
        print(f"     BUT: Check crash avoidance — the REAL value is risk management")
    else:
        print(f"\n  ⚖️ TIE on win rate — but check qualitative differences above")
    
    # Pattern discovery
    print(f"\n  KEY PATTERNS DISCOVERED:")
    
    # Find the best fear/greed zone
    best_fg_zone = None
    best_fg_win = 0
    for name, bucket in quintiles.items():
        if bucket:
            w = sum(1 for r in bucket if r.next_return > 0) / len(bucket) * 100
            if w > best_fg_win:
                best_fg_win = w
                best_fg_zone = name
    if best_fg_zone:
        print(f"    📊 Best F/G zone: {best_fg_zone} ({best_fg_win:.1f}% win rate)")
    
    # Find the best tactical mode
    best_tac = None
    best_tac_ret = -999
    for mode, bucket in tactics.items():
        if bucket:
            avg = sum(r.next_return for r in bucket) / len(bucket)
            if avg > best_tac_ret:
                best_tac_ret = avg
                best_tac = mode
    if best_tac:
        print(f"    ⚔️ Best tactical mode: {best_tac} (avg return: {best_tac_ret:+.3f}%)")
    
    # Find the best order flow intent
    best_intent = None
    best_intent_ret = -999
    for intent, rets in intents.items():
        if rets:
            avg = sum(rets) / len(rets)
            if avg > best_intent_ret:
                best_intent_ret = avg
                best_intent = intent
    if best_intent:
        print(f"    🌊 Best flow intent: {best_intent} (avg return: {best_intent_ret:+.3f}%)")
    
    print("\n" + "=" * 80)
    print("  BACKTEST COMPLETE — ALL RESULTS FROM REAL HISTORICAL DATA")
    print("=" * 80)


if __name__ == "__main__":
    run_backtest()
