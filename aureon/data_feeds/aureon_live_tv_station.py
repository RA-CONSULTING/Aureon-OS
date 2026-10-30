#!/usr/bin/env python3
"""
📺🌊 AUREON LIVE TV STATION - TRUTH PREDICTION ENGINE 🌊📺

Purpose:
- Consume REAL Binance WebSocket cache data (ws_cache/ws_prices.json)
- Use Queen's probability matrices
- Dr. Auris validation on all predictions
- Harmonic Hz resonance analysis
- Generate and validate TRUTH-BASED predictions
- Feed validation outcomes back to probability learning

⚠️ REAL DATA ONLY. Queen + Auris + Harmonic validation REQUIRED.
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        def _is_buffer_valid(stream):
            if not hasattr(stream, 'buffer'):
                return False
            try:
                return stream.buffer is not None and not stream.buffer.closed
            except (ValueError, AttributeError):
                return False
        if _is_buffer_valid(sys.stdout) and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if _is_buffer_valid(sys.stderr) and not _is_utf8_wrapper(sys.stderr):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

import json
import time
import math
from pathlib import Path
from typing import Dict, List, Deque, Tuple
from collections import deque
from datetime import datetime

from aureon.wisdom.metatrons_cube_knowledge_exchange import QueenAurisPingPong
from aureon.intelligence.aureon_truth_prediction_engine import (
    TruthPredictionEngine,
    MarketSnapshot
)

# Sacred constants
PHI = (1 + math.sqrt(5)) / 2
SCHUMANN_BASE = 7.83
MAX_HZ = 963.0

WS_CACHE_PATH = Path(os.getenv("WS_PRICE_CACHE_PATH", "ws_cache/ws_prices.json"))
STREAM_DELAY_SECONDS = 30.0
PINGPONG_INTERVAL = 10.0
PREDICTION_HORIZON_SECONDS = 30.0
MIN_HISTORY_SECONDS = 30.0
LOG_PATH = Path("live_tv_stream.jsonl")


def _read_ws_cache():
    if not WS_CACHE_PATH.exists():
        return None
    try:
        return json.loads(WS_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def _extract_price_data(payload: Dict) -> List[Tuple[str, float, float, float, float]]:
    """Extract (symbol, price, change_24h, volume_24h, timestamp) from cache."""
    tickers = payload.get("ticker_cache", {}) if isinstance(payload, dict) else {}
    generated_at = float(payload.get("generated_at", time.time()))
    results = []
    
    for symbol, ticker in tickers.items():
        if not isinstance(ticker, dict):
            continue
        try:
            price = float(ticker.get("c", 0))
            change_24h = float(ticker.get("P", 0))
            volume_24h = float(ticker.get("v", 0))
            if price > 0:
                results.append((symbol, price, change_24h, volume_24h, generated_at))
        except (ValueError, TypeError):
            continue
    
    return results


def _momentum_from_history(hist: Deque[Tuple[float, float]]) -> float:
    """Calculate % change over history window."""
    if len(hist) < 2:
        return 0.0
    t0, p0 = hist[0]
    t1, p1 = hist[-1]
    if p0 == 0:
        return 0.0
    return ((p1 - p0) / p0) * 100.0


def _volatility_from_history(hist: Deque[Tuple[float, float]]) -> float:
    """Calculate volatility (std dev as %) over history."""
    if len(hist) < 2:
        return 0.0
    prices = [p for _, p in hist]
    mean = sum(prices) / len(prices)
    if mean == 0:
        return 0.0
    variance = sum((p - mean) ** 2 for p in prices) / len(prices)
    return (math.sqrt(variance) / mean) * 100.0


def _price_to_hz(momentum: float, volatility: float) -> float:
    """Map momentum + volatility to harmonic Hz (7.83 - 963)."""
    strength = (abs(momentum) + volatility) / 10.0
    strength = max(0.0, min(strength, 10.0))
    return SCHUMANN_BASE + (strength * (MAX_HZ - SCHUMANN_BASE) / 10.0)


def _format_hz_label(hz: float) -> str:
    """Classify Hz into brainwave/harmonic bands."""
    if hz < 10:
        return "Schumann"
    elif hz < 100:
        return "Alpha"
    elif hz < 300:
        return "Beta"
    elif hz < 700:
        return "Gamma"
    else:
        return "Solfeggio"


def _log_event(data: Dict):
    """Append event to JSONL log."""
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(data) + "\n")
    except Exception:
        pass


def main():
    print(f"📺 AUREON LIVE TV STATION - TRUTH PREDICTION ENGINE")
    print(f"   Cache: {WS_CACHE_PATH}")
    print(f"   Delay: {STREAM_DELAY_SECONDS}s | Prediction horizon: {PREDICTION_HORIZON_SECONDS}s")
    print(f"   ✅ Queen's probability matrices")
    print(f"   ✅ Dr. Auris validation")
    print(f"   ✅ Harmonic Hz resonance analysis")
    print(f"   REAL DATA ONLY - waiting for Binance WS cache...\n")

    pingpong = QueenAurisPingPong()
    prediction_engine = TruthPredictionEngine()
    history: Dict[str, Deque[Tuple[float, float]]] = {}
    delayed_buffer: Deque[Dict] = deque(maxlen=10000)
    
    last_pingpong = 0.0
    last_seen_cache = 0.0
    prediction_count = 0
    last_stats_print = 0.0

    while True:
        payload = _read_ws_cache()
        if not payload:
            time.sleep(0.5)
            continue

        generated_at = float(payload.get("generated_at", time.time()))
        if generated_at == last_seen_cache:
            time.sleep(0.5)
            continue
        last_seen_cache = generated_at

        price_data = _extract_price_data(payload)
        now = time.time()

        for symbol, price, change_24h, volume_24h, timestamp in price_data:
            # Update price history
            hist = history.setdefault(symbol, deque(maxlen=180))
            hist.append((timestamp, price))

            # Need enough history for metrics
            duration = hist[-1][0] - hist[0][0] if len(hist) >= 2 else 0
            if duration < MIN_HISTORY_SECONDS:
                continue
            
            # Calculate metrics from history
            momentum = _momentum_from_history(hist)
            volatility = _volatility_from_history(hist)
            hz = _price_to_hz(momentum, volatility)
            
            # Build market snapshot for prediction engine
            market_snapshot = MarketSnapshot(
                symbol=symbol,
                price=price,
                change_24h=change_24h,
                volume_24h=volume_24h,
                momentum_30s=momentum,
                volatility_30s=volatility,
                hz_frequency=hz,
                timestamp=now
            )
            
            # Generate prediction using TRUTH ENGINE (every 20th symbol to avoid spam)
            if prediction_count % 20 == 0:
                pred = prediction_engine.generate_prediction(
                    market_snapshot,
                    horizon_seconds=PREDICTION_HORIZON_SECONDS,
                    min_confidence=0.65
                )
                if pred:
                    print(f"\n🎯 PREDICTION APPROVED: {pred.symbol}")
                    print(f"   {pred.predicted_direction} {pred.predicted_change_pct:+.3f}% | "
                          f"Win={pred.win_probability:.1%} | Confidence={pred.pattern_confidence:.1%}")
                    print(f"   Auris: {pred.auris_approved} (resonance={pred.auris_resonance:.2f}) | "
                          f"Queen: {pred.queen_approved}")
                    print(f"   Pattern: {pred.pattern_key}")
                    
                    _log_event({
                        "event": "prediction_generated",
                        "timestamp": now,
                        "symbol": pred.symbol,
                        "direction": pred.predicted_direction,
                        "change_pct": pred.predicted_change_pct,
                        "win_probability": pred.win_probability,
                        "pattern_confidence": pred.pattern_confidence,
                        "auris_approved": pred.auris_approved,
                        "queen_approved": pred.queen_approved,
                        "pattern_key": str(pred.pattern_key)
                    })
            prediction_count += 1
            
            # Validate any pending predictions for this symbol
            validated_preds = prediction_engine.validate_predictions(market_snapshot)
            for vp in validated_preds:
                print(f"\n✅ VALIDATION: {vp.symbol} | Predicted {vp.predicted_direction} {vp.predicted_change_pct:+.3f}%")
                print(f"              Actual {vp.actual_change_pct:+.3f}% | {'✅ CORRECT' if vp.correct else '❌ WRONG'}")
                print(f"              Geometric Truth: {vp.geometric_truth:.3f}")
                
                _log_event({
                    "event": "prediction_validated",
                    "timestamp": now,
                    "symbol": vp.symbol,
                    "predicted_direction": vp.predicted_direction,
                    "predicted_change_pct": vp.predicted_change_pct,
                    "actual_direction": "UP" if vp.actual_change_pct > 0 else ("DOWN" if vp.actual_change_pct < 0 else "FLAT"),
                    "actual_change_pct": vp.actual_change_pct,
                    "correct": vp.correct,
                    "geometric_truth": vp.geometric_truth,
                    "win_probability": vp.win_probability,
                    "pattern_key": str(vp.pattern_key)
                })
            
            # Push to delayed buffer for TV output
            delayed_buffer.append({
                "timestamp": timestamp,
                "symbol": symbol,
                "price": price,
                "change_24h": change_24h,
                "momentum": momentum,
                "volatility": volatility,
                "hz": hz,
                "hz_label": _format_hz_label(hz),
            })

        # Queen ↔ Auris ping-pong on top volume symbol
        if now - last_pingpong >= PINGPONG_INTERVAL and price_data:
            last_pingpong = now
            top_symbol, top_price, top_change, top_volume, _ = max(price_data, key=lambda x: x[3])
            hist = history.get(top_symbol, deque())
            if len(hist) >= 2:
                momentum = _momentum_from_history(hist)
                volatility = _volatility_from_history(hist)
                hz = _price_to_hz(momentum, volatility)
                message = (
                    f"LIVE METRICS | {top_symbol} price={top_price:.6f} change24h={top_change:+.2f}% "
                    f"momentum30s={momentum:+.3f}% vol30s={volatility:.3f}% hz={hz:.2f}"
                )
                thoughts = pingpong.queen_speaks(message, target_sphere=0)
                pingpong.auris_validates(thoughts)
                truth = pingpong.check_geometric_truth()
                if truth:
                    _log_event({
                        "type": "geometric_truth",
                        "timestamp": now,
                        "confidence": truth.confidence,
                        "truth": truth.truth
                    })

        # Emit delayed TV stream (30s)
        while delayed_buffer and (now - delayed_buffer[0]["timestamp"]) >= STREAM_DELAY_SECONDS:
            item = delayed_buffer.popleft()
            line = (
                f"📺 DELAYED {STREAM_DELAY_SECONDS:.0f}s | {item['symbol']} | "
                f"${item['price']:.6f} | 24h {item['change_24h']:+.2f}% | "
                f"mom30s {item['momentum']:+.3f}% | vol30s {item['volatility']:.3f}% | "
                f"{item['hz_label']} {item['hz']:.2f} Hz"
            )
            print(line)
            _log_event({
                "type": "delayed_stream",
                "timestamp": now,
                **item
            })

        # Show accuracy stats every 30 seconds
        if now - last_stats_print >= 30.0:
            last_stats_print = now
            stats = prediction_engine.get_accuracy_stats()
            if stats["total_validated"] > 0:
                print(f"\n📊 PREDICTION ACCURACY: {stats['accuracy_pct']:.1f}% ({stats['correct']}/{stats['total_validated']}) | "
                      f"Avg Geometric Truth: {stats['avg_geometric_truth']:.3f}\n")

        time.sleep(0.5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Live TV Station stopped")
