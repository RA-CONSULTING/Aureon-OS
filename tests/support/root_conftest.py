"""Reach the repository-root ``conftest.py`` without relying on its module name.

pytest imports every ``conftest.py`` that sits outside a package under the bare
name ``conftest``. ``tests/queen_benchmarks/conftest.py`` is one of those, so
after it loads, ``from conftest import ...`` finds the benchmark conftest
instead of the root one. Tests that need a root helper ask for it here.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT_CONFTEST = (Path(__file__).resolve().parents[2] / "conftest.py").resolve()
_FALLBACK_NAME = "_aureon_root_conftest"


def _is_root(module: object) -> bool:
    file = getattr(module, "__file__", None)
    return bool(file) and Path(str(file)).resolve() == ROOT_CONFTEST


def _root_spec() -> importlib.machinery.ModuleSpec:
    spec = importlib.util.spec_from_file_location(_FALLBACK_NAME, ROOT_CONFTEST)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {ROOT_CONFTEST}")
    return spec


def root_conftest(config: Any = None) -> ModuleType:
    """Return the root conftest module pytest already loaded, else load it once by path."""
    if config is not None:
        for plugin in config.pluginmanager.get_plugins():
            if isinstance(plugin, ModuleType) and _is_root(plugin):
                return plugin
    for module in list(sys.modules.values()):
        if isinstance(module, ModuleType) and _is_root(module):
            return module
    spec = _root_spec()
    module = importlib.util.module_from_spec(spec)
    sys.modules[_FALLBACK_NAME] = module
    spec.loader.exec_module(module)
    return module
