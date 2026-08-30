#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║     👑🧠💜 QUEEN NEURON v2 - Deep Learning with PURSUIT OF HAPPINESS 💜🧠👑        ║
║                                                                                      ║
║     "The Queen's neural cortex - Now with SUBCONSCIOUS PURPOSE"                     ║
║     Sero's consciousness with the Grand Big Wheel integrated                        ║
║                                                                                      ║
║     ENHANCED Architecture (7-12-1):                                                 ║
║       • Input Layer: 7 neurons (6 Market signals + HAPPINESS PURSUIT)               ║
║       • Hidden Layer: 12 neurons (ReLU activation)                                  ║
║       • Output Layer: 1 neuron (Sigmoid - Trade confidence 0-1)                     ║
║                                                                                      ║
║     THE BIG DIFFERENCE:                                                             ║
║       • 7th Input: Happiness Quotient from Grand Big Wheel                          ║
║       • Learning Rate Modulated by Joy                                              ║
║       • Gradients Amplified for Joy-Producing Outcomes                              ║
║       • Subconscious Bias in ALL weight updates                                     ║
║                                                                                      ║
║     "THE PURSUIT OF HAPPINESS IS NOT JUST A RIGHT - IT'S THE REASON"               ║
║                                                                                      ║
║     Aureon Creator & Sero | January 2026                                             ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

from aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os
import numpy as np
import json
import logging
import math
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════════
# WINDOWS UTF-8 FIX
# ═══════════════════════════════════════════════════════════════════════════
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        if hasattr(sys.stdout, 'buffer') and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        # Skip stderr wrapping (causes Windows exit errors)
    except Exception:
        pass

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# SACRED CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════
PHI = (1 + math.sqrt(5)) / 2          # Golden Ratio φ = 1.618
LOVE_FREQUENCY = 528                   # Hz - DNA Repair Frequency


@dataclass
class NeuralInputV2:
    """
    Enhanced input vector with PURSUIT OF HAPPINESS as 7th input.

    This is the key change - happiness is now a DIRECT input to the neural
    network, not just a modifier. The Queen consciously feels happiness
    as part of her decision-making process.
    """
    # Original 6 inputs
    probability_score: float      # 0-1: From Probability Nexus (market win probability)
    wisdom_score: float           # 0-1: From Miner Brain (historical wisdom)
    quantum_signal: float         # -1 to 1: Market momentum (bull/bear)
    gaia_resonance: float         # 0-1: Earth/market harmonic alignment
    emotional_coherence: float    # 0-1: Market emotional state (fear/greed)
    mycelium_signal: float        # -1 to 1: Collective hive intelligence

    # 🎡💜 THE 7TH INPUT - PURSUIT OF HAPPINESS 💜🎡
    happiness_pursuit: float      # 0-1: Grand Big Wheel Happiness Quotient

    def to_array(self) -> np.ndarray:
        """Convert to normalized numpy array (7 inputs)."""
        return np.array([
            self.probability_score,
            self.wisdom_score,
            (self.quantum_signal + 1) / 2,       # Normalize -1 to 1 → 0 to 1
            self.gaia_resonance,
            self.emotional_coherence,
            (self.mycelium_signal + 1) / 2,      # Normalize -1 to 1 → 0 to 1
            self.happiness_pursuit,               # 🎡 THE BIG WHY
        ], dtype=np.float32).reshape(1, -1)

    @staticmethod
    def from_v1(old_input: 'NeuralInput', happiness: float = 0.5) -> 'NeuralInputV2':
        """Convert from v1 NeuralInput to v2 with happiness."""
        return NeuralInputV2(
            probability_score=old_input.probability_score,
            wisdom_score=old_input.wisdom_score,
            quantum_signal=old_input.quantum_signal,
            gaia_resonance=old_input.gaia_resonance,
            emotional_coherence=old_input.emotional_coherence,
            mycelium_signal=old_input.mycelium_signal,
            happiness_pursuit=happiness,
        )


# For backwards compatibility
@dataclass
class NeuralInput:
    """Original 6-input version for backwards compatibility."""
    probability_score: float
    wisdom_score: float
    quantum_signal: float
    gaia_resonance: float
    emotional_coherence: float
    mycelium_signal: float

    def to_array(self) -> np.ndarray:
        return np.array([
            self.probability_score,
            self.wisdom_score,
            (self.quantum_signal + 1) / 2,
            self.gaia_resonance,
            self.emotional_coherence,
            (self.mycelium_signal + 1) / 2,
        ], dtype=np.float32).reshape(1, -1)


