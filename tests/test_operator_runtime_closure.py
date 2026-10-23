import ast
import importlib.util
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
MODULE = ROOT / "deployment/google-cloud/operator_runtime_closure.py"
SPEC = importlib.util.spec_from_file_location("operator_runtime_closure", MODULE)
closure = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(closure)


def minimal_tree(*extra: str) -> list[str]:
    return [
        "aureon-os-upstream/aureon/__init__.py",
        "aureon-os-upstream/aureon/operator/__init__.py",
        "aureon-os-upstream/aureon/operator/operator_server.py",
        *extra,
    ]


def rows_for(paths: tuple[str, ...] | list[str]) -> list[dict]:
    return [
        {"path": path, "sha256": f"{index + 1:064x}"[-64:], "size": index + 1}
        for index, path in enumerate(paths)
    ]


def _tracked_python_modules(paths: list[str]) -> tuple[dict[str, str], dict[str, str]]:
    """Mirror the release unit's three PYTHONPATH roots without importing code."""
    module_to_path: dict[str, str] = {}
    path_to_module: dict[str, str] = {}
    roots = (
        "deployment/google-cloud/",
        "",
        "aureon-os-upstream/",
    )
    for prefix in roots:
        for path in paths:
            if not path.endswith(".py") or prefix and not path.startswith(prefix):
                continue
            if not prefix and (
                path.startswith("deployment/google-cloud/")
                or path.startswith("aureon-os-upstream/")
            ):
                continue
            relative = path[len(prefix):] if prefix else path
            parts = relative[:-3].split("/")
            if parts[-1] == "__init__":
                parts.pop()
            if not parts or any(not part.isidentifier() for part in parts):
                continue
            module = ".".join(parts)
            module_to_path.setdefault(module, path)
            path_to_module.setdefault(path, module)
    return module_to_path, path_to_module


def _literal_imports(tree: ast.AST, *, module: str, is_package: bool) -> set[str]:
    package = module if is_package else module.rpartition(".")[0]
    imports: set[str] = set()
    for node in ast.walk(tree):
        candidates: list[str] = []
        if isinstance(node, ast.Import):
            candidates.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                if not package:
                    continue
                try:
                    base = importlib.util.resolve_name(
                        "." * node.level + base, package
                    )
                except (ImportError, ValueError):
                    continue
            if base:
                candidates.append(base)
            candidates.extend(
                f"{base}.{alias.name}" if base else alias.name
                for alias in node.names
                if alias.name != "*"
            )
        elif isinstance(node, ast.Call) and node.args:
            function = node.func
            is_dynamic_import = (
                isinstance(function, ast.Name) and function.id == "__import__"
            ) or (
                isinstance(function, ast.Attribute)
                and function.attr == "import_module"
            )
            first = node.args[0]
            if is_dynamic_import and isinstance(first, ast.Constant) and isinstance(
                first.value, str
            ):
                dynamic = first.value
                if dynamic.startswith(".") and package:
                    try:
                        dynamic = importlib.util.resolve_name(dynamic, package)
                    except (ImportError, ValueError):
                        continue
                candidates.append(dynamic)
        imports.update(candidate for candidate in candidates if candidate)
    return imports


def _checkout_package_prefixes(tracked: list[str]) -> tuple[str, ...]:
    """Release pin first, then the live ``aureon/`` tree when that is the checkout."""
    prefixes: list[str] = []
    if any(path.startswith(closure.OPERATOR_PACKAGE_PREFIX) for path in tracked):
        prefixes.append(closure.OPERATOR_PACKAGE_PREFIX)
    if any(path.startswith("aureon/") for path in tracked):
        prefixes.append("aureon/")
    return tuple(prefixes)


