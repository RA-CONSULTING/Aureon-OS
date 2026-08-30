from __future__ import annotations

import ast
import math
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from scripts.validation import validate_real_data_contract as validator


ROOT = Path(__file__).resolve().parents[1]
ORCA_PATH = ROOT / "aureon" / "bots" / "orca_complete_kill_cycle.py"


@dataclass
class _Opportunity:
    symbol: str
    exchange: str
    price: float
    change_pct: float
    volume: float
    momentum_score: float
    fee_rate: float


def _load_orca_functions(*method_names: str) -> dict[str, Any]:
    """Execute selected definitions without importing Orca's integration graph."""
    tree = ast.parse(ORCA_PATH.read_text(encoding="utf-8"), filename=str(ORCA_PATH))
    helper_names = {
        "_finite_number",
        "_provider_number",
        "_provider_sequence_number",
        "_provider_timestamp",
        "_provider_is_fresh",
    }
    selected = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in helper_names
    ]
    orca_class = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "OrcaKillCycle"
    )
    selected.extend(
        node for node in orca_class.body
        if isinstance(node, ast.FunctionDef) and node.name in set(method_names)
    )
    module = ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[]))
    namespace = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "Tuple": Tuple,
        "Union": Union,
        "MarketOpportunity": _Opportunity,
        "datetime": datetime,
        "math": math,
        "_time": time,
    }
    exec(compile(module, str(ORCA_PATH), "exec"), namespace)
    return namespace


def test_provider_numbers_require_explicit_finite_fields():
    ns = _load_orca_functions()
    read = ns["_provider_number"]
    read_sequence = ns["_provider_sequence_number"]

    assert read({}, "price", positive=True) is None
    assert read({"price": None}, "price", positive=True) is None
    assert read({"price": "nan"}, "price", positive=True) is None
    assert read({"price": "inf"}, "price", positive=True) is None
    assert read({"price": 0}, "price", positive=True) is None
    assert read({"price": "12.5"}, "price", positive=True) == 12.5
    assert read({"change": "-2.5"}, "change") == -2.5
    assert read({"volume": 0}, "volume", nonnegative=True) == 0.0
    assert read_sequence({"c": ["101.25"]}, "c", positive=True) == 101.25
    assert read_sequence({"c": []}, "c", positive=True) is None


def test_price_only_binance_receipt_never_becomes_bid_or_ask():
    ns = _load_orca_functions("_get_binance_ticker")

    class Client:
        def get_ticker(self, _symbol):
            return {}

        def get_ticker_price(self, _symbol):
            return {"price": "42.5"}

    result = ns["_get_binance_ticker"](object(), Client(), "BTCUSDT")

    assert result == {"price": 42.5}
    assert "bid" not in result
    assert "ask" not in result


def test_binance_scanner_omits_incomplete_provider_tickers():
    ns = _load_orca_functions("_scan_binance_market")

    class Response:
        status_code = 200

        def json(self):
            return [
                {"symbol": "MISSUSDT", "lastPrice": "2", "priceChangePercent": "5"},
                {
                    "symbol": "BTCUSDT",
                    "lastPrice": "100",
                    "priceChangePercent": "2",
                    "quoteVolume": "2500000",
                },
            ]

    class Session:
        def get(self, *_args, **_kwargs):
            return Response()

    class Client:
        session = Session()
        base = "https://offline.invalid"
        uk_mode = False

        @staticmethod
        def is_uk_restricted_symbol(_symbol):
            return False

    owner = type("Owner", (), {})()
    owner.clients = {"binance": Client()}
    owner.fee_rates = {"binance": 0.001}

    results = ns["_scan_binance_market"](owner, 1.0, 1.0)

    assert [item.symbol for item in results] == ["BTC/USDT"]
    assert results[0].price == 100.0
    assert results[0].volume == 2_500_000.0


def test_quantum_market_data_rejects_stale_or_incomplete_bars():
    ns = _load_orca_functions("_get_real_market_data")
    now = time.time()

    class Alpaca:
        bars = []

        def get_crypto_bars(self, *_args, **_kwargs):
            return {"bars": {"BTC/USD": self.bars}}

    alpaca = Alpaca()
    owner = type("Owner", (), {"clients": {"alpaca": alpaca}})()
    get_market_data = ns["_get_real_market_data"]

    alpaca.bars = [
        {"t": now - 1_000, "c": "100", "v": "1"},
        {"t": now - 900, "c": "101", "v": "2"},
    ]
    stale = get_market_data(owner, "BTC/USD", {"BTC/USD": 999_999})
    assert stale["data_status"] == "no_data"
    assert stale["price"] is None
    assert stale["blocker"] == "stale_or_untimestamped_alpaca_bar"

    alpaca.bars = [
        {"t": now - 60, "c": "100", "v": "1"},
        {"t": now - 1, "c": "101"},
    ]
    incomplete = get_market_data(owner, "BTC/USD", {})
    assert incomplete["data_status"] == "no_data"
    assert incomplete["blocker"] == "incomplete_alpaca_volume_series"


def test_quantum_market_data_uses_complete_fresh_candles_only():
    ns = _load_orca_functions("_get_real_market_data")
    now = time.time()

    class Alpaca:
        def get_crypto_bars(self, *_args, **_kwargs):
            return {
                "bars": {
                    "BTC/USD": [
                        {"t": now - 60, "c": "100", "v": "1.25"},
                        {"t": now - 1, "c": "101", "v": "2.75"},
                    ]
                }
            }

    owner = type("Owner", (), {"clients": {"alpaca": Alpaca()}})()
    result = ns["_get_real_market_data"](owner, "BTC/USD", {})

    assert result["data_status"] == "live"
    assert result["source"] == "alpaca_crypto_bars"
    assert result["price"] == 101.0
    assert result["volume"] == 4.0
    assert result["change_pct"] == 1.0
    assert result["momentum"] == 0.6
    assert result["source_timestamp"] == now - 1


