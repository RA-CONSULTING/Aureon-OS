#!/usr/bin/env python3
"""Non-mutating preflight for legacy-source current-balance live fixes."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent
WORKSPACE = REPO.parent
sys.path.insert(0, str(REPO))

from aureon.integrations.azyra.operator_bridge import AzyraOperatorBridge
from current_balance_screen_classifier import classify_image_screen


def env_bool(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def evidence_file_ok(entry: dict, field: str) -> bool:
    value = str(entry.get(field) or "").strip()
    return bool(value) and Path(value).exists()


def max_evidence_age_minutes() -> float:
    raw = os.getenv("AZYRA_CURRENT_BALANCE_MAX_EVIDENCE_AGE_MINUTES", "").strip()
    if not raw:
        return 60.0
    try:
        return float(raw)
    except ValueError:
        return 60.0


def evidence_file_fresh(entry: dict, field: str, max_age_minutes: float) -> bool:
    value = str(entry.get(field) or "").strip()
    if not value:
        return False
    path = Path(value)
    if not path.exists():
        return False
    age_minutes = (datetime.now(timezone.utc) - datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)).total_seconds() / 60.0
    return age_minutes <= max_age_minutes


def ledger_timestamp_fresh(entry: dict, field: str, max_age_minutes: float) -> bool:
    value = str(entry.get(field) or "").strip()
    if not value:
        return False
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    age_minutes = (datetime.now(timezone.utc) - timestamp).total_seconds() / 60.0
    return age_minutes <= max_age_minutes


def ledger_timestamp_present(entry: dict, field: str) -> bool:
    value = str(entry.get(field) or "").strip()
    if not value:
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def main() -> int:
    manifest_path = (
        WORKSPACE
        / "outputs"
        / "aureon_goal_contract_dispatcher"
        / "azyra_current_balance_fix"
        / "aureon_current_balance_runner_manifest.json"
    )
    output_dir = REPO / "outputs" / "aureon_current_balance_live_preflight"
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = manifest.get("items", [])
    missing_location = [item.get("sku") for item in items if not item.get("target_location")]
    nonpositive_quantity = [item.get("sku") for item in items if float(item.get("quantity") or 0) <= 0]
    ledger_path = manifest_path.parent / "current_balance_live_approval_ledger.json"
    readiness_path = manifest_path.parent / "current_balance_execution_readiness.json"
    evidence_queue_path = manifest_path.parent / "current_balance_evidence_queue.json"
    after_pdf_verification_path = manifest_path.parent / "current_balance_after_pdf_verification.json"
    completion_audit_path = manifest_path.parent / "current_balance_completion_audit.json"
    next_action_path = manifest_path.parent / "current_balance_next_action.json"
    readiness_summary = {"exists": readiness_path.exists()}
    if readiness_path.exists():
        readiness = json.loads(readiness_path.read_text(encoding="utf-8-sig"))
        readiness_summary = {
            "exists": True,
            "path": str(readiness_path),
            "summary": readiness.get("summary", {}),
        }
    evidence_queue_summary = {"exists": evidence_queue_path.exists()}
    if evidence_queue_path.exists():
        evidence_queue = json.loads(evidence_queue_path.read_text(encoding="utf-8-sig"))
        evidence_queue_summary = {
            "exists": True,
            "path": str(evidence_queue_path),
            "summary": evidence_queue.get("summary", {}),
        }
    after_pdf_verification_summary = {"exists": after_pdf_verification_path.exists()}
    if after_pdf_verification_path.exists():
        after_pdf_verification = json.loads(after_pdf_verification_path.read_text(encoding="utf-8-sig"))
        after_pdf_verification_summary = {
            "exists": True,
            "path": str(after_pdf_verification_path),
            "summary": after_pdf_verification.get("summary", {}),
        }
    completion_audit_summary = {"exists": completion_audit_path.exists()}
    if completion_audit_path.exists():
        completion_audit = json.loads(completion_audit_path.read_text(encoding="utf-8-sig"))
        completion_audit_summary = {
            "exists": True,
            "path": str(completion_audit_path),
            "complete": completion_audit.get("complete"),
            "blockers": completion_audit.get("blockers", []),
            "summary": completion_audit.get("summary", {}),
        }
    next_action_summary = {"exists": next_action_path.exists()}
    if next_action_path.exists():
        next_action = json.loads(next_action_path.read_text(encoding="utf-8-sig"))
        next_action_summary = {
            "exists": True,
            "path": str(next_action_path),
            "status": next_action.get("status"),
            "next_action": next_action.get("next_action"),
        }
    ledger_summary = {
        "exists": ledger_path.exists(),
        "approved_count": 0,
        "pending_count": len(items),
        "completed_count": 0,
        "open_closeout_count": len(items),
    }
    ledger_blocked = []
    freshness_limit_minutes = max_evidence_age_minutes()
    if ledger_path.exists():
        ledger = json.loads(ledger_path.read_text(encoding="utf-8-sig"))
        approvals = {
            (entry.get("manifest_index"), str(entry.get("sku", "")).upper()): entry
            for entry in ledger.get("items", [])
        }
        approved_count = 0
        completed_count = 0
        for item in items:
            key = (item.get("manifest_index"), str(item.get("sku", "")).upper())
            entry = approvals.get(key)
            if not entry:
                ledger_blocked.append(f"{item.get('sku')}:missing_ledger_entry")
                continue
            line_clear = (
                entry.get("approved_for_live_entry")
                and entry.get("current_balance_verified")
                and str(entry.get("movement_or_dispatch_check_status", "")).strip().lower() == "cleared"
                and entry.get("screen_stock_adjustments_confirmed")
                and ledger_timestamp_fresh(entry, "approved_at", freshness_limit_minutes)
                and evidence_file_fresh(entry, "stock_adjustments_screen_evidence", freshness_limit_minutes)
                and evidence_file_fresh(entry, "before_balance_evidence", freshness_limit_minutes)
                and evidence_file_fresh(entry, "movement_check_evidence", freshness_limit_minutes)
            )
            if line_clear:
                approved_count += 1
            else:
                ledger_blocked.append(f"{item.get('sku')}:pending_line_clearance")
            line_completed = (
                entry.get("approved_for_live_entry")
                and entry.get("current_balance_verified")
                and str(entry.get("movement_or_dispatch_check_status", "")).strip().lower() == "cleared"
                and entry.get("screen_stock_adjustments_confirmed")
                and ledger_timestamp_present(entry, "approved_at")
                and entry.get("after_balance_verified")
                and str(entry.get("closeout_status", "")).strip().lower() == "posted_and_after_balance_verified"
                and evidence_file_ok(entry, "stock_adjustments_screen_evidence")
                and evidence_file_ok(entry, "before_balance_evidence")
                and evidence_file_ok(entry, "movement_check_evidence")
                and evidence_file_ok(entry, "entered_line_evidence")
                and evidence_file_ok(entry, "posted_transaction_evidence")
                and evidence_file_ok(entry, "after_balance_evidence")
                and bool(str(entry.get("posted_transaction_reference", "")).strip())
                and ledger_timestamp_present(entry, "closed_at")
            )
            if line_completed:
                completed_count += 1
        ledger_summary = {
            "exists": True,
            "path": str(ledger_path),
            "approved_count": approved_count,
            "pending_count": len(items) - approved_count,
            "completed_count": completed_count,
            "open_closeout_count": len(items) - completed_count,
            "blocked_sample": ledger_blocked[:10],
        }

    bridge = AzyraOperatorBridge(allow_input=False, allow_submit=False)
    discovery = bridge.discover()
    region = bridge.window_region()
    screenshot_path = output_dir / f"preflight_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.png"
    capture = bridge.capture_screen(str(screenshot_path), window_only=True)
    image_screen_classification = classify_image_screen(screenshot_path)

    gates = {
        "AZYRA_OPERATOR_ALLOW_INPUT": env_bool("AZYRA_OPERATOR_ALLOW_INPUT"),
        "AZYRA_OPERATOR_ALLOW_SUBMIT": env_bool("AZYRA_OPERATOR_ALLOW_SUBMIT"),
        "AZYRA_OPERATOR_REMOTEAPP_KEYBOARD_ROUTE_PROVEN": env_bool("AZYRA_OPERATOR_REMOTEAPP_KEYBOARD_ROUTE_PROVEN"),
        "AZYRA_CURRENT_BALANCE_LIVE_APPROVED": env_bool("AZYRA_CURRENT_BALANCE_LIVE_APPROVED"),
    }
    blockers = []
    if missing_location:
        blockers.append("runner_manifest_has_missing_target_locations")
    if nonpositive_quantity:
        blockers.append("runner_manifest_has_nonpositive_quantities")
    if not ledger_summary["exists"]:
        blockers.append("approval_ledger_not_found")
    if ledger_summary.get("pending_count", 0):
        blockers.append("approval_ledger_has_pending_lines")
    if not discovery.get("window_found"):
        blockers.append("azyra_window_not_found")
    if not gates["AZYRA_OPERATOR_ALLOW_INPUT"]:
        blockers.append("live_input_gate_not_enabled")
    if not gates["AZYRA_OPERATOR_ALLOW_SUBMIT"]:
        blockers.append("live_submit_gate_not_enabled")
    if not gates["AZYRA_CURRENT_BALANCE_LIVE_APPROVED"]:
        blockers.append("current_balance_live_approval_not_enabled")
    blockers.append("must_visually_confirm_stock_adjustments_screen_before_entry")
    blockers.append("must_verify_no_pick_dispatch_or_movement_before_each_line")
    if image_screen_classification.get("screen_class") != "stock_adjustments":
        blockers.append(f"current_screen_classified_{image_screen_classification.get('screen_class')}")

    result = {
        "ok": True,
        "schema_version": "azyra-current-balance-live-preflight-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "manifest_path": str(manifest_path),
        "manifest_summary": manifest.get("summary", {}),
        "manifest_validation": {
            "item_count": len(items),
            "missing_location": missing_location,
            "nonpositive_quantity": nonpositive_quantity,
        },
        "approval_ledger": ledger_summary,
        "execution_readiness": readiness_summary,
        "evidence_queue": evidence_queue_summary,
        "after_pdf_verification": after_pdf_verification_summary,
        "completion_audit": completion_audit_summary,
        "next_action": next_action_summary,
        "gates": gates,
        "azyra_discovery": discovery,
        "azyra_window_region": region,
        "screenshot": {
            "path": str(screenshot_path),
            "ok": capture.ok,
            "reason": capture.reason,
        },
        "image_screen_classification": image_screen_classification,
        "allowed_to_execute_live_now": False,
        "blockers": blockers,
    }
    result_path = output_dir / "current_balance_live_preflight_status.json"
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"result_path": str(result_path), "blockers": blockers, "screenshot": str(screenshot_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
