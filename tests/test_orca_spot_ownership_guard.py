"""ORCA exit paths skip Alpaca/Binance/Kraken holdings with no recorded Aureon entry.

Owner rule (9 Nov 2026): Aureon must not close or manage positions Gary opened
himself. A balance alone, or a cost_basis_history.json row alone, is not an
Aureon entry. A holding is an exit candidate only with an open BUY in the radar
shadow book (shadow_book_<venue>.json) or an explicit AUREON_ORCA_ADOPT_POSITIONS
entry. These drive the real monitor and kill-chain functions with fake clients.
No network, no order, no file outside tmp_path.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[1]
BOTS = REPO / "aureon_radar" / "bots"
STATE_ENV = "AUREON_ORCA_SHADOW_STATE_DIR"
ADOPT_ENV = "AUREON_ORCA_ADOPT_POSITIONS"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"_spot_test_{name}", BOTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _book(state_dir: Path, venue: str, symbol: str, side: str = "buy") -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / f"shadow_book_{venue}.json").write_text(json.dumps({
        "venue": venue,
        "positions": {symbol: {"venue": venue, "symbol": symbol, "side": side, "qty": 1.0, "entry_price": 1.0}},
    }), encoding="utf-8")


class FakeAlpaca:
    def __init__(self, positions=()):
        self.positions = list(positions)
        self.orders = []

    def get_positions(self):
        return list(self.positions)

    def get_account(self):
        return {"equity": 0}

    def submit_order(self, symbol, side, qty=None, time_in_force=None):
        self.orders.append((symbol, side, qty))
        return {"status": "accepted", "order_id": "fake"}


class FakeBalanceVenue:
    """Binance/Kraken shaped enough for both bots."""

    def __init__(self, balances):
        self.balances = dict(balances)
        self.orders = []

    # monitor adapters
    def get_balance(self):
        return dict(self.balances)

    def get_price(self, symbol):
        return {"ok": True, "price": 2.0}

    def get_ticker(self, symbol):
        return {"price": 2.0, "last": 2.0, "bid": 1.99, "ask": 2.01}

    def place_order(self, symbol, side, qty, **kwargs):
        self.orders.append((symbol, side, qty))
        return {"status": "FILLED", "mode": "LIVE", "txids": ["fake"]}

    # kill-chain clients
    def account(self):
        return {"balances": [{"asset": a, "free": str(v), "locked": "0"} for a, v in self.balances.items()]}

    def get_account_balance(self):
        return dict(self.balances)

    def place_market_order(self, symbol, side, qty):
        self.orders.append((symbol, side, qty))
        return {"status": "FILLED", "orderId": "fake"}


class NoCapital:
    enabled = False


MANUAL_ALPACA = {"symbol": "AAPL", "qty": "2", "avg_entry_price": "100", "current_price": "150",
                 "unrealized_pl": "100", "unrealized_plpc": "0.5", "side": "long"}


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    state = tmp_path / "radar_state"
    state.mkdir()
    monkeypatch.setenv(STATE_ENV, str(state))
    monkeypatch.delenv(ADOPT_ENV, raising=False)
    return state


@pytest.fixture
def monitor(monkeypatch, isolated):
    mod = _load("orca_live_monitor")
    venues = SimpleNamespace(
        alpaca=FakeAlpaca([MANUAL_ALPACA]),
        binance=FakeBalanceVenue({"ADA": 10.0, "USDT": 5.0}),
        kraken=FakeBalanceVenue({"KNC": 15.70, "ZUSD": 3.0}),
    )
    monkeypatch.setattr(mod, "get_alpaca_adapter", lambda: venues.alpaca)
    monkeypatch.setattr(mod, "get_binance_adapter", lambda: venues.binance)
    monkeypatch.setattr(mod, "get_kraken_adapter", lambda: venues.kraken)
    monkeypatch.setattr(mod, "get_capital_client", lambda: NoCapital())
    monkeypatch.setattr(mod, "journal_live_order", lambda record: None)
    monkeypatch.setattr(mod, "_freshness_block_reason", lambda **_: None)
    mod._venues = venues
    return mod


@pytest.fixture
def kill_chain(monkeypatch, isolated):
    mod = _load("orca_unified_kill_chain")
    monkeypatch.setattr(mod, "queen_answer", lambda question, approves: "y")
    return mod


# ── orca_live_monitor ────────────────────────────────────────────────────────

def test_monitor_skips_manual_kraken_alpaca_binance_holdings(monitor):
    positions = monitor.get_all_positions()
    assert positions["kraken"] == []
    assert positions["alpaca"] == []
    assert positions["binance"] == []


@pytest.mark.parametrize("venue,symbol,qty", [
    ("kraken", "KNC/USD", 15.70),
    ("alpaca", "AAPL", 2.0),
    ("binance", "ADAUSDT", 10.0),
])
def test_monitor_refuses_exit_order_for_manual_holding(monitor, venue, symbol, qty):
    receipt = monitor.submit_exit_order(venue, symbol, qty, 2.0, "MAX HOLD (30 min)", {"symbol": symbol})
    assert receipt["status"] == "refused"
    assert getattr(monitor._venues, venue).orders == []


def test_monitor_keeps_holding_with_recorded_aureon_entry(monitor, isolated):
    _book(isolated, "kraken", "KNC/USD")
    positions = monitor.get_all_positions()
    assert [p["symbol"] for p in positions["kraken"]] == ["KNC/USD"]
    assert positions["alpaca"] == [] and positions["binance"] == []
    receipt = monitor.submit_exit_order("kraken", "KNC/USD", 15.70, 2.0, "TAKE PROFIT", positions["kraken"][0])
    assert receipt["status"] != "refused"
    assert monitor._venues.kraken.orders == [("KNC/USD", "sell", 15.70)]


def test_monitor_explicit_adoption_counts_as_entry(monitor, monkeypatch):
    monkeypatch.setenv(ADOPT_ENV, "alpaca:AAPL")
    assert [p["symbol"] for p in monitor.get_all_positions()["alpaca"]] == ["AAPL"]


def test_monitor_shadow_sell_or_corrupt_book_is_not_an_entry(monitor, isolated):
    _book(isolated, "kraken", "KNC/USD", side="sell")
    (isolated / "shadow_book_binance.json").write_text("{not json", encoding="utf-8")
    positions = monitor.get_all_positions()
    assert positions["kraken"] == [] and positions["binance"] == []


# ── orca_unified_kill_chain spot path ────────────────────────────────────────

def _chain(kraken, binance):
    # cost basis exists for both assets: that alone must not make them ORCA's.
    return SimpleNamespace(
        capital=None, kraken=kraken, binance=binance,
        cost_basis={"KNCUSD": {"avg_entry_price": 1.0}, "ADAUSDT": {"avg_entry_price": 1.0}},
    )


def test_kill_chain_scan_skips_manual_balances_even_with_cost_basis(kill_chain):
    chain = _chain(FakeBalanceVenue({"KNC": 15.70}), FakeBalanceVenue({"ADA": 10.0}))
    assert kill_chain.UnifiedKillChain.scan_all(chain) == []


def test_kill_chain_scan_keeps_balance_with_recorded_entry(kill_chain, isolated):
    _book(isolated, "kraken", "KNC/USD")
    chain = _chain(FakeBalanceVenue({"KNC": 15.70}), FakeBalanceVenue({"ADA": 10.0}))
    found = kill_chain.UnifiedKillChain.scan_all(chain)
    assert [(t["exchange"], t["id"]) for t in found] == [("kraken", "KNC")]


@pytest.mark.parametrize("exchange,symbol,asset", [("kraken", "KNCUSD", "KNC"), ("binance", "ADAUSDT", "ADA")])
def test_kill_chain_refuses_to_sell_manual_balance_even_if_targeted(kill_chain, exchange, symbol, asset):
    client = FakeBalanceVenue({asset: 10.0})
    target = {"exchange": exchange, "symbol": symbol, "id": asset, "type": "SPOT",
              "qty": 10.0, "pnl": 10.0, "client": client}
    kill_chain.UnifiedKillChain.execute_kill_chain(SimpleNamespace(), target)
    assert client.orders == []


def test_kill_chain_still_sells_balance_with_recorded_entry(kill_chain, isolated):
    _book(isolated, "binance", "ADAUSDT")
    client = FakeBalanceVenue({"ADA": 10.0})
    target = {"exchange": "binance", "symbol": "ADAUSDT", "id": "ADA", "type": "SPOT",
              "qty": 10.0, "pnl": 10.0, "client": client}
    kill_chain.UnifiedKillChain.execute_kill_chain(SimpleNamespace(), target)
    assert client.orders == [("ADAUSDT", "SELL", 10.0)]
