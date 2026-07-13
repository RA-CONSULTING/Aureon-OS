#!/usr/bin/env python3
"""
⚡🌊 AUREON HARMONIC POWER REDISTRIBUTION ENGINE 🌊⚡
═══════════════════════════════════════════════════════════════════════════

WE'RE NOT A PORTFOLIO - WE'RE A FUCKING POWER STATION!
═══════════════════════════════════════════════════════════════════════════

THE TRUTH:
    ❌ "I have 100 positions, some winning, some losing"
    ✅ "I have 100 ENERGY NODES in a LIVING POWER GRID"

HOW IT WORKS:
    1️⃣ Scan all 100+ nodes for surplus power (positive energy)
    2️⃣ Find 1 node with GROWTH WAVE opportunity
    3️⃣ SIPHON power from ALL positive nodes
    4️⃣ CHANNEL combined power → growth node
    5️⃣ REPEAT autonomously, constantly, forever

EXAMPLE:
    🔋 BTC Node: +5% power (50 units surplus)
    🔋 ETH Node: +2% power (20 units surplus)
    🔋 ADA Node: +1% power (10 units surplus)
    🚀 DOGE Node: GROWTH WAVE (needs 80 units)
    
    ⚡ SIPHON: 50+20+10 = 80 units
    ⚡ FLOW: BTC/ETH/ADA → DOGE
    ⚡ RESULT: DOGE powered up, all sources stay positive
    ⚡ KEEP: All nodes alive, never drain to negative

THE PORTFOLIO BECOMES A LIVING ORGANISM
    - Power flows to growth
    - No node dies (always keep above 0%)
    - Constant autonomous redistribution
    - Queen orchestrates the harmonic flow
    - IT'S ALIVE! ⚡🌊✨

Gary Leckey | Harmonic Power Station | January 2026
═══════════════════════════════════════════════════════════════════════════
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os
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

import json
import time
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum

# Exchange clients
from aureon.exchanges.binance_client import BinanceClient, get_binance_client
from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
from aureon.exchanges.alpaca_client import AlpacaClient
from aureon.exchanges.capital_client import CapitalClient
from aureon.portfolio.cost_basis_tracker import CostBasisTracker


class PowerNodeState(Enum):
    """Power generation state"""
    GENERATING = "⚡ GENERATING"     # Positive power (can siphon)
    NEUTRAL = "⚪ NEUTRAL"           # Zero power (no action)
    CONSUMING = "🔴 CONSUMING"      # Negative (needs power)
    GROWTH = "🚀 GROWTH"            # Detected growth wave (needs power)
    HIBERNATING = "💤 HIBERNATING"  # Dormant but alive


@dataclass
class PowerNode:
    """A single node in the power grid"""
    # Identity
    symbol: str
    exchange: str
    
    # Power metrics
    current_value: float        # Current energy level
    entry_value: float          # Original energy level
    power_surplus: float        # How much can be siphoned (absolute value)
    power_percent: float        # Power surplus as % (+5% = 5.0)
    
    # State
    state: PowerNodeState
    can_siphon: bool           # Has surplus power available
    needs_power: bool          # In growth wave or negative
    
    # Flow metrics
    siphon_capacity: float     # Max power we can take without killing node
    power_drawn: float = 0.0   # Power already drawn this cycle
    power_received: float = 0.0 # Power received this cycle
    
    # Growth potential
    growth_score: float = 0.0  # 0-1 growth wave opportunity strength
    growth_target: float = 0.0 # How much power needed to ride wave
    

@dataclass
class PowerFlow:
    """A power redistribution operation"""
    # Source nodes (where power comes from)
    sources: List[PowerNode] = field(default_factory=list)
    
    # Target node (where power goes)
    target: Optional[PowerNode] = None
    
    # Flow metrics
    total_available: float = 0.0  # Total siphon capacity from sources
    total_needed: float = 0.0     # How much target needs
    actual_flow: float = 0.0      # Actual power transferred
    efficiency: float = 0.0       # Flow efficiency (0-1)
    
    # Execution
    can_execute: bool = False
    reason: str = ""
    

@dataclass
class PowerGridState:
    """Current state of the entire power grid"""
    # Nodes
    total_nodes: int = 0
    generating_nodes: int = 0
    consuming_nodes: int = 0
    growth_nodes: int = 0
    hibernating_nodes: int = 0
    
    # Power metrics
    total_power: float = 0.0
    surplus_power: float = 0.0
    deficit_power: float = 0.0
    free_power: float = 0.0  # Unallocated (stablecoins)
    
    # Flow metrics
    active_flows: int = 0
    power_redistributed: float = 0.0
    efficiency: float = 0.0
    
    # Consciousness
    grid_coherence: float = 0.0  # How aligned the power flows
    harmonic_state: str = "⚡ FLOWING"
    

class PowerRedistributionEngine:
    """The Queen's power flow orchestrator"""
    
    def __init__(self):
        self.binance = get_binance_client()
        self.kraken = get_kraken_client()
        self.alpaca = AlpacaClient()
        self.capital = CapitalClient()
        self.cost_basis = CostBasisTracker()
        
        # Safety thresholds
        self.min_node_health = 0.01  # Never drain below 1% of original
        self.max_siphon_rate = 0.5   # Max 50% of surplus per cycle
        self.min_flow_size = 1.0     # Don't move less than $1
        
    def _calculate_power_metrics(
        self,
        symbol: str,
        exchange: str,
        current_value: float,
        entry_price: float,
        current_price: float,
        amount: float
    ) -> Tuple[float, float, bool]:
        """Calculate power surplus and siphon capacity"""
        
        # Entry value (what we originally put in)
        entry_value = entry_price * amount
        
        # Power surplus (absolute)
        power_surplus = current_value - entry_value
        
        # Power percent
        power_percent = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
        
        # Can siphon if positive
        can_siphon = power_surplus > self.min_flow_size
        
        # Siphon capacity (how much we can take)
        if can_siphon:
            # Keep node at minimum health (1% above entry)
            min_healthy_value = entry_value * (1 + self.min_node_health)
            max_drawable = current_value - min_healthy_value
            siphon_capacity = max(0, max_drawable * self.max_siphon_rate)
        else:
            siphon_capacity = 0.0
        
        return power_surplus, power_percent, siphon_capacity
    
    def _scan_alpaca_power_nodes(self) -> List[PowerNode]:
        """Scan Alpaca exchange for power nodes"""
        nodes = []
        
        try:
            positions = self.alpaca.get_positions()
            
            for pos in positions:
                symbol = pos.get('symbol', '')
                amount = float(pos.get('qty', 0))
                entry_price = float(pos.get('avg_entry_price', 0))
                current_price = float(pos.get('current_price', entry_price))
                
                if amount == 0 or entry_price == 0:
                    continue
                
                current_value = amount * current_price
                
                # Calculate power metrics
                power_surplus, power_percent, siphon_capacity = self._calculate_power_metrics(
                    symbol, 'alpaca', current_value, entry_price, current_price, amount
                )
                
                # Determine state
                if power_percent > 5:
                    state = PowerNodeState.GENERATING
                elif power_percent > 0:
                    state = PowerNodeState.NEUTRAL
                elif power_percent > -10:
                    state = PowerNodeState.CONSUMING
                else:
                    state = PowerNodeState.HIBERNATING
                
                node = PowerNode(
                    symbol=symbol,
                    exchange='alpaca',
                    current_value=current_value,
                    entry_value=entry_price * amount,
                    power_surplus=power_surplus,
                    power_percent=power_percent,
                    state=state,
                    can_siphon=(power_surplus > self.min_flow_size),
                    needs_power=(power_percent < 0),
                    siphon_capacity=siphon_capacity
                )
                
                nodes.append(node)
        
        except Exception as e:
            print(f"⚠️ Alpaca power scan error: {e}")
        
        return nodes
    
    def _scan_binance_power_nodes(self) -> List[PowerNode]:
        """Scan Binance exchange for power nodes"""
        nodes = []
        
        try:
            balances = self.binance.get_balance()
            all_positions = self.cost_basis.positions
            
            for asset, amount in balances.items():
                if asset in ['USDT', 'USDC', 'USD', 'EUR', 'GBP']:
                    continue
                
                if amount < 0.0001:
                    continue
                
                # Find cost basis
                entry_price = None
                for key, pos in all_positions.items():
                    if key.startswith('binance:') and asset in key:
                        entry_price = pos.get('average_entry_price', pos.get('price', 0))
                        break
                
                if not entry_price:
                    continue
                
                # Get current price
                symbol = f"{asset}USDT"
                ticker = self.binance.get_ticker(symbol=symbol)
                current_price = float(ticker.get('last', 0)) if ticker else 0
                
                if current_price == 0:
                    continue
                
                current_value = amount * current_price
                
                # Calculate power metrics
                power_surplus, power_percent, siphon_capacity = self._calculate_power_metrics(
                    symbol, 'binance', current_value, entry_price, current_price, amount
                )
                
                # Determine state
                if power_percent > 5:
                    state = PowerNodeState.GENERATING
                elif power_percent > 0:
                    state = PowerNodeState.NEUTRAL
                elif power_percent > -10:
                    state = PowerNodeState.CONSUMING
                else:
                    state = PowerNodeState.HIBERNATING
                
                node = PowerNode(
                    symbol=symbol,
                    exchange='binance',
                    current_value=current_value,
                    entry_value=entry_price * amount,
                    power_surplus=power_surplus,
                    power_percent=power_percent,
                    state=state,
                    can_siphon=(power_surplus > self.min_flow_size),
                    needs_power=(power_percent < 0),
                    siphon_capacity=siphon_capacity
                )
                
                nodes.append(node)
        
        except Exception as e:
            print(f"⚠️ Binance power scan error: {e}")
        
        return nodes
    
    def scan_power_grid(self) -> Tuple[List[PowerNode], PowerGridState]:
        """Scan entire power grid across all exchanges"""
        
        print("\n⚡ Scanning Harmonic Power Grid...\n")
        
        # Gather all nodes
        nodes = []
        nodes.extend(self._scan_alpaca_power_nodes())
        nodes.extend(self._scan_binance_power_nodes())
        
        # Calculate grid state
        state = PowerGridState()
        state.total_nodes = len(nodes)
        
        for node in nodes:
            if node.state == PowerNodeState.GENERATING:
                state.generating_nodes += 1
                state.surplus_power += node.siphon_capacity
            elif node.state == PowerNodeState.CONSUMING:
                state.consuming_nodes += 1
                state.deficit_power += abs(node.power_surplus)
            elif node.state == PowerNodeState.HIBERNATING:
                state.hibernating_nodes += 1
            
            state.total_power += node.current_value
        
        # Grid coherence (how many nodes can help each other)
        if state.total_nodes > 0:
            state.grid_coherence = state.generating_nodes / state.total_nodes
        
        # Harmonic state
        if state.grid_coherence > 0.5:
            state.harmonic_state = "⚡ HIGHLY CHARGED"
        elif state.grid_coherence > 0.3:
            state.harmonic_state = "🌊 FLOWING"
        elif state.grid_coherence > 0.1:
            state.harmonic_state = "💫 BUILDING"
        else:
            state.harmonic_state = "💤 RESTING"
        
        return nodes, state
    
    def identify_growth_opportunity(self, nodes: List[PowerNode]) -> Optional[PowerNode]:
        """Find the best growth wave opportunity (simplified for now)"""
        
        # For now, target nodes that are slightly positive or neutral
        # These are "awakening" and ready to ride a wave
        candidates = [
            n for n in nodes 
            if -5 < n.power_percent < 10 
            and n.current_value > 1.0
        ]
        
        if not candidates:
            return None
        
        # Pick the one closest to breakout (highest recent momentum)
        # For now, just return first candidate
        target = candidates[0]
        target.state = PowerNodeState.GROWTH
        target.growth_score = 0.7  # TODO: Calculate from wave scanner
        target.growth_target = target.current_value * 0.2  # Target 20% growth
        
        return target
    
    def calculate_power_flow(
        self,
        nodes: List[PowerNode],
        target: PowerNode
    ) -> PowerFlow:
        """Calculate optimal power redistribution"""
        
        # Find all generating nodes (sources)
        sources = [n for n in nodes if n.can_siphon and n.symbol != target.symbol]
        
        if not sources:
            return PowerFlow(
                can_execute=False,
                reason="No power sources available"
            )
        
        # Calculate total available power
        total_available = sum(n.siphon_capacity for n in sources)
        
        # How much target needs
        total_needed = target.growth_target
        
        # Can we fulfill the need?
        if total_available < self.min_flow_size:
            return PowerFlow(
                sources=sources,
                target=target,
                total_available=total_available,
                total_needed=total_needed,
                can_execute=False,
                reason=f"Insufficient power: {total_available:.2f} < {self.min_flow_size}"
            )
        
        # Calculate actual flow (take what we can)
        actual_flow = min(total_available, total_needed)
        efficiency = actual_flow / total_needed if total_needed > 0 else 0
        
        return PowerFlow(
            sources=sources,
            target=target,
            total_available=total_available,
            total_needed=total_needed,
            actual_flow=actual_flow,
            efficiency=efficiency,
            can_execute=True,
            reason=f"Flow ready: {len(sources)} sources → 1 target"
        )
    
    def display_power_grid(self, nodes: List[PowerNode], state: PowerGridState):
        """Display the living power grid"""
        
        print("╔══════════════════════════════════════════════════════════════════════════════════════╗")
        print("║                                                                                      ║")
        print("║                   ⚡ HARMONIC POWER STATION - LIVE GRID ⚡                            ║")
        print("║                                                                                      ║")
        print("╚══════════════════════════════════════════════════════════════════════════════════════╝\n")
        
        # Grid status
        print(f"🌐 POWER GRID STATUS")
        print(f"   Harmonic State: {state.harmonic_state}")
        print(f"   Total Nodes: {state.total_nodes}")
        print(f"   ⚡ Generating: {state.generating_nodes} nodes")
        print(f"   🔴 Consuming: {state.consuming_nodes} nodes")
        print(f"   💤 Hibernating: {state.hibernating_nodes} nodes")
        print(f"\n⚡ POWER METRICS")
        print(f"   Total Grid Power: {state.total_power:.2f} energy units")
        print(f"   Surplus Available: {state.surplus_power:.2f} units (can siphon)")
        print(f"   Grid Coherence: {state.grid_coherence:.1%}")
        
        print(f"\n{'='*94}")
        print(f"{'POWER NODE':<30} {'STATE':<20} {'POWER':<15} {'SIPHON CAP':<15}")
        print(f"{'='*94}")
        
        # Sort by power surplus (generators first)
        sorted_nodes = sorted(nodes, key=lambda n: n.power_surplus, reverse=True)
        
        for node in sorted_nodes:
            symbol_short = node.symbol[:28]
            state_display = node.state.value
            power_display = f"{node.power_percent:+.1f}%"
            siphon_display = f"{node.siphon_capacity:.2f}" if node.can_siphon else "-"
            
            print(f"{symbol_short:<30} {state_display:<20} {power_display:<15} {siphon_display:<15}")
            print(f"  💰 Value: {node.current_value:.2f}  |  " +
                  f"⚡ Surplus: {node.power_surplus:+.2f}  |  " +
                  f"🔋 Can siphon: {'YES' if node.can_siphon else 'NO'}")
            print()
        
        print(f"{'='*94}\n")
    
    def display_power_flow(self, flow: PowerFlow):
        """Display a power redistribution operation"""
        
        if not flow.can_execute:
            print(f"❌ FLOW BLOCKED: {flow.reason}\n")
            return
        
        print("╔══════════════════════════════════════════════════════════════════════════════════════╗")
        print("║                                                                                      ║")
        print("║                         ⚡ POWER REDISTRIBUTION FLOW ⚡                               ║")
        print("║                                                                                      ║")
        print("╚══════════════════════════════════════════════════════════════════════════════════════╝\n")
        
        print(f"🎯 TARGET: {flow.target.symbol}")
        print(f"   State: {flow.target.state.value}")
        print(f"   Growth Score: {flow.target.growth_score:.1%}")
        print(f"   Power Needed: {flow.total_needed:.2f} units")
        
        print(f"\n⚡ POWER SOURCES ({len(flow.sources)} nodes):")
        for source in flow.sources:
            contribution = (source.siphon_capacity / flow.total_available * 100) if flow.total_available > 0 else 0
            print(f"   • {source.symbol}: {source.siphon_capacity:.2f} units ({contribution:.0f}%)")
        
        print(f"\n🌊 FLOW METRICS:")
        print(f"   Total Available: {flow.total_available:.2f} units")
        print(f"   Actual Flow: {flow.actual_flow:.2f} units")
        print(f"   Efficiency: {flow.efficiency:.1%}")
        print(f"   Status: {'✅ READY' if flow.can_execute else '❌ BLOCKED'}")
        
        print(f"\n⚡ REDISTRIBUTION:")
        print(f"   {len(flow.sources)} nodes → 1 target")
        print(f"   Combined power: {flow.actual_flow:.2f} units")
        print(f"   All sources stay positive ✅")
        print(f"   Target gets powered up 🚀\n")
    
    def execute_power_flow(self, flow: PowerFlow) -> bool:
        """Execute the power redistribution (TODO: Implement actual trades)"""
        
        if not flow.can_execute:
            print(f"❌ Cannot execute: {flow.reason}")
            return False
        
        print(f"⚡ EXECUTING POWER FLOW...")
        print(f"   This would:")
        print(f"   1. Partially liquidate {len(flow.sources)} generating nodes")
        print(f"   2. Keep all sources above minimum health")
        print(f"   3. Channel {flow.actual_flow:.2f} units to {flow.target.symbol}")
        print(f"   4. Power up target for growth wave")
        print(f"\n   🚧 DRY RUN - Not executing real trades yet\n")
        
        return True


