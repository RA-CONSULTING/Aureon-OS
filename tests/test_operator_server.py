"""
Aureon Operator — production HTTP surface tests.

Endpoints (/healthz, /readyz, /metrics), config validation, and the security
envelope (bearer auth, rate limiting, error shapes). Offline, no network.
"""

from __future__ import annotations

import importlib

import pytest

pytest.importorskip("flask", reason="operator HTTP surface requires the `.[operator]` extra")

from aureon.operator.config import OperatorConfig  # noqa: E402
from aureon.operator.security import SecurityConfig, TokenBucket, check_bearer  # noqa: E402


def _client(monkeypatch=None, **env):
    """Fresh app under the given env (SecurityConfig is read at create_app time)."""
    import os

    for k, v in env.items():
        os.environ[k] = v
    try:
        import aureon.operator.operator_server as srv

        importlib.reload(srv)
        return srv.create_app().test_client()
    finally:
        for k in env:
            os.environ.pop(k, None)


# ── endpoints ─────────────────────────────────────────────────────────────────

def test_healthz_and_readyz_and_metrics():
    c = _client()
    assert c.get("/healthz").status_code == 200
    r = c.get("/readyz")
    assert r.status_code in (200, 503)
    assert set(r.get_json()["checks"]) >= {"providers", "repo_index"}
    m = c.get("/metrics")
    assert m.status_code == 200
    assert "aureon_operator" in m.get_data(as_text=True)


# ── config validation ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("kw", [
    {"temperature": 9.0}, {"max_tokens": 0}, {"request_timeout_s": 0},
    {"max_workers": 0}, {"consensus_min_agreement": 2.0},
])
def test_config_validation_rejects_bad(kw):
    with pytest.raises(ValueError):
        OperatorConfig(**kw).validate()


def test_config_validation_accepts_default():
    assert OperatorConfig().validate() is not None


# ── security primitives (unit) ──────────────────────────────────────────────

def test_check_bearer():
    assert check_bearer("Bearer k", "k") is True
    assert check_bearer("Bearer x", "k") is False
    assert check_bearer(None, "k") is False
    assert check_bearer(None, "") is True          # auth disabled when no key


def test_token_bucket_limits_and_refills():
    t = 100.0
    clock = lambda: t  # noqa: E731
    tb = TokenBucket(rate_rps=1.0, burst=1, clock=clock)
    assert tb.check("ip")[0] is True               # first token
    ok, retry = tb.check("ip")
    assert ok is False and retry > 0               # bucket empty


def test_security_config_off_by_default(monkeypatch):
    for k in ("AUREON_OPERATOR_API_KEY", "AUREON_OPERATOR_RATE_RPS"):
        monkeypatch.delenv(k, raising=False)
    s = SecurityConfig.from_env()
    assert s.auth_enabled is False and s.rate_enabled is False


# ── security envelope (integration) ─────────────────────────────────────────

def test_api_open_when_no_key():
    c = _client()
    assert c.post("/api/cognition/reason", json={"prompt": "hi"}).status_code == 200


def test_api_requires_bearer_when_key_set():
    c = _client(AUREON_LLM_OFFLINE="1", AUREON_OPERATOR_API_KEY="secret")
    assert c.post("/api/cognition/reason", json={"prompt": "hi"}).status_code == 401
    assert c.post("/api/cognition/reason", json={"prompt": "hi"},
                  headers={"Authorization": "Bearer secret"}).status_code == 200
    # probes stay open even with auth on
    assert c.get("/healthz").status_code == 200
    assert c.get("/metrics").status_code == 200


def test_api_rate_limited_returns_429():
    c = _client(AUREON_LLM_OFFLINE="1", AUREON_OPERATOR_RATE_RPS="0.5", AUREON_OPERATOR_RATE_BURST="1")
    assert c.post("/api/cognition/reason", json={"prompt": "hi"}).status_code == 200
    r = c.post("/api/cognition/reason", json={"prompt": "hi"})
    assert r.status_code == 429
    assert r.headers.get("Retry-After") is not None
    assert r.get_json()["error"]["code"] == 429


def test_missing_prompt_is_400():
    c = _client()
    assert c.post("/api/cognition/reason", json={}).status_code == 400
