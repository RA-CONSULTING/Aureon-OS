"""
Aureon Operator — end-user identity + per-tenant key isolation.

Proves the multi-tenant increment holds its two hard invariants:
  * **Isolation** — one tenant can never read, test, or apply another tenant's keys; a tenant sees only
    their own isolated store, never the instance/admin env keys.
  * **No leak** — a tenant write NEVER mutates ``os.environ`` (the shared process env), which is the only
    way one tenant's key could leak into another's reasoning.

Also covers the identity resolver matrix and backward-compat (no secrets ⇒ open, unchanged). Offline; the
keystore is redirected to a tmp dir so the real ``~/.aureon`` is never touched.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import importlib
import json
import os
import time

import pytest

pytest.importorskip("flask", reason="operator HTTP surface requires the `.[operator]` extra")

from aureon.operator.identity import resolve_identity  # noqa: E402

SECRET = "tenant-test-secret"
ADMIN_KEY = "admin-static-key"


def _mk_jwt(sub: str, secret: str = SECRET, exp: float | None = None) -> str:
    def b(d: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()

    h, p = b({"alg": "HS256", "typ": "JWT"}), b({"sub": sub, "exp": exp or time.time() + 3600})
    sig = base64.urlsafe_b64encode(
        hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()
    ).rstrip(b"=").decode()
    return f"{h}.{p}.{sig}"


def _tenant(sub: str) -> dict:
    return {"Authorization": f"Bearer {_mk_jwt(sub)}"}


_ADMIN = {"Authorization": f"Bearer {ADMIN_KEY}"}


@pytest.fixture
def env(tmp_path, monkeypatch):
    """A tenancy-enabled operator with the keystore isolated to a tmp dir. Returns (client, keystore)."""
    monkeypatch.setenv("AUREON_LLM_OFFLINE", "1")
    monkeypatch.setenv("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
    monkeypatch.setenv("AUREON_SUPABASE_JWT_SECRET", SECRET)
    monkeypatch.setenv("AUREON_OPERATOR_API_KEY", ADMIN_KEY)

    import aureon.operator.keystore as ks

    importlib.reload(ks)
    cfg = tmp_path / ".aureon"
    monkeypatch.setattr(ks, "CONFIG_DIR", cfg)
    monkeypatch.setattr(ks, "KEY_PATH", cfg / "provider_keys.key")
    monkeypatch.setattr(ks, "STORE_PATH", cfg / "provider_keys.json.enc")
    monkeypatch.setattr(ks, "TENANTS_DIR", cfg / "tenants")

    import aureon.operator.operator_server as srv

    importlib.reload(srv)
    return srv.create_app().test_client(), ks, cfg


def _openai_view(payload: dict) -> dict:
    return next(p for p in payload["providers"] if p["id"] == "openai")


# ── identity resolver matrix ────────────────────────────────────────────────────

def test_resolve_identity_matrix():
    # open: neither secret configured
    assert resolve_identity(None, operator_key="", jwt_secret="") == \
        __import__("aureon.operator.identity", fromlist=["Identity"]).Identity("open", None, True)
    # admin: static key
    i = resolve_identity(f"Bearer {ADMIN_KEY}", operator_key=ADMIN_KEY, jwt_secret=SECRET)
    assert (i.kind, i.tenant, i.ok) == ("admin", None, True)
    # tenant: valid jwt
    i = resolve_identity(f"Bearer {_mk_jwt('user-x')}", operator_key=ADMIN_KEY, jwt_secret=SECRET)
    assert (i.kind, i.tenant, i.ok) == ("tenant", "user-x", True)
    # invalid token when a scheme is on
    assert resolve_identity("Bearer nope", operator_key=ADMIN_KEY, jwt_secret=SECRET).ok is False
    # expired jwt
    bad = _mk_jwt("user-x", exp=time.time() - 10)
    assert resolve_identity(f"Bearer {bad}", operator_key="", jwt_secret=SECRET).ok is False


# ── isolation over the HTTP surface ─────────────────────────────────────────────

def test_tenant_keys_are_isolated(env):
    client, _ks, _cfg = env
    r = client.post("/api/providers/openai", json={"api_key": "sk-AAAA1234"}, headers=_tenant("aaa"))
    assert r.status_code == 200

    a_view = _openai_view(client.get("/api/providers", headers=_tenant("aaa")).get_json())
    b_view = _openai_view(client.get("/api/providers", headers=_tenant("bbb")).get_json())
    assert a_view["has_key"] is True and a_view["key_masked"].endswith("1234")
    assert b_view["has_key"] is False           # tenant B can never see tenant A's key
    # "live" describes the plane that will answer THIS caller: A's own key now drives A's own
    # engine (per-user live reasoning), and B — who has no key — sees nothing live.
    assert a_view["live"] is True
    assert b_view["live"] is False


def test_tenant_write_never_mutates_os_environ(env):
    """The core leak test: a tenant write must not touch the shared process env.

    Asserted as a DELTA, not an absolute: another test in the session may legitimately have left
    OPENAI_API_KEY set (e.g. an admin-plane ``apply_to_env``), and the invariant we care about is
    that *this* tenant write changes nothing — which must hold whatever the starting value was.
    """
    client, _ks, _cfg = env
    before = os.environ.get("OPENAI_API_KEY")
    client.post("/api/providers/openai", json={"api_key": "sk-TENANTKEY"}, headers=_tenant("aaa"))
    assert os.environ.get("OPENAI_API_KEY") == before   # unchanged → no cross-tenant leak
    assert os.environ.get("OPENAI_API_KEY") != "sk-TENANTKEY"


def test_tenant_write_lands_in_isolated_file(env):
    client, ks, cfg = env
    client.post("/api/providers/openai", json={"api_key": "sk-AAAA1234"}, headers=_tenant("aaa"))
    # "v_" marks the verbatim namespace — kept disjoint from the "h_" hashed one so the two can
    # never name the same directory (see test_safe_tenant_namespaces_cannot_collide).
    assert (cfg / "tenants" / "v_aaa" / "provider_keys.json.enc").exists()
    assert not (cfg / "tenants" / "v_bbb").exists()
    assert ks.load(tenant="bbb") == {}                 # B's store is empty
    assert "openai" in ks.load(tenant="aaa")


def test_admin_plane_uses_global_store_not_tenant(env):
    client, ks, _cfg = env
    r = client.post("/api/providers/openai", json={"api_key": "sk-GLOBAL99"}, headers=_ADMIN)
    assert r.status_code == 200
    assert "openai" in ks.load()                       # admin writes the global store
    # a tenant still sees nothing (admin's global key is not exposed to tenants)
    assert _openai_view(client.get("/api/providers", headers=_tenant("aaa")).get_json())["has_key"] is False
    # clean up any env the admin apply_to_env set, so the test leaves no residue
    os.environ.pop("OPENAI_API_KEY", None)


def test_tenant_can_live_test_own_key(env):
    client, _ks, _cfg = env
    client.post("/api/providers/openai", json={"api_key": "sk-AAAA1234"}, headers=_tenant("aaa"))
    r = client.post("/api/providers/openai/test", json={}, headers=_tenant("aaa"))
    assert r.status_code == 200
    body = r.get_json()
    assert set(body) >= {"ok", "latency_ms", "model"}   # an honest verdict, not a 500


# ── per-tenant live reasoning ────────────────────────────────────────────────────

def test_tenant_without_key_gets_honest_keyless_reply(env):
    # A signed-in user with no model of their own is answered honestly — NEVER the
    # instance's models — on both reasoning entrypoints.
    client, _ks, _cfg = env
    for path in ("/api/cognition/reason", "/api/operator/respond"):
        r = client.post(path, json={"prompt": "hello"}, headers=_tenant("nokey"))
        assert r.status_code == 200
        assert r.get_json().get("tenant_no_key") is True


def test_tenant_with_key_reasons_on_own_model(env):
    # After connecting a local model, the tenant reasons on THEIR engine (no keyless
    # fallback), and no key leaks into the process env.
    client, _ks, _cfg = env
    before = os.environ.get("OLLAMA_API_KEY")
    client.post("/api/providers/ollama",
                json={"api_key": "tok", "base_url": "http://x", "model": "llama3"},
                headers=_tenant("aaa"))
    r = client.post("/api/cognition/reason", json={"prompt": "say OK"}, headers=_tenant("aaa"))
    assert r.status_code == 200
    j = r.get_json()
    assert not j.get("tenant_no_key")                    # the tenant engine answered
    assert j.get("text")
    # delta, not absolute (see test_tenant_write_never_mutates_os_environ)
    assert os.environ.get("OLLAMA_API_KEY") == before     # no env leak from reasoning
    assert os.environ.get("OLLAMA_API_KEY") != "tok"


def test_tenant_reasoning_is_isolated(env):
    # A connects a model; B (no key) still gets the honest keyless reply — never A's engine.
    client, _ks, _cfg = env
    client.post("/api/providers/ollama", json={"api_key": "tok"}, headers=_tenant("aaa"))
    rb = client.post("/api/cognition/reason", json={"prompt": "hi"}, headers=_tenant("bbb"))
    assert rb.get_json().get("tenant_no_key") is True


def test_admin_reasoning_uses_shared_engine(env):
    # The admin/global plane reasons on the instance engine exactly as before — no
    # tenant scoping, no keyless gate.
    client, _ks, _cfg = env
    r = client.post("/api/cognition/reason", json={"prompt": "say OK"}, headers=_ADMIN)
    assert r.status_code == 200
    assert not r.get_json().get("tenant_no_key")


# ── keystore unit isolation ─────────────────────────────────────────────────────

def test_keystore_tenant_isolation_unit(tmp_path, monkeypatch):
    import aureon.operator.keystore as ks

    importlib.reload(ks)
    cfg = tmp_path / ".aureon"
    monkeypatch.setattr(ks, "CONFIG_DIR", cfg)
    monkeypatch.setattr(ks, "KEY_PATH", cfg / "provider_keys.key")
    monkeypatch.setattr(ks, "STORE_PATH", cfg / "provider_keys.json.enc")
    monkeypatch.setattr(ks, "TENANTS_DIR", cfg / "tenants")

    ks.save_provider("openai", api_key="sk-aaa", tenant="aaa")
    assert ks.load(tenant="bbb") == {}
    assert ks.load() == {}                              # global untouched by a tenant write
    assert ks.load(tenant="aaa")["openai"]["api_key"] == "sk-aaa"


def test_safe_tenant_defends_against_traversal():
    import aureon.operator.keystore as ks

    safe = ks._safe_tenant("../../etc/evil")
    assert "/" not in safe and ".." not in safe
    assert safe.startswith("h_") and len(safe) == 66     # hashed, not the raw path


def test_safe_tenant_namespaces_cannot_collide():
    """The verbatim and hashed forms must live in disjoint namespaces.

    A SHA-256 hex digest itself satisfies the verbatim whitelist. Without distinct prefixes, a tenant
    whose ``sub`` happens to be the digest of another tenant's crafted ``sub`` would be handed that
    tenant's store — reading their keys and hijacking their rotations.
    """
    import hashlib

    import aureon.operator.keystore as ks

    crafted = "../../etc/evil"
    digest = hashlib.sha256(crafted.encode("utf-8")).hexdigest()
    assert ks._safe_tenant(digest) != ks._safe_tenant(crafted)
    # and the two forms are separable by construction, for every input
    assert ks._safe_tenant(digest).startswith("v_")
    assert ks._safe_tenant(crafted).startswith("h_")


# ── backward compatibility (no secrets ⇒ open) ──────────────────────────────────

def test_open_mode_unchanged(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_LLM_OFFLINE", "1")
    monkeypatch.setenv("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
    monkeypatch.delenv("AUREON_SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.delenv("AUREON_OPERATOR_API_KEY", raising=False)

    import aureon.operator.operator_server as srv

    importlib.reload(srv)
    c = srv.create_app().test_client()
    # open: no auth needed, and a stray JWT header is simply ignored (no tenant scoping)
    assert c.get("/api/providers").status_code == 200
    assert c.get("/api/providers", headers=_tenant("aaa")).status_code == 200


# ── concurrency: a tenant's store must survive simultaneous writes ─────────────

def test_concurrent_saves_for_one_tenant_do_not_lose_writes(tmp_path, monkeypatch):
    """``save_provider`` is read-modify-write over the WHOLE store, so without a lock two concurrent
    saves race and the loser's provider is silently dropped.

    Reproduced before the fix: 24 threads saving two different providers for one tenant left exactly
    ONE provider stored. A user connecting two models at once would lose one, with no error.
    """
    import threading

    import aureon.operator.keystore as ks

    importlib.reload(ks)
    cfg = tmp_path / ".aureon"
    monkeypatch.setattr(ks, "CONFIG_DIR", cfg)
    monkeypatch.setattr(ks, "KEY_PATH", cfg / "provider_keys.key")
    monkeypatch.setattr(ks, "STORE_PATH", cfg / "provider_keys.json.enc")
    monkeypatch.setattr(ks, "TENANTS_DIR", cfg / "tenants")

    errors: list = []

    def writer(i: int) -> None:
        try:
            ks.save_provider("openai" if i % 2 else "ollama", api_key=f"key-{i}", tenant="aaa")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{type(exc).__name__}: {exc}")

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(24)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"concurrent saves raised: {errors[:3]}"
    stored = ks.load(tenant="aaa")
    assert set(stored) == {"openai", "ollama"}, f"a concurrent save was lost: kept {sorted(stored)}"


def test_a_torn_store_write_cannot_silently_empty_the_keystore(tmp_path, monkeypatch):
    """``_persist`` must be atomic. A partial Fernet token cannot be decrypted, and ``load`` reports
    an unreadable store as ``{}`` — so a torn write does not raise, it silently empties the store, and
    the next save then persists only its own entry, making the loss permanent.

    Asserts the write leaves no half-written file behind under the real store name, and that a
    temp-file crash is recoverable (the previous store is still intact).
    """
    import aureon.operator.keystore as ks

    importlib.reload(ks)
    cfg = tmp_path / ".aureon"
    monkeypatch.setattr(ks, "CONFIG_DIR", cfg)
    monkeypatch.setattr(ks, "KEY_PATH", cfg / "provider_keys.key")
    monkeypatch.setattr(ks, "STORE_PATH", cfg / "provider_keys.json.enc")
    monkeypatch.setattr(ks, "TENANTS_DIR", cfg / "tenants")

    ks.save_provider("openai", api_key="sk-first", tenant="aaa")
    path = ks._store_path("aaa")
    before = path.read_bytes()

    # A write that dies partway must not touch the live store.
    real_replace = os.replace

    def _boom(src, dst):  # noqa: ANN001
        raise OSError("simulated crash between temp write and rename")

    monkeypatch.setattr(os, "replace", _boom)
    with pytest.raises(OSError):
        ks.save_provider("ollama", api_key="sk-second", tenant="aaa")
    monkeypatch.setattr(os, "replace", real_replace)

    assert path.read_bytes() == before               # the live store is untouched
    assert ks.load(tenant="aaa")["openai"]["api_key"] == "sk-first"   # and still decrypts
    leftovers = [p.name for p in path.parent.iterdir() if p.name.endswith(".tmp")]
    assert not leftovers, f"temp files left behind: {leftovers}"
