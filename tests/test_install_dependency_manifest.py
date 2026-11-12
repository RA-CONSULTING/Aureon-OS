"""Install manifests declare what the evaluated paths import.

A clean-room run on 2026-11-12 found three gaps a stranger hits on a fresh
download: ``mcp`` only in requirements-plug.lock (31 errors in
tests/test_aureon_public_mcp.py on the pytest path), ``filelock`` absent from
the plug lock (fcntl fallback warning), and ``numpy`` absent from the wheel's
dependencies (``aureon.evaluation.brain_proof`` raises ModuleNotFoundError).
These checks read the manifests only. They install nothing and change no
runtime behaviour. Go-live stays HOLD.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _names(lines: list[str]) -> dict[str, str]:
    found: dict[str, str] = {}
    for raw in lines:
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        match = re.match(r"([A-Za-z0-9_.\-]+)", line)
        if match:
            found[match.group(1).lower().replace("_", "-")] = line
    return found


def _requirements(name: str) -> dict[str, str]:
    return _names((ROOT / name).read_text(encoding="utf-8").splitlines())


def _project() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]


def _lock_version(package: str) -> str:
    line = _requirements("requirements-plug.lock")[package]
    return line.split("==", 1)[1]


def test_mcp_is_declared_for_the_pytest_and_linux_paths_at_the_lock_version() -> None:
    pinned = f"mcp=={_lock_version('mcp')}"
    dev = _names(_project()["optional-dependencies"]["dev"])
    assert dev.get("mcp") == pinned
    assert _requirements("requirements-linux.txt").get("mcp") == pinned


def test_filelock_is_in_the_plug_lock_and_the_linux_set() -> None:
    lock = _requirements("requirements-plug.lock")
    direct = _requirements("requirements-plug.txt")
    assert "filelock" in lock
    assert direct.get("filelock") == lock["filelock"]
    assert "filelock" in _requirements("requirements-linux.txt")
    assert "filelock" in _names(_project()["dependencies"])


def test_wheel_dependencies_cover_the_brain_proof_numpy_import() -> None:
    # aureon.evaluation.brain_proof reaches numpy through its evaluation imports.
    assert "numpy" in _names(_project()["dependencies"])
