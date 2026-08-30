from datetime import datetime, timezone
from email.utils import format_datetime
import json

import pytest

from aureon.exchanges import capital_client as capital


NOW = 1_800_000_000.0


def _iso(offset: float = 0.0) -> str:
    return datetime.fromtimestamp(NOW + offset, timezone.utc).isoformat()


def _http_date(offset: float = 0.0) -> str:
    return format_datetime(datetime.fromtimestamp(NOW + offset, timezone.utc), usegmt=True)


class RecordedResponse:
    def __init__(self, payload, *, status_code=200, date_header=True):
        self._payload = payload
        self.status_code = status_code
        self.headers = {"Date": _http_date(-1)} if date_header else {}
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


def _offline_client() -> capital.CapitalClient:
    client = capital.CapitalClient.__new__(capital.CapitalClient)
    client.enabled = True
    client.dry_run = False
    client._accounts_cache = capital.ObservationList()
    client._accounts_cache_time = 0.0
    client._snapshot_cache = {}
    client._snapshot_cache_times = {}
    client._ticker_mem_cache = {}
    client._ticker_mem_cache_times = {}
    client.market_cache = []
    client.market_index = {}
    client.market_cache_time = 0.0
    client._rate_limit_until = 0.0
    client._pending_close_confirmations = {}
    client.last_account_observation = capital.BalanceObservation(
        truth_status="no_data",
        reason="not_fetched",
        received_at=NOW,
    )
    client.last_ticker_observation = capital.CapitalClient._no_data_ticker(
        "",
        "not_fetched",
        received_at=NOW,
    )
    return client


@pytest.fixture(autouse=True)
def _fixed_clock(monkeypatch):
    monkeypatch.setattr(capital.time, "time", lambda: NOW)


def _confirmation_payload():
    return {
        "date": _iso(-2),
        "status": "OPEN",
        "dealStatus": "ACCEPTED",
        "epic": "AAPL",
        "dealReference": "o-provider-1",
        "dealId": "provider-deal-parent",
        "affectedDeals": [{"dealId": "provider-deal-1", "status": "OPENED"}],
        "level": 101.0,
        "size": 2.0,
        "direction": "BUY",
    }


def _fee_receipt():
    return {
        "amount": 0.75,
        "currency": "GBP",
        "source_id": "capital_transaction:fee-1",
        "source_timestamp": _iso(-1),
        "truth_status": "real_observed",
        "generated_values": False,
    }


def test_ticker_requires_complete_fresh_provider_snapshot(monkeypatch):
    client = _offline_client()
    monkeypatch.setattr(
        client,
        "_get_cached_monitor_quote",
        lambda symbol: client._no_data_ticker(symbol, "cache_unavailable", received_at=NOW),
    )
    monkeypatch.setattr(client, "_resolve_market", lambda symbol: {"epic": "AAPL"})
    monkeypatch.setattr(
        client,
        "_get_market_snapshot",
        lambda epic: {
            "snapshot": {
                "bid": 100.0,
                "offer": 102.0,
                "percentageChange": 1.25,
                "high": 103.0,
                "low": 99.0,
                "marketStatus": "TRADEABLE",
                "updateTimeUTC": _iso(-1),
            }
        },
    )

    ticker = client.get_ticker("AAPL")

    assert ticker["price"] == 101.0
    assert ticker["truth_status"] == "real_derived"
    assert ticker["action_eligible"] is True
    assert ticker["source_timestamp"] == NOW - 1
    assert ticker["received_at"] == NOW
    assert ticker["source_timestamp"] != ticker["received_at"]
    assert ticker["generated_values"] is False


@pytest.mark.parametrize(
    "snapshot,reason",
    [
        (
            {
                "bid": 100.0,
                "percentageChange": 1.0,
                "marketStatus": "TRADEABLE",
                "updateTimeUTC": _iso(-1),
            },
            "market_snapshot_incomplete_or_stale",
        ),
        (
            {
                "bid": 100.0,
                "offer": 101.0,
                "percentageChange": 1.0,
                "marketStatus": "TRADEABLE",
                "updateTimeUTC": _iso(-(capital.CAPITAL_QUOTE_MAX_AGE_S + 1)),
            },
            "market_snapshot_incomplete_or_stale",
        ),
    ],
)
def test_ticker_missing_or_stale_fields_are_explicit_no_data(monkeypatch, snapshot, reason):
    client = _offline_client()
    monkeypatch.setattr(
        client,
        "_get_cached_monitor_quote",
        lambda symbol: client._no_data_ticker(symbol, "cache_unavailable", received_at=NOW),
    )
    monkeypatch.setattr(client, "_resolve_market", lambda symbol: {"epic": "AAPL"})
    monkeypatch.setattr(client, "_get_market_snapshot", lambda epic: {"snapshot": snapshot})

    ticker = client.get_ticker("AAPL")

    assert ticker["truth_status"] == "no_data"
    assert ticker["reason"] == reason
    assert ticker["price"] is None
    assert ticker["bid"] is None
    assert ticker["ask"] is None
    assert ticker["action_eligible"] is False


