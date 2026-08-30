#!/usr/bin/env python3
"""
Test Production API Rate Limiting & Data Source Management
"""
import logging
from aureon_production_rate_limiter import (
    get_rate_limiter,
    BatchRequestOptimizer,
    print_api_status,
    API_RATE_LIMITS,
    DATA_SOURCE_PRIORITY
)

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def _complete_without_event_loop(coroutine):
    """Complete a no-wait limiter coroutine without opening loop sockets."""
    try:
        yielded = coroutine.send(None)
    except StopIteration as completed:
        return completed.value
    coroutine.close()
    raise AssertionError(f"rate limiter unexpectedly suspended: {yielded!r}")


def test_rate_limiter():
    """Test the production rate limiter."""
    print("\n" + "=" * 100)
    print("🚀 PRODUCTION API RATE LIMITER TEST")
    print("=" * 100)
    
    limiter = get_rate_limiter()
    
    # Test 1: Check initial status
    print("\n1️⃣ INITIAL API STATUS:")
    print_api_status()
    
    # Test 2: Simulate API requests
    print("\n2️⃣ SIMULATING API REQUESTS:")
    test_apis = ['coingecko', 'binance_public', 'kraken', 'alpaca']
    for api in test_apis:
        _complete_without_event_loop(limiter.wait_if_needed(api))
        print(f"   ✅ Can request {api}")
    
    # Test 3: Show API limits
    print("\n3️⃣ PRODUCTION API LIMITS (Per-Minute):")
    print("   API               │ Calls/Min │ Priority  │ Batch Size │ Fallback")
    print("   " + "-" * 70)
    for api_name in sorted(API_RATE_LIMITS.keys()):
        config = API_RATE_LIMITS[api_name]
        print(f"   {api_name:17} │ {config['calls_per_minute']:9} │ {config['priority']:9} │ {config['batch_size']:10} │ {config['fallback']}")
    
    # Test 4: Show batch optimization
    print("\n4️⃣ BATCH REQUEST OPTIMIZATION:")
    print("   API               │ 100 Symbols │ 500 Symbols │ 1000 Symbols │ 5000 Symbols")
    print("   " + "-" * 75)
    for api_name in sorted(API_RATE_LIMITS.keys()):
        calls_100 = BatchRequestOptimizer.estimate_api_calls(100, api_name)
        calls_500 = BatchRequestOptimizer.estimate_api_calls(500, api_name)
        calls_1000 = BatchRequestOptimizer.estimate_api_calls(1000, api_name)
        calls_5000 = BatchRequestOptimizer.estimate_api_calls(5000, api_name)
        print(f"   {api_name:17} │ {calls_100:11} │ {calls_500:11} │ {calls_1000:12} │ {calls_5000:12}")
    
    # Test 5: Show data source hierarchy
    print("\n5️⃣ DATA SOURCE PRIORITY HIERARCHY:")
    for data_type, sources in DATA_SOURCE_PRIORITY.items():
        print(f"   {data_type:20} → {' → '.join(sources)}")
    
    # Test 6: Get best source
    print("\n6️⃣ BEST AVAILABLE DATA SOURCES:")
    for data_type in DATA_SOURCE_PRIORITY.keys():
        best = limiter.get_best_source(data_type)
        print(f"   {data_type:20} = {best or 'NONE'}")
    
    # Test 7: Rate limit utilization
    print("\n7️⃣ RATE LIMIT UTILIZATION:")
    status = limiter.check_status()
    assert all(status[api]["recent_requests"] >= 1 for api in test_apis)
    assert BatchRequestOptimizer.estimate_api_calls(101, "binance_public") >= 1
    assert all(
        limiter.get_best_source(kind) in sources
        for kind, sources in DATA_SOURCE_PRIORITY.items()
    )
    for api_name, api_status in sorted(status.items(), key=lambda x: x[1]['utilization'], reverse=True):
        util_bar = '█' * int(api_status['utilization'] / 5) + '░' * (20 - int(api_status['utilization'] / 5))
        print(f"   {api_name:17} │ {util_bar} │ {api_status['utilization']:5.1f}%")
    
    print("\n" + "=" * 100)
    print("✅ PRODUCTION RATE LIMITER TEST COMPLETE")
    print("=" * 100 + "\n")

if __name__ == '__main__':
    test_rate_limiter()
