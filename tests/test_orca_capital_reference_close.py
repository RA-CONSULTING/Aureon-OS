"""A reference-only Capital adoption closes by the confirmed OPENED dealId.

Scan adopts dealId or dealReference. The close must not send the reference.
GET /confirms/{ref} (affectedDeals OPENED) supplies the dealId. A missing
or REJECTED confirm does not close. Offline fakes only; no network.
"""
import importlib
import importlib.util
import json
from pathlib import Path
from unittest import mock

import pytest

from aureon.exchanges.orca_capital_ownership import (
    ADOPT_ENV,
    capital_close_deal_id,
    resolve_capital_close_id,
)

radar_kc = importlib.import_module("aureon_radar.bots.orca_unified_kill_chain")
aureon_kc = importlib.import_module("aureon.bots.orca_unified_kill_chain")


def _client(confirm):
    client = mock.Mock()
    client.get_ticker.return_value = {"price": 10.0, "bid": 9.9, "ask": 10.1}
    client.confirm_order.side_effect = confirm
    client.close_position.return_value = {"status": "submitted"}
    return client


def _target(client, deal_id="D-REAL", ref="o_REF"):
    return {
        "symbol": "US100",
        "exchange": "capital",
        "id": deal_id,
        "type": "CFD",
        "qty": 0.1,
        "pnl": 1.0,
        "client": client,
        "deal_reference": ref,
        "raw": {
            "position": {
                "dealId": deal_id,
                "dealReference": ref,
                "size": 0.1,
                "upl": 1.0,
            }
        },
    }


def _opened(ref="o_REF", deal_id="D-REAL"):
    return {
        "dealReference": ref,
        "dealStatus": "ACCEPTED",
        "affectedDeals": [
            {"dealId": deal_id, "status": "OPENED"},
            {"dealId": "D-OLD", "status": "CLOSED"},
        ],
    }


@pytest.fixture(autouse=True)
def _fast(monkeypatch):
    monkeypatch.setattr(radar_kc.time, "sleep", lambda *_a: None)
    monkeypatch.setattr(aureon_kc.time, "sleep", lambda *_a: None)
    monkeypatch.setenv(ADOPT_ENV, "o_REF")


def test_reference_with_opened_deal_closes_on_radar():
    client = _client(lambda ref: _opened(ref))
    radar = radar_kc.UnifiedKillChain.__new__(radar_kc.UnifiedKillChain)
    radar.execute_kill_chain_safe(_target(client))
    client.close_position.assert_called_once_with("D-REAL")
    client.confirm_order.assert_called_once_with("o_REF")

    client = _client(lambda ref: _opened(ref))
    aureon = aureon_kc.UnifiedKillChain.__new__(aureon_kc.UnifiedKillChain)
    aureon.execution_state_path = None
    aureon.execution_enabled = True
    refused = aureon.execute_kill_chain(_target(client))
    assert refused["reason"] == "execution_state_path_required"
    client.close_position.assert_not_called()
    client.confirm_order.assert_not_called()


def test_stored_receipt_is_not_a_reading_and_does_not_close():
    client = _client(lambda _ref: {"error": "404"})
    target = _target(client)
    target["confirmation"] = _opened(deal_id="D-STALE")
    chain = radar_kc.UnifiedKillChain.__new__(radar_kc.UnifiedKillChain)
    chain.execute_kill_chain_safe(target)
    client.close_position.assert_not_called()
    client.confirm_order.assert_called_once_with("o_REF")


def test_aureon_capital_close_stays_behind_execution_gate():
    client = _client(lambda ref: _opened(ref))
    chain = aureon_kc.UnifiedKillChain.__new__(aureon_kc.UnifiedKillChain)
    chain.execution_state_path = None
    chain.execution_enabled = False
    result = chain.execute_kill_chain(_target(client))
    assert result["reason"] == "execution_state_path_required"
    client.close_position.assert_not_called()
    client.confirm_order.assert_not_called()


def test_missing_or_rejected_confirm_does_not_close():
    payloads = (
        {"error": "404"},
        {
            "dealReference": "o_REF",
            "dealStatus": "REJECTED",
            "dealId": "D-REJ",
            "affectedDeals": [],
        },
        None,
    )
    for payload in payloads:
        client = _client(lambda _ref, payload=payload: payload)
        chain = radar_kc.UnifiedKillChain.__new__(radar_kc.UnifiedKillChain)
        chain.execute_kill_chain_safe(_target(client))
        client.close_position.assert_not_called()
        aureon = aureon_kc.UnifiedKillChain.__new__(aureon_kc.UnifiedKillChain)
        aureon.execution_state_path = None
        aureon.execution_enabled = True
        aureon.execute_kill_chain(_target(client))
        client.close_position.assert_not_called()


