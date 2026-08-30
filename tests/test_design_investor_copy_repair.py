from __future__ import annotations

import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

import aureon.operator.design_investor_copy_repair as repair
from aureon.operator.design_investor_copy_quality import (
    NON_AUTHORITATIVE_AUTHORITY as COPY_AUDIT_AUTHORITY,
)

NOW = datetime(2026, 7, 30, 8, 0, tzinfo=UTC)
ROUTE = "/funding/investor-deck/"
HTML_PATH = "funding/investor-deck/index.html"
TASK_ID = "DESIGN-COPY-001"


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _html(body: str) -> str:
    return (
        "<!doctype html><html><head>"
        "<title>Aureon Investor Evidence Platform</title>"
        '<meta name="description" content="A research-led systems company '
        "connecting controlled evidence, accountable delivery and investor-ready "
        'public research.">'
        f"</head><body><h1>Research-led systems company</h1><p>{body}</p></body></html>"
    )


def _policy(*, refresh_by: datetime) -> dict[str, Any]:
    return {
        "schema": "aureon.investor-copy-quality-policy.v1",
        "policy_id": "aureon-investor-copy-quality-test",
        "issued_at": "2026-07-30T00:00:00Z",
        "refresh_by": refresh_by.isoformat().replace("+00:00", "Z"),
        "authority": dict(COPY_AUDIT_AUTHORITY),
        "snapshot_max_age_days": 14,
        "routes": [
            {
                "route": ROUTE,
                "path": HTML_PATH,
                "rule_ids": [
                    "hype-language",
                    "meta-description",
                    "page-title",
                    "single-h1",
                    "static-operating-count",
                ],
                "required_concept_groups": [
                    {
                        "concept_id": "commercial-wedge",
                        "severity": "blocker",
                        "alternatives": ["evidence os"],
                    }
                ],
            }
        ],
    }


def _task() -> dict[str, Any]:
    return {
        "id": TASK_ID,
        "owner": "technical-editor",
        "title": "Remove investor-copy policy blockers from one bounded route",
        "finding": {
            "code": "copy.investor-quality",
            "severity": "error",
            "path": HTML_PATH,
            "route": ROUTE,
            "blocker_count": 1,
            "warning_count": 0,
        },
        "allowed_scope": [
            "artifacts/website-candidates/<run-id>/website/<exact paths declared by v4 work order>"
        ],
        "candidate_work_order_required": True,
        "acceptance": [
            "Rerun the investor-copy audit against the exact staged candidate.",
        ],
    }


def _claim_capsule() -> dict[str, Any]:
    return {
        "route_id": "investor-route",
        "route": ROUTE,
        "claims": [
            {
                "id": "evidence-os",
                "claim": "Controlled test wording that is never copied into the contract.",
                "state": "bounded",
                "boundary": "This does not establish independent external validation.",
                "permitted_wording": ["Evidence OS is the first wedge."],
                "prohibited_inferences": ["external validation"],
                "public_routes": [ROUTE],
                "expires_on": "2026-08-13",
                "source": {
                    "path": "website/funding/investor-deck/index.html",
                    "sha256": "A" * 64,
                },
            }
        ],
    }


