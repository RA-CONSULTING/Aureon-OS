"""Suite-quarantine markers have to say why the test is out of the default run."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUARANTINE_MARKERS = {"live", "windows", "skip", "skipif", "xfail"}


def _stated(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return bool(node.value.strip())
    if isinstance(node, ast.JoinedStr) and node.values:
        return True
    return isinstance(node, (ast.Name, ast.Attribute, ast.Call, ast.BinOp, ast.IfExp))


def test_quarantined_markers_state_a_reason() -> None:
    missing: list[str] = []
    for path in (ROOT / "tests").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            attr = node.func.attr
            if attr not in QUARANTINE_MARKERS:
                continue
            owner = node.func.value
            is_mark = isinstance(owner, ast.Attribute) and owner.attr == "mark"
            is_pytest_skip = attr == "skip" and isinstance(owner, ast.Name) and owner.id == "pytest"
            if not is_mark and not is_pytest_skip:
                continue
            reasons = [kw.value for kw in node.keywords if kw.arg == "reason"]
            stated = any(_stated(reason) for reason in reasons)
            if not stated and is_pytest_skip and node.args:
                stated = _stated(node.args[0])
            if not stated:
                rel = path.relative_to(ROOT)
                missing.append(f"{rel}:{node.lineno} @{attr}")
    assert missing == [], missing
