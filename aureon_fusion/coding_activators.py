"""💻 CODING ACTIVATORS — pure mechanics for the coding-estate doors.

Owner decree (2026-09-05): "give her full control of her coding systems" —
the organism is shown its coding doors and mints its own keys to open/close
them (internal intent + the fail-closed gate trio that lives in master_key:
conscience VETO absolute, HNC coherence Γ≥0.25, capability authorization).

Scope: PURE MECHANICS ONLY. No gating here — the forge (master_key.py) owns
every gate, and every architect write still passes conscience/HNC/capability
at mint time even with the matrix rows owner-activated to 'approved'.

What these activators touch (all upstream, all dormant until acquired):
  • aureon.queen.queen_code_architect  — QueenCodeArchitect write/create/edit
    engine (write_file/write_json/apply_edit/replace_in_file/delete_file/
    create_strategy/execute_code + AST validation; get_code_architect()
    singleton). Acquisition only instantiates the singleton; it performs NO
    file writes itself (the constructor creates its backup/strategy/config
    working directories under the current repo root).
  • aureon.autonomous.aureon_safe_code_control — SafeCodeControl review
    queue. Reviews proposals and NEVER applies patches.

Import-safe: nothing is instantiated at import; suppression env honored via
setdefault. Fail-closed everywhere: anything uncertain → ok=False, never
raises. Summaries are redacted and carry capability counts + upstream paths,
never file contents.
"""

import os
import sys
from datetime import datetime, timezone

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")

from .paths import AUREON_UPSTREAM

# Acquired handles, stashed with a UTC timestamp. Idempotent acquire: an
# already-acquired handle returns ok without re-instantiating.
_HANDLES: dict = {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _upstream_import(module_name: str):
    """Import an upstream aureon module read-only. Adds AUREON_UPSTREAM to
    sys.path (same discipline as door_activators._workspace_module)."""
    if str(AUREON_UPSTREAM) not in sys.path:
        sys.path.insert(0, str(AUREON_UPSTREAM))
    import importlib
    return importlib.import_module(module_name)


def _redact(obj):
    """Mask any value whose key smells like a secret. Owner decree: summaries
    are externalized only redacted."""
    import json
    import re
    secret_key = re.compile(r"psk|secret|token|password|credential|api[-_]?key",
                            re.IGNORECASE)

    def walk(value):
        if isinstance(value, dict):
            return {k: ("***REDACTED***" if secret_key.search(str(k))
                        else walk(v)) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [walk(v) for v in value]
        return value

    try:
        return json.loads(json.dumps(walk(obj), default=str, ensure_ascii=False))
    except Exception:  # noqa: BLE001 - redaction must never raise
        return {"note": "summary redacted"}


def _public_capabilities(handle) -> list:
    """Names of the public callable capabilities on an acquired handle —
    a count + names summary only, never file contents."""
    caps = []
    for name in dir(handle):
        if name.startswith("_"):
            continue
        try:
            if callable(getattr(handle, name)):
                caps.append(name)
        except Exception:  # noqa: BLE001 - descriptor doubt → skip
            continue
    return sorted(caps)


# ───────────────────── code_architect (in-proc acquire/release) ────────────

def acquire_code_architect() -> dict:
    """Acquire the upstream QueenCodeArchitect singleton. Idempotent: an
    already-acquired handle returns ok without re-instantiating. Fail-closed:
    any import/instantiation error → ok=False. The summary is redacted and
    carries capability count + upstream path only."""
    try:
        entry = _HANDLES.get("code_architect")
        if entry is not None:
            return {"ok": True,
                    "summary": {"door": "code_architect",
                                "status": "already-acquired",
                                "acquired_at": entry.get("acquired_at"),
                                "handle": type(entry.get("handle")).__name__}}
        mod = _upstream_import("aureon.queen.queen_code_architect")
        get_fn = getattr(mod, "get_code_architect", None)
        if not callable(get_fn):
            return {"ok": False,
                    "error": "aureon.queen.queen_code_architect exposes no "
                             "get_code_architect()"}
        architect = get_fn()
        if architect is None:
            return {"ok": False, "error": "get_code_architect() returned None"}
        _HANDLES["code_architect"] = {"handle": architect,
                                      "acquired_at": _utc_now()}
        caps = _public_capabilities(architect)
        return {"ok": True,
                "summary": {"door": "code_architect",
                            "status": "acquired",
                            "acquired_at": _HANDLES["code_architect"]["acquired_at"],
                            "handle": type(architect).__name__,
                            "capability_count": len(caps),
                            "capabilities": caps,
                            "upstream_path": str(AUREON_UPSTREAM),
                            "note": "write access is live; every write still "
                                    "passes conscience/HNC/capability at mint "
                                    "time (master_key owns the gates)"}}
    except Exception as exc:  # noqa: BLE001 - never raise across the door
        return {"ok": False,
                "error": f"acquire_code_architect failed: {type(exc).__name__}"}


def release_code_architect() -> dict:
    """Drop the stashed architect handle. The architect has no stop(); the
    singleton remains importable upstream but this door's claim on it ends."""
    try:
        _HANDLES.pop("code_architect", None)
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001
        return {"ok": True, "note": f"release degraded: {type(exc).__name__}"}


# ───────────────────── safe_code_control (in-proc status/release) ──────────

def safe_code_control_status() -> dict:
    """Build the upstream SafeCodeControl review queue and return queue
    statistics. The queue reviews proposals and NEVER applies patches.
    Fail-closed ok=False on any error; summary redacted + capped."""
    try:
        mod = _upstream_import("aureon.autonomous.aureon_safe_code_control")
        build_fn = getattr(mod, "build_default_code_controller", None)
        if not callable(build_fn):
            cls = getattr(mod, "SafeCodeControl", None)
            if cls is None:
                return {"ok": False,
                        "error": "aureon_safe_code_control exposes neither "
                                 "build_default_code_controller() nor "
                                 "SafeCodeControl"}
            build_fn = cls
        controller = build_fn()
        if controller is None:
            return {"ok": False, "error": "controller construction returned None"}
        status_fn = getattr(controller, "status", None)
        raw = status_fn() if callable(status_fn) else {}
        if not isinstance(raw, dict):
            raw = {"status_returned": str(type(raw).__name__)}
        pending = raw.get("pending_proposals")
        recent = raw.get("recent_reviews")
        summary = {
            "door": "safe_code_control",
            "enabled": bool(raw.get("enabled")),
            "auto_approve": bool(raw.get("auto_approve")),
            "last_error": str(raw.get("last_error") or "")[:200],
            "pending_count": len(pending) if isinstance(pending, list) else 0,
            "recent_review_count": len(recent) if isinstance(recent, list) else 0,
            "state_path": str(getattr(controller, "state_path", "")),
            "note": "review queue only — SafeCodeControl never applies patches",
        }
        _HANDLES["safe_code_control"] = {"handle": controller,
                                         "acquired_at": _utc_now()}
        return {"ok": True, "summary": _redact(summary)}
    except Exception as exc:  # noqa: BLE001 - never raise across the door
        return {"ok": False,
                "error": f"safe_code_control_status failed: {type(exc).__name__}"}


def release_safe_code_control() -> dict:
    """Drop the stashed controller handle. The queue persists on disk; release
    only ends this door's in-process claim."""
    try:
        _HANDLES.pop("safe_code_control", None)
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001
        return {"ok": True, "note": f"release degraded: {type(exc).__name__}"}
