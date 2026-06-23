#!/usr/bin/env python3
"""Capture non-mutating evidence for Boxtop/SFG0 current-balance corrections."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent
WORKSPACE = REPO.parent
sys.path.insert(0, str(REPO))

from aureon.integrations.azyra.operator_bridge import AzyraOperatorBridge
from current_balance_screen_classifier import classify_image_screen

FIX_DIR = Path(
    os.getenv(
        "AUREON_CURRENT_BALANCE_FIX_DIR",
        str(WORKSPACE / "outputs" / "aureon_goal_contract_dispatcher" / "azyra_current_balance_fix"),
    )
)
RUNNER_MANIFEST = Path(
    os.getenv("AUREON_CURRENT_BALANCE_RUNNER_MANIFEST", str(FIX_DIR / "aureon_current_balance_runner_manifest.json"))
)
LEDGER = Path(os.getenv("AUREON_CURRENT_BALANCE_LEDGER", str(FIX_DIR / "current_balance_live_approval_ledger.json")))
EVIDENCE_ROOT = Path(os.getenv("AUREON_CURRENT_BALANCE_EVIDENCE_ROOT", str(FIX_DIR / "evidence")))

STAGES = {
    "current-screen-probe": {
        "field": None,
        "confirm_arg": None,
        "description": "Unclassified current Azyra screen probe.",
    },
    "stock-adjustments-screen": {
        "field": "stock_adjustments_screen_evidence",
        "confirm_arg": "confirm_stock_adjustments_screen",
        "description": "Azyra is visibly on Stock > Adjustments before entry.",
    },
    "before-balance": {
        "field": "before_balance_evidence",
        "confirm_arg": "confirm_current_balance_screen",
        "description": "Live/current balance evidence before entry.",
    },
    "movement-check": {
        "field": "movement_check_evidence",
        "confirm_arg": "confirm_movement_check_screen",
        "description": "No pick, dispatch, or stock movement explains the discrepancy.",
    },
    "entered-line": {
        "field": "entered_line_evidence",
        "confirm_arg": "confirm_entered_line_screen",
        "description": "Adjustment line entered and reviewed before submit.",
    },
    "posted-transaction": {
        "field": "posted_transaction_evidence",
        "confirm_arg": "confirm_posted_transaction_screen",
        "description": "Azyra posted/confirmed the stock adjustment.",
    },
    "after-balance": {
        "field": "after_balance_evidence",
        "confirm_arg": "confirm_after_balance_screen",
        "description": "Live balance after posting reflects the corrected unit quantity.",
    },
}

PRE_ENTRY_FIELDS = [
    "stock_adjustments_screen_evidence",
    "before_balance_evidence",
    "movement_check_evidence",
]

CLOSEOUT_FIELDS = [
    "entered_line_evidence",
    "posted_transaction_evidence",
    "after_balance_evidence",
]

PLACEHOLDER_STOCK_ADJUSTMENTS = r"C:\path\to\stock_adjustments_screen.png"
PLACEHOLDER_BEFORE_BALANCE = r"C:\path\to\before_balance.png"
PLACEHOLDER_MOVEMENT_CHECK = r"C:\path\to\movement_check.png"
PLACEHOLDER_ENTERED_LINE = r"C:\path\to\entered_line.png"
PLACEHOLDER_POSTED_TRANSACTION = r"C:\path\to\posted_transaction.png"
PLACEHOLDER_AFTER_BALANCE = r"C:\path\to\after_balance.png"

FORBIDDEN_CLASSIFIED_SCREENS = {"outwards_transaction", "wms_menu", "stock_transaction_new"}


def slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("_") or "unknown"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def optional_ocr(path: Path) -> tuple[str, dict]:
    info = {"engine": "unavailable", "reason": ""}
    if not shutil.which("tesseract"):
        info["reason"] = "tesseract executable not found"
        return "", info
    try:
        import pytesseract
        from PIL import Image
    except Exception as exc:
        info["reason"] = f"pytesseract/PIL import failed: {exc}"
        return "", info
    try:
        text = pytesseract.image_to_string(Image.open(path))
    except Exception as exc:
        info["reason"] = f"ocr failed: {exc}"
        return "", info
    info = {"engine": "tesseract", "reason": "ok"}
    return text, info


def classify_screen(text: str) -> dict:
    lowered = re.sub(r"\s+", " ", text.lower()).strip()
    screen_class = "unknown"
    indicators = []
    if any(term in lowered for term in ["outwards", "waiting pick", "dispatch note", "pick list", "finished picking", "all picked"]):
        screen_class = "outwards_transaction"
        indicators = [
            term
            for term in ["outwards", "waiting pick", "dispatch note", "pick list", "finished picking", "all picked"]
            if term in lowered
        ]
    elif "stock" in lowered and any(term in lowered for term in ["adjustment", "adjustments"]):
        screen_class = "stock_adjustments"
        indicators = ["stock", "adjustment"]
    elif any(term in lowered for term in ["stock enquiry", "current balance", "balance"]):
        screen_class = "stock_or_balance_enquiry"
        indicators = [
            term
            for term in ["stock enquiry", "current balance", "balance"]
            if term in lowered
        ]
    return {
        "screen_class": screen_class,
        "indicators": indicators,
        "text_source_chars": len(text),
    }


def stage_guard(stage: str, classification: dict) -> tuple[bool, str]:
    if stage == "current-screen-probe":
        return True, "unclassified probe"
    screen_class = str(classification.get("screen_class", "unknown"))
    image_screen_class = str(classification.get("image_screen_class", "unknown"))
    if stage == "stock-adjustments-screen" and image_screen_class != "stock_adjustments":
        return False, f"image not classified as stock_adjustments: {image_screen_class}"
    if screen_class in FORBIDDEN_CLASSIFIED_SCREENS:
        return False, f"classified as forbidden screen: {screen_class}"
    return True, f"classified as {screen_class}"


def find_line(sku: str) -> tuple[dict, dict]:
    manifest = load_json(RUNNER_MANIFEST)
    ledger = load_json(LEDGER)
    wanted = sku.strip().upper()
    item = next((entry for entry in manifest.get("items", []) if str(entry.get("sku", "")).upper() == wanted), None)
    ledger_entry = next((entry for entry in ledger.get("items", []) if str(entry.get("sku", "")).upper() == wanted), None)
    if not item:
        raise SystemExit(f"[ERROR] SKU not found in runner manifest: {sku}")
    if not ledger_entry:
        raise SystemExit(f"[ERROR] SKU not found in approval ledger: {sku}")
    return item, ledger_entry


def evidence_dir(item: dict) -> Path:
    return EVIDENCE_ROOT / f"{int(item.get('manifest_index', 0)):03d}_{slug(str(item.get('sku', '')))}"


def load_evidence_state(path: Path, item: dict) -> dict:
    state_path = path / "line_evidence.json"
    if state_path.exists():
        state = load_json(state_path)
    else:
        state = {
            "schema_version": "azyra-current-balance-line-evidence-v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "sku": item.get("sku"),
            "manifest_index": item.get("manifest_index"),
            "quantity": item.get("quantity"),
            "target_location": item.get("target_location"),
            "description": item.get("description"),
            "captures": {},
        }
    state.update(
        {
            "sku": item.get("sku"),
            "manifest_index": item.get("manifest_index"),
            "quantity": item.get("quantity"),
            "target_location": item.get("target_location"),
            "description": item.get("description"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    state.setdefault("captures", {})
    return state


def upgrade_capture_metadata(state: dict) -> bool:
    changed = False
    for bucket in ["captures", "rejected_captures"]:
        for stage, captures in state.get(bucket, {}).items():
            for capture in captures:
                if "screen_classification" not in capture:
                    text = "\n".join(
                        part
                        for part in [capture.get("operator_observation", ""), capture.get("description", "")]
                        if part
                    )
                    classification = classify_screen(text)
                    guard_ok, guard_reason = stage_guard(stage, classification)
                    capture.setdefault("ocr", {"engine": "unavailable", "reason": "not run for legacy capture"})
                    capture["screen_classification"] = classification
                    capture["stage_guard_passed"] = guard_ok
                    capture["stage_guard_reason"] = guard_reason
                    changed = True
    if changed:
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
    return changed


def capture_screen(stage: str, out_dir: Path, observation: str = "") -> tuple[Path, dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    path = out_dir / f"{stage}_{stamp}.png"
    bridge = AzyraOperatorBridge(allow_input=False, allow_submit=False)
    discovery = bridge.discover()
    result = bridge.capture_screen(str(path), window_only=True)
    ocr_text, ocr_info = optional_ocr(path)
    combined_text = "\n".join(part for part in [observation, ocr_text] if part)
    classification = classify_screen(combined_text)
    image_classification = classify_image_screen(path)
    image_screen_class = str(image_classification.get("screen_class", "unknown"))
    classification = {
        **classification,
        "image_screen_class": image_screen_class,
        "image_confidence": image_classification.get("confidence"),
        "image_distance": image_classification.get("distance"),
    }
    if image_screen_class in FORBIDDEN_CLASSIFIED_SCREENS or classification.get("screen_class") == "unknown":
        classification = {
            **classification,
            "screen_class": image_screen_class,
        }
    guard_ok, guard_reason = stage_guard(stage, classification)
    return path, {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "path": str(path.resolve()),
        "ok": result.ok,
        "reason": result.reason,
        "window_found": bool(discovery.get("window_found")),
        "description": STAGES[stage]["description"],
        "operator_observation": observation,
        "ocr": ocr_info,
        "screen_classification": classification,
        "image_screen_classification": image_classification,
        "stage_guard_passed": guard_ok,
        "stage_guard_reason": guard_reason,
    }


def latest_paths(state: dict) -> dict[str, str]:
    found = {}
    for stage, meta in STAGES.items():
        field = meta["field"]
        if not field:
            continue
        captures = state.get("captures", {}).get(stage, [])
        if captures:
            found[field] = str(captures[-1].get("path", ""))
    return found


def iter_recent_captures(state: dict) -> list[tuple[str, str, dict]]:
    recent = []
    for bucket in ["captures", "rejected_captures"]:
        for stage, captures in state.get(bucket, {}).items():
            for capture in captures[-3:]:
                label = stage if bucket == "captures" else f"{stage} rejected"
                recent.append((capture.get("captured_at", ""), label, capture))
    return sorted(recent, reverse=True)[:8]


def ps_quote(value: str) -> str:
    return '"' + value.replace('"', '`"') + '"'


def build_approval_command(item: dict, paths: dict[str, str], approved_by: str) -> str:
    notes = (
        f"{item.get('sku')} current balance verified; no pick/dispatch/movement explains discrepancy; "
        f"approved for +{item.get('quantity')} units at {item.get('target_location')}."
    )
    return "\n".join(
        [
            'cd "C:\\Users\\Gary.Leckey\\OneDrive - SFG Forwarding Ltd\\Documents\\sfg azrya intergrations\\aureon-trading"',
            ".\\.venv\\Scripts\\python.exe .\\approve_current_balance_line.py `",
            f"  --sku {item.get('sku')} `",
            f"  --approved-by {ps_quote(approved_by)} `",
            f"  --stock-adjustments-screen-evidence {ps_quote(paths.get('stock_adjustments_screen_evidence', PLACEHOLDER_STOCK_ADJUSTMENTS))} `",
            f"  --before-balance-evidence {ps_quote(paths.get('before_balance_evidence', PLACEHOLDER_BEFORE_BALANCE))} `",
            f"  --movement-check-evidence {ps_quote(paths.get('movement_check_evidence', PLACEHOLDER_MOVEMENT_CHECK))} `",
            f"  --notes {ps_quote(notes)} `",
            "  --confirm-stock-adjustments-screen",
        ]
    )


def build_evidence_approval_command(item: dict, approved_by: str) -> str:
    return "\n".join(
        [
            'cd "C:\\Users\\Gary.Leckey\\OneDrive - SFG Forwarding Ltd\\Documents\\sfg azrya intergrations\\aureon-trading"',
            ".\\.venv\\Scripts\\python.exe .\\current_balance_evidence_to_ledger.py `",
            f"  --sku {item.get('sku')} `",
            "  --approve-pre-entry `",
            f"  --operator {ps_quote(approved_by)} `",
            "  --confirm-evidence-reviewed",
        ]
    )


def build_closeout_command(item: dict, paths: dict[str, str], closed_by: str) -> str:
    notes = f"{item.get('sku')} +{item.get('quantity')} posted and after-balance verified."
    return "\n".join(
        [
            'cd "C:\\Users\\Gary.Leckey\\OneDrive - SFG Forwarding Ltd\\Documents\\sfg azrya intergrations\\aureon-trading"',
            ".\\.venv\\Scripts\\python.exe .\\close_current_balance_line.py `",
            f"  --sku {item.get('sku')} `",
            f"  --closed-by {ps_quote(closed_by)} `",
            f"  --entered-line-evidence {ps_quote(paths.get('entered_line_evidence', PLACEHOLDER_ENTERED_LINE))} `",
            f"  --posted-transaction-evidence {ps_quote(paths.get('posted_transaction_evidence', PLACEHOLDER_POSTED_TRANSACTION))} `",
            '  --posted-transaction-reference "Azyra adjustment reference" `',
            f"  --after-balance-evidence {ps_quote(paths.get('after_balance_evidence', PLACEHOLDER_AFTER_BALANCE))} `",
            f"  --notes {ps_quote(notes)}",
        ]
    )


def build_evidence_closeout_command(item: dict, closed_by: str) -> str:
    return "\n".join(
        [
            'cd "C:\\Users\\Gary.Leckey\\OneDrive - SFG Forwarding Ltd\\Documents\\sfg azrya intergrations\\aureon-trading"',
            ".\\.venv\\Scripts\\python.exe .\\current_balance_evidence_to_ledger.py `",
            f"  --sku {item.get('sku')} `",
            "  --closeout-post-entry `",
            f"  --operator {ps_quote(closed_by)} `",
            '  --posted-transaction-reference "Azyra adjustment reference" `',
            "  --confirm-evidence-reviewed",
        ]
    )


def build_live_run_import_command(item: dict, operator: str) -> str:
    return "\n".join(
        [
            'cd "C:\\Users\\Gary.Leckey\\OneDrive - SFG Forwarding Ltd\\Documents\\sfg azrya intergrations\\aureon-trading"',
            ".\\.venv\\Scripts\\python.exe .\\current_balance_import_live_run_evidence.py `",
            f"  --sku {item.get('sku')} `",
            '  --summary "C:\\path\\to\\live_execution_summary.json" `',
            f"  --operator {ps_quote(operator)} `",
            "  --confirm-live-run-reviewed",
        ]
    )


def write_status_markdown(out_dir: Path, item: dict, ledger_entry: dict, state: dict, approved_by: str, closed_by: str) -> None:
    paths = latest_paths(state)
    missing_pre = [field for field in PRE_ENTRY_FIELDS if not paths.get(field) and not ledger_entry.get(field)]
    missing_close = [field for field in CLOSEOUT_FIELDS if not paths.get(field) and not ledger_entry.get(field)]
    approval_command = build_approval_command(item, {**paths, **{k: v for k, v in ledger_entry.items() if k in PRE_ENTRY_FIELDS and v}}, approved_by)
    closeout_command = build_closeout_command(item, {**paths, **{k: v for k, v in ledger_entry.items() if k in CLOSEOUT_FIELDS and v}}, closed_by)
    evidence_approval_command = build_evidence_approval_command(item, approved_by)
    evidence_closeout_command = build_evidence_closeout_command(item, closed_by)
    live_run_import_command = build_live_run_import_command(item, closed_by)
    md = [
        f"# {item.get('sku')} Current-Balance Evidence",
        "",
        f"- Description: `{item.get('description')}`",
        f"- Quantity: `{item.get('quantity')}` units",
        f"- Target location: `{item.get('target_location')}`",
        f"- Approval status: `{ledger_entry.get('approval_status')}`",
        f"- Closeout status: `{ledger_entry.get('closeout_status')}`",
        "",
        "## Pre-Entry Evidence",
    ]
    for field in PRE_ENTRY_FIELDS:
        value = paths.get(field) or ledger_entry.get(field) or ""
        mark = "x" if value else " "
        md.append(f"- [{mark}] `{field}` {value}")
    md.extend(["", "## Closeout Evidence"])
    for field in CLOSEOUT_FIELDS:
        value = paths.get(field) or ledger_entry.get(field) or ""
        mark = "x" if value else " "
        md.append(f"- [{mark}] `{field}` {value}")
    md.extend(
        [
            "",
            f"Missing pre-entry fields: `{', '.join(missing_pre) if missing_pre else 'none'}`",
            f"Missing closeout fields: `{', '.join(missing_close) if missing_close else 'none'}`",
            "",
            "Evidence freshness: approval and closeout helpers reject captured evidence older than 60 minutes by default. Recapture the line evidence if the Azyra screen or balance may have changed.",
            "",
            "## Recent Captures",
        ]
    )
    for _, stage, capture in iter_recent_captures(state):
        note = capture.get("operator_observation") or capture.get("description") or ""
        classification = capture.get("screen_classification", {}).get("screen_class", "unknown")
        guard = capture.get("stage_guard_reason", "")
        md.append(f"- `{stage}` `{classification}` {capture.get('path', '')} {note} {guard}")
    md.extend(
        [
            "",
            "## Approval Command",
            "",
            "```powershell",
            evidence_approval_command,
            "```",
            "",
            "## Manual Approval Fallback",
            "",
            "```powershell",
            approval_command,
            "```",
            "",
            "## Closeout Command",
            "",
            "```powershell",
            evidence_closeout_command,
            "```",
            "",
            "## Import Live Runner Evidence",
            "",
            "```powershell",
            live_run_import_command,
            "```",
            "",
            "## Manual Closeout Fallback",
            "",
            "```powershell",
            closeout_command,
            "```",
            "",
        ]
    )
    (out_dir / "line_evidence_status.md").write_text("\n".join(md), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture non-mutating Azyra evidence for one current-balance line.")
    parser.add_argument("--sku", default="LP4073")
    parser.add_argument("--stage", choices=sorted(STAGES), help="Evidence stage to capture.")
    parser.add_argument("--status", action="store_true", help="Write/read status without capturing a new screenshot.")
    parser.add_argument("--approved-by", default="Gary Leckey")
    parser.add_argument("--closed-by", default="Gary Leckey")
    parser.add_argument("--observation", default="", help="Short operator note to attach to a captured screenshot.")
    parser.add_argument("--confirm-stock-adjustments-screen", action="store_true")
    parser.add_argument("--confirm-current-balance-screen", action="store_true")
    parser.add_argument("--confirm-movement-check-screen", action="store_true")
    parser.add_argument("--confirm-entered-line-screen", action="store_true")
    parser.add_argument("--confirm-posted-transaction-screen", action="store_true")
    parser.add_argument("--confirm-after-balance-screen", action="store_true")
    args = parser.parse_args()

    if not args.stage and not args.status:
        parser.error("provide --stage to capture evidence, or --status to refresh the evidence status")

    item, ledger_entry = find_line(args.sku)
    out_dir = evidence_dir(item)
    out_dir.mkdir(parents=True, exist_ok=True)
    state = load_evidence_state(out_dir, item)
    state_changed = upgrade_capture_metadata(state)

    if args.stage:
        confirm_arg = STAGES[args.stage]["confirm_arg"]
        if confirm_arg and not getattr(args, confirm_arg):
            print(f"[ERROR] --{confirm_arg.replace('_', '-')} is required for stage {args.stage}.")
            return 1
        if args.stage != "current-screen-probe" and not args.observation.strip():
            print(f"[ERROR] --observation is required for classified evidence stage {args.stage}.")
            return 1
        path, capture = capture_screen(args.stage, out_dir, observation=args.observation)
        if not capture.get("stage_guard_passed", True):
            state.setdefault("rejected_captures", {}).setdefault(args.stage, []).append(capture)
            save_json(out_dir / "line_evidence.json", state)
            write_status_markdown(out_dir, item, ledger_entry, state, args.approved_by, args.closed_by)
            print(
                json.dumps(
                    {
                        "rejected": str(path.resolve()),
                        "stage": args.stage,
                        "reason": capture.get("stage_guard_reason"),
                        "screen_classification": capture.get("screen_classification", {}),
                    },
                    indent=2,
                )
            )
            return 1
        state.setdefault("captures", {}).setdefault(args.stage, []).append(capture)
        save_json(out_dir / "line_evidence.json", state)
        print(json.dumps({"captured": str(path.resolve()), "stage": args.stage, "ok": capture["ok"]}, indent=2))
    elif state_changed:
        save_json(out_dir / "line_evidence.json", state)

    write_status_markdown(out_dir, item, ledger_entry, state, args.approved_by, args.closed_by)
    paths = latest_paths(state)
    status = {
        "sku": item.get("sku"),
        "evidence_dir": str(out_dir.resolve()),
        "line_status": str(out_dir / "line_evidence_status.md"),
        "pre_entry_missing": [field for field in PRE_ENTRY_FIELDS if not paths.get(field) and not ledger_entry.get(field)],
        "closeout_missing": [field for field in CLOSEOUT_FIELDS if not paths.get(field) and not ledger_entry.get(field)],
        "ledger_approval_status": ledger_entry.get("approval_status"),
        "ledger_closeout_status": ledger_entry.get("closeout_status"),
    }
    print(json.dumps(status, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
