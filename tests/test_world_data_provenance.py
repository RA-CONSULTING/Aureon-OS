"""Offline provenance controls for WorldDataIngester."""

from __future__ import annotations

import time

from aureon.integrations.world_data.world_data_ingester import WorldDataIngester


class _Vault:
    def __init__(self) -> None:
        self.calls = []

    def ingest(self, **kwargs) -> None:
        self.calls.append(kwargs)


class _Bus:
    def __init__(self) -> None:
        self.calls = []

    def publish(self, *args, **kwargs) -> None:
        self.calls.append((args, kwargs))


def test_coingecko_requires_complete_fresh_receipt_and_preserves_provenance(monkeypatch):
    vault = _Vault()
    bus = _Bus()
    ingester = WorldDataIngester(vault=vault, thought_bus=bus)
    now = time.time()
    monkeypatch.setattr(ingester, "_http_get", lambda _url: {
        "id": "bitcoin",
        "name": "Bitcoin",
        "last_updated": now,
        "market_data": {
            "current_price": {"usd": 100.0},
            "price_change_percentage_24h": -1.5,
            "market_cap": {"usd": 1000.0},
            "total_volume": {"usd": 100.0},
        },
    })

    item = ingester.fetch_coingecko("bitcoin")
    assert item is not None
    assert item.source_timestamp == now
    assert ingester.ingest_to_vault([item]) == 1
    payload = vault.calls[0]["payload"]
    assert payload["source_id"] == "coingecko"
    assert payload["source_timestamp"] == now
    assert payload["received_at"] >= now
    assert payload["receipt_id"].startswith("bitcoin:")
    assert payload["truth_status"] == "real_observed"
    assert payload["generated_values"] is False
    assert payload["action_enabled"] is False
    assert payload["accounting_enabled"] is False
    assert payload["learning_enabled"] is False
    assert len(bus.calls) == 1

    monkeypatch.setattr(ingester, "_http_get", lambda _url: {
        "id": "bitcoin",
        "last_updated": now,
        "market_data": {"current_price": {"usd": 100.0}},
    })
    assert ingester.fetch_coingecko("bitcoin") is None
    item.source_timestamp = None
    assert ingester.ingest_to_vault([item]) == 0
    assert len(vault.calls) == 1
    assert len(bus.calls) == 1
