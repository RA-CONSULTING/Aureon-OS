"""
📡 Aureon Operator server — SSE stream + phone proof-of-concept.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A tiny Flask app so the switchboard can be *seen*, live, from a phone — the
"operator will be like streaming YouTube… you talk and it's a live stream"
part of the vision.

Routes:
  GET  /                       mobile-responsive chat page (self-contained HTML)
  GET  /watch                  Aureon Watch — voice-first wearable PWA (Pixel Watch / Ray-Ban)
  GET  /watch/<asset>          watch app static assets (css/js/manifest/sw/icons)
  GET  /api/operator/stream    Server-Sent Events: phases, then the answer token-by-token
  POST /api/operator/respond   one-shot JSON (OperatorResponse.to_dict())
  GET  /api/pulse              composed read-only vitals (line-up + status + organism)
  GET  /healthz                liveness + active provider line-up

Run:
  python -m aureon.operator.operator_server          # binds 127.0.0.1:8080
  AUREON_OPERATOR_PORT=8899 python -m aureon.operator.operator_server

Reaching it from a phone: this repo usually runs in a remote container, so open
the deployed/tunnelled URL on the phone (see the deployment section of
docs/architecture/AUREON_OPERATOR_SWITCHBOARD.md), not localhost.
"""

from __future__ import annotations

import contextlib
import hashlib
import ipaddress
import json
import logging
import os
import struct
import threading
from types import SimpleNamespace
from typing import Any, Dict, Final

logger = logging.getLogger("aureon.operator.server")


def _is_loopback_host(value: str | None) -> bool:
    host = str(value or "").strip().strip("[]").casefold()
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _load_env_file() -> None:
    """Honour a local ``.env`` so deploy-time credentials/endpoints (e.g. the
    Ollama base URL, model, and API key for the LLM capability) take effect.

    Called only from the serving entrypoints (``main`` / ``build_boot_app``), not
    at import — so ``create_app`` stays hermetic for tests. No-op if python-dotenv
    or the file is absent; never overrides an already-set variable.

    Delegates to the repo-canonical ``bootstrap_credentials`` (the same call the
    HNC daemons make): ``.env`` across all candidate paths + HNC env-packet decode
    + credential aliases, then the encrypted provider keystore (the Providers UI
    control plane) layered on top.
    """
    try:  # pragma: no cover - best-effort loader
        from aureon.core.aureon_env import bootstrap_credentials

        bootstrap_credentials()
    except Exception:  # noqa: BLE001
        pass

try:
    from flask import Flask, Response, g, jsonify, request, send_from_directory
except Exception as exc:  # noqa: BLE001
    raise SystemExit(
        "Flask is required for the operator server (it is in requirements.txt): "
        f"{exc}"
    ) from exc

from aureon.harmonic.hnc_quantum_packet_crypto import (  # noqa: E402
    packet_master_key_from_env,
)
from aureon.observability import (  # noqa: E402
    current_correlation_id,
    emit_local_event,
    install_flask_request_correlation,
)
from aureon.operator.aureon_operator import AureonOperator  # noqa: E402  (after guarded flask import)
from aureon.operator.providers import build_provider_set, describe_provider_set  # noqa: E402
from aureon.plumber.os_protection import (  # noqa: E402
    DEFAULT_MAX_INGRESS_BYTES,
    AdmittedHNC,
    IngressDisposition,
    LocalOSProtectionBoundary,
    QuarantinedHNC,
)

# The voice-first wearable (Pixel Watch / Ray-Ban) app — self-contained static PWA.
WEARABLE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wearable")


def _json_safe(obj: Any) -> Any:
    """Recursively replace non-finite floats (Infinity/NaN) with None.

    Python's json emits bare ``Infinity``/``NaN`` tokens, which are valid for
    Python's parser and curl but are **rejected** by browser ``Response.json()``
    (strict JSON). The watch calls ``/api/pulse`` from the browser, so its body
    must be spec-clean or the fetch throws.
    """
    import math

    if isinstance(obj, float):
        return None if (math.isinf(obj) or math.isnan(obj)) else obj
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    return obj


