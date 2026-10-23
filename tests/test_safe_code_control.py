from aureon.autonomous.aureon_safe_code_control import CodeProposal, SafeCodeControl


def _fake_expression_context(*args, **kwargs):
    return {
        "schema_features": ["aureon_code_expression_context_v1"],
        "ok": True,
        "voice_summary": "Aureon understands the code goal and can explain the patch for review.",
        "runtime_summary": "state translated for code review",
        "redaction_applied": False,
    }


def test_code_proposals_queue_for_review_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("AUREON_CODE_AUTO_APPROVE", raising=False)
    monkeypatch.setattr(
        "aureon.autonomous.aureon_safe_code_control.build_code_expression_context",
        _fake_expression_context,
    )
    ctl = SafeCodeControl(state_path=tmp_path / "code_state.json")

    result = ctl.propose(CodeProposal(kind="code_task", title="Add dashboard card"))

    assert result["status"] == "pending_review"
    assert result["summary"].startswith("Aureon understands")
    assert result["metadata"]["expression_context"]["ok"] is True
    assert ctl.status()["pending_count"] == 1
    assert ctl.status()["recent_reviews"] == []


def test_code_proposals_can_be_explicitly_auto_approved(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_CODE_AUTO_APPROVE", "1")
    monkeypatch.setattr(
        "aureon.autonomous.aureon_safe_code_control.build_code_expression_context",
        _fake_expression_context,
    )
    ctl = SafeCodeControl(state_path=tmp_path / "code_state.json")

    result = ctl.propose(CodeProposal(kind="code_task", title="Trusted local workflow"))

    assert result["status"] == "approved"
    assert result["reviewer"] == "env:AUREON_CODE_AUTO_APPROVE"
    assert ctl.status()["pending_count"] == 0
    assert ctl.status()["recent_reviews"][0]["title"] == "Trusted local workflow"


def test_auto_approve_does_not_cover_protected_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_CODE_AUTO_APPROVE", "1")
    monkeypatch.setattr(
        "aureon.autonomous.aureon_safe_code_control.build_code_expression_context",
        _fake_expression_context,
    )
    ctl = SafeCodeControl(state_path=tmp_path / "code_state.json")

    live = ctl.propose(
        CodeProposal(
            kind="code_task",
            title="Arm the desk",
            target_files=["arm.py"],
            patch_text="AUREON_LIVE_TRADING=1\n",
        )
    )
    secret = ctl.propose(
        CodeProposal(
            kind="code_task",
            title="Write local credentials",
            target_files=[".env"],
            patch_text="BINANCE_API_SECRET=\n",
        )
    )
    gate = ctl.propose(
        CodeProposal(
            kind="code_task",
            title="Open the gate",
            target_files=["gate.py"],
            patch_text='gate = "RELEASE"\nmay_act = True\n',
        )
    )

    assert live["status"] == "pending_human_review"
    assert live["human_review"] is True
    assert live["reason"] == "live_trading_flag"
    assert secret["status"] == "pending_human_review"
    assert secret["reason"] == "credential_path"
    assert gate["status"] == "pending_human_review"
    assert gate["reason"] == "evidence_gate"
    assert ctl.status()["recent_reviews"] == []
    assert all(item["status"] != "approved" for item in (live, secret, gate))


def test_code_proposals_approve_and_reject_from_queue(tmp_path, monkeypatch):
    monkeypatch.delenv("AUREON_CODE_AUTO_APPROVE", raising=False)
    monkeypatch.setattr(
        "aureon.autonomous.aureon_safe_code_control.build_code_expression_context",
        _fake_expression_context,
    )
    ctl = SafeCodeControl(state_path=tmp_path / "code_state.json")

    ctl.propose(CodeProposal(kind="code_task", title="Review me"))
    approved = ctl.approve_next(reviewer="operator")

    assert approved["ok"] is True
    assert approved["proposal"]["status"] == "approved"
    assert approved["proposal"]["reviewer"] == "operator"
    assert ctl.status()["pending_count"] == 0

    ctl.propose(CodeProposal(kind="code_task", title="Reject me"))
    rejected = ctl.reject_next(reviewer="operator", reason="not_needed")

    assert rejected["ok"] is True
    assert rejected["proposal"]["status"] == "rejected"
    assert rejected["proposal"]["reject_reason"] == "not_needed"
    assert ctl.status()["pending_count"] == 0
