"""Gary's 9 Nov rule: the unified kill chain must not close a Capital deal he opened.

``_scan_capital`` used to hand every Capital position to ``_evaluate_and_kill``,
and ``_close_capital`` issued DELETE /positions/{id} once profit and the Dr.
Auris votes passed. These tests drive that path with fake clients only. They
do not import the kill-chain module, so exchange clients never load and no
.env file is read.
"""

from __future__ import annotations

import ast
import math
import time
from datetime import datetime
from pathlib import Path

import pytest

from aureon.exchanges.orca_capital_ownership import ADOPT_ENV

ROOT = Path(__file__).resolve().parents[1]
KILL_CHAINS = (
    "unified_margin_trader/unified_kill_chain.py",
    "aureon/trading/unified_kill_chain.py",
)

# Shaped like Capital's /positions reply for Gary's manual CN50 buy.
CN50_MANUAL = {
    "market": {"epic": "CN50", "bid": 13000.0, "offer": 13001.0},
    "position": {
        "dealId": "MANUAL-CN50",
        "dealReference": "REF-CN50",
        "upl": 87.0,
        "openLevel": 12000.0,
        "dealSize": 0.087,
        "direction": "BUY",
    },
}
ADOPTED = {
    "market": {"epic": "US100", "bid": 100.0, "offer": 100.2},
    "position": {
        "dealId": "ORCA-1",
        "dealReference": "REF-ORCA-1",
        "upl": 12.5,
        "openLevel": 100.0,
        "dealSize": 0.1,
        "direction": "BUY",
    },
}


class FakeCapital:
    """Records close attempts. No socket, no session, no .env."""

    def __init__(self, positions):
        self._positions = list(positions)
        self.closed: list = []
        self.deleted: list = []

    def get_positions(self):
        return list(self._positions)

    def close_position(self, deal_id):
        self.closed.append(deal_id)
        return {"success": True, "status": "submitted", "dealId": deal_id}

    def _request(self, method, path):
        self.deleted.append((method, path))
        return {"method": method, "path": path}


def _load_kill_chain(relative: str):
    """Exec only the receipt helpers and the Capital scan/close methods."""
    target = ROOT / relative
    tree = ast.parse(target.read_text(encoding="utf-8"), filename=str(target))
    helper_names = {
        "_finite_provider_number",
        "_parse_provider_timestamp",
        "_valid_provider_identifier",
        "_first_present",
        "_provider_order_identifier",
        "_provider_trade_identifiers",
        "_execution_result",
        "_normalized_venue",
        "_normalized_symbol",
        "_same_observed_number",
        "_classify_action_evidence",
        "_classify_terminal_fill_receipt",
    }
    method_names = {"_scan_capital", "_evaluate_and_kill", "_close_capital"}
    selected = []
    for node in tree.body:
        is_constant = isinstance(node, ast.Assign) and any(
            isinstance(target_name, ast.Name)
            and target_name.id.startswith(("EXECUTION_RECEIPT_", "ACTION_EVIDENCE_"))
            for target_name in node.targets
        )
        is_helper = (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name in helper_names
        )
        if is_constant or is_helper:
            selected.append(node)
        elif isinstance(node, ast.ClassDef) and node.name == "UnifiedKillChain":
            scoped = ast.ClassDef(
                name=node.name,
                bases=[],
                keywords=[],
                body=[
                    item
                    for item in node.body
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and item.name in method_names
                ],
                decorator_list=[],
                type_params=[],
            )
            selected.append(scoped)

    logs = []
    namespace = {
        "math": math,
        "time": time,
        "datetime": datetime,
        "log_queen": lambda message: logs.append(("queen", message)),
        "log_auris": lambda message: logs.append(("auris", message)),
        "log_sniper": lambda message: logs.append(("sniper", message)),
        "log_system": lambda message: logs.append(("system", message)),
        "log_warn": lambda message: logs.append(("warn", message)),
        "log_harmonic": lambda message: logs.append(("harmonic", message)),
    }
    module = ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[]))
    exec(compile(module, str(target), "exec"), namespace)
    namespace["_logs"] = logs
    return namespace


def _chain(relative: str, positions):
    namespace = _load_kill_chain(relative)
    chain = namespace["UnifiedKillChain"].__new__(namespace["UnifiedKillChain"])
    chain.capital = FakeCapital(positions)
    chain.harmonic_field = None
    chain._pending_reconciliations = {}
    chain._validate_with_dr_auris = lambda **kwargs: {
        "approved": True,
        "timestamp": "2026-11-09T12:00:00+00:00",
        "reasoning": "two provider-backed votes",
        "confidence": 0.91,
        "votes_for": 2,
    }
    return namespace, chain


