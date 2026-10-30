"""Write mcp/aureon_public/COVERAGE_PLAN.md from the pinned inventory.

Every count comes from docs/mcp/inventory.json and public_entry_refusal.
The file is refused when its sha256 is not INVENTORY_SHA256.

    env -u PYTHONPATH PYTHONPATH=mcp python3.12 -m aureon_public.coverage_plan --check
    env -u PYTHONPATH PYTHONPATH=mcp python3.12 -m aureon_public.coverage_plan --write
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from aureon_public.body import (
    _BLOCKED,
    _CONSTRUCTOR_ALLOWLIST,
    INVENTORY_SHA256,
    _inventory,
    package_depth,
    public_entry_refusal,
)
from aureon_public.paths import repo_root

PLAN_PATH = Path("mcp") / "aureon_public" / "COVERAGE_PLAN.md"
FENCE = set(_BLOCKED) | {"unified_margin_trader"}

STAGE_TITLE = {
    1: "Deterministic read-only",
    2: "Read-only with a process or write mark",
    3: "Operator-scoped, no key, order, or fetch mark",
    4: "Keys, orders, network, and the refused-imports fence",
}


def safety_category(text: str) -> str:
    """One category for an inventory safety sentence. The words are the scanner's."""

    if text.startswith("personal or key") or "reads keys" in text:
        return "key"
    if "order" in text or "live_orders" in text:
        return "order"
    if text.startswith("live public fetch"):
        return "fetch"
    if text.startswith("process") or "UI start" in text or "loop" in text:
        return "process"
    if "write" in text and "no repo write" not in text:
        return "write"
    if "risky token" in text:
        return "risky"
    if "operator-scoped" in text or "no public import" in text:
        return "operator"
    if text.startswith("runs from inputs"):
        return "pure"
    if "module surface" in text:
        return "surface"
    if "file does not parse" in text:
        return "parse"
    return "other"


def stage_for(package: str, categories: set[str]) -> int:
    """Earlier stages are the safer reads. Stage 4 stays behind the fence."""

    if package in FENCE or "order" in categories or "key" in categories or "fetch" in categories:
        return 4
    if "process" in categories or "write" in categories:
        return 2
    if "operator" in categories and "pure" not in categories:
        return 3
    return 1


def _rows() -> tuple[list[dict], dict[str, dict[str, int]]]:
    loaded, _index = _inventory()
    if not loaded:
        raise SystemExit("inventory did not load")
    return loaded, package_depth()


def plan_rows() -> list[dict]:
    """One row per package. Counts are the pinned inventory and the current guard."""

    loaded, depth = _rows()
    by_package: dict[str, list[dict]] = defaultdict(list)
    for row in loaded:
        by_package[row["package"]].append(row)
    opened = _opened_by_allowlist(loaded)
    rows = []
    for package in sorted(by_package):
        items = by_package[package]
        categories = {safety_category(str(item.get("safety") or "")) for item in items}
        stage = stage_for(package, categories)
        counted = depth[package]
        rows.append(
            {
                "categories": sorted(categories),
                "fence": package in FENCE or "order" in categories,
                "listed": len(items),
                "opened_by_allowlist": opened.get(package, 0),
                "package": package,
                "public_entry_points": counted["public_entry_points"],
                "reachable": counted["reachable"],
                "stage": stage,
            }
        )
    rows.sort(key=lambda row: (row["stage"], row["package"]))
    return rows


def _opened_by_allowlist(loaded: list[dict]) -> dict[str, int]:
    """Reachable methods whose class is allowlisted. Those were refused before the list."""

    counts: dict[str, int] = defaultdict(int)
    seen: set[tuple[str, str]] = set()
    for row in loaded:
        if row["kind"] != "method" or row["server"] != "public":
            continue
        key = (str(row["module"]), str(row["symbol"]))
        if key in seen:
            continue
        seen.add(key)
        class_name = str(row["symbol"]).rsplit(".", 1)[0]
        if (str(row["module"]), class_name) not in _CONSTRUCTOR_ALLOWLIST:
            continue
        if public_entry_refusal(row) is None:
            counts[str(row["package"])] += 1
    return counts


def _excluded_packages() -> list[str]:
    from aureon_public.more_layers import UPDATES

    return sorted(package for package, kind, _reason in UPDATES if kind == "excluded")