def _both():
    return (
        radar_kc.UnifiedKillChain.__new__(radar_kc.UnifiedKillChain),
        aureon_kc.UnifiedKillChain.__new__(aureon_kc.UnifiedKillChain),
    )


def test_recorded_confirmation_on_an_unallowlisted_reference_never_closes_gary():
    """Dropping `ref not in allow` must not close D-GARY from a stored confirm."""
    recorded = _opened(ref="o_GARY", deal_id="D-GARY")
    client = _client(lambda ref: recorded)
    target = _target(client, deal_id="D-GARY", ref="o_GARY")
    target["confirmation"] = recorded
    allow = set()
    assert capital_close_deal_id(target, allow, recorded) is None
    reads = []
    assert (
        resolve_capital_close_id(
            target, allow, lambda ref: reads.append(ref) or recorded
        )
        is None
    )
    assert reads == []
    for chain in _both():
        assert chain._capital_close_deal_id(target) is None
    radar_kc.UnifiedKillChain.__new__(
        radar_kc.UnifiedKillChain
    ).execute_kill_chain_safe(target)
    client.close_position.assert_not_called()
    aureon = aureon_kc.UnifiedKillChain.__new__(aureon_kc.UnifiedKillChain)
    aureon.execution_state_path = None
    aureon.execute_kill_chain(target)
    client.close_position.assert_not_called()


def test_opened_deal_must_match_the_position_deal():
    """Dropping `position_deal != opened` must not close the other OPENED id."""
    client = _client(lambda ref: _opened(ref, "D-OTHER"))
    target = _target(client, deal_id="D-REAL", ref="o_REF")
    allow = {"o_REF"}
    assert capital_close_deal_id(target, allow, _opened("o_REF", "D-OTHER")) is None
    for chain in _both():
        assert chain._capital_close_deal_id(target) is None
    radar_kc.UnifiedKillChain.__new__(
        radar_kc.UnifiedKillChain
    ).execute_kill_chain_safe(target)
    client.close_position.assert_not_called()


def test_two_opened_rows_are_refused():
    """More than one OPENED row is refused. The first row does not win."""
    payload = {
        "dealReference": "o_REF",
        "dealStatus": "ACCEPTED",
        "affectedDeals": [
            {"dealId": "D-FIRST", "status": "OPENED"},
            {"dealId": "D-SECOND", "status": "OPENED"},
        ],
    }
    client = _client(lambda ref: payload)
    target = _target(client, deal_id="o_REF", ref="o_REF")
    assert capital_close_deal_id(target, {"o_REF"}, payload) is None
    for chain in _both():
        assert chain._capital_close_deal_id(target) is None
    radar_kc.UnifiedKillChain.__new__(
        radar_kc.UnifiedKillChain
    ).execute_kill_chain_safe(target)
    client.close_position.assert_not_called()


def test_close_id_is_not_the_reference():
    """An id equal to the reference is not the close id. The OPENED deal is."""
    client = _client(lambda ref: _opened(ref, "D-REAL"))
    target = _target(client, deal_id="o_REF", ref="o_REF")
    assert capital_close_deal_id(target, {"o_REF"}, _opened()) == "D-REAL"
    for chain in _both():
        assert chain._capital_close_deal_id(target) == "D-REAL"
    radar_kc.UnifiedKillChain.__new__(
        radar_kc.UnifiedKillChain
    ).execute_kill_chain_safe(target)
    client.close_position.assert_called_once_with("D-REAL")


def test_unknown_is_not_a_close_id(monkeypatch):
    """`unknown` is not a deal id, even when that word is on the allowlist."""
    monkeypatch.setenv(ADOPT_ENV, "unknown")
    payload = _opened("unknown", "D-GARY")
    client = _client(lambda ref: payload)
    target = _target(client, deal_id="unknown", ref="unknown")
    assert capital_close_deal_id(target, {"unknown"}, payload) is None
    for chain in _both():
        assert chain._capital_close_deal_id(target) is None
    radar_kc.UnifiedKillChain.__new__(
        radar_kc.UnifiedKillChain
    ).execute_kill_chain_safe(target)
    client.close_position.assert_not_called()
    client.confirm_order.assert_not_called()


