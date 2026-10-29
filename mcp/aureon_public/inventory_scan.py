"""Scan public modules, classes, and functions for the full-body plan.

The scan is AST only. It does not import aureon and it does not call anything.
"""

from __future__ import annotations

import ast
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

STAGE = {
    "harmonic": 1,
    "cognition": 2,
    "queen": 2,
    "swarm": 2,
    "swarm_motion": 2,
    "gates": 2,
    "governance": 2,
    "alignment": 2,
    "observer": 2,
    "organism": 3,
    "bio": 3,
    "evaluation": 3,
    "vault": 3,
    "identity": 3,
    "data_feeds": 4,
    "atn": 4,
    "decoders": 4,
    "search": 4,
    "portals": 4,
    "monitors": 4,
    "analytics": 4,
    "trading": 5,
    "exchanges": 5,
    "bots": 5,
    "bots_intelligence": 5,
    "bridges": 5,
    "scanners": 5,
    "strategies": 5,
    "portfolio": 5,
    "accounting": 5,
    "conversion": 5,
    "autonomous": 6,
    "code_architect": 6,
    "inhouse_ai": 6,
    "operator": 6,
    "launch": 6,
    "command_centers": 6,
    "connectors": 6,
    "saas": 6,
    "miner": 6,
    "generated": 6,
}

OPERATOR_PACKAGES = {
    "trading",
    "exchanges",
    "bots",
    "bots_intelligence",
    "bridges",
    "scanners",
    "strategies",
    "portfolio",
    "accounting",
    "conversion",
    "autonomous",
    "code_architect",
    "inhouse_ai",
    "operator",
    "launch",
    "command_centers",
    "connectors",
    "saas",
    "miner",
    "identity",
    "vault",
}

ORDER_RE = re.compile(
    r"place_order|create_order|submit_order|live_order|market_order|limit_order|send_order",
    re.I,
)
LAUNCH_RE = re.compile(
    r"^(main|start_|stop_|launch|serve|run_server|boot|demo)$|serve_forever|continuous|create_web",
    re.I,
)
WRITE_RE = re.compile(r"write_text|write_bytes|\.write\(|mkdir|open\([^)]*['\"]w", re.I)
KEY_RE = re.compile(
    r"api_key|secret|password|credential|dotenv|owner_address|master_key|from_env|private_key|read_identity",
    re.I,
)
FETCH_RE = re.compile(r"^(fetch_|download_|get_live)|requests\.|urlopen|httpx\.", re.I)


def stage_for(pkg: str, rel: str) -> int:
    low = rel.lower()
    if pkg == "core":
        if any(token in low for token in ("organism", "memory", "thought_bus")):
            return 3
        if any(token in low for token in ("hnc", "lambda", "field", "harmonic", "canonical")):
            return 1
        return 6
    if pkg == "utils":
        return 1 if any(token in low for token in ("auris", "queen_hive", "queen")) else 6
    if pkg == "wisdom":
        return 1 if "qgita" in low else 6
    return STAGE.get(pkg, 6)


def safety(pkg: str, name: str, src: str, stage: int) -> tuple[str, str]:
    blob = name + "\n" + src[:1500]
    if pkg == "identity" or (pkg == "vault" and KEY_RE.search(blob)):
        return "operator", "personal or key material; operator only; never returned"
    if ORDER_RE.search(blob) or pkg in {
        "trading",
        "exchanges",
        "bots",
        "bots_intelligence",
        "bridges",
        "scanners",
    }:
        return "operator", "order-capable path; live_orders refused; no live send"
    if LAUNCH_RE.search(name) or "serve_forever" in src[:800] or "while True" in src[:800]:
        return "operator", "process, loop, or UI start; own flag; status and stop"
    if WRITE_RE.search(src[:800]):
        return "operator", "writes; operator state root only, not the repo"
    if KEY_RE.search(blob):
        return "operator", "reads keys from env only; never logged or returned"
    if FETCH_RE.search(blob):
        return "public", "live public fetch allowed; source label and timeout"
    if pkg in OPERATOR_PACKAGES and stage >= 5:
        return "operator", "package is operator-scoped; no public import"
    server, text = "public", "runs from inputs or committed files; no keys and no repo write"
    return _honest_effect(name, server, text)


def _honest_effect(name: str, server: str, text: str) -> tuple[str, str]:
    """Names that write or start are not 'no repo write'."""

    leaf = name.split(".")[-1]
    if re.match(r"^(write_|save_|export_|dump_)", leaf, re.I) or leaf.lower() == "start":
        if "no repo write" in text:
            return server, "write or process start; the public server refuses it"
    return server, text


