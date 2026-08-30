import json
import time

from aureon.exchanges import capital_market_monitor as monitor


class _Client:
    enabled = True

    def __init__(self, quotes):
        self._quotes = quotes

    def get_tickers_for_symbols(self, symbols):
        return self._quotes


def _capital_receipt(now):
    return {
        "price": 1.25,
        "bid": 1.24,
        "ask": 1.26,
        "change_pct": 0.1,
        "epic": "CS.D.EURUSD.CFD.IP",
        "source_id": "capital_market:CS.D.EURUSD.CFD.IP",
        "source_timestamp": now - 2.0,
        "received_at": now - 1.0,
        "receipt_id": "capital-quote-1",
        "truth_status": "real_observed",
        "generated_values": False,
    }


def test_monitor_keeps_only_complete_observed_quote_receipts(monkeypatch):
    now = time.time()
    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"quoteResponse": {"result": [
                {"symbol": "AAPL", "bid": 99.0, "ask": 101.0,
                 "regularMarketPrice": 100.0, "regularMarketChangePercent": 0.5,
                 "regularMarketTime": now - 2.0, "marketState": "REGULAR"},
                {"symbol": "BAD", "bid": 101.0, "ask": 99.0,
                 "regularMarketPrice": 100.0, "regularMarketChangePercent": 0.5,
                 "regularMarketTime": now - 2.0},
            ]}}).encode("utf-8")

    monkeypatch.setattr(monitor.urllib.request, "urlopen", lambda *args, **kwargs: _Response())
    yahoo_quotes = monitor._fetch_yahoo_quotes(["AAPL", "BAD"])
    assert set(yahoo_quotes) == {"AAPL"}
    assert yahoo_quotes["AAPL"]["source_timestamp"] == now - 2.0
    assert yahoo_quotes["AAPL"]["receipt_id"].startswith("quote-")
    monkeypatch.setattr(monitor, "_fetch_yahoo_quotes", lambda symbols: yahoo_quotes)
    universe = {"symbols": [
        {"symbol": "AAPL", "yahoo_symbol": "AAPL", "epic": "AAPL"},
        {"symbol": "EURUSD", "yahoo_symbol": "", "epic": "CS.D.EURUSD.CFD.IP"},
    ]}
    payload = monitor._build_monitor_payload(_Client({"EURUSD": _capital_receipt(now)}), universe)
    assert payload["status"] == "real_observed"
    assert payload["generated_at"] >= now
    assert payload["prices"]["AAPL"]["source_timestamp"] == now - 2.0
    assert payload["prices"]["AAPL"]["receipt_id"] == yahoo_quotes["AAPL"]["receipt_id"]
    assert payload["prices"]["EURUSD"]["receipt_id"] == "capital-quote-1"

    monkeypatch.setattr(monitor, "_fetch_yahoo_quotes", lambda symbols: {})
    empty = monitor._build_monitor_payload(_Client({"EURUSD": {"price": 1.25}}), universe)
    assert empty["status"] == "no_data"
    assert empty["prices"] == {}
    assert empty["eligible_for_action"] is False
