from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import textwrap
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

import aureon.operator.design_investor_copy_governance as governance

NOW = datetime(2026, 7, 30, 10, 0, tzinfo=UTC)
DECIDED_AT = NOW - timedelta(minutes=5)
SOURCE_ROOT = Path(__file__).resolve().parents[1]

# This is the complete dependency closure used by the proposal/source replay and
# the unmodified claim, stakeholder-feedback, and design-brief audits.  Every
# test copies the exact bytes into an isolated repository before it may mutate.
_FIXTURE_FILES = (
    "artifacts/website-operator/20260730T045336Z-design-cycle-4204c795.json",
    "artifacts/website-operator/20260730T070009Z-investor-copy-governance-proposal.json",
    ("artifacts/website-operator/20260730T070009Z-investor-copy-governance-proposal-validation.json"),
    ("artifacts/website-operator/20260730T072344Z-investor-copy-governance-superseding-proposal.json"),
    (
        "artifacts/website-operator/"
        "20260730T072344Z-investor-copy-governance-superseding-proposal-validation.json"
    ),
    ("artifacts/website-operator/20260730T074800Z-investor-copy-governance-superseding-proposal-v3.json"),
    (
        "artifacts/website-operator/"
        "20260730T074800Z-investor-copy-governance-superseding-proposal-validation-v3.json"
    ),
    ("artifacts/website-operator/20260730T075154Z-investor-copy-governance-superseding-proposal-v4.json"),
    (
        "artifacts/website-operator/"
        "20260730T075154Z-investor-copy-governance-superseding-proposal-validation-v4.json"
    ),
    ("artifacts/website-operator/20260730T094627Z-investor-copy-governance-application-proposal-v5.json"),
    (
        "artifacts/website-operator/"
        "20260730T094627Z-investor-copy-governance-application-proposal-validation-v5.json"
    ),
    "data/website_operator/design_research_sources.v1.json",
    "data/website_operator/design_stakeholder_feedback.v1.json",
    "data/website_operator/investor_copy_quality_policy.v1.json",
    "data/website_operator/investor_site_design_brief.v1.json",
    "data/website_operator/public_claim_evidence_register.v1.json",
    "docs/research/AUREON_INVESTOR_NARRATIVE_ALIGNMENT_20260728.md",
    "docs/research/AUREON_INVESTOR_SITE_DESIGN_BRIEF_20260728.md",
    "docs/research/AUREON_INVESTOR_WEBSITE_PEER_BENCHMARK_20260730.md",
    "docs/research/AUREON_ORCID_PUBLIC_RECORD_RECONCILIATION_20260730.md",
    "docs/research/AUREON_STAKEHOLDER_SIGNAL_REDACTION_20260730.md",
    "website/about/index.html",
    "website/data/blades.json",
    "website/data/company-platform.json",
    "website/data/funding-status.json",
    "website/data/innovation-map.json",
    "website/data/research-catalogue.json",
    "website/data/updates.json",
    "website/funding/investor-deck/index.html",
    "website/index.html",
    "website/projects/index.html",
    "website/research/index.html",
    "website/script.js",
    "website/styles.css",
)


def _serialise(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_serialise(value))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()
    }


def _canonical_snapshot(root: Path) -> dict[str, bytes]:
    return {relative: (root / relative).read_bytes() for relative in governance.CANONICAL_GOVERNANCE_PATHS}


def _decision(*, state: str = governance.APPROVE_STATE) -> dict[str, Any]:
    return {
        "schema": governance.DECISION_SCHEMA,
        "decision_id": "governance-test-decision-001",
        "decided_at": DECIDED_AT.isoformat().replace("+00:00", "Z"),
        "owner": governance.NAMED_OWNER,
        "decision": state,
        "proposal": {
            "path": governance.DEFAULT_PROPOSAL_PATH.as_posix(),
            "sha256": governance.EXPECTED_PROPOSAL_SHA256,
        },
        "validation": {
            "path": governance.DEFAULT_VALIDATION_PATH.as_posix(),
            "sha256": governance.EXPECTED_VALIDATION_SHA256,
        },
        "acknowledgements": {
            "governance_files": list(governance.CANONICAL_GOVERNANCE_PATHS),
            "no_policy_change": True,
            "no_website_change": True,
            "no_candidate_or_package_authority": True,
            "no_release_or_deployment_authority": True,
            "v1_through_v4_superseded_and_rejected": True,
            "sentence_level_evidence_os_wording": governance.EXPECTED_SURFACE_WORDING,
        },
    }


@pytest.fixture()  # type: ignore[untyped-decorator]
def governance_fixture(tmp_path: Path) -> dict[str, Any]:
    root = tmp_path / "repo"
    (root / "aureon").mkdir(parents=True)
    (root / "pyproject.toml").write_bytes(b'[project]\nname = "governance-test-fixture"\nversion = "0"\n')
    for relative in _FIXTURE_FILES:
        source = SOURCE_ROOT / relative
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    decision_path = root / governance.DEFAULT_DECISION_ROOT / "governance-test-decision-001.json"
    _write_json(decision_path, _decision())
    return {
        "root": root,
        "decision_path": decision_path,
    }


@pytest.fixture(autouse=True)  # type: ignore[untyped-decorator]
def fixed_mutation_wall_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(governance, "_wall_now", lambda: NOW)


