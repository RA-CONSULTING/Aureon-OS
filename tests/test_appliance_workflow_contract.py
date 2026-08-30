from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ATTEST = ROOT / "packaging" / "appliance" / "rootfs" / "usr" / "lib" / "aureon" / "aureon-boot-attest"
BOOT_MARKER = "AUREON_APPLIANCE_BOOTABLE_FIRSTBOOT_REQUIRED"
WORKFLOW = ROOT / ".github" / "workflows" / "aureon-appliance-acceptance.yml"


def _posix_shell() -> Path:
    if os.name != "nt":
        shell = shutil.which("sh")
        if shell:
            return Path(shell)
    for root in (
        os.environ.get("PROGRAMFILES"),
        os.environ.get("PROGRAMW6432"),
        r"C:\Program Files",
    ):
        if root:
            candidate = Path(root) / "Git" / "bin" / "bash.exe"
            if candidate.is_file():
                return candidate
    pytest.skip("a POSIX-compatible shell is unavailable")


def _fake_systemctl(tmp_path: Path) -> Path:
    tool_dir = tmp_path / "bin"
    tool_dir.mkdir()
    command = tool_dir / "systemctl"
    command.write_text(
        """#!/bin/sh
verb=$1
case "$verb" in
    show)
        property=$2
        unit=$4
        case "$property" in
            --property=FragmentPath) printf '%s\\n' "/usr/lib/systemd/system/$unit" ;;
            --property=DropInPaths) printf '\\n' ;;
            *) exit 64 ;;
        esac
        ;;
    is-enabled)
        unit=$2
        if [ "${AUREON_TEST_BAD_ENABLEMENT:-}" = "$unit" ]; then
            printf '%s\\n' enabled
            exit 0
        fi
        case "$unit" in
            aureon-boot-attestation.service|aureon-firstboot-console.service)
                printf '%s\\n' enabled
                ;;
            getty@tty1.service)
                printf '%s\\n' masked
                exit 1
                ;;
            *)
                printf '%s\\n' disabled
                exit 1
                ;;
        esac
        ;;
    is-active) exit 1 ;;
    *) exit 64 ;;
esac
""",
        encoding="utf-8",
        newline="\n",
    )
    command.chmod(0o755)
    return tool_dir


def _run_attestor(tmp_path: Path, *, bad_enablement: str | None = None) -> subprocess.CompletedProcess[str]:
    shell = _posix_shell()
    tool_dir = _fake_systemctl(tmp_path)
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join((str(tool_dir), env.get("PATH", "")))
    if bad_enablement is not None:
        env["AUREON_TEST_BAD_ENABLEMENT"] = bad_enablement
    return subprocess.run(
        [str(shell), str(ATTEST)],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def test_unprovisioned_attestor_emits_exact_adjacent_boot_evidence(tmp_path: Path) -> None:
    completed = _run_attestor(tmp_path)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines() == [
        BOOT_MARKER,
        '{"schema":"aureon.appliance.boot.v1","status":"hold",'
        '"reason":"local_console_firstboot_required","core_started":false}',
    ]


def test_generator_style_enablement_drift_fails_before_boot_marker(tmp_path: Path) -> None:
    completed = _run_attestor(tmp_path, bad_enablement="aureon-operator.service")
    assert completed.returncode == 78
    assert (
        "AUREON_APPLIANCE_POLICY_HOLD unexpected_enablement "
        "unit=aureon-operator.service expected=disabled actual=enabled"
    ) in completed.stdout
    assert BOOT_MARKER not in completed.stdout


def test_acceptance_workflow_is_static_and_runs_both_contract_suites() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")
    assert "permissions:\n  contents: read" in source
    assert "tests/test_appliance_packaging_contract.py" in source
    assert "tests/test_appliance_workflow_contract.py" in source
    assert 'bash -n "$script"' in source
    assert "Language.Parser]::ParseFile" in source
    for forbidden in (
        "mkosi build",
        "Register-AureonAppliance.ps1 -",
        "Start-VM",
        "New-VM",
        "Invoke-WebRequest",
        "curl ",
        "wget ",
    ):
        assert forbidden not in source
