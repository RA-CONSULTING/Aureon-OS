"""Regression coverage for the source-bound focused candidate gate."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aureon.operator import design_candidate_source_closure as source_closure
from aureon.operator.design_candidate_control import (
    create_design_work_order,
    stage_design_candidate,
    validate_design_candidate,
    write_design_candidate_receipt,
    write_design_work_order,
)
from aureon.operator.design_candidate_initial_gate import (
    DesignCandidateInitialGateError,
    evaluate_initial_candidate_gate,
    snapshot_website_tree,
    write_initial_candidate_gate,
)
from aureon.operator.live_surface_reconciliation import (
    reconcile_live_surface,
    write_live_surface_reconciliation,
)

NOW = datetime(2026, 7, 28, 15, 0, tzinfo=UTC)
REPO_ROOT = Path(__file__).resolve().parents[1]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _copy_executable_source_closure(destination_root: Path) -> None:
    executable_closure = source_closure.build_source_closure(REPO_ROOT)
    for row in executable_closure["files"]:
        relative = Path(str(row["path"]))
        destination = destination_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / relative, destination)


def _fake_repo(root: Path) -> None:
    _write(root / "pyproject.toml", "[tool.pytest.ini_options]\n")
    (root / "aureon" / "operator").mkdir(parents=True)
    _write(root / "aureon" / "operator" / "website_operator.defaults.json", '{"policy":"test"}\n')
    _write(root / "website" / ".htaccess", "Options -Indexes\n")
    _write(
        root / "website" / "index.html",
        "<!doctype html><title>Aureon</title><p>Evidence, boundary and human review. "
        "This fixture is not evidence of customer adoption or independent validation.</p>\n",
    )
    _write(root / "website" / "styles.css", "body { color: #123456; }\n")
    register = {
        "schema": "aureon.public-claim-evidence-register.v1",
        "generated_at": "2026-07-28T15:00:00Z",
        "scope": "fixture public claim",
        "authority": {
            "scope": "read-only public-claim evidence control",
            "release_eligible": False,
            "deployment_authority": "none",
            "package_authority": "none",
            "human_review": "required",
        },
        "claims": [
            {
                "id": "fixture-claim",
                "title": "Fixture claim",
                "claim": "Aureon is evidence-led.",
                "state": "company-authored",
                "boundary": "This fixture is not evidence of customer adoption or independent validation.",
                "permitted_wording": ["Aureon is evidence-led."],
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
    _copy_executable_source_closure(root)


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


def _candidate(root: Path, run_id: str) -> tuple[Path, Path]:
    _fake_repo(root)
    order = create_design_work_order(
        goal="Test the staged initial browser gate.",
        allowed_paths=["styles.css"],
        routes=["/"],
        reconciliation_receipt=_aligned_reconciliation(root, run_id),
        run_id=run_id,
        repo_root=root,
        now=NOW,
    )
    order_path = write_design_work_order(
        order,
        root / "artifacts" / "website-candidates" / "work-orders" / f"{run_id}.v4.json",
        repo_root=root,
    )
    stage_design_candidate(order_path, repo_root=root)
    candidate_root = root / order["candidate_layout"]["root"]
    _write(candidate_root / "website" / "styles.css", "body { color: #234567; }\n")
    receipt = validate_design_candidate(
        order_path,
        claim_impacts=[
            {
                "path": "styles.css",
                "classification": "no-material-claim-change",
                "rationale": "This fixture changes no public claim text.",
            }
        ],
        repo_root=root,
        now=NOW,
    )
    assert receipt["passed"] is True
    receipt_path = write_design_candidate_receipt(
        receipt,
        candidate_root / "candidate.v1.json",
        repo_root=root,
    )
    return candidate_root, receipt_path


def _focused_visual(
    candidate_root: Path,
    *,
    geometry_pass: bool,
    long_task_pass: bool,
) -> Path:
    visual_path = candidate_root / "browser-qa" / "run-01" / "focused.json"
    geometry = {
        "status": "RAN",
        "pass": geometry_pass,
        "candidateCount": 1,
        "deltas": {"scrollHeightPx": 0 if geometry_pass else 48},
        "failureReasons": [] if geometry_pass else ["scroll-height:48>2"],
    }
    performance_pass = geometry_pass and long_task_pass
    visual = {
        "status": "PASS" if performance_pass else "FAIL",
        "selfHosted": True,
        "sourceBinding": {
            "before": snapshot_website_tree(candidate_root / "website"),
            "stable": True,
            "servedFromHashedSource": True,
        },
        "engines": [
            {
                "engine": "chromium",
                "status": "PASS" if performance_pass else "FAIL",
                "diagnostics": {"warnings": [], "errors": []},
                "engineWideDiagnostics": {"warnings": [], "errors": []},
                "routes": [
                    {
                        "name": "research",
                        "route": "/research/",
                        "status": 200,
                        "pass": True,
                        "errors": [],
                        "warnings": [],
                        "resourceFailures": [],
                    }
                ],
                "performance": [
                    {
                        "routeName": "research",
                        "route": "/research/",
                        "pass": performance_pass,
                        "metrics": {"longTaskTotalMs": 280 if long_task_pass else 307},
                        "budgets": {"longTaskTotalMs": 300},
                        "checks": {
                            "ttfb": {"pass": True},
                            "longTaskTotal": {"pass": long_task_pass},
                        },
                        "renderingGeometry": geometry,
                        "errors": [],
                        "warnings": [],
                        "resourceFailures": [],
                    }
                ],
            }
        ],
    }
    _write(visual_path, json.dumps(visual, indent=2) + "\n")
    return visual_path


def test_initial_gate_rejects_failed_performance_without_permitting_repeatability(tmp_path: Path) -> None:
    candidate_root, candidate_receipt = _candidate(tmp_path, "initial-perf-fail")
    visual = _focused_visual(candidate_root, geometry_pass=True, long_task_pass=False)

    receipt = evaluate_initial_candidate_gate(
        candidate_receipt,
        visual,
        route_name="research",
        repo_root=tmp_path,
        now=NOW,
    )

    assert receipt["state"] == "rejected-performance"
    assert receipt["passed"] is False
    assert receipt["repeatability_series_permitted"] is False
    assert receipt["release_eligible"] is False
    performance = next(item for item in receipt["checks"] if item["id"] == "initial-performance")
    assert performance["passed"] is False
    assert performance["evidence"]["failed_checks"] == ["longTaskTotal"]


def test_initial_gate_rejects_geometry_before_any_performance_series(tmp_path: Path) -> None:
    candidate_root, candidate_receipt = _candidate(tmp_path, "initial-geometry-fail")
    visual = _focused_visual(candidate_root, geometry_pass=False, long_task_pass=True)

    receipt = evaluate_initial_candidate_gate(
        candidate_receipt,
        visual,
        route_name="research",
        repo_root=tmp_path,
        now=NOW,
    )

    assert receipt["state"] == "rejected-geometry"
    assert receipt["repeatability_series_permitted"] is False
    geometry = next(item for item in receipt["checks"] if item["id"] == "deferred-render-geometry")
    assert geometry["passed"] is False


def test_initial_gate_permits_repeatability_but_never_release(tmp_path: Path) -> None:
    candidate_root, candidate_receipt = _candidate(tmp_path, "initial-pass")
    visual = _focused_visual(candidate_root, geometry_pass=True, long_task_pass=True)

    receipt = evaluate_initial_candidate_gate(
        candidate_receipt,
        visual,
        route_name="research",
        repo_root=tmp_path,
        now=NOW,
    )

    assert receipt["state"] == "eligible-for-repeatability"
    assert receipt["passed"] is True
    assert receipt["repeatability_series_permitted"] is True
    assert receipt["release_eligible"] is False
    output = write_initial_candidate_gate(
        receipt,
        candidate_root / "feedback" / "initial-gate.json",
        repo_root=tmp_path,
    )
    assert output.is_file()
    with pytest.raises(DesignCandidateInitialGateError):
        write_initial_candidate_gate(receipt, tmp_path / "outside.json", repo_root=tmp_path)


def test_initial_gate_blocks_changed_candidate_after_browser_capture(tmp_path: Path) -> None:
    candidate_root, candidate_receipt = _candidate(tmp_path, "initial-source-drift")
    visual = _focused_visual(candidate_root, geometry_pass=True, long_task_pass=True)
    _write(candidate_root / "website" / "styles.css", "body { color: #345678; }\n")

    receipt = evaluate_initial_candidate_gate(
        candidate_receipt,
        visual,
        route_name="research",
        repo_root=tmp_path,
        now=NOW,
    )

    assert receipt["state"] == "blocked"
    assert receipt["repeatability_series_permitted"] is False
    source = next(item for item in receipt["checks"] if item["id"] == "focused-source-binding")
    assert source["passed"] is False
