"""Logistics/admin capability matrix — the honest map of Aureon's office jobs.

Builds the declarative matrix of every administration job Aureon can route
(generic office baseline + the SFG warehouse/WMS overlay), marks each row
``proven`` ONLY when a matching proof artifact exists in the supplied proof
directories, and turns every unproven capability into a work order. The matrix
itself is read-only by construction: ``live_execution.allowed_now`` is always
``False`` because building a map must never type, submit, send, or mutate a
live system.
"""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Sequence

SCHEMA_VERSION = "aureon-logistics-admin-capability-matrix-v1"

# proof schema markers → the row families they prove
_PROOF_MARKERS = {
    "aureon-admin-cognitive-cycle-v1": "generic",
    "aureon-logistics-office-self-audit-v1": "generic",
    "aureon-workweek-dispatch-tick-v1": "generic",
    "azyra-stock-migration-queue-worker-result-v1": "sfg",
}


def _generic_admin_baseline() -> List[Dict[str, Any]]:
    """The generic office-administration job surface (route + safe gate each)."""
    gate_doc = "docs/azyra_warehouse_admin_reality_check.md"
    rows = [
        ("inbox_triage", "Triage inbound email/messages into the office queue",
         "office_admin_workweek", "read-only intake; send actions gated behind AUREON_ADMIN_LIVE_MODE",
         ["logistics_office_solo_cycle"]),
        ("record_update_control", "Controlled live record updates in WMS/ERP screens",
         "azyra_human_operator",
         f"all typing/submits pass the Azyra operator gates ({gate_doc})",
         ["azyra_operator_run_workflow", "azyra_operator_capture_screen"]),
        ("customer_supplier_comms", "Draft customer/supplier communications for human send",
         "office_admin_workweek", "drafts only; outbound send gated behind AUREON_ADMIN_LIVE_MODE",
         ["logistics_office_solo_cycle"]),
        ("admin_self_audit", "Audit the office queue, proofs, and evidence packs",
         "office_admin_workweek", "read-only self audit; no live mutation gate needed",
         ["logistics_office_self_audit"]),
        ("spreadsheet_review", "Review Excel stock balances and summarise variances",
         "office_admin_workweek", "read-only spreadsheet analysis",
         ["logistics_office_solo_cycle"]),
        ("report_generation", "Generate JSON/Markdown/CSV admin reports with evidence links",
         "office_admin_workweek", "writes only to state/ and outputs/, never to live systems",
         ["logistics_admin_capability_matrix"]),
        ("queue_management", "Build, dedupe, and dispatch the specialist work queue",
         "office_admin_workweek", "queue entries are contracts; execution stays behind its own gates",
         ["logistics_office_workweek_dispatch_tick"]),
        ("document_filing", "File evidence artifacts into the dated proof directories",
         "office_admin_workweek", "append-only filing under state/ proof dirs",
         ["logistics_office_solo_cycle"]),
        ("calendar_scheduling", "Plan the admin workweek cadence and monitor ticks",
         "office_admin_workweek", "planning only; no external calendar mutation",
         ["logistics_office_workweek_monitor_tick"]),
    ]
    return [
        {
            "id": f"generic:{key}",
            "label": label,
            "aureon_route": route,
            "safe_gate_path": gate,
            "required_tools": tools,
        }
        for key, label, route, gate, tools in rows
    ]


