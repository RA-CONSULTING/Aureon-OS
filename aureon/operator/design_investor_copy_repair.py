"""Fail-closed control for one source-bound investor-copy repair.

The contract created here is deliberately smaller than a design brief and
stricter than a diagnostic copy audit.  It binds one immutable WebsiteOperator
design-cycle task to one verified v4 candidate work order, one selected source
tree, one route, one policy snapshot, and one route claim capsule.  It carries
only finding counts, a controlled-rule histogram, and deterministic hashes; it
never carries public wording, snippets, correspondence, analytics, or messages.

This module cannot stage, promote, package, release, deploy, or access
credentials.  A passing candidate evaluation remains local evidence for the
existing WebsiteOperator and human-review gates.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
import uuid
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from aureon.operator.design_candidate_control import (
    WORK_ORDER_SCHEMA,
    verify_design_work_order,
)
from aureon.operator.design_investor_copy_quality import (
    DEFAULT_POLICY_PATH,
    POLICY_SCHEMA,
    RULE_IDS,
    _HTMLCopyParser,
    _route_findings,
    _validate_policy,
)
from aureon.operator.design_investor_copy_quality import (
    NON_AUTHORITATIVE_AUTHORITY as COPY_AUDIT_AUTHORITY,
)

CONTRACT_SCHEMA = "aureon.design-investor-copy-repair.v1"
PREFLIGHT_SCHEMA = "aureon.design-investor-copy-repair-preflight.v1"
VERIFICATION_SCHEMA = "aureon.design-investor-copy-repair-verification.v1"
EVALUATION_SCHEMA = "aureon.design-investor-copy-repair-evaluation.v1"
DESIGN_CYCLE_SCHEMA = "aureon-website-design-job-v1"
DEFAULT_CONTRACT_ROOT = Path("artifacts/website-operator/copy-repairs")
DEFAULT_DESIGN_RECEIPT_ROOT = Path("artifacts/website-operator")
DEFAULT_WORK_ORDER_ROOT = Path("artifacts/website-candidates/work-orders")
MAX_INPUT_AGE = timedelta(hours=24)
MAX_CONTRACT_LIFETIME = timedelta(hours=24)

NON_AUTHORITATIVE_AUTHORITY = {
    "scope": "one local source-bound staged investor-copy repair",
    "canonical_website_mutation": "never",
    "candidate_staging": "never",
    "claim_register_mutation": "never",
    "release_eligible": False,
    "package_authority": "none",
    "deployment_authority": "none",
    "credential_access": "none",
    "network_access": "none",
    "human_copy_review": "required",
    "human_visual_acceptance": "required",
    "release_authority": "WebsiteOperator owner gate only",
}

_CONTRACT_FIELDS = frozenset(
    {
        "schema",
        "contract_id",
        "created_at",
        "expires_at",
        "design_cycle",
        "work_order",
        "selected_source",
        "route",
        "policy",
        "source_audit",
        "claim_control",
        "acceptance",
        "authority",
    }
)
_DESIGN_BINDING_FIELDS = frozenset(
    {
        "schema",
        "receipt_path",
        "receipt_sha256",
        "run_id",
        "generated_at",
        "task_id",
        "task_sha256",
    }
)
_WORK_ORDER_BINDING_FIELDS = frozenset({"schema", "path", "sha256", "run_id", "created_at"})
_SOURCE_FIELDS = frozenset(
    {
        "kind",
        "root",
        "manifest_path",
        "manifest_sha256",
        "tree_sha256",
        "source_tree_sha256",
        "file_count",
        "total_bytes",
    }
)
_ROUTE_FIELDS = frozenset({"route", "path", "before_sha256"})
_POLICY_BINDING_FIELDS = frozenset({"schema", "policy_id", "path", "sha256", "issued_at", "refresh_by"})
_AUDIT_FIELDS = frozenset(
    {
        "audited_at",
        "findings_sha256",
        "rule_histogram",
        "route_count",
        "finding_count",
        "blocker_count",
        "warning_count",
        "target_blocker_count",
        "target_warning_count",
    }
)
_HISTOGRAM_FIELDS = frozenset({"rule_id", "finding_count", "blocker_count", "warning_count"})
_CLAIM_FIELDS = frozenset(
    {
        "route_claim_capsule_sha256",
        "required_claim_ids",
        "required_concept_groups_sha256",
        "satisfied_concept_ids",
    }
)
_ACCEPTANCE_FIELDS = frozenset(
    {
        "candidate_reaudit_required",
        "zero_blockers_required",
        "zero_warnings_required",
        "exact_route_only",
        "unchanged_non_target_files_required",
    }
)
_COPY_TASK_FIELDS = frozenset(
    {
        "id",
        "owner",
        "title",
        "finding",
        "allowed_scope",
        "candidate_work_order_required",
        "acceptance",
    }
)
_COPY_FINDING_FIELDS = frozenset({"code", "severity", "path", "route", "blocker_count", "warning_count"})
_CAPSULE_FIELDS = frozenset({"route_id", "route", "claims"})
_CAPSULE_CLAIM_FIELDS = frozenset(
    {
        "id",
        "claim",
        "state",
        "boundary",
        "permitted_wording",
        "prohibited_inferences",
        "public_routes",
        "expires_on",
        "source",
    }
)
_CAPSULE_SOURCE_FIELDS = frozenset({"path", "sha256"})
_BASELINE_FIELDS = frozenset({"tree_sha256", "file_count", "total_bytes", "files"})
_MANIFEST_ROW_FIELDS = frozenset({"path", "sha256", "bytes"})
_LIVE_SOURCE_FIELDS = frozenset(
    {
        "kind",
        "root",
        "manifest_path",
        "manifest_sha256",
        "tree_sha256",
        "baseline_tree_sha256",
        "file_count",
        "total_bytes",
        "remote_root",
    }
)
_TASK_SCOPE = ["artifacts/website-candidates/<run-id>/website/<exact paths declared by v4 work order>"]
_AUDIT_RULE_IDS = frozenset(set(RULE_IDS) | {"required-concept", "policy-freshness"})
_SHA256 = re.compile(r"^[A-F0-9]{64}$")
_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")
_TASK_ID = re.compile(r"^DESIGN-COPY-[0-9]{3}$")
_ROUTE = re.compile(r"^/[a-z0-9._/-]*$")
_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


class InvestorCopyRepairError(ValueError):
    """The repair contract or candidate is unsafe, stale, or malformed."""


def _find_repo_root(start: Path | None = None) -> Path:
    candidate = (start or Path.cwd()).resolve()
    for root in (candidate, *candidate.parents):
        if (root / "pyproject.toml").is_file() and (root / "aureon").is_dir():
            return root
    raise InvestorCopyRepairError("Repository root is unavailable.")


def _json_sha256(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest().upper()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _now(value: datetime | None) -> datetime:
    return (value or datetime.now(UTC)).astimezone(UTC)


def _timestamp(value: object, *, label: str) -> datetime:
    if not isinstance(value, str) or not value or len(value) > 64:
        raise InvestorCopyRepairError(f"{label} timestamp is malformed.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvestorCopyRepairError(f"{label} timestamp is malformed.") from exc
    if parsed.tzinfo is None:
        raise InvestorCopyRepairError(f"{label} timestamp is malformed.")
    return parsed.astimezone(UTC)


def _exact(value: Mapping[str, Any], fields: frozenset[str], *, label: str) -> None:
    if set(value) != fields:
        raise InvestorCopyRepairError(f"{label} field contract changed.")


def _mapping(value: object, *, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise InvestorCopyRepairError(f"{label} must be one object.")
    return dict(value)


def _safe_identifier(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise InvestorCopyRepairError(f"{label} is malformed.")
    return value


def _safe_sha256(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise InvestorCopyRepairError(f"{label} is malformed.")
    return value


def _safe_route(value: object) -> str:
    if (
        not isinstance(value, str)
        or _ROUTE.fullmatch(value) is None
        or "//" in value
        or "?" in value
        or "#" in value
        or any(part in {"", ".", ".."} for part in value.strip("/").split("/") if value != "/")
    ):
        raise InvestorCopyRepairError("Route is malformed.")
    return value


def _safe_html_path(value: object) -> str:
    if not isinstance(value, str) or not value or value != value.replace("\\", "/"):
        raise InvestorCopyRepairError("HTML path is malformed.")
    path = Path(value)
    if (
        path.is_absolute()
        or value.startswith("/")
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.suffix.casefold() != ".html"
    ):
        raise InvestorCopyRepairError("HTML path is malformed.")
    return path.as_posix()


def _safe_relative_path(value: object) -> str:
    if not isinstance(value, str) or not value or value != value.replace("\\", "/"):
        raise InvestorCopyRepairError("Manifest path is malformed.")
    path = Path(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise InvestorCopyRepairError("Manifest path is malformed.")
    return path.as_posix()


def _is_link_or_reparse(path: Path) -> bool:
    try:
        details = path.lstat()
    except OSError as exc:
        raise InvestorCopyRepairError("A bound filesystem object is unavailable.") from exc
    attributes = int(getattr(details, "st_file_attributes", 0))
    return path.is_symlink() or bool(attributes & _REPARSE_POINT)


def _regular_directory(path: Path, *, label: str) -> Path:
    lexical = path.absolute()
    if _is_link_or_reparse(lexical):
        raise InvestorCopyRepairError(f"{label} must not be a link or reparse point.")
    try:
        details = lexical.lstat()
    except OSError as exc:
        raise InvestorCopyRepairError(f"{label} is unavailable.") from exc
    if not stat.S_ISDIR(details.st_mode):
        raise InvestorCopyRepairError(f"{label} must be one directory.")
    return lexical.resolve(strict=True)


def _regular_file(path: Path, *, label: str) -> Path:
    lexical = path.absolute()
    if _is_link_or_reparse(lexical):
        raise InvestorCopyRepairError(f"{label} must not be a link or reparse point.")
    try:
        details = lexical.lstat()
    except OSError as exc:
        raise InvestorCopyRepairError(f"{label} is unavailable.") from exc
    if not stat.S_ISREG(details.st_mode) or details.st_nlink != 1:
        raise InvestorCopyRepairError(f"{label} must be one single-link regular file.")
    return lexical.resolve(strict=True)


def _controlled_file(
    root: Path,
    value: Path,
    *,
    allowed_root: Path,
    label: str,
) -> Path:
    lexical = value if value.is_absolute() else root / value
    allowed_lexical = allowed_root.absolute()
    allowed = _regular_directory(allowed_lexical, label=f"{label} root")
    lexical = lexical.absolute()
    try:
        relative = lexical.relative_to(allowed_lexical)
    except ValueError as exc:
        raise InvestorCopyRepairError(f"{label} escaped its controlled root.") from exc
    current = allowed_lexical
    for part in relative.parts:
        current = current / part
        if _is_link_or_reparse(current):
            raise InvestorCopyRepairError(f"{label} crosses a link or reparse point.")
    target = _regular_file(lexical, label=label)
    try:
        target.relative_to(allowed)
    except ValueError as exc:
        raise InvestorCopyRepairError(f"{label} escaped its controlled root.") from exc
    if target.suffix.casefold() != ".json":
        raise InvestorCopyRepairError(f"{label} must be JSON.")
    return target


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InvestorCopyRepairError(f"{label} is not valid UTF-8 JSON.") from exc
    return _mapping(value, label=label)


def _file_under(root: Path, relative: str, *, label: str) -> Path:
    source_root = _regular_directory(root, label=f"{label} root")
    relative_path = _safe_relative_path(relative)
    current = source_root
    for part in Path(relative_path).parts:
        current = current / part
        if _is_link_or_reparse(current):
            raise InvestorCopyRepairError(f"{label} crosses a link or reparse point.")
    target = _regular_file(current, label=label)
    try:
        target.relative_to(source_root)
    except ValueError as exc:
        raise InvestorCopyRepairError(f"{label} escaped its selected source.") from exc
    return target


def _tree_rows(root: Path) -> list[dict[str, Any]]:
    source_root = _regular_directory(root, label="Selected source")
    rows: list[dict[str, Any]] = []

    def visit(directory: Path) -> None:
        try:
            entries = sorted(os.scandir(directory), key=lambda item: item.name.casefold())
        except OSError as exc:
            raise InvestorCopyRepairError("Selected source tree cannot be enumerated.") from exc
        for entry in entries:
            path = Path(entry.path)
            if _is_link_or_reparse(path):
                raise InvestorCopyRepairError("Selected source tree contains a link or reparse point.")
            try:
                details = path.lstat()
                path.resolve(strict=True).relative_to(source_root)
            except (OSError, ValueError) as exc:
                raise InvestorCopyRepairError("Selected source tree escaped its root.") from exc
            if stat.S_ISDIR(details.st_mode):
                visit(path)
            elif stat.S_ISREG(details.st_mode):
                if details.st_nlink != 1:
                    raise InvestorCopyRepairError("Selected source tree contains a hard-linked file.")
                rows.append(
                    {
                        "path": path.relative_to(source_root).as_posix(),
                        "sha256": _file_sha256(path),
                        "bytes": details.st_size,
                    }
                )
            else:
                raise InvestorCopyRepairError(
                    "Selected source tree contains a non-regular filesystem object."
                )

    visit(source_root)
    return sorted(rows, key=lambda row: str(row["path"]))


def _tree_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    index: dict[str, dict[str, Any]] = {}
    for raw in rows:
        row = _mapping(raw, label="Manifest row")
        _exact(row, _MANIFEST_ROW_FIELDS, label="Manifest row")
        path = _safe_relative_path(row.get("path"))
        sha256 = _safe_sha256(row.get("sha256"), label="Manifest SHA-256")
        size = row.get("bytes")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0 or path in index:
            raise InvestorCopyRepairError("Manifest row is malformed or duplicated.")
        index[path] = {"path": path, "sha256": sha256, "bytes": size}
    ordered = [index[path] for path in sorted(index)]
    return {
        "tree_sha256": _json_sha256(ordered),
        "file_count": len(ordered),
        "total_bytes": sum(int(row["bytes"]) for row in ordered),
        "files": ordered,
    }


def _fresh_input(value: object, *, label: str, current: datetime) -> datetime:
    observed = _timestamp(value, label=label)
    age = current - observed
    if age < timedelta(minutes=-5) or age > MAX_INPUT_AGE:
        raise InvestorCopyRepairError(f"{label} is outside the 24-hour freshness window.")
    return observed


def _load_design_task(
    *,
    root: Path,
    path: Path,
    task_id: str,
    current: datetime,
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    receipt_path = _controlled_file(
        root,
        path,
        allowed_root=root / DEFAULT_DESIGN_RECEIPT_ROOT,
        label="Design-cycle receipt",
    )
    receipt = _read_json(receipt_path, label="Design-cycle receipt")
    if receipt.get("schema") != DESIGN_CYCLE_SCHEMA:
        raise InvestorCopyRepairError("Design-cycle receipt schema is unsupported.")
    run_id = _safe_identifier(receipt.get("run_id"), label="Design-cycle run id")
    if len(run_id) > 80:
        raise InvestorCopyRepairError("Design-cycle run id is malformed.")
    _fresh_input(receipt.get("generated_at"), label="Design-cycle receipt", current=current)
    if not _TASK_ID.fullmatch(task_id):
        raise InvestorCopyRepairError("Design-copy task id is malformed.")
    raw_tasks = receipt.get("work_orders")
    if not isinstance(raw_tasks, list) or not raw_tasks:
        raise InvestorCopyRepairError("Design-cycle receipt has no work orders.")
    matches = [
        _mapping(item, label="Design-copy task")
        for item in raw_tasks
        if isinstance(item, Mapping) and item.get("id") == task_id
    ]
    if len(matches) != 1:
        raise InvestorCopyRepairError("Design-copy task is missing or duplicated.")
    task = matches[0]
    _exact(task, _COPY_TASK_FIELDS, label="Design-copy task")
    if (
        task.get("owner") != "technical-editor"
        or task.get("candidate_work_order_required") is not True
        or task.get("allowed_scope") != _TASK_SCOPE
        or not isinstance(task.get("title"), str)
        or not str(task["title"]).strip()
        or not isinstance(task.get("acceptance"), list)
        or not task["acceptance"]
        or not all(isinstance(item, str) and item.strip() for item in task["acceptance"])
    ):
        raise InvestorCopyRepairError("Design-copy task authority or scope changed.")
    finding = _mapping(task.get("finding"), label="Design-copy task finding")
    _exact(finding, _COPY_FINDING_FIELDS, label="Design-copy task finding")
    if finding.get("code") != "copy.investor-quality" or finding.get("severity") != "error":
        raise InvestorCopyRepairError("Design-copy task no longer describes a copy-quality error.")
    route = _safe_route(finding.get("route"))
    path_value = _safe_html_path(finding.get("path"))
    for name in ("blocker_count", "warning_count"):
        count = finding.get(name)
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise InvestorCopyRepairError("Design-copy task count is malformed.")
    if int(finding["blocker_count"]) < 1:
        raise InvestorCopyRepairError("Design-copy task carries no blocker.")
    task["finding"] = {
        **finding,
        "route": route,
        "path": path_value,
    }
    return receipt, task, receipt_path


def _load_work_order(
    *,
    root: Path,
    path: Path,
    current: datetime,
) -> tuple[dict[str, Any], Path]:
    work_order_path = _controlled_file(
        root,
        path,
        allowed_root=root / DEFAULT_WORK_ORDER_ROOT,
        label="Design work order",
    )
    work_order = _read_json(work_order_path, label="Design work order")
    if work_order.get("schema") != WORK_ORDER_SCHEMA:
        raise InvestorCopyRepairError("Design work-order schema is unsupported.")
    _fresh_input(work_order.get("created_at"), label="Design work order", current=current)
    verification = verify_design_work_order(work_order, repo_root=root)
    if verification.get("passed") is not True:
        raise InvestorCopyRepairError("Design work order is not currently valid.")
    return work_order, work_order_path


def _selected_source(
    *,
    root: Path,
    work_order: Mapping[str, Any],
    work_order_path: Path,
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    baseline = _mapping(work_order.get("baseline"), label="Design work-order baseline")
    _exact(baseline, _BASELINE_FIELDS, label="Design work-order baseline")
    raw_files = baseline.get("files")
    if not isinstance(raw_files, list):
        raise InvestorCopyRepairError("Design work-order baseline manifest is missing.")
    expected = _tree_summary([_mapping(item, label="Baseline manifest row") for item in raw_files])
    if baseline != expected:
        raise InvestorCopyRepairError("Design work-order baseline manifest changed.")

    reconciliation = _mapping(
        work_order.get("live_reconciliation"),
        label="Design work-order reconciliation",
    )
    owner = _mapping(
        reconciliation.get("owner_source_reconciliation"),
        label="Owner source-reconciliation binding",
    )
    raw_live = owner.get("candidate_source")
    if raw_live is None:
        source_root = _regular_directory(root / "website", label="Canonical local source")
        binding = {
            "kind": "canonical-local",
            "root": str(source_root),
            "manifest_path": (f"{work_order_path.relative_to(root).as_posix()}#/baseline/files"),
            "manifest_sha256": _json_sha256(expected["files"]),
            "tree_sha256": expected["tree_sha256"],
            "source_tree_sha256": expected["tree_sha256"],
            "file_count": expected["file_count"],
            "total_bytes": expected["total_bytes"],
        }
    else:
        live = _mapping(raw_live, label="Verified-live-backup source binding")
        _exact(live, _LIVE_SOURCE_FIELDS, label="Verified-live-backup source binding")
        if (
            live.get("kind") != "verified-live-backup"
            or live.get("remote_root") != "/"
            or not isinstance(live.get("root"), str)
            or not Path(str(live["root"])).is_absolute()
            or live.get("baseline_tree_sha256") != expected["tree_sha256"]
            or live.get("file_count") != expected["file_count"]
            or live.get("total_bytes") != expected["total_bytes"]
        ):
            raise InvestorCopyRepairError("Verified-live-backup source binding changed.")
        source_root = _regular_directory(
            Path(str(live["root"])),
            label="Verified-live-backup source",
        )
        manifest_path = _regular_file(
            Path(str(live.get("manifest_path") or "")),
            label="Verified-live-backup manifest",
        )
        if _file_sha256(manifest_path) != live.get("manifest_sha256"):
            raise InvestorCopyRepairError("Verified-live-backup manifest changed.")
        binding = {
            "kind": "verified-live-backup",
            "root": str(source_root),
            "manifest_path": str(manifest_path),
            "manifest_sha256": _safe_sha256(
                live.get("manifest_sha256"),
                label="Verified-live-backup manifest SHA-256",
            ),
            "tree_sha256": expected["tree_sha256"],
            "source_tree_sha256": _safe_sha256(
                live.get("tree_sha256"),
                label="Verified-live-backup source tree SHA-256",
            ),
            "file_count": expected["file_count"],
            "total_bytes": expected["total_bytes"],
        }

    current = _tree_summary(_tree_rows(source_root))
    if current != expected:
        raise InvestorCopyRepairError("Selected source diverged from the verified v4 baseline.")
    return source_root, binding, expected


def _policy(
    *,
    root: Path,
    current: datetime,
) -> tuple[dict[str, Any], Path, list[dict[str, Any]], datetime, datetime, int]:
    policy_path = _file_under(
        root,
        DEFAULT_POLICY_PATH.as_posix(),
        label="Investor-copy policy",
    )
    policy = _read_json(policy_path, label="Investor-copy policy")
    try:
        routes, issued_at, refresh_by, max_age_days = _validate_policy(
            policy,
            as_of=current,
        )
    except ValueError as exc:
        raise InvestorCopyRepairError("Investor-copy policy is malformed.") from exc
    if policy.get("authority") != COPY_AUDIT_AUTHORITY:
        raise InvestorCopyRepairError("Investor-copy policy authority changed.")
    if not issued_at <= current <= refresh_by:
        raise InvestorCopyRepairError("Investor-copy policy is not current.")
    return policy, policy_path, routes, issued_at, refresh_by, max_age_days


def _audit_selected_source(
    *,
    source_root: Path,
    routes: Sequence[Mapping[str, Any]],
    max_age_days: int,
    current: datetime,
    target_route: str,
) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    target_blockers = 0
    target_warnings = 0
    for raw_route in routes:
        route_policy = _mapping(raw_route, label="Investor-copy policy route")
        route = _safe_route(route_policy.get("route"))
        path_value = _safe_html_path(route_policy.get("path"))
        document_path = _file_under(
            source_root,
            path_value,
            label="Investor-copy route document",
        )
        parser = _HTMLCopyParser()
        try:
            parser.feed(document_path.read_text(encoding="utf-8-sig"))
            parser.close()
        except (OSError, UnicodeError) as exc:
            raise InvestorCopyRepairError("Investor-copy route cannot be read as UTF-8.") from exc
        raw_findings = _route_findings(
            route_policy,
            parser.result(),
            snapshot_max_age_days=max_age_days,
            as_of=current,
        )
        for raw_finding in raw_findings:
            finding = _mapping(raw_finding, label="Investor-copy finding")
            rule_id = finding.get("rule_id")
            severity = finding.get("severity")
            if rule_id not in _AUDIT_RULE_IDS or severity not in {"blocker", "warning"}:
                raise InvestorCopyRepairError("Investor-copy audit emitted an unknown finding.")
            reduced = {
                "rule_id": str(rule_id),
                "severity": str(severity),
                "route": route,
                "path": path_value,
            }
            findings.append(reduced)
            if route == target_route:
                target_blockers += severity == "blocker"
                target_warnings += severity == "warning"

    findings.sort(
        key=lambda item: (
            item["rule_id"],
            item["severity"],
            item["route"],
            item["path"],
        )
    )
    histogram: list[dict[str, Any]] = []
    rule_counts: Counter[tuple[str, str]] = Counter((item["rule_id"], item["severity"]) for item in findings)
    for rule_id in sorted({item["rule_id"] for item in findings}):
        blockers = rule_counts[(rule_id, "blocker")]
        warnings = rule_counts[(rule_id, "warning")]
        histogram.append(
            {
                "rule_id": rule_id,
                "finding_count": blockers + warnings,
                "blocker_count": blockers,
                "warning_count": warnings,
            }
        )
    blocker_count = sum(item["severity"] == "blocker" for item in findings)
    warning_count = sum(item["severity"] == "warning" for item in findings)
    return {
        "audited_at": _iso(current),
        "findings_sha256": _json_sha256(findings),
        "rule_histogram": histogram,
        "route_count": len(routes),
        "finding_count": len(findings),
        "blocker_count": blocker_count,
        "warning_count": warning_count,
        "target_blocker_count": target_blockers,
        "target_warning_count": target_warnings,
    }


def _claim_binding(
    *,
    capsule: Mapping[str, Any],
    route: str,
    required_claim_ids: Sequence[str],
    required_concept_groups: object,
) -> dict[str, Any]:
    route_capsule = dict(capsule)
    _exact(route_capsule, _CAPSULE_FIELDS, label="Route claim capsule")
    if route_capsule.get("route") != route:
        raise InvestorCopyRepairError("Route claim capsule is bound to another route.")
    _safe_identifier(route_capsule.get("route_id"), label="Route claim capsule id")
    raw_claims = route_capsule.get("claims")
    if not isinstance(raw_claims, list) or not raw_claims:
        raise InvestorCopyRepairError("Route claim capsule has no claims.")
    observed_ids: list[str] = []
    permitted_wording: list[str] = []
    for raw_claim in raw_claims:
        claim = _mapping(raw_claim, label="Route claim capsule claim")
        _exact(claim, _CAPSULE_CLAIM_FIELDS, label="Route claim capsule claim")
        claim_id = _safe_identifier(claim.get("id"), label="Claim id")
        if claim_id in observed_ids:
            raise InvestorCopyRepairError("Route claim capsule repeats a claim id.")
        observed_ids.append(claim_id)
        if (
            not isinstance(claim.get("claim"), str)
            or not str(claim["claim"]).strip()
            or not isinstance(claim.get("state"), str)
            or not str(claim["state"]).strip()
            or not isinstance(claim.get("boundary"), str)
            or not str(claim["boundary"]).strip()
        ):
            raise InvestorCopyRepairError("Route claim capsule claim text contract changed.")
        for name in ("permitted_wording", "prohibited_inferences", "public_routes"):
            values = claim.get(name)
            if (
                not isinstance(values, list)
                or not values
                or not all(isinstance(item, str) and item.strip() for item in values)
            ):
                raise InvestorCopyRepairError("Route claim capsule list contract changed.")
        permitted_wording.extend(str(item) for item in claim["permitted_wording"])
        if route not in claim["public_routes"]:
            raise InvestorCopyRepairError("Route claim capsule includes an unpermitted claim.")
        source = _mapping(claim.get("source"), label="Route claim source")
        _exact(source, _CAPSULE_SOURCE_FIELDS, label="Route claim source")
        source_path = _safe_relative_path(source.get("path"))
        if not source_path.startswith("website/"):
            raise InvestorCopyRepairError("Route claim source is not a public website record.")
        _safe_sha256(source.get("sha256"), label="Route claim source SHA-256")
        if not isinstance(claim.get("expires_on"), str) or not str(claim["expires_on"]).strip():
            raise InvestorCopyRepairError("Route claim expiry is malformed.")

    required = [_safe_identifier(item, label="Required claim id") for item in required_claim_ids]
    if not required or len(required) != len(set(required)) or sorted(required) != sorted(observed_ids):
        raise InvestorCopyRepairError("Required claim ids do not exactly match the route claim capsule.")
    if not isinstance(required_concept_groups, list):
        raise InvestorCopyRepairError("Required concept groups are malformed.")
    normalised_groups: list[dict[str, Any]] = []
    satisfied_concepts: list[str] = []
    unsatisfied_concepts: list[str] = []
    for raw_group in required_concept_groups:
        group = _mapping(raw_group, label="Required concept group")
        if set(group) != {"concept_id", "severity", "alternatives"}:
            raise InvestorCopyRepairError("Required concept group field contract changed.")
        concept_id = _safe_identifier(group.get("concept_id"), label="Required concept id")
        severity = group.get("severity")
        alternatives = group.get("alternatives")
        if (
            severity not in {"blocker", "warning"}
            or not isinstance(alternatives, list)
            or not alternatives
            or not all(isinstance(item, str) and item.strip() for item in alternatives)
        ):
            raise InvestorCopyRepairError("Required concept group is malformed.")
        controlled_alternatives = sorted(str(item) for item in alternatives)
        normalised_groups.append(
            {
                "concept_id": concept_id,
                "severity": str(severity),
                "alternatives": controlled_alternatives,
            }
        )
        satisfied = any(
            alternative.casefold() in wording.casefold()
            for alternative in controlled_alternatives
            for wording in permitted_wording
        )
        if satisfied:
            satisfied_concepts.append(concept_id)
        else:
            unsatisfied_concepts.append(concept_id)
    normalised_groups.sort(key=lambda item: str(item["concept_id"]))
    if len({str(item["concept_id"]) for item in normalised_groups}) != len(normalised_groups):
        raise InvestorCopyRepairError("Required concept groups contain duplicate ids.")
    if unsatisfied_concepts:
        raise InvestorCopyRepairError("A required concept is not satisfiable by the sealed claim capsule.")
    return {
        "route_claim_capsule_sha256": _json_sha256(route_capsule),
        "required_claim_ids": sorted(required),
        "required_concept_groups_sha256": _json_sha256(normalised_groups),
        "satisfied_concept_ids": sorted(satisfied_concepts),
    }


def _policy_route(
    routes: Sequence[Mapping[str, Any]],
    *,
    route: str,
) -> dict[str, Any]:
    matches = [dict(item) for item in routes if item.get("route") == route]
    if len(matches) != 1:
        raise InvestorCopyRepairError("Target route is not uniquely controlled by the policy.")
    return matches[0]


def preflight_investor_copy_repair_contract(
    *,
    design_cycle_receipt: Path,
    task_id: str,
    route_claim_capsule: Mapping[str, Any],
    required_claim_ids: Sequence[str],
    repo_root: Path | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """Read-only task, policy, route, and claim satisfiability preflight.

    This deliberately runs before a v4 work order is written. It cannot prove
    or bind a selected source tree; the full contract creator repeats every
    check and adds that source/audit binding after the exact work order exists.
    """

    root = _find_repo_root(repo_root)
    current = _now(as_of)
    design, task, design_path = _load_design_task(
        root=root,
        path=design_cycle_receipt,
        task_id=task_id,
        current=current,
    )
    finding = _mapping(task.get("finding"), label="Design-copy task finding")
    route = _safe_route(finding.get("route"))
    html_path = _safe_html_path(finding.get("path"))
    policy, policy_path, routes, issued_at, refresh_by, _ = _policy(
        root=root,
        current=current,
    )
    controlled_route = _policy_route(routes, route=route)
    if _safe_html_path(controlled_route.get("path")) != html_path:
        raise InvestorCopyRepairError("Design-copy task and policy HTML path do not match.")
    claim_control = _claim_binding(
        capsule=route_claim_capsule,
        route=route,
        required_claim_ids=required_claim_ids,
        required_concept_groups=controlled_route.get("required_concept_groups"),
    )
    return {
        "schema": PREFLIGHT_SCHEMA,
        "checked_at": _iso(current),
        "passed": True,
        "design_cycle": {
            "receipt_path": design_path.relative_to(root).as_posix(),
            "receipt_sha256": _file_sha256(design_path),
            "run_id": _safe_identifier(
                design.get("run_id"),
                label="Design-cycle run id",
            ),
            "task_id": task_id,
            "task_sha256": _json_sha256(task),
        },
        "route": {
            "route": route,
            "path": html_path,
        },
        "policy": {
            "schema": POLICY_SCHEMA,
            "policy_id": policy["policy_id"],
            "path": policy_path.relative_to(root).as_posix(),
            "sha256": _file_sha256(policy_path),
            "issued_at": _iso(issued_at),
            "refresh_by": _iso(refresh_by),
        },
        "claim_control": claim_control,
        "authority": dict(NON_AUTHORITATIVE_AUTHORITY),
    }


def preflight_investor_copy_repair_work_order(
    *,
    design_cycle_receipt: Path,
    task_id: str,
    work_order: Mapping[str, Any],
    planned_work_order_path: Path,
    route_claim_capsule: Mapping[str, Any],
    required_claim_ids: Sequence[str],
    repo_root: Path | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """Read-only selected-source feasibility check before work-order persistence."""

    root = _find_repo_root(repo_root)
    current = _now(as_of)
    preflight = preflight_investor_copy_repair_contract(
        design_cycle_receipt=design_cycle_receipt,
        task_id=task_id,
        route_claim_capsule=route_claim_capsule,
        required_claim_ids=required_claim_ids,
        repo_root=root,
        as_of=current,
    )
    order = dict(work_order)
    if order.get("schema") != WORK_ORDER_SCHEMA:
        raise InvestorCopyRepairError("Design work-order schema is unsupported.")
    verification = verify_design_work_order(order, repo_root=root)
    if verification.get("passed") is not True:
        raise InvestorCopyRepairError("Design work order is not currently valid.")
    preflight_route = _mapping(
        preflight.get("route"),
        label="Investor-copy preflight route",
    )
    route = _safe_route(preflight_route.get("route"))
    html_path = _safe_html_path(preflight_route.get("path"))
    if order.get("routes") != [route] or order.get("allowed_paths") != [html_path]:
        raise InvestorCopyRepairError(
            "Copy repair work order must contain exactly one route and its one HTML path."
        )
    planned_path = planned_work_order_path
    if not planned_path.is_absolute():
        planned_path = root / planned_path
    try:
        planned_path.resolve().relative_to((root / DEFAULT_WORK_ORDER_ROOT).resolve())
    except ValueError as exc:
        raise InvestorCopyRepairError(
            "Planned copy-repair work order path escaped its controlled root."
        ) from exc
    source_root, source_binding, _ = _selected_source(
        root=root,
        work_order=order,
        work_order_path=planned_path.resolve(),
    )
    _, _, policy_routes, _, _, max_age_days = _policy(
        root=root,
        current=current,
    )
    source_audit = _audit_selected_source(
        source_root=source_root,
        routes=policy_routes,
        max_age_days=max_age_days,
        current=current,
        target_route=route,
    )
    if int(source_audit["target_blocker_count"]) == 0 and int(source_audit["target_warning_count"]) == 0:
        raise InvestorCopyRepairError("Selected source target has no current copy finding to repair.")
    if int(source_audit["blocker_count"]) != int(source_audit["target_blocker_count"]) or int(
        source_audit["warning_count"]
    ) != int(source_audit["target_warning_count"]):
        raise InvestorCopyRepairError(
            "Non-target policy routes have copy findings that an exact one-route repair cannot clear."
        )
    return {
        **preflight,
        "selected_source": source_binding,
        "source_audit": source_audit,
    }


def create_investor_copy_repair_contract(
    *,
    design_cycle_receipt: Path,
    task_id: str,
    work_order: Path,
    route_claim_capsule: Mapping[str, Any],
    required_claim_ids: Sequence[str],
    repo_root: Path | None = None,
    now: datetime | None = None,
    lifetime: timedelta = MAX_CONTRACT_LIFETIME,
) -> dict[str, Any]:
    """Create one privacy-minimised, source-neutral copy-repair contract."""

    root = _find_repo_root(repo_root)
    current = _now(now)
    if lifetime <= timedelta(0) or lifetime > MAX_CONTRACT_LIFETIME:
        raise InvestorCopyRepairError("Contract lifetime must be greater than zero and at most 24 hours.")

    design, task, design_path = _load_design_task(
        root=root,
        path=design_cycle_receipt,
        task_id=task_id,
        current=current,
    )
    order, order_path = _load_work_order(
        root=root,
        path=work_order,
        current=current,
    )
    finding = _mapping(task["finding"], label="Design-copy task finding")
    route = _safe_route(finding["route"])
    html_path = _safe_html_path(finding["path"])
    if order.get("routes") != [route] or order.get("allowed_paths") != [html_path]:
        raise InvestorCopyRepairError(
            "Copy repair work order must contain exactly one route and its one HTML path."
        )

    source_root, source_binding, _ = _selected_source(
        root=root,
        work_order=order,
        work_order_path=order_path,
    )
    policy, policy_path, policy_routes, issued_at, refresh_by, max_age_days = _policy(
        root=root,
        current=current,
    )
    controlled_route = _policy_route(policy_routes, route=route)
    if _safe_html_path(controlled_route.get("path")) != html_path:
        raise InvestorCopyRepairError("Task route and policy HTML path do not match.")
    target_file = _file_under(source_root, html_path, label="Selected investor-copy route")
    source_audit = _audit_selected_source(
        source_root=source_root,
        routes=policy_routes,
        max_age_days=max_age_days,
        current=current,
        target_route=route,
    )
    if int(source_audit["target_blocker_count"]) == 0 and int(source_audit["target_warning_count"]) == 0:
        raise InvestorCopyRepairError("Selected source target has no current copy finding to repair.")
    if int(source_audit["blocker_count"]) != int(source_audit["target_blocker_count"]) or int(
        source_audit["warning_count"]
    ) != int(source_audit["target_warning_count"]):
        raise InvestorCopyRepairError(
            "Non-target policy routes have copy findings that an exact one-route repair cannot clear."
        )
    claim_control = _claim_binding(
        capsule=route_claim_capsule,
        route=route,
        required_claim_ids=required_claim_ids,
        required_concept_groups=controlled_route.get("required_concept_groups"),
    )
    expires_at = min(current + lifetime, refresh_by)
    if expires_at <= current:
        raise InvestorCopyRepairError("Policy freshness leaves no usable contract lifetime.")
    design_run_id = _safe_identifier(design.get("run_id"), label="Design-cycle run id")
    order_run_id = _safe_identifier(order.get("run_id"), label="Work-order run id")
    contract_id = (
        f"copy-repair-{design_run_id[:8]}-{task_id.casefold()}-{order_run_id[:8]}-{uuid.uuid4().hex[:8]}"
    )
    return {
        "schema": CONTRACT_SCHEMA,
        "contract_id": contract_id,
        "created_at": _iso(current),
        "expires_at": _iso(expires_at),
        "design_cycle": {
            "schema": DESIGN_CYCLE_SCHEMA,
            "receipt_path": design_path.relative_to(root).as_posix(),
            "receipt_sha256": _file_sha256(design_path),
            "run_id": design_run_id,
            "generated_at": _iso(_timestamp(design["generated_at"], label="Design-cycle receipt")),
            "task_id": task_id,
            "task_sha256": _json_sha256(task),
        },
        "work_order": {
            "schema": WORK_ORDER_SCHEMA,
            "path": order_path.relative_to(root).as_posix(),
            "sha256": _file_sha256(order_path),
            "run_id": order_run_id,
            "created_at": _iso(_timestamp(order["created_at"], label="Design work order")),
        },
        "selected_source": source_binding,
        "route": {
            "route": route,
            "path": html_path,
            "before_sha256": _file_sha256(target_file),
        },
        "policy": {
            "schema": POLICY_SCHEMA,
            "policy_id": policy["policy_id"],
            "path": policy_path.relative_to(root).as_posix(),
            "sha256": _file_sha256(policy_path),
            "issued_at": _iso(issued_at),
            "refresh_by": _iso(refresh_by),
        },
        "source_audit": source_audit,
        "claim_control": claim_control,
        "acceptance": {
            "candidate_reaudit_required": True,
            "zero_blockers_required": True,
            "zero_warnings_required": True,
            "exact_route_only": True,
            "unchanged_non_target_files_required": True,
        },
        "authority": dict(NON_AUTHORITATIVE_AUTHORITY),
    }


def _validate_histogram(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise InvestorCopyRepairError("Rule histogram is malformed.")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in value:
        row = _mapping(raw, label="Rule histogram row")
        _exact(row, _HISTOGRAM_FIELDS, label="Rule histogram row")
        rule_id = row.get("rule_id")
        if rule_id not in _AUDIT_RULE_IDS or str(rule_id) in seen:
            raise InvestorCopyRepairError("Rule histogram contains an unknown or duplicate rule.")
        seen.add(str(rule_id))
        counts = []
        for name in ("finding_count", "blocker_count", "warning_count"):
            count = row.get(name)
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                raise InvestorCopyRepairError("Rule histogram count is malformed.")
            counts.append(count)
        if counts[0] != counts[1] + counts[2] or counts[0] == 0:
            raise InvestorCopyRepairError("Rule histogram totals are inconsistent.")
        rows.append(dict(row))
    if [str(row["rule_id"]) for row in rows] != sorted(seen):
        raise InvestorCopyRepairError("Rule histogram must use deterministic rule order.")
    return rows


def _validate_contract_shape(
    contract: Mapping[str, Any],
    *,
    current: datetime,
) -> dict[str, Any]:
    value = dict(contract)
    _exact(value, _CONTRACT_FIELDS, label="Investor-copy repair contract")
    if value.get("schema") != CONTRACT_SCHEMA:
        raise InvestorCopyRepairError("Investor-copy repair contract schema is unsupported.")
    _safe_identifier(value.get("contract_id"), label="Contract id")
    created_at = _timestamp(value.get("created_at"), label="Contract created_at")
    expires_at = _timestamp(value.get("expires_at"), label="Contract expires_at")
    if (
        expires_at <= created_at
        or expires_at - created_at > MAX_CONTRACT_LIFETIME
        or current < created_at - timedelta(minutes=5)
        or current > expires_at
    ):
        raise InvestorCopyRepairError("Investor-copy repair contract is stale or future-dated.")
    if value.get("authority") != NON_AUTHORITATIVE_AUTHORITY:
        raise InvestorCopyRepairError("Investor-copy repair authority changed.")

    design = _mapping(value.get("design_cycle"), label="Design-cycle binding")
    _exact(design, _DESIGN_BINDING_FIELDS, label="Design-cycle binding")
    if design.get("schema") != DESIGN_CYCLE_SCHEMA:
        raise InvestorCopyRepairError("Design-cycle binding schema changed.")
    _safe_identifier(design.get("run_id"), label="Design-cycle run id")
    if not isinstance(design.get("task_id"), str) or not _TASK_ID.fullmatch(str(design["task_id"])):
        raise InvestorCopyRepairError("Design-copy task id is malformed.")
    _safe_sha256(design.get("receipt_sha256"), label="Design-cycle receipt SHA-256")
    _safe_sha256(design.get("task_sha256"), label="Design-copy task SHA-256")
    _timestamp(design.get("generated_at"), label="Design-cycle generated_at")

    order = _mapping(value.get("work_order"), label="Work-order binding")
    _exact(order, _WORK_ORDER_BINDING_FIELDS, label="Work-order binding")
    if order.get("schema") != WORK_ORDER_SCHEMA:
        raise InvestorCopyRepairError("Work-order binding schema changed.")
    _safe_identifier(order.get("run_id"), label="Work-order run id")
    _safe_sha256(order.get("sha256"), label="Work-order SHA-256")
    _timestamp(order.get("created_at"), label="Work-order created_at")

    source = _mapping(value.get("selected_source"), label="Selected-source binding")
    _exact(source, _SOURCE_FIELDS, label="Selected-source binding")
    if source.get("kind") not in {"canonical-local", "verified-live-backup"}:
        raise InvestorCopyRepairError("Selected-source kind is unsupported.")
    if not isinstance(source.get("root"), str) or not Path(str(source["root"])).is_absolute():
        raise InvestorCopyRepairError("Selected-source root is malformed.")
    if not isinstance(source.get("manifest_path"), str) or not source["manifest_path"]:
        raise InvestorCopyRepairError("Selected-source manifest path is malformed.")
    for name in ("manifest_sha256", "tree_sha256", "source_tree_sha256"):
        _safe_sha256(source.get(name), label=f"Selected-source {name}")
    for name in ("file_count", "total_bytes"):
        count = source.get(name)
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise InvestorCopyRepairError("Selected-source count is malformed.")

    route = _mapping(value.get("route"), label="Route binding")
    _exact(route, _ROUTE_FIELDS, label="Route binding")
    _safe_route(route.get("route"))
    _safe_html_path(route.get("path"))
    _safe_sha256(route.get("before_sha256"), label="Route before SHA-256")

    policy = _mapping(value.get("policy"), label="Policy binding")
    _exact(policy, _POLICY_BINDING_FIELDS, label="Policy binding")
    if policy.get("schema") != POLICY_SCHEMA or policy.get("path") != DEFAULT_POLICY_PATH.as_posix():
        raise InvestorCopyRepairError("Policy binding schema or path changed.")
    _safe_identifier(policy.get("policy_id"), label="Policy id")
    _safe_sha256(policy.get("sha256"), label="Policy SHA-256")
    issued_at = _timestamp(policy.get("issued_at"), label="Policy issued_at")
    refresh_by = _timestamp(policy.get("refresh_by"), label="Policy refresh_by")
    if not issued_at <= current <= refresh_by:
        raise InvestorCopyRepairError("Bound investor-copy policy is stale.")

    audit = _mapping(value.get("source_audit"), label="Source audit")
    _exact(audit, _AUDIT_FIELDS, label="Source audit")
    _timestamp(audit.get("audited_at"), label="Source audit audited_at")
    _safe_sha256(audit.get("findings_sha256"), label="Source audit findings SHA-256")
    histogram = _validate_histogram(audit.get("rule_histogram"))
    totals: dict[str, int] = {}
    for name in (
        "route_count",
        "finding_count",
        "blocker_count",
        "warning_count",
        "target_blocker_count",
        "target_warning_count",
    ):
        count = audit.get(name)
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise InvestorCopyRepairError("Source audit count is malformed.")
        totals[name] = count
    if (
        totals["route_count"] < 1
        or totals["finding_count"] != totals["blocker_count"] + totals["warning_count"]
        or totals["finding_count"] != sum(int(row["finding_count"]) for row in histogram)
        or totals["blocker_count"] != sum(int(row["blocker_count"]) for row in histogram)
        or totals["warning_count"] != sum(int(row["warning_count"]) for row in histogram)
        or totals["target_blocker_count"] + totals["target_warning_count"] < 1
    ):
        raise InvestorCopyRepairError("Source audit totals are inconsistent.")

    claims = _mapping(value.get("claim_control"), label="Claim control")
    _exact(claims, _CLAIM_FIELDS, label="Claim control")
    _safe_sha256(
        claims.get("route_claim_capsule_sha256"),
        label="Route claim capsule SHA-256",
    )
    _safe_sha256(
        claims.get("required_concept_groups_sha256"),
        label="Required concept groups SHA-256",
    )
    raw_ids = claims.get("required_claim_ids")
    if not isinstance(raw_ids, list) or not raw_ids:
        raise InvestorCopyRepairError("Required claim ids are missing.")
    claim_ids = [_safe_identifier(item, label="Required claim id") for item in raw_ids]
    if claim_ids != sorted(set(claim_ids)):
        raise InvestorCopyRepairError("Required claim ids are not unique deterministic ids.")
    raw_concept_ids = claims.get("satisfied_concept_ids")
    if not isinstance(raw_concept_ids, list):
        raise InvestorCopyRepairError("Satisfied concept ids are malformed.")
    concept_ids = [_safe_identifier(item, label="Satisfied concept id") for item in raw_concept_ids]
    if concept_ids != sorted(set(concept_ids)):
        raise InvestorCopyRepairError("Satisfied concept ids are not unique deterministic ids.")

    acceptance = _mapping(value.get("acceptance"), label="Acceptance control")
    _exact(acceptance, _ACCEPTANCE_FIELDS, label="Acceptance control")
    if not all(acceptance.get(name) is True for name in _ACCEPTANCE_FIELDS):
        raise InvestorCopyRepairError("Acceptance control was weakened.")
    return value


def _verify_contract_or_raise(
    contract: Mapping[str, Any],
    *,
    route_claim_capsule: Mapping[str, Any],
    root: Path,
    current: datetime,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    value = _validate_contract_shape(contract, current=current)
    design_binding = _mapping(value["design_cycle"], label="Design-cycle binding")
    design, task, design_path = _load_design_task(
        root=root,
        path=Path(str(design_binding["receipt_path"])),
        task_id=str(design_binding["task_id"]),
        current=current,
    )
    if (
        _file_sha256(design_path) != design_binding["receipt_sha256"]
        or design.get("run_id") != design_binding["run_id"]
        or _iso(_timestamp(design["generated_at"], label="Design-cycle receipt"))
        != design_binding["generated_at"]
        or _json_sha256(task) != design_binding["task_sha256"]
    ):
        raise InvestorCopyRepairError("Design-cycle receipt or exact task changed.")

    order_binding = _mapping(value["work_order"], label="Work-order binding")
    order, order_path = _load_work_order(
        root=root,
        path=Path(str(order_binding["path"])),
        current=current,
    )
    if (
        _file_sha256(order_path) != order_binding["sha256"]
        or order.get("run_id") != order_binding["run_id"]
        or _iso(_timestamp(order["created_at"], label="Design work order")) != order_binding["created_at"]
    ):
        raise InvestorCopyRepairError("Verified v4 work order changed.")

    route_binding = _mapping(value["route"], label="Route binding")
    route = _safe_route(route_binding["route"])
    html_path = _safe_html_path(route_binding["path"])
    if order.get("routes") != [route] or order.get("allowed_paths") != [html_path]:
        raise InvestorCopyRepairError("Work-order route or path broadened.")
    task_finding = _mapping(task["finding"], label="Design-copy task finding")
    if task_finding.get("route") != route or task_finding.get("path") != html_path:
        raise InvestorCopyRepairError("Design-copy task route or path changed.")

    source_root, source_binding, _ = _selected_source(
        root=root,
        work_order=order,
        work_order_path=order_path,
    )
    if source_binding != value["selected_source"]:
        raise InvestorCopyRepairError("Selected source binding was substituted.")
    target = _file_under(source_root, html_path, label="Selected investor-copy route")
    if _file_sha256(target) != route_binding["before_sha256"]:
        raise InvestorCopyRepairError("Selected-source route diverged from its before hash.")

    policy, policy_path, routes, issued_at, refresh_by, max_age_days = _policy(
        root=root,
        current=current,
    )
    policy_binding = _mapping(value["policy"], label="Policy binding")
    if policy_binding != {
        "schema": POLICY_SCHEMA,
        "policy_id": policy["policy_id"],
        "path": policy_path.relative_to(root).as_posix(),
        "sha256": _file_sha256(policy_path),
        "issued_at": _iso(issued_at),
        "refresh_by": _iso(refresh_by),
    }:
        raise InvestorCopyRepairError("Investor-copy policy binding changed.")
    controlled_route = _policy_route(routes, route=route)
    if _safe_html_path(controlled_route["path"]) != html_path:
        raise InvestorCopyRepairError("Policy route/path binding changed.")

    source_audit = _audit_selected_source(
        source_root=source_root,
        routes=routes,
        max_age_days=max_age_days,
        current=current,
        target_route=route,
    )
    bound_audit = _mapping(value["source_audit"], label="Source audit")
    comparable_audit = {**source_audit, "audited_at": bound_audit["audited_at"]}
    if comparable_audit != bound_audit:
        raise InvestorCopyRepairError("Selected-source audit digest or histogram changed.")

    claim_binding = _claim_binding(
        capsule=route_claim_capsule,
        route=route,
        required_claim_ids=_mapping(
            value["claim_control"],
            label="Claim control",
        )["required_claim_ids"],
        required_concept_groups=controlled_route.get("required_concept_groups"),
    )
    if claim_binding != value["claim_control"]:
        raise InvestorCopyRepairError("Route claim capsule or required claim ids changed.")
    return value, order, source_audit


def verify_investor_copy_repair_contract(
    contract: Mapping[str, Any],
    *,
    route_claim_capsule: Mapping[str, Any],
    repo_root: Path | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """Revalidate every dependency without exposing source wording or findings."""

    root = _find_repo_root(repo_root)
    current = _now(as_of)
    try:
        value, _, source_audit = _verify_contract_or_raise(
            contract,
            route_claim_capsule=route_claim_capsule,
            root=root,
            current=current,
        )
        passed = True
        contract_id = str(value["contract_id"])
        audit_digest = str(source_audit["findings_sha256"])
    except (InvestorCopyRepairError, OSError, ValueError):
        passed = False
        contract_id = (
            str(contract.get("contract_id"))
            if isinstance(contract.get("contract_id"), str)
            and _IDENTIFIER.fullmatch(str(contract["contract_id"]))
            else ""
        )
        audit_digest = ""
    return {
        "schema": VERIFICATION_SCHEMA,
        "verified_at": _iso(current),
        "state": "pass" if passed else "blocked",
        "passed": passed,
        "contract_id": contract_id,
        "contract_sha256": _json_sha256(contract),
        "source_findings_sha256": audit_digest,
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "authority": dict(NON_AUTHORITATIVE_AUTHORITY),
    }


def _candidate_diff(
    *,
    candidate_root: Path,
    baseline: Mapping[str, Any],
    target_path: str,
) -> tuple[list[str], dict[str, Any]]:
    raw_files = baseline.get("files")
    if not isinstance(raw_files, list):
        raise InvestorCopyRepairError("Candidate baseline manifest is missing.")
    expected = _tree_summary([_mapping(item, label="Candidate baseline row") for item in raw_files])
    observed = _tree_summary(_tree_rows(candidate_root))
    expected_index = {str(item["path"]): item for item in expected["files"]}
    observed_index = {str(item["path"]): item for item in observed["files"]}
    if set(expected_index) != set(observed_index):
        raise InvestorCopyRepairError("Candidate added or removed a public file.")
    changed = sorted(
        path
        for path in expected_index
        if expected_index[path]["sha256"] != observed_index[path]["sha256"]
        or expected_index[path]["bytes"] != observed_index[path]["bytes"]
    )
    if changed != [target_path]:
        raise InvestorCopyRepairError("Candidate changed files outside the exact copy route.")
    return changed, observed


def evaluate_investor_copy_repair_candidate(
    contract: Mapping[str, Any],
    *,
    candidate_website_root: Path,
    route_claim_capsule: Mapping[str, Any],
    repo_root: Path | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """Re-audit the exact staged candidate; zero blockers and warnings are required."""

    root = _find_repo_root(repo_root)
    current = _now(as_of)
    checks = {
        "contract_current": False,
        "exact_candidate_root": False,
        "exact_target_only_diff": False,
        "target_changed": False,
        "policy_current": False,
        "zero_blockers": False,
        "zero_warnings": False,
        "stable_post_audit_tree": False,
    }
    candidate_sha256 = ""
    candidate_tree_sha256 = ""
    re_audit: dict[str, Any] = {
        "audited_at": _iso(current),
        "findings_sha256": "",
        "rule_histogram": [],
        "route_count": 0,
        "finding_count": 0,
        "blocker_count": 0,
        "warning_count": 0,
        "target_blocker_count": 0,
        "target_warning_count": 0,
    }
    contract_id = ""
    target_route = ""
    target_path = ""
    try:
        value, order, _ = _verify_contract_or_raise(
            contract,
            route_claim_capsule=route_claim_capsule,
            root=root,
            current=current,
        )
        checks["contract_current"] = True
        contract_id = str(value["contract_id"])
        route_binding = _mapping(value["route"], label="Route binding")
        target_route = _safe_route(route_binding["route"])
        target_path = _safe_html_path(route_binding["path"])

        layout = _mapping(order.get("candidate_layout"), label="Candidate layout")
        expected_relative = _safe_relative_path(layout.get("website_path"))
        expected_root = _regular_directory(
            root / expected_relative,
            label="Expected staged candidate website",
        )
        supplied_root = _regular_directory(
            candidate_website_root,
            label="Supplied staged candidate website",
        )
        if supplied_root != expected_root:
            raise InvestorCopyRepairError("Supplied candidate root is not the sealed v4 workspace.")
        checks["exact_candidate_root"] = True

        baseline = _mapping(order.get("baseline"), label="Candidate baseline")
        _, candidate_summary = _candidate_diff(
            candidate_root=supplied_root,
            baseline=baseline,
            target_path=target_path,
        )
        checks["exact_target_only_diff"] = True
        candidate_tree_sha256 = str(candidate_summary["tree_sha256"])
        candidate_target = _file_under(
            supplied_root,
            target_path,
            label="Candidate investor-copy route",
        )
        candidate_sha256 = _file_sha256(candidate_target)
        if candidate_sha256 == route_binding["before_sha256"]:
            raise InvestorCopyRepairError("Candidate target did not change.")
        checks["target_changed"] = True

        _, _, policy_routes, _, _, max_age_days = _policy(root=root, current=current)
        checks["policy_current"] = True
        re_audit = _audit_selected_source(
            source_root=supplied_root,
            routes=policy_routes,
            max_age_days=max_age_days,
            current=current,
            target_route=target_route,
        )
        checks["zero_blockers"] = int(re_audit["blocker_count"]) == 0
        checks["zero_warnings"] = int(re_audit["warning_count"]) == 0
        post_audit_summary = _tree_summary(_tree_rows(supplied_root))
        if post_audit_summary != candidate_summary or _file_sha256(candidate_target) != candidate_sha256:
            raise InvestorCopyRepairError("Candidate tree changed during investor-copy policy replay.")
        checks["stable_post_audit_tree"] = True
    except (InvestorCopyRepairError, OSError, ValueError):
        pass

    passed = all(checks.values())
    return {
        "schema": EVALUATION_SCHEMA,
        "evaluated_at": _iso(current),
        "state": "pass" if passed else "blocked",
        "passed": passed,
        "contract_id": contract_id,
        "contract_sha256": _json_sha256(contract),
        "route": target_route,
        "path": target_path,
        "candidate_sha256": candidate_sha256,
        "candidate_tree_sha256": candidate_tree_sha256,
        "candidate_audit": re_audit,
        "checks": [{"id": name.replace("_", "-"), "passed": outcome} for name, outcome in checks.items()],
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "authority": dict(NON_AUTHORITATIVE_AUTHORITY),
        "next_gate": (
            "A passing receipt may proceed only to existing claim-surface, browser, "
            "accessibility, visual, package, owner, backup and live read-back gates."
        ),
    }


def write_investor_copy_repair_contract(
    contract: Mapping[str, Any],
    *,
    output_path: Path | None = None,
    repo_root: Path | None = None,
) -> Path:
    """Persist one immutable contract below the dedicated copy-repair root."""

    root = _find_repo_root(repo_root)
    contract_id = _safe_identifier(contract.get("contract_id"), label="Contract id")
    allowed_parent = root / DEFAULT_CONTRACT_ROOT
    base_parent = _regular_directory(
        root / DEFAULT_CONTRACT_ROOT.parent,
        label="WebsiteOperator artifact root",
    )
    if allowed_parent.exists():
        destination_parent = _regular_directory(
            allowed_parent,
            label="Copy-repair artifact root",
        )
    else:
        allowed_parent.mkdir()
        destination_parent = _regular_directory(
            allowed_parent,
            label="Copy-repair artifact root",
        )
    if destination_parent.parent != base_parent:
        raise InvestorCopyRepairError("Copy-repair artifact root escaped its controlled parent.")
    destination = output_path if output_path is not None else destination_parent / f"{contract_id}.json"
    if not destination.is_absolute():
        destination = root / destination
    lexical = destination.absolute()
    if lexical.parent.resolve() != destination_parent or lexical.suffix.casefold() != ".json":
        raise InvestorCopyRepairError(
            "Copy-repair contract output must be one direct JSON child of its controlled root."
        )
    _validate_contract_shape(contract, current=_timestamp(contract["created_at"], label="created_at"))
    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{lexical.name}.",
        suffix=".tmp",
        dir=str(destination_parent),
    )
    temporary = Path(temporary_name)
    try:
        with open(handle, "w", encoding="utf-8", newline="\n", closefd=True) as stream:
            json.dump(dict(contract), stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, lexical)
        except FileExistsError as exc:
            raise InvestorCopyRepairError("Refusing to overwrite immutable copy-repair evidence.") from exc
    finally:
        if temporary.exists():
            temporary.unlink()
    return _regular_file(lexical, label="Written copy-repair contract")
