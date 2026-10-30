"""Write mcp/aureon_public/COVERAGE_PLAN.md from the pinned inventory.

Every count comes from docs/mcp/inventory.json and public_entry_refusal.
The file is refused when its sha256 is not INVENTORY_SHA256.

    env -u PYTHONPATH PYTHONPATH=mcp python3.12 -m aureon_public.coverage_plan --check
    env -u PYTHONPATH PYTHONPATH=mcp python3.12 -m aureon_public.coverage_plan --write
"""

from __future__ import annotations

import argparse
import json
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


def tested_keys() -> set[tuple[str, str]]:
    """Entry points a public tool calls and a test exercises."""

    from aureon_public.call_sweep import _tested_stage1_tools
    from aureon_public.stage2_layer import TESTED

    return set(_tested_stage1_tools()) | set(TESTED)


def _tested_counts(loaded: list[dict]) -> dict[str, int]:
    """Reachable public entry points that a tool calls. A refused point is not tested."""

    wanted = tested_keys()
    counts: dict[str, int] = defaultdict(int)
    seen: set[tuple[str, str]] = set()
    for row in loaded:
        if row["server"] != "public" or row["kind"] not in {"function", "method"}:
            continue
        key = (str(row["module"]), str(row["symbol"]))
        if key in seen or key not in wanted:
            continue
        seen.add(key)
        if public_entry_refusal(row) is None:
            counts[str(row["package"])] += 1
    return counts


def plan_rows() -> list[dict]:
    """One row per package. Counts are the pinned inventory and the current guard."""

    loaded, depth = _rows()
    by_package: dict[str, list[dict]] = defaultdict(list)
    for row in loaded:
        by_package[row["package"]].append(row)
    opened = _opened_by_allowlist(loaded)
    tested = _tested_counts(loaded)
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
                "refused": counted["public_entry_points"] - counted["reachable"],
                "stage": stage,
                "tested": tested.get(package, 0),
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


def _read_json(name: str) -> dict:
    path = repo_root() / "measured" / name
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _stage2_lines() -> list[str]:
    """What this run opened, refused, and left without a tool."""

    from aureon_public.stage2_arguments import NOT_A_TOOL

    imports = _read_json("aureon_public_stage2_imports.json")
    calls = _read_json("aureon_public_call_sweep.json")
    lines = [
        "Stage 2 tools call through `dispatch`. The inputs are the tests and committed files named on each tool. `atn` stays excluded because its modules load an HTTP client. `conversion` has no public function or method and stays excluded. The constructor allowlist, the `__post_init__` refusal, the `AUREON_PUBLIC_SWEEP` start refusal, and the pin check are unchanged.",
        "Import refusals:",
    ]
    modules = [row for row in imports.get("modules") or [] if isinstance(row, dict) and row.get("refused")]
    if not modules:
        lines.append("- none recorded")
    for row in sorted(modules, key=lambda item: str(item.get("module"))):
        lines.append(
            f"- `{row.get('module')}`: {row.get('refusal') or 'module import loads an adapter or http client'}"
        )
    lines.append("Import errors that are not refusals:")
    errors = [
        row
        for row in imports.get("modules") or []
        if isinstance(row, dict) and row.get("error") and not row.get("refused")
    ]
    if not errors:
        lines.append("- none recorded")
    for row in sorted(errors, key=lambda item: str(item.get("module"))):
        lines.append(f"- `{row.get('module')}`: {row.get('error')}")
    lines.append("Call refusals from the sweep:")
    entries = [
        row
        for row in calls.get("entries") or []
        if isinstance(row, dict) and row.get("refused")
    ]
    if not entries:
        lines.append("- none recorded")
    for row in sorted(entries, key=lambda item: (str(item.get("module")), str(item.get("symbol")))):
        extra = []
        for attempt in row.get("attempts") or []:
            if isinstance(attempt, dict) and attempt.get("process"):
                extra.append("The same call started a process. The sweep blocked it.")
            if isinstance(attempt, dict) and attempt.get("writes"):
                extra.append("The same call wrote outside the sandbox. The sweep blocked it.")
        suffix = (". " + " ".join(dict.fromkeys(extra))) if extra else ""
        lines.append(
            f"- `{row.get('module')}` `{row.get('symbol')}`: {row.get('refusal') or 'call loads a banned chain or opens a connection'}{suffix}"
        )
    from aureon_public.body import _ENTRY_REFUSAL, _UNTESTED_STAGE2, lookup, public_entry_refusal

    lines.append(
        "These five were reachable and had no tool. `body_call` and `dispatch` refuse them. The constructor allowlist is unchanged."
    )
    for key in sorted(item for item, reason in _ENTRY_REFUSAL.items() if reason == _UNTESTED_STAGE2):
        lines.append(f"- `{key[0]}` `{key[1]}`: {_UNTESTED_STAGE2}. {NOT_A_TOOL[key]}")
    still = []
    for key in sorted(NOT_A_TOOL):
        row = lookup(key[0], key[1])
        if row is not None and public_entry_refusal(row) is None:
            still.append(key)
    if still:
        lines.append("These stage-2 entry points are still reachable and are not tools:")
        for key in still:
            lines.append(f"- `{key[0]}` `{key[1]}`. {NOT_A_TOOL[key]}")
    return lines


