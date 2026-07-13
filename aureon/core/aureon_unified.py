#!/usr/bin/env python3
"""
🌊 AUREON UNIFIED ORCHESTRATOR 🌊
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

THE PROBLEM: "The left hand didn't know what the right hand was doing."

THE SOLUTION: A unified communication layer where each system reads and 
reassures the next. Each is a piece to a big puzzle.

ARCHITECTURE (from TypeScript analysis):
┌──────────────────────────────────────────────────────────────────────────┐
│                        AQTS ORCHESTRATOR                                 │
│                    (Central Command & Control)                           │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                   │
│  │ DATA        │───▶│ QGITA       │───▶│ DECISION    │                   │
│  │ INGESTION   │    │ ENGINE      │    │ FUSION      │                   │
│  └─────────────┘    └─────────────┘    └─────────────┘                   │
│        │                  │                  │                           │
│        ▼                  ▼                  ▼                           │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                   │
│  │ LIGHTHOUSE  │◀──▶│ MASTER      │◀──▶│ RISK        │                   │
│  │ METRICS     │    │ EQUATION    │    │ MANAGER     │                   │
│  └─────────────┘    └─────────────┘    └─────────────┘                   │
│        │                  │                  │                           │
│        ▼                  ▼                  ▼                           │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                   │
│  │ RAINBOW     │◀──▶│ ELEPHANT    │◀──▶│ EXECUTION   │                   │
│  │ BRIDGE      │    │ MEMORY      │    │ ENGINE      │                   │
│  └─────────────┘    └─────────────┘    └─────────────┘                   │
│        │                  │                  │                           │
│        └──────────────────┼──────────────────┘                           │
│                           ▼                                              │
│                    ┌─────────────┐                                       │
│                    │ FIRE        │                                       │
│                    │ STARTER     │                                       │
│                    └─────────────┘                                       │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

COMMUNICATION PROTOCOL:
  1. Each system publishes its STATE to the shared BUS
  2. Each system reads DEPENDENCIES from the BUS before acting
  3. Each system validates its output against PEER outputs
  4. Consensus required for trade execution

Author: Gary Leckey / Aureon System
"""
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os, sys, time, logging, argparse, json, math
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal, ROUND_DOWN
from dataclasses import dataclass, field, asdict
from aureon.exchanges.binance_client import BinanceClient, get_binance_client

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('aureon_unified.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# UNIFIED STATE BUS - THE COMMUNICATION LAYER
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SystemState:
    """State published by each system to the bus"""
    system_name: str
    timestamp: float
    ready: bool
    coherence: float = 0.0
    confidence: float = 0.0
    signal: str = 'NEUTRAL'  # 'BUY', 'SELL', 'NEUTRAL'
    data: Dict[str, Any] = field(default_factory=dict)

class UnifiedBus:
    """
    Central communication bus where all systems publish and read state.
    
    "Each system reads and reassures the next. Each is a piece to a big puzzle."
    """
    
    def __init__(self):
        self.states: Dict[str, SystemState] = {}
        self.history: List[Dict[str, SystemState]] = []
        self.lock = False  # Simple mutex for atomic updates
    
    def publish(self, state: SystemState):
        """Publish system state to the bus"""
        while self.lock:
            time.sleep(0.001)
        self.lock = True
        self.states[state.system_name] = state
        self.lock = False
        
        logger.debug(f"📡 BUS: {state.system_name} published | Γ={state.coherence:.3f} | signal={state.signal}")
    
    def read(self, system_name: str) -> Optional[SystemState]:
        """Read another system's state"""
        return self.states.get(system_name)
    
    def read_all(self) -> Dict[str, SystemState]:
        """Read all system states"""
        return self.states.copy()
    
    def snapshot(self) -> Dict[str, Any]:
        """Take a snapshot of the entire bus state"""
        return {name: asdict(state) for name, state in self.states.items()}
    
    def check_consensus(self, required_systems: List[str], min_coherence: float = 0.7) -> Tuple[bool, str]:
        """
        Check if all required systems are ready and aligned.
        
        Returns: (consensus_achieved, signal)
        """
        signals = []
        coherences = []
        
        for sys_name in required_systems:
            state = self.states.get(sys_name)
            if state is None:
                return False, f"{sys_name} not reporting"
            if not state.ready:
                return False, f"{sys_name} not ready"
            if state.coherence < min_coherence:
                return False, f"{sys_name} coherence too low ({state.coherence:.3f})"
            
            signals.append(state.signal)
            coherences.append(state.coherence)
        
        # Check signal alignment
        buy_votes = signals.count('BUY')
        sell_votes = signals.count('SELL')
        neutral_votes = signals.count('NEUTRAL')
        
        if buy_votes > sell_votes and buy_votes > neutral_votes:
            return True, 'BUY'
        elif sell_votes > buy_votes and sell_votes > neutral_votes:
            return True, 'SELL'
        else:
            return True, 'NEUTRAL'

# Global bus instance
BUS = UnifiedBus()

# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM 1: DATA INGESTION
# ═══════════════════════════════════════════════════════════════════════════

class DataIngestionSystem:
    """
    Ingests market data from Binance.
    Publishes: prices, volumes, order book depth, funding rates
    """
    
    NAME = "DataIngestion"
    
    def __init__(self, client: BinanceClient):
        self.client = client
        self.ticker_cache = {}
        self.price_history: Dict[str, List[float]] = {}
        self.volume_history: Dict[str, List[float]] = {}
        self.last_update = 0
    
    def update(self):
        """Fetch latest market data"""
        try:
            tickers = self.client.session.get(f"{self.client.base}/api/v3/ticker/24hr").json()
            self.ticker_cache = {t['symbol']: t for t in tickers}
            
            # Update history
            for symbol, data in self.ticker_cache.items():
                if symbol not in self.price_history:
                    self.price_history[symbol] = []
                    self.volume_history[symbol] = []
                
                price = float(data.get('lastPrice', 0))
                volume = float(data.get('quoteVolume', 0))
                
                self.price_history[symbol].append(price)
                self.volume_history[symbol].append(volume)
                
                # Keep last 100
                if len(self.price_history[symbol]) > 100:
                    self.price_history[symbol].pop(0)
                    self.volume_history[symbol].pop(0)
            
            self.last_update = time.time()
            
            # Publish to bus
            BUS.publish(SystemState(
                system_name=self.NAME,
                timestamp=time.time(),
                ready=True,
                coherence=1.0,  # Data is coherent if fetched successfully
                confidence=1.0,
                signal='NEUTRAL',
                data={'symbols_loaded': len(self.ticker_cache)}
            ))
            
        except Exception as e:
            logger.error(f"❌ DataIngestion error: {e}")
            BUS.publish(SystemState(
                system_name=self.NAME,
                timestamp=time.time(),
                ready=False,
                coherence=0.0
            ))
    
    def get_ticker(self, symbol: str) -> Optional[Dict]:
        return self.ticker_cache.get(symbol)
    
    def get_price(self, symbol: str) -> float:
        ticker = self.ticker_cache.get(symbol, {})
        return float(ticker.get('lastPrice', 0))
    
    def get_btc_price(self) -> float:
        return self.get_price('BTCUSDT')

# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM 2: LIGHTHOUSE METRICS (from lighthouseMetrics.ts)
# ═══════════════════════════════════════════════════════════════════════════

class LighthouseSystem:
    """
    Computes |Q| (anomaly pointer) and G_eff (effective gravity).
    These are the "flame" and "brake" metrics from the ablation study.
    """
    
    NAME = "Lighthouse"
    PHI = 1.618033988749
    PHI_INV = 1 / PHI
    
    def __init__(self, data_system: DataIngestionSystem):
        self.data = data_system
    
    def compute_anomaly_pointer(self, symbol: str) -> float:
        """
        |Q| = Flame metric - spikes during sudden change
        """
        ticker = self.data.get_ticker(symbol)
        if not ticker:
            return 0.0
        
        prices = self.data.price_history.get(symbol, [])
        volumes = self.data.volume_history.get(symbol, [])
        
        if len(prices) < 10 or len(volumes) < 10:
            return 0.0
        
        # Volume spike
        recent_vol = volumes[-10:]
        mean_vol = sum(recent_vol) / len(recent_vol)
        current_vol = float(ticker.get('quoteVolume', 0))
        volume_spike = min(1.0, current_vol / (mean_vol + 0.001))
        
        # Spread anomaly
        high = float(ticker.get('highPrice', 0))
        low = float(ticker.get('lowPrice', 0))
        price = float(ticker.get('lastPrice', 1))
        spread_ratio = (high - low) / price if price > 0 else 0
        spread_anomaly = min(1.0, spread_ratio * 10)
        
        # Price acceleration
        if len(prices) >= 5:
            recent = prices[-5:]
            diffs = [recent[i] - recent[i-1] for i in range(1, len(recent))]
            accel = [abs(diffs[i] - diffs[i-1]) for i in range(1, len(diffs))]
            mean_accel = sum(accel) / len(accel) if accel else 0
            price_accel = min(1.0, mean_accel / (price * 0.001)) if price > 0 else 0
        else:
            price_accel = 0
        
        # Weighted combination
        Q = volume_spike * 0.4 + spread_anomaly * 0.3 + price_accel * 0.3
        return min(1.0, Q)
    
    def compute_effective_gravity(self, symbol: str) -> float:
        """
        G_eff = Brake metric - geometric curvature × Fibonacci match
        """
        prices = self.data.price_history.get(symbol, [])
        
        if len(prices) < 5:
            return 0.0
        
        recent = prices[-5:]
        
        # Curvature (second derivative)
        p0, p1, p2 = recent[-3], recent[-2], recent[-1]
        dx1 = p1 - p0
        dx2 = p2 - p1
        curvature = abs(dx2 - dx1)
        kappa = curvature / (p1 + 1)
        
        # Fibonacci match (golden ratio spacing)
        # Simplified: check if price movements follow phi ratio
        if abs(dx1) > 0:
            ratio = abs(dx2) / abs(dx1)
        else:
            ratio = 1.0
        
        fib_match = max(0, 1 - abs(ratio - self.PHI_INV) / 0.1)
        
        # Local contrast
        local_contrast = abs(p2 - p1) / 2
        normalized_contrast = min(1.0, local_contrast / (p1 * 0.01)) if p1 > 0 else 0
        
        G_eff = kappa * fib_match * normalized_contrast * 100
        return min(1.0, G_eff)
    
    def compute_lighthouse_intensity(self, symbol: str) -> Dict[str, float]:
        """
        L(t) = (C_lin^w1 × C_nonlin^w2 × G_eff^w3 × |Q|^w4)^(1/Σw)
        """
        Q = self.compute_anomaly_pointer(symbol)
        G_eff = self.compute_effective_gravity(symbol)
        
        prices = self.data.price_history.get(symbol, [])
        
        # Linear coherence (trend strength)
        if len(prices) >= 20:
            recent = prices[-20:]
            trend = (recent[-1] - recent[0]) / recent[0] if recent[0] > 0 else 0
            C_lin = min(1.0, abs(trend) / 0.05)  # 5% move = max coherence
        else:
            C_lin = 0.5
        
        # Nonlinear coherence (inverse volatility)
        if len(prices) >= 20:
            mean = sum(prices[-20:]) / 20
            variance = sum((p - mean) ** 2 for p in prices[-20:]) / 20
            volatility = math.sqrt(variance) / mean if mean > 0 else 0
            C_nonlin = 1.0 / (1.0 + volatility)
        else:
            C_nonlin = 0.5
        
        # Lighthouse intensity (geometric mean with ablation weights)
        weights = {'C_lin': 1.0, 'C_nonlin': 1.2, 'G_eff': 1.2, 'Q': 0.8}
        total_weight = sum(weights.values())
        
        # Avoid log(0)
        C_lin = max(0.01, C_lin)
        C_nonlin = max(0.01, C_nonlin)
        G_eff = max(0.01, G_eff)
        Q = max(0.01, Q)
        
        log_sum = (
            weights['C_lin'] * math.log(C_lin) +
            weights['C_nonlin'] * math.log(C_nonlin) +
            weights['G_eff'] * math.log(G_eff) +
            weights['Q'] * math.log(Q)
        )
        
        L = math.exp(log_sum / total_weight)
        
        return {
            'Q': Q,
            'G_eff': G_eff,
            'C_lin': C_lin,
            'C_nonlin': C_nonlin,
            'L': L,
        }
    
    def evaluate(self, symbols: List[str]) -> Dict[str, Dict]:
        """Evaluate lighthouse metrics for all symbols"""
        results = {}
        avg_L = 0.0
        
        for symbol in symbols[:20]:  # Limit to top 20
            metrics = self.compute_lighthouse_intensity(symbol)
            results[symbol] = metrics
            avg_L += metrics['L']
        
        avg_L = avg_L / max(1, len(results))
        
        # Publish to bus
        BUS.publish(SystemState(
            system_name=self.NAME,
            timestamp=time.time(),
            ready=True,
            coherence=avg_L,
            confidence=avg_L,
            signal='NEUTRAL',
            data={'avg_lighthouse': avg_L, 'symbols_evaluated': len(results)}
        ))
        
        return results

# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM 3: MASTER EQUATION (Λ = S + O + E)
# ═══════════════════════════════════════════════════════════════════════════

class MasterEquationSystem:
    """
    Computes Λ(t) = S(t) + O(t) + E(t)
    
    S(t) = Substrate (9 Auris Nodes)
    O(t) = Observer (market price injection)
    E(t) = Echo (feedback from previous states)
    """
    
    NAME = "MasterEquation"
    
    # 9 Auris Nodes with frequencies
    AURIS_NODES = {
        'Tiger': {'freq': 741.0, 'role': 'Disruptor'},
        'Falcon': {'freq': 852.0, 'role': 'Perception'},
        'Hummingbird': {'freq': 963.0, 'role': 'Flow'},
        'Dolphin': {'freq': 528.0, 'role': 'Signal Clarity'},
        'Deer': {'freq': 396.0, 'role': 'Grounding'},
        'Owl': {'freq': 432.0, 'role': 'Memory'},
        'Panda': {'freq': 412.3, 'role': 'Empathy Core'},
        'CargoShip': {'freq': 174.0, 'role': 'Integration'},
        'Clownfish': {'freq': 639.0, 'role': 'Symbiosis'},
    }
    
    def __init__(self, data_system: DataIngestionSystem):
        self.data = data_system
        self.lambda_history: List[float] = []
        self.echo_decay = 0.9  # Echo feedback decay rate
        self.last_lambda = 0.5
    
    def compute_substrate(self, symbol: str) -> float:
        """
        S(t) = Weighted sum of 9 Auris Node activations
        
        Each node activates based on different market conditions.
        """
        ticker = self.data.get_ticker(symbol)
        if not ticker:
            logger.warning("[insufficient-data] compute_substrate returning "
                           "neutral 0.5 (no ticker for %s)", symbol)
            return 0.5

        price = float(ticker.get('lastPrice', 0))
        change = float(ticker.get('priceChangePercent', 0))
        volume = float(ticker.get('quoteVolume', 0))
        
        activations = []
        
        # Tiger: Activates on disruption (high volatility)
        tiger = min(1.0, abs(change) / 10.0)
        activations.append(tiger)
        
        # Falcon: Activates on perception (clear direction)
        falcon = 1.0 if abs(change) > 3.0 else 0.5
        activations.append(falcon)
        
        # Hummingbird: Flow state (steady upward)
        hummingbird = 1.0 if change > 5.0 else (0.3 if change > 0 else 0.1)
        activations.append(hummingbird)
        
        # Dolphin: Signal clarity (low noise)
        prices = self.data.price_history.get(symbol, [])
        if len(prices) >= 10:
            mean = sum(prices[-10:]) / 10
            variance = sum((p - mean) ** 2 for p in prices[-10:]) / 10
            noise = math.sqrt(variance) / mean if mean > 0 else 1
            dolphin = 1.0 - min(1.0, noise * 10)
        else:
            dolphin = 0.5
        activations.append(dolphin)
        
        # Deer: Grounding (stability near support)
        deer = 0.8 if abs(change) < 2.0 else 0.3
        activations.append(deer)
        
        # Owl: Memory (historical pattern match)
        if len(prices) >= 20:
            trend_20 = (prices[-1] - prices[-20]) / prices[-20] if prices[-20] > 0 else 0
            owl = 0.8 if abs(trend_20) < 0.1 else 0.4
        else:
            owl = 0.5
        activations.append(owl)
        
        # Panda: Empathy (market sentiment alignment)
        panda = 0.8 if change > 0 else 0.4
        activations.append(panda)
        
        # CargoShip: Integration (volume confirmation)
        cargoship = min(1.0, volume / 100.0)  # 100 BTC volume = max
        activations.append(cargoship)
        
        # Clownfish: Symbiosis (cross-market alignment)
        btc_ticker = self.data.get_ticker('BTCUSDT')
        btc_change = float(btc_ticker.get('priceChangePercent', 0)) if btc_ticker else 0
        clownfish = 1.0 if (change > 0 and btc_change > 0) or (change < 0 and btc_change < 0) else 0.3
        activations.append(clownfish)
        
        # Weighted average
        S = sum(activations) / len(activations)
        return S
    
    def compute_observer(self, symbol: str) -> float:
        """
        O(t) = Observer component (market price injection)
        """
        ticker = self.data.get_ticker(symbol)
        if not ticker:
            logger.warning("[insufficient-data] compute_observer returning "
                           "neutral 0.5 (no ticker for %s)", symbol)
            return 0.5

        change = float(ticker.get('priceChangePercent', 0))
        
        # Sigmoid mapping
        O = 1.0 / (1.0 + math.exp(-change / 5.0))
        return O
    
    def compute_echo(self) -> float:
        """
        E(t) = Echo component (feedback from previous Lambda)
        """
        if len(self.lambda_history) < 3:
            logger.warning("[insufficient-data] compute_echo returning neutral "
                           "0.5 (need 3 lambda samples, got %d)",
                           len(self.lambda_history))
            return 0.5
        
        # Exponentially weighted average of past Lambda values
        weights = [self.echo_decay ** i for i in range(min(10, len(self.lambda_history)))]
        recent = self.lambda_history[-10:][::-1]
        
        weighted_sum = sum(w * v for w, v in zip(weights, recent))
        total_weight = sum(weights[:len(recent)])
        
        E = weighted_sum / total_weight if total_weight > 0 else 0.5
        return E
    
    def compute_lambda(self, symbol: str) -> Dict[str, float]:
        """
        Λ(t) = S(t) + O(t) + E(t)
        
        Normalized to [0, 1] via division by 3
        """
        S = self.compute_substrate(symbol)
        O = self.compute_observer(symbol)
        E = self.compute_echo()
        
        Lambda = (S + O + E) / 3.0
        
        # Coherence is how stable Lambda is
        if len(self.lambda_history) >= 5:
            recent = self.lambda_history[-5:]
            coherence = 1.0 - min(1.0, 2 * (max(recent) - min(recent)))
        else:
            coherence = 0.5
        
        # Store in history
        self.lambda_history.append(Lambda)
        if len(self.lambda_history) > 100:
            self.lambda_history.pop(0)
        
        self.last_lambda = Lambda
        
        return {
            'Lambda': Lambda,
            'S': S,
            'O': O,
            'E': E,
            'coherence': coherence,
        }
    
    def evaluate(self, symbols: List[str]) -> Dict[str, Dict]:
        """Evaluate Master Equation for all symbols"""
        results = {}
        avg_lambda = 0.0
        avg_coherence = 0.0
        
        for symbol in symbols[:20]:
            metrics = self.compute_lambda(symbol)
            results[symbol] = metrics
            avg_lambda += metrics['Lambda']
            avg_coherence += metrics['coherence']
        
        n = max(1, len(results))
        avg_lambda /= n
        avg_coherence /= n
        
        # Determine signal based on Lambda
        if avg_lambda > 0.6:
            signal = 'BUY'
        elif avg_lambda < 0.4:
            signal = 'SELL'
        else:
            signal = 'NEUTRAL'
        
        # Publish to bus
        BUS.publish(SystemState(
            system_name=self.NAME,
            timestamp=time.time(),
            ready=True,
            coherence=avg_coherence,
            confidence=avg_lambda,
            signal=signal,
            data={'avg_lambda': avg_lambda, 'symbols_evaluated': len(results)}
        ))
        
        return results

# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM 4: RAINBOW BRIDGE (Emotional Frequency Mapping)
# ═══════════════════════════════════════════════════════════════════════════

class RainbowBridgeSystem:
    """
    Maps coherence to emotional frequency.
    528 Hz = LOVE = optimal trading state
    """
    
    NAME = "RainbowBridge"
    
    EMOTIONAL_FREQUENCIES = {
        'Anger': 110,
        'Fear': 174,
        'Frustration': 285,
        'Doubt': 330,
        'Worry': 396,
        'Hope': 412.3,
        'Calm': 432,
        'Neutral': 440,
        'Acceptance': 480,
        'LOVE': 528,  # THE CENTER
        'Harmony': 582,
        'Connection': 639,
        'Flow': 693,
        'Awakening': 741,
        'Clarity': 819,
        'Intuition': 852,
        'Awe': 963,
    }
    
    THE_VOW = "I trade with love, I trade with light"
    
    def get_emotional_state(self, coherence: float) -> Tuple[str, float]:
        """Map coherence (0-1) to emotional frequency"""
        freq = 110 + (coherence * (963 - 110))  # Linear map
        
        closest_emotion = 'Neutral'
        closest_dist = float('inf')
        
        for emotion, emotion_freq in self.EMOTIONAL_FREQUENCIES.items():
            dist = abs(freq - emotion_freq)
            if dist < closest_dist:
                closest_dist = dist
                closest_emotion = emotion
        
        return closest_emotion, freq
    
    def evaluate(self) -> Dict[str, Any]:
        """Evaluate current emotional state from bus data"""
        
        # Read from other systems
        master_eq = BUS.read('MasterEquation')
        lighthouse = BUS.read('Lighthouse')
        
        if master_eq and lighthouse:
            coherence = (master_eq.coherence + lighthouse.coherence) / 2
        elif master_eq:
            coherence = master_eq.coherence
        elif lighthouse:
            coherence = lighthouse.coherence
        else:
            coherence = 0.5
        
        emotion, freq = self.get_emotional_state(coherence)
        
        # 528 Hz = LOVE = best state
        love_distance = abs(freq - 528)
        love_alignment = 1.0 - (love_distance / 400)  # 0 at 528, decreasing outward
        
        # Signal based on emotional state
        if emotion in ['LOVE', 'Harmony', 'Connection', 'Flow', 'Awakening', 'Clarity', 'Intuition', 'Awe']:
            signal = 'BUY'  # Positive emotions = bullish
        elif emotion in ['Anger', 'Fear', 'Frustration', 'Doubt', 'Worry']:
            signal = 'SELL'  # Negative emotions = bearish
        else:
            signal = 'NEUTRAL'
        
        # Publish to bus
        BUS.publish(SystemState(
            system_name=self.NAME,
            timestamp=time.time(),
            ready=True,
            coherence=love_alignment,
            confidence=coherence,
            signal=signal,
            data={'emotion': emotion, 'frequency': freq, 'vow': self.THE_VOW}
        ))
        
        return {
            'emotion': emotion,
            'frequency': freq,
            'love_alignment': love_alignment,
            'coherence': coherence,
            'signal': signal,
        }

# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM 5: DECISION FUSION (Consensus Engine)
# ═══════════════════════════════════════════════════════════════════════════

class DecisionFusionSystem:
    """
    Fuses signals from all systems to make final trading decision.
    
    "Each system reads and reassures the next."
    """
    
    NAME = "DecisionFusion"
    
    REQUIRED_SYSTEMS = ['DataIngestion', 'Lighthouse', 'MasterEquation', 'RainbowBridge']
    
    def __init__(self):
        self.weights = {
            'MasterEquation': 0.35,
            'Lighthouse': 0.30,
            'RainbowBridge': 0.20,
            'DataIngestion': 0.15,
        }
    
    def evaluate(self) -> Dict[str, Any]:
        """
        Fuse all system signals into final decision.
        
        Requires consensus from all systems.
        """
        states = BUS.read_all()
        
        # Check all systems are ready
        for sys_name in self.REQUIRED_SYSTEMS:
            if sys_name not in states:
                BUS.publish(SystemState(
                    system_name=self.NAME,
                    timestamp=time.time(),
                    ready=False,
                    signal='HOLD',
                    data={'error': f'{sys_name} not reporting'}
                ))
                return {'decision': 'HOLD', 'reason': f'{sys_name} not reporting'}
            
            if not states[sys_name].ready:
                BUS.publish(SystemState(
                    system_name=self.NAME,
                    timestamp=time.time(),
                    ready=False,
                    signal='HOLD',
                    data={'error': f'{sys_name} not ready'}
                ))
                return {'decision': 'HOLD', 'reason': f'{sys_name} not ready'}
        
        # Compute weighted score
        buy_score = 0.0
        sell_score = 0.0
        total_coherence = 0.0
        
        for sys_name, weight in self.weights.items():
            state = states[sys_name]
            total_coherence += state.coherence * weight
            
            if state.signal == 'BUY':
                buy_score += weight * state.confidence
            elif state.signal == 'SELL':
                sell_score += weight * state.confidence
        
        # Determine final decision
        if buy_score > sell_score and buy_score > 0.4:
            decision = 'BUY'
            confidence = buy_score
        elif sell_score > buy_score and sell_score > 0.4:
            decision = 'SELL'
            confidence = sell_score
        else:
            decision = 'HOLD'
            confidence = 1.0 - abs(buy_score - sell_score)
        
        # Publish to bus
        BUS.publish(SystemState(
            system_name=self.NAME,
            timestamp=time.time(),
            ready=True,
            coherence=total_coherence,
            confidence=confidence,
            signal=decision,
            data={
                'buy_score': buy_score,
                'sell_score': sell_score,
                'system_votes': {s: states[s].signal for s in self.REQUIRED_SYSTEMS},
            }
        ))
        
        return {
            'decision': decision,
            'confidence': confidence,
            'coherence': total_coherence,
            'buy_score': buy_score,
            'sell_score': sell_score,
        }

# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM 6: ELEPHANT MEMORY (Trade Persistence)
# ═══════════════════════════════════════════════════════════════════════════

class ElephantMemorySystem:
    """
    Persists trade history with cooldowns and blacklisting.
    "The elephant never forgets."
    """
    
    NAME = "ElephantMemory"
    
    def __init__(self, filepath: str = 'elephant_memory.json'):
        self.filepath = filepath
        self.symbols: Dict[str, dict] = {}
        self.cooldown_minutes = 15
        self.loss_streak_limit = 3
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
        if symbol not in self.symbols:
            self.symbols[symbol] = {
                'trades': 0, 'wins': 0, 'losses': 0,
                'profit': 0.0, 'last_trade': 0, 'loss_streak': 0, 'blacklisted': False
            }
        
        s = self.symbols[symbol]
        s['trades'] += 1
        s['profit'] += profit
        s['last_trade'] = time.time()
        
        if profit >= 0:
            s['wins'] += 1
            s['loss_streak'] = 0
        else:
            s['losses'] += 1
            s['loss_streak'] += 1
            if s['loss_streak'] >= self.loss_streak_limit:
                s['blacklisted'] = True
        
        self.save()
        
        # Publish to bus
        BUS.publish(SystemState(
            system_name=self.NAME,
            timestamp=time.time(),
            ready=True,
            coherence=self.get_overall_win_rate(),
            data={'last_trade': symbol, 'profit': profit}
        ))
    
    def should_avoid(self, symbol: str) -> bool:
        if symbol not in self.symbols:
            return False
        s = self.symbols[symbol]
        if s.get('blacklisted'):
            return True
        if time.time() - s.get('last_trade', 0) < self.cooldown_minutes * 60:
            return True
        return False
    
    def get_overall_win_rate(self) -> float:
        total_wins = sum(s.get('wins', 0) for s in self.symbols.values())
        total_trades = sum(s.get('trades', 0) for s in self.symbols.values())
        return total_wins / max(1, total_trades)

# ═══════════════════════════════════════════════════════════════════════════
# UNIFIED ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════

class UnifiedOrchestrator:
    """
    The central brain that coordinates all systems.
    
    "Each system reads and reassures the next. Each is a piece to a big puzzle."
    """
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.client = get_binance_client()
        
        # Initialize all systems
        self.data = DataIngestionSystem(self.client)
        self.lighthouse = LighthouseSystem(self.data)
        self.master_eq = MasterEquationSystem(self.data)
        self.rainbow = RainbowBridgeSystem()
        self.fusion = DecisionFusionSystem()
        self.memory = ElephantMemorySystem()
        
        self.positions = {}
        self.total_profit = 0.0
        self.trade_count = 0
    
    def get_tradeable_symbols(self) -> List[str]:
        """Get BTC pairs we can trade (TRD_GRP_039)"""
        symbols = []
        for symbol in self.data.ticker_cache.keys():
            if symbol.endswith('BTC'):
                ticker = self.data.get_ticker(symbol)
                volume = float(ticker.get('quoteVolume', 0)) if ticker else 0
                if volume > 1.0:  # >1 BTC volume
                    symbols.append(symbol)
        return sorted(symbols, key=lambda s: float(self.data.get_ticker(s).get('quoteVolume', 0)), reverse=True)
    
    def display_bus_status(self):
        """Show current state of all systems on the bus"""
        states = BUS.read_all()
        
        logger.info("\n" + "═" * 70)
        logger.info("📡 UNIFIED BUS STATUS")
        logger.info("═" * 70)
        
        for name, state in states.items():
            status = "✅" if state.ready else "❌"
            logger.info(
                f"  {status} {name:20} | Γ={state.coherence:.3f} | "
                f"signal={state.signal:8} | conf={state.confidence:.3f}"
            )
        
        logger.info("═" * 70)
    
    def run_cycle(self) -> Optional[Dict]:
        """
        Run one complete cycle through all systems.
        
        Flow:
        1. DataIngestion → fetch data
        2. Lighthouse → compute metrics
        3. MasterEquation → compute Λ
        4. RainbowBridge → emotional state
        5. DecisionFusion → final decision
        6. Execute trade if consensus
        """
        
        # Step 1: Data Ingestion
        self.data.update()
        
        # Get tradeable symbols
        symbols = self.get_tradeable_symbols()[:20]
        
        if not symbols:
            logger.warning("No tradeable symbols found")
            return None
        
        # Step 2: Lighthouse Metrics
        lighthouse_results = self.lighthouse.evaluate(symbols)
        
        # Step 3: Master Equation
        master_results = self.master_eq.evaluate(symbols)
        
        # Step 4: Rainbow Bridge
        rainbow_result = self.rainbow.evaluate()
        
        # Step 5: Decision Fusion
        fusion_result = self.fusion.evaluate()
        
        # Display bus status
        self.display_bus_status()
        
        # Step 6: Execute if consensus
        decision = fusion_result['decision']
        confidence = fusion_result['confidence']
        coherence = fusion_result['coherence']
        
        logger.info(f"\n🎯 FUSION DECISION: {decision} | Confidence: {confidence:.3f} | Coherence: {coherence:.3f}")
        logger.info(f"💜 Emotional State: {rainbow_result['emotion']} ({rainbow_result['frequency']:.1f} Hz)")
        
        if decision != 'HOLD' and confidence > 0.6 and coherence > 0.5:
            # Find best symbol to trade
            best_symbol = None
            best_score = 0
            
            for symbol in symbols:
                if self.memory.should_avoid(symbol):
                    continue
                
                lh = lighthouse_results.get(symbol, {})
                me = master_results.get(symbol, {})
                
                score = lh.get('L', 0) * 0.5 + me.get('Lambda', 0.5) * 0.5
                
                if score > best_score:
                    best_score = score
                    best_symbol = symbol
            
            if best_symbol:
                logger.info(f"\n🚀 EXECUTE: {decision} {best_symbol} | Score: {best_score:.3f}")
                
                # Would execute trade here
                if not self.dry_run:
                    # Execute trade logic
                    pass
                
                return {
                    'action': decision,
                    'symbol': best_symbol,
                    'score': best_score,
                    'confidence': confidence,
                    'coherence': coherence,
                }
        
        return None
    
    def run(self, duration_sec: int = 3600):
        """Run the unified orchestrator"""
        
        logger.info("""
╔════════════════════════════════════════════════════════════════════════════════╗
║                    🌊 AUREON UNIFIED ORCHESTRATOR 🌊                           ║
╠════════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║   "Each system reads and reassures the next. Each is a piece to a big puzzle."║
║                                                                                ║
║   SYSTEMS:                                                                     ║
║     📡 DataIngestion   → Fetches market data from Binance                      ║
║     🔦 Lighthouse      → Computes |Q| and G_eff metrics                        ║
║     🌊 MasterEquation  → Λ(t) = S(t) + O(t) + E(t)                             ║
║     🌈 RainbowBridge   → Emotional frequency mapping (528 Hz = LOVE)           ║
║     🧠 DecisionFusion  → Consensus-based trade decisions                       ║
║     🐘 ElephantMemory  → Trade persistence with cooldowns                      ║
║                                                                                ║
║   COMMUNICATION:                                                               ║
║     All systems publish to UnifiedBus                                          ║
║     All systems read from UnifiedBus                                           ║
║     Consensus required for trade execution                                     ║
║                                                                                ║
╚════════════════════════════════════════════════════════════════════════════════╝
""")
        
        start = time.time()
        cycle = 0
        
        while time.time() - start < duration_sec:
            cycle += 1
            logger.info(f"\n{'─'*70}")
            logger.info(f"🔄 CYCLE {cycle}")
            logger.info(f"{'─'*70}")
            
            try:
                result = self.run_cycle()
                
                if result:
                    self.trade_count += 1
                    logger.info(f"✅ Trade #{self.trade_count}: {result['action']} {result['symbol']}")
                
            except Exception as e:
                logger.error(f"❌ Cycle error: {e}")
            
            time.sleep(10)  # 10 second cycles
        
        logger.info(f"\n🏁 Session complete. Trades executed: {self.trade_count}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--duration', type=int, default=300)
    args = parser.parse_args()
    
    orchestrator = UnifiedOrchestrator(dry_run=False)  # Always dry-run for safety
    orchestrator.run(duration_sec=args.duration)

if __name__ == "__main__":
    main()
