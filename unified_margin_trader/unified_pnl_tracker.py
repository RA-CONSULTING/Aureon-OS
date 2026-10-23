#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 UNIFIED P&L TRACKER - ONE SOURCE OF TRUTH
============================================
Pulls ALL data from Binance API directly.
No cached files. No confusion. Just facts.

Usage:
    python unified_pnl_tracker.py           # Full P&L report
    python unified_pnl_tracker.py --summary # Quick summary only
    python unified_pnl_tracker.py --save    # Save to JSON for dashboard
"""

import os
import sys
import json
import hmac
import hashlib
import time
import requests
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv

load_dotenv('/workspaces/aureon-trading/.env', override=True)

# ============================================================================
# CONFIG
# ============================================================================
LOOKBACK_DAYS = 90  # How far back to pull trades
STATE_FILE = '/workspaces/aureon-trading/unified_pnl_state.json'

# ============================================================================
# DATA STRUCTURES
# ============================================================================
@dataclass
class Trade:
    """Single trade from Binance"""
    timestamp: datetime
    symbol: str
    asset: str
    quote: str
    side: str  # BUY or SELL
    qty: float
    price: float
    usd_value: float
    commission: float
    trade_id: int

@dataclass 
class Position:
    """Current position with P&L"""
    asset: str
    qty_held: float
    qty_bought: float
    qty_sold: float
    total_cost: float      # Total USD spent buying
    total_revenue: float   # Total USD received selling
    avg_buy_price: float
    avg_sell_price: float
    current_price: float
    current_value: float
    cost_basis: float      # Cost of what we still hold
    unrealized_pnl: float
    unrealized_pnl_pct: float
    realized_pnl: float    # Profit/loss from sells
    total_pnl: float
    trade_count: int
    first_trade: datetime
    last_trade: datetime

@dataclass
class PortfolioSummary:
    """Overall portfolio summary"""
    timestamp: datetime
    total_invested: float
    total_current_value: float
    total_unrealized_pnl: float
    total_realized_pnl: float
    total_pnl: float
    total_pnl_pct: float
    winning_positions: int
    losing_positions: int
    breakeven_positions: int
    positions: List[Position]

# ============================================================================
# BINANCE API
# ============================================================================
class BinanceAPI:
    """Direct Binance API access - no wrappers, no confusion"""
    
    def __init__(self):
        self.api_key = os.environ.get('BINANCE_API_KEY')
        self.api_secret = os.environ.get('BINANCE_API_SECRET')
        self.base_url = 'https://api.binance.com'
        
        if not self.api_key or not self.api_secret:
            raise ValueError("Missing BINANCE_API_KEY or BINANCE_API_SECRET")
    
    def _signed_request(self, endpoint: str, params: dict = None) -> dict:
        """Make signed API request"""
        if params is None:
            params = {}
        params['timestamp'] = int(time.time() * 1000)
        
        query = '&'.join(f"{k}={v}" for k, v in params.items())
        signature = hmac.new(
            self.api_secret.encode(), 
            query.encode(), 
            hashlib.sha256
        ).hexdigest()
        query += f"&signature={signature}"
        
        headers = {'X-MBX-APIKEY': self.api_key}
        resp = requests.get(f"{self.base_url}{endpoint}?{query}", headers=headers)
        return resp.json()
    
    def _public_request(self, endpoint: str) -> dict:
        """Make public API request"""
        resp = requests.get(f"{self.base_url}{endpoint}")
        return resp.json()
    
    def get_balances(self) -> Dict[str, float]:
        """Get all non-zero balances"""
        account = self._signed_request('/api/v3/account')
        balances = {}
        for b in account.get('balances', []):
            total = float(b.get('free', 0)) + float(b.get('locked', 0))
            if total > 0.00000001:
                balances[b['asset']] = total
        return balances
    
    def get_all_prices(self) -> Dict[str, float]:
        """Get all current prices"""
        prices_data = self._public_request('/api/v3/ticker/price')
        return {p['symbol']: float(p['price']) for p in prices_data}
    
    def get_trades(self, symbol: str, start_time: int) -> List[dict]:
        """Get all trades for a symbol since start_time"""
        try:
            trades = self._signed_request('/api/v3/myTrades', {
                'symbol': symbol,
                'startTime': start_time,
                'limit': 1000
            })
            if isinstance(trades, list):
                return trades
        except Exception as e:
            pass
        return []

# ============================================================================
# P&L CALCULATOR
# ============================================================================
class UnifiedPnLTracker:
    """THE ONE TRUE P&L TRACKER"""
    
    def __init__(self):
        self.api = BinanceAPI()
        self.prices = {}
        self.btc_price = 0
        self.eur_rate = 1.08  # EUR/USD approximate
        
    def _get_usd_value(self, qty: float, price: float, quote: str) -> float:
        """Convert any quote currency to USD"""
        if quote in ('USDT', 'USDC', 'USD', 'BUSD', 'FDUSD'):
            return qty * price
        elif quote == 'BTC':
            return qty * price * self.btc_price
        elif quote == 'EUR':
            return qty * price * self.eur_rate
        else:
            return qty * price  # Assume USD-like
    
    def _get_current_price_usd(self, asset: str) -> float:
        """Get current USD price for an asset"""
        if asset in ('USDT', 'USDC', 'USD', 'BUSD', 'FDUSD'):
            return 1.0
        
        for quote in ['USDT', 'USDC', 'BUSD', 'FDUSD']:
            symbol = f"{asset}{quote}"
            if symbol in self.prices:
                return self.prices[symbol]
        
        # Try BTC pair
        btc_symbol = f"{asset}BTC"
        if btc_symbol in self.prices:
            return self.prices[btc_symbol] * self.btc_price
        
        return 0.0
    
    def fetch_all_trades(self, lookback_days: int = LOOKBACK_DAYS) -> Dict[str, List[Trade]]:
        """Fetch ALL trades for ALL assets we hold"""
        print("📡 Fetching data from Binance API...")
        
        # Get current state
        self.prices = self.api.get_all_prices()
        self.btc_price = self.prices.get('BTCUSDT', 100000)
        balances = self.api.get_balances()
        
        print(f"   Found {len(balances)} assets with balance")
        
        # Start time for trade lookup
        start_time = int((datetime.now() - timedelta(days=lookback_days)).timestamp() * 1000)
        
        # Assets to check (skip stablecoins)
        skip_assets = {'USDT', 'USDC', 'USD', 'BUSD', 'FDUSD', 'BNB'}
        assets_to_check = [a for a in balances.keys() if a not in skip_assets]
        
        # Quote currencies to try
        quotes = ['USDT', 'USDC', 'BTC', 'EUR', 'BUSD']
        
        all_trades: Dict[str, List[Trade]] = {}
        
        for asset in assets_to_check:
            trades_for_asset = []
            
            for quote in quotes:
                symbol = f"{asset}{quote}"
                raw_trades = self.api.get_trades(symbol, start_time)
                
                for t in raw_trades:
                    qty = float(t.get('qty', 0))
                    price = float(t.get('price', 0))
                    usd_value = self._get_usd_value(qty, price, quote)
                    
                    trade = Trade(
                        timestamp=datetime.fromtimestamp(t['time'] / 1000),
                        symbol=symbol,
                        asset=asset,
                        quote=quote,
                        side='BUY' if t['isBuyer'] else 'SELL',
                        qty=qty,
                        price=price,
                        usd_value=usd_value,
                        commission=float(t.get('commission', 0)),
                        trade_id=t['id']
                    )
                    trades_for_asset.append(trade)
            
            if trades_for_asset:
                # Sort by time
                trades_for_asset.sort(key=lambda x: x.timestamp)
                all_trades[asset] = trades_for_asset
                print(f"   {asset}: {len(trades_for_asset)} trades")
        
        return all_trades, balances
    
    def calculate_position(self, asset: str, trades: List[Trade], qty_held: float) -> Position:
        """Calculate P&L for a single position using AVERAGE COST method"""
        
        total_bought_qty = 0.0
        total_bought_cost = 0.0
        total_sold_qty = 0.0
        total_sold_revenue = 0.0
        
        for trade in trades:
            if trade.side == 'BUY':
                total_bought_qty += trade.qty
                total_bought_cost += trade.usd_value
            else:
                total_sold_qty += trade.qty
                total_sold_revenue += trade.usd_value
        
        # Average prices
        avg_buy_price = total_bought_cost / total_bought_qty if total_bought_qty > 0 else 0
        avg_sell_price = total_sold_revenue / total_sold_qty if total_sold_qty > 0 else 0
        
        # Current value
        current_price = self._get_current_price_usd(asset)
        current_value = qty_held * current_price
        
        # Cost basis of what we still hold (using average cost)
        cost_basis = avg_buy_price * qty_held
        
        # Unrealized P&L (paper gain/loss on current holdings)
        unrealized_pnl = current_value - cost_basis
        unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0
        
        # Realized P&L (profit/loss from sells)
        # Cost of sold units = avg_buy_price * qty_sold
        cost_of_sold = avg_buy_price * total_sold_qty
        realized_pnl = total_sold_revenue - cost_of_sold
        
        # Total P&L
        total_pnl = unrealized_pnl + realized_pnl
        
        return Position(
            asset=asset,
            qty_held=qty_held,
            qty_bought=total_bought_qty,
            qty_sold=total_sold_qty,
            total_cost=total_bought_cost,
            total_revenue=total_sold_revenue,
            avg_buy_price=avg_buy_price,
            avg_sell_price=avg_sell_price,
            current_price=current_price,
            current_value=current_value,
            cost_basis=cost_basis,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_pct=unrealized_pnl_pct,
            realized_pnl=realized_pnl,
            total_pnl=total_pnl,
            trade_count=len(trades),
            first_trade=trades[0].timestamp if trades else datetime.now(),
            last_trade=trades[-1].timestamp if trades else datetime.now()
        )
    
    def generate_report(self, lookback_days: int = LOOKBACK_DAYS) -> PortfolioSummary:
        """Generate full P&L report"""
        
        all_trades, balances = self.fetch_all_trades(lookback_days)
        
        positions = []
        
        for asset, trades in all_trades.items():
            qty_held = balances.get(asset, 0)
            if qty_held < 0.00000001 and not trades:
                continue
                
            pos = self.calculate_position(asset, trades, qty_held)
            
            # Only include positions with meaningful value
            if pos.current_value > 0.50 or pos.total_cost > 0.50:
                positions.append(pos)
        
        # Calculate totals
        total_invested = sum(p.cost_basis for p in positions)
        total_current_value = sum(p.current_value for p in positions)
        total_unrealized = sum(p.unrealized_pnl for p in positions)
        total_realized = sum(p.realized_pnl for p in positions)
        total_pnl = total_unrealized + total_realized
        total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
        
        winning = sum(1 for p in positions if p.total_pnl > 0.01)
        losing = sum(1 for p in positions if p.total_pnl < -0.01)
        breakeven = len(positions) - winning - losing
        
        return PortfolioSummary(
            timestamp=datetime.now(),
            total_invested=total_invested,
            total_current_value=total_current_value,
            total_unrealized_pnl=total_unrealized,
            total_realized_pnl=total_realized,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            winning_positions=winning,
            losing_positions=losing,
            breakeven_positions=breakeven,
            positions=positions
        )

# ============================================================================
# DISPLAY
# ============================================================================
def print_report(summary: PortfolioSummary, detailed: bool = True):
    """Print formatted P&L report"""
    
    print("\n" + "=" * 90)
    print("🎯 UNIFIED P&L REPORT - ONE SOURCE OF TRUTH")
    print("=" * 90)
    print(f"📅 Generated: {summary.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 90)
    
    if detailed:
        # Sort positions by total P&L
        sorted_positions = sorted(summary.positions, key=lambda x: x.total_pnl)
        
        print(f"\n{'Asset':<8} {'Held':>10} {'Cost Basis':>12} {'Current':>12} {'Unreal P&L':>12} {'Real P&L':>10} {'Total':>10}")
        print("-" * 90)
        
        for p in sorted_positions:
            status = "🟢" if p.total_pnl >= 0 else "🔴"
            print(f"{p.asset:<8} {p.qty_held:>10.4f} ${p.cost_basis:>10.2f} ${p.current_value:>10.2f} ${p.unrealized_pnl:>+10.2f} ${p.realized_pnl:>+8.2f} ${p.total_pnl:>+8.2f} {status}")
    
    # Summary
    print("\n" + "=" * 90)
    print("📋 PORTFOLIO SUMMARY")
    print("=" * 90)
    
    status_emoji = "🟢" if summary.total_pnl >= 0 else "🔴"
    
    print(f"""
