"""Loopback proxy for the seats the 5173 shell shows as tabs.

The gateway binds this surface before the heavy operator import finishes.
Each reading is the upstream's own JSON, or an explicit unavailable reason.
Nothing here invents a number. Live trading stays off. This does not place
an order.
"""

from __future__ import annotations

import json
import os
import socket
import threading
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from flask import Flask, jsonify

_FETCH_TIMEOUT_S = 1.5
_MAX_BYTES = 200_000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# id, label, the separate surface it replaces, upstream URL or None when the
# tab itself is the surface.
SEATS: tuple[dict[str, str | None], ...] = (
    {
        "id": "local-console",
        "label": "Local console",
        "was": "port 8080 dashboard",
        "upstream": None,
    },
    {
        "id": "gateway",
        "label": "Operator gateway",
        "was": "port 8790",
        "upstream": None,
    },
    {
        "id": "circulation",
        "label": "Circulation bus",
        "was": "port 8799",
        "upstream": "http://127.0.0.1:8799/healthz",
    },
    {
        "id": "fusion",
        "label": "Fusion seat",
        "was": "port 8765",
        "upstream": "http://127.0.0.1:8765/healthz",
    },
    {
        "id": "market-status",
        "label": "Market status",
        "was": "port 8791",
        "upstream": "http://127.0.0.1:8791/health",
    },
    {
        "id": "orca",
        "label": "Orca",
        "was": "port 8888",
        "upstream": "http://127.0.0.1:8888/health",
    },
    {
        "id": "neural-canvas",
        "label": "Neural canvas",
        "was": "port 13012",
        "upstream": "http://127.0.0.1:13012/",
    },
    {
        "id": "thought-hub",
        "label": "Thought-action hub",
        "was": "port 13002",
        "upstream": "http://127.0.0.1:13002/",
    },
    {
        "id": "error-sink",
        "label": "Error sink",
        "was": "port 8088",
        "upstream": "http://127.0.0.1:8088/healthz",
    },
    {
        "id": "api-b",
        "label": "API B",
        "was": "port 8766",
        "upstream": "http://127.0.0.1:8766/healthz",
    },
    {
        "id": "frontend",
        "label": "Unified frontend",
        "was": "port 5173",
        "upstream": "http://127.0.0.1:5173/",
    },
    {
        "id": "queen-unified",
        "label": "Queen unified",
        "was": "port 13000 queen unified dashboard",
        "upstream": None,
        "hold": "Off unless AUREON_SIMULATED_BOOT is set. The page draws invented readings, so this tab serves none.",
    },
    {
        "id": "pro-dashboard",
        "label": "Pro dashboard",
        "was": "port 14000 pro dashboard",
        "upstream": None,
        "hold": "Off unless AUREON_SIMULATED_BOOT is set. The page draws invented readings, so this tab serves none.",
    },
    {
        "id": "master-hub",
        "label": "Master hub",
        "was": "port 13333 unified master hub",
        "upstream": None,
        "hold": "Off unless AUREON_SIMULATED_BOOT is set. The page draws invented readings, so this tab serves none.",
    },
    {
        "id": "earth-shield",
        "label": "Earth shield",
        "was": "port 8785 earth shield dashboard",
        "upstream": None,
        "hold": "The Earth shield page runs an ionosphere model. It stays off unless AUREON_SIMULATED_BOOT is set. This tab serves no invented reading.",
    },
    {
        "id": "queen-web",
        "label": "Queen web",
        "was": "port 5000 queen web dashboard",
        "upstream": None,
        "hold": "The queen web server is not started by this boot. This tab does not invent a reading.",
    },
    {
        "id": "system-hub",
        "label": "System hub",
        "was": "port 13001 system hub dashboard",
        "upstream": None,
        "hold": "Retired from this boot. The separate server is not started, so this tab does not report a refused connection. No reading is invented.",
    },
    {
        "id": "bot-hunter",
        "label": "Bot hunter",
        "was": "port 9999 bot hunter dashboard",
        "upstream": None,
        "hold": "Retired from this boot. The separate server is not started, so this tab does not report a refused connection. No reading is invented.",
    },
    {
        "id": "dashboard-api",
        "label": "Dashboard API",
        "was": "port 13334 unified dashboard API",
        "upstream": None,
        "hold": "Retired from this boot. Its command routes are not started, so this tab does not report a refused connection and does not place an order.",
    },
    {
        "id": "queen-power",
        "label": "Queen power",
        "was": "port 8080 queen power dashboard",
        "upstream": None,
        "hold": "Queen power wants port 8080. This boot does not bind 8080. No reading is invented.",
    },
    {
        "id": "trader-local",
        "label": "Trader telemetry",
        "was": "unified market trader local dashboard on 8790",
        "upstream": None,
        "hold": "The trader local page is not started. It would take port 8790 from the gateway and can place an order. No reading is invented.",
    },
    {
        "id": "kraken-local",
        "label": "Kraken telemetry",
        "was": "kraken penny trader local dashboard",
        "upstream": None,
        "hold": "The kraken local page is not started. This boot does not place an order and does not invent a reading.",
    },
    {
        "id": "command-center-legacy",
        "label": "Legacy command center",
        "was": "separate command center UI",
        "upstream": None,
        "hold": "The separate command center stays off unless AUREON_SIMULATED_BOOT is set, because its page draws invented motion. Dashboard and Command Center inside this UI stay at /console/local.",
    },
    {
        "id": "live-bridge",
        "label": "Live Bridge",
        "was": "frontend bridge websocket",
        "upstream": "http://127.0.0.1:8787/health",
    },
)