@pytest.fixture()  # type: ignore[untyped-decorator]
def contract_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    root = tmp_path / "repo"
    (root / "aureon").mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
    source_file = root / "website" / HTML_PATH
    source_file.parent.mkdir(parents=True)
    source_file.write_text(
        _html("Evidence OS currently exposes 11 selected routes."),
        encoding="utf-8",
    )
    _write_json(
        root / "data" / "website_operator" / "investor_copy_quality_policy.v1.json",
        _policy(refresh_by=NOW + timedelta(days=1)),
    )
    (root / "artifacts" / "website-operator").mkdir(parents=True)
    (root / "artifacts" / "website-candidates" / "work-orders").mkdir(parents=True)

    baseline = repair._tree_summary(repair._tree_rows(root / "website"))
    work_order = {
        "schema": "aureon.design-work-order.v4",
        "created_at": NOW.isoformat().replace("+00:00", "Z"),
        "run_id": "copyrepairrun",
        "goal": "Repair one bounded investor-copy route.",
        "routes": [ROUTE],
        "allowed_paths": [HTML_PATH],
        "live_reconciliation": {
            "owner_source_reconciliation": {
                "candidate_source": None,
            }
        },
        "baseline": baseline,
        "candidate_layout": {
            "website_path": "artifacts/website-candidates/copyrepairrun/website",
        },
    }
    work_order_path = root / "artifacts" / "website-candidates" / "work-orders" / "copy-repair.json"
    _write_json(work_order_path, work_order)

    design_cycle = {
        "schema": "aureon-website-design-job-v1",
        "run_id": "designrun123",
        "generated_at": NOW.isoformat().replace("+00:00", "Z"),
        "work_orders": [_task()],
    }
    design_path = root / "artifacts" / "website-operator" / "design-cycle.json"
    _write_json(design_path, design_cycle)
    capsule = _claim_capsule()
    monkeypatch.setattr(
        repair,
        "verify_design_work_order",
        lambda *_args, **_kwargs: {"passed": True},
    )
    contract = repair.create_investor_copy_repair_contract(
        design_cycle_receipt=design_path,
        task_id=TASK_ID,
        work_order=work_order_path,
        route_claim_capsule=capsule,
        required_claim_ids=["evidence-os"],
        repo_root=root,
        now=NOW,
        lifetime=timedelta(hours=1),
    )
    return {
        "root": root,
        "contract": contract,
        "capsule": capsule,
        "work_order": work_order,
        "work_order_path": work_order_path,
        "design_path": design_path,
        "source_file": source_file,
    }


def _verify(fixture: dict[str, Any], contract: dict[str, Any] | None = None) -> dict[str, Any]:
    return repair.verify_investor_copy_repair_contract(
        contract or fixture["contract"],
        route_claim_capsule=fixture["capsule"],
        repo_root=fixture["root"],
        as_of=NOW + timedelta(minutes=5),
    )


def _candidate(fixture: dict[str, Any], body: str) -> Path:
    root = Path(fixture["root"])
    candidate_root = root / "artifacts" / "website-candidates" / "copyrepairrun" / "website"
    candidate_file = candidate_root / HTML_PATH
    candidate_file.parent.mkdir(parents=True)
    candidate_file.write_text(_html(body), encoding="utf-8")
    return candidate_root


