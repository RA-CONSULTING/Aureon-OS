"""Git-bound source closure for the held VM operator runtime.

The operator imports a large, partly lazy module graph.  A maintained list of
the imports visible in ``operator_server.py`` cannot prove that the VM is
running one revision: transitive and data-driven imports can otherwise resolve
an older file left in the workspace.  This module defines the release contract
as the complete tracked Aureon Python package, its classified package assets,
the few local companion modules reached by that package, and the hardened cloud
entry shims.

Runtime state is deliberately outside the contract.  The functions here only
classify paths and hashes; they never import application code or read secrets.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
from typing import Iterable, Mapping, Sequence


OPERATOR_RUNTIME_CLOSURE_SCHEMA = "aureon.operator-runtime-closure.v1"
OPERATOR_PACKAGE_PREFIX = "aureon-os-upstream/aureon/"
OPERATOR_ENTRYPOINT = OPERATOR_PACKAGE_PREFIX + "operator/operator_server.py"

# Package data that is immutable source/configuration.  Any new non-Python
# package asset must be reviewed and classified here before a release can be
# built.  This prevents a newly tracked cache, credential file, or ledger from
# silently joining a source bundle.
OPERATOR_PACKAGE_ASSETS = frozenset(
    {
        OPERATOR_PACKAGE_PREFIX + "exchanges/trading_gate_analysis_policy.json",
        OPERATOR_PACKAGE_PREFIX + "operator/public_claim_evidence.schema.json",
        OPERATOR_PACKAGE_PREFIX + "operator/website_operator.defaults.json",
        OPERATOR_PACKAGE_PREFIX + "operator/website_operator.schema.json",
        OPERATOR_PACKAGE_PREFIX + "operator/website_operator_receipts.schema.json",
        OPERATOR_PACKAGE_PREFIX + "operator/wearable/icon.svg",
        OPERATOR_PACKAGE_PREFIX + "operator/wearable/index.html",
        OPERATOR_PACKAGE_PREFIX + "operator/wearable/manifest.webmanifest",
        OPERATOR_PACKAGE_PREFIX + "operator/wearable/sw.js",
        OPERATOR_PACKAGE_PREFIX + "operator/wearable/watch.css",
        OPERATOR_PACKAGE_PREFIX + "operator/wearable/watch.js",
        OPERATOR_PACKAGE_PREFIX + "vault/ui/static/aureon-icon.svg",
        OPERATOR_PACKAGE_PREFIX + "vault/ui/static/bridge.html",
        OPERATOR_PACKAGE_PREFIX + "vault/ui/static/bridge_invite.html",
        OPERATOR_PACKAGE_PREFIX + "vault/ui/static/index.html",
        OPERATOR_PACKAGE_PREFIX + "vault/ui/static/manifest.webmanifest",
        OPERATOR_PACKAGE_PREFIX + "vault/ui/static/sw.js",
    }
)

# These files are tracked historical/runtime material, not immutable program
# inputs.  They stay on the data plane and are never copied or deleted by the
# source release transaction.
OPERATOR_PACKAGE_RUNTIME_STATE = frozenset(
    {
        OPERATOR_PACKAGE_PREFIX + "autonomous/7day_current_plan.json",
        OPERATOR_PACKAGE_PREFIX + "data_feeds/crypto_market_map_cache.json",
        OPERATOR_PACKAGE_PREFIX + "trading/barter_graph_cache.json",
    }
)

# Static analysis of the full package finds these repository-local imports
# outside ``aureon``.  They are explicit because broad sibling-directory copies
# would pull ledgers, fixtures, and unrelated launchers into the VM release.
OPERATOR_COMPANION_SOURCES = frozenset(
    {
        "aureon_fusion/__init__.py",
        "aureon_fusion/conscience_hook.py",
        "aureon_fusion/events.py",
        "aureon_fusion/paths.py",
        "aureon_fusion/receipts.py",
        "aureon-os-upstream/Kings_Accounting_Suite/tools/accounting_system_registry.py",
        "aureon-os-upstream/Kings_Accounting_Suite/tools/combined_bank_data.py",
        "aureon-os-upstream/aureon_mycelium.py",
        "aureon-os-upstream/aureon_thought_bus.py",
        "aureon-os-upstream/blueprints.py",
        "aureon-os-upstream/connector.py",
        "aureon-os-upstream/fetcher.py",
        "aureon-os-upstream/phenolic_fingerprint.py",
        "aureon-os-upstream/probability_ultimate_intelligence.py",
        "aureon-os-upstream/scripts/python/ingest_market_history.py",
        "aureon-os-upstream/scripts/validation/audit_economic_mutation_boundaries.py",
        "aureon-os-upstream/scripts/validation/audit_os_protection_boundaries.py",
        "aureon-os-upstream/scripts/validation/audit_saas_compliance.py",
        "aureon-os-upstream/scripts/validation/validate_real_data_contract.py",
        "sero_chirp.py",
        "sero_conscience_engine.py",
        "sero_thoughtbus.py",
    }
)

# The VM operator is held and has no exchange credentials.  These early shims
# are part of the same closure so the large legacy package cannot run without
# the process-wide environment guard.  The public entry is included to retain
# the existing end-to-end ingress-custody revision binding.
OPERATOR_DEPLOYMENT_SOURCES = frozenset(
    {
        "deployment/google-cloud/aureon-cloud-token-broker.service",
        "deployment/google-cloud/cloud_credential_boundary.py",
        "deployment/google-cloud/cloud_http_runtime.py",
        "deployment/google-cloud/cloud_operator.py",
        "deployment/google-cloud/cloud_ui_gateway.py",
        "deployment/google-cloud/operator_runtime_closure.py",
        "deployment/google-cloud/public-entry/aureon-public-bridge.service",
        "deployment/google-cloud/public-entry/public_entry.py",
        "deployment/google-cloud/sitecustomize.py",
        "deployment/google-cloud/vm_token_broker.py",
        "deployment/google-cloud/vm_workload_identity.py",
    }
)

OPERATOR_RUNTIME_TRIGGER_SOURCES = frozenset(
    {OPERATOR_ENTRYPOINT, "deployment/google-cloud/cloud_operator.py"}
)
_PACKAGE_SENTINELS = frozenset(
    {
        OPERATOR_PACKAGE_PREFIX + "__init__.py",
        OPERATOR_PACKAGE_PREFIX + "operator/__init__.py",
        OPERATOR_ENTRYPOINT,
    }
)
_BLOCKED_PARTS = frozenset(
    {
        ".git",
        ".aureon",
        "__pycache__",
        "backups",
        "logs",
        "private",
        "secrets",
        "uploads",
    }
)
_HASH = re.compile(r"[0-9a-f]{40}")
_SHA256 = re.compile(r"[0-9a-f]{64}")


class OperatorRuntimeClosureError(ValueError):
    """The proposed operator source closure is incomplete or unsafe."""


def _repo_path(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise OperatorRuntimeClosureError("invalid_operator_runtime_path")
    if any(character in value for character in ("\\", "\x00", ":", "\n", "\r")):
        raise OperatorRuntimeClosureError("invalid_operator_runtime_path")
    path = PurePosixPath(value)
    if path.is_absolute() or str(path) != value or any(
        part in {"", ".", ".."} for part in path.parts
    ):
        raise OperatorRuntimeClosureError("invalid_operator_runtime_path")
    return value


def _digest_json(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _package_path_kind(relative: str) -> str:
    """Classify one tracked path beneath the Aureon package."""
    relative = _repo_path(relative)
    if not relative.startswith(OPERATOR_PACKAGE_PREFIX):
        raise OperatorRuntimeClosureError("operator_package_path_required")
    parts = tuple(part.casefold() for part in PurePosixPath(relative).parts)
    name = parts[-1]
    if any(part in _BLOCKED_PARTS or part.startswith(".env") for part in parts):
        raise OperatorRuntimeClosureError("private_operator_package_path_forbidden")
    if relative in OPERATOR_PACKAGE_RUNTIME_STATE:
        return "runtime_state"
    if relative in OPERATOR_PACKAGE_ASSETS:
        return "asset"
    if name.endswith(".py"):
        return "python"
    raise OperatorRuntimeClosureError("unclassified_operator_package_asset")


def operator_package_runtime_sources(tracked_paths: Iterable[str]) -> tuple[str, ...]:
    """Return every immutable tracked package input, rejecting ambiguity."""
    package_paths: list[str] = []
    seen: set[str] = set()
    for raw in tracked_paths:
        relative = _repo_path(raw)
        if not relative.startswith(OPERATOR_PACKAGE_PREFIX):
            continue
        folded = relative.casefold()
        if folded in seen:
            raise OperatorRuntimeClosureError("duplicate_operator_package_path")
        seen.add(folded)
        kind = _package_path_kind(relative)
        if kind != "runtime_state":
            package_paths.append(relative)
    selected = tuple(sorted(package_paths))
    if not _PACKAGE_SENTINELS.issubset(selected):
        raise OperatorRuntimeClosureError("operator_package_entrypoints_missing")
    return selected


def required_operator_runtime_sources(tracked_paths: Iterable[str]) -> tuple[str, ...]:
    """Build the exact VM operator source set from a Git tree inventory."""
    return tuple(
        sorted(
            set(operator_package_runtime_sources(tracked_paths))
            | set(OPERATOR_COMPANION_SOURCES)
            | set(OPERATOR_DEPLOYMENT_SOURCES)
        )
    )


def operator_runtime_requested(selected_paths: Iterable[str]) -> bool:
    """Whether a proposed bundle contains an operator runtime entrypoint."""
    return bool(
        OPERATOR_RUNTIME_TRIGGER_SOURCES.intersection(
            _repo_path(path) for path in selected_paths
        )
    )


def _canonical_row(row: Mapping[str, object]) -> dict[str, object]:
    path = _repo_path(row.get("path"))
    sha256 = row.get("sha256")
    size = row.get("size")
    if not isinstance(sha256, str) or not _SHA256.fullmatch(sha256):
        raise OperatorRuntimeClosureError("operator_runtime_row_hash_invalid")
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise OperatorRuntimeClosureError("operator_runtime_row_size_invalid")
    return {"path": path, "sha256": sha256, "size": size}


def _row_index(rows: Sequence[Mapping[str, object]]) -> dict[str, dict[str, object]]:
    indexed: dict[str, dict[str, object]] = {}
    folded: set[str] = set()
    for value in rows:
        if not isinstance(value, Mapping):
            raise OperatorRuntimeClosureError("operator_runtime_row_invalid")
        row = _canonical_row(value)
        path = str(row["path"])
        if path.casefold() in folded:
            raise OperatorRuntimeClosureError("duplicate_operator_runtime_row")
        folded.add(path.casefold())
        indexed[path] = row
    return indexed


def build_operator_runtime_manifest(
    tracked_paths: Iterable[str],
    rows: Sequence[Mapping[str, object]],
    *,
    source_git_tree: str,
) -> dict[str, object]:
    """Bind the exact tracked closure to the already hashed release rows."""
    if not isinstance(source_git_tree, str) or not _HASH.fullmatch(source_git_tree):
        raise OperatorRuntimeClosureError("operator_runtime_git_tree_invalid")
    required = required_operator_runtime_sources(tracked_paths)
    indexed = _row_index(rows)
    missing = set(required) - set(indexed)
    if missing:
        raise OperatorRuntimeClosureError("complete_operator_runtime_sources_required")
    extra_package = {
        path
        for path in indexed
        if path.startswith(OPERATOR_PACKAGE_PREFIX) and path not in required
    }
    if extra_package:
        raise OperatorRuntimeClosureError("operator_runtime_state_selection_forbidden")
    closure_rows = [indexed[path] for path in required]
    return {
        "schema": OPERATOR_RUNTIME_CLOSURE_SCHEMA,
        "entrypoint": OPERATOR_ENTRYPOINT,
        "package_prefix": OPERATOR_PACKAGE_PREFIX,
        "source_git_tree": source_git_tree,
        "files": len(required),
        "paths_sha256": _digest_json(list(required)),
        "payload_sha256": _digest_json(closure_rows),
        "sources": list(required),
    }


def validate_operator_runtime_manifest(
    value: object,
    rows: Sequence[Mapping[str, object]],
    *,
    source_git_tree: str,
) -> frozenset[str]:
    """Validate a transported closure without importing application modules."""
    if not isinstance(value, Mapping):
        raise OperatorRuntimeClosureError("operator_runtime_manifest_required")
    if (
        value.get("schema") != OPERATOR_RUNTIME_CLOSURE_SCHEMA
        or value.get("entrypoint") != OPERATOR_ENTRYPOINT
        or value.get("package_prefix") != OPERATOR_PACKAGE_PREFIX
        or value.get("source_git_tree") != source_git_tree
        or not isinstance(source_git_tree, str)
        or not _HASH.fullmatch(source_git_tree)
    ):
        raise OperatorRuntimeClosureError("operator_runtime_manifest_identity_invalid")
    sources_value = value.get("sources")
    if not isinstance(sources_value, list) or not sources_value:
        raise OperatorRuntimeClosureError("operator_runtime_manifest_sources_invalid")
    sources = tuple(_repo_path(path) for path in sources_value)
    if list(sources) != sorted(set(sources)):
        raise OperatorRuntimeClosureError("operator_runtime_manifest_sources_invalid")
    source_set = frozenset(sources)
    package_sources = {
        path for path in sources if path.startswith(OPERATOR_PACKAGE_PREFIX)
    }
    if not _PACKAGE_SENTINELS.issubset(package_sources):
        raise OperatorRuntimeClosureError("operator_package_entrypoints_missing")
    for path in package_sources:
        if _package_path_kind(path) == "runtime_state":
            raise OperatorRuntimeClosureError("operator_runtime_state_selection_forbidden")
    if not OPERATOR_COMPANION_SOURCES.issubset(source_set) or not (
        OPERATOR_DEPLOYMENT_SOURCES.issubset(source_set)
    ):
        raise OperatorRuntimeClosureError("operator_runtime_boundary_sources_missing")
    allowed = package_sources | set(OPERATOR_COMPANION_SOURCES) | set(
        OPERATOR_DEPLOYMENT_SOURCES
    )
    if set(sources) != allowed:
        raise OperatorRuntimeClosureError("operator_runtime_manifest_source_scope_invalid")
    indexed = _row_index(rows)
    if not source_set.issubset(indexed):
        raise OperatorRuntimeClosureError("operator_runtime_manifest_payload_missing")
    extra_package = {
        path
        for path in indexed
        if path.startswith(OPERATOR_PACKAGE_PREFIX) and path not in source_set
    }
    if extra_package:
        raise OperatorRuntimeClosureError("operator_runtime_state_selection_forbidden")
    closure_rows = [indexed[path] for path in sources]
    if (
        value.get("files") != len(sources)
        or value.get("paths_sha256") != _digest_json(list(sources))
        or value.get("payload_sha256") != _digest_json(closure_rows)
    ):
        raise OperatorRuntimeClosureError("operator_runtime_manifest_digest_invalid")
    return source_set


def stale_operator_python_sources(
    workspace: Path, declared_sources: Iterable[str]
) -> tuple[str, ...]:
    """Find old package modules that could shadow the declared Git closure.

    The caller may transactionally remove the returned regular files.  Runtime
    data and package assets are not returned.  Links fail closed rather than
    being followed.
    """
    expected = {
        _repo_path(path)
        for path in declared_sources
        if str(path).startswith(OPERATOR_PACKAGE_PREFIX) and str(path).endswith(".py")
    }
    package_root = workspace.joinpath(*PurePosixPath(OPERATOR_PACKAGE_PREFIX).parts)
    if not package_root.exists():
        return ()
    if package_root.is_symlink() or not package_root.is_dir():
        raise OperatorRuntimeClosureError("operator_package_root_not_regular_directory")
    stale: list[str] = []
    for directory, names, files in os.walk(package_root, followlinks=False):
        current = Path(directory)
        for name in tuple(names):
            child = current / name
            if child.is_symlink():
                raise OperatorRuntimeClosureError("operator_package_link_forbidden")
            if name == "__pycache__":
                names.remove(name)
        for name in files:
            child = current / name
            if child.is_symlink() or not child.is_file():
                raise OperatorRuntimeClosureError("operator_package_link_forbidden")
            if child.suffix != ".py":
                continue
            relative = child.relative_to(workspace).as_posix()
            if relative not in expected:
                stale.append(relative)
    return tuple(sorted(stale))


def operator_python_cache_files(workspace: Path) -> tuple[str, ...]:
    """Return derived bytecode that must not survive a source cutover."""
    package_root = workspace.joinpath(*PurePosixPath(OPERATOR_PACKAGE_PREFIX).parts)
    if not package_root.exists():
        return ()
    if package_root.is_symlink() or not package_root.is_dir():
        raise OperatorRuntimeClosureError("operator_package_root_not_regular_directory")
    caches: list[str] = []
    for directory, names, files in os.walk(package_root, followlinks=False):
        current = Path(directory)
        for name in names:
            if (current / name).is_symlink():
                raise OperatorRuntimeClosureError("operator_package_link_forbidden")
        for name in files:
            child = current / name
            if child.is_symlink() or not child.is_file():
                raise OperatorRuntimeClosureError("operator_package_link_forbidden")
            if child.suffix in {".pyc", ".pyo"}:
                caches.append(child.relative_to(workspace).as_posix())
    return tuple(sorted(caches))


__all__ = [
    "OPERATOR_COMPANION_SOURCES",
    "OPERATOR_DEPLOYMENT_SOURCES",
    "OPERATOR_ENTRYPOINT",
    "OPERATOR_PACKAGE_ASSETS",
    "OPERATOR_PACKAGE_PREFIX",
    "OPERATOR_PACKAGE_RUNTIME_STATE",
    "OPERATOR_RUNTIME_CLOSURE_SCHEMA",
    "OPERATOR_RUNTIME_TRIGGER_SOURCES",
    "OperatorRuntimeClosureError",
    "build_operator_runtime_manifest",
    "operator_package_runtime_sources",
    "operator_python_cache_files",
    "operator_runtime_requested",
    "required_operator_runtime_sources",
    "stale_operator_python_sources",
    "validate_operator_runtime_manifest",
]
