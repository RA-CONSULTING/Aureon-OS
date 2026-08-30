#!/usr/bin/env python3
"""Lightweight baton link for system relay validation."""
from __future__ import annotations

import json
import os
import time
import sys
from pathlib import Path
from typing import Optional

try:
    from aureon.core.aureon_thought_bus import Thought, get_thought_bus
    THOUGHT_BUS_AVAILABLE = True
except Exception:
    Thought = None
    get_thought_bus = None
    THOUGHT_BUS_AVAILABLE = False

ensure_sonar = None
SONAR_AVAILABLE = False
_SONAR_IMPORT_ATTEMPTED = False
_LOADING_SONAR = False


_LINKED = set()
_LAST_PING: Optional[float] = None
_AUTO_CONTROL_DONE = False
_LAST_HANDOFF: Optional[tuple[str, float]] = None
_BATON_LOG_PATH = Path("state/baton_relay.jsonl")
# Observation truth and mutation authority are separate contracts. Importing a
# module may disable fabricated observation fallbacks, but it must never switch
# exchanges from dry-run/paper/testnet into live order execution.
_REAL_DATA_ENV_DEFAULTS = {
    "SIMULATION_MODE": "0",
    "DEMO_MODE": "0",
    "STATUS_MOCK": "false",
    "SIMULATED_ATTACKS": "false",
    "AUREON_COMMAND_CENTER_DEMO": "0",
    "SENTIENCE_FORCE_PERFECT": "0",
    "AUREON_ALLOW_SIM_FALLBACK": "0",
}


def _audit_mode_enabled() -> bool:
    return os.getenv("AUREON_AUDIT_MODE", "").strip().lower() in {"1", "true", "yes", "on"}


