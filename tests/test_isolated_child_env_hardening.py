"""Follow-up hardening for isolated_child_env and the repair pytest."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from aureon.autonomous import aureon_sandbox_self_repair as repair
from aureon.autonomous.self_repair_guard import ENABLE_ENV, KILL_ENV, review_log_path
from aureon.launch import session_scope

_FAKE_KEY = "fake-not-a-real-value"

MODULE = """\
def schumann_band_count():
    return 7
"""

TEST = """\
from schumann_band import schumann_band_count

def test_eight_bands():
    assert schumann_band_count() == 8
"""


def _sandbox(tmp_path: Path) -> Path:
    root = tmp_path / "sandbox"
    root.mkdir()
    (root / "schumann_band.py").write_text(MODULE, encoding="utf-8")
    (root / "test_schumann_band.py").write_text(TEST, encoding="utf-8")
    return root


def _enable(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENABLE_ENV, "1")
    monkeypatch.delenv(KILL_ENV, raising=False)
    config = root / "state" / "self_repair_config.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text('{"enabled": true}\n', encoding="utf-8")
    # The cycle cleaner can walk a large shared /tmp; these tests are about holds, not hygiene.
    import aureon.autonomous.queen_repair_cleaner as cleaner
    monkeypatch.setattr(cleaner, "clean_cycle", lambda root, **kwargs: {"ok": True})
    monkeypatch.setattr(cleaner, "ensure_space", lambda root, **kwargs: {"ok": True, "free_bytes": 10**12})


def _secret_in(report: dict, root: Path) -> bool:
    blob = json.dumps(report, default=str)
    log = review_log_path(root)
    if log.exists():
        blob += log.read_text(encoding="utf-8")
    return _FAKE_KEY in blob


def test_aws_access_key_id_is_stripped() -> None:
    env = {"AWS_ACCESS_KEY_ID": _FAKE_KEY, "PATH": "/usr/bin"}
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
    (tmp_path / ".env").write_text(f"CAPITAL_API_KEY={_FAKE_KEY}\n", encoding="utf-8")
    (tmp_path / "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    seen: dict[str, bool] = {}

    def fake_run(cmd, **kwargs):
        seen["ran"] = True
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(repair.subprocess, "run", fake_run)
    with pytest.raises(repair.PytestRefused) as caught:
        repair._pytest(tmp_path)
    assert "ran" not in seen
    assert ".env" in caught.value.names
    assert _FAKE_KEY not in str(caught.value)


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


def test_repair_holds_when_dotenv_present_and_does_not_call_pytest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _sandbox(tmp_path)
    _enable(root, monkeypatch)
    (root / ".env").write_text(f"CAPITAL_API_KEY={_FAKE_KEY}\n", encoding="utf-8")
    called: list[Path] = []

    def fake_pytest(project: Path):
        called.append(project)
        return subprocess.CompletedProcess(["pytest"], 0, "", "")

    monkeypatch.setattr(repair, "_pytest", fake_pytest)
    report = repair.repair_sandbox(root)
    assert report["status"] == "held"
    assert report["reason"] == "dotenv_present"
    assert report["repairs"] == []
    assert called == []
    assert ".env" in report.get("dotenv_files", [])
    assert (root / "schumann_band.py").read_text(encoding="utf-8") == MODULE
    assert _secret_in(report, root) is False
    log = review_log_path(root).read_text(encoding="utf-8")
    assert "dotenv_present" in log
    assert "repair_held" in log


def test_repair_holds_if_dotenv_appears_before_phase2_full(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _sandbox(tmp_path)
    _enable(root, monkeypatch)
    calls = {"n": 0}
    real = repair._pytest

    def wrapper(project: Path):
        calls["n"] += 1
        if calls["n"] >= 2:
            (project / ".env").write_text(f"CAPITAL_API_KEY={_FAKE_KEY}\n", encoding="utf-8")
        return real(project)

    monkeypatch.setattr(repair, "_pytest", wrapper)
    report = repair.repair_sandbox(root)
    assert calls["n"] >= 2, f"phase-2 full was never reached; calls={calls['n']}"
    assert report["status"] == "held"
    assert report["reason"] == "dotenv_present"
    assert report["repairs"] == []
    assert report.get("commit") in {None, "", False} or "commit" not in report
    assert (root / "schumann_band.py").read_text(encoding="utf-8") == MODULE
    assert _secret_in(report, root) is False


def test_bisect_trial_refusal_aborts_and_banks_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _sandbox(tmp_path)
    _enable(root, monkeypatch)
    calls = {"n": 0}
    real = repair._pytest

    def wrapper(project: Path):
        calls["n"] += 1
        if calls["n"] == 1:
            return real(project)
        if calls["n"] == 2:
            # A synthetic regression forces the bisect. This is not a real suite.
            return subprocess.CompletedProcess(
                ["pytest"],
                1,
                "FAILED test_reg.py::test_reg\n",
                "",
            )
        (project / ".env").write_text(f"CAPITAL_API_KEY={_FAKE_KEY}\n", encoding="utf-8")
        return real(project)

    monkeypatch.setattr(repair, "_pytest", wrapper)
    report = repair.repair_sandbox(root)
    assert calls["n"] >= 3, f"bisect trial was never reached; calls={calls['n']}"
    assert report["status"] == "held"
    assert report["reason"] == "dotenv_present"
    assert report["repairs"] == []
    assert report.get("commit") in {None, "", False} or "commit" not in report
    assert (root / "schumann_band.py").read_text(encoding="utf-8") == MODULE
    assert _secret_in(report, root) is False
