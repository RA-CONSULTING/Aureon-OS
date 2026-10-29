"""Address every inventoried entry point without registering thousands of tools.

`body_call` runs a real function or method. `body_surface` reads a module or
class and does not construct it. Depth is the count of calls, not the count
of rows in the plan. A helper label is not used here.
"""

from __future__ import annotations

import ast
import importlib
import importlib.util
import inspect
import json
import os
import re
import threading
from datetime import date
from pathlib import Path
from typing import Any

from aureon_public.guard_loader import PINNED_COMMIT, apply_space_guard, aureon_source
from aureon_public.paths import repo_root
from aureon_public.pin_blob import load_checkout_module
from aureon_public.quiet import quiet
from aureon_public.tools import _dumps

# Stages 1-6 raise this as each stage commit lands. Stage 7 is packaging.
ENABLED_THROUGH = 6

_UNSAFE_NAME = re.compile(
    r"(run_|start_|stop_|launch_|serve|main$|^demo$|create_app|activate_|connect_|"
    r"publish_|write_|save_|download_|fetch_|notify_|reset_|discover_|simulate_|"
    r"audit_|ingest_|record_|wire_|print_|benchmark|forever|continuous|^analyze|demo_)",
    re.I,
)
_SKIP_WORD = re.compile(
    r"price|live_|kraken|order|exchange|network|socket|download|schumann|biometric|trade|wallet|secret|"
    r"thought_bus|redis|postgres|sqlite|calibration|^evaluate_|^observe$|"
    r"feed_hub|ws_feed|space_weather|news_signal|coordinator|seer_vision|lyra",
    re.I,
)
_UNSAFE_SOURCE = (
    "requests",
    "urlopen",
    "httpx",
    "socket",
    "subprocess",
    "write_text",
    "write_bytes",
    "serve_forever",
    "SystemExit",
    "os._exit",
    "open(",
)

_BLOCKED = {
    "trading",
    "exchanges",
    "bots",
    "bots_intelligence",
    "bridges",
    "scanners",
    "unified_margin_trader",
}

_AURIS = {
    "QueenHiveMind.read_auris_nodes": "nine nodes",
    "QueenHiveMind.get_auris_coherence": "coherence evaluator",
    "evaluate_auris_nodes": "evaluation harness over brain proof, not the nine-node reader and not the conjecture",
    "get_auris_voice_filter": "harmonic AurisVoiceFilter",
    "reset_auris_voice_filter": "harmonic AurisVoiceFilter",
    "AurisVoiceFilter": "harmonic AurisVoiceFilter",
    "AurisValidator": "validator",
}

_ROWS: list[dict[str, Any]] | None = None
_INDEX: dict[tuple[str, str], dict[str, Any]] | None = None


def enabled_stage() -> int:
    return ENABLED_THROUGH


def _inventory() -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    global _ROWS, _INDEX
    if _ROWS is None or _INDEX is None:
        path = repo_root() / "docs" / "mcp" / "inventory.json"
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, list):
            raise TypeError("inventory.json")
        index: dict[tuple[str, str], dict[str, Any]] = {}
        for row in loaded:
            index.setdefault((row["module"], row["symbol"]), row)
        _ROWS = loaded
        _INDEX = index
    return _ROWS, _INDEX


def lookup(module: str, symbol: str) -> dict[str, Any] | None:
    _, index = _inventory()
    return index.get((module, symbol))


def file_for(module: str) -> Path:
    root = repo_root()
    if module.startswith("unified_margin_trader/"):
        return root / module
    return root / "aureon" / module


def dotted_for(module: str) -> str:
    if module.startswith("unified_margin_trader/"):
        relative = module
    else:
        relative = "aureon/" + module
    return ".".join(Path(relative).with_suffix("").parts)


def _outside(origin: Path, root: Path) -> bool:
    resolved = origin.resolve()
    root_resolved = root.resolve()
    return resolved != root_resolved and root_resolved not in resolved.parents


