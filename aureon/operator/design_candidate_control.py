"""Source-bound staging controls for autonomous public-site design candidates.

The public Aureon website is a company record. A coding agent may prepare a
candidate, but it must not silently write a broad diff into website/ and let
later audits guess where the change came from. This module creates a precise
v4 work order, stages a complete candidate below artifacts/website-candidates/,
and validates the resulting diff.

The control intentionally has no apply, release, credential, backup, hosting,
or deployment operation. A validated candidate is still only local evidence;
human visual review and the WebsiteOperator owner-gated lifecycle remain
separate controls.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import ipaddress
import json
import math
import os
import re
import shutil
import stat
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from aureon.operator import secure_immutable_artifact
from aureon.operator.design_candidate_claim_surface import (
    DesignCandidateClaimSurfaceError,
    evaluate_candidate_claim_surface,
)
from aureon.operator.design_candidate_source_closure import (
    DesignCandidateSourceClosureError,
    build_source_closure,
    require_source_closure_contract,
    verify_source_closure,
)
from aureon.operator.live_surface_reconciliation import (
    LiveSurfaceReconciliationError,
    validate_live_surface_reconciliation,
)
from aureon.operator.owner_source_reconciliation import (
    OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_SCHEMA,
    OwnerSourceReconciliationError,
    validate_owner_source_reconciliation,
)
from aureon.operator.public_claim_evidence import (
    PublicClaimEvidenceError,
    audit_public_claim_evidence_file,
)

WORK_ORDER_SCHEMA = "aureon.design-work-order.v4"
CANDIDATE_SCHEMA = "aureon.design-candidate.v1"
VERIFICATION_SCHEMA = "aureon.design-candidate-verification.v1"
VALIDATION_INPUT_SCHEMA = "aureon.design-candidate-validation-input.v1"
DEFAULT_CANDIDATE_ROOT = Path("artifacts/website-candidates")
DEFAULT_OPERATOR_ARTIFACT_ROOT = Path("artifacts/website-operator")
DEFAULT_VERIFIED_LIVE_BACKUP_ROOT = Path("artifacts/homepl-backups")
DEFAULT_OWNER_RECONCILIATION_ROOT = DEFAULT_OPERATOR_ARTIFACT_ROOT / "owner-source-reconciliations"
DEFAULT_CLAIM_REGISTER = Path("data/website_operator/public_claim_evidence_register.v1.json")
DEFAULT_EDITORIAL_PROVENANCE_MANIFEST = Path("data/website_operator/editorial_asset_provenance.v1.json")
DEFAULT_OPERATOR_CONFIG = Path("aureon/operator/website_operator.defaults.json")
DEFAULT_EDITORIAL_IMPORT_RECEIPT_NAME = "editorial-asset-import-receipt.v1.json"
DEFAULT_VALIDATION_INPUT_NAME = "candidate-validation-input.v1.json"
EDITORIAL_IMPORT_RECEIPT_SCHEMA = "aureon.design-editorial-asset-candidate-import.v1"
EDITORIAL_IMPORT_VERIFICATION_SCHEMA = "aureon.design-editorial-asset-candidate-import-verification.v1"
EDITORIAL_SURFACE_BINDING_SCHEMA = "aureon.design-editorial-asset-surface-binding.v1"

NON_AUTHORITATIVE_AUTHORITY = {
    "scope": "local staged website-candidate provenance and diff control",
    "canonical_website_mutation": "never by this control or a design agent",
    "release_eligible": False,
    "package_authority": "none",
    "deployment_authority": "none",
    "credential_access": "none",
    "human_visual_acceptance": "required for material brand changes",
    "release_authority": "WebsiteOperator owner gate only",
}
VALIDATION_INPUT_AUTHORITY = {
    "scope": "create-once local input provenance for one staged candidate validation",
    "release_eligible": False,
    "package_authority": "none",
    "deployment_authority": "none",
    "credential_access": "none",
    "wall_clock_attestation": "none",
    "input_origin_attested": False,
}
NEXT_CANDIDATE_GATE = (
    "Capture source-bound staged browser evidence and obtain separate named manual pixel review "
    "and human visual acceptance; this staged candidate cannot apply, package, or deploy itself."
)
CANDIDATE_CHECK_IDS = (
    "work-order-current",
    "candidate-workspace",
    "candidate-manifest",
    "candidate-diff",
    "exact-scope",
    "no-public-file-removal",
    "blocked-files",
    "strict-text-integrity",
    "remote-origin-diff",
    "secret-scan",
    "trusted-binary-import-replay",
    "trusted-editorial-surface-replay",
    "claim-impact-declarations",
    "material-claim-source-classification",
    "staged-claim-register",
    "claim-surface-capsule",
    "candidate-manifest-stable",
)

ALLOWED_FILE_NAMES = frozenset({".htaccess"})
ALLOWED_EXTENSIONS = frozenset(
    {
        ".css",
        ".gif",
        ".html",
        ".ico",
        ".jpeg",
        ".jpg",
        ".js",
        ".json",
        ".png",
        ".svg",
        ".txt",
        ".webmanifest",
        ".webp",
        ".woff",
        ".woff2",
        ".xml",
    }
)
BLOCKED_FILE_NAMES = frozenset({".env", ".env1", ".htaccess", "id_rsa", "id_ed25519"})
BLOCKED_EXTENSIONS = frozenset({".env", ".key", ".pem", ".pfx", ".p12"})
DECLARATION_REQUIRED_EXTENSIONS = frozenset(
    {".css", ".html", ".js", ".json", ".svg", ".txt", ".webmanifest", ".xml"}
)
CONTROLLED_TEXT_EXTENSIONS = DECLARATION_REQUIRED_EXTENSIONS
CONTROLLED_BINARY_EXTENSIONS = frozenset(ALLOWED_EXTENSIONS - CONTROLLED_TEXT_EXTENSIONS)
TRUSTED_EDITORIAL_IMPORT_EXTENSIONS = frozenset({".webp"})
CLAIM_IMPACT_CLASSIFICATIONS = frozenset({"no-material-claim-change", "material-claim-change"})
MAX_AUTONOMOUS_ALLOWED_PATHS = 12

WORK_ORDER_FIELDS = frozenset(
    {
        "schema",
        "created_at",
        "run_id",
        "goal",
        "routes",
        "allowed_paths",
        "allowed_new_origins",
        "live_reconciliation",
        "baseline",
        "claim_control",
        "editorial_asset_control",
        "test_policy",
        "candidate_layout",
        "authority",
    }
)
CANDIDATE_RECEIPT_FIELDS = frozenset(
    {
        "schema",
        "validated_at",
        "state",
        "passed",
        "release_eligible",
        "deployment_authority",
        "authority",
        "validation_input",
        "source_closure",
        "work_order",
        "candidate",
        "changes",
        "claims",
        "claim_surface",
        "checks",
        "next_gate",
    }
)
VALIDATION_INPUT_FIELDS = frozenset(
    {
        "schema",
        "issued_at",
        "work_order",
        "source_closure",
        "claim_impacts",
        "claim_surface",
        "authority",
        "payload_sha256",
    }
)
VALIDATION_INPUT_BINDING_FIELDS = frozenset(
    {
        "path",
        "file_sha256",
        "json_sha256",
        "payload_sha256",
    }
)
CANDIDATE_WORK_ORDER_BINDING_FIELDS = frozenset(
    {
        "run_id",
        "path",
        "file_sha256",
        "sha256",
        "baseline_tree_sha256",
    }
)
CANDIDATE_BINDING_FIELDS = frozenset(
    {
        "root",
        "website_path",
        "tree_sha256",
        "file_count",
        "total_bytes",
    }
)
EDITORIAL_ASSET_CONTROL_FIELDS = frozenset(
    {
        "policy",
        "receipt_path",
        "receipt_schema",
        "verification_schema",
        "binary_extensions",
        "trusted_import_extensions",
        "unreceipted_binary_diff",
        "replay_verification_required",
        "provenance_manifest_path",
        "provenance_manifest_sha256",
        "surface_binding_verification_required",
    }
)
BASELINE_FIELDS = frozenset({"tree_sha256", "file_count", "total_bytes", "files"})
MANIFEST_ROW_FIELDS = frozenset({"path", "sha256", "bytes"})
CLAIM_CONTROL_FIELDS = frozenset(
    {
        "register_path",
        "register_sha256",
        "bound_source_paths",
        "changed_html_or_json_requires_declaration",
        "bound_source_change_requires_staged_register_refresh",
    }
)
TEST_POLICY_FIELDS = frozenset({"path", "sha256"})
CANDIDATE_LAYOUT_FIELDS = frozenset({"root", "website_path", "staged_claim_register_path"})
LIVE_RECONCILIATION_FIELDS = frozenset(
    {
        "receipt_path",
        "receipt_sha256",
        "state",
        "selected_tree_sha256",
        "covered_local_paths",
        "current_local_paths",
        "owner_source_reconciliation",
    }
)
RETAINED_OWNER_RECONCILIATION_FIELDS = frozenset(
    {
        "required",
        "decision_path",
        "decision_sha256",
        "backup_receipt_path",
        "backup_receipt_sha256",
        "validation_state",
    }
)
VERIFIED_OWNER_RECONCILIATION_FIELDS = frozenset(
    {
        *RETAINED_OWNER_RECONCILIATION_FIELDS,
        "decision_schema",
        "source_selection",
        "candidate_source",
    }
)

_SHA256 = re.compile(r"[A-F0-9]{64}")
_RUN_ID = re.compile(r"[a-z0-9][a-z0-9._-]{2,80}")
_SECRET_PATTERNS = (
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("openai-api-key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("github-fine-grained-token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{12,}\b")),
    ("stripe-secret-key", re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9]{16,}\b")),
)
_URL_REFERENCE_PATTERN = re.compile(r"(?i)(?:https?:)?//[^\s\"'<>\\)]+")
_EMBEDDED_MEDIA_DATA_PATTERN = re.compile(
    r"(?i)\bdata:(?:audio|font|image|video)/[^,;\s]+(?:;[^,\s]*)*;base64,"
)
_VERIFIED_LIVE_BACKUP_SOURCE_FIELDS = frozenset(
    {
        "kind",
        "root",
        "manifest_path",
        "manifest_sha256",
        "tree_sha256",
        "baseline_tree_sha256",
        "file_count",
        "total_bytes",
        "remote_root",
    }
)


class DesignCandidateControlError(ValueError):
    """A work order or staged candidate is unsafe, stale, or malformed."""


def _utc_iso(value: datetime | None = None) -> str:
    return (value or datetime.now(UTC)).astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_utc_z_timestamp(value: object, *, label: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise DesignCandidateControlError(f"{label} must be a canonical UTC timestamp ending in Z.")
    try:
        parsed = datetime.fromisoformat(f"{value[:-1]}+00:00")
    except ValueError as exc:
        raise DesignCandidateControlError(f"{label} must be a valid UTC timestamp.") from exc
    if parsed.utcoffset() != UTC.utcoffset(parsed) or _utc_iso(parsed) != value:
        raise DesignCandidateControlError(f"{label} must use canonical UTC ISO-8601 form.")
    return parsed


def _find_repo_root(start: Path | None = None) -> Path:
    candidate = (start or Path.cwd()).resolve()
    for root in (candidate, *candidate.parents):
        if (root / "pyproject.toml").is_file() and (root / "aureon").is_dir():
            return root
    raise DesignCandidateControlError(
        "Could not locate an Aureon repository with pyproject.toml and aureon/."
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _canonical_json_bytes(value: object) -> bytes:
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise DesignCandidateControlError(
            "Candidate control JSON must contain only finite standard JSON values."
        ) from exc
    return encoded.encode("utf-8")


def _json_hash(value: object) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest().upper()


def _strict_json_equal(left: object, right: object) -> bool:
    try:
        return _canonical_json_bytes(left) == _canonical_json_bytes(right)
    except DesignCandidateControlError:
        return False


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise DesignCandidateControlError(f"Duplicate JSON key is forbidden: {key}")
        value[key] = item
    return value


def _reject_json_constant(value: str) -> None:
    raise DesignCandidateControlError(f"Non-finite JSON number is forbidden: {value}")


def _strict_json_object(raw: bytes, *, label: str) -> dict[str, Any]:
    try:
        decoded = raw.decode("utf-8-sig")
        value = json.loads(
            decoded,
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except UnicodeDecodeError as exc:
        raise DesignCandidateControlError(f"{label} is not strict UTF-8 JSON.") from exc
    except json.JSONDecodeError as exc:
        raise DesignCandidateControlError(f"{label} is not valid JSON.") from exc
    if not isinstance(value, dict):
        raise DesignCandidateControlError(f"{label} must contain one JSON object.")
    return value


def _safe_relative_path(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DesignCandidateControlError("A candidate path must be a non-empty relative path.")
    if ":" in value:
        raise DesignCandidateControlError(f"Candidate paths may not address alternate data streams: {value}")
    normalised = value.replace("\\", "/").lstrip("/")
    path = Path(normalised)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise DesignCandidateControlError(f"Unsafe candidate path: {value}")
    return path.as_posix()


def _safe_run_id(value: object) -> str:
    if not isinstance(value, str) or not _RUN_ID.fullmatch(value):
        raise DesignCandidateControlError(
            "Candidate run id must be a stable lowercase slug (3-81 characters)."
        )
    return value


def _safe_route(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DesignCandidateControlError("A work-order route must be a non-empty local route.")
    parsed = urlparse(value.strip())
    if parsed.scheme or parsed.netloc or parsed.params or parsed.query or parsed.fragment:
        raise DesignCandidateControlError("A work-order route must be a local path without an origin.")
    path = parsed.path
    if not path.startswith("/") or "//" in path or ".." in Path(path).parts:
        raise DesignCandidateControlError(f"Unsafe work-order route: {value}")
    return path


def _safe_origin(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DesignCandidateControlError("An allowed origin must be a non-empty HTTPS origin.")
    parsed = urlparse(value.strip())
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.path not in {"", "/"}
        or parsed.params
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise DesignCandidateControlError(
            "Allowed new origins must be canonical HTTPS origins without a path."
        )
    try:
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise DesignCandidateControlError(
            "Allowed new origins must have a valid HTTPS host and port."
        ) from exc
    if not hostname:
        raise DesignCandidateControlError("Allowed new origins must declare a hostname.")
    host = hostname.lower().rstrip(".")
    if host in {"localhost", "localhost.localdomain"} or host.endswith(
        (".localhost", ".local", ".internal", ".invalid", ".test")
    ):
        raise DesignCandidateControlError("Allowed new origins must use a public hostname.")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise DesignCandidateControlError("Allowed new origins may not use private or loopback addresses.")
    host_port = host if port in {None, 443} else f"{host}:{port}"
    return f"https://{host_port}"


def _relative_to_repo(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise DesignCandidateControlError("A control path must remain within the Aureon repository.") from exc


def _resolve_under(root: Path, relative: object, *, label: str) -> Path:
    safe = _safe_relative_path(relative)
    candidate = (root / safe).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise DesignCandidateControlError(f"{label} escapes its approved root: {relative}") from exc
    return candidate


def _is_link_or_reparse_point(path: Path) -> bool:
    """Detect symbolic links and Windows junctions without following them."""

    try:
        details = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(details.st_mode) or bool(
        getattr(details, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def _regular_single_link_file(path: Path, *, label: str) -> Path:
    """Require one lexical ordinary file without link or reparse traversal."""

    try:
        secure_immutable_artifact.validate_no_alternate_stream_path(path, label=label)
    except secure_immutable_artifact.SecureImmutableArtifactError as exc:
        raise DesignCandidateControlError(str(exc)) from exc
    lexical = Path(os.path.abspath(path))
    for component in (lexical, *lexical.parents):
        if not component.exists() and not component.is_symlink():
            continue
        try:
            details = component.lstat()
        except OSError as exc:
            raise DesignCandidateControlError(f"{label} could not be inspected safely.") from exc
        if _is_link_or_reparse_point(component):
            raise DesignCandidateControlError(f"{label} may not traverse a link or reparse point.")
        if component == lexical and not stat.S_ISREG(details.st_mode):
            raise DesignCandidateControlError(f"{label} must be an existing regular file.")
    if not lexical.is_file():
        raise DesignCandidateControlError(f"{label} must be an existing regular file.")
    try:
        details = lexical.stat()
    except OSError as exc:
        raise DesignCandidateControlError(f"{label} could not be inspected safely.") from exc
    if int(details.st_nlink) != 1:
        raise DesignCandidateControlError(f"{label} must have exactly one hard link.")
    return lexical


def _regular_directory(path: Path, *, label: str) -> Path:
    """Require one lexical directory without link or reparse traversal."""

    lexical = Path(os.path.abspath(path))
    for component in (lexical, *lexical.parents):
        if not component.exists() and not component.is_symlink():
            continue
        try:
            details = component.lstat()
        except OSError as exc:
            raise DesignCandidateControlError(f"{label} could not be inspected safely.") from exc
        if _is_link_or_reparse_point(component):
            raise DesignCandidateControlError(f"{label} may not traverse a link or reparse point.")
        if component == lexical and not stat.S_ISDIR(details.st_mode):
            raise DesignCandidateControlError(f"{label} must be an existing regular directory.")
    if not lexical.is_dir():
        raise DesignCandidateControlError(f"{label} must be an existing regular directory.")
    return lexical


def _bounded_tree_files(root: Path) -> list[Path]:
    """Enumerate one tree without following links, junctions, or root escapes."""

    lexical_root = root.absolute()
    if _is_link_or_reparse_point(lexical_root) or not lexical_root.is_dir():
        raise DesignCandidateControlError(f"Website tree must be a regular non-link directory: {root}")
    try:
        real_root = lexical_root.resolve(strict=True)
    except OSError as exc:
        raise DesignCandidateControlError(f"Website tree cannot be resolved: {root}") from exc

    directories = [lexical_root]
    files: list[Path] = []
    while directories:
        directory = directories.pop()
        try:
            directory.absolute().relative_to(lexical_root)
            directory.resolve(strict=True).relative_to(real_root)
        except (OSError, ValueError) as exc:
            raise DesignCandidateControlError(
                f"Website or candidate tree path escapes its lexical or real root: {directory}"
            ) from exc
        try:
            entries = sorted(os.scandir(directory), key=lambda item: item.name)
        except OSError as exc:
            raise DesignCandidateControlError(
                f"Website or candidate tree cannot be enumerated safely: {directory}"
            ) from exc
        for entry in entries:
            path = Path(entry.path)
            if _is_link_or_reparse_point(path):
                raise DesignCandidateControlError(
                    f"Website or candidate trees must not contain symbolic links or reparse points: {path}"
                )
            try:
                path.absolute().relative_to(lexical_root)
                path.resolve(strict=True).relative_to(real_root)
                details = path.lstat()
            except (OSError, ValueError) as exc:
                raise DesignCandidateControlError(
                    f"Website or candidate tree path escapes its lexical or real root: {path}"
                ) from exc
            if stat.S_ISDIR(details.st_mode):
                directories.append(path)
            elif stat.S_ISREG(details.st_mode):
                files.append(path)
            else:
                raise DesignCandidateControlError(
                    f"Website or candidate trees may contain only regular files and directories: {path}"
                )
    return sorted(files, key=lambda item: item.relative_to(lexical_root).as_posix())


def _file_manifest(root: Path) -> list[dict[str, Any]]:
    if not root.is_dir():
        raise DesignCandidateControlError(f"Website tree does not exist: {root}")
    rows: list[dict[str, Any]] = []
    lexical_root = root.absolute()
    for path in _bounded_tree_files(lexical_root):
        if path.stat().st_nlink != 1:
            raise DesignCandidateControlError(f"Website or candidate files must not share hard links: {path}")
        rows.append(
            {
                "path": path.relative_to(lexical_root).as_posix(),
                "sha256": _sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    return rows


def _manifest_hash(rows: Sequence[Mapping[str, Any]]) -> str:
    normalised = [
        {
            "path": str(row.get("path") or ""),
            "sha256": str(row.get("sha256") or "").upper(),
            "bytes": int(row.get("bytes") or 0),
        }
        for row in rows
    ]
    return _json_hash(normalised)


def _manifest_index(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or frozenset(row) != MANIFEST_ROW_FIELDS:
            raise DesignCandidateControlError(
                "Manifest row fields must exactly match path, sha256, and bytes."
            )
        path = _safe_relative_path(row.get("path"))
        if row.get("path") != path:
            raise DesignCandidateControlError(f"Manifest path is not canonical: {row.get('path')}")
        sha256 = str(row.get("sha256") or "").upper()
        if row.get("sha256") != sha256 or not _SHA256.fullmatch(sha256):
            raise DesignCandidateControlError(f"Manifest hash is invalid for {path}.")
        raw_bytes = row.get("bytes")
        if type(raw_bytes) is not int or raw_bytes < 0:
            raise DesignCandidateControlError(f"Manifest byte count is invalid for {path}.")
        if path in index:
            raise DesignCandidateControlError(f"Manifest path is duplicated: {path}.")
        index[path] = {"path": path, "sha256": sha256, "bytes": raw_bytes}
    return index


def _tree_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    index = _manifest_index(rows)
    ordered = [index[path] for path in sorted(index)]
    return {
        "tree_sha256": _manifest_hash(ordered),
        "file_count": len(ordered),
        "total_bytes": sum(int(row["bytes"]) for row in ordered),
        "files": ordered,
    }


def _website_operator_tree_hash(root: Path, rows: Sequence[Mapping[str, Any]]) -> str:
    """Recompute the exact WebsiteOperator verified-backup tree contract."""

    source_root = root.resolve(strict=True)
    digest = hashlib.sha256()
    index = _manifest_index(rows)
    for relative in sorted(index, key=lambda value: (root / value).resolve().as_posix().lower()):
        path = (root / relative).resolve(strict=True)
        try:
            path.relative_to(source_root)
        except ValueError as exc:
            raise DesignCandidateControlError(
                f"Verified backup manifest path escapes its source root: {relative}"
            ) from exc
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(index[relative]["sha256"]).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest().upper()


def _backup_manifest_rows(manifest_path: Path) -> list[dict[str, Any]]:
    """Read the exact V3 backup CSV contract without accepting path aliases."""

    manifest = _regular_single_link_file(manifest_path, label="Verified backup manifest")
    try:
        with manifest.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if tuple(reader.fieldnames or ()) != ("Path", "Bytes", "Sha256"):
                raise DesignCandidateControlError(
                    "Verified backup manifest must use the exact V3 Path,Bytes,Sha256 columns."
                )
            raw_rows = list(reader)
    except UnicodeError as exc:
        raise DesignCandidateControlError("Verified backup manifest must be valid UTF-8 text.") from exc
    if not raw_rows:
        raise DesignCandidateControlError("Verified backup manifest must not be empty.")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    seen_casefold: set[str] = set()
    for row in raw_rows:
        raw_path = str(row.get("Path", ""))
        relative = _safe_relative_path(raw_path)
        if raw_path != relative:
            raise DesignCandidateControlError(f"Verified backup manifest path is not canonical: {raw_path}")
        if relative in seen or relative.casefold() in seen_casefold:
            raise DesignCandidateControlError(
                f"Verified backup manifest path is duplicated or case-colliding: {relative}"
            )
        seen.add(relative)
        seen_casefold.add(relative.casefold())
        try:
            byte_count = int(str(row.get("Bytes", "")))
        except ValueError as exc:
            raise DesignCandidateControlError(
                f"Verified backup byte count is invalid for {relative}."
            ) from exc
        if byte_count < 0:
            raise DesignCandidateControlError(f"Verified backup byte count is invalid for {relative}.")
        sha256 = str(row.get("Sha256", "")).upper()
        if not _SHA256.fullmatch(sha256):
            raise DesignCandidateControlError(f"Verified backup SHA-256 is invalid for {relative}.")
        rows.append({"path": relative, "bytes": byte_count, "sha256": sha256})
    return rows


def _paths_overlap(first: Path, second: Path) -> bool:
    first_resolved = first.resolve()
    second_resolved = second.resolve()
    try:
        first_resolved.relative_to(second_resolved)
        return True
    except ValueError:
        pass
    try:
        second_resolved.relative_to(first_resolved)
        return True
    except ValueError:
        return False


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise DesignCandidateControlError(f"{label} does not exist: {path}") from exc
    return _strict_json_object(raw, label=f"{label}: {path}")


def _artifact_json_path(root: Path, value: object, *, allowed_root: Path, label: str) -> Path:
    if not isinstance(value, Path):
        raise DesignCandidateControlError(f"{label} must be a JSON path.")
    candidate = value if value.is_absolute() else root / value
    resolved = candidate.resolve()
    try:
        resolved.relative_to(allowed_root.resolve())
    except ValueError as exc:
        raise DesignCandidateControlError(
            f"{label} must remain below {allowed_root.relative_to(root).as_posix()}/."
        ) from exc
    if resolved.suffix.lower() != ".json":
        raise DesignCandidateControlError(f"{label} must use a .json filename.")
    if not resolved.is_file():
        raise DesignCandidateControlError(f"{label} does not exist: {resolved}")
    return resolved


def _strict_artifact_json_path(
    root: Path,
    value: Path,
    *,
    allowed_root: Path,
    label: str,
) -> Path:
    """Resolve one evidence file while rejecting aliases and hard links."""

    lexical = value if value.is_absolute() else root / value
    inspected = _regular_single_link_file(lexical, label=label)
    resolved = inspected.resolve(strict=True)
    try:
        resolved.relative_to(allowed_root.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise DesignCandidateControlError(
            f"{label} must remain below {allowed_root.relative_to(root).as_posix()}/."
        ) from exc
    if resolved.suffix.lower() != ".json":
        raise DesignCandidateControlError(f"{label} must use a .json filename.")
    return resolved


def _validated_live_backup_source(
    *,
    root: Path,
    decision: Mapping[str, Any],
    decision_path: Path,
    backup: Mapping[str, Any],
    backup_path: Path,
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    """Revalidate an owner-selected live backup down to every source byte."""

    if decision.get("schema") != OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_SCHEMA:
        raise DesignCandidateControlError(
            "Verified-live-backup staging requires the exact owner v2 source decision."
        )
    if decision.get("source_selection") != "use-verified-live-backup":
        raise DesignCandidateControlError(
            "Owner v2 source decision does not select the verified live backup."
        )
    _regular_single_link_file(decision_path, label="Owner source-reconciliation decision")
    _regular_single_link_file(backup_path, label="Verified backup receipt")

    raw_source = backup.get("backup_directory")
    raw_manifest = backup.get("manifest")
    if not isinstance(raw_source, str) or not Path(raw_source).is_absolute():
        raise DesignCandidateControlError("Verified backup receipt must name an absolute backup directory.")
    if not isinstance(raw_manifest, str) or not Path(raw_manifest).is_absolute():
        raise DesignCandidateControlError("Verified backup receipt must name an absolute backup manifest.")
    source_root = _regular_directory(Path(raw_source), label="Verified backup directory")
    manifest_path = _regular_single_link_file(
        Path(raw_manifest),
        label="Verified backup manifest",
    )
    artifact_root = (root / "artifacts").resolve()
    verified_backup_root = (root / DEFAULT_VERIFIED_LIVE_BACKUP_ROOT).resolve()
    try:
        source_root.resolve(strict=True).relative_to(verified_backup_root)
        manifest_path.resolve(strict=True).relative_to(artifact_root)
    except ValueError as exc:
        raise DesignCandidateControlError(
            "Verified live-backup directory must stay below artifacts/homepl-backups/ "
            "and its manifest must stay below artifacts/."
        ) from exc
    if source_root.resolve() == (root / "website").resolve() or _paths_overlap(source_root, root / "website"):
        raise DesignCandidateControlError(
            "Verified live-backup source must be separate from the canonical website tree."
        )
    if _paths_overlap(source_root, manifest_path):
        raise DesignCandidateControlError(
            "Verified backup manifest must remain outside the copied document-root tree."
        )
    for evidence_path, label in (
        (decision_path, "owner decision"),
        (backup_path, "backup receipt"),
    ):
        if _paths_overlap(source_root, evidence_path):
            raise DesignCandidateControlError(
                f"Verified backup {label} must remain outside the copied document-root tree."
            )

    manifest_sha256 = _sha256_file(manifest_path)
    if (
        backup.get("state") != "verified-backup"
        or backup.get("schema") != "aureon.website-operator.backup.v1"
        or backup.get("remote_root") != "/"
        or backup.get("method") not in {"homepl-ftps", "homepl-webftp"}
        or backup.get("source_assertion") != "Authenticated Home.pl document-root download"
        or backup.get("backup_directory") != str(source_root)
        or backup.get("manifest") != str(manifest_path)
        or backup.get("manifest_sha256") != manifest_sha256
        or decision.get("backup_directory") != str(source_root)
        or decision.get("backup_manifest") != str(manifest_path)
        or decision.get("backup_manifest_sha256") != manifest_sha256
    ):
        raise DesignCandidateControlError(
            "Verified live-backup receipt, manifest, source root, or owner binding changed."
        )

    declared_rows = _backup_manifest_rows(manifest_path)
    declared_index = _manifest_index(declared_rows)
    actual_rows = _file_manifest(source_root)
    actual_index = _manifest_index(actual_rows)
    if actual_index != declared_index:
        raise DesignCandidateControlError(
            "Verified backup directory no longer exactly matches every manifest path, byte count, and SHA-256."
        )
    blocked_source_paths = sorted(
        relative for relative in actual_index if not _allowed_verified_backup_source_file(relative)
    )
    if blocked_source_paths:
        raise DesignCandidateControlError(
            "Verified backup contains blocked credential-bearing, executable, or server-only paths: "
            + ", ".join(blocked_source_paths)
        )
    secret_findings: list[tuple[str, list[str]]] = []
    for relative in sorted(actual_index):
        patterns = _secret_hits(source_root / relative)
        if patterns:
            secret_findings.append((relative, patterns))
    if secret_findings:
        descriptions = [f"{relative} ({', '.join(patterns)})" for relative, patterns in secret_findings]
        raise DesignCandidateControlError(
            "Verified backup contains private-key or API-key credential patterns: " + "; ".join(descriptions)
        )
    file_count = len(declared_rows)
    total_bytes = sum(int(row["bytes"]) for row in declared_rows)
    if backup.get("file_count") != file_count or backup.get("total_bytes") != total_bytes:
        raise DesignCandidateControlError("Verified backup receipt file count or byte count changed.")
    receipt_tree = str(backup.get("tree_sha256") or "")
    calculated_tree = _website_operator_tree_hash(source_root, declared_rows)
    if (
        not _SHA256.fullmatch(receipt_tree)
        or calculated_tree != receipt_tree
        or decision.get("backup_tree_sha256") != receipt_tree
    ):
        raise DesignCandidateControlError(
            "Verified backup tree hash no longer matches its receipt and owner decision."
        )
    baseline = _tree_summary(actual_rows)
    source_binding = {
        "kind": "verified-live-backup",
        "root": str(source_root),
        "manifest_path": str(manifest_path),
        "manifest_sha256": manifest_sha256,
        "tree_sha256": receipt_tree,
        "baseline_tree_sha256": baseline["tree_sha256"],
        "file_count": file_count,
        "total_bytes": total_bytes,
        "remote_root": "/",
    }
    return source_root, baseline, source_binding


def _route_to_local_html_path(value: object) -> str:
    """Map a declared public route onto the local static HTML record it senses."""

    route = _safe_route(value)
    if route == "/":
        return "index.html"
    relative = route.lstrip("/")
    if route.endswith("/"):
        relative = f"{relative}index.html"
    elif Path(relative).suffix.lower() != ".html":
        relative = f"{relative}/index.html"
    return _safe_relative_path(relative)


def _reconciliation_binding(
    *,
    root: Path,
    routes: Sequence[str],
    reconciliation_receipt: Path,
    owner_source_decision: Path | None,
    backup_receipt: Path | None,
) -> dict[str, Any]:
    """Bind a current public-surface observation before candidate staging.

    A semantically aligned observation may proceed without an owner selection.
    A drifted observation requires an independently supplied owner decision and
    a verified backup.  The function never merges, copies, applies or uploads
    either source record.
    """

    if not routes:
        raise DesignCandidateControlError(
            "A reconciled autonomous candidate work order must name at least one public route."
        )
    receipt_path = _artifact_json_path(
        root,
        reconciliation_receipt,
        allowed_root=root / DEFAULT_OPERATOR_ARTIFACT_ROOT,
        label="Live-surface reconciliation receipt",
    )
    receipt = _read_json(receipt_path, label="Live-surface reconciliation receipt")
    try:
        validate_live_surface_reconciliation(receipt)
    except LiveSurfaceReconciliationError as exc:
        raise DesignCandidateControlError(f"Live-surface reconciliation receipt is invalid: {exc}") from exc
    state = str(receipt.get("state") or "")
    canonical = receipt.get("canonical")
    if not isinstance(canonical, Mapping):
        raise DesignCandidateControlError("Live-surface reconciliation has no canonical snapshot.")
    selected_tree_sha256 = str(canonical.get("selected_tree_sha256") or "")
    rows = receipt.get("routes")
    if not isinstance(rows, list):
        raise DesignCandidateControlError("Live-surface reconciliation has no route evidence.")
    observed = {
        str(row.get("local_path")): row
        for row in rows
        if isinstance(row, Mapping) and isinstance(row.get("local_path"), str)
    }
    covered_paths = sorted({_route_to_local_html_path(route) for route in routes})
    current_matches: list[str] = []
    for local_path in covered_paths:
        row = observed.get(local_path)
        if not isinstance(row, Mapping):
            raise DesignCandidateControlError(
                f"Live-surface reconciliation does not cover candidate route source: {local_path}"
            )
        local = row.get("local")
        if not isinstance(local, Mapping):
            raise DesignCandidateControlError(
                f"Live-surface reconciliation lacks a local snapshot for: {local_path}"
            )
        expected_sha256 = str(local.get("sha256") or "")
        source = root / "website" / local_path
        if not source.is_file() or _sha256_file(source) != expected_sha256:
            raise DesignCandidateControlError(
                f"Canonical route changed after live-surface reconciliation: {local_path}"
            )
        current_matches.append(local_path)

    binding: dict[str, Any] = {
        "receipt_path": _relative_to_repo(root, receipt_path),
        "receipt_sha256": _sha256_file(receipt_path),
        "state": state,
        "selected_tree_sha256": selected_tree_sha256,
        "covered_local_paths": covered_paths,
        "current_local_paths": current_matches,
        "owner_source_reconciliation": {
            "required": state == "live-drift-detected",
            "decision_path": "",
            "decision_sha256": "",
            "backup_receipt_path": "",
            "backup_receipt_sha256": "",
            "validation_state": "not-required-semantic-alignment",
        },
    }
    if state == "live-surface-semantically-aligned" and receipt.get("passed") is True:
        if owner_source_decision is not None or backup_receipt is not None:
            raise DesignCandidateControlError(
                "Owner source-selection evidence is only valid for an observed live drift."
            )
        return binding
    if state != "live-drift-detected":
        raise DesignCandidateControlError(
            "Live-surface reconciliation is incomplete; no autonomous candidate baseline may be assumed."
        )
    if owner_source_decision is None or backup_receipt is None:
        raise DesignCandidateControlError(
            "Observed live drift requires both an owner source-reconciliation decision and a verified backup receipt."
        )
    decision_path = _artifact_json_path(
        root,
        owner_source_decision,
        allowed_root=root / DEFAULT_OWNER_RECONCILIATION_ROOT,
        label="Owner source-reconciliation decision",
    )
    backup_path = _artifact_json_path(
        root,
        backup_receipt,
        allowed_root=root / DEFAULT_OPERATOR_ARTIFACT_ROOT,
        label="Verified backup receipt",
    )
    decision = _read_json(decision_path, label="Owner source-reconciliation decision")
    backup = _read_json(backup_path, label="Verified backup receipt")
    live_backup_selected = (
        decision.get("schema") == OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_SCHEMA
        and decision.get("source_selection") == "use-verified-live-backup"
    )
    if live_backup_selected:
        strict_receipt_path = _strict_artifact_json_path(
            root,
            reconciliation_receipt,
            allowed_root=root / DEFAULT_OPERATOR_ARTIFACT_ROOT,
            label="Live-surface reconciliation receipt",
        )
        strict_decision_path = _strict_artifact_json_path(
            root,
            owner_source_decision,
            allowed_root=root / DEFAULT_OWNER_RECONCILIATION_ROOT,
            label="Owner source-reconciliation decision",
        )
        strict_backup_path = _strict_artifact_json_path(
            root,
            backup_receipt,
            allowed_root=root / DEFAULT_OPERATOR_ARTIFACT_ROOT,
            label="Verified backup receipt",
        )
        if (
            strict_receipt_path != receipt_path
            or strict_decision_path != decision_path
            or strict_backup_path != backup_path
        ):
            raise DesignCandidateControlError(
                "Verified-live-backup evidence path changed during strict resolution."
            )
    try:
        decision_validation = validate_owner_source_reconciliation(
            decision,
            reconciliation_receipt=receipt,
            reconciliation_receipt_sha256=_sha256_file(receipt_path),
            backup_receipt=backup,
            backup_receipt_sha256=_sha256_file(backup_path),
        )
    except OwnerSourceReconciliationError as exc:
        raise DesignCandidateControlError(f"Owner source-reconciliation decision is invalid: {exc}") from exc
    if decision_validation.get("passed") is not True:
        failed = [
            str(check.get("id"))
            for check in decision_validation.get("checks", [])
            if isinstance(check, Mapping) and check.get("passed") is not True
        ]
        raise DesignCandidateControlError(
            "Owner source-reconciliation decision is not currently valid: " + ", ".join(failed)
        )
    owner_binding: dict[str, Any] = {
        "required": True,
        "decision_path": _relative_to_repo(root, decision_path),
        "decision_sha256": _sha256_file(decision_path),
        "backup_receipt_path": _relative_to_repo(root, backup_path),
        "backup_receipt_sha256": _sha256_file(backup_path),
        "validation_state": str(decision_validation.get("state") or "blocked"),
    }
    if live_backup_selected:
        _, source_baseline, source_binding = _validated_live_backup_source(
            root=root,
            decision=decision,
            decision_path=decision_path,
            backup=backup,
            backup_path=backup_path,
        )
        source_paths = {
            str(row.get("path") or "") for row in source_baseline["files"] if isinstance(row, Mapping)
        }
        missing_route_sources = sorted(set(covered_paths).difference(source_paths))
        if missing_route_sources:
            raise DesignCandidateControlError(
                "Verified live-backup source does not contain every selected route: "
                + ", ".join(missing_route_sources)
            )
        owner_binding.update(
            {
                "decision_schema": OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_SCHEMA,
                "source_selection": "use-verified-live-backup",
                "candidate_source": source_binding,
            }
        )
    binding["owner_source_reconciliation"] = owner_binding
    return binding


def _candidate_source_root(
    root: Path,
    reconciliation: Mapping[str, Any],
) -> tuple[Path, Mapping[str, Any] | None]:
    """Resolve only the exact source selected by the verified binding."""

    owner_binding = reconciliation.get("owner_source_reconciliation")
    if not isinstance(owner_binding, Mapping):
        raise DesignCandidateControlError("Candidate source reconciliation binding is missing.")
    raw_source = owner_binding.get("candidate_source")
    if raw_source is None:
        return root / "website", None
    if (
        not isinstance(raw_source, Mapping)
        or set(raw_source) != _VERIFIED_LIVE_BACKUP_SOURCE_FIELDS
        or raw_source.get("kind") != "verified-live-backup"
        or raw_source.get("remote_root") != "/"
        or owner_binding.get("decision_schema") != OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_SCHEMA
        or owner_binding.get("source_selection") != "use-verified-live-backup"
    ):
        raise DesignCandidateControlError(
            "Candidate source binding is not the exact verified-live-backup contract."
        )
    raw_root = raw_source.get("root")
    if not isinstance(raw_root, str) or not Path(raw_root).is_absolute():
        raise DesignCandidateControlError("Verified-live-backup candidate source root must be absolute.")
    source_root = _regular_directory(Path(raw_root), label="Verified backup directory")
    if str(source_root) != raw_root or _paths_overlap(source_root, root / "website"):
        raise DesignCandidateControlError(
            "Verified-live-backup candidate source root changed or overlaps canonical website."
        )
    return source_root, raw_source


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    temporary = Path(temporary_name)
    try:
        with open(handle, "w", encoding="utf-8", newline="\n", closefd=True) as stream:
            json.dump(dict(value), stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise DesignCandidateControlError(f"Refusing to overwrite control evidence: {path}") from exc
    finally:
        if temporary.exists():
            temporary.unlink()
    return path


def _candidate_root(root: Path, run_id: str) -> Path:
    candidate_root = (root / DEFAULT_CANDIDATE_ROOT / run_id).resolve()
    allowed_root = (root / DEFAULT_CANDIDATE_ROOT).resolve()
    try:
        candidate_root.relative_to(allowed_root)
    except ValueError as exc:
        raise DesignCandidateControlError("Candidate root escapes artifacts/website-candidates/.") from exc
    return candidate_root


def _editorial_asset_control(
    *,
    root: Path,
    run_id: str,
    allowed_paths: Sequence[str],
) -> dict[str, Any]:
    """Bind the exact trusted-binary policy into one immutable v4 order."""

    binary_paths = sorted(
        path for path in allowed_paths if Path(path).suffix.casefold() in CONTROLLED_BINARY_EXTENSIONS
    )
    unsupported = sorted(
        path
        for path in binary_paths
        if Path(path).suffix.casefold() not in TRUSTED_EDITORIAL_IMPORT_EXTENSIONS
    )
    if unsupported:
        raise DesignCandidateControlError(
            "Autonomous candidate work orders may mutate binary assets only through "
            "the trusted provenance-bound WebP importer; use a separate owner-controlled "
            "route for: " + ", ".join(unsupported)
        )

    provenance_path = root / DEFAULT_EDITORIAL_PROVENANCE_MANIFEST
    if binary_paths:
        if not provenance_path.is_file() or provenance_path.is_symlink():
            raise DesignCandidateControlError(
                "A source-bound editorial provenance manifest is required for WebP targets."
            )
        provenance_reference = _relative_to_repo(root, provenance_path)
        provenance_sha256 = _sha256_file(provenance_path)
    else:
        provenance_reference = ""
        provenance_sha256 = ""

    receipt_path = _candidate_root(root, run_id) / DEFAULT_EDITORIAL_IMPORT_RECEIPT_NAME
    return {
        "policy": "every-binary-diff-requires-trusted-editorial-import-receipt",
        "receipt_path": _relative_to_repo(root, receipt_path),
        "receipt_schema": EDITORIAL_IMPORT_RECEIPT_SCHEMA,
        "verification_schema": EDITORIAL_IMPORT_VERIFICATION_SCHEMA,
        "binary_extensions": sorted(CONTROLLED_BINARY_EXTENSIONS),
        "trusted_import_extensions": sorted(TRUSTED_EDITORIAL_IMPORT_EXTENSIONS),
        "unreceipted_binary_diff": "prohibited",
        "replay_verification_required": True,
        "provenance_manifest_path": provenance_reference,
        "provenance_manifest_sha256": provenance_sha256,
        "surface_binding_verification_required": bool(binary_paths),
    }


def _claim_source_paths(register: Mapping[str, Any]) -> list[str]:
    claims = register.get("claims")
    if not isinstance(claims, list):
        raise DesignCandidateControlError("Claim register must contain a claims list.")
    paths: set[str] = set()
    for candidate in claims:
        if not isinstance(candidate, Mapping):
            raise DesignCandidateControlError("Claim register entries must be JSON objects.")
        source = candidate.get("source")
        if not isinstance(source, Mapping):
            raise DesignCandidateControlError("Claim register entries must declare a source binding.")
        raw_path = _safe_relative_path(source.get("path"))
        pieces = Path(raw_path).parts
        if not pieces or pieces[0] != "website" or len(pieces) == 1:
            raise DesignCandidateControlError("Claim-register source bindings must remain below website/.")
        paths.add(Path(*pieces[1:]).as_posix())
    return sorted(paths)


def _claim_public_route_bindings(register: Mapping[str, Any]) -> list[dict[str, str]]:
    """Project only stable claim IDs and their exact public route scope."""

    claims = register.get("claims")
    if not isinstance(claims, list):
        raise DesignCandidateControlError("Claim register must contain a claims list.")
    bindings: set[tuple[str, str]] = set()
    for candidate in claims:
        if not isinstance(candidate, Mapping):
            raise DesignCandidateControlError("Claim register entries must be JSON objects.")
        claim_id = candidate.get("id")
        routes = candidate.get("public_routes")
        if not isinstance(claim_id, str) or not claim_id.strip():
            raise DesignCandidateControlError("Claim register entries must declare a claim id.")
        if not isinstance(routes, list) or not routes:
            raise DesignCandidateControlError(
                "Claim register entries must declare one or more public routes."
            )
        for raw_route in routes:
            route = _safe_route(raw_route)
            binding = (claim_id, route)
            if binding in bindings:
                raise DesignCandidateControlError(
                    f"Claim register repeats public route {route} for {claim_id}."
                )
            bindings.add(binding)
    return [{"claim_id": claim_id, "route": route} for claim_id, route in sorted(bindings)]


def _allowed_file(path: str) -> bool:
    candidate = Path(path)
    return candidate.name in ALLOWED_FILE_NAMES or candidate.suffix.lower() in ALLOWED_EXTENSIONS


def _blocked_file(path: str) -> bool:
    candidate = Path(path)
    return candidate.name in BLOCKED_FILE_NAMES or candidate.suffix.lower() in BLOCKED_EXTENSIONS


def _allowed_verified_backup_source_file(path: str) -> bool:
    """Permit public static source while retaining the intentional .htaccess."""

    candidate = Path(path)
    name = candidate.name.lower()
    if name == ".htaccess":
        return True
    if name == ".env" or name.startswith(".env.") or re.fullmatch(r"\.env\d+", name):
        return False
    if name in {item.lower() for item in BLOCKED_FILE_NAMES}:
        return False
    return _allowed_file(path) and candidate.suffix.lower() not in BLOCKED_EXTENSIONS


def _normalise_url_text(value: str) -> str:
    """Decode harmless escaped slash forms before remote-origin inspection."""

    return (
        html.unescape(value)
        .replace("\\/", "/")
        .replace("\\u002f", "/")
        .replace("\\u002F", "/")
        .replace("\\x2f", "/")
        .replace("\\x2F", "/")
    )


def _canonical_origin_reference(reference: str) -> str:
    candidate = reference.rstrip(".,;:")
    parsed = urlparse(f"https:{candidate}" if candidate.startswith("//") else candidate)
    if parsed.scheme not in {"http", "https"}:
        raise DesignCandidateControlError("Remote references must use HTTP(S).")
    if parsed.scheme == "http":
        raise DesignCandidateControlError("Remote references must use HTTPS.")
    return _safe_origin(f"https://{parsed.netloc}")


def _origins(root: Path, rows: Sequence[Mapping[str, Any]]) -> set[str]:
    origins: set[str] = set()
    text_extensions = set(DECLARATION_REQUIRED_EXTENSIONS)
    for row in rows:
        relative = _safe_relative_path(row.get("path"))
        if Path(relative).suffix.lower() not in text_extensions:
            continue
        text = _normalise_url_text((root / relative).read_text(encoding="utf-8", errors="replace"))
        for match in _URL_REFERENCE_PATTERN.finditer(text):
            raw = match.group(0)
            try:
                origins.add(_canonical_origin_reference(raw))
            except DesignCandidateControlError:
                # A malformed, HTTP, credentialed, or private reference must
                # be an unallowable *new* origin without reflecting its full
                # value back into a durable receipt.
                origins.add(f"unsafe-reference-sha256:{_sha256_file_from_text(raw)}")
    return origins


def _sha256_file_from_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest().upper()


def _secret_hits(path: Path) -> list[str]:
    text = path.read_bytes().decode("latin-1", errors="replace")
    return sorted(
        {pattern_name for pattern_name, pattern in _SECRET_PATTERNS for match in pattern.finditer(text)}
    )


def _strict_text_integrity_findings(
    candidate_site: Path,
    changes: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    """Reject binary/control payloads disguised behind autonomous text suffixes."""

    findings: list[dict[str, str]] = []
    for change in changes:
        path = _safe_relative_path(change.get("path"))
        if (
            change.get("change") == "removed"
            or Path(path).suffix.casefold() not in CONTROLLED_TEXT_EXTENSIONS
        ):
            continue
        target = candidate_site / path
        try:
            payload = target.read_bytes()
            text = payload.decode("utf-8", errors="strict")
        except (OSError, UnicodeDecodeError):
            findings.append({"path": path, "reason": "not-strict-utf8"})
            continue
        if any(byte < 0x20 and byte not in {0x09, 0x0A, 0x0D} for byte in payload):
            findings.append({"path": path, "reason": "control-byte"})
            continue
        if _EMBEDDED_MEDIA_DATA_PATTERN.search(text):
            findings.append({"path": path, "reason": "embedded-base64-media"})
    return findings


def _trusted_binary_import_replay_check(
    *,
    root: Path,
    order: Mapping[str, Any],
    candidate_root: Path,
    candidate_site: Path,
    changes: Sequence[Mapping[str, Any]],
    as_of: datetime | None,
    require_current_baseline: bool,
) -> dict[str, Any]:
    """Replay the fixed trusted importer for every autonomous binary delta."""

    allowed_paths = [_safe_relative_path(path) for path in order.get("allowed_paths", [])]
    declared_binary_paths = sorted(
        path for path in allowed_paths if Path(path).suffix.casefold() in CONTROLLED_BINARY_EXTENSIONS
    )
    changed_binary_paths = sorted(
        _safe_relative_path(change.get("path"))
        for change in changes
        if Path(_safe_relative_path(change.get("path"))).suffix.casefold() in CONTROLLED_BINARY_EXTENSIONS
    )
    unsupported_binary_paths = sorted(
        {
            path
            for path in (*declared_binary_paths, *changed_binary_paths)
            if Path(path).suffix.casefold() not in TRUSTED_EDITORIAL_IMPORT_EXTENSIONS
        }
    )
    control = order.get("editorial_asset_control")
    base_evidence: dict[str, Any] = {
        "required": bool(declared_binary_paths),
        "declared_binary_paths": declared_binary_paths,
        "changed_binary_paths": changed_binary_paths,
        "unsupported_binary_paths": unsupported_binary_paths,
        "receipt_path": "",
        "receipt_present": False,
        "receipt_file_sha256": "",
        "receipt_payload_sha256": "",
        "verification_schema": EDITORIAL_IMPORT_VERIFICATION_SCHEMA,
        "verification_state": "not-required-text-only",
        "imported_paths": [],
        "provenance_manifest_sha256": "",
        "selected_asset_capsules_sha256": "",
        "candidate_ready_asset_ids": [],
        "error": "",
    }
    if not isinstance(control, Mapping):
        base_evidence["verification_state"] = "blocked"
        base_evidence["error"] = "missing-v4-editorial-asset-control"
        return _check(
            "trusted-binary-import-replay",
            False,
            "Every autonomous binary change must replay one fixed trusted importer receipt.",
            **base_evidence,
        )

    receipt_reference = control.get("receipt_path")
    if not isinstance(receipt_reference, str):
        base_evidence["verification_state"] = "blocked"
        base_evidence["error"] = "invalid-fixed-receipt-path"
        return _check(
            "trusted-binary-import-replay",
            False,
            "Every autonomous binary change must replay one fixed trusted importer receipt.",
            **base_evidence,
        )
    base_evidence["receipt_path"] = receipt_reference
    try:
        receipt_path = _resolve_under(
            root,
            receipt_reference,
            label="Editorial import receipt",
        )
        receipt_path.relative_to(candidate_root)
    except (DesignCandidateControlError, ValueError):
        base_evidence["verification_state"] = "blocked"
        base_evidence["error"] = "fixed-receipt-path-outside-candidate"
        return _check(
            "trusted-binary-import-replay",
            False,
            "Every autonomous binary change must replay one fixed trusted importer receipt.",
            **base_evidence,
        )

    try:
        receipt_present = (
            receipt_path.is_file() and not receipt_path.is_symlink() and receipt_path.stat().st_nlink == 1
        )
    except OSError:
        receipt_present = False
    base_evidence["receipt_present"] = receipt_present
    if not declared_binary_paths and not changed_binary_paths and not receipt_present:
        return _check(
            "trusted-binary-import-replay",
            True,
            "Text-only candidates require no editorial binary import receipt.",
            **base_evidence,
        )
    if unsupported_binary_paths:
        base_evidence["verification_state"] = "blocked"
        base_evidence["error"] = "unsupported-autonomous-binary-extension"
        return _check(
            "trusted-binary-import-replay",
            False,
            "Autonomous binary changes are limited to exact provenance-bound WebP imports.",
            **base_evidence,
        )
    if not receipt_present:
        base_evidence["verification_state"] = "blocked"
        base_evidence["error"] = "required-fixed-receipt-missing"
        return _check(
            "trusted-binary-import-replay",
            False,
            "Every declared or changed editorial binary needs the immutable candidate-local importer receipt.",
            **base_evidence,
        )

    try:
        from aureon.operator.design_editorial_asset_candidate_importer import (
            verify_candidate_editorial_asset_import,
        )

        receipt = _read_json(receipt_path, label="Editorial import receipt")
        verification = verify_candidate_editorial_asset_import(
            receipt,
            repo_root=root,
            as_of=as_of,
            verified_at=as_of,
            _require_current_baseline=require_current_baseline,
        )
        imports = receipt.get("imports")
        if not isinstance(imports, list):
            raise DesignCandidateControlError("Editorial import receipt lost its exact import rows.")
        prefix = _relative_to_repo(root, candidate_site).rstrip("/") + "/"
        imported_paths: list[str] = []
        for item in imports:
            if not isinstance(item, Mapping):
                raise DesignCandidateControlError("Editorial import receipt contains a malformed import row.")
            target = item.get("target")
            if not isinstance(target, str) or not target.startswith(prefix):
                raise DesignCandidateControlError(
                    "Editorial import receipt target no longer belongs to this candidate."
                )
            imported_paths.append(_safe_relative_path(target[len(prefix) :]))
        imported_paths = sorted(imported_paths)
        provenance = receipt.get("provenance")
        if not isinstance(provenance, Mapping):
            raise DesignCandidateControlError(
                "Editorial import receipt lost its redacted provenance binding."
            )
        base_evidence.update(
            {
                "receipt_file_sha256": _sha256_file(receipt_path),
                "receipt_payload_sha256": str(receipt.get("receipt_payload_sha256") or ""),
                "verification_state": str(verification.get("state") or "blocked"),
                "imported_paths": imported_paths,
                "provenance_manifest_sha256": str(provenance.get("manifest_file_sha256") or ""),
                "selected_asset_capsules_sha256": str(provenance.get("selected_asset_capsules_sha256") or ""),
                "candidate_ready_asset_ids": sorted(
                    str(value) for value in provenance.get("candidate_ready_asset_ids", [])
                ),
            }
        )
        replay_ok = (
            verification.get("passed") is True
            and imported_paths == declared_binary_paths
            and set(changed_binary_paths).issubset(imported_paths)
        )
        if not replay_ok:
            base_evidence["error"] = "receipt-binary-delta-does-not-match-v4-order"
        return _check(
            "trusted-binary-import-replay",
            replay_ok,
            "Every autonomous binary delta must equal the current rights-bound WebP importer receipt while text changes remain separately controlled.",
            **base_evidence,
        )
    except (
        DesignCandidateControlError,
        ImportError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        base_evidence["verification_state"] = "blocked"
        base_evidence["error"] = f"{type(exc).__name__}:{str(exc)}"
        return _check(
            "trusted-binary-import-replay",
            False,
            "Every autonomous binary delta must replay the immutable trusted importer receipt.",
            **base_evidence,
        )


def _trusted_editorial_surface_replay_check(
    *,
    root: Path,
    order: Mapping[str, Any],
    candidate_root: Path,
    candidate_site: Path,
    binary_replay_check: Mapping[str, Any],
    as_of: datetime | None,
) -> dict[str, Any]:
    """Structurally bind imported images, public links, and exact safe copy."""

    binary_evidence = binary_replay_check.get("evidence")
    binary = binary_evidence if isinstance(binary_evidence, Mapping) else {}
    required = binary.get("required") is True
    base_evidence: dict[str, Any] = {
        "required": required,
        "verification_schema": EDITORIAL_SURFACE_BINDING_SCHEMA,
        "verification_state": "not-required-text-only",
        "manifest_file_sha256": "",
        "selected_asset_capsules_sha256": "",
        "selected_route_asset_capsules_sha256": "",
        "candidate_surface_bindings_sha256": "",
        "expected_surfaces_sha256": "",
        "candidate_ready_asset_ids": [],
        "expected_surfaces": [],
        "failed_surfaces": [],
        "error": "",
    }
    if not required:
        return _check(
            "trusted-editorial-surface-replay",
            binary_replay_check.get("passed") is True,
            "Text-only candidates require no editorial surface replay.",
            **base_evidence,
        )
    control = order.get("editorial_asset_control")
    if (
        binary_replay_check.get("passed") is not True
        or not isinstance(control, Mapping)
        or control.get("surface_binding_verification_required") is not True
    ):
        base_evidence["verification_state"] = "blocked"
        base_evidence["error"] = "trusted-binary-or-surface-policy-not-closed"
        return _check(
            "trusted-editorial-surface-replay",
            False,
            "Binary candidates require both trusted import replay and structural editorial surface verification.",
            **base_evidence,
        )

    try:
        from aureon.operator.design_editorial_asset_provenance import (
            audit_design_editorial_asset_provenance_file,
            verify_editorial_asset_surface_bindings,
        )

        receipt_path = _resolve_under(
            root,
            control.get("receipt_path"),
            label="Editorial import receipt",
        )
        receipt_path.relative_to(candidate_root)
        receipt = _read_json(
            receipt_path,
            label="Editorial import receipt",
        )
        provenance = receipt.get("provenance")
        imports = receipt.get("imports")
        if not isinstance(provenance, Mapping) or not isinstance(imports, list):
            raise DesignCandidateControlError(
                "Editorial import receipt lost its public provenance projection."
            )
        selected_asset_ids = sorted(str(value) for value in provenance.get("candidate_ready_asset_ids", []))
        if (
            not selected_asset_ids
            or selected_asset_ids != sorted(set(selected_asset_ids))
            or selected_asset_ids != list(binary.get("candidate_ready_asset_ids") or [])
        ):
            raise DesignCandidateControlError(
                "Editorial import receipt selected asset ids no longer match binary replay."
            )
        manifest_reference = control.get("provenance_manifest_path")
        if not isinstance(manifest_reference, str):
            raise DesignCandidateControlError("Editorial work order lost its canonical provenance manifest.")
        audit = audit_design_editorial_asset_provenance_file(
            Path(manifest_reference),
            repo_root=root,
            as_of=as_of,
        )
        if audit.get("passed") is not True:
            raise DesignCandidateControlError("Current editorial provenance audit no longer passes.")
        manifest_binding = audit.get("manifest")
        if not isinstance(manifest_binding, Mapping):
            raise DesignCandidateControlError("Editorial provenance audit lost its manifest binding.")
        manifest_file_sha256 = str(manifest_binding.get("sha256") or "")
        selected_capsules = sorted(
            [
                dict(item)
                for item in audit.get("asset_capsules", [])
                if isinstance(item, Mapping) and str(item.get("asset_id") or "") in selected_asset_ids
            ],
            key=lambda item: str(item.get("asset_id") or ""),
        )
        selected_asset_capsules_sha256 = _json_hash(selected_capsules)
        if (
            {str(item.get("asset_id") or "") for item in selected_capsules} != set(selected_asset_ids)
            or manifest_file_sha256 != str(binary.get("provenance_manifest_sha256") or "")
            or manifest_file_sha256 != str(provenance.get("manifest_file_sha256") or "")
            or selected_asset_capsules_sha256 != str(binary.get("selected_asset_capsules_sha256") or "")
            or selected_asset_capsules_sha256 != str(provenance.get("selected_asset_capsules_sha256") or "")
        ):
            raise DesignCandidateControlError(
                "Editorial surface replay drifted from its trusted import provenance."
            )

        raw_manifest = _read_json(
            root / manifest_reference,
            label="Canonical editorial provenance manifest",
        )
        raw_assets = raw_manifest.get("assets")
        if not isinstance(raw_assets, list):
            raise DesignCandidateControlError("Editorial provenance manifest lost its asset records.")
        assets_by_id = {
            str(item.get("asset_id") or ""): item for item in raw_assets if isinstance(item, Mapping)
        }
        if any(asset_id not in assets_by_id for asset_id in selected_asset_ids):
            raise DesignCandidateControlError("Editorial provenance manifest lost a selected asset.")

        allowed_paths = {_safe_relative_path(value) for value in order.get("allowed_paths", [])}
        order_routes = {str(value) for value in order.get("routes", []) if isinstance(value, str)}
        import_surface_ids: dict[str, set[str]] = {asset_id: set() for asset_id in selected_asset_ids}
        for item in imports:
            if not isinstance(item, Mapping):
                raise DesignCandidateControlError(
                    "Editorial import receipt contains a malformed public import row."
                )
            asset_id = str(item.get("asset_id") or "")
            if asset_id not in import_surface_ids:
                raise DesignCandidateControlError(
                    "Editorial import receipt contains an undeclared selected asset."
                )
            raw_surface_ids = item.get("surface_ids")
            if not isinstance(raw_surface_ids, list) or not all(
                isinstance(value, str) and value for value in raw_surface_ids
            ):
                raise DesignCandidateControlError("Editorial import receipt lost its surface identifiers.")
            import_surface_ids[asset_id].update(raw_surface_ids)

        raw_route_capsules = audit.get("route_asset_capsules")
        if not isinstance(raw_route_capsules, list):
            raise DesignCandidateControlError("Editorial provenance audit lost its route capsules.")
        selected_route_capsules: list[dict[str, Any]] = []
        for raw_capsule in raw_route_capsules:
            if not isinstance(raw_capsule, Mapping):
                raise DesignCandidateControlError(
                    "Editorial provenance audit contains a malformed route capsule."
                )
            asset_id = str(raw_capsule.get("asset_id") or "")
            placement = raw_capsule.get("placement")
            if asset_id not in selected_asset_ids or not isinstance(
                placement,
                Mapping,
            ):
                continue
            destination = str(placement.get("destination_path") or "")
            if not destination.startswith("website/"):
                raise DesignCandidateControlError("Editorial route capsule escaped the canonical website.")
            destination_relative = _safe_relative_path(destination[len("website/") :])
            if (
                raw_capsule.get("route_scope") in order_routes
                and destination_relative in allowed_paths
                and str(placement.get("surface_id") or "") in import_surface_ids[asset_id]
            ):
                selected_route_capsules.append(dict(raw_capsule))

        def route_capsule_key(
            item: Mapping[str, Any],
        ) -> tuple[str, str, str, str]:
            raw_placement = item.get("placement")
            placement = raw_placement if isinstance(raw_placement, Mapping) else {}
            return (
                str(item.get("route_scope") or ""),
                str(item.get("asset_id") or ""),
                str(placement.get("destination_path") or ""),
                str(placement.get("surface_id") or ""),
            )

        selected_route_capsules.sort(key=route_capsule_key)
        if not selected_route_capsules or {
            str(item.get("asset_id") or "") for item in selected_route_capsules
        } != set(selected_asset_ids):
            raise DesignCandidateControlError("Every imported asset needs an exact in-scope route surface.")

        candidate_bindings = {
            asset_id: verify_editorial_asset_surface_bindings(
                assets_by_id[asset_id],
                repo_root=root,
                website_root=candidate_site,
            )
            for asset_id in selected_asset_ids
        }
        expected_surfaces: list[dict[str, Any]] = []
        failed_surfaces: list[dict[str, Any]] = []
        selected_binding_rows: list[dict[str, Any]] = []
        seen_surface_keys: set[tuple[str, str]] = set()
        for capsule in selected_route_capsules:
            asset_id = str(capsule["asset_id"])
            placement = capsule.get("placement")
            variants = capsule.get("website_variants")
            if not isinstance(placement, Mapping) or not isinstance(
                variants,
                list,
            ):
                raise DesignCandidateControlError(
                    "Editorial route capsule lost placement or variant evidence."
                )
            destination_path = str(placement.get("destination_path") or "")
            surface_id = str(placement.get("surface_id") or "")
            key = (destination_path, surface_id)
            if key in seen_surface_keys:
                raise DesignCandidateControlError("Editorial route capsule repeats a destination surface.")
            seen_surface_keys.add(key)
            candidate_binding = candidate_bindings[asset_id]
            if (
                candidate_binding.get("schema") != EDITORIAL_SURFACE_BINDING_SCHEMA
                or candidate_binding.get("website_projection") != "candidate"
            ):
                raise DesignCandidateControlError(
                    "Candidate editorial surface verifier changed its contract."
                )
            binding_rows = [
                item
                for item in candidate_binding.get("placements", [])
                if isinstance(item, Mapping)
                and item.get("destination_path") == destination_path
                and item.get("surface_id") == surface_id
            ]
            if len(binding_rows) != 1:
                raise DesignCandidateControlError("Candidate editorial surface did not resolve uniquely.")
            binding_row = dict(binding_rows[0])
            selected_binding_rows.append(
                {
                    "asset_id": asset_id,
                    **binding_row,
                }
            )
            if (
                binding_row.get("state") != "bound"
                or binding_row.get("binding_complete") is not True
                or binding_row.get("finding_codes") != []
            ):
                failed_surfaces.append(
                    {
                        "asset_id": asset_id,
                        "route_scope": capsule.get("route_scope"),
                        "destination_path": destination_path,
                        "surface_id": surface_id,
                        "finding_codes": list(binding_row.get("finding_codes") or []),
                    }
                )
            expected_surfaces.append(
                {
                    "asset_id": asset_id,
                    "route_scope": capsule.get("route_scope"),
                    "destination_path": destination_path,
                    "surface_id": surface_id,
                    "public_post_url": capsule.get("public_post_url"),
                    "variants": sorted(
                        [
                            {
                                "role": item.get("role"),
                                "path": item.get("path"),
                                "sha256": item.get("sha256"),
                                "media_type": item.get("media_type"),
                                "width": item.get("width"),
                                "height": item.get("height"),
                            }
                            for item in variants
                            if isinstance(item, Mapping)
                        ],
                        key=lambda item: str(item.get("role") or ""),
                    ),
                    "alt": placement.get("alt"),
                    "caption": placement.get("caption"),
                    "credit": placement.get("credit"),
                    "route_asset_capsule_sha256": capsule.get("route_asset_capsule_sha256"),
                    "expected_binding_sha256": binding_row.get("expected_binding_sha256"),
                    "observation_sha256": binding_row.get("observation_sha256"),
                    "surface_binding_sha256": binding_row.get("surface_binding_sha256"),
                }
            )

        expected_surfaces.sort(
            key=lambda item: (
                str(item["route_scope"]),
                str(item["asset_id"]),
                str(item["destination_path"]),
                str(item["surface_id"]),
            )
        )
        selected_binding_rows.sort(
            key=lambda item: (
                str(item["route_scope"]),
                str(item["asset_id"]),
                str(item["destination_path"]),
                str(item["surface_id"]),
            )
        )
        selected_route_asset_capsules_sha256 = _json_hash(selected_route_capsules)
        candidate_surface_bindings_sha256 = _json_hash(selected_binding_rows)
        expected_surfaces_sha256 = _json_hash(expected_surfaces)
        base_evidence.update(
            {
                "verification_state": ("verified-local-candidate" if not failed_surfaces else "blocked"),
                "manifest_file_sha256": manifest_file_sha256,
                "selected_asset_capsules_sha256": (selected_asset_capsules_sha256),
                "selected_route_asset_capsules_sha256": (selected_route_asset_capsules_sha256),
                "candidate_surface_bindings_sha256": (candidate_surface_bindings_sha256),
                "expected_surfaces_sha256": expected_surfaces_sha256,
                "candidate_ready_asset_ids": selected_asset_ids,
                "expected_surfaces": expected_surfaces,
                "failed_surfaces": failed_surfaces,
            }
        )
        return _check(
            "trusted-editorial-surface-replay",
            not failed_surfaces,
            "Every imported editorial image must remain one exact route-bound structural surface with its approved local variants, post URL, alt, caption, and credit.",
            **base_evidence,
        )
    except (
        DesignCandidateControlError,
        ImportError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        base_evidence["verification_state"] = "blocked"
        base_evidence["error"] = "surface-replay-error:" + type(exc).__name__
        return _check(
            "trusted-editorial-surface-replay",
            False,
            "Every imported editorial image must replay through the privacy-safe structural surface verifier.",
            **base_evidence,
        )


def _change_records(
    baseline: Sequence[Mapping[str, Any]], candidate: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    before = _manifest_index(baseline)
    after = _manifest_index(candidate)
    rows: list[dict[str, Any]] = []
    for path in sorted(set(before).union(after)):
        old = before.get(path)
        new = after.get(path)
        if old is None:
            kind = "added"
        elif new is None:
            kind = "removed"
        elif old["sha256"] == new["sha256"] and old["bytes"] == new["bytes"]:
            continue
        else:
            kind = "modified"
        rows.append(
            {
                "path": path,
                "change": kind,
                "before_sha256": old["sha256"] if old else "",
                "after_sha256": new["sha256"] if new else "",
                "before_bytes": old["bytes"] if old else None,
                "after_bytes": new["bytes"] if new else None,
            }
        )
    return rows


def _check(identifier: str, passed: bool, message: str, **evidence: Any) -> dict[str, Any]:
    return {
        "id": identifier,
        "passed": bool(passed),
        "message": message,
        "evidence": evidence,
    }


def _require_exact_object(
    value: object,
    fields: frozenset[str],
    *,
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, dict) or frozenset(value) != fields:
        raise DesignCandidateControlError(f"{label} fields must exactly match the current contract.")
    return value


def _require_json_value(value: object, *, label: str) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise DesignCandidateControlError(f"{label} contains a non-finite JSON number.")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _require_json_value(item, label=f"{label}[{index}]")
        return
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise DesignCandidateControlError(f"{label} contains a non-string JSON object key.")
        for key, item in value.items():
            _require_json_value(item, label=f"{label}.{key}")
        return
    raise DesignCandidateControlError(f"{label} contains a non-JSON value.")


def _require_string(value: object, *, label: str, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value):
        raise DesignCandidateControlError(f"{label} must be a string.")
    return value


def _require_sha256(value: object, *, label: str, allow_empty: bool = False) -> str:
    text = _require_string(value, label=label, allow_empty=allow_empty)
    if (text or not allow_empty) and _SHA256.fullmatch(text) is None:
        raise DesignCandidateControlError(f"{label} must be an uppercase SHA-256.")
    return text


def _require_string_list(value: object, *, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise DesignCandidateControlError(f"{label} must be a JSON string array.")
    return value


def _require_canonical_string_list(
    value: object,
    *,
    label: str,
    canonicalizer: Any,
    allow_empty: bool,
) -> list[str]:
    items = _require_string_list(value, label=label)
    if not allow_empty and not items:
        raise DesignCandidateControlError(f"{label} must not be empty.")
    canonical: list[str] = []
    for index, item in enumerate(items):
        try:
            normalised = canonicalizer(item)
        except DesignCandidateControlError as exc:
            raise DesignCandidateControlError(f"{label}[{index}] is invalid.") from exc
        if normalised != item:
            raise DesignCandidateControlError(f"{label}[{index}] is not canonical.")
        canonical.append(item)
    if canonical != sorted(set(canonical)):
        raise DesignCandidateControlError(f"{label} must be sorted and unique.")
    return canonical


def _require_manifest_contract(value: object, *, label: str) -> dict[str, Any]:
    manifest = _require_exact_object(value, BASELINE_FIELDS, label=label)
    _require_sha256(manifest.get("tree_sha256"), label=f"{label}.tree_sha256")
    file_count = manifest.get("file_count")
    total_bytes = manifest.get("total_bytes")
    if type(file_count) is not int or file_count < 0:
        raise DesignCandidateControlError(f"{label}.file_count must be a non-negative integer.")
    if type(total_bytes) is not int or total_bytes < 0:
        raise DesignCandidateControlError(f"{label}.total_bytes must be a non-negative integer.")
    files = manifest.get("files")
    if not isinstance(files, list):
        raise DesignCandidateControlError(f"{label}.files must be a JSON array.")
    summary = _tree_summary(files)
    if not _strict_json_equal(manifest, summary):
        raise DesignCandidateControlError(f"{label} must equal its complete deterministic manifest summary.")
    return manifest


def _require_live_reconciliation_contract(value: object) -> dict[str, Any]:
    label = "Design work order live_reconciliation"
    reconciliation = _require_exact_object(value, LIVE_RECONCILIATION_FIELDS, label=label)
    receipt_path = _require_string(reconciliation.get("receipt_path"), label=f"{label}.receipt_path")
    if _safe_relative_path(receipt_path) != receipt_path:
        raise DesignCandidateControlError(f"{label}.receipt_path is not canonical.")
    _require_sha256(reconciliation.get("receipt_sha256"), label=f"{label}.receipt_sha256")
    state = reconciliation.get("state")
    if state not in {"live-surface-semantically-aligned", "live-drift-detected"}:
        raise DesignCandidateControlError(f"{label}.state is unsupported.")
    _require_sha256(
        reconciliation.get("selected_tree_sha256"),
        label=f"{label}.selected_tree_sha256",
    )
    covered = _require_canonical_string_list(
        reconciliation.get("covered_local_paths"),
        label=f"{label}.covered_local_paths",
        canonicalizer=_safe_relative_path,
        allow_empty=False,
    )
    current = _require_canonical_string_list(
        reconciliation.get("current_local_paths"),
        label=f"{label}.current_local_paths",
        canonicalizer=_safe_relative_path,
        allow_empty=False,
    )
    if current != covered or any(Path(path).suffix.lower() not in {".html", ".htm"} for path in covered):
        raise DesignCandidateControlError(
            f"{label} must bind the same sorted complete local HTML paths as covered and current."
        )

    owner = reconciliation.get("owner_source_reconciliation")
    if not isinstance(owner, dict):
        raise DesignCandidateControlError(f"{label}.owner_source_reconciliation must be an object.")
    owner_fields = frozenset(owner)
    if state == "live-surface-semantically-aligned":
        retained = _require_exact_object(
            owner,
            RETAINED_OWNER_RECONCILIATION_FIELDS,
            label=f"{label}.owner_source_reconciliation",
        )
        expected = {
            "required": False,
            "decision_path": "",
            "decision_sha256": "",
            "backup_receipt_path": "",
            "backup_receipt_sha256": "",
            "validation_state": "not-required-semantic-alignment",
        }
        if not _strict_json_equal(retained, expected):
            raise DesignCandidateControlError(
                f"{label}.owner_source_reconciliation is not the exact aligned-source contract."
            )
        return reconciliation

    if owner_fields == RETAINED_OWNER_RECONCILIATION_FIELDS:
        retained = owner
        if (
            retained.get("required") is not True
            or retained.get("validation_state") != "owner-reconciled-for-staged-candidate"
        ):
            raise DesignCandidateControlError(
                f"{label}.owner_source_reconciliation is not an approved retained-local decision."
            )
    elif owner_fields == VERIFIED_OWNER_RECONCILIATION_FIELDS:
        retained = owner
        if (
            retained.get("required") is not True
            or retained.get("validation_state") != "owner-reconciled-for-live-backup-staged-candidate"
            or retained.get("decision_schema") != OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_SCHEMA
            or retained.get("source_selection") != "use-verified-live-backup"
        ):
            raise DesignCandidateControlError(
                f"{label}.owner_source_reconciliation is not an approved verified-live-backup decision."
            )
        source_label = f"{label}.owner_source_reconciliation.candidate_source"
        source = _require_exact_object(
            retained.get("candidate_source"),
            _VERIFIED_LIVE_BACKUP_SOURCE_FIELDS,
            label=source_label,
        )
        if source.get("kind") != "verified-live-backup" or source.get("remote_root") != "/":
            raise DesignCandidateControlError(f"{source_label} kind or remote root is invalid.")
        for field in ("root", "manifest_path"):
            raw_path = _require_string(source.get(field), label=f"{source_label}.{field}")
            if not Path(raw_path).is_absolute():
                raise DesignCandidateControlError(f"{source_label}.{field} must be absolute.")
        for field in ("manifest_sha256", "tree_sha256", "baseline_tree_sha256"):
            _require_sha256(source.get(field), label=f"{source_label}.{field}")
        for field in ("file_count", "total_bytes"):
            count = source.get(field)
            if type(count) is not int or count < 1:
                raise DesignCandidateControlError(f"{source_label}.{field} must be a positive integer.")
    else:
        raise DesignCandidateControlError(
            f"{label}.owner_source_reconciliation fields do not match an approved contract."
        )

    for field in ("decision_path", "backup_receipt_path"):
        raw_path = _require_string(retained.get(field), label=f"{label}.owner_source_reconciliation.{field}")
        if _safe_relative_path(raw_path) != raw_path:
            raise DesignCandidateControlError(
                f"{label}.owner_source_reconciliation.{field} is not canonical."
            )
    for field in ("decision_sha256", "backup_receipt_sha256"):
        _require_sha256(
            retained.get(field),
            label=f"{label}.owner_source_reconciliation.{field}",
        )
    return reconciliation


def require_design_work_order_contract(value: object) -> dict[str, Any]:
    """Require the complete recursive, exact-field, type-strict v4 JSON contract."""

    label = "Design work order"
    order = _require_exact_object(value, WORK_ORDER_FIELDS, label=label)
    _require_json_value(order, label=label)
    if order.get("schema") != WORK_ORDER_SCHEMA:
        raise DesignCandidateControlError("Design work-order schema is unsupported.")
    _parse_utc_z_timestamp(order.get("created_at"), label="Design work order created_at")
    run_id = _safe_run_id(order.get("run_id"))
    goal = _require_string(order.get("goal"), label="Design work order goal")
    if goal != goal.strip():
        raise DesignCandidateControlError("Design work order goal must use canonical trimmed text.")

    _require_canonical_string_list(
        order.get("routes"),
        label="Design work order routes",
        canonicalizer=_safe_route,
        allow_empty=False,
    )
    allowed_paths = _require_canonical_string_list(
        order.get("allowed_paths"),
        label="Design work order allowed_paths",
        canonicalizer=_safe_relative_path,
        allow_empty=False,
    )
    if len(allowed_paths) > MAX_AUTONOMOUS_ALLOWED_PATHS or any(
        _blocked_file(path) or not _allowed_file(path) for path in allowed_paths
    ):
        raise DesignCandidateControlError(
            "Design work order allowed_paths exceed the bounded public-file policy."
        )
    origins = _require_string_list(
        order.get("allowed_new_origins"),
        label="Design work order allowed_new_origins",
    )
    if origins:
        raise DesignCandidateControlError("Design work order allowed_new_origins must be empty.")

    reconciliation = _require_live_reconciliation_contract(order.get("live_reconciliation"))
    baseline = _require_manifest_contract(order.get("baseline"), label="Design work order baseline")
    owner = reconciliation["owner_source_reconciliation"]
    if isinstance(owner, dict) and "candidate_source" in owner:
        source = owner["candidate_source"]
        if (
            source.get("baseline_tree_sha256") != baseline["tree_sha256"]
            or type(source.get("file_count")) is not int
            or source.get("file_count") != baseline["file_count"]
            or type(source.get("total_bytes")) is not int
            or source.get("total_bytes") != baseline["total_bytes"]
        ):
            raise DesignCandidateControlError(
                "Verified-live-backup source summary does not equal the work-order baseline."
            )

    claim = _require_exact_object(
        order.get("claim_control"),
        CLAIM_CONTROL_FIELDS,
        label="Design work order claim_control",
    )
    if claim.get("register_path") != DEFAULT_CLAIM_REGISTER.as_posix():
        raise DesignCandidateControlError("Design work order claim register path is not fixed.")
    _require_sha256(claim.get("register_sha256"), label="Design work order claim_control.register_sha256")
    _require_canonical_string_list(
        claim.get("bound_source_paths"),
        label="Design work order claim_control.bound_source_paths",
        canonicalizer=_safe_relative_path,
        allow_empty=False,
    )
    if (
        claim.get("changed_html_or_json_requires_declaration") is not True
        or claim.get("bound_source_change_requires_staged_register_refresh") is not True
    ):
        raise DesignCandidateControlError("Design work order claim-control gates must remain enabled.")

    editorial = _require_exact_object(
        order.get("editorial_asset_control"),
        EDITORIAL_ASSET_CONTROL_FIELDS,
        label="Design work order editorial_asset_control",
    )
    binary_paths = sorted(
        path for path in allowed_paths if Path(path).suffix.casefold() in CONTROLLED_BINARY_EXTENSIONS
    )
    expected_editorial_static: dict[str, Any] = {
        "policy": "every-binary-diff-requires-trusted-editorial-import-receipt",
        "receipt_path": (DEFAULT_CANDIDATE_ROOT / run_id / DEFAULT_EDITORIAL_IMPORT_RECEIPT_NAME).as_posix(),
        "receipt_schema": EDITORIAL_IMPORT_RECEIPT_SCHEMA,
        "verification_schema": EDITORIAL_IMPORT_VERIFICATION_SCHEMA,
        "binary_extensions": sorted(CONTROLLED_BINARY_EXTENSIONS),
        "trusted_import_extensions": sorted(TRUSTED_EDITORIAL_IMPORT_EXTENSIONS),
        "unreceipted_binary_diff": "prohibited",
        "replay_verification_required": True,
        "surface_binding_verification_required": bool(binary_paths),
    }
    for field, expected in expected_editorial_static.items():
        if not _strict_json_equal(editorial.get(field), expected):
            raise DesignCandidateControlError(f"Design work order editorial_asset_control.{field} changed.")
    provenance_path = editorial.get("provenance_manifest_path")
    provenance_sha256 = editorial.get("provenance_manifest_sha256")
    if binary_paths:
        if provenance_path != DEFAULT_EDITORIAL_PROVENANCE_MANIFEST.as_posix():
            raise DesignCandidateControlError(
                "Design work order editorial provenance manifest path is not fixed."
            )
        _require_sha256(
            provenance_sha256,
            label="Design work order editorial_asset_control.provenance_manifest_sha256",
        )
    elif provenance_path != "" or provenance_sha256 != "":
        raise DesignCandidateControlError(
            "Design work order without binary targets must not claim editorial provenance."
        )

    test_policy = _require_exact_object(
        order.get("test_policy"),
        TEST_POLICY_FIELDS,
        label="Design work order test_policy",
    )
    if test_policy.get("path") != DEFAULT_OPERATOR_CONFIG.as_posix():
        raise DesignCandidateControlError("Design work order test-policy path is not fixed.")
    _require_sha256(test_policy.get("sha256"), label="Design work order test_policy.sha256")

    layout = _require_exact_object(
        order.get("candidate_layout"),
        CANDIDATE_LAYOUT_FIELDS,
        label="Design work order candidate_layout",
    )
    expected_layout = {
        "root": (DEFAULT_CANDIDATE_ROOT / run_id).as_posix(),
        "website_path": (DEFAULT_CANDIDATE_ROOT / run_id / "website").as_posix(),
        "staged_claim_register_path": (
            DEFAULT_CANDIDATE_ROOT / run_id / "claim-evidence" / DEFAULT_CLAIM_REGISTER.name
        ).as_posix(),
    }
    if not _strict_json_equal(layout, expected_layout):
        raise DesignCandidateControlError(
            "Design work order candidate_layout is not the deterministic run layout."
        )
    if not _strict_json_equal(order.get("authority"), NON_AUTHORITATIVE_AUTHORITY):
        raise DesignCandidateControlError(
            "Design work order authority is not the exact non-authoritative boundary."
        )
    return order


def _require_work_order_binding(value: object, *, label: str) -> dict[str, Any]:
    binding = _require_exact_object(value, CANDIDATE_WORK_ORDER_BINDING_FIELDS, label=label)
    run_id = _require_string(binding.get("run_id"), label=f"{label}.run_id")
    if _RUN_ID.fullmatch(run_id) is None:
        raise DesignCandidateControlError(f"{label}.run_id is malformed.")
    path = _require_string(binding.get("path"), label=f"{label}.path")
    expected_path = (DEFAULT_CANDIDATE_ROOT / "work-orders" / f"{run_id}.v4.json").as_posix()
    if path != expected_path:
        raise DesignCandidateControlError(f"{label}.path does not match its run id.")
    _require_sha256(binding.get("file_sha256"), label=f"{label}.file_sha256")
    _require_sha256(binding.get("sha256"), label=f"{label}.sha256")
    _require_sha256(
        binding.get("baseline_tree_sha256"),
        label=f"{label}.baseline_tree_sha256",
    )
    return binding


def _require_validation_input_contract(value: object) -> dict[str, Any]:
    source = _require_exact_object(
        value,
        VALIDATION_INPUT_FIELDS,
        label="Candidate validation input",
    )
    _require_json_value(source, label="Candidate validation input")
    if source.get("schema") != VALIDATION_INPUT_SCHEMA:
        raise DesignCandidateControlError("Candidate validation-input schema is unsupported.")
    _parse_utc_z_timestamp(source.get("issued_at"), label="Candidate validation input issued_at")
    _require_work_order_binding(
        source.get("work_order"),
        label="Candidate validation input work-order binding",
    )
    try:
        require_source_closure_contract(source.get("source_closure"))
    except DesignCandidateSourceClosureError as exc:
        raise DesignCandidateControlError(
            f"Candidate validation-input executable-source closure is invalid: {exc}"
        ) from exc
    claim_impacts = source.get("claim_impacts")
    if not isinstance(claim_impacts, list) or not all(
        isinstance(item, dict) and frozenset(item) == frozenset({"path", "classification", "rationale"})
        for item in claim_impacts
    ):
        raise DesignCandidateControlError(
            "Candidate validation input claim-impact declarations are malformed."
        )
    for index, declaration in enumerate(claim_impacts):
        _require_string(
            declaration.get("path"),
            label=f"Candidate validation input declaration {index} path",
        )
        if declaration.get("classification") not in CLAIM_IMPACT_CLASSIFICATIONS:
            raise DesignCandidateControlError(
                f"Candidate validation input declaration {index} classification is invalid."
            )
        _require_string(
            declaration.get("rationale"),
            label=f"Candidate validation input declaration {index} rationale",
        )
    surface = _require_exact_object(
        source.get("claim_surface"),
        frozenset({"required", "binding", "manifest"}),
        label="Candidate validation input claim-surface binding",
    )
    if type(surface.get("required")) is not bool:
        raise DesignCandidateControlError(
            "Candidate validation input claim_surface.required must be boolean."
        )
    binding = surface.get("binding")
    manifest = surface.get("manifest")
    if (
        not isinstance(binding, dict)
        or not isinstance(manifest, list)
        or not all(isinstance(item, dict) for item in manifest)
    ):
        raise DesignCandidateControlError(
            "Candidate validation input claim-surface binding or manifest is malformed."
        )
    if surface["required"] is False and (binding or manifest):
        raise DesignCandidateControlError(
            "A non-runner validation input must retain an empty claim-surface binding and manifest."
        )
    if not _strict_json_equal(source.get("authority"), VALIDATION_INPUT_AUTHORITY):
        raise DesignCandidateControlError(
            "Candidate validation input must retain its local non-authoritative boundary."
        )
    payload_sha256 = _require_sha256(
        source.get("payload_sha256"),
        label="Candidate validation input payload_sha256",
    )
    unsigned = dict(source)
    unsigned.pop("payload_sha256")
    if _json_hash(unsigned) != payload_sha256:
        raise DesignCandidateControlError("Candidate validation-input self-hash is invalid.")
    return source


def require_candidate_receipt_contract(receipt: Mapping[str, Any]) -> None:
    """Reject any receipt that is not the exact type-strict v1 JSON contract."""

    value = _require_exact_object(
        receipt,
        CANDIDATE_RECEIPT_FIELDS,
        label="Candidate receipt",
    )
    _require_json_value(value, label="Candidate receipt")
    if value.get("schema") != CANDIDATE_SCHEMA:
        raise DesignCandidateControlError("Candidate receipt schema is unsupported.")
    _parse_utc_z_timestamp(value.get("validated_at"), label="Candidate receipt validated_at")
    if value.get("state") not in {"validated-local", "blocked"}:
        raise DesignCandidateControlError("Candidate receipt state is unsupported.")
    if type(value.get("passed")) is not bool:
        raise DesignCandidateControlError("Candidate receipt passed must be boolean.")
    if (value["passed"] is True) != (value["state"] == "validated-local"):
        raise DesignCandidateControlError("Candidate receipt state and boolean pass result disagree.")
    if value.get("release_eligible") is not False or value.get("deployment_authority") != "none":
        raise DesignCandidateControlError("Candidate receipt exceeds local staged authority.")
    if not _strict_json_equal(value.get("authority"), NON_AUTHORITATIVE_AUTHORITY):
        raise DesignCandidateControlError("Candidate receipt authority boundary is malformed.")

    validation_binding = _require_exact_object(
        value.get("validation_input"),
        VALIDATION_INPUT_BINDING_FIELDS,
        label="Candidate receipt validation-input binding",
    )
    _require_string(validation_binding.get("path"), label="Candidate receipt validation-input path")
    for field in ("file_sha256", "json_sha256", "payload_sha256"):
        _require_sha256(
            validation_binding.get(field),
            label=f"Candidate receipt validation-input {field}",
        )
    try:
        require_source_closure_contract(value.get("source_closure"))
    except DesignCandidateSourceClosureError as exc:
        raise DesignCandidateControlError(
            f"Candidate receipt executable-source closure is invalid: {exc}"
        ) from exc

    _require_work_order_binding(
        value.get("work_order"),
        label="Candidate receipt work-order binding",
    )
    candidate = _require_exact_object(
        value.get("candidate"),
        CANDIDATE_BINDING_FIELDS,
        label="Candidate receipt candidate binding",
    )
    _require_string(candidate.get("root"), label="Candidate receipt candidate root")
    _require_string(candidate.get("website_path"), label="Candidate receipt candidate website_path")
    _require_sha256(
        candidate.get("tree_sha256"),
        label="Candidate receipt candidate tree_sha256",
        allow_empty=value["passed"] is False,
    )
    for field in ("file_count", "total_bytes"):
        count = candidate.get(field)
        if type(count) is not int or count < 0:
            raise DesignCandidateControlError(
                f"Candidate receipt candidate {field} must be a non-negative integer."
            )

    changes = value.get("changes")
    if not isinstance(changes, list):
        raise DesignCandidateControlError("Candidate receipt changes must be an array.")
    change_fields = frozenset(
        {
            "path",
            "change",
            "before_sha256",
            "after_sha256",
            "before_bytes",
            "after_bytes",
        }
    )
    for index, raw_change in enumerate(changes):
        change = _require_exact_object(
            raw_change,
            change_fields,
            label=f"Candidate receipt change {index}",
        )
        _require_string(change.get("path"), label=f"Candidate receipt change {index} path")
        if change.get("change") not in {"added", "modified", "removed"}:
            raise DesignCandidateControlError(f"Candidate receipt change {index} kind is invalid.")
        _require_sha256(
            change.get("before_sha256"),
            label=f"Candidate receipt change {index} before_sha256",
            allow_empty=True,
        )
        _require_sha256(
            change.get("after_sha256"),
            label=f"Candidate receipt change {index} after_sha256",
            allow_empty=True,
        )
        for field in ("before_bytes", "after_bytes"):
            count = change.get(field)
            if count is not None and (type(count) is not int or count < 0):
                raise DesignCandidateControlError(
                    f"Candidate receipt change {index} {field} must be null or a non-negative integer."
                )

    claims = _require_exact_object(
        value.get("claims"),
        frozenset(
            {
                "changed_declaration_paths",
                "bound_source_changes",
                "material_by_default_paths",
                "material_claim_paths",
                "bound_material_claim_paths",
                "unbound_material_claim_paths",
                "declarations",
                "staged_register_sha256",
                "staged_register_audit",
            }
        ),
        label="Candidate receipt claims",
    )
    for field in (
        "changed_declaration_paths",
        "bound_source_changes",
        "material_by_default_paths",
        "material_claim_paths",
        "bound_material_claim_paths",
        "unbound_material_claim_paths",
    ):
        _require_string_list(claims.get(field), label=f"Candidate receipt claims {field}")
    declarations = claims.get("declarations")
    if not isinstance(declarations, list):
        raise DesignCandidateControlError("Candidate receipt declarations must be an array.")
    declaration_fields = frozenset({"path", "classification", "rationale"})
    for index, raw_declaration in enumerate(declarations):
        declaration = _require_exact_object(
            raw_declaration,
            declaration_fields,
            label=f"Candidate receipt declaration {index}",
        )
        _require_string(
            declaration.get("path"),
            label=f"Candidate receipt declaration {index} path",
        )
        if declaration.get("classification") not in CLAIM_IMPACT_CLASSIFICATIONS:
            raise DesignCandidateControlError(
                f"Candidate receipt declaration {index} classification is invalid."
            )
        _require_string(
            declaration.get("rationale"),
            label=f"Candidate receipt declaration {index} rationale",
        )
    _require_sha256(
        claims.get("staged_register_sha256"),
        label="Candidate receipt staged register SHA-256",
        allow_empty=True,
    )
    audit = _require_exact_object(
        claims.get("staged_register_audit"),
        frozenset({"state", "passed", "summary", "error"}),
        label="Candidate receipt staged register audit",
    )
    _require_string(audit.get("state"), label="Candidate receipt staged register audit state")
    if type(audit.get("passed")) is not bool:
        raise DesignCandidateControlError("Candidate receipt staged register audit passed must be boolean.")
    if not isinstance(audit.get("summary"), dict) or not isinstance(audit.get("error"), str):
        raise DesignCandidateControlError(
            "Candidate receipt staged register audit summary or error is malformed."
        )

    surface = _require_exact_object(
        value.get("claim_surface"),
        frozenset({"required", "state", "binding", "manifest", "result"}),
        label="Candidate receipt claim surface",
    )
    if type(surface.get("required")) is not bool:
        raise DesignCandidateControlError("Candidate receipt claim_surface.required must be boolean.")
    if surface.get("state") not in {"not-required-non-runner-candidate", "pass", "blocked"}:
        raise DesignCandidateControlError("Candidate receipt claim-surface state is unsupported.")
    if (
        not isinstance(surface.get("binding"), dict)
        or not isinstance(surface.get("manifest"), list)
        or not all(isinstance(item, dict) for item in surface["manifest"])
        or not isinstance(surface.get("result"), dict)
    ):
        raise DesignCandidateControlError("Candidate receipt claim-surface structure is malformed.")
    if surface["required"] is False and (
        surface["state"] != "not-required-non-runner-candidate"
        or surface["binding"]
        or surface["manifest"]
        or surface["result"]
    ):
        raise DesignCandidateControlError(
            "A non-runner receipt must retain the exact empty claim-surface boundary."
        )

    checks = value.get("checks")
    if not isinstance(checks, list) or len(checks) != len(CANDIDATE_CHECK_IDS):
        raise DesignCandidateControlError("Candidate receipt must contain the exact ordered check set.")
    check_fields = frozenset({"id", "passed", "message", "evidence"})
    for index, (raw_check, expected_id) in enumerate(zip(checks, CANDIDATE_CHECK_IDS, strict=True)):
        check = _require_exact_object(
            raw_check,
            check_fields,
            label=f"Candidate receipt check {index}",
        )
        if check.get("id") != expected_id or type(check.get("passed")) is not bool:
            raise DesignCandidateControlError(
                f"Candidate receipt check {index} id or boolean result is malformed."
            )
        _require_string(check.get("message"), label=f"Candidate receipt check {index} message")
        if not isinstance(check.get("evidence"), dict):
            raise DesignCandidateControlError(f"Candidate receipt check {index} evidence must be an object.")
    if value.get("next_gate") != NEXT_CANDIDATE_GATE:
        raise DesignCandidateControlError("Candidate receipt next gate is not the fixed current boundary.")


def _validation_input_bytes(value: Mapping[str, Any]) -> bytes:
    try:
        return (
            json.dumps(
                dict(value),
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise DesignCandidateControlError(
            "Candidate validation input must contain only finite standard JSON values."
        ) from exc


def _validation_input_binding(
    *,
    root: Path,
    path: Path,
    raw: bytes,
    source: Mapping[str, Any],
) -> dict[str, str]:
    return {
        "path": _relative_to_repo(root, path),
        "file_sha256": hashlib.sha256(raw).hexdigest().upper(),
        "json_sha256": _json_hash(source),
        "payload_sha256": str(source["payload_sha256"]),
    }


def _load_candidate_validation_input(
    *,
    root: Path,
    candidate_root: Path,
    work_order_binding: Mapping[str, Any],
    expected_binding: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], datetime, dict[str, str]]:
    exact_path = candidate_root / DEFAULT_VALIDATION_INPUT_NAME
    if expected_binding is not None:
        binding = _require_exact_object(
            expected_binding,
            VALIDATION_INPUT_BINDING_FIELDS,
            label="Candidate receipt validation-input binding",
        )
        if binding.get("path") != _relative_to_repo(root, exact_path):
            raise DesignCandidateControlError(
                "Candidate validation input must use its exact deterministic staged path."
            )
    path = _strict_artifact_json_path(
        root,
        exact_path,
        allowed_root=candidate_root,
        label="Candidate validation input",
    )
    if path != exact_path.resolve(strict=True):
        raise DesignCandidateControlError("Candidate validation-input path is not exact.")
    raw = path.read_bytes()
    source = _strict_json_object(raw, label="Candidate validation input")
    _require_validation_input_contract(source)
    try:
        verify_source_closure(root, source.get("source_closure"))
    except DesignCandidateSourceClosureError as exc:
        raise DesignCandidateControlError(
            f"Candidate validation-input executable-source closure changed: {exc}"
        ) from exc
    if not _strict_json_equal(source.get("work_order"), work_order_binding):
        raise DesignCandidateControlError(
            "Candidate validation input is not bound to the exact current work order."
        )
    actual_binding = _validation_input_binding(
        root=root,
        path=path,
        raw=raw,
        source=source,
    )
    if expected_binding is not None and not _strict_json_equal(actual_binding, expected_binding):
        raise DesignCandidateControlError(
            "Candidate validation-input raw, canonical, or payload hash changed."
        )
    issued_at = _parse_utc_z_timestamp(
        source.get("issued_at"),
        label="Candidate validation input issued_at",
    )
    return source, issued_at, actual_binding


def _issue_candidate_validation_input(
    *,
    root: Path,
    candidate_root: Path,
    work_order_binding: Mapping[str, Any],
    claim_impacts: Sequence[Mapping[str, Any]],
    claim_surface_context: Mapping[str, Any] | None,
    claim_surface_manifest: Sequence[Mapping[str, Any]] | None,
    now: datetime | None,
) -> tuple[dict[str, Any], datetime, dict[str, str]]:
    surface = {
        "required": claim_surface_context is not None,
        "binding": dict(claim_surface_context or {}),
        "manifest": [dict(item) for item in (claim_surface_manifest or [])],
    }
    _require_json_value(surface, label="Candidate validation-input claim surface")
    unsigned: dict[str, Any] = {
        "schema": VALIDATION_INPUT_SCHEMA,
        "issued_at": _utc_iso(now),
        "work_order": dict(work_order_binding),
        "source_closure": build_source_closure(root),
        "claim_impacts": [dict(item) for item in claim_impacts],
        "claim_surface": surface,
        "authority": dict(VALIDATION_INPUT_AUTHORITY),
    }
    source = {**unsigned, "payload_sha256": _json_hash(unsigned)}
    _require_validation_input_contract(source)
    output = candidate_root / DEFAULT_VALIDATION_INPUT_NAME
    raw = _validation_input_bytes(source)
    if output.exists() or output.is_symlink():
        existing, issued_at, binding = _load_candidate_validation_input(
            root=root,
            candidate_root=candidate_root,
            work_order_binding=work_order_binding,
        )
        if not _strict_json_equal(existing, source) or output.read_bytes() != raw:
            raise DesignCandidateControlError(
                "Candidate validation input already exists with different immutable inputs; "
                "issue a successor candidate."
            )
        return existing, issued_at, binding
    try:
        secure_immutable_artifact.write_new_file(output, raw)
    except secure_immutable_artifact.SecureImmutableArtifactError as exc:
        raise DesignCandidateControlError(
            f"Candidate validation input could not be created immutably: {exc}"
        ) from exc
    return _load_candidate_validation_input(
        root=root,
        candidate_root=candidate_root,
        work_order_binding=work_order_binding,
    )


def create_design_work_order(
    *,
    goal: str,
    allowed_paths: Sequence[str],
    routes: Sequence[str] = (),
    reconciliation_receipt: Path | None = None,
    owner_source_decision: Path | None = None,
    backup_receipt: Path | None = None,
    allowed_new_origins: Sequence[str] = (),
    run_id: str | None = None,
    repo_root: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Create a precise, source-bound order for a staged design candidate.

    allowed_paths is intentionally an exact file allow-list, not a broad
    website directory. This makes the task narrow enough for an autonomous
    worker to prove.
    """

    root = _find_repo_root(repo_root)
    objective = str(goal or "").strip()
    if not objective:
        raise DesignCandidateControlError("A design work order needs a bounded goal.")
    safe_paths = sorted({_safe_relative_path(path) for path in allowed_paths})
    if not safe_paths:
        raise DesignCandidateControlError("A design work order needs at least one exact allowed path.")
    if len(safe_paths) > MAX_AUTONOMOUS_ALLOWED_PATHS:
        raise DesignCandidateControlError(
            "Autonomous candidate work orders may cover at most "
            f"{MAX_AUTONOMOUS_ALLOWED_PATHS} exact public paths; split the work or use a separate owner route."
        )
    unsafe_paths = [path for path in safe_paths if _blocked_file(path) or not _allowed_file(path)]
    if unsafe_paths:
        raise DesignCandidateControlError(
            "Candidate work orders may not authorize blocked or unsupported public paths: "
            + ", ".join(unsafe_paths)
        )
    safe_routes = sorted({_safe_route(route) for route in routes})
    if reconciliation_receipt is None:
        raise DesignCandidateControlError(
            "A current live-surface reconciliation receipt is required before an autonomous candidate work order."
        )
    reconciliation = _reconciliation_binding(
        root=root,
        routes=safe_routes,
        reconciliation_receipt=reconciliation_receipt,
        owner_source_decision=owner_source_decision,
        backup_receipt=backup_receipt,
    )
    safe_origins = sorted({_safe_origin(origin) for origin in allowed_new_origins})
    if safe_origins:
        raise DesignCandidateControlError(
            "Autonomous design candidates may not introduce remote origins; "
            "use a separately owner-controlled integration route."
        )
    resolved_run_id = _safe_run_id(run_id or uuid.uuid4().hex)

    source_root, source_binding = _candidate_source_root(root, reconciliation)
    baseline = _tree_summary(_file_manifest(source_root))
    if source_binding is not None and (
        source_binding.get("baseline_tree_sha256") != baseline["tree_sha256"]
        or source_binding.get("file_count") != baseline["file_count"]
        or source_binding.get("total_bytes") != baseline["total_bytes"]
    ):
        raise DesignCandidateControlError(
            "Verified-live-backup source changed while the design work order was created."
        )
    register_path = root / DEFAULT_CLAIM_REGISTER
    register = _read_json(register_path, label="Claim register")
    config_path = root / DEFAULT_OPERATOR_CONFIG
    if not config_path.is_file():
        raise DesignCandidateControlError(
            f"WebsiteOperator config required for a candidate work order: {config_path}"
        )
    candidate_root = _candidate_root(root, resolved_run_id)
    editorial_asset_control = _editorial_asset_control(
        root=root,
        run_id=resolved_run_id,
        allowed_paths=safe_paths,
    )
    order = {
        "schema": WORK_ORDER_SCHEMA,
        "created_at": _utc_iso(now),
        "run_id": resolved_run_id,
        "goal": objective,
        "routes": safe_routes,
        "allowed_paths": safe_paths,
        "allowed_new_origins": safe_origins,
        "live_reconciliation": reconciliation,
        "baseline": baseline,
        "claim_control": {
            "register_path": _relative_to_repo(root, register_path),
            "register_sha256": _sha256_file(register_path),
            "bound_source_paths": _claim_source_paths(register),
            "changed_html_or_json_requires_declaration": True,
            "bound_source_change_requires_staged_register_refresh": True,
        },
        "editorial_asset_control": editorial_asset_control,
        "test_policy": {
            "path": _relative_to_repo(root, config_path),
            "sha256": _sha256_file(config_path),
        },
        "candidate_layout": {
            "root": _relative_to_repo(root, candidate_root),
            "website_path": _relative_to_repo(root, candidate_root / "website"),
            "staged_claim_register_path": _relative_to_repo(
                root, candidate_root / "claim-evidence" / register_path.name
            ),
        },
        "authority": dict(NON_AUTHORITATIVE_AUTHORITY),
    }
    require_design_work_order_contract(order)
    return order