💰 COST BASIS (What you paid):     ${summary.total_invested:>10.2f}
💼 CURRENT VALUE:                  ${summary.total_current_value:>10.2f}

📈 UNREALIZED P&L (Paper):         ${summary.total_unrealized_pnl:>+10.2f}
💵 REALIZED P&L (From sells):      ${summary.total_realized_pnl:>+10.2f}

{status_emoji} TOTAL P&L:                       ${summary.total_pnl:>+10.2f}  ({summary.total_pnl_pct:+.1f}%)

📊 Positions: {len(summary.positions)} total
   🟢 Winning:   {summary.winning_positions}
   🔴 Losing:    {summary.losing_positions}
   ⚪ Breakeven: {summary.breakeven_positions}
""")
    print("=" * 90)

def save_state(summary: PortfolioSummary):
    """Save state to JSON for dashboard"""
    data = {
        'timestamp': summary.timestamp.isoformat(),
        'total_invested': summary.total_invested,
        'total_current_value': summary.total_current_value,
        'total_unrealized_pnl': summary.total_unrealized_pnl,
        'total_realized_pnl': summary.total_realized_pnl,
        'total_pnl': summary.total_pnl,
        'total_pnl_pct': summary.total_pnl_pct,
        'winning_positions': summary.winning_positions,
        'losing_positions': summary.losing_positions,
        'positions': []
    }
    
    for p in summary.positions:
        data['positions'].append({
            'asset': p.asset,
            'qty_held': p.qty_held,
            'cost_basis': p.cost_basis,
            'current_value': p.current_value,
            'current_price': p.current_price,
            'unrealized_pnl': p.unrealized_pnl,
            'unrealized_pnl_pct': p.unrealized_pnl_pct,
            'realized_pnl': p.realized_pnl,
            'total_pnl': p.total_pnl,
            'trade_count': p.trade_count
        })
    
    with open(STATE_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"💾 State saved to {STATE_FILE}")

# ============================================================================
# MAIN
# ============================================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='Unified P&L Tracker')
    parser.add_argument('--summary', action='store_true', help='Show summary only')
    parser.add_argument('--save', action='store_true', help='Save state to JSON')
    parser.add_argument('--days', type=int, default=90, help='Lookback days')
    args = parser.parse_args()
    
    tracker = UnifiedPnLTracker()
    summary = tracker.generate_report(args.days)
    
    print_report(summary, detailed=not args.summary)
    
    if args.save:
        save_state(summary)
    
    return summary

if __name__ == '__main__':
    main()
