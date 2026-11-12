"""plug_and_play ports can move off ports a machine already uses.

No network. Defaults stay 8790 / 8077 / 5173 / 8787.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_NAMES = (
    "AUREON_PLUG_OPERATOR_PORT",
    "AUREON_PLUG_MCP_PORT",
    "AUREON_PLUG_FRONTEND_PORT",
    "AUREON_PLUG_STACK_PORT",
)


def _load(monkeypatch, **env):
    for name in _NAMES:
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    spec = importlib.util.spec_from_file_location(
        "plug_ports_under_test", ROOT / "scripts" / "plug_and_play.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_defaults_unchanged(monkeypatch):
    plug = _load(monkeypatch)
    assert (plug.OPERATOR_PORT, plug.MCP_PORT, plug.FRONTEND_PORT, plug.STACK_PORT) == (
        8790, 8077, 5173, 8787,
    )
    assert plug.OPERATOR_URL == "http://127.0.0.1:8790"


def test_overrides_reach_urls_commands_and_child_env(monkeypatch):
    plug = _load(
        monkeypatch,
        AUREON_PLUG_OPERATOR_PORT="18790",
        AUREON_PLUG_MCP_PORT="18077",
        AUREON_PLUG_FRONTEND_PORT="15173",
        AUREON_PLUG_STACK_PORT="18787",
    )
    assert plug.OPERATOR_URL == "http://127.0.0.1:18790"
    assert plug.MCP_URL == "http://127.0.0.1:18077/mcp"
    assert plug.FRONTEND_URL == "http://127.0.0.1:15173/"
    assert plug.STACK_URL == "http://127.0.0.1:18787"
    env = plug.process_env()
    assert env["AUREON_OPERATOR_PORT"] == "18790"
    assert env["VITE_OPERATOR_URL"] == "http://127.0.0.1:18790"
    assert env["AUREON_OPERATOR_URL"] == "http://127.0.0.1:18790"
    # order-safety pins are untouched by the port change
    assert env["AUREON_LIVE_TRADING"] == "0"
    assert env["AUREON_DISABLE_REAL_ORDERS"] == "1"
    assert env["AUREON_DISABLE_EXCHANGE_MUTATIONS"] == "1"


@pytest.mark.parametrize("bad", ["abc", "0", "70000", "-1"])
def test_bad_port_stops_the_run(monkeypatch, bad):
    with pytest.raises(SystemExit):
        _load(monkeypatch, AUREON_PLUG_OPERATOR_PORT=bad)
