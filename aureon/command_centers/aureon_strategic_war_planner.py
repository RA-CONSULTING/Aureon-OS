#!/usr/bin/env python3
"""
AUREON STRATEGIC WAR PLANNER - THE MIND
=============================================================================

"The general who wins the battle makes many calculations in his temple
before the battle is fought." — Sun Tzu, Art of War

THE CONCEPT:
    This is the system's MIND. It plays adversarial chess with itself.
    One side is REALIZED PROFIT (us). The other is LOSS OF REVENUE (the enemy).
    Every move we make, we simulate how the enemy will counter.
    Every move the enemy might make, we plan our response.

THE 2-STEPS-BACK, 1-STEP-FORWARD PRINCIPLE:
    We use TWO steps from the past to predict ONE step into the future,
    while constantly watching everything the enemy is doing.

    Step Back 2:  What happened 2 cycles ago? (Pattern seed)
    Step Back 1:  What happened 1 cycle ago? (Pattern confirmation)
    Step Forward:  What will happen next? (Predicted from the 2 lookbacks)

    The past doesn't repeat — but it RHYMES. And we listen for the rhyme.

ADVERSARIAL CHESS ENGINE:
    Board  = Current market state (prices, momentum, sentiment, positions)
    White  = Realized Profit (our side — trying to WIN every trade)
    Black  = Revenue Loss (fees, slippage, bad timing, stop hunts, whales)

    Each cycle:
    1. White proposes a MOVE (trade entry/exit/hold)
    2. Black simulates the COUNTER-MOVE (what could go wrong)
    3. White evaluates: Can we survive the counter? Is the risk worth it?
    4. If White still wins after Black's best counter → EXECUTE
    5. If Black wins → HOLD, RETREAT, or find a different angle of ATTACK

SYSTEMS CONNECTED:
    - Quantum Mirror Scanner   → Reality branch analysis (what timelines exist)
    - Quantum Telescope        → Geometric probability (sacred geometry lens)
    - Harmonic Alphabet        → Frequency-encoded communication
    - Miner Brain              → Critical thinking & speculation
    - War Strategy             → Quick-kill probability
    - Guerrilla Warfare Engine → Tactical modes & flying columns
    - HNC Probability Matrix   → Temporal frequency analysis
    - Orca Predator Detection  → Counter-intelligence (who's hunting US?)
    - Autonomy Hub             → The Big Wheel (data → prediction → decision)

WARFARE DOCTRINE (Sun Tzu + IRA):
    1. "Know the enemy, know yourself" → Orca predator + self-analysis
    2. "Attack where they are weak"   → Find thin-spread markets
    3. "All warfare is deception"     → Don't chase obvious signals
    4. "Flying columns"               → Small, fast, lethal trades
    5. "Intelligence supremacy"       → Use EVERY data source available
    6. "Never fight the same way twice" → Rotate strategies
    7. "Patience is the warrior's friend" → Only attack high-probability setups

Gary Leckey & Claude | February 2026
"The mind that plans wins. The hand that acts follows. The wheel that turns learns."
=============================================================================
"""

import json
import os
import time
import math
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from collections import deque, defaultdict
from enum import Enum

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

PHI = 1.618033988749895       # Golden Ratio
SCHUMANN = 7.83               # Earth's heartbeat
QUEEN_MIN_COP = 1.0188        # Sacred 1.88% minimum profit

# Boyd's OODA Loop timing targets (milliseconds)
OODA_OBSERVE_MAX_MS = 50
OODA_ORIENT_MAX_MS = 100
OODA_DECIDE_MAX_MS = 50
OODA_ACT_MAX_MS = 200

# Lookback windows for 2-back-1-forward
LOOKBACK_STEPS = 2
FORECAST_STEPS = 1


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

class ChessSide(Enum):
    """The two sides of the war."""
    WHITE = "PROFIT"    # Us — Realized Profit
    BLACK = "LOSS"      # Enemy — Revenue Loss (fees, slippage, bad timing)


class TacticalStance(Enum):
    """Current warfare stance — dictates behavior."""
    AMBUSH = "ambush"               # Waiting for perfect setup
    FLYING_COLUMN = "flying_column" # Active hit-and-run
    SIEGE = "siege"                 # Patient hold
    RETREAT = "retreat"             # Defensive — protect capital
    FEIGNED_RETREAT = "feigned"     # Sun Tzu: lure enemy into trap
    BLITZ = "blitz"                 # All-in coordinated strike


class MoveType(Enum):
    """Possible chess moves."""
    ATTACK = "BUY"           # Enter a position
    DEFEND = "SELL"          # Exit to protect profit
    HOLD = "HOLD"            # Maintain position
    RETREAT = "RETREAT"      # Exit at loss (cut losses)
    AMBUSH = "AMBUSH_WAIT"   # Wait for better entry
    FEINT = "FEINT"          # Deceptive probe used to test market response


@dataclass
class BoardState:
    """The chessboard — current market state snapshot."""
    timestamp: float = field(default_factory=time.time)
    symbol: str = ""

    # Price data
    current_price: float = 0.0
    price_1_step_ago: float = 0.0   # Step Back 1
    price_2_steps_ago: float = 0.0  # Step Back 2

    # Momentum
    momentum_1m: float = 0.0
    momentum_5m: float = 0.0
    momentum_15m: float = 0.0

    # Volume
    volume: float = 0.0
    volume_ratio: float = 1.0  # vs average

    # Positions
    has_position: bool = False
    position_side: str = "none"   # long/short/none
    position_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0

    # Intelligence from connected systems
    quantum_mirror_coherence: float = 0.0
    quantum_telescope_alignment: float = 0.0
    harmonic_resonance: float = 0.0
    miner_brain_confidence: float = 0.0
    orca_threat_level: float = 0.0  # 0 = safe, 1 = under attack
    war_strategy_go: bool = False
    guerrilla_ambush_score: float = 0.0
    hnc_probability: float = 0.5
    hub_direction: str = "NEUTRAL"
    hub_confidence: float = 0.0

    # Derived
    fear_greed: int = 50
    volatility: float = 0.0


