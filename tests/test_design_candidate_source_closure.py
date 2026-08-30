from __future__ import annotations

import ast
import copy
import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from aureon.operator import design_candidate_motion_policy_compiler as motion_compiler
from aureon.operator import design_candidate_source_closure as source_closure
from aureon.operator import design_candidate_test_policy_compiler as test_compiler

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_ast_closure_is_exact_and_records_all_bounded_runtime_exclusions() -> None:
    manifest = source_closure.build_source_closure(REPO_ROOT)

    source_closure.require_source_closure_contract(manifest)
    assert source_closure.verify_source_closure(REPO_ROOT, manifest) == manifest
    paths = [str(row["path"]) for row in manifest["files"]]
    assert len(paths) == 15
    assert "aureon/__init__.py" in paths
    assert "aureon/operator/__init__.py" in paths
    assert source_closure.SOURCE_CLOSURE_HELPER_PATH in paths
    assert "aureon/operator/design_editorial_asset_candidate_importer.py" in paths
    assert "aureon/operator/design_editorial_asset_provenance.py" in paths
    assert [row["kind"] for row in manifest["exclusions"]] == [
        "bounded-dormant-lazy-export",
        "bounded-dormant-lazy-export",
        "runtime-dead-type-checking-branch",
        "bounded-dormant-lazy-export",
    ]


@pytest.mark.parametrize(
    "unsafe",
    [
        "../source.py",
        "aureon/operator/../source.py",
        "aureon\\operator\\source.py",
        "aureon/operator/source.py:payload",
        "/aureon/operator/source.py",
    ],
)
def test_raw_source_reader_rejects_alias_and_alternate_stream_paths(
    tmp_path: Path,
    unsafe: str,
) -> None:
    with pytest.raises(
        source_closure.DesignCandidateSourceClosureError,
        match="canonical|aliased|alternate data stream|safe",
    ):
        source_closure.read_bound_source_file(
            tmp_path,
            unsafe,
            label="Unsafe source",
        )


def test_raw_source_reader_rejects_hard_links(tmp_path: Path) -> None:
    source = tmp_path / "aureon" / "operator" / "source.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    alias = tmp_path / "source-alias.py"
    try:
        os.link(source, alias)
    except OSError as exc:
        pytest.skip(f"Hard links are unavailable: {exc}")

    with pytest.raises(
        source_closure.DesignCandidateSourceClosureError,
        match="exactly one hard link",
    ):
        source_closure.read_bound_source_file(
            tmp_path,
            "aureon/operator/source.py",
            label="Hard-linked source",
        )


def test_contract_rejects_missing_extra_and_raw_different_rows() -> None:
    manifest = source_closure.build_source_closure(REPO_ROOT)

    missing = copy.deepcopy(manifest)
    missing["files"].pop()
    with pytest.raises(source_closure.DesignCandidateSourceClosureError):
        source_closure.require_source_closure_contract(missing)

    extra = copy.deepcopy(manifest)
    extra["unknown"] = True
    with pytest.raises(source_closure.DesignCandidateSourceClosureError):
        source_closure.require_source_closure_contract(extra)

    raw_different = copy.deepcopy(manifest)
    raw_different["files"][0]["sha256"] = "0" * 64
    with pytest.raises(source_closure.DesignCandidateSourceClosureError):
        source_closure.verify_source_closure(REPO_ROOT, raw_different)


