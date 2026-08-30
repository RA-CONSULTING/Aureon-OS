from __future__ import annotations

from email.utils import formatdate

import pytest

from aureon.exchanges import capital_client as module
from aureon.exchanges.capital_client import CapitalClient


class _Response:
    status_code = 200

    def __init__(self, payload, *, now: float) -> None:
        self._payload = payload
        self.headers = {"Date": formatdate(now, usegmt=True)}

    def json(self):
        return self._payload


def _client(monkeypatch: pytest.MonkeyPatch, payload, *, now: float) -> CapitalClient:
    client = object.__new__(CapitalClient)
    client.enabled = True
    calls = []

    def request(method, path, **kwargs):
        calls.append((method, path, kwargs))
        return _Response(payload, now=now)

    client._request = request
    client.transaction_test_calls = calls
    monkeypatch.setattr(module.time, "time", lambda: now)
    return client


def test_transaction_history_is_exact_read_only_observation(monkeypatch) -> None:
    now = 1_786_632_900.0
    client = _client(
        monkeypatch,
        {
            "transactions": [
                {
                    "currency": "GBP",
                    "dateUtc": "2026-08-13T14:14:58.000",
                    "instrumentName": "GOLD",
                    "note": "Trade closed",
                    "reference": "DEAL-1",
                    "size": "-1.25",
                    "status": "PROCESSED",
                    "transactionType": "TRADE",
                }
            ]
        },
        now=now,
    )

    result = client.get_transaction_history(last_period=900)

    assert client.transaction_test_calls == [
        ("GET", "/history/transactions", {"params": {"lastPeriod": 900}})
    ]
    assert result.truth_status == "real_observed"
    assert result.reason == "complete_provider_transaction_history"
    assert result[0]["amount"] == -1.25
    assert result[0]["reference"] == "DEAL-1"
    assert result[0]["generated_values"] is False


def test_incomplete_transaction_row_invalidates_absence_proof(monkeypatch) -> None:
    now = 1_786_632_900.0
    client = _client(
        monkeypatch,
        {
            "transactions": [
                {
                    "currency": "GBP",
                    "dateUtc": "2026-08-13T14:14:58.000",
                    "instrumentName": "GOLD",
                    "reference": "DEAL-1",
                    "status": "PROCESSED",
                    "transactionType": "TRADE",
                }
            ]
        },
        now=now,
    )

    result = client.get_transaction_history()

    assert result == []
    assert result.truth_status == "incomplete"
    assert result.reason == "transaction_history_contains_incomplete_rows"


@pytest.mark.parametrize("window", [True, 0, 86_401])
def test_invalid_transaction_windows_never_call_provider(monkeypatch, window) -> None:
    now = 1_786_632_900.0
    client = _client(monkeypatch, {"transactions": []}, now=now)

    result = client.get_transaction_history(window)

    assert result.truth_status == "no_data"
    assert client.transaction_test_calls == []
