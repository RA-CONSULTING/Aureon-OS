#!/usr/bin/env python3
"""
Phase Transition Detector
==========================

Detects regime changes in financial markets using geometric analysis
of phase space trajectories. Built on Takens embedding theorem and
Frenet-Serret curvature calculations.

Core Mathematics:
  1. Takens Embedding: Reconstruct d-dimensional phase space from scalar time series
  2. Geodesic Curvature: kappa(t) = ||dT/dt|| / ||dx/dt|| (Frenet-Serret)
  3. Coherence: Autocorrelation decay rate of phase-space distances
  4. Intrinsic Dimension: SVD-based effective dimensionality
  5. Transition Score: Logistic combination of curvature + coherence + dimension

Phase States:
  STABLE      - Low curvature, high coherence (attractor basin)
  ELEVATED    - Rising curvature or falling coherence (approaching boundary)
  CRITICAL    - High curvature, low coherence (phase transition imminent)
  RECOVERY    - Post-transition convergence to new attractor

Gary Leckey | February 2026
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from collections import deque
from enum import Enum

import numpy as np

logger = logging.getLogger(__name__)

# ===========================================================================
# Constants
# ===========================================================================
PHI = (1 + math.sqrt(5)) / 2
DEFAULT_EMBEDDING_DIM = 10
DEFAULT_TIME_DELAY = 1
DEFAULT_MEMORY_LENGTH = 144  # 144 observations (6 days at hourly)
CURVATURE_WARNING_THRESHOLD = 2.0
COHERENCE_SAFE_THRESHOLD = 0.7
TRANSITION_CRITICAL_THRESHOLD = 0.66
TRANSITION_ELEVATED_THRESHOLD = 0.33


class PhaseState(Enum):
    """Current state of the phase-space trajectory."""
    STABLE = "STABLE"
    ELEVATED = "ELEVATED"
    CRITICAL = "CRITICAL"
    RECOVERY = "RECOVERY"
    UNKNOWN = "UNKNOWN"


@dataclass
class PhaseSignature:
    """Complete geometric signature at a point in time."""
    timestamp: float
    coordinates: np.ndarray
    velocity: np.ndarray
    curvature: float
    coherence: float
    intrinsic_dimension: float
    speed: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "curvature": round(self.curvature, 6),
            "coherence": round(self.coherence, 4),
            "dimension": round(self.intrinsic_dimension, 2),
            "speed": round(self.speed, 6),
        }


@dataclass
class TransitionPrediction:
    """Prediction of an imminent phase transition."""
    probability: float
    state: PhaseState
    estimated_time_steps: float
    curvature: float
    coherence: float
    dimension: float
    target_attractor: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "probability": round(self.probability, 4),
            "state": self.state.value,
            "estimated_time_steps": round(self.estimated_time_steps, 1),
            "curvature": round(self.curvature, 6),
            "coherence": round(self.coherence, 4),
            "dimension": round(self.dimension, 2),
            "target_attractor": self.target_attractor,
        }


@dataclass
class PhaseTransitionEvent:
    """A detected phase transition."""
    timestamp: float
    from_state: PhaseState
    to_state: PhaseState
    curvature_at_transition: float
    coherence_at_transition: float
    price_at_transition: float = 0.0
    price_after_24h: float = 0.0


# ===========================================================================
# Phase Space Embedding (Takens' Theorem)
# ===========================================================================

class PhaseSpaceEmbedder:
    """
    Reconstructs a d-dimensional phase space from a scalar time series
    using delay embedding (Takens' theorem, 1981).

    For a scalar signal x(t), the embedded vector is:
      v(t) = [x(t), x(t-tau), x(t-2*tau), ..., x(t-(d-1)*tau)]

    where d is the embedding dimension and tau is the time delay.
    """

    def __init__(self, dimension: int = DEFAULT_EMBEDDING_DIM,
                 time_delay: int = DEFAULT_TIME_DELAY):
        self.dimension = dimension
        self.time_delay = time_delay

    def embed(self, signal: np.ndarray) -> np.ndarray:
        """
        Create delay-coordinate embedding of scalar signal.

        Returns (N - (d-1)*tau) x d matrix of embedded vectors.
        """
        n = len(signal)
        d = self.dimension
        tau = self.time_delay

        rows = n - (d - 1) * tau
        if rows <= 0:
            # Pad signal if too short
            padded = np.pad(signal, (d * tau, 0), mode="edge")
            return padded[-d:].reshape(1, -1)

        embedded = np.zeros((rows, d))
        for i in range(d):
            embedded[:, i] = signal[i * tau: i * tau + rows]

        return embedded


# ===========================================================================
# Geometric Feature Extraction
# ===========================================================================

class GeometricAnalyzer:
    """
    Extracts geometric features from phase-space trajectories.
    """

    @staticmethod
    def compute_curvature(trajectory: np.ndarray) -> np.ndarray:
        """
        Compute geodesic curvature using discrete Frenet-Serret formulas.

        kappa(t) = ||dT/dt|| / ||v(t)||

        where T = v / ||v|| is the unit tangent vector.
        """
        if len(trajectory) < 3:
            return np.zeros(max(1, len(trajectory)))

        # Velocity (first derivative)
        velocity = np.gradient(trajectory, axis=0)
        speed = np.linalg.norm(velocity, axis=1)

        # Unit tangent
        tangent = velocity / (speed[:, np.newaxis] + 1e-12)

        # Rate of change of tangent (second derivative effect)
        dtangent = np.gradient(tangent, axis=0)
        dtangent_norm = np.linalg.norm(dtangent, axis=1)

        # Curvature
        curvature = dtangent_norm / (speed + 1e-12)

        return curvature

    @staticmethod
    def compute_coherence(trajectory: np.ndarray, window: int = 50) -> float:
        """
        Measure trajectory self-similarity via autocorrelation decay.

        High coherence = trajectory stays near attractor (predictable).
        Low coherence = trajectory is chaotic/transitioning.
        """
        n = len(trajectory)
        if n < window:
            logger.warning("[insufficient-data] phase_transition coherence "
                           "returning neutral 0.5 (need %d samples, got %d)",
                           window, n)
            return 0.5

        recent = trajectory[-window:]

        # Compute autocorrelation of pairwise distances at different lags
        max_lag = min(window // 3, 15)
        if max_lag < 2:
            logger.warning("[insufficient-data] phase_transition coherence "
                           "returning neutral 0.5 (window too small for autocorrelation)")
            return 0.5

        distances = []
        for lag in range(1, max_lag + 1):
            dists = [
                np.linalg.norm(recent[i] - recent[i - lag])
                for i in range(lag, len(recent))
            ]
            distances.append(np.mean(dists) if dists else 0.0)

        distances = np.array(distances)
        if len(distances) < 2 or distances.max() < 1e-12:
            logger.warning("[insufficient-data] phase_transition coherence "
                           "returning neutral 0.5 (distances degenerate / max < 1e-12)")
            return 0.5

        # Fit exponential decay: d(lag) ~ A * exp(-lambda * lag)
        log_dist = np.log(distances + 1e-12)
        lags = np.arange(1, len(log_dist) + 1)

        # Simple linear regression on log distances
        coeffs = np.polyfit(lags, log_dist, 1)
        decay_rate = -coeffs[0]  # Negative slope = positive decay

        # Map decay rate to coherence [0, 1]
        # High decay = distances grow fast = low coherence
        # Low/negative decay = distances stable = high coherence
        coherence = 1.0 / (1.0 + abs(decay_rate))

        return float(np.clip(coherence, 0.0, 1.0))

    @staticmethod
    def estimate_dimension(trajectory: np.ndarray) -> float:
        """
        Estimate intrinsic dimensionality of the attractor via SVD.

        Uses inverse participation ratio of singular values:
          d_eff = (sum(s_i))^2 / sum(s_i^2)
        """
        if len(trajectory) < 3:
            return 1.0

        centered = trajectory - trajectory.mean(axis=0)

        try:
            _, s, _ = np.linalg.svd(centered, full_matrices=False)
        except np.linalg.LinAlgError:
            return 1.0

        s_sq = s ** 2
        total = s_sq.sum()
        if total < 1e-12:
            return 1.0

        # Inverse participation ratio
        ipr = total ** 2 / (np.sum(s_sq ** 2) + 1e-12)

        return float(ipr)


# ===========================================================================
# Phase Transition Detector (main engine)
# ===========================================================================

class PhaseTransitionDetector:
    """
    Detects and predicts phase transitions in financial time series.

    Pipeline:
      1. Receive scalar price/return data
      2. Embed in phase space (Takens)
      3. Extract geometric features (curvature, coherence, dimension)
      4. Score transition probability
      5. Classify phase state
      6. Emit prediction

    Usage:
        detector = PhaseTransitionDetector()
        for price in price_stream:
            detector.ingest(price)
            prediction = detector.predict()
            if prediction.state == PhaseState.CRITICAL:
                # Take protective action
    """

    def __init__(
        self,
        embedding_dim: int = DEFAULT_EMBEDDING_DIM,
        time_delay: int = DEFAULT_TIME_DELAY,
        memory_length: int = DEFAULT_MEMORY_LENGTH,
    ):
        self.embedder = PhaseSpaceEmbedder(embedding_dim, time_delay)
        self.analyzer = GeometricAnalyzer()

        self.memory_length = memory_length
        self.embedding_dim = embedding_dim

        # Data buffers
        self.price_buffer: deque = deque(maxlen=memory_length * 2)
        self.return_buffer: deque = deque(maxlen=memory_length * 2)
        self.signature_history: deque = deque(maxlen=500)
        self.transition_history: List[PhaseTransitionEvent] = []

        # Current state
        self.current_state = PhaseState.UNKNOWN
        self._prev_state = PhaseState.UNKNOWN
        self._step_count = 0

        logger.info(
            f"PhaseTransitionDetector initialized: "
            f"dim={embedding_dim}, delay={time_delay}, memory={memory_length}"
        )

    def ingest(self, price: float, timestamp: float = 0.0) -> Optional[PhaseSignature]:
        """
        Ingest a new price observation.

        Returns a PhaseSignature if enough data has accumulated,
        otherwise None.
        """
        self.price_buffer.append(price)
        self._step_count += 1

        if len(self.price_buffer) < 2:
            return None

        # Log return
        prev_price = self.price_buffer[-2]
        if prev_price > 0:
            log_return = math.log(price / prev_price)
        else:
            log_return = 0.0
        self.return_buffer.append(log_return)

        # Need enough returns for embedding
        if len(self.return_buffer) < self.memory_length:
            return None

        ts = timestamp if timestamp > 0 else float(self._step_count)

        # Extract signature
        returns = np.array(list(self.return_buffer))[-self.memory_length:]
        signature = self._extract_signature(returns, ts)

        if signature is not None:
            self.signature_history.append(signature)

        return signature

    def _extract_signature(
        self, returns: np.ndarray, timestamp: float
    ) -> Optional[PhaseSignature]:
        """Extract geometric signature from return window."""
        # Phase space embedding
        trajectory = self.embedder.embed(returns)

        if len(trajectory) < 3:
            return None

        # Geometric features
        curvature_array = self.analyzer.compute_curvature(trajectory)
        current_curvature = float(curvature_array[-1]) if len(curvature_array) > 0 else 0.0

        coherence = self.analyzer.compute_coherence(trajectory)
        dimension = self.analyzer.estimate_dimension(trajectory)

        # Current position and velocity
        position = trajectory[-1]
        velocity = trajectory[-1] - trajectory[-2] if len(trajectory) > 1 else np.zeros(self.embedding_dim)
        speed = float(np.linalg.norm(velocity))

        return PhaseSignature(
            timestamp=timestamp,
            coordinates=position,
            velocity=velocity,
            curvature=current_curvature,
            coherence=coherence,
            intrinsic_dimension=dimension,
            speed=speed,
        )

    def predict(self) -> Optional[TransitionPrediction]:
        """
        Generate transition prediction from current state.
        """
        if not self.signature_history:
            return None

        sig = self.signature_history[-1]

        # Score: logistic combination of instability indicators
        # High curvature + low coherence + high dimension = unstable
        raw_score = (
            1.6 * sig.curvature
            + 0.35 * sig.intrinsic_dimension / self.embedding_dim
            + 1.5 * (1.0 - sig.coherence)
            - 2.2
        )
        probability = 1.0 / (1.0 + math.exp(-raw_score))

        # Classify state
        if probability >= TRANSITION_CRITICAL_THRESHOLD:
            state = PhaseState.CRITICAL
        elif probability >= TRANSITION_ELEVATED_THRESHOLD:
            state = PhaseState.ELEVATED
        else:
            state = PhaseState.STABLE

        # Detect state transitions
        if state != self._prev_state:
            self._on_state_change(self._prev_state, state, sig)
        self._prev_state = state
        self.current_state = state

        # Time estimate: higher curvature + speed = sooner transition
        if sig.curvature > 0 and sig.speed > 0:
            est_time = 1.0 / (sig.curvature * sig.speed + 1e-10)
        else:
            est_time = float("inf")

        # Find nearest historical attractor
        target = self._classify_target(sig)

        return TransitionPrediction(
            probability=probability,
            state=state,
            estimated_time_steps=est_time,
            curvature=sig.curvature,
            coherence=sig.coherence,
            dimension=sig.intrinsic_dimension,
            target_attractor=target,
        )

    def _classify_target(self, current: PhaseSignature) -> Optional[str]:
        """Classify target attractor based on trajectory direction."""
        if len(self.signature_history) < 10:
            return None

        # Recent coherence trend
        recent = list(self.signature_history)[-10:]
        coherence_trend = recent[-1].coherence - recent[0].coherence

        if coherence_trend > 0.05:
            return "STABILIZING"
        elif coherence_trend < -0.05:
            return "DESTABILIZING"
        else:
            return "NEUTRAL"

    def _on_state_change(
        self,
        from_state: PhaseState,
        to_state: PhaseState,
        sig: PhaseSignature,
    ):
        """Handle phase state transition."""
        event = PhaseTransitionEvent(
            timestamp=sig.timestamp,
            from_state=from_state,
            to_state=to_state,
            curvature_at_transition=sig.curvature,
            coherence_at_transition=sig.coherence,
        )
        self.transition_history.append(event)

        logger.info(
            f"Phase transition: {from_state.value} -> {to_state.value} "
            f"(kappa={sig.curvature:.4f}, gamma={sig.coherence:.4f})"
        )

        # Publish to ThoughtBus if available
        self._publish_transition(event)

    def _publish_transition(self, event: PhaseTransitionEvent):
        """Publish transition event to ThoughtBus."""
        try:
            from aureon.core.aureon_thought_bus import get_thought_bus, Thought
            bus = get_thought_bus()
            if bus is not None:
                # Thought carries payload/meta — the old data=/confidence= kwargs
                # raised TypeError into the except below, so this topic had never
                # actually been emitted.
                bus.publish(Thought(
                    source="phase_transition_detector",
                    topic="phase.transition.detected",
                    payload={
                        "from_state": event.from_state.value,
                        "to_state": event.to_state.value,
                        "curvature": event.curvature_at_transition,
                        "coherence": event.coherence_at_transition,
                    },
                    meta={"confidence": 0.8},
                ))
        except Exception:
            pass

    def get_navigation_signal(self) -> str:
        """
        Simple trading signal based on phase geometry.

        Returns: "ENTER", "EXIT", or "HOLD"
        """
        prediction = self.predict()
        if prediction is None:
            return "HOLD"

        if prediction.state == PhaseState.CRITICAL and prediction.coherence < 0.4:
            return "EXIT"
        elif prediction.state == PhaseState.STABLE and prediction.coherence > 0.8:
            return "ENTER"
        else:
            return "HOLD"

    def get_status(self) -> Dict[str, Any]:
        """Return current detector status."""
        prediction = self.predict()
        return {
            "state": self.current_state.value,
            "observations": self._step_count,
            "signatures_computed": len(self.signature_history),
            "transitions_detected": len(self.transition_history),
            "current_prediction": prediction.to_dict() if prediction else None,
            "navigation_signal": self.get_navigation_signal(),
        }


# ===========================================================================
# Multi-Symbol Phase Monitor
# ===========================================================================

class MultiSymbolPhaseMonitor:
    """
    Monitor phase transitions across multiple symbols simultaneously.

    Detects correlated transitions (system-wide regime changes).
    """

    def __init__(self, symbols: List[str]):
        self.symbols = symbols
        self.detectors: Dict[str, PhaseTransitionDetector] = {
            sym: PhaseTransitionDetector() for sym in symbols
        }
        self._global_state = PhaseState.UNKNOWN

    def ingest(self, symbol: str, price: float, timestamp: float = 0.0):
        """Ingest price for a specific symbol."""
        if symbol in self.detectors:
            self.detectors[symbol].ingest(price, timestamp)

    def scan_all(self) -> Dict[str, Any]:
        """Scan all symbols for phase transitions."""
        results = {}
        states = []

        for sym, detector in self.detectors.items():
            prediction = detector.predict()
            if prediction is not None:
                results[sym] = prediction.to_dict()
                states.append(prediction.state)

        # Global state: most critical state across symbols
        if PhaseState.CRITICAL in states:
            self._global_state = PhaseState.CRITICAL
        elif PhaseState.ELEVATED in states:
            self._global_state = PhaseState.ELEVATED
        else:
            self._global_state = PhaseState.STABLE

        # Count by state
        state_counts = {}
        for s in states:
            state_counts[s.value] = state_counts.get(s.value, 0) + 1

        return {
            "global_state": self._global_state.value,
            "state_distribution": state_counts,
            "symbols_monitored": len(self.symbols),
            "symbols_with_data": len(results),
            "per_symbol": results,
        }


# ===========================================================================
# Standalone test
# ===========================================================================