def _rewrite_decision(
    fixture: dict[str, Any],
    transform: str,
) -> dict[str, Any]:
    value = _decision()
    if transform == "wrong-owner":
        value["owner"] = "Not the named owner"
    elif transform == "unsupported-state":
        value["decision"] = "approve"
    elif transform == "changed-acknowledgement":
        value["acknowledgements"]["no_website_change"] = False
    elif transform == "v4-not-rejected":
        value["acknowledgements"]["v1_through_v4_superseded_and_rejected"] = False
    elif transform == "wrong-sentence-wording":
        value["acknowledgements"]["sentence_level_evidence_os_wording"] = (
            "One research engine. One evidence OS. Many applications."
        )
    elif transform == "wrong-validation-path":
        value["validation"]["path"] = governance.SUPERSEDED_VALIDATION_PATH.as_posix()
    elif transform == "wrong-validation-sha":
        value["validation"]["sha256"] = "0" * 64
    elif transform == "stale":
        value["decided_at"] = (NOW - timedelta(hours=24, seconds=1)).isoformat().replace("+00:00", "Z")
    elif transform == "future":
        value["decided_at"] = (
            (NOW + governance.FUTURE_TOLERANCE + timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
        )
    else:
        raise AssertionError(f"Unknown decision transform: {transform}")
    _write_json(Path(fixture["decision_path"]), value)
    return value


def _assert_rolled_back_without_receipt(
    fixture: dict[str, Any],
    before: dict[str, bytes],
    result: dict[str, Any],
) -> None:
    root = Path(fixture["root"])
    assert result["applied"] is False
    assert result["state"] == "blocked"
    assert result["rollback_verified"] is True
    assert _canonical_snapshot(root) == before
    receipt_root = root / governance.DEFAULT_RECEIPT_ROOT
    assert not receipt_root.exists() or not any(receipt_root.iterdir())


def test_corrected_decision_verifies_and_plan_is_a_read_only_full_replay(
    governance_fixture: dict[str, Any],
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])
    before = _snapshot(root)

    verification = governance.verify_investor_copy_governance_decision(
        decision_path,
        repo_root=root,
        as_of=NOW,
    )
    plan = governance.plan_investor_copy_governance_application(
        decision_path,
        repo_root=root,
        as_of=NOW,
    )

    assert verification["valid"] is True
    assert verification["approved"] is True
    assert verification["state"] == "approved"
    assert verification["canonical_mutation"] is False
    assert plan["passed"] is True
    assert plan["state"] == "pass"
    assert plan["canonical_mutation"] is False
    assert [item["path"] for item in plan["canonical_changes"]] == (governance.CANONICAL_GOVERNANCE_PATHS)
    assert plan["route_capsule_sha256"] == governance.EXPECTED_ROUTE_CAPSULE_SHA256
    assert plan["satisfied_concept_ids"] == governance.EXPECTED_SATISFIED_CONCEPT_IDS
    assert plan["policy_change"] is False
    assert plan["website_change"] is False
    assert _snapshot(root) == before


def test_decision_bound_to_superseded_original_proposal_is_rejected(
    governance_fixture: dict[str, Any],
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])
    value = _decision()
    value["proposal"] = {
        "path": governance.SUPERSEDED_PROPOSAL_PATH.as_posix(),
        "sha256": governance.SUPERSEDED_PROPOSAL_SHA256,
    }
    _write_json(decision_path, value)
    before = _snapshot(root)

    verification = governance.verify_investor_copy_governance_decision(
        decision_path,
        repo_root=root,
        as_of=NOW,
    )

    assert verification["valid"] is False
    assert verification["approved"] is False
    assert verification["blocked_codes"] == ["proposal-binding"]
    assert _snapshot(root) == before


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("transform", "expected_code"),
    [
        ("wrong-owner", "decision-owner"),
        ("unsupported-state", "decision-state"),
        ("changed-acknowledgement", "decision-boundary"),
        ("v4-not-rejected", "decision-boundary"),
        ("wrong-sentence-wording", "decision-boundary"),
        ("wrong-validation-path", "validation-binding"),
        ("wrong-validation-sha", "validation-binding"),
        ("stale", "stale-input"),
        ("future", "future-input"),
    ],
)
def test_decision_contract_rejects_wrong_owner_state_ack_path_sha_and_time(
    governance_fixture: dict[str, Any],
    transform: str,
    expected_code: str,
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])
    _rewrite_decision(governance_fixture, transform)
    before = _snapshot(root)

    verification = governance.verify_investor_copy_governance_decision(
        decision_path,
        repo_root=root,
        as_of=NOW,
    )

    assert verification["state"] == "blocked"
    assert verification["valid"] is False
    assert verification["approved"] is False
    assert verification["blocked_codes"] == [expected_code]
    assert _snapshot(root) == before


def test_decision_file_outside_controlled_direct_child_path_is_rejected(
    governance_fixture: dict[str, Any],
) -> None:
    root = Path(governance_fixture["root"])
    outside_path = root / "owner-decision.json"
    _write_json(outside_path, _decision())
    before = _snapshot(root)

    verification = governance.verify_investor_copy_governance_decision(
        outside_path,
        repo_root=root,
        as_of=NOW,
    )

    assert verification["blocked_codes"] == ["decision-path"]
    assert _snapshot(root) == before


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("mutation", "expected_code"),
    [
        ("duplicate-decision", "json"),
        ("duplicate-nested-binding", "json"),
        ("nan", "json"),
        ("bom", "serialization"),
        ("noncanonical", "serialization"),
        ("crlf", "serialization"),
    ],
)
def test_owner_decision_json_is_unambiguous_and_canonical(
    governance_fixture: dict[str, Any],
    mutation: str,
    expected_code: str,
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])
    canonical = _serialise(_decision())
    if mutation == "duplicate-decision":
        raw = canonical.replace(
            b'  "decision": "approve-exact-governance-delta",\n',
            (b'  "decision": "reject",\n  "decision": "approve-exact-governance-delta",\n'),
        )
    elif mutation == "duplicate-nested-binding":
        raw = canonical.replace(
            b'    "path": "artifacts/website-operator/',
            (
                b'    "path": "artifacts/website-operator/owner-decisions/'
                b'not-applicable.json",\n'
                b'    "path": "artifacts/website-operator/'
            ),
            1,
        )
    elif mutation == "nan":
        raw = canonical.replace(b"{\n", b'{\n  "not_a_number": NaN,\n', 1)
    elif mutation == "bom":
        raw = b"\xef\xbb\xbf" + canonical
    elif mutation == "noncanonical":
        raw = json.dumps(_decision(), separators=(",", ":")).encode("utf-8")
    elif mutation == "crlf":
        raw = canonical.replace(b"\n", b"\r\n")
    else:
        raise AssertionError(mutation)
    decision_path.write_bytes(raw)

    verification = governance.verify_investor_copy_governance_decision(
        decision_path,
        repo_root=root,
        as_of=NOW,
    )

    assert verification["valid"] is False
    assert verification["blocked_codes"] == [expected_code]


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "unsafe_name",
    [
        "different-decision.json",
        "CON.json",
        "owner-decision.JSON",
        "owner decision.json",
        "owner-decision.json.",
        "owner-decision.json ",
        "owner:decision.json",
    ],
)
def test_owner_decision_filename_is_exact_ascii_and_matches_decision_id(
    governance_fixture: dict[str, Any],
    unsafe_name: str,
) -> None:
    root = Path(governance_fixture["root"])
    unsafe = root / governance.DEFAULT_DECISION_ROOT / unsafe_name
    if ":" not in unsafe_name and not unsafe_name.endswith((".", " ")):
        try:
            unsafe.write_bytes(_serialise(_decision()))
        except OSError:
            pass

    verification = governance.verify_investor_copy_governance_decision(
        unsafe,
        repo_root=root,
        as_of=NOW,
    )

    assert verification["blocked_codes"] == ["decision-path"]


