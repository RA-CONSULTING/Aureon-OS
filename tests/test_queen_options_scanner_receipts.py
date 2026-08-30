from __future__ import annotations

import ast
import copy
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from aureon.queen import queen_options_scanner as scanner_module


NOW = 1_800_000_000.0


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
    def __init__(self, option_type="call"):
        expiration = (
            datetime.fromtimestamp(NOW, tz=timezone.utc) + timedelta(days=30)
        ).strftime("%Y-%m-%d")
        self.contract = SimpleNamespace(
            id=f"contract-{option_type}",
            symbol=f"AAPL-{option_type.upper()}-105",
            underlying_symbol="AAPL",
            option_type=option_type,
            tradable=True,
            status="active",
            strike_price=105.0 if option_type == "call" else 95.0,
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
        self.contract_calls = 0
        self.quote_calls = 0

    def get_contracts(self, **kwargs):
        self.contract_calls += 1
        assert kwargs["option_type"].value in {"call", "put"}
        return [{"contract": self.contract, "receipt": copy.deepcopy(self.contract_receipt)}]

    def get_quotes(self, symbols):
        self.quote_calls += 1
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
        "underlying-1", symbol="AAPL", price=100.0, bid=99.9, ask=100.1
    )


def _level():
    return _receipt(
        "level-1", account_id="account-1", trading_level=1
    )


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


def test_fresh_linked_receipts_preserve_equations_and_are_analysis_only():
    adapter = TrapOptionsAdapter("call")
    scanner = scanner_module.QueenOptionsScanner(client=adapter, clock=lambda: NOW)
    opportunities = scanner.scan_covered_calls(
        "AAPL",
        100.0,
        underlying_receipt=_underlying(),
        position_receipt=_position(),
        trading_level_receipt=_level(),
    )

    assert len(opportunities) == 1
    opportunity = opportunities[0]
    mid = 2.1
    premium = mid * 100
    collateral = 100.0 * 100
    expiration = datetime.strptime(
        adapter.contract.expiration_date, "%Y-%m-%d"
    ).replace(tzinfo=timezone.utc)
    days = (expiration - datetime.fromtimestamp(NOW, tz=timezone.utc)).days
    premium_score = min(1.0, (premium / collateral) * 10)
    spread_score = 0.5
    volume_score = 0.7
    theta_score = min(1.0, ((mid / days) / mid * 100) * 10)
    annualized = (1 + premium / collateral) ** (365 / days) - 1
    total = (
        premium_score * 0.35
        + spread_score * 0.25
        + volume_score * 0.20
        + theta_score * 0.20
    )
    assert opportunity.premium_score == pytest.approx(premium_score)
    assert opportunity.spread_score == spread_score
    assert opportunity.volume_score == volume_score
    assert opportunity.theta_score == pytest.approx(theta_score)
    assert opportunity.annualized_return == pytest.approx(annualized)
    assert opportunity.total_score == pytest.approx(total)
    assert opportunity.days_to_expiry == days
    assert opportunity.queen_confidence is None
    assert opportunity.truth_status == "real_derived"
    assert opportunity.generated_values is False
    assert opportunity.eligible_for_ranking is True
    assert opportunity.eligible_for_action is False
    assert opportunity.eligible_for_accounting is False
    assert opportunity.eligible_for_learning is False
    assert opportunity.source_receipt_ids == (
        "underlying-1",
        "level-1",
        "position-1",
        "contract-receipt-call",
        "quote-receipt-call",
    )
    assert scanner.last_scan_receipt["eligible_for_action"] is False
    assert adapter.contract_calls == 1
    assert adapter.quote_calls == 1


@pytest.mark.parametrize(
    "defect", ["raw_contract", "stale_quote", "generated_underlying", "broken_link"]
)
def test_incomplete_or_untrusted_receipt_chain_fails_closed(defect):
    adapter = TrapOptionsAdapter("call")
    underlying = _underlying()
    position = _position()
    if defect == "raw_contract":
        adapter.get_contracts = lambda **_kwargs: [adapter.contract]
    elif defect == "stale_quote":
        adapter.quote_receipt["source_timestamp"] = NOW - 61.0
    elif defect == "generated_underlying":
        underlying["generated_values"] = True
    else:
        position["underlying_receipt_id"] = "unrelated-receipt"

    scanner = scanner_module.QueenOptionsScanner(client=adapter, clock=lambda: NOW)
    assert scanner.scan_covered_calls(
        "AAPL",
        100.0,
        underlying_receipt=underlying,
        position_receipt=position,
        trading_level_receipt=_level(),
    ) == []
    receipt = scanner.last_scan_receipt
    assert receipt["truth_status"] == "no_data"
    assert receipt["source_timestamp"] is None
    assert receipt["generated_values"] is False
    assert receipt["eligible_for_ranking"] is False
    assert receipt["eligible_for_action"] is False
    assert receipt["eligible_for_accounting"] is False
    assert receipt["eligible_for_learning"] is False
    assert not {
        "price", "bid", "ask", "premium", "confidence", "days_to_expiry"
    }.intersection(receipt)


def test_cash_chain_default_construction_cli_and_order_surface_are_inert(capsys):
    default_scanner = scanner_module.QueenOptionsScanner()
    assert default_scanner.client is None
    assert default_scanner.queen is None
    assert default_scanner.scan_covered_calls("AAPL", 100.0) == []
    assert scanner_module.scan_options("AAPL") == []
    assert scanner_module.main(["AAPL"]) == 2
    assert "No scan performed" in capsys.readouterr().out

    adapter = TrapOptionsAdapter("put")
    scanner = scanner_module.QueenOptionsScanner(client=adapter, clock=lambda: NOW)
    opportunities = scanner.scan_cash_secured_puts(
        "AAPL",
        100.0,
        underlying_receipt=_underlying(),
        capital_receipt=_capital(),
        trading_level_receipt=_level(),
    )
    assert len(opportunities) == 1
    assert opportunities[0].strategy == "cash_secured_put"
    assert opportunities[0].eligible_for_action is False

    source_path = Path(scanner_module.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    called_attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert not called_attributes.intersection(
        {"place_order", "submit_order", "execute_order", "exercise", "close_position"}
    )
    assert math.isfinite(float(opportunities[0].total_score))
