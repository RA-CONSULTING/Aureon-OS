"""Owner autonomy mode. Guarded stays the default. Full mode is explicit."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from aureon.autonomous.aureon_internal_self_coder import _apply_approved_patch
from aureon.autonomous.aureon_safe_code_control import CodeProposal, SafeCodeControl
from aureon.autonomous.aureon_sandbox_self_repair import load_architect
from aureon.autonomous.autonomy_mode import (
    MODE_ENV,
    autonomy_mode,
    kill_switch_engaged,
    set_runtime_authority,
)
from aureon.autonomous.self_repair_guard import review_log_path
from aureon.queen.unity_exchange_brain import QueenGovernedExchangeBrain
from aureon_fusion.join import status_report


def _fake_expression_context(*args, **kwargs):
    return {
        "schema_features": ["aureon_code_expression_context_v1"],
        "ok": True,
        "voice_summary": "Aureon understands the code goal and can explain the patch for review.",
        "runtime_summary": "state translated for code review",
        "redaction_applied": False,
    }


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.email", "self-repair@localhost")
    _git(root, "config", "user.name", "Aureon self-repair")
    (root / "offset.py").write_text("def band_offset():\n    return 1\n", encoding="utf-8")
    (root / "gate.py").write_text('def evidence_gate():\n    return "HOLD"\n', encoding="utf-8")
    (root / "size.py").write_text("def position_qty(price):\n    return 0\n", encoding="utf-8")
    _git(root, "add", "offset.py", "gate.py", "size.py")
    _git(root, "commit", "-m", "base")
    return root


def _auditor():
    path = Path(__file__).resolve().parents[1] / "scripts" / "validation" / "audit_economic_mutation_boundaries.py"
    spec = importlib.util.spec_from_file_location("autonomy_census_probe", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_public_default_is_guarded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(MODE_ENV, raising=False)
    monkeypatch.chdir(tmp_path)
    assert autonomy_mode(tmp_path) == "guarded"


def test_local_state_file_opens_full_mode_without_being_the_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(MODE_ENV, raising=False)
    monkeypatch.chdir(tmp_path)
    state = tmp_path / "state"
    state.mkdir()
    (state / "autonomy_mode.json").write_text('{"mode": "full"}\n', encoding="utf-8")
    assert autonomy_mode(tmp_path) == "full"
    monkeypatch.setenv(MODE_ENV, "guarded")
    assert autonomy_mode(tmp_path) == "guarded"


def test_full_mode_allows_protected_edits_and_still_refuses_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(MODE_ENV, "full")
    monkeypatch.delenv("AUREON_SELF_REPAIR_KILL", raising=False)
    architect = load_architect()(repo_path=str(tmp_path))
    secret = "super-secret-value"
    assert architect.write_file("arm.py", 'AUREON_LIVE_TRADING = "1"\n') is True
    assert "AUREON_LIVE_TRADING" in (tmp_path / "arm.py").read_text(encoding="utf-8")
    assert architect.write_file("gate.py", 'may_act = True\ngate = "RELEASE"\n') is True
    assert architect.write_file("aureon/trading/desk.py", "def position_qty(price):\n    return 1\n") is True
    assert "return 1" in (tmp_path / "aureon" / "trading" / "desk.py").read_text(encoding="utf-8")
    assert architect.write_file(".env", f"BINANCE_API_SECRET={secret}\n") is False
    assert not (tmp_path / ".env").exists()
    assert architect.write_file("notes.py", f"API_SECRET={secret}\n") is False
    assert not (tmp_path / "notes.py").exists()
    log = review_log_path(tmp_path).read_text(encoding="utf-8")
    audit = (tmp_path / "state" / "autonomy_audit.jsonl").read_text(encoding="utf-8")
    assert secret not in log
    assert secret not in audit
    assert "credential_path" in log
    assert "credential_material" in log


def test_full_mode_auto_approves_protected_proposals_except_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(MODE_ENV, "full")
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
    gate = ctl.propose(
        CodeProposal(
            kind="code_task",
            title="Open the gate",
            target_files=["gate.py"],
            patch_text='gate = "RELEASE"\nmay_act = True\n',
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
    assert live["status"] == "approved"
    assert live["reviewer"] == "env:AUREON_CODE_AUTO_APPROVE"
    assert gate["status"] == "approved"
    assert secret["status"] == "pending_human_review"
    assert secret["reason"] == "credential_path"


def test_failed_self_patch_rolls_back(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(MODE_ENV, "guarded")
    root = _repo(tmp_path)
    before = (root / "offset.py").read_text(encoding="utf-8")
    patch = (
        "diff --git a/offset.py b/offset.py\n"
        "--- a/offset.py\n"
        "+++ b/offset.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def band_offset():\n"
        "-    return 1\n"
        "+    return 0\n"
    )
    result = _apply_approved_patch(root, "offset.py", patch, [[sys.executable, "-c", "raise SystemExit(1)"]])
    assert result["rolled_back"] is True
    assert result["auto_merged"] is False
    assert result["ok"] is False
    assert (root / "offset.py").read_text(encoding="utf-8") == before


def test_full_mode_auto_merges_after_tests_pass_and_guarded_mode_does_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repo(tmp_path)
    patch = (
        "diff --git a/offset.py b/offset.py\n"
        "--- a/offset.py\n"
        "+++ b/offset.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def band_offset():\n"
        "-    return 1\n"
        "+    return 0\n"
    )
    command = [[sys.executable, "-c", "raise SystemExit(0)"]]
    monkeypatch.setenv(MODE_ENV, "guarded")
    guarded = _apply_approved_patch(root, "offset.py", patch, command)
    assert guarded["ok"] is True
    assert guarded["auto_merged"] is False
    assert "return 0" in (root / "offset.py").read_text(encoding="utf-8")
    subject = subprocess.run(
        ["git", "log", "-1", "--format=%s"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert subject.stdout.strip() == "base"
    _git(root, "checkout", "--", "offset.py")
    monkeypatch.setenv(MODE_ENV, "full")
    opened = _apply_approved_patch(root, "offset.py", patch, command)
    assert opened["ok"] is True, opened
    assert opened["auto_merged"] is True
    assert opened["commit"]
    subject = subprocess.run(
        ["git", "log", "-1", "--format=%s"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert subject.stdout.strip() == "self-patch: tests passed"
    assert "return 0" in (root / "offset.py").read_text(encoding="utf-8")


def test_full_mode_can_arm_live_without_placing_an_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AUREON_LIVE_TRADING", "0")
    monkeypatch.setenv("AUREON_MAY_ACT", "0")
    monkeypatch.setenv(MODE_ENV, "guarded")
    refused = set_runtime_authority(tmp_path, live_trading=True, may_act=True)
    assert refused["ok"] is False
    assert refused["reason"] == "autonomy_guarded"
    assert refused["order_placed"] is False
    assert os.environ["AUREON_LIVE_TRADING"] == "0"
    assert not (tmp_path / ".env").exists()
    monkeypatch.setenv(MODE_ENV, "full")
    armed = set_runtime_authority(tmp_path, live_trading=True, may_act=True)
    assert armed["ok"] is True
    assert armed["armed"] is True
    assert armed["may_act"] is True
    assert armed["order_placed"] is False
    assert armed["env_written"] is False
    assert not (tmp_path / ".env").exists()
    assert os.environ["AUREON_LIVE_TRADING"] == "1"
    assert os.environ["AUREON_MAY_ACT"] == "1"
    report = status_report()
    assert report["live_trading"] is True
    assert report["may_act"] is True
    audit = (tmp_path / "state" / "autonomy_audit.jsonl").read_text(encoding="utf-8")
    assert "runtime_authority_set" in audit
    assert "order_placed" in audit


def test_kill_switch_stops_writes_arming_and_orders(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(MODE_ENV, "full")
    monkeypatch.setenv("AUREON_LIVE_TRADING", "0")
    monkeypatch.setenv("AUREON_AUTONOMY_AUDIT_PATH", str(tmp_path / "orders.jsonl"))
    kill = tmp_path / "state" / "SELF_REPAIR_KILL"
    kill.parent.mkdir(parents=True)
    kill.write_text("stop\n", encoding="utf-8")
    assert kill_switch_engaged(tmp_path) is True
    architect = load_architect()(repo_path=str(tmp_path))
    assert architect.write_file("arm.py", "AUREON_LIVE_TRADING=1\n") is False
    assert not (tmp_path / "arm.py").exists()
    refused = set_runtime_authority(tmp_path, live_trading=True, may_act=True)
    assert refused["reason"] == "kill_switch"
    assert os.environ["AUREON_LIVE_TRADING"] == "0"
    monkeypatch.chdir(tmp_path)
    brain = QueenGovernedExchangeBrain(exchange="kraken", read_client=None, governed_client=None)
    receipt = brain.place_market_order("BTC/USD", "buy", quantity=1)
    assert receipt["reason"] == "kill_switch"
    assert receipt["decision"] == "HOLD"
    audit = (tmp_path / "orders.jsonl").read_text(encoding="utf-8")
    assert "kill_switch" in audit
    assert "order_placed_by_audit" in audit


def test_guarded_census_still_refuses_live_arming_and_full_mode_does_not(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auditor = _auditor()
    report = {"blocker_count": 4, "unallowlisted": [{"file": "desk.py"}]}
    monkeypatch.setenv("AUREON_LIVE_TRADING", "1")
    monkeypatch.setenv(MODE_ENV, "guarded")
    assert auditor.live_arming_refusal(report) == auditor.LIVE_ARMING_REFUSAL
    monkeypatch.setenv(MODE_ENV, "full")
    assert auditor.live_arming_refusal(report) is None
    recorded = json.dumps(report)
    assert "AUREON_LIVE_TRADING=1" not in recorded
