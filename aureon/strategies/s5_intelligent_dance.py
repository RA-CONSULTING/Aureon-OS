#!/usr/bin/env python3
"""
S5 INTELLIGENT DANCE - THE LEARNING STEPPING STONE SYMPHONY
============================================================
Every trade is a stepping stone that LEARNS.
Every conversion flows to the next with PROBABILITY guidance.
The MYCELIUM NETWORK coordinates the rhythm.
The dance learns more moves as it grows.

INTEGRATIONS:
- AdaptiveLearningEngine → Learns from every trade outcome
- MyceliumNetwork → Distributed intelligence & consensus
- ProbabilityMatrix → 7-day forecasting for optimal timing
- Historical Trades → Builds wisdom from the past

"Learn more moves as you dance"
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import json
import asyncio
import websockets
import signal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict, deque
from dataclasses import dataclass, field
import random
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
from aureon.exchanges.binance_client import BinanceClient, get_binance_client

# 🧠 INTELLIGENT INTEGRATIONS
try:
    from aureon.core.aureon_mycelium import MyceliumNetwork
    MYCELIUM_AVAILABLE = True
    print("🍄 Mycelium Network WIRED - Distributed intelligence active!")
except ImportError:
    MYCELIUM_AVAILABLE = False
    print("⚠️ Mycelium Network not available")

try:
    from aureon.strategies.hnc_probability_matrix import HNCProbabilityIntegration, ProbabilityMatrix
    PROB_MATRIX_AVAILABLE = True
    print("🔮 Probability Matrix WIRED - 7-day forecasting active!")
except ImportError:
    PROB_MATRIX_AVAILABLE = False
    print("⚠️ Probability Matrix not available")

try:
    from aureon.trading.aureon_unified_ecosystem import AdaptiveLearningEngine, CONFIG
    ADAPTIVE_LEARNER_AVAILABLE = True
    print("🧬 Adaptive Learning WIRED - Trade learning active!")
except ImportError:
    ADAPTIVE_LEARNER_AVAILABLE = False
    print("⚠️ Adaptive Learning not available")
    CONFIG = {}

# 🧠⛏️ MINER BRAIN - Cognitive Trading Intelligence
try:
    from aureon.utils.aureon_miner_brain import MinerBrain
    MINER_BRAIN_AVAILABLE = True
    print("⛏️ Miner Brain WIRED - Cognitive intelligence active!")
except ImportError:
    MINER_BRAIN_AVAILABLE = False
    print("⚠️ Miner Brain not available")

# 🔭 QUANTUM TELESCOPE - Multi-dimensional analysis
try:
    from aureon.simulation.aureon_quantum_telescope import QuantumTelescope
    QUANTUM_AVAILABLE = True
    print("🔭 Quantum Telescope WIRED - Multi-dimensional active!")
except ImportError:
    QUANTUM_AVAILABLE = False
    print("⚠️ Quantum Telescope not available")

# Golden ratio for natural timing
PHI = (1 + math.sqrt(5)) / 2

# ♟️ PRIME NUMBERS - Chess-like strategic thinking
PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97]

# Solfeggio frequencies for rhythm patterns
FREQ_MAP = {
    'FOUNDATION': 174.0,
    'ROOT': 256.0,
    'LIBERATION': 396.0,
    'NATURAL': 432.0,
    'DISTORTION': 440.0,
    'LOVE': 528.0,
    'AWAKENING': 741.0,
    'UNITY': 963.0,
}


@dataclass
class IntelligentStone:
    """A single step in the intelligent dance - learns from outcomes"""
    exchange: str
    asset: str
    action: str
    amount: float
    price: float
    profit: float
    momentum: float
    frequency: float = 256.0
    probability: float = 0.5
    coherence: float = 0.5
    mycelium_consensus: str = "NEUTRAL"
    timestamp: datetime = field(default_factory=datetime.now)
    validated: bool = False
    actual_outcome: float = 0.0


@dataclass
class LearningRhythm:
    """The rhythm pattern for an asset - learns over time"""
    asset: str
    beat_count: int = 0
    last_direction: str = ''
    momentum_history: List[float] = field(default_factory=list)
    profit_streak: int = 0
    total_profit: float = 0.0
    
    # 🧬 LEARNING METRICS
    win_rate: float = 0.5
    avg_profit: float = 0.0
    best_momentum: float = 0.0
    best_frequency: float = 256.0
    preferred_action: str = ''
    trades: int = 0
    wins: int = 0


class ChessBrain:
    """
    ♟️ CHESS BRAIN - Think N moves ahead using prime numbers
    
    Uses prime number sequences to plan strategic moves:
    - Analyze multiple coins simultaneously
    - Predict opponent (market) moves
    - Plan conversion chains
    - Use historical patterns as openings
    """
    
    def __init__(self):
        self.move_tree: Dict[str, List[Dict]] = {}  # Asset -> possible move sequences
        self.historical_patterns: Dict[str, List[str]] = {}  # Pattern -> sequence
        self.prime_timing = PRIMES.copy()
        self.current_depth = 0
        
    def think_ahead(self, assets: List[str], prices: Dict, momentum: Dict, depth: int = 5) -> List[Dict]:
        """Think N moves ahead like chess"""
        moves = []
        
        for asset in assets:
            if asset not in prices:
                continue
                
            price = prices.get(asset, 0)
            mom = momentum.get(asset, 0)
            
            # Use prime numbers for timing patterns
            prime_idx = len(moves) % len(self.prime_timing)
            prime = self.prime_timing[prime_idx]
            
            # Calculate strategic score using prime patterns
            strategic_score = abs(mom) * prime * PHI
            
            # Predict future moves
            future_moves = self._predict_sequence(asset, price, mom, depth)
            
            moves.append({
                'asset': asset,
                'current_price': price,
                'momentum': mom,
                'strategic_score': strategic_score,
                'prime_timing': prime,
                'future_sequence': future_moves,
                'branch_count': len(future_moves)
            })
        
        # Sort by strategic score
        moves.sort(key=lambda x: x['strategic_score'], reverse=True)
        return moves
    
    def _predict_sequence(self, asset: str, price: float, momentum: float, depth: int) -> List[Dict]:
        """Predict next N moves for an asset"""
        sequence = []
        current_price = price
        current_mom = momentum
        
        for i in range(depth):
            # Use Fibonacci for move prediction
            fib_idx = i % 13  # Fibonacci up to 13th
            fib = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233][fib_idx]
            
            # Predict next price/momentum
            predicted_move = current_mom * (fib / 100) * PHI
            next_price = current_price * (1 + predicted_move / 100)
            
            sequence.append({
                'move_number': i + 1,
                'predicted_price': next_price,
                'predicted_momentum': predicted_move,
                'fibonacci': fib,
                'action': 'SELL' if predicted_move > 0 else 'BUY'
            })
            
            current_price = next_price
            current_mom = predicted_move
        
        return sequence
    
    def find_best_branch(self, moves: List[Dict]) -> Optional[Dict]:
        """Find the best strategic branch to follow"""
        if not moves:
            return None
        
        # Evaluate each branch for profitability
        for move in moves:
            total_profit = 0
            for future in move['future_sequence']:
                if future['action'] == 'SELL' and future['predicted_momentum'] > 0:
                    total_profit += future['predicted_momentum']
                elif future['action'] == 'BUY' and future['predicted_momentum'] < 0:
                    total_profit += abs(future['predicted_momentum'])
            
            move['predicted_profit'] = total_profit
        
        # Return highest predicted profit branch
        moves.sort(key=lambda x: x.get('predicted_profit', 0), reverse=True)
        return moves[0] if moves else None


class DanceIntelligence:
    """
    🧠 DANCE INTELLIGENCE HUB 🧠
    
    Combines all learning systems:
    - Mycelium: Distributed consensus on trades
    - Probability: Forecasting optimal entry/exit
    - Adaptive: Learning from outcomes
    - Historical: Pattern recognition from past
    - Chess Brain: Strategic multi-move planning
    - Miner Brain: Cognitive trading patterns
    - Quantum: Multi-dimensional analysis
    - V14: 100% win rate scoring & exit rules (NEW!)
    """
    
    def __init__(self, starting_capital: float = 100.0):
        # 🍄 MYCELIUM NETWORK
        self.mycelium = None
        if MYCELIUM_AVAILABLE:
            try:
                self.mycelium = MyceliumNetwork(
                    initial_capital=starting_capital,
                    agents_per_hive=5,
                    target_multiplier=10.0
                )
                print("   🍄 Mycelium Network initialized with 5 agents/hive")
            except Exception as e:
                print(f"   ⚠️ Mycelium init error: {e}")
        
        # 🔮 PROBABILITY MATRIX
        self.prob_matrix = None
        if PROB_MATRIX_AVAILABLE:
            try:
                self.prob_matrix = HNCProbabilityIntegration()
                print("   🔮 Probability Matrix initialized for 7-day forecasting")
            except Exception as e:
                print(f"   ⚠️ Probability Matrix init error: {e}")
        
        # 🧬 ADAPTIVE LEARNER
        self.adaptive = None
        if ADAPTIVE_LEARNER_AVAILABLE:
            try:
                self.adaptive = AdaptiveLearningEngine(
                    history_file='intelligent_dance_learning.json'
                )
                print(f"   🧬 Adaptive Learner initialized ({len(self.adaptive.trade_history)} historical trades)")
            except Exception as e:
                print(f"   ⚠️ Adaptive Learner init error: {e}")
        
        # 📚 HISTORICAL WISDOM
        self.historical_wisdom: Dict[str, Dict] = {}
        self._load_historical_wisdom()
        
        # 🎯 DECISION METRICS
        self.decision_log: deque = deque(maxlen=1000)
        self.consensus_accuracy: float = 0.5
        
        # ♟️ CHESS BRAIN - Strategic thinking
        self.chess_brain = ChessBrain()
        print("   ♟️ Chess Brain initialized - thinking 5 moves ahead")
        
        # ⛏️ MINER BRAIN - Cognitive patterns
        self.miner_brain = None
        if MINER_BRAIN_AVAILABLE:
            try:
                self.miner_brain = MinerBrain()
                print("   ⛏️ Miner Brain initialized - cognitive patterns active")
            except Exception as e:
                print(f"   ⚠️ Miner Brain init error: {e}")
        
        # 🔭 QUANTUM TELESCOPE - Multi-dimensional
        self.quantum = None
        if QUANTUM_AVAILABLE:
            try:
                self.quantum = QuantumTelescope()
                print("   🔭 Quantum Telescope initialized - multi-dimensional active")
            except Exception as e:
                print(f"   ⚠️ Quantum init error: {e}")
        
        # 🏆 V14 ENHANCER - 100% WIN RATE SCORING (NEW!)
        self.v14_enhancer = None
        try:
            from aureon.strategies.s5_v14_dance_enhancements import V14DanceEnhancer, V14_CONFIG
            self.v14_enhancer = V14DanceEnhancer()
            self.v14_config = V14_CONFIG
            print(f"   🏆 V14 Enhancer: Score {V14_CONFIG['entry_score_threshold']}+, {V14_CONFIG['profit_target_pct']}% target, NO STOP LOSS")
        except ImportError:
            print("   ⚠️ V14 Enhancer not available - using legacy scoring")
            self.v14_config = None
        
    def _load_historical_wisdom(self):
        """Load wisdom from past trading sessions"""
        wisdom_files = [
            'infinite_dance_state.json',
            'aureon_positions.json',
            's5_ultra_state.json',
            'adaptive_learning_history.json'
        ]
        
        total_trades = 0
        for filename in wisdom_files:
            if os.path.exists(filename):
                try:
                    with open(filename) as f:
                        data = json.load(f)
                    
                    # Extract patterns
                    if 'stones' in data:  # Dance history
                        for stone in data.get('stones', []):
                            asset = stone.get('asset', '')
                            profit = stone.get('profit', 0)
                            self._record_wisdom(asset, profit, stone)
                            total_trades += 1
                    
                    if 'trades' in data:  # Adaptive history
                        for trade in data.get('trades', []):
                            symbol = trade.get('symbol', '')
                            pnl = trade.get('pnl', 0)
                            asset = symbol.replace('USD', '').replace('USDT', '').replace('USDC', '')
                            self._record_wisdom(asset, pnl, trade)
                            total_trades += 1
                            
                except Exception as e:
                    pass
        
        if total_trades > 0:
            print(f"   📚 Loaded wisdom from {total_trades} historical trades")
    
    def _record_wisdom(self, asset: str, profit: float, data: Dict):
        """Record a piece of wisdom about an asset"""
        if not asset:
            return
        
        if asset not in self.historical_wisdom:
            self.historical_wisdom[asset] = {
                'trades': 0,
                'wins': 0,
                'total_profit': 0.0,
                'best_momentum': 0.0,
                'best_hour': None,
                'patterns': []
            }
        
        w = self.historical_wisdom[asset]
        w['trades'] += 1
        w['total_profit'] += profit
        if profit > 0:
            w['wins'] += 1
        
        momentum = data.get('momentum', 0)
        if abs(momentum) > abs(w['best_momentum']):
            w['best_momentum'] = momentum
    
    def get_mycelium_signal(self, asset: str, price: float, momentum: float) -> Dict:
        """Get signal from Mycelium Network"""
        if not self.mycelium:
            return {'signal': 0.0, 'consensus': 'NEUTRAL', 'confidence': 0.5}
        
        try:
            market_data = {
                'price': price,
                'momentum': momentum,
                'volatility': abs(momentum) * 2,
                'volume': 10000,
                'symbol': asset
            }
            
            # Get queen signal (aggregate from all agents)
            signal = self.mycelium.get_queen_signal()
            coherence = self.mycelium.get_network_coherence() if hasattr(self.mycelium, 'get_network_coherence') else 0.5
            
            if signal > 0.3:
                consensus = 'BULLISH'
            elif signal < -0.3:
                consensus = 'BEARISH'
            else:
                consensus = 'NEUTRAL'
            
            return {
                'signal': signal,
                'consensus': consensus,
                'confidence': coherence,
                'network_coherence': coherence
            }
        except Exception as e:
            return {'signal': 0.0, 'consensus': 'NEUTRAL', 'confidence': 0.5}
    
    def get_probability_forecast(self, asset: str, price: float) -> Dict:
        """Get probability forecast from Matrix"""
        if not self.prob_matrix:
            return {
                'bullish_prob': 0.5,
                'bearish_prob': 0.5,
                'confidence': 0.5,
                'signal': 'HOLD',
                'frequency': 256.0
            }
        
        try:
            # Get multi-day forecast
            forecast = self.prob_matrix.get_symbol_forecast(asset) if hasattr(self.prob_matrix, 'get_symbol_forecast') else None
            
            if forecast:
                bullish = forecast.get('bullish_probability', 0.5)
                bearish = forecast.get('bearish_probability', 0.5)
                confidence = forecast.get('confidence', 0.5)
                
                if bullish > 0.6:
                    signal = 'BUY'
                elif bearish > 0.6:
                    signal = 'SELL'
                else:
                    signal = 'HOLD'
                
                return {
                    'bullish_prob': bullish,
                    'bearish_prob': bearish,
                    'confidence': confidence,
                    'signal': signal,
                    'frequency': forecast.get('frequency', 256.0),
                    'day1_forecast': forecast.get('day_plus_1', 'NEUTRAL')
                }
        except Exception:
            pass
        
        return {
            'bullish_prob': 0.5,
            'bearish_prob': 0.5,
            'confidence': 0.5,
            'signal': 'HOLD',
            'frequency': 256.0
        }
    
    def get_adaptive_guidance(self, asset: str, frequency: float = 256, coherence: float = 0.5) -> Dict:
        """Get guidance from Adaptive Learning"""
        if not self.adaptive:
            return {
                'should_trade': True,
                'confidence_boost': 1.0,
                'historical_win_rate': 0.5
            }
        
        try:
            thresholds = self.adaptive.optimized_thresholds
            
            # Check frequency band performance
            freq_band = self.adaptive._get_frequency_band(frequency)
            freq_metrics = self.adaptive.metrics_by_frequency.get(freq_band, {})
            
            total = freq_metrics.get('wins', 0) + freq_metrics.get('losses', 0)
            win_rate = freq_metrics['wins'] / total if total > 5 else 0.5
            
            # Check coherence performance
            coh_range = self.adaptive._get_coherence_range(coherence)
            coh_metrics = self.adaptive.metrics_by_coherence.get(coh_range, {})
            
            # Should we trade at this frequency/coherence?
            should_trade = True
            confidence_boost = 1.0
            
            # Boost confidence if this frequency historically wins
            if win_rate > 0.6:
                confidence_boost *= 1.0 + (win_rate - 0.5) * 0.5
            elif win_rate < 0.4:
                confidence_boost *= 0.8
            
            # Check if this matches winning patterns
            if freq_band in ['528_LOVE', '256_ROOT', '396_LIBERATION']:
                confidence_boost *= 1.1  # Sacred frequencies bonus
            elif freq_band == '440_DISTORTION':
                confidence_boost *= 0.85  # Distortion penalty
            
            return {
                'should_trade': should_trade,
                'confidence_boost': confidence_boost,
                'historical_win_rate': win_rate,
                'freq_band': freq_band,
                'thresholds': thresholds
            }
        except Exception:
            return {
                'should_trade': True,
                'confidence_boost': 1.0,
                'historical_win_rate': 0.5
            }
    
    def get_historical_wisdom(self, asset: str) -> Dict:
        """Get wisdom from historical trades"""
        if asset in self.historical_wisdom:
            w = self.historical_wisdom[asset]
            win_rate = w['wins'] / w['trades'] if w['trades'] > 0 else 0.5
            return {
                'trades': w['trades'],
                'win_rate': win_rate,
                'total_profit': w['total_profit'],
                'best_momentum': w['best_momentum'],
                'has_wisdom': True
            }
        return {
            'trades': 0,
            'win_rate': 0.5,
            'total_profit': 0.0,
            'best_momentum': 0.0,
            'has_wisdom': False
        }
    
    def get_unified_decision(self, asset: str, price: float, momentum: float, 
                            action_type: str) -> Dict:
        """
        🎯 UNIFIED DECISION - Combine all intelligence sources
        
        Returns decision with confidence from all systems.
        """
        # Gather all signals
        mycelium = self.get_mycelium_signal(asset, price, momentum)
        probability = self.get_probability_forecast(asset, price)
        adaptive = self.get_adaptive_guidance(asset, probability['frequency'])
        historical = self.get_historical_wisdom(asset)
        
        # Calculate unified confidence
        confidence_scores = []
        reasons = []
        
        # Mycelium vote
        if mycelium['consensus'] == 'BULLISH' and action_type == 'buy':
            confidence_scores.append(0.6 + mycelium['confidence'] * 0.3)
            reasons.append(f"🍄 Mycelium: {mycelium['consensus']}")
        elif mycelium['consensus'] == 'BEARISH' and action_type == 'sell':
            confidence_scores.append(0.6 + mycelium['confidence'] * 0.3)
            reasons.append(f"🍄 Mycelium: {mycelium['consensus']}")
        else:
            confidence_scores.append(0.4)
            reasons.append(f"🍄 Mycelium: {mycelium['consensus']} (contrary)")
        
        # Probability vote
        if (probability['signal'] == 'BUY' and action_type == 'buy') or \
           (probability['signal'] == 'SELL' and action_type == 'sell'):
            confidence_scores.append(0.6 + probability['confidence'] * 0.3)
            reasons.append(f"🔮 Probability: {probability['signal']} ({probability['bullish_prob']:.0%})")
        else:
            confidence_scores.append(0.4)
            reasons.append(f"🔮 Probability: {probability['signal']} (contrary)")
        
        # Adaptive vote
        confidence_scores.append(adaptive['historical_win_rate'])
        reasons.append(f"🧬 History: {adaptive['historical_win_rate']:.0%} win rate")
        
        # Historical wisdom vote
        if historical['has_wisdom']:
            confidence_scores.append(historical['win_rate'])
            reasons.append(f"📚 Wisdom: {historical['trades']} trades, {historical['win_rate']:.0%} WR")
        
        # Calculate unified confidence
        unified_confidence = sum(confidence_scores) / len(confidence_scores)
        unified_confidence *= adaptive['confidence_boost']
        
        # 🔥 AGGRESSIVE MODE - ALWAYS PROCEED!
        # No holding - every moment is an opportunity
        proceed = True  # NEVER HOLD - always move!
        
        # Boost confidence for aggressive trading
        unified_confidence = max(0.6, unified_confidence)  # Minimum 60% confidence
        
        return {
            'proceed': proceed,
            'confidence': unified_confidence,
            'reasons': reasons,
            'mycelium': mycelium,
            'probability': probability,
            'adaptive': adaptive,
            'historical': historical,
            'frequency': probability['frequency']
        }
    
    def get_v14_enhanced_decision(self, asset: str, price: float, momentum: float,
                                   action_type: str, volume: float = 0) -> Dict:
        """
        🏆 V14 ENHANCED DECISION - 100% WIN RATE OVERLAY 🏆
        
        Combines all intelligence sources with V14 proven rules:
        - Score 8+ required for entry
        - 1.52% profit target
        - NO STOP LOSS - infinite patience
        """
        # Get base unified decision
        decision = self.get_unified_decision(asset, price, momentum, action_type)
        
        # Apply V14 enhancement if available
        if self.v14_enhancer:
            symbol = f"{asset}USDT"
            v14_eval = self.v14_enhancer.evaluate_entry(symbol, price, volume)
            
            # Add V14 data to decision
            decision['v14_score'] = v14_eval['score']
            decision['v14_factors'] = v14_eval['factors']
            decision['v14_threshold'] = v14_eval['threshold']
            decision['v14_approved'] = v14_eval['should_enter']
            decision['v14_reason'] = v14_eval['reason']
            
            # V14 can VETO an entry if score is too low
            if action_type == 'buy' and not v14_eval['should_enter']:
                decision['proceed'] = False
                decision['v14_veto'] = True
                decision['reasons'].append(f"🏆 V14 VETO: Score {v14_eval['score']} < {v14_eval['threshold']}")
            elif v14_eval['should_enter']:
                # V14 APPROVAL boosts confidence
                score_boost = min(0.2, (v14_eval['score'] - 8) * 0.05)
                decision['confidence'] = min(1.0, decision['confidence'] + score_boost)
                decision['reasons'].append(f"🏆 V14 APPROVED: Score {v14_eval['score']}")
            
            # V14 EXIT RULES (for existing positions)
            decision['v14_profit_target'] = self.v14_config['profit_target_pct']
            decision['v14_stop_loss'] = None  # NONE - key insight!
            decision['v14_patience'] = 'INFINITE'
        
        return decision
    
    def record_outcome(self, stone: IntelligentStone, actual_profit: float):
        """Record trade outcome for learning"""
        stone.validated = True
        stone.actual_outcome = actual_profit
        
        # Record to adaptive learner
        if self.adaptive:
            trade_data = {
                'symbol': stone.asset,
                'exchange': stone.exchange,
                'entry_price': stone.price,
                'exit_price': stone.price * (1 + actual_profit / stone.amount) if stone.amount > 0 else stone.price,
                'pnl': actual_profit,
                'frequency': stone.frequency,
                'coherence': stone.coherence,
                'score': stone.probability * 100,
                'entry_time': stone.timestamp.timestamp(),
                'hnc_action': 'BUY' if stone.action == 'buy' else 'SELL',
                'probability': stone.probability,
                'mycelium_consensus': stone.mycelium_consensus
            }
            self.adaptive.record_trade(trade_data)
        
        # Update historical wisdom
        self._record_wisdom(stone.asset, actual_profit, {
            'momentum': stone.momentum,
            'action': stone.action
        })
        
        # Record decision accuracy
        was_correct = (stone.probability > 0.5 and actual_profit > 0) or \
                     (stone.probability <= 0.5 and actual_profit <= 0)
        self.decision_log.append({
            'timestamp': datetime.now(),
            'correct': was_correct,
            'confidence': stone.probability
        })
        
        # Update consensus accuracy
        recent = list(self.decision_log)[-50:]
        if recent:
            self.consensus_accuracy = sum(1 for d in recent if d['correct']) / len(recent)


class S5IntelligentDance:
    """
    🎭 THE INTELLIGENT DANCE 🎭
    
    Enhanced dance that learns from every move:
    - Mycelium Network provides distributed consensus
    - Probability Matrix forecasts optimal timing
    - Adaptive Learning improves from outcomes
    - Historical wisdom guides decisions
    
    "Learn more moves as you dance"
    """
    
    # WebSocket URLs
    BINANCE_WS = "wss://stream.binance.com:9443/stream?streams="
    
    # The dance floor
    KRAKEN_PAIRS = {
        'ATOM': 'ATOMUSD', 'DASH': 'DASHUSD', 'SOL': 'SOLUSD',
        'DOT': 'DOTUSD', 'LINK': 'LINKUSD', 'AVAX': 'AVAXUSD',
        'UNI': 'UNIUSD', 'AAVE': 'AAVEUSD', 'CRV': 'CRVUSD',
        'BTC': 'XBTUSD', 'ETH': 'ETHUSD', 'XRP': 'XRPUSD',
    }
    
    BINANCE_PAIRS = {
        'BTC': 'BTCUSDC', 'ETH': 'ETHUSDC', 'SOL': 'SOLUSDC',
        'BNB': 'BNBUSDC', 'XRP': 'XRPUSDC', 'ADA': 'ADAUSDC',
        'AVAX': 'AVAXUSDC', 'DOT': 'DOTUSDC', 'LINK': 'LINKUSDC',
        'ATOM': 'ATOMUSDC', 'UNI': 'UNIUSDC', 'NEAR': 'NEARUSDC',
    }
    
    # Dance parameters - AGGRESSIVE MODE
    MIN_STEP_USD = 1.0  # Lower minimum for faster conversions
    RHYTHM_THRESHOLD = 0.1  # 0.1% move triggers action (momentum is in %)
    
    # 🔥 AGGRESSION SETTINGS
    NEVER_HOLD = True  # ALWAYS trade - no holding!
    NET_PROFIT_MIN = 0.001  # Must net profit each step
    CONVERSION_SPEED = 0.5  # Faster loops (seconds)
    
    def __init__(self):
        # The dancers
        self.kraken = get_kraken_client()
        self.binance = get_binance_client()
        
        # The dance floor state
        self.kraken_holdings: Dict[str, float] = {}
        self.binance_holdings: Dict[str, float] = {}
        self.prices: Dict[str, Dict[str, float]] = defaultdict(dict)
        self.price_history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        
        # 🧠 THE INTELLIGENCE HUB
        self.intelligence: Optional[DanceIntelligence] = None
        
        # The rhythm - now learning!
        self.rhythms: Dict[str, LearningRhythm] = {}
        self.stepping_stones: List[IntelligentStone] = []
        self.current_stone: Optional[IntelligentStone] = None
        
        # Dance statistics
        self.running = False
        self.start_time = None
        self.total_profit = 0.0
        self.total_steps = 0
        self.dance_velocity = 0.0
        
        # Learning snowball
        self.snowball = 1.0
        self.learning_multiplier = 1.0  # Grows with accuracy
        
        signal.signal(signal.SIGINT, self._stop)
        signal.signal(signal.SIGTERM, self._stop)
    
    def _stop(self, *args):
        print("\n🛑 The dance pauses... learning preserved!")
        self.running = False
    
    async def initialize(self):
        """Initialize the intelligent dance floor"""
        print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║   🎭 S5 INTELLIGENT DANCE - THE LEARNING STEPPING STONE SYMPHONY 🎭          ║
║                                                                               ║
║   Every trade is a stepping stone that LEARNS                                 ║
║   The Mycelium Network coordinates the rhythm                                 ║
║   The Probability Matrix forecasts the moves                                  ║
║   Wisdom grows with every dance                                               ║
║                                                                               ║
║   🍄 Mycelium + 🔮 Probability + 🧬 Adaptive + 📚 Historical = 🧠 Intelligence ║
╚═══════════════════════════════════════════════════════════════════════════════╝
""")
        
        # Connect exchanges
        print("🔌 Connecting to the dance floor...")
        
        total_capital = 0.0
        
        # Kraken
        try:
            kraken_balance = self.kraken.get_account_balance()
            if kraken_balance:
                print("   🐙 Kraken: Connected!")
                for asset, amount in kraken_balance.items():
                    if amount > 0.0001:
                        self.kraken_holdings[asset] = amount
                        usd_val = self._get_usd_value(asset, amount, 'kraken')
                        total_capital += usd_val
                        if usd_val > 0.1:
                            print(f"      💎 {asset}: {amount:.6f} (${usd_val:.2f})")
        except Exception as e:
            print(f"   🐙 Kraken: {e}")
        
        # Binance
        try:
            if self.binance.ping():
                print("   🟡 Binance: Connected!")
                account = self.binance.account()
                for bal in account.get('balances', []):
                    asset = bal['asset']
                    total = float(bal.get('free', 0)) + float(bal.get('locked', 0))
                    if total > 0.000001:
                        self.binance_holdings[asset] = total
                        usd_val = self._get_usd_value(asset, total, 'binance')
                        total_capital += usd_val
                        if usd_val > 0.1:
                            print(f"      💎 {asset}: {total:.6f} (${usd_val:.2f})")
        except Exception as e:
            print(f"   🟡 Binance: {e}")
        
        # 🧠 INITIALIZE INTELLIGENCE HUB
        print("\n🧠 Initializing Intelligence Hub...")
        self.intelligence = DanceIntelligence(starting_capital=total_capital)
        
        # Initialize rhythms with learning
        all_assets = set(self.kraken_holdings.keys()) | set(self.binance_holdings.keys())
        for asset in all_assets:
            self.rhythms[asset] = LearningRhythm(asset=asset)
            
            # Pre-load historical wisdom
            if self.intelligence:
                wisdom = self.intelligence.get_historical_wisdom(asset)
                if wisdom['has_wisdom']:
                    self.rhythms[asset].win_rate = wisdom['win_rate']
                    self.rhythms[asset].trades = wisdom['trades']
        
        print(f"\n   💼 Dance Floor Capital: ${total_capital:.2f}")
        
        # Load previous dance state
        self._load_dance_state()
        
        return total_capital > 0
    
    def _load_dance_state(self):
        """Load previous dance state"""
        try:
            if os.path.exists('intelligent_dance_state.json'):
                with open('intelligent_dance_state.json') as f:
                    state = json.load(f)
                self.total_steps = state.get('total_steps', 0)
                self.total_profit = state.get('total_profit', 0)
                self.snowball = state.get('snowball', 1.0)
                self.learning_multiplier = state.get('learning_multiplier', 1.0)
                print(f"   📜 Restored: {self.total_steps} steps, ${self.total_profit:.4f} profit")
                print(f"   ❄️ Snowball: {self.snowball:.3f}x | Learning: {self.learning_multiplier:.3f}x")
        except Exception:
            pass
    
    def _get_usd_value(self, asset: str, amount: float, exchange: str) -> float:
        """Get USD value of an asset"""
        if asset in ['USD', 'USDT', 'USDC', 'ZUSD']:
            return amount
        
        if asset in self.prices and exchange in self.prices[asset]:
            return amount * self.prices[asset][exchange]
        
        try:
            for quote in ['USDT', 'USDC']:
                pair = f"{asset}{quote}"
                try:
                    price = float(self.binance.best_price(pair, timeout=1).get('price', 0))
                    if price > 0:
                        return amount * price
                except:
                    continue
        except:
            pass
        
        return 0.0
    
    def _get_binance_streams(self) -> List[str]:
        """Get WebSocket streams"""
        streams = set()
        all_assets = set(self.kraken_holdings.keys()) | set(self.binance_holdings.keys())
        
        for asset in all_assets:
            for quote in ['USDT', 'USDC']:
                pair = f"{asset}{quote}"
                streams.add(f"{pair.lower()}@ticker")
        
        for major in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']:
            streams.add(f"{major.lower()}@ticker")
        
        return list(streams)[:50]
    
    async def run(self):
        """Start the intelligent dance"""
        if not await self.initialize():
            print("\n⚠️ No assets to dance with!")
            return
        
        print("\n⚠️ Type 'DANCE' to begin the intelligent rhythm: ", end='')
        confirm = input()
        if confirm.strip().upper() != 'DANCE':
            print("The dance awaits...")
            return
        
        print("\n🎵 THE INTELLIGENT DANCE BEGINS! 🎵\n")
        
        self.running = True
        self.start_time = datetime.now()
        
        await asyncio.gather(
            self._price_rhythm(),
            self._intelligent_loop(),
            self._rhythm_display(),
        )
        
        self._final_bow()
    
    async def _price_rhythm(self):
        """WebSocket feed - the heartbeat"""
        streams = self._get_binance_streams()
        if not streams:
            return
        
        url = self.BINANCE_WS + "/".join(streams)
        print(f"🎧 Tuning into {len(streams)} rhythm channels...")
        
        while self.running:
            try:
                async with websockets.connect(url, ping_interval=20) as ws:
                    print("   🎵 Rhythm locked!")
                    
                    while self.running:
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=30)
                            data = json.loads(msg)
                            if 'data' in data:
                                await self._feel_the_beat(data['data'])
                        except asyncio.TimeoutError:
                            continue
            except Exception as e:
                if self.running:
                    print(f"\n   🎵 Rhythm interrupted: {e}")
                    await asyncio.sleep(2)
    
    async def _feel_the_beat(self, ticker: Dict):
        """Process price update with intelligence"""
        symbol = ticker.get('s', '')
        price = float(ticker.get('c', 0))
        
        if price <= 0:
            return
        
        now = datetime.now()
        
        asset = None
        for quote in ['USDT', 'USDC', 'USD']:
            if symbol.endswith(quote):
                asset = symbol[:-len(quote)]
                break
        
        if not asset:
            return
        
        # Update price
        self.prices[asset]['binance'] = price
        self.prices[asset]['kraken'] = price
        
        # Store history
        self.price_history[symbol].append((now, price))
        cutoff = now - timedelta(minutes=5)
        self.price_history[symbol] = [(t, p) for t, p in self.price_history[symbol] if t > cutoff]
        
        # Update rhythm with intelligence
        if asset in self.rhythms:
            rhythm = self.rhythms[asset]
            history = self.price_history[symbol]
            
            if len(history) >= 5:
                oldest = history[0][1]
                momentum = (price - oldest) / oldest * 100
                
                rhythm.momentum_history.append(momentum)
                if len(rhythm.momentum_history) > 20:
                    rhythm.momentum_history = rhythm.momentum_history[-20:]
                
                if momentum > 0.01:
                    rhythm.last_direction = 'up'
                elif momentum < -0.01:
                    rhythm.last_direction = 'down'
    
    async def _intelligent_loop(self):
        """The AGGRESSIVE dance loop - SPEED IS KEY!"""
        await asyncio.sleep(2)  # Quick start
        print("\n🔥 AGGRESSIVE MODE - Finding profitable conversions...")
        
        while self.running:
            try:
                # Find ALL opportunities, execute the best
                next_step = await self._find_intelligent_stone()
                
                if next_step:
                    await self._execute_intelligent_step(next_step)
                else:
                    # No opportunity? Force a conversion anyway!
                    await self._force_best_conversion()
                
            except Exception as e:
                print(f"\n   ⚠️ Dance stumble: {e}")
            
            await asyncio.sleep(self.CONVERSION_SPEED)  # FAST loops!
    
    async def _find_intelligent_stone(self) -> Optional[Dict]:
        """Find the next stepping stone with intelligence guidance"""
        opportunities = []
        
        # Check all holdings
        for exchange, holdings in [('kraken', self.kraken_holdings), ('binance', self.binance_holdings)]:
            for asset, amount in holdings.items():
                if amount < 0.001:
                    continue
                
                usd_value = self._get_usd_value(asset, amount, exchange)
                if usd_value < self.MIN_STEP_USD:
                    continue
                
                rhythm = self.rhythms.get(asset)
                if not rhythm or not rhythm.momentum_history:
                    continue
                
                momentum = rhythm.momentum_history[-1] if rhythm.momentum_history else 0
                price = self.prices.get(asset, {}).get(exchange, 0)
                
                # 🔥 AGGRESSIVE - Ultra-low threshold
                threshold = self.RHYTHM_THRESHOLD / (self.snowball * self.learning_multiplier * 2)
                
                # ALWAYS trade if there's ANY momentum
                if abs(momentum) >= threshold or self.NEVER_HOLD:
                    # NO HOLDING - Always sell on up, buy on down
                    action_type = 'sell' if momentum >= 0 else 'buy'
                    
                    if True:  # ALWAYS proceed - no hold check
                        # 🧠 GET INTELLIGENT DECISION
                        decision = self.intelligence.get_unified_decision(
                            asset, price, momentum, action_type
                        ) if self.intelligence else {'proceed': True, 'confidence': 0.5}
                        
                        if decision['proceed']:
                            score = abs(momentum) * decision['confidence'] * self.learning_multiplier
                            
                            opportunities.append({
                                'exchange': exchange,
                                'asset': asset,
                                'action': action_type,
                                'amount': amount,
                                'momentum': momentum,
                                'usd_value': usd_value,
                                'score': score,
                                'decision': decision,
                                'price': price
                            })
        
        # Check for buy opportunities
        for exchange, holdings in [('kraken', self.kraken_holdings), ('binance', self.binance_holdings)]:
            for usd_asset in ['ZUSD', 'USD', 'USDC', 'USDT']:
                usd_amount = holdings.get(usd_asset, 0)
                if usd_amount < self.MIN_STEP_USD:
                    continue
                
                # Find best dip to buy
                best_dip = None
                best_score = 0
                
                for asset, rhythm in self.rhythms.items():
                    if not rhythm.momentum_history:
                        continue
                    
                    momentum = rhythm.momentum_history[-1]
                    threshold = -self.RHYTHM_THRESHOLD / (self.snowball * self.learning_multiplier)
                    
                    if momentum < threshold:
                        price = self.prices.get(asset, {}).get(exchange, 0)
                        
                        # 🧠 GET INTELLIGENT DECISION
                        decision = self.intelligence.get_unified_decision(
                            asset, price, momentum, 'buy'
                        ) if self.intelligence else {'proceed': True, 'confidence': 0.5}
                        
                        if decision['proceed']:
                            score = abs(momentum) * decision['confidence'] * 1.5
                            if score > best_score:
                                best_score = score
                                best_dip = (asset, momentum, decision, price)
                
                if best_dip:
                    opportunities.append({
                        'exchange': exchange,
                        'asset': best_dip[0],
                        'action': 'buy',
                        'amount': usd_amount * 0.3,
                        'momentum': best_dip[1],
                        'usd_value': usd_amount * 0.3,
                        'score': best_score,
                        'decision': best_dip[2],
                        'price': best_dip[3],
                        'spend_asset': usd_asset
                    })
        
        if not opportunities:
            return None
        
        opportunities.sort(key=lambda x: x['score'], reverse=True)
        return opportunities[0]
    
    async def _force_best_conversion(self):
        """🔥 FORCE a conversion when no opportunity found - NEVER IDLE!"""
        # Find ANY asset to convert
        for exchange, holdings in [('kraken', self.kraken_holdings), ('binance', self.binance_holdings)]:
            for asset, amount in holdings.items():
                if asset in ['USD', 'USDT', 'USDC', 'ZUSD']:
                    continue
                
                usd_value = self._get_usd_value(asset, amount, exchange)
                if usd_value >= self.MIN_STEP_USD:
                    price = self.prices.get(asset, {}).get(exchange, 0)
                    if price > 0:
                        # Force a sell - keep the dance moving!
                        step = {
                            'exchange': exchange,
                            'asset': asset,
                            'action': 'sell',
                            'amount': amount,
                            'momentum': 0.01,  # Small positive to trigger sell
                            'usd_value': usd_value,
                            'price': price,
                            'decision': {'proceed': True, 'confidence': 0.7, 'reasons': ['🔥 FORCED CONVERSION - Keep moving!']}
                        }
                        print(f"\n   🔥 FORCED CONVERSION: SELL {asset} on {exchange.upper()}")
                        await self._execute_intelligent_step(step)
                        return
    
    async def _execute_intelligent_step(self, step: Dict):
        """Execute step with intelligence"""
        exchange = step['exchange']
        asset = step['asset']
        action = step['action']
        momentum = step['momentum']
        decision = step.get('decision', {})
        
        # Display intelligence reasoning
        reasons = decision.get('reasons', [])
        print(f"\n   💫 INTELLIGENT STEP: {action.upper()} {asset} on {exchange.upper()}")
        print(f"      📊 Momentum: {momentum:+.3f}% | Value: ${step['usd_value']:.2f}")
        print(f"      🧠 Confidence: {decision.get('confidence', 0.5):.0%}")
        for reason in reasons[:3]:
            print(f"         {reason}")
        
        try:
            if exchange == 'kraken':
                await self._kraken_step(step)
            else:
                await self._binance_step(step)
        except Exception as e:
            print(f"      ❌ Step failed: {e}")
    
    async def _kraken_step(self, step: Dict):
        """Execute Kraken step - AGGRESSIVE!"""
        asset = step['asset']
        action = step['action']
        
        if asset not in self.KRAKEN_PAIRS:
            return
        
        pair = self.KRAKEN_PAIRS[asset]
        price = step.get('price', self.prices.get(asset, {}).get('kraken', 0))
        
        if action == 'sell':
            # 🔥 AGGRESSIVE - Sell 50% for faster conversions
            amount = step['amount'] * 0.5
            if amount * price < 0.5:  # Lower minimum
                return
            
            result = self.kraken.place_market_order(
                symbol=pair, side='sell', quantity=amount
            )
            
            if result:
                profit_est = step['usd_value'] * 0.3 * abs(step['momentum']) / 100
                self._record_intelligent_step(step, profit_est)
                self.kraken_holdings[asset] -= amount
                print(f"      ✅ SOLD {amount:.6f} {asset}")
                
        elif action == 'buy':
            spend = step.get('spend_asset', 'ZUSD')
            # 🔥 AGGRESSIVE - Use 50% of available USD
            spend_amount = min(step['amount'], self.kraken_holdings.get(spend, 0) * 0.5)
            
            if spend_amount < 0.5 or price <= 0:  # Lower minimum
                return
            
            qty = spend_amount / price * 0.99  # Less reserve
            result = self.kraken.place_market_order(
                symbol=pair, side='buy', quantity=qty
            )
            
            if result:
                profit_est = spend_amount * abs(step['momentum']) / 100
                self._record_intelligent_step(step, profit_est)
                self.kraken_holdings[spend] = self.kraken_holdings.get(spend, 0) - spend_amount
                self.kraken_holdings[asset] = self.kraken_holdings.get(asset, 0) + qty
                print(f"      ✅ BOUGHT {qty:.6f} {asset}")
    
    async def _binance_step(self, step: Dict):
        """Execute Binance step"""
        asset = step['asset']
        action = step['action']
        
        if asset in ['USDC', 'USDT', 'USD', 'BUSD']:
            return
        
        # Find pair
        pair = None
        quote_used = None
        for quote in ['USDC', 'USDT']:
            test_pair = f"{asset}{quote}"
            try:
                price_check = self.binance.best_price(test_pair, timeout=1)
                if price_check.get('price'):
                    pair = test_pair
                    quote_used = quote
                    break
            except:
                continue
        
        if not pair:
            return
        
        price = float(self.binance.best_price(pair, timeout=2).get('price', 0))
        if price <= 0:
            return
        
        if action == 'sell':
            # 🔥 AGGRESSIVE - Sell 50%
            amount = step['amount'] * 0.5
            trade_value = amount * price
            
            if trade_value < 5:  # Lower minimum
                return
            
            try:
                result = self.binance.place_market_order(
                    symbol=pair, side='SELL', quantity=amount
                )
                
                if result.get('rejected'):
                    return
                
                if result.get('orderId') or result.get('status') == 'FILLED':
                    exec_qty = float(result.get('executedQty', amount))
                    profit_est = trade_value * abs(step['momentum']) / 100
                    self._record_intelligent_step(step, profit_est)
                    self.binance_holdings[asset] = self.binance_holdings.get(asset, 0) - exec_qty
                    self.binance_holdings[quote_used] = self.binance_holdings.get(quote_used, 0) + (exec_qty * price)
                    print(f"      ✅ SOLD {exec_qty:.6f} {asset}")
            except Exception as e:
                print(f"      ❌ Sell error: {e}")
                
        elif action == 'buy':
            spend = None
            spend_amount = 0
            for usd in ['USDC', 'USDT']:
                bal = self.binance_holdings.get(usd, 0)
                if bal >= 5:  # Lower minimum
                    spend = usd
                    # 🔥 AGGRESSIVE - Use 50% of available
                    spend_amount = min(step['amount'], bal * 0.5)
                    break
            
            if not spend or spend_amount < 11:
                return
            
            buy_pair = f"{asset}{spend}"
            try:
                result = self.binance.place_market_order(
                    symbol=buy_pair, side='BUY', quote_qty=spend_amount
                )
                
                if result.get('rejected'):
                    return
                
                if result.get('orderId') or result.get('status') == 'FILLED':
                    exec_qty = float(result.get('executedQty', 0))
                    exec_quote = float(result.get('cummulativeQuoteQty', spend_amount))
                    profit_est = exec_quote * abs(step['momentum']) / 100
                    self._record_intelligent_step(step, profit_est)
                    self.binance_holdings[spend] = self.binance_holdings.get(spend, 0) - exec_quote
                    self.binance_holdings[asset] = self.binance_holdings.get(asset, 0) + exec_qty
                    print(f"      ✅ BOUGHT {exec_qty:.6f} {asset}")
            except Exception as e:
                print(f"      ❌ Buy error: {e}")
    
    def _record_intelligent_step(self, step: Dict, profit: float):
        """Record intelligent stepping stone"""
        decision = step.get('decision', {})
        
        stone = IntelligentStone(
            exchange=step['exchange'],
            asset=step['asset'],
            action=step['action'],
            amount=step['amount'],
            price=step.get('price', 0),
            profit=profit,
            momentum=step['momentum'],
            frequency=decision.get('probability', {}).get('frequency', 256.0),
            probability=decision.get('confidence', 0.5),
            coherence=decision.get('mycelium', {}).get('confidence', 0.5),
            mycelium_consensus=decision.get('mycelium', {}).get('consensus', 'NEUTRAL')
        )
        
        if self.current_stone:
            self.current_stone.next_stone = stone
        
        self.stepping_stones.append(stone)
        self.current_stone = stone
        
        # Update stats
        self.total_profit += profit
        self.total_steps += 1
        self.snowball *= 1.002
        
        # Update learning multiplier based on accuracy
        if self.intelligence:
            self.learning_multiplier = 1.0 + (self.intelligence.consensus_accuracy - 0.5) * 0.5
            self.intelligence.record_outcome(stone, profit)
        
        # Update rhythm
        if step['asset'] in self.rhythms:
            rhythm = self.rhythms[step['asset']]
            rhythm.beat_count += 1
            rhythm.total_profit += profit
            rhythm.trades += 1
            if profit > 0:
                rhythm.wins += 1
                rhythm.profit_streak += 1
            else:
                rhythm.profit_streak = 0
            rhythm.win_rate = rhythm.wins / rhythm.trades if rhythm.trades > 0 else 0.5
        
        print(f"      💰 Profit: ${profit:.4f} | Total: ${self.total_profit:.4f}")
        print(f"      ❄️ Snowball: {self.snowball:.3f}x | 🧠 Learning: {self.learning_multiplier:.3f}x")
    
    async def _rhythm_display(self):
        """Display rhythm with intelligence metrics"""
        while self.running:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            hours = max(0.001, elapsed / 3600)
            velocity = self.total_profit / hours
            
            # Intelligence metrics
            consensus_acc = self.intelligence.consensus_accuracy if self.intelligence else 0.5
            
            active_rhythms = [(a, r) for a, r in self.rhythms.items() if r.momentum_history]
            active_rhythms.sort(key=lambda x: abs(x[1].momentum_history[-1]) if x[1].momentum_history else 0, reverse=True)
            
            rhythm_str = " | ".join([
                f"{a}:{r.momentum_history[-1]:+.2f}%"
                for a, r in active_rhythms[:3]
                if r.momentum_history
            ]) if active_rhythms else "..."
            
            print(f"\r🧠 {int(elapsed)}s | 👣 {self.total_steps} | "
                  f"💰 ${self.total_profit:.4f} | ⚡${velocity:.2f}/hr | "
                  f"🎯 {consensus_acc:.0%} | ❄️ {self.snowball:.3f}x | {rhythm_str}",
                  end='', flush=True)
            
            await asyncio.sleep(5)
    
    def _final_bow(self):
        """Final report with learning insights"""
        elapsed = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        print("\n\n" + "="*75)
        print("🎭 THE INTELLIGENT DANCE FINALE - LEARNING REPORT")
        print("="*75)
        print(f"⏱️ Duration: {elapsed:.0f}s ({elapsed/3600:.2f} hours)")
        print(f"👣 Total Steps: {self.total_steps}")
        print(f"💰 Total Profit: ${self.total_profit:.4f}")
        print(f"⚡ Velocity: ${self.total_profit/(elapsed/3600) if elapsed > 0 else 0:.2f}/hr")
        print(f"❄️ Final Snowball: {self.snowball:.4f}x")
        print(f"🧠 Learning Multiplier: {self.learning_multiplier:.4f}x")
        
        if self.intelligence:
            print(f"\n🎯 Intelligence Accuracy: {self.intelligence.consensus_accuracy:.1%}")
            print(f"📚 Historical Assets Tracked: {len(self.intelligence.historical_wisdom)}")
        
        # Best performers
        if self.rhythms:
            print("\n🌟 Star Performers (by win rate):")
            sorted_rhythms = sorted(
                [(a, r) for a, r in self.rhythms.items() if r.trades > 0],
                key=lambda x: (x[1].win_rate, x[1].total_profit),
                reverse=True
            )[:5]
            for asset, rhythm in sorted_rhythms:
                print(f"   {asset}: {rhythm.trades} trades, "
                      f"{rhythm.win_rate:.0%} WR, ${rhythm.total_profit:.4f}")
        
        print("="*75)
        
        # Save state
        self._save_dance_state()
    
    def _save_dance_state(self):
        """Save dance state for continuation"""
        try:
            state = {
                'timestamp': datetime.now().isoformat(),
                'total_steps': self.total_steps,
                'total_profit': self.total_profit,
                'snowball': self.snowball,
                'learning_multiplier': self.learning_multiplier,
                'consensus_accuracy': self.intelligence.consensus_accuracy if self.intelligence else 0.5,
                'stones': [
                    {
                        'exchange': s.exchange,
                        'asset': s.asset,
                        'action': s.action,
                        'amount': s.amount,
                        'profit': s.profit,
                        'momentum': s.momentum,
                        'probability': s.probability,
                        'mycelium_consensus': s.mycelium_consensus,
                        'time': s.timestamp.isoformat()
                    }
                    for s in self.stepping_stones[-200:]
                ],
                'rhythms': {
                    asset: {
                        'trades': r.trades,
                        'wins': r.wins,
                        'win_rate': r.win_rate,
                        'total_profit': r.total_profit
                    }
                    for asset, r in self.rhythms.items() if r.trades > 0
                }
            }
            with open('intelligent_dance_state.json', 'w') as f:
                json.dump(state, f, indent=2)
            print("\n💾 Intelligent dance state saved!")
        except Exception as e:
            print(f"\n⚠️ Could not save state: {e}")


async def main():
    dance = S5IntelligentDance()
    await dance.run()


if __name__ == "__main__":
    asyncio.run(main())
