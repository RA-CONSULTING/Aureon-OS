"""
Aureon Operator — provider API-key management tests.

Covers the encrypted keystore, the OpenAI-compatible registry rows, and the
/api/providers surface (list is masked, set persists + never leaks the full key,
test degrades to a verdict, delete clears, and writes are bearer-gated when the
operator API key is set). Offline, no network.
"""

from __future__ import annotations

import importlib
import pathlib
import tempfile

import pytest

pytest.importorskip("flask", reason="operator HTTP surface requires the `.[operator]` extra")
pytest.importorskip("cryptography", reason="keystore requires cryptography (Fernet)")

from aureon.operator import keystore  # noqa: E402
from aureon.operator import provider_catalog as catalog  # noqa: E402


@pytest.fixture()
def temp_store(monkeypatch):
    """Point the keystore at a throwaway dir so we never touch ~/.aureon."""
    tmp = pathlib.Path(tempfile.mkdtemp())
    monkeypatch.setattr(keystore, "CONFIG_DIR", tmp)
    monkeypatch.setattr(keystore, "KEY_PATH", tmp / "provider_keys.key")
    monkeypatch.setattr(keystore, "STORE_PATH", tmp / "provider_keys.json.enc")
    return tmp


def _client():
    import aureon.operator.operator_server as srv

    importlib.reload(srv)
    return srv.create_app().test_client()


# ── catalog ─────────────────────────────────────────────────────────────────

def test_catalog_has_all_providers():
    ids = catalog.provider_ids()
    for expected in ("openai", "anthropic", "grok", "gemini", "ollama",
                     "deepseek", "mistral", "groq", "openrouter", "perplexity"):
        assert expected in ids
    for p in catalog.CATALOG:
        assert p.get_keys_url.startswith("http") and p.docs_url.startswith("http")


# ── keystore ──────────────────────────────────────────────────────────────────

def test_keystore_roundtrip_and_masking(temp_store):
    keystore.save_provider("deepseek", api_key="sk-secret-ABCD1234", model="deepseek-chat")
    view = keystore.masked_view()["deepseek"]
    assert view["has_key"] is True
    assert view["key_masked"].endswith("1234")
    assert "ABCD1234" not in view["key_masked"]        # only the last 4 survive
    assert view["model"] == "deepseek-chat"


def test_keystore_apply_and_disable(temp_store, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    keystore.save_provider("deepseek", api_key="sk-secret-ABCD1234", enabled=True)
    keystore.apply_to_env()
    import os
    assert os.environ.get("DEEPSEEK_API_KEY") == "sk-secret-ABCD1234"
    # disabling removes the key env so the line drops out
    keystore.save_provider("deepseek", enabled=False)
    keystore.apply_to_env()
    assert "DEEPSEEK_API_KEY" not in os.environ


def test_unknown_provider_rejected(temp_store):
    with pytest.raises(KeyError):
        keystore.save_provider("not-a-provider", api_key="x")


# ── openai_compat registry build ──────────────────────────────────────────────

def test_openai_compat_row_is_key_gated(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    from aureon.operator.config import default_registry

    groq = next(s for s in default_registry() if s.name == "groq")
    assert groq.kind == "openai_compat"
    assert groq.key_present() is False           # skipped until a key is set
    monkeypatch.setenv("GROQ_API_KEY", "gsk-x")
    groq2 = next(s for s in default_registry() if s.name == "groq")
    assert groq2.key_present() is True


# ── /api/providers surface ─────────────────────────────────────────────────────

def test_get_providers_lists_catalog(temp_store):
    r = _client().get("/api/providers")
    assert r.status_code == 200
    provs = r.get_json()["providers"]
    assert {p["id"] for p in provs} >= {"openai", "anthropic", "ollama", "groq"}
    for p in provs:  # never expose a raw key field
        assert "api_key" not in p


def test_set_provider_masks_and_never_leaks(temp_store):
    c = _client()
    r = c.post("/api/providers/mistral", json={"api_key": "sk-mistral-ZZZZ9999", "enabled": True})
    assert r.status_code == 200
    assert "sk-mistral-ZZZZ9999" not in r.get_data(as_text=True)   # full key never returned
    prov = r.get_json()["provider"]
    assert prov["has_key"] is True and prov["key_masked"].endswith("9999")
    # and a fresh GET still only shows the masked value
    body = c.get("/api/providers").get_data(as_text=True)
    assert "sk-mistral-ZZZZ9999" not in body


def test_test_endpoint_returns_verdict_not_500(temp_store, monkeypatch):
    monkeypatch.setenv("AUREON_LLM_OFFLINE", "1")
    c = _client()
    r = c.post("/api/providers/deepseek/test", json={"api_key": "sk-x"})
    assert r.status_code == 200
    v = r.get_json()
    assert set(v) >= {"ok", "latency_ms", "model", "error"}
    assert v["ok"] is False            # offline → cannot round-trip, but no 500


def test_delete_provider(temp_store):
    c = _client()
    c.post("/api/providers/groq", json={"api_key": "gsk-abc1234"})
    assert c.delete("/api/providers/groq").status_code == 200
    prov = next(p for p in c.get("/api/providers").get_json()["providers"] if p["id"] == "groq")
    assert prov["has_key"] is False


def test_unknown_provider_404(temp_store):
    assert _client().post("/api/providers/nope", json={}).status_code == 404


def test_provider_writes_bearer_gated(temp_store, monkeypatch):
    monkeypatch.setenv("AUREON_OPERATOR_API_KEY", "topsecret")
    c = _client()
    # no bearer → 401 on the write
    assert c.post("/api/providers/openai", json={"api_key": "x"}).status_code == 401
    # correct bearer → allowed
    ok = c.post("/api/providers/openai", json={"api_key": "sk-abc1234"},
                headers={"Authorization": "Bearer topsecret"})
    assert ok.status_code == 200