def seat_by_id(seat_id: str) -> dict[str, str | None] | None:
    for seat in SEATS:
        if seat["id"] == seat_id:
            return seat
    return None


def _reading(
    seat: dict[str, str | None],
    *,
    available: bool,
    reason: str | None,
    payload: Any,
) -> dict[str, Any]:
    return {
        "id": seat["id"],
        "label": seat["label"],
        "was": seat["was"],
        "upstream": seat["upstream"],
        "available": available,
        "reason": reason,
        "fetched_at": _now(),
        "live_trading": False,
        "payload": payload,
    }


def _local_payload(seat_id: str, gateway: "GatewaySwitch | None") -> dict[str, Any]:
    if seat_id == "local-console":
        return {
            "folded_into": "/console/seats?seat=local-console",
            "separate_listener": False,
            "reason": "The 8080 dashboard is this tab. The launcher does not bind 8080.",
        }
    loaded = False if gateway is None else gateway.operator_loaded
    error = None if gateway is None else gateway.operator_error
    return {
        "listening": True,
        "proxy": True,
        "operator_loaded": loaded,
        "operator_error": error,
        "reason": "The gateway is this process. It proxies the other seats.",
    }


def _read_upstream(url: str) -> tuple[int, str, bytes]:
    """GET one loopback URL. This is a status read. It does not place an order."""

    parsed = urlparse(url)
    host = parsed.hostname or "127.0.0.1"
    port = int(parsed.port or (443 if parsed.scheme == "https" else 80))
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    message = (
        f"GET {path} HTTP/1.0\r\n"
        f"Host: {host}\r\n"
        "User-Agent: aureon-seat-proxy\r\n"
        "Connection: close\r\n\r\n"
    )
    with socket.create_connection((host, port), timeout=_FETCH_TIMEOUT_S) as sock:
        sock.settimeout(_FETCH_TIMEOUT_S)
        sock.sendall(message.encode("ascii"))
        chunks: list[bytes] = []
        total = 0
        while total < _MAX_BYTES + 8192:
            block = sock.recv(65536)
            if not block:
                break
            chunks.append(block)
            total += len(block)
    raw = b"".join(chunks)
    head, _, body = raw.partition(b"\r\n\r\n")
    status_line = head.split(b"\r\n", 1)[0].decode("ascii", "replace")
    parts = status_line.split()
    status = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    content_type = ""
    for line in head.split(b"\r\n")[1:]:
        if line.lower().startswith(b"content-type:"):
            content_type = line.split(b":", 1)[1].decode("ascii", "replace").strip()
            break
    return status, content_type, body[:_MAX_BYTES]


