"""ORCA exits only what Aureon really filled on Alpaca/Binance/Kraken, never more.

Owner rule (9 Nov 2026): Aureon must not close or manage positions Gary opened
himself. A balance alone, a cost_basis_history.json row, a paper/shadow book row
or an orca_executions.json attempt row is not an Aureon entry. Only
``aureon_owned_qty`` from ``aureon.exchanges.orca_real_fills`` (#382: confirmed
real buys minus sells) counts, or an explicit AUREON_ORCA_ADOPT_POSITIONS entry
for that venue, minus exits ORCA recorded outside that ledger. Without #382 the
fallback owns nothing. Every exit, including the kill chain's arbitrage Binance
sell, is capped at that. Fake clients, a fake or tmp ledger, tmp records root:
no network, no order, no file outside tmp_path.
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


REAL_FILLS = "aureon.exchanges.orca_real_fills"


def _attempt_row(root: Path, venue: str, pair: str, qty: float) -> None:
    """A real-looking FILLED line in the orca_executions.json attempt log (never read)."""
    _append(root / "orca_executions.json", {
        "timestamp": "2026-11-19T07:00:00",
        "opportunity": {"symbol": pair, "exchange": venue},
        "result": {"status": "FILLED", "pair": pair, "exchange": venue, "volume": qty,
                   "order": {"orderId": "real-1", "status": "FILLED", "executedQty": str(qty)}},
    })


class FakeLedger:
    """Stands in for #382's orca_real_fills: exact (venue, SYMBOL) -> owned qty."""

    def __init__(self):
        self.owned = {}
        self.calls = []
        self.recorded = []

    def aureon_owned_qty(self, venue, symbol):
        self.calls.append((venue, symbol))
        return self.owned.get((venue, symbol), 0)

    def record_confirmed_fill(self, venue, symbol, side, response):  # #382's writer, called by the kill chain
        self.recorded.append((venue, symbol, side))


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
    monkeypatch.setitem(sys.modules, REAL_FILLS, None)  # #382 absent unless a test installs a ledger
    return base


@pytest.fixture
def ledger(monkeypatch, root):
    fake = FakeLedger()
    monkeypatch.setitem(sys.modules, REAL_FILLS, fake)
    return fake


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


def test_kill_chain_scan_skips_manual_balances_even_with_cost_basis(kill_chain, ledger):
    chain = SimpleNamespace(capital=None, kraken=FakeBalanceVenue({"KNC": 15.70}), binance=FakeBalanceVenue({"ADA": 10.0}),
                            cost_basis={"KNCUSD": {"avg_entry_price": 1.0}, "ADAUSDT": {"avg_entry_price": 1.0}})
    assert kill_chain.UnifiedKillChain.scan_all(chain) == []


@pytest.mark.parametrize("exchange,symbol,asset", [("kraken", "KNCUSD", "KNC"), ("binance", "ADAUSDT", "ADA")])
def test_kill_chain_refuses_to_sell_manual_balance_even_if_targeted(kill_chain, ledger, exchange, symbol, asset):
    client = FakeBalanceVenue({asset: 10.0})
    target = {"exchange": exchange, "symbol": symbol, "id": asset, "type": "SPOT",
              "qty": 10.0, "pnl": 10.0, "client": client}
    kill_chain.UnifiedKillChain.execute_kill_chain(SimpleNamespace(), target)
    assert client.orders == []


# ── paper shadow books and the attempt log are not entries ───────────────────

def test_monitor_paper_shadow_book_plus_real_5_eth_sells_nothing(monkeypatch, root, ledger):
    _paper_book(root, "binance", "ETHUSDT")
    _paper_book(root, "alpaca", "ETH/USD")
    _attempt_row(root, "binance", "ETHUSDT", 0.02)
    mon = _monitor(monkeypatch, alpaca=[_alpaca_pos("ETH/USD", 5)], binance={"ETH": 5.0})
    positions = mon.get_all_positions()
    assert positions["binance"] == [] and positions["alpaca"] == []
    for venue, symbol in (("binance", "ETHUSDT"), ("alpaca", "ETH/USD")):
        receipt = mon.submit_exit_order(venue, symbol, 5.0, 3000.0, "TAKE PROFIT", {"symbol": symbol})
        assert receipt["status"] == "refused"
    assert mon._venues.binance.orders == [] and mon._venues.alpaca.orders == []


