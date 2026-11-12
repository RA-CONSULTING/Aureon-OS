"""Root conftest helpers stay reachable when another conftest owns the name."""

from __future__ import annotations

import sys
import types

import pytest

from tests.support.root_conftest import ROOT_CONFTEST, root_conftest


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


def test_root_conftest_loads_by_path_without_pytest_config(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, module in list(sys.modules.items()):
        if getattr(module, "__file__", None) and str(module.__file__).endswith("conftest.py"):
            monkeypatch.delitem(sys.modules, name)

    module = root_conftest()

    assert module.__file__ is not None
    assert callable(module._cloud_hold_env_overlay)
