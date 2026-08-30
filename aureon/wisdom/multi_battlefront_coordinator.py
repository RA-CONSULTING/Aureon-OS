#!/usr/bin/env python3
"""
☘️🌐 MULTI-BATTLEFRONT COORDINATOR 🌐☘️
═══════════════════════════════════════════════════════════════════════════════
                    UNITY IN DIVERSITY - ALL FRONTS AS ONE
═══════════════════════════════════════════════════════════════════════════════

"Níl neart go cur le chéile" - There is no strength without unity

THE CELTIC CONFEDERATION MODEL:
═══════════════════════════════════════════════════════════════════════════════

Ancient Celtic warriors operated in tribal confederations - independent tribes
that united for common cause. Each tribe fought their own battles but shared:
- Intelligence (scouts reporting to central command)
- Resources (warriors moving between fronts)
- Strategy (unified war council decisions)
- Victory (shared spoils of war)

In our financial warfare:
- Each EXCHANGE is a tribe/battlefront (Binance, Kraken, Alpaca, Capital.com)
- Each FLYING COLUMN operates independently but reports centrally
- INTELLIGENCE flows between all fronts
- CAPITAL can shift between exchanges as opportunities arise
- VICTORIES are aggregated for total campaign success

TACTICAL ADVANTAGES OF MULTI-FRONT:
═══════════════════════════════════════════════════════════════════════════════

1. DIVERSIFICATION OF RISK
   - Not dependent on single exchange
   - If one front stalls, others advance

2. ARBITRAGE OPPORTUNITIES
   - Price differences between exchanges
   - Faster execution on less congested exchange

3. 24/7 COVERAGE
   - Different exchanges, different markets
   - Stocks (Alpaca) + Crypto (Binance/Kraken) + CFD (Capital.com)

4. INTELLIGENCE MULTIPLICATION
   - Pattern on one exchange may precede pattern on another
   - Volume on Binance may signal move on Kraken

5. LIQUIDITY HUNTING
   - Find best liquidity for entry/exit
   - Avoid slippage by routing smartly

THE COMMANDER'S WAR ROOM:
═══════════════════════════════════════════════════════════════════════════════

This module implements the central war room that:
- Monitors all battlefronts simultaneously
- Allocates capital dynamically
- Routes trades to optimal exchanges
- Coordinates multi-front strikes
- Aggregates P&L across all operations
- Makes strategic retreat/advance decisions

Gary Leckey | December 2025
"United we stand, divided we fall - but united, we NEVER fall."
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import time
import json
import asyncio
import logging
import threading
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
from collections import defaultdict
from enum import Enum

# Import our warfare engines
from aureon.wisdom.guerrilla_warfare_engine import (
    get_guerrilla_commander,
    FlyingColumn,
    BattlefrontStatus,
    get_celtic_wisdom,
    GUERRILLA_CONFIG
)

from aureon.wisdom.celtic_preemptive_strike import (
    get_preemptive_controller,
    PreemptiveSignal,
    PreemptiveSignalType
)

# Import exchange clients
try:
    from aureon.exchanges.binance_client import BinanceClient
    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False
    BinanceClient = None

try:
    from aureon.exchanges.kraken_client import KrakenClient
    KRAKEN_AVAILABLE = True
except ImportError:
    KRAKEN_AVAILABLE = False
    KrakenClient = None

try:
    from aureon.exchanges.alpaca_client import AlpacaClient
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    AlpacaClient = None

try:
    from aureon.exchanges.capital_client import CapitalClient
    CAPITAL_AVAILABLE = True
except ImportError:
    CAPITAL_AVAILABLE = False
    CapitalClient = None

# Import penny profit engine
try:
    from aureon.trading.penny_profit_engine import get_penny_engine, check_penny_exit
    PENNY_AVAILABLE = True
except ImportError:
    PENNY_AVAILABLE = False


# Configure logging with fallback for Windows file locking
handlers = [logging.StreamHandler(sys.stdout)]
try:
    handlers.append(logging.FileHandler('multi_battlefront.log'))
except PermissionError:
    # If file is locked (common on Windows), try a unique name
    import os
    pid = os.getpid()
    handlers.append(logging.FileHandler(f'multi_battlefront_{pid}.log'))
except Exception as e:
    print(f"⚠️  Could not setup file logging: {e}")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=handlers
)
logger = logging.getLogger(__name__)


# =============================================================================
# 🏛️ WAR ROOM CONFIGURATION
# =============================================================================

class CampaignPhase(Enum):
    """Strategic campaign phases"""
    RECONNAISSANCE = "recon"           # Gathering intel only
    SKIRMISH = "skirmish"             # Light trading, testing
    OFFENSIVE = "offensive"            # Full attack mode
    DEFENSIVE = "defensive"            # Protect gains
    RETREAT = "retreat"                # Close positions, wait
    SIEGE = "siege"                    # Patient hold for victory


WAR_ROOM_CONFIG = {
    # ═══════════════════════════════════════════════════════════════════════
    # 🌐 BATTLEFRONT CONFIGURATION
    # ═══════════════════════════════════════════════════════════════════════
    'BATTLEFRONTS': {
        'binance': {
            'enabled': BINANCE_AVAILABLE,
            'priority': 1,              # Primary front
            'max_capital_pct': 0.40,    # Max 40% of total capital
            'fee_rate': 0.00075,        # 0.075% maker
            'min_trade': 10.0,          # Minimum $10 trade
            'quote_asset': 'USDC',      # Trading in USDC
        },
        'kraken': {
            'enabled': KRAKEN_AVAILABLE,
            'priority': 2,
            'max_capital_pct': 0.30,
            'fee_rate': 0.0026,         # 0.26% taker
            'min_trade': 10.0,
            'quote_asset': 'USD',
        },
        'alpaca': {
            'enabled': ALPACA_AVAILABLE,
            'priority': 3,
            'max_capital_pct': 0.20,
            'fee_rate': 0.0,            # Commission-free stocks
            'min_trade': 1.0,           # $1 minimum
            'quote_asset': 'USD',
        },
        'capital': {
            'enabled': CAPITAL_AVAILABLE,
            'priority': 4,
            'max_capital_pct': 0.10,
            'fee_rate': 0.0,            # Spread-based
            'min_trade': 20.0,
            'quote_asset': 'USD',
        },
    },
    
    # ═══════════════════════════════════════════════════════════════════════
    # ⚔️ STRATEGIC PARAMETERS
    # ═══════════════════════════════════════════════════════════════════════
    'INITIAL_PHASE': CampaignPhase.SKIRMISH,
    'MAX_TOTAL_EXPOSURE_PCT': 0.50,     # Max 50% of capital deployed
    'MIN_RESERVE_PCT': 0.20,            # Keep 20% as reserve
    'REBALANCE_THRESHOLD': 0.10,        # Rebalance if 10% off target
    
    # ═══════════════════════════════════════════════════════════════════════
    # 🎯 COORDINATION PARAMETERS
    # ═══════════════════════════════════════════════════════════════════════
    'COORDINATED_STRIKE_MIN_FRONTS': 2, # Min 2 fronts for coord strike
    'ARBITRAGE_MIN_SPREAD': 0.002,      # 0.2% min spread for arb
    'INTEL_SHARE_DELAY_SEC': 0.5,       # Share intel with delay
    
    # ═══════════════════════════════════════════════════════════════════════
    # 🏃 RETREAT PARAMETERS
    # ═══════════════════════════════════════════════════════════════════════
    'RETREAT_ON_DAILY_LOSS': 0.0,       # 0% - we don't lose
    'RETREAT_ON_DRAWDOWN': 0.05,        # 5% drawdown triggers retreat
    'RETREAT_DURATION_SEC': 300,        # 5 minute retreat
    
    # ═══════════════════════════════════════════════════════════════════════
    # 📊 REPORTING
    # ═══════════════════════════════════════════════════════════════════════
    'STATUS_UPDATE_INTERVAL_SEC': 30,   # Status update every 30 sec
    'DETAILED_LOGGING': True,
    'SAVE_STATE_INTERVAL_SEC': 60,      # Save state every minute
}


# =============================================================================
# 📊 DATA STRUCTURES
# =============================================================================

@dataclass
class ExchangePosition:
    """Position on a specific exchange"""
    exchange: str
    symbol: str
    column_id: str
    entry_price: float
    entry_time: float
    quantity: float
    entry_value: float
    current_price: float = 0.0
    current_value: float = 0.0
    unrealized_pnl: float = 0.0
    

@dataclass
class CampaignStats:
    """Overall campaign statistics"""
    start_time: float = field(default_factory=time.time)
    total_capital: float = 0.0
    deployed_capital: float = 0.0
    reserve_capital: float = 0.0
    
    # P&L tracking
    total_realized_pnl: float = 0.0
    total_unrealized_pnl: float = 0.0
    
    # Kill tracking
    total_kills: int = 0
    kills_by_front: Dict[str, int] = field(default_factory=dict)
    
    # Strategic metrics
    current_phase: CampaignPhase = CampaignPhase.RECONNAISSANCE
    fronts_active: int = 0
    positions_open: int = 0
    

@dataclass
class ArbitrageOpportunity:
    """Cross-exchange arbitrage opportunity"""
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    spread_pct: float
    potential_profit: float
    detected_at: float = field(default_factory=time.time)


# =============================================================================
# 🌐 THE WAR ROOM - CENTRAL COMMAND
# =============================================================================

class MultiBattlefrontWarRoom:
    """
    Central command for all battlefront operations.
    
    "From this room, we command all fronts.
    Every column reports here. Every decision flows from here.
    Unity of command - unity of purpose - unity of victory."
    """
    
    def __init__(self, total_capital: float = 10000.0):
        self.config = WAR_ROOM_CONFIG
        
        # Core components
        self.commander = get_guerrilla_commander()
        self.preemptive = get_preemptive_controller()
        
        # Capital management
        self.total_capital = total_capital
        self.reserve_capital = total_capital * self.config['MIN_RESERVE_PCT']
        self.available_capital = total_capital - self.reserve_capital
        
        # Exchange clients (initialized lazily)
        self.clients: Dict[str, Any] = {}
        
        # Position tracking
        self.positions: Dict[str, ExchangePosition] = {}  # column_id -> position
        
        # Statistics
        self.stats = CampaignStats(
            total_capital=total_capital,
            reserve_capital=self.reserve_capital
        )
        
        # Arbitrage tracking
        self.arb_opportunities: List[ArbitrageOpportunity] = []
        
        # Price cache for cross-exchange comparison
        self.price_cache: Dict[str, Dict[str, float]] = defaultdict(dict)  # exchange -> symbol -> price
        
        # State
        self._running = False
        self._retreat_until = 0
        self._last_save = 0
        
        # Initialize battlefronts
        self._init_battlefronts()
        
        logger.info(f"""
