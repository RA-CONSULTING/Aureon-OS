from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER_DIR = REPO_ROOT / "scripts" / "launchers"
POWERSHELL_LAUNCHERS = (
    LAUNCHER_DIR / "AUREON_WAKE_UP_FULL_AUTONOMOUS.ps1",
    LAUNCHER_DIR / "AUREON_DATA_OCEAN.ps1",
    LAUNCHER_DIR / "start_everything_production.ps1",
)
CMD_WRAPPERS = (
    LAUNCHER_DIR / "AUREON_PRODUCTION_LIVE.cmd",
    LAUNCHER_DIR / "AUREON_WAKE_UP_FULL_AUTONOMOUS.cmd",
    LAUNCHER_DIR / "AUREON_DATA_OCEAN.cmd",
)


def _powershell() -> str:
    executable = shutil.which("powershell.exe") or shutil.which("pwsh") or shutil.which("powershell")
    if executable is None:
        pytest.skip("PowerShell is unavailable; static launcher contracts still run.")
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


@pytest.mark.parametrize("launcher", POWERSHELL_LAUNCHERS, ids=lambda path: path.name)
def test_primary_powershell_launchers_parse(launcher: Path) -> None:
    _assert_powershell_parses(launcher)


@pytest.mark.parametrize(
    ("launcher", "stale_anchor"),
    (
        (POWERSHELL_LAUNCHERS[0], "$myinvocation.scriptname"),
        (POWERSHELL_LAUNCHERS[1], "$myinvocation.mycommand.path"),
        (POWERSHELL_LAUNCHERS[2], "$myinvocation.mycommand.definition"),
    ),
    ids=lambda value: value.name if isinstance(value, Path) else None,
)
def test_primary_powershell_launchers_resolve_the_repo_root(
    launcher: Path, stale_anchor: str
) -> None:
    source = launcher.read_text(encoding="utf-8").lower()

    assert "$psscriptroot" in source
    assert '"..\\.."' in source
    assert "pyproject.toml" in source
    assert stale_anchor not in source


@pytest.mark.parametrize("wrapper", CMD_WRAPPERS, ids=lambda path: path.name)
def test_primary_cmd_wrappers_resolve_root_and_propagate_exit_code(wrapper: Path) -> None:
    source = wrapper.read_text(encoding="utf-8").lower()

    assert '%~dp0..\\..' in source
    assert 'if not exist "%repo_root%\\pyproject.toml"' in source
    assert 'pushd "%repo_root%" >nul' in source
    assert 'set "exit_code=%errorlevel%"' in source
    assert "popd" in source
    assert source.rstrip().endswith("endlocal & exit /b %exit_code%")
    assert 'cd /d "%~dp0"' not in source


@pytest.mark.skipif(os.name != "nt", reason="Production launcher is Windows-only.")
def test_start_everything_whatif_uses_current_launcher_paths(tmp_path: Path) -> None:
    environment = os.environ.copy()
    environment.update({"LIVE": "0", "DRY_RUN": "1", "AUREON_LIVE_TRADING": "0"})
    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(LAUNCHER_DIR / "start_everything_production.ps1"),
            "-WhatIf",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
        check=False,
    )
    output = (result.stdout + result.stderr).lower()

    assert result.returncode == 0, output
    assert "whatif mode" in output
    assert "scripts\\launchers\\aureon_production_live.cmd" in output
    assert "scripts\\start_aureon_with_flameborn.ps1" in output
    assert "both terminals launched" not in output
