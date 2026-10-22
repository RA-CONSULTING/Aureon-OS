#!/usr/bin/env python3
"""
🇮🇪🎯 AUTO SNIPER - CONTINUOUS PENNY PROFIT KILLER 🎯🇮🇪

This runs continuously, checking all positions every 30 seconds
and automatically executing kills when penny profit is confirmed.

The boys make their kills automatically - no intervention needed.

Usage: python3 auto_sniper.py

Press Ctrl+C to stop.
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# State file
STATE_FILE = os.getenv('AUREON_STATE_FILE', 'aureon_kraken_state.json')
CHECK_INTERVAL = 30  # seconds between scans


def load_state() -> Dict:
    """Load current state file"""
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Cannot load state: {e}")
        return {}


def save_state(state: Dict):
    """Save state file"""
    try:
        state['timestamp'] = time.time()
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"⚠️ State save error: {e}")


def get_fee_rate(exchange: str) -> float:
    """Get total cost rate (fee + slippage + spread)"""
    base_fees = {
        'binance': 0.001,
        'kraken': 0.0026,
        'alpaca': 0.0025,
        'capital': 0.001,
    }
    fee = base_fees.get(exchange.lower(), 0.002)
    slippage = 0.002
    spread = 0.001
    return fee + slippage + spread


def check_and_kill(client, state: Dict) -> Tuple[int, float]:
    """
    Check all positions and execute kills on confirmed penny profits.
    Returns (kills_count, total_net_pnl)
    """
    positions = state.get('positions', {})
    if not positions:
        return 0, 0.0
    
    kills = 0
    total_net = 0.0
    to_remove = []
    
    for symbol, pos in positions.items():
        exchange = pos.get('exchange', 'kraken')
        entry_value = float(pos.get('entry_value', 0) or 0)
        quantity = float(pos.get('quantity', 0) or 0)
        
        if entry_value <= 0 or quantity <= 0:
            continue
        
        # Get current price
        try:
            ticker = client.get_ticker(exchange, symbol)
            if not ticker:
                continue
            current_price = float(ticker.get('price', 0) or 0)
            if current_price <= 0:
                continue
        except Exception as e:
            continue
        
        # Calculate P&L
        current_value = quantity * current_price
        gross_pnl = current_value - entry_value
        
        # Calculate net P&L after all costs
        total_rate = get_fee_rate(exchange)
        entry_fee = float(pos.get('entry_fee', 0) or entry_value * total_rate)
        exit_fee = current_value * total_rate
        net_pnl = gross_pnl - entry_fee - exit_fee
        
        pnl_pct = (gross_pnl / entry_value * 100) if entry_value > 0 else 0
        
        # 🎯 KILL CONDITION: Net profit >= $0.01 (one penny)
        if net_pnl >= 0.0001:
            print(f"   🎯 KILL TARGET: {exchange.upper()} {symbol}")
            print(f"      Entry: ${entry_value:.2f} | Now: ${current_value:.2f}")
            print(f"      Gross: ${gross_pnl:+.4f} ({pnl_pct:+.2f}%) | Net: ${net_pnl:+.4f}")
            
            # Execute the kill
            try:
                result = client.place_market_order(exchange, symbol, 'SELL', quantity=quantity)
                
                if result and not result.get('error') and not result.get('rejected'):
                    order_id = result.get('txid') or result.get('orderId') or result.get('id')
                    if order_id:
                        print(f"      ✅ KILL CONFIRMED! Order: {order_id}")
                        print(f"      💰 Net Profit: ${net_pnl:+.4f}")
                        to_remove.append(symbol)
                        kills += 1
                        total_net += net_pnl
                    else:
                        print(f"      ⚠️ Order placed but no ID: {result}")
                else:
                    error = result.get('reason', result.get('error', 'Unknown')) if result else 'No response'
                    print(f"      ❌ BLOCKED: {error}")
                    
            except Exception as e:
                print(f"      ❌ Error: {e}")
            
            time.sleep(0.5)  # Rate limit
    
    # Remove killed positions from state
    for symbol in to_remove:
        if symbol in state.get('positions', {}):
            del state['positions'][symbol]
    
    # Update stats
    if kills > 0:
        state['wins'] = state.get('wins', 0) + kills
        state['total_trades'] = state.get('total_trades', 0) + kills
        state['harvested'] = state.get('harvested', 0) + max(0, total_net)
        state['balance'] = state.get('balance', 0) + max(0, total_net)
        save_state(state)
    
    return kills, total_net


def show_status(client, state: Dict):
    """Show current position status"""
    positions = state.get('positions', {})
    
    print(f"\n{'─'*60}")
    print(f"📊 POSITION STATUS ({len(positions)} active)")
    print(f"{'─'*60}")
    
    for symbol, pos in positions.items():
        exchange = pos.get('exchange', 'kraken')
        entry_value = float(pos.get('entry_value', 0) or 0)
        quantity = float(pos.get('quantity', 0) or 0)
        
        if entry_value <= 0:
            continue
        
        # Get current price
        try:
            ticker = client.get_ticker(exchange, symbol)
            current_price = float(ticker.get('price', 0) or 0) if ticker else 0
        except:
            current_price = 0
        
        if current_price > 0:
            current_value = quantity * current_price
            gross_pnl = current_value - entry_value
            
            total_rate = get_fee_rate(exchange)
            entry_fee = float(pos.get('entry_fee', 0) or entry_value * total_rate)
            exit_fee = current_value * total_rate
            net_pnl = gross_pnl - entry_fee - exit_fee
            
            if net_pnl >= 0.0001:
                status = "🎯 KILL READY"
            elif gross_pnl > 0:
                status = "⏳ Waiting"
            else:
                status = "🛡️ Holding"
            
            print(f"   {exchange.upper():8s} {symbol:12s} | Net: ${net_pnl:+.4f} | {status}")
        else:
            print(f"   {exchange.upper():8s} {symbol:12s} | ❓ No price")
    
    print(f"{'─'*60}\n")


def main():
    print("=" * 60)
    print("🇮🇪🎯 AUTO SNIPER - THE BOYS MAKE THEIR KILLS 🎯🇮🇪")
    print("=" * 60)
    print()
    print(f"State File: {STATE_FILE}")
    print(f"Check Interval: {CHECK_INTERVAL}s")
    print()
    print("☘️ \"The sniper never sleeps. Every penny will be taken.\"")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()
    
    # Import exchange client
    try:
        from aureon.trading.unified_exchange_client import MultiExchangeClient
        client = MultiExchangeClient()
    except ImportError as e:
        print(f"❌ Cannot import MultiExchangeClient: {e}")
        sys.exit(1)
    
    # Stats
    total_kills = 0
    total_profit = 0.0
    start_time = time.time()
    
    try:
        while True:
            now = datetime.now().strftime("%H:%M:%S")
            
            # Load fresh state
            state = load_state()
            if not state:
                print(f"[{now}] ⚠️ No state file")
                time.sleep(CHECK_INTERVAL)
                continue
            
            positions = state.get('positions', {})
            print(f"[{now}] 🔍 Scanning {len(positions)} positions...")
            
            # Check and execute kills
            kills, net_pnl = check_and_kill(client, state)
            
            if kills > 0:
                total_kills += kills
                total_profit += net_pnl
                print(f"\n   🎯 SESSION: {total_kills} kills | ${total_profit:+.4f} total")
            
            # Show status every 5 minutes
            elapsed = time.time() - start_time
            if int(elapsed) % 300 < CHECK_INTERVAL:
                show_status(client, state)
            
            # Wait for next scan
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n")
        print("=" * 60)
        print("🇮🇪 AUTO SNIPER STOOD DOWN")
        print(f"   Total Kills: {total_kills}")
        print(f"   Total Profit: ${total_profit:+.4f}")
        print(f"   Runtime: {(time.time() - start_time) / 60:.1f} minutes")
        print("=" * 60)


if __name__ == "__main__":
    main()
