from __future__ import annotations

from dataclasses import dataclass

from aureon.trading.smart_harvest_system import SmartHarvestManager


@dataclass
class _Outcome:
    is_win: bool = True
    net_profit_usd: float = 10.0
    to_asset: str = "BTC"
    exchange: str = "kraken"


@dataclass
class _Portfolio:
    treasury_usd: float = 100.0


class _MustNotExecute:
    def __getattr__(self, name):
        raise AssertionError(f"unexpected execution surface access: {name}")


def test_harvest_without_terminal_conversion_receipt_is_numeric_free_no_data():
    manager = SmartHarvestManager(
        barter_navigator=_MustNotExecute(),
        exchange_client=_MustNotExecute(),
    )

    result = manager.process_profit(_Outcome(), _Portfolio())

    assert result is not None
    assert result.success is False
    assert result.status == "no_data"
    assert result.truth_status == "no_data"
    assert result.amount_harvested_usd is None
    assert result.stablecoin_received is None
    assert result.stablecoin_asset is None
    assert result.trade_id is None
    assert result.message == "fresh_terminal_profit_receipt_required"
    assert result.generated_values is False
    assert result.eligible_for_action is False
    assert result.eligible_for_accounting is False
    assert result.eligible_for_learning is False
    assert manager._active_harvests == {}


def test_receipted_profit_still_cannot_create_conversion_without_terminal_adapter():
    now = __import__("time").time()
    outcome = _Outcome()
    outcome.data_status = "live"
    outcome.truth_status = "real_derived"
    outcome.generated_values = False
    outcome.fill_receipt_complete = True
    outcome.eligible_for_accounting = True
    outcome.provider_order_id = "order-1"
    outcome.source_id = "kraken.query_orders"
    outcome.source_timestamp = now - 1.0
    outcome.received_at = now
    outcome.receipt_id = "receipt-1"
    manager = SmartHarvestManager(
        barter_navigator=_MustNotExecute(),
        exchange_client=_MustNotExecute(),
    )

    result = manager.process_profit(outcome, _Portfolio())

    assert result is not None
    assert result.status == "no_data"
    assert result.message == "conversion_adapter_with_terminal_provider_receipt_required"
    assert result.amount_harvested_usd is None
    assert result.stablecoin_received is None
    assert result.trade_id is None


def test_reinvestment_without_receipts_is_no_data_and_does_not_touch_portfolio():
    manager = SmartHarvestManager(
        barter_navigator=_MustNotExecute(),
        exchange_client=_MustNotExecute(),
    )
    portfolio = _Portfolio()

    result = manager.check_reinvestment_opportunities(portfolio)

    assert result.status == "no_data"
    assert result.amount_harvested_usd is None
    assert result.eligible_for_external_action is False
    assert portfolio.treasury_usd == 100.0
