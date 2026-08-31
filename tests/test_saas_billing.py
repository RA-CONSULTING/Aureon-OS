"""
Aureon SaaS — billing: REST client, token tally, metering buffer, gateway routes.

Offline: every HTTP surface is stubbed; skips when flask isn't installed.
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

from aureon.saas.metering import MeteringBuffer, UsageEvent, reset_buffer_for_tests
from aureon.saas.supabase_rest import SupabaseConfig, SupabaseRest

# ── stubs ────────────────────────────────────────────────────────────────────

class _Resp:
    def __init__(self, status_code=200, body=None, text=""):
        self.status_code = status_code
        self._body = body if body is not None else []
        self.text = text

    def json(self):
        return self._body


class _FakeSession:
    """Records calls; returns canned responses; can be told to fail."""

    def __init__(self, post_resp=None, get_resp=None, raise_exc=False):
        self.post_resp = post_resp or _Resp(201)
        self.get_resp = get_resp or _Resp(200, [])
        self.raise_exc = raise_exc
        self.posts = []
        self.gets = []

    def post(self, url, json=None, headers=None, timeout=None):
        if self.raise_exc:
            raise ConnectionError("boom")
        self.posts.append({"url": url, "json": json, "headers": headers})
        return self.post_resp

    def get(self, url, params=None, headers=None, timeout=None):
        if self.raise_exc:
            raise ConnectionError("boom")
        self.gets.append({"url": url, "params": params, "headers": headers})
        return self.get_resp


_CFG = SupabaseConfig(url="https://x.supabase.co", service_key="sk", timeout_s=1)


# ── SupabaseConfig / SupabaseRest ────────────────────────────────────────────

def test_config_from_env(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    cfg = SupabaseConfig.from_env()
    assert not cfg.ok and set(cfg.missing()) == {"SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"}
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co/")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "sk")
    cfg = SupabaseConfig.from_env()
    assert cfg.ok and cfg.url == "https://x.supabase.co" and cfg.missing() == []


def test_rest_insert_select_function_paths():
    s = _FakeSession(get_resp=_Resp(200, [{"balance": 5}]))
    rest = SupabaseRest(_CFG, session=s)
    assert rest.insert("t", [{"a": 1}]) is True
    assert s.posts[0]["url"].endswith("/rest/v1/t")
    assert s.posts[0]["headers"]["apikey"] == "sk"
    rows = rest.select("gas_tank_accounts", {"user_id": "eq.u1"}, limit=1)
    assert rows == [{"balance": 5}]
    assert s.gets[0]["params"]["user_id"] == "eq.u1"
    status, body = rest.call_function("gas-tank-deduct-fee", {"userId": "u1"})
    assert status == 201 and s.posts[1]["url"].endswith("/functions/v1/gas-tank-deduct-fee")


def test_rest_never_raises_on_transport_failure():
    rest = SupabaseRest(_CFG, session=_FakeSession(raise_exc=True))
    assert rest.insert("t", [{"a": 1}]) is False
    assert rest.select("t") is None
    status, body = rest.call_function("f", {})
    assert status == 0 and "error" in body


def test_rest_noop_when_unconfigured():
    rest = SupabaseRest(SupabaseConfig(url="", service_key=""), session=_FakeSession())
    assert rest.insert("t", [{"a": 1}]) is False
    assert rest.select("t") is None
    assert rest.call_function("f", {})[0] == 0


# ── token tally ──────────────────────────────────────────────────────────────

def test_token_tally_accumulates():
    from aureon.operator import metrics as m

    before = m.token_usage_totals().get("testprov", {"input_tokens": 0, "output_tokens": 0})
    m.record_token_usage("testprov", 10, 20)
    m.record_token_usage("testprov", 5, 0)
    m.record_token_usage("testprov", -3, 0)  # clamped, ignored
    after = m.token_usage_totals()["testprov"]
    assert after["input_tokens"] - before["input_tokens"] == 15
    assert after["output_tokens"] - before["output_tokens"] == 20


def test_call_line_records_usage():
    from aureon.operator import metrics as m
    from aureon.operator.aureon_operator import AureonOperator

    class _FakeOut:
        text = "answer"
        stop_reason = "stop"
        model = "fake-model"
        usage = {"input_tokens": 7, "output_tokens": 11}

    class _FakeAdapter:
        model = "fake-model"

        def prompt(self, messages, system=None, **kwargs):
            return _FakeOut()

    op = AureonOperator.__new__(AureonOperator)  # skip heavy __init__
    from aureon.operator.aureon_operator import _CircuitBreaker
    from aureon.operator.config import OperatorConfig

    op.config = OperatorConfig()
    op._breaker = _CircuitBreaker(threshold=3, cooldown_s=60)
    before = m.token_usage_totals().get("fakeline", {"input_tokens": 0, "output_tokens": 0})
    ans = op._call_line("fakeline", _FakeAdapter(), [{"role": "user", "content": "q"}], "sys")
    assert ans.ok
    after = m.token_usage_totals()["fakeline"]
    assert after["input_tokens"] - before["input_tokens"] == 7
    assert after["output_tokens"] - before["output_tokens"] == 11


# ── MeteringBuffer ───────────────────────────────────────────────────────────

def _event(**kw):
    return UsageEvent(kind="api_request", **kw)


def _baseline(buf):
    """Pin the token snapshot so process-wide tallies from other tests don't leak in."""
    from aureon.operator.metrics import token_usage_totals

    buf._token_snapshot = token_usage_totals()
    return buf


