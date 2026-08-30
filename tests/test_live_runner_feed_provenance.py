"""Provider-provenance contracts for the Queen live runner.

The runner is intentionally provider-only: it publishes complete fresh Binance
observations, emits explicit no_data for unavailable surfaces, and never
recreates the retired simulated market, whale, or bot feeds.
"""

from __future__ import annotations

import importlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest


@dataclass
class _RecordingBus:
    rows: list[dict[str, Any]] = field(default_factory=list)

    def think(self, content: str = "", topic: str = "", source: str = "", **kwargs: Any) -> None:
        self.rows.append(
            {
                "content": content,
                "topic": topic,
                "source": source,
                "payload": kwargs.get("payload"),
            }
        )


@pytest.fixture
def runner(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
    monkeypatch.setenv("AUREON_AUDIT_MODE", "1")
    monkeypatch.setenv("AUREON_THOUGHTS_FILE", str(tmp_path / "thoughts.jsonl"))
    monkeypatch.setenv("AUREON_THOUGHT_BUS_PATH", str(tmp_path / "bus.jsonl"))
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path / "bus-traces"))
    monkeypatch.delenv("AUREON_REDIS_URL", raising=False)

    import aureon.trading.aureon_queen_live_runner as lr

    importlib.reload(lr)
    bus = _RecordingBus()
    lr._thought_bus = bus
    return lr, bus


def _observation(lr, symbol: str = "BTC/USD", **overrides: Any):
    provider_symbol = symbol.replace("/", "").replace("USD", "USDT")
    now = time.time()
    values = {
        "symbol": symbol,
        "provider_symbol": provider_symbol,
        "price": 61_234.5,
        "bid": 61_233.0,
        "ask": 61_236.0,
        "base_volume_24h": 123.5,
        "quote_volume_24h": 7_500_000.0,
        "change_percent_24h": 1.25,
        "provider_timestamp": now - 1.0,
        "collected_at": now,
        "source_id": lr.BINANCE_SOURCE_ID,
        "source_url": "https://api.binance.com/api/v3/ticker/24hr",
        "source_event_id": f"{provider_symbol}:receipt",
        "freshness_ttl_sec": lr.FRESHNESS_TTL_SECONDS,
    }
    values.update(overrides)
    return lr.MarketObservation(**values)


def _ticker_rows(lr, *, timestamp: float | None = None) -> list[dict[str, str | int]]:
    close_time_ms = int((timestamp or time.time()) * 1000)
    return [
        {
            "symbol": provider_symbol,
            "lastPrice": "100.5",
            "bidPrice": "100.4",
            "askPrice": "100.6",
            "volume": "12.5",
            "quoteVolume": "1256.25",
            "priceChangePercent": "1.5",
            "closeTime": close_time_ms,
        }
        for provider_symbol in lr.BinancePublicMarketFeed.SYMBOLS.values()
    ]


class _Response:
    def __init__(self, payload: Any, status: int = 200):
        self.status = status
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def test_thought_stream_override_and_default_match_shared_root(runner, monkeypatch):
    lr, _ = runner
    assert Path(os.environ["AUREON_THOUGHTS_FILE"]) == lr.THOUGHTS_FILE

    monkeypatch.delenv("AUREON_THOUGHTS_FILE")
    assert lr._resolve_thoughts_file() == Path(lr.__file__).resolve().parents[2] / "thoughts.jsonl"


def test_simple_bus_writes_only_to_explicit_path(runner, tmp_path):
    lr, _ = runner
    path = tmp_path / "fallback" / "thoughts.jsonl"
    bus = lr.SimpleThoughtBus(path)
    bus.think(topic="market.status", source="test", payload={"truth_status": "no_data"})

    row = json.loads(path.read_text(encoding="utf-8"))
    assert row["topic"] == "market.status"
    assert row["source"] == "test"
    assert row["payload"] == {"truth_status": "no_data"}


def test_provider_feed_parses_complete_fresh_observations(runner, monkeypatch):
    lr, _ = runner
    captured: dict[str, Any] = {}

    def fake_urlopen(request, timeout):
        captured.update(url=request.full_url, timeout=timeout)
        return _Response(_ticker_rows(lr))

    monkeypatch.setattr(lr.urllib.request, "urlopen", fake_urlopen)
    observations = lr.BinancePublicMarketFeed(timeout_seconds=3.5).fetch()

    assert set(observations) == set(lr.BinancePublicMarketFeed.SYMBOLS)
    assert captured["timeout"] == 3.5
    assert captured["url"].startswith(f"{lr.BINANCE_API_BASE}/api/v3/ticker/24hr?")
    btc = observations["BTC/USD"]
    assert btc.price == pytest.approx(100.5)
    assert btc.bid == pytest.approx(100.4)
    assert btc.ask == pytest.approx(100.6)
    assert btc.truth_status == "live"
    assert btc.generated is False
    assert btc.source_id == lr.BINANCE_SOURCE_ID
    assert btc.source_event_id.startswith("BTCUSDT:")


