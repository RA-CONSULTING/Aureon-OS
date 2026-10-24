"""Orca observations are an authenticated read, and Kraken units are not summed."""

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
