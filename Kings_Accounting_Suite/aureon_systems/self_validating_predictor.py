#!/usr/bin/env python3
"""
Receipt-gated self-validating market prediction.

Import and default construction are inert. Callers inject a market-receipt
reader and supply a fresh, linked evidence -> market -> HNC -> Auris chain.
Learning state changes only after a separately linked provider outcome receipt.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, List, Mapping, Optional, Sequence, Tuple, Union

import numpy as np


PHI = (1 + math.sqrt(5)) / 2
MAX_RECEIPT_AGE_SECONDS = 30.0
FUTURE_TOLERANCE_SECONDS = 5.0

FREQ_MAP = {
    "ROOT": 256.0,
    "TRANSFORMATION": 417.0,
    "NATURAL": 432.0,
    "DISTORTION": 440.0,
    "LOVE": 528.0,
    "CONNECTION": 639.0,
}


@dataclass(frozen=True)
class NoDataPrediction:
    """Falsey and recursively numeric-free refusal."""

    data_status: str
    truth_status: str
    reason: str
    eligible_for_action: bool
    eligible_for_accounting: bool
    eligible_for_learning: bool
    generated_values: bool

    def __bool__(self) -> bool:
        return False


@dataclass(frozen=True)
class BaselineObservation:
    """Receipt-backed prices and their unchanged prediction inputs."""

    platform: str
    symbol: str
    prices: Tuple[float, ...]
    momentum: float
    frequency: float
    market_receipts: Tuple[Mapping[str, Any], ...]
    evidence_receipt_id: str


@dataclass
class Prediction:
    """A prediction backed by a complete authorization chain."""

    symbol: str
    platform: str
    timestamp: float
    baseline_price: float
    baseline_momentum: float
    baseline_frequency: float
    predicted_direction: str
    predicted_change_pct: float
    predicted_price: float
    confidence: float
    horizon_seconds: float
    receipt_id: str
    market_receipt_id: str
    evidence_receipt_id: str
    hnc_receipt_id: str
    auris_receipt_id: str
    input_receipt_ids: Tuple[str, ...]
    source_timestamp: float
    received_at: float
    data_status: str = "complete"
    truth_status: str = "derived_from_real_observed"
    generated_values: bool = False
    eligible_for_action: bool = True
    eligible_for_accounting: bool = False
    eligible_for_learning: bool = False
    outcome_receipt_id: Optional[str] = None
    actual_price: Optional[float] = None
    actual_change_pct: Optional[float] = None
    actual_direction: Optional[str] = None
    direction_correct: Optional[bool] = None
    magnitude_accuracy: Optional[float] = None
    validated: bool = False

    def _apply_validation(self, actual_price: float, outcome_receipt_id: str) -> None:
        """Apply the original validation equations after the receipt gate."""

        actual_change_pct = (
            (actual_price - self.baseline_price) / self.baseline_price
        ) * 100
        if actual_change_pct > 0.01:
            actual_direction = "UP"
        elif actual_change_pct < -0.01:
            actual_direction = "DOWN"
        else:
            actual_direction = "FLAT"

        direction_correct = self.predicted_direction == actual_direction
        if self.predicted_change_pct != 0:
            error = abs(actual_change_pct - self.predicted_change_pct)
            magnitude_accuracy = max(
                0,
                1 - (error / abs(self.predicted_change_pct)),
            )
        else:
            magnitude_accuracy = 1.0 if abs(actual_change_pct) < 0.02 else 0.0

        self.outcome_receipt_id = outcome_receipt_id
        self.actual_price = actual_price
        self.actual_change_pct = actual_change_pct
        self.actual_direction = actual_direction
        self.direction_correct = direction_correct
        self.magnitude_accuracy = magnitude_accuracy
        self.truth_status = "validated_real_outcome"
        self.eligible_for_learning = True
        self.validated = True


PredictionResult = Union[Prediction, NoDataPrediction]
BaselineResult = Union[BaselineObservation, NoDataPrediction]
MarketReceiptReader = Callable[[str, str], Mapping[str, Any]]


class SelfValidatingPredictor:
    """Predict and learn only from fresh, linked provider receipts."""

    def __init__(
        self,
        *,
        market_reader: Optional[MarketReceiptReader] = None,
        sleeper: Optional[Callable[[float], None]] = None,
        max_receipt_age_seconds: float = MAX_RECEIPT_AGE_SECONDS,
    ) -> None:
        if (
            not self._is_finite_number(max_receipt_age_seconds)
            or float(max_receipt_age_seconds) <= 0
        ):
            raise ValueError("max_receipt_age_seconds must be finite and positive")
        self._market_reader = market_reader
        self._sleep = sleeper if sleeper is not None else time.sleep
        self.max_receipt_age_seconds = float(max_receipt_age_seconds)
        self.predictions: List[Prediction] = []
        self.accuracy_window = deque(maxlen=20)
        self.total_predictions = 0
        self.correct_predictions = 0

    @staticmethod
    def _is_finite_number(value: Any) -> bool:
        return (
            not isinstance(value, bool)
            and isinstance(value, (int, float, np.integer, np.floating))
            and math.isfinite(float(value))
        )

    @staticmethod
    def _normalise_symbol(value: Any) -> str:
        return "".join(character for character in str(value).upper() if character.isalnum())

    @staticmethod
    def _normalise_provider(value: Any) -> str:
        return "".join(character for character in str(value).lower() if character.isalnum())

    @staticmethod
    def _receipt_id(receipt: Mapping[str, Any]) -> Optional[str]:
        for key in ("receipt_id", "provider_receipt_id", "event_id"):
            value = receipt.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    @staticmethod
    def _flag_true(receipt: Mapping[str, Any], *keys: str) -> bool:
        return any(receipt.get(key) is True for key in keys)

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

    @staticmethod
    def _stable_receipt_id(payload: Mapping[str, Any]) -> str:
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "self-validating-prediction:" + hashlib.sha256(encoded).hexdigest()

    def _common_receipt(
        self,
        receipt: Optional[Mapping[str, Any]],
        *,
        symbol: str,
        observed_at: float,
        expected_provider: Optional[str] = None,
        allowed_truth_statuses: Tuple[str, ...] = ("real_observed",),
        require_prediction: bool = False,
        require_action: bool = False,
        require_learning: bool = False,
    ) -> Tuple[bool, str, Optional[str], Optional[float], Optional[float]]:
        if not isinstance(receipt, Mapping):
            return False, "receipt_missing", None, None, None
        provider = receipt.get("provider")
        receipt_type = receipt.get("provider_receipt_type")
        if receipt_type is None:
            receipt_type = receipt.get("receipt_type")
        receipt_id = self._receipt_id(receipt)
        if not isinstance(provider, str) or not provider.strip():
            return False, "provider_missing", None, None, None
        if expected_provider is not None and (
            self._normalise_provider(provider)
            != self._normalise_provider(expected_provider)
        ):
            return False, "provider_mismatch", None, None, None
        if not isinstance(receipt_type, str) or not receipt_type.strip():
            return False, "provider_receipt_type_missing", None, None, None
        if receipt_id is None:
            return False, "receipt_id_missing", None, None, None
        if self._normalise_symbol(receipt.get("symbol")) != self._normalise_symbol(symbol):
            return False, "receipt_symbol_mismatch", None, None, None
        if receipt.get("data_status") not in {"live", "complete", "real_observed"}:
            return False, "receipt_not_complete", None, None, None
        if receipt.get("truth_status") not in allowed_truth_statuses:
            return False, "receipt_not_observed", None, None, None
        if receipt.get("generated_values") is not False:
            return False, "generated_values_not_explicitly_false", None, None, None
        if require_prediction and not self._flag_true(
            receipt, "eligible_for_prediction", "prediction_eligible"
        ):
            return False, "receipt_not_prediction_eligible", None, None, None
        if require_action and not self._flag_true(
            receipt, "eligible_for_action", "action_eligible", "actionable"
        ):
            return False, "receipt_not_action_eligible", None, None, None
        if require_learning and not self._flag_true(
            receipt, "eligible_for_learning", "learning_eligible"
        ):
            return False, "receipt_not_learning_eligible", None, None, None

        source_timestamp = receipt.get("source_timestamp")
        if source_timestamp is None:
            source_timestamp = receipt.get("provider_timestamp")
        received_at = receipt.get("received_at")
        if not self._is_finite_number(source_timestamp):
            return False, "source_timestamp_missing", None, None, None
        if not self._is_finite_number(received_at):
            return False, "received_at_missing", None, None, None
        source_timestamp = float(source_timestamp)
        received_at = float(received_at)
        if source_timestamp > received_at + FUTURE_TOLERANCE_SECONDS:
            return False, "source_timestamp_after_receipt", None, None, None
        if source_timestamp > observed_at + FUTURE_TOLERANCE_SECONDS:
            return False, "source_timestamp_in_future", None, None, None
        if received_at > observed_at + FUTURE_TOLERANCE_SECONDS:
            return False, "received_at_in_future", None, None, None
        if observed_at - source_timestamp > self.max_receipt_age_seconds:
            return False, "source_receipt_stale", None, None, None
        if observed_at - received_at > self.max_receipt_age_seconds:
            return False, "local_receipt_stale", None, None, None
        return True, "complete", receipt_id, source_timestamp, received_at

    def _validate_evidence_receipt(
        self,
        receipt: Optional[Mapping[str, Any]],
        *,
        platform: str,
        symbol: str,
        observed_at: float,
    ) -> Tuple[bool, str, Optional[str], Optional[float], Optional[float]]:
        result = self._common_receipt(
            receipt,
            symbol=symbol,
            observed_at=observed_at,
            expected_provider=platform,
            require_prediction=True,
            require_action=True,
        )
        if not result[0] or not isinstance(receipt, Mapping):
            return result
        if receipt.get("evidence_complete") is not True:
            return False, "evidence_incomplete", None, None, None
        return result

    def _validate_market_receipt(
        self,
        receipt: Optional[Mapping[str, Any]],
        *,
        platform: str,
        symbol: str,
        evidence_receipt_id: str,
        observed_at: float,
    ) -> Tuple[
        bool,
        str,
        Optional[str],
        Optional[float],
        Optional[float],
        Optional[float],
    ]:
        common = self._common_receipt(
            receipt,
            symbol=symbol,
            observed_at=observed_at,
            expected_provider=platform,
            require_prediction=True,
            require_action=True,
        )
        if not common[0] or not isinstance(receipt, Mapping):
            return common + (None,)
        if receipt.get("evidence_receipt_id") != evidence_receipt_id:
            return False, "market_evidence_link_mismatch", None, None, None, None
        price = receipt.get("price")
        if price is None:
            price = receipt.get("lastPrice")
        if not self._is_finite_number(price) or float(price) <= 0:
            return False, "market_price_missing", None, None, None, None
        return common + (float(price),)

    def _validate_gate_receipt(
        self,
        receipt: Optional[Mapping[str, Any]],
        *,
        gate_name: str,
        platform: str,
        symbol: str,
        market_receipt_id: str,
        evidence_receipt_id: str,
        observed_at: float,
        minimum_source_timestamp: float,
        hnc_receipt_id: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[str], Optional[float], Optional[float]]:
        common = self._common_receipt(
            receipt,
            symbol=symbol,
            observed_at=observed_at,
            allowed_truth_statuses=(
                "real_observed",
                "verified",
                "derived_from_real_observed",
            ),
            require_prediction=True,
            require_action=True,
        )
        if not common[0] or not isinstance(receipt, Mapping):
            return common
        if self._normalise_provider(receipt.get("market_provider")) != (
            self._normalise_provider(platform)
        ):
            return False, f"{gate_name}_market_provider_mismatch", None, None, None
        if receipt.get("market_receipt_id") != market_receipt_id:
            return False, f"{gate_name}_market_link_mismatch", None, None, None
        if receipt.get("evidence_receipt_id") != evidence_receipt_id:
            return False, f"{gate_name}_evidence_link_mismatch", None, None, None
        if hnc_receipt_id is not None and receipt.get("hnc_receipt_id") != hnc_receipt_id:
            return False, "auris_hnc_link_mismatch", None, None, None
        if not self._flag_true(receipt, "approved", "gate_open", "queen_approved"):
            return False, f"{gate_name}_gate_closed", None, None, None
        source_timestamp = common[3]
        if source_timestamp is None or source_timestamp < minimum_source_timestamp:
            return False, f"{gate_name}_precedes_input", None, None, None
        return common

    @staticmethod
    def _baseline_metrics(prices: Sequence[float]) -> Tuple[float, float]:
        momentums = [
            ((prices[index] - prices[index - 1]) / prices[index - 1]) * 100
            for index in range(1, len(prices))
        ]
        avg_momentum = float(np.mean(momentums))
        ratio = prices[-1] / prices[0]
        frequency = 432.0 * (ratio ** PHI)
        frequency = max(256, min(963, frequency))
        return avg_momentum, float(frequency)

    def collect_baseline(
        self,
        platform: str,
        symbol: str,
        duration_sec: int = 10,
        *,
        evidence_receipt: Optional[Mapping[str, Any]] = None,
        observed_at: Optional[float] = None,
    ) -> BaselineResult:
        """Collect provider receipts without substituting a price."""

        if not self._is_finite_number(observed_at):
            return self._no_data("observed_at_missing")
        observed_at = float(observed_at)
        if (
            isinstance(duration_sec, bool)
            or not isinstance(duration_sec, int)
            or duration_sec <= 0
        ):
            return self._no_data("baseline_duration_invalid")
        if self._market_reader is None:
            return self._no_data("market_reader_missing")

        evidence = self._validate_evidence_receipt(
            evidence_receipt,
            platform=platform,
            symbol=symbol,
            observed_at=observed_at,
        )
        if not evidence[0] or evidence[2] is None or evidence[3] is None:
            return self._no_data(evidence[1])
        evidence_receipt_id, evidence_timestamp = evidence[2], evidence[3]

        sample_count = duration_sec * 2
        if sample_count < 5:
            return self._no_data("baseline_sample_count_insufficient")
        prices: List[float] = []
        receipts: List[Mapping[str, Any]] = []
        previous_source_timestamp: Optional[float] = None
        seen_receipt_ids = set()

        for sample_index in range(sample_count):
            try:
                receipt = self._market_reader(platform, symbol)
            except Exception:
                return self._no_data("market_reader_failed")
            market = self._validate_market_receipt(
                receipt,
                platform=platform,
                symbol=symbol,
                evidence_receipt_id=evidence_receipt_id,
                observed_at=observed_at,
            )
            if not market[0]:
                return self._no_data(market[1])
            receipt_id, source_timestamp, price = market[2], market[3], market[5]
            if receipt_id is None or source_timestamp is None or price is None:
                return self._no_data("market_receipt_incomplete")
            if source_timestamp < evidence_timestamp:
                return self._no_data("market_precedes_evidence")
            if receipt_id in seen_receipt_ids:
                return self._no_data("market_receipt_reused")
            if (
                previous_source_timestamp is not None
                and source_timestamp < previous_source_timestamp
            ):
                return self._no_data("market_receipts_out_of_order")
            seen_receipt_ids.add(receipt_id)
            previous_source_timestamp = source_timestamp
            prices.append(price)
            receipts.append(receipt)
            if sample_index + 1 < sample_count:
                self._sleep(0.5)

        momentum, frequency = self._baseline_metrics(prices)
        return BaselineObservation(
            platform=platform,
            symbol=symbol,
            prices=tuple(prices),
            momentum=momentum,
            frequency=frequency,
            market_receipts=tuple(receipts),
            evidence_receipt_id=evidence_receipt_id,
        )

    def generate_prediction(
        self,
        platform: str,
        symbol: str,
        prices: Sequence[float],
        momentum: float,
        frequency: float,
        *,
        market_receipts: Sequence[Mapping[str, Any]],
        evidence_receipt: Optional[Mapping[str, Any]],
        hnc_receipt: Optional[Mapping[str, Any]],
        auris_receipt: Optional[Mapping[str, Any]],
        observed_at: Optional[float],
        horizon_seconds: float = 30.0,
    ) -> PredictionResult:
        """Apply the original equations to an authorized receipt chain."""

        if not self._is_finite_number(observed_at):
            return self._no_data("observed_at_missing")
        observed_at = float(observed_at)
        if not self._is_finite_number(horizon_seconds) or float(horizon_seconds) < 0:
            return self._no_data("prediction_horizon_invalid")
        if len(prices) < 5 or len(market_receipts) != len(prices):
            return self._no_data("baseline_receipts_incomplete")
        if not all(self._is_finite_number(price) and float(price) > 0 for price in prices):
            return self._no_data("baseline_prices_invalid")
        if not self._is_finite_number(momentum) or not self._is_finite_number(frequency):
            return self._no_data("baseline_metrics_invalid")
        prices = tuple(float(price) for price in prices)

        evidence = self._validate_evidence_receipt(
            evidence_receipt,
            platform=platform,
            symbol=symbol,
            observed_at=observed_at,
        )
        if (
            not evidence[0]
            or evidence[2] is None
            or evidence[3] is None
            or evidence[4] is None
        ):
            return self._no_data(evidence[1])
        evidence_id, evidence_timestamp = evidence[2], evidence[3]
        input_ids: List[str] = [evidence_id]
        input_received_at: List[float] = [evidence[4]]
        market_ids: List[str] = []
        latest_market_timestamp: Optional[float] = None
        latest_market_id: Optional[str] = None

        for expected_price, receipt in zip(prices, market_receipts):
            market = self._validate_market_receipt(
                receipt,
                platform=platform,
                symbol=symbol,
                evidence_receipt_id=evidence_id,
                observed_at=observed_at,
            )
            if not market[0]:
                return self._no_data(market[1])
            receipt_id, source_timestamp, received_at, receipt_price = (
                market[2],
                market[3],
                market[4],
                market[5],
            )
            if (
                receipt_id is None
                or source_timestamp is None
                or received_at is None
                or receipt_price is None
            ):
                return self._no_data("market_receipt_incomplete")
            if source_timestamp < evidence_timestamp:
                return self._no_data("market_precedes_evidence")
            if receipt_id in market_ids:
                return self._no_data("market_receipt_reused")
            if (
                latest_market_timestamp is not None
                and source_timestamp < latest_market_timestamp
            ):
                return self._no_data("market_receipts_out_of_order")
            if not math.isclose(
                receipt_price, expected_price, rel_tol=1e-12, abs_tol=1e-12
            ):
                return self._no_data("baseline_price_receipt_mismatch")
            market_ids.append(receipt_id)
            input_received_at.append(received_at)
            latest_market_id = receipt_id
            latest_market_timestamp = source_timestamp

        expected_momentum, expected_frequency = self._baseline_metrics(prices)
        if not math.isclose(
            float(momentum), expected_momentum, rel_tol=1e-12, abs_tol=1e-12
        ):
            return self._no_data("baseline_momentum_mismatch")
        if not math.isclose(
            float(frequency), expected_frequency, rel_tol=1e-12, abs_tol=1e-12
        ):
            return self._no_data("baseline_frequency_mismatch")
        if latest_market_id is None or latest_market_timestamp is None:
            return self._no_data("latest_market_receipt_missing")

        hnc = self._validate_gate_receipt(
            hnc_receipt,
            gate_name="hnc",
            platform=platform,
            symbol=symbol,
            market_receipt_id=latest_market_id,
            evidence_receipt_id=evidence_id,
            observed_at=observed_at,
            minimum_source_timestamp=latest_market_timestamp,
        )
        if not hnc[0] or hnc[2] is None or hnc[3] is None or hnc[4] is None:
            return self._no_data(hnc[1])
        hnc_id, hnc_timestamp, hnc_received_at = hnc[2], hnc[3], hnc[4]

        auris = self._validate_gate_receipt(
            auris_receipt,
            gate_name="auris",
            platform=platform,
            symbol=symbol,
            market_receipt_id=latest_market_id,
            evidence_receipt_id=evidence_id,
            observed_at=observed_at,
            minimum_source_timestamp=hnc_timestamp,
            hnc_receipt_id=hnc_id,
        )
        if not auris[0] or auris[2] is None or auris[3] is None or auris[4] is None:
            return self._no_data(auris[1])
        auris_id, auris_timestamp, auris_received_at = (
            auris[2],
            auris[3],
            auris[4],
        )

        baseline_price = prices[-1]
        recent_prices = prices[-5:]
        price_trend = float(
            np.polyfit(range(len(recent_prices)), recent_prices, 1)[0]
        )
        momentum_strength = abs(float(momentum)) * 10

        freq_boost = 0
        if abs(float(frequency) - FREQ_MAP["LOVE"]) < 30:
            freq_boost = 0.02
        elif abs(float(frequency) - FREQ_MAP["NATURAL"]) < 15:
            freq_boost = 0.01
        elif abs(float(frequency) - FREQ_MAP["DISTORTION"]) < 10:
            freq_boost = -0.02

        momentum_contribution = float(momentum) * 0.5
        trend_contribution = (price_trend / baseline_price) * 100 * 30
        predicted_change = (
            momentum_contribution + trend_contribution * 0.3 + freq_boost
        )
        predicted_change = max(-0.5, min(0.5, predicted_change))

        if predicted_change > 0.01:
            direction = "UP"
        elif predicted_change < -0.01:
            direction = "DOWN"
        else:
            direction = "FLAT"

        momentum_consistency = 1.0 - min(
            1.0,
            float(np.std(recent_prices)) / float(np.mean(recent_prices)) * 100,
        )
        confidence = min(
            0.9, momentum_consistency * 0.5 + momentum_strength * 0.3 + 0.2
        )
        predicted_price = baseline_price * (1 + predicted_change / 100)

        input_ids.extend(market_ids)
        input_ids.extend((hnc_id, auris_id))
        received_at = max(
            input_received_at + [hnc_received_at, auris_received_at]
        )
        receipt_payload = {
            "platform": platform,
            "symbol": self._normalise_symbol(symbol),
            "prices": prices,
            "momentum": float(momentum),
            "frequency": float(frequency),
            "predicted_direction": direction,
            "predicted_change_pct": predicted_change,
            "predicted_price": predicted_price,
            "confidence": confidence,
            "horizon_seconds": float(horizon_seconds),
            "source_timestamp": auris_timestamp,
            "input_receipt_ids": input_ids,
        }
        prediction_receipt_id = self._stable_receipt_id(receipt_payload)
        return Prediction(
            symbol=symbol,
            platform=platform,
            timestamp=auris_timestamp,
            baseline_price=baseline_price,
            baseline_momentum=float(momentum),
            baseline_frequency=float(frequency),
            predicted_direction=direction,
            predicted_change_pct=predicted_change,
            predicted_price=predicted_price,
            confidence=confidence,
            horizon_seconds=float(horizon_seconds),
            receipt_id=prediction_receipt_id,
            market_receipt_id=latest_market_id,
            evidence_receipt_id=evidence_id,
            hnc_receipt_id=hnc_id,
            auris_receipt_id=auris_id,
            input_receipt_ids=tuple(input_ids),
            source_timestamp=auris_timestamp,
            received_at=received_at,
        )

    def validate_prediction(
        self,
        prediction: Prediction,
        *,
        outcome_receipt: Optional[Mapping[str, Any]],
        observed_at: Optional[float],
    ) -> PredictionResult:
        """Validate and learn only from a linked, horizon-complete outcome."""

        if not isinstance(prediction, Prediction):
            return self._no_data("prediction_missing")
        if prediction.validated:
            return self._no_data("prediction_already_validated")
        if not self._is_finite_number(observed_at):
            return self._no_data("observed_at_missing")
        observed_at = float(observed_at)
        outcome = self._common_receipt(
            outcome_receipt,
            symbol=prediction.symbol,
            observed_at=observed_at,
            expected_provider=prediction.platform,
            require_learning=True,
        )
        if not outcome[0] or not isinstance(outcome_receipt, Mapping):
            return self._no_data(outcome[1])
        outcome_id, outcome_timestamp = outcome[2], outcome[3]
        if outcome_id is None or outcome_timestamp is None:
            return self._no_data("outcome_receipt_incomplete")
        if outcome_receipt.get("prediction_receipt_id") != prediction.receipt_id:
            return self._no_data("outcome_prediction_link_mismatch")
        if outcome_receipt.get("evidence_receipt_id") != prediction.evidence_receipt_id:
            return self._no_data("outcome_evidence_link_mismatch")
        if outcome_timestamp < prediction.timestamp + prediction.horizon_seconds:
            return self._no_data("prediction_horizon_not_elapsed")
        actual_price = outcome_receipt.get("price")
        if actual_price is None:
            actual_price = outcome_receipt.get("lastPrice")
        if not self._is_finite_number(actual_price) or float(actual_price) <= 0:
            return self._no_data("outcome_price_missing")

        prediction._apply_validation(float(actual_price), outcome_id)
        self.predictions.append(prediction)
        self.total_predictions += 1
        if prediction.direction_correct:
            self.correct_predictions += 1
        self.accuracy_window.append(1 if prediction.direction_correct else 0)
        return prediction

    def run_prediction_cycle(
        self,
        platform: str,
        symbol: str,
        *,
        evidence_receipt: Mapping[str, Any],
        hnc_receipt: Mapping[str, Any],
        auris_receipt: Mapping[str, Any],
        observed_at: float,
        validation_observed_at: Optional[float] = None,
        baseline_duration_sec: int = 10,
        prediction_window_sec: int = 30,
    ) -> PredictionResult:
        """Run one explicitly authorized cycle through an injected reader."""

        baseline = self.collect_baseline(
            platform,
            symbol,
            baseline_duration_sec,
            evidence_receipt=evidence_receipt,
            observed_at=observed_at,
        )
        if not baseline:
            return baseline
        prediction = self.generate_prediction(
            platform,
            symbol,
            baseline.prices,
            baseline.momentum,
            baseline.frequency,
            market_receipts=baseline.market_receipts,
            evidence_receipt=evidence_receipt,
            hnc_receipt=hnc_receipt,
            auris_receipt=auris_receipt,
            observed_at=observed_at,
            horizon_seconds=prediction_window_sec,
        )
        if not prediction:
            return prediction
        if self._market_reader is None:
            return self._no_data("market_reader_missing")
        if prediction_window_sec > 0:
            self._sleep(float(prediction_window_sec))
        if validation_observed_at is None:
            if prediction_window_sec > 0:
                return self._no_data("validation_observed_at_missing")
            validation_observed_at = observed_at
        try:
            outcome_receipt = self._market_reader(platform, symbol)
        except Exception:
            return self._no_data("outcome_reader_failed")
        return self.validate_prediction(
            prediction,
            outcome_receipt=outcome_receipt,
            observed_at=validation_observed_at,
        )

    @property
    def running_accuracy(self) -> Optional[float]:
        if not self.accuracy_window:
            return None
        return sum(self.accuracy_window) / len(self.accuracy_window)


def main() -> int:
    print(
        "SelfValidatingPredictor is inert by default. "
        "Inject a provider receipt reader and explicit evidence, HNC, and Auris receipts."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