def render() -> str:
    rows = plan_rows()
    listed = sum(row["listed"] for row in rows)
    public = sum(row["public_entry_points"] for row in rows)
    reachable = sum(row["reachable"] for row in rows)
    opened = sum(row["opened_by_allowlist"] for row in rows)
    excluded = _excluded_packages()
    first = next(row["package"] for row in rows if row["stage"] == 1)
    lines = [
        "# Public MCP coverage plan",
        "",
        "Counts are the pinned `docs/mcp/inventory.json`. A public entry point is a public function or method. Reachable means `public_entry_refusal` returns None, so `body_call` will run it. A listed module or class is not an entry point. The sha256 below is `INVENTORY_SHA256`. A different inventory file is not loaded.",
        "",
        f"Inventory sha256: `{INVENTORY_SHA256}`",
        "",
        "Reproduce:",
        "",
        "```bash",
        "env -u PYTHONPATH PYTHONPATH=mcp python3.12 -m aureon_public.coverage_plan --check",
        "```",
        "",
        "`--write` rewrites this file from the same function.",
        "",
        f"Listed symbols: {listed}. Public entry points: {public}. Reachable now: {reachable}. The previous plan recorded 879 reachable. Methods open because a constructor is allowlisted: {opened}. The refused-imports fence is unchanged.",
        "",
        "## Stage order",
        "",
        "The stage is the inventory safety text, not a new scan.",
        "",
        "1. Deterministic read-only. No key, order, live-fetch, process, or write sentence, and the package is not operator-only.",
        "2. A process or write sentence, and still no key, order, or live-fetch sentence.",
        "3. Operator-scoped, with no pure public row and no key, order, or live-fetch sentence.",
        "4. Last. Any key, order, or live-fetch sentence, plus the refused-imports fence. The fence is `_BLOCKED` and `unified_margin_trader`. This run does not add to it and does not import it.",
        "",
        f"Packages still excluded by `more_layers`: {', '.join(excluded)}. `generated` left that list because its score model is deterministic and does not fetch. The other exclusions stay.",
        "",
        f"Within a stage, packages are alphabetical. The first package is `{first}`.",
        "Stage 1 is the deterministic read-only packages. This run opens the rest of stage 1: generated, organism, and swarm, after alignment.",
        "Stage 2 is not opened. A stage-2 package has a process or write sentence, so it is not read-only. Those packages stay for a later run, with their own records.",
        "",
        "## Counts",
        "",
        "| Stage | Package | Listed | Public entry points | Reachable now |",
        "| ---: | --- | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['stage']} | {row['package']} | {row['listed']} | {row['public_entry_points']} | {row['reachable']} |"
        )
    lines.extend(
        [
            "",
            "## Fence",
            "",
            "These packages are stage 4 because they are on the refused-imports fence or an inventory row says order. `body_call` returns `live_orders: refused` and does not import them.",
            "",
        ]
    )
    for name in sorted(FENCE):
        lines.append(f"- `{name}`")
    by_name = {row["package"]: row for row in rows}
    queen_stage = by_name["queen"]["stage"]
    miner_stage = by_name["miner"]["stage"]
    both_open = max(queen_stage, miner_stage)
    lines.extend(
        [
            "",
            f"## Stage {both_open}",
            "",
            f"`alignment/unified_directive.py` `get_unified_directive` is not a stage-1 tool. Queen is stage {queen_stage}. Miner is stage {miner_stage}. Both are open at stage {both_open}, so this entry point waits there. It is not called by a tool in this run.",
            "",
            "Calling `get_unified_directive` constructs `UnifiedHarmonicDirective` with auto-wire on. That constructs `QueenAIBridge` and `MinerAIBridge`. Each bridge loads `AureonBrainAdapter` as the reasoning backend when the Ollama switchboard is missing or unhealthy, and each bridge wires itself to a `ThoughtBus`. The constructor imports `aureon.queen`, `aureon.miner`, and `aureon.swarm_motion`.",
            "",
            "## This run",
            "",
            "`alignment` stays the first stage-1 package. `get_pillar_alignment` stays, with `auto_load_pillars` false. `get_unified_directive` is not a stage-1 tool. This run also opens `generated`, `organism`, and `swarm`.",
            "Generated is the deterministic score model. It does not fetch. Swarm tools use fixtures from the swarm tests or fixed example arguments. Classes that need nested agent instances stay off the constructor allowlist: Cluster, Company, Zone, FleadhCompany, VisitorAgent, and WorkerAgent. Name-blocked `run_` entry points stay refused. Properties such as SwarmAgent.purity are not given tools because the worker calls methods. `validate_seat_receipt` stays reachable through `body_call` and is not a second tool: the public result cap would drop receipt fields before another call.",
            "Stage 2 was not started. No stage-2 tool was written.",
            "",
            "The pin stays `8aa6a2d971cc529484e2a5e261e28afafab4e4f4`. The alignment modules at this checkout match that pin, so the tools do not need a newer commit. `GUARD_BLOB` and `INVENTORY_SHA256` are unchanged.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="aureon-public-coverage-plan")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    text = render()
    path = repo_root() / PLAN_PATH
    if args.check:
        current = path.read_text(encoding="utf-8") if path.is_file() else ""
        if current != text:
            raise SystemExit("COVERAGE_PLAN.md does not match the inventory")
        return
    if args.write or not args.check:
        path.write_text(text, encoding="utf-8")
        print(path)


if __name__ == "__main__":
    main()
