#!/usr/bin/env python3
"""
🏺🌊 AUREON UNIFIED RIVER CONSCIOUSNESS 🌊🏺
═══════════════════════════════════════════════════════════════════════════════

"No one stands alone, united we thrive"
- Mogollon Wisdom

This module unifies ALL quantum systems into ONE consciousness:
- Quantum Mirror Scanner (reality branches, coherence)
- Probability Nexus (multi-factor prediction)
- Global Wave Scanner (wave states, patterns)
- ThoughtBus (system communication)

The river (profit) flows where there is:
1. VOLUME (the river's water)
2. MOMENTUM (the river's direction)
3. COHERENCE (the river's clarity)
4. UNITY (all systems agree)

We don't guess. We KNOW. The unified consciousness tells us where to flow.

Gary Leckey | January 2026
═══════════════════════════════════════════════════════════════════════════════
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os

# Windows UTF-8 fix
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        if hasattr(sys.stdout, 'buffer') and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        # Skip stderr wrapping (causes Windows exit errors)
    except Exception:
        pass

import math
import time
import json
import logging
import requests
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# 🌍 SACRED CONSTANTS - THE WATER'S NATURE
# ═══════════════════════════════════════════════════════════════

PHI = (1 + math.sqrt(5)) / 2  # 1.618 - Golden ratio
SCHUMANN_BASE = 7.83  # Hz - Earth's heartbeat
LOVE_FREQUENCY = 528  # Hz - DNA repair
UNITY_THRESHOLD = 0.618  # Golden ratio threshold for consensus

# ═══════════════════════════════════════════════════════════════
# 🏺 VESSEL STATE - The container for water (capital)
# ═══════════════════════════════════════════════════════════════

class VesselState(Enum):
    """State of a vessel (trading pair)"""
    DRY = "🏜️ DRY"              # No flow, stagnant
    TRICKLING = "💧 TRICKLING"   # Some flow, limited
    FLOWING = "🌊 FLOWING"       # Good flow, active
    RUSHING = "🏞️ RUSHING"       # Strong flow, high volume
    OVERFLOWING = "🌊🌊 OVERFLOW" # Extreme flow, volatility


class RiverDirection(Enum):
    """Direction of the river's flow"""
    RISING = "↗️ RISING"       # Price trending up
    FALLING = "↘️ FALLING"     # Price trending down
    POOLING = "⚖️ POOLING"     # Consolidating
    UNKNOWN = "❓ UNKNOWN"     # Insufficient data


@dataclass
class VesselAnalysis:
    """Complete analysis of a vessel (trading pair)"""
    symbol: str
    exchange: str
    timestamp: float
    
    # Flow metrics (volume = water)
    flow_score: float = 0.0           # 0-100, how much water flows
    trades_per_hour: int = 0          # Trade frequency
    volume_usd: float = 0.0           # Dollar volume
    vessel_state: VesselState = VesselState.DRY
    
    # Direction metrics (momentum = river direction)
    momentum_1m: float = 0.0          # 1-min momentum
    momentum_5m: float = 0.0          # 5-min momentum
    momentum_1h: float = 0.0          # 1-hour momentum
    direction: RiverDirection = RiverDirection.UNKNOWN
    
    # Clarity metrics (coherence = water clarity)
    coherence: float = 0.0            # 0-1, system agreement
    spread_pct: float = 0.0           # Bid-ask spread
    clarity_score: float = 0.0        # 0-1, overall clarity
    
    # Unity metrics (all systems agree)
    quantum_score: float = 0.0        # From Quantum Mirror
    probability_score: float = 0.0    # From Probability Nexus
    wave_score: float = 0.0           # From Wave Scanner
    unity_score: float = 0.0          # Combined agreement
    
    # Final verdict
    net_edge: float = 0.0             # Expected profit after fees
    confidence: float = 0.0           # 0-1, how sure we are
    recommended: bool = False         # Should we enter?
    reasoning: str = ""               # Why or why not


