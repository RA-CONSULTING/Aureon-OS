"""A pinned finder installed by a non-MCP test module must not leak into later modules.

Seen in a full run: tests/test_aureon_public_stage34.py reaches aureon_public.body,
which installs PinnedAureonFinder. tests/test_aureon_public_stage2.py does the same
via body_call (test_fixture_argument_is_not_built_without_the_sweep_env). Neither
module is in the MCP module list at tests/support/mcp_isolation.py:124-138, so
nothing removed the finder. Later modules then failed, including
tests/test_console_utf8_restored.py ("aureon.utils.console_utf8 is not an aureon
module path") and the sandbox self-repair / queen-gate tests
("checkout aureon/launch/session_scope.py differs from pin ...").
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_INSTALLS = '''
import sys
from pathlib import Path

ROOT = Path({root!r})


def test_installs_the_pinned_finder():
    sys.path.insert(0, str(ROOT / "mcp"))
    from aureon_public.pin_blob import PinnedAureonFinder, install_pinned_aureon_finder

    install_pinned_aureon_finder(ROOT)
    assert any(isinstance(f, PinnedAureonFinder) for f in sys.meta_path)
'''

_AFTER = '''
import sys


def test_next_module_has_no_pinned_finder():
    from aureon_public.pin_blob import PinnedAureonFinder

    assert not any(isinstance(f, PinnedAureonFinder) for f in sys.meta_path)
'''


def test_non_mcp_module_finder_is_removed_before_the_next_module(tmp_path: Path) -> None:
    (tmp_path / "test_a_installs.py").write_text(_INSTALLS.format(root=str(ROOT)), encoding="utf-8")
    (tmp_path / "test_b_after.py").write_text(_AFTER, encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT), env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
    env["AUREON_ACTIVATE_ON_IMPORT"] = "0"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "-p",
            "no:randomly",
            "-p",
            "tests.support.mcp_plugin",
            "--rootdir",
            str(tmp_path),
            "-c",
            os.devnull,
            str(tmp_path / "test_a_installs.py"),
            str(tmp_path / "test_b_after.py"),
        ],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