☘️🌐═══════════════════════════════════════════════════════════════════════🌐☘️
                    MULTI-BATTLEFRONT WAR ROOM INITIALIZED
☘️🌐═══════════════════════════════════════════════════════════════════════🌐☘️

   💰 Total Capital: ${total_capital:.2f}
   💎 Reserve: ${self.reserve_capital:.2f}
   ⚔️ Available for Deployment: ${self.available_capital:.2f}
   
   🌐 Battlefronts Configured: {len([f for f, c in self.config['BATTLEFRONTS'].items() if c['enabled']])}
""")
    
    def _init_battlefronts(self):
        """Initialize all enabled battlefronts"""
        for front_name, front_config in self.config['BATTLEFRONTS'].items():
            if front_config['enabled']:
                # Register with guerrilla commander
                max_capital = self.total_capital * front_config['max_capital_pct']
                self.commander.register_battlefront(front_name, max_capital)
                logger.info(f"   ✅ {front_name.upper()}: Max ${max_capital:.2f}")
    
    def connect_exchange(self, exchange: str, client: Any):
        """Connect an exchange client"""
        self.clients[exchange] = client
        logger.info(f"🌐 Connected to {exchange}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # 📡 INTELLIGENCE OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════
    
    def update_price(self, exchange: str, symbol: str, price: float, 
                    volume: float = 0):
        """Update price from exchange - feeds into all intelligence systems"""
        # Update guerrilla intelligence
        self.commander.update_intelligence(exchange, symbol, price, volume)
        
        # Update preemptive system
        self.preemptive.update(exchange, symbol, price, volume)
        
        # Cache for arbitrage detection
        self.price_cache[exchange][symbol] = price
        
        # Check for arbitrage
        self._check_arbitrage(symbol, exchange, price)
        
        # Update positions
        self._update_position_prices(exchange, symbol, price)
    
    def _check_arbitrage(self, symbol: str, source_exchange: str, price: float):
        """Check for cross-exchange arbitrage opportunities"""
        min_spread = self.config['ARBITRAGE_MIN_SPREAD']
        
        for other_exchange, prices in self.price_cache.items():
            if other_exchange == source_exchange:
                continue
            
            other_price = prices.get(symbol)
            if not other_price:
                continue
            
            # Calculate spread
            if price > other_price:
                spread = (price - other_price) / other_price
                buy_ex, sell_ex = other_exchange, source_exchange
                buy_price, sell_price = other_price, price
            else:
                spread = (other_price - price) / price
                buy_ex, sell_ex = source_exchange, other_exchange
                buy_price, sell_price = price, other_price
            
            if spread >= min_spread:
                # Factor in fees
                buy_fee = self.config['BATTLEFRONTS'].get(buy_ex, {}).get('fee_rate', 0.001)
                sell_fee = self.config['BATTLEFRONTS'].get(sell_ex, {}).get('fee_rate', 0.001)
                net_spread = spread - buy_fee - sell_fee
                
                if net_spread > 0:
                    potential_profit = GUERRILLA_CONFIG['COLUMN_SIZE_USD'] * net_spread
                    
                    arb = ArbitrageOpportunity(
                        symbol=symbol,
                        buy_exchange=buy_ex,
                        sell_exchange=sell_ex,
                        buy_price=buy_price,
                        sell_price=sell_price,
                        spread_pct=spread * 100,
                        potential_profit=potential_profit
                    )
                    
                    self.arb_opportunities.append(arb)
                    
                    logger.info(f"""
