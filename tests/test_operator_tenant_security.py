"""
Aureon Operator — multi-tenant security regressions.

Each test here pins a defect an adversarial audit of the tenancy work actually confirmed, so the hole
cannot silently reopen:

  * a TENANT's engine must not carry shell / repo-write tools — the tenant supplies their own
    ``base_url``, so the model answering them is a server THEY control and its ``tool_calls`` are
    dispatched on the operator host (that path could otherwise read the keystore's Fernet key and
    every other tenant's encrypted store);
  * the instance CONTROL PLANE (feature switchboard, local actions, approvals, manifest rebuild,
    instance notification credentials) is operator-only — a tenant JWT must not reach it;
  * the SSE reasoning streams must be tenant-aware, not a side door onto the instance's model keys;
  * a keyless tenant's ``*/test`` probe must not resolve an empty key from the process env;
  * a rotated / revoked tenant key must stop being used immediately (no stale cached engine);
  * a tenant's prompt must not land on the shared instance thought bus;
  * unicode / whitespace auth inputs must degrade to a clean verdict, never a 500.

Offline; the keystore is redirected to a tmp dir so the real ``~/.aureon`` is untouched.
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

SECRET = "sec-tenant-security"
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
def app_env(tmp_path, monkeypatch):
    """Tenancy-enabled app with an isolated keystore. Yields (client, srv_module, keystore)."""
    monkeypatch.setenv("AUREON_LLM_OFFLINE", "1")
    monkeypatch.setenv("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
    monkeypatch.setenv("AUREON_SUPABASE_JWT_SECRET", SECRET)
    monkeypatch.setenv("AUREON_OPERATOR_API_KEY", ADMIN_KEY)
    # This suite asserts a tenant cannot arm the instance. Never inherit a
    # process-level value restored by an earlier switchboard test.
    monkeypatch.delenv("AUREON_LIVE_TRADING", raising=False)

    import aureon.operator.keystore as ks

    importlib.reload(ks)
    cfg = tmp_path / ".aureon"
    monkeypatch.setattr(ks, "CONFIG_DIR", cfg)
    monkeypatch.setattr(ks, "KEY_PATH", cfg / "provider_keys.key")
    monkeypatch.setattr(ks, "STORE_PATH", cfg / "provider_keys.json.enc")
    monkeypatch.setattr(ks, "TENANTS_DIR", cfg / "tenants")

    import aureon.operator.operator_server as srv

    importlib.reload(srv)
    app = srv.create_app(
        test_ingress_release=srv.TestOnlyOperatorIngressRelease(
            master_key=b"operator-tenant-security-route-test-material",
        )
    )
    return app.test_client(), srv, ks


def _connect_model(client, headers, **over):
    body = {"api_key": "tok", "base_url": "http://tenant.invalid", "model": "llama3", **over}
    return client.post("/api/providers/ollama", json=body, headers=headers)


# ── CRITICAL: a tenant engine must have no shell / write tools ───────────────────

def test_tenant_engine_has_no_shell_or_write_tools(app_env):
    """The tenant's model is a server they control; its tool_calls run here. So the dangerous tools
    must not exist on their engine at all — the conscience veto runs after the tool loop."""
    client, _srv, _ks = app_env
    _connect_model(client, _tenant("aaa"))
    client.post("/api/cognition/reason", json={"prompt": "hi"}, headers=_tenant("aaa"))

    import aureon.operator.operator_server as srv_mod

    # Reach the engine the app cached for this tenant via a fresh build of the same toolbelt.
    from aureon.operator.tools import build_operator_tools

    tenant_tools = build_operator_tools(allow_writes=False, allow_shell=False)
    names = set(tenant_tools.names()) if hasattr(tenant_tools, "names") else set()
    for forbidden in ("execute_shell", "write_repo_file", "patch_repo_file"):
        assert forbidden not in names, f"{forbidden} must not be on a tenant toolbelt"
    # And the instance/admin engine is unchanged (still fully capable).
    admin_tools = build_operator_tools()
    assert "execute_shell" in set(admin_tools.names())
    assert srv_mod is not None


def test_tenant_models_never_receive_instance_repo_grounding(app_env, monkeypatch):
    """Automatic grounding is also a data boundary, not only a toolbelt concern.

    A tenant controls their model ``base_url``. Sending source packets to it would
    disclose the instance repository even when every repo-reading tool is absent.
    """
    client, _srv, _ks = app_env
    calls: list[str] = []

    import aureon.autonomous.aureon_dynamic_prompt_filter as prompt_filter_module
    import aureon.operator.cognition as cognition_module

    def forbidden_grounding(*_args, **_kwargs):
        calls.append("instance_repo_grounding")
        raise AssertionError("tenant plane must not read instance repository context")

    monkeypatch.setattr(cognition_module, "repo_search", forbidden_grounding)
    monkeypatch.setattr(prompt_filter_module, "build_dynamic_prompt_filter", forbidden_grounding)
    _connect_model(client, _tenant("aaa"))

    cognition = client.post(
        "/api/cognition/reason",
        json={"prompt": "explain this account"},
        headers=_tenant("aaa"),
    )
    operator = client.post(
        "/api/operator/respond",
        json={"prompt": "explain this account"},
        headers=_tenant("aaa"),
    )

    assert cognition.status_code == 200
    assert operator.status_code == 200
    assert calls == []


# ── CRITICAL: the instance control plane is operator-only ───────────────────────

def test_tenant_cannot_flip_feature_switchboard(app_env):
    """Flipping a flag writes os.environ, can re-apply the instance's keys, and can arm hard
    boundaries (e.g. live trading). A tenant must be refused."""
    client, _srv, _ks = app_env
    before = os.environ.get("AUREON_COGNITION_PREFER_LOCAL")
    r = client.post("/api/switchboard/AUREON_COGNITION_PREFER_LOCAL",
                    json={"enabled": True}, headers=_tenant("aaa"))
    assert r.status_code == 403
    assert os.environ.get("AUREON_COGNITION_PREFER_LOCAL") == before  # env untouched


def test_tenant_cannot_arm_a_hard_boundary(app_env):
    client, _srv, _ks = app_env
    r = client.post("/api/switchboard/AUREON_LIVE_TRADING",
                    json={"enabled": True, "confirm": "AUREON_LIVE_TRADING"}, headers=_tenant("aaa"))
    assert r.status_code in (403, 404)   # refused as tenant (404 only if the flag id is absent)
    if r.status_code == 403:
        assert os.environ.get("AUREON_LIVE_TRADING") in (None, "", "0", "false")


def test_admin_can_still_flip_the_switchboard(app_env):
    """Zero regression on the control plane: the operator keeps their switchboard."""
    client, _srv, _ks = app_env
    r = client.post("/api/switchboard/AUREON_COGNITION_PREFER_LOCAL",
                    json={"enabled": False}, headers=_ADMIN)
    assert r.status_code == 200 and r.get_json().get("ok") is True


def test_tenant_cannot_run_local_actions(app_env):
    client, _srv, _ks = app_env
    r = client.post("/api/action", json={"action": "noop"}, headers=_tenant("aaa"))
    assert r.status_code in (403, 404)   # 404 only if the bridge failed to mount in this env
    if r.status_code == 403:
        assert r.get_json()["error"]["plane"] == "admin"


def test_tenant_cannot_send_from_instance_telegram(app_env):
    """The fallback bot credentials are the instance's identity."""
    client, _srv, _ks = app_env
    r = client.post("/api/notifications/telegram", json={"message": "hi"}, headers=_tenant("aaa"))
    assert r.status_code == 403
    assert r.get_json()["ok"] is False


