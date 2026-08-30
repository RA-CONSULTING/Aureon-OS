#!/usr/bin/env python3
"""
Quick test for Revenue Board
"""

from aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
sys.path.insert(0, '/workspaces/aureon-trading')

from aureon_revenue_board import RevenueBoard, get_revenue_board, print_revenue_board

def test_revenue_board():
    print("🧪 Testing Revenue Board...")
    
    # Create board
    rb = RevenueBoard(initial_equity=10000.0)
    
    # Record some trades
    rb.record_trade('BTCUSDT', 'BINANCE', 'BUY', 0.01, 65000, 6.5, 0, 'TEST')
    rb.record_trade('ETHUSDT', 'KRAKEN', 'BUY', 1.0, 2500, 2.5, 0, 'TEST')
    rb.record_trade('BTCUSDT', 'BINANCE', 'SELL', 0.01, 65500, 6.55, 5.0, 'TEST')
    
    # Record sweeps
    rb.record_sweep('WORLD_1', 10.0, 'PROFIT_SWEEP')
    rb.record_sweep('WORLD_2', 5.0, 'PROFIT_SWEEP')
    
    # Compute equity — the board's real API is compute_equity() (returns an
    # EquitySnapshot); update_equity() never existed on RevenueBoard.
    rb.compute_equity()
    
    # Print board
    rb.print_board()
    
    # Test get_status
    status = rb.get_status()
    print(f"\n📊 Status Dict: {len(status)} keys")
    # get_status nests these under 'pnl' and 'trading' — the flat keys never existed.
    print(f"   Realized PnL: ${status['pnl']['realized']:.2f}")
    print(f"   Sweep PnL: ${status['pnl']['sweep']:.2f}")
    print(f"   Trade Count: {status['trading']['trades']}")
    
    print("\n✅ Revenue Board Test Complete!")

if __name__ == "__main__":
    test_revenue_board()