@pytest.mark.skipif(os.name != "nt", reason="NTFS alternate data streams are Windows-only")  # type: ignore[untyped-decorator]
def test_ntfs_alternate_data_stream_owner_decision_is_rejected(
    governance_fixture: dict[str, Any],
) -> None:
    root = Path(governance_fixture["root"])
    base = root / governance.DEFAULT_DECISION_ROOT / "cover"
    base.write_bytes(b"cover")
    ads = Path(f"{base}:governance-test-decision-001.json")
    ads.write_bytes(_serialise(_decision()))

    verification = governance.verify_investor_copy_governance_decision(
        ads,
        repo_root=root,
        as_of=NOW,
    )

    assert verification["blocked_codes"] == ["decision-path"]


def test_decision_snapshot_cannot_pair_approve_parse_with_reject_file_hash(
    governance_fixture: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])
    before = _canonical_snapshot(root)
    original_snapshot = governance._snapshot_json
    toggled = {"done": False}

    def snapshot_then_reject(
        path: Path,
        *,
        label: str,
        canonical: bool = False,
    ) -> Any:
        snapshot = original_snapshot(path, label=label, canonical=canonical)
        if label == "Owner decision" and not toggled["done"]:
            toggled["done"] = True
            _write_json(decision_path, _decision(state="reject"))
        return snapshot

    monkeypatch.setattr(governance, "_snapshot_json", snapshot_then_reject)

    result = governance.apply_investor_copy_governance_delta(
        decision_path,
        apply=True,
        repo_root=root,
    )

    assert result["applied"] is False
    assert result["blocked_codes"] == ["decision-not-approved"]
    assert _canonical_snapshot(root) == before
    assert not (root / governance.DEFAULT_RECEIPT_ROOT).exists()


def test_controlled_decision_ancestor_reparse_is_fail_closed(
    governance_fixture: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])
    marked = (root / "artifacts/website-operator").absolute()
    original = governance._is_link_or_reparse

    def mark_ancestor(path: Path) -> bool:
        return path.absolute() == marked or original(path)

    monkeypatch.setattr(governance, "_is_link_or_reparse", mark_ancestor)

    verification = governance.verify_investor_copy_governance_decision(
        decision_path,
        repo_root=root,
        as_of=NOW,
    )

    assert verification["blocked_codes"] == ["decision-root"]


def test_approved_decision_requires_explicit_apply_and_changes_nothing_by_default(
    governance_fixture: dict[str, Any],
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])
    before = _snapshot(root)

    result = governance.apply_investor_copy_governance_delta(
        decision_path,
        repo_root=root,
        as_of=NOW,
    )

    assert result["applied"] is False
    assert result["state"] == "blocked"
    assert result["blocked_codes"] == ["explicit-apply-required"]
    assert result["canonical_changes"] == []
    assert result["receipt_path"] == ""
    assert _snapshot(root) == before


def test_reject_decision_is_valid_but_cannot_plan_or_apply(
    governance_fixture: dict[str, Any],
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])
    _write_json(decision_path, _decision(state="reject"))
    before = _snapshot(root)

    verification = governance.verify_investor_copy_governance_decision(
        decision_path,
        repo_root=root,
        as_of=NOW,
    )
    plan = governance.plan_investor_copy_governance_application(
        decision_path,
        repo_root=root,
        as_of=NOW,
    )
    result = governance.apply_investor_copy_governance_delta(
        decision_path,
        apply=True,
        repo_root=root,
    )

    assert verification["valid"] is True
    assert verification["approved"] is False
    assert verification["state"] == "rejected"
    assert plan["passed"] is False
    assert plan["blocked_codes"] == ["decision-reject"]
    assert result["applied"] is False
    assert result["state"] == "rejected"
    assert result["blocked_codes"] == ["decision-reject"]
    assert _snapshot(root) == before


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("drift_kind", "expected_code"),
    [
        ("source", "source-drift"),
        ("canonical", "canonical-drift"),
    ],
)
def test_source_or_canonical_drift_blocks_before_any_governance_write(
    governance_fixture: dict[str, Any],
    drift_kind: str,
    expected_code: str,
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])
    if drift_kind == "source":
        source = root / "website/projects/index.html"
        source.write_bytes(source.read_bytes() + b"\n<!-- isolated test drift -->\n")
    else:
        register_path = root / governance.REGISTER_PATH
        register = json.loads(register_path.read_text(encoding="utf-8"))
        register["isolated_test_drift"] = True
        _write_json(register_path, register)
    before = _snapshot(root)

    plan = governance.plan_investor_copy_governance_application(
        decision_path,
        repo_root=root,
        as_of=NOW,
    )

    assert plan["passed"] is False
    assert plan["blocked_codes"] == [expected_code]
    assert plan["canonical_mutation"] is False
    assert _snapshot(root) == before


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("snapshot_label", "relative", "expected_code"),
    [
        (
            "Governance proposal",
            governance.DEFAULT_PROPOSAL_PATH,
            "approval-race",
        ),
        (
            "Design-cycle receipt",
            governance.EXPECTED_DESIGN_RECEIPT_PATH,
            "preflight-race",
        ),
        (
            "Claim register",
            governance.REGISTER_PATH,
            "preflight-race",
        ),
    ],
)
def test_bound_json_snapshot_change_is_detected_before_plan_passes(
    governance_fixture: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    snapshot_label: str,
    relative: Path,
    expected_code: str,
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])
    target = root / relative
    original_snapshot = governance._snapshot_json
    toggled = {"done": False}

    def snapshot_then_change(
        path: Path,
        *,
        label: str,
        canonical: bool = False,
    ) -> Any:
        snapshot = original_snapshot(path, label=label, canonical=canonical)
        if label == snapshot_label and not toggled["done"]:
            toggled["done"] = True
            changed = copy.deepcopy(snapshot.value)
            changed["external_test_change"] = True
            _write_json(target, changed)
        return snapshot

    monkeypatch.setattr(governance, "_snapshot_json", snapshot_then_change)

    plan = governance.plan_investor_copy_governance_application(
        decision_path,
        repo_root=root,
        as_of=NOW,
    )

    assert plan["passed"] is False
    assert plan["blocked_codes"] == [expected_code]
    assert plan["canonical_mutation"] is False