@dataclass
class ChessMove:
    """A proposed move on the board."""
    side: ChessSide
    move_type: MoveType
    symbol: str = ""
    confidence: float = 0.0       # 0-1, how sure we are
    expected_pnl: float = 0.0     # Expected profit/loss
    risk: float = 0.0             # Risk exposure 0-1
    reasoning: str = ""
    counter_moves: List[str] = field(default_factory=list)  # What enemy could do
    survival_probability: float = 0.0  # Can we survive the counter?
    source_systems: List[str] = field(default_factory=list)  # Which systems agree

    def net_score(self) -> float:
        """Net score: confidence * survival - risk."""
        return self.confidence * self.survival_probability - self.risk


@dataclass
class WarPlan:
    """The complete war plan for this cycle."""
    timestamp: float = field(default_factory=time.time)
    symbol: str = ""
    stance: TacticalStance = TacticalStance.AMBUSH

    # The proposed move
    white_move: Optional[ChessMove] = None      # Our best move
    black_counter: Optional[ChessMove] = None    # Enemy's best counter
    final_move: Optional[ChessMove] = None       # What we actually do

    # 2-back-1-forward prediction
    step_back_2: Dict = field(default_factory=dict)
    step_back_1: Dict = field(default_factory=dict)
    step_forward: Dict = field(default_factory=dict)

    # Board state
    board: Optional[BoardState] = None

    # Systems consulted
    systems_consulted: List[str] = field(default_factory=list)
    consensus_agreement: float = 0.0  # 0-1 how much systems agree

    def to_dict(self) -> Dict:
        result = {
            'timestamp': self.timestamp,
            'symbol': self.symbol,
            'stance': self.stance.value,
            'step_back_2': self.step_back_2,
            'step_back_1': self.step_back_1,
            'step_forward': self.step_forward,
            'systems_consulted': self.systems_consulted,
            'consensus_agreement': self.consensus_agreement,
        }
        if self.final_move:
            result['action'] = self.final_move.move_type.value
            result['confidence'] = self.final_move.confidence
            result['expected_pnl'] = self.final_move.expected_pnl
            result['reasoning'] = self.final_move.reasoning
            result['survival_probability'] = self.final_move.survival_probability
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# THE LOOKBACK ENGINE — "2 Steps Back, 1 Step Forward"
# ═══════════════════════════════════════════════════════════════════════════════

