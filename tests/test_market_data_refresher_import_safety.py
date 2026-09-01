"""Importing market refresh support must not read repository credentials."""

from __future__ import annotations

import importlib
import sys
import types

import pytest


def test_market_refresher_import_does_not_load_dotenv_without_explicit_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "aureon.data_feeds.market_data_refresher"
    fake_dotenv = types.ModuleType("dotenv")
    fake_dotenv.load_dotenv = lambda *_args, **_kwargs: pytest.fail(
        "market refresher import must not read .env"
    )
    monkeypatch.setitem(sys.modules, "dotenv", fake_dotenv)
    monkeypatch.delitem(sys.modules, module_name, raising=False)
    monkeypatch.delenv("AUREON_ENABLE_MARKET_DOTENV", raising=False)
    monkeypatch.delenv("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", raising=False)

    imported = importlib.import_module(module_name)

    assert imported.REFRESH_INTERVAL_S == 7200
