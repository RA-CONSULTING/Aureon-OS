#!/usr/bin/env python3
"""
🍄 MYCELIUM SPORE BRANCHING TEST 🍄
═══════════════════════════════════════════════════════════════
Tests the complete stem→spore→germination reality branching flow
with live ticker data to verify substrate pattern mapping.

Flow:
1. Fetch live market data (historical stem)
2. Create RealityStem from historical data
3. Run quick Monte Carlo simulation (spore projection)
4. Project spore into Stargate Protocol
5. Verify full lineage tracking through validation cycle
═══════════════════════════════════════════════════════════════
"""

from aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
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
            sys.stdout = sys.stdout if 'pytest' in sys.modules else io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

import time
import json
from typing import Dict, List
from dataclasses import asdict

# Import our systems
try:
    from aureon_stargate_protocol import (
        create_stargate_engine, 
        RealityStem, 
        spawn_spore_mirror,
        TimelinePhase
    )
    STARGATE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Stargate Protocol not available: {e}")
    STARGATE_AVAILABLE = False

try:
    from kraken_client import KrakenClient, get_kraken_client
    KRAKEN_AVAILABLE = True
except ImportError:
    print("⚠️ Kraken client not available")
    KRAKEN_AVAILABLE = False

# Sacred constants
PHI = 1.618033988749895
SCHUMANN_BASE = 7.83
LOVE_FREQUENCY = 528.0


def fetch_live_substrate_data(symbol: str = "BTC/USD") -> Dict:
    """
    Fetch live market data to form the substrate (historical stem).
    
    Returns dict with:
    - current_price
    - 24h_change_pct
    - volume
    - momentum
    - volatility
    """
    print(f"\n📊 Fetching live substrate data for {symbol}...")
    
    if not KRAKEN_AVAILABLE:
        print("   Using mock data (Kraken unavailable)")
        return {
            "symbol": symbol,
            "current_price": 104250.0,  # Current BTC price range
            "24h_change_pct": 1.8,
            "volume": 2345678.90,
            "momentum": 0.018,
            "volatility": 0.025,
            "timestamp": time.time()
        }
    
    try:
        client = get_kraken_client()
        ticker = client.get_ticker(symbol)
        
        if not ticker:
            print("   ⚠️ No ticker data received - using mock data")
            return {
                "symbol": symbol,
                "current_price": 104250.0,
                "24h_change_pct": 1.8,
                "volume": 2345678.90,
                "momentum": 0.018,
                "volatility": 0.025,
                "timestamp": time.time()
            }
        
        # Extract substrate features
        current_price = float(ticker.get('last', 0))
        change_24h = float(ticker.get('priceChangePercent', 0))
        volume = float(ticker.get('quoteVolume', 0))
        
        # Fallback if we got zero/invalid data
        if current_price <= 0:
            print("   ⚠️ Invalid price data - using mock data")
            return {
                "symbol": symbol,
                "current_price": 104250.0,
                "24h_change_pct": 1.8,
                "volume": 2345678.90,
                "momentum": 0.018,
                "volatility": 0.025,
                "timestamp": time.time()
            }
        
        data = {
            "symbol": symbol,
            "current_price": current_price,
            "24h_change_pct": change_24h,
            "volume": volume,
            "momentum": change_24h / 100.0,  # Convert to decimal
            "volatility": abs(change_24h) / 100.0,  # Rough volatility estimate
            "timestamp": time.time()
        }
        
        print(f"   ✅ Price: ${current_price:,.2f}")
        print(f"   ✅ 24h Change: {change_24h:+.2f}%")
        print(f"   ✅ Momentum: {data['momentum']:+.4f}")
        
        return data
        
    except Exception as e:
        print(f"   ❌ Error fetching data: {e}")
        return None


def create_reality_stem_from_substrate(substrate: Dict) -> RealityStem:
    """
    Create a RealityStem from live substrate data.
    This represents the "mushroom stem" - historical data flowing up to present.
    """
    print(f"\n🌱 Creating RealityStem from substrate...")
    
    stem = RealityStem(
        stem_id=f"stem::{substrate['symbol']}::{int(substrate['timestamp'])}",
        symbol=substrate['symbol'],
        exchange="kraken",
        lookback_seconds=604800,  # 7 days
        collected_at=substrate['timestamp'],
        notes=f"Live test stem - momentum: {substrate['momentum']:+.4f}"
    )
    
    print(f"   ✅ Stem ID: {stem.stem_id}")
    print(f"   ✅ Symbol: {stem.symbol}")
    print(f"   ✅ Lookback: {stem.lookback_seconds}s (7 days)")
    
    return stem