def test_exact_three_file_fixture_apply_passes_real_audits_and_receipt_is_write_once(
    governance_fixture: dict[str, Any],
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])
    before = _snapshot(root)

    result = governance.apply_investor_copy_governance_delta(
        decision_path,
        apply=True,
        repo_root=root,
    )

    assert result["applied"] is True
    assert result["state"] == "applied-governance-only"
    assert [item["path"] for item in result["canonical_changes"]] == (governance.CANONICAL_GOVERNANCE_PATHS)
    expected_after = {
        governance.REGISTER_PATH.as_posix(): governance.EXPECTED_REGISTER_AFTER_SHA256,
        governance.FEEDBACK_PATH.as_posix(): governance.EXPECTED_FEEDBACK_AFTER_SHA256,
        governance.BRIEF_PATH.as_posix(): governance.EXPECTED_BRIEF_AFTER_SHA256,
    }
    assert {
        relative: _sha256(root / relative) for relative in governance.CANONICAL_GOVERNANCE_PATHS
    } == expected_after
    applied_register = json.loads((root / governance.REGISTER_PATH).read_text(encoding="utf-8"))
    evidence_os_claims = [
        item for item in applied_register["claims"] if item.get("id") == governance.EXPECTED_SURFACE_CLAIM_ID
    ]
    assert len(evidence_os_claims) == 1
    evidence_os_claim = evidence_os_claims[0]
    assert evidence_os_claim["permitted_wording"].count(governance.EXPECTED_SURFACE_WORDING) == 1
    assert evidence_os_claim["source"]["evidence_texts"].count(governance.EXPECTED_SURFACE_WORDING) == 1
    assert governance._json_sha256(evidence_os_claim) == governance.EXPECTED_SURFACE_RECORD_AFTER_SHA256

    receipt_path = root / result["receipt_path"]
    assert receipt_path.is_file()
    assert stat.S_ISREG(receipt_path.stat().st_mode)
    assert receipt_path.stat().st_nlink == 1
    assert _sha256(receipt_path) == result["receipt_sha256"]
    receipt_bytes = receipt_path.read_bytes()
    receipt = json.loads(receipt_bytes.decode("utf-8"))
    assert receipt["audits"]["claim_audit_passed"] is True
    assert receipt["audits"]["stakeholder_feedback_audit_passed"] is True
    assert receipt["audits"]["design_audit_passed"] is True
    assert receipt["policy_change"] is False
    assert receipt["website_change"] is False
    assert receipt["release_eligible"] is False
    assert b"permitted_wording" not in receipt_bytes
    assert b"evidence_texts" not in receipt_bytes
    assert b"One research engine" not in receipt_bytes
    assert b"Aureon is a research-led systems company" not in receipt_bytes

    after = _snapshot(root)
    changed_existing = {relative for relative, value in before.items() if after.get(relative) != value}
    new_files = set(after) - set(before)
    assert changed_existing == set(governance.CANONICAL_GOVERNANCE_PATHS)
    assert new_files == {result["receipt_path"]}

    with pytest.raises(
        governance.InvestorCopyGovernanceError,
        match="Refusing to overwrite immutable application evidence",
    ) as exc_info:
        governance._write_immutable_receipt(receipt, root=root)
    assert exc_info.value.code == "receipt-exists"
    assert receipt_path.read_bytes() == receipt_bytes


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "failure_after_replace", [1, 2, 3]
)
@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "exception_type", [RuntimeError, TypeError]
)
def test_runtime_or_type_failure_after_each_replace_restores_all_three_files(
    governance_fixture: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    failure_after_replace: int,
    exception_type: type[Exception],
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])
    before = _canonical_snapshot(root)
    original_replace = governance._replace_file
    calls = 0
    injected = False

    def replace_then_fail(
        source: Path,
        destination: Path,
        **kwargs: Any,
    ) -> None:
        nonlocal calls, injected
        original_replace(source, destination, **kwargs)
        if not injected and destination.relative_to(root).as_posix() in (
            governance.CANONICAL_GOVERNANCE_PATHS
        ):
            calls += 1
            if calls == failure_after_replace:
                injected = True
                raise exception_type(f"isolated failure after replace {calls}")

    monkeypatch.setattr(governance, "_replace_file", replace_then_fail)

    result = governance.apply_investor_copy_governance_delta(
        decision_path,
        apply=True,
        repo_root=root,
    )

    assert result["blocked_codes"] == ["transaction-error"]
    _assert_rolled_back_without_receipt(governance_fixture, before, result)


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "exception_type", [RuntimeError, TypeError]
)
def test_runtime_or_type_failure_after_post_audit_restores_all_three_files(
    governance_fixture: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    exception_type: type[Exception],
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])
    before = _canonical_snapshot(root)
    original_post_audit = governance._post_write_validate

    def audit_then_fail(*args: Any, **kwargs: Any) -> Any:
        original_post_audit(*args, **kwargs)
        raise exception_type("isolated failure after post-write audits")

    monkeypatch.setattr(governance, "_post_write_validate", audit_then_fail)

    result = governance.apply_investor_copy_governance_delta(
        decision_path,
        apply=True,
        repo_root=root,
    )

    assert result["blocked_codes"] == ["transaction-error"]
    _assert_rolled_back_without_receipt(governance_fixture, before, result)


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "exception_type", [RuntimeError, TypeError]
)
def test_failure_after_exact_receipt_creation_recovers_as_committed(
    governance_fixture: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    exception_type: type[Exception],
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])
    original_write_receipt = governance._write_immutable_receipt

    def write_then_fail(*args: Any, **kwargs: Any) -> Path:
        original_write_receipt(*args, **kwargs)
        raise exception_type("isolated failure after receipt creation")

    monkeypatch.setattr(governance, "_write_immutable_receipt", write_then_fail)

    result = governance.apply_investor_copy_governance_delta(
        decision_path,
        apply=True,
        repo_root=root,
    )

    assert result["applied"] is True
    assert result["state"] == "applied-governance-only"
    assert result["blocked_codes"] == []
    assert _sha256(root / governance.REGISTER_PATH) == (governance.EXPECTED_REGISTER_AFTER_SHA256)
    assert _sha256(root / governance.FEEDBACK_PATH) == (governance.EXPECTED_FEEDBACK_AFTER_SHA256)
    assert _sha256(root / governance.BRIEF_PATH) == (governance.EXPECTED_BRIEF_AFTER_SHA256)
    assert (root / result["receipt_path"]).is_file()
    assert (root / result["recovery_receipt_path"]).is_file()
    assert not (root / governance.TRANSACTION_ROOT).exists()
    assert not (root / governance.TRANSACTION_LOCK_PATH).exists()


