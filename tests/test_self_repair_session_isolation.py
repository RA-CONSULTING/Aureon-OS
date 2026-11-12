"""A self-repair pytest must not inherit a running launcher's session."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from aureon.launch import session_scope
from aureon.autonomous import aureon_sandbox_self_repair as repair

_PARENT = {
    "AUREON_LAUNCHER_SCOPE": "aureon-launcher-live",
    "AUREON_LAUNCHER_CGROUP": "/sys/fs/cgroup/fake/aureon-launcher-live",
    "AUREON_LAUNCHER_ROOT_PID": "948600",
    "AUREON_LAUNCHER_INSIDE_SCOPE": "1",
    "AUREON_LAUNCHER_PROBE_STARTED": "1",
    "AUREON_LAUNCHER_STATE": "/workspace/live/state/launcher",
    "SERO_WORKSPACE": "/workspace/live",
}


def test_strip_drops_every_parent_session_var() -> None:
    env = {**_PARENT, "PATH": "/usr/bin", "AUREON_LIVE_TRADING": "0"}
    cleaned = session_scope.strip_inherited_session(env)
    for key in _PARENT:
        assert key not in cleaned
    assert cleaned["PATH"] == "/usr/bin"
    assert cleaned["AUREON_LIVE_TRADING"] == "0"
    assert env["SERO_WORKSPACE"] == "/workspace/live"  # input is not mutated


def test_strip_covers_the_scope_constants() -> None:
    for name in (
        session_scope.SCOPE_ENV,
        session_scope.CGROUP_ENV,
        session_scope.ROOT_ENV,
        session_scope.INSIDE_ENV,
    ):
        assert name in session_scope.INHERITED_SESSION_VARS


def test_repair_pytest_runs_without_parent_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in _PARENT.items():
        monkeypatch.setenv(key, value)
    seen: dict[str, dict[str, str]] = {}

    def fake_run(cmd, **kwargs):
        seen["env"] = dict(kwargs["env"])
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(repair.subprocess, "run", fake_run)
    repair._pytest(tmp_path)
    env = seen["env"]
    for key in _PARENT:
        assert key not in env, key
    assert env["PYTHONDONTWRITEBYTECODE"] == "1"


def test_fresh_clone_smoke_strips_session_and_kills_its_group() -> None:
    src = (Path(__file__).parent / "test_master_launcher.py").read_text(encoding="utf-8")
    body = src.split("def test_fresh_clone_smoke_prints_the_health_table", 1)[1]
    assert "isolated_child_env(os.environ.copy())" in body
    assert "start_new_session=True" in body
    assert "_kill_group(launcher.pid)" in body.split("finally:", 1)[1]


_FAKE_CREDS = {
    "CAPITAL_API_PASSWORD": "fake-not-a-real-value",
    "CAPITAL_USER": "fake",
    "APCA_API_KEY_ID": "fake",
    "APCA_API_SECRET_KEY": "fake",
    "BINANCE_SECRET": "fake",
    "ALPACA_KEY": "fake",
    "KRAKEN_API_SECRET": "fake",
    "SOME_FUTURE_EXCHANGE_PASSPHRASE": "fake",
    "UNLISTED_ALIAS_SECRET": "fake",
}


def test_credentials_are_stripped_by_pattern() -> None:
    env = {**_FAKE_CREDS, "PATH": "/usr/bin", "AUREON_LIVE_TRADING": "0"}
    cleaned = session_scope.isolated_child_env(env)
    for key in _FAKE_CREDS:
        assert key not in cleaned, key
    assert cleaned["PATH"] == "/usr/bin"
    assert cleaned["AUREON_LIVE_TRADING"] == "0"
    assert cleaned["PYTHON_DOTENV_DISABLED"] == "1"


_PROBE = """
import json, os
from pathlib import Path

root = Path(__file__).parent
loaded = None
try:
    from dotenv import load_dotenv
    load_dotenv(root / ".env", override=True)
    loaded = "dotenv"
except ImportError:
    loaded = "no-dotenv"


def test_probe():
    names = sorted(os.environ)
    (root / "seen.json").write_text(json.dumps({"names": names, "loader": loaded}))
"""


def test_real_repair_pytest_child_sees_no_credentials(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Run the real repair pytest on a tiny project with fake keys in env and .env."""

    for key, value in {**_PARENT, **_FAKE_CREDS}.items():
        monkeypatch.setenv(key, value)
    project = tmp_path / "proj"
    project.mkdir()
    (project / "test_probe.py").write_text(_PROBE, encoding="utf-8")
    (project / ".env").write_text("DOTENV_SEEDED_SECRET=fake\nCAPITAL_API_KEY=fake\n", encoding="utf-8")
    result = repair._pytest(project)
    assert result.returncode == 0, result.stdout + result.stderr
    seen = json.loads((project / "seen.json").read_text(encoding="utf-8"))
    names = set(seen["names"])
    for key in list(_PARENT) + list(_FAKE_CREDS) + ["DOTENV_SEEDED_SECRET", "CAPITAL_API_KEY"]:
        assert key not in names, key
    assert "PYTHON_DOTENV_DISABLED" in names
