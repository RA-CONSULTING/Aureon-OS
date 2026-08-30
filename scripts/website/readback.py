#!/usr/bin/env python3
"""Deterministic, credential-free release read-back comparison.

This module never opens a socket and never accepts credentials.  It compares
an already captured HTTP response set or an already downloaded FTPS/WebFTP
tree with the exact per-file SHA-256 manifest carried by a built package.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

FILE_HASH_MANIFEST_NAME = "HOMEPL_FILE_HASHES.json"
FILE_HASH_MANIFEST_SCHEMA = "aureon.homepl-file-hashes.v1"
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ReadbackInputError(ValueError):
    """Raised when a manifest or captured observation is unsafe or malformed."""


@dataclass(frozen=True)
class FileHashRecord:
    """One immutable expected public file."""

    path: str
    bytes: int
    sha256: str


@dataclass(frozen=True)
class FileHashManifest:
    """Validated release manifest with no recursive self-hash."""

    source_commit: str
    records: tuple[FileHashRecord, ...]


@dataclass(frozen=True)
class HttpObservation:
    """Captured public response bytes; no URL, headers, cookies, or credentials."""

    status_code: int
    body: bytes


@dataclass(frozen=True)
class ReadbackFinding:
    """One deterministic mismatch safe to retain in a release receipt."""

    path: str
    check: str
    expected: str
    observed: str

    def to_dict(self) -> dict[str, str]:
        return {
            "path": self.path,
            "check": self.check,
            "expected": self.expected,
            "observed": self.observed,
        }


@dataclass(frozen=True)
class ReadbackReport:
    """Credential-free exact comparison result."""

    method: str
    source_commit: str
    expected_file_count: int
    observed_file_count: int
    findings: tuple[ReadbackFinding, ...]

    @property
    def passed(self) -> bool:
        return not self.findings and self.observed_file_count == self.expected_file_count

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "aureon.homepl-readback-comparison.v1",
            "method": self.method,
            "source_commit": self.source_commit,
            "expected_file_count": self.expected_file_count,
            "observed_file_count": self.observed_file_count,
            "passed": self.passed,
            "findings": [finding.to_dict() for finding in self.findings],
            "credentials_recorded": False,
            "network_access_performed": False,
        }


def _safe_relative_path(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\t" in value or "\n" in value:
        raise ReadbackInputError("manifest path must be a non-empty forward-slash relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise ReadbackInputError(f"unsafe manifest path: {value}")
    return path.as_posix()


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise ReadbackInputError(f"{label} must be an object with string keys")
    return value


def parse_file_hash_manifest(payload: bytes | str) -> FileHashManifest:
    """Parse and strictly validate a deterministic package hash manifest."""

    try:
        text = payload.decode("utf-8") if isinstance(payload, bytes) else payload
    except UnicodeDecodeError as exc:
        raise ReadbackInputError("file hash manifest is not UTF-8") from exc
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ReadbackInputError("file hash manifest is not valid JSON") from exc
    data = _mapping(raw, "file hash manifest")
    if data.get("schema") != FILE_HASH_MANIFEST_SCHEMA:
        raise ReadbackInputError("unsupported file hash manifest schema")
    if data.get("algorithm") != "sha256" or data.get("manifest_self_included") is not False:
        raise ReadbackInputError("manifest must use SHA-256 and explicitly exclude itself")
    source_commit = data.get("source_commit")
    if not isinstance(source_commit, str) or not _COMMIT.fullmatch(source_commit):
        raise ReadbackInputError("manifest source_commit must be lowercase full-length hexadecimal")
    raw_records = data.get("records")
    if not isinstance(raw_records, list):
        raise ReadbackInputError("manifest records must be a list")
    if data.get("record_count") != len(raw_records):
        raise ReadbackInputError("manifest record_count does not match records")

    records: list[FileHashRecord] = []
    for index, item in enumerate(raw_records):
        row = _mapping(item, f"record {index}")
        path = _safe_relative_path(row.get("path"))
        size = row.get("bytes")
        digest = row.get("sha256")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ReadbackInputError(f"record {index} has an invalid byte count")
        if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            raise ReadbackInputError(f"record {index} has an invalid SHA-256")
        if path == FILE_HASH_MANIFEST_NAME:
            raise ReadbackInputError("file hash manifest must not hash itself")
        records.append(FileHashRecord(path=path, bytes=size, sha256=digest))

    paths = [record.path for record in records]
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise ReadbackInputError("manifest paths must be unique and sorted")
    return FileHashManifest(source_commit=source_commit, records=tuple(records))


def load_file_hash_manifest(package_dir: Path) -> tuple[FileHashManifest, bytes]:
    """Load the bounded package manifest and its exact bytes."""

    package = package_dir.resolve(strict=True)
    if not package.is_dir():
        raise ReadbackInputError("package_dir must be a directory")
    path = package / FILE_HASH_MANIFEST_NAME
    if not path.is_file():
        raise ReadbackInputError(f"package is missing {FILE_HASH_MANIFEST_NAME}")
    payload = path.read_bytes()
    return parse_file_hash_manifest(payload), payload


def _digest(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(131_072), b""):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def _directory_observation(root: Path, relative: str) -> tuple[int, str] | None:
    candidate = (root / Path(*PurePosixPath(relative).parts)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ReadbackInputError(f"read-back path escapes root: {relative}") from exc
    if not candidate.is_file():
        return None
    return _digest(candidate)


def _regular_file_paths(root: Path) -> tuple[set[str], tuple[ReadbackFinding, ...]]:
    """Enumerate an exact mirror without following links or accepting unsafe entries."""

    paths: set[str] = set()
    findings: list[ReadbackFinding] = []
    for candidate in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = candidate.relative_to(root).as_posix()
        if candidate.is_symlink():
            findings.append(ReadbackFinding(relative, "unsafe-entry", "ordinary file/directory", "symlink"))
            continue
        if candidate.is_file():
            paths.add(_safe_relative_path(relative))
    return paths, tuple(findings)


def compare_readback_directory(package_dir: Path, readback_dir: Path) -> ReadbackReport:
    """Compare an already downloaded remote tree with the exact package."""

    manifest, manifest_bytes = load_file_hash_manifest(package_dir)
    observed_root = readback_dir.resolve(strict=True)
    if not observed_root.is_dir():
        raise ReadbackInputError("readback_dir must be a directory")
    expected_manifest = FileHashRecord(
        path=FILE_HASH_MANIFEST_NAME,
        bytes=len(manifest_bytes),
        sha256=hashlib.sha256(manifest_bytes).hexdigest(),
    )
    expected = (expected_manifest, *manifest.records)
    observed_paths, unsafe_findings = _regular_file_paths(observed_root)
    findings: list[ReadbackFinding] = list(unsafe_findings)
    expected_paths = {record.path for record in expected}
    for record in expected:
        observed = _directory_observation(observed_root, record.path)
        if observed is None:
            findings.append(ReadbackFinding(record.path, "presence", "file", "missing"))
            continue
        size, digest = observed
        if size != record.bytes:
            findings.append(ReadbackFinding(record.path, "bytes", str(record.bytes), str(size)))
        if digest != record.sha256:
            findings.append(ReadbackFinding(record.path, "sha256", record.sha256, digest))
    for unexpected in sorted(observed_paths - expected_paths):
        findings.append(ReadbackFinding(unexpected, "unexpected-file", "absent", "present"))
    return ReadbackReport(
        method="downloaded-directory",
        source_commit=manifest.source_commit,
        expected_file_count=len(expected),
        observed_file_count=len(observed_paths),
        findings=tuple(findings),
    )


def compare_http_observations(
    package_dir: Path,
    observations: Mapping[str, HttpObservation],
) -> ReadbackReport:
    """Compare every expected package path from previously captured HTTP bodies.

    This proves the requested package paths, but unlike an exact downloaded
    served-root mirror it cannot discover unknown stale public paths.
    """

    manifest, manifest_bytes = load_file_hash_manifest(package_dir)
    normalised: dict[str, HttpObservation] = {}
    for path, observation in observations.items():
        safe = _safe_relative_path(path)
        if safe in normalised:
            raise ReadbackInputError(f"duplicate HTTP observation: {safe}")
        if not isinstance(observation, HttpObservation):
            raise ReadbackInputError(f"HTTP observation for {safe} has the wrong type")
        normalised[safe] = observation
    expected_manifest = FileHashRecord(
        path=FILE_HASH_MANIFEST_NAME,
        bytes=len(manifest_bytes),
        sha256=hashlib.sha256(manifest_bytes).hexdigest(),
    )
    expected = (expected_manifest, *manifest.records)
    findings: list[ReadbackFinding] = []
    observed_count = 0
    for record in expected:
        current = normalised.get(record.path)
        if current is None:
            findings.append(ReadbackFinding(record.path, "presence", "HTTP 200 body", "missing"))
            continue
        observed_count += 1
        if current.status_code != 200:
            findings.append(ReadbackFinding(record.path, "http-status", "200", str(current.status_code)))
            continue
        size = len(current.body)
        digest = hashlib.sha256(current.body).hexdigest()
        if size != record.bytes:
            findings.append(ReadbackFinding(record.path, "bytes", str(record.bytes), str(size)))
        if digest != record.sha256:
            findings.append(ReadbackFinding(record.path, "sha256", record.sha256, digest))
    return ReadbackReport(
        method="captured-http-expected-paths",
        source_commit=manifest.source_commit,
        expected_file_count=len(expected),
        observed_file_count=observed_count,
        findings=tuple(findings),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare an already downloaded Home.pl tree with an exact built package (no network)."
    )
    parser.add_argument("--package", required=True, help="built package directory")
    parser.add_argument("--readback-dir", required=True, help="already downloaded served-root tree")
    args = parser.parse_args(argv)
    try:
        report = compare_readback_directory(Path(args.package), Path(args.readback_dir))
    except (OSError, ReadbackInputError) as exc:
        print(f"read-back comparison refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.passed else 1


if __name__ == "__main__":  # pragma: no cover - CLI wrapper
    raise SystemExit(main())
