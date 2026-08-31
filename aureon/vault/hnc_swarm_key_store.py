"""Local HNC swarm key storage.

Stores swarm agent keys as Windows DPAPI-protected blobs under state/. The
metadata is safe to report; the raw agent keys never go into git, Obsidian, or
public frontend JSON.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from aureon.harmonic.hnc_quantum_packet_crypto import sha256_hex

SCHEMA_VERSION = "aureon-hnc-swarm-key-store-v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STORE_DIR = REPO_ROOT / "state/hnc_swarm_key_store"
DEFAULT_AGENT_NAMES = ("seer", "lyra", "king")


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def generate_agent_key() -> str:
    import base64

    return base64.urlsafe_b64encode(os.urandom(32)).decode("ascii").rstrip("=")


def _powershell() -> str:
    exe = shutil.which("powershell.exe") or shutil.which("powershell")
    if not exe:
        raise RuntimeError("powershell_not_available_for_dpapi_key_store")
    return exe


def _run_powershell(script: str, *, stdin: str | None = None, env: dict[str, str] | None = None) -> str:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    # A process started by PowerShell 7 inherits its PSModulePath.  Passing that
    # path to Windows PowerShell 5.1 can make it discover the PowerShell 7 copy
    # of Microsoft.PowerShell.Security first, which cannot be loaded by 5.1.
    # Leave the variable absent in the child so powershell.exe reconstructs its
    # native user, machine, and inbox module paths.  Remove every case variant
    # because Windows environment-variable names are case-insensitive.
    for name in tuple(merged_env):
        if name.casefold() == "psmodulepath":
            del merged_env[name]
    result = subprocess.run(
        [_powershell(), "-NoProfile", "-NonInteractive", "-Command", script],
        input=stdin,
        capture_output=True,
        text=True,
        env=merged_env,
        check=False,
    )
    if result.returncode != 0:
        # Successful DPAPI unprotect operations intentionally return the secret
        # on stdout, while PowerShell diagnostics can contain command input or
        # environment values.  Keep the public failure stable and non-secret.
        raise RuntimeError("powershell_failed")
    return result.stdout


def protect_secret_dpapi(secret: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    script = r"""
$ErrorActionPreference = 'Stop'
$target = $env:AUREON_DPAPI_TARGET
$secret = [Console]::In.ReadToEnd()
$secure = ConvertTo-SecureString -String $secret -AsPlainText -Force
$blob = $secure | ConvertFrom-SecureString
Set-Content -LiteralPath $target -Value $blob -Encoding UTF8
"""
    _run_powershell(script, stdin=secret, env={"AUREON_DPAPI_TARGET": str(path)})


def unprotect_secret_dpapi(path: Path) -> str:
    script = r"""
$ErrorActionPreference = 'Stop'
$target = $env:AUREON_DPAPI_TARGET
$blob = (Get-Content -LiteralPath $target -Raw).Trim()
$secure = ConvertTo-SecureString -String $blob
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
  [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
} finally {
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}
"""
    return _run_powershell(script, env={"AUREON_DPAPI_TARGET": str(path)}).strip()


def _key_path(agent: str, store_dir: Path = DEFAULT_STORE_DIR) -> Path:
    clean = "".join(ch for ch in agent.lower() if ch.isalnum() or ch in {"_", "-"})
    if not clean:
        raise ValueError("invalid_agent_name")
    return store_dir / f"{clean}.dpapi"


def ensure_dpapi_swarm_keys(
    agent_names: Iterable[str] = DEFAULT_AGENT_NAMES,
    *,
    store_dir: Path = DEFAULT_STORE_DIR,
    rotate: bool = False,
) -> dict:
    store_dir.mkdir(parents=True, exist_ok=True)
    agents: list[dict] = []
    for agent in agent_names:
        path = _key_path(agent, store_dir)
        created = False
        if rotate or not path.exists():
            secret = generate_agent_key()
            protect_secret_dpapi(secret, path)
            created = True
        secret_for_fingerprint = unprotect_secret_dpapi(path)
        agents.append(
            {
                "agent": agent,
                "store": "windows_dpapi_current_user",
                "path": str(path),
                "created_or_rotated": created,
                "fingerprint_sha256": sha256_hex(secret_for_fingerprint),
                "secret_policy": "dpapi_blob_only_no_raw_key",
            }
        )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "store_dir": str(store_dir),
        "agent_count": len(agents),
        "agents": agents,
        "secret_policy": "metadata_only_no_raw_keys",
    }
    (store_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def load_dpapi_swarm_agent_keys(
    agent_names: Iterable[str] = DEFAULT_AGENT_NAMES,
    *,
    store_dir: Path = DEFAULT_STORE_DIR,
) -> dict[str, str]:
    keys: dict[str, str] = {}
    for agent in agent_names:
        path = _key_path(agent, store_dir)
        if not path.exists():
            raise FileNotFoundError(f"missing_dpapi_swarm_key:{agent}:{path}")
        keys[agent] = unprotect_secret_dpapi(path)
    return keys


__all__ = [
    "DEFAULT_AGENT_NAMES",
    "DEFAULT_STORE_DIR",
    "SCHEMA_VERSION",
    "ensure_dpapi_swarm_keys",
    "generate_agent_key",
    "load_dpapi_swarm_agent_keys",
    "protect_secret_dpapi",
    "unprotect_secret_dpapi",
]
