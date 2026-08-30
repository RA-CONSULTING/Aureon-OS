"""Read-only planning and owner-decision validation for website source projection.

This module deliberately stops before staging.  It invokes the reviewed Home.pl
release builder only in ``-VerifyOnly`` mode, proves that its retained paths and
the omitted paths form an exact partition of the unchanged canonical website,
and records a proposal with no mutation authority.  A separately supplied,
short-lived named-owner decision can then be validated against that exact plan.

There is no source-copy, file-removal, candidate, canonical-promotion, package,
credential, network, or deployment entrypoint here.  Durable artifacts are
created once through :mod:`aureon.operator.secure_immutable_artifact`.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import threading
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import MappingProxyType, ModuleType
from typing import Any, Final
from urllib.parse import urlparse

PLAN_SCHEMA = "aureon.website-source-rationalisation-plan.v1"
OWNER_DECISION_SCHEMA = "aureon.website-source-rationalisation-owner-decision.v1"
OWNER_VALIDATION_SCHEMA = "aureon.website-source-rationalisation-owner-validation.v1"

SOURCE_ROOT = Path("website")
IMPLEMENTATION_PATH = Path("aureon/operator/website_source_rationalisation.py")
TRUSTED_LAUNCHER_PATH = Path("tools/run-website-source-rationalisation.py")
RELEASE_BUILDER_PATH = Path("tools/build-homepl-v28-narrow-release.ps1")
MOTION_POLICY_PATH = Path("aureon/operator/design_candidate_motion_policy_compiler.py")
SECURE_WRITER_PATH = Path("aureon/operator/secure_immutable_artifact.py")
ARTIFACT_ROOT = Path("artifacts/website-operator/source-rationalisations")
PLAN_ROOT = ARTIFACT_ROOT / "plans"
OWNER_DECISION_ROOT = ARTIFACT_ROOT / "owner-decisions"
VALIDATION_ROOT = ARTIFACT_ROOT / "validations"
RELEASE = "V29"
POWERSHELL_EXECUTABLE = Path("C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe")
REVIEWED_POWERSHELL_SHA256 = "3247BCFD60F6DD25F34CB74B5889AB10EF1B3EC72B4D4B3D95B5B25B534560B8"
REVIEWED_RELEASE_BUILDER_SHA256 = "0C42EA5FEB59DCE1583A7731189BF91223AB0F6B5DD333936BCA7E9F65438204"
REVIEWED_MOTION_POLICY_SHA256 = "2685C98B8D0199A30B09B3983E7F1C48DE65EF64D76E4B9900BE8F503F251A73"
REVIEWED_SECURE_WRITER_SHA256 = "D704D691A4D3221E096A470884E5D1293EA663164BB6740FE5BDD26D32B4DB81"
REVIEWED_TRUSTED_LAUNCHER_SHA256 = "827D4112E6C6042B4931E987237E1E7B6035B5A147373CDE202D9DC95184B009"
FIXED_RUNNER_ID = "python-subprocess-fixed-powershell-sanitized-environment-v1"
SANITIZED_ENVIRONMENT_POLICY_ID = "windows-powershell-minimal-no-inherited-environment-v1"
TEST_FIXTURE_RUNNER_ID = "injected-test-fixture-no-production-authority"

MAX_OWNER_DECISION_AGE = timedelta(hours=4)
MAX_FILES = 5_000
MAX_TREE_BYTES = 512 * 1024 * 1024
MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_PROCESS_OUTPUT_BYTES = 4 * 1024 * 1024
MAX_REVIEWED_SOURCE_BYTES = 4 * 1024 * 1024
PROCESS_TIMEOUT_SECONDS = 120

FIXED_FOOTPRINT_LIMITS: Final[Mapping[str, int]] = MappingProxyType(
    {
        "max_total_bytes": 4_500_000,
        "max_image_bytes": 2_200_000,
        "max_css_bytes": 350_000,
        "max_single_asset_bytes": 500_000,
    }
)

PLAN_AUTHORITY: Final[dict[str, object]] = {
    "scope": "read-only exact public-runtime source projection proposal",
    "canonical_website_mutation": "none",
    "physical_source_file_removal": "none",
    "staging_authority": "none",
    "candidate_authority": "none",
    "package_authority": "none",
    "release_eligible": False,
    "deployment_authority": "none",
    "credential_access": "none",
    "network_access": "none",
}

OWNER_DECISION_AUTHORITY: Final[dict[str, object]] = {
    "scope": "review-only acknowledgement of one exact source-projection proposal",
    "canonical_website_mutation": "none",
    "physical_source_file_removal": "none",
    "staging_authority": "none",
    "candidate_mutation": "none",
    "candidate_removal_authority": "none",
    "package_authority": "none",
    "release_eligible": False,
    "deployment_authority": "none",
    "credential_access": "none",
    "network_access": "none",
}

VALIDATION_AUTHORITY: Final[dict[str, object]] = {
    "scope": "read-only validation of one exact owner source-rationalisation decision",
    "canonical_website_mutation": "none",
    "physical_source_file_removal": "none",
    "staging_executed": False,
    "staging_authority": "none",
    "candidate_authority": "none",
    "package_authority": "none",
    "release_eligible": False,
    "deployment_authority": "none",
    "credential_access": "none",
    "network_access": "none",
}

_IMAGE_SUFFIXES = frozenset({".apng", ".avif", ".gif", ".ico", ".jpeg", ".jpg", ".png", ".svg", ".webp"})
_FONT_SUFFIXES = frozenset({".eot", ".otf", ".ttf", ".woff", ".woff2"})
_MEDIA_SUFFIXES = frozenset({".m4a", ".mov", ".mp3", ".mp4", ".oga", ".ogg", ".ogv", ".wav", ".webm"})

_SHA256 = re.compile(r"[A-F0-9]{64}\Z")
_RUN_ID = re.compile(r"[a-z0-9][a-z0-9._-]{2,80}\Z")
_GENERIC_APPROVERS = frozenset(
    {
        "admin",
        "ai",
        "aureon os",
        "codex",
        "operator",
        "owner",
        "system",
        "user",
    }
)

_MANIFEST_ROW_FIELDS = frozenset({"path", "bytes", "sha256"})
_OMITTED_ROW_FIELDS = frozenset({"path", "bytes", "sha256", "reason"})
_SUMMARY_FIELDS = frozenset({"tree_sha256", "manifest_sha256", "file_count", "total_bytes", "files"})
_OMITTED_FIELDS = frozenset({"manifest_sha256", "file_count", "total_bytes", "files"})
_SOURCE_FIELDS = frozenset({"root", *_SUMMARY_FIELDS})
_CLOSURE_FIELDS = frozenset(
    {
        "tool_path",
        "tool_sha256",
        "command",
        "release",
        "verify_only",
        "state",
        "entry_files",
        "local_reference_count",
        "missing_local_reference_count",
        "missing_fragment_reference_count",
        "remote_origins",
        "retained_manifest_sha256",
    }
)
_BUDGET_FIELDS = frozenset(
    {
        "policy_path",
        "policy_sha256",
        "max_total_bytes",
        "projected_total_bytes",
        "total_overage_bytes",
        "max_image_bytes",
        "projected_image_bytes",
        "image_overage_bytes",
        "max_css_bytes",
        "projected_css_bytes",
        "css_overage_bytes",
        "max_single_asset_bytes",
        "projected_largest_single_asset_bytes",
        "largest_single_asset_path",
        "largest_single_asset_category",
        "single_asset_overage_bytes",
        "violation_ids",
        "within_fixed_footprint_limits",
        "state",
        "eligible_for_next_local_gate",
        "candidate_qa_authority",
    }
)
_EXECUTION_FIELDS = frozenset(
    {
        "mode",
        "repo_root",
        "implementation_path",
        "implementation_sha256",
        "trusted_launcher_path",
        "reviewed_trusted_launcher_sha256",
        "launcher_attested",
        "release_builder_path",
        "reviewed_release_builder_sha256",
        "powershell_path",
        "reviewed_powershell_sha256",
        "motion_policy_path",
        "reviewed_motion_policy_sha256",
        "secure_writer_path",
        "reviewed_secure_writer_sha256",
        "runner_id",
        "environment_policy_id",
        "environment_sha256",
        "production_writable",
    }
)
_PLAN_FIELDS = frozenset(
    {
        "schema",
        "generated_at",
        "run_id",
        "state",
        "source_binding",
        "closure_binding",
        "retained_projection",
        "omitted_projection",
        "motion_budget_projection",
        "execution_binding",
        "authority",
        "payload_sha256",
    }
)
_DECISION_FIELDS = frozenset(
    {
        "schema",
        "decision",
        "scope",
        "plan_run_id",
        "plan_file_sha256",
        "plan_payload_sha256",
        "source_tree_sha256",
        "retained_tree_sha256",
        "omitted_manifest_sha256",
        "acknowledged_at",
        "expires_at",
        "acknowledged_by",
        "note",
        "authority",
    }
)
_VALIDATION_FIELDS = frozenset(
    {
        "schema",
        "validated_at",
        "state",
        "passed",
        "release_eligible",
        "authority",
        "plan",
        "decision",
        "checks",
        "next_gate",
        "payload_sha256",
    }
)
OWNER_VALIDATION_CHECK_IDS: Final[tuple[str, ...]] = (
    "exact-owner-decision-contract",
    "exact-plan-binding",
    "fresh-owner-decision",
    "current-plan-inputs",
    "non-authoritative-boundary",
)


class WebsiteSourceRationalisationError(ValueError):
    """A source projection or owner decision is unsafe, stale, or malformed."""


@dataclass(frozen=True)
class CommandResult:
    """Bounded result from the fixed read-only closure command."""

    returncode: int
    stdout: bytes
    stderr: bytes


CommandRunner = Callable[[Sequence[str], Path, bytes], CommandResult]


def _canonical_json_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise WebsiteSourceRationalisationError(
            "Source-rationalisation evidence must contain only finite standard JSON values."
        ) from exc


def _json_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest().upper()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest().upper()


def _same_file_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        stat.S_IFMT(left.st_mode) == stat.S_IFMT(right.st_mode)
        and int(left.st_dev) == int(right.st_dev)
        and int(left.st_ino) == int(right.st_ino)
    )


def _read_reviewed_source_bytes(path: Path, expected_sha256: str, *, label: str) -> bytes:
    source = _regular_file(path, label=label)
    before = source.lstat()
    if int(before.st_size) > MAX_REVIEWED_SOURCE_BYTES:
        raise WebsiteSourceRationalisationError(f"{label} exceeds its reviewed source bound.")
    try:
        with source.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            if not _same_file_identity(before, opened):
                raise WebsiteSourceRationalisationError(f"{label} changed before its handle opened.")
            payload = stream.read(MAX_REVIEWED_SOURCE_BYTES + 1)
    except OSError as exc:
        raise WebsiteSourceRationalisationError(f"{label} could not be read safely.") from exc
    after = source.lstat()
    if (
        len(payload) > MAX_REVIEWED_SOURCE_BYTES
        or not _same_file_identity(opened, after)
        or int(after.st_size) != len(payload)
        or _sha256_bytes(payload) != expected_sha256
    ):
        raise WebsiteSourceRationalisationError(f"{label} does not match its reviewed source pin.")
    return payload


def _utc_iso(value: datetime | None = None) -> str:
    instant = (value or datetime.now(UTC)).astimezone(UTC)
    return instant.isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_utc(value: object, *, label: str) -> datetime:
    if not isinstance(value, str) or not value or not value.endswith("Z"):
        raise WebsiteSourceRationalisationError(f"{label} must be canonical UTC ending in Z.")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00").astimezone(UTC)
    except ValueError as exc:
        raise WebsiteSourceRationalisationError(f"{label} must be valid ISO-8601.") from exc
    if _utc_iso(parsed) != value:
        raise WebsiteSourceRationalisationError(f"{label} must use second-precision canonical UTC.")
    return parsed


def _safe_run_id(value: object, *, label: str = "run_id") -> str:
    if not isinstance(value, str) or _RUN_ID.fullmatch(value) is None:
        raise WebsiteSourceRationalisationError(f"{label} is not a safe stable identifier.")
    return value


def _safe_relative_path(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise WebsiteSourceRationalisationError("Manifest path is not canonical.")
    candidate = Path(value)
    if candidate.is_absolute() or candidate.drive or value.startswith("/"):
        raise WebsiteSourceRationalisationError("Manifest path must be relative.")
    parts = value.split("/")
    if any(not part or part in {".", ".."} or ":" in part for part in parts):
        raise WebsiteSourceRationalisationError("Manifest path contains an unsafe component.")
    canonical = candidate.as_posix()
    if canonical != value:
        raise WebsiteSourceRationalisationError("Manifest path is not canonical.")
    return value


def _is_link_or_reparse(path: Path) -> bool:
    try:
        details = path.lstat()
    except OSError:
        return False
    attributes = int(getattr(details, "st_file_attributes", 0) or 0)
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0) or 0)
    return path.is_symlink() or bool(reparse_flag and attributes & reparse_flag)


def _regular_directory(path: Path, *, label: str) -> Path:
    lexical = Path(os.path.abspath(path))
    for component in (lexical, *lexical.parents):
        if not component.exists() and not component.is_symlink():
            continue
        if _is_link_or_reparse(component):
            raise WebsiteSourceRationalisationError(f"{label} may not traverse a link or reparse point.")
    if not lexical.is_dir():
        raise WebsiteSourceRationalisationError(f"{label} must be an existing ordinary directory.")
    return lexical


def _regular_file(path: Path, *, label: str, require_single_link: bool = True) -> Path:
    lexical = Path(os.path.abspath(path))
    for component in (lexical, *lexical.parents):
        if not component.exists() and not component.is_symlink():
            continue
        if _is_link_or_reparse(component):
            raise WebsiteSourceRationalisationError(f"{label} may not traverse a link or reparse point.")
    if not lexical.is_file():
        raise WebsiteSourceRationalisationError(f"{label} must be an existing ordinary file.")
    if require_single_link and int(lexical.stat().st_nlink) != 1:
        raise WebsiteSourceRationalisationError(f"{label} must have exactly one hard link.")
    return lexical


def _find_repo_root(start: Path | None = None) -> Path:
    candidate = (start or Path.cwd()).resolve()
    for root in (candidate, *candidate.parents):
        if (root / "pyproject.toml").is_file() and (root / SOURCE_ROOT).is_dir():
            return root
    raise WebsiteSourceRationalisationError(
        "Could not locate an Aureon repository with pyproject.toml and website/."
    )


def _canonical_repo_root() -> Path:
    implementation = _regular_file(Path(__file__), label="Loaded source-rationalisation implementation")
    root = implementation.parents[2]
    if implementation != Path(os.path.abspath(root / IMPLEMENTATION_PATH)):
        raise WebsiteSourceRationalisationError(
            "Loaded source-rationalisation implementation is outside its exact canonical path."
        )
    discovered = _find_repo_root(root)
    if discovered != root:
        raise WebsiteSourceRationalisationError("Loaded implementation has no exact canonical repository.")
    return root


def _require_trusted_launcher_attestation(root: Path) -> None:
    attestation = globals().get("__aureon_trusted_launcher_attestation__")
    implementation = _regular_file(
        root / IMPLEMENTATION_PATH,
        label="Attested source-rationalisation implementation",
    )
    launcher = _regular_file(root / TRUSTED_LAUNCHER_PATH, label="Trusted isolated launcher")
    _read_reviewed_source_bytes(
        launcher,
        REVIEWED_TRUSTED_LAUNCHER_SHA256,
        label="Trusted isolated launcher",
    )
    expected = {
        "launcher_path": str(launcher),
        "launcher_sha256": REVIEWED_TRUSTED_LAUNCHER_SHA256,
        "planner_path": str(implementation),
        "planner_sha256": _sha256_file(implementation),
        "isolated": True,
        "no_site": True,
        "dont_write_bytecode": True,
    }
    if not isinstance(attestation, dict) or attestation != expected:
        raise WebsiteSourceRationalisationError(
            "Production planner requires exact isolated-launcher attestation."
        )


def _manifest(root: Path) -> list[dict[str, object]]:
    source = _regular_directory(root, label="Canonical website source")
    source_real = source.resolve(strict=True)
    pending = [source]
    files: list[Path] = []
    total_bytes = 0
    seen_casefold: set[str] = set()
    while pending:
        directory = pending.pop()
        try:
            directory.resolve(strict=True).relative_to(source_real)
            entries = sorted(os.scandir(directory), key=lambda item: item.name)
        except (OSError, ValueError) as exc:
            raise WebsiteSourceRationalisationError(
                "Canonical website source changed or escaped while enumerated."
            ) from exc
        for entry in entries:
            path = Path(entry.path)
            if _is_link_or_reparse(path):
                raise WebsiteSourceRationalisationError(
                    f"Canonical website source contains a link or reparse point: {path}"
                )
            details = path.lstat()
            try:
                path.resolve(strict=True).relative_to(source_real)
            except (OSError, ValueError) as exc:
                raise WebsiteSourceRationalisationError(
                    f"Canonical website source path escaped its root: {path}"
                ) from exc
            if stat.S_ISDIR(details.st_mode):
                pending.append(path)
                continue
            if not stat.S_ISREG(details.st_mode) or int(details.st_nlink) != 1:
                raise WebsiteSourceRationalisationError(
                    f"Canonical website source files must be ordinary and single-link: {path}"
                )
            relative = _safe_relative_path(path.relative_to(source).as_posix())
            folded = relative.casefold()
            if folded in seen_casefold:
                raise WebsiteSourceRationalisationError(
                    f"Canonical website source contains a case-colliding path: {relative}"
                )
            seen_casefold.add(folded)
            files.append(path)
            total_bytes += int(details.st_size)
            if len(files) > MAX_FILES or total_bytes > MAX_TREE_BYTES:
                raise WebsiteSourceRationalisationError("Canonical website source exceeds planning bounds.")
    rows = [
        {
            "path": path.relative_to(source).as_posix(),
            "bytes": int(path.stat().st_size),
            "sha256": _sha256_file(path),
        }
        for path in sorted(files, key=lambda item: item.relative_to(source).as_posix())
    ]
    return rows


def _manifest_index(
    rows: object,
    *,
    label: str,
    require_sorted: bool = True,
) -> dict[str, dict[str, object]]:
    if not isinstance(rows, list):
        raise WebsiteSourceRationalisationError(f"{label} must be a JSON array.")
    result: dict[str, dict[str, object]] = {}
    seen_casefold: set[str] = set()
    for item in rows:
        if not isinstance(item, dict) or set(item) != _MANIFEST_ROW_FIELDS:
            raise WebsiteSourceRationalisationError(
                f"{label} rows must contain exactly path, bytes, and sha256."
            )
        path = _safe_relative_path(item.get("path"))
        byte_count = item.get("bytes")
        sha256 = item.get("sha256")
        if type(byte_count) is not int or byte_count < 0:
            raise WebsiteSourceRationalisationError(f"{label} byte count is invalid for {path}.")
        if not isinstance(sha256, str) or _SHA256.fullmatch(sha256) is None:
            raise WebsiteSourceRationalisationError(f"{label} SHA-256 is invalid for {path}.")
        if path in result or path.casefold() in seen_casefold:
            raise WebsiteSourceRationalisationError(f"{label} path is duplicated: {path}.")
        seen_casefold.add(path.casefold())
        result[path] = {"path": path, "bytes": byte_count, "sha256": sha256}
    if require_sorted and list(result) != sorted(result):
        raise WebsiteSourceRationalisationError(f"{label} must be sorted by canonical path.")
    return result


def _footprint_category(path: str) -> str:
    suffix = Path(path).suffix.casefold()
    if suffix in {".html", ".htm"}:
        return "html"
    if suffix == ".css":
        return "css"
    if suffix in {".js", ".mjs", ".cjs"}:
        return "javascript"
    if suffix in _IMAGE_SUFFIXES:
        return "image"
    if suffix in _FONT_SUFFIXES:
        return "font"
    if suffix in _MEDIA_SUFFIXES:
        return "media"
    return "other"


def _manifest_byte_count(row: Mapping[str, object]) -> int:
    value = row.get("bytes")
    if type(value) is not int or value < 0:
        raise WebsiteSourceRationalisationError("Manifest row byte count is invalid.")
    return value


def _fixed_footprint_projection(
    rows: Sequence[Mapping[str, object]],
    *,
    policy_sha256: str,
) -> dict[str, object]:
    categories = {"css": 0, "image": 0}
    largest_path = ""
    largest_category = "none"
    largest_bytes = 0
    for row in rows:
        path = str(row["path"])
        byte_count = _manifest_byte_count(row)
        category = _footprint_category(path)
        if category in categories:
            categories[category] += byte_count
        if category in {"image", "font", "media", "other"} and (
            byte_count > largest_bytes
            or (byte_count == largest_bytes and path.casefold() < largest_path.casefold())
        ):
            largest_path = path
            largest_category = category
            largest_bytes = byte_count

    total = sum(_manifest_byte_count(row) for row in rows)
    maxima = {
        "total": FIXED_FOOTPRINT_LIMITS["max_total_bytes"],
        "image": FIXED_FOOTPRINT_LIMITS["max_image_bytes"],
        "css": FIXED_FOOTPRINT_LIMITS["max_css_bytes"],
        "single-asset": FIXED_FOOTPRINT_LIMITS["max_single_asset_bytes"],
    }
    observed = {
        "total": total,
        "image": categories["image"],
        "css": categories["css"],
        "single-asset": largest_bytes,
    }
    violation_ids = [
        f"resource-byte-budget-exceeded:{category}"
        for category in ("total", "image", "css")
        if observed[category] > maxima[category]
    ]
    if observed["single-asset"] > maxima["single-asset"]:
        violation_ids.append("single-asset-budget-exceeded")
    return {
        "policy_path": MOTION_POLICY_PATH.as_posix(),
        "policy_sha256": policy_sha256,
        "max_total_bytes": maxima["total"],
        "projected_total_bytes": total,
        "total_overage_bytes": max(0, total - maxima["total"]),
        "max_image_bytes": maxima["image"],
        "projected_image_bytes": categories["image"],
        "image_overage_bytes": max(0, categories["image"] - maxima["image"]),
        "max_css_bytes": maxima["css"],
        "projected_css_bytes": categories["css"],
        "css_overage_bytes": max(0, categories["css"] - maxima["css"]),
        "max_single_asset_bytes": maxima["single-asset"],
        "projected_largest_single_asset_bytes": largest_bytes,
        "largest_single_asset_path": largest_path,
        "largest_single_asset_category": largest_category,
        "single_asset_overage_bytes": max(0, largest_bytes - maxima["single-asset"]),
        "violation_ids": violation_ids,
        "within_fixed_footprint_limits": not violation_ids,
        "state": "blocked-candidate-qa-not-run",
        "eligible_for_next_local_gate": False,
        "candidate_qa_authority": "none",
    }


def _execution_binding(
    root: Path,
    *,
    implementation_sha256: str,
    production: bool,
) -> dict[str, object]:
    environment = _sanitized_environment() if production else {"test_fixture": "no-authority"}
    return {
        "mode": "fixed-production" if production else "injected-test-fixture",
        "repo_root": str(root),
        "implementation_path": IMPLEMENTATION_PATH.as_posix(),
        "implementation_sha256": implementation_sha256,
        "trusted_launcher_path": TRUSTED_LAUNCHER_PATH.as_posix(),
        "reviewed_trusted_launcher_sha256": REVIEWED_TRUSTED_LAUNCHER_SHA256,
        "launcher_attested": production,
        "release_builder_path": RELEASE_BUILDER_PATH.as_posix(),
        "reviewed_release_builder_sha256": REVIEWED_RELEASE_BUILDER_SHA256,
        "powershell_path": str(POWERSHELL_EXECUTABLE),
        "reviewed_powershell_sha256": REVIEWED_POWERSHELL_SHA256,
        "motion_policy_path": MOTION_POLICY_PATH.as_posix(),
        "reviewed_motion_policy_sha256": REVIEWED_MOTION_POLICY_SHA256,
        "secure_writer_path": SECURE_WRITER_PATH.as_posix(),
        "reviewed_secure_writer_sha256": REVIEWED_SECURE_WRITER_SHA256,
        "runner_id": FIXED_RUNNER_ID if production else TEST_FIXTURE_RUNNER_ID,
        "environment_policy_id": (SANITIZED_ENVIRONMENT_POLICY_ID if production else TEST_FIXTURE_RUNNER_ID),
        "environment_sha256": _json_sha256(environment),
        "production_writable": production,
    }


def _tree_sha256(rows: Sequence[Mapping[str, object]]) -> str:
    # Exact compatibility with design_candidate_control._tree_summary:
    # SHA-256(canonical JSON([{path, sha256, bytes}, ...])) in case-sensitive path order.
    ordered = [dict(row) for row in sorted(rows, key=lambda item: str(item["path"]))]
    return _json_sha256(ordered)


def _summary(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    normalised = [dict(row) for row in rows]
    _manifest_index(normalised, label="Manifest")
    return {
        "tree_sha256": _tree_sha256(normalised),
        "manifest_sha256": _json_sha256(normalised),
        "file_count": len(normalised),
        "total_bytes": sum(_manifest_byte_count(row) for row in normalised),
        "files": normalised,
    }


def _sanitized_environment() -> dict[str, str]:
    windows_root = POWERSHELL_EXECUTABLE.parents[3]
    return {
        "COMSPEC": str(windows_root / "System32" / "cmd.exe"),
        "PATHEXT": ".COM;.EXE;.BAT;.CMD",
        "POWERSHELL_TELEMETRY_OPTOUT": "1",
        "SystemRoot": str(windows_root),
        "WINDIR": str(windows_root),
    }


def _default_runner(command: Sequence[str], cwd: Path, reviewed_source: bytes) -> CommandResult:
    if _sha256_bytes(reviewed_source) != REVIEWED_RELEASE_BUILDER_SHA256:
        raise WebsiteSourceRationalisationError(
            "Fixed runner received release-builder bytes outside the reviewed source pin."
        )
    overflow = threading.Event()
    reader_errors: list[OSError] = []
    stdout_buffer = bytearray()
    stderr_buffer = bytearray()
    try:
        process = subprocess.Popen(  # noqa: S603 - fixed executable and argument vector
            list(command),
            cwd=cwd,
            close_fds=True,
            env=_sanitized_environment(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
    except OSError as exc:
        raise WebsiteSourceRationalisationError(
            "Fixed read-only release-builder verification could not complete."
        ) from exc

    def drain(stream: Any, target: bytearray) -> None:
        try:
            while block := stream.read(64 * 1024):
                remaining = MAX_PROCESS_OUTPUT_BYTES + 1 - len(target)
                if remaining > 0:
                    target.extend(block[:remaining])
                if len(target) > MAX_PROCESS_OUTPUT_BYTES:
                    overflow.set()
                    try:
                        process.kill()
                    except OSError:
                        pass
        except OSError as exc:
            reader_errors.append(exc)

    if process.stdin is None or process.stdout is None or process.stderr is None:
        process.kill()
        raise WebsiteSourceRationalisationError("Fixed runner could not establish bounded pipes.")
    stdout_thread = threading.Thread(target=drain, args=(process.stdout, stdout_buffer), daemon=True)
    stderr_thread = threading.Thread(target=drain, args=(process.stderr, stderr_buffer), daemon=True)
    stdout_thread.start()
    stderr_thread.start()
    try:
        process.stdin.write(base64.b64encode(reviewed_source))
        process.stdin.close()
        returncode = process.wait(timeout=PROCESS_TIMEOUT_SECONDS)
    except (BrokenPipeError, OSError, subprocess.TimeoutExpired) as exc:
        try:
            process.kill()
            process.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            pass
        raise WebsiteSourceRationalisationError(
            "Fixed read-only release-builder verification could not complete."
        ) from exc
    finally:
        stdout_thread.join(timeout=5)
        stderr_thread.join(timeout=5)
    if stdout_thread.is_alive() or stderr_thread.is_alive() or reader_errors:
        raise WebsiteSourceRationalisationError("Fixed runner could not close its bounded output pipes.")
    if overflow.is_set():
        raise WebsiteSourceRationalisationError("Release-builder verification output exceeded its bound.")
    return CommandResult(returncode, bytes(stdout_buffer), bytes(stderr_buffer))


def _closure_command(root: Path) -> list[str]:
    def encoded(value: str) -> str:
        return base64.b64encode(value.encode("utf-8")).decode("ascii")

    wrapper = "\n".join(
        (
            "$ErrorActionPreference = 'Stop'",
            "$raw = [Convert]::FromBase64String([Console]::In.ReadToEnd())",
            "$sha = [BitConverter]::ToString(([Security.Cryptography.SHA256]::Create()).ComputeHash($raw)).Replace('-', '')",
            f"if ($sha -cne '{REVIEWED_RELEASE_BUILDER_SHA256}') {{ throw 'Reviewed builder hash mismatch.' }}",
            "$utf8 = New-Object System.Text.UTF8Encoding($false, $true)",
            "$builder = [ScriptBlock]::Create($utf8.GetString($raw))",
            f"$website = $utf8.GetString([Convert]::FromBase64String('{encoded(str(root / SOURCE_ROOT))}'))",
            f"$output = $utf8.GetString([Convert]::FromBase64String('{encoded(str(root / ARTIFACT_ROOT / 'verify-only-no-output'))}'))",
            f"& $builder -WebsiteRoot $website -OutputDirectory $output -Release '{RELEASE}' -VerifyOnly",
        )
    )
    encoded_wrapper = base64.b64encode(wrapper.encode("utf-16-le")).decode("ascii")
    return [
        str(POWERSHELL_EXECUTABLE),
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-EncodedCommand",
        encoded_wrapper,
    ]


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise WebsiteSourceRationalisationError(f"Duplicate JSON object key: {key}")
        value[key] = item
    return value


def _strict_json_bytes(raw: bytes, *, label: str) -> dict[str, Any]:
    if len(raw) > MAX_JSON_BYTES:
        raise WebsiteSourceRationalisationError(f"{label} exceeds the JSON input bound.")
    try:
        value = json.loads(
            raw.decode("utf-8-sig"),
            object_pairs_hook=_unique_json_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                WebsiteSourceRationalisationError(f"{label} contains non-finite JSON: {token}")
            ),
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise WebsiteSourceRationalisationError(f"{label} is not strict UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise WebsiteSourceRationalisationError(f"{label} must be a JSON object.")
    return value


def _closure_projection(
    *,
    root: Path,
    source_rows: Sequence[Mapping[str, object]],
    tool_bytes: bytes,
    runner: CommandRunner,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    if _sha256_bytes(tool_bytes) != REVIEWED_RELEASE_BUILDER_SHA256:
        raise WebsiteSourceRationalisationError("Release-builder execution bytes changed from their pin.")
    command = _closure_command(root)
    result = runner(command, root, tool_bytes)
    if result.returncode != 0:
        diagnostic = (result.stderr or result.stdout)[:1000].decode("utf-8", errors="replace")
        raise WebsiteSourceRationalisationError(
            "Fixed VerifyOnly release-builder command failed: " + diagnostic
        )
    payload = _strict_json_bytes(result.stdout, label="Release-builder VerifyOnly output")
    expected_top = {
        "State",
        "Release",
        "SourceRoot",
        "FileCount",
        "TotalBytes",
        "PackageRoot",
        "RemoteRoot",
        "EntryFiles",
        "Closure",
        "Files",
    }
    if set(payload) != expected_top:
        raise WebsiteSourceRationalisationError("Release-builder VerifyOnly output fields changed.")
    if (
        payload.get("State") != "release-plan-verified"
        or payload.get("Release") != RELEASE
        or payload.get("SourceRoot") != str(root / SOURCE_ROOT)
        or payload.get("PackageRoot") != "/"
        or payload.get("RemoteRoot") != "action-time-confirmation-required"
    ):
        raise WebsiteSourceRationalisationError("Release-builder VerifyOnly identity changed.")

    raw_files = payload.get("Files")
    if not isinstance(raw_files, list):
        raise WebsiteSourceRationalisationError("Release-builder retained files are missing.")
    retained_rows: list[dict[str, object]] = []
    for item in raw_files:
        if not isinstance(item, dict) or set(item) != {"Path", "Bytes", "Sha256"}:
            raise WebsiteSourceRationalisationError("Release-builder retained row fields changed.")
        retained_rows.append(
            {
                "path": _safe_relative_path(item.get("Path")),
                "bytes": item.get("Bytes"),
                "sha256": str(item.get("Sha256") or "").upper(),
            }
        )
    retained_index = _manifest_index(
        retained_rows,
        label="Retained projection",
        require_sorted=False,
    )
    retained_rows = [retained_index[path] for path in sorted(retained_index)]
    source_index = _manifest_index([dict(row) for row in source_rows], label="Source manifest")
    for path, row in retained_index.items():
        if source_index.get(path) != row:
            raise WebsiteSourceRationalisationError(
                f"Release-builder retained row is not an exact current source file: {path}"
            )
    if (
        type(payload.get("FileCount")) is not int
        or payload.get("FileCount") != len(retained_rows)
        or type(payload.get("TotalBytes")) is not int
        or payload.get("TotalBytes") != sum(_manifest_byte_count(row) for row in retained_rows)
    ):
        raise WebsiteSourceRationalisationError("Release-builder retained totals are inconsistent.")

    raw_entries = payload.get("EntryFiles")
    if not isinstance(raw_entries, list) or not all(isinstance(item, str) for item in raw_entries):
        raise WebsiteSourceRationalisationError("Release-builder entry files are malformed.")
    raw_entry_paths = [_safe_relative_path(item) for item in raw_entries]
    if len(raw_entry_paths) != len(set(raw_entry_paths)):
        raise WebsiteSourceRationalisationError("Release-builder entry files are duplicated.")
    entries = sorted(raw_entry_paths)
    if not set(entries).issubset(retained_index):
        raise WebsiteSourceRationalisationError(
            "Release-builder entry files are incomplete or non-canonical."
        )

    closure = payload.get("Closure")
    expected_closure = {
        "state",
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
        "remote_origins",
        "files_by_extension",
    }
    if not isinstance(closure, dict) or set(closure) != expected_closure:
        raise WebsiteSourceRationalisationError("Release-builder closure fields changed.")
    integer_fields = expected_closure.difference({"state", "remote_origins", "files_by_extension"})
    if any(type(closure.get(field)) is not int or int(closure[field]) < 0 for field in integer_fields):
        raise WebsiteSourceRationalisationError("Release-builder closure counts are malformed.")
    if (
        closure.get("state") != "verified-complete"
        or closure.get("missing_local_reference_count") != 0
        or closure.get("missing_fragment_reference_count") != 0
        or closure.get("included_local_reference_count") != closure.get("local_reference_count")
        or closure.get("verified_fragment_reference_count") != closure.get("fragment_reference_count")
        or closure.get("entry_file_count") != len(entries)
        or int(closure.get("entry_file_count", 0)) + int(closure.get("discovered_file_count", 0))
        != len(retained_rows)
    ):
        raise WebsiteSourceRationalisationError(
            "Release-builder did not prove a complete dependency and fragment closure."
        )
    raw_origins = closure.get("remote_origins")
    if not isinstance(raw_origins, list) or not all(isinstance(item, str) for item in raw_origins):
        raise WebsiteSourceRationalisationError("Release-builder remote origins are malformed.")
    origins = list(raw_origins)
    if len(origins) != len(set(origins)):
        raise WebsiteSourceRationalisationError("Release-builder remote origins are duplicated.")
    origins.sort()
    for origin in origins:
        parsed = urlparse(origin)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.params
            or parsed.query
            or parsed.fragment
        ):
            raise WebsiteSourceRationalisationError(
                f"Release-builder returned a non-canonical HTTPS origin: {origin}"
            )

    retained_summary = _summary(retained_rows)
    return (
        {
            "tool_path": RELEASE_BUILDER_PATH.as_posix(),
            "tool_sha256": _sha256_bytes(tool_bytes),
            "command": command,
            "release": RELEASE,
            "verify_only": True,
            "state": "verified-complete",
            "entry_files": entries,
            "local_reference_count": closure["local_reference_count"],
            "missing_local_reference_count": 0,
            "missing_fragment_reference_count": 0,
            "remote_origins": origins,
            "retained_manifest_sha256": retained_summary["manifest_sha256"],
        },
        retained_rows,
    )


def _exact_object(value: object, fields: frozenset[str], *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise WebsiteSourceRationalisationError(f"{label} fields are incomplete or unexpected.")
    return value


def _require_sha256(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise WebsiteSourceRationalisationError(f"{label} must be an uppercase SHA-256.")
    return value


def _require_summary(value: object, *, label: str) -> dict[str, Any]:
    summary = _exact_object(value, _SUMMARY_FIELDS, label=label)
    rows = summary.get("files")
    index = _manifest_index(rows, label=f"{label}.files")
    expected = _summary(list(index.values()))
    if summary != expected:
        raise WebsiteSourceRationalisationError(f"{label} does not match its exact manifest.")
    return summary


def _require_source_rationalisation_plan(
    value: object,
    *,
    root: Path,
    production: bool,
) -> dict[str, Any]:
    """Require the exact recursive plan contract for one execution mode."""

    plan = _exact_object(value, _PLAN_FIELDS, label="Source-rationalisation plan")
    if plan.get("schema") != PLAN_SCHEMA or plan.get("state") != "proposal-only":
        raise WebsiteSourceRationalisationError("Source-rationalisation plan identity is invalid.")
    _parse_utc(plan.get("generated_at"), label="plan.generated_at")
    _safe_run_id(plan.get("run_id"))
    if plan.get("authority") != PLAN_AUTHORITY:
        raise WebsiteSourceRationalisationError("Source-rationalisation plan authority changed.")

    execution = _exact_object(
        plan.get("execution_binding"),
        _EXECUTION_FIELDS,
        label="plan.execution_binding",
    )
    implementation = _regular_file(
        root / IMPLEMENTATION_PATH,
        label="Bound source-rationalisation implementation",
    )
    expected_execution = _execution_binding(
        root,
        implementation_sha256=_sha256_file(implementation),
        production=production,
    )
    if execution != expected_execution:
        raise WebsiteSourceRationalisationError(
            "Source-rationalisation implementation, runner, environment, or repository binding changed."
        )
    reviewed_sources = (
        (TRUSTED_LAUNCHER_PATH, REVIEWED_TRUSTED_LAUNCHER_SHA256, "isolated launcher"),
        (RELEASE_BUILDER_PATH, REVIEWED_RELEASE_BUILDER_SHA256, "release builder"),
        (MOTION_POLICY_PATH, REVIEWED_MOTION_POLICY_SHA256, "motion policy"),
        (SECURE_WRITER_PATH, REVIEWED_SECURE_WRITER_SHA256, "immutable writer"),
    )
    for relative, expected_sha256, label in reviewed_sources:
        source_file = _regular_file(root / relative, label=f"Reviewed {label} source")
        if _sha256_file(source_file) != expected_sha256:
            raise WebsiteSourceRationalisationError(f"Reviewed {label} source pin changed.")
    powershell = _regular_file(
        POWERSHELL_EXECUTABLE,
        label="Reviewed PowerShell executable",
        require_single_link=False,
    )
    if _sha256_file(powershell) != REVIEWED_POWERSHELL_SHA256:
        raise WebsiteSourceRationalisationError("Reviewed PowerShell binary pin changed.")

    source = _exact_object(plan.get("source_binding"), _SOURCE_FIELDS, label="plan.source_binding")
    if source.get("root") != SOURCE_ROOT.as_posix():
        raise WebsiteSourceRationalisationError("Source-rationalisation source root is not canonical.")
    source_summary = {key: source[key] for key in _SUMMARY_FIELDS}
    _require_summary(source_summary, label="plan.source_binding")

    retained = _require_summary(plan.get("retained_projection"), label="plan.retained_projection")
    source_index = _manifest_index(source.get("files"), label="plan.source_binding.files")
    retained_index = _manifest_index(retained.get("files"), label="plan.retained_projection.files")
    if not retained_index or any(source_index.get(path) != row for path, row in retained_index.items()):
        raise WebsiteSourceRationalisationError("Retained projection is not an exact source subset.")

    omitted = _exact_object(plan.get("omitted_projection"), _OMITTED_FIELDS, label="plan.omitted_projection")
    raw_omitted = omitted.get("files")
    if not isinstance(raw_omitted, list):
        raise WebsiteSourceRationalisationError("plan.omitted_projection.files must be an array.")
    omitted_plain: list[dict[str, object]] = []
    omitted_paths: set[str] = set()
    for item in raw_omitted:
        if not isinstance(item, dict) or set(item) != _OMITTED_ROW_FIELDS:
            raise WebsiteSourceRationalisationError("Omitted rows use an unsupported shape.")
        if item.get("reason") != "not-in-public-runtime-closure":
            raise WebsiteSourceRationalisationError("Omitted row reason is not fixed.")
        row = {key: item[key] for key in _MANIFEST_ROW_FIELDS}
        path = _safe_relative_path(row["path"])
        if path in omitted_paths:
            raise WebsiteSourceRationalisationError("Omitted path is duplicated.")
        omitted_paths.add(path)
        omitted_plain.append(row)
    omitted_index = _manifest_index(omitted_plain, label="plan.omitted_projection.files")
    expected_omitted = {
        "manifest_sha256": _json_sha256(raw_omitted),
        "file_count": len(raw_omitted),
        "total_bytes": sum(_manifest_byte_count(row) for row in omitted_plain),
        "files": raw_omitted,
    }
    if omitted != expected_omitted:
        raise WebsiteSourceRationalisationError("Omitted projection totals or digest changed.")
    if set(retained_index).intersection(omitted_index) or set(retained_index).union(omitted_index) != set(
        source_index
    ):
        raise WebsiteSourceRationalisationError(
            "Retained and omitted projections are not a disjoint complete source partition."
        )
    if any(source_index[path] != row for path, row in omitted_index.items()):
        raise WebsiteSourceRationalisationError("Omitted projection changed a source row.")

    closure = _exact_object(plan.get("closure_binding"), _CLOSURE_FIELDS, label="plan.closure_binding")
    if (
        closure.get("tool_path") != RELEASE_BUILDER_PATH.as_posix()
        or closure.get("tool_sha256") != REVIEWED_RELEASE_BUILDER_SHA256
        or closure.get("release") != RELEASE
        or closure.get("verify_only") is not True
        or closure.get("state") != "verified-complete"
        or closure.get("missing_local_reference_count") != 0
        or closure.get("missing_fragment_reference_count") != 0
        or closure.get("retained_manifest_sha256") != retained.get("manifest_sha256")
    ):
        raise WebsiteSourceRationalisationError("Source-rationalisation closure binding changed.")
    _require_sha256(closure.get("tool_sha256"), label="plan.closure_binding.tool_sha256")
    entries = closure.get("entry_files")
    if (
        not isinstance(entries, list)
        or not entries
        or not all(isinstance(item, str) for item in entries)
        or entries != sorted(set(entries))
        or not set(entries).issubset(retained_index)
    ):
        raise WebsiteSourceRationalisationError("Source-rationalisation entry-file binding changed.")
    origins = closure.get("remote_origins")
    if not isinstance(origins, list) or origins != sorted(set(origins)):
        raise WebsiteSourceRationalisationError("Source-rationalisation remote origins changed.")
    command = closure.get("command")
    if (
        not isinstance(command, list)
        or not all(isinstance(item, str) for item in command)
        or command != _closure_command(root)
    ):
        raise WebsiteSourceRationalisationError("Source-rationalisation command binding is malformed.")

    budget = _exact_object(
        plan.get("motion_budget_projection"), _BUDGET_FIELDS, label="plan.motion_budget_projection"
    )
    _require_sha256(budget.get("policy_sha256"), label="plan.motion_budget_projection.policy_sha256")
    if budget.get("policy_sha256") != REVIEWED_MOTION_POLICY_SHA256:
        raise WebsiteSourceRationalisationError("Plan motion-policy source pin changed.")
    expected_budget = _fixed_footprint_projection(
        retained["files"],
        policy_sha256=str(budget["policy_sha256"]),
    )
    if budget != expected_budget:
        raise WebsiteSourceRationalisationError("Motion-budget projection is not the fixed blocked contract.")

    payload = dict(plan)
    payload_hash = payload.pop("payload_sha256")
    _require_sha256(payload_hash, label="plan.payload_sha256")
    if payload_hash != _json_sha256(payload):
        raise WebsiteSourceRationalisationError("Source-rationalisation plan payload hash changed.")
    return plan


def require_source_rationalisation_plan(value: object) -> dict[str, Any]:
    """Require a production plan bound to this loaded module's canonical repository."""

    return _require_source_rationalisation_plan(
        value,
        root=_canonical_repo_root(),
        production=True,
    )


