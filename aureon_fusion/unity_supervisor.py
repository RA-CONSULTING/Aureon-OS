"""🛰️ Unity Supervisor — SaaS-style persistent fleet supervisor.

Runs a supervision loop that loads the organ registry, checks liveness for
every supervised organ/loop, and restarts dead ones via the registry's own
start/stop/restart functions. Critical safety gates:

  * queen_mind is NEVER restarted unless an explicit owner-approval file
    `aureon_fusion/state/queen_mind_restart_approved.json` exists with
    {approved:true, ts}. If queen_mind is dead without approval, the
    supervisor emits a loud chirp/event and records status
    'dead-awaiting-owner-restart'.
  * requires_release organs (e.g. live-trading radar suite) are skipped when
    the capital release pin is absent.
  * dormant organs are skipped.
  * The supervisor never restarts itself.

Each cycle writes `aureon_fusion/state/supervisor_state.json`:
    {ts, fleet:[{name, status, pid, last_seen}], restarts_this_cycle:[...],
     decisions:[...]}
and publishes a `supervisor.status` event via aureon_fusion.events.

CLI:
    python -m aureon_fusion.unity_supervisor           # daemon loop
    python -m aureon_fusion.unity_supervisor --once    # single cycle + exit
    python -m aureon_fusion.unity_supervisor --interval 45

Import-safe: no side effects at import time.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import events
from . import organ_registry
from .paths import FUSION_STATE, WORKSPACE

SUPERVISOR_STATE_FILE = FUSION_STATE / "supervisor_state.json"
QUEEN_MIND_RESTART_APPROVAL = FUSION_STATE / "queen_mind_restart_approved.json"

# Default cadence inside the owner-specified 30-60 s band.
DEFAULT_INTERVAL_S = 45

# Minimum interval to prevent runaway loops.
MIN_INTERVAL_S = 5


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _queen_restart_approved() -> bool:
    """True only when the owner-approval file exists and declares approved."""
    if not QUEEN_MIND_RESTART_APPROVAL.exists():
        return False
    try:
        data = json.loads(QUEEN_MIND_RESTART_APPROVAL.read_text(encoding="utf-8"))
        return bool(data.get("approved")) and bool(data.get("ts"))
    except Exception:
        return False


def _supervise_cycle(dry_run: bool = False) -> dict:
    """Run one supervision cycle.

    Returns the supervisor_state payload. When dry_run is True, decisions are
    recorded but no restart/stop actions are taken (used by --once when the
    caller wants a read-only snapshot; the default CLI restarts dead organs).
    """
    # Reload the registry module each cycle so ORGANS spec edits on disk
    # (module vs script, env, args) are honoured without a supervisor restart.
    try:
        importlib.reload(organ_registry)
    except Exception:
        pass
    ts = _utcnow()
    status = organ_registry.status_data()
    release_granted = organ_registry._release_granted()

    fleet = []
    restarts = []
    decisions = []

    for name, info in status.items():
        spec = organ_registry.ORGANS.get(name, {})
        entry = {
            "name": name,
            "status": info["state"],
            "pid": info.get("pid"),
            "last_seen": _iso(ts),
        }
        if info.get("gate_state"):
            entry["gate_state"] = info["gate_state"]
        fleet.append(entry)

        # Never restart the supervisor from inside itself.
        if name == "unity_supervisor":
            decisions.append({"organ": name, "action": "skip_self"})
            continue

        # Dormant organs are intentionally offline.
        if info["state"] == "dormant":
            decisions.append({
                "organ": name,
                "action": "skip_dormant",
                "reason": info.get("dormant_reason") or "organ marked dormant",
            })
            continue

        # Capital-gated live trading stays pinned HOLD unless released.
        if spec.get("requires_release") and not release_granted:
            if info["state"] != "running":
                decisions.append({
                    "organ": name,
                    "action": "skip_held",
                    "reason": f"{organ_registry.CAPITAL_RELEASE_FLAG.name} absent — live trading pinned HOLD",
                })
            continue

        # Already alive — nothing to do.
        if info["state"] == "running":
            continue

        # queen_mind restart requires explicit owner approval.
        if name == "queen_mind":
            if not _queen_restart_approved():
                entry["status"] = "dead-awaiting-owner-restart"
                reason = (
                    f"queen_mind is dead but {QUEEN_MIND_RESTART_APPROVAL.name} "
                    "missing or not approved — restart refused; waiting for owner"
                )
                decisions.append({
                    "organ": name,
                    "action": "await_owner_restart",
                    "reason": reason,
                })
                events.chirp(
                    "unity_supervisor",
                    "queen_mind_dead_awaiting_owner_restart",
                    urgency=9,
                    payload={
                        "organ": name,
                        "status": "dead-awaiting-owner-restart",
                        "approval_file": str(QUEEN_MIND_RESTART_APPROVAL),
                        "ts": _iso(ts),
                    },
                )
                events.publish_event(
                    "unity_supervisor",
                    "supervisor.queen_awaiting_owner_restart",
                    {"organ": name, "approval_file": str(QUEEN_MIND_RESTART_APPROVAL)},
                    priority=9,
                )
                continue

        # Recover a missing process (unless dry-run). The status snapshot can
        # age while another operator starts the organ. Idempotent start rechecks
        # liveness under the registry lock; restart would stop that new process.
        if dry_run:
            decisions.append({
                "organ": name,
                "action": "would_restart",
                "reason": "dry-run mode — no action taken",
            })
            continue

        try:
            result = organ_registry.start(name)
        except Exception as exc:
            result = {"ok": False, "error": str(exc)}

        decision = {
            "organ": name,
            "action": "ensure_running",
            "result": result,
        }
        decisions.append(decision)
        if result.get("ok") and result.get("state") in ("started", "already_running"):
            if result.get("state") == "started":
                restarts.append({
                    "organ": name,
                    "pid": result.get("pid"),
                    "state": result.get("state"),
                    "ts": _iso(ts),
                })
            # Refresh the fleet entry so the same-cycle snapshot reflects
            # the new process rather than the stale stopped state.
            entry.update({
                "status": "running",
                "pid": result.get("pid"),
                "last_seen": _iso(ts),
            })
            events.publish_event(
                "unity_supervisor",
                "supervisor.restarted" if result.get("state") == "started" else "supervisor.already_running",
                {"organ": name, "pid": result.get("pid"), "state": result.get("state")},
                priority=7,
            )
        else:
            events.publish_event(
                "unity_supervisor",
                "supervisor.restart_failed",
                {"organ": name, "result": result},
                priority=8,
            )

    payload = {
        "ts": _iso(ts),
        "fleet": fleet,
        "restarts_this_cycle": restarts,
        "decisions": decisions,
    }

    # Atomic write of supervisor state contract.
    FUSION_STATE.mkdir(parents=True, exist_ok=True)
    tmp = SUPERVISOR_STATE_FILE.with_name(
        f"{SUPERVISOR_STATE_FILE.name}.tmp.{os.getpid()}.{time.time_ns()}"
    )
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, SUPERVISOR_STATE_FILE)
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise

    # Publish the supervisor status event.
    events.publish_event(
        "unity_supervisor",
        "supervisor.status",
        {
            "ts": _iso(ts),
            "fleet_summary": {
                "total": len(fleet),
                "running": sum(1 for e in fleet if e["status"] == "running"),
                "stopped": sum(1 for e in fleet if e["status"] == "stopped"),
                "dormant": sum(1 for e in fleet if e["status"] == "dormant"),
                "awaiting_owner_restart": sum(
                    1 for e in fleet if e["status"] == "dead-awaiting-owner-restart"
                ),
            },
            "restarts_this_cycle": len(restarts),
        },
        priority=5,
    )

    # Phase 6: write the observed process identity receipt so the upstream
    # gateway can verify registered PIDs without scanning the fleet itself.
    try:
        organ_registry.write_observed_process_identity()
    except Exception as exc:
        events.publish_event(
            "unity_supervisor",
            "supervisor.identity_receipt_failed",
            {"error": str(exc)},
            priority=7,
        )

    return payload


def _print_summary(payload: dict) -> None:
    fleet = payload.get("fleet", [])
    restarts = payload.get("restarts_this_cycle", [])
    decisions = payload.get("decisions", [])
    running = sum(1 for e in fleet if e.get("status") == "running")
    print(f"[{payload.get('ts')}] unity_supervisor cycle complete")
    print(f"  fleet: {running}/{len(fleet)} running")
    if restarts:
        print(f"  restarts this cycle: {len(restarts)}")
        for r in restarts:
            print(f"    - {r['organ']}: pid={r.get('pid')} state={r.get('state')}")
    if decisions:
        print(f"  decisions: {len(decisions)}")
        for d in decisions[:10]:
            print(f"    - {d['organ']}: {d['action']}")
        if len(decisions) > 10:
            print(f"    ... and {len(decisions) - 10} more")
    print(f"  state written: {SUPERVISOR_STATE_FILE}")


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        prog="aureon_fusion.unity_supervisor",
        description="SaaS-style persistent supervisor for the Aureon organ fleet.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="run a single supervision cycle and exit",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_INTERVAL_S,
        help=f"seconds between supervision cycles (default {DEFAULT_INTERVAL_S}, min {MIN_INTERVAL_S})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="record decisions but do not actually restart organs",
    )
    args = parser.parse_args(argv)

    interval = max(MIN_INTERVAL_S, args.interval)

    if args.once:
        payload = _supervise_cycle(dry_run=args.dry_run)
        _print_summary(payload)
        return 0

    print(f"🛰️ unity_supervisor online — interval {interval:.0f}s", flush=True)
    while True:
        started = time.time()
        try:
            payload = _supervise_cycle(dry_run=args.dry_run)
            _print_summary(payload)
        except Exception as exc:
            print(f"⚠️ supervision cycle error: {exc}", flush=True)
        elapsed = time.time() - started
        sleep_for = max(0.0, interval - elapsed)
        if sleep_for > 0:
            time.sleep(sleep_for)


if __name__ == "__main__":
    sys.exit(main())
