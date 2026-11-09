"""ORCA kill chain: closes go through the guarded client and boundary refusals
are non-fatal HOLDs. Mocked clients only; no network."""
import importlib
from unittest import mock

import pytest

kc = importlib.import_module("aureon_radar.bots.orca_unified_kill_chain")
from aureon.governance.economic_boundary import EconomicGovernanceBlocked


def _chain():
    chain = kc.UnifiedKillChain.__new__(kc.UnifiedKillChain)
    return chain


def _target(client, exchange="capital"):
    return {"symbol": "CN50", "exchange": exchange, "id": "deal-1", "qty": 0.087,
            "pnl": 0.5, "client": client}


@pytest.fixture(autouse=True)
def _fast(monkeypatch):
    monkeypatch.setattr(kc.time, "sleep", lambda *_: None)
    monkeypatch.setattr(kc.sys if hasattr(kc, "sys") else __import__("sys"), "stdin", None)


def _client():
    c = mock.Mock()
    c.get_ticker.return_value = {"price": 10.0, "bid": 9.9, "ask": 10.1}
    return c


def test_capital_close_uses_guarded_close_position_not_raw_request():
    c = _client()
    c.close_position.return_value = {"status": "submitted", "dealReference": "ref"}
    _chain().execute_kill_chain_safe(_target(c))
    c.close_position.assert_called_once_with("deal-1")
    c._request.assert_not_called()


def test_boundary_refusal_is_hold_and_not_fatal():
    c = _client()
    c.close_position.side_effect = EconomicGovernanceBlocked(
        "boundary_issued_economic_transport_context_required")
    chain = _chain()
    chain.execute_kill_chain_safe(_target(c))  # must not raise
    key = chain._target_key(_target(c))
    assert chain.governance_holds[key][1] == "boundary_issued_economic_transport_context_required"
    # held target is not retried inside the hold window
    chain.execute_kill_chain_safe(_target(c))
    assert c.close_position.call_count == 1


def test_spot_sell_refusal_and_other_errors_not_fatal():
    c = _client()
    c.place_market_order.side_effect = EconomicGovernanceBlocked("x")
    chain = _chain()
    chain.execute_kill_chain_safe(_target(c, "kraken"))
    assert "kraken::deal-1" in chain.governance_holds
    c2 = _client()
    c2.get_ticker.side_effect = RuntimeError("boom")
    chain.execute_kill_chain_safe(_target(c2, "binance"))  # must not raise


def test_negative_pnl_queen_declines_headless():
    c = _client()
    t = _target(c); t["pnl"] = -1.0
    _chain().execute_kill_chain_safe(t)
    c.close_position.assert_not_called()
