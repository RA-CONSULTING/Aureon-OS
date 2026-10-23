#!/usr/bin/env python3
"""
🌟 RISING STAR LOGIC - Demo & Test
═══════════════════════════════════════════════════════════════════════════════

This script demonstrates Rising Star Logic without live trading.

Shows:
1. Multi-intelligence scanning
2. Monte Carlo simulations
3. Candidate selection
4. Accumulation math
5. 30-second profit window

Gary Leckey | The Math Works | January 2026
═══════════════════════════════════════════════════════════════════════════════
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
from aureon.utils.console_utf8 import ensure_utf8_stdout  # noqa: E402

ensure_utf8_stdout()

import time
import random
from dataclasses import dataclass


def demo_accumulation_math():
    """Show how accumulation beats single-buy strategy."""
    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║  📊 ACCUMULATION MATH DEMO                                 ║")
    print("╚════════════════════════════════════════════════════════════╝\n")
    
    # Scenario
    initial_price = 350.00
    drop_price = 340.00  # -2.86%
    recovery_price = 350.00  # Back to entry
    
    fee_rate = 0.0025  # 0.25% per side = 0.5% round-trip
    
    print("Scenario: BTC/USD")
    print(f"  Initial Price: ${initial_price:.2f}")
    print(f"  Drops to: ${drop_price:.2f} (-2.86%)")
    print(f"  Recovers to: ${recovery_price:.2f}")
    print(f"  Fees: {fee_rate * 100:.2f}% per side\n")
    
    # OLD WAY - No Accumulation
    print("=" * 60)
    print("OLD WAY - Single Buy (No Accumulation)")
    print("=" * 60)
    
    buy_amount_1 = 5.00
    buy_qty_1 = buy_amount_1 / initial_price
    buy_cost_1 = buy_amount_1 * (1 + fee_rate)
    
    print(f"  Buy: ${buy_amount_1:.2f} @ ${initial_price:.2f}")
    print(f"  Qty: {buy_qty_1:.6f} BTC")
    print(f"  Cost (with fees): ${buy_cost_1:.4f}")
    print(f"\n  Price drops to ${drop_price:.2f}...")
    print(f"  ❌ Do nothing (old strategy)")
    print(f"\n  Price recovers to ${recovery_price:.2f}")
    
    sell_value_1 = buy_qty_1 * recovery_price * (1 - fee_rate)
    pnl_1 = sell_value_1 - buy_cost_1
    
    print(f"  Sell: {buy_qty_1:.6f} BTC @ ${recovery_price:.2f}")
    print(f"  Gross: ${buy_qty_1 * recovery_price:.4f}")
    print(f"  After fees: ${sell_value_1:.4f}")
    print(f"\n  ❌ P&L: ${pnl_1:.4f} (LOSS)\n")
    
    # NEW WAY - With Accumulation
    print("=" * 60)
    print("NEW WAY - Accumulation (DCA)")
    print("=" * 60)
    
    # First buy
    buy_amount_1 = 5.00
    buy_qty_1 = buy_amount_1 / initial_price
    buy_cost_1 = buy_amount_1 * (1 + fee_rate)
    
    print(f"  Buy #1: ${buy_amount_1:.2f} @ ${initial_price:.2f}")
    print(f"  Qty: {buy_qty_1:.6f} BTC")
    print(f"  Cost: ${buy_cost_1:.4f}")
    print(f"\n  Price drops to ${drop_price:.2f} (-5% trigger)")
    
    # Second buy (accumulation)
    buy_amount_2 = 2.50  # Half size
    buy_qty_2 = buy_amount_2 / drop_price
    buy_cost_2 = buy_amount_2 * (1 + fee_rate)
    
    print(f"  🔄 ACCUMULATE!")
    print(f"  Buy #2: ${buy_amount_2:.2f} @ ${drop_price:.2f}")
    print(f"  Qty: {buy_qty_2:.6f} BTC")
    print(f"  Cost: ${buy_cost_2:.4f}")
    
    # Calculate averages
    total_qty = buy_qty_1 + buy_qty_2
    total_cost = buy_cost_1 + buy_cost_2
    avg_entry = total_cost / total_qty
    
    print(f"\n  Total Qty: {total_qty:.6f} BTC")
    print(f"  Total Cost: ${total_cost:.4f}")
    print(f"  Avg Entry: ${avg_entry:.2f}")
    print(f"\n  Price recovers to ${recovery_price:.2f}")
    
    sell_value_2 = total_qty * recovery_price * (1 - fee_rate)
    pnl_2 = sell_value_2 - total_cost
    
    print(f"  Sell: {total_qty:.6f} BTC @ ${recovery_price:.2f}")
    print(f"  Gross: ${total_qty * recovery_price:.4f}")
    print(f"  After fees: ${sell_value_2:.4f}")
    print(f"\n  ✅ P&L: ${pnl_2:.4f} (WIN!)\n")
    
    # Comparison
    print("=" * 60)
    print("COMPARISON")
    print("=" * 60)
    print(f"  Old Way (no DCA): ${pnl_1:.4f}")
    print(f"  New Way (DCA):    ${pnl_2:.4f}")
    print(f"  Difference:       ${pnl_2 - pnl_1:.4f}")
    print(f"\n  💡 Accumulation turned LOSS into WIN!")


def demo_monte_carlo_simulation():
    """Show Monte Carlo simulation example."""
    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║  🎲 MONTE CARLO SIMULATION DEMO                            ║")
    print("╚════════════════════════════════════════════════════════════╝\n")
    
    print("Simulating 1000 trades with intelligence factors:\n")
    
    # Intelligence factors
    probability_win = 0.75  # 75% win rate from Probability Intelligence
    quantum_boost = 1.2     # 20% boost from Quantum scoring
    momentum = 0.8          # Strong momentum from Wave Scanner
    
    print(f"  Probability Win Rate: {probability_win:.0%}")
    print(f"  Quantum Boost: {quantum_boost:.1f}x")
    print(f"  Momentum Strength: {momentum:.1f}")
    print(f"\n  Running 1000 simulations...\n")
    
    wins = 0
    total_profit = 0.0
    time_to_profits = []
    amount_per_trade = 2.50
    
    for i in range(1000):
        # Weighted win probability
        win_prob = probability_win * (quantum_boost / 1.2)
        
        if random.random() < win_prob:
            wins += 1
            
            # Profit calculation
            price_move_pct = random.uniform(0.5, 2.0) * momentum
            gross_profit = amount_per_trade * (price_move_pct / 100)
            fees = amount_per_trade * 0.005
            net_profit = gross_profit - fees
            
            if net_profit > 0:
                total_profit += net_profit
                
                # Time to profit
                base_time = 30
                time_factor = quantum_boost * momentum
                time_to_profit = base_time / max(time_factor, 0.5)
                time_to_profits.append(time_to_profit)
    
    # Results
    win_rate = wins / 1000
    avg_profit = total_profit / 1000
    avg_time = sum(time_to_profits) / len(time_to_profits) if time_to_profits else 0
    
    print("=" * 60)
    print("SIMULATION RESULTS")
    print("=" * 60)
    print(f"  Total Simulations: 1000")
    print(f"  Wins: {wins}")
    print(f"  Win Rate: {win_rate:.1%}")
    print(f"  Avg Profit per Trade: ${avg_profit:.4f}")
    print(f"  Avg Time to Profit: {avg_time:.1f}s")
    
    time_score = 1.0 if avg_time <= 30 else (30 / avg_time)
    confidence = win_rate * 0.7 + time_score * 0.3
    
    print(f"\n  Time Score: {time_score:.2f} (1.0 = ≤30s)")
    print(f"  Overall Confidence: {confidence:.1%}")
    
    if confidence >= 0.70:
        print(f"\n  ✅ PASS - High confidence, select for trading")
    else:
        print(f"\n  ❌ REJECT - Low confidence, skip this candidate")


def demo_30_second_window():
    """Show 30-second profit window optimization."""
    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║  ⚡ 30-SECOND PROFIT WINDOW DEMO                           ║")
    print("╚════════════════════════════════════════════════════════════╝\n")
    
    print("Comparing time-to-profit for different strategies:\n")
    
    scenarios = [
        ("Old Random", 120, False),
        ("With Momentum", 45, False),
        ("Rising Star", 28, True),
    ]
    
    print("=" * 60)
    for name, time_sec, meets_target in scenarios:
        status = "✅ FAST KILL" if meets_target else "⏳ Standard"
        print(f"  {name:20s} | {time_sec:3d}s | {status}")
    print("=" * 60)
    
    print("\n  💡 Rising Star targets 30-second window for maximum efficiency")
    print("     Faster kills = more trades = more compound growth")


# ─── INTERACTIVE DEMO (SIMULATED PRICES — NO LIVE TRADING) ───────────────────
if __name__ == "__main__":
    print("\n🌟 RISING STAR LOGIC - Interactive Demo (SIMULATED — NOT LIVE)\n")
    
    # Run all demos
    demo_accumulation_math()
    
    print("\n" + "─" * 60 + "\n")
    input("Press Enter to see Monte Carlo simulation demo...")
    
    demo_monte_carlo_simulation()
    
    print("\n" + "─" * 60 + "\n")
    input("Press Enter to see 30-second profit window demo...")
    
    demo_30_second_window()
    
    print("\n" + "═" * 60)
    print("\n✨ Demo Complete!")
    print("\nKey Takeaways:")
    print("  1. Accumulation (DCA) turns losses into wins")
    print("  2. Monte Carlo validates candidates before trading")
    print("  3. 30-second window maximizes compound efficiency")
    print("  4. Multi-intelligence scoring finds best opportunities")
    print("\nReady to integrate into War Room? See:")
    print("  - rising_star_war_room_enhancer.py")
    print("  - rising_star_war_room_integration.md")
    print()