def _all_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            keys.add(str(key))
            keys.update(_all_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.update(_all_keys(item))
    return keys


def test_contract_is_source_bound_private_and_current(
    contract_fixture: dict[str, Any],
) -> None:
    contract = contract_fixture["contract"]
    verification = _verify(contract_fixture)

    assert verification["passed"] is True
    assert contract["selected_source"]["kind"] == "canonical-local"
    assert contract["route"] == {
        "route": ROUTE,
        "path": HTML_PATH,
        "before_sha256": repair._file_sha256(contract_fixture["source_file"]),
    }
    assert contract["source_audit"]["blocker_count"] == 1
    assert contract["source_audit"]["rule_histogram"] == [
        {
            "rule_id": "static-operating-count",
            "finding_count": 1,
            "blocker_count": 1,
            "warning_count": 0,
        }
    ]
    assert contract["claim_control"]["satisfied_concept_ids"] == ["commercial-wedge"]
    assert repair._SHA256.fullmatch(contract["claim_control"]["required_concept_groups_sha256"])
    forbidden = {
        "alternatives",
        "analytics",
        "correspondence",
        "evidence",
        "match",
        "message",
        "messages",
        "snippet",
        "title",
        "h1",
        "wording",
    }
    assert forbidden.isdisjoint(_all_keys(contract))
    serialised = json.dumps(contract)
    assert "11 selected routes" not in serialised
    assert "Controlled test wording" not in serialised
    assert "Evidence OS is the first wedge" not in serialised


def test_read_only_preflight_binds_task_policy_route_and_claims_without_source_or_wording(
    contract_fixture: dict[str, Any],
) -> None:
    preflight = repair.preflight_investor_copy_repair_contract(
        design_cycle_receipt=contract_fixture["design_path"],
        task_id=TASK_ID,
        route_claim_capsule=contract_fixture["capsule"],
        required_claim_ids=["evidence-os"],
        repo_root=contract_fixture["root"],
        as_of=NOW,
    )

    assert preflight["schema"] == repair.PREFLIGHT_SCHEMA
    assert preflight["passed"] is True
    assert preflight["route"] == {"route": ROUTE, "path": HTML_PATH}
    assert preflight["design_cycle"]["task_sha256"] == repair._json_sha256(_task())
    serialised = json.dumps(preflight)
    assert "selected_source" not in serialised
    assert "11 selected routes" not in serialised
    assert "Evidence OS is the first wedge" not in serialised


def test_verified_live_backup_is_reaudited_instead_of_canonical_source(
    contract_fixture: dict[str, Any],
) -> None:
    root = Path(contract_fixture["root"])
    backup_root = root / "artifacts" / "homepl-backups" / "verified-live-backup" / "document-root"
    backup_file = backup_root / HTML_PATH
    backup_file.parent.mkdir(parents=True)
    backup_file.write_text(
        _html("The verified live Evidence OS source exposes 11 selected routes."),
        encoding="utf-8",
    )
    manifest = root / "artifacts" / "homepl-backups" / "verified-live-backup-manifest.csv"
    manifest.write_text(
        f"Path,Bytes,Sha256\n{HTML_PATH},{backup_file.stat().st_size},{repair._file_sha256(backup_file)}\n",
        encoding="utf-8",
    )
    baseline = repair._tree_summary(repair._tree_rows(backup_root))
    work_order = copy.deepcopy(contract_fixture["work_order"])
    work_order["baseline"] = baseline
    work_order["live_reconciliation"]["owner_source_reconciliation"]["candidate_source"] = {
        "kind": "verified-live-backup",
        "root": str(backup_root.resolve()),
        "manifest_path": str(manifest.resolve()),
        "manifest_sha256": repair._file_sha256(manifest),
        "tree_sha256": "C" * 64,
        "baseline_tree_sha256": baseline["tree_sha256"],
        "file_count": baseline["file_count"],
        "total_bytes": baseline["total_bytes"],
        "remote_root": "/",
    }
    _write_json(contract_fixture["work_order_path"], work_order)
    contract_fixture["source_file"].write_text(
        _html("The canonical-local page has no controlled finding."),
        encoding="utf-8",
    )

    contract = repair.create_investor_copy_repair_contract(
        design_cycle_receipt=contract_fixture["design_path"],
        task_id=TASK_ID,
        work_order=contract_fixture["work_order_path"],
        route_claim_capsule=contract_fixture["capsule"],
        required_claim_ids=["evidence-os"],
        repo_root=root,
        now=NOW,
    )

    assert contract["selected_source"]["kind"] == "verified-live-backup"
    assert contract["selected_source"]["root"] == str(backup_root.resolve())
    assert contract["route"]["before_sha256"] == repair._file_sha256(backup_file)
    assert contract["source_audit"]["blocker_count"] == 1


def test_work_order_preflight_rejects_dirty_non_target_policy_routes(
    contract_fixture: dict[str, Any],
) -> None:
    root = Path(contract_fixture["root"])
    other_route = "/research/"
    other_path = "research/index.html"
    other_file = root / "website" / other_path
    other_file.parent.mkdir(parents=True)
    other_file.write_text(
        _html("Evidence OS currently exposes 18 selected routes."),
        encoding="utf-8",
    )
    policy = _policy(refresh_by=NOW + timedelta(days=1))
    other_policy = copy.deepcopy(policy["routes"][0])
    other_policy["route"] = other_route
    other_policy["path"] = other_path
    policy["routes"].append(other_policy)
    _write_json(
        root / "data" / "website_operator" / "investor_copy_quality_policy.v1.json",
        policy,
    )
    work_order = copy.deepcopy(contract_fixture["work_order"])
    work_order["baseline"] = repair._tree_summary(repair._tree_rows(root / "website"))
    _write_json(contract_fixture["work_order_path"], work_order)

    with pytest.raises(
        repair.InvestorCopyRepairError,
        match="Non-target policy routes",
    ):
        repair.preflight_investor_copy_repair_work_order(
            design_cycle_receipt=contract_fixture["design_path"],
            task_id=TASK_ID,
            work_order=work_order,
            planned_work_order_path=contract_fixture["work_order_path"],
            route_claim_capsule=contract_fixture["capsule"],
            required_claim_ids=["evidence-os"],
            repo_root=root,
            as_of=NOW,
        )

    with pytest.raises(
        repair.InvestorCopyRepairError,
        match="Non-target policy routes",
    ):
        repair.create_investor_copy_repair_contract(
            design_cycle_receipt=contract_fixture["design_path"],
            task_id=TASK_ID,
            work_order=contract_fixture["work_order_path"],
            route_claim_capsule=contract_fixture["capsule"],
            required_claim_ids=["evidence-os"],
            repo_root=root,
            now=NOW,
        )


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("section", "field"),
    [
        ("design_cycle", "task_sha256"),
        ("work_order", "sha256"),
        ("policy", "sha256"),
        ("claim_control", "route_claim_capsule_sha256"),
        ("claim_control", "required_concept_groups_sha256"),
    ],
)
def test_hash_tampering_fails_closed(
    contract_fixture: dict[str, Any],
    section: str,
    field: str,
) -> None:
    tampered = copy.deepcopy(contract_fixture["contract"])
    tampered[section][field] = "B" * 64

    assert _verify(contract_fixture, tampered)["passed"] is False