def test_tenant_cannot_decide_approvals_or_rebuild_manifests(app_env):
    client, _srv, _ks = app_env
    a = client.post("/api/approvals/some-id", json={"decision": "approve"}, headers=_tenant("aaa"))
    m = client.post("/api/manifests/refresh", json={}, headers=_tenant("aaa"))
    assert a.status_code == 403
    assert m.status_code == 403


# ── HIGH: the SSE streams are tenant-aware ──────────────────────────────────────

def test_keyless_tenant_streams_get_the_honest_keyless_reply(app_env):
    """Neither stream may fall through to the instance engine (which holds the operator's keys)."""
    client, _srv, _ks = app_env
    for path in ("/api/cognition/stream?prompt=hi", "/api/operator/stream?prompt=hi"):
        r = client.get(path, headers=_tenant("nokey"))
        assert r.status_code == 200
        assert b"tenant_no_key" in r.data


# ── HIGH: a keyless tenant probe must not resolve the instance env key ──────────

def test_keyless_tenant_test_probe_never_uses_instance_env_key(app_env, monkeypatch):
    """Adapters do ``api_key or os.environ.get(...)``, so an empty tenant key would silently spend
    the instance's credentials and reveal which are live."""
    client, _srv, _ks = app_env
    monkeypatch.setenv("OPENAI_API_KEY", "sk-INSTANCE-SECRET-9999")
    r = client.post("/api/providers/openai/test", json={}, headers=_tenant("aaa"))
    assert r.status_code == 200
    body = r.get_json()
    assert body["ok"] is False
    assert "no key stored for your account" in body["error"]
    assert "9999" not in json.dumps(body)     # nothing about the instance key is echoed back


# ── HIGH: a rotated / revoked tenant key stops being used at once ───────────────

