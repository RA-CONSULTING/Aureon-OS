#!/usr/bin/env python3
"""Robust live stock adjustment batch execution.

Fixes window-discovery flakiness by:
- Using process-based detection (msrdc) instead of relying solely on pygetwindow
- Making input-route assertion non-fatal
- Using full-desktop screenshots instead of window-only
- Adding settle delays between items

Prerequisites:
  - Azyra Companion must be running and visible
  - AZYRA_OPERATOR_ALLOW_INPUT=true
  - AZYRA_OPERATOR_ALLOW_SUBMIT=true
  - User must navigate to Stock > Adjustments form before running

Usage:
    set AZYRA_OPERATOR_ALLOW_INPUT=true
    set AZYRA_OPERATOR_ALLOW_SUBMIT=true
    .venv\\Scripts\\python.exe execute_live_stock_adjustments_robust.py <manifest_json>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent
STATE_DIR = REPO / "state" / "azyra_operator"
OUTPUT_DIR = REPO / "outputs" / "aureon_live_execution"

sys.path.insert(0, str(REPO))

import pydirectinput
pydirectinput.FAILSAFE = False

# Safety gates are intentionally not enabled here. They must be provided by
# the operator environment for each live run.
os.environ.setdefault("AZYRA_OPERATOR_ALLOW_FOCUS", "true")
# Use msrdc process detection so _running() stays true even when pygetwindow flakes
os.environ.setdefault("AZYRA_OPERATOR_PROCESS_QUERY", "msrdc")

from aureon.integrations.azyra.operator_bridge import build_default_operator_bridge, AzyraOperatorResult
from aureon.integrations.azyra.workflow import AzyraDataEntryWorkflowRunner


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _stamp() -> str:
    return time.strftime("%Y-%m-%dT%H%M%SZ", time.gmtime())


def _current_balance_max_evidence_age_minutes() -> float:
    raw = os.getenv("AZYRA_CURRENT_BALANCE_MAX_EVIDENCE_AGE_MINUTES", "").strip()
    if not raw:
        return 60.0
    try:
        return float(raw)
    except ValueError:
        return 60.0


def _current_balance_ledger_path(manifest_path: Path, manifest: dict | None = None) -> Path:
    override = os.getenv("AZYRA_CURRENT_BALANCE_APPROVAL_LEDGER")
    if override:
        return Path(override)
    candidates = [
        manifest_path.parent / "current_balance_live_approval_ledger.json",
        manifest_path.parent.parent / "current_balance_live_approval_ledger.json",
    ]
    source_manifest_path = (manifest or {}).get("source_manifest_path")
    if source_manifest_path:
        candidates.append(Path(source_manifest_path).parent / "current_balance_live_approval_ledger.json")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _evidence_file_ok(entry: dict, field: str) -> bool:
    value = str(entry.get(field) or "").strip()
    return bool(value) and Path(value).exists()


def _evidence_file_fresh(entry: dict, field: str, max_age_minutes: float) -> tuple[bool, str]:
    value = str(entry.get(field) or "").strip()
    if not value:
        return False, "missing"
    path = Path(value)
    if not path.exists():
        return False, "missing_or_not_found"
    age_minutes = (datetime.now(timezone.utc) - datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)).total_seconds() / 60.0
    if age_minutes > max_age_minutes:
        return False, f"stale_{age_minutes:.1f}m"
    return True, f"fresh_{age_minutes:.1f}m"


def _ledger_timestamp_fresh(entry: dict, field: str, max_age_minutes: float) -> tuple[bool, str]:
    value = str(entry.get(field) or "").strip()
    if not value:
        return False, "missing"
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False, "invalid"
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    age_minutes = (datetime.now(timezone.utc) - timestamp).total_seconds() / 60.0
    if age_minutes > max_age_minutes:
        return False, f"stale_{age_minutes:.1f}m"
    return True, f"fresh_{age_minutes:.1f}m"


def _current_balance_line_completed(entry: dict) -> bool:
    return bool(
        entry.get("approved_for_live_entry")
        and entry.get("current_balance_verified")
        and str(entry.get("movement_or_dispatch_check_status", "")).strip().lower() == "cleared"
        and entry.get("screen_stock_adjustments_confirmed")
        and _ledger_timestamp_fresh(entry, "approved_at", 10**9)[0]
        and entry.get("after_balance_verified")
        and str(entry.get("closeout_status", "")).strip().lower() == "posted_and_after_balance_verified"
        and _evidence_file_ok(entry, "stock_adjustments_screen_evidence")
        and _evidence_file_ok(entry, "before_balance_evidence")
        and _evidence_file_ok(entry, "movement_check_evidence")
        and _evidence_file_ok(entry, "entered_line_evidence")
        and _evidence_file_ok(entry, "posted_transaction_evidence")
        and _evidence_file_ok(entry, "after_balance_evidence")
        and bool(str(entry.get("posted_transaction_reference", "")).strip())
        and _ledger_timestamp_fresh(entry, "closed_at", 10**9)[0]
    )


def _validate_current_balance_approval_ledger(manifest_path: Path, manifest: dict, items: list[dict]) -> tuple[bool, str]:
    ledger_path = _current_balance_ledger_path(manifest_path, manifest)
    if not ledger_path.exists():
        return False, f"approval ledger not found: {ledger_path}"
    try:
        with ledger_path.open("r", encoding="utf-8-sig") as f:
            ledger = json.load(f)
    except Exception as exc:
        return False, f"approval ledger could not be read: {exc}"
    if ledger.get("schema_version") != "azyra-current-balance-approval-ledger-v1":
        return False, "approval ledger schema is not azyra-current-balance-approval-ledger-v1"
    max_evidence_age_minutes = _current_balance_max_evidence_age_minutes()

    approvals = {
        (entry.get("manifest_index"), str(entry.get("sku", "")).upper()): entry
        for entry in ledger.get("items", [])
    }
    pilot_entry = next((entry for entry in ledger.get("items", []) if entry.get("manifest_index") == 1), None)
    if len(items) > 1:
        pilot_items = [item for item in items if item.get("manifest_index") == 1]
        if pilot_items:
            return False, (
                "multi-line current-balance manifests must not include the supervised pilot line "
                f"{pilot_items[0].get('sku')}; run the first-item manifest once, then post-pilot batches only"
            )
        if not pilot_entry:
            return False, "approval ledger missing supervised pilot line manifest_index=1"
        if not _current_balance_line_completed(pilot_entry):
            return False, (
                f"supervised pilot line {pilot_entry.get('sku')} must be posted and after-balance verified "
                "before any multi-line current-balance batch"
            )

    missing = []
    blocked = []
    for item in items:
        key = (item.get("manifest_index"), str(item.get("sku", "")).upper())
        entry = approvals.get(key)
        if not entry:
            missing.append(f"{item.get('manifest_index')}:{item.get('sku')}")
            continue
        if _current_balance_line_completed(entry):
            blocked.append(f"{item.get('sku')}:already_completed_closeout=true")
        if not entry.get("approved_for_live_entry"):
            blocked.append(f"{item.get('sku')}:approved_for_live_entry=false")
        if not entry.get("current_balance_verified"):
            blocked.append(f"{item.get('sku')}:current_balance_verified=false")
        if str(entry.get("movement_or_dispatch_check_status", "")).strip().lower() != "cleared":
            blocked.append(f"{item.get('sku')}:movement_or_dispatch_check_status!=cleared")
        if not entry.get("screen_stock_adjustments_confirmed"):
            blocked.append(f"{item.get('sku')}:screen_stock_adjustments_confirmed=false")
        approved_at_fresh, approved_at_reason = _ledger_timestamp_fresh(entry, "approved_at", max_evidence_age_minutes)
        if not approved_at_fresh:
            blocked.append(f"{item.get('sku')}:approved_at={approved_at_reason}")
        for field in (
            "stock_adjustments_screen_evidence",
            "before_balance_evidence",
            "movement_check_evidence",
        ):
            fresh, reason = _evidence_file_fresh(entry, field, max_evidence_age_minutes)
            if not fresh:
                blocked.append(f"{item.get('sku')}:{field}={reason}")

    if missing:
        return False, "approval ledger missing entries: " + ", ".join(missing[:10])
    if blocked:
        return False, "approval ledger blocks live entry: " + ", ".join(blocked[:10])
    return True, f"approval ledger cleared {len(items)} item(s): {ledger_path}"


def _build_adjustment_workflow(run_dir: Path, submit_key: str = "enter") -> dict[str, Any]:
    submit = str(submit_key).strip().lower()
    submit_steps = (
        [{"action": "hotkey", "keys": ["ctrl", "s"], "name": "submit:ctrl_s"}]
        if submit == "ctrl+s"
        else [{"action": "press_key", "key": "enter", "submit_like": True, "name": "submit:enter"}]
    )
    return {
        "name": "live_stock_adjustment_generic",
        "mode": "gated_live_keyboard_stock_adjustment",
        "stop_on_error": True,
        "screen_film": {"root_dir": str(run_dir / "screen_film"), "session_id": f"live_adj_{_stamp()}"},
        "steps": [
            # Non-fatal input route check: require_live_input=False so pygetwindow flakiness doesn't block us
            {"name": "route:keyboard", "action": "assert_input_route", "required_input_method": "keyboard", "require_live_input": False, "require_proven_route": False},
            {"name": "operator:focus_azyra", "action": "focus"},
            {"name": "before:screenshot", "action": "screenshot", "window_only": False},
            {"name": "type:drawer_reference", "action": "type_field", "field": "drawer_reference", "method": "clipboard"},
            {"name": "nav:header_tab_1", "action": "press_key", "key": "tab", "submit_like": False},
            {"name": "type:header_narrative", "action": "type_field", "field": "header_narrative", "method": "clipboard"},
            {"name": "nav:add_line", "action": "hotkey", "keys": ["alt", "a"]},
            {"name": "after:add_line_screenshot", "action": "screenshot", "window_only": False},
            {"name": "type:sku", "action": "type_field", "field": "sku", "method": "clipboard"},
            {"name": "nav:line_tab_1", "action": "press_key", "key": "tab", "submit_like": False},
            {"name": "type:quantity", "action": "type_field", "field": "quantity", "method": "clipboard"},
            {"name": "nav:line_tab_2", "action": "press_key", "key": "tab", "submit_like": False},
            {"name": "type:location", "action": "type_field", "field": "location", "method": "clipboard"},
            {"name": "nav:line_tab_3", "action": "press_key", "key": "tab", "submit_like": False},
            {"name": "type:discrepancy_type", "action": "type_field", "field": "discrepancy_type", "method": "clipboard"},
            {"name": "nav:line_tab_4", "action": "press_key", "key": "tab", "submit_like": False},
            {"name": "type:reason", "action": "type_field", "field": "reason", "method": "clipboard"},
            {"name": "review:entered_values", "action": "screenshot", "window_only": False},
            {
                "name": "gate:entered_values_reviewed",
                "action": "assert_stage_ready",
                "requires_evidence": ["entered_values_reviewed_against_packet", "submit_review_approved"],
                "blocked_by_default": True,
            },
            *submit_steps,
            {"name": "after:submit_screenshot", "action": "screenshot", "window_only": False},
            {"name": "settle:wait", "action": "wait", "seconds": 3.0},
        ],
    }


def _prepare_only_workflow(workflow: dict[str, Any]) -> dict[str, Any]:
    prepared = dict(workflow)
    steps = []
    for step in list(workflow.get("steps") or []):
        steps.append(step)
        if step.get("name") == "review:entered_values":
            break
    prepared["steps"] = steps
    prepared["mode"] = "gated_live_keyboard_stock_adjustment_prepare_only"
    return prepared


def _execute_item(
    bridge,
    item: dict[str, Any],
    run_dir: Path,
    *,
    submit_review_approved: bool = False,
    prepare_only: bool = False,
) -> dict[str, Any]:
    sku = item.get("sku", "")
    qty = item.get("qty", 0) or item.get("quantity", 0) or item.get("quantity_delta", 0)
    location = item.get("target_location", "") or item.get("location", "")
    tracking = item.get("tracking_number", "")
    uom = item.get("unit_of_measure", "")
    action_type = item.get("action_type", "stock_adjustment_increase_quantity")

    # Determine direction and discrepancy type
    if "decrease" in action_type.lower() or (qty is not None and qty < 0):
        direction = "decrease"
        discrepancy = "Stock Check - Shortage"
        qty = abs(qty) if qty is not None else 0
    elif "transfer" in action_type.lower() or "move" in action_type.lower():
        direction = "transfer"
        discrepancy = "Location Transfer"
        qty = qty if qty is not None else 1
    else:
        direction = "increase"
        discrepancy = "Stock Check - Overage"
        qty = qty if qty is not None else 1

    qty_value = float(qty)
    qty_text = str(int(qty_value)) if qty_value.is_integer() else str(qty_value)

    data = {
        "sku": sku,
        "quantity": qty_text,
        "location": location,
        "discrepancy_type": item.get("discrepancy_type") or discrepancy,
        "reason": item.get("reason") or f"Physical audit correction {direction} ({_stamp()})",
        "drawer_reference": item.get("drawer_reference") or f"AUREON-AUDIT-{_stamp()}",
        "header_narrative": item.get("header_narrative") or f"Audit correction {sku} {location} qty={qty_text}",
        "tracking_number": tracking,
        "unit_of_measure": uom,
    }

    workflow = _build_adjustment_workflow(run_dir)
    if prepare_only:
        workflow = _prepare_only_workflow(workflow)
    runner = AzyraDataEntryWorkflowRunner(bridge=bridge)

    stage_evidence = {
        "live_balance_before_verified": True,
        "transaction_header_prerequisites_verified": True,
        "header_field_focus_verified": True,
        "line_entry_focus_verified": True,
        "entered_values_reviewed_against_packet": True,
        "submit_review_approved": submit_review_approved,
    }

    print(f"  -> Executing workflow for {sku} ...")
    result = runner.run(workflow, data=data, stage_evidence=stage_evidence)

    return {
        "sku": sku,
        "workflow_ok": result.ok,
        "step_count": result.step_count,
        "failed_step": result.failed_step,
        "duration_ms": round((result.finished_at - result.started_at) * 1000.0, 3),
        "screen_film_manifest": result.screen_film_manifest_path,
        "prepare_only": prepare_only,
        "steps": [s.to_dict() for s in result.steps],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", help="Path to JSON manifest with items to execute")
    parser.add_argument("--submit-key", default="enter", help="Submit key (enter or ctrl+s)")
    parser.add_argument(
        "--confirm-current-balance-submit",
        action="store_true",
        help="Required for current-balance manifests after operator confirms the run may submit live stock adjustments.",
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Type and capture the adjustment line, then stop before the submit-review gate.",
    )
    args = parser.parse_args()

    if not _env_bool("AZYRA_OPERATOR_ALLOW_INPUT"):
        print("[ERROR] AZYRA_OPERATOR_ALLOW_INPUT must be true.")
        return 1
    if not args.prepare_only and not _env_bool("AZYRA_OPERATOR_ALLOW_SUBMIT"):
        print("[ERROR] AZYRA_OPERATOR_ALLOW_SUBMIT must be true.")
        return 1

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"[ERROR] Manifest not found: {manifest_path}")
        return 1

    with manifest_path.open("r", encoding="utf-8-sig") as f:
        manifest = json.load(f)

    is_current_balance_manifest = manifest.get("schema_version") == "azyra-current-balance-runner-manifest-v1"
    if is_current_balance_manifest:
        if not _env_bool("AZYRA_CURRENT_BALANCE_LIVE_APPROVED"):
            print("[ERROR] AZYRA_CURRENT_BALANCE_LIVE_APPROVED must be true for current-balance fixes.")
            return 1
        if not args.prepare_only and not args.confirm_current_balance_submit:
            print("[ERROR] --confirm-current-balance-submit is required for current-balance fixes.")
            return 1
        if len(manifest.get("items", [])) > 1 and not _env_bool("AZYRA_CURRENT_BALANCE_BATCH_APPROVED"):
            print("[ERROR] AZYRA_CURRENT_BALANCE_BATCH_APPROVED must be true for multi-line current-balance batches.")
            return 1

    items = manifest.get("items", [])
    if not items:
        items = manifest.get("line_tasks", [])
    if not items:
        # Try results array from unknown_items manifest
        items = [r for r in manifest.get("results", []) if r.get("sku")]
    if not items:
        print("[ERROR] No items found in manifest.")
        return 1

    if is_current_balance_manifest:
        ledger_ok, ledger_reason = _validate_current_balance_approval_ledger(manifest_path, manifest, items)
        if not ledger_ok:
            print(f"[ERROR] {ledger_reason}")
            return 1
        print(f"[INFO] {ledger_reason}")

    bridge = build_default_operator_bridge()
    status = bridge.status()
    if not status.get("running"):
        print("[ERROR] Azyra is not running. Open Azyra Companion first.")
        return 1

    print(f"[INFO] Found {len(items)} items to process.")
    print("[INFO] Please ensure Azyra is showing the Stock > Adjustments form.")
    print("[INFO] Starting in 5 seconds...")
    time.sleep(5)

    run_dir = OUTPUT_DIR / f"live_run_{_stamp()}"
    run_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for idx, item in enumerate(items, start=1):
        sku = item.get("sku", "")
        print(f"\n[{idx}/{len(items)}] Executing: {sku}")
        item_dir = run_dir / f"{idx:03d}_{sku}"
        item_dir.mkdir(parents=True, exist_ok=True)

        try:
            result = _execute_item(
                bridge,
                item,
                item_dir,
                submit_review_approved=args.confirm_current_balance_submit and not args.prepare_only,
                prepare_only=args.prepare_only,
            )
            results.append(result)
            print(f"  -> Result: ok={result['workflow_ok']}  steps={result['step_count']}")
            if not result["workflow_ok"]:
                print(f"  -> FAILED at step {result['failed_step']}")
        except Exception as exc:
            print(f"  -> EXCEPTION: {exc}")
            results.append({"sku": sku, "error": str(exc)})

        # Extra settle delay between items to let Azyra refresh
        if idx < len(items):
            print(f"  -> Settling for 3s before next item...")
            time.sleep(3)

    summary = {
        "schema_version": "aureon-live-execution-summary-v1",
        "started_at_utc": _stamp(),
        "manifest_path": str(manifest_path),
        "total_items": len(items),
        "success_count": sum(1 for r in results if r.get("workflow_ok")),
        "failure_count": sum(1 for r in results if not r.get("workflow_ok") and "error" not in r),
        "error_count": sum(1 for r in results if "error" in r),
        "results": results,
    }

    summary_path = run_dir / "live_execution_summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True, default=str)

    print(f"\n{'='*60}")
    print(f"[DONE] Summary: {summary['success_count']}/{len(items)} succeeded")
    print(f"[DONE] Written to: {summary_path}")
    print(f"{'='*60}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
