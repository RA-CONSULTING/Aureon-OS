from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_DIR = REPO_ROOT / "scripts" / "runners"
RUNNER_CMD = RUNNER_DIR / "run_aureon_voice_agent.cmd"
RUNNER_PS1 = RUNNER_DIR / "run_aureon_voice_agent.ps1"
STOP_PS1 = RUNNER_DIR / "stop_aureon_voice_agent.ps1"
VOICE_RUNNERS = (RUNNER_CMD, RUNNER_PS1, STOP_PS1)


def _powershell() -> str:
    executable = shutil.which("powershell.exe") or shutil.which("pwsh") or shutil.which("powershell")
    if executable is None:
        pytest.skip("PowerShell is unavailable; static voice-runner contracts still run.")
    return executable


def _assert_powershell_parses(path: Path) -> None:
    environment = os.environ.copy()
    environment["AUREON_TEST_PARSE_PATH"] = str(path)
    command = (
        "$path = [Environment]::GetEnvironmentVariable('AUREON_TEST_PARSE_PATH'); "
        "$tokens = $null; $errors = $null; "
        "[void][System.Management.Automation.Language.Parser]::ParseFile("
        "$path, [ref]$tokens, [ref]$errors); "
        "if ($errors.Count -gt 0) { "
        "$errors | ForEach-Object { [Console]::Error.WriteLine($_.Message) }; exit 1 }"
    )
    result = subprocess.run(
        [_powershell(), "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


@pytest.mark.parametrize("runner", (RUNNER_PS1, STOP_PS1), ids=lambda path: path.name)
def test_voice_powershell_runners_parse(runner: Path) -> None:
    _assert_powershell_parses(runner)


@pytest.mark.parametrize("runner", VOICE_RUNNERS, ids=lambda path: path.name)
def test_voice_runners_do_not_embed_a_user_profile_root(runner: Path) -> None:
    source = runner.read_text(encoding="utf-8")

    assert re.search(r"(?i)[a-z]:\\users\\", source) is None


def test_voice_cmd_derives_repo_and_validates_dependencies() -> None:
    source = RUNNER_CMD.read_text(encoding="utf-8").lower()

    assert 'for %%i in ("%~dp0..\\..") do set "repo_root=%%~fi"' in source
    assert 'if not exist "%python_exe%"' in source
    assert "protected_bootstrap_v05.py" in source
    assert "aureon_auto_approve_live_voice" not in source
    assert "refusing operation" in source


def test_voice_powershell_runners_derive_repo_and_validate_it() -> None:
    runner_source = RUNNER_PS1.read_text(encoding="utf-8").lower()
    stop_source = STOP_PS1.read_text(encoding="utf-8").lower()

    for source in (runner_source, stop_source):
        assert '(join-path $psscriptroot "..\\..")' in source
        assert "protected_bootstrap_v05.py" in source
        assert "aureon_auto_approve_live_voice" not in source
        assert "refusing operation" in source

    assert 'join-path $reporoot ".venv\\scripts\\python.exe"' in runner_source


def test_voice_runner_speech_and_approval_contract_is_unchanged() -> None:
    cmd_source = RUNNER_CMD.read_text(encoding="utf-8")
    ps_source = RUNNER_PS1.read_text(encoding="utf-8")

    assert "AUREON_AUTO_APPROVE_LIVE_VOICE" not in cmd_source
    assert "AUREON_AUTO_APPROVE_LIVE_VOICE" not in ps_source
    assert "--target-id local-gui" in cmd_source
    assert "--target-id local-gui" in ps_source
    assert "goto loop" not in cmd_source.lower()


def test_stop_runner_preserves_stop_file_contract() -> None:
    source = STOP_PS1.read_text(encoding="utf-8")

    assert "AUREON_AUTO_APPROVE_LIVE_VOICE" not in source
    assert "--target-id local-gui" in source
    assert "protected_bootstrap_v05.py" in source
    assert "aureon_voice_agent.stop" not in source.lower()