def _public_keys() -> dict[int, list[tuple[str, str]]]:
    """Reachable public entry points, by coverage-plan stage."""

    from aureon_public.body import _inventory, _plan_stage, public_entry_refusal

    seen: set[tuple[str, str]] = set()
    found: dict[int, list[tuple[str, str]]] = defaultdict(list)
    rows, _index = _inventory()
    for row in rows:
        if row["server"] != "public" or row["kind"] not in {"function", "method"}:
            continue
        key = (str(row["module"]), str(row["symbol"]))
        if key in seen:
            continue
        seen.add(key)
        if public_entry_refusal(row) is not None:
            continue
        found[_plan_stage(str(row["package"]))].append(key)
    for keys in found.values():
        keys.sort()
    return found


def _reconciliation_lines() -> list[str]:
    """How reachable and tested moved from main c1ae468d to this tree.

    Main recorded 85 reachable: stage 1 was 39 and stage 2 was 46. Stage 1
    tested 29 entry points and stage 2 tested none. A tool does not create a
    new reachable row.
    """

    from aureon_public.body import _ENTRY_REFUSAL, _UNTESTED_STAGE2
    from aureon_public.call_sweep import _tested_stage1_tools
    from aureon_public.stage2_layer import TESTED

    reachable = _public_keys()
    stage1_tested = sorted(_tested_stage1_tools())
    stage2_tested = sorted(TESTED)
    stage1_now = set(reachable.get(1, []))
    stage2_now = set(reachable.get(2, []))
    dropped = [key for key in stage1_tested if key not in stage1_now]
    untested_stage1 = [key for key in reachable.get(1, []) if key not in set(stage1_tested)]
    lines = [
        "## Count reconciliation",
        "",
        "Main `c1ae468d` recorded reachable 85. Stage 1 was 39 (alignment 11, generated 4, swarm 24). Stage 2 was 46 (atn 0, cognition 1, conversion 0, decoders 5, evaluation 7, gates 3, observer 29, s51 1). 39 + 46 = 85. Tested on that main was the 29 stage-1 tool entry points below. Stage 2 tested was 0. Registering a tool does not add a reachable row. The tool calls an entry point that was already reachable.",
        f"Stage 1 reachable now: {len(stage1_now)}. Stage 2 reachable now: {len(stage2_now)}. {len(stage1_now)} + {len(stage2_now)} = {len(stage1_now) + len(stage2_now)}.",
        f"Stage 1 tested now: {len(stage1_tested)}. Stage 2 tested now: {len(stage2_tested)}. {len(stage1_tested)} + {len(stage2_tested)} = {len(stage1_tested) + len(stage2_tested)}.",
        "Every stage-1 entry point that was tested on main is still tested. None dropped out:",
    ]
    if dropped:
        lines.append("Stage-1 tested entry points that are no longer reachable:")
        for module, symbol in dropped:
            lines.append(f"- `{module}` `{symbol}`")
    else:
        lines.append("No stage-1 tested entry point dropped out.")
    for module, symbol in stage1_tested:
        lines.append(f"- `{module}` `{symbol}`")
    lines.append(
        "Stage 1 still has reachable entry points that were not tested on main and are not tested now. This run did not remove them from tested, because they were not tested:"
    )
    for module, symbol in untested_stage1:
        lines.append(f"- `{module}` `{symbol}`")
    lines.append(
        "Stage 2 reachable fell by 7, from 46 to 39. The call sweep refused `self_coder_report`. Five reachable entry points had no tool. `log_blocked_fallback` would write a fallback log for an event that did not happen, so `body_call` refuses it."
    )
    calls = _read_json("aureon_public_call_sweep.json")
    self_coder = next(
        (
            row
            for row in calls.get("entries") or []
            if isinstance(row, dict)
            and row.get("module") == "evaluation/measured_proof.py"
            and row.get("symbol") == "self_coder_report"
        ),
        None,
    )
    if isinstance(self_coder, dict):
        lines.append(
            f"- `evaluation/measured_proof.py` `self_coder_report`: {self_coder.get('refusal') or 'refused by the call sweep'}."
        )
    else:
        lines.append(
            "- `evaluation/measured_proof.py` `self_coder_report`: refused by the call sweep. The record names the reason."
        )
    for key in sorted(item for item, reason in _ENTRY_REFUSAL.items() if reason == _UNTESTED_STAGE2):
        lines.append(f"- `{key[0]}` `{key[1]}`: {_UNTESTED_STAGE2}.")
    lines.append(
        "- `observer/live_data_policy.py` `log_blocked_fallback`: "
        "fallback log is not emitted for an event that did not happen."
    )
    total = len(stage1_now) + len(stage2_now)
    tested_total = len(stage1_tested) + len(stage2_tested)
    if (
        len(stage1_now) != 39
        or len(stage2_now) != 39
        or len(stage1_tested) != 29
        or len(stage2_tested) != 39
        or dropped
        or total != 78
        or tested_total != 68
    ):
        raise RuntimeError(
            "count reconciliation drifted: "
            f"stage1 {len(stage1_now)} tested {len(stage1_tested)}; "
            f"stage2 {len(stage2_now)} tested {len(stage2_tested)}; "
            f"dropped {dropped}"
        )
    lines.append(
        "Those seven are the only entry points that left the reachable set since main `c1ae468d`. "
        "85 - 7 = 78. Stage 2's remaining 39 reachable entry points are the 39 tested tools. "
        "39 + 39 = 78 reachable. 29 + 39 = 68 tested."
    )
    return lines