def verify_design_work_order(
    work_order: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
    require_current_baseline: bool = True,
) -> dict[str, Any]:
    """Verify an order's immutable structure and, normally, its current baseline.

    Post-promotion provenance checks still validate the original complete
    baseline manifest, but cannot require it to equal a deliberately promoted
    canonical site.  Only internal attribution callers may set
    ``require_current_baseline=False``; this does not grant mutation, release,
    package, credential, or deployment authority.
    """

    root = _find_repo_root(repo_root)
    checks: list[dict[str, Any]] = []
    contract_error = ""
    try:
        require_design_work_order_contract(work_order)
        contract_ok = True
    except DesignCandidateControlError as exc:
        contract_ok = False
        contract_error = str(exc)
    checks.append(
        _check(
            "exact-v4-contract",
            contract_ok,
            "Work order must satisfy the complete recursive, exact-field, type-strict current v4 contract.",
            missing_fields=sorted(WORK_ORDER_FIELDS.difference(work_order)),
            unexpected_fields=sorted(set(work_order).difference(WORK_ORDER_FIELDS)),
            error=contract_error,
        )
    )
    checks.append(
        _check(
            "schema",
            work_order.get("schema") == WORK_ORDER_SCHEMA,
            "Work-order schema must match the current candidate-control contract.",
        )
    )
    checks.append(
        _check(
            "authority",
            _strict_json_equal(work_order.get("authority"), NON_AUTHORITATIVE_AUTHORITY),
            "Work orders must retain no canonical-write, package, release, credential, or deployment authority.",
        )
    )

    run_id = ""
    try:
        run_id = _safe_run_id(work_order.get("run_id"))
        run_id_ok = True
    except DesignCandidateControlError:
        run_id_ok = False
    checks.append(_check("run-id", run_id_ok, "Work order needs a safe stable candidate run id."))

    goal_ok = isinstance(work_order.get("goal"), str) and bool(str(work_order.get("goal")).strip())
    checks.append(_check("goal", goal_ok, "Work order needs a bounded non-empty objective."))

    allowed_paths: list[str] = []
    try:
        raw_paths = work_order.get("allowed_paths")
        if not isinstance(raw_paths, list) or not raw_paths:
            raise DesignCandidateControlError("allowed_paths is empty")
        allowed_paths = [_safe_relative_path(value) for value in raw_paths]
        allowlist_ok = (
            len(allowed_paths) == len(set(allowed_paths))
            and len(allowed_paths) <= MAX_AUTONOMOUS_ALLOWED_PATHS
            and all(_allowed_file(path) and not _blocked_file(path) for path in allowed_paths)
        )
    except DesignCandidateControlError:
        allowlist_ok = False
    checks.append(
        _check(
            "exact-allowlist",
            allowlist_ok,
            "Work order must declare one or more unique exact website-relative paths.",
            allowed_paths=allowed_paths,
        )
    )

    raw_routes: list[Any] = []
    try:
        candidate_routes = work_order.get("routes")
        if not isinstance(candidate_routes, list):
            raise DesignCandidateControlError("Work-order routes must be a list.")
        raw_routes = candidate_routes
        routes_ok = all(_safe_route(value) == value for value in raw_routes)
    except DesignCandidateControlError:
        routes_ok = False
    checks.append(_check("routes", routes_ok, "Work-order routes must be local canonical paths."))

    reconciliation_ok = False
    reconciliation_error = ""
    live_reconciliation = work_order.get("live_reconciliation")
    if isinstance(live_reconciliation, Mapping) and routes_ok:
        try:
            owner_binding = live_reconciliation.get("owner_source_reconciliation")
            if not isinstance(owner_binding, Mapping):
                raise DesignCandidateControlError("Owner source-reconciliation binding is missing.")
            receipt_value = live_reconciliation.get("receipt_path")
            decision_value = owner_binding.get("decision_path")
            backup_value = owner_binding.get("backup_receipt_path")
            expected_reconciliation = _reconciliation_binding(
                root=root,
                routes=raw_routes,
                reconciliation_receipt=Path(str(receipt_value or "")),
                owner_source_decision=(
                    Path(str(decision_value)) if isinstance(decision_value, str) and decision_value else None
                ),
                backup_receipt=(
                    Path(str(backup_value)) if isinstance(backup_value, str) and backup_value else None
                ),
            )
            reconciliation_ok = _strict_json_equal(live_reconciliation, expected_reconciliation)
        except DesignCandidateControlError as exc:
            reconciliation_error = str(exc)
            reconciliation_ok = False
    checks.append(
        _check(
            "live-reconciliation",
            reconciliation_ok,
            "Work order must bind a current public-surface observation and an active owner source decision after live drift.",
            error=reconciliation_error,
        )
    )

    try:
        raw_origins = work_order.get("allowed_new_origins")
        origins_ok = isinstance(raw_origins, list) and all(
            _safe_origin(value) == value for value in raw_origins
        )
        origins_ok = origins_ok and len(raw_origins or []) == len(set(raw_origins or [])) and not raw_origins
    except DesignCandidateControlError:
        origins_ok = False
    checks.append(
        _check(
            "new-origin-policy",
            origins_ok,
            "New remote origins must be explicitly named as canonical HTTPS origins.",
        )
    )

    baseline = work_order.get("baseline")
    baseline_ok = False
    baseline_current = False
    if isinstance(baseline, Mapping):
        try:
            files = baseline.get("files")
            if not isinstance(files, list):
                raise DesignCandidateControlError("Baseline files are missing.")
            summary = _tree_summary(files)
            baseline_ok = _strict_json_equal(baseline, summary)
            if reconciliation_ok and isinstance(live_reconciliation, Mapping):
                source_root, source_binding = _candidate_source_root(root, live_reconciliation)
                current = _tree_summary(_file_manifest(source_root))
                source_binding_current = source_binding is None or (
                    source_binding.get("baseline_tree_sha256") == current["tree_sha256"]
                    and source_binding.get("file_count") == current["file_count"]
                    and source_binding.get("total_bytes") == current["total_bytes"]
                )
                baseline_current = (
                    baseline_ok and _strict_json_equal(current, summary) and source_binding_current
                )
        except DesignCandidateControlError:
            baseline_ok = False
            baseline_current = False
    checks.append(
        _check(
            "baseline-shape",
            baseline_ok,
            "Work order must bind a complete deterministic website file manifest.",
        )
    )
    checks.append(
        _check(
            "baseline-current",
            baseline_current if require_current_baseline else baseline_ok,
            (
                "Canonical website changed after the work order was created; issue a fresh order."
                if require_current_baseline
                else "Original baseline manifest remains structurally valid for post-promotion attribution."
            ),
            required=require_current_baseline,
            current_matches_baseline=baseline_current,
        )
    )

    claim_control = work_order.get("claim_control")
    claim_control_ok = False
    if isinstance(claim_control, Mapping):
        try:
            expected_path = _relative_to_repo(root, root / DEFAULT_CLAIM_REGISTER)
            source_paths = claim_control.get("bound_source_paths")
            current_register = _read_json(root / DEFAULT_CLAIM_REGISTER, label="Claim register")
            claim_control_ok = (
                claim_control.get("register_path") == expected_path
                and claim_control.get("register_sha256") == _sha256_file(root / DEFAULT_CLAIM_REGISTER)
                and source_paths == _claim_source_paths(current_register)
                and claim_control.get("changed_html_or_json_requires_declaration") is True
                and claim_control.get("bound_source_change_requires_staged_register_refresh") is True
            )
        except DesignCandidateControlError:
            claim_control_ok = False
    checks.append(
        _check(
            "claim-control",
            claim_control_ok,
            "Work order must bind the current claim register and all of its website source paths.",
        )
    )

    editorial_control_ok = False
    editorial_control_error = ""
    try:
        raw_editorial_control = work_order.get("editorial_asset_control")
        if (
            not isinstance(raw_editorial_control, Mapping)
            or set(raw_editorial_control) != EDITORIAL_ASSET_CONTROL_FIELDS
            or not run_id
            or not allowlist_ok
        ):
            raise DesignCandidateControlError("Editorial asset control is missing or malformed.")
        expected_editorial_control = _editorial_asset_control(
            root=root,
            run_id=run_id,
            allowed_paths=allowed_paths,
        )
        editorial_control_ok = _strict_json_equal(raw_editorial_control, expected_editorial_control)
        if not editorial_control_ok:
            editorial_control_error = (
                "The binary-import policy, receipt path, or provenance source binding changed."
            )
    except (DesignCandidateControlError, OSError) as exc:
        editorial_control_error = str(exc)
        editorial_control_ok = False
    checks.append(
        _check(
            "editorial-asset-control",
            editorial_control_ok,
            "Work order must bind the exact trusted WebP importer, fixed receipt replay policy, and current provenance source.",
            error=editorial_control_error,
        )
    )

    test_policy = work_order.get("test_policy")
    test_policy_ok = False
    if isinstance(test_policy, Mapping):
        expected_path = _relative_to_repo(root, root / DEFAULT_OPERATOR_CONFIG)
        test_policy_ok = test_policy.get("path") == expected_path and test_policy.get(
            "sha256"
        ) == _sha256_file(root / DEFAULT_OPERATOR_CONFIG)
    checks.append(
        _check(
            "test-policy",
            test_policy_ok,
            "Work order must bind the current WebsiteOperator policy file.",
        )
    )

    layout = work_order.get("candidate_layout")
    layout_ok = False
    if isinstance(layout, Mapping) and run_id:
        candidate_root = _candidate_root(root, run_id)
        layout_ok = _strict_json_equal(
            layout,
            {
                "root": _relative_to_repo(root, candidate_root),
                "website_path": _relative_to_repo(root, candidate_root / "website"),
                "staged_claim_register_path": _relative_to_repo(
                    root,
                    candidate_root / "claim-evidence" / DEFAULT_CLAIM_REGISTER.name,
                ),
            },
        )
    checks.append(
        _check(
            "staged-layout",
            layout_ok,
            "Candidate workspace must stay in its deterministic artifacts/website-candidates location.",
        )
    )

    passed = all(check["passed"] for check in checks)
    return {
        "schema": VERIFICATION_SCHEMA,
        "state": "pass" if passed else "fail",
        "passed": passed,
        "release_eligible": False,
        "deployment_authority": "none",
        "checks": checks,
    }


