#!/usr/bin/env python3
"""
AUREON TRADING - COMPLETE MULTI-EXCHANGE TRADE LOG GENERATOR
Shows journey from losses to gains with timestamps
Run this on Windows: python trade_log.py

Syncs trades from ALL exchanges:
- Kraken
- Binance

Also saves trade data in brain-compatible format for adaptive learning.
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import krakenex
import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def get_kraken_trades():
    """Get all trades from Kraken."""
    kraken = krakenex.API()
    kraken.key = os.getenv('KRAKEN_API_KEY')
    kraken.secret = os.getenv('KRAKEN_API_SECRET')
    
    if not kraken.key or not kraken.secret:
        print("   ⚠️ Kraken API keys not configured")
        return []
    
    result = kraken.query_private('TradesHistory', {'trades': True})
    
    if result.get('error'):
        print(f"   ❌ Kraken Error: {result['error']}")
        return []
    
    trades = result.get('result', {}).get('trades', {})
    trade_list = []
    
    for tid, trade in trades.items():
        trade_list.append({
            'exchange': 'kraken',
            'pair': trade.get('pair', ''),
            'side': trade.get('type', '').upper(),
            'price': float(trade.get('price', 0)),
            'quantity': float(trade.get('vol', 0)),
            'cost': float(trade.get('cost', 0)),
            'fee': float(trade.get('fee', 0)),
            'time': float(trade.get('time', 0)),
        })
    
    return trade_list


def get_binance_trades():
    """Get all trades from Binance."""
    try:
        from aureon.exchanges.binance_client import BinanceClient, get_binance_client
        
        binance_key = os.getenv('BINANCE_API_KEY')
        binance_secret = os.getenv('BINANCE_API_SECRET')
        
        if not binance_key or not binance_secret:
            print("   ⚠️ Binance API keys not configured")
            return []
        
        binance = get_binance_client()
        all_trades = binance.get_all_my_trades()
        
        trade_list = []
        for symbol, trades in all_trades.items():
            for trade in trades:
                trade_list.append({
                    'exchange': 'binance',
                    'pair': symbol,
                    'side': 'BUY' if trade.get('isBuyer') else 'SELL',
                    'price': float(trade.get('price', 0)),
                    'quantity': float(trade.get('qty', 0)),
                    'cost': float(trade.get('quoteQty', 0)),
                    'fee': float(trade.get('commission', 0)),
                    'time': trade.get('time', 0) / 1000,  # Convert from ms
                })
        
        return trade_list
        
    except Exception as e:
        print(f"   ⚠️ Binance error: {e}")
        return []


def generate_trade_log():
    # Get trades from ALL exchanges
    print("🔄 Fetching trades from all exchanges...")
    
    kraken_trades = get_kraken_trades()
    print(f"   🦑 Kraken: {len(kraken_trades)} trades")
    
    binance_trades = get_binance_trades()
    print(f"   🟡 Binance: {len(binance_trades)} trades")
    
    # Combine and sort all trades
    all_trades = kraken_trades + binance_trades
    all_trades.sort(key=lambda x: x['time'])
    
    if not all_trades:
        print("❌ No trades found on any exchange!")
        return
    
    print("=" * 140)
    print("📜 COMPLETE MULTI-EXCHANGE TRADE HISTORY - AUREON TRADING JOURNEY")
    print("=" * 140)
    
    starting_capital = 93.21  # GBP
    
    print(f"\n💰 Starting Capital: £{starting_capital:.2f}")
    print(f"📅 Trade Period: {datetime.fromtimestamp(all_trades[0]['time']).strftime('%Y-%m-%d')} to {datetime.fromtimestamp(all_trades[-1]['time']).strftime('%Y-%m-%d')}")
    print(f"🌐 Exchanges: Kraken ({len(kraken_trades)}) | Binance ({len(binance_trades)})")
    print("-" * 140)
    
    # Track holdings and P&L per exchange
    pair_holdings = {}
    running_cash = starting_capital
    total_fees = 0
    wins = 0
    losses = 0
    brain_trades = []
    
    # Print header
    print(f"{'#':>3} | {'Exch':<6} | {'Timestamp':<20} | {'Action':<6} | {'Pair':<14} | {'Quantity':>14} | {'Price':>14} | {'Value':>12} | {'Running P&L':>14}")
    print("-" * 140)
    
    for i, trade in enumerate(all_trades, 1):
        ts = datetime.fromtimestamp(trade['time']).strftime('%Y-%m-%d %H:%M:%S')
        exchange = trade['exchange']
        pair = trade['pair']
        side = trade['side']
        price = trade['price']
        qty = trade['quantity']
        cost = trade['cost']
        fee = trade['fee']
        
        # Use exchange:pair as key to track holdings per exchange
        holding_key = f"{exchange}:{pair}"
        
        total_fees += fee
        realized_pnl = 0
        cost_of_sold = 0
        avg_cost = price
        
        if side == 'BUY':
            running_cash -= (cost + fee)
            if holding_key not in pair_holdings:
                pair_holdings[holding_key] = {'qty': 0, 'cost_basis': 0, 'entry_time': trade['time']}
            pair_holdings[holding_key]['qty'] += qty
            pair_holdings[holding_key]['cost_basis'] += cost + fee
            pair_holdings[holding_key]['entry_time'] = trade['time']
            emoji = "🔵"
        else:  # SELL
            running_cash += (cost - fee)
            if holding_key in pair_holdings and pair_holdings[holding_key]['qty'] > 0:
                avg_cost = pair_holdings[holding_key]['cost_basis'] / pair_holdings[holding_key]['qty']
                cost_of_sold = avg_cost * qty
                proceeds = cost - fee
                realized_pnl = proceeds - cost_of_sold
                
                if realized_pnl >= 0:
                    wins += 1
                    emoji = "🟢"
                else:
                    losses += 1
                    emoji = "🔴"
                
                pair_holdings[holding_key]['qty'] -= qty
                pair_holdings[holding_key]['cost_basis'] -= cost_of_sold
                
                # Save for brain
                brain_trades.append({
                    'symbol': pair,
                    'exchange': exchange,
                    'entry_price': avg_cost / qty if qty > 0 else price,
                    'exit_price': price,
                    'pnl': realized_pnl,
                    'pnl_pct': (realized_pnl / cost_of_sold * 100) if cost_of_sold > 0 else 0,
                    'entry_time': pair_holdings.get(holding_key, {}).get('entry_time', trade['time']),
                    'exit_time': trade['time'],
                    'quantity': qty,
                    'frequency': 432,
                    'coherence': 0.5,
                    'score': 70,
                    'probability': 0.6,
                    'hnc_action': 'HOLD',
                    'source': f'{exchange}_log'
                })
            else:
                emoji = "⚪"
        
        net_change = running_cash - starting_capital
        status = "🟢" if net_change >= 0 else "🔴"
        
        exch_short = "🦑KRK" if exchange == 'kraken' else "🟡BIN"
        pnl_str = f"{status} £{net_change:+.2f}"
        if side == 'SELL' and realized_pnl != 0:
            pnl_str += f" ({realized_pnl:+.2f})"
        
        print(f"{i:>3} | {exch_short:<6} | {ts:<20} | {emoji} {side:<4} | {pair:<14} | {qty:>14.8f} | ${price:>13.6f} | ${cost:>11.2f} | {pnl_str}")
    
    print("-" * 140)
    
    # Current holdings
    print(f"\n📊 CURRENT HOLDINGS (Unrealized):")
    print("-" * 70)
    
    total_holding_value = 0
    for key, holding in pair_holdings.items():
        if holding['qty'] > 0.0001:
            exchange, pair = key.split(':', 1)
            avg_cost = holding['cost_basis'] / holding['qty'] if holding['qty'] > 0 else 0
            exch_emoji = "🦑" if exchange == 'kraken' else "🟡"
            print(f"   {exch_emoji} {pair}: {holding['qty']:.8f} @ avg ${avg_cost:.6f} (cost: ${holding['cost_basis']:.2f})")
            total_holding_value += holding['cost_basis']
    
    if total_holding_value == 0:
        print("   (No open positions)")
    
    print("-" * 70)
    
    # Final summary
    final_cash_pnl = running_cash - starting_capital
    
    print(f"\n" + "=" * 140)
    print(f"📈 MULTI-EXCHANGE TRADING JOURNEY SUMMARY")
    print(f"=" * 140)
    print(f"   💰 Starting Capital:     £{starting_capital:.2f}")
    print(f"   💵 Current Cash:         £{running_cash:.2f}")
    print(f"   📦 In Open Positions:    ${total_holding_value:.2f}")
    print(f"   💸 Total Fees Paid:      ${total_fees:.4f}")
    print(f"   ")
    print(f"   📊 Total Trades:         {len(all_trades)}")
    print(f"      🦑 Kraken:            {len(kraken_trades)}")
    print(f"      🟡 Binance:           {len(binance_trades)}")
    print(f"   🟢 Winning Trades:       {wins}")
    print(f"   🔴 Losing Trades:        {losses}")
    print(f"   📈 Win Rate:             {(wins/(wins+losses)*100) if (wins+losses) > 0 else 0:.1f}%")
    print(f"   ")
    print(f"   💎 Cash P&L:             £{final_cash_pnl:+.2f} ({(final_cash_pnl/starting_capital)*100:+.1f}%)")
    print(f"   ")
    
    if final_cash_pnl >= 0:
        print(f"   ✅ STATUS: NET POSITIVE - Recovered all losses and in profit!")
    else:
        print(f"   ⚠️ STATUS: Cash shows drawdown but open positions contain value")
    
    print(f"=" * 140)
    
    # Save to file
    with open('trade_log_output.txt', 'w', encoding='utf-8') as f:
        f.write(f"AUREON TRADING - MULTI-EXCHANGE TRADE LOG\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Exchanges: Kraken ({len(kraken_trades)}) | Binance ({len(binance_trades)})\n")
        f.write(f"Starting: £{starting_capital:.2f} | Trades: {len(all_trades)} | Wins: {wins} | Losses: {losses}\n")
        f.write(f"Cash P&L: £{final_cash_pnl:+.2f}\n")
    
    # 🧠 SAVE BRAIN-COMPATIBLE FORMAT
    with open('adaptive_learning_history.json', 'w') as f:
        json.dump({
            'trades': brain_trades,
            'thresholds': {
                'min_coherence': 0.45,
                'min_score': 65,
                'min_probability': 0.50,
                'harmonic_bonus': 1.15,
                'distortion_penalty': 0.70
            },
            'updated_at': datetime.now().isoformat(),
            'synced_from': 'multi_exchange_log',
            'exchanges': ['kraken', 'binance']
        }, f, indent=2)
    
    print(f"\n💾 Log saved to trade_log_output.txt")
    print(f"🧠 Brain data saved to adaptive_learning_history.json ({len(brain_trades)} completed trades)")
    
    if brain_trades:
        print(f"   └── Kraken trades: {len([t for t in brain_trades if t['exchange'] == 'kraken'])}")
        print(f"   └── Binance trades: {len([t for t in brain_trades if t['exchange'] == 'binance'])}")


if __name__ == "__main__":
    generate_trade_log()
