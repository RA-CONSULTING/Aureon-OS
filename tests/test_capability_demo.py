"""Tests for the capability demonstration — the "prove it in one command" one-shot.

Boots the operator app in-process and asserts the full capability surface is exercised honestly: every
capability class proven (no faults, parity all-served), the MCP read-only call crosses the membrane
laminarly, every rolled-up self-test suite is green, coverage is complete, and an offline test-probe
lands as an honest verdict — never a fabricated success and never a silent fault. Read-only; offline.

Tier-A is exercised in ``--fast`` mode (reads the committed ``report.json``) so the test stays quick; the
live 45-benchmark path is covered by the benchmark runner itself.
"""

from __future__ import annotations

import pytest

pytest.importorskip("flask", reason="operator HTTP surface requires the `.[operator]` extra")

from aureon.saas import capability_demo as cd  # noqa: E402

_EXPECTED_CLASSES = {
    "Reasoning", "Operator + conscience", "MCP boundary (end-to-end)",
    "Connections / providers", "SaaS telemetry surface", "Frontend ↔ backend parity",
}


@pytest.fixture(scope="module")
def result():
    # fast=True reads the committed Tier-A report.json; live Tier-A is exercised by the benchmark runner.
    return cd.demonstrate(fast=True)


def test_healthy(result):
    assert result["healthy"] is True


def test_every_capability_class_present_and_proven(result):
    names = {c["name"] for c in result["capability_classes"]}
    assert names == _EXPECTED_CLASSES
    for c in result["capability_classes"]:
        assert c["proven"] is True, f"{c['name']} not proven: {c['exercised']}"


def test_no_fault_across_live_exercises(result):
    faults = [r for c in result["capability_classes"] for r in c["exercised"] if r["status"] == "fault"]
    assert faults == [], f"faulting exercises: {faults}"


def test_mcp_call_is_laminar_end_to_end(result):
    mcp = next(c for c in result["capability_classes"] if c["name"] == "MCP boundary (end-to-end)")
    call = next(r for r in mcp["exercised"] if r["path"] == "/mcp/call")
    assert call["status"] == "ok"
    assert "laminar=True" in call["reason"]


def test_probes_are_honest_never_faults(result):
    probes = next(c for c in result["capability_classes"] if c["name"] == "Connections / providers")
    for r in probes["exercised"]:
        assert r["status"] in ("ok", "honest_unavailable")


def test_rolled_up_suites_all_green(result):
    assert result["suites"], "no self-test suites rolled up"
    for s in result["suites"]:
        assert s["ok"] is True, f"suite RED: {s['name']} — {s['detail']}"
    names = {s["name"] for s in result["suites"]}
    assert {"SaaS compliance audit", "MCP transport membrane", "Repo-wide coverage"} <= names


def test_tier_a_all_pass(result):
    tier = result["tier_a"]
    assert tier["total"] > 0
    assert tier["passed"] == tier["total"], f"Tier-A failures: {tier['failures']}"
    assert tier["failures"] == []


def test_coverage_complete(result):
    assert result["coverage_complete"] is True


def test_report_is_byte_identical_on_rewrite(result, tmp_path):
    a_md, a_json = tmp_path / "a.md", tmp_path / "a.json"
    b_md, b_json = tmp_path / "b.md", tmp_path / "b.json"
    cd.write_capability_report(result, a_md, a_json)
    cd.write_capability_report(result, b_md, b_json)
    assert a_md.read_bytes() == b_md.read_bytes()
    assert a_json.read_bytes() == b_json.read_bytes()


def test_cli_main_exits_zero(tmp_path):
    assert cd.main(["--fast"]) == 0
    out = tmp_path / "cap.md"
    assert cd.main(["--fast", "--report", str(out)]) == 0
    assert out.exists() and out.read_text(encoding="utf-8").startswith("# Aureon OS — capability demonstration")

def test_live_tier_a_branch_reports_a_real_total(monkeypatch):
    """Guards the LIVE Tier-A path, not just ``--fast``.

    Every other test here runs ``fast=True``, which returns from the committed-report branch before
    reaching the live loop — so a NameError in that loop shipped undetected (the default CLI
    invocation, with no ``--fast``, crashed with UnboundLocalError). A stub module keeps this cheap:
    two fake benchmarks exercise the same code path as all 45.
    """
    class _StubModule:
        TIER_A = [("fake_pass", lambda root: {"passed": True}),
                  ("fake_fail", lambda root: {"passed": False})]

    monkeypatch.setattr(cd, "_load_benchmark_module", lambda: _StubModule())
    out = cd._run_tier_a(fast=False)
    assert out["mode"] == "live"
    assert out["total"] == 2          # counted from the benchmarks actually run
    assert out["passed"] == 1
    assert out["failures"] == ["fake_fail"]


def test_live_tier_a_counts_a_raising_benchmark_as_a_failure(monkeypatch):
    def _boom(root):
        raise RuntimeError("nope")

    class _StubModule:
        TIER_A = [("explodes", _boom)]

    monkeypatch.setattr(cd, "_load_benchmark_module", lambda: _StubModule())
    out = cd._run_tier_a(fast=False)
    assert out["total"] == 1 and out["passed"] == 0
    assert out["failures"] == ["explodes: RuntimeError"]
