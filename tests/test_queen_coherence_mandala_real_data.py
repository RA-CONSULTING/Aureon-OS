from __future__ import annotations

import ast
import time
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aureon" / "queen" / "queen_coherence_mandala.py"


def _load_isolated_module():
    tree = ast.parse(TARGET.read_text(encoding="utf-8"), filename=str(TARGET))
    tree.body = [
        node
        for node in tree.body
        if not (
            isinstance(node, ast.ImportFrom)
            and node.module == "aureon.core.aureon_baton_link"
        )
        and not (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "_baton_link"
        )
    ]
    module = types.ModuleType("_isolated_queen_coherence_mandala")
    module.__file__ = str(TARGET)
    exec(compile(tree, str(TARGET), "exec"), module.__dict__)
    return module


def _receipt(index: int, now: float) -> dict:
    source_timestamp = now - 20.0 + index
    return {
        "status": "live",
        "data_status": "live",
        "truth_status": "real_observed",
        "symbol": "BTCUSDC",
        "price": 50_000.0 + index,
        "volume": 1_000_000.0 + index,
        "change_24h": 1.25,
        "source_id": "provider:test-market",
        "source_timestamp": source_timestamp,
        "received_at": source_timestamp + 0.01,
        "receipt_id": f"provider-receipt-{index}",
        "generated_values": False,
        "eligible_for_action": True,
        "eligible_for_learning": True,
    }


def test_missing_stale_and_duplicate_receipts_cannot_produce_coherence():
    module = _load_isolated_module()
    adapter = module.MarketCoherenceAdapter()
    system = module.QueenCoherenceSystem(dim=3, alpha=0.15)

    initial = system.get_state()
    assert initial["status"] == "no_data"
    assert initial["coherence_magnitude"] is None
    assert initial["eligible_for_action"] is False
    assert initial["eligible_for_accounting"] is False
    assert initial["eligible_for_learning"] is False

    now = time.time()
    stale = _receipt(0, now - module.MAX_MARKET_RECEIPT_AGE_SECONDS - 10.0)
    assert adapter.process(stale)["status"] == "no_data"
    assert adapter.price_history == []

    for index in range(adapter.MIN_OBSERVATIONS - 1):
        result = adapter.process(_receipt(index, now))
        assert result["status"] == "no_data"

    final_receipt = _receipt(adapter.MIN_OBSERVATIONS - 1, now)
    derived = adapter.process(final_receipt)
    assert derived["status"] == "live"
    assert derived["truth_status"] == "real_derived"
    assert derived["generated_values"] is False
    assert derived["receipt_id"] == final_receipt["receipt_id"]

    history_length = len(adapter.price_history)
    duplicate = adapter.process(final_receipt)
    assert duplicate["status"] == "no_data"
    assert len(adapter.price_history) == history_length

    state = system.update_from_market(derived)
    assert state["status"] == "live"
    assert state["source_timestamp"] == final_receipt["source_timestamp"]
    assert state["receipt_id"] == final_receipt["receipt_id"]
    assert state["eligible_for_accounting"] is False


def test_module_has_no_order_submission_surface():
    tree = ast.parse(TARGET.read_text(encoding="utf-8"), filename=str(TARGET))
    forbidden = {
        "place_order",
        "place_market_order",
        "submit_order",
        "create_order",
    }
    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert forbidden.isdisjoint(called)
