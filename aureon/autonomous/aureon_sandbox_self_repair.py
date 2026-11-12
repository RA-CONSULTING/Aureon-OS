"""Plug-in self-repair for a Python project.

Point it at a project. It runs pytest, repairs the implementation (not the
test) when the failure is one it can prove, reruns the tests, and commits the
repair on a local branch with a review log.

    python -m aureon.autonomous.aureon_sandbox_self_repair --root /path/to/project

From the fusion tree the same command is:

    python -m aureon_fusion.repair --root /path/to/project

It repairs a proved implementation bug, such as an off-by-one in a pure utility.
In guarded mode it does not arm live trading, change an evidence gate, change
position sizing, or write credential files. Those attempts are flagged for
human review and are not applied. Full autonomy mode, set locally by the owner,
allows the first three. Credential files stay refused in both modes. Repair
stays disabled unless AUREON_SELF_REPAIR_ENABLE=1 and
state/self_repair_config.json contains {"enabled": true}. A missing config
stops it. The kill variable and the kill file do not. The repair does not
rewrite the test file.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import operator
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from aureon.autonomous.self_repair_guard import (
    SelfRepairBlocked,
    append_review,
    block_reason_for_write,
    require_self_repair_enabled,
)

SCHEMA = "aureon.sandbox-self-repair.v2"
MAX_REPAIRS = 8
# Owner's call (12:20 GMT): small fixes, often and fast. Try many candidates per cycle, each
# checked against only its targeted/module tests (seconds), then ONE full suite confirms no
# regressions across the banked fixes. These bound the fast inner loop; env can override.
MAX_CANDIDATES = 24


def _inner_budget_s() -> float:
    try:
        return float(os.environ.get("AUREON_QUEEN_REPAIR_INNER_BUDGET_S", "180") or 180)
    except ValueError:
        return 180.0


def _fast_timeout_s() -> float | None:
    try:
        value = float(os.environ.get("AUREON_QUEEN_REPAIR_FAST_TIMEOUT_S", "120") or 120)
    except ValueError:
        value = 120.0
    return value if value > 0 else None


BISECT_MAX = 6


def load_architect():
    """Load the Queen writer without importing the rest of the Queen package."""

    path = Path(__file__).resolve().parents[1] / "queen" / "queen_code_architect.py"
    spec = importlib.util.spec_from_file_location("aureon_queen_code_architect_direct", path)
    if spec is None or spec.loader is None:
        raise ImportError("queen_code_architect.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.QueenCodeArchitect
_OPS: dict[type, tuple[str, Callable[[Any, Any], Any]]] = {
    ast.Add: ("+", operator.add),
    ast.Sub: ("-", operator.sub),
    ast.Mult: ("*", operator.mul),
    ast.FloorDiv: ("//", operator.floordiv),
}
_OP_TOKENS = {token: (node, func) for node, (token, func) in _OPS.items()}


class SuiteTimedOut(Exception):
    """The full suite ran past the operator's safety-net limit."""


def _suite_timeout() -> float | None:
    # No fixed cap by default: the suite runs until it finishes. AUREON_SELF_REPAIR_SUITE_TIMEOUT_S > 0 sets a safety net.
    try:
        value = float(os.environ.get("AUREON_SELF_REPAIR_SUITE_TIMEOUT_S", "0") or 0)
    except ValueError:
        value = 0.0
    return value if value > 0 else None


def _pytest(root: Path) -> subprocess.CompletedProcess[str]:
    for cache in root.rglob("__pycache__"):
        if cache.is_dir():
            shutil.rmtree(cache, ignore_errors=True)
    # The repair is often spawned by a live organ. Its pytest must not inherit
    # that launcher's session, workspace or exchange credentials, and must not
    # reload them from a .env: otherwise a launcher smoke test inside the suite
    # boots organs from the live folder, with live keys, and cannot stop them.
    from aureon.launch.session_scope import isolated_child_env

    env = isolated_child_env(dict(os.environ))
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    limit = _suite_timeout()
    # Private pytest temp root: the shared /tmp/pytest-of-<user> keeps only the newest three runs,
    # so another pytest on the host could delete this suite's tmp_path mid-run (FileNotFoundError storms).
    import tempfile
    basetemp = Path(tempfile.mkdtemp(prefix="aureon_self_repair_pytest_"))
    try:
        return subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "--tb=short", "-p", "no:cacheprovider",
             f"--basetemp={basetemp / 'run'}"],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=limit,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise SuiteTimedOut(limit) from exc
    finally:
        shutil.rmtree(basetemp, ignore_errors=True)


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, timeout=30)


def _prepare_branch(root: Path) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    branch = f"aureon-self-repair/{stamp}"
    if not (root / ".git").exists():
        _git(root, "init")
        _git(root, "config", "user.email", "aureon-self-repair@localhost")
        _git(root, "config", "user.name", "Aureon self-repair")
        _git(root, "add", "-A")
        _git(root, "commit", "-m", "sandbox before self-repair", "--allow-empty")
    _git(root, "checkout", "-B", branch)
    return branch


def _py_files(root: Path, *, tests: bool) -> list[Path]:
    found: list[Path] = []
    for path in sorted(root.rglob("*.py")):
        if any(part in {".git", "__pycache__", "state", "queen_backups"} for part in path.parts):
            continue
        relative = path.relative_to(root).as_posix()
        is_test = path.name.startswith("test_") or "/test_" in f"/{relative}" or relative.startswith("tests/")
        if is_test == tests:
            found.append(path)
    return found


def _failing_tests(output: str) -> set[str]:
    names = set(re.findall(r"FAILED\s+\S+::(test_\w+)", output))
    names.update(re.findall(r"^E\s+.*\b(test_\w+)\b", output, re.MULTILINE))
    return names


