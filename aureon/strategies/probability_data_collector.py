#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║     📊 PROBABILITY MATRIX DATA COLLECTOR 📊                                          ║
║     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                ║
║                                                                                      ║
║     Collects and analyzes real-time market data to calibrate                         ║
║     the HNC probability matrix and 6D harmonic waveform                              ║
║                                                                                      ║
║     COLLECTS:                                                                        ║
║       • Price movements and outcomes                                                 ║
║       • Coherence readings vs actual results                                         ║
║       • Frequency band performance                                                   ║
║       • Sentiment correlation                                                        ║
║       • 6D dimensional alignment accuracy                                            ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

import os
import json
import time
import logging
import math
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict

try:
    from aureon.exchanges.binance_client import get_binance_client
except ImportError:
    get_binance_client = None

logger = logging.getLogger(__name__)

BINANCE_TICKER_SOURCE_ID = "binance:/api/v3/ticker/24hr"
DEFAULT_TICKER_MAX_AGE_SECONDS = 120.0
DEFAULT_VALIDATION_HORIZON_SECONDS = 300.0
DEFAULT_VALIDATION_TOLERANCE_SECONDS = 30.0

@dataclass
class DataPoint:
    """Single market data observation"""
    timestamp: str
    symbol: str
    exchange: str
    price: float
    change_pct: float
    volume: float
    quote_volume: float
    open_price: float
    high_price: float
    low_price: float
    bid: float
    ask: float
    source_id: str
    source_timestamp: float
    provider_close_time_raw: Any
    received_at: str
    truth_status: str
    data_status: str
    generated_values: bool
    probability_score: Optional[float]
    probability_status: str
    probability_truth_status: str
    probability_source_id: Optional[str]
    probability_source_timestamp: Optional[float]
    probability_received_at: Optional[str]
    probability_generated_values: bool
    eligible_for_prediction: bool
    eligible_for_learning: bool
    outcome_1m: Optional[float] = None
    outcome_5m: Optional[float] = None

