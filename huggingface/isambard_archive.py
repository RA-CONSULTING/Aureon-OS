"""Resumable, gated Isambard archive inventory and Hugging Face transfer.

The scanner never follows symlinks and never modifies a source.  Absolute source
paths are confined to the SQLite state; public manifests contain logical roots
and repository-relative paths only.  Importing this module does not import
``huggingface_hub`` and does not read an access token.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import hmac
import importlib
import json
import os
import re
import sqlite3
import stat
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Iterator, Mapping, Sequence

DATA_REPO = "GaryLeckey/aureon-isambard-data"
RUNS_REPO = "GaryLeckey/aureon-isambard-runs"
ARCHIVE_REPO = "GaryLeckey/aureon-isambard-archive"
ALLOWED_REPOS = frozenset({DATA_REPO, RUNS_REPO, ARCHIVE_REPO})
TOKEN_NAMES = ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN")
PUBLIC_ACK = "I_UNDERSTAND_THIS_IS_PUBLIC"
PARTIAL_ACK = "I_APPROVE_A_PARTIAL_RELEASE"
SCAN_POLICY_VERSION = 1
DEFAULT_MAX_FILES = 100
DEFAULT_MAX_BATCH_BYTES = 1024**3
DEFAULT_LARGE_FILE_BYTES = 256 * 1024**2
_CHUNK_BYTES = 8 * 1024**2
_SCAN_OVERLAP = 4096


class ArchiveError(RuntimeError):
    """Base error for a refused or incomplete transfer."""


class SourceChangedError(ArchiveError):
    """A source changed while it was being read."""


class BatchUploadError(ArchiveError):
    """A batch failed; verified earlier batches remain recorded."""


class FinalVerificationError(ArchiveError):
    """Final verification found blockers, missing files, or hash mismatches."""

    def __init__(self, message: str, summary: Mapping[str, Any]):
        super().__init__(message)
        self.summary = dict(summary)


@dataclass(frozen=True)
class SourceSpec:
    """A local source and its stable, public logical name."""

    key: str
    path: Path

    def __post_init__(self) -> None:
        if self.key not in {"pretrain", "hnc-organism"}:
            raise ValueError(f"unsupported source key: {self.key}")
        object.__setattr__(self, "path", Path(self.path).expanduser().absolute())


@dataclass(frozen=True)
class Destination:
    repo_id: str
    destination: str


@dataclass(frozen=True)
class FileFilter:
    """Small-pilot filters; patterns apply to source-relative POSIX paths."""

    globs: tuple[str, ...] = ()
    contains: tuple[str, ...] = ()
    max_files: int | None = None
    max_bytes: int | None = None

    def __post_init__(self) -> None:
        if self.max_files is not None and self.max_files <= 0:
            raise ValueError("max_files must be positive")
        if self.max_bytes is not None and self.max_bytes <= 0:
            raise ValueError("max_bytes must be positive")

    def matches(self, relative_path: str) -> bool:
        if self.globs and not any(fnmatch.fnmatchcase(relative_path, p) for p in self.globs):
            return False
        return not self.contains or any(part in relative_path for part in self.contains)


@dataclass(frozen=True)
class SecurityDecision:
    status: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class Batch:
    files: tuple[sqlite3.Row, ...]

    @property
    def byte_count(self) -> int:
        return sum(int(row["size"]) for row in self.files)


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_within(path: Path, root: Path) -> bool:
    try:
        return os.path.commonpath((str(path.absolute()), str(root.absolute()))) == str(root.absolute())
    except ValueError:
        return False


def default_sources(
    pretrain_root: str | os.PathLike[str] = "/projects/u6vs/pretrain",
    hnc_root: str | os.PathLike[str] = "/projects/u6vs/hnc-organism",
) -> tuple[SourceSpec, SourceSpec]:
    return SourceSpec("pretrain", Path(pretrain_root)), SourceSpec("hnc-organism", Path(hnc_root))


def map_destination(source_key: str, relative_path: str | os.PathLike[str]) -> Destination:
    """Apply the complete source mapping, including canonical model artifacts."""

    relative = PurePosixPath(str(relative_path).replace("\\", "/"))
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError("source-relative path must be a safe, non-empty relative path")
    value = relative.as_posix()
    if source_key == "pretrain":
        return Destination(DATA_REPO, f"pretrain/{value}")
    if source_key != "hnc-organism":
        raise ValueError(f"unsupported source key: {source_key}")
    if value == "runs" or value.startswith("runs/"):
        return Destination(RUNS_REPO, value)
    if (
        value.startswith("training/sft/")
        or value in {"training/aureon_tokenizer.json", "training/aureon_tokenizer.report.json"}
    ):
        return Destination(DATA_REPO, value)
    # There is deliberately no canonical-model exception in the full archive.
    return Destination(ARCHIVE_REPO, f"hnc-organism/{value}")


def classify_license(source_key: str, relative_path: str) -> dict[str, str]:
    """Return conservative provenance and release obligations for one path."""

    value = relative_path.replace("\\", "/").lower()
    normalized = re.sub(r"[_\s]+", "-", value)
    if "fineweb-edu" in normalized or "fineweb-edu" in value:
        return {
            "provenance": "FineWeb-Edu / CommonCrawl",
            "provenance_status": "known_third_party",
            "license": "ODC-BY-1.0",
            "license_status": "approved_with_obligations",
            "license_reason": "Requires FineWeb-Edu attribution and compliance with CommonCrawl terms.",
        }
    if "fineweb" in normalized:
        return {
            "provenance": "FineWeb / CommonCrawl",
            "provenance_status": "known_third_party",
            "license": "ODC-BY-1.0",
            "license_status": "approved_with_obligations",
            "license_reason": "Requires FineWeb attribution and compliance with CommonCrawl terms.",
        }
    if "smollm-corpus" in normalized and "python-edu" in normalized:
        return {
            "provenance": "SmolLM-Corpus python-edu / The Stack",
            "provenance_status": "known_third_party",
            "license": "ODC-BY-1.0",
            "license_status": "approved_with_obligations",
            "license_reason": "Requires ODC-BY attribution and preservation of The Stack provenance.",
        }
    if normalized == "data/code-python-edu" or normalized.startswith("data/code-python-edu/"):
        return {
            "provenance": "SmolLM-Corpus python-edu / Software Heritage / The Stack",
            "provenance_status": "known_third_party",
            "license": "varied per source file",
            "license_status": "blocked",
            "license_reason": (
                "The upstream python-edu files are metadata; downloaded source text "
                "requires The Stack per-file redistribution review."
            ),
        }
    if normalized == "data/code" or normalized.startswith("data/code/"):
        return {
            "provenance": "CodeParrot Clean",
            "provenance_status": "known_third_party",
            "license": "per-row / unspecified card-wide",
            "license_status": "blocked",
            "license_reason": "CodeParrot has no card-wide license; raw data and code require documented review.",
        }
    if "codeparrot" in normalized:
        return {
            "provenance": "CodeParrot",
            "provenance_status": "known_third_party",
            "license": "unspecified",
            "license_status": "blocked",
            "license_reason": "CodeParrot has no card-wide license; raw data and code require documented review.",
        }
    if re.search(r"(?:^|[/._-])the-?stack(?:$|[/._-])", normalized) or "thestack" in normalized:
        return {
            "provenance": "The Stack",
            "provenance_status": "gated_third_party",
            "license": "gated / varied",
            "license_status": "blocked",
            "license_reason": "The Stack gated content is blocked by default; per-file rights and authorization are unresolved.",
        }
    hnc_review_roots = {
        "cache": "Download/cache content requires source and license review.",
        "containers": "Third-party container images have their own licenses and redistribution terms.",
        "corpus": "Raw corpus content requires per-source redistribution and privacy review.",
        "github": "GitHub snapshots require repository-specific provenance and license review.",
        "hf": "Hub cache content requires source, credential, and license review.",
        "hf_cache": "Hub cache content requires source, credential, and license review.",
        "models": "Third-party model files require model-specific license review.",
        "runtime": "Runtime state requires credential, session, and personal-data review.",
        "tmp": "Temporary state requires credential, session, and personal-data review.",
        "venvs": "Installed package contents have varied licenses and require redistribution review.",
    }
    first_part = PurePosixPath(value).parts[0]
    if source_key == "hnc-organism" and first_part in hnc_review_roots:
        return {
            "provenance": "mixed or operational archive content",
            "provenance_status": "review_required",
            "license": "unknown / varied",
            "license_status": "blocked",
            "license_reason": hnc_review_roots[first_part],
        }
    if source_key == "pretrain" or re.search(r"(?:^|/)(?:third[-_]?party|external|vendor|datasets)(?:/|$)", normalized):
        return {
            "provenance": "unknown third-party",
            "provenance_status": "unknown",
            "license": "unknown",
            "license_status": "blocked",
            "license_reason": "Unknown third-party provenance blocks release; no redistribution rights are assumed.",
        }
    return {
        "provenance": "Aureon/HNC project source",
        "provenance_status": "project_original",
        "license": "MIT",
        "license_status": "approved",
        "license_reason": "Project-original material follows the repository license; embedded third-party content still requires review.",
    }


_ENV_ALLOWLIST_NAMES = frozenset({".env.example", ".env.template", ".env.sample", "example.env", "template.env", "sample.env"})
_PRIVATE_KEY_NAMES = {
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "identity",
    "private.key",
    "private_key",
    "private.pem",
}
_CREDENTIAL_NAMES = {
    ".netrc",
    ".pgpass",
    ".git-credentials",
    ".hf_token",
    "credentials",
    "credentials.json",
    "credential.json",
    "auth.json",
    "cookies",
    "cookies.sqlite",
    "cookies.sqlite3",
    "token",
    "token.json",
    "session",
    "session.json",
    "session.yaml",
    "session.yml",
    ".bash_history",
    ".zsh_history",
    ".python_history",
}
_SPECIFIC_SECRET_PATTERNS = (
    ("embedded_private_key", re.compile(rb"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----")),
    ("huggingface_token", re.compile(rb"\bhf_[A-Za-z0-9]{28,}\b")),
    ("aws_access_key", re.compile(rb"\b(?:AKIA|ASIA|ABIA|ACCA)[A-Z0-9]{16}\b")),
    ("github_token", re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b")),
    ("openai_token", re.compile(rb"\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}\b")),
    ("slack_token", re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{16,}\b")),
    ("google_api_key", re.compile(rb"\bAIza[A-Za-z0-9_-]{30,}\b")),
)
_GENERIC_SECRET = re.compile(
    rb"(?i)(?:api[_-]?key|access[_-]?token|auth[_-]?token|secret[_-]?key|client[_-]?secret|password)"
    rb"\s*[=:]\s*[\"']?([^\s\"',;]{16,})"
)
_PLACEHOLDER = re.compile(
    rb"(?i)(?:placeholder|example|sample|dummy|redacted|replace|change[-_]?me|your[-_]|xxxx|\$\{|<[^>]+>)"
)


def filename_security_findings(relative_path: str) -> list[str]:
    parts = PurePosixPath(relative_path.replace("\\", "/")).parts
    lowered = [part.lower() for part in parts]
    name = lowered[-1]
    findings: list[str] = []
    if ".git" in lowered:
        # Compressed objects and packed history cannot be cleared by scanning
        # the compressed bytes. Publish reviewed Git history through GitHub,
        # not as unreviewed raw repository internals.
        findings.append("version_control_internals")
    if (name == ".env" or name.startswith(".env.") or name.endswith(".env")) and name not in _ENV_ALLOWLIST_NAMES:
        findings.append("dotenv_file")
    if ".ssh" in lowered[:-1] or name in _PRIVATE_KEY_NAMES or name.endswith((".ppk", ".p12", ".pfx")):
        findings.append("ssh_or_private_key_material")
    if name.endswith((".key", ".pem")) and "public" not in name and not name.endswith((".pub.pem",)):
        findings.append("potential_private_key_file")
    if name in _CREDENTIAL_NAMES or name.endswith((".session", ".session-journal")):
        findings.append("session_or_credential_material")
    cloud_directory = (
        any(part in {".aws", ".azure"} for part in lowered[:-1])
        or any(lowered[index : index + 2] == [".config", "gcloud"] for index in range(len(lowered) - 2))
    )
    if cloud_directory:
        findings.append("cloud_credential_material")
    return sorted(set(findings))


def _content_security_findings(chunks: Iterable[bytes]) -> list[str]:
    findings: set[str] = set()
    tail = b""
    for chunk in chunks:
        data = tail + chunk
        for reason, pattern in _SPECIFIC_SECRET_PATTERNS:
            if reason not in findings and pattern.search(data):
                findings.add(reason)
        if "generic_credential_assignment" not in findings:
            for match in _GENERIC_SECRET.finditer(data):
                if not _PLACEHOLDER.search(match.group(1)):
                    findings.add("generic_credential_assignment")
                    break
        tail = data[-_SCAN_OVERLAP:]
    return sorted(findings)


def scan_content_security(chunks: Iterable[bytes]) -> SecurityDecision:
    """Scan bytes without returning or logging any matched value."""

    findings = _content_security_findings(chunks)
    return SecurityDecision("blocked" if findings else "clean", tuple(findings))


def _stat_fingerprint(value: os.stat_result) -> tuple[int, int, int, int]:
    return (int(value.st_size), int(value.st_mtime_ns), int(value.st_dev), int(value.st_ino))


def _hash_and_scan(path: Path) -> tuple[str, str, SecurityDecision, os.stat_result, os.stat_result]:
    """Hash SHA-256 and Git blob SHA-1 in one no-follow read, checking stability."""

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as handle:
        opened = os.fstat(handle.fileno())
        if not stat.S_ISREG(opened.st_mode):
            raise SourceChangedError("source is no longer a regular file")
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or _stat_fingerprint(before) != _stat_fingerprint(opened):
            raise SourceChangedError("source changed before hashing")
        sha256 = hashlib.sha256()
        blob = hashlib.sha1()
        blob.update(f"blob {opened.st_size}\0".encode("ascii"))

        def reading_chunks() -> Iterator[bytes]:
            while True:
                chunk = handle.read(_CHUNK_BYTES)
                if not chunk:
                    break
                sha256.update(chunk)
                blob.update(chunk)
                yield chunk

        decision = scan_content_security(reading_chunks())
        after = path.lstat()
        final = os.fstat(handle.fileno())
        if (
            not stat.S_ISREG(after.st_mode)
            or _stat_fingerprint(after) != _stat_fingerprint(before)
            or _stat_fingerprint(final) != _stat_fingerprint(opened)
        ):
            raise SourceChangedError("source changed during hashing")
        return sha256.hexdigest(), blob.hexdigest(), decision, before, after


class ArchiveState:
    """SQLite resume state stored strictly outside every source root."""

    def __init__(self, path: str | os.PathLike[str], sources: Sequence[SourceSpec] | None = None):
        self.path = Path(path).expanduser().absolute()
        # Refuse an in-source state before creating the DB or its WAL sidecars.
        self.sources = tuple(sources or ())
        if self.sources:
            self._check_outside_sources(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self._create_schema()
        if sources is None:
            self.sources = self._load_sources()
        if not self.sources:
            raise ValueError("source roots are required for a new state database")
        self._check_outside_sources(self.path)
        self._save_sources()

    def _create_schema(self) -> None:
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY,
                local_path TEXT NOT NULL UNIQUE,
                source_key TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                size INTEGER NOT NULL,
                mtime_ns INTEGER NOT NULL,
                sha256 TEXT,
                git_blob_sha1 TEXT,
                repo_id TEXT NOT NULL,
                destination TEXT NOT NULL,
                provenance TEXT NOT NULL,
                provenance_status TEXT NOT NULL,
                license TEXT NOT NULL,
                license_status TEXT NOT NULL,
                license_reason TEXT NOT NULL,
                security_status TEXT NOT NULL,
                security_reasons TEXT NOT NULL,
                status TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                last_seen_generation INTEGER NOT NULL,
                scan_policy_version INTEGER NOT NULL,
                review_status TEXT,
                review_reason TEXT,
                reviewer TEXT,
                revision TEXT,
                verification_status TEXT,
                verified_at TEXT,
                remote_sha256 TEXT,
                remote_blob_sha1 TEXT,
                remote_size INTEGER,
                upload_attempts INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                UNIQUE(repo_id, destination)
            );
            CREATE TABLE IF NOT EXISTS symlinks (
                id INTEGER PRIMARY KEY,
                local_path TEXT NOT NULL UNIQUE,
                source_key TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                target TEXT NOT NULL,
                target_is_absolute INTEGER NOT NULL,
                link_kind TEXT NOT NULL,
                mtime_ns INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                last_seen_generation INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS batches (
                id INTEGER PRIMARY KEY,
                repo_id TEXT NOT NULL,
                status TEXT NOT NULL,
                file_count INTEGER NOT NULL,
                byte_count INTEGER NOT NULL,
                revision TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS batch_files (
                batch_id INTEGER NOT NULL REFERENCES batches(id),
                file_id INTEGER NOT NULL REFERENCES files(id),
                PRIMARY KEY(batch_id, file_id)
            );
            """
        )
        self.db.commit()

    def _load_sources(self) -> tuple[SourceSpec, ...]:
        row = self.db.execute("SELECT value FROM metadata WHERE key='sources'").fetchone()
        if row is None:
            return ()
        return tuple(SourceSpec(item["key"], Path(item["path"])) for item in json.loads(row["value"]))

    def _save_sources(self) -> None:
        value = json.dumps([{"key": source.key, "path": str(source.path)} for source in self.sources])
        self.db.execute(
            "INSERT INTO metadata(key,value) VALUES('sources',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (value,),
        )
        self.db.commit()

    def _check_outside_sources(self, path: Path) -> None:
        for source in self.sources:
            physical_path = path.resolve(strict=False)
            physical_root = source.path.resolve(strict=False)
            if _is_within(path, source.path) or _is_within(physical_path, physical_root):
                raise ArchiveError(f"state or export path must be outside source root {source.key}")

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> ArchiveState:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _next_generation(self) -> int:
        row = self.db.execute("SELECT value FROM metadata WHERE key='generation'").fetchone()
        generation = int(row["value"]) + 1 if row else 1
        self.db.execute(
            "INSERT INTO metadata(key,value) VALUES('generation',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(generation),),
        )
        self.db.execute(
            "INSERT INTO metadata(key,value) VALUES('scan_in_progress','1') "
            "ON CONFLICT(key) DO UPDATE SET value='1'"
        )
        self.db.commit()
        return generation

    @property
    def scan_in_progress(self) -> bool:
        row = self.db.execute("SELECT value FROM metadata WHERE key='scan_in_progress'").fetchone()
        return bool(row and row["value"] == "1")

    @staticmethod
    def _blocked(row: Mapping[str, Any] | sqlite3.Row) -> bool:
        return bool(
            row["security_status"] != "clean"
            or (row["license_status"] == "blocked" and row["review_status"] != "approved")
        )

    def _base_values(self, record: Mapping[str, Any], generation: int) -> dict[str, Any]:
        values = dict(record)
        values["last_seen_generation"] = generation
        values["scan_policy_version"] = SCAN_POLICY_VERSION
        values["active"] = 1
        values["status"] = (
            "blocked"
            if values["security_status"] != "clean" or values["license_status"] == "blocked"
            else "approved"
        )
        return values

    def _upsert_file(self, record: Mapping[str, Any], generation: int, *, unchanged: bool) -> None:
        values = self._base_values(record, generation)
        if unchanged:
            assignments = (
                "source_key=:source_key, relative_path=:relative_path, size=:size, mtime_ns=:mtime_ns, "
                "repo_id=:repo_id, destination=:destination, provenance=:provenance, "
                "provenance_status=:provenance_status, license=:license, license_status=:license_status, "
                "license_reason=:license_reason, status=:status, active=1, "
                "last_seen_generation=:last_seen_generation, scan_policy_version=:scan_policy_version, "
                "last_error=NULL"
            )
            values["local_path"] = record["local_path"]
            self.db.execute(f"UPDATE files SET {assignments} WHERE local_path=:local_path", values)
            return
        columns = (
            "local_path", "source_key", "relative_path", "size", "mtime_ns", "sha256", "git_blob_sha1",
            "repo_id", "destination", "provenance", "provenance_status", "license", "license_status",
            "license_reason", "security_status", "security_reasons", "status", "active",
            "last_seen_generation", "scan_policy_version",
        )
        placeholders = ",".join(f":{column}" for column in columns)
        updates = ",".join(f"{column}=excluded.{column}" for column in columns if column != "local_path")
        self.db.execute(
            f"INSERT INTO files({','.join(columns)}) VALUES({placeholders}) "
            f"ON CONFLICT(local_path) DO UPDATE SET {updates}, revision=NULL, verification_status=NULL, "
            "verified_at=NULL, remote_sha256=NULL, remote_blob_sha1=NULL, remote_size=NULL, last_error=NULL",
            values,
        )

    def upsert_symlink(self, record: Mapping[str, Any], generation: int) -> None:
        values = dict(record)
        values.update(active=1, last_seen_generation=generation)
        columns = (
            "local_path", "source_key", "relative_path", "target", "target_is_absolute",
            "link_kind", "mtime_ns", "active", "last_seen_generation",
        )
        placeholders = ",".join(f":{column}" for column in columns)
        updates = ",".join(f"{column}=excluded.{column}" for column in columns if column != "local_path")
        self.db.execute(
            f"INSERT INTO symlinks({','.join(columns)}) VALUES({placeholders}) "
            f"ON CONFLICT(local_path) DO UPDATE SET {updates}",
            values,
        )

    def file_rows(self, file_filter: FileFilter | None = None, *, approved_only: bool = False) -> list[sqlite3.Row]:
        rows = self.db.execute("SELECT * FROM files WHERE active=1 ORDER BY repo_id,destination").fetchall()
        selected = []
        for row in rows:
            if file_filter and not file_filter.matches(row["relative_path"]):
                continue
            if approved_only and self._blocked(row):
                continue
            selected.append(row)
        return selected

    def unresolved_blockers(self) -> list[sqlite3.Row]:
        return [row for row in self.file_rows() if self._blocked(row)]

    def record_license_review(
        self, source_key: str, relative_path: str, *, approve: bool, reason: str, reviewer: str
    ) -> None:
        if not reason.strip() or not reviewer.strip():
            raise ValueError("a documented review requires both reason and reviewer")
        result = self.db.execute(
            "UPDATE files SET review_status=?,review_reason=?,reviewer=? WHERE source_key=? AND relative_path=? AND active=1",
            ("approved" if approve else "blocked", reason.strip(), reviewer.strip(), source_key, relative_path),
        )
        if result.rowcount != 1:
            raise KeyError("active inventory file was not found")
        self.db.commit()

    def mark_unstable(self, file_id: int, reason: str) -> None:
        self.db.execute(
            "UPDATE files SET security_status='unstable',security_reasons=?,status='blocked',"
            "revision=NULL,verification_status=NULL,verified_at=NULL,last_error=? WHERE id=?",
            (json.dumps([reason]), reason, file_id),
        )
        self.db.commit()

    def update_verification(
        self,
        file_id: int,
        *,
        status: str,
        revision: str | None,
        remote_sha256: str | None,
        remote_blob_sha1: str | None,
        remote_size: int | None,
        error: str | None = None,
    ) -> None:
        self.db.execute(
            "UPDATE files SET verification_status=?,revision=?,verified_at=?,remote_sha256=?,"
            "remote_blob_sha1=?,remote_size=?,last_error=? WHERE id=?",
            (status, revision, _utc_now() if status == "verified" else None, remote_sha256,
             remote_blob_sha1, remote_size, error, file_id),
        )
        self.db.commit()

    def export_manifests(self, output_dir: str | os.PathLike[str]) -> dict[str, Any]:
        output = Path(output_dir).expanduser().absolute()
        self._check_outside_sources(output)
        output.mkdir(parents=True, exist_ok=True)
        approved: list[dict[str, Any]] = []
        blocked: list[dict[str, Any]] = []
        for row in self.file_rows():
            record = public_file_record(row, blocked=self._blocked(row))
            (blocked if self._blocked(row) else approved).append(record)
        for row in self.db.execute("SELECT * FROM symlinks WHERE active=1 ORDER BY source_key,relative_path"):
            record: dict[str, Any] = {
                "entry_type": "symlink",
                "source_root": row["source_key"],
                "relative_path": row["relative_path"],
                "link_kind": row["link_kind"],
                "target_is_absolute": bool(row["target_is_absolute"]),
                "uploaded": False,
                "reason": "Symlinks are inventoried as metadata only and are never followed or uploaded.",
            }
            if not row["target_is_absolute"]:
                record["target"] = row["target"]
            approved.append(record)
        summary = {
            "schema": "aureon.isambard-transfer.summary.v1",
            "generated_at": _utc_now(),
            "files": len(approved) + len(blocked) - sum(1 for item in approved if item["entry_type"] == "symlink"),
            "approved_files": sum(1 for item in approved if item["entry_type"] == "file"),
            "blocked_files": len(blocked),
            "symlinks": sum(1 for item in approved if item["entry_type"] == "symlink"),
            "approved_bytes": sum(int(item["size"]) for item in approved if item["entry_type"] == "file"),
            "blocked_bytes": sum(int(item["size"]) for item in blocked),
            "verified_files": sum(1 for item in approved if item.get("verification_status") == "verified"),
            "blocker_reasons": _reason_counts(blocked),
            "repositories": {repo: sum(1 for item in approved if item.get("repo_id") == repo) for repo in sorted(ALLOWED_REPOS)},
        }
        _write_jsonl(output / "manifest.jsonl", approved)
        _write_jsonl(output / "blocked.jsonl", blocked)
        _write_json(output / "summary.json", summary)
        return summary