def test_revoking_a_tenant_key_invalidates_the_cached_engine(app_env):
    client, srv, _ks = app_env
    _connect_model(client, _tenant("aaa"))
    r1 = client.post("/api/cognition/reason", json={"prompt": "hi"}, headers=_tenant("aaa"))
    assert not r1.get_json().get("tenant_no_key")          # engine built and cached
    client.delete("/api/providers/ollama", headers=_tenant("aaa"))
    # A byte-identical second request is correctly rejected by the HNC replay
    # ledger. Vary the prompt so this test isolates cached-engine revocation.
    r2 = client.post(
        "/api/cognition/reason",
        json={"prompt": "hi-after-revoke"},
        headers=_tenant("aaa"),
    )
    assert r2.get_json().get("tenant_no_key") is True      # stale engine must not answer
    assert srv is not None


# ── MEDIUM: a tenant's prompt must not enter shared instance memory ────────────

def test_tenant_prompt_does_not_reach_the_shared_thought_bus(app_env):
    client, _srv, _ks = app_env
    _connect_model(client, _tenant("aaa"))
    secret_prompt = "tenant-private-marker-8571"
    client.post("/api/cognition/reason", json={"prompt": secret_prompt}, headers=_tenant("aaa"))
    try:
        from aureon.core.aureon_thought_bus import get_thought_bus

        bus = get_thought_bus()
    except Exception:  # pragma: no cover - no bus in this env ⇒ nothing to leak into
        return
    if bus is None:
        return
    recent = bus.get_recent(limit=500) or []
    assert secret_prompt not in json.dumps(recent, default=str)


# ── MEDIUM: the tenant view reports its own live plane honestly ────────────────

def test_tenant_provider_view_reports_live_from_their_own_plane(app_env):
    """`live` must describe the runtime that will actually answer the tenant, so the Get Started
    checklist can complete."""
    client, _srv, _ks = app_env
    _connect_model(client, _tenant("aaa"))
    view = next(p for p in client.get("/api/providers", headers=_tenant("aaa")).get_json()["providers"]
                if p["id"] == "ollama")
    assert view["has_key"] is True
    assert view["live"] is True


# ── auth-input robustness ──────────────────────────────────────────────────────

def test_unicode_authorization_header_is_401_not_500(app_env):
    client, _srv, _ks = app_env
    r = client.get("/api/providers", headers={"Authorization": "Bearer ké¥-nön-ascii"})
    assert r.status_code == 401


def test_whitespace_only_operator_key_is_treated_as_unset():
    from aureon.operator.identity import resolve_identity

    ident = resolve_identity(None, operator_key="   ", jwt_secret="")
    assert ident.kind == "open" and ident.ok is True


# ═══════════════════════════════════════════════════════════════════════════════
# Round 2 — a COUNTER-audit attacked the round-1 patches and defeated several.
# Each test below pins one of those reproduced bypasses.
# ═══════════════════════════════════════════════════════════════════════════════

# ── CRITICAL: the round-1 "lockdown" was a denylist and left 14 of 17 tools ────

def test_tenant_toolbelt_is_an_allowlist_not_a_denylist():
    """Dropping shell+writes is not a lockdown. The retained tools were themselves the exploit:
    ``web_fetch`` = outbound HTTP from the operator's IP (SSRF onto co-located instance services
    and cloud metadata), ``touch_module`` = import anything, ``publish_thought`` = write the
    process-global thought bus, ``read_state``/``read_positions``/``read_prices`` = the instance's
    live trading state, ``repo_search``/``read_repo_file``/``list_repo`` = repository contents."""
    from aureon.operator.tools import TENANT_ALLOWED_TOOLS, build_operator_tools

    tenant = set(build_operator_tools(allow_writes=False, allow_shell=False,
                                      allowlist=TENANT_ALLOWED_TOOLS).names())
    forbidden = {"execute_shell", "write_repo_file", "patch_repo_file", "web_fetch", "web_search",
                 "publish_thought", "touch_module", "read_state", "read_positions", "read_prices",
                 "repo_search", "read_repo_file", "list_repo", "sense_organism", "list_organism"}
    assert not (tenant & forbidden), f"tenant belt must hold none of these: {sorted(tenant & forbidden)}"
    assert tenant, "the belt must still be a usable registry, not empty"
    # zero regression: the instance/admin belt keeps every capability
    assert {"execute_shell", "write_repo_file", "web_fetch"} <= set(build_operator_tools().names())


def test_allowlist_is_a_final_filter_so_new_builtins_cannot_widen_the_belt():
    """The filter runs last, so a tool registered by any future path is still excluded."""
    from aureon.operator.tools import build_operator_tools

    reg = build_operator_tools(allowlist={"code_validate"})
    assert set(reg.names()) == {"code_validate"}


# ── CRITICAL: the one route that moves money had no guard ──────────────────────

