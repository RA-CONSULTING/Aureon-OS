#!/usr/bin/env python3
"""
🌌 AUREON ULTIMATE - THE ONE TRADER TO RULE THEM ALL 🌌
======================================================

ALL 27 SYSTEMS UNIFIED INTO ONE BIG PYTHON:

  ✨ Master Equation Λ(t) = S(t) + O(t) + E(t) [the_play]
  ✨ 9 Auris Nodes with proper weighting [the_play]
  ✨ Elephant Memory (cooldowns + blacklisting) [btc_v2]
  ✨ Fire Starter (intensity scaling) [btc_v2]
  ✨ Rainbow Bridge (emotional frequencies) [btc_v2]
  ✨ Ping-Pong Engine (momentum building) [multiverse]
  ✨ Temporal Reader (Past/Present/Future) [multiverse]
  ✨ 10-9-1 Queen Hive (90% compound / 10% harvest) [infinite]
  ✨ QGITA Engine (Fibonacci lattice) [qgita]
  ✨ Decision Fusion (4-model ensemble) [tsx_trader]
  ✨ **PROPER LOT_SIZE** (precision handling) [FIXED!]

ONE SYSTEM. ALL THE POWER. NO MORE SNAKES.

Gary Leckey | November 2025
"We're making history! If you don't quit, you can't lose!" 🎵
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os, sys, time, math, json, logging, hmac, hashlib, random
from collections import Counter, deque
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal, ROUND_DOWN
from dataclasses import dataclass, field
from aureon.exchanges.binance_client import BinanceClient, get_binance_client
try:
    from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
except Exception:
    KrakenClient = None
from aureon.trading.aureon_commandos import QuackCommandos  # 🦆⚔️ THE ANIMAL ARMY
from aureon.wisdom.aureon_plums_guardian import PlumsGuardian, GuardianLimits  # 🇬🇧💎 UK SAFETY!
from aureon.intelligence.aureon_advanced_intelligence import AdvancedIntelligence, calculate_golden_ratio_alignment  # 🧠💎 THE MISSING PIECES!
from aureon.analytics.lighthouse_metrics import LighthouseMetricsEngine

# 🌉 BRIDGE INTEGRATION 🌉
try:
    from aureon.bridges.aureon_bridge import AureonBridge, Opportunity as BridgeOpportunity, CapitalState, Position as BridgePosition
    BRIDGE_AVAILABLE = True
except ImportError as e:
    BRIDGE_AVAILABLE = False
    # logger not defined yet, use print
    print(f"⚠️ Aureon Bridge not available: {e}")

# 🌌⚡ IMPERIAL PREDICTABILITY ENGINE ⚡🌌
try:
    from aureon.strategies.hnc_imperial_predictability import (
        ImperialTradingIntegration, PredictabilityEngine, CosmicStateEngine,
        CosmicPhase, MarketTorque, ImperialPredictabilityMatrix
    )
    IMPERIAL_AVAILABLE = True
except ImportError as e:
    IMPERIAL_AVAILABLE = False
    print(f"⚠️ Imperial Predictability not available: {e}")

# 🌌⚡ IMPERIAL PREDICTABILITY ENGINE ⚡🌌
try:
    from aureon.strategies.hnc_imperial_predictability import (
        ImperialTradingIntegration, CosmicPhase, MarketTorque
    )
    IMPERIAL_AVAILABLE = True
except ImportError as e:
    IMPERIAL_AVAILABLE = False
    print(f"⚠️ Imperial Predictability not available: {e}")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('aureon_ultimate.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION - UNIFIED (Enhanced with Quantum Quackers wisdom!)
# ═══════════════════════════════════════════════════════════════════════════

CONFIG = {
    # Entry/Exit (DecisionFusion from Quackers)
    'ENTRY_COHERENCE': 0.50,      # 🦆💎 BIG PLUMS MODE - AGGRESSIVE!
    'EXIT_COHERENCE': 0.40,       # Exit before coherence collapses
    'STOP_LOSS_MULTIPLIER': 1.2,  # Volatility-based stop (Quackers style)
    'REWARD_RISK_BASE': 2.0,      # R:R ratio for TP calculation
    
    # Position Management - DYNAMIC COMMANDO ECOSYSTEM
    # 7 total slots dynamically allocated to commandos
    # Each commando gets reserved slots that can be borrowed when idle
    'MAX_POSITIONS': 7,           # Total slots for the ecosystem
    'MIN_TRADE_NOTIONAL': 5.5,    # Binance requires $5 for most pairs
    'POSITION_SIZE_PCT': 0.12,    # 12% per trade = 7 positions, 16% reserve
    'PRIME_SCALE': 1.00,          # Prime multiplier 🦆💎 NO MORE TINY SIZES!
    
    # 🦆⚔️ COMMANDO ECOSYSTEM SLOTS ⚔️🦆
    # Each commando has reserved slots + can borrow from idle commandos
    'LION_SLOTS': 3,              # 🦁 Lion: Pride hunting (coherence-based)
    'WOLF_SLOTS': 2,              # 🐺 Wolf: Momentum sniping
    'ANTS_SLOTS': 1,              # 🐜 Ants: Floor scavenging
    'HUMMINGBIRD_SLOTS': 1,       # 🐝 Hummingbird: Quick rotations
    'ALLOW_SLOT_BORROWING': True, # Allow commandos to borrow idle slots
    'PRIMARY_QUOTE': 'USDC',      # Default spend asset for entries
    'TARGET_QUOTES': ['USDC', 'LDUSDC', 'BTC', 'BNB', 'ETH', 'EUR', 'USD', 'USDT'],  # Preferred quote assets (LDUSDC = Binance Earn)
    'PARTIAL_TP_PCT': 0.003,      # Trim half once +0.3% unrealized (floor = +0.1% net after fees)
    
    # Memory & Timing (Fibonacci from QGITA)
    'COOLDOWN_MINUTES': 13,       # Fibonacci timing
    'LOSS_STREAK_LIMIT': 3,
    'POSITION_TIMEOUT_SEC': 1440, # 24 minutes (Fibonacci)
    
    # Queen Hive (10-9-1)
    'COMPOUND_PCT': 0.90,         # 90% reinvest
    'HARVEST_PCT': 0.10,          # 10% secure
    'TAKER_FEE_PCT': 0.001,       # Approximate taker fee (0.10%)
    'BUSINESS_GREEN_THRESHOLD': 0.0,  # Net profit needed before closing trades
    'BUSINESS_GREEN_TOLERANCE': 0.25,  # Allow small negative realized PnL before gating exits
    
    # Decision Fusion Weights (from Quackers)
    'ENSEMBLE_WEIGHT': 0.6,
    'SENTIMENT_WEIGHT': 0.2,
    'COHERENCE_WEIGHT': 0.2,
    
    # 🌌⚡ Imperial Predictability Engine ⚡🌌
    'ENABLE_IMPERIAL': os.getenv('ENABLE_IMPERIAL', '1') == '1',
    'IMPERIAL_POSITION_WEIGHT': 0.30,   # Weight of imperial modifier in sizing
    'IMPERIAL_MIN_COHERENCE': 0.40,     # Minimum cosmic coherence to trade
    'IMPERIAL_DISTORTION_LIMIT': 0.20,  # Max distortion before halting
    'IMPERIAL_COSMIC_BOOST': True,      # Apply cosmic phase boost
}

PNL_BASELINE_FILE = "pnl_baseline.json"

# ═══════════════════════════════════════════════════════════════════════════
# EMOTIONAL FREQUENCIES (Rainbow Bridge)
# ═══════════════════════════════════════════════════════════════════════════

EMOTIONAL_FREQUENCIES = {
    'Fear': 174, 'Doubt': 330, 'Worry': 396, 'Hope': 412.3,
    'LOVE': 528, 'Harmony': 582, 'Flow': 693, 'Clarity': 819, 'Awe': 963,
}

def get_emotional_state(coherence: float) -> Tuple[str, float]:
    """Map coherence to emotional frequency"""
    freq = 174 + (coherence * (963 - 174))
    emotions = [(abs(freq - f), name) for name, f in EMOTIONAL_FREQUENCIES.items()]
    return min(emotions)[1], freq

# ═══════════════════════════════════════════════════════════════════════════
# ELEPHANT MEMORY
# ═══════════════════════════════════════════════════════════════════════════

class ElephantMemory:
    """
    Enhanced Elephant Memory from Quantum Quackers
    Tracks hunts + results with JSONL history.
    Integrates collective intelligence from all ecosystem agents.
    """
    
    def __init__(self, filepath: str = 'elephant_ultimate.json'):
        self.filepath = filepath
        self.history_path = filepath.replace('.json', '_history.jsonl')
        self.symbols = {} # Local memory
        self.collective_symbols = {} # Collective memory
        self.memory_sources = [
            'elephant_unified.json',
            'elephant_live.json'
        ]
        self.load()
    
    def load(self):
        # 1. Load local memory
        try:
            with open(self.filepath) as f:
                self.symbols = json.load(f)
        except:
            self.symbols = {}
            
        # 2. Load and aggregate collective memory
        self.collective_symbols = {}
        for source in self.memory_sources:
            if not os.path.exists(source):
                continue
            try:
                with open(source, 'r') as f:
                    data = json.load(f)
                    for sym, stats in data.items():
                        if sym not in self.collective_symbols:
                            self.collective_symbols[sym] = stats.copy()
                        else:
                            # Merge critical stats
                            s = self.collective_symbols[sym]
                            s['blacklisted'] = s.get('blacklisted', False) or stats.get('blacklisted', False)
                            s['streak'] = max(s.get('streak', 0), stats.get('streak', 0))
                            s['losses'] = s.get('losses', 0) + stats.get('losses', 0)
            except Exception as e:
                logger.warning(f"⚠️ Error loading collective memory from {source}: {e}")
    
    def save(self):
        with open(self.filepath, 'w') as f:
            json.dump(self.symbols, f, indent=2)
    
    def record_hunt(self, symbol: str, volume: float = 0, change: float = 0):
        """Remember we hunted this symbol (Quackers style)"""
        if symbol not in self.symbols:
            self.symbols[symbol] = {
                'hunts': 0, 'trades': 0, 'wins': 0, 'losses': 0,
                'profit': 0, 'last_time': 0, 'streak': 0, 'blacklisted': False
            }
        
        s = self.symbols[symbol]
        s['hunts'] = s.get('hunts', 0) + 1
        s['last_time'] = time.time()
        
        # Append to JSONL history
        try:
            with open(self.history_path, 'a') as f:
                record = {
                    'ts': datetime.now().isoformat(),
                    'type': 'hunt',
                    'symbol': symbol,
                    'volume': volume,
                    'change': change
                }
                f.write(json.dumps(record) + '\n')
        except:
            pass
        
        self.save()
    
    def record(self, symbol: str, profit_usd: float):
        """Record trade result"""
        if symbol not in self.symbols:
            self.symbols[symbol] = {
                'hunts': 0, 'trades': 0, 'wins': 0, 'losses': 0,
                'profit': 0, 'last_time': 0, 'streak': 0, 'blacklisted': False
            }
        
        s = self.symbols[symbol]
        s['trades'] += 1
        s['profit'] += profit_usd
        s['last_time'] = time.time()
        
        if profit_usd >= 0:
            s['wins'] += 1
            s['streak'] = 0
        else:
            s['losses'] += 1
            s['streak'] += 1
            if s['streak'] >= CONFIG['LOSS_STREAK_LIMIT']:
                s['blacklisted'] = True
                logger.warning(f"🚫 {symbol} BLACKLISTED after {s['streak']} losses")
        
        # Append to JSONL history
        try:
            with open(self.history_path, 'a') as f:
                record = {
                    'ts': datetime.now().isoformat(),
                    'type': 'result',
                    'symbol': symbol,
                    'profit': profit_usd
                }
                f.write(json.dumps(record) + '\n')
        except:
            pass
        
        self.save()
    
    def should_avoid(self, symbol: str) -> bool:
        # Check local memory
        if self._check_avoid(self.symbols.get(symbol)):
            return True
            
        # Check collective memory
        if self._check_avoid(self.collective_symbols.get(symbol)):
            return True
            
        return False
        
    def _check_avoid(self, s: dict) -> bool:
        if not s: return False
        
        # Blacklisted
        if s.get('blacklisted', False):
            return True
        
        # Cooldown
        if s.get('trades', 0) > 0 and time.time() - s.get('last_time', 0) < CONFIG['COOLDOWN_MINUTES'] * 60:
            return True
        
        return False
    
    def get_win_rate(self) -> float:
        total_wins = sum(s.get('wins', 0) for s in self.symbols.values())
        total_losses = sum(s.get('losses', 0) for s in self.symbols.values())
        if total_wins + total_losses == 0:
            return 0.55  # Default 55% (Quackers RiskManager default)
        return total_wins / (total_wins + total_losses)

# ═══════════════════════════════════════════════════════════════════════════
# FIRE STARTER (Enhanced from Quantum Quackers!)
# ═══════════════════════════════════════════════════════════════════════════

class FireStarter:
    """
    THE FIRE STARTER — BRING THE SMOKE, LIGHT THE FIRE 🔥
    From Quantum Quackers core/theFireStarter.ts
    """
    
    def __init__(self):
        self.temperature = 412.3  # Hope frequency
        self.intensity = 0.1      # Start as SPARK
        self.smoke_level = 0.1
        self.flame_height = 0.2
        self.resonance = 1.0
        self.time = 0
    
    def update(self, volatility: float, win_rate: float, trades_this_cycle: int = 0):
        """Update fire based on market conditions + trading activity"""
        self.time += 1
        
        # Temperature rises with volatility and time
        self.temperature = 412.3 + (volatility * 550) + math.sin(self.time * 0.1) * 50
        
        # Intensity from win rate + activity
        activity_boost = min(0.3, trades_this_cycle * 0.1)
        self.intensity = min(1.0, max(0.1, win_rate + activity_boost))
        
        # Smoke follows intensity
        self.smoke_level = self.intensity * 0.8
        
        # Flame height pulses with resonance
        self.flame_height = self.intensity * (1 + 0.3 * math.sin(self.time * 0.5))
    
    def get_status(self) -> str:
        if self.intensity >= 1.0: return '🔥 SUPERNOVA 🔥'
        if self.intensity >= 0.85: return '🔥 INFERNO 🔥'
        if self.intensity >= 0.6: return '🔥 BLAZING'
        if self.intensity >= 0.3: return '🔥 FLAME'
        return '✨ SPARK'
    
    def get_size_multiplier(self) -> float:
        """0.65x to 1.5x based on intensity + flame height - floor ensures $5+ min notional"""
        raw = 0.5 + (self.intensity * self.flame_height)
        return max(0.65, raw)  # Floor at 0.65x to ensure positions hit $5 min notional

# ═══════════════════════════════════════════════════════════════════════════
# LOT SIZE MANAGER - THE FIX!
# ═══════════════════════════════════════════════════════════════════════════

class LotSizeManager:
    """Handles Binance LOT_SIZE precision properly"""
    
    def __init__(self, client: BinanceClient):
        self.client = client
        self.cache = {}
        self.last_update = 0
    
    def update(self):
        if time.time() - self.last_update < 300:
            return
        try:
            info = self.client.exchange_info()
            for s in info['symbols']:
                sym = s['symbol']
                self.cache[sym] = {
                    'status': s['status'],
                    'base': s['baseAsset'],
                    'quote': s['quoteAsset'],
                    'filters': {}
                }
                for f in s['filters']:
                    self.cache[sym]['filters'][f['filterType']] = f
            self.last_update = time.time()
            logger.info(f"📊 Loaded {len(self.cache)} symbols")
        except Exception as e:
            if self.client.dry_run:
                logger.warning(f"⚠️ Exchange info failed (dry-run): {e}. Using fallback defaults.")
                # Mock some common symbols if cache is empty
                if not self.cache:
                    for s in ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'KDAUSDT']:
                        self.cache[s] = {
                            'status': 'TRADING',
                            'base': s.replace('USDT', ''),
                            'quote': 'USDT',
                            'filters': {
                                'LOT_SIZE': {'stepSize': '0.001', 'minQty': '0.001'},
                                'NOTIONAL': {'minNotional': '5.0'}
                            }
                        }
            else:
                logger.error(f"Exchange info error: {e}")
    
    def can_trade(self, symbol: str) -> bool:
        self.update()
        info = self.cache.get(symbol, {})
        return info.get('status') == 'TRADING'
    
    def get_step_size(self, symbol: str) -> float:
        self.update()
        lot = self.cache.get(symbol, {}).get('filters', {}).get('LOT_SIZE', {})
        return float(lot.get('stepSize', '0.001'))
    
    def get_min_qty(self, symbol: str) -> float:
        self.update()
        lot = self.cache.get(symbol, {}).get('filters', {}).get('LOT_SIZE', {})
        return float(lot.get('minQty', '0.001'))
    
    def get_min_notional(self, symbol: str) -> float:
        self.update()
        notional = self.cache.get(symbol, {}).get('filters', {}).get('NOTIONAL', {})
        return float(notional.get('minNotional', '5.0'))
    
    def format_qty(self, symbol: str, qty: float) -> str:
        """Format quantity to LOT_SIZE precision - THE FIX!"""
        step = self.get_step_size(symbol)
        min_qty = self.get_min_qty(symbol)
        
        # Calculate precision from step size
        if step >= 1:
            precision = 0
        else:
            precision = len(str(step).rstrip('0').split('.')[-1])
        
        # Use Decimal for exact arithmetic
        qty_d = Decimal(str(qty))
        step_d = Decimal(str(step))
        
        # Round DOWN to nearest step
        formatted = (qty_d // step_d) * step_d
        formatted = max(Decimal(str(min_qty)), formatted)
        
        if precision == 0:
            return str(int(formatted))
        return f"{formatted:.{precision}f}"

# ═══════════════════════════════════════════════════════════════════════════
# PRIMES & FIBONACCI (From Quantum Quackers HiveController)
# ═══════════════════════════════════════════════════════════════════════════

PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97]
FIBS = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377]

# ═══════════════════════════════════════════════════════════════════════════
# 9 AURIS NODES (From the_play.py)
# ═══════════════════════════════════════════════════════════════════════════

class AurisNode:
    def __init__(self, name: str, emoji: str, weight: float, freq: float):
        self.name = name
        self.emoji = emoji
        self.weight = weight
        self.freq = freq

AURIS_NODES = [
    AurisNode('Tiger', '🐯', 1.2, 220),
    AurisNode('Falcon', '🦅', 1.1, 285),
    AurisNode('Hummingbird', '🐦', 0.8, 396),
    AurisNode('Dolphin', '🐬', 1.0, 528),  # LOVE - The Center
    AurisNode('Deer', '🦌', 0.9, 639),
    AurisNode('Owl', '🦉', 1.0, 741),
    AurisNode('Panda', '🐼', 0.95, 852),
    AurisNode('CargoShip', '🚢', 1.3, 936),
    AurisNode('Clownfish', '🐠', 0.7, 963),
]

# ═══════════════════════════════════════════════════════════════════════════
# MASTER EQUATION: Λ(t) = S(t) + O(t) + E(t)
# ═══════════════════════════════════════════════════════════════════════════

def kelly_criterion(win_prob: float, win_loss_ratio: float) -> float:
    """
    Kelly Criterion from Quantum Quackers riskManagement.ts
    
    Returns optimal fraction to risk (0-1)
    """
    if win_loss_ratio <= 0:
        return 0
    kelly = win_prob - (1 - win_prob) / win_loss_ratio
    return max(0, min(1, kelly))

def calculate_rsi(closes: List[float], period: int = 14) -> float:
    """Calculate RSI indicator (Piano style)"""
    if len(closes) < period + 1:
        return 50.0
    
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas[-period:]]
    losses = [-d if d < 0 else 0 for d in deltas[-period:]]
    
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_coherence(price_change_pct: float, volume: float, volatility_pct: float) -> float:
    """
    Master Equation coherence calculation
    Enhanced with WebSocket-style velocity factors from Quackers
    
    S(t) = Substrate (volume strength)
    O(t) = Observer (directional momentum)  
    E(t) = Echo (volatility feedback)
    """
    # Velocity factor from volatility (Quackers masterEquation.ts)
    velocity_factor = 1.0 + abs(volatility_pct / 100) * 50
    velocity_factor = min(velocity_factor, 3.0)
    
    # Normalize inputs with velocity enhancement
    S = min(1.0, volume / 100000.0) * velocity_factor  # Volume + velocity
    O = min(1.0, abs(price_change_pct) / 10.0)  # Momentum
    E = min(1.0, volatility_pct / 20.0)  # Volatility feedback
    
    # Master Equation Λ(t)
    Lambda = (S + O + E) / 3.0
    
    # Sigmoid activation for smooth 0-1 mapping
    coherence = 1 / (1 + math.exp(-5 * (Lambda - 0.5)))
    
    return coherence

# ═══════════════════════════════════════════════════════════════════════════
# PING-PONG ENGINE
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Position:
    """Piano Key - Each position is a harmonic instrument"""
    symbol: str
    entry_price: float
    quantity: float
    entry_time: float
    coherence: float
    notional_usd: float
    bounces: int = 0
    stop_loss_price: float = 0.0  # Dynamic SL based on entry volatility
    take_profit_price: float = 0.0  # Dynamic TP based on entry volatility
    
    # Piano enhancements
    substrate: float = 0.0        # S(t) - 9-node waveform
    observer: float = 0.0         # O(t) - Conscious focus
    echo: float = 0.0             # E(t) - Causal feedback
    lambda_value: float = 0.0     # Λ(t) - Reality field
    dominant_node: str = "Dolphin"  # Most active node
    rainbow_state: str = "FORMING"  # FEAR → LOVE → UNITY
    rsi: float = 50.0             # RSI indicator
    fees_quote: float = 0.0       # Accrued fees in quote asset (approx)
    partial_taken: bool = False   # Whether partial TP already executed
    
    # 🦆 Commando tracking
    commando: str = "lion"        # Which commando owns this position
    field_gamma: float = 0.0      # Lighthouse gamma environment at entry
    field_distortion: float = 0.0 # Lighthouse distortion index at entry
    field_coherence: float = 0.0  # Lighthouse coherence baseline at entry
    field_maker_bias: float = 0.5 # Maker/taker bias snapshot

# ═══════════════════════════════════════════════════════════════════════════
# PIANO SIGNAL GENERATION
# ═══════════════════════════════════════════════════════════════════════════

def generate_piano_signal(pos: Position, coherence: float, momentum: float, rsi: float) -> Tuple[str, float]:
    """
    Piano-style signal generation from aureon_piano.py 🎹
    
    Returns: (signal, confidence)
    - STRONG_BUY/BUY: High coherence + bullish momentum
    - STRONG_SELL/SELL: Low coherence + bearish momentum
    - HOLD: Neutral
    """
    score = 0.0
    
    # Lambda contribution
    if pos.lambda_value > 2.0:
        score += 30
    elif pos.lambda_value > 1.5:
        score += 20
    elif pos.lambda_value > 1.0:
        score += 10
    elif pos.lambda_value < 0.5:
        score -= 20
    
    # Coherence contribution
    if coherence > 0.9:
        score += 25
    elif coherence > 0.8:
        score += 15
    elif coherence > 0.6:
        score += 5
    elif coherence < 0.3:
        score -= 20
    
    # Rainbow state contribution
    rainbow_scores = {
        "UNITY": 25, "AWE": 15, "LOVE": 10,
        "RESONANCE": 5, "FORMING": 0, "FEAR": -20
    }
    score += rainbow_scores.get(pos.rainbow_state, 0)
    
    # Momentum contribution
    if momentum > 2:
        score += 15
    elif momentum > 0.5:
        score += 8
    elif momentum < -2:
        score -= 15
    elif momentum < -0.5:
        score -= 8
    
    # RSI contribution
    if rsi < 30:
        score += 15  # Oversold = bullish
    elif rsi < 40:
        score += 8
    elif rsi > 70:
        score -= 15  # Overbought = bearish
    elif rsi > 60:
        score -= 8
    
    # Dominant node bonuses
    bullish_nodes = ["Falcon", "Dolphin", "CargoShip"]
    if pos.dominant_node in bullish_nodes:
        score += 10
    
    confidence = min(abs(score) / 100, 1.0)
    
    if score >= 60:
        return "STRONG_BUY", confidence
    elif score >= 30:
        return "BUY", confidence
    elif score <= -60:
        return "STRONG_SELL", confidence
    elif score <= -30:
        return "SELL", confidence
    else:
        return "HOLD", confidence

# ═══════════════════════════════════════════════════════════════════════════
# QUEEN HIVE (10-9-1)
# ═══════════════════════════════════════════════════════════════════════════

class QueenHive:
    """90% compound, 10% harvest"""
    
    def __init__(self):
        self.total_profit = 0.0
        self.harvested = 0.0
        self.compounded = 0.0
    
    def process_profit(self, profit: float) -> Tuple[float, float]:
        """Split profit: 90% compound, 10% harvest"""
        self.total_profit += profit
        
        compound = profit * CONFIG['COMPOUND_PCT']
        harvest = profit * CONFIG['HARVEST_PCT']
        
        self.compounded += compound
        self.harvested += harvest
        
        return compound, harvest

# ═══════════════════════════════════════════════════════════════════════════
# ULTIMATE TRADER
# ═══════════════════════════════════════════════════════════════════════════

class DecisionFusion:
    """
    Decision Fusion (4-model ensemble) from Quantum Quackers decisionFusion.ts
    Simulates ensemble model outputs based on market data heuristics.
    """
    def __init__(self):
        self.models = ['lstm', 'randomForest', 'xgboost', 'transformer']
        # Weights for final decision
        self.weights = {'ensemble': 0.6, 'sentiment': 0.2, 'qgita': 0.2}

    def generate_signal(self, change: float, volatility: float, volume: float) -> Tuple[float, float]:
        """
        Generate ensemble signal score (-1 to 1) and confidence (0 to 1).
        """
        # Normalize inputs
        vol = max(0.01, volatility)
        normalized_trend = math.tanh(change / vol)
        
        signals = []
        for model in self.models:
            # Add "personality" bias to each model to simulate diversity
            bias = 0.0
            if model == 'lstm': bias = 0.2       # Optimistic
            elif model == 'randomForest': bias = -0.1 # Conservative
            elif model == 'xgboost': bias = 0.1  # Aggressive
            
            # Noise factor
            noise = (random.random() - 0.5) * 0.1
            
            # Model score
            score = normalized_trend + bias + noise
            
            # Confidence based on signal strength (extreme signals = lower confidence usually, but here we invert for simplicity)
            # Actually, let's say confidence is higher when trend matches bias
            confidence = 0.5 + (random.random() * 0.4)
            
            signals.append({'score': score, 'confidence': confidence})
            
        # Aggregate ensemble
        total_weighted_score = sum(s['score'] * s['confidence'] for s in signals)
        total_confidence = sum(s['confidence'] for s in signals)
        
        ensemble_score = total_weighted_score / total_confidence if total_confidence > 0 else 0
        
        # Simulate Sentiment and QGITA (using volume and trend as proxies)
        sentiment_score = math.tanh(volume / 100000) * (1 if change > 0 else -1)
        qgita_score = normalized_trend # Proxy
        
        final_score = (
            ensemble_score * self.weights['ensemble'] +
            sentiment_score * self.weights['sentiment'] +
            qgita_score * self.weights['qgita']
        )
        
        # Normalize final score to -1 to 1
        final_score = max(-1.0, min(1.0, final_score))
        
        return final_score, total_confidence / len(self.models)

class AureonUltimate:
    """The ONE trader with ALL systems"""
    
    def __init__(self):
        # Select exchange via env EXCHANGE or --exchange arg
        ex = None
        for i, arg in enumerate(sys.argv):
            if arg == "--exchange" and i + 1 < len(sys.argv):
                ex = sys.argv[i+1]
        ex = ex or os.getenv("EXCHANGE", "binance").lower()

        if ex == "kraken" and KrakenClient is not None:
            self.client = get_kraken_client()
            logger.info("🟣 Using Kraken client (dry-run compatible)")
        else:
            self.client = get_binance_client()
            logger.info("🟡 Using Binance client")
        self.lot_mgr = LotSizeManager(self.client)
        self.memory = ElephantMemory()
        self.fire = FireStarter()
        self.hive = QueenHive()
        # Execution environment visibility
        try:
            logger.info(
                f"🟡 Binance Client: mainnet={str(not self.client.use_testnet)} | dry_run={str(self.client.dry_run)} | base={self.client.base}"
            )
        except Exception:
            pass
        
        # 🦆⚔️ BOT ROLE SPECIALIZATION ⚔️🦆
        self.bot_role = 'BALANCED'  # BUYER, SELLER, WATCHER, or BALANCED
        
        # 🦆⚔️ DEPLOY THE QUACK COMMANDOS ⚔️🦆
        self.commandos = QuackCommandos(self.client, CONFIG)  # Pass config for ecosystem slots
        
        # 🎯 Detect which quote assets Binance UK lets us touch today
        self.allowed_quotes = CONFIG.get('TARGET_QUOTES', ['USDC'])
        self.primary_quote = CONFIG.get('PRIMARY_QUOTE', self.allowed_quotes[0])
        try:
            self.sync_allowed_quotes_with_account()
        except Exception as e:
            logger.warning(f"⚠️ Failed to sync quotes with account (likely missing API keys). Using defaults. Error: {e}")
            self.allowed_quotes = ['USDC', 'USDT', 'BTC']
            self.primary_quote = 'USDC'

        # 🇬🇧💎 DEPLOY THE PLUMS GUARDIAN 💎🇬🇧 (TSX Intelligence!)
        self.initial_capital = self.get_quote_balance()
        guardian_limits = GuardianLimits(
            max_drawdown_pct=0.15,  # 15% circuit breaker from TechnologyRoadmap.tsx
            max_position_hold_hours=72.0,  # 72h max hold from TechnologyRoadmap.tsx
            max_daily_loss_usd=self.initial_capital * 0.05,  # 5% of capital daily
            atr_stop_multiplier=2.0,  # 2x ATR stops from TechnologyRoadmap.tsx
            max_position_pct=0.80,  # 80% BIG PLUMS mode!
        )
        self.guardian = PlumsGuardian(self.initial_capital, guardian_limits)
        logger.info("🇬🇧💎 PLUMS GUARDIAN DEPLOYED WITH TSX INTELLIGENCE! 💎🇬🇧")
        
        # 🧠💎 DEPLOY ADVANCED INTELLIGENCE 💎🧠 (The Missing Pieces!)
        self.advanced = AdvancedIntelligence()
        logger.info("🧠💎 ADVANCED INTELLIGENCE DEPLOYED! (Mycelium/Piano/Temporal/Fusion/Enhanced Auris) 💎🧠")

        # 🌈 LIGHTHOUSE METRICS ENGINE (Spectral / Gamma / Distortion gauges)
        self.lighthouse_engine = LighthouseMetricsEngine()
        self.lighthouse_history = deque(maxlen=2048)
        self.lighthouse_metrics: Dict[str, Any] = {}
        self.last_lighthouse_compute = 0.0
        
        self.positions: Dict[str, Position] = {}
        self.ticker_cache = {}
        self.last_ticker_update = 0
        self.commando_cache = None  # Cache commando targets
        self.last_commando_scan = 0
        
        self.trades = 0
        self.wins = 0
        self.cycle = 0
        self.harvest_total = 0.0  # Track total harvested profits

        # External Binance equity tracking
        self.real_equity_cache: Dict[str, Any] = {}
        self.last_real_equity_sync: float = 0.0
        
        # Business 101: Track Gross vs Fees = Net
        self.total_gross_pnl = 0.0
        self.total_fees = 0.0
        self.last_equity_net = 0.0  # Mark-to-market net (equity vs start)
        self.last_realized_net = 0.0  # Realized net (closed trades only)
        self.business_green_light = False
        
        # 🌉 BRIDGE INTEGRATION 🌉
        self.bridge = None
        self.bridge_enabled = BRIDGE_AVAILABLE and os.getenv('ENABLE_BRIDGE', '1') == '1'
        if self.bridge_enabled:
            try:
                self.bridge = AureonBridge()
                logger.info("🌉 Bridge enabled: Ultimate ↔ Unified communication active")
            except Exception as e:
                logger.warning(f"⚠️ Bridge initialization failed: {e}")
                self.bridge_enabled = False
        self.last_bridge_sync = 0.0
        self.bridge_sync_interval = 10.0  # Sync every 10 seconds
        
        # 🌌⚡ IMPERIAL PREDICTABILITY ENGINE ⚡🌌
        self.imperial = None
        self.cosmic_state = None
        self.imperial_enabled = IMPERIAL_AVAILABLE and CONFIG.get('ENABLE_IMPERIAL', True)
        if self.imperial_enabled:
            try:
                self.imperial = ImperialTradingIntegration()
                self.cosmic_state = self.imperial.update_cosmic_state()
                logger.info("🌌⚡ Imperial Predictability Engine ACTIVE")
                logger.info(f"   ├─ Cosmic Phase: {self.cosmic_state.phase.value}")
                logger.info(f"   ├─ Coherence: {self.cosmic_state.coherence:.2%}")
                logger.info(f"   └─ Planetary Torque: ×{self.cosmic_state.planetary_torque:.2f}")
            except Exception as e:
                logger.warning(f"⚠️ Imperial Predictability initialization failed: {e}")
                self.imperial_enabled = False
    
    def sync_allowed_quotes_with_account(self):
        """Blend Binance UK permissions with our preferred quotes - ONLY trade quotes with actual balance."""
        detected = self.detect_allowed_quotes()
        if detected:
            preferred = CONFIG.get('TARGET_QUOTES', [])
            ordered = [q for q in preferred if q in detected]
            ordered += [q for q in detected if q not in ordered]
        else:
            ordered = CONFIG.get('TARGET_QUOTES', []) or [self.primary_quote]

        if not ordered:
            ordered = ['USDC']

        # 🔥 CRITICAL FIX: Only allow quotes with actual balance!
        balances = self.client.account()['balances']
        min_notional = CONFIG.get('MIN_TRADE_NOTIONAL', 10.0)
        quotes_with_balance = []
        for quote in ordered:
            bal = next((float(b['free']) for b in balances if b['asset'] == quote), 0.0)
            if bal >= min_notional:
                quotes_with_balance.append(quote)
                logger.info(f"✅ {quote}: ${bal:.2f} available (can trade)")
            else:
                logger.info(f"❌ {quote}: ${bal:.2f} available (SKIP - below ${min_notional})")
        
        # Use only quotes with balance, fallback to primary if empty
        self.allowed_quotes = quotes_with_balance if quotes_with_balance else [self.primary_quote]
        if self.primary_quote not in self.allowed_quotes:
            self.primary_quote = self.allowed_quotes[0]

        logger.info(
            f"🎯 TRADEABLE quotes (with balance): {self.allowed_quotes} | Primary: {self.primary_quote}"
        )

    def detect_allowed_quotes(self) -> List[str]:
        """Return quote assets our trade-group is cleared for."""
        try:
            account = self.client.account()
            perms = account.get('permissions') or []
            trade_groups = {p for p in perms if p.startswith('TRD_GRP_')}
            if not trade_groups:
                logger.warning("Account is missing TRD_GRP permissions; falling back to config quotes.")
                return []

            info = self.client.exchange_info()
            allowed_symbols = []
            for sym in info.get('symbols', []):
                if sym.get('status') != 'TRADING' or not sym.get('isSpotTradingAllowed', False):
                    continue
                permsets = sym.get('permissionSets') or []
                if not permsets:
                    continue
                for permset in permsets:
                    group_flags = {p for p in permset if p.startswith('TRD_GRP_')}
                    if group_flags and trade_groups.intersection(group_flags):
                        allowed_symbols.append(sym)
                        break

            if not allowed_symbols:
                logger.warning("No spot symbols matched UK permission sets; defaulting to config quotes.")
                return []

            counts = Counter(sym['quoteAsset'] for sym in allowed_symbols)
            logger.info(f"🇬🇧 UK Quote coverage snapshot: {counts.most_common(10)}")
            return [quote for quote, _ in counts.most_common()]

        except Exception as exc:
            logger.error(f"Failed to detect allowed quotes: {exc}")
            return []

    def match_quote_asset(self, symbol: str) -> Optional[str]:
        for quote in self.allowed_quotes:
            if symbol.endswith(quote):
                return quote
        return None

    def _load_real_pnl_baseline(self) -> Tuple[Optional[float], Optional[str]]:
        try:
            with open(PNL_BASELINE_FILE, 'r') as f:
                data = json.load(f)
            baseline_val = float(data.get('total_value_usdc', 0.0))
            timestamp = data.get('timestamp')
            return baseline_val, timestamp
        except Exception:
            return None, None

    def _compute_account_total_usdc(self) -> Tuple[float, Dict[str, Dict[str, float]]]:
        total = 0.0
        details: Dict[str, Dict[str, float]] = {}
        try:
            usdt_usdc = 1.0
            try:
                quote = self.client.best_price('USDTUSDC')
                usdt_usdc = float(quote.get('price', 1.0)) or 1.0
            except Exception:
                pass

            account = self.client.account()
            for bal in account.get('balances', []):
                asset = bal.get('asset')
                if not asset:
                    continue
                free = float(bal.get('free', 0) or 0)
                locked = float(bal.get('locked', 0) or 0)
                qty = free + locked
                if qty <= 0:
                    continue

                price_usdc = 0.0
                ref = '(no price)'
                if asset == self.primary_quote:
                    price_usdc = 1.0
                    ref = self.primary_quote
                elif asset == 'USDT':
                    price_usdc = usdt_usdc
                    ref = 'USDTUSDC'
                else:
                    pair = f"{asset}{self.primary_quote}"
                    try:
                        info = self.client.best_price(pair)
                        price_usdc = float(info.get('price', 0))
                        if price_usdc > 0:
                            ref = pair
                    except Exception:
                        price_usdc = 0.0
                    if price_usdc <= 0:
                        pair = f"{asset}USDT"
                        try:
                            info = self.client.best_price(pair)
                            price_tmp = float(info.get('price', 0))
                            if price_tmp > 0:
                                price_usdc = price_tmp * usdt_usdc
                                ref = f"{pair}*USDTUSDC"
                        except Exception:
                            price_usdc = 0.0

                if price_usdc <= 0:
                    continue

                value = qty * price_usdc
                total += value
                details[asset] = {
                    'qty': qty,
                    'price_usdc': price_usdc,
                    'value_usdc': value,
                    'ref': ref,
                }
        except Exception as exc:
            if self.client.dry_run:
                return 10000.0, {}
            raise RuntimeError(f"Failed to compute Binance equity: {exc}")

        return total, details

    def get_real_exchange_equity(self, refresh_seconds: int = 60) -> Dict[str, Any]:
        now = time.time()
        if self.real_equity_cache and (now - self.last_real_equity_sync) < refresh_seconds:
            return self.real_equity_cache

        result: Dict[str, Optional[float]] = {}
        try:
            total, _ = self._compute_account_total_usdc()
            baseline_val, baseline_ts = self._load_real_pnl_baseline()
            delta = None
            pct = None
            if baseline_val is not None:
                delta = total - baseline_val
                pct = (delta / baseline_val * 100.0) if baseline_val > 0 else None

            result = {
                'total': total,
                'baseline': baseline_val,
                'baseline_ts': baseline_ts,
                'delta': delta,
                'pct': pct,
            }
        except Exception as exc:
            result = {'error': str(exc)}

        self.real_equity_cache = result
        self.last_real_equity_sync = now
        return result

    def get_base_asset(self, symbol: str) -> Optional[str]:
        info = self.lot_mgr.cache.get(symbol)
        if info and info.get('base'):
            return info['base']
        quote = self.match_quote_asset(symbol)
        if quote:
            return symbol[:-len(quote)] or None
        return None

    def get_available_position_quantity(self, symbol: str) -> float:
        base_asset = self.get_base_asset(symbol)
        if not base_asset:
            return 0.0
        try:
            return self.client.get_free_balance(base_asset)
        except Exception as exc:
            if self.client.dry_run:
                # Return tracked quantity if available, else 0
                pos = self.positions.get(symbol)
                return pos.quantity if pos else 0.0
            logger.error(f"Unable to fetch balance for {base_asset}: {exc}")
            return 0.0

    def get_quote_balance(self, asset: Optional[str] = None) -> float:
        quote = asset or self.primary_quote
        try:
            balance = self.client.get_free_balance(quote)
            # If no balance in primary asset, check LDUSDC (Binance Earn)
            if balance == 0.0 and quote == 'USDC':
                ld_balance = self.client.get_free_balance('LDUSDC')
                if ld_balance > 0:
                    logger.info(f"💰 Found {ld_balance:.4f} LDUSDC (Binance Earn) - treating as USDC")
                    balance = ld_balance
            return balance
        except Exception as e:
            logger.warning(f"⚠️ Error fetching balance for {quote}: {e}")
            if self.client.dry_run:
                return 10000.0  # Mock balance for dry-run
            return 0.0

    def current_realized_net(self) -> float:
        """Return realized net profit (closed trades only)."""
        return self.total_gross_pnl - self.total_fees

    def business_threshold(self) -> float:
        return CONFIG.get('BUSINESS_GREEN_THRESHOLD', 0.0)

    def business_can_execute(self, expected_net: float, action: str, allow_positive: bool = True) -> bool:
        """Centralize Business 101 gating rules for exits/harvests."""
        realized_net = self.current_realized_net()
        threshold = self.business_threshold()
        if realized_net >= threshold:
            return True
        if allow_positive and expected_net >= 0:
            return True
        logger.info(
            f"🚫 BUSINESS HOLD: Realized Net ${realized_net:+.2f} <= ${threshold:+.2f}. "
            f"{action} would realize ${expected_net:+.2f}."
        )
        return False

    def consolidate_balances(self, min_notional: float = 3.0):
        """Convert stray assets into the primary quote asset."""
        logger.info(
            f"♻️ CONSOLIDATION CHECK: Rolling non-{self.primary_quote} balances into {self.primary_quote}"
        )
        if self.client.dry_run:
            logger.info("♻️ Dry-run mode: Skipping consolidation.")
            return

        try:
            account = self.client.account()
        except Exception as exc:
            logger.error(f"Unable to fetch account for consolidation: {exc}")
            return

        conversions = 0
        for bal in account.get('balances', []):
            asset = bal.get('asset')
            if not asset or asset == self.primary_quote:
                continue
            free = float(bal.get('free', 0))
            if free <= 0:
                continue

            symbol = f"{asset}{self.primary_quote}"
            if not self.lot_mgr.can_trade(symbol):
                logger.debug(f"Skipping {asset}: pair {symbol} not tradable")
                continue

            try:
                price = float(self.client.best_price(symbol)['price'])
            except Exception as exc:
                logger.error(f"Failed to fetch price for {symbol}: {exc}")
                continue

            notional = free * price
            if notional < min_notional:
                logger.debug(
                    f"Skipping {asset}: notional {notional:.2f} below consolidation threshold {min_notional:.2f}"
                )
                continue

            qty_str = self.lot_mgr.format_qty(symbol, free)
            qty_float = float(qty_str)
            if qty_float <= 0:
                continue

            try:
                logger.info(
                    f"♻️ Converting {asset} -> {self.primary_quote}: {qty_str} via {symbol} (~{notional:.2f})"
                )
                result = self.client.place_market_order(symbol, 'SELL', quantity=qty_float)
                logger.info(
                    f"✅ Consolidated {asset}: order #{result.get('orderId', 'dry-run')}"
                )
                conversions += 1
            except Exception as exc:
                logger.error(f"❌ Conversion failed for {symbol}: {exc}")

        if conversions == 0:
            logger.info("♻️ No consolidations executed (nothing sizeable or tradable).")
        else:
            logger.info(f"♻️ Consolidation complete: {conversions} assets converted to {self.primary_quote}.")

    def auto_harvest_floor_winners(self) -> int:
        """Proactively harvest ANY position above the floor threshold.
        
        This runs every cycle to compound profits, regardless of position count.
        Returns the number of positions harvested.
        """
        if not self.positions:
            return 0
            
        fee_pct = CONFIG.get('TAKER_FEE_PCT', 0.001)
        # Require ~0.50% gross to get meaningful profits after fees (0.30%+ net)
        floor_threshold = max(0.005, fee_pct * 5.0)
        
        harvested = 0
        positions_to_harvest = []
        
        # Find all positions above floor
        for symbol, pos in self.positions.items():
            ticker = self.ticker_cache.get(symbol)
            if not ticker:
                continue
            try:
                price = float(ticker['lastPrice'])
            except (TypeError, ValueError):
                continue
            pnl_pct = (price - pos.entry_price) / pos.entry_price
            
            # Check if above floor and in profit
            if pnl_pct >= floor_threshold:
                positions_to_harvest.append((symbol, pos, price, pnl_pct))
        
        # Harvest each winner
        for symbol, pos, current_price, pnl_pct in positions_to_harvest:
            base_asset = self.get_base_asset(symbol)
            if not base_asset:
                continue
                
            available_qty = self.get_available_position_quantity(symbol)
            if available_qty <= 0:
                continue
            
            # Execute the exit
            min_qty = self.lot_mgr.get_min_qty(symbol)
            qty_str = self.lot_mgr.format_qty(symbol, available_qty)
            qty_to_sell = float(qty_str)
            
            if qty_to_sell < min_qty:
                continue
            
            # Check notional (price * qty) meets minimum
            min_notional = self.lot_mgr.get_min_notional(symbol)
            notional = qty_to_sell * current_price
            if notional < min_notional:
                logger.debug(f"⏭️ Skip harvest {symbol}: notional ${notional:.2f} < min ${min_notional:.2f}")
                continue
            
            try:
                # 💰 BEFORE HARVEST BALANCE
                balance_before = self.get_quote_balance()
                
                gross = qty_to_sell * current_price
                fee = gross * fee_pct
                net_proceeds = gross - fee
                entry_cost = qty_to_sell * pos.entry_price
                entry_fee_actual = pos.fees_quote
                net_pnl = net_proceeds - entry_cost - entry_fee_actual

                if not self.business_can_execute(net_pnl, f"floor harvest {symbol}"):
                    continue
                
                order = self.client.place_market_order(
                    symbol=symbol,
                    side='SELL',
                    quantity=qty_str
                )
                
                if order:
                    actual_fee = self.client.compute_order_fees_in_quote(order, self.primary_quote)
                    if actual_fee and actual_fee > 0:
                        fee = actual_fee
                        net_proceeds = gross - fee
                        net_pnl = net_proceeds - entry_cost - entry_fee_actual
                    self.total_gross_pnl += (qty_to_sell * (current_price - pos.entry_price))
                    self.total_fees += fee
                    
                    # 💰 AFTER HARVEST BALANCE
                    balance_after = self.get_quote_balance()
                    received = balance_after - balance_before
                    
                    harvested += 1
                    self.wins += 1
                    self.trades += 1
                    self.harvest_total += net_pnl
                    
                    logger.info(
                        f"🌾 FLOOR HARVEST! {symbol} @ {current_price:.4f} | "
                        f"+{pnl_pct*100:.2f}% | Net ${net_pnl:+.4f}"
                    )
                    logger.info(f"💰 BALANCE: Before=${balance_before:.4f} → After=${balance_after:.4f} | Received=${received:.4f}")
                    
                    # Remove from positions and notify commandos
                    if symbol in self.positions:
                        self.commandos.record_exit(symbol, net_pnl)
                        del self.positions[symbol]
                        
            except Exception as e:
                logger.error(f"❌ Floor harvest failed for {symbol}: {e}")
        
        if harvested > 0:
            logger.info(f"🌾 Auto-harvested {harvested} floor winners!")
            
        return harvested

    def harvest_winner_for_liquidity(self, target_cash: float) -> bool:
        """Trim the strongest position to free quote liquidity.
        
        Floor strategy: Take ANY net profit to compound faster.
        Minimum gain: 0.22% (covers 0.2% fees + 0.02% profit = survival mode)
        """
        if not self.positions:
            return False

        # Minimum gain required to harvest (absolute floor for net profit)
        fee_pct = CONFIG.get('TAKER_FEE_PCT', 0.001)
        min_harvest_gain = fee_pct * 1.2  # 0.12% = cover fees + tiny profit

        best_symbol = None
        best_position = None
        best_price = 0.0
        best_gain = float('-inf')

        for symbol, pos in self.positions.items():
            ticker = self.ticker_cache.get(symbol)
            if not ticker:
                continue
            try:
                price = float(ticker['lastPrice'])
            except (TypeError, ValueError):
                continue
            pnl_pct = (price - pos.entry_price) / pos.entry_price
            if pnl_pct > best_gain:
                best_gain = pnl_pct
                best_symbol = symbol
                best_position = pos
                best_price = price

        if not best_symbol or not best_position or best_price <= 0:
            return False
        
        # FLOOR MODE: Take any profit to compound. We own the house eventually!
        if best_gain < min_harvest_gain:
            logger.info(
                f"⏳ Harvest skipped: best position {best_symbol} at {best_gain*100:+.2f}% < "
                f"floor threshold {min_harvest_gain*100:.2f}%. Building from the ground up! 🏗️"
            )
            return False

        base_asset = self.get_base_asset(best_symbol)
        if not base_asset:
            logger.warning(f"⚠️ Unable to determine base asset for {best_symbol}; skipping harvest")
            return False

        available_qty = self.get_available_position_quantity(best_symbol)
        if available_qty <= 0:
            logger.warning(
                f"⚠️ Harvest blocked: no free {base_asset} available for {best_symbol}"
            )
            return False

        # Keep tracked quantity aligned with wallet to avoid over-selling after fees.
        if available_qty < best_position.quantity:
            best_position.quantity = available_qty
            best_position.notional_usd = best_position.quantity * best_position.entry_price

        min_qty = self.lot_mgr.get_min_qty(best_symbol)
        desired_cash = max(0.0, target_cash - self.get_quote_balance())
        if desired_cash <= 0:
            desired_cash = target_cash * 0.5

        sell_qty = max(min_qty, desired_cash / best_price)
        sell_qty = min(sell_qty, best_position.quantity, available_qty)
        qty_str = self.lot_mgr.format_qty(best_symbol, sell_qty)
        qty_float = float(qty_str)
        if qty_float <= 0:
            return False

        notional = qty_float * best_price
        min_notional = self.lot_mgr.get_min_notional(best_symbol)
        if notional < min_notional and best_position.quantity > qty_float:
            # Try selling the full position instead
            qty_str = self.lot_mgr.format_qty(best_symbol, best_position.quantity)
            qty_float = float(qty_str)
            notional = qty_float * best_price
        if notional < min_notional:
            return False

        qty_fraction_preview = (qty_float / best_position.quantity) if best_position.quantity > 0 else 0.0
        entry_fee_preview = best_position.fees_quote * qty_fraction_preview
        exit_fee_preview = best_price * qty_float * fee_pct
        expected_net = qty_float * (best_price - best_position.entry_price) - exit_fee_preview - entry_fee_preview
        if not self.business_can_execute(expected_net, f"liquidity harvest {best_symbol}"):
            return False

        logger.info(
            f"💎 Harvesting {best_symbol}: selling {qty_str} to free {self.primary_quote} liquidity"
        )

        def attempt_sell(quantity: float, context: str = "primary") -> Tuple[Optional[Dict], float]:
            sell_str = self.lot_mgr.format_qty(best_symbol, quantity)
            sell_float = float(sell_str)
            if sell_float <= 0:
                return None, 0.0
            try:
                return self.client.place_market_order(best_symbol, 'SELL', quantity=sell_float), sell_float
            except Exception as exc:
                if "-2010" in str(exc):
                    logger.warning(
                        f"⚠️ Harvest {context} sell insufficient balance for {best_symbol} @ {sell_str}; "
                        "rechecking wallet"
                    )
                    return None, 0.0
                raise

        try:
            result, executed_qty = attempt_sell(qty_float)
        except Exception as exc:
            logger.error(f"❌ Harvest sell failed for {best_symbol}: {exc}")
            return False

        if result is None:
            refreshed_qty = self.get_available_position_quantity(best_symbol)
            if refreshed_qty <= 0:
                logger.warning(
                    f"⚠️ Harvest fallback blocked: still no free {base_asset} for {best_symbol}"
                )
                return False
            fallback_qty = min(best_position.quantity, refreshed_qty)
            fallback_str = self.lot_mgr.format_qty(best_symbol, fallback_qty)
            fallback_float = float(fallback_str)
            fallback_notional = fallback_float * best_price
            if fallback_float <= 0 or fallback_notional < min_notional:
                logger.warning(
                    f"⚠️ Harvest fallback size invalid for {best_symbol}: qty={fallback_float} notional={fallback_notional:.4f}"
                )
                return False
            logger.info(
                f"💎 Harvest fallback: selling AVAILABLE {best_symbol} position ({fallback_str})"
            )
            try:
                result, executed_qty = attempt_sell(fallback_float, context="fallback")
            except Exception as exc:
                logger.error(f"❌ Harvest fallback sell failed for {best_symbol}: {exc}")
                return False
            if result is None:
                logger.error(
                    f"❌ Harvest fallback could not free liquidity for {best_symbol} (insufficient balance)"
                )
                return False
            qty_float = executed_qty
        else:
            qty_float = executed_qty

        fee_pct = CONFIG.get('TAKER_FEE_PCT', 0.0)
        freed_cash = qty_float * best_price
        realized = qty_float * (best_price - best_position.entry_price)
        
        # Use proportional share of tracked entry fees (actual from order response)
        qty_fraction = qty_float / best_position.quantity if best_position.quantity > 0 else 0.0
        entry_fee_actual = best_position.fees_quote * qty_fraction
        
        # Approximate exit fee before order; actual commission processed after order
        exit_fee_approx = best_price * qty_float * fee_pct
        realized_net = realized - exit_fee_approx - entry_fee_actual
        freed_cash_net = freed_cash * (1 - fee_pct)
        compound, harvest = self.hive.process_profit(realized_net)
        self.memory.record(best_symbol, realized_net)

        best_position.quantity -= qty_float
        best_position.notional_usd = best_position.quantity * best_position.entry_price
        if best_position.quantity <= min_qty:
            self.commandos.record_exit(best_symbol, realized_net)  # 🦆 Notify commandos
            del self.positions[best_symbol]

        # Try to replace exit fee with actual commission from order fills
        actual_exit_fee = 0.0
        try:
            actual_exit_fee = self.client.compute_order_fees_in_quote(result or {}, self.primary_quote)
        except Exception:
            actual_exit_fee = 0.0
        total_fees = (actual_exit_fee if actual_exit_fee > 0 else exit_fee_approx) + entry_fee_actual
        # Recompute net values using actual sell fee when available
        if actual_exit_fee > 0:
            freed_cash_net = freed_cash - actual_exit_fee
            realized_net = realized - actual_exit_fee - entry_fee_actual
        logger.info(
            f"✅ Harvested {best_symbol}: freed {self.primary_quote} {freed_cash_net:.4f} | "
            f"Realized Net PnL {realized_net:+.2f} (fees={total_fees:.4f} {self.primary_quote}) | "
            f"Hive ➜ Compound ${compound:.2f} / Harvest ${harvest:.2f}"
        )
        logger.info(f"✅ Harvest order #{result.get('orderId', 'dry-run')}")
        return True

    # ─────────────────────────────────────────────────────────
    # 🌉 Bridge Integration Methods
    # ─────────────────────────────────────────────────────────
    
    def sync_bridge(self):
        """Sync state with Aureon Bridge for Ultimate ↔ Unified communication"""
        if not BRIDGE_AVAILABLE or not self.bridge:
            return
        
        now = time.time()
        if now - self.last_bridge_sync < self.bridge_sync_interval:
            return
        
        try:
            # 1. Update Capital State
            quote_balance = self.get_quote_balance()
            pos_value = sum(
                float(self.ticker_cache.get(s, {}).get('lastPrice', 0)) * p.quantity
                for s, p in self.positions.items()
            )
            total_equity = quote_balance + pos_value
            
            capital_state = CapitalState(
                total_equity=total_equity,
                allocated_capital=pos_value,
                free_capital=quote_balance,
                realized_profit=self.last_realized_net,
                unrealized_profit=sum(
                    (float(self.ticker_cache.get(s, {}).get('lastPrice', 0)) - p.entry_price) * p.quantity
                    for s, p in self.positions.items()
                ),
                total_fees=self.total_fees,
                net_profit=self.last_equity_net,
                trades_count=self.trades,
                wins_count=self.wins,
                win_rate=self.wins / max(1, self.trades),
                exchange_breakdown={
                    'binance': total_equity,
                    'kraken': 0.0,  # Ultimate is Binance-only
                    'alpaca': 0.0,
                }
            )
            self.bridge.update_capital(capital_state)
            
            # 2. Register Open Positions
            for symbol, pos in self.positions.items():
                ticker = self.ticker_cache.get(symbol, {})
                current_price = float(ticker.get('lastPrice', 0)) if ticker else pos.entry_price
                
                bridge_pos = BridgePosition(
                    symbol=symbol,
                    exchange='binance',
                    side='BUY',
                    size=pos.quantity,
                    entry_price=pos.entry_price,
                    current_price=current_price,
                    unrealized_pnl=(current_price - pos.entry_price) * pos.quantity,
                    entry_time=pos.entry_time,
                    owner='ultimate'
                )
                self.bridge.register_position(bridge_pos)
            
            self.last_bridge_sync = now
            
        except Exception as e:
            logger.warning(f"⚠️ Bridge sync error: {e}")
    
    def publish_opportunities_to_bridge(self, opportunities: List[Dict]):
        """Publish top opportunities to bridge for Unified system"""
        if not BRIDGE_AVAILABLE or not self.bridge:
            return
        
        try:
            bridge_opps = []
            for opp in opportunities[:10]:  # Top 10
                bridge_opp = BridgeOpportunity(
                    symbol=opp['symbol'],
                    exchange='binance',
                    side='BUY',
                    score=opp['score'],
                    coherence=opp['coherence'],
                    momentum=opp['change24h'],
                    volume=opp['volume'],
                    price=opp['price'],
                    probability=opp.get('probability'),
                    anomaly_flags=opp.get('anomaly_flags', []),
                    frequency=opp.get('hnc_frequency'),
                    source_system='ultimate'
                )
                bridge_opps.append(bridge_opp)
            
            self.bridge.publish_opportunities(bridge_opps)
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to publish opportunities to bridge: {e}")
    
    def consume_unified_opportunities(self) -> List[Dict]:
        """Get opportunities from Unified system via bridge"""
        if not BRIDGE_AVAILABLE or not self.bridge:
            return []
        
        try:
            # Get opportunities from Unified (Kraken focus)
            bridge_opps = self.bridge.get_opportunities(
                exchange='kraken',
                min_score=CONFIG['MIN_SCORE'],
                max_age_seconds=60.0
            )
            
            # Convert to internal format
            opportunities = []
            for opp in bridge_opps:
                opportunities.append({
                    'symbol': opp.symbol,
                    'price': opp.price,
                    'change24h': opp.momentum,
                    'volume': opp.volume,
                    'score': opp.score,
                    'coherence': opp.coherence,
                    'dominant_node': 'TIGER',  # Default
                    'source': opp.exchange,
                    'hnc_frequency': opp.frequency or 256,
                    'hnc_harmonic': False,
                    'probability': opp.probability or 0.5,
                    'prob_confidence': 0.5,
                    'prob_action': 'BUY',
                    'from_bridge': True
                })
            
            if opportunities:
                logger.info(f"🌉 Received {len(opportunities)} opportunities from Unified")
            
            return opportunities
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to consume Unified opportunities: {e}")
            return []
    
    def check_bridge_commands(self):
        """Process control commands from bridge"""
        if not BRIDGE_AVAILABLE or not self.bridge:
            return
        
        try:
            commands = self.bridge.get_commands('ultimate', max_age_seconds=60.0, clear_after_read=True)
            
            for cmd in commands:
                if cmd.command == 'pause':
                    logger.info(f"🎛️ Trading PAUSED by bridge command")
                    # Implement pause logic if needed
                    
                elif cmd.command == 'resume':
                    logger.info(f"🎛️ Trading RESUMED by bridge command")
                    
                elif cmd.command == 'harvest':
                    min_profit = cmd.params.get('min_profit', 0.0)
                    # Force close winning positions
                    self.harvest_winner_for_liquidity(min_profit)
                    
                elif cmd.command == 'force_exit':
                    target_symbol = cmd.params.get('symbol')
                    if target_symbol and target_symbol in self.positions:
                        logger.info(f"🌉 Force exiting {target_symbol} via bridge command")
                        # Implement force exit logic
                        
        except Exception as e:
            logger.warning(f"⚠️ Bridge command processing error: {e}")

    def update_tickers(self):
        if time.time() - self.last_ticker_update < 2:
            return

        try:
            # Use client abstraction instead of hardcoded URL
            payload = self.client.get_24h_tickers()

            if isinstance(payload, dict):
                # Handle Binance error payloads (e.g. rate limit / IP ban)
                error_code = payload.get('code')
                message = payload.get('msg') or payload.get('message') or str(payload)
                wait_seconds = 5.0
                self.last_ticker_update = time.time() + wait_seconds
                logger.warning(
                    f"Ticker update returned error payload {error_code}: {message}. Backing off for {wait_seconds:.1f}s"
                )
                return

            filtered = {}
            for item in payload:
                symbol = item.get('symbol') if isinstance(item, dict) else None
                if not symbol:
                    continue
                if not any(symbol.endswith(q) for q in self.allowed_quotes):
                    continue
                filtered[symbol] = item

            if filtered:
                self.ticker_cache = filtered
            else:
                logger.warning(
                    "Ticker update returned no symbols matching allowed quotes; retaining previous cache"
                )

            self.last_ticker_update = time.time()

        except Exception as e:
            self.last_ticker_update = time.time()
            logger.error(f"Ticker update failed: {e}")
    
    def scan_opportunities(self) -> List[Dict]:
        """Scan for high-coherence entries with COMMANDO INTELLIGENCE 🦆⚔️"""
        
        # 🦆 Get commando targets (cache for 30 seconds)
        if time.time() - self.last_commando_scan > 30:
            logger.info("🦁 DEPLOYING COMMANDOS FOR PRIDE SCAN...")
            self.commando_cache = self.commandos.get_commando_targets(self.memory, self.allowed_quotes)
            self.last_commando_scan = time.time()
        
        opportunities = []
        env_gamma = float(self.lighthouse_metrics.get('gamma_ratio', 0.0)) if self.lighthouse_metrics else 0.0
        env_distortion = float(self.lighthouse_metrics.get('distortion_index', 0.0)) if self.lighthouse_metrics else 0.0
        env_coherence = float(self.lighthouse_metrics.get('coherence_score', 0.0)) if self.lighthouse_metrics else 0.0
        env_maker_bias = float(self.lighthouse_metrics.get('maker_bias', 0.5)) if self.lighthouse_metrics else 0.5
        
        for symbol, ticker in self.ticker_cache.items():
            if not self.lot_mgr.can_trade(symbol):
                continue
            if self.memory.should_avoid(symbol):
                continue
            quote = self.match_quote_asset(symbol)
            if quote is None:
                continue
            # Allow any allowed quote, not just primary
            if quote not in self.allowed_quotes:
                continue
            
            try:
                price = float(ticker['lastPrice'])
                change = float(ticker['priceChangePercent'])
                volume = float(ticker['quoteVolume'])
                high = float(ticker['highPrice'])
                low = float(ticker['lowPrice'])
                
                if volume < 10000:  # Min $10k volume equivalent
                    continue
                
                volatility = ((high - low) / low * 100) if low > 0 else 0
                coherence = calculate_coherence(change, volume, volatility)
                
                # 🦆 COMMANDO BOOST 🦆
                if self.commando_cache:
                    commando_boost = self.commandos.calculate_commando_boost(symbol, self.commando_cache)
                    coherence *= commando_boost
                
                # 🌈 THE PRISM - HARMONIC NEXUS CORE 🌈
                # Transform fear into love through 5-layer harmonic resonance
                # Level 0: Ψ₀×Ω×Λ×Φ×Σ (528 Hz LOVE SOURCE)
                # Full lambda state for maximum resonance
                prism_state = self.advanced.prism.process(
                    coherence=coherence,
                    volatility=volatility,
                    momentum=change,
                    observer=1.0,  # Default observer magnitude
                    substrate=self.advanced.auris.compute_substrate(volatility, change / 100, volume),
                    echo=0.0,
                    lambda_value=coherence * 2 - 1  # Map coherence to -1,+1
                )
                
                # 💜 SOURCE LAW: The frequency of LOVE (528Hz) is the key 💜
                if prism_state.get('is_love', False):
                    coherence *= 1.5  # Strong boost for LOVE resonance (528Hz)
                    emotion = "LOVE"  # Override emotion - we're in the zone!
                elif prism_state['is_aligned']:
                    coherence *= 1.2  # Boost for harmonic alignment
                else:
                    coherence *= 0.9  # Smaller penalty - don't reject everything
                
                # 📊 DECISION FUSION (4-Model Ensemble) 📊
                fusion_score, fusion_conf = self.advanced.fusion.generate_signal(change, volatility, volume)
                if fusion_score > 0.2:
                    coherence *= (1 + fusion_score * 0.5) # Boost
                elif fusion_score < -0.2:
                    coherence *= 0.5 # Penalty
                
                # Get emotional state
                emotion, freq = get_emotional_state(coherence)
                
                # Debug log for random symbols to diagnose filtering
                if random.random() < 0.002:
                     logger.info(f"🔍 DEBUG {symbol}: Coh={coherence:.3f} Prism(res={prism_state.get('resonance', 0):.2f}, love={prism_state.get('is_love', False)}) Fusion={fusion_score:.2f}")

                # 🦆💎 BIG PLUMS MODE: Enter on coherence alone!
                if coherence >= CONFIG['ENTRY_COHERENCE']:
                    score = abs(change) * coherence * (volume / 10000)
                    score *= (1 + 0.5 * env_gamma)
                    score *= max(0.3, 1 - env_distortion)
                    
                    opportunities.append({
                        'symbol': symbol,
                        'price': price,
                        'change': change,
                        'coherence': coherence,
                        'emotion': emotion,
                        'frequency': freq,
                        'volume': volume,
                        'score': score,
                        'env_gamma': env_gamma,
                        'env_distortion': env_distortion,
                        'env_coherence': env_coherence,
                        'env_maker_bias': env_maker_bias,
                    })
            except Exception as e:
                logger.error(f"❌ CRASH processing {symbol}: {e}")
                continue
        
        opportunities.sort(key=lambda x: x['score'], reverse=True)
        return opportunities
    
    def build_opportunity_from_eco_pick(self, eco_pick: Dict) -> Optional[Dict]:
        """Convert ecosystem recommendation to opportunity format for enter_position"""
        symbol = eco_pick['symbol']
        env_gamma = float(self.lighthouse_metrics.get('gamma_ratio', 0.0)) if self.lighthouse_metrics else 0.0
        env_distortion = float(self.lighthouse_metrics.get('distortion_index', 0.0)) if self.lighthouse_metrics else 0.0
        env_coherence = float(self.lighthouse_metrics.get('coherence_score', 0.0)) if self.lighthouse_metrics else 0.0
        env_maker_bias = float(self.lighthouse_metrics.get('maker_bias', 0.5)) if self.lighthouse_metrics else 0.5
        
        # Get ticker data
        ticker = self.ticker_cache.get(symbol)
        if not ticker:
            logger.warning(f"⚠️ No ticker data for {symbol}")
            return None
        
        # Make sure we can trade this with our allowed quotes
        quote = self.match_quote_asset(symbol)
        if quote not in self.allowed_quotes:
            logger.warning(f"⚠️ {symbol} requires {quote} which is not in allowed quotes {self.allowed_quotes}")
            return None
        
        try:
            price = float(ticker['lastPrice'])
            change = float(ticker.get('priceChangePercent', eco_pick.get('change', 0)))
            volume = float(ticker.get('quoteVolume', 0))
            high = float(ticker.get('highPrice', price))
            low = float(ticker.get('lowPrice', price))
            
            volatility = ((high - low) / low * 100) if low > 0 else 0
            coherence = calculate_coherence(change, volume, volatility)
            
            # Apply commando-specific boosts
            if eco_pick['commando'] == 'wolf':
                coherence *= 1.25  # Wolf gets momentum boost
            elif eco_pick['commando'] == 'ants':
                coherence *= 1.10  # Ants get floor finder boost
            elif eco_pick['commando'] == 'hummingbird':
                coherence *= 1.15  # Hummingbird gets rotation boost
            
            emotion, freq = get_emotional_state(coherence)
            score = abs(change) * coherence * (volume / 10000)
            score *= (1 + 0.5 * env_gamma)
            score *= max(0.3, 1 - env_distortion)
            
            opp = {
                'symbol': symbol,
                'price': price,
                'change': change,
                'coherence': coherence,
                'emotion': emotion,
                'frequency': freq,
                'volume': volume,
                'score': score,
                'commando': eco_pick['commando'],
                'reason': eco_pick.get('reason', ''),
                'env_gamma': env_gamma,
                'env_distortion': env_distortion,
                'env_coherence': env_coherence,
                'env_maker_bias': env_maker_bias,
            }
            
            # Add hummingbird-specific tight TP/SL if present
            if 'tp' in eco_pick:
                opp['tp_override'] = eco_pick['tp']
            if 'sl' in eco_pick:
                opp['sl_override'] = eco_pick['sl']
            
            return opp
            
        except Exception as e:
            logger.error(f"❌ Error building opportunity for {symbol}: {e}")
            return None
    
    def enter_position(self, opp: Dict, quote_balance: float, commando: str = 'lion') -> bool:
        """PING - Enter position with PRIME SCALING (commando-aware)"""
        symbol = opp['symbol']
        quote_asset = self.match_quote_asset(symbol) or self.primary_quote
        
        # Allow trading if quote is in allowed list, even if not primary
        if quote_asset not in self.allowed_quotes:
            logger.warning(f"⚠️ Skipping {symbol}: requires {quote_asset} which is not in allowed quotes {self.allowed_quotes}")
            return False
            
        # If using a non-primary quote, ensure we check THAT balance, not just the passed quote_balance (which is usually primary)
        if quote_asset != self.primary_quote:
            # Fetch specific balance for this asset
            quote_balance = self.get_quote_balance(quote_asset)
            if quote_balance < CONFIG['MIN_TRADE_NOTIONAL']:
                 logger.warning(f"⚠️ Skipping {symbol}: Insufficient {quote_asset} balance ({quote_balance:.2f})")
                 return False

        env_gamma = float(opp.get('env_gamma', self.lighthouse_metrics.get('gamma_ratio', 0.0) if self.lighthouse_metrics else 0.0))
        env_distortion = float(opp.get('env_distortion', self.lighthouse_metrics.get('distortion_index', 0.0) if self.lighthouse_metrics else 0.0))
        env_coherence = float(opp.get('env_coherence', self.lighthouse_metrics.get('coherence_score', 0.0) if self.lighthouse_metrics else 0.0))
        env_maker_bias = float(opp.get('env_maker_bias', self.lighthouse_metrics.get('maker_bias', 0.5) if self.lighthouse_metrics else 0.5))
        
        # Fire multiplier
        fire_mult = self.fire.get_size_multiplier()
        
        # Prime multiplier (HiveController style!)
        prime_idx = self.trades % len(PRIMES)
        prime = PRIMES[prime_idx]
        # Source Law 10-9-1: Keep positions at ~9%, Prime adds subtle variation (0.95x to 1.05x)
        prime_mult = 0.95 + (prime % 10) * 0.01  # Maps prime to 0.95-1.05 range
        
        # Kelly Criterion sizing (Quackers RiskManager)
        win_rate = self.memory.get_win_rate()
        reward_risk = (1.5 + opp['coherence']) * max(0.7, 1 - 0.3 * env_distortion) + (env_gamma * 0.5)
        kelly_fraction = kelly_criterion(win_rate, reward_risk)
        kelly_mult = 1.0 + kelly_fraction * 0.1  # Subtle Kelly: 1.0x to 1.1x max
        
        # Position size = Base (9%) * Fire * Prime * Kelly
        # Source Law 10-9-1: 10 positions, 9% each, 1 reserve (10% cash)
        base_size = quote_balance * CONFIG['POSITION_SIZE_PCT']
        size_quote = base_size * fire_mult * prime_mult * kelly_mult
        env_multiplier = (1 + 0.4 * env_gamma) * max(0.6, 1 - env_distortion) * (0.8 + 0.4 * env_coherence)
        env_multiplier *= (0.9 + 0.2 * env_maker_bias)
        size_quote *= env_multiplier
        buffer = max(0.25, quote_balance * 0.05)  # keep at least 5% or 0.25 units
        size_quote = min(size_quote, max(0.0, quote_balance - buffer))
        
        # Note: record_hunt moved to AFTER successful trade execution
        
        logger.info(
            f"💵 SIZE CHECK: {self.primary_quote} {size_quote:.4f} vs MIN={CONFIG['MIN_TRADE_NOTIONAL']:.2f}"
        )
        if size_quote < CONFIG['MIN_TRADE_NOTIONAL']:
            logger.warning(
                f"❌ SIZE TOO SMALL: {self.primary_quote} {size_quote:.4f} < {CONFIG['MIN_TRADE_NOTIONAL']:.2f}"
            )
            return False
        
        qty = size_quote / opp['price']
        qty_str = self.lot_mgr.format_qty(symbol, qty)
        
        notional = float(qty_str) * opp['price']
        min_notional = self.lot_mgr.get_min_notional(symbol)
        logger.info(
            f"💰 NOTIONAL CHECK: {self.primary_quote} {notional:.4f} vs MIN={min_notional:.2f}"
        )
        if notional < min_notional:
            logger.warning(
                f"❌ NOTIONAL TOO SMALL: {self.primary_quote} {notional:.4f} < {min_notional:.2f}"
            )
            return False
        
        logger.info(f"""
