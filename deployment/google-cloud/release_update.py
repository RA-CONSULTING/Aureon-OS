"""Finite source-only cloud update with held services and durable rollback.

This installer never imports application modules or copies runtime state. A
transaction is atomic to the stopped service set, with atomic individual file
replacements. Boot enablement stays inhibited while file installation is partial.
"""
from __future__ import annotations

import argparse
import contextlib
from datetime import UTC, datetime
import hashlib
import json
import math
import os
import re
import secrets
import ssl
import stat
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath

from cloud_credential_boundary import (
    CLOUD_CREDENTIAL_ISOLATION_ENV,
    CLOUD_EXCHANGE_CREDENTIALS_PINNED_ENV,
    CLOUD_EXCHANGE_CREDENTIAL_ENV_VARS,
    CLOUD_ENV_LOADER_CONTROL_VARS,
    CLOUD_OPERATOR_SAFE_MODE_ENV,
)
from operator_runtime_closure import (
    OPERATOR_COMPANION_SOURCES,
    OPERATOR_PACKAGE_ASSETS,
    OPERATOR_PACKAGE_PREFIX,
    OperatorRuntimeClosureError,
    operator_python_cache_files,
    stale_operator_python_sources,
    validate_operator_runtime_manifest,
)

SCHEMA = "aureon.source-release.v1"
HOLDS = {
    "AUREON_DEPLOYMENT_HOLD": "1", "AUREON_DISABLE_REAL_ORDERS": "1",
    "AUREON_DISABLE_EXCHANGE_MUTATIONS": "1", "AUREON_ORDER_INTENT_PUBLISH": "0",
    "AUREON_LIVE_TRADING": "0", "AUREON_UNIFIED_ORDER_EXECUTOR": "0",
}
ENV_LOADER_CONTROL_VARS = tuple(sorted(CLOUD_ENV_LOADER_CONTROL_VARS))
EXCHANGE_CREDENTIAL_ENV_VARS = tuple(sorted(CLOUD_EXCHANGE_CREDENTIAL_ENV_VARS))
SAFE_EXCHANGE_MODE_ENV = dict(CLOUD_OPERATOR_SAFE_MODE_ENV)
READ_ORGANS = frozenset({
    "real_time_data_feeder", "schumann_real_daemon", "planetary_monitor_daemon",
    "solar_system_collector", "sero_space_weather", "aureon_radar_bridge", "hnc_core",
    "soul_protection_daemon", "mind_neural_canvas", "queen_mind", "heartbeat_daemon",
    "hnc_live_daemon", "global_energy_aggregator", "assessment_snapshot_producer",
    "harmonic_affect_producer", "market_stream_feeder", "unified_market_status",
    "unified_market_trader",
})
# Only these read-only data owners consume the pinned owner provider bundle.
# heartbeat_daemon supplies the NASA key to its held planetary child; the HNC
# daemon owns the keyed NASA/NOAA/USGS source readers. No trading organ receives
# this bundle.
PROVIDER_CONFIG_ORGANS = frozenset({"heartbeat_daemon", "hnc_live_daemon"})
# Retain an already-active legacy service only; do not newly activate expansion.
RETAIN_ONLY = frozenset({"sero_autonomous_expansion"})
HTTP_UNITS = {"aureon-cloud-operator.service": "operator", "aureon-cloud-ui.service": "ui-gateway"}
COLLECTOR_UNITS = {"aureon-cloud-trade-receipt.service": "cloud_trade_receipt_collector.py"}
TOKEN_BROKER_UNIT = "aureon-cloud-token-broker.service"
PUBLIC_BRIDGE_UNIT = "aureon-public-bridge.service"
TOKEN_BROKER_SOURCE = "deployment/google-cloud/vm_token_broker.py"
WORKLOAD_IDENTITY_SOURCE = "deployment/google-cloud/vm_workload_identity.py"
TOKEN_BROKER_UNIT_SOURCE = "deployment/google-cloud/aureon-cloud-token-broker.service"
PUBLIC_BRIDGE_SOURCE = "deployment/google-cloud/public-entry/public_entry.py"
PUBLIC_BRIDGE_UNIT_SOURCE = "deployment/google-cloud/public-entry/aureon-public-bridge.service"
PUBLIC_BRIDGE_INSTALL_ROOT = Path("/srv/aureon/public-entry")
PUBLIC_BRIDGE_INSTALL_SOURCE = PUBLIC_BRIDGE_INSTALL_ROOT / "public_entry.py"
PUBLIC_BRIDGE_CERTIFICATE = Path("/etc/aureon-public/bridge-cert.pem")
PUBLIC_BRIDGE_PRIVATE_KEY = Path("/etc/aureon-public/bridge-key.pem")
PUBLIC_BRIDGE_ENV = Path("/etc/aureon-public/bridge.env")
PUBLIC_BRIDGE_REQUIRED_IP_SANS = ["10.40.0.2"]
PUBLIC_BRIDGE_MINIMUM_REMAINING_VALIDITY_SECONDS = 86_400
PUBLIC_BRIDGE_PLAINTEXT_IDENTITY_ENV = frozenset(
    {
        "AUREON_ALLOWED_USER_EMAILS",
        "AUREON_OWNER_EMAIL",
        "AUREON_IAP_ADMIN_EMAIL",
    }
)
BROKER_SERVICE_ACCOUNT = "aureon-vm-token-broker@aureon-trading.iam.gserviceaccount.com"
BROKER_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
AUTHORITY_RECEIPT_SCHEMA = "aureon.cloud-trading-authority-commission-receipt.v1"
IDENTITY_ROLLBACK_RECEIPT_SCHEMA = "aureon.vm-identity-rollback-receipt.v1"
VM_RELEASE_RECEIPT_SCHEMA = "aureon.gcp.vm-release-readback.v1"
VM_REBOOT_CONTINUITY_SCHEMA = "aureon.gcp.vm-reboot-continuity.v1"
CUTOVER_QUIESCENCE_SCHEMA = "aureon.gcp.vm-cutover-quiescence.v1"
TOKEN_SCHEMA = "aureon.gcp.workload-access-token.v1"
GCP_PROJECT = "aureon-trading"
GCP_PROJECT_NUMBER = "4435775023"
METADATA_ADDRESSES = ("169.254.169.254/32", "fd20:ce::254/128")
CONTROL_READERS_GROUP = "aureon-control-readers"
CONTROL_EXCHANGE_ROOT = "/var/lib/aureon-control-exchange"
RELEASE_LEDGER_DIR = CONTROL_EXCHANGE_ROOT + "/release-ledger"
RELEASE_LEDGER_PATH = RELEASE_LEDGER_DIR + "/release-ledger.jsonl"
TRADE_READBACK_DIR = CONTROL_EXCHANGE_ROOT + "/trade-readback"
TRADE_READBACK_PATH = TRADE_READBACK_DIR + "/latest-terminal-receipt.json"
TRADE_BRIDGE_STATUS_PATH = (
    TRADE_READBACK_DIR + "/latest-order-intent-bridge.json"
)
OPERATOR_INTENT_LEDGER_PATH = (
    "/var/lib/aureon-operator/operator-intent/operator-intent-replay.sqlite3"
)
FIXED_SERVICE_IDENTITIES = {
    "aureon-cloud-operator.service": "aureon-operator",
    "aureon-cloud-ui.service": "aureon-ui",
    "aureon-cloud-trade-receipt.service": "aureon-trade-bridge",
}
SPECIAL_SERVICE_IDENTITIES = {
    TOKEN_BROKER_UNIT: "root",
    PUBLIC_BRIDGE_UNIT: "aureon-public",
}
TOKEN_FILES = {
    "aureon-cloud-operator.service": "/run/aureon-cloud-identity/operator/token.json",
    "aureon-cloud-ui.service": "/run/aureon-cloud-identity/ui/token.json",
    "aureon-cloud-trade-receipt.service": "/run/aureon-cloud-identity/trade-bridge/token.json",
}
COLLECTOR_REQUIRED_SOURCES = frozenset({
    "deployment/google-cloud/cloud_trade_receipt_collector.py",
    "deployment/google-cloud/cloud_order_intent_bridge.py",
    "deployment/google-cloud/cloud_credential_boundary.py",
    "deployment/google-cloud/sitecustomize.py",
    WORKLOAD_IDENTITY_SOURCE,
    "deployment/google-cloud/trading-control/cloud_state.py",
    "deployment/google-cloud/trading-control/contract.py",
    "deployment/google-cloud/trading-control/firestore_ledger.py",
    "deployment/google-cloud/trading-control/make_probe.py",
    "deployment/google-cloud/trading-control/provider_boundary.py",
})
UI_GATEWAY_REQUIRED_SOURCES = frozenset({
    "deployment/google-cloud/cloud_http_runtime.py",
    "deployment/google-cloud/cloud_ui_gateway.py",
    "deployment/google-cloud/cloud_credential_boundary.py",
    WORKLOAD_IDENTITY_SOURCE,
    "aureon-os-upstream/frontend/dist/index.html",
})
READ_ORGAN_REQUIRED_SOURCES = frozenset({
    "deployment/google-cloud/cloud_credential_boundary.py",
    "deployment/google-cloud/cloud_http_runtime.py",
    "deployment/google-cloud/cloud_read_organ.py",
    "deployment/google-cloud/operator_runtime_closure.py",
    "deployment/google-cloud/release_update.py",
    "deployment/google-cloud/sitecustomize.py",
    WORKLOAD_IDENTITY_SOURCE,
})
TOKEN_BROKER_REQUIRED_SOURCES = frozenset(
    {TOKEN_BROKER_SOURCE, WORKLOAD_IDENTITY_SOURCE, TOKEN_BROKER_UNIT_SOURCE}
)
PUBLIC_BRIDGE_REQUIRED_SOURCES = frozenset(
    {PUBLIC_BRIDGE_SOURCE, PUBLIC_BRIDGE_UNIT_SOURCE}
)
BLOCKED_PARTS = frozenset({".git", ".aureon", "logs", "uploads", "node_modules", "__pycache__", "backups", "private", "secrets"})
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_RELEASE_BYTES = 512 * 1024 * 1024


