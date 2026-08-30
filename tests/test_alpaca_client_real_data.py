from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from aureon.exchanges.alpaca_client import AlpacaClient


def _iso_now(offset_seconds: float = 0.0) -> str:
    return (
        datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)
    ).isoformat()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ALPACA_API_KEY", "offline-test-key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "offline-test-secret")
    monkeypatch.setenv("ALPACA_DRY_RUN", "false")
    monkeypatch.setenv("ALPACA_QUOTE_MAX_AGE_SECONDS", "120")
    monkeypatch.setenv("ALPACA_ORDER_RECEIPT_MAX_AGE_SECONDS", "300")
    monkeypatch.delenv("PROMETHEUS_METRICS_PORT", raising=False)
    instance = AlpacaClient()
    try:
        yield instance
    finally:
        instance.close()


def test_latest_crypto_quotes_require_fresh_two_sided_provider_data(client, monkeypatch):
    fresh_time = _iso_now(-1)
    stale_time = _iso_now(-1000)

    def request(_method, _endpoint, **_kwargs):
        return {
            "quotes": {
                "BTC/USD": {"bp": "100", "ap": "102", "t": fresh_time},
                "ETH/USD": {"bp": "20", "t": fresh_time},
                "LTC/USD": {"bp": "8", "ap": "9", "t": stale_time},
            }
        }

    monkeypatch.setattr(client, "_request", request)

    quotes = client.get_latest_crypto_quotes(["BTC/USD", "ETH/USD", "LTC/USD"])

    assert list(quotes) == ["BTC/USD"]
    assert quotes["BTC/USD"]["bp"] == 100.0
    assert quotes["BTC/USD"]["ap"] == 102.0
    assert quotes["BTC/USD"]["mid"] == 101.0
    assert quotes["BTC/USD"]["provider_timestamp_raw"] == fresh_time
    assert quotes["BTC/USD"]["source_timestamp"] == pytest.approx(
        datetime.fromisoformat(fresh_time).timestamp()
    )
    assert quotes["BTC/USD"]["generated_values"] is False


def test_crypto_bars_preserve_provider_time_and_reject_malformed_rows(client, monkeypatch):
    source_time = _iso_now(-60)

    def request(_method, _endpoint, **_kwargs):
        return {
            "bars": {
                "BTC/USD": [
                    {
                        "o": "100",
                        "h": "110",
                        "l": "95",
                        "c": "105",
                        "v": "12.5",
                        "t": source_time,
                    },
                    {"o": "100", "h": "110", "l": "95", "c": "105", "v": "2"},
                    {
                        "o": "100",
                        "h": "90",
                        "l": "95",
                        "c": "96",
                        "v": "2",
                        "t": source_time,
                    },
                ]
            }
        }

    monkeypatch.setattr(client, "_request", request)

    result = client.get_crypto_bars(["BTC/USD"])

    assert result["data_status"] == "live"
    assert len(result["bars"]["BTC/USD"]) == 1
    bar = result["bars"]["BTC/USD"][0]
    assert bar["provider_timestamp_raw"] == source_time
    assert bar["source_timestamp"] == pytest.approx(
        datetime.fromisoformat(source_time).timestamp()
    )
    assert bar["generated_values"] is False


def test_ticker_no_data_has_no_zero_or_one_sided_price(client, monkeypatch):
    monkeypatch.setattr(client, "get_latest_crypto_quotes", lambda _symbols: {})

    ticker = client.get_ticker("BTC/USD")

    assert ticker["data_status"] == "no_data"
    assert ticker["price"] is None
    assert ticker["bid"] is None
    assert ticker["ask"] is None
    assert ticker["last"] is None
    assert ticker["action_eligible"] is False


def test_dry_run_order_is_explicitly_not_submitted(client, monkeypatch):
    client.dry_run = True
    monkeypatch.setattr(
        client,
        "_request",
        lambda *_args, **_kwargs: pytest.fail("dry-run must not call Alpaca"),
    )

    receipt = client.place_order("BTC/USD", 0.01, "buy", type="market")

    assert receipt["status"] == "not_submitted"
    assert receipt["submitted"] is False
    assert receipt["provider_order_id"] is None
    assert receipt["fills"] == []
    assert receipt["filled_qty"] is None
    assert receipt["fill_receipt_complete"] is False
    assert receipt["eligible_for_accounting"] is False
    assert receipt["eligible_for_learning"] is False
    assert receipt["generated_values"] is False