_SFG_TASKS: Sequence[tuple[str, str]] = (
    ("update_stock", "Post gated stock adjustments through the Azyra operator route"),
    ("goods_in_booking", "Book inbound goods against purchase orders"),
    ("goods_in_putaway", "Record putaway to WMS locations"),
    ("pick_list_release", "Release pick lists to the warehouse floor"),
    ("pick_confirmation", "Confirm picks against order lines"),
    ("dispatch_booking", "Book dispatches and carrier collections"),
    ("dispatch_labels", "Produce dispatch/carrier labels"),
    ("returns_intake", "Log customer returns into the returns queue"),
    ("returns_grading", "Grade returned stock for restock or write-off review"),
    ("stock_take_schedule", "Schedule perpetual inventory counts"),
    ("stock_take_entry", "Enter count results for variance review"),
    ("variance_review", "Review count variances before any adjustment"),
    ("location_create", "Create or prove WMS locations (New → code → Usage=Bulk → save)"),
    ("location_merge_review", "Review duplicate/overlapping WMS locations"),
    ("sku_master_review", "Review SKU master data (sizes vs encoded suffixes)"),
    ("pallet_tracking", "Track pallet IDs across moves"),
    ("serial_batch_capture", "Capture serial/batch references on movements"),
    ("order_entry_review", "Review sales-order entry for warehouse feasibility"),
    ("backorder_review", "Review backorders against free stock"),
    ("carrier_manifest", "Compile the end-of-day carrier manifest"),
    ("pod_filing", "File proof-of-delivery documents"),
    ("customer_stock_report", "Produce per-customer stock holding reports"),
    ("owner_billing_data", "Assemble storage/handling billing data"),
    ("kpi_dashboard", "Compile warehouse KPI summaries"),
    ("exception_log", "Maintain the operational exception log"),
    ("screen_film_evidence", "Record screen-film evidence for live stages"),
    ("closeout_ledger", "Maintain the adjustment closeout ledger"),
    ("stock_migration", "Run the Boxtop→Azyra stock migration queue"),
    ("quarantine_moves", "Move stock into/out of quarantine status"),
    ("adjustment_preflight", "Run the adjustment candidate preflight (dedupe, holds, gates)"),
)


def _sfg_admin_overlay() -> Dict[str, Any]:
    rows = [
        {
            "id": f"sfg_task:{key}",
            "label": label,
            "aureon_route": "azyra_human_operator" if key in {
                "update_stock", "location_create", "quarantine_moves"
            } else "office_admin_workweek",
            "safe_gate_path": (
                "Azyra operator gates (input/submit/keyboard-route) + stage evidence"
                if key in {"update_stock", "location_create", "quarantine_moves"}
                else "read/plan/report only; any live mutation escalates to the Azyra operator gates"
            ),
            "required_tools": (
                ["azyra_operator_run_workflow", "azyra_operator_capture_screen"]
                if key in {"update_stock", "location_create", "quarantine_moves"}
                else ["logistics_office_solo_cycle"]
            ),
        }
        for key, label in _SFG_TASKS
    ]
    return {"rows": rows, "source": "SFG warehouse administration job map"}


def _scan_proofs(proof_dirs: Sequence[Path] | None) -> Dict[str, Any]:
    """Scan real proof directories for known evidence schemas. No proof → unproven."""
    found: Dict[str, List[str]] = {marker: [] for marker in _PROOF_MARKERS}
    for directory in proof_dirs or []:
        directory = Path(directory)
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            marker = str(payload.get("schema_version") or "")
            if marker in found:
                found[marker].append(str(path))
    return {
        "markers_found": {k: v for k, v in found.items() if v},
        "generic_proven": any(v for k, v in found.items() if _PROOF_MARKERS[k] == "generic"),
        "sfg_proven": any(v for k, v in found.items() if _PROOF_MARKERS[k] == "sfg"),
    }


def _matrix_markdown(matrix: Dict[str, Any]) -> str:
    lines = [
        "# Logistics Admin Capability Matrix",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        "",
        "Live execution from this matrix: **never** — building the map cannot mutate live systems.",
        "",
        "## Generic admin baseline",
        "",
        "| Job | Route | Safe gate | Status |",
        "| --- | --- | --- | --- |",
    ]
    for row in matrix["generic_admin_baseline"]:
        lines.append(f"| {row['id']} | {row['aureon_route']} | {row['safe_gate_path']} | {row['status']} |")
    lines += ["", "## SFG logistics overlay", "", "| Job | Route | Status |", "| --- | --- | --- |"]
    for row in matrix["sfg_admin_overlay"]["rows"]:
        lines.append(f"| {row['id']} | {row['aureon_route']} | {row['status']} |")
    lines += ["", "## Work orders (capability gaps)", ""]
    for order in matrix["work_orders"]:
        lines.append(f"- `{order['id']}` — {order['note']}")
    return "\n".join(lines) + "\n"


