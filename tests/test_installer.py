"""The existing installer is production/install.sh and the Windows siblings."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "production" / "install.sh"
PS1 = ROOT / "production" / "Install-AUREON.ps1"
BATS = (
    ROOT / "production" / "install-windows.bat",
    ROOT / "production" / "Install-AUREON-Windows.bat",
)


def test_posix_installer_is_valid_bash_and_calls_the_launcher() -> None:
    text = INSTALL.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash")
    assert os.access(INSTALL, os.X_OK)
    parsed = subprocess.run(["bash", "-n", str(INSTALL)], capture_output=True, text=True)
    assert parsed.returncode == 0, parsed.stderr
    assert "scripts/launch/aureon-master.sh" in text
    assert "_ensure_local_env" in text
    assert ".env.example" in text
    assert "npm run build" in text
    assert "http://127.0.0.1:5173/" in text
    assert "apt-get install" in text
    assert "brew install" in text
    assert "native fallbacks" in text
    assert "production-supervisor" not in text
    assert "rm " not in text


def test_windows_installer_delegates_and_prints_the_ui_url() -> None:
    ps1 = PS1.read_text(encoding="utf-8")
    assert "aureon-master.ps1" in ps1
    assert "_ensure_local_env" in ps1
    assert "npm run build" in ps1
    assert "http://127.0.0.1:5173/" in ps1
    assert "winget install" in ps1
    assert "native fallbacks" in ps1
    assert "production-supervisor" not in ps1
    for bat in BATS:
        text = bat.read_text(encoding="utf-8")
        assert "Install-AUREON.ps1" in text
        lowered = text.casefold()
        assert ".env.example" not in lowered
        assert "capital.com" not in lowered
        assert "live=1" not in lowered
    if shutil.which("pwsh"):
        parsed = subprocess.run(
            ["pwsh", "-NoProfile", "-Command", f"Get-Command -Syntax {PS1}"],
            capture_output=True,
            text=True,
        )
        assert parsed.returncode == 0, parsed.stderr
