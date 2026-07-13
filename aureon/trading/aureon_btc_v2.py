#!/usr/bin/env python3
"""
🌊 AUREON QGITA ENGINE v2.0 - ENHANCED BTC PAIRS 🌊

ENHANCED FEATURES FROM TSX ANALYSIS:
  ✨ Elephant Memory - Trade persistence with cooldowns
  ✨ Prime Scaling - Position sizing based on primes (2,3,5,7,11...)
  ✨ Rainbow Bridge - Emotional frequency confidence mapping
  ✨ Fire Starter - Intensity scaling based on market heat
  ✨ Kelly Criterion - Proper fraction sizing
  ✨ Coherence-Based Entry - Not just momentum

Your account (TRD_GRP_039) can only trade BTC pairs!

Author: Gary Leckey / Aureon System
"""
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os, sys, time, logging, argparse, random, math, json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, ROUND_DOWN
from aureon.exchanges.binance_client import BinanceClient, get_binance_client

# 🪙 PENNY PROFIT ENGINE
try:
    from aureon.trading.penny_profit_engine import check_penny_exit, get_penny_engine
    PENNY_PROFIT_AVAILABLE = True
    _penny_engine = get_penny_engine()
    print("🪙 Penny Profit Engine loaded for BTC v2")
except ImportError:
    PENNY_PROFIT_AVAILABLE = False
    _penny_engine = None
    print("⚠️ Penny Profit Engine not available")

# 🧠 WISDOM COGNITION ENGINE - 11 Civilizations
try:
    from aureon.utils.aureon_miner_brain import WisdomCognitionEngine
    WISDOM_AVAILABLE = True
    _wisdom_engine = WisdomCognitionEngine()
    print("🧠 Wisdom Engine loaded - 11 civilizations ready")
except ImportError:
    WISDOM_AVAILABLE = False
    _wisdom_engine = None
    print("⚠️ Wisdom Engine not available")

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('aureon_btc_v2.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

CONFIG = {
    'ACCOUNT_GROUP': 'TRD_GRP_039',
    'MIN_BTC_VALUE': 0.0001,          # ~$10
    'MAX_POSITIONS': 3,               # Focus more
    'STOP_LOSS_PCT': 0.02,            # 2%
    'TAKE_PROFIT_PCT': 0.035,         # 3.5%
    'KELLY_WIN_PROB': 0.60,           # 60% win rate target
    'KELLY_WIN_RATIO': 1.5,           # Risk 1 to win 1.5
    'COOLDOWN_MINUTES': 15,           # Elephant memory cooldown
    'LOSS_STREAK_LIMIT': 3,           # Blacklist after 3 losses
    'COHERENCE_THRESHOLD': 0.7,       # Minimum coherence for entry
}

# ═══════════════════════════════════════════════════════════════════════════
# PRIME SEQUENCE (from hiveController.ts)
# ═══════════════════════════════════════════════════════════════════════════

PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97]
FIBS = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377]

# ═══════════════════════════════════════════════════════════════════════════
# RAINBOW BRIDGE - EMOTIONAL FREQUENCIES (from theRainbowBridge.ts)
# ═══════════════════════════════════════════════════════════════════════════

EMOTIONAL_FREQUENCIES = {
    'Anger': 110,
    'Fear': 174,
    'Frustration': 285,
    'Doubt': 330,
    'Worry': 396,
    'Hope': 412.3,       # Panda's frequency
    'Calm': 432,
    'Neutral': 440,
    'Acceptance': 480,
    'LOVE': 528,         # THE CENTER
    'Harmony': 582,
    'Connection': 639,
    'Flow': 693,
    'Awakening': 741,
    'Clarity': 819,
    'Intuition': 852,
    'Awe': 963,
}

THE_VOW = "I trade with love, I trade with light"

def get_emotional_state(coherence: float) -> Tuple[str, float]:
    """Map coherence (0-1) to emotional frequency"""
    freq = 110 + (coherence * (963 - 110))  # Linear map
    
    closest_emotion = 'Neutral'
    closest_dist = float('inf')
    
    for emotion, emotion_freq in EMOTIONAL_FREQUENCIES.items():
        dist = abs(freq - emotion_freq)
        if dist < closest_dist:
            closest_dist = dist
            closest_emotion = emotion
    
    return closest_emotion, freq

