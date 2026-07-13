#!/usr/bin/env python3
"""
🌌 AUREON UNIFIED LIVE TRADER 🌌
================================

ALL SYSTEMS INTEGRATED:
  ✨ 9 Auris Nodes (Coherence detection)
  ✨ Elephant Memory (Trade persistence)
  ✨ Fire Starter (Intensity scaling)
  ✨ Rainbow Bridge (Emotional frequencies)
  ✨ Kelly Criterion (Optimal sizing)
  ✨ Ping-Pong Engine (Momentum building)
  ✨ Temporal Reader (Past/Present/Future)
  ✨ Proper LOT_SIZE (No more errors!)

ONE SYSTEM. ALL THE POWER.

Gary Leckey | November 2025
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os, sys, time, math, json, logging, tempfile
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, ROUND_DOWN

# Windows Unicode Fix
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from aureon.exchanges.binance_client import BinanceClient, get_binance_client
from aureon.strategies.hnc_probability_matrix import HNCProbabilityIntegration
from aureon.core.aureon_memory_core import memory as spiral_memory

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('aureon_unified_live.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# v5 REAL TRADING INSIGHTS (FROM 24 PAPER + 1 REAL TRADE)
# ═══════════════════════════════════════════════════════════════════════════
"""
📊 KEY LEARNINGS:
┌─────────────────────────────────────────────────────────────────────┐
│ FREQUENCY BANDS:                                                    │
│   • 750-850Hz (Intuition) → 67% WR, +$0.48 P&L ✅ TRADE             │
│   • 850Hz+ (Awakening) → 67% WR, +$1.68 P&L ✅ TRADE                │
│   • 450-550Hz (Transformation) → 27% WR, -$0.16 P&L ⛔ AVOID        │
│                                                                      │
│ REAL TRADING INSIGHT:                                               │
│   • Paper: +$2.00 profit | Real: -$1.50 loss                        │
│   • Gap = FEES (0.2% round trip) + SLIPPAGE                         │
│   • Need minimum 0.5% gain to be profitable after fees              │
│                                                                      │
│ RISK/REWARD: 4.48:1 (Avg Win $0.27 / Avg Loss $0.06)                │
│ TP EXITS: 100% win rate when reached                                │
└─────────────────────────────────────────────────────────────────────┘
"""

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION - v6 TRAILING STOP + SPIKE PROTECTION
# ═══════════════════════════════════════════════════════════════════════════
"""
📊 v6 LEARNINGS FROM 24 PAPER + 1 REAL TRADE:
┌─────────────────────────────────────────────────────────────────────┐
│ WINNING PATTERNS:                                                   │
│   • SAPIEN @ 890-963Hz + Coherence 0.924 → TP exits (+$1.86)       │
│   • TP exits = 100% win rate (never give back gains!)              │
│   • High freq (750-963Hz) + High coherence (0.90+) = Best combo    │
│                                                                      │
│ LOSING PATTERNS:                                                    │
│   • Fast SL (11 sec hold) = spike caught us at entry               │
│   • Low freq (450-550Hz) = 27% WR - avoid completely               │
│   • Timeout exits at breakeven = wasted opportunity cost           │
│                                                                      │
│ v6 SOLUTION: TRAILING STOPS + SPIKE DETECTION                      │
│   • Trail profits at 0.8% below peak (never give back +1% gains)   │
│   • Detect price spikes (>1% in 30 sec) and delay entry            │
│   • Prioritize symbols with proven edge (SAPIEN > others)          │
└─────────────────────────────────────────────────────────────────────┘
"""

CONFIG = {
    'MIN_TRADE_USD': 10.0,        # v5: Increased min to reduce fee impact
    'MAX_POSITIONS': 2,           # v4: Reduced from 3 for focus
    'STOP_LOSS_PCT': 0.008,       # v5: Widened to 0.8% (was 0.5% - too tight)
    'TAKE_PROFIT_PCT': 0.015,     # v5: Increased to 1.5% to clear fees
    'PING_THRESHOLD': 0.005,      # 0.5% for entry
    'PONG_THRESHOLD': 0.01,       # 1% for exit
    
    # 🔓 FULL AUTONOMOUS: Lowered coherence threshold to allow more trades
    'COHERENCE_THRESHOLD': 0.30,  # 🔓 LOWERED from 0.70 - let more pass
    'COHERENCE_OPTIMAL': 0.60,    # 🔓 LOWERED from 0.88
    'COHERENCE_SCALING': True,    # v6: Scale position by coherence quality
    
    'COOLDOWN_MINUTES': 5,        # v4: Symbol cooldown
    'TIMEOUT_SEC': 420,           # v5: 7 min timeout (was 5 min)
    
    # v5 FEE AWARENESS (Updated for Safety)
    'BINANCE_FEE_PCT': 0.001,     # 0.1% per trade
    # ROUND_TRIP_FEE includes: 0.2% fees + 0.2% slippage + 0.1% spread = 0.5%
    'ROUND_TRIP_FEE': 0.005,      # 0.5% total cost buffer (Guaranteed Net Profit)
    'MIN_PROFIT_AFTER_FEES': 0.005,  # Need 0.5% profit minimum
    
    # v5 LEARNED FREQUENCY BANDS (extended to include 850Hz+)
    'FREQ_OPTIMAL_MIN': 750,      # 750-963Hz = 67% WR (Intuition + Awakening)
    'FREQ_OPTIMAL_MAX': 963,      # Extended to include Awakening band
    'FREQ_AVOID_MIN': 450,        # 450-550Hz = 27% WR (avoid)
    'FREQ_AVOID_MAX': 550,

    # Quote coverage
    'ALLOWED_QUOTES': ['USDC', 'USDT'],  # Trade both USDC and USDT pairs
    
    # v6 TRAILING STOP (Lock in profits!)
    'ENABLE_TRAILING_STOP': True,
    'TRAIL_ACTIVATION_PCT': 0.008,  # Activate trailing at +0.8% profit
    'TRAIL_DISTANCE_PCT': 0.005,    # Trail 0.5% below peak (tight trail)
    
    # v6 SPIKE PROTECTION (Avoid entries after pumps)
    'SPIKE_THRESHOLD_PCT': 0.01,    # 1% move in short time = spike
    'SPIKE_LOOKBACK_SEC': 30,       # Check last 30 seconds
    'SPIKE_COOLDOWN_SEC': 60,       # Wait 60 sec after spike before entry
    
    # v6 SYMBOL PREFERENCE (Learned edge)
    'PREFERRED_SYMBOLS': ['SAPIENUSDC'],  # Proven 67%+ WR
    'PREFERRED_BONUS': 1.5,         # 50% score bonus for proven symbols
        # v6.1 FORCE MODE (bypass most gates to land first trade)
        'FORCE_TRADE': os.getenv('FORCE_TRADE', '0') == '1',
        'FORCE_TRADE_SYMBOL': os.getenv('FORCE_TRADE_SYMBOL', ''),
        'FORCE_MIN_VOLUME': 15000,  # Still require basic liquidity guard
    
    # v6 ADAPTIVE PROBABILITY (from paper: 0.78-0.83 won, 0.85+ lost!)
    'PROB_MIN': 0.50,              # v6: Lowered - let other filters qualify
    'PROB_OPTIMAL_MIN': 0.78,      # v6: Sweet spot lower bound
    'PROB_OPTIMAL_MAX': 0.83,      # v6: Sweet spot upper bound (0.85+ = 0% WR!)
    'PROB_CAP': 0.83,              # v6: Never trust >83% (overconfident signals)
}

# ═══════════════════════════════════════════════════════════════════════════
# ELEPHANT MEMORY
# ═══════════════════════════════════════════════════════════════════════════

class ElephantMemory:
    def __init__(self, filepath: str = 'memory.json'):
        self.filepath = filepath
        self.symbols = {}
        self.load()
    
    def load(self):
        try:
            with open(self.filepath) as f:
                self.symbols = json.load(f)
        except:
            self.symbols = {}
    
    def save(self):
        with open(self.filepath, 'w') as f:
            json.dump(self.symbols, f, indent=2)
    
    def record(self, symbol: str, profit_usd: float, sell_price: float = None):
        if symbol not in self.symbols:
            self.symbols[symbol] = {'trades': 0, 'wins': 0, 'profit': 0, 'last_time': 0, 'streak': 0, 'last_sell_price': 0}
        
        s = self.symbols[symbol]
        s['trades'] += 1
        s['profit'] += profit_usd
        s['last_time'] = time.time()
        if sell_price:
            s['last_sell_price'] = sell_price
        
        if profit_usd >= 0:
            s['wins'] += 1
            s['streak'] = 0
        else:
            s['streak'] += 1
        
        self.save()
    
    def should_avoid(self, symbol: str, current_price: float = None) -> Tuple[bool, str]:
        if symbol not in self.symbols:
            return False, ""
        s = self.symbols[symbol]
        
        # Cooldown check
        time_since_last = time.time() - s.get('last_time', 0)
        if time_since_last < CONFIG['COOLDOWN_MINUTES'] * 60:
            # RE-ENTRY PROTECTION: Don't buy back higher than we sold!
            # If we are within cooldown, we are extra strict.
            # But even after cooldown, we might want to be careful? 
            # User said: "selling a coing then buying the same one at a higher raate"
            # Let's enforce this strictly during the cooldown period.
            
            if current_price and s.get('last_sell_price'):
                if current_price > s.get('last_sell_price'):
                    return True, f"Price ${current_price:.4f} > Last Sell ${s['last_sell_price']:.4f}"
            
            return True, f"Cooldown ({int(time_since_last)}s < {CONFIG['COOLDOWN_MINUTES']*60}s)"
            
        if s.get('streak', 0) >= 3:
            return True, "Losing streak (3+)"
            
        return False, ""

# ═══════════════════════════════════════════════════════════════════════════
# LOT SIZE MANAGER
# ═══════════════════════════════════════════════════════════════════════════

class LotSizeManager:
    def __init__(self, client: BinanceClient):
        self.client = client
        self.cache = {}
        self.last_update = 0
    
    def update(self):
        if time.time() - self.last_update < 300: return
        try:
            info = self.client.exchange_info()
            for s in info['symbols']:
                sym = s['symbol']
                self.cache[sym] = {'status': s['status'], 'base': s['baseAsset'], 'quote': s['quoteAsset'], 'filters': {}}
                for f in s['filters']:
                    self.cache[sym]['filters'][f['filterType']] = f
            self.last_update = time.time()
        except Exception as e:
            logger.error(f"Exchange info error: {e}")
    
    def can_trade(self, symbol: str) -> bool:
        self.update()
        return self.cache.get(symbol, {}).get('status') == 'TRADING'
    
    def format_qty(self, symbol: str, qty: float) -> str:
        self.update()
        lot = self.cache.get(symbol, {}).get('filters', {}).get('LOT_SIZE', {})
        step = float(lot.get('stepSize', '0.001'))
        min_qty = float(lot.get('minQty', '0.001'))
        
        precision = len(str(step).rstrip('0').split('.')[-1]) if '.' in str(step) else 0
        qty_d = Decimal(str(qty))
        step_d = Decimal(str(step))
        formatted = (qty_d // step_d) * step_d
        formatted = max(Decimal(str(min_qty)), formatted)
        
        if precision == 0: return str(int(formatted))
        return f"{formatted:.{precision}f}"

# ═══════════════════════════════════════════════════════════════════════════
# COHERENCE CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════

def calculate_coherence(price_change_pct: float, volume_btc: float, volatility_pct: float) -> float:
    S = min(1.0, volume_btc / 50.0)
    O = min(1.0, abs(price_change_pct) / 15.0)
    E = min(1.0, volatility_pct / 25.0)
    Lambda = (S + O + E) / 3.0
    return 1 / (1 + math.exp(-5 * (Lambda - 0.5)))

# ═══════════════════════════════════════════════════════════════════════════
# UNIFIED TRADER
# ═══════════════════════════════════════════════════════════════════════════

class AureonUnifiedLive:
    def __init__(self):
        self.client = get_binance_client()
        self.lot_mgr = LotSizeManager(self.client)
        self.memory = ElephantMemory()
        self.spiral = spiral_memory  # 🌀 SPIRAL MEMORY INTEGRATION
        self.hnc = HNCProbabilityIntegration()  # HNC Probability Matrix
        
        self.positions = {}
        self.ticker_cache = {}
        self.last_ticker_update = 0
        
        # v6: Price history for spike detection
        self.price_history = {}  # symbol -> [(timestamp, price), ...]
        self.price_history_max = 60  # Keep 60 data points per symbol
        
        # v6: Peak price tracking for trailing stops
        self.peak_prices = {}  # symbol -> highest price since entry

        # Stats
        self.wins = 0
        self.trades = 0
        self.total_profit_usd = 0.0
        self.rejections = []

        # 🎹 Brain/Piano resonance cache
        self.brain_state_path = os.path.join(tempfile.gettempdir(), "aureon_multidimensional_brain_output.json")
        self.brain_cache = {}
        self.brain_cache_time = 0

    def load_brain_state(self) -> Dict:
        """Load cached Quantum Brain/Piano state if recently updated."""
        try:
            now = time.time()
            if now - self.brain_cache_time < 10:  # reuse for 10 seconds
                return self.brain_cache

            if not os.path.exists(self.brain_state_path):
                return {}

            mtime = os.path.getmtime(self.brain_state_path)
            if mtime <= 0:
                return {}

            with open(self.brain_state_path) as f:
                data = json.load(f)

            # Extract Piano + cascade fields when available
            piano = data.get('piano', {}) if isinstance(data, dict) else {}
            meta = data.get('meta', {}) if isinstance(data, dict) else {}
            cascade = meta.get('multiverse_cascade') or data.get('multiverse_cascade')

            self.brain_cache = {
                'piano_lambda': piano.get('lambda'),
                'piano_coherence': piano.get('coherence'),
                'rainbow_state': piano.get('rainbow_state'),
                'cascade': cascade,
                'timestamp': data.get('timestamp') or meta.get('timestamp'),
            }
            self.brain_cache_time = now
            return self.brain_cache
        except Exception as e:
            logger.debug(f"Brain state load failed: {e}")
            return {}
        
        # v6: Rejection logging for analysis
        self.rejections = []  # List of rejected opportunities with reasons
        self.rejection_log_file = 'rejection_log.json'
        
        self.trades = 0
        self.wins = 0
        self.total_profit_usd = 0.0
    
    def update_tickers(self):
        if time.time() - self.last_ticker_update < 2: return
        try:
            tickers = self.client.session.get(f"{self.client.base}/api/v3/ticker/24hr", timeout=5).json()
            allowed_quotes = tuple(CONFIG.get('ALLOWED_QUOTES', ['USDC']))
            self.ticker_cache = {t['symbol']: t for t in tickers if t['symbol'].endswith(allowed_quotes)}
            self.last_ticker_update = time.time()
            
            # v6: Update price history for spike detection
            now = time.time()
            for symbol, ticker in self.ticker_cache.items():
                price = float(ticker.get('lastPrice', 0))
                if price > 0:
                    if symbol not in self.price_history:
                        self.price_history[symbol] = []
                    self.price_history[symbol].append((now, price))
                    # Keep only recent history
                    cutoff = now - 120  # 2 minutes
                    self.price_history[symbol] = [
                        (t, p) for t, p in self.price_history[symbol] if t > cutoff
                    ][-self.price_history_max:]
        except Exception as e:
            logger.error(f"Ticker update failed: {e}")
    
    def detect_spike(self, symbol: str) -> Tuple[bool, float]:
        """v6: Detect if symbol had a recent price spike (pump/dump)"""
        if symbol not in self.price_history:
            return False, 0.0
        
        history = self.price_history[symbol]
        if len(history) < 3:
            return False, 0.0
        
        now = time.time()
        lookback = CONFIG.get('SPIKE_LOOKBACK_SEC', 30)
        threshold = CONFIG.get('SPIKE_THRESHOLD_PCT', 0.01)
        
        # Get prices from lookback window
        recent = [(t, p) for t, p in history if now - t <= lookback]
        if len(recent) < 2:
            return False, 0.0
        
        oldest_price = recent[0][1]
        newest_price = recent[-1][1]
        change_pct = abs(newest_price - oldest_price) / oldest_price
        
        is_spike = change_pct >= threshold
        return is_spike, change_pct
    
    def log_rejection(self, symbol: str, reason: str, details: Dict):
        """v6: Log rejected opportunities for analysis"""
        rejection = {
            'timestamp': time.time(),
            'symbol': symbol,
            'reason': reason,
            **details
        }
        self.rejections.append(rejection)
        
        # Keep only last 100 rejections in memory
        if len(self.rejections) > 100:
            self.rejections = self.rejections[-100:]
        
        # Log to file periodically (every 10 rejections)
        if len(self.rejections) % 10 == 0:
            try:
                with open(self.rejection_log_file, 'w') as f:
                    json.dump(self.rejections[-50:], f, indent=2)
            except:
                pass

    def _force_candidate(self) -> Optional[Dict]:
        """Pick a fallback candidate when FORCE_TRADE is enabled."""
        target = CONFIG.get('FORCE_TRADE_SYMBOL', '').strip().upper()
        candidates = []
        allowed_quotes = tuple(CONFIG.get('ALLOWED_QUOTES', ['USDC']))

        for symbol, ticker in self.ticker_cache.items():
            if not symbol.endswith(allowed_quotes):  # keep stable quotes only
                continue
            if target and symbol != target:
                continue
            try:
                price = float(ticker['lastPrice'])
                change = float(ticker['priceChangePercent'])
                volume = float(ticker['quoteVolume'])
                high = float(ticker['highPrice'])
                low = float(ticker['lowPrice'])
            except Exception:
                continue

            if volume < CONFIG.get('FORCE_MIN_VOLUME', 15000):
                continue  # still require a basic liquidity floor
            if price <= 0 or high <= 0 or low <= 0:
                continue

            volatility = ((high - low) / low * 100) if low > 0 else 0
            coherence = calculate_coherence(change, volume / price if price > 0 else 0, volatility)
            price_range_pct = (price - low) / (high - low) if (high - low) > 0 else 0.5
            freq = max(256, min(963, 432 * ((1 + change/100) ** ((1 + 5**0.5) / 2))))
            freq_band = 'OPTIMAL' if CONFIG['FREQ_OPTIMAL_MIN'] <= freq <= CONFIG['FREQ_OPTIMAL_MAX'] else 'STANDARD'

            score = volume * (1 + max(0.0, coherence)) * (1 + (1 - price_range_pct))
            candidates.append({
                'symbol': symbol,
                'price': price,
                'change': change,
                'coherence': coherence,
                'volume': volume,
                'probability': 0.55,  # nudge above neutral
                'action': 'FORCE BUY',
                'frequency': freq,
                'is_harmonic': False,
                'score': score,
                'freq_band': freq_band,
                'range_pct': price_range_pct,
            })

        if not candidates:
            return None

        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates[0]
    
    def get_usdc_balance(self) -> float:
        return self.client.get_free_balance('USDC')

    def get_all_balances(self) -> Dict[str, float]:
        """Get all non-zero balances for reconciliation"""
        try:
            acc = self.client.account()
            balances = {}
            for b in acc.get('balances', []):
                total = float(b['free']) + float(b['locked'])
                if total > 0:
                    balances[b['asset']] = total
            return balances
        except Exception as e:
            logger.error(f"Failed to get balances: {e}")
            return {}
    
    def scan_opportunities(self) -> List[Dict]:
        """v4 Enhanced opportunity scanner with learned frequency filters"""
        opportunities = []
        PHI = (1 + 5**0.5) / 2  # Golden ratio

        # 🎹 Brain/Piano resonance influence
        brain = self.load_brain_state()
        brain_mult = 1.0
        piano_coh = brain.get('piano_coherence') if isinstance(brain, dict) else None
        piano_lambda = brain.get('piano_lambda') if isinstance(brain, dict) else None
        rainbow_state = (brain.get('rainbow_state') or '').upper() if isinstance(brain, dict) else ''

        if piano_coh is not None:
            brain_mult *= 1.0 + max(0.0, piano_coh - 0.5) * 0.2  # Up to +10% boost
        if piano_lambda is not None and piano_lambda > 1.5:
            brain_mult *= 1.0 + (piano_lambda - 1.0) * 0.05  # Mild lambda boost

        rainbow_boost = {
            'UNITY': 1.10,
            'AWE': 1.07,
            'LOVE': 1.05,
            'RESONANCE': 1.03,
        }
        if rainbow_state in rainbow_boost:
            brain_mult *= rainbow_boost[rainbow_state]
        
        allowed_quotes = tuple(CONFIG.get('ALLOWED_QUOTES', ['USDC']))

        for symbol, ticker in self.ticker_cache.items():
            if not symbol.endswith(allowed_quotes): continue
            if not self.lot_mgr.can_trade(symbol): continue
            
            try:
                price = float(ticker['lastPrice'])
                
                # Check memory (cooldowns, re-entry protection)
                avoid, reason = self.memory.should_avoid(symbol, current_price=price)
                if avoid:
                    # logger.debug(f"Skipping {symbol}: {reason}")
                    continue
                
                change = float(ticker['priceChangePercent'])
                volume = float(ticker['quoteVolume'])
                high = float(ticker['highPrice'])
                low = float(ticker['lowPrice'])
                
                if volume < 10000: continue  # Min $10k volume
                
                volatility = ((high - low) / low * 100) if low > 0 else 0
                coherence = calculate_coherence(change, volume / price if price > 0 else 0, volatility)
                
                # v6: Tiered coherence - base threshold for entry, bonus for high coherence
                if coherence < CONFIG['COHERENCE_THRESHOLD']:
                    self.log_rejection(symbol, 'LOW_COHERENCE', {'coherence': coherence, 'threshold': CONFIG['COHERENCE_THRESHOLD']})
                    continue
                
                # Calculate frequency from price action (Solfeggio mapping)
                freq = max(256, min(963, 432 * ((1 + change/100) ** PHI)))
                is_harmonic = abs(freq - 528) < 30  # Near LOVE frequency
                
                # v6: FREQUENCY BAND FILTERING (LEARNED)
                # 750-963Hz (Intuition + Awakening) = 67% WR - PRIORITIZE
                # 450-550Hz (Transformation) = 27% WR - AVOID
                freq_score = 0
                in_optimal_band = CONFIG['FREQ_OPTIMAL_MIN'] <= freq <= CONFIG['FREQ_OPTIMAL_MAX']
                in_avoid_band = CONFIG['FREQ_AVOID_MIN'] <= freq <= CONFIG['FREQ_AVOID_MAX']
                
                if in_avoid_band:
                    self.log_rejection(symbol, 'FREQ_AVOID_BAND', {'freq': freq})
                    continue  # Skip poor-performing frequency band
                
                # v6: Frequency scoring with bonus for optimal band
                if in_optimal_band:
                    freq_score = 100  # Strong bonus for 750-963Hz
                elif freq > 650:  # Above 650Hz is decent
                    freq_score = 50
                else:
                    freq_score = 25  # Lower frequencies underperform
                
                # Generate HNC Probability Matrix
                matrix = self.hnc.update_and_analyze(
                    symbol=symbol,
                    price=price,
                    frequency=freq,
                    momentum=change,
                    coherence=coherence,
                    is_harmonic=is_harmonic,
                    volume=volume
                )
                
                signal = self.hnc.get_trading_signal(symbol)
                prob = signal['probability']
                action = signal['action']
                
                # v6: Adaptive probability thresholds (learned: 0.78-0.83 sweet spot)
                prob_min = CONFIG.get('PROB_MIN', 0.50)
                prob_cap = CONFIG.get('PROB_CAP', 0.83)
                
                if prob < prob_min:
                    self.log_rejection(symbol, 'LOW_PROBABILITY', {'prob': prob, 'min': prob_min})
                    continue
                if prob > prob_cap:
                    prob = prob_cap  # Cap overconfident signals (0.85+ had 0% WR!)
                
                # v6: MOMENTUM CONFIRMATION - Don't buy at local highs
                # Require price to be in lower 70% of daily range (not overbought)
                price_range_pct = (price - low) / (high - low) if (high - low) > 0 else 0.5
                if price_range_pct > 0.75:
                    self.log_rejection(symbol, 'OVERBOUGHT', {'range_pct': price_range_pct, 'price': price})
                    continue  # Skip - price is in upper 25% of daily range (overbought)
                
                # v6: Widened momentum range based on paper trade analysis
                # Paper winners ranged from -3.5% to +10%, avoid extremes beyond that
                if change > 10.0 or change < -5.0:
                    self.log_rejection(symbol, 'MOMENTUM_EXTREME', {'change': change})
                    continue
                
                # v6: SPIKE DETECTION - Don't chase pumps
                is_spike, spike_magnitude = self.detect_spike(symbol)
                if is_spike:
                    self.log_rejection(symbol, 'SPIKE_DETECTED', {'spike_pct': spike_magnitude * 100})
                    continue
                
                # Entry criteria: HNC says BUY + High coherence + Good frequency
                if action in ['STRONG BUY', 'BUY', 'SLIGHT BUY']:
                    # v6: Score includes momentum quality and distance from high
                    base_score = prob * coherence * (1 + math.log10(max(1, volume/10000)))
                    freq_bonus = freq_score / 100  # 0-1 range
                    range_bonus = (1 - price_range_pct)  # Bonus for buying low in range
                    score = base_score * (1 + freq_bonus) * (1 + range_bonus * 0.5)
                    score *= brain_mult  # 🎹 Piano resonance boost
                    
                    # v6: Symbol preference bonus (proven edge symbols)
                    if symbol in CONFIG.get('PREFERRED_SYMBOLS', []):
                        score *= CONFIG.get('PREFERRED_BONUS', 1.5)
                    
                    opportunities.append({
                        'symbol': symbol,
                        'price': price,
                        'change': change,
                        'coherence': coherence,
                        'volume': volume,
                        'probability': prob,
                        'action': action,
                        'frequency': freq,
                        'is_harmonic': is_harmonic,
                        'score': score,
                        'freq_band': 'OPTIMAL' if in_optimal_band else 'STANDARD',
                        'range_pct': price_range_pct,  # v5: Track position in range
                    })
            except:
                continue
        
        # v5: Sort by frequency band, then range position, then score
        opportunities.sort(key=lambda x: (
            x.get('freq_band') == 'OPTIMAL', 
            -x.get('range_pct', 0.5),  # Lower range = better (negative for descending)
            x['score']
        ), reverse=True)

        # Force mode: if nothing qualifies, pick the best minimally-filtered candidate
        if not opportunities and CONFIG.get('FORCE_TRADE', False):
            forced = self._force_candidate()
            if forced:
                logger.warning(f"FORCE_TRADE active - bypassing gates with {forced['symbol']}")
                opportunities.append(forced)
        return opportunities
    
    def enter_position(self, opp: Dict, usdc_balance: float) -> bool:
        symbol = opp['symbol']
        coherence = opp.get('coherence', 0.70)
        
        # v6: Adaptive position sizing with coherence scaling
        # Base: 20% | Optimal freq: +15% | High coherence: +10% | Preferred symbol: +10%
        base_size_pct = 0.20
        
        # Frequency band bonus
        if opp.get('freq_band') == 'OPTIMAL':
            base_size_pct += 0.15  # +15% for 750-963Hz band
        
        # Coherence scaling (v6 new)
        if CONFIG.get('COHERENCE_SCALING', True):
            optimal_coh = CONFIG.get('COHERENCE_OPTIMAL', 0.88)
            threshold_coh = CONFIG.get('COHERENCE_THRESHOLD', 0.70)
            coh_factor = (coherence - threshold_coh) / (optimal_coh - threshold_coh)
            coh_factor = max(0.5, min(1.0, coh_factor))  # 0.5x to 1.0x
            base_size_pct *= coh_factor
        elif coherence >= 0.88:
            base_size_pct += 0.10  # +10% for high coherence
        
        # Preferred symbol bonus (SAPIEN has 67% WR)
        if symbol in CONFIG.get('PREFERRED_SYMBOLS', []):
            base_size_pct += 0.10  # +10% for proven winners
        
        # 🎹 Brain/Piano resonance sizing boost
        brain = self.load_brain_state()
        brain_mult = 1.0
        if isinstance(brain, dict):
            piano_coh = brain.get('piano_coherence')
            piano_lambda = brain.get('piano_lambda')
            rainbow_state = (brain.get('rainbow_state') or '').upper()
            if piano_coh is not None:
                brain_mult *= 1.0 + max(0.0, piano_coh - 0.5) * 0.2  # up to +10%
            if piano_lambda is not None and piano_lambda > 1.5:
                brain_mult *= 1.0 + (piano_lambda - 1.0) * 0.05       # mild lambda boost
            rainbow_boost = {
                'UNITY': 1.10,
                'AWE': 1.07,
                'LOVE': 1.05,
                'RESONANCE': 1.03,
            }
            if rainbow_state in rainbow_boost:
                brain_mult *= rainbow_boost[rainbow_state]

        # Cap at 45% max position size
        size_pct = min(0.45, base_size_pct * brain_mult)
        
        size_usd = usdc_balance * size_pct
        if size_usd < CONFIG['MIN_TRADE_USD']:
            return False
        
        qty = size_usd / opp['price']
        qty_str = self.lot_mgr.format_qty(symbol, qty)
        
        notional = float(qty_str) * opp['price']
        if notional < CONFIG['MIN_TRADE_USD']:
            return False
        
        logger.info(f"""