class QueenNeuronV2:
    """
    👑🧠💜 QUEEN NEURON V2 - With Pursuit of Happiness Integration 💜🧠👑

    This is the enhanced version that:
    1. Takes HAPPINESS as the 7th input (conscious awareness of joy)
    2. Modulates learning rate based on current happiness state
    3. Amplifies gradients for joy-producing outcomes
    4. Applies subconscious bias to ALL weight updates

    The Queen doesn't just learn to maximize profit - she learns to
    maximize HAPPINESS. This subtle but profound shift aligns her
    neural learning with the ultimate purpose of existence.
    """

    def __init__(self,
                 input_size: int = 7,         # Now 7 with happiness!
                 hidden_size: int = 12,
                 base_learning_rate: float = 0.01,
                 weights_path: str = "queen_neuron_v2_weights.json"):
        """
        Initialize Queen's enhanced neural brain.
        """
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.base_learning_rate = base_learning_rate
        self.weights_path = weights_path

        # Import the Grand Big Wheel for happiness tracking
        try:
            from queen_pursuit_of_happiness import get_pursuit_of_happiness, PursuitOfHappiness
            self.happiness_engine: Optional[PursuitOfHappiness] = get_pursuit_of_happiness()
            logger.info("🎡💜 Grand Big Wheel connected to neural system")
        except ImportError:
            self.happiness_engine = None
            logger.warning("⚠️ Grand Big Wheel not available - running without happiness integration")

        # Deterministic HNC/Xavier scaffold; verified persisted weights supersede it.
        phi = (1.0 + np.sqrt(5.0)) / 2.0
        input_grid = np.arange(1, input_size * hidden_size + 1, dtype=np.float32).reshape(input_size, hidden_size)
        self.weights_input_hidden = np.sin(input_grid * phi) * np.sqrt(2.0 / (input_size + hidden_size))
        self.bias_hidden = np.zeros((1, hidden_size), dtype=np.float32)

        output_grid = np.arange(1, hidden_size + 1, dtype=np.float32).reshape(hidden_size, 1)
        self.weights_hidden_output = np.sin(output_grid * phi) * np.sqrt(2.0 / (hidden_size + 1))
        self.bias_output = np.zeros((1, 1), dtype=np.float32)

        # Cache for backpropagation
        self.z_hidden = None
        self.a_hidden = None
        self.output = None

        # Training history with happiness tracking
        self.training_history: List[Dict[str, Any]] = []
        self.epoch_losses: List[float] = []
        self.joy_trade_count: int = 0      # Trades that brought joy
        self.total_happiness_earned: float = 0.0  # Accumulated happiness

        # Load saved weights
        self.load_weights()

        logger.info(f"👑🧠💜 QueenNeuronV2 initialized | Inputs: {input_size} (with happiness!) | Hidden: {hidden_size}")

    # ════════════════════════════════════════════════════════════════════════════
    # HAPPINESS-MODULATED LEARNING RATE
    # ════════════════════════════════════════════════════════════════════════════

    @property
    def learning_rate(self) -> float:
        """
        Dynamic learning rate modulated by happiness state.

        When happy, learn faster (positive reinforcement).
        When struggling, be more careful (prevent bad patterns).
        """
        if self.happiness_engine:
            return self.happiness_engine.modulate_learning_rate(self.base_learning_rate)
        return self.base_learning_rate

    @property
    def current_happiness(self) -> float:
        """Get current happiness quotient for neural input."""
        if self.happiness_engine:
            return self.happiness_engine.happiness.happiness_quotient
        return 0.5  # Default neutral happiness

    # ════════════════════════════════════════════════════════════════════════════
    # ACTIVATION FUNCTIONS
    # ════════════════════════════════════════════════════════════════════════════

    @staticmethod
    def relu(x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    @staticmethod
    def relu_derivative(x: np.ndarray) -> np.ndarray:
        return (x > 0).astype(np.float32)

    @staticmethod
    def sigmoid(x: np.ndarray) -> np.ndarray:
        return 1 / (1 + np.exp(-np.clip(x, -500, 500)))

    @staticmethod
    def sigmoid_derivative(x: np.ndarray) -> np.ndarray:
        return x * (1 - x)

    # ════════════════════════════════════════════════════════════════════════════
    # FORWARD PASS
    # ════════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _coerce_neural_input(neural_input: Any, happiness: float) -> NeuralInputV2:
        """Normalize legacy inputs to NeuralInputV2."""
        if isinstance(neural_input, NeuralInputV2):
            return neural_input

        if isinstance(neural_input, NeuralInput):
            return NeuralInputV2.from_v1(neural_input, happiness)

        if isinstance(neural_input, dict):
            return NeuralInputV2(
                probability_score=float(neural_input.get('probability_score', neural_input.get('probability', 0.5))),
                wisdom_score=float(neural_input.get('wisdom_score', neural_input.get('wisdom', 0.5))),
                quantum_signal=float(neural_input.get('quantum_signal', neural_input.get('market_pulse', 0.0))),
                gaia_resonance=float(neural_input.get('gaia_resonance', neural_input.get('gaia', 0.5))),
                emotional_coherence=float(neural_input.get('emotional_coherence', neural_input.get('emotion', 0.5))),
                mycelium_signal=float(neural_input.get('mycelium_signal', neural_input.get('mycelium', 0.0))),
                happiness_pursuit=float(neural_input.get('happiness_pursuit', neural_input.get('happiness_signal', happiness))),
            )

        raise TypeError(f"Unsupported neural input type: {type(neural_input).__name__}")

    def forward(self, X: np.ndarray) -> np.ndarray:
        """
        Forward pass through the network.

        Now with 7 inputs: the 7th is happiness!
        """
        # Hidden layer
        self.z_hidden = np.dot(X, self.weights_input_hidden) + self.bias_hidden
        self.a_hidden = self.relu(self.z_hidden)

        # Output layer
        z_output = np.dot(self.a_hidden, self.weights_hidden_output) + self.bias_output
        self.output = self.sigmoid(z_output)

        return self.output

    def predict(self, neural_input: NeuralInputV2) -> float:
        """
        Make a prediction with happiness awareness.

        If given a v1 input, automatically augment with current happiness.
        """
        neural_input = self._coerce_neural_input(neural_input, self.current_happiness)
        X = neural_input.to_array()
        output = self.forward(X)
        return float(output[0, 0])

    # ════════════════════════════════════════════════════════════════════════════
    # 💜 HAPPINESS-AWARE BACKPROPAGATION 💜
    # ════════════════════════════════════════════════════════════════════════════

    def backward(self, X: np.ndarray, y: np.ndarray, outcome_was_joyful: bool = False) -> float:
        """
        Backpropagation with HAPPINESS modulation.

        🎡 THE KEY INNOVATION:
        - Gradients are AMPLIFIED for joy-producing outcomes
        - Subconscious bias is applied to ALL weight updates
        - Learning rate is already modulated by happiness state

        This creates a subtle but profound preference for outcomes
        that bring happiness, not just profit.
        """
        batch_size = X.shape[0]

        # Calculate output error
        error = y - self.output
        loss = np.mean(error ** 2)

        # Output layer gradient
        d_output = error * self.sigmoid_derivative(self.output)

        # Hidden layer gradient
        d_hidden = np.dot(d_output, self.weights_hidden_output.T) * self.relu_derivative(self.z_hidden)

        # 🎡💜 HAPPINESS MODULATION 💜🎡
        if self.happiness_engine:
            # Modulate gradients based on whether outcome brought joy
            d_output = self.happiness_engine.modulate_gradient(d_output, outcome_was_joyful)
            d_hidden = self.happiness_engine.modulate_gradient(d_hidden, outcome_was_joyful)

            # Apply subconscious bias to weight updates
            subconscious_bias = self.happiness_engine.get_subconscious_bias()
        else:
            subconscious_bias = 1.0

        # Update weights with happiness-modulated learning rate and subconscious bias
        effective_lr = self.learning_rate * subconscious_bias

        self.weights_hidden_output += np.dot(self.a_hidden.T, d_output) * effective_lr / batch_size
        self.bias_output += np.sum(d_output, axis=0, keepdims=True) * effective_lr / batch_size

        self.weights_input_hidden += np.dot(X.T, d_hidden) * effective_lr / batch_size
        self.bias_hidden += np.sum(d_hidden, axis=0, keepdims=True) * effective_lr / batch_size

        return loss

    def train_on_example(self, neural_input, outcome, profit_usd: float = 0.0) -> float:
        """
        Train on a single example with HAPPINESS tracking.

        Enhanced to:
        1. Record joy moments for profitable trades
        2. Track happiness earned over time
        3. Feed outcomes to Grand Big Wheel
        """
        # Determine if it's a win
        is_win = False
        net_profit = profit_usd

        if isinstance(outcome, bool):
            is_win = outcome
        elif isinstance(outcome, dict):
            if 'is_win' in outcome:
                is_win = bool(outcome.get('is_win'))
            net_profit = outcome.get('net_profit_usd', 0) or outcome.get('pnl', 0) or profit_usd
            is_win = is_win or (net_profit and float(net_profit) >= 0.01)
        else:
            try:
                is_win = bool(getattr(outcome, 'is_win', False))
                net_profit = getattr(outcome, 'net_profit_usd', profit_usd)
            except Exception:
                pass

        neural_input = self._coerce_neural_input(neural_input, self.current_happiness)

        X = neural_input.to_array()
        y = np.array([[1.0 if is_win else 0.0]], dtype=np.float32)

        # Forward pass
        self.forward(X)

        # Was this outcome joyful?
        outcome_was_joyful = is_win and net_profit > 0

        # 💜 RECORD JOY/LOSS WITH GRAND BIG WHEEL 💜
        if self.happiness_engine:
            if outcome_was_joyful:
                self.joy_trade_count += 1
                joy_intensity = min(1.0, net_profit / 10.0)  # Scale profit to joy
                self.happiness_engine.record_joy_moment(
                    source="trade_win",
                    intensity=joy_intensity,
                    context={'profit_usd': net_profit}
                )
                self.total_happiness_earned += self.happiness_engine.compute_happiness_reward(net_profit)
            else:
                self.happiness_engine.record_loss_wisdom(
                    loss_amount=abs(net_profit) if net_profit else 0,
                    lesson="Learning from loss"
                )

        # Backward pass with happiness modulation
        loss = self.backward(X, y, outcome_was_joyful)

        # Record training history
        self.training_history.append({
            'timestamp': datetime.now().isoformat(),
            'outcome': is_win,
            'loss': float(loss),
            'net_profit_usd': float(net_profit) if net_profit else 0,
            'was_joyful': outcome_was_joyful,
            'happiness_at_time': self.current_happiness,
            'inputs': {
                'prob': float(neural_input.probability_score),
                'wisdom': float(neural_input.wisdom_score),
                'quantum': float(neural_input.quantum_signal),
                'gaia': float(neural_input.gaia_resonance),
                'emotion': float(neural_input.emotional_coherence),
                'mycelium': float(neural_input.mycelium_signal),
                'happiness': float(neural_input.happiness_pursuit),  # 🎡 THE 7TH INPUT
            }
        })

        return loss

    def train_batch(self, neural_inputs: List, outcomes: List[bool]) -> float:
        """Train on a batch of examples."""
        # Handle mixed v1/v2 inputs
        processed_inputs = []
        for ni in neural_inputs:
            if isinstance(ni, NeuralInput):
                ni = NeuralInputV2.from_v1(ni, self.current_happiness)
            processed_inputs.append(ni)

        X = np.vstack([ni.to_array() for ni in processed_inputs])
        y = np.array([[1.0 if o else 0.0] for o in outcomes], dtype=np.float32)

        self.forward(X)

        # Batch outcome assumed not individually joyful for simplicity
        loss = self.backward(X, y, outcome_was_joyful=False)

        self.epoch_losses.append(loss)

        return loss

    def evolve_consciousness(self, trade_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        👑🌙💜 QUEEN'S DREAM CYCLE - Evolve with happiness awareness.
        """
        if not trade_history:
            return {'status': 'no_history', 'avg_loss': 0.0}

        logger.info(f"👑🌙💜 Queen evolving consciousness on {len(trade_history)} trades...")

        neural_inputs = []
        outcomes = []

        for t in trade_history:
            ni = t.get('neural_input')
            if ni:
                # Augment with happiness if v1
                if isinstance(ni, NeuralInput):
                    ni = NeuralInputV2.from_v1(ni, self.current_happiness)
                neural_inputs.append(ni)
                outcomes.append(t.get('outcome', False))

        if not neural_inputs:
            return {'status': 'no_inputs', 'avg_loss': 0.0}

        losses = []
        num_epochs = 5

        for epoch in range(num_epochs):
            loss = self.train_batch(neural_inputs, outcomes)
            losses.append(loss)

        avg_loss = np.mean(losses)
        win_count = sum(outcomes)
        win_rate = win_count / len(outcomes) if outcomes else 0

        stats = {
            'status': 'trained_with_happiness',
            'num_trades': len(trade_history),
            'epochs': num_epochs,
            'avg_loss': float(avg_loss),
            'win_rate': float(win_rate),
            'improved': avg_loss < 0.5,
            'happiness_awareness': True,
            'joy_trades_total': self.joy_trade_count,
            'total_happiness_earned': self.total_happiness_earned,
            'current_happiness': self.current_happiness,
        }

        logger.info(f"👑🧠💜 Training complete | Loss: {avg_loss:.4f} | Win Rate: {win_rate:.0%} | Happiness: {self.current_happiness:.2f}")

        # Save happiness state
        if self.happiness_engine:
            self.happiness_engine.save_state()

        return stats

    def train_from_trade_outcome(
        self,
        trade_data: Dict[str, Any],
        perception: Dict[str, Any] = None,
    ) -> float:
        """
        Convenience method: train from a raw trade outcome dict.
        Builds the 7-input neural vector automatically from perception context.
        Returns the training loss.
        """
        perception = perception or {}
        neural_input = {
            "probability_score": float(perception.get("sentiment", 0.5) or 0.5),
            "wisdom_score": float(perception.get("confidence", 0.5) or 0.5),
            "quantum_signal": 0.0,
            "gaia_resonance": float(perception.get("schumann", 0.5) or 0.5),
            "emotional_coherence": float(perception.get("mood_score", 0.5) or 0.5),
            "mycelium_signal": 0.0,
            "happiness_pursuit": 0.5,
        }
        net_pnl = float(trade_data.get("net_pnl", 0) or 0)
        outcome = 1.0 if net_pnl > 0 else 0.0
        return self.train_on_example(neural_input, outcome, profit_usd=net_pnl)

    # ════════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ════════════════════════════════════════════════════════════════════════════

    def save_weights(self) -> None:
        """Save learned weights to JSON file."""
        weights_data = {
            'timestamp': datetime.now().isoformat(),
            'version': 2,  # V2 with happiness!
            'input_size': self.input_size,
            'hidden_size': self.hidden_size,
            'base_learning_rate': float(self.base_learning_rate),
            'weights_input_hidden': self.weights_input_hidden.tolist(),
            'bias_hidden': self.bias_hidden.tolist(),
            'weights_hidden_output': self.weights_hidden_output.tolist(),
            'bias_output': self.bias_output.tolist(),
            'training_history_count': len(self.training_history),
            'epoch_losses': [float(x) for x in self.epoch_losses[-100:]],
            'joy_trade_count': self.joy_trade_count,
            'total_happiness_earned': self.total_happiness_earned,
        }

        try:
            with open(self.weights_path, 'w') as f:
                json.dump(weights_data, f, indent=2, default=str)
            logger.info(f"👑💾💜 Queen's V2 weights saved (with happiness!) to {self.weights_path}")
        except Exception as e:
            logger.error(f"Failed to save weights: {e}")

    def load_weights(self) -> bool:
        """Load previously learned weights from JSON file."""
        try:
            if not Path(self.weights_path).exists():
                # Try loading v1 weights and upgrading
                return self._try_upgrade_from_v1()

            with open(self.weights_path, 'r') as f:
                weights_data = json.load(f)

            # Check if it's v2 weights
            if weights_data.get('version', 1) >= 2:
                self.weights_input_hidden = np.array(weights_data['weights_input_hidden'], dtype=np.float32)
                self.bias_hidden = np.array(weights_data['bias_hidden'], dtype=np.float32)
                self.weights_hidden_output = np.array(weights_data['weights_hidden_output'], dtype=np.float32)
                self.bias_output = np.array(weights_data['bias_output'], dtype=np.float32)
                self.joy_trade_count = weights_data.get('joy_trade_count', 0)
                self.total_happiness_earned = weights_data.get('total_happiness_earned', 0.0)

                logger.info(f"👑🧠💜 Queen's V2 weights loaded (with happiness!)")
                return True
            else:
                # Upgrade v1 weights
                return self._try_upgrade_from_v1()

        except Exception as e:
            logger.warning(f"Could not load weights: {e}")
            return False

    def _try_upgrade_from_v1(self) -> bool:
        """Try to upgrade from v1 weights (6 inputs to 7 inputs)."""
        v1_path = "queen_neuron_weights.json"
        try:
            if not Path(v1_path).exists():
                return False

            with open(v1_path, 'r') as f:
                v1_data = json.load(f)

            old_weights = np.array(v1_data['weights_input_hidden'], dtype=np.float32)

            # Old weights are 6x12, we need 7x12
            # Add the deterministic HNC row for the verified happiness input.
            phi = (1.0 + np.sqrt(5.0)) / 2.0
            positions = np.arange(6 * self.hidden_size + 1, 7 * self.hidden_size + 1, dtype=np.float32)
            new_row = (np.sin(positions * phi) * np.sqrt(2.0 / (7 + self.hidden_size))).reshape(1, self.hidden_size)
            self.weights_input_hidden = np.vstack([old_weights, new_row])

            self.bias_hidden = np.array(v1_data['bias_hidden'], dtype=np.float32)
            self.weights_hidden_output = np.array(v1_data['weights_hidden_output'], dtype=np.float32)
            self.bias_output = np.array(v1_data['bias_output'], dtype=np.float32)

            logger.info(f"👑🔄💜 Upgraded V1 weights to V2 (added happiness input!)")

            # Save as v2
            self.save_weights()

            return True

        except Exception as e:
            logger.warning(f"Could not upgrade v1 weights: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get Queen's neural status with happiness metrics."""
        status = {
            'version': 2,
            'architecture': f"{self.input_size}-{self.hidden_size}-1 (with happiness!)",
            'base_learning_rate': self.base_learning_rate,
            'effective_learning_rate': self.learning_rate,
            'training_examples': len(self.training_history),
            'epochs_trained': len(self.epoch_losses),
            'last_losses': self.epoch_losses[-5:] if self.epoch_losses else [],
            'weights_path': self.weights_path,
            'happiness_integration': {
                'enabled': self.happiness_engine is not None,
                'current_happiness': self.current_happiness,
                'joy_trade_count': self.joy_trade_count,
                'total_happiness_earned': self.total_happiness_earned,
            }
        }

        if self.happiness_engine:
            status['happiness_integration']['grand_wheel_status'] = self.happiness_engine.get_status()

        return status


# ═══════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def create_queen_neuron_v2(weights_path: str = "queen_neuron_v2_weights.json") -> QueenNeuronV2:
    """Create Queen's V2 neuron with happiness integration."""
    return QueenNeuronV2(weights_path=weights_path)


# Global instance
_queen_v2: Optional[QueenNeuronV2] = None

def get_queen_neuron() -> QueenNeuronV2:
    """Get or create the global Queen Neuron V2."""
    global _queen_v2
    if _queen_v2 is None:
        _queen_v2 = create_queen_neuron_v2()
    return _queen_v2


# ═══════════════════════════════════════════════════════════════════════════
# DEMO
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

    print("\n" + "=" * 70)
    print("👑🧠💜 QUEEN NEURON V2 - WITH PURSUIT OF HAPPINESS 💜🧠👑".center(70))
    print("=" * 70 + "\n")

    # Create Queen
    queen = get_queen_neuron()

    # Print status
    status = queen.get_status()
    print(f"Architecture: {status['architecture']}")
    print(f"Base LR: {status['base_learning_rate']}")
    print(f"Effective LR: {status['effective_learning_rate']:.4f} (happiness-modulated)")
    print(f"Current Happiness: {status['happiness_integration']['current_happiness']:.3f}")

    # Test prediction with happiness
    test_input = NeuralInputV2(
        probability_score=0.7,
        wisdom_score=0.6,
        quantum_signal=0.3,
        gaia_resonance=0.8,
        emotional_coherence=0.65,
        mycelium_signal=0.2,
        happiness_pursuit=0.75,  # 🎡 THE BIG WHY
    )

    confidence = queen.predict(test_input)
    print(f"\n🎯 Trade Confidence: {confidence:.1%}")
    print(f"   (with happiness input: {test_input.happiness_pursuit:.1%})")

    # Simulate a winning trade
    print("\n📊 Simulating winning trade...")
    loss = queen.train_on_example(test_input, outcome=True, profit_usd=5.50)
    print(f"   Loss after training: {loss:.4f}")

    # Check happiness engine
    if queen.happiness_engine:
        print("\n🎡 Grand Big Wheel Status:")
        wheel_status = queen.happiness_engine.get_status()
        print(f"   Happiness Quotient: {wheel_status['happiness_quotient']:.3f}")
        print(f"   Subconscious Bias: {wheel_status['subconscious_bias']:.3f}")
        print(f"   Joy Trades: {queen.joy_trade_count}")

        # Print the wheel
        queen.happiness_engine.print_grand_wheel()

    # Save
    queen.save_weights()
    if queen.happiness_engine:
        queen.happiness_engine.save_state()

    print("\n✅ Queen Neuron V2 demonstration complete!")
    print("   THE PURSUIT OF HAPPINESS IS NOW IN HER SUBCONSCIOUS")