def _run_crash_apply(
    root: Path,
    decision_path: Path,
    point: str,
) -> subprocess.CompletedProcess[str]:
    script = textwrap.dedent(
        """
        import os
        import sys
        from datetime import UTC, datetime
        from pathlib import Path

        import aureon.operator.design_investor_copy_governance as governance

        root = Path(sys.argv[1])
        decision = Path(sys.argv[2])
        point = sys.argv[3]
        fixed_now = datetime(2026, 7, 30, 10, 0, tzinfo=UTC)
        governance._wall_now = lambda: fixed_now

        if point.startswith("replace-"):
            wanted = int(point.split("-", 1)[1])
            original = governance._replace_file
            calls = {"count": 0}

            def replace_then_exit(source, destination, **kwargs):
                original(source, destination, **kwargs)
                try:
                    relative = destination.relative_to(root).as_posix()
                except ValueError:
                    return
                if relative in governance.CANONICAL_GOVERNANCE_PATHS:
                    calls["count"] += 1
                    if calls["count"] == wanted:
                        os._exit(91)

            governance._replace_file = replace_then_exit
        elif point == "journal-before-publish":
            original = governance.os.replace

            def replace_journal_then_exit(source, destination):
                if (
                    Path(destination) == root / governance.TRANSACTION_JOURNAL_PATH
                    and Path(source).name.startswith(".journal-")
                ):
                    os._exit(95)
                original(source, destination)

            governance.os.replace = replace_journal_then_exit
        elif point == "journal-partial":
            original = governance._write_exclusive_bytes

            def partial_journal_then_exit(path, value):
                if path.name.startswith(".journal-"):
                    with path.open("wb") as stream:
                        stream.write(b'{"partial":')
                        stream.flush()
                        os.fsync(stream.fileno())
                    os._exit(96)
                original(path, value)

            governance._write_exclusive_bytes = partial_journal_then_exit
        elif point.startswith("prepare-file-"):
            wanted = int(point.rsplit("-", 1)[1])
            original = governance._write_exclusive_bytes
            calls = {"count": 0}

            def prepare_file_then_exit(path, value):
                original(path, value)
                if (
                    path.parent == root / governance.TRANSACTION_ROOT
                    and not path.name.startswith(".journal-")
                ):
                    calls["count"] += 1
                    if calls["count"] == wanted:
                        os._exit(97)

            governance._write_exclusive_bytes = prepare_file_then_exit
        elif point == "validated":
            original = governance._set_transaction_state

            def state_then_exit(root_arg, journal, state, **kwargs):
                result = original(root_arg, journal, state, **kwargs)
                if state == "VALIDATED":
                    os._exit(91)
                return result

            governance._set_transaction_state = state_then_exit
        elif point == "audit":
            original = governance._post_write_validate

            def audit_then_exit(*args, **kwargs):
                original(*args, **kwargs)
                os._exit(91)

            governance._post_write_validate = audit_then_exit
        elif point == "receipt":
            original = governance._write_immutable_receipt

            def receipt_then_exit(*args, **kwargs):
                original(*args, **kwargs)
                os._exit(91)

            governance._write_immutable_receipt = receipt_then_exit
        elif point in {"receipt-before-link", "receipt-link"}:
            original = governance.os.link

            def application_link_then_exit(source, destination, *args, **kwargs):
                is_application = (
                    Path(destination).parent
                    == root / governance.DEFAULT_RECEIPT_ROOT
                )
                if is_application and point == "receipt-before-link":
                    os._exit(98)
                original(source, destination, *args, **kwargs)
                if is_application:
                    os._exit(93)

            governance.os.link = application_link_then_exit
        else:
            raise SystemExit(88)

        governance.apply_investor_copy_governance_delta(
            decision,
            apply=True,
            repo_root=root,
        )
        raise SystemExit(89)
        """
    )
    return subprocess.run(
        [sys.executable, "-c", script, str(root), str(decision_path), point],
        cwd=SOURCE_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _run_crash_recovery(
    root: Path,
    point: str = "after-first-restore",
    wanted: int = 1,
) -> subprocess.CompletedProcess[str]:
    script = textwrap.dedent(
        """
        import os
        import sys
        from datetime import UTC, datetime
        from pathlib import Path

        import aureon.operator.design_investor_copy_governance as governance

        root = Path(sys.argv[1])
        point = sys.argv[2]
        wanted = int(sys.argv[3])
        fixed_now = datetime(2026, 7, 30, 10, 0, tzinfo=UTC)
        governance._wall_now = lambda: fixed_now
        if point == "after-first-restore":
            original = governance._replace_file
            calls = {"count": 0}

            def replace_then_exit(source, destination, **kwargs):
                original(source, destination, **kwargs)
                try:
                    relative = destination.relative_to(root).as_posix()
                except ValueError:
                    return
                if relative in governance.CANONICAL_GOVERNANCE_PATHS:
                    calls["count"] += 1
                    if calls["count"] == 1:
                        os._exit(92)

            governance._replace_file = replace_then_exit
        elif point == "partial-stage":
            original = governance._prepare_fixed_stage
            calls = {"count": 0}

            def partial_stage_then_exit(source, stage, **kwargs):
                calls["count"] += 1
                if calls["count"] == wanted:
                    stage.write_bytes(b"partial-journal-owned-stage")
                    os._exit(94)
                original(source, stage, **kwargs)

            governance._prepare_fixed_stage = partial_stage_then_exit
        elif point in {"recovery-receipt-before-link", "recovery-receipt-link"}:
            original = governance.os.link

            def recovery_link_then_exit(source, destination, *args, **kwargs):
                is_recovery = (
                    Path(destination).parent
                    == root / governance.DEFAULT_RECOVERY_RECEIPT_ROOT
                )
                if is_recovery and point == "recovery-receipt-before-link":
                    os._exit(99)
                original(source, destination, *args, **kwargs)
                if is_recovery:
                    os._exit(100)

            governance.os.link = recovery_link_then_exit
        else:
            raise SystemExit(88)
        governance.recover_incomplete_investor_copy_governance_transaction(
            repo_root=root,
        )
        raise SystemExit(89)
        """
    )
    return subprocess.run(
        [sys.executable, "-c", script, str(root), point, str(wanted)],
        cwd=SOURCE_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _assert_no_transaction_debris(root: Path) -> None:
    assert not (root / governance.TRANSACTION_ROOT).exists()
    assert not (root / governance.TRANSACTION_LOCK_PATH).exists()
    assert not list((root / "data/website_operator").glob("*.governance.*.tmp"))
    for relative in (
        governance.DEFAULT_RECEIPT_ROOT,
        governance.DEFAULT_RECOVERY_RECEIPT_ROOT,
    ):
        receipt_root = root / relative
        if receipt_root.exists():
            assert not list(receipt_root.glob(".*.governance.*.tmp"))
            assert all(path.stat().st_nlink == 1 for path in receipt_root.iterdir())


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "crash_point",
    ["replace-1", "replace-2", "replace-3", "audit", "validated"],
)
def test_process_exit_before_commit_marker_is_durably_rolled_back(
    governance_fixture: dict[str, Any],
    crash_point: str,
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])
    before = _canonical_snapshot(root)

    crashed = _run_crash_apply(root, decision_path, crash_point)

    assert crashed.returncode == 91, (crashed.stdout, crashed.stderr)
    assert (root / governance.TRANSACTION_ROOT).is_dir()
    assert (root / governance.TRANSACTION_LOCK_PATH).is_file()
    blocked_plan = governance.plan_investor_copy_governance_application(
        decision_path,
        repo_root=root,
        as_of=NOW,
    )
    assert blocked_plan["blocked_codes"] == ["transaction-recovery-required"]

    recovered = governance.recover_incomplete_investor_copy_governance_transaction(
        repo_root=root,
    )

    assert recovered["state"] == "recovered"
    assert recovered["outcome"] == "rolled-back"
    assert recovered["rollback_verified"] is True
    assert _canonical_snapshot(root) == before
    assert (root / recovered["recovery_receipt_path"]).is_file()
    application_root = root / governance.DEFAULT_RECEIPT_ROOT
    assert not application_root.exists() or not any(application_root.iterdir())
    _assert_no_transaction_debris(root)

    recovery_receipt = (root / recovered["recovery_receipt_path"]).read_bytes()
    second = governance.recover_incomplete_investor_copy_governance_transaction(
        repo_root=root,
    )
    assert second["outcome"] == "absent"
    assert (root / recovered["recovery_receipt_path"]).read_bytes() == recovery_receipt