╔════════════════════════════════════════════════════════════════╗
║ 🏓 PING! Entering {symbol}
║────────────────────────────────────────────────────────────────
║ Coherence:  Γ={opp['coherence']:.3f} ({opp['emotion']})
║ Change:     {opp['change']:+.2f}%
║ Quantity:   {qty_str} @ ${opp['price']:.4f}
║ Notional:   {self.primary_quote} {notional:.4f}
║ Fire:       {self.fire.get_status()} ({fire_mult:.2f}x)
║ Prime[{prime_idx}]: {prime} ({prime_mult:.3f}x)
║ Kelly:      WR={win_rate*100:.1f}% | R:R={reward_risk:.2f} ({kelly_mult:.2f}x) ✨
║ Field:      Γ={env_coherence:.2f} | γ={env_gamma:.2f} | Δ={env_distortion:.2f} | Maker={env_maker_bias:.2f}
╚════════════════════════════════════════════════════════════════╝
""")
        
        try:
            # 💰 BEFORE TRADE BALANCE
            balance_before = self.get_quote_balance()
            
            result = self.client.place_market_order(
                symbol, 'BUY', quantity=float(qty_str)
            )
            
            # 💰 AFTER TRADE BALANCE
            balance_after = self.get_quote_balance()
            spent = balance_before - balance_after
            logger.info(f"💰 BALANCE: Before=${balance_before:.4f} → After=${balance_after:.4f} | Spent=${spent:.4f}")

            # 🦆 DRY-RUN SIMULATION MODE: Simulate trade for paper trading
            if result.get('dryRun'):
                logger.info("🧪 DRY-RUN MODE: Simulating trade execution...")
                # Simulate as if the trade went through
                spent = notional  # Pretend we spent the notional amount
                result['orderId'] = f"DRY-{int(time.time()*1000)}"
                result['fills'] = [{'price': str(opp['price']), 'qty': qty_str, 'commission': '0', 'commissionAsset': self.primary_quote}]
            elif result.get('orderId') is None:
                logger.error("❌ Order not confirmed on Binance (missing orderId); aborting entry.")
                return False
            elif spent <= 0:
                # Guard against false positives from simulation or rounding noise (live mode only)
                logger.error("❌ No spend detected after BUY; aborting entry.")
                return False
            elif spent < (min_notional * 0.5):
                logger.warning(
                    f"⚠️ Spend ${spent:.4f} below verification threshold (${min_notional*0.5:.2f}); treating as failed entry."
                )
                return False
            
            # Calculate Quackers-style volatility-based stops
            ticker = self.ticker_cache.get(symbol, {})
            high_24h = float(ticker.get('highPrice', opp['price']))
            low_24h = float(ticker.get('lowPrice', opp['price']))
            volatility = (high_24h - low_24h) / opp['price'] if opp['price'] > 0 else 0.01
            normalized_vol = max(0.001, volatility)
            
            # Dynamic stop loss = entry - (price * volatility * multiplier)
            stop_distance = opp['price'] * normalized_vol * CONFIG.get('STOP_LOSS_MULTIPLIER', 1.2)
            reward_risk_ratio = CONFIG.get('REWARD_RISK_BASE', 2.0) + opp['coherence']
            tp_distance = stop_distance * reward_risk_ratio
            
            stop_loss_price = opp['price'] - stop_distance
            take_profit_price = opp['price'] + tp_distance
            
            # 🐝 Hummingbird uses tighter TP/SL
            if commando == 'hummingbird' and 'tp_override' in opp:
                take_profit_price = opp['price'] * (1 + opp['tp_override'])
                stop_loss_price = opp['price'] * (1 + opp['sl_override'])
            
            self.positions[symbol] = Position(
                symbol=symbol,
                entry_price=opp['price'],
                quantity=float(qty_str),
                entry_time=time.time(),
                coherence=opp['coherence'],
                notional_usd=notional,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                commando=commando,  # 🦆 Track which commando owns this
                field_gamma=env_gamma,
                field_distortion=env_distortion,
                field_coherence=env_coherence,
                field_maker_bias=env_maker_bias,
            )
            # Record actual entry fee from fills if available; fallback to approx
            actual_fee = self.client.compute_order_fees_in_quote(result, self.primary_quote)
            if actual_fee and actual_fee > 0:
                self.positions[symbol].fees_quote += actual_fee
                self.total_fees += actual_fee  # Business 101: Track expense
                logger.info(f"💸 Entry fee (actual): {self.primary_quote} {actual_fee:.6f}")
            else:
                entry_fee = notional * CONFIG.get('TAKER_FEE_PCT', 0.0)
                self.positions[symbol].fees_quote += entry_fee
                self.total_fees += entry_fee  # Business 101: Track expense
                logger.info(f"💸 Entry fee (approx): {self.primary_quote} {entry_fee:.6f}")
            
            logger.info(f"✅ Filled: Order #{result.get('orderId')}")
            self.trades += 1
            
            # Record the successful hunt (Quackers ElephantMemory)
            self.memory.record_hunt(symbol, opp.get('volume', 0), opp.get('change', 0))
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Buy failed: {e}")
            return False
    
    def check_exits(self):
        """PONG - Check exit conditions with Piano intelligence"""
        if not self.business_green_light:
            threshold = CONFIG.get('BUSINESS_GREEN_THRESHOLD', 0.0)
            logger.info(
                f"🚫 BUSINESS HOLD: Realized Net ${self.last_realized_net:+.2f} <= ${threshold:+.2f}. Skipping exit checks this cycle."
            )
            return
        
        for symbol in list(self.positions.keys()):
            pos = self.positions[symbol]
            ticker = self.ticker_cache.get(symbol)
            
            if not ticker:
                continue
            
            price = float(ticker['lastPrice'])
            entry = pos.entry_price
            pnl_pct = (price - entry) / entry
            pnl_usd = pos.quantity * (price - entry)
            
            # Recalculate coherence + Piano components
            change = float(ticker['priceChangePercent'])
            volume = float(ticker['quoteVolume'])
            high = float(ticker['highPrice'])
            low = float(ticker['lowPrice'])
            volatility = ((high - low) / low * 100) if low > 0 else 0
            current_coherence = calculate_coherence(change, volume, volatility)
            
            # Update Piano state
            velocity_factor = 1.0 + abs(volatility / 100) * 50
            velocity_factor = min(velocity_factor, 3.0)
            
            pos.substrate = min(1.0, volume / 100000.0) * velocity_factor
            pos.observer = 0.5 + min(abs(pnl_pct) * 5, 0.3)  # Attention from P&L
            pos.echo = current_coherence * 0.8  # Echo from coherence
            pos.lambda_value = pos.substrate + 1.2 * pos.observer + pos.echo
            
            # Determine rainbow state
            if current_coherence > 0.9:
                pos.rainbow_state = "UNITY"
            elif current_coherence > 0.8:
                pos.rainbow_state = "AWE"
            elif current_coherence > 0.7:
                pos.rainbow_state = "LOVE"
            elif current_coherence > 0.5:
                pos.rainbow_state = "RESONANCE"
            elif current_coherence > 0.3:
                pos.rainbow_state = "FORMING"
            else:
                pos.rainbow_state = "FEAR"
            
            # Calculate RSI (simplified - using recent price action)
            pos.rsi = 50.0 + (change * 2)  # Rough approximation
            pos.rsi = max(0, min(100, pos.rsi))
            
            # Generate Piano signal
            signal, confidence = generate_piano_signal(pos, current_coherence, change, pos.rsi)

            # Partial take-profit: sell half once threshold reached
            base_partial = CONFIG.get('PARTIAL_TP_PCT', 0.005)
            partial_threshold = base_partial * (1 + pos.field_distortion * 0.5) * max(0.5, 1 - pos.field_gamma)
            if (not pos.partial_taken) and pnl_pct >= partial_threshold:
                partial_qty = pos.quantity * 0.5
                qty_str = self.lot_mgr.format_qty(symbol, partial_qty)
                qty_float = float(qty_str)
                min_qty = self.lot_mgr.get_min_qty(symbol)
                min_notional = self.lot_mgr.get_min_notional(symbol)
                notional = qty_float * price
                logger.info(f"💎 PARTIAL TP CHECK {symbol}: pnl={pnl_pct*100:.2f}% qty={qty_float} min_qty={min_qty} notional={notional:.2f} min_notional={min_notional}")
                if qty_float > 0 and qty_float >= min_qty and qty_float < pos.quantity and notional >= min_notional:
                    try:
                        result = self.client.place_market_order(symbol, 'SELL', quantity=qty_float)
                        fee_pct = CONFIG.get('TAKER_FEE_PCT', 0.0)
                        sell_fee_actual = self.client.compute_order_fees_in_quote(result, self.primary_quote)
                        sell_fee = sell_fee_actual if sell_fee_actual and sell_fee_actual > 0 else price * qty_float * fee_pct
                        # Use proportional share of tracked entry fees (actual from order response)
                        qty_fraction = qty_float / pos.quantity if pos.quantity > 0 else 0.0
                        entry_fee_actual = pos.fees_quote * qty_fraction
                        realized_partial = qty_float * (price - pos.entry_price)
                        realized_net = realized_partial - sell_fee - entry_fee_actual
                        self.total_gross_pnl += realized_partial
                        self.total_fees += sell_fee
                        compound, harvest = self.hive.process_profit(realized_net)
                        self.memory.record(symbol, realized_net)
                        pos.fees_quote -= entry_fee_actual
                        pos.fees_quote = max(pos.fees_quote, 0.0)
                        pos.quantity -= qty_float
                        pos.notional_usd = pos.quantity * pos.entry_price
                        pos.partial_taken = True
                        logger.info(
                            f"💠 Partial TP {symbol}: sold {qty_str} @ ${price:.4f} | Net ${realized_net:+.2f} "
                            f"(fees={sell_fee+entry_fee_actual:.4f} {self.primary_quote}) | Hive ➜ Compound ${compound:.2f} / Harvest ${harvest:.2f}"
                        )
                        # Move to next position after partial trim
                        continue
                    except Exception as exc:
                        logger.error(f"❌ Partial TP failed for {symbol}: {exc}")
            
            should_exit = False
            reason = ""
            
            loss_floor = -0.004 * (1 + pos.field_distortion)
            gain_floor = 0.005 * max(0.6, 1 - pos.field_distortion) * (0.8 + pos.field_gamma)
            gain_floor = max(0.003, gain_floor)

            # 🎯 PRIORITY 1: CUT TINY LOSSES FAST (-0.40% hard stop)
            if pnl_pct <= loss_floor:
                should_exit = True
                reason = f"✂️ TINY LOSS CUT ({pnl_pct*100:.2f}%)"
            # 🎯 PRIORITY 2: TAKE REAL PROFITS (+0.50%+ for meaningful gains)
            elif pnl_pct >= gain_floor:
                should_exit = True
                reason = f"💎 PROFIT TARGET ({pnl_pct*100:.2f}%)"
            # Exit conditions with Quackers dynamic stops + Piano intelligence
            elif pos.take_profit_price > 0 and price >= pos.take_profit_price:
                should_exit = True
                reason = f"💰 TAKE PROFIT (Dynamic ${pos.take_profit_price:.4f})"
            elif pos.stop_loss_price > 0 and price <= pos.stop_loss_price:
                should_exit = True
                reason = f"🛑 STOP LOSS (Dynamic ${pos.stop_loss_price:.4f})"
            elif signal in ["STRONG_SELL", "SELL"] and confidence > 0.5:
                should_exit = True
                reason = f"🎹 PIANO SELL ({signal})"
            elif current_coherence < CONFIG['EXIT_COHERENCE']:
                should_exit = True
                reason = "⚠️ COHERENCE BREAK"
            elif pos.rainbow_state == "FEAR":
                should_exit = True
                reason = "🌈 RAINBOW FEAR"
            elif time.time() - pos.entry_time > CONFIG['POSITION_TIMEOUT_SEC']:
                should_exit = True
                reason = "⏰ TIMEOUT"
            
            if should_exit:
                qty_str = self.lot_mgr.format_qty(symbol, pos.quantity)
                
                logger.info(f"""