def _plain(value: Any, depth: int = 0) -> Any:
    if depth > 4:
        return type(value).__name__
    if value is None or isinstance(value, (str, int, float, bool)):
        if isinstance(value, float) and value != value:
            return None
        if isinstance(value, str):
            return value[:500]
        return value
    if isinstance(value, dict):
        return {str(key): _plain(item, depth + 1) for key, item in list(value.items())[:30]}
    if isinstance(value, (list, tuple)):
        return [_plain(item, depth + 1) for item in list(value)[:30]]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        try:
            return _plain(value.to_dict(), depth + 1)
        except Exception:
            pass
    if hasattr(value, "__dict__") and not isinstance(value, type):
        fields = {key: item for key, item in vars(value).items() if not str(key).startswith("_")}
        return {"type": type(value).__name__, "fields": _plain(fields, depth + 1)}
    return {"type": type(value).__name__}


def _result(payload: dict[str, Any]) -> str:
    payload.setdefault("provenance", "cited")
    text = _dumps(payload)
    if len(text) > 8000:
        payload = {
            "called": payload.get("called"),
            "label": payload.get("label"),
            "provenance": payload.get("provenance", "cited"),
            "status": payload.get("status"),
            "truncated": True,
        }
        text = _dumps(payload)
    return text


def _unavailable(reason: str, **extra: Any) -> str:
    body = {"label": "cited. Not called.", "reason": reason, "status": "unavailable"}
    body.update(extra)
    return _result(body)


def _refused(reason: str) -> str:
    return _unavailable(reason, live_orders="refused")


def _function_source(module: str, symbol: str) -> str:
    path = file_for(module)
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(text)
    except (OSError, SyntaxError):
        return ""
    lines = text.splitlines()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol:
            end = node.end_lineno or node.lineno
            return "\n".join(lines[node.lineno - 1 : end])
    return ""


def _quiet_source(module: str, symbol: str) -> bool:
    source = _function_source(module, symbol)
    if not source:
        return False
    return not any(token in source for token in _UNSAFE_SOURCE)


def _coerce(fn: Any, kwargs: dict[str, Any]) -> dict[str, Any]:
    try:
        signature = inspect.signature(fn)
    except (TypeError, ValueError):
        return kwargs
    coerced = dict(kwargs)
    for name, value in list(coerced.items()):
        param = signature.parameters.get(name)
        if param is None:
            continue
        annotation = param.annotation
        origin = getattr(annotation, "__origin__", None)
        name_of = annotation if isinstance(annotation, str) else getattr(annotation, "__name__", "")
        if (annotation is date or name_of == "date" or str(name_of).endswith("date")) and isinstance(value, str):
            coerced[name] = date.fromisoformat(value)
        elif (annotation is frozenset or origin is frozenset) and isinstance(value, list):
            coerced[name] = frozenset(value)
    return coerced


def _required_missing(fn: Any, kwargs: dict[str, Any]) -> str | None:
    try:
        signature = inspect.signature(fn)
    except (TypeError, ValueError):
        return None
    try:
        signature.bind(**kwargs)
    except TypeError as exc:
        return str(exc)
    return None


def _call_with_timeout(fn: Any, kwargs: dict[str, Any], timeout: float) -> tuple[str, Any]:
    if inspect.iscoroutinefunction(fn):
        return "async", "async entry point is not awaited"
    box: dict[str, Any] = {}

    def runner() -> None:
        try:
            box["value"] = fn(**kwargs)
        except BaseException as exc:  # noqa: BLE001 - the tool must return the failure
            box["error"] = exc

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        return "timeout", f"exceeded {timeout:.0f}s"
    if "error" in box:
        exc = box["error"]
        if isinstance(exc, SystemExit):
            return "error", "SystemExit"
        return "error", f"{type(exc).__name__}: {exc}"[:240]
    return "ok", box.get("value")


def _import_checked(module: str) -> tuple[Any | None, str | None]:
    apply_space_guard()
    from aureon_public.layers import _load_phenolic_fingerprint

    _load_phenolic_fingerprint()
    root = repo_root()
    path = file_for(module)
    dotted = dotted_for(module)
    spec = importlib.util.find_spec(dotted)
    origin = getattr(spec, "origin", None) if spec is not None else None
    from_checkout = True
    if origin:
        origin_path = Path(origin)
        if origin_path.is_file() and _outside(origin_path, root):
            from_checkout = False
    if from_checkout:
        loaded, refusal = load_checkout_module(dotted, path, root, PINNED_COMMIT)
        if refusal:
            return None, refusal
        return loaded, None
    try:
        imported = importlib.import_module(dotted)
    except SystemExit:
        return None, "import raised SystemExit"
    except Exception as exc:  # noqa: BLE001 - import failure is an unavailable tool result
        return None, f"{type(exc).__name__}: {exc}"[:240]
    return imported, None