⚡ ARBITRAGE DETECTED ⚡
   Symbol: {symbol}
   Buy: {buy_ex} @ ${buy_price:.6f}
   Sell: {sell_ex} @ ${sell_price:.6f}
   Spread: {spread*100:.3f}%
   Potential: ${potential_profit:.4f}
""")
    
    def _update_position_prices(self, exchange: str, symbol: str, price: float):
        """Update current prices for open positions"""
        for column_id, position in self.positions.items():
            if position.exchange == exchange and position.symbol == symbol:
                position.current_price = price
                position.current_value = position.quantity * price
                position.unrealized_pnl = position.current_value - position.entry_value
    
    # ═══════════════════════════════════════════════════════════════════════
    # ⚔️ COMBAT OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════
    
    def deploy_column(self, exchange: str, symbol: str, 
                     price: float = None) -> Optional[FlyingColumn]:
        """
        Deploy a flying column on a specific exchange.
        
        This is the main entry point for opening a position.
        """
        # Check strategic restrictions
        if self.stats.current_phase == CampaignPhase.RETREAT:
            logger.warning(f"☘️ Cannot deploy - in RETREAT phase")
            return None
        
        if self.stats.current_phase == CampaignPhase.RECONNAISSANCE:
            logger.warning(f"☘️ Cannot deploy - in RECONNAISSANCE phase")
            return None
        
        # Check capital
        column_size = GUERRILLA_CONFIG['COLUMN_SIZE_USD']
        if self.available_capital < column_size:
            logger.warning(f"☘️ Insufficient capital for deployment")
            return None
        
        # Get current price if not provided
        if price is None:
            price = self.price_cache.get(exchange, {}).get(symbol)
            if not price:
                logger.warning(f"☘️ No price available for {exchange}:{symbol}")
                return None
        
        # Deploy through guerrilla commander
        column = self.commander.deploy_column(exchange, symbol, price, column_size)
        
        if column:
            # Track position
            quantity = column_size / price
            position = ExchangePosition(
                exchange=exchange,
                symbol=symbol,
                column_id=column.column_id,
                entry_price=price,
                entry_time=time.time(),
                quantity=quantity,
                entry_value=column_size,
                current_price=price,
                current_value=column_size
            )
            self.positions[column.column_id] = position
            
            # Update capital tracking
            self.available_capital -= column_size
            self.stats.deployed_capital += column_size
            self.stats.positions_open += 1
            
            # Register with preemptive system
            intel = self.commander.intelligence.get_intel(exchange, symbol)
            momentum = intel.price_momentum_1m if intel else 0
            self.preemptive.register_position_entry(exchange, symbol, momentum)
        
        return column
    
    def check_all_exits(self) -> List[Dict]:
        """
        Check all positions for exit conditions.
        
        Returns list of positions that should exit.
        """
        exits = []
        
        for column_id, position in list(self.positions.items()):
            # Get column from commander
            column = self.commander.columns.get(column_id)
            if not column or column.status not in ("active", "siege"):
                continue
            
            current_price = position.current_price
            if not current_price:
                continue
            
            # Check guerrilla exit (penny profit)
            should_exit, reason, net_pnl = self.commander.check_column_exit(
                column_id, current_price
            )
            
            # Check preemptive exit
            if not should_exit:
                intel = self.commander.intelligence.get_intel(position.exchange, position.symbol)
                momentum = intel.price_momentum_1m if intel else None
                
                preempt_exit, preempt_reason, confidence = self.preemptive.check_preemptive_exit(
                    position.exchange,
                    position.symbol,
                    position.entry_price,
                    current_price,
                    momentum
                )
                
                if preempt_exit and net_pnl > 0:
                    should_exit = True
                    reason = preempt_reason
            
            if should_exit:
                exits.append({
                    'column_id': column_id,
                    'position': position,
                    'reason': reason,
                    'net_pnl': net_pnl,
                    'exit_price': current_price
                })
        
        return exits
    
    def execute_exit(self, column_id: str, exit_price: float, 
                    net_pnl: float, reason: str) -> bool:
        """Execute an exit for a column"""
        position = self.positions.get(column_id)
        if not position:
            return False
        
        # Complete the kill in guerrilla commander
        self.commander.complete_column_kill(column_id, exit_price, net_pnl, reason)
        
        # Update capital
        self.available_capital += position.entry_value + net_pnl
        self.stats.deployed_capital -= position.entry_value
        self.stats.total_realized_pnl += net_pnl
        self.stats.positions_open -= 1
        
        if net_pnl > 0:
            self.stats.total_kills += 1
            if position.exchange not in self.stats.kills_by_front:
                self.stats.kills_by_front[position.exchange] = 0
            self.stats.kills_by_front[position.exchange] += 1
        
        # Clear from tracking
        del self.positions[column_id]
        self.preemptive.clear_position(position.exchange, position.symbol)
        
        return True
    
    # ═══════════════════════════════════════════════════════════════════════
    # 🎖️ STRATEGIC OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════
    
    def set_phase(self, phase: CampaignPhase):
        """Set the current campaign phase"""
        old_phase = self.stats.current_phase
        self.stats.current_phase = phase
        
        logger.info(f"""
