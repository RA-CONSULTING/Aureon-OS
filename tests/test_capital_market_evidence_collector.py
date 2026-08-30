from __future__ import annotations

from typing import Any

import pytest

import aureon.exchanges.capital_client as capital_module
from aureon.exchanges.capital_client import CapitalClient
from aureon.trading.capital_market_evidence_collector import collect_capital_market_evidence

NOW = 1_786_480_000.0
EPIC = "CS.D.GOLD.CFD.IP"


class _Observed(list):
    def __init__(self, values=(), *, truth_status="real_observed"):
        super().__init__(values)
        self.truth_status = truth_status
        self.source_timestamp = NOW - 1.0
        self.received_at = NOW - 0.5


class _Client:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    def get_ticker(self, symbol: str):
        self.calls.append(("quote", symbol))
        return {
            "action_eligible": True,
            "ask": 4_329.1,
            "bid": 4_328.9,
            "change_pct": 0.25,
            "epic": EPIC,
            "generated_values": False,
            "high": 4_331.0,
            "low": 4_327.0,
            "market_status": "TRADEABLE",
            "received_at": NOW - 0.5,
            "source_id": f"capital_market:{EPIC}",
            "source_timestamp": NOW - 1.0,
            "symbol": "GOLD",
            "truth_status": "real_derived",
        }

    def get_price_history(self, epic: str, *, resolution: str, max_points: int):
        self.calls.append(("history", epic, resolution, max_points))
        bars = []
        for index in range(30):
            mid = 4_300.0 + index
            bars.append(
                {
                    "timestamp": NOW - (30 - index) * 60.0,
                    "open_bid": mid - 0.1,
                    "open_ask": mid + 0.1,
                    "high_bid": mid + 0.3,
                    "high_ask": mid + 0.5,
                    "low_bid": mid - 0.5,
                    "low_ask": mid - 0.3,
                    "close_bid": mid - 0.1,
                    "close_ask": mid + 0.1,
                    "volume": 100 + index,
                }
            )
        return _Observed(bars)

    def get_accounts(self, *, cache_ttl: float):
        self.calls.append(("accounts", cache_ttl))
        return _Observed(
            [
                {
                    "accountId": "must-not-leak",
                    "action_eligible": True,
                    "available": 226.88,
                    "balance": 226.88,
                    "currency": "GBP",
                    "generated_values": False,
                    "preferred": True,
                    "source_id": "capital_account:must-not-leak",
                    "truth_status": "real_observed",
                }
            ]
        )

    def get_positions(self):
        self.calls.append(("positions",))
        return _Observed()

    def get_working_orders(self):
        self.calls.append(("working_orders",))
        return _Observed()


def _context():
    return [
        {
            "source_kind": "cftc_cot",
            "source_id": "cftc:gold:weekly",
            "source_uri": "https://publicreporting.cftc.gov/resource/6dca-aqww.json",
            "source_timestamp": NOW - 86_400.0,
            "received_at": NOW - 0.5,
            "payload": {"market": "GOLD", "net_contracts": 1},
        },
        {
            "source_kind": "treasury_yield",
            "source_id": "treasury:daily:rates",
            "source_uri": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates",
            "source_timestamp": NOW - 86_400.0,
            "received_at": NOW - 0.5,
            "payload": {"ten_year_yield_pct": 4.2},
        },
    ]


def test_collector_reads_all_five_capital_surfaces_and_redacts_account_id() -> None:
    client = _Client()
    receipt = collect_capital_market_evidence(
        client=client,
        public_contexts=_context(),
        now=NOW,
    )

    assert client.calls == [
        ("quote", "GOLD"),
        ("history", EPIC, "MINUTE", 100),
        ("accounts", 0.0),
        ("positions",),
        ("working_orders",),
    ]
    assert receipt["action_influence_allowed"] is True
    assert receipt["recommended_side"] == "BUY"
    assert "must-not-leak" not in str(receipt)


def test_collector_fails_closed_on_ambiguous_account_or_no_data_surface() -> None:
    client = _Client()
    client.get_accounts = lambda **_kwargs: _Observed([])  # type: ignore[method-assign]
    with pytest.raises(ValueError, match="exact_one_enabled_gbp"):
        collect_capital_market_evidence(client=client, public_contexts=_context(), now=NOW)

    client = _Client()
    client.get_working_orders = lambda: _Observed([], truth_status="no_data")  # type: ignore[method-assign]
    with pytest.raises(ValueError, match="real_observed_capital_working_orders"):
        collect_capital_market_evidence(client=client, public_contexts=_context(), now=NOW)


class _Response:
    status_code = 200
    text = ""
    headers = {"Date": str(NOW - 1.0)}

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


def test_capital_read_client_keeps_quote_and_history_methods_separate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(capital_module.time, "time", lambda: NOW)
    client = CapitalClient.__new__(CapitalClient)
    client.enabled = True
    client.last_ticker_observation = None
    client._get_cached_monitor_quote = lambda _symbol: None
    client._ticker_is_actionable = lambda _quote: False
    client._resolve_market = lambda _symbol: {"epic": EPIC}
    client._get_market_snapshot = lambda _epic: {
        "_provider_response_source_timestamp": NOW - 1.0,
        "snapshot": {
            "bid": 4_328.9,
            "offer": 4_329.1,
            "percentageChange": 0.25,
            "updateTime": "2026-08-13T15:49:44.508",
            "updateTimeUTC": None,
            "high": 4_331.0,
            "low": 4_327.0,
            "marketStatus": "TRADEABLE",
        }
    }

    quote = client.get_ticker("GOLD")

    assert quote["epic"] == EPIC
    assert quote["action_eligible"] is True

    prices = []
    for index in range(20):
        mid = 4_300.0 + index
        prices.append(
            {
                "snapshotTimeUTC": NOW - (20 - index) * 60.0,
                "openPrice": {"bid": mid - 0.1, "ask": mid + 0.1},
                "highPrice": {"bid": mid + 0.3, "ask": mid + 0.5},
                "lowPrice": {"bid": mid - 0.5, "ask": mid - 0.3},
                "closePrice": {"bid": mid - 0.1, "ask": mid + 0.1},
                "lastTradedVolume": 100 + index,
            }
        )
    calls = []
    client._request = lambda method, path, **kwargs: (
        calls.append((method, path, kwargs)) or _Response({"prices": prices})
    )

    history = client.get_price_history(EPIC, resolution="MINUTE", max_points=20)

    assert len(history) == 20
    assert history.truth_status == "real_observed"
    assert calls == [
        ("GET", f"/prices/{EPIC}", {"params": {"resolution": "MINUTE", "max": 20}})
    ]


def test_capital_working_orders_empty_is_observed_not_request_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(capital_module.time, "time", lambda: NOW)
    client = CapitalClient.__new__(CapitalClient)
    client.enabled = True
    client._request = lambda *_args, **_kwargs: _Response({"workingOrders": []})

    orders = client.get_working_orders()

    assert orders == []
    assert orders.truth_status == "real_observed"
    assert orders.reason == "fresh_provider_working_orders"