+================================================================+
| [ENTRY] {symbol}
| HNC Prob: {opp.get('probability', 0):.0%} | Action: {opp.get('action', 'N/A')}
| Coherence: G={coherence:.3f} | Freq: {opp.get('frequency', 0):.0f}Hz
| Size: {size_pct*100:.0f}% = ${notional:.2f} ({qty_str} @ ${opp['price']:.4f})
| Band: {opp.get('freq_band', 'STANDARD')} | Range: {opp.get('range_pct', 0)*100:.0f}%
+================================================================+
""")
        
        try:
            result = self.client.place_market_order(symbol, 'BUY', quantity=float(qty_str))
            
            # 🌀 SPIRAL MEMORY: Remember this moment
            self.spiral.remember_trade(
                symbol=symbol,
                exchange='Binance',
                entry_price=opp['price'],
                quantity=float(qty_str),
                side='BUY'
            )
            
            self.positions[symbol] = {
                'entry': opp['price'],
                'qty': float(qty_str),
                'entry_time': time.time(),
                'notional': notional,
                'peak_price': opp['price'],  # v6: Track peak for trailing stop
            }
            logger.info(f"[OK] Filled: Order #{result.get('orderId')}")
            self.trades += 1
            return True
        except Exception as e:
            logger.error(f"[FAIL] Buy failed: {e}")
            return False
    
    def check_exits(self):
        for symbol in list(self.positions.keys()):
            pos = self.positions[symbol]
            ticker = self.ticker_cache.get(symbol)
            if not ticker: continue
            
            price = float(ticker['lastPrice'])
            
            # 🌀 SPIRAL MEMORY: Update reality
            self.spiral.update_position(symbol, price)
            if self.spiral.get_spiral_check_needed(symbol):
                logger.info(f"🌀 Spiral Checkpoint reached for {symbol}. Validating probability matrix...")
                # TODO: Trigger deep HNC re-validation here if needed
            
            entry = pos['entry']
            pnl_pct = (price - entry) / entry
            pnl_usd = pos['qty'] * price * pnl_pct
            
            # v6: Update peak price for trailing stop
            if symbol not in self.peak_prices:
                self.peak_prices[symbol] = price
            elif price > self.peak_prices[symbol]:
                self.peak_prices[symbol] = price
            
            should_exit = False
            reason = ""
            
            # v6: TRAILING STOP - Lock in profits!
            if CONFIG.get('ENABLE_TRAILING_STOP', True):
                peak = self.peak_prices.get(symbol, price)
                peak_pnl_pct = (peak - entry) / entry
                
                # Activate trailing stop after reaching activation threshold
                if peak_pnl_pct >= CONFIG.get('TRAIL_ACTIVATION_PCT', 0.008):
                    trail_distance = CONFIG.get('TRAIL_DISTANCE_PCT', 0.005)
                    trail_price = peak * (1 - trail_distance)
                    
                    if price <= trail_price:
                        should_exit = True
                        reason = f"[TRAIL] TRAILING STOP (Peak: ${peak:.4f}, Trail: ${trail_price:.4f})"
            
            # Standard exits (only if trailing didn't trigger)
            if not should_exit:
                if pnl_pct >= CONFIG['TAKE_PROFIT_PCT']:
                    should_exit = True
                    reason = "[TP] TAKE PROFIT"
                elif pnl_pct <= -CONFIG['STOP_LOSS_PCT']:
                    should_exit = True
                    reason = "[SL] STOP LOSS"
                elif time.time() - pos['entry_time'] > CONFIG['TIMEOUT_SEC']:  # v4: Configurable timeout
                    should_exit = True
                    reason = "[TIME] TIMEOUT"
            
            if should_exit:
                # v4 FIX: Get actual balance from exchange for sells
                # This handles dust and ensures we sell what we actually have
                base_asset = symbol.replace('USDC', '').replace('USDT', '')
                actual_balance = self.client.get_free_balance(base_asset)
                
                # Use actual balance if available, otherwise use stored qty
                sell_qty = actual_balance if actual_balance > 0 else pos['qty']
                qty_str = self.lot_mgr.format_qty(symbol, sell_qty)
                
                # Verify notional is above minimum
                sell_notional = float(qty_str) * price
                if sell_notional < 5.0:  # Binance minimum
                    logger.warning(f"[WARN] {symbol} notional ${sell_notional:.2f} below $5 minimum - skipping sell")
                    continue
                
                logger.info(f"""
