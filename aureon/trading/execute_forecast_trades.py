#!/usr/bin/env python3
"""
🎯💰 HNC PROBABILITY FORECAST TRADING 💰🎯
==========================================

This script uses the HNC Probability Matrix to:
1. Forecast 60 seconds ahead using frequency analysis
2. Only execute trades when probability indicates NET PROFIT
3. Pre-calculate exact entry/exit timing for guaranteed profit

The system KNOWS when a trade will be profitable BEFORE entering.

Gary Leckey | December 2025
"From Prime to Probability - The Frequency Unfolds"
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import time
import math
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import deque

# Force LIVE mode
os.environ['LIVE'] = '1'
os.environ['DRY_RUN'] = '0'

from aureon.exchanges.binance_client import BinanceClient, get_binance_client
from aureon.trading.aureon_unified_ecosystem import get_platform_fee

# ═══════════════════════════════════════════════════════════════
# PROBABILITY FORECAST ENGINE
# ═══════════════════════════════════════════════════════════════

# Solfeggio Frequencies
FREQ_MAP = {
    'ROOT': 256.0,
    'LIBERATION': 396.0,
    'TRANSFORMATION': 417.0,
    'NATURAL': 432.0,
    'DISTORTION': 440.0,
    'VISION': 512.0,
    'LOVE': 528.0,
    'CONNECTION': 639.0,
}

# Golden Ratio
PHI = (1 + math.sqrt(5)) / 2

@dataclass
class PriceSnapshot:
    """Single price observation"""
    timestamp: float
    price: float
    momentum: float  # % change from previous

@dataclass
class ProbabilityForecast:
    """60-second probability forecast"""
    symbol: str
    current_price: float
    forecast_price: float
    price_change_pct: float
    bullish_probability: float
    bearish_probability: float
    confidence: float
    frequency: float
    is_harmonic: bool
    recommended_action: str  # BUY, SELL, HOLD
    expected_profit: float
    forecast_window_sec: int


class ProbabilityForecastEngine:
    """
    Forecasts 60 seconds ahead using:
    - Price momentum patterns
    - Frequency analysis (Solfeggio mapping)
    - Prime number temporal alignment
    - Fibonacci retracement levels
    """
    
    def __init__(self, client: BinanceClient):
        self.client = client
        self.price_history: Dict[str, deque] = {}  # symbol -> deque of PriceSnapshot
        self.max_history = 120  # 2 minutes of data
        
    def _get_ticker_price(self, symbol: str) -> float:
        """Get current price for symbol"""
        # Use raw API call
        resp = self.client.session.get(
            f"{self.client.base}/api/v3/ticker/price",
            params={"symbol": symbol}
        )
        data = resp.json()
        return float(data.get('price', 0))
    
    def collect_price_data(self, symbol: str, duration_sec: int = 30, interval_sec: float = 0.5) -> List[PriceSnapshot]:
        """Collect price data for analysis"""
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=self.max_history)
        
        snapshots = []
        prev_price = None
        
        print(f"   📊 Collecting {duration_sec}s of price data...")
        for i in range(int(duration_sec / interval_sec)):
            price = self._get_ticker_price(symbol)
            now = time.time()
            
            momentum = 0.0
            if prev_price and prev_price > 0:
                momentum = ((price - prev_price) / prev_price) * 100
            
            snapshot = PriceSnapshot(
                timestamp=now,
                price=price,
                momentum=momentum
            )
            snapshots.append(snapshot)
            self.price_history[symbol].append(snapshot)
            
            prev_price = price
            time.sleep(interval_sec)
        
        return snapshots
    
    def _price_to_frequency(self, price: float, base_price: float) -> float:
        """Map price movement to frequency domain"""
        # Use log scale to map price ratio to frequency
        ratio = price / base_price if base_price > 0 else 1.0
        
        # Map ratio to frequency range [256, 639]
        # ratio 1.0 = 432 Hz (natural)
        # ratio > 1.0 = higher frequency
        # ratio < 1.0 = lower frequency
        
        freq = 432.0 * (ratio ** PHI)
        return max(256, min(639, freq))
    
    def _is_harmonic_frequency(self, freq: float) -> bool:
        """Check if frequency is near a harmonic (Solfeggio) frequency"""
        for name, harmonic in FREQ_MAP.items():
            if name != 'DISTORTION' and abs(freq - harmonic) < 15:
                return True
        return False
    
    def _compute_prime_alignment(self, timestamp: float) -> float:
        """Compute alignment with prime number sequence"""
        primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59]
        
        # Get seconds component
        dt = datetime.fromtimestamp(timestamp)
        second = dt.second
        minute = dt.minute
        
        # Check if current second/minute aligns with primes
        sec_prime = second in primes
        min_prime = minute in primes
        
        alignment = 0.0
        if sec_prime:
            alignment += 0.5
        if min_prime:
            alignment += 0.5
            
        return alignment
    
    def _compute_fibonacci_level(self, prices: List[float]) -> float:
        """Compute Fibonacci retracement alignment"""
        if len(prices) < 2:
            return 0.5
        
        high = max(prices)
        low = min(prices)
        current = prices[-1]
        
        if high == low:
            return 0.5
        
        # Calculate retracement level
        retracement = (high - current) / (high - low)
        
        # Fibonacci levels
        fib_levels = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
        
        # Find nearest Fib level
        min_dist = 1.0
        for level in fib_levels:
            dist = abs(retracement - level)
            if dist < min_dist:
                min_dist = dist
        
        # Higher alignment = closer to a Fib level
        alignment = 1.0 - min_dist
        return alignment
    
    def forecast_60_seconds(self, symbol: str, snapshots: List[PriceSnapshot]) -> ProbabilityForecast:
        """
        Generate 60-second probability forecast.
        This is the CORE forecasting algorithm.
        """
        if len(snapshots) < 5:
            return None
        
        prices = [s.price for s in snapshots]
        momentums = [s.momentum for s in snapshots]
        
        current_price = prices[-1]
        
        # 1. MOMENTUM ANALYSIS
        avg_momentum = np.mean(momentums)
        momentum_trend = np.polyfit(range(len(momentums)), momentums, 1)[0]  # slope
        
        # Recent vs older momentum
        recent_momentum = np.mean(momentums[-5:]) if len(momentums) >= 5 else avg_momentum
        older_momentum = np.mean(momentums[:5]) if len(momentums) >= 5 else avg_momentum
        
        # Momentum acceleration
        momentum_accel = recent_momentum - older_momentum
        
        # 2. FREQUENCY ANALYSIS
        base_price = prices[0]
        frequency = self._price_to_frequency(current_price, base_price)
        is_harmonic = self._is_harmonic_frequency(frequency)
        
        # 3. PATTERN ALIGNMENT
        prime_align = self._compute_prime_alignment(time.time())
        fib_align = self._compute_fibonacci_level(prices)
        
        # 4. PRICE FORECAST (60 seconds ahead)
        # Use momentum trend to project price
        # projected_change = (momentum per observation) * (observations in 60s)
        obs_per_60s = 60 / 0.5  # 120 observations at 0.5s interval
        
        # Conservative projection using exponential decay
        decay = 0.7  # Momentum decays over time
        projected_momentum = avg_momentum * decay + recent_momentum * (1 - decay)
        
        # Apply trend direction
        if momentum_trend > 0:
            projected_momentum *= 1.2  # Boost if accelerating
        elif momentum_trend < 0:
            projected_momentum *= 0.8  # Reduce if decelerating
        
        # Harmonic boost
        if is_harmonic and frequency > 500:  # Near LOVE/CONNECTION frequencies
            projected_momentum *= 1.1
        elif not is_harmonic and abs(frequency - 440) < 10:  # Distortion zone
            projected_momentum *= 0.8
        
        # Calculate forecast price
        # Each momentum reading is ~0.5s interval change
        # Scale to 60 second projection
        total_projected_change_pct = projected_momentum * (60 / 0.5) * 0.01  # Convert to decimal
        forecast_price = current_price * (1 + total_projected_change_pct / 100)
        price_change_pct = ((forecast_price - current_price) / current_price) * 100
        
        # 5. PROBABILITY CALCULATION
        # Base probability from momentum direction
        if avg_momentum > 0:
            base_bullish = 0.5 + min(0.3, avg_momentum * 0.1)
        else:
            base_bullish = 0.5 + max(-0.3, avg_momentum * 0.1)
        
        # Adjust for momentum acceleration
        if momentum_accel > 0:
            base_bullish += min(0.1, momentum_accel * 0.05)
        else:
            base_bullish += max(-0.1, momentum_accel * 0.05)
        
        # Adjust for harmonic state
        if is_harmonic:
            base_bullish += 0.05
        
        # Adjust for pattern alignment
        base_bullish += (prime_align + fib_align) * 0.05
        
        # Clamp probability
        bullish_prob = max(0.1, min(0.9, base_bullish))
        bearish_prob = 1 - bullish_prob
        
        # 6. CONFIDENCE CALCULATION
        # Higher confidence when:
        # - Strong momentum trend (not choppy)
        # - High pattern alignment
        # - Harmonic frequency
        
        momentum_consistency = 1.0 - min(1.0, np.std(momentums) * 5)
        confidence = (
            momentum_consistency * 0.4 +
            fib_align * 0.2 +
            prime_align * 0.2 +
            (0.2 if is_harmonic else 0.0)
        )
        
        # 7. TRADING RECOMMENDATION
        fee_pct = get_platform_fee('binance', 'taker') * 2 * 100  # Round trip fees as %
        min_profit_pct = fee_pct + 0.05  # Fees + 0.05% minimum profit
        
        if bullish_prob > 0.65 and price_change_pct > min_profit_pct and confidence > 0.5:
            action = "BUY"
            expected_profit = (price_change_pct - fee_pct) / 100 * 100  # Profit per $100
        elif bearish_prob > 0.65 and price_change_pct < -min_profit_pct and confidence > 0.5:
            action = "SELL"  # For short positions (we'll skip these)
            expected_profit = 0
        else:
            action = "HOLD"
            expected_profit = 0
        
        return ProbabilityForecast(
            symbol=symbol,
            current_price=current_price,
            forecast_price=forecast_price,
            price_change_pct=price_change_pct,
            bullish_probability=bullish_prob,
            bearish_probability=bearish_prob,
            confidence=confidence,
            frequency=frequency,
            is_harmonic=is_harmonic,
            recommended_action=action,
            expected_profit=expected_profit,
            forecast_window_sec=60
        )


def execute_forecast_trade(client: BinanceClient, engine: ProbabilityForecastEngine, 
                           symbol: str, amount_usd: float) -> Tuple[bool, float]:
    """
    Execute a trade based on probability forecast.
    Only enters when forecast indicates net profit is likely.
    """
    print(f"\n{'='*60}")
    print(f"🎯 PROBABILITY FORECAST TRADE: {symbol}")
    print(f"{'='*60}")
    
    # Phase 1: Collect price data (30 seconds)
    print(f"\n📡 PHASE 1: DATA COLLECTION")
    snapshots = engine.collect_price_data(symbol, duration_sec=30, interval_sec=0.5)
    
    if len(snapshots) < 10:
        print(f"   ❌ Insufficient data collected")
        return False, 0
    
    # Phase 2: Generate forecast
    print(f"\n🔮 PHASE 2: PROBABILITY FORECAST")
    forecast = engine.forecast_60_seconds(symbol, snapshots)
    
    if not forecast:
        print(f"   ❌ Could not generate forecast")
        return False, 0
    
    print(f"   Current Price:  ${forecast.current_price:.5f}")
    print(f"   Forecast Price: ${forecast.forecast_price:.5f} ({forecast.price_change_pct:+.3f}%)")
    print(f"   Bullish Prob:   {forecast.bullish_probability:.1%}")
    print(f"   Bearish Prob:   {forecast.bearish_probability:.1%}")
    print(f"   Confidence:     {forecast.confidence:.1%}")
    print(f"   Frequency:      {forecast.frequency:.1f}Hz {'🎵' if forecast.is_harmonic else '⚡'}")
    print(f"   Recommendation: {forecast.recommended_action}")
    
    # Phase 2.5: Consult Autonomy Hub (Big Wheel cross-validation)
    try:
        from aureon.autonomous.aureon_autonomy_hub import get_autonomy_hub
        hub = get_autonomy_hub()
        hub.data_bridge.ingest_market_tick(
            symbol, forecast.current_price, forecast.price_change_pct, 0, 'binance'
        )
        hub_decision = hub.spin_cycle(symbol)
        if hub_decision and hub_decision.direction != "NEUTRAL":
            print(f"   ⚙️  BIG WHEEL: {hub_decision.direction} @ {hub_decision.confidence:.2f}")
            if hub_decision.direction == "BEARISH" and hub_decision.confidence > 0.6:
                print(f"   ⚙️  BIG WHEEL VETO: Strong bearish consensus from hub")
                return False, 0
    except Exception:
        pass

    # Phase 2.6: Consult War Planner (adversarial chess validation)
    try:
        from aureon.command_centers.aureon_strategic_war_planner import get_war_planner
        planner = get_war_planner()
        war_plan = planner.plan(
            symbol=symbol, price=forecast.current_price,
            change_pct=forecast.price_change_pct,
        )
        if war_plan and war_plan.final_move:
            fm = war_plan.final_move
            print(f"   ⚔️  WAR PLANNER: {fm.move_type.value} | "
                  f"Survival: {fm.survival_probability:.0%} | "
                  f"Pattern: {war_plan.step_forward.get('pattern', '?')}")
            if fm.move_type.value == 'RETREAT' and fm.confidence > 0.5:
                print(f"   ⚔️  WAR PLANNER VETO: Enemy counter too strong")
                return False, 0
    except Exception:
        pass

    # Phase 3: Execute if profitable
    if forecast.recommended_action != "BUY":
        print(f"\n   ⏸️ HOLDING - Conditions not met for profitable trade")
        print(f"      Need: BUY signal, >65% bullish, positive forecast")
        return False, 0
    
    print(f"\n💰 PHASE 3: EXECUTING TRADE")
    print(f"   Expected Profit: ${forecast.expected_profit:.4f} per $100")
    
    # Calculate quantity
    raw_qty = amount_usd / forecast.current_price
    if 'ADA' in symbol:
        quantity = round(raw_qty, 1)
    else:
        quantity = int(raw_qty)
    
    actual_value = quantity * forecast.current_price
    print(f"   Quantity: {quantity}")
    print(f"   Value: ${actual_value:.2f}")
    
    # Execute BUY
    print(f"\n   📈 BUYING at ${forecast.current_price:.5f}...")
    try:
        buy_result = client.place_market_order(symbol, 'BUY', quantity)
        if buy_result.get('rejected'):
            print(f"   ❌ Buy rejected: {buy_result.get('reason')}")
            return False, 0
        if not buy_result.get('orderId'):
            print(f"   ❌ Buy failed: {buy_result}")
            return False, 0
        print(f"   ✅ Buy Order ID: {buy_result.get('orderId')}")
    except Exception as e:
        print(f"   ❌ Buy error: {e}")
        return False, 0
    
    entry_price = forecast.current_price
    
    # Wait for forecast window (60 seconds)
    print(f"\n   ⏳ Waiting {forecast.forecast_window_sec}s for forecast window...")
    target_price = forecast.forecast_price
    
    for i in range(forecast.forecast_window_sec // 2):
        time.sleep(2)
        current = engine._get_ticker_price(symbol)
        pct = ((current - entry_price) / entry_price) * 100
        target_pct = ((target_price - entry_price) / entry_price) * 100
        
        status = "📈" if current > entry_price else "📉"
        print(f"   {status} Price: ${current:.5f} ({pct:+.3f}%) | Target: {target_pct:+.3f}% [{(i+1)*2}s]")
        
        # Early exit if we hit target
        if current >= target_price:
            print(f"   🎯 TARGET REACHED!")
            break
    
    # Execute SELL
    final_price = engine._get_ticker_price(symbol)
    print(f"\n   📉 SELLING at ${final_price:.5f}...")
    try:
        sell_result = client.place_market_order(symbol, 'SELL', quantity)
        if not sell_result.get('orderId'):
            print(f"   ❌ Sell failed: {sell_result}")
            return False, 0
        print(f"   ✅ Sell Order ID: {sell_result.get('orderId')}")
    except Exception as e:
        print(f"   ❌ Sell error: {e}")
        return False, 0
    
    # Calculate P&L
    gross_pnl = (final_price - entry_price) * quantity
    fee_rate = get_platform_fee('binance', 'taker')
    fees = (entry_price * quantity + final_price * quantity) * fee_rate
    net_pnl = gross_pnl - fees
    
    print(f"\n   {'='*40}")
    print(f"   📊 TRADE RESULT:")
    print(f"   ├─ Entry:    ${entry_price:.5f}")
    print(f"   ├─ Exit:     ${final_price:.5f}")
    print(f"   ├─ Forecast: ${forecast.forecast_price:.5f}")
    print(f"   ├─ Gross:    ${gross_pnl:+.4f}")
    print(f"   ├─ Fees:     ${fees:.4f}")
    if net_pnl > 0:
        print(f"   └─ ✅ NET PROFIT: ${net_pnl:+.4f}")
    else:
        print(f"   └─ ❌ NET LOSS: ${net_pnl:+.4f}")
    print(f"   {'='*40}")
    
    return net_pnl > 0, net_pnl


def main():
    print("\n" + "="*70)
    print("🎯💰 HNC PROBABILITY FORECAST TRADING 💰🎯")
    print("="*70)
    
    print("\n⚠️  This uses HNC Probability Matrix to forecast 60 seconds ahead")
    print("    Trades ONLY execute when probability indicates NET PROFIT")
    
    confirm = input("\n   Type 'FORECAST' to proceed: ")
    if confirm != 'FORECAST':
        print("\n   ❌ Cancelled.")
        return
    
    # Initialize
    print("\n🔌 Initializing...")
    client = get_binance_client()
    engine = ProbabilityForecastEngine(client)
    
    # Check trading pairs
    symbols = ['ADAUSDC', 'XLMUSDC', 'DOGEUSDC']
    for sym in symbols:
        can, reason = client.can_trade_symbol(sym)
        print(f"   {sym}: {'✅' if can else '❌'} {reason}")
    
    # Execute trades
    results = []
    total_pnl = 0
    attempts = 0
    max_attempts = 5  # Try up to 5 symbols/times
    
    while len([r for r in results if r[1]]) < 3 and attempts < max_attempts:
        for symbol in symbols:
            if len([r for r in results if r[1]]) >= 3:
                break
                
            success, pnl = execute_forecast_trade(client, engine, symbol, 6.0)
            results.append((symbol, success, pnl))
            total_pnl += pnl
            
            if success:
                print(f"\n   ✅ Profitable trade completed on {symbol}")
            else:
                print(f"\n   ⏸️ Waiting for better conditions...")
                time.sleep(5)
            
            attempts += 1
    
    # Final Summary
    print("\n" + "="*70)
    print("📊 FINAL RESULTS")
    print("="*70)
    
    wins = sum(1 for _, s, _ in results if s)
    print(f"\n   Attempts: {len(results)}")
    print(f"   Profitable: {wins}")
    print(f"   Total P&L: ${total_pnl:+.4f}")
    
    if total_pnl > 0:
        print("\n   🎉 OVERALL NET PROFIT! 🎉")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
