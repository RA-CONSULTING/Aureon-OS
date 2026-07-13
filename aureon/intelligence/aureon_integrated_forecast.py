#!/usr/bin/env python3
"""
🌳🎯 AUREON INTEGRATED FORECAST TRADER 🎯🌳
============================================

This script implements the COMPLETE prediction process tree:

1. COSMIC GATES: Earth Resonance + Imperial Predictability
2. PROBABILITY FORECAST: 60-second ahead using HNC Matrix
3. TRADE EXECUTION: Only when ALL systems align

The system KNOWS probability BEFORE entering any trade.

Gary Leckey | December 2025
"All Systems Aligned - From Cosmos to Profit"
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import time
import math
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from collections import deque

# Force LIVE mode
os.environ['LIVE'] = '1'
os.environ['DRY_RUN'] = '0'

# Import all prediction systems
from aureon.exchanges.binance_client import BinanceClient, get_binance_client
from aureon.harmonic.earth_resonance_engine import EarthResonanceEngine
from aureon.strategies.hnc_imperial_predictability import CosmicStateEngine, PredictabilityEngine, CosmicPhase

# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════

PHI = (1 + math.sqrt(5)) / 2  # Golden Ratio = 1.618

# Solfeggio Frequencies
FREQ_MAP = {
    'ROOT': 256.0,
    'LIBERATION': 396.0,
    'TRANSFORMATION': 417.0,
    'NATURAL': 432.0,
    'DISTORTION': 440.0,
    'LOVE': 528.0,
    'CONNECTION': 639.0,
}

# Fee structure (Binance taker fee)
FEE_RATE = 0.001  # 0.1%
MIN_PROFIT_ABOVE_FEES = 0.0005  # 0.05% above fees

# Thresholds
MIN_PROBABILITY = 0.65  # 65% bullish
MIN_CONFIDENCE = 0.50   # 50% confidence


@dataclass
class PriceSnapshot:
    """Single price observation"""
    timestamp: float
    price: float
    momentum: float


@dataclass
class IntegratedForecast:
    """Complete forecast using all systems"""
    symbol: str
    timestamp: datetime
    
    # Cosmic Gates
    earth_gate_open: bool
    earth_coherence: float
    earth_phi_boost: float
    cosmic_gate_open: bool
    cosmic_phase: str
    cosmic_boost: float
    planetary_torque: float
    
    # Probability Forecast
    current_price: float
    forecast_price: float
    price_change_pct: float
    bullish_probability: float
    confidence: float
    frequency: float
    is_harmonic: bool
    
    # Decision
    should_trade: bool
    reason: str
    recommended_action: str
    position_multiplier: float
    expected_profit_pct: float


class IntegratedForecastTrader:
    """
    Complete integrated forecast trader using ALL prediction systems:
    - Earth Resonance Engine (cosmic gate)
    - Imperial Predictability Engine (cosmic state)
    - HNC Probability Matrix (60s forecast)
    """
    
    def __init__(self):
        print("\n🌳 Initializing Integrated Forecast Trader...")
        
        # Initialize all engines
        self.client = get_binance_client()
        self.earth_engine = EarthResonanceEngine()
        self.cosmic_engine = CosmicStateEngine()
        self.predictability_engine = PredictabilityEngine()
        
        # Price history for forecasting
        self.price_history: Dict[str, deque] = {}
        
        print("   ✅ Binance Client")
        print("   ✅ Earth Resonance Engine")
        print("   ✅ Cosmic State Engine")
        print("   ✅ Predictability Engine")
        print("   🌳 All systems ready.\n")
    
    def _get_price(self, symbol: str) -> float:
        """Get current price"""
        resp = self.client.session.get(
            f"{self.client.base}/api/v3/ticker/price",
            params={"symbol": symbol}
        )
        return float(resp.json().get('price', 0))
    
    def _collect_price_data(self, symbol: str, duration_sec: int = 30) -> List[PriceSnapshot]:
        """Collect price snapshots for forecasting"""
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=200)
        
        snapshots = []
        prev_price = None
        interval = 0.5  # 500ms
        
        for _ in range(int(duration_sec / interval)):
            price = self._get_price(symbol)
            now = time.time()
            
            momentum = 0.0
            if prev_price and prev_price > 0:
                momentum = ((price - prev_price) / prev_price) * 100
            
            snap = PriceSnapshot(timestamp=now, price=price, momentum=momentum)
            snapshots.append(snap)
            self.price_history[symbol].append(snap)
            
            prev_price = price
            time.sleep(interval)
        
        return snapshots
    
    def _price_to_frequency(self, price: float, base_price: float) -> float:
        """Map price movement to frequency domain"""
        ratio = price / base_price if base_price > 0 else 1.0
        freq = 432.0 * (ratio ** PHI)
        return max(256, min(639, freq))
    
    def _is_harmonic(self, freq: float) -> bool:
        """Check if frequency is near a harmonic"""
        for name, harmonic in FREQ_MAP.items():
            if name != 'DISTORTION' and abs(freq - harmonic) < 15:
                return True
        return False
    
    def check_cosmic_gates(self) -> Tuple[bool, Dict]:
        """
        LAYER 1: Check all cosmic gates.
        Returns (gates_open, gate_details)
        """
        details = {}
        
        # 1A. Earth Resonance Gate
        # For live trading, temporarily use a lower threshold to allow more opportunities
        # The natural cycle will boost coherence over time
        self.earth_engine.COHERENCE_THRESHOLD = 0.45  # Reduced from 0.55
        
        # Update the Schumann state. In production, EarthResonanceEngine
        # reads from SchumannResonanceBridge (Barcelona/USGS); when no live
        # reading is available the call raises and we degrade earth_*
        # gracefully instead of trading off a sin-wave fabrication.
        try:
            self.earth_engine.update_schumann_state(market_volatility=0.0)
            gate_status = self.earth_engine.get_trading_gate_status_dict()
            earth_coherence = gate_status['coherence']
            earth_phase_lock = gate_status['phase_locked']
            earth_phi = self.earth_engine.get_phi_position_multiplier()
            earth_open = gate_status['gate_open']
        except RuntimeError as exc:
            # Live Schumann unavailable + no sim fallback. Treat as
            # "earth gate unknown" rather than fabricate a coherence reading.
            import logging
            logging.getLogger(__name__).warning(
                f"earth_resonance unavailable, earth_* set to neutral/closed: {exc}"
            )
            earth_coherence = None
            earth_phase_lock = False
            earth_phi = 1.0
            earth_open = False
        
        details['earth'] = {
            'open': earth_open,
            'coherence': earth_coherence,
            'phase_lock': 0.7 if earth_phase_lock else 0.4,  # Approximate
            'phi_boost': earth_phi,
            'reason': gate_status['reason'],
        }
        
        # 1B. Cosmic State Gate
        cosmic_state = self.cosmic_engine.compute_state()
        
        cosmic_phase = cosmic_state.phase
        cosmic_distortion = cosmic_state.distortion
        cosmic_coherence = cosmic_state.coherence
        
        # Cosmic gate open if not in DISTORTION phase
        # NOTE: Early December 2025 shows DISTORTION due to logistic ramp-up
        # After 3-4 days from baseline, coherence naturally rises above 0.5
        # For live trading, we can override if other indicators are positive
        cosmic_open = cosmic_phase != CosmicPhase.DISTORTION
        
        # Allow trading override if distortion is low even with low coherence
        # This handles the "early days" issue where coherence hasn't ramped up yet
        if not cosmic_open and cosmic_distortion < 0.02 and cosmic_coherence > 0.30:
            cosmic_open = True  # Low distortion = safe to trade
            cosmic_phase_name = "TRANSITION"  # Upgrade from DISTORTION
        else:
            cosmic_phase_name = cosmic_phase.name
        
        # Cosmic boost based on phase
        cosmic_boost = {
            CosmicPhase.UNITY: 1.5,
            CosmicPhase.COHERENCE: 1.3,
            CosmicPhase.HARMONIC: 1.1,
            CosmicPhase.TRANSITION: 0.9,
            CosmicPhase.DISTORTION: 0.5,
        }.get(cosmic_phase, 1.0)
        
        details['cosmic'] = {
            'open': cosmic_open,
            'phase': cosmic_phase_name,
            'boost': cosmic_boost,
            'distortion': cosmic_distortion,
            'coherence': cosmic_coherence,
        }
        
        # 1C. Planetary Torque
        planetary_torque = self.cosmic_engine.compute_planetary_torque(datetime.now())
        details['planetary_torque'] = planetary_torque
        
        # All gates must be open
        all_open = earth_open and cosmic_open
        details['all_open'] = all_open
        
        return all_open, details
    
    def generate_forecast(self, symbol: str, snapshots: List[PriceSnapshot], 
                          gate_details: Dict) -> IntegratedForecast:
        """
        LAYER 2: Generate 60-second probability forecast.
        Integrates cosmic state into probability calculation.
        """
        if len(snapshots) < 10:
            return None
        
        prices = [s.price for s in snapshots]
        momentums = [s.momentum for s in snapshots]
        
        current_price = prices[-1]
        base_price = prices[0]
        
        # Momentum analysis
        avg_momentum = np.mean(momentums)
        recent_momentum = np.mean(momentums[-10:])
        older_momentum = np.mean(momentums[:10])
        momentum_accel = recent_momentum - older_momentum
        momentum_trend = np.polyfit(range(len(momentums)), momentums, 1)[0]
        
        # Frequency analysis
        frequency = self._price_to_frequency(current_price, base_price)
        is_harmonic = self._is_harmonic(frequency)
        
        # ═══════════════════════════════════════════════════════════════
        # PROBABILITY CALCULATION (Integrated with Cosmic State)
        # ═══════════════════════════════════════════════════════════════
        
        # Base probability from momentum
        if avg_momentum > 0:
            base_prob = 0.5 + min(0.25, avg_momentum * 0.08)
        else:
            base_prob = 0.5 + max(-0.25, avg_momentum * 0.08)
        
        # Momentum acceleration adjustment
        if momentum_accel > 0:
            base_prob += min(0.10, momentum_accel * 0.04)
        else:
            base_prob += max(-0.10, momentum_accel * 0.04)
        
        # Harmonic frequency boost
        if is_harmonic and frequency > 500:  # Near LOVE/CONNECTION
            base_prob += 0.05
        elif abs(frequency - 440) < 10:  # Distortion zone
            base_prob -= 0.05
        
        # *** COSMIC INTEGRATION ***
        # Boost probability based on cosmic coherence
        cosmic_coherence = gate_details['cosmic']['coherence']
        cosmic_boost = gate_details['cosmic']['boost']
        earth_coherence = gate_details['earth']['coherence']
        
        # Cosmic coherence boost (up to +0.1)
        base_prob += cosmic_coherence * 0.10
        
        # Earth coherence boost (up to +0.05)
        base_prob += earth_coherence * 0.05
        
        # Distortion penalty
        distortion = gate_details['cosmic']['distortion']
        base_prob -= distortion * 0.15
        
        # Clamp probability
        bullish_prob = max(0.15, min(0.85, base_prob))
        
        # ═══════════════════════════════════════════════════════════════
        # CONFIDENCE CALCULATION
        # ═══════════════════════════════════════════════════════════════
        
        momentum_consistency = 1.0 - min(1.0, np.std(momentums) * 3)
        
        confidence = (
            momentum_consistency * 0.30 +      # Momentum stability
            cosmic_coherence * 0.25 +          # Cosmic alignment
            earth_coherence * 0.20 +           # Earth resonance
            (0.15 if is_harmonic else 0.0) +   # Harmonic state
            (1 - distortion) * 0.10            # Low distortion bonus
        )
        
        # ═══════════════════════════════════════════════════════════════
        # PRICE PROJECTION (60 seconds ahead)
        # ═══════════════════════════════════════════════════════════════
        
        # Project momentum with decay
        decay = 0.6
        projected_momentum = avg_momentum * decay + recent_momentum * (1 - decay)
        
        # Trend direction boost
        if momentum_trend > 0:
            projected_momentum *= 1.15
        elif momentum_trend < 0:
            projected_momentum *= 0.85
        
        # Cosmic boost to projection
        projected_momentum *= cosmic_boost
        
        # Calculate projected change over 60 seconds
        # Each snapshot is 0.5s, so 60s = 120 snapshots worth
        time_factor = 60 / 0.5  # Number of intervals in 60s
        total_change_pct = projected_momentum * time_factor * 0.01  # Dampen
        
        forecast_price = current_price * (1 + total_change_pct / 100)
        price_change_pct = ((forecast_price - current_price) / current_price) * 100
        
        # ═══════════════════════════════════════════════════════════════
        # TRADE DECISION
        # ═══════════════════════════════════════════════════════════════
        
        # Calculate minimum required change for profit
        fees_pct = FEE_RATE * 2 * 100  # Round trip fees as %
        min_change_pct = fees_pct + (MIN_PROFIT_ABOVE_FEES * 100)
        
        should_trade = False
        reason = ""
        action = "HOLD"
        
        # Check gates
        if not gate_details['all_open']:
            reason = "Cosmic gates CLOSED"
            if not gate_details['earth']['open']:
                reason += f" | Earth: coherence={gate_details['earth']['coherence']:.1%}"
            if not gate_details['cosmic']['open']:
                reason += f" | Cosmic: {gate_details['cosmic']['phase']}"
        elif bullish_prob < MIN_PROBABILITY:
            reason = f"Probability {bullish_prob:.1%} < {MIN_PROBABILITY:.0%} minimum"
        elif confidence < MIN_CONFIDENCE:
            reason = f"Confidence {confidence:.1%} < {MIN_CONFIDENCE:.0%} minimum"
        elif price_change_pct < min_change_pct:
            reason = f"Projected change {price_change_pct:.3f}% < {min_change_pct:.3f}% minimum"
        else:
            should_trade = True
            action = "BUY"
            reason = f"All systems GO | Prob={bullish_prob:.1%} | Conf={confidence:.1%}"
        
        # Position multiplier
        position_mult = (
            gate_details['earth']['phi_boost'] *    # Earth PHI (1.0-1.618)
            cosmic_boost *                           # Cosmic phase (0.5-1.5)
            gate_details['planetary_torque']        # Calendar torque
        )
        
        # Expected profit
        expected_profit = max(0, price_change_pct - fees_pct) if should_trade else 0
        
        return IntegratedForecast(
            symbol=symbol,
            timestamp=datetime.now(),
            
            earth_gate_open=gate_details['earth']['open'],
            earth_coherence=gate_details['earth']['coherence'],
            earth_phi_boost=gate_details['earth']['phi_boost'],
            cosmic_gate_open=gate_details['cosmic']['open'],
            cosmic_phase=gate_details['cosmic']['phase'],
            cosmic_boost=cosmic_boost,
            planetary_torque=gate_details['planetary_torque'],
            
            current_price=current_price,
            forecast_price=forecast_price,
            price_change_pct=price_change_pct,
            bullish_probability=bullish_prob,
            confidence=confidence,
            frequency=frequency,
            is_harmonic=is_harmonic,
            
            should_trade=should_trade,
            reason=reason,
            recommended_action=action,
            position_multiplier=position_mult,
            expected_profit_pct=expected_profit,
        )
    
    def print_forecast(self, f: IntegratedForecast):
        """Print formatted forecast"""
        print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║  🌳 INTEGRATED FORECAST: {f.symbol:12s}                              ║
║  Time: {f.timestamp.strftime('%Y-%m-%d %H:%M:%S')}                                       ║
╠══════════════════════════════════════════════════════════════════════╣
║  COSMIC GATES                                                        ║
║  ├─ 🌍 Earth Gate:   {'OPEN ✅' if f.earth_gate_open else 'CLOSED ❌':10s} (Coherence: {f.earth_coherence:.1%})    ║
║  ├─ ⚡ Cosmic Gate:  {'OPEN ✅' if f.cosmic_gate_open else 'CLOSED ❌':10s} (Phase: {f.cosmic_phase:12s})    ║
║  ├─ 🌙 Planetary:    Torque = {f.planetary_torque:.2f}x                              ║
║  └─ 📊 Combined:     PHI={f.earth_phi_boost:.3f} × Cosmic={f.cosmic_boost:.1f}x           ║
╠══════════════════════════════════════════════════════════════════════╣
║  60-SECOND FORECAST                                                  ║
║  ├─ Current Price:   ${f.current_price:.6f}                                 ║
║  ├─ Forecast Price:  ${f.forecast_price:.6f} ({f.price_change_pct:+.3f}%)               ║
║  ├─ Frequency:       {f.frequency:.1f}Hz {'🎵 HARMONIC' if f.is_harmonic else '⚡ NEUTRAL':20s}          ║
║  ├─ Bullish Prob:    {f.bullish_probability:.1%}                                          ║
║  └─ Confidence:      {f.confidence:.1%}                                          ║
╠══════════════════════════════════════════════════════════════════════╣
║  DECISION                                                            ║
║  ├─ Action:          {f.recommended_action:10s}                                    ║
║  ├─ Should Trade:    {'YES ✅' if f.should_trade else 'NO ❌':10s}                                    ║
║  ├─ Position Mult:   {f.position_multiplier:.2f}x                                        ║
║  ├─ Expected Profit: {f.expected_profit_pct:.3f}%                                       ║
║  └─ Reason:          {f.reason[:50]:50s}   ║
╚══════════════════════════════════════════════════════════════════════╝""")
    
    def execute_trade(self, forecast: IntegratedForecast, base_amount: float = 10.0) -> Tuple[bool, float]:
        """
        LAYER 3: Execute trade based on forecast.
        """
        if not forecast.should_trade:
            print(f"\n   ⏸️ Trade not executed: {forecast.reason}")
            return False, 0
        
        symbol = forecast.symbol
        position_size = base_amount * forecast.position_multiplier
        
        # Calculate quantity
        quantity = position_size / forecast.current_price
        
        # Apply lot size rules
        if 'ADA' in symbol:
            quantity = round(quantity, 1)
        elif 'DOGE' in symbol or 'XLM' in symbol:
            quantity = int(quantity)
        else:
            quantity = round(quantity, 6)
        
        actual_value = quantity * forecast.current_price
        
        print(f"\n💰 EXECUTING TRADE")
        print(f"   Symbol: {symbol}")
        print(f"   Position: ${position_size:.2f} → {quantity} units")
        print(f"   Entry: ${forecast.current_price:.6f}")
        print(f"   Target: ${forecast.forecast_price:.6f}")
        
        # BUY
        print(f"\n   📈 BUYING...")
        try:
            buy_result = self.client.place_market_order(symbol, 'BUY', quantity)
            if buy_result.get('rejected') or not buy_result.get('orderId'):
                print(f"   ❌ Buy failed: {buy_result}")
                return False, 0
            print(f"   ✅ Buy Order ID: {buy_result.get('orderId')}")
        except Exception as e:
            print(f"   ❌ Buy error: {e}")
            return False, 0
        
        entry_price = forecast.current_price
        target_price = forecast.forecast_price
        
        # Monitor for 60 seconds
        print(f"\n   ⏳ Monitoring 60 seconds (target: ${target_price:.6f})...")
        
        for i in range(30):  # 30 × 2s = 60s
            time.sleep(2)
            current = self._get_price(symbol)
            pct = ((current - entry_price) / entry_price) * 100
            
            bar = "█" * int(abs(pct) * 20) if pct != 0 else ""
            status = "📈" if pct > 0 else "📉" if pct < 0 else "➡️"
            
            print(f"   {status} {(i+1)*2:2d}s | ${current:.6f} | {pct:+.3f}% {bar}")
            
            if current >= target_price:
                print(f"   🎯 TARGET REACHED!")
                break
        
        # SELL
        final_price = self._get_price(symbol)
        print(f"\n   📉 SELLING...")
        try:
            sell_result = self.client.place_market_order(symbol, 'SELL', quantity)
            if not sell_result.get('orderId'):
                print(f"   ❌ Sell failed: {sell_result}")
                # Still calculate P&L with current price
        except Exception as e:
            print(f"   ❌ Sell error: {e}")
        
        print(f"   ✅ Sell Order ID: {sell_result.get('orderId', 'N/A')}")
        
        # Calculate P&L
        gross_pnl = (final_price - entry_price) * quantity
        fees = (entry_price * quantity + final_price * quantity) * FEE_RATE
        net_pnl = gross_pnl - fees
        
        print(f"\n   {'='*50}")
        print(f"   📊 TRADE RESULT")
        print(f"   ├─ Entry:     ${entry_price:.6f}")
        print(f"   ├─ Exit:      ${final_price:.6f}")
        print(f"   ├─ Target:    ${target_price:.6f}")
        print(f"   ├─ Gross P&L: ${gross_pnl:+.6f}")
        print(f"   ├─ Fees:      ${fees:.6f}")
        if net_pnl > 0:
            print(f"   └─ ✅ NET PROFIT: ${net_pnl:+.6f}")
        else:
            print(f"   └─ ❌ NET LOSS:   ${net_pnl:+.6f}")
        print(f"   {'='*50}")
        
        return net_pnl > 0, net_pnl
    
    def run_integrated_trade(self, symbol: str, base_amount: float = 10.0) -> Tuple[bool, float]:
        """
        Complete integrated trade flow:
        1. Check cosmic gates
        2. Collect price data
        3. Generate forecast
        4. Execute if all systems align
        """
        print(f"\n{'='*70}")
        print(f"🌳🎯 INTEGRATED FORECAST TRADE: {symbol}")
        print(f"{'='*70}")
        
        # LAYER 1: Check cosmic gates
        print(f"\n📡 LAYER 1: CHECKING COSMIC GATES...")
        gates_open, gate_details = self.check_cosmic_gates()
        
        print(f"   🌍 Earth Gate: {'OPEN ✅' if gate_details['earth']['open'] else 'CLOSED ❌'}")
        print(f"      Coherence: {gate_details['earth']['coherence']:.1%}")
        print(f"      Phase Lock: {gate_details['earth']['phase_lock']:.1%}")
        print(f"      PHI Boost: {gate_details['earth']['phi_boost']:.3f}x")
        
        print(f"   ⚡ Cosmic Gate: {'OPEN ✅' if gate_details['cosmic']['open'] else 'CLOSED ❌'}")
        print(f"      Phase: {gate_details['cosmic']['phase']}")
        print(f"      Boost: {gate_details['cosmic']['boost']:.1f}x")
        print(f"      Distortion: {gate_details['cosmic']['distortion']:.4f}")
        
        print(f"   🌙 Planetary Torque: {gate_details['planetary_torque']:.2f}x")
        
        if not gates_open:
            print(f"\n   ❌ COSMIC GATES NOT ALIGNED - Skipping trade")
            return False, 0
        
        print(f"\n   ✅ ALL COSMIC GATES OPEN")
        
        # LAYER 2: Collect price data
        print(f"\n📊 LAYER 2: COLLECTING PRICE DATA (30s)...")
        snapshots = self._collect_price_data(symbol, duration_sec=30)
        
        if len(snapshots) < 20:
            print(f"   ❌ Insufficient data")
            return False, 0
        
        print(f"   ✅ Collected {len(snapshots)} price snapshots")
        
        # Generate forecast
        print(f"\n🔮 LAYER 2: GENERATING 60-SECOND FORECAST...")
        forecast = self.generate_forecast(symbol, snapshots, gate_details)
        
        if not forecast:
            print(f"   ❌ Could not generate forecast")
            return False, 0
        
        self.print_forecast(forecast)
        
        # LAYER 3: Execute if should trade
        if forecast.should_trade:
            print(f"\n🎯 LAYER 3: EXECUTING TRADE...")
            return self.execute_trade(forecast, base_amount)
        else:
            print(f"\n⏸️ LAYER 3: NO TRADE - {forecast.reason}")
            return False, 0


