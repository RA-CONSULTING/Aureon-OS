"""Compile immutable, non-executing website runtime optimisation proposals.

The compiler consumes three explicitly named and SHA-256-bound JSON inputs:
an exact website source-rationalisation plan, strict measurement evidence, and
the release-blocking browser acceptance contract.  It replays the canonical
``website/`` tree, computes a conceptual runtime manifest, and stops.

It deliberately has no encoder, CSS transformer, reference rewriter, copy,
delete, candidate, staging, packaging, network, credential, publishing, or
deployment entrypoint.  A footprint projection is never proof that a candidate
exists or that any acceptance test passed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import MappingProxyType, ModuleType
from typing import Any, Final

MEASUREMENT_SCHEMA = "aureon.website-runtime-optimisation-measurement-evidence.v1"
PROPOSAL_SCHEMA = "aureon.website-runtime-optimisation-proposal.v1"
SOURCE_PLAN_SCHEMA = "aureon.website-source-rationalisation-plan.v1"
ACCEPTANCE_CONTRACT_SCHEMA = "aureon.browser-acceptance-contract.v1"
PRODUCTION_MEASUREMENT_PROVENANCE_STATE = "blocked-reviewed-measurement-provenance-tool-not-installed"

SOURCE_ROOT = Path("website")
IMPLEMENTATION_PATH = Path("aureon/operator/website_runtime_optimisation.py")
TRUSTED_LAUNCHER_PATH = Path("tools/run-website-runtime-optimisation.py")
SOURCE_PLANNER_PATH = Path("aureon/operator/website_source_rationalisation.py")
SOURCE_PLANNER_LAUNCHER_PATH = Path("tools/run-website-source-rationalisation.py")
RELEASE_BUILDER_PATH = Path("tools/build-homepl-v28-narrow-release.ps1")
MOTION_POLICY_PATH = Path("aureon/operator/design_candidate_motion_policy_compiler.py")
SECURE_WRITER_PATH = Path("aureon/operator/secure_immutable_artifact.py")
ACCEPTANCE_CONTRACT_PATH = Path("data/website_operator/browser_acceptance_contract.v1.json")
SOURCE_PLAN_ROOT = Path("artifacts/website-operator/source-rationalisations/plans")
MEASUREMENT_ROOT = Path("artifacts/website-operator/runtime-optimisations/measurements")
PROPOSAL_ROOT = Path("artifacts/website-operator/runtime-optimisations/proposals")

# Pins are deliberately updated only after source review.  The runtime launcher
# pin is filled after its isolated bootstrap has been reviewed and hashed.
REVIEWED_TRUSTED_LAUNCHER_SHA256 = "593A1703E31328C6A42D150C4D7AAFE8C7102D483D3A6D80134F7C46DC2B748A"
REVIEWED_SOURCE_PLANNER_SHA256 = "D79397371038912C26056A4C8A154671B0269DF54DDBBB2BAD0BE472D070DD09"
REVIEWED_SOURCE_PLANNER_LAUNCHER_SHA256 = "827D4112E6C6042B4931E987237E1E7B6035B5A147373CDE202D9DC95184B009"
REVIEWED_RELEASE_BUILDER_SHA256 = "0C42EA5FEB59DCE1583A7731189BF91223AB0F6B5DD333936BCA7E9F65438204"
REVIEWED_MOTION_POLICY_SHA256 = "2685C98B8D0199A30B09B3983E7F1C48DE65EF64D76E4B9900BE8F503F251A73"
REVIEWED_SECURE_WRITER_SHA256 = "D704D691A4D3221E096A470884E5D1293EA663164BB6740FE5BDD26D32B4DB81"
REVIEWED_ACCEPTANCE_CONTRACT_PAYLOAD_SHA256 = (
    "25C85236E40E954B9FB75B561D7EE645E3B019027D9872E71935F5CE4276E5EC"
)

MAX_INPUT_AGE = timedelta(hours=4)
MAX_CLOCK_SKEW = timedelta(minutes=5)
MAX_FILES = 5_000
MAX_TREE_BYTES = 512 * 1024 * 1024
MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_REVIEWED_SOURCE_BYTES = 4 * 1024 * 1024

FIXED_FOOTPRINT_LIMITS: Final[Mapping[str, int]] = MappingProxyType(
    {
        "max_total_bytes": 4_500_000,
        "max_image_bytes": 2_200_000,
        "max_css_bytes": 350_000,
        "max_single_asset_bytes": 500_000,
    }
)

NO_AUTHORITY: Final[dict[str, object]] = {
    "scope": "read-only runtime optimisation proposal compilation",
    "source_selection_authority": "none",
    "measurement_creation_authority": "none",
    "canonical_website_mutation": "none",
    "physical_source_file_removal": "none",
    "encoding_execution": "none",
    "css_transformation_execution": "none",
    "reference_mutation": "none",
    "candidate_authority": "none",
    "staging_authority": "none",
    "package_authority": "none",
    "release_eligible": False,
    "deployment_authority": "none",
    "credential_access": "none",
    "network_access": "none",
}

MEASUREMENT_AUTHORITY: Final[dict[str, object]] = {
    **NO_AUTHORITY,
    "scope": "strict machine-readable optimisation measurement declaration only",
}

ACCEPTANCE_REQUIREMENT_IDS: Final[tuple[str, ...]] = (
    "owner-source-selection-and-verified-live-backup",
    "exact-source-and-reference-closure-rebuild",
    "derivative-byte-and-dimension-integrity",
    "fixed-runtime-footprint-budget",
    "twenty-route-three-engine-browser-matrix",
    "seven-viewport-responsive-and-zoom-matrix",
    "keyboard-accessibility-and-skip-link-occlusion",
    "no-javascript-content-and-navigation",
    "reduced-motion-static-parity",
    "interactive-data-failure-and-fragment-states",
    "social-crawler-metadata-and-research-freshness",
    "approved-source-bound-visual-regression-and-human-review",
)

_IMAGE_SUFFIXES = frozenset({".apng", ".avif", ".gif", ".ico", ".jpeg", ".jpg", ".png", ".svg", ".webp"})
_SHA256 = re.compile(r"[A-F0-9]{64}\Z")
_SAFE_ID = re.compile(r"[a-z0-9][a-z0-9._-]{2,80}\Z")
_TRANSFORM_ACTIONS = frozenset({"replace-runtime-bytes", "omit-from-runtime-closure"})
_MEASUREMENT_BASES = frozenset(
    {
        "measured-derivative",
        "deterministic-minification-measurement",
        "static-reference-analysis",
        "browser-computed-style-analysis",
    }
)

_MANIFEST_ROW_FIELDS = frozenset({"path", "bytes", "sha256"})
_SOURCE_PLAN_BINDING_FIELDS = frozenset(
    {
        "path",
        "file_sha256",
        "payload_sha256",
        "plan_run_id",
        "source_tree_sha256",
        "retained_tree_sha256",
        "retained_manifest_sha256",
    }
)
_ACCEPTANCE_BINDING_FIELDS = frozenset({"path", "file_sha256", "payload_sha256", "contract_id"})
_MEASUREMENT_BINDING_FIELDS = frozenset({"path", "file_sha256", "payload_sha256", "measurement_run_id"})
_METHODOLOGY_FIELDS = frozenset(
    {
        "id",
        "tool_path",
        "tool_sha256",
        "measurement_mode",
        "ephemeral_workspace_only",
        "source_masters_preserved",
        "network_access",
        "commands_recorded",
    }
)
_TRANSFORMATION_FIELDS = frozenset(
    {
        "id",
        "action",
        "source_path",
        "source_sha256",
        "source_bytes",
        "projected_runtime_path",
        "projected_sha256",
        "projected_bytes",
        "expected_saving_bytes",
        "measurement_basis",
        "source_master_preserved",
        "reference_mutation_required",
        "execution_state",
    }
)
_MEASUREMENT_FIELDS = frozenset(
    {
        "schema",
        "measured_at",
        "run_id",
        "state",
        "source_plan_binding",
        "acceptance_contract_binding",
        "methodology",
        "transformations",
        "authority",
        "payload_sha256",
    }
)
_PROPOSAL_FIELDS = frozenset(
    {
        "schema",
        "generated_at",
        "run_id",
        "state",
        "source_plan_binding",
        "measurement_binding",
        "acceptance_contract_binding",
        "current_runtime",
        "projected_runtime",
        "transformations",
        "acceptance_requirements",
        "execution_binding",
        "eligible_for_next_local_gate",
        "authority",
        "payload_sha256",
    }
)
_FOOTPRINT_FIELDS = frozenset(
    {
        "tree_sha256",
        "manifest_sha256",
        "file_count",
        "total_bytes",
        "image_bytes",
        "css_bytes",
        "largest_single_asset_path",
        "largest_single_asset_bytes",
        "limits",
        "violation_ids",
        "within_fixed_footprint_limits",
    }
)
_PROJECTED_FOOTPRINT_FIELDS = _FOOTPRINT_FIELDS | {"saving_bytes"}
_ACCEPTANCE_REQUIREMENT_FIELDS = frozenset({"id", "required", "status", "passed"})
_TOOL_BINDING_FIELDS = frozenset({"path", "sha256"})
_EXECUTION_BINDING_FIELDS = frozenset(
    {
        "mode",
        "repo_root",
        "implementation",
        "trusted_launcher",
        "source_planner",
        "source_planner_launcher",
        "release_builder",
        "motion_policy",
        "secure_writer",
        "measurement_tool",
        "commands_executed",
        "transformations_executed",
        "production_writable",
    }
)
_FOOTPRINT_VIOLATION_IDS = frozenset(
    {
        "resource-byte-budget-exceeded:total",
        "resource-byte-budget-exceeded:image",
        "resource-byte-budget-exceeded:css",
        "single-asset-budget-exceeded",
    }
)


class WebsiteRuntimeOptimisationError(ValueError):
    """A proposal input or requested operation is unsafe, stale, or malformed."""


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
        raise WebsiteRuntimeOptimisationError("Value is not canonical JSON.") from exc


def _json_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest().upper()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def _utc_iso(value: datetime | None = None) -> str:
    resolved = (value or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    return resolved.isoformat().replace("+00:00", "Z")


def _parse_utc(value: object, *, label: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise WebsiteRuntimeOptimisationError(f"{label} must be an explicit UTC timestamp.")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise WebsiteRuntimeOptimisationError(f"{label} is not a valid UTC timestamp.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise WebsiteRuntimeOptimisationError(f"{label} must resolve to UTC.")
    return parsed.astimezone(UTC)


def _require_fresh(value: object, *, now: datetime, label: str) -> datetime:
    parsed = _parse_utc(value, label=label)
    if parsed > now + MAX_CLOCK_SKEW or now - parsed > MAX_INPUT_AGE:
        raise WebsiteRuntimeOptimisationError(f"{label} is future-dated or older than four hours.")
    return parsed


def _safe_id(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _SAFE_ID.fullmatch(value) is None:
        raise WebsiteRuntimeOptimisationError(f"{label} is not a safe identifier.")
    return value


def _require_sha256(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise WebsiteRuntimeOptimisationError(f"{label} must be uppercase SHA-256.")
    return value


def _safe_relative_path(value: object, *, allow_empty: bool = False) -> str:
    if allow_empty and value == "":
        return ""
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise WebsiteRuntimeOptimisationError("A path is not a safe repository-relative POSIX path.")
    path = Path(value)
    if path.is_absolute() or value.startswith("/") or any(part in {"", ".", ".."} for part in path.parts):
        raise WebsiteRuntimeOptimisationError("A path escapes its repository-relative boundary.")
    return path.as_posix()


def _is_link_or_reparse(path: Path) -> bool:
    details = path.lstat()
    attributes = int(getattr(details, "st_file_attributes", 0) or 0)
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400) or 0x400)
    return stat.S_ISLNK(details.st_mode) or bool(attributes & reparse)


def _same_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        stat.S_IFMT(left.st_mode) == stat.S_IFMT(right.st_mode)
        and int(left.st_dev) == int(right.st_dev)
        and int(left.st_ino) == int(right.st_ino)
    )


def _ordinary_file(path: Path, *, label: str, require_single_link: bool = True) -> Path:
    lexical = Path(os.path.abspath(path))
    for component in (lexical, *lexical.parents):
        if (component.exists() or component.is_symlink()) and _is_link_or_reparse(component):
            raise WebsiteRuntimeOptimisationError(f"{label} may not cross a link or reparse point.")
    if not lexical.is_file():
        raise WebsiteRuntimeOptimisationError(f"{label} must be an ordinary file.")
    if require_single_link and int(lexical.stat().st_nlink) != 1:
        raise WebsiteRuntimeOptimisationError(f"{label} must have exactly one hard link.")
    return lexical


def _ordinary_directory(path: Path, *, label: str) -> Path:
    lexical = Path(os.path.abspath(path))
    for component in (lexical, *lexical.parents):
        if (component.exists() or component.is_symlink()) and _is_link_or_reparse(component):
            raise WebsiteRuntimeOptimisationError(f"{label} may not cross a link or reparse point.")
    if not lexical.is_dir():
        raise WebsiteRuntimeOptimisationError(f"{label} must be an ordinary directory.")
    return lexical


def _canonical_repo_root() -> Path:
    implementation = Path(os.path.abspath(__file__))
    if implementation.name != IMPLEMENTATION_PATH.name:
        raise WebsiteRuntimeOptimisationError("Runtime optimisation implementation path is unexpected.")
    return implementation.parents[2]


def _read_exact_file(
    path: Path,
    expected_sha256: str,
    *,
    label: str,
    max_bytes: int = MAX_JSON_BYTES,
) -> tuple[bytes, os.stat_result]:
    expected = _require_sha256(expected_sha256, label=f"{label} expected SHA-256")
    source = _ordinary_file(path, label=label)
    before = source.lstat()
    if int(before.st_size) > max_bytes:
        raise WebsiteRuntimeOptimisationError(f"{label} exceeds its byte bound.")
    with source.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if not _same_identity(before, opened):
            raise WebsiteRuntimeOptimisationError(f"{label} changed before its handle opened.")
        payload = stream.read(max_bytes + 1)
    after = source.lstat()
    if (
        len(payload) > max_bytes
        or int(after.st_size) != len(payload)
        or not _same_identity(opened, after)
        or _sha256_bytes(payload) != expected
    ):
        raise WebsiteRuntimeOptimisationError(f"{label} bytes do not match the exact supplied pin.")
    return payload, after


def _strict_json(raw: bytes, *, label: str) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise WebsiteRuntimeOptimisationError(f"{label} must be UTF-8 JSON.") from exc

    def reject_duplicate(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise WebsiteRuntimeOptimisationError(f"{label} contains duplicate JSON keys.")
            result[key] = value
        return result

    try:
        value = json.loads(
            text,
            object_pairs_hook=reject_duplicate,
            parse_constant=lambda token: (_ for _ in ()).throw(
                WebsiteRuntimeOptimisationError(f"{label} contains non-finite {token}.")
            ),
        )
    except (json.JSONDecodeError, RecursionError) as exc:
        raise WebsiteRuntimeOptimisationError(f"{label} is not strict JSON.") from exc
    if not isinstance(value, dict):
        raise WebsiteRuntimeOptimisationError(f"{label} must be one JSON object.")
    return value


def _exact_object(value: object, fields: frozenset[str], *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise WebsiteRuntimeOptimisationError(f"{label} must contain exactly {sorted(fields)}.")
    return value


def _payload_hash(value: Mapping[str, Any], *, field: str = "payload_sha256") -> str:
    payload = dict(value)
    observed = _require_sha256(payload.pop(field, None), label=field)
    if _json_sha256(payload) != observed:
        raise WebsiteRuntimeOptimisationError(f"{field} does not authenticate the exact JSON payload.")
    return observed


def _manifest_rows(value: object, *, label: str) -> list[dict[str, object]]:
    if not isinstance(value, list) or len(value) > MAX_FILES:
        raise WebsiteRuntimeOptimisationError(f"{label} must be a bounded manifest list.")
    rows: list[dict[str, object]] = []
    paths: set[str] = set()
    total = 0
    for index, raw in enumerate(value):
        row = _exact_object(raw, _MANIFEST_ROW_FIELDS, label=f"{label}[{index}]")
        path = _safe_relative_path(row["path"])
        sha256 = _require_sha256(row["sha256"], label=f"{label}[{index}].sha256")
        size = row["bytes"]
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise WebsiteRuntimeOptimisationError(f"{label}[{index}].bytes must be non-negative.")
        if path in paths:
            raise WebsiteRuntimeOptimisationError(f"{label} contains a duplicate path.")
        paths.add(path)
        total += size
        if total > MAX_TREE_BYTES:
            raise WebsiteRuntimeOptimisationError(f"{label} exceeds the tree byte bound.")
        rows.append({"path": path, "bytes": size, "sha256": sha256})
    if rows != sorted(rows, key=lambda item: str(item["path"])):
        raise WebsiteRuntimeOptimisationError(f"{label} must use case-sensitive path order.")
    return rows


def _summary(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    normalised = [dict(row) for row in sorted(rows, key=lambda item: str(item["path"]))]
    total = sum(_row_bytes(row) for row in normalised)
    digest = _json_sha256(normalised)
    return {
        "tree_sha256": digest,
        "manifest_sha256": digest,
        "file_count": len(normalised),
        "total_bytes": total,
        "files": normalised,
    }


def _manifest(root: Path) -> list[dict[str, object]]:
    site = _ordinary_directory(root, label="Canonical website source")
    rows: list[dict[str, object]] = []
    total = 0
    for path in sorted(site.rglob("*"), key=lambda item: item.relative_to(site).as_posix()):
        if _is_link_or_reparse(path):
            raise WebsiteRuntimeOptimisationError(
                "Canonical website source contains a link or reparse point."
            )
        if path.is_dir():
            continue
        if not path.is_file() or int(path.stat().st_nlink) != 1:
            raise WebsiteRuntimeOptimisationError("Canonical website source contains a non-ordinary file.")
        relative = path.relative_to(site).as_posix()
        size = int(path.stat().st_size)
        total += size
        if len(rows) >= MAX_FILES or total > MAX_TREE_BYTES:
            raise WebsiteRuntimeOptimisationError("Canonical website source exceeds its manifest bounds.")
        payload, _ = _read_exact_file(
            path,
            hashlib.sha256(path.read_bytes()).hexdigest().upper(),
            label=f"Canonical source {relative}",
            max_bytes=max(size, 1),
        )
        rows.append({"path": relative, "bytes": len(payload), "sha256": _sha256_bytes(payload)})
    return rows


def _require_source_plan(value: object, *, now: datetime) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise WebsiteRuntimeOptimisationError("Source plan must be a JSON object.")
    if value.get("schema") != SOURCE_PLAN_SCHEMA or value.get("state") != "proposal-only":
        raise WebsiteRuntimeOptimisationError("Source plan is not the proposal-only v1 contract.")
    _payload_hash(value)
    _safe_id(value.get("run_id"), label="source plan run_id")
    _require_fresh(value.get("generated_at"), now=now, label="source plan generated_at")
    authority = value.get("authority")
    if not isinstance(authority, Mapping) or (
        authority.get("canonical_website_mutation") != "none"
        or authority.get("physical_source_file_removal") != "none"
        or authority.get("staging_authority") != "none"
        or authority.get("candidate_authority") != "none"
        or authority.get("package_authority") != "none"
        or authority.get("release_eligible") is not False
        or authority.get("deployment_authority") != "none"
        or authority.get("credential_access") != "none"
        or authority.get("network_access") != "none"
    ):
        raise WebsiteRuntimeOptimisationError("Source plan authority is not fail closed.")
    source = value.get("source_binding")
    retained = value.get("retained_projection")
    omitted = value.get("omitted_projection")
    if not all(isinstance(item, dict) for item in (source, retained, omitted)):
        raise WebsiteRuntimeOptimisationError("Source plan projections are missing.")
    assert isinstance(source, dict)
    assert isinstance(retained, dict)
    assert isinstance(omitted, dict)
    source_rows = _manifest_rows(source.get("files"), label="source plan source files")
    retained_rows = _manifest_rows(retained.get("files"), label="source plan retained files")
    raw_omitted = omitted.get("files")
    if not isinstance(raw_omitted, list):
        raise WebsiteRuntimeOptimisationError("Source plan omitted files must be a list.")
    omitted_rows: list[dict[str, object]] = []
    for index, raw in enumerate(raw_omitted):
        if not isinstance(raw, dict) or set(raw) != {"path", "bytes", "sha256", "reason"}:
            raise WebsiteRuntimeOptimisationError(f"Source plan omitted files[{index}] is malformed.")
        if raw.get("reason") != "not-in-public-runtime-closure":
            raise WebsiteRuntimeOptimisationError("Source plan omission reason is not closed-world.")
        omitted_rows.extend(
            _manifest_rows(
                [{key: raw[key] for key in ("path", "bytes", "sha256")}],
                label=f"source plan omitted file {index}",
            )
        )
    partition = sorted([*retained_rows, *omitted_rows], key=lambda item: str(item["path"]))
    if partition != source_rows:
        raise WebsiteRuntimeOptimisationError("Retained and omitted projections do not partition the source.")
    for label, projection, rows in (
        ("source", source, source_rows),
        ("retained", retained, retained_rows),
    ):
        expected = _summary(rows)
        for field in ("tree_sha256", "manifest_sha256", "file_count", "total_bytes"):
            if projection.get(field) != expected[field]:
                raise WebsiteRuntimeOptimisationError(f"Source plan {label} {field} is inconsistent.")
    if source.get("root") != SOURCE_ROOT.as_posix():
        raise WebsiteRuntimeOptimisationError("Source plan does not bind canonical website/.")
    closure = value.get("closure_binding")
    budget = value.get("motion_budget_projection")
    execution = value.get("execution_binding")
    if not all(isinstance(item, Mapping) for item in (closure, budget, execution)):
        raise WebsiteRuntimeOptimisationError("Source plan tool bindings are missing.")
    assert isinstance(closure, Mapping)
    assert isinstance(budget, Mapping)
    assert isinstance(execution, Mapping)
    if (
        closure.get("verify_only") is not True
        or closure.get("state") != "verified-complete"
        or closure.get("tool_sha256") != REVIEWED_RELEASE_BUILDER_SHA256
        or budget.get("policy_sha256") != REVIEWED_MOTION_POLICY_SHA256
        or execution.get("implementation_sha256") != REVIEWED_SOURCE_PLANNER_SHA256
        or execution.get("reviewed_trusted_launcher_sha256") != REVIEWED_SOURCE_PLANNER_LAUNCHER_SHA256
        or execution.get("reviewed_secure_writer_sha256") != REVIEWED_SECURE_WRITER_SHA256
        or execution.get("launcher_attested") is not True
    ):
        raise WebsiteRuntimeOptimisationError("Source plan is not bound to the reviewed planning closure.")
    return value


def _require_acceptance_contract(
    value: object,
    *,
    retained: Mapping[str, Any],
    reviewed_payload_required: bool = True,
) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != ACCEPTANCE_CONTRACT_SCHEMA:
        raise WebsiteRuntimeOptimisationError("Browser acceptance contract schema is invalid.")
    if set(value) != {
        "schema",
        "contractId",
        "mode",
        "origin",
        "authority",
        "sourceBinding",
        "routes",
        "browserMatrix",
        "releaseResultMaxima",
        "evidenceRequirements",
        "globalAssertions",
        "interactionAssertions",
        "derivativeIntegrityAssertions",
        "visualRegression",
        "progressiveEnhancementAssertions",
        "socialCrawlerAssertions",
        "researchAndArtworkBaselines",
        "footprintLimitsBytes",
        "perRoutePerformanceLimits",
        "knownReleaseBlockers",
        "payloadSha256",
    }:
        raise WebsiteRuntimeOptimisationError("Browser acceptance contract topology is not exact.")
    payload_field = "payloadSha256"
    payload = dict(value)
    observed = _require_sha256(payload.pop(payload_field, None), label=payload_field)
    if _json_sha256(payload) != observed:
        raise WebsiteRuntimeOptimisationError("Browser acceptance contract payload hash is invalid.")
    if reviewed_payload_required and observed != REVIEWED_ACCEPTANCE_CONTRACT_PAYLOAD_SHA256:
        raise WebsiteRuntimeOptimisationError(
            "Browser acceptance contract payload is not the reviewed immutable policy."
        )
    if (
        value.get("contractId") != "AUREON-WEB-V29-OPTIMISATION-ACCEPTANCE"
        or value.get("mode") != "release-blocking"
        or value.get("origin") != "https://aureonzorzatechnologies.pl"
    ):
        raise WebsiteRuntimeOptimisationError("Browser acceptance contract must be release-blocking.")
    authority = value.get("authority")
    if authority != {
        "scope": "read-only browser acceptance criteria",
        "candidateAuthority": "none",
        "canonicalWebsiteMutation": "none",
        "packageAuthority": "none",
        "releaseAuthority": "none",
        "releaseEligible": False,
        "deploymentAuthority": "none",
        "networkAccess": "none",
        "credentialAccess": "none",
    }:
        raise WebsiteRuntimeOptimisationError("Browser acceptance contract grants authority.")
    binding = value.get("sourceBinding")
    if not isinstance(binding, Mapping) or (
        binding.get("retainedManifestSha256") != retained.get("manifest_sha256")
        or binding.get("retainedFileCount") != retained.get("file_count")
        or binding.get("retainedTotalBytes") != retained.get("total_bytes")
        or binding.get("htmlDocumentCount") != 20
        or binding.get("indexableDocumentCount") != 17
        or binding.get("noindexDocumentCount") != 3
    ):
        raise WebsiteRuntimeOptimisationError("Browser acceptance contract source binding is stale.")
    verdict = value.get("releaseResultMaxima")
    evidence = value.get("evidenceRequirements")
    if (
        not isinstance(verdict, Mapping)
        or not isinstance(evidence, Mapping)
        or (
            verdict.get("failures") != 0
            or verdict.get("errors") != 0
            or verdict.get("warnings") != 0
            or verdict.get("firstPartyRequestFailures") != 0
            or evidence.get("manualVisualReviewRequired") is not True
            or evidence.get("browserReportRequired") is not True
            or evidence.get("screenshotManifestRequired") is not True
            or evidence.get("browserReportMustBindContractPayloadSha256") is not True
            or evidence.get("screenshotManifestMustBindSourceManifestSha256") is not True
            or evidence.get("derivativeManifestRequired") is not True
            or evidence.get("derivativeManifestMustBindMeasurementPayloadSha256") is not True
        )
    ):
        raise WebsiteRuntimeOptimisationError("Browser acceptance verdict is not fail closed.")
    routes = value.get("routes")
    matrix = value.get("browserMatrix")
    engines = matrix.get("engines") if isinstance(matrix, Mapping) else None
    viewports = matrix.get("viewports") if isinstance(matrix, Mapping) else None
    zoom = matrix.get("zoomProfile") if isinstance(matrix, Mapping) else None
    if not isinstance(routes, list) or len(routes) != 20:
        raise WebsiteRuntimeOptimisationError("Browser acceptance contract must cover 20 routes.")
    expected_routes = {
        ("/", "index.html", "indexable"),
        ("/404.html", "404.html", "noindex"),
        ("/about/", "about/index.html", "indexable"),
        ("/accessibility.html", "accessibility.html", "indexable"),
        ("/community/", "community/index.html", "indexable"),
        ("/contact/", "contact/index.html", "indexable"),
        ("/diligence/", "diligence/index.html", "indexable"),
        ("/downloads/", "downloads/index.html", "noindex"),
        (
            "/downloads/validation-metrics-ledger/",
            "downloads/validation-metrics-ledger/index.html",
            "noindex",
        ),
        ("/funding/", "funding/index.html", "indexable"),
        ("/funding/investor-deck/", "funding/investor-deck/index.html", "indexable"),
        ("/live/", "live/index.html", "indexable"),
        ("/privacy.html", "privacy.html", "indexable"),
        (
            "/projects/aureon-trading-system/",
            "projects/aureon-trading-system/index.html",
            "indexable",
        ),
        ("/projects/", "projects/index.html", "indexable"),
        ("/publications/", "publications/index.html", "indexable"),
        ("/research/", "research/index.html", "indexable"),
        ("/research/journal/", "research/journal/index.html", "indexable"),
        ("/updates/", "updates/index.html", "indexable"),
        ("/vision/", "vision/index.html", "indexable"),
    }
    observed_routes = {
        (row.get("route"), row.get("documentPath"), row.get("indexing"))
        for row in routes
        if isinstance(row, Mapping)
    }
    if observed_routes != expected_routes:
        raise WebsiteRuntimeOptimisationError("Browser acceptance route matrix is incomplete or altered.")
    if set(engines or []) != {
        "chromium",
        "firefox",
        "webkit",
    }:
        raise WebsiteRuntimeOptimisationError("Browser acceptance contract must cover three engines.")
    if not isinstance(viewports, list) or {
        (item.get("width"), item.get("height")) for item in viewports if isinstance(item, Mapping)
    } != {
        (320, 800),
        (360, 800),
        (390, 844),
        (768, 1024),
        (1280, 800),
        (1440, 1000),
        (1920, 1080),
    }:
        raise WebsiteRuntimeOptimisationError("Browser acceptance contract must cover seven viewports.")
    if not isinstance(zoom, Mapping) or dict(zoom) != {
        "routes": "all",
        "engine": "chromium",
        "viewport": {"width": 1280, "height": 800},
        "percent": [100, 200, 400],
        "horizontalOverflowPixels": 0,
        "contentLossAllowed": False,
    }:
        raise WebsiteRuntimeOptimisationError("Browser acceptance zoom coverage is incomplete.")
    static = value.get("footprintLimitsBytes")
    expected_limits = {
        "maximumTotal": FIXED_FOOTPRINT_LIMITS["max_total_bytes"],
        "maximumImages": FIXED_FOOTPRINT_LIMITS["max_image_bytes"],
        "maximumCss": FIXED_FOOTPRINT_LIMITS["max_css_bytes"],
        "maximumSingleAsset": FIXED_FOOTPRINT_LIMITS["max_single_asset_bytes"],
    }
    if static != expected_limits:
        raise WebsiteRuntimeOptimisationError("Browser contract footprint limits are not fixed policy.")
    for required in (
        "globalAssertions",
        "interactionAssertions",
        "derivativeIntegrityAssertions",
        "visualRegression",
        "progressiveEnhancementAssertions",
        "socialCrawlerAssertions",
        "researchAndArtworkBaselines",
        "perRoutePerformanceLimits",
        "knownReleaseBlockers",
    ):
        if required not in value:
            raise WebsiteRuntimeOptimisationError(f"Browser acceptance contract lacks {required}.")
    global_assertions = value["globalAssertions"]
    interactions = value["interactionAssertions"]
    derivative_integrity = value["derivativeIntegrityAssertions"]
    visual = value["visualRegression"]
    progressive = value["progressiveEnhancementAssertions"]
    social = value["socialCrawlerAssertions"]
    research = value["researchAndArtworkBaselines"]
    performance = value["perRoutePerformanceLimits"]
    blockers = value["knownReleaseBlockers"]
    if not all(
        isinstance(item, Mapping)
        for item in (
            global_assertions,
            interactions,
            derivative_integrity,
            visual,
            progressive,
            social,
            research,
            performance,
        )
    ) or not isinstance(blockers, list):
        raise WebsiteRuntimeOptimisationError("Browser acceptance assertions are malformed.")
    dom = global_assertions.get("dom")
    accessibility = global_assertions.get("accessibility")
    mobile = interactions.get("mobileNavigation")
    fragments = interactions.get("fragmentNavigation")
    skip = interactions.get("skipLinkStacking")
    interactive_states = interactions.get("interactiveStates")
    data_failure_states = interactions.get("dataFailureStates")
    no_js = progressive.get("noJavaScript")
    reduced = progressive.get("reducedMotion")
    if not all(
        isinstance(item, Mapping)
        for item in (
            dom,
            accessibility,
            mobile,
            fragments,
            skip,
            interactive_states,
            data_failure_states,
            no_js,
            reduced,
        )
    ):
        raise WebsiteRuntimeOptimisationError("Browser acceptance subcontracts are malformed.")
    assert isinstance(dom, Mapping)
    assert isinstance(accessibility, Mapping)
    assert isinstance(mobile, Mapping)
    assert isinstance(fragments, Mapping)
    assert isinstance(skip, Mapping)
    assert isinstance(interactive_states, Mapping)
    assert isinstance(data_failure_states, Mapping)
    assert isinstance(no_js, Mapping)
    assert isinstance(reduced, Mapping)
    if any(
        dom.get(key) != expected
        for key, expected in {
            "expectedHttpStatus": 200,
            "unexpectedRedirects": 0,
            "loginWalls": 0,
            "titleElements": 1,
            "mainLandmarks": 1,
            "h1Elements": 1,
            "duplicateIds": 0,
            "imagesWithoutAltAttribute": 0,
            "brokenFirstPartyLinks": 0,
            "missingInternalFragmentTargets": 0,
            "horizontalOverflowPixels": 0,
        }.items()
    ) or any(
        accessibility.get(key) != expected
        for key, expected in {
            "axeCriticalViolations": 0,
            "axeSeriousViolations": 0,
            "unnamedInteractiveControls": 0,
            "keyboardTraps": 0,
            "visibleFocusRequired": True,
            "skipLinkRequired": True,
            "skipLinkTargetRequired": True,
        }.items()
    ):
        raise WebsiteRuntimeOptimisationError("Global DOM or accessibility maxima were weakened.")
    if (
        mobile.get("toggleRequired") is not True
        or mobile.get("ariaExpandedMustTrackState") is not True
        or mobile.get("escapeClosesMenu") is not True
        or mobile.get("keyboardOperable") is not True
        or fragments.get("missingTargetMaximum") != 0
        or set(fragments.get("requiredDestinations") or [])
        != {
            "/projects/#core",
            "/projects/#blades",
        }
        or skip.get("focusedSkipLinkMustBeVisible") is not True
        or skip.get("minimumZIndexDeltaAboveStickyHeader") != 1
        or interactive_states.get("scope") != "all-interactive-controls"
        or interactive_states.get("requiredStates")
        != ["default", "keyboard-focus", "activated", "disabled-when-applicable"]
        or interactive_states.get("consoleErrors") != 0
        or interactive_states.get("uncaughtExceptions") != 0
        or data_failure_states.get("scope") != "all-data-dependent-surfaces"
        or data_failure_states.get("requiredStates") != ["loading", "success", "empty", "error"]
        or data_failure_states.get("fallbackVisibleOnError") is not True
        or data_failure_states.get("primaryNavigationUsableOnError") is not True
        or data_failure_states.get("uncaughtExceptions") != 0
    ):
        raise WebsiteRuntimeOptimisationError("Navigation or skip-link acceptance was weakened.")
    if dict(derivative_integrity) != {
        "manifestRequired": True,
        "sourceAndProjectedSha256Required": True,
        "sourceAndProjectedByteCountsRequired": True,
        "sourceAndProjectedDimensionsRequired": True,
        "decodedProjectedDimensionsRequired": True,
        "allowedDimensionChange": "explicitly-declared-no-unapproved-crop",
        "zeroByteDerivativesMaximum": 0,
    }:
        raise WebsiteRuntimeOptimisationError("Derivative integrity acceptance is incomplete.")
    desktop_visual = visual.get("desktop")
    mobile_visual = visual.get("mobileAndTablet")
    if (
        not isinstance(desktop_visual, Mapping)
        or not isinstance(mobile_visual, Mapping)
        or (
            desktop_visual.get("maximumPixelDifferenceRatio") != 0.005
            or desktop_visual.get("minimumSsim") != 0.99
            or mobile_visual.get("maximumPixelDifferenceRatio") != 0.01
            or mobile_visual.get("minimumSsim") != 0.985
            or visual.get("baselineMismatchIsReleaseBlocking") is not True
            or visual.get("manualReviewDoesNotWaiveThresholds") is not True
        )
    ):
        raise WebsiteRuntimeOptimisationError("Visual-regression acceptance was weakened.")
    if (
        no_js.get("everyRouteRequired") is not True
        or no_js.get("primaryContentVisible") is not True
        or no_js.get("primaryNavigationUsable") is not True
        or reduced.get("everyRouteRequired") is not True
        or reduced.get("materialContentEquivalent") is not True
        or reduced.get("autoplayingMotionAllowed") is not False
        or reduced.get("interactionUsable") is not True
    ):
        raise WebsiteRuntimeOptimisationError("Progressive-enhancement acceptance was weakened.")
    floors = research.get("providerRecordFloors")
    if (
        social.get("scope") != "all-17-indexable-routes"
        or social.get("crawlerRequestFailures") != 0
        or social.get("absoluteHttpsUrlsRequired") is not True
        or research.get("researchNoteMinimumCount") != 34
        or research.get("artworkEntryMinimumCount") != 6
        or research.get("artworkFileMinimumCount") != 12
        or floors != {"orcid": 74, "zenodo": 73}
        or research.get("providerSnapshotMaxAgeHours") != 24
        or research.get("providerSnapshotPayloadSha256Required") is not True
        or research.get("publicProviderReadbackRequired") is not True
        or research.get("websiteSelectedDoiSetMustEqualOrcid") is not True
        or research.get("selectedDoiCountMinimum") != 12
        or research.get("regressionAllowed") is not False
    ):
        raise WebsiteRuntimeOptimisationError("Crawler, research, or artwork acceptance was weakened.")
    if performance != {
        "maximumTtfbMs": 800,
        "maximumDomContentLoadedMs": 2500,
        "maximumLoadMs": 3500,
        "maximumLcpMs": 2500,
        "maximumCls": 0.1,
        "maximumRequestCount": 80,
        "maximumTransferBytes": 3_000_000,
        "maximumTotalLongTaskDurationMs": 300,
    }:
        raise WebsiteRuntimeOptimisationError("Per-route performance acceptance was weakened.")
    if {row.get("id") for row in blockers if isinstance(row, Mapping)} != {
        "projects-core-fragment-missing-live",
        "projects-blades-fragment-missing-live",
        "skip-link-obscured-by-header",
        "projects-current-source-hash-stale-live",
    }:
        raise WebsiteRuntimeOptimisationError("Known live release blockers are incomplete.")
    return value


def _require_transformation_rows(value: object) -> list[dict[str, Any]]:
    """Structurally validate exact non-executing transformation declarations."""

    rows = value
    if not isinstance(rows, list) or not rows or len(rows) > MAX_FILES:
        raise WebsiteRuntimeOptimisationError("Measurement transformations must be a bounded non-empty list.")
    validated: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    source_paths: set[str] = set()
    for index, raw in enumerate(rows):
        row = _exact_object(raw, _TRANSFORMATION_FIELDS, label=f"Transformation[{index}]")
        identifier = _safe_id(row["id"], label=f"Transformation[{index}].id")
        source_path = _safe_relative_path(row["source_path"])
        source_sha = _require_sha256(row["source_sha256"], label=f"Transformation[{index}].source_sha256")
        del source_sha
        source_bytes = row["source_bytes"]
        projected_bytes = row["projected_bytes"]
        savings = row["expected_saving_bytes"]
        if (
            identifier in identifiers
            or source_path in source_paths
            or isinstance(source_bytes, bool)
            or not isinstance(source_bytes, int)
            or source_bytes <= 0
            or source_bytes > MAX_TREE_BYTES
            or isinstance(projected_bytes, bool)
            or not isinstance(projected_bytes, int)
            or projected_bytes < 0
            or projected_bytes > MAX_TREE_BYTES
            or projected_bytes >= source_bytes
            or isinstance(savings, bool)
            or not isinstance(savings, int)
            or savings <= 0
            or savings > MAX_TREE_BYTES
            or savings != source_bytes - projected_bytes
        ):
            raise WebsiteRuntimeOptimisationError(
                "Transformation identifiers, paths, or byte arithmetic are invalid."
            )
        identifiers.add(identifier)
        source_paths.add(source_path)
        if (
            row["action"] not in _TRANSFORM_ACTIONS
            or row["measurement_basis"] not in _MEASUREMENT_BASES
            or row["source_master_preserved"] is not True
            or not isinstance(row["reference_mutation_required"], bool)
            or row["execution_state"] != "not-executed"
        ):
            raise WebsiteRuntimeOptimisationError("Transformation authority or evidence basis is invalid.")
        projected_path = _safe_relative_path(row["projected_runtime_path"], allow_empty=True)
        projected_sha = row["projected_sha256"]
        if row["action"] == "omit-from-runtime-closure":
            if projected_path or projected_sha != "" or projected_bytes != 0:
                raise WebsiteRuntimeOptimisationError(
                    "Closure omission may not declare runtime output bytes."
                )
        else:
            if not projected_path or projected_bytes <= 0:
                raise WebsiteRuntimeOptimisationError(
                    "Runtime replacement requires exact projected output evidence."
                )
            _require_sha256(
                projected_sha,
                label=f"Transformation[{index}].projected_sha256",
            )
        validated.append(row)
    return validated


def _require_source_plan_binding(value: object, *, label: str) -> dict[str, Any]:
    binding = _exact_object(value, _SOURCE_PLAN_BINDING_FIELDS, label=label)
    _safe_relative_path(binding["path"])
    for field in (
        "file_sha256",
        "payload_sha256",
        "source_tree_sha256",
        "retained_tree_sha256",
        "retained_manifest_sha256",
    ):
        _require_sha256(binding[field], label=f"{label}.{field}")
    _safe_id(binding["plan_run_id"], label=f"{label}.plan_run_id")
    return binding


def _require_acceptance_binding(value: object, *, label: str) -> dict[str, Any]:
    binding = _exact_object(value, _ACCEPTANCE_BINDING_FIELDS, label=label)
    _safe_relative_path(binding["path"])
    _require_sha256(binding["file_sha256"], label=f"{label}.file_sha256")
    _require_sha256(binding["payload_sha256"], label=f"{label}.payload_sha256")
    if not isinstance(binding["contract_id"], str) or not binding["contract_id"]:
        raise WebsiteRuntimeOptimisationError(f"{label}.contract_id is missing.")
    return binding


def require_measurement_evidence(value: object) -> dict[str, Any]:
    """Structurally validate a measurement declaration without proving provenance."""

    evidence = _exact_object(value, _MEASUREMENT_FIELDS, label="Measurement evidence")
    if evidence.get("schema") != MEASUREMENT_SCHEMA or evidence.get("state") != "measurement-only":
        raise WebsiteRuntimeOptimisationError("Measurement evidence schema or state is invalid.")
    _payload_hash(evidence)
    _safe_id(evidence.get("run_id"), label="measurement run_id")
    _parse_utc(evidence.get("measured_at"), label="measurement measured_at")
    _require_source_plan_binding(evidence.get("source_plan_binding"), label="Measurement source-plan binding")
    _require_acceptance_binding(
        evidence.get("acceptance_contract_binding"),
        label="Measurement acceptance-contract binding",
    )
    methodology = _exact_object(
        evidence.get("methodology"),
        _METHODOLOGY_FIELDS,
        label="Measurement methodology",
    )
    _safe_id(methodology["id"], label="methodology.id")
    _safe_relative_path(methodology["tool_path"])
    _require_sha256(methodology["tool_sha256"], label="methodology.tool_sha256")
    if (
        methodology["measurement_mode"] != "read-only-source-ephemeral-derivatives"
        or methodology["ephemeral_workspace_only"] is not True
        or methodology["source_masters_preserved"] is not True
        or methodology["network_access"] != "none"
        or methodology["commands_recorded"] is not False
    ):
        raise WebsiteRuntimeOptimisationError("Measurement methodology is not non-operational.")
    _require_transformation_rows(evidence.get("transformations"))
    if evidence.get("authority") != MEASUREMENT_AUTHORITY:
        raise WebsiteRuntimeOptimisationError("Measurement evidence authority is not exact and fail closed.")
    return evidence


def _row_bytes(row: Mapping[str, object]) -> int:
    value = row.get("bytes")
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise WebsiteRuntimeOptimisationError("Manifest row bytes are invalid.")
    return value


def _footprint(rows: Sequence[Mapping[str, object]]) -> dict[str, Any]:
    total = sum(_row_bytes(row) for row in rows)
    image = sum(_row_bytes(row) for row in rows if Path(str(row["path"])).suffix.lower() in _IMAGE_SUFFIXES)
    css = sum(_row_bytes(row) for row in rows if Path(str(row["path"])).suffix.lower() == ".css")
    largest = max(rows, key=_row_bytes, default={"path": "", "bytes": 0})
    violations: list[str] = []
    if total > FIXED_FOOTPRINT_LIMITS["max_total_bytes"]:
        violations.append("resource-byte-budget-exceeded:total")
    if image > FIXED_FOOTPRINT_LIMITS["max_image_bytes"]:
        violations.append("resource-byte-budget-exceeded:image")
    if css > FIXED_FOOTPRINT_LIMITS["max_css_bytes"]:
        violations.append("resource-byte-budget-exceeded:css")
    if _row_bytes(largest) > FIXED_FOOTPRINT_LIMITS["max_single_asset_bytes"]:
        violations.append("single-asset-budget-exceeded")
    return {
        "tree_sha256": _json_sha256([dict(row) for row in rows]),
        "manifest_sha256": _json_sha256([dict(row) for row in rows]),
        "file_count": len(rows),
        "total_bytes": total,
        "image_bytes": image,
        "css_bytes": css,
        "largest_single_asset_path": str(largest["path"]),
        "largest_single_asset_bytes": _row_bytes(largest),
        "limits": dict(FIXED_FOOTPRINT_LIMITS),
        "violation_ids": violations,
        "within_fixed_footprint_limits": not violations,
    }


def _require_footprint(value: object, *, label: str, projected: bool) -> dict[str, Any]:
    """Validate one non-empty footprint and its fixed-budget arithmetic."""

    expected_fields = _PROJECTED_FOOTPRINT_FIELDS if projected else _FOOTPRINT_FIELDS
    footprint = _exact_object(value, expected_fields, label=label)
    tree_sha256 = _require_sha256(footprint["tree_sha256"], label=f"{label}.tree_sha256")
    manifest_sha256 = _require_sha256(footprint["manifest_sha256"], label=f"{label}.manifest_sha256")
    if tree_sha256 != manifest_sha256:
        raise WebsiteRuntimeOptimisationError(f"{label} tree and manifest hashes diverge.")

    integer_fields = (
        "file_count",
        "total_bytes",
        "image_bytes",
        "css_bytes",
        "largest_single_asset_bytes",
    )
    integers: dict[str, int] = {}
    for field in integer_fields:
        raw = footprint[field]
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise WebsiteRuntimeOptimisationError(f"{label}.{field} must be an integer.")
        integers[field] = raw
    if not 1 <= integers["file_count"] <= MAX_FILES or not 1 <= integers["total_bytes"] <= MAX_TREE_BYTES:
        raise WebsiteRuntimeOptimisationError(f"{label} must describe a bounded non-empty runtime.")
    if not (
        0 <= integers["image_bytes"] <= integers["total_bytes"]
        and 0 <= integers["css_bytes"] <= integers["total_bytes"]
        and 0 <= integers["largest_single_asset_bytes"] <= integers["total_bytes"]
    ):
        raise WebsiteRuntimeOptimisationError(f"{label} byte totals are inconsistent.")
    _safe_relative_path(footprint["largest_single_asset_path"])
    if footprint["limits"] != FIXED_FOOTPRINT_LIMITS:
        raise WebsiteRuntimeOptimisationError(f"{label} weakens the fixed footprint limits.")

    violation_ids = footprint["violation_ids"]
    if (
        not isinstance(violation_ids, list)
        or len(violation_ids) != len(set(violation_ids))
        or any(identifier not in _FOOTPRINT_VIOLATION_IDS for identifier in violation_ids)
    ):
        raise WebsiteRuntimeOptimisationError(f"{label} violation ids are invalid.")
    expected_violations: list[str] = []
    if integers["total_bytes"] > FIXED_FOOTPRINT_LIMITS["max_total_bytes"]:
        expected_violations.append("resource-byte-budget-exceeded:total")
    if integers["image_bytes"] > FIXED_FOOTPRINT_LIMITS["max_image_bytes"]:
        expected_violations.append("resource-byte-budget-exceeded:image")
    if integers["css_bytes"] > FIXED_FOOTPRINT_LIMITS["max_css_bytes"]:
        expected_violations.append("resource-byte-budget-exceeded:css")
    if integers["largest_single_asset_bytes"] > FIXED_FOOTPRINT_LIMITS["max_single_asset_bytes"]:
        expected_violations.append("single-asset-budget-exceeded")
    if violation_ids != expected_violations or footprint["within_fixed_footprint_limits"] is not (
        not expected_violations
    ):
        raise WebsiteRuntimeOptimisationError(f"{label} budget result is inconsistent.")
    if projected:
        saving = footprint["saving_bytes"]
        if isinstance(saving, bool) or not isinstance(saving, int) or not 1 <= saving <= MAX_TREE_BYTES:
            raise WebsiteRuntimeOptimisationError(f"{label}.saving_bytes must be a positive integer.")
    return footprint


def _project_runtime(
    retained_rows: Sequence[Mapping[str, object]],
    transformations: Sequence[Mapping[str, Any]],
) -> list[dict[str, object]]:
    current = {str(row["path"]): dict(row) for row in retained_rows}
    projected = dict(current)
    for row in transformations:
        source_path = str(row["source_path"])
        source = current.get(source_path)
        if (
            source is None
            or source["sha256"] != row["source_sha256"]
            or source["bytes"] != row["source_bytes"]
        ):
            raise WebsiteRuntimeOptimisationError(
                "Transformation does not bind an exact retained runtime file."
            )
        projected.pop(source_path, None)
        if row["action"] == "replace-runtime-bytes":
            output_path = str(row["projected_runtime_path"])
            if output_path in projected:
                raise WebsiteRuntimeOptimisationError(
                    "Projected runtime output collides with another retained path."
                )
            projected[output_path] = {
                "path": output_path,
                "bytes": int(row["projected_bytes"]),
                "sha256": str(row["projected_sha256"]),
            }
    if not projected:
        raise WebsiteRuntimeOptimisationError("Projected runtime closure may not be empty.")
    return [projected[path] for path in sorted(projected)]


def _tool_binding(root: Path, relative: Path, expected: str, *, production: bool) -> dict[str, object]:
    path = root / relative
    if production:
        raw, _ = _read_exact_file(
            path,
            expected,
            label=relative.as_posix(),
            max_bytes=MAX_REVIEWED_SOURCE_BYTES,
        )
        observed = _sha256_bytes(raw)
    else:
        observed = expected
    if observed != expected:
        raise WebsiteRuntimeOptimisationError(f"Reviewed source binding drifted: {relative.as_posix()}.")
    return {"path": relative.as_posix(), "sha256": observed}


def _require_launcher_attestation(root: Path) -> dict[str, Any]:
    attestation = globals().get("__aureon_runtime_optimisation_launcher_attestation__")
    if not isinstance(attestation, dict):
        raise WebsiteRuntimeOptimisationError(
            "Production compilation requires the isolated trusted launcher."
        )
    expected_fields = {
        "launcher_path",
        "launcher_sha256",
        "planner_path",
        "planner_sha256",
        "isolated",
        "no_site",
        "dont_write_bytecode",
    }
    if set(attestation) != expected_fields:
        raise WebsiteRuntimeOptimisationError("Trusted launcher attestation is malformed.")
    launcher = _ordinary_file(root / TRUSTED_LAUNCHER_PATH, label="Runtime optimisation launcher")
    implementation = _ordinary_file(root / IMPLEMENTATION_PATH, label="Runtime optimisation compiler")
    if (
        Path(str(attestation["launcher_path"])) != launcher
        or attestation["launcher_sha256"] != REVIEWED_TRUSTED_LAUNCHER_SHA256
        or _sha256_bytes(launcher.read_bytes()) != REVIEWED_TRUSTED_LAUNCHER_SHA256
        or Path(str(attestation["planner_path"])) != implementation
        or attestation["planner_sha256"] != _sha256_bytes(implementation.read_bytes())
        or attestation["isolated"] is not True
        or attestation["no_site"] is not True
        or attestation["dont_write_bytecode"] is not True
        or not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode)
    ):
        raise WebsiteRuntimeOptimisationError("Trusted launcher attestation does not bind this execution.")
    return attestation


def _controlled_input(root: Path, path: Path, *, allowed_root: Path, label: str) -> Path:
    candidate = _ordinary_file(path, label=label)
    boundary = _ordinary_directory(root / allowed_root, label=f"{label} root")
    if candidate.parent != boundary:
        raise WebsiteRuntimeOptimisationError(
            f"{label} must be an explicitly named file in {allowed_root.as_posix()}."
        )
    return candidate


def _compile_runtime_optimisation_proposal(
    *,
    repo_root: Path,
    source_plan_path: Path,
    source_plan_sha256: str,
    measurement_path: Path,
    measurement_sha256: str,
    acceptance_contract_path: Path,
    acceptance_contract_sha256: str,
    run_id: str | None = None,
    now: datetime | None = None,
    production: bool,
) -> dict[str, Any]:
    root = Path(os.path.abspath(repo_root))
    launcher_attestation: Mapping[str, Any] | None = None
    if production:
        raise WebsiteRuntimeOptimisationError(PRODUCTION_MEASUREMENT_PROVENANCE_STATE)
    resolved_now = (now or datetime.now(UTC)).astimezone(UTC)
    resolved_run_id = _safe_id(run_id or uuid.uuid4().hex, label="proposal run_id")
    plan_file = _controlled_input(
        root,
        source_plan_path,
        allowed_root=SOURCE_PLAN_ROOT,
        label="Source rationalisation plan",
    )
    evidence_file = _controlled_input(
        root,
        measurement_path,
        allowed_root=MEASUREMENT_ROOT,
        label="Runtime optimisation measurement evidence",
    )
    acceptance_file = _ordinary_file(acceptance_contract_path, label="Browser acceptance contract")
    if acceptance_file != Path(os.path.abspath(root / ACCEPTANCE_CONTRACT_PATH)):
        raise WebsiteRuntimeOptimisationError("Browser acceptance contract path is not canonical.")
    plan_raw, plan_identity = _read_exact_file(
        plan_file, source_plan_sha256, label="Source rationalisation plan"
    )
    evidence_raw, evidence_identity = _read_exact_file(
        evidence_file,
        measurement_sha256,
        label="Runtime optimisation measurement evidence",
    )
    acceptance_raw, acceptance_identity = _read_exact_file(
        acceptance_file,
        acceptance_contract_sha256,
        label="Browser acceptance contract",
    )
    plan = _require_source_plan(_strict_json(plan_raw, label="Source rationalisation plan"), now=resolved_now)
    evidence = require_measurement_evidence(
        _strict_json(evidence_raw, label="Runtime optimisation measurement evidence")
    )
    _require_fresh(evidence["measured_at"], now=resolved_now, label="measurement measured_at")
    retained = plan["retained_projection"]
    acceptance = _require_acceptance_contract(
        _strict_json(acceptance_raw, label="Browser acceptance contract"),
        retained=retained,
        reviewed_payload_required=production,
    )
    expected_source_binding = {
        "path": plan_file.relative_to(root).as_posix(),
        "file_sha256": source_plan_sha256,
        "payload_sha256": plan["payload_sha256"],
        "plan_run_id": plan["run_id"],
        "source_tree_sha256": plan["source_binding"]["tree_sha256"],
        "retained_tree_sha256": retained["tree_sha256"],
        "retained_manifest_sha256": retained["manifest_sha256"],
    }
    expected_acceptance_binding = {
        "path": ACCEPTANCE_CONTRACT_PATH.as_posix(),
        "file_sha256": acceptance_contract_sha256,
        "payload_sha256": acceptance["payloadSha256"],
        "contract_id": acceptance["contractId"],
    }
    if evidence["source_plan_binding"] != expected_source_binding:
        raise WebsiteRuntimeOptimisationError("Measurement evidence does not bind this exact source plan.")
    if evidence["acceptance_contract_binding"] != expected_acceptance_binding:
        raise WebsiteRuntimeOptimisationError(
            "Measurement evidence does not bind this exact browser contract."
        )
    methodology = evidence["methodology"]
    measurement_tool_path = root / str(methodology["tool_path"])
    _read_exact_file(
        measurement_tool_path,
        str(methodology["tool_sha256"]),
        label="Reviewed runtime measurement tool",
        max_bytes=MAX_REVIEWED_SOURCE_BYTES,
    )
    current_source_rows = _manifest(root / SOURCE_ROOT)
    if current_source_rows != plan["source_binding"]["files"]:
        raise WebsiteRuntimeOptimisationError("Canonical website source changed after source planning.")
    retained_rows = _manifest_rows(retained["files"], label="retained runtime projection")
    projected_rows = _project_runtime(retained_rows, evidence["transformations"])
    current_runtime = _footprint(retained_rows)
    projected_runtime = _footprint(projected_rows)
    projected_runtime["saving_bytes"] = current_runtime["total_bytes"] - projected_runtime["total_bytes"]
    implementation_sha256 = (
        str(launcher_attestation["planner_sha256"])
        if launcher_attestation is not None
        else _sha256_bytes(Path(__file__).read_bytes())
    )
    execution_binding = {
        "mode": "isolated-fixed-production" if production else "test-fixture-no-production-authority",
        "repo_root": str(root),
        "implementation": _tool_binding(
            root,
            IMPLEMENTATION_PATH,
            implementation_sha256,
            production=production,
        ),
        "trusted_launcher": _tool_binding(
            root, TRUSTED_LAUNCHER_PATH, REVIEWED_TRUSTED_LAUNCHER_SHA256, production=production
        ),
        "source_planner": _tool_binding(
            root, SOURCE_PLANNER_PATH, REVIEWED_SOURCE_PLANNER_SHA256, production=production
        ),
        "source_planner_launcher": _tool_binding(
            root, SOURCE_PLANNER_LAUNCHER_PATH, REVIEWED_SOURCE_PLANNER_LAUNCHER_SHA256, production=production
        ),
        "release_builder": _tool_binding(
            root, RELEASE_BUILDER_PATH, REVIEWED_RELEASE_BUILDER_SHA256, production=production
        ),
        "motion_policy": _tool_binding(
            root, MOTION_POLICY_PATH, REVIEWED_MOTION_POLICY_SHA256, production=production
        ),
        "secure_writer": _tool_binding(
            root, SECURE_WRITER_PATH, REVIEWED_SECURE_WRITER_SHA256, production=production
        ),
        "measurement_tool": _tool_binding(
            root,
            Path(str(methodology["tool_path"])),
            str(methodology["tool_sha256"]),
            production=production,
        ),
        "commands_executed": False,
        "transformations_executed": False,
        "production_writable": production,
    }
    proposal: dict[str, Any] = {
        "schema": PROPOSAL_SCHEMA,
        "generated_at": _utc_iso(resolved_now),
        "run_id": resolved_run_id,
        "state": "proposal-only",
        "source_plan_binding": expected_source_binding,
        "measurement_binding": {
            "path": evidence_file.relative_to(root).as_posix(),
            "file_sha256": measurement_sha256,
            "payload_sha256": evidence["payload_sha256"],
            "measurement_run_id": evidence["run_id"],
        },
        "acceptance_contract_binding": expected_acceptance_binding,
        "current_runtime": current_runtime,
        "projected_runtime": projected_runtime,
        "transformations": [dict(row) for row in evidence["transformations"]],
        "acceptance_requirements": [
            {"id": identifier, "required": True, "status": "blocked-not-run", "passed": False}
            for identifier in ACCEPTANCE_REQUIREMENT_IDS
        ],
        "execution_binding": execution_binding,
        "eligible_for_next_local_gate": False,
        "authority": dict(NO_AUTHORITY),
    }
    proposal["payload_sha256"] = _json_sha256(proposal)
    require_runtime_optimisation_proposal(proposal)
    # Final current-source and exact-input replay closes the pre-write TOCTOU window.
    if _manifest(root / SOURCE_ROOT) != current_source_rows:
        raise WebsiteRuntimeOptimisationError("Canonical source changed during proposal compilation.")
    for path, raw, identity, label in (
        (plan_file, plan_raw, plan_identity, "Source rationalisation plan"),
        (evidence_file, evidence_raw, evidence_identity, "Measurement evidence"),
        (acceptance_file, acceptance_raw, acceptance_identity, "Browser acceptance contract"),
    ):
        after = path.lstat()
        if (
            not _same_identity(identity, after)
            or int(after.st_size) != len(raw)
            or _sha256_bytes(path.read_bytes()) != _sha256_bytes(raw)
        ):
            raise WebsiteRuntimeOptimisationError(f"{label} changed during proposal compilation.")
    if production:
        for binding in execution_binding.values():
            if isinstance(binding, Mapping) and set(binding) == {"path", "sha256"}:
                _tool_binding(
                    root,
                    Path(str(binding["path"])),
                    str(binding["sha256"]),
                    production=True,
                )
    return proposal


def compile_runtime_optimisation_proposal(
    *,
    source_plan_path: Path,
    source_plan_sha256: str,
    measurement_path: Path,
    measurement_sha256: str,
    acceptance_contract_path: Path,
    acceptance_contract_sha256: str,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Compile one canonical proposal; production requires the isolated launcher."""

    return _compile_runtime_optimisation_proposal(
        repo_root=_canonical_repo_root(),
        source_plan_path=source_plan_path,
        source_plan_sha256=source_plan_sha256,
        measurement_path=measurement_path,
        measurement_sha256=measurement_sha256,
        acceptance_contract_path=acceptance_contract_path,
        acceptance_contract_sha256=acceptance_contract_sha256,
        run_id=run_id,
        production=True,
    )


