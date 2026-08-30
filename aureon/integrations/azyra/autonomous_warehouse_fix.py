"""Autonomous warehouse-fix pass — classify a REAL stock audit into gated work.

Reads an actual Boxtop/Azyra stock audit file (JSON; XLSX is reported as
unsupported rather than guessed at), applies the production rules from
``docs/azyra_warehouse_admin_reality_check.md``:

* only unit-variance rows become ``ADJUSTMENT_CANDIDATE``s — encoded SKU or
  tracker suffixes (``=150``, ``=14``, ``-150`` …) are measurement sizes, not
  quantities to type;
* rows already covered by a ``commit_ok`` closeout in the output manifest are
  deduped, never double-posted;
* ``execute_live`` requires every Azyra operator gate — otherwise the pass is
  an honest dry-run preflight whose blockers become work items.

The pass NEVER fabricates stock numbers: no audit rows → ``source_data_empty``,
no audit file → the caller never reaches this function (see the goal route).
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List

from aureon.integrations.azyra.operator_bridge import AzyraOperatorBridge

SCHEMA_VERSION = "azyra-autonomous-warehouse-fix-pass-v1"

# encoded measurement suffixes that must never be typed as quantities
_ENCODED_SUFFIX_RE = re.compile(r"[=\-]\d+\s*$")


def _load_audit_rows(audit_path: Path) -> Dict[str, Any]:
    if audit_path.suffix.lower() != ".json":
        return {
            "ok": False,
            "rows": [],
            "reason": f"unsupported audit format {audit_path.suffix!r} — convert to JSON first",
        }
    try:
        payload = json.loads(audit_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ok": False, "rows": [], "reason": f"audit unreadable: {type(exc).__name__}: {exc}"}
    rows = payload.get("rows") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        rows = []
    return {"ok": True, "rows": [r for r in rows if isinstance(r, dict)], "reason": ""}


def _classify_row(row: Dict[str, Any]) -> Dict[str, Any]:
    sku = str(row.get("sku") or row.get("SKU") or row.get("code") or "").strip()
    variance = row.get("variance", row.get("unit_variance"))
    hold_reasons: List[str] = []
    if not sku:
        hold_reasons.append("missing_sku")
    if _ENCODED_SUFFIX_RE.search(sku):
        hold_reasons.append("encoded_measurement_suffix")
    try:
        variance_units = int(variance)
    except (TypeError, ValueError):
        variance_units = 0
        hold_reasons.append("non_unit_variance")
    if variance_units == 0 and "non_unit_variance" not in hold_reasons:
        hold_reasons.append("zero_variance")
    if str(row.get("hold") or "").strip().lower() in {"1", "true", "yes", "source_review", "live_movement"}:
        hold_reasons.append("explicit_hold")
    return {
        "sku": sku,
        "variance_units": variance_units,
        "classification": "ADJUSTMENT_CANDIDATE" if not hold_reasons else "HOLD",
        "hold_reasons": hold_reasons,
        "source_row": row,
    }


def _existing_closeouts(output_dir: Path) -> set[str]:
    done: set[str] = set()
    manifest = output_dir / "warehouse_fix_manifest.json"
    if manifest.exists():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            for item in data.get("closeouts", []):
                if isinstance(item, dict) and item.get("commit_ok"):
                    done.add(str(item.get("sku") or ""))
        except Exception:
            pass
    return done


def run_autonomous_warehouse_fix_pass(
    audit_path: Path,
    output_dir: Path | None = None,
    execute_live: bool = False,
    create_work_orders: bool = True,
    max_manifest_items: int = 250,
) -> Dict[str, Any]:
    """One classification + gated-execution pass over a real stock audit."""
    audit_path = Path(audit_path)
    out = Path(output_dir) if output_dir else audit_path.parent / "warehouse_fix"
    out.mkdir(parents=True, exist_ok=True)

    loaded = _load_audit_rows(audit_path)
    if not loaded["ok"]:
        return {
            "ok": False,
            "schema_version": SCHEMA_VERSION,
            "status": "source_data_unreadable",
            "audit_path": str(audit_path),
            "reason": loaded["reason"],
        }
    if not loaded["rows"]:
        return {
            "ok": False,
            "schema_version": SCHEMA_VERSION,
            "status": "source_data_empty",
            "audit_path": str(audit_path),
            "reason": "audit file parsed but contains no rows — nothing is invented in its place",
        }

    already_done = _existing_closeouts(out)
    classified = [_classify_row(r) for r in loaded["rows"][: max(1, int(max_manifest_items))]]
    candidates = [c for c in classified if c["classification"] == "ADJUSTMENT_CANDIDATE"
                  and c["sku"] not in already_done]
    deduped = [c for c in classified if c["classification"] == "ADJUSTMENT_CANDIDATE"
               and c["sku"] in already_done]
    holds = [c for c in classified if c["classification"] == "HOLD"]

    # live-gate preflight — the same gates the operator bridge enforces
    bridge = AzyraOperatorBridge()
    diagnostics = bridge.input_route_diagnostics()
    live_blockers = list(diagnostics.get("blockers") or [])
    live_ready = execute_live and not live_blockers

    executed: List[Dict[str, Any]] = []
    if live_ready:
        arm = bridge.arm(live=True)
        if not arm.ok:
            live_blockers = list(arm.blockers)
            live_ready = False
    if live_ready:
        # Each candidate would run its staged evidence workflow here; the pass
        # records per-candidate results from the gated bridge — never a pretend
        # success. (On any host without the Azyra session this branch is
        # unreachable because the gates above already refused.)
        for cand in candidates:
            executed.append({
                "sku": cand["sku"],
                "status": "queued_for_staged_execution",
                "note": "staged typing/submit runs through AzyraOperatorBridge.run_workflow with stage evidence",
            })

    work_orders: List[Dict[str, Any]] = []
    if create_work_orders:
        if not execute_live or live_blockers:
            for blocker in (live_blockers or (["live_execution_not_requested"] if not execute_live else [])):
                work_orders.append({
                    "id": f"clear_blocker_{blocker}",
                    "kind": "azyra_live_gate",
                    "blocker": blocker,
                    "note": "Clear this blocker before any production stock adjustment.",
                })
        for hold in holds:
            work_orders.append({
                "id": f"review_hold_{hold['sku'] or 'unknown'}",
                "kind": "source_review",
                "hold_reasons": hold["hold_reasons"],
            })

    manifest = {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "status": "live_execution_staged" if live_ready else "dry_run_preflight",
        "generated_at": time.time(),
        "audit_path": str(audit_path),
        "counts": {
            "rows_seen": len(loaded["rows"]),
            "rows_classified": len(classified),
            "adjustment_candidates": len(candidates),
            "deduped_already_committed": len(deduped),
            "holds": len(holds),
            "work_orders": len(work_orders),
        },
        "adjustment_candidates": candidates,
        "deduped": deduped,
        "holds": holds,
        "live_execution": {
            "requested": bool(execute_live),
            "ready": live_ready,
            "blockers": live_blockers,
            "diagnostics": diagnostics,
        },
        "executed": executed,
        "work_orders": work_orders,
        "closeouts": [],  # appended only by a real committed stage, never here
    }
    (out / "warehouse_fix_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    return manifest


__all__ = ["run_autonomous_warehouse_fix_pass", "SCHEMA_VERSION"]
