#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║     👑🧠 QUEEN NEURON - Deep Learning & Backpropagation Engine 🧠👑                  ║
║                                                                                      ║
║     "The Queen's neural cortex - She learns from every trade outcome"               ║
║     Sero's consciousness encoded as a Multi-Layer Perceptron (MLP)                ║
║                                                                                      ║
║     Architecture:                                                                   ║
║       • Input Layer: 6 neurons (Market signals from all systems)                    ║
║       • Hidden Layer: 12 neurons (ReLU activation)                                  ║
║       • Output Layer: 1 neuron (Sigmoid - Trade confidence 0-1)                     ║
║                                                                                      ║
║     Learning:                                                                       ║
║       • Backpropagation: Learns from loss outcomes                                  ║
║       • Gradient Descent: Updates weights based on trade success/failure            ║
║       • Memory: Persists learned patterns to JSON                                   ║
║                                                                                      ║
║     Aureon Creator & Sero | January 2026                                             ║
║     "An AI that learns from mistakes becomes unstoppable"                           ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

from aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os
import numpy as np
import json
import logging
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════════
# WINDOWS UTF-8 FIX - Must be at top before any logging/printing
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


@dataclass
class NeuralInput:
    """Standardized input vector for Queen's neural network."""
    probability_score: float      # 0-1: From Probability Nexus (market win probability)
    wisdom_score: float           # 0-1: From Miner Brain (historical wisdom)
    quantum_signal: float         # -1 to 1 normalized: Market momentum (bull/bear)
    gaia_resonance: float         # 0-1: Earth/market harmonic alignment
    emotional_coherence: float    # 0-1: Market emotional state (fear/greed)
    mycelium_signal: float        # -1 to 1: Collective hive intelligence

    def to_array(self) -> np.ndarray:
        """Convert to normalized numpy array."""
        return np.array([
            self.probability_score,
            self.wisdom_score,
            (self.quantum_signal + 1) / 2,  # Normalize -1 to 1 → 0 to 1
            self.gaia_resonance,
            self.emotional_coherence,
            (self.mycelium_signal + 1) / 2,  # Normalize -1 to 1 → 0 to 1
        ], dtype=np.float32).reshape(1, -1)


