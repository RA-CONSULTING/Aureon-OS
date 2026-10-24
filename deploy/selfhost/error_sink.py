"""Local error sink. Accepts the fusion webhook and a Sentry-style envelope.

Events stay on disk. Nothing is forwarded.
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LOG = Path(os.environ.get("AUREON_ERROR_SINK_PATH", "/tmp/aureon-errors.jsonl"))


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path in {"/", "/health", "/healthz", "/status"}:
            self._send(200, {"status": "ok", "live_trading": False, "may_act": False})
            return
        if path == "/events":
            count = 0
            if LOG.is_file():
                count = sum(1 for line in LOG.read_text(encoding="utf-8").splitlines() if line.strip())
            self._send(200, {"count": count, "live_trading": False})
            return
        self._send(404, {"error": "not_found", "live_trading": False})

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(min(length, 1_000_000))
        try:
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                payload = {"body": payload}
        except (UnicodeError, json.JSONDecodeError):
            payload = {"raw_bytes": len(raw)}
        payload["sink_path"] = self.path.split("?", 1)[0]
        payload["live_trading"] = False
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True, default=str) + "\n")
        self._send(200, {"ok": True, "live_trading": False})

    def log_message(self, fmt: str, *args) -> None:
        return

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    host = os.environ.get("AUREON_ERROR_SINK_BIND", "0.0.0.0")
    port = int(os.environ.get("AUREON_ERROR_SINK_PORT", "8088"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"error sink http://{host}:{port}/  live_trading=false", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
