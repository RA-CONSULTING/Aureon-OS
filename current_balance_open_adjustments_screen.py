#!/usr/bin/env python3
"""Open Azyra Stock > Adjustments for the current-balance pilot.

This helper performs navigation only. It does not type quantities, save lines,
or submit transactions. It defaults to dry-run and requires a separate
navigation approval flag before it will click the visible WMS Adjustments menu.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent
OUTPUT_DIR = REPO / "outputs" / "aureon_current_balance_adjustments_navigation"
sys.path.insert(0, str(REPO))

from aureon.integrations.azyra.operator_bridge import AzyraOperatorBridge
from current_balance_screen_classifier import classify_image_screen

TARGETS = {
    # Window-relative target from the visible WMS menu screenshots. It sits over
    # the "Adjustments" menu item in New Transactions, not on a submit/save control.
    "adjustments-menu": {"window_x": 560, "window_y": 188},
    # Target for the first dropdown option after clicking Adjustments.
    "increase-stock-balance": {"window_x": 960, "window_y": 372},
}


def env_true(name: str) -> bool:
    return str(os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def window_point(region: dict[str, int], target_def: dict[str, int]) -> dict[str, int]:
    return {
        "x": int(region["left"]) + target_def["window_x"],
        "y": int(region["top"]) + target_def["window_y"],
    }


def capture(bridge: AzyraOperatorBridge, name: str) -> tuple[Path, dict]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{name}_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.png"
    result = bridge.capture_screen(path, window_only=True)
    classification = classify_image_screen(path)
    return path, {"capture": result.to_dict(), "image_screen_classification": classification}


def write_target_marker(source: Path, target_def: dict[str, int]) -> str:
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return ""
    try:
        image = Image.open(source).convert("RGB")
        draw = ImageDraw.Draw(image)
        x = int(target_def["window_x"])
        y = int(target_def["window_y"])
        draw.line((x - 18, y, x + 18, y), fill=(220, 0, 0), width=3)
        draw.line((x, y - 18, x, y + 18), fill=(220, 0, 0), width=3)
        draw.ellipse((x - 8, y - 8, x + 8, y + 8), outline=(220, 0, 0), width=3)
        marked = source.with_name(source.stem + "_target_marked.png")
        image.save(marked)
        return str(marked.resolve())
    except Exception:
        return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Open Azyra Stock > Adjustments without entering or submitting stock data.")
    parser.add_argument("--dry-run", action="store_true", help="Calculate target and capture screens without clicking.")
    parser.add_argument("--confirm-navigation-only", action="store_true", help="Required with approval env before executing the click.")
    parser.add_argument("--target", choices=sorted(TARGETS), default="adjustments-menu")
    parser.add_argument(
        "--activation",
        choices=["click", "double-click", "enter"],
        default="click",
        help="Navigation-only activation method for the selected target.",
    )
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    target_def = TARGETS[args.target]
    bridge = AzyraOperatorBridge(allow_input=env_true("AZYRA_OPERATOR_ALLOW_INPUT"), allow_submit=False, allow_focus=True)
    region = bridge.window_region()
    if not region:
        print("[ERROR] Azyra window region not found.")
        return 1
    target = window_point(region, target_def)
    before_path, before = capture(bridge, "before_adjustments_navigation")
    before_class = before["image_screen_classification"].get("screen_class")
    target_marked_path = write_target_marker(before_path, target_def)

    approved = env_true("AZYRA_CURRENT_BALANCE_NAVIGATION_APPROVED") and args.confirm_navigation_only
    dry_run = args.dry_run or not approved
    focus_result = None
    activation_result = None
    after_path = None
    after = {}

    if dry_run:
        status = "dry_run_not_clicked"
        next_action = (
            "Set AZYRA_CURRENT_BALANCE_NAVIGATION_APPROVED=true and pass --confirm-navigation-only "
            "only when the visible Azyra WMS menu is ready for a non-submitting Adjustments click."
        )
    else:
        bridge.arm(live=True)
        focus_result = bridge.focus()
        if not focus_result.ok:
            print(json.dumps({"status": "focus_failed", "focus": focus_result.to_dict()}, indent=2))
            return 1
        if args.activation == "double-click":
            activation_result = bridge.double_click_window(
                target_def["window_x"],
                target_def["window_y"],
                submit_like=False,
            )
        elif args.activation == "enter":
            activation_result = bridge.press_key("enter", submit_like=False)
        else:
            activation_result = bridge.click_window(
                target_def["window_x"],
                target_def["window_y"],
                button="left",
                submit_like=False,
            )
        time.sleep(2.0)
        after_path, after = capture(bridge, "after_adjustments_navigation")
        after_class = after["image_screen_classification"].get("screen_class")
        if not activation_result.ok:
            status = "activation_failed"
            next_action = "Navigation activation failed; inspect before/after screenshots and do not run live entry."
        elif after_class == "stock_adjustments":
            status = "stock_adjustments_visible"
            next_action = "Capture fresh LP4073 pre-entry evidence; do not type or submit until evidence is approved."
        else:
            status = "navigation_not_verified"
            next_action = f"After-click screen classified as {after_class}; do not capture approval evidence yet."

    payload = {
        "ok": status == "stock_adjustments_visible" or dry_run,
        "schema_version": "azyra-current-balance-open-adjustments-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "next_action": next_action,
        "dry_run": dry_run,
        "approval_env": env_true("AZYRA_CURRENT_BALANCE_NAVIGATION_APPROVED"),
        "confirm_navigation_only": bool(args.confirm_navigation_only),
        "activation": args.activation,
        "window_region": region,
        "target_name": args.target,
        "target": {**target_def, **target},
        "target_marked_screenshot": target_marked_path,
        "before": {"path": str(before_path.resolve()), **before},
        "focus": focus_result.to_dict() if focus_result else None,
        "activation_result": activation_result.to_dict() if activation_result else None,
        "click": activation_result.to_dict() if activation_result else None,
        "after": {"path": str(after_path.resolve()), **after} if after_path else None,
    }
    out_json = OUTPUT_DIR / "current_balance_open_adjustments_status.json"
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"status": status, "dry_run": dry_run, "before_class": before_class, "target": payload["target"], "output": str(out_json)}, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
