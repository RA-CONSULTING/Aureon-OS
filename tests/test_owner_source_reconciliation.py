"""Safety guarantees for owner-controlled source selection after live drift."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from aureon.operator.live_surface_reconciliation import reconcile_live_surface
from aureon.operator.owner_source_reconciliation import (
    OWNER_SOURCE_RECONCILIATION_AUTHORITY,
    OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_AUTHORITY,
    OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_SCHEMA,
    validate_owner_source_reconciliation,
)

NOW = datetime(2026, 7, 28, 16, 0, tzinfo=UTC)


class _Response:
    status = 200
    headers = {"Content-Type": "text/html"}

    def __init__(self, body: bytes, url: str) -> None:
        self.body = body
        self.url = url

    def geturl(self) -> str:
        return self.url

    def read(self, amount: int = -1) -> bytes:
        return self.body if amount < 0 else self.body[:amount]

    def close(self) -> None:
        return None


def _sha(value: object) -> str:
    if isinstance(value, bytes):
        payload = value
    else:
        payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def _drift_receipt(tmp_path: Path) -> dict:
    repo = tmp_path / "repo"
    site = repo / "website"
    site.mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    local = b"<!doctype html><title>Local</title><p>Local company record.</p>"
    live = b"<!doctype html><title>Live</title><p>Live company record.</p>"
    (site / "index.html").write_bytes(local)
    return reconcile_live_surface(
        repo_root=repo,
        site_root=site,
        base_url="https://example.test/",
        routes=["index.html"],
        now=NOW,
        opener=lambda request, timeout: _Response(live, request.full_url),
    )


def _backup() -> dict:
    return {
        "schema": "aureon.website-operator.backup.v1",
        "state": "verified-backup",
        "observed_at": (NOW - timedelta(minutes=2)).isoformat().replace("+00:00", "Z"),
        "remote_root": "/",
        "tree_sha256": "B" * 64,
    }


def _decision(reconciliation: dict, backup: dict) -> dict:
    return {
        "schema": "aureon.owner-source-reconciliation-decision.v1",
        "decision": "approved",
        "scope": "successor-staged-design-candidate",
        "source_selection": "retain-local-canonical-source",
        "reconciliation_receipt_sha256": _sha(reconciliation),
        "reconciliation_selected_tree_sha256": reconciliation["canonical"]["selected_tree_sha256"],
        "backup_receipt_sha256": _sha(backup),
        "backup_tree_sha256": backup["tree_sha256"],
        "approved_at": (NOW - timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
        "expires_at": (NOW + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
        "approved_by": "Aureon owner",
        "note": "Local source is selected only for a future staged candidate; live record is preserved by backup.",
        "authority": dict(OWNER_SOURCE_RECONCILIATION_AUTHORITY),
    }


def _live_backup(tmp_path: Path) -> dict:
    backup_directory = (tmp_path / "homepl-backup" / "document-root").resolve()
    manifest = (tmp_path / "homepl-backup" / "manifest.csv").resolve()
    return {
        "schema": "aureon.website-operator.backup.v1",
        "state": "verified-backup",
        "observed_at": (NOW - timedelta(minutes=2)).isoformat().replace("+00:00", "Z"),
        "method": "homepl-ftps",
        "source_assertion": "Authenticated Home.pl document-root download",
        "remote_root": "/",
        "backup_directory": str(backup_directory),
        "manifest": str(manifest),
        "manifest_sha256": "A" * 64,
        "tree_sha256": "B" * 64,
        "file_count": 2,
        "total_bytes": 123,
    }


def _live_backup_decision(reconciliation: dict, backup: dict) -> dict:
    return {
        "schema": OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_SCHEMA,
        "decision": "approved",
        "scope": "successor-staged-design-candidate",
        "source_selection": "use-verified-live-backup",
        "reconciliation_receipt_sha256": _sha(reconciliation),
        "reconciliation_selected_tree_sha256": reconciliation["canonical"]["selected_tree_sha256"],
        "backup_receipt_sha256": _sha(backup),
        "backup_tree_sha256": backup["tree_sha256"],
        "backup_directory": backup["backup_directory"],
        "backup_manifest": backup["manifest"],
        "backup_manifest_sha256": backup["manifest_sha256"],
        "approved_at": (NOW - timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
        "expires_at": (NOW + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
        "approved_by": "Aureon owner",
        "note": "The exact fresh verified live backup is selected only for this staged candidate.",
        "authority": dict(OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_AUTHORITY),
    }


def _check(result: dict[str, Any], identifier: str) -> dict[str, Any]:
    return next(item for item in result["checks"] if item["id"] == identifier)


def test_owner_decision_binds_drift_and_verified_backup_without_release_authority(
    tmp_path: Path,
) -> None:
    reconciliation = _drift_receipt(tmp_path)
    backup = _backup()
    decision = _decision(reconciliation, backup)

    result = validate_owner_source_reconciliation(
        decision,
        reconciliation_receipt=reconciliation,
        reconciliation_receipt_sha256=_sha(reconciliation),
        backup_receipt=backup,
        backup_receipt_sha256=_sha(backup),
        now=NOW,
    )

    assert result["passed"] is True
    assert result["state"] == "owner-reconciled-for-staged-candidate"
    assert set(result) == {
        "schema",
        "state",
        "passed",
        "release_eligible",
        "package_authority",
        "deployment_authority",
        "authority",
        "checks",
        "next_gate",
    }
    assert result["release_eligible"] is False
    assert result["package_authority"] == "none"
    assert result["deployment_authority"] == "none"


def test_owner_decision_rejects_tampered_reconciliation_or_backup_binding(tmp_path: Path) -> None:
    reconciliation = _drift_receipt(tmp_path)
    backup = _backup()
    decision = _decision(reconciliation, backup)
    decision["backup_tree_sha256"] = "C" * 64

    result = validate_owner_source_reconciliation(
        decision,
        reconciliation_receipt=reconciliation,
        reconciliation_receipt_sha256=_sha(reconciliation),
        backup_receipt=backup,
        backup_receipt_sha256=_sha(backup),
        now=NOW,
    )

    assert result["passed"] is False
    assert _check(result, "backup-binding")["passed"] is False


def test_owner_decision_rejects_expired_or_non_backup_evidence(tmp_path: Path) -> None:
    reconciliation = _drift_receipt(tmp_path)
    backup = _backup()
    decision = _decision(reconciliation, backup)
    decision["expires_at"] = (NOW - timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
    backup["state"] = "backup-preflight"

    result = validate_owner_source_reconciliation(
        decision,
        reconciliation_receipt=reconciliation,
        reconciliation_receipt_sha256=_sha(reconciliation),
        backup_receipt=backup,
        backup_receipt_sha256=_sha(backup),
        now=NOW,
    )

    assert result["passed"] is False
    assert _check(result, "verified-live-backup")["passed"] is False
    assert _check(result, "fresh-owner-decision")["passed"] is False


def test_v2_owner_decision_selects_one_exact_fresh_verified_live_backup(
    tmp_path: Path,
) -> None:
    reconciliation = _drift_receipt(tmp_path)
    backup = _live_backup(tmp_path)
    decision = _live_backup_decision(reconciliation, backup)

    result = validate_owner_source_reconciliation(
        decision,
        reconciliation_receipt=reconciliation,
        reconciliation_receipt_sha256=_sha(reconciliation),
        backup_receipt=backup,
        backup_receipt_sha256=_sha(backup),
        now=NOW,
    )

    assert result["passed"] is True
    assert result["schema"] == "aureon.owner-source-reconciliation-validation.v2"
    assert result["state"] == "owner-reconciled-for-live-backup-staged-candidate"
    assert result["source_selection"] == "use-verified-live-backup"
    assert result["authority"] == OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_AUTHORITY
    assert result["release_eligible"] is False
    assert result["package_authority"] == "none"
    assert result["deployment_authority"] == "none"


def test_v2_owner_decision_rejects_minimal_or_substituted_backup_evidence(
    tmp_path: Path,
) -> None:
    reconciliation = _drift_receipt(tmp_path)
    complete = _live_backup(tmp_path)
    decision = _live_backup_decision(reconciliation, complete)
    minimal = _backup()

    minimal_result = validate_owner_source_reconciliation(
        decision,
        reconciliation_receipt=reconciliation,
        reconciliation_receipt_sha256=_sha(reconciliation),
        backup_receipt=minimal,
        backup_receipt_sha256=_sha(minimal),
        now=NOW,
    )
    assert minimal_result["passed"] is False
    assert _check(minimal_result, "verified-live-backup")["passed"] is False
    assert _check(minimal_result, "backup-binding")["passed"] is False

    substituted = dict(complete)
    substituted["backup_directory"] = str((tmp_path / "other-backup").resolve())
    substituted_result = validate_owner_source_reconciliation(
        decision,
        reconciliation_receipt=reconciliation,
        reconciliation_receipt_sha256=_sha(reconciliation),
        backup_receipt=substituted,
        backup_receipt_sha256=_sha(substituted),
        now=NOW,
    )
    assert substituted_result["passed"] is False
    assert _check(substituted_result, "backup-binding")["passed"] is False


def test_v2_owner_decision_rejects_backup_older_than_four_hours(
    tmp_path: Path,
) -> None:
    reconciliation = _drift_receipt(tmp_path)
    backup = _live_backup(tmp_path)
    backup["observed_at"] = (NOW - timedelta(hours=4, minutes=2)).isoformat().replace("+00:00", "Z")
    decision = _live_backup_decision(reconciliation, backup)

    result = validate_owner_source_reconciliation(
        decision,
        reconciliation_receipt=reconciliation,
        reconciliation_receipt_sha256=_sha(reconciliation),
        backup_receipt=backup,
        backup_receipt_sha256=_sha(backup),
        now=NOW,
    )

    assert result["passed"] is False
    assert _check(result, "fresh-owner-decision")["passed"] is False


def test_v2_owner_decision_rejects_boolean_backup_counts(tmp_path: Path) -> None:
    reconciliation = _drift_receipt(tmp_path)
    for field in ("file_count", "total_bytes"):
        backup = _live_backup(tmp_path)
        backup[field] = True
        decision = _live_backup_decision(reconciliation, backup)

        result = validate_owner_source_reconciliation(
            decision,
            reconciliation_receipt=reconciliation,
            reconciliation_receipt_sha256=_sha(reconciliation),
            backup_receipt=backup,
            backup_receipt_sha256=_sha(backup),
            now=NOW,
        )

        assert result["passed"] is False
        assert _check(result, "verified-live-backup")["passed"] is False
