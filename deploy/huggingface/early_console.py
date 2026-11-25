"""Immediate, read-only liveness and organism console for the public Space.

Starts before model loading. Strict /readyz remains with the aggregate service;
this service exposes no prompts, credentials, tools, or internal proxy routes.
"""

from __future__ import annotations

import html
import json
import os
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

HOST = "127.0.0.1"
PORT = 7860
MAX_READ_BYTES = 512 * 1024
STATUS_URL = os.environ.get("AUREON_CONSOLE_STATUS_URL", "http://127.0.0.1:8792/readyz")


def public_status() -> dict[str, Any]:
    """Read only the existing public readiness payload; never expose internals."""
    try:
        request = urllib.request.Request(STATUS_URL, headers={"Accept": "application/json"})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=0.5) as response:
            raw = response.read(MAX_READ_BYTES + 1)
            if len(raw) > MAX_READ_BYTES:
                raise ValueError("oversized_public_status")
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("invalid_public_status")
        return {
            "state": "ready" if payload.get("ready") is True else "starting",
            "ready": payload.get("ready") is True,
            "checks": payload.get("checks") if isinstance(payload.get("checks"), dict) else {},
            "organism": payload.get("organism") if isinstance(payload.get("organism"), dict) else {},
        }
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read(MAX_READ_BYTES + 1)
            payload = json.loads(raw.decode("utf-8")) if len(raw) <= MAX_READ_BYTES else {}
        except (UnicodeError, json.JSONDecodeError):
            payload = {}
        return {
            "state": "starting" if exc.code == 503 else "blocked",
            "ready": False,
            "http_status": exc.code,
            "checks": payload.get("checks") if isinstance(payload, dict) else {},
            "organism": payload.get("organism") if isinstance(payload, dict) else {},
        }
    except (OSError, ValueError, UnicodeError) as exc:
        return {
            "state": "starting", "ready": False, "blocker": type(exc).__name__,
            "checks": {}, "organism": {},
        }


def _gear_cards(payload: dict[str, Any]) -> str:
    evidence = payload.get("organism")
    if not isinstance(evidence, dict):
        evidence = {}
    gears = evidence.get("gears") if isinstance(evidence.get("gears"), list) else []
    gears = gears if isinstance(gears, list) else []
    cards: list[str] = []
    for gear in gears[:3]:
        if not isinstance(gear, dict):
            continue
        name = str(gear.get("name", "unknown"))
        if name not in {"field", "auris", "qgita"}:
            continue
        label = "Engaged" if gear.get("engaged") is True else "No data / held"
        details = []
        for key, display in (("coherence_gamma", "Γ"), ("lambda_t", "Λ")):
            value = gear.get(key)
            if type(value) in (int, float):
                details.append(f"{display} {value:.3f}")
        if name == "auris":
            grounded = gear.get("grounded_inputs")
            total = gear.get("total_inputs")
            if type(grounded) is int and type(total) is int:
                details.append(f"{grounded}/{total} grounded inputs")
        cards.append(
            f"<article class='card {'ready' if gear.get('engaged') is True else 'wait'}'>"
            f"<h2>{html.escape(name.upper() if name != 'field' else 'HNC field')}</h2>"
            f"<p>{html.escape(label)}</p><small>{html.escape(' · '.join(details))}</small></article>"
        )
    return "".join(cards)