╔════════════════════════════════════════════════════════════════╗
║ 🏓 PONG! Exiting {symbol}
║────────────────────────────────────────────────────────────────
║ Reason:     {reason}
║ Entry:      ${entry:.4f}
║ Exit:       ${price:.4f}
║ P&L:        {pnl_pct*100:+.2f}% (${pnl_usd:+.2f})
║ Coherence:  Γ={current_coherence:.3f} (was {pos.coherence:.3f})
║ 🎹 Piano:   Λ={pos.lambda_value:.2f} | 🌈{pos.rainbow_state}
║ Signal:     {signal} ({confidence:.0%}) | RSI={pos.rsi:.0f}
╚════════════════════════════════════════════════════════════════╝
""")
                
                try:
                    # 💰 BEFORE SELL BALANCE
                    balance_before = self.get_quote_balance()
                    
                    # Net PnL and fees: use actual tracked entry fees
                    fee_pct = CONFIG.get('TAKER_FEE_PCT', 0.0)
                    result = self.client.place_market_order(
                        symbol, 'SELL', quantity=float(qty_str)
                    )
                    
                    # 💰 AFTER SELL BALANCE
                    balance_after = self.get_quote_balance()
                    received = balance_after - balance_before
                    # Verify live execution and sufficient receipt
                    min_notional = self.lot_mgr.get_min_notional(symbol)
                    if result.get('dryRun') or (result.get('orderId') is None):
                        logger.error("❌ Sell not confirmed on Binance (dryRun or missing orderId); keeping position open.")
                        continue
                    if received <= 0:
                        logger.error("❌ No quote received after SELL; keeping position open.")
                        continue
                    if received < (min_notional * 0.5):
                        logger.warning(
                            f"⚠️ Received ${received:.4f} below verification threshold (${min_notional*0.5:.2f}); keeping position open."
                        )
                        continue
                    
                    # Prefer actual commission from order; fallback to approx
                    actual_sell_fee = self.client.compute_order_fees_in_quote(result, self.primary_quote)
                    entry_fee_actual = pos.fees_quote  # Full tracked entry fee
                    sell_fee = actual_sell_fee if actual_sell_fee and actual_sell_fee > 0 else (price * pos.quantity * fee_pct)
                    
                    # Business 101: Track Gross vs Fees
                    self.total_gross_pnl += pnl_usd
                    self.total_fees += sell_fee
                    
                    realized_net = pnl_usd - sell_fee - entry_fee_actual
                    
                    logger.info(f"💰 BALANCE: Before=${balance_before:.4f} → After=${balance_after:.4f} | Received=${received:.4f}")
                    logger.info(f"✅ Sold: Order #{result.get('orderId')} | Fees: entry={entry_fee_actual:.4f} {self.primary_quote}, sell={(sell_fee):.4f} {self.primary_quote}")
                    logger.info(f"📊 NET PROFIT CHECK: Gross=${pnl_usd:+.4f} - Fees=${(entry_fee_actual+sell_fee):.4f} = Net=${realized_net:+.4f}")
                    
                    # Queen Hive processing on net PnL
                    compound, harvest = self.hive.process_profit(realized_net)
                    logger.info(f"👑 Hive: Compound ${compound:.2f} | Harvest ${harvest:.2f} | Net PnL ${realized_net:+.2f}")
                    
                    # Memory recording
                    self.memory.record(symbol, realized_net)
                    
                    if realized_net >= 0:
                        self.wins += 1
                        pos.bounces += 1
                    
                    # 🦆 Notify commandos of exit
                    self.commandos.record_exit(symbol, realized_net)
                    
                    # 🌉 Record trade in bridge
                    if BRIDGE_AVAILABLE and self.bridge:
                        self.bridge.record_trade(
                            profit=pnl_usd,
                            fee=entry_fee_actual + sell_fee,
                            success=(realized_net > 0)
                        )
                        self.bridge.unregister_position('binance', symbol)
                    
                    del self.positions[symbol]
                    
                except Exception as e:
                    logger.error(f"❌ Sell failed: {e}")
    
    def display_status(self):
        """Display current status"""
        quote_balance = self.get_quote_balance()
        pos_value = sum(
            float(self.ticker_cache.get(s, {}).get('lastPrice', 0)) * p.quantity
            for s, p in self.positions.items()
        )
        total = quote_balance + pos_value

        # 🌈 Feed Lighthouse history with current total equity
        now_ts = time.time()
        self.lighthouse_history.append((now_ts, total))
        if (
            len(self.lighthouse_history) >= 64
            and (now_ts - self.last_lighthouse_compute) >= 10
        ):
            ts_arr, val_arr = zip(*self.lighthouse_history)
            try:
                metrics = self.lighthouse_engine.analyze_series(ts_arr, val_arr)
            except Exception as exc:
                logger.debug(f"Lighthouse metrics skipped: {exc}")
            else:
                self.lighthouse_metrics = metrics
                self.last_lighthouse_compute = now_ts
        
        # Calculate Net Profit for the session
        equity_net = total - self.initial_capital
        equity_net_pct = (equity_net / self.initial_capital * 100) if self.initial_capital > 0 else 0.0
        
        # Business 101: Gross - Fees = Net (include unrealized so we know if we're safe to exit)
        unrealized_pnl = sum(
            (float(self.ticker_cache.get(s, {}).get('lastPrice', 0)) - p.entry_price) * p.quantity
            for s, p in self.positions.items()
        )
        live_gross = self.total_gross_pnl + unrealized_pnl
        realized_net = self.total_gross_pnl - self.total_fees
        business_net = live_gross - self.total_fees
        
        # Persist business state for exit gating
        threshold = CONFIG.get('BUSINESS_GREEN_THRESHOLD', 0.0)
        self.last_equity_net = equity_net
        self.last_realized_net = realized_net
        self.business_green_light = realized_net >= threshold
        
        lighthouse_metrics = self.lighthouse_metrics or {}
        coherence_score = float(lighthouse_metrics.get('coherence_score', 0.0))
        gamma_ratio = float(lighthouse_metrics.get('gamma_ratio', 0.0))
        distortion_index = float(lighthouse_metrics.get('distortion_index', 0.0))
        maker_bias = float(lighthouse_metrics.get('maker_bias', 0.5))
        field_state = lighthouse_metrics.get('emotion', 'FORMING')

        win_rate = self.wins / max(1, self.trades)
        
        # Update fire state with trading activity
        avg_vol = sum(
            float(t.get('priceChangePercent', 0)) 
            for t in self.ticker_cache.values()
        ) / max(1, len(self.ticker_cache))
        vol_factor = abs(avg_vol) / 100
        vol_factor *= 1 + gamma_ratio
        adjusted_win = max(0.0, min(1.0, win_rate * max(0.0, 1 - 0.5 * distortion_index)))
        self.fire.update(vol_factor, adjusted_win, trades_this_cycle=len(self.positions))
        
        emotion, freq = get_emotional_state(win_rate)
        
        # Business 101 Status
        if realized_net > 0.0:
            biz_status = "✅ PROFITABLE"
        elif realized_net < 0.0:
            biz_status = "🔻 DEFICIT"
        else:
            biz_status = "⏳ WARMING UP" if self.trades == 0 else "⚖️ BREAKEVEN"
        
        # Role emoji
        role_emoji = {'BUYER': '💰', 'SELLER': '💎', 'WATCHER': '👁️', 'BALANCED': '⚖️'}.get(self.bot_role, '🦆')

        real_equity = self.get_real_exchange_equity()
        if real_equity.get('error'):
            binance_line = f"║ 🏦 Binance:  ⚠️ {real_equity['error']}"
        elif real_equity.get('total') is not None and real_equity.get('baseline') is not None:
            delta = real_equity.get('delta') or 0.0
            pct = real_equity.get('pct') or 0.0
            baseline_ts = real_equity.get('baseline_ts') or 'baseline'
            binance_line = f"║ 🏦 Binance:  ${real_equity['total']:.2f} | Δ ${delta:+.2f} ({pct:+.2f}%) vs {baseline_ts}"
        elif real_equity.get('total') is not None:
            binance_line = f"║ 🏦 Binance:  ${real_equity['total']:.2f} (no baseline)"
        else:
            binance_line = "║ 🏦 Binance:  (no data)"

        if self.lighthouse_metrics:
            lighthouse_line = (
                f"║ 🌈 Lighthouse: Γ {coherence_score:.2f} | γ {gamma_ratio:.2f} | Δ {distortion_index:.2f} | Maker {maker_bias:.2f}"
            )
            field_line = f"║ 🧭 Field State: {field_state}"
        else:
            lighthouse_line = "║ 🌈 Lighthouse: calibrating signal..."
            field_line = "║ 🧭 Field State: FORMING"

        logger.info(f"""
