"""Trusted, fail-closed editorial binary import into one staged candidate.

This control is deliberately narrower than the website design worker.  It
accepts only an already persisted, source-bound v4 design work order and
derives the complete image batch from that order's exact allow-list and the
current per-asset provenance audit.  Callers cannot provide source paths,
target paths, asset records, routes, hashes, or rights assertions.

The only binary read source is the content-addressed verified intake root.  The
only binary write targets are exact work-order-declared WebP paths below one
``artifacts/website-candidates/<run-id>/website`` tree.  The canonical
``website/`` tree, credentials, network, package, release, and deployment
surfaces are outside this module's authority.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from aureon.operator.design_candidate_control import (
    DEFAULT_CANDIDATE_ROOT,
    DesignCandidateControlError,
    verify_design_work_order,
)
from aureon.operator.design_editorial_asset_provenance import (
    DEFAULT_MANIFEST_PATH,
    GLOBAL_NOT_CLEARED_POLICY,
    DesignEditorialAssetProvenanceError,
    _audit_file_record,
    audit_design_editorial_asset_provenance_file,
)

IMPORT_RECEIPT_SCHEMA = "aureon.design-editorial-asset-candidate-import.v1"
IMPORT_VERIFICATION_SCHEMA = "aureon.design-editorial-asset-candidate-import-verification.v1"
EDITORIAL_WORK_ORDER_SCHEMA = "aureon.design-work-order.v4"
DEFAULT_VERIFIED_INTAKE_ROOT = Path("artifacts/website-operator/editorial-assets/verified")
DEFAULT_RECEIPT_NAME = "editorial-asset-import-receipt.v1.json"
MAX_IMPORT_FILES = 12
MAX_IMAGE_BYTES = 10 * 1024 * 1024

NON_AUTHORITATIVE_AUTHORITY = {
    "scope": "local trusted editorial binary import into one staged candidate",
    "canonical_website_mutation": "never",
    "candidate_write_scope": "exact work-order-declared image targets only",
    "binary_read_scope": "content-addressed verified editorial intake only",
    "transformations": "none",
    "release_eligible": False,
    "package_authority": "none",
    "deployment_authority": "none",
    "credential_access": "none",
    "network_access": "none",
    "connector_access": "none",
    "importer_receipt_required": True,
}

NEXT_GATE = (
    "candidate controller revalidates the complete staged diff, editorial import "
    "receipt, public claims, visual quality, accessibility and performance before "
    "any separate owner-gated release process"
)

_SHA256 = re.compile(r"^[A-F0-9]{64}$")
_RUN_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{2,80}$")
_ASSET_ID = re.compile(r"^[a-z0-9][a-z0-9-]{2,127}$")
_IMAGE_SUFFIXES = frozenset({".gif", ".ico", ".jpeg", ".jpg", ".png", ".svg", ".webp"})
BINARY_EXTENSIONS = frozenset({".gif", ".ico", ".jpeg", ".jpg", ".png", ".webp", ".woff", ".woff2"})
TRUSTED_IMPORT_EXTENSIONS = frozenset({".webp"})
_WORK_ORDER_FIELDS = frozenset(
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
        "test_policy",
        "candidate_layout",
        "editorial_asset_control",
        "authority",
    }
)
_BASELINE_FIELDS = frozenset({"tree_sha256", "file_count", "total_bytes", "files"})
_BASELINE_FILE_FIELDS = frozenset({"path", "sha256", "bytes"})
_CANDIDATE_LAYOUT_FIELDS = frozenset({"root", "website_path", "staged_claim_register_path"})
_EDITORIAL_ASSET_CONTROL_FIELDS = frozenset(
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
_RECEIPT_FIELDS = frozenset(
    {
        "schema",
        "imported_at",
        "state",
        "passed",
        "batch_complete",
        "receipt_authority",
        "release_eligible",
        "package_authority",
        "deployment_authority",
        "authority",
        "work_order",
        "provenance",
        "routes",
        "imports",
        "summary",
        "next_gate",
        "receipt_payload_sha256",
    }
)
_RECEIPT_WORK_ORDER_FIELDS = frozenset(
    {
        "run_id",
        "path",
        "file_sha256",
        "json_sha256",
        "baseline_tree_sha256",
        "candidate_copy_file_sha256",
    }
)
_RECEIPT_PROVENANCE_FIELDS = frozenset(
    {
        "manifest_id",
        "manifest_file_sha256",
        "asset_capsules_sha256",
        "selected_asset_capsules_sha256",
        "global_artwork_policy_state",
        "global_artwork_cleared_for_use",
        "candidate_ready_asset_ids",
    }
)
_RECEIPT_IMPORT_FIELDS = frozenset(
    {
        "asset_id",
        "role",
        "target",
        "sha256",
        "media_type",
        "bytes",
        "width",
        "height",
        "frame_count",
        "animation",
        "metadata_profile",
        "route_scopes",
        "destination_paths",
        "surface_ids",
        "asset_capsule_sha256",
        "rights_asset_scope_sha256",
    }
)
_RECEIPT_SUMMARY_FIELDS = frozenset(
    {
        "asset_count",
        "file_count",
        "total_bytes",
        "batch_complete",
        "imports_sha256",
    }
)


class DesignEditorialAssetCandidateImporterError(ValueError):
    """The requested editorial import is stale, unsafe, partial, or unbound."""


def _utc_iso(value: datetime | None = None) -> str:
    return (value or datetime.now(UTC)).astimezone(UTC).isoformat().replace("+00:00", "Z")


def _json_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _find_repo_root(start: Path | None = None) -> Path:
    candidate = (start or Path.cwd()).resolve()
    for root in (candidate, *candidate.parents):
        if (root / "pyproject.toml").is_file() and (root / "aureon").is_dir():
            return root
    raise DesignEditorialAssetCandidateImporterError(
        "Could not locate an Aureon repository with pyproject.toml and aureon/."
    )


def _component_has_reparse_point(path: Path) -> bool:
    try:
        info = os.lstat(path)
    except OSError:
        return False
    if stat.S_ISLNK(info.st_mode):
        return True
    attributes = getattr(info, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_flag)


def _lexical_absolute(path: Path) -> Path:
    """Return an absolute, normalised path without resolving reparse points."""

    return Path(os.path.abspath(os.fspath(path)))


def _relative_under(root: Path, candidate: Path, *, label: str) -> str:
    lexical_root = _lexical_absolute(root)
    lexical_candidate = _lexical_absolute(candidate)
    try:
        return lexical_candidate.relative_to(lexical_root).as_posix()
    except ValueError as exc:
        raise DesignEditorialAssetCandidateImporterError(f"{label} escapes its controlled root.") from exc


def _safe_relative_path(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise DesignEditorialAssetCandidateImporterError(f"{label} must be a non-empty relative path.")
    candidate = Path(value.replace("\\", "/"))
    if (
        candidate.is_absolute()
        or candidate.drive
        or candidate.root
        or not candidate.parts
        or any(part in {"", ".", ".."} for part in candidate.parts)
    ):
        raise DesignEditorialAssetCandidateImporterError(f"{label} is unsafe.")
    return candidate.as_posix()


def _assert_components_reparse_free(
    root: Path,
    candidate: Path,
    *,
    label: str,
) -> None:
    relative = _relative_under(root, candidate, label=label)
    current = _lexical_absolute(root)
    if _component_has_reparse_point(current):
        raise DesignEditorialAssetCandidateImporterError(f"{label} crosses a symlink or reparse point.")
    for part in Path(relative).parts:
        current = current / part
        if (current.exists() or current.is_symlink()) and _component_has_reparse_point(current):
            raise DesignEditorialAssetCandidateImporterError(f"{label} crosses a symlink or reparse point.")


def _require_safe_directory(root: Path, path: Path, *, label: str) -> None:
    _assert_components_reparse_free(root, path, label=label)
    if not path.is_dir():
        raise DesignEditorialAssetCandidateImporterError(f"{label} must be an existing directory.")


def _require_safe_file(
    root: Path,
    path: Path,
    *,
    label: str,
    max_bytes: int,
) -> None:
    _assert_components_reparse_free(root, path, label=label)
    try:
        file_stat = path.stat()
    except OSError as exc:
        raise DesignEditorialAssetCandidateImporterError(
            f"{label} must be an existing regular file."
        ) from exc
    if not path.is_file() or int(file_stat.st_nlink) != 1 or not 0 < int(file_stat.st_size) <= max_bytes:
        raise DesignEditorialAssetCandidateImporterError(
            f"{label} must be a non-empty, single-link, reparse-free regular file."
        )


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DesignEditorialAssetCandidateImporterError(f"{label} must be valid UTF-8 JSON.") from exc
    if not isinstance(value, Mapping):
        raise DesignEditorialAssetCandidateImporterError(f"{label} must contain one JSON object.")
    return dict(value)


def _exact_fields(
    value: object,
    fields: frozenset[str],
    *,
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise DesignEditorialAssetCandidateImporterError(f"{label} must be an object.")
    copied = dict(value)
    if set(copied) != fields:
        missing = sorted(fields - set(copied))
        extra = sorted(set(copied) - fields)
        raise DesignEditorialAssetCandidateImporterError(
            f"{label} fields do not match the exact contract (missing={missing}, extra={extra})."
        )
    return copied


def _persisted_work_order_path(root: Path, value: Path) -> Path:
    if not isinstance(value, Path):
        raise DesignEditorialAssetCandidateImporterError(
            "Editorial import requires a persisted design work-order JSON path."
        )
    candidate = value if value.is_absolute() else root / value
    candidate = _lexical_absolute(candidate)
    allowed = _lexical_absolute(root / DEFAULT_CANDIDATE_ROOT / "work-orders")
    relative = _relative_under(allowed, candidate, label="Design work order")
    if not Path(relative).parts or candidate.suffix.casefold() != ".json":
        raise DesignEditorialAssetCandidateImporterError(
            "Design work order must be a JSON artifact below artifacts/website-candidates/work-orders/."
        )
    _require_safe_file(
        root,
        candidate,
        label="Persisted design work order",
        max_bytes=4 * 1024 * 1024,
    )
    return candidate


def _baseline_summary(value: object) -> dict[str, Any]:
    baseline = _exact_fields(value, _BASELINE_FIELDS, label="Work-order baseline")
    raw_files = baseline.get("files")
    if not isinstance(raw_files, Sequence) or isinstance(raw_files, (str, bytes)):
        raise DesignEditorialAssetCandidateImporterError("Work-order baseline files must be an array.")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_files:
        row = _exact_fields(
            raw,
            _BASELINE_FILE_FIELDS,
            label="Work-order baseline file",
        )
        path = _safe_relative_path(row.get("path"), label="Baseline file path")
        sha256 = row.get("sha256")
        byte_count = row.get("bytes")
        if not isinstance(sha256, str) or not _SHA256.fullmatch(sha256):
            raise DesignEditorialAssetCandidateImporterError(f"Baseline file hash is invalid for {path}.")
        if isinstance(byte_count, bool) or not isinstance(byte_count, int) or byte_count < 0:
            raise DesignEditorialAssetCandidateImporterError(f"Baseline byte count is invalid for {path}.")
        if path in seen:
            raise DesignEditorialAssetCandidateImporterError(f"Baseline path is duplicated: {path}.")
        seen.add(path)
        rows.append({"path": path, "sha256": sha256, "bytes": byte_count})
    rows.sort(key=lambda item: str(item["path"]))
    computed = {
        "tree_sha256": _json_sha256(rows),
        "file_count": len(rows),
        "total_bytes": sum(int(item["bytes"]) for item in rows),
        "files": rows,
    }
    if dict(baseline) != computed:
        raise DesignEditorialAssetCandidateImporterError(
            "Work-order baseline is not a complete canonical tree binding."
        )
    return computed


def _tree_summary(root: Path) -> dict[str, Any]:
    _require_safe_directory(root, root, label="Candidate website")
    rows: list[dict[str, Any]] = []
    for directory_name, directory_names, file_names in os.walk(
        root,
        topdown=True,
        followlinks=False,
    ):
        directory = Path(directory_name)
        _assert_components_reparse_free(root, directory, label="Candidate website directory")
        directory_names.sort()
        file_names.sort()
        for name in directory_names:
            child = directory / name
            if _component_has_reparse_point(child):
                raise DesignEditorialAssetCandidateImporterError(
                    "Candidate website contains a symlink or reparse directory."
                )
        for name in file_names:
            path = directory / name
            _require_safe_file(
                root,
                path,
                label="Candidate website file",
                max_bytes=MAX_IMAGE_BYTES * 20,
            )
            rows.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "sha256": _sha256_file(path),
                    "bytes": path.stat().st_size,
                }
            )
    rows.sort(key=lambda item: str(item["path"]))
    return {
        "tree_sha256": _json_sha256(rows),
        "file_count": len(rows),
        "total_bytes": sum(int(item["bytes"]) for item in rows),
        "files": rows,
    }


def _website_relative(value: object, *, label: str) -> str:
    path = _safe_relative_path(value, label=label)
    parts = Path(path).parts
    if len(parts) < 2 or parts[0] != "website":
        raise DesignEditorialAssetCandidateImporterError(f"{label} must be an exact path below website/.")
    return Path(*parts[1:]).as_posix()


def _safe_routes(value: object) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise DesignEditorialAssetCandidateImporterError(
            "Editorial import work order must declare at least one route."
        )
    routes: list[str] = []
    for raw in value:
        if (
            not isinstance(raw, str)
            or not raw.startswith("/")
            or "//" in raw
            or "?" in raw
            or "#" in raw
            or ".." in Path(raw).parts
        ):
            raise DesignEditorialAssetCandidateImporterError(
                "Editorial import routes must be canonical local paths."
            )
        routes.append(raw)
    if len(routes) != len(set(routes)):
        raise DesignEditorialAssetCandidateImporterError("Editorial import routes must be unique.")
    return sorted(routes)


def _safe_allowed_paths(value: object) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise DesignEditorialAssetCandidateImporterError(
            "Editorial import work order has no exact allowed paths."
        )
    paths = [_safe_relative_path(item, label="Work-order allowed path") for item in value]
    if len(paths) != len(set(paths)) or len(paths) > MAX_IMPORT_FILES:
        raise DesignEditorialAssetCandidateImporterError(
            "Work-order allowed paths must be unique and remain within the bounded batch limit."
        )
    return sorted(paths)


def editorial_asset_control_binding(
    run_id: str,
    *,
    allowed_paths: Sequence[str],
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Return the exact v4 binary-import policy for one candidate run."""

    if not _RUN_ID.fullmatch(run_id):
        raise DesignEditorialAssetCandidateImporterError(
            "Editorial asset control run id is not a safe candidate slug."
        )
    root = _find_repo_root(repo_root)
    safe_paths = _safe_allowed_paths(allowed_paths)
    binary_paths = [path for path in safe_paths if Path(path).suffix.casefold() in BINARY_EXTENSIONS]
    provenance_manifest_path = ""
    provenance_manifest_sha256 = ""
    if binary_paths:
        manifest_path = _lexical_absolute(root / DEFAULT_MANIFEST_PATH)
        _require_safe_file(
            root,
            manifest_path,
            label="Canonical editorial provenance manifest",
            max_bytes=4 * 1024 * 1024,
        )
        provenance_manifest_path = _relative_under(
            root,
            manifest_path,
            label="Canonical editorial provenance manifest",
        )
        provenance_manifest_sha256 = _sha256_file(manifest_path)
    return {
        "policy": "every-binary-diff-requires-trusted-editorial-import-receipt",
        "receipt_path": (DEFAULT_CANDIDATE_ROOT / run_id / DEFAULT_RECEIPT_NAME).as_posix(),
        "receipt_schema": IMPORT_RECEIPT_SCHEMA,
        "verification_schema": IMPORT_VERIFICATION_SCHEMA,
        "binary_extensions": sorted(BINARY_EXTENSIONS),
        "trusted_import_extensions": sorted(TRUSTED_IMPORT_EXTENSIONS),
        "unreceipted_binary_diff": "prohibited",
        "replay_verification_required": True,
        "provenance_manifest_path": provenance_manifest_path,
        "provenance_manifest_sha256": provenance_manifest_sha256,
        "surface_binding_verification_required": bool(binary_paths),
    }


