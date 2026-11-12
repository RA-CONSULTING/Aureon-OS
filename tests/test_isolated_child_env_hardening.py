"""Follow-up hardening for isolated_child_env and the repair pytest."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from aureon.autonomous import aureon_sandbox_self_repair as repair
from aureon.launch import session_scope


def test_aws_access_key_id_is_stripped() -> None:
    env = {"AWS_ACCESS_KEY_ID": "fake-not-a-real-value", "PATH": "/usr/bin"}
    cleaned = session_scope.isolated_child_env(env)
    assert "AWS_ACCESS_KEY_ID" not in cleaned
    assert cleaned["PATH"] == "/usr/bin"


def test_live_switches_are_forced_off() -> None:
    env = {
        "AUREON_LIVE_TRADING": "1",
        "AUREON_DISABLE_REAL_ORDERS": "0",
        "DRY_RUN": "0",
        "PATH": "/usr/bin",
    }
    cleaned = session_scope.isolated_child_env(env)
    assert cleaned["AUREON_LIVE_TRADING"] == "0"
    assert cleaned["AUREON_DISABLE_REAL_ORDERS"] == "1"
    assert cleaned["DRY_RUN"] == "1"
    assert env["AUREON_LIVE_TRADING"] == "1"  # input is not mutated


def test_pytest_refuses_when_dotenv_exists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".env").write_text("CAPITAL_API_KEY=fake-not-a-real-value\n", encoding="utf-8")
    (tmp_path / "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    seen: dict[str, bool] = {}

    def fake_run(cmd, **kwargs):
        seen["ran"] = True
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(repair.subprocess, "run", fake_run)
    result = repair._pytest(tmp_path)
    assert result.returncode != 0
    assert "ran" not in seen
    assert ".env" in (result.stderr or "")
    combined = (result.stdout or "") + (result.stderr or "")
    assert "fake-not-a-real-value" not in combined


def test_pytest_runs_when_only_env_example_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".env.example").write_text("CAPITAL_API_KEY=\n", encoding="utf-8")
    seen: dict[str, bool] = {}

    def fake_run(cmd, **kwargs):
        seen["ran"] = True
        return subprocess.CompletedProcess(cmd, 0, "ok", "")

    monkeypatch.setattr(repair.subprocess, "run", fake_run)
    result = repair._pytest(tmp_path)
    assert result.returncode == 0
    assert seen.get("ran") is True
