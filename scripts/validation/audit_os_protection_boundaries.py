#!/usr/bin/env python3
"""Conservative static census of Aureon's local OS protection boundaries.

The census is intentionally read-only.  It parses Python and lexically scans
executable JavaScript/TypeScript without importing repository code, reading
credentials, or opening sockets.  A high-risk operation is protected only when
Python control flow contains structural evidence of all four local-development
steps: construction of the real ``LocalOSProtectionBoundary``, HNC admission,
a fail-closed ``AdmittedHNC`` guard, a same-handle Magic Star custody handoff,
and execution *inside* a capability registered with the same custody and
selected by ``LocalDevelopmentReleaseBoundaryV02.release``.  A custody handoff
followed by an arbitrary sink is still a blocker.  Names in comments, strings,
type annotations, or imports alone never earn protection. JavaScript/TypeScript
remains a blocker unless an equally strong parser-backed proof is added.

This is a boundary inventory, not a claim that local wrapping establishes
remote truth or production authority.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

ROOT = Path(__file__).resolve().parents[2]
SOURCE_SUFFIXES = {".cjs", ".js", ".jsx", ".mjs", ".py", ".ts", ".tsx"}
SKIP_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "site-packages",
    "vendor",
}

LOCAL_DEVELOPMENT_PROTECTED = "local-development-registered-release-protected"
PROTECTED = LOCAL_DEVELOPMENT_PROTECTED
EXPLICIT_HOLD = "explicit-hold-or-disabled"
BLOCKER = "unprotected-high-risk-blocker"
CLASSIFICATIONS = (LOCAL_DEVELOPMENT_PROTECTED, EXPLICIT_HOLD, BLOCKER)

CATEGORIES = (
    "http-server-ingress",
    "websocket-server-ingress",
    "interprocess-capability-dispatch",
    "subprocess-shell",
    "dynamic-code-execution",
    "unsafe-deserialization",
    "filesystem-mutation",
    "credential-config-write",
    "local-action-bridge",
    "economic-mutation",
)

_OS_PROTECTION_MODULE = "aureon.plumber.os_protection"
_PRODUCTION_RELEASE_BROKER_V03_FILE = (
    "aureon/plumber/production_release_broker_v03.py"
)
_PRODUCTION_RELEASE_BROKER_V03_SCOPE = (
    "ProductionReleaseBrokerV03.execute_release"
)
_PRODUCTION_RELEASE_BROKER_V03_EXECUTOR_CALL = "self._executor.execute"
_CONSTRUCTOR_REQUIRED_KEYWORDS = {
    "LocalOSProtectionBoundary": frozenset(
        {"boundary_id", "master_key_provider"}
    ),
    "RegisteredCapabilityV02": frozenset(
        {
            "capability_id",
            "handler",
            "measurement_sha256",
            "policy_measurement_sha256",
            "result_schema",
        }
    ),
    "LocalDevelopmentStarCustodyV02": frozenset(
        {
            "allow_insecure_same_process",
            "authorization_trust",
            "capabilities",
            "source_authority",
            "source_private_key",
            "state_store",
        }
    ),
    "LocalDevelopmentReleaseBoundaryV02": frozenset(
        {
            "allow_insecure_same_process",
            "authorization_trust",
            "capability_policies",
            "continuity_state_probe",
            "custody",
            "epas_store",
            "evidence_expectations_probe",
            "live_binding_probe",
            "receipt_authority",
            "receipt_private_key",
            "recipient_verifier",
            "release_evidence_trust",
            "star_trust",
            "state_store",
        }
    ),
}
_LITERAL_TRUE_CONSTRUCTORS = frozenset(
    {
        "LocalDevelopmentStarCustodyV02",
        "LocalDevelopmentReleaseBoundaryV02",
    }
)
_ADMISSION_REQUIRED_KEYWORDS = frozenset(
    {"source_id", "ingress_kind", "purpose"}
)
_HANDOFF_REQUIRED_KEYWORDS = frozenset(
    {"custody", "release_context_sha256"}
)
_RELEASE_REQUIRED_KEYWORDS = frozenset(
    {
        "authorization_chain",
        "capability_id",
        "challenge",
        "expected_channel_binding_sha256",
        "expected_live_binding_sha256",
        "expected_runtime_measurement_sha256",
        "observer_commitment",
        "recipient_proof",
        "release_evidence",
        "session_id",
        "star",
        "temporal_commitment",
    }
)
_ROUTE_TAILS = {"delete", "get", "head", "options", "patch", "post", "put", "route"}
_SERVER_CONSTRUCTOR_TAILS = {
    "apirouter",
    "application",
    "fastapi",
    "flask",
    "httpserver",
    "tcpserver",
}
_FRAMEWORK_SERVER_TYPE_EXPORTS = {
    "flask": frozenset({"Flask"}),
}
_MUTATING_FILE_TAILS = {
    "append_text",
    "appendfile",
    "appendfilesync",
    "chmod",
    "chown",
    "copy",
    "copy2",
    "copyfile",
    "copyfileobj",
    "copyfilesync",
    "copytree",
    "createwritestream",
    "hardlink_to",
    "link",
    "makedirs",
    "mkdir",
    "move",
    "remove",
    "removedirs",
    "rename",
    "renames",
    "replace",
    "rmdir",
    "rmtree",
    "symlink",
    "symlink_to",
    "touch",
    "truncate",
    "unlink",
    "write_bytes",
    "write_text",
    "writefile",
    "writefilesync",
}
_SUBPROCESS_NAMES = {
    "asyncio.create_subprocess_exec",
    "asyncio.create_subprocess_shell",
    "child_process.exec",
    "child_process.execfile",
    "child_process.execfilesync",
    "child_process.execsync",
    "child_process.fork",
    "child_process.spawn",
    "child_process.spawnsync",
    "os.popen",
    "os.system",
    "subprocess.call",
    "subprocess.check_call",
    "subprocess.check_output",
    "subprocess.getoutput",
    "subprocess.getstatusoutput",
    "subprocess.popen",
    "subprocess.run",
}
_DYNAMIC_CODE_NAMES = {
    "__import__",
    "builtins.eval",
    "builtins.exec",
    "eval",
    "exec",
    "importlib.import_module",
    "runpy.run_module",
    "runpy.run_path",
}
_UNSAFE_DESERIALIZATION_NAMES = {
    "cloudpickle.load",
    "cloudpickle.loads",
    "dill.load",
    "dill.loads",
    "joblib.load",
    "marshal.load",
    "marshal.loads",
    "pickle.load",
    "pickle.loads",
    "shelve.open",
    "torch.load",
    "v8.deserialize",
    "yaml.load",
    "yaml.load_all",
}
_ECONOMIC_TAILS = {
    "amendorder",
    "cancelall",
    "cancelallorders",
    "cancelorder",
    "cancelorders",
    "closeallpositions",
    "closemarginposition",
    "closeposition",
    "closetrade",
    "createorder",
    "createlimitorder",
    "createmarketbuyorder",
    "createmarketorder",
    "createmarketsellorder",
    "deleteworkingorder",
    "editorder",
    "exerciseoption",
    "exerciseoptionsposition",
    "openpositionwithtpsl",
    "orderlimitbuy",
    "orderlimitsell",
    "ordermarketbuy",
    "ordermarketsell",
    "placebracketorder",
    "placelimitorder",
    "placemarginorder",
    "placemarketorder",
    "placeocoorder",
    "placeorder",
    "placeorderwithtpsl",
    "placestoplimitorder",
    "placestoplossorder",
    "placestoporder",
    "placetakeprofitorder",
    "placetrailingstoporder",
    "placeworkingorder",
    "replaceorder",
    "submitorder",
    "updatepositionlimits",
}
_ECONOMIC_ENDPOINT = re.compile(
    r"(?:/api/v3/(?:order|openorders)|/sapi/v1/margin/order|"
    r"/fapi/v1/(?:order|batchorders)|/dapi/v1/(?:order|batchorders)|"
    r"/eapi/v1/(?:order|batchorders)|/papi/v1/order|"
    r"/api/v1/(?:positions|workingorders)|/v2/(?:orders|positions)|"
    r"\b(?:addorder|amendorder|cancelorder|editorder)\b)",
    re.IGNORECASE,
)
_CREDENTIAL_HINT = re.compile(
    r"(?:^|[^a-z0-9])(?:\.env|auth|config|credential|keyring|password|secret|"
    r"settings|token)(?:[^a-z0-9]|$)",
    re.IGNORECASE,
)
_HOLD_HINT = re.compile(r"\b(?:blocked|disabled|hold|quarantined|unreachable)\b", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class Finding:
    file: str
    line: int
    column: int
    language: str
    scope: str
    boundary_kind: str
    category: str
    operation: str
    classification: str
    fingerprint: str
    evidence: tuple[str, ...]
    rationale: str


@dataclass(frozen=True, slots=True)
class ParseError:
    file: str
    language: str
    line: int
    error: str


@dataclass(slots=True)
class _Candidate:
    file: str
    line: int
    column: int
    language: str
    scope: str
    boundary_kind: str
    category: str
    operation: str
    canonical: str
    node: ast.AST | None = None
    function: ast.FunctionDef | ast.AsyncFunctionDef | None = None
    classification: str = BLOCKER
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _Admission:
    outcome: str
    boundary: str
    node: ast.Call
    source_parameters: frozenset[str]


@dataclass(frozen=True, slots=True)
class _Handoff:
    outcome: str
    boundary: str
    node: ast.Call
    positive_guard: ast.If | None
    negative_guard: ast.If | None


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def iter_source_files(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().casefold()):
        if not path.is_file() or path.suffix.casefold() not in SOURCE_SUFFIXES:
            continue
        relative_parts = path.relative_to(root).parts
        if any(part.casefold() in SKIP_PARTS for part in relative_parts):
            continue
        yield path


def _callee(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _callee(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Call):
        return _callee(node.func)
    return ""


def _target_names(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, (ast.Tuple, ast.List)):
        return tuple(name for item in node.elts for name in _target_names(item))
    return ()


def _static_string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _normalized_tail(callee: str) -> str:
    return callee.rsplit(".", 1)[-1].casefold().replace("_", "")


def _scope_name(functions: Iterable[ast.AST]) -> str:
    names = [getattr(item, "name", "<scope>") for item in functions]
    return ".".join(names) if names else "<module>"


def _same_function_nodes(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> Iterator[ast.AST]:
    stack: list[ast.AST] = list(reversed(function.body))
    while stack:
        node = stack.pop()
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        stack.extend(reversed(list(ast.iter_child_nodes(node))))


def _contains(container: ast.AST, node: ast.AST) -> bool:
    return any(item is node for item in ast.walk(container))


def _in_body(statement: ast.If, node: ast.AST) -> bool:
    return any(_contains(item, node) for item in statement.body)


def _terminal_block(statements: list[ast.stmt]) -> bool:
    return bool(statements) and isinstance(statements[-1], (ast.Raise, ast.Return))


class _PythonScanner(ast.NodeVisitor):
    def __init__(self, *, file: str, source: str, tree: ast.Module) -> None:
        self.file = file
        self.source = source
        self.tree = tree
        self.candidates: list[_Candidate] = []
        self.scope: list[ast.AST] = []
        self.parent: dict[ast.AST, ast.AST] = {
            child: parent
            for parent in ast.walk(tree)
            for child in ast.iter_child_nodes(parent)
        }
        self.os_boundary_aliases: set[str] = set()
        self.admitted_aliases: set[str] = set()
        self.os_module_aliases: set[str] = set()
        self.registered_capability_aliases: set[str] = set()
        self.star_custody_aliases: set[str] = set()
        self.star_custody_module_aliases: set[str] = set()
        self.release_boundary_aliases: set[str] = set()
        self.release_boundary_module_aliases: set[str] = set()
        self.server_types: set[str] = set()
        self.server_factories: set[str] = set()
        self.server_receivers: set[str] = set()
        self.server_binding_events: dict[
            ast.AST,
            dict[str, list[tuple[int, int, ast.AST | None]]],
        ] = {}
        self.websocket_receivers: set[str] = set()
        self.local_action_receivers: set[str] = set()
        self.import_aliases: set[str] = set()
        self.binding_events: dict[ast.AST, dict[str, list[ast.AST]]] = {}
        self.release_registries: dict[
            str,
            tuple[str, dict[str, ast.FunctionDef | ast.AsyncFunctionDef]],
        ] = {}
        self._prepare_bindings()
        self._prepare()

    def _record_binding_event(
        self,
        *,
        owner: ast.AST,
        name: str,
        event: ast.AST,
    ) -> None:
        self.binding_events.setdefault(owner, {}).setdefault(name, []).append(event)

    def _binding_event_node(self, node: ast.Name) -> ast.AST:
        current: ast.AST = node
        binding_nodes = (
            ast.Assign,
            ast.AnnAssign,
            ast.AugAssign,
            ast.NamedExpr,
            ast.For,
            ast.AsyncFor,
            ast.With,
            ast.AsyncWith,
            ast.Delete,
            ast.comprehension,
        )
        while current in self.parent:
            current = self.parent[current]
            if isinstance(current, binding_nodes):
                return current
            if isinstance(
                current,
                (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda),
            ):
                break
        return node

    def _prepare_bindings(self) -> None:
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Name) and isinstance(
                node.ctx,
                (ast.Store, ast.Del),
            ):
                self._record_binding_event(
                    owner=self._lexical_owner(node),
                    name=node.id,
                    event=self._binding_event_node(node),
                )
            elif isinstance(node, ast.arg):
                self._record_binding_event(
                    owner=self._lexical_owner(node),
                    name=node.arg,
                    event=node,
                )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                self._record_binding_event(
                    owner=self._lexical_owner(node),
                    name=node.name,
                    event=node,
                )
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                owner = self._lexical_owner(node)
                for alias in node.names:
                    local = alias.asname or alias.name.split(".", 1)[0]
                    self._record_binding_event(
                        owner=owner,
                        name=local,
                        event=node,
                    )
                    if owner is self.tree:
                        self.import_aliases.add(local)
            elif isinstance(node, ast.ExceptHandler) and node.name is not None:
                self._record_binding_event(
                    owner=self._lexical_owner(node),
                    name=node.name,
                    event=node,
                )
            elif isinstance(node, (ast.Global, ast.Nonlocal)):
                owner = self._lexical_owner(node)
                for name in node.names:
                    self._record_binding_event(owner=owner, name=name, event=node)

    def _is_exact_single_binding(
        self,
        *,
        owner: ast.AST,
        name: str,
        expected: ast.AST,
    ) -> bool:
        events = self.binding_events.get(owner, {}).get(name, ())
        return len(events) == 1 and events[0] is expected

    def _is_unshadowed_module_import(self, name: str, node: ast.AST) -> bool:
        module_events = self.binding_events.get(self.tree, {}).get(name, ())
        if len(module_events) != 1 or not isinstance(
            module_events[0],
            (ast.Import, ast.ImportFrom),
        ):
            return False
        owner = self._lexical_owner(node)
        for candidate_owner in self._owner_chain(owner):
            if candidate_owner is self.tree:
                break
            if self.binding_events.get(candidate_owner, {}).get(name):
                return False
        return True

    def _is_module_scope(self, node: ast.AST) -> bool:
        parent = self.parent.get(node)
        while parent is not None:
            if isinstance(
                parent,
                (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda),
            ):
                return False
            parent = self.parent.get(parent)
        return True

    @staticmethod
    def _is_server_type_expression(node: ast.AST, server_types: set[str]) -> bool:
        if isinstance(node, (ast.Name, ast.Attribute)):
            return _callee(node) in server_types
        if isinstance(node, ast.IfExp):
            return any(
                _PythonScanner._is_server_type_expression(branch, server_types)
                for branch in (node.body, node.orelse)
            )
        return False

    @staticmethod
    def _is_server_instance_expression(
        node: ast.AST,
        *,
        server_types: set[str],
        server_factories: set[str],
        server_bindings: set[str],
    ) -> bool:
        if isinstance(node, ast.Call):
            callee = _callee(node.func)
            return callee in server_types or callee in server_factories
        if isinstance(node, ast.Name):
            return node.id in server_bindings
        if isinstance(node, ast.IfExp):
            return all(
                _PythonScanner._is_server_instance_expression(
                    branch,
                    server_types=server_types,
                    server_factories=server_factories,
                    server_bindings=server_bindings,
                )
                for branch in (node.body, node.orelse)
            )
        return False

    def _function_definitely_returns_server(
        self,
        function: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> bool:
        nodes = list(_same_function_nodes(function))
        assignments: dict[str, list[ast.AST]] = {}
        for node in nodes:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                for name in _target_names(target):
                    assignments.setdefault(name, []).append(node.value)

        bindings: set[str] = set()
        changed = True
        while changed:
            changed = False
            for name, values in assignments.items():
                if name in bindings or not values:
                    continue
                if all(
                    self._is_server_instance_expression(
                        value,
                        server_types=self.server_types,
                        server_factories=self.server_factories,
                        server_bindings=bindings,
                    )
                    for value in values
                ):
                    bindings.add(name)
                    changed = True

        returns = [node.value for node in nodes if isinstance(node, ast.Return)]
        return bool(returns) and all(
            value is not None
            and self._is_server_instance_expression(
                value,
                server_types=self.server_types,
                server_factories=self.server_factories,
                server_bindings=bindings,
            )
            for value in returns
        )

    def _lexical_owner(self, node: ast.AST) -> ast.AST:
        parent = self.parent.get(node)
        while parent is not None:
            if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                return parent
            parent = self.parent.get(parent)
        return self.tree

    def _owner_chain(self, owner: ast.AST) -> Iterator[ast.AST]:
        current: ast.AST | None = owner
        while current is not None:
            if isinstance(
                current,
                (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
            ):
                yield current
            current = self.parent.get(current)

    def _record_server_binding(
        self,
        *,
        owner: ast.AST,
        name: str,
        line: int,
        column: int,
        value: ast.AST | None,
    ) -> None:
        events = self.server_binding_events.setdefault(owner, {}).setdefault(name, [])
        events.append((line, column, value))

    def _server_binding_value(
        self,
        value: ast.AST,
        *,
        owner: ast.AST,
        position: tuple[int, int],
        seen: set[tuple[int, str, int, int]],
    ) -> bool:
        if isinstance(value, ast.Call):
            callee = _callee(value.func)
            return callee in self.server_types or callee in self.server_factories
        if isinstance(value, ast.Name):
            return self._server_name_at(
                value.id,
                owner=owner,
                position=position,
                seen=seen,
            )
        if isinstance(value, ast.IfExp):
            return all(
                self._server_binding_value(
                    branch,
                    owner=owner,
                    position=position,
                    seen=seen,
                )
                for branch in (value.body, value.orelse)
            )
        return False

    def _server_name_at(
        self,
        name: str,
        *,
        owner: ast.AST,
        position: tuple[int, int],
        seen: set[tuple[int, str, int, int]] | None = None,
    ) -> bool:
        visited = set() if seen is None else seen
        for candidate_owner in self._owner_chain(owner):
            events = self.server_binding_events.get(candidate_owner, {}).get(name, ())
            prior = [event for event in events if event[:2] < position]
            if not prior:
                continue
            line, column, value = max(prior, key=lambda event: event[:2])
            key = (id(candidate_owner), name, line, column)
            if key in visited or value is None:
                return False
            visited.add(key)
            return self._server_binding_value(
                value,
                owner=candidate_owner,
                position=(line, column),
                seen=visited,
            )
        return False

    def _has_proven_server_receiver(self, call: ast.Call) -> bool:
        if not isinstance(call.func, ast.Attribute):
            return False
        receiver = call.func.value
        if isinstance(receiver, ast.Call):
            callee = _callee(receiver.func)
            return callee in self.server_types or callee in self.server_factories
        if not isinstance(receiver, ast.Name):
            return False
        return self._server_name_at(
            receiver.id,
            owner=self._lexical_owner(call),
            position=(call.lineno, call.col_offset),
        )

    def _prepare(self) -> None:
        for node in self.tree.body:
            if isinstance(node, ast.ImportFrom) and node.module == _OS_PROTECTION_MODULE:
                for alias in node.names:
                    local = alias.asname or alias.name
                    if alias.name == "LocalOSProtectionBoundary":
                        self.os_boundary_aliases.add(local)
                    elif alias.name == "AdmittedHNC":
                        self.admitted_aliases.add(local)
            elif isinstance(node, ast.ImportFrom) and node.module == "aureon.plumber.star_custody_v02":
                for alias in node.names:
                    local = alias.asname or alias.name
                    if alias.name == "RegisteredCapabilityV02":
                        self.registered_capability_aliases.add(local)
                    elif alias.name == "LocalDevelopmentStarCustodyV02":
                        self.star_custody_aliases.add(local)
            elif isinstance(node, ast.ImportFrom) and node.module == "aureon.plumber.release_boundary_v02":
                for alias in node.names:
                    if alias.name == "LocalDevelopmentReleaseBoundaryV02":
                        self.release_boundary_aliases.add(alias.asname or alias.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == _OS_PROTECTION_MODULE:
                        self.os_module_aliases.add(alias.asname or alias.name)
                    elif alias.name == "aureon.plumber.star_custody_v02":
                        self.star_custody_module_aliases.add(alias.asname or alias.name)
                    elif alias.name == "aureon.plumber.release_boundary_v02":
                        self.release_boundary_module_aliases.add(alias.asname or alias.name)
        module_nodes = [node for node in ast.walk(self.tree) if self._is_module_scope(node)]
        for node in module_nodes:
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                framework = node.module.casefold().split(".", 1)[0]
                exports = _FRAMEWORK_SERVER_TYPE_EXPORTS.get(framework, ())
                for alias in node.names:
                    if alias.name in exports:
                        self.server_types.add(alias.asname or alias.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    framework = alias.name.casefold().split(".", 1)[0]
                    exports = _FRAMEWORK_SERVER_TYPE_EXPORTS.get(framework, ())
                    local = alias.asname or framework
                    self.server_types.update(f"{local}.{export}" for export in exports)

        type_assignments = [
            node for node in module_nodes if isinstance(node, (ast.Assign, ast.AnnAssign))
        ]
        class_definitions = [node for node in module_nodes if isinstance(node, ast.ClassDef)]
        changed = True
        while changed:
            changed = False
            for node in type_assignments:
                if node.value is None or not self._is_server_type_expression(
                    node.value,
                    self.server_types,
                ):
                    continue
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    for name in _target_names(target):
                        if name not in self.server_types:
                            self.server_types.add(name)
                            changed = True
            for node in class_definitions:
                if node.name in self.server_types:
                    continue
                if any(_callee(base) in self.server_types for base in node.bases):
                    self.server_types.add(node.name)
                    changed = True

        factory_definitions = [
            node
            for node in module_nodes
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        changed = True
        while changed:
            changed = False
            for node in factory_definitions:
                if node.name in self.server_factories:
                    continue
                if self._function_definitely_returns_server(node):
                    self.server_factories.add(node.name)
                    changed = True

        receiver_assignments = [
            node
            for node in ast.walk(self.tree)
            if isinstance(node, (ast.Assign, ast.AnnAssign))
        ]
        for node in receiver_assignments:
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                for name in _target_names(target):
                    self._record_server_binding(
                        owner=self._lexical_owner(node),
                        name=name,
                        line=node.lineno,
                        column=node.col_offset,
                        value=node.value,
                    )
        for node in ast.walk(self.tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            arguments = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
            if node.args.vararg is not None:
                arguments.append(node.args.vararg)
            if node.args.kwarg is not None:
                arguments.append(node.args.kwarg)
            for argument in arguments:
                self._record_server_binding(
                    owner=node,
                    name=argument.arg,
                    line=node.lineno,
                    column=node.col_offset,
                    value=None,
                )
        for bindings in self.server_binding_events.values():
            for events in bindings.values():
                events.sort(key=lambda event: event[:2])

        for node in receiver_assignments:
            value = node.value
            if not isinstance(value, ast.Call):
                continue
            names = (
                tuple(name for target in node.targets for name in _target_names(target))
                if isinstance(node, ast.Assign)
                else _target_names(node.target)
            )
            callee = _callee(value.func).casefold()
            tail = callee.rsplit(".", 1)[-1]
            if tail in _SERVER_CONSTRUCTOR_TAILS:
                self.server_receivers.update(names)
            if "websocket" in callee:
                self.websocket_receivers.update(names)
            if tail == "localactionbridge" or "local_action_bridge" in callee:
                self.local_action_receivers.update(names)
        self._prepare_release_registries()

    @staticmethod
    def _keyword(call: ast.Call, name: str) -> ast.AST | None:
        return next((item.value for item in call.keywords if item.arg == name), None)

    @staticmethod
    def _single_assignment_name(node: ast.Assign | ast.AnnAssign) -> str | None:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        names = [name for target in targets for name in _target_names(target)]
        return names[0] if len(names) == 1 else None

    @staticmethod
    def _dict_bindings(node: ast.AST | None) -> dict[str, str]:
        if not isinstance(node, ast.Dict):
            return {}
        result: dict[str, str] = {}
        for key, value in zip(node.keys, node.values, strict=True):
            static_key = _static_string(key)
            if static_key is not None and isinstance(value, ast.Name):
                result[static_key] = value.id
        return result

    def _matches_constructor(
        self,
        call: ast.Call,
        *,
        aliases: set[str],
        module_aliases: set[str],
        class_name: str,
    ) -> bool:
        name = _callee(call.func)
        direct = name in aliases
        matched_module_alias = next(
            (
                alias
                for alias in module_aliases
                if name == f"{alias}.{class_name}"
            ),
            None,
        )
        if not direct and matched_module_alias is None:
            return False
        import_name = name if direct else matched_module_alias
        if import_name is None or not self._is_unshadowed_module_import(import_name, call):
            return False
        required = _CONSTRUCTOR_REQUIRED_KEYWORDS.get(class_name)
        if required is None or call.args or any(item.arg is None for item in call.keywords):
            return False
        keywords = {item.arg for item in call.keywords if item.arg is not None}
        if not required <= keywords:
            return False
        if class_name in _LITERAL_TRUE_CONSTRUCTORS:
            insecure = self._keyword(call, "allow_insecure_same_process")
            if not isinstance(insecure, ast.Constant) or insecure.value is not True:
                return False
        return True

    def _prepare_release_registries(self) -> None:
        functions_by_name: dict[str, list[ast.FunctionDef | ast.AsyncFunctionDef]] = {}
        for node in self.tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions_by_name.setdefault(node.name, []).append(node)
        unique_functions = {
            name: functions[0]
            for name, functions in functions_by_name.items()
            if len(functions) == 1
        }

        capabilities: dict[str, tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]] = {}
        for node in self.tree.body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)) or not isinstance(node.value, ast.Call):
                continue
            if not self._matches_constructor(
                node.value,
                aliases=self.registered_capability_aliases,
                module_aliases=self.star_custody_module_aliases,
                class_name="RegisteredCapabilityV02",
            ):
                continue
            variable = self._single_assignment_name(node)
            capability_id = _static_string(self._keyword(node.value, "capability_id"))
            handler_node = self._keyword(node.value, "handler")
            if variable is None or capability_id is None or not isinstance(handler_node, ast.Name):
                continue
            if not self._is_exact_single_binding(
                owner=self.tree,
                name=variable,
                expected=node,
            ):
                continue
            handler = unique_functions.get(handler_node.id)
            if handler is not None:
                capabilities[variable] = (capability_id, handler)

        custodies: dict[str, dict[str, ast.FunctionDef | ast.AsyncFunctionDef]] = {}
        for node in self.tree.body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)) or not isinstance(node.value, ast.Call):
                continue
            if not self._matches_constructor(
                node.value,
                aliases=self.star_custody_aliases,
                module_aliases=self.star_custody_module_aliases,
                class_name="LocalDevelopmentStarCustodyV02",
            ):
                continue
            custody_variable = self._single_assignment_name(node)
            if custody_variable is None:
                continue
            if not self._is_exact_single_binding(
                owner=self.tree,
                name=custody_variable,
                expected=node,
            ):
                continue
            registered: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
            for capability_id, variable in self._dict_bindings(
                self._keyword(node.value, "capabilities")
            ).items():
                capability = capabilities.get(variable)
                if capability is not None and capability[0] == capability_id:
                    registered[capability_id] = capability[1]
            if registered:
                custodies[custody_variable] = registered

        for node in self.tree.body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)) or not isinstance(node.value, ast.Call):
                continue
            if not self._matches_constructor(
                node.value,
                aliases=self.release_boundary_aliases,
                module_aliases=self.release_boundary_module_aliases,
                class_name="LocalDevelopmentReleaseBoundaryV02",
            ):
                continue
            release_variable = self._single_assignment_name(node)
            custody_node = self._keyword(node.value, "custody")
            if release_variable is None or not isinstance(custody_node, ast.Name):
                continue
            if not self._is_exact_single_binding(
                owner=self.tree,
                name=release_variable,
                expected=node,
            ):
                continue
            registered = custodies.get(custody_node.id)
            if not registered:
                continue
            policy_ids = set(
                self._dict_bindings(self._keyword(node.value, "capability_policies"))
            )
            selected = {
                capability_id: handler
                for capability_id, handler in registered.items()
                if capability_id in policy_ids
            }
            if selected:
                self.release_registries[release_variable] = (custody_node.id, selected)

    def _is_boundary_constructor(self, call: ast.Call) -> bool:
        return self._matches_constructor(
            call,
            aliases=self.os_boundary_aliases,
            module_aliases=self.os_module_aliases,
            class_name="LocalOSProtectionBoundary",
        )

    def _function(self) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
        for item in reversed(self.scope):
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return item
        return None

    def _add(
        self,
        node: ast.AST,
        *,
        boundary_kind: str,
        category: str,
        operation: str,
        canonical: str,
    ) -> None:
        self.candidates.append(
            _Candidate(
                file=self.file,
                line=getattr(node, "lineno", 1),
                column=getattr(node, "col_offset", 0) + 1,
                language="python",
                scope=_scope_name(self.scope),
                boundary_kind=boundary_kind,
                category=category,
                operation=operation,
                canonical=canonical,
                node=node,
                function=self._function(),
            )
        )

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        self.scope.append(node)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self.scope.append(node)
        self.generic_visit(node)
        self.scope.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Assign(self, node: ast.Assign) -> Any:
        for target in node.targets:
            if isinstance(target, ast.Subscript) and _callee(target.value).casefold() == "os.environ":
                self._add(
                    node,
                    boundary_kind="sink",
                    category="credential-config-write",
                    operation="environment-credential-write",
                    canonical=ast.dump(node, include_attributes=False),
                )
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> Any:
        if isinstance(node.target, ast.Subscript) and _callee(node.target.value).casefold() == "os.environ":
            self._add(
                node,
                boundary_kind="sink",
                category="credential-config-write",
                operation="environment-credential-write",
                canonical=ast.dump(node, include_attributes=False),
            )
        self.generic_visit(node)

    def _ingress(self, call: ast.Call, callee: str) -> tuple[str, str] | None:
        lowered = callee.casefold()
        tail = lowered.rsplit(".", 1)[-1]
        receiver = callee.rsplit(".", 1)[0] if "." in callee else ""
        receiver_tail = receiver.rsplit(".", 1)[-1]
        if "websocket" in lowered and tail in {"serve", "listen", "run", "websocketserver"}:
            return "websocket-server-ingress", f"websocket-{tail}"
        if tail in {"httpserver", "threadinghttpserver", "tcpserver"}:
            return "http-server-ingress", "http-server-construction"
        if lowered in {"uvicorn.run", "aiohttp.web.run_app", "web.run_app"}:
            return "http-server-ingress", tail.replace("_", "-")
        proven_server_receiver = self._has_proven_server_receiver(call)
        if tail in _ROUTE_TAILS and (
            receiver_tail in self.server_receivers or proven_server_receiver
        ):
            return "http-server-ingress", f"http-route-{tail}"
        if tail == "websocket" and (
            receiver_tail in self.server_receivers or proven_server_receiver
        ):
            return "websocket-server-ingress", "websocket-route"
        if tail in {"run", "serve", "listen"} and (
            receiver_tail in self.server_receivers
            or proven_server_receiver
            or receiver_tail in self.websocket_receivers
            or any(token in lowered for token in ("http", "server", "uvicorn", "websocket"))
        ):
            category = "websocket-server-ingress" if "websocket" in lowered else "http-server-ingress"
            return category, f"server-{tail}"
        if tail == "bind" and any(token in lowered for token in ("http", "server", "socket")):
            return "http-server-ingress", "server-bind"
        return None

    @staticmethod
    def _call_tokens(call: ast.Call, callee: str) -> str:
        values = [callee]
        for node in ast.walk(call):
            if isinstance(node, ast.Name):
                values.append(node.id)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                values.append(node.value)
        return " ".join(values)

    def _filesystem(self, call: ast.Call, callee: str) -> tuple[str, str] | None:
        tail = callee.rsplit(".", 1)[-1].casefold()
        lowered = callee.casefold()
        receiver = lowered.rsplit(".", 1)[0] if "." in lowered else ""
        receiver_tail = receiver.rsplit(".", 1)[-1]
        module_head = lowered.split(".", 1)[0]
        path_hint = any(
            token in receiver_tail
            for token in ("config", "dir", "env", "file", "folder", "path", "setting")
        )
        filesystem_receiver = (
            module_head in {"os", "pathlib", "shutil"}
            or receiver_tail in {"fs", "path", "pathlib"}
            or lowered.startswith(("path.", "pathlib.path."))
            or path_hint
        )
        if tail == "open":
            if lowered not in {"open", "builtins.open"} and not filesystem_receiver:
                return None
            mode_node: ast.AST | None = call.args[1] if len(call.args) > 1 else None
            for keyword in call.keywords:
                if keyword.arg == "mode":
                    mode_node = keyword.value
            if mode_node is None:
                return None
            mode = _static_string(mode_node)
            if mode is not None and not any(flag in mode for flag in "wax+"):
                return None
            operation = "filesystem-open-dynamic-mode" if mode is None else "filesystem-open-write"
        elif tail in _MUTATING_FILE_TAILS:
            path_specific = tail in {
                "append_text",
                "appendfile",
                "appendfilesync",
                "createwritestream",
                "hardlink_to",
                "symlink_to",
                "write_bytes",
                "write_text",
                "writefile",
                "writefilesync",
            }
            if not path_specific and not filesystem_receiver:
                return None
            operation = f"filesystem-{tail.replace('_', '-')}"
        else:
            return None
        tokens = self._call_tokens(call, callee)
        category = "credential-config-write" if _CREDENTIAL_HINT.search(tokens) else "filesystem-mutation"
        return category, operation

    def _sink(self, call: ast.Call, callee: str) -> tuple[str, str] | None:
        lowered = callee.casefold()
        tail = lowered.rsplit(".", 1)[-1]
        normalized = _normalized_tail(callee)
        if (
            self.file == _PRODUCTION_RELEASE_BROKER_V03_FILE
            and _scope_name(self.scope) == _PRODUCTION_RELEASE_BROKER_V03_SCOPE
            and callee == _PRODUCTION_RELEASE_BROKER_V03_EXECUTOR_CALL
        ):
            return (
                "interprocess-capability-dispatch",
                "production-release-broker-v03-executor-dispatch",
            )
        if lowered in _SUBPROCESS_NAMES or (
            normalized in {"execfile", "execfilesync", "execsync", "fork", "spawn", "spawnsync"}
            and any(token in lowered for token in ("child_process", "childprocess", "subprocess"))
        ):
            return "subprocess-shell", f"process-{tail.replace('_', '-')}"
        if lowered in _DYNAMIC_CODE_NAMES or lowered.startswith("vm.runin") or lowered == "function":
            return "dynamic-code-execution", f"dynamic-{tail.replace('_', '-')}"
        if lowered in _UNSAFE_DESERIALIZATION_NAMES:
            if lowered in {"yaml.load", "yaml.load_all"}:
                for keyword in call.keywords:
                    if keyword.arg == "Loader" and _callee(keyword.value).casefold().endswith("safeloader"):
                        return None
            return "unsafe-deserialization", f"deserialize-{tail.replace('_', '-')}"
        filesystem = self._filesystem(call, callee)
        if filesystem is not None:
            return filesystem
        if lowered in {"dotenv.set_key", "keyring.set_password"} or (
            tail in {"set_key", "set_password"} and _CREDENTIAL_HINT.search(lowered)
        ):
            return "credential-config-write", f"credential-{tail.replace('_', '-')}"
        receiver = callee.rsplit(".", 1)[0] if "." in callee else ""
        receiver_tail = receiver.rsplit(".", 1)[-1]
        if normalized == "localactionbridge":
            return "local-action-bridge", "local-action-bridge-construction"
        if receiver_tail in self.local_action_receivers and tail in {
            "dispatch",
            "execute",
            "execute_action",
            "invoke",
            "run",
            "send",
        }:
            return "local-action-bridge", f"local-action-{tail.replace('_', '-')}"
        if normalized in _ECONOMIC_TAILS:
            return "economic-mutation", f"economic-{normalized}"
        if _ECONOMIC_ENDPOINT.search(self._call_tokens(call, callee)):
            return "economic-mutation", "economic-provider-http-mutation"
        return None

    def visit_Call(self, node: ast.Call) -> Any:
        callee = _callee(node.func)
        ingress = self._ingress(node, callee)
        if ingress is not None:
            self._add(
                node,
                boundary_kind="ingress",
                category=ingress[0],
                operation=ingress[1],
                canonical=ast.dump(node, include_attributes=False),
            )
        else:
            sink = self._sink(node, callee)
            if sink is not None:
                self._add(
                    node,
                    boundary_kind="sink",
                    category=sink[0],
                    operation=sink[1],
                    canonical=ast.dump(node, include_attributes=False),
                )
        self.generic_visit(node)

    def _is_admitted_type(self, node: ast.AST) -> bool:
        name = _callee(node)
        if name in self.admitted_aliases:
            return True
        return any(name == f"{alias}.AdmittedHNC" for alias in self.os_module_aliases)

    def _guard_outcome(self, node: ast.AST) -> tuple[str, bool] | None:
        negative = False
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            negative = True
            node = node.operand
        if not isinstance(node, ast.Call) or _callee(node.func) != "isinstance" or len(node.args) != 2:
            return None
        if not isinstance(node.args[0], ast.Name) or not self._is_admitted_type(node.args[1]):
            return None
        return node.args[0].id, negative

    def _positive_guard_for(self, node: ast.AST, outcome: str) -> ast.If | None:
        current = node
        while current in self.parent:
            current = self.parent[current]
            if isinstance(current, ast.If):
                guard = self._guard_outcome(current.test)
                if guard == (outcome, False) and _in_body(current, node):
                    return current
            if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
                break
        return None

    def _top_level_statement(
        self,
        function: ast.FunctionDef | ast.AsyncFunctionDef,
        node: ast.AST,
    ) -> ast.stmt | None:
        current = node
        while current in self.parent and self.parent[current] is not function:
            current = self.parent[current]
        return current if isinstance(current, ast.stmt) and self.parent.get(current) is function else None

    def _negative_guard_for(
        self,
        function: ast.FunctionDef | ast.AsyncFunctionDef,
        admission: _Admission,
        handoff: ast.Call,
    ) -> ast.If | None:
        handoff_statement = self._top_level_statement(function, handoff)
        if handoff_statement is None:
            return None
        for statement in function.body:
            if statement is handoff_statement:
                break
            if not isinstance(statement, ast.If) or statement.orelse or not _terminal_block(statement.body):
                continue
            if self._guard_outcome(statement.test) != (admission.outcome, True):
                continue
            if admission.node.lineno < statement.lineno < handoff.lineno:
                return statement
        return None

    def _boundary_variables(
        self,
        function: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> dict[str, ast.Call | None]:
        result: dict[str, ast.Call | None] = {}
        for node in _same_function_nodes(function):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)) or not isinstance(node.value, ast.Call):
                continue
            if not self._is_boundary_constructor(node.value):
                continue
            if self.parent.get(node) is not function:
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                for name in _target_names(target):
                    if self._is_exact_single_binding(
                        owner=function,
                        name=name,
                        expected=node,
                    ):
                        result[name] = node.value
        return result

    @staticmethod
    def _function_parameter_names(
        function: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> frozenset[str]:
        arguments = [
            *function.args.posonlyargs,
            *function.args.args,
            *function.args.kwonlyargs,
        ]
        if function.args.vararg is not None:
            arguments.append(function.args.vararg)
        if function.args.kwarg is not None:
            arguments.append(function.args.kwarg)
        return frozenset(item.arg for item in arguments)

    def _parameter_derived_expression(
        self,
        *,
        function: ast.FunctionDef | ast.AsyncFunctionDef,
        node: ast.AST,
        allowed_parameters: frozenset[str],
        before: tuple[int, int],
        seen: set[str] | None = None,
    ) -> bool:
        if isinstance(node, ast.Constant):
            return True
        if isinstance(node, ast.Name):
            if node.id in allowed_parameters:
                return True
            visited = set() if seen is None else set(seen)
            if node.id in visited:
                return False
            events = self.binding_events.get(function, {}).get(node.id, ())
            if len(events) != 1:
                return False
            event = events[0]
            if not isinstance(event, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
                return False
            if (event.lineno, event.col_offset) >= before:
                return False
            value = event.value
            if value is None:
                return False
            visited.add(node.id)
            return self._parameter_derived_expression(
                function=function,
                node=value,
                allowed_parameters=allowed_parameters,
                before=(event.lineno, event.col_offset),
                seen=visited,
            )
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            return all(
                self._parameter_derived_expression(
                    function=function,
                    node=item,
                    allowed_parameters=allowed_parameters,
                    before=before,
                    seen=seen,
                )
                for item in node.elts
            )
        if isinstance(node, ast.Dict):
            return all(
                item is not None
                and self._parameter_derived_expression(
                    function=function,
                    node=item,
                    allowed_parameters=allowed_parameters,
                    before=before,
                    seen=seen,
                )
                for item in (*node.keys, *node.values)
            )
        if isinstance(node, ast.Attribute):
            return self._parameter_derived_expression(
                function=function,
                node=node.value,
                allowed_parameters=allowed_parameters,
                before=before,
                seen=seen,
            )
        if isinstance(node, ast.Subscript):
            return all(
                self._parameter_derived_expression(
                    function=function,
                    node=item,
                    allowed_parameters=allowed_parameters,
                    before=before,
                    seen=seen,
                )
                for item in (node.value, node.slice)
            )
        if isinstance(node, ast.Starred):
            return self._parameter_derived_expression(
                function=function,
                node=node.value,
                allowed_parameters=allowed_parameters,
                before=before,
                seen=seen,
            )
        if isinstance(node, ast.UnaryOp):
            return self._parameter_derived_expression(
                function=function,
                node=node.operand,
                allowed_parameters=allowed_parameters,
                before=before,
                seen=seen,
            )
        if isinstance(node, ast.BinOp):
            values = (node.left, node.right)
        elif isinstance(node, ast.BoolOp):
            values = tuple(node.values)
        elif isinstance(node, ast.Compare):
            values = (node.left, *node.comparators)
        elif isinstance(node, ast.IfExp):
            values = (node.test, node.body, node.orelse)
        elif isinstance(node, ast.JoinedStr):
            values = tuple(node.values)
        elif isinstance(node, ast.FormattedValue):
            values = (node.value,)
        else:
            return False
        return all(
            self._parameter_derived_expression(
                function=function,
                node=item,
                allowed_parameters=allowed_parameters,
                before=before,
                seen=seen,
            )
            for item in values
        )

    @staticmethod
    def _call_keywords(call: ast.Call) -> set[str] | None:
        if any(item.arg is None for item in call.keywords):
            return None
        names = [item.arg for item in call.keywords if item.arg is not None]
        if len(names) != len(set(names)):
            return None
        return set(names)

    def _complete_boundary_call(
        self,
        call: ast.Call,
        *,
        primary_name: str,
        required_keywords: frozenset[str],
    ) -> ast.AST | None:
        keywords = self._call_keywords(call)
        if keywords is None or len(call.args) > 1 or not required_keywords <= keywords:
            return None
        primary_keywords = [
            item.value for item in call.keywords if item.arg == primary_name
        ]
        supplied = [*call.args, *primary_keywords]
        if len(supplied) != 1:
            return None
        return supplied[0]

    def _admissions(
        self,
        function: ast.FunctionDef | ast.AsyncFunctionDef,
        boundaries: dict[str, ast.Call | None],
    ) -> dict[str, _Admission]:
        result: dict[str, _Admission] = {}
        for node in _same_function_nodes(function):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)) or not isinstance(node.value, ast.Call):
                continue
            call = node.value
            callee = _callee(call.func)
            if not callee.endswith(".admit_external"):
                continue
            boundary = callee.rsplit(".", 1)[0]
            if boundary not in boundaries:
                continue
            boundary_constructor = boundaries[boundary]
            if boundary_constructor is None or boundary_constructor.lineno >= call.lineno:
                continue
            admitted_raw = self._complete_boundary_call(
                call,
                primary_name="raw",
                required_keywords=_ADMISSION_REQUIRED_KEYWORDS,
            )
            if admitted_raw is None:
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = [name for target in targets for name in _target_names(target)]
            if len(names) != 1 or self.parent.get(node) is not function:
                continue
            outcome = names[0]
            if not self._is_exact_single_binding(
                owner=function,
                name=outcome,
                expected=node,
            ):
                continue
            parameters = self._function_parameter_names(function)
            if not isinstance(admitted_raw, ast.Name) or admitted_raw.id not in parameters:
                continue
            result[outcome] = _Admission(
                outcome,
                boundary,
                call,
                frozenset({admitted_raw.id}),
            )
        return result

    def _handoffs(
        self,
        function: ast.FunctionDef | ast.AsyncFunctionDef,
        admissions: dict[str, _Admission],
    ) -> list[_Handoff]:
        result: list[_Handoff] = []
        for node in _same_function_nodes(function):
            if not isinstance(node, ast.Call):
                continue
            callee = _callee(node.func)
            if not callee.endswith(".protect_for_magic_star"):
                continue
            handle = self._complete_boundary_call(
                node,
                primary_name="handle",
                required_keywords=_HANDOFF_REQUIRED_KEYWORDS,
            )
            if handle is None:
                continue
            boundary = callee.rsplit(".", 1)[0]
            if not (
                isinstance(handle, ast.Attribute)
                and handle.attr == "handle"
                and isinstance(handle.value, ast.Name)
            ):
                continue
            outcome = handle.value.id
            admission = admissions.get(outcome)
            if admission is None or admission.boundary != boundary or admission.node.lineno >= node.lineno:
                continue
            positive = self._positive_guard_for(node, outcome)
            negative = self._negative_guard_for(function, admission, node) if positive is None else None
            if positive is not None or negative is not None:
                result.append(_Handoff(outcome, boundary, node, positive, negative))
        return result

    def _candidate_after_negative_guard(
        self,
        candidate: _Candidate,
        handoff: _Handoff,
    ) -> bool:
        assert candidate.function is not None and candidate.node is not None
        guard = handoff.negative_guard
        if guard is None:
            return False
        guard_statement = self._top_level_statement(candidate.function, guard)
        handoff_statement = self._top_level_statement(candidate.function, handoff.node)
        candidate_statement = self._top_level_statement(candidate.function, candidate.node)
        if guard_statement is None or handoff_statement is None or candidate_statement is None:
            return False
        positions = {id(item): index for index, item in enumerate(candidate.function.body)}
        return (
            positions[id(guard_statement)] < positions[id(handoff_statement)] < positions[id(candidate_statement)]
        )

    def _node_after_handoff(
        self,
        function: ast.FunctionDef | ast.AsyncFunctionDef,
        node: ast.AST,
        handoff: _Handoff,
    ) -> bool:
        if handoff.positive_guard is not None:
            return node.lineno > handoff.node.lineno and _in_body(handoff.positive_guard, node)
        guard = handoff.negative_guard
        if guard is None:
            return False
        guard_statement = self._top_level_statement(function, guard)
        handoff_statement = self._top_level_statement(function, handoff.node)
        node_statement = self._top_level_statement(function, node)
        if guard_statement is None or handoff_statement is None or node_statement is None:
            return False
        positions = {id(item): index for index, item in enumerate(function.body)}
        return positions[id(guard_statement)] < positions[id(handoff_statement)] < positions[id(node_statement)]

    def _handoff_packet_name(self, handoff: _Handoff) -> str | None:
        parent = self.parent.get(handoff.node)
        if isinstance(parent, (ast.Assign, ast.AnnAssign)) and parent.value is handoff.node:
            name = self._single_assignment_name(parent)
            owner = self._lexical_owner(parent)
            if (
                name is not None
                and isinstance(owner, (ast.FunctionDef, ast.AsyncFunctionDef))
                and self._is_exact_single_binding(
                    owner=owner,
                    name=name,
                    expected=parent,
                )
            ):
                return name
        return None

    @staticmethod
    def _call_argument(call: ast.Call, name: str, position: int) -> ast.AST | None:
        if len(call.args) > position:
            return call.args[position]
        return next((keyword.value for keyword in call.keywords if keyword.arg == name), None)

    def _handler_is_registry_only(
        self,
        handler: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> bool:
        """Require the registered handler to have no callable escape route.

        A bare-call check is insufficient because ``alias = handler`` followed
        by ``alias(payload)`` bypasses the release boundary without containing
        a call whose callee has the handler's original name.  The only allowed
        load reference is the exact ``handler=...`` value on a canonical
        ``RegisteredCapabilityV02`` construction.  Returning, aliasing,
        decorating, partially applying, storing, or directly calling the
        handler therefore prevents the sink from earning even local-development
        structural coverage.
        """

        references = [
            node
            for node in ast.walk(self.tree)
            if isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Load)
            and node.id == handler.name
        ]
        if len(references) != 1:
            return False
        reference = references[0]
        keyword = self.parent.get(reference)
        call = self.parent.get(keyword) if isinstance(keyword, ast.keyword) else None
        return bool(
            isinstance(keyword, ast.keyword)
            and keyword.arg == "handler"
            and keyword.value is reference
            and isinstance(call, ast.Call)
            and self._matches_constructor(
                call,
                aliases=self.registered_capability_aliases,
                module_aliases=self.star_custody_module_aliases,
                class_name="RegisteredCapabilityV02",
            )
        )

    def _effect_callee_is_payload_or_import_bound(
        self,
        *,
        function: ast.FunctionDef | ast.AsyncFunctionDef,
        call: ast.Call,
        parameters: frozenset[str],
    ) -> bool:
        callee = call.func
        if isinstance(callee, ast.Name):
            return callee.id in self.import_aliases or callee.id in {
                "__import__",
                "eval",
                "exec",
                "open",
            }
        if not isinstance(callee, ast.Attribute):
            return False
        root: ast.AST = callee.value
        while isinstance(root, ast.Attribute):
            root = root.value
        if isinstance(root, ast.Name) and root.id in self.import_aliases:
            return True
        return self._parameter_derived_expression(
            function=function,
            node=callee.value,
            allowed_parameters=parameters,
            before=(call.lineno, call.col_offset),
        )

    def _handler_effects_are_plaintext_derived(
        self,
        handler: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> bool:
        parameters = self._function_parameter_names(handler)
        if len(parameters) != 1:
            return False
        handler_candidates = [
            item for item in self.candidates if item.function is handler
        ]
        if not handler_candidates:
            return False
        for candidate in handler_candidates:
            call = candidate.node
            if not isinstance(call, ast.Call):
                return False
            if not self._effect_callee_is_payload_or_import_bound(
                function=handler,
                call=call,
                parameters=parameters,
            ):
                return False
            if any(item.arg is None for item in call.keywords):
                return False
            values = [*call.args, *(item.value for item in call.keywords)]
            if not all(
                self._parameter_derived_expression(
                    function=handler,
                    node=value,
                    allowed_parameters=parameters,
                    before=(call.lineno, call.col_offset),
                )
                for value in values
            ):
                return False
        return True

    def _release_links(
        self,
    ) -> tuple[
        set[ast.FunctionDef | ast.AsyncFunctionDef],
        set[ast.FunctionDef | ast.AsyncFunctionDef],
    ]:
        handlers: set[ast.FunctionDef | ast.AsyncFunctionDef] = set()
        orchestrators: set[ast.FunctionDef | ast.AsyncFunctionDef] = set()
        if not self.release_registries:
            return handlers, orchestrators
        functions = [
            node
            for node in ast.walk(self.tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        for function in functions:
            boundaries = self._boundary_variables(function)
            admissions = self._admissions(function, boundaries)
            handoffs = self._handoffs(function, admissions)
            handoffs_by_packet = {
                packet_name: handoff
                for handoff in handoffs
                if (packet_name := self._handoff_packet_name(handoff)) is not None
            }
            if not handoffs_by_packet:
                continue
            for node in _same_function_nodes(function):
                if not isinstance(node, ast.Call):
                    continue
                callee = _callee(node.func)
                if not callee.endswith(".release"):
                    continue
                packet_node = self._complete_boundary_call(
                    node,
                    primary_name="packet",
                    required_keywords=_RELEASE_REQUIRED_KEYWORDS,
                )
                if not isinstance(packet_node, ast.Name):
                    continue
                release_variable = callee.rsplit(".", 1)[0]
                registry = self.release_registries.get(release_variable)
                if registry is None:
                    continue
                custody_variable, registered_handlers = registry
                capability_id = _static_string(self._keyword(node, "capability_id"))
                if capability_id is None:
                    continue
                handler = registered_handlers.get(capability_id)
                handoff = handoffs_by_packet.get(packet_node.id)
                if handler is None or handoff is None:
                    continue
                custody_node = self._keyword(handoff.node, "custody")
                if not isinstance(custody_node, ast.Name) or custody_node.id != custody_variable:
                    continue
                if not self._node_after_handoff(function, node, handoff):
                    continue
                if not self._handler_is_registry_only(handler):
                    continue
                if not self._handler_effects_are_plaintext_derived(handler):
                    continue
                handlers.add(handler)
                orchestrators.add(function)
        return handlers, orchestrators

    def _disabled(self, candidate: _Candidate) -> bool:
        assert candidate.node is not None
        current = candidate.node
        while current in self.parent:
            current = self.parent[current]
            if isinstance(current, ast.If):
                test = current.test
                statically_false = isinstance(test, ast.Constant) and test.value is False
                if statically_false and _in_body(current, candidate.node):
                    return True
            if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
                break
        function = candidate.function
        if function is None:
            return False
        for statement in function.body:
            if statement.lineno >= candidate.line:
                break
            if isinstance(statement, ast.Raise) and _HOLD_HINT.search(ast.unparse(statement)):
                return True
        return False

    def classify(self) -> None:
        registered_handlers, release_orchestrators = self._release_links()
        for candidate in self.candidates:
            if self._disabled(candidate):
                candidate.classification = EXPLICIT_HOLD
                candidate.evidence = ("statically-unreachable-or-explicit-hold",)
                continue
            # A v0.3 broker dispatch is an isolation boundary that needs fresh
            # out-of-process attestation.  The same-process V02 structural
            # pattern can never upgrade it to protected coverage.  A statically
            # unreachable dispatch was handled above as an explicit hold;
            # every reachable dispatch remains a blocker.
            if candidate.category == "interprocess-capability-dispatch":
                continue
            function = candidate.function
            if function is None:
                continue
            is_registered_handler = function in registered_handlers
            is_released_ingress = (
                candidate.boundary_kind == "ingress"
                and function in release_orchestrators
            )
            if is_registered_handler or is_released_ingress:
                candidate.classification = LOCAL_DEVELOPMENT_PROTECTED
                candidate.evidence = (
                    "local-os-boundary-construction",
                    "hnc-admit-external",
                    "admitted-hnc-fail-closed-guard",
                    "magic-star-custody-handoff",
                    "registered-capability-handler",
                    "one-use-local-development-release-boundary",
                )


def _scan_python(path: Path, root: Path, source: str) -> tuple[list[_Candidate], list[ParseError]]:
    relative = _relative(path, root)
    try:
        tree = ast.parse(source, filename=relative)
    except SyntaxError as exc:
        return [], [
            ParseError(
                file=relative,
                language="python",
                line=exc.lineno or 1,
                error=f"SyntaxError:{exc.msg}",
            )
        ]
    scanner = _PythonScanner(file=relative, source=source, tree=tree)
    scanner.visit(tree)
    scanner.classify()
    return scanner.candidates, []


def _sanitize_javascript(source: str) -> tuple[str, str | None]:
    output = list(source)
    index = 0
    state = "code"
    quote = ""
    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""
        if state == "code":
            if char == "/" and next_char == "/":
                output[index] = output[index + 1] = " "
                index += 2
                state = "line-comment"
                continue
            if char == "/" and next_char == "*":
                output[index] = output[index + 1] = " "
                index += 2
                state = "block-comment"
                continue
            if char in {"'", '"'}:
                quote = char
                output[index] = " "
                index += 1
                state = "quoted-string"
                continue
            if char == "`":
                quote = char
                output[index] = " "
                index += 1
                state = "template"
                continue
            index += 1
            continue
        if state == "line-comment":
            if char in "\r\n":
                state = "code"
            else:
                output[index] = " "
            index += 1
            continue
        if state == "block-comment":
            if char == "*" and next_char == "/":
                output[index] = output[index + 1] = " "
                index += 2
                state = "code"
            else:
                if char not in "\r\n":
                    output[index] = " "
                index += 1
            continue
        if state in {"quoted-string", "template"}:
            if char == "\\":
                output[index] = " "
                if index + 1 < len(source):
                    if source[index + 1] not in "\r\n":
                        output[index + 1] = " "
                    index += 2
                else:
                    index += 1
                continue
            if char == quote:
                output[index] = " "
                index += 1
                state = "code"
                continue
            if state == "quoted-string" and char in "\r\n":
                # JavaScript single/double-quoted strings cannot cross an
                # unescaped physical newline.  JSX text and regex literals can
                # contain quote characters, so recover at the line boundary
                # instead of blanking the rest of a valid source file.
                state = "code"
                index += 1
                continue
            if char not in "\r\n":
                output[index] = " "
            index += 1
    if state in {"block-comment", "template"}:
        return "".join(output), f"unterminated-{state}"
    return "".join(output), None


_TS_PATTERNS: tuple[tuple[re.Pattern[str], str, str, str], ...] = (
    (
        re.compile(r"\b(?:new\s+)?WebSocketServer\s*\(|\bwebsockets?\s*\.\s*serve\s*\(", re.I),
        "ingress",
        "websocket-server-ingress",
        "websocket-server",
    ),
    (
        re.compile(r"\b(?:Deno|Bun)\s*\.\s*serve\s*\(|\b(?:http|https)\s*\.\s*createServer\s*\(", re.I),
        "ingress",
        "http-server-ingress",
        "http-server",
    ),
    (
        re.compile(r"\b(?:app|api|router|server)\s*\.\s*(?:delete|get|head|listen|options|patch|post|put|route)\s*\(", re.I),
        "ingress",
        "http-server-ingress",
        "http-route-or-listener",
    ),
    (
        re.compile(r"\b(?:child_process\s*\.\s*)?(?:exec|execFile|execFileSync|execSync|fork|spawn|spawnSync)\s*\(", re.I),
        "sink",
        "subprocess-shell",
        "process-execution",
    ),
    (
        re.compile(r"\b(?:eval|Function)\s*\(|\bvm\s*\.\s*runIn(?:Context|NewContext|ThisContext)\s*\(", re.I),
        "sink",
        "dynamic-code-execution",
        "dynamic-code",
    ),
    (
        re.compile(r"\b(?:v8|serialize|serializer)\s*\.\s*(?:deserialize|unserialize)\s*\(", re.I),
        "sink",
        "unsafe-deserialization",
        "unsafe-deserialize",
    ),
    (
        re.compile(r"\b(?:fs\s*\.\s*)?(?:appendFile|appendFileSync|chmod|chown|copyFile|copyFileSync|createWriteStream|mkdir|rename|rm|rmdir|truncate|unlink|writeFile|writeFileSync)\s*\(", re.I),
        "sink",
        "filesystem-mutation",
        "filesystem-mutation",
    ),
    (
        re.compile(r"\bnew\s+LocalActionBridge\s*\(|\blocalActionBridge\s*\.\s*(?:dispatch|execute|invoke|run|send)\s*\(", re.I),
        "sink",
        "local-action-bridge",
        "local-action-bridge",
    ),
    (
        re.compile(
            r"\b(?:amendOrder|cancelAllOrders|cancelOrder|closePosition|closeTrade|createOrder|editOrder|"
            r"placeLimitOrder|placeMarginOrder|placeMarketOrder|placeOrder|replaceOrder|submitOrder)\s*\(",
            re.I,
        ),
        "sink",
        "economic-mutation",
        "economic-provider-mutation",
    ),
)


def _scan_typescript(path: Path, root: Path, source: str) -> tuple[list[_Candidate], list[ParseError]]:
    relative = _relative(path, root)
    sanitized, lexical_error = _sanitize_javascript(source)
    errors = []
    if lexical_error is not None:
        errors.append(ParseError(relative, "typescript", source.count("\n") + 1, lexical_error))
    candidates: list[_Candidate] = []
    occupied: set[tuple[int, int]] = set()
    for pattern, boundary_kind, category, operation in _TS_PATTERNS:
        for match in pattern.finditer(sanitized):
            line = sanitized.count("\n", 0, match.start()) + 1
            column = match.start() - sanitized.rfind("\n", 0, match.start())
            location = (match.start(), match.end())
            if location in occupied:
                continue
            occupied.add(location)
            candidates.append(
                _Candidate(
                    file=relative,
                    line=line,
                    column=column,
                    language="typescript",
                    scope="<typescript-module>",
                    boundary_kind=boundary_kind,
                    category=category,
                    operation=operation,
                    canonical=re.sub(r"\s+", " ", match.group(0)).strip().casefold(),
                    classification=BLOCKER,
                )
            )
    return candidates, errors


def _finding(candidate: _Candidate, occurrence: int) -> Finding:
    material = "\x1f".join(
        (
            candidate.file,
            candidate.language,
            candidate.scope,
            candidate.boundary_kind,
            candidate.category,
            candidate.operation,
            candidate.canonical,
            str(occurrence),
        )
    )
    fingerprint = "osboundary:" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]
    if candidate.classification == LOCAL_DEVELOPMENT_PROTECTED:
        rationale = "The sink is a registered same-process capability selected through the linked local-development release boundary; this is structural lab coverage, not production authorization."
    elif candidate.classification == EXPLICIT_HOLD:
        rationale = "The operation is statically unreachable or enclosed by an explicit fail-closed HOLD/disabled branch."
    else:
        rationale = "No complete structural LocalOSProtectionBoundary-to-registered-capability release path was proven; custody handoff alone does not authorize this operation."
    return Finding(
        file=candidate.file,
        line=candidate.line,
        column=candidate.column,
        language=candidate.language,
        scope=candidate.scope,
        boundary_kind=candidate.boundary_kind,
        category=candidate.category,
        operation=candidate.operation,
        classification=candidate.classification,
        fingerprint=fingerprint,
        evidence=candidate.evidence,
        rationale=rationale,
    )


def audit(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    candidates: list[_Candidate] = []
    parse_errors: list[ParseError] = []
    scanned_by_language: Counter[str] = Counter()
    files = list(iter_source_files(root))
    for path in files:
        relative = _relative(path, root)
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            parse_errors.append(
                ParseError(relative, "unknown", 1, f"{type(exc).__name__}:source-read-failed")
            )
            continue
        if path.suffix.casefold() == ".py":
            scanned_by_language["python"] += 1
            found, errors = _scan_python(path, root, source)
        else:
            scanned_by_language["typescript"] += 1
            found, errors = _scan_typescript(path, root, source)
        candidates.extend(found)
        parse_errors.extend(errors)

    candidates.sort(
        key=lambda item: (
            item.file.casefold(),
            item.line,
            item.column,
            item.category,
            item.operation,
            item.canonical,
        )
    )
    occurrences: Counter[tuple[str, ...]] = Counter()
    findings: list[Finding] = []
    for candidate in candidates:
        key = (
            candidate.file,
            candidate.language,
            candidate.scope,
            candidate.boundary_kind,
            candidate.category,
            candidate.operation,
            candidate.canonical,
        )
        occurrence = occurrences[key]
        occurrences[key] += 1
        findings.append(_finding(candidate, occurrence))

    counts_by_classification = {
        classification: sum(item.classification == classification for item in findings)
        for classification in CLASSIFICATIONS
    }
    counts_by_category = {
        category: sum(item.category == category for item in findings)
        for category in CATEGORIES
    }
    blockers = [item for item in findings if item.classification == BLOCKER]
    inventory_material = "\n".join(sorted(item.fingerprint for item in findings))
    inventory_sha256 = hashlib.sha256(inventory_material.encode("utf-8")).hexdigest()
    parse_errors.sort(key=lambda item: (item.file.casefold(), item.line, item.error))
    certification_limitations = [
        "local-os-protection-boundary-production-ready-false",
        "magic-star-custody-production-ready-false",
        "release-boundary-production-ready-false",
    ]
    if blockers:
        certification_limitations.append("unprotected-high-risk-blockers-remain")
    if parse_errors:
        certification_limitations.append("source-parse-errors-remain")
    return {
        "schema": "aureon.os-protection-boundary-census.v1",
        "root": str(root),
        "source_files_scanned": len(files),
        "files_scanned_by_language": dict(sorted(scanned_by_language.items())),
        "detected_count": len(findings),
        "classified_count": len(findings),
        "blocker_count": len(blockers),
        "explicit_hold_count": counts_by_classification[EXPLICIT_HOLD],
        "protected_count": counts_by_classification[PROTECTED],
        "counts_by_classification": counts_by_classification,
        "counts_by_category": counts_by_category,
        "parse_errors": [asdict(item) for item in parse_errors],
        "inventory_sha256": inventory_sha256,
        "certified_full_os_protection": False,
        "certification_limitations": certification_limitations,
        "findings": [asdict(item) for item in findings],
        "blockers": [asdict(item) for item in blockers],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="emit the truthful inventory without failing solely because blockers remain",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = audit(args.root)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        sys.stdout.write(rendered)
    else:
        args.output.write_text(rendered, encoding="utf-8")
    if result["parse_errors"]:
        return 2
    if result["blocker_count"] and not args.report_only:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
