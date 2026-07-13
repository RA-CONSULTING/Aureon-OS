#!/usr/bin/env python3
"""
🌊 AUREON QGITA ENGINE - FULL IMPLEMENTATION FROM TSX 🌊

Based on core/aurisSymbolicTaxonomy.ts, core/aqtsOrchestrator.ts, 
core/riskManagement.ts, core/decisionFusion.ts, core/qgitaEngine.ts

Key Features:
  - 9 Auris Nodes with proper operators
  - QGITA Lighthouse Events (Fibonacci time lattice)
  - Decision Fusion Layer (ensemble signals)
  - Risk Management with Kelly Criterion
  - Proper LOT_SIZE and precision handling
  - Prism Status: Gold/Blue/Red

"The Dolphin sings the wave. The Hummingbird locks the pulse.
 The Tiger cuts the noise. The Owl remembers. The Panda loves."

Author: Gary Leckey / Aureon System
Date: November 28, 2025
"""
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os, sys, json, time, logging, argparse, random, math
from datetime import datetime
from typing import List, Dict, Any, Optional
from aureon.exchanges.binance_client import BinanceClient, get_binance_client
from decimal import Decimal, ROUND_DOWN

# Safe print for Windows multi-module imports
def _safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except (ValueError, OSError, IOError):
        pass

# 🪙 PENNY PROFIT ENGINE
try:
    from aureon.trading.penny_profit_engine import check_penny_exit, get_penny_engine
    PENNY_PROFIT_AVAILABLE = True
    _penny_engine = get_penny_engine()
    _safe_print("🪙 Penny Profit Engine loaded for QGITA")
except ImportError:
    PENNY_PROFIT_AVAILABLE = False
    _penny_engine = None
    _safe_print("⚠️ Penny Profit Engine not available")

# 🧠 WISDOM COGNITION ENGINE - 11 Civilizations
try:
    from aureon.utils.aureon_miner_brain import WisdomCognitionEngine
    WISDOM_AVAILABLE = True
    _wisdom_engine = WisdomCognitionEngine()
    _safe_print("🧠 Wisdom Engine loaded - 11 civilizations ready")