def test_kill_chain_paper_shadow_book_plus_real_5_eth_sells_nothing(kill_chain, root, ledger):
    _paper_book(root, "binance", "ETHUSDT")
    _attempt_row(root, "binance", "ETHUSDT", 0.02)
    client = FakeBalanceVenue({"ETH": 5.0})
    chain = SimpleNamespace(capital=None, kraken=None, binance=client, cost_basis={"ETHUSDT": {"avg_entry_price": 1.0}})
    assert kill_chain.UnifiedKillChain.scan_all(chain) == []
    target = {"exchange": "binance", "symbol": "ETHUSDT", "id": "ETH", "type": "SPOT", "qty": 5.0, "pnl": 1.0, "client": client}
    kill_chain.UnifiedKillChain.execute_kill_chain(SimpleNamespace(), target)
    assert client.orders == []


# ── a confirmed real fill caps the exit ──────────────────────────────────────

def test_monitor_real_fill_caps_exit_at_owned_qty(monkeypatch, ledger):
    ledger.owned[("binance", "ETHUSDT")] = 0.02
    mon = _monitor(monkeypatch, binance={"ETH": 5.0, "ADA": 10.0})
    positions = mon.get_all_positions()
    assert [(p["symbol"], p["qty"]) for p in positions["binance"]] == [("ETHUSDT", 0.02)]
    receipt = mon.submit_exit_order("binance", "ETHUSDT", 5.0, 3000.0, "TAKE PROFIT", positions["binance"][0])
    assert receipt["status"] != "refused" and receipt["qty"] == 0.02
    assert mon._venues.binance.orders == [("ETHUSDT", "SELL", 0.02)]


def test_monitor_kraken_pair_spelling_matches_ledger_and_keeps_knc_manual(monkeypatch, ledger):
    ledger.owned[("kraken", "ETHUSD")] = 0.02  # the kill chain records kraken_pair, e.g. ETHUSD
    mon = _monitor(monkeypatch, kraken={"ETH": 5.0, "KNC": 15.70})
    assert [(p["symbol"], p["qty"]) for p in mon.get_all_positions()["kraken"]] == [("ETH/USD", 0.02)]


def test_kill_chain_real_fill_caps_scan_and_sell_and_records_exit(kill_chain, root, ledger):
    ledger.owned[("binance", "ETHUSDT")] = 0.02
    client = FakeBalanceVenue({"ETH": 5.0, "ADA": 10.0})
    chain = SimpleNamespace(capital=None, kraken=None, binance=client,
                            cost_basis={"ETHUSDT": {"avg_entry_price": 1.0}, "ADAUSDT": {"avg_entry_price": 1.0}})
    assert [(t["id"], t["qty"]) for t in kill_chain.UnifiedKillChain.scan_all(chain)] == [("ETH", 0.02)]
    target = {"exchange": "binance", "symbol": "ETHUSDT", "id": "ETH", "type": "SPOT", "qty": 5.0, "pnl": 1.0, "client": client}
    kill_chain.UnifiedKillChain.execute_kill_chain(SimpleNamespace(), target)
    assert client.orders == [("ETHUSDT", "SELL", 0.02)]
    rows = [json.loads(line) for line in (root / "state" / "orca_spot_exits.jsonl").read_text().splitlines()]
    assert [(r["venue"], r["symbol"], r["side"], r["qty"], r["status"]) for r in rows] == [("binance", "ETHUSDT", "sell", 0.02, "filled")]
    # the exit is subtracted, so the same target is not sellable again
    kill_chain.UnifiedKillChain.execute_kill_chain(SimpleNamespace(), target)
    assert client.orders == [("ETHUSDT", "SELL", 0.02)]


def test_kill_chain_kraken_scan_caps_with_kraken_asset_codes(kill_chain, ledger):
    ledger.owned[("kraken", "ETHUSD")] = 0.02
    chain = SimpleNamespace(capital=None, binance=None, kraken=FakeBalanceVenue({"XETH": 5.0, "KNC": 15.70}),
                            cost_basis={"XETHUSD": {"avg_entry_price": 1.0}, "KNCUSD": {"avg_entry_price": 1.0}})
    assert [(t["id"], t["qty"]) for t in kill_chain.UnifiedKillChain.scan_all(chain)] == [("XETH", 0.02)]