def _resolved_upstream(seat: dict[str, str | None]) -> str | None:
    """Honor a taken-port override without rewriting the seat table."""

    seat_id = seat.get("id")
    if seat_id == "market-status":
        override = os.environ.get("AUREON_MARKET_STATUS_URL", "").strip()
        if override:
            return override
    if seat_id == "live-bridge":
        override = os.environ.get("AUREON_FRONTEND_BRIDGE_URL", "").strip()
        if override:
            return override
    upstream = seat.get("upstream")
    return str(upstream) if upstream else None


def read_seat(seat_id: str, gateway: "GatewaySwitch | None" = None) -> dict[str, Any]:
    """Read one seat. A missed upstream is unavailable, with the reason."""

    seat = seat_by_id(seat_id)
    if seat is None:
        return {
            "id": seat_id,
            "available": False,
            "reason": "unknown seat",
            "fetched_at": _now(),
            "live_trading": False,
            "payload": None,
        }
    hold = seat.get("hold")
    if hold:
        return _reading(seat, available=False, reason=str(hold), payload=None)
    upstream = _resolved_upstream(seat)
    if upstream:
        seat = dict(seat)
        seat["upstream"] = upstream
    if not upstream:
        return _reading(seat, available=True, reason=None, payload=_local_payload(seat_id, gateway))
    try:
        status, content_type, raw = _read_upstream(str(upstream))
    except Exception as exc:
        return _reading(
            seat,
            available=False,
            reason=f"{exc.__class__.__name__}: {exc}",
            payload=None,
        )
    if status >= 400:
        return _reading(seat, available=False, reason=f"upstream HTTP {status}", payload=None)
    text = raw.decode("utf-8", errors="replace")
    if "json" in content_type or text[:1] in "{[":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return _reading(seat, available=False, reason="upstream body is not JSON", payload=None)
        return _reading(seat, available=True, reason=None, payload=payload)
    return _reading(
        seat,
        available=True,
        reason=None,
        payload={"content_type": content_type or "text/html", "bytes": len(raw)},
    )


def catalog() -> dict[str, Any]:
    return {
        "live_trading": False,
        "fetched_at": _now(),
        "ui": "http://127.0.0.1:5173/console/seats",
        "seats": [
            {"id": seat["id"], "label": seat["label"], "was": seat["was"], "tab": f"/console/seats?seat={seat['id']}"}
            for seat in SEATS
        ],
    }


ACTIVE_GATEWAY: "GatewaySwitch | None" = None


def register_seat_routes(app: Flask, gateway: "GatewaySwitch | None" = None) -> None:
    @app.get("/api/seats")
    def seats_index():
        return jsonify(catalog())

    @app.get("/api/seats/<seat_id>")
    def seats_one(seat_id: str):
        current = gateway if gateway is not None else ACTIVE_GATEWAY
        reading = read_seat(seat_id, current)
        code = 200 if seat_by_id(seat_id) else 404
        return jsonify(reading), code


def build_early_app(gateway: "GatewaySwitch | None" = None) -> Flask:
    """Health and seat proxy only. The full operator app may replace this later."""

    app = Flask("aureon-seat-gateway")

    @app.get("/healthz")
    def healthz():
        loaded = False if gateway is None else gateway.operator_loaded
        return jsonify(
            {
                "ok": True,
                "service": "aureon-operator",
                "listening": True,
                "proxy": True,
                "operator_loaded": loaded,
                "live_trading": False,
                "orders": 0,
            }
        )

    register_seat_routes(app, gateway)
    return app


class GatewaySwitch:
    """WSGI app that answers immediately and can later hand off to the full operator."""

    def __init__(self, app: Any) -> None:
        self._app = app
        self.operator_loaded = False
        self.operator_error: str | None = None
        self._lock = threading.Lock()

    def swap(self, app: Any) -> None:
        with self._lock:
            self._app = app
            self.operator_loaded = True
            self.operator_error = None

    def fail(self, exc: BaseException) -> None:
        with self._lock:
            self.operator_loaded = False
            self.operator_error = f"{exc.__class__.__name__}: {exc}"

    def __call__(self, environ: dict, start_response: Any) -> Any:
        with self._lock:
            app = self._app
        return app(environ, start_response)
