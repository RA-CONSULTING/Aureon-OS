"""Boot with dummy exchange keys and install defaults must not place orders.

No network. The dummy values are obvious placeholders, not real keys.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

_DUMMY_KEYS = {
    "ALPACA_API_KEY": "dummy-evaluator-key",
    "ALPACA_SECRET_KEY": "dummy-evaluator-secret",
    "BINANCE_API_KEY": "dummy-evaluator-key",
    "BINANCE_API_SECRET": "dummy-evaluator-secret",
    "KRAKEN_API_KEY": "dummy-evaluator-key",
    "KRAKEN_API_SECRET": "dummy-evaluator-secret",
}

_PINS = {
    "AUREON_LIVE_TRADING": "0",
    "AUREON_DISABLE_REAL_ORDERS": "1",
    "AUREON_DISABLE_EXCHANGE_MUTATIONS": "1",
}


def _load_plug():
    path = ROOT / "scripts" / "plug_and_play.py"
    spec = importlib.util.spec_from_file_location("plug_and_play_dummy_keys", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_installers_pin_order_safety_defaults() -> None:
    sh = (ROOT / "install.sh").read_text(encoding="utf-8")
    assert "export AUREON_LIVE_TRADING=0" in sh
    assert "export AUREON_DISABLE_REAL_ORDERS=1" in sh
    assert "export AUREON_DISABLE_EXCHANGE_MUTATIONS=1" in sh
    assert "source .env" not in sh
    assert "cp .env" not in sh

    ps1 = (ROOT / "install.ps1").read_text(encoding="utf-8")
    assert '$env:AUREON_LIVE_TRADING = "0"' in ps1
    assert '$env:AUREON_DISABLE_REAL_ORDERS = "1"' in ps1
    assert '$env:AUREON_DISABLE_EXCHANGE_MUTATIONS = "1"' in ps1

    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert 'AUREON_LIVE_TRADING: "0"' in compose
    assert 'AUREON_DISABLE_REAL_ORDERS: "1"' in compose
    assert 'AUREON_DISABLE_EXCHANGE_MUTATIONS: "1"' in compose

    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "AUREON_LIVE_TRADING=0" in dockerfile
    assert "AUREON_DISABLE_REAL_ORDERS=1" in dockerfile
    assert "AUREON_DISABLE_EXCHANGE_MUTATIONS=1" in dockerfile


def test_boot_with_dummy_keys_and_defaults_places_no_orders(monkeypatch) -> None:
    for name, value in _DUMMY_KEYS.items():
        monkeypatch.setenv(name, value)
    for name, value in _PINS.items():
        monkeypatch.setenv(name, value)

    plug = _load_plug()
    env = plug.process_env()
    for name in _DUMMY_KEYS:
        assert name not in env
    for name, value in _PINS.items():
        assert env[name] == value

    from aureon.core.aureon_runtime_safety import (
        live_block_reason,
        live_trading_enabled,
        real_orders_allowed,
        require_real_orders_allowed,
    )

    assert live_trading_enabled(env) is False
    assert real_orders_allowed(env) is False
    assert live_block_reason("boot", env) is not None

    # Even if the dummy keys were still present, the pinned defaults
    # must block orders and exchange mutations.
    mixed = {**_DUMMY_KEYS, **_PINS}
    assert live_trading_enabled(mixed) is False
    assert real_orders_allowed(mixed) is False
    reason = live_block_reason("boot", mixed)
    assert reason is not None
    assert "blocks live exchange mutations" in reason
    with pytest.raises(RuntimeError, match="blocks live exchange mutations"):
        require_real_orders_allowed("boot", mixed)