☘️🎖️ CAMPAIGN PHASE CHANGE 🎖️☘️
   From: {old_phase.value.upper()}
   To: {phase.value.upper()}
""")
        
        if phase == CampaignPhase.RETREAT:
            self._retreat_until = time.time() + self.config['RETREAT_DURATION_SEC']
    
    def initiate_retreat(self, reason: str = "Strategic retreat"):
        """Initiate strategic retreat - close profitable positions"""
        self.set_phase(CampaignPhase.RETREAT)
        self.commander.initiate_retreat(reason)
        
        # Close all profitable positions
        exits = self.check_all_exits()
        profitable_exits = [e for e in exits if e['net_pnl'] > 0]
        
        for exit_info in profitable_exits:
            self.execute_exit(
                exit_info['column_id'],
                exit_info['exit_price'],
                exit_info['net_pnl'],
                f"🏃 RETREAT: {exit_info['reason']}"
            )
    
    def scan_opportunities(self) -> List[Dict]:
        """Scan all fronts for trading opportunities"""
        opportunities = []
        
        for exchange in self.config['BATTLEFRONTS']:
            if not self.config['BATTLEFRONTS'][exchange]['enabled']:
                continue
            
            # Get best targets from guerrilla commander
            targets = self.commander.intelligence.get_best_targets(
                exchange=exchange,
                min_score=GUERRILLA_CONFIG['MIN_AMBUSH_SCORE']
            )
            
            for target in targets[:3]:  # Top 3 per exchange
                # Check preemptive signals
                signals = self.preemptive.scan_all(
                    target.exchange, 
                    target.symbol,
                    target.current_price
                )
                
                buy_signals = [s for s in signals if s.action == "BUY"]
                
                opportunities.append({
                    'exchange': exchange,
                    'symbol': target.symbol,
                    'ambush_score': target.ambush_score,
                    'quick_kill_prob': target.quick_kill_probability,
                    'price': target.current_price,
                    'preemptive_signals': len(buy_signals),
                    'consensus': len(buy_signals) >= 2
                })
        
        # Sort by combined score
        opportunities.sort(
            key=lambda x: x['ambush_score'] * (1 + x['preemptive_signals'] * 0.2),
            reverse=True
        )
        
        return opportunities
    
    def execute_coordinated_strike(self, opportunities: List[Dict]) -> int:
        """Execute a coordinated strike across multiple fronts"""
        min_fronts = self.config['COORDINATED_STRIKE_MIN_FRONTS']
        
        # Group by exchange
        by_exchange = defaultdict(list)
        for opp in opportunities:
            by_exchange[opp['exchange']].append(opp)
        
        if len(by_exchange) < min_fronts:
            logger.info(f"☘️ Not enough fronts for coordinated strike ({len(by_exchange)}/{min_fronts})")
            return 0
        
        deployed = 0
        
        logger.info(f"""
