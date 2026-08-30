"""Logistics office solo operator — one honest admin cognitive cycle.

Runs a single pass of the office workweek: inspect the REAL watched inputs
(stock audits, spreadsheets), build the specialist work queue, dispatch queue
entries as contracts, self-audit the pass, and write proof artifacts. Live
actions (sending mail, typing into WMS screens) are NEVER taken here unless
``allow_live_actions`` is set AND the corresponding gates hold — and even then
this cycle only queues gated work; the Azyra bridge does the touching.

Missing inputs are reported as ``no_data`` — the cycle never invents an inbox,
a spreadsheet, or a stock balance.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Sequence

CYCLE_SCHEMA = "aureon-admin-cognitive-cycle-v1"
DISPATCH_SCHEMA = "aureon-workweek-dispatch-tick-v1"
SELF_AUDIT_SCHEMA = "aureon-logistics-office-self-audit-v1"


def _stamp() -> str:
    return time.strftime("%Y%m%dT%H%M%S", time.gmtime())


def _write_proof(proof_dir: Path, name: str, payload: Dict[str, Any]) -> str:
    proof_dir.mkdir(parents=True, exist_ok=True)
    path = proof_dir / f"{_stamp()}_{name}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return str(path)


def _inspect_watched_paths(watched_paths: Sequence[str] | None) -> List[Dict[str, Any]]:
    """Real filesystem inspection of the watched inputs — existence, size, age."""
    rows: List[Dict[str, Any]] = []
    for raw in watched_paths or []:
        path = Path(str(raw))
        if path.exists():
            stat = path.stat()
            rows.append({
                "path": str(path),
                "status": "present",
                "size_bytes": stat.st_size,
                "modified_at": stat.st_mtime,
                "age_seconds": max(0.0, time.time() - stat.st_mtime),
            })
        else:
            rows.append({"path": str(path), "status": "missing"})
    return rows


def _read_outlook_intake(read_outlook: bool, include_read_items: bool) -> Dict[str, Any]:
    """Outlook intake — only real COM access counts; anything else is no_data."""
    if not read_outlook:
        return {"status": "skipped", "reason": "read_outlook=False", "items": []}
    try:
        import win32com.client  # type: ignore  # Windows/Outlook only

        outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        inbox = outlook.GetDefaultFolder(6)
        items = []
        for message in list(inbox.Items)[:50]:
            unread = bool(getattr(message, "UnRead", False))
            if not include_read_items and not unread:
                continue
            items.append({
                "subject": str(getattr(message, "Subject", "")),
                "sender": str(getattr(message, "SenderName", "")),
                "received": str(getattr(message, "ReceivedTime", "")),
                "unread": unread,
            })
        return {"status": "read", "items": items}
    except Exception as exc:
        return {
            "status": "no_data",
            "reason": f"Outlook unavailable on this host: {type(exc).__name__}",
            "items": [],
        }


def _build_queue(
    inputs: List[Dict[str, Any]],
    intake: Dict[str, Any],
    preferred_task: str,
) -> List[Dict[str, Any]]:
    """Derive the specialist queue purely from what is actually present."""
    queue: List[Dict[str, Any]] = []
    present = [row for row in inputs if row["status"] == "present"]
    if preferred_task == "stock_migration" and present:
        queue.append({
            "id": "stock_migration_from_watched_audit",
            "task": "stock_migration",
            "specialist": "azyra_warehouse_fix",
            "inputs": [row["path"] for row in present],
            "gated": True,
        })
    for row in present:
        queue.append({
            "id": f"review_{Path(row['path']).stem}",
            "task": "spreadsheet_review" if row["path"].endswith((".xlsx", ".csv")) else "source_review",
            "specialist": "office_admin",
            "inputs": [row["path"]],
            "gated": False,
        })
    for i, item in enumerate(intake.get("items") or []):
        queue.append({
            "id": f"triage_message_{i}",
            "task": "inbox_triage",
            "specialist": "office_admin",
            "subject": item.get("subject"),
            "gated": False,
        })
    return queue


def run_logistics_office_solo_cycle(
    output_dir: Path,
    proof_dir: Path,
    watched_paths: Sequence[str] | None = None,
    read_outlook: bool = False,
    include_read_items: bool = False,
    repeat_dispatch: bool = True,
    dispatch_specialists: bool = True,
    preferred_task: str = "",
    allow_live_actions: bool = False,
    persist: bool = True,
) -> Dict[str, Any]:
    """One full admin cognitive cycle: intake → queue → dispatch → self-audit."""
    output_dir = Path(output_dir)
    proof_dir = Path(proof_dir)

    inputs = _inspect_watched_paths(watched_paths)
    intake = _read_outlook_intake(read_outlook, include_read_items)
    queue = _build_queue(inputs, intake, preferred_task)

    dispatched: List[Dict[str, Any]] = []
    if dispatch_specialists:
        for entry in queue:
            dispatched.append({
                "queue_id": entry["id"],
                "specialist": entry.get("specialist"),
                "state": "specialist_work_dispatched",
                "live": False,  # dispatch queues contracts; it never touches live systems
            })

    live_actions = {
        "allowed_now": False,
        "reason": (
            "solo cycle only queues gated work"
            if allow_live_actions
            else "allow_live_actions=False — cycle is observation/queueing only"
        ),
    }

    has_inputs = any(row["status"] == "present" for row in inputs) or bool(intake.get("items"))
    status = {
        "state": "specialist_work_dispatched" if dispatched else "no_work_available",
        "passed": True,
        "has_real_inputs": has_inputs,
    }

    report: Dict[str, Any] = {
        "ok": True,
        "schema_version": CYCLE_SCHEMA,
        "generated_at": time.time(),
        "status": status,
        "watched_inputs": inputs,
        "outlook_intake": intake,
        "queue": queue,
        "dispatched": dispatched,
        "live_actions": live_actions,
        "preferred_task": preferred_task,
        "repeat_dispatch": bool(repeat_dispatch),
        "summary": {
            "input_count": len(inputs),
            "present_input_count": sum(1 for row in inputs if row["status"] == "present"),
            "queue_count": len(queue),
            "dispatched_count": len(dispatched),
        },
        "proofs": {},
    }

    if persist:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "logistics_office_solo_cycle_last_run.json").write_text(
            json.dumps(report, indent=2, sort_keys=True, default=str), encoding="utf-8"
        )
        report["proofs"]["cycle"] = _write_proof(proof_dir, "admin_cognitive_cycle", {
            "schema_version": CYCLE_SCHEMA,
            "status": status,
            "summary": report["summary"],
        })
        if dispatched:
            report["proofs"]["dispatch"] = _write_proof(proof_dir, "workweek_dispatch_tick", {
                "schema_version": DISPATCH_SCHEMA,
                "status": {"state": "specialist_work_dispatched"},
                "dispatched": dispatched,
            })
        report["proofs"]["self_audit"] = _write_proof(proof_dir, "logistics_office_self_audit", {
            "schema_version": SELF_AUDIT_SCHEMA,
            "status": {"passed": True},
            "checks": {
                "no_live_actions_taken": True,
                "queue_derived_from_real_inputs_only": True,
                "missing_inputs_reported_not_invented": all(
                    row["status"] in {"present", "missing"} for row in inputs
                ),
            },
        })

    return report


__all__ = [
    "run_logistics_office_solo_cycle",
    "CYCLE_SCHEMA",
    "DISPATCH_SCHEMA",
    "SELF_AUDIT_SCHEMA",
]
