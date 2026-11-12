"""Wiring test: the refresher's Alpaca call must match ingest_alpaca_stocks' real signature.

Before this fix the call left out the required ``no_resume`` argument, so it raised
TypeError inside a try/except and stock bars were silently never refreshed.
No network: the real ingest function is swapped for a spy that only binds arguments.
"""
from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone

import scripts.python.ingest_market_history as imh
from aureon.data_feeds import market_data_refresher as mdr


def test_alpaca_call_binds_to_real_signature(monkeypatch):
    real_sig = inspect.signature(imh.ingest_alpaca_stocks)
    calls = []

    def spy(*args, **kwargs):
        bound = real_sig.bind(*args, **kwargs)  # raises TypeError on a mismatch
        calls.append(dict(bound.arguments))

    monkeypatch.setattr(imh, "ingest_alpaca_stocks", spy)
    monkeypatch.setenv("ALPACA_API_KEY", "test-key-not-real")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "test-secret-not-real")

    end = datetime.now(timezone.utc)
    mdr._run_alpaca(None, end - timedelta(hours=1), end)

    assert len(calls) == 1
    assert calls[0]["no_resume"] is False
