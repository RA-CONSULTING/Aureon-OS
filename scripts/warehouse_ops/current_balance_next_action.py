#!/usr/bin/env python3
"""Generate the next safe operator action for the current-balance live fix."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent
WORKSPACE = REPO.parent
FIX_DIR = WORKSPACE / "outputs" / "aureon_goal_contract_dispatcher" / "azyra_current_balance_fix"
PREFLIGHT = REPO / "outputs" / "aureon_current_balance_live_preflight" / "current_balance_live_preflight_status.json"
OUTPUT_JSON = FIX_DIR / "current_balance_next_action.json"
OUTPUT_MD = FIX_DIR / "current_balance_next_action.md"
DEFAULT_MAX_EVIDENCE_AGE_MINUTES = 60.0
PILOT_SKU = os.getenv("AUREON_CURRENT_BALANCE_PILOT_SKU", "SKU-EXAMPLE-001").strip().upper()
PILOT_EVIDENCE_DIR_NAME = os.getenv("AUREON_CURRENT_BALANCE_PILOT_EVIDENCE_DIR", f"001_{PILOT_SKU}")
PRE_ENTRY_STAGES = {
    "stock-adjustments-screen": "Azyra Stock > Adjustments screen",
    "before-balance": "current balance evidence",
    "movement-check": "movement/pick/dispatch clearance",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}


def path_exists(value: object) -> bool:
    text = str(value or "").strip()
    return bool(text) and Path(text).exists()


def evidence_file_fresh(value: object, max_age_minutes: float = DEFAULT_MAX_EVIDENCE_AGE_MINUTES) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    path = Path(text)
    if not path.exists():
        return False
    age_minutes = (datetime.now(timezone.utc) - datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)).total_seconds() / 60.0
    return age_minutes <= max_age_minutes


def timestamp_fresh(value: object, max_age_minutes: float = DEFAULT_MAX_EVIDENCE_AGE_MINUTES) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    try:
        timestamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return False
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    age_minutes = (datetime.now(timezone.utc) - timestamp).total_seconds() / 60.0
    return age_minutes <= max_age_minutes


def timestamp_present(value: object) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def line_approved(entry: dict) -> bool:
    return bool(
        entry.get("approved_for_live_entry")
        and entry.get("current_balance_verified")
        and str(entry.get("movement_or_dispatch_check_status", "")).strip().lower() == "cleared"
        and entry.get("screen_stock_adjustments_confirmed")
        and timestamp_fresh(entry.get("approved_at"))
        and evidence_file_fresh(entry.get("stock_adjustments_screen_evidence"))
        and evidence_file_fresh(entry.get("before_balance_evidence"))
        and evidence_file_fresh(entry.get("movement_check_evidence"))
    )


def line_completed(entry: dict) -> bool:
    return bool(
        entry.get("approved_for_live_entry")
        and entry.get("current_balance_verified")
        and str(entry.get("movement_or_dispatch_check_status", "")).strip().lower() == "cleared"
        and entry.get("screen_stock_adjustments_confirmed")
        and timestamp_present(entry.get("approved_at"))
        and entry.get("after_balance_verified")
        and str(entry.get("closeout_status", "")).strip().lower() == "posted_and_after_balance_verified"
        and path_exists(entry.get("entered_line_evidence"))
        and path_exists(entry.get("posted_transaction_evidence"))
        and path_exists(entry.get("after_balance_evidence"))
        and bool(str(entry.get("posted_transaction_reference", "")).strip())
        and timestamp_present(entry.get("closed_at"))
    )


def latest_capture_note(evidence_state: dict) -> str:
    captures = []
    for bucket in ("captures", "rejected_captures"):
        for stage, stage_captures in evidence_state.get(bucket, {}).items():
            for capture in stage_captures:
                captures.append((capture.get("captured_at", ""), bucket, stage, capture))
    if not captures:
        return ""
    _, bucket, stage, capture = sorted(captures, reverse=True)[0]
    classification = capture.get("screen_classification", {}).get("screen_class", "unknown")
    observation = capture.get("operator_observation") or capture.get("description") or ""
    reason = capture.get("stage_guard_reason", "")
    if bucket == "rejected_captures" and reason:
        return f"{bucket}:{stage}:{classification}: {reason}. Observation: {observation}".strip()
    return f"{bucket}:{stage}:{classification}: {observation}".strip()


def capture_fresh(capture: dict, max_age_minutes: float = DEFAULT_MAX_EVIDENCE_AGE_MINUTES) -> bool:
    captured_at = str(capture.get("captured_at") or "").strip()
    if not captured_at:
        return False
    try:
        timestamp = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    age_minutes = (datetime.now(timezone.utc) - timestamp).total_seconds() / 60.0
    return age_minutes <= max_age_minutes


def latest_stage_ok(evidence_state: dict, stage: str) -> bool:
    captures = evidence_state.get("captures", {}).get(stage, [])
    if not captures:
        return False
    capture = captures[-1]
    path = str(capture.get("path") or "").strip()
    return bool(
        path
        and Path(path).exists()
        and capture.get("stage_guard_passed") is not False
        and capture_fresh(capture)
    )


def missing_pre_entry_stages(evidence_state: dict) -> list[str]:
    return [stage for stage in PRE_ENTRY_STAGES if not latest_stage_ok(evidence_state, stage)]


def powershell_block(lines: list[str]) -> str:
    return "\n".join(lines)


def main() -> int:
    ledger = load_json(FIX_DIR / "current_balance_live_approval_ledger.json")
    readiness = load_json(FIX_DIR / "current_balance_execution_readiness.json")
    completion = load_json(FIX_DIR / "current_balance_completion_audit.json")
    preflight = load_json(PREFLIGHT)
    evidence = load_json(FIX_DIR / "evidence" / PILOT_EVIDENCE_DIR_NAME / "line_evidence.json")

    pilot_line = next((entry for entry in ledger.get("items", []) if entry.get("manifest_index") == 1), {})
    blockers = preflight.get("blockers", [])
    complete = bool(completion.get("complete"))
    approved = line_approved(pilot_line)
    completed = line_completed(pilot_line)
    missing_stages = missing_pre_entry_stages(evidence)

    if complete:
        status = "complete"
        next_action = "No action required. Completion audit is true."
        commands = []
    elif not approved:
        status = "pilot_pre_entry_evidence_required"
        if missing_stages == ["movement-check"]:
            next_action = (
                f"Capture or supply explicit {PILOT_SKU} movement/pick/dispatch clearance. The current PDF balance and "
                "Stock > Adjustments screen evidence are present; do not approve live entry until the movement check is real."
            )
        else:
            friendly_missing = ", ".join(PRE_ENTRY_STAGES[stage] for stage in missing_stages) or "ledger approval"
            next_action = (
                f"Finish {PILOT_SKU} pre-entry evidence: {friendly_missing}. Do not run live entry while the current screen "
                "is wrong or unclassified, including Outwards, WMS menu, File Explorer/foreground overlap, or any pick/dispatch screen."
            )
        commands = [
            'cd "<repo-root>"',
        ]
        if "stock-adjustments-screen" in missing_stages:
            commands.extend(
                [
                    f'.\\.venv\\Scripts\\python.exe .\\current_balance_wait_for_safe_screen.py --sku {PILOT_SKU}',
                    '.\\.venv\\Scripts\\python.exe .\\current_balance_open_adjustments_screen.py --dry-run',
                    f'.\\.venv\\Scripts\\python.exe .\\current_balance_evidence_capture.py --sku {PILOT_SKU} --stage stock-adjustments-screen --confirm-stock-adjustments-screen --observation "Azyra is on Stock Transaction Adjustment - Increase before the pilot entry; no stock code, location, or quantity has been entered."',
                ]
            )
        if "before-balance" in missing_stages:
            commands.append(f'.\\.venv\\Scripts\\python.exe .\\current_balance_build_source_evidence.py --sku {PILOT_SKU} --attach-before-balance')
        if "movement-check" in missing_stages:
            commands.append(
                f'.\\.venv\\Scripts\\python.exe .\\current_balance_evidence_capture.py --sku {PILOT_SKU} --stage movement-check --confirm-movement-check-screen --observation "After Azyra movement/pick/dispatch review, no pick, dispatch, or stock movement explains the current zero/null balance for the pilot line."'
            )
        commands.append(f'.\\.venv\\Scripts\\python.exe .\\current_balance_evidence_to_ledger.py --sku {PILOT_SKU} --approve-pre-entry --operator "<operator-name>" --confirm-evidence-reviewed')
    elif not completed:
        status = "pilot_approved_waiting_live_run_or_closeout"
        next_action = (
            f"Run the first-item manifest only, then import entered/posted evidence, capture after-balance evidence, and close out {PILOT_SKU}."
        )
        commands = [
            'cd "<repo-root>"',
            '$env:AZYRA_OPERATOR_ALLOW_INPUT = "true"',
            '$env:AZYRA_OPERATOR_ALLOW_SUBMIT = "true"',
            '$env:AZYRA_OPERATOR_REMOTEAPP_KEYBOARD_ROUTE_PROVEN = "true"',
            '$env:AZYRA_CURRENT_BALANCE_LIVE_APPROVED = "true"',
            '.\\.venv\\Scripts\\python.exe .\\execute_live_stock_adjustments_robust.py --confirm-current-balance-submit "<path-to-first-item-manifest.json>"',
        ]
    else:
        status = "pilot_complete_batches_waiting"
        next_action = f"{PILOT_SKU} is closed out. Prepare/approve post-pilot batch evidence and run batch manifests in order."
        commands = [
            'cd "<repo-root>"',
            '$env:AZYRA_OPERATOR_ALLOW_INPUT = "true"',
            '$env:AZYRA_OPERATOR_ALLOW_SUBMIT = "true"',
            '$env:AZYRA_OPERATOR_REMOTEAPP_KEYBOARD_ROUTE_PROVEN = "true"',
            '$env:AZYRA_CURRENT_BALANCE_LIVE_APPROVED = "true"',
            '$env:AZYRA_CURRENT_BALANCE_BATCH_APPROVED = "true"',
            '.\\.venv\\Scripts\\python.exe .\\execute_live_stock_adjustments_robust.py --confirm-current-balance-submit "<path-to-batch-manifest.json>"',
        ]

    payload = {
        "ok": True,
        "schema_version": "azyra-current-balance-next-action-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "next_action": next_action,
        "commands": commands,
        "preflight_blockers": blockers,
        "preflight_screenshot": preflight.get("screenshot", {}).get("path", ""),
        "latest_pilot_capture_note": latest_capture_note(evidence),
        "missing_pre_entry_stages": missing_stages,
        "ledger_summary": ledger.get("summary", {}),
        "readiness_summary": readiness.get("summary", {}),
        "completion": {
            "complete": completion.get("complete"),
            "blockers": completion.get("blockers", []),
            "summary": completion.get("summary", {}),
        },
        "links": {
            "pilot_evidence_status": str((FIX_DIR / "evidence" / PILOT_EVIDENCE_DIR_NAME / "line_evidence_status.md").resolve()),
            "execution_readiness": str((FIX_DIR / "current_balance_execution_readiness.md").resolve()),
            "completion_audit": str((FIX_DIR / "current_balance_completion_audit.md").resolve()),
        },
    }
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    md = [
        "# Current Balance Next Action",
        "",
        f"- Status: `{status}`",
        f"- Next action: {next_action}",
        f"- Latest pilot capture: `{payload['latest_pilot_capture_note'] or 'none'}`",
        f"- Preflight blockers: `{', '.join(blockers) if blockers else 'none'}`",
        "",
        "## Commands",
        "",
        "```powershell",
        powershell_block(commands) if commands else "# none",
        "```",
        "",
        "## Links",
        "",
        f"- Pilot evidence: `{payload['links']['pilot_evidence_status']}`",
        f"- Readiness: `{payload['links']['execution_readiness']}`",
        f"- Completion audit: `{payload['links']['completion_audit']}`",
    ]
    OUTPUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(json.dumps({"json": str(OUTPUT_JSON), "md": str(OUTPUT_MD), "status": status, "next_action": next_action}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
