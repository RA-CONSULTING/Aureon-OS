#!/usr/bin/env python3
"""
🦈🔪 HFT HARMONIC MYCELIUM TEST - Queen HFT Control Demo

Tests the newly integrated HFT capabilities in the Queen Hive Mind.
Demonstrates HFT activation, status monitoring, and emergency controls.
"""

from typing import Any, Dict

from aureon.utils.aureon_queen_hive_mind import QueenHiveMind, QueenState


def print_separator(title: str):
    """Print a formatted separator"""
    print(f"\n{'='*60}")
    print(f"🦈 {title}")
    print(f"{'='*60}")

def print_status(status: Dict[str, Any]):
    """Pretty print status response"""
    print(f"📊 Status: {status.get('status', 'unknown')}")
    if 'message' in status:
        print(f"💬 Message: {status['message']}")
    if 'state' in status:
        print(f"👑 Queen State: {status['state']}")
    if 'warning' in status:
        print(f"⚠️ Warning: {status['warning']}")

def test_hft_integration():
    """Test HFT integration with Queen Hive Mind"""
    print("🦈🔪 HFT HARMONIC MYCELIUM TEST")
    print("Testing Queen HFT Control Integration")

    # Initialize Queen
    print("\n👑 Initializing Queen Hive Mind...")
    class FakeHFTEngine:
        def __init__(self):
            self.start_calls = 0

        def start_hft(self):
            self.start_calls += 1
            return True

        @staticmethod
        def get_status():
            return {"mode": "SCANNING", "tick_count": 0}

    # Exercise only the Queen control surface. The full constructor wires
    # provider clients and is intentionally excluded from this offline test.
    engine = FakeHFTEngine()
    queen = QueenHiveMind.__new__(QueenHiveMind)
    queen.state = QueenState.AWARE
    queen.hft_engine = engine
    queen.order_router = None

    # Test 1: Check initial HFT status
    print_separator("TEST 1: Initial HFT Status")
    status = queen.get_hft_status()
    print("📊 Initial HFT Status:")
    for key, value in status.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for sub_key, sub_value in value.items():
                print(f"    {sub_key}: {sub_value}")
        else:
            print(f"  {key}: {value}")

    # Test 2: Try to start HFT (should work if engine is available)
    print_separator("TEST 2: Start HFT Trading")
    start_result = queen.start_hft_trading()
    print_status(start_result)

    # Test 3: Get updated status
    print_separator("TEST 3: Updated HFT Status After Start")
    status = queen.get_hft_status()
    print("📊 Updated HFT Status:")
    for key, value in status.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for sub_key, sub_value in value.items():
                print(f"    {sub_key}: {sub_value}")
        else:
            print(f"  {key}: {value}")

    # Test 4: Try to enable execution (only if scanning)
    if status.get('state') == 'HFT_SCANNING':
        print_separator("TEST 4: Enable Live HFT Execution")
        exec_result = queen.enable_hft_execution()
        print_status(exec_result)

        # Test 5: Get final status
        print_separator("TEST 5: Final HFT Status")
        status = queen.get_hft_status()
        print("📊 Final HFT Status:")
        for key, value in status.items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for sub_key, sub_value in value.items():
                    print(f"    {sub_key}: {sub_value}")
            else:
                print(f"  {key}: {value}")

        # Test 6: Emergency stop
        print_separator("TEST 6: Queen Emergency Stop")
        stop_result = queen.hft_emergency_stop("Test emergency stop")
        print_status(stop_result)

    # Test 7: Configure risk limits
    print_separator("TEST 7: Configure HFT Risk Limits")
    risk_result = queen.configure_hft_risk_limits(
        daily_loss_limit_usd=-50.0,
        max_position_size_usd=200.0,
        max_concurrent_orders=15
    )
    print_status(risk_result)

    assert start_result["status"] == "success"
    assert risk_result["status"] == "success"
    assert queen.state is QueenState.HFT_SCANNING
    assert engine.start_calls == 1

    print_separator("TEST COMPLETE")
    print("✅ HFT integration test completed successfully!")
    print("🦈 Queen now has full HFT control capabilities")

if __name__ == "__main__":
    test_hft_integration()