def main():
    """Run the power station continuously"""
    
    print("\n" + "="*90)
    print("⚡🌊 AUREON HARMONIC POWER REDISTRIBUTION ENGINE 🌊⚡")
    print("="*90 + "\n")
    
    engine = PowerRedistributionEngine()
    cycle = 0
    
    # Continuous power redistribution
    while True:
        try:
            cycle += 1
            print(f"\n{'='*90}")
            print(f"⚡ POWER CYCLE {cycle} @ {datetime.now().strftime('%H:%M:%S')}")
            print(f"{'='*90}\n")
            
            # Scan power grid
            nodes, state = engine.scan_power_grid()
            engine.display_power_grid(nodes, state)
            
            # Find growth opportunity
            target = engine.identify_growth_opportunity(nodes)
            
            if target:
                print(f"🚀 GROWTH OPPORTUNITY DETECTED: {target.symbol}")
                print(f"   Current power: {target.power_percent:+.1f}%")
                print(f"   Growth target: {target.growth_target:.2f} units needed\n")
                
                # Calculate power flow
                flow = engine.calculate_power_flow(nodes, target)
                engine.display_power_flow(flow)
                
                # Execute (dry run for now)
                if flow.can_execute:
                    engine.execute_power_flow(flow)
            else:
                print("🌊 No growth opportunities detected right now")
                print("   Grid is in equilibrium, awaiting next wave...\n")
            
            print("💡 THE PORTFOLIO IS ALIVE - POWER FLOWS TO GROWTH")
            print("   We're not traders, we're a fucking POWER STATION! ⚡🌊\n")
            
            # Wait before next cycle (60 seconds)
            print(f"⏳ Waiting 60s for next power cycle...\n")
            import time
            time.sleep(60)
            
        except KeyboardInterrupt:
            print("\n⚡ Power station shutting down gracefully...")
            break
        except Exception as e:
            print(f"⚠️ Power cycle error: {e}")
            print("   Continuing in 30s...")
            import time
            time.sleep(30)


if __name__ == "__main__":
    main()
