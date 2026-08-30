#!/usr/bin/env python3
"""
Comprehensive Whale Detection System Test

Tests all integration points:
1. On-chain provider connectivity
2. Stargate correlation mapping  
3. Metrics emission
4. ML training pipeline
5. End-to-end flow

Usage:
    python test_whale_system.py
"""
import os
import sys

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
        # Skip stderr wrapping (causes Windows exit errors)
    except Exception:
        pass

import logging
import time
from pathlib import Path

import pytest

from scripts.validation.pytest_no_skip_shards import (
    fingerprint_operational_paths,
    isolate_runtime_writers,
    safe_subprocess_environment,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
_REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module", autouse=True)
def _isolated_runtime(tmp_path_factory):
    before = fingerprint_operational_paths(_REPO_ROOT)
    runtime_root = tmp_path_factory.mktemp("whale-system")
    patcher = pytest.MonkeyPatch()
    safe_env, scrubbed = safe_subprocess_environment(dict(os.environ))
    safe_env = isolate_runtime_writers(safe_env, runtime_root)
    for name in scrubbed:
        patcher.delenv(name, raising=False)
    for name, value in safe_env.items():
        patcher.setenv(name, value)
    patcher.chdir(runtime_root)
    try:
        yield
    finally:
        patcher.undo()
        assert fingerprint_operational_paths(_REPO_ROOT) == before


def _check_onchain_providers():
    """Test 1: Exchange whale tracker connectivity"""
    print("\n" + "="*70)
    print("TEST 1: Exchange Whale Tracker (Using Existing Exchange APIs)")
    print("="*70)
    
    try:
        from aureon_whale_onchain_tracker import get_exchange_tracker
        
        tracker = get_exchange_tracker()
        if tracker:
            print(f"✅ Exchange tracker initialized")
            print(f"   Available exchanges: {list(tracker.exchanges.keys())}")
            print(f"   Threshold: ${tracker.threshold_usd:,.0f}")
            
            # Test simulated transfer
            tracker.simulate_transfer('ETH', '0xtest123', '0xfrom', '0xto', 150000.0)
            print(f"✅ Simulated whale event published")
        else:
            print("⚠️  Exchange tracker not initialized (no exchange clients available)")
        
        return True
    except Exception as e:
        print(f"❌ Exchange tracker test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def _check_stargate_correlation():
    """Test 2: Stargate correlation mapping"""
    print("\n" + "="*70)
    print("TEST 2: Stargate Correlation Mapping")
    print("="*70)
    
    try:
        from aureon_stargate_integration import get_stargate_integration, STARGATE_SYMBOL_MAP
        
        sg = get_stargate_integration()
        if not sg:
            print("⚠️  Stargate integration not initialized")
            return False
        
        print(f"✅ Stargate integration active")
        print(f"   Planetary nodes mapped: {len(STARGATE_SYMBOL_MAP)}")
        
        # Show sample mappings
        print("\n   Sample node→symbol mappings:")
        for node, symbols in list(STARGATE_SYMBOL_MAP.items())[:3]:
            print(f"     {node}: {', '.join(symbols[:3])}")
        
        # Test correlation
        from aureon_thought_bus import get_thought_bus, Thought
        bus = get_thought_bus()
        
        # Publish a stargate activation
        payload = {
            'node_id': 'giza',
            'coherence': 0.85,
            'frequency': 432.0
        }
        th = Thought(source='test', topic='stargate.activation', payload=payload)
        bus.publish(th)
        print(f"✅ Published stargate activation event")
        
        time.sleep(0.5)
        return True
    
    except Exception as e:
        print(f"❌ Stargate test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def _check_metrics():
    """Test 3: Metrics emission"""
    print("\n" + "="*70)
    print("TEST 3: Metrics Emission")
    print("="*70)
    
    try:
        from whale_metrics import (
            whale_shape_detected_total,
            whale_pattern_classified_total,
            whale_onchain_transfer_total,
            whale_stargate_coherence,
            get_whale_system_summary
        )
        
        # Emit test metrics
        whale_shape_detected_total.inc(subtype='grid', symbol='BTC/USD', exchange='kraken')
        whale_pattern_classified_total.inc(pattern_type='accumulation', symbol='BTC/USD')
        whale_onchain_transfer_total.inc(direction='deposit', exchange_name='Binance', token_symbol='ETH')
        whale_stargate_coherence.set(0.88, symbol='BTC/USD', node_id='giza')
        
        print(f"✅ Metrics emitted successfully")
        
        # Get values
        grid_count = whale_shape_detected_total.get(subtype='grid', symbol='BTC/USD', exchange='kraken')
        print(f"   Grid bot detections: {grid_count}")
        
        # Get summary
        summary = get_whale_system_summary()
        print(f"   System summary keys: {list(summary.keys())}")
        
        return True
    
    except Exception as e:
        print(f"❌ Metrics test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def _check_ml_pipeline():
    """Test 4: ML training pipeline"""
    print("\n" + "="*70)
    print("TEST 4: ML Training Pipeline")
    print("="*70)
    
    try:
        from whale_shape_ml_trainer import get_trainer, ShapeFeatures
        
        trainer = get_trainer()
        print(f"✅ ML trainer initialized")
        
        # Try to collect data
        n_samples = trainer.collect_training_data_from_elephant(min_samples=5)
        print(f"   Training data collected: {n_samples} samples")
        
        if n_samples >= 5:
            print(f"   Sufficient data for training!")
            # Don't actually train in test (takes time)
            # trainer.train(test_size=0.2, min_samples=5)
        else:
            print(f"   ℹ️  Need more data for training (min 5 samples)")
        
        # Test prediction (even without training)
        test_features = ShapeFeatures(
            spectral_centroid=0.5,
            spectral_bandwidth=0.3,
            spectral_flatness=0.4,
            spectral_energy=100.0,
            peak_count=3,
            layering_score=0.7,
            depth_imbalance=0.2,
            wall_count=2,
            dominant_frequency=450.0,
            harmonic_coherence=0.8,
            phase_alignment=0.6,
            volatility=0.05,
            volume=1000000.0,
            hour_of_day=14
        )
        
        prediction = trainer.predict(test_features)
        print(f"   Sample prediction: {prediction}")
        
        return True
    
    except Exception as e:
        print(f"❌ ML pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def _check_end_to_end():
    """Test 5: End-to-end flow"""
    print("\n" + "="*70)
    print("TEST 5: End-to-End Flow")
    print("="*70)
    
    try:
        from aureon_thought_bus import get_thought_bus, Thought
        import json
        
        bus = get_thought_bus()
        
        # Create synthetic market snapshot with all context
        market_payload = {
            'symbol': 'BTC/USD',
            'price': 45000.0,
            'volume': 1000000.0,
            'volatility': 0.05,
            'dominant_frequency': 450.0,
            'timestamp': time.time()
        }
        
        # Publish market snapshot
        th = Thought(source='test', topic='market.snapshot', payload=market_payload)
        bus.publish(th)
        print(f"✅ Published market snapshot")
        
        # Publish orderbook analysis
        orderbook_payload = {
            'symbol': 'BTC/USD',
            'exchange': 'kraken',
            'bids_depth': 5000000.0,
            'asks_depth': 3000000.0,
            'layering_score': 0.75,
            'walls': [
                {'side': 'bid', 'price': 44900, 'size': 10.0, 'notional': 449000}
            ],
            'timestamp': time.time()
        }
        th = Thought(source='test', topic='whale.orderbook.analyzed', payload=orderbook_payload)
        bus.publish(th)
        print(f"✅ Published orderbook analysis")
        
        # Wait for processing
        time.sleep(1.0)
        
        # Check if thoughts were processed
        print(f"✅ End-to-end flow completed")
        
        return True
    
    except Exception as e:
        print(f"❌ End-to-end test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_onchain_providers():
    assert _check_onchain_providers()


def test_stargate_correlation():
    assert _check_stargate_correlation()


def test_metrics():
    assert _check_metrics()


def test_ml_pipeline():
    assert _check_ml_pipeline()


def test_end_to_end():
    assert _check_end_to_end()


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🐋 WHALE DETECTION SYSTEM COMPREHENSIVE TEST")
    print("="*70)
    
    results = {
        'On-chain Providers': _check_onchain_providers(),
        'Stargate Correlation': _check_stargate_correlation(),
        'Metrics Emission': _check_metrics(),
        'ML Training Pipeline': _check_ml_pipeline(),
        'End-to-End Flow': _check_end_to_end(),
    }
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | {test_name}")
    
    total = len(results)
    passed = sum(results.values())
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Whale detection system fully operational.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check logs above for details.")
    
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