def _safety_block(row: dict[str, Any], *, allow_fetch: bool) -> str | None:
    text = str(row.get("safety") or "")
    if "live_orders" in text or row["package"] in _BLOCKED:
        return "live orders are refused and the blocked import was not performed"
    if "reads keys" in text or "personal or key" in text or "never returned" in text:
        return "key or personal material is not read"
    if text.startswith("process") or "UI start" in text or "loop" in text:
        return "process and loop entry points are not started"
    if text.startswith("writes"):
        return "write entry points are not started"
    if text.startswith("live public fetch") and not allow_fetch:
        return "live fetch is not part of this call"
    if "file does not parse" in text:
        return "file does not parse"
    return None


def _auris_field(symbol: str) -> dict[str, str]:
    meaning = _AURIS.get(symbol)
    if meaning is None and "auris" not in symbol.lower():
        return {}
    return {
        "auris_meaning": meaning or "unspecified Auris name; not scored as the conjecture",
        "auris_note": (
            "Four meanings stay separate. This call is only the meaning named above. "
            "The LambdaEngine conjecture is not called."
        ),
    }


def _invoke(row: dict[str, Any], arguments: dict[str, Any], timeout: float) -> str:
    block = _safety_block(row, allow_fetch=True)
    if block:
        if "live orders" in block:
            return _refused(block)
        return _unavailable(block)
    if row["kind"] in {"module", "class"}:
        return _unavailable("use body_surface for modules and classes")
    if int(row.get("stage") or 0) > ENABLED_THROUGH:
        return _unavailable(f"stage {row['stage']} is not open")
    imported, reason = _import_checked(row["module"])
    if imported is None:
        return _unavailable(reason or "import failed")
    label = f"cited. {row['module']} {row['symbol']} ran."
    extra = _auris_field(row["symbol"])
    if row["kind"] == "function":
        fn = getattr(imported, row["symbol"], None)
        if fn is None or not callable(fn):
            return _unavailable(f"{row['symbol']} is not callable on the imported module")
        arguments = _coerce(fn, arguments)
        missing = _required_missing(fn, arguments)
        if missing:
            return _unavailable(missing)
        state, value = _call_with_timeout(fn, arguments, timeout)
        if state != "ok":
            return _unavailable(str(value))
        return _result(
            {
                "called": True,
                "label": label,
                "result": _plain(value),
                "status": "cited",
                **extra,
            }
        )
    if "." not in row["symbol"]:
        return _unavailable("method symbol has no class")
    class_name, method_name = row["symbol"].rsplit(".", 1)
    cls = getattr(imported, class_name, None)
    if cls is None:
        return _unavailable(f"{class_name} is not on the imported module")
    init_args = arguments.get("init") if isinstance(arguments.get("init"), dict) else {}
    method_args = {key: value for key, value in arguments.items() if key != "init"}
    try:
        signature = inspect.signature(cls.__init__)
        parameters = [name for name in signature.parameters if name != "self"]
        init_args = {key: value for key, value in init_args.items() if key in parameters}
        missing = _required_missing(cls.__init__, {"self": None, **init_args})
    except (TypeError, ValueError):
        missing = None
    if missing:
        return _unavailable(f"constructor: {missing}")
    state, instance = _call_with_timeout(cls, init_args, timeout)
    if state != "ok":
        return _unavailable(f"constructor: {instance}")
    method = getattr(instance, method_name, None)
    if method is None or not callable(method):
        return _unavailable(f"{method_name} is not callable")
    method_args = _coerce(method, method_args)
    missing = _required_missing(method, method_args)
    if missing:
        return _unavailable(missing)
    state, value = _call_with_timeout(method, method_args, timeout)
    if state != "ok":
        return _unavailable(str(value))
    return _result(
        {
            "called": True,
            "label": label,
            "result": _plain(value),
            "status": "cited",
            **extra,
        }
    )