class LookbackEngine:
    """
    Uses 2 past states to predict 1 future state.

    The principle: Every market move rhymes with a prior pattern.
    By comparing step[-2] → step[-1], we extrapolate step[+1].

    This is NOT simple linear extrapolation. We look for:
    1. Direction change patterns (was accelerating? decelerating?)
    2. Volume confirmation (did volume support the move?)
    3. Momentum divergence (is momentum confirming or diverging?)
    4. Enemy behavior (was the move predatory — stop hunt, failed breakout?)
    """

    def __init__(self, max_history: int = 200):
        self._history: deque = deque(maxlen=max_history)
        self._pattern_memory: Dict[str, List[Dict]] = defaultdict(list)
        self._lock = threading.Lock()

    def record_state(self, state: BoardState):
        """Record a board state into history."""
        with self._lock:
            self._history.append(state)

    def predict_forward(self, symbol: str = "") -> Dict:
        """
        2 steps back → 1 step forward.

        Returns prediction dict with direction, magnitude, confidence.
        """
        with self._lock:
            states = [s for s in self._history if not symbol or s.symbol == symbol]

        if len(states) < 2:
            return {
                'direction': 'NEUTRAL',
                'magnitude': 0.0,
                'confidence': 0.0,
                'pattern': 'INSUFFICIENT_DATA',
                'reasoning': 'Need at least 2 historical states',
            }

        step_back_2 = states[-2]
        step_back_1 = states[-1]

        # --- Analyze the 2-step pattern ---

        # Price trajectory
        if step_back_2.current_price > 0 and step_back_1.current_price > 0:
            price_change_1 = (step_back_1.current_price - step_back_2.current_price) / step_back_2.current_price
        else:
            price_change_1 = 0.0

        # Momentum trajectory
        mom_accel = step_back_1.momentum_1m - step_back_2.momentum_1m

        # Volume trajectory
        vol_change = step_back_1.volume_ratio - step_back_2.volume_ratio

        # --- Pattern classification ---
        pattern = self._classify_pattern(price_change_1, mom_accel, vol_change,
                                         step_back_1, step_back_2)

        # --- Predict step forward ---
        pred = self._extrapolate(pattern, price_change_1, mom_accel, vol_change,
                                 step_back_1)

        # --- Check for enemy behavior (traps) ---
        trap_probability = self._detect_trap(step_back_2, step_back_1)
        if trap_probability > 0.5:
            pred['confidence'] *= (1.0 - trap_probability * 0.5)
            pred['trap_detected'] = True
            pred['trap_probability'] = trap_probability

        # Store the prediction for learning
        pred['step_back_2_price'] = step_back_2.current_price
        pred['step_back_1_price'] = step_back_1.current_price
        pred['price_change_observed'] = price_change_1

        return pred

    def _classify_pattern(self, price_change: float, mom_accel: float,
                          vol_change: float, s1: BoardState, s2: BoardState) -> str:
        """
        Classify the 2-step pattern into named patterns.

        Each pattern maps to a Sun Tzu / IRA tactical doctrine.
        """
        # 1. CHARGING BULL — price up, momentum accelerating, volume rising
        if price_change > 0.005 and mom_accel > 0 and vol_change > 0:
            return "CHARGING_BULL"  # "Attack when enemy retreats" — pursue

        # 2. EXHAUSTED BULL — price up but momentum decelerating
        if price_change > 0.002 and mom_accel < -0.1:
            return "EXHAUSTED_BULL"  # "Culminating point" — Clausewitz

        # 3. BEAR AMBUSH — price dropping, momentum accelerating down
        if price_change < -0.005 and mom_accel < 0:
            return "BEAR_AMBUSH"  # "Attack where they are weak"

        # 4. BEAR EXHAUSTION — price down but selling slowing
        if price_change < -0.002 and mom_accel > 0.1:
            return "BEAR_EXHAUSTION"  # "After the storm, buy the rainbow"

        # 5. CONSOLIDATION — small moves, low momentum
        if abs(price_change) < 0.002 and abs(mom_accel) < 0.05:
            return "CONSOLIDATION"  # "Patience is the warrior's friend"

        # 6. VOLUME DIVERGENCE — price moves but volume disagrees
        if abs(price_change) > 0.003 and vol_change < -0.2:
            return "VOLUME_DIVERGENCE"  # "Deception — all warfare is deception"

        # 7. SQUEEZE — volatility contracting (spring loading)
        if s1.volatility < s2.volatility * 0.8:
            return "SQUEEZE"  # "The compressed spring" — prepare for explosion

        # 8. WHALE SHADOW — orca threat high
        if s1.orca_threat_level > 0.5:
            return "WHALE_SHADOW"  # "Know your enemy" — IRA intelligence

        return "NEUTRAL"  # "When in doubt, do nothing" — Sun Tzu patience

    def _extrapolate(self, pattern: str, price_change: float, mom_accel: float,
                     vol_change: float, latest: BoardState) -> Dict:
        """
        From the classified pattern, predict 1 step forward.

        Uses the IRA principle: observe the pattern, predict the counter,
        then counter the counter.
        """
        predictions = {
            "CHARGING_BULL": {
                'direction': 'BULLISH',
                'magnitude': abs(price_change) * PHI,  # Golden ratio extension
                'confidence': 0.65,
                'reasoning': 'Charging bull — momentum + volume confirm. Pursue the retreat.',
                'tactical_advice': 'ATTACK with trailing stop. Ride the wave.',
            },
            "EXHAUSTED_BULL": {
                'direction': 'BEARISH',  # Counter-trend — the bull is dying
                'magnitude': abs(price_change) * 0.5,
                'confidence': 0.55,
                'reasoning': 'Exhausted bull — culminating point reached. Prepare feigned retreat.',
                'tactical_advice': 'DEFEND — take profit before reversal. Exit flying columns.',
            },
            "BEAR_AMBUSH": {
                'direction': 'BEARISH',
                'magnitude': abs(price_change) * PHI,
                'confidence': 0.60,
                'reasoning': 'Bear ambush in progress. Step aside, let it pass.',
                'tactical_advice': 'RETREAT — do not catch falling knives. Wait for exhaustion.',
            },
            "BEAR_EXHAUSTION": {
                'direction': 'BULLISH',  # Counter-trend — selling exhausted
                'magnitude': abs(price_change) * 0.618,  # Fibonacci retracement
                'confidence': 0.60,
                'reasoning': 'Bear exhaustion — selling pressure fading. Ambush position ready.',
                'tactical_advice': 'AMBUSH — enter on confirmation. Small flying column first.',
            },
            "CONSOLIDATION": {
                'direction': 'NEUTRAL',
                'magnitude': 0.001,
                'confidence': 0.40,
                'reasoning': 'Consolidation — the battlefield is quiet. Gather intelligence.',
                'tactical_advice': 'HOLD — patience is the warrior\'s friend. Scout all fronts.',
            },
            "VOLUME_DIVERGENCE": {
                'direction': 'BEARISH' if price_change > 0 else 'BULLISH',
                'magnitude': abs(price_change) * 0.8,
                'confidence': 0.55,
                'reasoning': 'Volume divergence — deception detected. The real move is opposite.',
                'tactical_advice': 'FEINT detected — prepare for reversal. Do not chase.',
            },
            "SQUEEZE": {
                'direction': 'NEUTRAL',  # Could go either way
                'magnitude': latest.volatility * 2.0,  # Expect double volatility
                'confidence': 0.50,
                'reasoning': 'Squeeze — spring compressed. Explosion imminent but direction unknown.',
                'tactical_advice': 'READY positions on BOTH sides. First-mover advantage critical.',
            },
            "WHALE_SHADOW": {
                'direction': 'NEUTRAL',
                'magnitude': 0.005,
                'confidence': 0.35,
                'reasoning': 'Whale shadow — predator detected. Do not swim in these waters.',
                'tactical_advice': 'RETREAT — orca predator active. Wait for clear waters.',
            },
            "NEUTRAL": {
                'direction': 'NEUTRAL',
                'magnitude': 0.0,
                'confidence': 0.30,
                'reasoning': 'No clear pattern. Sun Tzu: "When in doubt, do nothing."',
                'tactical_advice': 'HOLD — insufficient conviction. Continue surveillance.',
            },
        }

        pred = predictions.get(pattern, predictions["NEUTRAL"]).copy()
        pred['pattern'] = pattern

        # Boost confidence if quantum mirror and telescope agree
        if latest.quantum_mirror_coherence > 0.618:
            pred['confidence'] = min(1.0, pred['confidence'] + 0.1)
            pred['reasoning'] += ' Quantum Mirror coherence confirms.'

        if latest.quantum_telescope_alignment > 0.5:
            pred['confidence'] = min(1.0, pred['confidence'] + 0.08)
            pred['reasoning'] += ' Quantum Telescope alignment supports.'

        if latest.harmonic_resonance > 0.5:
            pred['confidence'] = min(1.0, pred['confidence'] + 0.07)
            pred['reasoning'] += ' Harmonic field resonates.'

        return pred

    def _detect_trap(self, s2: BoardState, s1: BoardState) -> float:
        """
        Detect if the enemy (market) is setting a trap.

        Trap signals:
        1. Price moving one way while smart money moves opposite (whale divergence)
        2. Volume spike without price follow-through (failed breakout)
        3. Orca predator detected (someone hunting our stops)
        4. Sudden sentiment shift without fundamental cause
        """
        trap_score = 0.0

        # Whale divergence
        if s1.orca_threat_level > 0.3:
            trap_score += s1.orca_threat_level * 0.4

        # Volume spike without price follow-through
        if s1.volume_ratio > 2.0 and abs(s1.momentum_1m) < 0.1:
            trap_score += 0.3

        # Quantum mirror shows low coherence (reality branches diverging)
        if s1.quantum_mirror_coherence < 0.3:
            trap_score += 0.2

        # Sharp reversal from step_back_2 to step_back_1
        if s2.momentum_1m > 0.5 and s1.momentum_1m < -0.3:
            trap_score += 0.25
        elif s2.momentum_1m < -0.5 and s1.momentum_1m > 0.3:
            trap_score += 0.25

        return min(1.0, trap_score)

    def get_step_summaries(self, symbol: str = "") -> Tuple[Dict, Dict]:
        """Get summary dicts for step_back_2 and step_back_1."""
        with self._lock:
            states = [s for s in self._history if not symbol or s.symbol == symbol]

        if len(states) < 2:
            return {}, {}

        s2, s1 = states[-2], states[-1]

        def _summarize(s: BoardState) -> Dict:
            return {
                'price': s.current_price,
                'momentum_1m': s.momentum_1m,
                'momentum_5m': s.momentum_5m,
                'volume_ratio': s.volume_ratio,
                'volatility': s.volatility,
                'orca_threat': s.orca_threat_level,
                'qm_coherence': s.quantum_mirror_coherence,
                'qt_alignment': s.quantum_telescope_alignment,
                'harmonic_resonance': s.harmonic_resonance,
            }

        return _summarize(s2), _summarize(s1)


