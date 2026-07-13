"""Shared helpers for the Azyra warehouse-floor location transfer batch."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Mapping, Sequence


REPO = Path(__file__).resolve().parent
WORKSPACE = REPO.parent
TRANSFER_ROOT = WORKSPACE / "outputs" / "aureon_goal_contract_dispatcher" / "azyra_location_moves_20260618"
PHOTO_PATH = (
    WORKSPACE
    / ".codex-remote-attachments"
    / "019eca7c-3ef8-7493-8dec-e69133ea7ac2"
    / "dd846be6-8a11-41b9-a719-5aadaaeb1b0f"
    / "1-Photo-1.jpg"
)


@dataclass(frozen=True)
class LocationMoveRow:
    row_id: int
    sku: str
    quantity: int
    from_location: str
    to_location: str
    confidence: str
    raw_note: str


PHOTO_ROWS: tuple[LocationMoveRow, ...] = (
    LocationMoveRow(1, "SKU-EXAMPLE-001", 1, "A1A", "B1A", "high", "SKU-EXAMPLE-001 x1 > A1A > B1A"),
    LocationMoveRow(2, "SKU-EXAMPLE-002", 2, "live-derived", "B2A", "medium", "SKU-EXAMPLE-002 x2 > B2A"),
    LocationMoveRow(3, "SKU-EXAMPLE-003", 5, "A3A", "C3A", "low", "SKU-EXAMPLE-003 x5 > A3A > C3A"),
)


def stamp() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value).strip("_") or "item"


def normalise_location(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text in {"LIVE-DERIVED", "LIVE_DERIVED", "LIVE DERIVED"}:
        return "live-derived"
    compact = text.replace(" ", "")
    if compact in {"WHBF100R", "WHBF10OR", "WHBF1OOR", "WHBFL00R", "WHBFL0OR", "WHBFLO0R"}:
        return "WHBFLOOR"
    return compact


def normalise_sku(value: Any) -> str:
    return str(value or "").strip().upper().replace(" ", "")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in PHOTO_ROWS:
        item = asdict(row)
        item.update(
            {
                "sku": normalise_sku(row.sku),
                "from_location": normalise_location(row.from_location),
                "to_location": normalise_location(row.to_location),
                "status": "pending",
                "action_type": "putaway_stock",
                "reason": "Physical warehouse floor location move from handwritten note",
                "source_image": str(PHOTO_PATH),
                "source_image_exists": PHOTO_PATH.exists(),
                "source_image_sha256": sha256(PHOTO_PATH) if PHOTO_PATH.exists() else "",
                "requires_live_stock_enquiry": True,
                "native_transfer_required": True,
                "do_not_use_balance_adjustment_pair": True,
            }
        )
        rows.append(item)
    return rows


def write_manifest(output_dir: Path = TRANSFER_ROOT) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir = output_dir / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    rows = build_manifest_rows()
    manifest = {
        "schema_version": "aureon-azyra-location-transfer-v1",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "owner": os.getenv("AUREON_AZYRA_OWNER_TEXT", "<owner-not-committed>"),
        "warehouse": os.getenv("AUREON_AZYRA_WAREHOUSE_TEXT", "<warehouse-not-committed>"),
        "source_image": str(PHOTO_PATH),
        "item_count": len(rows),
        "pending_count": len(rows),
        "completed_count": 0,
        "already_correct_count": 0,
        "held_count": 0,
        "rows": rows,
    }
    manifest_path = output_dir / "location_transfer_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    write_csv(output_dir / "location_transfer_manifest.csv", rows)
    write_summary(output_dir / "location_transfer_summary.json", rows)
    return {
        "ok": True,
        "manifest_path": str(manifest_path),
        "csv_path": str(output_dir / "location_transfer_manifest.csv"),
        "summary_path": str(output_dir / "location_transfer_summary.json"),
        "item_count": len(rows),
    }


def load_manifest(path: str | Path) -> dict[str, Any]:
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("location transfer manifest must be a JSON object")
    rows = manifest.get("rows")
    if not isinstance(rows, list):
        raise ValueError("location transfer manifest must contain rows")
    return manifest


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    fields = [
        "row_id",
        "sku",
        "quantity",
        "from_location",
        "to_location",
        "confidence",
        "status",
        "reason",
        "raw_note",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))


def write_summary(path: Path, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    summary = summarise_rows(rows)
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def summarise_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    statuses = [str(row.get("status") or "pending") for row in rows]
    return {
        "item_count": len(statuses),
        "completed_count": statuses.count("completed_live"),
        "already_correct_count": statuses.count("already_correct"),
        "held_count": statuses.count("held_requires_review"),
        "pending_count": statuses.count("pending") + statuses.count("ready_to_post"),
    }


def evidence_dir_for(row: Mapping[str, Any], root: Path = TRANSFER_ROOT) -> Path:
    return root / "evidence" / f"{int(row['row_id']):02d}_{safe_name(str(row['sku']))}"


def update_manifest_row(
    manifest_path: str | Path,
    row_id: int,
    *,
    status: str,
    decision: Mapping[str, Any],
    evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    path = Path(manifest_path)
    manifest = load_manifest(path)
    rows = manifest["rows"]
    for row in rows:
        if int(row.get("row_id", 0)) == int(row_id):
            row["status"] = status
            row["last_decision"] = dict(decision)
            if evidence:
                row.setdefault("evidence", {}).update(dict(evidence))
            break
    else:
        raise ValueError(f"row_id {row_id} not found in manifest")
    summary = summarise_rows(rows)
    manifest.update(summary)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    write_csv(path.parent / "location_transfer_manifest.csv", rows)
    write_summary(path.parent / "location_transfer_summary.json", rows)
    return manifest


def stock_row(
    location: str,
    *,
    balance: int,
    free: int | None = None,
    picking: int = 0,
    storage_pieces: int | None = None,
) -> dict[str, Any]:
    return {
        "location": normalise_location(location),
        "units_balance": int(balance),
        "units_free": int(balance if free is None else free),
        "units_picking": int(picking),
        "storage_pieces_balance": storage_pieces,
    }


def evaluate_location_move(
    row: Mapping[str, Any],
    stock_rows: Sequence[Mapping[str, Any]],
    *,
    sku_visible: bool = True,
    total_units: int | None = None,
) -> dict[str, Any]:
    sku = normalise_sku(row.get("sku"))
    qty = int(row.get("quantity") or 0)
    source = normalise_location(row.get("from_location"))
    target = normalise_location(row.get("to_location"))
    rows = [_normalise_stock_row(item) for item in stock_rows]

    if not sku_visible:
        return _decision("held_requires_review", "sku_not_visible", sku, qty, source, target, rows)
    if qty <= 0:
        return _decision("held_requires_review", "invalid_quantity", sku, qty, source, target, rows)
    if total_units is not None and int(total_units) < qty:
        return _decision("held_requires_review", "total_units_less_than_move_quantity", sku, qty, source, target, rows)

    target_row = _first_location(rows, target)
    if source == target:
        return _decision("already_correct", "source_equals_destination", sku, qty, source, target, rows, selected_source=target_row)

    if source == "live-derived":
        candidates = [item for item in rows if item["location"] != target and item["units_free"] >= qty and item["units_picking"] == 0]
        if len(candidates) == 1:
            return _decision("ready_to_post", "single_live_source_with_enough_free_stock", sku, qty, candidates[0]["location"], target, rows, selected_source=candidates[0])
        if len(candidates) > 1:
            return _decision("held_requires_review", "multiple_possible_live_sources", sku, qty, source, target, rows, candidate_sources=candidates)
        if target_row and target_row["units_balance"] >= qty:
            return _decision("already_correct", "destination_already_has_required_quantity", sku, qty, source, target, rows, selected_source=target_row)
        return _decision("held_requires_review", "no_live_source_with_enough_free_stock", sku, qty, source, target, rows)

    source_row = _first_location(rows, source)
    if source_row is None:
        if target_row and target_row["units_balance"] >= qty:
            return _decision("already_correct", "destination_already_has_required_quantity", sku, qty, source, target, rows, selected_source=target_row)
        return _decision("held_requires_review", "source_location_not_found", sku, qty, source, target, rows)
    if source_row["units_picking"] > 0:
        return _decision("held_requires_review", "source_has_picking_quantity", sku, qty, source, target, rows, selected_source=source_row)
    if source_row["units_free"] < qty:
        if target_row and target_row["units_balance"] >= qty:
            return _decision("already_correct", "destination_already_has_required_quantity", sku, qty, source, target, rows, selected_source=target_row)
        return _decision("held_requires_review", "source_free_quantity_short", sku, qty, source, target, rows, selected_source=source_row)
    return _decision("ready_to_post", "source_has_enough_free_stock", sku, qty, source, target, rows, selected_source=source_row)


def _normalise_stock_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return stock_row(
        row.get("location", ""),
        balance=int(row.get("units_balance") or row.get("balance") or 0),
        free=int(row.get("units_free") if row.get("units_free") is not None else row.get("free") or row.get("units_balance") or 0),
        picking=int(row.get("units_picking") or row.get("picking") or 0),
        storage_pieces=row.get("storage_pieces_balance"),
    )


def _first_location(rows: Sequence[Mapping[str, Any]], location: str) -> dict[str, Any] | None:
    wanted = normalise_location(location)
    for row in rows:
        if normalise_location(row.get("location")) == wanted:
            return dict(row)
    return None


def _decision(
    status: str,
    reason: str,
    sku: str,
    qty: int,
    source: str,
    target: str,
    rows: Sequence[Mapping[str, Any]],
    **extra: Any,
) -> dict[str, Any]:
    return {
        "status": status,
        "reason": reason,
        "sku": sku,
        "quantity": qty,
        "from_location": source,
        "to_location": target,
        "stock_rows": [dict(item) for item in rows],
        **extra,
    }
