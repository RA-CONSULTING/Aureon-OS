"""Orca observations are an authenticated read. Balance maps are not summed."""

from aureon.exchanges.orca_reader_observations import build_orca_reader_observations


class _Kraken:
    def get_account_balance(self):
        return {"XXBT": 0.5, "ZUSD": 10.0}


class _KrakenUsd:
    def get_account_balance(self):
        return {"XXBT": 0.5, "ZUSD": 10.0, "equity_usd": 42.0}


def test_kraken_balances_of_mixed_units_are_not_summed():
    payload = build_orca_reader_observations(None, _Kraken(), {})
    assert payload["kraken"]["balances"]["XXBT"] == 0.5
    assert payload["kraken"]["equity"] is None
    assert payload["kraken"]["live"] is False
    assert payload["orders"] == 0


def test_kraken_usd_total_is_the_equity():
    payload = build_orca_reader_observations(None, _KrakenUsd(), {})
    assert payload["kraken"]["equity"] == 42.0


class _AlpacaMixed:
    def get_account_balance(self):
        return {"USD": 10.0, "AAPL": 3.0}

    def get_account(self):
        return {"equity": "25.5", "cash": "10.0"}


class _AlpacaWithoutEquity:
    def get_account_balance(self):
        return {"USD": 10.0, "AAPL": 3.0}

    def get_account(self):
        return {}


def test_alpaca_equity_is_account_equity_not_a_sum_of_balances():
    payload = build_orca_reader_observations(_AlpacaMixed(), None, {})
    assert payload["alpaca"]["balances"]["USD"] == 10.0
    assert payload["alpaca"]["balances"]["AAPL"] == 3.0
    assert payload["alpaca"]["equity"] == 25.5
    assert payload["orders"] == 0


def test_alpaca_without_account_equity_is_none():
    payload = build_orca_reader_observations(_AlpacaWithoutEquity(), None, {})
    assert payload["alpaca"]["equity"] is None
    assert payload["alpaca"]["live"] is False