def _import_side_effects_suppressed() -> bool:
    return os.getenv("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _load_sonar() -> bool:
    """Load WhaleSonar only when a runtime link actually needs it."""
    global ensure_sonar, SONAR_AVAILABLE, _SONAR_IMPORT_ATTEMPTED, _LOADING_SONAR
    if SONAR_AVAILABLE and ensure_sonar is not None:
        return True
    if _LOADING_SONAR or _import_side_effects_suppressed() or _audit_mode_enabled():
        return False
    if _SONAR_IMPORT_ATTEMPTED:
        return False

    _SONAR_IMPORT_ATTEMPTED = True
    _LOADING_SONAR = True
    try:
        from aureon.core.mycelium_whale_sonar import ensure_sonar as loaded_ensure_sonar

        ensure_sonar = loaded_ensure_sonar
        SONAR_AVAILABLE = True
        return True
    except Exception:
        ensure_sonar = None
        SONAR_AVAILABLE = False
        return False
    finally:
        _LOADING_SONAR = False


def _stream_is_broken(stream) -> bool:
    if stream is None:
        return True
    try:
        if getattr(stream, "closed", False):
            return True
    except Exception:
        return True
    try:
        stream.write("")  # Probe; some wrappers raise ValueError if underlying handle is invalid.
        stream.flush()
        return False
    except Exception:
        return True


def _open_console_stream(name: str):
    # Windows: recover from broken stdout/stderr by reopening the console handles.
    if sys.platform == "win32":
        try:
            return open(name, "w", encoding="utf-8", errors="replace", buffering=1)
        except Exception:
            return None
    return None


def _ensure_stdio() -> None:
    """
    Some Windows execution paths can leave sys.stdout/sys.stderr as closed or invalid
    during import-time side effects. Repair them so module-level prints don't crash.
    """
    try:
        if _stream_is_broken(sys.stdout):
            repaired = _open_console_stream("CONOUT$") or open(os.devnull, "w")
            sys.stdout = repaired
    except Exception:
        pass

    try:
        if _stream_is_broken(sys.stderr):
            repaired = _open_console_stream("CONERR$") or open(os.devnull, "w")
            sys.stderr = repaired
    except Exception:
        pass


def _log_baton_event(payload: dict) -> None:
    try:
        _BATON_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _BATON_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
    except Exception:
        return


def _should_ping(now: float) -> bool:
    try:
        throttle = float(os.getenv("BATON_LINK_THROTTLE_SECONDS", "5") or 5.0)
    except Exception:
        throttle = 5.0
    if throttle <= 0:
        return True
    global _LAST_PING
    if _LAST_PING is None or (now - _LAST_PING) >= throttle:
        _LAST_PING = now
        return True
    return False


def _enforce_real_data_only() -> None:
    if _audit_mode_enabled():
        return
    if os.getenv("REAL_DATA_ONLY", "1").strip().lower() not in ("1", "true", "yes", "on"):
        return
    for key, value in _REAL_DATA_ENV_DEFAULTS.items():
        os.environ[key] = value


def link_system(module_name: str) -> None:
    """Publish a baton heartbeat without starting background services."""
    _ensure_stdio()
    if _import_side_effects_suppressed():
        return
    _enforce_real_data_only()
    if _audit_mode_enabled():
        return
    if module_name in _LINKED:
        return
    _LINKED.add(module_name)

    # Auto-control is deferred to explicit system launch — not triggered on import.
    # Call aureon.core.aureon_baton_link.activate_autonomous_control() to enable it.
    global _AUTO_CONTROL_DONE
    if not _AUTO_CONTROL_DONE and os.getenv("AUREON_ACTIVATE_ON_IMPORT", "0") == "1":
        _AUTO_CONTROL_DONE = True
        try:
            from aureon.utils.aureon_queen_hive_mind import get_queen
            queen = get_queen()
            try:
                queen.enable_full_autonomous_control()
            except Exception:
                pass
        except Exception:
            pass

    if not THOUGHT_BUS_AVAILABLE or not get_thought_bus:
        return

    bus = get_thought_bus(persist_path="logs/aureon_thoughts.jsonl")

    now = time.time()
    if not _should_ping(now):
        return

    try:
        bus.publish(Thought(
            source=module_name,
            topic="baton.link",
            payload={
                "module": module_name,
                "pid": os.getpid(),
                "ts": now,
            },
        ))
    except Exception:
        return


def activate_autonomous_control() -> None:
    """
    Explicitly activate Queen's full autonomous control.
    Call this from the ICS boot sequence, not from module imports.
    """
    global _AUTO_CONTROL_DONE
    if _AUTO_CONTROL_DONE:
        return
    _AUTO_CONTROL_DONE = True
    try:
        from aureon.utils.aureon_queen_hive_mind import get_queen
        queen = get_queen()
        try:
            queen.enable_full_autonomous_control()
        except Exception:
            pass
    except Exception:
        pass


def emit_stage(stage: str, source: str, *, topic: str | None = None, meta: Optional[dict] = None) -> None:
    """Emit a baton stage event to ThoughtBus."""
    stage = (stage or "").lower().strip()
    if stage not in {"intent", "plan", "execute", "confirm"}:
        return
    payload = {"stage": stage, "source": source}
    if meta:
        payload.update(meta)

    now = time.time()
    event = {
        "type": "stage",
        "system": source,
        "stage": stage,
        "ts": now,
        "topic": topic or f"baton.stage.{stage}",
    }
    _log_baton_event(event)

    global _LAST_HANDOFF
    if _LAST_HANDOFF:
        last_system, last_ts = _LAST_HANDOFF
        if last_system != source:
            _log_baton_event({
                "type": "handoff",
                "from_system": last_system,
                "to_system": source,
                "elapsed": round(now - last_ts, 3),
                "ts": now,
                "topic": topic or f"baton.stage.{stage}",
            })
    _LAST_HANDOFF = (source, now)

    if not THOUGHT_BUS_AVAILABLE or not get_thought_bus:
        return
    try:
        bus = get_thought_bus(persist_path="logs/aureon_thoughts.jsonl")
        bus.publish(Thought(
            source=source,
            topic=topic or f"baton.stage.{stage}",
            payload=payload,
        ))
    except Exception:
        return