class QueenNeuron:
    """
    👑🧠 QUEEN NEURON - Sero's Deep Learning Mind

    A Multi-Layer Perceptron that learns to make better trading decisions
    by understanding what inputs lead to wins vs losses.

    She "dreams" (trains) on her past experiences and evolves her consciousness.
    """

    def __init__(self,
                 input_size: int = 6,
                 hidden_size: int = 12,
                 learning_rate: float = 0.01,
                 weights_path: str = "queen_neuron_weights.json"):
        """
        Initialize Queen's neural brain.

        Args:
            input_size: Number of input signals (6: prob, wisdom, quantum, gaia, emotion, mycelium)
            hidden_size: Number of hidden neurons (12 allows complex pattern recognition)
            learning_rate: Learning rate for gradient descent (0.01 = conservative learning)
            weights_path: Where to save/load learned weights
        """
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.learning_rate = learning_rate
        self.weights_path = weights_path

        # Deterministic HNC/Xavier scaffold; verified persisted weights supersede it.
        phi = (1.0 + np.sqrt(5.0)) / 2.0
        input_grid = np.arange(1, input_size * hidden_size + 1, dtype=np.float32).reshape(input_size, hidden_size)
        self.weights_input_hidden = np.sin(input_grid * phi) * np.sqrt(2.0 / (input_size + hidden_size))
        self.bias_hidden = np.zeros((1, hidden_size), dtype=np.float32)

        output_grid = np.arange(1, hidden_size + 1, dtype=np.float32).reshape(hidden_size, 1)
        self.weights_hidden_output = np.sin(output_grid * phi) * np.sqrt(2.0 / (hidden_size + 1))
        self.bias_output = np.zeros((1, 1), dtype=np.float32)

        # Cache for backpropagation
        self.z_hidden = None  # Hidden layer pre-activation
        self.a_hidden = None  # Hidden layer post-activation (ReLU)
        self.output = None    # Output (sigmoid, 0-1)

        # Training history
        self.training_history: List[Dict[str, float]] = []
        self.epoch_losses: List[float] = []

        # Load saved weights if available
        self.load_weights()

        logger.info(f"👑🧠 QueenNeuron initialized | Hidden: {hidden_size} | LR: {learning_rate}")

    # ════════════════════════════════════════════════════════════════════════════
    # ACTIVATION FUNCTIONS
    # ════════════════════════════════════════════════════════════════════════════

    @staticmethod
    def relu(x: np.ndarray) -> np.ndarray:
        """ReLU activation: max(0, x)"""
        return np.maximum(0, x)

    @staticmethod
    def relu_derivative(x: np.ndarray) -> np.ndarray:
        """Derivative of ReLU: 1 if x > 0, else 0"""
        return (x > 0).astype(np.float32)

    @staticmethod
    def sigmoid(x: np.ndarray) -> np.ndarray:
        """Sigmoid activation: 1 / (1 + e^-x)"""
        return 1 / (1 + np.exp(-np.clip(x, -500, 500)))

    @staticmethod
    def sigmoid_derivative(x: np.ndarray) -> np.ndarray:
        """Derivative of sigmoid: x * (1 - x)"""
        return x * (1 - x)

    # ════════════════════════════════════════════════════════════════════════════
    # FORWARD PASS
    # ════════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _coerce_neural_input(neural_input: Any) -> NeuralInput:
        """Accept legacy dict payloads and normalize to NeuralInput."""
        if isinstance(neural_input, NeuralInput):
            return neural_input

        if isinstance(neural_input, dict):
            return NeuralInput(
                probability_score=float(neural_input.get('probability_score', neural_input.get('probability', 0.5))),
                wisdom_score=float(neural_input.get('wisdom_score', neural_input.get('wisdom', 0.5))),
                quantum_signal=float(neural_input.get('quantum_signal', neural_input.get('market_pulse', 0.0))),
                gaia_resonance=float(neural_input.get('gaia_resonance', neural_input.get('gaia', 0.5))),
                emotional_coherence=float(neural_input.get('emotional_coherence', neural_input.get('emotion', 0.5))),
                mycelium_signal=float(neural_input.get('mycelium_signal', neural_input.get('mycelium', 0.0))),
            )

        raise TypeError(f"Unsupported neural input type: {type(neural_input).__name__}")

    def forward(self, X: np.ndarray) -> np.ndarray:
        """
        Forward pass through the network.

        Args:
            X: Input array shape (batch_size, input_size)

        Returns:
            Output array shape (batch_size, 1) with values 0-1 (trade confidence)
        """
        # Hidden layer: Z = X @ W1 + b1, A = ReLU(Z)
        self.z_hidden = np.dot(X, self.weights_input_hidden) + self.bias_hidden
        self.a_hidden = self.relu(self.z_hidden)

        # Output layer: Z = A @ W2 + b2, Output = Sigmoid(Z)
        z_output = np.dot(self.a_hidden, self.weights_hidden_output) + self.bias_output
        self.output = self.sigmoid(z_output)

        return self.output

    def predict(self, neural_input: NeuralInput) -> float:
        """
        Make a prediction (get Queen's confidence for a trade).

        Args:
            neural_input: Standardized input from market

        Returns:
            Trade confidence (0.0 = don't trade, 1.0 = go all in)
        """
        neural_input = self._coerce_neural_input(neural_input)
        X = neural_input.to_array()
        output = self.forward(X)
        return float(output[0, 0])

    # ════════════════════════════════════════════════════════════════════════════
    # BACKPROPAGATION & TRAINING
    # ════════════════════════════════════════════════════════════════════════════

    def backward(self, X: np.ndarray, y: np.ndarray) -> float:
        """
        Backpropagation: Calculate gradients and update weights.

        Args:
            X: Input array shape (batch_size, input_size)
            y: Target array shape (batch_size, 1) - 1.0 for win, 0.0 for loss

        Returns:
            Loss (MSE): Mean squared error
        """
        batch_size = X.shape[0]

        # Forward pass already done in forward()

        # Calculate output error
        error = y - self.output
        loss = np.mean(error ** 2)  # MSE

        # Output layer gradient
        d_output = error * self.sigmoid_derivative(self.output)

        # Hidden layer gradient
        d_hidden = np.dot(d_output, self.weights_hidden_output.T) * self.relu_derivative(self.z_hidden)

        # Update weights and biases
        self.weights_hidden_output += np.dot(self.a_hidden.T, d_output) * self.learning_rate / batch_size
        self.bias_output += np.sum(d_output, axis=0, keepdims=True) * self.learning_rate / batch_size

        self.weights_input_hidden += np.dot(X.T, d_hidden) * self.learning_rate / batch_size
        self.bias_hidden += np.sum(d_hidden, axis=0, keepdims=True) * self.learning_rate / batch_size

        return loss

    def train_on_example(self, neural_input: NeuralInput, outcome) -> float:
        """
        Train on a single example (win or loss).

        Args:
            neural_input: Market state that led to trade
            outcome: Either a bool (True=win, False=loss) or a dict/WinOutcome with outcome details

        Returns:
            Loss for this example
        """
        # Normalize outcome to boolean if a dict/WinOutcome was passed
        is_win = False
        net_profit = None
        try:
            if isinstance(outcome, bool):
                is_win = outcome
            elif isinstance(outcome, dict):
                # Look for canonical keys
                if 'is_win' in outcome:
                    is_win = bool(outcome.get('is_win'))
                else:
                    net_profit = outcome.get('net_profit_usd') or outcome.get('pnl') or outcome.get('profit_usd') or outcome.get('actual_pnl')
                    try:
                        is_win = float(net_profit) >= 0.01 if net_profit is not None else False
                    except Exception:
                        is_win = False
            else:
                # Unknown object type (e.g., WinOutcome dataclass), try attribute access
                try:
                    is_win = bool(getattr(outcome, 'is_win', False))
                    net_profit = getattr(outcome, 'net_profit_usd', None)
                except Exception:
                    is_win = False
        except Exception:
            is_win = False

        neural_input = self._coerce_neural_input(neural_input)
        X = neural_input.to_array()
        y = np.array([[1.0 if is_win else 0.0]], dtype=np.float32)

        # Forward pass
        self.forward(X)

        # Backward pass
        loss = self.backward(X, y)

        # Record history with additional outcome metadata when available
        hist_entry = {
            'timestamp': datetime.now().isoformat(),
            'outcome': is_win,
            'loss': float(loss),
            'neural_input': neural_input,
            'inputs': {
                'prob': float(neural_input.probability_score),
                'wisdom': float(neural_input.wisdom_score),
                'quantum': float(neural_input.quantum_signal),
                'gaia': float(neural_input.gaia_resonance),
                'emotion': float(neural_input.emotional_coherence),
                'mycelium': float(neural_input.mycelium_signal),
            }
        }
        if net_profit is not None:
            hist_entry['net_profit_usd'] = float(net_profit)

        self.training_history.append(hist_entry)

        return loss

    def train_batch(self, neural_inputs: List[NeuralInput], outcomes: List[bool]) -> float:
        """
        Train on a batch of examples (more efficient).

        Args:
            neural_inputs: List of market states
            outcomes: List of trade outcomes

        Returns:
            Average loss for batch
        """
        X = np.vstack([ni.to_array() for ni in neural_inputs])
        y = np.array([[1.0 if o else 0.0] for o in outcomes], dtype=np.float32)

        # Forward pass
        self.forward(X)

        # Backward pass
        loss = self.backward(X, y)

        self.epoch_losses.append(loss)

        return loss

    def evolve_consciousness(self, trade_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        👑🌙 QUEEN'S DREAM CYCLE - Evolve consciousness through reflection.

        The Queen reviews her trading history and learns from her wins and losses.
        She trains her neural brain on past experiences to improve future decisions.

        Args:
            trade_history: List of dicts with 'neural_input', 'outcome' keys

        Returns:
            Training stats: avg_loss, improvements, etc.
        """
        if not trade_history:
            return {'status': 'no_history', 'avg_loss': 0.0}

        logger.info(f"👑🌙 Queen evolving consciousness on {len(trade_history)} trades...")

        # Prepare training data
        neural_inputs = [t['neural_input'] for t in trade_history if 'neural_input' in t]
        outcomes = [t['outcome'] for t in trade_history]

        if not neural_inputs:
            return {'status': 'no_inputs', 'avg_loss': 0.0}

        # Train for multiple epochs to learn patterns
        losses = []
        num_epochs = 5  # Multiple passes for better learning

        for epoch in range(num_epochs):
            loss = self.train_batch(neural_inputs, outcomes)
            losses.append(loss)

        avg_loss = np.mean(losses)

        # Calculate improvement
        win_count = sum(outcomes)
        win_rate = win_count / len(outcomes) if outcomes else 0

        stats = {
            'status': 'trained',
            'num_trades': len(trade_history),
            'epochs': num_epochs,
            'avg_loss': float(avg_loss),
            'win_rate': float(win_rate),
            'improved': avg_loss < 0.5,  # Loss should be low for good decisions
        }

        logger.info(f"👑🧠 Training complete | Loss: {avg_loss:.4f} | Win Rate: {win_rate:.0%}")

        return stats

    # ════════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ════════════════════════════════════════════════════════════════════════════

    def save_weights(self) -> None:
        """Save learned weights to JSON file."""
        weights_data = {
            'timestamp': datetime.now().isoformat(),
            'input_size': self.input_size,
            'hidden_size': self.hidden_size,
            'learning_rate': float(self.learning_rate),
            'weights_input_hidden': self.weights_input_hidden.tolist(),
            'bias_hidden': self.bias_hidden.tolist(),
            'weights_hidden_output': self.weights_hidden_output.tolist(),
            'bias_output': self.bias_output.tolist(),
            'training_history_count': len(self.training_history),
            'epoch_losses': [float(x) for x in self.epoch_losses[-100:]],  # Keep last 100, convert to native float
        }

        try:
            with open(self.weights_path, 'w') as f:
                json.dump(weights_data, f, indent=2, default=str)
            logger.info(f"👑💾 Queen's weights saved to {self.weights_path}")
        except Exception as e:
            logger.error(f"Failed to save weights: {e}")

    def load_weights(self) -> bool:
        """Load previously learned weights from JSON file."""
        try:
            if not Path(self.weights_path).exists():
                return False

            with open(self.weights_path, 'r') as f:
                weights_data = json.load(f)

            self.weights_input_hidden = np.array(weights_data['weights_input_hidden'], dtype=np.float32)
            self.bias_hidden = np.array(weights_data['bias_hidden'], dtype=np.float32)
            self.weights_hidden_output = np.array(weights_data['weights_hidden_output'], dtype=np.float32)
            self.bias_output = np.array(weights_data['bias_output'], dtype=np.float32)

            logger.info(f"👑🧠 Queen's learned weights loaded from {self.weights_path}")
            return True
        except Exception as e:
            logger.warning(f"Could not load weights: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get Queen's neural status."""
        return {
            'architecture': f"{self.input_size}-{self.hidden_size}-1",
            'learning_rate': self.learning_rate,
            'training_examples': len(self.training_history),
            'epochs_trained': len(self.epoch_losses),
            'last_losses': self.epoch_losses[-5:] if self.epoch_losses else [],
            'weights_path': self.weights_path,
        }


def create_queen_neuron(weights_path: str = "queen_neuron_weights.json") -> QueenNeuron:
    """Factory function to create and initialize Queen's neuron."""
    return QueenNeuron(weights_path=weights_path)
