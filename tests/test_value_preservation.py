#!/usr/bin/env python3
"""
Final test: Frog ensures value is maintained through the leap strategy.
Goal: Start with value, maintain it through leaps, and ensure recovery path exists.
"""

# ── live-venue guard ──────────────────────────────────────────────────────────────
# Pytest exercises the deterministic value/fee invariants below. The original
# credentialed market scenario remains available only through direct script execution.
import ast
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


def _load_value_types():
    """Execute only the two pure dataclass definitions from the production source."""
    source_path = Path(__file__).resolve().parents[1] / "aureon" / "queen" / "queen_eternal_machine.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    selected = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name in {"MainPosition", "LeapOpportunity"}
    ]
    assert {node.name for node in selected} == {"MainPosition", "LeapOpportunity"}
    namespace = {"dataclass": dataclass, "datetime": datetime}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(source_path), "exec"), namespace)
    return namespace["MainPosition"], namespace["LeapOpportunity"]


def test_value_preservation_strategy():
    """Verify the value and fee invariants without a live venue."""
    MainPosition, LeapOpportunity = _load_value_types()

    position = MainPosition(
        symbol="ETH",
        quantity=1.0,
        cost_basis=3000.0,
        entry_price=3000.0,
        entry_time=datetime.now(),
        current_price=1500.0,
        change_24h=-50.0,
    )
    assert position.current_value == 1500.0
    assert position.unrealized_pnl == -1500.0

    leap = LeapOpportunity(
        from_symbol="ETH",
        to_symbol="BTC",
        from_price=1500.0,
        to_price=30000.0,
        from_change=-50.0,
        to_change=-60.0,
        dip_advantage=10.0,
        quantity_multiplier=1.1,
        recovery_advantage=150.0,
        gross_value=1500.0,
        sell_fee_cost=7.5,
        buy_fee_cost=7.5,
        total_fees=15.0,
        net_value_after_fees=1485.0,
        fee_adjusted_multiplier=1.1,
    )
    assert leap.net_value_after_fees == leap.gross_value - leap.total_fees
    assert leap.breakeven_dip_advantage == 1.0
    assert leap.is_profitable_after_fees is True


async def _run_live_value_preservation_diagnostic():
    """Run the original credentialed market scenario explicitly as a script."""
    from queen_eternal_machine import MainPosition, QueenEternalMachine

    print("🐸 VALUE PRESERVATION STRATEGY TEST")
    print("=" * 70)

    frog = QueenEternalMachine(initial_vault=1000.0)
    frog.fetch_market_data()

    # Scenario: Gary has ETH with significant baggage
    eth_original_cost = 3000.0
    eth_current_value = 1500.0  # Lost $1500 (-50%)
    eth_qty = eth_current_value / frog.market_data["ETH"].price

    print("\n💰 STARTING POSITION:")
    print(f"   Original investment: ${eth_original_cost:.2f}")
    print(f"   Current value: ${eth_current_value:.2f}")
    print(
        f"   LOSS: ${eth_original_cost - eth_current_value:.2f} ({(eth_current_value / eth_original_cost - 1) * 100:+.1f}%)"
    )

    frog.main_position = MainPosition(
        symbol="ETH",
        quantity=eth_qty,
        cost_basis=eth_original_cost,
        entry_price=eth_original_cost / eth_qty,
        entry_time=datetime.now(),
        current_price=frog.market_data["ETH"].price,
        change_24h=frog.market_data["ETH"].change_24h,
    )
    frog.available_cash = 0.0

    print("\n🎯 FROG'S LEAP STRATEGY:")
    print("   Goal: Leap to DEEPER dips to capture recovery advantage")
    print("   Rule: ONLY leap if target has bigger downside (better recovery potential)")
    print("   Safety: Value preserved after fees, breadcrumb left for recovery")

    # Run 3 cycles
    for cycle in range(3):
        print(f"\n🔄 CYCLE {cycle + 1}:")
        await frog.run_cycle()

        # Calculate total value
        total = 0.0
        if frog.main_position:
            total += frog.main_position.current_value
            print(f"   Main: {frog.main_position.symbol} = ${frog.main_position.current_value:.2f}")

        for sym, crumb in frog.breadcrumbs.items():
            total += crumb.current_value
            print(f"   Breadcrumb {sym}: ${crumb.current_value:.2f}")

        total += frog.available_cash
        if frog.available_cash > 0:
            print(f"   Cash: ${frog.available_cash:.2f}")

        print(f"   Total Portfolio: ${total:.2f}")

        # Check value preservation
        value_lost = eth_current_value - total
        pct_lost = (value_lost / eth_current_value) * 100
        print(f"   Value lost to fees: ${value_lost:.2f} ({pct_lost:.2f}%)")

        if frog.total_leaps > 0:
            print("   ✅ Leaped to deeper dip (recovery potential)")
        else:
            print("   ⏸️  No leap (holding current position)")

    print("\n💎 FINAL ANALYSIS:")
    print(f"   Starting value: ${eth_current_value:.2f}")
    print(f"   Ending value: ${total:.2f}")
    print(f"   Value preserved: {(total / eth_current_value) * 100:.2f}%")
    print(f"   Leaps made: {frog.total_leaps}")
    print(f"   Breadcrumbs planted: {len(frog.breadcrumbs)}")

    if total >= (eth_current_value * 0.99):  # At least 99% preserved
        print("   ✅ VALUE PRESERVATION SUCCESS!")
        print("   ✅ Frog is following the recovery strategy")
    else:
        print("   ❌ Too much value lost")

    if frog.total_leaps > 0:
        print("   ✅ SMART LEAPING - jumping to recovery opportunities")
    else:
        print("   ⚠️  No leaps (might mean no recovery advantages found)")


if __name__ == "__main__":
    import asyncio

    asyncio.run(_run_live_value_preservation_diagnostic())