def _assertions(root: Path, only: set[str] | None) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for path in _py_files(root, tests=True):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
                continue
            if only and node.name not in only:
                continue
            for statement in ast.walk(node):
                if not isinstance(statement, ast.Assert) or not isinstance(statement.test, ast.Compare):
                    continue
                compare = statement.test
                if len(compare.ops) != 1 or not isinstance(compare.ops[0], ast.Eq):
                    continue
                if len(compare.comparators) != 1 or not isinstance(compare.comparators[0], ast.Constant):
                    continue
                expected = compare.comparators[0].value
                if isinstance(expected, (bool, int, float, str)) is False:
                    continue
                call = compare.left
                if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
                    continue
                args = []
                ok = True
                for arg in call.args:
                    if not isinstance(arg, ast.Constant) or isinstance(arg.value, bool) and not isinstance(arg.value, int):
                        ok = False
                        break
                    if not isinstance(arg.value, (int, float, str)):
                        ok = False
                        break
                    args.append(arg.value)
                if not ok or call.keywords:
                    continue
                found.append(
                    {
                        "test": path.relative_to(root).as_posix(),
                        "test_name": node.name,
                        "function": call.func.id,
                        "args": args,
                        "expected": expected,
                    }
                )
    return found


def _function(root: Path, name: str) -> tuple[Path, ast.FunctionDef] | None:
    matches: list[tuple[Path, ast.FunctionDef]] = []
    for path in _py_files(root, tests=False):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == name:
                matches.append((path, node))
    if len(matches) != 1:
        return None
    return matches[0]


def _literal_return_edit(path: Path, node: ast.FunctionDef, assertions: list[dict[str, Any]]) -> tuple[str, str] | None:
    if len(node.body) != 1 or not isinstance(node.body[0], ast.Return):
        return None
    value = node.body[0].value
    if not isinstance(value, ast.Constant):
        return None
    expected = {item["expected"] for item in assertions}
    if len(expected) != 1:
        return None
    target = expected.pop()
    current = value.value
    if current == target or type(current) is not type(target):
        return None
    line = path.read_text(encoding="utf-8").splitlines()[node.body[0].lineno - 1].strip()
    prefix = "return "
    if not line.startswith(prefix):
        return None
    expr = line[len(prefix) :].strip()
    if isinstance(target, str):
        quote = '"' if expr.startswith('"') else "'"
        rendered = quote + target.replace("\\", "\\\\").replace(quote, "\\" + quote) + quote
    elif isinstance(target, bool):
        rendered = "True" if target else "False"
    else:
        rendered = repr(target)
    return (line, prefix + rendered)


def _operator_edit(path: Path, node: ast.FunctionDef, assertions: list[dict[str, Any]]) -> tuple[str, str] | None:
    if len(node.args.args) != 2 or len(node.body) != 1 or not isinstance(node.body[0], ast.Return):
        return None
    value = node.body[0].value
    if not isinstance(value, ast.BinOp) or type(value.op) not in _OPS:
        return None
    left_name, right_name = node.args.args[0].arg, node.args.args[1].arg
    if not isinstance(value.left, ast.Name) or not isinstance(value.right, ast.Name):
        return None
    if value.left.id != left_name or value.right.id != right_name:
        return None
    if not assertions or any(len(item["args"]) != 2 for item in assertions):
        return None
    current_token = _OPS[type(value.op)][0]
    winners = []
    for token, (_node, func) in _OP_TOKENS.items():
        try:
            matches = all(func(item["args"][0], item["args"][1]) == item["expected"] for item in assertions)
        except Exception:
            matches = False
        if matches:
            winners.append(token)
    if len(winners) != 1 or winners[0] == current_token:
        return None
    line = path.read_text(encoding="utf-8").splitlines()[node.body[0].lineno - 1]
    old = f"return {left_name} {current_token} {right_name}"
    new = f"return {left_name} {winners[0]} {right_name}"
    if old not in line:
        return None
    return old, new


def _denominator_edit(path: Path, node: ast.FunctionDef, assertions: list[dict[str, Any]]) -> tuple[str, str] | None:
    """Repair ``return n // k`` when every assertion wants ``k`` one step away."""

    if len(node.args.args) != 1 or len(node.body) != 1 or not isinstance(node.body[0], ast.Return):
        return None
    value = node.body[0].value
    if not isinstance(value, ast.BinOp) or not isinstance(value.op, ast.FloorDiv):
        return None
    name = node.args.args[0].arg
    if not isinstance(value.left, ast.Name) or value.left.id != name:
        return None
    if not isinstance(value.right, ast.Constant) or isinstance(value.right.value, bool):
        return None
    if not isinstance(value.right.value, int):
        return None
    if not assertions or any(len(item["args"]) != 1 or isinstance(item["args"][0], bool) for item in assertions):
        return None
    current = int(value.right.value)
    winners: list[int] = []
    for candidate in (current - 1, current + 1):
        if candidate == 0:
            continue
        try:
            matches = all(operator.floordiv(item["args"][0], candidate) == item["expected"] for item in assertions)
        except Exception:
            matches = False
        if matches:
            winners.append(candidate)
    if len(winners) != 1 or winners[0] == current:
        return None
    line = path.read_text(encoding="utf-8").splitlines()[node.body[0].lineno - 1]
    old = f"return {name} // {current}"
    new = f"return {name} // {winners[0]}"
    if old not in line:
        return None
    return old, new


def _parity_edit(path: Path, node: ast.FunctionDef, assertions: list[dict[str, Any]]) -> tuple[str, str] | None:
    """Repair ``return n % 2 == 0`` when the assertions want the other residue."""

    if len(node.args.args) != 1 or len(node.body) != 1 or not isinstance(node.body[0], ast.Return):
        return None
    value = node.body[0].value
    if not isinstance(value, ast.Compare) or len(value.ops) != 1 or not isinstance(value.ops[0], ast.Eq):
        return None
    if len(value.comparators) != 1 or not isinstance(value.comparators[0], ast.Constant):
        return None
    bit = value.comparators[0].value
    if bit not in (0, 1) or isinstance(bit, bool):
        return None
    mod = value.left
    if not isinstance(mod, ast.BinOp) or not isinstance(mod.op, ast.Mod):
        return None
    name = node.args.args[0].arg
    if not isinstance(mod.left, ast.Name) or mod.left.id != name:
        return None
    if not isinstance(mod.right, ast.Constant) or mod.right.value != 2:
        return None
    if not assertions or any(len(item["args"]) != 1 for item in assertions):
        return None
    flipped = 0 if bit == 1 else 1
    try:
        matches = all(((item["args"][0] % 2) == flipped) == item["expected"] for item in assertions)
    except Exception:
        matches = False
    if not matches:
        return None
    line = path.read_text(encoding="utf-8").splitlines()[node.body[0].lineno - 1]
    old = f"return {name} % 2 == {bit}"
    new = f"return {name} % 2 == {flipped}"
    if old not in line:
        return None
    return old, new