def required_count(node: ast.AST) -> int:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return 0
    args = [item for item in node.args.args if item.arg not in {"self", "cls"}]
    required = len(args) - len(node.args.defaults)
    for default in node.args.kw_defaults:
        if default is None:
            required += 1
    if node.args.vararg or node.args.kwarg:
        return required
    return max(required, 0)


def _snippet(lines: list[str], node: ast.AST) -> str:
    start = getattr(node, "lineno", 1) - 1
    return "\n".join(lines[start : start + 40])


def _scan_tree(pkg: str, rel: str, text: str, server_default: str | None = None) -> list[dict]:
    rows: list[dict] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        stage = 5 if pkg == "unified_margin_trader" else stage_for(pkg, rel)
        rows.append(
            {
                "package": pkg,
                "module": rel,
                "symbol": "<syntax>",
                "kind": "module",
                "server": "operator",
                "form": "resource",
                "safety": "file does not parse",
                "stage": stage,
                "required": 0,
            }
        )
        return rows
    stage = 5 if pkg == "unified_margin_trader" else stage_for(pkg, rel)
    lines = text.splitlines()
    module_server = server_default or "operator" if pkg == "unified_margin_trader" else safety(pkg, Path(rel).stem, "", stage)[0]
    module_safety = (
        "order-capable tree; live_orders refused"
        if pkg == "unified_margin_trader"
        else "module surface; import is lazy and blob-checked when the file is the checkout"
    )
    rows.append(
        {
            "package": pkg,
            "module": rel,
            "symbol": Path(rel).stem,
            "kind": "module",
            "server": module_server,
            "form": "resource",
            "safety": module_safety,
            "stage": stage,
            "required": 0,
        }
    )
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            server, safe = (
                ("operator", "live_orders refused; no live send")
                if pkg == "unified_margin_trader"
                else safety(pkg, node.name, _snippet(lines, node), stage)
            )
            rows.append(
                {
                    "package": pkg,
                    "module": rel,
                    "symbol": node.name,
                    "kind": "class",
                    "server": server,
                    "form": "resource",
                    "safety": safe,
                    "stage": stage,
                    "required": 0,
                }
            )
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and not item.name.startswith("_"):
                    server, safe = (
                        ("operator", "live_orders refused; no live send")
                        if pkg == "unified_margin_trader"
                        else safety(pkg, item.name, _snippet(lines, item), stage)
                    )
                    rows.append(
                        {
                            "package": pkg,
                            "module": rel,
                            "symbol": f"{node.name}.{item.name}",
                            "kind": "method",
                            "server": server,
                            "form": "tool",
                            "safety": safe,
                            "stage": stage,
                            "required": required_count(item),
                            "async": isinstance(item, ast.AsyncFunctionDef),
                        }
                    )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            server, safe = (
                ("operator", "live_orders refused; no live send")
                if pkg == "unified_margin_trader"
                else safety(pkg, node.name, _snippet(lines, node), stage)
            )
            rows.append(
                {
                    "package": pkg,
                    "module": rel,
                    "symbol": node.name,
                    "kind": "function",
                    "server": server,
                    "form": "tool",
                    "safety": safe,
                    "stage": stage,
                    "required": required_count(node),
                    "async": isinstance(node, ast.AsyncFunctionDef),
                }
            )
    return rows


