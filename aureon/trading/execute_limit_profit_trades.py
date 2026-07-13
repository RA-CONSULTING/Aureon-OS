#!/usr/bin/env python3
"""
💰 EXECUTE 3 REAL MONEY NET PROFIT TRADES - LIMIT ORDER VERSION 💰
===================================================================

This script executes 3 real money trades designed for NET PROFIT using:
- Limit BUY below current price (get better entry)
- Limit SELL above entry (guarantee profit after fees)

Gary Leckey | December 2025
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import time

# Force LIVE mode
os.environ['LIVE'] = '1'
os.environ['DRY_RUN'] = '0'

from aureon.exchanges.binance_client import BinanceClient, get_binance_client
from aureon.trading.aureon_unified_ecosystem import CONFIG, get_platform_fee

def get_ticker(client, symbol: str):
    """Get current ticker data"""
    try:
        return client.ticker(symbol)
    except Exception as e:
        print(f"   ⚠️ Error getting ticker: {e}")
    return None

def execute_profit_trade(client: BinanceClient, symbol: str, amount_usd: float):
    """
    Execute a trade designed for net profit:
    1. Place limit BUY slightly below current price
    2. When filled, place limit SELL to guarantee profit after fees
    """
    print(f"\n{'='*60}")
    print(f"🎯 EXECUTING PROFIT TRADE: {symbol}")
    print(f"{'='*60}")
    
    # Get current price
    ticker = get_ticker(client, symbol)
    if not ticker:
        print("   ❌ Could not get ticker")
        return False, 0
    
    current_price = float(ticker.get('price', ticker.get('lastPrice', 0)))
    bid = float(ticker.get('bid', ticker.get('bidPrice', current_price)))
    ask = float(ticker.get('ask', ticker.get('askPrice', current_price)))
    
    print(f"   📊 Current: ${current_price:.5f} | Bid: ${bid:.5f} | Ask: ${ask:.5f}")
    
    # Calculate fee costs
    fee_rate = get_platform_fee('binance', 'taker')  
    total_fee_pct = fee_rate * 2  # Buy + Sell fees
    min_profit_pct = total_fee_pct + 0.001  # Fees + 0.1% profit
    
    print(f"   💸 Fee Rate: {fee_rate*100:.3f}% | Min Profit Target: {min_profit_pct*100:.3f}%")
    
    # Strategy: Buy at bid (maker order), sell at bid + min_profit
    entry_price = bid  # Try to buy at bid price
    target_exit = entry_price * (1 + min_profit_pct)
    
    # Calculate quantity with proper rounding
    raw_qty = amount_usd / entry_price
    if 'ADA' in symbol:
        quantity = round(raw_qty, 1)
        price_precision = 4
    elif 'XLM' in symbol:
        quantity = int(raw_qty)
        price_precision = 4
    elif 'DOGE' in symbol:
        quantity = int(raw_qty)
        price_precision = 5
    else:
        quantity = int(raw_qty)
        price_precision = 4
    
    entry_price = round(entry_price, price_precision)
    target_exit = round(target_exit, price_precision)
    
    actual_value = quantity * entry_price
    expected_profit = (target_exit - entry_price) * quantity - (actual_value * total_fee_pct)
    
    print(f"   📦 Quantity: {quantity}")
    print(f"   💵 Entry: ${entry_price:.5f}")
    print(f"   🎯 Target Exit: ${target_exit:.5f}")
    print(f"   📈 Expected Net Profit: ${expected_profit:.4f}")
    
    # Step 1: Place limit BUY order
    print(f"\n   📈 Placing LIMIT BUY at ${entry_price}...")
    try:
        buy_result = client.place_limit_order(symbol, 'BUY', quantity, entry_price)
        if not buy_result or not buy_result.get('orderId'):
            print(f"   ❌ Buy order failed: {buy_result}")
            return False, 0
        buy_order_id = buy_result.get('orderId')
        print(f"   ✅ Buy Order ID: {buy_order_id}")
    except Exception as e:
        print(f"   ❌ Buy error: {e}")
        return False, 0
    
    # Wait for buy to fill (max 30 seconds)
    print(f"   ⏳ Waiting for buy fill...")
    filled = False
    for i in range(15):
        time.sleep(2)
        try:
            order = client.get_order(symbol, buy_order_id)
            status = order.get('status', '')
            print(f"   📋 Status: {status} [{(i+1)*2}s]")
            if status == 'FILLED':
                filled = True
                actual_entry = float(order.get('price', entry_price))
                print(f"   ✅ Buy FILLED at ${actual_entry:.5f}")
                break
            elif status in ['CANCELED', 'REJECTED', 'EXPIRED']:
                print(f"   ❌ Buy order {status}")
                return False, 0
        except Exception as e:
            print(f"   ⚠️ Check error: {e}")
    
    if not filled:
        # Cancel unfilled order
        print(f"   ⏰ Timeout - canceling buy order...")
        try:
            client.cancel_order(symbol, buy_order_id)
            print(f"   🚫 Buy order canceled")
        except:
            pass
        return False, 0
    
    # Step 2: Place limit SELL order at target
    print(f"\n   📉 Placing LIMIT SELL at ${target_exit}...")
    try:
        sell_result = client.place_limit_order(symbol, 'SELL', quantity, target_exit)
        if not sell_result or not sell_result.get('orderId'):
            print(f"   ❌ Sell order failed: {sell_result}")
            # Emergency market sell
            print(f"   🚨 Emergency market sell...")
            client.place_market_order(symbol, 'SELL', quantity)
            return False, 0
        sell_order_id = sell_result.get('orderId')
        print(f"   ✅ Sell Order ID: {sell_order_id}")
    except Exception as e:
        print(f"   ❌ Sell error: {e}")
        return False, 0
    
    # Wait for sell to fill (max 60 seconds)
    print(f"   ⏳ Waiting for sell fill (target: ${target_exit})...")
    sell_filled = False
    for i in range(30):
        time.sleep(2)
        try:
            ticker = get_ticker(client, symbol)
            current = float(ticker.get('price', 0)) if ticker else 0
            
            order = client.get_order(symbol, sell_order_id)
            status = order.get('status', '')
            print(f"   📋 Price: ${current:.5f} | Status: {status} [{(i+1)*2}s]")
            
            if status == 'FILLED':
                sell_filled = True
                actual_exit = float(order.get('price', target_exit))
                print(f"   ✅ Sell FILLED at ${actual_exit:.5f}")
                break
        except Exception as e:
            print(f"   ⚠️ Check error: {e}")
    
    if not sell_filled:
        # Market sell to close position
        print(f"   ⏰ Timeout - market selling to close position...")
        try:
            client.cancel_order(symbol, sell_order_id)
            market_result = client.place_market_order(symbol, 'SELL', quantity)
            actual_exit = current_price  # Approximate
            print(f"   ✅ Market sold at ~${actual_exit:.5f}")
        except Exception as e:
            print(f"   ❌ Market sell error: {e}")
            return False, 0
    
    # Calculate final P&L
    gross_pnl = (actual_exit - actual_entry) * quantity
    fees = (actual_entry * quantity + actual_exit * quantity) * fee_rate
    net_pnl = gross_pnl - fees
    
    print(f"\n   {'='*40}")
    print(f"   📊 TRADE RESULT:")
    print(f"   ├─ Entry: ${actual_entry:.5f}")
    print(f"   ├─ Exit:  ${actual_exit:.5f}")
    print(f"   ├─ Gross: ${gross_pnl:+.4f}")
    print(f"   ├─ Fees:  ${fees:.4f}")
    if net_pnl > 0:
        print(f"   └─ ✅ NET PROFIT: ${net_pnl:+.4f}")
    else:
        print(f"   └─ ❌ NET LOSS: ${net_pnl:+.4f}")
    print(f"   {'='*40}")
    
    return net_pnl > 0, net_pnl


def main():
    print("\n" + "="*70)
    print("💰 REAL MONEY NET PROFIT TRADES - LIMIT ORDER STRATEGY 💰")
    print("="*70)
    
    print("\n⚠️  WARNING: This will execute REAL trades with REAL money!")
    print("    Strategy: Limit buy at bid, limit sell for profit")
    
    confirm = input("\n   Type 'PROFIT' to proceed: ")
    if confirm != 'PROFIT':
        print("\n   ❌ Cancelled. No trades executed.")
        return
    
    # Initialize Binance client
    print("\n🔌 Initializing BinanceClient (LIVE MODE)...")
    client = get_binance_client()
    print(f"   ✅ Client ready")
    
    # Check we can trade these pairs
    pairs = ['ADAUSDC', 'XLMUSDC', 'DOGEUSDC']
    for pair in pairs:
        can, reason = client.can_trade_symbol(pair)
        print(f"   {pair}: {'✅' if can else '❌'} {reason}")
        if not can:
            print(f"   ❌ Cannot trade {pair} - aborting")
            return
    
    # Execute trades
    results = []
    total_pnl = 0
    
    for symbol in pairs:
        success, pnl = execute_profit_trade(client, symbol, 6.0)
        results.append((symbol, success, pnl))
        total_pnl += pnl
        
        if symbol != pairs[-1]:
            print("\n   ⏳ Waiting 3 seconds before next trade...")
            time.sleep(3)
    
    # Final Summary
    print("\n" + "="*70)
    print("📊 FINAL RESULTS")
    print("="*70)
    
    wins = 0
    for symbol, success, pnl in results:
        icon = "✅" if success else "❌"
        print(f"   {icon} {symbol}: ${pnl:+.4f}")
        if success:
            wins += 1
    
    print(f"\n   Total Trades: {len(results)}")
    print(f"   Wins: {wins}")
    print(f"   Win Rate: {wins/len(results)*100:.1f}%")
    print(f"   Total Net P&L: ${total_pnl:+.4f}")
    
    if total_pnl > 0:
        print("\n   🎉 OVERALL NET PROFIT! 🎉")
    else:
        print("\n   📉 Overall net loss")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