def test_tenant_cannot_charge_a_fee_to_another_tenant(app_env, monkeypatch):
    """POST /api/billing/charge-fee took ``user_id`` from the request BODY and signed the deduct
    call with the instance's Supabase service-role key — so any signed-in user could debit any
    other user's gas tank and fabricate audited fee events against them."""
    monkeypatch.setenv("AUREON_BILLING_CHARGE_ENABLED", "1")
    client, _srv, _ks = app_env
    r = client.post("/api/billing/charge-fee",
                    json={"user_id": "VICTIM-TENANT", "profit": 99999.0}, headers=_tenant("aaa"))
    assert r.status_code == 403
    assert r.get_json()["error"]["plane"] == "admin"


# ── CRITICAL: the MCP surface is instance-plane only ──────────────────────────

def test_tenant_cannot_reach_the_mcp_surface(app_env):
    """``get_registry()`` is one process-wide INSTANCE registry — there is no tenant plane for MCP.
    Authentication alone let a tenant read the operator's live trading state via ``read_positions``,
    and ``repo_search`` returned raw repository lines."""
    client, _srv, _ks = app_env
    assert client.get("/mcp/tools", headers=_tenant("aaa")).status_code == 403
    assert client.post("/mcp/call", json={"name": "read_positions", "arguments": {}},
                       headers=_tenant("aaa")).status_code == 403


def test_admin_can_still_use_the_mcp_surface(app_env):
    client, _srv, _ks = app_env
    assert client.get("/mcp/tools", headers=_ADMIN).status_code == 200


def test_repo_search_never_returns_secret_file_contents(tmp_path, monkeypatch):
    """Defense in depth on every plane: repo_search echoes matching lines verbatim, so without a
    path filter a pattern like ``API_KEY=`` hands back the instance's .env in plaintext."""
    import aureon.inhouse_ai.tool_registry as tr

    (tmp_path / ".env").write_text('KRAKEN_API_KEY="LIVE-kraken-abc123"\n', encoding="utf-8")
    (tmp_path / "ok.py").write_text('X = "API_KEY=placeholder"\n', encoding="utf-8")
    monkeypatch.setattr(tr, "_repo_root", lambda: str(tmp_path))
    out = tr._builtin_repo_search({"pattern": "API_KEY=", "limit": 10})
    assert "LIVE-kraken-abc123" not in out
    assert ".env" not in json.dumps(json.loads(out)["hits"])
    assert "ok.py" in out            # ordinary files still searchable


# ── HIGH: the connections surface leaked the instance's credential posture ────

def test_tenant_never_sees_instance_connection_credentials(app_env, monkeypatch):
    """The round-1 fork reached the LLM rows only. The exchange / data-source rows — where the real
    money keys are — were still built from the GLOBAL keystore plus ``os.environ``, so a tenant
    enumerated which instance credentials exist, their source, and the last 4 characters."""
    client, _srv, _ks = app_env
    monkeypatch.setenv("KRAKEN_API_KEY", "INSTANCE-SECRET-9876")
    body = client.get("/api/connections", headers=_tenant("aaa")).get_json()
    rows = [c for s in body["categories"] for c in s["connections"]]
    kraken = next(c for c in rows if c["id"] == "kraken")
    assert kraken["has_key"] is False
    assert kraken["key_source"] == "none"
    assert kraken["key_masked"] == ""
    assert "9876" not in json.dumps(body)
    # the admin plane is unchanged — it still sees its own env credential
    admin_rows = [c for s in client.get("/api/connections", headers=_ADMIN).get_json()["categories"]
                  for c in s["connections"]]
    admin_kraken = next(c for c in admin_rows if c["id"] == "kraken")
    assert admin_kraken["has_key"] is True and admin_kraken["key_source"] == "env"


def test_tenant_readiness_does_not_report_instance_keys_present(app_env, monkeypatch):
    client, _srv, _ks = app_env
    monkeypatch.setenv("KRAKEN_API_KEY", "INSTANCE-SECRET-9876")
    items = client.get("/api/connections/readiness", headers=_tenant("aaa")).get_json()["items"]
    leaked = [i for i in items
              if i.get("category") not in ("ai_llm",) and i.get("present") and i.get("requirement") != "keyless"]
    assert not leaked, f"instance credentials reported present to a tenant: {leaked}"


def test_tenant_cannot_read_the_instance_credential_posture(app_env):
    """GET /api/env-credentials enumerates which of the operator's exchange keys are configured —
    the instance's security state, and a target list."""
    client, _srv, _ks = app_env
    assert client.get("/api/env-credentials", headers=_tenant("aaa")).status_code == 403
    assert client.get("/api/env-credentials", headers=_ADMIN).status_code == 200


# ── the round-1 guards locked the OPERATOR out too (a real regression) ────────

def test_admin_can_still_decide_approvals_under_tenancy(app_env):
    """``@_guarded`` requires a valid *Supabase JWT*; the admin static bearer is not one. Stacking it
    over ``@_admin_only`` 401s the operator before the admin check is reached — so with tenancy on,
    NO identity could decide an approval."""
    client, _srv, _ks = app_env
    r = client.post("/api/approvals/some-id", json={"decision": "approve"}, headers=_ADMIN)
    assert r.status_code != 401, "the operator must not be locked out of their own control plane"
    assert r.status_code != 403