@pytest.mark.parametrize(
    ("rows_factory", "error"),
    [
        (lambda lr: _ticker_rows(lr, timestamp=time.time() - 500), "BINANCE_TICKER_STALE"),
        (lambda lr: _ticker_rows(lr)[:-1], "BINANCE_TICKERS_MISSING"),
        (
            lambda lr: [
                {**row, "lastPrice": "0"} if row["symbol"] == "BTCUSDT" else row
                for row in _ticker_rows(lr)
            ],
            "BINANCE_TICKER_NONPOSITIVE",
        ),
    ],
)
def test_provider_feed_rejects_stale_missing_or_nonpositive_rows(
    runner, monkeypatch, rows_factory, error
):
    lr, _ = runner
    monkeypatch.setattr(
        lr.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _Response(rows_factory(lr)),
    )
    with pytest.raises(RuntimeError, match=error):
        lr.BinancePublicMarketFeed().fetch()


def test_provider_feed_rejects_non_list_and_http_error(runner, monkeypatch):
    lr, _ = runner
    monkeypatch.setattr(
        lr.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _Response({"symbol": "BTCUSDT"}),
    )
    with pytest.raises(RuntimeError, match="BINANCE_TICKER_RESPONSE_INVALID"):
        lr.BinancePublicMarketFeed().fetch()

    monkeypatch.setattr(
        lr.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _Response([], status=503),
    )
    with pytest.raises(RuntimeError, match="BINANCE_HTTP_503"):
        lr.BinancePublicMarketFeed().fetch()


def test_provider_failure_emits_only_explicit_no_data(runner):
    lr, bus = runner

    class FailingFeed:
        def fetch(self):
            raise TimeoutError("offline")

    result = lr.QueenLiveRunner(feed=FailingFeed()).run_cycle()

    assert result["truth_status"] == "no_data"
    assert result["generated"] is False
    assert result["reason"] == "MARKET_PROVIDER_UNAVAILABLE:TimeoutError:offline"
    assert [row["topic"] for row in bus.rows] == ["market.status"]
    assert bus.rows[0]["payload"] == result


def test_successful_cycle_preserves_provider_values_and_lineage(runner):
    lr, bus = runner
    observations = {
        "BTC/USD": _observation(lr, "BTC/USD", provider_timestamp=100.0),
        "ETH/USD": _observation(
            lr,
            "ETH/USD",
            price=3_200.25,
            provider_timestamp=101.0,
        ),
    }

    class Feed:
        def fetch(self):
            return observations

    heartbeat = lr.QueenLiveRunner(feed=Feed()).run_cycle()
    prices = [row for row in bus.rows if row["topic"] == "market.price"]

    assert len(prices) == 2
    assert prices[0]["payload"]["price"] == pytest.approx(61_234.5)
    assert prices[1]["payload"]["price"] == pytest.approx(3_200.25)
    assert {row["payload"]["truth_status"] for row in prices} == {"live"}
    assert {row["payload"]["generated"] for row in prices} == {False}
    assert heartbeat["truth_status"] == "real_derived"
    assert heartbeat["market_observation_count"] == 2
    assert heartbeat["source_timestamp"] == 100.0
    assert heartbeat["source_event_ids"] == sorted(
        observation.source_event_id for observation in observations.values()
    )


def test_unobserved_surfaces_are_no_data_not_measurements(runner):
    lr, bus = runner

    class Feed:
        def fetch(self):
            return {"BTC/USD": _observation(lr)}

    lr.QueenLiveRunner(feed=Feed()).run_cycle()
    by_topic = {row["topic"]: row["payload"] for row in bus.rows}

    for topic, reason in lr.QueenLiveRunner._unavailable_surfaces():
        assert by_topic[topic]["truth_status"] == "no_data"
        assert by_topic[topic]["generated"] is False
        assert by_topic[topic]["reason"] == reason
        assert isinstance(by_topic[topic]["collected_at"], float)
    assert "market.momentum" not in by_topic
    assert "whale.orderbook" not in by_topic
    assert "bot.detected" not in by_topic


def test_cycle_topics_and_truth_statuses_are_complete(runner):
    lr, bus = runner

    class Feed:
        def fetch(self):
            return {"BTC/USD": _observation(lr)}

    lr.QueenLiveRunner(feed=Feed()).run_cycle()
    topics = [row["topic"] for row in bus.rows]
    assert topics == [
        "market.price",
        "scanner.status",
        "whale.status",
        "bot.status",
        "queen.decision",
        "system.heartbeat",
    ]
    assert all(
        row["payload"]["truth_status"] in {"live", "real_derived", "no_data"}
        for row in bus.rows
    )
    assert all(row["payload"]["generated"] is False for row in bus.rows)


def test_invalid_interval_is_rejected(runner):
    lr, _ = runner
    with pytest.raises(ValueError, match="interval must be positive"):
        lr.QueenLiveRunner(interval=0)


def test_stop_emits_derived_shutdown_without_starting_thread(runner):
    lr, bus = runner
    live_runner = lr.QueenLiveRunner(feed=object())
    live_runner.running = True
    live_runner.cycle_count = 7
    live_runner.stop()

    assert live_runner.running is False
    assert bus.rows[-1]["topic"] == "system.shutdown"
    assert bus.rows[-1]["payload"]["truth_status"] == "real_derived"
    assert bus.rows[-1]["payload"]["generated"] is False
    assert bus.rows[-1]["payload"]["cycles_completed"] == 7
