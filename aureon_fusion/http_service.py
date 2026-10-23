"""Fusion HTTP surface.

/healthz and /readyz are unauthenticated so a load balancer can probe them.
Every other route requires Authorization: Bearer $AUREON_FUSION_API_TOKEN.
The process refuses to start when that token is missing, and it never places
an order. Live trading follows the process environment: on when the launcher
saw exchange keys, paper/public-data otherwise.
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


def authority_flags() -> dict[str, bool]:
    """Live flag and may_act. Guarded mode and the kill switch stay disarmed."""

    try:
        from aureon.autonomous.autonomy_mode import runtime_authority

        auth = runtime_authority()
        return {
            "live_trading": auth.get("live_trading") is True,
            "may_act": auth.get("may_act") is True,
        }
    except Exception:
        return {"live_trading": False, "may_act": False}


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
    _CACHE["redis"] = None


def _redis_client():
    """Shared cache. Absent URL or a dead server keeps the in-process cache."""

    url = os.environ.get("AUREON_REDIS_URL", "").strip()
    if not url:
        return None
    cached = _CACHE.get("redis")
    if cached is not None:
        return cached
    try:
        import redis
    except ImportError:
        return None
    try:
        client = redis.Redis.from_url(url, socket_timeout=0.3, socket_connect_timeout=0.3)
        client.ping()
    except Exception:
        return None
    _CACHE["redis"] = client
    return client


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
    client = _redis_client()
    if client is not None:
        try:
            raw = client.get("aureon:fusion:status")
        except Exception:
            raw = None
        if raw:
            try:
                saved = json.loads(raw)
                if time.time() - float(saved["at"]) < ttl:
                    body = dict(saved["body"])
                    body["cache"] = "hit"
                    body["cache_layer"] = "redis"
                    flags = authority_flags()
                    body["live_trading"] = flags["live_trading"]
                    body["may_act"] = flags["may_act"]
                    return body
            except (TypeError, ValueError, json.JSONDecodeError):
                pass
        body = status_report()
        body["cache"] = "miss"
        body["cache_layer"] = "redis"
        flags = authority_flags()
        body["live_trading"] = flags["live_trading"]
        body["may_act"] = flags["may_act"]
        try:
            client.set(
                "aureon:fusion:status",
                json.dumps({"at": time.time(), "body": body}, sort_keys=True),
                ex=max(1, int(ttl)),
            )
        except Exception:
            pass
        return body
    now = time.monotonic()
    if _CACHE["body"] is not None and now - float(_CACHE["at"]) < ttl:
        body = dict(_CACHE["body"])
        body["cache"] = "hit"
        flags = authority_flags()
        body["live_trading"] = flags["live_trading"]
        body["may_act"] = flags["may_act"]
        body["paper_default"] = not flags["live_trading"]
        body["dry_run_default"] = not flags["live_trading"]
        body["action_eligible"] = flags["may_act"]
        return body
    body = status_report()
    body["cache"] = "miss"
    flags = authority_flags()
    body["live_trading"] = flags["live_trading"]
    body["may_act"] = flags["may_act"]
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
    if report.get("live_trading"):
        banner = "LIVE · EXCHANGE KEYS PRESENT"
    elif report.get("may_act"):
        banner = "PAPER / PUBLIC DATA · NO EXCHANGE KEYS"
    else:
        banner = "DRY RUN · LIVE TRADING OFF · PAPER DEFAULT"
    gate_line = (
        "may_act = true · action gate = RELEASE"
        if report.get("may_act")
        else "may_act = false · action gate = HOLD"
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
  <div class="hold">{banner}</div>
  <h1>Aureon Fusion</h1>
  <p>Authenticated status page. This process does not place orders.</p>
</header>
<main>
  <p>{gate_line}</p>
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
                flags = authority_flags()
                return self._send(
                    200,
                    {
                        "status": "ok",
                        "live_trading": flags["live_trading"],
                        "paper_default": not flags["live_trading"],
                        "may_act": flags["may_act"],
                        "hosting": "self-hosted",
                        "replica": os.environ.get("AUREON_REPLICA_ID", "single"),
                    },
                )
            if path == "/readyz":
                report = cached_status()
                ready = all(item["present"] for item in report["capabilities"].values())
                return self._send(
                    200 if ready else 503,
                    {"ready": ready, "live_trading": authority_flags()["live_trading"]},
                )
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
    from aureon.autonomous.autonomy_mode import autonomy_mode

    if live_trading_armed() and autonomy_mode() != "full":
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