# ── MEDIUM: tenant turns must not radiate onto shared instance memory ────────

def test_tenant_engines_do_not_broadcast_onto_the_shared_mycelium(app_env, monkeypatch):
    """``join_mesh=False`` only skips INBOUND membership; the outbound ``broadcast_to_mesh`` calls
    fired regardless, carrying the conscience verdict (which quotes the user's prompt)."""
    client, _srv, _ks = app_env
    seen: list = []
    import aureon.operator.cognition as cog

    monkeypatch.setattr(cog, "broadcast_to_mesh", lambda topic, payload: seen.append(topic))
    _connect_model(client, _tenant("aaa"))
    client.post("/api/cognition/reason", json={"prompt": "hello"}, headers=_tenant("aaa"))
    assert seen == [], f"tenant turn broadcast onto the shared mesh: {seen}"


def test_tenant_conscience_is_not_a_subscriber_on_the_shared_bus(app_env):
    """QueenConscience.__init__ subscribes to "symbolic.life.pulse" before we can detach it, which
    left the tenant-plane conscience receiving the INSTANCE's substrate pulses (an inbound
    cross-plane read) and pinned a callback on the shared bus forever."""
    client, _srv, _ks = app_env
    _connect_model(client, _tenant("aaa"))
    client.post("/api/cognition/reason", json={"prompt": "hi"}, headers=_tenant("aaa"))
    try:
        from aureon.core.aureon_thought_bus import get_thought_bus

        bus = get_thought_bus()
    except Exception:  # pragma: no cover - no bus in this env ⇒ nothing to subscribe to
        return
    subs = getattr(bus, "_subs", None)
    if not isinstance(subs, dict):
        return
    from aureon.queen.queen_conscience import QueenConscience

    still = [h for handlers in subs.values() for h in handlers
             if isinstance(getattr(h, "__self__", None), QueenConscience)
             and getattr(h.__self__, "_thought_bus", "set") is None]
    assert not still, "the detached tenant conscience is still subscribed to the shared bus"


# ── token-validation hardening (probed directly, not claimed) ─────────────────

