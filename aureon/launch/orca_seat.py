"""Orca command center seat that answers before the heavy dashboard imports.

The full ``aureon_radar`` command center imports exchanges and scanners at
module level, so a boot that waits for that import never binds 8888. This
seat binds 127.0.0.1 first. Live trading stays off. It does not place an order.
A taken port exits instead of reporting the seat up.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

_HOST = "127.0.0.1"
_HTML: str | None = None
_IMPORT_NOTE = "heavy orca dashboard import has not finished"


class _Server(ThreadingHTTPServer):
    allow_reuse_address = False


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path in {"/health", "/healthz"}:
            raw = json.dumps(
                {
                    "ok": True,
                    "service": "orca_command_center",
                    "listening": True,
                    "live_trading": False,
                    "orders": 0,
                    "dashboard": _IMPORT_NOTE,
                }
            ).encode("utf-8")
            self._send(200, raw, "application/json")
            return
        if path == "/":
            page = _HTML or (
                "<!doctype html><title>Orca Command Center</title>"
                "<p>DRY RUN · LIVE TRADING OFF</p>"
                f"<p>{_IMPORT_NOTE}</p>"
                "<p>No order is placed.</p>"
            )
            self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")
            return
        raw = json.dumps({"ok": False, "live_trading": False, "error": "not_found"}).encode("utf-8")
        self._send(404, raw, "application/json")


def _load_dashboard() -> None:
    global _HTML, _IMPORT_NOTE
    try:
        from aureon_radar.bots.orca_command_center import ORCA_DASHBOARD_HTML

        if isinstance(ORCA_DASHBOARD_HTML, str) and ORCA_DASHBOARD_HTML.strip():
            _HTML = ORCA_DASHBOARD_HTML
            _IMPORT_NOTE = "orca dashboard html loaded; live trading stays off"
            return
        _IMPORT_NOTE = "orca dashboard html was empty; live trading stays off"
    except Exception as exc:
        _IMPORT_NOTE = f"orca dashboard import failed: {exc.__class__.__name__}; live trading stays off"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Orca command center seat")
    parser.add_argument("--port", type=int, default=8888)
    args = parser.parse_args(argv)
    try:
        server = _Server((_HOST, int(args.port)), _Handler)
    except OSError as exc:
        detail = exc.strerror or str(exc)
        print(
            f"orca command center failed to bind {_HOST}:{args.port} ({detail}); live trading stays off",
            file=sys.stderr,
            flush=True,
        )
        return 1
    thread = threading.Thread(target=server.serve_forever, name="orca-seat", daemon=True)
    thread.start()
    print(f"orca command center listening on http://{_HOST}:{args.port}/health", flush=True)
    threading.Thread(target=_load_dashboard, name="orca-dashboard-import", daemon=True).start()
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        server.shutdown()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
