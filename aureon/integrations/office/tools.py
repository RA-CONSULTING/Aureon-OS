"""Office logistics tools — ToolRegistry bindings for the admin capability layer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from aureon.integrations.office.capability_matrix import build_logistics_admin_capability_matrix
from aureon.integrations.office.solo_operator import run_logistics_office_solo_cycle

OFFICE_LOGISTICS_TOOL_NAMES = (
    "logistics_admin_capability_matrix",
    "logistics_office_solo_cycle",
    "logistics_office_self_audit",
)


def _dumps(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, default=str)


def _tool_capability_matrix(args: Dict[str, Any]) -> str:
    root = Path(str(args.get("root") or ".")).resolve()
    matrix = build_logistics_admin_capability_matrix(
        root=root, persist=bool(args.get("persist", False))
    )
    return _dumps({"ok": matrix["ok"], "summary": matrix["summary"], "paths": matrix["paths"]})


def _tool_solo_cycle(args: Dict[str, Any]) -> str:
    root = Path(str(args.get("root") or ".")).resolve()
    watched = args.get("watched_paths")
    if isinstance(watched, str):
        watched = [p.strip() for p in watched.split(",") if p.strip()]
    report = run_logistics_office_solo_cycle(
        output_dir=root / "state" / "logistics_office" / "tool_calls",
        proof_dir=root / "state" / "logistics_office" / "workweek_monitor",
        watched_paths=watched,
        allow_live_actions=False,  # tools never take live actions
        persist=bool(args.get("persist", True)),
    )
    return _dumps({"ok": report["ok"], "status": report["status"], "summary": report["summary"]})


def _tool_self_audit(args: Dict[str, Any]) -> str:
    root = Path(str(args.get("root") or ".")).resolve()
    proof_dir = root / "state" / "logistics_office" / "workweek_monitor"
    proofs = sorted(proof_dir.glob("*_logistics_office_self_audit.json")) if proof_dir.is_dir() else []
    if not proofs:
        return _dumps({"status": "no_data", "reason": "no self-audit proofs recorded yet",
                       "proof_dir": str(proof_dir)})
    latest = proofs[-1]
    try:
        payload = json.loads(latest.read_text(encoding="utf-8"))
    except Exception as exc:
        return _dumps({"status": "no_data", "reason": f"latest proof unreadable: {exc}",
                       "path": str(latest)})
    return _dumps({"status": "ok", "path": str(latest), "audit": payload})


def register_office_logistics_tools(registry: Any) -> list[str]:
    """Bind the office logistics tools onto a ToolRegistry. Returns the names."""
    specs = [
        ("logistics_admin_capability_matrix",
         "Build the logistics/admin capability matrix (read-only; proofs decide 'proven').",
         {"type": "object", "properties": {
             "root": {"type": "string"}, "persist": {"type": "boolean"}},
          "required": [], "additionalProperties": False}, _tool_capability_matrix),
        ("logistics_office_solo_cycle",
         "Run one office admin cognitive cycle over real watched inputs (no live actions).",
         {"type": "object", "properties": {
             "root": {"type": "string"},
             "watched_paths": {"type": "string", "description": "Comma-separated paths"},
             "persist": {"type": "boolean"}},
          "required": [], "additionalProperties": False}, _tool_solo_cycle),
        ("logistics_office_self_audit",
         "Read the latest logistics-office self-audit proof (no_data when none exists).",
         {"type": "object", "properties": {"root": {"type": "string"}},
          "required": [], "additionalProperties": False}, _tool_self_audit),
    ]
    for name, description, schema, handler in specs:
        registry.define_tool(name=name, description=description, input_schema=schema, handler=handler)
    return [name for name, *_ in specs]


__all__ = ["OFFICE_LOGISTICS_TOOL_NAMES", "register_office_logistics_tools"]