def _create_source_rationalisation_plan(
    *,
    root: Path,
    run_id: str | None = None,
    now: datetime | None = None,
    test_runner: CommandRunner | None = None,
    production: bool,
) -> dict[str, Any]:
    """Build one plan; injected execution is permanently marked test-only."""

    root = _find_repo_root(root)
    runner: CommandRunner
    if production:
        if root != _canonical_repo_root() or test_runner is not None:
            raise WebsiteSourceRationalisationError(
                "Production planning accepts only the canonical repository and fixed runner."
            )
        _require_trusted_launcher_attestation(root)
        runner = _default_runner
    else:
        if test_runner is None:
            raise WebsiteSourceRationalisationError(
                "Test-only planning requires its injected fixture runner."
            )
        runner = test_runner
    site = _regular_directory(root / SOURCE_ROOT, label="Canonical website source")
    if site != Path(os.path.abspath(root / SOURCE_ROOT)):
        raise WebsiteSourceRationalisationError("Canonical website source path changed.")
    tool = _regular_file(root / RELEASE_BUILDER_PATH, label="Fixed release-builder tool")
    policy = _regular_file(root / MOTION_POLICY_PATH, label="Fixed motion-policy compiler")
    writer = _regular_file(root / SECURE_WRITER_PATH, label="Reviewed immutable-artifact writer")
    powershell = _regular_file(
        POWERSHELL_EXECUTABLE,
        label="Reviewed PowerShell executable",
        require_single_link=False,
    )
    implementation = _regular_file(
        root / IMPLEMENTATION_PATH,
        label="Bound source-rationalisation implementation",
    )
    launcher = _regular_file(root / TRUSTED_LAUNCHER_PATH, label="Trusted isolated launcher")
    resolved_run_id = _safe_run_id(run_id or uuid.uuid4().hex)

    source_before = _manifest(site)
    source_summary = _summary(source_before)
    tool_bytes = _read_reviewed_source_bytes(
        tool,
        REVIEWED_RELEASE_BUILDER_SHA256,
        label="Fixed release-builder source",
    )
    tool_sha256_before = _sha256_bytes(tool_bytes)
    powershell_sha256_before = _sha256_file(powershell)
    if powershell_sha256_before != REVIEWED_POWERSHELL_SHA256:
        raise WebsiteSourceRationalisationError(
            "PowerShell executable does not match the reviewed binary pin; execution refused."
        )
    policy_sha256_before = _sha256_file(policy)
    if policy_sha256_before != REVIEWED_MOTION_POLICY_SHA256:
        raise WebsiteSourceRationalisationError(
            "Fixed motion-policy bytes do not match the reviewed source pin."
        )
    writer_sha256_before = _sha256_file(writer)
    if writer_sha256_before != REVIEWED_SECURE_WRITER_SHA256:
        raise WebsiteSourceRationalisationError(
            "Immutable-writer bytes do not match the reviewed source pin."
        )
    implementation_sha256_before = _sha256_file(implementation)
    launcher_sha256_before = _sha256_bytes(
        _read_reviewed_source_bytes(
            launcher,
            REVIEWED_TRUSTED_LAUNCHER_SHA256,
            label="Trusted isolated launcher",
        )
    )
    closure, retained_rows = _closure_projection(
        root=root,
        source_rows=source_before,
        tool_bytes=tool_bytes,
        runner=runner,
    )
    source_after = _manifest(site)
    if (
        source_after != source_before
        or _sha256_file(tool) != tool_sha256_before
        or _sha256_file(policy) != policy_sha256_before
        or _sha256_file(writer) != writer_sha256_before
        or _sha256_file(powershell) != powershell_sha256_before
        or _sha256_file(implementation) != implementation_sha256_before
        or _sha256_file(launcher) != launcher_sha256_before
    ):
        raise WebsiteSourceRationalisationError(
            "Canonical source, implementation, release-builder, or motion policy changed during planning."
        )
    if closure.get("tool_sha256") != tool_sha256_before:
        raise WebsiteSourceRationalisationError("Release-builder tool binding changed during planning.")

    retained_summary = _summary(retained_rows)
    retained_paths = {str(row["path"]) for row in retained_rows}
    omitted_plain = [dict(row) for row in source_before if str(row["path"]) not in retained_paths]
    omitted_rows = [{**row, "reason": "not-in-public-runtime-closure"} for row in omitted_plain]
    plan: dict[str, Any] = {
        "schema": PLAN_SCHEMA,
        "generated_at": _utc_iso(now),
        "run_id": resolved_run_id,
        "state": "proposal-only",
        "source_binding": {"root": SOURCE_ROOT.as_posix(), **source_summary},
        "closure_binding": closure,
        "retained_projection": retained_summary,
        "omitted_projection": {
            "manifest_sha256": _json_sha256(omitted_rows),
            "file_count": len(omitted_rows),
            "total_bytes": sum(_manifest_byte_count(row) for row in omitted_plain),
            "files": omitted_rows,
        },
        "motion_budget_projection": _fixed_footprint_projection(
            retained_rows,
            policy_sha256=policy_sha256_before,
        ),
        "execution_binding": _execution_binding(
            root,
            implementation_sha256=implementation_sha256_before,
            production=production,
        ),
        "authority": dict(PLAN_AUTHORITY),
    }
    plan["payload_sha256"] = _json_sha256(plan)
    _require_source_rationalisation_plan(plan, root=root, production=production)
    return plan


