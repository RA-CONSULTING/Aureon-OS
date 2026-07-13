#!/usr/bin/env python3
"""
🧠 HIVE MIND PORTFOLIO GROWTH 🧠
Moves ALL assets as a coordinated hive intelligence to grow portfolio.

Features:
- Hive mind coordination across all exchanges
- Synchronized trading decisions
- Real balance movement from $7.39
- Collective intelligence optimization
- Live growth tracking
- 306° perfection logic
- Russian doll validation

From $7.39 → Billions through hive coordination!
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys, os
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        def _is_buffer_valid(stream):
            if not hasattr(stream, 'buffer'):
                return False
            try:
                return stream.buffer is not None and not stream.buffer.closed
            except (ValueError, AttributeError):
                return False
        if _is_buffer_valid(sys.stdout) and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if _is_buffer_valid(sys.stderr) and not _is_utf8_wrapper(sys.stderr):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

import asyncio
import json
import math
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Sacred constants
PHI = (1 + math.sqrt(5)) / 2  # 1.618033989 - Golden Ratio
PERFECTION_ANGLE = 306.0  # 360 - 54 (golden angle complement)

# Import our systems
from aureon.portfolio.live_portfolio_growth_tracker import LivePortfolioTracker
from aureon.strategies.quantum_black_box_billion import QuantumBlackBox

# Import exchange clients
try:
    from aureon.exchanges.binance_client import BinanceClient, get_binance_client
    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False

try:
    from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
except ImportError:
    KrakenClient = None

try:
    from aureon.exchanges.alpaca_client import AlpacaClient
except ImportError:
    AlpacaClient = None


@dataclass
class HiveNode:
    """Individual hive mind node (exchange + consciousness)"""
    exchange_name: str
    client: any
    balance_usd: float
    available_assets: Dict[str, float] = field(default_factory=dict)
    active_positions: List[Dict] = field(default_factory=list)
    hive_contribution: float = 0.0  # How much this node contributes to hive decisions
    last_activity: float = 0.0
    consciousness_level: float = 1.0  # 0-1 scale of hive awareness


@dataclass
class HiveDecision:
    """Hive mind collective decision"""
    timestamp: float
    decision_type: str  # 'TRADE', 'REBALANCE', 'GROWTH'
    confidence: float
    hive_consensus: float  # 0-1 agreement level
    participating_nodes: int
    action_plan: Dict
    expected_outcome: Dict
    geometric_alignment: float
    perfection_score: float


@dataclass
class HiveMindPortfolio:
    """Hive mind coordinated portfolio"""
    hive_id: str
    start_time: float
    start_balance_usd: float
    current_balance_usd: float
    hive_nodes: List[HiveNode] = field(default_factory=list)
    hive_decisions: List[HiveDecision] = field(default_factory=list)
    total_trades: int = 0
    successful_trades: int = 0
    hive_intelligence_level: float = 1.0
    collective_consciousness: float = 1.0
    geometric_harmony: float = 0.0
    perfection_alignment: float = 0.0

    def get_total_balance_usd(self) -> float:
        """Returns the current total balance of the hive."""
        return self.current_balance_usd


class HiveMindTrader:
    """
    Hive mind intelligence that coordinates ALL assets across exchanges.
    
    Like a bee hive where each exchange is a worker bee, all working
    together to grow the collective portfolio from $7.39 to billions.
    """
    
    def __init__(self):
        """Initialize hive mind trader."""
        self.portfolio_tracker = LivePortfolioTracker()
        self.black_box = QuantumBlackBox()
        self.hive_portfolio = None
        
        # Hive mind settings
        self.hive_coordination_interval = 30  # seconds between hive decisions
        self.min_hive_consensus = 0.8  # 80% agreement required
        self.max_concurrent_positions = 5  # Max positions across all exchanges
        
        print("🧠 HIVE MIND PORTFOLIO GROWTH INITIALIZING...")
        print("   🐝 Each exchange becomes a worker bee")
        print("   🏆 Collective intelligence grows $7.39 → Billions")
        print("   🎯 306° perfection logic enforced")

    def display_hive_status(self):
        """Display the current status of the hive mind."""
        if not self.hive_portfolio:
            return

        print("\n" + "=" * 80)
        print("🧠 HIVE MIND STATUS 🧠")
        print("=" * 80)
        
        active_duration = (time.time() - self.hive_portfolio.start_time) / 60
        
        print(f"🏆 Hive ID: {self.hive_portfolio.hive_id}")
        print(f"⏱️  Active: {active_duration:.1f} minutes")
        print(f"🐝 Nodes: {len(self.hive_portfolio.hive_nodes)}")
        print()
        
        print("💰 HIVE PORTFOLIO:")
        print(f"   Started:  ${self.hive_portfolio.start_balance_usd:,.2f}")
        print(f"   Current:  ${self.hive_portfolio.current_balance_usd:,.2f}")
        pnl = self.hive_portfolio.current_balance_usd - self.hive_portfolio.start_balance_usd
        growth = (pnl / self.hive_portfolio.start_balance_usd * 100) if self.hive_portfolio.start_balance_usd > 0 else 0
        print(f"   P&L:      ${pnl:+.2f}")
        print(f"   Growth:   {growth:+.2f}%")
        print()

        print("📊 HIVE INTELLIGENCE:")
        print(f"   Collective Consciousness: {self.hive_portfolio.collective_consciousness:.1f}%")
        print(f"   Geometric Harmony: {self.hive_portfolio.geometric_harmony:.1f}%")
        print(f"   Perfection Alignment: {self.hive_portfolio.perfection_alignment:.1f}%")
        print()

        print("🐝 NODE STATUS:")
        for node in self.hive_portfolio.hive_nodes:
            print(f"   {node.exchange_name.upper()}: ${node.balance_usd:,.2f} | Consciousness: {node.consciousness_level:.1f}%")
        print()

        print("📈 TRADING STATS:")
        success_rate = (self.hive_portfolio.successful_trades / self.hive_portfolio.total_trades * 100) if self.hive_portfolio.total_trades > 0 else 0
        print(f"   Total Trades: {self.hive_portfolio.total_trades}")
        print(f"   Success Rate: {success_rate:.1f}%")
        print(f"   Hive Decisions: {len(self.hive_portfolio.hive_decisions)}")
        print()
    
    async def initialize_hive(self):
        """Initialize the hive mind with all available exchanges."""
        print("\n🐝 BUILDING HIVE MIND...")
        
        # Initialize portfolio tracker
        await self.portfolio_tracker.initialize_exchanges()
        
        # Initialize black box
        await self.black_box.initialize()
        
        # Create hive nodes for each exchange
        hive_nodes = []
        
        # Binance node
        if BINANCE_AVAILABLE:
            try:
                binance_client = get_binance_client()
                binance_balance = self._get_exchange_balance(binance_client, 'binance')
                if binance_balance > 0:
                    node = HiveNode(
                        exchange_name='binance',
                        client=binance_client,
                        balance_usd=binance_balance,
                        available_assets=self._get_available_assets(binance_client, 'binance')
                    )
                    hive_nodes.append(node)
                    print(f"   🐝 Binance node: ${binance_balance:.2f}")
            except Exception as e:
                print(f"   ⚠️  Binance node failed: {e}")
        
        # Kraken node
        if KrakenClient:
            try:
                kraken_client = get_kraken_client()
                kraken_balance = self._get_exchange_balance(kraken_client, 'kraken')
                if kraken_balance > 0:
                    node = HiveNode(
                        exchange_name='kraken',
                        client=kraken_client,
                        balance_usd=kraken_balance,
                        available_assets=self._get_available_assets(kraken_client, 'kraken')
                    )
                    hive_nodes.append(node)
                    print(f"   🐝 Kraken node: ${kraken_balance:.2f}")
            except Exception as e:
                print(f"   ⚠️  Kraken node failed: {e}")
        
        # Alpaca node
        if AlpacaClient:
            try:
                alpaca_client = AlpacaClient()
                alpaca_balance = self._get_exchange_balance(alpaca_client, 'alpaca')
                if alpaca_balance > 0:
                    node = HiveNode(
                        exchange_name='alpaca',
                        client=alpaca_client,
                        balance_usd=alpaca_balance,
                        available_assets=self._get_available_assets(alpaca_client, 'alpaca')
                    )
                    hive_nodes.append(node)
                    print(f"   🐝 Alpaca node: ${alpaca_balance:.2f}")
            except Exception as e:
                print(f"   ⚠️  Alpaca node failed: {e}")
        
        # Calculate total hive balance
        total_balance = sum(node.balance_usd for node in hive_nodes)
        
        # Create hive portfolio
        self.hive_portfolio = HiveMindPortfolio(
            hive_id=f"hive_{int(time.time())}",
            start_time=time.time(),
            start_balance_usd=total_balance,
            current_balance_usd=total_balance,
            hive_nodes=hive_nodes
        )
        
        print(f"\n🏆 HIVE MIND READY!")
        print(f"   Total bees: {len(hive_nodes)}")
        print(f"   Collective balance: ${total_balance:.2f}")
        print(f"   Target: Billions through hive intelligence!")
        
        return total_balance > 0
    
    def _get_exchange_balance(self, client: any, exchange: str) -> float:
        """Get total USD balance from exchange.

        Stage AN: was using hardcoded BTC=$95000 / ETH=$3400 multipliers
        (months-old reference prices). Real multipliers now come from the
        live-data fallback chain so a missing/stale primary feed doesn't
        warp portfolio totals broadcast to the operator dashboard.
        """
        try:
            if exchange == 'binance':
                usdt = client.get_free_balance('USDT')
                btc_qty = client.get_free_balance('BTC')
                eth_qty = client.get_free_balance('ETH')
                btc_price = eth_price = 0.0
                if btc_qty or eth_qty:
                    try:
                        from aureon.observer.real_price_fallback import (
                            get_real_prices_with_fallback,
                        )
                        prices, _ = get_real_prices_with_fallback(
                            symbols=['BTC/USD', 'ETH/USD'],
                            max_cache_age_sec=60.0, timeout_sec=4.0,
                        )
                        btc_price = float(prices.get('BTC/USD', 0.0))
                        eth_price = float(prices.get('ETH/USD', 0.0))
                    except Exception:
                        btc_price = eth_price = 0.0
                # Skip components where we couldn't get a real price rather
                # than fabricate the multiplier. Caller sees true USDT plus
                # whatever crypto we could value with real data.
                btc = btc_qty * btc_price if btc_price > 0 else 0.0
                eth = eth_qty * eth_price if eth_price > 0 else 0.0
                return usdt + btc + eth
            elif exchange == 'kraken':
                bal = client.get_account_balance()
                usd_total = 0.0
                for asset, amount in bal.items():
                    if asset in ['ZUSD', 'USD']:
                        usd_total += float(amount)
                return usd_total
            elif exchange == 'alpaca':
                acc = client.get_account()
                return float(acc.get('equity', 0))
        except:
            return 0.0
    
    def _get_available_assets(self, client: any, exchange: str) -> Dict[str, float]:
        """Get available assets for trading."""
        assets = {}
        try:
            if exchange == 'binance':
                assets['USDT'] = client.get_free_balance('USDT')
                assets['BTC'] = client.get_free_balance('BTC')
                assets['ETH'] = client.get_free_balance('ETH')
            elif exchange == 'kraken':
                bal = client.get_account_balance()
                for asset, amount in bal.items():
                    if float(amount) > 0.0001:
                        assets[asset] = float(amount)
            elif exchange == 'alpaca':
                acc = client.get_account()
                assets['USD'] = float(acc.get('cash', 0))
                assets['EQUITY'] = float(acc.get('equity', 0))
        except:
            pass
        return assets
    
    async def hive_consensus_decision(self) -> Optional[HiveDecision]:
        """
        Hive mind reaches consensus on next action.
        
        All nodes contribute their intelligence to make collective decision.
        """
        if not self.hive_portfolio or not self.hive_portfolio.hive_nodes:
            return None
        
        # Generate prediction from black box, using the actual hive balance
        available_balance = self.hive_portfolio.get_total_balance_usd() if self.hive_portfolio else 0.0
        prediction = await self.black_box.generate_prediction(available_balance=available_balance)
        if not prediction:
            return None
        
        # Hive nodes vote on the decision
        votes_for = 0
        votes_against = 0
        node_contributions = []
        
        for node in self.hive_portfolio.hive_nodes:
            # Each node evaluates the prediction
            node_opinion = await self._node_evaluate_prediction(node, prediction)
            node_contributions.append(node_opinion)
            
            if node_opinion['support']:
                votes_for += 1
            else:
                votes_against += 1
        
        # Calculate consensus
        total_votes = len(self.hive_portfolio.hive_nodes)
        consensus_level = votes_for / total_votes if total_votes > 0 else 0
        
        # Only proceed if hive agrees
        if consensus_level < self.min_hive_consensus:
            print(f"🐝 Hive consensus too low: {consensus_level:.1%} (need {self.min_hive_consensus:.1%})")
            return None
        
        # Calculate geometric alignment
        avg_confidence = sum(c['confidence'] for c in node_contributions) / len(node_contributions)
        geometric_alignment = self._calculate_hive_alignment(prediction, node_contributions)
        perfection_score = self._calculate_hive_perfection(geometric_alignment)
        
        # Create hive decision
        decision = HiveDecision(
            timestamp=time.time(),
            decision_type='TRADE',
            confidence=avg_confidence,
            hive_consensus=consensus_level,
            participating_nodes=total_votes,
            action_plan={
                'symbol': prediction.get('symbol'),
                'action': prediction.get('action'),
                'quantity': prediction.get('quantity', 0),
                'exchange': prediction.get('exchange'),
                'hive_coordination': True
            },
            expected_outcome={
                'expected_return': prediction.get('expected_return', 0),
                'risk_level': 'hive_managed',
                'coordination_benefit': consensus_level
            },
            geometric_alignment=geometric_alignment,
            perfection_score=perfection_score
        )
        
        return decision
    
    async def _node_evaluate_prediction(self, node: HiveNode, prediction: Dict) -> Dict:
        """Individual node evaluates a prediction."""
        # Node considers its own balance and capabilities
        confidence = prediction.get('confidence', 0) * node.consciousness_level
        
        # Node checks if it can execute this trade
        can_execute = self._node_can_execute_trade(node, prediction)
        
        # Node calculates its contribution to hive
        contribution = node.balance_usd / self.hive_portfolio.current_balance_usd
        
        # Node simply votes based on confidence, not full execution capacity
        return {
            'node': node.exchange_name,
            'support': confidence > 0.7, # Simplified vote
            'confidence': confidence,
            'contribution': contribution,
            'can_execute': self._node_can_execute_trade(node, prediction) # Still check for logging
        }
    
    def _node_can_execute_trade(self, node: HiveNode, prediction: Dict) -> bool:
        """Check if node can execute the trade."""
        symbol = prediction.get('symbol', '')
        action = prediction.get('action', '')
        quantity = prediction.get('quantity', 0)
        
        # Check if node has required assets
        if action.lower() == 'buy':
            # Need cash/USD
            cash_available = node.available_assets.get('USD', 0) + node.available_assets.get('USDT', 0)
            estimated_cost = quantity * self.black_box.get_live_price(symbol, node.exchange_name)
            return cash_available >= estimated_cost
        elif action.lower() == 'sell':
            # Need the asset
            asset_needed = symbol.split('/')[0] if '/' in symbol else symbol
            asset_available = node.available_assets.get(asset_needed, 0)
            return asset_available >= quantity
        
        return False
    
    def _calculate_hive_alignment(self, prediction: Dict, node_contributions: List[Dict]) -> float:
        """Calculate geometric alignment across hive."""
        # Use prediction confidence and node consensus
        base_alignment = prediction.get('confidence', 0) / 100.0
        
        # Boost alignment based on hive agreement
        consensus_boost = sum(c['contribution'] * (1 if c['support'] else 0) for c in node_contributions)
        
        return min(1.0, base_alignment * (1 + consensus_boost))
    
    def _calculate_hive_perfection(self, alignment: float) -> float:
        """Calculate how close hive is to 306° perfection."""
        # Map alignment to geometric angle approaching 306°
        angle = 240.0 + (alignment * 66.0)  # 240° to 306° range
        
        # Calculate distance from perfection
        distance = abs(angle - PERFECTION_ANGLE)
        if distance > 180:
            distance = 360 - distance
        
        return max(0.0, 1.0 - (distance / 180.0))
    
    async def execute_hive_decision(self, decision: HiveDecision) -> bool:
        """Execute hive decision across participating nodes."""
        if decision.decision_type != 'TRADE':
            return False
        
        action_plan = decision.action_plan
        symbol = action_plan['symbol']
        action = action_plan['action']
        
        # Find best node to execute, even with partial assets
        best_node = None
        best_score = 0
        
        # Find a node that has *any* of the required asset for selling, or cash for buying
        for node in self.hive_portfolio.hive_nodes:
            if self._node_can_partially_execute(node, action_plan):
                score = node.balance_usd  # Simple score, pick wealthiest node that can act
                if score > best_score:
                    best_score = score
                    best_node = node

        if not best_node:
            print("🐝 No hive node has any assets to execute this trade")
            return False
            
        # Adjust quantity to what the node can actually do
        executable_quantity = self._get_executable_quantity(best_node, action_plan)

        if executable_quantity <= 0.00001: # Add a small threshold
            print(f"🐝 Node {best_node.exchange_name} has no executable quantity.")
            return False

        print(f"🐝 Best node for execution: {best_node.exchange_name} with executable quantity {executable_quantity:.8f}")

        # Execute trade on best node with the quantity it can handle
        try:
            # The client's execute_trade is async
            result = await best_node.client.execute_trade(symbol, action, executable_quantity)
            
            if result and (result.get('status') == 'filled' or result.get('id')):
                # Update hive portfolio
                self.hive_portfolio.total_trades += 1
                
                # Estimate P&L (simplified)
                price = float(result.get('price', self.black_box.get_live_price(symbol, best_node.exchange_name)))
                usd_value = price * executable_quantity
                
                if action.lower() == 'sell':
                    pnl = usd_value
                else:
                    pnl = -usd_value
                
                self.hive_portfolio.current_balance_usd += pnl
                self.hive_portfolio.successful_trades += 1
                
                print(f"✅ Hive trade executed on {best_node.exchange_name}: {action} {executable_quantity:.8f} {symbol}")
                return True
            else:
                error_message = "Unknown error"
                if isinstance(result, dict):
                    error_message = result.get('error', result.get('message', 'Unknown error'))
                print(f"❌ Hive trade failed on {best_node.exchange_name}: {error_message}")
                return False
        except Exception as e:
            print(f"💥 Exception during hive execution: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _node_can_partially_execute(self, node: HiveNode, prediction: Dict) -> bool:
        """Check if a node has any of the required asset to participate in a trade."""
        action = prediction.get('action', '')
        symbol = prediction.get('symbol', '')

        if action.lower() == 'buy':
            # Check for any USD/USDT to buy with
            cash = node.available_assets.get('USD', 0) + node.available_assets.get('USDT', 0)
            return cash > 0.1 # Min cash to trade
        elif action.lower() == 'sell':
            # Check for any of the asset to sell
            asset_needed = symbol.split('/')[0].upper() if '/' in symbol else symbol.upper()
            return node.available_assets.get(asset_needed, 0) > 0
        return False

    def _get_executable_quantity(self, node: HiveNode, prediction: Dict) -> float:
        """Get the actual quantity a node can trade."""
        action = prediction.get('action', '')
        symbol = prediction.get('symbol', '')

        if action.lower() == 'buy':
            cash_available = node.available_assets.get('USD', 0) + node.available_assets.get('USDT', 0)
            price = self.black_box.get_live_price(symbol, node.exchange_name)
            if not price or price <= 0:
                return 0
            # Use 95% of available cash to be safe and avoid precision errors
            return (cash_available * 0.95) / price
        elif action.lower() == 'sell':
            asset_needed = symbol.split('/')[0].upper() if '/' in symbol else symbol.upper()
            asset_available = node.available_assets.get(asset_needed, 0)
            # Sell all available of that asset
            return asset_available
        return 0

    async def run_hive_growth_session(self, duration_minutes: int = 60):
        """Main loop for hive mind growth."""
        print(f"\n🚀 STARTING HIVE MIND GROWTH SESSION - {duration_minutes} minutes")
        print("   🐝 All exchanges coordinate as worker bees")
        print("   🧠 Collective intelligence grows your $7.39")
        print("   🎯 306° perfection logic enforced")
        
        # Initialize hive
        hive_ready = await self.initialize_hive()
        if not hive_ready:
            print("❌ Hive initialization failed - no balances found")
            return
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        decision_count = 0
        
        try:
            while time.time() < end_time:
                # Update hive consciousness
                self._update_hive_consciousness()
                
                # Display status every 5 minutes
                if decision_count % 10 == 0:  # Every 5 minutes (10 * 30s)
                    self.display_hive_status()
                
                # Hive reaches consensus
                decision = await self.hive_consensus_decision()
                
                if decision:
                    print(f"\n🧠 HIVE DECISION #{decision_count + 1}:")
                    print(f"   Type: {decision.decision_type}")
                    print(f"   Consensus: {decision.hive_consensus*100:.1f}%")
                    print(f"   Confidence: {decision.confidence*100:.1f}%")
                    print(f"   Perfection: {decision.perfection_score*100:.1f}%")
                    
                    # Execute decision
                    success = await self.execute_hive_decision(decision)
                    
                    if success:
                        self.hive_portfolio.hive_decisions.append(decision)
                        decision_count += 1
                        print("   ✅ Executed successfully!")
                    else:
                        print("   ❌ Execution failed")
                
                # Wait for next hive coordination
                await asyncio.sleep(self.hive_coordination_interval)
        
        except KeyboardInterrupt:
            print("\n\n⏹️  Hive session stopped by user")
        
        # Final status
        print("\n" + "="*80)
        print("🏁 HIVE MIND SESSION COMPLETE 🏁")
        print("="*80)
        
        self.display_hive_status()
        
        # Calculate final growth
        if self.hive_portfolio.start_balance_usd > 0:
            final_growth = ((self.hive_portfolio.current_balance_usd / self.hive_portfolio.start_balance_usd) - 1) * 100
            print(f"\n🎉 HIVE RESULT: {final_growth:+.2f}% growth!")
            print(f"   Started: ${self.hive_portfolio.start_balance_usd:.2f}")
            print(f"   Ended:   ${self.hive_portfolio.current_balance_usd:.2f}")
            print(f"   P&L:    ${self.hive_portfolio.current_balance_usd - self.hive_portfolio.start_balance_usd:+.2f}")
    
    def _update_hive_consciousness(self):
        """Update collective hive consciousness."""
        if not self.hive_portfolio:
            return
        
        # Consciousness grows with successful trades
        success_rate = (self.hive_portfolio.successful_trades / 
                       max(1, self.hive_portfolio.total_trades))
        
        # Geometric harmony based on balance distribution
        total_balance = self.hive_portfolio.current_balance_usd
        if total_balance > 0:
            balance_distribution = [node.balance_usd / total_balance 
                                  for node in self.hive_portfolio.hive_nodes]
            # Ideal distribution approaches golden ratio
            harmony = 1.0 - abs(sum(balance_distribution) / len(balance_distribution) - 1/PHI)
        else:
            harmony = 0.0
        
        # Update hive metrics
        self.hive_portfolio.hive_intelligence_level = min(1.0, success_rate * 1.2)
        self.hive_portfolio.collective_consciousness = min(1.0, success_rate + 0.3)
        self.hive_portfolio.geometric_harmony = harmony
        self.hive_portfolio.perfection_alignment = self._calculate_hive_perfection(harmony)


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hive Mind Portfolio Growth')
    parser.add_argument('--duration', type=float, default=30.0, help='Session duration in minutes')
    parser.add_argument('--demo', action='store_true', help='Demo mode (no real trades)')
    
    args = parser.parse_args()
    
    # Create hive mind trader
    hive = HiveMindTrader()
    
    if args.demo:
        print("🎭 DEMO MODE - Hive coordination simulation")
        # Just show current balances and hive structure
        hive_ready = await hive.initialize_hive()
        if hive_ready:
            hive.display_hive_status()
    else:
        print("🐝 LIVE MODE - Real hive coordination with actual trades!")
        await hive.run_hive_growth_session(duration_minutes=args.duration)


if __name__ == "__main__":
    asyncio.run(main())