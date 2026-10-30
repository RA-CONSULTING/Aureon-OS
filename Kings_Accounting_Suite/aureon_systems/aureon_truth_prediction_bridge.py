#!/usr/bin/env python3
"""
🌉 TRUTH PREDICTION BRIDGE - Orca ↔ Truth Engine Connection 🌉

Purpose:
- Read validated predictions from Truth Prediction Engine state file
- Provide simple API for Orca to check if trading is approved
- Block trades that contradict Truth Engine predictions
- Feed Truth Engine intelligence into Orca's decision gates

⚠️ This bridges REAL intelligence into trading decisions.
"""

from aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

STATE_FILE = Path("aureon_truth_prediction_state.json")
PHI = 1.618033988749895
MIN_CONFIDENCE = 0.65
MIN_RESONANCE = 0.618  # Golden ratio threshold


@dataclass
class TruthSignal:
    """Signal from Truth Engine about whether to trade a symbol."""
    approved: bool
    reason: str
    win_probability: float
    confidence: float
    predicted_direction: str  # "UP", "DOWN", "FLAT"
    auris_resonance: float
    queen_approved: bool
    age_seconds: float


class TruthPredictionBridge:
    """
    Bridge between Truth Prediction Engine and Orca trading system.

    Usage in Orca:
        bridge = TruthPredictionBridge()
        signal = bridge.get_trading_signal("BTCUSD", intended_direction="BUY")
        if not signal.approved:
            # Block trade - Truth Engine says no
            return {"approved": False, "reason": signal.reason}
    """

    def __init__(self):
        self.last_state: Dict = {}
        self.last_read_time = 0.0
        self.cache_ttl = 2.0  # Re-read every 2 seconds

    def _read_state(self) -> Dict:
        """Read current prediction state from file."""
        now = time.time()

        # Use cache if fresh
        if now - self.last_read_time < self.cache_ttl and self.last_state:
            return self.last_state

        try:
            if not STATE_FILE.exists():
                return {"predictions": {}, "validations": [], "last_updated": 0}

            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            self.last_state = state
            self.last_read_time = now
            return state

        except Exception as e:
            # Return empty on error
            return {"predictions": {}, "validations": [], "last_updated": 0}

    def get_trading_signal(
        self,
        symbol: str,
        intended_direction: str = "BUY",  # "BUY" or "SELL"
        max_age_seconds: float = 60.0
    ) -> TruthSignal:
        """
        Get Truth Engine's signal for trading this symbol.

        Args:
            symbol: Trading symbol (e.g., "BTCUSD", "BTC")
            intended_direction: "BUY" or "SELL" - what Orca wants to do
            max_age_seconds: Maximum age of prediction to consider valid

        Returns:
            TruthSignal with approved=True if Truth Engine approves trade
        """
        state = self._read_state()
        now = time.time()

        # Check if we have predictions for this symbol
        symbol_preds = state.get("predictions", {}).get(symbol, [])

        if not symbol_preds:
            # No predictions - BLOCK (need validated intelligence)
            return TruthSignal(
                approved=False,
                reason="NO_TRUTH_ENGINE_PREDICTIONS",
                win_probability=0.0,
                confidence=0.0,
                predicted_direction="UNKNOWN",
                auris_resonance=0.0,
                queen_approved=False,
                age_seconds=9999.0
            )

        # Find most recent non-validated prediction (current state)
        current_pred = None
        for pred in reversed(symbol_preds):
            if not pred.get("validated", False):
                current_pred = pred
                break

        # If no current prediction, use most recent validated one
        if not current_pred and symbol_preds:
            current_pred = symbol_preds[-1]

        if not current_pred:
            return TruthSignal(
                approved=False,
                reason="NO_VALID_PREDICTIONS",
                win_probability=0.0,
                confidence=0.0,
                predicted_direction="UNKNOWN",
                auris_resonance=0.0,
                queen_approved=False,
                age_seconds=9999.0
            )

        # Check age
        pred_age = now - current_pred.get("start_time", 0)
        if pred_age > max_age_seconds:
            return TruthSignal(
                approved=False,
                reason=f"PREDICTION_TOO_OLD ({pred_age:.1f}s > {max_age_seconds}s)",
                win_probability=current_pred.get("win_probability", 0.0),
                confidence=current_pred.get("pattern_confidence", 0.0),
                predicted_direction=current_pred.get("predicted_direction", "UNKNOWN"),
                auris_resonance=current_pred.get("auris_resonance", 0.0),
                queen_approved=current_pred.get("queen_approved", False),
                age_seconds=pred_age
            )

        # Extract prediction data
        win_prob = current_pred.get("win_probability", 0.0)
        confidence = current_pred.get("pattern_confidence", 0.0)
        predicted_dir = current_pred.get("predicted_direction", "FLAT")
        auris_resonance = current_pred.get("auris_resonance", 0.0)
        queen_approved = current_pred.get("queen_approved", False)
        auris_approved = current_pred.get("auris_approved", False)

        # Gate 1: Queen must approve (win_probability ≥ 0.65)
        if not queen_approved or win_prob < MIN_CONFIDENCE:
            return TruthSignal(
                approved=False,
                reason=f"QUEEN_REJECTED (win_prob={win_prob:.3f} < {MIN_CONFIDENCE})",
                win_probability=win_prob,
                confidence=confidence,
                predicted_direction=predicted_dir,
                auris_resonance=auris_resonance,
                queen_approved=False,
                age_seconds=pred_age
            )

        # Gate 2: Auris must approve (resonance ≥ φ = 0.618)
        if not auris_approved or auris_resonance < MIN_RESONANCE:
            return TruthSignal(
                approved=False,
                reason=f"AURIS_REJECTED (resonance={auris_resonance:.3f} < {MIN_RESONANCE})",
                win_probability=win_prob,
                confidence=confidence,
                predicted_direction=predicted_dir,
                auris_resonance=auris_resonance,
                queen_approved=queen_approved,
                age_seconds=pred_age
            )

        # Gate 3: Pattern confidence must be sufficient
        if confidence < MIN_CONFIDENCE:
            return TruthSignal(
                approved=False,
                reason=f"LOW_PATTERN_CONFIDENCE ({confidence:.3f} < {MIN_CONFIDENCE})",
                win_probability=win_prob,
                confidence=confidence,
                predicted_direction=predicted_dir,
                auris_resonance=auris_resonance,
                queen_approved=queen_approved,
                age_seconds=pred_age
            )

        # Gate 4: Direction alignment check
        # BUY requires UP or FLAT prediction
        # SELL requires DOWN or FLAT prediction
        direction_ok = False
        if intended_direction == "BUY":
            direction_ok = predicted_dir in ["UP", "FLAT"]
        elif intended_direction == "SELL":
            direction_ok = predicted_dir in ["DOWN", "FLAT"]
        else:
            direction_ok = True  # Unknown direction = allow

        if not direction_ok:
            return TruthSignal(
                approved=False,
                reason=f"DIRECTION_CONFLICT ({intended_direction} vs predicted {predicted_dir})",
                win_probability=win_prob,
                confidence=confidence,
                predicted_direction=predicted_dir,
                auris_resonance=auris_resonance,
                queen_approved=queen_approved,
                age_seconds=pred_age
            )

        # All gates passed - APPROVED
        return TruthSignal(
            approved=True,
            reason="TRUTH_ENGINE_APPROVED",
            win_probability=win_prob,
            confidence=confidence,
            predicted_direction=predicted_dir,
            auris_resonance=auris_resonance,
            queen_approved=queen_approved,
            age_seconds=pred_age
        )

    def get_validation_stats(self, symbol: Optional[str] = None) -> Dict:
        """Get validation statistics (accuracy) from Truth Engine."""
        state = self._read_state()
        validations = state.get("validations", [])

        if symbol:
            validations = [v for v in validations if v.get("symbol") == symbol]

        if not validations:
            return {
                "total": 0,
                "correct": 0,
                "accuracy": 0.0,
                "avg_geometric_truth": 0.0
            }

        total = len(validations)
        correct = sum(1 for v in validations if v.get("correct", False))
        avg_truth = sum(v.get("geometric_truth", 0.0) for v in validations) / total

        return {
            "total": total,
            "correct": correct,
            "accuracy": (correct / total * 100.0) if total > 0 else 0.0,
            "avg_geometric_truth": avg_truth
        }


