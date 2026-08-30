"""Lease-bound bridge for one staged public-website design worker.

The public website delivery runner deliberately stops at a staged candidate.
This module lets a *registered* local adapter make one bounded change inside
that candidate, then asks the existing runner to validate the diff exactly
once.  It is not a release, package, deployment, credential, or canonical
website interface.

Every lease is short lived, binds the runner's restricted worker context and
an exact candidate-tree snapshot, and is consumed by an immutable execution
receipt before the built-in declarative manifest applier runs. Version 2 does
not execute arbitrary or dynamically registered worker code: an autonomous
system may submit data only. Any future executable adapter must use a separate
OS-level sandbox with no secrets, network, or canonical-site mount.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlparse

from aureon.autonomous import aureon_public_website_design_runner as runner
from aureon.operator.design_candidate_claim_surface import (
    MANIFEST_KINDS,
    MANIFEST_RATIONALES_BY_KIND,
)
from aureon.operator.design_candidate_control import (
    CONTROLLED_TEXT_EXTENSIONS,
    DEFAULT_CANDIDATE_ROOT,
)
from aureon.operator.design_stakeholder_feedback import RESPONSE_CODES
from aureon.operator.secure_immutable_artifact import (
    SecureImmutableArtifactError,
    write_new_file,
)

LEASE_SCHEMA = "aureon.staged-design-worker-lease.v2"
ISSUANCE_SCHEMA = "aureon.staged-design-worker-issuance.v2"
EXECUTION_SCHEMA = "aureon.staged-design-worker-execution.v2"
OUTCOME_SCHEMA = "aureon.staged-design-worker-outcome.v2"
LEGACY_LEASE_SCHEMA = "aureon.staged-design-worker-lease.v1"
LEGACY_ISSUANCE_SCHEMA = "aureon.staged-design-worker-issuance.v1"
LEGACY_EXECUTION_SCHEMA = "aureon.staged-design-worker-execution.v1"
LEGACY_OUTCOME_SCHEMA = "aureon.staged-design-worker-outcome.v1"

DEFAULT_TRUSTED_ADAPTER_ID = "manifest-patch-v2"
DEFAULT_LEASE_TTL_SECONDS = 600
MAX_LEASE_TTL_SECONDS = 900
MAX_PATCH_BYTES = 512 * 1024
MAX_TOTAL_PATCH_BYTES = 1024 * 1024
TEXT_ONLY_EXTENSIONS = CONTROLLED_TEXT_EXTENSIONS

AUTHORITY = {
    "scope": "one leased local patch inside an existing staged website candidate only",
    "canonical_website_mutation": "never by this broker or a staged design worker",
    "release_eligible": False,
    "package_authority": "none",
    "deployment_authority": "none",
    "credential_access": "none",
    "release_authority": "WebsiteOperator owner gate only",
    "receipt_integrity_scope": (
        "local accidental-drift detection only; it is not tamper-resistant against "
        "an account with direct filesystem write access"
    ),
}

_LEASE_ID = re.compile(r"lease-[a-f0-9]{32}\Z")
_ADAPTER_ID = re.compile(r"[a-z0-9][a-z0-9._-]{2,64}\Z")
_SHA256 = re.compile(r"[A-F0-9]{64}\Z")
_FORBIDDEN_AUTHORITY_KEYS = frozenset(
    {
        "authority",
        "backup",
        "canonical_website_mutation",
        "credential",
        "credential_access",
        "credentials",
        "deploy",
        "deployment",
        "deployment_authority",
        "hosting",
        "owner_gate",
        "package",
        "package_authority",
        "promote",
        "promotion",
        "release",
        "release_eligible",
    }
)
_SUBMISSION_KEYS = frozenset(
    {
        "patch_manifest",
        "claim_impact_manifest",
        "claim_surface_manifest",
        "feedback_response_manifest",
    }
)
_FEEDBACK_RESPONSE_FIELDS = frozenset(
    {
        "disposition",
        "response_code",
        "route_scope",
        "changed_paths",
        "claim_ids",
        "signal_capsule_sha256",
    }
)
_FEEDBACK_SIGNAL_WRAPPER_FIELDS = frozenset({"signal", "signal_capsule_sha256"})
_FEEDBACK_SIGNAL_FIELDS = frozenset(
    {
        "signal_id",
        "signal_kind",
        "disposition",
        "priority",
        "requested_response_dimension",
        "route_scope",
        "claim_ids",
    }
)
_MUTATION_CONTRACT_FIELDS = frozenset(
    {
        "text_write_paths",
        "binary_read_authority",
        "binary_write_authority",
        "binary_import_authority",
        "canonical_write_authority",
    }
)
_ASSET_REQUIREMENT_FIELDS = frozenset(
    {
        "required",
        "declared_binary_paths",
        "trusted_import_extensions",
        "import_operation",
        "receipt_replay_required",
    }
)
_AUTHORING_CONTRACT_FIELDS = frozenset(
    {
        "schema",
        "state",
        "surfaces",
        "surfaces_sha256",
        "trusted_evidence",
        "trusted_evidence_sha256",
        "contract_sha256",
    }
)
_AUTHORING_SURFACE_FIELDS = frozenset(
    {
        "route",
        "destination",
        "surface_id",
        "public_post_url",
        "variants",
        "alt",
        "caption",
        "credit",
    }
)
_AUTHORING_VARIANT_FIELDS = frozenset({"role", "public_path", "media_type", "width", "height"})
_AUTHORING_EVIDENCE_FIELDS = frozenset(
    {
        "import_receipt_payload_sha256",
        "imports_sha256",
        "provenance_manifest_sha256",
        "selected_asset_capsules_sha256",
        "selected_route_asset_capsules_sha256",
    }
)
_INVESTOR_COPY_CONTEXT_FIELDS = frozenset(
    {
        "schema",
        "required",
        "contract_id",
        "contract_file_sha256",
        "contract_json_sha256",
        "task_id",
        "task_sha256",
        "route",
        "path",
        "source_audit",
        "claim_control",
        "acceptance",
        "authority",
    }
)
_INVESTOR_COPY_AUDIT_FIELDS = frozenset(
    {
        "findings_sha256",
        "rule_histogram",
        "finding_count",
        "blocker_count",
        "warning_count",
        "target_blocker_count",
        "target_warning_count",
    }
)
_INVESTOR_COPY_CLAIM_FIELDS = frozenset(
    {
        "route_claim_capsule_sha256",
        "required_claim_ids",
        "required_concept_groups_sha256",
        "satisfied_concept_ids",
    }
)
_INVESTOR_COPY_ACCEPTANCE_FIELDS = frozenset(
    {
        "candidate_reaudit_required",
        "zero_blockers_required",
        "zero_warnings_required",
        "exact_route_only",
        "unchanged_non_target_files_required",
    }
)
_INVESTOR_COPY_AUTHORITY = {
    "workspace": "exact staged HTML path only",
    "canonical_write_authority": "none",
    "claim_register_mutation": "none",
    "package_authority": "none",
    "deployment_authority": "none",
    "credential_access": "none",
}


class StagedDesignWorkerBrokerError(ValueError):
    """A proposed staged worker action is stale, malformed, or outside scope."""


class _StagedDesignWorkerManifestError(StagedDesignWorkerBrokerError):
    """A registered adapter wrote a result that is not its sealed patch manifest."""


@dataclass(frozen=True)
class RestrictedStagedDesignWorkerContext:
    """Worker-visible context with no repository-root or authority capability."""

    lease_id: str
    run_id: str
    adapter_id: str
    route_id: str
    route: str
    route_purpose: str
    content_order: tuple[str, ...]
    allowed_paths: tuple[str, ...]
    claim_capsule: Mapping[str, Any]
    claim_capsule_sha256: str
    feedback_capsule: Mapping[str, Any]
    feedback_capsule_sha256: str
    editorial_authoring_contract: Mapping[str, Any] | None
    investor_copy_repair: Mapping[str, Any] | None
    visual_rules: tuple[Mapping[str, Any], ...]
    acceptance_criteria: tuple[str, ...]
    prohibited_public_inferences: tuple[str, ...]
    work_order_sha256: str
    worker_context_sha256: str
    workspace_snapshot_sha256: str
    prohibited_operations: tuple[str, ...]


class StagedDesignWorkerSandbox:
    """A write-only-to-declared-paths view of the staged website workspace."""

    __slots__ = ("__declared_paths", "__workspace", "__writes")

    def __init__(
        self,
        workspace: Path,
        declared_paths: Sequence[str],
        *,
        repo_root: Path,
    ) -> None:
        _reject_symlink_ancestors(repo_root, workspace)
        self.__workspace = workspace.absolute()
        if not self.__workspace.is_dir() or _is_link_or_reparse_point(self.__workspace):
            raise StagedDesignWorkerBrokerError(
                "A staged worker workspace must be a regular non-link directory."
            )
        self.__declared_paths = frozenset(declared_paths)
        self.__writes: list[str] = []

    @property
    def written_paths(self) -> tuple[str, ...]:
        """Return only the relative candidate paths written through this sandbox."""

        return tuple(self.__writes)

    def read_text(self, path: str) -> str:
        """Read one declared candidate file as UTF-8 text."""

        target = self._target(path)
        _assert_regular_unlinked_file(target, label="A staged worker read target")
        return target.read_text(encoding="utf-8")

    def write_text(self, path: str, content: str) -> None:
        """Replace one declared candidate file without exposing a broader filesystem API."""

        if not isinstance(content, str):
            raise StagedDesignWorkerBrokerError("A staged worker patch must be UTF-8 text.")
        encoded = content.encode("utf-8")
        if len(encoded) > MAX_PATCH_BYTES:
            raise StagedDesignWorkerBrokerError("A staged worker patch exceeds the per-file size limit.")
        target = self._target(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        _reject_symlink_ancestors(self.__workspace, target.parent)
        if target.exists():
            _assert_regular_unlinked_file(target, label="A staged worker write target")
        _atomic_replace_text(target, encoded)
        if path not in self.__writes:
            self.__writes.append(path)

    def _target(self, path: str) -> Path:
        safe = _safe_relative_path(path, label="Staged worker path")
        if safe not in self.__declared_paths:
            raise StagedDesignWorkerBrokerError("A staged worker path is not declared by this submission.")
        target = self.__workspace / safe
        try:
            target.absolute().relative_to(self.__workspace.absolute())
        except ValueError as exc:
            raise StagedDesignWorkerBrokerError(
                "A staged worker path escapes its candidate workspace."
            ) from exc
        return target


def _utc_now(value: datetime | None = None) -> datetime:
    current = value or datetime.now(UTC)
    if current.tzinfo is None or current.utcoffset() is None:
        raise StagedDesignWorkerBrokerError("Lease timestamps must be timezone-aware UTC values.")
    return current.astimezone(UTC)


def _utc_iso(value: datetime | None = None) -> str:
    return _utc_now(value).isoformat().replace("+00:00", "Z")


def _parse_utc(value: object, *, label: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise StagedDesignWorkerBrokerError(f"{label} must be an absolute UTC timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise StagedDesignWorkerBrokerError(f"{label} must be an ISO-8601 UTC timestamp.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise StagedDesignWorkerBrokerError(f"{label} must declare an absolute timezone.")
    return parsed.astimezone(UTC)


def _find_repo_root(start: Path | None = None) -> Path:
    try:
        return runner._find_repo_root(start)  # noqa: SLF001 - one bounded runner integration point
    except runner.PublicWebsiteDesignRunnerError as exc:
        raise StagedDesignWorkerBrokerError(str(exc)) from exc


def _json_sha256(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest().upper()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _mapping(value: object, *, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise StagedDesignWorkerBrokerError(f"{label} must be an object.")
    return dict(value)


def _safe_run_id(value: object) -> str:
    try:
        return runner._safe_run_id(value)  # noqa: SLF001 - preserves the runner's run-id contract
    except runner.PublicWebsiteDesignRunnerError as exc:
        raise StagedDesignWorkerBrokerError(str(exc)) from exc


def _safe_lease_id(value: object) -> str:
    if not isinstance(value, str) or not _LEASE_ID.fullmatch(value):
        raise StagedDesignWorkerBrokerError("Lease id is not a broker-issued immutable identifier.")
    return value


def _safe_adapter_id(value: object) -> str:
    if not isinstance(value, str) or not _ADAPTER_ID.fullmatch(value):
        raise StagedDesignWorkerBrokerError("Adapter id must be a stable lowercase registered identifier.")
    return value


def _safe_relative_path(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StagedDesignWorkerBrokerError(f"{label} must be a non-empty relative path.")
    normalised = value.replace("\\", "/")
    path = Path(normalised)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise StagedDesignWorkerBrokerError(f"{label} is not a safe candidate-relative path.")
    return path.as_posix()


def _relative_to_repo(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise StagedDesignWorkerBrokerError(
            "Broker evidence must remain inside the Aureon repository."
        ) from exc


def _is_link_or_reparse_point(path: Path) -> bool:
    """Detect both POSIX links and Windows reparse points without resolving them."""

    try:
        details = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(details.st_mode) or bool(
        getattr(details, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def _assert_regular_unlinked_file(path: Path, *, label: str) -> None:
    """Reject links before a worker reads or replaces a staged candidate file."""

    if _is_link_or_reparse_point(path) or not path.is_file():
        raise StagedDesignWorkerBrokerError(f"{label} must be a regular non-link file.")
    if path.stat().st_nlink != 1:
        raise StagedDesignWorkerBrokerError(f"{label} must not share a hard link.")


def _atomic_replace_text(path: Path, content: bytes) -> None:
    """Replace one candidate file without mutating a possible linked inode."""

    with tempfile.NamedTemporaryFile(
        "wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as stream:
        stream.write(content)
        temporary = Path(stream.name)
    try:
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _reject_symlink_ancestors(root: Path, target: Path) -> None:
    """Reject existing link/reparse ancestors without resolving the raw path first."""

    raw_root = root.absolute()
    raw_target = target.absolute()
    if _is_link_or_reparse_point(raw_root) or not raw_root.is_dir():
        raise StagedDesignWorkerBrokerError("Candidate workspace must be a regular existing directory.")
    try:
        relative = raw_target.relative_to(raw_root)
    except ValueError as exc:
        raise StagedDesignWorkerBrokerError(
            "Broker receipt or worker path escapes its candidate root."
        ) from exc
    cursor = raw_root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.exists() and _is_link_or_reparse_point(cursor):
            raise StagedDesignWorkerBrokerError(
                "Symbolic links and reparse points are not permitted in staged worker paths."
            )


def _resolve_repo_directory(root: Path, value: object, *, label: str, allowed_root: Path) -> Path:
    safe = _safe_relative_path(value, label=label)
    raw = root / safe
    _reject_symlink_ancestors(root, raw)
    target = raw.resolve()
    approved = allowed_root.resolve()
    try:
        target.relative_to(approved)
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise StagedDesignWorkerBrokerError(f"{label} escapes its approved staged artifact root.") from exc
    if not target.is_dir() or _is_link_or_reparse_point(target):
        raise StagedDesignWorkerBrokerError(f"{label} must be a regular existing directory.")
    _reject_symlink_ancestors(approved, target)
    return target


def _resolve_repo_file(root: Path, value: object, *, label: str, allowed_root: Path) -> Path:
    safe = _safe_relative_path(value, label=label)
    raw = root / safe
    _reject_symlink_ancestors(root, raw)
    target = raw.resolve()
    approved = allowed_root.resolve()
    try:
        target.relative_to(approved)
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise StagedDesignWorkerBrokerError(f"{label} escapes its approved artifact root.") from exc
    _assert_regular_unlinked_file(target, label=label)
    _reject_symlink_ancestors(approved, target.parent)
    return target


def _bounded_workspace_files(root: Path) -> list[Path]:
    """Enumerate a candidate tree without following a link or junction."""

    lexical_root = root.absolute()
    if _is_link_or_reparse_point(lexical_root) or not lexical_root.is_dir():
        raise StagedDesignWorkerBrokerError("Candidate workspace must be a regular non-link directory.")
    try:
        real_root = lexical_root.resolve(strict=True)
    except OSError as exc:
        raise StagedDesignWorkerBrokerError("Candidate workspace cannot be resolved safely.") from exc

    directories = [lexical_root]
    files: list[Path] = []
    while directories:
        directory = directories.pop()
        try:
            directory.absolute().relative_to(lexical_root)
            directory.resolve(strict=True).relative_to(real_root)
        except (OSError, ValueError) as exc:
            raise StagedDesignWorkerBrokerError(
                "Candidate workspace path escapes its lexical or real root."
            ) from exc
        try:
            entries = sorted(os.scandir(directory), key=lambda item: item.name)
        except OSError as exc:
            raise StagedDesignWorkerBrokerError("Candidate workspace cannot be enumerated safely.") from exc
        for entry in entries:
            path = Path(entry.path)
            if _is_link_or_reparse_point(path):
                raise StagedDesignWorkerBrokerError(
                    "Candidate workspace cannot contain symbolic links or reparse points."
                )
            try:
                path.absolute().relative_to(lexical_root)
                path.resolve(strict=True).relative_to(real_root)
                details = path.lstat()
            except (OSError, ValueError) as exc:
                raise StagedDesignWorkerBrokerError(
                    "Candidate workspace path escapes its lexical or real root."
                ) from exc
            if stat.S_ISDIR(details.st_mode):
                directories.append(path)
            elif stat.S_ISREG(details.st_mode):
                files.append(path)
            else:
                raise StagedDesignWorkerBrokerError(
                    "Candidate workspace may contain only regular files and directories."
                )
    return sorted(
        files,
        key=lambda item: item.relative_to(lexical_root).as_posix(),
    )


def _candidate_workspace_snapshot(
    root: Path, job: Mapping[str, Any], context: Mapping[str, Any]
) -> tuple[Path, dict[str, Any]]:
    candidate = _mapping(job.get("candidate"), label="Staged candidate")
    workspace = _mapping(context.get("workspace"), label="Runner worker workspace")
    candidate_root = _resolve_repo_directory(
        root,
        candidate.get("candidate_root"),
        label="Staged candidate root",
        allowed_root=(root / DEFAULT_CANDIDATE_ROOT).resolve(),
    )
    candidate_website = _resolve_repo_directory(
        root,
        workspace.get("candidate_website"),
        label="Staged candidate website",
        allowed_root=candidate_root,
    )
    if candidate.get("candidate_website") != _relative_to_repo(root, candidate_website):
        raise StagedDesignWorkerBrokerError(
            "Runner worker context does not match its staged candidate workspace."
        )

    rows: list[dict[str, Any]] = []
    for path in _bounded_workspace_files(candidate_website):
        _assert_regular_unlinked_file(path, label="Candidate workspace file")
        rows.append(
            {
                "path": path.relative_to(candidate_website).as_posix(),
                "sha256": _sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    snapshot = {
        "candidate_root": _relative_to_repo(root, candidate_root),
        "candidate_website": _relative_to_repo(root, candidate_website),
        "tree_sha256": _json_sha256(rows),
        "file_count": len(rows),
        "total_bytes": sum(int(row["bytes"]) for row in rows),
        "files": rows,
    }
    return candidate_root, snapshot


def _candidate_root_for_run(root: Path, run_id: str) -> Path:
    """Resolve the deterministic candidate root even after a consumed run advances state."""

    try:
        job, _ = runner.load_latest_delivery_job(run_id, repo_root=root)
    except runner.PublicWebsiteDesignRunnerError as exc:
        raise StagedDesignWorkerBrokerError(str(exc)) from exc
    candidate = _mapping(job.get("candidate"), label="Staged candidate")
    return _resolve_repo_directory(
        root,
        candidate.get("candidate_root"),
        label="Staged candidate root",
        allowed_root=(root / DEFAULT_CANDIDATE_ROOT).resolve(),
    )


def _route_binding(context: Mapping[str, Any]) -> dict[str, Any]:
    route = _mapping(context.get("route"), label="Runner worker route")
    capsule = _mapping(route.get("claim_capsule"), label="Runner route claim capsule")
    feedback_capsule = _mapping(
        route.get("feedback_capsule"),
        label="Runner route stakeholder-feedback capsule",
    )
    allowed_raw = route.get("allowed_paths")
    if not isinstance(allowed_raw, list) or not allowed_raw:
        raise StagedDesignWorkerBrokerError("Runner worker context lacks an exact allowed path list.")
    allowed_paths = [_safe_relative_path(value, label="Runner allowed path") for value in allowed_raw]
    if len(allowed_paths) != len(set(allowed_paths)):
        raise StagedDesignWorkerBrokerError("Runner worker context has duplicate allowed paths.")
    mutation_contract = _mapping(
        context.get("mutation_contract"),
        label="Runner worker mutation contract",
    )
    if set(mutation_contract) != _MUTATION_CONTRACT_FIELDS:
        raise StagedDesignWorkerBrokerError(
            "Runner worker mutation contract does not match the exact text-only boundary."
        )
    raw_text_paths = mutation_contract.get("text_write_paths")
    if not isinstance(raw_text_paths, list) or not raw_text_paths:
        raise StagedDesignWorkerBrokerError(
            "Runner worker mutation contract has no controlled text write paths."
        )
    text_write_paths = [
        _safe_relative_path(value, label="Runner text write path") for value in raw_text_paths
    ]
    if (
        text_write_paths != sorted(text_write_paths)
        or len(text_write_paths) != len(set(text_write_paths))
        or any(Path(path).suffix.casefold() not in TEXT_ONLY_EXTENSIONS for path in text_write_paths)
        or allowed_paths != text_write_paths
        or mutation_contract.get("binary_read_authority") != "none"
        or mutation_contract.get("binary_write_authority") != "none"
        or mutation_contract.get("binary_import_authority") != "none"
        or mutation_contract.get("canonical_write_authority") != "none"
    ):
        raise StagedDesignWorkerBrokerError(
            "Runner worker route must expose only its exact controlled text write "
            "paths and no binary or canonical authority."
        )
    capsule_sha256 = str(route.get("claim_capsule_sha256") or "")
    if not _SHA256.fullmatch(capsule_sha256) or capsule_sha256 != _json_sha256(capsule):
        raise StagedDesignWorkerBrokerError("Runner route claim capsule hash does not verify.")
    feedback_capsule_sha256 = str(route.get("feedback_capsule_sha256") or "")
    if not _SHA256.fullmatch(feedback_capsule_sha256) or feedback_capsule_sha256 != _json_sha256(
        feedback_capsule
    ):
        raise StagedDesignWorkerBrokerError("Runner route stakeholder-feedback capsule hash does not verify.")
    route_id = route.get("id")
    route_path = route.get("route")
    if not isinstance(route_id, str) or not route_id or not isinstance(route_path, str) or not route_path:
        raise StagedDesignWorkerBrokerError("Runner worker context lacks a route identity.")
    if (
        feedback_capsule.get("route_id") != route_id
        or feedback_capsule.get("route") != route_path
        or not isinstance(feedback_capsule.get("signals"), list)
        or not all(isinstance(item, Mapping) for item in feedback_capsule.get("signals", []))
    ):
        raise StagedDesignWorkerBrokerError(
            "Runner stakeholder-feedback capsule does not bind the exact worker route."
        )
    binding = {
        "id": route_id,
        "route": route_path,
        "allowed_paths": allowed_paths,
        "claim_capsule_sha256": capsule_sha256,
        "feedback_capsule_sha256": feedback_capsule_sha256,
    }
    binding["route_binding_sha256"] = _json_sha256(binding)
    return binding


def _investor_copy_worker_binding(
    context: Mapping[str, Any],
    route: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Validate the runner's privacy-minimised exact-HTML copy projection."""

    raw_copy = context.get("investor_copy_repair")
    if raw_copy is None:
        return None
    copy = _mapping(
        raw_copy,
        label="Runner investor-copy worker context",
    )
    if (
        set(copy) != _INVESTOR_COPY_CONTEXT_FIELDS
        or copy.get("schema") != runner.INVESTOR_COPY_WORKER_CONTEXT_SCHEMA
        or copy.get("required") is not True
        or not isinstance(copy.get("contract_id"), str)
        or not copy["contract_id"]
        or not isinstance(copy.get("task_id"), str)
        or re.fullmatch(r"DESIGN-COPY-[0-9]{3}", str(copy["task_id"])) is None
        or not isinstance(copy.get("contract_file_sha256"), str)
        or not _SHA256.fullmatch(str(copy["contract_file_sha256"]))
        or not isinstance(copy.get("contract_json_sha256"), str)
        or not _SHA256.fullmatch(str(copy["contract_json_sha256"]))
        or not isinstance(copy.get("task_sha256"), str)
        or not _SHA256.fullmatch(str(copy["task_sha256"]))
        or copy.get("route") != route.get("route")
        or not isinstance(copy.get("path"), str)
        or Path(str(copy["path"])).suffix.casefold() not in {".html", ".htm"}
        or route.get("allowed_paths") != [copy.get("path")]
        or copy.get("authority") != _INVESTOR_COPY_AUTHORITY
    ):
        raise StagedDesignWorkerBrokerError(
            "Runner investor-copy context lost its exact task, contract, route, HTML, or no-authority binding."
        )

    source_audit = _mapping(
        copy.get("source_audit"),
        label="Runner investor-copy source audit",
    )
    if (
        set(source_audit) != _INVESTOR_COPY_AUDIT_FIELDS
        or not isinstance(source_audit.get("findings_sha256"), str)
        or not _SHA256.fullmatch(str(source_audit["findings_sha256"]))
        or not isinstance(source_audit.get("rule_histogram"), list)
        or not all(isinstance(item, Mapping) for item in source_audit["rule_histogram"])
    ):
        raise StagedDesignWorkerBrokerError("Runner investor-copy source audit projection is malformed.")
    for field in (
        "finding_count",
        "blocker_count",
        "warning_count",
        "target_blocker_count",
        "target_warning_count",
    ):
        value = source_audit.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise StagedDesignWorkerBrokerError("Runner investor-copy source audit counts are malformed.")

    claim_control = _mapping(
        copy.get("claim_control"),
        label="Runner investor-copy claim control",
    )
    source_route = _mapping(
        _mapping(context.get("route"), label="Runner worker route").get("claim_capsule"),
        label="Runner route claim capsule",
    )
    raw_claims = source_route.get("claims")
    if not isinstance(raw_claims, list) or not raw_claims:
        raise StagedDesignWorkerBrokerError(
            "Runner route claim capsule is unavailable for investor-copy binding."
        )
    capsule_claim_ids = sorted(
        str(item.get("id"))
        for item in raw_claims
        if isinstance(item, Mapping) and isinstance(item.get("id"), str)
    )
    required_ids = claim_control.get("required_claim_ids")
    satisfied_ids = claim_control.get("satisfied_concept_ids")
    if (
        set(claim_control) != _INVESTOR_COPY_CLAIM_FIELDS
        or claim_control.get("route_claim_capsule_sha256") != route.get("claim_capsule_sha256")
        or not isinstance(
            claim_control.get("required_concept_groups_sha256"),
            str,
        )
        or not _SHA256.fullmatch(str(claim_control["required_concept_groups_sha256"]))
        or not isinstance(required_ids, list)
        or not all(isinstance(item, str) and item for item in required_ids)
        or required_ids != sorted(set(required_ids))
        or required_ids != capsule_claim_ids
        or not isinstance(satisfied_ids, list)
        or not all(isinstance(item, str) and item for item in satisfied_ids)
        or satisfied_ids != sorted(set(satisfied_ids))
    ):
        raise StagedDesignWorkerBrokerError(
            "Runner investor-copy claim control no longer matches the sealed route capsule."
        )

    acceptance = _mapping(
        copy.get("acceptance"),
        label="Runner investor-copy acceptance",
    )
    if set(acceptance) != _INVESTOR_COPY_ACCEPTANCE_FIELDS or not all(
        acceptance.get(field) is True for field in _INVESTOR_COPY_ACCEPTANCE_FIELDS
    ):
        raise StagedDesignWorkerBrokerError("Runner investor-copy acceptance controls were weakened.")
    return copy


