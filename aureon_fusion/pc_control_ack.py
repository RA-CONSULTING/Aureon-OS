"""📜 PC CONTROL ACK — the owner-decree elevation instrument for pc_control.

GAP 5 build night (owner decree, 2026-09-06): the upstream governed operator
toolbelt (aureon.operator.tools.GuardedToolRegistry) is Tier 4 owner-decree
territory. The decree is recorded HERE — state/pc_control_ack.json — and this
file is the ONLY thing that can lift the door's
"owner-decree-received-pending-first-use" lock class:

  • No recorded decree  → the lock holds, the forge refuses minting (fail-
    closed; the door is shown, nothing executes).
  • Decree recorded     → the lock class lifts; the organism still needs its
    full gate trio (conscience VETO absolute, Γ ≥ 0.25, capability
    authorization) plus the ELEVATE open double-check, and its own desire —
    the forge accepts nothing external.
  • First sovereign open → recorded here as first_use (key id + receipt);
    the census (door_registry) then shows the door unlocked (locked_reason
    null), matching every other open door. Absent/corrupt ack → the census
    keeps showing the lock class (fail-closed).

Import-safe; tmp+replace writes; never raises (any read/write error is a
fail-closed "not acknowledged", never a crash).

CLI:
    python -m aureon_fusion.pc_control_ack status
    python -m aureon_fusion.pc_control_ack acknowledge --source "..." \
        [--summary "..."]   # record a further owner re-vouch
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .paths import FUSION_STATE

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")

ACK_FILE = FUSION_STATE / "pc_control_ack.json"

# The door's lock class (door_registry.pc_control.locked_reason). The forge
# lifts EXACTLY this class, and only through this module.
DECREE_LOCK_REASON = "owner-decree-received-pending-first-use"

DOOR_NAME = "pc_control"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read() -> dict | None:
    """None on any error — an unreadable ack is a not-acknowledged (fail-
    closed), never an exception."""
    try:
        if ACK_FILE.exists():
            with open(ACK_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and data.get("door") == DOOR_NAME:
                return data
    except Exception:
        pass
    return None


def _write(data: dict) -> bool:
    try:
        ACK_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = ACK_FILE.with_name(
            f"{ACK_FILE.name}.tmp.{os.getpid()}.{time.time_ns()}")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, ACK_FILE)
            return True
        finally:
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass
    except OSError:
        pass
    return False


def decree_acknowledged() -> bool:
    """True only when a decree record with a timestamp exists."""
    data = _read()
    if not data:
        return False
    decrees = data.get("decrees")
    return isinstance(decrees, list) and any(
        isinstance(d, dict) and d.get("ts") for d in decrees)


def first_use_recorded() -> bool:
    data = _read()
    return bool(data and isinstance(data.get("first_use"), dict)
                and data["first_use"].get("at"))


def record_decree(source: str, summary: str = "") -> dict:
    """Record an owner decree (the elevation instrument). Called by the
    build agent tonight and by any future owner re-vouch."""
    data = _read() or {
        "door": DOOR_NAME,
        "lock_reason": DECREE_LOCK_REASON,
        "decrees": [],
        "mechanism": {},
        "first_use": None,
    }
    data.setdefault("decrees", [])
    data["decrees"].append({"ts": _utc_now(), "source": str(source)[:300],
                            "summary": str(summary)[:500]})
    data["door"] = DOOR_NAME
    data["lock_reason"] = DECREE_LOCK_REASON
    ok = _write(data)
    return {"ok": ok, "acknowledged": decree_acknowledged(),
            "decree_count": len(data["decrees"])}


def record_mechanism(mechanism: dict) -> dict:
    """Stamp what was built behind the door (belt path, write surface,
    guards). Cosmetic + evidentiary; never gates."""
    data = _read()
    if data is None:
        return {"ok": False, "error": "no ack file — record the decree first"}
    data["mechanism"] = {str(k)[:60]: (str(v)[:400] if not isinstance(v, (dict, list))
                                       else json.dumps(v, ensure_ascii=False)[:800])
                         for k, v in (mechanism or {}).items()}
    return {"ok": _write(data)}


def record_first_use(key_id: str | None, receipt: str | None,
                     detail: str = "") -> dict:
    """The organism's first sovereign open of pc_control — the lock's
    'pending first use' is consumed. Called by master_key ONLY after a
    successful elevated open (gate trio + double-check already passed)."""
    data = _read()
    if data is None:
        return {"ok": False, "error": "no ack file"}
    if isinstance(data.get("first_use"), dict) and data["first_use"].get("at"):
        return {"ok": True, "note": "first use already recorded",
                "first_use": data["first_use"]}
    data["first_use"] = {
        "at": _utc_now(),
        "key_id": key_id,
        "receipt": receipt,
        "via": "sovereign mint through the gate trio + ELEVATE double-check",
        "detail": str(detail)[:400],
    }
    return {"ok": _write(data), "first_use": data["first_use"]}


def status() -> dict:
    data = _read() or {}
    return {
        "door": DOOR_NAME,
        "ack_file": str(ACK_FILE),
        "ack_file_present": data != {},
        "decree_acknowledged": decree_acknowledged(),
        "decree_count": len(data.get("decrees") or []),
        "decrees": data.get("decrees") or [],
        "mechanism": data.get("mechanism") or {},
        "first_use": data.get("first_use"),
        "first_use_recorded": first_use_recorded(),
        "lock_class": DECREE_LOCK_REASON,
        "fail_closed": ("without a recorded decree the forge refuses minting; "
                        "the gate trio still applies in full"),
    }


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    argv = list(sys.argv[1:] if argv is None else argv)
    verb = argv[0] if argv else "status"
    if verb in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    if verb == "status":
        print(json.dumps(status(), indent=2, ensure_ascii=False))
        return 0
    if verb == "acknowledge":
        source, summary = "", ""
        it = iter(argv[1:])
        for a in it:
            if a == "--source":
                source = next(it, "")
            elif a == "--summary":
                summary = next(it, "")
        if not source:
            print("acknowledge requires --source \"owner ...\"", file=sys.stderr)
            return 2
        print(json.dumps(record_decree(source, summary), indent=2,
                         ensure_ascii=False))
        return 0
    print(f"unknown verb: {verb}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