+================================================================+
| [EXIT] {symbol}
| Reason: {reason}
| Entry: ${entry:.4f} | Exit: ${price:.4f}
| Qty: {qty_str} (Balance: {actual_balance:.4f})
| P&L:   {pnl_pct*100:+.2f}% (${pnl_usd:+.2f})
+================================================================+
""")
                
                try:
                    result = self.client.place_market_order(symbol, 'SELL', quantity=float(qty_str))
                    logger.info(f"[OK] Sold: Order #{result.get('orderId')}")
                    
                    # Record trade with sell price for re-entry protection
                    self.memory.record(symbol, pnl_usd, sell_price=price)
                    
                    # 🌀 SPIRAL MEMORY: Close the loop
                    self.spiral.close_position(symbol, price, reason)
                    
                    self.total_profit_usd += pnl_usd
                    if pnl_usd >= 0:
                        self.wins += 1
                        # 🇮🇪 IRA SNIPER CELEBRATION!
                        import random
                        IRA_QUOTES = [
                            "Our revenge will be the laughter of our children. - Bobby Sands 🍀",
                            "Tiocfaidh ár lá! - Our day will come!",
                            "The Republic still lives! - Bobby Sands",
                            "Financial freedom IS freedom. Penny by penny, we rise! 💰",
                        ]
                        quote = random.choice(IRA_QUOTES)
                        print(f"\n🇮🇪🇮🇪🇮🇪 IRA SNIPER WIN! 🇮🇪🇮🇪🇮🇪")
                        print(f"    💰 +${pnl_usd:.4f} on {symbol}")
                        print(f"    📜 \"{quote}\"")
                        print(f"🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪\n")
                    
                    # v6: Clear peak price tracking
                    if symbol in self.peak_prices:
                        del self.peak_prices[symbol]
                    
                    del self.positions[symbol]
                except Exception as e:
                    logger.error(f"[FAIL] Sell failed: {e}")
    
    def display_status(self, cycle: int):
        usdc = self.get_usdc_balance()
        pos_value = sum(float(self.ticker_cache.get(s, {}).get('lastPrice', 0)) * p['qty'] 
                       for s, p in self.positions.items())
        total = usdc + pos_value
        
        win_rate = self.wins / max(1, self.trades) * 100
        
        # v6: Show trailing stop status for open positions
        trail_info = ""
        for sym, pos in self.positions.items():
            peak = self.peak_prices.get(sym, pos['entry'])
            curr = float(self.ticker_cache.get(sym, {}).get('lastPrice', pos['entry']))
            peak_pnl = (peak - pos['entry']) / pos['entry'] * 100
            curr_pnl = (curr - pos['entry']) / pos['entry'] * 100
            trail_info += f"\n|   {sym}: Entry ${pos['entry']:.4f} | Peak +{peak_pnl:.2f}% | Now {curr_pnl:+.2f}%"
        
        logger.info(f"""
