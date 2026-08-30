"""Trusted, hash-bound test evidence for one staged website candidate.

This control closes a narrow trust gap: a staged worker may request an exact
test suite, but it may not choose a command, add arguments or environment
variables, interpret output, or declare that it passed.  An operator pins a
strict JSON policy by exact file-byte SHA-256.  This module then runs the complete
ordered allowlist once, without a shell, below the staged candidate website.

Only hashes and byte counts of stdout/stderr are retained.  The Python control
itself does not initiate network access and supplies a sanitised, offline-intent
environment.  It is not a kernel network or filesystem sandbox: exact
canonical-site and scoped repository-control surfaces are compared before and
after so mutation is detected, not prevented.  The receipt grants no candidate
validation, promotion, package, release, or deployment authority.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Final, Mapping, Sequence

from aureon.operator import secure_immutable_artifact

POLICY_SCHEMA = "aureon.design-candidate-test-policy.v1"
RECEIPT_SCHEMA = "aureon.design-candidate-test-evidence.v2"
VERIFICATION_SCHEMA = "aureon.design-candidate-test-evidence-verification.v2"
CANDIDATE_SCHEMA = "aureon.design-candidate.v1"
MODULE_PATH = "aureon/operator/design_candidate_test_evidence.py"
SECURE_WRITER_PATH = "aureon/operator/secure_immutable_artifact.py"

POLICY_AUTHORITY = {
    "scope": "exact local staged-candidate test command allowlist",
    "canonical_website_mutation": "none",
    "candidate_validation_authority": "none",
    "promotion_authority": "none",
    "package_authority": "none",
    "release_authority": "none",
    "deployment_authority": "none",
    "credential_access": "none",
}

EVIDENCE_AUTHORITY = {
    "scope": "hash-bound local staged-candidate test observations only",
    "canonical_website_mutation": "none",
    "candidate_validation_authority": "none",
    "promotion_authority": "none",
    "package_authority": "none",
    "release_authority": "none",
    "deployment_authority": "none",
    "credential_access": "none",
}

CANDIDATE_NON_AUTHORITATIVE_AUTHORITY = {
    "scope": "local staged website-candidate provenance and diff control",
    "canonical_website_mutation": "never by this control or a design agent",
    "release_eligible": False,
    "package_authority": "none",
    "deployment_authority": "none",
    "credential_access": "none",
    "human_visual_acceptance": "required for material brand changes",
    "release_authority": "WebsiteOperator owner gate only",
}

LOCAL_EXECUTION_BOUNDARY = {
    "intent": "offline local execution of operator-reviewed hash-pinned tools",
    "enforcement": "sanitised environment and null-route proxy settings",
    "os_network_sandbox": False,
    "filesystem_sandbox": False,
    "output_capture_boundary": (
        "temporary-file size polling at 2 MiB per stream with a final size check; not an OS disk quota"
    ),
    "residual_risk": (
        "Detection, not prevention: a reviewed tool can bypass proxy settings with raw sockets "
        "or write outside the candidate; pinned canonical and repository-control surfaces are "
        "checked at pre/post endpoints. An equally privileged same-user process can mutate, run, "
        "and restore bytes between endpoint observations, or write after the post endpoint. "
        "Without OS isolation this is not prevented and these receipts are not origin attestation."
    ),
}

SUPPORTED_ENGINES = frozenset(
    {
        "python",
        "node",
        "playwright-chromium",
        "playwright-firefox",
        "playwright-webkit",
    }
)
SUPPORTED_VIEWPORT_WIDTHS = frozenset({320, 360, 390, 768, 1280, 1440, 1920})
PROCESS_OUTPUTS = ("exit-code", "stdout-sha256", "stderr-sha256")
MAX_POLICY_BYTES = 2 * 1024 * 1024
MAX_COMMANDS = 32
MAX_ARGUMENTS = 64
MAX_ARGUMENT_LENGTH = 4096
MAX_TIMEOUT_SECONDS = 900
MAX_STREAM_BYTES = 2 * 1024 * 1024

# This is deliberately a source-reviewed, machine-specific trust anchor rather
# than a discovery hint.  PATH, PATHEXT, registry aliases, package-manager
# shims, and caller-provided paths are never consulted.  A Node relocation or
# upgrade therefore fails closed until this binding is reviewed and updated.
NODE_TOOLCHAIN_BINDING: Final[dict[str, object]] = {
    "absolute_path": "C:/Program Files/nodejs/node.exe",
    "locator_authority": "reviewed-source-pinned-absolute-path-no-path-fallback",
    "platform": "win32",
    "schema": "aureon.node-toolchain-binding.v1",
    "sha256": "63C259C81E5D472B5F11C8D506070130CB04A1ECF84B80377A34ED6EC9048088",
    "size_bytes": 91_380_224,
    "version": "v24.14.0",
}
NODE_TOOLCHAIN_BINDING_SHA256 = "3C866F4735B8FD73CF5EA131B2419BCF7FD5DF2FC0710C151132067A5233CBEB"

_SHA256 = re.compile(r"[A-F0-9]{64}")
_IDENTIFIER = re.compile(r"[a-z0-9][a-z0-9._-]{2,126}")
_ENV_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
_FORBIDDEN_EVAL_ARGUMENTS = frozenset(
    {
        "-c",
        "-e",
        "--eval",
        "--print",
        "/c",
        "/k",
        "-command",
        "-encodedcommand",
    }
)
_FORBIDDEN_ARGUMENT_FRAGMENTS = (
    "\x00",
    "\r",
    "\n",
    "://",
    "file:",
    "\\\\",
    "$(",
    "`",
    "|",
    "&&",
    "||",
    ">",
    "<",
)
_ALLOWLIST_INHERITED_ENV_KEYS = (
    "COMSPEC",
    "LOCALAPPDATA",
    "PATHEXT",
    "PROGRAMFILES",
    "PROGRAMFILES(X86)",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "WINDIR",
)
_POLICY_FIELDS = frozenset(
    {
        "schema",
        "policy_id",
        "candidate",
        "repository_control",
        "required_command_ids",
        "commands",
        "execution",
        "authority",
    }
)
_POLICY_CANDIDATE_FIELDS = frozenset(
    {
        "receipt_path",
        "receipt_file_sha256",
        "receipt_json_sha256",
        "tree_sha256",
    }
)
_POLICY_EXECUTION_FIELDS = frozenset(
    {
        "mode",
        "shell",
        "inherit_environment",
        "network",
        "output_privacy",
        "preserve_failures",
        "retry_count",
    }
)
_POLICY_EXECUTION = {
    "mode": "ordered-once-fail-fast",
    "shell": False,
    "inherit_environment": False,
    "network": "offline-intent-no-kernel-network-sandbox",
    "output_privacy": "sha256-only",
    "preserve_failures": True,
    "retry_count": 0,
}
_REPOSITORY_CONTROL_FIELDS = frozenset(
    {
        "canonical_website_path",
        "canonical_website_tree_sha256",
        "entries",
        "manifest_sha256",
    }
)
_REPOSITORY_CONTROL_ENTRY_FIELDS = frozenset({"path", "kind", "sha256"})
_COMMAND_FIELDS = frozenset(
    {
        "id",
        "template",
        "template_sha256",
    }
)
_TEMPLATE_FIELDS = frozenset(
    {
        "engine",
        "argv",
        "cwd",
        "timeout_seconds",
        "viewport_widths",
        "trusted_inputs",
        "tool_executable_sha256",
        "required_outputs",
    }
)
_TRUSTED_INPUT_FIELDS = frozenset({"path", "sha256"})
_RECEIPT_FIELDS = frozenset(
    {
        "schema",
        "receipt_id",
        "created_at",
        "state",
        "passed",
        "local_execution",
        "implementation",
        "policy",
        "candidate",
        "selection",
        "executions",
        "authority",
        "receipt_payload_sha256",
    }
)
_IMPLEMENTATION_FIELDS = frozenset(
    {
        "candidate_test_evidence_path",
        "candidate_test_evidence_sha256",
        "secure_immutable_artifact_path",
        "secure_immutable_artifact_sha256",
    }
)
_RECEIPT_POLICY_FIELDS = frozenset(
    {
        "path",
        "file_sha256",
        "json_sha256",
        "policy_id",
    }
)
_RECEIPT_CANDIDATE_FIELDS = frozenset(
    {
        "receipt_path",
        "receipt_file_sha256",
        "receipt_json_sha256",
        "root",
        "website_path",
        "tree_sha256",
        "file_count",
        "total_bytes",
    }
)
_SELECTION_FIELDS = frozenset({"command_ids", "command_ids_sha256", "count"})
_EXECUTION_FIELDS = frozenset(
    {
        "ordinal",
        "command_id",
        "template_sha256",
        "engine",
        "viewport_widths",
        "argv_sha256",
        "cwd",
        "environment",
        "trusted_inputs_sha256",
        "tool",
        "started_at",
        "ended_at",
        "duration_ms",
        "attempt",
        "retry_count",
        "state",
        "passed",
        "exit_code",
        "timed_out",
        "output_limit_exceeded",
        "outputs",
        "integrity",
    }
)
_ENVIRONMENT_FIELDS = frozenset(
    {
        "mode",
        "inherited",
        "network",
        "keys",
        "keys_sha256",
        "values_sha256",
    }
)
_TOOL_FIELDS = frozenset(
    {
        "executable_file_sha256",
        "executable_path_sha256",
        "version_argv_sha256",
        "version_exit_code",
        "version_output_limit_exceeded",
        "version_stdout",
        "version_stderr",
    }
)
_OUTPUTS_FIELDS = frozenset({"exit-code", "stdout-sha256", "stderr-sha256"})
_STREAM_FIELDS = frozenset({"present", "sha256", "bytes", "retained"})
_EXIT_OUTPUT_FIELDS = frozenset({"present", "value"})
_INTEGRITY_FIELDS = frozenset(
    {
        "candidate_tree_before",
        "candidate_tree_after",
        "policy_file_before",
        "policy_file_after",
        "candidate_receipt_file_before",
        "candidate_receipt_file_after",
        "trusted_inputs_before",
        "trusted_inputs_after",
        "canonical_website_before",
        "canonical_website_after",
        "repository_control_before",
        "repository_control_after",
        "tool_executable_before",
        "tool_executable_after",
        "evidence_implementation_before",
        "evidence_implementation_after",
        "secure_writer_implementation_before",
        "secure_writer_implementation_after",
        "endpoint_consistent",
    }
)
_LOADED_SOURCE_SHA256: Final = hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()
_LOADED_SECURE_WRITER_SHA256: Final = (
    hashlib.sha256(Path(str(secure_immutable_artifact.__file__)).read_bytes()).hexdigest().upper()
)
_ISSUED_RECEIPT_PAYLOAD_HASHES: set[str] = set()
_ISSUED_RECEIPT_LOCK = threading.Lock()


class DesignCandidateTestEvidenceError(ValueError):
    """A test policy, staged tree, command, or receipt is unsafe or stale."""


@dataclass(frozen=True)
class _StreamObservation:
    sha256: str
    byte_count: int


def _utc_iso(value: datetime | None = None) -> str:
    return (value or datetime.now(UTC)).astimezone(UTC).isoformat().replace("+00:00", "Z")


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _json_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest().upper()


def _bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise DesignCandidateTestEvidenceError(f"Duplicate JSON key is forbidden: {key}")
        value[key] = item
    return value


def _reject_json_constant(value: str) -> None:
    raise DesignCandidateTestEvidenceError(f"Non-finite JSON number is forbidden: {value}")


def _load_json_file(path: Path, *, label: str) -> tuple[dict[str, Any], bytes]:
    safe_path = _regular_file(path, label=label, single_link=True)
    raw = safe_path.read_bytes()
    if len(raw) > MAX_POLICY_BYTES:
        raise DesignCandidateTestEvidenceError(f"{label} exceeds the {MAX_POLICY_BYTES}-byte limit.")
    try:
        decoded = raw.decode("utf-8-sig")
        parsed = json.loads(
            decoded,
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DesignCandidateTestEvidenceError(f"{label} is not strict UTF-8 JSON.") from exc
    if not isinstance(parsed, dict):
        raise DesignCandidateTestEvidenceError(f"{label} must be one JSON object.")
    return parsed, raw


def _find_repo_root(start: Path | None = None) -> Path:
    candidate = Path(os.path.abspath(start or Path.cwd()))
    for root in (candidate, *candidate.parents):
        if (root / "pyproject.toml").is_file() and (root / "aureon").is_dir():
            return root
    raise DesignCandidateTestEvidenceError(
        "Could not locate an Aureon repository with pyproject.toml and aureon/."
    )


def _is_link_or_reparse(path: Path) -> bool:
    try:
        details = path.lstat()
    except OSError as exc:
        raise DesignCandidateTestEvidenceError(f"Path could not be inspected safely: {path}") from exc
    if stat.S_ISLNK(details.st_mode):
        return True
    attributes = getattr(details, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_flag)


def _inspect_existing_ancestry(path: Path, *, label: str) -> None:
    lexical = Path(os.path.abspath(path))
    for component in (lexical, *lexical.parents):
        if not component.exists() and not component.is_symlink():
            continue
        if _is_link_or_reparse(component):
            raise DesignCandidateTestEvidenceError(
                f"{label} may not traverse a symbolic link or reparse point."
            )


def _regular_file(path: Path, *, label: str, single_link: bool) -> Path:
    lexical = Path(os.path.abspath(path))
    try:
        secure_immutable_artifact.validate_no_alternate_stream_path(lexical, label=label)
    except secure_immutable_artifact.SecureImmutableArtifactError as exc:
        raise DesignCandidateTestEvidenceError(str(exc)) from exc
    _inspect_existing_ancestry(lexical, label=label)
    try:
        details = lexical.lstat()
    except OSError as exc:
        raise DesignCandidateTestEvidenceError(f"{label} must be an existing regular file.") from exc
    if not stat.S_ISREG(details.st_mode):
        raise DesignCandidateTestEvidenceError(f"{label} must be an existing regular file.")
    if single_link and int(details.st_nlink) != 1:
        raise DesignCandidateTestEvidenceError(f"{label} must have exactly one hard link.")
    return lexical


def _assert_loaded_source_current() -> dict[str, str]:
    current = _regular_file(
        Path(__file__),
        label="Loaded candidate test-evidence module",
        single_link=True,
    )
    evidence_sha256 = _sha256_file(current)
    if evidence_sha256 != _LOADED_SOURCE_SHA256:
        raise DesignCandidateTestEvidenceError(
            "Loaded candidate test-evidence module bytes do not match its current source file."
        )
    secure_writer = _regular_file(
        Path(str(secure_immutable_artifact.__file__)),
        label="Loaded immutable-artifact writer",
        single_link=True,
    )
    writer_sha256 = _sha256_file(secure_writer)
    if writer_sha256 != _LOADED_SECURE_WRITER_SHA256:
        raise DesignCandidateTestEvidenceError(
            "Loaded immutable-artifact writer bytes do not match its current source file."
        )
    return {
        "candidate_test_evidence_path": MODULE_PATH,
        "candidate_test_evidence_sha256": evidence_sha256,
        "secure_immutable_artifact_path": SECURE_WRITER_PATH,
        "secure_immutable_artifact_sha256": writer_sha256,
    }


def _regular_directory(path: Path, *, label: str) -> Path:
    lexical = Path(os.path.abspath(path))
    try:
        secure_immutable_artifact.validate_no_alternate_stream_path(lexical, label=label)
    except secure_immutable_artifact.SecureImmutableArtifactError as exc:
        raise DesignCandidateTestEvidenceError(str(exc)) from exc
    _inspect_existing_ancestry(lexical, label=label)
    try:
        details = lexical.lstat()
    except OSError as exc:
        raise DesignCandidateTestEvidenceError(f"{label} must be an existing regular directory.") from exc
    if not stat.S_ISDIR(details.st_mode):
        raise DesignCandidateTestEvidenceError(f"{label} must be an existing regular directory.")
    return lexical


def _safe_relative_path(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise DesignCandidateTestEvidenceError(f"{label} must be a canonical relative path.")
    if "\\" in value or value.startswith("/") or ":" in value:
        raise DesignCandidateTestEvidenceError(f"{label} must use a safe POSIX relative path.")
    path = Path(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise DesignCandidateTestEvidenceError(f"{label} escapes its allowed root.")
    return path.as_posix()


def _resolve_under(root: Path, value: object, *, label: str, directory: bool = False) -> Path:
    relative = _safe_relative_path(value, label=label)
    lexical_root = _regular_directory(root, label=f"{label} root")
    lexical = Path(os.path.abspath(lexical_root / relative))
    try:
        lexical.relative_to(lexical_root)
    except ValueError as exc:
        raise DesignCandidateTestEvidenceError(f"{label} escapes its allowed root.") from exc
    return (
        _regular_directory(lexical, label=label)
        if directory
        else _regular_file(lexical, label=label, single_link=True)
    )


def _relative_to_repo(root: Path, path: Path) -> str:
    try:
        return Path(os.path.abspath(path)).relative_to(root).as_posix()
    except ValueError as exc:
        raise DesignCandidateTestEvidenceError("A bound path escapes the repository.") from exc


def _tree_manifest(root: Path) -> list[dict[str, Any]]:
    lexical_root = _regular_directory(root, label="Candidate website")
    real_root = lexical_root.resolve(strict=True)
    directories = [lexical_root]
    files: list[Path] = []
    while directories:
        directory = directories.pop()
        try:
            entries = sorted(os.scandir(directory), key=lambda item: item.name)
        except OSError as exc:
            raise DesignCandidateTestEvidenceError(
                f"Candidate website cannot be enumerated safely: {directory}"
            ) from exc
        for entry in entries:
            path = Path(entry.path)
            if _is_link_or_reparse(path):
                raise DesignCandidateTestEvidenceError(
                    f"Candidate website contains a link or reparse point: {path}"
                )
            try:
                path.resolve(strict=True).relative_to(real_root)
                details = path.lstat()
            except (OSError, ValueError) as exc:
                raise DesignCandidateTestEvidenceError(
                    f"Candidate website path escapes its real root: {path}"
                ) from exc
            if stat.S_ISDIR(details.st_mode):
                directories.append(path)
            elif stat.S_ISREG(details.st_mode):
                if int(details.st_nlink) != 1:
                    raise DesignCandidateTestEvidenceError(
                        f"Candidate website files must have exactly one hard link: {path}"
                    )
                files.append(path)
            else:
                raise DesignCandidateTestEvidenceError(
                    f"Candidate website contains a non-regular entry: {path}"
                )
    rows = [
        {
            "path": path.relative_to(lexical_root).as_posix(),
            "sha256": _sha256_file(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(files, key=lambda item: item.relative_to(lexical_root).as_posix())
    ]
    return rows


def _tree_summary(root: Path) -> dict[str, Any]:
    rows = _tree_manifest(root)
    return {
        "tree_sha256": _json_sha256(rows),
        "file_count": len(rows),
        "total_bytes": sum(int(row["bytes"]) for row in rows),
    }


def _require_exact_fields(value: Mapping[str, Any], expected: frozenset[str], *, label: str) -> None:
    actual = frozenset(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise DesignCandidateTestEvidenceError(
            f"{label} fields are not exact (missing={missing}, extra={extra})."
        )


def _require_sha256(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise DesignCandidateTestEvidenceError(f"{label} must be an uppercase SHA-256.")
    return value


def _require_identifier(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise DesignCandidateTestEvidenceError(f"{label} must be a stable lowercase identifier.")
    return value


def _candidate_authority_is_safe(receipt: Mapping[str, Any]) -> bool:
    authority = receipt.get("authority")
    return (
        isinstance(authority, Mapping)
        and receipt.get("release_eligible") is False
        and receipt.get("deployment_authority") == "none"
        and dict(authority) == CANDIDATE_NON_AUTHORITATIVE_AUTHORITY
    )


def _load_bound_candidate(
    root: Path,
    policy_candidate: Mapping[str, Any],
) -> tuple[dict[str, Any], Path, Path, Path, dict[str, Any], bytes]:
    _require_exact_fields(
        policy_candidate,
        _POLICY_CANDIDATE_FIELDS,
        label="Policy candidate binding",
    )
    receipt_path = _resolve_under(
        root,
        policy_candidate.get("receipt_path"),
        label="Candidate receipt",
    )
    candidate_receipt, candidate_raw = _load_json_file(
        receipt_path,
        label="Candidate receipt",
    )
    if candidate_receipt.get("schema") != CANDIDATE_SCHEMA:
        raise DesignCandidateTestEvidenceError("Candidate receipt schema is unsupported.")
    if candidate_receipt.get("state") != "validated-local" or candidate_receipt.get("passed") is not True:
        raise DesignCandidateTestEvidenceError(
            "Candidate receipt must be a boolean-passed validated-local receipt."
        )
    if not _candidate_authority_is_safe(candidate_receipt):
        raise DesignCandidateTestEvidenceError(
            "Candidate receipt smuggles authority beyond local staged validation."
        )
    candidate = candidate_receipt.get("candidate")
    if not isinstance(candidate, Mapping):
        raise DesignCandidateTestEvidenceError("Candidate receipt lacks its candidate binding.")
    candidate_root = _resolve_under(
        root,
        candidate.get("root"),
        label="Staged candidate root",
        directory=True,
    )
    website_root = _resolve_under(
        root,
        candidate.get("website_path"),
        label="Staged candidate website",
        directory=True,
    )
    try:
        website_root.relative_to(candidate_root)
        receipt_path.relative_to(candidate_root)
    except ValueError as exc:
        raise DesignCandidateTestEvidenceError(
            "Candidate website and receipt must stay below one staged candidate root."
        ) from exc
    summary = _tree_summary(website_root)
    receipt_file_hash = _bytes_sha256(candidate_raw)
    receipt_json_hash = _json_sha256(candidate_receipt)
    expected_file = _require_sha256(
        policy_candidate.get("receipt_file_sha256"),
        label="Candidate receipt file hash",
    )
    expected_json = _require_sha256(
        policy_candidate.get("receipt_json_sha256"),
        label="Candidate receipt JSON hash",
    )
    expected_tree = _require_sha256(
        policy_candidate.get("tree_sha256"),
        label="Candidate tree hash",
    )
    receipt_tree = _require_sha256(
        candidate.get("tree_sha256"),
        label="Candidate receipt tree hash",
    )
    if (
        receipt_file_hash != expected_file
        or receipt_json_hash != expected_json
        or summary["tree_sha256"] != expected_tree
        or receipt_tree != expected_tree
        or candidate.get("file_count") != summary["file_count"]
        or candidate.get("total_bytes") != summary["total_bytes"]
    ):
        raise DesignCandidateTestEvidenceError(
            "Candidate receipt or staged tree is stale or does not match the pinned policy."
        )
    return (
        candidate_receipt,
        receipt_path,
        candidate_root,
        website_root,
        summary,
        candidate_raw,
    )


def _resolve_reviewed_node_toolchain() -> Path:
    """Resolve only the reviewed Node bytes; ambient discovery is forbidden."""

    binding = NODE_TOOLCHAIN_BINDING
    if _json_sha256(binding) != NODE_TOOLCHAIN_BINDING_SHA256:
        raise DesignCandidateTestEvidenceError(
            "Reviewed Node toolchain binding changed without updating its source-pinned hash."
        )
    if binding.get("platform") != sys.platform:
        raise DesignCandidateTestEvidenceError(
            f"No reviewed Node toolchain binding exists for platform {sys.platform!r}."
        )
    raw_path = binding.get("absolute_path")
    expected_size = binding.get("size_bytes")
    expected_sha256 = binding.get("sha256")
    if (
        not isinstance(raw_path, str)
        or not Path(raw_path).is_absolute()
        or not isinstance(expected_size, int)
        or isinstance(expected_size, bool)
        or expected_size < 1
        or not isinstance(expected_sha256, str)
        or _SHA256.fullmatch(expected_sha256) is None
    ):
        raise DesignCandidateTestEvidenceError("Reviewed Node toolchain binding is malformed.")
    executable = _regular_file(
        Path(raw_path),
        label="reviewed Node executable",
        single_link=False,
    )
    try:
        observed_size = executable.stat().st_size
    except OSError as exc:
        raise DesignCandidateTestEvidenceError(
            "Reviewed Node executable could not be measured safely."
        ) from exc
    if observed_size != expected_size or _sha256_file(executable) != expected_sha256:
        raise DesignCandidateTestEvidenceError(
            "Reviewed Node executable does not match its source-pinned size and SHA-256."
        )
    return executable


def _resolve_tool(engine: str) -> tuple[Path, str]:
    if engine == "python":
        executable = _regular_file(
            Path(sys.executable),
            label="python executable",
            single_link=False,
        )
        return executable, "{python}"
    return _resolve_reviewed_node_toolchain(), "{node}"


def _trusted_inputs(
    root: Path,
    candidate_root: Path,
    raw_inputs: object,
) -> tuple[list[dict[str, str]], dict[str, Path]]:
    if not isinstance(raw_inputs, list) or not raw_inputs:
        raise DesignCandidateTestEvidenceError(
            "Every command template must bind at least one trusted operator tool."
        )
    rows: list[dict[str, str]] = []
    paths: dict[str, Path] = {}
    for index, raw in enumerate(raw_inputs):
        if not isinstance(raw, Mapping):
            raise DesignCandidateTestEvidenceError(f"Trusted input {index} must be one exact object.")
        _require_exact_fields(raw, _TRUSTED_INPUT_FIELDS, label=f"Trusted input {index}")
        relative = _safe_relative_path(raw.get("path"), label=f"Trusted input {index} path")
        if relative in paths:
            raise DesignCandidateTestEvidenceError(f"Trusted input path is duplicated: {relative}")
        path = _resolve_under(root, relative, label=f"Trusted input {relative}")
        try:
            path.relative_to(candidate_root)
        except ValueError:
            pass
        else:
            raise DesignCandidateTestEvidenceError(
                "Trusted operator tools must not be sourced from the staged candidate."
            )
        expected = _require_sha256(raw.get("sha256"), label=f"Trusted input {relative} hash")
        if _sha256_file(path) != expected:
            raise DesignCandidateTestEvidenceError(f"Trusted input changed: {relative}")
        rows.append({"path": relative, "sha256": expected})
        paths[relative] = path
    if rows != sorted(rows, key=lambda item: item["path"]):
        raise DesignCandidateTestEvidenceError("Trusted inputs must be sorted by path.")
    return rows, paths


def _repository_control_entry(
    root: Path,
    candidate_root: Path,
    raw: Mapping[str, Any],
    *,
    index: int,
) -> tuple[dict[str, str], Path]:
    _require_exact_fields(
        raw,
        _REPOSITORY_CONTROL_ENTRY_FIELDS,
        label=f"Repository-control entry {index}",
    )
    relative = _safe_relative_path(
        raw.get("path"),
        label=f"Repository-control entry {index} path",
    )
    kind = raw.get("kind")
    if kind not in {"file", "tree"}:
        raise DesignCandidateTestEvidenceError(
            f"Repository-control entry {relative} kind must be file or tree."
        )
    expected = _require_sha256(
        raw.get("sha256"),
        label=f"Repository-control entry {relative} hash",
    )
    if kind == "file":
        path = _resolve_under(root, relative, label=f"Repository-control file {relative}")
        live = _sha256_file(path)
    else:
        path = _resolve_under(
            root,
            relative,
            label=f"Repository-control tree {relative}",
            directory=True,
        )
        live = str(_tree_summary(path)["tree_sha256"])
    try:
        path.relative_to(candidate_root)
    except ValueError:
        pass
    else:
        raise DesignCandidateTestEvidenceError(
            "Repository-control entries must protect repository state outside the staged candidate."
        )
    if live != expected:
        raise DesignCandidateTestEvidenceError(f"Repository-control entry is stale: {relative}")
    return {"path": relative, "kind": str(kind), "sha256": expected}, path


def _normalise_repository_control(
    root: Path,
    candidate_root: Path,
    raw: object,
    commands: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise DesignCandidateTestEvidenceError("Test policy repository control must be an object.")
    _require_exact_fields(
        raw,
        _REPOSITORY_CONTROL_FIELDS,
        label="Test policy repository control",
    )
    canonical_relative = _safe_relative_path(
        raw.get("canonical_website_path"),
        label="Canonical website path",
    )
    canonical_root = _resolve_under(
        root,
        canonical_relative,
        label="Canonical website",
        directory=True,
    )
    try:
        canonical_root.relative_to(candidate_root)
    except ValueError:
        pass
    else:
        raise DesignCandidateTestEvidenceError(
            "Canonical website control cannot point at the staged candidate."
        )
    canonical_expected = _require_sha256(
        raw.get("canonical_website_tree_sha256"),
        label="Canonical website tree hash",
    )
    if _tree_summary(canonical_root)["tree_sha256"] != canonical_expected:
        raise DesignCandidateTestEvidenceError("Canonical website changed before candidate test execution.")
    raw_entries = raw.get("entries")
    if (
        not isinstance(raw_entries, list)
        or not 1 <= len(raw_entries) <= 256
        or not all(isinstance(item, Mapping) for item in raw_entries)
    ):
        raise DesignCandidateTestEvidenceError(
            "Repository-control manifest must contain 1-256 exact entries."
        )
    entries: list[dict[str, str]] = []
    paths: dict[str, Path] = {}
    for index, item in enumerate(raw_entries):
        row, path = _repository_control_entry(
            root,
            candidate_root,
            item,
            index=index,
        )
        relative = row["path"]
        if relative in paths:
            raise DesignCandidateTestEvidenceError(f"Repository-control path is duplicated: {relative}")
        entries.append(row)
        paths[relative] = path
    if entries != sorted(entries, key=lambda item: item["path"]):
        raise DesignCandidateTestEvidenceError("Repository-control entries must be sorted by path.")
    expected_manifest = _require_sha256(
        raw.get("manifest_sha256"),
        label="Repository-control manifest hash",
    )
    if _json_sha256(entries) != expected_manifest:
        raise DesignCandidateTestEvidenceError("Repository-control manifest hash is stale.")
    pyproject_entry = next(
        (entry for entry in entries if entry["path"] == "pyproject.toml" and entry["kind"] == "file"),
        None,
    )
    if pyproject_entry is None:
        raise DesignCandidateTestEvidenceError("Repository-control manifest must bind pyproject.toml.")
    controlled_files = {entry["path"]: entry["sha256"] for entry in entries if entry["kind"] == "file"}
    for command in commands:
        for trusted in command["trusted_inputs"]:
            if controlled_files.get(trusted["path"]) != trusted["sha256"]:
                raise DesignCandidateTestEvidenceError(
                    "Every trusted command input must also be pinned by repository control."
                )
    return {
        "canonical_website_path": canonical_relative,
        "canonical_website_tree_sha256": canonical_expected,
        "canonical_root": canonical_root,
        "entries": entries,
        "paths": paths,
        "manifest_sha256": expected_manifest,
    }


def _repository_control_fingerprint(control: Mapping[str, Any]) -> str:
    live: list[dict[str, str]] = []
    paths = control["paths"]
    for entry in control["entries"]:
        path = paths[entry["path"]]
        if entry["kind"] == "file":
            value = _sha256_file(
                _regular_file(
                    path,
                    label=f"Repository-control file {entry['path']}",
                    single_link=True,
                )
            )
        else:
            value = str(
                _tree_summary(
                    _regular_directory(
                        path,
                        label=f"Repository-control tree {entry['path']}",
                    )
                )["tree_sha256"]
            )
        live.append(
            {
                "path": entry["path"],
                "kind": entry["kind"],
                "sha256": value,
            }
        )
    return _json_sha256(live)


def _validate_widths(engine: str, value: object) -> list[int]:
    if not isinstance(value, list) or any(
        not isinstance(width, int) or isinstance(width, bool) for width in value
    ):
        raise DesignCandidateTestEvidenceError("Viewport widths must be a JSON integer list.")
    widths = list(value)
    if widths != sorted(set(widths)):
        raise DesignCandidateTestEvidenceError("Viewport widths must be sorted and unique.")
    if any(width not in SUPPORTED_VIEWPORT_WIDTHS for width in widths):
        raise DesignCandidateTestEvidenceError("A command claims an unsupported viewport width.")
    if engine.startswith("playwright-") and not widths:
        raise DesignCandidateTestEvidenceError(
            "A Playwright command must state at least one supported viewport width."
        )
    if not engine.startswith("playwright-") and widths:
        raise DesignCandidateTestEvidenceError(
            "Only a pinned Playwright command may make viewport-width claims."
        )
    return widths


def _expand_argv(
    raw_argv: object,
    *,
    engine: str,
    executable: Path,
    executable_token: str,
    root: Path,
    candidate_root: Path,
    trusted_paths: Mapping[str, Path],
) -> list[str]:
    if (
        not isinstance(raw_argv, list)
        or not 2 <= len(raw_argv) <= MAX_ARGUMENTS
        or not all(isinstance(item, str) for item in raw_argv)
    ):
        raise DesignCandidateTestEvidenceError(
            f"Command argv must contain 2-{MAX_ARGUMENTS} exact string tokens."
        )
    argv = list(raw_argv)
    if argv[0] != executable_token:
        raise DesignCandidateTestEvidenceError(
            f"{engine} command must begin with its exact executable placeholder."
        )
    trusted_tokens = {f"{{repo_root}}/{relative}": str(path) for relative, path in trusted_paths.items()}
    script_index = 2 if engine == "python" else 1
    if engine == "python" and (len(argv) <= 2 or argv[1] != "-I"):
        raise DesignCandidateTestEvidenceError(
            "Python grammar is exactly: {python} -I {hash-bound trusted tool} [tool args]."
        )
    if len(argv) <= script_index or argv[script_index] not in trusted_tokens:
        raise DesignCandidateTestEvidenceError(
            "The hash-bound trusted tool must occupy the single interpreter script position."
        )
    trusted_token_occurrences = sum(token in trusted_tokens for token in argv[1:])
    if trusted_token_occurrences != 1:
        raise DesignCandidateTestEvidenceError(
            "Exactly one hash-bound trusted tool may occupy the interpreter script position."
        )
    trusted_script = Path(trusted_tokens[argv[script_index]])
    expected_extension = ".py" if engine == "python" else ".js"
    if trusted_script.suffix.casefold() != expected_extension:
        raise DesignCandidateTestEvidenceError(
            f"{engine} trusted executable tool must use {expected_extension}."
        )
    expanded: list[str] = [str(executable)]
    trusted_tool_referenced = False
    for index, token in enumerate(argv[1:], start=1):
        if not token or len(token) > MAX_ARGUMENT_LENGTH or token != token.strip():
            raise DesignCandidateTestEvidenceError(f"Command argument {index} is malformed.")
        lowered = token.casefold()
        if lowered in _FORBIDDEN_EVAL_ARGUMENTS:
            raise DesignCandidateTestEvidenceError(
                "Inline code, shell, and eval command arguments are forbidden."
            )
        if _ENV_ASSIGNMENT.match(token):
            raise DesignCandidateTestEvidenceError(
                "Command templates may not inject environment assignments."
            )
        if any(fragment in token for fragment in _FORBIDDEN_ARGUMENT_FRAGMENTS):
            raise DesignCandidateTestEvidenceError(
                f"Command argument {index} contains a forbidden path, URL, or shell fragment."
            )
        if token in trusted_tokens:
            if index != script_index:
                raise DesignCandidateTestEvidenceError(
                    "A trusted tool token is forbidden outside the interpreter script position."
                )
            expanded.append(trusted_tokens[token])
            trusted_tool_referenced = True
            continue
        if token == "{candidate_root}":
            expanded.append(str(candidate_root))
            continue
        if token.startswith("{candidate_root}/"):
            suffix = _safe_relative_path(
                token.removeprefix("{candidate_root}/"),
                label=f"Candidate argument {index}",
            )
            candidate_path = _resolve_under(
                candidate_root,
                suffix,
                label=f"Candidate argument {index}",
            )
            expanded.append(str(candidate_path))
            continue
        if "{" in token or "}" in token:
            raise DesignCandidateTestEvidenceError(
                f"Command argument {index} contains an unsupported placeholder."
            )
        if Path(token).is_absolute() or re.match(r"^[A-Za-z]:", token):
            raise DesignCandidateTestEvidenceError(
                "Raw absolute command arguments are forbidden; use a pinned placeholder."
            )
        if any(part == ".." for part in token.replace("\\", "/").split("/")):
            raise DesignCandidateTestEvidenceError("Command argument path escapes are forbidden.")
        expanded.append(token)
    if not trusted_tool_referenced:
        raise DesignCandidateTestEvidenceError(
            "Command argv must invoke at least one hash-bound trusted operator tool."
        )
    return expanded


def _normalise_command(
    root: Path,
    candidate_root: Path,
    website_root: Path,
    raw: Mapping[str, Any],
) -> dict[str, Any]:
    _require_exact_fields(raw, _COMMAND_FIELDS, label="Test command")
    command_id = _require_identifier(raw.get("id"), label="Test command id")
    template = raw.get("template")
    if not isinstance(template, Mapping):
        raise DesignCandidateTestEvidenceError(f"Command {command_id} template must be an object.")
    _require_exact_fields(template, _TEMPLATE_FIELDS, label=f"Command {command_id} template")
    expected_template_hash = _require_sha256(
        raw.get("template_sha256"),
        label=f"Command {command_id} template hash",
    )
    if _json_sha256(template) != expected_template_hash:
        raise DesignCandidateTestEvidenceError(f"Command {command_id} template hash is stale.")
    engine = template.get("engine")
    if not isinstance(engine, str) or engine not in SUPPORTED_ENGINES:
        raise DesignCandidateTestEvidenceError(f"Command {command_id} engine is unsupported.")
    executable, executable_token = _resolve_tool(engine)
    expected_executable_hash = _require_sha256(
        template.get("tool_executable_sha256"),
        label=f"Command {command_id} tool executable hash",
    )
    if _sha256_file(executable) != expected_executable_hash:
        raise DesignCandidateTestEvidenceError(f"Command {command_id} tool executable changed.")
    widths = _validate_widths(engine, template.get("viewport_widths"))
    timeout = template.get("timeout_seconds")
    if not isinstance(timeout, int) or isinstance(timeout, bool) or not 1 <= timeout <= MAX_TIMEOUT_SECONDS:
        raise DesignCandidateTestEvidenceError(
            f"Command {command_id} timeout must be 1-{MAX_TIMEOUT_SECONDS} seconds."
        )
    if template.get("required_outputs") != list(PROCESS_OUTPUTS):
        raise DesignCandidateTestEvidenceError(
            f"Command {command_id} must require the exact process output evidence set."
        )
    cwd_relative = template.get("cwd")
    if cwd_relative == ".":
        cwd = website_root
        cwd_value = "."
    else:
        cwd_value = _safe_relative_path(cwd_relative, label=f"Command {command_id} cwd")
        cwd = _resolve_under(
            website_root,
            cwd_value,
            label=f"Command {command_id} cwd",
            directory=True,
        )
    trusted_rows, trusted_paths = _trusted_inputs(
        root,
        candidate_root,
        template.get("trusted_inputs"),
    )
    argv = _expand_argv(
        template.get("argv"),
        engine=engine,
        executable=executable,
        executable_token=executable_token,
        root=root,
        candidate_root=website_root,
        trusted_paths=trusted_paths,
    )
    return {
        "id": command_id,
        "template": dict(template),
        "template_sha256": expected_template_hash,
        "engine": engine,
        "executable": executable,
        "argv": argv,
        "cwd": cwd,
        "cwd_value": cwd_value,
        "timeout_seconds": timeout,
        "viewport_widths": widths,
        "trusted_inputs": trusted_rows,
        "trusted_paths": trusted_paths,
    }


def _load_policy(
    policy_path: Path,
    *,
    expected_policy_sha256: str,
    root: Path,
) -> tuple[
    dict[str, Any],
    bytes,
    Path,
    dict[str, Any],
    Path,
    Path,
    Path,
    dict[str, Any],
    bytes,
    list[dict[str, Any]],
    dict[str, Any],
]:
    expected = _require_sha256(expected_policy_sha256, label="Pinned test policy hash")
    policy_path = _regular_file(policy_path, label="Test policy", single_link=True)
    try:
        policy_path.relative_to(root)
    except ValueError as exc:
        raise DesignCandidateTestEvidenceError("Test policy must stay inside the repository.") from exc
    policy, policy_raw = _load_json_file(policy_path, label="Test policy")
    _require_exact_fields(policy, _POLICY_FIELDS, label="Test policy")
    if policy.get("schema") != POLICY_SCHEMA:
        raise DesignCandidateTestEvidenceError("Test policy schema is unsupported.")
    _require_identifier(policy.get("policy_id"), label="Test policy id")
    if _bytes_sha256(policy_raw) != expected:
        raise DesignCandidateTestEvidenceError(
            "Test policy file bytes do not match its externally pinned immutable hash."
        )
    if policy.get("authority") != POLICY_AUTHORITY:
        raise DesignCandidateTestEvidenceError("Test policy authority boundary is not exact.")
    execution = policy.get("execution")
    if not isinstance(execution, Mapping):
        raise DesignCandidateTestEvidenceError("Test policy execution control must be an object.")
    _require_exact_fields(execution, _POLICY_EXECUTION_FIELDS, label="Test policy execution")
    if dict(execution) != _POLICY_EXECUTION:
        raise DesignCandidateTestEvidenceError(
            "Test policy must retain local, no-shell, no-env, one-shot execution."
        )
    policy_candidate = policy.get("candidate")
    if not isinstance(policy_candidate, Mapping):
        raise DesignCandidateTestEvidenceError("Test policy candidate binding must be an object.")
    (
        candidate_receipt,
        candidate_receipt_path,
        candidate_root,
        website_root,
        candidate_summary,
        candidate_raw,
    ) = _load_bound_candidate(root, policy_candidate)
    try:
        policy_path.relative_to(candidate_root)
    except ValueError:
        pass
    else:
        raise DesignCandidateTestEvidenceError(
            "Operator test policy must stay outside the staged candidate root."
        )
    raw_ids = policy.get("required_command_ids")
    raw_commands = policy.get("commands")
    if (
        not isinstance(raw_ids, list)
        or not 1 <= len(raw_ids) <= MAX_COMMANDS
        or not all(isinstance(item, str) for item in raw_ids)
        or len(set(raw_ids)) != len(raw_ids)
        or not isinstance(raw_commands, list)
        or len(raw_commands) != len(raw_ids)
        or not all(isinstance(item, Mapping) for item in raw_commands)
    ):
        raise DesignCandidateTestEvidenceError(
            "Test policy must declare 1-32 unique required command ids and matching templates."
        )
    commands = [_normalise_command(root, candidate_root, website_root, command) for command in raw_commands]
    if [command["id"] for command in commands] != raw_ids:
        raise DesignCandidateTestEvidenceError(
            "Required command ids must exactly match ordered command templates."
        )
    repository_control = _normalise_repository_control(
        root,
        candidate_root,
        policy.get("repository_control"),
        commands,
    )
    return (
        policy,
        policy_raw,
        policy_path,
        candidate_receipt,
        candidate_receipt_path,
        candidate_root,
        website_root,
        candidate_summary,
        candidate_raw,
        commands,
        repository_control,
    )


def _sanitised_environment(executable: Path) -> dict[str, str]:
    environment: dict[str, str] = {
        "AUREON_OFFLINE_INTENT": "1",
        "AUREON_OS_NETWORK_SANDBOX": "0",
        "CI": "1",
        "NO_COLOR": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "PYTHONNOUSERSITE": "1",
        "PIP_NO_INDEX": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "NPM_CONFIG_OFFLINE": "true",
        "NPM_CONFIG_AUDIT": "false",
        "HTTP_PROXY": "http://127.0.0.1:9",
        "HTTPS_PROXY": "http://127.0.0.1:9",
        "ALL_PROXY": "http://127.0.0.1:9",
        "NO_PROXY": "",
    }
    for key in _ALLOWLIST_INHERITED_ENV_KEYS:
        value = os.environ.get(key)
        if value:
            environment[key] = value
    path_parts = [str(executable.parent)]
    system_root = environment.get("SYSTEMROOT") or environment.get("WINDIR")
    if system_root:
        path_parts.append(str(Path(system_root) / "System32"))
    environment["PATH"] = os.pathsep.join(dict.fromkeys(path_parts))
    return environment


def _environment_receipt(environment: Mapping[str, str]) -> dict[str, Any]:
    keys = sorted(environment)
    values = [{"key": key, "value": environment[key]} for key in keys]
    return {
        "mode": "sanitised-fixed-values-plus-os-runtime-allowlist",
        "inherited": sorted(key for key in _ALLOWLIST_INHERITED_ENV_KEYS if key in environment),
        "network": "offline-intent-null-proxy-no-kernel-network-sandbox",
        "keys": keys,
        "keys_sha256": _json_sha256(keys),
        "values_sha256": _json_sha256(values),
    }


def _observe_bytes(value: bytes) -> _StreamObservation:
    return _StreamObservation(sha256=_bytes_sha256(value), byte_count=len(value))


def _observe_file(stream: Any) -> _StreamObservation:
    digest = hashlib.sha256()
    byte_count = 0
    stream.flush()
    stream.seek(0)
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(block)
        byte_count += len(block)
    return _StreamObservation(
        sha256=digest.hexdigest().upper(),
        byte_count=byte_count,
    )


def _stream_receipt(value: bytes | _StreamObservation) -> dict[str, Any]:
    observation = _observe_bytes(value) if isinstance(value, bytes) else value
    return {
        "present": True,
        "sha256": observation.sha256,
        "bytes": observation.byte_count,
        "retained": False,
    }


def _empty_process_outputs() -> dict[str, Any]:
    return {
        "exit-code": {"present": False, "value": None},
        "stdout-sha256": _stream_receipt(b""),
        "stderr-sha256": _stream_receipt(b""),
    }


def _run_process_once(
    argv: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    timeout_seconds: int,
) -> tuple[
    int | None,
    bool,
    _StreamObservation,
    _StreamObservation,
    str,
    bool,
]:
    with (
        tempfile.TemporaryFile(mode="w+b") as stdout_file,
        tempfile.TemporaryFile(mode="w+b") as stderr_file,
    ):
        try:
            process = subprocess.Popen(
                list(argv),
                cwd=cwd,
                env=dict(environment),
                stdin=subprocess.DEVNULL,
                stdout=stdout_file,
                stderr=stderr_file,
                shell=False,
            )
        except OSError as exc:
            return (
                None,
                False,
                _observe_bytes(b""),
                _observe_bytes(str(exc).encode(errors="replace")),
                "execution-error",
                False,
            )
        deadline = time.monotonic() + timeout_seconds
        timed_out = False
        output_limit_exceeded = False
        while process.poll() is None:
            stdout_bytes = os.fstat(stdout_file.fileno()).st_size
            stderr_bytes = os.fstat(stderr_file.fileno()).st_size
            if stdout_bytes > MAX_STREAM_BYTES or stderr_bytes > MAX_STREAM_BYTES:
                output_limit_exceeded = True
                process.kill()
                break
            if time.monotonic() >= deadline:
                timed_out = True
                process.kill()
                break
            time.sleep(0.01)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        if (
            os.fstat(stdout_file.fileno()).st_size > MAX_STREAM_BYTES
            or os.fstat(stderr_file.fileno()).st_size > MAX_STREAM_BYTES
        ):
            output_limit_exceeded = True
        stdout = _observe_file(stdout_file)
        stderr = _observe_file(stderr_file)
        if output_limit_exceeded:
            return (
                None,
                False,
                stdout,
                stderr,
                "output-limit-exceeded",
                True,
            )
        if timed_out:
            return None, True, stdout, stderr, "", False
        return process.returncode, False, stdout, stderr, "", False


def _trusted_input_fingerprint(rows: Sequence[Mapping[str, str]], paths: Mapping[str, Path]) -> str:
    live: list[dict[str, str]] = []
    for row in rows:
        relative = row["path"]
        path = _regular_file(paths[relative], label=f"Trusted input {relative}", single_link=True)
        live.append({"path": relative, "sha256": _sha256_file(path)})
    return _json_sha256(live)


def _integrity_value(
    label: str,
    getter: Callable[[], str],
    *,
    tolerate_error: bool,
) -> str:
    try:
        return getter()
    except (DesignCandidateTestEvidenceError, OSError):
        if not tolerate_error:
            raise
        return _bytes_sha256(f"unavailable-integrity-observation:{label}".encode())


def _integrity_snapshot(
    *,
    website_root: Path,
    policy_path: Path,
    candidate_receipt_path: Path,
    trusted_rows: Sequence[Mapping[str, str]],
    trusted_paths: Mapping[str, Path],
    repository_control: Mapping[str, Any],
    executable: Path,
    tolerate_error: bool,
) -> dict[str, str]:
    implementation = _integrity_value(
        "loaded-implementation-pair",
        lambda: _json_sha256(_assert_loaded_source_current()),
        tolerate_error=tolerate_error,
    )
    expected_implementation_pair = _json_sha256(
        {
            "candidate_test_evidence_path": MODULE_PATH,
            "candidate_test_evidence_sha256": _LOADED_SOURCE_SHA256,
            "secure_immutable_artifact_path": SECURE_WRITER_PATH,
            "secure_immutable_artifact_sha256": _LOADED_SECURE_WRITER_SHA256,
        }
    )
    implementation_current = implementation == expected_implementation_pair
    return {
        "candidate_tree": _integrity_value(
            "candidate-tree",
            lambda: str(_tree_summary(website_root)["tree_sha256"]),
            tolerate_error=tolerate_error,
        ),
        "policy_file": _integrity_value(
            "policy-file",
            lambda: _sha256_file(_regular_file(policy_path, label="Test policy", single_link=True)),
            tolerate_error=tolerate_error,
        ),
        "candidate_receipt_file": _integrity_value(
            "candidate-receipt-file",
            lambda: _sha256_file(
                _regular_file(
                    candidate_receipt_path,
                    label="Candidate receipt",
                    single_link=True,
                )
            ),
            tolerate_error=tolerate_error,
        ),
        "trusted_inputs": _integrity_value(
            "trusted-inputs",
            lambda: _trusted_input_fingerprint(trusted_rows, trusted_paths),
            tolerate_error=tolerate_error,
        ),
        "canonical_website": _integrity_value(
            "canonical-website",
            lambda: str(_tree_summary(repository_control["canonical_root"])["tree_sha256"]),
            tolerate_error=tolerate_error,
        ),
        "repository_control": _integrity_value(
            "repository-control",
            lambda: _repository_control_fingerprint(repository_control),
            tolerate_error=tolerate_error,
        ),
        "tool_executable": _integrity_value(
            "tool-executable",
            lambda: _sha256_file(
                _regular_file(
                    executable,
                    label="Command executable",
                    single_link=False,
                )
            ),
            tolerate_error=tolerate_error,
        ),
        "evidence_implementation": (
            _LOADED_SOURCE_SHA256
            if implementation_current
            else _bytes_sha256(b"unavailable-integrity-observation:evidence-implementation")
        ),
        "secure_writer_implementation": (
            _LOADED_SECURE_WRITER_SHA256
            if implementation_current
            else _bytes_sha256(b"unavailable-integrity-observation:secure-writer-implementation")
        ),
    }


def _version_argv(engine: str, executable: Path) -> list[str]:
    del engine
    return [str(executable), "--version"]


def _skipped_execution(
    ordinal: int,
    command: Mapping[str, Any],
    *,
    policy_hash: str,
    candidate_receipt_hash: str,
    candidate_tree_hash: str,
    canonical_website_hash: str,
    repository_control_hash: str,
    implementation: Mapping[str, str],
) -> dict[str, Any]:
    empty_hash = _json_sha256([])
    return {
        "ordinal": ordinal,
        "command_id": command["id"],
        "template_sha256": command["template_sha256"],
        "engine": command["engine"],
        "viewport_widths": command["viewport_widths"],
        "argv_sha256": _json_sha256(command["argv"]),
        "cwd": command["cwd_value"],
        "environment": _environment_receipt(_sanitised_environment(command["executable"])),
        "trusted_inputs_sha256": _json_sha256(command["trusted_inputs"]),
        "tool": {
            "executable_file_sha256": _sha256_file(command["executable"]),
            "executable_path_sha256": _bytes_sha256(str(command["executable"]).encode("utf-8")),
            "version_argv_sha256": _json_sha256(_version_argv(command["engine"], command["executable"])),
            "version_exit_code": None,
            "version_output_limit_exceeded": False,
            "version_stdout": _stream_receipt(b""),
            "version_stderr": _stream_receipt(b""),
        },
        "started_at": None,
        "ended_at": None,
        "duration_ms": 0,
        "attempt": 0,
        "retry_count": 0,
        "state": "not-run-prior-failure",
        "passed": False,
        "exit_code": None,
        "timed_out": False,
        "output_limit_exceeded": False,
        "outputs": _empty_process_outputs(),
        "integrity": {
            "candidate_tree_before": candidate_tree_hash,
            "candidate_tree_after": candidate_tree_hash,
            "policy_file_before": policy_hash,
            "policy_file_after": policy_hash,
            "candidate_receipt_file_before": candidate_receipt_hash,
            "candidate_receipt_file_after": candidate_receipt_hash,
            "trusted_inputs_before": empty_hash,
            "trusted_inputs_after": empty_hash,
            "canonical_website_before": canonical_website_hash,
            "canonical_website_after": canonical_website_hash,
            "repository_control_before": repository_control_hash,
            "repository_control_after": repository_control_hash,
            "tool_executable_before": _sha256_file(command["executable"]),
            "tool_executable_after": _sha256_file(command["executable"]),
            "evidence_implementation_before": implementation["candidate_test_evidence_sha256"],
            "evidence_implementation_after": implementation["candidate_test_evidence_sha256"],
            "secure_writer_implementation_before": implementation["secure_immutable_artifact_sha256"],
            "secure_writer_implementation_after": implementation["secure_immutable_artifact_sha256"],
            "endpoint_consistent": False,
        },
    }


def execute_candidate_test_evidence(
    policy_path: Path,
    *,
    expected_policy_sha256: str,
    command_ids: Sequence[str],
    repo_root: Path | None = None,
    receipt_id: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Execute one complete pinned suite exactly once and return hash-only evidence.

    ``command_ids`` must equal the policy's complete ordered required list.
    There is deliberately no argv, environment, shell, retry, or output-content
    parameter.
    """

    implementation_start = _assert_loaded_source_current()
    root = _find_repo_root(repo_root)
    (
        policy,
        policy_raw,
        policy_path,
        candidate_receipt,
        candidate_receipt_path,
        candidate_root,
        website_root,
        candidate_summary,
        candidate_raw,
        commands,
        repository_control,
    ) = _load_policy(
        policy_path,
        expected_policy_sha256=expected_policy_sha256,
        root=root,
    )
    selected = list(command_ids)
    required = policy["required_command_ids"]
    if (
        not all(isinstance(item, str) for item in selected)
        or selected != required
        or len(set(selected)) != len(selected)
    ):
        raise DesignCandidateTestEvidenceError(
            "Command selection must equal the complete ordered pinned policy; args are not accepted."
        )
    run_id = _require_identifier(
        receipt_id or f"candidate-tests-{int(time.time_ns())}",
        label="Test evidence receipt id",
    )
    policy_file_hash = _bytes_sha256(policy_raw)
    candidate_receipt_file_hash = _bytes_sha256(candidate_raw)
    executions: list[dict[str, Any]] = []
    prior_failure = False
    for ordinal, command in enumerate(commands, start=1):
        if _assert_loaded_source_current() != implementation_start:
            raise DesignCandidateTestEvidenceError(
                "Test-evidence or immutable-writer implementation changed before command execution."
            )
        if prior_failure:
            executions.append(
                _skipped_execution(
                    ordinal,
                    command,
                    policy_hash=policy_file_hash,
                    candidate_receipt_hash=candidate_receipt_file_hash,
                    candidate_tree_hash=str(candidate_summary["tree_sha256"]),
                    canonical_website_hash=str(repository_control["canonical_website_tree_sha256"]),
                    repository_control_hash=str(repository_control["manifest_sha256"]),
                    implementation=implementation_start,
                )
            )
            continue
        environment = _sanitised_environment(command["executable"])
        before = _integrity_snapshot(
            website_root=website_root,
            policy_path=policy_path,
            candidate_receipt_path=candidate_receipt_path,
            trusted_rows=command["trusted_inputs"],
            trusted_paths=command["trusted_paths"],
            repository_control=repository_control,
            executable=command["executable"],
            tolerate_error=False,
        )
        version_argv = _version_argv(command["engine"], command["executable"])
        (
            version_exit,
            version_timed_out,
            version_stdout,
            version_stderr,
            version_error,
            version_output_limit_exceeded,
        ) = _run_process_once(
            version_argv,
            cwd=command["cwd"],
            environment=environment,
            timeout_seconds=30,
        )
        started_at: str | None = None
        ended_at: str | None = None
        duration_ms = 0
        exit_code: int | None = None
        timed_out = False
        stdout = _observe_bytes(b"")
        stderr = _observe_bytes(b"")
        process_error = ""
        output_limit_exceeded = False
        attempt = 0
        if (
            version_exit == 0
            and not version_timed_out
            and not version_error
            and not version_output_limit_exceeded
        ):
            attempt = 1
            started_at = _utc_iso(now)
            started_ns = time.monotonic_ns()
            (
                exit_code,
                timed_out,
                stdout,
                stderr,
                process_error,
                output_limit_exceeded,
            ) = _run_process_once(
                command["argv"],
                cwd=command["cwd"],
                environment=environment,
                timeout_seconds=command["timeout_seconds"],
            )
            duration_ms = max(0, (time.monotonic_ns() - started_ns) // 1_000_000)
            ended_at = _utc_iso(now)
        after = _integrity_snapshot(
            website_root=website_root,
            policy_path=policy_path,
            candidate_receipt_path=candidate_receipt_path,
            trusted_rows=command["trusted_inputs"],
            trusted_paths=command["trusted_paths"],
            repository_control=repository_control,
            executable=command["executable"],
            tolerate_error=True,
        )
        trusted_expected = _json_sha256(command["trusted_inputs"])
        endpoint_consistent = (
            before == after
            and before["candidate_tree"] == candidate_summary["tree_sha256"]
            and before["policy_file"] == policy_file_hash
            and before["candidate_receipt_file"] == candidate_receipt_file_hash
            and before["trusted_inputs"] == trusted_expected
            and before["canonical_website"] == repository_control["canonical_website_tree_sha256"]
            and before["repository_control"] == repository_control["manifest_sha256"]
            and before["tool_executable"] == command["template"]["tool_executable_sha256"]
            and before["evidence_implementation"] == implementation_start["candidate_test_evidence_sha256"]
            and after["evidence_implementation"] == implementation_start["candidate_test_evidence_sha256"]
            and before["secure_writer_implementation"]
            == implementation_start["secure_immutable_artifact_sha256"]
            and after["secure_writer_implementation"]
            == implementation_start["secure_immutable_artifact_sha256"]
        )
        command_passed = (
            attempt == 1
            and exit_code == 0
            and not timed_out
            and not process_error
            and not output_limit_exceeded
            and version_exit == 0
            and not version_timed_out
            and not version_error
            and not version_output_limit_exceeded
            and endpoint_consistent
        )
        if not endpoint_consistent:
            state = "integrity-failure"
        elif version_exit != 0 or version_timed_out or version_error or version_output_limit_exceeded:
            state = "tool-version-failure"
        elif timed_out:
            state = "timed-out"
        elif output_limit_exceeded:
            state = "output-limit-exceeded"
        elif process_error:
            state = "execution-error"
        elif exit_code != 0:
            state = "failed"
        else:
            state = "passed"
        execution = {
            "ordinal": ordinal,
            "command_id": command["id"],
            "template_sha256": command["template_sha256"],
            "engine": command["engine"],
            "viewport_widths": command["viewport_widths"],
            "argv_sha256": _json_sha256(command["argv"]),
            "cwd": command["cwd_value"],
            "environment": _environment_receipt(environment),
            "trusted_inputs_sha256": trusted_expected,
            "tool": {
                "executable_file_sha256": _sha256_file(command["executable"]),
                "executable_path_sha256": _bytes_sha256(str(command["executable"]).encode("utf-8")),
                "version_argv_sha256": _json_sha256(version_argv),
                "version_exit_code": version_exit,
                "version_output_limit_exceeded": version_output_limit_exceeded,
                "version_stdout": _stream_receipt(version_stdout),
                "version_stderr": _stream_receipt(version_stderr),
            },
            "started_at": started_at,
            "ended_at": ended_at,
            "duration_ms": duration_ms,
            "attempt": attempt,
            "retry_count": 0,
            "state": state,
            "passed": command_passed,
            "exit_code": exit_code,
            "timed_out": timed_out,
            "output_limit_exceeded": output_limit_exceeded,
            "outputs": {
                "exit-code": {"present": attempt == 1 and exit_code is not None, "value": exit_code},
                "stdout-sha256": _stream_receipt(stdout),
                "stderr-sha256": _stream_receipt(stderr),
            },
            "integrity": {
                "candidate_tree_before": before["candidate_tree"],
                "candidate_tree_after": after["candidate_tree"],
                "policy_file_before": before["policy_file"],
                "policy_file_after": after["policy_file"],
                "candidate_receipt_file_before": before["candidate_receipt_file"],
                "candidate_receipt_file_after": after["candidate_receipt_file"],
                "trusted_inputs_before": before["trusted_inputs"],
                "trusted_inputs_after": after["trusted_inputs"],
                "canonical_website_before": before["canonical_website"],
                "canonical_website_after": after["canonical_website"],
                "repository_control_before": before["repository_control"],
                "repository_control_after": after["repository_control"],
                "tool_executable_before": before["tool_executable"],
                "tool_executable_after": after["tool_executable"],
                "evidence_implementation_before": before["evidence_implementation"],
                "evidence_implementation_after": after["evidence_implementation"],
                "secure_writer_implementation_before": before["secure_writer_implementation"],
                "secure_writer_implementation_after": after["secure_writer_implementation"],
                "endpoint_consistent": endpoint_consistent,
            },
        }
        executions.append(execution)
        prior_failure = not command_passed
    implementation_end = _assert_loaded_source_current()
    if implementation_end != implementation_start:
        raise DesignCandidateTestEvidenceError(
            "Test-evidence or immutable-writer implementation changed during suite execution."
        )
    passed = bool(executions) and all(item["passed"] is True for item in executions)
    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "receipt_id": run_id,
        "created_at": _utc_iso(now),
        "state": "passed" if passed else "failed",
        "passed": passed,
        "local_execution": dict(LOCAL_EXECUTION_BOUNDARY),
        "implementation": implementation_start,
        "policy": {
            "path": _relative_to_repo(root, policy_path),
            "file_sha256": policy_file_hash,
            "json_sha256": _json_sha256(policy),
            "policy_id": policy["policy_id"],
        },
        "candidate": {
            "receipt_path": _relative_to_repo(root, candidate_receipt_path),
            "receipt_file_sha256": candidate_receipt_file_hash,
            "receipt_json_sha256": _json_sha256(candidate_receipt),
            "root": _relative_to_repo(root, candidate_root),
            "website_path": _relative_to_repo(root, website_root),
            "tree_sha256": candidate_summary["tree_sha256"],
            "file_count": candidate_summary["file_count"],
            "total_bytes": candidate_summary["total_bytes"],
        },
        "selection": {
            "command_ids": selected,
            "command_ids_sha256": _json_sha256(selected),
            "count": len(selected),
        },
        "executions": executions,
        "authority": dict(EVIDENCE_AUTHORITY),
    }
    receipt["receipt_payload_sha256"] = _json_sha256(receipt)
    with _ISSUED_RECEIPT_LOCK:
        _ISSUED_RECEIPT_PAYLOAD_HASHES.add(str(receipt["receipt_payload_sha256"]))
    return receipt