☘️🔥═══════════════════════════════════════════════════════════════════════🔥☘️
                    COORDINATED MULTI-FRONT STRIKE
                    Fronts: {len(by_exchange)}
☘️🔥═══════════════════════════════════════════════════════════════════════🔥☘️
""")
        
        # Deploy on each front
        for exchange, opps in by_exchange.items():
            best = opps[0]  # Take best opportunity per exchange
            
            column = self.deploy_column(exchange, best['symbol'], best['price'])
            if column:
                deployed += 1
                logger.info(f"   ✅ {exchange}:{best['symbol']} - DEPLOYED (score: {best['ambush_score']:.2f})")
        
        logger.info(f"""
   ⚔️ STRIKE COMPLETE: {deployed}/{len(by_exchange)} fronts engaged
☘️🔥═══════════════════════════════════════════════════════════════════════🔥☘️
""")
        
        return deployed
    
    # ═══════════════════════════════════════════════════════════════════════
    # 📊 REPORTING
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_campaign_status(self) -> str:
        """Get comprehensive campaign status"""
        # Calculate unrealized P&L
        total_unrealized = sum(p.unrealized_pnl for p in self.positions.values())
        self.stats.total_unrealized_pnl = total_unrealized
        
        # Count active fronts
        active_fronts = set(p.exchange for p in self.positions.values())
        self.stats.fronts_active = len(active_fronts)
        
        status = f"""
