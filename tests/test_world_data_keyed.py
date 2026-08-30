"""
Aureon — keyed world-data fetchers (Phase 16): NOAA NCEI CDO + USGS Water.

These two feeds are the first *keyed* consumers of NOAA_API_KEY / USGS_API_KEY
in the HNC Λ(t) pipeline. The tests pin the two behaviours the daemon relies on:
they **degrade to None** (a clean keyless-skip, never an exception) when the key
is absent or the HTTP layer fails, and they parse a well-formed payload into a
``WorldDataItem`` with the right source/category. Offline — the HTTP call is
stubbed, no network.
"""

from __future__ import annotations

import os

import pytest

from aureon.integrations.world_data.world_data_ingester import (
    WorldDataIngester,
    WorldDataItem,
)


@pytest.fixture()
def no_keys(monkeypatch):
    monkeypatch.delenv("NOAA_API_KEY", raising=False)
    monkeypatch.delenv("USGS_API_KEY", raising=False)


def test_noaa_and_usgs_skip_cleanly_without_a_key(no_keys):
    w = WorldDataIngester()
    assert w.fetch_noaa_climate() is None
    assert w.fetch_usgs_water() is None


def test_keyed_fetchers_return_none_when_http_fails(monkeypatch):
    monkeypatch.setenv("NOAA_API_KEY", "noaa-key")
    monkeypatch.setenv("USGS_API_KEY", "usgs-key")
    w = WorldDataIngester()
    # stub the headered GET to fail like a transport error
    monkeypatch.setattr(w, "_http_get_headers", lambda url, headers: None)
    assert w.fetch_noaa_climate() is None
    assert w.fetch_usgs_water() is None


def test_noaa_parses_datasets_payload(monkeypatch):
    monkeypatch.setenv("NOAA_API_KEY", "noaa-key")
    w = WorldDataIngester()
    captured = {}

    def fake_get(url, headers):
        captured["url"] = url
        captured["headers"] = headers
        return {"results": [{"id": "GHCND", "name": "Daily Summaries"}, {"id": "GSOM"}]}

    monkeypatch.setattr(w, "_http_get_headers", fake_get)
    item = w.fetch_noaa_climate()

    assert isinstance(item, WorldDataItem)
    assert item.source == "noaa_cdo"
    assert item.category == "environmental"
    assert "Daily Summaries" in item.title
    assert item.raw["count"] == 2
    # the CDO auth header is `token`, and the endpoint is /datasets (token-only)
    assert captured["headers"]["token"] == "noaa-key"
    assert "/datasets" in captured["url"]


def test_usgs_parses_collections_payload(monkeypatch):
    monkeypatch.setenv("USGS_API_KEY", "usgs-key")
    w = WorldDataIngester()
    captured = {}

    def fake_get(url, headers):
        captured["headers"] = headers
        return {"collections": [{"id": "monitoring-locations", "title": "Monitoring Locations"}]}

    monkeypatch.setattr(w, "_http_get_headers", fake_get)
    item = w.fetch_usgs_water()

    assert isinstance(item, WorldDataItem)
    assert item.source == "usgs_water"
    assert item.category == "environmental"
    assert item.raw["count"] == 1
    # USGS Water Data uses the `X-Api-Key` header
    assert captured["headers"]["X-Api-Key"] == "usgs-key"


def test_daemon_mappers_handle_none_and_payload():
    from aureon.core.hnc_live_daemon import _map_noaa_climate, _map_usgs_water

    # Missing measurements stay no_data; no numeric neutral enters the equation.
    for mapper in (_map_noaa_climate, _map_usgs_water):
        assert mapper(None) is None

    noaa = _map_noaa_climate(WorldDataItem(source="noaa_cdo", topic="d", title="t", text="x", raw={"count": 5}))
    assert noaa is None
    usgs = _map_usgs_water(WorldDataItem(source="usgs_water", topic="c", title="t", text="x", raw={"count": 35}))
    assert usgs is None
