from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest

from aureon.utils.get_first_winner import (
    WinningOpportunity,
    check_balances,
    execute_winning_trade,
    find_best_winner,
    get_live_opportunities,
)
from scripts.validation.validate_real_data_contract import scan_text_file


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aureon" / "utils" / "get_first_winner.py"


class _Kraken:
    def __init__(self) -> None:
        self.tickers: list[dict[str, Any]] = []
        self.balances: dict[str, Any] = {"USD": "100"}
        self.submission: dict[str, Any] = {
            "status": "pending_reconciliation",
            "data_status": "pending_reconciliation",
            "orderId": "K-1",
            "generated_values": False,
        }
        self.terminal: dict[str, Any] = dict(self.submission)
        self.order_calls: list[dict[str, Any]] = []

    def get_24h_tickers(self) -> list[dict[str, Any]]:
        return list(self.tickers)

    def get_account_balance(self) -> dict[str, Any]:
        return dict(self.balances)

    def place_market_order(self, **kwargs: Any) -> dict[str, Any]:
        self.order_calls.append(dict(kwargs))
        return dict(self.submission)

    def get_order_status(self, order_id: str) -> dict[str, Any]:
        assert order_id == "K-1"
        return dict(self.terminal)


def _ticker(symbol: str = "ETHUSD", *, age: float = 0.0) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "lastPrice": "50",
        "priceChangePercent": "2",
        "quoteVolume": "250000",
        "source_id": f"kraken:ticker:{symbol}",
        "source_timestamp": time.time() - age,
        "truth_status": "real_derived",
        "generated_values": False,
    }


def _opportunity(symbol: str = "ETHUSD") -> WinningOpportunity:
    return WinningOpportunity(
        symbol=symbol,
        exchange="kraken",
        current_price=50.0,
        momentum=2.0,
        score=3.0,
        reason="observed momentum",
        source_id=f"kraken:ticker:{symbol}",
        source_timestamp=time.time(),
    )


def test_import_source_has_no_runtime_baton_stdout_or_environment_mutation() -> None:
    source = TARGET.read_text(encoding="utf-8")
    assert "_baton_link(__name__)" not in source
    assert "sys.stdout =" not in source
    assert "os.environ" not in source


def test_only_complete_fresh_quotes_become_opportunities() -> None:
    client = _Kraken()
    stale = _ticker("BTCUSD", age=1000)
    incomplete = _ticker("SOLUSD")
    incomplete.pop("quoteVolume")
    client.tickers = [stale, incomplete, _ticker("ETHUSD")]

    opportunities = get_live_opportunities(client)

    assert [item.symbol for item in opportunities] == ["ETHUSD"]
    assert opportunities[0].source_timestamp <= time.time()
    assert opportunities[0].generated_values is False


def test_balance_selection_requires_exact_quote_currency() -> None:
    client = _Kraken()
    receipt = check_balances(client)

    assert receipt["data_status"] == "live"
    assert find_best_winner([_opportunity("ETHUSDC")], receipt) is None
    assert find_best_winner([_opportunity("ETHUSD")], receipt) is not None

    client.balances = {"USD": "not-a-number"}
    malformed = check_balances(client)
    assert malformed["data_status"] == "no_data"
    assert malformed["balances"] is None


def test_dry_run_is_not_submitted_and_persists_nothing(tmp_path: Path) -> None:
    client = _Kraken()
    target = tmp_path / "position.json"

    receipt = execute_winning_trade(
        client,
        _opportunity(),
        100.0,
        dry_run=True,
        position_path=target,
    )

    assert receipt["status"] == "NOT_SUBMITTED"
    assert receipt["position_persisted"] is False
    assert client.order_calls == []
    assert not target.exists()


def test_acknowledgement_only_is_pending_and_persists_nothing(
    tmp_path: Path,
) -> None:
    client = _Kraken()
    target = tmp_path / "position.json"

    receipt = execute_winning_trade(
        client,
        _opportunity(),
        100.0,
        dry_run=False,
        position_path=target,
    )

    assert receipt["status"] == "PENDING_RECONCILIATION"
    assert receipt["position_persisted"] is False
    assert len(client.order_calls) == 1
    assert not target.exists()


def test_terminal_fill_alone_persists_exact_provider_position(
    tmp_path: Path,
) -> None:
    client = _Kraken()
    provider_time = time.time()
    client.terminal = {
        "status": "FILLED",
        "data_status": "live",
        "truth_status": "real_observed",
        "side": "BUY",
        "orderId": "K-1",
        "source_id": "kraken:order:K-1",
        "provider_timestamp": provider_time,
        "executedQty": "1",
        "filled_avg_price": "50",
        "cummulativeQuoteQty": "50",
        "fee": "0.10",
        "fee_asset": "USD",
        "fill_receipt_complete": True,
        "eligible_for_accounting": True,
        "generated_values": False,
    }
    target = tmp_path / "position.json"

    receipt = execute_winning_trade(
        client,
        _opportunity(),
        100.0,
        dry_run=False,
        position_path=target,
    )
    persisted = json.loads(target.read_text(encoding="utf-8"))

    assert receipt["status"] == "FILLED"
    assert receipt["position_persisted"] is True
    assert persisted["executed_qty"] == pytest.approx(1.0)
    assert persisted["average_fill_price"] == pytest.approx(50.0)
    assert persisted["fees_by_asset"] == {"USD": pytest.approx(0.10)}
    assert persisted["source_timestamp"] == pytest.approx(provider_time)
    for forbidden in ("pnl", "profit", "target_profit", "learning"):
        assert forbidden not in persisted


def test_scoped_runtime_file_has_no_hardened_validator_findings() -> None:
    assert scan_text_file(TARGET, ROOT) == []