def test_submission_acknowledgement_remains_pending_without_fill(client, monkeypatch):
    order_id = "31f54367-960a-41d6-9a23-1fc61cf8c91c"
    monkeypatch.setattr(
        client,
        "_request",
        lambda *_args, **_kwargs: {
            "id": order_id,
            "status": "new",
            "submitted_at": _iso_now(-1),
            "symbol": "AAPL",
            "side": "buy",
        },
    )

    receipt = client.place_order("AAPL", 2, "buy", type="limit")

    assert receipt["provider_order_id"] == order_id
    assert receipt["provider_status"] == "new"
    assert receipt["status"] == "pending_reconciliation"
    assert receipt["submitted"] is True
    assert receipt["fill_receipt_complete"] is False
    assert receipt["eligible_for_accounting"] is False
    assert receipt["filled_qty"] is None
    assert receipt["generated_values"] is False


def _filled_order(*, filled_at: str, commission=None, currency=None):
    order = {
        "id": "31f54367-960a-41d6-9a23-1fc61cf8c91c",
        "status": "filled",
        "filled_qty": "2",
        "filled_avg_price": "101",
        "filled_at": filled_at,
        "symbol": "AAPL",
        "side": "buy",
    }
    if commission is not None:
        order["commission"] = commission
    if currency is not None:
        order["currency"] = currency
    return order


def _fill_activity(*, transaction_time: str, commission=None, currency=None):
    activity = {
        "activity_type": "FILL",
        "id": "20260810120000000::5a5ac271-bb70-4c48-af11-35b86e5c1475",
        "order_id": "31f54367-960a-41d6-9a23-1fc61cf8c91c",
        "symbol": "AAPL",
        "side": "buy",
        "qty": "2",
        "price": "101",
        "transaction_time": transaction_time,
    }
    if commission is not None:
        activity["commission"] = commission
    if currency is not None:
        activity["currency"] = currency
    return activity


def test_filled_order_without_provider_fee_stays_pending(client):
    provider_time = _iso_now(-1)

    receipt = client._normalize_order_receipt(
        _filled_order(filled_at=provider_time),
        fill_activities=[_fill_activity(transaction_time=provider_time)],
        submission_attempted=True,
    )

    assert receipt["provider_status"] == "filled"
    assert receipt["status"] == "pending_reconciliation"
    assert receipt["reason"] == "provider_fee_receipt_and_currency_required"
    assert receipt["filled_qty"] == 2.0
    assert receipt["filled_avg_price"] == 101.0
    assert receipt["fee"] is None
    assert receipt["fill_receipt_complete"] is False
    assert receipt["eligible_for_accounting"] is False
    assert receipt["eligible_for_learning"] is False


def test_fresh_fill_activity_and_provider_fee_complete_terminal_receipt(client):
    provider_time = _iso_now(-1)

    receipt = client._normalize_order_receipt(
        _filled_order(filled_at=provider_time),
        fill_activities=[
            _fill_activity(
                transaction_time=provider_time,
                commission="0.25",
                currency="USD",
            )
        ],
        submission_attempted=True,
    )

    assert receipt["status"] == "filled"
    assert receipt["data_status"] == "live"
    assert receipt["provider_order_id"] == "31f54367-960a-41d6-9a23-1fc61cf8c91c"
    assert receipt["fills"][0]["trade_id"].startswith("20260810120000000::")
    assert receipt["filled_qty"] == 2.0
    assert receipt["filled_avg_price"] == 101.0
    assert receipt["filled_notional"] == 202.0
    assert receipt["fee"] == 0.25
    assert receipt["fee_currency"] == "USD"
    assert receipt["fill_receipt_complete"] is True
    assert receipt["eligible_for_accounting"] is True
    assert receipt["eligible_for_learning"] is True
    assert receipt["generated_values"] is False