def dispatch(
    module: str,
    symbol: str,
    arguments: dict[str, Any] | None = None,
    *,
    server: str,
    timeout: float = 8.0,
) -> str:
    """Run one inventoried entry point, or refuse it."""

    row = lookup(module, symbol)
    if row is None:
        return _unavailable("symbol is not in the inventory")
    if server == "public" and row["server"] != "public":
        return _unavailable("operator entry point is not on aureon-public", live_orders="refused")
    if server == "public" and row["package"] in _BLOCKED:
        return _refused("blocked package is not imported on aureon-public")
    if server == "operator" and os.environ.get("AUREON_OPERATOR_MCP") != "1":
        return _unavailable("AUREON_OPERATOR_MCP=1 is required")
    if int(row.get("stage") or 0) > ENABLED_THROUGH:
        return _unavailable(f"stage {row['stage']} is not open")
    if server == "operator" and row["server"] == "public":
        return _unavailable("public entry point stays on aureon-public")
    return _invoke(row, arguments or {}, timeout)


def _parse_arguments(arguments_json: str) -> dict[str, Any] | str:
    text = (arguments_json or "").strip()
    if not text:
        return {}
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        return "arguments_json is not JSON"
    if not isinstance(loaded, dict):
        return "arguments_json must be an object"
    return loaded


@quiet
def body_call(module: str, symbol: str, arguments_json: str = "") -> str:
    """Call one public entry point from the inventory. Provenance: cited.

    This runs the named function. It is not a helper. Modules and classes
    are refused here. Operator, key, write, loop, and blocked packages are
    not called. A checkout file is imported only when its git blob matches
    pin a00f744d.

    Args:
        module: Inventory module path, such as harmonic/rainbow_reference.py. Label: cited.
        symbol: Function or Class.method. Label: cited.
        arguments_json: JSON object of keyword arguments. Empty means none. Label: cited.
    """

    parsed = _parse_arguments(arguments_json)
    if isinstance(parsed, str):
        return _unavailable(parsed)
    return dispatch(module, symbol, parsed, server="public")


@quiet
def body_call_operator(module: str, symbol: str, arguments_json: str = "") -> str:
    """Call one operator entry point, or refuse a live order. Provenance: cited.

    Live orders are refused and the blocked trading imports are not performed.
    Keys are not read or returned. AUREON_OPERATOR_MCP=1 is required.

    Args:
        module: Inventory module path. Label: cited.
        symbol: Function or Class.method. Label: cited.
        arguments_json: JSON object of keyword arguments. Label: cited.
    """

    parsed = _parse_arguments(arguments_json)
    if isinstance(parsed, str):
        return _unavailable(parsed)
    return dispatch(module, symbol, parsed, server="operator")


@quiet
def body_surface(module: str, symbol: str) -> str:
    """Read one module or class surface from the inventory. Provenance: cited.

    Nothing is imported and nothing is constructed. Functions are not called.

    Args:
        module: Inventory module path. Label: cited.
        symbol: Module stem or class name. Label: cited.
    """

    row = lookup(module, symbol)
    if row is None:
        return _unavailable("symbol is not in the inventory")
    if int(row.get("stage") or 0) > ENABLED_THROUGH:
        return _unavailable(f"stage {row['stage']} is not open")
    if row["server"] != "public":
        return _unavailable("operator surface is not on aureon-public")
    rows, _ = _inventory()
    methods = [
        item["symbol"]
        for item in rows
        if item["module"] == module and item["kind"] == "method" and item["symbol"].startswith(symbol + ".")
    ]
    return _result(
        {
            "called": False,
            "form": row["form"],
            "kind": row["kind"],
            "label": "cited. Surface only. The entry point was not called.",
            "methods": methods[:40],
            "safety": row["safety"],
            "server": row["server"],
            "stage": row["stage"],
            "status": "cited",
            "symbol": symbol,
        }
    )


