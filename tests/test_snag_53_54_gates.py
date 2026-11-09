"""Snag 53 and snag 54.

Snag 53: a live capital ALLOW names the lift that actually happened. Exchange
keys do not lift it. A truncated, empty, or unparseable mode file is guarded.
Full stays the default when the mode file is absent.

Snag 54: the brain and the plumber both call the shared coherence check before
the queen sees the value. Anything that is not a finite number in [0, 1] is
HOLD with no order intent, and the check does not raise.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from aureon.autonomous.autonomy_mode import MODE_ENV, autonomy_mode
from aureon.autonomous.metacognitive_coherence import (
    brain_llm_coherence,
    plumber_coherence,
)
from aureon.core.hnc_field import assess_coherence, reconcile_gamma
from aureon.operator.coherence_gate import compute_aperture

ROOT = Path(__file__).resolve().parents[1]
AUREON = ROOT / "aureon"
ALLOWLIST_PATH = Path(__file__).resolve().parent / "coherence_read_allowlist.json"
SHARED_CALLS = frozenset({
    "assess_coherence",
    "reconcile_gamma",
    "brain_llm_coherence",
    "plumber_coherence",
    "judge_coherence",
})

# Crafted rows, plus the values Gary and Spike named.
REFUSED_READINGS = (
    float("nan"),
    float("inf"),
    float("-inf"),
    None,
    -0.01,
    1.01,
    "abc",
    {"coherence": "abc"},
    True,
    False,
    [],
)


def _paths():
    return (brain_llm_coherence, plumber_coherence)


def _assert_hold(result: dict) -> None:
    assert result["verdict"] == "HOLD"
    assert result["order_intent"] is None
    assert result["queen_saw_value"] is False
    assert result.get("action") != "buy"


def test_full_mode_keys_do_not_allow_live_capital_and_do_not_claim_the_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Crafted row: FULL mode + fake Kraken key pair, no Gary flag."""

    from aureon_fusion import capability_gate as gate

    monkeypatch.setenv(MODE_ENV, "full")
    monkeypatch.delenv("AUREON_DEPLOYMENT_HOLD", raising=False)
    monkeypatch.delenv(gate.OPERATOR_TEST_SESSION_ENV, raising=False)
    monkeypatch.setenv("KRAKEN_API_KEY", "fake")
    monkeypatch.setenv("KRAKEN_API_SECRET", "fake")
    flag = tmp_path / "capital_release.flag"
    matrix = tmp_path / "capability_matrix.json"
    matrix.write_text(
        json.dumps({"gates": {gate.PINNED_GATE: {"status": "active", "level": "ELEVATE"}}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(gate, "FLAG_FILE", flag)
    monkeypatch.setattr(gate, "MATRIX_FILE", matrix)

    verdict = gate._check_verdict(gate.PINNED_GATE)

    assert verdict["verdict"] == "HOLD"
    assert verdict["allowed"] is False
    assert "pin lifted" not in verdict["reason"]
    assert "no exchange keys" not in verdict["reason"]


def test_verdict_names_the_release_flag_only_when_it_is_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aureon_fusion import capability_gate as gate

    monkeypatch.delenv("AUREON_DEPLOYMENT_HOLD", raising=False)
    monkeypatch.delenv(gate.OPERATOR_TEST_SESSION_ENV, raising=False)
    flag = tmp_path / "capital_release.flag"
    flag.write_text(gate.RELEASE_LINE + "\n", encoding="utf-8")
    matrix = tmp_path / "capability_matrix.json"
    matrix.write_text(
        json.dumps({"gates": {gate.PINNED_GATE: {"status": "active", "level": "ELEVATE"}}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(gate, "FLAG_FILE", flag)
    monkeypatch.setattr(gate, "MATRIX_FILE", matrix)

    verdict = gate._check_verdict(gate.PINNED_GATE)

    assert verdict["verdict"] == "ALLOW"
    assert verdict["allowed"] is True
    assert "pin lifted by owner decree flag" in verdict["reason"]
    assert "operator test-session record" not in verdict["reason"]


def test_verdict_names_the_operator_test_session_when_that_is_the_lift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aureon_fusion import capability_gate as gate

    monkeypatch.delenv("AUREON_DEPLOYMENT_HOLD", raising=False)
    monkeypatch.setenv(gate.OPERATOR_TEST_SESSION_ENV, "1")
    flag = tmp_path / "capital_release.flag"
    matrix = tmp_path / "capability_matrix.json"
    matrix.write_text(
        json.dumps({"gates": {gate.PINNED_GATE: {"status": "active", "level": "ELEVATE"}}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(gate, "FLAG_FILE", flag)
    monkeypatch.setattr(gate, "MATRIX_FILE", matrix)

    verdict = gate._check_verdict(gate.PINNED_GATE)

    assert verdict["verdict"] == "ALLOW"
    assert "pin lifted by operator test-session record (AUREON_OPERATOR_ALLOW_LIVE)" in verdict["reason"]
    assert "owner decree flag" not in verdict["reason"]


@pytest.mark.parametrize(
    "text",
    [
        '{"mode":"guar',
        "",
        "{",
    ],
)
def test_broken_mode_file_is_guarded_and_a_missing_file_stays_full(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, text: str
) -> None:
    monkeypatch.delenv(MODE_ENV, raising=False)
    state = tmp_path / "state"
    state.mkdir()
    (state / "autonomy_mode.json").write_text(text, encoding="utf-8")

    assert autonomy_mode(tmp_path) == "guarded"
    assert autonomy_mode(tmp_path / "no-file-here") == "full"


def test_crafted_nan_and_non_readings_hold_on_brain_and_plumber_paths() -> None:
    """Crafted row: Γ=NaN with the advisory open. Inf is the same HOLD."""

    for judge in _paths():
        for value in REFUSED_READINGS:
            result = judge(value, advisory_open=True)
            _assert_hold(result)
        for value in (float("nan"), float("inf"), float("-inf")):
            result = judge(value, advisory_open=True)
            _assert_hold(result)


def test_string_and_dict_coherence_do_not_raise() -> None:
    """Crafted row: Γ='abc' crashed. A dict coherence input must not raise either."""

    for judge in _paths():
        for value in ("abc", {"coherence": "abc"}):
            result = judge(value, advisory_open=True)
            _assert_hold(result)


def test_numpy_coherence_values_on_both_paths() -> None:
    numpy = pytest.importorskip("numpy")

    refused = (numpy.nan, numpy.True_, numpy.False_)
    for judge in _paths():
        for value in refused:
            _assert_hold(judge(value, advisory_open=True))
        accepted = judge(numpy.float32(0.5), advisory_open=True)
        assert accepted["verdict"] == "ACCEPTED"
        assert accepted["queen_saw_value"] is True
        assert accepted["coherence"] == pytest.approx(0.5)
        assert accepted["order_intent"] is None


def test_shared_check_order_rejects_bool_before_the_numeric_test() -> None:
    for value in (True, False):
        decision = assess_coherence(value)
        assert decision.verdict == "HOLD"
        assert decision.accepted is False
        assert decision.order_intent is None
        assert decision.value is None
    kept = reconcile_gamma(0.93)
    assert kept == pytest.approx(0.93)
    rejected = reconcile_gamma(float("nan"))
    assert rejected.verdict == "HOLD"
    assert rejected.order_intent is None
    assert not rejected >= 0.9


def test_crafted_nan_row_does_not_open_full_reach_or_buy() -> None:
    """Crafted row: Γ=NaN with the advisory open. The queen is not shown it.

    Inf is the same refusal. A string or a dict does not raise. A dark
    field (None at the aperture) stays the membrane's full reading; the
    order paths above still HOLD on None.
    """

    aperture = compute_aperture(float("nan"), True, None)
    assert aperture["aperture"] == "refuse"
    assert aperture["aperture"] != "full"
    assert compute_aperture(float("inf"), True, None)["aperture"] == "refuse"
    assert compute_aperture(float("-inf"), True, None)["aperture"] == "refuse"
    string_row = compute_aperture("abc", True, None)
    assert string_row["aperture"] == "refuse"
    dict_row = compute_aperture({"coherence": "abc"}, True, None)
    assert dict_row["aperture"] == "refuse"
    assert compute_aperture(None, None, None)["aperture"] == "full"
    for judge in _paths():
        for value in (float("nan"), float("inf"), "abc", {"coherence": "abc"}):
            result = judge(value, advisory_open=True)
            _assert_hold(result)


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _exec_nodes(node: ast.AST):
    """Executable nodes, skipping annotations and nested definitions."""

    for field, child in ast.iter_fields(node):
        if field in {"annotation", "returns", "type_comment"}:
            continue
        children = child if isinstance(child, list) else [child]
        for item in children:
            if not isinstance(item, ast.AST):
                continue
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            yield item
            yield from _exec_nodes(item)


def _function_reads_and_calls(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[bool, bool]:
    reads = False
    calls = False
    for arg in (
        *node.args.posonlyargs,
        *node.args.args,
        *node.args.kwonlyargs,
    ):
        if "coherence" in arg.arg.lower():
            reads = True
    if node.args.vararg is not None and "coherence" in node.args.vararg.arg.lower():
        reads = True
    if node.args.kwarg is not None and "coherence" in node.args.kwarg.arg.lower():
        reads = True
    for child in node.body:
        for item in (child, *_exec_nodes(child)):
            if isinstance(item, ast.Name) and "coherence" in item.id.lower():
                reads = True
            elif isinstance(item, ast.Attribute) and "coherence" in item.attr.lower():
                reads = True
            elif isinstance(item, ast.Subscript):
                key_node = item.slice
                if (
                    isinstance(key_node, ast.Constant)
                    and isinstance(key_node.value, str)
                    and "coherence" in key_node.value.lower()
                ):
                    reads = True
            elif isinstance(item, ast.Call):
                name = _call_name(item)
                if name in SHARED_CALLS:
                    calls = True
                if name in {"float", "int", "get"}:
                    for arg in item.args:
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and "coherence" in arg.value.lower():
                            reads = True
                        if isinstance(arg, ast.Name) and "coherence" in arg.id.lower():
                            reads = True
    return reads, calls


def _sites() -> dict[str, str]:
    found: dict[str, str] = {}

    class Visitor(ast.NodeVisitor):
        def __init__(self, file_path: str) -> None:
            self.file_path = file_path
            self.stack: list[str] = []

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def _function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            qual = ".".join([*self.stack, node.name])
            reads, calls = _function_reads_and_calls(node)
            if reads and not calls:
                found[f"{self.file_path}:{qual}"] = qual
            self.stack.append(node.name)
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    self.visit(child)
            self.stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._function(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._function(node)

    for file in AUREON.rglob("*.py"):
        file_path = file.relative_to(ROOT).as_posix()
        try:
            tree = ast.parse(file.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeError):
            continue
        Visitor(file_path).visit(tree)
    return found


def test_coherence_reads_go_through_the_shared_check() -> None:
    allowlist = json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    assert isinstance(allowlist, dict) and allowlist
    for key, reason in allowlist.items():
        assert isinstance(reason, str) and reason.strip()
        assert "\n" not in reason
    sites = _sites()
    missing = sorted(set(sites) - set(allowlist))
    assert missing == []
    stale = sorted(set(allowlist) - set(sites))
    assert stale == []
