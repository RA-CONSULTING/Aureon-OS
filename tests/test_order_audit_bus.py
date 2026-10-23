"""Order attempts from each engine are written and published on the circulation bus."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
ORDER_CALLS = {
    "place_market_order",
    "place_order",
    "place_margin_order",
    "place_trailing_stop_order",
    "place_take_profit_order",
    "place_working_order",
    "close_position",
    "create_order",
    "add_order",
    "convert_crypto",
    "execute_trade",
}


def _functions_missing_audit(relative: str) -> list[str]:
    tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
    missing: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            calls = [
                sub.func.attr
                for sub in ast.walk(item)
                if isinstance(sub, ast.Call)
                and isinstance(sub.func, ast.Attribute)
                and sub.func.attr in ORDER_CALLS
            ]
            noted = any(
                isinstance(sub, ast.Call)
                and isinstance(sub.func, ast.Attribute)
                and sub.func.attr == "_note_order_attempt"
                for sub in ast.walk(item)
            )
            if calls and not noted:
                missing.append(item.name)
    return missing


def _bus_events():
    from aureon.core.aureon_thought_bus import get_thought_bus

    thoughts = get_thought_bus().recall(topic_prefix="organism.circulation", limit=400)
    return [
        item["payload"]
        for item in thoughts
        if isinstance(item.get("payload"), dict) and item["payload"].get("kind") == "autonomy_audit"
    ]


def _assert_published(tmp_path: Path, operation: str, exchange: str) -> None:
    from aureon.core.organism_circulation import consumed_audits

    text = (tmp_path / "audit.jsonl").read_text(encoding="utf-8")
    rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    match = [
        row
        for row in rows
        if row.get("event") == "order" and row.get("operation") == operation and row.get("exchange") == exchange
    ]
    assert match, rows
    assert all(row.get("order_placed_by_audit") is False for row in match)
    payloads = [
        item
        for item in _bus_events()
        if item.get("event") == "order" and item.get("operation") == operation and item.get("exchange") == exchange
    ]
    assert payloads
    for loop in ("metacognition", "self_repair"):
        consumed = {item["event"] for item in consumed_audits(loop)}
        assert "order" in consumed


@pytest.fixture
def audit_bus(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from aureon.core.organism_circulation import start_organism_circulation, stop_organism_circulation

    monkeypatch.setenv("AUREON_AUTONOMY_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv("AUREON_ORGANISM_STATE", str(tmp_path / "organism-state"))
    monkeypatch.setenv("AUREON_ORGANISM_HTTP_PORT", "0")
    monkeypatch.setenv("AUREON_OFFLINE", "1")
    stop_organism_circulation()
    started = start_organism_circulation(port=0)
    assert started["started"] is True
    try:
        yield
    finally:
        stop_organism_circulation()


def test_unified_market_trader_order_reaches_the_bus(audit_bus, tmp_path: Path) -> None:
    from aureon.exchanges.unified_market_trader import UnifiedMarketTrader

    assert _functions_missing_audit("aureon/exchanges/unified_market_trader.py") == []

    class Client:
        def get_pair_leverage(self, symbol):
            return {"leverage_buy": [2], "leverage_sell": [2], "pair": symbol}

        def place_margin_order(self, symbol, side, quantity, leverage=2, **kwargs):
            return {"status": "accepted", "symbol": symbol, "side": side, "reason": "stub"}

    trader = UnifiedMarketTrader.__new__(UnifiedMarketTrader)
    trader.dry_run = False
    client = Client()
    trader._runtime_real_orders_allowed = lambda: True
    trader._kraken_spot_client = lambda: client
    trader._fresh_route_price_receipt = lambda _venue, _symbol: {"status": "live", "price": 100.0}
    trader._governed_client_for = lambda _exchange: client
    result = trader._execute_kraken_margin_route("BUY", "XBTUSD", 50.0)
    assert result["submitted"] is False or result["ok"] is True or result.get("status")
    _assert_published(tmp_path, "place_margin_order", "kraken")


def test_capital_cfd_trader_order_reaches_the_bus(audit_bus, tmp_path: Path) -> None:
    from aureon.exchanges.capital_cfd_trader import CapitalCFDTrader

    assert _functions_missing_audit("aureon/exchanges/capital_cfd_trader.py") == []

    class Client:
        def place_working_order(self, symbol, direction, size, level, order_type="LIMIT", **kwargs):
            return {"status": "working", "symbol": symbol, "direction": direction, "reason": "stub"}

    trader = CapitalCFDTrader.__new__(CapitalCFDTrader)
    trader.client = Client()
    submit = trader._submit_capital_pending_order(
        {
            "symbol": "BTCUSD",
            "direction": "BUY",
            "size": 0.1,
            "level": 100.0,
            "order_type": "LIMIT",
            "broker_exit_controls": {},
        },
        {"can_submit_pending_orders": True},
    )
    assert submit["ok"] is True
    _assert_published(tmp_path, "place_working_order", "capital")


def test_micro_profit_labyrinth_order_reaches_the_bus(audit_bus, tmp_path: Path) -> None:
    from aureon.trading.micro_profit_labyrinth import MicroProfitLabyrinth

    assert _functions_missing_audit("aureon/trading/micro_profit_labyrinth.py") == []

    class Client:
        def get_balance(self):
            return {"BTC": 2.0}

        def place_market_order(self, symbol, side, quantity=None, **kwargs):
            return {"rejected": True, "reason": "stub_hold", "symbol": symbol, "side": side}

    labyrinth = MicroProfitLabyrinth.__new__(MicroProfitLabyrinth)
    labyrinth.kraken_client = Client()
    labyrinth._mark_not_submitted = lambda *_args, **_kwargs: None
    opp = SimpleNamespace(from_asset="BTC", to_asset="USD", from_amount=0.1)
    assert labyrinth._execute_on_exchange("kraken", opp, 0.0, {}) is False
    _assert_published(tmp_path, "place_market_order", "kraken")