☘️🌐═══════════════════════════════════════════════════════════════════════🌐☘️
                    MULTI-BATTLEFRONT CAMPAIGN STATUS
☘️🌐═══════════════════════════════════════════════════════════════════════🌐☘️

🎖️ CAMPAIGN PHASE: {self.stats.current_phase.value.upper()}
⏱️ Runtime: {(time.time() - self.stats.start_time) / 60:.1f} minutes

💰 CAPITAL STATUS:
   Total Capital: ${self.total_capital:.2f}
   Reserve: ${self.reserve_capital:.2f}
   Available: ${self.available_capital:.2f}
   Deployed: ${self.stats.deployed_capital:.2f}

📈 P&L STATUS:
   Realized P&L: ${self.stats.total_realized_pnl:.4f}
   Unrealized P&L: ${total_unrealized:.4f}
   Total P&L: ${self.stats.total_realized_pnl + total_unrealized:.4f}

⚔️ COMBAT STATUS:
   Active Fronts: {self.stats.fronts_active}
   Open Positions: {self.stats.positions_open}
   Total Kills: {self.stats.total_kills}

🌐 KILLS BY FRONT:
"""
        for front, kills in self.stats.kills_by_front.items():
            status += f"   {front.upper()}: {kills} kills\n"

        if not self.stats.kills_by_front:
            status += "   No kills yet - preparing for battle\n"

        status += f"""