def depth_report() -> dict[str, Any]:
    """Per-package counts. ``called`` is filled from sweep files when present."""

    rows, _ = _inventory()
    packages: dict[str, dict[str, int]] = {}
    for row in rows:
        bucket = packages.setdefault(
            row["package"],
            {"called": 0, "listed": 0, "open": 0, "operator": 0, "public": 0},
        )
        bucket["listed"] += 1
        if row["server"] == "public":
            bucket["public"] += 1
        else:
            bucket["operator"] += 1
        if int(row["stage"]) <= ENABLED_THROUGH:
            bucket["open"] += 1
    root = repo_root()
    called: dict[str, int] = {}
    for stage in range(1, ENABLED_THROUGH + 1):
        path = root / "measured" / f"body_stage{stage}.json"
        if not path.is_file():
            continue
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for item in record.get("calls") or []:
            if item.get("called") is True:
                package = str(item.get("package") or "")
                called[package] = called.get(package, 0) + 1
    for package, count in called.items():
        if package in packages:
            packages[package]["called"] = count
    return {
        "enabled_through": ENABLED_THROUGH,
        "label": "cited. Depth counts calls recorded in measured/body_stageN.json. A listed row is not a call.",
        "packages": packages,
        "provenance": "cited",
        "servers": {
            "operator": sum(1 for row in rows if row["server"] == "operator"),
            "public": sum(1 for row in rows if row["server"] == "public"),
        },
        "status": "cited",
        "symbols": len(rows),
    }


@quiet
def body_registry() -> str:
    """Name the public and operator servers and the inventory they address. Provenance: cited.

    This is the registry. It does not call package entry points. Live orders stay refused.
    A checkout file is still blob-checked before a later call imports it.

    Args:
        none: This tool takes no inputs. Label: cited, the registry.
    """

    return _result(
        {
            "blocked_imports": sorted(_BLOCKED),
            "enabled_through": ENABLED_THROUGH,
            "inventory": "docs/mcp/FULL_BODY_PLAN.md",
            "label": "cited. Registry only. No package entry point ran.",
            "live_orders": "refused",
            "operator": {
                "flag": "AUREON_OPERATOR_MCP=1",
                "tool": "body_call_operator",
                "transport": "stdio",
            },
            "pin": PINNED_COMMIT,
            "public_tools": ["body_call", "body_depth", "body_registry", "body_surface"],
            "spaces": [
                "huggingface/hnc-field/app.py",
                "huggingface/auris-coherence/app.py",
                "huggingface/qgita-snr/app.py",
                "huggingface/organism-replay/app.py",
            ],
            "status": "cited",
        }
    )


@quiet
def body_depth() -> str:
    """Per-package depth for the stages that are open. Provenance: cited.

    ``called`` counts entry points that a measured sweep actually ran.
    Listing a symbol is not depth. Helper tools are not counted here.

    Args:
        none: This tool takes no inputs. Label: cited, the depth table.
    """

    report = depth_report()
    report["aureon_source_note"] = aureon_source().get("kind")
    return _result(report)


