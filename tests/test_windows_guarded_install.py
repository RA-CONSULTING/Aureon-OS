"""Windows guarded smoke contract. Live trading stays off. Go-live stays HOLD.

The Linux clean-checkout smoke remains ``./install.sh --smoke``. This file
checks the Windows sibling and the Windows process-control branch.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _plug():
    path = ROOT / "scripts" / "plug_and_play.py"
    spec = importlib.util.spec_from_file_location("plug_and_play_windows_contract", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_windows_install_script_is_guarded_and_leaves_the_organism_launcher_alone() -> None:
    script = _text("install.ps1")
    assert script.startswith("#Requires -Version 5.1\n")
    assert script.count("{") == script.count("}")
    assert "requirements-plug.lock" in script
    assert r"scripts\plug_and_play.py" in script
    assert "npm ci --ignore-scripts --prefix frontend" in script
    assert "--stop" in script
    assert "No .venv yet. Nothing to stop." in script
    assert "release boundary: HOLD" in script
    assert "Guarded smoke only" in script
    assert "Live trading stays off" in script
    assert "is not read" in script
    assert "supported go-live" in script.casefold()
    for forbidden in (
        "aureon-master",
        "winget",
        ".env.example",
        "AUREON_LIVE_TRADING=1",
        "AUREON_AUTONOMY_MODE=full",
        "Copy-Item",
        "Invoke-Expression",
        "requirements.txt",
        "npm run build",
        "install.sh",
    ):
        assert forbidden not in script
    wrapper = _text("install.cmd")
    assert "install.ps1" in wrapper
    assert "ExecutionPolicy Bypass" in wrapper
    assert "%*" in wrapper


def test_docs_send_a_windows_stranger_to_guarded_smoke() -> None:
    for relative in (
        "README.md",
        "PORTABILITY.md",
        "docs/windows/GUARDED_SMOKE.md",
        "production/README.md",
        "CLAUDE.md",
    ):
        text = _text(relative)
        assert "install.cmd --smoke" in text, relative
        assert "HOLD" in text, relative
    guide = _text("docs/windows/GUARDED_SMOKE.md")
    assert "AUREON_AUTONOMY_MODE=guarded" in guide
    assert "AUREON_LIVE_TRADING=0" in guide
    assert "requirements-plug.lock" in guide
    assert "production\\Install-AUREON.ps1" in guide
    portability = _text("PORTABILITY.md")
    assert "is meant to boot" in portability
    assert "can boot the same local stack" not in portability
    assert "No Windows run of `install.cmd --smoke` has been measured yet." in _text("README.md")
    assert "did not execute `install.cmd --smoke`" in portability
    assert "windows-latest" in portability
    workflow = _text(".github/workflows/windows-contract.yml")
    assert "tests/test_windows_guarded_install.py" in workflow
    assert "Parser]::ParseFile" in workflow
    assert 'AUREON_LIVE_TRADING: "0"' in workflow


def test_linux_install_script_stays_the_bash_smoke_entry() -> None:
    script = _text("install.sh")
    assert script.startswith("#!/usr/bin/env bash\n")
    assert "install.ps1" not in script
    assert "install.cmd" not in script
    assert "taskkill" not in script
    assert "requirements-plug.lock" in script
    assert "scripts/plug_and_play.py" in script


def test_process_env_forces_guarded_mode_and_drops_exchange_keys(monkeypatch) -> None:
    module = _plug()
    monkeypatch.setenv("AUREON_AUTONOMY_MODE", "full")
    monkeypatch.setenv("AUREON_LIVE_TRADING", "1")
    monkeypatch.setenv("BINANCE_API_KEY", "secret-value")
    env = module.process_env()
    assert env["AUREON_AUTONOMY_MODE"] == "guarded"
    assert env["AUREON_LIVE_TRADING"] == "0"
    assert env["AUREON_LLM_OFFLINE"] == "1"
    assert env["AUREON_DISABLE_REAL_ORDERS"] == "1"
    assert "BINANCE_API_KEY" not in env


def test_windows_process_control_is_separate_from_posix() -> None:
    module = _plug()
    assert module._popen_session_kwargs("posix") == {"start_new_session": True}
    windows_flags = module._popen_session_kwargs("nt")
    assert windows_flags == {"creationflags": module._CREATE_NEW_PROCESS_GROUP}
    assert module._CREATE_NEW_PROCESS_GROUP == 0x00000200
    assert "start_new_session" not in windows_flags
    assert module._stop_command("posix") == "./install.sh --stop"
    assert module._stop_command("nt") == "install.cmd --stop"
    try:
        module._frontend_argv("nt")
    except SystemExit as exc:
        assert str(exc).endswith("vite.js")
    else:
        argv = module._frontend_argv("nt")
        assert argv[0] == "node"
        assert argv[1].endswith("vite.js")
    try:
        posix = module._frontend_argv("posix")
    except SystemExit as exc:
        assert exc.code is not None
        assert ".bin" in str(exc)
        assert "vite.js" not in str(exc)
    else:
        assert posix[0].endswith("vite")
        assert posix[0] != "node"


def test_tasklist_parser_matches_the_pid_column_only() -> None:
    module = _plug()
    sample = '"python.exe","4242","Console","1","12,345 K"\n'
    assert module._tasklist_lists_pid(sample, 4242) is True
    assert module._tasklist_lists_pid(sample, 424) is False
    assert module._tasklist_lists_pid(sample, 12) is False
    assert (
        module._tasklist_lists_pid(
            "INFO: No tasks are running which match the specified criteria.\n",
            4242,
        )
        is False
    )


def test_windows_stop_forces_only_a_pid_tasklist_still_shows(monkeypatch) -> None:
    module = _plug()
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        stdout = ""
        if cmd[0] == "tasklist":
            stdout = '"python.exe","4242","Console","1","12,345 K"\n'
        return SimpleNamespace(returncode=0, stdout=stdout)

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)
    module._stop_windows_pids({4242})
    assert calls[0] == ["taskkill", "/T", "/PID", "4242"]
    assert calls[1][0] == "tasklist"
    assert any("4242" in part for part in calls[1])
    assert calls[2] == ["taskkill", "/F", "/T", "/PID", "4242"]


def test_windows_stop_skips_force_when_the_pid_is_gone(monkeypatch) -> None:
    module = _plug()
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        return SimpleNamespace(
            returncode=0,
            stdout="INFO: No tasks are running which match the specified criteria.\n",
        )

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)
    module._stop_windows_pids({4242})
    assert [cmd[0] for cmd in calls] == ["taskkill", "tasklist"]
    assert "/F" not in calls[0]