def test_unsatisfied_blocker_concept_prevents_contract_creation(
    contract_fixture: dict[str, Any],
) -> None:
    policy = _policy(refresh_by=NOW + timedelta(days=1))
    policy["routes"][0]["required_concept_groups"].append(
        {
            "concept_id": "human-control",
            "severity": "blocker",
            "alternatives": ["human gate", "accountable approval"],
        }
    )
    _write_json(
        Path(contract_fixture["root"]) / "data" / "website_operator" / "investor_copy_quality_policy.v1.json",
        policy,
    )

    with pytest.raises(
        repair.InvestorCopyRepairError,
        match="not satisfiable",
    ):
        repair.preflight_investor_copy_repair_contract(
            design_cycle_receipt=contract_fixture["design_path"],
            task_id=TASK_ID,
            route_claim_capsule=contract_fixture["capsule"],
            required_claim_ids=["evidence-os"],
            repo_root=contract_fixture["root"],
            as_of=NOW,
        )

    with pytest.raises(
        repair.InvestorCopyRepairError,
        match="not satisfiable",
    ):
        repair.create_investor_copy_repair_contract(
            design_cycle_receipt=contract_fixture["design_path"],
            task_id=TASK_ID,
            work_order=contract_fixture["work_order_path"],
            route_claim_capsule=contract_fixture["capsule"],
            required_claim_ids=["evidence-os"],
            repo_root=contract_fixture["root"],
            now=NOW,
        )


