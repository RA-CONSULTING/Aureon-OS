import asyncio
import json
from unittest.mock import patch

import aureon.data_feeds.ws_market_data_feeder as feeder_mod
from aureon.data_feeds.ws_market_data_feeder import (
    CAPITAL_DEFAULT_SYMBOLS,
    MarketSnapshotStore,
    _acquire_single_writer_lock,
    _build_generic_ticker_cache,
    _cached_last_good_snapshot,
    _extract_kraken_prices_and_tickers,
    _extract_prices_and_tickers,
    _merge_market_snapshots,
    _release_single_writer_lock,
    _snapshots_from_merged_cache,
    _ticker_cache_to_waveform_bars,
)


def test_extract_prices_accepts_binance_websocket_payload():
    prices, ticker_cache = _extract_prices_and_tickers(
        [{"s": "BTCUSDT", "c": "50000.0", "P": "1.5", "v": "12.0"}],
        binance_uk_mode=False,
    )

    assert prices["BTC"] == 50000.0
    assert ticker_cache["BTCUSDT"]["change24h"] == 1.5
    assert ticker_cache["binance:BTCUSDT"]["volume"] == 12.0


def test_extract_prices_accepts_binance_rest_24hr_payload():
    prices, ticker_cache = _extract_prices_and_tickers(
        [
            {
                "symbol": "ETHUSDT",
                "lastPrice": "3200.0",
                "priceChangePercent": "2.25",
                "quoteVolume": "987654321.0",
            }
        ],
        binance_uk_mode=False,
    )

    assert prices["ETH"] == 3200.0
    assert ticker_cache["ETHUSDT"]["change24h"] == 2.25
    assert ticker_cache["ETHUSDT"]["volume"] == 987654321.0


def test_extract_kraken_prices_accepts_public_ticker_payload():
    prices, ticker_cache = _extract_kraken_prices_and_tickers(
        {
            "XXBTZUSD": {
                "a": ["50100.0"],
                "b": ["50000.0"],
                "c": ["50050.0"],
                "o": "49000.0",
                "v": ["1.0", "2.0"],
            }
        }
    )

    assert prices["BTC"] == 50050.0
    assert ticker_cache["BTCUSD"]["exchange"] == "kraken"
    assert ticker_cache["kraken:BTCUSD"]["quote"] == "USD"
    assert ticker_cache["BTCUSD"]["change24h"] > 2.0


def test_generic_authenticated_snapshots_build_equity_cache():
    prices, ticker_cache = _build_generic_ticker_cache(
        [{"symbol": "AAPL", "price": 215.5, "bid": 215.4, "ask": 215.6, "change_pct": 0.8, "volume": 12345}],
        exchange="alpaca",
        source="alpaca_rest_snapshot",
    )

    assert prices["AAPL"] == 215.5
    assert ticker_cache["AAPLUSD"]["exchange"] == "alpaca"
    assert ticker_cache["alpaca:AAPLUSD"]["change24h"] == 0.8


def test_capital_default_watchlist_prioritizes_gold_target_lane():
    assert CAPITAL_DEFAULT_SYMBOLS[:4] == ["GOLD", "GCM2026", "GLD", "GDX"]


def test_merge_market_snapshots_preserves_source_health_and_tickers():
    merged = _merge_market_snapshots(
        {
            "binance": {
                "generated_at": 100.0,
                "source": "binance_ws",
                "prices": {"BTC": 50000.0},
                "ticker_cache": {"BTCUSDT": {"price": 50000.0, "base": "BTC", "exchange": "binance"}},
                "source_health": {"binance": {"source": "binance_ws", "active": True, "generated_at": 100.0}},
            },
            "kraken": {
                "generated_at": 101.0,
                "source": "kraken_public_rest",
                "prices": {"ETH": 3000.0},
                "ticker_cache": {"ETHUSD": {"price": 3000.0, "base": "ETH", "exchange": "kraken"}},
                "source_health": {"kraken": {"source": "kraken_public_rest", "active": True, "generated_at": 101.0}},
            },
        }
    )

    assert merged["source"] == "multi_exchange_stream_cache"
    assert merged["prices"]["BTC"] == 50000.0
    assert merged["prices"]["ETH"] == 3000.0
    assert set(merged["source_health"]) == {"binance", "kraken"}
    assert "ETHUSD" in merged["ticker_cache"]


def test_live_cache_tickers_convert_to_global_waveform_bars():
    bars = _ticker_cache_to_waveform_bars(
        {
            "generated_at": 100.0,
            "source": "multi_exchange_stream_cache",
            "ticker_cache": {
                "binance:BTCUSDT": {
                    "price": 50000.0,
                    "bid": 49990.0,
                    "ask": 50010.0,
                    "volume": 1000000.0,
                    "base": "BTC",
                    "quote": "USDT",
                    "exchange": "binance",
                    "pair": "BTCUSDT",
                },
                "kraken:ETHUSD": {
                    "price": 3000.0,
                    "volume": 2000000.0,
                    "base": "ETH",
                    "quote": "USD",
                    "exchange": "kraken",
                    "pair": "ETHUSD",
                },
            },
        },
        now_ms=1_800_000_123_456,
        bucket_ms=60_000,
        max_symbols=2,
    )

    assert len(bars) == 2
    assert bars[0]["provider"] == "aureon_live_stream_cache"
    assert bars[0]["period_id"] == "LIVE_60S"
    assert bars[0]["symbol"] in {"BTCUSD", "ETHUSD"}
    assert any(bar["venue"] == "KRAKEN" for bar in bars)


