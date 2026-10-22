"""Fusion HTTP surface.

/healthz and /readyz are unauthenticated so a load balancer can probe them.
Every other route requires Authorization: Bearer $AUREON_FUSION_API_TOKEN.
The process refuses to start when that token is missing, and it never places
an order. Live trading stays off.
"""

from __future__ import annotations

import hashlib
import hmac
import html
import json
import os
import sys
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .errors import capture_exception
from .join import status_report
from .logging_json import log_event

_CACHE: dict[str, Any] = {"at": 0.0, "body": None}
_HITS: dict[str, deque[float]] = defaultdict(deque)


def token_from_env() -> str:
    token = os.environ.get("AUREON_FUSION_API_TOKEN", "")
    if len(token) < 16:
        raise RuntimeError("AUREON_FUSION_API_TOKEN must be set to at least 16 characters")
    return token


def live_trading_armed() -> bool:
    return os.environ.get("AUREON_LIVE_TRADING", "0") == "1" or os.environ.get("AUREON_FUSION_ARM_LIVE") == "1"


def rate_limit() -> int:
    raw = os.environ.get("AUREON_FUSION_RATE_LIMIT", "60")
    try:
        return max(1, int(raw))
    except ValueError:
        return 60


def window_seconds() -> float:
    raw = os.environ.get("AUREON_FUSION_RATE_WINDOW_S", "60")
    try:
        return max(0.1, float(raw))
    except ValueError:
        return 60.0


def allow(client: str, now: float | None = None) -> bool:
    moment = time.monotonic() if now is None else now
    bucket = _HITS[client]
    span = window_seconds()
    while bucket and moment - bucket[0] > span:
        bucket.popleft()
    if len(bucket) >= rate_limit():
        return False
    bucket.append(moment)
    return True


def reset_limits() -> None:
    _HITS.clear()
    _CACHE["at"] = 0.0
    _CACHE["body"] = None


def authorized(header: str, token: str) -> bool:
    scheme, _, presented = header.partition(" ")
    if scheme != "Bearer" or not presented:
        presented = ""
    return hmac.compare_digest(
        hashlib.sha256(presented.encode("utf-8")).digest(),
        hashlib.sha256(token.encode("utf-8")).digest(),
    )


def cached_status() -> dict[str, Any]:
    ttl = float(os.environ.get("AUREON_FUSION_CACHE_TTL_S", "5"))
    now = time.monotonic()
    if _CACHE["body"] is not None and now - float(_CACHE["at"]) < ttl:
        body = dict(_CACHE["body"])
        body["cache"] = "hit"
        return body
    body = status_report()
    body["cache"] = "miss"
    body["live_trading"] = False
    _CACHE["at"] = now
    _CACHE["body"] = body
    return body


def render_page(report: dict[str, Any]) -> bytes:
    rows = []
    for name, info in report["capabilities"].items():
        state = "present" if info["present"] else "missing"
        rows.append(
            "<tr><td>{}</td><td>{}</td><td><code>{}</code></td></tr>".format(
                html.escape(str(name)),
                html.escape(state),
                html.escape(str(info["path"])),
            )
        )
    missing = "".join(
        "<li><code>{}</code> — {}</li>".format(html.escape(item["repo"]), html.escape(item["reason"]))
        for item in report["unavailable_sources"]
    )
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Aureon Fusion — dry run</title>
<style>
  body {{ font-family: Georgia, serif; background:#0e1412; color:#e7efe9; margin:0; }}
  header {{ padding:28px 32px; background:#143028; border-bottom:4px solid #d4a017; }}
  h1 {{ margin:0 0 8px; font-weight:500; }}
  .hold {{ display:inline-block; background:#d4a017; color:#1a1200; padding:4px 10px; font-family:sans-serif; font-size:13px; }}
  main {{ padding:24px 32px 48px; max-width:980px; }}
  table {{ border-collapse:collapse; width:100%; }}
  td, th {{ border-bottom:1px solid #2a4036; text-align:left; padding:8px 10px; font-family:ui-monospace,monospace; font-size:14px; }}
</style>
</head>
<body>
<header>
  <div class="hold">DRY RUN · LIVE TRADING OFF · PAPER DEFAULT</div>
  <h1>Aureon Fusion</h1>
  <p>Authenticated status page. This process does not place orders.</p>
</header>
<main>
  <p>may_act = false · action gate = HOLD</p>
  <table>
    <thead><tr><th>Capability</th><th>State</th><th>Path</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
  <h2>Sources not retrieved</h2>
  <ul>{missing}</ul>
</main>
</body>
</html>
"""
    return page.encode("utf-8")


def make_handler(token: str):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self):  # noqa: N802
            started = time.perf_counter()
            status = 500
            try:
                status = self._dispatch()
            except Exception as exc:
                capture_exception(exc, path=self.path.split("?", 1)[0], method="GET")
                status = self._send(500, {"error": "internal", "live_trading": False})
            log_event(
                "info",
                "request",
                method="GET",
                path=self.path.split("?", 1)[0],
                status=status,
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                client=self.client_address[0],
            )

        def log_message(self, fmt: str, *args) -> None:
            return

        def _dispatch(self) -> int:
            path = self.path.split("?", 1)[0]
            if path not in {"/healthz", "/readyz"} and not allow(self.client_address[0]):
                self.send_response(429)
                self.send_header("Content-Type", "application/json")
                self.send_header("Retry-After", "1")
                body = b'{"error":"rate_limited","live_trading":false}'
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return 429
            if path == "/healthz":
                return self._send(200, {"status": "ok", "live_trading": False, "paper_default": True})
            if path == "/readyz":
                report = cached_status()
                ready = all(item["present"] for item in report["capabilities"].values())
                return self._send(200 if ready else 503, {"ready": ready, "live_trading": False})
            if not authorized(self.headers.get("Authorization", ""), token):
                return self._send(401, {"error": "unauthorized", "live_trading": False})
            if path == "/api/status":
                return self._send(200, cached_status())
            if path == "/error-test":
                raise RuntimeError("fusion_error_sink_test")
            if path in {"/", "/index.html"}:
                body = render_page(cached_status())
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "private, max-age=0")
                self.end_headers()
                self.wfile.write(body)
                return 200
            return self._send(404, {"error": "not_found", "live_trading": False})

        def _send(self, status: int, payload: dict[str, Any]) -> int:
            body = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "private, max-age=0")
            self.end_headers()
            self.wfile.write(body)
            return status

    return Handler


def serve(port: int | None = None) -> ThreadingHTTPServer:
    if live_trading_armed():
        raise RuntimeError("refusing to start: live trading flags are set; this service stays disarmed")
    token = token_from_env()
    bind = os.environ.get("AUREON_FUSION_BIND", "127.0.0.1")
    chosen = port if port is not None else int(os.environ.get("AUREON_FUSION_PORT", "8765"))
    server = ThreadingHTTPServer((bind, chosen), make_handler(token))
    log_event("info", "listen", bind=bind, port=chosen, live_trading=False)
    return server


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--once" in args:
        token_from_env()
        print("fusion http config ok; live_trading=false")
        return 0
    try:
        server = serve()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Aureon Fusion http://{server.server_address[0]}:{server.server_address[1]}/  live_trading=false")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