# ═══════════════════════════════════════════════════════════════════════════════
# THE ADVERSARIAL CHESS ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class AdversarialChessEngine:
    """
    Plays chess against itself.

    White (us) proposes moves. Black (enemy) finds counters.
    Only if White can survive Black's best counter do we proceed.

    Sun Tzu: "Every battle is won before it is fought."
    IRA: "Never engage unless you've already won."
    """

    def __init__(self):
        self._game_history: deque = deque(maxlen=500)
        self._win_rate = 0.5  # Updated from feedback

    def play_round(self, board: BoardState, prediction: Dict) -> Tuple[ChessMove, ChessMove]:
        """
        Play one round of adversarial chess.

        1. White proposes its best move based on prediction
        2. Black finds the strongest counter-move
        3. Return both for evaluation

        Returns: (white_move, black_counter)
        """
        white_move = self._white_proposes(board, prediction)
        black_counter = self._black_counters(board, white_move, prediction)

        # Evaluate survival
        white_move.survival_probability = self._evaluate_survival(
            white_move, black_counter, board
        )

        return white_move, black_counter

    def _white_proposes(self, board: BoardState, prediction: Dict) -> ChessMove:
        """
        WHITE (Profit) proposes its best move.

        Decision tree:
        1. If prediction is BULLISH with high confidence → ATTACK
        2. If we have a winning position → DEFEND (take profit)
        3. If prediction is BEARISH → RETREAT or AMBUSH
        4. If unclear → HOLD (Sun Tzu patience)
        """
        direction = prediction.get('direction', 'NEUTRAL')
        confidence = prediction.get('confidence', 0.0)
        magnitude = prediction.get('magnitude', 0.0)
        pattern = prediction.get('pattern', 'NEUTRAL')

        # If we have a profitable position — consider defending (taking profit)
        if board.has_position and board.unrealized_pnl_pct > 0.02:
            # Guerrilla doctrine: take the penny, don't be greedy
            if confidence < 0.6 or direction != ('BULLISH' if board.position_side == 'long' else 'BEARISH'):
                return ChessMove(
                    side=ChessSide.WHITE,
                    move_type=MoveType.DEFEND,
                    symbol=board.symbol,
                    confidence=0.7,
                    expected_pnl=board.position_pnl,
                    risk=0.1,
                    reasoning=f"Take profit. Guerrilla doctrine: penny secured > penny risked. Pattern: {pattern}",
                    source_systems=['war_strategy', 'guerrilla_doctrine'],
                )

        # ATTACK if bullish with conviction
        if direction == 'BULLISH' and confidence >= 0.55:
            # Check additional system agreement
            system_count = 0
            systems = []
            if board.quantum_mirror_coherence > 0.5:
                system_count += 1
                systems.append('quantum_mirror')
            if board.quantum_telescope_alignment > 0.4:
                system_count += 1
                systems.append('quantum_telescope')
            if board.war_strategy_go:
                system_count += 1
                systems.append('war_strategy')
            if board.guerrilla_ambush_score > 0.5:
                system_count += 1
                systems.append('guerrilla_engine')
            if board.hub_direction == 'BULLISH':
                system_count += 1
                systems.append('autonomy_hub')
            if board.harmonic_resonance > 0.5:
                system_count += 1
                systems.append('harmonic_field')
            if board.hnc_probability > 0.6:
                system_count += 1
                systems.append('hnc_matrix')

            # Need at least 3 systems to agree (combined arms doctrine)
            if system_count >= 3:
                return ChessMove(
                    side=ChessSide.WHITE,
                    move_type=MoveType.ATTACK,
                    symbol=board.symbol,
                    confidence=min(1.0, confidence + system_count * 0.05),
                    expected_pnl=magnitude * 100,  # Rough $ estimate
                    risk=max(0.1, 1.0 - confidence),
                    reasoning=f"ATTACK. {system_count}/7 systems agree. Pattern: {pattern}. "
                              f"Combined arms: {', '.join(systems)}",
                    source_systems=systems,
                )
            else:
                return ChessMove(
                    side=ChessSide.WHITE,
                    move_type=MoveType.AMBUSH,
                    symbol=board.symbol,
                    confidence=confidence * 0.7,
                    expected_pnl=magnitude * 50,
                    risk=0.3,
                    reasoning=f"AMBUSH WAIT. Only {system_count}/7 agree. Need combined arms. Pattern: {pattern}",
                    source_systems=systems,
                )

        # RETREAT if bearish and we have position
        if direction == 'BEARISH' and board.has_position:
            return ChessMove(
                side=ChessSide.WHITE,
                move_type=MoveType.RETREAT,
                symbol=board.symbol,
                confidence=confidence,
                expected_pnl=board.position_pnl,  # Accept current P&L
                risk=0.8 if board.position_pnl < 0 else 0.2,
                reasoning=f"RETREAT. Bearish prediction. Pattern: {pattern}. Cut losses early — IRA doctrine.",
                source_systems=['lookback_engine'],
            )

        # Default: HOLD — "when in doubt, do nothing"
        return ChessMove(
            side=ChessSide.WHITE,
            move_type=MoveType.HOLD,
            symbol=board.symbol,
            confidence=0.3,
            expected_pnl=0.0,
            risk=0.1,
            reasoning=f"HOLD. Sun Tzu: 'When in doubt, do nothing.' Pattern: {pattern}",
            source_systems=['sun_tzu_patience'],
        )

    def _black_counters(self, board: BoardState, white_move: ChessMove,
                        prediction: Dict) -> ChessMove:
        """
        BLACK (Revenue Loss) finds the strongest counter to White's move.

        Black represents everything that can go wrong:
        - Fees eating the profit
        - Slippage widening at execution
        - Stop-hunt by whales
        - Sudden reversal
        - Spread widening
        - Exchange downtime
        """
        counter_moves = []

        # 1. FEE ATTACK — the constant enemy
        fee_drag = 0.015  # ~1.5% round-trip fees on small positions
        if white_move.move_type == MoveType.ATTACK:
            counter_moves.append(
                f"Fee drag: -{fee_drag*100:.1f}% round-trip will eat into the expected "
                f"+{prediction.get('magnitude', 0)*100:.2f}% move"
            )

        # 2. WHALE COUNTER — if orca predator is active
        if board.orca_threat_level > 0.3:
            counter_moves.append(
                f"Predator active (threat: {board.orca_threat_level:.0%}). "
                f"Stop-hunt or front-running likely."
            )

        # 3. REVERSAL TRAP — fake move to lure in
        trap_prob = prediction.get('trap_probability', 0.0)
        if trap_prob > 0.3:
            counter_moves.append(
                f"Trap detected ({trap_prob:.0%}). The move may be an unconfirmed reversal."
            )

        # 4. VOLATILITY SPIKE — sudden adverse move
        if board.volatility > 0.03:
            counter_moves.append(
                f"High volatility ({board.volatility:.1%}). Adverse spike risk elevated."
            )

        # 5. LOW COHERENCE — reality branches diverging
        if board.quantum_mirror_coherence < 0.3:
            counter_moves.append(
                "Low quantum coherence. Multiple contradictory timelines — chaos risk."
            )

        # 6. TIMING ATTACK — we might be too late
        pattern = prediction.get('pattern', '')
        if pattern in ('EXHAUSTED_BULL', 'BEAR_EXHAUSTION'):
            counter_moves.append(
                "Late entry. The move is already exhausted — we're the last to the party."
            )

        # Black's overall counter strength
        counter_strength = min(1.0, len(counter_moves) * 0.15 + board.orca_threat_level * 0.3)

        return ChessMove(
            side=ChessSide.BLACK,
            move_type=MoveType.ATTACK,  # Black always attacks
            symbol=board.symbol,
            confidence=counter_strength,
            expected_pnl=-abs(white_move.expected_pnl) * counter_strength,
            risk=counter_strength,
            reasoning=f"Enemy counters with {len(counter_moves)} threats. "
                      f"Overall counter strength: {counter_strength:.0%}",
            counter_moves=counter_moves,
            source_systems=['enemy_simulation'],
        )

    def _evaluate_survival(self, white: ChessMove, black: ChessMove,
                           board: BoardState) -> float:
        """
        Can White survive Black's counter?

        Survival = White's edge minus Black's counter strength,
        weighted by the number of supporting systems.

        IRA principle: "Only fight if you've already won."
        """
        # Base survival from confidence difference
        base_survival = white.confidence - black.confidence * 0.5

        # System consensus boosts survival
        system_bonus = len(white.source_systems) * 0.05

        # Queen's 1.88% profit law — if expected profit doesn't meet minimum, penalize
        min_profit_pct = (QUEEN_MIN_COP - 1.0)  # 0.0188
        if white.expected_pnl > 0:
            estimated_pct = white.expected_pnl / max(10.0, board.current_price)
            if estimated_pct < min_profit_pct:
                base_survival *= 0.7  # Penalize sub-threshold trades

        # Harmonic resonance supports survival
        harmonic_bonus = board.harmonic_resonance * 0.1

        survival = base_survival + system_bonus + harmonic_bonus

        # Clamp
        return max(0.0, min(1.0, survival))

    def record_result(self, move: ChessMove, actual_pnl: float):
        """Record the actual result for learning."""
        won = actual_pnl > 0
        self._game_history.append({
            'time': time.time(),
            'move_type': move.move_type.value,
            'confidence': move.confidence,
            'expected_pnl': move.expected_pnl,
            'actual_pnl': actual_pnl,
            'won': won,
            'survival_prob': move.survival_probability,
        })
        # Update rolling win rate
        recent = list(self._game_history)[-100:]
        if recent:
            self._win_rate = sum(1 for g in recent if g['won']) / len(recent)


