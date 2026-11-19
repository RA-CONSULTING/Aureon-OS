"""ORCA exits only what Aureon really filled on Alpaca/Binance/Kraken, never more.

Owner rule (9 Nov 2026): Aureon must not close or manage positions Gary opened
himself. A balance alone, a cost_basis_history.json row alone, or a paper/shadow
book row is not an Aureon entry. Only a real ORCA fill recorded in
orca_executions.json counts (or an explicit AUREON_ORCA_ADOPT_POSITIONS entry),
and any exit is capped at the recorded net real fill (fills minus recorded exits).
These drive the real monitor and kill-chain functions with fake clients and a
tmp records root. No network, no order, no file outside tmp_path.
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
ROOT_ENV = "AUREON_ORCA_RECORDS_ROOT"
OLD_SHADOW_ENV = "AUREON_ORCA_SHADOW_STATE_DIR"  # read by the earlier shadow-book design
ADOPT_ENV = "AUREON_ORCA_ADOPT_POSITIONS"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"_spot_test_{name}", BOTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _append(path: Path, row) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write((row if isinstance(row, str) else json.dumps(row)) + "\n")


def _fill(root: Path, venue: str, pair: str, qty: float, *, status="FILLED", order=None) -> None:
    order = {"orderId": "real-1", "status": "FILLED", "executedQty": str(qty)} if order is None else order
    _append(root / "orca_executions.json", {
        "timestamp": "2026-11-19T07:00:00",
        "opportunity": {"symbol": pair, "exchange": venue},
        "result": {"status": status, "pair": pair, "exchange": venue, "volume": qty, "order": order},
    })


def _paper_book(root: Path, venue: str, symbol: str, qty: float = 0.02) -> None:
    state = root / "aureon_radar" / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / f"shadow_book_{venue}.json").write_text(json.dumps({
        "venue": venue,
        "positions": {symbol: {"venue": venue, "symbol": symbol, "side": "buy", "qty": qty,
                               "entry_price": 3000.0, "signal_source": "paper"}},
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

    def get_balance(self):
        return dict(self.balances)

    def get_price(self, symbol):
        return {"ok": True, "price": 2.0}

    def get_ticker(self, symbol):
        return {"price": 2.0, "last": 2.0, "bid": 1.99, "ask": 2.01}

    def place_order(self, symbol, side, qty, **kwargs):
        self.orders.append((symbol, side, qty))
        return {"status": "FILLED", "mode": "LIVE", "txids": ["fake"]}

    def account(self):
        return {"balances": [{"asset": a, "free": str(v), "locked": "0"} for a, v in self.balances.items()]}

    def get_account_balance(self):
        return dict(self.balances)

    def place_market_order(self, symbol, side, qty):
        self.orders.append((symbol, side, qty))
        return {"status": "FILLED", "orderId": "fake"}


class NoCapital:
    enabled = False


def _alpaca_pos(symbol, qty):
    return {"symbol": symbol, "qty": str(qty), "avg_entry_price": "100", "current_price": "150",
            "unrealized_pl": "1", "unrealized_plpc": "0.5", "side": "long"}


@pytest.fixture
def root(monkeypatch, tmp_path):
    base = tmp_path / "records"
    base.mkdir()
    monkeypatch.setenv(ROOT_ENV, str(base))
    monkeypatch.setenv(OLD_SHADOW_ENV, str(base / "aureon_radar" / "state"))
    monkeypatch.delenv(ADOPT_ENV, raising=False)
    return base


def _monitor(monkeypatch, alpaca=(), binance=None, kraken=None):
    mod = _load("orca_live_monitor")
    venues = SimpleNamespace(
        alpaca=FakeAlpaca(alpaca),
        binance=FakeBalanceVenue(binance or {}),
        kraken=FakeBalanceVenue(kraken or {}),
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
def manual_monitor(monkeypatch, root):
    return _monitor(monkeypatch, alpaca=[_alpaca_pos("AAPL", 2)],
                    binance={"ADA": 10.0, "USDT": 5.0}, kraken={"KNC": 15.70, "ZUSD": 3.0})


@pytest.fixture
def kill_chain(monkeypatch, root):
    mod = _load("orca_unified_kill_chain")
    monkeypatch.setattr(mod, "queen_answer", lambda question, approves: "y")
    return mod


# ── manual holdings (KNC / Alpaca / Binance) ─────────────────────────────────

def test_monitor_skips_manual_kraken_alpaca_binance_holdings(manual_monitor):
    positions = manual_monitor.get_all_positions()
    assert positions["kraken"] == [] and positions["alpaca"] == [] and positions["binance"] == []


@pytest.mark.parametrize("venue,symbol,qty", [
    ("kraken", "KNC/USD", 15.70),
    ("alpaca", "AAPL", 2.0),
    ("binance", "ADAUSDT", 10.0),
])
def test_monitor_refuses_exit_order_for_manual_holding(manual_monitor, venue, symbol, qty):
    receipt = manual_monitor.submit_exit_order(venue, symbol, qty, 2.0, "MAX HOLD (30 min)", {"symbol": symbol})
    assert receipt["status"] == "refused"
    assert getattr(manual_monitor._venues, venue).orders == []


# ── paper / shadow books are not entries ─────────────────────────────────────

def test_monitor_paper_shadow_book_plus_real_5_eth_sells_nothing(monkeypatch, root):
    _paper_book(root, "binance", "ETHUSDT")
    _paper_book(root, "alpaca", "ETH/USD")
    mon = _monitor(monkeypatch, alpaca=[_alpaca_pos("ETH/USD", 5)], binance={"ETH": 5.0})
    positions = mon.get_all_positions()
    assert positions["binance"] == [] and positions["alpaca"] == []
    for venue, symbol in (("binance", "ETHUSDT"), ("alpaca", "ETH/USD")):
        receipt = mon.submit_exit_order(venue, symbol, 5.0, 3000.0, "TAKE PROFIT", {"symbol": symbol})
        assert receipt["status"] == "refused"
    assert mon._venues.binance.orders == [] and mon._venues.alpaca.orders == []


def test_kill_chain_paper_shadow_book_plus_real_5_eth_sells_nothing(kill_chain, root):
    _paper_book(root, "binance", "ETHUSDT")
    client = FakeBalanceVenue({"ETH": 5.0})
    chain = SimpleNamespace(capital=None, kraken=None, binance=client, cost_basis={"ETHUSDT": {"avg_entry_price": 1.0}})
    assert kill_chain.UnifiedKillChain.scan_all(chain) == []
    target = {"exchange": "binance", "symbol": "ETHUSDT", "id": "ETH", "type": "SPOT", "qty": 5.0, "pnl": 1.0, "client": client}
    kill_chain.UnifiedKillChain.execute_kill_chain(SimpleNamespace(), target)
    assert client.orders == []


# ── a real recorded fill caps the exit ───────────────────────────────────────

def test_monitor_real_fill_caps_exit_at_recorded_qty(monkeypatch, root):
    _fill(root, "binance", "ETHUSDT", 0.02)
    mon = _monitor(monkeypatch, binance={"ETH": 5.0, "ADA": 10.0})
    positions = mon.get_all_positions()
    assert [(p["symbol"], p["qty"]) for p in positions["binance"]] == [("ETHUSDT", 0.02)]
    receipt = mon.submit_exit_order("binance", "ETHUSDT", 5.0, 3000.0, "TAKE PROFIT", positions["binance"][0])
    assert receipt["status"] != "refused" and receipt["qty"] == 0.02
    assert mon._venues.binance.orders == [("ETHUSDT", "SELL", 0.02)]


def test_monitor_real_kraken_fill_caps_and_keeps_knc_manual(monkeypatch, root):
    _fill(root, "kraken", "ETHUSD", 0.02)
    mon = _monitor(monkeypatch, kraken={"ETH": 5.0, "KNC": 15.70})
    assert [(p["symbol"], p["qty"]) for p in mon.get_all_positions()["kraken"]] == [("ETH/USD", 0.02)]


def test_kill_chain_real_fill_caps_scan_and_sell_and_records_exit(kill_chain, root):
    _fill(root, "binance", "ETHUSDT", 0.02)
    client = FakeBalanceVenue({"ETH": 5.0, "ADA": 10.0})
    chain = SimpleNamespace(capital=None, kraken=None, binance=client,
                            cost_basis={"ETHUSDT": {"avg_entry_price": 1.0}, "ADAUSDT": {"avg_entry_price": 1.0}})
    found = kill_chain.UnifiedKillChain.scan_all(chain)
    assert [(t["id"], t["qty"]) for t in found] == [("ETH", 0.02)]
    target = {"exchange": "binance", "symbol": "ETHUSDT", "id": "ETH", "type": "SPOT", "qty": 5.0, "pnl": 1.0, "client": client}
    kill_chain.UnifiedKillChain.execute_kill_chain(SimpleNamespace(), target)
    assert client.orders == [("ETHUSDT", "SELL", 0.02)]
    # the exit was recorded, so the same target is not sellable again
    kill_chain.UnifiedKillChain.execute_kill_chain(SimpleNamespace(), target)
    assert client.orders == [("ETHUSDT", "SELL", 0.02)]


def test_kill_chain_real_kraken_fill_caps_scan(kill_chain, root):
    _fill(root, "kraken", "ETHUSD", 0.02)
    chain = SimpleNamespace(capital=None, binance=None, kraken=FakeBalanceVenue({"ETH": 5.0, "KNC": 15.70}),
                            cost_basis={"ETHUSD": {"avg_entry_price": 1.0}, "KNCUSD": {"avg_entry_price": 1.0}})
    assert [(t["id"], t["qty"]) for t in kill_chain.UnifiedKillChain.scan_all(chain)] == [("ETH", 0.02)]


def test_recorded_exits_are_subtracted(monkeypatch, root):
    _fill(root, "binance", "ETHUSDT", 0.02)
    _append(root / "aureon_radar" / "orca_live_journal.jsonl",
            {"venue": "binance", "symbol": "ETHUSDT", "side": "sell", "qty": 0.015, "status": "LIVE"})
    _append(root / "aureon_radar" / "orca_live_journal.jsonl",
            {"venue": "binance", "symbol": "ETHUSDT", "side": "sell", "qty": 5.0, "status": "refused"})
    mon = _monitor(monkeypatch, binance={"ETH": 5.0})
    [pos] = mon.get_all_positions()["binance"]
    assert pos["qty"] == pytest.approx(0.005)
    _append(root / "orca_executions.json",
            {"kind": "exit", "exchange": "binance", "symbol": "ETHUSDT", "asset": "ETH", "qty": 0.005, "status": "failed"})
    assert mon.get_all_positions()["binance"] == []


# ── dry-run / skipped / not-submitted execution records are not owned ────────

@pytest.mark.parametrize("status,order", [
    ("BALANCE_DRY_RUN", {"orderId": "x", "executedQty": "0.02"}),
    ("SKIPPED", {"orderId": "x", "executedQty": "0.02"}),
    ("NO_FUNDS", None),
    ("FILLED", {"status": "not_submitted", "dryRun": True, "submitted": False, "executedQty": None}),
    ("FILLED", {"orderId": "x", "status": "FILLED", "executedQty": "0.02", "mode": "DRY_RUN"}),
    ("FILLED", {"orderId": "x", "status": "FILLED", "executedQty": "0.02", "paper": True}),
    ("FILLED", {"orderId": "x", "status": "submitted", "executedQty": None, "filled_qty": None}),
])
def test_dry_run_skipped_or_unfilled_records_are_not_owned(monkeypatch, root, status, order):
    _fill(root, "binance", "ETHUSDT", 0.02, status=status, order=order if order is not None else {})
    mon = _monitor(monkeypatch, binance={"ETH": 5.0})
    assert mon.get_all_positions()["binance"] == []
    assert mon.submit_exit_order("binance", "ETHUSDT", 5.0, 3000.0, "TP", {})["status"] == "refused"


def test_corrupt_records_fail_closed(monkeypatch, root):
    _fill(root, "binance", "ETHUSDT", 0.02)
    _append(root / "orca_executions.json", "{not json")
    mon = _monitor(monkeypatch, binance={"ETH": 5.0})
    assert mon.get_all_positions()["binance"] == []


# ── explicit adoption ────────────────────────────────────────────────────────

def test_adoption_without_qty_adopts_the_whole_holding(monkeypatch, root):
    """Documented: ``venue:ASSET`` with no QTY is an explicit whole-holding adoption."""
    monkeypatch.setenv(ADOPT_ENV, "alpaca:AAPL")
    mon = _monitor(monkeypatch, alpaca=[_alpaca_pos("AAPL", 2)])
    assert [(p["symbol"], p["qty"]) for p in mon.get_all_positions()["alpaca"]] == [("AAPL", 2.0)]


def test_adoption_with_qty_caps_at_that_qty(monkeypatch, root):
    monkeypatch.setenv(ADOPT_ENV, "kraken:KNC:3")
    mon = _monitor(monkeypatch, kraken={"KNC": 15.70})
    assert [(p["symbol"], p["qty"]) for p in mon.get_all_positions()["kraken"]] == [("KNC/USD", 3.0)]


# ── kill chain manual cases ──────────────────────────────────────────────────

def test_kill_chain_scan_skips_manual_balances_even_with_cost_basis(kill_chain, root):
    chain = SimpleNamespace(capital=None, kraken=FakeBalanceVenue({"KNC": 15.70}), binance=FakeBalanceVenue({"ADA": 10.0}),
                            cost_basis={"KNCUSD": {"avg_entry_price": 1.0}, "ADAUSDT": {"avg_entry_price": 1.0}})
    assert kill_chain.UnifiedKillChain.scan_all(chain) == []


@pytest.mark.parametrize("exchange,symbol,asset", [("kraken", "KNCUSD", "KNC"), ("binance", "ADAUSDT", "ADA")])
def test_kill_chain_refuses_to_sell_manual_balance_even_if_targeted(kill_chain, root, exchange, symbol, asset):
    client = FakeBalanceVenue({asset: 10.0})
    target = {"exchange": exchange, "symbol": symbol, "id": asset, "type": "SPOT",
              "qty": 10.0, "pnl": 10.0, "client": client}
    kill_chain.UnifiedKillChain.execute_kill_chain(SimpleNamespace(), target)
    assert client.orders == []


def test_kill_chain_writes_fills_and_exits_where_the_guard_reads():
    """Real buys and spot exits must land in the file orca_spot_ownership reads."""
    src = (BOTS / "orca_unified_kill_chain.py").read_bytes().decode("utf-8")
    assert "open('orca_executions.json'" not in src
    assert src.count("with open(executions_path(), 'a') as f:") == 2