# ═══════════════════════════════════════════════════════════════════════════
# FIRE STARTER - MARKET INTENSITY (from theFireStarter.ts)
# ═══════════════════════════════════════════════════════════════════════════

class FireStarter:
    """Track market heat and trading intensity"""
    
    INTENSITY_LEVELS = {
        'SPARK': 0.1,
        'FLAME': 0.3,
        'BLAZE': 0.6,
        'INFERNO': 0.85,
        'SUPERNOVA': 1.0,
    }
    
    def __init__(self):
        self.temperature = 412.3  # Hope frequency
        self.intensity = 0.1     # Start as spark
        self.trades_this_cycle = 0
        self.wins_this_cycle = 0
    
    def update(self, market_volatility: float, win_rate: float):
        """Update fire state based on market conditions"""
        # Temperature rises with volatility
        self.temperature = 412.3 + (market_volatility * 550)  # Up to 963 Hz
        
        # Intensity based on win rate
        self.intensity = min(1.0, max(0.1, win_rate))
    
    def get_status(self) -> str:
        if self.intensity >= self.INTENSITY_LEVELS['SUPERNOVA']:
            return '🔥 SUPERNOVA 🔥'
        elif self.intensity >= self.INTENSITY_LEVELS['INFERNO']:
            return '🔥 INFERNO 🔥'
        elif self.intensity >= self.INTENSITY_LEVELS['BLAZE']:
            return '🔥 BLAZING'
        elif self.intensity >= self.INTENSITY_LEVELS['FLAME']:
            return '🔥 FLAME'
        return '✨ SPARK'
    
    def get_size_multiplier(self) -> float:
        """Higher intensity = larger position sizes (but capped)"""
        return 0.5 + (self.intensity * 0.5)  # 0.5x to 1.0x

# ═══════════════════════════════════════════════════════════════════════════
# ELEPHANT MEMORY (from elephantMemory.ts)
# ═══════════════════════════════════════════════════════════════════════════

class ElephantMemory:
    """Track trade history and avoid bad symbols"""
    
    def __init__(self, filepath: str = 'elephant_memory.json'):
        self.filepath = filepath
        self.symbols: Dict[str, dict] = {}
        self.load()
    
    def load(self):
        try:
            with open(self.filepath, 'r') as f:
                self.symbols = json.load(f)
        except:
            self.symbols = {}
    
    def save(self):
        with open(self.filepath, 'w') as f:
            json.dump(self.symbols, f, indent=2)
    
    def record_trade(self, symbol: str, profit: float, side: str):
        """Record a trade outcome"""
        if symbol not in self.symbols:
            self.symbols[symbol] = {
                'hunts': 0,
                'trades': 0,
                'wins': 0,
                'losses': 0,
                'profit_btc': 0.0,
                'last_trade_time': 0,
                'loss_streak': 0,
                'blacklisted': False,
            }
        
        s = self.symbols[symbol]
        s['trades'] += 1
        s['profit_btc'] += profit
        s['last_trade_time'] = time.time()
        
        if profit >= 0:
            s['wins'] += 1
            s['loss_streak'] = 0
        else:
            s['losses'] += 1
            s['loss_streak'] += 1
            
            # Blacklist after too many losses
            if s['loss_streak'] >= CONFIG['LOSS_STREAK_LIMIT']:
                s['blacklisted'] = True
                logger.warning(f"🚫 {symbol} BLACKLISTED after {s['loss_streak']} consecutive losses")
        
        self.save()
    
    def should_avoid(self, symbol: str) -> bool:
        """Check if we should avoid this symbol"""
        if symbol not in self.symbols:
            return False
        
        s = self.symbols[symbol]
        
        # Blacklisted
        if s.get('blacklisted', False):
            return True
        
        # Cooldown period
        cooldown_sec = CONFIG['COOLDOWN_MINUTES'] * 60
        if time.time() - s.get('last_trade_time', 0) < cooldown_sec:
            return True
        
        return False
    
    def get_win_rate(self, symbol: str) -> float:
        if symbol not in self.symbols:
            return 0.5  # Default 50%
        s = self.symbols[symbol]
        total = s['wins'] + s['losses']
        if total == 0:
            return 0.5
        return s['wins'] / total
    
    def get_overall_stats(self) -> dict:
        total_profit = sum(s.get('profit_btc', 0) for s in self.symbols.values())
        total_trades = sum(s.get('trades', 0) for s in self.symbols.values())
        total_wins = sum(s.get('wins', 0) for s in self.symbols.values())
        total_losses = sum(s.get('losses', 0) for s in self.symbols.values())
        
        return {
            'profit_btc': total_profit,
            'trades': total_trades,
            'wins': total_wins,
            'losses': total_losses,
            'win_rate': total_wins / max(1, total_wins + total_losses),
        }