def probes_for(stage: int) -> list[dict[str, Any]]:
    """Real entry points the measured run calls for one stage."""

    table: dict[int, list[dict[str, Any]]] = {
        1: [
            {"module": "harmonic/rainbow_reference.py", "symbol": "solfeggio_ladder"},
            {"module": "harmonic/rainbow_reference.py", "symbol": "love_centrality"},
            {
                "module": "harmonic/aureon_harmonic_reality.py",
                "symbol": "HarmonicSubstrate.evaluate",
                "arguments": {"t": 0.0},
            },
            {
                "module": "harmonic/aureon_harmonic_reality.py",
                "symbol": "CausalEcho.evaluate",
                "arguments": {"current_lambda": 0.0},
            },
            {"module": "core/hnc_field.py", "symbol": "blend_field"},
            {"module": "core/hnc_params.py", "symbol": "load_params"},
            {"module": "wisdom/aureon_qgita_framework.py", "symbol": "get_qgita_analyzer"},
            {
                "module": "utils/aureon_queen_hive_mind.py",
                "symbol": "QueenHiveMind.read_auris_nodes",
            },
        ],
        2: [
            {
                "module": "alignment/harmonic_resonance.py",
                "symbol": "consonance_score",
                "arguments": {"ratio": 1.0},
            },
            {"module": "cognition/logic_flow.py", "symbol": "compute_logic_flow"},
            {
                "module": "queen/temporal_ground.py",
                "symbol": "compute_zpe_ground",
                "arguments": {"lambda_t": 0.0},
            },
            {
                "module": "swarm/druidic_council.py",
                "symbol": "voice_for_gamma",
                "arguments": {"gamma": 0.5},
            },
            {
                "module": "swarm_motion/love_stream.py",
                "symbol": "StandingWaveLoveStream.evaluate",
            },
            {
                "module": "gates/switchboard.py",
                "symbol": "is_human_held",
                "arguments": {"action": "draft"},
            },
            {
                "module": "gates/panel.py",
                "symbol": "ungrounded_nodes",
                "arguments": {"grounded_slices": []},
            },
            {
                "module": "governance/celtic_voice_bank.py",
                "symbol": "seasonal_gate_for_date",
                "arguments": {"value": "2026-10-29"},
            },
            {"module": "observer/live_data_policy.py", "symbol": "simulation_fallback_allowed"},
        ],
        3: [
            {
                "module": "bio/audio_signal_adapter.py",
                "symbol": "synthetic_audio",
                "arguments": {"kind": "noise", "n": 16},
            },
            {
                "module": "bio/calibration_curve.py",
                "symbol": "compute_calibration",
                "arguments": {"trials": 2, "nulls": 1},
            },
            {"module": "organism/repository_layers.py", "symbol": "compose_repository_layers"},
            {"module": "core/aureon_organism_spine.py", "symbol": "build_organism_manifest"},
            {
                "module": "vault/voice/document_artifact_skill.py",
                "symbol": "count_words",
                "arguments": {"text": "one two three"},
            },
            {
                "module": "evaluation/auris_node_eval.py",
                "symbol": "evaluate_auris_nodes",
                "timeout": 20,
            },
        ],
        4: [
            {
                "module": "data_feeds/unified_ws_feed.py",
                "symbol": "parse_binance_tick",
                "arguments": {
                    "data": {"s": "BTCUSDT", "b": "1", "a": "2", "c": "1.5", "v": "3", "P": "0", "E": 0}
                },
            },
            {
                "module": "decoders/grail_convergence.py",
                "symbol": "haversine",
                "arguments": {"lat1": 51.5, "lon1": -0.12, "lat2": 48.86, "lon2": 2.35},
            },
            {
                "module": "search/online_research_cinema.py",
                "symbol": "summarize_text",
                "arguments": {"text": "The field is a reading. The reading is not an order.", "topic": "field"},
            },
            {
                "module": "portals/ifs.py",
                "symbol": "html_to_text",
                "arguments": {"html": "<p>Hello field</p>"},
            },
            {
                "module": "analytics/backtest_sentiment_oracle.py",
                "symbol": "derive_fear_greed",
                "arguments": {
                    "closes": [1, 1.1, 1.2, 1.1, 1.3, 1.4, 1.2, 1.5],
                    "volumes": [1, 1, 1, 1, 1, 1, 1, 1],
                    "idx": 7,
                },
            },
            {
                "module": "atn/aureon_atn_backtest.py",
                "symbol": "compute_impacts",
                "arguments": {"events": [], "candles": [], "symbol": "BTC"},
            },
            {
                "module": "monitors/margin_eta_predictor.py",
                "symbol": "calc_breakeven",
                "arguments": {"entry": 100.0},
            },
            {
                "module": "monitors/margin_eta_predictor.py",
                "symbol": "normalise_pair",
                "arguments": {"pair": "btcusd"},
            },
        ],
        5: [
            {"module": "accounting/file_drop.py", "symbol": "registered_ingestors", "server": "operator"},
            {
                "module": "portfolio/aureon_billion_goal_tracker.py",
                "symbol": "get_days_remaining",
                "server": "operator",
            },
            {"module": "trading/__init__.py", "symbol": "__init__", "server": "operator"},
            {"module": "exchanges/__init__.py", "symbol": "__init__", "server": "operator"},
            {"module": "bots/__init__.py", "symbol": "__init__", "server": "operator"},
            {"module": "bots_intelligence/__init__.py", "symbol": "__init__", "server": "operator"},
            {"module": "bridges/__init__.py", "symbol": "__init__", "server": "operator"},
            {"module": "scanners/__init__.py", "symbol": "__init__", "server": "operator"},
            {
                "module": "unified_margin_trader/_margin_monitor.py",
                "symbol": "_margin_monitor",
                "server": "operator",
            },
        ],
        6: [
            {
                "module": "approval/compose.py",
                "symbol": "subject_line",
                "arguments": {"action": "status"},
            },
            {
                "module": "briefing/schemas.py",
                "symbol": "severity_rank",
                "arguments": {"severity": "high"},
            },
            {
                "module": "grants/daemon.py",
                "symbol": "breath_interval",
                "arguments": {"urgency": None},
            },
            {
                "module": "integrations/ollama/hnc_phi_swarm.py",
                "symbol": "build_phi_swarm_plan",
                "arguments": {"flow": {"flow": "observe"}, "catalog_size": 2, "max_total_calls": 4},
            },
            {
                "module": "intelligence/aureon_advanced_intelligence.py",
                "symbol": "calculate_harmonic_resonance",
                "arguments": {"freq1": 100.0, "freq2": 200.0},
            },
            {
                "module": "plumber/crypto.py",
                "symbol": "sha256_hex",
                "arguments": {"value": "aureon-public"},
            },
            {
                "module": "s51/aureon_51_compound.py",
                "symbol": "summarize_compounding",
                "arguments": {"receipts": []},
            },
            {
                "module": "simulation/aureon_world_simulator.py",
                "symbol": "hz_to_rgb",
                "arguments": {"hz": 528.0},
            },
            {
                "module": "generated/research_cinema/harmonic_nexus_score_model.py",
                "symbol": "build_default_inputs",
            },
        ],
    }
    return table.get(stage, [])


