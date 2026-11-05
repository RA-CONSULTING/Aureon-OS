"""Miner read gate. Queen, exchanges, and the public depth table stay put.

A miner function or method is opened when the read gate and the miner call
sweep both allow it. ``body_call`` runs those entry points. The inventory
server field stays operator, so ``package_depth`` keeps miner at 0 and the
stages 1 and 2 reachable count is not republished.

    bash measured/aureon_public_miner_sweep.sh
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

RECORD_NAME = "aureon_public_miner_sweep.json"
# body_call entry points the miner test exercises. A refused point is not listed.
TESTED: tuple[tuple[str, str], ...] = (
    ("miner/miner_inhouse_ai_bridge.py", "MinerAIInsight.to_dict"),
)
_READ_CONSTRUCTORS = {
    ("miner/miner_inhouse_ai_bridge.py", "MinerAIInsight"),
}
_ORDER_RESULT_KEYS = {"order_id", "client_order_id", "exchange_order_id"}
_FENCE_MODULES = (
    "aureon.exchanges",
    "aureon.trading",
    "aureon.bots",
    "aureon.bots_intelligence",
    "aureon.bridges",
    "aureon.scanners",
    "unified_margin_trader",
)


def miner_constructor_allowed(module: str, class_name: str) -> bool:
    """True for the miner dataclass the read gate can construct.

    ``MinerAIBridge`` stays off this set. Its constructor loads the adapter.
    """

    return (module, class_name) in _READ_CONSTRUCTORS


def entry_rows() -> list[dict[str, Any]]:
    """Miner functions and methods in the pinned inventory. Modules and classes are not entry points."""

    from aureon_public.body import _inventory

    rows, _index = _inventory()
    seen: set[tuple[str, str]] = set()
    found: list[dict[str, Any]] = []
    for row in rows:
        if str(row.get("package") or "") != "miner":
            continue
        if row.get("kind") not in {"function", "method"}:
            continue
        key = (str(row["module"]), str(row["symbol"]))
        if key in seen:
            continue
        seen.add(key)
        found.append(row)
    found.sort(key=lambda item: (str(item["module"]), str(item["symbol"])))
    return found


def _is_property(module: str, symbol: str) -> bool:
    from aureon_public.body import file_for

    class_name, _, method_name = symbol.partition(".")
    if not method_name:
        return False
    path = file_for(module)
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError):
        return False
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == method_name:
                return any(_decorator_name(deco) == "property" for deco in item.decorator_list)
    return False


def _decorator_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def read_gate_refusal(row: dict[str, Any]) -> str | None:
    """Why this miner row is not a read. None when the call sweep may still open it."""

    from aureon_public.body import _function_source, _leaky_parameter, _name_blocked, _quiet_source
    from aureon_public.coverage_plan import safety_category
    from aureon_public.inventory_scan import ORDER_RE

    text = str(row.get("safety") or "")
    category = safety_category(text)
    if category == "order" or "live_orders" in text:
        return "live orders are refused"
    if category == "key":
        return "key or personal material is not read"
    if category == "fetch":
        return "live fetch is not part of this call"
    if "risky token" in text:
        return "read gate refuses a risky token"
    if category in {"process", "write"} or "write or process start" in text:
        return "read gate refuses a process or write"
    module = str(row["module"])
    symbol = str(row["symbol"])
    if _is_property(module, symbol):
        return "property is not called; the worker calls methods"
    blocked = _name_blocked(symbol)
    if blocked:
        return blocked
    if _leaky_parameter(module, symbol):
        return "parameter can carry a url, path, file, or host"
    source = _function_source(module, symbol)
    if ORDER_RE.search(symbol + "\n" + source):
        return "live orders are refused"
    if not _quiet_source(module, symbol):
        return "source is not a quiet read"
    if symbol == "get_miner_ai_bridge" or symbol.startswith("MinerAIBridge."):
        return "constructor loads the miner bridge"
    return None


def order_keys(value: Any) -> list[str]:
    """Order identifiers in a call result. A verdict string is not an order."""

    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key) in _ORDER_RESULT_KEYS:
                found.append(str(key))
            found.extend(order_keys(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(order_keys(item))
    return found


def fence_modules(loaded: list[str]) -> list[str]:
    """Queen, exchanges, trading, and the other fence imports. Miner itself is the target."""

    names = []
    for name in loaded:
        if name in {"aureon.queen", "aureon.swarm_motion"} or name.startswith(
            ("aureon.queen.", "aureon.swarm_motion.")
        ):
            names.append(name)
            continue
        if name in _FENCE_MODULES or any(name.startswith(prefix + ".") for prefix in _FENCE_MODULES):
            names.append(name)
    return sorted(set(names))


def runtime_refusal(read_gate: str | None, measured: str | None) -> str | None:
    """The sentence ``body_call`` returns. A measured hazard outranks the static gate."""

    if measured and measured != "call did not finish":
        return measured
    if read_gate:
        return read_gate
    return measured


def opened_entry(read_gate: str | None, measured: str | None, called: bool) -> bool:
    return read_gate is None and measured is None and called is True


def _record_path() -> Path:
    from aureon_public.paths import repo_root

    return repo_root() / "measured" / RECORD_NAME


def load_record() -> dict[str, Any] | None:
    path = _record_path()
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, dict) else None


def _entry_index(record: dict[str, Any] | None) -> dict[tuple[str, str], dict[str, Any]]:
    table: dict[tuple[str, str], dict[str, Any]] = {}
    if not isinstance(record, dict):
        return table
    for row in record.get("entries") or []:
        if isinstance(row, dict) and row.get("module") and row.get("symbol"):
            table[(str(row["module"]), str(row["symbol"]))] = row
    return table


def miner_entry_refusal(row: dict[str, Any]) -> str | None:
    """Why ``body_call`` will not run this miner entry point. None when it may run.

    The stages 1 and 2 call sweep sets ``_sweep_measuring``. Miner stays out of
    that sweep. This function answers the live server from the miner record.
    """

    from aureon_public import body as body_module

    if body_module._sweep_measuring:
        return "miner entry point stays out of the stages 1 and 2 call sweep"
    record = load_record()
    if record is None:
        return "miner call sweep record is missing"
    key = (str(row.get("module") or ""), str(row.get("symbol") or ""))
    entry = _entry_index(record).get(key)
    if entry is None:
        return "miner entry point is not in the call sweep"
    if entry.get("opened") is True:
        return None
    return str(entry.get("refusal") or "miner entry point is not open")


def summarize(entries: list[dict[str, Any]], public_table: dict[str, Any]) -> dict[str, Any]:
    """Call-sweep delta for miner. The public table numbers are the baseline."""

    opened = [row for row in entries if row.get("opened") is True]
    tested = [
        row
        for row in opened
        if (str(row.get("module")), str(row.get("symbol"))) in set(TESTED)
    ]
    swept = len(entries)
    refused = swept - len(opened)
    return {
        "baseline_public_entry_points": int(public_table["miner_public_entry_points"]),
        "baseline_reachable": int(public_table["miner_reachable"]),
        "baseline_refused": int(public_table["miner_refused"]),
        "baseline_tested": int(public_table["miner_tested"]),
        "opened": len(opened),
        "opened_delta": len(opened) - int(public_table["miner_reachable"]),
        "refused": refused,
        "refused_delta": refused - int(public_table["miner_refused"]),
        "swept": swept,
        "tested": len(tested),
        "tested_delta": len(tested) - int(public_table["miner_tested"]),
    }


def public_table_snapshot() -> dict[str, Any]:
    """Miner row and the all-package reachable sum from the public depth table."""

    from aureon_public.coverage_plan import plan_rows

    rows = plan_rows()
    miner = next(row for row in rows if row["package"] == "miner")
    return {
        "miner_listed": miner["listed"],
        "miner_public_entry_points": miner["public_entry_points"],
        "miner_reachable": miner["reachable"],
        "miner_refused": miner["refused"],
        "miner_tested": miner["tested"],
        "reachable_all_packages": sum(row["reachable"] for row in rows),
        "tested_all_packages": sum(row["tested"] for row in rows),
    }


def plan_lines() -> list[str]:
    """Lines for COVERAGE_PLAN.md. Missing record stays an explicit gap."""

    record = load_record()
    lines = [
        "## Miner surface",
        "",
        "This section is the miner read gate. Queen and exchanges are outside it. The counts in the table above stay on the inventory server field. Miner there is operator, so that row stays at public entry points 0. `package_depth` keeps miner reachable at 0. `OPEN_PLAN_THROUGH` stays 2. The pin stays `34864ff0547d2cff03e707414743a3b0cc8770b5`. Go-live stays HOLD. The stages 1 and 2 call sweep file is not rewritten. No order is sent.",
        "",
    ]
    if record is None:
        lines.extend(
            [
                "`measured/aureon_public_miner_sweep.json` is missing. No miner entry point is open. `body_call` refuses each miner function and method with `miner call sweep record is missing`.",
                "",
                "Reproduce the miner sweep with `bash measured/aureon_public_miner_sweep.sh`.",
                "",
            ]
        )
        return lines
    delta = record.get("delta") if isinstance(record.get("delta"), dict) else {}
    table = record.get("public_table") if isinstance(record.get("public_table"), dict) else {}
    lines.append(
        "The miner sweep calls each miner function and method with no arguments, sockets blocked, process starts blocked, and writes outside the sandbox blocked. "
        f"Swept {delta.get('swept')}. Opened {delta.get('opened')}. Tested {delta.get('tested')}. Refused {delta.get('refused')}. "
        f"Opened delta {delta.get('opened_delta')}. Tested delta {delta.get('tested_delta')}. Refused delta {delta.get('refused_delta')}. "
        f"The public table at measurement time listed miner reachable {table.get('miner_reachable')} and all-package reachable {table.get('reachable_all_packages')}. Those table figures are not republished from this sweep."
    )
    lines.append(
        "`body_call` runs an opened entry point. A measured hazard is the refusal sentence when the call loaded queen, swarm_motion, inhouse_ai, ollama_config, an HTTP client, the exchanges fence, or an order id, or when it opened a connection, started a process, or wrote outside the sandbox. The read gate supplies the sentence when the call had no such hazard and is still not a read. `MinerAIBridge` stays unconstructed on the public path. `MinerAIInsight` is the constructor this gate allows."
    )
    lines.append("Opened:")
    opened = [row for row in record.get("entries") or [] if isinstance(row, dict) and row.get("opened") is True]
    if not opened:
        lines.append("- none")
    for row in opened:
        lines.append(f"- `{row.get('module')}` `{row.get('symbol')}`")
    lines.append("Refused:")
    refused = [row for row in record.get("entries") or [] if isinstance(row, dict) and row.get("opened") is not True]
    if not refused:
        lines.append("- none")
    for row in refused:
        lines.append(f"- `{row.get('module')}` `{row.get('symbol')}`: {row.get('refusal')}")
    lines.extend(
        [
            "",
            "Reproduce the miner sweep with `bash measured/aureon_public_miner_sweep.sh`. The test is `tests/test_aureon_public_miner.py`.",
            "",
        ]
    )
    return lines