╔════════════════════════════════════════════════════════════════╗
║ {role_emoji} AUREON {self.bot_role} 🦆 COMMANDOS | Cycle {self.cycle:4d}
║────────────────────────────────────────────────────────────────
    ║ 💵 {self.primary_quote}:  {quote_balance:.4f}
║ 💼 Positions: ${pos_value:.2f} ({len(self.positions)}/{CONFIG['MAX_POSITIONS']})
║ 📊 Total:     ${total:.2f} | Equity Net: ${equity_net:+.2f} ({equity_net_pct:+.2f}%)
║ 📉 Business:  Realized ${realized_net:+.2f} | Live ${business_net:+.2f} (≥ ${threshold:+.2f}? {self.business_green_light})
{binance_line}
{lighthouse_line}
{field_line}
║────────────────────────────────────────────────────────────────
║ 🏆 Trades: {self.trades} | Wins: {self.wins} | WR: {win_rate*100:.1f}% | {biz_status}
║ 👑 Hive:  Compound ${self.hive.compounded:.2f} | Harvest ${self.hive.harvested:.2f}
║ 🔥 Fire:  {self.fire.get_status()} | {emotion} ({freq:.0f}Hz)
║────────────────────────────────────────────────────────────────
║ 🏆 Trades: {self.trades} | Wins: {self.wins} | WR: {win_rate*100:.1f}%
║ 👑 Hive:  Compound ${self.hive.compounded:.2f} | Harvest ${self.hive.harvested:.2f}
║ 🔥 Fire:  {self.fire.get_status()} | {emotion} ({freq:.0f}Hz)
║────────────────────────────────────────────────────────────────
{self.commandos.get_status()}║
╚════════════════════════════════════════════════════════════════╝
""")
        
        # Show active positions
        if self.positions:
            logger.info("📊 ACTIVE POSITIONS:")
            for sym, pos in self.positions.items():
                ticker = self.ticker_cache.get(sym, {})
                price = float(ticker.get('lastPrice', 0))
                pnl_pct = ((price - pos.entry_price) / pos.entry_price * 100) if price > 0 else 0
                age_min = (time.time() - pos.entry_time) / 60
                
                logger.info(
                    f"  {sym:12} | Entry ${pos.entry_price:.4f} | "
                    f"Now ${price:.4f} | {pnl_pct:+.2f}% | {age_min:.0f}m"
                )
    
    # ═══════════════════════════════════════════════════════════
    # 🌉 BRIDGE INTEGRATION METHODS
    # ═══════════════════════════════════════════════════════════
    
    def sync_bridge(self):
        """Sync state with bridge for Unified ↔ Ultimate communication"""
        if not self.bridge_enabled or not self.bridge:
            return
        
        now = time.time()
        if now - self.last_bridge_sync < self.bridge_sync_interval:
            return
        
        try:
            # Calculate current equity
            quote_balance = self.get_quote_balance()
            pos_value = sum(
                float(self.ticker_cache.get(s, {}).get('lastPrice', 0)) * p.quantity
                for s, p in self.positions.items()
            )
            total_equity = quote_balance + pos_value
            
            # 1. Update Capital State
            capital_state = CapitalState(
                total_equity=total_equity,
                allocated_capital=sum(pos.entry_price * pos.quantity for pos in self.positions.values()),
                free_capital=quote_balance,
                realized_profit=self.total_gross_pnl,
                unrealized_profit=sum(
                    (float(self.ticker_cache.get(s, {}).get('lastPrice', 0)) - p.entry_price) * p.quantity
                    for s, p in self.positions.items()
                ),
                total_fees=self.total_fees,
                net_profit=self.total_gross_pnl - self.total_fees,
                trades_count=self.trades,
                wins_count=self.wins,
                win_rate=self.wins / max(1, self.trades),
                exchange_breakdown={'binance': total_equity}  # Ultimate is Binance-focused
            )
            self.bridge.update_capital(capital_state)
            
            # 2. Register Open Positions
            for symbol, pos in self.positions.items():
                current_price = float(self.ticker_cache.get(symbol, {}).get('lastPrice', pos.entry_price))
                bridge_pos = BridgePosition(
                    symbol=symbol,
                    exchange='binance',
                    side='BUY',
                    size=pos.quantity,
                    entry_price=pos.entry_price,
                    current_price=current_price,
                    unrealized_pnl=(current_price - pos.entry_price) * pos.quantity,
                    entry_time=pos.entry_time,
                    owner='ultimate'
                )
                self.bridge.register_position(bridge_pos)
            
            self.last_bridge_sync = now
            
        except Exception as e:
            logger.warning(f"⚠️ Bridge sync error: {e}")
    
    def publish_opportunities_to_bridge(self):
        """Publish commando targets as opportunities to bridge"""
        if not self.bridge_enabled or not self.bridge or not self.commando_cache:
            return
        
        try:
            bridge_opps = []
            for symbol, target_data in list(self.commando_cache.items())[:10]:  # Top 10
                ticker = self.ticker_cache.get(symbol, {})
                price = float(ticker.get('lastPrice', 0))
                volume = float(ticker.get('quoteVolume', 0))
                change = float(ticker.get('priceChangePercent', 0))
                
                if price == 0:
                    continue
                
                # Get coherence from advanced intelligence
                coherence = self.advanced.auris.compute_coherence_simple(change, volume)
                
                bridge_opp = BridgeOpportunity(
                    symbol=symbol,
                    exchange='binance',
                    side='BUY',
                    score=target_data.get('score', 50),
                    coherence=coherence,
                    momentum=change,
                    volume=volume,
                    price=price,
                    source_system='ultimate'
                )
                bridge_opps.append(bridge_opp)
            
            if bridge_opps:
                self.bridge.publish_opportunities(bridge_opps)
                logger.debug(f"📡 Published {len(bridge_opps)} Ultimate opportunities to bridge")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to publish opportunities to bridge: {e}")
    
    def consume_unified_opportunities(self) -> List[str]:
        """Get opportunity symbols from Unified system via bridge"""
        if not self.bridge_enabled or not self.bridge:
            return []
        
        try:
            # Get Kraken opportunities from Unified
            bridge_opps = self.bridge.get_opportunities(
                exchange='kraken',
                min_score=40.0,
                max_age_seconds=60.0
            )
            
            # Convert to symbols list for commando consideration
            symbols = [opp.symbol for opp in bridge_opps[:5]]  # Top 5
            
            if symbols:
                logger.info(f"🌉 Received {len(symbols)} opportunities from Unified: {symbols[:3]}")
            
            return symbols
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to consume Unified opportunities: {e}")
            return []
    
    def check_bridge_commands(self):
        """Process control commands from bridge"""
        if not self.bridge_enabled or not self.bridge:
            return
        
        try:
            commands = self.bridge.get_commands('ultimate', max_age_seconds=60.0, clear_after_read=True)
            
            for cmd in commands:
                if cmd.command == 'harvest':
                    min_profit = cmd.params.get('min_profit', 0.0)
                    logger.info(f"🎛️ Harvest command received (min_profit=${min_profit})")
                    # Force close winning positions
                    for symbol, pos in list(self.positions.items()):
                        ticker = self.ticker_cache.get(symbol)
                        if ticker:
                            price = float(ticker['lastPrice'])
                            pnl = (price - pos.entry_price) * pos.quantity
                            if pnl >= min_profit:
                                logger.info(f"🌉 Harvesting {symbol} (${pnl:+.2f}) via bridge command")
                                self.force_exit_position(symbol, "bridge_harvest")
                    
                elif cmd.command == 'force_exit':
                    target_symbol = cmd.params.get('symbol')
                    if target_symbol and target_symbol in self.positions:
                        logger.info(f"🌉 Force exiting {target_symbol} via bridge command")
                        self.force_exit_position(target_symbol, "bridge_force_exit")
                        
        except Exception as e:
            logger.warning(f"⚠️ Bridge command processing error: {e}")
    
    def force_exit_position(self, symbol: str, reason: str):
        """Force exit a position (used by bridge commands)"""
        if symbol not in self.positions:
            return
        
        pos = self.positions[symbol]
        ticker = self.ticker_cache.get(symbol)
        if not ticker:
            return
        
        price = float(ticker['lastPrice'])
        try:
            qty_str = self.lot_mgr.format_qty(symbol, pos.quantity)
            result = self.client.place_market_order(symbol, 'SELL', quantity=float(qty_str))
            
            # Calculate P&L
            fee_pct = CONFIG.get('TAKER_FEE_PCT', 0.001)
            actual_sell_fee = self.client.compute_order_fees_in_quote(result, self.primary_quote)
            sell_fee = actual_sell_fee if actual_sell_fee and actual_sell_fee > 0 else (price * pos.quantity * fee_pct)
            realized = pos.quantity * (price - pos.entry_price)
            realized_net = realized - sell_fee - pos.fees_quote
            
            self.total_gross_pnl += realized
            self.total_fees += sell_fee
            
            # Record in bridge
            if self.bridge_enabled and self.bridge:
                self.bridge.record_trade(
                    profit=realized,
                    fee=sell_fee,
                    success=(realized_net >= 0)
                )
                self.bridge.unregister_position('binance', symbol)
            
            compound, harvest = self.hive.process_profit(realized_net)
            self.memory.record(symbol, realized_net)
            if realized_net >= 0:
                self.wins += 1
            self.commandos.record_exit(symbol, realized_net)
            del self.positions[symbol]
            
            logger.info(f"✅ Force exit complete: {symbol} | Net ${realized_net:+.2f}")
            
        except Exception as e:
            logger.error(f"❌ Force exit failed for {symbol}: {e}")
    
    def run(self, duration_sec: int = 3600):
        """Run the ultimate trader"""
        logger.info("""
