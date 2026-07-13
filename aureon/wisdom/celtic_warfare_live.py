#!/usr/bin/env python3
"""
☘️🔥 AUREON CELTIC WARFARE LIVE TRADER 🔥☘️
═══════════════════════════════════════════════════════════════════════════════
                    HIT-AND-RUN TACTICS DEPLOYED TO LIVE MARKETS
═══════════════════════════════════════════════════════════════════════════════

This is the LIVE integration that combines:
1. ☘️ Guerrilla Warfare Engine - Flying columns, hit-and-run tactics
2. ⚡ Celtic Preemptive Strike - Move before the market reacts  
3. 🌐 Multi-Battlefront Coordinator - Unified command across exchanges
4. 🎯 IRA Sniper Mode - Zero loss, confirmed kills only
5. ⚔️ War Strategy - Quick kill probability assessment
6. 🪙 Penny Profit Engine - Exact math for minimum profit

THE DOCTRINE:
═══════════════════════════════════════════════════════════════════════════════
"Our portfolio energy is Irish - relentless, united, unconquerable.
Our enemy is the global financial ecosystem.
Our battlefronts are our exchanges.
Our weapon is cash and crypto.
Our goal: NEVER take a net loss. Every engagement is a victory."

OPERATIONAL MODES:
═══════════════════════════════════════════════════════════════════════════════
1. RECONNAISSANCE - Gather intel, no trading
2. SKIRMISH - Light trading, test signals
3. OFFENSIVE - Full attack, maximum columns
4. DEFENSIVE - Protect gains, close winners
5. SIEGE - Patient hold for victory

Gary Leckey | December 2025
"Tiocfaidh ár lá" - Our day will come
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import time
import json
import signal
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Optional

# Celtic warfare systems
from aureon.wisdom.guerrilla_warfare_engine import (
    get_guerrilla_commander,
    FlyingColumn,
    get_celtic_wisdom,
    GUERRILLA_CONFIG
)

from aureon.wisdom.celtic_preemptive_strike import (
    get_preemptive_controller,
    PreemptiveSignal
)

from aureon.wisdom.multi_battlefront_coordinator import (
    get_war_room,
    MultiBattlefrontWarRoom,
    CampaignPhase
)

# Existing Aureon systems
try:
    from aureon.exchanges.binance_client import BinanceClient, get_binance_client
    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False

try:
    from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
    KRAKEN_AVAILABLE = True
except ImportError:
    KRAKEN_AVAILABLE = False

try:
    from aureon.scanners.ira_sniper_mode import get_sniper_config, SNIPER_CONFIG
    SNIPER_AVAILABLE = True
except ImportError:
    SNIPER_AVAILABLE = False

try:
    from aureon.trading.penny_profit_engine import get_penny_engine, check_penny_exit
    PENNY_AVAILABLE = True
except ImportError:
    PENNY_AVAILABLE = False

try:
    from aureon.command_centers.war_strategy import get_quick_kill_estimate, should_attack as war_should_attack
    WAR_STRATEGY_AVAILABLE = True
except ImportError:
    WAR_STRATEGY_AVAILABLE = False

try:
    from aureon.trading.unified_sniper_brain import get_unified_brain, get_entry_signal, check_exit_signal
    UNIFIED_BRAIN_AVAILABLE = True
except ImportError:
    UNIFIED_BRAIN_AVAILABLE = False


# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('celtic_warfare_live.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# =============================================================================
# 🏛️ CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    # Trading mode
    'DRY_RUN': True,                      # Set False for real trading
    'INITIAL_CAPITAL': 1000.0,            # Starting capital
    
    # Exchange selection  
    'USE_BINANCE': BINANCE_AVAILABLE,
    'USE_KRAKEN': KRAKEN_AVAILABLE,
    
    # Position sizing
    'COLUMN_SIZE': 10.0,                  # $10 per flying column
    'MAX_COLUMNS': 5,                     # Max simultaneous columns
    
    # Cycle timing
    'SCAN_INTERVAL_SEC': 2.0,             # Scan every 2 seconds
    'EXIT_CHECK_INTERVAL_SEC': 1.0,       # Check exits every 1 second
    
    # Campaign settings
    'INITIAL_PHASE': 'skirmish',          # Start in skirmish mode
    
    # Symbols to trade (crypto pairs)
    'BINANCE_SYMBOLS': [
        'BTCUSDC', 'ETHUSDC', 'SOLUSDC', 'AVAXUSDC', 'ADAUSDC',
        'DOTUSDC', 'LINKUSDC', 'MATICUSDC', 'UNIUSDC', 'ATOMUSDC'
    ],
    'KRAKEN_SYMBOLS': [
        'XXBTZUSD', 'XETHZUSD', 'SOLUSD', 'AVAXUSD', 'ADAUSD',
        'DOTUSD', 'LINKUSD', 'MATICUSD', 'UNIUSD', 'ATOMUSD'
    ],
}


# =============================================================================
# ☘️ CELTIC WARFARE LIVE TRADER
# =============================================================================

class CelticWarfareLiveTrader:
    """
    The unified live trader that implements Celtic hit-and-run warfare tactics.
    
    Coordinates:
    - Multi-exchange operations
    - Flying column deployment
    - Preemptive entry/exit
    - Penny profit targeting
    - Zero loss enforcement
    """
    
    def __init__(self, dry_run: bool = False, capital: float = 1000.0):
        self.dry_run = dry_run
        self.initial_capital = capital
        
        # Initialize war room
        self.war_room = get_war_room(capital)
        self.commander = get_guerrilla_commander()
        self.preemptive = get_preemptive_controller()
        
        # Exchange clients
        self.binance_client: Optional[BinanceClient] = None
        self.kraken_client: Optional[KrakenClient] = None
        
        # State
        self._running = False
        self._shutdown_requested = False
        
        # Counters
        self.scan_count = 0
        self.trade_count = 0
        
        # Price cache
        self.last_prices: Dict[str, Dict[str, float]] = {}
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info(f"""
☘️🔥═══════════════════════════════════════════════════════════════════════🔥☘️
                    CELTIC WARFARE LIVE TRADER INITIALIZED