class ProbabilityCollector:
    def __init__(
        self,
        binance_client=None,
        *,
        output_file: str = "probability_matrix_data.jsonl",
        symbols: Optional[List[str]] = None,
        clock: Optional[Callable[[], float]] = None,
        ticker_max_age_seconds: float = DEFAULT_TICKER_MAX_AGE_SECONDS,
        validation_horizon_seconds: float = DEFAULT_VALIDATION_HORIZON_SECONDS,
        validation_tolerance_seconds: float = DEFAULT_VALIDATION_TOLERANCE_SECONDS,
        learning_sink: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        if binance_client is None:
            if get_binance_client is None:
                raise RuntimeError("no_data: Binance provider adapter is unavailable")
            binance_client = get_binance_client()
        if binance_client is None:
            raise RuntimeError("no_data: Binance provider client is unavailable")
        self.binance = binance_client
        self._clock = clock or time.time
        self.ticker_max_age_seconds = float(ticker_max_age_seconds)
        self.validation_horizon_seconds = float(validation_horizon_seconds)
        self.validation_tolerance_seconds = float(validation_tolerance_seconds)
        if min(
            self.ticker_max_age_seconds,
            self.validation_horizon_seconds,
            self.validation_tolerance_seconds,
        ) <= 0.0:
            raise ValueError("collector freshness and validation windows must be positive")
        self.learning_sink = learning_sink
        self.data_buffer: List[DataPoint] = []
        self.collection_interval = 60  # Collect every minute
        # 🔶 COMPREHENSIVE SYMBOLS (50+)
        default_symbols = [
            # TOP TIER
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT', 'AVAXUSDT',
            'DOTUSDT', 'ATOMUSDT', 'NEARUSDT', 'APTUSDT', 'SUIUSDT',
            # LAYER 2s
            'ARBUSDT', 'OPUSDT', 'MATICUSDT',
            # DEFI
            'UNIUSDT', 'AAVEUSDT', 'LINKUSDT',
            # AI
            'FETUSDT', 'INJUSDT', 'WLDUSDT',
            # MEMECOINS
            'DOGEUSDT', 'SHIBUSDT', 'PEPEUSDT', 'BONKUSDT', 'WIFUSDT',
            # MID CAPS
            'LTCUSDT', 'XLMUSDT', 'TRXUSDT', 'HBARUSDT',
        ]
        self.symbols = list(symbols) if symbols is not None else default_symbols
        self.output_file = output_file
        self.last_collection_receipt = self._no_data_receipt("collector_not_run")
        
        logger.info("Probability Collector Initialized")

    @staticmethod
    def _finite_number(
        value: Any,
        *,
        positive: bool = False,
        nonnegative: bool = False,
    ) -> Optional[float]:
        if value is None or isinstance(value, bool):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if not math.isfinite(number):
            return None
        if positive and number <= 0.0:
            return None
        if nonnegative and number < 0.0:
            return None
        return number

    @staticmethod
    def _timestamp_epoch(value: Any) -> Optional[float]:
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            timestamp = float(value)
            if not math.isfinite(timestamp) or timestamp <= 0.0:
                return None
            if timestamp >= 1e17:
                timestamp /= 1e9
            elif timestamp >= 1e14:
                timestamp /= 1e6
            elif timestamp >= 1e11:
                timestamp /= 1e3
            return timestamp
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            try:
                parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            except ValueError:
                return None
            if parsed.tzinfo is None:
                return None
            timestamp = parsed.timestamp()
            return timestamp if math.isfinite(timestamp) and timestamp > 0.0 else None
        return None

    @staticmethod
    def _iso_timestamp(timestamp: float) -> str:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()

    def _no_data_receipt(self, reason: str) -> Dict[str, Any]:
        received_at = self._iso_timestamp(float(self._clock()))
        return {
            "source_id": BINANCE_TICKER_SOURCE_ID,
            "source_timestamp": None,
            "received_at": received_at,
            "data_status": "no_data",
            "truth_status": "no_data",
            "reason": reason,
            "generated_values": False,
            "eligible_for_prediction": False,
            "eligible_for_learning": False,
        }

    def _normalize_ticker_receipt(
        self,
        requested_symbol: str,
        receipt: Any,
        *,
        received_epoch: float,
    ) -> Optional[Dict[str, Any]]:
        """Return a complete, fresh Binance 24-hour observation or no data."""
        if not isinstance(receipt, dict) or receipt.get("generated_values") is True:
            return None
        if "data_status" in receipt and receipt.get("data_status") != "live":
            return None
        if "truth_status" in receipt and receipt.get("truth_status") not in {
            "real_observed",
            "real_derived",
        }:
            return None
        symbol = str(receipt.get("symbol") or "").strip().upper()
        if not symbol or symbol != str(requested_symbol).strip().upper():
            return None

        price_change = self._finite_number(receipt.get("priceChange"))
        change_pct = self._finite_number(receipt.get("priceChangePercent"))
        weighted_price = self._finite_number(receipt.get("weightedAvgPrice"), positive=True)
        previous_close = self._finite_number(receipt.get("prevClosePrice"), positive=True)
        price = self._finite_number(receipt.get("lastPrice"), positive=True)
        last_quantity = self._finite_number(receipt.get("lastQty"), positive=True)
        bid = self._finite_number(receipt.get("bidPrice"), positive=True)
        bid_quantity = self._finite_number(receipt.get("bidQty"), positive=True)
        ask = self._finite_number(receipt.get("askPrice"), positive=True)
        ask_quantity = self._finite_number(receipt.get("askQty"), positive=True)
        open_price = self._finite_number(receipt.get("openPrice"), positive=True)
        high_price = self._finite_number(receipt.get("highPrice"), positive=True)
        low_price = self._finite_number(receipt.get("lowPrice"), positive=True)
        volume = self._finite_number(receipt.get("volume"), positive=True)
        quote_volume = self._finite_number(receipt.get("quoteVolume"), positive=True)
        identifiers = [
            self._finite_number(receipt.get("firstId"), nonnegative=True),
            self._finite_number(receipt.get("lastId"), nonnegative=True),
            self._finite_number(receipt.get("count"), positive=True),
        ]
        numeric_values = [
            price_change,
            change_pct,
            weighted_price,
            previous_close,
            price,
            last_quantity,
            bid,
            bid_quantity,
            ask,
            ask_quantity,
            open_price,
            high_price,
            low_price,
            volume,
            quote_volume,
            *identifiers,
        ]
        if any(value is None for value in numeric_values):
            return None
        assert price_change is not None and change_pct is not None
        assert weighted_price is not None and previous_close is not None and price is not None
        assert bid is not None and ask is not None and open_price is not None
        assert high_price is not None and low_price is not None
        assert volume is not None and quote_volume is not None
        first_id, last_id, trade_count = identifiers
        assert first_id is not None and last_id is not None and trade_count is not None
        if any(not value.is_integer() for value in (first_id, last_id, trade_count)):
            return None
        if first_id > last_id or bid > ask:
            return None
        if not (
            low_price <= open_price <= high_price
            and low_price <= previous_close <= high_price
            and low_price <= price <= high_price
            and low_price <= weighted_price <= high_price
        ):
            return None

        expected_change = price - open_price
        if not math.isclose(price_change, expected_change, rel_tol=1e-6, abs_tol=1e-8):
            return None
        expected_change_pct = (expected_change / open_price) * 100.0
        if not math.isclose(change_pct, expected_change_pct, rel_tol=1e-4, abs_tol=0.02):
            return None

        open_timestamp = self._timestamp_epoch(receipt.get("openTime"))
        source_timestamp = self._timestamp_epoch(receipt.get("closeTime"))
        if open_timestamp is None or source_timestamp is None or source_timestamp <= open_timestamp:
            return None
        window_seconds = source_timestamp - open_timestamp
        if not (23.0 * 60.0 * 60.0 <= window_seconds <= 25.0 * 60.0 * 60.0):
            return None
        if source_timestamp >= received_epoch:
            return None
        if received_epoch - source_timestamp > self.ticker_max_age_seconds:
            return None

        return {
            "symbol": symbol,
            "price": price,
            "change_pct": change_pct,
            "volume": volume,
            "quote_volume": quote_volume,
            "open_price": open_price,
            "high_price": high_price,
            "low_price": low_price,
            "bid": bid,
            "ask": ask,
            "source_id": BINANCE_TICKER_SOURCE_ID,
            "source_timestamp": source_timestamp,
            "provider_close_time_raw": receipt.get("closeTime"),
            "received_at": self._iso_timestamp(received_epoch),
            "truth_status": "real_observed",
            "data_status": "live",
            "generated_values": False,
        }
        
    def collect_snapshot(self) -> List[DataPoint]:
        """Collects a snapshot of current market state and probability readings"""
        collected: List[DataPoint] = []
        get_ticker = getattr(self.binance, "get_24h_ticker", None)
        if not callable(get_ticker):
            self.last_collection_receipt = self._no_data_receipt("binance_24h_ticker_method_unavailable")
            return collected
        
        for symbol in self.symbols:
            try:
                ticker = get_ticker(symbol)
                received_epoch = float(self._clock())
                normalized = self._normalize_ticker_receipt(
                    symbol,
                    ticker,
                    received_epoch=received_epoch,
                )
                if normalized is None:
                    logger.warning("no_data: incomplete or stale Binance 24h receipt for %s", symbol)
                    continue
                
                dp = DataPoint(
                    timestamp=self._iso_timestamp(normalized["source_timestamp"]),
                    symbol=normalized["symbol"],
                    exchange="BINANCE",
                    price=normalized["price"],
                    change_pct=normalized["change_pct"],
                    volume=normalized["volume"],
                    quote_volume=normalized["quote_volume"],
                    open_price=normalized["open_price"],
                    high_price=normalized["high_price"],
                    low_price=normalized["low_price"],
                    bid=normalized["bid"],
                    ask=normalized["ask"],
                    source_id=normalized["source_id"],
                    source_timestamp=normalized["source_timestamp"],
                    provider_close_time_raw=normalized["provider_close_time_raw"],
                    received_at=normalized["received_at"],
                    truth_status=normalized["truth_status"],
                    data_status=normalized["data_status"],
                    generated_values=False,
                    probability_score=None,
                    probability_status="no_data",
                    probability_truth_status="no_data",
                    probability_source_id=None,
                    probability_source_timestamp=None,
                    probability_received_at=None,
                    probability_generated_values=False,
                    eligible_for_prediction=False,
                    eligible_for_learning=False,
                )
                
                self.data_buffer.append(dp)
                collected.append(dp)
                logger.info("Collected %s market observation with no proven probability", symbol)
                
            except Exception as e:
                logger.error(f"Error collecting {symbol}: {e}")

        if collected:
            self.last_collection_receipt = {
                "source_id": BINANCE_TICKER_SOURCE_ID,
                "source_timestamp": min(point.source_timestamp for point in collected),
                "received_at": max(point.received_at for point in collected),
                "data_status": "live",
                "truth_status": "real_observed",
                "observation_count": len(collected),
                "probability_status": "no_data",
                "generated_values": False,
                "eligible_for_prediction": False,
                "eligible_for_learning": False,
            }
        else:
            self.last_collection_receipt = self._no_data_receipt("no_complete_fresh_binance_24h_receipts")
        return collected

    def save_data(self):
        """Saves buffered data to disk"""
        if not self.data_buffer:
            return
            
        try:
            with open(self.output_file, 'a') as f:
                for dp in self.data_buffer:
                    f.write(json.dumps(asdict(dp)) + "\n")
            
            logger.info(f"Saved {len(self.data_buffer)} data points to {self.output_file}")
            self.data_buffer = [] # Clear buffer
        except Exception as e:
            logger.error(f"Error saving data: {e}")

    def _normalize_persisted_market_row(self, row: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(row, dict):
            return None
        if (
            row.get("data_status") != "live"
            or row.get("truth_status") != "real_observed"
            or row.get("generated_values") is not False
            or row.get("source_id") != BINANCE_TICKER_SOURCE_ID
            or str(row.get("exchange") or "").upper() != "BINANCE"
        ):
            return None
        symbol = str(row.get("symbol") or "").strip().upper()
        if not symbol:
            return None

        source_timestamp = self._timestamp_epoch(row.get("source_timestamp"))
        timestamp_field = self._timestamp_epoch(row.get("timestamp"))
        provider_close_timestamp = self._timestamp_epoch(row.get("provider_close_time_raw"))
        received_timestamp = self._timestamp_epoch(row.get("received_at"))
        if any(
            value is None
            for value in (
                source_timestamp,
                timestamp_field,
                provider_close_timestamp,
                received_timestamp,
            )
        ):
            return None
        assert source_timestamp is not None and timestamp_field is not None
        assert provider_close_timestamp is not None and received_timestamp is not None
        if not math.isclose(timestamp_field, source_timestamp, abs_tol=1e-3):
            return None
        if not math.isclose(provider_close_timestamp, source_timestamp, abs_tol=1e-3):
            return None
        if source_timestamp >= received_timestamp:
            return None
        if received_timestamp - source_timestamp > self.ticker_max_age_seconds:
            return None

        price = self._finite_number(row.get("price"), positive=True)
        change_pct = self._finite_number(row.get("change_pct"))
        volume = self._finite_number(row.get("volume"), positive=True)
        quote_volume = self._finite_number(row.get("quote_volume"), positive=True)
        open_price = self._finite_number(row.get("open_price"), positive=True)
        high_price = self._finite_number(row.get("high_price"), positive=True)
        low_price = self._finite_number(row.get("low_price"), positive=True)
        bid = self._finite_number(row.get("bid"), positive=True)
        ask = self._finite_number(row.get("ask"), positive=True)
        if any(
            value is None
            for value in (
                price,
                change_pct,
                volume,
                quote_volume,
                open_price,
                high_price,
                low_price,
                bid,
                ask,
            )
        ):
            return None
        assert price is not None and change_pct is not None
        assert open_price is not None and high_price is not None and low_price is not None
        assert bid is not None and ask is not None
        if bid > ask or not (low_price <= open_price <= high_price and low_price <= price <= high_price):
            return None
        expected_change_pct = ((price - open_price) / open_price) * 100.0
        if not math.isclose(change_pct, expected_change_pct, rel_tol=1e-4, abs_tol=0.02):
            return None

        return {
            **row,
            "symbol": symbol,
            "_source_timestamp": source_timestamp,
            "_received_timestamp": received_timestamp,
            "_price": price,
        }

    def _proof_eligible_probability(self, row: Dict[str, Any]) -> Optional[float]:
        if (
            row.get("probability_status") != "live"
            or row.get("probability_truth_status") not in {"real_observed", "real_derived"}
            or row.get("probability_generated_values") is not False
            or row.get("eligible_for_prediction") is not True
            or row.get("eligible_for_learning") is not True
        ):
            return None
        source_id = str(row.get("probability_source_id") or "").strip()
        if not source_id or "hnc" not in source_id.lower():
            return None
        score = self._finite_number(row.get("probability_score"), nonnegative=True)
        probability_source_timestamp = self._timestamp_epoch(row.get("probability_source_timestamp"))
        probability_received_timestamp = self._timestamp_epoch(row.get("probability_received_at"))
        if score is None or score > 1.0:
            return None
        if probability_source_timestamp is None or probability_received_timestamp is None:
            return None
        if not math.isclose(
            probability_source_timestamp,
            row["_source_timestamp"],
            abs_tol=1e-3,
        ):
            return None
        if probability_received_timestamp <= probability_source_timestamp:
            return None
        if probability_received_timestamp - probability_source_timestamp > self.ticker_max_age_seconds:
            return None
        return score

    def _validation_no_data(self, reason: str) -> Dict[str, Any]:
        return {
            "data_status": "no_data",
            "truth_status": "no_data",
            "reason": reason,
            "validation_horizon_seconds": self.validation_horizon_seconds,
            "total_predictions": None,
            "correct_predictions": None,
            "accuracy_pct": None,
            "generated_values": False,
            "eligible_for_learning": False,
        }

    def _feed_validation_learning(self, report: Dict[str, Any]) -> None:
        if report.get("eligible_for_learning") is not True:
            return
        if self.learning_sink is not None:
            self.learning_sink(report)
            return
        try:
            from aureon.autonomous.aureon_autonomy_hub import get_autonomy_hub

            hub = get_autonomy_hub()
            with hub.feedback_loop._lock:
                accuracy = hub.feedback_loop._predictor_accuracy['probability_collector']
                accuracy['total'] = report['total_predictions']
                accuracy['correct'] = report['correct_predictions']
                accuracy['incorrect'] = report['incorrect_predictions']
        except Exception as exc:
            logger.warning("Proof-eligible validation learning sink unavailable: %s", type(exc).__name__)

    def validate_predictions(self) -> Dict[str, Any]:
        """Validate proven predictions against same-symbol observations at the real horizon."""
        if not os.path.exists(self.output_file):
            return self._validation_no_data("observation_ledger_missing")

        logger.info("Validating proof-eligible probability predictions")
        observations: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        try:
            with open(self.output_file, 'r') as handle:
                for line in handle:
                    try:
                        raw = json.loads(line)
                    except (TypeError, ValueError, json.JSONDecodeError):
                        continue
                    normalized = self._normalize_persisted_market_row(raw)
                    if normalized is not None:
                        observations[normalized["symbol"]].append(normalized)
        except Exception as exc:
            logger.error("Validation read error: %s", type(exc).__name__)
            return self._validation_no_data("observation_ledger_unreadable")

        validated_rows: List[Dict[str, Any]] = []
        for symbol, rows in observations.items():
            rows.sort(key=lambda item: item["_source_timestamp"])
            for prediction_row in rows:
                score = self._proof_eligible_probability(prediction_row)
                if score is None:
                    continue
                target_timestamp = prediction_row["_source_timestamp"] + self.validation_horizon_seconds
                horizon_start = target_timestamp - self.validation_tolerance_seconds
                horizon_end = target_timestamp + self.validation_tolerance_seconds
                candidates = [
                    candidate
                    for candidate in rows
                    if (
                        candidate["_source_timestamp"] > prediction_row["_source_timestamp"]
                        and horizon_start <= candidate["_source_timestamp"] <= horizon_end
                    )
                ]
                future_row = min(
                    candidates,
                    key=lambda candidate: abs(candidate["_source_timestamp"] - target_timestamp),
                    default=None,
                )
                if future_row is None:
                    continue
                actual_horizon = future_row["_source_timestamp"] - prediction_row["_source_timestamp"]
                if abs(actual_horizon - self.validation_horizon_seconds) > self.validation_tolerance_seconds:
                    continue

                price_change = (future_row["_price"] - prediction_row["_price"]) / prediction_row["_price"]
                prediction = "UP" if score > 0.55 else "DOWN" if score < 0.45 else "NEUTRAL"
                outcome = "UP" if price_change > 0.001 else "DOWN" if price_change < -0.001 else "NEUTRAL"
                if prediction == "NEUTRAL":
                    continue
                validated_rows.append({
                    "symbol": symbol,
                    "prediction_source_timestamp": prediction_row["_source_timestamp"],
                    "outcome_source_timestamp": future_row["_source_timestamp"],
                    "actual_horizon_seconds": actual_horizon,
                    "prediction": prediction,
                    "outcome": outcome,
                    "correct": prediction == outcome,
                    "generated_values": False,
                })

        if not validated_rows:
            logger.info("No proof-eligible predictions have reached their validation horizon")
            return self._validation_no_data("proof_eligible_prediction_and_horizon_pair_required")

        total_predictions = len(validated_rows)
        correct_predictions = sum(1 for row in validated_rows if row["correct"])
        report = {
            "data_status": "live",
            "truth_status": "real_derived",
            "validation_horizon_seconds": self.validation_horizon_seconds,
            "total_predictions": total_predictions,
            "correct_predictions": correct_predictions,
            "incorrect_predictions": total_predictions - correct_predictions,
            "accuracy_pct": (correct_predictions / total_predictions) * 100.0,
            "validated_rows": validated_rows,
            "generated_values": False,
            "eligible_for_learning": True,
        }
        self._feed_validation_learning(report)
        logger.info(
            "Validation complete: %.2f%% accuracy (%s/%s)",
            report["accuracy_pct"],
            correct_predictions,
            total_predictions,
        )
        return report

    def run(self):
        """Main collection loop"""
        logger.info("Starting Data Collection Loop...")
        while True:
            try:
                self.collect_snapshot()
                self.save_data()
                
                # Run validation every 5 cycles
                if len(self.data_buffer) == 0: # Just saved
                     self.validate_predictions()
                
                # Sleep for interval
                time.sleep(self.collection_interval)
                
            except KeyboardInterrupt:
                logger.info("Stopping collector...")
                break
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                time.sleep(5)

if __name__ == "__main__":
    collector = ProbabilityCollector()
    collector.run()
