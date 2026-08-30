"""
Aureon Operator — legacy runtime API surface.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The older trading console (``frontend/src/App.tsx`` + ``frontend/src/components/``) calls a handful of
endpoints that historically lived on a *standalone* status server (``unified_market_status_server`` on
``127.0.0.1:8790``). Through the operator those paths 404'd, so the console fell back to the local port
that isn't up in a hosted SaaS deploy.

This module mounts those endpoints on the operator Flask app so the one gateway serves the whole console.
Everything here is **read-only or notify-only** and **honest**: it delegates to the existing pure
handlers in ``unified_market_status_server`` (which already return truthful "booting / stale /
unavailable" payloads when the live trader hasn't written ``state/*.json``), and where no real data
source exists it returns an explicit empty/`unavailable` shape — **never a fabricated value**.

``register_legacy_runtime_routes(app)`` follows the same guarded-registration idiom as the SaaS gateway
and MCP transport: an import/wiring failure logs a warning and the operator still serves.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable, Dict, Tuple

logger = logging.getLogger("aureon.operator.legacy_runtime_api")

# Env names for the (optional) Telegram notify path — already a registered operator connection.
_TG_TOKEN_ENV = "TELEGRAM_BOT_TOKEN"
_TG_CHAT_ENV = "TELEGRAM_CHAT_ID"


def _status_handlers() -> Tuple[Callable[[], Dict[str, Any]], ...]:
    """Import the pure, import-safe handlers from the standalone status server (socket only binds under
    ``__main__``). Returns ``(read_status, flight_test, env_credentials_status)`` or raises."""
    from aureon.exchanges.unified_market_status_server import (
        _env_credentials_status,
        _flight_test,
        _read_status,
    )

    return _read_status, _flight_test, _env_credentials_status


def _unavailable(reason: str, exc: Exception | None = None) -> Dict[str, Any]:
    """Honest 'this subsystem isn't reachable right now' payload — never fabricated data."""
    payload: Dict[str, Any] = {"ok": False, "available": False, "reason": reason}
    if exc is not None:
        payload["error"] = str(exc)[:200]
    return payload


