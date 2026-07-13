#!/usr/bin/env python3
"""Build source evidence cards for current-balance corrections."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent
WORKSPACE = REPO.parent
FIX_DIR = WORKSPACE / "outputs" / "aureon_goal_contract_dispatcher" / "azyra_current_balance_fix"
RUNNER_MANIFEST = FIX_DIR / "aureon_current_balance_runner_manifest.json"
PDF_EXTRACTION = Path(
    os.getenv(
        "AUREON_LEGACY_BALANCE_PDF_EXTRACTION",
        str(WORKSPACE / "legacy_source_outputs" / "current_balances_from_pdf.json"),
    )
)
EVIDENCE_ROOT = FIX_DIR / "evidence"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("_") or "unknown"


def find_item(manifest: dict, sku: str) -> dict:
    wanted = sku.strip().upper()
    for item in manifest.get("items", []):
        if str(item.get("sku", "")).strip().upper() == wanted:
            return item
    raise SystemExit(f"[ERROR] SKU not found in runner manifest: {sku}")


def evidence_dir(item: dict) -> Path:
    return EVIDENCE_ROOT / f"{int(item.get('manifest_index', 0)):03d}_{slug(str(item.get('sku', '')))}"


def stock_rows(pdf_data: dict, sku: str) -> list[dict]:
    wanted = sku.strip().upper()
    rows = []
    for row in pdf_data.get("rows", []):
        stock_code = str(row.get("stock_code") or row.get("Stock Code") or row.get("sku") or "").strip().upper()
        if stock_code == wanted:
            rows.append(row)
    return rows


def draw_card(path: Path, lines: list[str]) -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception as exc:
        raise SystemExit(f"[ERROR] Pillow is required to render evidence card: {exc}") from exc

    image = Image.new("RGB", (1600, 1000), "white")
    draw = ImageDraw.Draw(image)
    try:
        title_font = ImageFont.truetype("arial.ttf", 34)
        body_font = ImageFont.truetype("arial.ttf", 23)
        small_font = ImageFont.truetype("arial.ttf", 19)
    except Exception:
        title_font = body_font = small_font = ImageFont.load_default()

    y = 44
    draw.text((56, y), lines[0], fill=(30, 44, 70), font=title_font)
    y += 64
    for line in lines[1:]:
        font = small_font if line.startswith("Note:") or line.startswith("Source ") else body_font
        fill = (45, 45, 45)
        if line.startswith("Movement clearance:"):
            fill = (145, 70, 20)
        draw.text((56, y), line[:145], fill=fill, font=font)
        y += 36
    image.save(path)


def build_evidence(item: dict, pdf_data: dict, out_dir: Path) -> tuple[Path, Path, dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = stock_rows(pdf_data, str(item.get("sku", "")))
    summary = pdf_data.get("summary", {})
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    png_path = out_dir / f"before-balance-source-pdf_{stamp}.png"
    json_path = out_dir / f"before-balance-source-pdf_{stamp}.json"
    evidence = {
        "schema_version": "azyra-current-balance-source-evidence-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sku": item.get("sku"),
        "description": item.get("description"),
        "target_location": item.get("target_location"),
        "quantity_delta": item.get("quantity"),
        "unit_conversion_summary": item.get("unit_conversion_summary"),
        "current_balance_summary": item.get("current_balance_summary"),
        "pdf_path": summary.get("pdf_path"),
        "pdf_name": summary.get("pdf_name"),
        "pdf_as_at": summary.get("as_at"),
        "pdf_pages": summary.get("pdf_pages"),
        "parsed_rows": summary.get("parsed_rows"),
        "matching_pdf_rows": len(rows),
        "matching_pdf_row_sample": rows[:5],
        "movement_clearance": "not_cleared_by_this_artifact",
    }
    lines = [
        f"{item.get('sku')} Before-Balance Evidence",
        f"Description: {item.get('description')}",
        f"Current balance PDF as-at: {summary.get('as_at')} ({summary.get('pdf_name')})",
        f"Matching {item.get('sku')} rows in parsed legacy balance PDF: {len(rows)}",
        f"Runner current balance summary: {item.get('current_balance_summary')}",
        f"Legacy-source conversion: {item.get('unit_conversion_summary')}",
        f"Planned correction: +{item.get('quantity')} units at {item.get('target_location')}",
        f"Source PDF parsed rows/pages: {summary.get('parsed_rows')} rows / {summary.get('pdf_pages')} pages",
        "Movement clearance: NOT cleared by this artifact; check picks, dispatches, or movements separately.",
        f"Source PDF: {summary.get('pdf_path')}",
    ]
    draw_card(png_path, lines)
    save_json(json_path, evidence)
    return png_path, json_path, evidence


def attach_before_balance(item: dict, evidence_dir_path: Path, png_path: Path, evidence: dict) -> Path:
    state_path = evidence_dir_path / "line_evidence.json"
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
    capture = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "path": str(png_path.resolve()),
        "ok": True,
        "reason": "source_pdf_current_balance_evidence",
        "window_found": False,
        "description": "Current legacy-source balance evidence from parsed warehouse balances PDF.",
        "operator_observation": (
            f"{item.get('sku')} has {evidence.get('matching_pdf_rows')} matching row(s) in the "
            f"current legacy-source PDF as-at {evidence.get('pdf_as_at')}; {item.get('current_balance_summary')}."
        ),
        "ocr": {"engine": "not_run", "reason": "generated source evidence card"},
        "screen_classification": {
            "screen_class": "stock_or_balance_enquiry",
            "indicators": ["current balance pdf", "warehouse balances"],
            "text_source_chars": 0,
            "evidence_source": "current_pdf_balance_snapshot",
            "movement_clearance": "not_cleared_by_this_artifact",
        },
        "image_screen_classification": {
            "screen_class": "stock_or_balance_enquiry",
            "confidence": "source_artifact",
            "reason": "generated from parsed current balance PDF",
            "nearest_reference": "",
            "distance": None,
        },
        "stage_guard_passed": True,
        "stage_guard_reason": "source current-balance PDF evidence; movement check still separate",
    }
    state.setdefault("captures", {}).setdefault("before-balance", []).append(capture)
    save_json(state_path, state)
    return state_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build current-balance source evidence card for one SKU.")
    parser.add_argument("--sku", default=os.getenv("AUREON_CURRENT_BALANCE_PILOT_SKU", "SKU-EXAMPLE-001"))
    parser.add_argument("--attach-before-balance", action="store_true")
    args = parser.parse_args()

    manifest = load_json(RUNNER_MANIFEST)
    pdf_data = load_json(PDF_EXTRACTION)
    item = find_item(manifest, args.sku)
    out_dir = evidence_dir(item)
    png_path, json_path, evidence = build_evidence(item, pdf_data, out_dir)
    state_path = ""
    if args.attach_before_balance:
        state_path = str(attach_before_balance(item, out_dir, png_path, evidence))
    print(
        json.dumps(
            {
                "sku": item.get("sku"),
                "png": str(png_path.resolve()),
                "json": str(json_path.resolve()),
                "attached_line_evidence": state_path,
                "matching_pdf_rows": evidence.get("matching_pdf_rows"),
                "movement_clearance": evidence.get("movement_clearance"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
