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


def test_duplicate_case_keys_are_not_collapsed():
    amount, reason = gbp_equity_from_balances({"GBP": 100, "gbp": 50})
    assert amount is None
    assert amount != 50.0
    assert reason


def test_a_real_zero_stays_zero():
    amount, reason = gbp_equity_from_balances({"GBP": 0.0})
    assert amount == 0.0
    assert reason == ""


def test_a_negative_amount_is_null():
    amount, reason = gbp_equity_from_balances({"GBP": -1.0})
    assert amount is None
    assert "negative" in reason


def test_non_finite_and_non_numeric_values_are_not_amounts():
    for raw in (
        {"GBP": float("nan")},
        {"GBP": float("inf")},
        {"GBP": float("-inf")},
        {"GBP": True},
        {"GBP": False},
        {"GBP": "55.5"},
    ):
        amount, reason = gbp_equity_from_balances(raw)
        assert amount is None
        assert "not a number" in reason