def test_stale_terminal_fill_is_not_accounting_eligible(client):
    stale_time = _iso_now(-1000)

    receipt = client._normalize_order_receipt(
        _filled_order(filled_at=stale_time, commission="0", currency="USD"),
        fill_activities=[
            _fill_activity(
                transaction_time=stale_time,
                commission="0",
                currency="USD",
            )
        ],
        submission_attempted=True,
    )

    assert receipt["status"] == "pending_reconciliation"
    assert receipt["fill_receipt_complete"] is False
    assert receipt["eligible_for_accounting"] is False
    assert receipt["eligible_for_learning"] is False


def test_fee_helper_never_estimates_missing_provider_fee(client):
    raw_order = _filled_order(filled_at=_iso_now(-1))

    fee = client.compute_order_fees(raw_order)

    assert fee["data_status"] == "no_data"
    assert fee["fee"] is None
    assert fee["fee_currency"] is None
    assert fee["generated_values"] is False


def test_multi_hop_conversion_never_implicitly_submits_orders(client, monkeypatch):
    provider_time = _iso_now(-1)
    path = [
        {"pair": "ETH/USD", "side": "sell"},
        {"pair": "BTC/USD", "side": "buy"},
    ]
    quotes = {
        "ETH/USD": {
            "bp": 2000.0,
            "ap": 2001.0,
            "provider_timestamp": datetime.fromisoformat(provider_time).timestamp(),
        },
        "BTC/USD": {
            "bp": 100000.0,
            "ap": 100010.0,
            "provider_timestamp": datetime.fromisoformat(provider_time).timestamp(),
        },
    }
    monkeypatch.setattr(client, "find_conversion_path", lambda *_args: path)
    monkeypatch.setattr(
        client,
        "get_latest_crypto_quotes",
        lambda symbols: {symbols[0]: quotes[symbols[0]]},
    )
    monkeypatch.setattr(
        client,
        "place_market_order",
        lambda *_args, **_kwargs: pytest.fail("route planning must not submit orders"),
    )

    result = client.convert_crypto("ETH", "BTC", 2.0)

    assert result["status"] == "not_submitted"
    assert result["submitted"] is False
    assert result["reason"] == (
        "explicit_per_hop_order_authority_and_terminal_receipts_required"
    )
    assert len(result["price_evidence"]) == 2
    assert result["fill_receipt_complete"] is False
    assert result["eligible_for_accounting"] is False
    assert result["generated_values"] is False


def test_spread_no_data_uses_none_not_zero(client, monkeypatch):
    monkeypatch.setattr(client, "get_orderbook", lambda _symbol: {})
    monkeypatch.setattr(client, "get_latest_crypto_quotes", lambda _symbols: {})

    spread = client.get_spread("BTC/USD")

    assert spread["data_status"] == "no_data"
    assert spread["bid"] is None
    assert spread["ask"] is None
    assert spread["mid"] is None
    assert spread["spread_abs"] is None
    assert spread["spread_pct"] is None
    assert spread["generated_values"] is False


def test_trade_cost_never_infers_provider_fee(client, monkeypatch):
    provider_epoch = datetime.now(timezone.utc).timestamp()
    monkeypatch.setattr(
        client,
        "get_spread",
        lambda _symbol: {
            "bid": 100.0,
            "ask": 102.0,
            "mid": 101.0,
            "spread_abs": 2.0,
            "spread_pct": 2.0 / 101.0 * 100.0,
            "provider_timestamp": provider_epoch,
            "source_timestamp": provider_epoch,
            "data_status": "live",
            "generated_values": False,
        },
    )

    cost = client.estimate_trade_cost("BTC/USD", "buy", 2.0)

    assert cost["notional"] == 204.0
    assert cost["spread_cost"] == 2.0
    assert cost["fee"] is None
    assert cost["fee_currency"] is None
    assert cost["total_cost"] is None
    assert cost["data_status"] == "no_data"
    assert cost["eligible_for_accounting"] is False
    assert cost["generated_values"] is False
