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
  python -m aureon.operator.operator_server          # binds 0.0.0.0:8080
  AUREON_OPERATOR_PORT=8899 python -m aureon.operator.operator_server

Reaching it from a phone: this repo usually runs in a remote container, so open
the deployed/tunnelled URL on the phone (see the deployment section of
docs/architecture/AUREON_OPERATOR_SWITCHBOARD.md), not localhost.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger("aureon.operator.server")


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
    from flask import Flask, Response, jsonify, request, send_from_directory
except Exception as exc:  # noqa: BLE001
    raise SystemExit(
        "Flask is required for the operator server (it is in requirements.txt): "
        f"{exc}"
    ) from exc

from aureon.operator.aureon_operator import AureonOperator  # noqa: E402  (after guarded flask import)
from aureon.operator.providers import build_provider_set, describe_provider_set  # noqa: E402

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
        kind = info.kind
        if kind in ("openai", "openai_compat"):
            from aureon.operator.providers import AureonOpenAIAdapter

            adapter = AureonOpenAIAdapter(api_key=api_key, base_url=base_url, model=model)
        elif kind == "grok":
            from aureon.operator.providers import AureonGrokAdapter

            adapter = AureonGrokAdapter(api_key=api_key, base_url=base_url, model=model)
        elif kind == "gemini":
            from aureon.operator.providers import AureonGeminiAdapter

            adapter = AureonGeminiAdapter(api_key=api_key, model=model, base_url=base_url)
        elif kind == "anthropic":
            from aureon.inhouse_ai.llm_adapter import AureonAnthropicAdapter

            adapter = AureonAnthropicAdapter(api_key=api_key, model=model)
        else:  # local / self-hosted (Ollama)
            from aureon.inhouse_ai.llm_adapter import AureonLocalAdapter

            adapter = AureonLocalAdapter(api_key=api_key, base_url=base_url, model=model)

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
        return {"ok": False, "latency_ms": 0, "model": model, "sample": "",
                "error": f"{type(exc).__name__}: {str(exc)[:140]}"}


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