def test_recorded_exits_are_subtracted(monkeypatch, root, ledger):
    ledger.owned[("binance", "ETHUSDT")] = 0.02
    journal = root / "aureon_radar" / "orca_live_journal.jsonl"
    _append(journal, {"venue": "binance", "symbol": "ETHUSDT", "side": "sell", "qty": 0.015, "status": "LIVE"})
    _append(journal, {"venue": "binance", "symbol": "ETHUSDT", "side": "sell", "qty": 5.0, "status": "refused"})
    _append(journal, {"venue": "kraken", "symbol": "ETH/USD", "side": "sell", "qty": 5.0, "status": "LIVE"})
    mon = _monitor(monkeypatch, binance={"ETH": 5.0})
    [pos] = mon.get_all_positions()["binance"]
    assert pos["qty"] == pytest.approx(0.005)
    _append(root / "state" / "orca_spot_exits.jsonl",
            {"venue": "binance", "symbol": "ETHUSDT", "side": "sell", "qty": 0.005, "status": "failed"})
    assert mon.get_all_positions()["binance"] == []


def test_corrupt_exits_record_fails_closed(monkeypatch, root, ledger):
    ledger.owned[("binance", "ETHUSDT")] = 0.02
    _append(root / "state" / "orca_spot_exits.jsonl", "{not json")
    mon = _monitor(monkeypatch, binance={"ETH": 5.0})
    assert mon.get_all_positions()["binance"] == []


# ── the helper: #382 absent, failing or odd -> nothing owned ─────────────────

def test_without_real_fills_module_nothing_is_owned(monkeypatch, root):
    from aureon.exchanges import orca_spot_ownership as own
    assert own.aureon_owned_qty("binance", "ETHUSDT") == 0.0
    mon = _monitor(monkeypatch, binance={"ETH": 5.0}, kraken={"ETH": 5.0})
    positions = mon.get_all_positions()
    assert positions["binance"] == [] and positions["kraken"] == []


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -0.02, "abc", None, RuntimeError("ledger down")])
def test_helper_errors_or_bad_values_own_nothing(monkeypatch, root, value):
    def helper(venue, symbol):
        if isinstance(value, Exception):
            raise value
        return value if symbol == "ETHUSDT" else 0
    monkeypatch.setitem(sys.modules, REAL_FILLS, SimpleNamespace(aureon_owned_qty=helper))
    from aureon.exchanges import orca_spot_ownership as own
    assert own.sellable_cap("binance", "ETHUSDT") == 0.0


def test_decimal_from_the_real_helper_is_accepted(monkeypatch, root):
    from decimal import Decimal
    monkeypatch.setitem(sys.modules, REAL_FILLS, SimpleNamespace(
        aureon_owned_qty=lambda venue, symbol: Decimal("0.02") if (venue, symbol) == ("binance", "ETHUSDT") else Decimal(0)))
    from aureon.exchanges import orca_spot_ownership as own
    assert own.capped_qty("binance", "ETH", 5.0) == pytest.approx(0.02)


def test_only_the_exact_kill_chain_keys_are_read(ledger):
    for key in (("binance", "ETHUSDC"), ("binance", "ETH"), ("binance", "ETH/USDT"),
                ("kraken", "ETH/USD"), ("kraken", "XETHZUSD"), ("kraken", "ETH"), ("alpaca", "ETH/USD")):
        ledger.owned[key] = 9.0
    from aureon.exchanges import orca_spot_ownership as own
    assert own.capped_qty("binance", "ETH", 5.0) == 0.0
    assert own.capped_qty("kraken", "ETH/USD", 5.0) == 0.0
    assert own.capped_qty("alpaca", "ETH/USD", 5.0) == 0.0
    ledger.owned[("binance", "ETHUSDT")] = 0.02
    ledger.owned[("kraken", "ETHUSD")] = 0.03
    assert own.capped_qty("binance", "ETH", 5.0) == pytest.approx(0.02)
    assert own.capped_qty("kraken", "XETH", 5.0) == pytest.approx(0.03)
    assert set(ledger.calls) == {("binance", "ETHUSDT"), ("kraken", "ETHUSD")}