+================================================================+
| * AUREON UNIFIED v6 | Cycle {cycle:3d}
|----------------------------------------------------------------
| [USDC] USDC:      ${usdc:.2f}
| [POS]  Positions: ${pos_value:.2f} ({len(self.positions)}){trail_info}
| [TOT]  Total:     ${total:.2f}
|----------------------------------------------------------------
| [TRD]  Trades: {self.trades} | Wins: {self.wins} | WR: {win_rate:.1f}%
| [P&L]  Profit: ${self.total_profit_usd:+.2f}
| [REJ]  Rejections: {len(self.rejections)} (last cycle)
+================================================================+
""")
    
    def _fetch_origin_trade(self, asset: str) -> Optional[Dict]:
        """Callback for Spiral Memory to find trade origin"""
        # Try common pairs
        for quote in ['USDC', 'USDT']:
            symbol = f"{asset}{quote}"
            try:
                trades = self.client.get_my_trades(symbol)
                if trades:
                    # Find last buy
                    buys = [t for t in trades if t['isBuyer']]
                    if buys:
                        last_buy = buys[-1]
                        return {
                            'symbol': symbol,
                            'exchange': 'Binance',
                            'price': float(last_buy['price']),
                            'date': datetime.fromtimestamp(last_buy['time']/1000).strftime('%Y-%m-%d %H:%M:%S'),
                            'timestamp': last_buy['time']/1000
                        }
            except:
                pass
        return None

    def run(self, duration_sec: int = 3600):
        logger.info("""