def _recursive_repo_local_imports(tracked: list[str]) -> set[str]:
    module_to_path, path_to_module = _tracked_python_modules(tracked)
    prefixes = _checkout_package_prefixes(tracked)
    pending = [
        path
        for path in tracked
        if path.endswith(".py") and any(path.startswith(prefix) for prefix in prefixes)
    ]
    reached = set(pending)
    while pending:
        path = pending.pop()
        module = path_to_module[path]
        tree = ast.parse((ROOT / path).read_bytes(), filename=path)
        for imported in _literal_imports(
            tree, module=module, is_package=path.endswith("/__init__.py")
        ):
            candidate = imported
            while candidate:
                dependency = module_to_path.get(candidate)
                if dependency is not None:
                    if dependency not in reached:
                        reached.add(dependency)
                        pending.append(dependency)
                    break
                candidate = candidate.rpartition(".")[0]
    return reached


def _tracked_package_inventory() -> tuple[list[str], str]:
    """Classify the pinned prefix when it is populated, otherwise the live tree.

    ``OPERATOR_PACKAGE_PREFIX`` stays ``aureon-os-upstream/aureon/``. This
    checkout keeps the package at ``aureon/``.
    """
    pinned = subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "ls-files",
            "--",
            "aureon-os-upstream/aureon",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    tracked = pinned.stdout.splitlines()
    if tracked:
        return tracked, closure.OPERATOR_PACKAGE_PREFIX
    live = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "--", "aureon"],
        check=True,
        capture_output=True,
        text=True,
    )
    tracked = [path for path in live.stdout.splitlines() if path.startswith("aureon/")]
    return tracked, "aureon/"


def test_current_git_tree_classifies_every_tracked_package_file():
    tracked, prefix = _tracked_package_inventory()
    sources = set(
        closure.operator_package_runtime_sources(tracked, package_prefix=prefix)
    )
    assets = {
        prefix + path[len(closure.OPERATOR_PACKAGE_PREFIX) :]
        for path in closure.OPERATOR_PACKAGE_ASSETS
    }
    runtime_state = {
        prefix + path[len(closure.OPERATOR_PACKAGE_PREFIX) :]
        for path in closure.OPERATOR_PACKAGE_RUNTIME_STATE
    }
    expected = {
        path
        for path in tracked
        if path.endswith(".py") or path in assets
    }
    assert sources == expected
    assert sources.isdisjoint(runtime_state)
    assert len(sources) > 1_000  # A short maintained import list must never pass.


def _declared_companion_path(path: str) -> str:
    """Map a live checkout path onto the release companion name when aliased.

    The prefix pin stays ``aureon-os-upstream/``. This checkout stores those
    same modules at the repository root.
    """
    aliased = "aureon-os-upstream/" + path
    if aliased in closure.OPERATOR_COMPANION_SOURCES:
        return aliased
    return path


def _companion_is_in_checkout(path: str, tracked: set[str]) -> bool:
    if path in tracked:
        return True
    prefix = "aureon-os-upstream/"
    if path.startswith(prefix) and path[len(prefix) :] in tracked:
        return True
    return False


def test_every_tracked_package_import_resolves_inside_the_declared_closure():
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "--", "*.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    tracked = result.stdout.splitlines()
    tracked_set = set(tracked)
    reached = _recursive_repo_local_imports(tracked)
    prefixes = _checkout_package_prefixes(tracked)
    outside_package = {
        _declared_companion_path(path)
        for path in reached
        if not any(path.startswith(prefix) for prefix in prefixes)
    }
    missing = outside_package - set(closure.OPERATOR_COMPANION_SOURCES) - set(
        closure.OPERATOR_DEPLOYMENT_SOURCES
    )
    assert missing == set()
    # Every companion present in this checkout is a demonstrated static/literal
    # dependency. New broad sibling-directory inclusions must not silently
    # expand this VM read plane. The release prefix pin is unchanged.
    demonstrated = {
        path
        for path in closure.OPERATOR_COMPANION_SOURCES
        if _companion_is_in_checkout(path, tracked_set)
    }
    assert outside_package - set(closure.OPERATOR_DEPLOYMENT_SOURCES) == demonstrated