def _validate_timestamp(value: object, *, nullable: bool, label: str) -> None:
    if nullable and value is None:
        return
    if not isinstance(value, str) or not value.endswith("Z"):
        raise DesignCandidateTestEvidenceError(f"{label} must be a UTC Z timestamp.")
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise DesignCandidateTestEvidenceError(f"{label} must be an ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None:
        raise DesignCandidateTestEvidenceError(f"{label} must be timezone-aware.")


def _validate_stream(value: object, *, label: str) -> None:
    if not isinstance(value, Mapping):
        raise DesignCandidateTestEvidenceError(f"{label} must be an object.")
    _require_exact_fields(value, _STREAM_FIELDS, label=label)
    if value.get("present") is not True or value.get("retained") is not False:
        raise DesignCandidateTestEvidenceError(f"{label} must be present and hash-only.")
    _require_sha256(value.get("sha256"), label=f"{label} hash")
    byte_count = value.get("bytes")
    if not isinstance(byte_count, int) or isinstance(byte_count, bool) or byte_count < 0:
        raise DesignCandidateTestEvidenceError(f"{label} byte count is invalid.")


def _validate_execution(
    value: Mapping[str, Any],
    *,
    ordinal: int,
    command: Mapping[str, Any],
    policy_file_hash: str,
    candidate_receipt_hash: str,
    candidate_tree_hash: str,
    canonical_website_hash: str,
    repository_control_hash: str,
    implementation: Mapping[str, str],
) -> bool:
    _require_exact_fields(value, _EXECUTION_FIELDS, label=f"Execution {ordinal}")
    if (
        value.get("ordinal") != ordinal
        or value.get("command_id") != command["id"]
        or value.get("template_sha256") != command["template_sha256"]
        or value.get("engine") != command["engine"]
        or value.get("viewport_widths") != command["viewport_widths"]
        or value.get("argv_sha256") != _json_sha256(command["argv"])
        or value.get("cwd") != command["cwd_value"]
        or value.get("trusted_inputs_sha256") != _json_sha256(command["trusted_inputs"])
    ):
        raise DesignCandidateTestEvidenceError(
            f"Execution {ordinal} drifted from its exact command template."
        )
    environment = value.get("environment")
    if not isinstance(environment, Mapping):
        raise DesignCandidateTestEvidenceError(f"Execution {ordinal} environment is missing.")
    _require_exact_fields(environment, _ENVIRONMENT_FIELDS, label=f"Execution {ordinal} environment")
    expected_environment = _environment_receipt(_sanitised_environment(command["executable"]))
    if dict(environment) != expected_environment:
        raise DesignCandidateTestEvidenceError(
            f"Execution {ordinal} contains arbitrary or inherited environment state."
        )
    tool = value.get("tool")
    if not isinstance(tool, Mapping):
        raise DesignCandidateTestEvidenceError(f"Execution {ordinal} tool evidence is missing.")
    _require_exact_fields(tool, _TOOL_FIELDS, label=f"Execution {ordinal} tool")
    if (
        tool.get("executable_file_sha256") != _sha256_file(command["executable"])
        or tool.get("executable_path_sha256") != _bytes_sha256(str(command["executable"]).encode("utf-8"))
        or tool.get("version_argv_sha256")
        != _json_sha256(_version_argv(command["engine"], command["executable"]))
    ):
        raise DesignCandidateTestEvidenceError(f"Execution {ordinal} tool identity is not hash-bound.")
    version_exit = tool.get("version_exit_code")
    if version_exit is not None and (not isinstance(version_exit, int) or isinstance(version_exit, bool)):
        raise DesignCandidateTestEvidenceError(f"Execution {ordinal} tool version exit code is invalid.")
    if not isinstance(tool.get("version_output_limit_exceeded"), bool):
        raise DesignCandidateTestEvidenceError(
            f"Execution {ordinal} tool version output-limit status is invalid."
        )
    _validate_stream(tool.get("version_stdout"), label=f"Execution {ordinal} version stdout")
    _validate_stream(tool.get("version_stderr"), label=f"Execution {ordinal} version stderr")
    _validate_timestamp(value.get("started_at"), nullable=True, label=f"Execution {ordinal} start")
    _validate_timestamp(value.get("ended_at"), nullable=True, label=f"Execution {ordinal} end")
    duration = value.get("duration_ms")
    if not isinstance(duration, int) or isinstance(duration, bool) or duration < 0:
        raise DesignCandidateTestEvidenceError(f"Execution {ordinal} duration is invalid.")
    attempt = value.get("attempt")
    if attempt not in {0, 1} or isinstance(attempt, bool) or value.get("retry_count") != 0:
        raise DesignCandidateTestEvidenceError(f"Execution {ordinal} violates one-shot, no-retry execution.")
    if (
        not isinstance(value.get("passed"), bool)
        or not isinstance(value.get("timed_out"), bool)
        or not isinstance(value.get("output_limit_exceeded"), bool)
    ):
        raise DesignCandidateTestEvidenceError(
            f"Execution {ordinal} uses worker-declared non-boolean status."
        )
    exit_code = value.get("exit_code")
    if exit_code is not None and (not isinstance(exit_code, int) or isinstance(exit_code, bool)):
        raise DesignCandidateTestEvidenceError(f"Execution {ordinal} exit code is invalid.")
    outputs = value.get("outputs")
    if not isinstance(outputs, Mapping):
        raise DesignCandidateTestEvidenceError(f"Execution {ordinal} outputs are missing.")
    _require_exact_fields(outputs, _OUTPUTS_FIELDS, label=f"Execution {ordinal} outputs")
    exit_output = outputs.get("exit-code")
    if not isinstance(exit_output, Mapping):
        raise DesignCandidateTestEvidenceError(f"Execution {ordinal} exit output is missing.")
    _require_exact_fields(
        exit_output,
        _EXIT_OUTPUT_FIELDS,
        label=f"Execution {ordinal} exit output",
    )
    if not isinstance(exit_output.get("present"), bool) or exit_output.get("value") != exit_code:
        raise DesignCandidateTestEvidenceError(f"Execution {ordinal} exit output is inconsistent.")
    _validate_stream(outputs.get("stdout-sha256"), label=f"Execution {ordinal} stdout")
    _validate_stream(outputs.get("stderr-sha256"), label=f"Execution {ordinal} stderr")
    integrity = value.get("integrity")
    if not isinstance(integrity, Mapping):
        raise DesignCandidateTestEvidenceError(f"Execution {ordinal} integrity is missing.")
    _require_exact_fields(integrity, _INTEGRITY_FIELDS, label=f"Execution {ordinal} integrity")
    for field in _INTEGRITY_FIELDS - {"endpoint_consistent"}:
        _require_sha256(integrity.get(field), label=f"Execution {ordinal} {field}")
    if not isinstance(integrity.get("endpoint_consistent"), bool):
        raise DesignCandidateTestEvidenceError(
            f"Execution {ordinal} endpoint integrity status must be boolean."
        )
    endpoint_consistent = (
        integrity.get("endpoint_consistent") is True
        and integrity.get("candidate_tree_before") == candidate_tree_hash
        and integrity.get("candidate_tree_after") == candidate_tree_hash
        and integrity.get("policy_file_before") == policy_file_hash
        and integrity.get("policy_file_after") == policy_file_hash
        and integrity.get("candidate_receipt_file_before") == candidate_receipt_hash
        and integrity.get("candidate_receipt_file_after") == candidate_receipt_hash
        and integrity.get("trusted_inputs_before") == _json_sha256(command["trusted_inputs"])
        and integrity.get("trusted_inputs_after") == _json_sha256(command["trusted_inputs"])
        and integrity.get("canonical_website_before") == canonical_website_hash
        and integrity.get("canonical_website_after") == canonical_website_hash
        and integrity.get("repository_control_before") == repository_control_hash
        and integrity.get("repository_control_after") == repository_control_hash
        and integrity.get("tool_executable_before") == command["template"]["tool_executable_sha256"]
        and integrity.get("tool_executable_after") == command["template"]["tool_executable_sha256"]
        and integrity.get("evidence_implementation_before")
        == implementation["candidate_test_evidence_sha256"]
        and integrity.get("evidence_implementation_after") == implementation["candidate_test_evidence_sha256"]
        and integrity.get("secure_writer_implementation_before")
        == implementation["secure_immutable_artifact_sha256"]
        and integrity.get("secure_writer_implementation_after")
        == implementation["secure_immutable_artifact_sha256"]
    )
    state = value.get("state")
    if not isinstance(state, str):
        raise DesignCandidateTestEvidenceError(f"Execution {ordinal} state must be a derived string.")
    derived_passed: bool
    if attempt == 0:
        empty_stream = _stream_receipt(b"")
        skipped_integrity = (
            integrity.get("candidate_tree_before") == candidate_tree_hash
            and integrity.get("candidate_tree_after") == candidate_tree_hash
            and integrity.get("policy_file_before") == policy_file_hash
            and integrity.get("policy_file_after") == policy_file_hash
            and integrity.get("candidate_receipt_file_before") == candidate_receipt_hash
            and integrity.get("candidate_receipt_file_after") == candidate_receipt_hash
            and integrity.get("trusted_inputs_before") == _json_sha256([])
            and integrity.get("trusted_inputs_after") == _json_sha256([])
            and integrity.get("canonical_website_before") == canonical_website_hash
            and integrity.get("canonical_website_after") == canonical_website_hash
            and integrity.get("repository_control_before") == repository_control_hash
            and integrity.get("repository_control_after") == repository_control_hash
            and integrity.get("tool_executable_before") == command["template"]["tool_executable_sha256"]
            and integrity.get("tool_executable_after") == command["template"]["tool_executable_sha256"]
            and integrity.get("evidence_implementation_before")
            == implementation["candidate_test_evidence_sha256"]
            and integrity.get("evidence_implementation_after")
            == implementation["candidate_test_evidence_sha256"]
            and integrity.get("secure_writer_implementation_before")
            == implementation["secure_immutable_artifact_sha256"]
            and integrity.get("secure_writer_implementation_after")
            == implementation["secure_immutable_artifact_sha256"]
            and integrity.get("endpoint_consistent") is False
        )
        common_not_run = (
            value.get("started_at") is None
            and value.get("ended_at") is None
            and duration == 0
            and exit_code is None
            and value.get("timed_out") is False
            and value.get("output_limit_exceeded") is False
            and exit_output == {"present": False, "value": None}
            and outputs.get("stdout-sha256") == empty_stream
            and outputs.get("stderr-sha256") == empty_stream
        )
        if not common_not_run:
            raise DesignCandidateTestEvidenceError(f"Execution {ordinal} unattempted state is inconsistent.")
        if state == "not-run-prior-failure":
            if not skipped_integrity or tool.get("version_exit_code") is not None:
                raise DesignCandidateTestEvidenceError(
                    f"Execution {ordinal} skipped state lacks its exact marker."
                )
        elif state == "tool-version-failure":
            if not endpoint_consistent or (
                tool.get("version_exit_code") == 0 and tool.get("version_output_limit_exceeded") is False
            ):
                raise DesignCandidateTestEvidenceError(
                    f"Execution {ordinal} tool-version failure is inconsistent."
                )
        elif state == "integrity-failure":
            if endpoint_consistent or skipped_integrity:
                raise DesignCandidateTestEvidenceError(
                    f"Execution {ordinal} integrity failure is inconsistent."
                )
        else:
            raise DesignCandidateTestEvidenceError(f"Execution {ordinal} unattempted state is unsupported.")
        derived_passed = False
    else:
        if (
            value.get("started_at") is None
            or value.get("ended_at") is None
            or exit_output.get("present") != (exit_code is not None)
            or tool.get("version_exit_code") != 0
            or tool.get("version_output_limit_exceeded") is not False
        ):
            raise DesignCandidateTestEvidenceError(f"Execution {ordinal} attempted evidence is incomplete.")
        if not endpoint_consistent:
            expected_state = "integrity-failure"
        elif value.get("timed_out") is True:
            expected_state = "timed-out"
        elif value.get("output_limit_exceeded") is True:
            expected_state = "output-limit-exceeded"
        elif exit_code is None:
            expected_state = "execution-error"
        elif exit_code != 0:
            expected_state = "failed"
        else:
            expected_state = "passed"
        if state != expected_state:
            raise DesignCandidateTestEvidenceError(f"Execution {ordinal} state contradicts process evidence.")
        derived_passed = expected_state == "passed"
    if value.get("passed") is not derived_passed:
        raise DesignCandidateTestEvidenceError(
            f"Execution {ordinal} pass status contradicts trusted process evidence."
        )
    return bool(derived_passed)


def validate_candidate_test_evidence_receipt(
    receipt: Mapping[str, Any],
    *,
    policy_path: Path,
    expected_policy_sha256: str,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Strictly replay bindings and structure without rerunning any test."""

    current_implementation = _assert_loaded_source_current()
    root = _find_repo_root(repo_root)
    (
        policy,
        policy_raw,
        loaded_policy_path,
        candidate_receipt,
        candidate_receipt_path,
        candidate_root,
        website_root,
        candidate_summary,
        candidate_raw,
        commands,
        repository_control,
    ) = _load_policy(
        policy_path,
        expected_policy_sha256=expected_policy_sha256,
        root=root,
    )
    _require_exact_fields(receipt, _RECEIPT_FIELDS, label="Test evidence receipt")
    if receipt.get("schema") != RECEIPT_SCHEMA:
        raise DesignCandidateTestEvidenceError("Test evidence receipt schema is unsupported.")
    _require_identifier(receipt.get("receipt_id"), label="Test evidence receipt id")
    _validate_timestamp(receipt.get("created_at"), nullable=False, label="Receipt timestamp")
    if (
        not isinstance(receipt.get("passed"), bool)
        or receipt.get("local_execution") != LOCAL_EXECUTION_BOUNDARY
        or receipt.get("authority") != EVIDENCE_AUTHORITY
    ):
        raise DesignCandidateTestEvidenceError(
            "Test evidence receipt smuggles authority or worker-declared status."
        )
    implementation = receipt.get("implementation")
    if not isinstance(implementation, Mapping):
        raise DesignCandidateTestEvidenceError("Test evidence receipt implementation binding is missing.")
    _require_exact_fields(
        implementation,
        _IMPLEMENTATION_FIELDS,
        label="Test evidence receipt implementation",
    )
    if dict(implementation) != current_implementation:
        raise DesignCandidateTestEvidenceError(
            "Test evidence receipt implementation binding is stale or malformed."
        )
    policy_binding = receipt.get("policy")
    if not isinstance(policy_binding, Mapping):
        raise DesignCandidateTestEvidenceError("Receipt policy binding is missing.")
    _require_exact_fields(policy_binding, _RECEIPT_POLICY_FIELDS, label="Receipt policy binding")
    policy_file_hash = _bytes_sha256(policy_raw)
    if policy_binding != {
        "path": _relative_to_repo(root, loaded_policy_path),
        "file_sha256": policy_file_hash,
        "json_sha256": _json_sha256(policy),
        "policy_id": policy["policy_id"],
    }:
        raise DesignCandidateTestEvidenceError("Receipt policy binding is stale or malformed.")
    candidate_binding = receipt.get("candidate")
    if not isinstance(candidate_binding, Mapping):
        raise DesignCandidateTestEvidenceError("Receipt candidate binding is missing.")
    _require_exact_fields(
        candidate_binding,
        _RECEIPT_CANDIDATE_FIELDS,
        label="Receipt candidate binding",
    )
    expected_candidate_binding = {
        "receipt_path": _relative_to_repo(root, candidate_receipt_path),
        "receipt_file_sha256": _bytes_sha256(candidate_raw),
        "receipt_json_sha256": _json_sha256(candidate_receipt),
        "root": _relative_to_repo(root, candidate_root),
        "website_path": _relative_to_repo(root, website_root),
        "tree_sha256": candidate_summary["tree_sha256"],
        "file_count": candidate_summary["file_count"],
        "total_bytes": candidate_summary["total_bytes"],
    }
    if candidate_binding != expected_candidate_binding:
        raise DesignCandidateTestEvidenceError("Receipt candidate binding is stale or malformed.")
    selection = receipt.get("selection")
    if not isinstance(selection, Mapping):
        raise DesignCandidateTestEvidenceError("Receipt command selection is missing.")
    _require_exact_fields(selection, _SELECTION_FIELDS, label="Receipt command selection")
    required_ids = policy["required_command_ids"]
    if selection != {
        "command_ids": required_ids,
        "command_ids_sha256": _json_sha256(required_ids),
        "count": len(required_ids),
    }:
        raise DesignCandidateTestEvidenceError("Receipt command selection is incomplete or not policy-bound.")
    raw_executions = receipt.get("executions")
    if (
        not isinstance(raw_executions, list)
        or len(raw_executions) != len(commands)
        or not all(isinstance(item, Mapping) for item in raw_executions)
    ):
        raise DesignCandidateTestEvidenceError("Receipt executions are missing or incomplete.")
    execution_passes = [
        _validate_execution(
            execution,
            ordinal=index,
            command=commands[index - 1],
            policy_file_hash=policy_file_hash,
            candidate_receipt_hash=_bytes_sha256(candidate_raw),
            candidate_tree_hash=str(candidate_summary["tree_sha256"]),
            canonical_website_hash=str(repository_control["canonical_website_tree_sha256"]),
            repository_control_hash=str(repository_control["manifest_sha256"]),
            implementation=current_implementation,
        )
        for index, execution in enumerate(raw_executions, start=1)
    ]
    derived_passed = bool(execution_passes) and all(execution_passes)
    if receipt.get("passed") is not derived_passed or receipt.get("state") != (
        "passed" if derived_passed else "failed"
    ):
        raise DesignCandidateTestEvidenceError("Receipt top-level state contradicts exact process evidence.")
    payload = dict(receipt)
    recorded_payload_hash = payload.pop("receipt_payload_sha256", None)
    if recorded_payload_hash != _json_sha256(payload):
        raise DesignCandidateTestEvidenceError("Receipt payload hash is invalid.")
    return {
        "schema": VERIFICATION_SCHEMA,
        "state": "pass",
        "passed": True,
        "verification_scope": "strict structure and current live bindings only",
        "origin_attested": False,
        "trusted_orchestration_seal_required": True,
        "evidence_passed": derived_passed,
        "release_eligible": False,
        "deployment_authority": "none",
        "policy_file_sha256": _bytes_sha256(policy_raw),
        "policy_json_sha256": _json_sha256(policy),
        "candidate_tree_sha256": candidate_summary["tree_sha256"],
        "canonical_website_tree_sha256": repository_control["canonical_website_tree_sha256"],
        "repository_control_manifest_sha256": repository_control["manifest_sha256"],
        "candidate_test_evidence_sha256": current_implementation["candidate_test_evidence_sha256"],
        "secure_immutable_artifact_sha256": current_implementation["secure_immutable_artifact_sha256"],
        "receipt_payload_sha256": recorded_payload_hash,
    }


def write_candidate_test_evidence_receipt(
    receipt: Mapping[str, Any],
    output_path: Path,
    *,
    policy_path: Path,
    expected_policy_sha256: str,
    repo_root: Path | None = None,
) -> Path:
    """Validate and create one immutable receipt beside, never inside, the site tree."""

    _assert_loaded_source_current()
    try:
        secure_immutable_artifact.validate_no_alternate_stream_path(
            output_path,
            label="Test evidence output path",
        )
    except secure_immutable_artifact.SecureImmutableArtifactError as exc:
        raise DesignCandidateTestEvidenceError(str(exc)) from exc
    root = _find_repo_root(repo_root)
    issued_hash = receipt.get("receipt_payload_sha256")
    with _ISSUED_RECEIPT_LOCK:
        if not isinstance(issued_hash, str) or issued_hash not in _ISSUED_RECEIPT_PAYLOAD_HASHES:
            raise DesignCandidateTestEvidenceError(
                "Receipt writer accepts only a fresh same-process result issued by "
                "execute_candidate_test_evidence; structural validation is not origin attestation."
            )
        _ISSUED_RECEIPT_PAYLOAD_HASHES.remove(issued_hash)
    validate_candidate_test_evidence_receipt(
        receipt,
        policy_path=policy_path,
        expected_policy_sha256=expected_policy_sha256,
        repo_root=root,
    )
    candidate = receipt.get("candidate")
    if not isinstance(candidate, Mapping):
        raise DesignCandidateTestEvidenceError("Receipt candidate binding is missing.")
    candidate_root = _resolve_under(
        root,
        candidate.get("root"),
        label="Staged candidate root",
        directory=True,
    )
    website_root = _resolve_under(
        root,
        candidate.get("website_path"),
        label="Staged candidate website",
        directory=True,
    )
    output = Path(os.path.abspath(output_path if output_path.is_absolute() else root / output_path))
    try:
        output.relative_to(candidate_root)
    except ValueError as exc:
        raise DesignCandidateTestEvidenceError(
            "Test evidence must stay below its staged candidate root."
        ) from exc
    try:
        output.relative_to(website_root)
    except ValueError:
        pass
    else:
        raise DesignCandidateTestEvidenceError(
            "Test evidence must not mutate the hash-bound candidate website tree."
        )
    if output.suffix.lower() != ".json":
        raise DesignCandidateTestEvidenceError("Test evidence output must use .json.")
    parent = _regular_directory(output.parent, label="Test evidence output directory")
    try:
        parent.relative_to(candidate_root)
    except ValueError as exc:
        raise DesignCandidateTestEvidenceError(
            "Test evidence output directory escapes the staged candidate."
        ) from exc
    encoded = (
        json.dumps(
            receipt,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )
    try:
        secure_immutable_artifact.write_new_file(output, encoded)
    except secure_immutable_artifact.SecureImmutableArtifactError as exc:
        raise DesignCandidateTestEvidenceError(
            f"Test evidence receipt could not be created safely: {exc}"
        ) from exc
    return output


def verify_candidate_test_evidence_receipt(
    receipt_path: Path,
    *,
    expected_receipt_file_sha256: str,
    policy_path: Path,
    expected_policy_sha256: str,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Verify an immutable file against an external receipt hash and live bindings."""

    _assert_loaded_source_current()
    try:
        secure_immutable_artifact.validate_no_alternate_stream_path(
            receipt_path,
            label="Test evidence receipt path",
        )
    except secure_immutable_artifact.SecureImmutableArtifactError as exc:
        raise DesignCandidateTestEvidenceError(str(exc)) from exc
    root = _find_repo_root(repo_root)
    expected_receipt_hash = _require_sha256(
        expected_receipt_file_sha256,
        label="Pinned receipt file hash",
    )
    receipt_path = _regular_file(
        receipt_path,
        label="Test evidence receipt",
        single_link=True,
    )
    receipt, raw = _load_json_file(receipt_path, label="Test evidence receipt")
    if _bytes_sha256(raw) != expected_receipt_hash:
        raise DesignCandidateTestEvidenceError(
            "Test evidence receipt does not match its external immutable hash."
        )
    result = validate_candidate_test_evidence_receipt(
        receipt,
        policy_path=policy_path,
        expected_policy_sha256=expected_policy_sha256,
        repo_root=root,
    )
    candidate = receipt.get("candidate")
    if not isinstance(candidate, Mapping):
        raise DesignCandidateTestEvidenceError("Receipt candidate binding is missing.")
    candidate_root = _resolve_under(
        root,
        candidate.get("root"),
        label="Staged candidate root",
        directory=True,
    )
    website_root = _resolve_under(
        root,
        candidate.get("website_path"),
        label="Staged candidate website",
        directory=True,
    )
    try:
        receipt_path.relative_to(candidate_root)
    except ValueError as exc:
        raise DesignCandidateTestEvidenceError(
            "Test evidence receipt escaped its staged candidate root."
        ) from exc
    try:
        receipt_path.relative_to(website_root)
    except ValueError:
        pass
    else:
        raise DesignCandidateTestEvidenceError(
            "Test evidence receipt was written inside the candidate website tree."
        )
    result["receipt_file_sha256"] = expected_receipt_hash
    return result


__all__ = [
    "CANDIDATE_SCHEMA",
    "CANDIDATE_NON_AUTHORITATIVE_AUTHORITY",
    "EVIDENCE_AUTHORITY",
    "LOCAL_EXECUTION_BOUNDARY",
    "MAX_STREAM_BYTES",
    "NODE_TOOLCHAIN_BINDING",
    "NODE_TOOLCHAIN_BINDING_SHA256",
    "POLICY_AUTHORITY",
    "POLICY_SCHEMA",
    "PROCESS_OUTPUTS",
    "RECEIPT_SCHEMA",
    "SUPPORTED_ENGINES",
    "SUPPORTED_VIEWPORT_WIDTHS",
    "VERIFICATION_SCHEMA",
    "DesignCandidateTestEvidenceError",
    "execute_candidate_test_evidence",
    "validate_candidate_test_evidence_receipt",
    "verify_candidate_test_evidence_receipt",
    "write_candidate_test_evidence_receipt",
]
