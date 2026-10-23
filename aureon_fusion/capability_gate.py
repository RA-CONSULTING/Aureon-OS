"""🚦 Capability Gate — enforceable answers for domain:action requests.

Loads sero_autonomous_state/capability_matrix.json (read-only) and answers
check("domain:action") with ALLOW / HOLD verdicts.

HARD PIN (owner decree): trading_execution:execute_live_trades is pinned to
HOLD regardless of what the matrix says. The pin lifts ONLY if
aureon_fusion/state/capital_release.flag exists and contains the exact line
  RELEASE_AUTHORIZED_BY_GARY
Absence of that file (or of the exact line) = HOLD. Live capital trading
stays off either way unless the matrix gate itself is also active.

Import-safe; the matrix file is never written here.

RUNTIME-SAFETY COMPLEMENT: upstream core/aureon_runtime_safety.py HOLD-flag
semantics are merged in as an ADDITIVE check for trading_execution:* gates —
it can tighten an ALLOW into a HOLD, never loosen one, and the capital pin
above is untouched. The upstream module is imported lazily, only under the
suppression env vars, and is never executed as a launcher.
"""

import json
import os
import sys
from pathlib import Path

from .paths import SERO_AUTONOMOUS, FUSION_STATE, AUREON_UPSTREAM
from . import events

MATRIX_FILE = SERO_AUTONOMOUS / "capability_matrix.json"
FLAG_FILE = FUSION_STATE / "capital_release.flag"
RELEASE_LINE = "RELEASE_AUTHORIZED_BY_GARY"
PINNED_GATE = "trading_execution:execute_live_trades"

ALLOWED_STATUSES = ("active", "approved")

# Gate domains the upstream runtime-safety HOLD complement applies to.
# Additive only: it may tighten an ALLOW to HOLD, never the reverse.
RUNTIME_SAFETY_DOMAINS = ("trading_execution:",)


def _runtime_safety_hold(context: str, attested: bool = False):
    """Live block reason from upstream aureon_runtime_safety, or None.

    Lazy import under the suppression env vars; the upstream repo root is
    pinned on sys.path. Any failure degrades to a fail-closed HOLD string
    (never None) — for trading_execution domains an internal error must
    tighten the verdict, never loosen it.

    ``attested=True`` mirrors upstream PRODUCTION_RELEASE_ATTESTED for the
    pinned capital gate: the owner-decree release flag is the fused
    organism's production attestation, so it supersedes the upstream
    constant HOLD for THAT gate only. Every other trading_execution gate
    stays under the full upstream terminal HOLD.
    """
    if attested:
        return None
    try:
        os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
        os.environ.setdefault("AUREON_AUDIT_MODE", "1")
        upstream = str(AUREON_UPSTREAM)
        if upstream not in sys.path:
            sys.path.insert(0, upstream)
        from aureon.core import aureon_runtime_safety as rts

        return rts.live_block_reason(context)
    except Exception as exc:
        # FAIL-CLOSED: for trading_execution domains an internal error in the
        # runtime-safety complement must tighten to a HOLD, never fail open.
        # The string doubles as the hold reason recorded on the verdict.
        return (f"runtime-safety complement error "
                f"({type(exc).__name__}) — fail-closed HOLD")


def _load_matrix() -> dict:
    try:
        if MATRIX_FILE.exists():
            with open(MATRIX_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("gates", {}) if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}


def release_authorized() -> bool:
    """True only if the owner-decree flag file carries the exact release line."""
    if os.environ.get("AUREON_DEPLOYMENT_HOLD") == "1":
        return False
    try:
        if FLAG_FILE.exists():
            with open(FLAG_FILE, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.read().splitlines()]
            return RELEASE_LINE in lines
    except Exception:
        pass
    return False