📍 OPEN POSITIONS:
"""
        for col_id, pos in self.positions.items():
            pnl_emoji = "📈" if pos.unrealized_pnl > 0 else "📉"
            status += f"   {pnl_emoji} {col_id}: {pos.exchange}:{pos.symbol} | "
            status += f"Entry: ${pos.entry_price:.4f} | "
            status += f"Current: ${pos.current_price:.4f} | "
            status += f"P&L: ${pos.unrealized_pnl:.4f}\n"

        if not self.positions:
            status += "   No open positions - awaiting opportunity\n"

        status += f"""
⚡ ARBITRAGE OPPORTUNITIES: {len(self.arb_opportunities)}

☘️🌐═══════════════════════════════════════════════════════════════════════🌐☘️
                    "{get_celtic_wisdom()}"
☘️🌐═══════════════════════════════════════════════════════════════════════🌐☘️
"""
        return status
    
    def save_state(self):
        """Save war room state to disk"""
        state = {
            'timestamp': time.time(),
            'total_capital': self.total_capital,
            'available_capital': self.available_capital,
            'stats': {
                'total_realized_pnl': self.stats.total_realized_pnl,
                'total_kills': self.stats.total_kills,
                'kills_by_front': self.stats.kills_by_front,
                'current_phase': self.stats.current_phase.value,
            },
            'positions': {
                col_id: {
                    'exchange': pos.exchange,
                    'symbol': pos.symbol,
                    'entry_price': pos.entry_price,
                    'entry_time': pos.entry_time,
                    'quantity': pos.quantity,
                    'entry_value': pos.entry_value,
                }
                for col_id, pos in self.positions.items()
            }
        }
        
        try:
            with open('war_room_state.json', 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"☘️ Could not save state: {e}")
    
    def load_state(self):
        """Load war room state from disk"""
        try:
            if os.path.exists('war_room_state.json'):
                with open('war_room_state.json', 'r') as f:
                    state = json.load(f)
                    
                    self.stats.total_realized_pnl = state.get('stats', {}).get('total_realized_pnl', 0)
                    self.stats.total_kills = state.get('stats', {}).get('total_kills', 0)
                    self.stats.kills_by_front = state.get('stats', {}).get('kills_by_front', {})
                    
                    logger.info(f"☘️ Loaded war room state: {self.stats.total_kills} total kills")
        except Exception as e:
            logger.warning(f"☘️ Fresh war room state: {e}")


# =============================================================================
# 🌍 GLOBAL WAR ROOM INSTANCE
# =============================================================================

_WAR_ROOM: Optional[MultiBattlefrontWarRoom] = None


def get_war_room(total_capital: float = 10000.0) -> MultiBattlefrontWarRoom:
    """Get the global war room instance"""
    global _WAR_ROOM
    if _WAR_ROOM is None:
        _WAR_ROOM = MultiBattlefrontWarRoom(total_capital)
    return _WAR_ROOM


# =============================================================================