def require_runtime_optimisation_proposal(value: object) -> dict[str, Any]:
    """Validate the immutable proposal contract without treating it as execution proof."""

    proposal = _exact_object(value, _PROPOSAL_FIELDS, label="Runtime optimisation proposal")
    if proposal.get("schema") != PROPOSAL_SCHEMA or proposal.get("state") != "proposal-only":
        raise WebsiteRuntimeOptimisationError("Runtime optimisation proposal schema or state is invalid.")
    _payload_hash(proposal)
    _safe_id(proposal.get("run_id"), label="proposal run_id")
    _parse_utc(proposal.get("generated_at"), label="proposal generated_at")
    if proposal.get("authority") != NO_AUTHORITY or proposal.get("eligible_for_next_local_gate") is not False:
        raise WebsiteRuntimeOptimisationError("Runtime optimisation proposal grants downstream authority.")
    _require_source_plan_binding(proposal.get("source_plan_binding"), label="Proposal source-plan binding")
    measurement_binding = _exact_object(
        proposal.get("measurement_binding"),
        _MEASUREMENT_BINDING_FIELDS,
        label="Proposal measurement binding",
    )
    _safe_relative_path(measurement_binding["path"])
    _require_sha256(measurement_binding["file_sha256"], label="measurement_binding.file_sha256")
    _require_sha256(measurement_binding["payload_sha256"], label="measurement_binding.payload_sha256")
    _safe_id(measurement_binding["measurement_run_id"], label="measurement_binding.measurement_run_id")
    _require_acceptance_binding(
        proposal.get("acceptance_contract_binding"),
        label="Proposal acceptance-contract binding",
    )
    current_runtime = _require_footprint(
        proposal.get("current_runtime"), label="Current runtime footprint", projected=False
    )
    projected_runtime = _require_footprint(
        proposal.get("projected_runtime"), label="Projected runtime footprint", projected=True
    )
    if (
        projected_runtime["total_bytes"] >= current_runtime["total_bytes"]
        or projected_runtime["saving_bytes"]
        != current_runtime["total_bytes"] - projected_runtime["total_bytes"]
    ):
        raise WebsiteRuntimeOptimisationError("Projected runtime saving arithmetic is inconsistent.")
    requirements = proposal.get("acceptance_requirements")
    if not isinstance(requirements, list) or [
        row.get("id") for row in requirements if isinstance(row, Mapping)
    ] != list(ACCEPTANCE_REQUIREMENT_IDS):
        raise WebsiteRuntimeOptimisationError(
            "Runtime optimisation proposal acceptance contract is incomplete."
        )
    for index, row in enumerate(requirements):
        requirement = _exact_object(
            row,
            _ACCEPTANCE_REQUIREMENT_FIELDS,
            label=f"Acceptance requirement[{index}]",
        )
        if (
            requirement["required"] is not True
            or requirement["status"] != "blocked-not-run"
            or requirement["passed"] is not False
        ):
            raise WebsiteRuntimeOptimisationError(
                "Runtime optimisation proposal fabricates acceptance evidence."
            )
    execution = _exact_object(
        proposal.get("execution_binding"),
        _EXECUTION_BINDING_FIELDS,
        label="Proposal execution binding",
    )
    if (
        execution["mode"] != "test-fixture-no-production-authority"
        or not isinstance(execution["repo_root"], str)
        or not execution["repo_root"]
        or execution["commands_executed"] is not False
        or execution["transformations_executed"] is not False
        or execution["production_writable"] is not False
    ):
        raise WebsiteRuntimeOptimisationError("Runtime optimisation proposal claims execution.")
    for field in (
        "implementation",
        "trusted_launcher",
        "source_planner",
        "source_planner_launcher",
        "release_builder",
        "motion_policy",
        "secure_writer",
        "measurement_tool",
    ):
        binding = _exact_object(execution[field], _TOOL_BINDING_FIELDS, label=f"execution_binding.{field}")
        _safe_relative_path(binding["path"])
        _require_sha256(binding["sha256"], label=f"execution_binding.{field}.sha256")
    _require_transformation_rows(proposal.get("transformations"))
    return proposal