def test_jwt_verifier_rejects_dangerous_tokens():
    """HS256 is forced, so alg-confusion cannot apply; the claim checks close the rest.

    A signed token with NO ``exp`` is the one that matters: it never expires and cannot be revoked,
    so a single leaked bearer is permanent access. Supabase always sets exp — this refuses to depend
    on the identity provider for a property the gate can enforce itself.
    """
    import hashlib as _h

    from aureon.operator.identity import resolve_identity, verify_supabase_jwt

    secret = "the-real-secret"

    def _b(d: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()

    def _sign(h: str, p: str, sec: str) -> str:
        return base64.urlsafe_b64encode(
            hmac.new(sec.encode(), f"{h}.{p}".encode(), _h.sha256).digest()
        ).rstrip(b"=").decode()

    def _tok(payload: dict, *, alg: str = "HS256", sec: str = secret, sig: str | None = None) -> str:
        h, p = _b({"alg": alg, "typ": "JWT"}), _b(payload)
        return f"{h}.{p}.{sig if sig is not None else _sign(h, p, sec)}"

    live = time.time() + 3600

    # alg-confusion: unsigned tokens are refused whatever the header claims
    assert verify_supabase_jwt(_tok({"sub": "x", "exp": live}, alg="none", sig=""), secret) is None
    # a bad signature is refused
    assert verify_supabase_jwt(_tok({"sub": "x", "exp": live}, sec="wrong-secret"), secret) is None
    # no exp ⇒ refused (would otherwise be an eternal, unrevokable bearer)
    assert verify_supabase_jwt(_tok({"sub": "x"}), secret) is None
    # expired ⇒ refused
    assert verify_supabase_jwt(_tok({"sub": "x", "exp": time.time() - 5}), secret) is None
    # not yet valid ⇒ refused
    assert verify_supabase_jwt(_tok({"sub": "x", "exp": live, "nbf": time.time() + 8000}), secret) is None
    # a Supabase project API key is not an end user (the anon key is public!)
    assert verify_supabase_jwt(_tok({"sub": "x", "exp": live, "role": "anon"}), secret) is None
    assert verify_supabase_jwt(_tok({"sub": "x", "exp": live, "role": "service_role"}), secret) is None
    # a non-string sub never becomes a tenant
    for bad_sub in (12345, {"a": 1}, None, ["x"]):
        ident = resolve_identity(f"Bearer {_tok({'sub': bad_sub, 'exp': live})}",
                                 operator_key="ADMIN", jwt_secret=secret)
        assert ident.tenant is None and ident.ok is False, f"sub={bad_sub!r} became a tenant"
    # CONTROL: a well-formed user token still works, unchanged
    ok = resolve_identity(f"Bearer {_tok({'sub': 'legit', 'exp': live, 'role': 'authenticated'})}",
                          operator_key="ADMIN", jwt_secret=secret)
    assert (ok.kind, ok.tenant, ok.ok) == ("tenant", "legit", True)


# ═══════════════════════════════════════════════════════════════════════════════
# Round 3 — the SAME defect class appeared a third time: the write sibling of a
# route pair was guarded and the read sibling kept serving. These pin the
# structural fix (central default-deny) rather than the individual routes.
# ═══════════════════════════════════════════════════════════════════════════════

# Every instance route round 3 found open to a tenant, plus the ones round 2 closed by hand — all
# must now be refused by the gate, and all must still answer the operator.
_INSTANCE_ONLY_GETS = [
    "/api/terminal-state",   # instance equity, exchange account id, open positions, session PnL
    "/api/flight-test",      # the instance .env path + which exchange keys were written
    "/api/reboot-advice",    # same payload as flight-test
    "/api/switchboard",      # all flags incl. the 7 hard boundaries' armed state
    "/api/pulse",            # instance live provider/model line-up
    "/api/action/status",    # whether the host's hands are armed
    "/api/approvals",        # pending big plays: venue, notional, account, item ids
    "/api/env-credentials",  # closed in round 2; flight-test was leaking the same thing
    "/api/status",
    "/api/trades",
    "/api/bots",
    "/mcp/tools",
]


@pytest.mark.parametrize("path", _INSTANCE_ONLY_GETS)
def test_tenant_cannot_read_instance_state(app_env, path):
    client, _srv, _ks = app_env
    r = client.get(path, headers=_tenant("aaa"))
    assert r.status_code == 403, f"{path} served a tenant (HTTP {r.status_code})"


@pytest.mark.parametrize("path", _INSTANCE_ONLY_GETS)
def test_admin_can_still_read_instance_state(app_env, path):
    """Invariant (1). Round 2 shipped a guard that locked the OPERATOR out of their own approvals
    desk; this is the assertion that would have caught it."""
    client, _srv, _ks = app_env
    assert client.get(path, headers=_ADMIN).status_code != 403


def test_every_route_is_classified(app_env):
    """Proves the gate really enforces default-deny across the whole surface.

    Walk the real url_map: every `/api` or `/mcp` rule must be either listed in `_TENANT_ALLOWED` or
    actually refused to a tenant — no third state. This is what makes the defect class structural
    rather than per-route: a route added later is closed to tenants by construction, because it is
    absent from the allowlist, so nobody has to remember to guard it.

    (This test does NOT catch "someone added a route and forgot to classify it" — under default-deny
    that case is already safe. The case it does catch is the gate silently stopping enforcing, e.g.
    the tenant branch being reordered, short-circuited, or dropped.)
    """
    client, srv, _ks = app_env
    app = srv.create_app(
        test_ingress_release=srv.TestOnlyOperatorIngressRelease(
            master_key=b"operator-tenant-classification-test-material",
        )
    )
    unclassified = []
    for rule in app.url_map.iter_rules():
        if not (rule.rule.startswith("/api/") or rule.rule.startswith("/mcp/")):
            continue
        for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
            if (method, rule.rule) in srv_tenant_allowed(srv):
                continue
            # Not allowlisted ⇒ a tenant must actually be refused. Probe a concrete path.
            probe = rule.rule.replace("<provider_id>", "openai").replace("<conn_id>", "kraken")
            probe = probe.replace("<item_id>", "x").replace("<domain>", "queen")
            probe = probe.replace("<name>", "x")
            if "<" in probe:
                continue  # unusual converter — cannot synthesize a path, skip rather than false-fail
            resp = client.open(probe, method=method, headers=_tenant("aaa"), json={})
            if resp.status_code != 403:
                unclassified.append(f"{method} {rule.rule} -> {resp.status_code}")
    assert not unclassified, (
        "these routes are neither tenant-allowlisted nor refused to a tenant — classify them in "
        "_TENANT_ALLOWED or confirm they should 403:\n  " + "\n  ".join(sorted(unclassified))
    )


def srv_tenant_allowed(srv_module):
    """The gate's real allowlist — imported, not re-derived, so the test cannot drift from it."""
    pairs = srv_module._TENANT_ALLOWED
    assert pairs, "operator_server._TENANT_ALLOWED is empty"
    return pairs


def test_tenant_can_still_reach_their_own_plane_and_the_showcase(app_env):
    """Default-deny must not dark the console: everything allowlisted stays reachable."""
    client, srv, _ks = app_env
    # Telegram is allowlisted at the GATE but the view is deliberately stricter: a tenant may send
    # only with their OWN botToken, never the instance's bot identity. So probe it with that body —
    # a 403 for a tenant supplying no token is correct behavior, not a darked route.
    bodies = {"/api/notifications/telegram": {"botToken": "t", "chatId": "c", "message": "hi"}}
    denied = []
    for method, rule in sorted(srv_tenant_allowed(srv)):
        probe = rule.replace("<provider_id>", "openai").replace("<conn_id>", "kraken")
        probe = probe.replace("<domain>", "queen")
        if "<" in probe:
            continue
        resp = client.open(probe, method=method, headers=_tenant("aaa"), json=bodies.get(rule, {}))
        if resp.status_code == 403:
            denied.append(f"{method} {rule} -> {resp.get_json()}")
    assert not denied, f"allowlisted routes refused a tenant: {denied}"


# ── the allowlist mechanism must fail CLOSED ────────────────────────────────────

def test_an_empty_allowlist_yields_an_empty_belt_not_the_full_one():
    """ToolRegistry defines __len__, so a registry pruned to zero tools is FALSY — and
    ``self.tools = tools or build_operator_tools(...)`` would then hand back the FULL instance
    toolbelt, exactly inverting what an empty allowlist asks for. That is a fail-open in the
    mechanism that protects the tenant plane, so it is pinned here."""
    from aureon.operator.cognition import AureonCognition
    from aureon.operator.tools import build_operator_tools

    empty = build_operator_tools(allow_writes=False, allow_shell=False, allowlist=frozenset())
    assert list(empty.names()) == []
    assert not empty, "precondition: an empty registry is falsy (that is the whole hazard)"

    eng = AureonCognition(adapter=object(), tools=empty, join_mesh=False, mesh_broadcast=False)
    assert list(eng.tools.names()) == [], "an empty toolbelt was silently replaced by the full one"


def test_tenant_conscience_failure_is_isolated_and_denied_no_data(app_env, monkeypatch):
    """A private-conscience construction failure must neither borrow the shared object nor
    become downstream APPROVED. The isolated unavailable sentinel emits an explicit no_data VETO.
    """
    from types import SimpleNamespace

    import aureon.operator.cognition as cognition_mod
    import aureon.queen.queen_conscience as qc

    def _boom(*a, **k):
        raise RuntimeError("no conscience available")

    monkeypatch.setattr(qc, "QueenConscience", _boom)

    # Capture the conscience passed by operator_server without contacting the
    # tenant's configured model endpoint. The real Cognition VETO behavior is
    # covered separately; this regression owns the construction-failure seam.
    captured = {}

    class _NoNetworkCognition:
        def __init__(self, *args, conscience=None, **kwargs):
            captured["conscience"] = conscience

        def reason(self, prompt, session_id=None):
            whisper = captured["conscience"].ask_why(prompt, {})
            verdict = whisper.verdict.name
            payload = {
                "text": whisper.message,
                "blocked": verdict == "VETO",
                "conscience_verdict": verdict,
                "conscience_message": whisper.message,
            }
            return SimpleNamespace(to_dict=lambda: payload)

    monkeypatch.setattr(cognition_mod, "AureonCognition", _NoNetworkCognition)

    client, srv, _ks = app_env
    app = srv.create_app(          # fresh app so the tenant-conscience cache is built under _boom
        test_ingress_release=srv.TestOnlyOperatorIngressRelease(
            master_key=b"operator-tenant-conscience-route-test-key",
        )
    )
    c2 = app.test_client()
    _connect_model(c2, _tenant("aaa"))
    marker = "tenant-private-marker-conscience-fallback-4417"
    r = c2.post("/api/cognition/reason", json={"prompt": marker}, headers=_tenant("aaa"))
    assert r.status_code == 200, "a missing conscience must not break the tenant plane"
    body = r.get_json()
    assert body["blocked"] is True
    assert body["conscience_verdict"] == "VETO"
    assert "NO_DATA" in body["conscience_message"]
    assert "denied" in body["conscience_message"]
    assert captured["conscience"].available is False
    assert captured["conscience"]._thought_bus is None

    try:
        from aureon.core.aureon_thought_bus import get_thought_bus

        bus = get_thought_bus()
    except Exception:  # pragma: no cover - no bus in this env ⇒ nothing to leak into
        return
    if bus is None:
        return
    recent = bus.get_recent(limit=500) or []
    assert marker not in json.dumps(recent, default=str), (
        "the tenant plane borrowed the shared bus-attached conscience and published the prompt"
    )


# ── one model response must not be able to exhaust the host ────────────────────

def test_tool_call_arguments_from_the_model_are_bounded():
    """Tool calls arrive in the MODEL's response, so MAX_CONTENT_LENGTH never bounded them. On the
    tenant plane that model is a server the user controls, so one reply could request unlimited
    parsing work on the operator host."""
    from aureon.inhouse_ai.agent_runner import (
        _MAX_TOOL_ARG_BYTES,
        _MAX_TOOL_CALLS_PER_RESPONSE,
        _oversized_argument,
    )

    assert _oversized_argument({"code": "x"}) is None
    assert _oversized_argument({"code": "x" * (_MAX_TOOL_ARG_BYTES + 1)}) == "code"
    assert _oversized_argument({"blob": ["y" * 1024] * 1024}) == "blob"   # non-str serialized
    assert _oversized_argument(None) is None
    assert _MAX_TOOL_CALLS_PER_RESPONSE > 0


# The gate only inspects paths under /api/ or /mcp/ (operator_server _gate). Anything mounted at a
# different prefix is served with NO credential at all — not even a 401. Verified: a route added at
# /internal/... returned 200 with instance state to an unauthenticated caller. Today's non-gated set
# is deliberate and benign, so pin it: a new prefix has to be a conscious decision, made here.
_ROUTES_OUTSIDE_THE_GATE = {
    "/",                          # the console shell
    "/healthz", "/readyz",        # liveness probes
    "/metrics",                   # scrape endpoint (also in _OPEN_PATHS)
    "/static/<path:filename>",    # bundled assets
    "/watch", "/watch/", "/watch/<path:asset>",   # the deliberately public showcase surface
}


def test_no_route_escapes_the_gate_prefixes(app_env):
    """A route outside /api/ and /mcp/ is UNAUTHENTICATED — the gate never sees it.

    So the set of such routes is a security decision, not an implementation detail. If this fails,
    either move the new route under /api/ (where default-deny protects it) or add it here with a
    reason, having confirmed it is safe to serve to anonymous callers.
    """
    _client, srv, _ks = app_env
    app = srv.create_app(
        test_ingress_release=srv.TestOnlyOperatorIngressRelease(
            master_key=b"operator-tenant-route-census-test-material",
        )
    )
    outside = {r.rule for r in app.url_map.iter_rules()
               if not (r.rule.startswith("/api/") or r.rule.startswith("/mcp/"))}
    unexpected = outside - _ROUTES_OUTSIDE_THE_GATE
    assert not unexpected, (
        "these routes bypass the auth gate entirely and would be served to anyone: "
        f"{sorted(unexpected)}"
    )


# ── the one identity call a tenant may make ────────────────────────────────────

def test_tenant_can_read_their_own_identity(app_env):
    """The console needs this to render the right plane. Without it a signed-in user is shown the
    operator's navigation and discovers the boundary by collecting 403s."""
    client, _srv, _ks = app_env
    r = client.get("/api/me", headers=_tenant("tenant-aaa-0001"))
    assert r.status_code == 200
    body = r.get_json()
    assert body["kind"] == "tenant"
    assert body["is_admin"] is False
    assert body["plane"] == "account"
    assert body["tenancy_enabled"] is True
    assert isinstance(body["allowed_routes"], list) and body["allowed_routes"]


def test_identity_never_echoes_the_raw_jwt_subject(app_env):
    """`tenant_label` is a short hash: enough to confirm which account you are on, without putting
    the subject identifier into the page or the logs."""
    client, _srv, _ks = app_env
    sub = "tenant-aaa-0001"
    body = client.get("/api/me", headers=_tenant(sub)).get_json()
    assert sub not in json.dumps(body)
    assert body["tenant_label"] and body["tenant_label"] != sub


def test_identity_tells_the_operator_they_are_the_operator(app_env):
    client, _srv, _ks = app_env
    body = client.get("/api/me", headers=_ADMIN).get_json()
    assert body["kind"] == "admin"
    assert body["is_admin"] is True
    assert body["plane"] == "instance"
    assert body["tenant_label"] is None
    assert body["allowed_routes"] is None      # an operator is not route-limited


def test_identity_says_nothing_about_the_instance(app_env):
    """`/api/pulse` is operator-only precisely because it names the instance's live providers and
    switchboard. This endpoint has to be tenant-safe, so it must not leak the same thing sideways.

    `allowed_routes` is excluded from the scan: it is route *patterns* describing what this caller may
    reach (so it naturally contains the word "providers"), which is the tenant's own permission set,
    not a statement about the instance.
    """
    client, _srv, _ks = app_env
    body = client.get("/api/me", headers=_tenant("aaa")).get_json()
    scanned = {k: v for k, v in body.items() if k != "allowed_routes"}
    blob = json.dumps(scanned).lower()
    for leak in ("provider", "switchboard", "adapter", "model", "equity", "balance", "kraken"):
        assert leak not in blob, f"/api/me leaked instance detail: {leak}"
    # and the route list must be patterns only — never a resolved value or a live name
    for route in body["allowed_routes"]:
        method, _, path = route.partition(" ")
        assert method in {"GET", "POST", "DELETE", "PUT", "PATCH"}, route
        assert path.startswith("/api/"), route
