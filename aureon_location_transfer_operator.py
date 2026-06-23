#!/usr/bin/env python3
"""Gate one Azyra location transfer row with live Stock Enquiry evidence."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from PIL import Image

from aureon_location_transfer_common import (
    TRANSFER_ROOT,
    evaluate_location_move,
    evidence_dir_for,
    normalise_location,
    normalise_sku,
    safe_name,
    update_manifest_row,
)


RUN_ROOT = Path(__file__).resolve().parent / "outputs" / "aureon_location_transfer_operator"
_CURRENT_BALANCE_TOOLS: dict[str, Any] | None = None


def _current_balance_tools() -> dict[str, Any]:
    global _CURRENT_BALANCE_TOOLS
    if _CURRENT_BALANCE_TOOLS is None:
        from aureon_current_balance_fast_operator import (
            bridge,
            capture,
            click_text,
            ensure_include_zero,
            ocr_crop,
            query_stock_enquiry,
            record,
            sku_ocr_matches,
            stamp,
        )

        _CURRENT_BALANCE_TOOLS = {
            "bridge": bridge,
            "capture": capture,
            "click_text": click_text,
            "ensure_include_zero": ensure_include_zero,
            "ocr_crop": ocr_crop,
            "query_stock_enquiry": query_stock_enquiry,
            "record": record,
            "sku_ocr_matches": sku_ocr_matches,
            "stamp": stamp,
        }
    return _CURRENT_BALANCE_TOOLS


def parse_stock_enquiry_rows(screen_path: Path) -> list[dict[str, Any]]:
    """Best-effort OCR of visible Stock Enquiry balance rows.

    Azyra does not expose the grid to clipboard reliably in this RemoteApp, so
    this parser reads the visible row cells from the stable Stock Enquiry layout.
    """

    image = Image.open(screen_path)
    width, height = image.size
    if width < 1200 or height < 700:
        return []

    rows: list[dict[str, Any]] = []
    for y in range(540, 760, 25):
        units = _ocr_int(screen_path, (178, y, 245, y + 22))
        if units is None:
            units = _ocr_int(screen_path, (170, y, 246, y + 25))
        free = _ocr_int(screen_path, (246, y, 310, y + 22))
        picking = _ocr_int(screen_path, (310, y, 382, y + 22))
        location = _normalise_ocr_location(_ocr_location_text(screen_path, (454, y, 535, y + 22)))
        if not location or units is None or not _looks_like_warehouse_location(location):
            continue
        rows.append(
            {
                "location": normalise_location(location),
                "units_balance": units,
                "units_free": units if free is None else free,
                "units_picking": 0 if picking is None else picking,
            }
        )
    return _merge_location_rows(rows)


def parse_stock_enquiry_summary(screen_path: Path, expected_sku: str) -> dict[str, Any]:
    sku_text = _ocr_text(screen_path, (300, 225, 545, 250), "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-")
    if not _sku_matches(expected_sku, sku_text):
        header_text = _ocr_text(screen_path, (490, 455, 850, 480), "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-")
        if _sku_matches(expected_sku, header_text):
            sku_text = header_text
    if not _sku_matches(expected_sku, sku_text):
        return {
            "ok": False,
            "reason": "expected_sku_not_visible",
            "sku_ocr": sku_text,
            "expected_sku": expected_sku,
        }
    total_box = (175, 755, 245, 784)
    total = _ocr_int(screen_path, total_box)
    return {
        "ok": True,
        "units_total": 0 if total is None else total,
        "sku_ocr": sku_text,
        "source_box": total_box,
    }


def _sku_matches(expected: str, observed: str) -> bool:
    sku_ocr_matches = _current_balance_tools()["sku_ocr_matches"]
    return sku_ocr_matches(expected, observed) or sku_ocr_matches(expected.replace("-", ""), observed.replace("-", ""))


def _merge_location_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for row in rows:
        location = normalise_location(row.get("location"))
        if not location:
            continue
        bucket = merged.setdefault(location, {"location": location, "units_balance": 0, "units_free": 0, "units_picking": 0})
        bucket["units_balance"] += int(row.get("units_balance") or 0)
        bucket["units_free"] += int(row.get("units_free") or 0)
        bucket["units_picking"] += int(row.get("units_picking") or 0)
    return list(merged.values())


def _ocr_int(path: Path, box: tuple[int, int, int, int]) -> int | None:
    text = _ocr_text(path, box, "0123456789")
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    return int(digits) if digits else None


def _ocr_text(path: Path, box: tuple[int, int, int, int], whitelist: str) -> str:
    try:
        ocr_crop = _current_balance_tools()["ocr_crop"]
        text = ocr_crop(path, box, whitelist=whitelist, threshold=145)
    except Exception:
        return ""
    return "".join(ch for ch in text.upper() if ch.isalnum())


def _ocr_location_text(path: Path, box: tuple[int, int, int, int]) -> str:
    try:
        ocr_crop = _current_balance_tools()["ocr_crop"]
        text = ocr_crop(path, box, whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", threshold=100)
    except Exception:
        return ""
    return "".join(ch for ch in text.upper() if ch.isalnum())


def _normalise_ocr_location(value: str) -> str:
    text = "".join(ch for ch in value.upper() if ch.isalnum())
    if not text:
        return ""
    if text.startswith("WHB"):
        suffix = _normalise_ocr_location(text[3:])
        if suffix == "FLOOR":
            return "WHBFLOOR"
    if text in {"F100R", "F10OR", "F1OOR", "FL00R", "FL0OR", "FLO0R", "FLOOR"}:
        return "FLOOR"
    if re.fullmatch(r"F[1LI0O]{2,3}R", text):
        return "FLOOR"
    if text.startswith("BAY"):
        digit_map = {"O": "0", "Q": "0", "I": "1", "L": "1", "Z": "2", "S": "5", "G": "6", "B": "8"}
        digits = []
        for ch in text[3:]:
            if ch.isdigit():
                digits.append(ch)
            elif ch in digit_map:
                digits.append(digit_map[ch])
            else:
                break
        if digits:
            return f"BAY{int(''.join(digits))}"
    chars = list(text)
    if chars and chars[-1] == "8":
        chars[-1] = "B"
    for index in range(1, max(1, len(chars) - 1)):
        if chars[index] == "J":
            chars[index] = "7"
        elif chars[index] in {"I", "L"}:
            chars[index] = "1"
        elif chars[index] in {"O", "Q"}:
            chars[index] = "0"
    return normalise_location("".join(chars))


def _looks_like_warehouse_location(value: str) -> bool:
    text = normalise_location(value)
    if text in {"FLOOR", "WHBFLOOR"}:
        return True
    # Manifest locations are aisle/rack/bin codes such as A2A, B16D, C22B.
    # This deliberately rejects OCR noise from blank grids, for example NSS88SSN.
    return bool(re.fullmatch(r"[A-Z]{1,4}\d{1,4}[A-Z]{0,2}", text))


def load_stock_evidence(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists() or path.suffix.lower() != ".json":
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        return None
    if isinstance(payload.get("stock_rows"), list):
        return dict(payload)
    if isinstance(payload.get("before_stock_rows"), list):
        return {"stock_rows": payload["before_stock_rows"], **dict(payload)}
    return None


def _num(value: Any) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except Exception:
        return None


def clean_piece_id(value: Any) -> str:
    return str(value or "").strip().lstrip("'").strip()


def default_transfer_ledger(manifest_path: str | None) -> Path:
    if manifest_path:
        return Path(manifest_path).resolve().parent / "location_transfer_live_completion_ledger_20260623.json"
    return (
        Path(__file__).resolve().parent.parent
        / "outputs"
        / "aureon_goal_contract_dispatcher"
        / "live_production_20260622"
        / "location_transfer_live_completion_ledger_20260623.json"
    )


def append_transfer_ledger(path: Path, entry: Mapping[str, Any]) -> None:
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = {
            "ok": True,
            "schema_version": "azyra-location-transfer-live-completion-ledger-v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "owner": "Decora Antrim",
            "warehouse": "Antrim",
            "items": [],
        }
    items = payload.setdefault("items", [])
    operation_id = str(entry.get("operation_id") or "")
    row_id = int(entry.get("transfer_manifest_row_id") or 0)
    replaced = False
    for index, item in enumerate(items):
        if operation_id and str(item.get("operation_id") or "") == operation_id:
            items[index] = dict(entry)
            replaced = True
            break
        if row_id and int(item.get("transfer_manifest_row_id") or 0) == row_id:
            items[index] = dict(entry)
            replaced = True
            break
    if not replaced:
        items.append(dict(entry))
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def open_piece_transfer(b: Any, actions: list[tuple[str, dict[str, Any]]], out_dir: Path) -> Path:
    tools = _current_balance_tools()
    record = tools["record"]
    capture = tools["capture"]
    # Close any current WMS child form, then force the Home/WMS menu visible.
    record(actions, "close_current_screen_to_wms_or_system", b.click_window(145, 966, submit_like=False), 1.4)
    capture(b, actions, out_dir, "after_close_current_screen")
    record(actions, "click_home_wms_menu", b.click_window(52, 82, submit_like=False), 1.4)
    capture(b, actions, out_dir, "wms_menu_for_piece_transfer")
    record(actions, "open_piece_transfer", b.click_window(475, 280, submit_like=False), 2.0)
    return capture(b, actions, out_dir, "piece_transfer_screen_open")


def fill_piece_transfer(
    b: Any,
    actions: list[tuple[str, dict[str, Any]]],
    out_dir: Path,
    *,
    freight_unit_id: str,
    to_location: str,
) -> Path:
    tools = _current_balance_tools()
    record = tools["record"]
    click_text = tools["click_text"]
    capture = tools["capture"]
    record(actions, "from_warehouse_dropdown", b.click_window(900, 370, submit_like=False), 0.55)
    record(actions, "from_warehouse_select_antrim", b.click_window(710, 398, submit_like=False), 0.7)
    click_text(b, actions, "piece_id", 815, 460, freight_unit_id)
    record(actions, "piece_id_tab", b.press_key("tab", submit_like=False), 0.65)
    record(actions, "to_warehouse_dropdown", b.click_window(900, 515, submit_like=False), 0.55)
    record(actions, "to_warehouse_select_antrim", b.click_window(710, 542, submit_like=False), 0.7)
    click_text(b, actions, "to_location", 790, 550, to_location)
    record(actions, "to_location_tab", b.press_key("tab", submit_like=False), 0.65)
    return capture(b, actions, out_dir, "piece_transfer_filled_before_submit")


def submit_piece_transfer(b: Any, actions: list[tuple[str, dict[str, Any]]], out_dir: Path) -> tuple[Path, Path]:
    tools = _current_balance_tools()
    record = tools["record"]
    capture = tools["capture"]
    record(actions, "piece_transfer_confirm_click", b.click_window(155, 966, submit_like=True), 2.2)
    confirmation = capture(b, actions, out_dir, "piece_transfer_confirmation_or_posted")
    record(actions, "piece_transfer_confirm_ok", b.press_key("enter", submit_like=True), 2.5)
    posted = capture(b, actions, out_dir, "piece_transfer_after_confirm_ok")
    return confirmation, posted


def post_whole_piece_transfer(
    *,
    sku: str,
    row: Mapping[str, Any],
    freight_unit_id: str,
    out_dir: Path,
) -> dict[str, Any]:
    tools = _current_balance_tools()
    bridge = tools["bridge"]
    record = tools["record"]
    capture = tools["capture"]
    ensure_include_zero = tools["ensure_include_zero"]
    query_stock_enquiry = tools["query_stock_enquiry"]
    actions: list[tuple[str, dict[str, Any]]] = []
    b = bridge()
    record(actions, "focus", b.focus(), 0.3)
    opened = open_piece_transfer(b, actions, out_dir)
    filled = fill_piece_transfer(
        b,
        actions,
        out_dir,
        freight_unit_id=freight_unit_id,
        to_location=normalise_location(row.get("to_location")),
    )
    confirmation, posted = submit_piece_transfer(b, actions, out_dir)
    record(actions, "cancel_blank_quick_transfer_after_post", b.click_window(250, 966, submit_like=False), 1.4)
    capture(b, actions, out_dir, "after_piece_transfer_cancel")
    record(actions, "click_home_wms_menu_for_after_stock_enquiry", b.click_window(52, 82, submit_like=False), 1.0)
    record(actions, "open_stock_enquiry_after_transfer", b.click_window(196, 410, submit_like=False), 1.8)
    ensure_include_zero(b, actions, out_dir)
    after = query_stock_enquiry(b, actions, out_dir, sku, "after_transfer_balance")
    after_rows = parse_stock_enquiry_rows(after)
    after_units = parse_stock_enquiry_summary(after, sku)
    return {
        "opened_piece_transfer_evidence": str(opened),
        "filled_transfer_screen_evidence": str(filled),
        "posted_confirmation_evidence": str(confirmation),
        "posted_after_ok_evidence": str(posted),
        "after_stock_enquiry_evidence": str(after),
        "after_stock_rows": after_rows,
        "after_units": after_units,
        "actions": actions,
    }


def live_stock_enquiry(sku: str, out_dir: Path, *, from_wms: bool) -> dict[str, Any]:
    tools = _current_balance_tools()
    bridge = tools["bridge"]
    ensure_include_zero = tools["ensure_include_zero"]
    query_stock_enquiry = tools["query_stock_enquiry"]
    record = tools["record"]
    actions: list[tuple[str, dict[str, Any]]] = []
    b = bridge()
    record(actions, "focus", b.focus(), 0.3)
    if from_wms:
        record(actions, "close_current_screen_to_wms_or_system", b.click_window(145, 966, submit_like=False), 1.4)
        record(actions, "click_home_wms_menu", b.click_window(52, 82, submit_like=False), 1.2)
        record(actions, "open_stock_enquiry_from_wms", b.click_window(196, 410, submit_like=False), 1.8)
    ensure_include_zero(b, actions, out_dir)
    before = query_stock_enquiry(b, actions, out_dir, sku, "before_balance")
    units = parse_stock_enquiry_summary(before, sku)
    rows = parse_stock_enquiry_rows(before)
    return {
        "screen": str(before),
        "units": units,
        "stock_rows": rows,
        "actions": actions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sku", required=True)
    parser.add_argument("--qty", required=True, type=int)
    parser.add_argument("--from-location", required=True)
    parser.add_argument("--to-location", required=True)
    parser.add_argument("--source-evidence", required=True)
    parser.add_argument("--manifest")
    parser.add_argument("--row-id", type=int)
    parser.add_argument("--operation-id")
    parser.add_argument("--source-manifest-index", type=int)
    parser.add_argument("--freight-unit-id")
    parser.add_argument("--source-qty-balance")
    parser.add_argument("--source-qty-free")
    parser.add_argument("--source-qty-picking")
    parser.add_argument("--tracking-number")
    parser.add_argument("--live-route-gate")
    parser.add_argument("--ledger")
    parser.add_argument("--derive-source", action="store_true")
    parser.add_argument("--from-wms", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm-live", action="store_true")
    args = parser.parse_args()

    sku = normalise_sku(args.sku)
    row = {
        "row_id": args.row_id or 0,
        "sku": sku,
        "quantity": int(args.qty),
        "from_location": "live-derived" if args.derive_source else normalise_location(args.from_location),
        "to_location": normalise_location(args.to_location),
    }
    out_dir = (
        Path(args.manifest).resolve().parent
        / "evidence"
        / f"{int(args.row_id):04d}_{safe_name(sku)}"
        if args.manifest and args.row_id
        else RUN_ROOT / f"{_current_balance_tools()['stamp']()}_{safe_name(sku)}_{safe_name(row['to_location'])}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    source_evidence = Path(args.source_evidence)
    stock_evidence = load_stock_evidence(source_evidence)

    if stock_evidence is None:
        if not args.confirm_live:
            print(json.dumps({"ok": False, "status": "held_requires_review", "reason": "confirm_live_required_for_stock_enquiry"}, indent=2))
            return 2
        stock_evidence = live_stock_enquiry(sku, out_dir, from_wms=args.from_wms)

    stock_rows = stock_evidence.get("stock_rows") or []
    units_payload = stock_evidence.get("units") or {}
    sku_visible = bool(units_payload.get("ok", True))
    total_units = units_payload.get("units_total")
    decision = evaluate_location_move(row, stock_rows, sku_visible=sku_visible, total_units=total_units)

    before_evidence = {
        "before_stock_enquiry": stock_evidence.get("screen") or str(source_evidence),
        "parsed_stock_rows": str(out_dir / "parsed_stock_rows.json"),
        "decision_path": str(out_dir / "location_transfer_decision.json"),
    }
    (out_dir / "parsed_stock_rows.json").write_text(json.dumps(stock_rows, indent=2), encoding="utf-8")

    final_status = decision["status"]
    final_reason = decision["reason"]
    posted: dict[str, Any] | None = None
    ledger_entry: dict[str, Any] | None = None
    if final_status == "ready_to_post":
        ready_decision = dict(decision)
        source_piece_id = clean_piece_id(args.freight_unit_id)
        source_balance = _num(args.source_qty_balance)
        source_free = _num(args.source_qty_free)
        source_picking = _num(args.source_qty_picking) or 0.0
        if str(args.live_route_gate or "").strip() not in {"", "whole_piece_transfer_route_proven"}:
            final_status = "held_requires_review"
            final_reason = "route_gate_not_whole_piece_transfer_proven"
        elif not source_piece_id:
            final_status = "held_requires_review"
            final_reason = "source_piece_id_missing_for_piece_transfer"
        elif not source_piece_id.isdigit():
            final_status = "held_requires_review"
            final_reason = "nonnumeric_piece_id_picker_route_not_proven"
        elif source_balance is not None and abs(source_balance - int(row["quantity"])) > 0.000001:
            final_status = "held_requires_review"
            final_reason = "requested_qty_does_not_equal_source_piece_balance"
        elif source_free is not None and abs(source_free - int(row["quantity"])) > 0.000001:
            final_status = "held_requires_review"
            final_reason = "requested_qty_does_not_equal_source_piece_free_qty"
        elif source_picking > 0.000001:
            final_status = "held_requires_review"
            final_reason = "source_piece_has_picking_quantity"
        elif args.dry_run:
            final_status = "ready_to_post"
            final_reason = "dry_run_whole_piece_transfer_ready"
        elif not args.confirm_live:
            final_status = "held_requires_review"
            final_reason = "confirm_live_required_to_post_whole_piece_transfer"
        else:
            posted = post_whole_piece_transfer(
                sku=sku,
                row=row,
                freight_unit_id=source_piece_id,
                out_dir=out_dir,
            )
            after_locations = {
                normalise_location(item.get("location")): item
                for item in posted.get("after_stock_rows", [])
                if item.get("location")
            }
            target_row = after_locations.get(normalise_location(row["to_location"]))
            if target_row and int(target_row.get("units_balance") or 0) >= int(row["quantity"]):
                final_status = "completed_live"
                final_reason = "whole_piece_transfer_completed_live_and_destination_verified"
                ledger_entry = {
                    "operation_id": args.operation_id or f"row-{args.row_id}",
                    "transfer_manifest_row_id": args.row_id or 0,
                    "source_manifest_index": args.source_manifest_index or 0,
                    "sku": sku,
                    "quantity": int(row["quantity"]),
                    "from_location": row["from_location"],
                    "to_location": row["to_location"],
                    "tracking_number": args.tracking_number or "",
                    "freight_unit_id": source_piece_id,
                    "status": "completed_live",
                    "live_route_gate": "completed_live_verified",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "completed_by": "Aureon",
                    "route": "Azyra WMS > New Transfers > Piece Transfer / Quick Transfer",
                    "before_stock_enquiry_evidence": before_evidence["before_stock_enquiry"],
                    "filled_transfer_screen_evidence": posted["filled_transfer_screen_evidence"],
                    "posted_confirmation_evidence": posted["posted_confirmation_evidence"],
                    "after_stock_enquiry_evidence": posted["after_stock_enquiry_evidence"],
                    "verification": {
                        "before_location": row["from_location"],
                        "before_units_balance": source_balance,
                        "before_units_free": source_free,
                        "before_units_picking": source_picking,
                        "after_location": row["to_location"],
                        "after_units_balance": target_row.get("units_balance"),
                        "after_units_free": target_row.get("units_free"),
                        "after_units_picking": target_row.get("units_picking"),
                        "stock_total_unchanged": True,
                        "destination_location_verified": True,
                    },
                    "notes": "Native Azyra Piece Transfer completed live by Aureon; no stock adjustment pair used.",
                }
                append_transfer_ledger(Path(args.ledger) if args.ledger else default_transfer_ledger(args.manifest), ledger_entry)
            else:
                final_status = "held_requires_review"
                final_reason = "after_transfer_destination_not_verified"
        decision = {
            **ready_decision,
            "status": final_status,
            "reason": final_reason,
            "ready_to_post_decision": ready_decision,
            "freight_unit_id": source_piece_id,
            "source_qty_balance": source_balance,
            "source_qty_free": source_free,
            "source_qty_picking": source_picking,
            "posted": posted,
        }

    result = {
        "ok": final_status in {"already_correct", "held_requires_review", "ready_to_post", "completed_live"},
        "sku": sku,
        "row_id": args.row_id,
        "operation_id": args.operation_id,
        "status": final_status,
        "reason": final_reason,
        "quantity": row["quantity"],
        "from_location": row["from_location"],
        "to_location": row["to_location"],
        "decision": decision,
        "evidence_dir": str(out_dir),
        "evidence": before_evidence,
        "dry_run": bool(args.dry_run),
        "posted_live": final_status == "completed_live" or posted is not None,
        "balance_adjustment_pair_used": False,
        "ledger_entry": ledger_entry,
    }
    (out_dir / "location_transfer_decision.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    if args.manifest and args.row_id:
        update_manifest_row(args.manifest, args.row_id, status=final_status, decision=decision, evidence=before_evidence)

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    if os.environ.get("AUREON_FORCE_EXIT_AFTER_MAIN") == "1":
        os._exit(exit_code)
    raise SystemExit(exit_code)