def test_order_normalizer_never_invents_fill_receipts():
    ns = _load_orca_functions("normalize_order_response")
    normalize = ns["normalize_order_response"]
    owner = object()

    missing = normalize(owner, {"orderId": 123}, "binance")
    assert missing["data_status"] == "no_data"
    assert missing["filled_qty"] is None
    assert missing["filled_avg_price"] is None

    dry_run = normalize(owner, {"dryRun": True}, "binance")
    assert dry_run["data_status"] == "not_submitted"
    assert dry_run["order_id"] is None
    assert dry_run["filled_qty"] is None

    placeholder = normalize(
        owner,
        {
            "id": "dry_run_id",
            "status": "filled",
            "filled_qty": "2",
            "filled_avg_price": "10.5",
        },
        "alpaca",
    )
    assert placeholder["data_status"] == "not_submitted"
    assert placeholder["order_id"] is None
    assert placeholder["filled_qty"] is None

    live = normalize(
        owner,
        {
            "orderId": 123,
            "executedQty": "2",
            "cummulativeQuoteQty": "21",
            "status": "FILLED",
        },
        "binance",
    )
    assert live["data_status"] == "live"
    assert live["order_id"] == 123
    assert live["filled_qty"] == 2.0
    assert live["filled_avg_price"] == 10.5

    # Kraken AddOrder acknowledgement fields are not a fill receipt. The
    # Kraken adapter must provide its own confirmed vol_exec/cost evidence.
    unconfirmed_kraken = normalize(
        owner,
        {
            "txid": ["OID-1"],
            "executedQty": "2",
            "cummulativeQuoteQty": "21",
            "status": "FILLED",
        },
        "kraken",
    )
    assert unconfirmed_kraken["data_status"] == "no_data"
    assert unconfirmed_kraken["filled_qty"] is None
    assert unconfirmed_kraken["filled_avg_price"] is None


def test_cash_and_energy_omit_unpriced_gbp_instead_of_using_fixed_fx():
    ns = _load_orca_functions("get_available_cash", "_get_energy_snapshot")

    class Kraken:
        api_key = "offline-test-key"
        api_secret = "offline-test-secret"

        @staticmethod
        def get_balance():
            return {"ZUSD": "10", "ZGBP": "5"}

    owner = type("Owner", (), {})()
    owner.clients = {"kraken": Kraken()}
    owner._get_live_crypto_prices = lambda: {}
    owner.energy_last_totals = {}

    cash = ns["get_available_cash"](owner)
    assert cash == {"kraken": 10.0}
    assert owner.last_cash_status["kraken"] == "partial_no_data:ZGBP"

    energy = ns["_get_energy_snapshot"](owner)
    assert energy["exchanges"]["kraken"]["cash"] == 10.0
    assert energy["exchanges"]["kraken"]["data_status"] == "partial"
    assert "no_data:ZGBPUSD" in energy["exchanges"]["kraken"]["blockers"]


def test_capital_scanner_requires_provider_volume():
    ns = _load_orca_functions("_scan_capital_market")

    class Capital:
        enabled = True

        @staticmethod
        def get_tickers_for_symbols(_symbols, max_workers=10):
            assert max_workers == 10
            return {
                "MISSING_VOLUME": {"price": "100", "change_pct": "2"},
                "COMPLETE": {
                    "price": "101",
                    "change_pct": "3",
                    "volume": "2500",
                },
            }

    owner = type("Owner", (), {})()
    owner._ensure_capital_client = lambda: Capital()
    owner.fee_rates = {"capital": 0.0008}

    results = ns["_scan_capital_market"](owner, 1.0, 1.0)

    assert [item.symbol for item in results] == ["COMPLETE"]
    assert results[0].volume == 2500.0


def test_kraken_position_valuation_requires_kraken_bid():
    ns = _load_orca_functions("get_all_positions")

    class CostBasis:
        @staticmethod
        def get_entry_price(_symbol, _exchange):
            return 90.0

    class Kraken:
        bid = "100"

        @staticmethod
        def get_balance():
            return {"BTC": "1"}

        def get_ticker(self, _symbol):
            return {"bid": self.bid}

    kraken = Kraken()
    owner = type("Owner", (), {})()
    owner.clients = {"kraken": kraken}
    owner.cost_basis_tracker = CostBasis()

    live = ns["get_all_positions"](owner)
    assert live["kraken"][0]["current_price"] == 100.0
    assert live["kraken"][0]["unrealized_pl"] == 10.0

    kraken.bid = None
    missing = ns["get_all_positions"](owner)
    assert missing["kraken"] == []


def test_no_fixed_fx_or_synthetic_market_fields_remain():
    source = ORCA_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    zero_market_fields = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "MarketOpportunity":
            continue
        for keyword in node.keywords:
            if keyword.arg not in {"price", "volume", "change_pct"}:
                continue
            if isinstance(keyword.value, ast.Constant) and keyword.value.value in {0, 0.0}:
                zero_market_fields.append((node.lineno, keyword.arg))

    assert "1.27" not in source
    assert "Create a synthetic opportunity object" not in source
    assert zero_market_fields == []


def test_orca_file_has_no_operational_real_data_contract_errors():
    findings = validator.scan_text_file(ORCA_PATH, ROOT)
    errors = [finding for finding in findings if finding.severity == "error"]
    assert errors == []