def test_buffer_disabled_is_noop():
    buf = MeteringBuffer(None, enabled=False)
    buf.record(_event())
    assert buf.stats()["sink"] == "disabled" and buf.stats()["pending"] == 0


def test_buffer_flush_posts_rows():
    rest = SupabaseRest(_CFG, session=_FakeSession())
    buf = _baseline(MeteringBuffer(rest, enabled=True))
    buf.record(_event(tenant_id="u1", route="/api/x", status=200))
    n = buf.flush_now()
    assert n == 1 and buf.stats()["flushed"] == 1
    row = rest._session.posts[0]["json"][0]
    assert row["tenant_id"] == "u1" and row["kind"] == "api_request" and row["status"] == 200


def test_buffer_drop_oldest_and_fail_count():
    failing = SupabaseRest(_CFG, session=_FakeSession(raise_exc=True))
    buf = _baseline(MeteringBuffer(failing, maxlen=10, enabled=True))
    for i in range(15):
        buf.record(_event(route=f"/r{i}"))
    st = buf.stats()
    assert st["pending"] == 10 and st["dropped"] == 5      # drop-oldest counted
    buf.flush_now()
    st = buf.stats()
    assert st["flush_failures"] == 1 and st["flushed"] == 0 and st["dropped"] == 15


def test_buffer_prometheus_only_sink():
    buf = _baseline(MeteringBuffer(None, enabled=True))
    buf.record(_event())
    assert buf.stats()["sink"] == "prometheus-only"
    assert buf.flush_now() == 0 and buf.stats()["dropped"] == 1


def test_token_delta_sweep():
    from aureon.operator import metrics as m

    rest = SupabaseRest(_CFG, session=_FakeSession())
    buf = _baseline(MeteringBuffer(rest, enabled=True))
    m.record_token_usage("sweepprov", 100, 50)
    buf.flush_now()
    rows = rest._session.posts[0]["json"]
    tok = [r for r in rows if r["kind"] == "llm_tokens" and r["metadata"].get("provider") == "sweepprov"]
    assert len(tok) == 1 and tok[0]["quantity"] == 150 and tok[0]["tenant_id"] is None
    # idle interval → no new event
    rest._session.posts.clear()
    buf.flush_now()
    assert not rest._session.posts


# ── gateway routes (flask) ───────────────────────────────────────────────────

pytest.importorskip("flask", reason="billing gateway requires the `.[operator]` extra")


class _StubOperator:
    providers = {}

    def respond(self, *args, **kwargs):
        raise AssertionError("billing tests should not invoke operator respond")

    def stream_events(self, *args, **kwargs):
        raise AssertionError("billing tests should not invoke operator stream")