def test_monitor_cache_without_per_quote_provider_time_is_rejected(monkeypatch, tmp_path):
    cache_path = tmp_path / "capital_monitor.json"
    cache_path.write_text(
        json.dumps(
            {
                "generated_at": NOW,
                "prices": {
                    "AAPL": {
                        "source": "yahoo",
                        "price": 101.0,
                        "bid": 100.0,
                        "ask": 102.0,
                        "change_pct": 1.0,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(capital, "CAPITAL_MONITOR_CACHE_PATH", str(cache_path))
    client = _offline_client()

    ticker = client._get_cached_monitor_quote("AAPL")

    assert ticker["truth_status"] == "no_data"
    assert ticker["reason"] == "monitor_quote_incomplete_or_unproven"
    assert ticker["action_eligible"] is False


def test_accounts_use_provider_currency_and_http_date(monkeypatch):
    client = _offline_client()
    response = RecordedResponse(
        {
            "accounts": [
                {
                    "accountId": "account-1",
                    "accountName": "EUR",
                    "status": "ENABLED",
                    "accountType": "CFD",
                    "preferred": True,
                    "balance": {"balance": 125.5, "available": 100.25},
                    "currency": "EUR",
                }
            ]
        }
    )
    monkeypatch.setattr(client, "_request", lambda *args, **kwargs: response)
    monkeypatch.setenv("CAPITAL_ACCOUNT_CURRENCY", "GBP")

    accounts = client.get_accounts(cache_ttl=0.0)
    balances = client.get_account_balance()

    assert accounts.truth_status == "real_observed"
    assert accounts[0]["currency"] == "EUR"
    assert accounts[0]["source_timestamp"] == NOW - 1
    assert accounts[0]["received_at"] == NOW
    assert dict(balances) == {"EUR": 125.5}
    assert balances.truth_status == "real_derived"
    assert "GBP" not in balances


@pytest.mark.parametrize(
    "payload,date_header",
    [
        (
            {
                "accounts": [
                    {
                        "accountId": "account-1",
                        "status": "ENABLED",
                        "balance": {"balance": 125.5},
                        "currency": "EUR",
                    }
                ]
            },
            True,
        ),
        (
            {
                "accounts": [
                    {
                        "accountId": "account-1",
                        "status": "ENABLED",
                        "balance": {"balance": 125.5, "available": 100.25},
                        "currency": "EUR",
                    }
                ]
            },
            False,
        ),
    ],
)
def test_incomplete_account_receipts_are_no_data(monkeypatch, payload, date_header):
    client = _offline_client()
    monkeypatch.setattr(
        client,
        "_request",
        lambda *args, **kwargs: RecordedResponse(payload, date_header=date_header),
    )

    accounts = client.get_accounts(cache_ttl=0.0)

    assert list(accounts) == []
    assert accounts.truth_status == "no_data"
    assert accounts.reason in {"accounts_incomplete", "account_receipt_missing_provider_time"}


def test_market_order_http_success_is_only_submission_acknowledgement(monkeypatch):
    client = _offline_client()
    captured = {}
    monkeypatch.setattr(client, "_resolve_market", lambda symbol: {"epic": "AAPL"})

    def _request(method, path, *, json_body=None, **kwargs):
        captured.update(json_body or {})
        return RecordedResponse({"dealReference": "o-provider-1"})

    monkeypatch.setattr(client, "_request", _request)

    receipt = client.place_market_order("AAPL", "BUY", 2.0)

    assert receipt["status"] == "submitted"
    assert receipt["submission_acknowledged"] is True
    assert receipt["terminal_fill"] is False
    assert receipt["terminal_fill_receipt_complete"] is False
    assert receipt["eligible_for_state"] is False
    assert receipt["eligible_for_pnl"] is False
    assert receipt["eligible_for_learning"] is False
    assert receipt["source_timestamp"] == NOW - 1
    assert receipt["received_at"] == NOW
    assert "currencyCode" not in captured


def test_dry_run_never_emits_a_fill(monkeypatch):
    client = _offline_client()
    client.dry_run = True
    monkeypatch.setattr(client, "_request", lambda *args, **kwargs: pytest.fail("request must not run"))

    receipt = client.place_market_order("AAPL", "BUY", 2.0)

    assert receipt["status"] == "not_submitted"
    assert receipt["terminal_fill"] is False
    assert receipt["eligible_for_state"] is False
    assert "id" not in receipt


def test_pending_close_blocks_reverse_market_order_fallback(monkeypatch):
    client = _offline_client()
    calls = []

    def _request(method, path, **kwargs):
        calls.append((method, path))
        return RecordedResponse({"dealReference": "close-provider-1"})

    monkeypatch.setattr(client, "_request", _request)

    close_receipt = client.close_position("provider-deal-1")
    blocked = client.place_market_order("AAPL", "SELL", 2.0)

    assert close_receipt["status"] == "submitted"
    assert close_receipt["terminal_fill"] is False
    assert blocked["status"] == "rejected"
    assert blocked["reason"] == "close_confirmation_pending"
    assert blocked["rejected"] is True
    assert blocked["decision_status"] == "denied"
    assert calls == [("DELETE", "/positions/provider-deal-1")]


def test_complete_close_confirmation_releases_pending_close_guard(monkeypatch):
    client = _offline_client()
    client._pending_close_confirmations["close-provider-1"] = {
        "requested_deal_id": "provider-deal-1",
        "received_at": NOW,
        "source_timestamp": NOW - 1,
    }
    payload = _confirmation_payload()
    payload.update({
        "dealReference": "close-provider-1",
        "status": "CLOSED",
        "direction": "SELL",
        "affectedDeals": [{"dealId": "provider-deal-1", "status": "CLOSED"}],
    })
    monkeypatch.setattr(client, "_request", lambda *args, **kwargs: RecordedResponse(payload))

    receipt = client.confirm_order("close-provider-1", fee_receipt=_fee_receipt())

    assert receipt["terminal_fill_receipt_complete"] is True
    assert receipt["eligible_for_state"] is True
    assert client._pending_close_confirmations == {}


def test_confirmation_requires_affected_deal_and_provider_fee_receipt():
    client = _offline_client()

    unsettled = client.normalize_order_confirmation(_confirmation_payload(), received_at=NOW)
    complete = client.normalize_order_confirmation(
        _confirmation_payload(),
        received_at=NOW,
        fee_receipt=_fee_receipt(),
    )

    assert unsettled["status"] == "filled_unsettled"
    assert unsettled["terminal_fill"] is True
    assert unsettled["terminal_fill_receipt_complete"] is False
    assert unsettled["eligible_for_pnl"] is False
    assert complete["status"] == "filled"
    assert complete["provider_order_id"] == "o-provider-1"
    assert complete["provider_deal_id"] == "provider-deal-1"
    assert complete["filled_qty"] == 2.0
    assert complete["filled_avg_price"] == 101.0
    assert complete["fee_amount"] == 0.75
    assert complete["fee_currency"] == "GBP"
    assert complete["terminal_fill_receipt_complete"] is True
    assert complete["eligible_for_state"] is True
    assert complete["eligible_for_pnl"] is True
    assert complete["eligible_for_learning"] is True


def test_accepted_without_affected_deal_remains_pending():
    client = _offline_client()
    payload = _confirmation_payload()
    payload["affectedDeals"] = []

    receipt = client.normalize_order_confirmation(payload, received_at=NOW, fee_receipt=_fee_receipt())

    assert receipt["status"] == "pending"
    assert receipt["terminal_fill"] is False
    assert receipt["terminal_fill_receipt_complete"] is False
    assert receipt["eligible_for_state"] is False


def test_fee_and_cost_basis_require_complete_provider_receipts(monkeypatch):
    client = _offline_client()
    position = {
        "position": {"size": 2.0, "level": 101.0},
        "market": {"epic": "AAPL"},
        "source_timestamp": NOW - 2,
    }

    incomplete_fees = client.compute_trade_fees(position)
    position["provider_fee_receipt"] = _fee_receipt()
    complete_fees = client.compute_trade_fees(position)
    complete_fill = client.normalize_order_confirmation(
        _confirmation_payload(),
        received_at=NOW,
        fee_receipt=_fee_receipt(),
    )
    monkeypatch.setattr(client, "get_order_history", lambda: [complete_fill])
    basis = client.calculate_cost_basis("AAPL")

    assert incomplete_fees["truth_status"] == "incomplete"
    assert incomplete_fees["total_fees"] is None
    assert complete_fees["truth_status"] == "real_derived"
    assert complete_fees["total_fees"] == 0.75
    assert complete_fees["fee_currency"] == "GBP"
    assert basis["truth_status"] == "real_derived"
    assert basis["total_quantity"] == 2.0
    assert basis["total_cost"] == 202.0
    assert basis["avg_cost"] == 101.0
    assert basis["total_fees_by_currency"] == {"GBP": 0.75}


def test_activity_acceptance_is_not_cost_basis(monkeypatch):
    client = _offline_client()
    activity = {
        "epic": "AAPL",
        "dealId": "provider-deal-1",
        "status": "ACCEPTED",
        "type": "POSITION",
        "truth_status": "real_observed",
        "generated_values": False,
        "terminal_fill": False,
        "terminal_fill_receipt_complete": False,
    }
    monkeypatch.setattr(client, "get_order_history", lambda: [activity])

    basis = client.calculate_cost_basis("AAPL")

    assert basis["truth_status"] == "incomplete"
    assert basis["total_quantity"] is None
    assert basis["total_cost"] is None
    assert basis["trades"] is None
