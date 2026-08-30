import time
from collections import deque

from aureon.bridges.aureon_hnc_live_connector import HncLiveConnector


class _Detector:
    analysis_window_size = 32

    def __init__(self):
        self.price_history = {}
        self.ticks = []

    def add_price_tick(self, symbol, price):
        self.ticks.append((symbol, price))
        self.price_history.setdefault(symbol, deque(maxlen=32)).append(price)

    def detect_surge(self, symbol):
        return None


class _Hub:
    def __init__(self):
        self.published = []

    def _publish_to_bus(self, topic, data):
        self.published.append((topic, data))
        return True


def _connector():
    connector = HncLiveConnector.__new__(HncLiveConnector)
    connector.symbols = ["BTC/USD"]
    connector.detector = _Detector()
    connector.hub = _Hub()
    connector.thought_bus = None
    connector.qgita = None
    connector.bot_shape_scanner = None
    connector._source_timestamp_history = {}
    connector._receipt_id_history = {}
    connector._last_receipt = {}
    return connector


def test_bare_or_generated_ticks_are_rejected_without_detector_or_bus_mutation():
    connector = _connector()
    connector._hub_event_handler("market.ticker.BTCUSD", {"symbol": "BTCUSD", "price": 100.0})
    assert connector.detector.ticks == []
    now = time.time()
    connector._hub_event_handler("market.ticker.BTCUSD", {
        "data_status": "live", "symbol": "BTCUSD", "price": 100.0,
        "source_id": "provider.binance", "source_timestamp": now - 1,
        "received_at": now, "receipt_id": "tick-1", "truth_status": "real_observed",
        "generated_values": True,
    })
    assert connector.detector.ticks == []
    connector._hub_event_handler("market.ticker.BTCUSD", {
        "data_status": "live", "symbol": "BTCUSD", "price": 100.0,
        "source_id": "provider.binance", "source_timestamp": now - 1,
        "received_at": now, "receipt_id": "tick-2", "truth_status": "real_observed",
        "generated_values": False,
    })
    assert connector.detector.ticks == [("BTC/USD", 100.0)]
    assert list(connector._source_timestamp_history["BTC/USD"]) == [now - 1]
    assert connector.hub.published == []