def test_raising_helper_means_no_sell(monkeypatch, kill_chain, root):
    import decimal

    def boom(venue, symbol):
        raise decimal.Overflow("ledger overflow")
    monkeypatch.setitem(sys.modules, REAL_FILLS, SimpleNamespace(aureon_owned_qty=boom, record_confirmed_fill=lambda *a: None))
    mon = _monitor(monkeypatch, binance={"ETH": 5.0}, kraken={"ETH": 5.0})
    positions = mon.get_all_positions()
    assert positions["binance"] == [] and positions["kraken"] == []
    assert mon.submit_exit_order("binance", "ETHUSDT", 5.0, 3000.0, "TP", {})["status"] == "refused"
    client = FakeBalanceVenue({"ETH": 5.0})
    target = {"exchange": "binance", "symbol": "ETHUSDT", "id": "ETH", "type": "SPOT", "qty": 5.0, "pnl": 1.0, "client": client}
    kill_chain.UnifiedKillChain.execute_kill_chain(SimpleNamespace(), target)
    assert client.orders == [] and mon._venues.binance.orders == []


# ── Charlie's surviving mutations: qty-0 row, venue mismatch, adopt for another venue ──

def test_qty_zero_rows_own_nothing(monkeypatch, ledger):
    ledger.owned[("binance", "ETHUSDT")] = 0
    monkeypatch.setenv(ADOPT_ENV, "binance:ETH:0,kraken:ETH:-1,alpaca:ETH:abc")
    mon = _monitor(monkeypatch, alpaca=[_alpaca_pos("ETH/USD", 5)], binance={"ETH": 5.0}, kraken={"ETH": 5.0})
    positions = mon.get_all_positions()
    assert positions["binance"] == [] and positions["kraken"] == [] and positions["alpaca"] == []
    assert mon.submit_exit_order("binance", "ETHUSDT", 5.0, 3000.0, "TP", {})["status"] == "refused"


def test_fill_on_one_venue_does_not_own_another(monkeypatch, kill_chain, ledger):
    ledger.owned[("kraken", "ETHUSD")] = 0.02
    mon = _monitor(monkeypatch, binance={"ETH": 5.0}, kraken={"ETH": 5.0})
    positions = mon.get_all_positions()
    assert positions["binance"] == [] and [(p["symbol"], p["qty"]) for p in positions["kraken"]] == [("ETH/USD", 0.02)]
    assert mon.submit_exit_order("binance", "ETHUSDT", 5.0, 3000.0, "TP", {})["status"] == "refused"
    client = FakeBalanceVenue({"ETH": 5.0})
    target = {"exchange": "binance", "symbol": "ETHUSDT", "id": "ETH", "type": "SPOT", "qty": 5.0, "pnl": 1.0, "client": client}
    kill_chain.UnifiedKillChain.execute_kill_chain(SimpleNamespace(), target)
    assert client.orders == []
    assert ("binance", "ETHUSDT") in ledger.calls


def test_adoption_for_another_venue_owns_nothing_here(monkeypatch, kill_chain, ledger):
    monkeypatch.setenv(ADOPT_ENV, "kraken:ETH,alpaca:ADA:3")
    mon = _monitor(monkeypatch, alpaca=[_alpaca_pos("ETH/USD", 5)], binance={"ETH": 5.0, "ADA": 10.0})
    positions = mon.get_all_positions()
    assert positions["binance"] == [] and positions["alpaca"] == []
    client = FakeBalanceVenue({"ETH": 5.0})
    target = {"exchange": "binance", "symbol": "ETHUSDT", "id": "ETH", "type": "SPOT", "qty": 5.0, "pnl": 1.0, "client": client}
    kill_chain.UnifiedKillChain.execute_kill_chain(SimpleNamespace(), target)
    assert client.orders == []


# ── explicit adoption ────────────────────────────────────────────────────────