def _normalise_work_order(
    work_order: Mapping[str, Any],
    *,
    root: Path,
) -> tuple[dict[str, Any], dict[str, Any], Path, Path]:
    order = _exact_fields(
        work_order,
        _WORK_ORDER_FIELDS,
        label="Persisted design work order",
    )
    if order.get("schema") != EDITORIAL_WORK_ORDER_SCHEMA:
        raise DesignEditorialAssetCandidateImporterError(
            f"Editorial import requires the current {EDITORIAL_WORK_ORDER_SCHEMA} contract."
        )
    run_id = order.get("run_id")
    if not isinstance(run_id, str) or not _RUN_ID.fullmatch(run_id):
        raise DesignEditorialAssetCandidateImporterError(
            "Work-order run id is not a safe stable candidate slug."
        )
    allowed_paths = _safe_allowed_paths(order.get("allowed_paths"))
    editorial_control = _exact_fields(
        order.get("editorial_asset_control"),
        _EDITORIAL_ASSET_CONTROL_FIELDS,
        label="Work-order editorial asset control",
    )
    if editorial_control != editorial_asset_control_binding(
        run_id,
        allowed_paths=allowed_paths,
        repo_root=root,
    ):
        raise DesignEditorialAssetCandidateImporterError(
            "Work-order editorial asset control does not match the exact v4 "
            "receipt, replay, and provenance-surface binding."
        )
    baseline = _baseline_summary(order.get("baseline"))
    _safe_routes(order.get("routes"))

    layout = _exact_fields(
        order.get("candidate_layout"),
        _CANDIDATE_LAYOUT_FIELDS,
        label="Candidate layout",
    )
    expected_root = (DEFAULT_CANDIDATE_ROOT / run_id).as_posix()
    expected_site = (DEFAULT_CANDIDATE_ROOT / run_id / "website").as_posix()
    if layout.get("root") != expected_root or layout.get("website_path") != expected_site:
        raise DesignEditorialAssetCandidateImporterError(
            "Work-order candidate layout does not match its exact run id."
        )
    candidate_root = _lexical_absolute(root / expected_root)
    candidate_site = _lexical_absolute(root / expected_site)
    _require_safe_directory(root, candidate_root, label="Candidate root")
    _require_safe_directory(candidate_root, candidate_site, label="Candidate website")
    return order, baseline, candidate_root, candidate_site


