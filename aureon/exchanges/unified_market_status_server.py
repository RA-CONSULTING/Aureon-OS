"""Read-only local status API for the unified market runtime.

This server starts before the heavy trading/cognitive runtime. It gives the
frontend a stable heartbeat while the full trader imports, wires cognition, and
connects exchanges. The trader keeps writing state/unified_runtime_status.json;
this process only serves that file and never places orders.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from aureon.core.aureon_env import apply_env_aliases, env_presence
from aureon.harmonic.hnc_quantum_packet_crypto import (
    LEGACY_MASTER_KEY_ENV,
    MASTER_KEY_ENV,
    encode_env_packet,
    env_packet_summary,
    is_env_packet,
    packet_master_key_from_env,
    write_hnc_packet_evidence,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_ROOT = REPO_ROOT / "state"
STATUS_PATH = REPO_ROOT / "state" / "unified_runtime_status.json"
MARKET_INTENT_PATH = STATE_ROOT / "aureon_market_reboot_intent.json"
ENV_UPDATE_INTENT_PATH = STATE_ROOT / "aureon_env_update_intent.json"
HNC_PACKET_EVIDENCE_PATH = STATE_ROOT / "aureon_hnc_quantum_packet_last_run.json"
ENV_PATH = Path(os.getenv("AUREON_ENV_FILE") or (REPO_ROOT / ".env")).expanduser()
HOST = "127.0.0.1"
STATUS_FILE_STALE_AFTER_SEC = float(os.getenv("UNIFIED_STATUS_FILE_STALE_AFTER_SEC", "60") or 60)
TICK_STALE_AFTER_SEC = float(os.getenv("UNIFIED_READY_STALE_AFTER_SEC", "45") or 45)
TICK_RUNNING_STALE_AFTER_SEC = max(
    TICK_STALE_AFTER_SEC,
    float(os.getenv("UNIFIED_TICK_RUNNING_STALE_AFTER_SEC", "600") or 600),
)

EXCHANGE_ENV_FIELDS: dict[str, tuple[str, ...]] = {
    "binance": ("BINANCE_API_KEY", "BINANCE_API_SECRET"),
    "kraken": ("KRAKEN_API_KEY", "KRAKEN_API_SECRET"),
    "alpaca": ("ALPACA_API_KEY", "ALPACA_SECRET_KEY"),
    "capital": ("CAPITAL_API_KEY", "CAPITAL_IDENTIFIER", "CAPITAL_PASSWORD"),
}

FRIENDLY_CREDENTIAL_KEYS: dict[str, dict[str, str]] = {
    "binance": {"binanceApiKey": "BINANCE_API_KEY", "binanceApiSecret": "BINANCE_API_SECRET"},
    "kraken": {"krakenApiKey": "KRAKEN_API_KEY", "krakenApiSecret": "KRAKEN_API_SECRET"},
    "alpaca": {"alpacaApiKey": "ALPACA_API_KEY", "alpacaSecretKey": "ALPACA_SECRET_KEY"},
    "capital": {
        "capitalApiKey": "CAPITAL_API_KEY",
        "capitalIdentifier": "CAPITAL_IDENTIFIER",
        "capitalPassword": "CAPITAL_PASSWORD",
    },
}

ENV_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


def _parse_iso_timestamp(value: Any) -> float:
    if not value:
        return 0.0
    try:
        text = str(value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text).timestamp()
    except Exception:
        return 0.0


def _runtime_watchdog(payload: dict[str, Any], status_file_age_sec: float | None = None) -> dict[str, Any]:
    existing = payload.get("runtime_watchdog")
    if isinstance(existing, dict):
        watchdog = dict(existing)
    else:
        watchdog = {}

    now = time.time()
    last_completed_ts = _parse_iso_timestamp(payload.get("last_tick_completed_at"))
    last_started_ts = _parse_iso_timestamp(payload.get("last_tick_started_at"))
    last_tick_age_sec = payload.get("last_tick_age_sec")
    try:
        last_tick_age = float(last_tick_age_sec) if last_tick_age_sec is not None else (now - last_completed_ts if last_completed_ts else None)
    except Exception:
        last_tick_age = None
    tick_running_sec = max(0.0, now - last_started_ts) if last_started_ts > last_completed_ts else 0.0

    existing_reason = str(payload.get("stale_reason") or watchdog.get("tick_stale_reason") or "")
    active_tick = bool(last_started_ts > last_completed_ts)
    stale_reason = ""
    tick_stale = False
    if not active_tick and last_tick_age is not None and last_tick_age > TICK_STALE_AFTER_SEC:
        tick_stale = True
        stale_reason = "last_tick_age_exceeded"
    if active_tick and tick_running_sec > TICK_RUNNING_STALE_AFTER_SEC:
        tick_stale = True
        stale_reason = "tick_in_progress_stalled"
    if not tick_stale and existing_reason not in {"", "last_tick_age_exceeded", "tick_in_progress_stalled"}:
        tick_stale = bool(payload.get("stale") or watchdog.get("tick_stale"))
        stale_reason = existing_reason

    status_file_fresh = status_file_age_sec is None or status_file_age_sec <= STATUS_FILE_STALE_AFTER_SEC
    open_positions = _has_open_positions(payload)
    severity = "critical" if tick_stale and open_positions else "degraded" if tick_stale else "healthy"
    recovery_action = (
        "preserve_position_monitoring_and_defer_restart_until_flat_downtime"
        if tick_stale and open_positions
        else "restart_in_downtime_window"
        if tick_stale
        else "none"
    )

    watchdog.update(
        {
            "status_file_fresh": status_file_fresh,
            "status_file_age_sec": round(float(status_file_age_sec), 3) if status_file_age_sec is not None else None,
            "heartbeat_fresh_but_tick_stale": bool(status_file_fresh and tick_stale),
            "tick_stale": tick_stale,
            "tick_stale_reason": stale_reason,
            "tick_stale_after_sec": TICK_STALE_AFTER_SEC,
            "tick_active": active_tick,
            "tick_long_running": bool(active_tick and tick_running_sec > TICK_STALE_AFTER_SEC),
            "tick_running_stale_after_sec": TICK_RUNNING_STALE_AFTER_SEC,
            "last_tick_age_sec": round(float(last_tick_age), 3) if last_tick_age is not None else None,
            "last_tick_running_sec": round(float(tick_running_sec), 3) if tick_running_sec > 0 else 0.0,
            "open_positions": open_positions,
            "severity": severity,
            "recovery_action": recovery_action,
        }
    )
    return watchdog


def _read_status() -> dict[str, Any]:
    if STATUS_PATH.exists():
        try:
            with STATUS_PATH.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if isinstance(payload, dict):
                stat = STATUS_PATH.stat()
                age_sec = max(0.0, time.time() - stat.st_mtime)
                payload.setdefault("ok", True)
                payload.setdefault("source", "unified-market-status-server")
                payload.setdefault(
                    "generated_at",
                    payload.get("dashboard_generated_at")
                    or payload.get("last_tick_completed_at")
                    or datetime.fromtimestamp(stat.st_mtime).isoformat(),
                )
                payload["status_file"] = str(STATUS_PATH)
                payload["status_file_mtime"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
                payload["status_file_age_sec"] = round(age_sec, 3)
                payload["runtime_watchdog"] = _runtime_watchdog(payload, age_sec)
                if payload["runtime_watchdog"].get("tick_stale"):
                    payload["stale"] = True
                    payload["stale_reason"] = payload["runtime_watchdog"].get("tick_stale_reason")
                elif str(payload.get("stale_reason") or "") in {"last_tick_age_exceeded", "tick_in_progress_stalled"}:
                    payload["stale"] = False
                    payload["stale_reason"] = ""
                if (
                    not payload.get("stale")
                    and bool(payload.get("trading_ready"))
                    and bool(payload.get("data_ready"))
                    and not bool(payload.get("duplicate_runtime"))
                ):
                    payload["ok"] = True
                if age_sec > STATUS_FILE_STALE_AFTER_SEC:
                    payload["stale"] = True
                    payload.setdefault("warnings", [])
                    if isinstance(payload["warnings"], list):
                        payload["warnings"].append("runtime_status_file_stale")
                return payload
        except Exception as exc:
            return {
                "ok": False,
                "source": "unified-market-status-server",
                "error": f"status_file_read_failed: {exc}",
                "status_file": str(STATUS_PATH),
                "generated_at": datetime.now().isoformat(),
            }

    return {
        "ok": True,
        "source": "unified-market-status-server",
        "generated_at": datetime.now().isoformat(),
        "service": "unified-market-trader",
        "trading_ready": False,
        "data_ready": False,
        "stale": True,
        "lines": "UNIFIED MARKET STATUS | Runtime status server is awake. Trader is still booting.",
        "terminal_lines": [
            "UNIFIED MARKET STATUS",
            "Runtime status server is awake.",
            "Trader is still booting and wiring exchange/cognitive systems.",
        ],
        "status_file": str(STATUS_PATH),
        "combined": {
            "open_positions": 0,
            "kraken_equity": 0.0,
            "capital_equity_gbp": 0.0,
        },
        "exchanges": {
            "kraken_ready": False,
            "capital_ready": False,
            "alpaca_ready": False,
            "binance_ready": False,
        },
    }


def _day_allowed(day_name: str, allowed_days: str | None) -> bool:
    raw = (allowed_days or "Sun").strip().lower()
    if raw in {"*", "all", "daily", "everyday"}:
        return True
    names = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    current = day_name[:3].lower()
    for part in raw.replace(";", ",").split(","):
        item = part.strip()
        if not item:
            continue
        if item == current or item == day_name.lower():
            return True
        if "-" in item:
            start_raw, end_raw = [piece.strip()[:3].lower() for piece in item.split("-", 1)]
            if start_raw in names and end_raw in names and current in names:
                start = names.index(start_raw)
                end = names.index(end_raw)
                now = names.index(current)
                if start <= end and start <= now <= end:
                    return True
                if start > end and (now >= start or now <= end):
                    return True
    return False


def _parse_clock(value: str | None, fallback: str) -> tuple[int, int]:
    raw = value or fallback
    try:
        hour_raw, minute_raw = raw.split(":", 1)
        return max(0, min(23, int(hour_raw))), max(0, min(59, int(minute_raw)))
    except Exception:
        hour_raw, minute_raw = fallback.split(":", 1)
        return int(hour_raw), int(minute_raw)


def _market_downtime_window() -> bool:
    days = os.getenv("AUREON_MARKET_DOWNTIME_DAYS") or os.getenv("AUREON_MIND_DOWNTIME_DAYS") or "Sun"
    start_h, start_m = _parse_clock(
        os.getenv("AUREON_MARKET_DOWNTIME_START_LOCAL") or os.getenv("AUREON_MIND_DOWNTIME_START_LOCAL"),
        "03:00",
    )
    end_h, end_m = _parse_clock(
        os.getenv("AUREON_MARKET_DOWNTIME_END_LOCAL") or os.getenv("AUREON_MIND_DOWNTIME_END_LOCAL"),
        "03:15",
    )
    now = datetime.now()
    start = now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
    end = now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
    if end <= start:
        end += timedelta(days=1)
    if _day_allowed(now.strftime("%A"), days) and start <= now < end:
        return True
    if end_h < start_h or (end_h == start_h and end_m <= start_m):
        yesterday = now - timedelta(days=1)
        previous_start = start - timedelta(days=1)
        previous_end = end - timedelta(days=1)
        if _day_allowed(yesterday.strftime("%A"), days) and previous_start <= now < previous_end:
            return True
    return False


def _read_market_intent() -> dict[str, Any] | None:
    try:
        if not MARKET_INTENT_PATH.exists():
            return None
        payload = json.loads(MARKET_INTENT_PATH.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    except Exception:
        return None
    return None


def _read_env_update_intent() -> dict[str, Any] | None:
    try:
        if not ENV_UPDATE_INTENT_PATH.exists():
            return None
        payload = json.loads(ENV_UPDATE_INTENT_PATH.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    except Exception:
        return None
    return None


def _parse_env_values(path: Path | None = None) -> dict[str, str]:
    target = path or ENV_PATH
    values: dict[str, str] = {}
    if not target.exists():
        return values
    for raw_line in target.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not ENV_KEY_RE.match(key):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def _quote_env_value(value: str) -> str:
    text = str(value)
    if not text:
        return ""
    if any(ch.isspace() for ch in text) or "#" in text or '"' in text or "'" in text:
        return json.dumps(text)
    return text


def _env_packet_master_key(env_values: dict[str, str] | None = None) -> str:
    values = env_values or _parse_env_values()
    return packet_master_key_from_env(os.environ) or str(values.get(MASTER_KEY_ENV) or values.get(LEGACY_MASTER_KEY_ENV) or "").strip()


def _packetize_env_updates(updates: dict[str, str]) -> tuple[dict[str, str], list[str], dict[str, Any] | None]:
    master_key = _env_packet_master_key()
    if not master_key:
        return dict(updates), [], None
    stored: dict[str, str] = {}
    encrypted_keys: list[str] = []
    summaries: dict[str, Any] = {}
    for key, value in updates.items():
        token = encode_env_packet(value, master_key, env_key=key)
        stored[key] = token
        encrypted_keys.append(key)
        summaries[key] = env_packet_summary(token)
    evidence = {
        "event": "env_credentials_packetized",
        "updated_keys": sorted(updates),
        "encrypted_keys": sorted(encrypted_keys),
        "packet_format": "hncqp1",
        "packet_summaries": summaries,
    }
    write_hnc_packet_evidence(evidence, HNC_PACKET_EVIDENCE_PATH)
    return stored, sorted(encrypted_keys), evidence


def _write_env_updates(updates: dict[str, str]) -> dict[str, Any]:
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing_text = ENV_PATH.read_text(encoding="utf-8", errors="replace") if ENV_PATH.exists() else ""
    lines = existing_text.splitlines()
    updated_keys = set(updates)
    stored_updates, encrypted_keys, packet_evidence = _packetize_env_updates(updates)
    written: set[str] = set()
    output: list[str] = []
    for raw_line in lines:
        stripped = raw_line.strip()
        prefix = ""
        check_line = stripped
        if check_line.startswith("export "):
            prefix = "export "
            check_line = check_line[len("export ") :].strip()
        if "=" in check_line:
            key = check_line.split("=", 1)[0].strip()
            if key in stored_updates:
                output.append(f"{prefix}{key}={_quote_env_value(stored_updates[key])}")
                written.add(key)
                continue
        output.append(raw_line)
    missing = [key for key in stored_updates if key not in written]
    if missing and output and output[-1].strip():
        output.append("")
    for key in missing:
        output.append(f"{key}={_quote_env_value(stored_updates[key])}")

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_path = None
    if ENV_PATH.exists():
        backup_path = ENV_PATH.with_name(f"{ENV_PATH.name}.bak-{timestamp}")
        shutil.copy2(ENV_PATH, backup_path)
    temp_path = ENV_PATH.with_name(f"{ENV_PATH.name}.tmp-{timestamp}")
    temp_path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
    os.replace(temp_path, ENV_PATH)
    for key, value in updates.items():
        os.environ[key] = value
    apply_env_aliases(os.environ, override=False)
    return {
        "env_file": str(ENV_PATH),
        "backup_file": str(backup_path) if backup_path else None,
        "updated_keys": sorted(updated_keys),
        "hnc_packet_encrypted_keys": encrypted_keys,
        "hnc_packet_evidence": packet_evidence,
    }


def _env_credentials_status() -> dict[str, Any]:
    env_values = _parse_env_values()
    apply_env_aliases(env_values, override=False)
    master_key = _env_packet_master_key(env_values)
    packet_encoded_keys = sorted(key for key, value in env_values.items() if is_env_packet(value))
    exchanges: dict[str, Any] = {}
    for exchange, keys in EXCHANGE_ENV_FIELDS.items():
        presence = env_presence(keys, env_values)
        missing = [key for key, meta in presence.items() if not meta.get("set")]
        exchanges[exchange] = {
            "present": not missing,
            "missing_keys": missing,
            "keys": presence,
        }
    intent = _read_env_update_intent()
    pending_restart = bool(intent and intent.get("status") == "pending")
    return {
        "ok": True,
        "service": "unified-market-status-server",
        "generated_at": datetime.now().isoformat(),
        "env_file": str(ENV_PATH),
        "env_file_exists": ENV_PATH.exists(),
        "writable": ENV_PATH.exists() and os.access(ENV_PATH, os.W_OK) or os.access(ENV_PATH.parent, os.W_OK),
        "exchanges": exchanges,
        "restart_required": pending_restart,
        "restart_intent": intent,
        "hnc_packet_encryption": {
            "enabled": bool(master_key),
            "format": "hncqp1",
            "encoded_key_count": len(packet_encoded_keys),
            "encoded_keys": packet_encoded_keys,
            "master_key_present": bool(master_key),
            "evidence_file": str(HNC_PACKET_EVIDENCE_PATH),
            "policy": "new local credential writes are packet-encrypted at rest when AUREON_HNC_PACKET_MASTER_KEY is present",
            "secret_policy": "metadata_only_no_values_returned",
        },
        "secret_policy": "metadata_only_no_values_returned",
    }


def _extract_env_updates(exchange: str, credentials: dict[str, Any]) -> dict[str, str]:
    normalized = exchange.strip().lower()
    if normalized not in EXCHANGE_ENV_FIELDS:
        raise ValueError(f"unsupported_exchange:{exchange}")
    allowed = set(EXCHANGE_ENV_FIELDS[normalized])
    friendly = FRIENDLY_CREDENTIAL_KEYS.get(normalized, {})
    updates: dict[str, str] = {}
    for raw_key, raw_value in credentials.items():
        key = friendly.get(str(raw_key), str(raw_key))
        if key not in allowed:
            continue
        value = str(raw_value or "").strip()
        if value:
            updates[key] = value
    if not updates:
        raise ValueError("no_supported_non_empty_credentials")
    return updates


def _record_env_update_intent(exchange: str, updated_keys: list[str]) -> dict[str, Any]:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "pending",
        "surface": "env_credentials",
        "exchange": exchange,
        "reason": "credentials_updated_from_local_console",
        "updated_keys": sorted(updated_keys),
        "env_file": str(ENV_PATH),
        "restart_required": True,
        "created_at": datetime.now().isoformat(),
        "secret_policy": "metadata_only_no_values_returned",
    }
    ENV_UPDATE_INTENT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    market_payload = {
        "status": "pending",
        "surface": "market",
        "requested_by": "unified-market-status-server",
        "reason": "env_credentials_updated_from_local_console",
        "change_id": f"env_credentials_{exchange}",
        "updated_keys": sorted(updated_keys),
        "requested_at": datetime.now().isoformat(),
        "policy": "restart only when runtime is live, configured downtime window is active, and no open positions are reported",
        "secret_policy": "metadata_only_no_values_returned",
    }
    MARKET_INTENT_PATH.write_text(json.dumps(market_payload, indent=2), encoding="utf-8")
    return payload


def _has_open_positions(payload: dict[str, Any]) -> bool:
    combined = payload.get("combined")
    if isinstance(combined, dict):
        try:
            return int(combined.get("open_positions", 0) or 0) > 0
        except Exception:
            return True
    positions = payload.get("positions")
    if isinstance(positions, list):
        return len(positions) > 0
    return True


def _flight_test() -> dict[str, Any]:
    status = _read_status()
    intent = _read_market_intent()
    env_intent = _read_env_update_intent()
    pending_restart = bool(intent and intent.get("status") == "pending") or bool(env_intent and env_intent.get("status") == "pending")
    watchdog = status.get("runtime_watchdog") if isinstance(status.get("runtime_watchdog"), dict) else _runtime_watchdog(status)
    stale = bool(status.get("stale") or watchdog.get("tick_stale"))
    open_positions = _has_open_positions(status)
    downtime = _market_downtime_window()
    should_reboot = pending_restart or stale
    can_reboot_now = bool(should_reboot and downtime and not open_positions)
    if can_reboot_now:
        reason = "downtime_window_active_and_no_open_positions"
    elif stale and open_positions:
        reason = "runtime_tick_stale_with_open_positions"
    elif open_positions:
        reason = "open_positions_reported"
    elif not downtime:
        reason = "outside_market_downtime_window"
    elif stale:
        reason = "runtime_tick_stale"
    else:
        reason = "no_restart_needed"

    return {
        "ok": bool(status.get("ok")) and not stale,
        "service": "unified-market-status-server",
        "generated_at": datetime.now().isoformat(),
        "checks": {
            "status_file_exists": STATUS_PATH.exists(),
            "runtime_ok": bool(status.get("ok")),
            "trading_ready": bool(status.get("trading_ready")),
            "data_ready": bool(status.get("data_ready")),
            "tick_fresh": not stale,
            "heartbeat_fresh_but_tick_stale": bool(watchdog.get("heartbeat_fresh_but_tick_stale")),
            "open_positions": open_positions,
            "downtime_window": downtime,
            "pending_restart": pending_restart,
        },
        "reboot_advice": {
            "surface": "market",
            "should_reboot": should_reboot,
            "can_reboot_now": can_reboot_now,
            "decision": (
                "reboot_now"
                if can_reboot_now
                else "hold_monitor_positions"
                if stale and open_positions
                else ("hold" if should_reboot else "none")
            ),
            "reason": reason,
            "recovery_action": watchdog.get("recovery_action"),
        },
        "intent": intent,
        "env_update_intent": env_intent,
        "runtime": {
            "last_tick_started_at": status.get("last_tick_started_at"),
            "last_tick_completed_at": status.get("last_tick_completed_at"),
            "last_tick_age_sec": status.get("last_tick_age_sec"),
            "last_tick_running_sec": status.get("last_tick_running_sec"),
            "runtime_watchdog": watchdog,
            "combined": status.get("combined"),
            "exchanges": status.get("exchanges"),
        },
    }


class StatusHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:
        if self.path in {"/", "/health", "/api/terminal-state", "/api/flight-test", "/api/reboot-advice", "/api/env-credentials"}:
            if self.path == "/api/env-credentials":
                self._json(200, _env_credentials_status())
                return
            if self.path in {"/api/flight-test", "/api/reboot-advice"}:
                self._json(200, _flight_test())
                return
            payload = _read_status()
            if self.path == "/health":
                payload = {
                    "ok": True,
                    "service": "unified-market-status-server",
                    "generated_at": datetime.now().isoformat(),
                    "status_file": str(STATUS_PATH),
                    "status_file_exists": STATUS_PATH.exists(),
                    "served_status_ok": bool(payload.get("ok", False)),
                }
            self._json(200, payload)
            return
        self._json(404, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:
        if self.path != "/api/env-credentials":
            self._json(404, {"ok": False, "error": "not_found"})
            return
        if not self._local_origin_allowed():
            self._json(403, {"ok": False, "error": "local_origin_required"})
            return
        if self.headers.get("X-Aureon-Local-Operator") != "1":
            self._json(403, {"ok": False, "error": "operator_header_required"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0") or 0)
            if length <= 0 or length > 65536:
                self._json(400, {"ok": False, "error": "invalid_body_length"})
                return
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            exchange = str(body.get("exchange") or "").strip().lower()
            credentials = body.get("credentials") if isinstance(body.get("credentials"), dict) else {}
            updates = _extract_env_updates(exchange, credentials)
            result = _write_env_updates(updates)
            intent = _record_env_update_intent(exchange, result["updated_keys"])
            self._json(
                200,
                {
                    "ok": True,
                    "service": "unified-market-status-server",
                    "generated_at": datetime.now().isoformat(),
                    "exchange": exchange,
                    "updated_keys": result["updated_keys"],
                    "hnc_packet_encrypted_keys": result.get("hnc_packet_encrypted_keys", []),
                    "env_file": result["env_file"],
                    "backup_file": result["backup_file"],
                    "restart_required": True,
                    "restart_intent": intent,
                    "credential_status": _env_credentials_status(),
                    "secret_policy": "metadata_only_no_values_returned",
                },
            )
        except ValueError as exc:
            self._json(400, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self._json(500, {"ok": False, "error": f"env_update_failed:{type(exc).__name__}"})

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _cors(self) -> None:
        origin = self.headers.get("Origin", "")
        if origin.startswith("http://127.0.0.1") or origin.startswith("http://localhost"):
            self.send_header("Access-Control-Allow-Origin", origin)
        else:
            self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Aureon-Local-Operator")

    def _local_origin_allowed(self) -> bool:
        origin = self.headers.get("Origin", "")
        return not origin or origin.startswith("http://127.0.0.1") or origin.startswith("http://localhost")

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only unified market status server")
    parser.add_argument("--port", type=int, default=8790)
    args = parser.parse_args()

    server = ThreadingHTTPServer((HOST, int(args.port)), StatusHandler)
    print(
        f"[{datetime.now().isoformat()}] unified market status server online: "
        f"http://{HOST}:{args.port}/api/terminal-state",
        flush=True,
    )
    try:
        while True:
            server.handle_request()
            time.sleep(0.001)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