def test_unallowlisted_reference_does_not_confirm(monkeypatch):
    """A reference that is not on the allowlist does not GET /confirms."""
    monkeypatch.setenv(ADOPT_ENV, "OTHER")
    client = _client(lambda ref: _opened(ref, "D-GARY"))
    target = _target(client, deal_id="o_REF", ref="o_REF")
    reads = []
    assert (
        resolve_capital_close_id(
            target,
            {"OTHER"},
            lambda ref: reads.append(ref) or _opened(ref, "D-GARY"),
        )
        is None
    )
    assert reads == []
    for chain in _both():
        assert chain._capital_close_deal_id(target) is None
    assert client.confirm_order.call_count == 0
    radar_kc.UnifiedKillChain.__new__(
        radar_kc.UnifiedKillChain
    ).execute_kill_chain_safe(target)
    client.close_position.assert_not_called()
    assert client.confirm_order.call_count == 0


def _receipt_helpers():
    path = Path(__file__).with_name("test_orca_unified_kill_chain_receipts.py")
    spec = importlib.util.spec_from_file_location("orca_receipt_helpers", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _as_capital(node):
    if isinstance(node, dict):
        return {key: _as_capital(value) for key, value in node.items()}
    if isinstance(node, list):
        return [_as_capital(value) for value in node]
    if node == "kraken":
        return "capital"
    return node


def test_capital_receipt_close_uses_the_lock_and_does_not_repeat(
    tmp_path, monkeypatch
):
    """Capital CFD close is the receipt path: lock, one submit, no second close.

    execution_enabled must be the boolean True. 'yes' and 1 do not submit.
    """
    helpers = _receipt_helpers()
    now = 1_800_000_000.0
    client = _client(lambda ref: _opened(ref))
    target = _as_capital(
        helpers._target(now, intent_id="intent-cap-1", position_id="D-REAL")
    )
    target["type"] = "CFD"
    target["client"] = client
    terminal = _as_capital(
        helpers._terminal(
            now,
            receipt_id="terminal-cap-1",
            order_id="provider-order-1",
            trade_id="provider-trade-1",
        )
    )
    adapter = helpers._Adapter(
        submissions=[
            _as_capital(
                helpers._ack(now, order_id="provider-order-1", status="ACCEPTED")
            )
        ],
        readbacks=[
            _as_capital(
                helpers._ack(
                    now, order_id="provider-order-1", status="PARTIALLY_FILLED"
                )
            ),
            terminal,
        ],
    )
    entered = []
    real_lock = aureon_kc._execution_state_lock

    def _locked(path):
        entered.append(path)
        return real_lock(path)

    monkeypatch.setattr(aureon_kc, "_execution_state_lock", _locked)

    def _chain(name, enabled):
        chain = aureon_kc.UnifiedKillChain.__new__(aureon_kc.UnifiedKillChain)
        chain.execution_state_path = tmp_path / name
        chain.clock = lambda: now
        chain.execution_adapters = {"capital": adapter}
        chain.execution_enabled = enabled
        chain.last_no_data = []
        chain.wins_executed = []
        chain.total_pnl = 0.0
        return chain

    for enabled in ("yes", 1, False):
        refused = _chain(f"gate-{enabled}", enabled).execute_kill_chain(target)
        assert refused["status"] == "not_submitted"
        assert refused["reason"] == "execution_enable_gate_required"
    assert adapter.submit_calls == []
    client.close_position.assert_not_called()

    state_path = tmp_path / "capital-receipt-state.json"
    chain = _chain("capital-receipt-state.json", True)
    entered.clear()
    acknowledged = chain.execute_kill_chain(target)
    assert acknowledged["status"] == "pending_reconciliation"
    assert len(adapter.submit_calls) == 1
    assert adapter.submit_calls[0]["position_id"] == "D-REAL"
    assert entered and entered[0] == state_path
    client.close_position.assert_not_called()

    partial = chain.execute_kill_chain(target)
    assert partial["status"] == "pending_reconciliation"
    assert len(adapter.submit_calls) == 1

    filled = chain.execute_kill_chain(target)
    assert filled["status"] == "filled"
    assert len(adapter.submit_calls) == 1
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["completed_actions"]["intent-cap-1"] == "terminal-cap-1"

    duplicate = chain.execute_kill_chain(target)
    assert duplicate["status"] == "already_committed"
    assert duplicate["reason"] == "action_intent_already_committed"
    assert len(adapter.submit_calls) == 1
    client.close_position.assert_not_called()
