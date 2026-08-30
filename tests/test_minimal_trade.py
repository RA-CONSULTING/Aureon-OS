"""A minimal trade calculation must remain offline and fee complete."""

from __future__ import annotations

import pytest

from aureon.trading.aureon_unified_ecosystem import required_price_increase


def test_minimal_trade_target_covers_both_fee_legs_exactly() -> None:
    trade_size = 10.0
    fee_rate = 0.0026
    target_profit = 0.01

    required_move = required_price_increase(trade_size, fee_rate, target_profit)
    realised_net = trade_size * ((1.0 - fee_rate) ** 2 * (1.0 + required_move) - 1.0)

    assert required_move > (2.0 * fee_rate)
    assert realised_net == pytest.approx(target_profit, abs=1e-12)


@pytest.mark.parametrize(
    ("trade_size", "fee_rate", "target_profit"),
    [(0.0, 0.0026, 0.01), (-1.0, 0.0026, 0.01), (10.0, -0.1, 0.01), (10.0, 0.0026, 0.0)],
)
def test_invalid_minimal_trade_inputs_fail_closed(
    trade_size: float, fee_rate: float, target_profit: float
) -> None:
    assert required_price_increase(trade_size, fee_rate, target_profit) == 0.0
