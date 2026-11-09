"""Launchers stay guarded unless the stage 11 gate is clear and the operator flag is set."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FLAG = "AUREON_OPERATOR_ALLOW_LIVE"
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
