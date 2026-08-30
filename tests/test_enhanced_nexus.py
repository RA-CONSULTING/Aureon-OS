"""Hermetic contracts for the current enhanced probability nexus."""

from __future__ import annotations

import pytest

from aureon.bridges.aureon_probability_nexus import EnhancedProbabilityNexus, ProfitFilter


def test_profit_filter_only_accepts_a_real_fee_clearing_future_exit() -> None:
    profit_filter = ProfitFilter(fee_rate=0.001, max_hold=4)
    candles = [{"close": 100.0}, {"close": 100.1}, {"close": 100.5}]

    profitable, hold, expected_profit = profit_filter.check_profitability(candles, 0, "LONG")

    assert profitable is True
    assert hold == 2
    assert expected_profit == pytest.approx(0.003)
    assert profit_filter.is_exit_profitable(100.0, 100.1, "LONG") is False


def test_prediction_without_future_candles_never_invents_profit() -> None:
    nexus = EnhancedProbabilityNexus(exchange="binance")
    candles = [{"close": 100.0 + index} for index in range(24)]

    prediction, profitable, hold, expected_profit = nexus.predict_with_profit_filter(
        "BTC/USD", candles, len(candles) - 1
    )

    assert prediction.factors["candles_observed"] == 24
    assert profitable is False
    assert hold == 0
    assert expected_profit == 0.0


def test_trade_accounting_deducts_round_trip_fees_before_compounding() -> None:
    nexus = EnhancedProbabilityNexus(
        exchange="binance", leverage=1.0, starting_balance=1_000.0
    )

    trade = nexus.execute_trade(
        pair="BTC/USD",
        direction="LONG",
        entry_price=100.0,
        exit_price=101.0,
        confidence=0.4,
    )

    assert trade["position_size"] == 100.0
    assert trade["gross_pnl"] == pytest.approx(1.0)
    assert trade["fees"] == pytest.approx(0.2)
    assert trade["net_pnl"] == pytest.approx(0.8)
    assert trade["balance_after"] == pytest.approx(1_000.8)
    assert nexus.get_win_rate() == 100.0