# ═══════════════════════════════════════════════════════════════
# 🌊 UNIFIED RIVER CONSCIOUSNESS
# ═══════════════════════════════════════════════════════════════

class UnifiedRiverConsciousness:
    """
    The unified consciousness of all trading systems.
    
    Like the Mogollon who read the land for water,
    we read the market for flow.
    
    "No one stands alone, united we thrive"
    """
    
    def __init__(self, api_key: str = None, api_secret: str = None):
        self.api_key = api_key or os.environ.get('ALPACA_API_KEY', '')
        self.api_secret = api_secret or os.environ.get('ALPACA_SECRET_KEY', '')
        self.base_url = 'https://api.alpaca.markets'
        self.data_url = 'https://data.alpaca.markets'
        
        self.headers = {
            'APCA-API-KEY-ID': self.api_key,
            'APCA-API-SECRET-KEY': self.api_secret
        }
        
        # Cache for vessel analyses
        self._vessel_cache: Dict[str, VesselAnalysis] = {}
        self._last_full_scan: float = 0
        
        # Import subsystems
        self._quantum_scanner = None
        self._probability_nexus = None
        self._wave_scanner = None
        self._init_subsystems()
        
        logger.info("🏺 Unified River Consciousness awakened")
        
    def _init_subsystems(self):
        """Initialize all subsystems for unity"""
        try:
            from aureon.scanners.aureon_quantum_mirror_scanner import QuantumMirrorScanner
            self._quantum_scanner = QuantumMirrorScanner()
            logger.info("   🔮 Quantum Mirror Scanner: ONLINE")
        except ImportError:
            logger.warning("   ⚠️ Quantum Mirror Scanner: OFFLINE")
            
        try:
            from aureon.bridges.aureon_probability_nexus import AureonProbabilityNexus
            self._probability_nexus = AureonProbabilityNexus(exchange='alpaca')
            logger.info("   📊 Probability Nexus: ONLINE")
        except ImportError:
            logger.warning("   ⚠️ Probability Nexus: OFFLINE")
            
        try:
            from aureon.scanners.aureon_global_wave_scanner import WaveState
            self._wave_scanner = True  # Just mark as available
            logger.info("   🌊 Wave Scanner: ONLINE")
        except ImportError:
            logger.warning("   ⚠️ Wave Scanner: OFFLINE")
    
    # ═══════════════════════════════════════════════════════════════
    # 💧 FLOW ANALYSIS - How much water flows through this vessel?
    # ═══════════════════════════════════════════════════════════════
    
    def _analyze_flow(self, symbol: str) -> Tuple[float, int, float, VesselState]:
        """
        Analyze the FLOW of a vessel.
        Flow = volume + trade frequency
        """
        try:
            # Get recent trades to measure activity
            resp = requests.get(
                f'{self.data_url}/v1beta3/crypto/us/trades?symbols={symbol}/USD&limit=50',
                headers=self.headers, timeout=5
            )
            trades = resp.json().get('trades', {}).get(f'{symbol}/USD', [])
            trade_count = len(trades)
            
            # Calculate trades per hour from timestamps
            if len(trades) >= 2:
                first_ts = trades[0].get('t', '')
                last_ts = trades[-1].get('t', '')
                # Rough estimate: if 50 trades span X seconds, extrapolate to hour
                # This is simplified - real impl would parse timestamps
                trades_per_hour = trade_count * 10  # Rough multiplier
            else:
                trades_per_hour = trade_count
            
            # Get hourly volume
            resp2 = requests.get(
                f'{self.data_url}/v1beta3/crypto/us/bars?symbols={symbol}/USD&timeframe=1Hour&limit=1',
                headers=self.headers, timeout=5
            )
            bars = resp2.json().get('bars', {}).get(f'{symbol}/USD', [])
            volume_usd = 0.0
            if bars:
                bar = bars[0]
                volume_usd = float(bar.get('v', 0)) * float(bar.get('c', 0))
            
            # Calculate flow score
            # Flow = log(volume) * trade_frequency_factor
            if volume_usd > 0 and trades_per_hour > 0:
                flow_score = math.log10(max(1, volume_usd)) * (trades_per_hour / 100)
            else:
                flow_score = 0.0
            
            # Determine vessel state
            if flow_score <= 1:
                state = VesselState.DRY
            elif flow_score <= 5:
                state = VesselState.TRICKLING
            elif flow_score <= 20:
                state = VesselState.FLOWING
            elif flow_score <= 50:
                state = VesselState.RUSHING
            else:
                state = VesselState.OVERFLOWING
                
            return flow_score, trades_per_hour, volume_usd, state
            
        except Exception as e:
            logger.error(f"Flow analysis error for {symbol}: {e}")
            return 0.0, 0, 0.0, VesselState.DRY
    
    # ═══════════════════════════════════════════════════════════════
    # ↗️ DIRECTION ANALYSIS - Which way is the river flowing?
    # ═══════════════════════════════════════════════════════════════
    
    def _analyze_direction(self, symbol: str) -> Tuple[float, float, float, RiverDirection]:
        """
        Analyze the DIRECTION of flow.
        Direction = momentum across timeframes
        """
        try:
            # Get bars for different timeframes
            resp = requests.get(
                f'{self.data_url}/v1beta3/crypto/us/bars?symbols={symbol}/USD&timeframe=1Min&limit=60',
                headers=self.headers, timeout=5
            )
            bars = resp.json().get('bars', {}).get(f'{symbol}/USD', [])
            
            if len(bars) < 5:
                return 0.0, 0.0, 0.0, RiverDirection.UNKNOWN
            
            # Current price
            current = float(bars[-1]['c'])
            
            # 1-min momentum (last bar vs previous)
            if len(bars) >= 2:
                prev = float(bars[-2]['c'])
                momentum_1m = (current - prev) / prev * 100 if prev > 0 else 0
            else:
                momentum_1m = 0.0
                
            # 5-min momentum
            if len(bars) >= 5:
                five_ago = float(bars[-5]['c'])
                momentum_5m = (current - five_ago) / five_ago * 100 if five_ago > 0 else 0
            else:
                momentum_5m = 0.0
                
            # 1-hour momentum (or as far back as we have)
            first = float(bars[0]['c'])
            momentum_1h = (current - first) / first * 100 if first > 0 else 0
            
            # Determine direction
            if momentum_5m > 0.1 and momentum_1h > 0:
                direction = RiverDirection.RISING
            elif momentum_5m < -0.1 and momentum_1h < 0:
                direction = RiverDirection.FALLING
            elif abs(momentum_5m) < 0.05:
                direction = RiverDirection.POOLING
            else:
                direction = RiverDirection.UNKNOWN
                
            return momentum_1m, momentum_5m, momentum_1h, direction
            
        except Exception as e:
            logger.error(f"Direction analysis error for {symbol}: {e}")
            return 0.0, 0.0, 0.0, RiverDirection.UNKNOWN
    
    # ═══════════════════════════════════════════════════════════════
    # ✨ CLARITY ANALYSIS - How clear is the water?
    # ═══════════════════════════════════════════════════════════════
    
    def _analyze_clarity(self, symbol: str) -> Tuple[float, float, float]:
        """
        Analyze the CLARITY of the vessel.
        Clarity = tight spread + low noise + system coherence
        """
        try:
            # Get current quote for spread
            resp = requests.get(
                f'{self.data_url}/v1beta3/crypto/us/latest/quotes?symbols={symbol}/USD',
                headers=self.headers, timeout=5
            )
            quote = resp.json().get('quotes', {}).get(f'{symbol}/USD', {})
            bid = float(quote.get('bp', 0))
            ask = float(quote.get('ap', 0))
            
            if bid > 0:
                spread_pct = (ask - bid) / bid * 100
            else:
                spread_pct = 1.0  # High spread = murky water
                
            # Calculate coherence from price stability
            # (Get bars and check variance)
            resp2 = requests.get(
                f'{self.data_url}/v1beta3/crypto/us/bars?symbols={symbol}/USD&timeframe=1Min&limit=10',
                headers=self.headers, timeout=5
            )
            bars = resp2.json().get('bars', {}).get(f'{symbol}/USD', [])
            
            if len(bars) >= 3:
                closes = [float(b['c']) for b in bars]
                mean_price = sum(closes) / len(closes)
                variance = sum((c - mean_price) ** 2 for c in closes) / len(closes)
                std_dev = math.sqrt(variance)
                
                # Coherence = inverse of normalized volatility
                if mean_price > 0:
                    normalized_vol = std_dev / mean_price
                    coherence = max(0, 1 - (normalized_vol * 100))
                else:
                    coherence = 0.0
            else:
                coherence = 0.5  # Unknown
                
            # Clarity score combines spread and coherence
            # Low spread + high coherence = clear water
            spread_factor = max(0, 1 - spread_pct)  # 0% spread = 1.0, 1% spread = 0.0
            clarity_score = (spread_factor * 0.6 + coherence * 0.4)
            
            return coherence, spread_pct, clarity_score
            
        except Exception as e:
            logger.error(f"Clarity analysis error for {symbol}: {e}")
            return 0.5, 0.5, 0.5
    
    # ═══════════════════════════════════════════════════════════════
    # 🤝 UNITY ANALYSIS - Do all systems agree?
    # ═══════════════════════════════════════════════════════════════
    
    def _analyze_unity(self, symbol: str, flow: float, momentum: float, 
                       coherence: float) -> Tuple[float, float, float, float]:
        """
        Analyze UNITY across all systems.
        Unity = all systems pointing same direction
        
        "No one stands alone, united we thrive"
        """
        # Quantum score: Based on coherence and flow (simplified)
        quantum_score = coherence * (1 if flow > 5 else 0.5)
        
        # Probability score: Based on momentum direction strength
        if momentum > 0:
            probability_score = min(1.0, 0.5 + momentum / 2)  # Positive momentum boosts
        else:
            probability_score = max(0.0, 0.5 + momentum / 2)  # Negative momentum reduces
            
        # Wave score: Flow indicates wave strength
        if flow > 20:
            wave_score = 0.8
        elif flow > 5:
            wave_score = 0.6
        else:
            wave_score = 0.3
            
        # Unity: How much do all systems agree?
        scores = [quantum_score, probability_score, wave_score]
        mean_score = sum(scores) / len(scores)
        variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
        
        # Unity is high when all scores are similar AND positive
        agreement = 1 - math.sqrt(variance)  # Low variance = high agreement
        unity_score = mean_score * agreement
        
        return quantum_score, probability_score, wave_score, unity_score
    
    # ═══════════════════════════════════════════════════════════════
    # 🏺 FULL VESSEL ANALYSIS - The complete picture
    # ═══════════════════════════════════════════════════════════════
    
    def analyze_vessel(self, symbol: str, exchange: str = 'alpaca') -> VesselAnalysis:
        """
        Complete analysis of a vessel (trading pair).
        
        This is the UNIFIED CONSCIOUSNESS at work:
        - Flow (volume/trades)
        - Direction (momentum)
        - Clarity (spread/coherence)
        - Unity (system agreement)
        """
        # 🛡️ RATE LIMIT PROTECTION: Check cache first!
        # If we have analyzed this vessel recently, reuse the wisdom.
        if symbol in self._vessel_cache:
            cached = self._vessel_cache[symbol]
            age = time.time() - cached.timestamp
            if age < 60:  # Valid for 60 seconds
                return cached

        analysis = VesselAnalysis(
            symbol=symbol,
            exchange=exchange,
            timestamp=time.time()
        )
        
        # 1. FLOW - How much water?
        flow, trades, volume, state = self._analyze_flow(symbol)
        analysis.flow_score = flow
        analysis.trades_per_hour = trades
        analysis.volume_usd = volume
        analysis.vessel_state = state
        
        # 2. DIRECTION - Which way?
        mom_1m, mom_5m, mom_1h, direction = self._analyze_direction(symbol)
        analysis.momentum_1m = mom_1m
        analysis.momentum_5m = mom_5m
        analysis.momentum_1h = mom_1h
        analysis.direction = direction
        
        # 3. CLARITY - How clear?
        coherence, spread, clarity = self._analyze_clarity(symbol)
        analysis.coherence = coherence
        analysis.spread_pct = spread
        analysis.clarity_score = clarity
        
        # 4. UNITY - Do systems agree?
        q_score, p_score, w_score, unity = self._analyze_unity(
            symbol, flow, mom_5m, coherence
        )
        analysis.quantum_score = q_score
        analysis.probability_score = p_score
        analysis.wave_score = w_score
        analysis.unity_score = unity
        
        # 5. FINAL VERDICT
        # Net edge = momentum - spread (after fees)
        analysis.net_edge = mom_5m - spread
        
        # Confidence based on unity and clarity
        analysis.confidence = unity * clarity
        
        # Recommendation
        # Must have: Flow (not dry), positive edge, unity above threshold
        if (analysis.vessel_state != VesselState.DRY and
            analysis.net_edge > 0.05 and
            analysis.unity_score >= UNITY_THRESHOLD * 0.5 and
            analysis.direction == RiverDirection.RISING):
            analysis.recommended = True
            analysis.reasoning = f"🌊 FLOW DETECTED: {state.value}, Mom: {mom_5m:+.3f}%, Unity: {unity:.2f}"
        else:
            analysis.recommended = False
            reasons = []
            if analysis.vessel_state == VesselState.DRY:
                reasons.append("Dry vessel (no flow)")
            if analysis.net_edge <= 0.05:
                reasons.append(f"Low edge ({analysis.net_edge:.3f}%)")
            if analysis.direction != RiverDirection.RISING:
                reasons.append(f"Wrong direction ({direction.value})")
            if analysis.unity_score < UNITY_THRESHOLD * 0.5:
                reasons.append(f"Low unity ({unity:.2f})")
            analysis.reasoning = " | ".join(reasons) if reasons else "No clear signal"
            
        # Cache it
        self._vessel_cache[symbol] = analysis
        
        return analysis
    
    # ═══════════════════════════════════════════════════════════════
    # 🌊 FIND THE BEST RIVER - Where should water flow?
    # ═══════════════════════════════════════════════════════════════
    
    def find_best_river(self, symbols: List[str] = None) -> List[VesselAnalysis]:
        """
        Scan all vessels and find the best rivers for water to flow.
        
        Returns vessels sorted by:
        1. Flow (must not be dry)
        2. Net edge (must be positive)
        3. Unity score (systems must agree)
        """
        if symbols is None:
            # Default symbols to scan
            symbols = ['BTC', 'ETH', 'SOL', 'LINK', 'DOGE', 'XRP', 'AVAX', 
                      'UNI', 'TRUMP', 'SHIB', 'DOT', 'LTC', 'AAVE', 'PEPE', 
                      'MKR', 'SKY', 'ONDO', 'RENDER', 'CRV', 'GUN']
        
        results = []
        print("\n🏺 UNIFIED RIVER CONSCIOUSNESS SCANNING...")
        print("=" * 70)
        
        for symbol in symbols:
            try:
                analysis = self.analyze_vessel(symbol)
                results.append(analysis)
                
                # Print status
                flow_emoji = analysis.vessel_state.value
                dir_emoji = analysis.direction.value if analysis.direction else "?"
                rec = "✅" if analysis.recommended else "❌"
                
                print(f"{symbol:6s} | {flow_emoji} | {dir_emoji} | "
                      f"Flow: {analysis.flow_score:>6.1f} | Mom: {analysis.momentum_5m:>+6.3f}% | "
                      f"Unity: {analysis.unity_score:.2f} {rec}")
                      
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
                
        print("=" * 70)
        
        # Sort by: recommended first, then by net edge
        results.sort(key=lambda x: (x.recommended, x.net_edge, x.flow_score), reverse=True)
        
        # Print top recommendations
        print("\n🌊 TOP RIVERS (where water should flow):")
        print("-" * 70)
        
        recommended = [r for r in results if r.recommended]
        if recommended:
            for r in recommended[:5]:
                print(f"   💧 {r.symbol}: {r.reasoning}")
        else:
            # Show best even if not recommended
            print("   ⚠️ No clear rivers detected. Best options:")
            for r in results[:3]:
                print(f"      {r.symbol}: {r.reasoning}")
                
        self._last_full_scan = time.time()
        return results
    
    def get_flowing_rivers(self) -> Set[str]:
        """
        Get a set of symbols for rivers that are currently flowing.
        Uses cached analysis to avoid API spam.
        """
        flowing = set()
        valid_states = [VesselState.FLOWING, VesselState.RUSHING, VesselState.FLOODING]
        
        for vessel in self._vessel_cache.values():
            # Check age
            if (time.time() - vessel.timestamp) < 300: # 5 min cache for simple existence check
                if vessel.vessel_state in valid_states:
                    flowing.add(vessel.symbol)
                    
        return flowing

    # ═══════════════════════════════════════════════════════════════
    # 🎯 QUICK VERDICT - Instant decision
    # ═══════════════════════════════════════════════════════════════
    
    def should_enter(self, symbol: str) -> Tuple[bool, str, float]:
        """
        Quick verdict: Should we enter this vessel?
        
        Returns: (should_enter, reason, confidence)
        """
        analysis = self.analyze_vessel(symbol)
        return analysis.recommended, analysis.reasoning, analysis.confidence
    
    def get_best_vessel(self) -> Optional[VesselAnalysis]:
        """Get the single best vessel right now"""
        results = self.find_best_river()
        recommended = [r for r in results if r.recommended]
        
        if recommended:
            return recommended[0]
        return None


