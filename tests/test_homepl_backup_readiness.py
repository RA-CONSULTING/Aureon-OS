"""Offline safety contract for the exact-root Home.pl backup scripts."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import unicodedata
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKUP_SCRIPT = REPO_ROOT / "website" / "backup-homepl-ftps.ps1"
LAUNCHER_SCRIPT = REPO_ROOT / "tools" / "start-homepl-ftps-backup.ps1"
PUBLISH_SCRIPT = REPO_ROOT / "website" / "publish-homepl-ftps.ps1"


def test_backup_script_is_exact_root_and_remote_read_only() -> None:
    text = BACKUP_SCRIPT.read_text(encoding="utf-8")
    methods = set(re.findall(r"WebRequestMethods\+Ftp\]::([A-Za-z]+)", text))

    assert "[Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$RemoteRoot" in text
    assert "$RemoteRoot -ne '/'" in text
    assert "/public_html" not in text
    assert methods == {"ListDirectory", "GetFileSize", "DownloadFile"}
    assert "UploadFile" not in text
    assert "DeleteFile" not in text
    assert "MakeDirectory" not in text
    assert "RemoveDirectory" not in text
    assert "Rename" not in text


def test_backup_script_binds_preflight_staging_manifest_and_transfer_receipt() -> None:
    text = BACKUP_SCRIPT.read_text(encoding="utf-8")

    assert "[string]$PreflightReceipt" in text
    assert "backup_script_sha256" in text
    assert "preflight_receipt_sha256" in text
    assert "ftp_binding_sha256" in text
    assert "aureon.homepl-root-mapping.v1" in text
    assert "remote_root_index_sha256" in text
    assert "public_root_sha256" in text
    assert "root_mapping_receipt_sha256" in text
    assert "transfer_start_root_listing_sha256" in text
    assert "transfer_end_root_listing_sha256" in text
    assert "transfer_start_root_index_sha256" in text
    assert "transfer_end_root_index_sha256" in text
    assert "The downloaded /index.html does not match" in text
    assert "remote_write_methods_used = $false" in text
    assert "credentials_recorded = $false" in text
    assert "partial-" in text
    assert "[System.IO.Directory]::Move($stagingDirectory, $resolvedOutputDirectory)" in text
    assert "[System.IO.File]::Move($temporaryManifest, $manifestPath)" in text
    assert "[System.IO.File]::Move($temporaryTransferReceipt, $transferReceiptPath)" in text
    assert "Export-Csv" in text
    assert "Test-Path -LiteralPath $manifestPath" in text


def test_backup_launcher_keeps_password_out_of_arguments_and_waits_for_completion() -> None:
    text = LAUNCHER_SCRIPT.read_text(encoding="utf-8")

    assert "$processInfo.EnvironmentVariables['HOMEPL_FTPS_PASSWORD'] = $passwordValue" in text
    assert "$env:HOMEPL_FTPS_PASSWORD" not in text
    assert "EncodedCommand" in text
    assert "$process.WaitForExit()" in text
    assert "CredentialsRecorded = $false" in text
    assert "-PreflightReceipt" in text
    assert "RemoteRoot -ne '/'" in text
    assert text.index("exact repository Home.pl backup script") < text.index("[Console]::In.ReadLine()")
    assert text.index("ftp_binding_sha256") < text.index("[Console]::In.ReadLine()")
    assert "[System.IO.FileShare]::Read" in text
    assert "Get-Sha256Stream -Stream $scriptReadLock" in text
    assert text.index("$scriptReadLock = [System.IO.File]::Open") < text.index("[Console]::In.ReadLine()")
    assert text.index("$process.WaitForExit()") < text.rindex("$scriptReadLock.Dispose()")


def test_backup_launcher_rejects_arbitrary_script_before_secret_handoff(
    tmp_path: Path,
) -> None:
    powershell = shutil.which("powershell")
    if powershell is None:
        pytest.skip("Windows PowerShell is unavailable on this test host.")
    marker = tmp_path / "malicious-script-ran.txt"
    malicious = tmp_path / "malicious.ps1"
    malicious.write_text(
        f"[IO.File]::WriteAllText('{marker}', $env:HOMEPL_FTPS_PASSWORD)\n",
        encoding="utf-8",
    )
    preflight = tmp_path / "forged-preflight.json"
    preflight.write_text("{}\n", encoding="utf-8")
    sentinel = "launcher-secret-sentinel"

    result = subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(LAUNCHER_SCRIPT),
            "-BackupScript",
            str(malicious),
            "-FtpHost",
            "homepl.test",
            "-FtpUser",
            "test-account@example.test",
            "-RemoteRoot",
            "/",
            "-OutputDirectory",
            str(tmp_path / "backup"),
            "-PreflightReceipt",
            str(preflight),
            "-StandardOutputPath",
            str(tmp_path / "stdout.log"),
            "-StandardErrorPath",
            str(tmp_path / "stderr.log"),
        ],
        input=sentinel + "\n",
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert result.returncode != 0
    assert "exact repository Home.pl backup script" in result.stderr
    assert sentinel not in result.stdout
    assert sentinel not in result.stderr
    assert not marker.exists()


def test_backup_launcher_denies_same_path_swap_while_waiting_for_secret(
    tmp_path: Path,
) -> None:
    powershell = shutil.which("powershell")
    if powershell is None or os.name != "nt":
        pytest.skip("Windows PowerShell sharing controls are unavailable.")

    mirror = tmp_path / "repo"
    mirror_backup = mirror / "website" / BACKUP_SCRIPT.name
    mirror_launcher = mirror / "tools" / LAUNCHER_SCRIPT.name
    receipts = mirror / "artifacts" / "website-operator"
    backup_root = mirror / "artifacts" / "homepl-backups"
    for directory in (mirror_backup.parent, mirror_launcher.parent, receipts, backup_root):
        directory.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(BACKUP_SCRIPT, mirror_backup)
    shutil.copyfile(LAUNCHER_SCRIPT, mirror_launcher)

    output = backup_root / f"race-{uuid.uuid4().hex}"
    preflight_path = receipts / "race-preflight.json"
    live_path = receipts / "race-live.json"
    mapping_path = Path(f"{output}-root-mapping.json")
    now = datetime.now(UTC).isoformat()
    live_path.write_text("{}\n", encoding="utf-8")

    def sha_file(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest().upper()

    def sha_text(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()

    host_id = "homepl.test:21"
    account = unicodedata.normalize("NFC", "test-account@example.test")
    host_sha = sha_text(host_id)
    account_sha = sha_text(account)
    binding_sha = sha_text(f"{host_id}\0{account}")
    script_sha = sha_file(mirror_backup)
    required = ["index.html", "styles.css", "script.js"]
    public_sha = "A" * 64
    preflight = {
        "schema": "aureon.website-operator.backup-preflight.v1",
        "run_id": uuid.uuid4().hex,
        "generated_at": now,
        "repo_root": str(mirror),
        "site_root": str(mirror / "website"),
        "config_sha256": "B" * 64,
        "state": "ready-for-explicit-backup",
        "backup_script": str(mirror_backup),
        "backup_script_exists": True,
        "backup_script_safe": True,
        "backup_script_sha256": script_sha,
        "backup_root": str(backup_root),
        "backup_root_safe": True,
        "output_directory": str(output),
        "output_directory_exists": False,
        "output_parent_exists": True,
        "output_parent_safe": True,
        "output_within_backup_root": True,
        "manifest": f"{output}-manifest.csv",
        "manifest_exists": False,
        "root_mapping_receipt": str(mapping_path),
        "root_mapping_receipt_exists": False,
        "transfer_receipt": f"{output}-transfer.json",
        "transfer_receipt_exists": False,
        "remote_root": "/",
        "ftp_host_id": host_id,
        "ftp_host_sha256": host_sha,
        "ftp_account_sha256": account_sha,
        "ftp_binding_sha256": binding_sha,
        "live_reconciliation_receipt": str(live_path),
        "live_reconciliation_receipt_sha256": sha_file(live_path),
        "live_reconciliation_observed_at": now,
        "public_root_url": "https://example.test/",
        "public_root_sha256": public_sha,
        "public_root_bytes": 1,
        "required_root_entries": required,
        "credentials": {
            "required_runtime_names": [
                "HOMEPL_FTPS_HOST",
                "HOMEPL_FTPS_USER",
                "HOMEPL_FTPS_PASSWORD",
            ],
            "values_recorded": False,
        },
        "read_only_contract": {
            "remote_methods": ["ListDirectory", "GetFileSize", "DownloadFile"],
            "remote_write_methods_permitted": False,
            "final_output_published_only_after_complete_download": True,
            "manifest_overwrite_permitted": False,
        },
        "destructive_action": False,
        "execution_attempted": False,
        "note": "race fixture",
    }
    preflight_path.write_text(
        json.dumps(preflight, indent=2) + "\n",
        encoding="utf-8",
    )
    mapping = {
        "schema": "aureon.homepl-root-mapping.v1",
        "state": "authenticated-served-root-mapped",
        "method": "homepl-ftps",
        "source_assertion": "Authenticated Home.pl account mapped to current public root bytes",
        "source_tool": "repo-read-only-ftps-script",
        "observed_at": now,
        "remote_root": "/",
        "ftp_host_id": host_id,
        "ftp_host_sha256": host_sha,
        "ftp_account_sha256": account_sha,
        "ftp_binding_sha256": binding_sha,
        "preflight_receipt": str(preflight_path),
        "preflight_receipt_sha256": sha_file(preflight_path),
        "backup_script": str(mirror_backup),
        "backup_script_sha256": script_sha,
        "live_reconciliation_receipt": str(live_path),
        "live_reconciliation_receipt_sha256": sha_file(live_path),
        "live_reconciliation_observed_at": now,
        "public_root_url": "https://example.test/",
        "public_root_sha256": public_sha,
        "public_root_bytes": 1,
        "remote_root_index_sha256": public_sha,
        "remote_root_index_bytes": 1,
        "listing_entry_count": len(required),
        "listing_sha256": "C" * 64,
        "required_root_entries": required,
        "required_root_entries_observed": True,
        "remote_operations": ["ListDirectory", "DownloadFile"],
        "remote_write_methods_used": False,
        "credentials_recorded": False,
    }
    mapping_path.write_text(json.dumps(mapping, indent=2) + "\n", encoding="utf-8")
    original_hash = sha_file(mirror_backup)
    process = subprocess.Popen(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(mirror_launcher),
            "-BackupScript",
            str(mirror_backup),
            "-FtpHost",
            "homepl.test",
            "-FtpUser",
            account,
            "-RemoteRoot",
            "/",
            "-OutputDirectory",
            str(output),
            "-PreflightReceipt",
            str(preflight_path),
            "-StandardOutputPath",
            str(mirror / "race-stdout.log"),
            "-StandardErrorPath",
            str(mirror / "race-stderr.log"),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    lock_observed = False
    deadline = time.monotonic() + 45
    try:
        while time.monotonic() < deadline and process.poll() is None:
            try:
                with mirror_backup.open("r+b"):
                    pass
            except OSError:
                lock_observed = True
                break
            time.sleep(0.1)
        assert lock_observed
        assert process.poll() is None
        assert process.stdin is not None
        process.stdin.write("\n")
        process.stdin.flush()
        stdout, stderr = process.communicate(timeout=30)
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=10)

    assert process.returncode != 0
    assert "Supply the temporary FTPS password" in stderr
    assert stdout.strip() == ""
    assert sha_file(mirror_backup) == original_hash
    assert not output.exists()
    assert not Path(f"{output}-transfer.json").exists()


def test_backup_path_never_invokes_the_publish_script() -> None:
    backup_text = BACKUP_SCRIPT.read_text(encoding="utf-8")
    launcher_text = LAUNCHER_SCRIPT.read_text(encoding="utf-8")
    publish_text = PUBLISH_SCRIPT.read_text(encoding="utf-8")

    assert "publish-homepl-ftps.ps1" not in backup_text
    assert "publish-homepl-ftps.ps1" not in launcher_text
    assert "UploadFile" in publish_text
    assert "[switch]$Deploy" in publish_text