def render() -> str:
    rows = plan_rows()
    listed = sum(row["listed"] for row in rows)
    public = sum(row["public_entry_points"] for row in rows)
    reachable = sum(row["reachable"] for row in rows)
    tested = sum(row["tested"] for row in rows)
    refused = sum(row["refused"] for row in rows)
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
        "bash measured/aureon_public_protocol_run.sh",
        "env -u PYTHONPATH /tmp/aureon-public-venv/bin/python -m pytest tests/test_aureon_public_mcp.py tests/test_aureon_body.py tests/bio/test_mcp_interior_attribution.py tests/bio/test_mcp_membrane.py tests/bio/test_mcp_transport.py tests/test_aureon_public_alignment.py tests/test_aureon_public_stage1.py tests/test_aureon_public_stage2.py tests/test_aureon_public_protocol.py --tb=line",
        "```",
        "",
        "That pytest command is the gate. It runs in `/tmp/aureon-public-venv`, the venv `measured/aureon_public_stage1_run.sh` creates (`VENV` overrides the path). The file list is `tests/test_aureon_public_mcp.py`, `tests/test_aureon_body.py`, `tests/bio/test_mcp_interior_attribution.py`, `tests/bio/test_mcp_membrane.py`, `tests/bio/test_mcp_transport.py`, `tests/test_aureon_public_alignment.py`, `tests/test_aureon_public_stage1.py`, `tests/test_aureon_public_stage2.py`, and `tests/test_aureon_public_protocol.py`. `tests/test_async_socket_isolation.py` is not in the gate list. It imports `pytest_socket`, and `mcp/aureon_public/test-requirements.txt` does not install that plugin.",
        "",
        "`--write` rewrites this file from the same function. `measured/aureon_public_stage1_run.sh` installs `mcp/aureon_public/requirements.txt` and `mcp/aureon_public/test-requirements.txt`, then rewrites both `measured/aureon_public_alignment.json` and `measured/aureon_public_stage1.json`. It writes those two files under a temp directory first and copies them into `measured/` only after both stamps have finished. `measurement_stamp` raises `RuntimeError` when `git status --porcelain` is not empty, so the second stamp must not see the first file. `test-requirements.txt` is the test install: pytest, pytest-timeout, flask, pandas, and scipy. It is not the public server runtime. `measured/aureon_public_stage2_sweep.sh` and `measured/aureon_public_call_sweep.sh` copy the checkout with `cp -a` under an ordinary temp parent, place fake `NEXUS-LIVE-FEED-` and `Aureon-Trading--Project-Sero` checkouts beside that copy, block sockets, and rewrite their measured records. Each sweep record names the pin, the `aureon/` tree hash beside that pin, the `aureon_source` kind, and that temp parent. `measured/aureon_public_protocol_run.sh` starts this server over stdio and over Streamable HTTP bound to `127.0.0.1`, with `AUREON_PUBLIC_REQUIRE_PIN=1`. An MCP SDK 1.30.0 client calls `tools/list`, `resources/list`, `prompts/list`, and one `tools/call` (`alignment_consonance_read` with ratio 1.0). The raw pages are `measured/aureon_public_protocol.json`. These measured records name `code_commit`, the parent of the commit that contains the record file. A record cannot name the commit that adds the file.",
        "",
        f"Listed symbols: {listed}. Public entry points: {public}. Reachable now: {reachable}. Tested: {tested}. Refused: {refused}. The plan on main recorded 879 reachable. An earlier draft head of the stage-1 PR recorded 89 reachable, before the call sweep. Methods open because a constructor is allowlisted: {opened}. The refused-imports fence is unchanged.",
        "Reachable means `public_entry_refusal` returns None. Tested means a public tool calls that entry point and `tests/test_aureon_public_stage1.py` or `tests/test_aureon_public_stage2.py` exercises the tool. Refused means a public entry point the server will not run. Plan stages 3 and 4 stay closed. The call sweep calls every entry point that was still reachable, with no arguments, and calls each stage-2 entry point again with the real arguments in `stage2_arguments.py`. It refuses one that opens a connection, starts a process, writes outside the sandbox, or loads queen, miner, swarm_motion, inhouse_ai, ollama_config, or an HTTP client. `get_unified_directive` is refused that way. It does not build the queen and miner bridges.",
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
        "Stage 2 is open. A stage-2 module whose import loads an adapter or an HTTP client, starts a process, or writes outside the sandbox is refused. A stage-2 entry point is refused when the no-argument call or a real-argument call does any of those, or does not finish. `atn` stays excluded. `conversion` has no public function or method and stays excluded.",
        "",
        "## Counts",
        "",
        "| Stage | Package | Listed | Public entry points | Reachable now | Tested | Refused |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['stage']} | {row['package']} | {row['listed']} | {row['public_entry_points']} | {row['reachable']} | {row['tested']} | {row['refused']} |"
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
            *_stage2_lines(),
            *_reconciliation_lines(),
            "",
            "The pin stays `8aa6a2d971cc529484e2a5e261e28afafab4e4f4`. The alignment modules at this checkout match that pin, so the tools do not need a newer commit. `GUARD_BLOB` and `INVENTORY_SHA256` are unchanged.",
            "",
            "## MCP SDK",
            "",
            "This server imports `FastMCP` from `mcp.server.fastmcp` and passes `host`, `port`, and `streamable_http_path` to that constructor. The requirement is `mcp==1.30.0,<2` in `mcp/aureon_public/requirements.txt` and `mcp/pyproject.toml`. That specifier matches 1.30.0 and excludes every 2.x release. Migration to SDK v2 is a later decision.",
            "",
            "The claim that official Python SDK v2 renamed `FastMCP` to `MCPServer` was checked against the published package and the v2 source. The claim is true.",
            "",
            "- PyPI project `mcp`: `info.version` is 2.3.0. The newest 1.x release is 1.30.0. https://pypi.org/pypi/mcp/json",
            "- Release v2.0.0, published 28 July 2026, says `FastMCP` is now `MCPServer`, v1.x is maintenance-only on branch `v1.x`, and a project that is not migrating should keep a `<2` upper bound, for example `mcp>=1.28,<2`. https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.0.0",
            "- Migration guide, section `FastMCP` renamed to `MCPServer`: `from mcp.server.fastmcp import FastMCP` becomes `from mcp.server.mcpserver import MCPServer`. https://py.sdk.modelcontextprotocol.io/v2/migration/",
            "- Tag v2.0.0 and tag v2.3.0 `src/mcp/server/__init__.py` export `MCPServer` from `.mcpserver`. https://github.com/modelcontextprotocol/python-sdk/blob/v2.3.0/src/mcp/server/__init__.py",
            "- Tag v2.3.0 `src/mcp/server/mcpserver/server.py` defines `class MCPServer`. `MCPServer.__init__` takes no `host`, `port`, or `streamable_http_path`. Those arguments are on `run(transport=\"streamable-http\")`. The default name when none is passed is `mcp-server`. `instructions` is no longer the second positional parameter. https://github.com/modelcontextprotocol/python-sdk/blob/v2.3.0/src/mcp/server/mcpserver/server.py",
            "- `src/mcp/server/fastmcp/__init__.py` on tag v2.3.0 is not published. The raw URL returns HTTP 404. https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/v2.3.0/src/mcp/server/fastmcp/__init__.py",
            "- v1 documentation stays at https://py.sdk.modelcontextprotocol.io/v1/",
            "",
            "The same v2.0.0 notes also replace `ClientSession` plus the transport clients with `Client`, and the v2.3.0 constructor no longer accepts `host`, `port`, or `streamable_http_path`. This server still passes those three to `FastMCP`, and the measured client still uses `ClientSession`. Staying on 1.30.0 keeps that call shape.",
            "",
            "The protocol proof is the stdio session and the Streamable HTTP session bound to `127.0.0.1`. A Hugging Face Space scaffold and remote HTTP auth stay for a later PR. Stage 2 is this run.",
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
