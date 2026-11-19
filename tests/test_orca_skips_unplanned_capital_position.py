"""Behavioural proof that ORCA's exit paths skip a Capital position Aureon has no plan for.

Gary's own CN50 BUY 0.087 on Capital.com has no Aureon shadow trade, forecast or
entry plan, so neither ``orca_live_monitor`` nor ``orca_unified_kill_chain`` may
treat it as an exit candidate or close it. The existing CN50 tests check source
strings; these drive the real functions with fake clients. No network, no order.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[1]
BOTS = REPO / "aureon_radar" / "bots"
ADOPT_ENV = "AUREON_ORCA_CAPITAL_ADOPT_DEALS"

# Shaped like Capital's /positions reply for a manual CN50 buy with no Aureon plan.
CN50_MANUAL = {
    "market": {"epic": "CN50", "bid": 13000.0, "offer": 13001.0},
    "position": {
        "dealId": "MANUAL-CN50",
        "dealReference": "REF-CN50",
        "size": 0.087,
        "direction": "BUY",
        "level": 12000.0,
        "upl": 87.0,
    },
}


class FakeCapital:
    enabled = True

    def __init__(self, positions):
        self._positions = positions
        self.closed: list = []

    def get_positions(self):
        return list(self._positions)

    def close_position(self, deal_id):
        self.closed.append(deal_id)
        return {"success": True, "status": "submitted"}

    def get_ticker(self, symbol):
        return {"price": 13000.5, "bid": 13000.0, "ask": 13001.0}


class _Empty:
    def get_positions(self):
        return []

    def get_balance(self):
        return {}

    def get_account(self):
        return {"equity": 0}


def _load(name: str):
    path = BOTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_test_{name}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def monitor(monkeypatch):
    mod = _load("orca_live_monitor")
    monkeypatch.setattr(mod, "get_alpaca_adapter", lambda: _Empty())
    monkeypatch.setattr(mod, "get_binance_adapter", lambda: _Empty())
    monkeypatch.setattr(mod, "get_kraken_adapter", lambda: _Empty())
    monkeypatch.setattr(mod, "journal_live_order", lambda record: None)
    monkeypatch.setattr(mod, "_freshness_block_reason", lambda **_: None)
    return mod


@pytest.fixture
def kill_chain():
    return _load("orca_unified_kill_chain")


def test_monitor_does_not_list_unplanned_cn50_as_exit_candidate(monitor, monkeypatch):
    monkeypatch.delenv(ADOPT_ENV, raising=False)
    capital = FakeCapital([CN50_MANUAL])
    monkeypatch.setattr(monitor, "get_capital_client", lambda: capital)
    positions = monitor.get_all_positions()
    assert positions["capital"] == []
    assert capital.closed == []


def test_monitor_lists_only_an_adopted_deal(monitor, monkeypatch):
    adopted = {
        "market": {"epic": "US100", "bid": 1.0},
        "position": {"dealId": "ORCA-1", "size": 0.1, "direction": "SELL", "level": 1.0},
    }
    monkeypatch.setenv(ADOPT_ENV, "ORCA-1")
    monkeypatch.setattr(monitor, "get_capital_client", lambda: FakeCapital([CN50_MANUAL, adopted]))
    symbols = [p["symbol"] for p in monitor.get_all_positions()["capital"]]
    assert symbols == ["US100"]


def test_monitor_exit_order_refuses_unplanned_cn50(monitor, monkeypatch):
    monkeypatch.delenv(ADOPT_ENV, raising=False)
    capital = FakeCapital([CN50_MANUAL])
    monkeypatch.setattr(monitor, "get_capital_client", lambda: capital)
    pos = {"symbol": "CN50", "deal_id": "MANUAL-CN50", "qty": 0.087}
    receipt = monitor.submit_exit_order("capital", "CN50", 0.087, 13000.0, "MAX HOLD (30 min)", pos)
    assert receipt["status"] == "refused"
    assert capital.closed == []


def test_kill_chain_scan_skips_unplanned_cn50(kill_chain, monkeypatch):
    monkeypatch.delenv(ADOPT_ENV, raising=False)
    capital = FakeCapital([CN50_MANUAL])
    fake_self = SimpleNamespace(capital=capital, binance=None, kraken=None, cost_basis={})
    opportunities = kill_chain.UnifiedKillChain.scan_all(fake_self)
    assert [o for o in opportunities if o["exchange"] == "capital"] == []
    assert capital.closed == []


def test_kill_chain_refuses_to_close_unplanned_cn50_even_if_targeted(kill_chain, monkeypatch):
    monkeypatch.delenv(ADOPT_ENV, raising=False)
    monkeypatch.setattr(kill_chain, "queen_answer", lambda question, approves: "y")
    capital = FakeCapital([CN50_MANUAL])
    target = {
        "exchange": "capital",
        "symbol": "CN50",
        "id": "MANUAL-CN50",
        "type": "CFD",
        "qty": 0.087,
        "pnl": 87.0,
        "client": capital,
        "raw": CN50_MANUAL,
    }
    kill_chain.UnifiedKillChain.execute_kill_chain(SimpleNamespace(), target)
    assert capital.closed == []