except ImportError:
    WISDOM_AVAILABLE = False
    _wisdom_engine = None
    _safe_print("⚠️ Wisdom Engine not available")

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('qgita.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION - From TSX core/config.ts
# ═══════════════════════════════════════════════════════════════════════════

CONFIG = {
    # Decision Fusion Thresholds (from decisionFusion.ts)
    'BUY_THRESHOLD': 0.15,
    'SELL_THRESHOLD': -0.15,
    'MIN_CONFIDENCE': 0.35,
    
    # Risk Management (from riskManagement.ts)
    'MAX_PORTFOLIO_RISK': 0.03,
    'MAX_LEVERAGE': 5,
    'CIRCUIT_BREAKER': 0.10,
    'RISK_PER_TRADE_CAP': 0.04,
    'KELLY_MULTIPLIER': 1.0,
    
    # Prism Status Thresholds (from aqtsOrchestrator.ts)
    'GOLD_CONFIDENCE': 0.8,
    'GOLD_SPREAD': 0.0015,
    'RED_CONFIDENCE': 0.45,
    'RED_SPREAD': 0.003,
    
    # Trade Parameters
    'MIN_USD_VALUE': 6.0,
    'MAX_POSITIONS': 10,
    'STOP_LOSS_MULT': 1.2,
    'TAKE_PROFIT_MULT': 2.25,
    
    # Auris Frequencies (Hz)
    'FREQ_OWL': 432.0,
    'FREQ_DEER': 396.0,
    'FREQ_DOLPHIN': 528.0,   # Love
    'FREQ_TIGER': 741.0,
    'FREQ_HUMMINGBIRD': 963.0,
    'FREQ_CARGOSHIP': 174.0,
    'FREQ_CLOWNFISH': 639.0,
    'FREQ_FALCON': 852.0,
    'FREQ_PANDA': 412.3,     # Hope
}

# ═══════════════════════════════════════════════════════════════════════════
# AURIS SYMBOLIC TAXONOMY - 9 NODES (from aurisSymbolicTaxonomy.ts)
# ═══════════════════════════════════════════════════════════════════════════

class AurisState:
    """State object passed through all 9 Auris operators"""
    def __init__(self, market_data: Dict):
        self.time = market_data.get('time', 0)
        self.price = market_data.get('price', 0)
        self.high = market_data.get('high', 0)
        self.low = market_data.get('low', 0)
        self.volume = market_data.get('volume', 0)
        self.change_pct = market_data.get('change_pct', 0)
        
        # Derived values
        self.volatility = (self.high - self.low) / self.price if self.price > 0 else 0
        self.momentum = self.change_pct / 100
        self.volume_norm = min(self.volume / 1e9, 1.0)
        
        # Initial coherence
        self.coherenceIndex = 0.5
        self.unityIndex = 0.5
        self.dataIntegrity = 0.8
        self.prismStatus = 'Blue'
        
        # Node states
        self.memory = []
        self.microShiftMagnitude = 0
        self.deerAlert = 'CALM'
        self.emotionalCarrier = 0
        self.dolphinSong = 'LISTENING'
        self.tigerCut = False
        self.hummingbirdLocked = False
        self.choeranceDrift = 0
        self.pingPong = 0
        self.momentumBuffer = []
        self.smoothedMomentum = 0
        self.synapseStrength = 0
        self.clownfishBond = 'SEEKING'
        self.systemSync = False
        self.falconSurge = False
        self.surgeWindow = False
        self.surgeMagnitude = 0
        self.lastVelocity = 0
        self.pandaHeart = 0
        self.emotionalState = 'SEEKING'
        self.centerHeld = False
        self.inerchaVector = 0
        self.crystalCoherence = 0.5

def owl_operator(state: AurisState) -> AurisState:
    """Ψ∞ - Long-Term Memory - Holds echo of past cycles"""
    state.memory.append({
        'time': state.time,
        'coherence': state.coherenceIndex,
        'prism': state.prismStatus,
    })
    if len(state.memory) > 1000:
        state.memory.pop(0)
    return state

def deer_operator(state: AurisState) -> AurisState:
    """ℵ - Subtle Sensing - Detects micro-shifts"""
    state.microShiftMagnitude = abs(state.choeranceDrift) * state.dataIntegrity
    state.deerAlert = 'SENSITIVE' if state.microShiftMagnitude > 0.15 else 'CALM'
    return state

def dolphin_operator(state: AurisState) -> AurisState:
    """Φ - Emotional Carrier - 528Hz Love frequency"""
    state.emotionalCarrier = math.sin(state.time * 0.1) * state.coherenceIndex
    state.dolphinSong = 'SINGING' if state.emotionalCarrier > 0.7 else 'LISTENING'
    return state

def tiger_operator(state: AurisState) -> AurisState:
    """ℱ - Phase Disruptor - Cuts noise, enforces clarity"""
    if state.unityIndex < 0.5:
        state.tigerCut = True
        state.prismStatus = 'Red'
    else:
        state.tigerCut = False
    # Remove noise
    state.inerchaVector = state.inerchaVector if abs(state.inerchaVector) > 0.3 else 0
    return state

def hummingbird_operator(state: AurisState) -> AurisState:
    """L - Micro-Stabilizer - Locks high-frequency coherence"""
    coherence_lock = state.crystalCoherence > 0.8 and state.unityIndex > 0.9
    state.hummingbirdLocked = coherence_lock
    if coherence_lock:
        state.choeranceDrift *= 0.5
        state.pingPong *= 0.8
    return state

def cargoship_operator(state: AurisState) -> AurisState:
    """Ω - Time-Latency Buffer - Carries momentum"""
    state.momentumBuffer.append(state.inerchaVector)
    if len(state.momentumBuffer) > 10:
        state.momentumBuffer.pop(0)
    state.smoothedMomentum = sum(state.momentumBuffer) / len(state.momentumBuffer) if state.momentumBuffer else 0
    return state

def clownfish_operator(state: AurisState) -> AurisState:
    """ρ - Symbiosis Link - Binds subsystems"""
    state.synapseStrength = state.unityIndex * state.dataIntegrity
    state.clownfishBond = 'BONDED' if state.synapseStrength > 0.8 else 'SEEKING'
    state.systemSync = state.synapseStrength > 0.7
    return state

def falcon_operator(state: AurisState) -> AurisState:
    """C - Velocity Trigger - Initiates Surge Window"""
    velocity = abs(state.inerchaVector)
    acceleration = velocity - state.lastVelocity
    state.falconSurge = acceleration > 0.2 and velocity > 0.5
    state.lastVelocity = velocity
    state.surgeWindow = state.falconSurge
    state.surgeMagnitude = acceleration if state.falconSurge else 0
    return state

def panda_operator(state: AurisState) -> AurisState:
    """Ψ'∞ - Empathy Core - Holds the heart of the loop"""
    state.pandaHeart = state.coherenceIndex * state.emotionalCarrier
    if state.pandaHeart > 0.9:
        state.emotionalState = 'UNITY'
    elif state.pandaHeart > 0.7:
        state.emotionalState = 'HOPE'
    elif state.pandaHeart > 0.5:
        state.emotionalState = 'CALM'
    else:
        state.emotionalState = 'SEEKING'
    state.centerHeld = True
    return state

def execute_auris_loop(state: AurisState) -> AurisState:
    """Execute the 9-node loop: Ψ∞ → C → ℵ → Φ → ℱ → L → Ω → ρ → C → Ψ'∞"""
    operators = [
        owl_operator,
        deer_operator,
        dolphin_operator,
        tiger_operator,
        hummingbird_operator,
        cargoship_operator,
        clownfish_operator,
        falcon_operator,
        panda_operator,
    ]
    for op in operators:
        state = op(state)
    return state

# ═══════════════════════════════════════════════════════════════════════════
# QGITA ENGINE - Fibonacci Time Lattice (from qgitaEngine.ts)
# ═══════════════════════════════════════════════════════════════════════════

class QGITAEngine:
    """Quantized Geometric Intelligence Trading Algorithm"""
    def __init__(self):
        self.history: List[Dict] = []
        self.fib_sequence = [5, 8, 13, 21, 34, 55]
        self.min_confidence = 0.35
        self.neutral_confidence = 0.45
        self.history_limit = 300
    
    def register(self, snapshot: Dict):
        self.history.append(snapshot)
        if len(self.history) > self.history_limit:
            self.history.pop(0)
    
    def compute_curvature(self, values: List[float]) -> float:
        if len(values) < 3:
            return 0
        curvature = 0
        for i in range(1, len(values) - 1):
            prev, curr, next_val = values[i-1], values[i], values[i+1]
            curvature += abs(next_val - 2 * curr + prev)
        return curvature / (len(values) - 2)
    
    def evaluate(self) -> Optional[Dict]:
        """Evaluate for Lighthouse Event"""
        max_fib = max(self.fib_sequence)
        if len(self.history) < max_fib:
            return None
        
        closes = [h['price'] for h in self.history]
        
        # Fibonacci windows
        fib_windows = []
        for length in self.fib_sequence:
            slice_data = closes[-length:]
            start, end = slice_data[0], slice_data[-1]
            max_val = max(end, start) or 1
            ratio_alignment = min(abs(end - start) / max_val, 0.12) / 0.12
            curvature = self.compute_curvature(slice_data)
            fib_windows.append({
                'length': length,
                'ratio_alignment': ratio_alignment,
                'curvature': curvature
            })
        
        # Time Lattice Score
        time_lattice = sum(w['ratio_alignment'] for w in fib_windows) / len(fib_windows)
        
        # Coherence from recent history
        recent = self.history[-21:] if len(self.history) >= 21 else self.history
        avg_momentum = sum(h.get('momentum', 0) for h in recent) / len(recent)
        
        # Volume curvature
        volumes = [h.get('volume', 0) for h in recent]
        vol_curvature = self.compute_curvature(volumes)
        volatility_score = max(0, 1 - min(vol_curvature / 1.5e12, 1))
        
        coherence_score = (time_lattice + volatility_score) / 2
        
        # Direction
        if avg_momentum > 0.02:
            direction = 'long'
        elif avg_momentum < -0.02:
            direction = 'short'
        else:
            direction = 'neutral'
        
        confidence = min(1.0, coherence_score * 1.2)
        
        if confidence < self.min_confidence:
            return None
        
        return {
            'direction': direction,
            'confidence': confidence,
            'time_lattice': time_lattice,
            'coherence': coherence_score,
        }

# ═══════════════════════════════════════════════════════════════════════════
# DECISION FUSION LAYER (from decisionFusion.ts)
# ═══════════════════════════════════════════════════════════════════════════

class DecisionFusion:
    """Fuses ensemble model signals with QGITA lighthouse"""
    def __init__(self):
        self.weights = {
            'ensemble': 0.6,
            'sentiment': 0.2,
            'qgita': 0.2,
        }
    
    def generate_model_signal(self, snapshot: Dict) -> Dict:
        """Simulate ensemble model signals (lstm, rf, xgb, transformer)"""
        trend = snapshot.get('momentum', 0)
        volatility = snapshot.get('volatility', 0.01)
        normalized_trend = math.tanh(trend / volatility) if volatility > 0 else 0
        
        # Simulate 4 models
        models = ['lstm', 'randomForest', 'xgboost', 'transformer']
        signals = []
        for model in models:
            bias = {'lstm': 0.2, 'randomForest': -0.1, 'xgboost': 0.1, 'transformer': 0}[model]
            score = normalized_trend + bias + (random.random() - 0.5) * 0.1
            confidence = max(0.2, min(0.95, 0.4 + random.random() * 0.5 - abs(score) * 0.1))
            signals.append({'model': model, 'score': score, 'confidence': confidence})
        return signals
    
    def decide(self, snapshot: Dict, lighthouse_event: Optional[Dict]) -> Dict:
        model_signals = self.generate_model_signal(snapshot)
        
        # Aggregate ensemble
        agg_score = sum(s['score'] * s['confidence'] for s in model_signals)
        total_conf = sum(s['confidence'] for s in model_signals)
        normalized = agg_score / total_conf if total_conf > 0 else 0
        
        # QGITA boost
        qgita_boost = 0
        if lighthouse_event:
            direction_mult = 1 if lighthouse_event['direction'] == 'long' else -1
            qgita_boost = lighthouse_event['confidence'] * direction_mult
        
        # Weighted final score
        w = self.weights
        w_total = w['ensemble'] + w['qgita']
        final_score = (normalized * w['ensemble'] + qgita_boost * w['qgita']) / w_total
        
        # Action
        if final_score > CONFIG['BUY_THRESHOLD']:
            action = 'buy'
        elif final_score < CONFIG['SELL_THRESHOLD']:
            action = 'sell'
        else:
            action = 'hold'
        
        return {
            'action': action,
            'score': final_score,
            'confidence': min(1.0, abs(final_score) + 0.3),
        }

# ═══════════════════════════════════════════════════════════════════════════
# RISK MANAGER (from riskManagement.ts)
# ═══════════════════════════════════════════════════════════════════════════

def kelly_criterion(win_rate: float, reward_risk: float) -> float:
    """Kelly: k = p - (1-p)/R"""
    if reward_risk <= 0:
        return 0
    return max(0, min(1, win_rate - (1 - win_rate) / reward_risk))

class RiskManager:
    def __init__(self, initial_equity: float = 100):
        self.equity = initial_equity
        self.peak_equity = initial_equity
        self.max_drawdown = 0
        self.positions = []
    
    def evaluate(self, decision: Dict, snapshot: Dict, available_balance: float) -> Optional[Dict]:
        if decision['action'] == 'hold':
            return None
        
        direction = 'long' if decision['action'] == 'buy' else 'short'
        confidence = decision['confidence']
        
        # Volatility-based sizing
        volatility = snapshot.get('volatility', 0.02)
        normalized_vol = max(0.001, volatility)
        
        # Kelly sizing
        win_rate = 0.55 * confidence + 0.45 * random.random()
        reward_risk = 1.5 + confidence
        kelly_frac = kelly_criterion(win_rate, reward_risk) * CONFIG['KELLY_MULTIPLIER']
        
        # Risk budget
        base_risk = min(CONFIG['MAX_PORTFOLIO_RISK'], kelly_frac)
        risk_fraction = min(base_risk, CONFIG['RISK_PER_TRADE_CAP'])
        risk_budget = available_balance * risk_fraction
        
        if risk_budget < CONFIG['MIN_USD_VALUE']:
            return None
        
        # Stop loss / Take profit
        price = snapshot['price']
        sl_distance = price * normalized_vol * CONFIG['STOP_LOSS_MULT']
        tp_distance = sl_distance * CONFIG['TAKE_PROFIT_MULT']
        
        if direction == 'long':
            stop_loss = price - sl_distance
            take_profit = price + tp_distance
        else:
            stop_loss = price + sl_distance
            take_profit = price - tp_distance
        
        return {
            'direction': direction,
            'notional': min(risk_budget * 3, available_balance * 0.95),
            'stop_loss': stop_loss,
            'take_profit': take_profit,
        }

# ═══════════════════════════════════════════════════════════════════════════
# LOT SIZE HANDLER - CRITICAL FOR BINANCE
# ═══════════════════════════════════════════════════════════════════════════

class LotSizeManager:
    """Handles Binance LOT_SIZE and precision requirements"""
    def __init__(self, client: BinanceClient):
        self.client = client
        self.symbol_info = {}
        self.last_update = 0
    
    def update_symbol_info(self):
        """Fetch exchange info and parse LOT_SIZE filters"""
        if time.time() - self.last_update < 300:  # Cache for 5 minutes
            return
        
        try:
            info = self.client.exchange_info()
            for s in info.get('symbols', []):
                symbol = s['symbol']
                self.symbol_info[symbol] = {
                    'status': s.get('status'),
                    'base': s.get('baseAsset'),
                    'quote': s.get('quoteAsset'),
                    'filters': {},
                }
                for f in s.get('filters', []):
                    self.symbol_info[symbol]['filters'][f['filterType']] = f
            self.last_update = time.time()
            logger.info(f"📊 Loaded {len(self.symbol_info)} symbol filters")
        except Exception as e:
            logger.error(f"❌ Failed to load symbol info: {e}")
    
    def get_lot_size(self, symbol: str) -> Dict:
        """Get stepSize, minQty, maxQty for a symbol"""
        self.update_symbol_info()
        info = self.symbol_info.get(symbol, {})
        lot_size = info.get('filters', {}).get('LOT_SIZE', {})
        return {
            'stepSize': float(lot_size.get('stepSize', '0.00000001')),
            'minQty': float(lot_size.get('minQty', '0.00000001')),
            'maxQty': float(lot_size.get('maxQty', '9999999999')),
        }
    
    def get_notional(self, symbol: str) -> Dict:
        """Get MIN_NOTIONAL filter"""
        self.update_symbol_info()
        info = self.symbol_info.get(symbol, {})
        notional = info.get('filters', {}).get('NOTIONAL', info.get('filters', {}).get('MIN_NOTIONAL', {}))
        return {
            'minNotional': float(notional.get('minNotional', '5.0')),
        }
    
    def format_quantity(self, symbol: str, quantity: float) -> str:
        """Format quantity to match LOT_SIZE stepSize"""
        lot = self.get_lot_size(symbol)
        step_size = lot['stepSize']
        min_qty = lot['minQty']
        max_qty = lot['maxQty']
        
        # Calculate precision from step size
        if step_size >= 1:
            precision = 0
        else:
            precision = len(str(step_size).rstrip('0').split('.')[-1])
        
        # Round down to step size
        qty_decimal = Decimal(str(quantity))
        step_decimal = Decimal(str(step_size))
        formatted = (qty_decimal // step_decimal) * step_decimal
        
        # Clamp to min/max
        formatted = max(Decimal(str(min_qty)), min(formatted, Decimal(str(max_qty))))
        
        # Format to string without scientific notation
        if precision == 0:
            return str(int(formatted))
        else:
            return f"{formatted:.{precision}f}"
    
    def is_tradeable(self, symbol: str) -> bool:
        """Check if symbol is allowed for trading"""
        self.update_symbol_info()
        info = self.symbol_info.get(symbol, {})
        return info.get('status') == 'TRADING'

# ═══════════════════════════════════════════════════════════════════════════
# MAIN TRADER
# ═══════════════════════════════════════════════════════════════════════════

class AureonQGITATrader:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.client = get_binance_client()
        self.lot_manager = LotSizeManager(self.client)
        self.qgita = QGITAEngine()
        self.decision_fusion = DecisionFusion()
        self.risk_manager = RiskManager()
        self.positions = {}
        self.total_profit = 0.0
        self.ticker_cache = {}
        self.last_ticker_update = 0
        self.cycle = 0
        
        # Load existing positions
        self.load_existing_bags()
    
    def load_existing_bags(self):
        """Load existing balances as positions"""
        logger.info("🔍 Scanning for existing bags...")
        try:
            account = self.client.account()
            for b in account['balances']:
                asset = b['asset']
                free = float(b['free'])
                if free > 0 and asset not in ['USDT', 'BUSD', 'USDC', 'LDUSDC']:
                    symbol = f"{asset}USDT"
                    try:
                        ticker = self.client.session.get(
                            f"{self.client.base}/api/v3/ticker/price",
                            params={'symbol': symbol}
                        ).json()
                        if 'price' not in ticker:
                            continue
                        price = float(ticker['price'])
                        value = free * price
                        
                        if value >= CONFIG['MIN_USD_VALUE']:
                            # Check if tradeable
                            if not self.lot_manager.is_tradeable(symbol):
                                logger.warning(f"⚠️ {symbol} not tradeable, skipping")
                                continue
                            
                            self.positions[symbol] = {
                                'entry_price': price,
                                'quantity': free,
                                'entry_time': time.time(),
                                'is_existing': True,
                            }
                            logger.info(f"✅ Loaded bag: {symbol} ({free:.6f}) ~ ${value:.2f}")
                    except Exception as e:
                        continue
            logger.info(f"📊 Loaded {len(self.positions)} existing positions")
        except Exception as e:
            logger.error(f"❌ Failed to load bags: {e}")
    
    def update_tickers(self):
        """Bulk update ticker cache"""
        if time.time() - self.last_ticker_update < 2:
            return
        try:
            tickers = self.client.session.get(f"{self.client.base}/api/v3/ticker/24hr").json()
            self.ticker_cache = {t['symbol']: t for t in tickers}
            self.last_ticker_update = time.time()
        except Exception as e:
            logger.error(f"❌ Ticker update failed: {e}")
    
    def get_snapshot(self, symbol: str) -> Optional[Dict]:
        """Get market snapshot for symbol"""
        ticker = self.ticker_cache.get(symbol)
        if not ticker:
            return None
        
        try:
            return {
                'time': self.cycle,
                'price': float(ticker['lastPrice']),
                'high': float(ticker['highPrice']),
                'low': float(ticker['lowPrice']),
                'volume': float(ticker['quoteVolume']),
                'change_pct': float(ticker['priceChangePercent']),
                'momentum': float(ticker['priceChangePercent']) / 100,
                'volatility': (float(ticker['highPrice']) - float(ticker['lowPrice'])) / float(ticker['lastPrice'])
            }
        except:
            return None
    
    def derive_prism_status(self, confidence: float, spread: float = 0.001) -> str:
        """Derive Prism Status from confidence and spread"""
        if confidence > CONFIG['GOLD_CONFIDENCE'] and spread < CONFIG['GOLD_SPREAD']:
            return 'Gold'
        if confidence < CONFIG['RED_CONFIDENCE'] or spread > CONFIG['RED_SPREAD']:
            return 'Red'
        return 'Blue'
    
    def check_exits(self):
        """Check and execute exits for open positions"""
        for symbol in list(self.positions.keys()):
            pos = self.positions[symbol]
            snap = self.get_snapshot(symbol)
            if not snap:
                continue
            
            price = snap['price']
            entry = pos['entry_price']
            pnl_pct = (price - entry) / entry if entry > 0 else 0
            
            # Track cycles for min hold time
            pos['cycles'] = pos.get('cycles', 0) + 1
            current_value = pos.get('qty', 0) * price
            entry_value = pos.get('entry_value', pos.get('qty', 0) * entry)
            gross_pnl = current_value - entry_value
            
            # Create Auris state and run loop
            state = AurisState(snap)
            state = execute_auris_loop(state)
            
            # QGITA evaluation
            self.qgita.register(snap)
            lighthouse = self.qgita.evaluate()
            
            prism = self.derive_prism_status(
                lighthouse['confidence'] if lighthouse else 0.3,
                snap['volatility'] * 0.1
            )
            
            should_exit = False
            exit_reason = ""
            
            # 🪙 PENNY PROFIT EXIT LOGIC (priority)
            if PENNY_PROFIT_AVAILABLE and _penny_engine is not None and entry_value > 0:
                action, _ = check_penny_exit('binance', entry_value, current_value)
                threshold = _penny_engine.get_threshold('binance', entry_value)
                
                if action == 'TAKE_PROFIT':
                    should_exit = True
                    exit_reason = f"🪙 PENNY TP (${gross_pnl:.4f} >= ${threshold.win_gte:.4f})"
                elif action == 'STOP_LOSS' and pos['cycles'] >= 5:
                    should_exit = True
                    exit_reason = f"🪙 PENNY SL (${gross_pnl:.4f} <= ${threshold.stop_lte:.4f})"
                elif prism == 'Red' and pos['cycles'] >= 5:
                    should_exit = True
                    exit_reason = f"🔴 RED PRISM (low confidence)"
                elif state.tigerCut and pos['cycles'] >= 5:
                    should_exit = True
                    exit_reason = f"🐯 TIGER CUT (phase disruption)"
            else:
                # Fallback exit conditions
                if prism == 'Red' and pos['cycles'] >= 5:
                    should_exit = True
                    exit_reason = f"🔴 RED PRISM (low confidence)"
                elif pnl_pct >= CONFIG['TAKE_PROFIT_MULT'] * 0.01:
                    should_exit = True
                    exit_reason = f"💰 TAKE PROFIT (+{pnl_pct*100:.2f}%)"
                elif pnl_pct <= -CONFIG['STOP_LOSS_MULT'] * 0.01 and pos['cycles'] >= 5:
                    should_exit = True
                    exit_reason = f"🛑 STOP LOSS ({pnl_pct*100:.2f}%)"
                elif state.tigerCut and pos['cycles'] >= 5:
                    should_exit = True
                    exit_reason = f"🐯 TIGER CUT (phase disruption)"
            
            # Random status log
            if random.random() < 0.02:
                logger.info(f"📊 {symbol}: Prism={prism} | PnL={pnl_pct*100:.2f}% | State={state.emotionalState}")
            
            if should_exit:
                logger.info(f"⚡ {symbol}: {exit_reason}")
                self.close_position(symbol, pos, price, pnl_pct)
    
    def close_position(self, symbol: str, pos: Dict, price: float, pnl_pct: float):
        """Close a position with proper LOT_SIZE handling"""
        if self.dry_run:
            logger.info(f"📝 DRY-RUN SELL: {symbol}")
            del self.positions[symbol]
            return
        
        try:
            # Extract base asset by stripping known quote suffix
            # MUST use endswith() — .replace() corrupts symbols like ETHFIUSDC → FI
            base = symbol
            for _q in ('USDT', 'USDC', 'BUSD', 'FDUSD', 'TUSD', 'USD', 'BTC', 'BNB', 'ETH'):
                if symbol.endswith(_q) and len(symbol) > len(_q):
                    base = symbol[:-len(_q)]
                    break
            
            # Get actual balance
            balance = self.client.get_free_balance(base)
            if balance <= 0:
                logger.warning(f"⚠️ No {base} balance to sell")
                del self.positions[symbol]
                return
            
            # Check value
            value_usd = balance * price
            if value_usd < CONFIG['MIN_USD_VALUE']:
                logger.warning(f"⚠️ {symbol} value ${value_usd:.2f} below minimum")
                del self.positions[symbol]
                return
            
            # Check if tradeable
            if not self.lot_manager.is_tradeable(symbol):
                logger.warning(f"⚠️ {symbol} not tradeable on this account")
                del self.positions[symbol]
                return
            
            # Format quantity
            qty_str = self.lot_manager.format_quantity(symbol, balance)
            
            logger.info(f"🚀 SELLING {symbol}: {qty_str} (raw: {balance})")
            
            # Execute sell
            result = self.client.place_market_order(symbol, 'SELL', quantity=float(qty_str))
            logger.info(f"✅ Sold {symbol}: {result}")
            
            profit = pos['quantity'] * price * pnl_pct
            self.total_profit += profit
            
        except Exception as e:
            logger.error(f"❌ Sell failed {symbol}: {e}")
        
        if symbol in self.positions:
            del self.positions[symbol]
    
    def scan_for_entries(self):
        """Scan for new entry opportunities"""
        if len(self.positions) >= CONFIG['MAX_POSITIONS']:
            return
        
        # Get tradeable pairs with USDT quote
        try:
            account = self.client.account()
            usdt_balance = 0
            for b in account['balances']:
                if b['asset'] == 'USDT':
                    usdt_balance = float(b['free'])
                    break
            
            if usdt_balance < CONFIG['MIN_USD_VALUE']:
                return
            
            # Get all USDT pairs
            self.lot_manager.update_symbol_info()
            usdt_pairs = [
                s for s in self.lot_manager.symbol_info.keys()
                if s.endswith('USDT') and self.lot_manager.symbol_info[s].get('status') == 'TRADING'
            ]
            
            # Shuffle for randomness
            random.shuffle(usdt_pairs)
            
            for symbol in usdt_pairs[:50]:  # Scan 50 at a time
                if symbol in self.positions:
                    continue
                if len(self.positions) >= CONFIG['MAX_POSITIONS']:
                    break
                
                snap = self.get_snapshot(symbol)
                if not snap or snap['price'] <= 0:
                    continue
                
                # Run QGITA
                self.qgita.register(snap)
                lighthouse = self.qgita.evaluate()
                
                # Decision fusion
                decision = self.decision_fusion.decide(snap, lighthouse)
                
                if decision['action'] != 'buy':
                    continue
                
                # Risk evaluation
                order = self.risk_manager.evaluate(decision, snap, usdt_balance)
                if not order:
                    continue
                
                prism = self.derive_prism_status(decision['confidence'])
                
                # Only enter on Blue or Gold
                if prism == 'Red':
                    continue
                
                # Format and execute
                size_usdt = min(order['notional'], usdt_balance * 0.9)
                if size_usdt < CONFIG['MIN_USD_VALUE']:
                    continue
                
                size_usdt = round(size_usdt, 4)
                
                logger.info(f"🎯 {symbol}: BUY ${size_usdt:.2f} | Prism={prism} | Conf={decision['confidence']:.2f}")
                
                if self.dry_run:
                    logger.info(f"📝 DRY-RUN BUY: {symbol}")
                    self.positions[symbol] = {
                        'entry_price': snap['price'],
                        'quantity': size_usdt / snap['price'],
                        'entry_time': time.time(),
                    }
                else:
                    try:
                        result = self.client.place_market_order(symbol, 'BUY', quote_qty=size_usdt)
                        self.positions[symbol] = {
                            'entry_price': snap['price'],
                            'quantity': size_usdt / snap['price'],
                            'entry_time': time.time(),
                        }
                        logger.info(f"✅ Bought {symbol}: {result}")
                        usdt_balance -= size_usdt
                    except Exception as e:
                        logger.error(f"❌ Buy failed {symbol}: {e}")
                
                time.sleep(0.1)  # Rate limit
                
        except Exception as e:
            logger.error(f"❌ Entry scan failed: {e}")
    
    def run(self, duration_sec: int = 3600):
        """Main trading loop"""
        logger.info("""
╔════════════════════════════════════════════════════════════╗
║           🌊 AUREON QGITA TRADING ENGINE 🌊                ║
║                                                            ║
║  "The Dolphin sings the wave. The Tiger cuts the noise.   ║
║   The Owl remembers. The Panda loves."                     ║
║                                                            ║
║  Features:                                                 ║
║    • 9 Auris Node Operators                                ║
║    • QGITA Fibonacci Time Lattice                          ║
║    • Decision Fusion (Ensemble + Lighthouse)               ║
║    • Kelly Criterion Risk Sizing                           ║
║    • Proper LOT_SIZE Handling                              ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
        """)
        
        start = time.time()
        
        while time.time() - start < duration_sec:
            self.cycle += 1
            
            logger.info(f"\n🔄 Cycle {self.cycle} | Positions: {len(self.positions)} | Profit: ${self.total_profit:+.2f}")
            
            # Update tickers
            self.update_tickers()
            
            # Check exits
            self.check_exits()
            
            # Scan entries
            self.scan_for_entries()
            
            time.sleep(1)  # 1 second between cycles
        
        logger.info(f"\n🏁 Session complete. Total profit: ${self.total_profit:+.2f}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Paper trading mode')
    parser.add_argument('--duration', type=int, default=3600, help='Run duration in seconds')
    args = parser.parse_args()
    
    if not args.dry_run:
        if os.getenv('CONFIRM_LIVE', '').lower() != 'yes':
            logger.error("❌ Set CONFIRM_LIVE=yes for live trading")
            sys.exit(1)
        logger.warning("⚠️  LIVE TRADING MODE - REAL MONEY")
    
    trader = AureonQGITATrader(dry_run=args.dry_run)
    trader.run(duration_sec=args.duration)

if __name__ == "__main__":
    main()
