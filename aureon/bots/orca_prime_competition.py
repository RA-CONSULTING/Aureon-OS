#!/usr/bin/env python3
"""
🦈🏆 ORCA PRIME COMPETITION - PARALLEL ORCAS RACING FOR PROFIT 🏆🦈
═══════════════════════════════════════════════════════════════════════════════

CONCEPT: Multiple parallel "Orcas" (trading strategies) compete against each 
other like quantum superposition - all trying to be THE PRIME that catches profit.

COMPETITION LAYERS:
  Layer 1: MOMENTUM ORCA    - Rides price waves, first to catch momentum
  Layer 2: REVERSAL ORCA    - Catches oversold bounces, contrarian plays  
  Layer 3: VOLUME ORCA      - Follows volume spikes, whale activity
  Layer 4: SPREAD ORCA      - Arbitrage opportunities, bid/ask exploits
  Layer 5: PRIME ORCA       - Meta-layer that picks winners from all layers

RULES:
  1. ALL Orcas monitor the SAME positions
  2. FIRST Orca to detect profit opportunity WINS and executes
  3. NO selling at a loss - validated cost basis always
  4. Winner gets credit, losers learn from winner's strategy
  5. Competition drives evolution - best strategies survive

Gary Leckey | January 2026 | The Orcas Hunt Together
═══════════════════════════════════════════════════════════════════════════════
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os
import time
import json
import threading
import requests
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue, Empty

# Windows UTF-8 fix
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

from aureon.exchanges.binance_client import BinanceClient, get_binance_client

# =============================================================================
# CONFIGURATION
# =============================================================================

COST_BASIS_FILE = "orca_prime_costs.json"
COMPETITION_LOG = "orca_competition_log.json"
MIN_PROFIT_TO_SELL = 0.25  # Minimum profit to trigger sell
MIN_TRADE_SIZE = 5.0       # Binance minimum
CASH_RESERVE = 3.0         # Always keep this much

# Trading universe
TRADE_COINS = ['SOL', 'ETH', 'XRP', 'DOGE', 'ADA', 'AVAX', 'LINK', 'SUI', 'APT', 'NEAR', 
               'ARB', 'OP', 'PEPE', 'SHIB', 'WIF', 'BONK', 'FET', 'RENDER', 'INJ', 'TIA']

# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Position:
    asset: str
    quantity: float
    cost_basis: float
    avg_price: float
    entry_time: str

@dataclass
class OrcaDecision:
    orca_name: str
    action: str  # BUY, SELL, HOLD
    asset: str
    confidence: float
    reason: str
    timestamp: str

@dataclass
class CompetitionResult:
    winner: str
    action: str
    asset: str
    profit: float
    timestamp: str

# =============================================================================
# COST BASIS TRACKER (VALIDATED - NO PHANTOM GAINS)
# =============================================================================

class CostTracker:
    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.load()
    
    def load(self):
        if os.path.exists(COST_BASIS_FILE):
            try:
                with open(COST_BASIS_FILE) as f:
                    data = json.load(f)
                    for asset, pos in data.items():
                        self.positions[asset] = Position(**pos)
            except:
                pass
    
    def save(self):
        data = {asset: asdict(pos) for asset, pos in self.positions.items()}
        with open(COST_BASIS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    
    def record_buy(self, asset: str, qty: float, cost: float):
        now = datetime.now().isoformat()
        if asset in self.positions:
            pos = self.positions[asset]
            new_qty = pos.quantity + qty
            new_cost = pos.cost_basis + cost
            pos.quantity = new_qty
            pos.cost_basis = new_cost
            pos.avg_price = new_cost / new_qty
        else:
            self.positions[asset] = Position(
                asset=asset,
                quantity=qty,
                cost_basis=cost,
                avg_price=cost/qty,
                entry_time=now
            )
        self.save()
    
    def record_sell(self, asset: str, qty: float, received: float) -> float:
        if asset not in self.positions:
            return 0
        pos = self.positions[asset]
        cost_of_sold = (qty / pos.quantity) * pos.cost_basis if pos.quantity > 0 else 0
        profit = received - cost_of_sold
        
        remaining = pos.quantity - qty
        if remaining <= 0.00000001:
            del self.positions[asset]
        else:
            pos.quantity = remaining
            pos.cost_basis -= cost_of_sold
        self.save()
        return profit
    
    def is_profitable(self, asset: str, current_price: float) -> Tuple[bool, float, float]:
        if asset not in self.positions:
            return False, 0, 0
        pos = self.positions[asset]
        value = pos.quantity * current_price
        profit = value - pos.cost_basis
        pct = (profit / pos.cost_basis * 100) if pos.cost_basis > 0 else 0
        return profit > MIN_PROFIT_TO_SELL, profit, pct

# =============================================================================
# ORCA STRATEGIES - Each competes to find profit first
# =============================================================================

class BaseOrca:
    """Base class for all Orca strategies"""
    name = "BASE"
    
    def __init__(self, client: BinanceClient):
        self.client = client
        self.wins = 0
        self.decisions = 0
    
    def analyze(self, asset: str, current_price: float, cost_basis: float, 
                market_data: dict) -> OrcaDecision:
        """Analyze and decide - must be implemented by each Orca"""
        raise NotImplementedError
    
    def get_market_data(self, symbol: str) -> dict:
        """Get market data for analysis"""
        try:
            resp = requests.get(
                f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=12",
                timeout=5
            )
            klines = resp.json()
            if isinstance(klines, list) and len(klines) >= 3:
                prices = [float(k[4]) for k in klines]
                volumes = [float(k[5]) for k in klines]
                return {
                    'prices': prices,
                    'volumes': volumes,
                    'change_5m': (prices[-1] - prices[-2]) / prices[-2] * 100 if prices[-2] > 0 else 0,
                    'change_1h': (prices[-1] - prices[0]) / prices[0] * 100 if prices[0] > 0 else 0,
                    'vol_spike': volumes[-1] / (sum(volumes[:-1]) / len(volumes[:-1])) if sum(volumes[:-1]) > 0 else 1
                }
        except:
            pass
        return {'prices': [], 'volumes': [], 'change_5m': 0, 'change_1h': 0, 'vol_spike': 1}


class MomentumOrca(BaseOrca):
    """Rides momentum waves - catches fast runners"""
    name = "MOMENTUM"
    
    def analyze(self, asset: str, current_price: float, cost_basis: float, 
                market_data: dict) -> OrcaDecision:
        now = datetime.now().strftime('%H:%M:%S')
        self.decisions += 1
        
        profit_pct = ((current_price * 100) / cost_basis - 100) if cost_basis > 0 else 0
        change_5m = market_data.get('change_5m', 0)
        
        # SELL if profitable AND momentum turning down
        if profit_pct > 0.5 and change_5m < -0.1:
            return OrcaDecision(self.name, 'SELL', asset, 0.8, 
                              f"Profit {profit_pct:.1f}% + momentum fading", now)
        
        # BUY if strong upward momentum
        if change_5m > 0.3:
            return OrcaDecision(self.name, 'BUY', asset, change_5m / 2, 
                              f"Strong momentum +{change_5m:.2f}%", now)
        
        return OrcaDecision(self.name, 'HOLD', asset, 0.3, "Waiting for momentum", now)


class ReversalOrca(BaseOrca):
    """Catches oversold bounces - contrarian plays"""
    name = "REVERSAL"
    
    def analyze(self, asset: str, current_price: float, cost_basis: float,
                market_data: dict) -> OrcaDecision:
        now = datetime.now().strftime('%H:%M:%S')
        self.decisions += 1
        
        profit_pct = ((current_price * 100) / cost_basis - 100) if cost_basis > 0 else 0
        change_1h = market_data.get('change_1h', 0)
        change_5m = market_data.get('change_5m', 0)
        
        # SELL if profitable AND overbought (big 1h gain)
        if profit_pct > 0.5 and change_1h > 2:
            return OrcaDecision(self.name, 'SELL', asset, 0.85,
                              f"Take profit - overbought +{change_1h:.1f}% 1h", now)
        
        # BUY if oversold (big 1h drop) but bouncing (5m up)
        if change_1h < -2 and change_5m > 0.1:
            return OrcaDecision(self.name, 'BUY', asset, 0.7,
                              f"Oversold bounce: 1h={change_1h:.1f}%, 5m=+{change_5m:.2f}%", now)
        
        return OrcaDecision(self.name, 'HOLD', asset, 0.2, "No reversal setup", now)


class VolumeOrca(BaseOrca):
    """Follows volume spikes - whale activity detector"""
    name = "VOLUME"
    
    def analyze(self, asset: str, current_price: float, cost_basis: float,
                market_data: dict) -> OrcaDecision:
        now = datetime.now().strftime('%H:%M:%S')
        self.decisions += 1
        
        profit_pct = ((current_price * 100) / cost_basis - 100) if cost_basis > 0 else 0
        vol_spike = market_data.get('vol_spike', 1)
        change_5m = market_data.get('change_5m', 0)
        
        # SELL if profitable AND volume dying
        if profit_pct > 0.5 and vol_spike < 0.5:
            return OrcaDecision(self.name, 'SELL', asset, 0.75,
                              f"Profit {profit_pct:.1f}% + volume dying", now)
        
        # BUY if huge volume spike with price up
        if vol_spike > 2 and change_5m > 0.2:
            return OrcaDecision(self.name, 'BUY', asset, min(vol_spike / 3, 0.9),
                              f"Volume spike {vol_spike:.1f}x + price up", now)
        
        return OrcaDecision(self.name, 'HOLD', asset, 0.2, "Normal volume", now)


class SpreadOrca(BaseOrca):
    """Looks for spread/arbitrage opportunities"""
    name = "SPREAD"
    
    def analyze(self, asset: str, current_price: float, cost_basis: float,
                market_data: dict) -> OrcaDecision:
        now = datetime.now().strftime('%H:%M:%S')
        self.decisions += 1
        
        profit_pct = ((current_price * 100) / cost_basis - 100) if cost_basis > 0 else 0
        
        # Simple: sell if profit > 0.5% (covers spread + fees)
        if profit_pct > 0.5:
            return OrcaDecision(self.name, 'SELL', asset, 0.9,
                              f"Spread covered + profit {profit_pct:.2f}%", now)
        
        return OrcaDecision(self.name, 'HOLD', asset, 0.1, "Spread not covered", now)


class PrimeOrca(BaseOrca):
    """Meta-layer: picks the best decision from all Orcas"""
    name = "PRIME"
    
    def __init__(self, client: BinanceClient, orcas: List[BaseOrca]):
        super().__init__(client)
        self.orcas = orcas
    
    def analyze(self, asset: str, current_price: float, cost_basis: float,
                market_data: dict) -> OrcaDecision:
        now = datetime.now().strftime('%H:%M:%S')
        self.decisions += 1
        
        # Gather all decisions
        decisions = []
        for orca in self.orcas:
            try:
                dec = orca.analyze(asset, current_price, cost_basis, market_data)
                decisions.append(dec)
            except:
                pass
        
        # Count votes
        sell_votes = [d for d in decisions if d.action == 'SELL']
        buy_votes = [d for d in decisions if d.action == 'BUY']
        
        # If majority says SELL with confidence, SELL
        if len(sell_votes) >= 2:
            best_sell = max(sell_votes, key=lambda x: x.confidence)
            return OrcaDecision(self.name, 'SELL', asset, best_sell.confidence,
                              f"PRIME: {len(sell_votes)} Orcas agree SELL ({best_sell.orca_name} leads)", now)
        
        # If majority says BUY with confidence, BUY
        if len(buy_votes) >= 2:
            best_buy = max(buy_votes, key=lambda x: x.confidence)
            return OrcaDecision(self.name, 'BUY', asset, best_buy.confidence,
                              f"PRIME: {len(buy_votes)} Orcas agree BUY ({best_buy.orca_name} leads)", now)
        
        # Single strong signal
        all_actions = sell_votes + buy_votes
        if all_actions:
            best = max(all_actions, key=lambda x: x.confidence)
            if best.confidence > 0.7:
                return OrcaDecision(self.name, best.action, asset, best.confidence * 0.8,
                                  f"PRIME: Strong signal from {best.orca_name}", now)
        
        return OrcaDecision(self.name, 'HOLD', asset, 0.3, "PRIME: No consensus", now)


# =============================================================================
# COMPETITION ARENA
# =============================================================================

class OrcaCompetition:
    """
    The Arena where Orcas compete - first to catch profit wins!
    """
    
    def __init__(self):
        self.client = get_binance_client()
        self.cost_tracker = CostTracker()
        self.competition_log: List[CompetitionResult] = []
        
        # Initialize Orcas
        self.momentum = MomentumOrca(self.client)
        self.reversal = ReversalOrca(self.client)
        self.volume = VolumeOrca(self.client)
        self.spread = SpreadOrca(self.client)
        
        # Prime Orca orchestrates all
        self.orcas = [self.momentum, self.reversal, self.volume, self.spread]
        self.prime = PrimeOrca(self.client, self.orcas)
        
        self.total_profit = 0
        self.races_won = {orca.name: 0 for orca in self.orcas}
        self.races_won['PRIME'] = 0
    
    def get_positions_with_costs(self) -> List[Dict]:
        """Get all positions with their cost basis"""
        positions = []
        acct = self.client.account()
        
        for bal in acct.get('balances', []):
            asset = bal['asset']
            qty = float(bal.get('free', 0))
            
            if qty > 0 and asset not in ['USDC', 'USD', 'LDUSDC', 'USDT']:
                try:
                    ticker = self.client.get_ticker(f'{asset}USDC')
                    if ticker:
                        price = float(ticker['price'])
                        value = qty * price
                        
                        if value > 1:  # Only track > $1
                            if asset in self.cost_tracker.positions:
                                cost = self.cost_tracker.positions[asset].cost_basis
                                profit = value - cost
                                profit_pct = ((value - cost) / cost * 100) if cost > 0 else 0
                                cost_known = True
                            else:
                                cost = None
                                profit = None
                                profit_pct = None
                                cost_known = False
                            
                            positions.append({
                                'asset': asset,
                                'qty': qty,
                                'price': price,
                                'value': value,
                                'cost': cost,
                                'profit': profit,
                                'profit_pct': profit_pct,
                                'cost_known': cost_known
                            })
                except:
                    pass
        
        return positions
    
    def run_race(self, position: Dict) -> Optional[CompetitionResult]:
        """Run a race on a single position - all Orcas compete"""
        if not position.get('cost_known'):
            print(f"   ⚠️ {position['asset']}: cost basis unknown - no sell/decision")
            return None
        asset = position['asset']
        price = position['price']
        cost = position['cost']
        symbol = f"{asset}USDC"
        
        # Get market data
        market_data = self.momentum.get_market_data(symbol)
        
        # VALIDATION: Check if actually profitable before any sell
        is_profitable, profit, profit_pct = self.cost_tracker.is_profitable(asset, price)
        
        # Let all Orcas analyze
        decisions = []
        for orca in self.orcas:
            try:
                dec = orca.analyze(asset, price, cost, market_data)
                decisions.append(dec)
            except:
                pass
        
        # Prime makes final call
        prime_decision = self.prime.analyze(asset, price, cost, market_data)
        
        # Execute if SELL and validated profitable
        if prime_decision.action == 'SELL':
            if not is_profitable:
                print(f"   ⚠️ {asset}: SELL blocked - NOT profitable (P&L: ${profit:.2f})")
                return None
            
            # Find which Orca had the winning insight
            sell_decisions = [d for d in decisions if d.action == 'SELL']
            winner = max(sell_decisions, key=lambda x: x.confidence) if sell_decisions else prime_decision
            
            # Execute the sell
            qty = position['qty']
            result = self.client.place_market_order(symbol, 'SELL', quantity=qty)
            
            if 'orderId' in result:
                received = float(result.get('cummulativeQuoteQty', 0))
                actual_profit = self.cost_tracker.record_sell(asset, qty, received)
                self.total_profit += actual_profit
                self.races_won[winner.orca_name] += 1
                
                now = datetime.now().strftime('%H:%M:%S')
                comp_result = CompetitionResult(
                    winner=winner.orca_name,
                    action='SELL',
                    asset=asset,
                    profit=actual_profit,
                    timestamp=now
                )
                self.competition_log.append(comp_result)
                
                print(f"   🏆 {winner.orca_name} WINS! Sold {asset} for ${received:.2f} (Profit: ${actual_profit:.2f})")
                return comp_result
        
        return None
    
    def scan_for_buys(self) -> Optional[CompetitionResult]:
        """Scan for buy opportunities - Orcas compete to find best entry"""
        usdc = self.client.get_free_balance('USDC')
        available = usdc - CASH_RESERVE
        
        if available < MIN_TRADE_SIZE:
            return None
        
        best_buy = None
        best_confidence = 0
        best_orca = None
        
        held_assets = {pos['asset'] for pos in self.get_positions_with_costs()}

        for coin in TRADE_COINS[:10]:  # Scan first 10
            if coin in held_assets:
                continue
            symbol = f"{coin}USDC"
            try:
                ticker = self.client.get_ticker(symbol)
                if not ticker:
                    continue
                
                price = float(ticker['price'])
                market_data = self.momentum.get_market_data(symbol)
                
                # All Orcas analyze
                for orca in self.orcas:
                    dec = orca.analyze(coin, price, price, market_data)
                    if dec.action == 'BUY' and dec.confidence > best_confidence:
                        best_confidence = dec.confidence
                        best_buy = {'coin': coin, 'symbol': symbol, 'price': price}
                        best_orca = orca
            except:
                pass
        
        if best_buy and best_confidence > 0.5:
            # Execute buy
            buy_amount = min(available, 25)  # Max $25 per buy
            result = self.client.place_market_order(best_buy['symbol'], 'BUY', quote_qty=buy_amount)
            
            if 'orderId' in result:
                filled = float(result.get('executedQty', 0))
                spent = float(result.get('cummulativeQuoteQty', 0))
                
                self.cost_tracker.record_buy(best_buy['coin'], filled, spent)
                self.races_won[best_orca.name] += 1
                
                now = datetime.now().strftime('%H:%M:%S')
                print(f"   🎯 {best_orca.name} found entry: Bought {filled:.6f} {best_buy['coin']} @ ${best_buy['price']:.4f}")
                
                return CompetitionResult(
                    winner=best_orca.name,
                    action='BUY',
                    asset=best_buy['coin'],
                    profit=0,
                    timestamp=now
                )
        
        return None
    
    def run_competition(self, rounds: int = 50):
        """Run the full competition"""
        print("=" * 70)
        print("🦈🏆 ORCA PRIME COMPETITION - PARALLEL ORCAS RACING FOR PROFIT 🏆🦈")
        print("=" * 70)
        print(f"Orcas competing: {', '.join([o.name for o in self.orcas])} + PRIME")
        print(f"Target: First to catch profit wins!")
        print()
        
        for round_num in range(1, rounds + 1):
            now = datetime.now().strftime('%H:%M:%S')
            print(f"\n[{now}] ══════ RACE {round_num} ══════")
            
            # Get all positions
            positions = self.get_positions_with_costs()
            
            # Run race on each position
            for pos in positions:
                if pos['value'] > MIN_TRADE_SIZE:
                    if pos.get('cost_known'):
                        status = '✅' if pos['profit'] > MIN_PROFIT_TO_SELL else '⏳'
                        print(f"   {status} {pos['asset']}: ${pos['value']:.2f} (P&L: ${pos['profit']:.2f})")
                    else:
                        print(f"   ⚠️ {pos['asset']}: ${pos['value']:.2f} (P&L: unknown cost basis)")
                    self.run_race(pos)
            
            # Scan for new buys
            self.scan_for_buys()
            
            # Show scoreboard every 5 rounds
            if round_num % 5 == 0:
                print(f"\n   📊 SCOREBOARD:")
                for name, wins in sorted(self.races_won.items(), key=lambda x: -x[1]):
                    if wins > 0:
                        print(f"      {name}: {wins} wins")
                print(f"      Total Profit: ${self.total_profit:.2f}")
            
            time.sleep(5)
        
        # Final results
        print("\n" + "=" * 70)
        print("🏆 FINAL RESULTS 🏆")
        print("=" * 70)
        for name, wins in sorted(self.races_won.items(), key=lambda x: -x[1]):
            print(f"   {name}: {wins} wins")
        print(f"\n💰 TOTAL PROFIT: ${self.total_profit:.2f}")
        
        # Show current portfolio
        print("\n📊 FINAL PORTFOLIO:")
        total = self.client.get_free_balance('USDC')
        for pos in self.get_positions_with_costs():
            print(f"   {pos['asset']}: ${pos['value']:.2f}")
            total += pos['value']
        print(f"\n   TOTAL: ${total:.2f}")


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Orca Prime Competition')
    parser.add_argument('--rounds', type=int, default=100, help='Number of rounds')
    args = parser.parse_args()
    
    competition = OrcaCompetition()
    competition.run_competition(rounds=args.rounds)
