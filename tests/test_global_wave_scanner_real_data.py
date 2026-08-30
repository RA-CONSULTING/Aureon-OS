from __future__ import annotations

import asyncio
import math
import time
from pathlib import Path

from aureon.scanners import aureon_global_wave_scanner as wave
from scripts.validation.validate_real_data_contract import scan_text_file


def _scanner() -> wave.GlobalWaveScanner:
    scanner = object.__new__(wave.GlobalWaveScanner)
    scanner._use_sse_tickers = False
    scanner.scanner_bridge = None
    scanner.kraken = None
    scanner.binance = None
    scanner.alpaca = None
    scanner.last_no_data = {}
    scanner._dynamic_tier_1 = wave.TIER_1_THRESHOLD
    scanner._dynamic_tier_2 = wave.TIER_2_THRESHOLD
    scanner._dynamic_tier_3 = wave.TIER_3_THRESHOLD
    return scanner


def _ticker(now: float) -> dict:
    return {
        "price": 101.0,
        "change24h": 4.0,
        "volume": 2_000_000.0,
        "high": 103.0,
        "low": 98.0,
        "change_1m": 0.6,
        "change_5m": 0.8,
        "source_id": "provider:ticker",
        "source_timestamp": now,
        "receipt_id": "provider-ticker-receipt",
        "data_status": "live",
        "truth_status": "live",
        "generated_values": False,
    }


def _bars(now: float, count: int = 12) -> list[dict]:
    rows = []
    for index in range(count):
        observed_at = now - (count - index - 1) * 60
        opened = 100.0 + index
        closed = opened + 0.5
        rows.append(
            {
                "open": opened,
                "high": closed + 1.0,
                "low": opened - 1.0,
                "close": closed,
                "volume": 10.0 + index,
                "source_id": "provider:bars",
                "source_timestamp": observed_at,
                "receipt_id": f"bar-receipt-{index}",
                "data_status": "live",
                "truth_status": "live",
                "generated_values": False,
            }
        )
    return rows


def _assert_numeric_free_no_data(result: dict) -> None:
    assert result["status"] == "no_data"
    assert result["data_status"] == "no_data"
    assert result["truth_status"] == "no_data"
    assert result["eligible_for_action"] is False
    assert result["eligible_for_accounting"] is False
    assert result["eligible_for_learning"] is False
    assert all(
        not isinstance(value, (int, float)) or isinstance(value, bool)
        for value in result.values()
    )


def test_fresh_complete_ticker_is_the_only_path_to_wave_action() -> None:
    now = time.time()
    scanner = _scanner()
    analysis = asyncio.run(
        scanner._analyze_wave(
            "BTCUSD",
            "kraken",
            {"BTCUSD": _ticker(now)},
        )
    )

    assert analysis is not None
    assert analysis.source_id == "provider:ticker"
    assert analysis.source_timestamp == now
    assert analysis.receipt_id == "provider-ticker-receipt"
    assert analysis.generated_values is False
    assert analysis.eligible_for_action is True
    assert analysis.eligible_for_learning is True
    assert analysis.eligible_for_accounting is False

    for mutation in (
        {"source_timestamp": now - wave.MAX_TICKER_AGE_SECONDS - 1},
        {"generated_values": True},
        {"receipt_id": None},
        {"volume": math.nan},
        {"low": 102.0},
    ):
        denied_ticker = _ticker(now)
        denied_ticker.update(mutation)
        denied = asyncio.run(
            scanner._analyze_wave(
                "ETHUSD",
                "kraken",
                {"ETHUSD": denied_ticker},
            )
        )
        assert denied is None
        _assert_numeric_free_no_data(scanner.last_no_data["ETHUSD"])


def test_provider_bars_require_finite_ohlcv_strict_order_and_freshness() -> None:
    now = time.time()
    bars = _bars(now)
    assert len(wave._normalise_provider_bars(bars, received_at=now)) == len(bars)

    reversed_bars = list(reversed(bars))
    assert wave._normalise_provider_bars(reversed_bars, received_at=now) == []

    malformed = _bars(now)
    malformed[-1]["high"] = malformed[-1]["close"] - 1
    assert wave._normalise_provider_bars(malformed, received_at=now) == []

    generated = _bars(now)
    generated[-1]["generated_values"] = True
    assert wave._normalise_provider_bars(generated, received_at=now) == []

    stale = _bars(now - wave.MAX_LATEST_CANDLE_AGE_SECONDS - 1)
    assert wave._normalise_provider_bars(stale, received_at=now) == []

    class OfflineBinance:
        def get_24h_ticker(self, _symbol):
            receipt = _ticker(now)
            receipt.pop("source_id")
            receipt.pop("source_timestamp")
            receipt.pop("receipt_id")
            receipt.pop("generated_values")
            receipt["closeTime"] = int(now * 1000)
            return receipt

        def get_klines(self, **_kwargs):
            return [
                {
                    "timestamp": row["source_timestamp"],
                    "open": row["open"],
                    "high": row["high"],
                    "low": row["low"],
                    "close": row["close"],
                    "volume": row["volume"],
                }
                for row in bars
            ]

    scanner = _scanner()
    scanner.binance = OfflineBinance()
    ticker = asyncio.run(scanner._fetch_ticker("BTCUSD", "binance"))
    assert wave._normalise_ticker_receipt(ticker) is not None
    fetched_bars = asyncio.run(scanner._fetch_candles("BTCUSD", "binance"))
    assert len(fetched_bars) == len(bars)
    assert all(row["receipt_id"] for row in fetched_bars)
    assert all(row["generated_values"] is False for row in fetched_bars)


def test_deep_dive_returns_numeric_free_no_data_for_unproven_bars() -> None:
    scanner = _scanner()

    async def invalid_fetch(*_args, **_kwargs):
        rows = _bars(time.time())
        rows[-1].pop("receipt_id")
        return rows

    scanner._fetch_candles = invalid_fetch
    result = asyncio.run(scanner.deep_dive_candles("BTCUSD", "kraken"))
    _assert_numeric_free_no_data(result)


def test_exact_hardened_validator_is_clean() -> None:
    root = Path(__file__).resolve().parents[1]
    target = root / "aureon" / "scanners" / "aureon_global_wave_scanner.py"
    assert scan_text_file(target, root) == []
