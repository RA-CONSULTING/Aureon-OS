"""Serialisation and byte-verification helpers for AGPHA source snapshots."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .source_snapshot import (
    SOURCE_SNAPSHOT_VERSION,
    QueryReceipt,
    QueryStatus,
    SnapshotFile,
    SnapshotVerification,
    SourceSnapshotManifest,
    sha256_file,
)
from .source_registry import SOURCE_REGISTRY_VERSION


def source_snapshot_from_dict(data: Mapping[str, Any]) -> SourceSnapshotManifest:
    snapshot = SourceSnapshotManifest(
        schema_version=str(data.get("schema_version", SOURCE_SNAPSHOT_VERSION)),
        registry_version=str(data.get("registry_version", SOURCE_REGISTRY_VERSION)),
        snapshot_id=str(data["snapshot_id"]),
        created_at=str(data["created_at"]),
        files=tuple(
            SnapshotFile(
                relpath=str(item["relpath"]),
                source_id=str(item["source_id"]),
                source_record_id=str(item["source_record_id"]),
                retrieved_at=str(item["retrieved_at"]),
                licence_or_terms=str(item["licence_or_terms"]),
                size_bytes=int(item["size_bytes"]),
                sha256=str(item["sha256"]),
                media_type=item.get("media_type"),
                notes=item.get("notes"),
            )
            for item in data.get("files", [])
        ),
        queries=tuple(
            QueryReceipt(
                query_id=str(item["query_id"]),
                source_id=str(item["source_id"]),
                request_sha256=str(item["request_sha256"]),
                status=QueryStatus(item["status"]),
                result_count=(int(item["result_count"]) if item.get("result_count") is not None else None),
                retrieved_at=str(item["retrieved_at"]),
                response_relpath=item.get("response_relpath"),
                response_sha256=item.get("response_sha256"),
                notes=item.get("notes"),
            )
            for item in data.get("queries", [])
        ),
        metadata=dict(data.get("metadata", {})),
    )
    return snapshot.require_valid()


def load_source_snapshot(path: str | Path) -> SourceSnapshotManifest:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("source snapshot JSON must contain an object")
    return source_snapshot_from_dict(payload)


def write_source_snapshot(snapshot: SourceSnapshotManifest, path: str | Path) -> Path:
    snapshot.require_valid()
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(snapshot.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def verify_source_snapshot(
    snapshot: SourceSnapshotManifest,
    root: str | Path,
) -> SnapshotVerification:
    snapshot.require_valid()
    base = Path(root)
    missing: list[str] = []
    size_mismatches: list[str] = []
    checksum_mismatches: list[str] = []
    verified = 0
    for item in snapshot.files:
        path = base / item.relpath
        if not path.is_file():
            missing.append(item.relpath)
            continue
        if path.stat().st_size != item.size_bytes:
            size_mismatches.append(item.relpath)
            continue
        if sha256_file(path) != item.sha256.lower():
            checksum_mismatches.append(item.relpath)
            continue
        verified += 1
    declared = {item.relpath for item in snapshot.files}
    undeclared_response_files = sorted(
        receipt.response_relpath
        for receipt in snapshot.queries
        if receipt.response_relpath is not None and receipt.response_relpath not in declared
    )
    return SnapshotVerification(
        snapshot_id=snapshot.snapshot_id,
        expected_files=len(snapshot.files),
        verified_files=verified,
        missing=tuple(sorted(missing)),
        size_mismatches=tuple(sorted(size_mismatches)),
        checksum_mismatches=tuple(sorted(checksum_mismatches)),
        undeclared_response_files=tuple(undeclared_response_files),
    )


def snapshot_files_from_paths(
    root: str | Path,
    entries: Iterable[Mapping[str, Any]],
) -> tuple[SnapshotFile, ...]:
    """Build file records from explicit metadata plus local paths.

    This helper does not discover or guess provenance.  Each entry must supply
    ``relpath``, ``source_id``, ``source_record_id``, ``retrieved_at``, and
    ``licence_or_terms``; size and checksum are calculated from the frozen bytes.
    """

    base = Path(root)
    records: list[SnapshotFile] = []
    for entry in entries:
        relpath = str(entry["relpath"])
        path = base / relpath
        if not path.is_file():
            raise FileNotFoundError(path)
        records.append(
            SnapshotFile(
                relpath=relpath,
                source_id=str(entry["source_id"]),
                source_record_id=str(entry["source_record_id"]),
                retrieved_at=str(entry["retrieved_at"]),
                licence_or_terms=str(entry["licence_or_terms"]),
                size_bytes=path.stat().st_size,
                sha256=sha256_file(path),
                media_type=entry.get("media_type"),
                notes=entry.get("notes"),
            )
        )
    return tuple(records)
