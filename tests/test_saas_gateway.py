"""
Aureon SaaS — gateway HTTP routes + Supabase JWT bridge.

Offline; skips when flask isn't installed (CI installs the operator extra).
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

pytest.importorskip("flask", reason="SaaS gateway requires the `.[operator]` extra")

from aureon.saas.gateway import verify_supabase_jwt  # noqa: E402


def _app(**env):
    for k, v in env.items():
        os.environ[k] = v
    try:
        import aureon.operator.operator_server as srv

        importlib.reload(srv)
        return srv.create_app().test_client()
    finally:
        for k in env:
            os.environ.pop(k, None)


def _mk_jwt(claims, secret):
    def b(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()
    h, p = b({"alg": "HS256", "typ": "JWT"}), b(claims)
    sig = base64.urlsafe_b64encode(
        hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()
    ).rstrip(b"=").decode()
    return f"{h}.{p}.{sig}"


# ── routes ────────────────────────────────────────────────────────────────────

def test_catalog_route():
    c = _app(AUREON_LLM_OFFLINE="1")
    r = c.get("/api/catalog")
    assert r.status_code == 200
    assert len(r.get_json()["categories"]) == 12


def test_domains_routes():
    c = _app(AUREON_LLM_OFFLINE="1")
    d = c.get("/api/domains").get_json()
    assert len(d["product_domains"]) == 6 and len(d["domains"]) >= 24
    one = c.get("/api/domains/trading").get_json()
    assert one["domain"] == "trading" and one["system_count"] >= 0


def test_status_route():
    c = _app(AUREON_LLM_OFFLINE="1")
    s = c.get("/api/status").get_json()
    assert s["status"] in {"healthy", "degraded", "critical"}


def test_mount_route_is_saas_active():
    c = _app(AUREON_LLM_OFFLINE="1")
    r = c.get("/api/mount")
    assert r.status_code == 200
    b = r.get_json()
    assert b["service"] == "aureon-mount"
    assert {e["id"] for e in b["engines"]} == {"aureon-cognition", "aureon-switchboard"}
    assert {m["id"] for m in b["models"]} == {"aureon-cognition", "aureon-switchboard"}
    assert "provenance_keys" in b and b["endpoint"] == "POST /v1/chat/completions"
    # carries the SaaS provenance stamp like every other /api read
    assert b["truth_status"] == "real_derived" and "provenance" in b


def test_manifests_refresh_route(tmp_path, monkeypatch):
    c = _app(AUREON_LLM_OFFLINE="1")
    r = c.post("/api/manifests/refresh").get_json()
    assert r["refreshed"] is True
    assert set(r["manifests"]) == {"aureon_saas_system_inventory.json", "aureon_organism_runtime_status.json"}


def test_manifest_get_route():
    c = _app(AUREON_LLM_OFFLINE="1")
    inv = c.get("/api/manifests/aureon_saas_system_inventory.json")
    assert inv.status_code == 200
    assert inv.get_json()["summary"]["surface_count"] > 0
    runtime = c.get("/api/manifests/aureon_organism_runtime_status.json").get_json()
    assert runtime["mode"] == "live" and len(runtime["domains"]) == 6
    missing = c.get("/api/manifests/nope.json")
    assert missing.status_code == 404
    assert "available" in missing.get_json()["error"]


# ── Supabase JWT bridge ────────────────────────────────────────────────────

def test_verify_supabase_jwt_unit():
    good = _mk_jwt({"sub": "u1", "exp": time.time() + 3600}, "sekret")
    assert verify_supabase_jwt(good, "sekret")["sub"] == "u1"
    assert verify_supabase_jwt(good, "wrong") is None                       # bad sig
    assert verify_supabase_jwt(_mk_jwt({"sub": "u", "exp": time.time() - 5}, "sekret"), "sekret") is None  # expired
    assert verify_supabase_jwt("not.a.jwt", "sekret") is None


def test_jwt_bridge_gates_when_secret_set():
    c = _app(AUREON_LLM_OFFLINE="1", AUREON_SUPABASE_JWT_SECRET="sekret")
    assert c.get("/api/catalog").status_code == 401                          # no token
    good = _mk_jwt({"sub": "u", "exp": time.time() + 3600}, "sekret")
    assert c.get("/api/catalog", headers={"Authorization": f"Bearer {good}"}).status_code == 200