def _action_receipts(now, *, symbol, position_id, quantity, pnl, entry_price, current_price):
    position_receipt_id = f"capital-position-receipt-{position_id}"
    position = {
        "data_status": "live",
        "truth_status": "real_observed",
        "generated_values": False,
        "eligible_for_action": True,
        "venue": "capital",
        "symbol": symbol,
        "source_id": "capital:positions",
        "source_timestamp": now,
        "received_at": now,
        "receipt_id": position_receipt_id,
        "position_id": position_id,
        "quantity": quantity,
    }
    opportunity = {
        "data_status": "live",
        "truth_status": "real_derived",
        "generated_values": False,
        "eligible_for_action": True,
        "venue": "capital",
        "symbol": symbol,
        "source_id": "aureon:unified_kill_chain",
        "source_timestamp": now,
        "received_at": now,
        "receipt_id": f"capital-opportunity-receipt-{position_id}",
        "position_receipt_id": position_receipt_id,
        "pnl": pnl,
        "entry_price": entry_price,
        "current_price": current_price,
    }
    return position, opportunity


def _kill_profitable(chain, *, symbol, deal_id, quantity, pnl, entry_price, current_price):
    """Profit, fresh receipts, and a unanimous vote: the path that closes."""
    now = time.time()
    position, opportunity = _action_receipts(
        now,
        symbol=symbol,
        position_id=deal_id,
        quantity=quantity,
        pnl=pnl,
        entry_price=entry_price,
        current_price=current_price,
    )
    return chain._evaluate_and_kill(
        "Capital",
        symbol,
        pnl,
        deal_id,
        quantity,
        chain.capital,
        chain._close_capital,
        entry_price,
        current_price,
        position_receipt=position,
        opportunity_receipt=opportunity,
        now=now,
    )


def _assert_nothing_closed(capital: FakeCapital):
    assert capital.closed == [], capital.closed
    assert capital.deleted == [], capital.deleted


@pytest.mark.parametrize("relative", KILL_CHAINS)
def test_manual_gary_deal_meeting_profit_and_vote_is_not_closed(monkeypatch, relative):
    monkeypatch.delenv(ADOPT_ENV, raising=False)
    namespace, chain = _chain(relative, [CN50_MANUAL])

    _kill_profitable(
        chain,
        symbol="CN50",
        deal_id="MANUAL-CN50",
        quantity=0.087,
        pnl=87.0,
        entry_price=12000.0,
        current_price=13000.0,
    )
    _assert_nothing_closed(chain.capital)

    evaluated = []
    real_evaluate = chain._evaluate_and_kill

    def spy(*args, **kwargs):
        evaluated.append(args)
        return real_evaluate(*args, **kwargs)

    chain._evaluate_and_kill = spy
    chain._scan_capital()
    assert evaluated == []
    _assert_nothing_closed(chain.capital)
    assert not any("BOOM" in message for _kind, message in namespace["_logs"])


@pytest.mark.parametrize("relative", KILL_CHAINS)
def test_allowlisted_capital_deal_is_closed(monkeypatch, relative):
    monkeypatch.setenv(ADOPT_ENV, "ORCA-1")
    _namespace, chain = _chain(relative, [ADOPTED])

    _kill_profitable(
        chain,
        symbol="US100",
        deal_id="ORCA-1",
        quantity=0.1,
        pnl=12.5,
        entry_price=100.0,
        current_price=225.0,
    )
    assert chain.capital.closed == ["ORCA-1"]
    assert chain.capital.deleted == []

    evaluated = []
    chain.capital.closed.clear()

    def spy(*args, **kwargs):
        evaluated.append(kwargs.get("position_id"))

    chain._evaluate_and_kill = spy
    chain._scan_capital()
    assert evaluated == ["ORCA-1"]


@pytest.mark.parametrize("relative", KILL_CHAINS)
def test_ownership_lookup_error_closes_nothing(monkeypatch, relative):
    monkeypatch.setenv(ADOPT_ENV, "ORCA-1")

    def explode(env=None):
        raise RuntimeError("ownership lookup failed")

    monkeypatch.setattr(
        "aureon.exchanges.orca_capital_ownership.adopted_deal_ids",
        explode,
    )
    namespace, chain = _chain(relative, [CN50_MANUAL, ADOPTED])

    _kill_profitable(
        chain,
        symbol="US100",
        deal_id="ORCA-1",
        quantity=0.1,
        pnl=12.5,
        entry_price=100.0,
        current_price=225.0,
    )
    _assert_nothing_closed(chain.capital)

    evaluated = []

    def spy(*args, **kwargs):
        evaluated.append(args)

    chain._evaluate_and_kill = spy
    chain._scan_capital()
    assert evaluated == []
    _assert_nothing_closed(chain.capital)
    assert any("could not be determined" in message for _kind, message in namespace["_logs"])