╔════════════════════════════════════════════════════════════════╗
║                                                                
║            🌌 AUREON ULTIMATE 🌌                               
║                                                                
║  ALL 27 SYSTEMS UNIFIED INTO ONE BIG PYTHON                   
║                                                                
║  "If you don't quit, you can't lose!"                         
║  "We're making history!" 🎵                                    
║                                                                
╚════════════════════════════════════════════════════════════════╝
""")
        
        # Consolidate stray balances before firing
        self.consolidate_balances()
        
        # Update initial capital after consolidation to reflect true starting equity
        self.initial_capital = self.get_quote_balance()
        
        start = time.time()
        deadlock_cycles = 0  # Track cycles stuck without capital
        
        while time.time() - start < duration_sec:
            self.cycle += 1
            
            self.update_tickers()
            
            # 🌉 Sync with Bridge
            if BRIDGE_AVAILABLE and self.bridge:
                self.sync_bridge()
                self.check_bridge_commands()
            
            self.display_status()
            
            # 🦆⚔️ ROLE-BASED EXECUTION ⚔️🦆
            # SELLER bots: Only manage exits
            # BUYER bots: Only find entries
            # WATCHER bots: Only scan (dry run)
            # BALANCED: Do everything
            
            # Check exits (PONG) - SELLERS + BALANCED
            if self.bot_role in ['SELLER', 'BALANCED']:
                self.check_exits()
                
                # AUTO-HARVEST: Take profits from any position above floor
                floor_harvests = self.auto_harvest_floor_winners()
                if floor_harvests > 0:
                    deadlock_cycles = 0  # Reset deadlock if we harvested
            
            # Scan and enter (PING) - BUYERS + BALANCED
            if self.bot_role in ['BUYER', 'BALANCED']:
                logger.info(f"\n🔍 POSITION CHECK: {len(self.positions)}/{CONFIG['MAX_POSITIONS']} positions")
                if len(self.positions) < CONFIG['MAX_POSITIONS']:
                    logger.info(f"✅ CAN ENTER NEW POSITION - Activating Ecosystem...")
                    
                    # Get commando targets first
                    if time.time() - self.last_commando_scan > 30:
                        logger.info("🦁 DEPLOYING COMMANDOS FOR PRIDE SCAN...")
                        self.commando_cache = self.commandos.get_commando_targets(self.memory, self.allowed_quotes)
                        self.last_commando_scan = time.time()
                    
                    # 🦆 DYNAMIC ECOSYSTEM: Let commandos compete for slots!
                    current_symbols = set(self.positions.keys())
                    eco_pick = self.commandos.get_next_entry_recommendation(
                        self.commando_cache,
                        current_symbols,
                        len(self.positions),
                        CONFIG['MAX_POSITIONS'],
                        self.memory
                    )
                    
                    if eco_pick:
                        logger.info(f"🦆 ECOSYSTEM SELECTED: {eco_pick['commando'].upper()} → {eco_pick['symbol']}")
                        
                        # Convert ecosystem pick to opportunity format
                        opp = self.build_opportunity_from_eco_pick(eco_pick)
                        
                        if opp:
                            quote_balance = self.get_quote_balance()
                            logger.info(
                                f"💰 {self.primary_quote} balance={quote_balance:.4f} | MIN={CONFIG['MIN_TRADE_NOTIONAL']:.2f}"
                            )
                            if quote_balance >= CONFIG['MIN_TRADE_NOTIONAL']:
                                logger.info(f"🦆💎 {eco_pick['commando'].upper()} ENTERING {opp['symbol']}!")
                                entered = self.enter_position(opp, quote_balance, commando=eco_pick['commando'])
                                if entered:
                                    self.commandos.record_entry(opp['symbol'], eco_pick['commando'])
                                    
                                    # 🌉 Publish opportunity to bridge for Unified system awareness
                                    if BRIDGE_AVAILABLE and self.bridge:
                                        # Convert to list of opportunities
                                        self.publish_opportunities_to_bridge()
                                else:
                                    logger.warning(f"⚠️ Entry failed for {opp['symbol']}")
                        else:
                            quote_balance = self.get_quote_balance()
                            if self.harvest_winner_for_liquidity(CONFIG['MIN_TRADE_NOTIONAL'] * 2):
                                logger.info("💎 Harvested liquidity from winners. Will rescan next cycle.")
                                deadlock_cycles = 0  # Reset deadlock counter
                            else:
                                logger.warning(
                                    f"❌ NOT ENOUGH {self.primary_quote}: {quote_balance:.4f} < {CONFIG['MIN_TRADE_NOTIONAL']:.2f}"
                                )
                            deadlock_cycles += 1
                            
                            # Emergency: Force-exit flattest position if stuck for 10+ cycles
                            if deadlock_cycles >= 10 and self.positions:
                                logger.warning("🚨 DEADLOCK DETECTED: Force-exiting flattest position for liquidity!")
                                # Find position closest to entry price WITH ACTUAL WALLET BALANCE
                                flattest = None
                                min_move = float('inf')
                                for sym, pos in self.positions.items():
                                    ticker = self.ticker_cache.get(sym)
                                    if ticker:
                                        # Check ACTUAL wallet balance first
                                        base_asset = self.get_base_asset(sym)
                                        actual_qty = self.client.get_free_balance(base_asset) if base_asset else 0.0
                                        if actual_qty <= 0:
                                            # Position is ghost - remove it from tracking
                                            logger.warning(f"👻 Ghost position detected: {sym} (no wallet balance). Removing from tracking.")
                                            continue
                                        price = float(ticker['lastPrice'])
                                        move = abs((price - pos.entry_price) / pos.entry_price)
                                        if move < min_move:
                                            min_move = move
                                            flattest = sym
                                
                                # Clean up any ghost positions found
                                ghost_positions = [sym for sym, pos in self.positions.items() 
                                                   if self.client.get_free_balance(self.get_base_asset(sym) or '') <= 0]
                                for ghost in ghost_positions:
                                    logger.info(f"🧹 Removing ghost position: {ghost}")
                                    self.commandos.record_exit(ghost, 0.0)  # 🦆 Notify commandos
                                    del self.positions[ghost]
                                    deadlock_cycles = 0
                                
                                if flattest:
                                    if not self.business_green_light:
                                        threshold = CONFIG.get('BUSINESS_GREEN_THRESHOLD', 0.0)
                                        logger.warning(
                                            f"🚫 BUSINESS HOLD: Realized Net ${self.last_realized_net:+.2f} <= ${threshold:+.2f}. "
                                            "Cannot run emergency exit despite deadlock."
                                        )
                                    else:
                                        pos = self.positions[flattest]
                                        ticker = self.ticker_cache.get(flattest)
                                        price = float(ticker['lastPrice'])
                                        # Use ACTUAL wallet balance, not tracked quantity
                                        base_asset = self.get_base_asset(flattest)
                                        actual_qty = self.client.get_free_balance(base_asset) if base_asset else 0.0
                                        sell_qty = min(pos.quantity, actual_qty)
                                        qty_str = self.lot_mgr.format_qty(flattest, sell_qty)
                                        try:
                                            logger.info(f"🔓 Emergency exit: {flattest} @ ${price:.4f} (qty={qty_str}) to break deadlock")
                                            result = self.client.place_market_order(flattest, 'SELL', quantity=float(qty_str))
                                            fee_pct = CONFIG.get('TAKER_FEE_PCT', 0.0)
                                            actual_sell_fee = self.client.compute_order_fees_in_quote(result, self.primary_quote)
                                            sell_fee = actual_sell_fee if actual_sell_fee and actual_sell_fee > 0 else (price * sell_qty * fee_pct)
                                            entry_fee_actual = pos.fees_quote
                                            realized = sell_qty * (price - pos.entry_price)
                                            realized_net = realized - sell_fee - entry_fee_actual
                                            self.total_gross_pnl += realized
                                            self.total_fees += sell_fee
                                            compound, harvest = self.hive.process_profit(realized_net)
                                            self.memory.record(flattest, realized_net)
                                            if realized_net >= 0:
                                                self.wins += 1
                                            self.commandos.record_exit(flattest, realized_net)  # 🦆 Notify commandos
                                            del self.positions[flattest]
                                            logger.info(f"✅ Emergency exit complete: Net ${realized_net:+.2f}")
                                            deadlock_cycles = 0  # Reset after breaking deadlock
                                        except Exception as exc:
                                            logger.error(f"❌ Emergency exit failed: {exc}")
                                            # If failed, remove from tracking anyway to prevent infinite loop
                                            self.commandos.record_exit(flattest, 0.0)  # 🦆 Notify commandos
                                            del self.positions[flattest]
                                            deadlock_cycles = 0
                    else:
                        logger.info(f"🦆 NO ECOSYSTEM PICKS (commandos have no targets)")
            
            time.sleep(0.5)  # 🦆💎 BIG PLUMS: 500ms RAPID FIRE!
        
        # Final summary
        logger.info(f"""
╔════════════════════════════════════════════════════════════════╗
║ 🏁 SESSION COMPLETE
║────────────────────────────────────────────────────────────────
║ Trades:     {self.trades}
║ Wins:       {self.wins}
║ Win Rate:   {self.wins/max(1,self.trades)*100:.1f}%
║ Profit:     ${self.hive.total_profit:+.2f}
║ Compounded: ${self.hive.compounded:.2f}
║ Harvested:  ${self.hive.harvested:.2f}
╚════════════════════════════════════════════════════════════════╝
""")

if __name__ == "__main__":
    trader = AureonUltimate()
    trader.run(duration_sec=300)  # 5 min test