def _names_in_file(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
    return names


def _distance_one(left: str, right: str) -> bool:
    if left == right or abs(len(left) - len(right)) > 1:
        return False
    if len(left) == len(right):
        return sum(a != b for a, b in zip(left, right)) == 1
    longer, shorter = (left, right) if len(left) > len(right) else (right, left)
    for index in range(len(longer)):
        if longer[:index] + longer[index + 1 :] == shorter:
            return True
    return False


def _rank_repair_paths(paths: list[str]) -> list[str]:
    """A path that keeps failing goes last. Every path stays in the list."""

    from aureon.core.organism_circulation import repair_priority

    ranked = repair_priority(list(paths))
    if len(ranked) != len(paths) or set(ranked) != set(paths):
        return list(paths)
    return ranked


def _name_error_edit(root: Path, output: str, hints: list[str] | None = None) -> tuple[str, str, str] | None:
    match = re.search(r"NameError: name '([A-Za-z_][A-Za-z0-9_]*)' is not defined", output)
    if not match:
        return None
    missing = match.group(1)
    root_resolved = root.resolve()
    seen: list[Path] = []
    for raw in re.findall(r"(?m)^(?:E\s+)?(.+?\.py):\d+:", output):
        candidate = Path(raw.strip())
        if not candidate.is_absolute():
            candidate = root / candidate
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved == root_resolved or root_resolved not in resolved.parents:
            continue
        if resolved.name.startswith("test_") or resolved in seen:
            continue
        seen.append(resolved)
    order = _rank_repair_paths([path.relative_to(root_resolved).as_posix() for path in seen])
    rank = {path: index for index, path in enumerate(order)}
    seen.sort(key=lambda path: rank.get(path.relative_to(root_resolved).as_posix(), len(order)))
    for path in seen:
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (OSError, SyntaxError):
            continue
        if not re.search(rf"\b{re.escape(missing)}\b", source):
            continue
        names = _names_in_file(tree)
        candidates = [name for name in names if _distance_one(missing, name)]
        if len(candidates) != 1:  # Python's own "Did you mean" or her research may name it; still gate-proven
            candidates = [name for name in (hints or []) if name in names and name != missing][:1]
        if len(candidates) != 1:
            continue
        if len(re.findall(rf"\b{re.escape(missing)}\b", source)) != 1:
            continue
        return path.relative_to(root_resolved).as_posix(), missing, candidates[0]
    return None


def _failing_py_files(root: Path, output: str) -> list[Path]:
    """Non-test .py files named in the traceback frames, nearest-frame first."""

    root_resolved = root.resolve()
    seen: list[Path] = []
    for raw in re.findall(r"(?m)^(?:E\s+)?(.+?\.py):\d+:", output):
        candidate = Path(raw.strip())
        if not candidate.is_absolute():
            candidate = root / candidate
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved == root_resolved or root_resolved not in resolved.parents:
            continue
        if resolved.name.startswith("test_") or resolved in seen:
            continue
        seen.append(resolved)
    return seen


def _dotted_module(root: Path, path: Path) -> str:
    relative = path.resolve().relative_to(root.resolve()).as_posix()
    if relative.endswith("/__init__.py"):
        relative = relative[: -len("/__init__.py")]
    elif relative.endswith(".py"):
        relative = relative[: -len(".py")]
    return relative.replace("/", ".")


def _repo_definitions(root: Path, name: str, exclude: set[Path]) -> list[str]:
    """Dotted modules that define a top-level `def`/`class` called `name`.

    Only importable callables and types count, and the pinned public mirror,
    tests and vendored snapshots are skipped so an edit never cites them.
    """

    root_resolved = root.resolve()
    skip_parts = {".git", "__pycache__", "state", "queen_backups", ".venv",
                  "node_modules", "imports", "mcp"}
    found: list[str] = []
    for path in sorted(root_resolved.rglob("*.py")):
        if any(part in skip_parts for part in path.parts):
            continue
        if path.name.startswith("test_") or path.resolve() in exclude:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name:
                found.append(_dotted_module(root_resolved, path))
                break
    return sorted(set(found))


def _already_imports(tree: ast.AST, name: str) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if (alias.asname or alias.name) == name:
                    return True
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if (alias.asname or alias.name.split(".")[0]) == name:
                    return True
    return False


def _missing_import_edit(root: Path, output: str, blocked: set[str] | None = None):
    """A `NameError` for a name defined, uniquely, in one other repo module.

    When the name has no close spelling match in the failing file (so a rename
    is wrong) but exactly one non-test module defines a top-level `def`/`class`
    of that exact name, the fix is a missing import: add `from <module> import
    <name>`. Returns (relative, old_anchor, new_anchor). Deterministic: a single
    defining module and a single, unambiguous insertion point, or nothing.
    """

    match = re.search(r"NameError: name '([A-Za-z_][A-Za-z0-9_]*)' is not defined", output)
    if not match:
        return None
    missing = match.group(1)
    blocked = blocked or set()
    for path in _failing_py_files(root, output):
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (OSError, SyntaxError):
            continue
        if not re.search(rf"\b{re.escape(missing)}\b", source):
            continue
        if _already_imports(tree, missing):
            continue
        # A close spelling match in-file is a rename job, not a missing import.
        if any(_distance_one(missing, name) for name in _names_in_file(tree)):
            continue
        modules = _repo_definitions(root, missing, exclude={path.resolve()})
        if len(modules) != 1:
            continue
        import_stmt = f"from {modules[0]} import {missing}"
        lines = source.splitlines()
        import_rows = [i for i, ln in enumerate(lines)
                       if re.match(r"^(import |from )\S", ln)]
        anchor = lines[import_rows[-1]] if import_rows else (lines[0] if lines else "")
        if not anchor or source.count(anchor + "\n") + source.count(anchor) < 1:
            continue
        if lines.count(anchor) != 1:  # the insertion point must be unambiguous
            continue
        if import_rows:
            new_anchor = anchor + "\n" + import_stmt
        else:
            new_anchor = import_stmt + "\n" + anchor
        relative = path.resolve().relative_to(root.resolve()).as_posix()
        change = f"+{import_stmt}"
        if f"{relative}::{change}" in blocked:
            continue
        return relative, anchor, new_anchor, change
    return None


def _attribute_close_match_edit(root: Path, output: str, blocked: set[str] | None = None):
    """An `AttributeError: module 'm' has no attribute 'X'` with one close match.

    When module `m` has exactly one top-level name a single edit-distance from
    `X`, and the access `.X` appears exactly once in the nearest non-test frame,
    the fix is a renamed attribute: rewrite that one `.X` to `.Y`. Deterministic:
    a single close match and a single occurrence, or nothing.
    """

    match = re.search(r"AttributeError: module '([\w.]+)' has no attribute '([A-Za-z_][A-Za-z0-9_]*)'", output)
    if not match:
        return None
    module_name, bad = match.group(1), match.group(2)
    blocked = blocked or set()
    module_path = root / (module_name.replace(".", "/") + ".py")
    if not module_path.is_file():
        module_path = root / module_name.replace(".", "/") / "__init__.py"
    if not module_path.is_file():
        return None
    try:
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return None
    top: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            top.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    top.add(target.id)
    candidates = [name for name in top if _distance_one(bad, name)]
    if len(candidates) != 1:
        return None
    good = candidates[0]
    for path in _failing_py_files(root, output):
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if len(re.findall(rf"\.{re.escape(bad)}\b", source)) != 1:
            continue
        relative = path.resolve().relative_to(root.resolve()).as_posix()
        change = f".{bad} -> .{good}"
        if f"{relative}::{change}" in blocked:
            continue
        return relative, f".{bad}", f".{good}", change
    return None


_MISSING_FILE = re.compile(r"FileNotFoundError: \[Errno 2\] No such file or directory: '([^']+)'")


def _cwd_relative_missing(root: Path, output: str) -> list[str]:
    """Relative paths a FileNotFoundError names that DO exist under the repo root.

    Such a failure is not a missing file: the test read a cwd-relative path after
    something earlier in the same process changed the working directory. The file
    is there; only the reader depends on the process cwd.
    """

    found: list[str] = []
    root_resolved = root.resolve()
    for raw in _MISSING_FILE.findall(output or ""):
        if not raw or Path(raw).is_absolute() or ".." in Path(raw).parts:
            continue
        try:
            candidate = (root_resolved / raw).resolve()
        except OSError:
            continue
        if root_resolved not in candidate.parents or not candidate.exists():
            continue
        if raw not in found:
            found.append(raw)
    return found


def _offset(lines: list[str], lineno: int, col: int) -> int:
    """Character offset of an AST (1-based line, UTF-8 byte column) position."""

    before = sum(len(line) for line in lines[: lineno - 1])
    return before + len(lines[lineno - 1].encode("utf-8")[:col].decode("utf-8", errors="ignore"))


def _cwd_anchor_edit(root: Path, output: str, blocked: set[str] | None = None):
    """Anchor a test's cwd-relative ``Path("<rel>")`` read at the repo root.

    Shape: ``FileNotFoundError: ... '<rel>'`` where ``<rel>`` is a relative path
    that exists under the repo root, raised by a failing test whose own function
    builds it as ``Path("<rel>")``. The minimal honest fix is to make that read
    independent of the process cwd: ``(Path(__file__).resolve().parents[k] /
    "<rel>")`` where ``parents[k]`` is the repo root. Every sibling
    ``Path("<literal>")`` in the same test function that is also a relative path
    existing under the root is anchored the same way (one test, one reason).
    Nothing else changes: the same file is read and every assertion stays.
    Returns (relative_test_file, old_function_text, new_function_text, change).
    """

    missing = _cwd_relative_missing(root, output)
    if not missing:
        return None
    blocked = blocked or set()
    root_resolved = root.resolve()
    nodeids = re.findall(r"(?m)^(?:FAILED|ERROR)\s+(\S+?\.py)::(\S+)", output or "")
    for test_file, rest in nodeids:
        func_name = re.sub(r"\[.*$", "", rest.split("::")[-1])
        path = (root_resolved / test_file).resolve()
        if root_resolved not in path.parents or not path.is_file():
            continue
        relative = path.relative_to(root_resolved).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        funcs = [node for node in ast.walk(tree)
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name]
        if len(funcs) != 1:
            continue
        func = funcs[0]
        calls = []
        for node in ast.walk(func):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Path"):
                continue
            if len(node.args) != 1 or node.keywords:
                continue
            arg = node.args[0]
            if not (isinstance(arg, ast.Constant) and isinstance(arg.value, str)):
                continue
            value = arg.value
            if not value or Path(value).is_absolute() or ".." in Path(value).parts:
                continue
            if not (root_resolved / value).exists():
                continue
            calls.append((node, value))
        if not calls or not any(value in missing for _node, value in calls):
            continue
        depth = len(Path(relative).parts) - 1
        if depth < 0 or path.parents[depth] != root_resolved:
            continue
        lines = source.splitlines(keepends=True)
        start = _offset(lines, func.lineno, func.col_offset)
        end = _offset(lines, func.end_lineno, func.end_col_offset)
        old = source[start:end]
        if not old or source.count(old) != 1:
            continue
        new = old
        for node, value in sorted(calls, key=lambda item: (item[0].lineno, item[0].col_offset), reverse=True):
            a = _offset(lines, node.lineno, node.col_offset) - start
            b = _offset(lines, node.end_lineno, node.end_col_offset) - start
            new = new[:a] + f"(Path(__file__).resolve().parents[{depth}] / {json.dumps(value)})" + new[b:]
        if new == old:
            continue
        change = "anchor cwd-relative Path(" + ", ".join(sorted({value for _n, value in calls})) + ")"
        if f"{relative}::{change}" in blocked:
            continue
        return relative, old, new, change
    return None


def _refuse_edit(root: Path, relative: str, old: str, new: str) -> str | None:
    path = root / relative
    try:
        previous = path.read_text(encoding="utf-8") if path.is_file() else ""
    except OSError:
        return "credential_path"
    if old not in previous:
        return None
    updated = previous.replace(old, new, 1)
    return block_reason_for_write(relative, updated, previous, root)


def _apply_or_refuse(root: Path, architect: Any, relative: str, old: str, new: str,
                     kind: str, change: str, extra: dict | None = None) -> dict[str, Any] | None:
    refused = _refuse_edit(root, relative, old, new)
    if refused:
        return {"path": relative, "kind": kind, "change": change, "refused": refused, "human_review": True}
    if architect.apply_edit(relative, old, new, backup=True):
        result = {"path": relative, "kind": kind, "change": change}
        if extra:
            result.update(extra)
        return result
    return None


def _attempt(root: Path, output: str, architect: Any, hints: list[str] | None = None,
             blocked: set[str] | None = None) -> dict[str, Any] | None:
    blocked = blocked or set()
    name_edit = _name_error_edit(root, output, hints)
    if name_edit:
        relative, missing, replacement = name_edit
        change = f"{missing} -> {replacement}"
        if f"{relative}::{change}" not in blocked:
            result = _apply_or_refuse(root, architect, relative, missing, replacement, "name_error", change)
            if result is not None:
                return result
    # A name defined elsewhere in the repo but not imported here: add the one import.
    import_edit = _missing_import_edit(root, output, blocked)
    if import_edit:
        relative, old, new, change = import_edit
        result = _apply_or_refuse(root, architect, relative, old, new, "missing_import", change)
        if result is not None:
            return result
    # A renamed module attribute with one close match among the module's own symbols.
    attr_edit = _attribute_close_match_edit(root, output, blocked)
    if attr_edit:
        relative, old, new, change = attr_edit
        result = _apply_or_refuse(root, architect, relative, old, new, "attribute_rename", change)
        if result is not None:
            return result
    # A FileNotFoundError for a file that exists: the test's read depends on the process cwd.
    cwd_edit = _cwd_anchor_edit(root, output, blocked)
    if cwd_edit:
        relative, old, new, change = cwd_edit
        result = _apply_or_refuse(root, architect, relative, old, new, "cwd_anchor", change)
        if result is not None:
            return result
    failing = _failing_tests(output)
    assertions = _assertions(root, failing or None)
    by_function: dict[str, list[dict[str, Any]]] = {}
    for item in assertions:
        by_function.setdefault(item["function"], []).append(item)
    candidates: list[tuple[str, str, str, str]] = []
    for function_name, group in by_function.items():
        located = _function(root, function_name)
        if located is None:
            continue
        path, node = located
        relative = path.relative_to(root).as_posix()
        edit = (
            _literal_return_edit(path, node, group)
            or _operator_edit(path, node, group)
            or _denominator_edit(path, node, group)
            or _parity_edit(path, node, group)
        )
        if edit is None:
            continue
        old, new = edit
        candidates.append((relative, old, new, function_name))
    order = _rank_repair_paths([item[0] for item in candidates])
    rank = {path: index for index, path in enumerate(order)}
    candidates.sort(key=lambda item: rank.get(item[0], len(order)))
    for relative, old, new, function_name in candidates:
        if f"{relative}::{old} -> {new}" in blocked:
            continue
        refused = _refuse_edit(root, relative, old, new)
        if refused:
            return {
                "path": relative,
                "kind": "implementation",
                "change": f"{old} -> {new}",
                "refused": refused,
                "human_review": True,
            }
        applied = architect.apply_edit(relative, old, new, backup=True)
        if not applied:
            continue
        proof = by_function.get(function_name, [])  # the assertions that proved it; authors her regression test
        return {"path": relative, "kind": "implementation", "change": f"{old} -> {new}", "proof": proof}
    return None


def repair_sandbox(root: Path) -> dict[str, Any]:
    """Repair a project in place; a suite timeout becomes a held report, never a crash.

    Disk hygiene runs at the end of every cycle (owner 12:30), even on crash or timeout, so a
    stale base-temp dir can never be left behind to fill the disk.
    """
    root = Path(root).resolve()
    try:
        return _repair_sandbox(root)
    except SuiteTimedOut as exc:
        branch = (_git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout or "").strip()
        append_review(root, "repair_held", reason="suite_timed_out", branch=branch, timeout_s=exc.args[0])
        return {"schema": SCHEMA, "root": str(root), "live_trading": False, "may_act": False,
                "edited_test": False, "status": "held", "reason": "suite_timed_out",
                "timeout_s": exc.args[0], "branch": branch, "repairs": []}
    finally:
        try:
            from aureon.autonomous import queen_repair_cleaner as cleaner
            cleaner.clean_cycle(root)
        except Exception:
            pass



def _try_model_fix(root: Path, report: dict[str, Any], gate: Any, architect: Any,
                   census_before: dict[str, dict[str, int]], red_before: set[str],
                   branch: str) -> dict[str, Any] | None:
    """Opt-in (AUREON_QUEEN_REPAIR_CODER=1): let Aureon's own coding organ author a diff for a
    failing test and prove it through the same gate and no-regression rule. None => not taken."""
    try:
        from aureon.autonomous import queen_repair_coder as coder
    except Exception:
        return None
    if not coder.coder_enabled():
        return None
    records = report.get("_diagnosis_records") or []
    if not records:
        return None
    findings = report.get("_findings_by_test") or {}
    try:
        delta = coder.attempt_model_fixes(
            root, records, gate=gate, architect=architect, pytest_fn=_pytest,
            census_before=census_before, red_before=red_before, branch=branch,
            findings_by_test=findings,
        )
    except Exception as exc:
        report["model_fix_error"] = f"{type(exc).__name__}: {exc}"[:300]
        return None
    if delta.get("status") == "repaired":
        report.update(delta)
        return report
    report["coder_backend"] = delta.get("coder_backend")
    return None


def _repair_sandbox(root: Path) -> dict[str, Any]:
    """Repair a project in place. Edits implementations only, then retests."""

    root = root.resolve()
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "root": str(root),
        "live_trading": False,
        "may_act": False,
        "edited_test": False,
        "status": "held",
        "repairs": [],
    }
    try:
        require_self_repair_enabled(root)
    except SelfRepairBlocked as exc:
        append_review(root, "repair_refused", reason=exc.reason, human_review=False)
        report["reason"] = exc.reason
        return report
    branch = _prepare_branch(root)
    report["branch"] = branch
    architect = load_architect()(repo_path=str(root))
    # Disk guard (owner 12:30): if free space is low, clean first and skip the suite rather than crash.
    from aureon.autonomous import queen_repair_cleaner as cleaner
    space = cleaner.ensure_space(root)
    report["free_bytes"] = space["free_bytes"]
    if not space["ok"]:
        report.update({"status": "held", "reason": "low_disk"})
        append_review(root, "repair_held", reason="low_disk", branch=branch,
                      free_bytes=space["free_bytes"])
        return report
    before = _pytest(root)
    report["before_returncode"] = before.returncode
    if before.returncode == 0:
        report["status"] = "already_passing"
        report["reason"] = "tests_already_passed"
        append_review(root, "repair_skipped", reason="tests_already_passed", branch=branch)
        return report
    output = (before.stdout or "") + "\n" + (before.stderr or "")
    from aureon.autonomous import queen_benchmark_gate as gate

    census_before = gate.census_tests(root)
    red_before = gate.failed_nodeids(before.stdout or "")
    hints: list[str] = []
    try:  # diagnosis per failing test, plus opt-in read-only research (AUREON_QUEEN_REPAIR_WEB=1)
        from aureon.autonomous import queen_repair_research as research

        diagnosis = research.diagnose(root, output)
        findings = research.research(root, diagnosis)
        research.write_diagnosis(root, diagnosis, findings)
        hints = [name for record in diagnosis for name in research.hinted_names(record, findings)]
        findings_by_test = {f["test_id"]: " ".join(s.get("summary", "") for s in f.get("sources", []))[:600]
                            for f in findings}
        report.update({"failures": len(diagnosis), "diagnosis": research.compact(diagnosis),
                       "research": [{"test": f["test_id"], "sources": len(f["sources"])} for f in findings],
                       "hints": hints[:10], "_diagnosis_records": diagnosis,
                       "_findings_by_test": findings_by_test})
    except Exception as exc:  # diagnosis must never stop the repair
        report["diagnosis_error"] = f"{type(exc).__name__}: {exc}"[:300]
    def _finalize(after: subprocess.CompletedProcess[str]) -> dict[str, Any]:
        """Verify the accumulated repairs through the gate and commit, or revert as unverified.

        Proven = the benchmark gate verifies (seed benchmarks pass, the authored test is red
        before and green after, nothing weakened) AND no previously-passing test regressed.
        The whole suite need not pass; unrelated pre-existing failures are left alone.
        """
        paths = sorted({item["path"] for item in report["repairs"] if item.get("path")})
        verdict = gate.verify_repair(root, census_before=census_before, red_before=red_before,
                                     repairs=report["repairs"], architect=architect)
        report["gate"] = verdict
        report["regressions"] = []
        targets_green = bool(red_before - prev_failed)
        if not (verdict["verified"] and targets_green):
            # Not fully provable (gate unverified, or only a narrowing with no target yet green).
            # Drop any authored test, then try to land it as partial progress (owner's call,
            # 11:54 GMT): at least one previously-failing test now passes or a failure's error
            # narrowed, with zero regressions, and the benchmark gate still holds (seed benchmarks
            # pass, nothing weakened). Otherwise revert, no commit.
            if verdict.get("authored_test"):
                (root / verdict["authored_test"]).unlink(missing_ok=True)
                verdict["authored_test"] = None
            if (cycle_fixed or cycle_narrowed) and verdict["seed_benchmarks"]["ok"] and not verdict["weakened"]:
                _git(root, "add", *paths)
                commit = _git(root, "commit", "-m",
                              "self-repair (partial: progress, no regressions, gate holds): " + ", ".join(paths))
                head = _git(root, "rev-parse", "--short", "HEAD")
                report.update({
                    "status": "repaired_partial", "reason": "partial_progress",
                    "commit": (head.stdout or "").strip(), "commit_ok": commit.returncode == 0,
                    "after_returncode": after.returncode, "paths": paths,
                    "path": paths[0] if len(paths) == 1 else "",
                    "fixed": sorted(cycle_fixed), "narrowed": cycle_narrowed,
                })
                append_review(root, "repair_committed_partial", reason=report["reason"], branch=branch,
                              path=",".join(paths), commit=report["commit"], fixed=sorted(cycle_fixed),
                              narrowed=len(cycle_narrowed), seed_benchmarks=verdict["seed_benchmarks"])
                return report
            _git(root, "checkout", "--", *paths)
            reason = ",".join(verdict["reasons"]) or "no_proven_repair"
            report.update({"status": "unverified", "reason": reason, "paths": paths})
            append_review(root, "repair_unverified", reason=reason, branch=branch,
                          path=",".join(paths), gate=verdict)
            return report
        if verdict.get("authored_test"):
            report["authored_test"] = verdict["authored_test"]
        _git(root, "add", *paths, *([verdict["authored_test"]] if verdict.get("authored_test") else []))
        commit = _git(root, "commit", "-m", "self-repair (gate-verified, no regressions): " + ", ".join(paths))
        head = _git(root, "rev-parse", "--short", "HEAD")
        report.update(
            {
                "status": "repaired",
                "reason": "retested_on_branch",
                "commit": (head.stdout or "").strip(),
                "commit_ok": commit.returncode == 0,
                "after_returncode": after.returncode,
                "path": paths[0] if len(paths) == 1 else "",
                "paths": paths,
            }
        )
        if len(paths) == 1 and report["repairs"]:
            change = report["repairs"][0].get("change", "")
            parts = change.split(" -> ")
            if len(parts) == 2 and parts[0].startswith("return ") and parts[1].startswith("return "):
                try:
                    report["previous_return"] = ast.literal_eval(parts[0][len("return ") :])
                    report["repaired_return"] = ast.literal_eval(parts[1][len("return ") :])
                except (SyntaxError, ValueError):
                    pass
        append_review(
            root,
            "repair_committed",
            reason=report["reason"],
            branch=branch,
            path=",".join(paths),
            commit=report["commit"],
            tests_passed=True,
            verified=True,
            authored_test=report.get("authored_test"),
            seed_benchmarks=verdict["seed_benchmarks"],
        )
        return report

    from aureon.autonomous import queen_repair_progress as progress
    blocked: set[str] = set(progress.reverted_changes(root))
    cycle_attempts: list[dict[str, Any]] = []
    cycle_fixed: set[str] = set()
    cycle_narrowed: list[dict[str, Any]] = []

    def _exc_map(combined: str) -> dict[str, str]:
        try:
            from aureon.autonomous import queen_repair_research as research
            return {r["test_id"]: r.get("exception", "") for r in research.diagnose(root, combined)}
        except Exception:
            return {}

    prev_failed: set[str] = set(red_before)
    prev_exc = _exc_map(output)

    def _log_cycle(committed: bool, reason: str) -> None:
        progress.record_cycle(root, fixed=sorted(cycle_fixed), narrowed=cycle_narrowed,
                              attempts=cycle_attempts, committed=committed, reason=reason)

    def _finalize_and_log(after: subprocess.CompletedProcess[str]) -> dict[str, Any]:
        result = _finalize(after)
        _log_cycle(result.get("status") in {"repaired", "repaired_partial"}, result.get("reason", ""))
        return result

    # Diagnosis-derived maps: which failing test points at which source file (for scoping a
    # fast, targeted re-test per candidate rather than the whole suite).
    diagnosis_records = report.get("_diagnosis_records", []) or []
    suspect_map = {r["test_id"]: r.get("suspected_file", "") for r in diagnosis_records}
    tb_text = {r["test_id"]: " ".join(r.get("traceback_tail", []))[:2000] for r in diagnosis_records}
    base_exc = {r["test_id"]: r.get("exception", "") for r in diagnosis_records} or dict(prev_exc)
    work_exc = dict(base_exc)  # phase 1 updates this as fixes land; base_exc stays the baseline
    refusals: list[dict[str, Any]] = []

    def _targets_for(relative: str) -> list[str]:
        """Originally-red tests that point at this source file (suspect or in the traceback)."""
        hits = [t for t in red_before
                if suspect_map.get(t) == relative or relative in tb_text.get(t, "")]
        if not hits:  # fall back to a same-named test module, e.g. aureon/x/foo.py -> test_foo.py
            stem = Path(relative).stem
            hits = [t for t in red_before if Path(t.split("::")[0]).stem in {f"test_{stem}", stem}]
        return sorted(set(hits))

    _skip = {".git", "__pycache__", ".venv", "node_modules", "queen_backups", "state"}

    def _module_test_files(relative: str) -> list[str]:
        stem = Path(relative).stem
        files: list[str] = []
        if stem:
            for path in root.rglob("test_*.py"):
                if any(part in _skip for part in path.parts):
                    continue
                if stem in path.stem:
                    files.append(path.relative_to(root).as_posix())
        return sorted(set(files))

    def _fast_scope(relative: str, targets: list[str]) -> list[str]:
        # Whole test files, not single nodeids, so a sibling test in the same file catches a
        # regression fast (owner 12:20: targeted test(s) PLUS that file's/module's tests).
        files = set(_module_test_files(relative)) | {t.split("::")[0] for t in targets}
        return sorted(files)[:12]

    def _fast_run(scope: list[str]) -> tuple[set[str], dict[str, str]]:
        try:
            done = gate._pytest_paths(root, scope, timeout=_fast_timeout_s())
        except subprocess.TimeoutExpired:
            return set(), {}
        out = (done.stdout or "") + "\n" + (done.stderr or "")
        return gate.failed_nodeids(done.stdout or ""), _exc_map(out)

    def _slice(rec: dict[str, Any]) -> str:
        body = "\n".join(rec.get("traceback_tail", []))
        return f"FAILED {rec['test_id']} - {rec.get('error', '')}\n{body}\n"

    # ── Phase 1: one candidate per failing test, each proved against only its targeted/module
    # tests (seconds). Many candidates per cycle, under a wall-clock budget (owner 12:20). ──
    remaining = [r for r in diagnosis_records if r.get("test_id") in red_before]
    if not remaining:
        remaining = [{"test_id": t, "error": "", "traceback_tail": [], "exception": ""}
                     for t in sorted(red_before)]
    deadline = time.monotonic() + _inner_budget_s()
    candidates = 0
    for rec in remaining:
        if candidates >= MAX_CANDIDATES or time.monotonic() > deadline:
            break
        try:
            attempt = _attempt(root, _slice(rec), architect, hints, blocked)
        except SelfRepairBlocked as exc:
            report["reason"] = exc.reason
            append_review(root, "repair_refused", reason=exc.reason, branch=branch)
            _log_cycle(False, exc.reason)
            return report
        if not attempt:
            continue
        candidates += 1
        if attempt.get("refused"):
            # A refused edit (a live-flag/gate/credential guard) is flagged for human review; its
            # change is never applied. Keep trying other failures and surface it if nothing lands.
            refusals.append(attempt)
            cycle_attempts.append({"path": attempt.get("path"), "kind": attempt.get("kind"),
                                   "change": attempt.get("change"), "result": "refused",
                                   "refused": attempt["refused"]})
            append_review(root, "human_review_required", reason=attempt["refused"], branch=branch,
                          path=attempt.get("path", ""), human_review=True)
            continue
        relative = attempt.get("path", "")
        blocked.add(f"{relative}::{attempt.get('change', '')}")  # never re-pick the same edit
        targets = sorted(set(_targets_for(relative)) | {rec["test_id"]})
        fast_failed, fast_exc = _fast_run(_fast_scope(relative, targets))
        # No-regression rule, fast scope (owner 10:43): a scoped test that was green must not go red.
        fast_regressions = sorted(fast_failed - red_before)
        if fast_regressions:
            architect.restore_backup(relative)
            cycle_attempts.append({"path": relative, "kind": attempt.get("kind"),
                                   "change": attempt.get("change"), "result": "reverted_regression",
                                   "regressions": fast_regressions})
            append_review(root, "repair_reverted", reason="regression", branch=branch,
                          path=relative, regressions=fast_regressions)
            continue
        this_fixed = sorted(t for t in targets if t not in fast_failed)
        this_narrowed = [{"test": t, "from": work_exc.get(t, ""), "to": fast_exc.get(t, "")}
                         for t in targets if t in fast_failed
                         and progress.is_narrower(work_exc.get(t, ""), fast_exc.get(t, ""))]
        if not (this_fixed or this_narrowed):
            architect.restore_backup(relative)
            cycle_attempts.append({"path": relative, "kind": attempt.get("kind"),
                                   "change": attempt.get("change"), "result": "reverted_inert"})
            continue
        # Bank the fix. Its backup stays, so later edits layer on top; the final suite confirms it.
        report["repairs"].append(attempt)
        cycle_attempts.append({"path": relative, "kind": attempt.get("kind"),
                               "change": attempt.get("change"), "result": "kept",
                               "fixed": this_fixed, "narrowed": [n["test"] for n in this_narrowed]})
        cleaner.clean_cycle(root)  # housekeep right after a fix is banked (owner 12:30)
        for t in this_fixed:
            work_exc[t] = ""
        for n in this_narrowed:
            work_exc[n["test"]] = n["to"]

    # Repair-priority order (a path that keeps failing goes last); also the order bisect drops in.
    order = _rank_repair_paths([item["path"] for item in report["repairs"] if item.get("path")])
    _rank = {path: index for index, path in enumerate(order)}
    report["repairs"].sort(key=lambda item: _rank.get(item.get("path", ""), len(order)))

    if not report["repairs"] and refusals:
        # Nothing landed and at least one edit was a safety-refused change: surface for human review.
        report.update({"status": "human_review", "human_review": True,
                       "reason": refusals[0]["refused"], "path": refusals[0].get("path", "")})
        _log_cycle(False, report["reason"])
        return report

    if not report["repairs"]:
        model = _try_model_fix(root, report, gate, architect, census_before, red_before, branch)
        if model is not None:
            _log_cycle(model.get("status") == "repaired", model.get("reason", ""))
            return model
        report["reason"] = "no_proven_repair"
        append_review(root, "repair_held", reason=report["reason"], branch=branch)
        _log_cycle(False, report["reason"])
        return report

    # ── Phase 2: ONE full suite confirms no regression across all banked fixes. If one appears,
    # bisect by reverting the most-recently banked patch and retry, keeping the rest (owner 12:20). ──
    full = _pytest(root)
    full_failed = gate.failed_nodeids(full.stdout or "")
    if sorted(full_failed - red_before) and report["repairs"]:
        # A regression spans the banked set. Isolate the offending patch by reverting one at a
        # time (newest first), keeping every patch that is not the culprit (owner 12:20). Snapshot
        # each banked file so an innocent revert is put straight back.
        banked_content: dict[str, bytes | None] = {}
        for item in report["repairs"]:
            try:
                banked_content[item["path"]] = (root / item["path"]).read_bytes()
            except OSError:
                banked_content[item["path"]] = None
        culprit = None
        for index in range(len(report["repairs"]) - 1, -1, -1):
            if len(report["repairs"]) - 1 - index >= BISECT_MAX:
                break
            path = report["repairs"][index]["path"]
            architect.restore_backup(path)
            trial = _pytest(root)
            trial_failed = gate.failed_nodeids(trial.stdout or "")
            if not sorted(trial_failed - red_before):
                culprit, full, full_failed = index, trial, trial_failed
                break
            # Not the (sole) culprit: put its fix back and try the next patch.
            if banked_content.get(path) is not None:
                (root / path).write_bytes(banked_content[path])
        if culprit is not None:
            dropped = report["repairs"].pop(culprit)
            blocked.add(f"{dropped['path']}::{dropped.get('change', '')}")
            cycle_attempts.append({"path": dropped.get("path"), "kind": dropped.get("kind"),
                                   "change": dropped.get("change"), "result": "reverted_bisect"})
            append_review(root, "repair_reverted", reason="full_suite_regression", branch=branch,
                          path=dropped.get("path"))

    full_output = (full.stdout or "") + "\n" + (full.stderr or "")
    if sorted(full_failed - red_before) or not report["repairs"]:
        # Could not isolate a clean set: revert everything that is left, commit nothing.
        for item in report["repairs"]:
            architect.restore_backup(item["path"])
        _git(root, "checkout", "--", ".")
        report["repairs"] = []
        report.update({"status": "unverified", "reason": "full_suite_regression"})
        append_review(root, "repair_unverified", reason=report["reason"], branch=branch)
        _log_cycle(False, report["reason"])
        return report

    # Clean full suite (zero regressions). Recompute the banked outcome from the authoritative run.
    final_exc = _exc_map(full_output)
    prev_failed = set(full_failed)
    cycle_fixed = set(sorted(red_before - full_failed))
    cycle_narrowed = [{"test": t, "from": base_exc.get(t, ""), "to": final_exc.get(t, "")}
                      for t in sorted(red_before & full_failed)
                      if progress.is_narrower(base_exc.get(t, ""), final_exc.get(t, ""))]
    report["full_suite_regressions"] = []
    # Say so when a banked fix touched a test file (a cwd anchor); assertions are never changed.
    report["edited_test"] = any(item.get("kind") == "cwd_anchor" for item in report["repairs"])
    return _finalize_and_log(full)

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Repair a Python project from its own tests.")
    parser.add_argument("--root", required=True, help="Project directory to repair. Tests must be pytest.")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if not root.is_dir():
        print(json.dumps({"ok": False, "reason": "root_not_found", "root": str(root)}))
        return 2
    report = repair_sandbox(root)
    printable = {k: v for k, v in report.items() if not k.startswith("_")}
    print(json.dumps(printable, indent=2, sort_keys=True, default=str))
    return 0 if report["status"] in {"repaired", "already_passing"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
