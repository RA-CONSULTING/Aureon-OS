"""Order leak: a collected test must not leave '.' on sys.path.

``test_supervisor_imports_the_checkout_when_started_as_a_script`` removes the
absolute checkout entries and still expects ``import aureon`` to fail. A
relative ``'.'`` entry, with pytest's cwd at the checkout, keeps that import
working. Each polluter is loaded, then the victim runs, in this process.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str, name: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _victim():
    from test_plug_and_play_static import (
        test_supervisor_imports_the_checkout_when_started_as_a_script,
    )

    test_supervisor_imports_the_checkout_when_started_as_a_script()


def test_profit_validation_import_then_supervisor_checkout_stays_closed() -> None:
    _load("tests/test_profit_validation.py", "polluter_profit_validation")
    _victim()


def test_queen_trading_import_then_supervisor_checkout_stays_closed() -> None:
    _load("tests/test_queen_trading.py", "polluter_queen_trading")
    _victim()
