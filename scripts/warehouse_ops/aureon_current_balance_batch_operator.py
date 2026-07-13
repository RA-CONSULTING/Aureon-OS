#!/usr/bin/env python3
"""Batch runner for Aureon current-balance fast operator.

The posting work is still performed by ``aureon_current_balance_fast_operator.py``.
This wrapper only sequences known single-location items so a live run can keep
moving through safe rows and stop cleanly on the first failure.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


REPO = Path(__file__).resolve().parent
WORKSPACE = REPO.parent
RUN_ROOT = REPO / "outputs" / "aureon_fast_current_balance_batch"
FAST_OPERATOR = REPO / "aureon_current_balance_fast_operator.py"


def stamp() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def parse_item(value: str) -> dict[str, str]:
    parts = [part.strip() for part in value.split("|")]
    if len(parts) not in {5, 6}:
        raise argparse.ArgumentTypeError(
            "--item must be formatted as SKU|QTY|LOCATION|TRACKING|PO or SKU|QTY|LOCATION|TRACKING|PO|TARGET_TOTAL"
        )
    sku, qty, location, tracking, po = parts[:5]
    target_total = parts[5] if len(parts) == 6 else ""
    if not sku or not qty or not location:
        raise argparse.ArgumentTypeError("SKU, QTY, and LOCATION are required in --item")
    if not tracking:
        tracking = po
    if not po:
        po = tracking
    return {
        "sku": sku.upper(),
        "qty": qty,
        "location": location.upper(),
        "tracking": tracking,
        "po": po,
        "target_total": target_total,
        "direction": "increase",
    }


def manifest_items(
    path: Path,
    *,
    route_status: str,
    only_increases: bool,
    max_items: int | None,
) -> list[dict[str, str]]:
    manifest = json.loads(path.read_text(encoding="utf-8-sig"))
    items: list[dict[str, str]] = []
    for entry in manifest.get("items", []):
        if entry.get("route_status") != route_status:
            continue
        action_type = str(entry.get("action_type") or "")
        direction = "decrease" if "decrease" in action_type else "increase"
        if only_increases and direction != "increase":
            continue
        if entry.get("live_route_gate") != "data_ready_route_not_proven":
            continue
        tracking = str(entry.get("tracking_number") or entry.get("tracking_numbers") or "").strip()
        if not tracking or any(separator in tracking for separator in [",", ";", "|"]):
            continue
        item = {
            "sku": str(entry.get("sku") or "").strip().upper(),
            "qty": str(entry.get("qty") or entry.get("quantity") or "").strip(),
            "location": str(entry.get("target_location") or entry.get("location") or "").strip().upper(),
            "tracking": tracking,
            "po": tracking,
            "target_total": "",
            "direction": direction,
        }
        if item["sku"] and item["qty"] and item["location"]:
            items.append(item)
        if max_items is not None and len(items) >= max_items:
            break
    return items


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--item", action="append", type=parse_item, default=[])
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--route-status", default="route_blocked")
    parser.add_argument("--only-increases", action="store_true")
    parser.add_argument("--max-items", type=int)
    parser.add_argument("--per-item-timeout", type=int, default=900)
    parser.add_argument("--confirm-live", action="store_true")
    args = parser.parse_args(argv)

    if not args.confirm_live:
        print("[ERROR] --confirm-live is required.")
        return 1

    items = list(args.item or [])
    if args.manifest:
        items.extend(
            manifest_items(
                args.manifest,
                route_status=args.route_status,
                only_increases=args.only_increases,
                max_items=args.max_items,
            )
        )
    if not items:
        print("[ERROR] No batch items supplied or selected from manifest.")
        return 1

    out_dir = RUN_ROOT / stamp()
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "batch_operator_log.jsonl"

    env = os.environ.copy()
    env["AZYRA_OPERATOR_ALLOW_INPUT"] = "true"
    env["AZYRA_OPERATOR_ALLOW_SUBMIT"] = "true"
    env["AZYRA_OPERATOR_ALLOW_FOCUS"] = "true"
    env["AZYRA_OPERATOR_REMOTEAPP_KEYBOARD_ROUTE_PROVEN"] = "true"
    env["AUREON_DESKTOP_INPUT_BACKEND"] = "pydirectinput"
    pydeps = WORKSPACE / ".codex_pydeps"
    if pydeps.exists():
        existing_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = str(pydeps) + (os.pathsep + existing_pythonpath if existing_pythonpath else "")
    if args.manifest:
        env["AUREON_CURRENT_BALANCE_RUNNER_MANIFEST"] = str(args.manifest.resolve())
        package_dir = args.manifest.resolve().parent
        ledger = package_dir / "current_balance_live_approval_ledger_20260622.json"
        evidence = package_dir / "evidence"
        if ledger.exists():
            env["AUREON_CURRENT_BALANCE_LEDGER"] = str(ledger)
        if evidence.exists():
            env["AUREON_CURRENT_BALANCE_EVIDENCE_ROOT"] = str(evidence)

    summary: list[dict[str, object]] = []
    for index, item in enumerate(items, start=1):
        cmd = [
            sys.executable,
            str(FAST_OPERATOR),
            "--sku",
            item["sku"],
            "--qty",
            item["qty"],
            "--location",
            item["location"],
            "--tracking",
            item["tracking"],
            "--po",
            item["po"],
            "--direction",
            item["direction"],
            "--confirm-live",
        ]
        if item.get("target_total"):
            cmd.extend(["--target-total", item["target_total"]])
        started_at = stamp()
        symbol = "+" if item["direction"] == "increase" else "-"
        print(f"[BATCH] {index}/{len(items)} {item['sku']} {symbol}{item['qty']} {item['location']}", flush=True)
        try:
            result = subprocess.run(
                cmd,
                cwd=str(REPO),
                env=env,
                text=True,
                capture_output=True,
                timeout=args.per_item_timeout,
            )
            entry = {
                "index": index,
                "item": item,
                "started_at": started_at,
                "finished_at": stamp(),
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except subprocess.TimeoutExpired as exc:
            entry = {
                "index": index,
                "item": item,
                "started_at": started_at,
                "finished_at": stamp(),
                "returncode": "timeout",
                "stdout": exc.stdout or "",
                "stderr": exc.stderr or "",
                "timeout_seconds": args.per_item_timeout,
            }

        summary.append(entry)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

        if entry["returncode"] != 0:
            print(json.dumps({"ok": False, "stopped_on": item, "log": str(log_path)}, indent=2))
            return 1

    (out_dir / "batch_operator_summary.json").write_text(
        json.dumps({"ok": True, "items": summary, "log": str(log_path)}, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "count": len(summary), "log": str(log_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
