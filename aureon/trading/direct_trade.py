#!/usr/bin/env python3
"""
🔥 DIRECT FORCE TRADE - Execute a real trade using your USDT balance 🔥

This bypasses all the ecosystem complexity and directly places a Binance order.
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from aureon.exchanges.binance_client import BinanceClient, get_binance_client
from datetime import datetime

def direct_trade(symbol: str = None, amount_usdt: float = 15.0):
    """Execute a direct market buy on Binance"""
    
    print("\n" + "="*70)
    print("🔥 DIRECT BINANCE TRADE 🔥")
    print("="*70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    client = get_binance_client()
    
    # Check balance
    account = client.account()
    usdc_balance = 0
    usdt_balance = 0
    
    for bal in account.get('balances', []):
        asset = bal.get('asset', '')
        free = float(bal.get('free', 0))
        if asset == 'LDUSDC':
            usdc_balance = free
        elif asset == 'USDT':
            usdt_balance = free
        elif asset == 'USDC':
            usdc_balance += free
    
    print(f"💰 Available Balance:")
    print(f"   LDUSDC: ${usdc_balance:.2f}")
    print(f"   USDT:   ${usdt_balance:.2f}")
    print()
    
    # LDUSDC needs to be converted first - let's check for any USDT
    if usdt_balance < 10 and usdc_balance < 10:
        print("❌ Insufficient balance. Need at least $10 USDT or USDC.")
        print("   Your LDUSDC (Lido staked USDC) needs to be unstaked first.")
        return False
    
    # If no symbol specified, pick a good one
    if not symbol:
        symbol = "BTCUSDT"  # Default to BTC
    
    # Ensure it's a USDT pair
    if not symbol.endswith('USDT'):
        symbol = symbol.replace('GBP', 'USDT').replace('USD', 'USDT')
        if not symbol.endswith('USDT'):
            symbol = symbol + 'USDT'
    
    print(f"🎯 Target: {symbol}")
    print(f"💵 Amount: ${amount_usdt:.2f}")
    print()
    
    # Get current price
    try:
        tickers = client.get_24h_tickers()
        price = None
        for t in tickers:
            if t.get('symbol') == symbol:
                price = float(t.get('lastPrice', 0))
                change = float(t.get('priceChangePercent', 0))
                break
        
        if not price:
            print(f"❌ Could not find price for {symbol}")
            return False
        
        print(f"📈 Current Price: ${price:.8f}")
        print(f"📊 24h Change: {change:+.2f}%")
        print()
        
        # Calculate quantity
        quantity = amount_usdt / price
        
        # Round to appropriate precision (depends on asset)
        if 'BTC' in symbol:
            quantity = round(quantity, 5)
        elif 'ETH' in symbol:
            quantity = round(quantity, 4)
        else:
            quantity = round(quantity, 2)
        
        print(f"📦 Quantity: {quantity}")
        print()
        
        print("="*70)
        print("⚠️  EXECUTING REAL TRADE...")
        print("="*70)
        
        # Execute market buy
        result = client.market_buy(symbol, quantity)
        
        if result and result.get('status') == 'FILLED':
            print()
            print("="*70)
            print("✅ TRADE EXECUTED SUCCESSFULLY!")
            print("="*70)
            print(f"  Order ID:    {result.get('orderId')}")
            print(f"  Symbol:      {result.get('symbol')}")
            print(f"  Side:        {result.get('side')}")
            print(f"  Quantity:    {result.get('executedQty')}")
            print(f"  Price:       ${float(result.get('cummulativeQuoteQty', 0)) / float(result.get('executedQty', 1)):.8f}")
            print(f"  Total Cost:  ${result.get('cummulativeQuoteQty')}")
            print("="*70)
            return True
        else:
            print(f"❌ Order failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Trade failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else None
    amount = float(sys.argv[2]) if len(sys.argv) > 2 else 15.0
    
    success = direct_trade(symbol, amount)
    sys.exit(0 if success else 1)
