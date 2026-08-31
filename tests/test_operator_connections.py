"""
Aureon Operator — unified connections tests.

Catalog completeness, the full-capacity readiness report, and the
/api/connections surface: masked reads with no key leak, keyless probe verdicts,
data-source key set via keystore, exchange writes DELEGATED (never stored in the
operator keystore), and the bearer gate. Offline, no network.
"""

from __future__ import annotations

import importlib
import pathlib
import tempfile

import pytest

pytest.importorskip("flask", reason="operator HTTP surface requires the `.[operator]` extra")
pytest.importorskip("cryptography", reason="keystore requires cryptography (Fernet)")

from aureon.operator import connections_api, keystore  # noqa: E402
from aureon.operator import connections_catalog as cat  # noqa: E402


@pytest.fixture()
def temp_store(monkeypatch):
    tmp = pathlib.Path(tempfile.mkdtemp())
    monkeypatch.setattr(keystore, "CONFIG_DIR", tmp)
    monkeypatch.setattr(keystore, "KEY_PATH", tmp / "provider_keys.key")
    monkeypatch.setattr(keystore, "STORE_PATH", tmp / "provider_keys.json.enc")
    # Isolate os.environ: apply_to_env() writes real env vars, and importing the
    # aureon package loads any local .env — snapshot and restore so tests don't
    # leak keys into one another (or read the developer's .env).
    import os as _os
    saved = dict(_os.environ)
    for var in keystore.managed_env_vars() + [c.key_env for c in cat.CATALOG if c.key_env]:
        _os.environ.pop(var, None)
    yield tmp
    _os.environ.clear()
    _os.environ.update(saved)


def _client():
    import aureon.operator.operator_server as srv

    importlib.reload(srv)
    return srv.create_app(
        test_ingress_release=srv.TestOnlyOperatorIngressRelease(
            master_key=b"operator-connections-route-test-key-material",
        )
    ).test_client()


# ── catalog ─────────────────────────────────────────────────────────────────

def test_catalog_spans_all_categories():
    cat_ids = {c.category for c in cat.CATALOG}
    for expected in ("exchange", "market_data", "space_science", "ephemeris",
                     "onchain_whale", "news_social", "notifications"):
        assert expected in cat_ids
    # keyed sources declare a credential env; keyless declare none
    for c in cat.CATALOG:
        if c.requirement == "keyless":
            assert not c.credential_env
        else:
            assert c.credential_env


def test_key_sources_have_get_keys_links():
    for c in cat.CATALOG:
        if c.requirement != "keyless":
            assert c.get_keys_url.startswith("http")


# ── readiness ─────────────────────────────────────────────────────────────────

def test_readiness_report_shape(temp_store):
    r = connections_api.readiness(llm_providers=[])
    s = r["summary"]
    assert {"capacity_pct", "keyed_present", "keyed_total", "all_connected",
            "missing_count", "keyless"} <= set(s)
    assert isinstance(r["missing"], list)
    # internally consistent regardless of which keys happen to be present
    assert s["keyed_total"] > 0
    assert 0 <= s["keyed_present"] <= s["keyed_total"]
    assert s["missing_count"] == s["keyed_total"] - s["keyed_present"]


def test_readiness_counts_a_saved_key(temp_store):
    keystore.save_provider("nasa", api_key="NASA-KEY-1234")
    r = connections_api.readiness(llm_providers=[])
    nasa = next(i for i in r["items"] if i["id"] == "nasa")
    assert nasa["present"] is True
    assert r["summary"]["keyed_present"] >= 1


# ── /api/connections surface ───────────────────────────────────────────────────

def test_connections_list_categorized_and_masked(temp_store):
    c = _client()
    c.post("/api/connections/coinapi", json={"api_key": "coin-SECRET-9999"})
    r = c.get("/api/connections")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "coin-SECRET-9999" not in body            # never leak the full key
    cats = {s["category"] for s in r.get_json()["categories"]}
    assert {"ai_llm", "exchange", "space_science", "onchain_whale"} <= cats
    coinapi = next(x for s in r.get_json()["categories"] for x in s["connections"] if x["id"] == "coinapi")
    assert coinapi["has_key"] is True and coinapi["key_masked"].endswith("9999")


def test_set_data_source_persists_to_keystore(temp_store):
    c = _client()
    r = c.post("/api/connections/firms", json={"api_key": "firms-abc1234", "enabled": True})
    assert r.status_code == 200 and r.get_json()["ok"] is True
    assert "firms-abc1234" not in r.get_data(as_text=True)
    assert keystore.load().get("firms", {}).get("api_key") == "firms-abc1234"


def test_exchange_write_is_delegated_not_keystored(temp_store, monkeypatch):
    calls = {}

    def fake_set(conn, api_key, extra):
        calls["conn"] = conn.id
        return {"ok": True, "updated_keys": [conn.key_env], "restart_required": True}

    monkeypatch.setattr(connections_api, "set_exchange_credential", fake_set)
    c = _client()
    r = c.post("/api/connections/binance", json={"api_key": "bnkey", "extra": {"BINANCE_API_SECRET": "s"}})
    assert r.status_code == 200 and r.get_json()["ok"] is True
    assert calls.get("conn") == "binance"
    assert "binance" not in keystore.load()          # NOT stored in the operator keystore


def test_readiness_endpoint(temp_store):
    r = _client().get("/api/connections/readiness")
    assert r.status_code == 200
    assert "summary" in r.get_json() and "missing" in r.get_json()


def test_keyless_probe_needs_no_key():
    noaa = cat.get_connection("noaa_swpc")
    assert noaa is not None and noaa.requirement == "keyless"
    # keyed source without a key → verdict "no key", never an exception
    nasa = cat.get_connection("nasa")
    v = connections_api.probe(nasa, api_key="")
    assert v["ok"] is False and "no key" in v["error"]


def test_unknown_connection_404(temp_store):
    assert _client().post("/api/connections/nope", json={}).status_code == 404


def test_connection_writes_bearer_gated(temp_store, monkeypatch):
    monkeypatch.setenv("AUREON_OPERATOR_API_KEY", "sesame")
    c = _client()
    assert c.post("/api/connections/coinapi", json={"api_key": "x"}).status_code == 401
    ok = c.post("/api/connections/coinapi", json={"api_key": "coin-abc1234"},
                headers={"Authorization": "Bearer sesame"})
    assert ok.status_code == 200