def _send_telegram(token: str, chat_id: str, message: str, parse_mode: str = "Markdown") -> Dict[str, Any]:
    """Send one Telegram message via the real Bot API (stdlib only). Honest on failure; never fakes ok."""
    import json
    import urllib.request

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = json.dumps({"chat_id": chat_id, "text": message, "parse_mode": parse_mode}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 - fixed api.telegram.org host
        ok = 200 <= resp.status < 300
        return {"ok": ok, "status": resp.status}


def register_legacy_runtime_routes(app: Any) -> int:
    """Mount the legacy runtime endpoints on a Flask app. Returns the number of routes added (0 on
    failure). Idempotent-safe under the operator's guarded registration."""
    try:
        from flask import jsonify, request
    except Exception:  # noqa: BLE001 - no Flask → no routes, but import stays safe
        return 0

    def _terminal_state() -> Any:
        try:
            read_status, _flight, _env = _status_handlers()
            return jsonify(read_status())
        except Exception as exc:  # noqa: BLE001 - degrade honestly, never 500
            logger.debug("terminal-state unavailable: %s", exc)
            return jsonify(_unavailable("runtime status server unavailable", exc))

    def _flight_test_route() -> Any:
        try:
            _read, flight_test, _env = _status_handlers()
            return jsonify(flight_test())
        except Exception as exc:  # noqa: BLE001
            logger.debug("flight-test unavailable: %s", exc)
            return jsonify(_unavailable("flight test unavailable", exc))

    def _reboot_advice() -> Any:
        # The standalone server serves the same flight-test payload here; the console reads its
        # ``reboot_advice`` sub-object. Mirror that exactly.
        try:
            _read, flight_test, _env = _status_handlers()
            return jsonify(flight_test())
        except Exception as exc:  # noqa: BLE001
            logger.debug("reboot-advice unavailable: %s", exc)
            return jsonify(_unavailable("reboot advice unavailable", exc))

    def _env_credentials() -> Any:
        # Operator-only: this enumerates the INSTANCE's exchange-credential posture — which of the
        # operator's keys are configured and their masked tails. Masked or not, it is the instance's
        # security state, not the user's, and it tells a tenant exactly which live venues to target.
        from flask import g

        if not getattr(g, "is_admin", True):
            return jsonify({"ok": False, "reason": "the instance credential posture is operator-only",
                            "plane": "admin"}), 403
        try:
            _read, _flight, env_credentials_status = _status_handlers()
            return jsonify(env_credentials_status())  # masked; metadata_only_no_values_returned
        except Exception as exc:  # noqa: BLE001
            logger.debug("env-credentials unavailable: %s", exc)
            return jsonify(_unavailable("env credentials unavailable", exc))

    def _bots() -> Any:
        # No {name, tail[]} process-log source is wired on the operator; report honestly empty rather
        # than invent tails. The console already renders "No bots reporting yet." for an empty list.
        return jsonify({"bots": [], "note": "no per-bot log tail source wired on the operator"})

    def _trades() -> Any:
        # No symbol-keyed trade list source exists offline; report honestly empty. NEVER mock:true with
        # fabricated trades — the console renders "No trades available." for an empty map.
        return jsonify({"trades": {}, "note": "no symbol-keyed trade source wired on the operator"})

    def _notifications_telegram() -> Any:
        # Operator-only: the fallback credentials are the INSTANCE's Telegram bot. A signed-in end
        # user must not send from the operator's identity (they may still pass their own botToken).
        # g.is_admin is set by the operator gate; absent (bare app / tests) ⇒ permissive, unchanged.
        from flask import g

        body = request.get_json(silent=True) or {}
        own_token = str(body.get("botToken") or "").strip()
        if not getattr(g, "is_admin", True) and not own_token:
            return jsonify({"ok": False, "reason": "sending from the instance's Telegram bot is "
                                                   "operator-only; supply your own botToken"}), 403
        token = str(body.get("botToken") or os.environ.get(_TG_TOKEN_ENV, "")).strip()
        chat_id = str(body.get("chatId") or os.environ.get(_TG_CHAT_ENV, "")).strip()
        message = str(body.get("message") or "").strip()
        parse_mode = str(body.get("parseMode") or "Markdown")
        if not message:
            return jsonify({"ok": False, "reason": "missing message"}), 400
        if not token or not chat_id:
            # Honest 'not configured' — never fake a successful send.
            return jsonify({"ok": False, "reason": "telegram not configured"}), 503
        try:
            result = _send_telegram(token, chat_id, message, parse_mode)
            return jsonify(result), (200 if result.get("ok") else 502)
        except Exception as exc:  # noqa: BLE001 - upstream failure, reported honestly
            logger.debug("telegram send failed: %s", exc)
            return jsonify({"ok": False, "reason": "telegram send failed", "error": str(exc)[:200]}), 502

    routes = (
        ("/api/terminal-state", "legacy_terminal_state", _terminal_state, ["GET"]),
        ("/api/flight-test", "legacy_flight_test", _flight_test_route, ["GET"]),
        ("/api/reboot-advice", "legacy_reboot_advice", _reboot_advice, ["GET"]),
        ("/api/env-credentials", "legacy_env_credentials", _env_credentials, ["GET"]),
        ("/api/bots", "legacy_bots", _bots, ["GET"]),
        ("/api/trades", "legacy_trades", _trades, ["GET"]),
        ("/api/notifications/telegram", "legacy_notifications_telegram", _notifications_telegram, ["POST"]),
    )
    added = 0
    for rule, endpoint, view, methods in routes:
        app.add_url_rule(rule, endpoint, view, methods=methods)
        added += 1
    return added


__all__ = ["register_legacy_runtime_routes"]
