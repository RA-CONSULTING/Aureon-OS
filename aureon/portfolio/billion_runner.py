#!/usr/bin/env python3
"""
BILLION DOLLAR RUNNER
=====================
Autonomous trading system that:
1. ONLY sells when profitable (checks cost basis)
2. Compounds all gains
3. Tracks every position's cost basis
4. Runs 24/7 until we hit $1B

RULES:
- Never sell at a loss
- Always check cost basis before selling
- Compound all profits back into trades
- Track everything in JSON
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os

# Windows UTF-8 fix
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        if hasattr(sys.stdout, 'buffer') and sys.stdout.buffer:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if hasattr(sys.stderr, 'buffer') and sys.stderr.buffer:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except:
        pass

import json
import time
import requests
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, Optional, List
from aureon.exchanges.binance_client import BinanceClient, get_binance_client

# =============================================================================
# CONFIGURATION
# =============================================================================

COST_BASIS_FILE = "billion_cost_basis.json"
TRADE_LOG_FILE = "billion_trade_log.json"
TARGET = 1_000_000_000  # $1 Billion

MIN_TRADE_SIZE = 5.0      # Binance minimum
MAX_TRADE_SIZE = 100.0    # Max per trade
CASH_RESERVE = 5.0        # Always keep this much
MIN_PROFIT_TO_SELL = 0.50 # Minimum profit to trigger sell
MOMENTUM_THRESHOLD = 0.15 # % change to trigger buy

# Coins to trade (UK-allowed USDC pairs)
TRADE_COINS = ['SOL', 'ETH', 'XRP', 'DOGE', 'ADA', 'AVAX', 'LINK', 'SUI', 'APT', 'NEAR', 'ARB', 'OP']

# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Position:
    asset: str
    quantity: float
    cost_basis: float  # Total USD spent
    avg_price: float   # Average buy price
    
    @property
    def cost_per_unit(self):
        return self.cost_basis / self.quantity if self.quantity > 0 else 0

@dataclass 
class Trade:
    timestamp: str
    asset: str
    side: str  # BUY or SELL
    quantity: float
    price: float
    total: float
    profit: float  # 0 for buys, actual profit for sells
    order_id: str

# =============================================================================
# COST BASIS TRACKER
# =============================================================================

class CostBasisTracker:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.positions: Dict[str, Position] = {}
        self.load()
    
    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath) as f:
                    data = json.load(f)
                    for asset, pos in data.items():
                        self.positions[asset] = Position(**pos)
            except:
                pass
    
    def save(self):
        data = {asset: asdict(pos) for asset, pos in self.positions.items()}
        with open(self.filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def record_buy(self, asset: str, quantity: float, total_cost: float):
        """Record a buy and update cost basis"""
        if asset in self.positions:
            pos = self.positions[asset]
            new_qty = pos.quantity + quantity
            new_cost = pos.cost_basis + total_cost
            pos.quantity = new_qty
            pos.cost_basis = new_cost
            pos.avg_price = new_cost / new_qty
        else:
            self.positions[asset] = Position(
                asset=asset,
                quantity=quantity,
                cost_basis=total_cost,
                avg_price=total_cost / quantity
            )
        self.save()
    
    def record_sell(self, asset: str, quantity: float, total_received: float) -> float:
        """Record a sell and return profit"""
        if asset not in self.positions:
            return 0
        
        pos = self.positions[asset]
        cost_of_sold = (quantity / pos.quantity) * pos.cost_basis
        profit = total_received - cost_of_sold
        
        # Update position
        remaining_qty = pos.quantity - quantity
        if remaining_qty <= 0.00000001:
            del self.positions[asset]
        else:
            remaining_cost = pos.cost_basis - cost_of_sold
            pos.quantity = remaining_qty
            pos.cost_basis = remaining_cost
            pos.avg_price = remaining_cost / remaining_qty
        
        self.save()
        return profit
    
    def get_position(self, asset: str) -> Optional[Position]:
        return self.positions.get(asset)
    
    def is_profitable(self, asset: str, current_price: float) -> tuple:
        """Check if selling at current price would be profitable"""
        pos = self.get_position(asset)
        if not pos:
            return False, 0, 0
        
        current_value = pos.quantity * current_price
        profit = current_value - pos.cost_basis
        profit_pct = (profit / pos.cost_basis * 100) if pos.cost_basis > 0 else 0
        
        return profit > MIN_PROFIT_TO_SELL, profit, profit_pct

# =============================================================================
# TRADE LOGGER
# =============================================================================

class TradeLogger:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.trades: List[Trade] = []
        self.load()
    
    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath) as f:
                    data = json.load(f)
                    self.trades = [Trade(**t) for t in data]
            except:
                pass
    
    def save(self):
        with open(self.filepath, 'w') as f:
            json.dump([asdict(t) for t in self.trades], f, indent=2)
    
    def log(self, trade: Trade):
        self.trades.append(trade)
        self.save()
    
    def total_profit(self) -> float:
        return sum(t.profit for t in self.trades)

# =============================================================================
# MARKET SCANNER
# =============================================================================

def scan_momentum(coins: List[str]) -> Optional[dict]:
    """Scan for coins with positive momentum"""
    best = None
    best_score = -999
    
    for coin in coins:
        symbol = f"{coin}USDC"
        try:
            resp = requests.get(
                f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=6",
                timeout=5
            )
            klines = resp.json()
            
            if isinstance(klines, list) and len(klines) >= 3:
                prices = [float(k[4]) for k in klines]
                
                # Calculate momentum
                change_15m = (prices[-1] - prices[-3]) / prices[-3] * 100
                change_5m = (prices[-1] - prices[-2]) / prices[-2] * 100
                
                # Score: recent momentum + trend
                score = change_5m + (change_15m * 0.5)
                
                if score > best_score:
                    best_score = score
                    best = {
                        'coin': coin,
                        'symbol': symbol,
                        'price': prices[-1],
                        'change_5m': change_5m,
                        'change_15m': change_15m,
                        'score': score
                    }
        except Exception as e:
            pass
    
    return best if best and best_score > MOMENTUM_THRESHOLD else None

# =============================================================================
# MAIN TRADING LOOP
# =============================================================================

def run_billion_trader():
    print("=" * 60)
    print("🚀 BILLION DOLLAR RUNNER")
    print("=" * 60)
    print(f"Target: ${TARGET:,}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Initialize
    client = get_binance_client()
    tracker = CostBasisTracker(COST_BASIS_FILE)
    logger = TradeLogger(TRADE_LOG_FILE)
    
    # Get starting balance
    start_total = get_portfolio_value(client, tracker)
    print(f"Starting Portfolio: ${start_total:.2f}")
    print(f"Required Growth: {TARGET / start_total:.0f}x")
    print()
    
    round_num = 0
    
    while True:
        round_num += 1
        now = datetime.now().strftime('%H:%M:%S')
        
        try:
            # Get current cash
            usdc = client.get_free_balance('USDC')
            
            print(f"\n[{now}] Round {round_num} | Cash: ${usdc:.2f}")
            
            # STEP 1: Check if any position is profitable to sell
            for asset in list(tracker.positions.keys()):
                try:
                    qty = client.get_free_balance(asset)
                    if qty <= 0:
                        continue
                    
                    ticker = client.get_ticker(f"{asset}USDC")
                    if not ticker:
                        continue
                    
                    price = float(ticker['price'])
                    is_profit, profit, profit_pct = tracker.is_profitable(asset, price)
                    
                    value = qty * price
                    if is_profit and value >= MIN_TRADE_SIZE:
                        print(f"   ✅ {asset} profitable: ${profit:.2f} (+{profit_pct:.1f}%)")
                        
                        result = client.place_market_order(f"{asset}USDC", 'SELL', quantity=qty)
                        
                        if 'orderId' in result:
                            received = float(result.get('cummulativeQuoteQty', 0))
                            actual_profit = tracker.record_sell(asset, qty, received)
                            
                            logger.log(Trade(
                                timestamp=now,
                                asset=asset,
                                side='SELL',
                                quantity=qty,
                                price=price,
                                total=received,
                                profit=actual_profit,
                                order_id=str(result['orderId'])
                            ))
                            
                            print(f"   💰 SOLD {asset}: ${received:.2f} (Profit: ${actual_profit:.2f})")
                            usdc = client.get_free_balance('USDC')
                except Exception as e:
                    print(f"   Error checking {asset}: {e}")
            
            # STEP 2: If we have cash, look for buying opportunities
            available = usdc - CASH_RESERVE
            if available >= MIN_TRADE_SIZE:
                opp = scan_momentum(TRADE_COINS)
                
                if opp:
                    buy_amount = min(available, MAX_TRADE_SIZE)
                    print(f"   🎯 Opportunity: {opp['coin']} ({opp['score']:+.2f}%)")
                    
                    result = client.place_market_order(opp['symbol'], 'BUY', quote_qty=buy_amount)
                    
                    if 'orderId' in result:
                        filled = float(result.get('executedQty', 0))
                        spent = float(result.get('cummulativeQuoteQty', 0))
                        avg_price = spent / filled if filled > 0 else 0
                        
                        tracker.record_buy(opp['coin'], filled, spent)
                        
                        logger.log(Trade(
                            timestamp=now,
                            asset=opp['coin'],
                            side='BUY',
                            quantity=filled,
                            price=avg_price,
                            total=spent,
                            profit=0,
                            order_id=str(result['orderId'])
                        ))
                        
                        print(f"   📈 BOUGHT {filled:.6f} {opp['coin']} @ ${avg_price:.4f}")
                    elif result.get('rejected'):
                        print(f"   ❌ Rejected: {result.get('reason', 'Unknown')}")
                else:
                    print(f"   ⏸️  No momentum opportunity")
            else:
                print(f"   💤 Low cash, waiting for profits...")
            
            # STEP 3: Show progress
            if round_num % 10 == 0:
                total = get_portfolio_value(client, tracker)
                profit = logger.total_profit()
                progress = total / TARGET * 100
                print(f"\n   📊 Portfolio: ${total:.2f} | Total Profit: ${profit:.2f} | Progress: {progress:.6f}%")
            
            # Check if we hit target
            total = get_portfolio_value(client, tracker)
            if total >= TARGET:
                print("\n" + "=" * 60)
                print("🎉🎉🎉 BILLION DOLLAR TARGET REACHED! 🎉🎉🎉")
                print("=" * 60)
                break
            
            time.sleep(5)  # Wait 5 seconds between rounds
            
        except KeyboardInterrupt:
            print("\n\nStopping trader...")
            break
        except Exception as e:
            print(f"   ❌ Error: {e}")
            time.sleep(10)

def get_portfolio_value(client: BinanceClient, tracker: CostBasisTracker) -> float:
    """Calculate total portfolio value"""
    total = 0
    
    # Cash
    for asset in ['USDC', 'USD', 'LDUSDC']:
        total += client.get_free_balance(asset)
    
    # Positions
    for asset in tracker.positions.keys():
        qty = client.get_free_balance(asset)
        if qty > 0:
            try:
                ticker = client.get_ticker(f"{asset}USDC")
                if ticker:
                    total += qty * float(ticker['price'])
            except:
                pass
    
    # Other assets not in tracker
    acct = client.account()
    for bal in acct.get('balances', []):
        asset = bal['asset']
        free = float(bal.get('free', 0))
        if free > 0 and asset not in ['USDC', 'USD', 'LDUSDC'] and asset not in tracker.positions:
            try:
                ticker = client.get_ticker(f"{asset}USDC")
                if ticker:
                    total += free * float(ticker['price'])
            except:
                pass
    
    return total

# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    run_billion_trader()
