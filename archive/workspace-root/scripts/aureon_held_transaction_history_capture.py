#!/usr/bin/env python3
"""Capture read-only Stock Enquiry history evidence for held audit SKUs."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyperclip  # type: ignore
from PIL import Image

REPO = Path(__file__).resolve().parent
WORKSPACE = REPO.parent
sys.path.insert(0, str(REPO))

from aureon.integrations.azyra.operator_bridge import AzyraOperatorBridge


DEFAULT_OUTPUT = (
    WORKSPACE
    / "outputs"
    / "aureon_goal_contract_dispatcher"
    / "historical_quantity_live_fix_20260620"
    / "evidence"
    / "held_transaction_history_20260621"
)

HELD_SKUS = [
    sku.strip().upper()
    for sku in os.getenv("AUREON_HELD_TRANSACTION_SKUS", "SKU-EXAMPLE-001,SKU-EXAMPLE-002").split(",")
    if sku.strip()
]

MODES = {
    "balance": (862, 191),
    "all_transactions": (862, 216),
    "outwards": (862, 266),
    "adjustments": (862, 316),
}


def stamp() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value).strip("_") or "item"


def bridge() -> AzyraOperatorBridge:
    os.environ["AZYRA_OPERATOR_ALLOW_INPUT"] = "true"
    os.environ["AZYRA_OPERATOR_ALLOW_SUBMIT"] = "false"
    os.environ["AZYRA_OPERATOR_ALLOW_FOCUS"] = "true"
    os.environ["AZYRA_OPERATOR_REMOTEAPP_KEYBOARD_ROUTE_PROVEN"] = "true"
    os.environ["AUREON_DESKTOP_INPUT_BACKEND"] = "pydirectinput"
    b = AzyraOperatorBridge(
        window_title="Azyra 701",
        process_query="msrdc",
        allow_input=True,
        allow_submit=False,
        allow_focus=True,
        remoteapp_keyboard_route_proven=True,
    )
    b.arm(live=True)
    return b


def rec(actions: list[tuple[str, dict[str, Any]]], name: str, result: object, delay: float = 0.2) -> None:
    actions.append((name, result.to_dict() if hasattr(result, "to_dict") else dict(result)))
    if delay:
        time.sleep(delay)


def capture(b: AzyraOperatorBridge, actions: list[tuple[str, dict[str, Any]]], path: Path, name: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rec(actions, f"capture:{name}", b.capture_screen(path, window_only=True), 0.1)
    return path.resolve()


def include_zero_checked(path: Path) -> bool:
    image = Image.open(path).convert("L")
    crop = image.crop((1000, 178, 1021, 199))
    return sum(1 for pixel in crop.getdata() if pixel < 80) > 5


def click_text(
    b: AzyraOperatorBridge,
    actions: list[tuple[str, dict[str, Any]]],
    name: str,
    x: int,
    y: int,
    text: str,
) -> None:
    rec(actions, f"click:{name}", b.click_window(x, y, submit_like=False), 0.12)
    rec(actions, f"ctrl_a:{name}", b.hotkey(["ctrl", "a"]), 0.08)
    rec(actions, f"type:{name}", b.type_text(text, method="clipboard"), 0.25)


def clear_field(
    b: AzyraOperatorBridge,
    actions: list[tuple[str, dict[str, Any]]],
    name: str,
    x: int,
    y: int,
) -> None:
    rec(actions, f"click:{name}", b.click_window(x, y, submit_like=False), 0.08)
    rec(actions, f"ctrl_a:{name}", b.hotkey(["ctrl", "a"]), 0.05)
    rec(actions, f"backspace:{name}", b.press_key("backspace", submit_like=False), 0.08)


def copy_grid(b: AzyraOperatorBridge, actions: list[tuple[str, dict[str, Any]]], label: str) -> dict[str, Any]:
    sentinel = f"__AUREON_HELD_HISTORY_{label}_{stamp()}__"
    try:
        pyperclip.copy(sentinel)
    except Exception as exc:
        return {"ok": False, "reason": f"clipboard_seed_failed:{exc}", "changed": False, "text": ""}
    rec(actions, f"{label}:click_grid", b.click_window(760, 555, submit_like=False), 0.12)
    rec(actions, f"{label}:grid_ctrl_a", b.hotkey(["ctrl", "a"]), 0.15)
    rec(actions, f"{label}:grid_ctrl_c", b.hotkey(["ctrl", "c"]), 0.45)
    try:
        text = pyperclip.paste()
    except Exception as exc:
        return {"ok": False, "reason": f"clipboard_read_failed:{exc}", "changed": False, "text": ""}
    return {"ok": True, "changed": text != sentinel, "text": text}


def prepare_stock_code(b: AzyraOperatorBridge, actions: list[tuple[str, dict[str, Any]]], sku: str) -> None:
    click_text(b, actions, "stock_code", 360, 237, sku)
    clear_field(b, actions, "tracking", 400, 307)
    clear_field(b, actions, "storage_piece", 400, 342)
    clear_field(b, actions, "location", 400, 377)
    rec(actions, "commit_stock_code", b.press_key("tab", submit_like=False), 0.55)


def run_sku(b: AzyraOperatorBridge, root: Path, sku: str) -> dict[str, Any]:
    sku = sku.strip().upper()
    out_dir = root / f"{safe_name(sku)}"
    out_dir.mkdir(parents=True, exist_ok=True)
    actions: list[tuple[str, dict[str, Any]]] = []
    captures: dict[str, dict[str, Any]] = {}

    rec(actions, "focus", b.focus(), 0.2)
    open_path = capture(b, actions, out_dir / f"00_open_{stamp()}.png", "open")
    if not include_zero_checked(open_path):
        rec(actions, "tick_include_zero", b.click_window(1010, 187, submit_like=False), 0.25)

    prepare_stock_code(b, actions, sku)
    capture(b, actions, out_dir / f"01_filled_{stamp()}.png", "filled")

    for mode, (x, y) in MODES.items():
        rec(actions, f"{mode}:select_radio", b.click_window(x, y, submit_like=False), 0.18)
        rec(actions, f"{mode}:click_select", b.click_window(712, 394, submit_like=False), 2.2)
        image = capture(b, actions, out_dir / f"{mode}_{stamp()}.png", mode)
        clipboard = copy_grid(b, actions, mode)
        captures[mode] = {
            "image": str(image),
            "clipboard_changed": bool(clipboard.get("changed")),
            "clipboard_text": clipboard.get("text", ""),
        }
        (out_dir / f"{mode}_clipboard.txt").write_text(str(clipboard.get("text", "")), encoding="utf-8")

    return {
        "sku": sku,
        "out_dir": str(out_dir.resolve()),
        "captures": captures,
        "actions": actions,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--sku", action="append", help="SKU to capture; can be repeated. Defaults to held historical SKUs.")
    parser.add_argument("--confirm-readonly-query", action="store_true")
    args = parser.parse_args(argv)
    if not args.confirm_readonly_query:
        print("[ERROR] --confirm-readonly-query is required.")
        return 1

    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=True)
    b = bridge()
    skus = args.sku or HELD_SKUS
    results = []
    for sku in skus:
        results.append(run_sku(b, root, sku))

    payload = {
        "ok": True,
        "schema_version": "aureon-held-transaction-history-capture-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "read_only_stock_enquiry",
        "skus": [item["sku"] for item in results],
        "results": results,
    }
    out = root / f"history_capture_{stamp()}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(out.resolve()), "skus": payload["skus"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