def _verification_failures(verification: Mapping[str, Any]) -> list[str]:
    raw_checks = verification.get("checks")
    if not isinstance(raw_checks, Sequence) or isinstance(raw_checks, (str, bytes)):
        return ["malformed-verification"]
    return sorted(
        {
            str(check.get("id") or "unknown")
            for check in raw_checks
            if isinstance(check, Mapping) and check.get("passed") is not True
        }
    )


def _candidate_ready_batch(
    *,
    audit: Mapping[str, Any],
    allowed_paths: Sequence[str],
    routes: Sequence[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    raw_assets = audit.get("assets")
    raw_capsules = audit.get("asset_capsules")
    if (
        not isinstance(raw_assets, Sequence)
        or isinstance(raw_assets, (str, bytes))
        or not isinstance(raw_capsules, Sequence)
        or isinstance(raw_capsules, (str, bytes))
    ):
        raise DesignEditorialAssetCandidateImporterError(
            "Editorial provenance audit did not emit the controlled asset records."
        )

    audit_by_id = {
        str(item.get("asset_id")): item
        for item in raw_assets
        if isinstance(item, Mapping) and isinstance(item.get("asset_id"), str)
    }
    capsule_by_id = {
        str(item.get("asset_id")): item
        for item in raw_capsules
        if isinstance(item, Mapping) and isinstance(item.get("asset_id"), str)
    }
    variant_owners: dict[str, list[tuple[str, Mapping[str, Any]]]] = {}
    for asset_id, audit_asset in audit_by_id.items():
        raw_variants = audit_asset.get("variants")
        if not isinstance(raw_variants, Sequence) or isinstance(raw_variants, (str, bytes)):
            continue
        for variant in raw_variants:
            if not isinstance(variant, Mapping):
                continue
            target = _website_relative(
                variant.get("path"),
                label="Provenance variant target",
            )
            variant_owners.setdefault(target, []).append((asset_id, variant))

    image_paths = sorted(path for path in allowed_paths if Path(path).suffix.casefold() in _IMAGE_SUFFIXES)
    if not image_paths:
        raise DesignEditorialAssetCandidateImporterError("Work order declares no editorial image target.")
    if any(Path(path).suffix.casefold() != ".webp" for path in image_paths):
        raise DesignEditorialAssetCandidateImporterError(
            "Editorial importer accepts only exact provenance-bound WebP targets."
        )

    selected_ids: set[str] = set()
    selected_variants: dict[str, Mapping[str, Any]] = {}
    for target in image_paths:
        owners = variant_owners.get(target, [])
        if len(owners) != 1:
            raise DesignEditorialAssetCandidateImporterError(
                f"Image target is not uniquely bound by editorial provenance: {target}."
            )
        asset_id, variant = owners[0]
        audit_asset = audit_by_id[asset_id]
        if audit_asset.get("candidate_use_ready") is not True or asset_id not in capsule_by_id:
            raise DesignEditorialAssetCandidateImporterError(
                f"Editorial asset is not candidate-use-ready: {asset_id}."
            )
        if variant.get("integrity_matches") is not True:
            raise DesignEditorialAssetCandidateImporterError(
                f"Editorial provenance integrity is not closed for: {asset_id}."
            )
        selected_ids.add(asset_id)
        selected_variants[target] = variant

    allowed_set = set(allowed_paths)
    route_set = set(routes)
    route_coverage: set[str] = set()
    import_rows: list[dict[str, Any]] = []
    selected_capsules: list[dict[str, Any]] = []
    for asset_id in sorted(selected_ids):
        raw_capsule = capsule_by_id[asset_id]
        capsule = dict(raw_capsule)
        raw_website_variants = capsule.get("website_variants")
        raw_placements = capsule.get("placements")
        if (
            not isinstance(raw_website_variants, Sequence)
            or isinstance(raw_website_variants, (str, bytes))
            or not isinstance(raw_placements, Sequence)
            or isinstance(raw_placements, (str, bytes))
        ):
            raise DesignEditorialAssetCandidateImporterError(
                f"Candidate-ready capsule is malformed: {asset_id}."
            )
        expected_targets = {
            _website_relative(item.get("path"), label="Capsule variant target")
            for item in raw_website_variants
            if isinstance(item, Mapping)
        }
        if not expected_targets or not expected_targets.issubset(set(image_paths)):
            raise DesignEditorialAssetCandidateImporterError(
                f"Partial editorial asset batch is prohibited: {asset_id}."
            )

        selected_placements: list[Mapping[str, Any]] = []
        for placement in raw_placements:
            if not isinstance(placement, Mapping):
                raise DesignEditorialAssetCandidateImporterError(
                    f"Candidate-ready placement is malformed: {asset_id}."
                )
            route = placement.get("route_scope")
            if route not in route_set:
                continue
            destination = _website_relative(
                placement.get("destination_path"),
                label="Placement destination",
            )
            if destination not in allowed_set:
                raise DesignEditorialAssetCandidateImporterError(
                    f"Route placement destination is not declared by the work order: "
                    f"{asset_id}:{route}:{destination}."
                )
            selected_placements.append(placement)
            route_coverage.add(str(route))
        if not selected_placements:
            raise DesignEditorialAssetCandidateImporterError(
                f"Editorial asset has no placement on a work-order route: {asset_id}."
            )

        selected_roles: set[str] = set()
        for placement in selected_placements:
            raw_roles = placement.get("variant_roles")
            if not isinstance(raw_roles, Sequence) or isinstance(raw_roles, (str, bytes)):
                raise DesignEditorialAssetCandidateImporterError(
                    f"Candidate-ready placement roles are malformed: {asset_id}."
                )
            selected_roles.update(str(role) for role in raw_roles)
        capsule_roles = {str(item.get("role")) for item in raw_website_variants if isinstance(item, Mapping)}
        if selected_roles != capsule_roles:
            raise DesignEditorialAssetCandidateImporterError(
                f"Route/variant role binding is incomplete for: {asset_id}."
            )

        asset_capsule_sha256 = capsule.get("asset_capsule_sha256")
        rights = capsule.get("rights")
        if (
            not isinstance(asset_capsule_sha256, str)
            or not _SHA256.fullmatch(asset_capsule_sha256)
            or not isinstance(rights, Mapping)
            or not isinstance(rights.get("asset_scope_sha256"), str)
            or not _SHA256.fullmatch(str(rights.get("asset_scope_sha256")))
        ):
            raise DesignEditorialAssetCandidateImporterError(
                f"Candidate-ready capsule lost its exact rights binding: {asset_id}."
            )

        route_scopes = sorted({str(item["route_scope"]) for item in selected_placements})
        destinations = sorted(
            {
                _website_relative(
                    item["destination_path"],
                    label="Placement destination",
                )
                for item in selected_placements
            }
        )
        surface_ids = sorted({str(item["surface_id"]) for item in selected_placements})
        for target in sorted(expected_targets):
            variant = selected_variants[target]
            role = variant.get("role")
            if (
                not isinstance(role, str)
                or role not in {"small", "large"}
                or not isinstance(variant.get("sha256"), str)
                or not _SHA256.fullmatch(str(variant.get("sha256")))
            ):
                raise DesignEditorialAssetCandidateImporterError(
                    f"Editorial variant binding is malformed: {asset_id}:{target}."
                )
            import_rows.append(
                {
                    "asset_id": asset_id,
                    "role": role,
                    "target_relative": target,
                    "sha256": str(variant["sha256"]),
                    "media_type": str(variant["media_type"]),
                    "bytes": int(variant["bytes"]),
                    "width": int(variant["width"]),
                    "height": int(variant["height"]),
                    "frame_count": int(variant["frame_count"]),
                    "animation": str(variant["animation"]),
                    "metadata_profile": str(variant["metadata_profile"]),
                    "metadata_sha256": str(variant["metadata_sha256"]),
                    "route_scopes": route_scopes,
                    "destination_paths": destinations,
                    "surface_ids": surface_ids,
                    "asset_capsule_sha256": asset_capsule_sha256,
                    "rights_asset_scope_sha256": str(rights["asset_scope_sha256"]),
                }
            )
        selected_capsules.append(capsule)

    if route_coverage != route_set:
        missing = sorted(route_set - route_coverage)
        raise DesignEditorialAssetCandidateImporterError(
            f"Work-order routes are not exactly covered by the selected editorial assets: {missing}."
        )
    if {str(item["target_relative"]) for item in import_rows} != set(image_paths):
        raise DesignEditorialAssetCandidateImporterError(
            "Editorial image batch does not exactly cover every declared image target."
        )
    if not 0 < len(import_rows) <= MAX_IMPORT_FILES:
        raise DesignEditorialAssetCandidateImporterError(
            "Editorial image batch is empty or exceeds the bounded import limit."
        )
    import_rows.sort(
        key=lambda item: (
            str(item["asset_id"]),
            str(item["role"]),
            str(item["target_relative"]),
        )
    )
    selected_capsules.sort(key=lambda item: str(item["asset_id"]))
    return import_rows, selected_capsules


def _intake_path(root: Path, sha256: str) -> Path:
    if not _SHA256.fullmatch(sha256):
        raise DesignEditorialAssetCandidateImporterError(
            "Verified intake lookup requires an uppercase SHA-256."
        )
    intake_root = _lexical_absolute(root / DEFAULT_VERIFIED_INTAKE_ROOT)
    _require_safe_directory(root, intake_root, label="Verified editorial intake root")
    candidate = intake_root / f"{sha256}.webp"
    _require_safe_file(
        root,
        candidate,
        label="Verified editorial intake image",
        max_bytes=MAX_IMAGE_BYTES,
    )
    return candidate


def _record_for_path(row: Mapping[str, Any], path: Path, root: Path) -> dict[str, Any]:
    return {
        "path": _relative_under(root, path, label="Audited editorial binary"),
        "sha256": row["sha256"],
        "media_type": row["media_type"],
        "bytes": row["bytes"],
        "width": row["width"],
        "height": row["height"],
        "frame_count": row["frame_count"],
        "animation": row["animation"],
        "metadata_profile": row["metadata_profile"],
        "metadata_sha256": row["metadata_sha256"],
    }


def _assert_image_integrity(
    *,
    root: Path,
    row: Mapping[str, Any],
    path: Path,
    label: str,
) -> None:
    _require_safe_file(
        root,
        path,
        label=label,
        max_bytes=MAX_IMAGE_BYTES,
    )
    audit = _audit_file_record(root, _record_for_path(row, path, root))
    if audit.get("integrity_matches") is not True:
        failed = sorted(
            key
            for key in (
                "hash_matches",
                "magic_mime_matches",
                "dimensions_match",
                "static_single_frame",
                "metadata_matches",
            )
            if audit.get(key) is not True
        )
        raise DesignEditorialAssetCandidateImporterError(
            f"{label} drifted from the exact approved image record: {failed}."
        )


def _receipt_import_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    root: Path,
    candidate_site: Path,
) -> list[dict[str, Any]]:
    public_rows: list[dict[str, Any]] = []
    for row in rows:
        target = candidate_site / str(row["target_relative"])
        public_rows.append(
            {
                "asset_id": row["asset_id"],
                "role": row["role"],
                "target": _relative_under(root, target, label="Candidate image target"),
                "sha256": row["sha256"],
                "media_type": row["media_type"],
                "bytes": row["bytes"],
                "width": row["width"],
                "height": row["height"],
                "frame_count": row["frame_count"],
                "animation": row["animation"],
                "metadata_profile": row["metadata_profile"],
                "route_scopes": list(row["route_scopes"]),
                "destination_paths": list(row["destination_paths"]),
                "surface_ids": list(row["surface_ids"]),
                "asset_capsule_sha256": row["asset_capsule_sha256"],
                "rights_asset_scope_sha256": row["rights_asset_scope_sha256"],
            }
        )
    return public_rows


def _remove_stage(candidate_root: Path, stage: Path) -> None:
    relative = _relative_under(candidate_root, stage, label="Importer staging directory")
    if len(Path(relative).parts) != 1 or not Path(relative).name.startswith(".editorial-import-"):
        raise DesignEditorialAssetCandidateImporterError(
            "Refusing to remove an unexpected importer staging path."
        )
    if stage.exists():
        shutil.rmtree(stage)


def _parse_utc_datetime(value: object, *, label: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise DesignEditorialAssetCandidateImporterError(
            f"{label} must be a UTC ISO-8601 timestamp ending in Z."
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise DesignEditorialAssetCandidateImporterError(
            f"{label} must be a valid UTC ISO-8601 timestamp."
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise DesignEditorialAssetCandidateImporterError(f"{label} must use UTC.")
    return parsed


def _fixed_receipt_path(root: Path, run_id: str) -> tuple[Path, Path, Path]:
    if not _RUN_ID.fullmatch(run_id):
        raise DesignEditorialAssetCandidateImporterError(
            "Editorial import receipt run id is not a safe candidate slug."
        )
    candidate_root = _lexical_absolute(root / DEFAULT_CANDIDATE_ROOT / run_id)
    candidate_site = candidate_root / "website"
    _require_safe_directory(root, candidate_root, label="Candidate root")
    _require_safe_directory(candidate_root, candidate_site, label="Candidate website")
    receipt_path = candidate_root / DEFAULT_RECEIPT_NAME
    _assert_components_reparse_free(
        candidate_root,
        receipt_path,
        label="Editorial import receipt",
    )
    return candidate_root, candidate_site, receipt_path


def _binary_projection(
    raw_rows: object,
    *,
    label: str,
) -> dict[str, Any]:
    if not isinstance(raw_rows, Sequence) or isinstance(raw_rows, (str, bytes)):
        raise DesignEditorialAssetCandidateImporterError(f"{label} files must be an array.")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_rows:
        if not isinstance(raw, Mapping):
            raise DesignEditorialAssetCandidateImporterError(f"{label} file rows must be objects.")
        path = _safe_relative_path(raw.get("path"), label=f"{label} file path")
        if Path(path).suffix.casefold() not in BINARY_EXTENSIONS:
            continue
        sha256 = raw.get("sha256")
        byte_count = raw.get("bytes")
        if not isinstance(sha256, str) or not _SHA256.fullmatch(sha256):
            raise DesignEditorialAssetCandidateImporterError(f"{label} binary hash is invalid for {path}.")
        if isinstance(byte_count, bool) or not isinstance(byte_count, int) or byte_count < 0:
            raise DesignEditorialAssetCandidateImporterError(
                f"{label} binary byte count is invalid for {path}."
            )
        if path in seen:
            raise DesignEditorialAssetCandidateImporterError(f"{label} binary path is duplicated: {path}.")
        seen.add(path)
        rows.append({"path": path, "sha256": sha256, "bytes": byte_count})
    rows.sort(key=lambda item: str(item["path"]))
    return {
        "tree_sha256": _json_sha256(rows),
        "file_count": len(rows),
        "total_bytes": sum(int(item["bytes"]) for item in rows),
        "files": rows,
    }


def _expected_post_import_binary_projection(
    baseline: Mapping[str, Any],
    imports: Sequence[Mapping[str, Any]],
    *,
    candidate_site_relative: str,
) -> dict[str, Any]:
    rows_by_path: dict[str, dict[str, Any]] = {
        str(item["path"]): {
            "path": str(item["path"]),
            "sha256": str(item["sha256"]),
            "bytes": int(item["bytes"]),
        }
        for item in baseline["files"]
        if isinstance(item, Mapping) and Path(str(item["path"])).suffix.casefold() in BINARY_EXTENSIONS
    }
    prefix = candidate_site_relative.rstrip("/") + "/"
    for row in imports:
        target = str(row["target"])
        if not target.startswith(prefix):
            raise DesignEditorialAssetCandidateImporterError(
                "Editorial import target does not belong to its exact candidate website."
            )
        target_relative = _safe_relative_path(
            target[len(prefix) :],
            label="Receipt candidate image target",
        )
        if Path(target_relative).suffix.casefold() != ".webp":
            raise DesignEditorialAssetCandidateImporterError(
                "Editorial import receipt may bind only exact WebP targets."
            )
        rows_by_path[target_relative] = {
            "path": target_relative,
            "sha256": str(row["sha256"]),
            "bytes": int(row["bytes"]),
        }
    rows = sorted(rows_by_path.values(), key=lambda item: str(item["path"]))
    return _binary_projection(rows, label="Expected candidate")


def _verify_candidate_editorial_asset_import(
    receipt: Mapping[str, Any],
    *,
    root: Path,
    manifest_path: Path | None,
    as_of: datetime | None,
    require_persisted_receipt: bool,
    require_current_baseline: bool,
    verified_at: datetime | None,
) -> dict[str, Any]:
    controlled = _exact_fields(
        receipt,
        _RECEIPT_FIELDS,
        label="Editorial asset import receipt",
    )
    _parse_utc_datetime(controlled.get("imported_at"), label="Editorial asset import time")
    if (
        controlled.get("schema") != IMPORT_RECEIPT_SCHEMA
        or controlled.get("state") != "imported-local-candidate"
        or controlled.get("passed") is not True
        or controlled.get("batch_complete") is not True
        or controlled.get("receipt_authority") is not False
        or controlled.get("release_eligible") is not False
        or controlled.get("package_authority") != "none"
        or controlled.get("deployment_authority") != "none"
        or controlled.get("authority") != NON_AUTHORITATIVE_AUTHORITY
        or controlled.get("next_gate") != NEXT_GATE
    ):
        raise DesignEditorialAssetCandidateImporterError(
            "Editorial asset import receipt changed its exact non-authoritative contract."
        )

    payload_hash = controlled.get("receipt_payload_sha256")
    payload = dict(controlled)
    payload.pop("receipt_payload_sha256")
    if (
        not isinstance(payload_hash, str)
        or not _SHA256.fullmatch(payload_hash)
        or _json_sha256(payload) != payload_hash
    ):
        raise DesignEditorialAssetCandidateImporterError(
            "Editorial asset import receipt payload hash does not match."
        )

    work_binding = _exact_fields(
        controlled.get("work_order"),
        _RECEIPT_WORK_ORDER_FIELDS,
        label="Editorial asset import work-order binding",
    )
    run_id = work_binding.get("run_id")
    if not isinstance(run_id, str) or not _RUN_ID.fullmatch(run_id):
        raise DesignEditorialAssetCandidateImporterError(
            "Editorial asset import work-order run id is invalid."
        )
    raw_work_order_path = work_binding.get("path")
    if not isinstance(raw_work_order_path, str):
        raise DesignEditorialAssetCandidateImporterError("Editorial asset import work-order path is invalid.")
    persisted_path = _persisted_work_order_path(root, Path(raw_work_order_path))
    order = _read_json_object(persisted_path, label="Persisted design work order")
    order, baseline, candidate_root, candidate_site = _normalise_work_order(
        order,
        root=root,
    )
    if order["run_id"] != run_id:
        raise DesignEditorialAssetCandidateImporterError(
            "Editorial asset import receipt changed its work-order run id."
        )
    expected_candidate_root, expected_candidate_site, receipt_path = _fixed_receipt_path(
        root,
        run_id,
    )
    if candidate_root != expected_candidate_root or candidate_site != expected_candidate_site:
        raise DesignEditorialAssetCandidateImporterError(
            "Editorial asset import receipt no longer matches its work-order candidate layout."
        )

    try:
        work_order_verification = verify_design_work_order(
            order,
            repo_root=root,
            require_current_baseline=require_current_baseline,
        )
    except DesignCandidateControlError as exc:
        raise DesignEditorialAssetCandidateImporterError(
            f"Editorial import work order failed current source-bound verification: {exc}"
        ) from exc
    if work_order_verification.get("passed") is not True:
        failed = _verification_failures(work_order_verification)
        raise DesignEditorialAssetCandidateImporterError(
            "Editorial import work order is no longer valid: " + ", ".join(failed)
        )

    candidate_order_path = candidate_root / "work-order.v4.json"
    _require_safe_file(
        candidate_root,
        candidate_order_path,
        label="Candidate work-order copy",
        max_bytes=4 * 1024 * 1024,
    )
    candidate_order = _read_json_object(
        candidate_order_path,
        label="Candidate work-order copy",
    )
    if candidate_order != order:
        raise DesignEditorialAssetCandidateImporterError(
            "Candidate work-order copy no longer matches the persisted source-bound order."
        )
    expected_work_binding = {
        "run_id": run_id,
        "path": _relative_under(
            root,
            persisted_path,
            label="Persisted design work order",
        ),
        "file_sha256": _sha256_file(persisted_path),
        "json_sha256": _json_sha256(order),
        "baseline_tree_sha256": baseline["tree_sha256"],
        "candidate_copy_file_sha256": _sha256_file(candidate_order_path),
    }
    if work_binding != expected_work_binding:
        raise DesignEditorialAssetCandidateImporterError("Editorial asset import work-order binding drifted.")

    try:
        provenance_audit = audit_design_editorial_asset_provenance_file(
            manifest_path or DEFAULT_MANIFEST_PATH,
            repo_root=root,
            as_of=as_of,
        )
    except DesignEditorialAssetProvenanceError as exc:
        raise DesignEditorialAssetCandidateImporterError(
            f"Editorial provenance no longer closes: {exc}"
        ) from exc
    allowed_paths = _safe_allowed_paths(order.get("allowed_paths"))
    routes = _safe_routes(order.get("routes"))
    import_rows, selected_capsules = _candidate_ready_batch(
        audit=provenance_audit,
        allowed_paths=allowed_paths,
        routes=routes,
    )
    public_imports = _receipt_import_rows(
        import_rows,
        root=root,
        candidate_site=candidate_site,
    )
    provenance_manifest = provenance_audit.get("manifest")
    if not isinstance(provenance_manifest, Mapping):
        raise DesignEditorialAssetCandidateImporterError(
            "Editorial provenance audit lost its manifest binding."
        )
    selected_asset_ids = sorted({str(item["asset_id"]) for item in public_imports})
    expected_provenance = {
        "manifest_id": provenance_manifest.get("manifest_id"),
        "manifest_file_sha256": provenance_manifest.get("sha256"),
        "asset_capsules_sha256": provenance_audit.get("asset_capsules_sha256"),
        "selected_asset_capsules_sha256": _json_sha256(selected_capsules),
        "global_artwork_policy_state": GLOBAL_NOT_CLEARED_POLICY["state"],
        "global_artwork_cleared_for_use": False,
        "candidate_ready_asset_ids": selected_asset_ids,
    }
    provenance_binding = _exact_fields(
        controlled.get("provenance"),
        _RECEIPT_PROVENANCE_FIELDS,
        label="Editorial asset import provenance binding",
    )
    if provenance_binding != expected_provenance:
        raise DesignEditorialAssetCandidateImporterError(
            "Editorial asset import provenance or rights binding drifted."
        )

    raw_routes = controlled.get("routes")
    if raw_routes != routes:
        raise DesignEditorialAssetCandidateImporterError("Editorial asset import route binding drifted.")
    raw_imports = controlled.get("imports")
    if (
        not isinstance(raw_imports, Sequence)
        or isinstance(raw_imports, (str, bytes))
        or not raw_imports
        or len(raw_imports) > MAX_IMPORT_FILES
    ):
        raise DesignEditorialAssetCandidateImporterError(
            "Editorial asset import receipt has an invalid bounded import batch."
        )
    receipt_imports = [
        _exact_fields(
            item,
            _RECEIPT_IMPORT_FIELDS,
            label="Editorial asset import row",
        )
        for item in raw_imports
    ]
    if receipt_imports != public_imports:
        raise DesignEditorialAssetCandidateImporterError(
            "Editorial asset import rows drifted from current provenance and work-order scope."
        )

    expected_summary = {
        "asset_count": len(selected_asset_ids),
        "file_count": len(public_imports),
        "total_bytes": sum(int(item["bytes"]) for item in public_imports),
        "batch_complete": True,
        "imports_sha256": _json_sha256(public_imports),
    }
    summary = _exact_fields(
        controlled.get("summary"),
        _RECEIPT_SUMMARY_FIELDS,
        label="Editorial asset import summary",
    )
    if summary != expected_summary:
        raise DesignEditorialAssetCandidateImporterError("Editorial asset import summary drifted.")

    candidate_site_relative = _relative_under(
        root,
        candidate_site,
        label="Candidate website",
    )
    expected_binary_projection = _expected_post_import_binary_projection(
        baseline,
        public_imports,
        candidate_site_relative=candidate_site_relative,
    )
    observed_tree = _tree_summary(candidate_site)
    observed_binary_projection = _binary_projection(
        observed_tree.get("files"),
        label="Observed candidate",
    )
    if observed_binary_projection != expected_binary_projection:
        raise DesignEditorialAssetCandidateImporterError(
            "Candidate binary projection no longer equals the source-bound "
            "baseline plus the exact receipted editorial import batch."
        )
    for row in import_rows:
        target = candidate_site / str(row["target_relative"])
        _assert_image_integrity(
            root=root,
            row=row,
            path=target,
            label="Imported candidate editorial image",
        )

    receipt_file_sha256 = ""
    if require_persisted_receipt:
        _require_safe_file(
            candidate_root,
            receipt_path,
            label="Editorial import receipt",
            max_bytes=4 * 1024 * 1024,
        )
        persisted_receipt = _read_json_object(
            receipt_path,
            label="Editorial import receipt",
        )
        if persisted_receipt != controlled:
            raise DesignEditorialAssetCandidateImporterError(
                "Persisted editorial import receipt no longer matches the supplied receipt."
            )
        receipt_file_sha256 = _sha256_file(receipt_path)

    return {
        "schema": IMPORT_VERIFICATION_SCHEMA,
        "verified_at": _utc_iso(verified_at),
        "state": "verified-local-candidate",
        "passed": True,
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "authority": dict(NON_AUTHORITATIVE_AUTHORITY),
        "receipt": {
            "path": _relative_under(
                root,
                receipt_path,
                label="Editorial import receipt",
            ),
            "payload_sha256": payload_hash,
            "file_sha256": receipt_file_sha256,
            "persisted": require_persisted_receipt,
        },
        "work_order": expected_work_binding,
        "summary": expected_summary,
        "next_gate": NEXT_GATE,
    }


def verify_candidate_editorial_asset_import(
    receipt: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
    manifest_path: Path | None = None,
    as_of: datetime | None = None,
    verified_at: datetime | None = None,
    _require_current_baseline: bool = True,
) -> dict[str, Any]:
    """Revalidate the persisted receipt, exact binaries, work order and rights."""

    root = _find_repo_root(repo_root)
    return _verify_candidate_editorial_asset_import(
        receipt,
        root=root,
        manifest_path=manifest_path,
        as_of=as_of,
        require_persisted_receipt=True,
        require_current_baseline=_require_current_baseline,
        verified_at=verified_at,
    )


def write_candidate_editorial_asset_import(
    receipt: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
    manifest_path: Path | None = None,
    as_of: datetime | None = None,
) -> Path:
    """Write one verified receipt to its fixed candidate-local path once."""

    root = _find_repo_root(repo_root)
    verification = _verify_candidate_editorial_asset_import(
        receipt,
        root=root,
        manifest_path=manifest_path,
        as_of=as_of,
        require_persisted_receipt=False,
        require_current_baseline=True,
        verified_at=None,
    )
    work_binding = verification["work_order"]
    run_id = str(work_binding["run_id"])
    candidate_root, _candidate_site, receipt_path = _fixed_receipt_path(root, run_id)
    if receipt_path.exists() or receipt_path.is_symlink():
        raise DesignEditorialAssetCandidateImporterError(
            "Editorial import receipt is immutable and already exists for this candidate."
        )

    encoded = json.dumps(dict(receipt), ensure_ascii=False, indent=2) + "\n"
    descriptor: int | None = None
    created = False
    try:
        descriptor = os.open(
            receipt_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        created = True
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            descriptor = None
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        _require_safe_file(
            candidate_root,
            receipt_path,
            label="Editorial import receipt",
            max_bytes=4 * 1024 * 1024,
        )
        readback = _read_json_object(
            receipt_path,
            label="Editorial import receipt",
        )
        if readback != dict(receipt):
            raise DesignEditorialAssetCandidateImporterError(
                "Editorial import receipt failed immutable read-back."
            )
        return receipt_path
    except FileExistsError as exc:
        raise DesignEditorialAssetCandidateImporterError(
            "Editorial import receipt is immutable and already exists for this candidate."
        ) from exc
    except Exception:
        if descriptor is not None:
            os.close(descriptor)
        if created and receipt_path.exists():
            receipt_path.unlink()
        raise


def import_editorial_assets_to_candidate(
    work_order_path: Path,
    *,
    repo_root: Path | None = None,
    manifest_path: Path | None = None,
    as_of: datetime | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Import one complete approved editorial batch into one staged candidate.

    The work order must already exist below
    ``artifacts/website-candidates/work-orders/`` and its candidate must already
    have been staged by the existing candidate controller.  No mapping object is
    accepted so a caller cannot bypass the work order or provenance controls.
    """

    root = _find_repo_root(repo_root)
    persisted_path = _persisted_work_order_path(root, work_order_path)
    persisted_sha256 = _sha256_file(persisted_path)
    work_order = _read_json_object(persisted_path, label="Persisted design work order")
    order, baseline, candidate_root, candidate_site = _normalise_work_order(
        work_order,
        root=root,
    )

    try:
        verification = verify_design_work_order(order, repo_root=root)
    except DesignCandidateControlError as exc:
        raise DesignEditorialAssetCandidateImporterError(
            f"Persisted design work order failed source-bound verification: {exc}"
        ) from exc
    if verification.get("passed") is not True:
        failed = _verification_failures(verification)
        raise DesignEditorialAssetCandidateImporterError(
            "Persisted design work order is invalid or stale: " + ", ".join(failed)
        )

    candidate_order_path = candidate_root / "work-order.v4.json"
    _require_safe_file(
        candidate_root,
        candidate_order_path,
        label="Candidate work-order copy",
        max_bytes=4 * 1024 * 1024,
    )
    candidate_order = _read_json_object(
        candidate_order_path,
        label="Candidate work-order copy",
    )
    if candidate_order != order:
        raise DesignEditorialAssetCandidateImporterError(
            "Candidate work-order copy does not match the persisted source-bound order."
        )
    candidate_order_sha256 = _sha256_file(candidate_order_path)

    receipt_path = candidate_root / DEFAULT_RECEIPT_NAME
    _assert_components_reparse_free(
        candidate_root,
        receipt_path,
        label="Editorial import receipt",
    )
    if receipt_path.exists() or receipt_path.is_symlink():
        raise DesignEditorialAssetCandidateImporterError(
            "Editorial import receipt is immutable and already exists for this candidate."
        )

    candidate_before = _tree_summary(candidate_site)
    if candidate_before != baseline:
        raise DesignEditorialAssetCandidateImporterError(
            "Candidate website baseline mismatch indicates a partial stage or importer bypass."
        )

    try:
        provenance_audit = audit_design_editorial_asset_provenance_file(
            manifest_path or DEFAULT_MANIFEST_PATH,
            repo_root=root,
            as_of=as_of,
        )
    except DesignEditorialAssetProvenanceError as exc:
        raise DesignEditorialAssetCandidateImporterError(
            f"Editorial provenance did not close: {exc}"
        ) from exc

    allowed_paths = _safe_allowed_paths(order.get("allowed_paths"))
    routes = _safe_routes(order.get("routes"))
    import_rows, selected_capsules = _candidate_ready_batch(
        audit=provenance_audit,
        allowed_paths=allowed_paths,
        routes=routes,
    )

    sources: dict[str, Path] = {}
    targets: dict[str, Path] = {}
    baseline_by_path = {str(item["path"]): item for item in baseline["files"] if isinstance(item, Mapping)}
    for row in import_rows:
        target_relative = str(row["target_relative"])
        target = candidate_site / target_relative
        _relative_under(candidate_site, target, label="Candidate image target")
        _require_safe_directory(
            candidate_site,
            target.parent,
            label="Candidate image target parent",
        )
        expected_baseline = baseline_by_path.get(target_relative)
        if not isinstance(expected_baseline, Mapping):
            if target.exists() or target.is_symlink():
                raise DesignEditorialAssetCandidateImporterError(
                    f"Undeclared pre-existing candidate image indicates importer bypass: {target_relative}."
                )
        else:
            _require_safe_file(
                candidate_site,
                target,
                label="Candidate baseline image",
                max_bytes=MAX_IMAGE_BYTES,
            )
            if _sha256_file(target) != expected_baseline.get(
                "sha256"
            ) or target.stat().st_size != expected_baseline.get("bytes"):
                raise DesignEditorialAssetCandidateImporterError(
                    f"Candidate image no longer matches the source-bound baseline: {target_relative}."
                )
        source = _intake_path(root, str(row["sha256"]))
        _assert_image_integrity(
            root=root,
            row=row,
            path=source,
            label="Verified editorial intake image",
        )
        sources[target_relative] = source
        targets[target_relative] = target

    stage = Path(tempfile.mkdtemp(prefix=".editorial-import-", dir=str(candidate_root)))
    _require_safe_directory(candidate_root, stage, label="Importer staging directory")
    staged: dict[str, Path] = {}
    backups: dict[str, Path] = {}
    committed: list[str] = []
    receipt_committed = False
    rollback_failed = False
    try:
        for index, row in enumerate(import_rows):
            target_relative = str(row["target_relative"])
            staged_path = stage / f"{index:02d}-{row['sha256']}.webp"
            shutil.copyfile(sources[target_relative], staged_path)
            _assert_image_integrity(
                root=root,
                row=row,
                path=staged_path,
                label="Staged editorial import image",
            )
            staged[target_relative] = staged_path

        # Close time-of-check/time-of-use gaps before the first target write.
        if _sha256_file(persisted_path) != persisted_sha256:
            raise DesignEditorialAssetCandidateImporterError(
                "Persisted work order changed during editorial import preflight."
            )
        if _sha256_file(candidate_order_path) != candidate_order_sha256:
            raise DesignEditorialAssetCandidateImporterError(
                "Candidate work-order copy changed during editorial import preflight."
            )
        if _tree_summary(candidate_site) != baseline:
            raise DesignEditorialAssetCandidateImporterError(
                "Candidate website changed during editorial import preflight."
            )
        for row in import_rows:
            target_relative = str(row["target_relative"])
            _assert_image_integrity(
                root=root,
                row=row,
                path=sources[target_relative],
                label="Verified editorial intake image",
            )
        if receipt_path.exists() or receipt_path.is_symlink():
            raise DesignEditorialAssetCandidateImporterError(
                "Editorial import receipt appeared during preflight."
            )

        for index, row in enumerate(import_rows):
            target_relative = str(row["target_relative"])
            target = targets[target_relative]
            if target.exists():
                backup = stage / f"{index:02d}.baseline"
                target.replace(backup)
                backups[target_relative] = backup
            staged[target_relative].replace(target)
            committed.append(target_relative)

        for row in import_rows:
            target_relative = str(row["target_relative"])
            _assert_image_integrity(
                root=root,
                row=row,
                path=targets[target_relative],
                label="Imported candidate editorial image",
            )

        public_imports = _receipt_import_rows(
            import_rows,
            root=root,
            candidate_site=candidate_site,
        )
        provenance_manifest = provenance_audit.get("manifest")
        if not isinstance(provenance_manifest, Mapping):
            raise DesignEditorialAssetCandidateImporterError(
                "Editorial provenance audit lost its manifest binding."
            )
        manifest_id = provenance_manifest.get("manifest_id")
        manifest_sha256 = provenance_manifest.get("sha256")
        if (
            not isinstance(manifest_id, str)
            or not _ASSET_ID.fullmatch(manifest_id)
            or not isinstance(manifest_sha256, str)
            or not _SHA256.fullmatch(manifest_sha256)
        ):
            raise DesignEditorialAssetCandidateImporterError(
                "Editorial provenance manifest binding is malformed."
            )
        selected_asset_ids = sorted({str(item["asset_id"]) for item in public_imports})
        receipt: dict[str, Any] = {
            "schema": IMPORT_RECEIPT_SCHEMA,
            "imported_at": _utc_iso(now),
            "state": "imported-local-candidate",
            "passed": True,
            "batch_complete": True,
            "receipt_authority": False,
            "release_eligible": False,
            "package_authority": "none",
            "deployment_authority": "none",
            "authority": dict(NON_AUTHORITATIVE_AUTHORITY),
            "work_order": {
                "run_id": order["run_id"],
                "path": _relative_under(
                    root,
                    persisted_path,
                    label="Persisted design work order",
                ),
                "file_sha256": persisted_sha256,
                "json_sha256": _json_sha256(order),
                "baseline_tree_sha256": baseline["tree_sha256"],
                "candidate_copy_file_sha256": candidate_order_sha256,
            },
            "provenance": {
                "manifest_id": manifest_id,
                "manifest_file_sha256": manifest_sha256,
                "asset_capsules_sha256": provenance_audit.get("asset_capsules_sha256"),
                "selected_asset_capsules_sha256": _json_sha256(selected_capsules),
                "global_artwork_policy_state": GLOBAL_NOT_CLEARED_POLICY["state"],
                "global_artwork_cleared_for_use": False,
                "candidate_ready_asset_ids": selected_asset_ids,
            },
            "routes": routes,
            "imports": public_imports,
            "summary": {
                "asset_count": len(selected_asset_ids),
                "file_count": len(public_imports),
                "total_bytes": sum(int(item["bytes"]) for item in public_imports),
                "batch_complete": True,
                "imports_sha256": _json_sha256(public_imports),
            },
            "next_gate": NEXT_GATE,
        }
        receipt["receipt_payload_sha256"] = _json_sha256(receipt)
        written_receipt = write_candidate_editorial_asset_import(
            receipt,
            repo_root=root,
            manifest_path=manifest_path,
            as_of=as_of,
        )
        if written_receipt != receipt_path:
            raise DesignEditorialAssetCandidateImporterError(
                "Editorial import receipt writer returned an unexpected path."
            )
        receipt_committed = True
        verification = verify_candidate_editorial_asset_import(
            receipt,
            repo_root=root,
            manifest_path=manifest_path,
            as_of=as_of,
            verified_at=now,
        )
        if verification.get("passed") is not True:
            raise DesignEditorialAssetCandidateImporterError(
                "Editorial import receipt failed current post-write verification."
            )
        return receipt
    except Exception as exc:
        try:
            if receipt_committed and receipt_path.exists():
                receipt_path.unlink()
            for row in reversed(import_rows):
                target_relative = str(row["target_relative"])
                target = targets[target_relative]
                if target_relative in committed and target.exists():
                    target.unlink()
                rollback_backup = backups.get(target_relative)
                if rollback_backup is not None and rollback_backup.exists():
                    if target.exists():
                        target.unlink()
                    rollback_backup.replace(target)
        except OSError:
            rollback_failed = True
        if rollback_failed:
            raise DesignEditorialAssetCandidateImporterError(
                "Editorial import failed and rollback could not restore the exact "
                "candidate baseline; the staging directory is retained for investigation."
            ) from exc
        if isinstance(exc, DesignEditorialAssetCandidateImporterError):
            raise
        raise DesignEditorialAssetCandidateImporterError(
            "Editorial import failed during atomic candidate replacement; the "
            "source-bound baseline was restored."
        ) from exc
    finally:
        if not rollback_failed:
            _remove_stage(candidate_root, stage)


__all__ = [
    "BINARY_EXTENSIONS",
    "DEFAULT_RECEIPT_NAME",
    "DEFAULT_VERIFIED_INTAKE_ROOT",
    "EDITORIAL_WORK_ORDER_SCHEMA",
    "IMPORT_RECEIPT_SCHEMA",
    "IMPORT_VERIFICATION_SCHEMA",
    "NON_AUTHORITATIVE_AUTHORITY",
    "TRUSTED_IMPORT_EXTENSIONS",
    "DesignEditorialAssetCandidateImporterError",
    "editorial_asset_control_binding",
    "import_editorial_assets_to_candidate",
    "verify_candidate_editorial_asset_import",
    "write_candidate_editorial_asset_import",
]