def simulate_spore_projection(substrate: Dict) -> Dict:
    """
    Simulate a Monte Carlo projection to create spore prediction data.
    This represents the "spore boom" - projecting possible future paths.
    """
    print(f"\n🍄 Simulating spore projection (Monte Carlo)...")
    
    # Quick simulation: Project price movement based on momentum
    base_momentum = substrate['momentum']
    volatility = substrate['volatility']
    
    # Simple projection: assume momentum continues with some noise
    num_simulations = 100
    wins = 0
    total_return = 0.0
    
    for _ in range(num_simulations):
        # Random walk with momentum bias
        import random
        noise = random.gauss(0, volatility)
        projected_return = base_momentum + noise
        
        # Win if projected return > 0.34% (cost threshold)
        if projected_return > 0.0034:
            wins += 1
        total_return += projected_return
    
    win_rate = wins / num_simulations
    expected_value = total_return / num_simulations
    confidence = win_rate if win_rate > 0.5 else (1 - win_rate)
    
    # Determine direction
    direction = "BULLISH" if expected_value > 0 else "BEARISH"
    
    # Create prediction data for spore
    prediction_data = {
        "symbol": substrate['symbol'],
        "direction": direction,
        "probability": win_rate,
        "expected_value": expected_value,
        "confidence": confidence,
        "frequencies": [
            LOVE_FREQUENCY,  # 528 Hz - transformation
            SCHUMANN_BASE * (1 + abs(expected_value)),  # Scale with EV
            432.0  # Gaia resonance
        ]
    }
    
    print(f"   ✅ Direction: {direction}")
    print(f"   ✅ Win Rate: {win_rate:.1%}")
    print(f"   ✅ Expected Value: {expected_value:+.4f}")
    print(f"   ✅ Confidence: {confidence:.3f}")
    print(f"   ✅ Frequencies: {prediction_data['frequencies']}")
    
    return prediction_data