# ═══════════════════════════════════════════════════════════════════════════════
# THE STRATEGIC WAR PLANNER — THE MIND
# ═══════════════════════════════════════════════════════════════════════════════

class StrategicWarPlanner:
    """
    The system's MIND.

    Each cycle:
    1. OBSERVE — gather intelligence from all connected systems
    2. ORIENT  — classify the pattern (2 steps back)
    3. DECIDE  — play adversarial chess (White vs Black)
    4. ACT     — emit the final plan

    This is Boyd's OODA loop fused with Sun Tzu's calculated temple
    and the IRA's flying column doctrine.
    """

    def __init__(self):
        self.lookback = LookbackEngine()
        self.chess = AdversarialChessEngine()

        # Connected systems (lazy-loaded)
        self._quantum_mirror = None
        self._quantum_telescope = None
        self._war_strategy = None
        self._guerrilla_engine = None
        self._miner_brain = None
        self._orca_detector = None
        self._hnc_matrix = None
        self._autonomy_hub = None

        # State
        self._current_stance = TacticalStance.AMBUSH
        self._plans_history: deque = deque(maxlen=200)
        self._consecutive_holds = 0
        self._consecutive_wins = 0
        self._consecutive_losses = 0
        self._lock = threading.Lock()

        # Strategy rotation (IRA: never fight the same way twice)
        self._strategy_rotation = deque([
            'penny_sniper',      # Quick in/out for penny profit
            'momentum_rider',    # Ride strong trends
            'mean_reversion',    # Buy dips, sell rips
            'volatility_scalp',  # Scalp volatility spikes
            'whale_follower',    # Follow smart money
        ])
        self._current_strategy = self._strategy_rotation[0]

        logger.info("[WarPlanner] THE MIND initialized")
        logger.info("[WarPlanner] OODA Loop: Observe → Orient → Decide → Act")
        logger.info("[WarPlanner] Doctrine: Sun Tzu + IRA + Boyd")

    # ─── SYSTEM CONNECTION ──────────────────────────────────────────────

    def _connect_systems(self):
        """Lazy-connect to all available subsystems."""
        # Quantum Mirror
        if self._quantum_mirror is None:
            try:
                from aureon.scanners.aureon_quantum_mirror_scanner import QuantumMirrorScanner
                self._quantum_mirror = QuantumMirrorScanner()
            except Exception:
                pass

        # Quantum Telescope
        if self._quantum_telescope is None:
            try:
                from aureon.simulation.aureon_quantum_telescope import QuantumTelescope
                self._quantum_telescope = QuantumTelescope()
            except Exception:
                pass

        # War Strategy
        if self._war_strategy is None:
            try:
                from aureon.command_centers.war_strategy import WarStrategy
                self._war_strategy = WarStrategy()
            except Exception:
                pass

        # Guerrilla Warfare Engine
        if self._guerrilla_engine is None:
            try:
                from aureon.wisdom.guerrilla_warfare_engine import IntelligenceNetwork
                self._guerrilla_engine = IntelligenceNetwork()
            except Exception:
                pass

        # Miner Brain (speculation engine)
        if self._miner_brain is None:
            try:
                from aureon.utils.aureon_miner_brain import MinerBrain
                self._miner_brain = MinerBrain()
            except Exception:
                pass

        # Orca Predator Detection
        if self._orca_detector is None:
            try:
                from aureon.bots.orca_predator_detection import OrcaPredatorDetector
                self._orca_detector = OrcaPredatorDetector()
            except Exception:
                pass

        # HNC Probability Matrix
        if self._hnc_matrix is None:
            try:
                from aureon.strategies.hnc_probability_matrix import TemporalFrequencyAnalyzer
                self._hnc_matrix = TemporalFrequencyAnalyzer()
            except Exception:
                pass

        # Autonomy Hub
        if self._autonomy_hub is None:
            try:
                from aureon.autonomous.aureon_autonomy_hub import get_autonomy_hub
                self._autonomy_hub = get_autonomy_hub()
            except Exception:
                pass

    # ─── THE OODA LOOP ──────────────────────────────────────────────────

    def plan(self, symbol: str, price: float, volume: float = 0.0,
             change_pct: float = 0.0, has_position: bool = False,
             position_pnl: float = 0.0, position_side: str = "none",
             exchange: str = "binance") -> WarPlan:
        """
        Execute one full OODA cycle and produce a WarPlan.

        This is the MAIN entry point. Call this every cycle.
        """
        self._connect_systems()
        cycle_start = time.time()

        # ═══ OBSERVE ═══
        board = self._observe(symbol, price, volume, change_pct,
                              has_position, position_pnl, position_side, exchange)

        # ═══ ORIENT ═══
        self.lookback.record_state(board)
        prediction = self.lookback.predict_forward(symbol)
        step_back_2, step_back_1 = self.lookback.get_step_summaries(symbol)

        # ═══ DECIDE ═══
        white_move, black_counter = self.chess.play_round(board, prediction)

        # Apply stance modifier
        final_move = self._apply_stance(white_move, black_counter, board, prediction)

        # ═══ ACT ═══
        plan = WarPlan(
            symbol=symbol,
            stance=self._current_stance,
            white_move=white_move,
            black_counter=black_counter,
            final_move=final_move,
            step_back_2=step_back_2,
            step_back_1=step_back_1,
            step_forward=prediction,
            board=board,
            systems_consulted=self._get_connected_systems(),
            consensus_agreement=self._calculate_consensus(board, prediction),
        )

        self._plans_history.append(plan)
        self._update_stance(final_move, board)

        # Publish to ThoughtBus
        self._publish_plan(plan)

        cycle_ms = (time.time() - cycle_start) * 1000
        logger.info(f"[WarPlanner] OODA cycle: {cycle_ms:.0f}ms | "
                    f"Pattern: {prediction.get('pattern', '?')} | "
                    f"Move: {final_move.move_type.value} | "
                    f"Confidence: {final_move.confidence:.0%} | "
                    f"Survival: {final_move.survival_probability:.0%} | "
                    f"Stance: {self._current_stance.value}")

        return plan

    def _observe(self, symbol: str, price: float, volume: float,
                 change_pct: float, has_position: bool, position_pnl: float,
                 position_side: str, exchange: str) -> BoardState:
        """
        OBSERVE phase: Gather intelligence from ALL connected systems.

        "Use of spies is the most important element in warfare,
        on which all army operations depend." — Sun Tzu
        """
        board = BoardState(
            symbol=symbol,
            current_price=price,
            momentum_1m=change_pct,
            volume=volume,
            has_position=has_position,
            position_pnl=position_pnl,
            position_side=position_side,
            unrealized_pnl_pct=position_pnl / max(10.0, price) if price > 0 else 0.0,
        )

        # Fill in historical prices from lookback
        with self.lookback._lock:
            states = [s for s in self.lookback._history if s.symbol == symbol]
            if len(states) >= 1:
                board.price_1_step_ago = states[-1].current_price
                board.momentum_5m = states[-1].momentum_5m
            if len(states) >= 2:
                board.price_2_steps_ago = states[-2].current_price

        # Quantum Mirror — reality branch coherence
        if self._quantum_mirror:
            try:
                boost, _ = self._quantum_mirror.get_quantum_boost(
                    symbol.replace('USD', ''), 'USD', exchange
                )
                board.quantum_mirror_coherence = max(0.0, min(1.0, boost))
            except Exception:
                pass

        # Quantum Telescope — geometric alignment
        if self._quantum_telescope:
            try:
                obs = self._quantum_telescope.observe(symbol, price, volume, change_pct)
                board.quantum_telescope_alignment = obs.get('geometric_alignment', 0.0)
            except Exception:
                pass

        # War Strategy — quick-kill probability
        if self._war_strategy:
            try:
                self._war_strategy.update_volatility(symbol, [
                    board.price_2_steps_ago or price * 0.999,
                    board.price_1_step_ago or price * 0.9995,
                    price
                ], exchange)
                estimate = self._war_strategy.estimate_quick_kill(symbol, exchange)
                if estimate:
                    board.war_strategy_go = estimate.go_signal
                    board.guerrilla_ambush_score = estimate.prob_quick_kill
                    board.volatility = estimate.recent_volatility
            except Exception:
                pass

        # Orca Predator Detection
        if self._orca_detector:
            try:
                threat = self._orca_detector.get_threat_level(symbol)
                board.orca_threat_level = threat if isinstance(threat, float) else 0.0
            except Exception:
                pass

        # HNC Probability Matrix
        if self._hnc_matrix:
            try:
                matrix = self._hnc_matrix.generate_probability_matrix(symbol, {
                    'price': price, 'volume': volume, 'change_pct': change_pct
                })
                if matrix and hasattr(matrix, 'combined_probability'):
                    board.hnc_probability = matrix.combined_probability
                elif isinstance(matrix, dict):
                    board.hnc_probability = matrix.get('combined_probability', 0.5)
            except Exception:
                pass

        # Autonomy Hub — the big wheel's current opinion
        if self._autonomy_hub:
            try:
                decision = self._autonomy_hub.spin_cycle(symbol)
                board.hub_direction = decision.direction
                board.hub_confidence = decision.confidence
            except Exception:
                pass

        # Volume ratio from recent history
        with self.lookback._lock:
            recent_volumes = [s.volume for s in self.lookback._history
                              if s.symbol == symbol and s.volume > 0][-20:]
        if recent_volumes:
            avg_vol = sum(recent_volumes) / len(recent_volumes)
            board.volume_ratio = volume / max(1.0, avg_vol)

        return board

    def _apply_stance(self, white: ChessMove, black: ChessMove,
                      board: BoardState, prediction: Dict) -> ChessMove:
        """
        Apply the current tactical stance to the proposed move.

        The stance modifies the final decision:
        - AMBUSH: only execute if survival > 0.65
        - FLYING_COLUMN: lower threshold (0.50), faster execution
        - SIEGE: only defend, never attack
        - RETREAT: always exit positions
        - BLITZ: execute even marginal moves
        """
        min_survival = {
            TacticalStance.AMBUSH: 0.65,
            TacticalStance.FLYING_COLUMN: 0.50,
            TacticalStance.SIEGE: 0.80,
            TacticalStance.RETREAT: 0.0,   # Always retreat
            TacticalStance.FEIGNED_RETREAT: 0.55,
            TacticalStance.BLITZ: 0.40,
        }

        threshold = min_survival.get(self._current_stance, 0.60)

        # RETREAT stance overrides everything
        if self._current_stance == TacticalStance.RETREAT:
            if board.has_position:
                return ChessMove(
                    side=ChessSide.WHITE,
                    move_type=MoveType.RETREAT,
                    symbol=board.symbol,
                    confidence=0.9,
                    expected_pnl=board.position_pnl,
                    risk=0.1,
                    reasoning="RETREAT stance — exit all positions. Protect capital.",
                    survival_probability=1.0,
                    source_systems=['stance_override'],
                )
            return ChessMove(
                side=ChessSide.WHITE, move_type=MoveType.HOLD,
                symbol=board.symbol, confidence=0.5,
                reasoning="RETREAT stance — no positions to exit. Holding.",
                survival_probability=1.0,
                source_systems=['stance_override'],
            )

        # SIEGE stance — only defend
        if self._current_stance == TacticalStance.SIEGE:
            if white.move_type == MoveType.ATTACK:
                return ChessMove(
                    side=ChessSide.WHITE, move_type=MoveType.HOLD,
                    symbol=board.symbol, confidence=0.5,
                    reasoning=f"SIEGE stance — attack suppressed. Patience. "
                              f"Original: {white.reasoning}",
                    survival_probability=0.9,
                    source_systems=white.source_systems,
                )

        # Standard: check survival threshold
        if white.survival_probability < threshold:
            return ChessMove(
                side=ChessSide.WHITE,
                move_type=MoveType.HOLD,
                symbol=board.symbol,
                confidence=white.confidence * 0.5,
                expected_pnl=0.0,
                risk=0.05,
                reasoning=f"Survival too low ({white.survival_probability:.0%} < "
                          f"{threshold:.0%}). {self._current_stance.value} stance says HOLD. "
                          f"Original plan: {white.reasoning}",
                survival_probability=white.survival_probability,
                source_systems=white.source_systems,
            )

        # Passed all checks — execute the original move
        return white

    def _update_stance(self, final_move: ChessMove, board: BoardState):
        """
        Update tactical stance based on results.

        IRA doctrine: adapt to conditions on the ground.
        """
        if final_move.move_type == MoveType.HOLD:
            self._consecutive_holds += 1
        else:
            self._consecutive_holds = 0

        # If we've been holding too long, switch to FLYING COLUMN
        # (IRA: mobility > static defense)
        if self._consecutive_holds > 10:
            self._current_stance = TacticalStance.FLYING_COLUMN
            self._consecutive_holds = 0
            logger.info("[WarPlanner] Stance → FLYING_COLUMN (too many holds)")

        # If orca predator detected, go SIEGE
        if board.orca_threat_level > 0.6:
            self._current_stance = TacticalStance.SIEGE
            logger.info("[WarPlanner] Stance → SIEGE (predator detected)")

        # If consecutive losses, go RETREAT
        if self._consecutive_losses >= 3:
            self._current_stance = TacticalStance.RETREAT
            logger.info("[WarPlanner] Stance → RETREAT (3 consecutive losses)")

        # If consecutive wins, go BLITZ
        if self._consecutive_wins >= 5:
            self._current_stance = TacticalStance.BLITZ
            logger.info("[WarPlanner] Stance → BLITZ (5 consecutive wins — pressing advantage)")

        # Default back to AMBUSH if conditions normalize
        if (board.orca_threat_level < 0.3 and
                self._consecutive_losses < 2 and
                self._consecutive_wins < 5 and
                self._current_stance in (TacticalStance.RETREAT, TacticalStance.SIEGE)):
            self._current_stance = TacticalStance.AMBUSH
            logger.info("[WarPlanner] Stance → AMBUSH (conditions normalized)")

    def record_outcome(self, symbol: str, pnl: float):
        """Record trade outcome for learning and stance adjustment."""
        if pnl > 0:
            self._consecutive_wins += 1
            self._consecutive_losses = 0
        else:
            self._consecutive_losses += 1
            self._consecutive_wins = 0

        self.chess.record_result(
            ChessMove(side=ChessSide.WHITE, move_type=MoveType.ATTACK, symbol=symbol),
            pnl
        )

        # Rotate strategy after every 10 outcomes (IRA: never fight same way twice)
        total_games = len(self.chess._game_history)
        if total_games > 0 and total_games % 10 == 0:
            self._strategy_rotation.rotate(-1)
            self._current_strategy = self._strategy_rotation[0]
            logger.info(f"[WarPlanner] Strategy rotated → {self._current_strategy}")

    def _calculate_consensus(self, board: BoardState, prediction: Dict) -> float:
        """Calculate how much all systems agree (0-1)."""
        direction = prediction.get('direction', 'NEUTRAL')
        agreements = 0
        total = 0

        checks = [
            (board.hub_direction, board.hub_confidence > 0.3),
            ('BULLISH' if board.quantum_mirror_coherence > 0.618 else 'NEUTRAL',
             board.quantum_mirror_coherence > 0.3),
            ('BULLISH' if board.quantum_telescope_alignment > 0.5 else 'NEUTRAL',
             board.quantum_telescope_alignment > 0.2),
            ('BULLISH' if board.hnc_probability > 0.6 else
             'BEARISH' if board.hnc_probability < 0.4 else 'NEUTRAL',
             True),
            ('BULLISH' if board.war_strategy_go else 'NEUTRAL', True),
        ]

        for sys_direction, is_active in checks:
            if is_active:
                total += 1
                if sys_direction == direction:
                    agreements += 1

        return agreements / max(1, total)

    def _get_connected_systems(self) -> List[str]:
        """List which systems are actually connected."""
        systems = []
        if self._quantum_mirror:
            systems.append('quantum_mirror')
        if self._quantum_telescope:
            systems.append('quantum_telescope')
        if self._war_strategy:
            systems.append('war_strategy')
        if self._guerrilla_engine:
            systems.append('guerrilla_engine')
        if self._miner_brain:
            systems.append('miner_brain')
        if self._orca_detector:
            systems.append('orca_predator')
        if self._hnc_matrix:
            systems.append('hnc_probability_matrix')
        if self._autonomy_hub:
            systems.append('autonomy_hub')
        return systems

    def _publish_plan(self, plan: WarPlan):
        """Publish the plan to ThoughtBus for system-wide awareness."""
        try:
            from aureon.core.aureon_thought_bus import get_thought_bus, Thought
            bus = get_thought_bus()
            bus.publish(Thought(
                source="war_planner",
                topic="strategy.war_plan",
                payload=plan.to_dict()
            ))
        except Exception:
            pass

    def get_status(self) -> Dict:
        """Get planner status for monitoring."""
        return {
            'stance': self._current_stance.value,
            'strategy': self._current_strategy,
            'consecutive_wins': self._consecutive_wins,
            'consecutive_losses': self._consecutive_losses,
            'consecutive_holds': self._consecutive_holds,
            'chess_win_rate': self.chess._win_rate,
            'plans_generated': len(self._plans_history),
            'connected_systems': self._get_connected_systems(),
            'lookback_history_size': len(self.lookback._history),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON & CONVENIENCE
# ═══════════════════════════════════════════════════════════════════════════════

_planner_instance: Optional[StrategicWarPlanner] = None
_planner_lock = threading.Lock()


def get_war_planner() -> StrategicWarPlanner:
    """Get or create the global StrategicWarPlanner singleton."""
    global _planner_instance
    with _planner_lock:
        if _planner_instance is None:
            _planner_instance = StrategicWarPlanner()
    return _planner_instance


def plan_move(symbol: str, price: float, volume: float = 0.0,
              change_pct: float = 0.0, **kwargs) -> WarPlan:
    """Convenience: plan a move."""
    planner = get_war_planner()
    return planner.plan(symbol, price, volume, change_pct, **kwargs)


def record_outcome(symbol: str, pnl: float):
    """Convenience: record trade outcome."""
    planner = get_war_planner()
    planner.record_outcome(symbol, pnl)


def war_status() -> Dict:
    """Convenience: get planner status."""
    planner = get_war_planner()
    return planner.get_status()


# Deliberately no standalone runtime: production callers must supply live context.
