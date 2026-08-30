"""Tests for the SaaS connection verifier — the repeatable "is every connection wired?" check.

Boots the operator app in-process and asserts (a) every registered JSON GET route returns 200 or an
honest self-declared 503 (never a 500 / crash / HTML), and (b) every endpoint the React console calls —
shell console + legacy trading console — has a matching backend route. Read-only; offline; no network.
"""

from __future__ import annotations

import pytest

pytest.importorskip("flask", reason="operator HTTP surface requires the `.[operator]` extra")

from aureon.saas import connection_verifier as cv  # noqa: E402


def test_surface_has_no_faults():
    report = cv.verify_surface()
    faults = [e.to_dict() for e in report.endpoints if e.status == "fault"]
    assert report.faults == 0, f"faulting endpoints: {faults}"
    assert report.checked > 20            # the surface is real, not empty
    assert report.ok >= report.checked - report.honest_unavailable


def test_honest_unavailable_declares_a_reason():
    # A 503 must be self-declared with a reason (a configured-off feature), never a bare fault.
    report = cv.verify_surface()
    for e in report.endpoints:
        if e.status == "honest_unavailable":
            assert e.reason, f"{e.path} degraded without a declared reason"


def test_frontend_parity_all_served():
    parity = cv.verify_frontend_parity()
    assert parity["all_served"] is True, f"unserved console endpoints: {parity['missing']}"
    assert parity["missing"] == []
    assert parity["expected"] >= 30       # shell + legacy endpoints are actually being checked


def test_legacy_endpoints_are_in_the_parity_set_and_served():
    parity = cv.verify_frontend_parity()
    served = {s["path"] for s in parity["served"]}
    for legacy in ("/api/bots", "/api/trades", "/api/terminal-state", "/api/flight-test",
                   "/api/reboot-advice", "/api/env-credentials", "/api/notifications/telegram"):
        assert legacy in served, f"{legacy} not served after wiring"


def test_verify_all_healthy():
    result = cv.verify_all()
    assert result["healthy"] is True
    assert result["surface"]["faults"] == 0
    assert result["parity"]["all_served"] is True


def test_report_is_byte_identical_on_rewrite(tmp_path):
    result = cv.verify_all()
    a_md, a_json = tmp_path / "a.md", tmp_path / "a.json"
    b_md, b_json = tmp_path / "b.md", tmp_path / "b.json"
    cv.write_connection_report(result, a_md, a_json)
    cv.write_connection_report(result, b_md, b_json)
    assert a_md.read_bytes() == b_md.read_bytes()
    assert a_json.read_bytes() == b_json.read_bytes()


def test_cli_main_exits_zero_when_healthy():
    assert cv.main([]) == 0
