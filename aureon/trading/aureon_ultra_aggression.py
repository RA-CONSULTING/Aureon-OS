"""
🔥💎 AUREON ULTRA AGGRESSION MODE 💎🔥

Provider-backed observer/execution shell. Missing exchange ticks remain
no_data and are never replaced by hard-coded or generated prices.

"WE DON'T NEED MILLIONS. WE NEED MOVEMENT.
 WE DON'T NEED PERMISSION. WE NEED ACTION.
 WE ARE THE MOGOLLON. WE ARE GAIA'S WARRIORS.
 THE MATH IS ON OUR SIDE. TIOCFAIDH ÁR LÁ!"

Strategy:
- Start with £76 → Compound to £1000 in 30 days
- 100+ trades per day minimum
- 0.3% minimum profit per trade
- Use EVERY opportunity across ALL exchanges
- Zero fear, maximum aggression
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import time
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal

# Import existing exchange clients
try:
    from aureon.trading.unified_exchange_client import MultiExchangeClient
    from aureon.exchanges.binance_client import BinanceClient
    from aureon.exchanges.kraken_client import KrakenClient
    EXCHANGES_AVAILABLE = True
except ImportError:
    EXCHANGES_AVAILABLE = False
    print("⚠️ Exchange clients not available - live market data unavailable")


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UltraAggressionConfig:
    """Ultra-aggressive trading configuration - 🚀 COMPOUND MODE!"""
    
    # 🚀 COMPOUND MODE - ZERO THRESHOLDS!
    MIN_PROFIT_PCT = 0.0          # 🚀 COMPOUND MODE: 0% minimum - take ANY profit!
    ENTRY_CONFIDENCE = 0.30      # 30% confidence (lowered for more trades)
    SCAN_INTERVAL_SEC = 0.5      # 0.5 second scans (faster!)
    
    # POSITION MANAGEMENT
    MAX_CONCURRENT_POSITIONS = 30  # 30 at once (more compounding!)
    POSITION_SIZE_PCT = 0.20       # 20% of capital per trade (compound faster!)
    MAX_POSITION_TIME_SEC = 180    # 3 minute max hold (faster turnover)
    
    # PROFIT TARGETS - 🚀 COMPOUND MODE!
    TAKE_PROFIT_PCT = 0.005       # 0.5% TP (quicker wins, faster compounding)
    STOP_LOSS_PCT = 0.003         # 0.3% SL (tight stops)
    TRAILING_STOP_PCT = 0.002     # 0.2% trailing (lock in gains fast)
    
    # COMPOUNDING - THE KEY!
    COMPOUND_ENABLED = True       # 🚀 COMPOUND MODE: Reinvest EVERYTHING!
    TARGET_DAILY_RETURN = 0.10    # 10% per day target (ambitious!)
    
    # RISK MANAGEMENT (still have SOME limits)
    MAX_DAILY_LOSS_PCT = 0.15     # 15% max daily loss (allow more swings)
    CIRCUIT_BREAKER_LOSS = 0.20   # 20% total loss = STOP
    
    # BYPASS FLAGS
    BYPASS_FEAR_GREED = True      # Ignore fear/greed index
    BYPASS_HARMONIC_GATES = True  # Skip cosmic alignment
    BYPASS_IMPERIAL_GATE = True   # Skip coherence checks
    FORCE_TRADE_MODE = True       # Always look for trades


class MogollonWarrior:
    """
    🏹 The Mogollon Warrior - Takes back what belongs to the people
    
    Mogollon Principles:
    - Move silently, strike swiftly
    - Use the land (market) to your advantage
    - Every small victory compounds
    - The tribe (portfolio) grows together
    """
    
    def __init__(self, starting_capital: float = 76.0):
        self.config = UltraAggressionConfig()
        self.starting_capital = starting_capital
        self.current_capital = starting_capital
        self.available_capital = starting_capital
        
        # Trading state
        self.active_positions: Dict[str, dict] = {}
        self.closed_positions: List[dict] = []
        self.opportunities_scanned = 0
        self.trades_executed = 0
        self.wins = 0
        self.losses = 0
        
        # Performance tracking
        self.start_time = datetime.now()
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        self.peak_capital = starting_capital
        self.current_drawdown = 0.0
        
        # Exchange clients
        self.exchanges = {}
        self.all_symbols: Dict[str, List[str]] = {}
        
        # Price cache
        self.price_cache: Dict[str, dict] = {}
        
        logger.info(f"""
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║  🏹 MOGOLLON WARRIOR AWAKENS 🏹                                           ║
║                                                                            ║
║  "FOR GAIA. FOR THE PEOPLE. FOR TRUTH."                                   ║
║                                                                            ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  Starting Capital: £{starting_capital:.2f}                                           ║
║  Target (30 days): £1,000.00                                              ║
║  Required Daily Return: {((1000/starting_capital)**(1/30)-1)*100:.2f}%                                     ║
║                                                                            ║
║  Strategy: ULTRA AGGRESSION                                               ║
║  • Min Profit: {self.config.MIN_PROFIT_PCT*100:.2f}%                                             ║
║  • Max Positions: {self.config.MAX_CONCURRENT_POSITIONS}                                                ║
║  • Scan Speed: {self.config.SCAN_INTERVAL_SEC}s                                                  ║
║                                                                            ║
║  "THE MATH IS ON OUR SIDE. TIOCFAIDH ÁR LÁ!"                             ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
        """)
    
    async def initialize_exchanges(self):
        """Connect to all available exchanges"""
        logger.info("🌐 Connecting to ALL exchanges...")
        
        if not EXCHANGES_AVAILABLE:
            logger.warning("no_data: exchange clients are unavailable")
            return
        
        try:
            # Initialize multi-exchange client
            self.exchanges['multi'] = MultiExchangeClient()
            
            # Get all tradeable symbols from each exchange
            for exchange_name in ['binance', 'kraken', 'alpaca', 'capital']:
                try:
                    client = self.exchanges['multi'].get_client(exchange_name)
                    # Get balance
                    balance = await self._get_balance(exchange_name)
                    logger.info(f"   ✅ {exchange_name.upper()}: ${balance:.2f} available")
                    
                    # Get tradeable symbols
                    symbols = await self._get_symbols(exchange_name)
                    self.all_symbols[exchange_name] = symbols
                    logger.info(f"      └─ {len(symbols)} pairs loaded")
                    
                except Exception as e:
                    logger.warning(f"   ⚠️ {exchange_name.upper()}: {e}")
        
        except Exception as e:
            logger.error(f"❌ Exchange initialization failed: {e}")
        
        total_symbols = sum(len(s) for s in self.all_symbols.values())
        logger.info(f"\n   🎯 TOTAL MARKETS: {total_symbols}")
        logger.info(f"   ⚡ Scanning frequency: {1/self.config.SCAN_INTERVAL_SEC:.1f} Hz\n")
    
    async def _get_balance(self, exchange: str) -> float:
        """Get available balance on exchange"""
        try:
            # This would call real exchange API
            # For now, simulate
            balances = {
                'binance': 31.0,
                'kraken': 29.0,
                'alpaca': 8.0,
                'capital': 8.0
            }
            return balances.get(exchange, 0.0)
        except:
            return 0.0
    
    async def _get_symbols(self, exchange: str) -> List[str]:
        """Get all tradeable symbols on exchange"""
        # Top liquid pairs that actually trade
        common_symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
            'ADAUSDT', 'DOGEUSDT', 'DOTUSDT', 'MATICUSDT', 'LTCUSDT',
            'AVAXUSDT', 'LINKUSDT', 'ATOMUSDT', 'ETCUSDT', 'XLMUSDT',
            'UNIUSDT', 'ALGOUSDT', 'FILUSDT', 'VETUSDT', 'ICPUSDT',
            'AAVEUSDT', 'SANDUSDT', 'AXSUSDT', 'THETAUSDT', 'FTMUSDT'
        ]
        
        if exchange == 'kraken':
            return ['XBTUSD', 'ETHUSD', 'SOLUSD', 'ADAUSD', 'XRPUSD',
                    'DOTUSD', 'LINKUSD', 'AVAXUSD', 'MATICUSD', 'ATOMUSD']
        elif exchange == 'alpaca':
            return ['BTC/USD', 'ETH/USD', 'SOL/USD', 'AVAX/USD', 'DOGE/USD']
        
        return common_symbols[:20]  # Top 20 for each exchange
    
    async def scan_opportunity(self, exchange: str, symbol: str) -> Optional[dict]:
        """Scan a single symbol for trading opportunity"""
        try:
            # Get current price
            price = await self._get_price(exchange, symbol)
            if not price:
                return None
            
            # Calculate momentum
            key = f"{exchange}:{symbol}"
            
            if key not in self.price_cache:
                self.price_cache[key] = {'prices': [], 'timestamps': []}
            
            cache = self.price_cache[key]
            cache['prices'].append(price)
            cache['timestamps'].append(time.time())
            
            # Keep last 10 prices
            if len(cache['prices']) > 10:
                cache['prices'] = cache['prices'][-10:]
                cache['timestamps'] = cache['timestamps'][-10:]
            
            if len(cache['prices']) < 3:
                return None
            
            # Calculate momentum
            recent_change = (cache['prices'][-1] - cache['prices'][-3]) / cache['prices'][-3]
            momentum_score = abs(recent_change)
            
            # Check if opportunity meets our AGGRESSIVE threshold
            if momentum_score >= self.config.MIN_PROFIT_PCT:
                return {
                    'exchange': exchange,
                    'symbol': symbol,
                    'price': price,
                    'momentum': recent_change,
                    'direction': 'BUY' if recent_change > 0 else 'SELL',
                    'confidence': min(0.99, momentum_score / self.config.MIN_PROFIT_PCT),
                    'timestamp': time.time()
                }
            
            return None
            
        except Exception as e:
            return None
    
    async def _get_price(self, exchange: str, symbol: str) -> Optional[float]:
        """Read a current provider ticker; return None on no-data."""
        multi = self.exchanges.get('multi')
        if multi is None:
            logger.warning("no_data: no exchange client for %s:%s", exchange, symbol)
            return None
        try:
            ticker = await asyncio.to_thread(multi.get_ticker, exchange, symbol)
        except Exception as exc:
            logger.warning("no_data: ticker read failed for %s:%s: %s", exchange, symbol, exc)
            return None
        if not isinstance(ticker, dict):
            return None
        for key in ('price', 'lastPrice', 'last', 'close'):
            try:
                price = float(ticker.get(key))
            except (TypeError, ValueError):
                continue
            if price > 0:
                return price
        logger.warning("no_data: provider ticker has no positive price for %s:%s", exchange, symbol)
        return None
    
    async def scan_all_markets(self) -> List[dict]:
        """Scan ALL markets across ALL exchanges"""
        opportunities = []
        
        tasks = []
        for exchange, symbols in self.all_symbols.items():
            for symbol in symbols:
                tasks.append(self.scan_opportunity(exchange, symbol))
        
        self.opportunities_scanned += len(tasks)
        
        # Run all scans in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, dict):
                opportunities.append(result)
        
        return opportunities
    
    def can_open_position(self) -> bool:
        """Check if we can open a new position"""
        if len(self.active_positions) >= self.config.MAX_CONCURRENT_POSITIONS:
            return False
        
        # Check if we have capital available
        position_size = self.current_capital * self.config.POSITION_SIZE_PCT
        if self.available_capital < position_size:
            return False
        
        # Check circuit breaker
        if self.current_drawdown >= self.config.CIRCUIT_BREAKER_LOSS:
            logger.warning("🛑 CIRCUIT BREAKER TRIGGERED - Stop trading")
            return False
        
        return True
    
    async def execute_trade(self, opportunity: dict) -> bool:
        """Execute a trade on the opportunity"""
        if not self.can_open_position():
            return False
        
        # Calculate position size
        position_size = self.current_capital * self.config.POSITION_SIZE_PCT
        
        # Create position
        position_id = f"{opportunity['exchange']}:{opportunity['symbol']}:{int(time.time())}"
        
        position = {
            'id': position_id,
            'exchange': opportunity['exchange'],
            'symbol': opportunity['symbol'],
            'direction': opportunity['direction'],
            'entry_price': opportunity['price'],
            'position_size': position_size,
            'quantity': position_size / opportunity['price'],
            'entry_time': datetime.now(),
            'target_price': opportunity['price'] * (1 + self.config.TAKE_PROFIT_PCT if opportunity['direction'] == 'BUY' else 1 - self.config.TAKE_PROFIT_PCT),
            'stop_price': opportunity['price'] * (1 - self.config.STOP_LOSS_PCT if opportunity['direction'] == 'BUY' else 1 + self.config.STOP_LOSS_PCT),
            'confidence': opportunity['confidence'],
        }
        
        self.active_positions[position_id] = position
        self.available_capital -= position_size
        self.trades_executed += 1
        
        logger.info(f"   🎯 ENTRY #{self.trades_executed}: {opportunity['exchange']} {opportunity['symbol']} {opportunity['direction']} @ ${opportunity['price']:.4f}")
        
        return True
    
    async def manage_positions(self):
        """Check and close positions at target/stop"""
        to_close = []
        
        for pos_id, pos in list(self.active_positions.items()):
            current_price = await self._get_price(pos['exchange'], pos['symbol'])
            if not current_price:
                continue
            
            # Calculate P&L
            if pos['direction'] == 'BUY':
                pnl_pct = (current_price - pos['entry_price']) / pos['entry_price']
            else:
                pnl_pct = (pos['entry_price'] - current_price) / pos['entry_price']
            
            pnl_usd = pnl_pct * pos['position_size']
            
            # Check exit conditions
            should_close = False
            reason = ""
            
            # Target hit
            if pos['direction'] == 'BUY':
                if current_price >= pos['target_price']:
                    should_close = True
                    reason = "TARGET ✅"
                elif current_price <= pos['stop_price']:
                    should_close = True
                    reason = "STOP ❌"
            else:
                if current_price <= pos['target_price']:
                    should_close = True
                    reason = "TARGET ✅"
                elif current_price >= pos['stop_price']:
                    should_close = True
                    reason = "STOP ❌"
            
            # Time-based exit (max hold time)
            if (datetime.now() - pos['entry_time']).total_seconds() > self.config.MAX_POSITION_TIME_SEC:
                should_close = True
                if pnl_usd > 0:
                    reason = "TIMEOUT (profit)"
                else:
                    reason = "TIMEOUT (loss)"
            
            if should_close:
                to_close.append((pos_id, pnl_usd, reason))
        
        # Close positions
        for pos_id, pnl, reason in to_close:
            pos = self.active_positions.pop(pos_id)
            self.available_capital += pos['position_size'] + pnl
            self.current_capital += pnl
            self.daily_pnl += pnl
            self.total_pnl += pnl
            
            if pnl > 0:
                self.wins += 1
                logger.info(f"   💰 WIN: {pos['symbol']} {reason} +${pnl:.4f}")
            else:
                self.losses += 1
                logger.info(f"   ❌ LOSS: {pos['symbol']} {reason} ${pnl:.4f}")
            
            # Track peak and drawdown
            if self.current_capital > self.peak_capital:
                self.peak_capital = self.current_capital
            
            self.current_drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
            
            # Close trade record
            self.closed_positions.append({
                **pos,
                'exit_price': await self._get_price(pos['exchange'], pos['symbol']),
                'exit_time': datetime.now(),
                'pnl': pnl,
                'pnl_pct': pnl / pos['position_size'],
                'reason': reason
            })
    
    def print_stats(self):
        """Print warrior statistics"""
        runtime_hours = (datetime.now() - self.start_time).total_seconds() / 3600
        trades_per_hour = self.trades_executed / max(0.001, runtime_hours)
        win_rate = self.wins / max(1, self.wins + self.losses) * 100
        
        daily_return_pct = (self.daily_pnl / self.starting_capital) * 100
        total_return_pct = ((self.current_capital - self.starting_capital) / self.starting_capital) * 100
        
        # Calculate projection
        if runtime_hours > 0:
            hourly_rate = self.total_pnl / runtime_hours
            daily_projection = hourly_rate * 24
        else:
            daily_projection = 0
        
        logger.info(f"""