def test_adoption_without_qty_adopts_the_whole_holding(monkeypatch, root):
    """Documented: venue:ASSET (no QTY) caps at the venue balance, like an adopted Capital deal."""
    monkeypatch.setenv(ADOPT_ENV, "kraken:KNC")
    mon = _monitor(monkeypatch, kraken={"KNC": 15.70})
    assert [(p["symbol"], p["qty"]) for p in mon.get_all_positions()["kraken"]] == [("KNC/USD", 15.70)]


def test_adoption_with_qty_caps_at_that_qty(monkeypatch, root):
    monkeypatch.setenv(ADOPT_ENV, "kraken:KNC:3")
    mon = _monitor(monkeypatch, kraken={"KNC": 15.70})
    assert [(p["symbol"], p["qty"]) for p in mon.get_all_positions()["kraken"]] == [("KNC/USD", 3.0)]


# ── the kill chain's arbitrage Binance sell is capped too ────────────────────

class FakeArbKraken(FakeBalanceVenue):
    dry_run = False
    last_balance_source = "live"

    def place_market_order(self, symbol, side, qty):
        self.orders.append((symbol, side, qty))
        return {"status": "FILLED", "orderId": "k-1", "executedQty": "0.04"}


def _arbitrage(kill_chain, binance_balances):
    kraken = FakeArbKraken({"USD": 100.0})
    binance = FakeBalanceVenue(binance_balances)
    chain = SimpleNamespace(kraken=kraken, binance=binance, wins_executed=[],
                            _refresh_portfolio_after_trade=lambda order_sent=True: True)
    opportunity = {"exchange": "arbitrage", "symbol": "ETH/USD", "type": "arbitrage", "buy_exchange": "kraken",
                   "sell_exchange": "binance", "kraken_price": 2000.0, "binance_price": 2010.0, "spread_pct": 0.5}
    return kill_chain.UnifiedKillChain._execute_trade(chain, opportunity), kraken, binance


def test_arbitrage_refuses_binance_sell_of_coins_aureon_does_not_own(monkeypatch, tmp_path, kill_chain, ledger):
    monkeypatch.chdir(tmp_path)  # the attempt log is cwd-relative
    result, kraken, binance = _arbitrage(kill_chain, {"ETH": 5.0})
    assert kraken.orders and kraken.orders[0][1] == "buy"
    assert binance.orders == []
    assert result["status"] == "PARTIAL" and result["sell_error"]["status"] == "REFUSED"


def test_arbitrage_binance_sell_capped_at_owned_qty(monkeypatch, tmp_path, kill_chain, ledger):
    monkeypatch.chdir(tmp_path)
    ledger.owned[("binance", "ETHUSDT")] = 0.02
    _result, _kraken, binance = _arbitrage(kill_chain, {"ETH": 5.0})
    assert binance.orders == [("ETHUSDT", "SELL", 0.02)]


# ── Spike's PASS conditions, against #382's real ledger when it is installed ──

@pytest.fixture
def real_ledger(monkeypatch, root, tmp_path):
    monkeypatch.delitem(sys.modules, REAL_FILLS, raising=False)
    fills = pytest.importorskip(REAL_FILLS, reason="#382 (orca_real_fills) not merged on this base")
    monkeypatch.setattr(fills, "LEDGER_PATH", tmp_path / "state" / "aureon_real_fills.jsonl")
    return fills


def test_real_ledger_kraken_dry_run_receipt_counts_zero(monkeypatch, real_ledger):
    real_ledger.record_confirmed_fill("kraken", "ETHUSD", "buy",
                                      {"status": "not_submitted", "dryRun": True, "submitted": False, "executedQty": None})
    real_ledger.record_confirmed_fill("kraken", "ETHUSD", "buy", {"error": "NO_FUNDS"})
    mon = _monitor(monkeypatch, kraken={"ETH": 5.0})
    assert mon.get_all_positions()["kraken"] == []