def test_unsatisfied_warning_concept_prevents_zero_warning_contract(
    contract_fixture: dict[str, Any],
) -> None:
    policy = _policy(refresh_by=NOW + timedelta(days=1))
    policy["routes"][0]["required_concept_groups"].append(
        {
            "concept_id": "buyer-clarity",
            "severity": "warning",
            "alternatives": ["first accountable buyer"],
        }
    )
    _write_json(
        Path(contract_fixture["root"]) / "data" / "website_operator" / "investor_copy_quality_policy.v1.json",
        policy,
    )

    with pytest.raises(
        repair.InvestorCopyRepairError,
        match="not satisfiable",
    ):
        repair.preflight_investor_copy_repair_contract(
            design_cycle_receipt=contract_fixture["design_path"],
            task_id=TASK_ID,
            route_claim_capsule=contract_fixture["capsule"],
            required_claim_ids=["evidence-os"],
            repo_root=contract_fixture["root"],
            as_of=NOW,
        )


def test_tampered_satisfied_concept_binding_fails_closed(
    contract_fixture: dict[str, Any],
) -> None:
    tampered = copy.deepcopy(contract_fixture["contract"])
    tampered["claim_control"]["satisfied_concept_ids"] = []

    assert _verify(contract_fixture, tampered)["passed"] is False


def test_source_substitution_and_source_divergence_fail_closed(
    contract_fixture: dict[str, Any],
) -> None:
    substituted = copy.deepcopy(contract_fixture["contract"])
    substituted["selected_source"]["root"] = str(Path(contract_fixture["root"]) / "another-source")
    assert _verify(contract_fixture, substituted)["passed"] is False

    contract_fixture["source_file"].write_text(
        _html("Source changed after contract creation."),
        encoding="utf-8",
    )
    assert _verify(contract_fixture)["passed"] is False


def test_stale_contract_and_stale_policy_fail_closed(
    contract_fixture: dict[str, Any],
) -> None:
    stale_contract = repair.verify_investor_copy_repair_contract(
        contract_fixture["contract"],
        route_claim_capsule=contract_fixture["capsule"],
        repo_root=contract_fixture["root"],
        as_of=NOW + timedelta(hours=2),
    )
    assert stale_contract["passed"] is False

    _write_json(
        Path(contract_fixture["root"]) / "data" / "website_operator" / "investor_copy_quality_policy.v1.json",
        _policy(refresh_by=NOW - timedelta(minutes=1)),
    )
    assert _verify(contract_fixture)["passed"] is False


def test_route_path_broadening_and_private_field_injection_fail_closed(
    contract_fixture: dict[str, Any],
) -> None:
    broadened_contract = copy.deepcopy(contract_fixture["contract"])
    broadened_contract["route"]["path"] = "funding/index.html"
    assert _verify(contract_fixture, broadened_contract)["passed"] is False

    injected = copy.deepcopy(contract_fixture["contract"])
    injected["source_audit"]["snippet"] = "private source text"
    assert _verify(contract_fixture, injected)["passed"] is False

    work_order = copy.deepcopy(contract_fixture["work_order"])
    work_order["routes"].append("/research/")
    _write_json(contract_fixture["work_order_path"], work_order)
    with pytest.raises(
        repair.InvestorCopyRepairError,
        match="exactly one route",
    ):
        repair.create_investor_copy_repair_contract(
            design_cycle_receipt=contract_fixture["design_path"],
            task_id=TASK_ID,
            work_order=contract_fixture["work_order_path"],
            route_claim_capsule=contract_fixture["capsule"],
            required_claim_ids=["evidence-os"],
            repo_root=contract_fixture["root"],
            now=NOW,
        )


def test_candidate_requires_zero_blockers_and_zero_warnings(
    contract_fixture: dict[str, Any],
) -> None:
    candidate_root = _candidate(
        contract_fixture,
        "A revolutionary Evidence OS platform with a human gate.",
    )
    receipt = repair.evaluate_investor_copy_repair_candidate(
        contract_fixture["contract"],
        candidate_website_root=candidate_root,
        route_claim_capsule=contract_fixture["capsule"],
        repo_root=contract_fixture["root"],
        as_of=NOW + timedelta(minutes=5),
    )

    assert receipt["passed"] is False
    assert receipt["candidate_audit"]["blocker_count"] == 0
    assert receipt["candidate_audit"]["warning_count"] == 1
    assert next(item for item in receipt["checks"] if item["id"] == "zero-warnings")["passed"] is False


