#!/usr/bin/env python3
"""Process the Azyra location-transfer manifest row by row through Aureon."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

from aureon_location_transfer_common import PHOTO_PATH, load_manifest, summarise_rows, update_manifest_row


REPO = Path(__file__).resolve().parent
OPERATOR = REPO / "aureon_location_transfer_operator.py"


def load_mock_evidence(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, Mapping):
        raise ValueError("mock evidence must be a JSON object keyed by row id")
    return {str(key): value for key, value in payload.items()}


def write_row_evidence(row_id: int, evidence: Mapping[str, Any], root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"row_{int(row_id):02d}_stock_evidence.json"
    path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    return path


def run_operator(args: list[str]) -> dict[str, Any]:
    env = os.environ.copy()
    pydeps = REPO.parent / ".codex_pydeps"
    pythonpath_parts = [str(REPO)]
    if pydeps.exists():
        pythonpath_parts.insert(0, str(pydeps))
    if env.get("PYTHONPATH"):
        pythonpath_parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
    env.setdefault("AUREON_DESKTOP_INPUT_BACKEND", "pyautogui")
    result = subprocess.run([sys.executable, str(OPERATOR), *args], cwd=str(REPO), env=env, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(
            json.dumps(
                {
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "args": args,
                },
                indent=2,
            )
        )
    return json.loads(result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--confirm-live", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--mock-evidence")
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--from-wms-first", action="store_true")
    args = parser.parse_args()

    manifest_path = Path(args.manifest).resolve()
    manifest = load_manifest(manifest_path)
    rows = [
        row
        for row in manifest["rows"]
        if isinstance(row, Mapping)
        and str(row.get("status") or "pending") == "pending"
        and str(row.get("live_route_gate") or "") == "whole_piece_transfer_route_proven"
    ]
    if args.max_rows:
        rows = rows[: args.max_rows]
    mock = load_mock_evidence(args.mock_evidence)
    mock_dir = manifest_path.parent / "mock_stock_evidence"
    processed: list[dict[str, Any]] = []

    for index, row in enumerate(rows):
        row_id = int(row.get("row_id") or 0)
        source_evidence = str(PHOTO_PATH)
        if str(row_id) in mock:
            source_evidence = str(write_row_evidence(row_id, mock[str(row_id)], mock_dir))

        command = [
            "--sku",
            str(row["sku"]),
            "--qty",
            str(row["quantity"]),
            "--from-location",
            str(row["from_location"]),
            "--to-location",
            str(row["to_location"]),
            "--source-evidence",
            source_evidence,
            "--manifest",
            str(manifest_path),
            "--row-id",
            str(row_id),
            "--operation-id",
            str(row.get("operation_id") or ""),
            "--source-manifest-index",
            str(row.get("source_manifest_index") or row.get("manifest_index") or 0),
            "--freight-unit-id",
            str(row.get("source_freight_unit_id") or ""),
            "--source-qty-balance",
            str(row.get("source_qty_balance") or ""),
            "--source-qty-free",
            str(row.get("source_qty_free") or ""),
            "--source-qty-picking",
            str(row.get("source_qty_picking") or row.get("source_qty_picking_at_location") or 0),
            "--tracking-number",
            str(row.get("tracking_number") or row.get("tracking_numbers") or ""),
            "--live-route-gate",
            str(row.get("live_route_gate") or ""),
        ]
        if str(row.get("from_location")) == "live-derived":
            command.append("--derive-source")
        if args.dry_run:
            command.append("--dry-run")
        if args.confirm_live:
            command.append("--confirm-live")
        if args.from_wms_first and index == 0:
            command.append("--from-wms")

        try:
            processed.append(run_operator(command))
        except Exception as exc:
            decision = {"status": "held_requires_review", "reason": "operator_failed", "error": str(exc)}
            update_manifest_row(manifest_path, row_id, status="held_requires_review", decision=decision)
            processed.append({"ok": False, "row_id": row_id, **decision})

    final_manifest = load_manifest(manifest_path)
    summary = summarise_rows(final_manifest["rows"])
    processed_ok = all(bool(item.get("ok")) for item in processed)
    payload = {
        "ok": processed_ok,
        "manifest_complete": summary["pending_count"] == 0,
        "manifest": str(manifest_path),
        "summary": summary,
        "processed_count": len(processed),
        "processed": processed,
    }
    (manifest_path.parent / "location_transfer_batch_result.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if processed_ok else 4


if __name__ == "__main__":
    raise SystemExit(main())