def create_app(operator: AureonOperator | None = None, cognition: Any = None) -> Flask:
    app = Flask("aureon-operator")
    _operator = operator or AureonOperator()

    # ── Security envelope (auth + rate limit + body cap; off by default) ───────
    from aureon.operator.security import SecurityConfig, TokenBucket, check_bearer

    _sec = SecurityConfig.from_env()
    _bucket = TokenBucket(_sec.rate_rps, _sec.burst)
    app.config["MAX_CONTENT_LENGTH"] = _sec.max_body_bytes
    _OPEN_PATHS = ("/", "/healthz", "/readyz", "/metrics", "/favicon.ico")

    def _err(code: int, message: str, **extra):
        return jsonify({"error": {"code": code, "message": message, **extra}}), code

    @app.before_request
    def _gate():
        path = request.path
        if path in _OPEN_PATHS or not path.startswith("/api/"):
            return None
        if _sec.auth_enabled and not check_bearer(request.headers.get("Authorization"), _sec.api_key):
            return _err(401, "missing or invalid bearer token")
        if _sec.rate_enabled:
            client = request.headers.get("X-Forwarded-For", request.remote_addr or "anon").split(",")[0].strip()
            ok, retry = _bucket.check(client)
            if not ok:
                resp = _err(429, "rate limit exceeded", retry_after=retry)
                resp[0].headers["Retry-After"] = str(int(retry) + 1)
                return resp
        return None

    @app.errorhandler(400)
    def _400(e):
        return _err(400, "bad request")

    @app.errorhandler(404)
    def _404(e):
        return _err(404, "not found")

    @app.errorhandler(413)
    def _413(e):
        return _err(413, f"request body exceeds {_sec.max_body_bytes} bytes")

    @app.errorhandler(500)
    def _500(e):
        logger.exception("unhandled server error")
        return _err(500, "internal server error")

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
            out["status"] = {"status": "unknown", "error": str(exc)[:200]}
        try:
            from aureon.saas.gateway import build_organism_payload

            out["organism"] = build_organism_payload()
        except Exception as exc:  # noqa: BLE001
            out["organism"] = {"available": False, "error": str(exc)[:200]}
        try:  # the human control plane's safety posture, at a glance
            from aureon.operator import feature_switchboard as _sb

            out["switchboard"] = _sb.summary()
        except Exception as exc:  # noqa: BLE001
            out["switchboard"] = {"error": str(exc)[:200]}
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
            checks["repo_index_error"] = str(exc)
        checks["cognition"] = _cognition["engine"] is not None
        try:
            from aureon.operator.connections_api import _real_data_policy_summary

            checks["real_data_policy"] = _real_data_policy_summary()
        except Exception as exc:  # noqa: BLE001
            checks["real_data_policy"] = {"probe_report_status": "unavailable", "error": str(exc)[:160]}
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

        def gen():
            for event in _operator.stream_events(prompt, session_id=session_id):
                etype = event.get("type", "message")
                yield f"event: {etype}\ndata: {json.dumps(event, default=str)}\n\n"

        return Response(
            gen(),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.post("/api/operator/respond")
    def respond():
        body: Dict[str, Any] = request.get_json(silent=True) or {}
        prompt = str(body.get("prompt", "")).strip()
        if not prompt:
            return jsonify({"error": "missing prompt"}), 400
        resp = _operator.respond(prompt, session_id=body.get("session_id"))
        return jsonify(resp.to_dict())

    # ── Agentic cognition mode (tools + repo-wide grounding + veto) ────────────
    _cognition = {"engine": cognition}

    def _get_cognition():
        if _cognition["engine"] is None:
            from aureon.operator.cognition import AureonCognition

            _cognition["engine"] = AureonCognition(join_mesh=True)
        return _cognition["engine"]

    @app.get("/api/cognition/stream")
    def cognition_stream():
        prompt = request.args.get("prompt", "").strip()
        session_id = request.args.get("session_id")  # capture before the generator (no request ctx inside gen)
        if not prompt:
            return jsonify({"error": "missing prompt"}), 400

        def gen():
            for event in _get_cognition().stream_events(prompt, session_id=session_id):
                yield f"event: {event.get('type','message')}\ndata: {json.dumps(event, default=str)}\n\n"

        return Response(gen(), mimetype="text/event-stream",
                        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.post("/api/cognition/reason")
    def cognition_reason():
        body: Dict[str, Any] = request.get_json(silent=True) or {}
        prompt = str(body.get("prompt", "")).strip()
        if not prompt:
            return jsonify({"error": "missing prompt"}), 400
        return jsonify(_get_cognition().reason(prompt, session_id=body.get("session_id")).to_dict())

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

    def _provider_view() -> list:
        stored = _keystore.masked_view()
        live_names = {p["name"] for p in describe_provider_set(_operator.providers)}
        out = []
        for info in CATALOG:
            s = stored.get(info.id, {})
            env_key = os.environ.get(info.key_env, "") if info.key_env else ""
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
        return jsonify({"providers": _provider_view()})

    @app.post("/api/providers/<provider_id>")
    def providers_set(provider_id: str):
        if get_provider(provider_id) is None:
            return _err(404, f"unknown provider: {provider_id}")
        body: Dict[str, Any] = request.get_json(silent=True) or {}
        try:
            _keystore.save_provider(
                provider_id,
                api_key=body.get("api_key"),
                base_url=body.get("base_url"),
                model=body.get("model"),
                enabled=body.get("enabled"),
            )
        except KeyError:
            return _err(404, f"unknown provider: {provider_id}")
        _rebuild_switchboard()
        view = next((p for p in _provider_view() if p["id"] == provider_id), None)
        return jsonify({"ok": True, "provider": view})

    @app.delete("/api/providers/<provider_id>")
    def providers_delete(provider_id: str):
        if get_provider(provider_id) is None:
            return _err(404, f"unknown provider: {provider_id}")
        _keystore.delete_provider(provider_id)
        _rebuild_switchboard()
        return jsonify({"ok": True, "provider_id": provider_id})

    @app.post("/api/providers/<provider_id>/test")
    def providers_test(provider_id: str):
        info = get_provider(provider_id)
        if info is None:
            return _err(404, f"unknown provider: {provider_id}")
        body: Dict[str, Any] = request.get_json(silent=True) or {}
        stored = _keystore.load().get(provider_id, {})
        api_key = body.get("api_key") or stored.get("api_key") or os.environ.get(info.key_env, "")
        base_url = body.get("base_url") or stored.get("base_url") or info.default_base_url or None
        model = body.get("model") or stored.get("model") or info.default_model
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
        return jsonify(_json_safe(_conn_api.build_view(_provider_view())))

    @app.get("/api/connections/readiness")
    def connections_readiness():
        return jsonify(_json_safe(_conn_api.readiness(_provider_view())))

    @app.post("/api/connections/<conn_id>")
    def connections_set(conn_id: str):
        body: Dict[str, Any] = request.get_json(silent=True) or {}
        api_key = body.get("api_key")
        extra = body.get("extra") or {}
        # LLM provider → keystore + switchboard rebuild (same as /api/providers)
        if get_provider(conn_id) is not None:
            _keystore.save_provider(
                conn_id, api_key=api_key, base_url=body.get("base_url"),
                model=body.get("model"), enabled=body.get("enabled"),
            )
            _rebuild_switchboard()
            view = next((p for p in _provider_view() if p["id"] == conn_id), None)
            return jsonify({"ok": True, "connection": view})
        conn = _get_conn(conn_id)
        if conn is None:
            return _err(404, f"unknown connection: {conn_id}")
        if conn.category == "exchange":
            result = _conn_api.set_exchange_credential(conn, api_key or "", extra)
            code = 200 if result.get("ok") else 502
            return jsonify(result), code
        # operator-consumed data source → keystore + env
        _keystore.save_provider(conn_id, api_key=api_key, enabled=body.get("enabled"), extra=extra)
        _keystore.apply_to_env()
        return jsonify({"ok": True, "connection": _conn_api.connection_public(
            conn, _keystore.load(), {})})

    @app.post("/api/connections/<conn_id>/test")
    def connections_test(conn_id: str):
        body: Dict[str, Any] = request.get_json(silent=True) or {}
        # LLM → real prompt round-trip; data source → connectivity probe
        info = get_provider(conn_id)
        if info is not None:
            stored = _keystore.load().get(conn_id, {})
            api_key = body.get("api_key") or stored.get("api_key") or os.environ.get(info.key_env, "")
            base_url = body.get("base_url") or stored.get("base_url") or info.default_base_url or None
            model = body.get("model") or stored.get("model") or info.default_model
            return jsonify(_test_provider_adapter(info, api_key, base_url, model))
        conn = _get_conn(conn_id)
        if conn is None:
            return _err(404, f"unknown connection: {conn_id}")
        stored = _keystore.load().get(conn_id, {})
        api_key = body.get("api_key") or stored.get("api_key") or (
            os.environ.get(conn.key_env, "") if conn.key_env else "")
        return jsonify(_conn_api.probe(conn, api_key))

    # ── Grounded local-machine actions (the organism's hands) ──────────────────
    # Every move is grounded through HNC (Master Formula / Auris) + the Queen's
    # conscience before it can touch the machine, and is DRY-RUN unless armed via
    # AUREON_LOCAL_ACTIONS_ARMED. Under /api/* so the bearer gate protects it.
    try:
        from aureon.operator.local_action_bridge import get_local_action_bridge

        @app.post("/api/action")
        def local_action():
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
    host = os.environ.get("AUREON_OPERATOR_HOST", "0.0.0.0")
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