def project_spores_to_stargate(stem: RealityStem, prediction_data: Dict):
    # Pipeline stage, not a pytest test — its old ``test_`` name made pytest inject
    # ``stem``/``prediction_data`` as fixtures and error the module on every run.
    """
    Test projecting the spore into the Stargate Protocol.
    Verify full lineage tracking: stem → spore → quantum mirror.
    """
    print(f"\n🌌 Projecting spore into Stargate Protocol...")
    
    if not STARGATE_AVAILABLE:
        print("   ⚠️ Stargate Protocol unavailable - cannot test projection")
        return
    
    try:
        # Create Stargate engine
        engine = create_stargate_engine(with_integrations=False)
        
        print(f"\n   📡 Stargate Engine Status:")
        print(f"      Planetary Nodes: {len(engine.stargates)}")
        print(f"      Quantum Mirrors: {len(engine.quantum_mirrors)}")
        
        # Project spore from stem
        spore_mirror = engine.project_spore_from_stem(stem, prediction_data)
        
        if not spore_mirror:
            print("   ❌ Failed to create spore mirror")
            return
        
        print(f"\n   ✅ SPORE PROJECTED SUCCESSFULLY!")
        print(f"      Mirror ID: {spore_mirror.mirror_id}")
        print(f"      Spore ID: {spore_mirror.spore_id}")
        print(f"      Stem Source: {spore_mirror.stem_source}")
        print(f"      Projection Confidence: {spore_mirror.projection_confidence:.3f}")
        print(f"      Phase: {spore_mirror.phase.value}")
        print(f"      Coherence: {spore_mirror.coherence_signature:.3f}")
        print(f"      Beneficial Score: {spore_mirror.beneficial_score:.3f}")
        print(f"      Stability Index: {spore_mirror.stability_index:.3f}")
        print(f"      Frequencies: {spore_mirror.frequency_spectrum}")
        
        # Verify lineage
        print(f"\n   🔍 LINEAGE VERIFICATION:")
        assert spore_mirror.stem_source == stem.stem_id, "Stem lineage broken!"
        assert spore_mirror.spore_id is not None, "Spore ID missing!"
        assert spore_mirror.projection_confidence > 0, "Confidence not set!"
        print(f"      ✅ Stem lineage intact: {spore_mirror.stem_source}")
        print(f"      ✅ Spore ID tracked: {spore_mirror.spore_id}")
        print(f"      ✅ Confidence propagated: {spore_mirror.projection_confidence:.3f}")
        
        # Test germination monitoring (update entanglement)
        print(f"\n   🌱 Testing germination cycle...")
        initial_entanglement = spore_mirror.entanglement_strength
        
        # Simulate resonance input (like network coherence)
        spore_mirror.update_entanglement(resonance_strength=0.7, delta_t=1.0)
        
        print(f"      Initial Entanglement: {initial_entanglement:.3f}")
        print(f"      After Resonance: {spore_mirror.entanglement_strength:.3f}")
        print(f"      Phase: {spore_mirror.phase.value}")
        
        if spore_mirror.entanglement_strength > initial_entanglement:
            print(f"      ✅ Spore is germinating! (entanglement growing)")
        
        # Compute overall score
        score = spore_mirror.compute_score()
        print(f"\n   📊 SPORE VIABILITY SCORE: {score:.4f}")
        print(f"      Formula: coherence × probability × beneficial × stability × φ")
        print(f"      = {spore_mirror.coherence_signature:.3f} × " +
              f"{spore_mirror.probability_amplitude:.3f} × " +
              f"{spore_mirror.beneficial_score:.3f} × " +
              f"{spore_mirror.stability_index:.3f} × {PHI:.3f}")
        
        # Save spore data to file
        spore_data = {
            "stem": asdict(stem),
            "prediction": prediction_data,
            "spore_mirror": {
                "mirror_id": spore_mirror.mirror_id,
                "spore_id": spore_mirror.spore_id,
                "stem_source": spore_mirror.stem_source,
                "projection_confidence": spore_mirror.projection_confidence,
                "phase": spore_mirror.phase.value,
                "coherence_signature": spore_mirror.coherence_signature,
                "beneficial_score": spore_mirror.beneficial_score,
                "stability_index": spore_mirror.stability_index,
                "entanglement_strength": spore_mirror.entanglement_strength,
                "viability_score": score,
            }
        }
        
        with open('test_spore_projection.json', 'w') as f:
            json.dump(spore_data, f, indent=2)
        
        print(f"\n   💾 Spore data saved to: test_spore_projection.json")
        
        return spore_mirror
        
    except Exception as e:
        print(f"   ❌ Error during spore projection: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run the complete mycelium spore branching test."""
    print("=" * 70)
    print("🍄 MYCELIUM SPORE BRANCHING TEST 🍄")
    print("=" * 70)
    print("\nTesting substrate pattern mapping with live ticker data...")
    print(f"Sacred Constants: φ={PHI:.4f}, Schumann={SCHUMANN_BASE}Hz, Love={LOVE_FREQUENCY}Hz")
    
    # Step 1: Fetch live substrate data
    substrate = fetch_live_substrate_data("BTC/USD")
    if not substrate:
        print("\n❌ Failed to fetch substrate data - aborting test")
        return
    
    # Step 2: Create reality stem
    stem = create_reality_stem_from_substrate(substrate)
    
    # Step 3: Simulate spore projection
    prediction_data = simulate_spore_projection(substrate)
    
    # Step 4: Project into Stargate
    spore_mirror = project_spores_to_stargate(stem, prediction_data)
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    
    if spore_mirror:
        print("✅ SUBSTRATE PATTERN CORRECTLY MAPPED!")
        print(f"   🌱 Stem: {stem.stem_id}")
        print(f"   🍄 Spore: {spore_mirror.spore_id}")
        print(f"   🪞 Mirror: {spore_mirror.mirror_id}")
        print(f"   📈 Viability: {spore_mirror.compute_score():.4f}")
        print(f"   🌊 Phase: {spore_mirror.phase.value}")
        print(f"\n   The mycelium network is alive and branching reality! 🍄🌌")
    else:
        print("❌ SUBSTRATE MAPPING FAILED")
        print("   Check error messages above for details")
    
    print("=" * 70)


if __name__ == "__main__":
    main()
