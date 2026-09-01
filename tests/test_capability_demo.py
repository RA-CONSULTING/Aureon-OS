"""Fail-closed tests for the unreleased capability preflight facade."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from aureon.saas import capability_demo as cd


@pytest.fixture(scope="module")
def result():
    # The committed report is stale, so fast mode must stop before app construction.
    return cd.demonstrate(fast=True)


def test_stale_report_forces_aggregate_unhealthy(result):
    assert result["healthy"] is False


def test_stale_fast_preflight_exercises_no_capability_class(result):
    assert result["capability_classes"] == []


def test_no_live_exercise_rows_exist(result):
    faults = [r for c in result["capability_classes"] for r in c["exercised"] if r["status"] == "fault"]
    assert faults == [], f"faulting exercises: {faults}"


def test_stale_fast_preflight_does_not_call_mcp(result):
    assert result["capability_classes"] == []


def test_stale_fast_preflight_does_not_probe_providers(result):
    assert "no app" in result["note"]
    assert "provider" in result["note"]


def test_stale_fast_preflight_runs_no_rollup_suite(result):
    assert result["suites"] == []


def test_stale_tier_a_is_not_promoted_to_a_pass(result):
    tier = result["tier_a"]
    assert tier["mode"] == "stale_report"
    assert tier["total"] == 0
    assert tier["passed"] == 0
    assert tier["failures"] == ["committed report is stale/superseded release evidence"]
    assert tier["production_ready"] is False
    assert tier["current_effect_claim"] is False


def test_coverage_complete(result):
    assert result["coverage_complete"] is False


def test_report_is_byte_identical_on_rewrite(result, tmp_path):
    a_md, a_json = tmp_path / "a.md", tmp_path / "a.json"
    b_md, b_json = tmp_path / "b.md", tmp_path / "b.json"
    cd.write_capability_report(result, a_md, a_json)
    cd.write_capability_report(result, b_md, b_json)
    assert a_md.read_bytes() == b_md.read_bytes()
    assert a_json.read_bytes() == b_json.read_bytes()


def test_cli_main_exits_nonzero_for_stale_report(tmp_path):
    assert cd.main([]) == 1
    assert cd.main(["--fast"]) == 1
    out = tmp_path / "cap.md"
    assert cd.main(["--fast", "--report", str(out)]) == 1
    assert out.exists() and out.read_text(encoding="utf-8").startswith("# Aureon OS — capability demonstration")


@pytest.mark.parametrize(
    "release_fields",
    [
        {},
        {"report_status": "STALE_SUPERSEDED", "production_ready": False,
         "current_effect_claim": False},
        {"report_status": "CURRENT", "production_ready": False,
         "current_effect_claim": True},
        {"report_status": "CURRENT", "production_ready": True,
         "current_effect_claim": False},
    ],
)
def test_fast_tier_a_rejects_missing_or_noncurrent_release_attestation(
    monkeypatch, tmp_path, release_fields,
):
    report_dir = tmp_path / "tests" / "benchmarks"
    report_dir.mkdir(parents=True)
    (report_dir / "report.json").write_text(
        json.dumps({
            **release_fields,
            "tier_a": [{"name": "historical pass", "passed": True}],
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(cd, "_REPO_ROOT", tmp_path)

    out = cd._run_tier_a(fast=True)

    assert out["mode"] == "stale_report"
    assert out["passed"] == out["total"] == 0
    assert out["historical_total"] == 1
    assert out["failures"]


def test_fast_tier_a_rejects_non_mapping_report(monkeypatch, tmp_path):
    report_dir = tmp_path / "tests" / "benchmarks"
    report_dir.mkdir(parents=True)
    (report_dir / "report.json").write_text("[]", encoding="utf-8")
    monkeypatch.setattr(cd, "_REPO_ROOT", tmp_path)

    out = cd._run_tier_a(fast=True)

    assert out["mode"] == "unavailable_report"
    assert out["passed"] == out["total"] == 0
    assert out["failures"] == ["report.json must contain a JSON object"]


def test_fast_tier_a_bounds_report_read_and_requires_exact_boolean_abi(
    monkeypatch, tmp_path
):
    report_dir = tmp_path / "tests" / "benchmarks"
    report_dir.mkdir(parents=True)
    report_path = report_dir / "report.json"
    monkeypatch.setattr(cd, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(cd, "_MAX_COMMITTED_REPORT_BYTES", 128)

    report_path.write_bytes(b"{" + b" " * 128 + b"}")
    oversized = cd._run_tier_a(fast=True)
    assert oversized["mode"] == "unavailable_report"
    assert "metadata read limit" in oversized["failures"][0]

    monkeypatch.setattr(cd, "_MAX_COMMITTED_REPORT_BYTES", 4096)
    report_path.write_text(
        json.dumps(
            {
                "report_status": "CURRENT",
                "production_ready": True,
                "current_effect_claim": True,
                "tier_a": [{"name": "truthy integer", "passed": 1}],
            }
        ),
        encoding="utf-8",
    )
    invalid_abi = cd._run_tier_a(fast=True)
    assert invalid_abi == {
        "passed": 0,
        "total": 0,
        "failures": ["current report tier_a rows have an invalid result ABI"],
        "mode": "unavailable_report",
    }


def test_stale_fast_demonstration_holds_before_app_construction(
    monkeypatch, tmp_path,
):
    report_dir = tmp_path / "tests" / "benchmarks"
    report_dir.mkdir(parents=True)
    (report_dir / "report.json").write_text(json.dumps({
        "report_status": "STALE_SUPERSEDED",
        "production_ready": False,
        "current_effect_claim": False,
        "tier_a": [{"name": "historical pass", "passed": True}],
    }), encoding="utf-8")
    monkeypatch.setattr(cd, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        cd,
        "_build_app",
        lambda: pytest.fail("stale fast preflight must not construct the app"),
    )

    out = cd.demonstrate(fast=True)

    assert out["healthy"] is False
    assert out["capability_classes"] == []
    assert out["suites"] == []
    assert out["tier_a"]["mode"] == "stale_report"


@pytest.mark.parametrize(
    "live_helper",
    [
        lambda: cd._build_app(),
        lambda: cd._exercise(object(), "POST", "/api/providers/x/test", {}),
        lambda: cd._rollup_suites(),
        lambda: cd._load_benchmark_module(),
        lambda: cd._run_tier_a(fast=False),
    ],
)
def test_every_direct_live_helper_returns_the_exact_release_hold(live_helper):
    with pytest.raises(RuntimeError) as exc:
        live_helper()
    assert str(exc.value) == cd.CAPABILITY_DEMO_RELEASE_HOLD


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"fast": False},
        {"fast": True, "run_tier_a": False},
        {"app": object(), "fast": False},
    ],
)
def test_default_and_live_or_skip_variants_hold_without_runtime_owners(
    monkeypatch, kwargs,
):
    def trap(*_args, **_kwargs):
        pytest.fail("held path touched a live owner")

    monkeypatch.setattr(cd, "_build_app", trap)
    monkeypatch.setattr(cd, "_exercise", trap)
    monkeypatch.setattr(cd, "_rollup_suites", trap)
    monkeypatch.setattr(cd, "_load_benchmark_module", trap)

    out = cd.demonstrate(**kwargs)

    assert out["status"] == "HOLD"
    assert out["reason_code"] == cd.CAPABILITY_DEMO_RELEASE_HOLD
    assert out["production_ready"] is False
    assert out["current_effect_claim"] is False
    assert out["healthy"] is False


def test_fresh_process_default_and_fast_are_effect_free_and_exit_nonzero() -> None:
    repo_root = Path(cd.__file__).resolve().parents[2]
    env = os.environ.copy()
    env.update({
        "PYTHONDONTWRITEBYTECODE": "1",
        "AUREON_DISABLE_LLM_HTTP": "1",
        "AUREON_AUDIT_MODE": "1",
    })
    trap_script = r'''
import sys
import threading
from pathlib import Path

threads_before = {thread.ident for thread in threading.enumerate()}

def reject_resolve(*_args, **_kwargs):
    raise AssertionError("capability facade resolved a filesystem path during import")

Path.resolve = reject_resolve
from aureon.saas import capability_demo as cd
threads_after = {thread.ident for thread in threading.enumerate()}
assert threads_after == threads_before
assert "aureon.operator.operator_server" not in sys.modules
assert "aureon_benchmark_scope" not in sys.modules

def trap(*_args, **_kwargs):
    raise AssertionError("capability facade touched a live owner")

cd._build_app = trap
cd._exercise = trap
cd._rollup_suites = trap
cd._load_benchmark_module = trap
assert cd.main([]) == 1
assert cd.main(["--fast", "--json"]) == 1
try:
    cd._run_tier_a(fast=False)
except RuntimeError as exc:
    assert str(exc) == cd.CAPABILITY_DEMO_RELEASE_HOLD
else:
    raise AssertionError("live Tier-A path did not HOLD")
'''
    trapped = subprocess.run(
        [sys.executable, "-B", "-c", trap_script],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert trapped.returncode == 0, trapped.stderr

    for args in ([], ["--fast", "--json"]):
        completed = subprocess.run(
            [sys.executable, "-B", "-m", "aureon.saas.capability_demo", *args],
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert completed.returncode == 1, completed.stderr
