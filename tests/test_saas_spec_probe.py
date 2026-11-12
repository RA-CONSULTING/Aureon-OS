"""The SaaS reachability probe finds modules without running any package code."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from aureon.saas.spec_probe import module_spec_exists

ROOT = Path(__file__).resolve().parents[1]

_CHILD = """
import json, sys
from aureon.saas import domains, consciousness_catalog
before = set(sys.modules)
found = {
    "exchanges": domains._module_importable("aureon.exchanges.kraken_client"),
    "package": domains._module_importable("aureon.exchanges"),
    "catalog": consciousness_catalog._module_importable("aureon.exchanges.kraken_client"),
    "missing": domains._module_importable("aureon.exchanges.no_such_client"),
}
loaded = sorted(n for n in set(sys.modules) - before if n.startswith("aureon"))
print(json.dumps({"found": found, "loaded": loaded}))
"""


def _run_child() -> dict:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "PYTHONPATH": os.pathsep.join([str(ROOT), os.environ.get("PYTHONPATH", "")]).rstrip(os.pathsep),
        "PYTHONDONTWRITEBYTECODE": "1",
        "AUREON_ACTIVATE_ON_IMPORT": "0",
    }
    completed = subprocess.run(
        [sys.executable, "-c", _CHILD], cwd=str(ROOT), env=env,
        capture_output=True, text=True, timeout=120,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout.strip().splitlines()[-1])


def test_probe_finds_exchange_modules_without_importing_them() -> None:
    result = _run_child()
    assert result["found"] == {"exchanges": True, "package": True, "catalog": True, "missing": False}
    assert not [name for name in result["loaded"] if name.startswith("aureon.exchanges")], result["loaded"]


def test_spec_probe_handles_bad_and_plain_module_names() -> None:
    assert module_spec_exists("json") is True
    assert module_spec_exists("json.decoder") is True
    assert module_spec_exists("json.decoder.not_a_child") is False
    assert module_spec_exists("") is False
    assert module_spec_exists("aureon..saas") is False
    assert module_spec_exists("no_such_top_level_package_xyz") is False
