from __future__ import annotations

import ast
import copy
import importlib.util
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from aureon.queen import queen_options_scanner as canonical


NOW = 1_800_000_000.0
ROOT = Path(__file__).resolve().parents[1]
LEGACY_PATH = (
    ROOT
    / "Kings_Accounting_Suite"
    / "aureon_systems"
    / "queen_options_scanner.py"
)


def _load_legacy_bridge():
    spec = importlib.util.spec_from_file_location(
        "kings_accounting_queen_options_bridge", LEGACY_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def _receipt(receipt_id: str, **fields):
    return {
        "source_id": "alpaca:test-adapter",
        "source_timestamp": NOW - 2.0,
        "received_at": _iso(NOW - 1.0),
        "receipt_id": receipt_id,
        "truth_status": "real_observed",
        "data_status": "live",
        "generated_values": False,
        **fields,
    }


class Quote:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.bid = 2.0
        self.ask = 2.2
        self.bid_size = 5
        self.ask_size = 7
        self.last_price = 2.1
        self.volume = 150
        self.timestamp = _iso(NOW - 2.0)

    @property
    def mid_price(self):
        return (self.bid + self.ask) / 2

    @property
    def spread_pct(self):
        return ((self.ask - self.bid) / self.mid_price) * 100


class TrapOptionsAdapter:
    def __init__(self, option_type: str):
        expiration = (
            datetime.fromtimestamp(NOW, tz=timezone.utc) + timedelta(days=30)
        ).strftime("%Y-%m-%d")
        strike = 105.0 if option_type == "call" else 95.0
        self.contract = SimpleNamespace(
            id=f"contract-{option_type}",
            symbol=f"AAPL-{option_type.upper()}-{int(strike)}",
            underlying_symbol="AAPL",
            option_type=option_type,
            tradable=True,
            status="active",
            strike_price=strike,
            size=100,
            expiration_date=expiration,
        )
        self.quote = Quote(self.contract.symbol)
        self.contract_receipt = _receipt(
            f"contract-receipt-{option_type}",
            symbol=self.contract.symbol,
            underlying_receipt_id="underlying-1",
        )
        self.quote_receipt = _receipt(
            f"quote-receipt-{option_type}",
            symbol=self.contract.symbol,
            contract_receipt_id=self.contract_receipt["receipt_id"],
            underlying_receipt_id="underlying-1",
        )

    def get_contracts(self, **kwargs):
        assert kwargs["option_type"].value in {"call", "put"}
        return [
            {
                "contract": self.contract,
                "receipt": copy.deepcopy(self.contract_receipt),
            }
        ]

    def get_quotes(self, symbols):
        assert symbols == [self.contract.symbol]
        return {
            self.contract.symbol: {
                "quote": self.quote,
                "receipt": copy.deepcopy(self.quote_receipt),
            }
        }

    def __getattr__(self, name):
        if any(token in name.lower() for token in ("order", "execute", "exercise", "close")):
            raise AssertionError(f"forbidden action surface requested: {name}")
        raise AttributeError(name)


def _underlying():
    return _receipt(
        "underlying-1",
        symbol="AAPL",
        price=100.0,
        bid=99.9,
        ask=100.1,
    )


def _level():
    return _receipt("level-1", account_id="account-1", trading_level=1)


def _position():
    return _receipt(
        "position-1",
        account_id="account-1",
        symbol="AAPL",
        shares=100,
        trading_level_receipt_id="level-1",
        underlying_receipt_id="underlying-1",
    )


def _capital():
    return _receipt(
        "capital-1",
        account_id="account-1",
        currency="USD",
        available_cash=10_000.0,
        trading_level_receipt_id="level-1",
    )


def test_legacy_bridge_is_inert_and_exposes_only_the_canonical_contract(capsys):
    source = LEGACY_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert imported_modules <= {"typing", "aureon.queen.queen_options_scanner"}
    assert "get_options_client" not in source
    assert "get_alpaca_client" not in source
    called_attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert not called_attributes.intersection(
        {"place_order", "submit_order", "execute_order", "exercise", "close_position"}
    )

    legacy = _load_legacy_bridge()
    assert legacy.QueenOptionsScanner is canonical.QueenOptionsScanner
    assert legacy.OptionsOpportunity is canonical.OptionsOpportunity
    scanner = legacy.QueenOptionsScanner()
    assert scanner.client is None
    assert scanner.queen is None
    assert scanner.scan_covered_calls("AAPL", 100.0) == []
    assert legacy.scan_options("AAPL") == []
    assert legacy.main(["AAPL"]) == 2
    assert "No scan performed" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("option_type", "strategy"),
    (("call", "covered_call"), ("put", "cash_secured_put")),
)
def test_linked_receipts_preserve_equations_and_remain_analysis_only(
    option_type, strategy
):
    legacy = _load_legacy_bridge()
    adapter = TrapOptionsAdapter(option_type)
    scanner = legacy.QueenOptionsScanner(client=adapter, clock=lambda: NOW)
    if strategy == "covered_call":
        opportunities = scanner.scan_covered_calls(
            "AAPL",
            100.0,
            underlying_receipt=_underlying(),
            position_receipt=_position(),
            trading_level_receipt=_level(),
        )
    else:
        opportunities = scanner.scan_cash_secured_puts(
            "AAPL",
            100.0,
            underlying_receipt=_underlying(),
            capital_receipt=_capital(),
            trading_level_receipt=_level(),
        )

    assert len(opportunities) == 1
    opportunity = opportunities[0]
    mid = 2.1
    premium = mid * 100
    collateral = 100.0 * 100 if strategy == "covered_call" else 95.0 * 100
    expiration = datetime.strptime(
        adapter.contract.expiration_date, "%Y-%m-%d"
    ).replace(tzinfo=timezone.utc)
    days = (expiration - datetime.fromtimestamp(NOW, tz=timezone.utc)).days
    expected_annualized = (1 + premium / collateral) ** (365 / days) - 1
    expected_theta = min(1.0, ((mid / days) / mid * 100) * 10)
    assert opportunity.premium_score == pytest.approx(
        min(1.0, (premium / collateral) * 10)
    )
    assert opportunity.spread_score == 0.5
    assert opportunity.volume_score == 0.7
    assert opportunity.theta_score == pytest.approx(expected_theta)
    assert opportunity.annualized_return == pytest.approx(expected_annualized)
    assert opportunity.days_to_expiry == days
    assert opportunity.queen_confidence is None
    assert opportunity.truth_status == "real_derived"
    assert opportunity.generated_values is False
    assert opportunity.eligible_for_ranking is True
    assert opportunity.eligible_for_action is False
    assert opportunity.eligible_for_accounting is False
    assert opportunity.eligible_for_learning is False
    assert scanner.last_scan_receipt["eligible_for_action"] is False

    adapter.quote_receipt["source_timestamp"] = NOW - 61.0
    stale = legacy.QueenOptionsScanner(client=adapter, clock=lambda: NOW)
    if strategy == "covered_call":
        result = stale.scan_covered_calls(
            "AAPL",
            100.0,
            underlying_receipt=_underlying(),
            position_receipt=_position(),
            trading_level_receipt=_level(),
        )
    else:
        result = stale.scan_cash_secured_puts(
            "AAPL",
            100.0,
            underlying_receipt=_underlying(),
            capital_receipt=_capital(),
            trading_level_receipt=_level(),
        )
    assert result == []
    assert stale.last_scan_receipt["truth_status"] == "no_data"
    assert stale.last_scan_receipt["source_timestamp"] is None
    assert stale.last_scan_receipt["eligible_for_ranking"] is False
    assert stale.last_scan_receipt["eligible_for_action"] is False
    assert stale.last_scan_receipt["eligible_for_accounting"] is False
    assert stale.last_scan_receipt["eligible_for_learning"] is False
    assert math.isfinite(float(opportunity.total_score))