☘️🔥═══════════════════════════════════════════════════════════════════════🔥☘️

   Mode: {'🔧 DRY RUN' if dry_run else '💰 LIVE TRADING'}
   Capital: ${capital:.2f}
   
   Exchanges:
     Binance: {'✅' if BINANCE_AVAILABLE else '❌'}
     Kraken: {'✅' if KRAKEN_AVAILABLE else '❌'}
   
   Systems:
     Sniper Mode: {'✅' if SNIPER_AVAILABLE else '❌'}
     Penny Engine: {'✅' if PENNY_AVAILABLE else '❌'}
     War Strategy: {'✅' if WAR_STRATEGY_AVAILABLE else '❌'}
     Unified Brain: {'✅' if UNIFIED_BRAIN_AVAILABLE else '❌'}
   
   ☘️ "{get_celtic_wisdom()}"
☘️🔥═══════════════════════════════════════════════════════════════════════🔥☘️
""")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("\n☘️ Shutdown signal received - initiating tactical retreat...")
        self._shutdown_requested = True
    
    def connect_exchanges(self) -> bool:
        """Connect to enabled exchanges"""
        success = True
        
        if LIVE_CONFIG['USE_BINANCE'] and BINANCE_AVAILABLE:
            try:
                self.binance_client = get_binance_client()
                self.war_room.connect_exchange('binance', self.binance_client)
                logger.info("✅ Connected to Binance")
            except Exception as e:
                logger.error(f"❌ Failed to connect to Binance: {e}")
                success = False
        
        if LIVE_CONFIG['USE_KRAKEN'] and KRAKEN_AVAILABLE:
            try:
                self.kraken_client = get_kraken_client()
                self.war_room.connect_exchange('kraken', self.kraken_client)
                logger.info("✅ Connected to Kraken")
            except Exception as e:
                logger.error(f"❌ Failed to connect to Kraken: {e}")
                success = False
        
        return success
    
    def fetch_prices(self) -> Dict[str, Dict[str, float]]:
        """Fetch current prices from all connected exchanges"""
        prices = {}
        
        # Binance prices
        if self.binance_client:
            try:
                prices['binance'] = {}
                for symbol in LIVE_CONFIG['BINANCE_SYMBOLS']:
                    ticker = self.binance_client.get_ticker(symbol)
                    if ticker and 'price' in ticker:
                        price = float(ticker['price'])
                        prices['binance'][symbol] = price
                        
                        # Update war room intelligence
                        self.war_room.update_price('binance', symbol, price)
            except Exception as e:
                logger.warning(f"Binance price fetch error: {e}")
        
        # Kraken prices
        if self.kraken_client:
            try:
                prices['kraken'] = {}
                for symbol in LIVE_CONFIG['KRAKEN_SYMBOLS']:
                    ticker = self.kraken_client.get_ticker(symbol)
                    if ticker:
                        price = float(ticker.get('c', [0])[0]) if isinstance(ticker.get('c'), list) else float(ticker.get('last', 0))
                        if price > 0:
                            prices['kraken'][symbol] = price
                            
                            # Update war room intelligence
                            self.war_room.update_price('kraken', symbol, price)
            except Exception as e:
                logger.warning(f"Kraken price fetch error: {e}")
        
        self.last_prices = prices
        return prices
    
    def scan_and_deploy(self):
        """Scan for opportunities and deploy flying columns"""
        self.scan_count += 1
        
        # Get opportunities from war room
        opportunities = self.war_room.scan_opportunities()
        
        if not opportunities:
            return 0
        
        deployed = 0
        
        for opp in opportunities[:3]:  # Top 3 opportunities
            # Check if we can deploy
            if self.war_room.stats.positions_open >= LIVE_CONFIG['MAX_COLUMNS']:
                break
            
            exchange = opp['exchange']
            symbol = opp['symbol']
            price = opp['price']
            
            # Verify with war strategy if available
            if WAR_STRATEGY_AVAILABLE:
                go_signal, reason, priority = war_should_attack(symbol, exchange)
                if not go_signal:
                    logger.debug(f"War strategy rejected {symbol}: {reason}")
                    continue
            
            # Check preemptive consensus
            if opp.get('consensus'):
                # Strong signal - deploy immediately
                logger.info(f"⚡ CONSENSUS SIGNAL: {exchange}:{symbol}")
            
            # Deploy column
            if self.dry_run:
                # Simulate deployment
                column = self.commander.deploy_column(exchange, symbol, price)
                if column:
                    deployed += 1
                    self.trade_count += 1
                    logger.info(f"☘️ [DRY RUN] Deployed column {column.column_id} on {exchange}:{symbol}")
            else:
                # Live trading
                column = self.war_room.deploy_column(exchange, symbol, price)
                if column:
                    deployed += 1
                    self.trade_count += 1
        
        return deployed
    
    def check_and_exit(self):
        """Check all positions for exit conditions"""
        exits = self.war_room.check_all_exits()
        
        for exit_info in exits:
            column_id = exit_info['column_id']
            exit_price = exit_info['exit_price']
            net_pnl = exit_info['net_pnl']
            reason = exit_info['reason']
            
            if self.dry_run:
                # Simulate exit
                self.commander.complete_column_kill(column_id, exit_price, net_pnl, reason)
                logger.info(f"☘️ [DRY RUN] Exit {column_id}: {reason} (P&L: ${net_pnl:.4f})")
            else:
                # Live exit
                self.war_room.execute_exit(column_id, exit_price, net_pnl, reason)
    
    def run_cycle(self):
        """Run one trading cycle"""
        # Fetch latest prices
        self.fetch_prices()
        
        # Check exits first (protect gains)
        self.check_and_exit()
        
        # Then scan for new entries
        if self.war_room.stats.current_phase in (CampaignPhase.SKIRMISH, CampaignPhase.OFFENSIVE):
            self.scan_and_deploy()
    
    def run(self, duration_minutes: int = 60):
        """
        Run the Celtic warfare trading session.
        
        Args:
            duration_minutes: How long to run (0 = indefinite)
        """
        self._running = True
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60) if duration_minutes > 0 else float('inf')
        
        # Connect exchanges
        if not self.connect_exchanges():
            logger.error("☘️ Failed to connect to exchanges - aborting")
            return
        
        # Set initial phase
        phase_map = {
            'recon': CampaignPhase.RECONNAISSANCE,
            'skirmish': CampaignPhase.SKIRMISH,
            'offensive': CampaignPhase.OFFENSIVE,
            'defensive': CampaignPhase.DEFENSIVE,
        }
        self.war_room.set_phase(phase_map.get(LIVE_CONFIG['INITIAL_PHASE'], CampaignPhase.SKIRMISH))
        
        logger.info(f"""