# Global singleton
_bridge = None

def get_truth_bridge() -> TruthPredictionBridge:
    """Get global Truth Prediction Bridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = TruthPredictionBridge()
    return _bridge


if __name__ == "__main__":
    print("🌉 Truth Prediction Bridge - Test Mode")
    print("=" * 60)

    bridge = get_truth_bridge()

    # Test signal check
    test_symbols = ["BTCUSD", "BTC", "ETHUSD", "ETH"]

    for symbol in test_symbols:
        signal = bridge.get_trading_signal(symbol, "BUY")
        print(f"\n{symbol} BUY signal:")
        print(f"  Approved: {signal.approved}")
        print(f"  Reason: {signal.reason}")
        if signal.approved:
            print(f"  Win Probability: {signal.win_probability:.1%}")
            print(f"  Confidence: {signal.confidence:.1%}")
            print(f"  Predicted: {signal.predicted_direction}")
            print(f"  Auris Resonance: {signal.auris_resonance:.3f}")

    # Show validation stats
    stats = bridge.get_validation_stats()
    print(f"\n📊 Overall Validation Stats:")
    print(f"  Total: {stats['total']}")
    print(f"  Correct: {stats['correct']}")
    print(f"  Accuracy: {stats['accuracy']:.1f}%")
    print(f"  Avg Geometric Truth: {stats['avg_geometric_truth']:.3f}")

    print("\n" + "=" * 60)
