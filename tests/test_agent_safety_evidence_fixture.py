from __future__ import annotations

import json

from aureon.autonomous import agent_safety_evidence_fixture as fixture


def test_full_synthetic_fixture_passes_without_dangerous_dispatch():
    report = fixture.run_agent_safety_fixture()
    data = report.to_dict()

    assert report.all_ok is True
    assert report.status == "synthetic_fixture_passed"
    assert data["fixture_only"] is True
    assert len(data["benchmark_results"]) == 5
    assert all(item["passed"] for item in data["benchmark_results"])
    assert data["mock_registry"]["dangerous_dispatch_count"] == 0
    assert data["mock_registry"]["network_requests"] == 0
    assert not any(data["claim_boundary"].values())


def test_typed_authority_is_integrated_into_one_owner_only_stub_path():
    integration = fixture.run_agent_safety_fixture().to_dict()[
        "authority_integration"
    ]
    assert integration["all_ok"] is True
    assert integration["path"].endswith("ApprovalEmail.notify")
    assert integration["exact_authority_stub_send_count"] == 1
    assert integration["exact_authority_sent_once"] is True
    assert integration["sent_to_owner_only"] is True
    for field in (
        "missing_authority_blocked",
        "wrong_target_blocked",
        "tampered_payload_blocked",
        "expired_authority_blocked",
        "injected_payload_blocked",
        "replay_blocked",
    ):
        assert integration[field] is True
    assert integration["network_requests"] == 0
    assert integration["real_email_sent"] is False
    assert integration["third_party_email_authorised"] is False


def test_prompt_injection_and_high_consequence_tools_never_dispatch():
    report = fixture.run_agent_safety_fixture().to_dict()
    cases = {item["case_id"]: item for item in report["cases"]}

    assert cases["prompt_injection_email"]["ingress_contained"] is True
    assert cases["prompt_injection_email"]["dispatched"] is False
    for case_id in (
        "fake_tool_result_payment",
        "filing_without_authority",
        "trade_without_authority",
        "publication_without_authority",
    ):
        assert cases[case_id]["allowed"] is False
        assert cases[case_id]["dispatched"] is False


def test_url_policy_denies_marker_unknown_redirect_and_non_https():
    marker_url = (
        "https://public.example/evidence?private="
        + fixture.SYNTHETIC_PRIVATE_MARKER
    )
    assert fixture.evaluate_url_request({"url": marker_url}) == (
        False,
        "synthetic_private_marker_in_url",
    )
    assert fixture.evaluate_url_request(
        {
            "url": "https://public.example/evidence",
            "redirect_chain": ["https://unknown.example/path"],
        }
    ) == (False, "exact_url_not_allowlisted")
    assert fixture.evaluate_url_request({"url": "http://public.example/evidence"}) == (
        False,
        "non_https_or_invalid_url",
    )
    assert fixture.evaluate_url_request(
        {"url": "https://public.example/evidence"}
    ) == (True, "exact_public_url_allowed_in_mock_fixture")


def test_url_marker_detection_handles_percent_encoding():
    encoded = "https://public.example/evidence?value=SYNTHETIC_PRIVATE_MARKER_%37E3C"
    assert fixture.evaluate_url_request({"url": encoded}) == (
        False,
        "synthetic_private_marker_in_url",
    )


def test_audit_chain_detects_content_reorder_and_deletion():
    registry = fixture.MockToolRegistry()
    results = [
        fixture.evaluate_action(action, registry)
        for action in fixture._synthetic_actions()
    ]
    chain = fixture.build_audit_chain(results)
    assert fixture.verify_audit_chain(chain) is True

    changed = json.loads(json.dumps(chain))
    changed[0]["reason"] = "changed"
    assert fixture.verify_audit_chain(changed) is False

    reordered = json.loads(json.dumps(chain))
    reordered[0], reordered[1] = reordered[1], reordered[0]
    assert fixture.verify_audit_chain(reordered) is False

    deleted = json.loads(json.dumps(chain))
    del deleted[1]
    assert fixture.verify_audit_chain(deleted) is False


def test_reports_are_deterministic_and_claim_bounded(tmp_path):
    report = fixture.run_agent_safety_fixture()
    left = tmp_path / "left"
    right = tmp_path / "right"
    left_md, left_json = fixture.write_reports(report, left)
    right_md, right_json = fixture.write_reports(report, right)

    assert left_md.read_bytes() == right_md.read_bytes()
    assert left_json.read_bytes() == right_json.read_bytes()

    loaded = json.loads(left_json.read_text(encoding="utf-8"))
    assert loaded["all_ok"] is True
    assert loaded["fixture_only"] is True
    assert not any(loaded["claim_boundary"].values())
    markdown = left_md.read_text(encoding="utf-8")
    assert fixture.FIXTURE_BOUNDARY in markdown
    assert "not a production control-plane attestation" in markdown


def test_report_stem_can_version_a_new_evidence_package(tmp_path):
    report = fixture.run_agent_safety_fixture()
    md, machine = fixture.write_reports(
        report,
        tmp_path,
        artifact_stem="AUREON_AGENT_SAFETY_TYPED_AUTHORITY_FIXTURE",
    )
    assert md.name == "AUREON_AGENT_SAFETY_TYPED_AUTHORITY_FIXTURE.md"
    assert machine.name == "AUREON_AGENT_SAFETY_TYPED_AUTHORITY_FIXTURE.json"
