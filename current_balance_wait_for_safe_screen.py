#!/usr/bin/env python3
"""Passively watch the Azyra screen before current-balance evidence capture."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent
WORKSPACE = REPO.parent
FIX_DIR = WORKSPACE / "outputs" / "aureon_goal_contract_dispatcher" / "azyra_current_balance_fix"
OUTPUT_DIR = REPO / "outputs" / "aureon_current_balance_screen_watch"

sys.path.insert(0, str(REPO))

from aureon.integrations.azyra.operator_bridge import AzyraOperatorBridge
from current_balance_screen_classifier import classify_image_screen

AUTO_BLOCKED_CLASSES = {"unknown", "outwards_transaction", "wms_menu", "stock_transaction_new"}


def watch_once(sku: str) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    screenshot_path = OUTPUT_DIR / f"screen_watch_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.png"
    bridge = AzyraOperatorBridge(allow_input=False, allow_submit=False)
    discovery = bridge.discover()
    capture = bridge.capture_screen(str(screenshot_path), window_only=True)
    classification = classify_image_screen(screenshot_path)
    screen_class = str(classification.get("screen_class", "unknown"))
    auto_blocked = screen_class != "stock_adjustments"
    if auto_blocked:
        status = "blocked_wrong_screen"
        next_action = (
            "Navigate Azyra manually to the correct Stock > Adjustments entry screen. "
            "Do not capture approval evidence from this screen."
        )
    else:
        status = "visual_confirmation_required"
        next_action = (
            "Visually confirm this is the Stock > Adjustments entry screen, then capture fresh pre-entry evidence."
        )
    result = {
        "ok": True,
        "schema_version": "azyra-current-balance-screen-watch-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sku": sku,
        "status": status,
        "next_action": next_action,
        "auto_blocked": auto_blocked,
        "auto_blocked_classes": sorted(AUTO_BLOCKED_CLASSES),
        "azyra_discovery": discovery,
        "screenshot": {
            "path": str(screenshot_path.resolve()),
            "ok": capture.ok,
            "reason": capture.reason,
        },
        "image_screen_classification": classification,
    }
    return result


def write_outputs(result: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / "current_balance_screen_watch_status.json"
    md_path = OUTPUT_DIR / "current_balance_screen_watch_status.md"
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    classification = result.get("image_screen_classification", {})
    md = [
        "# Current Balance Screen Watch",
        "",
        f"- Status: `{result.get('status')}`",
        f"- Next action: {result.get('next_action')}",
        f"- Screen class: `{classification.get('screen_class', 'unknown')}`",
        f"- Confidence: `{classification.get('confidence', 'unknown')}`",
        f"- Distance: `{classification.get('distance', '')}`",
        f"- Screenshot: `{result.get('screenshot', {}).get('path', '')}`",
        "",
        "Auto-blocked classes: `" + ", ".join(result.get("auto_blocked_classes", [])) + "`",
    ]
    md_path.write_text("\n".join(md), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Passively classify the current Azyra screen for current-balance work.")
    parser.add_argument("--sku", default="LP4073")
    parser.add_argument("--watch", action="store_true", help="Poll until the screen is no longer auto-blocked or timeout expires.")
    parser.add_argument("--timeout-seconds", type=float, default=0.0)
    parser.add_argument("--interval-seconds", type=float, default=10.0)
    args = parser.parse_args()

    deadline = time.monotonic() + args.timeout_seconds if args.watch and args.timeout_seconds > 0 else None
    while True:
        result = watch_once(args.sku)
        write_outputs(result)
        print(json.dumps({
            "status": result["status"],
            "screen_class": result["image_screen_classification"].get("screen_class"),
            "screenshot": result["screenshot"]["path"],
            "next_action": result["next_action"],
        }, indent=2))
        if not args.watch or not result["auto_blocked"]:
            return 0 if not result["auto_blocked"] else 1
        if deadline is not None and time.monotonic() >= deadline:
            return 1
        time.sleep(max(args.interval_seconds, 1.0))


if __name__ == "__main__":
    raise SystemExit(main())