def _fail_closed_verdict(domain_action: str, reason: str) -> dict:
    """Most restrictive verdict for a domain on internal error: HOLD,
    never allowed, never None. Trading-execution and undefined gates are
    already fail-closed (HOLD / DENY) — this covers everything else."""
    return {"gate": domain_action, "matrix_file": str(MATRIX_FILE),
            "verdict": "HOLD", "allowed": False,
            "fail_closed": True, "reason": reason}


def check(domain_action: str) -> dict:
    """Enforceable verdict for a 'domain:action' gate key, published to the
    event spine as gate.checked. A block at ELEVATE level also chirps (7).

    FAIL-CLOSED: any internal error while computing the verdict yields a
    HOLD for the requested domain — the gate never raises through to a
    caller that might treat an exception as consent."""
    try:
        result = _check_verdict(domain_action)
        if not isinstance(result, dict) or not isinstance(result.get("verdict"), str):
            result = _fail_closed_verdict(
                domain_action, "invalid verdict shape — fail-closed HOLD")
    except Exception as exc:
        result = _fail_closed_verdict(
            domain_action,
            f"internal gate error ({type(exc).__name__}) — fail-closed HOLD")
    events.publish_event(
        "capability_gate", "gate.checked",
        {"gate": domain_action,
         "verdict": result.get("verdict"),
         "allowed": result.get("allowed"),
         "level": result.get("level"),
         "pinned": result.get("pinned", False)},
        priority=6 if not result.get("allowed") else 4,
    )
    if not result.get("allowed") and str(result.get("level", "")).upper() == "ELEVATE":
        events.chirp("capability_gate", "gate_blocked", 7,
                     {"gate": domain_action, "verdict": result.get("verdict"),
                      "level": result.get("level")})
    if not result.get("allowed"):
        # Audit trail: every refusal lands in the intrusion ledger
        # (commitments only, never raw detail). Never raises.
        try:
            from . import receipts
            receipts.log_intrusion({
                "event": "capability_gate.refusal",
                "reason": str(result.get("reason", ""))[:256],
                "detail": {"gate": domain_action,
                           "verdict": result.get("verdict"),
                           "level": result.get("level"),
                           "pinned": bool(result.get("pinned"))},
            })
        except Exception:
            pass
    return result


def _check_verdict(domain_action: str) -> dict:
    """Enforceable verdict for a 'domain:action' gate key."""
    if os.environ.get("AUREON_DEPLOYMENT_HOLD") == "1":
        # Restored approvals remain historical until this host is commissioned.
        domain = domain_action.partition(":")[0]
        held = domain in {"trading_execution", "external_communication", "code_generation", "process_control"}
        held = held or (domain == "network_access" and domain_action != "network_access:fetch_public_data")
        if held:
            return {"gate": domain_action, "matrix_file": str(MATRIX_FILE),
                    "verdict": "HOLD", "allowed": False, "deployment_hold": True,
                    "pinned": domain_action == PINNED_GATE,
                    "reason": "Cloud commissioning HOLD; no consequential actions authorized"}
    gates = _load_matrix()
    gate = gates.get(domain_action)

    base = {"gate": domain_action, "matrix_file": str(MATRIX_FILE)}
    if gate is None:
        return {**base, "verdict": "DENY", "allowed": False,
                "reason": "no gate defined for this domain:action"}

    status = gate.get("status", "unknown")
    level = gate.get("level", "?")

    # Hard pin: live capital trading requires Gary's explicit release flag.
    if domain_action == PINNED_GATE and not release_authorized():
        return {
            **base,
            "verdict": "HOLD",
            "allowed": False,
            "pinned": True,
            "status": status,
            "level": level,
            "reason": ("HARD PIN: live capital trading stays HOLD regardless of matrix "
                       f"status ({status}). Owner decree required: write the exact line "
                       f"'{RELEASE_LINE}' to {FLAG_FILE} to lift the pin."),
        }

    allowed = status in ALLOWED_STATUSES
    if allowed and domain_action.startswith(RUNTIME_SAFETY_DOMAINS):
        # Owner attestation (release flag) only supersedes the upstream
        # terminal HOLD for the pinned capital gate itself; it never
        # authorizes any other trading_execution action.
        attested = domain_action == PINNED_GATE and release_authorized()
        hold = _runtime_safety_hold(f"capability_gate:{domain_action}",
                                    attested=attested)
        if hold:
            return {
                **base,
                "verdict": "HOLD",
                "allowed": False,
                "runtime_safety_hold": True,
                "status": status,
                "level": level,
                "reason": f"runtime safety HOLD ({hold})",
            }
    return {
        **base,
        "verdict": "ALLOW" if allowed else "HOLD",
        "allowed": allowed,
        "pinned": domain_action == PINNED_GATE and not release_authorized(),
        "status": status,
        "level": level,
        "reason": f"matrix status '{status}'" +
                  (" (pin lifted by owner decree flag)" if domain_action == PINNED_GATE else ""),
    }


