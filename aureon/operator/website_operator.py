"""
Aureon Website Operator.

The public website is a high-consequence company record, not an unconstrained
generation target.  This module gives Aureon OS a deterministic tool belt for
observing, auditing, planning, packaging and (only after explicit owner
approval) publishing that record.

The default path is read-only.  Building a release writes only timestamped
local artefacts.  Deployment requires a current audit, verified release,
verified remote backup, short-lived owner approval and an exact package-hash
confirmation.  Credentials are accepted only by the existing Home.pl scripts
through the runtime environment or standard input; they are never read into a
receipt.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unicodedata
import uuid
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Sequence, cast
from urllib.parse import unquote, urljoin, urlparse

from aureon.operator.design_benchmark_evidence import (
    DesignBenchmarkEvidenceError,
    discover_design_benchmark_evidence,
    verify_design_benchmark_evidence_against_config,
)
from aureon.operator.design_candidate_control import (
    DEFAULT_EDITORIAL_IMPORT_RECEIPT_NAME,
    WORK_ORDER_SCHEMA,
    DesignCandidateControlError,
    create_design_work_order,
    stage_design_candidate,
    write_design_candidate_receipt,
    write_design_work_order,
)
from aureon.operator.design_candidate_control import (
    validate_design_candidate as validate_staged_design_candidate,
)
from aureon.operator.design_candidate_visual_review import (
    DesignCandidateVisualReviewError,
    validate_candidate_visual_review,
    write_candidate_visual_review,
)
from aureon.operator.design_editorial_asset_provenance import (
    DEFAULT_MANIFEST_PATH as DEFAULT_EDITORIAL_PROVENANCE_MANIFEST,
)
from aureon.operator.design_editorial_asset_provenance import (
    DesignEditorialAssetProvenanceError,
    audit_design_editorial_asset_provenance_file,
)
from aureon.operator.design_investor_copy_quality import (
    AUDIT_SCHEMA as INVESTOR_COPY_AUDIT_SCHEMA,
)
from aureon.operator.design_investor_copy_quality import (
    DEFAULT_POLICY_PATH as DEFAULT_INVESTOR_COPY_POLICY,
)
from aureon.operator.design_investor_copy_quality import (
    NON_AUTHORITATIVE_AUTHORITY as INVESTOR_COPY_AUTHORITY,
)
from aureon.operator.design_investor_copy_quality import (
    InvestorCopyQualityError,
    audit_investor_copy_quality_file,
)
from aureon.operator.design_learning_ledger import (
    DesignLearningLedgerError,
    validate_design_learning_record,
    write_design_learning_record,
)
from aureon.operator.design_research_refresh import (
    DesignResearchRefreshError,
    audit_design_research_sources_file,
)
from aureon.operator.design_stakeholder_feedback import (
    DesignStakeholderFeedbackError,
    audit_design_stakeholder_feedback_file,
)
from aureon.operator.live_surface_reconciliation import (
    LiveSurfaceReconciliationError,
    reconcile_live_surface,
    validate_live_surface_reconciliation,
    write_live_surface_reconciliation,
)
from aureon.operator.public_claim_evidence import (
    PublicClaimEvidenceError,
    audit_public_claim_evidence_file,
)

SCHEMA_PREFIX = "aureon.website-operator"
DEFAULT_CONFIG_NAME = "website_operator.defaults.json"
DESIGN_CYCLE_SCHEMA = "aureon-website-design-job-v1"
_AUTOMATIC_DESIGN_CYCLE_NAME = re.compile(r"\d{8}T\d{6}Z-design-cycle-[0-9a-f]{8}\.json\Z")
COMPOSITE_VISUAL_GATE_CHECK_ID = "v28-composite-visual-release-gate"
COMPOSITE_VISUAL_GATE_MANIFEST_SCHEMA = "aureon-visual-release-gate-manifest-v28.1"
COMPOSITE_VISUAL_GATE_SCRIPT = "{repo_root}/tools/aureon_visual_release_gate_v28.js"
HOMEPL_BACKUP_ROOT = Path("artifacts/homepl-backups")
HOMEPL_TRANSFER_SCHEMA = "aureon.homepl-backup-transfer.v1"
HOMEPL_ROOT_MAPPING_SCHEMA = "aureon.homepl-root-mapping.v1"
HOMEPL_TRANSFER_SOURCE_ASSERTION = "Authenticated Home.pl document-root download"
HOMEPL_ROOT_MAPPING_MAX_AGE = timedelta(minutes=15)
HOMEPL_PREFLIGHT_RECEIPT_FIELDS = frozenset(
    {
        "schema",
        "run_id",
        "generated_at",
        "repo_root",
        "site_root",
        "config_sha256",
        "state",
        "backup_script",
        "backup_script_exists",
        "backup_script_safe",
        "backup_script_sha256",
        "backup_root",
        "backup_root_safe",
        "output_directory",
        "output_directory_exists",
        "output_parent_exists",
        "output_parent_safe",
        "output_within_backup_root",
        "manifest",
        "manifest_exists",
        "root_mapping_receipt",
        "root_mapping_receipt_exists",
        "transfer_receipt",
        "transfer_receipt_exists",
        "remote_root",
        "ftp_host_id",
        "ftp_host_sha256",
        "ftp_account_sha256",
        "ftp_binding_sha256",
        "live_reconciliation_receipt",
        "live_reconciliation_receipt_sha256",
        "live_reconciliation_observed_at",
        "public_root_url",
        "public_root_sha256",
        "public_root_bytes",
        "required_root_entries",
        "credentials",
        "read_only_contract",
        "destructive_action",
        "execution_attempted",
        "note",
    }
)
HOMEPL_TRANSFER_RECEIPT_FIELDS = frozenset(
    {
        "schema",
        "state",
        "method",
        "source_assertion",
        "source_tool",
        "started_at",
        "completed_at",
        "remote_root",
        "ftp_host_id",
        "ftp_host_sha256",
        "ftp_account_sha256",
        "ftp_binding_sha256",
        "backup_directory",
        "manifest",
        "manifest_sha256",
        "file_count",
        "total_bytes",
        "preflight_receipt",
        "preflight_receipt_sha256",
        "backup_script",
        "backup_script_sha256",
        "root_mapping_receipt",
        "root_mapping_receipt_sha256",
        "live_reconciliation_receipt",
        "live_reconciliation_receipt_sha256",
        "public_root_sha256",
        "root_continuity_observed",
        "transfer_start_root_listing_sha256",
        "transfer_start_root_listing_entry_count",
        "transfer_start_root_index_sha256",
        "transfer_start_root_index_bytes",
        "transfer_end_root_listing_sha256",
        "transfer_end_root_listing_entry_count",
        "transfer_end_root_index_sha256",
        "transfer_end_root_index_bytes",
        "remote_operations",
        "remote_write_methods_used",
        "credentials_recorded",
    }
)
HOMEPL_BACKUP_RECEIPT_FIELDS = frozenset(
    {
        "schema",
        "run_id",
        "generated_at",
        "repo_root",
        "site_root",
        "config_sha256",
        "state",
        "observed_at",
        "method",
        "source_assertion",
        "remote_root",
        "ftp_host_id",
        "ftp_host_sha256",
        "ftp_account_sha256",
        "ftp_binding_sha256",
        "backup_directory",
        "manifest",
        "manifest_sha256",
        "tree_sha256",
        "file_count",
        "total_bytes",
        "preflight_receipt",
        "preflight_receipt_sha256",
        "root_mapping_receipt",
        "root_mapping_receipt_sha256",
        "root_mapping_observed_at",
        "served_root_continuity",
        "live_reconciliation_receipt",
        "live_reconciliation_receipt_sha256",
        "live_reconciliation_observed_at",
        "public_root_url",
        "public_root_sha256",
        "public_root_bytes",
        "transfer_receipt",
        "transfer_receipt_sha256",
        "backup_script",
        "backup_script_sha256",
        "complete_manifest_membership",
        "ordinary_single_link_files_only",
        "remote_write_methods_used",
        "credentials_recorded",
        "package_receipt",
        "package_sha256",
        "rollback",
    }
)
COMPOSITE_VISUAL_GATE_STDOUT_KEYS = {
    "state",
    "blockers",
    "axeViolations",
    "axeIncompleteNodes",
    "manualFailures",
    "manualUnreviewed",
    "sourceTreeSha256",
    "output",
}
RESEARCH_HYDRATION_ATTRIBUTION_SCHEMA = "aureon.research-hydration-attribution.v1"
RESEARCH_HYDRATION_ATTRIBUTION_SCRIPT = "tools/aureon_research_hydration_attribution.js"
RESEARCH_HYDRATION_ATTRIBUTION_ROOT = "artifacts/website-operator/research-hydration-attribution"
RESEARCH_HYDRATION_MINIMIZED_TRACE_SCHEMA = "aureon.research-hydration-minimized-trace.v1"
RESEARCH_HYDRATION_PROTOCOL_VERSION = "aureon.research-hydration-attribution.protocol.v2"
RESEARCH_HYDRATION_REQUIRED_SOURCE_FILES = (
    "research/index.html",
    "script.js",
    "data/research.json",
    "data/research-catalogue.json",
)
RESEARCH_HYDRATION_TARGET_IDS = (
    "research-register-hydration",
    "research-profiles-hydration",
    "research-notes-hydration",
    "research-catalogue-hydration",
)
RESEARCH_HYDRATION_MARKER_PREFIX_RE = re.compile(r"^aureon-attribution:[a-f0-9]{24}:$")
DESIGN_NEXUS_WEIGHTS = {
    "source_strength": 0.30,
    "coherence": 0.25,
    "repeatability": 0.20,
    "feasibility": 0.15,
    "contradiction_control": 0.10,
}
TEXT_EXTENSIONS = {
    ".css",
    ".csv",
    ".html",
    ".js",
    ".json",
    ".md",
    ".svg",
    ".txt",
    ".webmanifest",
    ".xml",
}
PUBLIC_EXTENSIONS = {
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
HOMEPL_RELEASE_SCHEMA_V3 = "aureon-homepl-audited-release-v3"
HOMEPL_V3_REQUIRED_PATHS = {".htaccess"}


class WebsiteOperatorError(RuntimeError):
    """A deterministic operator boundary or validation failure."""


@dataclass
class Finding:
    """One inspectable audit result."""

    code: str
    severity: str
    message: str
    path: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
        }
        if self.path:
            result["path"] = self.path
        if self.evidence:
            result["evidence"] = dict(self.evidence)
        return result


@dataclass
class CommandResult:
    """Sanitised result from an allow-listed external tool."""

    returncode: int
    stdout: str = ""
    stderr: str = ""


CommandRunner = Callable[[Sequence[str], Path], CommandResult]


def _default_runner(command: Sequence[str], cwd: Path) -> CommandResult:
    completed = subprocess.run(
        list(command),
        cwd=str(cwd),
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return CommandResult(
        returncode=int(completed.returncode),
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime | None = None) -> str:
    return (value or _utc_now()).astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise WebsiteOperatorError(f"{label} must be a non-empty ISO-8601 timestamp.")
    normalised = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalised)
    except ValueError as exc:
        raise WebsiteOperatorError(f"{label} is not a valid ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None:
        raise WebsiteOperatorError(f"{label} must include a timezone.")
    return parsed.astimezone(UTC)


def _read_json(path: Path) -> Dict[str, Any]:
    def unique_object(pairs: List[tuple[str, Any]]) -> Dict[str, Any]:
        value: Dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise WebsiteOperatorError(f"Duplicate JSON object field in {path}: {key}")
            value[key] = item
        return value

    try:
        value = json.loads(
            path.read_text(encoding="utf-8-sig"),
            object_pairs_hook=unique_object,
        )
    except FileNotFoundError as exc:
        raise WebsiteOperatorError(f"Required JSON file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise WebsiteOperatorError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise WebsiteOperatorError(f"Expected a JSON object in {path}.")
    return value


def _regular_single_link_file(path: Path, *, label: str) -> Path:
    """Require one lexical, non-reparse, ordinary file without following aliases."""

    lexical = Path(os.path.abspath(path))
    for component in (lexical, *lexical.parents):
        if not component.exists() and not component.is_symlink():
            continue
        try:
            component_stat = component.lstat()
        except OSError as exc:
            raise WebsiteOperatorError(f"{label} could not be inspected safely.") from exc
        attributes = int(getattr(component_stat, "st_file_attributes", 0) or 0)
        reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0) or 0)
        if component.is_symlink() or (reparse_flag and attributes & reparse_flag):
            raise WebsiteOperatorError(f"{label} may not traverse a link or reparse point.")
    if not lexical.is_file():
        raise WebsiteOperatorError(f"{label} must be an existing regular file.")
    try:
        file_stat = lexical.stat()
    except OSError as exc:
        raise WebsiteOperatorError(f"{label} could not be inspected safely.") from exc
    if int(file_stat.st_nlink) != 1:
        raise WebsiteOperatorError(f"{label} must have exactly one hard link.")
    return lexical


def _regular_directory(path: Path, *, label: str) -> Path:
    """Require one lexical directory path without link or reparse traversal."""

    lexical = Path(os.path.abspath(path))
    for component in (lexical, *lexical.parents):
        if not component.exists() and not component.is_symlink():
            continue
        try:
            component_stat = component.lstat()
        except OSError as exc:
            raise WebsiteOperatorError(f"{label} could not be inspected safely.") from exc
        attributes = int(getattr(component_stat, "st_file_attributes", 0) or 0)
        reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0) or 0)
        if component.is_symlink() or (reparse_flag and attributes & reparse_flag):
            raise WebsiteOperatorError(f"{label} may not traverse a link or reparse point.")
    if not lexical.is_dir():
        raise WebsiteOperatorError(f"{label} must be an existing regular directory.")
    return lexical


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    path = Path(os.path.abspath(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise WebsiteOperatorError(f"Refusing to overwrite receipt: {path}")
    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(dict(payload), stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary_path, path)
        except FileExistsError as exc:
            raise WebsiteOperatorError(f"Refusing to overwrite receipt: {path}") from exc
        except OSError as exc:
            raise WebsiteOperatorError(
                f"Could not atomically retain new receipt without replacement: {path}"
            ) from exc
        try:
            directory_handle = os.open(path.parent, os.O_RDONLY)
        except OSError:
            directory_handle = None
        if directory_handle is not None:
            try:
                os.fsync(directory_handle)
            except OSError:
                pass
            finally:
                os.close(directory_handle)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
    return _regular_single_link_file(path, label="New receipt")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest().upper()


def _sha256_json(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return _sha256_bytes(encoded.encode("utf-8"))


def _safe_relative_path(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WebsiteOperatorError("A relative path is empty.")
    normalised = value.replace("\\", "/").lstrip("/")
    path = Path(normalised)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise WebsiteOperatorError(f"Unsafe relative path: {value}")
    return normalised


def _normalise_design_route(value: object) -> str:
    """Map a public website route to its safe, website-relative HTML file.

    Design briefs naturally name routes such as ``/research/`` while package
    and audit logic works with files such as ``research/index.html``.  Keep
    that translation explicit and fail closed for values that would not name
    one local public route.
    """
    if not isinstance(value, str) or not value.strip():
        raise WebsiteOperatorError("A design route is empty.")
    parsed = urlparse(value.strip())
    if parsed.scheme or parsed.netloc or parsed.params or parsed.query or parsed.fragment:
        raise WebsiteOperatorError(
            "A design route must be a local path without a query, fragment, or URL origin."
        )
    route_path = unquote(parsed.path).replace("\\", "/")
    if route_path in {"", "/"}:
        return "index.html"
    relative = _safe_relative_path(route_path)
    if route_path.endswith("/") or not Path(relative).suffix:
        return f"{relative.rstrip('/')}/index.html"
    return relative


def _safe_repo_path(repo_root: Path, value: object) -> Path:
    relative = _safe_relative_path(value)
    candidate = (repo_root / relative).resolve()
    try:
        candidate.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise WebsiteOperatorError(f"Path escapes the repository: {value}") from exc
    return candidate


def _find_repo_root(start: Path | None = None) -> Path:
    candidate = (start or Path.cwd()).resolve()
    for directory in (candidate, *candidate.parents):
        if (directory / "pyproject.toml").is_file() and (directory / "website").is_dir():
            return directory
    raise WebsiteOperatorError("Could not locate an Aureon repository with pyproject.toml and website/.")


def _tree_hash(root: Path, files: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted((item.resolve() for item in files), key=lambda item: item.as_posix().lower()):
        relative = path.relative_to(root.resolve()).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(_sha256_file(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest().upper()


def _path_below(path: Path, root: Path) -> bool:
    """Return whether one absolute path is a proper descendant of another."""

    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    return bool(relative.parts)


def _complete_regular_tree_files(root: Path, *, label: str) -> List[Path]:
    """Enumerate a tree without accepting aliases, reparse points, or hard links."""

    root = _regular_directory(root, label=label)
    files: List[Path] = []
    seen_casefold: set[str] = set()
    for current, directory_names, file_names in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        for name in directory_names:
            _regular_directory(current_path / name, label=f"{label} directory")
        for name in file_names:
            path = _regular_single_link_file(current_path / name, label=f"{label} file")
            relative = path.relative_to(root).as_posix()
            canonical = _safe_relative_path(relative)
            if relative != canonical:
                raise WebsiteOperatorError(f"{label} contains a non-canonical path: {relative}")
            folded = canonical.casefold()
            if folded in seen_casefold:
                raise WebsiteOperatorError(f"{label} contains a case-colliding path: {relative}")
            seen_casefold.add(folded)
            files.append(path)
    return sorted(files, key=lambda item: item.relative_to(root).as_posix().casefold())


def _homepl_ftp_identity(ftp_host: object, ftp_account: object) -> Dict[str, str]:
    """Return copy-minimised exact bindings for one Home.pl FTPS identity."""

    if not isinstance(ftp_host, str) or ftp_host != ftp_host.strip():
        raise WebsiteOperatorError("FTPS host must be one trimmed hostname with an optional port.")
    match = re.fullmatch(
        r"(?i)([a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?)(?::([0-9]{1,5}))?",
        ftp_host,
    )
    if match is None:
        raise WebsiteOperatorError("FTPS host must be one hostname with an optional port.")
    host_name = match.group(1).lower()
    if any(not label or len(label) > 63 for label in host_name.split(".")):
        raise WebsiteOperatorError("FTPS host contains an invalid DNS label.")
    port = int(match.group(2) or "21")
    if not 1 <= port <= 65535:
        raise WebsiteOperatorError("FTPS host port is outside the valid range.")
    host_id = f"{host_name}:{port}"

    if not isinstance(ftp_account, str) or ftp_account != ftp_account.strip():
        raise WebsiteOperatorError("FTPS account identifier must be one trimmed non-empty string.")
    account_id = unicodedata.normalize("NFC", ftp_account)
    if (
        not account_id
        or len(account_id) > 256
        or any(unicodedata.category(character).startswith("C") for character in account_id)
    ):
        raise WebsiteOperatorError("FTPS account identifier contains unsupported characters.")
    host_sha256 = _sha256_bytes(host_id.encode("utf-8"))
    account_sha256 = _sha256_bytes(account_id.encode("utf-8"))
    binding_sha256 = _sha256_bytes(f"{host_id}\0{account_id}".encode())
    return {
        "ftp_host_id": host_id,
        "ftp_host_sha256": host_sha256,
        "ftp_account_sha256": account_sha256,
        "ftp_binding_sha256": binding_sha256,
    }


def _homepl_required_root_entries(required_paths: Iterable[object]) -> List[str]:
    """Return the unique immediate names visible in an authenticated `/` listing."""

    entries: List[str] = []
    seen: set[str] = set()
    for value in required_paths:
        relative = _safe_relative_path(value)
        entry = relative.split("/", 1)[0]
        folded = entry.casefold()
        if folded not in seen:
            entries.append(entry)
            seen.add(folded)
    return entries


def _research_attribution_tree_snapshot(root: Path) -> Dict[str, Any]:
    """Mirror the Node attribution snapshot contract for receipt read-back.

    The JavaScript diagnostic snapshots every ordinary file in code-unit path
    order using ``path NUL bytes NUL file_sha256 LF``.  Recompute that exact
    lower-case digest here so a subprocess cannot bind its receipt to an old
    or different source tree.
    """
    resolved_root = root.resolve()
    if not resolved_root.is_dir():
        raise WebsiteOperatorError(f"Research attribution source is missing: {resolved_root}")
    rows: list[Dict[str, Any]] = []
    for item in resolved_root.rglob("*"):
        if item.is_symlink():
            raise WebsiteOperatorError(
                f"Research attribution source contains an unsupported symbolic link: {item}"
            )
        if not item.is_file():
            continue
        relative = item.relative_to(resolved_root).as_posix()
        rows.append(
            {
                "path": relative,
                "bytes": item.stat().st_size,
                "sha256": _sha256_file(item).lower(),
            }
        )
    rows.sort(key=lambda row: str(row["path"]))
    digest = hashlib.sha256()
    for row in rows:
        digest.update(str(row["path"]).encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(row["bytes"]).encode("ascii"))
        digest.update(b"\0")
        digest.update(str(row["sha256"]).encode("ascii"))
        digest.update(b"\n")
    return {
        "sha256": digest.hexdigest(),
        "file_count": len(rows),
        "total_bytes": sum(int(row["bytes"]) for row in rows),
        "files": rows,
    }


def _require_research_attribution_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise WebsiteOperatorError(f"Research hydration attribution {label} must be an object.")
    return value


def _require_research_attribution_int(value: object, label: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise WebsiteOperatorError(
            f"Research hydration attribution {label} must be an integer of at least {minimum}."
        )
    return value


def _require_research_attribution_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value):
        raise WebsiteOperatorError(
            f"Research hydration attribution {label} must be a lower-case SHA-256 digest."
        )
    return value


def _short_output(value: str, limit: int = 2000) -> str:
    clean = value.replace("\x00", "").strip()
    return clean if len(clean) <= limit else clean[-limit:]


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _command_exists(executable: str) -> bool:
    return shutil.which(executable) is not None


class PageParser(HTMLParser):
    """Small dependency-free parser for metadata, structure and local references."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lang = ""
        self.title = ""
        self._in_title = False
        self.h1_count = 0
        self.meta: Dict[str, str] = {}
        self.canonical = ""
        self.ids: List[str] = []
        self.references: List[Dict[str, str]] = []
        self.images_without_alt = 0
        self.autoplay_media = 0
        self.json_ld_count = 0
        self._interactive_stack: List[Dict[str, Any]] = []
        self.inaccessible_interactions = 0
        self.text_parts: List[str] = []

    @staticmethod
    def _attributes(attrs: List[tuple[str, str | None]]) -> Dict[str, str]:
        return {str(name).lower(): str(value or "") for name, value in attrs}

    def handle_starttag(self, tag: str, attrs: List[tuple[str, str | None]]) -> None:
        attributes = self._attributes(attrs)
        tag = tag.lower()
        if tag == "html":
            self.lang = attributes.get("lang", "").strip()
        elif tag == "title":
            self._in_title = True
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "meta":
            key = (attributes.get("name") or attributes.get("property") or "").strip().lower()
            if key:
                self.meta[key] = attributes.get("content", "").strip()
        elif tag == "link" and "canonical" in attributes.get("rel", "").lower().split():
            self.canonical = attributes.get("href", "").strip()
        elif tag == "script" and attributes.get("type", "").lower() == "application/ld+json":
            self.json_ld_count += 1

        element_id = attributes.get("id", "").strip()
        if element_id:
            self.ids.append(element_id)

        if tag == "img" and "alt" not in attributes:
            self.images_without_alt += 1
        if tag in {"audio", "video"} and "autoplay" in attributes:
            self.autoplay_media += 1

        for attribute in ("href", "src", "poster"):
            value = attributes.get(attribute, "").strip()
            if value:
                self.references.append({"tag": tag, "attribute": attribute, "value": value})
        for attribute in ("srcset",):
            for candidate in attributes.get(attribute, "").split(","):
                value = candidate.strip().split(" ", 1)[0]
                if value:
                    self.references.append({"tag": tag, "attribute": attribute, "value": value})

        if tag in {"a", "button"}:
            self._interactive_stack.append(
                {
                    "tag": tag,
                    "named": bool(
                        attributes.get("aria-label", "").strip()
                        or attributes.get("aria-labelledby", "").strip()
                        or attributes.get("title", "").strip()
                        or (tag == "a" and attributes.get("href", "").strip() == "")
                    ),
                    "text": [],
                }
            )

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
        if tag in {"a", "button"} and self._interactive_stack:
            interactive = self._interactive_stack.pop()
            text = " ".join(str(item) for item in interactive["text"]).strip()
            if not interactive["named"] and not text:
                self.inaccessible_interactions += 1

    def handle_data(self, data: str) -> None:
        clean = " ".join(data.split())
        if not clean:
            return
        if self._in_title:
            self.title = f"{self.title} {clean}".strip()
        if self._interactive_stack:
            self._interactive_stack[-1]["text"].append(clean)
        self.text_parts.append(clean)

    @property
    def text(self) -> str:
        return " ".join(self.text_parts)


