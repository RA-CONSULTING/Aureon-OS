"""Root conftest helpers stay reachable when another conftest owns the name."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from tests.support.root_conftest import _FALLBACK_NAME, ROOT_CONFTEST, _root_spec, root_conftest


def test_root_conftest_is_found_when_the_bare_name_is_taken(
    monkeypatch: pytest.MonkeyPatch, pytestconfig: pytest.Config
) -> None:
    impostor = types.ModuleType("conftest")
    impostor.__file__ = str(ROOT_CONFTEST.parent / "tests" / "queen_benchmarks" / "conftest.py")
    monkeypatch.setitem(sys.modules, "conftest", impostor)

    module = root_conftest(pytestconfig)

    assert module is not impostor
    assert callable(module._isolate_leaked_credentials)
    assert callable(module._cloud_hold_env_overlay)


def test_root_conftest_is_found_in_sys_modules_without_pytest_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stand_in = types.ModuleType("conftest_by_other_name")
    stand_in.__file__ = str(ROOT_CONFTEST)
    monkeypatch.setitem(sys.modules, "conftest", types.ModuleType("conftest"))
    monkeypatch.setitem(sys.modules, "conftest_by_other_name", stand_in)

    assert root_conftest() is stand_in


def test_root_conftest_fallback_targets_the_root_file_without_running_it() -> None:
    # Checks the by-path fallback without executing the root conftest a second
    # time, which would repoint journal paths and leave a module behind.
    spec = _root_spec()

    assert spec.origin is not None
    assert Path(spec.origin).resolve() == ROOT_CONFTEST
    assert _FALLBACK_NAME not in sys.modules
