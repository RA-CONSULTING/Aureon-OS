"""Immutable source-snapshot manifests for AGPHA acquisition runs.

Compute workers never contact public providers.  An acquisition process first freezes
source files and query receipts under a snapshot root, writes this manifest, and
verifies every byte before an :class:`~aureon.bio.plant_atlas.sharding.AtlasRunManifest`
may refer to the snapshot.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

from .source_registry import SOURCE_REGISTRY_VERSION, source_registry

SOURCE_SNAPSHOT_VERSION = "agpha.source-snapshot.v1"


class QueryStatus(str, Enum):
    COMPLETE = "complete"
    ZERO_RESULT = "zero_result"
    FAILED = "failed"


def _valid_digest(value: str) -> bool:
    digest = value.lower()
    return len(digest) == 64 and all(ch in "0123456789abcdef" for ch in digest)


def _valid_relpath(value: str) -> bool:
    path = PurePosixPath(value)
    return bool(value.strip()) and not path.is_absolute() and ".." not in path.parts


def sha256_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class SnapshotFile:
    relpath: str
    source_id: str
    source_record_id: str
    retrieved_at: str
    licence_or_terms: str
    size_bytes: int
    sha256: str
    media_type: str | None = None
    notes: str | None = None

    def validate(self, known_sources: set[str]) -> list[str]:
        errors: list[str] = []
        if not _valid_relpath(self.relpath):
            errors.append(f"snapshot file {self.relpath!r}: relpath must be safe and relative")
        if self.source_id not in known_sources:
            errors.append(f"snapshot file {self.relpath!r}: unknown source_id {self.source_id!r}")
        if not all(
            value.strip()
            for value in (self.source_record_id, self.retrieved_at, self.licence_or_terms)
        ):
            errors.append(
                f"snapshot file {self.relpath!r}: source_record_id, retrieved_at, and licence_or_terms are required"
            )
        if self.size_bytes < 0:
            errors.append(f"snapshot file {self.relpath!r}: size_bytes must be non-negative")
        if not _valid_digest(self.sha256):
            errors.append(f"snapshot file {self.relpath!r}: invalid sha256")
        return errors


@dataclass(frozen=True)
class QueryReceipt:
    query_id: str
    source_id: str
    request_sha256: str
    status: QueryStatus
    result_count: int | None
    retrieved_at: str
    response_relpath: str | None = None
    response_sha256: str | None = None
    notes: str | None = None

    def validate(self, known_sources: set[str]) -> list[str]:
        errors: list[str] = []
        if not self.query_id.strip():
            errors.append("query receipt query_id is required")
        if self.source_id not in known_sources:
            errors.append(f"query {self.query_id}: unknown source_id {self.source_id!r}")
        if not _valid_digest(self.request_sha256):
            errors.append(f"query {self.query_id}: invalid request_sha256")
        if not self.retrieved_at.strip():
            errors.append(f"query {self.query_id}: retrieved_at is required")
        if self.result_count is not None and self.result_count < 0:
            errors.append(f"query {self.query_id}: result_count must be non-negative")
        if self.status == QueryStatus.ZERO_RESULT and self.result_count != 0:
            errors.append(f"query {self.query_id}: zero_result requires result_count=0")
        if self.status == QueryStatus.COMPLETE and self.result_count is None:
            errors.append(f"query {self.query_id}: complete requires result_count")
        if self.status == QueryStatus.FAILED and not (self.notes and self.notes.strip()):
            errors.append(f"query {self.query_id}: failed query requires notes")
        if self.response_relpath is not None and not _valid_relpath(self.response_relpath):
            errors.append(f"query {self.query_id}: response_relpath must be safe and relative")
        if (self.response_relpath is None) != (self.response_sha256 is None):
            errors.append(
                f"query {self.query_id}: response_relpath and response_sha256 must be supplied together"
            )
        if self.response_sha256 is not None and not _valid_digest(self.response_sha256):
            errors.append(f"query {self.query_id}: invalid response_sha256")
        return errors


@dataclass(frozen=True)
class SourceSnapshotManifest:
    snapshot_id: str
    created_at: str
    files: tuple[SnapshotFile, ...]
    queries: tuple[QueryReceipt, ...]
    registry_version: str = SOURCE_REGISTRY_VERSION
    schema_version: str = SOURCE_SNAPSHOT_VERSION
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.schema_version != SOURCE_SNAPSHOT_VERSION:
            errors.append(f"unsupported source snapshot schema {self.schema_version!r}")
        if self.registry_version != SOURCE_REGISTRY_VERSION:
            errors.append(f"unsupported source registry version {self.registry_version!r}")
        if not self.snapshot_id.strip() or not self.created_at.strip():
            errors.append("snapshot_id and created_at are required")
        if not self.files and not self.queries:
            errors.append("source snapshot must declare at least one file or query receipt")
        known_sources = set(source_registry())
        for item in self.files:
            errors.extend(item.validate(known_sources))
        for receipt in self.queries:
            errors.extend(receipt.validate(known_sources))
        relpaths = [item.relpath for item in self.files]
        if len(relpaths) != len(set(relpaths)):
            errors.append("source snapshot file relpaths must be unique")
        query_ids = [item.query_id for item in self.queries]
        if len(query_ids) != len(set(query_ids)):
            errors.append("source snapshot query_id values must be unique")
        declared_files = set(relpaths)
        for receipt in self.queries:
            if receipt.response_relpath is not None and receipt.response_relpath not in declared_files:
                errors.append(
                    f"query {receipt.query_id}: response_relpath is not declared in snapshot files"
                )
        return errors

    def require_valid(self) -> "SourceSnapshotManifest":
        errors = self.validate()
        if errors:
            raise ValueError("invalid AGPHA source snapshot:\n- " + "\n- ".join(errors))
        return self

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for query in payload["queries"]:
            query["status"] = query["status"].value if isinstance(query["status"], QueryStatus) else query["status"]
        return payload

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def content_sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SnapshotVerification:
    snapshot_id: str
    expected_files: int
    verified_files: int
    missing: tuple[str, ...]
    size_mismatches: tuple[str, ...]
    checksum_mismatches: tuple[str, ...]
    undeclared_response_files: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not (
            self.missing
            or self.size_mismatches
            or self.checksum_mismatches
            or self.undeclared_response_files
        ) and self.expected_files == self.verified_files

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["passed"] = self.passed
        return payload


def source_snapshot_from_dict(data: Mapping[str, Any]) -> SourceSnapshotManifest:
    from .snapshot_io import source_snapshot_from_dict as _parse

    return _parse(data)


def load_source_snapshot(path: str | Path) -> SourceSnapshotManifest:
    from .snapshot_io import load_source_snapshot as _load

    return _load(path)


def write_source_snapshot(snapshot: SourceSnapshotManifest, path: str | Path) -> Path:
    from .snapshot_io import write_source_snapshot as _write

    return _write(snapshot, path)


def verify_source_snapshot(
    snapshot: SourceSnapshotManifest,
    root: str | Path,
) -> SnapshotVerification:
    from .snapshot_io import verify_source_snapshot as _verify

    return _verify(snapshot, root)


def snapshot_files_from_paths(
    root: str | Path,
    entries: Iterable[Mapping[str, Any]],
) -> tuple[SnapshotFile, ...]:
    from .snapshot_io import snapshot_files_from_paths as _build

    return _build(root, entries)
