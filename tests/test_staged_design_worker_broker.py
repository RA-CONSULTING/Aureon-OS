"""Safety tests for the lease-bound staged design-worker bridge."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from aureon.autonomous import aureon_public_website_design_runner as runner
from aureon.autonomous import aureon_staged_design_worker_broker as broker
from aureon.operator import design_candidate_source_closure as source_closure
from aureon.operator.design_investor_copy_quality import (
    NON_AUTHORITATIVE_AUTHORITY as COPY_AUDIT_AUTHORITY,
)
from aureon.operator.live_surface_reconciliation import (
    reconcile_live_surface,
    write_live_surface_reconciliation,
)

NOW = datetime(2026, 7, 28, 20, 0, tzinfo=UTC)
COPY_ROUTE = "/funding/investor-deck/"
COPY_HTML_PATH = "funding/investor-deck/index.html"
COPY_TASK_ID = "DESIGN-COPY-001"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _feedback_signal() -> dict:
    return {
        "signal_id": "fixture-first-visit-clarity",
        "signal_kind": "clarity-gap",
        "disposition": "action-requested",
        "priority": "high",
        "requested_response_dimension": "first-visit-clarity",
        "route_scope": "/",
        "claim_ids": ["homepage-claim"],
    }


def _feedback_capsule() -> dict:
    signal = _feedback_signal()
    return {
        "route_id": "home",
        "route": "/",
        "signals": [
            {
                "signal": signal,
                "signal_capsule_sha256": runner._json_sha256(signal),
            }
        ],
    }


def _brief_document() -> dict:
    return {
        "route_plan": [
            {
                "id": "home",
                "route": "/",
                "purpose": "Lead with the evidence-control wedge before broader research positioning.",
                "allowed_paths": ["index.html", "styles.css"],
                "content_order": ["Decision problem", "Evidence method", "Bounded proof"],
            }
        ],
        "visual_rules": [
            {
                "id": "evidence-loop",
                "purpose": "Keep the decision-to-evidence loop readable before decorative motion.",
                "static_equivalent": "A readable ordered evidence loop remains when motion is disabled.",
                "reduced_motion_required": True,
                "affects_paths": ["index.html", "styles.css"],
            }
        ],
        "prohibited_public_inferences": [
            "Do not imply customer adoption from research or repository signals.",
            "Do not publish confidential funding figures.",
        ],
        "acceptance_criteria": [
            "Keep the evidence-control wedge understandable before research breadth.",
            "Provide a static reduced-motion equivalent for material animation.",
            "Keep canonical website files unchanged until owner promotion.",
        ],
    }


def _copy_html(*, include_static_count: bool) -> str:
    static_count = "<p>Evidence OS currently exposes 11 selected routes.</p>" if include_static_count else ""
    return (
        "<!doctype html><html><head>"
        "<title>Aureon Investor Evidence Platform</title>"
        '<meta name="description" content="A research-led systems company '
        "connecting controlled evidence, accountable delivery and investor-ready "
        'public research.">'
        "</head><body><h1>Research-led systems company</h1>"
        "<p>Evidence OS is the first wedge.</p>"
        "<p>This does not establish independent external validation.</p>"
        "<p>Accountable human control remains required.</p>"
        f"{static_count}</body></html>"
    )


def _copy_brief_document() -> dict:
    return {
        "route_plan": [
            {
                "id": "investor-reading-room",
                "route": COPY_ROUTE,
                "purpose": "Give investor readers one controlled evidence route.",
                "allowed_paths": [COPY_HTML_PATH, "styles.css"],
                "content_order": [
                    "Investment reading frame",
                    "Commercial wedge",
                    "Controlled next step",
                ],
            }
        ],
        "visual_rules": [
            {
                "id": "investor-evidence-flow",
                "purpose": "Keep the evidence route readable before motion.",
                "static_equivalent": "The evidence route remains readable without motion.",
                "reduced_motion_required": True,
                "affects_paths": [COPY_HTML_PATH, "styles.css"],
            }
        ],
        "prohibited_public_inferences": [
            "Do not imply independent external validation.",
            "Do not publish confidential funding figures.",
        ],
        "acceptance_criteria": [
            "Remove stale operating counts.",
            "Keep the representation boundary visible.",
            "Keep canonical website files unchanged.",
        ],
    }


def _fake_repo(root: Path) -> None:
    _write(root / "pyproject.toml", "[tool.pytest.ini_options]\n")
    (root / "aureon" / "operator").mkdir(parents=True, exist_ok=True)
    source_root = Path(runner.__file__).resolve().parents[2]
    executable_closure = source_closure.build_source_closure(source_root)
    for row in executable_closure["files"]:
        relative = Path(str(row["path"]))
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_root / relative, destination)
    _write(root / "aureon" / "operator" / "website_operator.defaults.json", '{"policy":"test"}\n')
    _write(root / "website" / ".htaccess", "Options -Indexes\n")
    _write(
        root / "website" / "index.html",
        "<!doctype html><title>Aureon</title><p>Aureon is an evidence-led test company. "
        "This fixture is not evidence of customer adoption or independent validation.</p>\n",
    )
    _write(root / "website" / "styles.css", "body { color: #123456; }\n")
    brief_path = root / "data" / "website_operator" / "investor_site_design_brief.v1.json"
    _write(brief_path, json.dumps(_brief_document(), indent=2) + "\n")
    register = {
        "schema": "aureon.public-claim-evidence-register.v1",
        "generated_at": "2026-07-28T20:00:00Z",
        "scope": "material public website positioning claims",
        "authority": {
            "scope": "read-only public-claim evidence control",
            "release_eligible": False,
            "deployment_authority": "none",
            "package_authority": "none",
            "human_review": "required for material public wording changes",
        },
        "claims": [
            {
                "id": "homepage-claim",
                "title": "Test homepage positioning",
                "claim": "Aureon is an evidence-led test company.",
                "state": "company-authored",
                "boundary": "This fixture is not evidence of customer adoption or independent validation.",
                "permitted_wording": ["Aureon is an evidence-led test company."],
                "prohibited_inferences": ["customer adoption", "independent validation"],
                "expires_on": "2027-07-28",
                "source": {
                    "path": "website/index.html",
                    "sha256": _sha256(root / "website" / "index.html"),
                    "locator": "fixture:index",
                    "evidence_texts": ["Aureon", "boundary"],
                    "boundary_text": "This fixture is not evidence of customer adoption or independent validation.",
                },
                "public_routes": ["/"],
            }
        ],
    }
    _write(
        root / "data" / "website_operator" / "public_claim_evidence_register.v1.json",
        json.dumps(register, indent=2) + "\n",
    )


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


def _aligned_reconciliation(root: Path, run_id: str) -> Path:
    source = (root / "website" / "index.html").read_bytes()
    receipt = reconcile_live_surface(
        repo_root=root,
        site_root=root / "website",
        base_url="https://example.test/",
        routes=["index.html"],
        now=NOW,
        opener=lambda request, timeout: _Response(source, request.full_url),
    )
    return write_live_surface_reconciliation(
        receipt,
        root / "artifacts" / "website-operator" / f"{run_id}-alignment.json",
        repo_root=root,
    )


def _brief_audit(root: Path) -> dict:
    capsule = {
        "route_id": "home",
        "route": "/",
        "claims": [
            {
                "id": "homepage-claim",
                "claim": "Aureon is an evidence-led test company.",
                "boundary": "This fixture is not evidence of customer adoption or independent validation.",
                "permitted_wording": ["Aureon is an evidence-led test company."],
                "prohibited_inferences": ["customer adoption", "independent validation"],
            }
        ],
    }
    brief_path = root / "data" / "website_operator" / "investor_site_design_brief.v1.json"
    feedback_capsule = _feedback_capsule()
    return {
        "schema": "aureon.design-evidence-brief-audit.v1",
        "passed": True,
        "brief": {
            "brief_id": "fixture-brief",
            "path": "data/website_operator/investor_site_design_brief.v1.json",
            "sha256": _sha256(brief_path),
            "refresh_by": "2026-08-09T23:59:59Z",
        },
        "research_refresh": {
            "declaration_path": "data/website_operator/design_research_sources.v1.json",
            "declaration_sha256": "D" * 64,
            "state": "current",
            "passed": True,
            "artwork": {"state": "not-cleared", "cleared_for_use": False},
        },
        "stakeholder_feedback": {
            "feedback_id": "fixture-feedback",
            "path": "data/website_operator/design_stakeholder_feedback.v1.json",
            "sha256": "E" * 64,
            "state": "current",
            "passed": True,
            "signal_ids": ["fixture-first-visit-clarity"],
            "signal_capsules_sha256": "F" * 64,
        },
        "claim_control": {
            "register_path": "data/website_operator/public_claim_evidence_register.v1.json",
            "register_sha256": _sha256(
                root / "data" / "website_operator" / "public_claim_evidence_register.v1.json"
            ),
            "claim_ids": ["homepage-claim"],
        },
        "source_inputs": [
            {
                "id": "fixture",
                "path": "website/index.html",
                "sha256": _sha256(root / "website" / "index.html"),
            }
        ],
        "route_plan": [
            {
                "id": "home",
                "route": "/",
                "local_path": "index.html",
                "allowed_paths": ["index.html", "styles.css"],
                "claim_ids": ["homepage-claim"],
                "content_order": ["Decision problem", "Evidence method", "Bounded proof"],
            }
        ],
        "route_claim_capsules": [capsule],
        "route_claim_capsules_sha256": runner._json_sha256([capsule]),
        "route_feedback_capsules": [feedback_capsule],
        "route_feedback_capsules_sha256": runner._json_sha256([feedback_capsule]),
    }


def _copy_brief_audit(root: Path) -> dict:
    claim = {
        "id": "evidence-os",
        "claim": "Controlled test wording that is never copied into the contract.",
        "state": "bounded",
        "boundary": "This does not establish independent external validation.",
        "permitted_wording": ["Evidence OS is the first wedge."],
        "prohibited_inferences": ["external validation"],
        "public_routes": [COPY_ROUTE],
        "expires_on": "2027-07-28",
        "source": {
            "path": f"website/{COPY_HTML_PATH}",
            "sha256": _sha256(root / "website" / COPY_HTML_PATH),
        },
    }
    capsule = {
        "route_id": "investor-reading-room",
        "route": COPY_ROUTE,
        "claims": [claim],
    }
    signal = {
        "signal_id": "fixture-investor-clarity",
        "signal_kind": "clarity-gap",
        "disposition": "action-requested",
        "priority": "high",
        "requested_response_dimension": "business-model-clarity",
        "route_scope": COPY_ROUTE,
        "claim_ids": ["evidence-os"],
    }
    feedback_capsule = {
        "route_id": "investor-reading-room",
        "route": COPY_ROUTE,
        "signals": [
            {
                "signal": signal,
                "signal_capsule_sha256": runner._json_sha256(signal),
            }
        ],
    }
    brief_path = root / "data" / "website_operator" / "investor_site_design_brief.v1.json"
    return {
        "schema": "aureon.design-evidence-brief-audit.v1",
        "passed": True,
        "brief": {
            "brief_id": "fixture-copy-brief",
            "path": "data/website_operator/investor_site_design_brief.v1.json",
            "sha256": _sha256(brief_path),
            "refresh_by": "2026-08-09T23:59:59Z",
        },
        "research_refresh": {
            "declaration_path": "data/website_operator/design_research_sources.v1.json",
            "declaration_sha256": "D" * 64,
            "state": "current",
            "passed": True,
            "artwork": {"state": "not-cleared", "cleared_for_use": False},
        },
        "stakeholder_feedback": {
            "feedback_id": "fixture-copy-feedback",
            "path": "data/website_operator/design_stakeholder_feedback.v1.json",
            "sha256": "E" * 64,
            "state": "current",
            "passed": True,
            "signal_ids": ["fixture-investor-clarity"],
            "signal_capsules_sha256": "F" * 64,
        },
        "claim_control": {
            "register_path": "data/website_operator/public_claim_evidence_register.v1.json",
            "register_sha256": _sha256(
                root / "data" / "website_operator" / "public_claim_evidence_register.v1.json"
            ),
            "claim_ids": ["evidence-os"],
        },
        "source_inputs": [
            {
                "id": "fixture-copy",
                "path": f"website/{COPY_HTML_PATH}",
                "sha256": _sha256(root / "website" / COPY_HTML_PATH),
            }
        ],
        "route_plan": [
            {
                "id": "investor-reading-room",
                "route": COPY_ROUTE,
                "local_path": COPY_HTML_PATH,
                "allowed_paths": [COPY_HTML_PATH, "styles.css"],
                "claim_ids": ["evidence-os"],
                "content_order": [
                    "Investment reading frame",
                    "Commercial wedge",
                    "Controlled next step",
                ],
            }
        ],
        "route_claim_capsules": [capsule],
        "route_claim_capsules_sha256": runner._json_sha256([capsule]),
        "route_feedback_capsules": [feedback_capsule],
        "route_feedback_capsules_sha256": runner._json_sha256([feedback_capsule]),
    }


def _copy_reconciliation(root: Path, run_id: str) -> Path:
    source = (root / "website" / COPY_HTML_PATH).read_bytes()
    receipt = reconcile_live_surface(
        repo_root=root,
        site_root=root / "website",
        base_url="https://example.test/",
        routes=[COPY_HTML_PATH],
        now=NOW,
        opener=lambda request, timeout: _Response(source, request.full_url),
    )
    return write_live_surface_reconciliation(
        receipt,
        root / "artifacts" / "website-operator" / f"{run_id}-alignment.json",
        repo_root=root,
    )


def _setup_copy_run(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    run_id: str,
) -> dict:
    _fake_repo(root)
    _write(
        root / "website" / COPY_HTML_PATH,
        _copy_html(include_static_count=True),
    )
    _write(
        root / "data" / "website_operator" / "investor_site_design_brief.v1.json",
        json.dumps(_copy_brief_document(), indent=2) + "\n",
    )
    policy = {
        "schema": "aureon.investor-copy-quality-policy.v1",
        "policy_id": "aureon-investor-copy-quality-broker-test",
        "issued_at": (NOW - timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
        "refresh_by": (NOW + timedelta(days=1)).isoformat().replace("+00:00", "Z"),
        "authority": dict(COPY_AUDIT_AUTHORITY),
        "snapshot_max_age_days": 14,
        "routes": [
            {
                "route": COPY_ROUTE,
                "path": COPY_HTML_PATH,
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
    _write(
        root / "data" / "website_operator" / "investor_copy_quality_policy.v1.json",
        json.dumps(policy, indent=2) + "\n",
    )
    design_cycle = {
        "schema": "aureon-website-design-job-v1",
        "run_id": "designcopybroker",
        "generated_at": NOW.isoformat().replace("+00:00", "Z"),
        "work_orders": [
            {
                "id": COPY_TASK_ID,
                "owner": "technical-editor",
                "title": "Remove investor-copy policy blockers from one route",
                "finding": {
                    "code": "copy.investor-quality",
                    "severity": "error",
                    "path": COPY_HTML_PATH,
                    "route": COPY_ROUTE,
                    "blocker_count": 1,
                    "warning_count": 0,
                },
                "allowed_scope": [
                    "artifacts/website-candidates/<run-id>/website/<exact paths declared by v4 work order>"
                ],
                "candidate_work_order_required": True,
                "acceptance": ["Rerun the investor-copy audit against the exact staged candidate."],
            }
        ],
    }
    design_path = root / "artifacts" / "website-operator" / "design-copy-cycle.json"
    _write(design_path, json.dumps(design_cycle, indent=2) + "\n")
    audit = _copy_brief_audit(root)
    monkeypatch.setattr(
        runner,
        "audit_design_evidence_brief_file",
        lambda **_kwargs: deepcopy(audit),
    )
    runner.create_design_delivery_job(
        goal="Repair one exact investor-copy route.",
        route_id="investor-reading-room",
        reconciliation_receipt=_copy_reconciliation(root, run_id),
        design_cycle_receipt=design_path,
        design_copy_task_id=COPY_TASK_ID,
        run_id=run_id,
        repo_root=root,
        now=NOW,
    )
    staged, _ = runner.stage_design_delivery_job(
        run_id,
        repo_root=root,
        now=NOW,
    )
    return staged


def _create_staged_run(root: Path, monkeypatch: pytest.MonkeyPatch, run_id: str) -> dict:
    audit = _brief_audit(root)
    monkeypatch.setattr(runner, "audit_design_evidence_brief_file", lambda **_kwargs: deepcopy(audit))
    runner.create_design_delivery_job(
        goal="Refine one bounded investor-facing route.",
        route_id="home",
        reconciliation_receipt=_aligned_reconciliation(root, run_id),
        run_id=run_id,
        repo_root=root,
        now=NOW,
    )
    staged, _ = runner.stage_design_delivery_job(run_id, repo_root=root, now=NOW)
    return staged


def _patch_fake_editorial_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audits: dict[Path, dict] = {}

    def fake_import(
        work_order_path: Path,
        *,
        repo_root: Path | None = None,
        **_kwargs: object,
    ) -> dict:
        assert repo_root is not None
        order = json.loads((repo_root / work_order_path).read_text(encoding="utf-8"))
        control = order["editorial_asset_control"]
        asset_capsule = {
            "asset_id": "fixture-hero",
            "scope": "privacy-safe-test-capsule",
        }
        placement = {
            "route_scope": "/",
            "destination_path": "website/index.html",
            "surface_id": "fixture-home-hero",
            "alt": "Aureon research evidence illustration",
            "caption": "Research evidence translated into a bounded public explanation.",
            "credit": "Artwork supplied for the linked Aureon research article.",
        }
        route_capsule = {
            "route_scope": "/",
            "asset_id": "fixture-hero",
            "public_post_url": "https://example.substack.com/p/fixture-hero",
            "website_variants": [
                {
                    "role": "large",
                    "path": "website/assets/hero.webp",
                    "sha256": "D" * 64,
                    "media_type": "image/webp",
                    "width": 1600,
                    "height": 900,
                }
            ],
            "placement": placement,
        }
        route_capsule["route_asset_capsule_sha256"] = runner._json_sha256(route_capsule)
        selected_capsules_sha256 = runner._json_sha256([asset_capsule])
        audits[repo_root.resolve()] = {
            "passed": True,
            "manifest": {
                "sha256": control["provenance_manifest_sha256"],
            },
            "asset_capsules": [asset_capsule],
            "route_asset_capsules": [route_capsule],
        }
        receipt = {
            "receipt_payload_sha256": "A" * 64,
            "provenance": {
                "manifest_file_sha256": control["provenance_manifest_sha256"],
                "selected_asset_capsules_sha256": selected_capsules_sha256,
                "candidate_ready_asset_ids": ["fixture-hero"],
            },
            "summary": {"imports_sha256": "C" * 64},
            "work_order": {
                "json_sha256": runner._json_sha256(order),
                "baseline_tree_sha256": order["baseline"]["tree_sha256"],
            },
            "imports": [
                {
                    "asset_id": "fixture-hero",
                    "target": (f"artifacts/website-candidates/{order['run_id']}/website/assets/hero.webp"),
                    "route_scopes": ["/"],
                    "destination_paths": ["index.html"],
                    "surface_ids": ["fixture-home-hero"],
                }
            ],
        }
        _write(
            repo_root / control["receipt_path"],
            json.dumps(receipt, indent=2) + "\n",
        )
        return receipt

    def fake_verify(
        _receipt: dict,
        **_kwargs: object,
    ) -> dict:
        return {
            "schema": ("aureon.design-editorial-asset-candidate-import-verification.v1"),
            "state": "verified-local-candidate",
            "passed": True,
        }

    def fake_audit(
        _manifest_path: Path,
        *,
        repo_root: Path | None = None,
        **_kwargs: object,
    ) -> dict:
        assert repo_root is not None
        return deepcopy(audits[repo_root.resolve()])

    monkeypatch.setattr(runner, "import_editorial_assets_to_candidate", fake_import)
    monkeypatch.setattr(
        runner,
        "verify_candidate_editorial_asset_import",
        fake_verify,
    )
    monkeypatch.setattr(
        runner,
        "audit_design_editorial_asset_provenance_file",
        fake_audit,
    )


def _submission(content: str = "body { color: #234567; }\n") -> dict:
    signal = _feedback_signal()
    return {
        "patch_manifest": [{"path": "styles.css", "content": content}],
        "claim_impact_manifest": [
            {
                "path": "styles.css",
                "classification": "no-material-claim-change",
                "rationale": "The bounded stylesheet refinement does not alter the permitted public claim wording.",
            }
        ],
        "claim_surface_manifest": [],
        "feedback_response_manifest": {
            signal["signal_id"]: {
                "disposition": signal["disposition"],
                "response_code": "addressed",
                "route_scope": signal["route_scope"],
                "changed_paths": ["styles.css"],
                "claim_ids": ["homepage-claim"],
                "signal_capsule_sha256": runner._json_sha256(signal),
            }
        },
    }


def _issue(
    root: Path, monkeypatch: pytest.MonkeyPatch, run_id: str = "broker-style"
) -> tuple[dict, Path, dict]:
    _fake_repo(root)
    staged = _create_staged_run(root, monkeypatch, run_id)
    lease, lease_path = broker.issue_staged_design_worker_lease(
        run_id,
        repo_root=root,
        now=NOW,
        ttl_seconds=60,
    )
    return lease, lease_path, staged


def test_broker_secure_writer_failure_never_unlinks_a_lexical_substitute(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate_root = tmp_path / "candidate"
    candidate_root.mkdir()
    target = candidate_root / "worker-broker" / "lease-issuance.v2.json"
    substitute = b'{"attacker":"lexical-substitute"}\n'

    def fail_after_substitution(output: Path, _payload: bytes) -> None:
        output.write_bytes(substitute)
        raise broker.SecureImmutableArtifactError("fixture handle-bound failure")

    monkeypatch.setattr(broker, "write_new_file", fail_after_substitution)

    with pytest.raises(broker.StagedDesignWorkerBrokerError):
        broker._atomic_no_overwrite_json(
            candidate_root,
            target,
            {"trusted": True},
        )

    assert target.read_bytes() == substitute


def test_broker_executes_exact_html_copy_repair_and_returns_both_validation_outcomes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = "broker-copy-exact"
    baseline_html = _copy_html(include_static_count=True)
    staged = _setup_copy_run(tmp_path, monkeypatch, run_id)
    lease, _ = broker.issue_staged_design_worker_lease(
        run_id,
        repo_root=tmp_path,
        now=NOW,
        ttl_seconds=60,
    )
    restricted = broker._restricted_context(lease)
    signal = lease["worker_context"]["route"]["feedback_capsule"]["signals"][0]["signal"]
    submission = {
        "patch_manifest": [
            {
                "path": COPY_HTML_PATH,
                "content": _copy_html(include_static_count=False),
            }
        ],
        "claim_impact_manifest": [
            {
                "path": COPY_HTML_PATH,
                "classification": "material-claim-change",
                "rationale": (
                    "Removed a stale operating count while preserving the exact "
                    "permitted claim and representation boundary."
                ),
            }
        ],
        "claim_surface_manifest": [],
        "feedback_response_manifest": {
            signal["signal_id"]: {
                "disposition": signal["disposition"],
                "response_code": "addressed",
                "route_scope": signal["route_scope"],
                "changed_paths": [COPY_HTML_PATH],
                "claim_ids": ["evidence-os"],
                "signal_capsule_sha256": runner._json_sha256(signal),
            }
        },
    }

    outcome, outcome_path = broker.submit_staged_design_worker_delivery(
        run_id,
        lease["lease_id"],
        adapter_id=broker.DEFAULT_TRUSTED_ADAPTER_ID,
        submission=submission,
        repo_root=tmp_path,
        now=NOW + timedelta(seconds=1),
    )

    assert lease["route"]["allowed_paths"] == [COPY_HTML_PATH]
    assert restricted.allowed_paths == (COPY_HTML_PATH,)
    assert restricted.investor_copy_repair is not None
    assert (
        restricted.investor_copy_repair["contract_json_sha256"]
        == lease["worker_context"]["investor_copy_repair"]["contract_json_sha256"]
    )
    assert outcome["state"] == "candidate-validated"
    assert outcome["candidate_outcome"]["candidate_validation"]["control_passed"] is True
    assert outcome["candidate_outcome"]["candidate_validation"]["passed"] is True
    assert outcome["candidate_outcome"]["investor_copy_evaluation"]["passed"] is True
    assert outcome_path.is_file()
    assert (tmp_path / "website" / COPY_HTML_PATH).read_text(encoding="utf-8") == baseline_html
    assert (tmp_path / staged["candidate"]["candidate_website"] / COPY_HTML_PATH).read_text(
        encoding="utf-8"
    ) == _copy_html(include_static_count=False)


def test_broker_rejects_unsealed_subset_and_non_html_copy_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = "broker-copy-subset-guard"
    _setup_copy_run(tmp_path, monkeypatch, run_id)
    job, _ = runner.load_latest_delivery_job(run_id, repo_root=tmp_path)
    context = runner.worker_context_for_delivery_job(
        run_id,
        repo_root=tmp_path,
        now=NOW,
    )
    route = broker._route_binding(context)

    stripped = deepcopy(context)
    stripped.pop("investor_copy_repair")
    with pytest.raises(
        broker.StagedDesignWorkerBrokerError,
        match="one-HTML copy subset",
    ):
        broker._sealed_design_directives(
            tmp_path,
            job,
            stripped,
            route,
        )

    non_html = deepcopy(context)
    non_html["route"]["allowed_paths"] = ["styles.css"]
    non_html["mutation_contract"]["text_write_paths"] = ["styles.css"]
    non_html["investor_copy_repair"]["path"] = "styles.css"
    non_html_route = broker._route_binding(non_html)
    with pytest.raises(
        broker.StagedDesignWorkerBrokerError,
        match="exact task, contract, route, HTML",
    ):
        broker._sealed_design_directives(
            tmp_path,
            job,
            non_html,
            non_html_route,
        )


def test_broker_rejects_copy_contract_drift_before_adapter_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = "broker-copy-contract-drift"
    _setup_copy_run(tmp_path, monkeypatch, run_id)
    lease, _ = broker.issue_staged_design_worker_lease(
        run_id,
        repo_root=tmp_path,
        now=NOW,
        ttl_seconds=60,
    )
    job, _ = runner.load_latest_delivery_job(run_id, repo_root=tmp_path)
    contract_path = tmp_path / job["investor_copy_repair"]["path"]
    contract_path.write_text(
        contract_path.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )
    signal = lease["worker_context"]["route"]["feedback_capsule"]["signals"][0]["signal"]
    submission = {
        "patch_manifest": [
            {
                "path": COPY_HTML_PATH,
                "content": _copy_html(include_static_count=False),
            }
        ],
        "claim_impact_manifest": [
            {
                "path": COPY_HTML_PATH,
                "classification": "material-claim-change",
                "rationale": "Bounded exact HTML copy repair.",
            }
        ],
        "claim_surface_manifest": [],
        "feedback_response_manifest": {
            signal["signal_id"]: {
                "disposition": signal["disposition"],
                "response_code": "addressed",
                "route_scope": signal["route_scope"],
                "changed_paths": [COPY_HTML_PATH],
                "claim_ids": ["evidence-os"],
                "signal_capsule_sha256": runner._json_sha256(signal),
            }
        },
    }

    with pytest.raises(
        broker.StagedDesignWorkerBrokerError,
        match="Delivery job no longer verifies",
    ):
        broker.submit_staged_design_worker_delivery(
            run_id,
            lease["lease_id"],
            adapter_id=broker.DEFAULT_TRUSTED_ADAPTER_ID,
            submission=submission,
            repo_root=tmp_path,
            now=NOW + timedelta(seconds=1),
        )

    candidate = tmp_path / job["candidate"]["candidate_website"] / COPY_HTML_PATH
    assert candidate.read_text(encoding="utf-8") == _copy_html(include_static_count=True)


@pytest.mark.parametrize("nested", [False, True])
def test_broker_rejects_all_worker_test_manifests_before_adapter_or_runner_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, nested: bool
) -> None:
    suffix = "nested" if nested else "legacy"
    lease, lease_path, staged = _issue(tmp_path, monkeypatch, f"broker-test-{suffix}")
    candidate_stylesheet = tmp_path / staged["candidate"]["candidate_website"] / "styles.css"
    candidate_before = candidate_stylesheet.read_text(encoding="utf-8")
    submission = _submission()
    worker_assertion = [
        {
            "id": "worker-controlled-pass",
            "status": "passed",
            "evidence": "A worker string is not trusted QA evidence.",
        }
    ]
    if nested:
        submission["feedback_response_manifest"]["nested-test-manifest"] = {"test_manifest": worker_assertion}
    else:
        submission["test_manifest"] = worker_assertion

    def validation_must_not_run(*_args, **_kwargs):
        raise AssertionError("Runner validation must not run for worker-controlled QA")

    monkeypatch.setattr(runner, "validate_design_delivery_job", validation_must_not_run)

    with pytest.raises(
        broker.StagedDesignWorkerBrokerError,
        match="no test-manifest",
    ):
        broker.submit_staged_design_worker_delivery(
            f"broker-test-{suffix}",
            lease["lease_id"],
            adapter_id=broker.DEFAULT_TRUSTED_ADAPTER_ID,
            submission=submission,
            repo_root=tmp_path,
            now=NOW + timedelta(seconds=1),
        )

    assert candidate_stylesheet.read_text(encoding="utf-8") == candidate_before
    broker_root = lease_path.parent.parent
    assert not (broker_root / "executions").exists()
    assert not (broker_root / "outcomes").exists()


def test_broker_seals_design_context_validates_once_and_never_mutates_canonical_site(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lease, lease_path, staged = _issue(tmp_path, monkeypatch)
    canonical_before = (tmp_path / "website" / "styles.css").read_text(encoding="utf-8")
    calls: list[tuple[tuple, dict]] = []
    original_validate = runner.validate_design_delivery_job

    def counted_validate(*args, **kwargs):
        calls.append((args, kwargs))
        return original_validate(*args, **kwargs)

    monkeypatch.setattr(runner, "validate_design_delivery_job", counted_validate)
    outcome, outcome_path = broker.submit_staged_design_worker_delivery(
        "broker-style",
        lease["lease_id"],
        adapter_id=broker.DEFAULT_TRUSTED_ADAPTER_ID,
        submission=_submission(),
        repo_root=tmp_path,
        now=NOW + timedelta(seconds=1),
    )

    directives = lease["design_directives"]
    assert directives["route_purpose"].startswith("Lead with the evidence-control wedge")
    assert directives["content_order"] == ["Decision problem", "Evidence method", "Bounded proof"]
    assert directives["visual_rules"][0]["reduced_motion_required"] is True
    assert "customer adoption" in directives["prohibited_public_inferences"]
    assert lease["worker_context_sha256"]
    assert lease["work_order"]["sha256"]
    assert lease["route"]["claim_capsule_sha256"]
    assert lease["route"]["feedback_capsule_sha256"]
    assert lease["design_directives"]["stakeholder_feedback"]["source_content_available"] is False
    assert lease["workspace_snapshot"]["tree_sha256"]
    assert broker._restricted_context(lease).editorial_authoring_contract is None
    assert lease_path.is_file()
    assert "worker-broker/leases" in lease_path.as_posix()
    assert len(calls) == 1
    assert outcome["state"] == "candidate-validated"
    assert outcome["candidate_outcome"]["state"] == "candidate-validated"
    assert outcome["release_eligible"] is False
    assert outcome["package_authority"] == "none"
    assert outcome["deployment_authority"] == "none"
    assert outcome["credential_access"] == "none"
    assert outcome["manifest_summary"]["feedback_addressed_signal_ids"] == ["fixture-first-visit-clarity"]
    assert outcome_path.is_file()
    assert "worker-broker/outcomes" in outcome_path.as_posix()
    assert (tmp_path / "website" / "styles.css").read_text(encoding="utf-8") == canonical_before
    candidate_style = tmp_path / staged["candidate"]["candidate_website"] / "styles.css"
    assert candidate_style.read_text(encoding="utf-8") == "body { color: #234567; }\n"


def test_broker_requires_binary_asset_ready_and_leases_only_controlled_text_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_repo(tmp_path)
    _patch_fake_editorial_import(monkeypatch)
    run_id = "broker-binary-assets"
    _write(tmp_path / "website" / "assets" / "hero.webp", "fixture-webp-bytes")
    _write(
        tmp_path / "data" / "website_operator" / "editorial_asset_provenance.v1.json",
        '{"schema":"fixture-source-binding"}\n',
    )
    brief = _brief_document()
    brief["route_plan"][0]["allowed_paths"].append("assets/hero.webp")
    _write(
        tmp_path / "data" / "website_operator" / "investor_site_design_brief.v1.json",
        json.dumps(brief, indent=2) + "\n",
    )
    audit = _brief_audit(tmp_path)
    audit["route_plan"][0]["allowed_paths"].append("assets/hero.webp")
    monkeypatch.setattr(
        runner,
        "audit_design_evidence_brief_file",
        lambda **_kwargs: deepcopy(audit),
    )
    runner.create_design_delivery_job(
        goal="Refine text around one trusted editorial asset.",
        route_id="home",
        reconciliation_receipt=_aligned_reconciliation(tmp_path, run_id),
        run_id=run_id,
        repo_root=tmp_path,
        now=NOW,
    )
    runner.stage_design_delivery_job(run_id, repo_root=tmp_path, now=NOW)

    with pytest.raises(
        broker.StagedDesignWorkerBrokerError,
        match="candidate-assets-ready",
    ):
        broker.issue_staged_design_worker_lease(
            run_id,
            repo_root=tmp_path,
            now=NOW,
            ttl_seconds=60,
        )

    ready_job, _ = runner.prepare_design_delivery_assets(
        run_id,
        repo_root=tmp_path,
        now=NOW,
    )
    lease, _ = broker.issue_staged_design_worker_lease(
        run_id,
        repo_root=tmp_path,
        now=NOW,
        ttl_seconds=60,
    )

    assert ready_job["state"] == "candidate-assets-ready"
    assert lease["route"]["allowed_paths"] == ["index.html", "styles.css"]
    assert "assets/hero.webp" not in lease["route"]["allowed_paths"]
    mutation = lease["worker_context"]["mutation_contract"]
    assert mutation["text_write_paths"] == ["index.html", "styles.css"]
    assert mutation["binary_read_authority"] == "none"
    assert mutation["binary_write_authority"] == "none"
    assert mutation["binary_import_authority"] == "none"
    assert lease["worker_context"]["asset_import"]["assets_ready"] is True
    restricted = broker._restricted_context(lease)
    authoring = restricted.editorial_authoring_contract
    assert authoring is not None
    assert authoring["schema"] == runner.EDITORIAL_AUTHORING_CONTRACT_SCHEMA
    assert authoring["surfaces"][0] == {
        "route": "/",
        "destination": "index.html",
        "surface_id": "fixture-home-hero",
        "public_post_url": "https://example.substack.com/p/fixture-hero",
        "variants": [
            {
                "role": "large",
                "public_path": "assets/hero.webp",
                "media_type": "image/webp",
                "width": 1600,
                "height": 900,
            }
        ],
        "alt": "Aureon research evidence illustration",
        "caption": "Research evidence translated into a bounded public explanation.",
        "credit": "Artwork supplied for the linked Aureon research article.",
    }
    assert set(authoring["surfaces"][0]) == broker._AUTHORING_SURFACE_FIELDS
    assert set(authoring["surfaces"][0]["variants"][0]) == (broker._AUTHORING_VARIANT_FIELDS)
    assert "binary asset read" in restricted.prohibited_operations
    assert "binary asset write" in restricted.prohibited_operations
    assert "binary asset import" in restricted.prohibited_operations

    tampered_context = deepcopy(lease["worker_context"])
    tampered_context["route"]["allowed_paths"].append("assets/hero.webp")
    tampered_context["mutation_contract"]["text_write_paths"].append("assets/hero.webp")
    with pytest.raises(
        broker.StagedDesignWorkerBrokerError,
        match="controlled text write paths",
    ):
        broker._route_binding(tampered_context)

    tampered_authoring = deepcopy(lease["worker_context"])
    tampered_authoring["asset_import"]["authoring_contract"]["surfaces"][0]["credit"] = (
        "Untrusted replacement credit."
    )
    with pytest.raises(
        broker.StagedDesignWorkerBrokerError,
        match="contract hash",
    ):
        broker._editorial_authoring_binding(
            tampered_authoring,
            lease["route"],
            assets_required=True,
        )


def test_broker_requires_an_explicit_hash_only_claim_surface_manifest_before_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lease, lease_path, staged = _issue(tmp_path, monkeypatch, "broker-surface-manifest")
    candidate_stylesheet = tmp_path / staged["candidate"]["candidate_website"] / "styles.css"
    before = candidate_stylesheet.read_text(encoding="utf-8")
    submission = _submission()
    submission.pop("claim_surface_manifest")

    with pytest.raises(broker.StagedDesignWorkerBrokerError, match="claim-surface manifest list"):
        broker.submit_staged_design_worker_delivery(
            "broker-surface-manifest",
            lease["lease_id"],
            adapter_id=broker.DEFAULT_TRUSTED_ADAPTER_ID,
            submission=submission,
            repo_root=tmp_path,
            now=NOW + timedelta(seconds=1),
        )

    assert candidate_stylesheet.read_text(encoding="utf-8") == before
    assert not (lease_path.parent.parent / "executions").exists()


def test_broker_rejects_free_form_claim_surface_rationale_before_worker_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lease, lease_path, staged = _issue(tmp_path, monkeypatch, "broker-surface-rationale")
    candidate_stylesheet = tmp_path / staged["candidate"]["candidate_website"] / "styles.css"
    before = candidate_stylesheet.read_text(encoding="utf-8")
    submission = _submission()
    submission["claim_surface_manifest"] = [
        {
            "path": "styles.css",
            "kind": "non-claim",
            "claim_id": "",
            "text_sha256": "A" * 64,
            "surface_sha256": "B" * 64,
            "rationale": "Aureon has customer adoption in regulated sectors.",
        }
    ]

    with pytest.raises(broker.StagedDesignWorkerBrokerError, match="claim-surface manifest entry"):
        broker.submit_staged_design_worker_delivery(
            "broker-surface-rationale",
            lease["lease_id"],
            adapter_id=broker.DEFAULT_TRUSTED_ADAPTER_ID,
            submission=submission,
            repo_root=tmp_path,
            now=NOW + timedelta(seconds=1),
        )

    assert candidate_stylesheet.read_text(encoding="utf-8") == before
    assert not (lease_path.parent.parent / "executions").exists()


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("missing", "feedback-response manifest"),
        ("free-form", "unsupported or free-form fields"),
        ("unknown-signal", "close every route signal exactly once"),
        ("unpatched-path", "must bind actual patch paths"),
    ],
)
def test_broker_requires_exact_closed_stakeholder_feedback_before_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
    message: str,
) -> None:
    run_id = f"broker-feedback-{mutation}"
    lease, lease_path, staged = _issue(tmp_path, monkeypatch, run_id)
    candidate_stylesheet = tmp_path / staged["candidate"]["candidate_website"] / "styles.css"
    before = candidate_stylesheet.read_text(encoding="utf-8")
    submission = _submission()
    signal_id = "fixture-first-visit-clarity"
    if mutation == "missing":
        submission.pop("feedback_response_manifest")
    elif mutation == "free-form":
        submission["feedback_response_manifest"][signal_id]["rationale"] = "Unbounded private interpretation."
    elif mutation == "unknown-signal":
        response = submission["feedback_response_manifest"].pop(signal_id)
        submission["feedback_response_manifest"]["unknown-signal"] = response
    else:
        submission["feedback_response_manifest"][signal_id]["changed_paths"] = ["index.html"]

    with pytest.raises(broker.StagedDesignWorkerBrokerError, match=message):
        broker.submit_staged_design_worker_delivery(
            run_id,
            lease["lease_id"],
            adapter_id=broker.DEFAULT_TRUSTED_ADAPTER_ID,
            submission=submission,
            repo_root=tmp_path,
            now=NOW + timedelta(seconds=1),
        )

    assert candidate_stylesheet.read_text(encoding="utf-8") == before
    assert not (lease_path.parent.parent / "executions").exists()


def test_broker_rejects_expired_lease_and_does_not_touch_candidate_or_canonical(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lease, _, staged = _issue(tmp_path, monkeypatch, "broker-expiry")
    canonical_before = (tmp_path / "website" / "styles.css").read_text(encoding="utf-8")
    candidate_before = (tmp_path / staged["candidate"]["candidate_website"] / "styles.css").read_text(
        encoding="utf-8"
    )

    with pytest.raises(broker.StagedDesignWorkerBrokerError, match="already has worker evidence"):
        broker.issue_staged_design_worker_lease(
            "broker-expiry",
            repo_root=tmp_path,
            now=NOW + timedelta(seconds=1),
            ttl_seconds=60,
        )

    with pytest.raises(broker.StagedDesignWorkerBrokerError, match="expired"):
        broker.submit_staged_design_worker_delivery(
            "broker-expiry",
            lease["lease_id"],
            adapter_id=broker.DEFAULT_TRUSTED_ADAPTER_ID,
            submission=_submission(),
            repo_root=tmp_path,
            now=NOW + timedelta(seconds=61),
        )

    assert (tmp_path / "website" / "styles.css").read_text(encoding="utf-8") == canonical_before
    assert (tmp_path / staged["candidate"]["candidate_website"] / "styles.css").read_text(
        encoding="utf-8"
    ) == candidate_before


def test_broker_rejects_reused_lease_and_keeps_outcome_receipt_immutable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lease, _, _ = _issue(tmp_path, monkeypatch, "broker-reuse")
    _, outcome_path = broker.submit_staged_design_worker_delivery(
        "broker-reuse",
        lease["lease_id"],
        adapter_id=broker.DEFAULT_TRUSTED_ADAPTER_ID,
        submission=_submission(),
        repo_root=tmp_path,
        now=NOW + timedelta(seconds=1),
    )
    outcome_before = outcome_path.read_bytes()

    with pytest.raises(broker.StagedDesignWorkerBrokerError, match="already been consumed"):
        broker.submit_staged_design_worker_delivery(
            "broker-reuse",
            lease["lease_id"],
            adapter_id=broker.DEFAULT_TRUSTED_ADAPTER_ID,
            submission=_submission("body { color: #345678; }\n"),
            repo_root=tmp_path,
            now=NOW + timedelta(seconds=2),
        )
    assert outcome_path.read_bytes() == outcome_before


def test_broker_exposes_only_the_builtin_declarative_manifest_applier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_repo(tmp_path)
    _create_staged_run(tmp_path, monkeypatch, "broker-manifest")

    assert broker.trusted_adapter_ids() == (broker.DEFAULT_TRUSTED_ADAPTER_ID,)
    assert not hasattr(broker, "register_trusted_adapter")
    with pytest.raises(broker.StagedDesignWorkerBrokerError, match="built-in declarative"):
        broker.issue_staged_design_worker_lease(
            "broker-manifest",
            adapter_id="arbitrary-adapter-v1",
            repo_root=tmp_path,
            now=NOW,
            ttl_seconds=60,
        )


def test_broker_rejects_tampered_lease_and_workspace_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lease, lease_path, staged = _issue(tmp_path, monkeypatch, "broker-tamper")
    tampered = json.loads(lease_path.read_text(encoding="utf-8"))
    tampered["workspace_snapshot"]["tree_sha256"] = "0" * 64
    lease_path.write_text(json.dumps(tampered, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(broker.StagedDesignWorkerBrokerError, match="integrity"):
        broker.submit_staged_design_worker_delivery(
            "broker-tamper",
            lease["lease_id"],
            adapter_id=broker.DEFAULT_TRUSTED_ADAPTER_ID,
            submission=_submission(),
            repo_root=tmp_path,
            now=NOW + timedelta(seconds=1),
        )

    lease, _, staged = _issue(tmp_path, monkeypatch, "broker-workspace-tamper")
    candidate_style = tmp_path / staged["candidate"]["candidate_website"] / "styles.css"
    candidate_style.write_text("body { color: #abcdef; }\n", encoding="utf-8")
    with pytest.raises(broker.StagedDesignWorkerBrokerError, match="workspace snapshot"):
        broker.submit_staged_design_worker_delivery(
            "broker-workspace-tamper",
            lease["lease_id"],
            adapter_id=broker.DEFAULT_TRUSTED_ADAPTER_ID,
            submission=_submission(),
            repo_root=tmp_path,
            now=NOW + timedelta(seconds=1),
        )


def test_broker_blocks_path_escape_and_forbidden_authority_fields_before_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lease, _, staged = _issue(tmp_path, monkeypatch, "broker-boundaries")
    canonical_before = (tmp_path / "website" / "styles.css").read_text(encoding="utf-8")
    escaped = _submission()
    escaped["patch_manifest"][0]["path"] = "../website/styles.css"
    escaped["claim_impact_manifest"][0]["path"] = "../website/styles.css"

    with pytest.raises(broker.StagedDesignWorkerBrokerError, match="safe candidate-relative"):
        broker.submit_staged_design_worker_delivery(
            "broker-boundaries",
            lease["lease_id"],
            adapter_id=broker.DEFAULT_TRUSTED_ADAPTER_ID,
            submission=escaped,
            repo_root=tmp_path,
            now=NOW + timedelta(seconds=1),
        )

    forbidden = _submission()
    forbidden["deployment_authority"] = "live"
    with pytest.raises(broker.StagedDesignWorkerBrokerError, match="release, deployment, or credentials"):
        broker.submit_staged_design_worker_delivery(
            "broker-boundaries",
            lease["lease_id"],
            adapter_id=broker.DEFAULT_TRUSTED_ADAPTER_ID,
            submission=forbidden,
            repo_root=tmp_path,
            now=NOW + timedelta(seconds=1),
        )

    binary = _submission()
    binary["patch_manifest"][0]["path"] = "hero.png"
    binary["claim_impact_manifest"][0]["path"] = "hero.png"
    with pytest.raises(broker.StagedDesignWorkerBrokerError, match="text-only"):
        feedback_capsule = _feedback_capsule()
        broker._normalise_submission(
            binary,
            allowed_paths=["hero.png"],
            feedback_capsule=feedback_capsule,
            feedback_capsule_sha256=runner._json_sha256(feedback_capsule),
        )

    assert (tmp_path / "website" / "styles.css").read_text(encoding="utf-8") == canonical_before
    assert (tmp_path / staged["candidate"]["candidate_website"] / "styles.css").read_text(
        encoding="utf-8"
    ) == canonical_before


def test_broker_rejects_a_hard_linked_candidate_file_before_issuing_a_lease(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_repo(tmp_path)
    staged = _create_staged_run(tmp_path, monkeypatch, "broker-hard-link")
    canonical_stylesheet = tmp_path / "website" / "styles.css"
    candidate_stylesheet = tmp_path / staged["candidate"]["candidate_website"] / "styles.css"
    canonical_before = canonical_stylesheet.read_bytes()
    candidate_stylesheet.unlink()
    try:
        os.link(canonical_stylesheet, candidate_stylesheet)
    except OSError as exc:
        pytest.skip(f"Hard links are unavailable on this filesystem: {exc}")

    with pytest.raises(broker.StagedDesignWorkerBrokerError, match="worker context is withheld|hard link"):
        broker.issue_staged_design_worker_lease(
            "broker-hard-link",
            repo_root=tmp_path,
            now=NOW,
            ttl_seconds=60,
        )

    assert canonical_stylesheet.read_bytes() == canonical_before


def test_broker_snapshot_rejects_an_outside_directory_link_before_hashing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_repo(tmp_path)
    staged = _create_staged_run(
        tmp_path,
        monkeypatch,
        "broker-linked-tree",
    )
    context = runner.worker_context_for_delivery_job(
        "broker-linked-tree",
        repo_root=tmp_path,
        now=NOW,
    )
    outside = tmp_path / "outside-worker-tree"
    _write(outside / "must-not-enter-snapshot.txt", "outside\n")
    candidate_site = tmp_path / staged["candidate"]["candidate_website"]
    linked = candidate_site / "linked-outside"
    try:
        os.symlink(outside, linked, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"Directory symlink or junction-style reparse points are unavailable: {exc}")

    with pytest.raises(
        broker.StagedDesignWorkerBrokerError,
        match="symbolic links or reparse points",
    ):
        broker._candidate_workspace_snapshot(  # noqa: SLF001 - walker boundary under test
            tmp_path,
            staged,
            context,
        )


def test_broker_accepts_only_builtin_adapter_and_has_no_release_entrypoints(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_repo(tmp_path)
    _create_staged_run(tmp_path, monkeypatch, "broker-adapter-id")

    with pytest.raises(broker.StagedDesignWorkerBrokerError, match="built-in declarative"):
        broker.issue_staged_design_worker_lease(
            "broker-adapter-id",
            adapter_id="arbitrary-adapter-v1",
            repo_root=tmp_path,
            now=NOW,
        )

    forbidden_entrypoints = {"deploy", "build_package", "promote_candidate", "read_credentials"}
    assert not (forbidden_entrypoints & set(dir(broker)))
    assert broker.AUTHORITY["canonical_website_mutation"].startswith("never")
    assert broker.AUTHORITY["package_authority"] == "none"
    assert broker.AUTHORITY["deployment_authority"] == "none"
