"""Source-bound competitor benchmark evidence for Aureon's design feedback loop.

This module intentionally performs no network requests, browser automation,
package construction, backup, or deployment.  It verifies that the local
WebsiteOperator competitor metadata has a complete provenance and freshness
record.  It does *not* claim that a remote page is unchanged, and a passing
result has no release or deployment authority.

Competitor research is retained only as short abstract design-pattern notes.
The contract deliberately excludes copied page content, source code, imagery,
screenshots, CSS, and trade dress.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

BENCHMARK_SCHEMA = "aureon.design-benchmark-evidence.v1"
VERIFICATION_SCHEMA = "aureon.design-benchmark-evidence-verification.v1"
DEFAULT_CONFIG_PATH = "aureon/operator/website_operator.defaults.json"
EVIDENCE_OUTPUT_DIRECTORY = "artifacts/website-operator"

OBSERVATION_TYPE = "abstract-design-pattern"
PATTERN_USE_BOUNDARY = (
    "Abstract pattern notes only; never retain or copy competitor code, copy, "
    "imagery, screenshots, assets, CSS, HTML, or trade dress."
)
LOCAL_METADATA_VERIFICATION = (
    "Local configuration provenance only; remote page content is not fetched or "
    "asserted unchanged by this validator."
)
NON_AUTHORITATIVE_AUTHORITY = {
    "scope": "local competitor-metadata provenance and design-feedback evidence only",
    "release_eligibility": "always-false",
    "package_authority": "none",
    "deployment_authority": "none",
    "credential_access": "none",
    "remote_fetch": "not performed",
    "human_research_review": "required when refreshing source observations",
}

_SOURCE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
_SHA256 = re.compile(r"^[A-F0-9]{64}$")
_SOURCE_FIELDS = frozenset(
    {
        "id",
        "name",
        "official_url",
        "official_host",
        "checked_at",
        "metadata_sha256",
        "observation_type",
        "patterns",
        "use_boundary",
        "metadata_verification",
        "remote_content_fetched",
    }
)
_EVIDENCE_FIELDS = frozenset(
    {
        "schema",
        "generated_at",
        "snapshot_kind",
        "authority",
        "config",
        "freshness_policy",
        "sources",
        "verification",
    }
)
_CONFIG_FIELDS = frozenset({"path", "sha256"})


class DesignBenchmarkEvidenceError(ValueError):
    """The local benchmark evidence cannot be read or safely validated."""


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise DesignBenchmarkEvidenceError(f"{label} must be a non-empty ISO-8601 timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DesignBenchmarkEvidenceError(f"{label} must be an ISO-8601 timestamp with a timezone.") from exc
    if parsed.tzinfo is None:
        raise DesignBenchmarkEvidenceError(f"{label} must include a timezone.")
    return parsed.astimezone(UTC)


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest().upper()


def _find_repo_root(start: Path | None = None) -> Path:
    candidate = (start or Path.cwd()).resolve()
    for root in (candidate, *candidate.parents):
        if (root / "pyproject.toml").is_file() and (root / "aureon").is_dir():
            return root
    raise DesignBenchmarkEvidenceError(
        "Could not locate an Aureon repository with pyproject.toml and aureon/."
    )


def _safe_repo_path(repo_root: Path, value: object) -> tuple[Path, str]:
    if not isinstance(value, str) or not value.strip():
        raise DesignBenchmarkEvidenceError("A benchmark path must be a non-empty relative path.")
    normalised = value.replace("\\", "/")
    relative = Path(normalised)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise DesignBenchmarkEvidenceError(f"Unsafe benchmark path: {value}")
    path = (repo_root / relative).resolve()
    try:
        path.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise DesignBenchmarkEvidenceError(f"Benchmark path escapes the repository: {value}") from exc
    return path, relative.as_posix()


def _safe_evidence_output_path(repo_root: Path, value: object) -> Path:
    path, relative = _safe_repo_path(repo_root, value)
    allowed_root, allowed_relative = _safe_repo_path(repo_root, EVIDENCE_OUTPUT_DIRECTORY)
    try:
        path.relative_to(allowed_root)
    except ValueError as exc:
        raise DesignBenchmarkEvidenceError(
            f"Benchmark evidence output must be inside {allowed_relative}/."
        ) from exc
    if path.suffix.casefold() != ".json" or not path.name.startswith("design-benchmark-evidence-"):
        raise DesignBenchmarkEvidenceError(
            "Benchmark evidence output must be a new design-benchmark-evidence-*.json file."
        )
    if path.exists():
        raise DesignBenchmarkEvidenceError(f"Refusing to overwrite existing benchmark evidence: {relative}")
    return path


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DesignBenchmarkEvidenceError(f"JSON file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DesignBenchmarkEvidenceError(f"JSON file is invalid: {path}") from exc
    if not isinstance(value, dict):
        raise DesignBenchmarkEvidenceError(f"JSON file must contain one object: {path}")
    return value


def _clean_pattern(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise DesignBenchmarkEvidenceError(f"{label} must be text.")
    pattern = " ".join(value.split())
    if not 3 <= len(pattern) <= 180:
        raise DesignBenchmarkEvidenceError(f"{label} must be 3 to 180 characters.")
    lowered = pattern.casefold()
    forbidden = ("<", ">", "http://", "https://", "www.", "{", "}", "```", "data:")
    if any(token in lowered for token in forbidden):
        raise DesignBenchmarkEvidenceError(
            f"{label} must be an abstract pattern note, not copied source expression."
        )
    return pattern


def _source_metadata(config_source: Mapping[str, Any]) -> dict[str, Any]:
    identifier = config_source.get("id")
    name = config_source.get("name")
    url = config_source.get("url")
    checked_at = config_source.get("checked_at")
    patterns = config_source.get("patterns")
    if not isinstance(identifier, str) or not _SOURCE_ID.fullmatch(identifier):
        raise DesignBenchmarkEvidenceError("Competitor source id must be a stable lowercase identifier.")
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 120:
        raise DesignBenchmarkEvidenceError(f"Competitor source '{identifier}' needs a concise name.")
    if not isinstance(url, str):
        raise DesignBenchmarkEvidenceError(f"Competitor source '{identifier}' needs an HTTPS URL.")
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or not parsed.path
    ):
        raise DesignBenchmarkEvidenceError(
            f"Competitor source '{identifier}' must use a direct credential-free HTTPS URL."
        )
    _parse_datetime(checked_at, f"competitor source '{identifier}' checked_at")
    if not isinstance(patterns, list) or not patterns:
        raise DesignBenchmarkEvidenceError(
            f"Competitor source '{identifier}' needs at least one abstract pattern note."
        )
    cleaned_patterns = [
        _clean_pattern(pattern, f"competitor source '{identifier}' pattern") for pattern in patterns
    ]
    if len(set(cleaned_patterns)) != len(cleaned_patterns):
        raise DesignBenchmarkEvidenceError(f"Competitor source '{identifier}' cannot repeat a pattern note.")
    return {
        "id": identifier,
        "name": name.strip(),
        "official_url": url,
        "official_host": parsed.hostname.casefold(),
        "checked_at": _iso(_parse_datetime(checked_at, f"competitor source '{identifier}' checked_at")),
        "patterns": cleaned_patterns,
    }


def _metadata_hash(metadata: Mapping[str, Any]) -> str:
    return _sha256_bytes(
        _canonical_json(
            {
                "id": metadata["id"],
                "name": metadata["name"],
                "official_url": metadata["official_url"],
                "official_host": metadata["official_host"],
                "checked_at": metadata["checked_at"],
                "patterns": metadata["patterns"],
            }
        )
    )


def _load_design_config(
    repo_root: Path, config_path: str = DEFAULT_CONFIG_PATH
) -> tuple[Path, str, dict[str, Any], Mapping[str, Any], list[dict[str, Any]]]:
    path, relative = _safe_repo_path(repo_root, config_path)
    config = _read_json(path)
    design, metadata = _design_metadata_from_config(config)
    return path, relative, config, design, metadata


def _design_metadata_from_config(
    config: Mapping[str, Any],
) -> tuple[Mapping[str, Any], list[dict[str, Any]]]:
    """Read only the strict benchmark contract from an operator config mapping."""

    if not isinstance(config, Mapping):
        raise DesignBenchmarkEvidenceError("WebsiteOperator config must be an object mapping.")
    design = config.get("design")
    if not isinstance(design, Mapping):
        raise DesignBenchmarkEvidenceError("WebsiteOperator config has no design section.")
    max_age_days = design.get("competitor_max_age_days")
    target = design.get("competitor_source_target")
    source_rows = design.get("competitor_sources")
    if not isinstance(max_age_days, int) or max_age_days < 1:
        raise DesignBenchmarkEvidenceError("design.competitor_max_age_days must be a positive integer.")
    if not isinstance(target, int) or target < 1:
        raise DesignBenchmarkEvidenceError("design.competitor_source_target must be a positive integer.")
    if not isinstance(source_rows, list):
        raise DesignBenchmarkEvidenceError("design.competitor_sources must be an array.")
    metadata = [_source_metadata(source) for source in source_rows if isinstance(source, Mapping)]
    if len(metadata) != len(source_rows):
        raise DesignBenchmarkEvidenceError("Each design.competitor_sources item must be an object.")
    identifiers = [row["id"] for row in metadata]
    if len(set(identifiers)) != len(identifiers):
        raise DesignBenchmarkEvidenceError("design.competitor_sources ids must be unique.")
    return design, metadata


def _mapping_sha256(value: Mapping[str, Any]) -> str:
    """Return the canonical semantic hash used to bind a supplied config mapping.

    The file-backed verifier continues to bind an evidence record to its exact
    on-disk SHA-256.  This second hash proves that an in-memory mapping is the
    same configuration, independent of insignificant JSON whitespace.
    """

    return _sha256_bytes(_canonical_json(_json_compatible(value)))


def _json_compatible(value: object) -> Any:
    """Copy a generic mapping into a canonical JSON-safe value without mutation."""

    if isinstance(value, Mapping):
        copied: dict[str, Any] = {}
        for key, nested in value.items():
            if not isinstance(key, str):
                raise DesignBenchmarkEvidenceError(
                    "Supplied WebsiteOperator config must use string keys for provenance verification."
                )
            copied[key] = _json_compatible(nested)
        return copied
    if isinstance(value, (list, tuple)):
        return [_json_compatible(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        raise DesignBenchmarkEvidenceError(
            "Supplied WebsiteOperator config cannot contain non-finite numbers."
        )
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise DesignBenchmarkEvidenceError(
        "Supplied WebsiteOperator config must be JSON-serializable for provenance verification."
    )


def _freshness_policy(design: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "max_age_days": design["competitor_max_age_days"],
        "minimum_fresh_sources": design["competitor_source_target"],
        "clock": "UTC",
        "refresh_when_stale": True,
        "source_requirement": "credential-free HTTPS source metadata",
        "copying_prohibited": True,
        "trade_dress_prohibited": True,
        "store_remote_content": False,
    }


def _source_record(metadata: Mapping[str, Any]) -> dict[str, Any]:
    return {
        **metadata,
        "metadata_sha256": _metadata_hash(metadata),
        "observation_type": OBSERVATION_TYPE,
        "use_boundary": PATTERN_USE_BOUNDARY,
        "metadata_verification": LOCAL_METADATA_VERIFICATION,
        "remote_content_fetched": False,
    }


def _check(identifier: str, passed: bool, message: str, **evidence: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"id": identifier, "passed": passed, "message": message}
    if evidence:
        payload["evidence"] = evidence
    return payload


def _compare_source_record(record: object, expected: Mapping[str, Any]) -> tuple[bool, str]:
    if not isinstance(record, Mapping):
        return False, "source record is not an object"
    if set(record) != _SOURCE_FIELDS:
        return False, "source record fields are not the strict abstract-pattern contract"
    for field in ("id", "name", "official_url", "official_host", "checked_at", "patterns"):
        if record.get(field) != expected[field]:
            return False, f"{field} no longer matches WebsiteOperator metadata"
    if record.get("metadata_sha256") != _metadata_hash(expected):
        return False, "metadata_sha256 is not bound to the declared source metadata"
    if record.get("observation_type") != OBSERVATION_TYPE:
        return False, "observation_type is not abstract-design-pattern"
    if record.get("use_boundary") != PATTERN_USE_BOUNDARY:
        return False, "the no-copy/no-trade-dress boundary is missing or changed"
    if record.get("metadata_verification") != LOCAL_METADATA_VERIFICATION:
        return False, "metadata verification scope is missing or changed"
    if record.get("remote_content_fetched") is not False:
        return False, "benchmark evidence must not retain fetched remote content"
    try:
        _source_metadata(
            {
                "id": record.get("id"),
                "name": record.get("name"),
                "url": record.get("official_url"),
                "checked_at": record.get("checked_at"),
                "patterns": record.get("patterns"),
            }
        )
    except DesignBenchmarkEvidenceError as exc:
        return False, str(exc)
    return True, "source metadata is config-bound and abstract-pattern-only"


def discover_design_benchmark_evidence(
    repo_root: Path | None = None,
    *,
    config_path: str = DEFAULT_CONFIG_PATH,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Create a local, source-bound competitor benchmark evidence snapshot.

    Discovery reads only the committed WebsiteOperator configuration.  It does
    not contact a competitor, fetch web content, or grant any release right.
    """

    root = _find_repo_root(repo_root)
    config, relative, _raw_config, design, metadata = _load_design_config(root, config_path)
    moment = (now or _utc_now()).astimezone(UTC)
    snapshot: dict[str, Any] = {
        "schema": BENCHMARK_SCHEMA,
        "generated_at": _iso(moment),
        "snapshot_kind": "local-config-provenance-not-remote-content-verification",
        "authority": dict(NON_AUTHORITATIVE_AUTHORITY),
        "config": {"path": relative, "sha256": _sha256_file(config)},
        "freshness_policy": _freshness_policy(design),
        "sources": [_source_record(item) for item in metadata],
        "verification": {
            "schema": VERIFICATION_SCHEMA,
            "verified_at": _iso(moment),
            "state": "fail",
            "passed": False,
            "release_eligible": False,
            "deployment_authority": "none",
            "checks": [],
        },
    }
    snapshot["verification"] = verify_design_benchmark_evidence(snapshot, repo_root=root, now=moment)
    return snapshot