def sweep_zero_arg(stage: int, *, timeout: float = 8.0) -> list[dict[str, Any]]:
    """Call public zero-argument functions for one open stage.

    Fetches, writes, keys, loops, and blocked packages are skipped.
    """

    if stage > ENABLED_THROUGH:
        return []
    rows, _ = _inventory()
    calls: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for probe in probes_for(stage):
        key = (probe["module"], probe["symbol"])
        seen.add(key)
        target = str(probe.get("server") or "public")
        if target == "operator":
            os.environ["AUREON_OPERATOR_MCP"] = "1"
            os.environ["AUREON_DISABLE_REAL_ORDERS"] = "1"
        raw = dispatch(
            probe["module"],
            probe["symbol"],
            probe.get("arguments") or {},
            server=target,
            timeout=float(probe.get("timeout") or timeout),
        )
        calls.append(_summarize(probe["module"], probe["symbol"], raw, probe=True))
    for row in rows:
        if int(row["stage"]) != stage or row["server"] != "public":
            continue
        if row["kind"] != "function" or int(row.get("required") or 0) != 0 or row.get("async"):
            continue
        if not str(row.get("safety") or "").startswith("runs from inputs"):
            continue
        if stage >= 6:
            continue
        if stage >= 2:
            if row["package"] == "queen":
                continue
            if _UNSAFE_NAME.search(row["symbol"]) or _SKIP_WORD.search(row["symbol"]):
                continue
            if not _quiet_source(row["module"], row["symbol"]):
                continue
        key = (row["module"], row["symbol"])
        if key in seen:
            continue
        seen.add(key)
        raw = dispatch(row["module"], row["symbol"], {}, server="public", timeout=timeout)
        calls.append(_summarize(row["module"], row["symbol"], raw, probe=False))
    return calls


def _summarize(module: str, symbol: str, raw: str, *, probe: bool) -> dict[str, Any]:
    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        body = {"status": "unavailable", "reason": "result was not JSON"}
    package = module.split("/", 1)[0]
    if module.startswith("unified_margin_trader/"):
        package = "unified_margin_trader"
    elif not module.startswith("unified_margin_trader"):
        # inventory modules are relative to aureon/, so the first part is the package
        # except core/utils/wisdom paths. package is the first directory.
        package = module.split("/", 1)[0]
    return {
        "called": body.get("called") is True and body.get("status") == "cited",
        "module": module,
        "package": package,
        "probe": probe,
        "reason": body.get("reason"),
        "status": body.get("status"),
        "symbol": symbol,
    }