☘️⚔️═══════════════════════════════════════════════════════════════════════⚔️☘️
                    CELTIC WARFARE SESSION STARTED
                    Duration: {'Indefinite' if duration_minutes == 0 else f'{duration_minutes} minutes'}
☘️⚔️═══════════════════════════════════════════════════════════════════════⚔️☘️
""")
        
        cycle_count = 0
        last_status_time = 0
        
        try:
            while self._running and time.time() < end_time:
                if self._shutdown_requested:
                    break
                
                cycle_start = time.time()
                cycle_count += 1
                
                # Run trading cycle
                self.run_cycle()
                
                # Periodic status update
                if time.time() - last_status_time >= 60:  # Every minute
                    logger.info(self.war_room.get_campaign_status())
                    last_status_time = time.time()
                
                # Sleep until next cycle
                cycle_duration = time.time() - cycle_start
                sleep_time = max(0, LIVE_CONFIG['SCAN_INTERVAL_SEC'] - cycle_duration)
                if sleep_time > 0:
                    time.sleep(sleep_time)
        
        except KeyboardInterrupt:
            logger.info("\n☘️ Keyboard interrupt received")
        
        except Exception as e:
            logger.error(f"☘️ Error in main loop: {e}", exc_info=True)
        
        finally:
            self._running = False
            self._shutdown()
    
    def _shutdown(self):
        """Clean shutdown - close all positions profitably if possible"""
        logger.info("""
