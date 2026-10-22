from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.binance_trading_bot import (
    TradingConfig,
    build_websocket_stream_url,
    resolve_streams,
)


def test_resolve_streams_defaults():
    config = TradingConfig()
    assert resolve_streams(config) == ["btcusdt@kline_1m"]


def test_resolve_streams_override_interval():
    config = TradingConfig(symbol="ETHUSDT", ws_kline_interval="5m")
    assert resolve_streams(config) == ["ethusdt@kline_5m"]


def test_resolve_streams_custom_list():
    config = TradingConfig(ws_streams=["BTCUSDT@TRADE", "ethusdt@trade "])
    assert resolve_streams(config) == ["btcusdt@trade", "ethusdt@trade"]


def test_resolve_streams_invalid_override():
    config = TradingConfig(ws_streams=["   "])
    with pytest.raises(ValueError):
        resolve_streams(config)


def test_build_websocket_url_default():
    config = TradingConfig()
    assert (
        build_websocket_stream_url(config)
        == "wss://stream.binance.com:9443/ws/btcusdt@kline_1m"
    )


def test_build_websocket_url_combined_auto():
    config = TradingConfig(ws_streams=["btcusdt@trade", "ethusdt@trade"])
    assert (
        build_websocket_stream_url(config)
        == "wss://stream.binance.com:9443/stream?streams=btcusdt@trade/ethusdt@trade"
    )


def test_build_websocket_url_combined_explicit_timeunit():
    config = TradingConfig(
        ws_streams=["btcusdt@trade", "ethusdt@trade"],
        ws_use_combined=True,
        ws_time_unit="MICROSECOND",
    )
    assert (
        build_websocket_stream_url(config)
        == "wss://stream.binance.com:9443/stream?streams=btcusdt@trade/ethusdt@trade&timeUnit=MICROSECOND"
    )


def test_build_websocket_url_raw_with_timeunit():
    config = TradingConfig(ws_use_combined=False, ws_time_unit="microsecond")
    assert (
        build_websocket_stream_url(config)
        == "wss://stream.binance.com:9443/ws/btcusdt@kline_1m?timeUnit=microsecond"
    )


def test_build_websocket_url_without_suffix():
    config = TradingConfig(
        ws_url="wss://data-stream.binance.vision",
        ws_use_combined=False,
    )
    assert (
        build_websocket_stream_url(config)
        == "wss://data-stream.binance.vision/ws/btcusdt@kline_1m"
    )
