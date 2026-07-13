#!/usr/bin/env python
"""Live monitor for active positions, profit targets, and Batten Matrix readings."""
import json
import time
import os
from datetime import datetime
from pathlib import Path

def clear_screen():
    os.system('clear' if os.name != 'nt' else 'cls')

def get_current_price(symbol, exchange):
    """Get current price from exchange."""
    try:
        if exchange == 'kraken':
            from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
            client = get_kraken_client()
            ticker = client.get_ticker(symbol)
            return float(ticker.get('last', 0)) if ticker else 0
        elif exchange == 'binance':
            from aureon.exchanges.binance_client import BinanceClient, get_binance_client
            client = get_binance_client()
            ticker = client.get_ticker(symbol)
            return float(ticker.get('price', 0)) if ticker else 0
        elif exchange == 'alpaca':
            from aureon.exchanges.alpaca_client import AlpacaClient
            client = AlpacaClient()
            ticker = client.get_ticker(symbol)
            return float(ticker.get('last', 0)) if ticker else 0
    except Exception as e:
        return 0
    return 0

def monitor_live():
    """Monitor active positions and Batten Matrix in real-time."""
    
    while True:
        clear_screen()
        
        print("=" * 90)
        print("🦈 ORCA LIVE POSITION MONITOR - PROFIT TRACKING".center(90))
        print("=" * 90)
        print(f"Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 90)
        
        # Load active position
        position_file = Path('active_position.json')
        if position_file.exists():
            try:
                with open(position_file) as f:
                    pos = json.load(f)
                
                symbol = pos.get('symbol', 'Unknown')
                entry_price = pos.get('entry_price', 0)
                quantity = pos.get('quantity', 0)
                target_price = pos.get('target_price', 0)
                target_pct = pos.get('target_pct', 0)
                amount_usdc = pos.get('amount_usdc', 0)
                status = pos.get('status', 'unknown')
                notes = pos.get('notes', '')
                
                # Get current price (try to fetch live)
                current_price = get_current_price(symbol, 'kraken')
                if current_price == 0:
                    current_price = entry_price  # Fallback
                
                # Calculate profit/loss
                if entry_price > 0:
                    current_value = current_price * quantity
                    profit_usd = current_value - amount_usdc
                    profit_pct = ((current_price - entry_price) / entry_price) * 100
                    target_needed = target_price - current_price
                    target_pct_away = ((target_price - current_price) / current_price) * 100
                    
                    print(f"\n💰 ACTIVE POSITION:")
                    print(f"   Symbol: {symbol}")
                    print(f"   Status: {status.upper()}")
                    print(f"   Quantity: {quantity:.4f}")
                    print(f"\n📊 PRICES:")
                    print(f"   Entry:   ${entry_price:.6f}")
                    print(f"   Current: ${current_price:.6f}")
                    print(f"   Target:  ${target_price:.6f} ({target_pct:+.2f}%)")
                    print(f"\n💵 PROFIT/LOSS:")
                    print(f"   Invested: ${amount_usdc:.2f}")
                    print(f"   Current:  ${current_value:.2f}")
                    print(f"   P&L:      ${profit_usd:+.4f} ({profit_pct:+.3f}%)")
                    
                    # Progress bar to target
                    if target_pct_away > 0:
                        progress = max(0, min(100, (profit_pct / target_pct) * 100))
                        bar_length = 40
                        filled = int(bar_length * progress / 100)
                        bar = '█' * filled + '░' * (bar_length - filled)
                        print(f"\n🎯 TARGET PROGRESS: [{bar}] {progress:.1f}%")
                        print(f"   Need: ${target_needed:+.6f} ({target_pct_away:+.2f}%) to hit target")
                        
                        if profit_pct >= target_pct:
                            print(f"\n   🟢🟢🟢 TARGET HIT! PROFITABLE! READY TO SELL! 🟢🟢🟢")
                        elif profit_pct > 0:
                            print(f"\n   🟡 IN PROFIT (but below target)")
                        else:
                            print(f"\n   🔴 UNDERWATER (waiting for recovery)")
                    
                    if notes:
                        print(f"\n📝 Notes: {notes}")
                    
            except Exception as e:
                print(f"\n❌ Error loading position: {e}")
        else:
            print("\n⚠️ No active position found")
        
        # Load Batten Matrix readings
        print(f"\n{'=' * 90}")
        print("🎯 BATTEN MATRIX - COHERENCE × LAMBDA × PROBABILITY")
        print("=" * 90)
        
        try:
            from aureon.bridges.aureon_probability_nexus import SUBSYSTEM_STATE
            
            if SUBSYSTEM_STATE and len(SUBSYSTEM_STATE) > 0:
                print(f"\n✅ {len(SUBSYSTEM_STATE)} symbols with metrics:\n")
                
                for symbol, metrics in list(SUBSYSTEM_STATE.items())[:5]:
                    clarity = metrics.get('avg_clarity', 0)
                    coherence = metrics.get('avg_coherence', 0)
                    chaos = metrics.get('chaos', 0)
                    snapshot_count = metrics.get('snapshot_count', 0)
                    
                    # Calculate confidence and lambda
                    confidence = (clarity / 5.0) * 0.5 + coherence * 0.5
                    lambda_stability = max(0, 1 - chaos) if chaos > 0 else 0.5
                    
                    # Batten Matrix Score
                    score = coherence * lambda_stability * confidence
                    status = "🟢 PASS" if score >= 0.618 else "🔴 FAIL"
                    
                    print(f"{symbol:12s} | Score: {score:.4f} {status} | Coherence: {coherence:.3f} | λ: {lambda_stability:.3f} | Snapshots: {snapshot_count}")
            else:
                print("\n⏳ Waiting for data... (Probability Nexus collecting market snapshots)")
                
                # Check if orca is feeding
                if Path('/tmp/orca.log').exists():
                    with open('/tmp/orca.log') as f:
                        log_lines = f.readlines()
                        fed_lines = [l for l in log_lines if 'Fed' in l and 'snapshots' in l]
                        if fed_lines:
                            print(f"   Last feed: {fed_lines[-1].strip()}")
                        else:
                            print(f"   Orca hasn't scanned market yet (still initializing)")
                
        except Exception as e:
            print(f"\n⚠️ Batten Matrix not available: {e}")
        
        # Check orca process status
        print(f"\n{'=' * 90}")
        print("🦈 SYSTEM STATUS")
        print("=" * 90)
        
        try:
            result = os.popen("ps aux | grep -E '[o]rca_complete_kill_cycle' | awk '{print $2, $3, $4, $9}'").read().strip()
            if result:
                parts = result.split()
                pid = parts[0] if len(parts) > 0 else "?"
                cpu = parts[1] if len(parts) > 1 else "?"
                mem = parts[2] if len(parts) > 2 else "?"
                start_time = parts[3] if len(parts) > 3 else "?"
                print(f"   Orca PID: {pid} | CPU: {cpu}% | Memory: {mem}% | Started: {start_time}")
            else:
                print(f"   ⚠️ Orca not running!")
        except:
            pass
        
        print(f"\n{'=' * 90}")
        print("Press Ctrl+C to exit | Refreshing every 5 seconds...")
        print("=" * 90)
        
        time.sleep(5)

if __name__ == "__main__":
    try:
        monitor_live()
    except KeyboardInterrupt:
        print("\n\n✋ Monitor stopped by user\n")
