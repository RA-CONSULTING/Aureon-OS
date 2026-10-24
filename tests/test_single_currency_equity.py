"""capital_equity_gbp is one sterling amount, or null."""

from aureon.exchanges.single_currency_equity import gbp_equity_from_balances


def test_gbp_only_balance_is_the_equity():
    amount, reason = gbp_equity_from_balances({"gbp": 12.5})
    assert amount == 12.5
    assert reason == ""


def test_mixed_currencies_are_not_summed():
    amount, reason = gbp_equity_from_balances({"GBP": 10.0, "USD": 5.0})
    assert amount is None
    assert "more than one currency" in reason


def test_non_gbp_currency_is_not_relabeled():
    amount, reason = gbp_equity_from_balances({"USD": 9.0})
    assert amount is None
    assert "USD" in reason
    assert "not GBP" in reason


def test_empty_balance_is_not_zero():
    amount, reason = gbp_equity_from_balances({})
    assert amount is None
    assert reason