☘️🏃═══════════════════════════════════════════════════════════════════════🏃☘️
                    INITIATING TACTICAL RETREAT
☘️🏃═══════════════════════════════════════════════════════════════════════🏃☘️
""")
        
        # Set retreat phase
        self.war_room.set_phase(CampaignPhase.RETREAT)
        
        # Try to close profitable positions
        self.check_and_exit()
        
        # Final status
        logger.info(self.war_room.get_campaign_status())
        
        # Save state
        self.war_room.save_state()
        
        # Final report
        runtime = (time.time() - self.war_room.stats.start_time) / 60
        
        logger.info(f"""
☘️═══════════════════════════════════════════════════════════════════════════════☘️
                    CELTIC WARFARE SESSION COMPLETE
☘️═══════════════════════════════════════════════════════════════════════════════☘️

   ⏱️ Runtime: {runtime:.1f} minutes
   📊 Scans: {self.scan_count}
   🎯 Trades: {self.trade_count}
   💰 Total Kills: {self.war_room.stats.total_kills}
   📈 Total P&L: ${self.war_room.stats.total_realized_pnl:.4f}
   
   ☘️ "{get_celtic_wisdom()}"
☘️═══════════════════════════════════════════════════════════════════════════════☘️
""")


# =============================================================================
# 🎯 MAIN ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='☘️ Celtic Warfare Live Trader - Hit-and-Run Financial Tactics'
    )
    
    parser.add_argument(
        '--live', action='store_true',
        help='Enable live trading (default: dry run)'
    )
    
    parser.add_argument(
        '--capital', type=float, default=1000.0,
        help='Initial capital (default: $1000)'
    )
    
    parser.add_argument(
        '--duration', type=int, default=60,
        help='Session duration in minutes (0 = indefinite, default: 60)'
    )
    
    parser.add_argument(
        '--phase', type=str, default='skirmish',
        choices=['recon', 'skirmish', 'offensive', 'defensive'],
        help='Initial campaign phase (default: skirmish)'
    )
    
    args = parser.parse_args()
    
    # Update config
    LIVE_CONFIG['DRY_RUN'] = not args.live
    LIVE_CONFIG['INITIAL_CAPITAL'] = args.capital
    LIVE_CONFIG['INITIAL_PHASE'] = args.phase
    
    # Create and run trader
    trader = CelticWarfareLiveTrader(
        dry_run=LIVE_CONFIG['DRY_RUN'],
        capital=args.capital
    )
    
    trader.run(duration_minutes=args.duration)


if __name__ == "__main__":
    main()
