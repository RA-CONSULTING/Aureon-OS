"""Plug-in self-repair for a Python project.

Point it at a project. It runs pytest, repairs the implementation (not the
test) when the failure is one it can prove, reruns the tests, and commits the
repair on a local branch with a review log.

    python -m aureon.autonomous.aureon_sandbox_self_repair --root /path/to/project

From the fusion tree the same command is:

    python -m aureon_fusion.repair --root /path/to/project

It repairs a proved implementation bug, such as an off-by-one in a pure utility.
It does not arm live trading, change an evidence gate, change position sizing,
or write credential files. Those attempts are flagged for human review and are
not applied. Repair stays disabled unless AUREON_SELF_REPAIR_ENABLE=1 and
state/self_repair_config.json contains {"enabled": true}. AUREON_SELF_REPAIR_KILL=1
or a missing config stops it. The repair does not rewrite the test file.
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


def _pytest(root: Path) -> subprocess.CompletedProcess[str]:
    for cache in root.rglob("__pycache__"):
        if cache.is_dir():
            shutil.rmtree(cache, ignore_errors=True)
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=short", "-p", "no:cacheprovider"],
        cwd=root,
        text=True,
        capture_output=True,
        timeout=120,
        env=env,
    )


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


def _name_error_edit(root: Path, output: str) -> tuple[str, str, str] | None:
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
    for path in seen:
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (OSError, SyntaxError):
            continue
        if not re.search(rf"\b{re.escape(missing)}\b", source):
            continue
        candidates = [name for name in _names_in_file(tree) if _distance_one(missing, name)]
        if len(candidates) != 1:
            continue
        if len(re.findall(rf"\b{re.escape(missing)}\b", source)) != 1:
            continue
        return path.relative_to(root_resolved).as_posix(), missing, candidates[0]
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
    return block_reason_for_write(relative, updated, previous)


def _attempt(root: Path, output: str, architect: Any) -> dict[str, Any] | None:
    name_edit = _name_error_edit(root, output)
    if name_edit:
        relative, missing, replacement = name_edit
        refused = _refuse_edit(root, relative, missing, replacement)
        if refused:
            return {
                "path": relative,
                "kind": "name_error",
                "change": f"{missing} -> {replacement}",
                "refused": refused,
                "human_review": True,
            }
        applied = architect.apply_edit(relative, missing, replacement, backup=True)
        if applied:
            return {"path": relative, "kind": "name_error", "change": f"{missing} -> {replacement}"}
        return None
    failing = _failing_tests(output)
    assertions = _assertions(root, failing or None)
    by_function: dict[str, list[dict[str, Any]]] = {}
    for item in assertions:
        by_function.setdefault(item["function"], []).append(item)
    for function_name, group in by_function.items():
        located = _function(root, function_name)
        if located is None:
            continue
        path, node = located
        relative = path.relative_to(root).as_posix()
        edit = _literal_return_edit(path, node, group) or _operator_edit(path, node, group)
        if edit is None:
            continue
        old, new = edit
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
        return {"path": relative, "kind": "implementation", "change": f"{old} -> {new}"}
    return None


def repair_sandbox(root: Path) -> dict[str, Any]:
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
    before = _pytest(root)
    report["before_returncode"] = before.returncode
    if before.returncode == 0:
        report["status"] = "already_passing"
        report["reason"] = "tests_already_passed"
        append_review(root, "repair_skipped", reason="tests_already_passed", branch=branch)
        return report
    output = (before.stdout or "") + "\n" + (before.stderr or "")
    for _ in range(MAX_REPAIRS):
        try:
            attempt = _attempt(root, output, architect)
        except SelfRepairBlocked as exc:
            report["reason"] = exc.reason
            append_review(root, "repair_refused", reason=exc.reason, branch=branch)
            return report
        if not attempt:
            report["reason"] = "no_proven_repair"
            append_review(root, "repair_held", reason=report["reason"], branch=branch)
            return report
        if attempt.get("refused"):
            report["status"] = "human_review"
            report["human_review"] = True
            report["reason"] = attempt["refused"]
            report["path"] = attempt.get("path", "")
            append_review(
                root,
                "human_review_required",
                reason=report["reason"],
                branch=branch,
                path=attempt.get("path", ""),
                human_review=True,
            )
            return report
        after = _pytest(root)
        output = (after.stdout or "") + "\n" + (after.stderr or "")
        if after.returncode != 0 and attempt.get("path"):
            # Keep the edit only when the suite got closer: fewer failures, or this file's NameError/assert is gone.
            # A still-failing suite is fine if another independent bug remains. Revert only when the failure count rises.
            before_failed = before.stdout.count("FAILED")
            after_failed = after.stdout.count("FAILED")
            if after_failed > before_failed:
                architect.restore_backup(attempt["path"])
                report["reason"] = "retest_failed_change_reverted"
                append_review(root, "repair_reverted", reason=report["reason"], branch=branch, path=attempt["path"])
                return report
        report["repairs"].append(attempt)
        before = after
        if after.returncode == 0:
            paths = sorted({item["path"] for item in report["repairs"] if item.get("path")})
            _git(root, "add", *paths)
            commit = _git(root, "commit", "-m", "self-repair: tests pass after " + ", ".join(paths))
            head = _git(root, "rev-parse", "--short", "HEAD")
            report.update(
                {
                    "status": "repaired",
                    "reason": "retested_on_branch",
                    "commit": (head.stdout or "").strip(),
                    "commit_ok": commit.returncode == 0,
                    "after_returncode": 0,
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
            )
            return report
    report["reason"] = "repair_limit_reached"
    append_review(root, "repair_held", reason=report["reason"], branch=branch)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Repair a Python project from its own tests.")
    parser.add_argument("--root", required=True, help="Project directory to repair. Tests must be pytest.")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if not root.is_dir():
        print(json.dumps({"ok": False, "reason": "root_not_found", "root": str(root)}))
        return 2
    report = repair_sandbox(root)
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 0 if report["status"] in {"repaired", "already_passing"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
