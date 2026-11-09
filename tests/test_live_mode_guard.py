"""Launchers stay guarded unless the stage 11 gate is clear and the operator flag is set.

An operator test session is a separate route. These tests reload the gate
module and clear the session env so an earlier test cannot leak either.
"""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FLAG = "AUREON_OPERATOR_ALLOW_LIVE"
SESSION_ENV = "AUREON_OPERATOR_TEST_SESSION"
NOW = datetime(2026, 11, 9, 19, 0, tzinfo=UTC)
LAUNCHERS = (
    "scripts/linux/aureon-up.sh",
    "scripts/launch/aureon-master.sh",
    "scripts/launch/aureon-master.ps1",
    "scripts/launch/aureon-master.bat",
    "production/install.sh",
    "production/Install-AUREON.ps1",
    "aureon_radar/start_radar.sh",
    "aureon_radar/start_radar.bat",
    "aureon_radar/launch_all.bat",
    "aureon_radar/launch_all_fixed.bat",
)


def _clean_env() -> dict[str, str]:
    """Child env with no Aureon variables inherited from the suite."""

    return {
        "HOME": os.environ.get("HOME", ""),
        "PATH": os.environ.get("PATH", ""),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(ROOT),
    }


def _reload_checkout(module_name: str):
    """Reload a checkout module even if a leaked pin finder is on ``sys.meta_path``."""

    saved = sys.meta_path[:]
    sys.meta_path = [finder for finder in saved if type(finder).__name__ != "PinnedAureonFinder"]
    try:
        module = importlib.import_module(module_name)
        return importlib.reload(module)
    finally:
        sys.meta_path[:] = saved


@pytest.fixture(autouse=True)
def _isolate_live_gate(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(FLAG, raising=False)
    monkeypatch.delenv(SESSION_ENV, raising=False)
    monkeypatch.delenv("AUREON_OPERATOR_TEST_SESSION_STAMP", raising=False)
    _reload_checkout("aureon.launch.live_gate")


def _session_record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "approval_reference": (
            "Gary Leckey, 9 Nov 2026 18:47 GMT, in-room approval to test live and paper trading"
        ),
        "expires_at": "2026-11-09T21:00:00+00:00",
        "owner": "Lrya",
        "session_id": "room-1847",
        "starts_at": "2026-11-09T18:47:00+00:00",
    }
    record.update(overrides)
    return record


def _write_session(root: Path, record: dict[str, object]) -> None:
    path = root / "state" / "operator_test_session.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")


