"""Shared value objects and safe, read-only file helpers."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import TypeAlias

Metric: TypeAlias = str | int | float | bool
RESULT_SCHEMA = "aureon.website-capability-result.v1"


class CapabilityInputError(ValueError):
    """Raised when a capability receives unsafe or malformed input."""


class Severity(StrEnum):
    """Stable finding severity used across every implementation."""

    PASS = "pass"
    WARNING = "warning"
    BLOCKER = "blocker"


@dataclass(frozen=True)
class CapabilityFinding:
    """One deterministic finding bound to an optional source location."""

    code: str
    severity: Severity
    message: str
    location: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
            "location": self.location,
        }


@dataclass(frozen=True)
class CapabilityResult:
    """Immutable read-only audit result with evidence and numeric facts."""

    skill_id: str
    findings: tuple[CapabilityFinding, ...]
    evidence: tuple[str, ...] = ()
    metrics: Mapping[str, Metric] = field(default_factory=dict)
    publishable_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "metrics", MappingProxyType(dict(self.metrics)))

    @property
    def passed(self) -> bool:
        return not any(finding.severity is Severity.BLOCKER for finding in self.findings)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": RESULT_SCHEMA,
            "skill_id": self.skill_id,
            "passed": self.passed,
            "findings": [finding.to_dict() for finding in self.findings],
            "evidence": list(self.evidence),
            "metrics": dict(self.metrics),
            "publishable_ids": list(self.publishable_ids),
            "release_eligible": False,
            "deployment_authority": "none",
        }


def finding(
    code: str,
    passed: bool,
    message: str,
    *,
    location: str | None = None,
    warning: bool = False,
) -> CapabilityFinding:
    """Construct a pass, warning, or blocker without ambiguous booleans."""

    severity = Severity.PASS if passed else (Severity.WARNING if warning else Severity.BLOCKER)
    return CapabilityFinding(code=code, severity=severity, message=message, location=location)


def require_non_empty_string(value: object, field_name: str) -> str:
    """Validate and return a stripped required string."""

    if not isinstance(value, str) or not value.strip():
        raise CapabilityInputError(f"{field_name} must be a non-empty string")
    return value.strip()


def require_safe_relative_path(value: object, field_name: str = "path") -> str:
    """Reject absolute, traversal, backslash, or empty artifact paths."""

    raw = require_non_empty_string(value, field_name)
    if "\\" in raw:
        raise CapabilityInputError(f"{field_name} must use forward slashes")
    path = PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise CapabilityInputError(f"{field_name} must be a safe repository-relative path")
    return path.as_posix()


def resolve_readonly_file(
    root: Path,
    relative_path: object,
    *,
    suffixes: Iterable[str] | None = None,
    max_bytes: int = 10_000_000,
) -> Path:
    """Resolve a regular in-root file without following it outside the root."""

    if max_bytes <= 0:
        raise CapabilityInputError("max_bytes must be positive")
    root_resolved = root.resolve(strict=True)
    if not root_resolved.is_dir():
        raise CapabilityInputError("root must be an existing directory")
    safe = require_safe_relative_path(relative_path)
    candidate = (root_resolved / Path(*PurePosixPath(safe).parts)).resolve(strict=True)
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise CapabilityInputError(f"path escapes root: {safe}") from exc
    if not candidate.is_file():
        raise CapabilityInputError(f"path is not a regular file: {safe}")
    if suffixes is not None and candidate.suffix.lower() not in {item.lower() for item in suffixes}:
        raise CapabilityInputError(f"unsupported file type: {safe}")
    if candidate.stat().st_size > max_bytes:
        raise CapabilityInputError(f"file exceeds read limit: {safe}")
    return candidate


def read_text(
    root: Path,
    relative_path: object,
    *,
    suffixes: Iterable[str] | None = None,
    max_bytes: int = 2_000_000,
) -> tuple[str, str]:
    """Read one UTF-8 artifact and return its safe path and content."""

    safe = require_safe_relative_path(relative_path)
    path = resolve_readonly_file(root, safe, suffixes=suffixes, max_bytes=max_bytes)
    try:
        return safe, path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise CapabilityInputError(f"file is not UTF-8 text: {safe}") from exc


def sha256_file(root: Path, relative_path: object, *, max_bytes: int = 50_000_000) -> tuple[str, int]:
    """Hash a bounded in-root file without changing it."""

    path = resolve_readonly_file(root, relative_path, max_bytes=max_bytes)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(131_072), b""):
            digest.update(chunk)
    return digest.hexdigest(), path.stat().st_size


def require_mapping(value: object, field_name: str) -> Mapping[str, object]:
    """Narrow an arbitrary value to a string-keyed mapping."""

    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise CapabilityInputError(f"{field_name} must be an object with string keys")
    return value
