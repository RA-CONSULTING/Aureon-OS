"""Privacy and closure guarantees for stakeholder-driven design signals."""

from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from aureon.operator.design_stakeholder_feedback import (
    DEFAULT_FEEDBACK_PATH,
    FEEDBACK_AUDIT_SCHEMA,
    FEEDBACK_SCHEMA,
    NON_AUTHORITATIVE_AUTHORITY,
    RESPONSE_AUDIT_SCHEMA,
    RESPONSE_MANIFEST_SCHEMA,
    DesignStakeholderFeedbackError,
    audit_design_stakeholder_feedback,
    audit_design_stakeholder_feedback_file,
    audit_design_stakeholder_response_manifest,
    response_manifest_sha256,
    signal_capsule_sha256,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FEEDBACK_PATH = REPO_ROOT / DEFAULT_FEEDBACK_PATH
SCHEMA_PATH = (
    REPO_ROOT
    / "docs/research/schemas/AUREON_DESIGN_STAKEHOLDER_FEEDBACK_V1.schema.json"
)
AS_OF = datetime(2026, 7, 30, 18, 0, tzinfo=UTC)

_PRIMARY_PATH_BY_ROUTE = {
    "/": "index.html",
    "/funding/investor-deck/": "funding/investor-deck/index.html",
    "/projects/": "projects/index.html",
    "/research/": "research/index.html",
}


def _feedback() -> dict:
    return json.loads(FEEDBACK_PATH.read_text(encoding="utf-8"))


def _audit() -> dict:
    return audit_design_stakeholder_feedback_file(
        FEEDBACK_PATH,
        repo_root=REPO_ROOT,
        as_of=AS_OF,
    )


def _valid_manifest() -> dict:
    audit = _audit()
    responses: dict[str, dict] = {}
    for item in audit["signal_capsules"]:
        signal = item["signal"]
        if signal["disposition"] == "no-action":
            response_code = "unchanged"
            changed_paths: list[str] = []
            claim_ids: list[str] = []
        elif signal["disposition"] == "consider":
            response_code = "deferred"
            changed_paths = []
            claim_ids = []
        else:
            response_code = "addressed"
            changed_paths = [_PRIMARY_PATH_BY_ROUTE[signal["route_scope"]]]
            claim_ids = [signal["claim_ids"][0]]
        responses[signal["signal_id"]] = {
            "disposition": signal["disposition"],
            "response_code": response_code,
            "route_scope": signal["route_scope"],
            "changed_paths": changed_paths,
            "claim_ids": claim_ids,
            "signal_capsule_sha256": item["signal_capsule_sha256"],
        }
    manifest = {
        "schema": RESPONSE_MANIFEST_SCHEMA,
        "feedback": {
            "feedback_id": audit["feedback"]["feedback_id"],
            "path": audit["feedback"]["path"],
            "sha256": audit["feedback"]["sha256"],
        },
        "authority": NON_AUTHORITATIVE_AUTHORITY,
        "responses": responses,
        "manifest_sha256": "0" * 64,
    }
    manifest["manifest_sha256"] = response_manifest_sha256(manifest)
    return manifest


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _write_private_snapshot(text: str) -> tuple[Path, str]:
    path = REPO_ROOT / "docs/research" / f"_stakeholder-private-test-{uuid4().hex}.md"
    path.write_text(text, encoding="utf-8")
    return path, path.relative_to(REPO_ROOT).as_posix()


def test_canonical_feedback_is_current_source_bound_and_non_authoritative() -> None:
    result = _audit()

    assert result["schema"] == FEEDBACK_AUDIT_SCHEMA
    assert result["state"] == "current"
    assert result["passed"] is True
    assert result["receipt_authority"] is False
    assert result["release_eligible"] is False
    assert result["package_authority"] == "none"
    assert result["deployment_authority"] == "none"
    assert result["authority"] == NON_AUTHORITATIVE_AUTHORITY
    assert result["summary"] == {
        "signal_count": 7,
        "emitted_capsule_count": 7,
        "action_requested_count": 5,
        "no_action_count": 1,
    }
    assert result["freshness"]["state"] == "current"
    assert result["evidence_snapshot"]["privacy_safe"] is True
    assert result["evidence_snapshot"]["hash_matches"] is True
    assert len(result["signal_capsules"]) == 7
    for item in result["signal_capsules"]:
        assert set(item) == {"signal", "signal_capsule_sha256"}
        assert set(item["signal"]) == {
            "signal_id",
            "signal_kind",
            "disposition",
            "priority",
            "requested_response_dimension",
            "route_scope",
            "claim_ids",
        }
    serialised = json.dumps(result["signal_capsules"]).casefold()
    assert "the first screen needs" not in serialised
    assert "original correspondence" not in serialised
    assert "pricing" not in serialised


def test_stale_feedback_fails_closed_without_emitting_capsules() -> None:
    result = audit_design_stakeholder_feedback_file(
        FEEDBACK_PATH,
        repo_root=REPO_ROOT,
        as_of=datetime(2026, 8, 14, 0, 0, tzinfo=UTC),
    )

    assert result["state"] == "stale"
    assert result["passed"] is False
    assert result["freshness"]["state"] == "stale"
    assert result["signal_capsules"] == []
    assert result["summary"]["emitted_capsule_count"] == 0
    assert result["receipt_authority"] is False


def test_unknown_and_private_fields_fail_closed() -> None:
    unknown = _feedback()
    unknown["signals"][0]["worker_note"] = "unbounded prose"
    with pytest.raises(DesignStakeholderFeedbackError, match="fields do not match"):
        audit_design_stakeholder_feedback(
            unknown,
            feedback_path=FEEDBACK_PATH,
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )

    private = _feedback()
    private["signals"][0]["raw_message"] = "copied provider message"
    with pytest.raises(DesignStakeholderFeedbackError, match="private-content fields"):
        audit_design_stakeholder_feedback(
            private,
            feedback_path=FEEDBACK_PATH,
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("sender@example.test", "email"),
        ("https://provider.example/private/message", "url"),
        ("sk-proj-ABCDEFGH12345678", "credential-token"),
        ("From: Example Person\nSubject: copied message", "raw-message"),
        ("message-id: 19fa2eb29f90d7ef", "raw-message"),
        ("> copied private quotation", "raw-quotation"),
        ("Dr Exampleperson requested a revision.", "named-person"),
        ("Private valuation GBP 2500000.", "private-finance"),
    ],
)
def test_private_snapshot_material_is_rejected_without_emission(
    text: str,
    code: str,
) -> None:
    path, relative = _write_private_snapshot(
        "# Human-created redacted evidence snapshot\n\n" + text + "\n"
    )
    try:
        feedback = _feedback()
        feedback["evidence_snapshot"]["path"] = relative
        feedback["evidence_snapshot"]["sha256"] = _sha256(path)

        result = audit_design_stakeholder_feedback(
            feedback,
            feedback_path=FEEDBACK_PATH,
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )

        snapshot_check = next(
            item
            for item in result["checks"]
            if item["id"] == "evidence-snapshot-integrity"
        )
        assert result["passed"] is False
        assert result["signal_capsules"] == []
        assert result["evidence_snapshot"]["privacy_safe"] is False
        assert code in snapshot_check["evidence"]["privacy_violation_codes"]
    finally:
        path.unlink(missing_ok=True)


