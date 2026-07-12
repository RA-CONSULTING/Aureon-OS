"""
📡 Aureon Operator server — SSE stream + phone proof-of-concept.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A tiny Flask app so the switchboard can be *seen*, live, from a phone — the
"operator will be like streaming YouTube… you talk and it's a live stream"
part of the vision.

Routes:
  GET  /                       mobile-responsive chat page (self-contained HTML)
  GET  /api/operator/stream    Server-Sent Events: phases, then the answer token-by-token
  POST /api/operator/respond   one-shot JSON (OperatorResponse.to_dict())
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

try:
    from flask import Flask, Response, jsonify, request
except Exception as exc:  # noqa: BLE001
    raise SystemExit(
        "Flask is required for the operator server (it is in requirements.txt): "
        f"{exc}"
    ) from exc

from aureon.operator.aureon_operator import AureonOperator  # noqa: E402  (after guarded flask import)
from aureon.operator.providers import build_provider_set, describe_provider_set  # noqa: E402

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
        if not prompt:
            return jsonify({"error": "missing prompt"}), 400

        def gen():
            for event in _get_cognition().stream_events(prompt, session_id=request.args.get("session_id")):
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

    # ── SaaS platform surface (catalog / domains / status) ─────────────────────
    try:
        from aureon.saas.gateway import register_saas_routes

        register_saas_routes(app)
    except Exception as exc:  # noqa: BLE001 — the operator must serve even if SaaS routes fail
        logger.warning("SaaS gateway routes not registered: %s", exc)

    return app


def build_boot_app():
    """Construct the fully-wired Flask app for production serving.

    Validates config fail-fast, eagerly builds the cognition (so the running
    service joins the mycelium mesh + Queen hive at boot, not lazily), and
    returns the app. Used by both main() and the wsgi module entrypoint.
    """
    from aureon.operator.config import OperatorConfig

    OperatorConfig.from_env().validate()  # fail-fast on a bad deploy

    boot_cognition = None
    try:
        from aureon.operator.cognition import AureonCognition

        boot_cognition = AureonCognition(join_mesh=True)
        logger.info("Aureon Cognition wired onto the mesh at startup")
    except Exception as exc:  # noqa: BLE001 — server must still serve if cognition boot fails
        logger.warning("cognition eager-boot skipped: %s", exc)
    # Write the frontend catalog manifests at boot so the console has data.
    try:
        from aureon.saas.catalog import write_frontend_manifests

        write_frontend_manifests()
    except Exception as exc:  # noqa: BLE001
        logger.warning("frontend manifest write skipped: %s", exc)
    return create_app(cognition=boot_cognition)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
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