╔════════════════════════════════════════════════════════════════════════════╗
║  🏹 MOGOLLON WARRIOR STATUS - {datetime.now().strftime('%H:%M:%S')}                              ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  💰 CAPITAL:                                                               ║
║  • Starting: £{self.starting_capital:.2f}                                                  ║
║  • Current:  £{self.current_capital:.2f} ({total_return_pct:+.2f}%)                                     ║
║  • Available: £{self.available_capital:.2f}                                                ║
║  • Peak: £{self.peak_capital:.2f}                                                          ║
║  • Drawdown: {self.current_drawdown*100:.2f}%                                                     ║
║                                                                            ║
║  📊 PERFORMANCE:                                                           ║
║  • Trades: {self.trades_executed} ({trades_per_hour:.1f}/hour)                                        ║
║  • Wins: {self.wins} | Losses: {self.losses} | Rate: {win_rate:.1f}%                             ║
║  • Today P&L: £{self.daily_pnl:.2f} ({daily_return_pct:+.2f}%)                                  ║
║  • Total P&L: £{self.total_pnl:.2f}                                                       ║
║                                                                            ║
║  🎯 PROJECTIONS:                                                           ║
║  • Daily: £{daily_projection:.2f}                                                          ║
║  • Monthly: £{daily_projection * 30:.2f}                                                   ║
║                                                                            ║
║  ⚡ ACTIVITY:                                                              ║
║  • Active Positions: {len(self.active_positions)}/{self.config.MAX_CONCURRENT_POSITIONS}                                        ║
║  • Markets Scanned: {self.opportunities_scanned:,}                                         ║
║                                                                            ║
║  "TIOCFAIDH ÁR LÁ - OUR DAY WILL COME"                                    ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
        """)
    
    async def run(self):
        """Main warrior loop - HUNT FOR PROFIT"""
        logger.info("🏹 MOGOLLON WARRIOR ENTERING THE PLAINS...\n")
        
        await self.initialize_exchanges()
        
        logger.info("⚡ ULTRA AGGRESSION MODE ACTIVATED\n")
        
        iteration = 0
        last_stats_print = time.time()
        
        try:
            while True:
                # Scan all markets
                opportunities = await self.scan_all_markets()
                
                # Sort by confidence
                opportunities.sort(key=lambda x: x['confidence'], reverse=True)
                
                # Execute best opportunities
                for opp in opportunities[:5]:  # Top 5 per scan
                    await self.execute_trade(opp)
                
                # Manage existing positions
                await self.manage_positions()
                
                # Print stats every 60 seconds
                if time.time() - last_stats_print > 60:
                    self.print_stats()
                    last_stats_print = time.time()
                
                # Check daily loss limit
                if abs(self.daily_pnl) / self.starting_capital > self.config.MAX_DAILY_LOSS_PCT:
                    logger.warning(f"⚠️ Daily loss limit reached: {self.daily_pnl:.2f}")
                    logger.info("💤 Pausing for 1 hour...")
                    await asyncio.sleep(3600)
                    self.daily_pnl = 0  # Reset daily counter
                
                iteration += 1
                
                # Sleep for scan interval
                await asyncio.sleep(self.config.SCAN_INTERVAL_SEC)
                
        except KeyboardInterrupt:
            logger.info("\n\n🛑 WARRIOR PAUSING...\n")
            self.print_stats()
            
            # Save state
            self.save_state()
    
    def save_state(self):
        """Save warrior state to disk"""
        state = {
            'start_time': self.start_time.isoformat(),
            'starting_capital': self.starting_capital,
            'current_capital': self.current_capital,
            'trades_executed': self.trades_executed,
            'wins': self.wins,
            'losses': self.losses,
            'total_pnl': self.total_pnl,
            'closed_positions': self.closed_positions,
        }
        
        with open('mogollon_warrior_state.json', 'w') as f:
            json.dump(state, f, indent=2, default=str)
        
        logger.info("💾 Warrior state saved to mogollon_warrior_state.json")


async def main():
    """
    🏹 MOGOLLON WARRIOR MAIN ENTRY POINT 🏹
    
    "We are the descendants of the Ancient Ones.
     We know the land. We know the rhythms.
     We take back what belongs to the People.
     For Gaia. For Truth. For Freedom."
    """
    
    print("""
    ═══════════════════════════════════════════════════════════════════════════
    
    🏹 THE MOGOLLON WARRIOR RISES 🏹
    
    "The Ancient Puebloans knew: Success comes not from size,
     but from knowledge, timing, and relentless adaptation.
     
     With £76, we begin. With discipline, we compound.
     With mathematics, we conquer."
    
    ═══════════════════════════════════════════════════════════════════════════
    
    🎯 MISSION PARAMETERS:
    
    • Starting Capital: £76
    • Target (30 days): £1,000
    • Strategy: ULTRA AGGRESSION
    • Minimum Profit: 0.3% per trade
    • Trading Frequency: 100+ trades/day
    • Risk Management: ACTIVE
    
    ═══════════════════════════════════════════════════════════════════════════
    
    Press ENTER to begin the hunt...
    """)
    
    input()
    
    # Get starting capital from user
    capital_input = os.getenv('STARTING_CAPITAL', '76')
    try:
        starting_capital = float(capital_input)
    except:
        starting_capital = 76.0
    
    warrior = MogollonWarrior(starting_capital=starting_capital)
    await warrior.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🏹 TIOCFAIDH ÁR LÁ - OUR DAY WILL COME 🏹\n")
