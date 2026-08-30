#!/usr/bin/env python3
"""
🎯🔮 AUREON TRUTH PREDICTION ENGINE 🔮🎯

CRITICAL: This is NOT a fortune teller. This is a VALIDATION SYSTEM.

Purpose:
- Use Queen's probability matrices + Dr. Auris validation
- Integrate harmonic resonance analysis (Hz frequencies)
- Generate predictions based on REAL MARKET INTELLIGENCE
- Validate predictions against actual outcomes
- Expose receipt-backed validation results without mutating a learning system

⚠️ REAL DATA ONLY. NO SIMULATIONS. NO LINEAR GUESSES.
"""

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple, Union

# Sacred constants
PHI = (1 + math.sqrt(5)) / 2
SCHUMANN_BASE = 7.83
LOVE_FREQUENCY = 528.0
PERFECTION_ANGLE = 306.0  # 360° - 54° golden angle
@dataclass
class MarketSnapshot:
    """Current market state for a symbol."""
    symbol: str
    price: float
    change_24h: float
    volume_24h: float
    momentum_30s: float  # % change over 30s
    volatility_30s: float  # Standard deviation as %
    hz_frequency: float  # Harmonic encoding
    timestamp: float


@dataclass(frozen=True)
class NoDataPrediction:
    """Falsey, numeric-free refusal returned when provenance is incomplete."""

    data_status: str
    truth_status: str
    reason: str
    eligible_for_action: bool
    eligible_for_accounting: bool
    eligible_for_learning: bool
    generated_values: bool

    def __bool__(self) -> bool:
        return False


class PredictionValidationBatch(list):
    """List-compatible validation response with explicit provenance status."""

    def __init__(
        self,
        values: Iterable["TruthPrediction"] = (),
        *,
        data_status: str,
        truth_status: str,
        reason: str,
        eligible_for_learning: bool,
    ) -> None:
        super().__init__(values)
        self.data_status = data_status
        self.truth_status = truth_status
        self.reason = reason
        self.eligible_for_learning = eligible_for_learning
        self.generated_values = False


@dataclass
class TruthPrediction:
    """A prediction with FULL validation chain."""
    symbol: str
    start_time: float
    start_price: float

    # Probability intelligence
    win_probability: float  # From Queen's matrices
    pattern_key: Tuple[str, str, str, str, str]  # 5D pattern
    pattern_confidence: float

    # Dr. Auris validation
    auris_approved: bool
    auris_resonance: float  # 0-1

    # Harmonic analysis
    hz_strength: float  # Signal strength
    hz_band: str  # Schumann/Alpha/Beta/Gamma/Solfeggio

    # Prediction
    predicted_direction: str  # "UP", "DOWN", "FLAT"
    predicted_change_pct: float
    horizon_seconds: float

    # Complete linked provider provenance
    market_receipt_id: str
    hnc_receipt_id: str
    auris_receipt_id: str

    # Validation (filled later)
    validated: bool = False
    actual_price: Optional[float] = None
    actual_change_pct: Optional[float] = None
    correct: Optional[bool] = None

    # Truth metrics
    queen_approved: bool = False
    geometric_truth: Optional[float] = None  # From crystallization


PredictionResult = Union[TruthPrediction, NoDataPrediction]


