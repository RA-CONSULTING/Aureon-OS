"""Status listener for the thought-action hub port.

The hub's goal loop can pursue a trade, so this boot does not start it.
The port still answers /health. Live trading stays off. No order is placed.
"""

from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

_HOST = "127.0.0.1"


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path not in {"/", "/health", "/healthz", "/status"}:
            body = json.dumps({"ok": False, "error": "not_found", "live_trading": False}).encode("utf-8")
            self._send(404, body)
            return
        body = json.dumps(
            {
                "ok": True,
                "service": "thought-action-hub",
                "status": "goal loop is not started",
                "reason": "The thought-action hub goal loop can pursue trading, so this listener is status only.",
                "goal_loop": False,
                "live_trading": False,
                "orders": 0,
            }
        ).encode("utf-8")
        self._send(200, body)

    def _send(self, code: int, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Thought-action hub status route")
    parser.add_argument("--port", type=int, default=13002)
    args = parser.parse_args(argv)
    try:
        server = ThreadingHTTPServer((_HOST, int(args.port)), _Handler)
    except OSError as exc:
        print(
            f"thought-action hub status failed to bind {_HOST}:{args.port} ({exc.strerror or exc})",
            file=sys.stderr,
            flush=True,
        )
        return 1
    print(f"thought-action hub status listening on http://{_HOST}:{args.port}/health", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