def test_unknown_package_asset_fails_closed_but_named_state_stays_out():
    with pytest.raises(
        closure.OperatorRuntimeClosureError,
        match="unclassified_operator_package_asset",
    ):
        closure.operator_package_runtime_sources(
            minimal_tree("aureon-os-upstream/aureon/operator/unreviewed.dat")
        )

    tracked = minimal_tree(*closure.OPERATOR_PACKAGE_RUNTIME_STATE)
    sources = set(closure.operator_package_runtime_sources(tracked))
    assert sources.isdisjoint(closure.OPERATOR_PACKAGE_RUNTIME_STATE)


def test_manifest_binds_complete_sources_and_payload_hashes():
    tracked = minimal_tree("aureon-os-upstream/aureon/operator/dependency.py")
    required = closure.required_operator_runtime_sources(tracked)
    rows = rows_for(required)
    tree = "b" * 40
    manifest = closure.build_operator_runtime_manifest(
        tracked, rows, source_git_tree=tree
    )
    assert manifest["files"] == len(required)
    assert manifest["sources"] == list(required)
    assert closure.validate_operator_runtime_manifest(
        manifest, rows, source_git_tree=tree
    ) == frozenset(required)

    tampered = dict(manifest)
    tampered["payload_sha256"] = "0" * 64
    with pytest.raises(
        closure.OperatorRuntimeClosureError,
        match="operator_runtime_manifest_digest_invalid",
    ):
        closure.validate_operator_runtime_manifest(
            tampered, rows, source_git_tree=tree
        )


def test_manifest_rejects_missing_source_and_selected_runtime_state():
    tracked = minimal_tree()
    required = closure.required_operator_runtime_sources(tracked)
    rows = rows_for(required)
    with pytest.raises(
        closure.OperatorRuntimeClosureError,
        match="complete_operator_runtime_sources_required",
    ):
        closure.build_operator_runtime_manifest(
            tracked, rows[:-1], source_git_tree="b" * 40
        )

    state = next(iter(closure.OPERATOR_PACKAGE_RUNTIME_STATE))
    with pytest.raises(
        closure.OperatorRuntimeClosureError,
        match="operator_runtime_state_selection_forbidden",
    ):
        closure.build_operator_runtime_manifest(
            tracked,
            [*rows, {"path": state, "sha256": "f" * 64, "size": 1}],
            source_git_tree="b" * 40,
        )


def test_stale_operator_python_sources_only_reports_old_code(tmp_path):
    workspace = tmp_path / "workspace"
    package = workspace / "aureon-os-upstream/aureon"
    (package / "operator").mkdir(parents=True)
    current = package / "operator/operator_server.py"
    stale = package / "operator/deleted_dependency.py"
    adjacent_cache = package / "operator/deleted_dependency.pyc"
    tagged_cache = package / "operator/__pycache__/operator_server.cpython-312.pyc"
    state = package / "data_feeds/crypto_market_map_cache.json"
    state.parent.mkdir(parents=True)
    tagged_cache.parent.mkdir(parents=True)
    current.write_text("VALUE = 'current'\n", encoding="utf-8")
    stale.write_text("VALUE = 'old'\n", encoding="utf-8")
    adjacent_cache.write_bytes(b"old bytecode")
    tagged_cache.write_bytes(b"cached bytecode")
    state.write_text("{}\n", encoding="utf-8")

    assert closure.stale_operator_python_sources(
        workspace, [closure.OPERATOR_ENTRYPOINT]
    ) == ("aureon-os-upstream/aureon/operator/deleted_dependency.py",)
    assert closure.operator_python_cache_files(workspace) == (
        "aureon-os-upstream/aureon/operator/__pycache__/operator_server.cpython-312.pyc",
        "aureon-os-upstream/aureon/operator/deleted_dependency.pyc",
    )
    assert stale.exists()  # Discovery is side-effect free; the updater owns removal.


def test_operator_trigger_is_specific_to_operator_not_ui_bundle():
    assert closure.operator_runtime_requested([closure.OPERATOR_ENTRYPOINT])
    assert closure.operator_runtime_requested(
        ["deployment/google-cloud/cloud_operator.py"]
    )
    assert not closure.operator_runtime_requested(
        [
            "deployment/google-cloud/cloud_http_runtime.py",
            "deployment/google-cloud/cloud_ui_gateway.py",
        ]
    )