def _editorial_authoring_binding(
    context: Mapping[str, Any],
    route: Mapping[str, Any],
    *,
    assets_required: bool,
) -> dict[str, Any] | None:
    """Validate the runner's minimal post-import route authoring contract."""

    asset_import = _mapping(
        context.get("asset_import"),
        label="Runner worker asset import",
    )
    raw_contract = asset_import.get("authoring_contract")
    if not assets_required:
        if raw_contract is not None:
            raise StagedDesignWorkerBrokerError(
                "Text-only worker context must not expose an editorial authoring contract."
            )
        return None
    contract = _mapping(
        raw_contract,
        label="Runner editorial authoring contract",
    )
    if (
        set(contract) != _AUTHORING_CONTRACT_FIELDS
        or contract.get("schema") != runner.EDITORIAL_AUTHORING_CONTRACT_SCHEMA
        or contract.get("state") != "trusted-route-bound"
    ):
        raise StagedDesignWorkerBrokerError(
            "Runner editorial authoring contract does not match its exact trusted schema."
        )
    contract_sha256 = str(contract.get("contract_sha256") or "")
    contract_payload = dict(contract)
    contract_payload.pop("contract_sha256", None)
    if not _SHA256.fullmatch(contract_sha256) or contract_sha256 != _json_sha256(contract_payload):
        raise StagedDesignWorkerBrokerError("Runner editorial authoring contract hash does not verify.")

    evidence = _mapping(
        contract.get("trusted_evidence"),
        label="Runner editorial authoring evidence",
    )
    evidence_sha256 = str(contract.get("trusted_evidence_sha256") or "")
    receipt = _mapping(
        asset_import.get("receipt"),
        label="Runner editorial import receipt binding",
    )
    verification = _mapping(
        asset_import.get("verification"),
        label="Runner editorial import verification binding",
    )
    provenance = _mapping(
        asset_import.get("provenance"),
        label="Runner editorial import provenance binding",
    )
    if (
        set(evidence) != _AUTHORING_EVIDENCE_FIELDS
        or not all(isinstance(value, str) and _SHA256.fullmatch(value) for value in evidence.values())
        or not _SHA256.fullmatch(evidence_sha256)
        or evidence_sha256 != _json_sha256(evidence)
        or evidence.get("import_receipt_payload_sha256") != receipt.get("payload_sha256")
        or evidence.get("imports_sha256") != verification.get("imports_sha256")
        or evidence.get("provenance_manifest_sha256") != provenance.get("manifest_file_sha256")
        or evidence.get("selected_asset_capsules_sha256") != provenance.get("selected_asset_capsules_sha256")
        or evidence.get("selected_route_asset_capsules_sha256")
        != provenance.get("route_asset_capsules_sha256")
    ):
        raise StagedDesignWorkerBrokerError(
            "Runner editorial authoring evidence no longer binds the trusted import."
        )

    raw_surfaces = contract.get("surfaces")
    if not isinstance(raw_surfaces, list) or not raw_surfaces:
        raise StagedDesignWorkerBrokerError("Runner editorial authoring contract has no route surfaces.")
    allowed_paths = set(route.get("allowed_paths") or [])
    requirement = _mapping(
        context.get("asset_requirement"),
        label="Runner worker asset requirement",
    )
    raw_binary_paths = requirement.get("declared_binary_paths")
    if not isinstance(raw_binary_paths, list):
        raise StagedDesignWorkerBrokerError(
            "Runner editorial authoring contract lost its binary path binding."
        )
    binary_paths = {
        _safe_relative_path(
            value,
            label="Runner editorial binary path",
        )
        for value in raw_binary_paths
    }
    surfaces: list[dict[str, Any]] = []
    public_paths: set[str] = set()
    seen_surfaces: set[tuple[str, str]] = set()
    for raw_surface in raw_surfaces:
        surface = _mapping(
            raw_surface,
            label="Runner editorial authoring surface",
        )
        if set(surface) != _AUTHORING_SURFACE_FIELDS:
            raise StagedDesignWorkerBrokerError(
                "Runner editorial authoring surface contains unsupported fields."
            )
        destination = _safe_relative_path(
            surface.get("destination"),
            label="Runner editorial destination",
        )
        surface_id = surface.get("surface_id")
        public_post_url = surface.get("public_post_url")
        parsed_post = urlparse(public_post_url) if isinstance(public_post_url, str) else None
        if (
            surface.get("route") != route.get("route")
            or destination not in allowed_paths
            or not isinstance(surface_id, str)
            or not surface_id
            or parsed_post is None
            or parsed_post.scheme != "https"
            or not parsed_post.netloc
            or parsed_post.username is not None
            or parsed_post.password is not None
            or parsed_post.query
            or parsed_post.fragment
            or not all(
                isinstance(surface.get(key), str) and str(surface[key]).strip()
                for key in ("alt", "caption", "credit")
            )
        ):
            raise StagedDesignWorkerBrokerError(
                "Runner editorial authoring surface is outside its exact route or copy scope."
            )
        surface_key = (destination, surface_id)
        if surface_key in seen_surfaces:
            raise StagedDesignWorkerBrokerError(
                "Runner editorial authoring contract duplicates a route surface."
            )
        seen_surfaces.add(surface_key)
        raw_variants = surface.get("variants")
        if not isinstance(raw_variants, list) or not raw_variants:
            raise StagedDesignWorkerBrokerError("Runner editorial authoring surface has no trusted variants.")
        variants: list[dict[str, Any]] = []
        seen_roles: set[str] = set()
        for raw_variant in raw_variants:
            variant = _mapping(
                raw_variant,
                label="Runner editorial authoring variant",
            )
            if set(variant) != _AUTHORING_VARIANT_FIELDS:
                raise StagedDesignWorkerBrokerError(
                    "Runner editorial authoring variant contains unsupported fields."
                )
            role = variant.get("role")
            public_path = _safe_relative_path(
                variant.get("public_path"),
                label="Runner editorial public path",
            )
            width = variant.get("width")
            height = variant.get("height")
            if (
                role not in {"small", "large"}
                or role in seen_roles
                or public_path not in binary_paths
                or Path(public_path).suffix.casefold() != ".webp"
                or variant.get("media_type") != "image/webp"
                or not isinstance(width, int)
                or isinstance(width, bool)
                or width <= 0
                or not isinstance(height, int)
                or isinstance(height, bool)
                or height <= 0
            ):
                raise StagedDesignWorkerBrokerError(
                    "Runner editorial authoring variant drifted from its exact WebP scope."
                )
            seen_roles.add(str(role))
            public_paths.add(public_path)
            variants.append(dict(variant))
        variants.sort(key=lambda item: str(item["role"]))
        normalised_surface = dict(surface)
        normalised_surface["destination"] = destination
        normalised_surface["variants"] = variants
        surfaces.append(normalised_surface)

    surfaces.sort(
        key=lambda item: (
            str(item["route"]),
            str(item["destination"]),
            str(item["surface_id"]),
        )
    )
    if (
        surfaces != raw_surfaces
        or public_paths != binary_paths
        or contract.get("surfaces_sha256") != _json_sha256(surfaces)
    ):
        raise StagedDesignWorkerBrokerError(
            "Runner editorial authoring surfaces no longer equal their sealed route and import scope."
        )
    return contract


