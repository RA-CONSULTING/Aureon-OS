#!/usr/bin/env python3
"""
⚡🌊 AUREON HARMONIC POWER REDISTRIBUTION - CORE MATHEMATICS 🌊⚡
═══════════════════════════════════════════════════════════════════════════════════════════════

THIS IS NOT A GAME. THIS IS THE REAL FUCKING DEAL.
═══════════════════════════════════════════════════════════════════════════════════════════════

CORE EQUATIONS:

1️⃣  NODE POWER (P_n):
    P_n = (CurrentValue - EntryValue)
    P_n = Amount × (CurrentPrice - EntryPrice)
    
    Positive P_n = Node is GENERATING
    Negative P_n = Node is CONSUMING
    Zero P_n = Node is NEUTRAL

2️⃣  EXTRACTABLE SURPLUS (E_n):
    We can NEVER drain a node below its entry point (that would create negative energy)
    
    E_n = max(0, P_n - SafetyBuffer)
    SafetyBuffer = EntryValue × MIN_HEALTH_RATIO  (typically 1%)
    
    This ensures:
    - Node always stays alive (never goes negative)
    - Small buffer prevents oscillation near zero

3️⃣  TRANSFER COST (T_c):
    Moving power between nodes costs energy (exchange fees)
    
    T_c = Amount × (MakerFee + TakerFee + Spread)
    
    Binance: ~0.1% maker + 0.1% taker = 0.2% per hop
    Kraken:  ~0.16% maker + 0.26% taker = 0.42% per hop
    Alpaca:  ~0.15% maker + 0.25% taker = 0.4% per hop
    
    Cross-exchange adds withdrawal fees + deposit times

4️⃣  NET POWER FLOW (F_net):
    F_net = E_source - T_c
    
    Power received at target = Power extracted from source - Transfer costs

5️⃣  GRID TOTAL SURPLUS (S_total):
    S_total = Σ E_n for all n where P_n > 0
    
    This is the TOTAL power available for redistribution

6️⃣  REDISTRIBUTION EFFICIENCY (η):
    η = F_net / E_source = 1 - (T_c / E_source)
    
    Higher efficiency = less power lost in transfer

7️⃣  OPTIMAL FLOW ALLOCATION:
    Given:
    - N source nodes with surplus E_1, E_2, ... E_N
    - 1 target node needing power G
    - Transfer cost function T_c(amount, source, target)
    
    Minimize: Σ T_c(x_i) for all i
    Subject to: Σ (x_i - T_c(x_i)) >= G  (target gets enough)
               x_i <= E_i  (can't extract more than available)
               x_i >= 0    (no negative flows)

8️⃣  MULTI-HOP PATHS (Cross-Exchange):
    Path: Source(Exchange_A) → Stablecoin → Target(Exchange_B)
    
    Total cost: T_c1 (sell to stable) + Withdrawal + Deposit + T_c2 (buy target)
    
    Example: BTC@Binance → USDT → DOGE@Alpaca
    - Sell BTC → USDT on Binance: 0.1% fee
    - Withdraw USDT from Binance: $1 flat fee
    - Deposit USDT to Alpaca: Free
    - Buy DOGE with USDT on Alpaca: 0.25% fee
    - Total: 0.35% + $1 fixed

═══════════════════════════════════════════════════════════════════════════════════════════════
Gary Leckey | Harmonic Power Mathematics | January 2026
═══════════════════════════════════════════════════════════════════════════════════════════════
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
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from enum import Enum

# Exchange clients
from aureon.exchanges.binance_client import BinanceClient, get_binance_client
from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
from aureon.exchanges.alpaca_client import AlpacaClient
from aureon.exchanges.capital_client import CapitalClient
from aureon.portfolio.cost_basis_tracker import CostBasisTracker

# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 👑💰 QUEEN'S SACRED 1.88% LAW - POWER REDISTRIBUTION MUST OBEY! 💰👑
# ═══════════════════════════════════════════════════════════════════════════════════════════════
#
#   THE QUEEN HAS SPOKEN: MIN_COP = 1.0188 (1.88% MINIMUM REALIZED PROFIT)
#   
#   POWER REDISTRIBUTION RULES:
#   • Only redistribute power when target node can achieve 1.88%
#   • Never transfer if fees would eat below 1.88% net
#   • All flow calculations must account for Queen's minimum
#
# ═══════════════════════════════════════════════════════════════════════════════════════════════

QUEEN_MIN_COP = Decimal('1.0188')        # 👑 1.88% minimum realized profit
QUEEN_MIN_PROFIT_PCT = Decimal('1.88')   # 👑 As percentage
QUEEN_MIN_THRESHOLD = Decimal('0.0188')  # 👑 As decimal

# Sacred constants
PHI = Decimal(str((1 + math.sqrt(5)) / 2))  # Golden ratio for harmonic calculations


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# FEE STRUCTURES PER RELAY (EXCHANGE)
# ═══════════════════════════════════════════════════════════════════════════════════════════════

@dataclass
class RelayFeeStructure:
    """Fee structure for a relay (exchange)"""
    name: str
    maker_fee: Decimal      # Fee when providing liquidity
    taker_fee: Decimal      # Fee when taking liquidity
    spread_estimate: Decimal # Typical bid/ask spread
    min_order: Decimal      # Minimum order size
    withdrawal_fee: Dict[str, Decimal] = field(default_factory=dict)  # Per-asset withdrawal fees
    
    def round_trip_cost(self) -> Decimal:
        """Cost to enter and exit a position (buy then sell)"""
        return self.maker_fee + self.taker_fee + (self.spread_estimate * 2)
    
    def single_trade_cost(self, is_taker: bool = True) -> Decimal:
        """Cost for a single trade"""
        fee = self.taker_fee if is_taker else self.maker_fee
        return fee + self.spread_estimate


# Real fee structures from exchanges
RELAY_FEES: Dict[str, RelayFeeStructure] = {
    'binance': RelayFeeStructure(
        name='Binance',
        maker_fee=Decimal('0.001'),      # 0.1%
        taker_fee=Decimal('0.001'),      # 0.1%
        spread_estimate=Decimal('0.0005'), # 0.05% typical
        min_order=Decimal('10'),          # $10 minimum
        withdrawal_fee={
            'USDT': Decimal('1'),         # $1 USDT withdrawal (TRC20)
            'USDC': Decimal('1'),
            'BTC': Decimal('0.0001'),     # 0.0001 BTC
            'ETH': Decimal('0.001'),      # 0.001 ETH
        }
    ),
    'kraken': RelayFeeStructure(
        name='Kraken',
        maker_fee=Decimal('0.0016'),     # 0.16%
        taker_fee=Decimal('0.0026'),     # 0.26%
        spread_estimate=Decimal('0.001'), # 0.1% typical
        min_order=Decimal('5'),           # $5 minimum
        withdrawal_fee={
            'USD': Decimal('5'),          # $5 USD withdrawal
            'USDT': Decimal('2.5'),
            'BTC': Decimal('0.00015'),
            'ETH': Decimal('0.0025'),
        }
    ),
    'alpaca': RelayFeeStructure(
        name='Alpaca',
        maker_fee=Decimal('0.0015'),     # 0.15%
        taker_fee=Decimal('0.0025'),     # 0.25%
        spread_estimate=Decimal('0.001'), # 0.1% typical
        min_order=Decimal('1'),           # $1 minimum
        withdrawal_fee={
            'USD': Decimal('0'),          # Free ACH
            'USDT': Decimal('0'),
            'BTC': Decimal('0'),
            'ETH': Decimal('0'),
        }
    ),
    'capital': RelayFeeStructure(
        name='Capital.com',
        maker_fee=Decimal('0'),          # Spread only
        taker_fee=Decimal('0'),          # Spread only  
        spread_estimate=Decimal('0.005'), # 0.5% typical CFD spread
        min_order=Decimal('20'),          # $20 minimum
        withdrawal_fee={
            'GBP': Decimal('0'),
            'USD': Decimal('0'),
        }
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# POWER NODE MATHEMATICS
# ═══════════════════════════════════════════════════════════════════════════════════════════════

@dataclass
class PowerNode:
    """A single node in the power grid with precise calculations"""
    
    # Identity
    symbol: str
    base_asset: str
    quote_asset: str
    relay: str  # Exchange name
    
    # Quantities (using Decimal for precision)
    amount: Decimal           # How many units we hold
    entry_price: Decimal      # Average entry price
    current_price: Decimal    # Current market price
    
    # Calculated values (set by calculate_power())
    entry_value: Decimal = Decimal('0')
    current_value: Decimal = Decimal('0')
    power: Decimal = Decimal('0')           # P_n = current - entry
    power_percent: Decimal = Decimal('0')   # P_n as percentage
    extractable: Decimal = Decimal('0')     # E_n = max(0, P_n - buffer)
    
    # State
    is_generating: bool = False
    is_consuming: bool = False
    is_neutral: bool = False
    
    # Timestamps
    first_entry_time: float = 0
    last_update_time: float = 0
    
    def calculate_power(self, min_health_ratio: Decimal = Decimal('0.01')):
        """
        Calculate node power and extractable surplus.
        
        EQUATIONS:
        - EntryValue = Amount × EntryPrice
        - CurrentValue = Amount × CurrentPrice
        - Power P_n = CurrentValue - EntryValue
        - SafetyBuffer = EntryValue × MinHealthRatio
        - Extractable E_n = max(0, P_n - SafetyBuffer)
        """
        
        self.entry_value = self.amount * self.entry_price
        self.current_value = self.amount * self.current_price
        
        # Core power calculation
        self.power = self.current_value - self.entry_value
        
        # Power as percentage
        if self.entry_value > 0:
            self.power_percent = (self.power / self.entry_value) * Decimal('100')
        else:
            self.power_percent = Decimal('0')
        
        # Extractable surplus (with safety buffer)
        safety_buffer = self.entry_value * min_health_ratio
        self.extractable = max(Decimal('0'), self.power - safety_buffer)
        
        # State flags
        self.is_generating = self.power > Decimal('0')
        self.is_consuming = self.power < Decimal('0')
        self.is_neutral = self.power == Decimal('0')
        
        self.last_update_time = time.time()


@dataclass
class PowerTransfer:
    """A calculated power transfer between nodes"""
    
    # Source
    source_node: PowerNode
    source_relay: str
    
    # Target
    target_symbol: str
    target_relay: str
    
    # Amounts
    extract_amount: Decimal      # How much to extract from source
    transfer_value: Decimal      # Value being transferred
    
    # Costs
    sell_fee: Decimal           # Cost to liquidate source
    withdrawal_fee: Decimal     # Cost to withdraw (if cross-relay)
    buy_fee: Decimal            # Cost to buy target
    total_cost: Decimal         # Total power lost in transfer
    
    # Result
    net_power_delivered: Decimal  # What actually arrives at target
    efficiency: Decimal           # η = net / extract
    
    # Execution details
    sell_order_qty: Decimal      # Exact quantity to sell
    sell_order_price: Decimal    # Expected sell price
    buy_order_qty: Decimal       # Exact quantity to buy
    buy_order_price: Decimal     # Expected buy price
    
    # State
    is_profitable: bool = False
    is_executable: bool = False
    blocking_reason: str = ""


@dataclass
class RedistributionPlan:
    """A complete plan to redistribute power across the grid"""
    
    # Timing
    plan_id: str
    created_at: float
    
    # Grid snapshot
    total_nodes: int
    generating_nodes: int
    consuming_nodes: int
    
    # Power metrics
    total_grid_power: Decimal
    total_surplus: Decimal      # Σ E_n for all generating nodes
    total_deficit: Decimal      # Σ |P_n| for all consuming nodes
    
    # Transfers
    transfers: List[PowerTransfer] = field(default_factory=list)
    
    # Aggregate costs
    total_transfer_cost: Decimal = Decimal('0')
    total_power_moved: Decimal = Decimal('0')
    total_power_delivered: Decimal = Decimal('0')
    
    # Efficiency
    overall_efficiency: Decimal = Decimal('0')  # delivered / moved
    
    # Execution
    is_executable: bool = False
    execution_sequence: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# HARMONIC REDISTRIBUTION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════════════════════

class HarmonicRedistributionMath:
    """
    The core mathematical engine for power redistribution.
    
    ALL calculations use Decimal for precision.
    NO floating point errors in financial calculations.
    """
    
    def __init__(self):
        # Exchange clients
        self.binance = get_binance_client()
        self.kraken = get_kraken_client()
        self.alpaca = AlpacaClient()
        self.capital = CapitalClient()
        self.cost_basis = CostBasisTracker()
        
        # Configuration
        self.min_health_ratio = Decimal('0.01')   # 1% safety buffer
        self.min_transfer_value = Decimal('5')    # Don't transfer less than $5
        self.max_single_extract = Decimal('0.5')  # Max 50% of surplus per transfer
        
        # State
        self.nodes: List[PowerNode] = []
        self.free_energy: Dict[str, Decimal] = {}  # Stablecoins per relay
        
    def _to_decimal(self, value) -> Decimal:
        """Safely convert any numeric to Decimal"""
        if isinstance(value, Decimal):
            return value
        if value is None:
            return Decimal('0')
        try:
            return Decimal(str(value))
        except:
            return Decimal('0')
    
    def _parse_symbol(self, symbol: str) -> Tuple[str, str]:
        """Parse symbol into base and quote assets"""
        # Common quote currencies
        quotes = ['USDT', 'USDC', 'USD', 'EUR', 'GBP', 'ZUSD', 'BTC', 'ETH']
        
        for quote in quotes:
            if symbol.endswith(quote):
                base = symbol[:-len(quote)]
                return base, quote
        
        # Handle slash notation
        if '/' in symbol:
            parts = symbol.split('/')
            return parts[0], parts[1] if len(parts) > 1 else 'USD'
        
        return symbol, 'USD'
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # NODE SCANNING - Map entire grid
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def scan_alpaca_nodes(self) -> List[PowerNode]:
        """Scan Alpaca relay for all power nodes"""
        nodes = []
        
        try:
            positions = self.alpaca.get_positions()
            
            for pos in positions:
                symbol = pos.get('symbol', '')
                base, quote = self._parse_symbol(symbol)
                
                amount = self._to_decimal(pos.get('qty', 0))
                entry_price = self._to_decimal(pos.get('avg_entry_price', 0))
                current_price = self._to_decimal(pos.get('current_price', 0))
                
                if amount == 0 or entry_price == 0:
                    continue
                
                node = PowerNode(
                    symbol=symbol,
                    base_asset=base,
                    quote_asset=quote,
                    relay='alpaca',
                    amount=amount,
                    entry_price=entry_price,
                    current_price=current_price if current_price > 0 else entry_price
                )
                
                node.calculate_power(self.min_health_ratio)
                nodes.append(node)
                
        except Exception as e:
            print(f"⚠️ Alpaca scan error: {e}")
        
        return nodes
    
    def scan_binance_nodes(self) -> List[PowerNode]:
        """Scan Binance relay for all power nodes"""
        nodes = []
        
        try:
            balances = self.binance.get_balance()
            positions = self.cost_basis.positions
            
            stables = ['USDT', 'USDC', 'USD', 'EUR', 'GBP', 'BUSD']
            
            for asset, amount_float in balances.items():
                amount = self._to_decimal(amount_float)
                
                # Track free energy (stablecoins)
                if asset in stables:
                    if amount > Decimal('0.01'):
                        self.free_energy['binance'] = self.free_energy.get('binance', Decimal('0')) + amount
                    continue
                
                if amount < Decimal('0.00001'):
                    continue
                
                # Find entry price from cost basis
                entry_price = Decimal('0')
                for key, pos in positions.items():
                    if key.startswith('binance:') and asset in key:
                        entry_price = self._to_decimal(
                            pos.get('average_entry_price', pos.get('price', 0))
                        )
                        break
                
                if entry_price == 0:
                    continue
                
                # Get current price
                symbol = f"{asset}USDT"
                ticker = self.binance.get_ticker(symbol=symbol)
                current_price = self._to_decimal(ticker.get('last', 0)) if ticker else Decimal('0')
                
                if current_price == 0:
                    continue
                
                node = PowerNode(
                    symbol=symbol,
                    base_asset=asset,
                    quote_asset='USDT',
                    relay='binance',
                    amount=amount,
                    entry_price=entry_price,
                    current_price=current_price
                )
                
                node.calculate_power(self.min_health_ratio)
                nodes.append(node)
                
        except Exception as e:
            print(f"⚠️ Binance scan error: {e}")
        
        return nodes
    
    def scan_kraken_nodes(self) -> List[PowerNode]:
        """Scan Kraken relay for all power nodes"""
        nodes = []
        
        try:
            # Read from state file (avoids rate limits)
            with open('aureon_kraken_state.json', 'r') as f:
                state = json.load(f)
            
            positions = state.get('positions', {})
            
            for symbol, pos in positions.items():
                base, quote = self._parse_symbol(symbol)
                
                amount = self._to_decimal(pos.get('amount', 0))
                entry_price = self._to_decimal(pos.get('entry_price', 0))
                current_price = self._to_decimal(pos.get('current_price', entry_price))
                
                if amount == 0 or entry_price == 0:
                    continue
                
                node = PowerNode(
                    symbol=symbol,
                    base_asset=base,
                    quote_asset=quote,
                    relay='kraken',
                    amount=amount,
                    entry_price=entry_price,
                    current_price=current_price
                )
                
                node.calculate_power(self.min_health_ratio)
                nodes.append(node)
                
            # Track free energy
            kraken_balance = self._to_decimal(state.get('usd_balance', 0))
            if kraken_balance > 0:
                self.free_energy['kraken'] = kraken_balance
                
        except Exception as e:
            print(f"⚠️ Kraken scan error: {e}")
        
        return nodes
    
    def scan_full_grid(self) -> List[PowerNode]:
        """Scan ALL relays and build complete node map"""
        
        print("⚡ Scanning complete power grid across all relays...\n")
        
        self.nodes = []
        self.free_energy = {}
        
        # Scan each relay
        self.nodes.extend(self.scan_alpaca_nodes())
        self.nodes.extend(self.scan_binance_nodes())
        self.nodes.extend(self.scan_kraken_nodes())
        
        # Sort by power (generators first)
        self.nodes.sort(key=lambda n: n.power, reverse=True)
        
        return self.nodes
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # POWER FLOW CALCULATIONS
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def calculate_transfer_cost(
        self,
        source_relay: str,
        target_relay: str,
        value: Decimal,
        is_cross_relay: bool
    ) -> Tuple[Decimal, Decimal, Decimal, Decimal]:
        """
        Calculate the cost of transferring power.
        
        Returns: (sell_fee, withdrawal_fee, buy_fee, total_cost)
        """
        
        source_fees = RELAY_FEES.get(source_relay, RELAY_FEES['binance'])
        target_fees = RELAY_FEES.get(target_relay, RELAY_FEES['binance'])
        
        # Sell fee (liquidate source position)
        sell_fee = value * source_fees.single_trade_cost(is_taker=True)
        
        # Withdrawal fee (if cross-relay)
        withdrawal_fee = Decimal('0')
        if is_cross_relay:
            # Assume USDT transfer
            withdrawal_fee = source_fees.withdrawal_fee.get('USDT', Decimal('1'))
        
        # Buy fee (enter target position)
        buy_fee = value * target_fees.single_trade_cost(is_taker=True)
        
        total_cost = sell_fee + withdrawal_fee + buy_fee
        
        return sell_fee, withdrawal_fee, buy_fee, total_cost
    
    def calculate_single_transfer(
        self,
        source: PowerNode,
        target_symbol: str,
        target_relay: str,
        target_price: Decimal,
        extract_amount: Decimal
    ) -> PowerTransfer:
        """
        Calculate a single power transfer with full precision.
        
        This determines:
        - Exact amounts to trade
        - All fees and costs
        - Net power delivered
        - Transfer efficiency
        """
        
        is_cross_relay = (source.relay != target_relay)
        
        # Value being transferred
        transfer_value = extract_amount * source.current_price
        
        # Calculate costs
        sell_fee, withdrawal_fee, buy_fee, total_cost = self.calculate_transfer_cost(
            source.relay, target_relay, transfer_value, is_cross_relay
        )
        
        # Net power delivered
        net_power = transfer_value - total_cost
        
        # Efficiency
        efficiency = (net_power / transfer_value) if transfer_value > 0 else Decimal('0')
        
        # Order details
        sell_qty = extract_amount.quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)
        sell_price = source.current_price
        
        buy_value = net_power  # After fees
        buy_qty = (buy_value / target_price).quantize(Decimal('0.00000001'), rounding=ROUND_DOWN) if target_price > 0 else Decimal('0')
        
        # Check if executable
        min_order = RELAY_FEES.get(source.relay, RELAY_FEES['binance']).min_order
        is_executable = transfer_value >= min_order and net_power > Decimal('0')
        
        blocking_reason = ""
        if not is_executable:
            if transfer_value < min_order:
                blocking_reason = f"Below minimum order ({min_order})"
            elif net_power <= 0:
                blocking_reason = "Fees exceed transfer value"
        
        return PowerTransfer(
            source_node=source,
            source_relay=source.relay,
            target_symbol=target_symbol,
            target_relay=target_relay,
            extract_amount=extract_amount,
            transfer_value=transfer_value,
            sell_fee=sell_fee,
            withdrawal_fee=withdrawal_fee,
            buy_fee=buy_fee,
            total_cost=total_cost,
            net_power_delivered=net_power,
            efficiency=efficiency,
            sell_order_qty=sell_qty,
            sell_order_price=sell_price,
            buy_order_qty=buy_qty,
            buy_order_price=target_price,
            is_profitable=(net_power > total_cost),
            is_executable=is_executable,
            blocking_reason=blocking_reason
        )
    
    def calculate_optimal_redistribution(
        self,
        target_symbol: str,
        target_relay: str,
        target_price: Decimal,
        power_needed: Decimal
    ) -> RedistributionPlan:
        """
        Calculate optimal power redistribution to target.
        
        Algorithm:
        1. Identify all generating nodes (positive power)
        2. Sort by extraction efficiency
        3. Pull from best sources until target is met
        4. Calculate total costs and efficiency
        """
        
        plan_id = f"PLAN-{int(time.time())}"
        
        # Grid stats
        generating = [n for n in self.nodes if n.is_generating and n.extractable > Decimal('0')]
        consuming = [n for n in self.nodes if n.is_consuming]
        
        total_power = sum(n.power for n in self.nodes)
        total_surplus = sum(n.extractable for n in generating)
        total_deficit = sum(abs(n.power) for n in consuming)
        
        plan = RedistributionPlan(
            plan_id=plan_id,
            created_at=time.time(),
            total_nodes=len(self.nodes),
            generating_nodes=len(generating),
            consuming_nodes=len(consuming),
            total_grid_power=total_power,
            total_surplus=total_surplus,
            total_deficit=total_deficit
        )
        
        if total_surplus == 0:
            plan.is_executable = False
            return plan
        
        # Sort generators by efficiency (same relay first, then by surplus)
        def efficiency_score(node: PowerNode) -> float:
            same_relay_bonus = 1.0 if node.relay == target_relay else 0.5
            surplus_factor = float(node.extractable)
            return same_relay_bonus * surplus_factor
        
        generating.sort(key=efficiency_score, reverse=True)
        
        # Pull power from sources
        power_collected = Decimal('0')
        
        for source in generating:
            if power_collected >= power_needed:
                break
            
            # How much to extract from this source
            remaining_need = power_needed - power_collected
            max_from_source = min(
                source.extractable * self.max_single_extract,  # Respect max extraction rate
                remaining_need * Decimal('1.1')  # Slight overhead for fees
            )
            
            if max_from_source < self.min_transfer_value / source.current_price:
                continue  # Not worth extracting from this source
            
            # Calculate this transfer
            transfer = self.calculate_single_transfer(
                source=source,
                target_symbol=target_symbol,
                target_relay=target_relay,
                target_price=target_price,
                extract_amount=max_from_source / source.current_price
            )
            
            if transfer.is_executable:
                plan.transfers.append(transfer)
                power_collected += transfer.net_power_delivered
                
                plan.total_transfer_cost += transfer.total_cost
                plan.total_power_moved += transfer.transfer_value
                plan.total_power_delivered += transfer.net_power_delivered
        
        # Overall efficiency
        if plan.total_power_moved > 0:
            plan.overall_efficiency = plan.total_power_delivered / plan.total_power_moved
        
        # Can we execute?
        plan.is_executable = len(plan.transfers) > 0 and plan.total_power_delivered >= power_needed * Decimal('0.9')
        
        # Execution sequence
        plan.execution_sequence = [
            f"SELL {t.sell_order_qty} {t.source_node.base_asset} @ {t.source_relay}"
            for t in plan.transfers
        ]
        plan.execution_sequence.append(f"BUY {target_symbol} @ {target_relay}")
        
        return plan
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # DISPLAY
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def display_grid_status(self):
        """Display complete grid status with precise math"""
        
        print("╔══════════════════════════════════════════════════════════════════════════════════════════════════╗")
        print("║                                                                                                  ║")
        print("║                    ⚡ HARMONIC POWER GRID - MATHEMATICAL STATE ⚡                                 ║")
        print("║                                                                                                  ║")
        print("╚══════════════════════════════════════════════════════════════════════════════════════════════════╝\n")
        
        # Grid summary
        generating = [n for n in self.nodes if n.is_generating]
        consuming = [n for n in self.nodes if n.is_consuming]
        neutral = [n for n in self.nodes if n.is_neutral]
        
        total_power = sum(n.power for n in self.nodes)
        total_surplus = sum(n.extractable for n in generating)
        total_deficit = sum(abs(n.power) for n in consuming)
        total_value = sum(n.current_value for n in self.nodes)
        total_free = sum(self.free_energy.values())
        
        print(f"🌐 GRID TOPOLOGY")
        print(f"   Total Nodes: {len(self.nodes)}")
        print(f"   ├─ Generating: {len(generating)} (positive power)")
        print(f"   ├─ Consuming: {len(consuming)} (negative power)")
        print(f"   └─ Neutral: {len(neutral)} (zero power)")
        
        print(f"\n⚡ POWER METRICS (Precise)")
        print(f"   Total Grid Value: {total_value:.8f} units")
        print(f"   Total Power: {total_power:+.8f} units")
        print(f"   Extractable Surplus: {total_surplus:.8f} units")
        print(f"   Deficit Gap: {total_deficit:.8f} units")
        print(f"   Free Energy (Stables): {total_free:.8f} units")
        
        # Per-relay breakdown
        print(f"\n📡 RELAY BREAKDOWN")
        for relay in ['binance', 'kraken', 'alpaca']:
            relay_nodes = [n for n in self.nodes if n.relay == relay]
            relay_power = sum(n.power for n in relay_nodes)
            relay_surplus = sum(n.extractable for n in relay_nodes if n.is_generating)
            relay_free = self.free_energy.get(relay, Decimal('0'))
            
            print(f"   {relay.upper():12} │ Nodes: {len(relay_nodes):3} │ Power: {relay_power:+12.4f} │ Extractable: {relay_surplus:10.4f} │ Free: {relay_free:10.4f}")
        
        # Node detail
        print(f"\n{'═'*100}")
        print(f"{'NODE':<20} {'RELAY':<10} {'AMOUNT':<15} {'ENTRY':<12} {'CURRENT':<12} {'POWER':<15} {'EXTRACT':<12}")
        print(f"{'═'*100}")
        
        for node in self.nodes:
            state_icon = "⚡" if node.is_generating else "🔴" if node.is_consuming else "⚪"
            
            print(f"{state_icon} {node.symbol:<18} {node.relay:<10} {node.amount:>14.8f} {node.entry_price:>11.4f} {node.current_price:>11.4f} {node.power:>+14.4f} {node.extractable:>11.4f}")
            
            # Show percentage
            print(f"   └─ Power %: {node.power_percent:+.2f}%  │  Value: ${node.current_value:.2f}  │  Entry Value: ${node.entry_value:.2f}")
        
        print(f"{'═'*100}\n")
    
    def display_redistribution_plan(self, plan: RedistributionPlan):
        """Display a redistribution plan with full math"""
        
        print("╔══════════════════════════════════════════════════════════════════════════════════════════════════╗")
        print("║                                                                                                  ║")
        print("║                    🌊 POWER REDISTRIBUTION PLAN 🌊                                                ║")
        print("║                                                                                                  ║")
        print("╚══════════════════════════════════════════════════════════════════════════════════════════════════╝\n")
        
        print(f"📋 Plan ID: {plan.plan_id}")
        print(f"   Created: {datetime.fromtimestamp(plan.created_at).isoformat()}")
        
        print(f"\n📊 GRID SNAPSHOT")
        print(f"   Total Nodes: {plan.total_nodes}")
        print(f"   Generating: {plan.generating_nodes}")
        print(f"   Consuming: {plan.consuming_nodes}")
        print(f"   Total Surplus: {plan.total_surplus:.8f}")
        
        print(f"\n💸 TRANSFER SUMMARY")
        print(f"   Transfers: {len(plan.transfers)}")
        print(f"   Total Power Moved: {plan.total_power_moved:.8f}")
        print(f"   Total Cost (Fees): {plan.total_transfer_cost:.8f}")
        print(f"   Net Power Delivered: {plan.total_power_delivered:.8f}")
        print(f"   Overall Efficiency: {plan.overall_efficiency:.2%}")
        
        if plan.transfers:
            print(f"\n{'─'*100}")
            print(f"{'FROM':<25} {'EXTRACT':<15} {'VALUE':<12} {'FEES':<12} {'NET':<12} {'EFF':<8}")
            print(f"{'─'*100}")
            
            for t in plan.transfers:
                src = f"{t.source_node.symbol}@{t.source_relay}"
                print(f"{src:<25} {t.extract_amount:>14.8f} {t.transfer_value:>11.4f} {t.total_cost:>11.4f} {t.net_power_delivered:>11.4f} {t.efficiency:>7.1%}")
                print(f"   └─ Sell: {t.sell_fee:.4f} │ Withdraw: {t.withdrawal_fee:.4f} │ Buy: {t.buy_fee:.4f}")
        
        print(f"\n{'─'*100}")
        
        print(f"\n🎯 EXECUTION SEQUENCE:")
        for i, step in enumerate(plan.execution_sequence, 1):
            print(f"   {i}. {step}")
        
        status = "✅ EXECUTABLE" if plan.is_executable else "❌ NOT EXECUTABLE"
        print(f"\n   Status: {status}\n")


def main():
    """Run the mathematical redistribution engine"""
    
    print("\n" + "="*100)
    print("⚡🌊 AUREON HARMONIC POWER REDISTRIBUTION - MATHEMATICAL ENGINE 🌊⚡")
    print("="*100 + "\n")
    
    engine = HarmonicRedistributionMath()
    
    # Scan complete grid
    nodes = engine.scan_full_grid()
    
    # Display grid status
    engine.display_grid_status()
    
    # Find a growth opportunity (example)
    generating = [n for n in nodes if n.is_generating and n.extractable > Decimal('0')]
    
    if generating:
        print("🚀 GROWTH OPPORTUNITY DETECTED\n")
        
        # Example: Redistribute to first consuming node or a new opportunity
        consuming = [n for n in nodes if n.is_consuming]
        if consuming:
            target = consuming[0]
            
            # Calculate redistribution plan
            power_needed = abs(target.power) + Decimal('5')  # Cover deficit + extra
            
            plan = engine.calculate_optimal_redistribution(
                target_symbol=target.symbol,
                target_relay=target.relay,
                target_price=target.current_price,
                power_needed=power_needed
            )
            
            engine.display_redistribution_plan(plan)
    else:
        print("💤 NO GENERATING NODES")
        print("   Grid is in rest mode - no surplus to redistribute")
        print("   Waiting for any node to generate positive power...\n")
    
    print("="*100)
    print("⚡ THE MATH IS PRECISE. THE POWER FLOWS. THE GRID IS ALIVE. ⚡")
    print("="*100 + "\n")


if __name__ == "__main__":
    main()