def test_unknown_claim_and_route_are_rejected() -> None:
    unknown_claim = _feedback()
    unknown_claim["signals"][0]["claim_ids"] = ["unknown-public-claim"]
    with pytest.raises(DesignStakeholderFeedbackError, match="unknown public claim"):
        audit_design_stakeholder_feedback(
            unknown_claim,
            feedback_path=FEEDBACK_PATH,
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )

    unknown_route = _feedback()
    unknown_route["signals"][0]["route_scope"] = "/private-data-room/"
    with pytest.raises(DesignStakeholderFeedbackError, match="not an allowed public route"):
        audit_design_stakeholder_feedback(
            unknown_route,
            feedback_path=FEEDBACK_PATH,
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )


def test_snapshot_traversal_and_hash_drift_fail_closed() -> None:
    traversal = _feedback()
    traversal["evidence_snapshot"]["path"] = "../.env"
    with pytest.raises(DesignStakeholderFeedbackError, match="unsafe"):
        audit_design_stakeholder_feedback(
            traversal,
            feedback_path=FEEDBACK_PATH,
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )

    drift = _feedback()
    drift["evidence_snapshot"]["sha256"] = "0" * 64
    result = audit_design_stakeholder_feedback(
        drift,
        feedback_path=FEEDBACK_PATH,
        repo_root=REPO_ROOT,
        as_of=AS_OF,
    )
    assert result["passed"] is False
    assert result["evidence_snapshot"]["hash_matches"] is False
    assert result["signal_capsules"] == []


def test_snapshot_symlink_is_rejected() -> None:
    target = REPO_ROOT / "docs/research" / f"_stakeholder-target-{uuid4().hex}.md"
    link = REPO_ROOT / "docs/research" / f"_stakeholder-link-{uuid4().hex}.md"
    target.write_text("# Redacted signal codes only\n", encoding="utf-8")
    try:
        try:
            os.symlink(target, link)
        except (OSError, NotImplementedError) as exc:
            pytest.skip(f"Symlink creation is unavailable: {exc}")
        feedback = _feedback()
        feedback["evidence_snapshot"]["path"] = link.relative_to(REPO_ROOT).as_posix()
        feedback["evidence_snapshot"]["sha256"] = _sha256(target)

        result = audit_design_stakeholder_feedback(
            feedback,
            feedback_path=FEEDBACK_PATH,
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )

        assert result["passed"] is False
        assert result["evidence_snapshot"]["regular_file"] is False
        assert result["signal_capsules"] == []
    finally:
        link.unlink(missing_ok=True)
        target.unlink(missing_ok=True)