def status() -> dict:
    gates = _load_matrix()
    counts = {}
    for gate in gates.values():
        counts[gate.get("status", "unknown")] = counts.get(gate.get("status", "unknown"), 0) + 1
    return {
        "matrix_file": str(MATRIX_FILE),
        "gates_total": len(gates),
        "by_status": counts,
        "capital_pin": {
            "gate": PINNED_GATE,
            "matrix_status": gates.get(PINNED_GATE, {}).get("status", "missing"),
            "flag_file": str(FLAG_FILE),
            "flag_present": FLAG_FILE.exists(),
            "release_authorized": release_authorized(),
            "effective_verdict": _check_verdict(PINNED_GATE)["verdict"],
        },
        "runtime_safety": {
            "domains": list(RUNTIME_SAFETY_DOMAINS),
            "live_block_reason": _runtime_safety_hold("capability_gate:status"),
            "pinned_gate_attested": release_authorized(),
            "note": ("upstream terminal HOLD applies to all trading_execution "
                     "gates; the owner release flag attests the pinned capital "
                     "gate only"),
        },
    }


def status_text() -> str:
    s = status()
    lines = ["═" * 72, "🚦 CAPABILITY GATE", "═" * 72]
    lines.append(f"  matrix   : {s['matrix_file']}")
    lines.append(f"  gates    : {s['gates_total']} ({', '.join(f'{k}={v}' for k, v in sorted(s['by_status'].items()))})")
    pin = s["capital_pin"]
    lines.append("─" * 72)
    lines.append(f"  CAPITAL PIN ({pin['gate']})")
    lines.append(f"    matrix_status        : {pin['matrix_status']}")
    lines.append(f"    release flag file    : {pin['flag_file']} (present={pin['flag_present']})")
    lines.append(f"    release_authorized   : {pin['release_authorized']}")
    lines.append(f"    EFFECTIVE VERDICT    : {pin['effective_verdict']}  ← always HOLD while pin holds")
    rs = s["runtime_safety"]
    lines.append("─" * 72)
    lines.append("  RUNTIME SAFETY (upstream HOLD semantics — additive complement)")
    lines.append(f"    domains                : {', '.join(rs['domains'])}")
    lines.append(f"    upstream block reason  : {rs['live_block_reason']}")
    lines.append(f"    pinned gate attested   : {rs['pinned_gate_attested']} (owner release flag)")
    lines.append(f"    note                   : {rs['note']}")
    lines.append("═" * 72)
    return "\n".join(lines)


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print("usage: python -m aureon_fusion.capability_gate [status | check <domain:action>]")
        print("example: python -m aureon_fusion.capability_gate check file_system:read_files")
        return 0
    verb = argv[0]
    if verb == "status":
        print(status_text())
        return 0
    if verb == "check":
        if len(argv) < 2:
            print("usage: check <domain:action>", file=sys.stderr)
            return 2
        result = check(argv[1])
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["allowed"] else 1
    print(f"unknown verb: {verb}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