def test_process_exit_after_exact_receipt_is_durably_completed(
    governance_fixture: dict[str, Any],
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])

    crashed = _run_crash_apply(root, decision_path, "receipt")

    assert crashed.returncode == 91, (crashed.stdout, crashed.stderr)
    recovered = governance.recover_incomplete_investor_copy_governance_transaction(
        repo_root=root,
    )

    assert recovered["applied"] is True
    assert recovered["outcome"] == "committed"
    assert recovered["state"] == "applied-governance-only"
    assert _sha256(root / governance.REGISTER_PATH) == (governance.EXPECTED_REGISTER_AFTER_SHA256)
    assert _sha256(root / governance.FEEDBACK_PATH) == (governance.EXPECTED_FEEDBACK_AFTER_SHA256)
    assert _sha256(root / governance.BRIEF_PATH) == (governance.EXPECTED_BRIEF_AFTER_SHA256)
    assert _sha256(root / recovered["receipt_path"]) == recovered["receipt_sha256"]
    assert (root / recovered["recovery_receipt_path"]).is_file()
    _assert_no_transaction_debris(root)


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("point", "returncode"),
    [
        ("journal-before-publish", 95),
        ("journal-partial", 96),
        *[(f"prepare-file-{index}", 97) for index in range(1, 8)],
    ],
)
def test_process_exit_during_durable_preparation_is_safely_aborted(
    governance_fixture: dict[str, Any],
    point: str,
    returncode: int,
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])
    before = _canonical_snapshot(root)

    crashed = _run_crash_apply(root, decision_path, point)
    assert crashed.returncode == returncode, (crashed.stdout, crashed.stderr)

    recovered = governance.recover_incomplete_investor_copy_governance_transaction(
        repo_root=root,
    )

    assert recovered["state"] != "blocked"
    assert recovered["applied"] is False
    assert _canonical_snapshot(root) == before
    _assert_no_transaction_debris(root)


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("point", "returncode", "expected_outcome"),
    [
        ("receipt-before-link", 98, "rolled-back"),
        ("receipt-link", 93, "committed"),
    ],
)
def test_application_receipt_publish_window_has_no_hardlink_alias(
    governance_fixture: dict[str, Any],
    point: str,
    returncode: int,
    expected_outcome: str,
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])
    before = _canonical_snapshot(root)

    crashed = _run_crash_apply(root, decision_path, point)
    assert crashed.returncode == returncode, (crashed.stdout, crashed.stderr)

    recovered = governance.recover_incomplete_investor_copy_governance_transaction(
        repo_root=root,
    )

    assert recovered["outcome"] == expected_outcome
    if expected_outcome == "committed":
        receipt = root / recovered["receipt_path"]
        assert recovered["applied"] is True
        assert receipt.stat().st_nlink == 1
    else:
        assert recovered["applied"] is False
        assert _canonical_snapshot(root) == before
    _assert_no_transaction_debris(root)