def _load_secure_writer(root: Path) -> ModuleType:
    writer = _ordinary_file(root / SECURE_WRITER_PATH, label="Reviewed immutable-artifact writer")
    raw, _ = _read_exact_file(
        writer,
        REVIEWED_SECURE_WRITER_SHA256,
        label="Reviewed immutable-artifact writer",
        max_bytes=MAX_REVIEWED_SOURCE_BYTES,
    )
    module = ModuleType("_aureon_runtime_optimisation_secure_writer")
    module.__file__ = str(writer)
    module.__package__ = None
    sys.modules[module.__name__] = module
    try:
        exec(compile(raw, str(writer), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception:
        sys.modules.pop(module.__name__, None)
        raise
    if not callable(getattr(module, "write_new_file", None)):
        raise WebsiteRuntimeOptimisationError("Reviewed immutable writer lacks write_new_file.")
    return module


def _revalidate_proposal_inputs(root: Path, proposal: Mapping[str, Any]) -> None:
    """Replay exact proposal inputs immediately before the immutable write."""

    source_binding = proposal.get("source_plan_binding")
    measurement_binding = proposal.get("measurement_binding")
    acceptance_binding = proposal.get("acceptance_contract_binding")
    execution = proposal.get("execution_binding")
    if not all(
        isinstance(item, Mapping)
        for item in (source_binding, measurement_binding, acceptance_binding, execution)
    ):
        raise WebsiteRuntimeOptimisationError("Proposal input bindings are malformed.")
    assert isinstance(source_binding, Mapping)
    assert isinstance(measurement_binding, Mapping)
    assert isinstance(acceptance_binding, Mapping)
    assert isinstance(execution, Mapping)
    plan_raw, _ = _read_exact_file(
        root / str(source_binding["path"]),
        str(source_binding["file_sha256"]),
        label="Source plan pre-write replay",
    )
    evidence_raw, _ = _read_exact_file(
        root / str(measurement_binding["path"]),
        str(measurement_binding["file_sha256"]),
        label="Measurement evidence pre-write replay",
    )
    acceptance_raw, _ = _read_exact_file(
        root / str(acceptance_binding["path"]),
        str(acceptance_binding["file_sha256"]),
        label="Browser acceptance contract pre-write replay",
    )
    plan = _require_source_plan(
        _strict_json(plan_raw, label="Source plan pre-write replay"),
        now=datetime.now(UTC),
    )
    evidence = require_measurement_evidence(
        _strict_json(evidence_raw, label="Measurement evidence pre-write replay")
    )
    _require_fresh(evidence["measured_at"], now=datetime.now(UTC), label="measurement measured_at")
    _require_acceptance_contract(
        _strict_json(acceptance_raw, label="Browser acceptance contract pre-write replay"),
        retained=plan["retained_projection"],
    )
    if _manifest(root / SOURCE_ROOT) != plan["source_binding"]["files"]:
        raise WebsiteRuntimeOptimisationError("Canonical source changed before proposal write.")
    for binding in execution.values():
        if isinstance(binding, Mapping) and set(binding) == {"path", "sha256"}:
            _tool_binding(
                root,
                Path(str(binding["path"])),
                str(binding["sha256"]),
                production=True,
            )


def write_runtime_optimisation_proposal(
    *,
    source_plan_path: Path,
    source_plan_sha256: str,
    measurement_path: Path,
    measurement_sha256: str,
    acceptance_contract_path: Path,
    acceptance_contract_sha256: str,
    output_path: Path,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Compile and exclusively write one proposal under the controlled artifact root."""

    root = _canonical_repo_root()
    proposal = compile_runtime_optimisation_proposal(
        source_plan_path=source_plan_path,
        source_plan_sha256=source_plan_sha256,
        measurement_path=measurement_path,
        measurement_sha256=measurement_sha256,
        acceptance_contract_path=acceptance_contract_path,
        acceptance_contract_sha256=acceptance_contract_sha256,
        run_id=run_id,
    )
    output = Path(os.path.abspath(output_path))
    parent = _ordinary_directory(root / PROPOSAL_ROOT, label="Runtime optimisation proposal root")
    if output.parent != parent or output.suffix.lower() != ".json":
        raise WebsiteRuntimeOptimisationError(
            "Proposal output must be a new JSON file in the controlled proposal root."
        )
    writer = _load_secure_writer(root)
    _revalidate_proposal_inputs(root, proposal)
    payload = (
        json.dumps(proposal, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8")
        + b"\n"
    )
    writer.write_new_file(output, payload)
    if output.read_bytes() != payload:
        raise WebsiteRuntimeOptimisationError("Immutable proposal failed exact read-back.")
    return proposal


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="website-runtime-optimisation")
    parser.add_argument("--source-plan", type=Path, required=True)
    parser.add_argument("--source-plan-sha256", required=True)
    parser.add_argument("--measurement", type=Path, required=True)
    parser.add_argument("--measurement-sha256", required=True)
    parser.add_argument("--acceptance-contract", type=Path, required=True)
    parser.add_argument("--acceptance-contract-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-id")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        proposal = write_runtime_optimisation_proposal(
            source_plan_path=args.source_plan,
            source_plan_sha256=args.source_plan_sha256,
            measurement_path=args.measurement,
            measurement_sha256=args.measurement_sha256,
            acceptance_contract_path=args.acceptance_contract,
            acceptance_contract_sha256=args.acceptance_contract_sha256,
            output_path=args.output,
            run_id=args.run_id,
        )
    except (WebsiteRuntimeOptimisationError, OSError) as exc:
        print(f"blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(proposal, sort_keys=True, separators=(",", ":")))
    return 0


__all__ = [
    "ACCEPTANCE_CONTRACT_SCHEMA",
    "ACCEPTANCE_REQUIREMENT_IDS",
    "FIXED_FOOTPRINT_LIMITS",
    "MEASUREMENT_AUTHORITY",
    "MEASUREMENT_SCHEMA",
    "NO_AUTHORITY",
    "PROPOSAL_SCHEMA",
    "WebsiteRuntimeOptimisationError",
    "compile_runtime_optimisation_proposal",
    "require_measurement_evidence",
    "require_runtime_optimisation_proposal",
    "write_runtime_optimisation_proposal",
]


if __name__ == "__main__":
    raise SystemExit(main())