class _EditorialSemanticHTMLParser(HTMLParser):
    """Count nearby Substack/WebP pairs that lack an editorial surface marker."""

    _VOID_ELEMENTS = frozenset(
        {
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        }
    )

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._stack: list[dict[str, Any]] = []
        self.ambiguous_pair_count = 0

    @staticmethod
    def _attributes(attrs: List[tuple[str, str | None]]) -> Dict[str, str]:
        return {str(name).casefold(): str(value or "").strip() for name, value in attrs}

    @staticmethod
    def _is_substack_url(value: str) -> bool:
        try:
            parsed = urlparse(value)
        except ValueError:
            return False
        host = str(parsed.hostname or "").casefold().rstrip(".")
        return parsed.scheme.casefold() in {"http", "https"} and (
            host == "substack.com" or host.endswith(".substack.com")
        )

    @staticmethod
    def _has_webp_reference(value: str) -> bool:
        for candidate in value.split(","):
            pieces = candidate.strip().split(None, 1)
            if not pieces:
                continue
            token = pieces[0]
            try:
                path = urlparse(token).path
            except ValueError:
                path = token
            if path.casefold().endswith(".webp"):
                return True
        return False

    def _finalise_top(self) -> None:
        if not self._stack:
            return
        node = self._stack.pop()
        substack_distance = node.get("substack_distance")
        webp_distance = node.get("webp_distance")
        paired_here = (
            node.get("protected") is not True
            and isinstance(substack_distance, int)
            and isinstance(webp_distance, int)
            and substack_distance <= 2
            and webp_distance <= 2
        )
        if paired_here:
            self.ambiguous_pair_count += 1
            substack_distance = None
            webp_distance = None
        if not self._stack or self._stack[-1].get("protected") is True:
            return
        parent = self._stack[-1]
        if isinstance(substack_distance, int):
            candidate_distance = substack_distance + 1
            current = parent.get("substack_distance")
            if not isinstance(current, int) or candidate_distance < current:
                parent["substack_distance"] = candidate_distance
        if isinstance(webp_distance, int):
            candidate_distance = webp_distance + 1
            current = parent.get("webp_distance")
            if not isinstance(current, int) or candidate_distance < current:
                parent["webp_distance"] = candidate_distance

    def handle_starttag(self, tag: str, attrs: List[tuple[str, str | None]]) -> None:
        tag = tag.casefold()
        attributes = self._attributes(attrs)
        protected = bool(
            (self._stack and self._stack[-1].get("protected") is True)
            or "data-editorial-surface-id" in attributes
        )
        node: dict[str, Any] = {
            "tag": tag,
            "protected": protected,
            "substack_distance": None,
            "webp_distance": None,
        }
        if not protected:
            href = attributes.get("href", "")
            if href and self._is_substack_url(href):
                node["substack_distance"] = 0
            for name in ("src", "srcset", "poster", "content"):
                if self._has_webp_reference(attributes.get(name, "")):
                    node["webp_distance"] = 0
                    break
        self._stack.append(node)
        if tag in self._VOID_ELEMENTS:
            self._finalise_top()

    def handle_startendtag(self, tag: str, attrs: List[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if self._stack and self._stack[-1].get("tag") == tag.casefold():
            self._finalise_top()

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        matching_index = next(
            (index for index in range(len(self._stack) - 1, -1, -1) if self._stack[index].get("tag") == tag),
            None,
        )
        if matching_index is None:
            return
        while len(self._stack) > matching_index:
            self._finalise_top()

    def handle_data(self, data: str) -> None:
        if not self._stack or self._stack[-1].get("protected") is True:
            return
        node = self._stack[-1]
        if re.search(
            r"https?://[^\s\"'<>]*substack\.com(?:[/?#][^\s\"'<>]*)?",
            data,
            flags=re.IGNORECASE,
        ):
            node["substack_distance"] = 0
        if re.search(
            r"(?<![A-Za-z0-9])[^ \t\r\n\"'<>]*\.webp(?:[?#][^\s\"'<>]*)?",
            data,
            flags=re.IGNORECASE,
        ):
            node["webp_distance"] = 0

    def close(self) -> None:
        super().close()
        while self._stack:
            self._finalise_top()


class WebsiteOperator:
    """Deterministic website lifecycle controller."""

    def __init__(
        self,
        repo_root: Path,
        config: Mapping[str, Any],
        receipts_dir: Path,
        runner: CommandRunner = _default_runner,
        *,
        config_path: Path | None = None,
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.config = dict(config)
        self.config_path = config_path.resolve() if config_path is not None else None
        self.receipts_dir = receipts_dir.resolve()
        self.runner = runner
        self._validate_config()
        self.site_root = _safe_repo_path(self.repo_root, self.config["site"]["root"])
        if not self.site_root.is_dir():
            raise WebsiteOperatorError(f"Configured website root is missing: {self.site_root}")
        self.config_sha256 = _sha256_json(self.config)

    @classmethod
    def from_paths(
        cls,
        repo_root: Path | None = None,
        config_path: Path | None = None,
        receipts_dir: Path | None = None,
        runner: CommandRunner = _default_runner,
    ) -> WebsiteOperator:
        root = _find_repo_root(repo_root)
        source = (config_path or Path(__file__).with_name(DEFAULT_CONFIG_NAME)).resolve()
        config = _read_json(source)
        output = receipts_dir or (root / "artifacts" / "website-operator")
        return cls(root, config, output, runner=runner, config_path=source)

    def _validate_config(self) -> None:
        if self.config.get("schema") != f"{SCHEMA_PREFIX}.config.v1":
            raise WebsiteOperatorError("Unsupported website operator config schema.")
        for section in ("site", "ethos", "budgets", "checks", "packaging", "deployment"):
            if not isinstance(self.config.get(section), dict):
                raise WebsiteOperatorError(f"Config section '{section}' must be an object.")
        site = self.config["site"]
        if not isinstance(site.get("root"), str) or not isinstance(site.get("base_url"), str):
            raise WebsiteOperatorError("site.root and site.base_url are required.")
        base = urlparse(site["base_url"])
        if base.scheme != "https" or not base.netloc:
            raise WebsiteOperatorError("site.base_url must be an absolute HTTPS URL.")
        deployment = self.config["deployment"]
        if deployment.get("remote_root") != "/":
            raise WebsiteOperatorError(
                "The verified Home.pl document root must be explicit and equal to '/'."
            )
        if deployment.get("automatic_rollback") is not False:
            raise WebsiteOperatorError("Automatic rollback must remain disabled.")
        if deployment.get("credentials_in_receipts") is not False:
            raise WebsiteOperatorError("Credentials in receipts must remain disabled.")
        design = self.config.get("design", {})
        if design and not isinstance(design, dict):
            raise WebsiteOperatorError("Config section 'design' must be an object when provided.")
        weights = design.get("nexus_weights", DESIGN_NEXUS_WEIGHTS)
        if not isinstance(weights, dict) or set(weights) != set(DESIGN_NEXUS_WEIGHTS):
            raise WebsiteOperatorError("design.nexus_weights must define the five Design Nexus dimensions.")
        try:
            weight_total = sum(float(value) for value in weights.values())
        except (TypeError, ValueError) as exc:
            raise WebsiteOperatorError("design.nexus_weights values must be numeric.") from exc
        if abs(weight_total - 1.0) > 0.000001:
            raise WebsiteOperatorError("design.nexus_weights must sum to 1.0.")
        for source in design.get("competitor_sources", []):
            if not isinstance(source, dict):
                raise WebsiteOperatorError("Each design.competitor_sources item must be an object.")
            parsed = urlparse(str(source.get("url") or ""))
            if parsed.scheme != "https" or not parsed.netloc:
                raise WebsiteOperatorError("Competitor research sources must use absolute HTTPS URLs.")
        external = self.config["checks"].get("external", [])
        if not isinstance(external, list):
            raise WebsiteOperatorError("checks.external must be an array.")
        identifiers = set()
        for check in external:
            if not isinstance(check, dict):
                raise WebsiteOperatorError("Each checks.external item must be an object.")
            identifier = str(check.get("id") or "").strip()
            if not identifier:
                raise WebsiteOperatorError("Each checks.external item needs a stable id.")
            if identifier in identifiers:
                raise WebsiteOperatorError(f"Duplicate external check id: {identifier}")
            identifiers.add(identifier)
            command = check.get("command")
            if (
                not isinstance(command, list)
                or not command
                or not all(isinstance(item, str) and item for item in command)
            ):
                raise WebsiteOperatorError(
                    f"External check '{identifier}' command must be a non-empty string array."
                )
            if identifier == COMPOSITE_VISUAL_GATE_CHECK_ID:
                self._validate_composite_gate_command_config(check)

    @staticmethod
    def _validate_composite_gate_command_config(check: Mapping[str, Any]) -> None:
        if check.get("enabled") is not True or check.get("required") is not True:
            raise WebsiteOperatorError(f"{COMPOSITE_VISUAL_GATE_CHECK_ID} must be enabled and required.")
        command = check.get("command")
        expected_prefix = [
            "node",
            COMPOSITE_VISUAL_GATE_SCRIPT,
            "--repo-root",
            "{repo_root}",
            "--manifest",
        ]
        if not isinstance(command, list) or len(command) != 6 or command[:5] != expected_prefix:
            raise WebsiteOperatorError(
                f"{COMPOSITE_VISUAL_GATE_CHECK_ID} must use the canonical six-token command."
            )
        manifest_token = command[5]
        prefix = "{repo_root}/docs/audits/"
        manifest_basename = manifest_token[len(prefix) :] if manifest_token.startswith(prefix) else ""
        if (
            not manifest_token.startswith(prefix)
            or not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9._-]*"
                r"\d{8}T\d{6}(?:\d{3})?Z"
                r"[A-Za-z0-9._-]*\.manifest\.json",
                manifest_basename,
            )
            or any(character in manifest_token for character in ("<", ">", "\\"))
        ):
            raise WebsiteOperatorError(
                "Composite visual gate manifest must be one immutable, timestamped "
                "{repo_root}/docs/audits/*.manifest.json path."
            )
        _safe_relative_path(manifest_token[len("{repo_root}/") :])

    def _path_for_output(self, kind: str, output: Path | None = None) -> Path:
        if output:
            return output.resolve()
        stamp = _utc_now().strftime("%Y%m%dT%H%M%SZ")
        return self.receipts_dir / f"{stamp}-{kind}-{uuid.uuid4().hex[:8]}.json"

    def _base_receipt(self, kind: str) -> Dict[str, Any]:
        return {
            "schema": f"{SCHEMA_PREFIX}.{kind}.v1",
            "run_id": uuid.uuid4().hex,
            "generated_at": _iso(),
            "repo_root": str(self.repo_root),
            "site_root": str(self.site_root),
            "config_sha256": self.config_sha256,
        }

    def _public_files(self) -> List[Path]:
        return [
            path
            for path in self.site_root.rglob("*")
            if path.is_file()
            and path.suffix.lower() in PUBLIC_EXTENSIONS
            and not any(part in {".git", "node_modules", "__pycache__"} for part in path.parts)
        ]

    def _git_state(self) -> Dict[str, Any]:
        result = self.runner(["git", "status", "--short", "--", "website"], self.repo_root)
        if result.returncode != 0:
            return {"available": False, "error": _short_output(result.stderr)}
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        head = self.runner(["git", "rev-parse", "HEAD"], self.repo_root)
        return {
            "available": True,
            "head": head.stdout.strip() if head.returncode == 0 else "",
            "website_dirty": bool(lines),
            "website_change_count": len(lines),
            "website_changes": lines,
            "note": "Dirty state is recorded, never discarded or treated as deployment authority.",
        }

    def _capacity_context(self) -> Dict[str, Any]:
        value = self.config["site"].get("capacity_receipt")
        if not value:
            return {"available": False}
        path = _safe_repo_path(self.repo_root, value)
        receipt = _read_json(path)
        if receipt.get("schema") != f"{SCHEMA_PREFIX}.hosting-capacity.v1":
            raise WebsiteOperatorError(f"Unsupported hosting capacity receipt schema: {path}")
        return {
            "available": True,
            "path": str(path),
            "sha256": _sha256_file(path),
            "observation": receipt,
            "policy": "Hosting capacity is context only. It is not a performance or media budget.",
        }

    def inventory_payload(self) -> Dict[str, Any]:
        files = self._public_files()
        extension_counts: Dict[str, int] = Counter()
        extension_bytes: Dict[str, int] = Counter()
        largest: List[Dict[str, Any]] = []
        for path in files:
            extension = path.suffix.lower() or "[none]"
            extension_counts[extension] += 1
            extension_bytes[extension] += path.stat().st_size
        for path in sorted(files, key=lambda item: item.stat().st_size, reverse=True)[:20]:
            largest.append(
                {
                    "path": path.relative_to(self.site_root).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": _sha256_file(path),
                }
            )
        html_files = [path for path in files if path.suffix.lower() == ".html"]
        receipt = self._base_receipt("inventory")
        receipt.update(
            {
                "state": "observed-read-only",
                "tree_sha256": _tree_hash(self.site_root, files),
                "file_count": len(files),
                "total_bytes": sum(path.stat().st_size for path in files),
                "html_page_count": len(html_files),
                "extensions": [
                    {
                        "extension": extension,
                        "files": extension_counts[extension],
                        "bytes": extension_bytes[extension],
                    }
                    for extension in sorted(extension_counts)
                ],
                "largest_files": largest,
                "git": self._git_state(),
                "hosting_capacity": self._capacity_context(),
            }
        )
        return receipt

    def inventory(self, output: Path | None = None) -> Path:
        return _atomic_write_json(self._path_for_output("inventory", output), self.inventory_payload())

    def observe_live_surface(
        self,
        *,
        routes: Sequence[str] | None = None,
        output: Path | None = None,
    ) -> Path:
        """Read only the configured public HTTPS surface against canonical source.

        This is an early reconciliation signal, distinct from the exact
        package-manifest read-back performed after a successful deployment.
        It cannot change source, access credentials, create a candidate,
        package a release, back up Home.pl, approve a release or deploy.
        """

        try:
            selected = (
                [_normalise_design_route(route) for route in routes]
                if routes
                else [_safe_relative_path(route) for route in self.config["site"]["critical_routes"]]
            )
            receipt = reconcile_live_surface(
                repo_root=self.repo_root,
                site_root=self.site_root,
                base_url=str(self.config["site"]["base_url"]),
                routes=selected,
                canonical_overrides=self.config["site"].get("canonical_overrides", {}),
            )
            return cast(
                Path,
                write_live_surface_reconciliation(
                    receipt,
                    self._path_for_output("live-surface-reconciliation", output),
                    repo_root=self.repo_root,
                ),
            )
        except LiveSurfaceReconciliationError as exc:
            raise WebsiteOperatorError(f"Live-surface reconciliation failed: {exc}") from exc

    def _research_attribution_source(self, source_root: Path | None) -> Path:
        """Resolve one local-only source tree allowed for runtime attribution."""
        if source_root is None:
            return self.site_root
        source = (
            source_root.resolve() if source_root.is_absolute() else (self.repo_root / source_root).resolve()
        )
        try:
            source.relative_to(self.repo_root)
        except ValueError as exc:
            raise WebsiteOperatorError(
                "Research attribution source must remain inside this repository."
            ) from exc
        if source == self.site_root:
            return source
        candidates_root = (self.repo_root / "artifacts" / "website-candidates").resolve()
        try:
            candidate_relative = source.relative_to(candidates_root)
        except ValueError as exc:
            raise WebsiteOperatorError(
                "Research attribution may observe only canonical website/ or a staged "
                "artifacts/website-candidates/*/website tree."
            ) from exc
        if source.name != "website" or len(candidate_relative.parts) != 2:
            raise WebsiteOperatorError(
                "A staged research attribution source must be the candidate's website directory."
            )
        return source

    def _validate_research_hydration_attribution_receipt(
        self,
        payload: Mapping[str, Any],
        *,
        source: Path,
        artifact_root: Path,
        receipt: Path,
        tool: Path,
    ) -> Path:
        """Fail closed on the diagnostic's source, coverage and authority proof."""
        expected = {
            "schema": RESEARCH_HYDRATION_ATTRIBUTION_SCHEMA,
            "state": "complete",
            "analysis_only": True,
            "release_eligible": False,
            "package_authority": "none",
            "deployment_authority": "none",
        }
        if any(payload.get(key) != value for key, value in expected.items()):
            raise WebsiteOperatorError(
                "Research hydration attribution receipt must retain its analysis-only authority boundary."
            )
        _parse_datetime(payload.get("observed_at"), "Research hydration attribution observed_at")
        expected_authority = {
            "scope": "read-only staged or canonical research-route runtime attribution",
            "canonical_website_mutation": "never",
            "candidate_creation": "none",
            "release_eligibility": False,
            "package_authority": "none",
            "deployment_authority": "none",
            "credential_access": "none",
        }
        if (
            dict(_require_research_attribution_mapping(payload.get("authority"), "authority"))
            != expected_authority
        ):
            raise WebsiteOperatorError(
                "Research hydration attribution receipt has expanded or missing authority."
            )

        target = _require_research_attribution_mapping(payload.get("target"), "target")
        if set(target) != {
            "route",
            "viewport",
            "browser",
            "self_hosted",
            "response",
            "source_root",
            "source_before",
            "source_after_tree_sha256",
            "source_stable",
        }:
            raise WebsiteOperatorError("Research hydration attribution target has an unexpected shape.")
        try:
            reported_source = Path(str(target.get("source_root") or "")).resolve()
        except (OSError, ValueError) as exc:
            raise WebsiteOperatorError(
                "Research hydration attribution receipt has an invalid source binding."
            ) from exc
        if (
            reported_source != source
            or target.get("route") != "/research/"
            or target.get("browser") != "chromium"
            or target.get("self_hosted") is not True
            or target.get("source_stable") is not True
        ):
            raise WebsiteOperatorError(
                "Research hydration attribution receipt is not bound to the requested local source and route."
            )
        viewport = _require_research_attribution_mapping(target.get("viewport"), "target.viewport")
        if dict(viewport) != {"width": 1440, "height": 1000}:
            raise WebsiteOperatorError(
                "Research hydration attribution must use the fixed 1440x1000 viewport."
            )
        response = _require_research_attribution_mapping(target.get("response"), "target.response")
        status = _require_research_attribution_int(response.get("status"), "target.response.status")
        if (
            set(response) != {"status", "same_origin"}
            or not 200 <= status < 300
            or response.get("same_origin") is not True
        ):
            raise WebsiteOperatorError(
                "Research hydration attribution route did not complete successfully on same origin."
            )

        current_snapshot = _research_attribution_tree_snapshot(source)
        before = _require_research_attribution_mapping(target.get("source_before"), "target.source_before")
        if set(before) != {"root", "tree_sha256", "file_count", "total_bytes", "selected_files"}:
            raise WebsiteOperatorError(
                "Research hydration attribution source binding has an unexpected shape."
            )
        before_hash = _require_research_attribution_sha256(
            before.get("tree_sha256"), "target.source_before.tree_sha256"
        )
        after_hash = _require_research_attribution_sha256(
            target.get("source_after_tree_sha256"), "target.source_after_tree_sha256"
        )
        if (
            str(before.get("root") or "") != str(source)
            or before_hash != current_snapshot["sha256"]
            or after_hash != current_snapshot["sha256"]
            or _require_research_attribution_int(
                before.get("file_count"), "target.source_before.file_count", 1
            )
            != current_snapshot["file_count"]
            or _require_research_attribution_int(
                before.get("total_bytes"), "target.source_before.total_bytes", 1
            )
            != current_snapshot["total_bytes"]
        ):
            raise WebsiteOperatorError(
                "Research hydration attribution receipt is not bound to the current unchanged requested source tree."
            )
        selected = before.get("selected_files")
        if not isinstance(selected, list) or len(selected) != len(RESEARCH_HYDRATION_REQUIRED_SOURCE_FILES):
            raise WebsiteOperatorError(
                "Research hydration attribution source binding lacks the required selected files."
            )
        files_by_path = {str(row["path"]): row for row in current_snapshot["files"]}
        for expected_path, row in zip(RESEARCH_HYDRATION_REQUIRED_SOURCE_FILES, selected, strict=True):
            selected_row = _require_research_attribution_mapping(row, "target.source_before.selected_files[]")
            if set(selected_row) != {"path", "sha256", "bytes"} or selected_row.get("path") != expected_path:
                raise WebsiteOperatorError(
                    "Research hydration attribution selected-file path binding is invalid."
                )
            expected_file = files_by_path.get(expected_path)
            if expected_file is None or (
                _require_research_attribution_sha256(
                    selected_row.get("sha256"), "target.source_before.selected_files[].sha256"
                )
                != expected_file["sha256"]
                or _require_research_attribution_int(
                    selected_row.get("bytes"), "target.source_before.selected_files[].bytes", 1
                )
                != expected_file["bytes"]
            ):
                raise WebsiteOperatorError(
                    "Research hydration attribution selected-file digest does not match source."
                )

        instrumentation = _require_research_attribution_mapping(
            payload.get("instrumentation"), "instrumentation"
        )
        if set(instrumentation) != {
            "protocol_version",
            "protocol_sha256",
            "marker_prefix",
            "post_load_wait_ms",
            "playwright_source",
            "browser_version",
            "capture_count",
            "method",
            "non_gating",
            "caveat",
        }:
            raise WebsiteOperatorError(
                "Research hydration attribution instrumentation has an unexpected shape."
            )
        marker_prefix = instrumentation.get("marker_prefix")
        if (
            instrumentation.get("protocol_version") != RESEARCH_HYDRATION_PROTOCOL_VERSION
            or _require_research_attribution_sha256(
                instrumentation.get("protocol_sha256"), "instrumentation.protocol_sha256"
            )
            != _sha256_file(tool).lower()
            or not isinstance(marker_prefix, str)
            or not RESEARCH_HYDRATION_MARKER_PREFIX_RE.fullmatch(marker_prefix)
            or _require_research_attribution_int(
                instrumentation.get("post_load_wait_ms"), "instrumentation.post_load_wait_ms"
            )
            > 10_000
            or instrumentation.get("capture_count") != 1
            or instrumentation.get("non_gating") is not True
            or not all(
                isinstance(value, str) and value.strip()
                for key in ("playwright_source", "browser_version", "method", "caveat")
                for value in (instrumentation.get(key),)
            )
        ):
            raise WebsiteOperatorError("Research hydration attribution instrumentation binding is invalid.")

        observed = _require_research_attribution_mapping(payload.get("observed"), "observed")
        if set(observed) != {
            "events",
            "events_truncated",
            "register_rows",
            "profile_cards",
            "note_cards",
            "catalogue_records",
        }:
            raise WebsiteOperatorError(
                "Research hydration attribution observed data has an unexpected shape."
            )
        observed_events = observed.get("events")
        if not isinstance(observed_events, list) or observed.get("events_truncated") is not False:
            raise WebsiteOperatorError("Research hydration attribution observer log is incomplete.")
        observed_marker_names: set[str] = set()
        for event in observed_events:
            event_row = _require_research_attribution_mapping(event, "observed.events[]")
            event_time = event_row.get("time_ms")
            if (
                set(event_row) != {"name", "time_ms"}
                or not isinstance(event_row.get("name"), str)
                or not str(event_row["name"]).startswith(marker_prefix)
                or isinstance(event_time, bool)
                or not isinstance(event_time, (int, float))
                or event_time < 0
            ):
                raise WebsiteOperatorError("Research hydration attribution observer event is invalid.")
            observed_marker_names.add(str(event_row["name"]))
        expected_resource_markers = {
            f"{marker_prefix}resource:research-json:complete",
            f"{marker_prefix}resource:research-catalogue-json:complete",
        }
        expected_target_markers = {
            f"{marker_prefix}{target}:mutation-observer-delivery" for target in RESEARCH_HYDRATION_TARGET_IDS
        }
        if not (
            expected_resource_markers | expected_target_markers | {f"{marker_prefix}capture-complete"}
        ).issubset(observed_marker_names):
            raise WebsiteOperatorError(
                "Research hydration attribution observer log lacks required nonce-bound marks."
            )
        for key in ("register_rows", "profile_cards", "note_cards", "catalogue_records"):
            if _require_research_attribution_int(observed.get(key), f"observed.{key}") <= 0:
                raise WebsiteOperatorError(
                    "Research hydration attribution did not observe all expected rendered records."
                )
        runtime_messages = _require_research_attribution_mapping(
            payload.get("runtime_messages"), "runtime_messages"
        )
        if set(runtime_messages) != {"console_counts", "page_error_count"}:
            raise WebsiteOperatorError("Research hydration attribution runtime message summary is invalid.")
        console_counts = _require_research_attribution_mapping(
            runtime_messages.get("console_counts"), "runtime_messages.console_counts"
        )
        if (
            any(
                isinstance(value, bool) or not isinstance(value, int) or value < 0
                for value in console_counts.values()
            )
            or _require_research_attribution_int(
                runtime_messages.get("page_error_count"), "runtime_messages.page_error_count"
            )
            != 0
            or _require_research_attribution_int(
                console_counts.get("error", 0), "runtime_messages.console_counts.error"
            )
            != 0
        ):
            raise WebsiteOperatorError("Research hydration attribution recorded runtime errors.")

        coverage = _require_research_attribution_mapping(payload.get("coverage"), "coverage")
        coverage_keys = {
            "route_success",
            "route_status",
            "same_origin",
            "runtime_clean",
            "expected_resources",
            "missing_resources",
            "expected_targets",
            "missing_targets",
            "missing_runtime_marks",
            "missing_observed_counts",
            "observer_log_complete",
            "minimized_trace_complete",
            "document_root_layout_count",
            "passed",
        }
        if (
            set(coverage) != coverage_keys
            or any(
                coverage.get(key) is not True
                for key in (
                    "route_success",
                    "same_origin",
                    "runtime_clean",
                    "observer_log_complete",
                    "minimized_trace_complete",
                    "passed",
                )
            )
            or _require_research_attribution_int(coverage.get("route_status"), "coverage.route_status")
            != status
        ):
            raise WebsiteOperatorError(
                "Research hydration attribution coverage did not pass its strict evidence checks."
            )
        if (
            coverage.get("expected_resources") != ["research-json", "research-catalogue-json"]
            or coverage.get("expected_targets") != list(RESEARCH_HYDRATION_TARGET_IDS)
            or any(
                coverage.get(key) != []
                for key in (
                    "missing_resources",
                    "missing_targets",
                    "missing_runtime_marks",
                    "missing_observed_counts",
                )
            )
        ):
            raise WebsiteOperatorError(
                "Research hydration attribution coverage is missing required route evidence."
            )

        correlation = _require_research_attribution_mapping(payload.get("correlation"), "correlation")
        correlation_keys = {
            "marker_count",
            "markers",
            "layout_count",
            "document_root_layout_count",
            "full_document_layout_count",
            "longest_layouts",
            "initial_document_layout_finding",
            "hypotheses",
        }
        if set(correlation) != correlation_keys:
            raise WebsiteOperatorError("Research hydration attribution correlation has an unexpected shape.")
        markers = correlation.get("markers")
        if not isinstance(markers, list) or _require_research_attribution_int(
            correlation.get("marker_count"), "correlation.marker_count"
        ) != len(markers):
            raise WebsiteOperatorError("Research hydration attribution correlation marker count is invalid.")
        trace_marker_names: set[str] = set()
        for marker in markers:
            marker_row = _require_research_attribution_mapping(marker, "correlation.markers[]")
            if (
                set(marker_row) != {"name", "timestamp_us", "phase", "pid", "tid"}
                or not isinstance(marker_row.get("timestamp_us"), (int, float))
                or not isinstance(marker_row.get("name"), str)
                or not str(marker_row["name"]).startswith(marker_prefix)
            ):
                raise WebsiteOperatorError("Research hydration attribution trace marker is not nonce-bound.")
            trace_marker_names.add(str(marker_row["name"]))
        if not (expected_resource_markers | expected_target_markers).issubset(trace_marker_names):
            raise WebsiteOperatorError(
                "Research hydration attribution trace lacks required nonce-bound marks."
            )
        document_root_layout_count = _require_research_attribution_int(
            correlation.get("document_root_layout_count"), "correlation.document_root_layout_count"
        )
        if (
            _require_research_attribution_int(correlation.get("layout_count"), "correlation.layout_count")
            <= 0
            or document_root_layout_count <= 0
            or _require_research_attribution_int(
                coverage.get("document_root_layout_count"), "coverage.document_root_layout_count"
            )
            != document_root_layout_count
            or not isinstance(correlation.get("longest_layouts"), list)
            or not isinstance(correlation.get("initial_document_layout_finding"), Mapping)
        ):
            raise WebsiteOperatorError("Research hydration attribution trace lacks document-layout evidence.")
        hypotheses = correlation.get("hypotheses")
        if not isinstance(hypotheses, list) or [
            item.get("id") if isinstance(item, Mapping) else None for item in hypotheses
        ] != list(RESEARCH_HYDRATION_TARGET_IDS):
            raise WebsiteOperatorError(
                "Research hydration attribution hypotheses do not cover each declared target."
            )
        for hypothesis in hypotheses:
            hypothesis_row = _require_research_attribution_mapping(hypothesis, "correlation.hypotheses[]")
            if hypothesis_row.get("state") not in {
                "inconclusive",
                "temporally-correlated",
                "not-correlated-in-capture",
            } or not isinstance(hypothesis_row.get("limitation"), str):
                raise WebsiteOperatorError(
                    "Research hydration attribution hypothesis overstates or omits its limitation."
                )
            correlations = hypothesis_row.get("correlations")
            if not isinstance(correlations, list):
                raise WebsiteOperatorError(
                    "Research hydration attribution hypothesis correlations are invalid."
                )
            for item in correlations:
                row = _require_research_attribution_mapping(item, "correlation.hypotheses[].correlations[]")
                delta = row.get("marker_to_layout_start_ms")
                if (
                    not isinstance(row.get("marker"), str)
                    or not str(row["marker"]).startswith(marker_prefix)
                    or row.get("relation") not in {"within-layout", "precedes-within-window"}
                    or row.get("layout_kind") not in {"full-document", "document-root-partial"}
                    or isinstance(delta, bool)
                    or not isinstance(delta, (int, float))
                ):
                    raise WebsiteOperatorError(
                        "Research hydration attribution correlation lacks a bounded layout relation."
                    )

        trace = _require_research_attribution_mapping(payload.get("trace"), "trace")
        trace_keys = {
            "path",
            "schema",
            "sha256",
            "original_event_count",
            "relevant_event_count",
            "retained_event_count",
            "trace_truncated",
            "raw_trace_persisted",
        }
        if set(trace) != trace_keys or trace.get("schema") != RESEARCH_HYDRATION_MINIMIZED_TRACE_SCHEMA:
            raise WebsiteOperatorError("Research hydration attribution trace metadata is invalid.")
        if trace.get("raw_trace_persisted") is not False or trace.get("trace_truncated") is not False:
            raise WebsiteOperatorError(
                "Research hydration attribution may retain only a complete minimized trace."
            )
        trace_hash = _require_research_attribution_sha256(trace.get("sha256"), "trace.sha256")
        raw_trace = trace.get("path")
        if not isinstance(raw_trace, str) or not raw_trace.strip():
            raise WebsiteOperatorError("Research hydration attribution trace path is missing.")
        trace_path = _safe_repo_path(self.repo_root, raw_trace)
        try:
            trace_relative = trace_path.relative_to(artifact_root)
        except ValueError as exc:
            raise WebsiteOperatorError(
                "Research hydration attribution trace must remain below its controlled artifact root."
            ) from exc
        if (
            len(trace_relative.parts) != 2
            or trace_path.parent != receipt.parent
            or trace_path.name != "research-hydration.trace.json"
            or not trace_path.is_file()
            or _sha256_file(trace_path).lower() != trace_hash
        ):
            raise WebsiteOperatorError(
                "Research hydration attribution trace is missing or no longer matches its receipt hash."
            )
        trace_payload = _read_json(trace_path)
        if set(trace_payload) != {
            "schema",
            "marker_prefix",
            "original_event_count",
            "relevant_event_count",
            "retained_event_count",
            "event_limit",
            "trace_truncated",
            "redaction",
            "traceEvents",
        } or (
            trace_payload.get("schema") != RESEARCH_HYDRATION_MINIMIZED_TRACE_SCHEMA
            or trace_payload.get("marker_prefix") != marker_prefix
            or trace_payload.get("trace_truncated") is not False
            or trace_payload.get("original_event_count") != trace.get("original_event_count")
            or trace_payload.get("relevant_event_count") != trace.get("relevant_event_count")
            or trace_payload.get("retained_event_count") != trace.get("retained_event_count")
            or not isinstance(trace_payload.get("traceEvents"), list)
            or len(trace_payload["traceEvents"]) != trace.get("retained_event_count")
            or re.search(r"https?://", json.dumps(trace_payload, sort_keys=True))
        ):
            raise WebsiteOperatorError(
                "Research hydration attribution minimized trace is incomplete or unredacted."
            )
        original_count = _require_research_attribution_int(
            trace.get("original_event_count"), "trace.original_event_count"
        )
        relevant_count = _require_research_attribution_int(
            trace.get("relevant_event_count"), "trace.relevant_event_count"
        )
        retained_count = _require_research_attribution_int(
            trace.get("retained_event_count"), "trace.retained_event_count"
        )
        if retained_count > relevant_count or relevant_count > original_count:
            raise WebsiteOperatorError("Research hydration attribution trace event counts are inconsistent.")
        return trace_path

    def research_hydration_attribution(self, source_root: Path | None = None) -> Path:
        """Run one local, analysis-only Research route attribution capture.

        The Node diagnostic owns its append-only output directory and validates
        source stability before emitting a receipt. This wrapper only permits
        local canonical or staged candidate trees, rehashes and semantically
        validates the returned non-authoritative receipt, and never stages,
        promotes, packages, or deploys a candidate.
        """
        source = self._research_attribution_source(source_root)
        if not source.is_dir():
            raise WebsiteOperatorError(f"Research attribution source is missing: {source}")
        tool = _safe_repo_path(self.repo_root, RESEARCH_HYDRATION_ATTRIBUTION_SCRIPT)
        if not tool.is_file():
            raise WebsiteOperatorError(f"Research attribution tool is missing: {tool}")
        source_relative = source.relative_to(self.repo_root).as_posix()
        result = self.runner(
            ["node", RESEARCH_HYDRATION_ATTRIBUTION_SCRIPT, "--source-root", source_relative],
            self.repo_root,
        )
        if result.returncode != 0:
            raise WebsiteOperatorError(
                "Research hydration attribution did not complete: "
                f"{_short_output(result.stderr or result.stdout)}"
            )
        try:
            reported = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise WebsiteOperatorError(
                "Research hydration attribution did not return a JSON receipt location."
            ) from exc
        if not isinstance(reported, Mapping) or reported.get("state") != "complete":
            raise WebsiteOperatorError(
                "Research hydration attribution must report a complete analysis-only capture."
            )
        raw_receipt = reported.get("receipt")
        raw_trace = reported.get("trace")
        if not isinstance(raw_receipt, str) or not raw_receipt.strip():
            raise WebsiteOperatorError("Research hydration attribution receipt path is missing.")
        receipt = Path(raw_receipt).resolve()
        artifact_root = _safe_repo_path(self.repo_root, RESEARCH_HYDRATION_ATTRIBUTION_ROOT)
        try:
            receipt_relative = receipt.relative_to(artifact_root)
        except ValueError as exc:
            raise WebsiteOperatorError(
                "Research hydration attribution receipt must remain below its controlled artifact root."
            ) from exc
        if (
            len(receipt_relative.parts) != 2
            or receipt.name != "AUREON_RESEARCH_HYDRATION_ATTRIBUTION.json"
            or not receipt.is_file()
        ):
            raise WebsiteOperatorError(
                "Research hydration attribution receipt is not a direct controlled artifact."
            )
        payload = _read_json(receipt)
        trace_path = self._validate_research_hydration_attribution_receipt(
            payload,
            source=source,
            artifact_root=artifact_root,
            receipt=receipt,
            tool=tool,
        )
        if not isinstance(raw_trace, str) or Path(raw_trace).resolve() != trace_path:
            raise WebsiteOperatorError(
                "Research hydration attribution stdout trace binding does not match its receipt."
            )
        return receipt

    def _parse_pages(self) -> Dict[str, PageParser]:
        pages: Dict[str, PageParser] = {}
        for path in self.site_root.rglob("*.html"):
            parser = PageParser()
            try:
                parser.feed(path.read_text(encoding="utf-8-sig"))
                parser.close()
            except (OSError, UnicodeError) as exc:
                raise WebsiteOperatorError(f"Could not parse HTML {path}: {exc}") from exc
            pages[path.relative_to(self.site_root).as_posix()] = parser
        return pages

    def _resolve_reference(self, page: str, value: str) -> Path | None:
        value = value.strip()
        parsed = urlparse(value)
        if parsed.scheme or value.startswith(("#", "mailto:", "tel:", "data:", "javascript:")):
            return None
        path_value = unquote(parsed.path)
        if not path_value:
            return None
        if path_value.startswith("/"):
            candidate = self.site_root / path_value.lstrip("/")
        else:
            candidate = self.site_root / Path(page).parent / path_value
        resolved = candidate.resolve()
        try:
            resolved.relative_to(self.site_root)
        except ValueError:
            return resolved
        if path_value.endswith("/") or resolved.is_dir():
            resolved = resolved / "index.html"
        return resolved

    def _expected_canonical(self, page: str) -> str:
        override = self.config["site"].get("canonical_overrides", {}).get(page)
        if override:
            return str(override)
        route = "/" if page == "index.html" else f"/{page.removesuffix('index.html')}"
        return cast(str, urljoin(self.config["site"]["base_url"], route))

    @staticmethod
    def _canonical_equivalent(left: str, right: str) -> bool:
        def normalise(value: str) -> tuple[str, str, str]:
            parsed = urlparse(value)
            path = parsed.path or "/"
            if path.endswith("index.html"):
                path = path[: -len("index.html")]
            if not path.endswith("/"):
                path += "/"
            return parsed.scheme.lower(), parsed.netloc.lower(), path

        return normalise(left) == normalise(right)

    def _metadata_findings(self, pages: Mapping[str, PageParser]) -> List[Finding]:
        findings: List[Finding] = []
        critical = {_safe_relative_path(item) for item in self.config["site"]["critical_routes"]}
        for page, parser in pages.items():
            strict = page in critical
            severity = "error" if strict else "warning"
            robots_tokens = {
                token for token in re.split(r"[\s,]+", parser.meta.get("robots", "").lower()) if token
            }
            indexable = "noindex" not in robots_tokens
            if not parser.lang:
                findings.append(Finding("metadata.lang_missing", severity, "HTML lang is missing.", page))
            if not parser.title:
                findings.append(Finding("metadata.title_missing", severity, "Page title is missing.", page))
            elif indexable and not 20 <= len(parser.title) <= 75:
                findings.append(
                    Finding(
                        "metadata.title_length",
                        "warning",
                        "Title should normally be 20-75 characters.",
                        page,
                        {"characters": len(parser.title)},
                    )
                )
            description = parser.meta.get("description", "")
            if not description:
                findings.append(
                    Finding("metadata.description_missing", severity, "Meta description is missing.", page)
                )
            elif indexable and not 70 <= len(description) <= 200:
                findings.append(
                    Finding(
                        "metadata.description_length",
                        "warning",
                        "Description should normally be 70-200 characters.",
                        page,
                        {"characters": len(description)},
                    )
                )
            if not parser.meta.get("viewport"):
                findings.append(
                    Finding(
                        "metadata.viewport_missing",
                        severity,
                        "Responsive viewport metadata is missing.",
                        page,
                    )
                )
            if not parser.canonical:
                findings.append(
                    Finding("metadata.canonical_missing", severity, "Canonical URL is missing.", page)
                )
            elif strict and not self._canonical_equivalent(parser.canonical, self._expected_canonical(page)):
                findings.append(
                    Finding(
                        "metadata.canonical_mismatch",
                        "error",
                        "Canonical URL does not match the configured production route.",
                        page,
                        {
                            "observed": parser.canonical,
                            "expected": self._expected_canonical(page),
                        },
                    )
                )
            for social_key in ("og:title", "og:description", "og:image"):
                if strict and not parser.meta.get(social_key):
                    findings.append(
                        Finding(
                            "metadata.social_missing",
                            "warning",
                            f"Critical route is missing {social_key}.",
                            page,
                        )
                    )
            if strict and parser.h1_count != 1:
                findings.append(
                    Finding(
                        "structure.h1_count",
                        "error",
                        "Critical route must contain exactly one H1.",
                        page,
                        {"count": parser.h1_count},
                    )
                )
            if strict and parser.json_ld_count == 0:
                findings.append(
                    Finding(
                        "metadata.structured_data_missing",
                        "warning",
                        "Critical route has no JSON-LD structured data.",
                        page,
                    )
                )
        for missing in sorted(critical.difference(pages)):
            findings.append(
                Finding(
                    "site.critical_route_missing", "error", "Configured critical route is missing.", missing
                )
            )
        return findings

    def _static_findings(self, pages: Mapping[str, PageParser]) -> List[Finding]:
        findings: List[Finding] = []
        for page, parser in pages.items():
            duplicates = sorted(key for key, count in Counter(parser.ids).items() if count > 1)
            if duplicates:
                findings.append(
                    Finding(
                        "structure.duplicate_ids",
                        "error",
                        "Duplicate element IDs break navigation and interaction semantics.",
                        page,
                        {"ids": duplicates},
                    )
                )
            if parser.images_without_alt:
                findings.append(
                    Finding(
                        "accessibility.image_alt",
                        "error",
                        "Images without an alt attribute were found.",
                        page,
                        {"count": parser.images_without_alt},
                    )
                )
            if parser.inaccessible_interactions:
                findings.append(
                    Finding(
                        "accessibility.interaction_name",
                        "error",
                        "Links or buttons without an accessible name were found.",
                        page,
                        {"count": parser.inaccessible_interactions},
                    )
                )
            if parser.autoplay_media:
                findings.append(
                    Finding(
                        "motion.autoplay",
                        "error",
                        "Autoplay media is not permitted by the default motion policy.",
                        page,
                        {"count": parser.autoplay_media},
                    )
                )
            for reference in parser.references:
                value = reference["value"]
                parsed = urlparse(value)
                if parsed.scheme == "http":
                    findings.append(
                        Finding(
                            "security.insecure_reference",
                            "error",
                            "Insecure HTTP reference found.",
                            page,
                            {"reference": value},
                        )
                    )
                    continue
                target = self._resolve_reference(page, value)
                if target is None:
                    continue
                try:
                    target.relative_to(self.site_root)
                except ValueError:
                    findings.append(
                        Finding(
                            "references.outside_site",
                            "error",
                            "Local reference escapes the website root.",
                            page,
                            {"reference": value},
                        )
                    )
                    continue
                if not target.exists():
                    findings.append(
                        Finding(
                            "references.missing",
                            "error",
                            "Local reference target is missing.",
                            page,
                            {"reference": value},
                        )
                    )
        css_text = "\n".join(
            path.read_text(encoding="utf-8-sig", errors="replace") for path in self.site_root.glob("*.css")
        )
        if (
            self.config["checks"].get("require_reduced_motion", True)
            and "prefers-reduced-motion" not in css_text
        ):
            findings.append(
                Finding(
                    "motion.reduced_motion_missing",
                    "error",
                    "The shared CSS does not expose a prefers-reduced-motion policy.",
                )
            )
        return findings

    @staticmethod
    def _negated(text: str, start: int) -> bool:
        context_start = max(
            text.rfind(".", 0, start),
            text.rfind("!", 0, start),
            text.rfind("?", 0, start),
            text.rfind(";", 0, start),
            start - 180,
        )
        context = text[max(0, context_start) : start].lower()
        return bool(
            re.search(
                r"\b(?:no|not|never|none|neither|without|does not|isn't|is not)\b",
                context,
            )
        )

    def _claim_input_findings(self) -> List[Finding]:
        findings: List[Finding] = []
        for item in self.config["ethos"].get("claim_inputs", []):
            if not isinstance(item, dict):
                findings.append(Finding("claims.input_config", "error", "Claim input config is invalid."))
                continue
            value = item.get("path")
            required = bool(item.get("required", True))
            try:
                path = _safe_repo_path(self.repo_root, value)
            except WebsiteOperatorError as exc:
                findings.append(Finding("claims.input_path", "error", str(exc)))
                continue
            if not path.is_file():
                findings.append(
                    Finding(
                        "claims.input_missing",
                        "error" if required else "warning",
                        "Claim/evidence input is missing.",
                        str(value),
                    )
                )
                continue
            try:
                payload = _read_json(path)
            except WebsiteOperatorError as exc:
                findings.append(Finding("claims.input_invalid", "error", str(exc), str(value)))
                continue
            expected_schema = item.get("schema")
            if expected_schema and payload.get("schema") != expected_schema:
                findings.append(
                    Finding(
                        "claims.schema_mismatch",
                        "error",
                        "Claim input schema does not match configuration.",
                        str(value),
                        {"expected": expected_schema, "observed": payload.get("schema")},
                    )
                )
            if payload.get("schema") == "aureon-sector-blades-v1":
                required_fields = {
                    "id",
                    "lane",
                    "name",
                    "buyer",
                    "problem_or_use_case",
                    "shared_core",
                    "public_evidence_basis",
                    "strategic_relevance",
                    "next_validation",
                    "public_boundary",
                    "source_links",
                }
                legacy_fields = {
                    "decision_or_use_case",
                    "current_evidence_state",
                    "controlled_evidence",
                    "grant_or_provider_evidence",
                    "partner_evidence",
                    "next_proof",
                }
                blades = payload.get("blades")
                if not isinstance(blades, list) or not blades:
                    findings.append(
                        Finding(
                            "claims.blades_missing",
                            "error",
                            "Sector-blade register has no blades.",
                            str(value),
                        )
                    )
                else:
                    for index, blade in enumerate(blades):
                        if not isinstance(blade, dict):
                            findings.append(
                                Finding(
                                    "claims.blade_invalid",
                                    "error",
                                    "Sector blade must be an object.",
                                    f"{value}#blades[{index}]",
                                )
                            )
                            continue
                        missing = sorted(
                            field
                            for field in required_fields
                            if field not in blade or blade.get(field) in ("", None, [])
                        )
                        if missing:
                            findings.append(
                                Finding(
                                    "claims.blade_fields",
                                    "error",
                                    "Sector blade is missing evidence-control fields.",
                                    f"{value}#blades[{index}]",
                                    {"missing": missing},
                                )
                            )
                        legacy = sorted(field for field in legacy_fields if field in blade)
                        if legacy:
                            findings.append(
                                Finding(
                                    "claims.blade_legacy_fields",
                                    "error",
                                    "Sector blade exposes legacy public-disclosure fields.",
                                    f"{value}#blades[{index}]",
                                    {"fields": legacy},
                                )
                            )
        return findings

    def _ethos_findings(self, pages: Mapping[str, PageParser]) -> List[Finding]:
        findings = self._claim_input_findings()
        critical = {_safe_relative_path(item) for item in self.config["site"]["critical_routes"]}
        combined = "\n".join(parser.text for page, parser in pages.items() if page in critical)
        for rule in self.config["ethos"].get("required_site_signals", []):
            pattern = str(rule.get("pattern", ""))
            if not pattern or re.search(pattern, combined, flags=re.IGNORECASE) is None:
                findings.append(
                    Finding(
                        f"ethos.signal.{rule.get('id', 'unknown')}",
                        str(rule.get("severity", "error")),
                        str(rule.get("message", "Required company-ethos signal is absent.")),
                    )
                )
        for page, parser in pages.items():
            if page not in critical:
                continue
            for rule in self.config["ethos"].get("prohibited_claim_patterns", []):
                pattern = str(rule.get("pattern", ""))
                if not pattern:
                    continue
                for match in re.finditer(pattern, parser.text, flags=re.IGNORECASE):
                    if self._negated(parser.text, match.start()):
                        continue
                    findings.append(
                        Finding(
                            f"ethos.claim.{rule.get('id', 'unsafe')}",
                            str(rule.get("severity", "error")),
                            str(
                                rule.get(
                                    "message", "Unbounded public claim requires evidence or qualification."
                                )
                            ),
                            page,
                            {"matched_text": match.group(0)},
                        )
                    )
        return findings

    def _budget_findings(
        self,
        inventory: Mapping[str, Any],
        pages: Mapping[str, PageParser],
    ) -> List[Finding]:
        findings: List[Finding] = []
        budgets = self.config["budgets"]
        if int(inventory["total_bytes"]) > int(budgets["site_total_bytes"]):
            findings.append(
                Finding(
                    "budget.site_bytes",
                    "error",
                    "Public site exceeds its deliberate source-size budget.",
                    evidence={
                        "observed": inventory["total_bytes"],
                        "limit": budgets["site_total_bytes"],
                    },
                )
            )
        if int(inventory["file_count"]) > int(budgets["site_file_count"]):
            findings.append(
                Finding(
                    "budget.site_files",
                    "error",
                    "Public site exceeds its deliberate file-count budget.",
                    evidence={
                        "observed": inventory["file_count"],
                        "limit": budgets["site_file_count"],
                    },
                )
            )
        per_file = budgets.get("per_file_bytes", {})
        for path in self._public_files():
            limit = per_file.get(path.suffix.lower())
            if limit is not None and path.stat().st_size > int(limit):
                findings.append(
                    Finding(
                        "budget.asset_bytes",
                        "error",
                        "Asset exceeds its type-specific budget.",
                        path.relative_to(self.site_root).as_posix(),
                        {"observed": path.stat().st_size, "limit": int(limit)},
                    )
                )
        critical = {_safe_relative_path(item) for item in self.config["site"]["critical_routes"]}
        page_limit = int(budgets["critical_page_direct_bytes"])
        for page in sorted(critical):
            parser = pages.get(page)
            page_path = self.site_root / page
            if not parser or not page_path.is_file():
                continue
            referenced = {page_path.resolve()}
            for reference in parser.references:
                target = self._resolve_reference(page, reference["value"])
                if target and target.is_file():
                    try:
                        target.relative_to(self.site_root)
                    except ValueError:
                        continue
                    referenced.add(target.resolve())
            observed = sum(path.stat().st_size for path in referenced)
            if observed > page_limit:
                findings.append(
                    Finding(
                        "budget.critical_page_direct_bytes",
                        "error",
                        "Critical route exceeds the uncompressed direct-reference budget.",
                        page,
                        {
                            "observed": observed,
                            "limit": page_limit,
                            "files": len(referenced),
                            "measurement": "HTML plus directly referenced local files; not hosting capacity",
                        },
                    )
                )
        return findings

    def _secret_findings(self) -> List[Finding]:
        findings: List[Finding] = []
        patterns = [
            re.compile(pattern, flags=re.IGNORECASE)
            for pattern in self.config["packaging"].get("secret_patterns", [])
        ]
        blocked_names = {str(item).lower() for item in self.config["packaging"]["blocked_file_names"]}
        blocked_suffixes = {str(item).lower() for item in self.config["packaging"]["blocked_extensions"]}
        for path in self._public_files():
            if path.name.lower() in blocked_names or path.suffix.lower() in blocked_suffixes:
                findings.append(
                    Finding(
                        "security.blocked_public_file",
                        "error",
                        "Credential-like file is inside the public website tree.",
                        path.relative_to(self.site_root).as_posix(),
                    )
                )
                continue
            if path.suffix.lower() not in TEXT_EXTENSIONS:
                continue
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            if any(pattern.search(text) for pattern in patterns):
                findings.append(
                    Finding(
                        "security.secret_pattern",
                        "error",
                        "Potential credential literal found in a public file.",
                        path.relative_to(self.site_root).as_posix(),
                    )
                )
        return findings

    def _composite_gate_check(self) -> Mapping[str, Any] | None:
        matches = [
            check
            for check in self.config["checks"].get("external", [])
            if isinstance(check, dict)
            and check.get("id") == COMPOSITE_VISUAL_GATE_CHECK_ID
            and check.get("enabled") is True
            and check.get("required") is True
        ]
        return matches[0] if len(matches) == 1 else None

    @staticmethod
    def _parse_external_json(stdout: str) -> Dict[str, Any] | None:
        value = str(stdout or "").strip()
        if not value:
            return None
        try:
            payload = json.loads(value)
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _is_zero_blocker_pass(payload: object) -> bool:
        if (
            not isinstance(payload, Mapping)
            or set(payload) != COMPOSITE_VISUAL_GATE_STDOUT_KEYS
            or payload.get("state") != "pass"
            or payload.get("output") is not None
        ):
            return False
        integer_fields = (
            "blockers",
            "axeViolations",
            "axeIncompleteNodes",
            "manualFailures",
            "manualUnreviewed",
        )
        if any(type(payload.get(name)) is not int for name in integer_fields):
            return False
        if (
            payload.get("blockers") != 0
            or payload.get("axeViolations") != 0
            or payload.get("manualFailures") != 0
            or payload.get("manualUnreviewed") != 0
            or int(payload["axeIncompleteNodes"]) < 0
        ):
            return False
        return bool(re.fullmatch(r"[a-f0-9]{64}", str(payload.get("sourceTreeSha256") or "")))

    def _evidence_file(
        self,
        value: object,
        label: str,
        *,
        declared_sha256: object | None = None,
    ) -> Dict[str, Any]:
        relative = _safe_relative_path(value)
        if not relative.startswith("docs/audits/"):
            raise WebsiteOperatorError(f"{label} must stay inside docs/audits/.")
        candidate = _safe_repo_path(self.repo_root, relative)
        if not candidate.is_file():
            raise WebsiteOperatorError(f"{label} is missing: {relative}")
        try:
            candidate.resolve().relative_to(self.repo_root)
        except ValueError as exc:
            raise WebsiteOperatorError(f"{label} resolves outside the repository.") from exc
        observed = _sha256_file(candidate)
        if declared_sha256 is not None:
            declared = str(declared_sha256 or "")
            if not re.fullmatch(r"[A-Fa-f0-9]{64}", declared):
                raise WebsiteOperatorError(f"{label} has an invalid declared SHA-256.")
            if observed != declared.upper():
                raise WebsiteOperatorError(f"{label} bytes do not match their declared SHA-256.")
        return {"path": relative, "sha256": observed}

    def _composite_gate_binding(
        self,
        command: Sequence[str],
        stdout_json: Mapping[str, Any] | None,
        current_source_tree_sha256: str,
    ) -> Dict[str, Any]:
        if not isinstance(stdout_json, Mapping) or not self._is_zero_blocker_pass(stdout_json):
            raise WebsiteOperatorError(
                "Composite visual gate did not return one parseable zero-blocker PASS."
            )
        if len(command) != 6:
            raise WebsiteOperatorError("Expanded composite visual gate command is not canonical.")
        manifest_path = Path(command[5]).resolve()
        try:
            manifest_relative = manifest_path.relative_to(self.repo_root).as_posix()
        except ValueError as exc:
            raise WebsiteOperatorError("Composite visual gate manifest escapes the repository.") from exc
        manifest_reference = self._evidence_file(manifest_relative, "Composite gate manifest")
        manifest = _read_json(manifest_path)
        if manifest.get("schema") != COMPOSITE_VISUAL_GATE_MANIFEST_SCHEMA:
            raise WebsiteOperatorError("Composite visual gate manifest schema is unsupported.")
        if manifest.get("intent") != "final-release":
            raise WebsiteOperatorError("Composite visual gate manifest is not final-release evidence.")
        release_id = str(manifest.get("releaseId") or "").strip()
        source_hash = str(manifest.get("websiteTreeSha256") or "")
        if not release_id or not re.fullmatch(r"[a-f0-9]{64}", source_hash):
            raise WebsiteOperatorError("Composite visual gate manifest lacks a releaseId or source hash.")
        if stdout_json.get("sourceTreeSha256") != source_hash:
            raise WebsiteOperatorError(
                "Composite visual gate stdout is not bound to its manifest source hash."
            )
        evidence = manifest.get("evidence")
        if not isinstance(evidence, dict):
            raise WebsiteOperatorError("Composite visual gate manifest has no evidence object.")
        visual = evidence.get("visualReceipt")
        manual = evidence.get("manualPixelReviewReceipt")
        if not isinstance(visual, dict) or not isinstance(manual, dict):
            raise WebsiteOperatorError("Composite visual gate manifest must bind visual and manual receipts.")
        visual_reference = self._evidence_file(
            visual.get("path"),
            "Composite visual receipt",
            declared_sha256=visual.get("sha256"),
        )
        manual_reference = self._evidence_file(
            manual.get("path"),
            "Composite manual pixel-review receipt",
            declared_sha256=manual.get("sha256"),
        )
        return {
            "check_id": COMPOSITE_VISUAL_GATE_CHECK_ID,
            "release_id": release_id,
            "operator_source_tree_sha256": current_source_tree_sha256,
            "visual_source_tree_sha256": source_hash,
            "manifest": manifest_reference,
            "visual_receipt": visual_reference,
            "manual_pixel_review_receipt": manual_reference,
        }

    def _run_external_check(
        self,
        check: Mapping[str, Any],
        current_source_tree_sha256: str,
    ) -> tuple[Dict[str, Any], List[Finding]]:
        identifier = str(check.get("id") or "external")
        required = check.get("required", True) is True
        severity = "error" if required else "warning"
        command = self._expand_command(check.get("command", []), {})
        record: Dict[str, Any] = {
            "id": identifier,
            "required": required,
            "command": command,
            "checked_at": _iso(),
            "current_source_tree_sha256": current_source_tree_sha256,
            "returncode": None,
            "stdout_json": None,
            "state": "not-run",
        }
        findings: List[Finding] = []
        if not _command_exists(command[0]):
            record["state"] = "executable-unavailable"
            record["stderr_tail"] = f"Executable unavailable: {command[0]}"
            findings.append(
                Finding(
                    f"external.{identifier}",
                    severity,
                    f"Required audit executable is unavailable: {command[0]}",
                )
            )
            return record, findings
        result = self.runner(command, self.repo_root)
        record["returncode"] = result.returncode
        record["stdout_json"] = self._parse_external_json(result.stdout)
        if result.returncode != 0:
            record["state"] = "failed"
            record["stdout_tail"] = _short_output(result.stdout)
            record["stderr_tail"] = _short_output(result.stderr)
            findings.append(
                Finding(
                    f"external.{identifier}",
                    severity,
                    "Allow-listed external audit failed.",
                    evidence={
                        "returncode": result.returncode,
                        "stdout_tail": record["stdout_tail"],
                        "stderr_tail": record["stderr_tail"],
                    },
                )
            )
            return record, findings
        if identifier == COMPOSITE_VISUAL_GATE_CHECK_ID:
            try:
                record["composite_gate"] = self._composite_gate_binding(
                    command,
                    record["stdout_json"],
                    current_source_tree_sha256,
                )
            except WebsiteOperatorError as exc:
                record["state"] = "invalid-success-evidence"
                record["evidence_error"] = str(exc)
                findings.append(
                    Finding(
                        f"external.{identifier}.evidence",
                        "error",
                        "Composite visual gate returned zero without valid bound evidence.",
                        evidence={"error": str(exc)},
                    )
                )
                return record, findings
        record["state"] = "pass"
        return record, findings

    def _run_external_checks(
        self,
        current_source_tree_sha256: str,
    ) -> tuple[List[Finding], Dict[str, Any]]:
        findings: List[Finding] = []
        configured = self.config["checks"].get("external", [])
        enabled = [check for check in configured if isinstance(check, dict) and check.get("enabled", True)]
        composite = self._composite_gate_check()
        if composite is None:
            findings.append(
                Finding(
                    "external.release_gate_configuration",
                    "error",
                    "Release eligibility requires exactly one enabled, required canonical "
                    f"{COMPOSITE_VISUAL_GATE_CHECK_ID} check.",
                )
            )
        records: List[Dict[str, Any]] = []
        for check in enabled:
            record, check_findings = self._run_external_check(
                check,
                current_source_tree_sha256,
            )
            records.append(record)
            findings.extend(check_findings)
        required_records = [record for record in records if record.get("required") is True]
        composite_records = [
            record for record in records if record.get("id") == COMPOSITE_VISUAL_GATE_CHECK_ID
        ]
        complete = bool(enabled) and bool(required_records) and bool(composite_records)
        complete = complete and all(record.get("returncode") is not None for record in records)
        complete = complete and all(record.get("state") == "pass" for record in required_records)
        complete = complete and len(composite_records) == 1
        complete = complete and isinstance(
            composite_records[0].get("composite_gate") if composite_records else None,
            dict,
        )
        return findings, {
            "requested": True,
            "configured_count": len(configured),
            "enabled_count": len(enabled),
            "executed_count": sum(1 for record in records if record.get("returncode") is not None),
            "required_count": len(required_records),
            "complete": complete,
            "required_composite_check_id": COMPOSITE_VISUAL_GATE_CHECK_ID,
            "results": records,
        }

    def audit_payload(self, run_external: bool = True) -> Dict[str, Any]:
        inventory = self.inventory_payload()
        pages = self._parse_pages()
        findings: List[Finding] = []
        findings.extend(self._metadata_findings(pages))
        findings.extend(self._static_findings(pages))
        findings.extend(self._ethos_findings(pages))
        findings.extend(self._budget_findings(inventory, pages))
        findings.extend(self._secret_findings())
        if run_external:
            external_findings, external_checks = self._run_external_checks(inventory["tree_sha256"])
            findings.extend(external_findings)
        else:
            external_checks = {
                "requested": False,
                "configured_count": len(self.config["checks"].get("external", [])),
                "enabled_count": 0,
                "executed_count": 0,
                "required_count": 0,
                "complete": False,
                "required_composite_check_id": COMPOSITE_VISUAL_GATE_CHECK_ID,
                "results": [],
            }
        counts = Counter(finding.severity for finding in findings)
        receipt = self._base_receipt("audit")
        receipt.update(
            {
                "state": "pass" if counts["error"] == 0 else "blocked",
                "source_tree_sha256": inventory["tree_sha256"],
                "inventory": {
                    "file_count": inventory["file_count"],
                    "total_bytes": inventory["total_bytes"],
                    "html_page_count": inventory["html_page_count"],
                    "hosting_capacity": inventory["hosting_capacity"],
                    "git": inventory["git"],
                },
                "summary": {
                    "blockers": counts["error"],
                    "warnings": counts["warning"],
                    "informational": counts["info"],
                    "external_checks_run": external_checks["complete"],
                },
                "external_checks": external_checks,
                "findings": [finding.to_dict() for finding in findings],
                "boundary": {
                    "hosting_capacity_is_budget": False,
                    "audit_is_publication_authority": False,
                    "owner_gate_required": True,
                },
            }
        )
        return receipt

    def audit(self, output: Path | None = None, run_external: bool = True) -> Path:
        payload = self.audit_payload(run_external=run_external)
        return _atomic_write_json(self._path_for_output("audit", output), payload)

    def work_order(self, audit_receipt: Path, output: Path | None = None) -> Path:
        audit = _read_json(audit_receipt.resolve())
        self._require_receipt(audit, "audit")
        findings = audit.get("findings")
        if not isinstance(findings, list):
            raise WebsiteOperatorError("Audit receipt has no findings array.")
        tasks = []
        for index, finding in enumerate(findings, start=1):
            if not isinstance(finding, dict):
                continue
            tasks.append(
                {
                    "id": f"WEB-{index:03d}",
                    "priority": "P0" if finding.get("severity") == "error" else "P1",
                    "source_finding": finding,
                    "allowed_scope": [
                        "analysis-only; issue a separate exact-path staged candidate work order before any website change"
                    ],
                    "candidate_work_order_required": True,
                    "acceptance": [
                        "Re-run the complete website audit.",
                        "Preserve evidence labels and human authority.",
                        "Bind any implementation to a reconciled v4 candidate baseline, exact file allow-list, trusted binary policy and claim-impact declaration.",
                        "Do not publish or handle credentials.",
                    ],
                }
            )
        receipt = self._base_receipt("work-order")
        receipt.update(
            {
                "state": "proposed-local-work",
                "audit_receipt": str(audit_receipt.resolve()),
                "audit_sha256": _sha256_file(audit_receipt.resolve()),
                "task_count": len(tasks),
                "tasks": tasks,
                "candidate_control": {
                    "work_order_schema": WORK_ORDER_SCHEMA,
                    "execution": "separate exact-path staged candidate work order required",
                    "canonical_website_mutation": "not authorised",
                    "deployment_authority": "none",
                },
                "mutation_authority": "none",
                "publication_authority": "none",
            }
        )
        return _atomic_write_json(self._path_for_output("work-order", output), receipt)

    def create_candidate_work_order(
        self,
        *,
        goal: str,
        allowed_paths: Sequence[str],
        routes: Sequence[str] = (),
        reconciliation_receipt: Path | None = None,
        owner_source_decision: Path | None = None,
        backup_receipt: Path | None = None,
        allowed_new_origins: Sequence[str] = (),
        run_id: str | None = None,
        output: Path | None = None,
    ) -> Path:
        """Create one reconciled V30+ staged candidate order without touching website/.

        The legacy audit work order remains a diagnostic task list. This
        stricter order is the execution contract for a future autonomous
        design worker: it contains a complete baseline manifest, exact file
        allow-list, claim-source binding, current live-surface observation and
        staged artifact destination. A drifted production record additionally
        requires an owner source-selection decision bound to a verified backup.
        """

        try:
            work_order = create_design_work_order(
                goal=goal,
                allowed_paths=allowed_paths,
                routes=routes,
                reconciliation_receipt=reconciliation_receipt,
                owner_source_decision=owner_source_decision,
                backup_receipt=backup_receipt,
                allowed_new_origins=allowed_new_origins,
                run_id=run_id,
                repo_root=self.repo_root,
            )
            layout = work_order["candidate_layout"]
            candidate_root = self.repo_root / str(layout["root"])
            target = output or (candidate_root.parent / "work-orders" / f"{work_order['run_id']}.v4.json")
            written: Any = write_design_work_order(work_order, target, repo_root=self.repo_root)
            return cast(Path, written)
        except DesignCandidateControlError as exc:
            raise WebsiteOperatorError(f"Candidate work-order control failed: {exc}") from exc

    def stage_candidate(self, work_order: Path) -> Dict[str, str]:
        """Stage a full candidate copy below artifacts/website-candidates only."""

        try:
            staged: Any = stage_design_candidate(work_order, repo_root=self.repo_root)
            return cast(Dict[str, str], staged)
        except DesignCandidateControlError as exc:
            raise WebsiteOperatorError(f"Candidate staging control failed: {exc}") from exc

    def validate_candidate(
        self,
        work_order: Path,
        *,
        claim_impacts: Sequence[Mapping[str, Any]],
        output: Path | None = None,
    ) -> Path:
        """Validate one staged candidate without applying, packaging, or deploying it."""

        try:
            candidate = validate_staged_design_candidate(
                work_order,
                claim_impacts=claim_impacts,
                repo_root=self.repo_root,
            )
            candidate_root = self.repo_root / str(candidate["candidate"]["root"])
            target = output or candidate_root / "candidate.v1.json"
            written: Any = write_design_candidate_receipt(
                candidate,
                target,
                repo_root=self.repo_root,
            )
            return cast(Path, written)
        except DesignCandidateControlError as exc:
            raise WebsiteOperatorError(f"Candidate validation control failed: {exc}") from exc

    def verify_candidate_prepromotion_review(
        self,
        candidate_receipt: Path,
        capture_receipt: Path,
        manual_review: Path,
        human_acceptance: Path,
        *,
        output: Path | None = None,
    ) -> Path:
        """Retain only a fully bound, staged pre-promotion visual review.

        This method is read-only with respect to ``website/``.  Its passing
        receipt is local evidence for an owner to consider during a separate
        promotion; it cannot satisfy the later canonical audit/composite gate
        or authorise release packaging and deployment.
        """

        try:
            receipt = validate_candidate_visual_review(
                candidate_receipt,
                capture_receipt,
                manual_review,
                human_acceptance,
                repo_root=self.repo_root,
            )
            candidate = receipt.get("candidate")
            if not isinstance(candidate, Mapping):
                raise WebsiteOperatorError("Candidate visual review did not identify its staged candidate.")
            candidate_root = self.repo_root / str(candidate.get("root") or "")
            target = output or candidate_root / "prepromotion-visual-review.v1.json"
            written: Any = write_candidate_visual_review(
                receipt,
                target,
                repo_root=self.repo_root,
            )
            return cast(Path, written)
        except (DesignCandidateControlError, DesignCandidateVisualReviewError) as exc:
            raise WebsiteOperatorError(f"Candidate visual-review control failed: {exc}") from exc

    def record_design_learning(
        self,
        candidate_receipt: Path,
        visual_review: Path,
        learning_manifest: Path,
        *,
        output: Path | None = None,
    ) -> Path:
        """Record one human-reviewed staged pattern as a non-applied skill proposal.

        The Design Suite's learning phase is local and append-only. It
        revalidates the candidate and visual evidence, then records a bounded
        proposal for a future human-reviewed skill change. It cannot change
        the canonical website, a skill source, a package, hosting, credentials
        or a deployment state.
        """

        try:
            record = validate_design_learning_record(
                candidate_receipt,
                visual_review,
                learning_manifest,
                repo_root=self.repo_root,
            )
            candidate = record.get("candidate")
            if not isinstance(candidate, Mapping):
                raise WebsiteOperatorError("Design-learning record did not identify its staged candidate.")
            candidate_root = self.repo_root / str(candidate.get("root") or "")
            target = output or candidate_root / "feedback" / "design-learning.v1.json"
            written: Any = write_design_learning_record(
                record,
                target,
                repo_root=self.repo_root,
            )
            return cast(Path, written)
        except DesignLearningLedgerError as exc:
            raise WebsiteOperatorError(f"Design-learning ledger control failed: {exc}") from exc

    @staticmethod
    def _design_issue_score(
        findings: Sequence[Mapping[str, Any]],
        prefixes: Sequence[str],
    ) -> float:
        relevant = [
            finding
            for finding in findings
            if any(str(finding.get("code") or "").startswith(prefix) for prefix in prefixes)
        ]
        penalty = sum(
            0.25
            if finding.get("severity") == "error"
            else 0.06
            if finding.get("severity") == "warning"
            else 0.01
            for finding in relevant
        )
        return _clamp01(1.0 - penalty)

    def _competitor_research(self) -> Dict[str, Any]:
        design = self.config.get("design", {})
        max_age_days = int(design.get("competitor_max_age_days", 45) or 45)
        now = _utc_now()
        sources: List[Dict[str, Any]] = []
        fresh_count = 0
        for source in design.get("competitor_sources", []):
            checked_at = str(source.get("checked_at") or "")
            fresh = False
            if checked_at:
                try:
                    fresh = now - _parse_datetime(checked_at, "competitor checked_at") <= timedelta(
                        days=max_age_days
                    )
                except WebsiteOperatorError:
                    fresh = False
            if fresh:
                fresh_count += 1
            sources.append(
                {
                    "id": str(source.get("id") or ""),
                    "name": str(source.get("name") or ""),
                    "url": str(source.get("url") or ""),
                    "checked_at": checked_at,
                    "fresh": fresh,
                    "patterns": [str(item) for item in source.get("patterns", [])],
                    "use_policy": "Pattern evidence only; never copy competitor code, copy, or trade dress.",
                }
            )
        target = max(1, int(design.get("competitor_source_target", 8) or 8))
        return {
            "source_count": len(sources),
            "fresh_source_count": fresh_count,
            "target_source_count": target,
            "freshness_max_age_days": max_age_days,
            "coverage_score": round(_clamp01(fresh_count / target), 4),
            "sources": sources,
            "benchmark_blend": [
                "Benchling: calm scientific authority and disciplined taxonomy",
                "Databricks: strong information architecture and progressive disclosure",
                "Credo AI: product-as-instrument framing and visible operating proof",
                "Arize: technical openness, selectors, metrics, and trust cues",
                "IBM: restrained enterprise language, factsheets, documentation, and buyer clarity",
            ],
        }

    def _config_provenance_path(self) -> str | None:
        """Return the resolved, repository-relative config source when available.

        A design cycle may be created from an in-memory configuration in tests or
        tooling, but such a configuration cannot prove the file provenance that
        the benchmark control requires.  Treating that condition as a failed
        local evidence control is intentional and never grants a release path.
        """
        if self.config_path is None or not self.config_path.is_file():
            return None
        try:
            return self.config_path.relative_to(self.repo_root).as_posix()
        except ValueError:
            return None

    @staticmethod
    def _failed_design_evidence_control(error: str) -> Dict[str, Any]:
        return {
            "passed": False,
            "state": "blocked",
            "error": error,
            "release_eligible": False,
            "deployment_authority": "none",
        }

    def _editorial_asset_release_binding(
        self,
        receipt: Mapping[str, Any],
    ) -> Dict[str, Any]:
        """Reduce a provenance audit to exact public package evidence.

        The binding deliberately excludes rights-decision identities and local
        source-art paths.  It retains only the canonical manifest hash,
        privacy-safe capsule hashes, semantic surface hash, and the exact
        canonical public files that a release must contain byte-for-byte.
        """

        manifest = receipt.get("manifest")
        public_coverage = receipt.get("public_coverage")
        if not isinstance(manifest, Mapping) or not isinstance(
            public_coverage,
            Mapping,
        ):
            raise WebsiteOperatorError(
                "Editorial provenance audit lost its public manifest or coverage binding."
            )

        required_files: dict[str, Dict[str, Any]] = {}

        def add_public_file(raw_path: object, expected_sha256: object | None) -> None:
            if not isinstance(raw_path, str) or not raw_path.startswith("website/"):
                raise WebsiteOperatorError(
                    "Editorial provenance selected a path outside the canonical website."
                )
            relative = _safe_relative_path(raw_path[len("website/") :])
            source = self.site_root / relative
            if not source.is_file() or source.is_symlink():
                raise WebsiteOperatorError(f"Editorial release source is missing or unsafe: {relative}")
            observed_sha256 = _sha256_file(source)
            if expected_sha256 is not None and expected_sha256 != observed_sha256:
                raise WebsiteOperatorError(f"Editorial release source hash drifted: {relative}")
            row = {
                "path": relative,
                "bytes": source.stat().st_size,
                "sha256": observed_sha256,
            }
            previous = required_files.get(relative)
            if previous is not None and previous != row:
                raise WebsiteOperatorError(f"Editorial release source has conflicting bindings: {relative}")
            required_files[relative] = row

        raw_assets = receipt.get("assets")
        if not isinstance(raw_assets, list):
            raise WebsiteOperatorError("Editorial provenance audit lost its public asset records.")
        for asset in raw_assets:
            if not isinstance(asset, Mapping):
                raise WebsiteOperatorError("Editorial provenance audit contains a malformed public asset.")
            current_routes = asset.get("current_reference_routes")
            if not isinstance(current_routes, list):
                raise WebsiteOperatorError("Editorial provenance audit lost current route coverage.")
            if not current_routes:
                continue
            if asset.get("current_use_authorised") is not True:
                raise WebsiteOperatorError(
                    "A currently referenced editorial asset is not authorised for exact use."
                )
            variants = asset.get("variants")
            placements = asset.get("placements")
            if not isinstance(variants, list) or not isinstance(placements, list):
                raise WebsiteOperatorError("Editorial provenance audit lost variant or placement evidence.")
            for variant in variants:
                if not isinstance(variant, Mapping):
                    raise WebsiteOperatorError("Editorial provenance audit contains a malformed variant.")
                add_public_file(variant.get("path"), variant.get("sha256"))
            for placement in placements:
                if not isinstance(placement, Mapping):
                    raise WebsiteOperatorError("Editorial provenance audit contains a malformed placement.")
                if placement.get("currently_referenced") is True:
                    add_public_file(placement.get("destination_path"), None)

        rows = sorted(required_files.values(), key=lambda item: str(item["path"]))
        surface_binding = receipt.get("surface_binding")
        if surface_binding is not None and not isinstance(surface_binding, Mapping):
            raise WebsiteOperatorError("Editorial provenance audit surface binding is malformed.")
        binding = {
            "state": str(receipt.get("state") or ""),
            "manifest_id": manifest.get("manifest_id"),
            "manifest_file_sha256": manifest.get("sha256"),
            "asset_capsules_sha256": receipt.get("asset_capsules_sha256"),
            "route_asset_capsules_sha256": receipt.get("route_asset_capsules_sha256"),
            "surface_binding_sha256": (
                surface_binding.get("surface_binding_sha256") if isinstance(surface_binding, Mapping) else ""
            ),
            "coverage_sha256": public_coverage.get("coverage_sha256"),
            "required_public_files": rows,
            "required_public_files_sha256": _sha256_json(rows),
        }
        binding["binding_sha256"] = _sha256_json(binding)
        return binding

    @staticmethod
    def _json_editorial_surface_ids(value: object) -> list[str]:
        surface_ids: list[str] = []
        if isinstance(value, Mapping):
            for key, nested in value.items():
                if key == "surface_id" and isinstance(nested, str):
                    surface_ids.append(nested)
                surface_ids.extend(WebsiteOperator._json_editorial_surface_ids(nested))
        elif isinstance(value, list):
            for nested in value:
                surface_ids.extend(WebsiteOperator._json_editorial_surface_ids(nested))
        return surface_ids

    @staticmethod
    def _json_unbound_editorial_pair_state(
        value: object,
    ) -> tuple[bool, bool, int]:
        """Return unprotected Substack/WebP presence and bounded pair count."""

        if isinstance(value, str):
            has_substack = bool(
                re.search(
                    r"https?://[^\s\"'<>]*substack\.com(?:[/?#][^\s\"'<>]*)?",
                    value,
                    flags=re.IGNORECASE,
                )
            )
            has_webp = bool(
                re.search(
                    r"(?<![A-Za-z0-9])[^ \t\r\n\"'<>]*\.webp(?:[?#][^\s\"'<>]*)?",
                    value,
                    flags=re.IGNORECASE,
                )
            )
            return has_substack, has_webp, 0
        if isinstance(value, list):
            pair_count = 0
            for nested in value:
                _, _, nested_pairs = WebsiteOperator._json_unbound_editorial_pair_state(nested)
                pair_count += nested_pairs
            return False, False, pair_count
        if not isinstance(value, Mapping):
            return False, False, 0
        if isinstance(value.get("surface_id"), str):
            return False, False, 0
        has_substack = False
        has_webp = False
        pair_count = 0
        for nested in value.values():
            nested_substack, nested_webp, nested_pairs = WebsiteOperator._json_unbound_editorial_pair_state(
                nested
            )
            has_substack = has_substack or nested_substack
            has_webp = has_webp or nested_webp
            pair_count += nested_pairs
        if has_substack and has_webp:
            return False, False, pair_count + 1
        return has_substack, has_webp, pair_count

    def _editorial_semantic_surface_observation(self) -> Dict[str, Any]:
        """Return a copy-free inventory of public editorial surface markers."""

        attribute_pattern = re.compile(
            r"""\bdata-editorial-surface-id\s*=\s*(?P<quote>["'])(?P<value>.*?)(?P=quote)""",
            flags=re.IGNORECASE | re.DOTALL,
        )
        json_pattern = re.compile(
            r'"surface_id"\s*:\s*"(?P<value>(?:[^"\\]|\\.)*)"',
            flags=re.IGNORECASE,
        )
        controlled_id = re.compile(r"[a-z0-9][a-z0-9._:-]{0,127}")
        observed_counts: Counter[str] = Counter()
        invalid_marker_count = 0
        marker_file_count = 0
        ambiguous_file_count = 0
        scanned_file_count = 0
        for source in self._public_files():
            if source.suffix.casefold() not in TEXT_EXTENSIONS:
                continue
            scanned_file_count += 1
            text = source.read_text(encoding="utf-8-sig", errors="replace")
            raw_values = [match.group("value") for match in attribute_pattern.finditer(text)]
            if source.suffix.casefold() == ".json":
                try:
                    parsed_json: object = json.loads(text)
                except json.JSONDecodeError:
                    raw_values.extend(match.group("value") for match in json_pattern.finditer(text))
                else:
                    raw_values.extend(self._json_editorial_surface_ids(parsed_json))
            file_has_marker = bool(raw_values)
            if file_has_marker:
                marker_file_count += 1
            for raw_value in raw_values:
                surface_id = raw_value.strip()
                if controlled_id.fullmatch(surface_id):
                    observed_counts[surface_id] += 1
                else:
                    invalid_marker_count += 1
            has_substack_reference = bool(
                re.search(
                    r"https?://[^\s\"'<>]*substack\.com(?:[/?#][^\s\"'<>]*)?",
                    text,
                    flags=re.IGNORECASE,
                )
            )
            has_webp_reference = bool(
                re.search(
                    r"(?<![A-Za-z0-9])[^ \t\r\n\"'<>]*\.webp\b",
                    text,
                    flags=re.IGNORECASE,
                )
            )
            unbound_pair_count = 0
            if source.suffix.casefold() in {".html", ".htm"}:
                parser = _EditorialSemanticHTMLParser()
                try:
                    parser.feed(text)
                    parser.close()
                except (ValueError, TypeError):
                    unbound_pair_count = int(
                        has_substack_reference and has_webp_reference and not file_has_marker
                    )
                else:
                    unbound_pair_count = parser.ambiguous_pair_count
            elif source.suffix.casefold() == ".json":
                try:
                    parsed_for_pairs: object = json.loads(text)
                except json.JSONDecodeError:
                    unbound_pair_count = int(
                        has_substack_reference and has_webp_reference and not file_has_marker
                    )
                else:
                    _, _, unbound_pair_count = self._json_unbound_editorial_pair_state(parsed_for_pairs)
            elif has_substack_reference and has_webp_reference and not file_has_marker:
                unbound_pair_count = 1
            if unbound_pair_count:
                ambiguous_file_count += 1

        observed_ids = sorted(observed_counts)
        payload: Dict[str, Any] = {
            "scanned_public_text_file_count": scanned_file_count,
            "marker_file_count": marker_file_count,
            "surface_ids": observed_ids,
            "surface_id_count": len(observed_ids),
            "surface_marker_occurrence_count": sum(observed_counts.values()),
            "duplicate_surface_id_count": sum(count > 1 for count in observed_counts.values()),
            "invalid_surface_marker_count": invalid_marker_count,
            "ambiguous_substack_webp_file_count": ambiguous_file_count,
            "raw_copy_recorded": False,
            "raw_urls_recorded": False,
        }
        payload["observation_sha256"] = _sha256_json(payload)
        return payload

    @staticmethod
    def _declared_editorial_surface_ids(receipt: Mapping[str, Any]) -> list[str]:
        raw_bindings = receipt.get("surface_bindings")
        if not isinstance(raw_bindings, list):
            raise WebsiteOperatorError("Editorial provenance audit lost its structural surface bindings.")
        declared: set[str] = set()
        for binding in raw_bindings:
            placements = binding.get("placements") if isinstance(binding, Mapping) else None
            if not isinstance(placements, list):
                raise WebsiteOperatorError(
                    "Editorial provenance audit contains malformed structural surface bindings."
                )
            for placement in placements:
                surface_id = placement.get("surface_id") if isinstance(placement, Mapping) else None
                if not isinstance(surface_id, str) or not re.fullmatch(
                    r"[a-z0-9][a-z0-9._:-]{0,127}", surface_id
                ):
                    raise WebsiteOperatorError(
                        "Editorial provenance audit contains an invalid structural surface identifier."
                    )
                if surface_id in declared:
                    raise WebsiteOperatorError(
                        "Editorial provenance audit declares a duplicate structural surface identifier."
                    )
                declared.add(surface_id)
        return sorted(declared)

    def _editorial_asset_evidence_control(self) -> Dict[str, Any]:
        """Audit the canonical per-asset provenance record when it is in use."""

        manifest_path = self.repo_root / DEFAULT_EDITORIAL_PROVENANCE_MANIFEST
        semantic_observation = self._editorial_semantic_surface_observation()
        controlled_asset_root = self.site_root / "assets" / "images" / "research" / "substack"
        controlled_files_present = bool(
            controlled_asset_root.is_dir()
            and any(path.is_file() for path in controlled_asset_root.rglob("*"))
        )
        controlled_reference_present = False
        reference_token = "assets/images/research/substack/"
        for source in self._public_files():
            if source.suffix.casefold() in TEXT_EXTENSIONS and reference_token in source.read_text(
                encoding="utf-8-sig",
                errors="replace",
            ):
                controlled_reference_present = True
                break

        if not manifest_path.is_file():
            semantic_evidence_present = any(
                int(semantic_observation[key]) > 0
                for key in (
                    "surface_marker_occurrence_count",
                    "invalid_surface_marker_count",
                    "ambiguous_substack_webp_file_count",
                )
            )
            if controlled_files_present or controlled_reference_present or semantic_evidence_present:
                return self._failed_design_evidence_control(
                    "Controlled editorial assets, references, or semantic surfaces exist without "
                    "the canonical per-asset provenance manifest."
                )
            binding = {
                "state": "not-required-no-controlled-editorial-assets",
                "manifest_path": DEFAULT_EDITORIAL_PROVENANCE_MANIFEST.as_posix(),
                "manifest_present": False,
                "controlled_files_present": False,
                "controlled_reference_present": False,
                "semantic_surface_observation": semantic_observation,
                "required_public_files": [],
                "required_public_files_sha256": _sha256_json([]),
            }
            binding["binding_sha256"] = _sha256_json(binding)
            return {
                "passed": True,
                "state": binding["state"],
                "error": "",
                "receipt": None,
                "binding": binding,
                "release_eligible": False,
                "deployment_authority": "none",
            }

        try:
            receipt = audit_design_editorial_asset_provenance_file(
                manifest_path,
                repo_root=self.repo_root,
            )
            declared_surface_ids = self._declared_editorial_surface_ids(receipt)
            observed_surface_ids = semantic_observation["surface_ids"]
            if not isinstance(observed_surface_ids, list):
                raise WebsiteOperatorError("Editorial semantic surface observation is malformed.")
            undeclared_surface_ids = sorted(set(observed_surface_ids).difference(declared_surface_ids))
            if semantic_observation["invalid_surface_marker_count"]:
                raise WebsiteOperatorError("Public website contains an invalid editorial surface identifier.")
            if semantic_observation["duplicate_surface_id_count"]:
                raise WebsiteOperatorError(
                    "Public website contains a duplicate editorial surface identifier."
                )
            if semantic_observation["ambiguous_substack_webp_file_count"]:
                raise WebsiteOperatorError(
                    "Public website contains a Substack plus WebP editorial reference "
                    "without a structural surface identifier."
                )
            if undeclared_surface_ids:
                raise WebsiteOperatorError(
                    "Public website contains editorial surface identifiers absent from "
                    "the canonical provenance manifest."
                )
            if receipt.get("passed") is True:
                binding = self._editorial_asset_release_binding(receipt)
            else:
                manifest = receipt.get("manifest")
                coverage = receipt.get("public_coverage")
                surface_binding = receipt.get("surface_binding")
                binding = {
                    "state": str(receipt.get("state") or "blocked"),
                    "manifest_file_sha256": (manifest.get("sha256") if isinstance(manifest, Mapping) else ""),
                    "asset_capsules_sha256": receipt.get("asset_capsules_sha256"),
                    "route_asset_capsules_sha256": receipt.get("route_asset_capsules_sha256"),
                    "surface_binding_sha256": (
                        surface_binding.get("surface_binding_sha256")
                        if isinstance(surface_binding, Mapping)
                        else ""
                    ),
                    "coverage_sha256": (
                        coverage.get("coverage_sha256") if isinstance(coverage, Mapping) else ""
                    ),
                    "required_public_files": [],
                    "required_public_files_sha256": _sha256_json([]),
                }
                binding["binding_sha256"] = _sha256_json(binding)
            binding.pop("binding_sha256", None)
            binding.update(
                {
                    "semantic_surface_observation": semantic_observation,
                    "declared_surface_id_count": len(declared_surface_ids),
                    "declared_surface_ids_sha256": _sha256_json(declared_surface_ids),
                    "undeclared_surface_id_count": 0,
                }
            )
            binding["binding_sha256"] = _sha256_json(binding)
            return {
                "passed": receipt.get("passed") is True,
                "state": receipt.get("state"),
                "error": "",
                "receipt": receipt,
                "binding": binding,
                "release_eligible": False,
                "deployment_authority": "none",
            }
        except (
            DesignEditorialAssetProvenanceError,
            OSError,
            TypeError,
            ValueError,
            WebsiteOperatorError,
        ) as exc:
            return self._failed_design_evidence_control(
                f"Editorial asset provenance control failed: {type(exc).__name__}: {exc}"
            )

    def _design_evidence_controls(self) -> Dict[str, Any]:
        """Run read-only provenance controls used by the design-cycle gates.

        These controls verify local benchmark, public-claim, investor-copy,
        research-source and privacy-safe stakeholder-signal evidence only.
        They do not fetch competitor sites, read correspondence, build a
        package, use credentials, or grant any release/deployment authority.
        Their own non-authoritative fields are retained in the receipt; the
        WebsiteOperator remains responsible for the separate audit, visual,
        human-review and owner-gate lifecycle.
        """
        benchmark: Dict[str, Any]
        config_path = self._config_provenance_path()
        if config_path is None:
            benchmark = self._failed_design_evidence_control(
                "A source-bound repository-relative WebsiteOperator config file is required."
            )
        else:
            try:
                snapshot = discover_design_benchmark_evidence(
                    self.repo_root,
                    config_path=config_path,
                )
                verification = verify_design_benchmark_evidence_against_config(
                    snapshot,
                    self.config,
                    repo_root=self.repo_root,
                    config_path=config_path,
                )
                benchmark = {
                    "passed": verification.get("passed") is True,
                    "error": "",
                    "snapshot": snapshot,
                    "verification": verification,
                    "release_eligible": False,
                    "deployment_authority": "none",
                }
            except (DesignBenchmarkEvidenceError, OSError, TypeError, ValueError) as exc:
                benchmark = self._failed_design_evidence_control(
                    f"Benchmark evidence control failed: {type(exc).__name__}: {exc}"
                )

        try:
            receipt = audit_public_claim_evidence_file(repo_root=self.repo_root)
            public_claims: Dict[str, Any] = {
                "passed": receipt.get("passed") is True,
                "error": "",
                "receipt": receipt,
                "release_eligible": False,
                "deployment_authority": "none",
            }
        except (PublicClaimEvidenceError, OSError, TypeError, ValueError) as exc:
            public_claims = self._failed_design_evidence_control(
                f"Public-claim evidence control failed: {type(exc).__name__}: {exc}"
            )

        investor_copy = self._investor_copy_evidence_control()

        try:
            receipt = audit_design_research_sources_file(repo_root=self.repo_root)
            research_refresh: Dict[str, Any] = {
                "passed": receipt.get("passed") is True,
                "error": "",
                "receipt": receipt,
                "release_eligible": False,
                "deployment_authority": "none",
            }
        except (DesignResearchRefreshError, OSError, TypeError, ValueError) as exc:
            research_refresh = self._failed_design_evidence_control(
                f"Design research refresh control failed: {type(exc).__name__}: {exc}"
            )

        try:
            receipt = audit_design_stakeholder_feedback_file(repo_root=self.repo_root)
            stakeholder_feedback: Dict[str, Any] = {
                "passed": receipt.get("passed") is True,
                "error": "",
                "receipt": receipt,
                "release_eligible": False,
                "deployment_authority": "none",
            }
        except (
            DesignStakeholderFeedbackError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            stakeholder_feedback = self._failed_design_evidence_control(
                f"Stakeholder feedback control failed: {type(exc).__name__}: {exc}"
            )

        editorial_assets = self._editorial_asset_evidence_control()

        return {
            "benchmark": benchmark,
            "public_claims": public_claims,
            "investor_copy": investor_copy,
            "research_refresh": research_refresh,
            "stakeholder_feedback": stakeholder_feedback,
            "editorial_assets": editorial_assets,
            "release_eligible": False,
            "deployment_authority": "none",
        }

    def _investor_copy_evidence_control(self) -> Dict[str, Any]:
        """Return privacy-minimised, source-bound investor-copy evidence."""

        def exact_mapping(
            value: object,
            expected_fields: frozenset[str],
            *,
            label: str,
        ) -> Mapping[str, Any]:
            if not isinstance(value, Mapping) or set(value) != expected_fields:
                raise WebsiteOperatorError(f"{label} has an invalid field contract.")
            return value

        def safe_count(value: object, *, label: str) -> int:
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise WebsiteOperatorError(f"{label} must be a non-negative integer.")
            return value

        def safe_sha256(value: object, *, label: str) -> str:
            if not isinstance(value, str) or re.fullmatch(r"[A-F0-9]{64}", value) is None:
                raise WebsiteOperatorError(f"{label} must be one uppercase SHA-256 digest.")
            return value

        def safe_route(value: object, *, label: str) -> str:
            if (
                not isinstance(value, str)
                or value != value.strip()
                or re.fullmatch(r"/[a-z0-9._/-]*", value) is None
                or "//" in value
                or any(part in {"", ".", ".."} for part in value.strip("/").split("/") if value != "/")
            ):
                raise WebsiteOperatorError(f"{label} must be one safe local route.")
            return value

        def safe_html_path(value: object, *, label: str) -> str:
            if (
                not isinstance(value, str)
                or value != value.strip()
                or re.fullmatch(r"(?:[a-z0-9._-]+/)*[a-z0-9._-]+\.html", value) is None
            ):
                raise WebsiteOperatorError(f"{label} must be one safe relative HTML path.")
            return value

        try:
            receipt = audit_investor_copy_quality_file(
                repo_root=self.repo_root,
                website_root=self.site_root,
            )
            exact_mapping(
                receipt,
                frozenset(
                    {
                        "schema",
                        "audited_at",
                        "state",
                        "passed",
                        "release_eligible",
                        "package_authority",
                        "deployment_authority",
                        "authority",
                        "policy",
                        "website_root",
                        "routes",
                        "findings",
                        "summary",
                        "next_gate",
                    }
                ),
                label="Investor-copy audit receipt",
            )
            if (
                receipt.get("schema") != INVESTOR_COPY_AUDIT_SCHEMA
                or receipt.get("authority") != INVESTOR_COPY_AUTHORITY
                or receipt.get("release_eligible") is not False
                or receipt.get("package_authority") != "none"
                or receipt.get("deployment_authority") != "none"
                or not isinstance(receipt.get("passed"), bool)
                or not isinstance(receipt.get("next_gate"), str)
            ):
                raise WebsiteOperatorError(
                    "Investor-copy audit schema, authority or non-release boundary is invalid."
                )
            audited_at = _parse_datetime(receipt.get("audited_at"), "Investor-copy audited_at")

            policy = exact_mapping(
                receipt.get("policy"),
                frozenset(
                    {
                        "policy_id",
                        "path",
                        "sha256",
                        "issued_at",
                        "refresh_by",
                        "current",
                    }
                ),
                label="Investor-copy policy binding",
            )
            policy_id = policy.get("policy_id")
            policy_path = policy.get("path")
            if (
                not isinstance(policy_id, str)
                or re.fullmatch(r"[a-z0-9][a-z0-9-]{2,127}", policy_id) is None
                or policy_path != DEFAULT_INVESTOR_COPY_POLICY.as_posix()
                or not isinstance(policy.get("current"), bool)
            ):
                raise WebsiteOperatorError("Investor-copy policy identity or path is invalid.")
            policy_sha256 = safe_sha256(
                policy.get("sha256"),
                label="Investor-copy policy digest",
            )
            issued_at = _parse_datetime(
                policy.get("issued_at"),
                "Investor-copy policy issued_at",
            )
            refresh_by = _parse_datetime(
                policy.get("refresh_by"),
                "Investor-copy policy refresh_by",
            )
            policy_current_at_audit = issued_at <= audited_at <= refresh_by
            if policy.get("current") is not policy_current_at_audit:
                raise WebsiteOperatorError(
                    "Investor-copy policy freshness disagrees with the audit timestamp."
                )
            policy_target = _regular_single_link_file(
                self.repo_root / str(policy_path),
                label="Investor-copy policy",
            )
            if _sha256_file(policy_target) != policy_sha256:
                raise WebsiteOperatorError(
                    "Investor-copy policy digest does not match the current policy file."
                )
            policy_current = policy_current_at_audit and issued_at <= _utc_now() <= refresh_by

            expected_website_root = self.site_root.relative_to(self.repo_root).as_posix()
            if receipt.get("website_root") != expected_website_root:
                raise WebsiteOperatorError("Investor-copy audit is not bound to the configured website root.")

            routes = receipt.get("routes")
            findings = receipt.get("findings")
            summary = exact_mapping(
                receipt.get("summary"),
                frozenset(
                    {
                        "route_count",
                        "finding_count",
                        "blocker_count",
                        "warning_count",
                    }
                ),
                label="Investor-copy summary",
            )
            if not isinstance(routes, list) or not routes or not isinstance(findings, list):
                raise WebsiteOperatorError("Investor-copy audit receipt is malformed.")

            route_records: List[Dict[str, Any]] = []
            route_keys: set[tuple[str, str]] = set()
            route_names: set[str] = set()
            route_paths: set[str] = set()
            route_counts: Dict[tuple[str, str], tuple[int, int, int]] = {}
            for index, raw_route in enumerate(routes):
                route = exact_mapping(
                    raw_route,
                    frozenset(
                        {
                            "route",
                            "path",
                            "sha256",
                            "title",
                            "h1",
                            "finding_count",
                            "blocker_count",
                            "warning_count",
                        }
                    ),
                    label=f"Investor-copy route[{index}]",
                )
                route_name = safe_route(
                    route.get("route"),
                    label=f"Investor-copy route[{index}] route",
                )
                route_path = safe_html_path(
                    route.get("path"),
                    label=f"Investor-copy route[{index}] path",
                )
                if (
                    _normalise_design_route(route_name) != route_path
                    or route_name in route_names
                    or route_path in route_paths
                    or not isinstance(route.get("title"), str)
                    or not isinstance(route.get("h1"), str)
                ):
                    raise WebsiteOperatorError(f"Investor-copy route[{index}] source binding is invalid.")
                route_sha256 = safe_sha256(
                    route.get("sha256"),
                    label=f"Investor-copy route[{index}] digest",
                )
                source_path = _regular_single_link_file(
                    self.site_root / route_path,
                    label=f"Investor-copy route[{index}] source",
                )
                if _sha256_file(source_path) != route_sha256:
                    raise WebsiteOperatorError(
                        f"Investor-copy route[{index}] digest does not match its current source."
                    )
                finding_count = safe_count(
                    route.get("finding_count"),
                    label=f"Investor-copy route[{index}] finding_count",
                )
                blocker_count = safe_count(
                    route.get("blocker_count"),
                    label=f"Investor-copy route[{index}] blocker_count",
                )
                warning_count = safe_count(
                    route.get("warning_count"),
                    label=f"Investor-copy route[{index}] warning_count",
                )
                if finding_count != blocker_count + warning_count:
                    raise WebsiteOperatorError(
                        f"Investor-copy route[{index}] finding counts are inconsistent."
                    )
                key = (route_name, route_path)
                route_names.add(route_name)
                route_paths.add(route_path)
                route_keys.add(key)
                route_counts[key] = (finding_count, blocker_count, warning_count)
                route_records.append(
                    {
                        "route": route_name,
                        "path": route_path,
                        "sha256": route_sha256,
                        "finding_count": finding_count,
                        "blocker_count": blocker_count,
                        "warning_count": warning_count,
                    }
                )

            observed_finding_counts: Counter[tuple[str, str]] = Counter()
            observed_blocker_counts: Counter[tuple[str, str]] = Counter()
            observed_warning_counts: Counter[tuple[str, str]] = Counter()
            global_findings = 0
            for index, raw_finding in enumerate(findings):
                finding = exact_mapping(
                    raw_finding,
                    frozenset(
                        {
                            "rule_id",
                            "severity",
                            "route",
                            "path",
                            "message",
                            "evidence",
                        }
                    ),
                    label=f"Investor-copy finding[{index}]",
                )
                rule_id = finding.get("rule_id")
                severity = finding.get("severity")
                finding_route = finding.get("route")
                finding_path = finding.get("path")
                if (
                    not isinstance(rule_id, str)
                    or re.fullmatch(r"[a-z0-9][a-z0-9-]{2,127}", rule_id) is None
                    or severity not in {"blocker", "warning"}
                    or not isinstance(finding.get("message"), str)
                    or not isinstance(finding.get("evidence"), Mapping)
                ):
                    raise WebsiteOperatorError(
                        f"Investor-copy finding[{index}] has an invalid safe contract."
                    )
                if finding_route == "*":
                    if (
                        policy_current_at_audit
                        or rule_id != "policy-freshness"
                        or finding_path != policy_path
                    ):
                        raise WebsiteOperatorError(
                            f"Investor-copy finding[{index}] has an invalid global binding."
                        )
                    global_findings += 1
                    continue
                route_name = safe_route(
                    finding_route,
                    label=f"Investor-copy finding[{index}] route",
                )
                route_path = safe_html_path(
                    finding_path,
                    label=f"Investor-copy finding[{index}] path",
                )
                key = (route_name, route_path)
                if key not in route_keys:
                    raise WebsiteOperatorError(
                        f"Investor-copy finding[{index}] does not bind one audited route."
                    )
                observed_finding_counts[key] += 1
                if severity == "blocker":
                    observed_blocker_counts[key] += 1
                else:
                    observed_warning_counts[key] += 1

            for key, expected_counts in route_counts.items():
                observed_counts = (
                    observed_finding_counts[key],
                    observed_blocker_counts[key],
                    observed_warning_counts[key],
                )
                if observed_counts != expected_counts:
                    raise WebsiteOperatorError("Investor-copy route and finding counts are inconsistent.")

            summary_route_count = safe_count(
                summary.get("route_count"),
                label="Investor-copy summary route_count",
            )
            summary_finding_count = safe_count(
                summary.get("finding_count"),
                label="Investor-copy summary finding_count",
            )
            summary_blocker_count = safe_count(
                summary.get("blocker_count"),
                label="Investor-copy summary blocker_count",
            )
            summary_warning_count = safe_count(
                summary.get("warning_count"),
                label="Investor-copy summary warning_count",
            )
            expected_finding_count = sum(counts[0] for counts in route_counts.values()) + global_findings
            expected_blocker_count = sum(
                finding.get("severity") == "blocker" for finding in findings if isinstance(finding, Mapping)
            )
            expected_warning_count = sum(
                finding.get("severity") == "warning" for finding in findings if isinstance(finding, Mapping)
            )
            if (
                summary_route_count != len(route_records)
                or summary_finding_count != len(findings)
                or summary_finding_count != expected_finding_count
                or summary_blocker_count != expected_blocker_count
                or summary_warning_count != expected_warning_count
            ):
                raise WebsiteOperatorError(
                    "Investor-copy route, finding and summary counts are inconsistent."
                )

            audit_passed = summary_blocker_count == 0 and policy_current_at_audit
            expected_audit_state = "pass" if audit_passed else "blocked"
            if receipt.get("passed") is not audit_passed or receipt.get("state") != expected_audit_state:
                raise WebsiteOperatorError("Investor-copy audit state and counts are inconsistent.")
            control_passed = (
                audit_passed and policy_current and summary_blocker_count == 0 and summary_warning_count == 0
            )
            control_state = "pass" if control_passed else "blocked"

            route_bindings: List[Dict[str, Any]] = []
            for route in route_records:
                route_bindings.append(
                    {
                        "route": route["route"],
                        "path": route["path"],
                        "sha256": route["sha256"],
                        "finding_count": route["finding_count"],
                        "blocker_count": route["blocker_count"],
                        "warning_count": route["warning_count"],
                    }
                )
            route_bindings.sort(key=lambda row: str(row.get("path") or ""))
            policy_binding = {
                "policy_id": policy_id,
                "path": policy_path,
                "sha256": policy_sha256,
                "refresh_by": _iso(refresh_by),
                "current": policy_current,
            }
            compact_summary = {
                "route_count": summary_route_count,
                "finding_count": summary_finding_count,
                "blocker_count": summary_blocker_count,
                "warning_count": summary_warning_count,
            }
            binding: Dict[str, Any] = {
                "state": control_state,
                "policy_path": policy_binding["path"],
                "policy_sha256": policy_binding["sha256"],
                "policy_current": policy_binding["current"],
                "website_root": expected_website_root,
                "route_count": compact_summary["route_count"],
                "route_hashes_sha256": _sha256_json(route_bindings),
                "findings_sha256": _sha256_json(findings),
                "blocker_count": compact_summary["blocker_count"],
                "warning_count": compact_summary["warning_count"],
            }
            binding["binding_sha256"] = _sha256_json(binding)
            compact_receipt = {
                "schema": INVESTOR_COPY_AUDIT_SCHEMA,
                "state": control_state,
                "passed": control_passed,
                "policy": policy_binding,
                "website_root": expected_website_root,
                "routes": route_bindings,
                "summary": compact_summary,
                "findings_sha256": binding["findings_sha256"],
            }
            return {
                "passed": control_passed,
                "state": control_state,
                "error": "",
                "receipt": compact_receipt,
                "binding": binding,
                "release_eligible": False,
                "deployment_authority": "none",
            }
        except (
            InvestorCopyQualityError,
            OSError,
            TypeError,
            ValueError,
            WebsiteOperatorError,
        ) as exc:
            return self._failed_design_evidence_control(
                f"Investor-copy quality control failed: {type(exc).__name__}: {exc}"
            )

    @staticmethod
    def _design_evidence_gate_summary(control: Mapping[str, Any]) -> Dict[str, Any]:
        summary: Dict[str, Any] = {
            "passed": control.get("passed") is True,
            "error": str(control.get("error") or ""),
            "release_eligible": False,
            "deployment_authority": "none",
        }
        snapshot = control.get("snapshot")
        if isinstance(snapshot, Mapping):
            summary["config"] = snapshot.get("config")
            summary["source_count"] = len(snapshot.get("sources") or [])
        receipt = control.get("receipt")
        if isinstance(receipt, Mapping):
            register = receipt.get("register")
            if isinstance(register, Mapping):
                summary["register"] = register
            receipt_summary = receipt.get("summary")
            if isinstance(receipt_summary, Mapping):
                summary["summary"] = receipt_summary
            declaration = receipt.get("declaration")
            if isinstance(declaration, Mapping):
                summary["declaration"] = declaration
            artwork = receipt.get("artwork")
            if isinstance(artwork, Mapping):
                summary["artwork"] = {
                    "state": artwork.get("state"),
                    "cleared_for_use": artwork.get("cleared_for_use"),
                }
            feedback = receipt.get("feedback")
            if isinstance(feedback, Mapping):
                summary["feedback"] = {
                    "feedback_id": feedback.get("feedback_id"),
                    "path": feedback.get("path"),
                    "sha256": feedback.get("sha256"),
                }
                summary["freshness"] = receipt.get("freshness")
                summary["signal_capsules_sha256"] = receipt.get("signal_capsules_sha256")
        verification = control.get("verification")
        if isinstance(verification, Mapping):
            summary["verification"] = {
                "state": verification.get("state"),
                "passed": verification.get("passed") is True,
            }
        binding = control.get("binding")
        if isinstance(binding, Mapping):
            if "policy_sha256" in binding:
                summary["binding"] = {
                    "state": binding.get("state"),
                    "policy_path": binding.get("policy_path"),
                    "policy_sha256": binding.get("policy_sha256"),
                    "policy_current": binding.get("policy_current"),
                    "website_root": binding.get("website_root"),
                    "route_count": binding.get("route_count"),
                    "route_hashes_sha256": binding.get("route_hashes_sha256"),
                    "findings_sha256": binding.get("findings_sha256"),
                    "blocker_count": binding.get("blocker_count"),
                    "warning_count": binding.get("warning_count"),
                    "binding_sha256": binding.get("binding_sha256"),
                }
            else:
                summary["binding"] = {
                    "state": binding.get("state"),
                    "manifest_present": binding.get("manifest_present"),
                    "manifest_file_sha256": binding.get("manifest_file_sha256"),
                    "asset_capsules_sha256": binding.get("asset_capsules_sha256"),
                    "route_asset_capsules_sha256": binding.get("route_asset_capsules_sha256"),
                    "surface_binding_sha256": binding.get("surface_binding_sha256"),
                    "required_public_files_sha256": binding.get("required_public_files_sha256"),
                    "binding_sha256": binding.get("binding_sha256"),
                }
        return summary

    def _previous_design_cycle(self, explicit: Path | None = None) -> Dict[str, Any] | None:
        candidates: List[Path]
        if explicit:
            candidates = [explicit.resolve()]
        else:
            candidates = sorted(
                (
                    path
                    for path in self.receipts_dir.glob("*-design-cycle-*.json")
                    if _AUTOMATIC_DESIGN_CYCLE_NAME.fullmatch(path.name)
                ),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )[:1]
        if not candidates:
            return None
        previous = _read_json(candidates[0])
        if previous.get("schema") != DESIGN_CYCLE_SCHEMA:
            raise WebsiteOperatorError("Previous design cycle has an unsupported schema.")
        if previous.get("config_sha256") != self.config_sha256:
            return None
        return previous

    def design_cycle_payload(
        self,
        goal: str,
        routes: Sequence[str] | None = None,
        run_external: bool = True,
        previous_cycle: Path | None = None,
    ) -> Dict[str, Any]:
        """Build a deterministic, local-only public-website design job.

        The HNC adaptation is deliberately narrow: it supplies the weighted
        evidence-coherence feedback structure.  It is not aesthetic truth,
        scientific validation, or publication authority.
        """
        objective = str(goal or "").strip()
        if not objective:
            raise WebsiteOperatorError("A design-cycle goal is required.")
        configured_routes = list(self.config["site"].get("critical_routes", []))
        requested_routes = list(routes or configured_routes)
        safe_routes = [_normalise_design_route(route) for route in requested_routes]
        missing_routes = [route for route in safe_routes if not (self.site_root / route).resolve().is_file()]

        audit = self.audit_payload(run_external=run_external)
        inventory = self.inventory_payload()
        findings = [finding for finding in audit.get("findings", []) if isinstance(finding, dict)]
        benchmark = self._competitor_research()
        evidence_controls = self._design_evidence_controls()
        benchmark_evidence = evidence_controls["benchmark"]
        public_claim_evidence = evidence_controls["public_claims"]
        investor_copy_evidence = evidence_controls["investor_copy"]
        research_refresh_evidence = evidence_controls["research_refresh"]
        stakeholder_feedback_evidence = evidence_controls["stakeholder_feedback"]
        editorial_asset_evidence = evidence_controls["editorial_assets"]
        source_integrity = self._design_issue_score(
            findings,
            ("claims.", "security.secret", "security.blocked"),
        )
        if (
            public_claim_evidence.get("passed") is not True
            or investor_copy_evidence.get("passed") is not True
            or research_refresh_evidence.get("passed") is not True
            or stakeholder_feedback_evidence.get("passed") is not True
            or editorial_asset_evidence.get("passed") is not True
        ):
            source_integrity = 0.0
        route_coverage = _clamp01((len(safe_routes) - len(missing_routes)) / max(1, len(safe_routes)))
        external_integrity = self._design_issue_score(findings, ("external.",))
        dimensions = {
            "source_strength": round(
                _clamp01(0.55 * source_integrity + 0.45 * float(benchmark["coverage_score"])),
                4,
            ),
            "coherence": round(
                self._design_issue_score(
                    findings,
                    ("metadata.", "structure.", "ethos.", "references."),
                ),
                4,
            ),
            "repeatability": round(
                _clamp01(0.55 * route_coverage + 0.45 * external_integrity),
                4,
            ),
            "feasibility": round(
                self._design_issue_score(
                    findings,
                    ("accessibility.", "motion.", "budget.", "security."),
                ),
                4,
            ),
            "contradiction_control": round(
                self._design_issue_score(findings, ("claims.", "ethos.")),
                4,
            ),
        }
        weights = {
            key: float(value)
            for key, value in self.config.get("design", {}).get("nexus_weights", DESIGN_NEXUS_WEIGHTS).items()
        }
        weighted_score = round(
            100.0 * sum(dimensions[key] * weights[key] for key in DESIGN_NEXUS_WEIGHTS),
            2,
        )
        spread = round(max(dimensions.values()) - min(dimensions.values()), 4)
        coherence = round(_clamp01((weighted_score / 100.0) * (1.0 - 0.35 * spread)), 4)
        minimum_score = float(self.config.get("design", {}).get("minimum_score", 85.0))
        audit_blocker_count = int(audit.get("summary", {}).get("blockers", 0) or 0)
        audit_warning_count = int(audit.get("summary", {}).get("warnings", 0) or 0)
        copy_receipt = investor_copy_evidence.get("receipt")
        copy_summary = copy_receipt.get("summary") if isinstance(copy_receipt, Mapping) else {}
        copy_blocker_count = (
            int(copy_summary.get("blocker_count", 0) or 0) if isinstance(copy_summary, Mapping) else 0
        )
        copy_warning_count = (
            int(copy_summary.get("warning_count", 0) or 0) if isinstance(copy_summary, Mapping) else 0
        )
        blocker_count = audit_blocker_count + copy_blocker_count
        warning_count = audit_warning_count + copy_warning_count
        hard_gates = [
            {
                "id": "source_tree_bound",
                "passed": bool(audit.get("source_tree_sha256")),
                "evidence": audit.get("source_tree_sha256"),
            },
            {
                "id": "website_audit",
                "passed": audit.get("state") == "pass",
                "evidence": audit.get("summary"),
            },
            {
                "id": "external_checks_complete",
                "passed": run_external and audit.get("summary", {}).get("external_checks_run") is True,
                "evidence": {
                    "run_external": run_external,
                    "external_checks_run": audit.get("summary", {}).get("external_checks_run"),
                    "diagnostic_skip_cannot_verify": True,
                },
            },
            {
                "id": "open_audit_findings_closed",
                "passed": blocker_count == 0 and warning_count == 0,
                "evidence": {
                    "blockers": blocker_count,
                    "warnings": warning_count,
                    "website_audit_blockers": audit_blocker_count,
                    "website_audit_warnings": audit_warning_count,
                    "investor_copy_blockers": copy_blocker_count,
                    "investor_copy_warnings": copy_warning_count,
                    "release_requires_zero_open_warnings": True,
                },
            },
            {
                "id": "route_coverage",
                "passed": not missing_routes,
                "evidence": {"requested": safe_routes, "missing": missing_routes},
            },
            {
                "id": "competitor_research_fresh",
                "passed": benchmark["fresh_source_count"] >= benchmark["target_source_count"],
                "evidence": {
                    "fresh": benchmark["fresh_source_count"],
                    "target": benchmark["target_source_count"],
                },
            },
            {
                "id": "benchmark_evidence_current",
                "passed": benchmark_evidence.get("passed") is True,
                "evidence": self._design_evidence_gate_summary(benchmark_evidence),
            },
            {
                "id": "claims_evidence_current",
                "passed": public_claim_evidence.get("passed") is True,
                "evidence": self._design_evidence_gate_summary(public_claim_evidence),
            },
            {
                "id": "investor_copy_quality_current",
                "passed": investor_copy_evidence.get("passed") is True,
                "evidence": self._design_evidence_gate_summary(investor_copy_evidence),
            },
            {
                "id": "research_source_refresh_current",
                "passed": research_refresh_evidence.get("passed") is True,
                "evidence": self._design_evidence_gate_summary(research_refresh_evidence),
            },
            {
                "id": "stakeholder_feedback_current",
                "passed": stakeholder_feedback_evidence.get("passed") is True,
                "evidence": self._design_evidence_gate_summary(stakeholder_feedback_evidence),
            },
            {
                "id": "editorial_asset_provenance_current",
                "passed": editorial_asset_evidence.get("passed") is True,
                "evidence": self._design_evidence_gate_summary(editorial_asset_evidence),
            },
            {
                "id": "design_nexus_threshold",
                "passed": weighted_score >= minimum_score,
                "evidence": {"score": weighted_score, "minimum": minimum_score},
            },
        ]
        objective_hard_gates_pass = all(bool(gate["passed"]) for gate in hard_gates)
        previous = self._previous_design_cycle(previous_cycle)
        if previous and str(previous.get("goal") or "").strip() != objective:
            if previous_cycle is not None:
                raise WebsiteOperatorError(
                    "Previous design cycle belongs to a different bounded work-order goal."
                )
            previous = None
        previous_score = float(previous.get("design_nexus", {}).get("score", 0.0)) if previous else None

        role_contracts = [
            (
                "design-director",
                "Website Design Director",
                "Own the brief, institutional quality bar, design council and human visual review.",
                ["website/", "docs/audits/", "artifacts/website-operator/"],
            ),
            (
                "benchmark-scout",
                "Competitor Research Scout",
                "Refresh official-source benchmark patterns without copying competitor expression.",
                ["docs/audits/", "data/website_operator/"],
            ),
            (
                "brand-system-lead",
                "Brand and Design-System Lead",
                "Maintain typography, colour, spacing, component, imagery and responsive coherence.",
                ["website/"],
            ),
            (
                "technical-editor",
                "Technical Editorial Writer",
                "Make proposition, research, products and buyer journeys clear in precise en-GB prose.",
                ["website/"],
            ),
            (
                "claims-editor",
                "Claims and Evidence Editor",
                "Bind material public statements to current source state and permitted wording.",
                ["website/", "data/website_operator/"],
            ),
            (
                "stakeholder-insight-editor",
                "Stakeholder Insight & Privacy Editor",
                "Translate current stakeholder questions into code-only route and claim signals, then require response closure without exposing correspondence or identity.",
                [
                    "data/website_operator/",
                    "docs/research/",
                    "artifacts/website-operator/",
                ],
            ),
            (
                "motion-engineer",
                "Motion Designer",
                "Use purposeful restrained motion with keyboard and reduced-motion parity.",
                ["website/"],
            ),
            (
                "visual-asset-director",
                "Visual Asset Director",
                "Commission or create source-cleared graphics with explicit asset and performance budgets.",
                ["website/"],
            ),
            (
                "accessibility-performance-qa",
                "Accessibility and Performance QA",
                "Run responsive, keyboard, reduced-motion, contrast, browser and performance checks.",
                ["website/", "tools/", "docs/audits/"],
            ),
            (
                "design-release-qa",
                "Design Release QA",
                "Prove dependency closure, package integrity, backup readiness and live read-back.",
                ["website/", "tools/", "docs/audits/", "artifacts/website-operator/"],
            ),
        ]
        council: List[Dict[str, Any]] = []
        for role_id, title, mission, allowed_scope in role_contracts:
            relevant_findings = [
                finding
                for finding in findings
                if (
                    role_id == "claims-editor"
                    and str(finding.get("code") or "").startswith(("claims.", "ethos."))
                )
                or (
                    role_id == "accessibility-performance-qa"
                    and str(finding.get("code") or "").startswith(
                        ("accessibility.", "motion.", "budget.", "external.")
                    )
                )
                or (role_id == "design-release-qa" and finding.get("severity") == "error")
            ]
            feedback_veto = (
                role_id == "stakeholder-insight-editor"
                and stakeholder_feedback_evidence.get("passed") is not True
            )
            copy_veto = (
                role_id in {"technical-editor", "claims-editor", "design-release-qa"}
                and investor_copy_evidence.get("passed") is not True
            )
            evidence_veto = feedback_veto or copy_veto
            finding_codes = [str(item.get("code") or "") for item in relevant_findings]
            if feedback_veto:
                finding_codes.append("hard-gate.stakeholder_feedback_current")
            if copy_veto:
                finding_codes.append("hard-gate.investor_copy_quality_current")
            council.append(
                {
                    "role_id": role_id,
                    "title": title,
                    "mission": mission,
                    "allowed_scope": allowed_scope,
                    "authority": "local-analysis-and-staged-candidate-change-only",
                    "write_boundary": (
                        "Any implementation needs a separate reconciled v4 exact-path candidate work order "
                        "and may write only below artifacts/website-candidates."
                    ),
                    "veto": any(item.get("severity") == "error" for item in relevant_findings)
                    or evidence_veto,
                    "finding_codes": finding_codes,
                }
            )

        iteration = int(previous.get("iteration", 0) or 0) + 1 if previous else 1
        score_delta = round(weighted_score - previous_score, 2) if previous_score is not None else None
        previous_stop_control = (
            previous.get("stop_control", {})
            if previous and isinstance(previous.get("stop_control"), dict)
            else {}
        )
        previous_no_progress = int(previous_stop_control.get("consecutive_no_progress_iterations", 0) or 0)
        consecutive_no_progress = (
            previous_no_progress + 1
            if previous is not None and score_delta is not None and score_delta <= 0
            else 0
        )
        blocker_identity_set = {
            (
                f"hard-gate.{str(gate.get('id') or '')}",
                _sha256_json(gate.get("evidence")),
            )
            for gate in hard_gates
            if gate.get("passed") is not True
        }
        blocker_identity_set.update(
            {
                (
                    str(finding.get("code") or ""),
                    str(finding.get("path") or ""),
                )
                for finding in findings
                if finding.get("severity") == "error"
            }
        )
        blocker_identity = sorted(blocker_identity_set)
        blocker_signature = _sha256_json(blocker_identity) if blocker_identity else None
        previous_blocker_signature = previous_stop_control.get("blocker_signature")
        if previous and not previous_blocker_signature:
            previous_findings = previous.get("audit", {}).get("findings", [])
            previous_blocker_set = {
                (
                    f"hard-gate.{str(gate.get('id') or '')}",
                    _sha256_json(gate.get("evidence")),
                )
                for gate in previous.get("hard_gates", [])
                if isinstance(gate, dict) and gate.get("passed") is not True
            }
            previous_blocker_set.update(
                {
                    (
                        str(finding.get("code") or ""),
                        str(finding.get("path") or ""),
                    )
                    for finding in previous_findings
                    if isinstance(finding, dict) and finding.get("severity") == "error"
                }
            )
            previous_blockers = sorted(previous_blocker_set)
            previous_blocker_signature = _sha256_json(previous_blockers) if previous_blockers else None
        repeated_identical_blocker = bool(
            blocker_signature and blocker_signature == previous_blocker_signature
        )
        blocker_codes = {code for code, _ in blocker_identity}
        missing_claim_evidence = any(
            code.startswith("claims.") or code == "hard-gate.claims_evidence_current"
            for code in blocker_codes
        )
        critical_veto_prefixes = (
            "security.",
            "accessibility.",
            "package.",
            "authority.",
        )
        critical_veto_codes = sorted(
            code for code in blocker_codes if code.startswith(critical_veto_prefixes)
        )
        triggered_stop_conditions: List[str] = []
        if iteration > 5:
            triggered_stop_conditions.append("maximum_iterations_exceeded")
        if consecutive_no_progress >= 2:
            triggered_stop_conditions.append("two_consecutive_no_progress_iterations")
        if repeated_identical_blocker:
            triggered_stop_conditions.append("repeated_identical_blocker")
        if missing_claim_evidence:
            triggered_stop_conditions.append("missing_claim_evidence")
        if critical_veto_codes:
            triggered_stop_conditions.append("critical_veto")
        if previous_stop_control.get("continuation_allowed") is False:
            triggered_stop_conditions.append("previous_cycle_stopped")
        triggered_stop_conditions = list(dict.fromkeys(triggered_stop_conditions))
        stop_enforced = bool(triggered_stop_conditions)
        hard_gates_pass = objective_hard_gates_pass and not stop_enforced

        tasks: List[Dict[str, Any]] = []
        for index, finding in enumerate(findings, start=1):
            if finding.get("severity") not in {"error", "warning"}:
                continue
            code = str(finding.get("code") or "")
            owner = (
                "claims-editor"
                if code.startswith(("claims.", "ethos."))
                else "accessibility-performance-qa"
                if code.startswith(("accessibility.", "motion.", "budget.", "external."))
                else "brand-system-lead"
            )
            tasks.append(
                {
                    "id": f"DESIGN-{index:03d}",
                    "owner": owner,
                    "finding": finding,
                    "allowed_scope": [
                        "artifacts/website-candidates/<run-id>/website/<exact paths declared by v4 work order>"
                    ],
                    "candidate_work_order_required": True,
                    "acceptance": [
                        "Close the exact finding under the unchanged test policy.",
                        "Create a source-bound v4 work order with an exact file allow-list before staging any implementation.",
                        "For binary paths, run the trusted runner-only editorial importer before giving the text worker a lease.",
                        "Validate the staged diff, structural editorial surface binding, remote-origin policy and claim-impact declarations.",
                        "Rerun the failing check, then the full website audit.",
                        "Record before/after source hashes and preserve unrelated dirty state.",
                    ],
                }
            )
        copy_routes = copy_receipt.get("routes") if isinstance(copy_receipt, Mapping) else []
        if isinstance(copy_routes, list):
            for index, route in enumerate(copy_routes, start=1):
                if not isinstance(route, Mapping) or int(route.get("blocker_count", 0) or 0) < 1:
                    continue
                tasks.append(
                    {
                        "id": f"DESIGN-COPY-{index:03d}",
                        "owner": "technical-editor",
                        "title": "Remove investor-copy policy blockers from one bounded route",
                        "finding": {
                            "code": "copy.investor-quality",
                            "severity": "error",
                            "path": route.get("path"),
                            "route": route.get("route"),
                            "blocker_count": route.get("blocker_count"),
                            "warning_count": route.get("warning_count"),
                        },
                        "allowed_scope": [
                            "artifacts/website-candidates/<run-id>/website/<exact paths declared by v4 work order>"
                        ],
                        "candidate_work_order_required": True,
                        "acceptance": [
                            "Remove static traction, research, operating, finance and snapshot figures prohibited by the current policy.",
                            "Retain only claim-bound durable evidence categories and explicit interpretation boundaries.",
                            "Rerun the investor-copy audit against the exact staged candidate with zero blockers and warnings.",
                            "Preserve the source, policy, route and candidate hashes in the staged validation receipt.",
                        ],
                    }
                )
        if not tasks:
            tasks = [
                {
                    "id": "DESIGN-CONTINUOUS-001",
                    "owner": "design-director",
                    "title": "Benchmark-led continuous improvement candidate",
                    "allowed_scope": [
                        "artifacts/website-candidates/<run-id>/website/<exact paths declared by v4 work order>"
                    ],
                    "candidate_work_order_required": True,
                    "acceptance": [
                        "Target a named evidence-backed design opportunity.",
                        "Create and validate an exact-path staged candidate before any canonical promotion.",
                        "Pass the complete design council with no hard-gate regression.",
                        "Require human visual acceptance before baseline promotion.",
                    ],
                }
            ]

        run_id = uuid.uuid4().hex
        if stop_enforced:
            state = "stopped"
        elif not run_external:
            state = "diagnostic-only-external-checks-skipped"
        elif hard_gates_pass:
            state = "verified-local-human-review-required"
        else:
            state = "needs-repair"
        receipt = self._base_receipt("design-cycle")
        receipt.update(
            {
                "schema": DESIGN_CYCLE_SCHEMA,
                "run_id": run_id,
                "parent_run_id": previous.get("run_id") if previous else None,
                "iteration": iteration,
                "state": state,
                "goal": objective,
                "source_tree_sha256": audit.get("source_tree_sha256"),
                "test_policy_sha256": self.config_sha256,
                "routes": safe_routes,
                "competitor_research": benchmark,
                "evidence_controls": evidence_controls,
                "design_nexus": {
                    "kind": "operational-evidence-coherence-score",
                    "score": weighted_score,
                    "minimum_score": minimum_score,
                    "dimensions": dimensions,
                    "weights": weights,
                    "phase_spread": spread,
                    "coherence": coherence,
                    "previous_score": previous_score,
                    "score_delta": score_delta,
                    "claim_boundary": (
                        "This adapts a Harmonic Nexus weighted feedback pattern for design "
                        "operations. It is not scientific validation or automated aesthetic truth."
                    ),
                },
                "hard_gates": hard_gates,
                "hard_gates_pass": hard_gates_pass,
                "release_eligible": hard_gates_pass,
                "audit": audit,
                "external_checks": audit.get("external_checks"),
                "inventory": {
                    "file_count": inventory["file_count"],
                    "total_bytes": inventory["total_bytes"],
                    "html_page_count": inventory["html_page_count"],
                    "tree_sha256": inventory["tree_sha256"],
                },
                "design_council": council,
                "work_orders": tasks,
                "candidate_control": {
                    "schema": WORK_ORDER_SCHEMA,
                    "enforcement": "required for autonomous V30+ implementation candidates",
                    "staging_root": "artifacts/website-candidates/<run-id>/website",
                    "canonical_website_mutation": "not authorised by design cycle or design agents",
                    "required_proof": [
                        "current live-surface reconciliation receipt",
                        "owner source decision plus verified backup when live drift exists",
                        "exact file allow-list",
                        "baseline tree manifest",
                        "per-file before/after hashes",
                        "claim-impact declaration",
                        "current privacy-safe stakeholder signal binding and complete response manifest",
                        "runner-only trusted WebP import receipt for every binary delta",
                        "unique structural route, link, variant, alt, caption and credit binding for every editorial surface",
                        "zero binary read, write or import authority for text workers",
                        "remote-origin diff",
                        "secret scan",
                    ],
                    "release_eligible": False,
                    "deployment_authority": "none",
                },
                "feedback_loop": [
                    "sense: bind source, evidence, benchmark, current website hashes and public live-surface drift",
                    "orient: map routes, claims, privacy-safe stakeholder signals, tokens, components, assets and buyer journeys",
                    "branch: create bounded deterministic candidates only from a reconciled source baseline",
                    "compose: stage an exact-path candidate, import rights-bound WebP bytes through the runner, and give text workers zero binary authority",
                    "prove: replay importer bytes and structural editorial surfaces, then rerun exact failure and the full browser/a11y/performance/claims suite",
                    "challenge: let any objective critic veto a regression or unsupported claim",
                    "retain-or-revert: preserve receipts and keep only the passing candidate",
                    "package: require exact runtime dependency closure",
                    "release: backup, exact-hash owner gate, deploy, live read-back",
                    "learn: promote accepted patterns as versioned reusable design skills",
                ],
                "stop_control": {
                    "enforced": True,
                    "continuation_allowed": not stop_enforced,
                    "triggered": triggered_stop_conditions,
                    "maximum_iterations": 5,
                    "consecutive_no_progress_iterations": consecutive_no_progress,
                    "blocker_signature": blocker_signature,
                    "repeated_identical_blocker": repeated_identical_blocker,
                    "missing_claim_evidence": missing_claim_evidence,
                    "critical_veto_codes": critical_veto_codes,
                },
                "skill_hierarchy": {
                    "L0_atomic": [
                        "inventory_site",
                        "observe_live_surface",
                        "bind_owner_source_reconciliation",
                        "validate_owner_source_reconciliation",
                        "read_claim_register",
                        "audit_stakeholder_feedback",
                        "prepare_editorial_asset_rights_decisions",
                        "bind_route_feedback_capsules",
                        "validate_feedback_response_manifest",
                        "preflight_investor_copy_repair_contract",
                        "preflight_investor_copy_repair_work_order",
                        "verify_investor_copy_repair_contract",
                        "evaluate_investor_copy_repair_candidate",
                        "verify_investor_copy_governance_decision",
                        "simulate_investor_copy_governance_application",
                        "apply_exact_owner_approved_investor_copy_governance_delta",
                        "create_reconciled_source_bound_work_order",
                        "stage_candidate_tree",
                        "import_rights_bound_editorial_webp",
                        "validate_candidate_diff",
                        "revalidate_candidate_provenance",
                        "verify_editorial_surface_binding",
                        "capture_route",
                        "run_accessibility",
                        "run_performance",
                        "diff_screenshot",
                        "validate_motion",
                        "verify_dependency_closure",
                    ],
                    "L1_compound": [
                        "benchmark_competitor",
                        "audit_route",
                        "audit_design_system",
                        "audit_copy_and_claims",
                        "translate_stakeholder_signals",
                        "draft_variant",
                    ],
                    "L2_task": [
                        "redesign_route",
                        "motion_pass",
                        "copy_evidence_pass",
                        "repair_finding",
                    ],
                    "L3_workflow": [
                        "public_site_design_cycle",
                        "staged_candidate_change_control",
                        "website_release_preflight",
                    ],
                    "L4_role": [item[1] for item in role_contracts],
                },
                "authority_boundaries": {
                    "local_mutation": "staged candidate only; canonical website promotion is separately owner-controlled",
                    "candidate_staging": "artifacts/website-candidates/<run-id>/website only",
                    "credential_access": "none",
                    "deployment": "none",
                    "owner_source_selection": (
                        "validate and bind only an existing explicit owner v1 retained-local "
                        "or v2 verified-live-backup decision; never choose autonomously"
                    ),
                    "editorial_rights_decision": (
                        "prepare evidence only from an exact decision already supplied by "
                        "the controlled named human; never make or infer the decision"
                    ),
                    "investor_copy_repair": (
                        "exact task, selected-source and work-order preflight plus bounded "
                        "contract replay and candidate re-audit only; no source selection, "
                        "canonical mutation, package, release or deployment authority"
                    ),
                    "investor_copy_governance": (
                        "verification and full shadow simulation are read-only; broad system "
                        "access is not approval, and exact three-file application remains "
                        "blocked without a fresh immutable named-owner decision plus explicit "
                        "apply; no website, policy, candidate, package, release or deployment "
                        "authority"
                    ),
                    "production_publication": (
                        "WebsiteOperator backup plus short-lived package-hash owner gate only"
                    ),
                    "human_visual_acceptance_required": True,
                    "autonomous_threshold_changes": False,
                },
                "deployment_state": "not-authorised-not-attempted",
                "summary": {
                    "blocker_count": blocker_count,
                    "warning_count": warning_count,
                    "work_order_count": len(tasks),
                    "council_veto_count": sum(1 for item in council if item["veto"]),
                    "hard_gate_count": len(hard_gates),
                    "hard_gate_pass_count": sum(1 for gate in hard_gates if gate["passed"]),
                    "ready_for_human_visual_review": hard_gates_pass,
                    "release_eligible": hard_gates_pass,
                    "ready_for_deployment": False,
                },
            }
        )
        return receipt

    def design_cycle(
        self,
        goal: str,
        output: Path | None = None,
        routes: Sequence[str] | None = None,
        run_external: bool = True,
        previous_cycle: Path | None = None,
    ) -> Path:
        payload = self.design_cycle_payload(
            goal=goal,
            routes=routes,
            run_external=run_external,
            previous_cycle=previous_cycle,
        )
        return _atomic_write_json(self._path_for_output("design-cycle", output), payload)

    def _require_receipt(self, receipt: Mapping[str, Any], kind: str) -> None:
        expected = f"{SCHEMA_PREFIX}.{kind}.v1"
        if receipt.get("schema") != expected:
            raise WebsiteOperatorError(f"Expected {expected}; observed {receipt.get('schema')!r}.")
        if receipt.get("config_sha256") != self.config_sha256:
            raise WebsiteOperatorError(f"{kind} receipt was produced under a different operator config.")

    def _expand_command(
        self,
        command: object,
        values: Mapping[str, str],
    ) -> List[str]:
        if not isinstance(command, list) or not all(isinstance(item, str) for item in command):
            raise WebsiteOperatorError("Configured command must be an array of strings.")
        base = {
            "repo_root": str(self.repo_root),
            "site_root": str(self.site_root),
            **values,
        }
        return [item.format(**base) for item in command]

    def _manifest_rows(self, manifest_path: Path) -> List[Dict[str, Any]]:
        with manifest_path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if tuple(reader.fieldnames or ()) != ("Path", "Bytes", "Sha256"):
                raise WebsiteOperatorError("Release manifest does not use the V3 Path,Bytes,Sha256 columns.")
            rows = list(reader)
        if not rows:
            raise WebsiteOperatorError("Release manifest is empty.")
        result = []
        seen = set()
        seen_casefold = set()
        for row in rows:
            raw_relative = str(row.get("Path", ""))
            relative = _safe_relative_path(raw_relative)
            if raw_relative != relative:
                raise WebsiteOperatorError(f"Non-canonical release manifest path: {raw_relative}")
            if relative in seen:
                raise WebsiteOperatorError(f"Duplicate release manifest path: {relative}")
            if relative.casefold() in seen_casefold:
                raise WebsiteOperatorError(f"Case-colliding release manifest path: {relative}")
            seen.add(relative)
            seen_casefold.add(relative.casefold())
            try:
                size = int(row.get("Bytes", ""))
            except (TypeError, ValueError) as exc:
                raise WebsiteOperatorError(f"Invalid byte count in manifest for {relative}.") from exc
            if size < 0:
                raise WebsiteOperatorError(f"Invalid byte count in manifest for {relative}.")
            sha = str(row.get("Sha256", "")).upper()
            if not re.fullmatch(r"[A-F0-9]{64}", sha):
                raise WebsiteOperatorError(f"Invalid SHA-256 in manifest for {relative}.")
            result.append({"path": relative, "bytes": size, "sha256": sha})
        return result

    def _dependency_manifest_summary(
        self,
        dependency_manifest_path: Path,
        manifest_paths: set[str],
    ) -> Dict[str, int]:
        required_fields = (
            "Source",
            "Reference",
            "Disposition",
            "Target",
            "Fragment",
            "FragmentState",
        )
        with dependency_manifest_path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if tuple(reader.fieldnames or ()) != required_fields:
                raise WebsiteOperatorError(
                    "Dependency manifest does not use the V3 closure evidence columns."
                )
            rows = list(reader)

        counts: Counter[str] = Counter()
        seen: set[tuple[str, ...]] = set()
        verified_fragments = 0
        for index, row in enumerate(rows, start=2):
            raw_source = str(row.get("Source", ""))
            source = _safe_relative_path(raw_source)
            if raw_source != source:
                raise WebsiteOperatorError(f"Non-canonical dependency source at row {index}: {raw_source}")
            if source not in manifest_paths:
                raise WebsiteOperatorError(
                    f"Dependency manifest source is outside the package at row {index}: {source}"
                )
            reference = str(row.get("Reference", "")).strip()
            disposition = str(row.get("Disposition", "")).strip()
            target = str(row.get("Target", "")).strip()
            fragment = str(row.get("Fragment", "")).strip()
            fragment_state = str(row.get("FragmentState", "")).strip()
            if not reference or disposition not in {"local-included", "remote", "non-file"}:
                raise WebsiteOperatorError(f"Invalid dependency evidence at row {index}.")
            key = (source, reference, disposition, target, fragment, fragment_state)
            if key in seen:
                raise WebsiteOperatorError(f"Duplicate dependency evidence at row {index}.")
            seen.add(key)
            counts[disposition] += 1

            if disposition == "local-included":
                local_target = _safe_relative_path(target)
                if target != local_target:
                    raise WebsiteOperatorError(f"Non-canonical dependency target at row {index}: {target}")
                if local_target not in manifest_paths:
                    raise WebsiteOperatorError(
                        "Dependency manifest proves a local runtime target that is absent "
                        f"from the package: {local_target}"
                    )
                expected_fragment_state = "verified" if fragment else "not-applicable"
                if fragment_state != expected_fragment_state:
                    raise WebsiteOperatorError(f"Invalid local fragment proof at dependency row {index}.")
                if fragment:
                    verified_fragments += 1
            else:
                if not target:
                    raise WebsiteOperatorError(f"Non-local dependency has no target at row {index}.")
                if fragment or fragment_state:
                    raise WebsiteOperatorError(
                        f"Non-local dependency has invalid fragment evidence at row {index}."
                    )

        return {
            "row_count": len(rows),
            "local-included": counts["local-included"],
            "remote": counts["remote"],
            "non-file": counts["non-file"],
            "verified_fragments": verified_fragments,
        }

    def _validate_v3_dependency_closure(
        self,
        raw: Mapping[str, Any],
        rows: Sequence[Mapping[str, Any]],
        dependency_manifest_path: Path,
    ) -> Dict[str, Any]:
        if raw.get("schema") != HOMEPL_RELEASE_SCHEMA_V3:
            raise WebsiteOperatorError(
                "Package builder receipt does not prove the V3 dependency-closed release contract."
            )
        if raw.get("deployment_state") != "audited-release-prepared-not-uploaded":
            raise WebsiteOperatorError("V3 package builder receipt has an invalid deployment state.")
        if raw.get("package_root") != "/":
            raise WebsiteOperatorError("V3 package must place release files at the archive root.")
        try:
            source_root = Path(str(raw.get("source_root", ""))).resolve()
        except (OSError, RuntimeError) as exc:
            raise WebsiteOperatorError("V3 package receipt has an invalid source root.") from exc
        if source_root != self.site_root:
            raise WebsiteOperatorError("V3 package receipt is bound to another website source root.")

        manifest_paths = {str(row["path"]) for row in rows}
        manifest_rows = {str(row["path"]): (int(row["bytes"]), str(row["sha256"])) for row in rows}
        raw_files = raw.get("files")
        if not isinstance(raw_files, list) or not raw_files:
            raise WebsiteOperatorError("V3 package receipt has no exact file proof.")
        receipt_rows: Dict[str, tuple[int, str]] = {}
        receipt_paths_casefold: set[str] = set()
        for item in raw_files:
            if not isinstance(item, Mapping):
                raise WebsiteOperatorError("V3 package receipt has an invalid file proof.")
            raw_relative = str(item.get("Path", ""))
            relative = _safe_relative_path(raw_relative)
            if raw_relative != relative:
                raise WebsiteOperatorError(f"Non-canonical V3 receipt file path: {raw_relative}")
            if relative in receipt_rows:
                raise WebsiteOperatorError(f"Duplicate V3 receipt file path: {relative}")
            if relative.casefold() in receipt_paths_casefold:
                raise WebsiteOperatorError(f"Case-colliding V3 receipt file path: {relative}")
            byte_count = item.get("Bytes")
            if type(byte_count) is not int or byte_count < 0:
                raise WebsiteOperatorError(f"Invalid V3 receipt byte count for {relative}.")
            sha = str(item.get("Sha256", "")).upper()
            if not re.fullmatch(r"[A-F0-9]{64}", sha):
                raise WebsiteOperatorError(f"Invalid V3 receipt SHA-256 for {relative}.")
            receipt_rows[relative] = (byte_count, sha)
            receipt_paths_casefold.add(relative.casefold())
        if receipt_rows != manifest_rows:
            raise WebsiteOperatorError("V3 receipt file proof and release manifest differ.")

        def require_count(container: Mapping[str, Any], name: str) -> int:
            value = container.get(name)
            if type(value) is not int or value < 0:
                raise WebsiteOperatorError(f"Invalid V3 closure count: {name}")
            return value

        file_count = require_count(raw, "file_count")
        total_bytes = require_count(raw, "total_bytes")
        if file_count != len(rows) or total_bytes != sum(int(row["bytes"]) for row in rows):
            raise WebsiteOperatorError("V3 receipt file totals do not match the release manifest.")

        package_validation = raw.get("package_validation")
        if not isinstance(package_validation, Mapping):
            raise WebsiteOperatorError("V3 package validation proof is missing.")
        if package_validation.get("state") != "verified":
            raise WebsiteOperatorError("V3 package validation is not verified.")
        if require_count(package_validation, "zip_file_count") != len(rows):
            raise WebsiteOperatorError("V3 ZIP file count does not match the release manifest.")
        for field_name in (
            "manifest_paths_exact",
            "manifest_bytes_exact",
            "manifest_sha256_exact",
            "staging_dependency_closure_exact",
            "staging_fragment_targets_exact",
        ):
            if package_validation.get(field_name) is not True:
                raise WebsiteOperatorError(f"V3 package validation does not prove {field_name}.")

        closure = raw.get("dependency_closure")
        if not isinstance(closure, Mapping) or closure.get("state") != "verified-complete":
            raise WebsiteOperatorError("V3 receipt does not prove a verified-complete dependency closure.")
        closure_counts = {
            name: require_count(closure, name)
            for name in (
                "entry_file_count",
                "discovered_file_count",
                "local_reference_count",
                "included_local_reference_count",
                "missing_local_reference_count",
                "fragment_reference_count",
                "verified_fragment_reference_count",
                "missing_fragment_reference_count",
                "remote_reference_count",
                "non_file_reference_count",
            )
        }
        if closure_counts["entry_file_count"] == 0 or closure_counts["entry_file_count"] + closure_counts[
            "discovered_file_count"
        ] != len(rows):
            raise WebsiteOperatorError("V3 closure file counts do not cover the exact manifest.")
        if (
            closure_counts["missing_local_reference_count"] != 0
            or closure_counts["local_reference_count"] != closure_counts["included_local_reference_count"]
        ):
            raise WebsiteOperatorError(
                "V3 receipt does not prove exact transitive runtime dependency closure."
            )
        if (
            closure_counts["missing_fragment_reference_count"] != 0
            or closure_counts["fragment_reference_count"]
            != closure_counts["verified_fragment_reference_count"]
        ):
            raise WebsiteOperatorError("V3 receipt does not prove all local fragment targets.")

        dependency_summary = self._dependency_manifest_summary(
            dependency_manifest_path,
            manifest_paths,
        )
        expected_dependency_counts = {
            "local-included": closure_counts["included_local_reference_count"],
            "remote": closure_counts["remote_reference_count"],
            "non-file": closure_counts["non_file_reference_count"],
            "verified_fragments": closure_counts["verified_fragment_reference_count"],
        }
        for name, expected in expected_dependency_counts.items():
            if dependency_summary[name] != expected:
                raise WebsiteOperatorError(
                    f"V3 dependency manifest count does not match the closure receipt: {name}"
                )
        expected_rows = (
            closure_counts["local_reference_count"]
            + closure_counts["remote_reference_count"]
            + closure_counts["non_file_reference_count"]
        )
        if dependency_summary["row_count"] != expected_rows:
            raise WebsiteOperatorError("V3 dependency manifest does not enumerate every recorded reference.")

        return {
            "builder_schema": HOMEPL_RELEASE_SCHEMA_V3,
            "package_validation": dict(package_validation),
            "dependency_closure": dict(closure),
            "dependency_evidence_rows": dependency_summary["row_count"],
        }

    def _validate_package(self, raw_receipt_path: Path) -> Dict[str, Any]:
        raw_receipt_path = _regular_single_link_file(
            raw_receipt_path,
            label="Package builder receipt",
        )
        raw = _read_json(raw_receipt_path)
        if raw.get("schema") != HOMEPL_RELEASE_SCHEMA_V3:
            raise WebsiteOperatorError(
                "Package builder receipt does not prove the V3 dependency-closed release contract."
            )
        bound_paths: dict[str, Path] = {}
        for path_field, label in (
            ("package", "Release package"),
            ("manifest", "Release manifest"),
            ("dependency_manifest", "Release dependency manifest"),
        ):
            raw_value = raw.get(path_field)
            if not isinstance(raw_value, str) or not raw_value.strip():
                raise WebsiteOperatorError(
                    f"Package builder receipt {path_field} must be a non-empty absolute path."
                )
            candidate = Path(raw_value)
            if not candidate.is_absolute():
                raise WebsiteOperatorError(f"Package builder receipt {path_field} must be an absolute path.")
            bound_paths[path_field] = _regular_single_link_file(candidate, label=label)
        package_path = bound_paths["package"]
        manifest_path = bound_paths["manifest"]
        dependency_manifest_path = bound_paths["dependency_manifest"]
        observed_package_hash = _sha256_file(package_path)
        if observed_package_hash != str(raw.get("package_sha256", "")).upper():
            raise WebsiteOperatorError("Package hash does not match the builder receipt.")
        observed_manifest_hash = _sha256_file(manifest_path)
        if observed_manifest_hash != str(raw.get("manifest_sha256", "")).upper():
            raise WebsiteOperatorError("Manifest hash does not match the V3 builder receipt.")
        observed_dependency_manifest_hash = _sha256_file(dependency_manifest_path)
        if observed_dependency_manifest_hash != str(raw.get("dependency_manifest_sha256", "")).upper():
            raise WebsiteOperatorError("Dependency manifest hash does not match the V3 builder receipt.")
        rows = self._manifest_rows(manifest_path)
        required = {_safe_relative_path(item) for item in self.config["packaging"]["required_release_paths"]}
        required.update(HOMEPL_V3_REQUIRED_PATHS)
        paths = {row["path"] for row in rows}
        missing = sorted(required.difference(paths))
        if missing:
            raise WebsiteOperatorError(
                "Release manifest does not cover required production paths: " + ", ".join(missing)
            )
        closure_proof = self._validate_v3_dependency_closure(
            raw,
            rows,
            dependency_manifest_path,
        )
        blocked_names = {str(item).lower() for item in self.config["packaging"]["blocked_file_names"]}
        blocked_extensions = {str(item).lower() for item in self.config["packaging"]["blocked_extensions"]}
        allowed_names = {str(item).lower() for item in self.config["packaging"]["allowed_file_names"]}
        allowed_extensions = {str(item).lower() for item in self.config["packaging"]["allowed_extensions"]}
        secret_patterns = [
            re.compile(pattern, flags=re.IGNORECASE)
            for pattern in self.config["packaging"].get("secret_patterns", [])
        ]
        row_by_path = {row["path"]: row for row in rows}
        for row in rows:
            source = self.site_root / row["path"]
            if not source.is_file():
                raise WebsiteOperatorError(f"Release source file is missing: {row['path']}")
            if source.name.lower() in blocked_names or source.suffix.lower() in blocked_extensions:
                raise WebsiteOperatorError(f"Blocked file selected for release: {row['path']}")
            if source.name.lower() not in allowed_names and source.suffix.lower() not in allowed_extensions:
                raise WebsiteOperatorError(f"Unapproved public file type selected: {row['path']}")
            if source.stat().st_size != row["bytes"] or _sha256_file(source) != row["sha256"]:
                raise WebsiteOperatorError(f"Release manifest is stale or incorrect: {row['path']}")
            if source.suffix.lower() in TEXT_EXTENSIONS or source.name.lower() in allowed_names:
                text = source.read_text(encoding="utf-8-sig", errors="replace")
                if any(pattern.search(text) for pattern in secret_patterns):
                    raise WebsiteOperatorError(
                        f"Potential credential literal selected for release: {row['path']}"
                    )
        with zipfile.ZipFile(package_path, "r") as archive:
            archive_paths = set()
            archive_paths_casefold = set()
            for info in archive.infolist():
                if info.is_dir():
                    continue
                archive_name = info.filename.replace("\\", "/")
                relative = _safe_relative_path(archive_name)
                if archive_name != relative:
                    raise WebsiteOperatorError(f"Non-canonical archive path: {info.filename}")
                if relative in archive_paths or relative.casefold() in archive_paths_casefold:
                    raise WebsiteOperatorError(f"Duplicate or case-colliding archive path: {relative}")
                archive_paths.add(relative)
                archive_paths_casefold.add(relative.casefold())
                if relative not in row_by_path:
                    raise WebsiteOperatorError(f"Archive contains an unmanifested file: {relative}")
                data = archive.read(info)
                expected = row_by_path[relative]
                if len(data) != expected["bytes"] or _sha256_bytes(data) != expected["sha256"]:
                    raise WebsiteOperatorError(f"Archive content mismatch: {relative}")
            if archive_paths != paths:
                raise WebsiteOperatorError("Archive and manifest file sets differ.")
        return {
            "raw_receipt": str(raw_receipt_path),
            "raw_receipt_sha256": _sha256_file(raw_receipt_path),
            "package": str(package_path),
            "package_sha256": observed_package_hash,
            "package_bytes": package_path.stat().st_size,
            "manifest": str(manifest_path),
            "manifest_sha256": observed_manifest_hash,
            "dependency_manifest": str(dependency_manifest_path),
            "dependency_manifest_sha256": observed_dependency_manifest_hash,
            "file_count": len(rows),
            "total_uncompressed_bytes": sum(row["bytes"] for row in rows),
            "paths": sorted(paths),
            **closure_proof,
        }

    def _require_composite_external_evidence(
        self,
        external_checks: object,
        current_tree: str,
        label: str,
    ) -> Dict[str, Any]:
        if (
            not isinstance(external_checks, dict)
            or external_checks.get("complete") is not True
            or external_checks.get("required_composite_check_id") != COMPOSITE_VISUAL_GATE_CHECK_ID
        ):
            raise WebsiteOperatorError(f"{label} does not prove a complete canonical composite visual gate.")
        results = external_checks.get("results")
        if not isinstance(results, list):
            raise WebsiteOperatorError(f"{label} has no external-check result records.")
        matches = [
            record
            for record in results
            if isinstance(record, dict) and record.get("id") == COMPOSITE_VISUAL_GATE_CHECK_ID
        ]
        if len(matches) != 1:
            raise WebsiteOperatorError(f"{label} must contain exactly one composite visual gate result.")
        record = matches[0]
        stdout_json = record.get("stdout_json")
        if (
            record.get("required") is not True
            or record.get("returncode") != 0
            or record.get("state") != "pass"
            or record.get("current_source_tree_sha256") != current_tree
            or not isinstance(stdout_json, Mapping)
            or not self._is_zero_blocker_pass(stdout_json)
        ):
            raise WebsiteOperatorError(
                f"{label} composite visual gate result is not a source-bound zero-blocker PASS."
            )
        binding = record.get("composite_gate")
        expected_keys = {
            "check_id",
            "release_id",
            "operator_source_tree_sha256",
            "visual_source_tree_sha256",
            "manifest",
            "visual_receipt",
            "manual_pixel_review_receipt",
        }
        if not isinstance(binding, dict) or set(binding) != expected_keys:
            raise WebsiteOperatorError(f"{label} composite visual gate binding is malformed.")
        if (
            binding.get("check_id") != COMPOSITE_VISUAL_GATE_CHECK_ID
            or binding.get("operator_source_tree_sha256") != current_tree
            or stdout_json.get("sourceTreeSha256") != binding.get("visual_source_tree_sha256")
            or not str(binding.get("release_id") or "").strip()
            or not re.fullmatch(
                r"[a-f0-9]{64}",
                str(binding.get("visual_source_tree_sha256") or ""),
            )
        ):
            raise WebsiteOperatorError(f"{label} composite visual gate binding is inconsistent.")
        for name in ("manifest", "visual_receipt", "manual_pixel_review_receipt"):
            reference = binding.get(name)
            if (
                not isinstance(reference, dict)
                or set(reference) != {"path", "sha256"}
                or not str(reference.get("path") or "").startswith("docs/audits/")
                or not re.fullmatch(r"[A-F0-9]{64}", str(reference.get("sha256") or ""))
            ):
                raise WebsiteOperatorError(f"{label} composite visual gate {name} reference is malformed.")
        return dict(binding)

    @staticmethod
    def _same_composite_binding(
        left: Mapping[str, Any],
        right: Mapping[str, Any],
    ) -> bool:
        return json.dumps(
            dict(left),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ) == json.dumps(
            dict(right),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    def _rerun_composite_gate(
        self,
        current_tree: str,
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        check = self._composite_gate_check()
        if check is None:
            raise WebsiteOperatorError("The canonical composite visual release gate is not configured.")
        record, findings = self._run_external_check(check, current_tree)
        if findings:
            diagnostic = "; ".join(finding.message for finding in findings)
            raise WebsiteOperatorError(f"Composite visual gate revalidation failed: {diagnostic}")
        external = {
            "complete": True,
            "required_composite_check_id": COMPOSITE_VISUAL_GATE_CHECK_ID,
            "results": [record],
        }
        binding = self._require_composite_external_evidence(
            external,
            current_tree,
            "Current composite visual gate",
        )
        return record, binding

    def _validate_design_evidence_controls_for_release(
        self,
        design: Mapping[str, Any],
    ) -> None:
        """Re-run and bind the local design-evidence inputs before packaging.

        A design receipt can be syntactically intact while a claim register,
        benchmark timestamp or bound operator config has changed afterwards.
        Re-evaluating every local control closes that gap without assigning
        release authority to any control.
        """
        stored_controls = design.get("evidence_controls")
        if not isinstance(stored_controls, Mapping):
            raise WebsiteOperatorError(
                "Design-cycle receipt lacks current benchmark, public-claim, research-refresh or stakeholder-feedback evidence controls."
            )
        stored_benchmark = stored_controls.get("benchmark")
        stored_claims = stored_controls.get("public_claims")
        stored_copy = stored_controls.get("investor_copy")
        stored_refresh = stored_controls.get("research_refresh")
        stored_feedback = stored_controls.get("stakeholder_feedback")
        stored_editorial = stored_controls.get("editorial_assets")
        if (
            not isinstance(stored_benchmark, Mapping)
            or not isinstance(stored_claims, Mapping)
            or not isinstance(stored_copy, Mapping)
            or not isinstance(stored_refresh, Mapping)
            or not isinstance(stored_feedback, Mapping)
            or not isinstance(stored_editorial, Mapping)
            or stored_benchmark.get("passed") is not True
            or stored_claims.get("passed") is not True
            or stored_copy.get("passed") is not True
            or stored_refresh.get("passed") is not True
            or stored_feedback.get("passed") is not True
            or stored_editorial.get("passed") is not True
        ):
            raise WebsiteOperatorError(
                "Design-cycle benchmark, public-claim, investor-copy, research-refresh, "
                "stakeholder-feedback or editorial-asset evidence controls are not passing."
            )

        stored_copy_binding = stored_copy.get("binding")
        if (
            not isinstance(stored_copy_binding, Mapping)
            or stored_copy_binding.get("blocker_count") != 0
            or stored_copy_binding.get("warning_count") != 0
            or stored_copy_binding.get("state") != "pass"
        ):
            raise WebsiteOperatorError(
                "Stored investor-copy evidence must bind exactly zero blockers and warnings."
            )
        raw_hard_gates = design.get("hard_gates")
        copy_hard_gates = (
            [
                gate
                for gate in raw_hard_gates
                if isinstance(gate, Mapping) and gate.get("id") == "investor_copy_quality_current"
            ]
            if isinstance(raw_hard_gates, list)
            else []
        )
        expected_copy_gate_evidence = self._design_evidence_gate_summary(stored_copy)
        if (
            len(copy_hard_gates) != 1
            or set(copy_hard_gates[0]) != {"id", "passed", "evidence"}
            or copy_hard_gates[0].get("passed") is not True
            or copy_hard_gates[0].get("evidence") != expected_copy_gate_evidence
        ):
            raise WebsiteOperatorError(
                "Design-cycle receipt must contain exactly one passing, control-bound "
                "investor-copy quality hard gate."
            )

        current_controls = self._design_evidence_controls()
        current_benchmark = current_controls["benchmark"]
        current_claims = current_controls["public_claims"]
        current_copy = current_controls["investor_copy"]
        current_refresh = current_controls["research_refresh"]
        current_feedback = current_controls["stakeholder_feedback"]
        current_editorial = current_controls["editorial_assets"]
        if current_benchmark.get("passed") is not True:
            raise WebsiteOperatorError(
                "Current benchmark evidence no longer passes source, freshness or no-copy verification."
            )
        if current_claims.get("passed") is not True:
            raise WebsiteOperatorError(
                "Current public-claim evidence no longer passes source-bound verification."
            )
        if current_copy.get("passed") is not True:
            raise WebsiteOperatorError(
                "Current investor-copy quality no longer passes the bounded source and policy audit."
            )
        if current_refresh.get("passed") is not True:
            raise WebsiteOperatorError(
                "Current design research refresh evidence no longer passes local source-bound verification."
            )
        stored_snapshot = stored_benchmark.get("snapshot")
        current_snapshot = current_benchmark.get("snapshot")
        stored_config = stored_snapshot.get("config") if isinstance(stored_snapshot, Mapping) else None
        current_config = current_snapshot.get("config") if isinstance(current_snapshot, Mapping) else None
        if not isinstance(stored_config, Mapping) or stored_config != current_config:
            raise WebsiteOperatorError(
                "Benchmark evidence config binding changed after the design cycle; run a fresh cycle."
            )

        stored_receipt = stored_claims.get("receipt")
        current_receipt = current_claims.get("receipt")
        stored_register = stored_receipt.get("register") if isinstance(stored_receipt, Mapping) else None
        current_register = current_receipt.get("register") if isinstance(current_receipt, Mapping) else None
        if not isinstance(stored_register, Mapping) or stored_register != current_register:
            raise WebsiteOperatorError(
                "Public-claim evidence register changed after the design cycle; run a fresh cycle."
            )
        current_copy_binding = current_copy.get("binding")
        if (
            not isinstance(stored_copy_binding, Mapping)
            or not isinstance(current_copy_binding, Mapping)
            or stored_copy_binding != current_copy_binding
        ):
            raise WebsiteOperatorError(
                "Investor-copy policy, bounded route or finding binding changed after "
                "the design cycle; run a fresh cycle."
            )
        if (
            current_copy_binding.get("blocker_count") != 0
            or current_copy_binding.get("warning_count") != 0
            or current_copy_binding.get("state") != "pass"
        ):
            raise WebsiteOperatorError(
                "Current investor-copy evidence must bind exactly zero blockers and warnings."
            )
        if current_feedback.get("passed") is not True:
            raise WebsiteOperatorError(
                "Current stakeholder feedback no longer passes privacy-safe source-bound verification."
            )
        if current_editorial.get("passed") is not True:
            raise WebsiteOperatorError(
                "Current editorial asset provenance no longer closes rights, bytes, semantic placement and public copy."
            )

        stored_refresh_receipt = stored_refresh.get("receipt")
        current_refresh_receipt = current_refresh.get("receipt")
        stored_declaration = (
            stored_refresh_receipt.get("declaration") if isinstance(stored_refresh_receipt, Mapping) else None
        )
        current_declaration = (
            current_refresh_receipt.get("declaration")
            if isinstance(current_refresh_receipt, Mapping)
            else None
        )
        if not isinstance(stored_declaration, Mapping) or stored_declaration != current_declaration:
            raise WebsiteOperatorError(
                "Design research source declaration changed after the design cycle; run a fresh cycle."
            )

        stored_feedback_receipt = stored_feedback.get("receipt")
        current_feedback_receipt = current_feedback.get("receipt")
        stored_feedback_binding = (
            stored_feedback_receipt.get("feedback") if isinstance(stored_feedback_receipt, Mapping) else None
        )
        current_feedback_binding = (
            current_feedback_receipt.get("feedback")
            if isinstance(current_feedback_receipt, Mapping)
            else None
        )
        stored_feedback_capsules_sha256 = (
            stored_feedback_receipt.get("signal_capsules_sha256")
            if isinstance(stored_feedback_receipt, Mapping)
            else None
        )
        current_feedback_capsules_sha256 = (
            current_feedback_receipt.get("signal_capsules_sha256")
            if isinstance(current_feedback_receipt, Mapping)
            else None
        )
        if (
            not isinstance(stored_feedback_binding, Mapping)
            or stored_feedback_binding != current_feedback_binding
            or not isinstance(stored_feedback_capsules_sha256, str)
            or stored_feedback_capsules_sha256 != current_feedback_capsules_sha256
        ):
            raise WebsiteOperatorError(
                "Stakeholder feedback or its controlled signal capsules changed after the design cycle; run a fresh cycle."
            )

        stored_editorial_binding = stored_editorial.get("binding")
        current_editorial_binding = current_editorial.get("binding")
        if (
            not isinstance(stored_editorial_binding, Mapping)
            or not isinstance(current_editorial_binding, Mapping)
            or stored_editorial_binding != current_editorial_binding
        ):
            raise WebsiteOperatorError(
                "Editorial asset provenance, rights, surface or public-file binding changed after the design cycle; run a fresh cycle."
            )

    def _validate_design_cycle_for_release(
        self,
        path: Path,
        current_tree: str,
    ) -> Dict[str, Any]:
        design = _read_json(path)
        if design.get("schema") != DESIGN_CYCLE_SCHEMA:
            raise WebsiteOperatorError("A release build requires a supported design-cycle receipt.")
        if design.get("config_sha256") != self.config_sha256:
            raise WebsiteOperatorError("Design-cycle receipt was produced under a different operator config.")
        if design.get("test_policy_sha256") != self.config_sha256:
            raise WebsiteOperatorError("Design-cycle receipt is not bound to the current test policy.")
        if (
            design.get("state") != "verified-local-human-review-required"
            or design.get("hard_gates_pass") is not True
            or design.get("release_eligible") is not True
        ):
            raise WebsiteOperatorError("Design-cycle receipt is not passing and release-eligible.")
        if design.get("source_tree_sha256") != current_tree:
            raise WebsiteOperatorError(
                "Website changed after the design cycle; run a fresh full design cycle."
            )
        self._validate_design_evidence_controls_for_release(design)
        summary = design.get("summary", {})
        if (
            not isinstance(summary, dict)
            or int(summary.get("blocker_count", 1)) != 0
            or int(summary.get("warning_count", 1)) != 0
        ):
            raise WebsiteOperatorError("Open design-cycle findings prevent release packaging.")
        audit_summary = design.get("audit", {}).get("summary", {})
        if not isinstance(audit_summary, dict) or audit_summary.get("external_checks_run") is not True:
            raise WebsiteOperatorError(
                "Design-cycle receipt does not prove the complete external audit suite."
            )
        embedded_external = design.get("audit", {}).get("external_checks")
        design_external = design.get("external_checks")
        if design_external != embedded_external:
            raise WebsiteOperatorError("Design-cycle external evidence differs from its embedded audit.")
        self._require_composite_external_evidence(
            design_external,
            current_tree,
            "Design-cycle receipt",
        )
        stop_control = design.get("stop_control", {})
        if (
            not isinstance(stop_control, dict)
            or stop_control.get("enforced") is not True
            or stop_control.get("continuation_allowed") is not True
            or stop_control.get("triggered")
        ):
            raise WebsiteOperatorError("Design-cycle stop control prevents release packaging.")
        generated_at = _parse_datetime(design.get("generated_at"), "design_cycle.generated_at")
        age = _utc_now() - generated_at
        if age < -timedelta(minutes=5):
            raise WebsiteOperatorError("Design-cycle receipt timestamp is in the future.")
        if age > timedelta(hours=float(self.config["deployment"]["audit_max_age_hours"])):
            raise WebsiteOperatorError("Design-cycle receipt is stale.")
        return design

    def _validate_editorial_package_binding(
        self,
        package: Mapping[str, Any],
        design: Mapping[str, Any],
    ) -> Dict[str, Any]:
        """Require exact provenance-bound public files in the release archive."""

        controls = design.get("evidence_controls")
        editorial = controls.get("editorial_assets") if isinstance(controls, Mapping) else None
        binding = editorial.get("binding") if isinstance(editorial, Mapping) else None
        if (
            not isinstance(editorial, Mapping)
            or editorial.get("passed") is not True
            or not isinstance(binding, Mapping)
        ):
            raise WebsiteOperatorError("Design-cycle receipt lacks a passing editorial package binding.")

        package_paths = package.get("paths")
        manifest_path = package.get("manifest")
        if not isinstance(package_paths, list) or not isinstance(manifest_path, str):
            raise WebsiteOperatorError("Validated package lost its exact path or manifest binding.")
        forbidden_receipt_names = {
            DEFAULT_EDITORIAL_IMPORT_RECEIPT_NAME.casefold(),
            "work-order.v4.json",
            "candidate.v1.json",
        }
        forbidden = sorted(
            path for path in package_paths if Path(str(path)).name.casefold() in forbidden_receipt_names
        )
        if forbidden:
            raise WebsiteOperatorError(
                "Candidate-control receipts may not be published in the website package: "
                + ", ".join(forbidden)
            )
        forbidden_receipt_schemas = {
            "aureon.design-editorial-asset-candidate-import.v1",
            "aureon.design-candidate.v1",
            WORK_ORDER_SCHEMA,
        }
        package_path_value = package.get("package")
        if not isinstance(package_path_value, str):
            raise WebsiteOperatorError("Validated package lost its release archive path.")
        package_path = _regular_single_link_file(
            Path(package_path_value),
            label="Editorial-bound release package",
        )
        schema_matches: list[str] = []
        with zipfile.ZipFile(package_path, "r") as archive:
            for relative in package_paths:
                canonical = _safe_relative_path(relative)
                if Path(canonical).suffix.casefold() != ".json":
                    continue
                try:
                    payload = json.loads(archive.read(canonical).decode("utf-8-sig"))
                except (KeyError, UnicodeDecodeError, json.JSONDecodeError):
                    continue
                if isinstance(payload, Mapping) and payload.get("schema") in forbidden_receipt_schemas:
                    schema_matches.append(canonical)
        if schema_matches:
            raise WebsiteOperatorError(
                "Candidate-control receipt schemas may not be published in the website package: "
                + ", ".join(sorted(schema_matches))
            )

        raw_required = binding.get("required_public_files")
        expected_required_hash = binding.get("required_public_files_sha256")
        if not isinstance(raw_required, list) or _sha256_json(raw_required) != (expected_required_hash):
            raise WebsiteOperatorError("Editorial package binding lost its exact required-file projection.")
        required_rows: dict[str, tuple[int, str]] = {}
        for item in raw_required:
            if not isinstance(item, Mapping):
                raise WebsiteOperatorError(
                    "Editorial package binding contains a malformed required-file row."
                )
            relative = _safe_relative_path(item.get("path"))
            byte_count = item.get("bytes")
            sha256 = item.get("sha256")
            if (
                type(byte_count) is not int
                or byte_count < 0
                or not isinstance(sha256, str)
                or not re.fullmatch(r"[A-F0-9]{64}", sha256)
                or relative in required_rows
            ):
                raise WebsiteOperatorError(f"Editorial package binding is invalid for: {relative}")
            required_rows[relative] = (byte_count, sha256)

        manifest_rows = {
            str(item["path"]): (int(item["bytes"]), str(item["sha256"]))
            for item in self._manifest_rows(
                _regular_single_link_file(
                    Path(manifest_path),
                    label="Editorial-bound release manifest",
                )
            )
        }
        missing_or_drifted = sorted(
            path for path, expected in required_rows.items() if manifest_rows.get(path) != expected
        )
        if missing_or_drifted:
            raise WebsiteOperatorError(
                "Release package omitted or changed provenance-bound editorial files: "
                + ", ".join(missing_or_drifted)
            )

        verified = dict(binding)
        verified["package_required_file_count"] = len(required_rows)
        verified["package_required_files_exact"] = True
        verified["candidate_control_receipts_excluded"] = True
        verified["package_binding_sha256"] = _sha256_json(verified)
        return verified

    def build_release(
        self,
        audit_receipt: Path,
        output_directory: Path,
        output: Path | None = None,
        *,
        design_cycle_receipt: Path | None = None,
        human_visual_accepted: bool = False,
        human_visual_accepted_by: str | None = None,
    ) -> Path:
        audit_path = audit_receipt.resolve()
        audit = _read_json(audit_path)
        self._require_receipt(audit, "audit")
        if audit.get("state") != "pass" or int(audit.get("summary", {}).get("blockers", 1)) != 0:
            raise WebsiteOperatorError("A blocked audit cannot authorise a release build.")
        if int(audit.get("summary", {}).get("warnings", 1)) != 0:
            raise WebsiteOperatorError("Open audit warnings prevent a release build.")
        if audit.get("summary", {}).get("external_checks_run") is not True:
            raise WebsiteOperatorError("A release build requires the complete external audit suite.")
        current_tree = _tree_hash(self.site_root, self._public_files())
        if audit.get("source_tree_sha256") != current_tree:
            raise WebsiteOperatorError("Website changed after the audit; run a fresh audit before building.")
        audit_composite_binding = self._require_composite_external_evidence(
            audit.get("external_checks"),
            current_tree,
            "Audit receipt",
        )
        if design_cycle_receipt is None:
            raise WebsiteOperatorError("A current passing design-cycle receipt is required.")
        design_path = design_cycle_receipt.resolve()
        design = self._validate_design_cycle_for_release(design_path, current_tree)
        design_composite_binding = self._require_composite_external_evidence(
            design.get("external_checks"),
            current_tree,
            "Design-cycle receipt",
        )
        if not self._same_composite_binding(
            audit_composite_binding,
            design_composite_binding,
        ):
            raise WebsiteOperatorError(
                "Audit and design-cycle receipts bind different composite visual evidence."
            )
        visual_reviewer = str(human_visual_accepted_by or "").strip()
        if human_visual_accepted is not True or not visual_reviewer:
            raise WebsiteOperatorError(
                "Explicit identified human visual acceptance is required before packaging."
            )
        composite_record, current_composite_binding = self._rerun_composite_gate(current_tree)
        if not self._same_composite_binding(
            audit_composite_binding,
            current_composite_binding,
        ):
            raise WebsiteOperatorError("Composite visual evidence changed after the audit or design cycle.")
        output_directory = output_directory.resolve()
        output_directory.mkdir(parents=True, exist_ok=True)
        pattern = str(self.config["packaging"]["receipt_glob"])
        before = {path.resolve() for path in output_directory.glob(pattern)}
        command = self._expand_command(
            self.config["packaging"]["command"],
            {"output_directory": str(output_directory)},
        )
        result = self.runner(command, self.repo_root)
        if result.returncode != 0:
            raise WebsiteOperatorError(
                "Release builder failed: "
                + (_short_output(result.stderr) or _short_output(result.stdout) or "no diagnostic")
            )
        after = {path.resolve() for path in output_directory.glob(pattern)}
        created = sorted(after.difference(before), key=lambda path: path.stat().st_mtime_ns)
        if len(created) != 1:
            raise WebsiteOperatorError(f"Expected exactly one new package receipt, observed {len(created)}.")
        post_builder_tree = _tree_hash(self.site_root, self._public_files())
        if post_builder_tree != current_tree:
            raise WebsiteOperatorError(
                "Website changed while the release builder was running; discard the package and run fresh gates."
            )
        self._validate_design_evidence_controls_for_release(design)
        package = self._validate_package(created[0])
        editorial_package_binding = self._validate_editorial_package_binding(
            package,
            design,
        )
        receipt = self._base_receipt("package")
        receipt.update(
            {
                "state": "prepared-not-deployed",
                "source_tree_sha256": current_tree,
                "audit_receipt": str(audit_path),
                "audit_receipt_sha256": _sha256_file(audit_path),
                "design_cycle_receipt": str(design_path),
                "design_cycle_receipt_sha256": _sha256_file(design_path),
                "design_cycle_run_id": design.get("run_id"),
                "composite_visual_gate": {
                    "check_id": COMPOSITE_VISUAL_GATE_CHECK_ID,
                    "returncode": composite_record.get("returncode"),
                    "checked_at": composite_record.get("checked_at"),
                    "current_source_tree_sha256": current_tree,
                    "stdout_json": composite_record.get("stdout_json"),
                    "binding": current_composite_binding,
                },
                "human_visual_acceptance": {
                    "accepted": True,
                    "accepted_by": visual_reviewer,
                    "accepted_at": _iso(),
                    "basis": "explicit-build-invocation",
                    "source_tree_sha256": current_tree,
                    "design_cycle_run_id": design.get("run_id"),
                },
                "editorial_asset_provenance": editorial_package_binding,
                **package,
                "deployment_authority": "none",
                "next_gate": "verified backup plus short-lived owner approval",
            }
        )
        return _atomic_write_json(self._path_for_output("package", output), receipt)

    def _homepl_live_root_binding(
        self,
        receipt_path: Path,
        *,
        require_fresh: bool = True,
    ) -> Dict[str, Any]:
        path = _regular_single_link_file(
            Path(os.path.abspath(receipt_path)),
            label="Home.pl root-mapping live reconciliation receipt",
        )
        reconciliation_root = _regular_directory(
            Path(os.path.abspath(self.repo_root / "artifacts" / "website-operator")),
            label="Website Operator reconciliation root",
        )
        if not _path_below(path, reconciliation_root):
            raise WebsiteOperatorError(
                "Home.pl root-mapping live reconciliation must stay below the receipts root."
            )
        receipt = _read_json(path)
        try:
            validate_live_surface_reconciliation(receipt)
        except LiveSurfaceReconciliationError as exc:
            raise WebsiteOperatorError(f"Home.pl root-mapping live reconciliation is invalid: {exc}") from exc
        observed = _parse_datetime(
            receipt.get("observed_at"),
            "live_reconciliation.observed_at",
        )
        now = _utc_now()
        if observed > now + timedelta(minutes=5):
            raise WebsiteOperatorError("Home.pl live reconciliation time is in the future.")
        if require_fresh and now - observed > HOMEPL_ROOT_MAPPING_MAX_AGE:
            raise WebsiteOperatorError(
                "Home.pl live reconciliation is too old for an action-time root mapping."
            )
        canonical = receipt.get("canonical")
        if not isinstance(canonical, dict):
            raise WebsiteOperatorError(
                "Home.pl live reconciliation is bound to another repository or website."
            )
        canonical_repo_value = canonical.get("repository_root")
        canonical_site_value = canonical.get("site_root")
        try:
            if not isinstance(canonical_repo_value, str) or not Path(canonical_repo_value).is_absolute():
                raise WebsiteOperatorError("Canonical repository root must be absolute.")
            canonical_repo = Path(canonical_repo_value).resolve()
            canonical_site_relative = _safe_relative_path(canonical_site_value)
            canonical_site = _safe_repo_path(canonical_repo, canonical_site_relative)
        except (OSError, RuntimeError, WebsiteOperatorError) as exc:
            raise WebsiteOperatorError(
                "Home.pl live reconciliation is bound to another repository or website."
            ) from exc
        if canonical_repo != self.repo_root or canonical_site != self.site_root:
            raise WebsiteOperatorError(
                "Home.pl live reconciliation is bound to another repository or website."
            )
        expected_public_url = urljoin(self.config["site"]["base_url"], "/")
        root_routes = [
            route
            for route in receipt.get("routes", [])
            if isinstance(route, dict) and route.get("local_path") == "index.html"
        ]
        if len(root_routes) != 1:
            raise WebsiteOperatorError(
                "Home.pl live reconciliation must contain exactly one root index route."
            )
        route = root_routes[0]
        live = route.get("live")
        if (
            route.get("public_url") != expected_public_url
            or route.get("final_url") != expected_public_url
            or not isinstance(route.get("http_status"), int)
            or not 200 <= route["http_status"] < 300
            or not isinstance(live, dict)
            or not re.fullmatch(r"[A-F0-9]{64}", str(live.get("sha256") or ""))
            or not isinstance(live.get("bytes"), int)
            or live["bytes"] < 1
        ):
            raise WebsiteOperatorError(
                "Home.pl live reconciliation lacks one exact successful public root fingerprint."
            )
        return {
            "live_reconciliation_receipt": str(path),
            "live_reconciliation_receipt_sha256": _sha256_file(path),
            "live_reconciliation_observed_at": _iso(observed),
            "public_root_url": expected_public_url,
            "public_root_sha256": live["sha256"],
            "public_root_bytes": live["bytes"],
        }

    def backup_preflight(
        self,
        output_directory: Path,
        ftp_host: str,
        ftp_account: str,
        live_reconciliation_receipt: Path,
        output: Path | None = None,
    ) -> Path:
        deployment = self.config["deployment"]
        identity = _homepl_ftp_identity(ftp_host, ftp_account)
        live_binding = self._homepl_live_root_binding(live_reconciliation_receipt)
        script_relative = _safe_relative_path(deployment["backup_script"])
        script = Path(os.path.abspath(self.repo_root / script_relative))
        backup_root = Path(os.path.abspath(self.repo_root / HOMEPL_BACKUP_ROOT))
        credential_names = [str(item) for item in deployment["credential_env_names"]]
        output_directory = Path(os.path.abspath(output_directory))
        manifest_path = Path(f"{output_directory}-manifest.csv")
        root_mapping_receipt_path = Path(f"{output_directory}-root-mapping.json")
        transfer_receipt_path = Path(f"{output_directory}-transfer.json")
        existing = output_directory.exists() or output_directory.is_symlink()
        parent_exists = output_directory.parent.exists()
        manifest_exists = manifest_path.exists() or manifest_path.is_symlink()
        root_mapping_receipt_exists = (
            root_mapping_receipt_path.exists() or root_mapping_receipt_path.is_symlink()
        )
        transfer_receipt_exists = transfer_receipt_path.exists() or transfer_receipt_path.is_symlink()
        script_safe = False
        script_sha256 = ""
        try:
            script = _regular_single_link_file(script, label="Home.pl backup script")
            script_safe = True
            script_sha256 = _sha256_file(script)
        except WebsiteOperatorError:
            pass
        backup_root_safe = False
        try:
            _regular_directory(backup_root, label="Home.pl backup root")
            backup_root_safe = True
        except WebsiteOperatorError:
            pass
        output_parent_safe = False
        if parent_exists:
            try:
                _regular_directory(output_directory.parent, label="Home.pl backup output parent")
                output_parent_safe = True
            except WebsiteOperatorError:
                pass
        output_within_backup_root = _path_below(output_directory, backup_root)
        ready = all(
            (
                deployment["remote_root"] == "/",
                script_safe,
                backup_root_safe,
                parent_exists,
                output_parent_safe,
                output_within_backup_root,
                not existing,
                not manifest_exists,
                not root_mapping_receipt_exists,
                not transfer_receipt_exists,
            )
        )
        receipt = self._base_receipt("backup-preflight")
        receipt.update(
            {
                "state": "ready-for-explicit-backup" if ready else "blocked",
                "backup_script": str(script),
                "backup_script_exists": script.is_file(),
                "backup_script_safe": script_safe,
                "backup_script_sha256": script_sha256,
                "backup_root": str(backup_root),
                "backup_root_safe": backup_root_safe,
                "output_directory": str(output_directory),
                "output_directory_exists": existing,
                "output_parent_exists": parent_exists,
                "output_parent_safe": output_parent_safe,
                "output_within_backup_root": output_within_backup_root,
                "manifest": str(manifest_path),
                "manifest_exists": manifest_exists,
                "root_mapping_receipt": str(root_mapping_receipt_path),
                "root_mapping_receipt_exists": root_mapping_receipt_exists,
                "transfer_receipt": str(transfer_receipt_path),
                "transfer_receipt_exists": transfer_receipt_exists,
                "remote_root": deployment["remote_root"],
                **identity,
                **live_binding,
                "required_root_entries": _homepl_required_root_entries(deployment["required_backup_paths"]),
                "credentials": {
                    "required_runtime_names": credential_names,
                    "values_recorded": False,
                },
                "read_only_contract": {
                    "remote_methods": ["ListDirectory", "GetFileSize", "DownloadFile"],
                    "remote_write_methods_permitted": False,
                    "final_output_published_only_after_complete_download": True,
                    "manifest_overwrite_permitted": False,
                },
                "destructive_action": False,
                "execution_attempted": False,
                "note": (
                    "Use the hash-bound backup tool explicitly. This receipt is preflight, "
                    "not transfer or backup proof."
                ),
            }
        )
        return _atomic_write_json(self._path_for_output("backup-preflight", output), receipt)

    def _validate_homepl_preflight(
        self,
        preflight: Mapping[str, Any],
        *,
        backup_directory: Path,
        manifest_path: Path,
        root_mapping_path: Path,
        transfer_path: Path,
        backup_script: Path,
        backup_root: Path,
        require_live_fresh: bool,
    ) -> Dict[str, Any]:
        self._require_receipt(preflight, "backup-preflight")
        if set(preflight) != HOMEPL_PREFLIGHT_RECEIPT_FIELDS:
            raise WebsiteOperatorError("Backup preflight receipt fields are incomplete or unexpected.")
        required_root_entries = _homepl_required_root_entries(
            self.config["deployment"]["required_backup_paths"]
        )
        expected_fields = {
            "repo_root": str(self.repo_root),
            "site_root": str(self.site_root),
            "state": "ready-for-explicit-backup",
            "backup_script": str(backup_script),
            "backup_script_exists": True,
            "backup_script_safe": True,
            "backup_script_sha256": _sha256_file(backup_script),
            "backup_root": str(backup_root),
            "backup_root_safe": True,
            "output_directory": str(backup_directory),
            "output_directory_exists": False,
            "output_parent_exists": True,
            "output_parent_safe": True,
            "output_within_backup_root": True,
            "manifest": str(manifest_path),
            "manifest_exists": False,
            "root_mapping_receipt": str(root_mapping_path),
            "root_mapping_receipt_exists": False,
            "transfer_receipt": str(transfer_path),
            "transfer_receipt_exists": False,
            "remote_root": "/",
            "required_root_entries": required_root_entries,
            "destructive_action": False,
            "execution_attempted": False,
            "note": (
                "Use the hash-bound backup tool explicitly. This receipt is preflight, "
                "not transfer or backup proof."
            ),
        }
        for receipt_field, expected in expected_fields.items():
            if preflight.get(receipt_field) != expected:
                raise WebsiteOperatorError(f"Backup preflight field changed or is unsafe: {receipt_field}")
        run_id = preflight.get("run_id")
        if not isinstance(run_id, str) or not re.fullmatch(r"[a-f0-9]{32}", run_id):
            raise WebsiteOperatorError("Backup preflight run_id is invalid.")
        generated = _parse_datetime(preflight.get("generated_at"), "preflight.generated_at")
        if generated > _utc_now() + timedelta(minutes=5):
            raise WebsiteOperatorError("Backup preflight generation time is in the future.")
        expected_credentials = {
            "required_runtime_names": [
                str(item) for item in self.config["deployment"]["credential_env_names"]
            ],
            "values_recorded": False,
        }
        if preflight.get("credentials") != expected_credentials:
            raise WebsiteOperatorError("Backup preflight credential boundary is invalid.")
        expected_read_only = {
            "remote_methods": ["ListDirectory", "GetFileSize", "DownloadFile"],
            "remote_write_methods_permitted": False,
            "final_output_published_only_after_complete_download": True,
            "manifest_overwrite_permitted": False,
        }
        if preflight.get("read_only_contract") != expected_read_only:
            raise WebsiteOperatorError("Backup preflight read-only contract is invalid.")
        identity_fields = (
            "ftp_host_id",
            "ftp_host_sha256",
            "ftp_account_sha256",
            "ftp_binding_sha256",
        )
        if not all(
            re.fullmatch(r"[A-F0-9]{64}", str(preflight.get(field) or "")) for field in identity_fields[1:]
        ) or _homepl_ftp_identity(
            preflight.get("ftp_host_id"),
            "identity-check",
        ).get("ftp_host_sha256") != preflight.get("ftp_host_sha256"):
            raise WebsiteOperatorError("Backup preflight FTPS identity binding is invalid.")
        live_binding = self._homepl_live_root_binding(
            Path(str(preflight.get("live_reconciliation_receipt", ""))),
            require_fresh=require_live_fresh,
        )
        if any(preflight.get(field) != value for field, value in live_binding.items()):
            raise WebsiteOperatorError("Backup preflight public root binding has changed.")
        live_observed = _parse_datetime(
            live_binding["live_reconciliation_observed_at"],
            "preflight.live_reconciliation_observed_at",
        )
        if generated < live_observed - timedelta(minutes=5):
            raise WebsiteOperatorError("Backup preflight predates its public root observation.")
        return live_binding

    def _validate_homepl_root_mapping(
        self,
        mapping_path: Path,
        *,
        preflight_path: Path,
        preflight: Mapping[str, Any],
        backup_directory: Path,
        backup_script: Path,
        require_fresh: bool,
    ) -> Dict[str, Any]:
        path = _regular_single_link_file(
            Path(os.path.abspath(mapping_path)),
            label="Home.pl authenticated root-mapping receipt",
        )
        expected_path = Path(f"{backup_directory}-root-mapping.json")
        if path != expected_path or preflight.get("root_mapping_receipt") != str(path):
            raise WebsiteOperatorError(
                "Home.pl root-mapping receipt is not the preflight-bound adjacent receipt."
            )
        mapping = _read_json(path)
        required_fields = {
            "schema",
            "state",
            "method",
            "source_assertion",
            "source_tool",
            "observed_at",
            "remote_root",
            "ftp_host_id",
            "ftp_host_sha256",
            "ftp_account_sha256",
            "ftp_binding_sha256",
            "preflight_receipt",
            "preflight_receipt_sha256",
            "backup_script",
            "backup_script_sha256",
            "live_reconciliation_receipt",
            "live_reconciliation_receipt_sha256",
            "live_reconciliation_observed_at",
            "public_root_url",
            "public_root_sha256",
            "public_root_bytes",
            "remote_root_index_sha256",
            "remote_root_index_bytes",
            "listing_entry_count",
            "listing_sha256",
            "required_root_entries",
            "required_root_entries_observed",
            "remote_operations",
            "remote_write_methods_used",
            "credentials_recorded",
        }
        if set(mapping) != required_fields:
            raise WebsiteOperatorError("Home.pl root-mapping receipt fields are incomplete or unexpected.")
        identity_fields = (
            "ftp_host_id",
            "ftp_host_sha256",
            "ftp_account_sha256",
            "ftp_binding_sha256",
        )
        live_fields = (
            "live_reconciliation_receipt",
            "live_reconciliation_receipt_sha256",
            "live_reconciliation_observed_at",
            "public_root_url",
            "public_root_sha256",
            "public_root_bytes",
        )
        if (
            mapping.get("schema") != HOMEPL_ROOT_MAPPING_SCHEMA
            or mapping.get("state") != "authenticated-served-root-mapped"
            or mapping.get("method") != "homepl-ftps"
            or mapping.get("source_assertion")
            != "Authenticated Home.pl account mapped to current public root bytes"
            or mapping.get("source_tool") != "repo-read-only-ftps-script"
            or mapping.get("remote_root") != "/"
            or any(mapping.get(field) != preflight.get(field) for field in identity_fields)
            or any(mapping.get(field) != preflight.get(field) for field in live_fields)
            or mapping.get("preflight_receipt") != str(preflight_path)
            or mapping.get("preflight_receipt_sha256") != _sha256_file(preflight_path)
            or mapping.get("backup_script") != str(backup_script)
            or mapping.get("backup_script_sha256") != _sha256_file(backup_script)
            or mapping.get("public_root_sha256") != mapping.get("remote_root_index_sha256")
            or mapping.get("public_root_bytes") != mapping.get("remote_root_index_bytes")
            or mapping.get("required_root_entries") != preflight.get("required_root_entries")
            or mapping.get("required_root_entries_observed") is not True
            or mapping.get("remote_operations") != ["ListDirectory", "DownloadFile"]
            or mapping.get("remote_write_methods_used") is not False
            or mapping.get("credentials_recorded") is not False
            or not isinstance(mapping.get("listing_entry_count"), int)
            or mapping["listing_entry_count"] < len(mapping["required_root_entries"])
            or not re.fullmatch(r"[A-F0-9]{64}", str(mapping.get("listing_sha256") or ""))
        ):
            raise WebsiteOperatorError(
                "Home.pl root-mapping receipt does not prove the exact authenticated served root."
            )
        current_live = self._homepl_live_root_binding(
            Path(str(preflight.get("live_reconciliation_receipt", ""))),
            require_fresh=require_fresh,
        )
        if any(preflight.get(field) != current_live.get(field) for field in live_fields):
            raise WebsiteOperatorError("Home.pl root-mapping public reconciliation binding has changed.")
        observed = _parse_datetime(mapping.get("observed_at"), "root_mapping.observed_at")
        live_observed = _parse_datetime(
            mapping.get("live_reconciliation_observed_at"),
            "root_mapping.live_reconciliation_observed_at",
        )
        now = _utc_now()
        if observed < live_observed - timedelta(minutes=5):
            raise WebsiteOperatorError("Home.pl root mapping predates its public root observation.")
        if observed - live_observed > HOMEPL_ROOT_MAPPING_MAX_AGE:
            raise WebsiteOperatorError(
                "Home.pl root mapping was not created from a current public observation."
            )
        preflight_generated = _parse_datetime(
            preflight.get("generated_at"),
            "preflight.generated_at",
        )
        if observed < preflight_generated - timedelta(minutes=5):
            raise WebsiteOperatorError("Home.pl root mapping predates its bound preflight.")
        if observed > now + timedelta(minutes=5):
            raise WebsiteOperatorError("Home.pl root-mapping observation is in the future.")
        if require_fresh and now - observed > HOMEPL_ROOT_MAPPING_MAX_AGE:
            raise WebsiteOperatorError("Home.pl root-mapping observation is stale.")
        return mapping

    def verify_backup(
        self,
        backup_directory: Path,
        manifest_path: Path,
        method: str,
        observed_at: str | None = None,
        package_receipt: Path | None = None,
        output: Path | None = None,
        *,
        preflight_receipt: Path,
        transfer_receipt: Path,
    ) -> Path:
        if method != "homepl-ftps":
            raise WebsiteOperatorError(
                "The exact-host backup verifier currently requires method homepl-ftps."
            )
        backup_directory = _regular_directory(
            Path(os.path.abspath(backup_directory)),
            label="Home.pl backup directory",
        )
        manifest_path = _regular_single_link_file(
            Path(os.path.abspath(manifest_path)),
            label="Home.pl backup manifest",
        )
        backup_root = _regular_directory(
            Path(os.path.abspath(self.repo_root / HOMEPL_BACKUP_ROOT)),
            label="Home.pl backup root",
        )
        artifacts_root = _regular_directory(
            Path(os.path.abspath(self.repo_root / "artifacts")),
            label="Aureon artifacts root",
        )
        if not _path_below(backup_directory, backup_root):
            raise WebsiteOperatorError(
                "Backup directory must stay below the repository artifacts/homepl-backups root."
            )
        if not _path_below(manifest_path, artifacts_root) or _path_below(
            manifest_path,
            backup_directory,
        ):
            raise WebsiteOperatorError(
                "Backup manifest must stay below artifacts and outside the downloaded tree."
            )
        expected_manifest = Path(f"{backup_directory}-manifest.csv")
        if manifest_path != expected_manifest:
            raise WebsiteOperatorError("Backup manifest is not the preflight-bound adjacent manifest.")

        preflight_path = _regular_single_link_file(
            Path(os.path.abspath(preflight_receipt)),
            label="Home.pl backup preflight receipt",
        )
        receipts_root = _regular_directory(
            Path(os.path.abspath(self.receipts_dir)),
            label="Website Operator receipts root",
        )
        if not _path_below(preflight_path, receipts_root):
            raise WebsiteOperatorError(
                "Backup preflight receipt must stay below the Website Operator receipts root."
            )
        preflight = _read_json(preflight_path)

        deployment = self.config["deployment"]
        script_relative = _safe_relative_path(deployment["backup_script"])
        backup_script = _regular_single_link_file(
            Path(os.path.abspath(self.repo_root / script_relative)),
            label="Home.pl backup script",
        )
        backup_script_sha256 = _sha256_file(backup_script)
        expected_root_mapping = Path(f"{backup_directory}-root-mapping.json")
        expected_transfer = Path(f"{backup_directory}-transfer.json")
        identity_fields = (
            "ftp_host_id",
            "ftp_host_sha256",
            "ftp_account_sha256",
            "ftp_binding_sha256",
        )
        live_binding = self._validate_homepl_preflight(
            preflight,
            backup_directory=backup_directory,
            manifest_path=expected_manifest,
            root_mapping_path=expected_root_mapping,
            transfer_path=expected_transfer,
            backup_script=backup_script,
            backup_root=backup_root,
            require_live_fresh=True,
        )
        root_mapping = self._validate_homepl_root_mapping(
            expected_root_mapping,
            preflight_path=preflight_path,
            preflight=preflight,
            backup_directory=backup_directory,
            backup_script=backup_script,
            require_fresh=True,
        )
        root_mapping_sha256 = _sha256_file(expected_root_mapping)

        transfer_path = _regular_single_link_file(
            Path(os.path.abspath(transfer_receipt)),
            label="Home.pl backup transfer receipt",
        )
        if transfer_path != expected_transfer:
            raise WebsiteOperatorError("Backup transfer receipt is not the preflight-bound receipt.")
        transfer = _read_json(transfer_path)
        if set(transfer) != HOMEPL_TRANSFER_RECEIPT_FIELDS:
            raise WebsiteOperatorError("Backup transfer receipt fields are incomplete or unexpected.")
        if (
            transfer.get("schema") != HOMEPL_TRANSFER_SCHEMA
            or transfer.get("state") != "backup-complete"
            or transfer.get("method") != method
            or transfer.get("source_assertion") != HOMEPL_TRANSFER_SOURCE_ASSERTION
            or transfer.get("remote_root") != "/"
            or any(transfer.get(field) != preflight.get(field) for field in identity_fields)
            or transfer.get("backup_directory") != str(backup_directory)
            or transfer.get("manifest") != str(manifest_path)
            or transfer.get("preflight_receipt") != str(preflight_path)
            or transfer.get("preflight_receipt_sha256") != _sha256_file(preflight_path)
            or transfer.get("root_mapping_receipt") != str(expected_root_mapping)
            or transfer.get("root_mapping_receipt_sha256") != root_mapping_sha256
            or transfer.get("live_reconciliation_receipt") != preflight.get("live_reconciliation_receipt")
            or transfer.get("live_reconciliation_receipt_sha256")
            != preflight.get("live_reconciliation_receipt_sha256")
            or transfer.get("public_root_sha256") != preflight.get("public_root_sha256")
            or transfer.get("root_continuity_observed") is not True
            or transfer.get("transfer_start_root_listing_sha256") != root_mapping.get("listing_sha256")
            or transfer.get("transfer_start_root_listing_entry_count")
            != root_mapping.get("listing_entry_count")
            or transfer.get("transfer_start_root_index_sha256")
            != root_mapping.get("remote_root_index_sha256")
            or transfer.get("transfer_start_root_index_bytes") != root_mapping.get("remote_root_index_bytes")
            or transfer.get("transfer_end_root_listing_sha256") != root_mapping.get("listing_sha256")
            or transfer.get("transfer_end_root_listing_entry_count")
            != root_mapping.get("listing_entry_count")
            or transfer.get("transfer_end_root_index_sha256") != root_mapping.get("remote_root_index_sha256")
            or transfer.get("transfer_end_root_index_bytes") != root_mapping.get("remote_root_index_bytes")
            or transfer.get("remote_write_methods_used") is not False
            or transfer.get("credentials_recorded") is not False
        ):
            raise WebsiteOperatorError("Backup transfer receipt does not match the exact read-only run.")
        if (
            transfer.get("source_tool") != "repo-read-only-ftps-script"
            or transfer.get("backup_script") != str(backup_script)
            or transfer.get("backup_script_sha256") != backup_script_sha256
            or transfer.get("remote_operations") != ["ListDirectory", "GetFileSize", "DownloadFile"]
            or root_mapping.get("ftp_binding_sha256") != transfer.get("ftp_binding_sha256")
        ):
            raise WebsiteOperatorError("FTPS transfer receipt is not bound to the audited script.")
        started = _parse_datetime(transfer.get("started_at"), "transfer.started_at")
        completed = _parse_datetime(transfer.get("completed_at"), "transfer.completed_at")
        now = _utc_now()
        if started > completed:
            raise WebsiteOperatorError("Backup transfer completed before it started.")
        if completed > now + timedelta(minutes=5):
            raise WebsiteOperatorError("Backup transfer completion time is in the future.")
        root_mapping_observed = _parse_datetime(
            root_mapping.get("observed_at"),
            "root_mapping.observed_at",
        )
        if started < root_mapping_observed - timedelta(minutes=5):
            raise WebsiteOperatorError("Backup transfer predates its authenticated root mapping.")
        if completed - root_mapping_observed > HOMEPL_ROOT_MAPPING_MAX_AGE:
            raise WebsiteOperatorError("Backup transfer exceeded the authenticated root-mapping window.")
        if now - completed > timedelta(hours=float(self.config["deployment"]["backup_max_age_hours"])):
            raise WebsiteOperatorError("Completed backup transfer is already stale.")
        if observed_at is not None:
            supplied_observed = _parse_datetime(observed_at, "observed_at")
            if supplied_observed != completed:
                raise WebsiteOperatorError(
                    "observed_at must exactly match the transfer receipt completion time."
                )
        observed = completed

        rows = self._manifest_rows(manifest_path)
        files = _complete_regular_tree_files(
            backup_directory,
            label="Home.pl backup tree",
        )
        actual_paths = {path.relative_to(backup_directory).as_posix(): path for path in files}
        manifest_paths = {row["path"] for row in rows}
        if set(actual_paths) != manifest_paths:
            missing = sorted(manifest_paths.difference(actual_paths))
            extra = sorted(set(actual_paths).difference(manifest_paths))
            details = []
            if missing:
                details.append("missing=" + ",".join(missing))
            if extra:
                details.append("unmanifested=" + ",".join(extra))
            raise WebsiteOperatorError(
                "Backup manifest does not describe the complete downloaded tree"
                + (": " + "; ".join(details) if details else ".")
            )
        for row in rows:
            path = actual_paths[row["path"]]
            if path.stat().st_size != row["bytes"] or _sha256_file(path) != row["sha256"]:
                raise WebsiteOperatorError(f"Backup manifest mismatch: {row['path']}")
        manifest_sha256 = _sha256_file(manifest_path)
        total_bytes = sum(row["bytes"] for row in rows)
        if (
            transfer.get("manifest_sha256") != manifest_sha256
            or transfer.get("file_count") != len(rows)
            or transfer.get("total_bytes") != total_bytes
        ):
            raise WebsiteOperatorError("Backup transfer receipt does not match downloaded bytes.")
        root_index_rows = [row for row in rows if row["path"] == "index.html"]
        if (
            len(root_index_rows) != 1
            or root_index_rows[0]["sha256"] != root_mapping.get("remote_root_index_sha256")
            or root_index_rows[0]["bytes"] != root_mapping.get("remote_root_index_bytes")
        ):
            raise WebsiteOperatorError(
                "Downloaded root index does not match the authenticated public root mapping."
            )
        required_backup = {
            _safe_relative_path(item) for item in self.config["deployment"]["required_backup_paths"]
        }
        backup_paths = {row["path"] for row in rows}
        missing_required = sorted(required_backup.difference(backup_paths))
        if missing_required:
            raise WebsiteOperatorError(
                "Backup is missing required live paths: " + ", ".join(missing_required)
            )
        release_paths: set[str] = set()
        package_sha = ""
        package_path_string = ""
        if package_receipt:
            package_path = package_receipt.resolve()
            package = self._validate_package_receipt(package_path)
            release_paths = {_safe_relative_path(item) for item in package.get("paths", [])}
            package_sha = str(package.get("package_sha256", ""))
            package_path_string = str(package_path)
        protected = sorted(release_paths.intersection(backup_paths))
        new_paths = sorted(release_paths.difference(backup_paths))
        receipt = self._base_receipt("backup")
        receipt.update(
            {
                "state": "verified-backup",
                "observed_at": _iso(observed),
                "method": method,
                "source_assertion": HOMEPL_TRANSFER_SOURCE_ASSERTION,
                "remote_root": self.config["deployment"]["remote_root"],
                **{field: preflight[field] for field in identity_fields},
                "backup_directory": str(backup_directory),
                "manifest": str(manifest_path),
                "manifest_sha256": manifest_sha256,
                "tree_sha256": _tree_hash(backup_directory, files),
                "file_count": len(rows),
                "total_bytes": total_bytes,
                "preflight_receipt": str(preflight_path),
                "preflight_receipt_sha256": _sha256_file(preflight_path),
                "root_mapping_receipt": str(expected_root_mapping),
                "root_mapping_receipt_sha256": root_mapping_sha256,
                "root_mapping_observed_at": root_mapping["observed_at"],
                "served_root_continuity": {
                    "start_and_end_match_mapping": True,
                    "downloaded_index_matches_mapping": True,
                    "listing_sha256": root_mapping["listing_sha256"],
                    "root_index_sha256": root_mapping["remote_root_index_sha256"],
                    "root_index_bytes": root_mapping["remote_root_index_bytes"],
                },
                **live_binding,
                "transfer_receipt": str(transfer_path),
                "transfer_receipt_sha256": _sha256_file(transfer_path),
                "backup_script": str(backup_script),
                "backup_script_sha256": backup_script_sha256,
                "complete_manifest_membership": True,
                "ordinary_single_link_files_only": True,
                "remote_write_methods_used": False,
                "credentials_recorded": False,
                "package_receipt": package_path_string,
                "package_sha256": package_sha,
                "rollback": {
                    "protected_release_paths": protected,
                    "new_release_paths": new_paths,
                    "mode": "manual-owner-approved-restore-only",
                    "automatic_rollback": False,
                    "new_path_removal_requires_separate_owner_review": bool(new_paths),
                },
            }
        )
        return _atomic_write_json(self._path_for_output("backup", output), receipt)

    def _validate_package_receipt(self, path: Path) -> Dict[str, Any]:
        path = _regular_single_link_file(path, label="WebsiteOperator package receipt")
        receipt = _read_json(path)
        self._require_receipt(receipt, "package")
        if receipt.get("state") != "prepared-not-deployed":
            raise WebsiteOperatorError("Package receipt is not in prepared-not-deployed state.")
        raw_path_value = receipt.get("raw_receipt")
        if not isinstance(raw_path_value, str) or not Path(raw_path_value).is_absolute():
            raise WebsiteOperatorError("Package receipt raw_receipt must be an absolute path.")
        raw_path = Path(raw_path_value)
        current = self._validate_package(raw_path)
        for receipt_field in (
            "raw_receipt",
            "raw_receipt_sha256",
            "package",
            "package_sha256",
            "package_bytes",
            "manifest",
            "manifest_sha256",
            "dependency_manifest",
            "dependency_manifest_sha256",
            "file_count",
            "total_uncompressed_bytes",
            "paths",
            "package_validation",
            "dependency_closure",
            "dependency_evidence_rows",
            "builder_schema",
        ):
            if receipt.get(receipt_field) != current.get(receipt_field):
                raise WebsiteOperatorError(f"Package receipt field changed or is invalid: {receipt_field}")
        current_tree = _tree_hash(self.site_root, self._public_files())
        if receipt.get("source_tree_sha256") != current_tree:
            raise WebsiteOperatorError("Website changed after release packaging.")
        audit_path = Path(str(receipt.get("audit_receipt", ""))).resolve()
        if not audit_path.is_file() or _sha256_file(audit_path) != receipt.get("audit_receipt_sha256"):
            raise WebsiteOperatorError("Bound audit receipt is missing or has changed.")
        audit = _read_json(audit_path)
        self._require_receipt(audit, "audit")
        audit_binding = self._require_composite_external_evidence(
            audit.get("external_checks"),
            current_tree,
            "Bound audit receipt",
        )
        design_path = Path(str(receipt.get("design_cycle_receipt", ""))).resolve()
        if not design_path.is_file() or _sha256_file(design_path) != receipt.get(
            "design_cycle_receipt_sha256"
        ):
            raise WebsiteOperatorError("Bound design-cycle receipt is missing or has changed.")
        design = self._validate_design_cycle_for_release(design_path, current_tree)
        design_binding = self._require_composite_external_evidence(
            design.get("external_checks"),
            current_tree,
            "Bound design-cycle receipt",
        )
        if not self._same_composite_binding(audit_binding, design_binding):
            raise WebsiteOperatorError(
                "Bound audit and design-cycle receipts use different composite evidence."
            )
        current_editorial_package_binding = self._validate_editorial_package_binding(
            current,
            design,
        )
        if receipt.get("editorial_asset_provenance") != current_editorial_package_binding:
            raise WebsiteOperatorError("Package editorial provenance binding changed or no longer verifies.")
        package_gate = receipt.get("composite_visual_gate")
        if not isinstance(package_gate, dict):
            raise WebsiteOperatorError("Package lacks a bound composite visual gate.")
        package_record = {
            "id": package_gate.get("check_id"),
            "required": True,
            "returncode": package_gate.get("returncode"),
            "state": "pass" if package_gate.get("returncode") == 0 else "failed",
            "current_source_tree_sha256": package_gate.get("current_source_tree_sha256"),
            "stdout_json": package_gate.get("stdout_json"),
            "composite_gate": package_gate.get("binding"),
        }
        package_binding = self._require_composite_external_evidence(
            {
                "complete": True,
                "required_composite_check_id": COMPOSITE_VISUAL_GATE_CHECK_ID,
                "results": [package_record],
            },
            current_tree,
            "Package receipt",
        )
        if not self._same_composite_binding(audit_binding, package_binding):
            raise WebsiteOperatorError(
                "Package composite visual binding differs from its audit and design evidence."
            )
        _, current_binding = self._rerun_composite_gate(current_tree)
        if not self._same_composite_binding(package_binding, current_binding):
            raise WebsiteOperatorError("Composite visual evidence changed after release packaging.")
        acceptance = receipt.get("human_visual_acceptance", {})
        if (
            not isinstance(acceptance, dict)
            or acceptance.get("accepted") is not True
            or not str(acceptance.get("accepted_by") or "").strip()
            or acceptance.get("source_tree_sha256") != current_tree
            or acceptance.get("design_cycle_run_id") != design.get("run_id")
        ):
            raise WebsiteOperatorError("Package lacks valid source-bound human visual acceptance.")
        sanitised = dict(receipt)
        sanitised.update(current)
        return sanitised

    def _revalidate_backup_receipt(self, backup: Mapping[str, Any]) -> None:
        self._require_receipt(backup, "backup")
        if set(backup) != HOMEPL_BACKUP_RECEIPT_FIELDS:
            raise WebsiteOperatorError("Verified backup receipt fields are incomplete or unexpected.")
        if (
            backup.get("state") != "verified-backup"
            or backup.get("repo_root") != str(self.repo_root)
            or backup.get("site_root") != str(self.site_root)
            or not isinstance(backup.get("run_id"), str)
            or not re.fullmatch(r"[a-f0-9]{32}", str(backup.get("run_id")))
        ):
            raise WebsiteOperatorError("Verified backup base binding has changed.")
        backup_directory = _regular_directory(
            Path(os.path.abspath(str(backup.get("backup_directory", "")))),
            label="Verified Home.pl backup directory",
        )
        manifest_path = _regular_single_link_file(
            Path(os.path.abspath(str(backup.get("manifest", "")))),
            label="Verified Home.pl backup manifest",
        )
        backup_root = _regular_directory(
            Path(os.path.abspath(self.repo_root / HOMEPL_BACKUP_ROOT)),
            label="Home.pl backup root",
        )
        artifacts_root = _regular_directory(
            Path(os.path.abspath(self.repo_root / "artifacts")),
            label="Aureon artifacts root",
        )
        if (
            not _path_below(backup_directory, backup_root)
            or not _path_below(manifest_path, artifacts_root)
            or _path_below(manifest_path, backup_directory)
            or manifest_path != Path(f"{backup_directory}-manifest.csv")
        ):
            raise WebsiteOperatorError("Verified backup paths no longer satisfy their boundary.")
        if _sha256_file(manifest_path) != backup.get("manifest_sha256"):
            raise WebsiteOperatorError("Verified backup manifest has changed.")
        rows = self._manifest_rows(manifest_path)
        files = _complete_regular_tree_files(
            backup_directory,
            label="Verified Home.pl backup tree",
        )
        actual_paths = {path.relative_to(backup_directory).as_posix(): path for path in files}
        if set(actual_paths) != {row["path"] for row in rows}:
            raise WebsiteOperatorError("Verified backup tree membership has changed.")
        for row in rows:
            path = actual_paths[row["path"]]
            if path.stat().st_size != row["bytes"] or _sha256_file(path) != row["sha256"]:
                raise WebsiteOperatorError(f"Verified backup file has changed: {row['path']}")
        backup_paths = set(actual_paths)
        package_receipt_value = backup.get("package_receipt")
        package_sha256_value = backup.get("package_sha256")
        if not isinstance(package_receipt_value, str) or not isinstance(
            package_sha256_value,
            str,
        ):
            raise WebsiteOperatorError("Verified backup package binding is malformed.")
        release_paths: set[str] = set()
        if package_receipt_value:
            package_path = Path(package_receipt_value)
            if not package_path.is_absolute():
                raise WebsiteOperatorError("Verified backup package receipt path must be absolute.")
            package = self._validate_package_receipt(package_path)
            if package_sha256_value != package.get("package_sha256"):
                raise WebsiteOperatorError("Verified backup package binding has changed.")
            release_paths = {_safe_relative_path(item) for item in package.get("paths", [])}
        elif package_sha256_value:
            raise WebsiteOperatorError("Verified backup has a package hash without a package receipt.")
        expected_rollback = {
            "protected_release_paths": sorted(release_paths.intersection(backup_paths)),
            "new_release_paths": sorted(release_paths.difference(backup_paths)),
            "mode": "manual-owner-approved-restore-only",
            "automatic_rollback": False,
            "new_path_removal_requires_separate_owner_review": bool(release_paths.difference(backup_paths)),
        }
        if backup.get("rollback") != expected_rollback:
            raise WebsiteOperatorError("Verified backup rollback coverage has changed.")
        if _tree_hash(backup_directory, files) != backup.get("tree_sha256"):
            raise WebsiteOperatorError("Verified backup tree hash has changed.")
        if (
            backup.get("file_count") != len(rows)
            or backup.get("total_bytes") != sum(row["bytes"] for row in rows)
            or backup.get("complete_manifest_membership") is not True
            or backup.get("ordinary_single_link_files_only") is not True
            or backup.get("remote_write_methods_used") is not False
            or backup.get("credentials_recorded") is not False
            or backup.get("source_assertion") != HOMEPL_TRANSFER_SOURCE_ASSERTION
        ):
            raise WebsiteOperatorError("Verified backup safety boundary has changed.")

        preflight_path = _regular_single_link_file(
            Path(os.path.abspath(str(backup.get("preflight_receipt", "")))),
            label="Verified Home.pl preflight receipt",
        )
        root_mapping_path = _regular_single_link_file(
            Path(os.path.abspath(str(backup.get("root_mapping_receipt", "")))),
            label="Verified Home.pl root-mapping receipt",
        )
        transfer_path = _regular_single_link_file(
            Path(os.path.abspath(str(backup.get("transfer_receipt", "")))),
            label="Verified Home.pl transfer receipt",
        )
        receipts_root = _regular_directory(
            Path(os.path.abspath(self.receipts_dir)),
            label="Website Operator receipts root",
        )
        if not _path_below(preflight_path, receipts_root):
            raise WebsiteOperatorError("Verified backup preflight leaves the Website Operator receipts root.")
        if root_mapping_path != Path(f"{backup_directory}-root-mapping.json") or transfer_path != Path(
            f"{backup_directory}-transfer.json"
        ):
            raise WebsiteOperatorError(
                "Verified backup provenance receipts are not the adjacent bound files."
            )
        if (
            _sha256_file(preflight_path) != backup.get("preflight_receipt_sha256")
            or _sha256_file(root_mapping_path) != backup.get("root_mapping_receipt_sha256")
            or _sha256_file(transfer_path) != backup.get("transfer_receipt_sha256")
        ):
            raise WebsiteOperatorError("Verified backup provenance receipt has changed.")
        preflight = _read_json(preflight_path)
        script_relative = _safe_relative_path(self.config["deployment"]["backup_script"])
        backup_script = _regular_single_link_file(
            Path(os.path.abspath(self.repo_root / script_relative)),
            label="Verified Home.pl backup script",
        )
        self._validate_homepl_preflight(
            preflight,
            backup_directory=backup_directory,
            manifest_path=manifest_path,
            root_mapping_path=root_mapping_path,
            transfer_path=transfer_path,
            backup_script=backup_script,
            backup_root=backup_root,
            require_live_fresh=False,
        )
        root_mapping = self._validate_homepl_root_mapping(
            root_mapping_path,
            preflight_path=preflight_path,
            preflight=preflight,
            backup_directory=backup_directory,
            backup_script=backup_script,
            require_fresh=False,
        )
        transfer = _read_json(transfer_path)
        if set(transfer) != HOMEPL_TRANSFER_RECEIPT_FIELDS:
            raise WebsiteOperatorError("Verified backup transfer fields are incomplete or unexpected.")
        identity_fields = (
            "ftp_host_id",
            "ftp_host_sha256",
            "ftp_account_sha256",
            "ftp_binding_sha256",
        )
        live_fields = (
            "live_reconciliation_receipt",
            "live_reconciliation_receipt_sha256",
            "live_reconciliation_observed_at",
            "public_root_url",
            "public_root_sha256",
            "public_root_bytes",
        )
        transfer_live_fields = (
            "live_reconciliation_receipt",
            "live_reconciliation_receipt_sha256",
            "public_root_sha256",
        )
        expected_continuity = {
            "start_and_end_match_mapping": True,
            "downloaded_index_matches_mapping": True,
            "listing_sha256": root_mapping.get("listing_sha256"),
            "root_index_sha256": root_mapping.get("remote_root_index_sha256"),
            "root_index_bytes": root_mapping.get("remote_root_index_bytes"),
        }
        root_index_rows = [row for row in rows if row["path"] == "index.html"]
        started = _parse_datetime(transfer.get("started_at"), "transfer.started_at")
        completed = _parse_datetime(transfer.get("completed_at"), "transfer.completed_at")
        backup_observed = _parse_datetime(backup.get("observed_at"), "backup.observed_at")
        backup_generated = _parse_datetime(
            backup.get("generated_at"),
            "backup.generated_at",
        )
        mapping_observed = _parse_datetime(
            root_mapping.get("observed_at"),
            "root_mapping.observed_at",
        )
        now = _utc_now()
        if (
            started > completed
            or completed != backup_observed
            or started < mapping_observed - timedelta(minutes=5)
            or started - mapping_observed > HOMEPL_ROOT_MAPPING_MAX_AGE
            or completed - mapping_observed > HOMEPL_ROOT_MAPPING_MAX_AGE
            or completed > now + timedelta(minutes=5)
            or backup_generated < completed - timedelta(minutes=5)
            or backup_generated > now + timedelta(minutes=5)
        ):
            raise WebsiteOperatorError("Verified backup transfer chronology has changed or is unsafe.")
        if (
            preflight.get("state") != "ready-for-explicit-backup"
            or preflight.get("output_directory") != str(backup_directory)
            or preflight.get("manifest") != str(manifest_path)
            or preflight.get("root_mapping_receipt") != str(root_mapping_path)
            or preflight.get("transfer_receipt") != str(transfer_path)
            or transfer.get("schema") != HOMEPL_TRANSFER_SCHEMA
            or transfer.get("state") != "backup-complete"
            or backup.get("method") != "homepl-ftps"
            or transfer.get("method") != backup.get("method")
            or transfer.get("source_assertion") != HOMEPL_TRANSFER_SOURCE_ASSERTION
            or backup.get("remote_root") != "/"
            or transfer.get("remote_root") != backup.get("remote_root")
            or any(
                not (
                    preflight.get(field)
                    == transfer.get(field)
                    == root_mapping.get(field)
                    == backup.get(field)
                )
                for field in identity_fields
            )
            or transfer.get("backup_directory") != str(backup_directory)
            or transfer.get("manifest") != str(manifest_path)
            or transfer.get("manifest_sha256") != backup.get("manifest_sha256")
            or transfer.get("file_count") != backup.get("file_count")
            or transfer.get("total_bytes") != backup.get("total_bytes")
            or transfer.get("preflight_receipt") != str(preflight_path)
            or transfer.get("preflight_receipt_sha256") != backup.get("preflight_receipt_sha256")
            or transfer.get("root_mapping_receipt") != str(root_mapping_path)
            or transfer.get("root_mapping_receipt_sha256") != backup.get("root_mapping_receipt_sha256")
            or backup.get("root_mapping_observed_at") != root_mapping.get("observed_at")
            or any(
                preflight.get(field) != backup.get(field) or root_mapping.get(field) != preflight.get(field)
                for field in live_fields
            )
            or any(transfer.get(field) != preflight.get(field) for field in transfer_live_fields)
            or transfer.get("root_continuity_observed") is not True
            or transfer.get("transfer_start_root_listing_sha256") != root_mapping.get("listing_sha256")
            or transfer.get("transfer_start_root_listing_entry_count")
            != root_mapping.get("listing_entry_count")
            or transfer.get("transfer_start_root_index_sha256")
            != root_mapping.get("remote_root_index_sha256")
            or transfer.get("transfer_start_root_index_bytes") != root_mapping.get("remote_root_index_bytes")
            or transfer.get("transfer_end_root_listing_sha256") != root_mapping.get("listing_sha256")
            or transfer.get("transfer_end_root_listing_entry_count")
            != root_mapping.get("listing_entry_count")
            or transfer.get("transfer_end_root_index_sha256") != root_mapping.get("remote_root_index_sha256")
            or transfer.get("transfer_end_root_index_bytes") != root_mapping.get("remote_root_index_bytes")
            or len(root_index_rows) != 1
            or root_index_rows[0]["sha256"] != root_mapping.get("remote_root_index_sha256")
            or root_index_rows[0]["bytes"] != root_mapping.get("remote_root_index_bytes")
            or backup.get("served_root_continuity") != expected_continuity
            or transfer.get("backup_script") != str(backup_script)
            or transfer.get("backup_script_sha256") != _sha256_file(backup_script)
            or backup.get("backup_script") != str(backup_script)
            or backup.get("backup_script_sha256") != _sha256_file(backup_script)
            or transfer.get("source_tool") != "repo-read-only-ftps-script"
            or transfer.get("remote_operations") != ["ListDirectory", "GetFileSize", "DownloadFile"]
            or transfer.get("remote_write_methods_used") is not False
            or transfer.get("credentials_recorded") is not False
        ):
            raise WebsiteOperatorError("Verified backup provenance binding has changed.")

    def gate_deployment(
        self,
        audit_receipt: Path,
        package_receipt: Path,
        backup_receipt: Path,
        approval_receipt: Path,
        output: Path | None = None,
    ) -> Path:
        now = _utc_now()
        audit_path = audit_receipt.resolve()
        package_path = package_receipt.resolve()
        backup_path = backup_receipt.resolve()
        approval_path = approval_receipt.resolve()
        audit = _read_json(audit_path)
        self._require_receipt(audit, "audit")
        if audit.get("state") != "pass":
            raise WebsiteOperatorError("Audit receipt is blocked.")
        audit_age = now - _parse_datetime(audit.get("generated_at"), "audit.generated_at")
        if audit_age > timedelta(hours=float(self.config["deployment"]["audit_max_age_hours"])):
            raise WebsiteOperatorError("Audit receipt is stale.")
        package = self._validate_package_receipt(package_path)
        if package.get("audit_receipt_sha256") != _sha256_file(audit_path):
            raise WebsiteOperatorError("Package was not built from the supplied audit receipt.")
        backup = _read_json(backup_path)
        self._require_receipt(backup, "backup")
        if backup.get("state") != "verified-backup":
            raise WebsiteOperatorError("Backup receipt is not verified.")
        self._revalidate_backup_receipt(backup)
        if backup.get("remote_root") != self.config["deployment"]["remote_root"]:
            raise WebsiteOperatorError("Backup remote root does not match the deployment root.")
        backup_age = now - _parse_datetime(backup.get("observed_at"), "backup.observed_at")
        max_backup_age = timedelta(hours=float(self.config["deployment"]["backup_max_age_hours"]))
        if backup_age > max_backup_age:
            raise WebsiteOperatorError("Backup receipt is stale.")
        if backup.get("package_sha256") != package.get("package_sha256"):
            raise WebsiteOperatorError("Backup receipt is not bound to this exact deployment package.")
        approval = _read_json(approval_path)
        if approval.get("schema") != f"{SCHEMA_PREFIX}.owner-approval.v1":
            raise WebsiteOperatorError("Unsupported owner approval receipt schema.")
        if approval.get("decision") != "approved":
            raise WebsiteOperatorError("Owner approval decision is not approved.")
        if approval.get("scope") != "static-website-release":
            raise WebsiteOperatorError("Owner approval scope is not static-website-release.")
        if approval.get("package_sha256") != package.get("package_sha256"):
            raise WebsiteOperatorError("Owner approval is bound to another package.")
        approved_at = _parse_datetime(approval.get("approved_at"), "approval.approved_at")
        expires_at = _parse_datetime(approval.get("expires_at"), "approval.expires_at")
        if not approved_at <= now < expires_at:
            raise WebsiteOperatorError("Owner approval is not currently valid.")
        approval_max = timedelta(hours=float(self.config["deployment"]["approval_max_age_hours"]))
        if now - approved_at > approval_max:
            raise WebsiteOperatorError("Owner approval exceeds the maximum approval age.")
        if not str(approval.get("approved_by", "")).strip():
            raise WebsiteOperatorError("Owner approval must identify the approving owner.")
        backup_expiry = _parse_datetime(backup.get("observed_at"), "backup.observed_at") + max_backup_age
        gate_expiry = min(expires_at, backup_expiry)
        receipt = self._base_receipt("deployment-gate")
        receipt.update(
            {
                "state": "owner-approved-deploy-ready",
                "valid_until": _iso(gate_expiry),
                "audit_receipt": str(audit_path),
                "audit_receipt_sha256": _sha256_file(audit_path),
                "package_receipt": str(package_path),
                "package_receipt_sha256": _sha256_file(package_path),
                "package_sha256": package["package_sha256"],
                "backup_receipt": str(backup_path),
                "backup_receipt_sha256": _sha256_file(backup_path),
                "approval_receipt": str(approval_path),
                "approval_receipt_sha256": _sha256_file(approval_path),
                "remote_root": self.config["deployment"]["remote_root"],
                "rollback": backup["rollback"],
                "credentials_recorded": False,
                "automatic_rollback": False,
            }
        )
        return _atomic_write_json(self._path_for_output("deployment-gate", output), receipt)

    def _validate_gate(self, path: Path) -> tuple[Dict[str, Any], Dict[str, Any]]:
        gate = _read_json(path)
        self._require_receipt(gate, "deployment-gate")
        if gate.get("state") != "owner-approved-deploy-ready":
            raise WebsiteOperatorError("Deployment gate is not deploy-ready.")
        if _utc_now() >= _parse_datetime(gate.get("valid_until"), "gate.valid_until"):
            raise WebsiteOperatorError("Deployment gate has expired.")
        package_path = Path(str(gate.get("package_receipt", ""))).resolve()
        if _sha256_file(package_path) != gate.get("package_receipt_sha256"):
            raise WebsiteOperatorError("Deployment gate package receipt has changed.")
        package = self._validate_package_receipt(package_path)
        if package.get("package_sha256") != gate.get("package_sha256"):
            raise WebsiteOperatorError("Deployment gate package hash mismatch.")
        for key in ("audit_receipt", "backup_receipt", "approval_receipt"):
            receipt_path = Path(str(gate.get(key, ""))).resolve()
            expected_hash = gate.get(f"{key}_sha256")
            if not receipt_path.is_file() or _sha256_file(receipt_path) != expected_hash:
                raise WebsiteOperatorError(f"Deployment gate dependency changed: {key}")
        backup = _read_json(Path(str(gate["backup_receipt"])).resolve())
        self._revalidate_backup_receipt(backup)
        return gate, package

    def readback(
        self,
        package_receipt: Path,
        output: Path | None = None,
    ) -> Path:
        package = self._validate_package_receipt(package_receipt.resolve())
        result_path = self._path_for_output("live-readback-data")
        command = self._expand_command(
            self.config["deployment"]["readback_command"],
            {
                "manifest": str(package["manifest"]),
                "package": str(package["package"]),
                "output": str(result_path),
                "base_url": str(self.config["site"]["base_url"]),
            },
        )
        result = self.runner(command, self.repo_root)
        receipt = self._base_receipt("live-readback")
        receipt.update(
            {
                "state": "verified-live" if result.returncode == 0 else "readback-failed",
                "package_receipt": str(package_receipt.resolve()),
                "package_sha256": package["package_sha256"],
                "readback_data": str(result_path),
                "readback_data_sha256": _sha256_file(result_path) if result_path.is_file() else "",
                "returncode": result.returncode,
                "diagnostic": _short_output(result.stderr or result.stdout),
                "publication_complete": result.returncode == 0,
            }
        )
        receipt_path = _atomic_write_json(self._path_for_output("live-readback", output), receipt)
        if result.returncode != 0:
            raise WebsiteOperatorError(f"Live read-back failed; receipt: {receipt_path}")
        return receipt_path

    def _materialize_verified_deploy_inputs(
        self,
        package: Mapping[str, Any],
    ) -> Dict[str, Any]:
        """Copy exact validated release inputs into a controlled publish staging area."""

        package_sha256 = package.get("package_sha256")
        if not isinstance(package_sha256, str) or not re.fullmatch(
            r"[A-F0-9]{64}",
            package_sha256,
        ):
            raise WebsiteOperatorError("Validated package lost its exact release hash.")
        staging_root = self.receipts_dir / "deploy-inputs"
        staging_root.mkdir(parents=True, exist_ok=True)
        staging_root = _regular_directory(
            staging_root,
            label="Deployment-input staging root",
        )
        staging_directory = staging_root / f"{package_sha256}-{uuid.uuid4().hex}"
        try:
            staging_directory.mkdir()
        except FileExistsError as exc:
            raise WebsiteOperatorError("Refusing to reuse a deployment-input staging directory.") from exc
        staging_directory = _regular_directory(
            staging_directory,
            label="Deployment-input staging directory",
        )

        specifications = (
            (
                "package",
                "package_sha256",
                "package_bytes",
                f"release{Path(str(package.get('package', ''))).suffix.casefold() or '.zip'}",
            ),
            (
                "manifest",
                "manifest_sha256",
                None,
                f"manifest{Path(str(package.get('manifest', ''))).suffix.casefold() or '.csv'}",
            ),
            (
                "dependency_manifest",
                "dependency_manifest_sha256",
                None,
                "dependencies"
                f"{Path(str(package.get('dependency_manifest', ''))).suffix.casefold() or '.csv'}",
            ),
        )
        staged: Dict[str, Any] = {
            "state": "materialized-verified",
            "directory": str(staging_directory),
            "source_package_sha256": package_sha256,
        }
        for input_field, hash_field, size_field, destination_name in specifications:
            source_value = package.get(input_field)
            expected_hash = package.get(hash_field)
            if (
                not isinstance(source_value, str)
                or not Path(source_value).is_absolute()
                or not isinstance(expected_hash, str)
                or not re.fullmatch(r"[A-F0-9]{64}", expected_hash)
            ):
                raise WebsiteOperatorError(f"Validated deployment input is malformed: {input_field}")
            source = _regular_single_link_file(
                Path(source_value),
                label=f"Deployment source {input_field}",
            )
            expected_size = package.get(size_field) if size_field else source.stat().st_size
            if type(expected_size) is not int or expected_size < 0:
                raise WebsiteOperatorError(f"Validated deployment input size is malformed: {input_field}")
            if source.stat().st_size != expected_size or _sha256_file(source) != expected_hash:
                raise WebsiteOperatorError(f"Deployment source changed before staging: {input_field}")

            destination = staging_directory / destination_name
            digest = hashlib.sha256()
            copied_bytes = 0
            with source.open("rb") as input_stream:
                before = os.fstat(input_stream.fileno())
                if not stat.S_ISREG(before.st_mode) or int(before.st_nlink) != 1:
                    raise WebsiteOperatorError(
                        f"Deployment source is no longer a regular single-link file: {input_field}"
                    )
                try:
                    output_stream = destination.open("xb")
                except FileExistsError as exc:
                    raise WebsiteOperatorError(
                        f"Refusing to replace deployment staging input: {input_field}"
                    ) from exc
                with output_stream:
                    while True:
                        block = input_stream.read(1024 * 1024)
                        if not block:
                            break
                        output_stream.write(block)
                        digest.update(block)
                        copied_bytes += len(block)
                    output_stream.flush()
                    os.fsync(output_stream.fileno())
                after = os.fstat(input_stream.fileno())
            if (
                (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                or int(after.st_nlink) != 1
                or copied_bytes != expected_size
                or digest.hexdigest().upper() != expected_hash
            ):
                raise WebsiteOperatorError(f"Deployment source changed while staging: {input_field}")
            current_source = _regular_single_link_file(
                source,
                label=f"Deployment source {input_field}",
            )
            current_stat = current_source.stat()
            if (
                (current_stat.st_dev, current_stat.st_ino) != (after.st_dev, after.st_ino)
                or current_stat.st_size != expected_size
                or _sha256_file(current_source) != expected_hash
            ):
                raise WebsiteOperatorError(f"Deployment source path changed while staging: {input_field}")
            destination.chmod(stat.S_IREAD)
            verified_destination = _regular_single_link_file(
                destination,
                label=f"Staged deployment input {input_field}",
            )
            if (
                verified_destination.stat().st_size != expected_size
                or _sha256_file(verified_destination) != expected_hash
            ):
                raise WebsiteOperatorError(f"Staged deployment input failed verification: {input_field}")
            staged[input_field] = str(verified_destination)
            staged[hash_field] = expected_hash
            staged[f"{input_field}_bytes"] = expected_size
        staged["binding_sha256"] = _sha256_json(staged)
        return staged

    @staticmethod
    def _revalidate_deploy_inputs(staged: Mapping[str, Any]) -> None:
        for input_field, hash_field in (
            ("package", "package_sha256"),
            ("manifest", "manifest_sha256"),
            ("dependency_manifest", "dependency_manifest_sha256"),
        ):
            path_value = staged.get(input_field)
            expected_hash = staged.get(hash_field)
            expected_size = staged.get(f"{input_field}_bytes")
            if (
                not isinstance(path_value, str)
                or not Path(path_value).is_absolute()
                or not isinstance(expected_hash, str)
                or not re.fullmatch(r"[A-F0-9]{64}", expected_hash)
                or type(expected_size) is not int
                or expected_size < 0
            ):
                raise WebsiteOperatorError(f"Staged deployment input binding is malformed: {input_field}")
            path = _regular_single_link_file(
                Path(path_value),
                label=f"Staged deployment input {input_field}",
            )
            if path.stat().st_size != expected_size or _sha256_file(path) != expected_hash:
                raise WebsiteOperatorError(f"Staged deployment input changed: {input_field}")

    def deploy(
        self,
        gate_receipt: Path,
        confirm_package_sha256: str,
        execute: bool,
        output: Path | None = None,
    ) -> Path:
        gate_path = gate_receipt.resolve()
        gate, package = self._validate_gate(gate_path)
        if confirm_package_sha256.upper() != str(package["package_sha256"]).upper():
            raise WebsiteOperatorError("Exact package hash confirmation does not match.")
        deployment = self.config["deployment"]
        if execute:
            credential_names = [str(item) for item in deployment["credential_env_names"]]
            missing = [name for name in credential_names if not os.environ.get(name, "").strip()]
            if missing:
                raise WebsiteOperatorError(
                    "Runtime deployment credentials are missing: " + ", ".join(missing)
                )
        deploy_inputs = self._materialize_verified_deploy_inputs(package)
        self._revalidate_deploy_inputs(deploy_inputs)
        values = {
            "manifest": str(deploy_inputs["manifest"]),
            "package": str(deploy_inputs["package"]),
            "remote_root": str(deployment["remote_root"]),
        }
        command = self._expand_command(deployment["publish_command"], values)
        if execute:
            command.append("-Deploy")
        else:
            command.append("-VerifyOnly")
        publish_result = self.runner(command, self.repo_root)
        self._revalidate_deploy_inputs(deploy_inputs)
        readback_result: CommandResult | None = None
        readback_data_path: Path | None = None
        if execute and publish_result.returncode == 0:
            readback_data_path = self._path_for_output("post-deploy-readback-data")
            readback_command = self._expand_command(
                deployment["readback_command"],
                {
                    "manifest": str(deploy_inputs["manifest"]),
                    "package": str(deploy_inputs["package"]),
                    "output": str(readback_data_path),
                    "base_url": str(self.config["site"]["base_url"]),
                },
            )
            readback_result = self.runner(readback_command, self.repo_root)
        if publish_result.returncode != 0:
            state = "deployment-command-failed"
        elif not execute:
            state = "deployment-preflight-passed"
        elif readback_result is not None and readback_result.returncode == 0:
            state = "deployed-and-verified-live"
        else:
            state = "deployed-readback-failed"
        receipt = self._base_receipt("deployment")
        receipt.update(
            {
                "state": state,
                "execute": execute,
                "gate_receipt": str(gate_path),
                "gate_receipt_sha256": _sha256_file(gate_path),
                "package_sha256": package["package_sha256"],
                "deployment_inputs": deploy_inputs,
                "remote_root": deployment["remote_root"],
                "publish_returncode": publish_result.returncode,
                "readback_returncode": (readback_result.returncode if readback_result is not None else None),
                "readback_data": str(readback_data_path) if readback_data_path else "",
                "readback_data_sha256": (
                    _sha256_file(readback_data_path)
                    if readback_data_path is not None and readback_data_path.is_file()
                    else ""
                ),
                "credentials_recorded": False,
                "rollback": gate["rollback"],
                "live_readback_required": execute and state != "deployed-and-verified-live",
                "publication_complete": state == "deployed-and-verified-live",
                "diagnostic": {
                    "publish": _short_output(publish_result.stderr or publish_result.stdout),
                    "readback": (
                        _short_output(readback_result.stderr or readback_result.stdout)
                        if readback_result is not None
                        else ""
                    ),
                },
            }
        )
        receipt_path = _atomic_write_json(self._path_for_output("deployment", output), receipt)
        if publish_result.returncode != 0:
            raise WebsiteOperatorError(f"Deployment command failed; receipt: {receipt_path}")
        if execute and state != "deployed-and-verified-live":
            raise WebsiteOperatorError(f"Upload completed but live read-back failed; receipt: {receipt_path}")
        return receipt_path

    def capabilities_payload(self) -> Dict[str, Any]:
        deployment = self.config["deployment"]
        tools = []
        for identifier, category, path_key in (
            ("site-audit", "audit", None),
            ("live-surface-reconciliation", "observe", None),
            ("research-route-layout-attribution", "diagnose", None),
            ("owner-source-reconciliation", "reconcile", None),
            ("design-nexus-cycle", "design", None),
            ("release-builder", "build", None),
            ("homepl-backup", "backup", "backup_script"),
            ("homepl-publish", "deploy", "publish_script"),
            ("live-hash-readback", "verify", "readback_script"),
        ):
            path = (
                _safe_repo_path(self.repo_root, deployment[path_key])
                if path_key
                else Path(__file__).resolve()
            )
            tools.append(
                {
                    "id": identifier,
                    "category": category,
                    "available": path.is_file(),
                    "path": str(path),
                }
            )
        governance_path = _safe_repo_path(
            self.repo_root,
            "aureon/operator/design_investor_copy_governance.py",
        )
        tools.append(
            {
                "id": "investor-copy-governance",
                "category": "governance",
                "available": governance_path.is_file(),
                "path": str(governance_path),
            }
        )
        try:
            from aureon.operator.design_capability_registry import (
                investor_copy_governance_readiness,
            )

            governance_readiness = investor_copy_governance_readiness(self.repo_root)
        except Exception as exc:
            governance_readiness = {
                "available": False,
                "state": "unavailable",
                "decision_verification_available": False,
                "simulation_available": False,
                "apply_protocol_available": False,
                "implementation_tooling_verified": False,
                "exact_owner_decision_required": True,
                "autonomous_owner_decision": False,
                "broad_access_approval_valid": False,
                "current_owner_decision_present": False,
                "current_apply_authorised": False,
                "current_apply_ready": False,
                "website_mutation": "never",
                "policy_mutation": "never",
                "candidate_authority": "none",
                "package_authority": "none",
                "release_eligible": False,
                "deployment_authority": "none",
                "error": f"{type(exc).__name__}: {exc}",
            }
        return {
            "schema": f"{SCHEMA_PREFIX}.capabilities.v1",
            "generated_at": _iso(),
            "operator": "Aureon OS",
            "tools": tools,
            "investor_copy_governance": governance_readiness,
            "lifecycle": [
                "inventory",
                "live-surface-reconciliation",
                "research-route-layout-attribution",
                "owner-source-reconciliation",
                "audit",
                "design-cycle",
                "work-order",
                "reconciled-candidate-work-order",
                "build-release",
                "backup-preflight",
                "verify-backup",
                "owner-gate",
                "deploy-preflight",
                "explicit-deploy",
                "live-readback",
            ],
            "hard_boundaries": [
                "No credentials in configuration or receipts.",
                "No deployment without a verified current backup.",
                "No deployment without short-lived owner approval bound to the package hash.",
                "No automatic rollback or deletion.",
                "Hosting capacity is never treated as a target to fill.",
                "Harmonic feedback is an operational design-control pattern, not aesthetic or scientific proof.",
                "No packaging without a current full design-cycle pass and identified human visual acceptance.",
                "No packaging without a current hash-bound composite visual gate PASS.",
                "No autonomous candidate after observed live drift without a current owner source decision bound to a verified backup.",
                "Broad system-access approval is not an investor-copy governance decision.",
                "Investor-copy governance verification and shadow simulation are read-only; exact three-file apply requires a fresh immutable named-owner decision plus explicit apply and grants no website, package, release, or deployment authority.",
                "Research route attribution is a non-gating, runtime-only diagnostic and cannot establish causation or release eligibility.",
                "Material brand changes require human visual acceptance before baseline promotion.",
            ],
        }


def _add_common_output(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output", type=Path, help="Write the timestamped JSON receipt here.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aureon-website",
        description="Audit, prepare and owner-gate the Aureon public website.",
    )
    parser.add_argument("--repo-root", type=Path, help="Aureon repository root.")
    parser.add_argument("--config", type=Path, help="Operator config JSON.")
    parser.add_argument("--receipts-dir", type=Path, help="Default local receipt directory.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory = subparsers.add_parser("inventory", help="Observe local website and hosting context.")
    _add_common_output(inventory)

    live_drift = subparsers.add_parser(
        "live-drift",
        help="Read-only canonical-source to public-HTTPS reconciliation; never deploys.",
    )
    live_drift.add_argument(
        "--route",
        action="append",
        default=[],
        help="Public route (/research/) or website-relative HTML route; repeat for multiple routes.",
    )
    _add_common_output(live_drift)

    research_attribution = subparsers.add_parser(
        "research-attribution",
        help="Run one local, non-gating Research route layout attribution capture.",
    )
    research_attribution.add_argument(
        "--source-root",
        type=Path,
        help="Canonical website/ or a staged artifacts/website-candidates/*/website tree.",
    )

    audit = subparsers.add_parser("audit", help="Run metadata, ethos, budget and static checks.")
    audit.add_argument("--skip-external", action="store_true", help="Skip configured Node/PowerShell checks.")
    _add_common_output(audit)

    design_cycle = subparsers.add_parser(
        "design-cycle",
        help="Build a local-only benchmark, design-council and feedback-loop receipt.",
    )
    design_cycle.add_argument("--goal", required=True)
    design_cycle.add_argument(
        "--route",
        action="append",
        default=[],
        help="Public route (/research/) or website-relative HTML route; repeat for multiple routes.",
    )
    design_cycle.add_argument("--previous-cycle", type=Path)
    design_cycle.add_argument(
        "--skip-external",
        action="store_true",
        help="Diagnostic only: skip external checks and force release eligibility to fail.",
    )
    _add_common_output(design_cycle)

    work_order = subparsers.add_parser("work-order", help="Turn an audit into bounded remediation tasks.")
    work_order.add_argument("--audit-receipt", type=Path, required=True)
    _add_common_output(work_order)

    candidate_work_order = subparsers.add_parser(
        "candidate-work-order",
        help="Create a reconciled, staged-only V30+ candidate work order; never applies or deploys.",
    )
    candidate_work_order.add_argument("--goal", required=True)
    candidate_work_order.add_argument("--allow", action="append", required=True, dest="allowed_paths")
    candidate_work_order.add_argument("--route", action="append", required=True, dest="routes")
    candidate_work_order.add_argument("--reconciliation-receipt", type=Path, required=True)
    candidate_work_order.add_argument("--owner-source-decision", type=Path)
    candidate_work_order.add_argument("--backup-receipt", type=Path)
    candidate_work_order.add_argument("--run-id")
    _add_common_output(candidate_work_order)

    candidate_visual_review = subparsers.add_parser(
        "candidate-visual-review",
        help="Verify local-only pre-promotion visual evidence for one staged candidate.",
    )
    candidate_visual_review.add_argument("--candidate-receipt", type=Path, required=True)
    candidate_visual_review.add_argument("--capture-receipt", type=Path, required=True)
    candidate_visual_review.add_argument("--manual-review", type=Path, required=True)
    candidate_visual_review.add_argument("--human-acceptance", type=Path, required=True)
    _add_common_output(candidate_visual_review)

    candidate_learning = subparsers.add_parser(
        "candidate-learning",
        help="Record a local-only, human-reviewed staged pattern as a proposed Design Suite skill update.",
    )
    candidate_learning.add_argument("--candidate-receipt", type=Path, required=True)
    candidate_learning.add_argument("--visual-review", type=Path, required=True)
    candidate_learning.add_argument("--learning-manifest", type=Path, required=True)
    _add_common_output(candidate_learning)

    build = subparsers.add_parser(
        "build",
        help="Build and verify a release from passing audit/design receipts and visual acceptance.",
    )
    build.add_argument("--audit-receipt", type=Path, required=True)
    build.add_argument("--design-cycle-receipt", type=Path, required=True)
    build.add_argument(
        "--human-visual-accepted",
        action="store_true",
        help="Record explicit human visual acceptance for this exact source-bound design cycle.",
    )
    build.add_argument(
        "--human-visual-accepted-by",
        required=True,
        help="Identify the human reviewer who visually accepted this exact source tree.",
    )
    build.add_argument("--output-directory", type=Path, required=True)
    _add_common_output(build)

    backup_preflight = subparsers.add_parser(
        "backup-preflight",
        help="Check safe backup prerequisites without transferring files.",
    )
    backup_preflight.add_argument("--output-directory", type=Path, required=True)
    backup_preflight.add_argument(
        "--ftp-host",
        required=True,
        help="Exact non-secret Home.pl FTPS hostname, with optional port.",
    )
    backup_preflight.add_argument(
        "--ftp-account",
        required=True,
        help="Exact non-secret Home.pl FTPS account identifier; only its SHA-256 is recorded.",
    )
    backup_preflight.add_argument(
        "--live-reconciliation-receipt",
        type=Path,
        required=True,
        help="Fresh public HTTPS reconciliation used for served-root byte mapping.",
    )
    _add_common_output(backup_preflight)

    verify_backup = subparsers.add_parser(
        "verify-backup",
        help="Verify a completed Home.pl backup and emit rollback metadata.",
    )
    verify_backup.add_argument("--backup-directory", type=Path, required=True)
    verify_backup.add_argument("--manifest", type=Path, required=True)
    verify_backup.add_argument("--preflight-receipt", type=Path, required=True)
    verify_backup.add_argument("--transfer-receipt", type=Path, required=True)
    verify_backup.add_argument("--method", choices=("homepl-ftps",), required=True)
    verify_backup.add_argument(
        "--observed-at",
        help=(
            "Optional independent observation time; when supplied it must exactly match "
            "the transfer receipt completion time."
        ),
    )
    verify_backup.add_argument("--package-receipt", type=Path)
    _add_common_output(verify_backup)

    gate = subparsers.add_parser("gate", help="Validate backup and owner approval for one package.")
    gate.add_argument("--audit-receipt", type=Path, required=True)
    gate.add_argument("--package-receipt", type=Path, required=True)
    gate.add_argument("--backup-receipt", type=Path, required=True)
    gate.add_argument("--approval-receipt", type=Path, required=True)
    _add_common_output(gate)

    deploy = subparsers.add_parser(
        "deploy",
        help="Verify by default; upload only with --execute and a valid owner gate.",
    )
    deploy.add_argument("--gate-receipt", type=Path, required=True)
    deploy.add_argument("--confirm-package-sha256", required=True)
    deploy.add_argument("--execute", action="store_true")
    _add_common_output(deploy)

    readback = subparsers.add_parser("readback", help="Hash-verify the manifest against the live domain.")
    readback.add_argument("--package-receipt", type=Path, required=True)
    _add_common_output(readback)

    subparsers.add_parser("capabilities", help="Print the bounded website tool belt.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        operator = WebsiteOperator.from_paths(
            repo_root=args.repo_root,
            config_path=args.config,
            receipts_dir=args.receipts_dir,
        )
        result: Path | Dict[str, Any]
        if args.command == "inventory":
            result = operator.inventory(args.output)
        elif args.command == "live-drift":
            result = operator.observe_live_surface(routes=args.route or None, output=args.output)
        elif args.command == "research-attribution":
            result = operator.research_hydration_attribution(args.source_root)
        elif args.command == "audit":
            result = operator.audit(args.output, run_external=not args.skip_external)
        elif args.command == "design-cycle":
            result = operator.design_cycle(
                goal=args.goal,
                output=args.output,
                routes=args.route or None,
                run_external=not args.skip_external,
                previous_cycle=args.previous_cycle,
            )
        elif args.command == "work-order":
            result = operator.work_order(args.audit_receipt, args.output)
        elif args.command == "candidate-work-order":
            result = operator.create_candidate_work_order(
                goal=args.goal,
                allowed_paths=args.allowed_paths,
                routes=args.routes,
                reconciliation_receipt=args.reconciliation_receipt,
                owner_source_decision=args.owner_source_decision,
                backup_receipt=args.backup_receipt,
                run_id=args.run_id,
                output=args.output,
            )
        elif args.command == "candidate-visual-review":
            result = operator.verify_candidate_prepromotion_review(
                args.candidate_receipt,
                args.capture_receipt,
                args.manual_review,
                args.human_acceptance,
                output=args.output,
            )
        elif args.command == "candidate-learning":
            result = operator.record_design_learning(
                args.candidate_receipt,
                args.visual_review,
                args.learning_manifest,
                output=args.output,
            )
        elif args.command == "build":
            result = operator.build_release(
                args.audit_receipt,
                args.output_directory,
                args.output,
                design_cycle_receipt=args.design_cycle_receipt,
                human_visual_accepted=args.human_visual_accepted,
                human_visual_accepted_by=args.human_visual_accepted_by,
            )
        elif args.command == "backup-preflight":
            result = operator.backup_preflight(
                args.output_directory,
                args.ftp_host,
                args.ftp_account,
                args.live_reconciliation_receipt,
                args.output,
            )
        elif args.command == "verify-backup":
            result = operator.verify_backup(
                args.backup_directory,
                args.manifest,
                args.method,
                args.observed_at,
                args.package_receipt,
                args.output,
                preflight_receipt=args.preflight_receipt,
                transfer_receipt=args.transfer_receipt,
            )
        elif args.command == "gate":
            result = operator.gate_deployment(
                args.audit_receipt,
                args.package_receipt,
                args.backup_receipt,
                args.approval_receipt,
                args.output,
            )
        elif args.command == "deploy":
            result = operator.deploy(
                args.gate_receipt,
                args.confirm_package_sha256,
                args.execute,
                args.output,
            )
        elif args.command == "readback":
            result = operator.readback(args.package_receipt, args.output)
        elif args.command == "capabilities":
            result = operator.capabilities_payload()
        else:
            parser.error(f"Unsupported command: {args.command}")
            return 2
        if isinstance(result, Path):
            output_payload: Dict[str, Any] = {"receipt": str(result)}
            if args.command == "live-drift":
                live_drift = _read_json(result)
                output_payload.update(
                    {
                        "state": live_drift.get("state"),
                        "passed": live_drift.get("passed"),
                        "release_eligible": False,
                        "deployment_authority": "none",
                    }
                )
            print(json.dumps(output_payload, indent=2))
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        if args.command == "audit" and isinstance(result, Path):
            audit = _read_json(result)
            return 0 if audit.get("state") == "pass" else 2
        if args.command == "live-drift" and isinstance(result, Path):
            live_drift = _read_json(result)
            return 0 if live_drift.get("passed") is True else 2
        return 0
    except WebsiteOperatorError as exc:
        print(json.dumps({"error": str(exc), "state": "blocked"}, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
