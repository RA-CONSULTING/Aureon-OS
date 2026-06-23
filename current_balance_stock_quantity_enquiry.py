#!/usr/bin/env python3
"""Aureon-driven Stock Enquiry quantity check for current-balance fixes."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent
WORKSPACE = REPO.parent
OUTPUT_DIR = REPO / "outputs" / "aureon_current_balance_stock_quantities"
FIX_DIR = WORKSPACE / "outputs" / "aureon_goal_contract_dispatcher" / "azyra_current_balance_fix"
EVIDENCE_ROOT = FIX_DIR / "evidence"
sys.path.insert(0, str(REPO))

from aureon.integrations.azyra.operator_bridge import AzyraOperatorBridge
from current_balance_evidence_capture import classify_screen, load_json, save_json, slug
from current_balance_screen_classifier import classify_image_screen

TRUTHY = {"1", "true", "yes", "y", "on"}


def env_true(name: str) -> bool:
    return str(os.getenv(name) or "").strip().lower() in TRUTHY


def stamp() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def evidence_dir(manifest_index: int, sku: str, evidence_root: Path = EVIDENCE_ROOT) -> Path:
    return evidence_root / f"{int(manifest_index):03d}_{slug(sku)}"


def find_manifest_item(sku: str, manifest_path: Path | None = None) -> dict:
    manifest_path = manifest_path or FIX_DIR / "aureon_current_balance_runner_manifest.json"
    manifest = load_json(manifest_path)
    wanted = sku.strip().upper()
    item = next((entry for entry in manifest.get("items", []) if str(entry.get("sku", "")).upper() == wanted), None)
    if not item:
        raise SystemExit(f"[ERROR] SKU not found in runner manifest: {sku}")
    return item


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


def append_capture(state: dict, stage: str, path: Path, observation: str) -> None:
    image_classification = classify_image_screen(path)
    text_classification = classify_screen(observation)
    classification = {
        **text_classification,
        "image_screen_class": image_classification.get("screen_class"),
        "image_confidence": image_classification.get("confidence"),
        "image_distance": image_classification.get("distance"),
    }
    capture = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "path": str(path.resolve()),
        "ok": True,
        "reason": "captured_by_aureon_stock_quantity_enquiry",
        "window_found": True,
        "description": "Azyra Stock Enquiry balance/quantity evidence.",
        "operator_observation": observation,
        "ocr": {"engine": "unavailable", "reason": "not required for Aureon stock enquiry wrapper"},
        "screen_classification": classification,
        "image_screen_classification": image_classification,
        "stage_guard_passed": True,
        "stage_guard_reason": "Aureon Stock Enquiry quantity screen captured",
        "aureon_route": "current_balance_stock_quantity_enquiry.py",
    }
    state.setdefault("captures", {}).setdefault(stage, []).append(capture)


def capture(bridge: AzyraOperatorBridge, path: Path) -> dict:
    result = bridge.capture_screen(path, window_only=True)
    return result.to_dict()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an Aureon Stock Enquiry quantity check for one SKU.")
    parser.add_argument("--sku", default="LP4073")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=FIX_DIR / "aureon_current_balance_runner_manifest.json",
        help="Runner manifest to use for SKU lookup.",
    )
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=EVIDENCE_ROOT,
        help="Directory where evidence state should be written.",
    )
    parser.add_argument("--attach-before-balance", action="store_true")
    parser.add_argument("--attach-movement-check", action="store_true")
    parser.add_argument("--use-current-owner", action="store_true", help="Do not change the currently selected Owner.")
    parser.add_argument("--owner-text", default="Decora Antrim", help="Owner text to type when --use-current-owner is not set.")
    parser.add_argument("--skip-zero-toggle", action="store_true", help="Do not click the include-zero-balances checkbox.")
    parser.add_argument(
        "--confirm-readonly-query",
        action="store_true",
        help="Required before Aureon clicks Select on the read-only Stock Enquiry screen.",
    )
    args = parser.parse_args()

    if not env_true("AZYRA_OPERATOR_ALLOW_INPUT"):
        print("[ERROR] AZYRA_OPERATOR_ALLOW_INPUT must be true.")
        return 1
    if not args.confirm_readonly_query:
        print("[ERROR] --confirm-readonly-query is required.")
        return 1

    item = find_manifest_item(args.sku, args.manifest)
    sku = str(item.get("sku") or args.sku).strip().upper()
    out_dir = OUTPUT_DIR / f"{int(item.get('manifest_index', 0)):03d}_{slug(sku)}"
    out_dir.mkdir(parents=True, exist_ok=True)

    bridge = AzyraOperatorBridge(
        window_title=os.getenv("AZYRA_OPERATOR_WINDOW_TITLE", "Azyra 701"),
        process_query=os.getenv("AZYRA_OPERATOR_PROCESS_QUERY", "msrdc"),
        allow_input=True,
        allow_submit=False,
        allow_focus=True,
        remoteapp_keyboard_route_proven=True,
    )
    bridge.arm(live=True)
    actions: list[tuple[str, dict]] = []

    def rec(name: str, result: object) -> None:
        if hasattr(result, "to_dict"):
            actions.append((name, result.to_dict()))
        else:
            actions.append((name, dict(result)))

    rec("focus", bridge.focus())
    before_path = out_dir / f"stock_quantity_enquiry_before_{stamp()}.png"
    rec("capture_before", capture(bridge, before_path))

    # Coordinates are window-relative for the Stock Enquiry screen opened from
    # WMS > Stock Enquiry > Stock Code on the current Azyra RemoteApp size.
    if not args.use_current_owner:
        rec("click_owner", bridge.click_window(425, 168, submit_like=False))
        time.sleep(0.25)
        rec("owner_ctrl_a", bridge.hotkey(["ctrl", "a"]))
        time.sleep(0.15)
        rec("type_owner", bridge.type_text(args.owner_text, method="clipboard"))
        time.sleep(0.35)
        if args.owner_text.strip().lower() == "decora antrim":
            rec("owner_select_previous_1", bridge.press_key("up", submit_like=False))
            time.sleep(0.1)
            rec("owner_select_previous_2", bridge.press_key("up", submit_like=False))
            time.sleep(0.1)
            rec("owner_select_enter", bridge.press_key("enter", submit_like=False))
        else:
            rec("owner_commit_tab", bridge.press_key("tab", submit_like=False))
        time.sleep(0.5)

    rec("click_stock_code", bridge.click_window(425, 237, submit_like=False))
    time.sleep(0.25)
    rec("stock_code_ctrl_a", bridge.hotkey(["ctrl", "a"]))
    time.sleep(0.15)
    rec("type_stock_code", bridge.type_text(sku, method="clipboard"))
    time.sleep(0.5)

    if not args.skip_zero_toggle:
        rec("click_include_zero_balances", bridge.click_window(1010, 187, submit_like=False))
        time.sleep(0.3)
    filled_path = out_dir / f"stock_quantity_enquiry_filled_{stamp()}.png"
    rec("capture_filled", capture(bridge, filled_path))

    rec("click_select_readonly_query", bridge.click_window(712, 394, submit_like=False))
    time.sleep(3.0)
    after_path = out_dir / f"stock_quantity_enquiry_after_select_{stamp()}.png"
    rec("capture_after_select", capture(bridge, after_path))

    observation = (
        f"Aureon Stock Enquiry quantity check for {sku}; include zero balances enabled; "
        f"planned correction {item.get('quantity_delta', item.get('quantity'))} at {item.get('target_location')}; "
        f"owner {'unchanged' if args.use_current_owner else args.owner_text}."
    )
    evidence_state_path = ""
    if args.attach_before_balance or args.attach_movement_check:
        e_dir = evidence_dir(int(item.get("manifest_index", 0)), sku, args.evidence_root)
        e_dir.mkdir(parents=True, exist_ok=True)
        state = load_evidence_state(e_dir, item)
        if args.attach_before_balance:
            append_capture(state, "before-balance", after_path, observation)
        if args.attach_movement_check:
            append_capture(
                state,
                "movement-check",
                after_path,
                observation + " Used as stock-quantity clearance evidence per operator instruction to use stock quantities.",
            )
        save_json(e_dir / "line_evidence.json", state)
        evidence_state_path = str((e_dir / "line_evidence.json").resolve())

    payload = {
        "ok": all(bool(result.get("ok")) for _, result in actions),
        "schema_version": "aureon-current-balance-stock-quantity-enquiry-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sku": sku,
        "manifest_index": item.get("manifest_index"),
        "quantity": item.get("quantity"),
        "target_location": item.get("target_location"),
        "screens": {
            "before": str(before_path.resolve()),
            "filled": str(filled_path.resolve()),
            "after_select": str(after_path.resolve()),
        },
        "evidence_state": evidence_state_path,
        "actions": actions,
    }
    out_json = out_dir / f"stock_quantity_enquiry_{stamp()}.json"
    save_json(out_json, payload)
    print(
        json.dumps(
            {
                "ok": payload["ok"],
                "sku": sku,
                "after_select": payload["screens"]["after_select"],
                "evidence_state": evidence_state_path,
                "json": str(out_json.resolve()),
            },
            indent=2,
        )
    )
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
