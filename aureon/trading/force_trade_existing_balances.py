#!/usr/bin/env python3
"""
🔥🔥🔥 FORCE TRADE USING EXISTING BALANCES 🔥🔥🔥
═══════════════════════════════════════════════════════════════════════════════

Uses ACTUAL held assets to execute trades and verify systems are connected.
Will sell small amounts of existing holdings to prove live trading works.

Gary Leckey | January 2026 | PROVE IT WORKS
═══════════════════════════════════════════════════════════════════════════════
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os

# Windows UTF-8 fix
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

# FORCE LIVE MODE
os.environ['LIVE'] = '1'
os.environ['KRAKEN_DRY_RUN'] = 'false'
os.environ['BINANCE_DRY_RUN'] = 'false'
os.environ['ALPACA_DRY_RUN'] = 'false'

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded .env file")
except ImportError:
    print("⚠️ python-dotenv not installed")

import time
import json
from datetime import datetime

print("\n" + "=" * 70)
print("🔥🔥🔥 FORCE TRADE USING EXISTING BALANCES 🔥🔥🔥")
print("=" * 70)
print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"   LIVE Mode: {os.getenv('LIVE', '0')}")
print("=" * 70 + "\n")

results = {
    'kraken': {'status': 'PENDING', 'trade': None, 'error': None},
    'binance': {'status': 'PENDING', 'trade': None, 'error': None},
    'alpaca': {'status': 'PENDING', 'trade': None, 'error': None},
}

# ════════════════════════════════════════════════════════════════════════════
# 🐙 KRAKEN - Sell small amount of TUSD or ESX
# ════════════════════════════════════════════════════════════════════════════
print("\n🐙 KRAKEN: Testing SELL with existing balance...")
try:
    from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
    
    kraken = get_kraken_client()
    print(f"   Dry Run Mode: {kraken.dry_run}")
    
    balance = kraken.get_balance()
    
    # Find tradeable assets (prioritize stablecoins, then regular assets)
    tradeable = [
        ('TUSD', balance.get('TUSD', 0), 'TUSDUSD', 5.0),     # TUSD → sell 5 for USD (min is 5)
        ('FIS', balance.get('FIS', 0), 'FISUSD', 5.0),        # Fis - min is usually 5
        ('TRX', balance.get('TRX', 0), 'TRXUSD', 5.0),        # TRX → sell for USD
        ('SCRT', balance.get('SCRT', 0), 'SCRTUSD', 5.0),     # Secret
        ('ROLL', balance.get('ROLL', 0), 'ROLLUSD', 5.0),     # Roll
    ]
    
    executed = False
    for asset, amount, pair, min_qty in tradeable:
        if amount > min_qty:
            try:
                print(f"   Found {asset}: {amount} - attempting to sell {min_qty}...")
                order = kraken.place_market_order(
                    symbol=pair,
                    side='sell',
                    quantity=min_qty
                )
                print(f"   ✅ KRAKEN SELL ORDER: {order}")
                results['kraken'] = {'status': 'SUCCESS', 'trade': order, 'error': None, 'asset': asset}
                executed = True
                break
            except Exception as e:
                print(f"   ⚠️ {asset} failed: {e}")
                continue
    
    if not executed:
        # Try to find ANY asset with value to trade
        print("   Looking for any tradeable asset...")
        for asset, amount in balance.items():
            if amount > 1.0 and asset not in ['USD', 'ZUSD', 'USDT', 'ZCAD', 'ZGBP']:
                try:
                    # Try common pair formats
                    for pair_format in [f"{asset}USD", f"X{asset}ZUSD", f"{asset}ZUSD"]:
                        try:
                            print(f"   Trying {pair_format} with {amount} {asset}...")
                            order = kraken.place_market_order(
                                symbol=pair_format,
                                side='sell',
                                quantity=min(amount * 0.1, 10)  # Sell 10% or max 10 units
                            )
                            print(f"   ✅ KRAKEN SELL ORDER: {order}")
                            results['kraken'] = {'status': 'SUCCESS', 'trade': order, 'error': None, 'asset': asset}
                            executed = True
                            break
                        except Exception:
                            continue
                    if executed:
                        break
                except Exception as e:
                    continue
    
    if not executed:
        print("   ⚠️ No viable assets found to trade")
        results['kraken'] = {'status': 'NO_TRADEABLE_ASSETS', 'trade': None, 'error': 'No tradeable assets found'}
        
except Exception as e:
    print(f"   ❌ Kraken error: {e}")
    results['kraken'] = {'status': 'CONNECTION_ERROR', 'trade': None, 'error': str(e)}

# ════════════════════════════════════════════════════════════════════════════
# 🟡 BINANCE - Sell small amount of IO or ZRO
# ════════════════════════════════════════════════════════════════════════════
print("\n🟡 BINANCE: Testing SELL with existing balance...")
try:
    from aureon.exchanges.binance_client import BinanceClient, get_binance_client
    
    binance = get_binance_client()
    print(f"   Dry Run Mode: {binance.dry_run}")
    
    balance = binance.get_balance()
    
    # Find tradeable assets - need to meet $5 minimum notional
    tradeable = [
        ('IO', balance.get('IO', 0), 'IOUSDT', 35.0),         # IO @ ~$0.16 → need ~35 for $5
        ('ZRO', balance.get('ZRO', 0), 'ZROUSDT', 3.0),       # ZRO @ ~$2 → need ~3 for $5  
        ('SENT', balance.get('SENT', 0), 'SENTUSDT', 200.0),  # SENT @ ~$0.027 → need ~200 for $5
        ('GUN', balance.get('GUN', 0), 'GUNUSDT', 150.0),     # GUN @ ~$0.034 → need ~150 for $5
    ]
    
    executed = False
    for asset, amount, pair, min_qty in tradeable:
        if amount > min_qty:
            try:
                print(f"   Found {asset}: {amount} - attempting to sell {min_qty}...")
                order = binance.place_market_order(
                    symbol=pair,
                    side='SELL',
                    quantity=min_qty
                )
                if order.get('error'):
                    print(f"   ⚠️ {asset} failed: {order}")
                    continue
                print(f"   ✅ BINANCE SELL ORDER: {order}")
                results['binance'] = {'status': 'SUCCESS', 'trade': order, 'error': None, 'asset': asset}
                executed = True
                break
            except Exception as e:
                print(f"   ⚠️ {asset} failed: {e}")
                continue
    
    if not executed:
        print("   ⚠️ No viable assets found to trade")
        results['binance'] = {'status': 'NO_TRADEABLE_ASSETS', 'trade': None, 'error': 'No tradeable assets'}
        
except Exception as e:
    print(f"   ❌ Binance error: {e}")
    results['binance'] = {'status': 'CONNECTION_ERROR', 'trade': None, 'error': str(e)}

# ════════════════════════════════════════════════════════════════════════════
# 🦙 ALPACA - Check if we can do any crypto or fractional stock trade
# ════════════════════════════════════════════════════════════════════════════
print("\n🦙 ALPACA: Testing trade with existing balance...")
try:
    from aureon.exchanges.alpaca_client import AlpacaClient
    
    alpaca = AlpacaClient()
    
    # Check if paper mode
    is_paper = 'paper' in str(getattr(alpaca, 'base_url', '')).lower()
    print(f"   Paper Mode: {is_paper}")
    
    account = alpaca.get_account()
    buying_power = float(account.get('buying_power', 0))
    cash = float(account.get('cash', 0))
    print(f"   Cash: ${cash:.2f}")
    print(f"   Buying Power: ${buying_power:.2f}")
    
    # Check existing positions
    positions = alpaca.get_positions()
    print(f"   Positions: {len(positions)}")
    
    executed = False
    
    # Try to sell a small amount of an existing position
    if positions:
        for pos in positions:
            symbol = pos.get('symbol', '')
            qty = float(pos.get('qty', 0))
            if qty > 0.01:
                try:
                    sell_qty = min(qty * 0.1, 0.1)  # Sell 10% or 0.1, whichever is smaller
                    is_crypto = '/' in symbol or symbol.endswith('USD')
                    print(f"   Found position {symbol}: {qty} - attempting to sell {sell_qty}...")
                    order = alpaca.place_order(
                        symbol=symbol,
                        qty=sell_qty,
                        side='sell',
                        type='market',
                        time_in_force='ioc' if is_crypto else 'day'  # IOC for crypto, day for stocks
                    )
                    if order and not order.get('error'):
                        print(f"   ✅ ALPACA SELL ORDER: {order}")
                        results['alpaca'] = {'status': 'SUCCESS', 'trade': order, 'error': None, 'asset': symbol}
                        executed = True
                        break
                    else:
                        print(f"   ⚠️ {symbol} order returned: {order}")
                except Exception as e:
                    print(f"   ⚠️ {symbol} failed: {e}")
                    continue
    
    # If no positions to sell, try to buy with available cash
    if not executed and buying_power >= 1.0:
        try:
            print(f"   Attempting to buy $1 of BTC/USD...")
            order = alpaca.place_order(
                symbol='BTC/USD',
                qty=None,
                side='buy',
                type='market',
                time_in_force='gtc',
                notional=1.0
            )
            print(f"   ✅ ALPACA BUY ORDER: {order}")
            results['alpaca'] = {'status': 'SUCCESS', 'trade': order, 'error': None, 'asset': 'BTC/USD'}
            executed = True
        except Exception as e:
            print(f"   ⚠️ BTC/USD buy failed: {e}")
    
    if not executed:
        print("   ⚠️ No viable trades available")
        results['alpaca'] = {'status': 'NO_TRADEABLE_ASSETS', 'trade': None, 'error': 'No viable trades'}
        
except Exception as e:
    print(f"   ❌ Alpaca error: {e}")
    results['alpaca'] = {'status': 'CONNECTION_ERROR', 'trade': None, 'error': str(e)}

# ════════════════════════════════════════════════════════════════════════════
# 📊 FINAL RESULTS
# ════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("📊 FORCE TRADE RESULTS - ALL PLATFORMS")
print("=" * 70)

success_count = 0
for platform, result in results.items():
    emoji = "✅" if result['status'] == 'SUCCESS' else "❌"
    if result['status'] == 'SUCCESS':
        success_count += 1
    print(f"   {emoji} {platform.upper()}: {result['status']}")
    if result.get('asset'):
        print(f"      Asset: {result['asset']}")
    if result['error']:
        print(f"      Error: {result['error']}")
    if result['trade']:
        trade_str = str(result['trade'])[:150]
        print(f"      Trade: {trade_str}...")

print("\n" + "=" * 70)
print(f"🎯 SUMMARY: {success_count}/3 platforms executed trades successfully")
if success_count == 3:
    print("🔥🔥🔥 ALL SYSTEMS OPERATIONAL - LIVE TRADING CONFIRMED! 🔥🔥🔥")
elif success_count > 0:
    print("⚠️ PARTIAL SUCCESS - Some platforms working!")
else:
    print("❌ NO TRADES EXECUTED - CHECK API KEYS AND BALANCES!")
print("=" * 70)

# Save results
with open('force_trade_results.json', 'w') as f:
    json.dump({
        'timestamp': datetime.now().isoformat(),
        'live_mode': os.getenv('LIVE', '0'),
        'results': results
    }, f, indent=2, default=str)
print(f"\n📁 Results saved to force_trade_results.json")