def render_cards(payload: dict[str, Any]) -> str:
    checks = payload.get("checks") if isinstance(payload.get("checks"), dict) else {}
    if not isinstance(checks, dict):
        checks = {}
    cards: list[str] = []
    for name in ("operator", "model", "public_posture", "organism"):
        reading = checks.get(name)
        reading = reading if isinstance(reading, dict) else {}
        value = reading.get("ok", reading.get("ready"))
        label = "Ready" if value is True else "Blocked" if payload.get("state") == "blocked" else "Starting / unavailable"
        cards.append(
            f"<article class='card {'ready' if value is True else 'wait'}' data-component='{html.escape(name)}'>"
            f"<h2>{html.escape(name.replace('_', ' ').title())}</h2>"
            f"<p>{html.escape(label)}</p></article>"
        )
    return "".join(cards)


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="5"><title>Aureon OS — Organism status</title>
<style>
:root{color-scheme:dark;background:#080c17;color:#ecf2ff;font-family:system-ui,sans-serif}
body{max-width:1080px;margin:0 auto;padding:clamp(20px,5vw,56px)}
header{display:flex;align-items:center;gap:14px}h1{font-size:clamp(24px,4vw,40px);margin:0}
.mark{width:20px;height:20px;border:4px solid #e9c767;border-radius:50%}
.eyebrow{color:#95a8cb;letter-spacing:.16em;text-transform:uppercase;font-size:12px}
.lead{color:#c6d3ea;max-width:65ch;line-height:1.65}.panel{border:1px solid #263754;border-radius:16px;
padding:20px;background:#111a2b;margin:22px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.card{background:#0b1323;border:1px solid #2a3a55;border-radius:12px;padding:16px}.card h2{font-size:16px}
.card p{font-size:20px;font-weight:650}.wait p{color:#e9c767}.ready p{color:#82e5c4}
a{color:#a8c7fa;margin-right:20px}footer{color:#95a8cb;font-size:13px;line-height:1.6}
</style></head><body>
<header><div class="mark"></div><div><div class="eyebrow">Aureon OS · live organism</div>
<h1>HNC / Auris / QGITA</h1></div></header>
<p class="lead">The console starts before the model. Strict readiness requires the verified Aureon 7B,
HNC evidence and operator. Missing evidence stays visible rather than becoming a false healthy status.</p>
<div class="panel"><strong>__STATE__</strong><p>__DETAIL__</p></div>
<div class="grid">__CARDS__</div><div class="panel"><a href="/hnc/">HNC evidence</a><a href="/app/">Full console</a>
<p>Read-only. No live trading, credentials, terminal or external mutations.</p></div>
<div class="panel"><strong>Isambard compute</strong><p>No verified public status bridge is configured.
This Space cannot directly inspect the cluster queue or storage.</p></div>
<footer>Automatic refresh every five seconds. Liveness is not model readiness.</footer></body></html>
"""


class ConsoleHandler(BaseHTTPRequestHandler):
    """Three GET/HEAD routes. Request logging and all mutations are disabled."""

    def log_message(self, _format: str, *args: Any) -> None:
        del args

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/healthz":
            body = json.dumps({
                "ok": True, "service": "aureon-public-console", "live_trading": False,
            }).encode("utf-8")
            self._send(200, body, "application/json")
            return
        if self.path == "/api/console/status":
            self._send(200, json.dumps(public_status(), allow_nan=False).encode(), "application/json")
            return
        if self.path == "/":
            status = public_status()
            ready = status.get("ready") is True
            text = PAGE.replace(
                "__STATE__", "All systems ready" if ready else "Organism is starting / evidence unavailable"
            ).replace(
                "__DETAIL__", html.escape(
                    "The verified model and operator are ready." if ready else
                    "The console is live; strict model or organism readiness is unavailable."
                )
            ).replace("__CARDS__", render_cards(status))
            self._send(200, text.encode("utf-8"), "text/html; charset=utf-8")
            return
        self._send(404, b'{"error":"not_found"}', "application/json")

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET()

    def _reject(self) -> None:
        self._send(405, b'{"error":"method_not_allowed"}', "application/json")

    do_POST = _reject
    do_PUT = _reject
    do_PATCH = _reject
    do_DELETE = _reject
    do_OPTIONS = _reject
    do_TRACE = _reject
    do_CONNECT = _reject


def bind() -> ThreadingHTTPServer:
    """Bind synchronously before any GPU/model startup can block or fail."""
    server = ThreadingHTTPServer((HOST, PORT), ConsoleHandler)
    server.daemon_threads = True
    return server


def serve(server: ThreadingHTTPServer | None = None) -> None:
    server = server or bind()
    threading.Thread(target=server.serve_forever, daemon=True, name="public-console-http").start()
    print("[early-console] listening on 127.0.0.1:7860; strict readiness is separate", flush=True)
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    serve()
