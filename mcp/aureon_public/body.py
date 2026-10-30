"""Address every inventoried entry point without registering thousands of tools.

`body_call` runs a real function or method. `body_surface` reads a module or
class and does not construct it. Depth is the count of calls, not the count
of rows in the plan. A helper label is not used here.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
from datetime import date
from pathlib import Path
from typing import Any

from aureon_public.guard_loader import PINNED_COMMIT, apply_space_guard, aureon_source
from aureon_public.paths import repo_root
from aureon_public.pin_blob import checkout_blob_refusal, load_checkout_module
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
    "os.system",
    "sqlite",
    "execute(",
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
_INVENTORY_REFUSAL: str | None = None
# sha256 of the committed docs/mcp/inventory.json. A different file is not loaded.
INVENTORY_SHA256 = "4bc19ea9b5444a7b8a9abbd3fabf635d083bd25bea6c1b2d6eab2605b4f5716b"
_LEAKY_PARAMS = {"url", "path", "out", "file", "host"}
# Operator-scoped rows are refused unless named here. No portfolio or accounting key reader.
_OPERATOR_ALLOWLIST = {
    ("accounting/file_drop.py", "registered_ingestors"),
    ("portfolio/aureon_billion_goal_tracker.py", "get_days_remaining"),
}
# A method call constructs its class. An unlisted constructor is not run.
_CONSTRUCTOR_ALLOWLIST: set[tuple[str, str]] = set()
_NAME_CONTAINS = ("write", "save", "export", "dump", "start", "run")
_WORKER_SLOTS = threading.BoundedSemaphore(4)


def enabled_stage() -> int:
    return ENABLED_THROUGH


def _inventory() -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    global _ROWS, _INDEX, _INVENTORY_REFUSAL
    if _ROWS is not None and _INDEX is not None:
        return _ROWS, _INDEX
    path = repo_root() / "docs" / "mcp" / "inventory.json"
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != INVENTORY_SHA256:
        _INVENTORY_REFUSAL = "inventory hash mismatch"
        _ROWS = []
        _INDEX = {}
        return _ROWS, _INDEX
    _INVENTORY_REFUSAL = None
    loaded = json.loads(data)
    if not isinstance(loaded, list):
        _INVENTORY_REFUSAL = "inventory hash mismatch"
        _ROWS = []
        _INDEX = {}
        return _ROWS, _INDEX
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


def _blocked_dotted_prefix(dotted: str) -> str | None:
    parts = dotted.split(".")
    if parts[0] in _BLOCKED:
        return f"package {parts[0]} is not importable"
    if parts[0] == "aureon" and len(parts) > 1 and parts[1] in _BLOCKED:
        return f"package {parts[1]} is not importable"
    return None


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
    class_name, _, method_name = symbol.partition(".")
    nodes: list[ast.AST] = list(tree.body)
    target = symbol
    if method_name:
        target = method_name
        nodes = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                nodes = list(node.body)
                break
    for node in nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == target:
            end = node.end_lineno or node.lineno
            return "\n".join(lines[node.lineno - 1 : end])
    return ""


def _parameter_names(module: str, symbol: str) -> list[str] | None:
    """Named parameters from the AST. None when the function cannot be found."""

    path = file_for(module)
    if not path.is_file():
        return None
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError):
        return None
    class_name, _, method_name = symbol.partition(".")
    nodes: list[ast.AST] = list(tree.body)
    target = symbol
    if method_name:
        target = method_name
        nodes = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                nodes = list(node.body)
                break
    for node in nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == target:
            names = [
                item.arg
                for item in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
                if item.arg not in {"self", "cls"}
            ]
            return names
    return None


def _leaky_parameter(module: str, symbol: str) -> bool:
    names = _parameter_names(module, symbol)
    if names is None:
        return True
    for name in names:
        parts = name.lower().split("_")
        if any(part in _LEAKY_PARAMS for part in parts):
            return True
    return False


def _name_blocked(symbol: str) -> str | None:
    leaf = symbol.rsplit(".", 1)[-1]
    if "run_humaneval" in symbol.lower():
        return "run_humaneval is not called"
    if _UNSAFE_NAME.search(leaf) or _SKIP_WORD.search(leaf):
        return "name is not called on the public server"
    lowered = leaf.lower()
    for token in _NAME_CONTAINS:
        if token in lowered:
            return f"name contains {token}"
    return None


def _package_kind(package: str) -> str:
    import aureon_public.more_layers  # noqa: F401 - applies the excluded kinds

    from aureon_public.layers import PACKAGES

    for row in PACKAGES:
        if row["package"] == package:
            return row["kind"]
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


def _checkout_load(module: str) -> str | None:
    """Hash-check the target file. The worker loads parents through the finder.

    ``find_spec`` is not used. It would import parent packages before the blob check.
    """

    return checkout_blob_refusal(file_for(module), repo_root(), PINNED_COMMIT)


def _worker_env() -> dict[str, str]:
    """Minimal child environment. Parent secrets and extras are not copied across."""

    package_root = str(Path(__file__).resolve().parents[1])
    env: dict[str, str] = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "TMPDIR": os.environ.get("TMPDIR", "") or tempfile.gettempdir(),
        "PYTHONPATH": package_root,
        "AUREON_AUDIT_MODE": "1",
        "AUREON_DISABLE_REAL_ORDERS": "1",
        "AUREON_DISABLE_LIVE_BACKGROUND_STARTUP": "1",
        "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS": "1",
        "AUREON_ENABLE_AUTONOMOUS_CONTROL": "0",
        "AUREON_ACTIVATE_ON_IMPORT": "0",
    }
    for key in ("LANG", "LC_ALL", "LC_CTYPE", "PYTHONHASHSEED"):
        value = os.environ.get(key)
        if value:
            env[key] = value
    return env


def _worker_argv() -> list[str]:
    """Isolated interpreter. The mcp path is argv, not cwd and not PYTHONPATH.

    ``-I`` implies ``-E``, ``-s``, and ``-P``, so the checkout is not on sys.path
    and a root-level ``json.py`` or ``aureon_public`` package cannot shadow the worker.
    """

    mcp_root = str(Path(__file__).resolve().parents[1])
    code = (
        "import sys\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "from aureon_public.call_worker import main\n"
        "main()\n"
    )
    return [sys.executable, "-I", "-c", code, mcp_root]


def _worker_cwd() -> str:
    """A directory outside the checkout. cwd must not become sys.path[0]."""

    return tempfile.gettempdir()


def _acquire_worker() -> None:
    _WORKER_SLOTS.acquire()


def _release_worker() -> None:
    _WORKER_SLOTS.release()


def _call_in_subprocess(module: str, symbol: str, arguments: dict[str, Any], timeout: float) -> tuple[str, Any]:
    """Run the entry point in a child process. A timeout kills the process group."""

    if symbol.lower().endswith(".__init__") or symbol.split(".")[-1].startswith("_"):
        return "error", "private entry point is not called"
    checkout_error = _checkout_load(module)
    if checkout_error:
        return "error", checkout_error
    _acquire_worker()
    payload = json.dumps(
        {
            "dotted": dotted_for(module),
            "module": module,
            "symbol": symbol,
            "arguments": arguments,
        }
    ).encode("utf-8")
    try:
        process = subprocess.Popen(
            _worker_argv(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            cwd=_worker_cwd(),
            env=_worker_env(),
        )
        try:
            stdout, _stderr = process.communicate(payload, timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
            return "timeout", f"exceeded {timeout:g}s"
        if process.returncode not in {0, None}:
            text = stdout.decode("utf-8", errors="replace").strip()
            if not text:
                return "error", f"worker exited {process.returncode}"
        try:
            body = json.loads(stdout.decode("utf-8"))
        except json.JSONDecodeError:
            return "error", "worker result was not JSON"
        if body.get("ok") is True:
            return "ok", body.get("result")
        return "error", str(body.get("error") or "worker failed")[:240]
    finally:
        _release_worker()


def _constructor_refusal(module: str, class_name: str) -> str | None:
    from aureon_public.inventory_scan import source_is_risky

    if (module, class_name) not in _CONSTRUCTOR_ALLOWLIST:
        return "constructor is not allowlisted"
    source = _function_source(module, f"{class_name}.__init__")
    if source_is_risky(source):
        return "constructor failed the risk scan"
    return None


def _operator_allowlist_refusal(row: dict[str, Any]) -> str | None:
    """Every operator-path row must be named. Fetch and write stay closed."""

    key = (str(row["module"]), str(row["symbol"]))
    if key not in _OPERATOR_ALLOWLIST:
        return "operator row is not allowlisted"
    source = _function_source(str(row["module"]), str(row["symbol"]))
    if re.search(r"api_key|secret|password|credential|private_key", source or "", re.I):
        return "portfolio or accounting key reader is not allowlisted"
    if row["package"] in {"portfolio", "accounting"} and re.search(
        r"api_key|secret|password|credential|private_key", str(row["symbol"]), re.I
    ):
        return "portfolio or accounting key reader is not allowlisted"
    return None


def _import_checked(module: str) -> tuple[Any | None, str | None]:
    """Load a module and its parents through the pinned loader.

    There is no outside-checkout fallback and no ``find_spec`` on the full name.
    """

    apply_space_guard()
    from aureon_public.layers import _load_phenolic_fingerprint

    _load_phenolic_fingerprint()
    path = file_for(module)
    dotted = dotted_for(module)
    blocked = _blocked_dotted_prefix(dotted)
    if blocked:
        return None, blocked
    root = repo_root()
    loaded, refusal = load_checkout_module(dotted, path, root, PINNED_COMMIT)
    if refusal:
        return None, refusal
    return loaded, None


def _safety_block(row: dict[str, Any], *, allow_fetch: bool, allow_write: bool) -> str | None:
    text = str(row.get("safety") or "")
    if "live_orders" in text or row["package"] in _BLOCKED:
        return "live orders are refused and the blocked import was not performed"
    if "reads keys" in text or "personal or key" in text or "never returned" in text:
        return "key or personal material is not read"
    if text.startswith("process") or "UI start" in text or "loop" in text:
        return "process and loop entry points are not started"
    if text.startswith("writes") and not allow_write:
        return "write entry points are not started"
    if "write or process start" in text and not allow_write:
        return "write or process start is refused"
    if text.startswith("live public fetch") and not allow_fetch:
        return "live fetch is not part of this call"
    if "file does not parse" in text:
        return "file does not parse"
    return None


_REFUSAL_CACHE: dict[tuple[str, str], str | None] = {}


def public_entry_refusal(row: dict[str, Any]) -> str | None:
    """Why the public server will not run this row. None when it may run."""

    key = (str(row.get("module") or ""), str(row.get("symbol") or ""))
    if key in _REFUSAL_CACHE:
        return _REFUSAL_CACHE[key]
    reason = _public_entry_refusal(row)
    _REFUSAL_CACHE[key] = reason
    return reason


def _public_entry_refusal(row: dict[str, Any]) -> str | None:
    if row["server"] != "public":
        return "operator entry point is not on aureon-public"
    if row["package"] in _BLOCKED:
        return "blocked package is not imported on aureon-public"
    kind = _package_kind(str(row["package"]))
    if kind in {"operator", "excluded"}:
        return f"package {row['package']} is {kind}"
    if int(row.get("stage") or 0) > ENABLED_THROUGH:
        return f"stage {row['stage']} is not open"
    if row["kind"] not in _ENTRY_KINDS:
        return "use body_surface for modules and classes"
    block = _safety_block(row, allow_fetch=False, allow_write=False)
    if block:
        return block
    blocked_name = _name_blocked(str(row["symbol"]))
    if blocked_name:
        return blocked_name
    if _leaky_parameter(str(row["module"]), str(row["symbol"])):
        return "parameter can carry a url, path, file, or host"
    if row["kind"] == "method":
        class_name = str(row["symbol"]).rsplit(".", 1)[0]
        constructor = _constructor_refusal(str(row["module"]), class_name)
        if constructor:
            return constructor
    if not _quiet_source(str(row["module"]), str(row["symbol"])):
        return "source is not a quiet read"
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


def _invoke(
    row: dict[str, Any],
    arguments: dict[str, Any],
    timeout: float,
    *,
    allow_fetch: bool,
    allow_write: bool,
) -> str:
    block = _safety_block(row, allow_fetch=allow_fetch, allow_write=allow_write)
    if block:
        if "live orders" in block:
            return _refused(block)
        return _unavailable(block)
    if row["kind"] in {"module", "class"}:
        return _unavailable("use body_surface for modules and classes")
    if int(row.get("stage") or 0) > ENABLED_THROUGH:
        return _unavailable(f"stage {row['stage']} is not open")
    if "." in str(row["symbol"]):
        class_name = str(row["symbol"]).rsplit(".", 1)[0]
        constructor = _constructor_refusal(str(row["module"]), class_name)
        if constructor:
            return _unavailable(constructor)
    label = f"cited. {row['module']} {row['symbol']} ran."
    extra = _auris_field(row["symbol"])
    state, value = _call_in_subprocess(str(row["module"]), str(row["symbol"]), arguments, timeout)
    if state != "ok":
        return _unavailable(str(value))
    return _result(
        {
            "called": True,
            "label": label,
            "result": value,
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

    _inventory()
    if _INVENTORY_REFUSAL:
        return _unavailable(_INVENTORY_REFUSAL)
    row = lookup(module, symbol)
    if row is None:
        return _unavailable("symbol is not in the inventory")
    if server == "operator" and os.environ.get("AUREON_OPERATOR_MCP") != "1":
        return _unavailable("AUREON_OPERATOR_MCP=1 is required")
    if server == "operator":
        allow = _operator_allowlist_refusal(row)
        if allow:
            return _unavailable(allow, live_orders="refused")
        return _invoke(row, arguments or {}, timeout, allow_fetch=False, allow_write=False)
    if server == "public":
        reason = public_entry_refusal(row)
        if reason:
            if (
                "live orders" in reason
                or reason.startswith("blocked package")
                or reason.startswith("operator entry point")
            ):
                return _refused(reason)
            return _unavailable(reason)
        return _invoke(row, arguments or {}, timeout, allow_fetch=False, allow_write=False)
    return _unavailable("unknown server")


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


_ENTRY_KINDS = {"function", "method"}


def package_depth(stage: int | None = None) -> dict[str, dict[str, int]]:
    """Reachable public functions and methods, out of the pinned inventory.

    The denominator is every public function and method. The numerator is how
    many of those the public server will still run. A listed row is not reachable.
    """

    rows, _ = _inventory()
    selected = [row for row in rows if stage is None or int(row["stage"]) == stage]
    seen: dict[str, set[tuple[str, str]]] = {}
    reachable: dict[str, set[tuple[str, str]]] = {}
    names: set[str] = set()
    for row in selected:
        names.add(str(row["package"]))
        if row["server"] != "public" or row["kind"] not in _ENTRY_KINDS:
            continue
        key = (str(row["module"]), str(row["symbol"]))
        bucket = seen.setdefault(str(row["package"]), set())
        if key in bucket:
            continue
        bucket.add(key)
        if public_entry_refusal(row) is None:
            reachable.setdefault(str(row["package"]), set()).add(key)
    return {
        package: {
            "reachable": len(reachable.get(package, set())),
            "public_entry_points": len(seen.get(package, set())),
        }
        for package in sorted(names)
    }


def render_readme_depth() -> str:
    """The README depth section. Tests require the file to contain this text."""

    lines = [
        "A layer counts as full depth only where its real entry points are called.",
        "Each figure is reachable public functions and methods out of the public functions and methods in the pinned `docs/mcp/inventory.json`.",
        "",
        "| Package | Reachable | Public entry points |",
        "| --- | ---: | ---: |",
    ]
    for package, row in package_depth().items():
        lines.append(f"| {package} | {row['reachable']} | {row['public_entry_points']} |")
    return "\n".join(lines)


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
    entry_points = package_depth()
    for package, row in entry_points.items():
        bucket = packages.setdefault(
            package,
            {"called": 0, "listed": 0, "open": 0, "operator": 0, "public": 0},
        )
        bucket["called"] = row["reachable"]
        bucket["reachable"] = row["reachable"]
        bucket["public_entry_points"] = row["public_entry_points"]
    return {
        "enabled_through": ENABLED_THROUGH,
        "entry_points": entry_points,
        "label": (
            "cited. Depth is reachable public functions and methods out of the public "
            "functions and methods in the pinned inventory. A listed row is not reachable."
        ),
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