def test_signal_capsule_hash_is_deterministic_and_content_free() -> None:
    first = _audit()["signal_capsules"]
    second = _audit()["signal_capsules"]

    assert first == second
    assert all(
        item["signal_capsule_sha256"] == signal_capsule_sha256(item["signal"])
        for item in first
    )
    assert len({item["signal_capsule_sha256"] for item in first}) == len(first)


def test_valid_response_manifest_is_closed_hash_bound_and_non_authoritative() -> None:
    result = audit_design_stakeholder_response_manifest(
        _valid_manifest(),
        repo_root=REPO_ROOT,
        as_of=AS_OF,
    )

    assert result["schema"] == RESPONSE_AUDIT_SCHEMA
    assert result["state"] == "pass"
    assert result["passed"] is True
    assert result["receipt_authority"] is False
    assert result["release_eligible"] is False
    assert result["package_authority"] == "none"
    assert result["deployment_authority"] == "none"
    assert result["summary"]["signal_count"] == 7
    assert result["summary"]["response_count"] == 7
    assert result["summary"]["unchanged_count"] == 1


def test_response_manifest_closure_and_hash_drift_fail_closed() -> None:
    incomplete = _valid_manifest()
    incomplete["responses"].pop("signal-market-problem-clarity")
    incomplete["manifest_sha256"] = response_manifest_sha256(incomplete)
    with pytest.raises(DesignStakeholderFeedbackError, match="close every signal"):
        audit_design_stakeholder_response_manifest(
            incomplete,
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )

    drift = _valid_manifest()
    drift["responses"]["signal-market-problem-clarity"]["changed_paths"] = ["styles.css"]
    with pytest.raises(DesignStakeholderFeedbackError, match="deterministic hash"):
        audit_design_stakeholder_response_manifest(
            drift,
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )

    capsule_drift = _valid_manifest()
    capsule_drift["responses"]["signal-market-problem-clarity"][
        "signal_capsule_sha256"
    ] = "0" * 64
    capsule_drift["manifest_sha256"] = response_manifest_sha256(capsule_drift)
    with pytest.raises(DesignStakeholderFeedbackError, match="capsule binding"):
        audit_design_stakeholder_response_manifest(
            capsule_drift,
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )


def test_unchanged_no_action_signal_cannot_declare_changes() -> None:
    manifest = _valid_manifest()
    response = manifest["responses"]["signal-proof-state-clarity"]
    response["response_code"] = "addressed"
    response["changed_paths"] = ["funding/investor-deck/index.html"]
    response["claim_ids"] = ["github-technical-access"]
    manifest["manifest_sha256"] = response_manifest_sha256(manifest)

    with pytest.raises(DesignStakeholderFeedbackError, match="must remain unchanged"):
        audit_design_stakeholder_response_manifest(
            manifest,
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )


def test_response_manifest_rejects_path_escape_and_unknown_claim() -> None:
    escaped = _valid_manifest()
    response = escaped["responses"]["signal-market-problem-clarity"]
    response["changed_paths"] = ["../website/index.html"]
    escaped["manifest_sha256"] = response_manifest_sha256(escaped)
    with pytest.raises(DesignStakeholderFeedbackError, match="unsafe"):
        audit_design_stakeholder_response_manifest(
            escaped,
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )

    unknown_claim = _valid_manifest()
    response = unknown_claim["responses"]["signal-market-problem-clarity"]
    response["claim_ids"] = ["unknown-public-claim"]
    unknown_claim["manifest_sha256"] = response_manifest_sha256(unknown_claim)
    with pytest.raises(DesignStakeholderFeedbackError, match="exceed its signal capsule"):
        audit_design_stakeholder_response_manifest(
            unknown_claim,
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )


def test_schema_is_exact_and_declares_no_operational_authority() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    feedback = _feedback()

    assert feedback["schema"] == FEEDBACK_SCHEMA
    assert schema["$defs"]["feedback"]["additionalProperties"] is False
    assert schema["$defs"]["signal"]["additionalProperties"] is False
    assert schema["$defs"]["response"]["additionalProperties"] is False
    assert schema["$defs"]["responseManifest"]["additionalProperties"] is False
    authority = schema["$defs"]["authority"]["properties"]
    assert authority["release_eligible"]["const"] is False
    assert authority["package_authority"]["const"] == "none"
    assert authority["deployment_authority"]["const"] == "none"
    assert authority["credential_access"]["const"] == "none"
    assert authority["network_access"]["const"] == "none"
    assert authority["connector_access"]["const"] == "none"

    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.Draft202012Validator(schema).validate(feedback)
    jsonschema.Draft202012Validator(schema).validate(_valid_manifest())