def public_file_record(row: Mapping[str, Any] | sqlite3.Row, *, blocked: bool = False) -> dict[str, Any]:
    """Serialize an inventory row without its absolute local path or raw errors."""

    record = {
        "entry_type": "file",
        "source_root": row["source_key"],
        "relative_path": row["relative_path"],
        "size": row["size"],
        "mtime_ns": row["mtime_ns"],
        "sha256": row["sha256"],
        "repo_id": row["repo_id"],
        "repo_type": "dataset",
        "destination": row["destination"],
        "provenance": row["provenance"],
        "provenance_status": row["provenance_status"],
        "license": row["license"],
        "license_status": row["license_status"],
        "license_reason": row["license_reason"],
        "review_status": row["review_status"],
        "review_reason": row["review_reason"],
        "reviewer": row["reviewer"],
        "security_status": row["security_status"],
        "security_reasons": json.loads(row["security_reasons"]),
        "status": "blocked" if blocked else "approved",
        "revision": row["revision"],
        "verification_status": row["verification_status"],
    }
    if blocked:
        record["block_reasons"] = _block_reasons(row)
    return record


def _block_reasons(row: Mapping[str, Any] | sqlite3.Row) -> list[str]:
    reasons = list(json.loads(row["security_reasons"]))
    if row["license_status"] == "blocked" and row["review_status"] != "approved":
        reasons.append("license_or_provenance_review_required")
    return sorted(set(reasons))