def test_process_exit_during_rollback_is_idempotently_recovered(
    governance_fixture: dict[str, Any],
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])
    before = _canonical_snapshot(root)
    initial_crash = _run_crash_apply(root, decision_path, "replace-3")
    assert initial_crash.returncode == 91

    recovery_crash = _run_crash_recovery(root)

    assert recovery_crash.returncode == 92, (
        recovery_crash.stdout,
        recovery_crash.stderr,
    )
    assert (root / governance.TRANSACTION_ROOT).is_dir()
    blocked = governance.verify_investor_copy_governance_decision(
        decision_path,
        repo_root=root,
        as_of=NOW,
    )
    assert blocked["blocked_codes"] == ["transaction-recovery-required"]

    recovered = governance.recover_incomplete_investor_copy_governance_transaction(
        repo_root=root,
    )

    assert recovered["outcome"] == "rolled-back"
    assert recovered["rollback_verified"] is True
    assert _canonical_snapshot(root) == before
    _assert_no_transaction_debris(root)


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "wanted",
    [1, 2, 3],
)
def test_partial_disposable_rollback_stage_is_rebuilt_idempotently(
    governance_fixture: dict[str, Any],
    wanted: int,
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])
    before = _canonical_snapshot(root)
    assert _run_crash_apply(root, decision_path, "replace-3").returncode == 91

    crashed = _run_crash_recovery(root, "partial-stage", wanted)
    assert crashed.returncode == 94, (crashed.stdout, crashed.stderr)

    recovered = governance.recover_incomplete_investor_copy_governance_transaction(
        repo_root=root,
    )

    assert recovered["outcome"] == "rolled-back"
    assert recovered["rollback_verified"] is True
    assert _canonical_snapshot(root) == before
    _assert_no_transaction_debris(root)


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("point", "returncode"),
    [
        ("recovery-receipt-before-link", 99),
        ("recovery-receipt-link", 100),
    ],
)
def test_recovery_receipt_publish_window_has_no_hardlink_alias(
    governance_fixture: dict[str, Any],
    point: str,
    returncode: int,
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])
    before = _canonical_snapshot(root)
    assert _run_crash_apply(root, decision_path, "replace-3").returncode == 91

    crashed = _run_crash_recovery(root, point)
    assert crashed.returncode == returncode, (crashed.stdout, crashed.stderr)

    recovered = governance.recover_incomplete_investor_copy_governance_transaction(
        repo_root=root,
    )

    assert recovered["outcome"] == "rolled-back"
    recovery_receipt = root / recovered["recovery_receipt_path"]
    assert recovery_receipt.stat().st_nlink == 1
    assert _canonical_snapshot(root) == before
    _assert_no_transaction_debris(root)


def test_journal_snapshot_race_blocks_state_overwrite(
    governance_fixture: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])
    assert _run_crash_apply(root, decision_path, "replace-1").returncode == 91
    journal_path = root / governance.TRANSACTION_JOURNAL_PATH
    original_snapshot = governance._snapshot_json
    toggled = {"done": False}

    def snapshot_then_change(
        path: Path,
        *,
        label: str,
        canonical: bool = False,
    ) -> Any:
        snapshot = original_snapshot(path, label=label, canonical=canonical)
        if label == "Transaction journal" and not toggled["done"]:
            toggled["done"] = True
            changed = copy.deepcopy(snapshot.value)
            changed["external_test_change"] = True
            _write_json(journal_path, changed)
        return snapshot

    monkeypatch.setattr(governance, "_snapshot_json", snapshot_then_change)

    recovered = governance.recover_incomplete_investor_copy_governance_transaction(
        repo_root=root,
    )

    assert recovered["state"] == "blocked"
    assert recovered["blocked_codes"] == ["transaction-journal-race"]
    assert (root / governance.TRANSACTION_ROOT).is_dir()


def test_recovery_refuses_canonical_ancestor_reparse_without_external_write(
    governance_fixture: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])
    assert _run_crash_apply(root, decision_path, "replace-1").returncode == 91
    after_crash = _canonical_snapshot(root)
    marked = (root / "data/website_operator").absolute()
    original = governance._is_link_or_reparse

    def mark_ancestor(path: Path) -> bool:
        return path.absolute() == marked or original(path)

    monkeypatch.setattr(governance, "_is_link_or_reparse", mark_ancestor)

    recovered = governance.recover_incomplete_investor_copy_governance_transaction(
        repo_root=root,
    )

    assert recovered["state"] == "blocked"
    assert recovered["blocked_codes"] == ["transaction-journal"]
    assert _canonical_snapshot(root) == after_crash


def test_mutating_apply_rejects_historical_time_override(
    governance_fixture: dict[str, Any],
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])
    before = _snapshot(root)

    result = governance.apply_investor_copy_governance_delta(
        decision_path,
        apply=True,
        repo_root=root,
        as_of=NOW,
    )

    assert result["blocked_codes"] == ["apply-time-override-forbidden"]
    assert _snapshot(root) == before