def create_source_rationalisation_plan(*, run_id: str | None = None) -> dict[str, Any]:
    """Create a production proposal only for this module's canonical repository."""

    return _create_source_rationalisation_plan(
        root=_canonical_repo_root(),
        run_id=run_id,
        production=True,
    )


def _create_test_only_source_rationalisation_plan(
    *,
    repo_root: Path,
    runner: CommandRunner,
    run_id: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Create a non-writable fixture plan for hostile unit tests only."""

    return _create_source_rationalisation_plan(
        root=repo_root,
        run_id=run_id,
        now=now,
        test_runner=runner,
        production=False,
    )


def _json_artifact_bytes(value: Mapping[str, Any]) -> bytes:
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
        raise WebsiteSourceRationalisationError("Artifact is not deterministic standard JSON.") from exc


def _ensure_artifact_parent(root: Path, parent: Path, *, allowed_root: Path) -> None:
    artifacts = _regular_directory(root / "artifacts", label="Aureon artifacts root")
    target_root = Path(os.path.abspath(allowed_root))
    try:
        target_root.relative_to(artifacts)
        Path(os.path.abspath(parent)).relative_to(target_root)
    except ValueError as exc:
        raise WebsiteSourceRationalisationError("Artifact output escaped its fixed root.") from exc
    current = artifacts
    for part in target_root.relative_to(artifacts).parts:
        current /= part
        if not current.exists():
            current.mkdir()
        _regular_directory(current, label="Source-rationalisation artifact directory")
    for part in Path(os.path.abspath(parent)).relative_to(target_root).parts:
        current /= part
        if not current.exists():
            current.mkdir()
        _regular_directory(current, label="Source-rationalisation artifact directory")


def _load_reviewed_secure_writer(root: Path) -> Any:
    """Authenticate immutable-writer bytes before executing that repo-local module."""

    source = _regular_file(root / SECURE_WRITER_PATH, label="Reviewed immutable-artifact writer")
    payload = _read_reviewed_source_bytes(
        source,
        REVIEWED_SECURE_WRITER_SHA256,
        label="Reviewed immutable-artifact writer",
    )
    module = ModuleType("_aureon_reviewed_source_rationalisation_immutable_writer")
    module.__file__ = str(source)
    module.__package__ = "aureon.operator"
    try:
        exec(compile(payload, str(source), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except (ImportError, OSError, SyntaxError) as exc:
        raise WebsiteSourceRationalisationError(
            "Reviewed immutable-writer import could not complete."
        ) from exc
    if not callable(getattr(module, "write_new_file", None)):
        raise WebsiteSourceRationalisationError("Reviewed immutable writer has no callable entrypoint.")
    return module


def write_source_rationalisation_plan(
    plan: Mapping[str, Any],
    output_path: Path,
) -> Path:
    """Persist one exact plan at its fixed path without replacement."""

    root = _canonical_repo_root()
    _require_trusted_launcher_attestation(root)
    controlled = require_source_rationalisation_plan(dict(plan))
    run_id = str(controlled["run_id"])
    expected = root / PLAN_ROOT / f"{run_id}.plan.v1.json"
    output = output_path if output_path.is_absolute() else root / output_path
    output = Path(os.path.abspath(output))
    if output != Path(os.path.abspath(expected)):
        raise WebsiteSourceRationalisationError(
            "Plan output must use source-rationalisations/plans/<run-id>.plan.v1.json."
        )
    _revalidate_plan_current(root, controlled)
    _ensure_artifact_parent(root, output.parent, allowed_root=root / PLAN_ROOT)
    raw = _json_artifact_bytes(controlled)
    writer = _load_reviewed_secure_writer(root)
    try:
        writer.write_new_file(output, raw)
    except OSError as exc:
        raise WebsiteSourceRationalisationError(
            f"Source-rationalisation plan could not be created immutably: {exc}"
        ) from exc
    if output.read_bytes() != raw:
        raise WebsiteSourceRationalisationError("Immutable plan failed exact byte read-back.")
    return output


def _read_json_file(path: Path, *, label: str) -> tuple[dict[str, Any], bytes]:
    file_path = _regular_file(path, label=label)
    raw = file_path.read_bytes()
    return _strict_json_bytes(raw, label=label), raw


def _relative_to_repo(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError as exc:
        raise WebsiteSourceRationalisationError("Evidence path escaped the Aureon repository.") from exc


def _controlled_input_path(root: Path, path: Path, *, allowed_root: Path, label: str) -> Path:
    candidate = path if path.is_absolute() else root / path
    lexical = _regular_file(candidate, label=label)
    try:
        lexical.relative_to(Path(os.path.abspath(allowed_root)))
    except ValueError as exc:
        raise WebsiteSourceRationalisationError(f"{label} escaped its controlled artifact root.") from exc
    return lexical


def _revalidate_plan_current(root: Path, plan: Mapping[str, Any]) -> None:
    site = _regular_directory(root / SOURCE_ROOT, label="Canonical website source")
    tool = _regular_file(root / RELEASE_BUILDER_PATH, label="Fixed release-builder tool")
    policy = _regular_file(root / MOTION_POLICY_PATH, label="Fixed motion-policy compiler")
    implementation = _regular_file(
        root / IMPLEMENTATION_PATH,
        label="Bound source-rationalisation implementation",
    )
    writer = _regular_file(root / SECURE_WRITER_PATH, label="Reviewed immutable-artifact writer")
    powershell = _regular_file(
        POWERSHELL_EXECUTABLE,
        label="Reviewed PowerShell executable",
        require_single_link=False,
    )
    source_rows = _manifest(site)
    current_summary = _summary(source_rows)
    source = plan["source_binding"]
    if current_summary != {key: source[key] for key in _SUMMARY_FIELDS}:
        raise WebsiteSourceRationalisationError("Canonical website source changed after planning.")
    closure = plan["closure_binding"]
    pinned_files = {
        "implementation": (implementation, plan["execution_binding"]["implementation_sha256"]),
        "release-builder": (tool, REVIEWED_RELEASE_BUILDER_SHA256),
        "motion-policy": (policy, REVIEWED_MOTION_POLICY_SHA256),
        "immutable-writer": (writer, REVIEWED_SECURE_WRITER_SHA256),
        "powershell": (powershell, REVIEWED_POWERSHELL_SHA256),
    }
    before_hashes = {label: _sha256_file(path) for label, (path, _expected) in pinned_files.items()}
    if any(before_hashes[label] != expected for label, (_path, expected) in pinned_files.items()):
        raise WebsiteSourceRationalisationError(
            "Implementation, release-builder, PowerShell, motion-policy, or writer pin changed."
        )
    tool_bytes = _read_reviewed_source_bytes(
        tool,
        REVIEWED_RELEASE_BUILDER_SHA256,
        label="Fixed release-builder source",
    )
    replay_closure, replay_rows = _closure_projection(
        root=root,
        source_rows=source_rows,
        tool_bytes=tool_bytes,
        runner=_default_runner,
    )
    if (
        _manifest(site) != source_rows
        or any(
            _sha256_file(path) != before_hashes[label] for label, (path, _expected) in pinned_files.items()
        )
        or replay_closure != closure
        or _summary(replay_rows) != plan["retained_projection"]
        or closure.get("command") != _closure_command(root)
    ):
        raise WebsiteSourceRationalisationError(
            "Fixed VerifyOnly replay or its bound sources changed after planning."
        )


def _require_owner_decision_shape(decision: object) -> dict[str, Any]:
    value = _exact_object(decision, _DECISION_FIELDS, label="Owner source-rationalisation decision")
    if (
        value.get("schema") != OWNER_DECISION_SCHEMA
        or value.get("decision") != "acknowledged-review-only"
        or value.get("scope") != "acknowledge-exact-source-rationalisation-proposal"
        or value.get("authority") != OWNER_DECISION_AUTHORITY
    ):
        raise WebsiteSourceRationalisationError("Owner decision identity or authority is invalid.")
    _safe_run_id(value.get("plan_run_id"), label="decision.plan_run_id")
    for field in (
        "plan_file_sha256",
        "plan_payload_sha256",
        "source_tree_sha256",
        "retained_tree_sha256",
        "omitted_manifest_sha256",
    ):
        _require_sha256(value.get(field), label=f"decision.{field}")
    acknowledged_by = value.get("acknowledged_by")
    note = value.get("note")
    if (
        not isinstance(acknowledged_by, str)
        or acknowledged_by != acknowledged_by.strip()
        or len(acknowledged_by) < 3
        or not any(character.isalpha() for character in acknowledged_by)
        or acknowledged_by.casefold() in _GENERIC_APPROVERS
    ):
        raise WebsiteSourceRationalisationError("Owner decision must identify a named human approver.")
    if not isinstance(note, str) or note != note.strip() or not note:
        raise WebsiteSourceRationalisationError("Owner decision note must be non-empty canonical text.")
    _parse_utc(value.get("acknowledged_at"), label="decision.acknowledged_at")
    _parse_utc(value.get("expires_at"), label="decision.expires_at")
    return value


def _check(identifier: str, passed: bool, message: str, **evidence: object) -> dict[str, object]:
    return {"id": identifier, "passed": bool(passed), "message": message, "evidence": evidence}


def _validate_owner_source_rationalisation_decision(
    plan_path: Path,
    decision_path: Path,
    *,
    now: datetime,
) -> dict[str, Any]:
    """Validate one decision at a caller-captured instant for deterministic replay."""

    root = _canonical_repo_root()
    _require_trusted_launcher_attestation(root)
    now = now.astimezone(UTC)
    plan_file = _controlled_input_path(
        root,
        plan_path,
        allowed_root=root / PLAN_ROOT,
        label="Source-rationalisation plan",
    )
    decision_file = _controlled_input_path(
        root,
        decision_path,
        allowed_root=root / OWNER_DECISION_ROOT,
        label="Owner source-rationalisation decision",
    )
    plan, plan_raw = _read_json_file(plan_file, label="Source-rationalisation plan")
    require_source_rationalisation_plan(plan)
    run_id = str(plan["run_id"])
    expected_plan = root / PLAN_ROOT / f"{run_id}.plan.v1.json"
    expected_decision = root / OWNER_DECISION_ROOT / f"{run_id}.decision.v1.json"
    if plan_file != Path(os.path.abspath(expected_plan)) or decision_file != Path(
        os.path.abspath(expected_decision)
    ):
        raise WebsiteSourceRationalisationError("Plan or decision does not use its exact run-bound path.")
    if plan_raw != _json_artifact_bytes(plan):
        raise WebsiteSourceRationalisationError("Persisted plan bytes are not the deterministic V1 encoding.")
    decision, decision_raw = _read_json_file(
        decision_file,
        label="Owner source-rationalisation decision",
    )

    checks: list[dict[str, object]] = []
    shape_error = ""
    try:
        controlled_decision = _require_owner_decision_shape(decision)
        shape_ok = True
    except WebsiteSourceRationalisationError as exc:
        controlled_decision = decision
        shape_ok = False
        shape_error = str(exc)
    checks.append(
        _check(
            "exact-owner-decision-contract",
            shape_ok,
            "Decision must use the exact named-owner review-only contract.",
            error=shape_error,
        )
    )

    plan_file_sha256 = _sha256_bytes(plan_raw)
    binding_ok = shape_ok and all(
        (
            controlled_decision.get("plan_run_id") == run_id,
            controlled_decision.get("plan_file_sha256") == plan_file_sha256,
            controlled_decision.get("plan_payload_sha256") == plan["payload_sha256"],
            controlled_decision.get("source_tree_sha256") == plan["source_binding"]["tree_sha256"],
            controlled_decision.get("retained_tree_sha256") == plan["retained_projection"]["tree_sha256"],
            controlled_decision.get("omitted_manifest_sha256")
            == plan["omitted_projection"]["manifest_sha256"],
        )
    )
    checks.append(
        _check(
            "exact-plan-binding",
            binding_ok,
            "Owner decision must bind the exact plan bytes, source, retained tree, and omissions.",
        )
    )

    timing_ok = False
    if shape_ok:
        try:
            reference = (now or datetime.now(UTC)).astimezone(UTC)
            generated_at = _parse_utc(plan["generated_at"], label="plan.generated_at")
            acknowledged_at = _parse_utc(
                controlled_decision["acknowledged_at"],
                label="decision.acknowledged_at",
            )
            expires_at = _parse_utc(controlled_decision["expires_at"], label="decision.expires_at")
            timing_ok = (
                generated_at <= acknowledged_at <= reference < expires_at
                and expires_at - acknowledged_at <= MAX_OWNER_DECISION_AGE
            )
        except WebsiteSourceRationalisationError:
            timing_ok = False
    checks.append(
        _check(
            "fresh-owner-decision",
            timing_ok,
            "Owner decision must follow the plan and remain active for at most four hours.",
            maximum_hours=MAX_OWNER_DECISION_AGE.total_seconds() / 3600,
        )
    )

    current_error = ""
    try:
        _revalidate_plan_current(root, plan)
        current_ok = True
    except WebsiteSourceRationalisationError as exc:
        current_ok = False
        current_error = str(exc)
    checks.append(
        _check(
            "current-plan-inputs",
            current_ok,
            "Canonical source, fixed VerifyOnly tool, command, and motion policy must remain unchanged.",
            error=current_error,
        )
    )
    checks.append(
        _check(
            "non-authoritative-boundary",
            shape_ok and controlled_decision.get("authority") == OWNER_DECISION_AUTHORITY,
            "Decision grants no staging execution, candidate, canonical, package, or deployment authority here.",
        )
    )

    passed = all(check["passed"] is True for check in checks)
    validation: dict[str, Any] = {
        "schema": OWNER_VALIDATION_SCHEMA,
        "validated_at": _utc_iso(now),
        "state": "owner-decision-validated-review-only" if passed else "blocked",
        "passed": passed,
        "release_eligible": False,
        "authority": dict(VALIDATION_AUTHORITY),
        "plan": {
            "path": _relative_to_repo(root, plan_file),
            "file_sha256": plan_file_sha256,
            "run_id": run_id,
            "payload_sha256": plan["payload_sha256"],
        },
        "decision": {
            "path": _relative_to_repo(root, decision_file),
            "file_sha256": _sha256_bytes(decision_raw),
            "acknowledged_by": controlled_decision.get("acknowledged_by") if shape_ok else "",
        },
        "checks": checks,
        "next_gate": (
            "Review-only acknowledgement recorded; a separate implementation and authority gate is required."
            if passed
            else "Repair the exact plan or named-owner decision; no staging is authorised."
        ),
    }
    validation["payload_sha256"] = _json_sha256(validation)
    require_owner_validation(validation)
    return validation


def validate_owner_source_rationalisation_decision(
    plan_path: Path,
    decision_path: Path,
) -> dict[str, Any]:
    """Validate exact canonical evidence now; never create or stage files."""

    return _validate_owner_source_rationalisation_decision(
        plan_path,
        decision_path,
        now=datetime.now(UTC),
    )


def require_owner_validation(value: object) -> dict[str, Any]:
    """Require the exact non-authoritative validation receipt contract."""

    validation = _exact_object(value, _VALIDATION_FIELDS, label="Owner decision validation")
    if validation.get("schema") != OWNER_VALIDATION_SCHEMA:
        raise WebsiteSourceRationalisationError("Owner decision validation schema is invalid.")
    _parse_utc(validation.get("validated_at"), label="validation.validated_at")
    passed = validation.get("passed")
    if type(passed) is not bool:
        raise WebsiteSourceRationalisationError("Owner decision validation passed must be boolean.")
    expected_state = "owner-decision-validated-review-only" if passed else "blocked"
    if (
        validation.get("state") != expected_state
        or validation.get("release_eligible") is not False
        or validation.get("authority") != VALIDATION_AUTHORITY
    ):
        raise WebsiteSourceRationalisationError("Owner decision validation authority changed.")
    plan = _exact_object(
        validation.get("plan"),
        frozenset({"path", "file_sha256", "run_id", "payload_sha256"}),
        label="validation.plan",
    )
    _safe_relative_path(plan.get("path"))
    _safe_run_id(plan.get("run_id"), label="validation.plan.run_id")
    _require_sha256(plan.get("file_sha256"), label="validation.plan.file_sha256")
    _require_sha256(plan.get("payload_sha256"), label="validation.plan.payload_sha256")
    decision = _exact_object(
        validation.get("decision"),
        frozenset({"path", "file_sha256", "acknowledged_by"}),
        label="validation.decision",
    )
    _safe_relative_path(decision.get("path"))
    _require_sha256(decision.get("file_sha256"), label="validation.decision.file_sha256")
    if passed and (not isinstance(decision.get("acknowledged_by"), str) or not decision["acknowledged_by"]):
        raise WebsiteSourceRationalisationError("Passing validation lost its named approver.")
    checks = validation.get("checks")
    if (
        not isinstance(checks, list)
        or [check.get("id") for check in checks if isinstance(check, dict)]
        != list(OWNER_VALIDATION_CHECK_IDS)
        or any(
            not isinstance(check, dict) or set(check) != {"id", "passed", "message", "evidence"}
            for check in checks
        )
        or any(type(check["passed"]) is not bool for check in checks)
        or any(not isinstance(check["message"], str) or not check["message"] for check in checks)
        or any(not isinstance(check["evidence"], dict) for check in checks)
        or passed != all(check["passed"] is True for check in checks)
    ):
        raise WebsiteSourceRationalisationError("Owner decision validation checks are malformed.")
    if not isinstance(validation.get("next_gate"), str) or not validation["next_gate"]:
        raise WebsiteSourceRationalisationError("Owner decision validation next gate is missing.")
    payload = dict(validation)
    payload_hash = payload.pop("payload_sha256")
    _require_sha256(payload_hash, label="validation.payload_sha256")
    if payload_hash != _json_sha256(payload):
        raise WebsiteSourceRationalisationError("Owner decision validation payload hash changed.")
    return validation


def write_owner_validation(
    plan_path: Path,
    decision_path: Path,
    output_path: Path,
) -> Path:
    """Generate, deterministically replay, and immutably persist validation."""

    root = _canonical_repo_root()
    _require_trusted_launcher_attestation(root)
    captured_at = datetime.now(UTC)
    controlled = _validate_owner_source_rationalisation_decision(
        plan_path,
        decision_path,
        now=captured_at,
    )
    run_id = str(controlled["plan"]["run_id"])
    expected = root / VALIDATION_ROOT / f"{run_id}.validation.v1.json"
    output = output_path if output_path.is_absolute() else root / output_path
    output = Path(os.path.abspath(output))
    if output != Path(os.path.abspath(expected)):
        raise WebsiteSourceRationalisationError(
            "Validation output must use source-rationalisations/validations/<run-id>.validation.v1.json."
        )
    _ensure_artifact_parent(root, output.parent, allowed_root=root / VALIDATION_ROOT)
    raw = _json_artifact_bytes(controlled)
    writer = _load_reviewed_secure_writer(root)
    replayed = _validate_owner_source_rationalisation_decision(
        plan_path,
        decision_path,
        now=captured_at,
    )
    if _json_artifact_bytes(replayed) != raw:
        raise WebsiteSourceRationalisationError(
            "Plan or decision changed between validation and immutable write replay."
        )
    try:
        writer.write_new_file(output, raw)
    except OSError as exc:
        raise WebsiteSourceRationalisationError(
            f"Owner validation could not be created immutably: {exc}"
        ) from exc
    if output.read_bytes() != raw:
        raise WebsiteSourceRationalisationError("Immutable validation failed exact byte read-back.")
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aureon-website-source-rationalisation",
        description="Plan a read-only website source projection and validate exact owner evidence.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("plan", help="Create a proposal-only exact source partition.")
    plan.add_argument("--run-id")
    plan.add_argument("--output", type=Path, required=True)

    validate = subparsers.add_parser(
        "validate-decision",
        help="Validate a supplied named-owner decision; never stage or mutate source.",
    )
    validate.add_argument("--plan", type=Path, required=True)
    validate.add_argument("--decision", type=Path, required=True)
    validate.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        root = _canonical_repo_root()
        _require_trusted_launcher_attestation(root)
        args = build_parser().parse_args(list(argv) if argv is not None else None)
        if args.command == "plan":
            plan = create_source_rationalisation_plan(run_id=args.run_id)
            output = write_source_rationalisation_plan(plan, args.output)
            print(
                json.dumps(
                    {
                        "state": plan["state"],
                        "output": _relative_to_repo(root, output),
                        "payload_sha256": plan["payload_sha256"],
                        "staging_authority": "none",
                    },
                    indent=2,
                )
            )
            return 0
        output = write_owner_validation(args.plan, args.decision, args.output)
        validation, _raw = _read_json_file(output, label="Written owner validation")
        require_owner_validation(validation)
        print(
            json.dumps(
                {
                    "state": validation["state"],
                    "passed": validation["passed"],
                    "output": _relative_to_repo(root, output),
                    "staging_executed": False,
                },
                indent=2,
            )
        )
        return 0 if validation["passed"] else 2
    except (OSError, WebsiteSourceRationalisationError) as exc:
        print(
            json.dumps(
                {
                    "state": "blocked",
                    "error": str(exc),
                    "staging_executed": False,
                    "canonical_website_mutation": "none",
                }
            )
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "FIXED_FOOTPRINT_LIMITS",
    "OWNER_DECISION_AUTHORITY",
    "OWNER_DECISION_SCHEMA",
    "OWNER_VALIDATION_SCHEMA",
    "PLAN_AUTHORITY",
    "PLAN_SCHEMA",
    "VALIDATION_AUTHORITY",
    "WebsiteSourceRationalisationError",
    "create_source_rationalisation_plan",
    "require_owner_validation",
    "require_source_rationalisation_plan",
    "validate_owner_source_rationalisation_decision",
    "write_owner_validation",
    "write_source_rationalisation_plan",
]
