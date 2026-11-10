"""Kraken and Capital balance reads: an empty or unreadable reading is not "no funds".

All responses are mocked. Nothing here talks to an exchange.
"""

from datetime import datetime, timezone
from email.utils import format_datetime
import importlib
import json
from types import SimpleNamespace

import pytest

from aureon.exchanges import capital_client as capital
from aureon.exchanges import kraken_client as kraken_mod
from aureon.exchanges import unified_market_trader as umt

kc = importlib.import_module("aureon_radar.bots.orca_unified_kill_chain")

NOW = 1_800_000_000.0


class _Resp:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200
        self.headers = {"Date": format_datetime(datetime.fromtimestamp(NOW - 1, timezone.utc), usegmt=True)}
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


def _capital_client():
    client = capital.CapitalClient.__new__(capital.CapitalClient)
    client.enabled = True
    client.dry_run = False
    client._accounts_cache = capital.ObservationList()
    client._accounts_cache_time = 0.0
    client.last_account_observation = capital.BalanceObservation(truth_status="no_data", reason="not_fetched")
    return client


# Shape of the live /accounts reply seen on 10 Nov 2026 (IDs and figures changed).
TWO_SPREADBET_ACCOUNTS = {
    "accounts": [
        {
            "accountId": "acct-pref",
            "status": "ENABLED",
            "accountType": "SPREADBET",
            "preferred": True,
            "currency": "GBP",
            "balance": {"balance": 105.07, "deposit": 117.08, "profitLoss": -12.01, "available": -7.54},
        },
        {
            "accountId": "acct-two",
            "accountName": "Second",
            "status": "ENABLED",
            "accountType": "SPREADBET",
            "preferred": False,
            "currency": "GBP",
            "balance": {"balance": 0.0, "deposit": 0.0, "profitLoss": 0.0, "available": 0.0},
        },
    ]
}


@pytest.fixture
def frozen(monkeypatch):
    monkeypatch.setattr(capital.time, "time", lambda: NOW)


def test_capital_negative_available_keeps_the_preferred_account(monkeypatch, frozen):
    client = _capital_client()
    monkeypatch.setattr(client, "_request", lambda *a, **k: _Resp(TWO_SPREADBET_ACCOUNTS))

    accounts = client.get_accounts(cache_ttl=0.0)
    balances = client.get_account_balance()

    assert accounts.truth_status == "real_observed"
    assert len(accounts) == 2
    pref = next(a for a in accounts if a["preferred"])
    assert pref["balance"] == 105.07
    assert pref["available"] == 0.0
    assert pref["available_reported"] == -7.54
    assert pref["margin_deficit"] == pytest.approx(7.54)
    assert pref["field_provenance"]["available"]["floored_at_zero"] is True
    assert dict(balances) == {"GBP": pytest.approx(105.07)}
    assert balances.truth_status == "real_derived"


def test_capital_missing_available_is_still_incomplete(monkeypatch, frozen):
    client = _capital_client()
    payload = {"accounts": [{"accountId": "a", "status": "ENABLED", "currency": "GBP", "balance": {"balance": 1.0}}]}
    monkeypatch.setattr(client, "_request", lambda *a, **k: _Resp(payload))

    accounts = client.get_accounts(cache_ttl=0.0)

    assert list(accounts) == []
    assert accounts.reason == "accounts_incomplete"


def _bare_umt():
    trader = umt.UnifiedMarketTrader.__new__(umt.UnifiedMarketTrader)
    trader.capital_ready = False
    trader.capital_error = ""
    trader._boot_balances = {}
    return trader


def test_umt_reads_capital_currency_from_the_observation_itself():
    trader = _bare_umt()
    observation = capital.BalanceObservation({"GBP": 105.07}, truth_status="real_derived", reason="ok")
    trader.capital = SimpleNamespace(client=SimpleNamespace(get_account_balance=lambda: observation))

    trader._probe_capital_balance()

    boot = trader._boot_balances["capital"]
    assert boot["error"] == ""
    assert boot["alive"] is True
    assert boot["equity"] == pytest.approx(105.07)
    assert trader.capital_error == ""
    assert trader.capital_ready is True


def test_kraken_dry_run_balance_is_marked_synthetic(monkeypatch):
    monkeypatch.setenv("KRAKEN_DRY_RUN", "true")
    client = kraken_mod.KrakenClient()

    assert client.get_account_balance() == {}
    assert client.last_balance_source == "dry_run_synthetic"
    assert kc.kraken_balance_not_live(client) == "BALANCE_DRY_RUN"


def test_kraken_failed_read_is_unreadable_not_zero(monkeypatch):
    monkeypatch.setenv("KRAKEN_DRY_RUN", "false")
    client = kraken_mod.KrakenClient()

    def boom(*a, **k):
        raise RuntimeError("Kraken error: ['EAPI:Invalid nonce']")

    monkeypatch.setattr(client, "account", boom)

    assert client.get_account_balance() == {}
    assert client.last_balance_source == "error"
    assert kc.kraken_balance_not_live(client) == "BALANCE_UNREADABLE"


def test_kraken_live_read_maps_zusd_and_xxbt(monkeypatch):
    monkeypatch.setenv("KRAKEN_DRY_RUN", "false")
    client = kraken_mod.KrakenClient()
    client._balance_cache = {}
    client._balance_cache_time = 0.0
    monkeypatch.setattr(client, "_private", lambda path, data=None, **k: {"ZUSD": "12.50", "XXBT": "0.01", "USDC": "0"})

    bal = client.get_account_balance()

    assert bal == {"USD": 12.5, "BTC": 0.01}
    assert client.last_balance_source == "live"
    assert kc.kraken_balance_not_live(client) == ""


def test_umt_kraken_posture_names_dry_run_instead_of_stale_cache(monkeypatch):
    trader = _bare_umt()
    dry = SimpleNamespace(dry_run=True, get_account_balance=lambda: {}, _balance_cache_time=0.0)
    monkeypatch.setattr(trader, "_kraken_spot_client", lambda: dry)
    monkeypatch.setattr(trader, "_governor", lambda: pytest.fail("no provider call in dry run"), raising=False)

    posture = trader._kraken_spot_portfolio_posture(force=True)

    assert posture["reason"] == "kraken_client_dry_run_no_live_balance"
    assert posture["status"] == "no_data"