def test_this_checkout_refuses_live_mode() -> None:
    from aureon.launch.live_gate import OPERATOR_FLAG, decide, repo_root

    mode, reason = decide(repo_root(), {})
    assert mode == "guarded"
    assert "go_live_clear is false" in reason
    assert f"{OPERATOR_FLAG} is not set" in reason
    assert "production ready" not in reason.casefold()
    assert "validated" not in reason.casefold()
    completed = subprocess.run(
        [sys.executable, "-m", "aureon.launch.live_gate"],
        cwd=ROOT,
        env=_clean_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0
    output = completed.stdout + completed.stderr
    assert "refuses live mode" in output
    assert "AUREON_LIVE_TRADING=0" in output
    assert "guarded" in output
    assert "No real orders." in output
    assert FLAG in output


def test_operator_flag_does_not_override_the_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    from aureon.launch.live_gate import decide, repo_root

    monkeypatch.setenv(FLAG, "1")
    mode, reason = decide(repo_root(), os.environ)
    assert mode == "guarded"
    assert "does not override the gate" in reason
    assert "go_live_clear is false" in reason


def test_stage11_script_and_flag_are_both_required(tmp_path: Path) -> None:
    from aureon.launch.live_gate import decide

    script = tmp_path / "scripts" / "bootstrap" / "go_live_stage11_gate.py"
    script.parent.mkdir(parents=True)
    script.write_text(
        "import json\nprint(json.dumps({'go_live_clear': True, 'reason': 'clear'}))\n",
        encoding="utf-8",
    )
    receipt = tmp_path / "reports" / "measured" / "go_live_receipt5_deployment.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text(json.dumps({"go_live_clear": False}) + "\n", encoding="utf-8")
    blocked, blocked_reason = decide(tmp_path, {})
    assert blocked == "guarded"
    assert f"{FLAG} is not set" in blocked_reason
    allowed, allowed_reason = decide(tmp_path, {FLAG: "1"})
    assert allowed == "live"
    assert "reports clear" in allowed_reason
    script.write_text(
        "import json\nprint(json.dumps({'go_live_clear': False, 'reason': 'hold'}))\n",
        encoding="utf-8",
    )
    held, held_reason = decide(tmp_path, {FLAG: "true"})
    assert held == "guarded"
    assert "does not override the gate" in held_reason
    assert "hold" in held_reason


def test_missing_stage11_script_reads_go_live_clear(tmp_path: Path) -> None:
    from aureon.launch.live_gate import decide

    receipt = tmp_path / "reports" / "measured" / "go_live_receipt5_deployment.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text(json.dumps({"go_live_clear": False}) + "\n", encoding="utf-8")
    mode, reason = decide(tmp_path, {FLAG: "1"})
    assert mode == "guarded"
    assert "go_live_clear is false" in reason
    receipt.write_text(json.dumps({"go_live_clear": True}) + "\n", encoding="utf-8")
    allowed, _reason = decide(tmp_path, {FLAG: "yes"})
    assert allowed == "live"
    still, _still_reason = decide(tmp_path, {FLAG: "0"})
    assert still == "guarded"


def test_launchers_force_guarded_mode_unless_the_gate_allows_live() -> None:
    for relative in LAUNCHERS:
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "aureon.launch.live_gate" in text or "live-mode-guard" in text, relative
        assert "AUREON_LIVE_TRADING" in text, relative
        assert "guarded" in text, relative
    guard = (ROOT / "scripts/launch/live-mode-guard.sh").read_text(encoding="utf-8")
    assert "AUREON_LIVE_TRADING=0" in guard
    assert "AUREON_AUTONOMY_MODE=guarded" in guard
    assert "AUREON_DISABLE_REAL_ORDERS=1" in guard
    windows = (ROOT / "scripts/launch/live-mode-guard.ps1").read_text(encoding="utf-8")
    assert 'AUREON_LIVE_TRADING = "0"' in windows
    assert 'AUREON_AUTONOMY_MODE = "guarded"' in windows


def test_bash_guard_exports_the_guarded_environment() -> None:
    script = f"""
set -euo pipefail
cd {ROOT}
source {ROOT}/scripts/launch/live-mode-guard.sh
live_mode_guard {sys.executable}
printf 'LIVE=%s\\n' "$AUREON_LIVE_TRADING"
printf 'MODE=%s\\n' "$AUREON_AUTONOMY_MODE"
printf 'ORDERS=%s\\n' "$AUREON_DISABLE_REAL_ORDERS"
"""
    completed = subprocess.run(
        ["bash", "-c", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
            FLAG: "1",
        },
    )
    output = completed.stdout + completed.stderr
    assert completed.returncode == 0, output
    assert "refuses live mode" in output
    assert "does not override the gate" in output
    assert "LIVE=0" in output
    assert "MODE=guarded" in output
    assert "ORDERS=1" in output


def test_live_is_refused_without_a_session_record(tmp_path: Path) -> None:
    from aureon.launch.live_gate import SESSION_ENV, active_test_session, decide

    mode, reason = decide(tmp_path, {SESSION_ENV: "1"}, now=NOW)
    assert active_test_session(tmp_path, {SESSION_ENV: "1"}, now=NOW) is None
    assert mode == "guarded"
    assert "go_live_clear" in reason
    receipt = tmp_path / "reports" / "measured" / "go_live_receipt5_deployment.json"
    assert not receipt.exists()


def test_live_is_refused_after_the_session_expires(tmp_path: Path) -> None:
    from aureon.launch.live_gate import SESSION_ENV, active_test_session, decide

    _write_session(tmp_path, _session_record())
    later = datetime(2026, 11, 9, 22, 0, tzinfo=UTC)
    assert active_test_session(tmp_path, {SESSION_ENV: "1"}, now=later) is None
    mode, _reason = decide(tmp_path, {SESSION_ENV: "1"}, now=later)
    assert mode == "guarded"


def test_session_without_an_approval_reference_is_refused(tmp_path: Path) -> None:
    from aureon.launch.live_gate import SESSION_ENV, active_test_session, decide

    for approval in (None, ""):
        record = _session_record()
        if approval is None:
            del record["approval_reference"]
        else:
            record["approval_reference"] = approval
        _write_session(tmp_path, record)
        env = {SESSION_ENV: "1"}
        assert active_test_session(tmp_path, env, now=NOW) is None
        mode, _reason = decide(tmp_path, env, now=NOW)
        assert mode == "guarded"


def test_valid_session_stays_off_the_go_live_gate(tmp_path: Path) -> None:
    from aureon.launch.live_gate import SESSION_ENV, active_test_session, decide, evaluate_launcher_order

    receipt = tmp_path / "reports" / "measured" / "go_live_receipt5_deployment.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text(
        json.dumps({"go_live_clear": False, "pin": "bb04503119681adcf832f3c3e9b0cbf09fc7a938"}) + "\n",
        encoding="utf-8",
    )
    before = receipt.read_bytes()
    _write_session(tmp_path, _session_record())
    env = {SESSION_ENV: "1"}
    session = active_test_session(tmp_path, env, now=NOW)
    assert session is not None
    mode, reason = decide(tmp_path, env, now=NOW)
    assert mode == "live"
    assert "go_live_clear stays false" in reason
    record = evaluate_launcher_order(tmp_path, env, {"action": "EXECUTE"}, now=NOW)
    assert record["go_live_clear"] is False
    assert record["orders_placed"] is False
    assert record["stamp"] == "operator_test_session=room-1847, go_live_clear=false"
    assert receipt.read_bytes() == before
    assert "bb04503119681adcf832f3c3e9b0cbf09fc7a938" in (
        ROOT / "mcp/aureon_public/guard_loader.py"
    ).read_text(encoding="utf-8")
    assert "release%20boundary-HOLD-orange" in (ROOT / "README.md").read_text(encoding="utf-8")