def verify_design_benchmark_evidence(
    evidence: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Verify local evidence without treating it as remote or release proof."""

    root = _find_repo_root(repo_root)
    moment = (now or _utc_now()).astimezone(UTC)
    checks: list[dict[str, Any]] = []
    checks.append(
        _check(
            "schema",
            evidence.get("schema") == BENCHMARK_SCHEMA,
            "Benchmark evidence schema must match the current contract.",
        )
    )
    checks.append(
        _check(
            "strict-record-shape",
            set(evidence) == _EVIDENCE_FIELDS,
            "Benchmark evidence may contain only the explicit local-provenance contract fields.",
        )
    )
    checks.append(
        _check(
            "non-authoritative-boundary",
            evidence.get("authority") == NON_AUTHORITATIVE_AUTHORITY,
            "Benchmark evidence must retain no package, release, credential, or deployment authority.",
        )
    )
    checks.append(
        _check(
            "local-only-verification-scope",
            evidence.get("snapshot_kind") == "local-config-provenance-not-remote-content-verification",
            "The evidence must not overstate local metadata validation as a remote-page verification.",
        )
    )

    config_ok = False
    expected_metadata: list[dict[str, Any]] = []
    expected_policy: dict[str, Any] = {}
    config_record = evidence.get("config")
    if isinstance(config_record, Mapping) and set(config_record) == _CONFIG_FIELDS:
        try:
            path, relative, _raw_config, design, expected_metadata = _load_design_config(
                root, str(config_record.get("path") or "")
            )
            expected_policy = _freshness_policy(design)
            config_ok = (
                config_record.get("path") == relative
                and config_record.get("sha256") == _sha256_file(path)
                and isinstance(config_record.get("sha256"), str)
                and bool(_SHA256.fullmatch(str(config_record.get("sha256"))))
            )
        except DesignBenchmarkEvidenceError:
            config_ok = False
    checks.append(
        _check(
            "config-provenance",
            config_ok,
            "The source metadata must bind to the unchanged local WebsiteOperator config.",
        )
    )
    checks.append(
        _check(
            "freshness-policy",
            bool(expected_policy) and evidence.get("freshness_policy") == expected_policy,
            "Freshness, HTTPS, no-copy, no-trade-dress, and remote-content policy must match config.",
        )
    )

    generated_at_ok = False
    try:
        generated_at = _parse_datetime(evidence.get("generated_at"), "generated_at")
        generated_at_ok = generated_at <= moment + timedelta(minutes=5)
    except DesignBenchmarkEvidenceError:
        generated_at_ok = False
    checks.append(
        _check(
            "snapshot-timestamp",
            generated_at_ok,
            "Evidence generation time must be timezone-aware and not materially in the future.",
        )
    )

    embedded_verification = evidence.get("verification")
    embedded_verification_ok = (
        isinstance(embedded_verification, Mapping)
        and embedded_verification.get("schema") == VERIFICATION_SCHEMA
        and embedded_verification.get("release_eligible") is False
        and embedded_verification.get("deployment_authority") == "none"
    )
    checks.append(
        _check(
            "embedded-verification-boundary",
            embedded_verification_ok,
            "The embedded snapshot summary must retain its non-authoritative release boundary.",
        )
    )

    rows = evidence.get("sources")
    source_binding_ok = isinstance(rows, list) and len(rows) == len(expected_metadata)
    freshness_rows: list[tuple[str, bool, str]] = []
    expected_by_id = {row["id"]: row for row in expected_metadata}
    seen_identifiers: set[str] = set()
    if isinstance(rows, list):
        for record in rows:
            identifier = record.get("id") if isinstance(record, Mapping) else ""
            if not isinstance(identifier, str) or identifier in seen_identifiers:
                source_binding_ok = False
                continue
            seen_identifiers.add(identifier)
            expected = expected_by_id.get(identifier)
            if expected is None:
                source_binding_ok = False
                continue
            matches, _reason = _compare_source_record(record, expected)
            if not matches:
                source_binding_ok = False
                continue
            try:
                checked_at = _parse_datetime(record.get("checked_at"), f"source '{identifier}' checked_at")
                age = moment - checked_at
                fresh = timedelta(0) <= age <= timedelta(days=expected_policy["max_age_days"])
                freshness_rows.append((identifier, fresh, _iso(checked_at)))
            except (DesignBenchmarkEvidenceError, KeyError):
                source_binding_ok = False
    source_binding_ok = source_binding_ok and set(expected_by_id) == seen_identifiers
    checks.append(
        _check(
            "source-metadata-binding",
            source_binding_ok,
            "Every source must exactly match the configured HTTPS metadata and abstract observation boundary.",
            expected_source_count=len(expected_metadata),
            observed_source_count=len(rows) if isinstance(rows, list) else 0,
        )
    )

    fresh_count = sum(1 for _identifier, fresh, _checked_at in freshness_rows if fresh)
    target = expected_policy.get("minimum_fresh_sources", 1)
    freshness_ok = source_binding_ok and fresh_count >= target
    checks.append(
        _check(
            "fresh-source-coverage",
            freshness_ok,
            "Enough source observations must remain within the configured UTC freshness window.",
            fresh_source_count=fresh_count,
            required_fresh_sources=target,
            sources=[
                {"id": identifier, "fresh": fresh, "checked_at": checked_at}
                for identifier, fresh, checked_at in freshness_rows
            ],
        )
    )

    passed = all(bool(check["passed"]) for check in checks)
    return {
        "schema": VERIFICATION_SCHEMA,
        "verified_at": _iso(moment),
        "state": "pass" if passed else "fail",
        "passed": passed,
        "release_eligible": False,
        "deployment_authority": "none",
        "checks": checks,
    }


def verify_design_benchmark_evidence_against_config(
    evidence: Mapping[str, Any],
    config: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
    config_path: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Verify benchmark evidence against an in-memory WebsiteOperator mapping.

    This is a read-only integration adapter for a future WebsiteOperator call
    site.  It first preserves the normal file-backed provenance check, then
    proves that the supplied mapping is semantically identical to that declared
    config and exposes the same strict benchmark metadata.  It never fetches a
    competitor, writes a receipt, changes the mapping, or grants release or
    deployment authority.

    ``config_path`` is repository-relative when provided and must exactly equal
    the path recorded in the evidence.  Supplying a path prevents a caller from
    accidentally validating an operator's in-memory config against a different
    local policy file.
    """

    root = _find_repo_root(repo_root)
    moment = (now or _utc_now()).astimezone(UTC)
    base = verify_design_benchmark_evidence(evidence, repo_root=root, now=moment)
    checks = [dict(check) for check in base["checks"]]

    config_record = evidence.get("config")
    declared_path = ""
    declared_path_ok = (
        isinstance(config_record, Mapping)
        and set(config_record) == _CONFIG_FIELDS
        and isinstance(config_record.get("path"), str)
    )
    if isinstance(config_record, Mapping) and declared_path_ok:
        declared_path = str(config_record["path"])

    requested_path = config_path if config_path is not None else declared_path
    path_ok = False
    disk_config: dict[str, Any] | None = None
    if declared_path_ok and isinstance(requested_path, str):
        try:
            _requested, requested_relative = _safe_repo_path(root, requested_path)
            disk_path, declared_relative = _safe_repo_path(root, declared_path)
            path_ok = requested_relative == declared_relative
            if path_ok:
                disk_config = _read_json(disk_path)
        except DesignBenchmarkEvidenceError:
            path_ok = False
    checks.append(
        _check(
            "supplied-config-path",
            path_ok,
            "The supplied WebsiteOperator config path must exactly match the evidence provenance path.",
        )
    )

    mapping_contract_ok = False
    mapping_sha256 = ""
    try:
        supplied_design, supplied_metadata = _design_metadata_from_config(config)
        mapping_sha256 = _mapping_sha256(config)
        mapping_contract_ok = (
            _freshness_policy(supplied_design) == evidence.get("freshness_policy")
            and isinstance(evidence.get("sources"), list)
            and len(evidence["sources"]) == len(supplied_metadata)
            and all(
                _compare_source_record(record, expected)[0]
                for record, expected in zip(evidence["sources"], supplied_metadata, strict=True)
            )
        )
    except (DesignBenchmarkEvidenceError, TypeError, ValueError):
        mapping_contract_ok = False
    checks.append(
        _check(
            "supplied-config-design-contract",
            mapping_contract_ok,
            "The supplied mapping must retain the exact abstract-pattern, no-copy and freshness contract.",
        )
    )

    mapping_provenance_ok = False
    if path_ok and disk_config is not None and mapping_sha256:
        try:
            mapping_provenance_ok = mapping_sha256 == _mapping_sha256(disk_config)
        except DesignBenchmarkEvidenceError:
            mapping_provenance_ok = False
    checks.append(
        _check(
            "supplied-config-provenance",
            mapping_provenance_ok,
            "The supplied mapping must be semantically identical to the file bound by the evidence SHA-256.",
        )
    )

    adapter_boundary_ok = (
        base.get("release_eligible") is False
        and base.get("deployment_authority") == "none"
        and evidence.get("authority") == NON_AUTHORITATIVE_AUTHORITY
    )
    checks.append(
        _check(
            "adapter-non-authoritative-boundary",
            adapter_boundary_ok,
            "In-memory verification has no release, package, credential, or deployment authority.",
        )
    )

    passed = all(bool(check["passed"]) for check in checks)
    return {
        "schema": VERIFICATION_SCHEMA,
        "verified_at": _iso(moment),
        "state": "pass" if passed else "fail",
        "passed": passed,
        "release_eligible": False,
        "deployment_authority": "none",
        "checks": checks,
    }


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def main(argv: Sequence[str] | None = None) -> int:
    """Generate or verify a local-only benchmark evidence JSON document."""

    parser = argparse.ArgumentParser(
        prog="aureon-design-benchmark-evidence",
        description="Verify source-bound competitor metadata for Aureon's design feedback loop.",
    )
    parser.add_argument("--repo-root", type=Path, help="Aureon repository root.")
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG_PATH,
        help="Repository-relative WebsiteOperator configuration path.",
    )
    parser.add_argument("--verify", type=Path, help="Verify an existing JSON evidence file.")
    parser.add_argument(
        "--output",
        help="Repository-relative path to write a newly generated JSON evidence file.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.verify and args.output:
        parser.error("--verify and --output cannot be used together.")
    try:
        root = _find_repo_root(args.repo_root)
        if args.verify:
            evidence_path = args.verify.resolve()
            try:
                evidence_path.relative_to(root)
            except ValueError as exc:
                raise DesignBenchmarkEvidenceError(
                    "Evidence to verify must be inside the Aureon repository."
                ) from exc
            evidence = _read_json(evidence_path)
            verification = verify_design_benchmark_evidence(evidence, repo_root=root)
            payload: Mapping[str, Any] = {"evidence": evidence, "verification": verification}
        else:
            payload = discover_design_benchmark_evidence(root, config_path=args.config)
            verification = payload["verification"]
            if args.output:
                output_path = _safe_evidence_output_path(root, args.output)
                _atomic_write_json(output_path, payload)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0 if verification["passed"] else 2
    except DesignBenchmarkEvidenceError as exc:
        print(json.dumps({"state": "blocked", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