def scan(root: Path) -> list[dict]:
    rows: list[dict] = []
    aureon = root / "aureon"
    for pkg_path in sorted(path for path in aureon.iterdir() if (path / "__init__.py").is_file()):
        for path in sorted(pkg_path.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            rel = str(path.relative_to(aureon))
            text = path.read_text(encoding="utf-8", errors="replace")
            rows.extend(_scan_tree(pkg_path.name, rel, text))
    umt = root / "unified_margin_trader"
    for path in sorted(umt.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        rows.extend(_scan_tree("unified_margin_trader", str(path.relative_to(root)), text, "operator"))
    return rows


def render_plan(rows: list[dict]) -> str:
    lines = [
        "# Full body MCP plan",
        "",
        "This is the stage-0 inventory of every public module, class, function, and method in the 54 `aureon` packages plus `unified_margin_trader`. A name that starts with `_` is not listed.",
        "",
        "A layer is at full depth only where a measured call runs that entry point. Listing it here, or reading its signature, is not depth. A helper call is not that layer's cognition. The depth table in each later stage counts calls, not rows.",
        "",
        "MCP lets outside models call Aureon's tools. No outside model or API becomes Aureon's reasoning. The cognition runs in Aureon's own code.",
        "",
        "Public (`aureon-public`) is for entry points that run without keys, personal data, or writes. Live public fetches are allowed there, with a source label and a timeout. Operator (`aureon-operator`) is stdio only, off unless `AUREON_OPERATOR_MCP=1`. It may read keys from the environment and must not log or return them. It writes only under a configurable state root. Live orders return `live_orders: refused`. Process starters are start, status, and stop tools, each behind its own flag.",
        "",
        "Functions and methods are tools. Modules and classes are resources (the surface, not a constructed instance). The running servers address them through `body_call` and `body_surface` so the catalog stays one pair of tools instead of nineteen thousand registrations. The form column is the kind of call. `body_call` runs the real function. `body_surface` does not.",
        "",
        "`repo_root()` and `aureon_source()` raise `FileNotFoundError` when there is no checkout. The servers need that checkout.",
        "",
        "Any checkout file loaded beside the pin must pass the git blob check in `mcp/aureon_public/pin_blob.py` before it is executed. A file whose blob is not the blob at pin `a00f744d` is not imported.",
        "",
        "HOLD stays explicit: trade readiness, the Auris-to-Lambda link, QGITA detection and false-alarm rates, Schumann f0, and HumanEval not run. `consciousness_*` keys are dropped. The pin and `AUREON_PUBLIC_REQUIRE_PIN` stay. Space entry points call `enforce_public_pin()`.",
        "",
        "## Stages",
        "",
        "1. HNC, harmonic core, Auris, and QGITA.",
        "2. cognition, queen, swarm, swarm_motion, gates, governance, alignment, observer.",
        "3. organism, bio, evaluation, memory and vault, identity readers.",
        "4. data_feeds, atn, decoders, search, portals, monitors, analytics.",
        "5. trading, exchanges, bots, bots_intelligence, bridges, scanners, strategies, portfolio, accounting, unified_margin_trader, conversion. Operator server. Live orders refused.",
        "6. autonomous, code_architect, inhouse_ai, operator, launch, command_centers, connectors, saas, miner, generated, and the rest.",
        "7. Space entry points and MCP registry packaging.",
        "",
        "## Counts",
        "",
        "| Package | Symbols | Public | Operator | Stage |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    by_pkg: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_pkg[row["package"]].append(row)
    for pkg in sorted(by_pkg):
        items = by_pkg[pkg]
        public = sum(1 for row in items if row["server"] == "public")
        operator = sum(1 for row in items if row["server"] == "operator")
        stages = ",".join(str(item) for item in sorted({row["stage"] for row in items}))
        lines.append(f"| {pkg} | {len(items)} | {public} | {operator} | {stages} |")
    lines.extend(
        [
            "",
            f"Total symbols: {len(rows)}. Packages: {len(by_pkg)}.",
            "",
            "Stage totals: "
            + ", ".join(f"{stage}={count}" for stage, count in sorted(Counter(row["stage"] for row in rows).items()))
            + ".",
            "",
            "Server totals: "
            + ", ".join(f"{server}={count}" for server, count in sorted(Counter(row["server"] for row in rows).items()))
            + ".",
            "",
            "## Every public module, class, and function",
            "",
            "Columns: stage, server, form, kind, module, symbol, safety.",
            "",
            "| Stage | Server | Form | Kind | Module | Symbol | Safety |",
            "| ---: | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        safety_text = row["safety"].replace("|", "/")
        symbol = row["symbol"].replace("|", "/")
        lines.append(
            f"| {row['stage']} | {row['server']} | {row['form']} | {row['kind']} | `{row['module']}` | `{symbol}` | {safety_text} |"
        )
    return "\n".join(lines) + "\n"


def write_outputs(root: Path) -> tuple[int, Path, Path]:
    rows = scan(root)
    plan = root / "docs" / "mcp" / "FULL_BODY_PLAN.md"
    inventory = root / "docs" / "mcp" / "inventory.json"
    plan.parent.mkdir(parents=True, exist_ok=True)
    plan.write_text(render_plan(rows), encoding="utf-8")
    inventory.write_text(json.dumps(rows, separators=(",", ":")), encoding="utf-8")
    return len(rows), plan, inventory