class ReleaseError(RuntimeError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def manifest_payload_sha256(rows: list[dict]) -> str:
    canonical = [
        {"path": row.get("path"), "sha256": row.get("sha256"), "size": row.get("size")}
        for row in rows
    ]
    return digest(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode())


def _manifest_row_index(rows: list[dict]) -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    for row in rows:
        path = row.get("path") if isinstance(row, dict) else None
        if not isinstance(path, str) or path in indexed:
            raise ReleaseError("manifest_path_index_invalid")
        indexed[path] = row
    return indexed


def validate_vm_python_runtime_manifest(
    value: object, rows: list[dict], *, source_git_tree: str
) -> frozenset[str]:
    """Validate the commit-bound full package used by collector/read organs."""
    if not isinstance(value, dict):
        raise ReleaseError("vm_python_runtime_manifest_required")
    sources_value = value.get("sources")
    if (
        value.get("schema") != "aureon.vm-python-runtime-closure.v1"
        or value.get("source_git_tree") != source_git_tree
        or not isinstance(sources_value, list)
        or not sources_value
    ):
        raise ReleaseError("vm_python_runtime_manifest_invalid")
    try:
        sources = tuple(source_path(path) for path in sources_value)
    except ReleaseError as error:
        raise ReleaseError("vm_python_runtime_manifest_invalid") from error
    if list(sources) != sorted(set(sources)):
        raise ReleaseError("vm_python_runtime_manifest_invalid")
    source_set = frozenset(sources)
    package = {path for path in sources if path.startswith(OPERATOR_PACKAGE_PREFIX)}
    if not {
        OPERATOR_PACKAGE_PREFIX + "__init__.py",
        OPERATOR_PACKAGE_PREFIX + "operator/__init__.py",
        OPERATOR_PACKAGE_PREFIX + "operator/operator_server.py",
    }.issubset(package) or not OPERATOR_COMPANION_SOURCES.issubset(source_set):
        raise ReleaseError("vm_python_runtime_boundary_sources_missing")
    if source_set != package | OPERATOR_COMPANION_SOURCES:
        raise ReleaseError("vm_python_runtime_source_scope_invalid")
    indexed = _manifest_row_index(rows)
    if not source_set.issubset(indexed):
        raise ReleaseError("vm_python_runtime_payload_missing")
    extra_package = {
        path for path in indexed if path.startswith(OPERATOR_PACKAGE_PREFIX) and path not in source_set
    }
    if extra_package:
        raise ReleaseError("vm_python_runtime_package_scope_invalid")
    selected = [indexed[path] for path in sources]
    if (
        value.get("files") != len(sources)
        or value.get("payload_sha256") != manifest_payload_sha256(selected)
    ):
        raise ReleaseError("vm_python_runtime_manifest_digest_invalid")
    return source_set


def validate_component_manifest(
    value: object,
    rows: list[dict],
    required: frozenset[str],
    *,
    schema: str,
    source_git_tree: str,
) -> dict:
    if not isinstance(value, dict):
        raise ReleaseError("release_component_manifest_required")
    indexed = _manifest_row_index(rows)
    sources = value.get("sources")
    selected = [indexed[path] for path in sorted(required) if path in indexed]
    if (
        value.get("schema") != schema
        or value.get("source_git_tree") != source_git_tree
        or sources != sorted(required)
        or value.get("files") != len(required)
        or len(selected) != len(required)
        or value.get("payload_sha256") != manifest_payload_sha256(selected)
    ):
        raise ReleaseError("release_component_manifest_invalid")
    return value


def validate_frontend_build_manifest(value: object, rows: list[dict], tree: str) -> None:
    dist_rows = [
        row
        for row in rows
        if str(row.get("path") or "").startswith("aureon-os-upstream/frontend/dist/")
    ]
    if not isinstance(value, dict):
        raise ReleaseError("frontend_dist_manifest_binding_invalid")
    environment_keys = value.get("environment_keys")
    toolchain = value.get("toolchain")
    if (
        value.get("schema") != "aureon.frontend-reproducible-build.v1"
        or value.get("entrypoint") != "aureon-os-upstream/frontend/dist/index.html"
        or value.get("files") != len(dist_rows)
        or value.get("sha256") != manifest_payload_sha256(dist_rows)
        or value.get("source_git_tree") != tree
        or value.get("recipe")
        != ["npm ci --ignore-scripts --no-audit --no-fund", "npm run build"]
        or not isinstance(environment_keys, list)
        or not {
            "VITE_REQUIRE_AUTH",
            "VITE_SUPABASE_URL",
            "VITE_SUPABASE_PUBLISHABLE_KEY",
        }.issubset(environment_keys)
        or environment_keys != sorted(set(environment_keys))
        or re.fullmatch(r"[0-9a-f]{64}", str(value.get("environment_sha256") or "")) is None
        or not isinstance(toolchain, dict)
        or not all(isinstance(toolchain.get(name), str) and toolchain[name] for name in ("node", "npm"))
    ):
        raise ReleaseError("frontend_dist_manifest_binding_invalid")


def read_bytes(path: Path, limit=MAX_FILE_BYTES) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ReleaseError("source_not_regular_file")
    with path.open("rb") as handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        raise ReleaseError("source_size_limit")
    return data


def source_path(value: str) -> str:
    if not isinstance(value, str) or any(character in value for character in ("\\", "\x00", ":", "\n", "\r")):
        raise ReleaseError("invalid_source_path")
    path = PurePosixPath(value)
    if path.is_absolute() or str(path) != value or any(p in {"", ".", ".."} for p in path.parts):
        raise ReleaseError("invalid_source_path")
    workspace_python = len(path.parts) == 1 and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*\.py", value)
    sero_package_python = bool(path.parts and path.parts[0].startswith("sero_") and path.suffix == ".py")
    if not path.parts or (path.parts[0] not in {"aureon-os-upstream", "aureon_fusion", "aureon_radar", "sero_mycelium", "deployment"}
                          and not workspace_python and not sero_package_python):
        raise ReleaseError("source_root_not_allowed")
    lowered = tuple(part.lower() for part in path.parts)
    name = lowered[-1]
    if any(p in BLOCKED_PARTS or p.startswith(".env") for p in lowered):
        raise ReleaseError("runtime_or_private_path_forbidden")
    code_subtree = (path.parts[:2] == ("aureon-os-upstream", "aureon") or
                    path.parts[:3] == ("aureon-os-upstream", "frontend", "src"))
    if any(p in {"state", "autonomy"} for p in lowered) and not code_subtree:
        raise ReleaseError("runtime_or_private_path_forbidden")
    if (name.endswith((".env", ".sqlite", ".sqlite3", ".db", ".jsonl", ".log", ".dpapi", ".pem", ".key", ".enc", ".zip", ".tar", ".gz"))
            or name in {"provider_keys.json", "organ_registry.json", "brain_predictions_history.json", "miner_brain_knowledge.json"}):
        raise ReleaseError("runtime_or_private_file_forbidden")
    if (name.endswith(".json")
            and value not in OPERATOR_PACKAGE_ASSETS
            and any(marker in name for marker in ("approval", "decision", "receipt", "ledger", "history", "portfolio", "position", "credential", "secret", "token"))):
        raise ReleaseError("runtime_json_forbidden")
    if path.parts[0] == "deployment" and path.parts[1:2] != ("google-cloud",):
        raise ReleaseError("deployment_path_not_allowed")
    return value


def confined(root: Path, relative: str) -> Path:
    """Refuse symlink/reparse-point traversal, including existing parent folders."""
    if root.is_symlink() or not root.is_dir():
        raise ReleaseError("root_not_real_directory")
    candidate = root.joinpath(*PurePosixPath(relative).parts)
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise ReleaseError("path_escaped_root")
    cursor = root
    for part in PurePosixPath(relative).parts:
        cursor /= part
        if cursor.exists() or cursor.is_symlink():
            attributes = getattr(cursor.lstat(), "st_file_attributes", 0)
            if cursor.is_symlink() or attributes & 0x400:
                raise ReleaseError("link_in_managed_path")
    return candidate


def durable_write(path: Path, data: bytes, mode: int = 0o600, owner: tuple[int, int] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".release-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        if owner is not None and os.name == "posix":
            os.chown(temporary, *owner)
        os.replace(temporary, path)
        if os.name == "posix":
            directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def durable_unlink(path: Path) -> None:
    """Remove one already-confined regular file and sync its directory."""
    if path.is_symlink() or not path.is_file():
        raise ReleaseError("delete_target_not_regular_file")
    path.unlink()
    if os.name == "posix":
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)


def immutable_source_metadata(path: Path) -> bool:
    """Whether a deployed source is root-owned and non-writable on Linux."""
    if os.name != "posix":
        return True
    if path.is_symlink() or not path.is_file():
        return False
    metadata = path.stat(follow_symlinks=False)
    return metadata.st_uid == 0 and metadata.st_gid == 0 and not (
        stat.S_IMODE(metadata.st_mode) & 0o222
    )


def _source_directory_target(workspace: Path, relative: str) -> Path:
    if relative == ".":
        return workspace
    # ``deployment`` is a necessary ancestor of every allowed
    # ``deployment/google-cloud`` source.  Validate that ancestor through its
    # allowed child rather than inventing the forbidden sibling
    # ``deployment/sentinel.py``.
    probe = (
        "deployment/google-cloud/sentinel.py"
        if relative == "deployment"
        else relative + "/sentinel.py"
    )
    source_path(probe)
    return confined(workspace, relative)


def _directory_metadata(path: Path) -> tuple[int, tuple[int, int]]:
    if path.is_symlink() or not path.is_dir():
        raise ReleaseError("source_parent_not_regular_directory")
    metadata = path.stat(follow_symlinks=False)
    return stat.S_IMODE(metadata.st_mode), (metadata.st_uid, metadata.st_gid)


def operator_source_directory_plan(
    workspace: Path, sources: frozenset[str]
) -> list[dict]:
    """Snapshot every parent needed by the exact operator source closure."""
    if os.name != "posix":
        return []
    relatives = {"."}
    for source in sources:
        source_path(source)
        parent = PurePosixPath(source).parent
        for depth in range(1, len(parent.parts) + 1):
            relatives.add(PurePosixPath(*parent.parts[:depth]).as_posix())
    plan: list[dict] = []
    for relative in sorted(relatives, key=lambda value: (value.count("/"), value)):
        target = _source_directory_target(workspace, relative)
        exists = target.exists()
        if exists:
            mode, owner = _directory_metadata(target)
            after_mode = (mode | 0o555) & ~0o022
        else:
            mode, owner, after_mode = None, None, 0o755
        plan.append(
            {
                "path": relative,
                "before_exists": exists,
                "before_mode": mode,
                "before_owner": list(owner) if owner is not None else None,
                "after_mode": after_mode,
                "after_owner": [0, 0],
            }
        )
    return plan


def _directory_matches(workspace: Path, row: dict, state: str) -> bool:
    target = _source_directory_target(workspace, row["path"])
    if state == "before" and row["before_exists"] is False:
        return not target.exists() and not target.is_symlink()
    if not target.exists():
        return False
    try:
        mode, owner = _directory_metadata(target)
    except ReleaseError:
        return False
    return mode == row[f"{state}_mode"] and list(owner) == row[f"{state}_owner"]


def immutable_source_parent_metadata(path: Path, workspace: Path) -> bool:
    """Require root ownership and no non-root write on every source ancestor."""
    if os.name != "posix":
        return True
    try:
        resolved_workspace = workspace.resolve(strict=True)
        cursor = path.parent.resolve(strict=True)
    except (OSError, RuntimeError):
        return False
    if not cursor.is_relative_to(resolved_workspace):
        return False
    while True:
        try:
            mode, owner = _directory_metadata(cursor)
        except ReleaseError:
            return False
        if owner != (0, 0) or mode & 0o022:
            return False
        if cursor == resolved_workspace:
            return True
        cursor = cursor.parent


def apply_operator_source_directory_plan(workspace: Path, plan: list[dict]) -> None:
    if os.name != "posix":
        return
    for row in plan:
        target = _source_directory_target(workspace, row["path"])
        if not target.exists():
            target.mkdir()
        _directory_metadata(target)
        os.chown(target, *row["after_owner"])
        os.chmod(target, row["after_mode"])


def rollback_operator_source_directory_plan(
    workspace: Path, plan: list[dict]
) -> None:
    if os.name != "posix":
        return
    for row in reversed(plan):
        target = _source_directory_target(workspace, row["path"])
        if row["before_exists"]:
            _directory_metadata(target)
            os.chown(target, *row["before_owner"])
            os.chmod(target, row["before_mode"])
        else:
            try:
                target.rmdir()
            except OSError as error:
                raise ReleaseError("new_source_parent_not_empty_on_rollback") from error


def operator_workspace_inventory(journal: dict) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Read stale source and bytecode inventories for a package transaction."""
    sources = journal.get("runtime_sources") or journal.get("operator_runtime_sources")
    if not sources:
        return (), ()
    try:
        workspace = Path(journal["workspace"])
        if not isinstance(sources, list) or not sources:
            raise OperatorRuntimeClosureError("operator_runtime_manifest_sources_invalid")
        return (
            stale_operator_python_sources(workspace, sources),
            operator_python_cache_files(workspace),
        )
    except OperatorRuntimeClosureError as error:
        raise ReleaseError(str(error)) from error


def save_journal(release: Path, journal: dict) -> None:
    durable_write(release / "journal.json", (json.dumps(journal, sort_keys=True, indent=2) + "\n").encode())


@contextlib.contextmanager
def update_lock(releases: Path):
    releases.mkdir(parents=True, exist_ok=True)
    lock = confined(releases, ".source-update.lock")
    with lock.open("a+b") as handle:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            if lock.stat().st_size == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def organ_name(unit: str) -> str | None:
    match = re.fullmatch(r"aureon-organ@([a-z0-9_]+)\.service", unit)
    return match[1] if match and match[1] in READ_ORGANS | RETAIN_ONLY else None


def validate_service_names(services: list[str]) -> None:
    if not services or len(services) > 32 or len(set(services)) != len(services):
        raise ReleaseError("explicit_unique_owned_services_required")
    if any(
        unit not in HTTP_UNITS
        and unit not in COLLECTOR_UNITS
        and unit not in {TOKEN_BROKER_UNIT, PUBLIC_BRIDGE_UNIT}
        and organ_name(unit) is None
        for unit in services
    ):
        raise ReleaseError("service_not_allowlisted")


def service_uses_broker(unit: str) -> bool:
    return (
        unit in HTTP_UNITS
        or unit in COLLECTOR_UNITS
        or organ_name(unit) in PROVIDER_CONFIG_ORGANS
    )


def service_rank(unit: str) -> tuple[int, str]:
    if unit == TOKEN_BROKER_UNIT:
        return (0, unit)
    if organ_name(unit) in PROVIDER_CONFIG_ORGANS:
        return (1, unit)
    if unit in COLLECTOR_UNITS:
        return (2, unit)
    if organ_name(unit) is not None:
        return (2, unit)
    if unit == "aureon-cloud-operator.service":
        return (3, unit)
    if unit == "aureon-cloud-ui.service":
        return (4, unit)
    if unit == PUBLIC_BRIDGE_UNIT:
        return (5, unit)
    raise ReleaseError("service_not_allowlisted")


def normalise_service_plan(services: list[str]) -> list[str]:
    validate_service_names(services)
    planned = set(services)
    if any(service_uses_broker(unit) for unit in planned):
        planned.add(TOKEN_BROKER_UNIT)
    if PUBLIC_BRIDGE_UNIT in planned and not {
        "aureon-cloud-operator.service",
        "aureon-cloud-ui.service",
    }.issubset(planned):
        raise ReleaseError("public_bridge_requires_operator_and_ui_transaction")
    result = sorted(planned, key=service_rank)
    validate_service_names(result)
    return result


def service_identity(unit: str) -> str:
    """Return the exact non-root identity for one managed service."""
    validate_service_names([unit])
    if unit in SPECIAL_SERVICE_IDENTITIES:
        return SPECIAL_SERVICE_IDENTITIES[unit]
    if unit in FIXED_SERVICE_IDENTITIES:
        return FIXED_SERVICE_IDENTITIES[unit]
    name = organ_name(unit)
    if name in PROVIDER_CONFIG_ORGANS:
        return "aureon-provider"
    # Ordinary read organs have no shared uid. The digest keeps Linux account
    # names bounded even for long organ names and is stable across releases.
    return "aureon-organ-" + hashlib.sha256(unit.encode("ascii")).hexdigest()[:12]


def service_state_directory(unit: str) -> str:
    """Return one systemd-owned persistent directory per managed unit."""
    identity = service_identity(unit)
    if unit in SPECIAL_SERVICE_IDENTITIES:
        raise ReleaseError("special_service_has_no_managed_state_directory")
    name = organ_name(unit)
    if name in PROVIDER_CONFIG_ORGANS:
        return identity + "-" + name.replace("_", "-")
    return identity


def service_token_file(unit: str) -> str | None:
    if unit in {TOKEN_BROKER_UNIT, PUBLIC_BRIDGE_UNIT}:
        return None
    if unit in TOKEN_FILES:
        return TOKEN_FILES[unit]
    if organ_name(unit) in PROVIDER_CONFIG_ORGANS:
        return "/run/aureon-cloud-identity/provider/token.json"
    return None


def require_pinned_secret(project: str, secret: str, version: str, reason: str) -> None:
    if (not all(isinstance(value, str) for value in (project, secret, version))
            or not re.fullmatch(r"(?:[a-z][a-z0-9-]{4,61}[a-z0-9]|[0-9]{6,20})", project)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,255}", secret)
            or not re.fullmatch(r"[1-9][0-9]{0,18}", version)):
        raise ReleaseError(reason)


def require_owner_identity(subject: str, email_sha256: str) -> None:
    """Require one canonical Supabase subject plus a non-plaintext email binding."""
    if not isinstance(subject, str) or not isinstance(email_sha256, str):
        raise ReleaseError("supabase_owner_identity_binding_required")
    # Match the runtime boot gate exactly: one canonical RFC 4122 UUID and one
    # lowercase digest.  This prevents prepare from accepting an identity that
    # the newly installed operator would reject only after the service stop.
    if (
        re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
            subject,
        )
        is None
        or re.fullmatch(r"[0-9a-f]{64}", email_sha256) is None
    ):
        raise ReleaseError("supabase_owner_identity_binding_invalid")


def metadata_identity_snapshot(reader=None) -> dict:
    """Read the VM placement and attached identity without reading a token."""
    if reader is None:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

        def reader(url: str) -> bytes:
            request = urllib.request.Request(url, headers={"Metadata-Flavor": "Google"})
            with opener.open(request, timeout=5) as response:
                raw = response.read(16_385)
            if len(raw) > 16_384:
                raise ReleaseError("vm_attached_identity_readback_invalid")
            return raw

    metadata_root = "http://metadata.google.internal/computeMetadata/v1/"
    account_root = metadata_root + "instance/service-accounts/default/"
    try:
        project = reader(metadata_root + "project/project-id").decode("ascii").strip()
        zone_resource = reader(metadata_root + "instance/zone").decode("ascii").strip()
        instance = reader(metadata_root + "instance/name").decode("ascii").strip()
        email = reader(account_root + "email").decode("ascii").strip()
        scopes = sorted(
            line.strip()
            for line in reader(account_root + "scopes").decode("ascii").splitlines()
            if line.strip()
        )
    except ReleaseError:
        raise
    except Exception as error:
        raise ReleaseError("vm_attached_identity_readback_invalid") from error
    zone = zone_resource.rsplit("/", 1)[-1]
    if (
        re.fullmatch(r"[a-z][a-z0-9-]{4,61}[a-z0-9]", project) is None
        or re.fullmatch(r"[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?", instance) is None
        or re.fullmatch(r"[a-z0-9-]+-[a-z0-9]+[0-9]-[a-z]", zone) is None
        or re.fullmatch(r"[a-z0-9-]+@[a-z0-9-]+\.iam\.gserviceaccount\.com", email) is None
    ):
        raise ReleaseError("vm_attached_identity_readback_invalid")
    if not scopes or any(not scope.startswith("https://www.googleapis.com/auth/") for scope in scopes):
        raise ReleaseError("vm_attached_identity_readback_invalid")
    return {
        "project": project,
        "zone": zone,
        "instance": instance,
        "email": email,
        "scopes": scopes,
    }


def _is_broker_identity(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    return bool(
        value.get("project") == GCP_PROJECT
        and re.fullmatch(r"[a-z0-9-]+-[a-z0-9]+[0-9]-[a-z]", str(value.get("zone") or ""))
        and re.fullmatch(r"[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?", str(value.get("instance") or ""))
        and value.get("email") == BROKER_SERVICE_ACCOUNT
        and value.get("scopes") == [BROKER_SCOPE]
    )


def require_broker_identity(value: dict) -> None:
    if not _is_broker_identity(value):
        raise ReleaseError("vm_token_broker_attached_identity_required")


def _parse_receipt_time(value: object, reason: str) -> float:
    if not isinstance(value, str) or len(value) > 64:
        raise ReleaseError(reason)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC).timestamp()
    except (ValueError, TypeError, OverflowError) as error:
        raise ReleaseError(reason) from error


def validate_public_bridge_certificate_evidence(
    value: object, *, now: float, reason: str
) -> dict:
    """Validate the exact redacted certificate identity carried across layers."""

    if (
        not isinstance(value, dict)
        or set(value)
        != {
            "receipt_sha256",
            "fingerprint_sha256",
            "required_ip_sans",
            "not_before",
            "not_after",
            "minimum_remaining_validity_seconds",
        }
        or re.fullmatch(r"[0-9a-f]{64}", str(value.get("receipt_sha256") or ""))
        is None
        or re.fullmatch(
            r"[0-9a-f]{64}", str(value.get("fingerprint_sha256") or "")
        )
        is None
        or value.get("required_ip_sans") != PUBLIC_BRIDGE_REQUIRED_IP_SANS
        or value.get("minimum_remaining_validity_seconds")
        != PUBLIC_BRIDGE_MINIMUM_REMAINING_VALIDITY_SECONDS
    ):
        raise ReleaseError(reason)
    not_before = _parse_receipt_time(value.get("not_before"), reason)
    not_after = _parse_receipt_time(value.get("not_after"), reason)
    if (
        not_before > now
        or not_after <= now
        or not_after - now < PUBLIC_BRIDGE_MINIMUM_REMAINING_VALIDITY_SECONDS
    ):
        raise ReleaseError(reason)
    return dict(value)


def validate_authority_receipt(
    path: Path, expected_sha256: str, revision: str, *, now: float | None = None
) -> dict:
    raw = read_bytes(path, 1024 * 1024)
    if re.fullmatch(r"[0-9a-f]{64}", expected_sha256 or "") is None or digest(raw) != expected_sha256:
        raise ReleaseError("authority_receipt_hash_mismatch")
    try:
        value = json.loads(raw)
    except (ValueError, TypeError, UnicodeError) as error:
        raise ReleaseError("authority_receipt_invalid") from error
    current = time.time() if now is None else float(now)
    recorded = _parse_receipt_time(value.get("recorded_at"), "authority_receipt_time_invalid")
    if recorded > current + 300 or current - recorded > 21_600:
        raise ReleaseError("authority_receipt_not_fresh")
    provider = value.get("provider_readback")
    image_receipt_hash = value.get("immutable_image_build_receipt_sha256")
    certificate = validate_public_bridge_certificate_evidence(
        value.get("public_bridge_certificate"),
        now=current,
        reason="authority_receipt_certificate_invalid",
    )
    if (
        value.get("schema") != AUTHORITY_RECEIPT_SCHEMA
        or value.get("status") != "staged_attested"
        or value.get("phase") != "staged-revision-attestation"
        or value.get("source_revision") != revision
        or value.get("provider_readback_ok") is not True
        or value.get("provider_error_codes") != []
        or value.get("vm_readback_deferred_to_release_receipt") is not True
        or value.get("cloud_run_staged_without_traffic") is not True
        or value.get("cloud_run_traffic_changed") is not False
        or value.get("secret_payloads_requested") is not False
        or value.get("sensitive_environment_values_returned") is not False
        or value.get("release_authority") is not False
        or value.get("mutation_authority") is not False
        or re.fullmatch(r"[0-9a-f]{64}", str(value.get("contract_sha256") or "")) is None
        or re.fullmatch(r"[0-9a-f]{64}", str(value.get("provider_readback_sha256") or "")) is None
        or re.fullmatch(r"[0-9a-f]{64}", str(image_receipt_hash or "")) is None
        or not isinstance(provider, dict)
        or digest(
            json.dumps(provider, sort_keys=True, separators=(",", ":")).encode(
                "ascii"
            )
        )
        != value.get("provider_readback_sha256")
    ):
        raise ReleaseError("authority_receipt_invalid")
    required_provider_keys = {
        "schema",
        "project",
        "region",
        "contract_sha256",
        "source_revision",
        "image_build_receipt_sha256",
        "public_bridge_certificate",
        "services",
        "secret_values_recorded",
        "release_authority",
        "mutation_authority",
    }
    if (
        set(provider) != required_provider_keys
        or provider.get("schema")
        != "aureon.gcp.cloud-run-staged-provider-readback.v1"
        or provider.get("project") != GCP_PROJECT
        or provider.get("region") != "europe-west1"
        or provider.get("contract_sha256") != value.get("contract_sha256")
        or provider.get("source_revision") != revision
        or provider.get("image_build_receipt_sha256") != image_receipt_hash
        or provider.get("public_bridge_certificate") != certificate
        or provider.get("secret_values_recorded") is not False
        or provider.get("release_authority") is not False
        or provider.get("mutation_authority") is not False
    ):
        raise ReleaseError("authority_receipt_provider_binding_invalid")
    expected_names = {
        "aureon-trade-controller",
        "aureon-trade-review",
        "aureon-trade-dispatch",
        "aureon-trade-executor",
        "aureon-trade-receipt",
        "aureon-fusion-web",
        "aureon-fusion-operator",
    }
    services = provider.get("services")
    if not isinstance(services, list) or len(services) != len(expected_names):
        raise ReleaseError("authority_receipt_provider_binding_invalid")
    observed_names: set[str] = set()
    authority_image: str | None = None
    public_image: str | None = None
    for row in services:
        if not isinstance(row, dict) or set(row) != {
            "name",
            "revision",
            "latest_ready_revision",
            "traffic",
            "image",
            "configuration_sha256",
        }:
            raise ReleaseError("authority_receipt_provider_binding_invalid")
        name = row.get("name")
        staged_revision = row.get("revision")
        image = row.get("image")
        traffic = row.get("traffic")
        expected_repository = (
            "europe-west1-docker.pkg.dev/aureon-trading/aureon-web/"
            + (
                "aureon-public-entry"
                if str(name).startswith("aureon-fusion-")
                else "aureon-trading-authority"
            )
        )
        if (
            name not in expected_names
            or name in observed_names
            or staged_revision != f"{name}-r{revision[:12]}"
            or not isinstance(image, str)
            or re.fullmatch(
                re.escape(expected_repository) + r"@sha256:[0-9a-f]{64}", image
            )
            is None
            or re.fullmatch(
                r"[0-9a-f]{64}", str(row.get("configuration_sha256") or "")
            )
            is None
            or not isinstance(traffic, list)
            or any(
                not isinstance(item, dict)
                or set(item) != {"revision", "percent", "tag"}
                or (
                    item.get("revision") == staged_revision
                    and item.get("percent") != 0
                )
                for item in traffic
            )
        ):
            raise ReleaseError("authority_receipt_provider_binding_invalid")
        observed_names.add(name)
        if str(name).startswith("aureon-fusion-"):
            public_image = public_image or image
            if image != public_image:
                raise ReleaseError("authority_receipt_provider_binding_invalid")
        else:
            authority_image = authority_image or image
            if image != authority_image:
                raise ReleaseError("authority_receipt_provider_binding_invalid")
    if observed_names != expected_names or authority_image == public_image:
        raise ReleaseError("authority_receipt_provider_binding_invalid")
    return {
        "sha256": expected_sha256,
        "recorded_at": value["recorded_at"],
        "contract_sha256": value["contract_sha256"],
        "provider_readback_sha256": value["provider_readback_sha256"],
        "immutable_image_build_receipt_sha256": image_receipt_hash,
        "public_bridge_certificate": certificate,
        "secret_payloads_requested": False,
        "sensitive_environment_values_returned": False,
        "vm_readback_deferred_to_release_receipt": True,
        "cloud_run_staged_without_traffic": True,
        "cloud_run_traffic_changed": False,
    }


def _openssl(*args: str, input_data: bytes | None = None) -> bytes:
    try:
        result = subprocess.run(
            ["/usr/bin/openssl", *args], input=input_data, capture_output=True,
            timeout=15, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ReleaseError("public_bridge_tls_identity_invalid") from error
    if result.returncode != 0 or len(result.stdout) > 1024 * 1024:
        raise ReleaseError("public_bridge_tls_identity_invalid")
    return result.stdout


def _public_bridge_environment_revision(environment: bytes) -> str:
    try:
        lines = environment.decode("utf-8").splitlines()
    except UnicodeError as error:
        raise ReleaseError("public_bridge_environment_invalid") from error
    revisions = [
        line.split("=", 1)[1]
        for line in lines
        if line.startswith("AUREON_REVISION=")
    ]
    if (
        len(revisions) != 1
        or re.fullmatch(r"[0-9a-f]{40}", revisions[0]) is None
    ):
        raise ReleaseError("public_bridge_environment_revision_invalid")
    return revisions[0]


def _public_bridge_environment_identity(
    environment: bytes,
) -> tuple[str | None, list[str]]:
    try:
        lines = environment.decode("utf-8").splitlines()
    except UnicodeError as error:
        raise ReleaseError("public_bridge_environment_invalid") from error
    commitments = [
        line.split("=", 1)[1]
        for line in lines
        if line.startswith("AUREON_IAP_ADMIN_EMAIL_SHA256=")
    ]
    if (
        len(commitments) > 1
        or commitments
        and re.fullmatch(r"[0-9a-f]{64}", commitments[0]) is None
    ):
        raise ReleaseError("public_bridge_environment_identity_invalid")
    plaintext_names = sorted(
        {
            name
            for name in PUBLIC_BRIDGE_PLAINTEXT_IDENTITY_ENV
            if any(line.startswith(name + "=") for line in lines)
        }
    )
    return (commitments[0] if commitments else None), plaintext_names


def _public_bridge_environment_for_release(
    environment: bytes, revision: str, iap_admin_email_sha256: str
) -> bytes:
    if re.fullmatch(r"[0-9a-f]{40}", revision or "") is None:
        raise ReleaseError("public_bridge_environment_revision_invalid")
    if (
        re.fullmatch(r"[0-9a-f]{64}", iap_admin_email_sha256 or "") is None
    ):
        raise ReleaseError("iap_admin_email_commitment_invalid")
    existing = _public_bridge_environment_revision(environment)
    existing_commitment, _plaintext_names = (
        _public_bridge_environment_identity(environment)
    )
    try:
        lines = environment.decode("utf-8").splitlines(keepends=True)
    except UnicodeError as error:  # pragma: no cover - validated above.
        raise ReleaseError("public_bridge_environment_invalid") from error
    result: list[str] = []
    revision_replaced = 0
    commitment_written = False
    for line in lines:
        if line.endswith("\r\n"):
            body, ending = line[:-2], "\r\n"
        elif line.endswith("\n"):
            body, ending = line[:-1], "\n"
        else:
            body, ending = line, ""
        name = body.split("=", 1)[0] if "=" in body else None
        if name in PUBLIC_BRIDGE_PLAINTEXT_IDENTITY_ENV:
            if existing_commitment is None and not commitment_written:
                body = (
                    "AUREON_IAP_ADMIN_EMAIL_SHA256="
                    + iap_admin_email_sha256
                )
                commitment_written = True
            else:
                continue
        elif name == "AUREON_IAP_ADMIN_EMAIL_SHA256":
            body = "AUREON_IAP_ADMIN_EMAIL_SHA256=" + iap_admin_email_sha256
            commitment_written = True
        elif body == f"AUREON_REVISION={existing}":
            body = f"AUREON_REVISION={revision}"
            revision_replaced += 1
        result.append(body + ending)
    if revision_replaced != 1:
        raise ReleaseError("public_bridge_environment_revision_invalid")
    if not commitment_written:
        if result and not result[-1].endswith(("\n", "\r")):
            result[-1] += "\n"
        result.append(
            "AUREON_IAP_ADMIN_EMAIL_SHA256="
            + iap_admin_email_sha256
            + ("\n" if environment.endswith((b"\n", b"\r")) else "")
        )
    updated = "".join(result).encode("utf-8")
    commitment, plaintext_names = _public_bridge_environment_identity(updated)
    if commitment != iap_admin_email_sha256 or plaintext_names:
        raise ReleaseError("public_bridge_environment_identity_invalid")
    if _public_bridge_environment_revision(updated) != revision:
        raise ReleaseError("public_bridge_environment_revision_invalid")
    return updated


def inspect_public_bridge_identity(
    expected_fingerprint: str, revision: str | None
) -> dict:
    """Validate certificate/key metadata and binding without copying either."""
    if os.name != "posix" or os.geteuid() != 0:
        raise ReleaseError("linux_root_required_for_bridge_identity")
    try:
        import grp

        group_id = grp.getgrnam("aureon-public").gr_gid
        directory = PUBLIC_BRIDGE_CERTIFICATE.parent.stat(follow_symlinks=False)
        cert = PUBLIC_BRIDGE_CERTIFICATE.stat(follow_symlinks=False)
        key = PUBLIC_BRIDGE_PRIVATE_KEY.stat(follow_symlinks=False)
        env = PUBLIC_BRIDGE_ENV.stat(follow_symlinks=False)
    except (OSError, KeyError) as error:
        raise ReleaseError("public_bridge_tls_identity_invalid") from error
    if any(path.is_symlink() for path in (PUBLIC_BRIDGE_CERTIFICATE, PUBLIC_BRIDGE_PRIVATE_KEY, PUBLIC_BRIDGE_ENV)):
        raise ReleaseError("public_bridge_tls_identity_invalid")
    if (
        not stat.S_ISDIR(directory.st_mode)
        or directory.st_uid != 0
        or directory.st_gid != group_id
        or stat.S_IMODE(directory.st_mode) != 0o751
        or not stat.S_ISREG(cert.st_mode)
        or cert.st_uid != 0
        or cert.st_gid != group_id
        or stat.S_IMODE(cert.st_mode) != 0o644
        or not stat.S_ISREG(key.st_mode)
        or key.st_uid != 0
        or key.st_gid != group_id
        or stat.S_IMODE(key.st_mode) != 0o640
        or not stat.S_ISREG(env.st_mode)
        or env.st_uid != 0
        or env.st_gid != group_id
        or stat.S_IMODE(env.st_mode) != 0o640
    ):
        raise ReleaseError("public_bridge_tls_identity_metadata_invalid")
    certificate = read_bytes(PUBLIC_BRIDGE_CERTIFICATE, 128 * 1024)
    der = _openssl("x509", "-outform", "DER", input_data=certificate)
    fingerprint = digest(der)
    if fingerprint != expected_fingerprint:
        raise ReleaseError("public_bridge_certificate_fingerprint_mismatch")
    san = _openssl(
        "x509", "-noout", "-ext", "subjectAltName", input_data=certificate
    )
    try:
        san_lines = san.decode("ascii").splitlines()
        san_entries = [
            entry.strip()
            for line in san_lines[1:]
            for entry in line.split(",")
            if entry.strip()
        ]
    except UnicodeError as error:
        raise ReleaseError("public_bridge_certificate_san_invalid") from error
    if san_entries != ["IP Address:10.40.0.2"]:
        raise ReleaseError("public_bridge_certificate_san_invalid")
    dates = _openssl("x509", "-noout", "-dates", input_data=certificate)
    try:
        date_rows = dict(
            line.split("=", 1)
            for line in dates.decode("ascii").splitlines()
            if "=" in line
        )
        not_before_timestamp = ssl.cert_time_to_seconds(date_rows["notBefore"])
        not_after_timestamp = ssl.cert_time_to_seconds(date_rows["notAfter"])
    except (KeyError, UnicodeError, ValueError) as error:
        raise ReleaseError("public_bridge_certificate_validity_invalid") from error
    current = time.time()
    if (
        not_before_timestamp > current
        or not_after_timestamp <= current
        or not_after_timestamp - current
        < PUBLIC_BRIDGE_MINIMUM_REMAINING_VALIDITY_SECONDS
    ):
        raise ReleaseError("public_bridge_certificate_validity_invalid")
    cert_public = _openssl("x509", "-pubkey", "-noout", input_data=certificate)
    key_public = _openssl(
        "pkey", "-pubout", "-in", str(PUBLIC_BRIDGE_PRIVATE_KEY)
    )
    if digest(cert_public) != digest(key_public):
        raise ReleaseError("public_bridge_certificate_key_mismatch")
    environment = read_bytes(PUBLIC_BRIDGE_ENV, 64 * 1024)
    environment_revision = _public_bridge_environment_revision(environment)
    iap_admin_email_sha256, plaintext_identity_names = (
        _public_bridge_environment_identity(environment)
    )
    if revision is not None and environment_revision != revision:
        raise ReleaseError("public_bridge_environment_revision_mismatch")
    return {
        "certificate_fingerprint_sha256": fingerprint,
        "certificate_required_ip_sans": list(PUBLIC_BRIDGE_REQUIRED_IP_SANS),
        "certificate_not_before": datetime.fromtimestamp(
            not_before_timestamp, UTC
        ).isoformat(),
        "certificate_not_after": datetime.fromtimestamp(
            not_after_timestamp, UTC
        ).isoformat(),
        "certificate_minimum_remaining_validity_seconds": (
            PUBLIC_BRIDGE_MINIMUM_REMAINING_VALIDITY_SECONDS
        ),
        "certificate_path": str(PUBLIC_BRIDGE_CERTIFICATE),
        "private_key_preserved": True,
        "environment_revision": environment_revision,
        "environment_sha256": digest(environment),
        "iap_admin_email_sha256": iap_admin_email_sha256,
        "plaintext_identity_environment_names": plaintext_identity_names,
    }


def require_bridge_identity_matches_certificate(
    identity: object, certificate: object
) -> None:
    """Bind a live VM certificate readback to the immutable build identity."""

    evidence = validate_public_bridge_certificate_evidence(
        certificate,
        now=time.time(),
        reason="public_bridge_certificate_evidence_invalid",
    )
    if (
        not isinstance(identity, dict)
        or identity.get("certificate_fingerprint_sha256")
        != evidence["fingerprint_sha256"]
        or identity.get("certificate_required_ip_sans")
        != evidence["required_ip_sans"]
        or identity.get("certificate_not_before") != evidence["not_before"]
        or identity.get("certificate_not_after") != evidence["not_after"]
        or identity.get("certificate_minimum_remaining_validity_seconds")
        != evidence["minimum_remaining_validity_seconds"]
        or identity.get("private_key_preserved") is not True
    ):
        raise ReleaseError("public_bridge_certificate_evidence_mismatch")


def public_bridge_certificate_evidence_from_manifest(
    certificate: object,
) -> dict:
    """Extract and validate the certificate identity bound into a release bundle."""

    if not isinstance(certificate, dict):
        raise ReleaseError("public_bridge_manifest_binding_invalid")
    receipt = certificate.get("receipt")
    if (
        set(certificate) != {"path", "algorithm", "sha256", "receipt"}
        or certificate.get("path") != str(PUBLIC_BRIDGE_CERTIFICATE)
        or certificate.get("algorithm") != "x509-der-sha256"
        or not isinstance(receipt, dict)
        or set(receipt)
        != {
            "schema",
            "sha256",
            "recorded_at",
            "project",
            "zone",
            "instance",
            "fingerprint_sha256",
            "required_ip_sans",
            "not_before",
            "not_after",
            "minimum_remaining_validity_seconds",
        }
        or receipt.get("schema")
        != "aureon.gcp.vm-public-bridge-certificate-receipt.v1"
        or receipt.get("project") != GCP_PROJECT
        or receipt.get("zone") != "europe-west1-b"
        or receipt.get("instance") != "aureon-sero-20260906"
        or receipt.get("fingerprint_sha256") != certificate.get("sha256")
    ):
        raise ReleaseError("public_bridge_manifest_binding_invalid")
    return validate_public_bridge_certificate_evidence(
        {
            "receipt_sha256": receipt.get("sha256"),
            "fingerprint_sha256": receipt.get("fingerprint_sha256"),
            "required_ip_sans": receipt.get("required_ip_sans"),
            "not_before": receipt.get("not_before"),
            "not_after": receipt.get("not_after"),
            "minimum_remaining_validity_seconds": receipt.get(
                "minimum_remaining_validity_seconds"
            ),
        },
        now=time.time(),
        reason="public_bridge_manifest_binding_invalid",
    )


BROKER_WORKLOADS = (
    ("ui", "aureon-vm-ui@aureon-trading.iam.gserviceaccount.com", "aureon-ui", "/run/aureon-cloud-identity/ui/token.json"),
    ("operator", "aureon-vm-operator@aureon-trading.iam.gserviceaccount.com", "aureon-operator", "/run/aureon-cloud-identity/operator/token.json"),
    ("trade-bridge", "aureon-vm-trade-bridge@aureon-trading.iam.gserviceaccount.com", "aureon-trade-bridge", "/run/aureon-cloud-identity/trade-bridge/token.json"),
    ("provider", "aureon-vm-provider@aureon-trading.iam.gserviceaccount.com", "aureon-provider", "/run/aureon-cloud-identity/provider/token.json"),
)


def verify_broker_tokens(*, now: float | None = None) -> list[dict]:
    """Return redacted token freshness/ownership evidence only."""
    if os.name != "posix":
        raise ReleaseError("broker_token_readback_requires_linux")
    import grp
    import pwd

    current = time.time() if now is None else float(now)
    observed_at = datetime.fromtimestamp(current, UTC).isoformat()
    rows: list[dict] = []
    for name, account, user, raw_path in BROKER_WORKLOADS:
        path = Path(raw_path)
        try:
            group = grp.getgrnam(user)
            reader = pwd.getpwnam(user)
            parent = path.parent.stat(follow_symlinks=False)
            metadata = path.stat(follow_symlinks=False)
            raw = read_bytes(path, 16 * 1024)
            value = json.loads(raw)
        except (OSError, KeyError, ValueError, TypeError, UnicodeError) as error:
            raise ReleaseError("broker_token_readback_invalid") from error
        expires = value.get("expires_at_epoch") if isinstance(value, dict) else None
        if (
            path.is_symlink()
            or not stat.S_ISDIR(parent.st_mode)
            or parent.st_uid != 0
            or parent.st_gid != group.gr_gid
            or stat.S_IMODE(parent.st_mode) != 0o750
            or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != 0
            or metadata.st_gid != group.gr_gid
            or stat.S_IMODE(metadata.st_mode) != 0o640
            or value.get("schema") != TOKEN_SCHEMA
            or value.get("service_account") != account
            or value.get("token_type") != "Bearer"
            or not isinstance(value.get("access_token"), str)
            or not 20 <= len(value["access_token"]) <= 8192
            or not isinstance(expires, (int, float))
            or not current + 120 < float(expires) <= current + 1860
        ):
            raise ReleaseError("broker_token_readback_invalid")
        rows.append(
            {
                "workload": name,
                "target_service_account": account,
                "token_path": raw_path,
                "schema": TOKEN_SCHEMA,
                "owner_uid": metadata.st_uid,
                "owner_gid": metadata.st_gid,
                "reader_uid": reader.pw_uid,
                "reader_gid": group.gr_gid,
                "mode": "0640",
                "expires_at": datetime.fromtimestamp(float(expires), UTC).isoformat(),
                "observed_at": observed_at,
                "readback_sha256": digest(raw),
                "secret_value_recorded": False,
            }
        )
    return validate_broker_token_receipts(rows, now=current)


def validate_broker_token_receipts(
    rows: object, *, now: float | None = None, require_current: bool = True
) -> list[dict]:
    """Validate a complete redacted broker readback, including test adapters."""
    if not isinstance(rows, list) or len(rows) != len(BROKER_WORKLOADS):
        raise ReleaseError("broker_token_readback_invalid")
    expected = {
        name: (account, user, path)
        for name, account, user, path in BROKER_WORKLOADS
    }
    current = time.time() if now is None else float(now)
    observed_names: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ReleaseError("broker_token_readback_invalid")
        name = row.get("workload")
        if name not in expected or name in observed_names:
            raise ReleaseError("broker_token_readback_invalid")
        observed_names.add(name)
        account, _user, path = expected[name]
        try:
            observed = _parse_receipt_time(
                row.get("observed_at"), "broker_token_readback_invalid"
            )
            expires = _parse_receipt_time(
                row.get("expires_at"), "broker_token_readback_invalid"
            )
        except ReleaseError:
            raise
        if (
            row.get("target_service_account") != account
            or row.get("token_path") != path
            or row.get("schema") != TOKEN_SCHEMA
            or not isinstance(row.get("owner_uid"), int)
            or isinstance(row.get("owner_uid"), bool)
            or not isinstance(row.get("owner_gid"), int)
            or isinstance(row.get("owner_gid"), bool)
            or not isinstance(row.get("reader_uid"), int)
            or isinstance(row.get("reader_uid"), bool)
            or not isinstance(row.get("reader_gid"), int)
            or isinstance(row.get("reader_gid"), bool)
            or row.get("owner_uid") != 0
            or row.get("owner_gid") != row.get("reader_gid")
            or row.get("mode") != "0640"
            or row.get("secret_value_recorded") is not False
            or re.fullmatch(r"[0-9a-f]{64}", str(row.get("readback_sha256") or "")) is None
            or require_current and abs(current - observed) > 300
            or not observed + 120 < expires <= observed + 1860
        ):
            raise ReleaseError("broker_token_readback_invalid")
    if observed_names != set(expected):
        raise ReleaseError("broker_token_readback_invalid")
    return [dict(row) for row in rows]


def wait_for_broker_tokens() -> list[dict]:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            return verify_broker_tokens()
        except ReleaseError:
            time.sleep(1)
    raise ReleaseError("broker_tokens_not_fresh")


def verify_public_bridge_liveness(_unit: str, _revision: str) -> dict:
    context = ssl.create_default_context(cafile=str(PUBLIC_BRIDGE_CERTIFICATE))
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=context), NoRedirect()
    )
    request = urllib.request.Request("https://10.40.0.2:8443/__aureon_health")
    try:
        with opener.open(request, timeout=5) as response:
            status = response.status
            body = response.read(4097)
    except urllib.error.HTTPError as error:
        status = error.code
        body = error.read(4097)
    except Exception as error:
        raise ReleaseError("public_bridge_tls_health_unavailable") from error
    if status not in {200, 400, 401, 403, 503} or len(body) > 4096:
        raise ReleaseError("public_bridge_tls_health_unavailable")
    return {
        "tls": True,
        "http_status": status,
        "certificate_pinned": True,
        "response_sha256": digest(body),
    }


def render_unit(unit: str, workspace: Path, revision: str, project: str, secret: str, version: str,
                tenant_secret: str = "", tenant_version: str = "",
                provider_secret: str = "", provider_version: str = "",
                owner_subject: str = "", owner_email_sha256: str = "") -> bytes:
    """Commands contain only validated paths and secret identifiers, never values."""
    validate_service_names([unit])
    if re.search(r"[^A-Za-z0-9_./-]", str(workspace)):
        raise ReleaseError("unsupported_cloud_workspace_path")
    runner = workspace / "deployment/google-cloud"
    identity = service_identity(unit)
    state_directory = service_state_directory(unit)
    state_root = f"/var/lib/{state_directory}"
    cache_root = f"/var/cache/{state_directory}"
    token_file = service_token_file(unit)
    if unit in HTTP_UNITS:
        require_pinned_secret(project, secret, version, "pinned_cloud_secret_identifiers_required")
        shim = "cloud_operator.py" if HTTP_UNITS[unit] == "operator" else "cloud_ui_gateway.py"
        dist_argument = f"--dist-root {workspace}/aureon-os-upstream/frontend/dist " if HTTP_UNITS[unit] == "ui-gateway" else ""
        command = (f"/srv/aureon/venv/bin/python {runner}/{shim} "
                   f"--source-root {workspace}/aureon-os-upstream {dist_argument}"
                   f"--revision {revision} --project {project} --secret {secret} --secret-version {version}")
        if HTTP_UNITS[unit] == "operator":
            require_pinned_secret(project, tenant_secret, tenant_version,
                                  "pinned_cloud_tenant_secret_identifiers_required")
            require_pinned_secret(project, provider_secret, provider_version,
                                  "pinned_cloud_owner_provider_secret_identifiers_required")
            require_owner_identity(owner_subject, owner_email_sha256)
            command += f" --tenant-secret {tenant_secret} --tenant-secret-version {tenant_version}"
            command += f" --provider-secret {provider_secret} --provider-secret-version {provider_version}"
    elif unit in COLLECTOR_UNITS:
        command = (
            f"/srv/aureon/venv/bin/python {runner}/{COLLECTOR_UNITS[unit]} "
            f"--revision {revision} "
            f"--output {TRADE_READBACK_PATH}"
        )
    else:
        name = organ_name(unit)
        command = f"/srv/aureon/venv/bin/python {runner}/cloud_read_organ.py {name}"
        if name in PROVIDER_CONFIG_ORGANS:
            require_pinned_secret(project, provider_secret, provider_version,
                                  "pinned_cloud_owner_provider_secret_identifiers_required")
            command += (f" --project {project} --provider-secret {provider_secret}"
                        f" --provider-secret-version {provider_version}")
    environment = {**HOLDS, **SAFE_EXCHANGE_MODE_ENV, "SERO_WORKSPACE": str(workspace),
                   "SERO_STATE_ROOT": f"{state_root}/runtime",
                   "AUREON_SERVICE_STATE_DIR": state_root,
                   "XDG_CACHE_HOME": cache_root,
                   "MPLCONFIGDIR": f"{cache_root}/matplotlib",
                   # Keep the early sitecustomize boundary first for this VM
                   # service and every Python child the organ registry starts.
                   "PYTHONPATH": f"{runner}:{workspace}:{workspace}/aureon-os-upstream",
                   "PYTHONUNBUFFERED": "1", "PYTHONDONTWRITEBYTECODE": "1",
                   "PYTHON_DOTENV_DISABLED": "1",
                   "AUREON_VM_TOKEN_BROKER_REQUIRED": "1",
                   "AUREON_GCP_PROJECT_NUMBER": GCP_PROJECT_NUMBER,
                   CLOUD_CREDENTIAL_ISOLATION_ENV: "1",
                   CLOUD_EXCHANGE_CREDENTIALS_PINNED_ENV: "1"}
    if token_file is not None:
        environment["AUREON_GOOGLE_TOKEN_FILE"] = token_file
    read_only_paths = [str(workspace)]
    if token_file is not None:
        read_only_paths.append(str(PurePosixPath(token_file).parent))
    inaccessible_token_paths = [
        path
        for path in {
            *TOKEN_FILES.values(),
            "/run/aureon-cloud-identity/provider/token.json",
        }
        if path != token_file
    ]
    state_lines: list[str] = [
        f"StateDirectory={state_directory}",
        "StateDirectoryMode=0700",
        f"CacheDirectory={state_directory}",
        "CacheDirectoryMode=0700",
    ]
    writable_paths = [state_root, cache_root]
    if HTTP_UNITS.get(unit) == "operator":
        environment.update({"AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS": "1", "AUREON_AUDIT_MODE": "1",
                            "AUREON_LLM_ALLOW_HTTP_IN_AUDIT": "1", "AUREON_LLM_REQUEST_TIMEOUT_S": "15",
                            "AUREON_OPERATOR_TIMEOUT_S": "15", "AUREON_OPERATOR_MAX_RETRIES": "0",
                            "AUREON_COGNITION_MAX_MODEL_CALLS": "3"})
        environment["AUREON_CLOUD_TRADE_READBACK_PATH"] = TRADE_READBACK_PATH
        environment["AUREON_CLOUD_TRADE_BRIDGE_STATUS_PATH"] = (
            TRADE_BRIDGE_STATUS_PATH
        )
        environment["AUREON_SUPABASE_OWNER_SUBJECT"] = owner_subject
        environment["AUREON_SUPABASE_OWNER_EMAIL_SHA256"] = owner_email_sha256
        # systemd creates this persistent directory owned by the service user
        # before applying ProtectSystem/ProtectHome. The keystore tightens all
        # tenant subdirectories and files beneath it as well.
        environment["AUREON_KEYSTORE_DIR"] = f"{state_root}/keystore"
        environment["AUREON_FEATURE_SWITCHBOARD_DIR"] = f"{state_root}/feature-switchboard"
        environment["AUREON_OPERATOR_INTENT_LEDGER"] = OPERATOR_INTENT_LEDGER_PATH
        environment["AUREON_RELEASE_LEDGER_PATH"] = RELEASE_LEDGER_PATH
        writable_paths.append(RELEASE_LEDGER_DIR)
        read_only_paths.append(TRADE_READBACK_DIR)
    if unit in COLLECTOR_UNITS:
        environment["AUREON_RELEASE_LEDGER_PATH"] = RELEASE_LEDGER_PATH
        environment["AUREON_CLOUD_TRADE_READBACK_PATH"] = TRADE_READBACK_PATH
        environment["AUREON_CLOUD_TRADE_LIVE_READBACK_PATH"] = (
            f"{state_root}/latest-live-terminal-receipt.json"
        )
        environment["AUREON_ORDER_INTENT_STATE_PATH"] = (
            f"{state_root}/order-intent-bridge-state.json"
        )
        environment["AUREON_ORDER_INTENT_STATUS_PATH"] = TRADE_BRIDGE_STATUS_PATH
        writable_paths.append(TRADE_READBACK_DIR)
        read_only_paths.append(RELEASE_LEDGER_DIR)
    description = (
        "Aureon cloud receipt collector and governed owner intent bridge (local executor held)"
        if unit in COLLECTOR_UNITS else "Aureon held cloud service"
    )
    dotenv_paths = (
        workspace / ".env",
        workspace / "aureon-os-upstream/.env",
        workspace / "aureon_radar/.env",
        PurePosixPath("/workspaces/aureon-trading/.env"),
    )
    dependencies = ["network-online.target"]
    if token_file is not None:
        dependencies.append(TOKEN_BROKER_UNIT)
    lines = ["# Managed source release; no action release authority.", "[Unit]",
             f"Description={description}", f"After={' '.join(dependencies)}", "Wants=network-online.target",
             *([f"Requires={TOKEN_BROKER_UNIT}"] if token_file is not None else []),
             "StartLimitIntervalSec=300", "StartLimitBurst=4", "[Service]", "Type=simple",
             f"User={identity}", f"Group={identity}",
             *([f"SupplementaryGroups={CONTROL_READERS_GROUP}"]
               if unit == "aureon-cloud-operator.service" or unit in COLLECTOR_UNITS else []),
             *(["DynamicUser=yes"] if unit not in FIXED_SERVICE_IDENTITIES and organ_name(unit) not in PROVIDER_CONFIG_ORGANS else []),
             f"WorkingDirectory={workspace}",
             f"UnsetEnvironment={' '.join((*ENV_LOADER_CONTROL_VARS, *EXCHANGE_CREDENTIAL_ENV_VARS))}",
             *[f"Environment={key}={value}" for key, value in environment.items()],
             *state_lines, f"ExecStart={command}", "Restart=on-failure", "RestartSec=20", "TimeoutStopSec=45", "KillMode=control-group",
             ("UMask=0027" if unit == "aureon-cloud-operator.service" or unit in COLLECTOR_UNITS else "UMask=0077"),
             "NoNewPrivileges=true", "PrivateTmp=true", "ProtectHome=true", "ProtectSystem=strict",
             "ProtectProc=invisible", "ProcSubset=pid",
             *[f"IPAddressDeny={address}" for address in METADATA_ADDRESSES],
             f"InaccessiblePaths={' '.join('-' + str(path) for path in (*dotenv_paths, *inaccessible_token_paths))}",
             f"ReadOnlyPaths={' '.join(read_only_paths)}",
             f"ReadWritePaths={' '.join(writable_paths)}", "CapabilityBoundingSet=", "RestrictSUIDSGID=true",
             "[Install]", "WantedBy=multi-user.target", ""]
    return "\n".join(lines).encode()


class Systemd:
    """Every operation is finite and restricted to the supplied unit inventory."""
    def __init__(self, workspace: Path, unit_root: Path, allowed: list[str]):
        if os.name != "posix" or os.geteuid() != 0:
            raise ReleaseError("linux_root_required_for_systemd")
        validate_service_names(allowed)
        self.workspace, self.unit_root, self.allowed = workspace, unit_root, set(allowed)

    def run(self, operation: str, *args: str, timeout=60) -> str:
        result = subprocess.run(["/bin/systemctl", operation, *args], capture_output=True, text=True, timeout=timeout)
        if result.returncode:
            raise ReleaseError("systemd_operation_failed_" + operation)
        return result.stdout

    def snapshot(self, unit: str) -> dict:
        if unit not in self.allowed:
            raise ReleaseError("service_outside_plan")
        raw = self.run(
            "show", unit,
            "--property=LoadState,ActiveState,SubState,MainPID,UnitFileState,User,Group,FragmentPath,ExecStart,WorkingDirectory,Result,ExecMainStatus,ActiveEnterTimestamp",
        )
        fields = dict(line.split("=", 1) for line in raw.splitlines() if "=" in line)
        if fields.get("LoadState") == "not-found":
            return {"exists": False, "active": False, "enabled": False, "main_pid": 0}
        fragment = fields.get("FragmentPath")
        allowed_fragments = {str(self.unit_root / unit)}
        if organ_name(unit):
            allowed_fragments.add(str(self.unit_root / "aureon-organ@.service"))
        command = fields.get("ExecStart", "")
        shim = "cloud_operator.py" if HTTP_UNITS.get(unit) == "operator" else "cloud_ui_gateway.py"
        if unit == TOKEN_BROKER_UNIT:
            runner_names, role_argument = ["vm_token_broker.py"], "vm_token_broker.py"
        elif unit == PUBLIC_BRIDGE_UNIT:
            runner_names, role_argument = [], "public_entry:create_app()"
        elif unit in HTTP_UNITS:
            runner_names, role_argument = [shim], "--source-root "
        elif unit in COLLECTOR_UNITS:
            runner_names, role_argument = [COLLECTOR_UNITS[unit]], COLLECTOR_UNITS[unit]
        else:
            runner_names, role_argument = ["cloud_read_organ.py", "cloud_organ.py"], f" {organ_name(unit)}"
        runners = [str(self.workspace / "deployment/google-cloud" / name) for name in runner_names]
        configured_user = fields.get("User")
        allowed_users = {service_identity(unit)}
        if unit not in {TOKEN_BROKER_UNIT, PUBLIC_BRIDGE_UNIT}:
            allowed_users.add("aureon")
        runner_matches = (
            fields.get("WorkingDirectory") == str(PUBLIC_BRIDGE_INSTALL_ROOT)
            if unit == PUBLIC_BRIDGE_UNIT
            else any(runner in command for runner in runners)
        )
        if fields.get("LoadState") != "loaded" or configured_user not in allowed_users or fragment not in allowed_fragments or not runner_matches or role_argument not in command:
            raise ReleaseError("existing_service_ownership_unverified")
        active = fields.get("ActiveState")
        if active not in {"active", "inactive", "failed"}:
            raise ReleaseError("service_transition_in_progress")
        main_pid = int(fields.get("MainPID", "0"))
        if active == "active" and (fields.get("SubState") != "running" or main_pid <= 0):
            raise ReleaseError("active_service_has_no_running_owned_process")
        try:
            exec_main_status = int(fields.get("ExecMainStatus", "0"))
        except ValueError as error:
            raise ReleaseError("existing_service_status_invalid") from error
        return {
            "exists": True,
            "active": active == "active",
            "enabled": fields.get("UnitFileState") == "enabled",
            "main_pid": main_pid,
            "user": configured_user,
            "result": fields.get("Result") or None,
            "exec_main_status": exec_main_status,
            "started_at": fields.get("ActiveEnterTimestamp") or None,
        }

    def stop(self, unit: str) -> None:
        self.snapshot(unit)
        self.run("stop", unit)
        if self.snapshot(unit)["active"]:
            raise ReleaseError("service_did_not_stop")

    def start(self, unit: str) -> None:
        self.snapshot(unit)
        self.run("start", unit)
        current = self.snapshot(unit)
        if current.get("user") != service_identity(unit):
            raise ReleaseError("deployed_service_identity_mismatch")
        if not current["active"]:
            raise ReleaseError("service_did_not_start")

    def restart(self, unit: str) -> None:
        self.snapshot(unit)
        self.run("restart", unit)
        current = self.snapshot(unit)
        if current.get("user") != service_identity(unit) or not current["active"]:
            raise ReleaseError("service_did_not_restart")

    def reload(self) -> None:
        self.run("daemon-reload")

    def enabled(self, unit: str, value: bool) -> None:
        if unit not in self.allowed:
            raise ReleaseError("service_outside_plan")
        self.run("enable" if value else "disable", unit)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def verify_http(unit: str, revision: str) -> dict | None:
    if unit not in HTTP_UNITS:
        return None
    port = 8080 if HTTP_UNITS[unit] == "operator" else 5173
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            with opener.open(f"http://127.0.0.1:{port}/__aureon_health", timeout=3) as response:
                body = response.read(16385)
                if len(body) > 16384:
                    raise ReleaseError("health_response_too_large")
                row = json.loads(body)
            if (row.get("schema") == "aureon.cloud-http-health.v1" and row.get("revision") == revision
                    and row.get("role") == HTTP_UNITS[unit] and row.get("ready") is True
                    and row.get("deployment_hold") is True and row.get("release_authority") is False
                    and row.get("tenant_auth_ready") is True):
                return {
                    "schema": row["schema"],
                    "revision": revision,
                    "role": row["role"],
                    "ready": True,
                    "deployment_hold": True,
                    "release_authority": False,
                    "tenant_auth_ready": True,
                    "response_sha256": digest(body),
                }
        except Exception:
            pass
        time.sleep(1)
    raise ReleaseError("exact_revision_held_http_health_unavailable")


def prepare(bundle: Path, workspace: Path, releases: Path, units: Path, services: list[str], controller,
            *, project: str = "", secret: str = "", version: str = "",
            tenant_secret: str = "", tenant_version: str = "",
            provider_secret: str = "", provider_version: str = "",
            owner_subject: str = "", owner_email_sha256: str = "",
            iap_admin_email_sha256: str = "",
            identity_snapshot=metadata_identity_snapshot,
            bridge_identity=inspect_public_bridge_identity) -> Path:
    services = normalise_service_plan(services)
    manifest = json.loads(read_bytes(bundle / "manifest.json", 4 * 1024 * 1024))
    revision, release_id = manifest.get("revision"), manifest.get("release_id")
    if manifest.get("schema") != SCHEMA or not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ReleaseError("manifest_schema_or_revision_invalid")
    if not isinstance(release_id, str) or not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8,16}", release_id):
        raise ReleaseError("dated_release_id_required")
    rows = manifest.get("files")
    if not isinstance(rows, list) or not rows or len(rows) > 20000:
        raise ReleaseError("bounded_nonempty_file_manifest_required")
    if (manifest.get("source_git_revision") != revision
            or not re.fullmatch(r"[0-9a-f]{40}", str(manifest.get("source_git_tree") or ""))
            or manifest.get("payload_sha256") != manifest_payload_sha256(rows)):
        raise ReleaseError("git_revision_or_payload_binding_invalid")
    with update_lock(releases):
        for pending in releases.glob("*/journal.json"):
            previous = json.loads(read_bytes(pending, 16 * 1024 * 1024))
            if previous.get("phase") not in {"committed", "rolled_back", "prepared"}:
                raise ReleaseError("previous_transaction_requires_rollback")
        payload, seen, total = [], set(), 0
        for row in rows:
            relative = source_path(row.get("path"))
            if relative.casefold() in seen:
                raise ReleaseError("duplicate_manifest_path")
            seen.add(relative.casefold())
            data = read_bytes(confined(bundle / "files", relative))
            if row.get("sha256") != digest(data) or row.get("size") != len(data):
                raise ReleaseError("manifest_hash_or_size_mismatch")
            total += len(data)
            if total > MAX_RELEASE_BYTES:
                raise ReleaseError("release_size_limit")
            if relative.endswith(".py"):
                compile(data, relative, "exec")  # syntax preflight; no import/execution/pycache
            payload.append(("source", relative, data))
        operator_runtime_sources: frozenset[str] = frozenset()
        runtime_sources: frozenset[str] = frozenset()
        operator_stale_sources: tuple[str, ...] = ()
        operator_python_caches: tuple[str, ...] = ()
        operator_source_directories: list[dict] = []
        package_services = {
            unit for unit in services
            if unit == "aureon-cloud-operator.service"
            or unit in COLLECTOR_UNITS
            or organ_name(unit) is not None
        }
        if set(services) & set(COLLECTOR_UNITS) and not COLLECTOR_REQUIRED_SOURCES.issubset(seen):
            raise ReleaseError("trade_receipt_and_intent_bridge_sources_required")
        if any(organ_name(unit) is not None for unit in services) and not READ_ORGAN_REQUIRED_SOURCES.issubset(seen):
            raise ReleaseError("complete_read_organ_runtime_sources_required")
        if package_services:
            try:
                if "aureon-cloud-operator.service" in services:
                    operator_runtime_sources = validate_operator_runtime_manifest(
                        manifest.get("operator_runtime"),
                        rows,
                        source_git_tree=manifest.get("source_git_tree"),
                    )
                runtime_sources = validate_vm_python_runtime_manifest(
                    manifest.get("vm_python_runtime"),
                    rows,
                    source_git_tree=manifest.get("source_git_tree"),
                )
                operator_stale_sources = stale_operator_python_sources(
                    workspace, runtime_sources
                )
                operator_python_caches = operator_python_cache_files(workspace)
                operator_source_directories = operator_source_directory_plan(
                    workspace, frozenset(row["path"] for row in rows)
                )
            except OperatorRuntimeClosureError as error:
                raise ReleaseError(str(error)) from error
            payload.extend(
                ("source_delete", relative, None)
                for relative in operator_stale_sources
            )
        if "aureon-cloud-ui.service" in services:
            if not UI_GATEWAY_REQUIRED_SOURCES.issubset(seen):
                raise ReleaseError("complete_ui_gateway_runtime_sources_required")
            validate_frontend_build_manifest(
                manifest.get("frontend_dist"), rows, manifest["source_git_tree"]
            )
        broker_manifest = None
        original_identity = None
        if TOKEN_BROKER_UNIT in services:
            if not TOKEN_BROKER_REQUIRED_SOURCES.issubset(seen):
                raise ReleaseError("complete_token_broker_sources_required")
            broker_manifest = validate_component_manifest(
                manifest.get("token_broker"), rows, TOKEN_BROKER_REQUIRED_SOURCES,
                schema="aureon.vm-token-broker-release.v1",
                source_git_tree=manifest["source_git_tree"],
            )
            original_identity = identity_snapshot()
        public_bridge_manifest = None
        public_bridge_identity = None
        public_bridge_environment = None
        if PUBLIC_BRIDGE_UNIT in services:
            if (
                re.fullmatch(r"[0-9a-f]{64}", iap_admin_email_sha256 or "")
                is None
            ):
                raise ReleaseError("iap_admin_email_commitment_invalid")
            if not PUBLIC_BRIDGE_REQUIRED_SOURCES.issubset(seen):
                raise ReleaseError("complete_public_bridge_sources_required")
            public_bridge_manifest = validate_component_manifest(
                manifest.get("public_bridge"), rows, PUBLIC_BRIDGE_REQUIRED_SOURCES,
                schema="aureon.vm-public-bridge-release.v1",
                source_git_tree=manifest["source_git_tree"],
            )
            indexed = _manifest_row_index(rows)
            certificate = public_bridge_manifest.get("certificate")
            if (
                public_bridge_manifest.get("revision") != revision
                or public_bridge_manifest.get("source_sha256") != indexed[PUBLIC_BRIDGE_SOURCE]["sha256"]
                or public_bridge_manifest.get("unit_sha256") != indexed[PUBLIC_BRIDGE_UNIT_SOURCE]["sha256"]
            ):
                raise ReleaseError("public_bridge_manifest_binding_invalid")
            certificate_evidence = (
                public_bridge_certificate_evidence_from_manifest(certificate)
            )
            public_bridge_identity = bridge_identity(certificate["sha256"], None)
            require_bridge_identity_matches_certificate(
                public_bridge_identity, certificate_evidence
            )
            existing_environment = read_bytes(PUBLIC_BRIDGE_ENV, 64 * 1024)
            if (
                public_bridge_identity.get("environment_sha256")
                != digest(existing_environment)
            ):
                raise ReleaseError("public_bridge_environment_changed_during_prepare")
            public_bridge_environment = _public_bridge_environment_for_release(
                existing_environment, revision, iap_admin_email_sha256
            )
        snapshots = {unit: controller.snapshot(unit) for unit in services}
        if any(organ_name(unit) in RETAIN_ONLY and not row["active"] for unit, row in snapshots.items()):
            raise ReleaseError("legacy_expansion_may_only_be_retained")
        indexed_payload = {relative: data for kind, relative, data in payload if kind == "source"}
        for unit in services:
            if unit == TOKEN_BROKER_UNIT:
                unit_data = indexed_payload[TOKEN_BROKER_UNIT_SOURCE]
            elif unit == PUBLIC_BRIDGE_UNIT:
                unit_data = indexed_payload[PUBLIC_BRIDGE_UNIT_SOURCE]
            else:
                unit_data = render_unit(
                    unit, workspace, revision, project, secret, version,
                    tenant_secret, tenant_version, provider_secret, provider_version,
                    owner_subject, owner_email_sha256,
                )
            payload.append(("unit", unit, unit_data))
        if PUBLIC_BRIDGE_UNIT in services:
            payload.append(
                ("public_bridge_source", "public_entry.py", indexed_payload[PUBLIC_BRIDGE_SOURCE])
            )
            payload.append(
                ("public_bridge_environment", "bridge.env", public_bridge_environment)
            )
        release = confined(releases, release_id)
        release.mkdir(mode=0o700)  # collision is a hard error; never overwrite a prior release
        journal = {"schema": SCHEMA, "revision": revision, "release_id": release_id, "phase": "prepared",
                   "workspace": str(workspace.resolve()), "units": str(units.resolve()), "services": services,
                   "source_git_tree": manifest["source_git_tree"],
                   "original_services": snapshots, "manifest_sha256": digest(read_bytes(bundle / "manifest.json", 4 * 1024 * 1024)),
                   "entries": [], "deployment_hold": True, "release_authority": False,
                   "runtime_state_restored": False, "data_source_freshness": "not_attested",
                   "tenant_auth_secret": tenant_secret or None,
                   "tenant_auth_secret_version": tenant_version or None,
                   "owner_provider_secret": provider_secret or None,
                   "owner_provider_secret_version": provider_version or None,
                   "supabase_owner_subject": owner_subject or None,
                   "supabase_owner_email_sha256": owner_email_sha256 or None,
                    "operator_runtime_sources": sorted(operator_runtime_sources),
                    "runtime_sources": sorted(runtime_sources),
                   "operator_stale_sources": list(operator_stale_sources),
                   "operator_python_caches_at_prepare": list(operator_python_caches),
                    "operator_source_directories": operator_source_directories,
                    "token_broker": broker_manifest,
                    "original_attached_identity": original_identity,
                    "attached_identity_after": None,
                    "authority_receipt": None,
                    "external_identity_rollback_required": False,
                     "public_bridge": public_bridge_manifest,
                     "public_bridge_identity": public_bridge_identity,
                     "iap_admin_email_sha256": (
                         iap_admin_email_sha256
                         if public_bridge_manifest is not None
                         else None
                     ),
                    "public_bridge_root": str(PUBLIC_BRIDGE_INSTALL_ROOT),
                    "service_order": services,
                    "vm_release_receipt": None}
        for index, (kind, relative, data) in enumerate(payload):
            if kind in {"source", "source_delete"}:
                root = workspace
            elif kind == "public_bridge_source":
                root = PUBLIC_BRIDGE_INSTALL_ROOT
            elif kind == "public_bridge_environment":
                root = PUBLIC_BRIDGE_ENV.parent
            else:
                root = units
            target = confined(root, relative)
            before = read_bytes(target) if target.exists() else None
            if (
                kind == "public_bridge_environment"
                and public_bridge_identity.get("environment_sha256")
                != digest(before or b"")
            ):
                raise ReleaseError("public_bridge_environment_changed_during_prepare")
            if kind == "source_delete" and before is None:
                raise ReleaseError("stale_operator_source_changed_during_prepare")
            mode = stat.S_IMODE(target.stat().st_mode) if before is not None else 0o644
            owner = ([target.stat().st_uid, target.stat().st_gid]
                     if before is not None else None)
            after_mode = (
                mode & ~0o222
                if kind in {"source", "public_bridge_source"} and os.name == "posix"
                else 0o644 if kind == "unit" and os.name == "posix" else mode
            )
            after_owner = (
                [0, 0]
                if kind in {"source", "public_bridge_source", "unit"} and os.name == "posix"
                else owner
            )
            entry = {"kind": kind, "path": relative,
                     "after_sha256": digest(data) if data is not None else None,
                     "after_mode": after_mode, "after_owner": after_owner, "mode": mode,
                     "before_sha256": digest(before) if before is not None else None, "slot": str(index),
                     "owner": owner,
                     "bootstrap": (
                         kind == "unit" and relative == TOKEN_BROKER_UNIT
                         or kind == "source" and relative in {TOKEN_BROKER_SOURCE, WORKLOAD_IDENTITY_SOURCE}
                     )}
            if data is not None:
                durable_write(release / "staged" / str(index), data)
            if before is not None:
                durable_write(release / "backup" / str(index), before)
            journal["entries"].append(entry)
        save_journal(release, journal)
        return release


def journal_target(journal: dict, entry: dict) -> Path:
    if entry["kind"] in {"source", "source_delete"}:
        source_path(entry["path"])
        return confined(Path(journal["workspace"]), entry["path"])
    if entry["kind"] == "unit" and entry["path"] in journal["services"]:
        return confined(Path(journal["units"]), entry["path"])
    if entry["kind"] == "public_bridge_source" and entry["path"] == "public_entry.py":
        return confined(Path(journal["public_bridge_root"]), entry["path"])
    if entry["kind"] == "public_bridge_environment" and entry["path"] == "bridge.env":
        return PUBLIC_BRIDGE_ENV
    raise ReleaseError("journal_entry_invalid")


def current_hash(path: Path) -> str | None:
    return digest(read_bytes(path)) if path.exists() else None


def _verify_transaction_files(release: Path, journal: dict, *, state: str) -> None:
    for entry in journal["entries"]:
        expected = entry["after_sha256"] if state == "after" and entry.get("bootstrap") else entry["before_sha256"]
        if current_hash(journal_target(journal, entry)) != expected:
            raise ReleaseError("source_changed_after_prepare")
        if (
            entry["after_sha256"] is not None
            and digest(read_bytes(release / "staged" / entry["slot"])) != entry["after_sha256"]
        ):
            raise ReleaseError("staged_source_hash_mismatch")


def _install_entry(release: Path, journal: dict, entry: dict) -> None:
    target = journal_target(journal, entry)
    if current_hash(target) not in {entry["before_sha256"], entry["after_sha256"]}:
        raise ReleaseError("source_changed_during_install")
    if entry["after_sha256"] is None:
        if target.exists():
            durable_unlink(target)
    elif current_hash(target) != entry["after_sha256"]:
        durable_write(
            target,
            read_bytes(release / "staged" / entry["slot"]),
            entry.get("after_mode", entry["mode"]),
            entry.get("after_owner"),
        )


def _stable_service_state(snapshot: object) -> dict:
    """Project a systemd snapshot onto fields that survive a host reboot."""
    if not isinstance(snapshot, dict):
        raise ReleaseError("service_snapshot_invalid")
    exists = snapshot.get("exists")
    active = snapshot.get("active")
    enabled = snapshot.get("enabled")
    main_pid = snapshot.get("main_pid")
    if (
        type(exists) is not bool
        or type(active) is not bool
        or type(enabled) is not bool
        or type(main_pid) is not int
        or main_pid < 0
        or active and main_pid <= 0
        or not active and main_pid != 0
        or not exists and (active or enabled or main_pid != 0)
    ):
        raise ReleaseError("service_snapshot_invalid")
    user = snapshot.get("user") if exists else None
    if exists and (not isinstance(user, str) or not user):
        raise ReleaseError("service_snapshot_invalid")
    return {
        "exists": exists,
        "active": active,
        "enabled": enabled,
        "main_pid": main_pid,
        "user": user,
    }


def _quiescence_expected_services(journal: dict) -> dict[str, dict]:
    services = journal.get("services")
    if (
        not isinstance(services, list)
        or journal.get("service_order") != services
        or TOKEN_BROKER_UNIT not in services
    ):
        raise ReleaseError("cutover_quiescence_journal_invalid")
    original = journal.get("original_services")
    broker = journal.get("broker_bootstrap_service")
    if not isinstance(original, dict) or not isinstance(broker, dict):
        raise ReleaseError("cutover_quiescence_journal_invalid")
    expected: dict[str, dict] = {}
    for unit in services:
        baseline = broker if unit == TOKEN_BROKER_UNIT else original.get(unit)
        projected = _stable_service_state(baseline)
        expected[unit] = {
            "exists": projected["exists"],
            "active": False,
            "enabled": False,
            "main_pid": 0,
            "user": projected["user"],
        }
    return expected


def _validated_quiescence_record(journal: dict) -> tuple[dict, dict[str, dict]]:
    expected = _quiescence_expected_services(journal)
    record = journal.get("cutover_quiescence")
    original_sha256 = digest(
        json.dumps(
            journal["original_services"], sort_keys=True, separators=(",", ":")
        ).encode("ascii")
    )
    broker_sha256 = digest(
        json.dumps(
            journal["broker_bootstrap_service"],
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
    )
    record_keys = {
        "schema",
        "service_order",
        "expected_services",
        "original_services_sha256",
        "broker_bootstrap_service_sha256",
        "started_at",
        "completed_at",
        "provider_readback",
    }
    started_at = record.get("started_at") if isinstance(record, dict) else None
    if (
        not isinstance(record, dict)
        or set(record) != record_keys
        or record.get("schema") != CUTOVER_QUIESCENCE_SCHEMA
        or record.get("service_order") != journal["services"]
        or record.get("expected_services") != expected
        or record.get("original_services_sha256") != original_sha256
        or record.get("broker_bootstrap_service_sha256") != broker_sha256
        or type(started_at) not in {int, float}
        or not math.isfinite(started_at)
        or started_at <= 0
    ):
        raise ReleaseError("cutover_quiescence_journal_invalid")
    phase = journal.get("phase")
    completed_at = record.get("completed_at")
    if phase == "quiescing":
        if completed_at is not None or record.get("provider_readback") is not None:
            raise ReleaseError("cutover_quiescence_journal_invalid")
    elif phase == "quiesced":
        if (
            type(completed_at) not in {int, float}
            or not math.isfinite(completed_at)
            or completed_at < started_at
            or record.get("provider_readback") != expected
        ):
            raise ReleaseError("cutover_quiescence_journal_invalid")
    else:
        raise ReleaseError("cutover_quiescence_journal_invalid")
    return record, expected


def _quiescence_state_reachable(
    current: dict, baseline: dict, expected: dict
) -> bool:
    disabled = dict(baseline)
    disabled["enabled"] = False
    return current in (baseline, disabled, expected)


def bootstrap_broker(release: Path, controller) -> dict:
    """Install the hash-bound broker without starting or stopping workloads."""
    with update_lock(release.parent):
        journal = json.loads(read_bytes(release / "journal.json", 16 * 1024 * 1024))
        if journal.get("phase") != "prepared" or TOKEN_BROKER_UNIT not in journal.get("services", []):
            raise ReleaseError("prepared_token_broker_release_required")
        _verify_transaction_files(release, journal, state="before")
        if any(
            controller.snapshot(unit) != journal["original_services"][unit]
            for unit in journal["services"]
        ):
            raise ReleaseError("service_inventory_changed_after_prepare")
        journal["phase"] = "broker_bootstrapping"
        save_journal(release, journal)
        try:
            original = journal["original_services"][TOKEN_BROKER_UNIT]
            if original["exists"]:
                controller.enabled(TOKEN_BROKER_UNIT, False)
                if controller.snapshot(TOKEN_BROKER_UNIT)["active"]:
                    controller.stop(TOKEN_BROKER_UNIT)
            apply_operator_source_directory_plan(
                Path(journal["workspace"]), journal.get("operator_source_directories", [])
            )
            for entry in journal["entries"]:
                if entry.get("bootstrap"):
                    _install_entry(release, journal, entry)
            controller.reload()
            broker = controller.snapshot(TOKEN_BROKER_UNIT)
            if not broker["exists"] or broker["active"]:
                raise ReleaseError("token_broker_bootstrap_readback_invalid")
            journal["broker_bootstrap_service"] = broker
            journal["phase"] = "broker_installed"
            journal["broker_installed_at"] = time.time()
            journal["external_identity_cutover_required"] = (
                not _is_broker_identity(journal.get("original_attached_identity"))
            )
            save_journal(release, journal)
            return journal
        except Exception:
            rolled = _rollback(release, journal, controller)
            if rolled.get("phase") == "rollback_external_identity_required":
                raise ReleaseError("broker_bootstrap_failed_external_identity_rollback_required") from None
            raise ReleaseError("broker_bootstrap_failed_source_rolled_back") from None


def quiesce_for_identity_cutover(release: Path, controller) -> dict:
    """Durably stop and disable the complete release inventory before VM identity changes."""
    with update_lock(release.parent):
        journal = json.loads(read_bytes(release / "journal.json", 16 * 1024 * 1024))
        phase = journal.get("phase")
        if phase not in {"broker_installed", "quiescing", "quiesced"}:
            raise ReleaseError("broker_installed_release_required_for_quiescence")
        _verify_transaction_files(release, journal, state="after")
        workspace = Path(journal["workspace"])
        if any(
            not _directory_matches(workspace, row, "after")
            for row in journal.get("operator_source_directories", [])
        ):
            raise ReleaseError("source_parent_changed_after_prepare")
        stale, _caches = operator_workspace_inventory(journal)
        if list(stale) != journal.get("operator_stale_sources", []):
            raise ReleaseError("operator_stale_source_inventory_changed")

        expected = _quiescence_expected_services(journal)
        baselines = {
            unit: _stable_service_state(
                journal["broker_bootstrap_service"]
                if unit == TOKEN_BROKER_UNIT
                else journal["original_services"][unit]
            )
            for unit in journal["services"]
        }
        if phase == "broker_installed":
            if any(
                controller.snapshot(unit)
                != (
                    journal["broker_bootstrap_service"]
                    if unit == TOKEN_BROKER_UNIT
                    else journal["original_services"][unit]
                )
                for unit in journal["services"]
            ):
                raise ReleaseError("service_inventory_changed_after_broker_bootstrap")
            journal["cutover_quiescence"] = {
                "schema": CUTOVER_QUIESCENCE_SCHEMA,
                "service_order": list(journal["services"]),
                "expected_services": expected,
                "original_services_sha256": digest(
                    json.dumps(
                        journal["original_services"],
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("ascii")
                ),
                "broker_bootstrap_service_sha256": digest(
                    json.dumps(
                        journal["broker_bootstrap_service"],
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("ascii")
                ),
                "started_at": time.time(),
                "completed_at": None,
                "provider_readback": None,
            }
            journal["phase"] = "quiescing"
            save_journal(release, journal)
        else:
            _validated_quiescence_record(journal)

        current = {
            unit: _stable_service_state(controller.snapshot(unit))
            for unit in journal["services"]
        }
        if phase == "quiesced":
            if current != expected:
                raise ReleaseError("service_inventory_changed_after_quiescence")
            return journal
        if any(
            not _quiescence_state_reachable(
                current[unit], baselines[unit], expected[unit]
            )
            for unit in journal["services"]
        ):
            raise ReleaseError("service_inventory_changed_during_quiescence")

        # Disable the complete release inventory before stopping any process so
        # an interruption or reboot cannot auto-start a legacy workload.
        for unit in journal["services"]:
            state = _stable_service_state(controller.snapshot(unit))
            if not _quiescence_state_reachable(
                state, baselines[unit], expected[unit]
            ):
                raise ReleaseError("service_inventory_changed_during_quiescence")
            if state["exists"] and state["enabled"]:
                controller.enabled(unit, False)
                state = _stable_service_state(controller.snapshot(unit))
            if state not in (
                {**baselines[unit], "enabled": False},
                expected[unit],
            ):
                raise ReleaseError("service_disable_readback_failed")
        for unit in reversed(journal["services"]):
            state = _stable_service_state(controller.snapshot(unit))
            if state["exists"] and state["active"]:
                controller.stop(unit)
                state = _stable_service_state(controller.snapshot(unit))
            if state != expected[unit]:
                raise ReleaseError("service_stop_readback_failed")

        readback = {
            unit: _stable_service_state(controller.snapshot(unit))
            for unit in journal["services"]
        }
        if readback != expected:
            raise ReleaseError("cutover_quiescence_readback_failed")
        journal["cutover_quiescence"]["provider_readback"] = readback
        journal["cutover_quiescence"]["completed_at"] = time.time()
        journal["phase"] = "quiesced"
        save_journal(release, journal)
        return journal


def validate_identity_rollback_receipt(
    path: Path,
    expected_sha256: str,
    journal: dict,
    *,
    now: float | None = None,
) -> dict:
    raw = read_bytes(path, 1024 * 1024)
    if re.fullmatch(r"[0-9a-f]{64}", expected_sha256 or "") is None or digest(raw) != expected_sha256:
        raise ReleaseError("identity_rollback_receipt_hash_mismatch")
    try:
        value = json.loads(raw)
    except (ValueError, TypeError, UnicodeError) as error:
        raise ReleaseError("identity_rollback_receipt_invalid") from error
    current = time.time() if now is None else float(now)
    recorded = _parse_receipt_time(value.get("recorded_at"), "identity_rollback_receipt_invalid")
    if recorded > current + 300 or current - recorded > 21_600:
        raise ReleaseError("identity_rollback_receipt_not_fresh")
    if (
        value.get("schema") != IDENTITY_ROLLBACK_RECEIPT_SCHEMA
        or value.get("release_id") != journal.get("release_id")
        or value.get("revision") != journal.get("revision")
        or value.get("attached_identity") != journal.get("original_attached_identity")
        or value.get("provider_readback_ok") is not True
        or value.get("iam_rollback_readback_ok") is not True
        or value.get("secret_values_read") is not False
    ):
        raise ReleaseError("identity_rollback_receipt_invalid")
    return {"sha256": expected_sha256, "recorded_at": value["recorded_at"]}


def _health_receipt(value: object, unit: str, revision: str) -> dict:
    if isinstance(value, dict):
        safe = {
            key: item
            for key, item in value.items()
            if key in {
                "schema", "revision", "role", "ready", "deployment_hold",
                "release_authority", "tenant_auth_ready", "tls", "http_status",
                "certificate_pinned", "response_sha256", "tokens_fresh",
            }
            and isinstance(item, (str, int, bool, type(None)))
        }
    else:
        safe = {}
    return {"unit": unit, "revision": revision, "passed": True, "readback": safe}


def boot_id_sha256() -> str:
    """Hash the kernel boot id so the receipt never exposes the host identifier."""
    if os.name != "posix":
        raise ReleaseError("linux_boot_id_readback_required")
    raw = read_bytes(Path("/proc/sys/kernel/random/boot_id"), 256).strip()
    if re.fullmatch(rb"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", raw) is None:
        raise ReleaseError("linux_boot_id_readback_invalid")
    return digest(raw)


def _deployed_entry(journal: dict, kind: str, path: str) -> dict:
    rows = [
        row
        for row in journal.get("entries", [])
        if row.get("kind") == kind and row.get("path") == path
    ]
    if len(rows) != 1 or rows[0].get("after_sha256") is None:
        raise ReleaseError("vm_release_receipt_source_inventory_invalid")
    return rows[0]


def require_bridge_environment_matches_release(identity: object, journal: dict) -> None:
    entry = _deployed_entry(
        journal, "public_bridge_environment", "bridge.env"
    )
    if (
        not isinstance(identity, dict)
        or identity.get("environment_revision") != journal.get("revision")
        or identity.get("environment_sha256") != entry["after_sha256"]
        or identity.get("iap_admin_email_sha256")
        != journal.get("iap_admin_email_sha256")
        or identity.get("plaintext_identity_environment_names") != []
    ):
        raise ReleaseError("public_bridge_environment_release_mismatch")


def _unit_executable_entry(journal: dict, unit: str) -> tuple[dict, Path]:
    if unit == TOKEN_BROKER_UNIT:
        source = TOKEN_BROKER_SOURCE
        entry = _deployed_entry(journal, "source", source)
        return entry, confined(Path(journal["workspace"]), source)
    if unit == PUBLIC_BRIDGE_UNIT:
        entry = _deployed_entry(journal, "public_bridge_source", "public_entry.py")
        return entry, confined(Path(journal["public_bridge_root"]), "public_entry.py")
    if unit == "aureon-cloud-operator.service":
        source = "deployment/google-cloud/cloud_operator.py"
    elif unit == "aureon-cloud-ui.service":
        source = "deployment/google-cloud/cloud_ui_gateway.py"
    elif unit in COLLECTOR_UNITS:
        source = "deployment/google-cloud/cloud_trade_receipt_collector.py"
    elif organ_name(unit) is not None:
        source = "deployment/google-cloud/cloud_read_organ.py"
    else:  # pragma: no cover - service allowlisting makes this unreachable.
        raise ReleaseError("vm_release_receipt_service_inventory_invalid")
    entry = _deployed_entry(journal, "source", source)
    return entry, confined(Path(journal["workspace"]), source)


def _loopback_health_receipts(
    rows: list[dict], services: list[str], revision: str
) -> dict[str, dict]:
    indexed = {
        row.get("unit"): row.get("readback")
        for row in rows
        if isinstance(row, dict)
    }
    result: dict[str, dict] = {}
    for unit, role in HTTP_UNITS.items():
        if unit not in services:
            continue
        value = indexed.get(unit)
        if (
            not isinstance(value, dict)
            or value.get("schema") != "aureon.cloud-http-health.v1"
            or value.get("revision") != revision
            or value.get("role") != role
            or value.get("ready") is not True
            or value.get("deployment_hold") is not True
            or value.get("release_authority") is not False
            or value.get("tenant_auth_ready") is not True
            or re.fullmatch(r"[0-9a-f]{64}", str(value.get("response_sha256") or "")) is None
        ):
            raise ReleaseError("vm_release_receipt_loopback_health_invalid")
        result[role] = {"unit": unit, **value}
    return result


def write_vm_release_receipt(
    release: Path,
    journal: dict,
    controller,
    *,
    health_rows: list[dict],
    token_rows: list[dict],
    restart_rows: list[dict],
    started_at: dict[str, str],
    start_order: list[str],
    restart_order: list[str],
    boot_id_before_sha256: str,
    boot_id_after_sha256: str,
) -> dict:
    attached = journal.get("attached_identity_after")
    if TOKEN_BROKER_UNIT in journal["services"]:
        require_broker_identity(attached)
        token_rows = validate_broker_token_receipts(token_rows)
    elif token_rows:
        raise ReleaseError("vm_release_receipt_unexpected_broker_tokens")
    if (
        not isinstance(attached, dict)
        or not all(isinstance(attached.get(key), str) for key in ("project", "zone", "instance", "email"))
        or not isinstance(attached.get("scopes"), list)
    ):
        raise ReleaseError("vm_release_receipt_attached_identity_invalid")
    if (
        re.fullmatch(r"[0-9a-f]{64}", boot_id_before_sha256 or "") is None
        or boot_id_before_sha256 != boot_id_after_sha256
    ):
        raise ReleaseError("controlled_restart_boot_continuity_invalid")
    units = []
    for unit in journal["services"]:
        state = controller.snapshot(unit)
        unit_entry = _deployed_entry(journal, "unit", unit)
        unit_path = confined(Path(journal["units"]), unit)
        executable_entry, executable_path = _unit_executable_entry(journal, unit)
        # The updater records this immediately after the controlled restart.
        # systemd's human-formatted ActiveEnterTimestamp is locale-dependent.
        effective_started_at = started_at.get(unit)
        effective_result = state.get("result") or (
            "success" if state.get("active") is True else "not_running"
        )
        effective_exec_status = state.get("exec_main_status", 0)
        if (
            state.get("active") is not True
            or state.get("enabled") is not True
            or (state.get("user") or service_identity(unit)) != service_identity(unit)
            or effective_result != "success"
            or effective_exec_status != 0
            or not isinstance(effective_started_at, str)
            or not effective_started_at
            or current_hash(unit_path) != unit_entry["after_sha256"]
            or current_hash(executable_path) != executable_entry["after_sha256"]
        ):
            raise ReleaseError("vm_release_receipt_service_inventory_invalid")
        units.append(
            {
                "unit": unit,
                "user": service_identity(unit),
                "active": True,
                "enabled": True,
                "result": effective_result,
                "exec_main_status": effective_exec_status,
                "fragment_path": str(unit_path),
                "fragment_sha256": unit_entry["after_sha256"],
                "executable_path": str(executable_path),
                "executable_sha256": executable_entry["after_sha256"],
                "started_at": effective_started_at,
            }
        )
    source_rows = [
        {"kind": row["kind"], "path": row["path"], "sha256": row["after_sha256"]}
        for row in journal["entries"]
        if row["kind"] in {"source", "public_bridge_source"}
        and row["after_sha256"] is not None
    ]
    source_tree_sha256 = digest(
        json.dumps(source_rows, sort_keys=True, separators=(",", ":")).encode("ascii")
    )
    bridge = journal.get("public_bridge")
    bridge_source_sha256 = bridge.get("source_sha256") if isinstance(bridge, dict) else None
    bridge_certificate_sha256 = (
        bridge.get("certificate", {}).get("sha256") if isinstance(bridge, dict) else None
    )
    bridge_certificate_evidence = (
        public_bridge_certificate_evidence_from_manifest(
            bridge.get("certificate")
        )
        if isinstance(bridge, dict)
        else None
    )
    if isinstance(bridge, dict) and (
        re.fullmatch(r"[0-9a-f]{64}", str(bridge_source_sha256 or "")) is None
        or re.fullmatch(r"[0-9a-f]{64}", str(bridge_certificate_sha256 or "")) is None
        or journal.get("public_bridge_identity", {}).get("private_key_preserved") is not True
    ):
        raise ReleaseError("vm_release_receipt_public_bridge_invalid")
    if isinstance(bridge, dict):
        require_bridge_identity_matches_certificate(
            journal.get("public_bridge_identity"),
            bridge_certificate_evidence,
        )
        require_bridge_environment_matches_release(
            journal.get("public_bridge_identity"), journal
        )
    _loopback_health_receipts(
        health_rows, journal["services"], journal["revision"]
    )
    restart_loopback = _loopback_health_receipts(
        restart_rows, journal["services"], journal["revision"]
    )
    authority = journal.get("authority_receipt") or {}
    if (
        TOKEN_BROKER_UNIT in journal["services"]
        and re.fullmatch(r"[0-9a-f]{64}", str(authority.get("contract_sha256") or "")) is None
    ):
        raise ReleaseError("vm_release_receipt_authority_binding_invalid")
    receipt = {
        "schema": VM_RELEASE_RECEIPT_SCHEMA,
        "project": attached["project"],
        "zone": attached["zone"],
        "instance": attached["instance"],
        "status": "passed",
        "attached_service_account": attached["email"],
        "attached_scopes": attached["scopes"],
        "contract_sha256": authority.get("contract_sha256"),
        "source_revision": journal["revision"],
        "recorded_at": datetime.now(UTC).isoformat(),
        "bundle_manifest_sha256": journal["manifest_sha256"],
        "source_tree_sha256": source_tree_sha256,
        "public_bridge_source_sha256": bridge_source_sha256,
        "public_bridge_certificate_sha256": bridge_certificate_sha256,
        "public_bridge_certificate": bridge_certificate_evidence,
        "units": units,
        "broker_tokens": token_rows,
        "loopback_health": restart_loopback,
        "restart_continuity": {
            "controlled_restart": "passed",
            "boot_id_before_sha256": boot_id_before_sha256,
            "boot_id_after_sha256": boot_id_after_sha256,
            "boot_id_unchanged": True,
            "broker_before_workloads": journal.get("broker_started_before_workloads") is True,
            "start_order": start_order,
            "restart_order": restart_order,
            "readback": restart_rows,
            "reboot_validation": "pending_separate_cutover_evidence",
        },
        "deployment_hold": True,
        "release_authority": False,
        "secret_values_recorded": False,
    }
    raw = (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode("ascii")
    durable_write(release / "vm-release-receipt.json", raw, 0o600)
    return {
        "schema": receipt["schema"],
        "path": str((release / "vm-release-receipt.json").resolve()),
        "sha256": digest(raw),
        "recorded_at": receipt["recorded_at"],
    }


def validate_vm_release_receipt(release: Path, journal: dict) -> dict:
    raw = read_bytes(release / "vm-release-receipt.json", 16 * 1024 * 1024)
    expected = journal.get("vm_release_receipt")
    if (
        not isinstance(expected, dict)
        or expected.get("schema") != VM_RELEASE_RECEIPT_SCHEMA
        or expected.get("sha256") != digest(raw)
    ):
        raise ReleaseError("vm_release_receipt_invalid")
    try:
        value = json.loads(raw)
    except (ValueError, TypeError, UnicodeError) as error:
        raise ReleaseError("vm_release_receipt_invalid") from error
    bridge = journal.get("public_bridge")
    continuity = value.get("restart_continuity")
    units = value.get("units")
    token_rows = value.get("broker_tokens")
    expected_loopback_roles = {
        role for unit, role in HTTP_UNITS.items() if unit in journal["services"]
    }
    if (
        value.get("schema") != VM_RELEASE_RECEIPT_SCHEMA
        or value.get("status") != "passed"
        or value.get("source_revision") != journal["revision"]
        or value.get("bundle_manifest_sha256") != journal["manifest_sha256"]
        or re.fullmatch(r"[0-9a-f]{64}", str(value.get("source_tree_sha256") or "")) is None
        or value.get("public_bridge_source_sha256")
        != (bridge.get("source_sha256") if isinstance(bridge, dict) else None)
        or value.get("public_bridge_certificate_sha256")
        != (bridge.get("certificate", {}).get("sha256") if isinstance(bridge, dict) else None)
        or value.get("public_bridge_certificate")
        != (
            public_bridge_certificate_evidence_from_manifest(
                bridge.get("certificate")
            )
            if isinstance(bridge, dict)
            else None
        )
        or not isinstance(units, list)
        or [row.get("unit") for row in units if isinstance(row, dict)] != journal["services"]
        or any(
            not isinstance(row, dict)
            or row.get("active") is not True
            or row.get("enabled") is not True
            or row.get("result") != "success"
            or row.get("exec_main_status") != 0
            or re.fullmatch(r"[0-9a-f]{64}", str(row.get("fragment_sha256") or "")) is None
            or re.fullmatch(r"[0-9a-f]{64}", str(row.get("executable_sha256") or "")) is None
            for row in units
        )
        or not isinstance(continuity, dict)
        or continuity.get("controlled_restart") != "passed"
        or continuity.get("boot_id_unchanged") is not True
        or continuity.get("boot_id_before_sha256") != continuity.get("boot_id_after_sha256")
        or re.fullmatch(r"[0-9a-f]{64}", str(continuity.get("boot_id_before_sha256") or "")) is None
        or continuity.get("start_order") != journal["services"]
        or continuity.get("restart_order") != journal["services"]
        or set((value.get("loopback_health") or {}).keys()) != expected_loopback_roles
        or value.get("deployment_hold") is not True
        or value.get("release_authority") is not False
        or value.get("secret_values_recorded") is not False
    ):
        raise ReleaseError("vm_release_receipt_invalid")
    if TOKEN_BROKER_UNIT in journal["services"]:
        require_broker_identity(
            {
                "project": value.get("project"),
                "zone": value.get("zone"),
                "instance": value.get("instance"),
                "email": value.get("attached_service_account"),
                "scopes": value.get("attached_scopes"),
            }
        )
        validate_broker_token_receipts(token_rows, require_current=False)
        if (
            continuity.get("broker_before_workloads") is not True
            or re.fullmatch(r"[0-9a-f]{64}", str(value.get("contract_sha256") or "")) is None
        ):
            raise ReleaseError("vm_release_receipt_invalid")
    elif token_rows != []:
        raise ReleaseError("vm_release_receipt_invalid")
    forbidden = {"access_token", "private_key", "secret_value", "token_value"}

    def contains_forbidden(item: object) -> bool:
        if isinstance(item, dict):
            return bool(forbidden.intersection(item)) or any(
                contains_forbidden(child) for child in item.values()
            )
        if isinstance(item, list):
            return any(contains_forbidden(child) for child in item)
        return False

    if contains_forbidden(value):
        raise ReleaseError("vm_release_receipt_contains_sensitive_value")
    return value


def record_vm_reboot_continuity(
    release: Path,
    controller,
    *,
    identity_snapshot=metadata_identity_snapshot,
    broker_health=wait_for_broker_tokens,
    health=verify_http,
    bridge_identity=inspect_public_bridge_identity,
    bridge_health=verify_public_bridge_liveness,
    boot_id=boot_id_sha256,
) -> dict:
    """Record read-only evidence after an externally controlled VM reboot."""
    with update_lock(release.parent):
        journal = check(release)
        if journal.get("phase") != "committed":
            raise ReleaseError("committed_vm_release_required_for_reboot_readback")
        required_services = {
            TOKEN_BROKER_UNIT,
            "aureon-cloud-operator.service",
            "aureon-cloud-ui.service",
            PUBLIC_BRIDGE_UNIT,
        }
        if not required_services.issubset(journal.get("services", [])):
            raise ReleaseError("complete_vm_cutover_services_required_for_reboot_readback")
        release_receipt = validate_vm_release_receipt(release, journal)
        attached = identity_snapshot()
        require_broker_identity(attached)
        if any(
            attached.get(key) != release_receipt.get(receipt_key)
            for key, receipt_key in (
                ("project", "project"),
                ("zone", "zone"),
                ("instance", "instance"),
                ("email", "attached_service_account"),
                ("scopes", "attached_scopes"),
            )
        ):
            raise ReleaseError("reboot_attached_identity_changed")
        before_boot = release_receipt["restart_continuity"][
            "boot_id_after_sha256"
        ]
        after_boot = boot_id()
        if (
            re.fullmatch(r"[0-9a-f]{64}", str(after_boot or "")) is None
            or after_boot == before_boot
        ):
            raise ReleaseError("vm_reboot_not_observed")
        observed_at = datetime.now(UTC).isoformat()
        units: list[dict] = []
        for unit in journal["services"]:
            state = controller.snapshot(unit)
            unit_entry = _deployed_entry(journal, "unit", unit)
            executable_entry, executable_path = _unit_executable_entry(journal, unit)
            unit_path = confined(Path(journal["units"]), unit)
            result = state.get("result") or (
                "success" if state.get("active") is True else "not_running"
            )
            exec_status = state.get("exec_main_status", 0)
            if (
                state.get("active") is not True
                or state.get("enabled") is not True
                or (state.get("user") or service_identity(unit)) != service_identity(unit)
                or result != "success"
                or exec_status != 0
                or current_hash(unit_path) != unit_entry["after_sha256"]
                or current_hash(executable_path) != executable_entry["after_sha256"]
            ):
                raise ReleaseError("vm_reboot_service_continuity_invalid")
            units.append(
                {
                    "unit": unit,
                    "user": service_identity(unit),
                    "active": True,
                    "enabled": True,
                    "result": result,
                    "exec_main_status": exec_status,
                    "fragment_sha256": unit_entry["after_sha256"],
                    "executable_sha256": executable_entry["after_sha256"],
                    "observed_at": observed_at,
                }
            )
        token_rows = validate_broker_token_receipts(broker_health())
        loopback_rows = [
            _health_receipt(health(unit, journal["revision"]), unit, journal["revision"])
            for unit in ("aureon-cloud-operator.service", "aureon-cloud-ui.service")
        ]
        loopback = _loopback_health_receipts(
            loopback_rows, journal["services"], journal["revision"]
        )
        bridge = journal["public_bridge"]
        certificate = bridge["certificate"]
        certificate_evidence = public_bridge_certificate_evidence_from_manifest(
            certificate
        )
        bridge_readback = bridge_identity(
            certificate["sha256"], journal["revision"]
        )
        require_bridge_identity_matches_certificate(
            bridge_readback, certificate_evidence
        )
        require_bridge_environment_matches_release(bridge_readback, journal)
        public_health = _health_receipt(
            bridge_health(PUBLIC_BRIDGE_UNIT, journal["revision"]),
            PUBLIC_BRIDGE_UNIT,
            journal["revision"],
        )
        if (
            public_health["readback"].get("tls") is not True
            or public_health["readback"].get("certificate_pinned") is not True
            or re.fullmatch(
                r"[0-9a-f]{64}",
                str(public_health["readback"].get("response_sha256") or ""),
            )
            is None
        ):
            raise ReleaseError("vm_reboot_public_bridge_health_invalid")
        loopback["public-bridge"] = public_health
        receipt = {
            "schema": VM_REBOOT_CONTINUITY_SCHEMA,
            "status": "passed",
            "recorded_at": observed_at,
            "vm_release_receipt_sha256": journal["vm_release_receipt"]["sha256"],
            "contract_sha256": release_receipt["contract_sha256"],
            "source_revision": release_receipt["source_revision"],
            "bundle_manifest_sha256": release_receipt["bundle_manifest_sha256"],
            "source_tree_sha256": release_receipt["source_tree_sha256"],
            "project": attached["project"],
            "zone": attached["zone"],
            "instance": attached["instance"],
            "attached_service_account": attached["email"],
            "attached_scopes": attached["scopes"],
            "boot_id_before_sha256": before_boot,
            "boot_id_after_sha256": after_boot,
            "boot_id_changed": True,
            "vm_status": "RUNNING",
            "units": units,
            "broker_tokens": token_rows,
            "loopback_health": loopback,
            "public_bridge_source_sha256": release_receipt[
                "public_bridge_source_sha256"
            ],
            "public_bridge_certificate_sha256": release_receipt[
                "public_bridge_certificate_sha256"
            ],
            "public_bridge_certificate": certificate_evidence,
            "deployment_hold": True,
            "release_authority": False,
            "secret_values_recorded": False,
        }
        raw = (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode("ascii")
        durable_write(release / "vm-reboot-continuity.json", raw, 0o600)
        journal["vm_reboot_continuity_receipt"] = {
            "schema": VM_REBOOT_CONTINUITY_SCHEMA,
            "path": str((release / "vm-reboot-continuity.json").resolve()),
            "sha256": digest(raw),
            "recorded_at": observed_at,
        }
        save_journal(release, journal)
        return journal["vm_reboot_continuity_receipt"]


def rollback(
    release: Path,
    controller,
    *,
    identity_snapshot=metadata_identity_snapshot,
    identity_rollback_receipt: Path | None = None,
    identity_rollback_receipt_sha256: str = "",
) -> dict:
    with update_lock(release.parent):
        journal = json.loads(read_bytes(release / "journal.json", 16 * 1024 * 1024))
        return _rollback(
            release,
            journal,
            controller,
            identity_snapshot=identity_snapshot,
            identity_rollback_receipt=identity_rollback_receipt,
            identity_rollback_receipt_sha256=identity_rollback_receipt_sha256,
        )


def _rollback(
    release: Path,
    journal: dict,
    controller,
    *,
    identity_snapshot=metadata_identity_snapshot,
    identity_rollback_receipt: Path | None = None,
    identity_rollback_receipt_sha256: str = "",
) -> dict:
    if journal["phase"] == "rolled_back":
        return journal
    # A prior committed release cannot overwrite a newer update's source.
    for entry in journal["entries"]:
        if current_hash(journal_target(journal, entry)) not in {entry["before_sha256"], entry["after_sha256"]}:
            raise ReleaseError("rollback_conflicts_with_external_or_newer_source")
        if entry["before_sha256"] is not None and digest(read_bytes(release / "backup" / entry["slot"])) != entry["before_sha256"]:
            raise ReleaseError("rollback_backup_hash_mismatch")
    workspace = Path(journal["workspace"])
    for row in journal.get("operator_source_directories", []):
        if not (
            _directory_matches(workspace, row, "before")
            or _directory_matches(workspace, row, "after")
        ):
            raise ReleaseError("rollback_conflicts_with_source_parent_metadata")
    journal["phase"] = "rolling_back"
    save_journal(release, journal)
    for unit in journal["services"]:
        if controller.snapshot(unit)["exists"]:
            controller.enabled(unit, False)
    for unit in reversed(journal["services"]):
        if controller.snapshot(unit)["exists"]:
            controller.stop(unit)
            if not journal["original_services"][unit]["exists"]:
                controller.enabled(unit, False)
    for entry in reversed(journal["entries"]):
        target = journal_target(journal, entry)
        if current_hash(target) == entry["before_sha256"]:
            continue
        if entry["before_sha256"] is None:
            target.unlink()  # only the exact newly-created, hash-matched managed file
        else:
            durable_write(target, read_bytes(release / "backup" / entry["slot"]), entry["mode"], entry.get("owner"))
    rollback_operator_source_directory_plan(
        workspace, journal.get("operator_source_directories", [])
    )
    controller.reload()
    original_identity = journal.get("original_attached_identity")
    if original_identity is not None:
        current_identity = identity_snapshot()
        identity_changed = current_identity != original_identity
        external_change = journal.get("attached_identity_after") not in (None, original_identity)
        if identity_changed or external_change and identity_rollback_receipt is None:
            journal["phase"] = "rollback_external_identity_required"
            journal["external_identity_rollback_required"] = True
            journal["external_identity_rollback"] = {
                "expected_attached_identity": original_identity,
                "current_attached_identity": current_identity,
                "provider_readback_required": True,
                "iam_rollback_readback_required": True,
                "services_remain_stopped": True,
            }
            save_journal(release, journal)
            return journal
        if external_change:
            receipt = validate_identity_rollback_receipt(
                identity_rollback_receipt,
                identity_rollback_receipt_sha256,
                journal,
            )
            if current_identity != original_identity:
                raise ReleaseError("identity_rollback_provider_readback_mismatch")
            journal["external_identity_rollback_receipt"] = receipt
    for unit in journal["services"]:
        original = journal["original_services"][unit]
        if original["exists"]:
            controller.enabled(unit, original["enabled"])
            if original["active"]:
                controller.start(unit)
    journal["phase"] = "rolled_back"
    journal["external_identity_rollback_required"] = False
    journal["rolled_back_at"] = time.time()
    save_journal(release, journal)
    return journal


def check(release: Path) -> dict:
    journal = json.loads(read_bytes(release / "journal.json", 16 * 1024 * 1024))
    phase = journal.get("phase")
    if phase not in {
        "prepared", "broker_installed", "quiesced", "committed", "rolled_back",
        "rollback_external_identity_required",
    }:
        raise ReleaseError("interrupted_transaction_requires_rollback")
    if "aureon-cloud-operator.service" in journal.get("services", []):
        require_owner_identity(
            journal.get("supabase_owner_subject"),
            journal.get("supabase_owner_email_sha256"),
        )
    workspace = Path(journal["workspace"])
    for entry in journal["entries"]:
        target = journal_target(journal, entry)
        expected_key = (
            "after_sha256"
            if phase == "committed"
            or phase in {"broker_installed", "quiesced"} and entry.get("bootstrap")
            else "before_sha256"
        )
        if current_hash(target) != entry[expected_key]:
            raise ReleaseError("release_readback_hash_mismatch")
        if (phase == "committed" and entry["kind"] in {"source", "public_bridge_source"}
                and not immutable_source_metadata(target)):
            raise ReleaseError("release_source_not_root_owned_immutable")
        if (phase == "committed" and entry["kind"] == "source"
                and not immutable_source_parent_metadata(target, workspace)):
            raise ReleaseError("release_source_parent_not_root_owned_immutable")
    directory_state = (
        "after" if phase in {"committed", "broker_installed", "quiesced"} else "before"
    )
    if any(
        not _directory_matches(workspace, row, directory_state)
        for row in journal.get("operator_source_directories", [])
    ):
        raise ReleaseError("release_source_parent_metadata_mismatch")
    stale, caches = operator_workspace_inventory(journal)
    if phase == "committed" and (stale or caches):
        raise ReleaseError("operator_runtime_workspace_not_exact")
    if phase in {"prepared", "rolled_back", "rollback_external_identity_required"} and list(stale) != journal.get(
        "operator_stale_sources", []
    ):
        raise ReleaseError("operator_stale_source_inventory_changed")
    if phase == "quiesced":
        _validated_quiescence_record(journal)
    if phase == "committed":
        vm_release = validate_vm_release_receipt(release, journal)
        reboot = journal.get("vm_reboot_continuity_receipt")
        if reboot is not None:
            raw = read_bytes(release / "vm-reboot-continuity.json", 16 * 1024 * 1024)
            try:
                value = json.loads(raw)
            except (ValueError, TypeError, UnicodeError) as error:
                raise ReleaseError("vm_reboot_continuity_receipt_invalid") from error
            if (
                not isinstance(reboot, dict)
                or reboot.get("schema") != VM_REBOOT_CONTINUITY_SCHEMA
                or reboot.get("sha256") != digest(raw)
                or value.get("schema") != VM_REBOOT_CONTINUITY_SCHEMA
                or value.get("status") != "passed"
                or value.get("vm_release_receipt_sha256")
                != journal["vm_release_receipt"]["sha256"]
                or value.get("source_revision") != journal["revision"]
                or value.get("public_bridge_certificate")
                != vm_release.get("public_bridge_certificate")
                or value.get("public_bridge_certificate_sha256")
                != vm_release.get("public_bridge_certificate_sha256")
                or value.get("boot_id_changed") is not True
                or value.get("boot_id_before_sha256") == value.get("boot_id_after_sha256")
                or value.get("secret_values_recorded") is not False
            ):
                raise ReleaseError("vm_reboot_continuity_receipt_invalid")
    return journal


def apply(
    release: Path,
    controller,
    health=verify_http,
    *,
    authority_receipt: Path | None = None,
    authority_receipt_sha256: str = "",
    identity_snapshot=metadata_identity_snapshot,
    broker_health=wait_for_broker_tokens,
    bridge_identity=inspect_public_bridge_identity,
    bridge_health=verify_public_bridge_liveness,
    boot_id=boot_id_sha256,
) -> dict:
    with update_lock(release.parent):
        journal = json.loads(read_bytes(release / "journal.json", 16 * 1024 * 1024))
        has_broker = TOKEN_BROKER_UNIT in journal.get("services", [])
        expected_phase = "quiesced" if has_broker else "prepared"
        if journal.get("phase") != expected_phase:
            if has_broker and journal.get("phase") == "prepared":
                reason = "broker_bootstrap_required_before_apply"
            elif has_broker and journal.get("phase") == "broker_installed":
                reason = "cutover_quiescence_required_before_apply"
            elif has_broker and journal.get("phase") == "quiescing":
                reason = "cutover_quiescence_incomplete"
            else:
                reason = "only_prepared_release_may_apply_use_rollback_for_interruption"
            raise ReleaseError(reason)
        stale, _caches = operator_workspace_inventory(journal)
        if list(stale) != journal.get("operator_stale_sources", []):
            raise ReleaseError("operator_stale_source_inventory_changed")
        _verify_transaction_files(
            release, journal, state="after" if has_broker else "before"
        )
        workspace = Path(journal["workspace"])
        directory_state = "after" if has_broker else "before"
        if any(
            not _directory_matches(workspace, row, directory_state)
            for row in journal.get("operator_source_directories", [])
        ):
            raise ReleaseError("source_parent_changed_after_prepare")
        if has_broker:
            _record, expected_services = _validated_quiescence_record(journal)
            if any(
                _stable_service_state(controller.snapshot(unit))
                != expected_services[unit]
                for unit in journal["services"]
            ):
                raise ReleaseError("service_inventory_changed_after_quiescence")
        elif any(
            controller.snapshot(unit) != journal["original_services"][unit]
            for unit in journal["services"]
        ):
            raise ReleaseError("service_inventory_changed_after_prepare")
        if PUBLIC_BRIDGE_UNIT in journal["services"]:
            certificate = journal["public_bridge"]["certificate"]
            certificate_evidence = (
                public_bridge_certificate_evidence_from_manifest(certificate)
            )
            prepared_identity = journal.get("public_bridge_identity")
            prepared_revision = (
                prepared_identity.get("environment_revision")
                if isinstance(prepared_identity, dict)
                else None
            )
            prepared_environment_sha256 = (
                prepared_identity.get("environment_sha256")
                if isinstance(prepared_identity, dict)
                else None
            )
            if (
                re.fullmatch(r"[0-9a-f]{40}", str(prepared_revision or ""))
                is None
                or re.fullmatch(
                    r"[0-9a-f]{64}", str(prepared_environment_sha256 or "")
                )
                is None
            ):
                raise ReleaseError("prepared_public_bridge_identity_invalid")
            observed = bridge_identity(certificate["sha256"], prepared_revision)
            require_bridge_identity_matches_certificate(
                observed, certificate_evidence
            )
            if (
                observed.get("environment_revision") != prepared_revision
                or observed.get("environment_sha256")
                != prepared_environment_sha256
            ):
                raise ReleaseError("public_bridge_environment_changed_after_prepare")
        if has_broker:
            if authority_receipt is None:
                raise ReleaseError("authority_prepare_receipt_required")
            authority = validate_authority_receipt(
                authority_receipt, authority_receipt_sha256, journal["revision"]
            )
            if PUBLIC_BRIDGE_UNIT in journal["services"] and not secrets.compare_digest(
                digest(
                    json.dumps(
                        authority["public_bridge_certificate"],
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("ascii")
                ),
                digest(
                    json.dumps(
                        certificate_evidence,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("ascii")
                ),
            ):
                raise ReleaseError("authority_bridge_certificate_binding_invalid")
            attached = identity_snapshot()
            require_broker_identity(attached)
            journal["authority_receipt"] = authority
            journal["attached_identity_after"] = attached
            journal["external_identity_rollback_required"] = (
                attached != journal.get("original_attached_identity")
            )
        journal["phase"] = "starting_broker" if has_broker else "stopping"
        save_journal(release, journal)
        try:
            token_rows: list[dict] = []
            health_rows: list[dict] = []
            started_at: dict[str, str] = {}
            start_order: list[str] = []
            boot_before = boot_id()
            if has_broker:
                controller.start(TOKEN_BROKER_UNIT)
                started_at[TOKEN_BROKER_UNIT] = datetime.now(UTC).isoformat()
                start_order.append(TOKEN_BROKER_UNIT)
                token_rows = validate_broker_token_receipts(broker_health())
                journal["broker_started_before_workloads"] = True
                journal["broker_token_readback"] = token_rows
                journal["phase"] = "stopping"
                save_journal(release, journal)
            # Persistently remove boot enablement before changing any dependent
            # source. The broker remains running so no workload is started with
            # missing identity material.
            for unit in journal["services"]:
                if unit != TOKEN_BROKER_UNIT and journal["original_services"][unit]["exists"]:
                    controller.enabled(unit, False)
            for unit in reversed(journal["services"]):
                if unit != TOKEN_BROKER_UNIT and controller.snapshot(unit)["exists"]:
                    controller.stop(unit)
            stale, _caches = operator_workspace_inventory(journal)
            if list(stale) != journal.get("operator_stale_sources", []):
                raise ReleaseError("operator_stale_source_inventory_changed")
            if journal.get("runtime_sources"):
                for relative in operator_python_cache_files(workspace):
                    durable_unlink(confined(workspace, relative))
                if operator_python_cache_files(workspace):
                    raise ReleaseError("operator_python_cache_purge_failed")
                if not has_broker:
                    apply_operator_source_directory_plan(
                        workspace, journal.get("operator_source_directories", [])
                    )
            journal["phase"] = "installing"
            save_journal(release, journal)
            for entry in journal["entries"]:
                if has_broker and entry.get("bootstrap"):
                    continue
                _install_entry(release, journal, entry)
            stale, caches = operator_workspace_inventory(journal)
            if stale or caches:
                raise ReleaseError("operator_runtime_workspace_not_exact")
            for entry in journal["entries"]:
                target = journal_target(journal, entry)
                if (
                    entry["kind"] in {"source", "public_bridge_source"}
                    and not immutable_source_metadata(target)
                ):
                    raise ReleaseError("release_source_not_root_owned_immutable")
                if (
                    entry["kind"] == "source"
                    and not immutable_source_parent_metadata(target, workspace)
                ):
                    raise ReleaseError("release_source_parent_not_root_owned_immutable")
            controller.reload()
            journal["phase"] = "verifying"
            save_journal(release, journal)
            for unit in journal["services"]:
                if unit == TOKEN_BROKER_UNIT:
                    continue
                controller.start(unit)
                started_at[unit] = datetime.now(UTC).isoformat()
                start_order.append(unit)
                if unit == PUBLIC_BRIDGE_UNIT:
                    certificate = journal["public_bridge"]["certificate"]
                    observed = bridge_identity(
                        certificate["sha256"], journal["revision"]
                    )
                    require_bridge_identity_matches_certificate(
                        observed, certificate_evidence
                    )
                    require_bridge_environment_matches_release(observed, journal)
                    journal["public_bridge_identity"] = observed
                    result = bridge_health(unit, journal["revision"])
                else:
                    result = health(unit, journal["revision"])
                health_rows.append(_health_receipt(result, unit, journal["revision"]))
            for unit in journal["services"]:
                controller.enabled(unit, True)
            restart_rows: list[dict] = []
            restart_order: list[str] = []
            for unit in journal["services"]:
                controller.restart(unit)
                started_at[unit] = datetime.now(UTC).isoformat()
                restart_order.append(unit)
                if unit == TOKEN_BROKER_UNIT:
                    token_rows = validate_broker_token_receipts(broker_health())
                    result = {"ready": True, "tokens_fresh": True}
                elif unit == PUBLIC_BRIDGE_UNIT:
                    certificate = journal["public_bridge"]["certificate"]
                    observed = bridge_identity(
                        certificate["sha256"], journal["revision"]
                    )
                    require_bridge_identity_matches_certificate(
                        observed, certificate_evidence
                    )
                    require_bridge_environment_matches_release(observed, journal)
                    journal["public_bridge_identity"] = observed
                    result = bridge_health(unit, journal["revision"])
                else:
                    result = health(unit, journal["revision"])
                restart_rows.append(_health_receipt(result, unit, journal["revision"]))
            if any(
                not controller.snapshot(unit).get("active")
                or not controller.snapshot(unit).get("enabled")
                for unit in journal["services"]
            ):
                raise ReleaseError("service_continuity_readback_failed")
            if journal.get("attached_identity_after") is None:
                journal["attached_identity_after"] = identity_snapshot()
            boot_after = boot_id()
            journal["vm_release_receipt"] = write_vm_release_receipt(
                release,
                journal,
                controller,
                health_rows=health_rows,
                token_rows=token_rows,
                restart_rows=restart_rows,
                started_at=started_at,
                start_order=start_order,
                restart_order=restart_order,
                boot_id_before_sha256=boot_before,
                boot_id_after_sha256=boot_after,
            )
            journal["phase"] = "committed"
            journal["committed_at"] = time.time()
            journal["verification_scope"] = (
                "exact_source_and_unit_hashes_identity_tokens_loopback_health_and_controlled_restart"
            )
            save_journal(release, journal)
            return journal
        except Exception:
            try:
                rolled = _rollback(
                    release, journal, controller, identity_snapshot=identity_snapshot
                )
            except Exception:
                journal["phase"] = "rollback_blocked"
                save_journal(release, journal)
                raise ReleaseError("update_failed_rollback_requires_operator_review") from None
            if rolled.get("phase") == "rollback_external_identity_required":
                raise ReleaseError("update_failed_external_identity_rollback_required") from None
            raise ReleaseError("update_failed_source_rolled_back") from None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=(
            "prepare",
            "bootstrap",
            "quiesce",
            "apply",
            "reboot-readback",
            "rollback",
            "check",
        ),
    )
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--workspace", type=Path, default=Path("/srv/aureon/runtime/workspace"))
    parser.add_argument("--releases", type=Path, default=Path("/srv/aureon/releases"))
    parser.add_argument("--units", type=Path, default=Path("/etc/systemd/system"))
    parser.add_argument("--release", type=Path)
    parser.add_argument("--service", action="append", default=[])
    parser.add_argument("--project", default="")
    parser.add_argument("--secret", default="")
    parser.add_argument("--secret-version", default="")
    parser.add_argument("--tenant-secret", default="")
    parser.add_argument("--tenant-secret-version", default="")
    parser.add_argument("--provider-secret", default="")
    parser.add_argument("--provider-secret-version", default="")
    parser.add_argument("--owner-subject", default="")
    parser.add_argument("--owner-email-sha256", default="")
    parser.add_argument("--iap-admin-email-sha256", default="")
    parser.add_argument("--authority-receipt", type=Path)
    parser.add_argument("--authority-receipt-sha256", default="")
    parser.add_argument("--identity-rollback-receipt", type=Path)
    parser.add_argument("--identity-rollback-receipt-sha256", default="")
    args = parser.parse_args()
    if args.command == "prepare":
        if args.bundle is None:
            raise ReleaseError("bundle_required")
        planned_services = normalise_service_plan(args.service)
        controller = Systemd(args.workspace, args.units, planned_services)
        release = prepare(args.bundle, args.workspace, args.releases, args.units, planned_services, controller,
                          project=args.project, secret=args.secret, version=args.secret_version,
                          tenant_secret=args.tenant_secret, tenant_version=args.tenant_secret_version,
                           provider_secret=args.provider_secret,
                           provider_version=args.provider_secret_version,
                           owner_subject=args.owner_subject,
                           owner_email_sha256=args.owner_email_sha256,
                           iap_admin_email_sha256=args.iap_admin_email_sha256)
        print(json.dumps({"prepared": True, "release": str(release), "requires_review_before_apply": True}))
        return 0
    if args.release is None:
        raise ReleaseError("release_required")
    journal = json.loads(read_bytes(args.release / "journal.json", 16 * 1024 * 1024))
    if args.command == "check":
        journal = check(args.release)
        print(json.dumps({key: journal.get(key) for key in ("revision", "phase", "services", "deployment_hold", "release_authority", "runtime_state_restored", "data_source_freshness")}))
        return 0
    controller = Systemd(Path(journal["workspace"]), Path(journal["units"]), journal["services"])
    if args.command == "bootstrap":
        result = bootstrap_broker(args.release, controller)
    elif args.command == "quiesce":
        result = quiesce_for_identity_cutover(args.release, controller)
    elif args.command == "apply":
        result = apply(
            args.release,
            controller,
            authority_receipt=args.authority_receipt,
            authority_receipt_sha256=args.authority_receipt_sha256,
        )
    elif args.command == "reboot-readback":
        result = record_vm_reboot_continuity(args.release, controller)
        print(json.dumps(result, sort_keys=True))
        return 0
    else:
        result = rollback(
            args.release,
            controller,
            identity_rollback_receipt=args.identity_rollback_receipt,
            identity_rollback_receipt_sha256=args.identity_rollback_receipt_sha256,
        )
    print(json.dumps({"revision": result["revision"], "phase": result["phase"], "release_authority": False}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReleaseError as error:
        print(json.dumps({"ok": False, "reason": str(error)}))
        raise SystemExit(2)