def test_candidate_passes_only_for_exact_clean_route_diff(
    contract_fixture: dict[str, Any],
) -> None:
    candidate_root = _candidate(
        contract_fixture,
        "Evidence OS is the first wedge, with accountable human control.",
    )
    receipt = repair.evaluate_investor_copy_repair_candidate(
        contract_fixture["contract"],
        candidate_website_root=candidate_root,
        route_claim_capsule=contract_fixture["capsule"],
        repo_root=contract_fixture["root"],
        as_of=NOW + timedelta(minutes=5),
    )

    assert receipt["passed"] is True
    assert receipt["candidate_audit"]["blocker_count"] == 0
    assert receipt["candidate_audit"]["warning_count"] == 0
    assert receipt["release_eligible"] is False
    assert receipt["package_authority"] == "none"
    assert receipt["deployment_authority"] == "none"


def test_candidate_tree_change_during_policy_replay_fails_closed(
    contract_fixture: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate_root = _candidate(
        contract_fixture,
        "Evidence OS is the first wedge, with accountable human control.",
    )
    original_audit = repair._audit_selected_source

    def racing_audit(**kwargs: Any) -> dict[str, Any]:
        result = original_audit(**kwargs)
        source_root = Path(kwargs["source_root"]).resolve()
        if source_root == candidate_root.resolve():
            target = source_root / HTML_PATH
            target.write_text(
                target.read_text(encoding="utf-8") + "\n<!-- concurrent drift -->\n",
                encoding="utf-8",
            )
        return result

    monkeypatch.setattr(repair, "_audit_selected_source", racing_audit)
    receipt = repair.evaluate_investor_copy_repair_candidate(
        contract_fixture["contract"],
        candidate_website_root=candidate_root,
        route_claim_capsule=contract_fixture["capsule"],
        repo_root=contract_fixture["root"],
        as_of=NOW + timedelta(minutes=5),
    )

    assert receipt["passed"] is False
    assert (
        next(item for item in receipt["checks"] if item["id"] == "stable-post-audit-tree")["passed"] is False
    )


def test_claim_capsule_change_and_extra_candidate_file_fail_closed(
    contract_fixture: dict[str, Any],
) -> None:
    changed_capsule = copy.deepcopy(contract_fixture["capsule"])
    changed_capsule["claims"][0]["boundary"] = "A different claim boundary."
    assert (
        repair.verify_investor_copy_repair_contract(
            contract_fixture["contract"],
            route_claim_capsule=changed_capsule,
            repo_root=contract_fixture["root"],
            as_of=NOW + timedelta(minutes=5),
        )["passed"]
        is False
    )

    candidate_root = _candidate(
        contract_fixture,
        "Evidence OS is the first wedge, with accountable human control.",
    )
    (candidate_root / "extra.html").write_text(_html("Extra route."), encoding="utf-8")
    receipt = repair.evaluate_investor_copy_repair_candidate(
        contract_fixture["contract"],
        candidate_website_root=candidate_root,
        route_claim_capsule=contract_fixture["capsule"],
        repo_root=contract_fixture["root"],
        as_of=NOW + timedelta(minutes=5),
    )
    assert receipt["passed"] is False
    assert (
        next(item for item in receipt["checks"] if item["id"] == "exact-target-only-diff")["passed"] is False
    )


def test_immutable_writer_refuses_overwrite(
    contract_fixture: dict[str, Any],
) -> None:
    output = repair.write_investor_copy_repair_contract(
        contract_fixture["contract"],
        repo_root=contract_fixture["root"],
    )
    assert output.is_file()
    assert output.stat().st_nlink == 1

    with pytest.raises(repair.InvestorCopyRepairError, match="overwrite"):
        repair.write_investor_copy_repair_contract(
            contract_fixture["contract"],
            repo_root=contract_fixture["root"],
        )
