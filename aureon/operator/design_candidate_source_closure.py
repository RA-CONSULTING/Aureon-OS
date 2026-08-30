"""Deterministic raw-byte closure for local candidate-control Python sources.

This module deliberately imports only the Python standard library. Candidate
compilers authenticate its exact raw bytes from the immutable validation input
before executing it, then use it to inspect the remaining local source graph
without importing any of those modules.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.abc
import importlib.util
import json
import os
import stat
import sys
from collections import deque
from importlib.machinery import ModuleSpec
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import Any, Mapping, Sequence

SOURCE_CLOSURE_SCHEMA = "aureon.design-candidate-executable-source-closure.v1"
SOURCE_CLOSURE_ALGORITHM = "python-ast-local-raw-sha256-closure-v2"
SOURCE_CLOSURE_HELPER_PATH = "aureon/operator/design_candidate_source_closure.py"
DEFAULT_SOURCE_CLOSURE_ROOTS = (
    "aureon/operator/design_candidate_motion_policy_compiler.py",
    SOURCE_CLOSURE_HELPER_PATH,
    "aureon/operator/design_candidate_test_policy_compiler.py",
)
SOURCE_CLOSURE_FIELDS = frozenset(
    {
        "schema",
        "algorithm",
        "roots",
        "files",
        "exclusions",
        "manifest_sha256",
    }
)
SOURCE_CLOSURE_FILE_FIELDS = frozenset({"path", "bytes", "sha256"})
SOURCE_CLOSURE_EXCLUSION_FIELDS = frozenset({"path", "line", "kind", "targets", "reason"})
_SHA256_LENGTH = 64
_REPARSE_ATTRIBUTE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


class DesignCandidateSourceClosureError(ValueError):
    """The local executable-source closure is malformed, unsafe, or stale."""


def _canonical_json_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise DesignCandidateSourceClosureError(
            "Executable-source closure contains a non-standard JSON value."
        ) from exc


def _json_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest().upper()


def _strict_json_equal(left: object, right: object) -> bool:
    try:
        return _canonical_json_bytes(left) == _canonical_json_bytes(right)
    except DesignCandidateSourceClosureError:
        return False


def _safe_relative_python_path(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise DesignCandidateSourceClosureError(f"{label} must be a canonical relative path.")
    if "\\" in value or ":" in value or value.startswith("/"):
        raise DesignCandidateSourceClosureError(
            f"{label} may not be absolute, aliased, or address an alternate data stream."
        )
    path = PurePosixPath(value)
    if (
        path.as_posix() != value
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.suffix != ".py"
    ):
        raise DesignCandidateSourceClosureError(f"{label} is not a safe canonical Python path.")
    return value


def _is_link_or_reparse(path: Path) -> bool:
    details = path.lstat()
    return stat.S_ISLNK(details.st_mode) or bool(
        int(getattr(details, "st_file_attributes", 0)) & int(_REPARSE_ATTRIBUTE)
    )


def _identity(details: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        stat.S_IFMT(details.st_mode),
        int(getattr(details, "st_dev", 0)),
        int(getattr(details, "st_ino", 0)),
        int(details.st_nlink),
        int(details.st_size),
    )


def read_bound_source_file(
    repo_root: Path,
    relative: object,
    *,
    label: str,
) -> tuple[Path, bytes]:
    """Read one lexical, ordinary, single-link source file exactly once."""

    safe = _safe_relative_python_path(relative, label=label)
    root = Path(os.path.abspath(repo_root))
    lexical = Path(os.path.abspath(root.joinpath(*PurePosixPath(safe).parts)))
    try:
        lexical.relative_to(root)
    except ValueError as exc:
        raise DesignCandidateSourceClosureError(f"{label} escapes the repository.") from exc
    try:
        root_details = root.lstat()
    except OSError as exc:
        raise DesignCandidateSourceClosureError("Executable-source repository root is missing.") from exc
    if not stat.S_ISDIR(root_details.st_mode) or _is_link_or_reparse(root):
        raise DesignCandidateSourceClosureError(
            "Executable-source repository root must be an ordinary directory."
        )
    current = root
    try:
        for part in PurePosixPath(safe).parts:
            case_matches = sorted(
                entry.name for entry in os.scandir(current) if entry.name.casefold() == part.casefold()
            )
            if case_matches != [part]:
                raise DesignCandidateSourceClosureError(
                    f"{label} has a missing or case-aliased path component."
                )
            current = current / part
            current.lstat()
            if _is_link_or_reparse(current):
                raise DesignCandidateSourceClosureError(f"{label} may not traverse a link or reparse point.")
        before = lexical.lstat()
    except OSError as exc:
        raise DesignCandidateSourceClosureError(f"{label} is missing or unreadable.") from exc
    if not stat.S_ISREG(before.st_mode) or int(before.st_nlink) != 1:
        raise DesignCandidateSourceClosureError(
            f"{label} must be an ordinary Python file with exactly one hard link."
        )
    try:
        raw = lexical.read_bytes()
        after = lexical.lstat()
    except OSError as exc:
        raise DesignCandidateSourceClosureError(f"{label} could not be read safely.") from exc
    if _identity(before) != _identity(after) or len(raw) != int(after.st_size):
        raise DesignCandidateSourceClosureError(f"{label} changed while its raw bytes were read.")
    return lexical, raw


def _module_name(relative: str) -> str:
    path = PurePosixPath(relative)
    parts = list(path.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _module_relative(module_name: str, repo_root: Path) -> str | None:
    if not module_name or any(part in {"", ".", ".."} for part in module_name.split(".")):
        return None
    module_file = PurePosixPath(*module_name.split(".")).with_suffix(".py").as_posix()
    package_file = (PurePosixPath(*module_name.split(".")) / "__init__.py").as_posix()
    module_exists = (repo_root / Path(*PurePosixPath(module_file).parts)).is_file()
    package_exists = (repo_root / Path(*PurePosixPath(package_file).parts)).is_file()
    if module_exists and package_exists:
        raise DesignCandidateSourceClosureError(
            f"Local import has ambiguous module and package targets: {module_name}"
        )
    if module_exists:
        return module_file
    if package_exists:
        return package_file
    return None


def _package_initializers(module_name: str, repo_root: Path) -> set[str]:
    parts = module_name.split(".")
    initializers: set[str] = set()
    for length in range(1, len(parts)):
        relative = (PurePosixPath(*parts[:length]) / "__init__.py").as_posix()
        if (repo_root / Path(*PurePosixPath(relative).parts)).is_file():
            initializers.add(relative)
    return initializers


def _relative_import_base(current_relative: str, module: str | None, level: int) -> str:
    current_module = _module_name(current_relative)
    current_path = PurePosixPath(current_relative)
    package_parts = current_module.split(".")
    if current_path.name != "__init__.py":
        package_parts = package_parts[:-1]
    if level < 1 or level > len(package_parts) + 1:
        raise DesignCandidateSourceClosureError(
            f"Relative import level escapes local package in {current_relative}."
        )
    base_parts = package_parts[: len(package_parts) - (level - 1)]
    if module:
        base_parts.extend(module.split("."))
    return ".".join(base_parts)


def _local_import_targets(
    tree: ast.AST,
    *,
    current_relative: str,
    repo_root: Path,
) -> tuple[set[str], list[dict[str, Any]]]:
    targets: set[str] = set()
    exclusions: list[dict[str, Any]] = []

    def is_type_checking_guard(node: ast.AST) -> bool:
        if not isinstance(node, ast.If):
            return False
        test = node.test
        return bool(
            (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING")
            or (
                isinstance(test, ast.Attribute)
                and test.attr == "TYPE_CHECKING"
                and isinstance(test.value, ast.Name)
                and test.value.id == "typing"
            )
        )

    type_checking_guards: dict[int, ast.If | None] = {}
    execution_scopes: dict[int, ast.AST | None] = {}
    parents: dict[int, ast.AST | None] = {id(tree): None}
    nodes: list[ast.AST] = []
    pending_context: deque[tuple[ast.AST, ast.If | None, ast.AST | None]] = deque([(tree, None, None)])
    while pending_context:
        node, active_guard, active_scope = pending_context.popleft()
        nodes.append(node)
        type_checking_guards[id(node)] = active_guard
        execution_scopes[id(node)] = active_scope
        guard_node = node if isinstance(node, ast.If) and is_type_checking_guard(node) else None
        guarded_body_ids = {id(child) for child in guard_node.body} if guard_node else set()
        function_body_ids = (
            {id(child) for child in node.body}
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            else set()
        )
        for child in ast.iter_child_nodes(node):
            child_guard = active_guard
            if guard_node is not None and id(child) in guarded_body_ids:
                child_guard = guard_node
            child_scope = active_scope
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if id(child) in function_body_ids:
                    child_scope = node
            elif (
                isinstance(node, ast.Lambda)
                and child is node.body
                or isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp))
            ):
                child_scope = node
            parents[id(child)] = node
            pending_context.append((child, child_guard, child_scope))

    def import_names(node: ast.AST) -> list[str]:
        if isinstance(node, ast.Import):
            return sorted(alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            prefix = "." * node.level + (node.module or "")
            if node.module:
                return sorted(f"{prefix}.{alias.name}" for alias in node.names)
            return sorted(f"{prefix}{alias.name}" for alias in node.names)
        return []

    def bound_alias_name(alias: ast.alias) -> str:
        return alias.asname or alias.name.split(".", 1)[0]

    unshadowed_binding_cache: dict[tuple[str, int], bool] = {}

    def binding_is_unshadowed(name: str, approved_alias: ast.alias) -> bool:
        cache_key = (name, id(approved_alias))
        if cache_key in unshadowed_binding_cache:
            return unshadowed_binding_cache[cache_key]
        valid = True
        for candidate in nodes:
            if isinstance(candidate, ast.alias):
                if candidate is not approved_alias and bound_alias_name(candidate) == name:
                    valid = False
                    break
            elif isinstance(candidate, ast.Name):
                if candidate.id == name and isinstance(candidate.ctx, (ast.Store, ast.Del)):
                    valid = False
                    break
            elif isinstance(candidate, ast.arg):
                if candidate.arg == name:
                    valid = False
                    break
            elif (
                isinstance(
                    candidate,
                    (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.ExceptHandler),
                )
                and candidate.name == name
            ):
                valid = False
                break
            elif isinstance(candidate, (ast.Global, ast.Nonlocal)):
                if name in candidate.names:
                    valid = False
                    break
            elif (
                (isinstance(candidate, (ast.MatchAs, ast.MatchStar)) and candidate.name == name)
                or (isinstance(candidate, ast.MatchMapping) and candidate.rest == name)
                or (
                    name == "typing"
                    and isinstance(candidate, ast.Attribute)
                    and isinstance(candidate.value, ast.Name)
                    and candidate.value.id == "typing"
                    and candidate.attr == "TYPE_CHECKING"
                    and isinstance(candidate.ctx, (ast.Store, ast.Del))
                )
                or (
                    name == "typing"
                    and isinstance(candidate, ast.Call)
                    and isinstance(candidate.func, ast.Name)
                    and candidate.func.id in {"setattr", "delattr"}
                    and len(candidate.args) >= 2
                    and isinstance(candidate.args[0], ast.Name)
                    and candidate.args[0].id == "typing"
                )
            ):
                valid = False
                break
        unshadowed_binding_cache[cache_key] = valid
        return valid

    module_body = tree.body if isinstance(tree, ast.Module) else []
    type_checking_aliases = [
        alias
        for statement in module_body
        if isinstance(statement, ast.ImportFrom) and statement.level == 0 and statement.module == "typing"
        for alias in statement.names
        if alias.name == "TYPE_CHECKING" and alias.asname is None
    ]
    typing_aliases = [
        alias
        for statement in module_body
        if isinstance(statement, ast.Import)
        for alias in statement.names
        if alias.name == "typing" and alias.asname is None
    ]

    def require_type_checking_binding(guard: ast.If) -> None:
        if isinstance(guard.test, ast.Name):
            aliases = type_checking_aliases
            name = "TYPE_CHECKING"
        else:
            aliases = typing_aliases
            name = "typing"
        if len(aliases) != 1 or not binding_is_unshadowed(name, aliases[0]):
            raise DesignCandidateSourceClosureError(
                f"TYPE_CHECKING guard has no exact unshadowed module-level typing binding in {current_relative}."
            )

    type_guards = [node for node in nodes if isinstance(node, ast.If) and is_type_checking_guard(node)]
    for type_guard in type_guards:
        require_type_checking_binding(type_guard)

    def add_module(module_name: str, *, required: bool) -> bool:
        relative = _module_relative(module_name, repo_root)
        if relative is not None:
            targets.add(relative)
            targets.update(_package_initializers(module_name, repo_root))
            return True
        if required:
            raise DesignCandidateSourceClosureError(f"Local Python import target is missing: {module_name}")
        return False

    dynamic_import_names = {"__import__"}
    forbidden_loader_names: set[str] = set()
    for node in nodes:
        if not isinstance(node, ast.ImportFrom) or node.level:
            continue
        if node.module == "importlib":
            for alias in node.names:
                if alias.name == "import_module":
                    dynamic_import_names.add(alias.asname or alias.name)
        elif node.module == "builtins":
            if any(alias.name == "__import__" for alias in node.names):
                raise DesignCandidateSourceClosureError(
                    f"Importing or aliasing __import__ is forbidden in {current_relative}."
                )
        elif node.module == "runpy":
            for alias in node.names:
                if alias.name in {"run_module", "run_path"}:
                    forbidden_loader_names.add(alias.asname or alias.name)
        elif node.module in {"importlib.util", "importlib.machinery"}:
            for alias in node.names:
                if alias.name in {
                    "SourceFileLoader",
                    "SourcelessFileLoader",
                    "spec_from_file_location",
                }:
                    forbidden_loader_names.add(alias.asname or alias.name)
    dynamic_callable_names = dynamic_import_names.union(forbidden_loader_names)
    loader_attribute_names = {
        "SourceFileLoader",
        "SourcelessFileLoader",
        "__import__",
        "import_module",
        "run_module",
        "run_path",
        "spec_from_file_location",
    }

    def is_direct_call_function(node: ast.AST) -> bool:
        parent = parents.get(id(node))
        return isinstance(parent, ast.Call) and parent.func is node

    def reflected_loader_name(node: ast.Call) -> str | None:
        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and len(node.args) >= 2
            and isinstance(node.args[1], ast.Constant)
            and isinstance(node.args[1].value, str)
            and node.args[1].value in loader_attribute_names
        ):
            return node.args[1].value
        return None

    for node in nodes:
        if (
            isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Load)
            and node.id in dynamic_callable_names
            and not is_direct_call_function(node)
        ):
            raise DesignCandidateSourceClosureError(
                f"Aliasing a dynamic Python import callable is forbidden in {current_relative}."
            )
        if (
            isinstance(node, ast.Attribute)
            and node.attr in loader_attribute_names
            and not is_direct_call_function(node)
        ):
            raise DesignCandidateSourceClosureError(
                f"Aliasing a dynamic Python loader callable is forbidden in {current_relative}."
            )
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value == "__import__"
            and not is_direct_call_function(node)
        ):
            raise DesignCandidateSourceClosureError(
                f"Aliasing a dynamic Python import callable is forbidden in {current_relative}."
            )
        if (
            isinstance(node, ast.Call)
            and reflected_loader_name(node) is not None
            and not is_direct_call_function(node)
        ):
            raise DesignCandidateSourceClosureError(
                f"Aliasing a reflected Python loader callable is forbidden in {current_relative}."
            )

    def exact_top_level_function(name: str) -> ast.FunctionDef | None:
        matches = [
            statement
            for statement in module_body
            if isinstance(statement, ast.FunctionDef) and statement.name == name
        ]
        if len(matches) != 1:
            return None
        function = matches[0]
        if (
            function.decorator_list
            or function.args.posonlyargs
            or len(function.args.args) != 1
            or function.args.args[0].arg != "name"
            or function.args.vararg is not None
            or function.args.kwonlyargs
            or function.args.kwarg is not None
            or function.args.defaults
            or any(default is not None for default in function.args.kw_defaults)
        ):
            return None
        return function

    operator_lazy_function = (
        exact_top_level_function("__getattr__") if current_relative == "aureon/operator/__init__.py" else None
    )
    aureon_lazy_function = (
        exact_top_level_function("__getattr__") if current_relative == "aureon/__init__.py" else None
    )
    if current_relative == "aureon/operator/__init__.py":
        for node in nodes:
            if (
                isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id == "__getattr__"
            ) or (isinstance(node, ast.Attribute) and node.attr == "__getattr__"):
                raise DesignCandidateSourceClosureError(
                    "Operator lazy-export function is referenced or invoked from executable package source."
                )
    operator_lazy_targets_cache: tuple[str, ...] | None = None

    def operator_lazy_targets() -> list[str]:
        nonlocal operator_lazy_targets_cache
        if operator_lazy_targets_cache is not None:
            return list(operator_lazy_targets_cache)
        candidates: list[ast.Assign | ast.AnnAssign] = []
        for candidate in module_body:
            if not isinstance(candidate, (ast.Assign, ast.AnnAssign)):
                continue
            assignment_targets = (
                candidate.targets if isinstance(candidate, ast.Assign) else [candidate.target]
            )
            if any(
                isinstance(target, ast.Name) and target.id == "_LAZY_EXPORTS" for target in assignment_targets
            ):
                candidates.append(candidate)
        if len(candidates) != 1:
            raise DesignCandidateSourceClosureError(
                "Operator lazy-export call has no one exact module-level target map."
            )
        candidate = candidates[0]
        for possible_binding in nodes:
            if (
                isinstance(possible_binding, ast.Name)
                and possible_binding.id == "_LAZY_EXPORTS"
                and isinstance(possible_binding.ctx, (ast.Store, ast.Del))
                and parents.get(id(possible_binding)) is not candidate
            ):
                raise DesignCandidateSourceClosureError("Operator lazy-export map is rebound.")
        if candidate.value is None:
            raise DesignCandidateSourceClosureError("Operator lazy-export map has no literal value.")
        try:
            value = ast.literal_eval(candidate.value)
        except (ValueError, TypeError) as exc:
            raise DesignCandidateSourceClosureError(
                "Operator lazy-export map is not a literal bounded mapping."
            ) from exc
        if not isinstance(value, dict):
            raise DesignCandidateSourceClosureError("Operator lazy-export map is not a dictionary.")
        resolved: set[str] = set()
        for binding in value.values():
            if (
                not isinstance(binding, tuple)
                or len(binding) != 2
                or not isinstance(binding[0], str)
                or not isinstance(binding[1], str)
            ):
                raise DesignCandidateSourceClosureError(
                    "Operator lazy-export binding is not an exact module/attribute pair."
                )
            resolved.add(binding[0])
        expected = {
            "aureon.operator.aureon_operator",
            "aureon.operator.cognition",
            "aureon.operator.schemas",
        }
        if resolved != expected:
            raise DesignCandidateSourceClosureError(
                "Operator lazy-export targets exceed the fixed dormant exclusion."
            )
        operator_lazy_targets_cache = tuple(sorted(resolved))
        return list(operator_lazy_targets_cache)

    def call_function_name(node: ast.Call) -> str:
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
        if (
            isinstance(node.func, ast.Subscript)
            and isinstance(node.func.slice, ast.Constant)
            and node.func.slice.value == "__import__"
        ):
            return "__import__"
        if isinstance(node.func, ast.Call):
            return reflected_loader_name(node.func) or ""
        return ""

    forbidden_loader_call_names = forbidden_loader_names.union(
        {
            "SourceFileLoader",
            "SourcelessFileLoader",
            "run_module",
            "run_path",
            "spec_from_file_location",
        }
    )

    def require_dynamic_call_shape(node: ast.Call, function_name: str, *, guarded: bool) -> str:
        if function_name == "__import__" and (len(node.args) != 1 or node.keywords):
            raise DesignCandidateSourceClosureError(
                f"Nontrivial __import__ call is forbidden in {current_relative}."
            )
        if guarded and (len(node.args) != 1 or node.keywords):
            raise DesignCandidateSourceClosureError(
                f"TYPE_CHECKING dynamic import call is not one exact literal argument in {current_relative}."
            )
        if (
            not node.args
            or not isinstance(node.args[0], ast.Constant)
            or not isinstance(node.args[0].value, str)
            or not node.args[0].value
            or node.args[0].value != node.args[0].value.strip()
        ):
            location = "TYPE_CHECKING dynamic import" if guarded else "Dynamic Python import"
            raise DesignCandidateSourceClosureError(
                f"{location} is not a literal module name in {current_relative}."
            )
        return node.args[0].value

    guarded_import_names: dict[int, set[str]] = {id(guard): set() for guard in type_guards}
    for node in nodes:
        active_type_guard = type_checking_guards[id(node)]
        if active_type_guard is None:
            continue
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            guarded_import_names[id(active_type_guard)].update(import_names(node))
        elif isinstance(node, ast.Call):
            function_name = call_function_name(node)
            if function_name in forbidden_loader_call_names:
                raise DesignCandidateSourceClosureError(
                    f"Unbounded Python loader call is forbidden in {current_relative}."
                )
            if function_name in dynamic_import_names or function_name == "import_module":
                guarded_import_names[id(active_type_guard)].add(
                    require_dynamic_call_shape(node, function_name, guarded=True)
                )
    for type_guard in type_guards:
        names = guarded_import_names[id(type_guard)]
        if names:
            exclusions.append(
                {
                    "path": current_relative,
                    "line": int(type_guard.lineno),
                    "kind": "runtime-dead-type-checking-branch",
                    "targets": sorted(names),
                    "reason": "TYPE_CHECKING is false during compiler receipt replay",
                }
            )

    for node in nodes:
        active_type_guard = type_checking_guards[id(node)]
        if active_type_guard is not None:
            continue
        if isinstance(node, ast.Import):
            for alias in node.names:
                add_module(alias.name, required=alias.name.startswith("aureon."))
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = _relative_import_base(current_relative, node.module, node.level)
                base_relative = _module_relative(base, repo_root)
                base_is_module = bool(
                    base_relative is not None and not base_relative.endswith("/__init__.py")
                )
                if base_is_module:
                    targets.add(str(base_relative))
                for alias in node.names:
                    if alias.name != "*":
                        add_module(
                            f"{base}.{alias.name}" if base else alias.name,
                            required=base_relative is None,
                        )
            elif node.module:
                base = node.module
                base_relative = _module_relative(base, repo_root)
                base_is_module = bool(
                    base_relative is not None and not base_relative.endswith("/__init__.py")
                )
                if base_is_module:
                    targets.add(str(base_relative))
                for alias in node.names:
                    if alias.name != "*":
                        add_module(
                            f"{base}.{alias.name}",
                            required=base.startswith("aureon.") and base_relative is None,
                        )
        elif isinstance(node, ast.Call):
            function_name = call_function_name(node)
            if current_relative == "aureon/operator/__init__.py" and function_name == "__getattr__":
                raise DesignCandidateSourceClosureError(
                    "Operator lazy-export function is invoked from executable package source."
                )
            if function_name in forbidden_loader_call_names:
                raise DesignCandidateSourceClosureError(
                    f"Unbounded Python loader call is forbidden in {current_relative}."
                )
            if function_name not in dynamic_import_names and function_name != "import_module":
                continue
            execution_scope = execution_scopes[id(node)]
            if (
                current_relative == "aureon/operator/__init__.py"
                and operator_lazy_function is not None
                and execution_scope is operator_lazy_function
                and function_name == "import_module"
                and len(node.args) == 1
                and not node.keywords
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id == "module_name"
            ):
                exclusions.append(
                    {
                        "path": current_relative,
                        "line": int(node.lineno),
                        "kind": "bounded-dormant-lazy-export",
                        "targets": operator_lazy_targets(),
                        "reason": "compiler imports request no operator lazy-export attribute",
                    }
                )
                continue
            module_name = require_dynamic_call_shape(node, function_name, guarded=False)
            if add_module(module_name, required=module_name.startswith("aureon.")):
                continue
            if (
                current_relative == "aureon/__init__.py"
                and aureon_lazy_function is not None
                and execution_scope is aureon_lazy_function
                and function_name == "import_module"
                and len(node.args) == 1
                and not node.keywords
                and module_name in {"aureon_nexus", "binance_client"}
            ):
                exclusions.append(
                    {
                        "path": current_relative,
                        "line": int(node.lineno),
                        "kind": "bounded-dormant-lazy-export",
                        "targets": [module_name],
                        "reason": "compiler imports request no top-level Aureon lazy-export attribute",
                    }
                )
                continue
            raise DesignCandidateSourceClosureError(
                f"Unresolved dynamic Python import is not an approved dormant site in {current_relative}."
            )
    return targets, exclusions


def _parse_source(raw: bytes, *, relative: str) -> ast.AST:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DesignCandidateSourceClosureError(
            f"Executable Python source is not strict UTF-8: {relative}"
        ) from exc
    try:
        return ast.parse(text, filename=relative)
    except SyntaxError as exc:
        raise DesignCandidateSourceClosureError(
            f"Executable Python source cannot be parsed without execution: {relative}"
        ) from exc


def build_source_closure(
    repo_root: Path,
    *,
    roots: Sequence[str] = DEFAULT_SOURCE_CLOSURE_ROOTS,
) -> dict[str, Any]:
    """Derive the exact local Python closure without importing local code."""

    root_values = [
        _safe_relative_python_path(value, label=f"Executable-source root {index}")
        for index, value in enumerate(roots)
    ]
    if root_values != sorted(set(root_values)) or tuple(root_values) != tuple(DEFAULT_SOURCE_CLOSURE_ROOTS):
        raise DesignCandidateSourceClosureError(
            "Executable-source roots must equal the fixed sorted compiler bootstrap roots."
        )
    pending = list(root_values)
    for relative in root_values:
        pending.extend(
            sorted(
                _package_initializers(
                    _module_name(relative),
                    repo_root,
                )
            )
        )
    rows: dict[str, dict[str, Any]] = {}
    exclusions: list[dict[str, Any]] = []
    while pending:
        relative = min(pending)
        pending.remove(relative)
        if relative in rows:
            continue
        _, raw = read_bound_source_file(
            repo_root,
            relative,
            label=f"Executable source {relative}",
        )
        rows[relative] = {
            "path": relative,
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest().upper(),
        }
        tree = _parse_source(raw, relative=relative)
        local_targets, local_exclusions = _local_import_targets(
            tree,
            current_relative=relative,
            repo_root=repo_root,
        )
        exclusions.extend(local_exclusions)
        for target in sorted(local_targets):
            if target not in rows and target not in pending:
                pending.append(target)
    files = [rows[path] for path in sorted(rows)]
    ordered_exclusions = sorted(
        exclusions,
        key=lambda item: (
            str(item["path"]),
            int(item["line"]),
            str(item["kind"]),
            tuple(item["targets"]),
        ),
    )
    unsigned: dict[str, Any] = {
        "schema": SOURCE_CLOSURE_SCHEMA,
        "algorithm": SOURCE_CLOSURE_ALGORITHM,
        "roots": root_values,
        "files": files,
        "exclusions": ordered_exclusions,
    }
    return {**unsigned, "manifest_sha256": _json_sha256(unsigned)}


def require_source_closure_contract(value: object) -> dict[str, Any]:
    """Require exact fields, types, ordering, raw hashes, and self-hash."""

    if not isinstance(value, dict) or frozenset(value) != SOURCE_CLOSURE_FIELDS:
        raise DesignCandidateSourceClosureError(
            "Executable-source closure fields do not match the exact current contract."
        )
    if value.get("schema") != SOURCE_CLOSURE_SCHEMA:
        raise DesignCandidateSourceClosureError("Executable-source closure schema is unsupported.")
    if value.get("algorithm") != SOURCE_CLOSURE_ALGORITHM:
        raise DesignCandidateSourceClosureError("Executable-source closure algorithm is unsupported.")
    roots = value.get("roots")
    if not isinstance(roots, list) or roots != list(DEFAULT_SOURCE_CLOSURE_ROOTS):
        raise DesignCandidateSourceClosureError(
            "Executable-source closure roots are not the exact fixed roots."
        )
    files = value.get("files")
    if not isinstance(files, list) or not files:
        raise DesignCandidateSourceClosureError("Executable-source closure files must not be empty.")
    paths: list[str] = []
    for index, row in enumerate(files):
        label = f"Executable-source closure file {index}"
        if not isinstance(row, dict) or frozenset(row) != SOURCE_CLOSURE_FILE_FIELDS:
            raise DesignCandidateSourceClosureError(f"{label} fields are not exact.")
        path = _safe_relative_python_path(row.get("path"), label=f"{label}.path")
        raw_bytes = row.get("bytes")
        sha256 = row.get("sha256")
        if type(raw_bytes) is not int or raw_bytes < 1:
            raise DesignCandidateSourceClosureError(f"{label}.bytes must be a positive integer.")
        if (
            not isinstance(sha256, str)
            or len(sha256) != _SHA256_LENGTH
            or any(character not in "0123456789ABCDEF" for character in sha256)
        ):
            raise DesignCandidateSourceClosureError(f"{label}.sha256 must be an uppercase SHA-256.")
        paths.append(path)
    if paths != sorted(set(paths)):
        raise DesignCandidateSourceClosureError(
            "Executable-source closure file paths must be sorted and unique."
        )
    if not set(roots).issubset(paths):
        raise DesignCandidateSourceClosureError(
            "Executable-source closure does not contain every fixed root."
        )
    exclusions = value.get("exclusions")
    if not isinstance(exclusions, list):
        raise DesignCandidateSourceClosureError("Executable-source closure exclusions must be an array.")
    exclusion_keys: list[tuple[str, int, str, tuple[str, ...]]] = []
    for index, row in enumerate(exclusions):
        label = f"Executable-source closure exclusion {index}"
        if not isinstance(row, dict) or frozenset(row) != SOURCE_CLOSURE_EXCLUSION_FIELDS:
            raise DesignCandidateSourceClosureError(f"{label} fields are not exact.")
        path = _safe_relative_python_path(row.get("path"), label=f"{label}.path")
        line = row.get("line")
        kind = row.get("kind")
        targets = row.get("targets")
        reason = row.get("reason")
        if type(line) is not int or line < 1:
            raise DesignCandidateSourceClosureError(f"{label}.line must be positive.")
        if kind not in {
            "bounded-dormant-lazy-export",
            "runtime-dead-type-checking-branch",
        }:
            raise DesignCandidateSourceClosureError(f"{label}.kind is unsupported.")
        if (
            not isinstance(targets, list)
            or not targets
            or not all(isinstance(target, str) and target and target == target.strip() for target in targets)
            or targets != sorted(set(targets))
        ):
            raise DesignCandidateSourceClosureError(f"{label}.targets must be sorted unique module names.")
        if not isinstance(reason, str) or not reason or reason != reason.strip():
            raise DesignCandidateSourceClosureError(f"{label}.reason is malformed.")
        if path not in paths:
            raise DesignCandidateSourceClosureError(f"{label}.path is not a bound executable source.")
        exclusion_keys.append((path, line, str(kind), tuple(targets)))
    if exclusion_keys != sorted(set(exclusion_keys)):
        raise DesignCandidateSourceClosureError(
            "Executable-source closure exclusions must be sorted and unique."
        )
    unsigned = dict(value)
    manifest_sha256 = unsigned.pop("manifest_sha256", None)
    if manifest_sha256 != _json_sha256(unsigned):
        raise DesignCandidateSourceClosureError("Executable-source closure manifest self-hash is invalid.")
    return value


def verify_source_closure(
    repo_root: Path,
    expected: object,
) -> dict[str, Any]:
    """Compare an exact expected manifest with a fresh AST-derived raw closure."""

    source = require_source_closure_contract(expected)
    current = build_source_closure(repo_root, roots=source["roots"])
    if not _strict_json_equal(source, current):
        raise DesignCandidateSourceClosureError(
            "Executable-source closure does not equal the current AST-derived raw source graph."
        )
    return current


def verify_loaded_source_modules(
    expected: object,
    *,
    require_verified_loader: bool = False,
) -> None:
    """Verify every closure module already loaded by Python against expected raw bytes."""

    source = require_source_closure_contract(expected)
    by_path = {str(row["path"]): row for row in source["files"]}
    for relative, row in by_path.items():
        module_name = _module_name(relative)
        module = sys.modules.get(module_name)
        if not isinstance(module, ModuleType):
            continue
        if require_verified_loader:
            loader = getattr(module, "__loader__", None)
            if (
                getattr(loader, "_aureon_verified_source_path", None) != relative
                or getattr(loader, "_aureon_verified_source_sha256", None) != row["sha256"]
            ):
                raise DesignCandidateSourceClosureError(
                    f"Loaded executable-source module bypassed the verified raw loader: {module_name}"
                )
        raw_path = getattr(module, "__file__", None)
        if not isinstance(raw_path, str):
            raise DesignCandidateSourceClosureError(
                f"Loaded executable-source module has no source path: {module_name}"
            )
        loaded_path = Path(raw_path)
        if loaded_path.suffix == ".pyc":
            loaded_path = loaded_path.with_suffix(".py")
        expected_suffix = Path(*PurePosixPath(relative).parts)
        try:
            if tuple(loaded_path.parts[-len(expected_suffix.parts) :]) != expected_suffix.parts:
                raise DesignCandidateSourceClosureError(
                    f"Loaded executable-source module is relocated: {module_name}"
                )
            _, raw = read_bound_source_file(
                loaded_path.parents[len(expected_suffix.parts) - 1],
                relative,
                label=f"Loaded executable source {module_name}",
            )
        except (IndexError, OSError) as exc:
            raise DesignCandidateSourceClosureError(
                f"Loaded executable-source module path is invalid: {module_name}"
            ) from exc
        if len(raw) != row["bytes"] or hashlib.sha256(raw).hexdigest().upper() != row["sha256"]:
            raise DesignCandidateSourceClosureError(
                f"Loaded executable-source module bytes changed: {module_name}"
            )


class _VerifiedRawSourceLoader(importlib.abc.Loader):
    def __init__(
        self,
        repo_root: Path,
        relative: str,
        row: Mapping[str, Any],
        *,
        is_package: bool,
    ) -> None:
        self._repo_root = repo_root
        self._relative = relative
        self._row = dict(row)
        self._is_package = is_package
        self._aureon_verified_source_path = relative
        self._aureon_verified_source_sha256 = str(row["sha256"])

    def create_module(self, spec: object) -> None:
        return None

    def exec_module(self, module: ModuleType) -> None:
        path, raw = read_bound_source_file(
            self._repo_root,
            self._relative,
            label=f"Verified executable import {self._relative}",
        )
        if len(raw) != self._row["bytes"] or hashlib.sha256(raw).hexdigest().upper() != self._row["sha256"]:
            raise DesignCandidateSourceClosureError(
                f"Verified executable import changed before execution: {self._relative}"
            )
        module.__file__ = str(path)
        module.__dict__["__cached__"] = None
        if self._is_package:
            module.__path__ = [str(path.parent)]
        code = compile(raw, str(path), "exec")
        exec(code, module.__dict__)  # noqa: S102


class _VerifiedRawSourceFinder(importlib.abc.MetaPathFinder):
    def __init__(self, repo_root: Path, expected: Mapping[str, Any]) -> None:
        self._repo_root = repo_root
        self._by_module: dict[str, tuple[str, dict[str, Any], bool]] = {}
        for raw_row in expected["files"]:
            row = dict(raw_row)
            relative = str(row["path"])
            self._by_module[_module_name(relative)] = (
                relative,
                row,
                relative.endswith("/__init__.py"),
            )

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None = None,
        target: ModuleType | None = None,
    ) -> ModuleSpec | None:
        binding = self._by_module.get(fullname)
        if binding is None:
            return None
        relative, row, is_package = binding
        loader = _VerifiedRawSourceLoader(
            self._repo_root,
            relative,
            row,
            is_package=is_package,
        )
        return importlib.util.spec_from_loader(
            fullname,
            loader,
            origin=str(self._repo_root / Path(*PurePosixPath(relative).parts)),
            is_package=is_package,
        )


def install_verified_source_importer(
    repo_root: Path,
    expected: object,
    *,
    require_unloaded: bool,
) -> _VerifiedRawSourceFinder:
    """Install a first-position raw-source importer for every bound module."""

    source = require_source_closure_contract(expected)
    module_names = {_module_name(str(row["path"])) for row in source["files"]}
    loaded = sorted(module_names.intersection(sys.modules))
    if require_unloaded and loaded:
        raise DesignCandidateSourceClosureError(
            "Sealed compiler ingress found preloaded local modules: " + ", ".join(loaded)
        )
    finder = _VerifiedRawSourceFinder(Path(repo_root), source)
    sys.meta_path.insert(0, finder)
    return finder


def remove_verified_source_importer(finder: _VerifiedRawSourceFinder) -> None:
    """Remove exactly one previously installed verified-source finder."""

    try:
        sys.meta_path.remove(finder)
    except ValueError:
        pass


__all__ = [
    "DEFAULT_SOURCE_CLOSURE_ROOTS",
    "DesignCandidateSourceClosureError",
    "SOURCE_CLOSURE_ALGORITHM",
    "SOURCE_CLOSURE_FIELDS",
    "SOURCE_CLOSURE_EXCLUSION_FIELDS",
    "SOURCE_CLOSURE_FILE_FIELDS",
    "SOURCE_CLOSURE_HELPER_PATH",
    "SOURCE_CLOSURE_SCHEMA",
    "build_source_closure",
    "install_verified_source_importer",
    "read_bound_source_file",
    "remove_verified_source_importer",
    "require_source_closure_contract",
    "verify_loaded_source_modules",
    "verify_source_closure",
]