# ═══════════════════════════════════════════════════════════════════════════
# LOT SIZE MANAGER
# ═══════════════════════════════════════════════════════════════════════════

class LotSizeManager:
    def __init__(self, client: BinanceClient):
        self.client = client
        self.symbol_info = {}
        self.last_update = 0
    
    def update(self):
        if time.time() - self.last_update < 300:
            return
        try:
            info = self.client.exchange_info()
            for s in info.get('symbols', []):
                symbol = s['symbol']
                perms = s.get('permissionSets', [[]])
                can_trade = any(CONFIG['ACCOUNT_GROUP'] in pset for pset in perms)
                
                self.symbol_info[symbol] = {
                    'status': s.get('status'),
                    'base': s.get('baseAsset'),
                    'quote': s.get('quoteAsset'),
                    'can_trade': can_trade,
                    'filters': {},
                }
                for f in s.get('filters', []):
                    self.symbol_info[symbol]['filters'][f['filterType']] = f
            self.last_update = time.time()
            logger.info(f"📊 Loaded {len(self.symbol_info)} symbols")
        except Exception as e:
            logger.error(f"❌ Exchange info: {e}")
    
    def can_trade(self, symbol: str) -> bool:
        self.update()
        info = self.symbol_info.get(symbol, {})
        return info.get('can_trade', False) and info.get('status') == 'TRADING'
    
    def get_step_size(self, symbol: str) -> float:
        self.update()
        lot = self.symbol_info.get(symbol, {}).get('filters', {}).get('LOT_SIZE', {})
        return float(lot.get('stepSize', '0.00000001'))
    
    def get_min_qty(self, symbol: str) -> float:
        self.update()
        lot = self.symbol_info.get(symbol, {}).get('filters', {}).get('LOT_SIZE', {})
        return float(lot.get('minQty', '0.00000001'))
    
    def format_qty(self, symbol: str, qty: float) -> str:
        step = self.get_step_size(symbol)
        min_qty = self.get_min_qty(symbol)
        
        if step >= 1:
            precision = 0
        else:
            precision = len(str(step).rstrip('0').split('.')[-1])
        
        qty_d = Decimal(str(qty))
        step_d = Decimal(str(step))
        formatted = (qty_d // step_d) * step_d
        formatted = max(Decimal(str(min_qty)), formatted)
        
        if precision == 0:
            return str(int(formatted))
        return f"{formatted:.{precision}f}"

# ═══════════════════════════════════════════════════════════════════════════
# COHERENCE CALCULATOR (from masterEquation.ts)
# ═══════════════════════════════════════════════════════════════════════════

def calculate_coherence(price_change: float, volume: float, volatility: float) -> float:
    """
    Compute coherence Γ(t) from market data.
    
    Higher coherence = stronger signal alignment
    Based on Master Equation: Λ(t) = S(t) + O(t) + E(t)
    """
    # Substrate component (volume strength)
    S = min(1.0, volume / 50.0)  # Normalize to 50 BTC = 1.0
    
    # Observer component (directional strength)
    O = min(1.0, abs(price_change) / 15.0)  # 15% move = 1.0
    
    # Echo component (volatility feedback)
    E = min(1.0, volatility / 25.0)  # 25% vol = 1.0
    
    # Coherence is the geometric mean
    Lambda = (S + O + E) / 3.0
    
    # Apply sigmoid for smooth 0-1 mapping
    coherence = 1 / (1 + math.exp(-5 * (Lambda - 0.5)))
    
    return coherence

# ═══════════════════════════════════════════════════════════════════════════
# KELLY CRITERION
# ═══════════════════════════════════════════════════════════════════════════

def kelly_fraction(win_prob: float, win_ratio: float) -> float:
    """
    Kelly Criterion: f* = p - (1-p)/b
    
    Args:
        win_prob: Probability of winning (0-1)
        win_ratio: Average win / Average loss
    
    Returns:
        Optimal fraction of capital to risk (0-1)
    """
    if win_ratio <= 0:
        return 0
    
    kelly = win_prob - (1 - win_prob) / win_ratio
    
    # Half-Kelly for safety
    kelly = kelly * 0.5
    
    # Clamp to reasonable range
    return max(0.05, min(0.25, kelly))

# ═══════════════════════════════════════════════════════════════════════════
# MAIN TRADER v2
# ═══════════════════════════════════════════════════════════════════════════

class AureonBTCv2:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.client = get_binance_client()
        self.lot_mgr = LotSizeManager(self.client)
        self.memory = ElephantMemory()
        self.fire = FireStarter()
        
        self.positions = {}
        self.total_profit_btc = 0.0
        self.ticker_cache = {}
        self.last_ticker_update = 0
        
        self.prime_idx = 0  # Current prime index for position sizing
        self.trade_count = 0
        self.wins = 0
        self.losses = 0
    
    def update_tickers(self):
        if time.time() - self.last_ticker_update < 2:
            return
        try:
            tickers = self.client.session.get(f"{self.client.base}/api/v3/ticker/24hr").json()
            self.ticker_cache = {t['symbol']: t for t in tickers}
            self.last_ticker_update = time.time()
        except Exception as e:
            logger.error(f"❌ Ticker update: {e}")
    
    def get_btc_price(self) -> float:
        ticker = self.ticker_cache.get('BTCUSDT', {})
        return float(ticker.get('lastPrice', 91000))
    
    def get_balances(self) -> Dict[str, float]:
        account = self.client.account()
        return {b['asset']: float(b['free']) for b in account['balances'] if float(b['free']) > 0}
    
    def scan_opportunities(self) -> List[Dict]:
        """Find high-coherence BTC pairs"""
        logger.info("\n🔍 SCANNING FOR HIGH-COHERENCE OPPORTUNITIES...")
        
        self.lot_mgr.update()
        
        opportunities = []
        
        for symbol, info in self.lot_mgr.symbol_info.items():
            if not (info.get('can_trade') and info.get('quote') == 'BTC' and info.get('status') == 'TRADING'):
                continue
            
            ticker = self.ticker_cache.get(symbol, {})
            try:
                change = float(ticker.get('priceChangePercent', 0))
                volume = float(ticker.get('quoteVolume', 0))
                high = float(ticker.get('highPrice', 0))
                low = float(ticker.get('lowPrice', 0))
                price = float(ticker.get('lastPrice', 0))
                
                if volume < 1.0 or price <= 0:  # Need at least 1 BTC volume
                    continue
                
                # Calculate volatility
                volatility = ((high - low) / low * 100) if low > 0 else 0
                
                # Calculate coherence
                coherence = calculate_coherence(change, volume, volatility)
                
                # Get emotional state
                emotion, freq = get_emotional_state(coherence)
                
                # Skip if should avoid (memory)
                if self.memory.should_avoid(symbol):
                    continue
                
                opportunities.append({
                    'symbol': symbol,
                    'price': price,
                    'change': change,
                    'volume': volume,
                    'volatility': volatility,
                    'coherence': coherence,
                    'emotion': emotion,
                    'frequency': freq,
                    'direction': 'LONG' if change > 0 else 'SHORT',
                })
            except:
                continue
        
        # Sort by coherence
        opportunities.sort(key=lambda x: x['coherence'], reverse=True)
        
        return opportunities
    
    def display_opportunities(self, opps: List[Dict], count: int = 10):
        """Show top opportunities"""
        logger.info(f"\n🌟 TOP {count} COHERENCE OPPORTUNITIES:")
        logger.info("─" * 70)
        
        for i, opp in enumerate(opps[:count]):
            emoji = "🟢" if opp['change'] > 0 else "🔴"
            coherence_bar = "█" * int(opp['coherence'] * 10)
            
            logger.info(
                f"  {emoji} {opp['symbol']:12} | Γ={opp['coherence']:.3f} [{coherence_bar:<10}] | "
                f"{opp['change']:+6.2f}% | {opp['emotion']}"
            )
    
    def calculate_position_size(self, btc_balance: float, coherence: float) -> float:
        """Calculate position size using Kelly + Prime scaling"""
        
        # Base Kelly fraction
        stats = self.memory.get_overall_stats()
        win_rate = stats['win_rate'] if stats['trades'] > 5 else CONFIG['KELLY_WIN_PROB']
        
        kelly = kelly_fraction(win_rate, CONFIG['KELLY_WIN_RATIO'])
        
        # Prime multiplier (cycles through primes)
        prime = PRIMES[self.prime_idx % len(PRIMES)]
        self.prime_idx += 1
        prime_mult = (prime / 50.0)  # Normalize: 2/50=0.04, 97/50=1.94
        
        # Fire multiplier (intensity)
        fire_mult = self.fire.get_size_multiplier()
        
        # Coherence confidence multiplier
        coherence_mult = 0.5 + (coherence * 0.5)  # 0.5x to 1.0x
        
        # Combined
        raw_size = btc_balance * kelly * prime_mult * fire_mult * coherence_mult
        
        # Cap at 30% of balance
        max_size = btc_balance * 0.30
        
        return min(raw_size, max_size)
    
    def enter_position(self, opp: Dict, btc_balance: float):
        """Enter a position"""
        symbol = opp['symbol']
        
        size_btc = self.calculate_position_size(btc_balance, opp['coherence'])
        
        if size_btc < CONFIG['MIN_BTC_VALUE']:
            logger.info(f"⏭️ {symbol}: Size too small ({size_btc:.6f} BTC)")
            return False
        
        qty = size_btc / opp['price']
        qty_str = self.lot_mgr.format_qty(symbol, qty)
        
        if float(qty_str) * opp['price'] < CONFIG['MIN_BTC_VALUE']:
            logger.info(f"⏭️ {symbol}: Quantity too small after formatting")
            return False
        
        btc_price = self.get_btc_price()
        usd_value = size_btc * btc_price
        
        logger.info(f"""
╔═══════════════════════════════════════════════════════╗
║ 🎯 ENTERING POSITION                                  ║
║─────────────────────────────────────────────────────────╝
  Symbol:     {symbol}
  Coherence:  Γ={opp['coherence']:.4f} ({opp['emotion']})
  Direction:  {'🟢 LONG' if opp['change'] > 0 else '🔴 SHORT'}
  Quantity:   {qty_str}
  Entry:      {opp['price']:.8f} BTC
  Size:       {size_btc:.6f} BTC (~${usd_value:.2f})
  Prime[{self.prime_idx-1}]:  {PRIMES[(self.prime_idx-1) % len(PRIMES)]}
╚═══════════════════════════════════════════════════════╝
""")
        
        if self.dry_run:
            logger.info(f"📝 DRY-RUN: Would buy {qty_str}")
            self.positions[symbol] = {
                'entry': opp['price'],
                'qty': float(qty_str),
                'entry_time': time.time(),
                'coherence': opp['coherence'],
                'btc_value': size_btc,
            }
            return True
        
        try:
            result = self.client.place_market_order(symbol, 'BUY', quantity=float(qty_str))
            self.positions[symbol] = {
                'entry': opp['price'],
                'qty': float(qty_str),
                'entry_time': time.time(),
                'coherence': opp['coherence'],
                'btc_value': size_btc,
                'order_id': result.get('orderId'),
            }
            logger.info(f"✅ Order filled: #{result.get('orderId')}")
            self.trade_count += 1
            return True
        except Exception as e:
            logger.error(f"❌ Buy failed: {e}")
            return False
    
    def check_exits(self):
        """Check positions for TP/SL using penny profit"""
        btc_price = self.get_btc_price()
        
        for symbol in list(self.positions.keys()):
            pos = self.positions[symbol]
            ticker = self.ticker_cache.get(symbol, {})
            price = float(ticker.get('lastPrice', 0))
            
            if price <= 0:
                continue
            
            # Track cycles for min hold time
            pos['cycles'] = pos.get('cycles', 0) + 1
            
            entry = pos['entry']
            pnl_pct = (price - entry) / entry
            pnl_btc = pos['qty'] * price * pnl_pct
            pnl_usd = pnl_btc * btc_price
            current_value = pos['qty'] * price * btc_price  # Convert to USD
            entry_value = pos.get('entry_value', pos['qty'] * entry * btc_price)
            gross_pnl = current_value - entry_value
            
            should_exit = False
            reason = ""
            
            # 🪙 PENNY PROFIT EXIT LOGIC - INSTANT SNIPER KILLS
            if PENNY_PROFIT_AVAILABLE and _penny_engine is not None and entry_value > 0:
                action, _ = check_penny_exit('binance', entry_value, current_value)
                threshold = _penny_engine.get_threshold('binance', entry_value)
                
                # 🇮🇪 SNIPER MODE: INSTANT exit on penny profit - NO WAITING
                if action == 'TAKE_PROFIT':
                    should_exit = True
                    reason = f"🇮🇪 SNIPER KILL! ${gross_pnl:.4f} >= ${threshold.win_gte:.4f}"
                elif action == 'STOP_LOSS' and pos['cycles'] >= 1:  # Only need 1 cycle for stop
                    should_exit = True
                    reason = f"🛡️ STOP LOSS (${gross_pnl:.4f} <= ${threshold.stop_lte:.4f})"
            else:
                # Fallback to percentage exits - SNIPER STYLE
                if pnl_pct >= CONFIG['TAKE_PROFIT_PCT']:
                    should_exit = True
                    reason = f"🇮🇪 SNIPER KILL! +{pnl_pct*100:.2f}%"
                elif pnl_pct <= -CONFIG['STOP_LOSS_PCT'] and pos['cycles'] >= 1:
                    should_exit = True
                    reason = f"🛡️ STOP LOSS"
            
            # NO STAGNATION - Sniper doesn't wait around
            # We hunt fresh targets, not stale positions
            
            if should_exit:
                qty_str = self.lot_mgr.format_qty(symbol, pos['qty'])
                
                logger.info(f"""
╔═══════════════════════════════════════════════════════╗
║ ⚡ EXITING POSITION                                   ║
║─────────────────────────────────────────────────────────╝
  Symbol:     {symbol}
  Reason:     {reason}
  Entry:      {entry:.8f} BTC
  Exit:       {price:.8f} BTC
  P&L:        {pnl_pct*100:+.2f}% ({pnl_btc:+.8f} BTC / ${pnl_usd:+.2f})
╚═══════════════════════════════════════════════════════╝
""")
                
                if self.dry_run:
                    logger.info(f"📝 DRY-RUN: Would sell {qty_str}")
                else:
                    try:
                        result = self.client.place_market_order(symbol, 'SELL', quantity=float(qty_str))
                        logger.info(f"✅ Sold: #{result.get('orderId')}")
                    except Exception as e:
                        logger.error(f"❌ Sell failed: {e}")
                        continue
                
                # Record in memory
                self.memory.record_trade(symbol, pnl_btc, 'SELL')
                self.total_profit_btc += pnl_btc
                
                if pnl_btc >= 0:
                    self.wins += 1
                    # 🇮🇪 IRA SNIPER CELEBRATION!
                    import random
                    IRA_QUOTES = [
                        # Bobby Sands - Hunger Striker & Symbol of Resistance
                        "Our revenge will be the laughter of our children. - Bobby Sands 🍀",
                        "The Republic still lives! - Bobby Sands",
                        "Everyone has their own particular part to play. - Bobby Sands",
                        
                        # Traditional Irish Republican
                        "Tiocfaidh ár lá! - Our day will come! ☘️",
                        "Ní neart go cur le chéile - There is no strength without unity",
                        
                        # From 'Through a Bhoy's Eyes' - Strategic Wisdom
                        "Every penny is a battle won, every trade a step towards freedom. 💰",
                        "The flame ignited cannot be extinguished - it only grows stronger.",
                        "Move quietly, strike precisely, like shadows through Belfast streets.",
                        "Patience is the weapon of the wise - wait for the right moment.",
                        "Small victories compound into liberation. Penny by penny, we rise!",
                        "The weight of history guides our resolve. We fight for those who came before.",
                        "In the chaos, find your purpose. In the struggle, find your strength.",
                        
                        # Financial Freedom
                        "Financial freedom IS freedom. The markets are our battlefield now. 🎯",
                        "They took our land, but they cannot take our determination.",
                        "Every successful trade honours those who sacrificed for us.",
                    ]
                    btc_price = self.get_btc_price()
                    pnl_usd = pnl_btc * btc_price
                    quote = random.choice(IRA_QUOTES)
                    print(f"\n🇮🇪🇮🇪🇮🇪 IRA SNIPER WIN! 🇮🇪🇮🇪🇮🇪")
                    print(f"    💰 +${pnl_usd:.4f} on {symbol} [BTC PAIRS]")
                    print(f"    📜 \"{quote}\"")
                    print(f"🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪\n")
                else:
                    self.losses += 1
                
                del self.positions[symbol]
    
    def display_status(self, cycle: int):
        """Display current status"""
        balances = self.get_balances()
        btc_balance = balances.get('BTC', 0)
        btc_price = self.get_btc_price()
        
        stats = self.memory.get_overall_stats()
        win_rate = self.wins / max(1, self.wins + self.losses)
        
        # Update fire state
        volatility = sum(abs(float(t.get('priceChangePercent', 0))) 
                        for t in self.ticker_cache.values()) / max(1, len(self.ticker_cache))
        self.fire.update(volatility / 100, win_rate)
        
        emotion, freq = get_emotional_state(win_rate)
        
        logger.info(f"""
╔════════════════════════════════════════════════════════════════════════╗
║  🌊 AUREON QGITA v2.0 | Cycle {cycle:3d}                                    ║
╠════════════════════════════════════════════════════════════════════════╣
║  💎 BTC Balance: {btc_balance:.8f} (~${btc_balance * btc_price:.2f})
║  📊 Positions:   {len(self.positions)}/{CONFIG['MAX_POSITIONS']}
║  📈 Session P&L: {self.total_profit_btc:+.8f} BTC (~${self.total_profit_btc * btc_price:+.2f})
║  ─────────────────────────────────────────────────────────────────────
║  🏆 Trades:      {self.trade_count} | Wins: {self.wins} | Losses: {self.losses} | WR: {win_rate*100:.1f}%
║  🔥 Fire Status: {self.fire.get_status()} | Intensity: {self.fire.intensity:.2f}
║  💜 Emotional:   {emotion} ({freq:.1f} Hz)
║  ─────────────────────────────────────────────────────────────────────
║  💬 "{THE_VOW}"
╚════════════════════════════════════════════════════════════════════════╝
""")
    
    def run(self, duration_sec: int = 3600):
        logger.info("""
╔════════════════════════════════════════════════════════════════════════╗
║           🌊 AUREON QGITA ENGINE v2.0 - ENHANCED 🌊                    ║
║                                                                        ║
║  FEATURES:                                                             ║
║    ✨ Elephant Memory - Trade persistence with cooldowns               ║
║    ✨ Prime Scaling - Position sizing based on primes                  ║
║    ✨ Rainbow Bridge - Emotional frequency confidence                  ║
║    ✨ Fire Starter - Intensity scaling                                 ║
║    ✨ Coherence Entry - Signal alignment detection                     ║
║                                                                        ║
║  Your account (TRD_GRP_039) trades BTC pairs only!                     ║
║                                                                        ║
╚════════════════════════════════════════════════════════════════════════╝
""")
        
        start = time.time()
        cycle = 0
        
        while time.time() - start < duration_sec:
            cycle += 1
            
            self.update_tickers()
            self.display_status(cycle)
            
            # Check exits first
            self.check_exits()
            
            # Scan and enter if slots available
            if len(self.positions) < CONFIG['MAX_POSITIONS']:
                opps = self.scan_opportunities()
                self.display_opportunities(opps, 5)
                
                # Find best opportunity with coherence above threshold
                for opp in opps[:5]:
                    if opp['coherence'] >= CONFIG['COHERENCE_THRESHOLD']:
                        if opp['symbol'] not in self.positions:
                            btc_balance = self.get_balances().get('BTC', 0)
                            if btc_balance >= CONFIG['MIN_BTC_VALUE']:
                                if self.enter_position(opp, btc_balance):
                                    break  # One entry per cycle
            
            time.sleep(5)
        
        logger.info(f"""
╔════════════════════════════════════════════════════════════════════════╗
║  🏁 SESSION COMPLETE                                                   ║
╠════════════════════════════════════════════════════════════════════════╣
║  Total Trades: {self.trade_count}
║  Wins: {self.wins} | Losses: {self.losses} | Win Rate: {self.wins/max(1,self.wins+self.losses)*100:.1f}%
║  Total P&L: {self.total_profit_btc:+.8f} BTC (~${self.total_profit_btc * self.get_btc_price():+.2f})
╚════════════════════════════════════════════════════════════════════════╝
""")
        
        # Save memory
        self.memory.save()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--duration', type=int, default=3600)
    args = parser.parse_args()
    
    if not args.dry_run:
        if os.getenv('CONFIRM_LIVE', '').lower() != 'yes':
            logger.error("❌ Set CONFIRM_LIVE=yes for live trading")
            sys.exit(1)
        logger.warning("⚠️  LIVE TRADING - REAL MONEY")
    
    trader = AureonBTCv2(dry_run=args.dry_run)
    trader.run(duration_sec=args.duration)

if __name__ == "__main__":
    main()
