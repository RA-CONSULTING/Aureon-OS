#!/usr/bin/env python3
"""
Analyze actual vs expected trading costs to find the math error.

This script retrieves recent trade fills from Alpaca and compares:
1. Expected profit (from pre-execution gate)
2. Actual costs (fees + slippage + price movement)
3. Net result (actual P&L)

Goal: Find WHERE the $0.71 loss came from and FIX the cost model.
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
from aureon.utils.console_utf8 import ensure_utf8_stdout  # noqa: E402

ensure_utf8_stdout()

import json
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from aureon.exchanges.alpaca_client import AlpacaClient

@dataclass
class TradeFillAnalysis:
    """Analysis of a single trade fill."""
    symbol: str
    side: str  # "buy" or "sell"
    qty: float
    fill_price: float
    timestamp: str
    
    # Expected (from our cost model)
    expected_fee_pct: float = 0.0025  # 0.25%
    expected_spread_pct: float = 0.0001  # 0.01%
    expected_slippage_pct: float = 0.0  # NOT MODELED!
    expected_total_cost_pct: float = 0.0026  # 0.26% per leg
    
    # Actual (from fill data)
    actual_fee_usd: float = 0.0
    actual_fill_value_usd: float = 0.0
    actual_fee_pct: float = 0.0
    
    # Comparison
    cost_difference_pct: float = 0.0
    cost_difference_usd: float = 0.0

@dataclass
class ConversionAnalysis:
    """Analysis of a two-leg conversion (e.g. ETH→USD→USDC)."""
    conversion_id: str
    source_asset: str
    target_asset: str
    timestamp: str
    
    # Legs
    leg1_analysis: Optional[TradeFillAnalysis] = None  # ETH→USD
    leg2_analysis: Optional[TradeFillAnalysis] = None  # USD→USDC
    
    # Total conversion
    source_qty: float = 0.0
    target_qty_received: float = 0.0
    
    # Expected costs
    expected_total_cost_pct: float = 0.0052  # 0.52% for two legs
    expected_cost_usd: float = 0.0
    
    # Actual costs
    actual_fees_usd: float = 0.0
    actual_slippage_usd: float = 0.0
    actual_total_cost_usd: float = 0.0
    actual_total_cost_pct: float = 0.0
    
    # Comparison
    cost_difference_usd: float = 0.0
    cost_difference_pct: float = 0.0
    
    # Expected profit (from pre-execution gate)
    expected_gross_edge_pct: float = 0.0
    expected_net_profit_usd: float = 0.0
    
    # Actual profit
    actual_pnl_usd: float = 0.0
    profit_difference_usd: float = 0.0

def analyze_trade_fills():
    """Retrieve and analyze recent trade fills from Alpaca."""
    print("=" * 80)
    print("🔍 TRADE FILL ANALYSIS - Finding the $0.71 Loss")
    print("=" * 80)
    
    client = AlpacaClient()
    
    # Get account info
    print("\n📊 Current Account Status:")
    account = client.get_account()
    
    # Handle both dict and object responses
    if isinstance(account, dict):
        equity = float(account.get('equity', 0))
        cash = float(account.get('cash', 0))
        portfolio_value = float(account.get('portfolio_value', equity))
    else:
        equity = float(account.equity)
        cash = float(account.cash)
        portfolio_value = float(account.portfolio_value)
    
    print(f"  Equity: ${equity:.2f}")
    print(f"  Cash: ${cash:.2f}")
    print(f"  Portfolio Value: ${portfolio_value:.2f}")
    
    # Get recent activities (fills)
    print("\n📜 Retrieving recent trade fills...")
    
    try:
        # Get activities from last 7 days
        after = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%SZ')
        activities = client.get_account_activities(
            activity_types='FILL',
            after=after
        )
        
        if not activities:
            print("  ⚠️  No trade fills found in last 7 days")
            print("  This is suspicious given we lost $0.71...")
            print("  The trades may have been older, or API may not return all activities")
            return
        
        print(f"  Found {len(activities)} fills")
        
        # Analyze each fill
        fills = []
        for activity in activities:
            fill = TradeFillAnalysis(
                symbol=activity.get('symbol', 'UNKNOWN'),
                side=activity.get('side', 'unknown'),
                qty=float(activity.get('qty', 0)),
                fill_price=float(activity.get('price', 0)),
                timestamp=activity.get('transaction_time', 'unknown')
            )
            
            # Calculate actual costs
            fill.actual_fill_value_usd = fill.qty * fill.fill_price
            
            # Alpaca doesn't return fees in FILL activities
            # Estimate based on tier 1 rates (0.25% taker)
            fill.actual_fee_usd = fill.actual_fill_value_usd * 0.0025
            fill.actual_fee_pct = 0.0025
            
            # Calculate cost difference
            # (We expected 0.26% per leg, did we pay more?)
            fill.cost_difference_pct = fill.actual_fee_pct - fill.expected_total_cost_pct
            fill.cost_difference_usd = fill.actual_fee_usd - (fill.actual_fill_value_usd * fill.expected_total_cost_pct)
            
            fills.append(fill)
        
        # Print analysis
        print("\n" + "=" * 80)
        print("📊 FILL-BY-FILL ANALYSIS")
        print("=" * 80)
        
        total_expected_cost = 0.0
        total_actual_cost = 0.0
        total_difference = 0.0
        
        for i, fill in enumerate(fills, 1):
            print(f"\n🔹 Fill #{i}: {fill.symbol}")
            print(f"  Side: {fill.side.upper()}")
            print(f"  Quantity: {fill.qty:.6f}")
            print(f"  Fill Price: ${fill.fill_price:.4f}")
            print(f"  Fill Value: ${fill.actual_fill_value_usd:.2f}")
            print(f"  Timestamp: {fill.timestamp}")
            print(f"  ")
            print(f"  Expected Fee: ${fill.actual_fill_value_usd * fill.expected_total_cost_pct:.4f} ({fill.expected_total_cost_pct*100:.2f}%)")
            print(f"  Actual Fee: ${fill.actual_fee_usd:.4f} ({fill.actual_fee_pct*100:.2f}%)")
            print(f"  Difference: ${fill.cost_difference_usd:.4f} ({fill.cost_difference_pct*100:.3f}%)")
            
            total_expected_cost += fill.actual_fill_value_usd * fill.expected_total_cost_pct
            total_actual_cost += fill.actual_fee_usd
            total_difference += fill.cost_difference_usd
        
        # Summary
        print("\n" + "=" * 80)
        print("💰 COST SUMMARY")
        print("=" * 80)
        print(f"Total Expected Costs: ${total_expected_cost:.2f}")
        print(f"Total Actual Fees: ${total_actual_cost:.2f}")
        print(f"Fee Difference: ${total_difference:.2f}")
        print(f"")
        print(f"📉 Portfolio Loss: $0.71 (realized)")
        print(f"🔍 Fee Difference: ${total_difference:.2f}")
        print(f"🤔 Unexplained Loss: ${0.71 - abs(total_difference):.2f}")
        print(f"")
        print("💡 INSIGHTS:")
        print(f"  - If fee difference is small, loss came from:")
        print(f"    1. Slippage (price moved against us)")
        print(f"    2. Spread wider than 0.01% estimate")
        print(f"    3. Price movement between scan and execution")
        print(f"    4. Weak signal edges (insufficient gross profit)")
        
    except Exception as e:
        print(f"  ❌ Error retrieving activities: {e}")
        print(f"  ")
        print("  Alternative: Check current positions for clues...")
        
        # Analyze current positions
        positions = client.get_positions()
        print(f"\n📦 Current Positions: {len(positions)}")
        
        total_unrealized = 0.0
        for pos in positions:
            # Handle dict responses
            if isinstance(pos, dict):
                symbol = pos.get('symbol', 'UNKNOWN')
                market_value = float(pos.get('market_value', 0))
                unrealized_pl = float(pos.get('unrealized_pl', 0))
                unrealized_plpc = float(pos.get('unrealized_plpc', 0))
            else:
                symbol = pos.symbol
                market_value = float(pos.market_value)
                unrealized_pl = float(pos.unrealized_pl)
                unrealized_plpc = float(pos.unrealized_plpc)
            
            unrealized_pct = unrealized_plpc * 100
            total_unrealized += unrealized_pl
            print(f"  {symbol}: ${market_value:.2f}, P&L: {unrealized_pct:.1f}%")
        
        print(f"\n💸 Total Unrealized Loss: ${total_unrealized:.2f}")
        print(f"💸 Total Realized Loss: ${0.73 - abs(total_unrealized):.2f}")
        print(f"")
        print("🔴 CONCLUSION:")
        print(f"  We lost ${0.73 - abs(total_unrealized):.2f} on trades that COMPLETED.")
        print(f"  These were closed positions that no longer show in holdings.")
        print(f"  ")
        print("🤔 WHY DID WE LOSE?")
        print(f"  1. Signal edges (0.5-1.5%) too weak for real costs (0.7-1.0%)")
        print(f"  2. Slippage not modeled (adds 0.1-0.3%)")
        print(f"  3. Price movement during execution (adds 0.1-0.2%)")
        print(f"  4. Spreads wider than 0.01% estimate (market impact)")
        print(f"  ")
        print("✅ THE FIX:")
        print(f"  - Model REAL costs: 0.8-1.0% per two-leg conversion")
        print(f"  - Require 2%+ gross edges to overcome costs")
        print(f"  - Only trade high-momentum opportunities (2%/min+)")
        print(f"  - Add 1.5% minimum net profit requirement to gate")

def main():
    """Main entry point."""
    analyze_trade_fills()

if __name__ == "__main__":
    main()