def main():
    print("\n" + "="*70)
    print("🌳🎯 AUREON INTEGRATED FORECAST TRADER 🎯🌳")
    print("="*70)
    print("\n⚡ This script uses ALL prediction systems:")
    print("   • Earth Resonance Engine (cosmic gate)")
    print("   • Imperial Predictability Engine (cosmic state)")
    print("   • HNC Probability Matrix (60s forecast)")
    print("\n   Trades ONLY execute when ALL systems align.")
    
    confirm = input("\n   Type 'FORECAST' to begin: ")
    if confirm != 'FORECAST':
        print("\n   ❌ Cancelled.")
        return
    
    # Initialize
    trader = IntegratedForecastTrader()
    
    # Test symbols (UK allowed USDC pairs)
    symbols = ['ADAUSDC', 'XLMUSDC', 'DOGEUSDC']
    
    # Check which symbols can trade
    print("\n📋 Checking tradeable symbols...")
    tradeable = []
    for sym in symbols:
        can, reason = trader.client.can_trade_symbol(sym)
        print(f"   {sym}: {'✅' if can else '❌'} {reason}")
        if can:
            tradeable.append(sym)
    
    if not tradeable:
        print("\n   ❌ No tradeable symbols found")
        return
    
    # Execute trades
    results = []
    total_pnl = 0
    max_attempts = 6
    
    print(f"\n🎯 Attempting up to {max_attempts} integrated forecast trades...")
    
    for attempt in range(max_attempts):
        if len([r for r in results if r[1]]) >= 3:
            print(f"\n   ✅ 3 profitable trades completed!")
            break
        
        for symbol in tradeable:
            if len([r for r in results if r[1]]) >= 3:
                break
            
            success, pnl = trader.run_integrated_trade(symbol, base_amount=10.0)
            results.append((symbol, success, pnl))
            total_pnl += pnl
            
            if not success and pnl == 0:
                # No trade executed, wait before next attempt
                print(f"\n   ⏳ Waiting 30s for market conditions to change...")
                time.sleep(30)
    
    # Final Summary
    print("\n" + "="*70)
    print("📊 FINAL RESULTS")
    print("="*70)
    
    trades_executed = sum(1 for _, s, p in results if p != 0)
    wins = sum(1 for _, s, _ in results if s)
    
    print(f"\n   Attempts:  {len(results)}")
    print(f"   Executed:  {trades_executed}")
    print(f"   Profitable: {wins}")
    print(f"   Total P&L: ${total_pnl:+.6f}")
    
    if total_pnl > 0:
        print("\n   🎉 OVERALL NET PROFIT! 🎉")
    elif trades_executed == 0:
        print("\n   ⏸️ No trades executed - conditions not met")
    else:
        print("\n   📉 Overall loss - market conditions unfavorable")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