+================================================================+
|        * AUREON UNIFIED LIVE TRADER v6.1 *
|
|  ALL SYSTEMS INTEGRATED:
|    * HNC Probability Matrix
|    * Solfeggio Frequency Mapping (750-963Hz optimal)
|    * Tiered Coherence (0.70 base, 0.88 optimal)
|    * Elephant Memory (Symbol learning)
|    * Spiral Memory (State persistence) 🌀
|    * Trailing Stops (Lock in +0.8% gains)
|    * Spike Detection (Avoid pump entries)
|    * Near-Miss Monitoring (Watch list)
|
+================================================================+
""")
        
        # 🌀 SPIRAL RECONCILIATION
        logger.info("🌀 Synchronizing with Spiral Memory...")
        self.spiral.reconcile_with_reality(
            self.get_all_balances(),
            self._fetch_origin_trade
        )
        
        # Load reconciled positions into local state
        for sym, pos in self.spiral.positions.items():
            if sym not in self.positions and pos['status'] == 'OPEN':
                self.positions[sym] = {
                    'entry': pos['entry_price'],
                    'qty': pos['quantity'],
                    'entry_time': pos['entry_time'],
                    'notional': pos['entry_price'] * pos['quantity'],
                    'peak_price': pos.get('highest_price', pos['entry_price'])
                }
                logger.info(f"🌀 Restored {sym} from Spiral Memory (Entry: ${pos['entry_price']:.4f})")

        start = time.time()
        cycle = 0
        
        while time.time() - start < duration_sec:
            cycle += 1
            
            self.update_tickers()
            self.display_status(cycle)
            
            # Check exits
            self.check_exits()
            
            # Scan and enter
            if len(self.positions) < CONFIG['MAX_POSITIONS']:
                opps = self.scan_opportunities()
                
                if opps:
                    logger.info(f"\n[SCAN] Top 3 HNC Opportunities:")
                    for i, opp in enumerate(opps[:3]):
                        harmonic = "[H]" if opp.get('is_harmonic') else ""
                        logger.info(f"  {i+1}. {opp['symbol']}: P={opp['probability']:.0%} | G={opp['coherence']:.3f} | {opp['action']} {harmonic}")
                    
                    usdc = self.get_usdc_balance()
                    if usdc >= CONFIG['MIN_TRADE_USD']:
                        self.enter_position(opps[0], usdc)
                else:
                    # v6.1: Show near-miss opportunities (watching list)
                    self.show_watch_list()
            
            time.sleep(10)
        
        logger.info(f"""
