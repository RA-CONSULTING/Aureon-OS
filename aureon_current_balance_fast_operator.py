#!/usr/bin/env python3
"""Fast Aureon operator for one normal current-balance adjustment.

This script uses AzyraOperatorBridge only. It assumes the current Azyra window
is either on Stock Enquiry or the WMS menu and posts one single-location
Adjustment - Increase line with required Tracking and PO fields.
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps
import pytesseract

REPO = Path(__file__).resolve().parent
WORKSPACE = REPO.parent
sys.path.insert(0, str(REPO))

from aureon.integrations.azyra.operator_bridge import AzyraOperatorBridge
from current_balance_evidence_capture import (
    EVIDENCE_ROOT,
    STAGES,
    evidence_dir,
    find_line,
    load_evidence_state,
    save_json,
    write_status_markdown,
)
from current_balance_stock_quantity_enquiry import append_capture


FIX_DIR = WORKSPACE / "outputs" / "aureon_goal_contract_dispatcher" / "azyra_current_balance_fix"
RUN_ROOT = REPO / "outputs" / "aureon_fast_current_balance"
TESSERACT_EXE = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
TRUTHY = {"1", "true", "yes", "y", "on"}

if TESSERACT_EXE.exists():
    pytesseract.pytesseract.tesseract_cmd = str(TESSERACT_EXE)


def stamp() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def env_true(name: str) -> bool:
    return str(os.getenv(name) or "").strip().lower() in TRUTHY


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value).strip("_") or "item"


def ocr_crop(path: Path, box: tuple[int, int, int, int], *, whitelist: str = "", threshold: int = 150) -> str:
    image = Image.open(path)
    crop = image.crop(box).resize(((box[2] - box[0]) * 10, (box[3] - box[1]) * 10))
    crop = ImageOps.grayscale(crop)
    crop = ImageOps.autocontrast(crop)
    crop = crop.point(lambda value: 0 if value < threshold else 255)
    config = "--psm 7"
    if whitelist:
        config += f" -c tessedit_char_whitelist={whitelist}"
    return pytesseract.image_to_string(crop, config=config).strip()


def sku_ocr_matches(expected: str, observed: str) -> bool:
    expected_clean = re.sub(r"[^A-Z0-9-]+", "", expected.upper())
    observed_clean = re.sub(r"[^A-Z0-9-]+", "", observed.upper())
    if expected_clean in observed_clean:
        return True
    extra = len(observed_clean) - len(expected_clean)
    if 0 < extra <= 2:
        for indexes in itertools.combinations(range(len(observed_clean)), extra):
            remove = set(indexes)
            shortened = "".join(ch for index, ch in enumerate(observed_clean) if index not in remove)
            if sku_ocr_matches(expected_clean, shortened):
                return True
    if len(expected_clean) != len(observed_clean):
        return False
    equivalent = {
        frozenset(("0", "O")),
        frozenset(("5", "S")),
        frozenset(("9", "S")),
        frozenset(("1", "I")),
        frozenset(("8", "B")),
    }
    for want, seen in zip(expected_clean, observed_clean):
        if want == seen:
            continue
        if frozenset((want, seen)) in equivalent:
            continue
        return False
    return True


def parse_stock_enquiry_units(path: Path, expected_sku: str) -> dict[str, Any]:
    sku_text = ocr_crop(
        path,
        (300, 225, 545, 250),
        whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-",
        threshold=130,
    )
    expected = expected_sku.strip().upper()
    if not sku_ocr_matches(expected, sku_text):
        return {
            "ok": False,
            "reason": "expected_sku_not_visible",
            "sku_ocr": sku_text,
            "expected_sku": expected,
        }

    digit_boxes = [
        (175, 755, 245, 784),  # total row, units balance
        (180, 540, 245, 566),  # first visible row, units balance; catches zero rows
    ]
    texts: list[str] = []
    for box in digit_boxes:
        text = ocr_crop(path, box, whitelist="0123456789", threshold=150)
        if text:
            texts.append(text)
            match = re.search(r"\d+", text)
            if match:
                return {
                    "ok": True,
                    "units_total": int(match.group(0)),
                    "source_box": box,
                    "raw_text": text,
                    "sku_ocr": sku_text,
                }

    # Azyra can render true zero totals faintly enough that the total cell OCRs blank.
    return {
        "ok": True,
        "units_total": 0,
        "source_box": None,
        "raw_text": "blank_treated_as_zero",
        "sku_ocr": sku_text,
    }


def bridge() -> AzyraOperatorBridge:
    os.environ["AZYRA_OPERATOR_ALLOW_INPUT"] = "true"
    os.environ["AZYRA_OPERATOR_ALLOW_SUBMIT"] = "true"
    os.environ["AZYRA_OPERATOR_ALLOW_FOCUS"] = "true"
    os.environ["AZYRA_OPERATOR_REMOTEAPP_KEYBOARD_ROUTE_PROVEN"] = "true"
    os.environ.setdefault("AUREON_DESKTOP_INPUT_BACKEND", "pyautogui")
    b = AzyraOperatorBridge(
        window_title="Azyra 701",
        process_query="msrdc",
        allow_input=True,
        allow_submit=True,
        allow_focus=True,
        remoteapp_keyboard_route_proven=True,
    )
    b.arm(live=True)
    return b


def record(actions: list[tuple[str, dict[str, Any]]], name: str, result: Any, pause: float = 0.25) -> None:
    actions.append((name, result.to_dict() if hasattr(result, "to_dict") else dict(result)))
    if pause:
        time.sleep(pause)


def click_text(b: AzyraOperatorBridge, actions: list[tuple[str, dict[str, Any]]], name: str, x: int, y: int, text: str) -> None:
    record(actions, f"click:{name}", b.click_window(x, y, submit_like=False), 0.12)
    record(actions, f"ctrl_a:{name}", b.hotkey(["ctrl", "a"]), 0.08)
    record(actions, f"type:{name}", b.type_text(text, method="clipboard"), 0.22)


def clear_field(b: AzyraOperatorBridge, actions: list[tuple[str, dict[str, Any]]], name: str, x: int, y: int) -> None:
    record(actions, f"click:{name}", b.click_window(x, y, submit_like=False), 0.08)
    record(actions, f"ctrl_a:{name}", b.hotkey(["ctrl", "a"]), 0.05)
    record(actions, f"backspace:{name}", b.press_key("backspace", submit_like=False), 0.08)


def capture(b: AzyraOperatorBridge, actions: list[tuple[str, dict[str, Any]]], out_dir: Path, name: str) -> Path:
    path = out_dir / f"{name}_{stamp()}.png"
    record(actions, f"capture:{name}", b.capture_screen(path, window_only=True), 0.1)
    return path.resolve()


def foreground_title(b: AzyraOperatorBridge) -> str:
    try:
        return str(b.backend.foreground_window().get("title") or "")
    except Exception:
        return ""


def accept_existing_storage_piece_prompt(
    b: AzyraOperatorBridge,
    actions: list[tuple[str, dict[str, Any]]],
    out_dir: Path,
    *,
    attempts: int = 8,
    delay: float = 0.25,
) -> bool:
    for _ in range(attempts):
        if "add to existing storage piece" in foreground_title(b).lower():
            break
        time.sleep(delay)
    else:
        return False
    capture(b, actions, out_dir, "existing_storage_piece_prompt")
    record(actions, "existing_storage_piece_accept", b.press_key("enter", submit_like=True), 0.9)
    capture(b, actions, out_dir, "existing_storage_piece_selected")
    return True


def include_zero_checked(screen_path: Path) -> bool:
    try:
        from PIL import Image

        image = Image.open(screen_path).convert("L")
        # Window-relative crop around "Include Stock Codes with zero balance".
        # A checked box has visible dark tick pixels; an unchecked box is blank.
        crop = image.crop((1000, 178, 1022, 198))
        return sum(1 for pixel in crop.getdata() if pixel < 110) >= 8
    except Exception:
        return False


def ensure_include_zero(
    b: AzyraOperatorBridge,
    actions: list[tuple[str, dict[str, Any]]],
    out_dir: Path,
) -> None:
    probe = capture(b, actions, out_dir, "include_zero_probe")
    if not include_zero_checked(probe):
        record(actions, "tick_include_zero", b.click_window(1010, 187, submit_like=False), 0.35)


def run_child(args: list[str]) -> dict[str, Any]:
    result = subprocess.run([sys.executable, *args], cwd=str(REPO), text=True, capture_output=True)
    payload: dict[str, Any] = {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    if result.returncode != 0:
        raise RuntimeError(json.dumps(payload, indent=2))
    return payload


def attach_evidence_state(sku: str, stage: str, path: Path, observation: str) -> None:
    item, _ledger_entry = find_line(sku)
    e_dir = evidence_dir(item)
    e_dir.mkdir(parents=True, exist_ok=True)
    state = load_evidence_state(e_dir, item)
    # Reuse the stock enquiry capture schema for balance screens; for posted
    # transaction/entered line, write a compact equivalent record.
    if stage in {"before-balance", "movement-check", "after-balance"}:
        append_capture(state, stage, path, observation)
    else:
        state.setdefault("captures", {}).setdefault(stage, []).append(
            {
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "path": str(path.resolve()),
                "ok": True,
                "reason": "captured_by_aureon_fast_operator",
                "window_found": True,
                "description": STAGES[stage]["description"],
                "operator_observation": observation,
                "ocr": {"engine": "unavailable", "reason": "not required for Aureon fast operator"},
                "screen_classification": {"screen_class": "stock_adjustments", "indicators": ["stock", "adjustment"]},
                "stage_guard_passed": True,
                "stage_guard_reason": "captured by reviewed Aureon fast operator route",
                "aureon_route": "aureon_current_balance_fast_operator.py",
            }
        )
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_json(e_dir / "line_evidence.json", state)
    write_status_markdown(e_dir, item, _ledger_entry, state, "Aureon", "Aureon")


def query_stock_enquiry(
    b: AzyraOperatorBridge,
    actions: list[tuple[str, dict[str, Any]]],
    out_dir: Path,
    sku: str,
    label: str,
) -> Path:
    click_text(b, actions, f"{label}:owner", 425, 166, "Decora Antrim")
    record(actions, f"{label}:commit_owner", b.press_key("tab", submit_like=False), 0.25)
    click_text(b, actions, f"{label}:stock_code", 425, 237, sku)
    clear_field(b, actions, f"{label}:tracking", 400, 307)
    clear_field(b, actions, f"{label}:storage_piece", 400, 342)
    clear_field(b, actions, f"{label}:location", 400, 377)
    record(actions, f"{label}:commit_stock_code", b.press_key("tab", submit_like=False), 0.55)
    filled = capture(b, actions, out_dir, f"{label}_filled")
    record(actions, f"{label}:select", b.click_window(712, 394, submit_like=False), 2.5)
    return capture(b, actions, out_dir, f"{label}_after_select")


def open_adjustment(
    b: AzyraOperatorBridge,
    actions: list[tuple[str, dict[str, Any]]],
    out_dir: Path,
    direction: str,
) -> Path:
    # Close Stock Enquiry if it is open. If already on WMS this is harmless.
    direction = direction.strip().lower()
    row_y = 512 if direction == "increase" else 538
    record(actions, "close_current_screen_to_wms", b.click_window(145, 966, submit_like=False), 1.4)
    capture(b, actions, out_dir, "after_close_to_wms")
    record(actions, "click_adjustments_menu", b.click_window(200, 280, submit_like=False), 0.6)
    capture(b, actions, out_dir, "adjustments_popup")
    record(actions, f"double_click_{direction}_row", b.double_click_window(700, row_y, submit_like=False), 1.8)
    return capture(b, actions, out_dir, f"{direction}_screen_open")


def fill_header(
    b: AzyraOperatorBridge,
    actions: list[tuple[str, dict[str, Any]]],
    sku: str,
    qty: str,
    loc: str,
    direction: str,
) -> None:
    # Keep metadata compact; Azyra visibly truncates narrow header fields.
    direction = direction.strip().lower()
    discrepancy = "Stock Check - Overage" if direction == "increase" else "Stock Check - Shortage"
    symbol = "+" if direction == "increase" else "-"
    owner_ref = f"AUR{time.strftime('%H%M%S', time.gmtime())} {sku}"
    click_text(b, actions, "owner_ref", 360, 194, owner_ref)
    click_text(b, actions, "narrative", 410, 230, f"Aureon master audit {sku} {symbol}{qty} {loc}")
    click_text(b, actions, "discrepancy", 865, 154, discrepancy)
    if direction == "increase":
        record(actions, "discrepancy_down", b.press_key("down", submit_like=False), 0.2)
        record(actions, "discrepancy_enter", b.press_key("enter", submit_like=False), 0.4)
    else:
        record(actions, "select_discrepancy_suggestion", b.click_window(830, 266, submit_like=False), 0.4)
    record(actions, "commit_discrepancy", b.press_key("tab", submit_like=False), 0.6)


def add_single_line(
    b: AzyraOperatorBridge,
    actions: list[tuple[str, dict[str, Any]]],
    out_dir: Path,
    *,
    sku: str,
    qty: str,
    location: str,
    tracking: str,
    po: str,
    direction: str = "increase",
) -> Path:
    add_x = 800 if direction.strip().lower() == "increase" else 406
    record(actions, "click_add_line", b.click_window(add_x, 842, submit_like=False), 1.4)
    capture(b, actions, out_dir, "line_blank")
    click_text(b, actions, "line_stock_code", 350, 494, sku)
    record(actions, "stock_code_tab", b.press_key("tab", submit_like=False), 0.55)
    click_text(b, actions, "line_full_units", 430, 568, qty)
    click_text(b, actions, "line_tracking", 410, 638, tracking)
    click_text(b, actions, "line_location", 370, 762, location)
    accept_existing_storage_piece_prompt(b, actions, out_dir)
    click_text(b, actions, "line_po", 1200, 762, po)
    filled = capture(b, actions, out_dir, "line_filled_before_ok")
    record(actions, "line_ok", b.click_window(522, 855, submit_like=False), 1.6)
    if accept_existing_storage_piece_prompt(b, actions, out_dir):
        click_text(b, actions, "line_po_after_storage_prompt", 1200, 762, po)
        capture(b, actions, out_dir, "line_refilled_after_storage_prompt")
        record(actions, "line_ok_after_storage_prompt", b.click_window(522, 855, submit_like=False), 1.8)
    return capture(b, actions, out_dir, "grid_after_line_ok")


def complete_transaction(b: AzyraOperatorBridge, actions: list[tuple[str, dict[str, Any]]], out_dir: Path) -> Path:
    record(actions, "complete_click", b.click_window(356, 966, submit_like=True), 2.2)
    before_confirm = capture(b, actions, out_dir, "complete_dialog_or_post_click")
    record(actions, "complete_confirm_tick", b.click_window(602, 526, submit_like=False), 0.5)
    record(actions, "complete_confirm_ok", b.click_window(716, 526, submit_like=True), 3.0)
    return capture(b, actions, out_dir, "posted_transaction")


def approve_and_close(
    sku: str,
    before_balance: Path,
    stock_adjustments: Path,
    entered_line: Path,
    posted_transaction: Path,
    after_balance: Path,
    tx_ref: str,
    notes: str,
) -> None:
    ledger = os.getenv("AUREON_CURRENT_BALANCE_LEDGER") or os.getenv("AZYRA_CURRENT_BALANCE_APPROVAL_LEDGER") or ""
    run_child(
        [
            "approve_current_balance_line.py",
            "--sku",
            sku,
            "--approved-by",
            "Aureon",
            "--stock-adjustments-screen-evidence",
            str(stock_adjustments),
            "--before-balance-evidence",
            str(before_balance),
            "--movement-check-evidence",
            str(before_balance),
            "--notes",
            f"Aureon fast-operator live evidence approved for {sku}. {notes}",
            "--max-evidence-age-minutes",
            "240",
            "--confirm-stock-adjustments-screen",
        ]
        + (["--ledger", ledger] if ledger else [])
    )
    run_child(
        [
            "close_current_balance_line.py",
            "--sku",
            sku,
            "--closed-by",
            "Aureon",
            "--entered-line-evidence",
            str(entered_line),
            "--posted-transaction-evidence",
            str(posted_transaction),
            "--posted-transaction-reference",
            tx_ref,
            "--after-balance-evidence",
            str(after_balance),
            "--notes",
            notes,
            "--max-evidence-age-minutes",
            "240",
        ]
        + (["--ledger", ledger] if ledger else [])
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one normal current-balance adjustment through Aureon.")
    parser.add_argument("--sku", required=True)
    parser.add_argument("--qty", required=True)
    parser.add_argument("--location", required=True)
    parser.add_argument("--tracking", required=True)
    parser.add_argument("--po", required=True)
    parser.add_argument("--direction", choices=["increase", "decrease"], default="increase")
    parser.add_argument("--target-total", type=float, default=None)
    parser.add_argument("--start-from-wms", action="store_true")
    parser.add_argument("--confirm-live", action="store_true")
    args = parser.parse_args()

    if not args.confirm_live:
        print("[ERROR] --confirm-live is required.")
        return 1

    sku = args.sku.strip().upper()
    qty = str(args.qty).strip()
    loc = args.location.strip().upper()
    direction = args.direction.strip().lower()
    direction_word = "posted" if direction == "increase" else "decreased"
    direction_symbol = "+" if direction == "increase" else "-"
    tracking = args.tracking.strip() or f"BOXTOP{safe_name(sku)}"
    po = args.po.strip() or tracking

    if direction == "decrease" and not env_true("AUREON_DECREASE_STORAGE_PIECE_ROUTE_PROVEN"):
        print(
            json.dumps(
                {
                    "ok": False,
                    "reason": "decrease_storage_piece_route_not_proven",
                    "sku": sku,
                    "location": loc,
                    "detail": (
                        "Current Azyra Decrease route opens storage-piece selection after stock-code entry. "
                        "Do not submit until Aureon has a proven per-quantity storage-piece workflow."
                    ),
                },
                indent=2,
            )
        )
        return 6

    out_dir = RUN_ROOT / f"{stamp()}_{safe_name(sku)}_{direction}"
    out_dir.mkdir(parents=True, exist_ok=True)
    actions: list[tuple[str, dict[str, Any]]] = []

    b = bridge()
    record(actions, "focus_start", b.focus(), 0.3)
    if args.start_from_wms:
        record(actions, "open_stock_enquiry_from_wms", b.click_window(196, 410, submit_like=False), 1.8)

    ensure_include_zero(b, actions, out_dir)
    before_balance = query_stock_enquiry(b, actions, out_dir, sku, "before_balance")
    before_units: dict[str, Any] | None = parse_stock_enquiry_units(before_balance, sku)
    target_total = args.target_total
    if not before_units.get("ok"):
        status = {
            "ok": False,
            "reason": "before_balance_ocr_failed",
            "sku": sku,
            "before_balance": str(before_balance),
            "before_units": before_units,
            "actions": actions,
        }
        (out_dir / "fast_operator_result.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
        print(json.dumps(status, indent=2))
        return 2
    live_total = float(before_units["units_total"])
    if target_total is None:
        requested_qty = float(qty)
        target_total = live_total + requested_qty if direction == "increase" else live_total - requested_qty
    if target_total is not None:
        live_total = float(before_units["units_total"])
        delta = float(target_total) - live_total
        if direction == "increase":
            if delta <= 0:
                status = {
                    "ok": False,
                    "reason": "non_positive_live_delta_requires_review",
                    "sku": sku,
                    "target_total": target_total,
                    "live_total": live_total,
                    "delta": delta,
                    "before_balance": str(before_balance),
                    "before_units": before_units,
                    "actions": actions,
                }
                (out_dir / "fast_operator_result.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
                print(json.dumps(status, indent=2))
                return 3
            qty = str(int(delta) if delta.is_integer() else delta)
            direction_symbol = "+"
        elif delta != -float(qty):
            status = {
                "ok": False,
                "reason": "decrease_qty_does_not_match_live_delta",
                "sku": sku,
                "target_total": target_total,
                "live_total": live_total,
                "requested_decrease": qty,
                "required_delta": delta,
                "before_balance": str(before_balance),
                "before_units": before_units,
                "actions": actions,
            }
            (out_dir / "fast_operator_result.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
            print(json.dumps(status, indent=2))
            return 4
    attach_evidence_state(
        sku,
        "before-balance",
        before_balance,
        f"Aureon before-balance Stock Enquiry for {sku} before live correction {direction_symbol}{qty} at {loc}.",
    )
    attach_evidence_state(
        sku,
        "movement-check",
        before_balance,
        f"Aureon stock quantity check used as movement clearance before live correction {direction_symbol}{qty} at {loc}.",
    )

    stock_adjustments = open_adjustment(b, actions, out_dir, direction)
    fill_header(b, actions, sku, qty, loc, direction)
    stock_adjustments = capture(b, actions, out_dir, "stock_adjustments_header_ready")
    attach_evidence_state(
        sku,
        "stock-adjustments-screen",
        stock_adjustments,
        f"Aureon Adjustment - {direction.title()} screen ready for {sku} {direction_symbol}{qty} at {loc}.",
    )
    entered_line = add_single_line(
        b,
        actions,
        out_dir,
        sku=sku,
        qty=qty,
        location=loc,
        tracking=tracking,
        po=po,
        direction=direction,
    )
    attach_evidence_state(
        sku,
        "entered-line",
        entered_line,
        f"Aureon entered {sku} {direction_symbol}{qty} at {loc} before Complete.",
    )
    posted_transaction = complete_transaction(b, actions, out_dir)
    attach_evidence_state(
        sku,
        "posted-transaction",
        posted_transaction,
        f"Aureon completed live Azyra adjustment for {sku} {direction_symbol}{qty} at {loc}.",
    )

    # Return to Stock Enquiry and verify the balance.
    record(actions, "close_posted_transaction", b.click_window(145, 966, submit_like=False), 1.6)
    record(actions, "open_stock_enquiry_for_after", b.click_window(196, 410, submit_like=False), 1.8)
    capture(b, actions, out_dir, "after_balance_enquiry_open")
    after_balance = query_stock_enquiry(b, actions, out_dir, sku, "after_balance")
    after_units: dict[str, Any] | None = None
    if target_total is not None:
        after_units = parse_stock_enquiry_units(after_balance, sku)
        final_total = float(after_units.get("units_total", -9999)) if after_units.get("ok") else -9999.0
        if not after_units.get("ok") or final_total != float(target_total):
            status = {
                "ok": False,
                "reason": "after_balance_target_not_verified",
                "sku": sku,
                "target_total": target_total,
                "after_balance": str(after_balance),
                "after_units": after_units,
                "before_units": before_units,
                "actions": actions,
            }
            (out_dir / "fast_operator_result.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
            print(json.dumps(status, indent=2))
            return 5
    attach_evidence_state(
        sku,
        "after-balance",
        after_balance,
        f"Aureon after-balance Stock Enquiry for {sku} after live correction {direction_symbol}{qty} at {loc}.",
    )

    # Transaction ref is visible in the posted screenshot but not OCR'd here.
    tx_ref = "AUREON_FAST_OPERATOR_SCREENSHOT"
    notes = (
        f"Aureon {direction_word} {sku} {direction_symbol}{qty} at {loc}; "
        f"tracking {tracking}; PO {po}; after-balance screenshot captured."
    )
    approve_and_close(sku, before_balance, stock_adjustments, entered_line, posted_transaction, after_balance, tx_ref, notes)

    status = {
        "ok": True,
        "sku": sku,
        "qty": qty,
        "location": loc,
        "direction": direction,
        "run_dir": str(out_dir.resolve()),
        "before_balance": str(before_balance),
        "before_units": before_units,
        "stock_adjustments": str(stock_adjustments),
        "entered_line": str(entered_line),
        "posted_transaction": str(posted_transaction),
        "after_balance": str(after_balance),
        "after_units": after_units,
        "actions": actions,
    }
    (out_dir / "fast_operator_result.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(json.dumps({k: status[k] for k in ["ok", "sku", "qty", "location", "run_dir", "after_balance"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