def test_guarded_mode_when_neither_the_gate_nor_a_session_holds(tmp_path: Path) -> None:
    from aureon.launch.live_gate import decide, evaluate_launcher_order

    mode, _reason = decide(tmp_path, {}, now=NOW)
    assert mode == "guarded"
    record = evaluate_launcher_order(tmp_path, {}, {"action": "EXECUTE"}, now=NOW)
    assert record["mode"] == "guarded"
    assert record["admitted"] is False
    assert record["go_live_clear"] is False
    assert "operator_test_session" not in record


def test_session_output_is_rejected_as_go_live_evidence(tmp_path: Path) -> None:
    from aureon.launch.live_gate import SESSION_ENV, accepts_go_live_evidence, evaluate_launcher_order

    _write_session(tmp_path, _session_record())
    record = evaluate_launcher_order(tmp_path, {SESSION_ENV: "1"}, {"action": "EXECUTE"}, now=NOW)
    assert accepts_go_live_evidence(record) is False
    forged = dict(record)
    forged["go_live_clear"] = True
    assert accepts_go_live_evidence(forged) is False


def test_session_and_guarded_mode_call_the_same_risk_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aureon.launch import live_gate

    calls: list[dict[str, object]] = []

    def _hold(reading: dict[str, object]) -> str:
        calls.append(dict(reading))
        return "HOLD"

    _write_session(tmp_path, _session_record())
    session_env = {SESSION_ENV: "1"}
    plain_guarded = live_gate.evaluate_launcher_order(tmp_path, {}, {"action": "EXECUTE"}, now=NOW)
    plain_session = live_gate.evaluate_launcher_order(tmp_path, session_env, {"action": "EXECUTE"}, now=NOW)
    assert plain_guarded["gates_called"] == plain_session["gates_called"] == ["launcher_risk_gate"]
    assert plain_guarded["risk_gates"] == plain_session["risk_gates"] == ["EXECUTE"]
    monkeypatch.setattr(live_gate, "launcher_risk_gate", _hold)
    guarded = live_gate.evaluate_launcher_order(tmp_path, {}, {"action": "EXECUTE"}, now=NOW)
    session = live_gate.evaluate_launcher_order(tmp_path, session_env, {"action": "EXECUTE"}, now=NOW)
    assert guarded["gates_called"] == session["gates_called"]
    assert len(calls) == 2
    assert guarded["risk_gates"] == session["risk_gates"] == ["HOLD"]
    assert session["mode"] == "live"
    assert session["admitted"] is False
    assert session["blocked"] is True
    assert session["block_reason"] == "risk gate HOLD"
    assert session["go_live_clear"] is False
    assert session["orders_placed"] is False


def test_liquidation_scripts_do_not_honour_the_session() -> None:
    from aureon.launch.live_gate import LIQUIDATION_SCRIPTS, SESSION_ENV

    for relative in LIQUIDATION_SCRIPTS:
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert SESSION_ENV not in text
        assert "operator_test_session" not in text
        assert "live_gate" not in text