def _reason_counts(records: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        for reason in record.get("block_reasons", []):
            counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def _write_jsonl(path: Path, records: Iterable[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


class Inventory:
    def __init__(self, state: ArchiveState):
        self.state = state

    def scan(self, file_filter: FileFilter | None = None) -> dict[str, int]:
        file_filter = file_filter or FileFilter()
        generation = self.state._next_generation()
        stats = {"files": 0, "reused": 0, "hashed": 0, "blocked": 0, "changed_during_scan": 0, "symlinks": 0}
        selected_sources: set[str] = set()
        stop = False
        for source in self.state.sources:
            if stop:
                break
            root = source.path
            root_stat = root.lstat()
            if not stat.S_ISDIR(root_stat.st_mode) or stat.S_ISLNK(root_stat.st_mode):
                raise ArchiveError(f"source root {source.key} is not a real directory")
            selected_sources.add(source.key)
            stack = [root]
            while stack and not stop:
                directory = stack.pop()
                with os.scandir(directory) as entries:
                    ordered = sorted(entries, key=lambda entry: entry.name, reverse=True)
                for entry in ordered:
                    try:
                        entry_stat = entry.stat(follow_symlinks=False)
                        relative = Path(entry.path).relative_to(root).as_posix()
                        if entry.is_symlink():
                            self.state.upsert_symlink(
                                {
                                    "local_path": str(Path(entry.path).absolute()),
                                    "source_key": source.key,
                                    "relative_path": relative,
                                    "target": os.readlink(entry.path),
                                    "target_is_absolute": Path(os.readlink(entry.path)).is_absolute(),
                                    "link_kind": "not_followed",
                                    "mtime_ns": entry_stat.st_mtime_ns,
                                },
                                generation,
                            )
                            self.state.db.commit()
                            stats["symlinks"] += 1
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(Path(entry.path))
                            continue
                        if not stat.S_ISREG(entry_stat.st_mode) or not file_filter.matches(relative):
                            continue
                        if file_filter.max_files is not None and stats["files"] >= file_filter.max_files:
                            stop = True
                            break
                        if file_filter.max_bytes is not None and stats["files"] > 0:
                            current_bytes = self.state.db.execute(
                                "SELECT COALESCE(SUM(size),0) AS total FROM files WHERE last_seen_generation=?",
                                (generation,),
                            ).fetchone()["total"]
                            if current_bytes + entry_stat.st_size > file_filter.max_bytes:
                                stop = True
                                break
                        outcome = self._scan_file(source, Path(entry.path), relative, entry_stat, generation)
                        # Persist each completed file so an interrupted multi-hundred-GB
                        # scan resumes from durable hashes rather than one huge transaction.
                        self.state.db.commit()
                        stats["files"] += 1
                        stats[outcome] += 1
                        if outcome == "changed_during_scan":
                            stats["blocked"] += 1
                    except OSError as error:
                        # Never turn an unreadable entry into a silent inventory gap.
                        raise ArchiveError("inventory could not read a directory entry") from error
        if not any((file_filter.globs, file_filter.contains, file_filter.max_files, file_filter.max_bytes)):
            for source_key in selected_sources:
                self.state.db.execute(
                    "UPDATE files SET active=0 WHERE source_key=? AND last_seen_generation<>?",
                    (source_key, generation),
                )
                self.state.db.execute(
                    "UPDATE symlinks SET active=0 WHERE source_key=? AND last_seen_generation<>?",
                    (source_key, generation),
                )
        self.state.db.execute(
            "INSERT INTO metadata(key,value) VALUES('scan_in_progress','0') "
            "ON CONFLICT(key) DO UPDATE SET value='0'"
        )
        self.state.db.commit()
        current = self.state.db.execute(
            "SELECT * FROM files WHERE last_seen_generation=?", (generation,)
        ).fetchall()
        stats["blocked"] = sum(1 for row in current if self.state._blocked(row))
        return stats

    def _scan_file(
        self,
        source: SourceSpec,
        path: Path,
        relative: str,
        initial: os.stat_result,
        generation: int,
    ) -> str:
        local_path = str(path.absolute())
        previous = self.state.db.execute("SELECT * FROM files WHERE local_path=?", (local_path,)).fetchone()
        destination = map_destination(source.key, relative)
        license_info = classify_license(source.key, relative)
        common = {
            "local_path": local_path,
            "source_key": source.key,
            "relative_path": relative,
            "repo_id": destination.repo_id,
            "destination": destination.destination,
            **license_info,
        }
        if (
            previous is not None
            and previous["size"] == initial.st_size
            and previous["mtime_ns"] == initial.st_mtime_ns
            and previous["scan_policy_version"] == SCAN_POLICY_VERSION
            and previous["sha256"]
            and previous["security_status"] in {"clean", "blocked"}
        ):
            self.state._upsert_file(
                {
                    **common,
                    "size": initial.st_size,
                    "mtime_ns": initial.st_mtime_ns,
                    "security_status": previous["security_status"],
                    "security_reasons": previous["security_reasons"],
                },
                generation,
                unchanged=True,
            )
            return "reused"
        try:
            digest, blob_digest, content_decision, before, after = _hash_and_scan(path)
            reasons = sorted(set(filename_security_findings(relative)) | set(content_decision.reasons))
            security_status = "blocked" if reasons else "clean"
            self.state._upsert_file(
                {
                    **common,
                    "size": after.st_size,
                    "mtime_ns": after.st_mtime_ns,
                    "sha256": digest,
                    "git_blob_sha1": blob_digest,
                    "security_status": security_status,
                    "security_reasons": json.dumps(reasons),
                },
                generation,
                unchanged=False,
            )
            return "hashed"
        except SourceChangedError:
            self.state._upsert_file(
                {
                    **common,
                    "size": initial.st_size,
                    "mtime_ns": initial.st_mtime_ns,
                    "sha256": None,
                    "git_blob_sha1": None,
                    "security_status": "unstable",
                    "security_reasons": json.dumps(["changed_during_scan"]),
                },
                generation,
                unchanged=False,
            )
            return "changed_during_scan"
        except OSError:
            self.state._upsert_file(
                {
                    **common,
                    "size": initial.st_size,
                    "mtime_ns": initial.st_mtime_ns,
                    "sha256": None,
                    "git_blob_sha1": None,
                    "security_status": "unreadable",
                    "security_reasons": json.dumps(["read_failed"]),
                },
                generation,
                unchanged=False,
            )
            return "hashed"


def build_batches(
    rows: Sequence[sqlite3.Row],
    *,
    max_files: int = DEFAULT_MAX_FILES,
    max_bytes: int = DEFAULT_MAX_BATCH_BYTES,
    large_file_bytes: int = DEFAULT_LARGE_FILE_BYTES,
) -> list[Batch]:
    if min(max_files, max_bytes, large_file_bytes) <= 0:
        raise ValueError("batch limits must be positive")
    batches: list[Batch] = []
    current: list[sqlite3.Row] = []
    current_bytes = 0

    def flush() -> None:
        nonlocal current, current_bytes
        if current:
            batches.append(Batch(tuple(current)))
            current = []
            current_bytes = 0

    for row in rows:
        size = int(row["size"])
        if size >= large_file_bytes or size > max_bytes:
            flush()
            batches.append(Batch((row,)))
            continue
        if current and (len(current) >= max_files or current_bytes + size > max_bytes):
            flush()
        current.append(row)
        current_bytes += size
    flush()
    return batches


def _entry_value(entry: Any, name: str, default: Any = None) -> Any:
    if isinstance(entry, Mapping):
        return entry.get(name, default)
    return getattr(entry, name, default)


def _entry_path(entry: Any) -> str:
    value = _entry_value(entry, "path") or _entry_value(entry, "rfilename")
    if not value:
        raise ArchiveError("Hub metadata entry has no repository path")
    return str(value)


def _revision_value(value: Any) -> str | None:
    revision = _entry_value(value, "sha") or _entry_value(value, "oid")
    return str(revision) if revision else None


def _lfs_oid(entry: Any) -> str | None:
    lfs = _entry_value(entry, "lfs")
    if not lfs:
        return None
    oid = _entry_value(lfs, "oid") or _entry_value(lfs, "sha256")
    if not oid:
        return None
    return str(oid).removeprefix("sha256:")


def _remote_match(row: Mapping[str, Any] | sqlite3.Row, entry: Any) -> tuple[bool, dict[str, Any]]:
    lfs_oid = _lfs_oid(entry)
    remote_blob = _entry_value(entry, "blob_id") or _entry_value(entry, "oid")
    remote_size = _entry_value(entry, "size")
    metadata = {
        "remote_sha256": lfs_oid,
        "remote_blob_sha1": None if lfs_oid else remote_blob,
        "remote_size": remote_size,
    }
    expected = row["sha256"] if lfs_oid else row["git_blob_sha1"]
    actual = lfs_oid or remote_blob
    matches = bool(expected and actual and hmac.compare_digest(str(expected), str(actual)))
    if remote_size is not None:
        matches = matches and int(remote_size) == int(row["size"])
    return matches, metadata


def _safe_error(error: BaseException, token: str | None = None) -> str:
    message = f"{type(error).__name__}: {error}"
    if token:
        message = message.replace(token, "[redacted]")
    return message[:2000]


class ArchiveUploader:
    """Resumable batch uploader; construct with a fake API for offline tests."""

    def __init__(
        self,
        state: ArchiveState,
        api: Any,
        *,
        commit_operation_add: Any,
        token: str | None = None,
    ):
        self.state = state
        self.api = api
        self.commit_operation_add = commit_operation_add
        self.token = token

    @classmethod
    def from_environment(cls, state: ArchiveState) -> ArchiveUploader:
        token = next((os.environ[name].strip() for name in TOKEN_NAMES if os.environ.get(name, "").strip()), None)
        if not token:
            raise ArchiveError("HF_TOKEN or HUGGING_FACE_HUB_TOKEN is required")
        hub = importlib.import_module("huggingface_hub")
        return cls(state, hub.HfApi(token=token), commit_operation_add=hub.CommitOperationAdd, token=token)

    def upload_approved(
        self,
        *,
        acknowledge_public: str | None,
        acknowledge_partial_release: str | None,
        file_filter: FileFilter | None = None,
        max_files: int = DEFAULT_MAX_FILES,
        max_bytes: int = DEFAULT_MAX_BATCH_BYTES,
        large_file_bytes: int = DEFAULT_LARGE_FILE_BYTES,
    ) -> dict[str, int]:
        if acknowledge_public != PUBLIC_ACK:
            raise ArchiveError(f"public release requires acknowledgement {PUBLIC_ACK}")
        if acknowledge_partial_release != PARTIAL_ACK:
            raise ArchiveError(f"approved-only release requires acknowledgement {PARTIAL_ACK}")
        if self.state.scan_in_progress:
            raise ArchiveError("inventory is incomplete; resume the scan before upload")
        selected = self.state.file_rows(file_filter)
        rows = [
            row for row in selected
            if not self.state._blocked(row)
            and row["verification_status"] != "verified"
            and row["sha256"] and row["git_blob_sha1"]
        ]
        summary = {
            "candidate_files": len(rows),
            "blocked_files_in_selection": sum(1 for row in selected if self.state._blocked(row)),
            "unresolved_blockers_total": len(self.state.unresolved_blockers()),
            "skipped_remote": 0,
            "uploaded_files": 0,
            "verified_files": 0,
        }
        by_repo: dict[str, list[sqlite3.Row]] = {}
        for row in rows:
            if row["repo_id"] not in ALLOWED_REPOS:
                raise ArchiveError("inventory destination is outside the approved repository mapping")
            by_repo.setdefault(row["repo_id"], []).append(row)
        for repo_id, repo_rows in by_repo.items():
            self.api.create_repo(repo_id, repo_type="dataset", private=False, exist_ok=True)
            revision_row = self.api.repo_info(repo_id, repo_type="dataset")
            remote_revision = _revision_value(revision_row)
            pending: list[sqlite3.Row] = []
            # Resolve only candidate paths, in bounded groups. Listing a mature
            # archive recursively would hold every remote path in memory.
            for start in range(0, len(repo_rows), 100):
                group = repo_rows[start : start + 100]
                entries = self.api.get_paths_info(
                    repo_id,
                    [row["destination"] for row in group],
                    repo_type="dataset",
                    revision=remote_revision,
                    expand=True,
                )
                remote = {_entry_path(entry): entry for entry in entries}
                for row in group:
                    entry = remote.get(row["destination"])
                    if entry is not None:
                        matches, metadata = _remote_match(row, entry)
                        if matches:
                            self.state.update_verification(
                                row["id"], status="verified", revision=remote_revision,
                                error=None, **metadata
                            )
                            summary["skipped_remote"] += 1
                            summary["verified_files"] += 1
                            continue
                    pending.append(row)
            for batch in build_batches(
                pending, max_files=max_files, max_bytes=max_bytes, large_file_bytes=large_file_bytes
            ):
                self._upload_batch(repo_id, batch, summary)
        return summary

    def _upload_batch(self, repo_id: str, batch: Batch, summary: dict[str, int]) -> None:
        stable: list[sqlite3.Row] = []
        unstable = False
        for row in batch.files:
            try:
                current = Path(row["local_path"]).lstat()
                if not stat.S_ISREG(current.st_mode) or (current.st_size, current.st_mtime_ns) != (
                    row["size"], row["mtime_ns"]
                ):
                    self.state.mark_unstable(row["id"], "changed_before_upload")
                    unstable = True
                    continue
                stable.append(row)
            except OSError:
                self.state.mark_unstable(row["id"], "unreadable_before_upload")
                unstable = True
        if unstable:
            raise BatchUploadError("a source changed or became unreadable before upload; rescan is required")
        if not stable:
            return
        batch_id = self._start_batch(repo_id, stable)
        operations = [
            self.commit_operation_add(path_in_repo=row["destination"], path_or_fileobj=row["local_path"])
            for row in stable
        ]
        self.state.db.execute(
            f"UPDATE files SET upload_attempts=upload_attempts+1 WHERE id IN ({','.join('?' for _ in stable)})",
            tuple(row["id"] for row in stable),
        )
        self.state.db.commit()
        try:
            result = self.api.create_commit(
                repo_id=repo_id,
                repo_type="dataset",
                operations=operations,
                commit_message=f"Isambard resumable archive batch {batch_id}",
            )
            revision = _revision_value(result)
            entries = self.api.get_paths_info(
                repo_id, [row["destination"] for row in stable], repo_type="dataset",
                revision=revision, expand=True,
            )
            by_path = {_entry_path(entry): entry for entry in entries}
            mismatches: list[str] = []
            for row in stable:
                entry = by_path.get(row["destination"])
                if entry is None:
                    self.state.update_verification(
                        row["id"], status="missing", revision=revision, remote_sha256=None,
                        remote_blob_sha1=None, remote_size=None, error="remote metadata missing after commit",
                    )
                    mismatches.append(row["destination"])
                    continue
                matches, metadata = _remote_match(row, entry)
                self.state.update_verification(
                    row["id"], status="verified" if matches else "mismatch", revision=revision,
                    error=None if matches else "remote hash mismatch", **metadata,
                )
                if matches:
                    summary["uploaded_files"] += 1
                    summary["verified_files"] += 1
                else:
                    mismatches.append(row["destination"])
            self._finish_batch(batch_id, "verified" if not mismatches else "verification_failed", revision,
                               "remote hash verification failed" if mismatches else None)
            if mismatches:
                raise BatchUploadError(f"batch {batch_id} failed remote hash verification")
        except Exception as error:
            if isinstance(error, BatchUploadError):
                self._finish_batch(batch_id, "verification_failed", None, str(error))
            else:
                self._finish_batch(batch_id, "failed", None, _safe_error(error, self.token))
                self.state.db.execute(
                    f"UPDATE files SET last_error=? WHERE id IN ({','.join('?' for _ in stable)})",
                    (_safe_error(error, self.token), *(row["id"] for row in stable)),
                )
                self.state.db.commit()
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                raise
            if isinstance(error, BatchUploadError):
                raise
            raise BatchUploadError(f"batch {batch_id} failed; resume will exclude verified files") from error

    def _start_batch(self, repo_id: str, rows: Sequence[sqlite3.Row]) -> int:
        cursor = self.state.db.execute(
            "INSERT INTO batches(repo_id,status,file_count,byte_count,created_at) VALUES(?,?,?,?,?)",
            (repo_id, "running", len(rows), sum(row["size"] for row in rows), _utc_now()),
        )
        batch_id = int(cursor.lastrowid)
        self.state.db.executemany(
            "INSERT INTO batch_files(batch_id,file_id) VALUES(?,?)",
            ((batch_id, row["id"]) for row in rows),
        )
        self.state.db.commit()
        return batch_id

    def _finish_batch(self, batch_id: int, status: str, revision: str | None, error: str | None) -> None:
        self.state.db.execute(
            "UPDATE batches SET status=?,revision=COALESCE(?,revision),error=?,completed_at=? WHERE id=?",
            (status, revision, error, _utc_now(), batch_id),
        )
        self.state.db.commit()


def verify_remote(
    state: ArchiveState,
    api: Any,
    *,
    file_filter: FileFilter | None = None,
    final: bool = False,
) -> dict[str, Any]:
    """Verify Hub metadata; final mode also refuses every unresolved blocker."""

    blockers = state.unresolved_blockers()
    summary: dict[str, Any] = {
        "blocked_files": len(blockers),
        "verified_files": 0,
        "missing_files": 0,
        "mismatched_files": 0,
        "failed_destinations": [],
    }
    if final and state.scan_in_progress:
        raise FinalVerificationError("final verification failed: inventory scan is incomplete", summary)
    if final and blockers:
        raise FinalVerificationError("final verification failed: unresolved blocked files remain", summary)
    if final and not state.file_rows():
        raise FinalVerificationError("final verification failed: the active inventory is empty", summary)
    # Final means the whole active inventory, never a pilot subset.
    rows = state.file_rows(None if final else file_filter, approved_only=True)
    by_repo: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        by_repo.setdefault(row["repo_id"], []).append(row)
    for repo_id, repo_rows in by_repo.items():
        info = api.repo_info(repo_id, repo_type="dataset")
        revision = _revision_value(info)
        for start in range(0, len(repo_rows), 100):
            group = repo_rows[start : start + 100]
            entries = api.get_paths_info(
                repo_id, [row["destination"] for row in group], repo_type="dataset",
                revision=revision, expand=True,
            )
            by_path = {_entry_path(entry): entry for entry in entries}
            for row in group:
                entry = by_path.get(row["destination"])
                if entry is None:
                    state.update_verification(
                        row["id"], status="missing", revision=revision, remote_sha256=None,
                        remote_blob_sha1=None, remote_size=None, error="remote metadata missing",
                    )
                    summary["missing_files"] += 1
                    summary["failed_destinations"].append(f"{repo_id}/{row['destination']}")
                    continue
                matches, metadata = _remote_match(row, entry)
                state.update_verification(
                    row["id"], status="verified" if matches else "mismatch", revision=revision,
                    error=None if matches else "remote hash mismatch", **metadata,
                )
                if matches:
                    summary["verified_files"] += 1
                else:
                    summary["mismatched_files"] += 1
                    summary["failed_destinations"].append(f"{repo_id}/{row['destination']}")
    if final and summary["failed_destinations"]:
        raise FinalVerificationError("final verification failed: remote files are missing or mismatched", summary)
    return summary


def _filter_from_args(args: argparse.Namespace) -> FileFilter:
    return FileFilter(
        globs=tuple(args.glob or ()),
        contains=tuple(args.contains or ()),
        max_files=getattr(args, "max_files", None),
        max_bytes=getattr(args, "max_bytes", None),
    )


def _add_filter_arguments(parser: argparse.ArgumentParser, *, limits: bool = True) -> None:
    parser.add_argument("--glob", action="append", help="source-relative POSIX glob; repeatable")
    parser.add_argument("--contains", action="append", help="source-relative substring; repeatable")
    if limits:
        parser.add_argument("--max-files", type=int)
        parser.add_argument("--max-bytes", type=int)


def _open_cli_state(args: argparse.Namespace, *, defaults: bool = False) -> ArchiveState:
    if defaults or args.pretrain_root or args.hnc_root:
        sources = default_sources(
            args.pretrain_root or "/projects/u6vs/pretrain",
            args.hnc_root or "/projects/u6vs/hnc-organism",
        )
        return ArchiveState(args.state, sources)
    return ArchiveState(args.state)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    inventory = commands.add_parser("inventory", help="scan or resume the source inventory")
    inventory.add_argument("--state", required=True)
    inventory.add_argument("--pretrain-root")
    inventory.add_argument("--hnc-root")
    _add_filter_arguments(inventory)

    export = commands.add_parser("export", help="export path-safe public manifests")
    export.add_argument("--state", required=True)
    export.add_argument("--output-dir", required=True)
    export.add_argument("--pretrain-root")
    export.add_argument("--hnc-root")

    upload = commands.add_parser("upload", help="upload approved files in resumable public batches")
    upload.add_argument("--state", required=True)
    upload.add_argument("--pretrain-root")
    upload.add_argument("--hnc-root")
    upload.add_argument("--acknowledge-public")
    upload.add_argument("--acknowledge-partial-release")
    upload.add_argument("--batch-files", type=int, default=DEFAULT_MAX_FILES)
    upload.add_argument("--batch-bytes", type=int, default=DEFAULT_MAX_BATCH_BYTES)
    upload.add_argument("--large-file-bytes", type=int, default=DEFAULT_LARGE_FILE_BYTES)
    _add_filter_arguments(upload, limits=False)

    verify = commands.add_parser("verify", help="verify every selected file using Hub metadata")
    verify.add_argument("--state", required=True)
    verify.add_argument("--pretrain-root")
    verify.add_argument("--hnc-root")
    verify.add_argument("--final", action="store_true", help="fail on any unresolved blocker or bad remote file")
    _add_filter_arguments(verify, limits=False)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        with _open_cli_state(args, defaults=args.command == "inventory") as state:
            if args.command == "inventory":
                result: Mapping[str, Any] = Inventory(state).scan(_filter_from_args(args))
            elif args.command == "export":
                result = state.export_manifests(args.output_dir)
            elif args.command == "upload":
                uploader = ArchiveUploader.from_environment(state)
                result = uploader.upload_approved(
                    acknowledge_public=args.acknowledge_public,
                    acknowledge_partial_release=args.acknowledge_partial_release,
                    file_filter=_filter_from_args(args),
                    max_files=args.batch_files,
                    max_bytes=args.batch_bytes,
                    large_file_bytes=args.large_file_bytes,
                )
            else:
                token = next(
                    (os.environ[name].strip() for name in TOKEN_NAMES if os.environ.get(name, "").strip()), None
                )
                if not token:
                    raise ArchiveError("HF_TOKEN or HUGGING_FACE_HUB_TOKEN is required")
                hub = importlib.import_module("huggingface_hub")
                result = verify_remote(state, hub.HfApi(token=token), file_filter=_filter_from_args(args), final=args.final)
                if result["failed_destinations"]:
                    return 1
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except FinalVerificationError as error:
        print(json.dumps({"error": str(error), "summary": error.summary}, indent=2, sort_keys=True), file=sys.stderr)
        return 1
    except (ArchiveError, OSError, ValueError) as error:
        token = next((os.environ.get(name, "") for name in TOKEN_NAMES if os.environ.get(name)), None)
        print(json.dumps({"error": _safe_error(error, token)}), file=sys.stderr)
        return 1
    except Exception as error:
        # Hub exceptions can contain request details; redact the environment token
        # rather than exposing an unfiltered traceback through this operational CLI.
        token = next((os.environ.get(name, "") for name in TOKEN_NAMES if os.environ.get(name)), None)
        print(json.dumps({"error": _safe_error(error, token)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
