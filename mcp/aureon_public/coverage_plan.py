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

    # compose_repository_layers loads core.organism_composition, which imports
    # aureon.inhouse_ai.llm_adapter, agent_runner, orchestrator,
    # aureon.ollama_config, and aureon.autonomous.aureon_internal_coding_workforce.
    # inhouse_ai is excluded. That chain is not a stage-1 read.
    if package == "organism":
        return 4
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
        "bash measured/aureon_public_stage1_run.sh",
        "bash measured/aureon_public_stage2_sweep.sh",
        "bash measured/aureon_public_call_sweep.sh",
        "env -u PYTHONPATH /tmp/aureon-public-venv/bin/python -m pytest tests/test_aureon_public_mcp.py tests/test_aureon_body.py tests/bio/test_mcp_*.py tests/test_aureon_public_alignment.py tests/test_aureon_public_stage1.py --tb=line",
        "```",
        "",
        "`--write` rewrites this file from the same function. `measured/aureon_public_stage1_run.sh` installs `mcp/aureon_public/requirements.txt` and `mcp/aureon_public/test-requirements.txt`, then rewrites both `measured/aureon_public_alignment.json` and `measured/aureon_public_stage1.json`. `test-requirements.txt` is the test install: pytest, pytest-timeout, flask, pandas, and scipy. It is not the public server runtime. `measured/aureon_public_stage2_sweep.sh` and `measured/aureon_public_call_sweep.sh` copy the checkout under an ordinary temp parent, place fake `NEXUS-LIVE-FEED-` and `Aureon-Trading--Project-Sero` checkouts beside that copy, block sockets, and rewrite their measured records. Each record names the pin, the `aureon_source` kind, and that temp parent.",
        "",
        f"Listed symbols: {listed}. Public entry points: {public}. Reachable now: {reachable}. The previous plan recorded 89 reachable. Methods open because a constructor is allowlisted: {opened}. The refused-imports fence is unchanged.",
        "Only the stage-1 tools are tested. Reachable now is what `body_call` still runs after the call sweep. Plan stages 3 and 4 stay closed. Stage 2 reach that remains is untested, unaudited reach, not coverage. The call sweep calls every entry point that was still reachable, with no arguments, and refuses one that opens a connection or loads queen, miner, swarm_motion, inhouse_ai, ollama_config, or an HTTP client. `get_unified_directive` is refused that way. It does not build the queen and miner bridges.",
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
        "Stage 1 is the deterministic read-only packages. This run opens generated and swarm, after alignment. Organism is stage 4 because its join loads the in-house adapter chain.",
        "Stage 2 has no new tools. Clean stage-2 entry points stay callable through `body_call`. A stage-2 module whose import loads an adapter or an HTTP client, or opens a connection, is refused.",
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
            f"`alignment/unified_directive.py` `get_unified_directive` is not a stage-1 tool. Queen is stage {queen_stage}. Miner is stage {miner_stage}. `body_call` refuses it now. The no-argument call is in the call sweep.",
            "",
            "Calling `get_unified_directive` constructs `UnifiedHarmonicDirective` with auto-wire on. That constructs `QueenAIBridge` and `MinerAIBridge`. Each bridge loads `AureonBrainAdapter` as the reasoning backend when the Ollama switchboard is missing or unhealthy, and each bridge wires itself to a `ThoughtBus`. The call imports `aureon.queen`, `aureon.miner`, and `aureon.swarm_motion`, and it attempted a connection to `127.0.0.1:11434`. The sweep blocked that socket.",
            "",
            "## This run",
            "",
            "`alignment` stays the first stage-1 package. `get_pillar_alignment` stays, with `auto_load_pillars` false. `get_unified_directive` is not a stage-1 tool. This run opens `generated` and `swarm`. `organism` is not opened.",
            "Generated was on the more_layers exclusion list. It is open because `aureon/generated/research_cinema/harmonic_nexus_score_model.py` imports only dataclasses and its module docstring calls it a deterministic helper, not trading authority. The four entry points are `build_default_inputs`, `HarmonicNexusScoreInputs.normalized`, `harmonic_nexus_score`, and `score_breakdown`. `tests/generated/test_harmonic_nexus_score_model.py` shows all-ones inputs score 100.0. That 100 is the weighted sum in that file. It does not score any Aureon or HNC claim and cannot be quoted as evidence.",
            "`body_call` refuses `organism/repository_layers.py` `compose_repository_layers`. With the checkout beside `NEXUS-LIVE-FEED-` and `Aureon-Trading--Project-Sero`, that call uses `Path(__file__).parents[3]`, independent of `AUREON_REPOS_ROOT`, and execs those sibling modules outside the pin. One call also loads `core.organism_composition`, and through that `aureon.inhouse_ai.llm_adapter`, `agent_runner`, `orchestrator`, `aureon.ollama_config`, and `aureon.autonomous.aureon_internal_coding_workforce`. `inhouse_ai` stays excluded. Organism reachable is 0.",
            "`body_call` refuses `swarm/capability_grid.py` `build_lane`. `build_lane(\"fintech\")` imports `aureon.accounting`, and that package init reaches `aureon.autonomous.aureon_internal_coding_workforce`, which imports `aureon.inhouse_ai` and `aureon.ollama_config`. Swarm's other entry points stay. Swarm reachable is 24.",
            "The other swarm tools use fixtures from the swarm tests or fixed example arguments. Classes that need nested agent instances stay off the constructor allowlist: Cluster, Company, Zone, FleadhCompany, VisitorAgent, and WorkerAgent. Name-blocked `run_` entry points stay refused. Properties such as SwarmAgent.purity are not given tools because the worker calls methods. `validate_seat_receipt` stays reachable through `body_call` and is not a second tool: the public result cap would drop receipt fields before another call.",
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