def _app(**env):
    reset_buffer_for_tests()
    managed_env = {
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "AUREON_SUPABASE_JWT_SECRET",
        "AUREON_LLM_OFFLINE",
    } | set(env)
    previous = {k: os.environ.get(k) for k in managed_env}
    for k in managed_env:
        os.environ[k] = ""
    for k, v in env.items():
        os.environ[k] = v
    try:
        import aureon.operator.operator_server as srv

        importlib.reload(srv)
        return srv.create_app(
            operator=_StubOperator(),
            test_ingress_release=srv.TestOnlyOperatorIngressRelease(
                master_key=b"saas-billing-http-route-test-key-material",
            ),
        ).test_client()
    finally:
        for k, v in previous.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _mk_jwt(claims, secret):
    def b(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()
    h, p = b({"alg": "HS256", "typ": "JWT"}), b(claims)
    sig = base64.urlsafe_b64encode(
        hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()
    ).rstrip(b"=").decode()
    return f"{h}.{p}.{sig}"


def test_billing_status_bare():
    c = _app(AUREON_LLM_OFFLINE="1")
    s = c.get("/api/billing/status").get_json()
    assert s["configured"] is False
    assert set(s["missing_env"]) == {"SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"}
    assert s["metering"]["sink"] == "disabled"
    assert s["charge_endpoint"]["enabled"] is False


def test_billing_balance_guards():
    c = _app(AUREON_LLM_OFFLINE="1")
    assert c.get("/api/billing/balance").status_code == 503     # bridge off
    c = _app(AUREON_LLM_OFFLINE="1", AUREON_SUPABASE_JWT_SECRET="sekret")
    assert c.get("/api/billing/balance").status_code == 401     # bridge on, no token
    good = _mk_jwt({"sub": "u1", "exp": time.time() + 3600}, "sekret")
    r = c.get("/api/billing/balance", headers={"Authorization": f"Bearer {good}"})
    assert r.status_code == 503                                  # authed but no Supabase env
    assert "missing" in r.get_json()["error"]


def test_charge_fee_disabled_by_default():
    c = _app(AUREON_LLM_OFFLINE="1")
    r = c.post("/api/billing/charge-fee", json={"user_id": "u1", "profit": 10})
    assert r.status_code == 403
    assert "disabled" in r.get_json()["error"]["message"]


def test_charge_fee_validates_input():
    c = _app(AUREON_LLM_OFFLINE="1", AUREON_BILLING_CHARGE_ENABLED="1",
             SUPABASE_URL="https://x.supabase.co", SUPABASE_SERVICE_ROLE_KEY="sk")
    r = c.post("/api/billing/charge-fee", json={"user_id": "u1", "profit": -5})
    assert r.status_code == 400
    r = c.post("/api/billing/charge-fee", json={"profit": 5})
    assert r.status_code == 400


def test_metering_hook_records_and_attributes(monkeypatch):
    c = _app(AUREON_LLM_OFFLINE="1", AUREON_BILLING_METERING="1",
             AUREON_SUPABASE_JWT_SECRET="sekret")
    from aureon.saas.metering import get_buffer

    buf = get_buffer()
    with buf._lock:
        buf._events.clear()
    good = _mk_jwt({"sub": "u9", "exp": time.time() + 3600}, "sekret")
    c.get("/api/domains", headers={"Authorization": f"Bearer {good}"})
    c.get("/healthz")                                            # open path — not metered
    with buf._lock:
        events = list(buf._events)
    api_events = [e for e in events if e.kind == "api_request"]
    assert len(api_events) == 1
    assert api_events[0].tenant_id == "u9"
    assert api_events[0].route == "/api/domains"


def test_metering_hook_none_tenant_without_jwt():
    c = _app(AUREON_LLM_OFFLINE="1", AUREON_BILLING_METERING="1")
    from aureon.saas.metering import get_buffer

    buf = get_buffer()
    with buf._lock:
        buf._events.clear()
    c.get("/api/status")
    with buf._lock:
        events = [e for e in buf._events if e.kind == "api_request"]
    assert len(events) == 1 and events[0].tenant_id is None