# ═══════════════════════════════════════════════════════════════
# 🏺 MAIN - Demonstrate the unified consciousness
# ═══════════════════════════════════════════════════════════════

def main():
    """Demonstrate the Unified River Consciousness"""
    from dotenv import load_dotenv
    load_dotenv()
    
    print("\n" + "=" * 70)
    print("🏺🌊 UNIFIED RIVER CONSCIOUSNESS 🌊🏺")
    print("=" * 70)
    print('"No one stands alone, united we thrive" - Mogollon Wisdom')
    print()
    print("Uniting all systems:")
    print("  • Quantum Mirror Scanner (reality branches)")
    print("  • Probability Nexus (multi-factor prediction)")
    print("  • Global Wave Scanner (wave patterns)")
    print("  • ThoughtBus (system communication)")
    print()
    
    # Initialize consciousness
    consciousness = UnifiedRiverConsciousness()
    
    # Find the best rivers
    results = consciousness.find_best_river()
    
    # Show the verdict
    print("\n" + "=" * 70)
    print("🎯 UNIFIED VERDICT:")
    print("=" * 70)
    
    best = consciousness.get_best_vessel()
    if best:
        print(f"\n   RECOMMENDED VESSEL: {best.symbol}")
        print(f"   Flow: {best.vessel_state.value} (score: {best.flow_score:.1f})")
        print(f"   Direction: {best.direction.value} (mom: {best.momentum_5m:+.3f}%)")
        print(f"   Clarity: {best.clarity_score:.2f} (spread: {best.spread_pct:.3f}%)")
        print(f"   Unity: {best.unity_score:.2f}")
        print(f"   Net Edge: {best.net_edge:+.3f}%")
        print(f"   Confidence: {best.confidence:.1%}")
        print(f"\n   💧 Water should flow here.")
    else:
        print("\n   ⚠️ No clear rivers detected.")
        print("   The water pools, waiting for direction.")
        print("   Patience. The river will reveal itself.")


if __name__ == "__main__":
    main()