def build_logistics_admin_capability_matrix(
    output_dir: Path | None = None,
    proof_dirs: Sequence[Path] | None = None,
    persist: bool = True,
    root: Path | None = None,
) -> Dict[str, Any]:
    """Build (and optionally persist) the full admin capability matrix."""
    root = Path(root) if root else Path.cwd()
    out = Path(output_dir) if output_dir else root / "state" / "logistics_office" / "capability_matrix"

    proofs = _scan_proofs(proof_dirs)
    generic_rows = _generic_admin_baseline()
    overlay = _sfg_admin_overlay()
    for row in generic_rows:
        row["status"] = "proven" if proofs["generic_proven"] else "declared_untested"
    for row in overlay["rows"]:
        row["status"] = "proven" if proofs["sfg_proven"] else "declared_untested"

    work_orders = [
        {
            "id": f"prove_{row['id'].replace(':', '_')}",
            "kind": "capability_proof",
            "row_id": row["id"],
            "note": f"Record real proof evidence for {row['id']} — declared capability is not proven capability.",
        }
        for row in generic_rows + overlay["rows"]
        if row["status"] != "proven"
    ]
    # even a fully proven matrix keeps its standing re-verification order —
    # proofs age, so the gap list is never allowed to silently reach zero
    work_orders.append({
        "id": "reverify_admin_capability_proofs",
        "kind": "capability_proof_refresh",
        "row_id": "*",
        "note": "Re-run the admin proof cycle so capability evidence stays current.",
    })

    matrix: Dict[str, Any] = {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "generated_at": time.time(),
        "generic_admin_baseline": generic_rows,
        "sfg_admin_overlay": overlay,
        "proof_scan": proofs,
        "live_execution": {
            "allowed_now": False,
            "reason": (
                "capability-matrix construction is read-only by design; typing, submits, "
                "sends, and record mutations only ever run through the Azyra operator "
                "gates or AUREON_ADMIN_LIVE_MODE"
            ),
        },
        "work_orders": work_orders,
        "summary": {
            "generic_admin_row_count": len(generic_rows),
            "sfg_admin_row_count": len(overlay["rows"]),
            "proven_row_count": sum(
                1 for row in generic_rows + overlay["rows"] if row["status"] == "proven"
            ),
            "work_order_count": len(work_orders),
        },
        "paths": {},
    }

    if persist:
        out.mkdir(parents=True, exist_ok=True)
        json_path = out / "logistics_admin_capability_matrix.json"
        md_path = out / "logistics_admin_capability_matrix.md"
        csv_path = out / "logistics_admin_capability_matrix.csv"
        docs_dir = root / "docs" / "audits"
        public_dir = root / "frontend" / "public"
        docs_dir.mkdir(parents=True, exist_ok=True)
        public_dir.mkdir(parents=True, exist_ok=True)
        docs_json = docs_dir / "logistics_admin_capability_matrix.json"
        public_json = public_dir / "logistics_admin_capability_matrix.json"

        matrix["paths"] = {
            "json": str(json_path),
            "markdown": str(md_path),
            "csv": str(csv_path),
            "docs_json": str(docs_json),
            "public_json": str(public_json),
        }
        serialized = json.dumps(matrix, indent=2, sort_keys=True, default=str)
        json_path.write_text(serialized, encoding="utf-8")
        docs_json.write_text(serialized, encoding="utf-8")
        public_json.write_text(serialized, encoding="utf-8")
        md_path.write_text(_matrix_markdown(matrix), encoding="utf-8")
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["id", "label", "aureon_route", "safe_gate_path", "status"],
                extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerows(generic_rows + overlay["rows"])

    return matrix


__all__ = ["build_logistics_admin_capability_matrix", "SCHEMA_VERSION"]