def test_decision_before_v5_validation_cannot_verify_plan_or_apply(
    governance_fixture: dict[str, Any],
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])
    value = _decision()
    value["decided_at"] = "2026-07-30T09:47:00Z"
    _write_json(decision_path, value)

    verification = governance.verify_investor_copy_governance_decision(
        decision_path,
        repo_root=root,
        as_of=NOW,
    )
    plan = governance.plan_investor_copy_governance_application(
        decision_path,
        repo_root=root,
        as_of=NOW,
    )
    result = governance.apply_investor_copy_governance_delta(
        decision_path,
        apply=True,
        repo_root=root,
    )

    assert verification["blocked_codes"] == ["decision-before-artifacts"]
    assert plan["blocked_codes"] == ["decision-before-artifacts"]
    assert result["blocked_codes"] == ["decision-before-artifacts"]


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("proposal_path", "proposal_sha256"),
    [
        (
            governance.SUPERSEDED_PROPOSAL_PATH,
            governance.SUPERSEDED_PROPOSAL_SHA256,
        ),
        (
            governance.SUPERSEDED_V2_PROPOSAL_PATH,
            governance.SUPERSEDED_V2_PROPOSAL_SHA256,
        ),
        (
            governance.SUPERSEDED_V3_PROPOSAL_PATH,
            governance.SUPERSEDED_V3_PROPOSAL_SHA256,
        ),
        (
            governance.SUPERSEDED_V4_PROPOSAL_PATH,
            governance.SUPERSEDED_V4_PROPOSAL_SHA256,
        ),
    ],
)
def test_every_superseded_proposal_generation_is_rejected(
    governance_fixture: dict[str, Any],
    proposal_path: Path,
    proposal_sha256: str,
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])
    value = _decision()
    value["proposal"] = {
        "path": proposal_path.as_posix(),
        "sha256": proposal_sha256,
    }
    _write_json(decision_path, value)

    verification = governance.verify_investor_copy_governance_decision(
        decision_path,
        repo_root=root,
        as_of=NOW,
    )

    assert verification["blocked_codes"] == ["proposal-binding"]


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("validation_path", "validation_sha256"),
    [
        (
            governance.SUPERSEDED_VALIDATION_PATH,
            governance.SUPERSEDED_VALIDATION_SHA256,
        ),
        (
            governance.SUPERSEDED_V2_VALIDATION_PATH,
            governance.SUPERSEDED_V2_VALIDATION_SHA256,
        ),
        (
            governance.SUPERSEDED_V3_VALIDATION_PATH,
            governance.SUPERSEDED_V3_VALIDATION_SHA256,
        ),
        (
            governance.SUPERSEDED_V4_VALIDATION_PATH,
            governance.SUPERSEDED_V4_VALIDATION_SHA256,
        ),
    ],
)
def test_every_superseded_validation_generation_is_rejected(
    governance_fixture: dict[str, Any],
    validation_path: Path,
    validation_sha256: str,
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])
    value = _decision()
    value["validation"] = {
        "path": validation_path.as_posix(),
        "sha256": validation_sha256,
    }
    _write_json(decision_path, value)

    verification = governance.verify_investor_copy_governance_decision(
        decision_path,
        repo_root=root,
        as_of=NOW,
    )

    assert verification["blocked_codes"] == ["validation-binding"]


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "drift_index",
    [0, 1, 2],
)
def test_commit_cas_preserves_foreign_drift_and_rolls_back_owned_outputs(
    governance_fixture: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    drift_index: int,
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])
    before = _canonical_snapshot(root)
    target_relative = governance.CANONICAL_GOVERNANCE_PATHS[drift_index]
    target = root / target_relative
    foreign = target.read_bytes() + b"\nforeign concurrent bytes\n"
    original = governance._replace_file
    calls = {"count": 0}

    def drift_before_replace(
        source: Path,
        destination: Path,
        **kwargs: Any,
    ) -> None:
        try:
            relative = destination.relative_to(root).as_posix()
        except ValueError:
            relative = ""
        if relative in governance.CANONICAL_GOVERNANCE_PATHS and calls["count"] == drift_index:
            destination.write_bytes(foreign)
            calls["count"] += 1
        elif relative in governance.CANONICAL_GOVERNANCE_PATHS:
            calls["count"] += 1
        original(source, destination, **kwargs)

    monkeypatch.setattr(governance, "_replace_file", drift_before_replace)

    result = governance.apply_investor_copy_governance_delta(
        decision_path,
        apply=True,
        repo_root=root,
    )

    assert result["applied"] is False
    assert "commit-cas-mismatch" in result["blocked_codes"]
    assert "concurrent-drift-preserved" in result["blocked_codes"]
    assert result["concurrent_drift_preserved_paths"] == [target_relative]
    assert target.read_bytes() == foreign
    for relative, original_bytes in before.items():
        if relative != target_relative:
            assert (root / relative).read_bytes() == original_bytes
    assert (root / governance.TRANSACTION_ROOT).is_dir()
    assert not (root / governance.TRANSACTION_LOCK_PATH).exists()


def test_lock_release_failure_is_not_reported_as_plain_success(
    governance_fixture: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])
    original_release = governance._release_transaction_lock
    monkeypatch.setattr(governance, "_release_transaction_lock", lambda *_: False)

    result = governance.apply_investor_copy_governance_delta(
        decision_path,
        apply=True,
        repo_root=root,
    )

    assert result["applied"] is True
    assert result["state"] == "applied-governance-maintenance-required"
    assert result["blocked_codes"] == ["transaction-lock-release-failed"]
    assert result["transaction_lock_released"] is False
    assert result["transaction_journal_cleaned"] is False
    assert (root / governance.TRANSACTION_ROOT).is_dir()
    assert (root / governance.TRANSACTION_LOCK_PATH).is_file()

    monkeypatch.setattr(governance, "_release_transaction_lock", original_release)
    recovered = governance._recover_transaction(
        root,
        current=NOW,
        allow_current_pid=True,
    )
    assert recovered["applied"] is True
    assert recovered["blocked_codes"] == []
    _assert_no_transaction_debris(root)


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "guarded_relative",
    [
        governance.SUPERSEDED_V2_PROPOSAL_PATH,
        governance.SUPERSEDED_V3_VALIDATION_PATH,
        governance.SUPERSEDED_V4_PROPOSAL_PATH,
        governance.EXPECTED_DESIGN_RECEIPT_PATH,
        governance.EXPECTED_PROJECTS_SOURCE_PATH,
        governance.EXPECTED_COMPANY_PLATFORM_PATH,
    ],
)
def test_commit_window_drift_in_every_extended_guard_blocks_before_write(
    governance_fixture: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    guarded_relative: Path,
) -> None:
    root = Path(governance_fixture["root"])
    decision_path = Path(governance_fixture["decision_path"])
    before = _canonical_snapshot(root)
    guarded = root / guarded_relative
    original_value = guarded.read_bytes()
    original_prepare = governance._prepare_transaction_journal

    def prepare_then_drift(*args: Any, **kwargs: Any) -> dict[str, Any]:
        journal = original_prepare(*args, **kwargs)
        guarded.write_bytes(original_value + b"\ncommit-window-drift\n")
        return journal

    monkeypatch.setattr(
        governance,
        "_prepare_transaction_journal",
        prepare_then_drift,
    )

    result = governance.apply_investor_copy_governance_delta(
        decision_path,
        apply=True,
        repo_root=root,
    )

    assert result["applied"] is False
    assert result["blocked_codes"] == ["commit-cas-mismatch"]
    assert result["rollback_verified"] is True
    assert _canonical_snapshot(root) == before
    assert guarded.read_bytes() == original_value + b"\ncommit-window-drift\n"
    _assert_no_transaction_debris(root)