def _work_order_binding(root: Path, context: Mapping[str, Any], run_id: str) -> dict[str, Any]:
    work_order = _mapping(context.get("work_order"), label="Runner worker work order")
    path_value = work_order.get("path")
    work_order_path = _resolve_repo_file(
        root,
        path_value,
        label="Runner worker work order",
        allowed_root=(root / runner.DEFAULT_WORK_ORDER_ROOT).resolve(),
    )
    sha256 = str(work_order.get("sha256") or "")
    if not _SHA256.fullmatch(sha256) or sha256 != _sha256_file(work_order_path):
        raise StagedDesignWorkerBrokerError("Runner worker work-order hash does not verify.")
    if work_order.get("run_id") != run_id:
        raise StagedDesignWorkerBrokerError("Runner worker work order does not bind this run.")
    return {"path": _relative_to_repo(root, work_order_path), "sha256": sha256, "run_id": run_id}


def _text_items(value: object, *, label: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise StagedDesignWorkerBrokerError(f"{label} must be a non-empty list of text values.")
    values = [item.strip() for item in value if isinstance(item, str) and item.strip()]
    if len(values) != len(value):
        raise StagedDesignWorkerBrokerError(f"{label} must contain only non-empty text values.")
    return values


def _sealed_design_directives(
    root: Path,
    job: Mapping[str, Any],
    context: Mapping[str, Any],
    route: Mapping[str, Any],
) -> dict[str, Any]:
    """Read only the exact brief already verified by the runner and seal worker directives."""

    brief_binding = _mapping(job.get("brief_binding"), label="Runner brief binding")
    brief_reference = _mapping(brief_binding.get("brief"), label="Runner brief reference")
    brief_path = _resolve_repo_file(
        root,
        brief_reference.get("path"),
        label="Runner canonical design brief",
        allowed_root=root,
    )
    brief_sha256 = str(brief_reference.get("sha256") or "")
    if not _SHA256.fullmatch(brief_sha256) or brief_sha256 != _sha256_file(brief_path):
        raise StagedDesignWorkerBrokerError("Runner canonical design brief hash does not verify.")
    brief = _read_json(brief_path, label="Runner canonical design brief")
    route_plan = brief.get("route_plan")
    if not isinstance(route_plan, list):
        raise StagedDesignWorkerBrokerError("Runner canonical design brief lacks a route plan.")
    route_matches = [
        _mapping(item, label="Canonical brief route")
        for item in route_plan
        if isinstance(item, Mapping) and item.get("id") == route.get("id")
    ]
    if len(route_matches) != 1:
        raise StagedDesignWorkerBrokerError(
            "Worker route must occur exactly once in the canonical design brief."
        )
    route_entry = route_matches[0]
    purpose = route_entry.get("purpose")
    if not isinstance(purpose, str) or not purpose.strip():
        raise StagedDesignWorkerBrokerError(
            "Worker route purpose is missing from the canonical design brief."
        )
    content_order = _text_items(route_entry.get("content_order"), label="Worker route content order")
    raw_brief_paths = route_entry.get("allowed_paths")
    if not isinstance(raw_brief_paths, list) or not all(
        isinstance(path, str) and path for path in raw_brief_paths
    ):
        raise StagedDesignWorkerBrokerError("Canonical brief route lacks its exact public path allow-list.")
    brief_text_paths = sorted(
        path for path in raw_brief_paths if Path(path).suffix.casefold() in TEXT_ONLY_EXTENSIONS
    )
    investor_copy = _investor_copy_worker_binding(context, route)
    route_paths = route.get("allowed_paths")
    path_scope_ok = (
        brief_text_paths == route_paths
        if investor_copy is None
        else (route_paths == [investor_copy.get("path")] and investor_copy.get("path") in brief_text_paths)
    )
    if route_entry.get("route") != route.get("route") or not path_scope_ok:
        raise StagedDesignWorkerBrokerError(
            "Canonical brief route no longer matches the runner's exact text-only route binding or sealed one-HTML copy subset."
        )

    allowed_paths = {str(path) for path in route["allowed_paths"]}
    raw_visual_rules = brief.get("visual_rules")
    if not isinstance(raw_visual_rules, list):
        raise StagedDesignWorkerBrokerError("Canonical design brief lacks visual rules.")
    visual_rules: list[dict[str, Any]] = []
    for raw_rule in raw_visual_rules:
        rule = _mapping(raw_rule, label="Canonical brief visual rule")
        affects_paths = _text_items(rule.get("affects_paths"), label="Visual rule affected paths")
        if not allowed_paths.intersection(affects_paths):
            continue
        purpose_value = rule.get("purpose")
        static_equivalent = rule.get("static_equivalent")
        if (
            not isinstance(rule.get("id"), str)
            or not rule["id"]
            or not isinstance(purpose_value, str)
            or not purpose_value.strip()
            or not isinstance(static_equivalent, str)
            or not static_equivalent.strip()
            or rule.get("reduced_motion_required") is not True
        ):
            raise StagedDesignWorkerBrokerError(
                "Relevant visual rules must retain a static reduced-motion equivalent."
            )
        visual_rules.append(
            {
                "id": rule["id"],
                "purpose": purpose_value.strip(),
                "static_equivalent": static_equivalent.strip(),
                "reduced_motion_required": True,
                "affects_paths": affects_paths,
            }
        )
    if not visual_rules:
        raise StagedDesignWorkerBrokerError("Worker route has no relevant sealed visual rule.")

    prohibited = _text_items(
        brief.get("prohibited_public_inferences"),
        label="Canonical brief prohibited public inferences",
    )
    worker_route = _mapping(context.get("route"), label="Runner worker route")
    capsule = _mapping(worker_route.get("claim_capsule"), label="Runner route claim capsule")
    claims = capsule.get("claims")
    if not isinstance(claims, list) or not claims:
        raise StagedDesignWorkerBrokerError("Worker route claim capsule is empty.")
    feedback_capsule = _mapping(
        worker_route.get("feedback_capsule"),
        label="Runner route stakeholder-feedback capsule",
    )
    feedback_capsule_sha256 = str(worker_route.get("feedback_capsule_sha256") or "")
    raw_feedback_signals = feedback_capsule.get("signals")
    if (
        feedback_capsule.get("route_id") != route.get("id")
        or feedback_capsule.get("route") != route.get("route")
        or not isinstance(raw_feedback_signals, list)
        or not _SHA256.fullmatch(feedback_capsule_sha256)
        or feedback_capsule_sha256 != _json_sha256(feedback_capsule)
    ):
        raise StagedDesignWorkerBrokerError(
            "Worker route lacks a sealed code-only stakeholder-feedback capsule."
        )
    feedback_signals: list[dict[str, Any]] = []
    for raw_feedback_signal in raw_feedback_signals:
        feedback_wrapper = _mapping(
            raw_feedback_signal,
            label="Worker stakeholder signal wrapper",
        )
        if set(feedback_wrapper) != _FEEDBACK_SIGNAL_WRAPPER_FIELDS:
            raise StagedDesignWorkerBrokerError(
                "Worker stakeholder signal wrapper contains unsupported fields."
            )
        signal = _mapping(
            feedback_wrapper.get("signal"),
            label="Worker stakeholder signal",
        )
        signal_sha256 = str(feedback_wrapper.get("signal_capsule_sha256") or "")
        if (
            set(signal) != _FEEDBACK_SIGNAL_FIELDS
            or signal.get("route_scope") != route.get("route")
            or not _SHA256.fullmatch(signal_sha256)
            or signal_sha256 != _json_sha256(signal)
        ):
            raise StagedDesignWorkerBrokerError(
                "Worker stakeholder signal is malformed or outside the exact route."
            )
        feedback_signals.append(
            {
                "signal": dict(signal),
                "signal_capsule_sha256": signal_sha256,
            }
        )
    claim_prohibitions: list[str] = []
    for raw_claim in claims:
        claim = _mapping(raw_claim, label="Worker route claim")
        claim_prohibitions.extend(
            _text_items(
                claim.get("prohibited_inferences"),
                label="Worker route claim prohibited inferences",
            )
        )
    acceptance_criteria = _text_items(
        brief.get("acceptance_criteria"), label="Canonical brief acceptance criteria"
    )
    directives = {
        "brief": {"path": _relative_to_repo(root, brief_path), "sha256": brief_sha256},
        "route_purpose": purpose.strip(),
        "content_order": content_order,
        "visual_rules": visual_rules,
        "acceptance_criteria": acceptance_criteria,
        "prohibited_public_inferences": sorted(set(prohibited + claim_prohibitions)),
        "stakeholder_feedback": {
            "signals": feedback_signals,
            "feedback_capsule_sha256": feedback_capsule_sha256,
            "source_content_available": False,
        },
    }
    directives["sha256"] = _json_sha256(directives)
    return directives


def _current_binding(root: Path, run_id: str, *, now: datetime | None) -> tuple[dict[str, Any], Path]:
    """Derive all broker bindings through the existing candidate-only runner."""

    try:
        context = runner.worker_context_for_delivery_job(run_id, repo_root=root, now=now)
        job, _ = runner.load_latest_delivery_job(run_id, repo_root=root)
    except runner.PublicWebsiteDesignRunnerError as exc:
        raise StagedDesignWorkerBrokerError(str(exc)) from exc
    requirement = _mapping(
        context.get("asset_requirement"),
        label="Runner worker asset requirement",
    )
    if set(requirement) != _ASSET_REQUIREMENT_FIELDS:
        raise StagedDesignWorkerBrokerError(
            "Runner worker asset requirement does not match its exact v4 contract."
        )
    raw_binary_paths = requirement.get("declared_binary_paths")
    if not isinstance(raw_binary_paths, list) or not all(
        isinstance(path, str) and path for path in raw_binary_paths
    ):
        raise StagedDesignWorkerBrokerError(
            "Runner worker asset requirement lost its declared binary path list."
        )
    binary_paths = [
        _safe_relative_path(path, label="Runner declared binary path") for path in raw_binary_paths
    ]
    assets_required = requirement.get("required") is True
    if (
        assets_required != bool(binary_paths)
        or requirement.get("receipt_replay_required") is not assets_required
    ):
        raise StagedDesignWorkerBrokerError(
            "Runner worker asset requirement is inconsistent with its declared binary paths."
        )
    asset_import = _mapping(
        context.get("asset_import"),
        label="Runner worker asset import",
    )
    expected_state = "candidate-assets-ready" if assets_required else "candidate-staged"
    expected_import_state = "candidate-assets-ready" if assets_required else "not-required-text-only"
    if (
        job.get("state") != expected_state
        or context.get("run_id") != run_id
        or asset_import.get("required") is not assets_required
        or asset_import.get("state") != expected_import_state
        or asset_import.get("assets_ready") is not assets_required
        or asset_import.get("release_eligible") is not False
        or asset_import.get("package_authority") != "none"
        or asset_import.get("deployment_authority") != "none"
    ):
        raise StagedDesignWorkerBrokerError(
            "A worker lease is available only for a current untouched text-only "
            "candidate-staged job or a binary-bearing candidate-assets-ready job."
        )
    candidate_root, workspace_snapshot = _candidate_workspace_snapshot(root, job, context)
    route = _route_binding(context)
    _editorial_authoring_binding(
        context,
        route,
        assets_required=assets_required,
    )
    work_order = _work_order_binding(root, context, run_id)
    design_directives = _sealed_design_directives(root, job, context, route)
    context_sha256 = _json_sha256(context)
    return (
        {
            "worker_context_sha256": context_sha256,
            "work_order": work_order,
            "route": route,
            "design_directives": design_directives,
            "workspace_snapshot": workspace_snapshot,
            "worker_context": context,
        },
        candidate_root,
    )


def _receipt_path(candidate_root: Path, category: str, lease_id: str) -> Path:
    if category not in {"leases", "executions", "outcomes"}:
        raise StagedDesignWorkerBrokerError("Unknown staged worker receipt category.")
    safe_lease_id = _safe_lease_id(lease_id)
    target = candidate_root / "worker-broker" / category / f"{safe_lease_id}.v2.json"
    _reject_symlink_ancestors(candidate_root, target.parent)
    resolved = target.resolve()
    try:
        resolved.relative_to(candidate_root.resolve())
    except ValueError as exc:
        raise StagedDesignWorkerBrokerError("Staged worker receipt escapes its candidate root.") from exc
    return resolved


def _issuance_receipt_path(candidate_root: Path) -> Path:
    """Return the fixed per-run receipt which atomically permits only one lease."""

    target = candidate_root / "worker-broker" / "lease-issuance.v2.json"
    _reject_symlink_ancestors(candidate_root, target.parent)
    resolved = target.resolve()
    try:
        resolved.relative_to(candidate_root.resolve())
    except ValueError as exc:
        raise StagedDesignWorkerBrokerError(
            "Staged worker issuance receipt escapes its candidate root."
        ) from exc
    return resolved


def _assert_no_prior_worker_activity(candidate_root: Path) -> None:
    """Fail closed when this staged run already contains any worker evidence."""

    broker_root = candidate_root / "worker-broker"
    if not broker_root.exists():
        return
    if broker_root.is_symlink() or not broker_root.is_dir():
        raise StagedDesignWorkerBrokerError("Staged worker receipt root must be a regular directory.")
    _reject_symlink_ancestors(candidate_root, broker_root)
    if any(broker_root.iterdir()):
        raise StagedDesignWorkerBrokerError(
            "This staged candidate already has worker evidence; issue a separately scoped successor run."
        )


def _atomic_no_overwrite_json(candidate_root: Path, path: Path, payload: Mapping[str, Any]) -> Path:
    """Claim a new immutable receipt name atomically; never replace existing evidence."""

    _reject_symlink_ancestors(candidate_root, path.parent)
    path.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlink_ancestors(candidate_root, path.parent)
    if path.exists() or path.is_symlink():
        raise StagedDesignWorkerBrokerError(f"Refusing to overwrite immutable staged-worker evidence: {path}")
    encoded = (
        json.dumps(
            dict(payload),
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )
    try:
        write_new_file(path, encoded)
    except SecureImmutableArtifactError as exc:
        raise StagedDesignWorkerBrokerError(
            f"Refusing to overwrite immutable staged-worker evidence: {path}"
        ) from exc
    return path


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise StagedDesignWorkerBrokerError(f"{label} must be an existing regular receipt file.")
    try:
        parsed = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StagedDesignWorkerBrokerError(f"{label} is not valid JSON.") from exc
    return _mapping(parsed, label=label)


def _lease_integrity(lease: Mapping[str, Any]) -> str:
    core = dict(lease)
    core.pop("integrity_sha256", None)
    return _json_sha256(core)


def _reject_authority_fields(value: object) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if isinstance(key, str) and key.lower() in _FORBIDDEN_AUTHORITY_KEYS:
                raise StagedDesignWorkerBrokerError(
                    "Worker submissions cannot request release, deployment, or credentials."
                )
            _reject_authority_fields(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_authority_fields(nested)


def _reject_worker_qa_fields(value: object) -> None:
    """Reject legacy or nested worker assertions before the adapter is claimed."""

    if isinstance(value, Mapping):
        for key, nested in value.items():
            if isinstance(key, str) and key.casefold() == "test_manifest":
                raise StagedDesignWorkerBrokerError(
                    "V2 workers have no test-manifest, QA-policy, status or evidence authority."
                )
            _reject_worker_qa_fields(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_worker_qa_fields(nested)


def _normalise_submission(
    submission: Mapping[str, Any],
    *,
    allowed_paths: Sequence[str],
    feedback_capsule: Mapping[str, Any],
    feedback_capsule_sha256: str,
) -> dict[str, Any]:
    raw = _mapping(submission, label="Staged worker submission")
    _reject_worker_qa_fields(raw)
    _reject_authority_fields(raw)
    unexpected = sorted(set(raw).difference(_SUBMISSION_KEYS))
    if unexpected:
        raise StagedDesignWorkerBrokerError(
            "Worker submission contains an unrecognised or authority-bearing field."
        )

    allowed = set(allowed_paths)
    raw_patches = raw.get("patch_manifest")
    if not isinstance(raw_patches, list) or not raw_patches:
        raise StagedDesignWorkerBrokerError("Worker submission needs a non-empty patch manifest.")
    patches: list[dict[str, str]] = []
    patch_paths: list[str] = []
    total_patch_bytes = 0
    for item in raw_patches:
        patch = _mapping(item, label="Worker patch manifest entry")
        if set(patch).difference({"path", "content"}) or "path" not in patch or "content" not in patch:
            raise StagedDesignWorkerBrokerError("Each worker patch must contain only path and UTF-8 content.")
        path = _safe_relative_path(patch.get("path"), label="Worker patch path")
        if path not in allowed:
            raise StagedDesignWorkerBrokerError(
                "A worker patch path is outside the route's exact allow-list."
            )
        if Path(path).suffix.lower() not in TEXT_ONLY_EXTENSIONS:
            raise StagedDesignWorkerBrokerError(
                "Staged worker v2 accepts text-only public files and cannot mutate binary assets."
            )
        content = patch.get("content")
        if not isinstance(content, str):
            raise StagedDesignWorkerBrokerError("Worker patch content must be UTF-8 text.")
        size = len(content.encode("utf-8"))
        if size > MAX_PATCH_BYTES:
            raise StagedDesignWorkerBrokerError("A worker patch exceeds the per-file size limit.")
        total_patch_bytes += size
        patches.append({"path": path, "content": content})
        patch_paths.append(path)
    if len(patch_paths) != len(set(patch_paths)):
        raise StagedDesignWorkerBrokerError("Worker patch paths must be unique.")
    if total_patch_bytes > MAX_TOTAL_PATCH_BYTES:
        raise StagedDesignWorkerBrokerError("Worker submission exceeds the aggregate patch size limit.")

    raw_impacts = raw.get("claim_impact_manifest")
    if not isinstance(raw_impacts, list) or not raw_impacts:
        raise StagedDesignWorkerBrokerError("Worker submission needs a non-empty claim-impact manifest.")
    impacts: list[dict[str, str]] = []
    impact_paths: list[str] = []
    for item in raw_impacts:
        impact = _mapping(item, label="Worker claim-impact manifest entry")
        required = {"path", "classification", "rationale"}
        if set(impact) != required:
            raise StagedDesignWorkerBrokerError(
                "Each claim-impact entry must have path, classification, and rationale."
            )
        path = _safe_relative_path(impact.get("path"), label="Worker claim-impact path")
        classification = impact.get("classification")
        rationale = impact.get("rationale")
        if classification not in {"no-material-claim-change", "material-claim-change"}:
            raise StagedDesignWorkerBrokerError("Worker claim-impact classification is not recognised.")
        if not isinstance(rationale, str) or not rationale.strip():
            raise StagedDesignWorkerBrokerError("Worker claim-impact rationale must be non-empty.")
        impacts.append({"path": path, "classification": str(classification), "rationale": rationale.strip()})
        impact_paths.append(path)
    if len(impact_paths) != len(set(impact_paths)) or set(impact_paths) != set(patch_paths):
        raise StagedDesignWorkerBrokerError(
            "Claim-impact entries must occur exactly once for every declared worker patch path."
        )

    # The worker supplies hashes and classifications only.  The runner derives
    # the actual rendered text from the sealed staged tree, so a worker cannot
    # self-certify unsupported investor-facing copy.
    raw_surfaces = raw.get("claim_surface_manifest")
    if not isinstance(raw_surfaces, list):
        raise StagedDesignWorkerBrokerError(
            "Worker submission needs a claim-surface manifest list (empty for no-copy changes)."
        )
    surfaces: list[dict[str, str]] = []
    surface_keys: list[tuple[str, str]] = []
    for item in raw_surfaces:
        surface = _mapping(item, label="Worker claim-surface manifest entry")
        required = {"path", "kind", "claim_id", "text_sha256", "surface_sha256", "rationale"}
        if set(surface) != required:
            raise StagedDesignWorkerBrokerError(
                "Each claim-surface entry must have path, kind, claim_id, text_sha256, surface_sha256, and rationale."
            )
        path = _safe_relative_path(surface.get("path"), label="Worker claim-surface path")
        kind = surface.get("kind")
        claim_id = surface.get("claim_id")
        text_sha256 = surface.get("text_sha256")
        surface_sha256 = surface.get("surface_sha256")
        rationale = surface.get("rationale")
        if (
            path not in allowed
            or kind not in MANIFEST_KINDS
            or not isinstance(claim_id, str)
            or not isinstance(text_sha256, str)
            or not _SHA256.fullmatch(text_sha256)
            or not isinstance(surface_sha256, str)
            or not _SHA256.fullmatch(surface_sha256)
            or not isinstance(rationale, str)
            or rationale not in MANIFEST_RATIONALES_BY_KIND.get(str(kind), frozenset())
            or (kind == "non-claim" and claim_id)
            or (kind != "non-claim" and not claim_id)
        ):
            raise StagedDesignWorkerBrokerError(
                "Worker claim-surface manifest entry is malformed or outside the exact route scope."
            )
        surfaces.append(
            {
                "path": path,
                "kind": str(kind),
                "claim_id": claim_id,
                "text_sha256": text_sha256,
                "surface_sha256": surface_sha256,
                "rationale": rationale,
            }
        )
        surface_keys.append((path, surface_sha256))
    if len(surface_keys) != len(set(surface_keys)):
        raise StagedDesignWorkerBrokerError(
            "Worker claim-surface manifest cannot duplicate a public text surface."
        )

    if not _SHA256.fullmatch(feedback_capsule_sha256) or feedback_capsule_sha256 != _json_sha256(
        feedback_capsule
    ):
        raise StagedDesignWorkerBrokerError(
            "The sealed route stakeholder-feedback capsule no longer verifies."
        )
    raw_signal_wrappers = feedback_capsule.get("signals")
    if not isinstance(raw_signal_wrappers, list):
        raise StagedDesignWorkerBrokerError(
            "The sealed route stakeholder-feedback capsule lacks a signal list."
        )
    signals_by_id: dict[str, dict[str, Any]] = {}
    signal_hashes: dict[str, str] = {}
    for raw_signal_wrapper in raw_signal_wrappers:
        signal_wrapper = _mapping(
            raw_signal_wrapper,
            label="Sealed stakeholder signal wrapper",
        )
        if set(signal_wrapper) != _FEEDBACK_SIGNAL_WRAPPER_FIELDS:
            raise StagedDesignWorkerBrokerError(
                "Sealed stakeholder signal wrapper contains unsupported fields."
            )
        signal = _mapping(
            signal_wrapper.get("signal"),
            label="Sealed stakeholder signal",
        )
        signal_sha256 = str(signal_wrapper.get("signal_capsule_sha256") or "")
        signal_id = signal.get("signal_id")
        if (
            set(signal) != _FEEDBACK_SIGNAL_FIELDS
            or not isinstance(signal_id, str)
            or not signal_id
            or signal_id in signals_by_id
            or signal.get("route_scope") != feedback_capsule.get("route")
            or not _SHA256.fullmatch(signal_sha256)
            or signal_sha256 != _json_sha256(signal)
        ):
            raise StagedDesignWorkerBrokerError(
                "Sealed stakeholder signal is malformed, duplicated, or outside the route."
            )
        signals_by_id[signal_id] = dict(signal)
        signal_hashes[signal_id] = signal_sha256

    raw_feedback_responses = raw.get("feedback_response_manifest")
    if not isinstance(raw_feedback_responses, Mapping):
        raise StagedDesignWorkerBrokerError(
            "Worker submission needs a stakeholder feedback-response manifest keyed by signal id."
        )
    response_ids = {str(key) for key in raw_feedback_responses}
    if response_ids != set(signals_by_id):
        raise StagedDesignWorkerBrokerError(
            "Worker feedback responses must close every route signal exactly once and no others."
        )
    feedback_responses: dict[str, dict[str, Any]] = {}
    for signal_id in sorted(signals_by_id):
        signal = signals_by_id[signal_id]
        response = _mapping(
            raw_feedback_responses.get(signal_id),
            label=f"Worker feedback response '{signal_id}'",
        )
        if set(response) != _FEEDBACK_RESPONSE_FIELDS:
            raise StagedDesignWorkerBrokerError(
                f"Worker feedback response '{signal_id}' contains unsupported or free-form fields."
            )
        disposition = response.get("disposition")
        response_code = response.get("response_code")
        route_scope = response.get("route_scope")
        signal_capsule_sha256 = str(response.get("signal_capsule_sha256") or "")
        if (
            disposition != signal.get("disposition")
            or response_code not in RESPONSE_CODES
            or route_scope != signal.get("route_scope")
            or signal_capsule_sha256 != signal_hashes[signal_id]
        ):
            raise StagedDesignWorkerBrokerError(
                f"Worker feedback response '{signal_id}' does not bind its exact controlled signal."
            )
        raw_changed_paths = response.get("changed_paths")
        if not isinstance(raw_changed_paths, list) or not all(
            isinstance(item, str) and item.strip() for item in raw_changed_paths
        ):
            raise StagedDesignWorkerBrokerError(
                f"Worker feedback response '{signal_id}' changed_paths must be a string list."
            )
        changed_paths = [
            _safe_relative_path(
                item,
                label=f"Worker feedback response '{signal_id}' changed path",
            )
            for item in raw_changed_paths
        ]
        raw_response_claim_ids = response.get("claim_ids")
        if not isinstance(raw_response_claim_ids, list) or not all(
            isinstance(item, str) and item.strip() for item in raw_response_claim_ids
        ):
            raise StagedDesignWorkerBrokerError(
                f"Worker feedback response '{signal_id}' claim_ids must be a string list."
            )
        response_claim_ids = [str(item) for item in raw_response_claim_ids]
        signal_claim_ids = signal.get("claim_ids")
        if (
            not isinstance(signal_claim_ids, list)
            or len(changed_paths) != len(set(changed_paths))
            or len(response_claim_ids) != len(set(response_claim_ids))
            or not set(changed_paths).issubset(allowed)
            or not set(response_claim_ids).issubset({str(item) for item in signal_claim_ids})
        ):
            raise StagedDesignWorkerBrokerError(
                f"Worker feedback response '{signal_id}' exceeds its route or claim scope."
            )

        no_change = response_code in {"declined", "deferred", "unchanged"}
        if disposition == "no-action":
            allowed_response_codes = {"unchanged"}
        elif disposition == "action-requested":
            allowed_response_codes = {"addressed", "declined", "deferred"}
        else:
            allowed_response_codes = set(RESPONSE_CODES)
        if response_code not in allowed_response_codes:
            raise StagedDesignWorkerBrokerError(
                f"Worker feedback response '{signal_id}' is incompatible with its disposition."
            )
        if no_change and (changed_paths or response_claim_ids):
            raise StagedDesignWorkerBrokerError(
                f"Worker feedback response '{signal_id}' cannot declare changes for {response_code}."
            )
        if response_code == "addressed" and (
            not changed_paths or not response_claim_ids or not set(changed_paths).issubset(set(patch_paths))
        ):
            raise StagedDesignWorkerBrokerError(
                f"Addressed feedback response '{signal_id}' must bind actual patch paths and existing claim ids."
            )
        feedback_responses[signal_id] = {
            "disposition": disposition,
            "response_code": response_code,
            "route_scope": route_scope,
            "changed_paths": sorted(changed_paths),
            "claim_ids": sorted(response_claim_ids),
            "signal_capsule_sha256": signal_capsule_sha256,
        }

    return {
        "patch_manifest": patches,
        "claim_impact_manifest": impacts,
        "claim_surface_manifest": surfaces,
        "feedback_response_manifest": feedback_responses,
    }


def _snapshot_index(snapshot: Mapping[str, Any], *, label: str) -> dict[str, dict[str, Any]]:
    rows = snapshot.get("files")
    if not isinstance(rows, list):
        raise _StagedDesignWorkerManifestError(f"{label} does not contain a file manifest.")
    index: dict[str, dict[str, Any]] = {}
    for raw_row in rows:
        row = _mapping(raw_row, label=f"{label} file entry")
        path = _safe_relative_path(row.get("path"), label=f"{label} path")
        sha256 = str(row.get("sha256") or "")
        raw_bytes = row.get("bytes")
        if path in index or not _SHA256.fullmatch(sha256) or not isinstance(raw_bytes, int) or raw_bytes < 0:
            raise _StagedDesignWorkerManifestError(f"{label} contains an invalid file manifest entry.")
        index[path] = {"path": path, "sha256": sha256, "bytes": raw_bytes}
    return index


def _verify_post_adapter_manifest(
    *,
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    submission: Mapping[str, Any],
    sandbox: StagedDesignWorkerSandbox,
) -> None:
    """Require the adapter's exact write result to equal its sealed text manifest."""

    patches = submission.get("patch_manifest")
    if not isinstance(patches, list):
        raise _StagedDesignWorkerManifestError("Validated worker submission lost its patch manifest.")
    declared_paths = [str(_mapping(item, label="Worker patch")["path"]) for item in patches]
    if set(sandbox.written_paths) != set(declared_paths):
        raise _StagedDesignWorkerManifestError(
            "Registered adapter did not write exactly every sealed patch path."
        )
    before_index = _snapshot_index(before, label="Pre-execution candidate snapshot")
    after_index = _snapshot_index(after, label="Post-execution candidate snapshot")
    changed_paths = {
        path
        for path in set(before_index).union(after_index)
        if before_index.get(path) != after_index.get(path)
    }
    undeclared_paths = changed_paths.difference(declared_paths)
    if undeclared_paths:
        raise _StagedDesignWorkerManifestError(
            "Registered adapter changed a candidate path outside the sealed patch manifest."
        )
    for raw_patch in patches:
        patch = _mapping(raw_patch, label="Worker patch")
        path = str(patch["path"])
        content = patch.get("content")
        if not isinstance(content, str):
            raise _StagedDesignWorkerManifestError("Sealed worker patch content is no longer UTF-8 text.")
        expected_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest().upper()
        actual = after_index.get(path)
        if actual is None or actual.get("sha256") != expected_sha256:
            raise _StagedDesignWorkerManifestError(
                "Registered adapter result does not match the sealed UTF-8 patch content."
            )


def _manifest_patch_adapter(
    _context: RestrictedStagedDesignWorkerContext,
    submission: Mapping[str, Any],
    sandbox: StagedDesignWorkerSandbox,
) -> Mapping[str, Any]:
    """Apply only the prevalidated manifest through the constrained sandbox."""

    patches = submission.get("patch_manifest")
    if not isinstance(patches, list):
        raise StagedDesignWorkerBrokerError("Trusted manifest adapter received no validated patch manifest.")
    for patch in patches:
        item = _mapping(patch, label="Trusted adapter patch")
        sandbox.write_text(str(item["path"]), str(item["content"]))
    return {"written_paths": list(sandbox.written_paths)}


def trusted_adapter_ids() -> tuple[str, ...]:
    """Return the sole built-in declarative adapter; arbitrary code is never invoked."""

    return (DEFAULT_TRUSTED_ADAPTER_ID,)


def _trusted_adapter(
    adapter_id: str,
) -> Callable[
    [
        RestrictedStagedDesignWorkerContext,
        Mapping[str, Any],
        StagedDesignWorkerSandbox,
    ],
    Mapping[str, Any],
]:
    """Resolve only the built-in data applier, never a dynamic Python callback."""

    safe = _safe_adapter_id(adapter_id)
    if safe != DEFAULT_TRUSTED_ADAPTER_ID:
        raise StagedDesignWorkerBrokerError(
            "Requested adapter is not the built-in declarative staged-worker manifest applier."
        )
    return _manifest_patch_adapter


def _restricted_context(lease: Mapping[str, Any]) -> RestrictedStagedDesignWorkerContext:
    route = _mapping(lease.get("route"), label="Lease route binding")
    worker_context = _mapping(lease.get("worker_context"), label="Lease worker context")
    source_route = _mapping(worker_context.get("route"), label="Lease worker-context route")
    asset_requirement = _mapping(
        worker_context.get("asset_requirement"),
        label="Lease worker asset requirement",
    )
    editorial_authoring_contract = _editorial_authoring_binding(
        worker_context,
        route,
        assets_required=asset_requirement.get("required") is True,
    )
    investor_copy_repair = _investor_copy_worker_binding(
        worker_context,
        route,
    )
    directives = _mapping(lease.get("design_directives"), label="Lease sealed design directives")
    return RestrictedStagedDesignWorkerContext(
        lease_id=str(lease["lease_id"]),
        run_id=str(lease["run_id"]),
        adapter_id=str(lease["adapter_id"]),
        route_id=str(route["id"]),
        route=str(route["route"]),
        route_purpose=str(directives["route_purpose"]),
        content_order=tuple(str(item) for item in directives["content_order"]),
        allowed_paths=tuple(str(path) for path in route["allowed_paths"]),
        claim_capsule=_mapping(source_route.get("claim_capsule"), label="Lease claim capsule"),
        claim_capsule_sha256=str(route["claim_capsule_sha256"]),
        feedback_capsule=_mapping(
            source_route.get("feedback_capsule"),
            label="Lease stakeholder-feedback capsule",
        ),
        feedback_capsule_sha256=str(route["feedback_capsule_sha256"]),
        editorial_authoring_contract=editorial_authoring_contract,
        investor_copy_repair=investor_copy_repair,
        visual_rules=tuple(_mapping(item, label="Lease visual rule") for item in directives["visual_rules"]),
        acceptance_criteria=tuple(str(item) for item in directives["acceptance_criteria"]),
        prohibited_public_inferences=tuple(str(item) for item in directives["prohibited_public_inferences"]),
        work_order_sha256=str(_mapping(lease.get("work_order"), label="Lease work order")["sha256"]),
        worker_context_sha256=str(lease["worker_context_sha256"]),
        workspace_snapshot_sha256=str(
            _mapping(lease.get("workspace_snapshot"), label="Lease workspace snapshot")["tree_sha256"]
        ),
        prohibited_operations=(
            "canonical website mutation",
            "candidate promotion",
            "package creation",
            "backup",
            "owner gate",
            "deployment",
            "credential access",
            "binary asset read",
            "binary asset write",
            "binary asset import",
        ),
    )


def _lease_receipt(
    *,
    lease_id: str,
    run_id: str,
    adapter_id: str,
    binding: Mapping[str, Any],
    issued_at: datetime,
    ttl_seconds: int,
) -> dict[str, Any]:
    expires_at = issued_at + timedelta(seconds=ttl_seconds)
    core = {
        "schema": LEASE_SCHEMA,
        "state": "lease-issued",
        "lease_id": lease_id,
        "run_id": run_id,
        "adapter_id": adapter_id,
        "issued_at": _utc_iso(issued_at),
        "expires_at": _utc_iso(expires_at),
        "ttl_seconds": ttl_seconds,
        "worker_context_sha256": binding["worker_context_sha256"],
        "worker_context": binding["worker_context"],
        "work_order": binding["work_order"],
        "route": binding["route"],
        "design_directives": binding["design_directives"],
        "workspace_snapshot": binding["workspace_snapshot"],
        "authority": dict(AUTHORITY),
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "credential_access": "none",
    }
    core["integrity_sha256"] = _lease_integrity(core)
    return core


def issue_staged_design_worker_lease(
    run_id: str,
    *,
    adapter_id: str = DEFAULT_TRUSTED_ADAPTER_ID,
    ttl_seconds: int = DEFAULT_LEASE_TTL_SECONDS,
    repo_root: Path | None = None,
    now: datetime | None = None,
) -> tuple[dict[str, Any], Path]:
    """Issue one short-lived immutable lease for an untouched staged candidate only."""

    root = _find_repo_root(repo_root)
    safe_run_id = _safe_run_id(run_id)
    safe_adapter_id = _safe_adapter_id(adapter_id)
    _trusted_adapter(safe_adapter_id)
    if (
        not isinstance(ttl_seconds, int)
        or isinstance(ttl_seconds, bool)
        or not 1 <= ttl_seconds <= MAX_LEASE_TTL_SECONDS
    ):
        raise StagedDesignWorkerBrokerError(
            f"Lease TTL must be an integer from 1 to {MAX_LEASE_TTL_SECONDS} seconds."
        )
    issued_at = _utc_now(now)
    binding, candidate_root = _current_binding(root, safe_run_id, now=issued_at)
    _assert_no_prior_worker_activity(candidate_root)
    lease_id = f"lease-{uuid.uuid4().hex}"
    lease = _lease_receipt(
        lease_id=lease_id,
        run_id=safe_run_id,
        adapter_id=safe_adapter_id,
        binding=binding,
        issued_at=issued_at,
        ttl_seconds=ttl_seconds,
    )
    issuance = {
        "schema": ISSUANCE_SCHEMA,
        "state": "lease-issued",
        "issued_at": _utc_iso(issued_at),
        "run_id": safe_run_id,
        "lease_id": lease_id,
        "adapter_id": safe_adapter_id,
        "lease_integrity_sha256": lease["integrity_sha256"],
        "workspace_snapshot": binding["workspace_snapshot"],
        "authority": dict(AUTHORITY),
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "credential_access": "none",
    }
    _atomic_no_overwrite_json(candidate_root, _issuance_receipt_path(candidate_root), issuance)
    return lease, _atomic_no_overwrite_json(
        candidate_root, _receipt_path(candidate_root, "leases", lease_id), lease
    )


def _verify_lease(
    lease: Mapping[str, Any],
    *,
    run_id: str,
    adapter_id: str,
    binding: Mapping[str, Any],
    now: datetime,
) -> None:
    if lease.get("schema") != LEASE_SCHEMA or lease.get("state") != "lease-issued":
        raise StagedDesignWorkerBrokerError("Lease schema is not recognised.")
    _safe_lease_id(lease.get("lease_id"))
    if lease.get("integrity_sha256") != _lease_integrity(lease):
        raise StagedDesignWorkerBrokerError("Lease receipt integrity does not verify.")
    if (
        lease.get("run_id") != run_id
        or lease.get("adapter_id") != adapter_id
        or lease.get("authority") != AUTHORITY
        or lease.get("release_eligible") is not False
        or lease.get("package_authority") != "none"
        or lease.get("deployment_authority") != "none"
        or lease.get("credential_access") != "none"
    ):
        raise StagedDesignWorkerBrokerError(
            "Lease authority or requested adapter does not match its staged-only binding."
        )
    issued_at = _parse_utc(lease.get("issued_at"), label="Lease issued_at")
    expires_at = _parse_utc(lease.get("expires_at"), label="Lease expires_at")
    ttl_seconds = lease.get("ttl_seconds")
    if (
        not isinstance(ttl_seconds, int)
        or isinstance(ttl_seconds, bool)
        or not 1 <= ttl_seconds <= MAX_LEASE_TTL_SECONDS
        or expires_at != issued_at + timedelta(seconds=ttl_seconds)
        or now >= expires_at
    ):
        raise StagedDesignWorkerBrokerError(
            "Lease is expired, malformed, or exceeds the short-lived TTL policy."
        )
    if (
        lease.get("worker_context_sha256") != binding["worker_context_sha256"]
        or lease.get("worker_context") != binding["worker_context"]
        or lease.get("work_order") != binding["work_order"]
        or lease.get("route") != binding["route"]
        or lease.get("design_directives") != binding["design_directives"]
        or lease.get("workspace_snapshot") != binding["workspace_snapshot"]
    ):
        raise StagedDesignWorkerBrokerError(
            "Lease no longer binds the exact runner context, work order, route, or candidate workspace snapshot."
        )


def _verify_issuance_receipt(
    path: Path,
    lease: Mapping[str, Any],
    binding: Mapping[str, Any],
) -> None:
    issuance = _read_json(path, label="Worker lease issuance")
    if (
        issuance.get("schema") != ISSUANCE_SCHEMA
        or issuance.get("state") != "lease-issued"
        or issuance.get("run_id") != lease.get("run_id")
        or issuance.get("lease_id") != lease.get("lease_id")
        or issuance.get("adapter_id") != lease.get("adapter_id")
        or issuance.get("lease_integrity_sha256") != lease.get("integrity_sha256")
        or issuance.get("workspace_snapshot") != binding.get("workspace_snapshot")
        or issuance.get("authority") != AUTHORITY
        or issuance.get("release_eligible") is not False
        or issuance.get("package_authority") != "none"
        or issuance.get("deployment_authority") != "none"
        or issuance.get("credential_access") != "none"
    ):
        raise StagedDesignWorkerBrokerError(
            "Lease issuance receipt no longer binds the exact staged worker lease."
        )


def _outcome(
    *,
    state: str,
    lease: Mapping[str, Any],
    execution_path: Path,
    root: Path,
    submission: Mapping[str, Any],
    pre_execution_snapshot: Mapping[str, Any],
    post_execution_snapshot: Mapping[str, Any] | None,
    candidate_outcome: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": OUTCOME_SCHEMA,
        "recorded_at": _utc_iso(),
        "state": state,
        "run_id": lease["run_id"],
        "lease_id": lease["lease_id"],
        "adapter_id": lease["adapter_id"],
        "lease_integrity_sha256": lease["integrity_sha256"],
        "execution_receipt": {
            "path": _relative_to_repo(root, execution_path),
            "sha256": _sha256_file(execution_path),
        },
        "submission_sha256": _json_sha256(submission),
        "feedback_response_manifest": dict(submission["feedback_response_manifest"]),
        "feedback_response_manifest_sha256": _json_sha256(submission["feedback_response_manifest"]),
        "manifest_summary": {
            "patch_paths": [entry["path"] for entry in submission["patch_manifest"]],
            "claim_impact_paths": [entry["path"] for entry in submission["claim_impact_manifest"]],
            "claim_surface_count": len(submission["claim_surface_manifest"]),
            "claim_surface_paths": [entry["path"] for entry in submission["claim_surface_manifest"]],
            "feedback_signal_ids": sorted(submission["feedback_response_manifest"]),
            "feedback_addressed_signal_ids": sorted(
                signal_id
                for signal_id, response in submission["feedback_response_manifest"].items()
                if response["response_code"] == "addressed"
            ),
        },
        "pre_execution_workspace_snapshot": dict(pre_execution_snapshot),
        "post_execution_workspace_snapshot": dict(post_execution_snapshot or {}),
        "candidate_outcome": dict(candidate_outcome),
        "authority": dict(AUTHORITY),
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "credential_access": "none",
    }


def submit_staged_design_worker_delivery(
    run_id: str,
    lease_id: str,
    *,
    adapter_id: str,
    submission: Mapping[str, Any],
    repo_root: Path | None = None,
    now: datetime | None = None,
) -> tuple[dict[str, Any], Path]:
    """Consume one valid lease, run one restricted adapter, and validate once through the runner."""

    root = _find_repo_root(repo_root)
    safe_run_id = _safe_run_id(run_id)
    safe_lease_id = _safe_lease_id(lease_id)
    safe_adapter_id = _safe_adapter_id(adapter_id)
    adapter = _trusted_adapter(safe_adapter_id)
    submitted_at = _utc_now(now)
    prior_candidate_root = _candidate_root_for_run(root, safe_run_id)
    prior_execution_path = _receipt_path(prior_candidate_root, "executions", safe_lease_id)
    prior_outcome_path = _receipt_path(prior_candidate_root, "outcomes", safe_lease_id)
    if prior_execution_path.exists() or prior_outcome_path.exists():
        raise StagedDesignWorkerBrokerError(
            "This lease has already been consumed; issue a new staged candidate run."
        )
    binding, candidate_root = _current_binding(root, safe_run_id, now=submitted_at)
    if candidate_root != prior_candidate_root:
        raise StagedDesignWorkerBrokerError(
            "Staged candidate root changed before the worker lease could execute."
        )
    lease_path = _receipt_path(candidate_root, "leases", safe_lease_id)
    lease = _read_json(lease_path, label="Worker lease")
    _verify_lease(
        lease,
        run_id=safe_run_id,
        adapter_id=safe_adapter_id,
        binding=binding,
        now=submitted_at,
    )
    _verify_issuance_receipt(_issuance_receipt_path(candidate_root), lease, binding)
    lease_worker_context = _mapping(
        lease.get("worker_context"),
        label="Lease worker context",
    )
    lease_worker_route = _mapping(
        lease_worker_context.get("route"),
        label="Lease worker route",
    )
    normalised_submission = _normalise_submission(
        submission,
        allowed_paths=_mapping(lease.get("route"), label="Lease route binding")["allowed_paths"],
        feedback_capsule=_mapping(
            lease_worker_route.get("feedback_capsule"),
            label="Lease stakeholder-feedback capsule",
        ),
        feedback_capsule_sha256=str(lease_worker_route.get("feedback_capsule_sha256") or ""),
    )

    execution_path = _receipt_path(candidate_root, "executions", safe_lease_id)
    outcome_path = _receipt_path(candidate_root, "outcomes", safe_lease_id)
    if execution_path.exists() or outcome_path.exists():
        raise StagedDesignWorkerBrokerError(
            "This lease has already been consumed; issue a new staged candidate run."
        )
    execution = {
        "schema": EXECUTION_SCHEMA,
        "state": "execution-claimed",
        "claimed_at": _utc_iso(submitted_at),
        "run_id": safe_run_id,
        "lease_id": safe_lease_id,
        "adapter_id": safe_adapter_id,
        "lease_integrity_sha256": lease["integrity_sha256"],
        "submission_sha256": _json_sha256(normalised_submission),
        "pre_execution_workspace_snapshot": binding["workspace_snapshot"],
        "authority": dict(AUTHORITY),
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "credential_access": "none",
    }
    execution_path = _atomic_no_overwrite_json(candidate_root, execution_path, execution)

    restricted_context = _restricted_context(lease)
    sandbox = StagedDesignWorkerSandbox(
        root / str(binding["workspace_snapshot"]["candidate_website"]),
        [entry["path"] for entry in normalised_submission["patch_manifest"]],
        repo_root=root,
    )
    try:
        adapter_result = adapter(restricted_context, normalised_submission, sandbox)
        if adapter_result is not None and not isinstance(adapter_result, Mapping):
            raise StagedDesignWorkerBrokerError("Trusted staged-worker adapter returned an invalid result.")
        _, post_execution_snapshot = _candidate_workspace_snapshot(
            root,
            runner.load_latest_delivery_job(safe_run_id, repo_root=root)[0],
            binding["worker_context"],
        )
        _verify_post_adapter_manifest(
            before=binding["workspace_snapshot"],
            after=post_execution_snapshot,
            submission=normalised_submission,
            sandbox=sandbox,
        )
    except Exception as exc:  # A trusted adapter failure is recorded, never retried on this lease.
        try:
            _, failure_snapshot = _candidate_workspace_snapshot(
                root,
                runner.load_latest_delivery_job(safe_run_id, repo_root=root)[0],
                binding["worker_context"],
            )
        except (StagedDesignWorkerBrokerError, runner.PublicWebsiteDesignRunnerError):
            failure_snapshot = None
        outcome = _outcome(
            state=(
                "adapter-manifest-rejected"
                if isinstance(exc, _StagedDesignWorkerManifestError)
                else "adapter-failed"
            ),
            lease=lease,
            execution_path=execution_path,
            root=root,
            submission=normalised_submission,
            pre_execution_snapshot=binding["workspace_snapshot"],
            post_execution_snapshot=failure_snapshot,
            candidate_outcome={
                "state": (
                    "adapter-manifest-rejected"
                    if isinstance(exc, _StagedDesignWorkerManifestError)
                    else "adapter-failed"
                ),
                "error_type": type(exc).__name__,
            },
        )
        return outcome, _atomic_no_overwrite_json(candidate_root, outcome_path, outcome)

    try:
        validated_job, validation_path = runner.validate_design_delivery_job(
            safe_run_id,
            claim_impacts=normalised_submission["claim_impact_manifest"],
            claim_surface_manifest=normalised_submission["claim_surface_manifest"],
            repo_root=root,
            now=submitted_at,
        )
        candidate_outcome = {
            "state": validated_job["state"],
            "candidate_validation": dict(
                _mapping(validated_job.get("candidate_validation"), label="Runner candidate validation")
            ),
            "validation_receipt": _relative_to_repo(root, validation_path),
            "next_required_stage": str(validated_job.get("next_required_stage") or ""),
        }
        if validated_job.get("investor_copy_evaluation") is not None:
            candidate_outcome["investor_copy_evaluation"] = dict(
                _mapping(
                    validated_job.get("investor_copy_evaluation"),
                    label="Runner investor-copy evaluation",
                )
            )
        outcome_state = str(validated_job["state"])
    except runner.PublicWebsiteDesignRunnerError as exc:
        candidate_outcome = {"state": "validation-error", "error_type": type(exc).__name__}
        outcome_state = "validation-error"
    outcome = _outcome(
        state=outcome_state,
        lease=lease,
        execution_path=execution_path,
        root=root,
        submission=normalised_submission,
        pre_execution_snapshot=binding["workspace_snapshot"],
        post_execution_snapshot=post_execution_snapshot,
        candidate_outcome=candidate_outcome,
    )
    return outcome, _atomic_no_overwrite_json(candidate_root, outcome_path, outcome)
