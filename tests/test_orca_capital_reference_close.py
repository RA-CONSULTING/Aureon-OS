"""A reference-only Capital adoption closes by the confirmed OPENED dealId.

Scan adopts dealId or dealReference. The close must not send the reference.
GET /confirms/{ref} (affectedDeals OPENED) supplies the dealId. A missing
or REJECTED confirm does not close. Offline fakes only; no network.
"""
import importlib
from unittest import mock

import pytest

from aureon.exchanges.orca_capital_ownership import ADOPT_ENV

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


def test_reference_with_opened_deal_closes_on_both_copies():
    for module, runner in (
        (radar_kc, lambda chain, target: chain.execute_kill_chain_safe(target)),
        (aureon_kc, lambda chain, target: chain.execute_kill_chain(target)),
    ):
        client = _client(lambda ref: _opened(ref))
        chain = module.UnifiedKillChain.__new__(module.UnifiedKillChain)
        runner(chain, _target(client))
        client.close_position.assert_called_once_with("D-REAL")
        client.confirm_order.assert_called_once_with("o_REF")


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
        aureon.execute_kill_chain(_target(client))
        client.close_position.assert_not_called()
