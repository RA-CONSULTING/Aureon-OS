#!/usr/bin/env python3
"""Thirty-second quantum analysis windows over live provider observations.

No price walk, volume, sentiment, market capitalization, or forecast is
generated here. The stream exposes observed ticks and deterministic indicators;
a future prediction is unavailable until a real model receipt is supplied.
"""

from __future__ import annotations

import math
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from aureon.core.aureon_baton_link import link_system as _baton_link

_baton_link(__name__)


@dataclass(frozen=True)
class MarketSnapshot:
    timestamp: float
    prices: Dict[str, float]
    source_event_ids: List[str]
    truth_status: str = "real_derived"
    generated_values: bool = False


@dataclass(frozen=True)
class LiveTick:
    timestamp: float
    symbol: str
    price: float
    volume: float
    source_id: str
    source_event_id: str
    source_timestamp: str
    truth_status: str = "live"
    generated_values: bool = False


@dataclass(frozen=True)
class FuturePrediction:
    prediction_time: float
    symbol: str
    current_price: float
    predicted_price: Optional[float]
    confidence: Optional[float]
    source_id: Optional[str]
    source_event_id: Optional[str]
    source_timestamp: Optional[str]
    truth_status: str
    generated_values: bool = False


class QuantumPredictionStream:
    """Maintain a fresh window of live provider ticks."""

    def __init__(self, max_age_seconds: float = 30.0):
        self.max_age_seconds = float(max_age_seconds)
        self.ticks: Dict[str, List[LiveTick]] = {}
        self.model_receipts: Dict[str, FuturePrediction] = {}

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("source_timestamp must include a timezone")
        return parsed.astimezone(timezone.utc)

    def ingest_tick(self, payload: Dict[str, Any]) -> LiveTick:
        required = (
            "timestamp",
            "symbol",
            "price",
            "volume",
            "source_id",
            "source_event_id",
            "source_timestamp",
            "truth_status",
            "generated_values",
        )
        missing = [name for name in required if payload.get(name) is None]
        if missing:
            raise ValueError(f"missing tick fields: {', '.join(missing)}")
        if payload["truth_status"] not in {"live", "provider_observed"}:
            raise ValueError("tick must be provider-observed")
        if payload["generated_values"] is not False:
            raise ValueError("generated tick values are prohibited")
        source_time = self._parse_timestamp(str(payload["source_timestamp"]))
        age = (datetime.now(timezone.utc) - source_time).total_seconds()
        if age < -30 or age > self.max_age_seconds:
            raise ValueError(f"stale tick: age_seconds={age:.3f}")
        price = float(payload["price"])
        volume = float(payload["volume"])
        if not all(math.isfinite(value) for value in (price, volume)):
            raise ValueError("tick values must be finite")
        if price <= 0 or volume < 0:
            raise ValueError("price must be positive and volume non-negative")
        tick = LiveTick(
            timestamp=float(payload["timestamp"]),
            symbol=str(payload["symbol"]),
            price=price,
            volume=volume,
            source_id=str(payload["source_id"]),
            source_event_id=str(payload["source_event_id"]),
            source_timestamp=str(payload["source_timestamp"]),
            truth_status=str(payload["truth_status"]),
        )
        history = self.ticks.setdefault(tick.symbol, [])
        if not any(item.source_event_id == tick.source_event_id for item in history):
            history.append(tick)
        self._prune()
        return tick

    def _prune(self) -> None:
        now = datetime.now(timezone.utc)
        for symbol, history in list(self.ticks.items()):
            current = [
                tick
                for tick in history
                if (now - self._parse_timestamp(tick.source_timestamp)).total_seconds()
                <= self.max_age_seconds
            ]
            if current:
                self.ticks[symbol] = current
            else:
                del self.ticks[symbol]

    def calculate_fibonacci_alignment(
        self, price: float, symbol: str
    ) -> Optional[float]:
        """Derive alignment from at least ten observed prices."""
        history = [tick.price for tick in self.ticks.get(symbol, [])]
        if len(history) < 10:
            return None
        high, low = max(history), min(history)
        range_value = high - low
        if range_value <= 0:
            return None
        retracement = (high - float(price)) / range_value
        levels = (0.236, 0.382, 0.5, 0.618, 0.786, 1.0)
        return max(0.0, min(1.0, 1.0 - min(abs(retracement - x) for x in levels) * 2))

    def window_1_current_valuation(self) -> Dict[str, Any]:
        self._prune()
        if not self.ticks:
            return {
                "truth_status": "no_data",
                "generated_values": False,
                "reason": "no_fresh_provider_ticks",
            }
        latest = {symbol: history[-1] for symbol, history in self.ticks.items()}
        snapshot = MarketSnapshot(
            timestamp=time.time(),
            prices={symbol: tick.price for symbol, tick in latest.items()},
            source_event_ids=[tick.source_event_id for tick in latest.values()],
        )
        return asdict(snapshot)

    def window_2_live_stream(self) -> Dict[str, Any]:
        self._prune()
        observations = [
            asdict(tick) for history in self.ticks.values() for tick in history
        ]
        return {
            "truth_status": "provider_observed" if observations else "no_data",
            "generated_values": False,
            "ticks": observations,
            "reason": None if observations else "no_fresh_provider_ticks",
        }

    def ingest_prediction_receipt(self, payload: Dict[str, Any]) -> FuturePrediction:
        required = (
            "prediction_time",
            "symbol",
            "current_price",
            "predicted_price",
            "confidence",
            "source_id",
            "source_event_id",
            "source_timestamp",
            "truth_status",
            "generated_values",
        )
        if any(payload.get(name) is None for name in required):
            raise ValueError("complete external-model prediction receipt required")
        if payload["truth_status"] not in {"live", "provider_observed"}:
            raise ValueError("prediction must have a provider receipt")
        if payload["generated_values"] is not False:
            raise ValueError("generated_values must be false for adopted receipts")
        self._parse_timestamp(str(payload["source_timestamp"]))
        prediction = FuturePrediction(
            prediction_time=float(payload["prediction_time"]),
            symbol=str(payload["symbol"]),
            current_price=float(payload["current_price"]),
            predicted_price=float(payload["predicted_price"]),
            confidence=float(payload["confidence"]),
            source_id=str(payload["source_id"]),
            source_event_id=str(payload["source_event_id"]),
            source_timestamp=str(payload["source_timestamp"]),
            truth_status=str(payload["truth_status"]),
        )
        self.model_receipts[prediction.symbol] = prediction
        return prediction

    def window_3_future_snapshot(self) -> Dict[str, Any]:
        if not self.model_receipts:
            return {
                "truth_status": "no_data",
                "generated_values": False,
                "reason": "no_external_model_prediction_receipts",
                "predictions": [],
            }
        return {
            "truth_status": "provider_observed",
            "generated_values": False,
            "predictions": [asdict(item) for item in self.model_receipts.values()],
        }

    def run_complete_stream(self) -> Dict[str, Any]:
        return {
            "current": self.window_1_current_valuation(),
            "live": self.window_2_live_stream(),
            "future": self.window_3_future_snapshot(),
        }


def main() -> None:
    print(QuantumPredictionStream().run_complete_stream())


if __name__ == "__main__":
    main()
