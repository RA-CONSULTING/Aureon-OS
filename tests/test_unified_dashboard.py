#!/usr/bin/env python3
"""
🧪 TEST SCRIPT - Unified Dashboard Integration Test
===================================================

Tests all components of the unified dashboard system:
  - System Coordinator
  - Unified Decision Engine
  - Feed Hub Consolidation
  - Unified Dashboard API
  - Orca Monitor

Run this script to verify everything is wired correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))


def test_system_coordinator():
    """Test system coordinator."""
    print("\n" + "=" * 70)
    print("🔗 Testing System Coordinator")
    print("=" * 70)

    try:
        from aureon_system_coordinator import SystemCoordinator, SystemState

        coordinator = SystemCoordinator()
        print(f"✅ Coordinator initialized with {len(coordinator.systems)} systems")

        # Simulate system states
        coordinator.set_system_state("kraken_client", SystemState.READY)
        coordinator.set_system_state("binance_client", SystemState.READY)
        coordinator.set_system_state("alpaca_client", SystemState.READY)

        can_execute, blockers = coordinator.can_execute_orca()
        print(f"✅ Orca execution check: {can_execute}")
        if blockers:
            print(f"   Blocked by: {blockers}")

        state = coordinator.get_coordination_state()
        print(f"✅ Coordination state: {state['total_systems']} systems, Orca ready: {state['orca_ready']}")

        assert state["total_systems"] == len(coordinator.systems)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise AssertionError("system coordinator contract failed") from e


def test_decision_engine():
    """Test unified decision engine."""
    print("\n" + "=" * 70)
    print("⚡ Testing Unified Decision Engine")
    print("=" * 70)

    try:
        from aureon_unified_decision_engine import UnifiedDecisionEngine, SignalInput, DecisionType, DecisionReason

        engine = UnifiedDecisionEngine()
        print(f"✅ Decision engine initialized")

        # Add some test signals
        signals = [
            SignalInput("seer_oracle", "BTC", "bullish", 0.8),
            SignalInput("momentum_scanner", "BTC", "bullish", 0.75),
            SignalInput("pattern_matcher", "BTC", "bullish", 0.7),
        ]

        for signal in signals:
            engine.add_signal(signal)

        print(f"✅ Added {len(signals)} test signals")

        # Analyze signals
        confidence, direction = engine.analyze_signals("BTC")
        print(f"✅ Signal analysis: {direction} (confidence: {confidence:.2f})")

        # Generate a decision
        decision = engine.generate_decision("BTC", DecisionType.BUY, DecisionReason.SIGNAL_STRENGTH)
        if decision:
            print(f"✅ Decision generated: {decision.decision_id}")
            print(f"   Type: {decision.decision_type.value}")
            print(f"   Confidence: {decision.confidence:.2f}")

        assert decision is not None
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise AssertionError("decision engine contract failed") from e


def test_feed_hub():
    """Test feed hub consolidation."""
    print("\n" + "=" * 70)
    print("📡 Testing Feed Hub Consolidation")
    print("=" * 70)

    try:
        from aureon_real_data_feed_hub import get_feed_hub

        hub = get_feed_hub()
        print(f"✅ Feed hub initialized")

        # Get consolidated feeds status
        status = hub.get_consolidated_feeds_status()
        print(f"✅ Consolidated feed streams:")
        for stream_name, stream_info in status.items():
            assert stream_info["stream_type"] == stream_name
            assert stream_info["data_status"] in {"live", "no_data"}
            if stream_info["data_status"] == "live":
                assert isinstance(stream_info["is_healthy"], bool)
            else:
                assert stream_info["truth_status"] == "no_data"
                assert stream_info["generated_values"] is False
                assert stream_info["operational_eligible"] is False
                assert stream_info["actionable"] is False
            print(
                f"   - {stream_name}: {stream_info['stream_type']} "
                f"(status={stream_info['data_status']})"
            )

        assert isinstance(status, dict)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise AssertionError("feed hub contract failed") from e


def test_orca_monitor():
    """Test Orca monitor."""
    print("\n" + "=" * 70)
    print("🐋 Testing Orca Monitor")
    print("=" * 70)

    try:
        from aureon_orca_monitor import OrcaMonitor

        monitor = OrcaMonitor()
        print(f"✅ Orca monitor initialized")

        # Simulate state changes
        monitor.set_execution_state("starting")
        monitor.set_execution_state("running")

        # Simulate a position
        monitor.add_position("BTC", "BUY", 1.0, 97500, 98500, 96500)
        print(f"✅ Added test position")

        # Check status
        status = monitor.get_orca_status()
        print(f"✅ Orca status:")
        print(f"   State: {status['state']}")
        print(f"   Active positions: {status['active_positions']}")
        print(f"   Total P&L: ${status['total_pnl']:.2f}")

        assert status["active_positions"] == 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise AssertionError("Orca monitor contract failed") from e


async def test_api_server():
    """Test API server initialization."""
    print("\n" + "=" * 70)
    print("🎯 Testing Unified Dashboard API")
    print("=" * 70)

    try:
        from aureon_unified_dashboard_api import UnifiedDashboardAPI

        api = UnifiedDashboardAPI()
        print(f"✅ Unified Dashboard API initialized")
        print(f"✅ Routes configured: {len(api.app.router.routes())} endpoints")

        # List endpoints
        for route in api.app.router.routes():
            if hasattr(route, 'resource'):
                print(f"   - {route.resource.canonical}")

        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_frontend_types():
    """Test that frontend types are properly defined."""
    print("\n" + "=" * 70)
    print("📄 Testing Frontend Types")
    print("=" * 70)

    try:
        # Check if types file exists and has our new types
        types_file = Path(__file__).parent / "frontend" / "src" / "types.ts"
        if types_file.exists():
            content = types_file.read_text()
            required_types = [
                "OrcaStatus",
                "CoordinationState",
                "FeedsStatus",
                "TradingDecision",
                "UnifiedState"
            ]

            all_found = True
            for type_name in required_types:
                if type_name in content:
                    print(f"✅ Found type: {type_name}")
                else:
                    print(f"❌ Missing type: {type_name}")
                    all_found = False

            return all_found
        else:
            print(f"❌ Types file not found: {types_file}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 10 + "🎯 UNIFIED DASHBOARD INTEGRATION TEST SUITE" + " " * 14 + "║")
    print("╚" + "=" * 68 + "╝")

    results = []

    # Run sync tests
    results.append(("System Coordinator", test_system_coordinator()))
    results.append(("Decision Engine", test_decision_engine()))
    results.append(("Feed Hub", test_feed_hub()))
    results.append(("Orca Monitor", test_orca_monitor()))

    # Run async tests
    results.append(("API Server", await test_api_server()))
    results.append(("Frontend Types", await test_frontend_types()))

    # Print summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for component, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {component}")

    print(f"\n{'='*70}")
    print(f"Result: {passed}/{total} components passed")

    if passed == total:
        print("🎉 All tests passed! System is ready.")
        return 0
    else:
        print(f"⚠️  {total - passed} component(s) need attention.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
