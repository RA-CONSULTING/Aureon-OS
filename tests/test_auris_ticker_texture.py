"""Pins for the Auris market texture.

Volume and spread come from the ticker. Volatility and momentum are no
reading until a documented scale exists. A real 0.0 stays 0.0.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _trader():
    from aureon.exchanges.unified_market_trader import UnifiedMarketTrader

    return UnifiedMarketTrader.__new__(UnifiedMarketTrader)


def _metrics():
    return {
        "passed": True,
        "avg_confidence": 0.8,
        "avg_support_count": 4.0,
        "avg_change_pct": 1.1,
        "avg_abs_change_pct": 1.1,
        "model_alignment_rate": 1.0,
        "source_count": 4.0,
    }


def test_support_and_confidence_are_not_volume_or_spread():
    trader = _trader()
    texture = trader._hnc_market_texture(
        _metrics(),
        {},
        {"symbols": {"BTCUSD": {"confidence": 0.9, "support_count": 4, "change_pct": 8.0}}},
        {},
    )
    assert texture["volume"] is None
    assert texture["spread"] is None
    assert texture["volatility"] is None
    assert texture["momentum"] is None


def test_ticker_volume_and_spread_pass_through_including_zero():
    trader = _trader()
    texture = trader._hnc_market_texture(
        _metrics(),
        {},
        {"symbols": {"BTCUSD": {"volume_24h": 0.0, "bid": 10.0, "ask": 10.0}}},
        {},
    )
    assert texture["volume"] == 0.0
    assert texture["spread"] == 0.0
    assert texture["volatility"] is None
    assert texture["momentum"] is None


def test_quote_volume_and_explicit_spread_are_readings():
    trader = _trader()
    texture = trader._hnc_market_texture(
        _metrics(),
        {},
        {},
        {"active_order_flow": [{"quoteVolume": 1250000.0, "spread": 20.0}]},
    )
    assert texture["volume"] == 1250000.0
    assert texture["spread"] == 20.0


def test_the_old_scales_are_not_in_the_texture():
    source = (ROOT / "aureon/exchanges/unified_market_trader.py").read_text(encoding="utf-8")
    assert "avg_abs_change / 5.0" not in source
    assert "avg_change / 5.0" not in source
    assert "(avg_support + source_count) / 8.0" not in source
    assert "1.0 - avg_confidence" not in source
