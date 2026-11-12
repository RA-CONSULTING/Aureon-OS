"""The SaaS domain probe locates modules without importing them or their parents.

On 12 Nov 2026 the contained multi-user smoke showed ``exchange_module_count``
going from 0 to 10: the admin pulse calls ``get_platform_status``, which runs
``domain_report`` -> ``probe_domain`` -> ``_module_importable``. That used
``importlib.util.find_spec``, which imports every parent package of a dotted
name, so a status read loaded the exchange clients and trading packages.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_CHILD = r"""
import json, sys
before = set(sys.modules)
from aureon.saas import domains
loaded_by_import = set(sys.modules) - before
out = {
    "present": domains._module_importable("aureon.exchanges.capital_client"),
    "package_present": domains._module_importable("aureon.exchanges"),
    "missing": domains._module_importable("aureon.exchanges.no_such_module_xyz"),
    "missing_parent": domains._module_importable("aureon.no_such_pkg_xyz.child"),
    "empty": domains._module_importable(""),
    "relative": domains._module_importable(".exchanges"),
}
report = domains.domain_report()
after = set(sys.modules) - before - loaded_by_import
out["new_aureon_modules"] = sorted(n for n in after if n.startswith("aureon"))
out["domains"] = len(report) if hasattr(report, "__len__") else None
print(json.dumps(out))
"""


def test_probe_finds_modules_and_imports_none_of_them() -> None:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", str(ROOT)),
        "PYTHONPATH": str(ROOT),
        "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS": "1",
        "AUREON_LIVE_TRADING": "0",
        "AUREON_DISABLE_REAL_ORDERS": "1",
        "AUREON_DISABLE_EXCHANGE_MUTATIONS": "1",
        "AUREON_LLM_OFFLINE": "1",
    }
    done = subprocess.run(
        [sys.executable, "-c", _CHILD],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert done.returncode == 0, done.stderr
    out = json.loads(done.stdout.strip().splitlines()[-1])
    assert out["present"] is True
    assert out["package_present"] is True
    assert out["missing"] is False
    assert out["missing_parent"] is False
    assert out["empty"] is False
    assert out["relative"] is False
    assert out["new_aureon_modules"] == []