def test_ast_closure_resolves_import_module_aliases_and_rejects_nonliteral_targets(
    tmp_path: Path,
) -> None:
    for relative in (
        "aureon/__init__.py",
        "aureon/operator/__init__.py",
        "aureon/operator/probe.py",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("VALUE = 1\n", encoding="utf-8")
    literal = ast.parse(
        "from importlib import import_module as load_local\nload_local('aureon.operator.probe')\n"
    )
    targets, exclusions = source_closure._local_import_targets(  # noqa: SLF001
        literal,
        current_relative="aureon/operator/caller.py",
        repo_root=tmp_path,
    )
    assert targets == {
        "aureon/__init__.py",
        "aureon/operator/__init__.py",
        "aureon/operator/probe.py",
    }
    assert exclusions == []

    nonliteral = ast.parse(
        "from importlib import import_module as load_local\n"
        "module_name = 'aureon.operator.probe'\n"
        "load_local(module_name)\n"
    )
    with pytest.raises(
        source_closure.DesignCandidateSourceClosureError,
        match="not a literal module name",
    ):
        source_closure._local_import_targets(  # noqa: SLF001
            nonliteral,
            current_relative="aureon/operator/caller.py",
            repo_root=tmp_path,
        )


def test_ast_context_walk_is_linear_and_preserves_nested_type_guard_semantics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for relative in (
        "aureon/__init__.py",
        "aureon/operator/__init__.py",
        "aureon/operator/runtime_probe.py",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("VALUE = 1\n", encoding="utf-8")
    tree = ast.parse(
        "from typing import TYPE_CHECKING\n"
        "import typing\n"
        "if TYPE_CHECKING:\n"
        "    import missing.outer_direct\n"
        "    if FEATURE:\n"
        "        import missing.outer_nested\n"
        "    if typing.TYPE_CHECKING:\n"
        "        import missing.inner\n"
        "    else:\n"
        "        import missing.outer_inner_else\n"
        "else:\n"
        "    import aureon.operator.runtime_probe\n"
    )
    node_count = len(list(ast.walk(tree)))
    original_iter_child_nodes = ast.iter_child_nodes
    child_iteration_count = 0

    def counted_iter_child_nodes(node: ast.AST) -> Iterator[ast.AST]:
        nonlocal child_iteration_count
        child_iteration_count += 1
        return original_iter_child_nodes(node)

    monkeypatch.setattr(source_closure.ast, "iter_child_nodes", counted_iter_child_nodes)

    targets, exclusions = source_closure._local_import_targets(  # noqa: SLF001
        tree,
        current_relative="aureon/operator/caller.py",
        repo_root=tmp_path,
    )

    assert child_iteration_count == node_count
    assert targets == {
        "aureon/__init__.py",
        "aureon/operator/__init__.py",
        "aureon/operator/runtime_probe.py",
    }
    assert exclusions == [
        {
            "path": "aureon/operator/caller.py",
            "line": 3,
            "kind": "runtime-dead-type-checking-branch",
            "targets": [
                "missing.outer_direct",
                "missing.outer_inner_else",
                "missing.outer_nested",
            ],
            "reason": "TYPE_CHECKING is false during compiler receipt replay",
        },
        {
            "path": "aureon/operator/caller.py",
            "line": 7,
            "kind": "runtime-dead-type-checking-branch",
            "targets": ["missing.inner"],
            "reason": "TYPE_CHECKING is false during compiler receipt replay",
        },
    ]


def test_operator_lazy_export_rejects_non_body_and_eager_execution_shapes(tmp_path: Path) -> None:
    lazy_map = (
        "_LAZY_EXPORTS = {\n"
        "    'a': ('aureon.operator.aureon_operator', 'a'),\n"
        "    'b': ('aureon.operator.cognition', 'b'),\n"
        "    'c': ('aureon.operator.schemas', 'c'),\n"
        "}\n"
        "module_name = 'aureon.operator.design_candidate_claim_surface'\n"
    )
    unsafe_sources = {
        "default": (
            "from importlib import import_module\n"
            + lazy_map
            + "def __getattr__(value=import_module(module_name)):\n    return value\n"
        ),
        "decorator": (
            "from importlib import import_module\n"
            + lazy_map
            + "@import_module(module_name)\ndef __getattr__(name):\n    return name\n"
        ),
        "wrapping-decorator": (
            "from importlib import import_module\n"
            + lazy_map
            + "def decorate(function):\n    return function\n"
            "@decorate\n"
            "def __getattr__(name):\n    return import_module(module_name)\n"
        ),
        "class-method": (
            "from importlib import import_module\n" + lazy_map + "class Trigger:\n"
            "    def __getattr__(self, name):\n"
            "        return import_module(module_name)\n"
            "Trigger().__getattr__('run-now')\n"
        ),
        "nested-function": (
            "from importlib import import_module\n" + lazy_map + "def __getattr__(name):\n"
            "    def nested():\n"
            "        return import_module(module_name)\n"
            "    return nested()\n"
        ),
        "eager-invocation": (
            "import importlib\n" + lazy_map + "def __getattr__(name):\n"
            "    return importlib.import_module(module_name)\n"
            "__getattr__('run-now')\n"
        ),
        "aliased-eager-invocation": (
            "import importlib\n" + lazy_map + "def __getattr__(name):\n"
            "    return importlib.import_module(module_name)\n"
            "run_lazy = __getattr__\n"
            "run_lazy('run-now')\n"
        ),
    }

    for source in unsafe_sources.values():
        with pytest.raises(
            source_closure.DesignCandidateSourceClosureError,
            match="literal module name|invoked",
        ):
            source_closure._local_import_targets(  # noqa: SLF001
                ast.parse(source),
                current_relative="aureon/operator/__init__.py",
                repo_root=tmp_path,
            )


def test_type_checking_exclusion_requires_unshadowed_module_binding(tmp_path: Path) -> None:
    shadowed_sources = (
        "from typing import TYPE_CHECKING\nTYPE_CHECKING = True\n"
        "if TYPE_CHECKING:\n    import aureon.operator.probe\n",
        "from typing import TYPE_CHECKING\n"
        "def probe(TYPE_CHECKING=True):\n"
        "    if TYPE_CHECKING:\n        import aureon.operator.probe\n",
        "import typing\ntyping = object()\nif typing.TYPE_CHECKING:\n    import aureon.operator.probe\n",
        "import typing\ntyping.TYPE_CHECKING = True\n"
        "if typing.TYPE_CHECKING:\n    import aureon.operator.probe\n",
        "import typing\nsetattr(typing, 'TYPE_CHECKING', True)\n"
        "if typing.TYPE_CHECKING:\n    import aureon.operator.probe\n",
    )

    for source in shadowed_sources:
        with pytest.raises(
            source_closure.DesignCandidateSourceClosureError,
            match="unshadowed module-level typing binding",
        ):
            source_closure._local_import_targets(  # noqa: SLF001
                ast.parse(source),
                current_relative="aureon/operator/caller.py",
                repo_root=tmp_path,
            )


def test_type_checking_exclusion_records_literal_dynamic_import_and_rejects_nonliteral(
    tmp_path: Path,
) -> None:
    literal = ast.parse(
        "from typing import TYPE_CHECKING\n"
        "from importlib import import_module\n"
        "if TYPE_CHECKING:\n"
        "    import_module('aureon.operator.dynamic_probe')\n"
    )

    targets, exclusions = source_closure._local_import_targets(  # noqa: SLF001
        literal,
        current_relative="aureon/operator/caller.py",
        repo_root=tmp_path,
    )

    assert targets == set()
    assert exclusions == [
        {
            "path": "aureon/operator/caller.py",
            "line": 3,
            "kind": "runtime-dead-type-checking-branch",
            "targets": ["aureon.operator.dynamic_probe"],
            "reason": "TYPE_CHECKING is false during compiler receipt replay",
        }
    ]

    nonliteral = ast.parse(
        "from typing import TYPE_CHECKING\n"
        "from importlib import import_module\n"
        "module_name = 'aureon.operator.dynamic_probe'\n"
        "if TYPE_CHECKING:\n"
        "    import_module(module_name)\n"
    )
    with pytest.raises(
        source_closure.DesignCandidateSourceClosureError,
        match="TYPE_CHECKING dynamic import is not a literal module name",
    ):
        source_closure._local_import_targets(  # noqa: SLF001
            nonliteral,
            current_relative="aureon/operator/caller.py",
            repo_root=tmp_path,
        )


def test_dynamic_import_aliases_and_nontrivial_builtin_import_are_rejected(tmp_path: Path) -> None:
    unsafe_sources = (
        "import builtins\nload = builtins.__import__\nload('aureon.operator.probe')\n",
        "load, = (__import__,)\nload('aureon.operator.probe')\n",
        "from importlib import import_module as load\nindirect = load\nindirect('aureon.operator.probe')\n",
        "import builtins\nload = getattr(builtins, '__import__')\nload('aureon.operator.probe')\n",
        "__import__('aureon.operator', fromlist=['probe'])\n",
    )

    for source in unsafe_sources:
        with pytest.raises(source_closure.DesignCandidateSourceClosureError):
            source_closure._local_import_targets(  # noqa: SLF001
                ast.parse(source),
                current_relative="aureon/operator/caller.py",
                repo_root=tmp_path,
            )


def test_exact_single_argument_builtin_import_is_closed_over(tmp_path: Path) -> None:
    for relative in (
        "aureon/__init__.py",
        "aureon/operator/__init__.py",
        "aureon/operator/probe.py",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("VALUE = 1\n", encoding="utf-8")

    targets, exclusions = source_closure._local_import_targets(  # noqa: SLF001
        ast.parse("__import__('aureon.operator.probe')\n"),
        current_relative="aureon/operator/caller.py",
        repo_root=tmp_path,
    )

    assert targets == {
        "aureon/__init__.py",
        "aureon/operator/__init__.py",
        "aureon/operator/probe.py",
    }
    assert exclusions == []


def test_operator_lazy_export_map_is_evaluated_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tree = ast.parse(
        "import importlib\n"
        "_LAZY_EXPORTS = {\n"
        "    'a': ('aureon.operator.aureon_operator', 'a'),\n"
        "    'b': ('aureon.operator.cognition', 'b'),\n"
        "    'c': ('aureon.operator.schemas', 'c'),\n"
        "}\n"
        "def __getattr__(name):\n"
        "    module_name = _LAZY_EXPORTS[name][0]\n"
        "    if name == 'a':\n"
        "        importlib.import_module(module_name)\n"
        "    return importlib.import_module(module_name)\n"
    )
    original_literal_eval = ast.literal_eval
    evaluation_count = 0

    def counted_literal_eval(node: ast.AST) -> object:
        nonlocal evaluation_count
        evaluation_count += 1
        return original_literal_eval(node)

    monkeypatch.setattr(source_closure.ast, "literal_eval", counted_literal_eval)

    targets, exclusions = source_closure._local_import_targets(  # noqa: SLF001
        tree,
        current_relative="aureon/operator/__init__.py",
        repo_root=tmp_path,
    )

    assert targets == set()
    assert len(exclusions) == 2
    assert evaluation_count == 1


def test_module_resolution_rejects_module_package_ambiguity(tmp_path: Path) -> None:
    module = tmp_path / "aureon" / "operator" / "ambiguous.py"
    package = tmp_path / "aureon" / "operator" / "ambiguous" / "__init__.py"
    module.parent.mkdir(parents=True)
    package.parent.mkdir(parents=True)
    module.write_text("VALUE = 1\n", encoding="utf-8")
    package.write_text("VALUE = 2\n", encoding="utf-8")

    with pytest.raises(
        source_closure.DesignCandidateSourceClosureError,
        match="ambiguous module and package",
    ):
        source_closure._module_relative(  # noqa: SLF001
            "aureon.operator.ambiguous",
            tmp_path,
        )


@pytest.mark.parametrize(
    ("reader", "error"),
    [
        (
            test_compiler._bootstrap_read_file,  # noqa: SLF001
            test_compiler.DesignCandidateTestPolicyCompilerError,
        ),
        (
            motion_compiler._bootstrap_read_file,  # noqa: SLF001
            motion_compiler.DesignCandidateMotionPolicyCompilerError,
        ),
    ],
)
def test_compiler_bootstraps_reject_case_aliased_paths(
    tmp_path: Path,
    reader: object,
    error: type[Exception],
) -> None:
    source = tmp_path / "aureon" / "operator" / "source.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")

    with pytest.raises(error, match="case-aliased"):
        reader(  # type: ignore[operator]
            tmp_path,
            tmp_path / "AUREON" / "operator" / "source.py",
            label="Case-aliased bootstrap source",
        )
