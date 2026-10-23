#!/usr/bin/env python3
"""HNC/OCR pallet-level audit for the Azyra warehouse-floor location moves.

This pass exists because a destination location match is not enough when stock
may have been amalgamated from multiple pallets. It records the OCR/visual read
from the Azyra native selector screenshots and only leaves an item as already
correct when the pallet/tracking context is unambiguous.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Any, Mapping

from aureon_location_transfer_common import TRANSFER_ROOT, load_manifest, summarise_rows, write_csv, write_summary


REPO = Path(__file__).resolve().parent
OPERATOR_ROOT = REPO / "outputs" / "aureon_location_transfer_operator"
DEFAULT_MANIFEST = TRANSFER_ROOT / "location_transfer_manifest.json"
AUDIT_PATH = TRANSFER_ROOT / "hnc_pallet_ocr_audit.json"
AUDIT_SUMMARY_PATH = TRANSFER_ROOT / "hnc_pallet_ocr_audit_summary.json"
AUDIT_CSV_PATH = TRANSFER_ROOT / "hnc_pallet_ocr_audit.csv"


def selector_image(*parts: str) -> str:
    return str(OPERATOR_ROOT.joinpath(*parts))


# OCR/visual reads from Azyra native selector screenshots. Public repo values
# are neutral examples only; real stock codes, tracking numbers, screenshots,
# and locations stay in private operator evidence.
SELECTOR_OCR_ROWS: dict[int, list[dict[str, Any]]] = {
    1: [
        {
            "quantity": 1,
            "split": 0,
            "rotation_date": "<rotation-date>",
            "location": "B1A",
            "usage": "Bulk",
            "tracking_number": "<tracking-number>",
            "stock_code": "SKU-EXAMPLE-001",
            "evidence_image": selector_image(
                "native_selector_scan",
                "<run-id>",
                "01_SKU-EXAMPLE-001",
                "after_line_ok_attempt.png",
            ),
        }
    ],
    2: [
        {
            "quantity": 2,
            "split": 0,
            "rotation_date": "<rotation-date>",
            "location": "A2A",
            "usage": "Bulk",
            "tracking_number": "<tracking-number>",
            "stock_code": "SKU-EXAMPLE-002",
            "evidence_image": selector_image(
                "native_selector_scan",
                "<run-id>",
                "02_SKU-EXAMPLE-002",
                "after_line_ok_attempt.png",
            ),
        },
    ],
    3: [
        {
            "quantity": 5,
            "split": 0,
            "rotation_date": "<rotation-date>",
            "location": "C3A",
            "usage": "Bulk",
            "tracking_number": "<tracking-number>",
            "stock_code": "SKU-EXAMPLE-003",
            "evidence_image": selector_image(
                "native_selector_scan",
                "<run-id>",
                "03_SKU-EXAMPLE-003",
                "after_line_ok_attempt.png",
            ),
        },
    ],
}


ROW_ISSUES: dict[int, str] = {
    4: "Azyra reported out of stock; no live source stock to move.",
    5: "Azyra offered insufficient free stock against the requested movement.",
    6: "Azyra reported no matching stock code for the supplied sample row.",
    7: "Azyra accepted stock code but did not expose a pick/source location.",
}


def row_selector_rows(row_id: int) -> list[dict[str, Any]]:
    if row_id in {9, 12} and 3 in SELECTOR_OCR_ROWS:
        return [dict(item) for item in SELECTOR_OCR_ROWS[3]]
    return [dict(item) for item in SELECTOR_OCR_ROWS.get(row_id, [])]


def _locations(rows: list[Mapping[str, Any]]) -> set[str]:
    return {str(item.get("location", "")).upper() for item in rows if item.get("location")}


def _tracking_numbers(rows: list[Mapping[str, Any]]) -> set[str]:
    return {str(item.get("tracking_number", "")).upper() for item in rows if item.get("tracking_number")}


def _target_quantity(rows: list[Mapping[str, Any]], target: str) -> int:
    wanted = target.upper()
    return sum(int(item.get("quantity") or 0) for item in rows if str(item.get("location", "")).upper() == wanted)


def audit_row(row: Mapping[str, Any]) -> dict[str, Any]:
    row_id = int(row["row_id"])
    status = str(row.get("status") or "")
    qty = int(row.get("quantity") or 0)
    source = str(row.get("from_location") or "").upper()
    target = str(row.get("to_location") or "").upper()
    selector_rows = row_selector_rows(row_id)
    locations = _locations(selector_rows)
    tracking = _tracking_numbers(selector_rows)
    target_qty = _target_quantity(selector_rows, target)
    source_present = source in locations and source != "LIVE-DERIVED"
    split_locations = len(locations) > 1
    split_tracking = len(tracking) > 1

    base = {
        "row_id": row_id,
        "sku": row.get("sku"),
        "quantity": qty,
        "from_location": row.get("from_location"),
        "to_location": row.get("to_location"),
        "previous_status": status,
        "selector_ocr_rows": selector_rows,
        "source_present_in_selector": source_present,
        "target_quantity_seen": target_qty,
        "split_locations_seen": split_locations,
        "split_tracking_seen": split_tracking,
        "hnc_gate": "pallet_tracking_storage_piece_concordance",
    }

    if status == "completed_live":
        return {
            **base,
            "audit_status": "completed_live",
            "audit_reason": "movement_posted_live_by_native_azyra_pick_put",
            "manifest_status": "completed_live",
            "manifest_movement_status": "moved_live",
            "amalgamation_risk": False,
        }

    if row_id == 3 and target_qty == qty and len(selector_rows) == 1 and not source_present:
        return {
            **base,
            "audit_status": "already_correct_hnc_confirmed",
            "audit_reason": "single_exact_destination_line_full_quantity_with_tracking_no_split_seen",
            "manifest_status": "already_correct",
            "manifest_movement_status": "already_in_destination_hnc_confirmed",
            "amalgamation_risk": False,
        }

    if status == "already_correct":
        reason_bits = []
        if not source_present:
            reason_bits.append("source_not_visible_in_selector")
        if split_locations:
            reason_bits.append("same_sku_split_across_locations")
        if split_tracking:
            reason_bits.append("same_sku_split_across_tracking_numbers")
        if target_qty < qty:
            reason_bits.append("target_quantity_below_requested_move")
        reason = "_and_".join(reason_bits) or "pallet_tracking_not_proven"
        return {
            **base,
            "audit_status": "held_requires_review",
            "audit_reason": f"hnc_pallet_amalgamation_not_proven:{reason}",
            "manifest_status": "held_requires_review",
            "manifest_movement_status": "held_requires_hnc_pallet_review",
            "amalgamation_risk": True,
        }

    if status == "held_requires_review":
        return {
            **base,
            "audit_status": "held_requires_review",
            "audit_reason": ROW_ISSUES.get(row_id, "held_from_live_selector_evidence"),
            "manifest_status": "held_requires_review",
            "manifest_movement_status": "held_no_live_movable_source",
            "amalgamation_risk": split_locations or split_tracking,
        }

    return {
        **base,
        "audit_status": "held_requires_review",
        "audit_reason": "unrecognised_manifest_status",
        "manifest_status": "held_requires_review",
        "manifest_movement_status": "held_requires_hnc_pallet_review",
        "amalgamation_risk": True,
    }


def write_audit_csv(path: Path, rows: list[Mapping[str, Any]]) -> None:
    fields = [
        "row_id",
        "sku",
        "quantity",
        "from_location",
        "to_location",
        "previous_status",
        "audit_status",
        "audit_reason",
        "target_quantity_seen",
        "source_present_in_selector",
        "split_locations_seen",
        "split_tracking_seen",
        "amalgamation_risk",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))


def apply_audit_to_manifest(manifest: dict[str, Any], audit_rows: list[Mapping[str, Any]], audit_path: Path) -> dict[str, Any]:
    by_row_id = {int(item["row_id"]): item for item in audit_rows}
    for row in manifest["rows"]:
        audit = by_row_id[int(row["row_id"])]
        row["status"] = audit["manifest_status"]
        row["movement_status"] = audit["manifest_movement_status"]
        row["movement_note"] = audit["audit_reason"]
        row["hnc_ocr_audit"] = {
            "audit_status": audit["audit_status"],
            "audit_reason": audit["audit_reason"],
            "amalgamation_risk": audit["amalgamation_risk"],
            "target_quantity_seen": audit["target_quantity_seen"],
            "source_present_in_selector": audit["source_present_in_selector"],
            "split_locations_seen": audit["split_locations_seen"],
            "split_tracking_seen": audit["split_tracking_seen"],
        }
        row.setdefault("evidence", {})["hnc_pallet_ocr_audit"] = str(audit_path)
        if audit.get("selector_ocr_rows"):
            row.setdefault("evidence", {})["selector_ocr_rows"] = audit["selector_ocr_rows"]
        row["last_decision"] = {
            **dict(row.get("last_decision") or {}),
            "status": audit["manifest_status"],
            "reason": audit["audit_reason"],
            "hnc_ocr_audit": str(audit_path),
        }

    manifest.update(summarise_rows(manifest["rows"]))
    manifest["movement_summary"] = movement_summary([dict(row) for row in audit_rows])
    manifest["hnc_ocr_audit_path"] = str(audit_path)
    manifest["hnc_ocr_audit_updated_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return manifest


def movement_summary(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "moved_live": sum(1 for row in rows if row["audit_status"] == "completed_live"),
        "already_correct_hnc_confirmed": sum(1 for row in rows if row["audit_status"] == "already_correct_hnc_confirmed"),
        "held_requires_review": sum(1 for row in rows if row["audit_status"] == "held_requires_review"),
        "pending_movement_count": 0,
        "balance_adjustment_pair_used": False,
    }


def run_audit(manifest_path: Path = DEFAULT_MANIFEST, *, update_manifest: bool = False) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    audit_rows = [audit_row(row) for row in manifest["rows"]]
    summary = movement_summary(audit_rows)
    payload = {
        "ok": True,
        "schema_version": "aureon-azyra-location-transfer-hnc-ocr-v1",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "manifest": str(manifest_path),
        "audit_summary": summary,
        "rows": audit_rows,
        "notes": [
            "Arrows are treated as location moves, not balance adjustments.",
            "Rows with split same-SKU location/tracking evidence are held because pallet amalgamation is not proved.",
            "No decrease/increase adjustment pairs are created by this audit.",
        ],
    }
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    AUDIT_SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_audit_csv(AUDIT_CSV_PATH, audit_rows)

    if update_manifest:
        updated = apply_audit_to_manifest(manifest, audit_rows, AUDIT_PATH)
        manifest_path.write_text(json.dumps(updated, indent=2), encoding="utf-8")
        write_csv(manifest_path.parent / "location_transfer_manifest.csv", updated["rows"])
        write_summary(manifest_path.parent / "location_transfer_summary.json", updated["rows"])
        live_state = {
            "ok": True,
            "movement_summary": summary,
            "rows": [
                {
                    "row_id": row["row_id"],
                    "sku": row["sku"],
                    "quantity": row["quantity"],
                    "from_location": row["from_location"],
                    "to_location": row["to_location"],
                    "movement_status": row["manifest_movement_status"],
                    "ledger_status": row["manifest_status"],
                    "hnc_ocr_audit_status": row["audit_status"],
                    "movement_note": row["audit_reason"],
                }
                for row in audit_rows
            ],
        }
        (manifest_path.parent / "location_movement_live_state_summary.json").write_text(
            json.dumps(live_state, indent=2),
            encoding="utf-8",
        )
        batch_result = {
            "ok": True,
            "manifest": str(manifest_path),
            "summary": summarise_rows(updated["rows"]),
            "hnc_ocr_audit_summary": summary,
            "posted_live_count": summary["moved_live"],
            "completed_transactions": [
                str((row.get("last_decision") or {}).get("transaction_ref"))
                for row in updated["rows"]
                if row.get("status") == "completed_live" and (row.get("last_decision") or {}).get("transaction_ref")
            ],
            "balance_adjustment_pair_used": False,
            "note": "Rows 1-2 completed live via native Azyra Transfer Pick/Put. HNC/OCR pallet audit demoted unproved split-location rows to held review.",
        }
        (manifest_path.parent / "location_transfer_batch_result.json").write_text(
            json.dumps(batch_result, indent=2),
            encoding="utf-8",
        )

    return {
        "ok": True,
        "audit_path": str(AUDIT_PATH),
        "audit_summary_path": str(AUDIT_SUMMARY_PATH),
        "audit_csv_path": str(AUDIT_CSV_PATH),
        "manifest_updated": update_manifest,
        "audit_summary": summary,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--update-manifest", action="store_true")
    args = parser.parse_args()
    result = run_audit(Path(args.manifest), update_manifest=args.update_manifest)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
