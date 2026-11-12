from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


MODULE = Path(__file__).resolve().parents[1] / "trading-control" / "firestore_ledger.py"
spec = importlib.util.spec_from_file_location("firestore_ledger", MODULE)
ledger_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ledger_module
spec.loader.exec_module(ledger_module)


class Response:
    def __init__(self, status, value):
        self.status_code, self.value = status, value

    def json(self):
        return self.value


class Firestore:
    def __init__(self):
        self.effect = None
        self.budget = None
        self.calls = []

    def __call__(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if url.endswith(":beginTransaction"):
            return Response(200, {"transaction": "dHJhbnNhY3Rpb24="})
        if method == "GET" and "/aureon_trade_effects/" in url:
            return Response(404, {}) if self.effect is None else Response(200, self.effect)
        if method == "GET" and "/aureon_trade_budgets/" in url:
            return Response(404, {}) if self.budget is None else Response(200, self.budget)
        if url.endswith(":commit"):
            writes = kwargs["json"]["writes"]
            assert writes[0]["currentDocument"] == {"exists": False}
            assert writes[1]["currentDocument"] == {"exists": False}
            self.effect = {**writes[0]["update"], "updateTime": "t1"}
            self.budget = {**writes[1]["update"], "updateTime": "t1"}
            return Response(200, {"writeResults": [{"updateTime": "t1"}, {"updateTime": "t1"}]})
        if method == "PATCH":
            assert kwargs["params"]["currentDocument.updateTime"] == "t1"
            assert set(kwargs["params"]["updateMask.fieldPaths"]) >= {"state", "updated_at_ms"}
            fields = {**self.effect["fields"], **kwargs["json"]["fields"]}
            self.effect = {**self.effect, "fields": fields, "updateTime": "t2"}
            return Response(200, self.effect)
        raise AssertionError((method, url, kwargs))


def make_ledger(fake, budget=20):
    return ledger_module.FirestoreLedger(budget, requester=fake, token_provider=lambda: "t" * 40)


def test_reservation_atomically_claims_effect_and_daily_budget_then_transitions():
    fake = Firestore()
    ledger = make_ledger(fake)
    result = ledger.reserve(
        intent_id="a" * 64, order_sha256="b" * 64, authorization_sha256="c" * 64,
        instrument_preflight_sha256="d" * 64,
        venue="binance", quote_value_usd=5.0, now_ms=1_789_000_000_000,
    )
    assert result["created"] is True and result["state"] == "claimed"
    fields = fake.budget["fields"]
    assert fields["reserved_usd"] == {"doubleValue": 5.0}
    updated = ledger.transition(
        "a" * 64, expected_update_time="t1", state="observed", now_ms=1_789_000_000_001,
        provider_order_id="provider-1", provider_readback_sha256="d" * 64,
    )
    assert updated["state"] == "observed" and updated["provider_order_id"] == "provider-1"


def test_existing_effect_is_returned_without_reserving_budget_twice():
    fake = Firestore()
    ledger = make_ledger(fake)
    first = ledger.reserve(intent_id="a" * 64, order_sha256="b" * 64, authorization_sha256="c" * 64,
                           instrument_preflight_sha256="d" * 64, venue="alpaca",
                           quote_value_usd=2.0, now_ms=1_789_000_000_000)
    second = ledger.reserve(intent_id="a" * 64, order_sha256="b" * 64, authorization_sha256="c" * 64,
                            instrument_preflight_sha256="d" * 64, venue="alpaca",
                            quote_value_usd=2.0, now_ms=1_789_000_000_100)
    assert first["created"] is True and second["created"] is False
    assert sum(1 for method, url, _ in fake.calls if url.endswith(":commit")) == 1


def test_budget_and_commitment_mismatch_fail_closed():
    fake = Firestore()
    ledger = make_ledger(fake, budget=4)
    with pytest.raises(ledger_module.LedgerError, match="daily_budget_exceeded"):
        ledger.reserve(intent_id="a" * 64, order_sha256="b" * 64, authorization_sha256="c" * 64,
                       instrument_preflight_sha256="d" * 64, venue="kraken",
                       quote_value_usd=5.0, now_ms=1_789_000_000_000)
    assert not any(url.endswith(":commit") for _, url, _ in fake.calls)
    fake = Firestore()
    ledger = make_ledger(fake)
    ledger.reserve(intent_id="a" * 64, order_sha256="b" * 64, authorization_sha256="c" * 64,
                   instrument_preflight_sha256="d" * 64, venue="capital",
                   quote_value_usd=1.0, now_ms=1_789_000_000_000)
    with pytest.raises(ledger_module.LedgerError, match="commitment_mismatch"):
        ledger.reserve(intent_id="a" * 64, order_sha256="b" * 64, authorization_sha256="c" * 64,
                       instrument_preflight_sha256="f" * 64, venue="capital",
                       quote_value_usd=1.0, now_ms=1_789_000_000_050)
    with pytest.raises(ledger_module.LedgerError, match="commitment_mismatch"):
        ledger.reserve(intent_id="a" * 64, order_sha256="e" * 64, authorization_sha256="c" * 64,
                       instrument_preflight_sha256="d" * 64, venue="capital",
                       quote_value_usd=1.0, now_ms=1_789_000_000_100)


def test_document_payload_contains_no_credentials():
    fake = Firestore()
    make_ledger(fake).reserve(intent_id="a" * 64, order_sha256="b" * 64, authorization_sha256="c" * 64,
                              instrument_preflight_sha256="d" * 64, venue="binance",
                              quote_value_usd=1.0, now_ms=1_789_000_000_000)
    encoded = json.dumps(fake.calls).lower()
    for forbidden in ("api_key", "secret_key", "password", "credential"):
        assert forbidden not in encoded