+================================================================+
| [FIN] SESSION COMPLETE
| Trades: {self.trades} | Wins: {self.wins} | WR: {self.wins/max(1,self.trades)*100:.1f}%
| Total P&L: ${self.total_profit_usd:+.2f}
+================================================================+
""")
    
    def show_watch_list(self):
        """Show assets that are close to passing filters - potential future entries"""
        watch = []
        PHI = (1 + 5**0.5) / 2
        
        for symbol, ticker in self.ticker_cache.items():
            if not symbol.endswith('USDC'): continue
            try:
                price = float(ticker['lastPrice'])
                change = float(ticker['priceChangePercent'])
                volume = float(ticker['quoteVolume'])
                high = float(ticker['highPrice'])
                low = float(ticker['lowPrice'])
                
                if volume < 10000: continue
                
                volatility = ((high - low) / low * 100) if low > 0 else 0
                coh = calculate_coherence(change, volume / price if price > 0 else 0, volatility)
                
                if coh < 0.65: continue  # At least close to threshold
                
                freq = max(256, min(963, 432 * ((1 + change/100) ** PHI)))
                in_avoid = CONFIG['FREQ_AVOID_MIN'] <= freq <= CONFIG['FREQ_AVOID_MAX']
                in_optimal = CONFIG['FREQ_OPTIMAL_MIN'] <= freq <= CONFIG['FREQ_OPTIMAL_MAX']
                
                range_pct = (price - low) / (high - low) if (high - low) > 0 else 0.5
                
                # Count how many filters it passes (out of 5)
                passes = 0
                if coh >= CONFIG['COHERENCE_THRESHOLD']: passes += 1
                if not in_avoid: passes += 1
                if -5.0 <= change <= 10.0: passes += 1
                if range_pct <= 0.75: passes += 1
                if in_optimal: passes += 1
                
                if passes >= 3:  # Show if passing at least 3/5 filters
                    watch.append({
                        'symbol': symbol,
                        'coherence': coh,
                        'freq': freq,
                        'change': change,
                        'range_pct': range_pct,
                        'passes': passes,
                        'in_optimal': in_optimal,
                        'in_avoid': in_avoid,
                    })
            except:
                continue
        
        if watch:
            watch.sort(key=lambda x: (-x['passes'], -x['coherence']))
            logger.info(f"\n[WATCH] WATCH LIST ({len(watch)} near-miss):")
            for w in watch[:5]:
                freq_status = "[!]OPTIMAL" if w['in_optimal'] else ("[X]AVOID" if w['in_avoid'] else "OK")
                # Use 'G' instead of Gamma symbol for Windows compatibility
                logger.info(f"  {w['symbol']}: G={w['coherence']:.2f} | {w['freq']:.0f}Hz ({freq_status}) | {w['change']:+.1f}% | {w['passes']}/5 filters")

if __name__ == "__main__":
    trader = AureonUnifiedLive()
    trader.run(duration_sec=300)  # 5 min test
