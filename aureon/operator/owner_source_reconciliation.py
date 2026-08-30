"""Owner-controlled source selection after a live website drift observation.

This module deliberately has no function that creates, edits, promotes,
packages, uploads, or deploys a website.  It only verifies a narrowly scoped
owner decision that lets one future *staged* design candidate either retain the
current local canonical source under the existing v1 contract or select one
exact fresh, verified Home.pl live backup under the stricter v2 contract.

The decision is separate from the later package-hash release approval.  It is
short-lived and evidence-bound so a coding agent cannot quietly decide that a
local branch should replace the public company record.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping

from aureon.operator.live_surface_reconciliation import (
    RECONCILIATION_SCHEMA,
    LiveSurfaceReconciliationError,
    validate_live_surface_reconciliation,
)

OWNER_SOURCE_RECONCILIATION_SCHEMA = "aureon.owner-source-reconciliation-decision.v1"
OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_SCHEMA = "aureon.owner-source-reconciliation-decision.v2"
OWNER_SOURCE_RECONCILIATION_VALIDATION_SCHEMA = "aureon.owner-source-reconciliation-validation.v1"
OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_VALIDATION_SCHEMA = (
    "aureon.owner-source-reconciliation-validation.v2"
)
MAX_OWNER_SOURCE_DECISION_AGE = timedelta(hours=4)

OWNER_SOURCE_RECONCILIATION_AUTHORITY = {
    "scope": "owner-controlled local-source selection after observed public website drift",
    "canonical_website_mutation": "none by this decision or a design agent",
    "release_eligible": False,
    "package_authority": "none",
    "deployment_authority": "none",
    "credential_access": "none",
    "release_authority": "WebsiteOperator owner gate only",
}

OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_AUTHORITY = {
    "scope": "owner-controlled verified-live-backup source selection after observed public website drift",
    "canonical_website_mutation": "none by this decision or a design agent",
    "release_eligible": False,
    "package_authority": "none",
    "deployment_authority": "none",
    "credential_access": "none",
    "release_authority": "WebsiteOperator owner gate only",
}


class OwnerSourceReconciliationError(ValueError):
    """A decision cannot safely bind a drifted live and local website record."""


def _check(identifier: str, passed: bool, message: str, **evidence: Any) -> dict[str, Any]:
    return {
        "id": identifier,
        "passed": bool(passed),
        "message": message,
        "evidence": evidence,
    }


def _parse_datetime(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise OwnerSourceReconciliationError(f"{label} must be a non-empty ISO-8601 timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OwnerSourceReconciliationError(f"{label} must be a valid ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None:
        raise OwnerSourceReconciliationError(f"{label} must include a timezone.")
    return parsed.astimezone(UTC)


def _sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789ABCDEF" for character in value)
    )


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise OwnerSourceReconciliationError(f"{label} must be a JSON object.")
    return value


def _decision_shape(decision: Mapping[str, Any]) -> tuple[bool, str]:
    common = {
        "schema",
        "decision",
        "scope",
        "source_selection",
        "reconciliation_receipt_sha256",
        "reconciliation_selected_tree_sha256",
        "backup_receipt_sha256",
        "backup_tree_sha256",
        "approved_at",
        "expires_at",
        "approved_by",
        "note",
        "authority",
    }
    schema = decision.get("schema")
    expected = set(common)
    if schema == OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_SCHEMA:
        expected.update(
            {
                "backup_directory",
                "backup_manifest",
                "backup_manifest_sha256",
            }
        )
    missing = expected.difference(decision)
    unexpected = set(decision).difference(expected)
    if missing:
        return False, "missing: " + ", ".join(sorted(missing))
    if unexpected:
        return False, "unsupported: " + ", ".join(sorted(unexpected))
    if schema not in {
        OWNER_SOURCE_RECONCILIATION_SCHEMA,
        OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_SCHEMA,
    }:
        return False, "schema"
    if decision.get("decision") != "approved":
        return False, "decision"
    if decision.get("scope") != "successor-staged-design-candidate":
        return False, "scope"
    expected_selection = (
        "use-verified-live-backup"
        if schema == OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_SCHEMA
        else "retain-local-canonical-source"
    )
    if decision.get("source_selection") != expected_selection:
        return False, "source_selection"
    expected_authority = (
        OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_AUTHORITY
        if schema == OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_SCHEMA
        else OWNER_SOURCE_RECONCILIATION_AUTHORITY
    )
    if decision.get("authority") != expected_authority:
        return False, "authority"
    for field in (
        "reconciliation_receipt_sha256",
        "reconciliation_selected_tree_sha256",
        "backup_receipt_sha256",
        "backup_tree_sha256",
    ):
        if not _sha256(decision.get(field)):
            return False, field
    if schema == OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_SCHEMA:
        if not _sha256(decision.get("backup_manifest_sha256")):
            return False, "backup_manifest_sha256"
        for field in ("backup_directory", "backup_manifest"):
            value = decision.get(field)
            if not isinstance(value, str) or not value.strip() or not Path(value).is_absolute():
                return False, field
    if not isinstance(decision.get("approved_by"), str) or not decision["approved_by"].strip():
        return False, "approved_by"
    if not isinstance(decision.get("note"), str) or not decision["note"].strip():
        return False, "note"
    try:
        _parse_datetime(decision.get("approved_at"), "approved_at")
        _parse_datetime(decision.get("expires_at"), "expires_at")
    except OwnerSourceReconciliationError as exc:
        return False, str(exc)
    return True, ""


def validate_owner_source_reconciliation(
    decision: Mapping[str, Any],
    *,
    reconciliation_receipt: Mapping[str, Any],
    reconciliation_receipt_sha256: str,
    backup_receipt: Mapping[str, Any],
    backup_receipt_sha256: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Verify a short-lived owner source choice for one staged candidate.

    The caller supplies byte hashes of the immutable receipts it loaded from
    disk.  This keeps paths under the caller's repository-bound policy while
    the decision itself remains portable and unable to name an arbitrary file.
    """

    checks: list[dict[str, Any]] = []
    decision_object = _mapping(decision, "Owner source-reconciliation decision")
    reconciliation = _mapping(reconciliation_receipt, "Live-surface reconciliation receipt")
    backup = _mapping(backup_receipt, "Verified backup receipt")
    shape_ok, shape_error = _decision_shape(decision_object)
    live_backup_selected = (
        decision_object.get("schema") == OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_SCHEMA
        and decision_object.get("source_selection") == "use-verified-live-backup"
    )
    checks.append(
        _check(
            "decision-shape",
            shape_ok,
            "Decision must use the exact owner source-reconciliation contract and remain non-authoritative for release.",
            error=shape_error,
        )
    )

    reconciliation_ok = False
    reconciliation_state = ""
    selected_tree = ""
    try:
        validate_live_surface_reconciliation(reconciliation)
        reconciliation_state = str(reconciliation.get("state") or "")
        canonical = _mapping(reconciliation.get("canonical"), "Reconciliation canonical snapshot")
        selected_tree = str(canonical.get("selected_tree_sha256") or "")
        reconciliation_ok = (
            reconciliation.get("schema") == RECONCILIATION_SCHEMA
            and reconciliation_state == "live-drift-detected"
            and reconciliation.get("passed") is False
        )
    except LiveSurfaceReconciliationError:
        reconciliation_ok = False
    checks.append(
        _check(
            "live-drift-evidence",
            reconciliation_ok,
            "A local-source selection is permitted only after a valid, materially drifted public-surface observation.",
            state=reconciliation_state,
        )
    )

    receipt_binding_ok = (
        shape_ok
        and _sha256(reconciliation_receipt_sha256)
        and decision_object.get("reconciliation_receipt_sha256") == reconciliation_receipt_sha256
        and decision_object.get("reconciliation_selected_tree_sha256") == selected_tree
    )
    checks.append(
        _check(
            "reconciliation-binding",
            receipt_binding_ok,
            "Decision must bind the exact reconciliation receipt and its selected local-source snapshot.",
        )
    )

    backup_state = str(backup.get("state") or "")
    backup_tree = str(backup.get("tree_sha256") or "")
    backup_ok = (
        backup_state == "verified-backup"
        and backup.get("remote_root") == "/"
        and _sha256(backup_tree)
        and isinstance(backup.get("observed_at"), str)
    )
    if live_backup_selected:
        backup_ok = (
            backup_ok
            and backup.get("schema") == "aureon.website-operator.backup.v1"
            and backup.get("method") in {"homepl-ftps", "homepl-webftp"}
            and backup.get("source_assertion") == "Authenticated Home.pl document-root download"
            and isinstance(backup.get("backup_directory"), str)
            and bool(str(backup.get("backup_directory") or "").strip())
            and Path(str(backup.get("backup_directory"))).is_absolute()
            and isinstance(backup.get("manifest"), str)
            and bool(str(backup.get("manifest") or "").strip())
            and Path(str(backup.get("manifest"))).is_absolute()
            and _sha256(backup.get("manifest_sha256"))
            and type(backup.get("file_count")) is int
            and int(backup.get("file_count", 0)) > 0
            and type(backup.get("total_bytes")) is int
            and int(backup.get("total_bytes", -1)) >= 0
        )
    checks.append(
        _check(
            "verified-live-backup",
            backup_ok,
            "Decision must be backed by a fresh verified Home.pl document-root backup, not a preflight or package receipt.",
            state=backup_state,
            remote_root=backup.get("remote_root"),
        )
    )
    backup_binding_ok = (
        shape_ok
        and _sha256(backup_receipt_sha256)
        and decision_object.get("backup_receipt_sha256") == backup_receipt_sha256
        and decision_object.get("backup_tree_sha256") == backup_tree
    )
    if live_backup_selected:
        backup_binding_ok = (
            backup_binding_ok
            and decision_object.get("backup_directory") == backup.get("backup_directory")
            and decision_object.get("backup_manifest") == backup.get("manifest")
            and decision_object.get("backup_manifest_sha256") == backup.get("manifest_sha256")
        )
    checks.append(
        _check(
            "backup-binding",
            backup_binding_ok,
            "Decision must bind the exact verified-backup receipt and backup tree hash.",
        )
    )

    timing_ok = False
    observed_before_approval = False
    try:
        approved_at = _parse_datetime(decision_object.get("approved_at"), "approved_at")
        expires_at = _parse_datetime(decision_object.get("expires_at"), "expires_at")
        observed_at = _parse_datetime(backup.get("observed_at"), "backup.observed_at")
        reference = (now or datetime.now(UTC)).astimezone(UTC)
        observed_before_approval = observed_at <= approved_at
        timing_ok = (
            approved_at <= reference < expires_at
            and expires_at - approved_at <= MAX_OWNER_SOURCE_DECISION_AGE
            and observed_before_approval
        )
        if live_backup_selected:
            timing_ok = timing_ok and approved_at - observed_at <= MAX_OWNER_SOURCE_DECISION_AGE
    except OwnerSourceReconciliationError:
        timing_ok = False
    checks.append(
        _check(
            "fresh-owner-decision",
            timing_ok,
            "Owner source selection must be active for at most four hours and follow the verified live backup.",
            maximum_hours=MAX_OWNER_SOURCE_DECISION_AGE.total_seconds() / 3600,
            backup_observed_before_approval=observed_before_approval,
        )
    )

    passed = all(check["passed"] for check in checks)
    result = {
        "schema": (
            OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_VALIDATION_SCHEMA
            if live_backup_selected
            else OWNER_SOURCE_RECONCILIATION_VALIDATION_SCHEMA
        ),
        "state": (
            (
                "owner-reconciled-for-live-backup-staged-candidate"
                if live_backup_selected
                else "owner-reconciled-for-staged-candidate"
            )
            if passed
            else "blocked"
        ),
        "passed": passed,
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "authority": dict(
            OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_AUTHORITY
            if live_backup_selected
            else OWNER_SOURCE_RECONCILIATION_AUTHORITY
        ),
        "checks": checks,
        "next_gate": (
            "A separate exact-path staged candidate work order may now bind this evidence. It remains unable to promote, package, back up or deploy."
            if passed
            else "Preserve both source records and repair the owner-decision evidence before staging any autonomous candidate."
        ),
    }
    if live_backup_selected:
        result["source_selection"] = "use-verified-live-backup"
    return result
