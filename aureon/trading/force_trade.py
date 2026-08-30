#!/usr/bin/env python3
"""
🔥 FORCE TRADE - Execute a single trade bypassing all gates 🔥

This script forces the Aureon system to execute one trade immediately,
bypassing all gate checks, coherence thresholds, and halts.

Usage:
    python force_trade.py              # Auto-select best opportunity
    python force_trade.py BTCGBP       # Force trade on specific symbol
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os

# Set FORCE_TRADE mode BEFORE importing anything
os.environ['FORCE_TRADE'] = '1'
os.environ['LIVE'] = '1'  # Enable live trading

# Force minimum score to 0 to allow any opportunity
os.environ['FORCE_MIN_SCORE'] = '0'

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import time
from datetime import datetime

from aureon.queen.queen_force_trade_governance import evaluate_queen_force_trade_authority

def force_trade():
    """Force execute a single trade"""
    
    print("\n" + "="*70)
    print("🔥 AUREON FORCE TRADE MODE 🔥")
    print("="*70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Get optional symbol from command line
    target_symbol = sys.argv[1].upper() if len(sys.argv) > 1 else None
    if target_symbol:
        os.environ['FORCE_TRADE_SYMBOL'] = target_symbol
        print(f"🎯 Target Symbol: {target_symbol}")
    else:
        print("🎯 Target: Best available opportunity")
    
    print()
    print("⚠️  WARNING: This will execute a REAL trade!")
    print("="*70)

    decision = evaluate_queen_force_trade_authority()
    print(f"👑 Queen Governance: {decision.reason}")
    if decision.missing_requirements:
        print("   Missing requirements:")
        for requirement in decision.missing_requirements:
            print(f"   - {requirement}")
    if not decision.allowed:
        print("🛑 Aborting force trade: only the unified Queen may authorize forced trades.")
        return False

    # P4 bypass visibility: a Queen-authorized force trade skips every gate
    # (SignalGate phase + volatility checks, coherence, halts) — that skip is
    # a named audit row, never a silent door.
    try:
        from aureon.observer.production_mode import audit as _pm_audit
        _pm_audit(
            "force_trade_gate_bypass",
            {
                "target_symbol": target_symbol or "best_available",
                "queen_reason": str(decision.reason),
                "skipped_checks": (
                    "signal_gate,phase_transition,volatility_sentinel,"
                    "entry_coherence,min_score,halt"
                ),
            },
            decision="entry_gate_bypass",
            would_have_blocked=None,
            actually_blocked=False,
        )
    except Exception:
        pass

    print()
    
    # Import after setting environment
    from aureon.trading.aureon_unified_ecosystem import AureonKrakenEcosystem, CONFIG
    
    # Override config for force trade
    CONFIG['FORCE_TRADE'] = True
    CONFIG['MIN_SCORE'] = 0
    CONFIG['OPTIMAL_MIN_GATES'] = 0
    CONFIG['OPTIMAL_MIN_COHERENCE'] = 0
    CONFIG['ENTRY_COHERENCE'] = 0
    CONFIG['MIN_MOMENTUM'] = -100  # Allow any momentum
    CONFIG['MAX_MOMENTUM'] = 1000
    CONFIG['BINANCE_DRY_RUN'] = False
    CONFIG['KRAKEN_DRY_RUN'] = False
    
    print("📊 Loading system...")
    ecosystem = AureonKrakenEcosystem()
    
    print("🔄 Refreshing market data...")
    
    # Force load Binance data since that's where we have API keys
    print("   📊 Loading Binance market data...")
    try:
        from aureon.exchanges.binance_client import get_binance_client
        binance = get_binance_client()
        tickers = binance.get_24h_tickers()
        
        for t in tickers:
            symbol = t.get('symbol', '')
            # Focus on GBP and major USDT pairs
            if symbol.endswith('GBP') or (symbol.endswith('USDT') and any(x in symbol for x in ['BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'DOGE', 'AVAX', 'DOT', 'MATIC'])):
                try:
                    ecosystem.ticker_cache[symbol] = {
                        'price': float(t.get('lastPrice', 0)),
                        'change24h': float(t.get('priceChangePercent', 0)),
                        'volume': float(t.get('quoteVolume', 0)),
                        'source': 'binance'
                    }
                except:
                    continue
        print(f"   ✅ Loaded {len(ecosystem.ticker_cache)} tradeable pairs from Binance")
    except Exception as e:
        print(f"   ❌ Binance fetch failed: {e}")
        import traceback
        traceback.print_exc()
    
    if len(ecosystem.ticker_cache) == 0:
        print("❌ No market data available. Check Binance API connectivity.")
        return False
    
    print("🔍 Scanning for opportunities (all gates bypassed)...")
    
    # Force opportunity scan with no filters
    opportunities = ecosystem.find_opportunities()
    
    if not opportunities:
        print("❌ No opportunities found even with gates bypassed")
        print("   Check exchange connectivity and market data")
        return False
    
    print(f"\n✅ Found {len(opportunities)} opportunities")
    print()
    
    # Find target or best opportunity
    selected_opp = None
    
    if target_symbol:
        # Find specific symbol
        for opp in opportunities:
            if opp['symbol'] == target_symbol or target_symbol in opp['symbol']:
                selected_opp = opp
                break
        
        if not selected_opp:
            print(f"❌ Symbol {target_symbol} not found in opportunities")
            print(f"   Available: {[o['symbol'] for o in opportunities[:10]]}")
            return False
    else:
        # Take best opportunity (highest score)
        selected_opp = opportunities[0]
    
    # Display selected opportunity
    print("="*70)
    print("📈 SELECTED OPPORTUNITY")
    print("="*70)
    print(f"  Symbol:     {selected_opp['symbol']}")
    print(f"  Price:      {selected_opp['price']:.8f}")
    print(f"  Score:      {selected_opp['score']}")
    print(f"  Coherence:  {selected_opp['coherence']:.2%}")
    print(f"  24h Change: {selected_opp.get('change24h', 0):.2f}%")
    print(f"  Exchange:   {selected_opp.get('source', 'kraken')}")
    print(f"  Gates:      {selected_opp.get('gate_status', 'N/A')}")
    print("="*70)
    print()
    
    # Execute the trade
    print("🚀 EXECUTING TRADE...")
    print()
    
    try:
        ecosystem.open_position(selected_opp)
        
        # Check if position was opened
        time.sleep(2)
        
        if selected_opp['symbol'] in ecosystem.positions:
            pos = ecosystem.positions[selected_opp['symbol']]
            print("="*70)
            print("✅ TRADE EXECUTED SUCCESSFULLY!")
            print("="*70)
            print(f"  Symbol:      {pos.symbol}")
            print(f"  Entry Price: {pos.entry_price:.8f}")
            print(f"  Quantity:    {pos.quantity:.8f}")
            print(f"  Value:       £{pos.entry_value:.2f}")
            print(f"  Exchange:    {pos.exchange}")
            print("="*70)
            return True
        else:
            print("⚠️  Trade may not have been executed")
            print("   Check exchange for pending orders")
            return False
            
    except Exception as e:
        print(f"❌ Trade execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = force_trade()
    sys.exit(0 if success else 1)