class TruthPredictionEngine:
    """
    Truth-based prediction engine using ALL validation layers.

    Workflow:
    1. Read market snapshot (price, momentum, volatility, volume)
    2. Query Queen's probability matrices for win probability
    3. Run Dr. Auris validation on prediction reasoning
    4. Check harmonic resonance (Hz analysis)
    5. Generate prediction ONLY if all 3 layers approve
    6. Validate prediction after horizon elapsed
    7. Return the validated outcome for an explicit downstream learning gate
    """

    def __init__(self, *, max_receipt_age_seconds: float = 30.0):
        if not self._is_finite_number(max_receipt_age_seconds) or max_receipt_age_seconds <= 0:
            raise ValueError("max_receipt_age_seconds must be finite and positive")
        self.max_receipt_age_seconds = float(max_receipt_age_seconds)
        self.pending_predictions: Dict[str, List[TruthPrediction]] = {}
        self.validated_predictions: List[TruthPrediction] = []

    @staticmethod
    def _is_finite_number(value: Any) -> bool:
        return (
            not isinstance(value, bool)
            and isinstance(value, (int, float))
            and math.isfinite(float(value))
        )

    @staticmethod
    def _receipt_id(receipt: Mapping[str, Any]) -> Optional[str]:
        for key in ("receipt_id", "provider_receipt_id", "event_id"):
            value = receipt.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    @staticmethod
    def _normalise_symbol(value: Any) -> str:
        return "".join(character for character in str(value).upper() if character.isalnum())

    @staticmethod
    def _no_data(reason: str) -> NoDataPrediction:
        return NoDataPrediction(
            data_status="no_data",
            truth_status="unverified",
            reason=reason,
            eligible_for_action=False,
            eligible_for_accounting=False,
            eligible_for_learning=False,
            generated_values=False,
        )

    def _common_receipt(
        self,
        receipt: Optional[Mapping[str, Any]],
        *,
        symbol: str,
        observed_at: float,
    ) -> Tuple[bool, str, Optional[str], Optional[float]]:
        if not isinstance(receipt, Mapping):
            return False, "receipt_missing", None, None
        provider = receipt.get("provider")
        receipt_type = receipt.get("provider_receipt_type")
        receipt_id = self._receipt_id(receipt)
        if not isinstance(provider, str) or not provider.strip():
            return False, "provider_missing", None, None
        if not isinstance(receipt_type, str) or not receipt_type.strip():
            return False, "provider_receipt_type_missing", None, None
        if receipt_id is None:
            return False, "receipt_id_missing", None, None
        if self._normalise_symbol(receipt.get("symbol")) != self._normalise_symbol(symbol):
            return False, "receipt_symbol_mismatch", None, None
        if receipt.get("data_status") not in {"live", "complete", "real_observed"}:
            return False, "receipt_not_live", None, None
        if receipt.get("truth_status") != "real_observed":
            return False, "receipt_not_observed", None, None
        if receipt.get("generated_values") is not False:
            return False, "generated_values_not_explicitly_false", None, None
        if receipt.get("eligible_for_prediction") is not True:
            return False, "receipt_not_prediction_eligible", None, None

        timestamp = receipt.get("provider_timestamp")
        if timestamp is None:
            timestamp = receipt.get("source_timestamp")
        if not self._is_finite_number(timestamp):
            return False, "provider_timestamp_missing", None, None
        timestamp = float(timestamp)
        if timestamp > observed_at:
            return False, "provider_timestamp_in_future", None, None
        if observed_at - timestamp > self.max_receipt_age_seconds:
            return False, "provider_receipt_stale", None, None
        return True, "complete", receipt_id, timestamp

    @staticmethod
    def _same_number(left: Any, right: Any) -> bool:
        return (
            TruthPredictionEngine._is_finite_number(left)
            and TruthPredictionEngine._is_finite_number(right)
            and math.isclose(float(left), float(right), rel_tol=1e-12, abs_tol=1e-12)
        )

    def _validate_market_receipt(
        self,
        snapshot: MarketSnapshot,
        receipt: Optional[Mapping[str, Any]],
        *,
        observed_at: float,
    ) -> Tuple[bool, str, Optional[str], Optional[float]]:
        complete, reason, receipt_id, timestamp = self._common_receipt(
            receipt,
            symbol=snapshot.symbol,
            observed_at=observed_at,
        )
        if not complete or not isinstance(receipt, Mapping):
            return complete, reason, receipt_id, timestamp
        values = {
            "price": snapshot.price,
            "change_24h": snapshot.change_24h,
            "volume_24h": snapshot.volume_24h,
            "momentum_30s": snapshot.momentum_30s,
            "volatility_30s": snapshot.volatility_30s,
            "hz_frequency": snapshot.hz_frequency,
        }
        for field, snapshot_value in values.items():
            if not self._same_number(receipt.get(field), snapshot_value):
                return False, f"market_{field}_mismatch", None, None
        if not self._same_number(snapshot.timestamp, timestamp):
            return False, "market_timestamp_mismatch", None, None
        if float(snapshot.price) <= 0 or float(snapshot.volume_24h) < 0:
            return False, "market_values_out_of_range", None, None
        return True, "complete", receipt_id, timestamp

    def _classify_scenario(self, snapshot: MarketSnapshot) -> str:
        """Classify market scenario for probability matrix."""
        momentum = snapshot.momentum_30s
        volatility = snapshot.volatility_30s

        # Strong uptrend
        if momentum > 0.3 and volatility < 0.3:
            return "strong"

        # Dying momentum
        if abs(momentum) < 0.1 and volatility < 0.2:
            return "dying"

        # High volatility
        if volatility > 0.5:
            return "volatile"

        # Reversal (momentum vs 24h change disagree)
        if (momentum > 0 and snapshot.change_24h < -2.0) or \
           (momentum < 0 and snapshot.change_24h > 2.0):
            return "reversal"

        return "sideways"

    def _classify_momentum_band(self, momentum: float) -> str:
        """Classify momentum for pattern key."""
        if momentum < -0.1:
            return "down"
        elif momentum < 0.3:
            return "flat"
        else:
            return "up"

    def _classify_hz_band(self, hz: float) -> str:
        """Classify harmonic band."""
        if hz < 10:
            return "schumann"
        elif hz < 100:
            return "alpha"
        elif hz < 300:
            return "beta"
        elif hz < 700:
            return "gamma"
        else:
            return "solfeggio"

    def generate_prediction(
        self,
        snapshot: MarketSnapshot,
        horizon_seconds: float = 30.0,
        min_confidence: float = 0.65,
        *,
        market_receipt: Optional[Mapping[str, Any]] = None,
        hnc_receipt: Optional[Mapping[str, Any]] = None,
        auris_receipt: Optional[Mapping[str, Any]] = None,
        observed_at: Optional[float] = None,
    ) -> PredictionResult:
        """
        Generate a prediction with FULL validation.

        Returns:
            TruthPrediction only for a complete linked receipt chain; otherwise
            a falsey, numeric-free NoDataPrediction.
        """
        if not self._is_finite_number(observed_at):
            return self._no_data("observed_at_missing")
        observed_at = float(observed_at)
        if not self._is_finite_number(horizon_seconds) or float(horizon_seconds) <= 0:
            return self._no_data("horizon_invalid")
        if (
            not self._is_finite_number(min_confidence)
            or not 0 <= float(min_confidence) <= 1
        ):
            return self._no_data("minimum_confidence_invalid")

        market_ok, reason, market_id, market_timestamp = self._validate_market_receipt(
            snapshot,
            market_receipt,
            observed_at=observed_at,
        )
        if not market_ok or market_id is None or market_timestamp is None:
            return self._no_data(reason)

        hnc_ok, reason, hnc_id, hnc_timestamp = self._common_receipt(
            hnc_receipt,
            symbol=snapshot.symbol,
            observed_at=observed_at,
        )
        if not hnc_ok or hnc_id is None or hnc_timestamp is None:
            return self._no_data(f"hnc_{reason}")
        if not isinstance(hnc_receipt, Mapping):
            return self._no_data("hnc_receipt_missing")
        if hnc_receipt.get("market_receipt_id") != market_id:
            return self._no_data("hnc_market_link_mismatch")
        if hnc_timestamp < market_timestamp:
            return self._no_data("hnc_precedes_market_receipt")

        raw_pattern_key = hnc_receipt.get("pattern_key")
        if not (
            isinstance(raw_pattern_key, (list, tuple))
            and len(raw_pattern_key) == 5
            and all(isinstance(value, str) and value.strip() for value in raw_pattern_key)
        ):
            return self._no_data("hnc_pattern_key_incomplete")
        pattern_key = tuple(value.strip() for value in raw_pattern_key)
        win_probability = hnc_receipt.get("win_probability")
        pattern_confidence = hnc_receipt.get("pattern_confidence")
        if not (
            self._is_finite_number(win_probability)
            and self._is_finite_number(pattern_confidence)
            and 0 <= float(win_probability) <= 1
            and 0 <= float(pattern_confidence) <= 1
        ):
            return self._no_data("hnc_probability_values_incomplete")
        win_probability = float(win_probability)
        pattern_confidence = float(pattern_confidence)
        if hnc_receipt.get("queen_approved") is not True or win_probability < 0.65:
            return self._no_data("queen_probability_gate_rejected")
        if pattern_confidence < float(min_confidence):
            return self._no_data("hnc_confidence_below_threshold")

        auris_ok, reason, auris_id, auris_timestamp = self._common_receipt(
            auris_receipt,
            symbol=snapshot.symbol,
            observed_at=observed_at,
        )
        if not auris_ok or auris_id is None or auris_timestamp is None:
            return self._no_data(f"auris_{reason}")
        if not isinstance(auris_receipt, Mapping):
            return self._no_data("auris_receipt_missing")
        if auris_receipt.get("market_receipt_id") != market_id:
            return self._no_data("auris_market_link_mismatch")
        if auris_receipt.get("hnc_receipt_id") != hnc_id:
            return self._no_data("auris_hnc_link_mismatch")
        if auris_timestamp < hnc_timestamp:
            return self._no_data("auris_precedes_hnc_receipt")
        auris_resonance = auris_receipt.get("geometric_truth")
        if (
            auris_receipt.get("approved") is not True
            or not self._is_finite_number(auris_resonance)
            or not 0 <= float(auris_resonance) <= 1
            or float(auris_resonance) < (PHI - 1.0)
        ):
            return self._no_data("auris_gate_rejected")
        auris_resonance = float(auris_resonance)

        # Determine predicted direction and magnitude
        if snapshot.momentum_30s > 0.1:
            predicted_direction = "UP"
            # Scale by win probability and pattern confidence
            predicted_change_pct = snapshot.momentum_30s * win_probability * pattern_confidence
        elif snapshot.momentum_30s < -0.1:
            predicted_direction = "DOWN"
            predicted_change_pct = snapshot.momentum_30s * win_probability * pattern_confidence
        else:
            predicted_direction = "FLAT"
            predicted_change_pct = 0.0

        # Build prediction
        prediction = TruthPrediction(
            symbol=snapshot.symbol,
            start_time=snapshot.timestamp,
            start_price=snapshot.price,
            win_probability=win_probability,
            pattern_key=pattern_key,
            pattern_confidence=pattern_confidence,
            auris_approved=True,
            auris_resonance=auris_resonance,
            hz_strength=(abs(snapshot.momentum_30s) + snapshot.volatility_30s) / 10.0,
            hz_band=self._classify_hz_band(snapshot.hz_frequency),
            predicted_direction=predicted_direction,
            predicted_change_pct=predicted_change_pct,
            horizon_seconds=horizon_seconds,
            market_receipt_id=market_id,
            hnc_receipt_id=hnc_id,
            auris_receipt_id=auris_id,
            queen_approved=True,
        )

        # Track for validation
        if snapshot.symbol not in self.pending_predictions:
            self.pending_predictions[snapshot.symbol] = []
        self.pending_predictions[snapshot.symbol].append(prediction)

        return prediction

    def validate_predictions(
        self,
        snapshot: MarketSnapshot,
        *,
        market_receipt: Optional[Mapping[str, Any]] = None,
        observed_at: Optional[float] = None,
    ) -> PredictionValidationBatch:
        """
        Validate any pending predictions for this symbol.

        Returns:
            List of validated predictions
        """
        if not self._is_finite_number(observed_at):
            return PredictionValidationBatch(
                data_status="no_data",
                truth_status="unverified",
                reason="observed_at_missing",
                eligible_for_learning=False,
            )
        observed_at = float(observed_at)
        market_ok, reason, _market_id, market_timestamp = self._validate_market_receipt(
            snapshot,
            market_receipt,
            observed_at=observed_at,
        )
        if not market_ok or market_timestamp is None or not isinstance(market_receipt, Mapping):
            return PredictionValidationBatch(
                data_status="no_data",
                truth_status="unverified",
                reason=reason,
                eligible_for_learning=False,
            )
        if market_receipt.get("eligible_for_learning") is not True:
            return PredictionValidationBatch(
                data_status="no_data",
                truth_status="unverified",
                reason="outcome_not_learning_eligible",
                eligible_for_learning=False,
            )
        if snapshot.symbol not in self.pending_predictions:
            return PredictionValidationBatch(
                data_status="no_data",
                truth_status="real_observed",
                reason="no_pending_predictions",
                eligible_for_learning=False,
            )

        validated = []
        still_pending = []

        for pred in self.pending_predictions[snapshot.symbol]:
            if pred.validated:
                continue  # Already validated

            # Check if horizon elapsed
            if market_receipt.get("prediction_receipt_id") != pred.auris_receipt_id:
                still_pending.append(pred)
                continue
            elapsed = market_timestamp - pred.start_time
            if elapsed >= pred.horizon_seconds:
                # Validate!
                pred.validated = True
                pred.actual_price = snapshot.price
                pred.actual_change_pct = ((snapshot.price - pred.start_price) / pred.start_price) * 100.0

                # Check direction correctness
                if pred.predicted_direction == "UP":
                    pred.correct = pred.actual_change_pct > 0
                elif pred.predicted_direction == "DOWN":
                    pred.correct = pred.actual_change_pct < 0
                else:  # FLAT
                    pred.correct = abs(pred.actual_change_pct) < 0.1

                # Calculate geometric truth (alignment of prediction vs reality)
                if pred.actual_change_pct != 0:
                    accuracy_ratio = min(abs(pred.predicted_change_pct / pred.actual_change_pct), 2.0)
                    pred.geometric_truth = math.exp(-abs(1.0 - accuracy_ratio))
                else:
                    pred.geometric_truth = 1.0 if abs(pred.predicted_change_pct) < 0.01 else 0.0

                validated.append(pred)
                self.validated_predictions.append(pred)
            else:
                still_pending.append(pred)

        # Update pending list
        self.pending_predictions[snapshot.symbol] = still_pending

        if validated:
            return PredictionValidationBatch(
                validated,
                data_status="live",
                truth_status="real_observed",
                reason="validated_from_linked_provider_receipt",
                eligible_for_learning=True,
            )
        return PredictionValidationBatch(
            data_status="no_data",
            truth_status="real_observed",
            reason="no_linked_prediction_horizon_elapsed",
            eligible_for_learning=False,
        )

    def get_accuracy_stats(self) -> Dict[str, Any]:
        """Get overall prediction accuracy statistics."""
        total = 0
        correct = 0
        avg_geometric_truth = 0.0

        for pred in self.validated_predictions:
            total += 1
            if pred.correct:
                correct += 1
            if pred.geometric_truth is not None:
                avg_geometric_truth += pred.geometric_truth

        if total == 0:
            return {
                "data_status": "no_data",
                "truth_status": "unverified",
                "eligible_for_learning": False,
                "generated_values": False,
            }
        return {
            "data_status": "live",
            "truth_status": "real_observed",
            "total_validated": total,
            "correct": correct,
            "accuracy_pct": correct / total * 100.0,
            "avg_geometric_truth": avg_geometric_truth / total,
            "eligible_for_learning": True,
            "generated_values": False,
        }