def write_design_work_order(
    work_order: Mapping[str, Any],
    output_path: Path,
    *,
    repo_root: Path | None = None,
) -> Path:
    """Persist immutable work-order evidence below the candidate-artifact root."""

    root = _find_repo_root(repo_root)
    require_design_work_order_contract(work_order)
    output = output_path if output_path.is_absolute() else root / output_path
    try:
        secure_immutable_artifact.validate_no_alternate_stream_path(
            output,
            label="Design work-order output path",
        )
    except secure_immutable_artifact.SecureImmutableArtifactError as exc:
        raise DesignCandidateControlError(str(exc)) from exc
    output = Path(os.path.abspath(output))
    allowed_root = (root / DEFAULT_CANDIDATE_ROOT).resolve()
    try:
        output.resolve().relative_to(allowed_root)
    except ValueError as exc:
        raise DesignCandidateControlError(
            "Work-order evidence must stay below artifacts/website-candidates/."
        ) from exc
    try:
        run_id = _safe_run_id(work_order.get("run_id"))
        candidate_root = _candidate_root(root, run_id)
        output.resolve().relative_to(candidate_root)
    except ValueError:
        pass
    else:
        raise DesignCandidateControlError(
            "Work-order evidence must sit beside, not inside, its sealed candidate workspace."
        )
    expected_output = root / DEFAULT_CANDIDATE_ROOT / "work-orders" / f"{run_id}.v4.json"
    if output != Path(os.path.abspath(expected_output)):
        raise DesignCandidateControlError(
            "Work-order evidence must use the exact artifacts/website-candidates/work-orders/"
            "<run-id>.v4.json path."
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    raw = _work_order_bytes(work_order)
    try:
        secure_immutable_artifact.write_new_file(output, raw)
    except secure_immutable_artifact.SecureImmutableArtifactError as exc:
        raise DesignCandidateControlError(f"Design work order could not be created immutably: {exc}") from exc
    loaded, relative, loaded_raw = _load_work_order(output, root)
    if (
        not _strict_json_equal(loaded, work_order)
        or relative != _relative_to_repo(root, output)
        or loaded_raw != raw
    ):
        raise DesignCandidateControlError(
            "Design work-order immutable write failed exact JSON and raw-byte read-back."
        )
    return output


def _work_order_bytes(value: Mapping[str, Any]) -> bytes:
    try:
        return (
            json.dumps(
                dict(value),
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
            + b"\n"
        )
    except (TypeError, ValueError) as exc:
        raise DesignCandidateControlError(
            "Design work order must contain only finite standard JSON values."
        ) from exc


def _load_work_order(
    value: Mapping[str, Any] | Path,
    root: Path,
) -> tuple[dict[str, Any], str, bytes]:
    if not isinstance(value, Path):
        raise DesignCandidateControlError(
            "Candidate staging and validation require an approved persisted work-order JSON path."
        )
    path = value if value.is_absolute() else root / value
    work_order_root = root / DEFAULT_CANDIDATE_ROOT / "work-orders"
    resolved = _strict_artifact_json_path(
        root,
        path,
        allowed_root=work_order_root,
        label="Candidate work order",
    )
    raw = resolved.read_bytes()
    order = _strict_json_object(raw, label=f"Design work order: {resolved}")
    require_design_work_order_contract(order)
    if raw != _work_order_bytes(order):
        raise DesignCandidateControlError(
            "Design work-order exact persisted bytes are not the deterministic current encoding."
        )
    expected = root / DEFAULT_CANDIDATE_ROOT / "work-orders" / f"{order['run_id']}.v4.json"
    if resolved != expected.resolve(strict=True):
        raise DesignCandidateControlError(
            "Candidate work-order input must use the exact work-orders/<run-id>.v4.json path."
        )
    return order, _relative_to_repo(root, resolved), raw


def require_current_work_order_binding(
    value: object,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Replay a receipt binding against both persisted bytes and canonical JSON."""

    root = _find_repo_root(repo_root)
    binding = _require_work_order_binding(value, label="Candidate receipt work-order binding")
    order, relative, raw = _load_work_order(Path(binding["path"]), root)
    baseline = order["baseline"]
    if (
        relative != binding["path"]
        or order["run_id"] != binding["run_id"]
        or hashlib.sha256(raw).hexdigest().upper() != binding["file_sha256"]
        or _json_hash(order) != binding["sha256"]
        or baseline["tree_sha256"] != binding["baseline_tree_sha256"]
    ):
        raise DesignCandidateControlError(
            "Candidate receipt work-order binding does not match the exact persisted bytes and JSON."
        )
    return order


def _copy_verified_source_tree(
    source_root: Path,
    target_root: Path,
    expected: Mapping[str, Any],
) -> None:
    """Copy one exact manifest and prove both source and destination stability."""

    raw_files = expected.get("files")
    if not isinstance(raw_files, list):
        raise DesignCandidateControlError("Verified-live-backup baseline manifest is missing.")
    expected_summary = _tree_summary(raw_files)
    source_before = _tree_summary(_file_manifest(source_root))
    if source_before != expected_summary:
        raise DesignCandidateControlError("Verified-live-backup source changed before candidate staging.")
    target_root.mkdir(parents=True)
    source_resolved = source_root.resolve(strict=True)
    for row in expected_summary["files"]:
        relative = _safe_relative_path(row["path"])
        source = source_root / relative
        if _is_link_or_reparse_point(source):
            raise DesignCandidateControlError(
                f"Verified-live-backup source path became a link or reparse point: {relative}"
            )
        try:
            details = source.lstat()
            source.resolve(strict=True).relative_to(source_resolved)
        except (OSError, ValueError) as exc:
            raise DesignCandidateControlError(
                f"Verified-live-backup source path escaped during staging: {relative}"
            ) from exc
        if not stat.S_ISREG(details.st_mode) or int(details.st_nlink) != 1:
            raise DesignCandidateControlError(
                f"Verified-live-backup source path must remain a single-link regular file: {relative}"
            )
        if details.st_size != row["bytes"] or _sha256_file(source) != row["sha256"]:
            raise DesignCandidateControlError(
                f"Verified-live-backup source file changed before copy: {relative}"
            )
        target = target_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target, follow_symlinks=False)
        if target.stat().st_size != row["bytes"] or _sha256_file(target) != row["sha256"]:
            raise DesignCandidateControlError(
                f"Staged candidate copy does not match its verified source: {relative}"
            )
    source_after = _tree_summary(_file_manifest(source_root))
    target_summary = _tree_summary(_file_manifest(target_root))
    if source_after != source_before:
        raise DesignCandidateControlError(
            "Verified-live-backup source changed while candidate staging was in progress."
        )
    if target_summary != expected_summary:
        raise DesignCandidateControlError(
            "Staged candidate tree does not exactly match the verified-live-backup baseline."
        )


def stage_design_candidate(
    work_order: Mapping[str, Any] | Path,
    *,
    repo_root: Path | None = None,
) -> dict[str, str]:
    """Copy the selected immutable source into a sealed candidate workspace.

    This is the sole write operation in the module. It only writes a new
    artifact directory and deliberately never applies its contents to the
    canonical website tree.
    """

    root = _find_repo_root(repo_root)
    order, order_path, order_raw = _load_work_order(work_order, root)
    verification = verify_design_work_order(order, repo_root=root)
    if verification["passed"] is not True:
        failed = [check["id"] for check in verification["checks"] if check["passed"] is not True]
        raise DesignCandidateControlError("Cannot stage an invalid or stale work order: " + "; ".join(failed))
    layout = order["candidate_layout"]
    candidate_root = _resolve_under(root, layout["root"], label="Candidate root")
    website_target = _resolve_under(root, layout["website_path"], label="Candidate website")
    register_target = _resolve_under(
        root, layout["staged_claim_register_path"], label="Staged claim register"
    )
    if candidate_root.exists():
        raise DesignCandidateControlError(
            f"Candidate workspace already exists and will not be overwritten: {candidate_root}"
        )
    candidate_root.mkdir(parents=True)
    try:
        source_root, source_binding = _candidate_source_root(root, order["live_reconciliation"])
        if source_binding is None:
            shutil.copytree(root / "website", website_target, copy_function=shutil.copy2)
        else:
            _copy_verified_source_tree(source_root, website_target, order["baseline"])
        register_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / DEFAULT_CLAIM_REGISTER, register_target)
        work_order_target = candidate_root / "work-order.v4.json"
        try:
            secure_immutable_artifact.write_new_file(work_order_target, order_raw)
        except secure_immutable_artifact.SecureImmutableArtifactError as exc:
            raise DesignCandidateControlError(
                f"Staged work-order copy could not be created immutably: {exc}"
            ) from exc
        if source_binding is not None:
            final_verification = verify_design_work_order(order, repo_root=root)
            if final_verification["passed"] is not True:
                failed = [
                    check["id"] for check in final_verification["checks"] if check["passed"] is not True
                ]
                raise DesignCandidateControlError(
                    "Verified-live-backup evidence changed during candidate staging: " + "; ".join(failed)
                )
    except Exception:
        # The artifact tree is deliberately retained for investigation. It is
        # never a reason to touch the canonical website.
        raise
    return {
        "candidate_root": _relative_to_repo(root, candidate_root),
        "candidate_website": _relative_to_repo(root, website_target),
        "staged_claim_register": _relative_to_repo(root, register_target),
        "work_order": order_path or _relative_to_repo(root, work_order_target),
    }


def _claim_impact_checks(
    *,
    changed_paths: Sequence[str],
    declarations: Sequence[Mapping[str, Any]],
    bound_source_paths: set[str],
    baseline_register_sha256: str,
    staged_register: Path,
    candidate_site: Path,
    repo_root: Path,
    as_of: datetime | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    declaration_paths = sorted(
        path for path in changed_paths if Path(path).suffix.lower() in DECLARATION_REQUIRED_EXTENSIONS
    )
    checks: list[dict[str, Any]] = []
    seen: set[str] = set()
    declaration_by_path: dict[str, Mapping[str, Any]] = {}
    shape_ok = True
    for item in declarations:
        if not isinstance(item, Mapping) or set(item) != {"path", "classification", "rationale"}:
            shape_ok = False
            continue
        try:
            path = _safe_relative_path(item.get("path"))
        except DesignCandidateControlError:
            shape_ok = False
            continue
        classification = item.get("classification")
        rationale = item.get("rationale")
        if (
            path not in declaration_paths
            or path in seen
            or classification not in CLAIM_IMPACT_CLASSIFICATIONS
            or not isinstance(rationale, str)
            or not rationale.strip()
        ):
            shape_ok = False
            continue
        seen.add(path)
        declaration_by_path[path] = item
    checks.append(
        _check(
            "claim-impact-declarations",
            shape_ok and seen == set(declaration_paths),
            "Every changed public text or rendering file needs exactly one explicit claim-impact declaration.",
            changed_declaration_paths=declaration_paths,
            declared_paths=sorted(seen),
        )
    )

    bound_changes = sorted(set(declaration_paths).intersection(bound_source_paths))
    material_by_default = sorted(
        path for path in declaration_paths if Path(path).suffix.lower() in {".html", ".js", ".json", ".svg"}
    )
    material_required_paths = sorted(set(bound_changes).union(material_by_default))
    material_classification_ok = all(
        declaration_by_path.get(path, {}).get("classification") == "material-claim-change"
        for path in material_required_paths
    )
    checks.append(
        _check(
            "material-claim-source-classification",
            material_classification_ok,
            "Bound claim sources and changed HTML, JavaScript, JSON, or SVG rendering surfaces must be treated as material claim changes.",
            bound_claim_source_changes=bound_changes,
            material_by_default_paths=material_by_default,
        )
    )
    material_paths = sorted(
        path
        for path, item in declaration_by_path.items()
        if item.get("classification") == "material-claim-change"
    )
    bound_material_paths = sorted(set(material_paths).intersection(bound_source_paths))
    unbound_material_paths = sorted(set(material_paths).difference(bound_source_paths))
    staged_hash = _sha256_file(staged_register) if staged_register.is_file() else ""
    audit: Mapping[str, Any] | None = None
    audit_error = ""
    bindings: dict[str, str] = {}
    missing_bindings: list[str] = []
    stale_bindings: list[str] = []
    added_source_bindings: list[str] = []
    removed_source_bindings: list[str] = []
    added_route_bindings: list[dict[str, str]] = []
    removed_route_bindings: list[dict[str, str]] = []
    if bound_material_paths:
        try:
            audit = audit_public_claim_evidence_file(
                staged_register,
                repo_root=repo_root,
                website_root=candidate_site,
                as_of=(as_of or datetime.now(UTC)).date(),
            )
            register = _read_json(staged_register, label="Staged claim register")
            claims = register.get("claims")
            if not isinstance(claims, list):
                raise DesignCandidateControlError("Staged claim register must contain a claims list.")
            for claim in claims:
                if not isinstance(claim, Mapping) or not isinstance(claim.get("source"), Mapping):
                    continue
                source = claim["source"]
                source_path = _safe_relative_path(source.get("path"))
                if not source_path.startswith("website/"):
                    continue
                bindings[source_path.removeprefix("website/")] = str(source.get("sha256") or "").upper()
            baseline_register_path = repo_root / DEFAULT_CLAIM_REGISTER
            if _sha256_file(baseline_register_path) != baseline_register_sha256:
                raise DesignCandidateControlError(
                    "Baseline claim register changed after the candidate work order."
                )
            baseline_register = _read_json(
                baseline_register_path,
                label="Baseline claim register",
            )
            baseline_route_bindings = _claim_public_route_bindings(baseline_register)
            staged_route_bindings = _claim_public_route_bindings(register)
            baseline_routes = {(row["claim_id"], row["route"]) for row in baseline_route_bindings}
            staged_routes = {(row["claim_id"], row["route"]) for row in staged_route_bindings}
            added_route_bindings = [
                {"claim_id": claim_id, "route": route}
                for claim_id, route in sorted(staged_routes.difference(baseline_routes))
            ]
            removed_route_bindings = [
                {"claim_id": claim_id, "route": route}
                for claim_id, route in sorted(baseline_routes.difference(staged_routes))
            ]
        except (DesignCandidateControlError, PublicClaimEvidenceError, OSError) as exc:
            audit_error = str(exc)

        staged_source_paths = set(bindings)
        added_source_bindings = sorted(staged_source_paths.difference(bound_source_paths))
        removed_source_bindings = sorted(bound_source_paths.difference(staged_source_paths))
        missing_bindings = sorted(set(bound_material_paths).difference(bindings))
        for path in sorted(set(bound_material_paths).intersection(bindings)):
            target = candidate_site / path
            if not target.is_file() or bindings[path] != _sha256_file(target):
                stale_bindings.append(path)
        audit_passed = bool(audit and audit.get("passed") is True)
        refresh_ok = (
            bool(_SHA256.fullmatch(staged_hash))
            and staged_hash != baseline_register_sha256
            and audit_passed
            and not audit_error
            and not missing_bindings
            and not stale_bindings
            and not added_source_bindings
            and not removed_source_bindings
            and not added_route_bindings
            and not removed_route_bindings
        )
    else:
        refresh_ok = bool(_SHA256.fullmatch(staged_hash)) and staged_hash == baseline_register_sha256
    checks.append(
        _check(
            "staged-claim-register",
            refresh_ok,
            "Material changes to existing bound claim sources require an exact current staged-register refresh. Unbound material paths and no-material candidates must preserve the register unchanged, and a refresh may not broaden claim source or route scope.",
            material_claim_paths=material_paths,
            bound_material_claim_paths=bound_material_paths,
            unbound_material_claim_paths=unbound_material_paths,
            baseline_register_sha256=baseline_register_sha256,
            staged_register_sha256=staged_hash,
            staged_register_audit_state=audit.get("state") if audit else "not-run",
            staged_register_audit_errors=(audit or {}).get("summary", {}).get("error_count")
            if audit
            else None,
            missing_material_source_bindings=missing_bindings,
            stale_material_source_bindings=stale_bindings,
            added_source_bindings=added_source_bindings,
            removed_source_bindings=removed_source_bindings,
            added_public_route_bindings=added_route_bindings,
            removed_public_route_bindings=removed_route_bindings,
            audit_error=audit_error,
        )
    )
    return checks, {
        "changed_declaration_paths": declaration_paths,
        "bound_source_changes": bound_changes,
        "material_by_default_paths": material_by_default,
        "material_claim_paths": material_paths,
        "bound_material_claim_paths": bound_material_paths,
        "unbound_material_claim_paths": unbound_material_paths,
        "declarations": [dict(item) for item in declarations if isinstance(item, Mapping)],
        "staged_register_sha256": staged_hash,
        "staged_register_audit": {
            "state": audit.get("state") if audit else "not-run",
            "passed": audit.get("passed") if audit else False,
            "summary": dict((audit or {}).get("summary") or {}),
            "error": audit_error,
        },
    }


def validate_design_candidate(
    work_order: Mapping[str, Any] | Path,
    *,
    claim_impacts: Sequence[Mapping[str, Any]],
    claim_surface_context: Mapping[str, Any] | None = None,
    claim_surface_manifest: Sequence[Mapping[str, Any]] | None = None,
    repo_root: Path | None = None,
    now: datetime | None = None,
    _require_current_baseline: bool = True,
    _validation_input: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate a staged candidate diff without applying it to the canonical site."""

    root = _find_repo_root(repo_root)
    order, order_path, order_raw = _load_work_order(work_order, root)
    order_verification = verify_design_work_order(
        order,
        repo_root=root,
        require_current_baseline=_require_current_baseline,
    )
    raw_layout = order.get("candidate_layout")
    layout: Mapping[str, Any] = raw_layout if isinstance(raw_layout, Mapping) else {}
    candidate_root = _resolve_under(root, layout.get("root"), label="Candidate root")
    candidate_site = _resolve_under(root, layout.get("website_path"), label="Candidate website")
    staged_register = _resolve_under(
        root, layout.get("staged_claim_register_path"), label="Staged claim register"
    )
    work_order_binding = {
        "run_id": order.get("run_id"),
        "path": order_path or _relative_to_repo(root, candidate_root / "work-order.v4.json"),
        "file_sha256": hashlib.sha256(order_raw).hexdigest().upper(),
        "sha256": _json_hash(order),
        "baseline_tree_sha256": (
            order.get("baseline", {}).get("tree_sha256") if isinstance(order.get("baseline"), Mapping) else ""
        ),
    }
    _require_work_order_binding(
        work_order_binding,
        label="Candidate validation work-order binding",
    )
    if _validation_input is None:
        validation_source, validation_instant, validation_binding = _issue_candidate_validation_input(
            root=root,
            candidate_root=candidate_root,
            work_order_binding=work_order_binding,
            claim_impacts=claim_impacts,
            claim_surface_context=claim_surface_context,
            claim_surface_manifest=claim_surface_manifest,
            now=now,
        )
    else:
        validation_source, validation_instant, validation_binding = _load_candidate_validation_input(
            root=root,
            candidate_root=candidate_root,
            work_order_binding=work_order_binding,
            expected_binding=_validation_input,
        )
    raw_validation_claims = validation_source["claim_impacts"]
    effective_claim_impacts = [dict(item) for item in raw_validation_claims]
    validation_surface = validation_source["claim_surface"]
    effective_claim_surface_context = (
        dict(validation_surface["binding"]) if validation_surface["required"] is True else None
    )
    effective_claim_surface_manifest = [dict(item) for item in validation_surface["manifest"]]
    checks: list[dict[str, Any]] = [
        _check(
            "work-order-current",
            order_verification["passed"] is True,
            "Candidate must derive from a structurally valid, source-current work order.",
            failed_checks=[
                check["id"] for check in order_verification["checks"] if check["passed"] is not True
            ],
        ),
        _check(
            "candidate-workspace",
            candidate_root.is_dir()
            and candidate_site.is_dir()
            and not candidate_root.is_symlink()
            and not candidate_site.is_symlink(),
            "Candidate website must exist in the deterministic staged workspace.",
            candidate_root=_relative_to_repo(root, candidate_root)
            if candidate_root.exists()
            else str(candidate_root),
        ),
    ]
    candidate_rows: list[dict[str, Any]] = []
    if candidate_site.is_dir():
        try:
            candidate_rows = _file_manifest(candidate_site)
            manifest_ok = True
        except DesignCandidateControlError:
            manifest_ok = False
    else:
        manifest_ok = False
    checks.append(
        _check(
            "candidate-manifest",
            manifest_ok,
            "Candidate website must have a deterministic regular-file manifest without symbolic links.",
        )
    )

    baseline_rows = (
        order.get("baseline", {}).get("files", []) if isinstance(order.get("baseline"), Mapping) else []
    )
    changes: list[dict[str, Any]] = []
    try:
        changes = _change_records(baseline_rows, candidate_rows)
        changes_ok = True
    except DesignCandidateControlError:
        changes_ok = False
    checks.append(
        _check(
            "candidate-diff",
            changes_ok,
            "Candidate diff must compare against the source-bound baseline manifest.",
        )
    )
    changed_paths = [row["path"] for row in changes]
    allowed_paths = set(order.get("allowed_paths") or [])
    out_of_scope = sorted(path for path in changed_paths if path not in allowed_paths)
    checks.append(
        _check(
            "exact-scope",
            not out_of_scope,
            "Candidate may only add, modify, or remove exact paths declared by its work order.",
            changed_paths=changed_paths,
            out_of_scope_paths=out_of_scope,
        )
    )

    removed_paths = sorted(row["path"] for row in changes if row.get("change") == "removed")
    checks.append(
        _check(
            "no-public-file-removal",
            not removed_paths,
            "Autonomous candidates may refine public files but may not remove them; removal needs a separate owner-controlled route.",
            removed_paths=removed_paths,
        )
    )

    blocked_paths = sorted(path for path in changed_paths if _blocked_file(path))
    unsupported_paths = sorted(path for path in changed_paths if not _allowed_file(path))
    checks.append(
        _check(
            "blocked-files",
            not blocked_paths and not unsupported_paths,
            "Candidate may not contain secret-bearing, blocked, or unsupported public file types.",
            blocked_paths=blocked_paths,
            unsupported_paths=unsupported_paths,
        )
    )

    text_integrity_findings = _strict_text_integrity_findings(
        candidate_site,
        changes,
    )
    checks.append(
        _check(
            "strict-text-integrity",
            not text_integrity_findings,
            "Changed autonomous text files must be strict UTF-8 without control-byte or embedded base64-media payloads.",
            findings=text_integrity_findings,
        )
    )

    try:
        baseline_site, _ = _candidate_source_root(root, order["live_reconciliation"])
    except (DesignCandidateControlError, KeyError):
        baseline_site = root / "website"
    baseline_origins = _origins(baseline_site, baseline_rows) if baseline_site.is_dir() else set()
    candidate_origins = _origins(candidate_site, candidate_rows) if candidate_site.is_dir() else set()
    allowed_new_origins = set(order.get("allowed_new_origins") or [])
    new_origins = sorted(candidate_origins.difference(baseline_origins).difference(allowed_new_origins))
    checks.append(
        _check(
            "remote-origin-diff",
            not new_origins,
            "Candidate may not introduce an undeclared remote origin.",
            new_origins=new_origins,
            allowed_new_origins=sorted(allowed_new_origins),
        )
    )

    secret_findings: list[dict[str, Any]] = []
    for change in changes:
        if change["change"] == "removed":
            continue
        target = candidate_site / change["path"]
        if target.is_file():
            hits = _secret_hits(target)
            if hits:
                secret_findings.append({"path": change["path"], "matches": hits})
    checks.append(
        _check(
            "secret-scan",
            not secret_findings,
            "Changed candidate files may not contain private-key or API-key patterns.",
            findings=secret_findings,
        )
    )

    binary_replay_check = _trusted_binary_import_replay_check(
        root=root,
        order=order,
        candidate_root=candidate_root,
        candidate_site=candidate_site,
        changes=changes,
        as_of=validation_instant,
        require_current_baseline=_require_current_baseline,
    )
    checks.append(binary_replay_check)
    checks.append(
        _trusted_editorial_surface_replay_check(
            root=root,
            order=order,
            candidate_root=candidate_root,
            candidate_site=candidate_site,
            binary_replay_check=binary_replay_check,
            as_of=validation_instant,
        )
    )

    raw_claim_control = order.get("claim_control")
    claim_control: Mapping[str, Any] = raw_claim_control if isinstance(raw_claim_control, Mapping) else {}
    claim_checks, claim_summary = _claim_impact_checks(
        changed_paths=changed_paths,
        declarations=effective_claim_impacts,
        bound_source_paths=set(claim_control.get("bound_source_paths") or []),
        baseline_register_sha256=str(claim_control.get("register_sha256") or ""),
        staged_register=staged_register,
        candidate_site=candidate_site,
        repo_root=root,
        as_of=validation_instant,
    )
    checks.extend(claim_checks)

    # A generic WebsiteOperator candidate can retain the established claim
    # register control without pretending it was produced by the sealed design
    # runner.  Runner/broker candidates always pass an exact route capsule and
    # therefore fail closed on public-text surface drift.
    if effective_claim_surface_context is None:
        claim_surface = {
            "required": False,
            "state": "not-required-non-runner-candidate",
            "binding": {},
            "manifest": [],
            "result": {},
        }
        surface_ok = True
        surface_error = ""
    else:
        try:
            surface_result = evaluate_candidate_claim_surface(
                baseline_site=baseline_site,
                candidate_site=candidate_site,
                changed_paths=[row["path"] for row in changes if row.get("change") != "removed"],
                context=effective_claim_surface_context,
                manifest=effective_claim_surface_manifest,
            )
            surface_ok = surface_result.get("passed") is True
            surface_error = ""
            claim_surface = {
                "required": True,
                "state": str(surface_result.get("state") or "blocked"),
                # Only a fully validated capsule is replayable.  Never echo
                # malformed worker-provided context or free-form manifest
                # data into a durable investor-facing candidate receipt.
                "binding": dict(effective_claim_surface_context) if surface_ok else {},
                "manifest": [
                    dict(item) for item in surface_result.get("manifest", []) if isinstance(item, Mapping)
                ],
                "result": surface_result,
            }
        except DesignCandidateClaimSurfaceError as exc:
            surface_ok = False
            surface_error = str(exc)
            claim_surface = {
                "required": True,
                "state": "blocked",
                "binding": {},
                "manifest": [],
                "result": {},
            }
    checks.append(
        _check(
            "claim-surface-capsule",
            surface_ok,
            "Runner-managed candidates must bind every new public text surface to exact permitted route wording or a boundary.",
            required=claim_surface["required"],
            state=claim_surface["state"],
            error=surface_error,
        )
    )

    final_candidate_rows: list[dict[str, Any]] = []
    final_manifest_error = ""
    try:
        final_candidate_rows = _file_manifest(candidate_site)
    except DesignCandidateControlError as exc:
        final_manifest_error = str(exc)
    manifest_stable = manifest_ok and final_candidate_rows == candidate_rows
    checks.append(
        _check(
            "candidate-manifest-stable",
            manifest_stable,
            "The complete candidate manifest must remain byte-for-byte unchanged from its initial checked snapshot through final receipt construction.",
            initial_tree_sha256=(_manifest_hash(candidate_rows) if candidate_rows else ""),
            final_tree_sha256=(_manifest_hash(final_candidate_rows) if final_candidate_rows else ""),
            error=final_manifest_error,
        )
    )

    candidate_summary = (
        _tree_summary(candidate_rows)
        if candidate_rows
        else {
            "tree_sha256": "",
            "file_count": 0,
            "total_bytes": 0,
            "files": [],
        }
    )
    passed = all(check["passed"] for check in checks)
    receipt = {
        "schema": CANDIDATE_SCHEMA,
        "validated_at": _utc_iso(validation_instant),
        "state": "validated-local" if passed else "blocked",
        "passed": passed,
        "release_eligible": False,
        "deployment_authority": "none",
        "authority": dict(NON_AUTHORITATIVE_AUTHORITY),
        "validation_input": validation_binding,
        "source_closure": dict(validation_source["source_closure"]),
        "work_order": work_order_binding,
        "candidate": {
            "root": _relative_to_repo(root, candidate_root),
            "website_path": _relative_to_repo(root, candidate_site),
            "tree_sha256": candidate_summary["tree_sha256"],
            "file_count": candidate_summary["file_count"],
            "total_bytes": candidate_summary["total_bytes"],
        },
        "changes": changes,
        "claims": claim_summary,
        "claim_surface": claim_surface,
        "checks": checks,
        "next_gate": NEXT_CANDIDATE_GATE,
    }
    require_candidate_receipt_contract(receipt)
    return receipt


def write_design_candidate_receipt(
    receipt: Mapping[str, Any],
    output_path: Path,
    *,
    repo_root: Path | None = None,
) -> Path:
    """Persist candidate validation only within its staged artifact root."""

    root = _find_repo_root(repo_root)
    require_candidate_receipt_contract(receipt)
    candidate = receipt.get("candidate") if isinstance(receipt, Mapping) else None
    if not isinstance(candidate, Mapping):
        raise DesignCandidateControlError("Candidate receipt must declare its staged candidate root.")
    candidate_root = _resolve_under(root, candidate.get("root"), label="Candidate receipt root")
    output = output_path if output_path.is_absolute() else root / output_path
    output = output.resolve()
    try:
        output.relative_to(candidate_root)
    except ValueError as exc:
        raise DesignCandidateControlError(
            "Candidate validation evidence must stay inside its staged candidate root."
        ) from exc
    if output.suffix.lower() != ".json":
        raise DesignCandidateControlError("Candidate receipt output must use a .json filename.")
    return _atomic_write_json(output, receipt)


def verify_staged_candidate_receipt(
    receipt: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
    _require_current_baseline: bool = True,
) -> dict[str, Any]:
    """Revalidate one staged candidate without applying or attributing it.

    The candidate receipt is evidence, not a trust boundary by itself. This
    function reconstructs the source-bound validation from the immutable work
    order and records whether the staged tree still satisfies it. It never
    copies the candidate into ``website/``, packages it, grants credentials,
    or confers release or deployment authority.
    """

    root = _find_repo_root(repo_root)
    contract_error = ""
    try:
        require_candidate_receipt_contract(receipt)
        contract_ok = True
    except DesignCandidateControlError as exc:
        contract_ok = False
        contract_error = str(exc)
    checks: list[dict[str, Any]] = [
        _check(
            "schema",
            contract_ok,
            "Candidate receipt must satisfy the complete type-strict runtime v1 contract.",
            error=contract_error,
        ),
        _check(
            "validated-state",
            receipt.get("state") == "validated-local" and receipt.get("passed") is True,
            "Candidate receipt must have passed staged validation.",
        ),
        _check(
            "authority",
            _strict_json_equal(receipt.get("authority"), NON_AUTHORITATIVE_AUTHORITY)
            and receipt.get("release_eligible") is False
            and receipt.get("deployment_authority") == "none",
            "Candidate receipt must retain its non-authoritative boundary.",
        ),
    ]
    validated_at: datetime | None = None
    validated_at_error = ""
    try:
        validated_at = _parse_utc_z_timestamp(
            receipt.get("validated_at"),
            label="Candidate receipt validated_at",
        )
    except DesignCandidateControlError as exc:
        validated_at_error = str(exc)
    order: dict[str, Any] | None = None
    order_path: Path | None = None
    work_order_binding_ok = False
    work_order = receipt.get("work_order")
    if isinstance(work_order, Mapping):
        try:
            order = require_current_work_order_binding(work_order, repo_root=root)
            order_path = root / str(work_order["path"])
            work_order_binding_ok = True
        except (DesignCandidateControlError, ValueError):
            work_order_binding_ok = False
    checks.append(
        _check(
            "work-order-binding",
            work_order_binding_ok,
            "Candidate receipt must remain bound to an unchanged v4 source-bound work order.",
        )
    )

    candidate = receipt.get("candidate")
    layout_ok = False
    staged_ok = False
    expected_tree = ""
    candidate_root_path: Path | None = None
    if isinstance(candidate, Mapping) and isinstance(order, Mapping):
        try:
            layout = order.get("candidate_layout")
            expected_root = layout.get("root") if isinstance(layout, Mapping) else None
            expected_site = layout.get("website_path") if isinstance(layout, Mapping) else None
            layout_ok = (
                candidate.get("root") == expected_root and candidate.get("website_path") == expected_site
            )
            candidate_root_path = _resolve_under(
                root,
                candidate.get("root"),
                label="Candidate root",
            )
            candidate_site = _resolve_under(root, candidate.get("website_path"), label="Candidate website")
            expected_tree = str(candidate.get("tree_sha256") or "")
            staged_summary = _tree_summary(_file_manifest(candidate_site))
            staged_ok = (
                expected_tree == staged_summary["tree_sha256"]
                and candidate.get("file_count") == staged_summary["file_count"]
                and candidate.get("total_bytes") == staged_summary["total_bytes"]
            )
        except DesignCandidateControlError:
            staged_ok = False
            layout_ok = False
            candidate_root_path = None
    checks.append(
        _check(
            "receipt-layout-binding",
            layout_ok,
            "Candidate receipt root and website path must exactly match its immutable work-order layout.",
        )
    )
    checks.append(
        _check(
            "staged-candidate-unchanged",
            staged_ok,
            "Staged candidate changed after validation or no longer has its recorded manifest.",
            expected_tree_sha256=expected_tree,
        )
    )

    validation_input_ok = False
    validation_input_error = ""
    validation_source_at: datetime | None = None
    validation_binding: Mapping[str, Any] | None = None
    if (
        contract_ok
        and work_order_binding_ok
        and isinstance(work_order, Mapping)
        and candidate_root_path is not None
    ):
        try:
            _, validation_source_at, validation_binding = _load_candidate_validation_input(
                root=root,
                candidate_root=candidate_root_path,
                work_order_binding=work_order,
                expected_binding=receipt.get("validation_input")
                if isinstance(receipt.get("validation_input"), Mapping)
                else None,
            )
            validation_input_ok = validation_binding is not None
        except DesignCandidateControlError as exc:
            validation_input_error = str(exc)
    checks.append(
        _check(
            "validation-input-binding",
            validation_input_ok,
            "Candidate validation time, claim declarations, and claim-surface inputs must come from the unchanged create-once staged validation-input artifact.",
            error=validation_input_error,
        )
    )
    validation_time_matches = (
        validated_at is not None
        and validation_source_at is not None
        and validated_at == validation_source_at
        and receipt.get("validated_at") == _utc_iso(validation_source_at)
    )
    checks.append(
        _check(
            "validated-at",
            validation_time_matches,
            "Candidate receipt validated_at must exactly equal the independently replayed validation-input instant.",
            error=validated_at_error or validation_input_error,
        )
    )

    revalidated_ok = False
    revalidated_receipt_match = False
    revalidation_error = ""
    if (
        contract_ok
        and work_order_binding_ok
        and order_path is not None
        and validation_input_ok
        and validation_binding is not None
        and validation_time_matches
    ):
        try:
            revalidated = validate_design_candidate(
                order_path,
                claim_impacts=(),
                repo_root=root,
                _require_current_baseline=_require_current_baseline,
                _validation_input=validation_binding,
            )
            revalidated_ok = revalidated.get("passed") is True
            revalidated_receipt_match = _strict_json_equal(receipt, revalidated)
        except DesignCandidateControlError as exc:
            revalidation_error = str(exc)
    else:
        revalidation_error = (
            contract_error or validation_input_error or validated_at_error or "Prerequisite binding failed."
        )
    checks.append(
        _check(
            "candidate-control-revalidation",
            revalidated_ok and revalidated_receipt_match,
            "The complete candidate receipt must equal a timestamp-bound reconstruction of every scope, provenance, claim, check, and authority field from the immutable work order.",
            complete_receipt_match=revalidated_receipt_match,
            error=revalidation_error,
        )
    )
    passed = all(check["passed"] for check in checks)
    return {
        "schema": VERIFICATION_SCHEMA,
        "state": "pass" if passed else "fail",
        "passed": passed,
        "release_eligible": False,
        "deployment_authority": "none",
        "checks": checks,
    }


def verify_candidate_receipt_for_current_site(
    receipt: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Attribute a staged candidate to a separately promoted canonical tree.

    This is a post-promotion provenance check only. It cannot promote, package,
    approve, deploy, or replace the fresh canonical WebsiteOperator audit,
    visual review, backup, owner approval, and live HTTPS read-back sequence.
    """

    root = _find_repo_root(repo_root)
    staged = verify_staged_candidate_receipt(
        receipt,
        repo_root=root,
        _require_current_baseline=False,
    )
    checks = list(staged["checks"])
    candidate = receipt.get("candidate")
    canonical_ok = False
    expected_tree = ""
    if isinstance(candidate, Mapping):
        try:
            expected_tree = str(candidate.get("tree_sha256") or "")
            canonical_summary = _tree_summary(_file_manifest(root / "website"))
            canonical_ok = canonical_summary["tree_sha256"] == expected_tree
        except DesignCandidateControlError:
            canonical_ok = False
    checks.append(
        _check(
            "canonical-tree-matches-candidate",
            canonical_ok,
            "Current canonical website must exactly equal the validated candidate before it can be attributed to that order.",
            expected_tree_sha256=expected_tree,
        )
    )
    passed = all(check["passed"] for check in checks)
    return {
        "schema": VERIFICATION_SCHEMA,
        "state": "pass" if passed else "fail",
        "passed": passed,
        "release_eligible": False,
        "deployment_authority": "none",
        "checks": checks,
    }


def _load_claim_impacts(path: Path) -> list[Mapping[str, Any]]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8-sig"),
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except json.JSONDecodeError as exc:
        raise DesignCandidateControlError("Claim-impact input is not valid JSON.") from exc
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise DesignCandidateControlError("Claim-impact input must be a JSON list of objects.")
    return [dict(item) for item in value]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aureon-design-candidate-control",
        description="Create and validate source-bound staged Aureon website design candidates.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Create an immutable reconciled v4 candidate work order.")
    create.add_argument("--repo-root", type=Path)
    create.add_argument("--goal", required=True)
    create.add_argument("--allow", action="append", required=True, dest="allowed_paths")
    create.add_argument("--route", action="append", default=[], dest="routes")
    create.add_argument(
        "--reconciliation-receipt",
        type=Path,
        required=True,
        help="Current append-only live-surface reconciliation receipt below artifacts/website-operator/.",
    )
    create.add_argument(
        "--owner-source-decision",
        type=Path,
        help="Required only when the reconciliation detects live drift; supplied by the owner, never generated here.",
    )
    create.add_argument(
        "--backup-receipt",
        type=Path,
        help="Required with an owner source decision; must be a fresh verified Home.pl backup receipt.",
    )
    create.add_argument(
        "--allow-new-origin",
        action="append",
        default=[],
        dest="allowed_new_origins",
        help="Rejected for autonomous candidates; remote integrations need a separate owner-controlled route.",
    )
    create.add_argument("--run-id")
    create.add_argument("--output", type=Path, required=True)

    stage = subparsers.add_parser(
        "stage",
        help="Copy the reconciled selected source into a sealed artifact workspace.",
    )
    stage.add_argument("--repo-root", type=Path)
    stage.add_argument("--work-order", type=Path, required=True)

    validate = subparsers.add_parser("validate", help="Validate a staged candidate diff without applying it.")
    validate.add_argument("--repo-root", type=Path)
    validate.add_argument("--work-order", type=Path, required=True)
    validate.add_argument("--claim-impacts", type=Path, required=True)
    validate.add_argument("--output", type=Path, required=True)

    verify = subparsers.add_parser(
        "verify-current-site",
        help="Check a validated candidate against the current canonical site without applying anything.",
    )
    verify.add_argument("--repo-root", type=Path)
    verify.add_argument("--receipt", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        root = _find_repo_root(args.repo_root)
        if args.command == "create":
            order = create_design_work_order(
                goal=args.goal,
                allowed_paths=args.allowed_paths,
                routes=args.routes,
                reconciliation_receipt=args.reconciliation_receipt,
                owner_source_decision=args.owner_source_decision,
                backup_receipt=args.backup_receipt,
                allowed_new_origins=args.allowed_new_origins,
                run_id=args.run_id,
                repo_root=root,
            )
            output = write_design_work_order(order, args.output, repo_root=root)
            print(json.dumps({"work_order": order, "output": _relative_to_repo(root, output)}, indent=2))
            return 0
        if args.command == "stage":
            result = stage_design_candidate(args.work_order, repo_root=root)
            print(json.dumps(result, indent=2))
            return 0
        if args.command == "validate":
            impacts = _load_claim_impacts(args.claim_impacts)
            receipt = validate_design_candidate(args.work_order, claim_impacts=impacts, repo_root=root)
            output = write_design_candidate_receipt(receipt, args.output, repo_root=root)
            print(json.dumps({"receipt": receipt, "output": _relative_to_repo(root, output)}, indent=2))
            return 0 if receipt["passed"] else 2
        receipt = _read_json(args.receipt.resolve(), label="Candidate receipt")
        result = verify_candidate_receipt_for_current_site(receipt, repo_root=root)
        print(json.dumps(result, indent=2))
        return 0 if result["passed"] else 2
    except (DesignCandidateControlError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"state": "blocked", "error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
