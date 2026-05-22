from __future__ import annotations

from unittest.mock import patch

from aureon.exchanges import capital_cfd_trader as trader_mod
from aureon.exchanges.capital_cfd_trader import CapitalCFDTrader


class _ClientStub:
    session_start_time = 0.0
    _rate_limit_until = 0.0


def test_capital_record_order_lifecycle_enriches_live_proof_fields():
    trader = CapitalCFDTrader.__new__(CapitalCFDTrader)
    trader.client = _ClientStub()
    captured = {}

    def fake_append(*args, **kwargs):
        captured.update(kwargs)

    with patch.object(trader_mod, "append_order_lifecycle_event", side_effect=fake_append):
        trader._record_order_lifecycle(
            "order_submitted",
            "order_submitted",
            "life-capital-1",
            candidate_id="cand-capital-1",
            intent_id="intent-capital-1",
            route_key="capital:cfd:GOLD:BUY",
            venue="capital",
            symbol="GOLD",
            side="BUY",
            deal_reference="DR-1",
        )

    assert captured.get("event_type") == "order_submitted"
    assert captured.get("status") == "order_submitted"
    assert captured.get("lifecycle_id") == "life-capital-1"
    assert captured.get("proof_mode") == "live_runtime"
    assert captured.get("authority_mode") == "runtime_gated_executor_path"
    assert captured.get("no_trading_gate_bypass") is True
    assert captured.get("publisher_owner") == "capital_cfd_trader._record_order_lifecycle"
    assert captured.get("verification_source") == "capital_cfd_trader"
    assert str(captured.get("rate_limit_family", "")).startswith("capital_")
    assert captured.get("api_budget_source") == "capital_cfd_trader.session_guard"
