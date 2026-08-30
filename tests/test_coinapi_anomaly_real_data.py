from __future__ import annotations

import io
import os
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")

from aureon.exchanges import coinapi_anomaly_detector as module


class FakeCoinAPIClient:
    def __init__(self, *, quotes=None, orderbook=None, trades=None):
        self.quotes = list(quotes or [])
        self.orderbook = orderbook
        self.trades = list(trades or [])

    def get_quotes_current(self, _symbol_filter):
        return list(self.quotes)

    def get_orderbook_current(self, _symbol_id):
        return self.orderbook

    def get_trades_latest(self, _symbol_id, limit=100):
        return list(self.trades[:limit])


class CoinAPIRealDataTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)

    def point(self, exchange: str, price: float) -> module.ExchangeDataPoint:
        return module.ExchangeDataPoint(
            exchange_id=exchange,
            symbol="BTC/USD",
            price=price,
            volume_24h=None,
            bid=price - 0.5,
            ask=price + 0.5,
            timestamp=self.now,
            received_at=self.now,
            source_id=f"coinapi_quote:{exchange}_SPOT_BTC_USD",
        )

    def test_quote_ingestion_rejects_missing_crossed_and_stale_values(self):
        fresh = self.now.isoformat()
        stale = (self.now - timedelta(hours=1)).isoformat()
        client = FakeCoinAPIClient(quotes=[
            {
                "symbol_id": "KRAKEN_SPOT_BTC_USD",
                "bid": 100.0,
                "ask": 101.0,
                "time_exchange": fresh,
            },
            {
                "symbol_id": "MISSING_SPOT_BTC_USD",
                "ask": 101.0,
                "time_exchange": fresh,
            },
            {
                "symbol_id": "CROSSED_SPOT_BTC_USD",
                "bid": 102.0,
                "ask": 101.0,
                "time_exchange": fresh,
            },
            {
                "symbol_id": "STALE_SPOT_BTC_USD",
                "bid": 100.0,
                "ask": 101.0,
                "time_exchange": stale,
            },
        ])

        points = module.AnomalyDetector(client).fetch_multi_exchange_data("BTC", "USD")

        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].exchange_id, "KRAKEN")
        self.assertEqual(points[0].price, 100.5)
        self.assertIsNone(points[0].volume_24h)
        self.assertEqual(points[0].truth_status, "real_derived")
        self.assertFalse(points[0].generated_values)

    def test_no_quotes_is_explicit_no_data_without_numeric_placeholders(self):
        analysis = module.AnomalyDetector(FakeCoinAPIClient()).analyze_symbol("BTC", "USD")

        self.assertEqual(analysis["truth_status"], "no_data")
        self.assertIsNone(analysis["mean_price"])
        self.assertIsNone(analysis["price_std"])
        self.assertIsNone(analysis["source_timestamp"])
        self.assertFalse(analysis["eligible_for_learning"])
        self.assertFalse(analysis["eligible_for_external_action"])

    def test_price_anomaly_confidence_and_timestamp_come_from_fresh_evidence(self):
        older = self.now - timedelta(seconds=10)
        points = [self.point("KRAKEN", 100.0), self.point("COINBASE", 110.0)]
        points[0].timestamp = older
        detector = module.AnomalyDetector(FakeCoinAPIClient())

        anomalies = detector.detect_price_manipulation(points)

        self.assertEqual(len(anomalies), 2)
        self.assertEqual(anomalies[0].confidence, 0.2)
        self.assertEqual(anomalies[0].source_timestamp, older)
        self.assertEqual(anomalies[0].truth_status, "real_derived")
        self.assertFalse(anomalies[0].generated_values)
        self.assertFalse(anomalies[0].eligible_for_external_action)

    def test_orderbook_requires_complete_fresh_depth(self):
        missing_size = {
            "time_exchange": self.now.isoformat(),
            "bids": [{"price": 100.0}],
            "asks": [{"price": 101.0, "size": 1.0}],
        }
        self.assertIsNone(
            module.AnomalyDetector(
                FakeCoinAPIClient(orderbook=missing_size)
            ).detect_orderbook_spoofing("KRAKEN_SPOT_BTC_USD")
        )

        complete = {
            "time_exchange": self.now.isoformat(),
            "bids": [{"price": 100.0, "size": 9.0}],
            "asks": [{"price": 101.0, "size": 1.0}],
        }
        anomaly = module.AnomalyDetector(
            FakeCoinAPIClient(orderbook=complete)
        ).detect_orderbook_spoofing("KRAKEN_SPOT_BTC_USD")

        self.assertIsNotNone(anomaly)
        self.assertEqual(anomaly.confidence, 0.1)
        self.assertEqual(anomaly.source_timestamp, self.now)
        self.assertEqual(anomaly.evidence["levels_observed"], 2)

    def test_wash_pattern_requires_at_least_ten_complete_fresh_trades(self):
        incomplete = [
            {
                "price": 100.0,
                "size": 1.0,
                "time_exchange": self.now.isoformat(),
            }
            for _ in range(9)
        ]
        incomplete.append({
            "size": 1.0,
            "time_exchange": self.now.isoformat(),
        })
        self.assertIsNone(
            module.AnomalyDetector(
                FakeCoinAPIClient(trades=incomplete)
            ).detect_wash_trading("KRAKEN_SPOT_BTC_USD")
        )

        complete = [
            {
                "price": 100.0,
                "size": 1.0,
                "time_exchange": self.now.isoformat(),
            }
            for _ in range(20)
        ]
        anomaly = module.AnomalyDetector(
            FakeCoinAPIClient(trades=complete)
        ).detect_wash_trading("KRAKEN_SPOT_BTC_USD")

        self.assertIsNotNone(anomaly)
        self.assertEqual(anomaly.confidence, 0.2)
        self.assertEqual(anomaly.evidence["total_observed_volume"], 20.0)
        self.assertEqual(anomaly.source_id, "coinapi_trades:KRAKEN_SPOT_BTC_USD")

    def test_cross_exchange_spread_is_observable_but_not_executable(self):
        detector = module.AnomalyDetector(FakeCoinAPIClient())
        anomalies = detector.detect_cross_exchange_arbitrage([
            self.point("KRAKEN", 100.0),
            self.point("COINBASE", 104.0),
        ])

        self.assertEqual(len(anomalies), 1)
        anomaly = anomalies[0]
        self.assertFalse(anomaly.eligible_for_external_action)
        self.assertFalse(anomaly.evidence["fees_transfers_and_fillability_verified"])
        refinement = detector.refine_algorithm(anomaly)
        self.assertEqual(refinement["truth_status"], "real_derived")
        self.assertEqual(
            refinement["adjustment"]["external_action"],
            "blocked_pending_cost_and_fill_receipts",
        )

    def test_stale_anomaly_cannot_enter_refinement_log(self):
        stale = self.now - timedelta(hours=1)
        anomaly = module.MarketAnomaly(
            anomaly_type=module.AnomalyType.PRICE_MANIPULATION,
            symbol="BTC/USD",
            exchange="KRAKEN",
            timestamp=stale,
            severity=0.5,
            confidence=0.5,
            description="stale observation",
            evidence={},
            recommendation="REVIEW",
            truth_status="real_derived",
            source_id="coinapi_quote:KRAKEN_SPOT_BTC_USD",
            source_timestamp=stale,
            received_at=self.now,
        )
        detector = module.AnomalyDetector(FakeCoinAPIClient())

        refinement = detector.refine_algorithm(anomaly)

        self.assertEqual(refinement["truth_status"], "no_data")
        self.assertFalse(refinement["eligible_for_learning"])
        self.assertEqual(detector.refinement_log, [])

    def test_no_data_report_does_not_claim_market_is_clean(self):
        analysis = module.AnomalyDetector(FakeCoinAPIClient()).analyze_symbol("BTC", "USD")
        output = io.StringIO()

        with redirect_stdout(output):
            module.AnomalyDetector(FakeCoinAPIClient()).print_anomaly_report(analysis)

        rendered = output.getvalue()
        self.assertIn("NO DATA", rendered)
        self.assertNotIn("data looks clean", rendered)

    def test_live_entry_requires_key_before_runtime_wiring(self):
        with patch.dict(os.environ, {"COINAPI_KEY": ""}):
            with patch.object(module, "_link_runtime_system") as link:
                with self.assertRaisesRegex(RuntimeError, "COINAPI_KEY missing"):
                    module.run_live_anomaly_detection()
        link.assert_not_called()
        self.assertFalse(hasattr(module, "demo_with_simulated_data"))


if __name__ == "__main__":
    unittest.main()
