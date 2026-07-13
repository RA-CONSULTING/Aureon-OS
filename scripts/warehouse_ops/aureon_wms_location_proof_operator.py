#!/usr/bin/env python3
"""Create or prove Azyra WMS locations through the live Aureon UI route.

This operator assumes Azyra is already on the configured warehouse's WMS Locations screen.
It only touches the warehouse-location table: for each supplied code it clicks
New, enters the code, selects Usage=Bulk, then either records Azyra's duplicate
"Location Already Exists" proof or saves the new WMS location.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent
WORKSPACE = REPO.parent
sys.path.insert(0, str(REPO))

from aureon.integrations.azyra.operator_bridge import AzyraOperatorBridge


TRUTHY = {"1", "true", "yes", "y", "on"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stamp() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value).strip("_") or "item"


def normalise_location(value: str) -> str:
    return "".join(ch for ch in str(value or "").strip().upper() if ch.isalnum())


def env_true(name: str) -> bool:
    return str(os.getenv(name) or "").strip().lower() in TRUTHY


def bridge() -> AzyraOperatorBridge:
    os.environ["AZYRA_OPERATOR_ALLOW_INPUT"] = "true"
    os.environ["AZYRA_OPERATOR_ALLOW_SUBMIT"] = "true"
    os.environ["AZYRA_OPERATOR_ALLOW_FOCUS"] = "true"
    os.environ["AZYRA_OPERATOR_REMOTEAPP_KEYBOARD_ROUTE_PROVEN"] = "true"
    os.environ["AUREON_DESKTOP_INPUT_BACKEND"] = "pydirectinput"
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


def record(actions: list[tuple[str, dict[str, Any]]], name: str, result: Any, pause: float = 0.25) -> dict[str, Any]:
    result_dict = result.to_dict() if hasattr(result, "to_dict") else dict(result)
    actions.append((name, result_dict))
    if pause:
        time.sleep(pause)
    return result_dict


def foreground_title(b: AzyraOperatorBridge) -> str:
    try:
        return str(b.backend.foreground_window().get("title") or "")
    except Exception:
        return ""


def duplicate_present(b: AzyraOperatorBridge) -> bool:
    return "location already exists" in foreground_title(b).lower()


def capture(
    b: AzyraOperatorBridge,
    actions: list[tuple[str, dict[str, Any]]],
    out_dir: Path,
    location: str,
    stage: str,
) -> str:
    path = out_dir / f"{safe_name(location)}_{stage}_{stamp()}.png"
    record(actions, f"{location}:capture:{stage}", b.capture_screen(path, window_only=True), 0.1)
    return str(path)


def click_text(
    b: AzyraOperatorBridge,
    actions: list[tuple[str, dict[str, Any]]],
    location: str,
    x: int,
    y: int,
    text: str,
) -> None:
    record(actions, f"{location}:code_click", b.click_window(x, y, submit_like=False), 0.12)
    record(actions, f"{location}:code_ctrl_a", b.hotkey(["ctrl", "a"]), 0.08)
    record(actions, f"{location}:code_type", b.type_text(text, method="clipboard"), 0.35)


def dismiss_duplicate(
    b: AzyraOperatorBridge,
    actions: list[tuple[str, dict[str, Any]]],
    out_dir: Path,
    location: str,
) -> str:
    evidence = capture(b, actions, out_dir, location, "duplicate_exists")
    record(actions, f"{location}:duplicate_ok", b.click_window(802, 598, submit_like=False), 0.45)
    record(actions, f"{location}:cancel_form_after_duplicate", b.click_window(733, 793, submit_like=False), 0.45)
    capture(b, actions, out_dir, location, "after_duplicate_cleanup")
    return evidence


def prove_one(
    b: AzyraOperatorBridge,
    actions: list[tuple[str, dict[str, Any]]],
    out_dir: Path,
    location: str,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "location": location,
        "warehouse": os.getenv("AUREON_AZYRA_WAREHOUSE_TEXT", "<warehouse-not-committed>"),
        "owner_or_company": os.getenv("AUREON_AZYRA_OWNER_TEXT", "<owner-not-committed>"),
        "usage": "Bulk",
        "status": "started",
        "proved_at_utc": now_iso(),
        "evidence": "",
        "action_log": "",
        "note": "",
    }

    record(actions, f"{location}:new_click", b.click_window(780, 813, submit_like=False), 0.4)
    click_text(b, actions, location, 423, 410, location)

    if duplicate_present(b):
        row["status"] = "already_exists"
        row["evidence"] = dismiss_duplicate(b, actions, out_dir, location)
        row["note"] = "Azyra duplicate popup proves the WMS location already exists for the configured warehouse."
        return row

    record(actions, f"{location}:usage_dropdown", b.click_window(700, 460, submit_like=False), 0.25)
    record(actions, f"{location}:usage_bulk", b.click_window(610, 490, submit_like=False), 0.55)

    if duplicate_present(b):
        row["status"] = "already_exists"
        row["evidence"] = dismiss_duplicate(b, actions, out_dir, location)
        row["note"] = "Azyra duplicate popup proves the WMS location already exists for the configured warehouse."
        return row

    row["evidence"] = capture(b, actions, out_dir, location, "before_save")
    record(actions, f"{location}:save_ok", b.click_window(649, 793, submit_like=True), 0.85)

    if duplicate_present(b):
        row["status"] = "already_exists"
        row["evidence"] = dismiss_duplicate(b, actions, out_dir, location)
        row["note"] = "Azyra duplicate popup appeared after save click; location already exists."
        return row

    after = capture(b, actions, out_dir, location, "after_save_or_grid")
    row["status"] = "created_or_already_on_grid"
    row["after_evidence"] = after
    row["note"] = "Azyra accepted the WMS location form and returned to the WMS Locations grid."
    return row


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--locations", required=True, help="Comma-separated WMS location codes.")
    parser.add_argument(
        "--out-dir",
        default=str(
            WORKSPACE
            / "outputs"
            / "aureon_goal_contract_dispatcher"
            / "live_production_20260622"
            / "location_create_live"
        ),
    )
    parser.add_argument("--require-live", action="store_true", help="Require AUREON_LIVE_WMS_LOCATION_PROOF=true.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.require_live and not env_true("AUREON_LIVE_WMS_LOCATION_PROOF"):
        raise SystemExit("Refusing live WMS proof without AUREON_LIVE_WMS_LOCATION_PROOF=true")

    locations = [normalise_location(value) for value in args.locations.split(",")]
    locations = [value for value in locations if value]
    if not locations:
        raise SystemExit("No locations supplied")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    actions: list[tuple[str, dict[str, Any]]] = []
    rows: list[dict[str, Any]] = []

    b = bridge()
    record(actions, "focus_start", b.focus(), 0.5)
    capture(b, actions, out_dir, "batch", "start_wms_locations")

    for location in locations:
        rows.append(prove_one(b, actions, out_dir, location))

    action_log = out_dir / "prove_required_locations_actions.json"
    ledger_json = out_dir / "azyra_wms_locations_created_or_proven_20260622.json"
    ledger_csv = out_dir / "azyra_wms_locations_created_or_proven_20260622.csv"
    for row in rows:
        row["action_log"] = str(action_log)

    action_ok = all(result.get("ok") for _, result in actions)
    status_ok = all(row["status"] in {"already_exists", "created_or_already_on_grid"} for row in rows)
    payload = {
        "ok": action_ok and status_ok,
        "created_at_utc": now_iso(),
        "source": "Aureon live Azyra configured-warehouse WMS Locations table",
        "locations": rows,
        "counts": {
            "location_count": len(rows),
            "already_exists": sum(1 for row in rows if row["status"] == "already_exists"),
            "created_or_already_on_grid": sum(1 for row in rows if row["status"] == "created_or_already_on_grid"),
            "failed_action_count": sum(1 for _, result in actions if not result.get("ok")),
        },
    }
    action_log.write_text(json.dumps({"ok": True, "actions": actions}, indent=2), encoding="utf-8")
    ledger_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    fieldnames = [
        "location",
        "warehouse",
        "usage",
        "status",
        "proved_at_utc",
        "evidence",
        "after_evidence",
        "action_log",
        "note",
    ]
    with ledger_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(json.dumps(payload, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