def test_real_ledger_filled_buy_caps_and_completed_arbitrage_nets_to_zero(monkeypatch, real_ledger):
    real_ledger.record_confirmed_fill("kraken", "ETHUSD", "buy", {"status": "FILLED", "orderId": "k-1", "executedQty": "0.04"})
    real_ledger.record_confirmed_fill("binance", "ETHUSDT", "SELL", {"status": "FILLED", "orderId": "b-1", "executedQty": "0.04"})
    from aureon.exchanges import orca_spot_ownership as own
    assert own.aureon_owned_qty("kraken", "ETH") + float(real_ledger.aureon_net_fill_qty("binance", "ETHUSDT")) == pytest.approx(0.0)
    assert own.aureon_owned_qty("binance", "ETHUSDT") == 0.0  # negative net is nothing to sell
    mon = _monitor(monkeypatch, binance={"ETH": 5.0}, kraken={"ETH": 5.0})
    positions = mon.get_all_positions()
    assert positions["binance"] == []
    assert [(p["symbol"], p["qty"]) for p in positions["kraken"]] == [("ETH/USD", pytest.approx(0.04))]


def test_real_ledger_corrupt_file_owns_nothing(monkeypatch, real_ledger):
    real_ledger.record_confirmed_fill("binance", "ETHUSDT", "BUY", {"status": "FILLED", "orderId": "b-1", "executedQty": "0.02"})
    with open(real_ledger.LEDGER_PATH, "a", encoding="utf-8") as fh:
        fh.write("{not json\n")
    mon = _monitor(monkeypatch, binance={"ETH": 5.0})
    assert mon.get_all_positions()["binance"] == []


def test_negative_owned_qty_sells_nothing(monkeypatch, kill_chain, ledger):
    """Spike (#382 gate): an earlier arbitrage Binance sell records -q (Gary's coins). cap = max(0, owned)."""
    ledger.owned[("binance", "ETHUSDT")] = -0.04
    mon = _monitor(monkeypatch, binance={"ETH": 5.0})
    assert mon.get_all_positions()["binance"] == []
    receipt = mon.submit_exit_order("binance", "ETHUSDT", 5.0, 3000.0, "TP", {})
    assert receipt["status"] == "refused" and mon._venues.binance.orders == []
    client = FakeBalanceVenue({"ETH": 5.0})
    chain = SimpleNamespace(capital=None, kraken=None, binance=client, cost_basis={"ETHUSDT": {"avg_entry_price": 1.0}})
    assert kill_chain.UnifiedKillChain.scan_all(chain) == []
    target = {"exchange": "binance", "symbol": "ETHUSDT", "id": "ETH", "type": "SPOT", "qty": 5.0, "pnl": 1.0, "client": client}
    kill_chain.UnifiedKillChain.execute_kill_chain(SimpleNamespace(), target)
    assert client.orders == []


class FakeVolExecKraken(FakeArbKraken):
    """A real Kraken closed result: vol_exec, no executedQty, so actual_qty falls back to the request."""

    def place_market_order(self, symbol, side, qty):
        self.orders.append((symbol, side, qty))
        return {"status": "FILLED", "txid": ["K-VOL-1"], "vol_exec": "0.01"}


@pytest.mark.parametrize("owned,expected", [(None, []), (0.02, [("ETHUSDT", "SELL", 0.02)]), (0.5, [("ETHUSDT", "SELL", 0.04)])])
def test_arbitrage_sell_after_vol_exec_only_kraken_fill_is_bounded_by_the_cap(monkeypatch, tmp_path, kill_chain, ledger, owned, expected):
    """Buzz: the Binance leg is sized on the request (0.04) when Kraken returns only vol_exec.

    The owned-qty cap still bounds it: nothing without Binance ownership, at most
    the owned 0.02, and never more than the request.
    """
    monkeypatch.chdir(tmp_path)
    if owned is not None:
        ledger.owned[("binance", "ETHUSDT")] = owned
    kraken = FakeVolExecKraken({"USD": 100.0})
    binance = FakeBalanceVenue({"ETH": 5.0})
    chain = SimpleNamespace(kraken=kraken, binance=binance, wins_executed=[],
                            _refresh_portfolio_after_trade=lambda order_sent=True: True)
    opportunity = {"exchange": "arbitrage", "symbol": "ETH/USD", "type": "arbitrage", "buy_exchange": "kraken",
                   "sell_exchange": "binance", "kraken_price": 2000.0, "binance_price": 2010.0, "spread_pct": 0.5}
    kill_chain.UnifiedKillChain._execute_trade(chain, opportunity)
    assert kraken.orders == [("ETHUSD", "buy", pytest.approx(0.04))]
    assert [(s, side, pytest.approx(q)) for s, side, q in binance.orders] == expected