def _test_provider_adapter(info: Any, api_key: str, base_url: Any, model: str) -> Dict[str, Any]:
    """Construct a fresh adapter for ``info`` with the given key and do ONE real
    ``prompt()`` round-trip. Never raises; returns a compact verdict (no secrets)."""
    import time

    try:
        from aureon.operator.providers import build_adapter

        adapter = build_adapter(info.kind, api_key=api_key, base_url=base_url, model=model)

        t0 = time.perf_counter()
        resp = adapter.prompt(
            [{"role": "user", "content": "Reply with exactly: OK"}], max_tokens=16
        )
        elapsed = int((time.perf_counter() - t0) * 1000)
        text = str(getattr(resp, "text", "") or "")
        stop = str(getattr(resp, "stop_reason", "") or "")
        ok = bool(text) and not text.startswith("[ERROR]") and stop != "error"
        return {
            "ok": ok,
            "latency_ms": elapsed,
            "model": model,
            "sample": text[:80],
            "error": "" if ok else (text[:160] or "no response"),
        }
    except Exception as exc:  # noqa: BLE001 — a failed test is a verdict, not a 500
        emit_local_event(
            logger,
            logging.WARNING,
            "operator_provider_test_failure",
            correlation_id=current_correlation_id(),
            fields={"component": "provider_test", "model": model},
            exception=exc,
        )
        return {
            "ok": False,
            "latency_ms": 0,
            "model": model,
            "sample": "",
            "error": "provider_test_failed",
            "error_type": type(exc).__name__,
        }


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Aureon Operator</title>
<style>
  :root { color-scheme: light dark; --bg:#0b1020; --panel:#141c33; --ink:#e7ecff;
          --muted:#8b95bb; --accent:#7c5cff; --ok:#39d98a; --warn:#ffcc4d; --veto:#ff6b6b; }
  @media (prefers-color-scheme: light) {
    :root { --bg:#f4f6ff; --panel:#ffffff; --ink:#141c33; --muted:#5a6488; --accent:#5b3df5; }
  }
  * { box-sizing: border-box; }
  html,body { margin:0; height:100%; }
  body { background:var(--bg); color:var(--ink); font:16px/1.5 -apple-system,BlinkMacSystemFont,
         "Segoe UI",Roboto,Helvetica,Arial,sans-serif; display:flex; flex-direction:column; }
  header { padding:14px 16px; background:var(--panel); border-bottom:1px solid rgba(124,92,255,.25);
           display:flex; align-items:center; gap:10px; position:sticky; top:0; }
  header .dot { width:10px; height:10px; border-radius:50%; background:var(--ok);
                box-shadow:0 0 10px var(--ok); }
  header h1 { font-size:16px; margin:0; font-weight:700; letter-spacing:.02em; }
  header small { color:var(--muted); margin-left:auto; font-size:12px; }
  #log { flex:1; overflow-y:auto; padding:16px; display:flex; flex-direction:column; gap:12px; }
  .msg { max-width:88%; padding:10px 13px; border-radius:14px; white-space:pre-wrap; word-wrap:break-word; }
  .me { align-self:flex-end; background:var(--accent); color:#fff; border-bottom-right-radius:4px; }
  .ai { align-self:flex-start; background:var(--panel); border:1px solid rgba(124,92,255,.2);
        border-bottom-left-radius:4px; }
  .phases { align-self:flex-start; display:flex; flex-wrap:wrap; gap:6px; max-width:88%; }
  .chip { font-size:11px; padding:3px 9px; border-radius:999px; background:var(--panel);
          border:1px solid rgba(124,92,255,.3); color:var(--muted); }
  .chip.on { color:var(--ink); border-color:var(--accent); }
  .verdict { font-size:12px; margin-top:6px; color:var(--muted); }
  .verdict.veto { color:var(--veto); font-weight:700; }
  footer { padding:10px; background:var(--panel); border-top:1px solid rgba(124,92,255,.25);
           display:flex; gap:8px; padding-bottom:calc(10px + env(safe-area-inset-bottom)); }
  #prompt { flex:1; padding:12px 14px; border-radius:12px; border:1px solid rgba(124,92,255,.3);
            background:var(--bg); color:var(--ink); font-size:16px; }
  #send { padding:12px 18px; border:0; border-radius:12px; background:var(--accent); color:#fff;
          font-weight:700; font-size:16px; }
  #send:disabled { opacity:.5; }
</style>
</head>
<body>
  <header>
    <span class="dot"></span>
    <h1>Aureon Operator</h1>
    <label style="margin-left:auto;font-size:12px;color:var(--muted);display:flex;align-items:center;gap:6px;cursor:pointer">
      <input type="checkbox" id="mode"> 🧠 cognition
    </label>
    <small id="lineup" style="margin-left:12px">switchboard…</small>
  </header>
  <div id="log">
    <div class="ai msg">Ask me anything about Aureon. I fan your question across every AI line,
ground it in the repo, collapse the answers to one, and run it past the Queen's conscience before I speak.</div>
  </div>
  <footer>
    <input id="prompt" placeholder="How does Aureon integrate data across systems?"
           autocomplete="off" enterkeyhint="send">
    <button id="send">Send</button>
  </footer>
<script>
const log = document.getElementById('log');
const input = document.getElementById('prompt');
const send = document.getElementById('send');
const PHASES = ['ground','fan_out','consensus','veto'];

fetch('/healthz').then(r=>r.json()).then(d=>{
  document.getElementById('lineup').textContent =
    (d.providers||[]).map(p=>p.name).join(' · ') || 'offline';
}).catch(()=>{});

function el(cls, text){ const d=document.createElement('div'); d.className=cls; if(text)d.textContent=text; log.appendChild(d); log.scrollTop=log.scrollHeight; return d; }

function ask(){
  const q = input.value.trim();
  if(!q) return;
  el('me msg', q);
  input.value=''; send.disabled=true; input.disabled=true;

  const cognition = document.getElementById('mode').checked;
  const chips = el('phases');
  const chipEls = {};
  const steps = cognition ? ['grounding','tool','veto'] : PHASES;
  steps.forEach(p=>{ const c=document.createElement('span'); c.className='chip'; c.textContent=p; chips.appendChild(c); chipEls[p]=c; });
  const bubble = el('ai msg', '');
  let answer = '';

  const base = cognition ? '/api/cognition/stream' : '/api/operator/stream';
  const es = new EventSource(base+'?prompt='+encodeURIComponent(q));
  es.addEventListener('phase', e=>{
    const d = JSON.parse(e.data);
    if(chipEls[d.phase]){ chipEls[d.phase].classList.add('on');
      if(d.phase==='fan_out'&&d.detail) chipEls[d.phase].textContent='fan_out '+d.detail.n_ok+'/'+d.detail.n_total;
      if(d.phase==='consensus'&&d.detail) chipEls[d.phase].textContent='consensus '+Math.round((d.detail.agreement||0)*100)+'%';
    }
    log.scrollTop=log.scrollHeight;
  });
  es.addEventListener('grounding', e=>{ const d=JSON.parse(e.data).detail||{}; if(chipEls.grounding){chipEls.grounding.classList.add('on'); chipEls.grounding.textContent='grounding '+(d.source_count||0)+' src';} });
  es.addEventListener('tool', e=>{ const d=JSON.parse(e.data).detail||{}; if(chipEls.tool){chipEls.tool.classList.add('on'); chipEls.tool.textContent='🔧 '+(d.tool||'tool');} });
  es.addEventListener('veto', e=>{ const d=JSON.parse(e.data).detail||{}; if(chipEls.veto){chipEls.veto.classList.add('on'); chipEls.veto.textContent='veto '+(d.verdict||'');} });
  es.addEventListener('token', e=>{ answer += JSON.parse(e.data).text; bubble.textContent = answer; log.scrollTop=log.scrollHeight; });
  es.addEventListener('complete', e=>{
    const d = JSON.parse(e.data).response||{};
    const v = document.createElement('div');
    v.className = 'verdict' + (d.blocked ? ' veto':'');
    v.textContent = '🦗 conscience: '+(d.conscience_verdict||'—') +
      (d.consensus? '  ·  agreement '+Math.round((d.consensus.agreement||0)*100)+'%':'') +
      (d.grounding? '  ·  '+(d.grounding.source_count||0)+' sources':'');
    bubble.appendChild(v);
    es.close(); send.disabled=false; input.disabled=false; input.focus();
  });
  es.onerror = ()=>{ es.close(); if(!answer) bubble.textContent='[stream error]'; send.disabled=false; input.disabled=false; };
}
send.onclick = ask;
input.addEventListener('keydown', e=>{ if(e.key==='Enter') ask(); });
</script>
</body>
</html>
"""


# ── What a TENANT may reach: an ALLOWLIST, enforced once in the gate ──────────────────────────
#
# Default-deny. Any /api or /mcp route absent from this table is operator-only for a signed-in
# end user, whichever registrar mounted it.
#
# This replaces per-route guarding because per-route guarding failed three audits running, always
# the same way: the WRITE sibling got a guard and the READ sibling kept serving. Round 1 found
# unguarded POSTs; round 2 guarded them; round 3 then found GET /api/terminal-state (instance
# equity, exchange account id, open positions, PnL), GET /api/flight-test and /api/reboot-advice
# (the instance .env path and which exchange keys were written — the very disclosure round 2 had
# just closed on /api/env-credentials), GET /api/approvals, GET /api/switchboard, GET /api/pulse
# and GET /api/action/status. The reason enumeration keeps missing routes is structural: the ~64
# rules are mounted by five different registrars (this module, saas/gateway, legacy_runtime_api,
# connections_api, autonomous/aureon_face_app), so no file lists them and no reviewer sees them
# all. The gate does see them all — so the decision belongs here.
#
# The failure mode is now "a tenant feature 403s until it is added here", which is loud and safe,
# instead of "an instance route leaks until an auditor finds it".
_TENANT_OWN_PLANE = {
    # Who am I / what may I do. Reports the caller's own identity and nothing about the instance,
    # so the console can render the right plane instead of discovering it by collecting 403s.
    ("GET", "/api/me"),
    # The user's own data: their keys, their reasoning, their billing.
    ("GET", "/api/providers"), ("POST", "/api/providers/<provider_id>"),
    ("DELETE", "/api/providers/<provider_id>"), ("POST", "/api/providers/<provider_id>/test"),
    ("GET", "/api/connections"), ("GET", "/api/connections/readiness"),
    ("POST", "/api/connections/<conn_id>"), ("POST", "/api/connections/<conn_id>/test"),
    ("POST", "/api/cognition/reason"), ("POST", "/api/operator/respond"),
    ("GET", "/api/cognition/stream"), ("GET", "/api/operator/stream"),
    ("GET", "/api/billing/balance"), ("GET", "/api/billing/usage"), ("GET", "/api/billing/status"),
    # Listed, but the view is stricter than this table: it permits a tenant ONLY when they supply
    # their own botToken, never the instance's bot identity.
    ("POST", "/api/notifications/telegram"),
}
_TENANT_SHOWCASE = {
    # Read-only views of the organism that are ALREADY public by design — the same material the
    # /watch surface and the Twitch stream put in front of anonymous visitors. Withholding these
    # from a signed-in user would protect nothing.
    ("GET", "/api/catalog"), ("GET", "/api/domains"), ("GET", "/api/domains/<domain>"),
    ("GET", "/api/coverage"), ("GET", "/api/defense"),
    ("GET", "/api/organism"), ("GET", "/api/soul"), ("GET", "/api/consciousness"),
    ("GET", "/api/company"), ("GET", "/api/org"), ("GET", "/api/affect"),
    ("GET", "/api/pursuit"), ("GET", "/api/inner-work"), ("GET", "/api/metacognition"),
    ("GET", "/api/automation"), ("GET", "/api/cognition"), ("GET", "/api/cognition/brain"),
    ("GET", "/api/cognition/bus"), ("GET", "/api/cognition/connectome"),
    ("GET", "/api/cognition/field"), ("GET", "/api/cognition/mycelium"),
}
_TENANT_ALLOWED = _TENANT_OWN_PLANE | _TENANT_SHOWCASE


OPERATOR_CONTROL_PLANE_PURPOSE: Final = "aureon.operator.control-plane.http-ingress.v0"
MAX_OPERATOR_AUTHORIZATION_BYTES: Final = 8 * 1024
MAX_OPERATOR_FORWARDED_FOR_BYTES: Final = 4 * 1024
MAX_OPERATOR_CONTENT_TYPE_BYTES: Final = 512
MAX_OPERATOR_PATH_BYTES: Final = 4 * 1024
MAX_OPERATOR_QUERY_BYTES: Final = 16 * 1024
MAX_OPERATOR_BODY_BYTES: Final = (
    DEFAULT_MAX_INGRESS_BYTES - MAX_OPERATOR_QUERY_BYTES - MAX_OPERATOR_PATH_BYTES - 4096
)
_MUTATING_METHODS: Final = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_QUERY_DRIVEN_EFFECT_RULES: Final = frozenset(
    {"/api/cognition/stream", "/api/operator/stream"}
)


class TestOnlyOperatorIngressRelease:
    """Explicit non-production seam for HTTP route unit tests.

    This seam never decrypts an HNC carrier and never claims a Magic Star
    release.  It only permits a Flask view to run *after* the local admission's
    opaque handle has been atomically burned.  ``create_app`` refuses this type
    in production, and the serving entrypoints never construct it.
    """

    test_only = True
    production_ready = False
    magic_star_release = False

    def __init__(self, *, master_key: bytes | str) -> None:
        key_snapshot = bytes(master_key) if isinstance(master_key, bytes) else str(master_key)
        self._boundary = LocalOSProtectionBoundary(
            boundary_id="operator-control-plane-test-only",
            master_key_provider=lambda: key_snapshot,
            max_ingress_bytes=DEFAULT_MAX_INGRESS_BYTES,
        )

    def _authorize_after_discard(
        self,
        *,
        admission_summary: dict[str, Any],
        discard_summary: dict[str, Any],
    ) -> bool:
        """Validate the test receipt without accepting caller-defined callbacks."""

        return bool(
            admission_summary.get("disposition") == str(IngressDisposition.ADMITTED_HNC)
            and discard_summary.get("disposition") == "DISCARDED_HNC"
            and admission_summary.get("admission_id") == discard_summary.get("admission_id")
            and discard_summary.get("carrier_released") is False
            and discard_summary.get("plaintext_decoded") is False
            and admission_summary.get("production_ready") is False
            and discard_summary.get("production_ready") is False
        )

    def boundary_public_summary(self) -> dict[str, Any]:
        """Commitment-only boundary state for tests; no key or carrier is exposed."""

        return self._boundary.public_summary()


def _strict_json_object(raw: bytes) -> bool:
    """Accept one duplicate-free finite JSON object, without retaining a parse."""

    if not raw:
        return True

    def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate_json_key")
            result[key] = value
        return result

    def _reject_constant(_value: str) -> Any:
        raise ValueError("non_finite_json_number")

    try:
        decoded = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_object_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, ValueError, TypeError, RecursionError):
        return False
    return isinstance(decoded, dict)


def _frame_operator_ingress(
    *,
    method: bytes,
    path: bytes,
    route_rule: bytes,
    query: bytes,
    body: bytes,
) -> bytes:
    """Length-frame exact HTTP material before local HNC admission."""

    fields = (method, path, route_rule, query, body)
    return b"aureon.operator.http-ingress.v0\x00" + b"".join(
        struct.pack(">Q", len(field)) + field for field in fields
    )


def _operator_hnc_master_key() -> str | None:
    """Return configured packet key material, preserving missing vs invalid."""

    value = packet_master_key_from_env()
    return value or None


def create_app(
    operator: AureonOperator | None = None,
    cognition: Any = None,
    *,
    test_ingress_release: TestOnlyOperatorIngressRelease | None = None,
) -> Flask:
    app = Flask("aureon-operator")
    install_flask_request_correlation(app, logger=logger)
    _operator = operator or AureonOperator()

    # ── Security envelope (production fail-closed; explicit dev/test is permissive) ──
    from aureon.operator.identity import resolve_identity
    from aureon.operator.security import SecurityConfig, TokenBucket

    _sec = SecurityConfig.from_env()
    if test_ingress_release is not None:
        if type(test_ingress_release) is not TestOnlyOperatorIngressRelease:
            raise TypeError("test_ingress_release_must_be_exact_test_only_seam")
        if _sec.production:
            raise ValueError("test_ingress_release_forbidden_in_production")
    # End-user tenancy (optional): a Supabase HS256 JWT identifies the caller as a tenant, so their
    # provider/connection keys are namespaced to them. Off by default (secret unset) ⇒ the gate is
    # identical to the single static-key path — see aureon.operator.identity.resolve_identity.
    _jwt_secret = str(os.environ.get("AUREON_SUPABASE_JWT_SECRET", "") or "")
    _bucket = TokenBucket(_sec.rate_rps, _sec.burst)
    _effective_body_limit = min(_sec.max_body_bytes, MAX_OPERATOR_BODY_BYTES)
    app.config["MAX_CONTENT_LENGTH"] = _effective_body_limit
    _ingress_boundary = (
        test_ingress_release._boundary
        if test_ingress_release is not None
        else LocalOSProtectionBoundary(
            boundary_id="operator-control-plane-local-hnc",
            master_key_provider=_operator_hnc_master_key,
            max_ingress_bytes=DEFAULT_MAX_INGRESS_BYTES,
        )
    )
    # Expose only a commitment-only status callable for hostile/runtime tests.
    # The boundary object, carriers, handles, and key provider remain private.
    app.extensions["aureon_operator_ingress_status"] = _ingress_boundary.public_summary
    _OPEN_PATHS = ("/", "/healthz", "/readyz", "/metrics", "/favicon.ico")
    def _err(code: int, message: str, **extra):
        response = jsonify({"error": {"code": code, "message": message, **extra}})
        response.headers["Cache-Control"] = "no-store"
        return response, code

    def _bounded_header(name: str, maximum_bytes: int) -> bool:
        value = request.headers.get(name, "")
        try:
            return len(value.encode("utf-8", errors="strict")) <= maximum_bytes
        except UnicodeEncodeError:
            return False

    def _requires_hnc_protection() -> bool:
        if request.method in _MUTATING_METHODS:
            return True
        rule = getattr(request.url_rule, "rule", None)
        return request.method == "GET" and rule in _QUERY_DRIVEN_EFFECT_RULES

    def _held_response(outcome: AdmittedHNC | QuarantinedHNC):
        summary = outcome.public_summary()
        if isinstance(outcome, AdmittedHNC):
            discard = _ingress_boundary.discard_admitted(
                outcome.handle,
                reason_code="production_magic_star_release_unavailable",
            )
            if test_ingress_release is not None and test_ingress_release._authorize_after_discard(
                admission_summary=summary,
                discard_summary=discard,
            ):
                # Explicit route-test seam only.  This is not a Magic Star
                # release and is unreachable from the default/serving apps.
                g.operator_ingress_test_only = True
                g.operator_ingress_admission_commitment = summary["admission_commitment"]
                return None
            return _err(
                503,
                "operator control-plane ingress held",
                disposition=summary["disposition"],
                reason_code="production_magic_star_release_unavailable",
                admission_commitment=summary["admission_commitment"],
                handle_commitment=summary["handle"]["handle_commitment"],
                carrier_released=False,
                plaintext_decoded=False,
                handler_invoked=False,
                local_development_only=True,
                production_ready=False,
            )
        return _err(
            503,
            "operator control-plane ingress quarantined",
            disposition=summary["disposition"],
            reason_code="hnc_ingress_quarantined",
            quarantine_commitment=summary["quarantine_commitment"],
            denial_codes=summary["denial_codes"],
            raw_material_retained=False,
            handler_invoked=False,
            local_development_only=True,
            production_ready=False,
        )

    def _protect_control_plane_ingress(client: str):
        try:
            client_bytes = client.encode("utf-8", errors="strict")
        except UnicodeEncodeError:
            return _err(400, "client address is not valid UTF-8")
        source_commitment = hashlib.sha256(client_bytes).hexdigest()
        try:
            path_bytes = request.path.encode("utf-8", errors="strict")
        except UnicodeEncodeError:
            return _err(400, "request path is not valid UTF-8")
        if len(path_bytes) > MAX_OPERATOR_PATH_BYTES:
            return _err(414, "request path exceeds operator boundary")
        query_bytes = bytes(request.query_string)
        if len(query_bytes) > MAX_OPERATOR_QUERY_BYTES:
            return _err(414, "request query exceeds operator boundary")
        content_length = request.content_length
        if content_length is not None and (
            content_length < 0 or content_length > _effective_body_limit
        ):
            return _err(413, f"request body exceeds {_effective_body_limit} bytes")
        # Werkzeug/Flask enforces MAX_CONTENT_LENGTH here even when a peer omits
        # Content-Length. Cache preserves the same exact bytes for a test-only
        # route handler without a second socket read.
        body_bytes = bytes(request.get_data(cache=True, as_text=False))
        if len(body_bytes) > _effective_body_limit:
            return _err(413, f"request body exceeds {_effective_body_limit} bytes")
        if body_bytes and (
            request.mimetype != "application/json" or not _strict_json_object(body_bytes)
        ):
            body_contract_valid = False
        else:
            body_contract_valid = True
        rule = str(getattr(request.url_rule, "rule", None) or "<unmatched>")
        method_bytes = request.method.encode("ascii", errors="strict")
        rule_bytes = rule.encode("utf-8", errors="strict")
        framed = _frame_operator_ingress(
            method=method_bytes,
            path=path_bytes,
            route_rule=rule_bytes,
            query=query_bytes,
            body=body_bytes,
        )
        operator_aad = {
            "schema": "aureon.operator.http-ingress-aad.v0",
            "method": request.method,
            "path_sha256": hashlib.sha256(path_bytes).hexdigest(),
            "path_size_bytes": len(path_bytes),
            "route_rule_sha256": hashlib.sha256(rule_bytes).hexdigest(),
            "query_sha256": hashlib.sha256(query_bytes).hexdigest(),
            "query_size_bytes": len(query_bytes),
            "body_sha256": hashlib.sha256(body_bytes).hexdigest(),
            "body_size_bytes": len(body_bytes),
            "content_type_sha256": hashlib.sha256(
                str(request.content_type or "").encode("utf-8", errors="strict")
            ).hexdigest(),
            "identity_kind": str(getattr(g, "identity_kind", "unknown")),
            "tenant_commitment": hashlib.sha256(
                str(getattr(g, "tenant", "") or "").encode("utf-8", errors="strict")
            ).hexdigest(),
            "source_truth_established_by_local_wrapping": False,
            "production_magic_star_release_available": False,
        }
        outcome = _ingress_boundary.admit_external(
            framed,
            source_id=f"operator-http-peer-sha256:{source_commitment}",
            ingress_kind=f"http:{request.method}:{rule}",
            purpose=OPERATOR_CONTROL_PLANE_PURPOSE,
            operator_aad=operator_aad,
            content_validator=lambda _view: body_contract_valid,
        )
        return _held_response(outcome)

    def _record_runtime_exception(
        event: str,
        component: str,
        exc: BaseException,
        *,
        level: int = logging.ERROR,
    ) -> None:
        emit_local_event(
            logger,
            level,
            event,
            correlation_id=current_correlation_id(),
            fields={"component": component, "method": request.method, "path": request.path},
            exception=exc,
        )

    @app.before_request
    def _gate():
        path = request.path
        if path in _OPEN_PATHS or not (path.startswith("/api/") or path.startswith("/mcp/")):
            return None
        # Bound attacker-controlled address/auth headers before parsing or HNC
        # work.  In particular, never feed an unbounded trusted-proxy chain to
        # the rate limiter or an unbounded bearer to the identity verifier.
        if not _bounded_header("Authorization", MAX_OPERATOR_AUTHORIZATION_BYTES):
            return _err(431, "authorization header exceeds operator boundary")
        if not _bounded_header("X-Forwarded-For", MAX_OPERATOR_FORWARDED_FOR_BYTES):
            return _err(431, "forwarded address header exceeds operator boundary")
        if not _bounded_header("Content-Type", MAX_OPERATOR_CONTENT_TYPE_BYTES):
            return _err(431, "content type header exceeds operator boundary")
        direct_client = str(request.remote_addr or "")
        try:
            direct_client_size = len(direct_client.encode("utf-8", errors="strict"))
        except UnicodeEncodeError:
            direct_client_size = MAX_OPERATOR_FORWARDED_FOR_BYTES + 1
        if direct_client_size > 128:
            return _err(400, "client address exceeds operator boundary")
        # Rate-limit before authentication so invalid bearer attempts cannot
        # bypass the limiter. Forwarded addresses are resolved only through
        # explicitly configured trusted proxy networks.
        if _sec.rate_enabled:
            client = _sec.client_ip(
                request.remote_addr,
                request.headers.get("X-Forwarded-For"),
            )
            ok, retry = _bucket.check(client)
            if not ok:
                resp = _err(429, "rate limit exceeded", retry_after=retry)
                resp[0].headers["Retry-After"] = str(int(retry) + 1)
                return resp
        if (
            not _sec.auth_enabled
            and not _jwt_secret
            and not _is_loopback_host(direct_client)
        ):
            return _err(401, "authenticated loopback operator required")
        # Resolve identity once. In explicit development/test mode, an empty static key and JWT
        # secret retain the local kind="open" behavior; production validation refuses that state.
        ident = resolve_identity(
            request.headers.get("Authorization"), operator_key=_sec.api_key, jwt_secret=_jwt_secret,
        )
        if not ident.ok:
            return _err(401, "missing or invalid bearer token")
        # Downstream routes namespace per-user stores by g.tenant (None ⇒ admin/global plane).
        g.tenant = ident.tenant
        g.is_admin = ident.kind in ("admin", "open")
        g.identity_kind = ident.kind
        # Default-deny for tenants (see _TENANT_ALLOWED). Match the url RULE, not request.path, so a
        # crafted id can never be read as a different route; an unmatched path (url_rule None ⇒ 404)
        # falls through untouched so Flask still answers 404 rather than 403. Admin and open planes
        # skip this entirely, which is what keeps the single-operator default byte-for-byte unchanged.
        if ident.kind == "tenant":
            rule = getattr(request.url_rule, "rule", None)
            if rule is not None and (request.method, rule) not in _TENANT_ALLOWED:
                return _err(403, "this route is operator-only", plane="admin")
        if _requires_hnc_protection():
            client = _sec.client_ip(
                request.remote_addr,
                request.headers.get("X-Forwarded-For"),
            )
            return _protect_control_plane_ingress(client)
        return None

    def _admin_denied():
        """403 for an end-user (tenant) reaching an INSTANCE-control route, else None.

        ``g.is_admin`` is true for the admin bearer and for the open/unauthenticated single-operator
        default, so this guard changes nothing when tenancy is off. It exists because the instance
        control plane — the feature switchboard (which can arm hard boundaries and re-apply the
        instance's own keys to ``os.environ``), local machine actions, manifest rebuilds, the
        approvals desk and the instance's notification credentials — is the operator's, not a
        signed-in end user's.
        """
        if getattr(g, "is_admin", True):
            return None
        return _err(403, "this control-plane route is operator-only", plane="admin")

    @app.errorhandler(400)
    def _400(e):
        return _err(400, "bad request")

    @app.errorhandler(404)
    def _404(e):
        return _err(404, "not found")

    @app.errorhandler(413)
    def _413(e):
        return _err(413, f"request body exceeds {_effective_body_limit} bytes")

    @app.errorhandler(500)
    def _500(e):
        # Flask calls the overridden, sanitized ``app.log_exception`` before
        # wrapping an unhandled failure as InternalServerError. Avoid emitting
        # a duplicate record for that path; explicit HTTP 500 responses have no
        # original exception and still receive one safe local event here.
        if getattr(e, "original_exception", None) is None:
            _record_runtime_exception("operator_unhandled_exception", "request", e)
        return _err(500, "internal server error", request_id=current_correlation_id())

    @app.get("/")
    def index():
        return Response(PAGE, mimetype="text/html")

    # ── Aureon Watch — voice-first wearable PWA (the Ray-Ban path on the wrist) ──
    @app.get("/watch")
    @app.get("/watch/")
    def watch_index():
        return send_from_directory(WEARABLE_DIR, "index.html")

    @app.get("/watch/<path:asset>")
    def watch_asset(asset: str):
        resp = send_from_directory(WEARABLE_DIR, asset)
        if asset == "sw.js":
            # let the service worker claim the whole origin, and never stale-cache it
            resp.headers["Service-Worker-Allowed"] = "/"
            resp.headers["Cache-Control"] = "no-cache"
        return resp

    @app.get("/api/me")
    def whoami():
        """Who is this caller, and what may they do? The one identity call a TENANT may make.

        The console needs this to render honestly: without it a signed-in end user is shown the
        operator's navigation and discovers the boundary by collecting 403s. Deliberately says
        nothing about the instance — no provider line-up, no switchboard, no counts — so it is safe
        on the tenant plane, unlike ``/api/pulse`` which is operator-only for exactly that reason.

        The tenant id is reported as a **label** (a short hash), never the raw JWT ``sub``: it is
        enough for the user to confirm which account they are on and for support to correlate a
        report, without echoing the subject identifier back into the page or the logs.
        """
        kind = str(getattr(g, "identity_kind", "open") or "open")
        tenant = getattr(g, "tenant", None)
        is_admin = bool(getattr(g, "is_admin", True))
        return jsonify({
            "kind": kind,                       # "open" | "admin" | "tenant"
            "is_admin": is_admin,
            "tenant_label": _tenant_label(tenant) if tenant else None,
            "plane": "instance" if is_admin else "account",
            "tenancy_enabled": bool(_jwt_secret),
            "auth_required": bool(_sec.api_key or _jwt_secret),
            # What this caller may reach, so the console can hide what would 403 rather than
            # letting the user find the boundary by trial and error.
            "allowed_routes": (None if is_admin else
                               sorted(f"{m} {r}" for m, r in _TENANT_ALLOWED)),
        })

    @app.get("/api/pulse")
    def pulse():
        # One composed, read-only vitals call for the watch: line-up + platform
        # status + organism, so the wrist polls once instead of three times.
        out: Dict[str, Any] = {
            "ok": True,
            "service": "aureon-operator",
            "providers": describe_provider_set(_operator.providers),
        }
        try:
            from aureon.saas.status import get_platform_status

            out["status"] = get_platform_status()
        except Exception as exc:  # noqa: BLE001 — degrade honestly, never 500
            _record_runtime_exception(
                "operator_component_unavailable", "platform_status", exc, level=logging.WARNING
            )
            out["status"] = {"status": "unknown", "error": "platform_status_unavailable"}
        try:
            from aureon.saas.gateway import build_organism_payload

            out["organism"] = build_organism_payload()
        except Exception as exc:  # noqa: BLE001
            _record_runtime_exception(
                "operator_component_unavailable", "organism", exc, level=logging.WARNING
            )
            out["organism"] = {"available": False, "error": "organism_unavailable"}
        try:  # the human control plane's safety posture, at a glance
            from aureon.operator import feature_switchboard as _sb

            out["switchboard"] = _sb.summary()
        except Exception as exc:  # noqa: BLE001
            _record_runtime_exception(
                "operator_component_unavailable", "switchboard", exc, level=logging.WARNING
            )
            out["switchboard"] = {"error": "switchboard_unavailable"}
        # Browser Response.json() rejects bare Infinity/NaN — keep the body spec-clean.
        return jsonify(_json_safe(out))

    @app.get("/healthz")
    def healthz():
        # Liveness: the process is up and can describe its line-up.
        return jsonify(
            {
                "ok": True,
                "service": "aureon-operator",
                "providers": describe_provider_set(_operator.providers),
            }
        )

    @app.get("/readyz")
    def readyz():
        # Readiness: can we actually serve a request? (providers resolved, repo
        # index constructible, cognition present). Distinct from liveness so an
        # orchestrator doesn't route traffic before the service is usable.
        checks: Dict[str, Any] = {}
        checks["providers"] = len(_operator.providers) > 0
        try:
            from aureon.operator.repo_index import get_operator_repo_index

            get_operator_repo_index()
            checks["repo_index"] = True
        except Exception as exc:  # noqa: BLE001
            checks["repo_index"] = False
            checks["repo_index_error"] = "repo_index_unavailable"
            _record_runtime_exception(
                "operator_readiness_failure", "repo_index", exc, level=logging.WARNING
            )
        checks["cognition"] = _cognition["engine"] is not None
        try:
            from aureon.operator.connections_api import _real_data_policy_summary

            checks["real_data_policy"] = _real_data_policy_summary()
        except Exception as exc:  # noqa: BLE001
            checks["real_data_policy"] = {
                "probe_report_status": "unavailable",
                "error": "real_data_policy_unavailable",
            }
            _record_runtime_exception(
                "operator_readiness_failure", "real_data_policy", exc, level=logging.WARNING
            )
        ready = bool(checks["providers"] and checks["repo_index"])
        return jsonify({"ready": ready, "checks": checks}), (200 if ready else 503)

    @app.get("/metrics")
    def metrics():
        # Prometheus exposition of the aureon_operator_* metrics (metrics.py).
        try:
            from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

            return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
        except Exception:  # noqa: BLE001 — prometheus_client optional
            return jsonify({"error": "prometheus_client not installed"}), 501

    @app.get("/api/operator/stream")
    def stream():
        prompt = request.args.get("prompt", "").strip()
        session_id = request.args.get("session_id")
        if not prompt:
            return jsonify({"error": "missing prompt"}), 400
        # Tenant-aware exactly like POST /api/operator/respond: a signed-in user streams on THEIR
        # OWN model, never the instance's keys.
        op = _get_operator_for(getattr(g, "tenant", None))
        if op is None:
            return _sse([{"type": "complete", "response": _NO_TENANT_KEY}])
        return _sse(op.stream_events(prompt, session_id=session_id))

    @app.post("/api/operator/respond")
    def respond():
        body: Dict[str, Any] = request.get_json(silent=True) or {}
        prompt = str(body.get("prompt", "")).strip()
        if not prompt:
            return jsonify({"error": "missing prompt"}), 400
        op = _get_operator_for(getattr(g, "tenant", None))
        if op is None:  # signed-in user with no model of their own — honest, never instance models
            return jsonify(_NO_TENANT_KEY)
        resp = op.respond(prompt, session_id=body.get("session_id"))
        return jsonify(resp.to_dict())

    # ── Agentic cognition mode (tools + repo-wide grounding + veto) ────────────
    _cognition = {"engine": cognition}

    def _get_cognition():
        if _cognition["engine"] is None:
            from aureon.operator.cognition import AureonCognition

            _cognition["engine"] = AureonCognition(join_mesh=True)
        return _cognition["engine"]

    # ── Per-tenant live reasoning ──────────────────────────────────────────────
    # A signed-in end user reasons on THEIR OWN model keys, in isolation. We build a
    # request-scoped engine from the tenant's keystore (never os.environ), cache it per
    # tenant (bounded LRU), share the one tenant-agnostic conscience, and keep the engine
    # off the mesh AND off the shared thought bus. When a tenant has no key we answer
    # honestly instead of falling back to the instance's models.
    from collections import OrderedDict

    class _IsolatedBus:
        """A no-op bus for per-tenant engines: nothing published, nothing subscribed, nothing read.

        Two isolation duties. (1) ``subscribe`` must not register organism callbacks, or every cached
        tenant engine would accumulate them on the shared bus. (2) ``publish``/``recall`` must not
        touch shared memory, because a tenant's prompt and answer would otherwise land in the
        instance-wide thought bus where other planes can recall them. Read calls return empty rather
        than raising, so cognition simply reasons without organism context.
        """

        def subscribe(self, *args: Any, **kwargs: Any) -> None:
            return None

        def publish(self, *args: Any, **kwargs: Any) -> None:
            return None

        def recall(self, *args: Any, **kwargs: Any) -> list:
            return []

        def get_recent(self, *args: Any, **kwargs: Any) -> list:
            return []

        def __getattr__(self, name: str) -> Any:  # any other bus call is a silent no-op
            return lambda *a, **k: None

    def _tenant_label(tenant: str) -> str:
        """A short, non-reversible tag for logs/provenance — never the raw JWT sub."""
        import hashlib

        return hashlib.sha256(tenant.encode("utf-8")).hexdigest()[:12]

    _TENANT_ENGINE_MAX = 8
    _tenant_cog: OrderedDict[str, Any] = OrderedDict()
    _tenant_op: OrderedDict[str, Any] = OrderedDict()
    # Flask serves requests on many threads, so these caches are shared mutable state. Individual
    # dict operations are atomic under the GIL, but `if t in cache: cache.move_to_end(t)` is not —
    # a concurrent credential write calling _invalidate_tenant_engines can pop the key inside that
    # window, turning a request into a KeyError 500. Narrow, but it is a real interleaving.
    _engine_lock = threading.RLock()
    _NO_TENANT_KEY: Dict[str, Any] = {
        "text": "No model is connected to your account yet. Add an API key in Providers "
                "to reason with your own model.",
        "grounded": False, "blocked": False, "conscience_verdict": "APPROVED",
        "tenant_no_key": True,
    }

    def _shared_conscience() -> Any:
        try:
            return _get_cognition()._get_conscience()
        except Exception:  # noqa: BLE001 — no conscience ⇒ APPROVED-by-default downstream
            return None

    _tenant_conscience: Dict[str, Any] = {}

    class _UnavailableTenantConscience:
        """Fail-closed verdict source used when the isolated conscience has no evidence."""

        _thought_bus = None
        available = False

        def ask_why(self, *args: Any, **kwargs: Any) -> Any:
            return SimpleNamespace(
                verdict=SimpleNamespace(name="VETO"),
                message="NO_DATA: tenant-plane conscience unavailable; decision denied",
                truth_status="no_data",
                decision_status="denied",
                generated_values=False,
            )

    def _tenant_plane_conscience() -> Any:
        """One conscience for the whole tenant plane, with bus publishing disabled.

        The ethical gate must judge a tenant's turn in full — it is load-bearing, never skipped — but
        the Queen publishes each verdict (which quotes the action, i.e. the user's prompt) onto the
        shared thought bus, where other planes could recall it. So the tenant plane gets its own
        instance with ``_thought_bus`` detached: identical judgement, nothing written into shared
        instance memory.

        If a private conscience cannot be built, return an isolated unavailable conscience whose
        only verdict is an explicit ``VETO`` with ``no_data`` provenance — never ``None`` and never
        the shared one. Falling back to ``_shared_conscience()`` would cache the INSTANCE's bus-attached object
        for the whole tenant plane, so every later tenant verdict would publish the quoted action —
        the user's prompt — straight into shared instance memory, defeating the entire point of this
        function. A constructor failure must not downgrade either isolation or the decision gate.
        """
        if "obj" in _tenant_conscience:
            return _tenant_conscience["obj"]
        obj: Any
        try:
            from aureon.queen.queen_conscience import QueenConscience

            obj = QueenConscience()
            # __init__ subscribes to "symbolic.life.pulse" on the shared bus before we can detach it,
            # which leaves the tenant-plane conscience receiving the INSTANCE's substrate pulses and
            # feeding them into tenant verdicts — an inbound cross-plane read, and a callback the
            # shared bus would hold forever. Detach the subscription, then cut publishing.
            _detach_from_shared_bus(obj)
            obj._thought_bus = None  # verdicts judged, never published to shared memory
        except Exception:  # noqa: BLE001 — fail closed on both isolation and decision authority
            logger.warning("tenant-plane conscience unavailable; tenant turns are denied with no_data "
                           "rather than borrowing the instance's bus-attached conscience")
            # Do not cache the unavailable sentinel globally: a later tenant build
            # may recover after a transient constructor failure.
            return _UnavailableTenantConscience()
        _tenant_conscience["obj"] = obj
        return obj

    def _detach_from_shared_bus(obj: Any) -> None:
        """Remove every subscription ``obj`` registered on the shared thought bus. Best-effort."""
        bus = getattr(obj, "_thought_bus", None)
        subs = getattr(bus, "_subs", None)
        if not isinstance(subs, dict):
            return
        try:
            lock = getattr(bus, "_lock", None)
            ctx = lock if lock is not None else contextlib.nullcontext()
            with ctx:
                for handlers in subs.values():
                    if not isinstance(handlers, list):
                        continue
                    for h in [h for h in handlers if getattr(h, "__self__", None) is obj]:
                        handlers.remove(h)
        except Exception:  # noqa: BLE001 — a detached conscience is best-effort hardening
            logger.debug("tenant conscience: shared-bus detach failed", exc_info=True)

    def _tenant_provider_set(tenant: str) -> Dict[str, Any]:
        from aureon.operator import keystore as _ks
        from aureon.operator.providers import build_provider_set_from_entries

        return build_provider_set_from_entries(_ks.load(tenant))

    def _lru_put(cache: OrderedDict[str, Any], key: str, value: Any) -> None:
        with _engine_lock:
            cache[key] = value
            cache.move_to_end(key)
            while len(cache) > _TENANT_ENGINE_MAX:
                cache.popitem(last=False)

    def _lru_get(cache: OrderedDict[str, Any], key: str) -> Any:
        """Fetch-and-promote atomically. Returns None on a miss (never raises on a concurrent evict)."""
        with _engine_lock:
            eng = cache.get(key)
            if eng is not None:
                cache.move_to_end(key)
            return eng

    def _invalidate_tenant_engines(tenant: str | None) -> None:
        """Drop a tenant's cached engines so the NEXT request rebuilds from the keystore.

        Called on every tenant credential write/delete: without this a revoked or rotated key
        would keep being spent by a cached engine that still holds the old adapter.
        """
        if tenant is None:
            return
        with _engine_lock:
            _tenant_cog.pop(tenant, None)
            _tenant_op.pop(tenant, None)

    def _tenant_tools() -> Any:
        """The toolbelt a TENANT's engine may use: an ALLOWLIST of pure-compute tools only.

        This is a hard boundary, not a preference. A tenant supplies their own ``base_url``, so the
        model answering their turn is a server THEY control; whatever ``tool_calls`` it returns are
        dispatched on the operator host. The conscience veto runs after the tool loop, so it cannot
        undo a side effect — the tools must never exist.

        A *denylist* is not enough here, and a counter-audit proved it: dropping shell + repo writes
        still left ``web_fetch`` (outbound HTTP from the operator's IP → SSRF onto co-located instance
        services and cloud metadata), ``touch_module`` (import anything), ``publish_thought`` (writes
        the process-global thought bus, going around ``_IsolatedBus``) and the instance's live trading
        state readers. So the belt is pinned positively — see
        :data:`~aureon.operator.tools.TENANT_ALLOWED_TOOLS`.
        """
        from aureon.operator.tools import TENANT_ALLOWED_TOOLS, build_operator_tools

        return build_operator_tools(allow_writes=False, allow_shell=False,
                                    allowlist=TENANT_ALLOWED_TOOLS)

    def _get_cognition_for(tenant: str | None) -> Any:
        if tenant is None:
            return _get_cognition()  # admin / open plane — unchanged
        cached = _lru_get(_tenant_cog, tenant)
        if cached is not None:
            return cached
        providers = _tenant_provider_set(tenant)
        if not providers:
            return None
        from aureon.operator.cognition import AureonCognition

        adapter = next(iter(providers.values()))
        eng = AureonCognition(adapter=adapter, bus=_IsolatedBus(), join_mesh=False,
                              mesh_broadcast=False,
                              conscience=_tenant_plane_conscience(), tools=_tenant_tools(),
                              allow_writes=False, allow_shell=False,
                              allow_repo_grounding=False,
                              allow_organism_context=False,
                              governance_enabled=False,
                              source=f"aureon.cognition.tenant:{_tenant_label(tenant)}")
        _lru_put(_tenant_cog, tenant, eng)
        return eng

    def _get_operator_for(tenant: str | None) -> Any:
        if tenant is None:
            return _operator  # admin / open plane — unchanged
        cached = _lru_get(_tenant_op, tenant)
        if cached is not None:
            return cached
        providers = _tenant_provider_set(tenant)
        if not providers:
            return None
        op = AureonOperator(providers=providers, conscience=_tenant_plane_conscience(), join_mesh=False,
                            mesh_broadcast=False, bus=_IsolatedBus(),
                            allow_repo_grounding=False,
                            source=f"aureon.operator.tenant:{_tenant_label(tenant)}")
        _lru_put(_tenant_op, tenant, op)
        return op

    def _sse(events: Any) -> Any:
        return Response(
            (f"event: {e.get('type','message')}\ndata: {json.dumps(e, default=str)}\n\n" for e in events),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/cognition/stream")
    def cognition_stream():
        prompt = request.args.get("prompt", "").strip()
        session_id = request.args.get("session_id")  # capture before the generator (no request ctx inside gen)
        if not prompt:
            return jsonify({"error": "missing prompt"}), 400
        # Tenant-aware exactly like POST /api/cognition/reason (see that route): the stream must not
        # be a side door onto the instance's models.
        eng = _get_cognition_for(getattr(g, "tenant", None))
        if eng is None:
            return _sse([{"type": "complete", "response": _NO_TENANT_KEY}])
        return _sse(eng.stream_events(prompt, session_id=session_id))

    @app.post("/api/cognition/reason")
    def cognition_reason():
        body: Dict[str, Any] = request.get_json(silent=True) or {}
        prompt = str(body.get("prompt", "")).strip()
        if not prompt:
            return jsonify({"error": "missing prompt"}), 400
        eng = _get_cognition_for(getattr(g, "tenant", None))
        if eng is None:  # signed-in user with no model of their own — honest keyless reply
            return jsonify(_NO_TENANT_KEY)
        return jsonify(eng.reason(prompt, session_id=body.get("session_id")).to_dict())

    # ── Provider API-key management (instance-owned, encrypted keystore) ────────
    # BYO keys for every model. Keys are stored encrypted (keystore.py), masked on
    # read, never logged; writes hot-rebuild the switchboard (no restart).
    from aureon.operator import keystore as _keystore
    from aureon.operator.provider_catalog import CATALOG, get_provider

    def _rebuild_switchboard() -> None:
        _keystore.apply_to_env()
        _operator.providers = build_provider_set()
        _cognition["engine"] = None  # rebuilt lazily on next cognition call

    def _mask_env(value: str) -> str:
        value = str(value or "")
        if not value:
            return ""
        return ("•" * 4) + value[-4:] if len(value) > 4 else "•" * len(value)

    def _provider_view(tenant: str | None = None) -> list:
        # A tenant sees ONLY their own isolated keystore — never the instance env keys. "live" is
        # computed from the plane that will actually answer them: their own tenant provider set when
        # signed in, the shared instance line-up for the admin/global plane (unchanged).
        stored = _keystore.masked_view(tenant)
        if tenant is None:
            live_names = {p["name"] for p in describe_provider_set(_operator.providers)}
        else:
            try:
                live_names = set(_tenant_provider_set(tenant).keys())
            except Exception:  # noqa: BLE001 — an unbuildable entry is simply not live
                live_names = set()
        out = []
        for info in CATALOG:
            s = stored.get(info.id, {})
            env_key = "" if tenant is not None else (os.environ.get(info.key_env, "") if info.key_env else "")
            has_key = bool(s.get("has_key")) or bool(env_key)
            key_masked = s.get("key_masked") or (_mask_env(env_key) if env_key else "")
            source = "keystore" if s.get("has_key") else ("env" if env_key else "none")
            out.append({
                **info.to_public_dict(),
                "model": s.get("model") or info.default_model,
                "base_url": s.get("base_url") or info.default_base_url,
                "has_key": has_key,
                "key_masked": key_masked,
                "key_source": source,
                "enabled": bool(s.get("enabled", True)) if s else True,
                "live": info.registry_name in live_names,
            })
        return out

    @app.get("/api/providers")
    def providers_list():
        return jsonify({"providers": _provider_view(getattr(g, "tenant", None))})

    @app.post("/api/providers/<provider_id>")
    def providers_set(provider_id: str):
        if get_provider(provider_id) is None:
            return _err(404, f"unknown provider: {provider_id}")
        tenant = getattr(g, "tenant", None)
        body: Dict[str, Any] = request.get_json(silent=True) or {}
        try:
            _keystore.save_provider(
                provider_id,
                api_key=body.get("api_key"),
                base_url=body.get("base_url"),
                model=body.get("model"),
                enabled=body.get("enabled"),
                tenant=tenant,
            )
        except KeyError:
            return _err(404, f"unknown provider: {provider_id}")
        # A tenant write must NEVER touch os.environ / the shared switchboard (the leak vector);
        # instead drop their cached engines so the next request rebuilds on the new key.
        if tenant is None:
            _rebuild_switchboard()
        else:
            _invalidate_tenant_engines(tenant)
        view = next((p for p in _provider_view(tenant) if p["id"] == provider_id), None)
        return jsonify({"ok": True, "provider": view})

    @app.delete("/api/providers/<provider_id>")
    def providers_delete(provider_id: str):
        if get_provider(provider_id) is None:
            return _err(404, f"unknown provider: {provider_id}")
        tenant = getattr(g, "tenant", None)
        _keystore.delete_provider(provider_id, tenant=tenant)
        if tenant is None:
            _rebuild_switchboard()
        else:
            _invalidate_tenant_engines(tenant)   # a revoked key must stop being spent immediately
        return jsonify({"ok": True, "provider_id": provider_id})

    def _no_key_verdict(model: str) -> Dict[str, Any]:
        """Honest verdict when a tenant has no key of their own to test.

        We must NOT call an adapter with an empty key: every adapter falls back to the process env
        (``api_key or os.environ.get(...)``), so an empty tenant key would silently spend the
        INSTANCE's credentials and confirm which instance keys are live.
        """
        return {"ok": False, "latency_ms": 0, "model": model, "sample": "",
                "error": "no key stored for your account — add one first"}

    @app.post("/api/providers/<provider_id>/test")
    def providers_test(provider_id: str):
        info = get_provider(provider_id)
        if info is None:
            return _err(404, f"unknown provider: {provider_id}")
        tenant = getattr(g, "tenant", None)
        body: Dict[str, Any] = request.get_json(silent=True) or {}
        stored = _keystore.load(tenant).get(provider_id, {})
        # A tenant tests ONLY their own key — never the instance env key, and never an empty key
        # (which the adapters would resolve from the env).
        env_key = "" if tenant is not None else os.environ.get(info.key_env, "")
        api_key = body.get("api_key") or stored.get("api_key") or env_key
        base_url = body.get("base_url") or stored.get("base_url") or info.default_base_url or None
        model = body.get("model") or stored.get("model") or info.default_model
        if tenant is not None and not str(api_key or "").strip():
            return jsonify(_no_key_verdict(model))
        result = _test_provider_adapter(info, api_key, base_url, model)
        return jsonify(result)

    # ── Feature switchboard (turn every system feature on/off at human discretion) ─
    # Instance-owned, encrypted flag store. Flipping a flag only sets its env var;
    # hard-boundary flags require a typed confirm and NEVER remove a downstream gate
    # (conscience veto / approval queue / runtime dry-run stay in force).
    from aureon.operator import feature_switchboard as _switchboard

    @app.get("/api/switchboard")
    def switchboard_list():
        return jsonify({"groups": _switchboard.grouped_view(), "summary": _switchboard.summary()})

    @app.post("/api/switchboard/<flag_id>")
    def switchboard_set(flag_id: str):
        # Operator-only: flipping a flag writes os.environ, can re-apply the instance's own keys via
        # _rebuild_switchboard, and can arm hard boundaries (e.g. live trading).
        denied = _admin_denied()
        if denied is not None:
            return denied
        flag = _switchboard.get_flag(flag_id)
        if flag is None:
            return _err(404, f"unknown feature flag: {flag_id}")
        body: Dict[str, Any] = request.get_json(silent=True) or {}
        if "enabled" not in body:
            return _err(400, "missing 'enabled'")
        enabled = bool(body.get("enabled"))
        # Hard-boundary flags need an explicit typed-confirm arming gesture.
        if flag.kind == "hard_boundary" and enabled and body.get("confirm") != flag_id:
            return _err(400, "hard-boundary flag requires confirm == flag id", confirm_required=flag_id)
        _switchboard.save_flag(flag_id, enabled)  # persists + applies to os.environ
        # Cognition-routing flags are consumed by the operator's own engine → hot-rebuild.
        if flag_id in _switchboard.LIVE_FLAG_IDS:
            _rebuild_switchboard()
        applied = "applied to the operator now" if flag.effect == "live" else flag.effect_note
        return jsonify({"ok": True, "flag": _switchboard.flag_view(flag), "applied": applied})

    # ── Unified Connections (all external sources: trading → NASA) ──────────────
    from aureon.operator import connections_api as _conn_api
    from aureon.operator.connections_catalog import get_connection as _get_conn

    @app.get("/api/connections")
    def connections_list():
        # `tenant` must reach build_view itself, not just the LLM rows it is handed: the non-LLM
        # (exchange / data-source) rows are built inside from the keystore + os.environ.
        tenant = getattr(g, "tenant", None)
        return jsonify(_json_safe(_conn_api.build_view(_provider_view(tenant), tenant=tenant)))

    @app.get("/api/connections/readiness")
    def connections_readiness():
        tenant = getattr(g, "tenant", None)
        return jsonify(_json_safe(_conn_api.readiness(_provider_view(tenant), tenant=tenant)))

    @app.post("/api/connections/<conn_id>")
    def connections_set(conn_id: str):
        tenant = getattr(g, "tenant", None)
        body: Dict[str, Any] = request.get_json(silent=True) or {}
        api_key = body.get("api_key")
        extra = body.get("extra") or {}
        # LLM provider → keystore (+ switchboard rebuild only on the global/admin plane)
        if get_provider(conn_id) is not None:
            _keystore.save_provider(
                conn_id, api_key=api_key, base_url=body.get("base_url"),
                model=body.get("model"), enabled=body.get("enabled"), tenant=tenant,
            )
            if tenant is None:
                _rebuild_switchboard()
            else:
                _invalidate_tenant_engines(tenant)
            view = next((p for p in _provider_view(tenant) if p["id"] == conn_id), None)
            return jsonify({"ok": True, "connection": view})
        conn = _get_conn(conn_id)
        if conn is None:
            return _err(404, f"unknown connection: {conn_id}")
        # Exchange credentials on the global/admin plane validate + write the instance .env. A tenant
        # instead stores the credential in isolation (never touching the shared .env / os.environ).
        if tenant is None and conn.category == "exchange":
            result = _conn_api.set_exchange_credential(conn, api_key or "", extra)
            code = 200 if result.get("ok") else 502
            return jsonify(result), code
        # data source (or any tenant credential) → keystore; apply_to_env only on the global plane.
        _keystore.save_provider(conn_id, api_key=api_key, enabled=body.get("enabled"),
                                extra=extra, tenant=tenant)
        if tenant is None:
            _keystore.apply_to_env()
        else:
            _invalidate_tenant_engines(tenant)
        return jsonify({"ok": True, "connection": _conn_api.connection_public(
            conn, _keystore.load(tenant), {}, allow_env=tenant is None)})

    @app.post("/api/connections/<conn_id>/test")
    def connections_test(conn_id: str):
        tenant = getattr(g, "tenant", None)
        body: Dict[str, Any] = request.get_json(silent=True) or {}
        # LLM → real prompt round-trip; data source → connectivity probe. A tenant tests ONLY their
        # own stored key — never the instance env key.
        info = get_provider(conn_id)
        if info is not None:
            stored = _keystore.load(tenant).get(conn_id, {})
            env_key = "" if tenant is not None else os.environ.get(info.key_env, "")
            api_key = body.get("api_key") or stored.get("api_key") or env_key
            base_url = body.get("base_url") or stored.get("base_url") or info.default_base_url or None
            model = body.get("model") or stored.get("model") or info.default_model
            if tenant is not None and not str(api_key or "").strip():
                return jsonify(_no_key_verdict(model))   # never let an empty key resolve from env
            return jsonify(_test_provider_adapter(info, api_key, base_url, model))
        conn = _get_conn(conn_id)
        if conn is None:
            return _err(404, f"unknown connection: {conn_id}")
        stored = _keystore.load(tenant).get(conn_id, {})
        env_key = "" if tenant is not None else (os.environ.get(conn.key_env, "") if conn.key_env else "")
        api_key = body.get("api_key") or stored.get("api_key") or env_key
        if tenant is not None and conn.key_env and not str(api_key or "").strip():
            return jsonify({"ok": False, "latency_ms": 0,
                            "error": "no key stored for your account — add one first"})
        return jsonify(_conn_api.probe(conn, api_key))

    # ── Grounded local-machine actions (the organism's hands) ──────────────────
    # Every move is grounded through HNC (Master Formula / Auris) + the Queen's
    # conscience before it can touch the machine, and is DRY-RUN unless armed via
    # AUREON_LOCAL_ACTIONS_ARMED. Under /api/* so the bearer gate protects it.
    try:
        from aureon.operator.local_action_bridge import get_local_action_bridge

        @app.post("/api/action")
        def local_action():
            # Operator-only: this touches the host machine. An end user never gets the hands.
            denied = _admin_denied()
            if denied is not None:
                return denied
            body: Dict[str, Any] = request.get_json(silent=True) or {}
            action = str(body.get("action") or "").strip()
            if not action:
                return _err(400, "missing 'action'")
            bridge = get_local_action_bridge()
            result = bridge.perform(action, body.get("params") or {}, body.get("context") or {})
            return jsonify(_json_safe(result))

        @app.get("/api/action/status")
        def local_action_status():
            bridge = get_local_action_bridge()
            return jsonify(_json_safe({
                "armed": bridge.armed,
                "recent": bridge.recent_stats(),
                "note": "dry-run unless armed; every move grounded through HNC + conscience",
            }))
    except Exception as exc:  # noqa: BLE001 - never sink the app on a wiring error
        logger.warning("local-action routes not registered: %s", exc)

    # ── SaaS platform surface (catalog / domains / status) ─────────────────────
    try:
        from aureon.saas.gateway import register_saas_routes

        register_saas_routes(app)
    except Exception as exc:  # noqa: BLE001 — the operator must serve even if SaaS routes fail
        logger.warning("SaaS gateway routes not registered: %s", exc)

    # ── billing surface (metering + /api/billing) ───────────────────────────────
    try:
        from aureon.saas.billing import register_billing

        register_billing(app)
    except Exception as exc:  # noqa: BLE001 — billing is optional; the operator must serve
        logger.warning("billing routes not registered: %s", exc)

    # ── MCP transport (GET /mcp/tools, POST /mcp/call) ───────────────────────────
    # Attaches Aureon as a live MCP-style server: every tool call is routed through the
    # membrane (ingress screened as data, egress sealed, guarded dispatch). Optional.
    try:
        from aureon.bio.mcp_transport import register_mcp_routes

        register_mcp_routes(app)
    except Exception as exc:  # noqa: BLE001 — the transport is optional; the operator must serve
        logger.warning("MCP transport routes not registered: %s", exc)

    # ── legacy runtime surface (terminal-state / flight-test / bots / trades / …) ─
    # Serves the older trading console's endpoints on the one gateway, read-only/notify-only and
    # honest (real state or an explicit unavailable, never fabricated). Optional.
    try:
        from aureon.operator.legacy_runtime_api import register_legacy_runtime_routes

        register_legacy_runtime_routes(app)
    except Exception as exc:  # noqa: BLE001 — legacy surface is optional; the operator must serve
        logger.warning("legacy runtime routes not registered: %s", exc)

    return app


def build_boot_app():
    """Construct the fully-wired Flask app for production serving.

    Validates config fail-fast, eagerly builds the cognition (so the running
    service joins the mycelium mesh + Queen hive at boot, not lazily), and
    returns the app. Used by both main() and the wsgi module entrypoint.
    """
    _load_env_file()  # deploy-time .env (Ollama base URL / model / key, etc.)
    from aureon.operator.config import OperatorConfig

    OperatorConfig.from_env().validate()  # fail-fast on a bad deploy

    boot_cognition = None
    try:
        from aureon.operator.cognition import AureonCognition

        boot_cognition = AureonCognition(join_mesh=True)
        logger.info("Aureon Cognition wired onto the mesh at startup")
    except Exception as exc:  # noqa: BLE001 — server must still serve if cognition boot fails
        logger.warning("cognition eager-boot skipped: %s", exc)
    # Trace pump: re-fire the subscribe-based cross-process signals (auris cosmic
    # state, lighthouse events) onto THIS process's bus so cognition's live
    # subscribers sense them. Cognition is already wired above, so its handlers
    # exist before the pump seeds current state. Opt out with AUREON_TRACE_PUMP=0.
    if str(os.environ.get("AUREON_TRACE_PUMP", "1")).strip().lower() not in {"0", "false", "no", "off"}:
        try:
            from aureon.core.trace_pump import get_trace_pump

            get_trace_pump().start()
        except Exception as exc:  # noqa: BLE001 — the pump is optional
            logger.warning("trace pump not started: %s", exc)
    # Close the cognitive immune layer's loop: subscribe immune memory to confirmed
    # neutralizations (bio.swarm_defense.run) so a repeat parasite is recognized
    # instantly. The Queen observes on her own channel; the effector stays leaderless.
    if str(os.environ.get("AUREON_IMMUNE_MEMORY", "1")).strip().lower() not in {"0", "false", "no", "off"}:
        try:
            from aureon.bio.immune_memory import install_immune_memory

            install_immune_memory()
        except Exception as exc:  # noqa: BLE001 — the immune memory is optional
            logger.warning("immune memory not installed: %s", exc)
        # The homeostatic brake: a confirmed neutralization registers a cooldown so the layer
        # does not re-attack a just-cleared threat (memory accelerates; regulation restrains).
        try:
            from aureon.bio.immune_regulation import install_immune_regulation

            install_immune_regulation()
        except Exception as exc:  # noqa: BLE001 — the immune regulation is optional
            logger.warning("immune regulation not installed: %s", exc)
    # The static manifests in frontend/public are owned by the repo's manifest
    # pipeline (scripts/validation/generate_*) and checked in with a richer
    # schema; the gateway serves its own live manifests at /api/manifests/<name>.
    # Overwriting the static files at boot is therefore opt-in only.
    if str(os.environ.get("AUREON_WRITE_STATIC_MANIFESTS", "") or "") == "1":
        try:
            from aureon.saas.catalog import write_frontend_manifests

            write_frontend_manifests()
        except Exception as exc:  # noqa: BLE001
            logger.warning("frontend manifest write skipped: %s", exc)
        # publish the full agent-company roster so the (already-mounted) company
        # console lights up with every role from the CEO Goal Steward to the cleaner.
        try:
            from aureon.autonomous.aureon_agent_company_builder import (
                build_and_write_agent_company_bill_list,
            )

            build_and_write_agent_company_bill_list(online=False)
        except Exception as exc:  # noqa: BLE001
            logger.warning("agent-company roster publish skipped: %s", exc)
    return create_app(cognition=boot_cognition)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    _load_env_file()  # deploy-time .env (Ollama base URL / model / key, etc.)
    port = int(os.environ.get("AUREON_OPERATOR_PORT", "8080"))
    host = os.environ.get("AUREON_OPERATOR_HOST", "127.0.0.1")
    from aureon.operator.security import SecurityConfig

    security = SecurityConfig.from_env()
    if not _is_loopback_host(host) and not security.auth_enabled:
        raise RuntimeError("non_loopback_operator_requires_AUREON_OPERATOR_API_KEY")
    logger.info("Aureon Operator server on %s:%s — lines: %s", host, port,
                describe_provider_set(build_provider_set()))
    app = build_boot_app()

    dev = str(os.environ.get("AUREON_OPERATOR_DEV", "")).strip().lower() in {"1", "true", "yes", "on"}
    if dev:
        logger.warning("AUREON_OPERATOR_DEV set — using the Flask dev server (not for production)")
        app.run(host=host, port=port, threaded=True)
        return
    try:
        from waitress import serve  # type: ignore[import-untyped]

        threads = int(os.environ.get("AUREON_OPERATOR_THREADS", "8"))
        logger.info("Serving under waitress (%d threads)", threads)
        serve(app, host=host, port=port, threads=threads)
    except ImportError:
        logger.warning("waitress not installed — falling back to the Flask dev server. "
                       "Install `.[operator]` for production serving.")
        app.run(host=host, port=port, threaded=True)


if __name__ == "__main__":
    main()