def test_single_writer_lock_replaces_stale_lock(tmp_path):
    lock_path = tmp_path / "state" / "feeder.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text('{"pid": 999999999, "out_path": "old"}', encoding="utf-8")

    acquired = _acquire_single_writer_lock(lock_path, out_path=tmp_path / "ws_cache" / "ws_prices.json")

    assert acquired == lock_path
    assert "999999999" not in lock_path.read_text(encoding="utf-8")
    _release_single_writer_lock(acquired)
    assert not lock_path.exists()


def test_windows_pid_check_uses_tasklist_before_openprocess():
    with patch.object(feeder_mod.sys, "platform", "win32"), patch.object(feeder_mod.subprocess, "run") as run:
        run.return_value.stdout = "INFO: No tasks are running which match the specified criteria."

        assert feeder_mod._pid_is_running(14524) is False

    run.assert_called_once()


def test_cached_last_good_snapshot_preserves_mapping_during_provider_backoff():
    cached = _cached_last_good_snapshot(
        "capital",
        {
            "generated_at": 100.0,
            "source": "capital_rest_snapshot",
            "ticker_cache": {"capital:AAPLUSD": {"exchange": "capital", "price": 100.0}},
            "source_health": {"capital": {"active": True, "fresh": True, "ticker_count": 1, "generated_at": 100.0}},
        },
        "rate_limited",
    )

    assert cached["ticker_cache"]
    assert cached["source_health"]["capital"]["active"] is True
    assert cached["source_health"]["capital"]["fresh"] is True
    assert cached["source_health"]["capital"]["reason"] == "cached_last_good_due_to:rate_limited"
    assert cached["source_health"]["capital"]["data_age_sec"] >= 0


def test_market_snapshot_store_hydrates_existing_merged_cache_before_fast_source_write(tmp_path):
    out_path = tmp_path / "ws_cache" / "ws_prices.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            _merge_market_snapshots(
                {
                    "binance": {
                        "generated_at": 100.0,
                        "source": "binance_rest",
                        "prices": {"BTC": 100.0},
                        "ticker_cache": {"binance:BTCUSDT": {"exchange": "binance", "base": "BTC", "price": 100.0}},
                        "source_health": {"binance": {"active": True, "fresh": True, "ticker_count": 1, "generated_at": 100.0}},
                    },
                    "kraken": {
                        "generated_at": 101.0,
                        "source": "kraken_rest",
                        "prices": {"ETH": 10.0},
                        "ticker_cache": {"kraken:ETHUSD": {"exchange": "kraken", "base": "ETH", "price": 10.0}},
                        "source_health": {"kraken": {"active": True, "fresh": True, "ticker_count": 1, "generated_at": 101.0}},
                    },
                }
            )
        ),
        encoding="utf-8",
    )
    store = MarketSnapshotStore(out_path)

    merged = asyncio.run(
        store.update(
            "binance",
            {
                "generated_at": 102.0,
                "source": "binance_rest",
                "prices": {"BTC": 101.0},
                "ticker_cache": {"binance:BTCUSDT": {"exchange": "binance", "base": "BTC", "price": 101.0}},
                "source_health": {"binance": {"active": True, "fresh": True, "ticker_count": 1, "generated_at": 102.0}},
            },
        )
    )

    assert set(merged["source_health"]) == {"binance", "kraken"}
    assert "kraken:ETHUSD" in merged["ticker_cache"]
    assert _snapshots_from_merged_cache(merged)["kraken"]["ticker_cache"]


def test_binance_rest_writer_preserves_existing_slower_source_snapshots(tmp_path, monkeypatch):
    out_path = tmp_path / "ws_cache" / "ws_prices.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            _merge_market_snapshots(
                {
                    "binance": {
                        "generated_at": 100.0,
                        "source": "binance_rest",
                        "prices": {"BTC": 100.0},
                        "ticker_cache": {"binance:BTCUSDT": {"exchange": "binance", "base": "BTC", "price": 100.0}},
                        "source_health": {"binance": {"active": True, "fresh": True, "ticker_count": 1, "generated_at": 100.0}},
                    },
                    "capital": {
                        "generated_at": 101.0,
                        "source": "capital_rest",
                        "prices": {"AAPL": 10.0},
                        "ticker_cache": {"capital:AAPLUSD": {"exchange": "capital", "base": "AAPL", "price": 10.0}},
                        "source_health": {"capital": {"active": True, "fresh": True, "ticker_count": 1, "generated_at": 101.0}},
                    },
                }
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        feeder_mod,
        "_fetch_binance_all_tickers_rest",
        lambda: [{"symbol": "BTCUSDT", "lastPrice": "101.0", "priceChangePercent": "1", "quoteVolume": "1000"}],
    )
    store = MarketSnapshotStore(out_path)

    asyncio.run(
        feeder_mod._write_binance_rest_snapshot(
            out_path=out_path,
            binance_uk_mode=False,
            source="binance_rest_gap_fill",
            store=store,
        )
    )
    written = json.loads(out_path.read_text(encoding="utf-8"))

    assert set(written["source_health"]) == {"binance", "capital"}
    assert "capital:AAPLUSD" in written["ticker_cache"]
