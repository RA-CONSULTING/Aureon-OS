from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest

from aureon.exchanges.kraken_client import KrakenClient
from aureon.governance.durable_contingency import (
    DurableContingencyRecordRef,
    bind_durable_contingency_recovery,
)
from aureon.governance.economic_boundary import (
    CONTINGENCY_WARRANT_SCHEMA,
    ContingencyWarrant,
    EconomicGovernanceBoundary,
)
from aureon.strategies.s5_live_execution import (
    ConversionOpportunity,
    LivePrice,
    PendingIntent,
    S5LiveExecutionEngine,
)

NOW = 2_000_000_000.0
ORDER_ID = "OABC12-DEF345-GHI678"
ACCOUNT_HASH = "a" * 64
HNC_RECEIPT = "hnc:live_field:s5-readiness"
AURIS_RECEIPT = "auris:cosmic_state:s5-readiness"


def _allowing_boundary() -> EconomicGovernanceBoundary:
    boundary = Mock(spec=EconomicGovernanceBoundary)
    boundary._boundary_id = 'economic-boundary:test-s5'
    boundary._recovery_capability = object()
    boundary._permit_ttl = Decimal('2')
    boundary._validate_recovered_warrant.return_value = None
    boundary._validate_contingency_reduction.return_value = None
    boundary.prepare_mutation.side_effect = lambda intent: SimpleNamespace(
        permit_id=f"permit:{intent.intent_digest}",
        dual_receipt_id="dual:s5-readiness",
        proposal_digest="b" * 64,
    )
    boundary.approve_contingency_warrant.side_effect = (
        lambda scope: ContingencyWarrant(
            schema=CONTINGENCY_WARRANT_SCHEMA,
            warrant_id=f"warrant:{scope.scope_digest}",
            boundary_id=boundary._boundary_id,
            scope_digest=scope.scope_digest,
            scope_json=json.dumps(
                scope.payload(),
                sort_keys=True,
                separators=(',', ':'),
            ),
            dual_receipt_id='dual:s5-readiness',
            dual_receipt_json='{}',
            proposal_digest='c' * 64,
            issued_at=str(NOW),
            expires_at=str(NOW + 60),
        )
    )
    boundary.prepare_recovered_contingency_reduction.side_effect = (
        lambda claim, intent: SimpleNamespace(
            permit_id=f"permit:{intent.intent_digest}",
            dual_receipt_id=claim.warrant.dual_receipt_id,
            proposal_digest=claim.warrant.proposal_digest,
            expires_at=str(NOW + 2),
        )
    )
    boundary.consume_and_call.side_effect = (
        lambda _permit, **kwargs: kwargs["transport"]()
    )
    return boundary


def _recovery_adapter(boundary, state_path):
    return bind_durable_contingency_recovery(
        adapter_id='adapter:s5-kraken-recovery:v1',
        trusted_adapter_ids=frozenset({
            'adapter:s5-kraken-recovery:v1',
        }),
        boundary=boundary,
        store_path=state_path.with_name(
            state_path.stem + '.contingency.json'
        ),
        clock=lambda: NOW,
        claim_ttl_s=5.0,
    )


def _client() -> KrakenClient:
    client = KrakenClient()
    client.dry_run = False
    return client


def test_pair_scoped_account_receipt_converts_provider_fee_percent_exactly() -> None:
    provider_time = time.time() - 0.25
    client = _client()
    client._resolve_pair = Mock(
        return_value=("XXBTZUSD", {"altname": "XBTUSD"})
    )

    def private(path: str, data: dict) -> dict:
        if path == "/0/private/GetApiKeyInfo":
            return {
                "apiKey": client.api_key,
                "permissions": ["modify-trades", "query-funds"],
                "validUntil": "0",
                "ipAllowlist": [],
                "secret_not_receipted": "do-not-copy",
            }
        if path == "/0/private/Balance":
            return {"XXBT": "0.25", "ZUSD": "125.50"}
        if path == "/0/private/TradeVolume":
            assert data == {"pair": "XXBTZUSD", "fee-info": True}
            return {
                "currency": "ZUSD",
                "fees": {
                    "XXBTZUSD": {
                        "fee": "0.2600",
                        "secret_not_receipted": "do-not-copy",
                    }
                },
            }
        raise AssertionError(path)

    client._private = Mock(side_effect=private)
    client._public_get = Mock(return_value={"unixtime": provider_time})

    first = client.get_account_balance_receipt(pair="XBTUSD")
    second = client.get_account_balance_receipt(pair="XBTUSD")

    assert first["provider_receipt_type"] == "Balance+TradeVolume+Time+KeyInfo"
    assert first["taker_fee_pair"] == "XBTUSD"
    assert first["provider_fee_pair"] == "XXBTZUSD"
    assert first["taker_fee_percent_text"] == "0.2600"
    assert first["taker_fee_rate_text"] == "0.0026"
    assert first["taker_fee_rate"] == pytest.approx(0.0026)
    assert first["balances"] == {"BTC": 0.25, "USD": 125.5}
    assert len(first["input_receipt_ids"]) == 4
    assert first["api_key_query_funds"] is True
    assert first["api_key_modify_trades"] is True
    assert first["api_key_funding_mutations_absent"] is True
    assert len(first["account_id_hash"]) == 64
    assert first["receipt_id"] == second["receipt_id"]
    assert "secret_not_receipted" not in json.dumps(first)
    assert client._private.call_args_list == [
        call("/0/private/GetApiKeyInfo", {}),
        call("/0/private/Balance", {}),
        call(
            "/0/private/TradeVolume",
            {"pair": "XXBTZUSD", "fee-info": True},
        ),
        call("/0/private/GetApiKeyInfo", {}),
        call("/0/private/Balance", {}),
        call(
            "/0/private/TradeVolume",
            {"pair": "XXBTZUSD", "fee-info": True},
        ),
    ]
    assert client._public_get.call_args_list == [
        call("/0/public/Time"),
        call("/0/public/Time"),
    ]


def test_account_receipt_rejects_funding_capable_api_key() -> None:
    client = _client()
    client._private = Mock(
        return_value={
            "apiKey": client.api_key,
            "permissions": [
                "modify-trades",
                "query-funds",
                "withdraw-funds",
            ],
            "validUntil": "0",
            "ipAllowlist": [],
        }
    )
    client._public_get = Mock(side_effect=AssertionError("clock not expected"))

    receipt = client.get_account_balance_receipt(pair="XBTUSD")

    assert receipt["data_status"] == "no_data"
    assert receipt["reason"] == "least_privilege_kraken_trading_key_required"
    assert receipt["receipt_id"] is None
    assert client._private.call_args_list == [
        call("/0/private/GetApiKeyInfo", {}),
    ]
    client._public_get.assert_not_called()


@pytest.mark.parametrize("fee", [None, True, "NaN", "-0.01", "100.01"])
def test_pair_scoped_account_receipt_rejects_unusable_provider_fee(
    fee: object,
) -> None:
    client = _client()
    client._resolve_pair = Mock(
        return_value=("XXBTZUSD", {"altname": "XBTUSD"})
    )
    client._private = Mock(
        side_effect=[
            {
                "apiKey": client.api_key,
                "permissions": ["modify-trades", "query-funds"],
                "validUntil": "0",
                "ipAllowlist": [],
            },
            {"ZUSD": "10"},
            {"fees": {"XXBTZUSD": {"fee": fee}}},
        ]
    )
    client._public_get = Mock(side_effect=AssertionError("clock not expected"))

    receipt = client.get_account_balance_receipt(pair="XBTUSD")

    assert receipt["data_status"] == "no_data"
    assert receipt["receipt_id"] is None
    assert receipt["taker_fee_rate"] is None
    client._public_get.assert_not_called()


def test_market_add_order_uses_cl_ord_id_and_never_transport_retries_post() -> None:
    client = _client()
    allowed_methods = client.session.get_adapter("https://").max_retries.allowed_methods
    assert set(allowed_methods or ()) == {"GET"}

    client._resolve_pair = Mock(
        return_value=(
            "XXBTZUSD",
            {"altname": "XBTUSD", "ordermin": "0.0001", "lot_decimals": 8},
        )
    )
    client._private = Mock(return_value={"txid": [ORDER_ID]})
    client_order_id = hashlib.sha256(b"durable-s5-intent").hexdigest()[:32]

    acknowledgement = client.place_market_order(
        symbol="XBTUSD",
        side="sell",
        quantity="0.1",
        client_order_id=client_order_id,
    )

    assert acknowledgement["orderId"] == ORDER_ID
    assert acknowledgement["cl_ord_id"] == client_order_id
    client._private.assert_called_once_with(
        "/0/private/AddOrder",
        {
            "pair": "XXBTZUSD",
            "type": "sell",
            "ordertype": "market",
            "volume": "0.1",
            "cl_ord_id": client_order_id,
        },
    )
    with pytest.raises(ValueError, match="32-character hexadecimal"):
        client.place_market_order(
            symbol="XBTUSD",
            side="sell",
            quantity="0.1",
            client_order_id="not-valid",
        )


class _PairAwareKraken:
    def __init__(self, state_path, mode: str) -> None:
        self.state_path = state_path
        self.mode = mode
        self.account_pairs: list[str] = []
        self.submissions: list[dict] = []
        self.snapshots_before_post: list[dict] = []
        self.reads = 0
        self.base_balance = 1.0

    def get_account_balance_receipt(self, *, pair: str) -> dict:
        self.account_pairs.append(pair)
        phase = "pre" if self.base_balance == 1.0 else "post"
        receipt_id = (
            "kraken-account-xbtusd"
            if phase == "pre"
            else "kraken-account-xbtusd-post"
        )
        return {
            "provider": "kraken",
            "venue": "kraken",
            "provider_receipt_type": "Balance+TradeVolume+Time+KeyInfo",
            "account_scope": "complete",
            "balances": {"USD": 100.0, "BTC": self.base_balance},
            "taker_fee_pair": pair,
            "taker_fee_rate": 0.0026,
            "input_receipt_ids": [
                f"kraken-balance-xbtusd-{phase}",
                f"kraken-fee-xbtusd-{phase}",
                f"kraken-time-xbtusd-{phase}",
                f"kraken-permissions-xbtusd-{phase}",
            ],
            "account_id_hash": ACCOUNT_HASH,
            "api_key_permission_receipt_id": (
                f"kraken_api_key_permissions:xbtusd-{phase}"
            ),
            "api_key_query_funds": True,
            "api_key_modify_trades": True,
            "api_key_funding_mutations_absent": True,
            "source_id": (
                "kraken:/0/private/Balance+"
                "/0/private/TradeVolume+/0/public/Time"
            ),
            "source_timestamp": NOW - 1.5,
            "received_at": NOW - 1.4,
            "receipt_id": receipt_id,
            "data_status": "live",
            "truth_status": "real_observed",
            "generated_values": False,
        }

    @staticmethod
    def prepare_economic_market_order(
        *,
        symbol: str,
        side: str,
        quantity: float,
        client_order_id: str,
    ) -> dict:
        return {
            "pair": symbol,
            "type": side,
            "ordertype": "market",
            "volume": str(quantity),
            "cl_ord_id": client_order_id,
        }

    def place_market_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: float,
        client_order_id: str,
    ) -> dict:
        snapshot = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.snapshots_before_post.append(snapshot)
        self.submissions.append(
            {
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "client_order_id": client_order_id,
            }
        )
        order_id = (
            ORDER_ID
            if len(self.submissions) == 1
            else "OXYZ12-ABC345-DEF678"
        )
        if self.mode == "raise":
            raise TimeoutError("offline ambiguous transport")
        acknowledgement = {
            "orderId": order_id,
            "status": "pending_reconciliation",
            "data_status": "pending_reconciliation",
            "truth_status": "real_observed",
            "generated_values": False,
        }
        if self.mode == "success":
            acknowledgement["cl_ord_id"] = client_order_id
        return acknowledgement

    def get_order_status(self, order_id: str) -> dict:
        self.reads += 1
        assert order_id == ORDER_ID
        return {
            "orderId": ORDER_ID,
            "symbol": "XBTUSD",
            "side": "buy",
            "status": "CANCELED",
            "data_status": "live",
            "truth_status": "real_observed",
            "generated_values": False,
            "reconciliation_required": False,
            "source_id": f"kraken_order:/0/private/QueryOrders:{ORDER_ID}",
            "source_timestamp": NOW - 0.2,
            "received_at": NOW - 0.1,
        }


def _gate_receipt() -> dict:
    return {
        "source_id": "aureon:hnc_auris_gate",
        "receipt_id": "hnc-auris-xbtusd",
        "input_receipt_ids": [
            "market-xbtusd",
            "kraken-account-xbtusd",
            HNC_RECEIPT,
            AURIS_RECEIPT,
        ],
        "hnc_receipt_id": HNC_RECEIPT,
        "auris_receipt_id": AURIS_RECEIPT,
        "authorization_receipt_id": "authorization:s5-readiness",
        "cycle_id": "cycle:s5-readiness",
        "environment": "live",
        "symbol": "XBTUSD",
        "source_timestamp": NOW - 1.0,
        "received_at": NOW - 0.9,
        "truth_status": "real_derived",
        "generated_values": False,
        "eligible_for_action": True,
        "earth_open": True,
        "cosmic_open": True,
        "earth_coherence": 0.8,
        "earth_phase_lock": 0.7,
        "earth_phi_boost": 1.1,
        "cosmic_coherence": 0.8,
        "cosmic_distortion": 0.1,
        "cosmic_boost": 1.05,
        "cosmic_joy": 0.4,
        "cosmic_reciprocity": 0.5,
        "planetary_torque": 1.0,
        "lunar_phase": 0.3,
        "cosmic_phase": "aligned",
    }


def _engine_and_evidence(tmp_path, mode: str):
    state_path = tmp_path / f"s5-kraken-{mode}.json"
    kraken = _PairAwareKraken(state_path, mode)
    boundary = _allowing_boundary()
    engine = S5LiveExecutionEngine(
        starting_capital=100.0,
        dry_run=False,
        kraken=kraken,
        network=object(),
        account_receipt_supplier=kraken.get_account_balance_receipt,
        hnc_auris_gate_receipt_supplier=_gate_receipt,
        economic_governance_boundary=boundary,
        contingency_recovery=_recovery_adapter(
            boundary,
            state_path,
        ),
        intent_store_path=state_path,
        clock=lambda: NOW,
    )
    market = LivePrice(
        symbol="BTCUSDT",
        venue_symbol="XBTUSD",
        price=100.0,
        bid=99.9,
        ask=100.1,
        volume_24h=10.0,
        change_24h=0.01,
        source_id="kraken:/0/public/Ticker+/0/public/Time",
        source_timestamp=NOW - 2.0,
        received_at=NOW - 1.9,
        receipt_id="market-xbtusd",
    )
    engine.prices["BTCUSDT"] = market
    evidence, reason = engine._evidence_bundle("BTCUSDT")
    assert reason == ""
    assert evidence is not None
    assert kraken.account_pairs == ["XBTUSD"]
    opportunity = ConversionOpportunity(
        from_asset="USD",
        to_asset="BTC",
        gross_profit=0.2,
        fee=0.05,
        net_profit=0.15,
        price_change=0.01,
        timestamp=datetime.fromtimestamp(NOW, tz=UTC),
        opportunity_type="offline_spot_readiness",
        s5_score=0.8,
        symbol="BTCUSDT",
        venue_symbol="XBTUSD",
        quantity=1.0,
        side="buy",
        market_receipt_id=market.receipt_id,
        account_receipt_id=evidence["account"]["receipt_id"],
        gate_receipt_id=evidence["gate"]["receipt_id"],
    )
    return engine, kraken, evidence, opportunity, state_path


def _restart_engine(state_path, kraken, boundary, *, gate_supplier=_gate_receipt):
    return S5LiveExecutionEngine(
        dry_run=False,
        kraken=kraken,
        network=object(),
        account_receipt_supplier=kraken.get_account_balance_receipt,
        hnc_auris_gate_receipt_supplier=gate_supplier,
        economic_governance_boundary=boundary,
        contingency_recovery=_recovery_adapter(boundary, state_path),
        intent_store_path=state_path,
        clock=lambda: NOW,
    )


def _settle_entry_fill(engine, acknowledgement) -> None:
    pending = engine._pending_intents[acknowledgement['intent_key']]
    entry_fill = {
        'receipt_id': 'kraken-entry-fill-1',
        'orderId': ORDER_ID,
        'symbol': 'XBTUSD',
        'side': 'buy',
        'status': 'FILLED',
        'data_status': 'live',
        'truth_status': 'real_observed',
        'generated_values': False,
        'fill_receipt_complete': True,
        'eligible_for_accounting': True,
        'eligible_for_learning': True,
        'reconciliation_required': False,
        'filled_qty': '1',
        'filled_avg_price': '100',
        'filled_notional': '100',
        'fee': '0.26',
        'fee_currency': 'USD',
        'fills': [{
            'tradeId': 'TENTRY1-ABC123-DEF456',
            'source': 'kraken_queryorders',
        }],
        'source_id': f'kraken_order:{ORDER_ID}',
        'source_timestamp': NOW - 0.2,
        'received_at': NOW - 0.1,
    }
    normalized, reason = engine._terminal_fill_receipt(entry_fill, pending)
    assert reason == ''
    assert normalized is not None
    assert engine._apply_terminal_fill(pending, normalized)['status'] == 'FILLED'


@pytest.mark.parametrize(
    ("mode", "reason"),
    [
        ("raise", "ambiguous_submission_requires_external_reconciliation"),
        ("missing_link", "provider_client_order_id_link_required"),
    ],
)
def test_s5_persists_cl_ord_id_before_ambiguous_post_and_never_replays(
    tmp_path,
    mode: str,
    reason: str,
) -> None:
    engine, kraken, evidence, opportunity, state_path = _engine_and_evidence(
        tmp_path, mode
    )

    result = engine._submit_intent(opportunity, bundle=evidence)

    assert result["status"] == "pending_reconciliation"
    assert result["reason"] == reason
    assert len(kraken.submissions) == 1
    intent_key = (
        "conversion:BTCUSDT:buy:market-xbtusd"
    )
    expected_client_order_id = hashlib.sha256(
        intent_key.encode("utf-8")
    ).hexdigest()[:32]
    assert kraken.submissions[0]["client_order_id"] == expected_client_order_id
    before_post = kraken.snapshots_before_post[0]["pending_intents"][0]
    assert before_post["intent_key"] == intent_key
    assert before_post["client_order_id"] == expected_client_order_id
    assert before_post["state"] == "submission_in_progress"
    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    assert persisted["pending_intents"][0]["client_order_id"] == (
        expected_client_order_id
    )

    reconcile_only = engine._reconcile_pending(intent_key)
    assert reconcile_only["reason"] == (
        "ambiguous_submission_requires_external_reconciliation"
    )
    duplicate = engine._submit_intent(opportunity, bundle=evidence)
    assert duplicate["reason"] == "unresolved_intent_suppresses_duplicate_submission"
    assert len(kraken.submissions) == 1
    assert kraken.reads == 0

    reloaded = S5LiveExecutionEngine(
        dry_run=False,
        kraken=kraken,
        network=object(),
        account_receipt_supplier=kraken.get_account_balance_receipt,
        hnc_auris_gate_receipt_supplier=_gate_receipt,
        intent_store_path=state_path,
        clock=lambda: NOW,
    )
    assert reloaded._state_load_error is None
    assert reloaded._pending_intents[intent_key].client_order_id == (
        expected_client_order_id
    )


def test_terminal_nonfill_closes_intent_and_blocks_cl_ord_id_reuse(tmp_path) -> None:
    engine, kraken, evidence, opportunity, state_path = _engine_and_evidence(
        tmp_path, "success"
    )

    acknowledgement = engine._submit_intent(opportunity, bundle=evidence)
    intent_key = acknowledgement["intent_key"]
    assert acknowledgement["reason"] == (
        "submission_acknowledged_terminal_receipt_required"
    )

    terminal = engine._reconcile_pending(intent_key)

    assert terminal["reason"] == "terminal_provider_receipt_without_fill"
    assert kraken.reads == 1
    assert engine.stats["real_trades_placed"] == 0
    assert engine.stats["observed_fees_by_currency"] == {}
    closed = json.loads(state_path.read_text(encoding="utf-8"))["closed_intents"]
    assert closed[intent_key]["client_order_id"] == (
        kraken.submissions[0]["client_order_id"]
    )
    duplicate = engine._submit_intent(opportunity, bundle=evidence)
    assert duplicate["reason"] == "closed_intent_client_order_id_reuse_blocked"
    assert len(kraken.submissions) == 1


def test_fresh_restart_recovers_exact_containment_without_new_voices(
    tmp_path,
) -> None:
    engine, kraken, evidence, opportunity, state_path = _engine_and_evidence(
        tmp_path,
        'success',
    )
    acknowledgement = engine._submit_intent(opportunity, bundle=evidence)
    _settle_entry_fill(engine, acknowledgement)
    entry_boundary = engine.economic_governance_boundary
    assert isinstance(entry_boundary, EconomicGovernanceBoundary)
    entry_boundary.approve_contingency_warrant.assert_called_once()
    kraken.base_balance = 2.0

    restarted_boundary = _allowing_boundary()
    disabled_gate = Mock(
        side_effect=AssertionError('HNC/Auris gate must not reopen'),
    )
    restarted = _restart_engine(
        state_path,
        kraken,
        restarted_boundary,
        gate_supplier=disabled_gate,
    )
    restarted.prices.update(engine.prices)
    assert restarted._state_load_error is None

    result = restarted.submit_preapproved_contingency_reduction(
        entry_order_id=ORDER_ID,
    )

    assert result['reason'] == (
        'containment_acknowledged_terminal_receipt_required'
    )
    assert len(kraken.submissions) == 2
    assert kraken.submissions[-1]['side'] == 'sell'
    assert 0 < kraken.submissions[-1]['quantity'] <= 1.0
    disabled_gate.assert_not_called()
    restarted_boundary.prepare_mutation.assert_not_called()
    restarted_boundary.approve_contingency_warrant.assert_not_called()
    restarted_boundary.prepare_contingency_reduction.assert_not_called()
    restarted_boundary.prepare_recovered_contingency_reduction.assert_called_once()
    restarted_boundary.consume_and_call.assert_called_once()


def test_legacy_unhashed_s5_state_fails_closed_before_provider(
    tmp_path,
) -> None:
    engine, kraken, evidence, opportunity, state_path = _engine_and_evidence(
        tmp_path,
        'success',
    )
    assert engine._persist_intent_state() is True
    legacy = json.loads(state_path.read_text(encoding='utf-8'))
    legacy['schema'] = 'aureon.s5_live_execution.intent.v1'
    legacy.pop('state_hash')
    state_path.write_text(
        json.dumps(legacy, sort_keys=True, separators=(',', ':')),
        encoding='utf-8',
    )
    submissions_before = list(kraken.submissions)
    boundary = _allowing_boundary()

    restarted = _restart_engine(state_path, kraken, boundary)
    result = restarted._submit_intent(opportunity, bundle=evidence)

    assert restarted._state_load_error == 'ValueError'
    assert restarted.check_runtime_ready() is False
    assert result['reason'] == 'valid_intent_state_readback_required'
    assert kraken.submissions == submissions_before
    boundary.prepare_mutation.assert_not_called()
    boundary.approve_contingency_warrant.assert_not_called()
    boundary.consume_and_call.assert_not_called()


@pytest.mark.parametrize(
    ('crash_point', 'sidecar_status', 'containment_calls'),
    [
        ('transport_ambiguous', 'AMBIGUOUS', 1),
        ('after_submitting_checkpoint', 'SUBMITTING', 0),
    ],
)
def test_containment_uncertainty_restarts_reconciliation_only(
    tmp_path,
    crash_point: str,
    sidecar_status: str,
    containment_calls: int,
) -> None:
    engine, kraken, evidence, opportunity, state_path = _engine_and_evidence(
        tmp_path,
        'success',
    )
    acknowledgement = engine._submit_intent(opportunity, bundle=evidence)
    _settle_entry_fill(engine, acknowledgement)
    kraken.base_balance = 2.0
    boundary = _allowing_boundary()
    restarted = _restart_engine(state_path, kraken, boundary)
    restarted.prices.update(engine.prices)
    submissions_before = len(kraken.submissions)

    if crash_point == 'transport_ambiguous':
        kraken.mode = 'raise'
        first = restarted.submit_preapproved_contingency_reduction(
            entry_order_id=ORDER_ID,
        )
        assert first['reason'] == (
            'ambiguous_containment_requires_external_reconciliation'
        )
    else:
        boundary.consume_and_call.side_effect = SystemExit(
            'simulated process termination after SUBMITTING checkpoint'
        )
        with pytest.raises(SystemExit):
            restarted.submit_preapproved_contingency_reduction(
                entry_order_id=ORDER_ID,
            )

    fill = restarted._settled_fills[0]
    reference = DurableContingencyRecordRef(
        record_digest=fill['contingency_recovery_record_digest'],
        entry_state_anchor=fill['contingency_recovery_entry_state_anchor'],
        bound_route_state_anchor=(
            fill['contingency_recovery_route_binding_anchor']
        ),
    )
    assert restarted.contingency_recovery.status(reference) == sidecar_status
    assert len(kraken.submissions) == submissions_before + containment_calls

    kraken.mode = 'success'
    final_boundary = _allowing_boundary()
    final_restart = _restart_engine(state_path, kraken, final_boundary)
    replay = final_restart.submit_preapproved_contingency_reduction(
        entry_order_id=ORDER_ID,
    )

    assert replay['reason'] == 'contingency_attempt_already_recorded'
    assert len(kraken.submissions) == submissions_before + containment_calls
    final_boundary.prepare_recovered_contingency_reduction.assert_not_called()
    final_boundary.consume_and_call.assert_not_called()


def test_same_process_warrant_reduces_only_observed_entry_exposure(
    tmp_path,
) -> None:
    engine, kraken, evidence, opportunity, state_path = _engine_and_evidence(
        tmp_path, "success"
    )
    acknowledgement = engine._submit_intent(opportunity, bundle=evidence)
    pending = engine._pending_intents[acknowledgement["intent_key"]]
    entry_fill = {
        "receipt_id": "kraken-entry-fill-1",
        "orderId": ORDER_ID,
        "symbol": "XBTUSD",
        "side": "buy",
        "status": "FILLED",
        "data_status": "live",
        "truth_status": "real_observed",
        "generated_values": False,
        "fill_receipt_complete": True,
        "eligible_for_accounting": True,
        "eligible_for_learning": True,
        "reconciliation_required": False,
        "filled_qty": "1",
        "filled_avg_price": "100",
        "filled_notional": "100",
        "fee": "0.26",
        "fee_currency": "USD",
        "fills": [
            {
                "tradeId": "TENTRY1-ABC123-DEF456",
                "source": "kraken_queryorders",
            }
        ],
        "source_id": f"kraken_order:{ORDER_ID}",
        "source_timestamp": NOW - 0.2,
        "received_at": NOW - 0.1,
    }
    normalized, reason = engine._terminal_fill_receipt(entry_fill, pending)
    assert reason == ""
    assert normalized is not None
    applied = engine._apply_terminal_fill(pending, normalized)
    assert applied["status"] == "FILLED"

    boundary = engine.economic_governance_boundary
    assert isinstance(boundary, EconomicGovernanceBoundary)
    boundary.prepare_mutation.side_effect = AssertionError(
        "fresh Council/Crown entry authority must not be reused"
    )
    boundary.approve_contingency_warrant.side_effect = AssertionError(
        "warrant was already approved before entry submission"
    )
    boundary.prepare_contingency_reduction.side_effect = AssertionError(
        'in-memory warrant path must not be used'
    )
    kraken.base_balance = 2.0
    containment = engine.submit_preapproved_contingency_reduction(
        entry_order_id=ORDER_ID
    )

    assert containment["reason"] == (
        "containment_acknowledged_terminal_receipt_required"
    )
    assert len(kraken.submissions) == 2
    assert kraken.submissions[1]["side"] == "sell"
    assert 0 < kraken.submissions[1]["quantity"] <= 1.0
    boundary.prepare_recovered_contingency_reduction.assert_called_once()
    reduction_intent = (
        boundary.prepare_recovered_contingency_reduction.call_args.args[1]
    )
    assert reduction_intent.side == "SELL"
    assert reduction_intent.position_side == "LONG"
    assert reduction_intent.reduce_only is True
    assert float(reduction_intent.quantity) <= 1.0
    assert float(reduction_intent.quantity) <= float(
        reduction_intent.observed_exposure_quantity
    )

    restarted_boundary = _allowing_boundary()
    restarted = S5LiveExecutionEngine(
        dry_run=False,
        kraken=kraken,
        network=object(),
        account_receipt_supplier=kraken.get_account_balance_receipt,
        hnc_auris_gate_receipt_supplier=_gate_receipt,
        economic_governance_boundary=restarted_boundary,
        contingency_recovery=_recovery_adapter(
            restarted_boundary,
            state_path,
        ),
        intent_store_path=state_path,
        clock=lambda: NOW,
    )
    restart_result = restarted.submit_preapproved_contingency_reduction(
        entry_order_id=ORDER_ID
    )
    assert restart_result["reason"] == "contingency_attempt_already_recorded"
    assert len(kraken.submissions) == 2


def test_canonical_query_orders_receipt_reaches_s5_terminal_gate() -> None:
    observed_now = time.time()
    client = _client()
    client._pair_base_quote = Mock(return_value=("BTC", "USD"))
    provider_order = {
        "status": "closed",
        "closetm": observed_now - 0.2,
        "vol": "1",
        "vol_exec": "1",
        "price": "100",
        "cost": "100",
        "fee": "0.26",
        "trades": ["TABC12-DEF345-GHI678"],
        "descr": {"pair": "XBTUSD", "type": "buy", "ordertype": "market"},
    }
    receipt = client._normalize_order_receipt(
        ORDER_ID,
        provider_order,
        provider_receipt_type="QueryOrders",
        now=observed_now,
    )
    assert receipt["source_id"] == (
        f"kraken_order:/0/private/QueryOrders:{ORDER_ID}"
    )
    assert receipt["fee_currency"] == "USD"

    engine = S5LiveExecutionEngine(
        dry_run=False,
        clock=lambda: observed_now,
    )
    pending = PendingIntent(
        intent_key="conversion:BTCUSDT:buy:market-xbtusd",
        client_order_id="a" * 32,
        symbol="BTCUSDT",
        venue_symbol="XBTUSD",
        side="buy",
        requested_quantity=1.0,
        opportunity={"from_asset": "USD", "to_asset": "BTC"},
        market_receipt_id="market-xbtusd",
        account_receipt_id="kraken-account-xbtusd",
        gate_receipt_id="hnc-auris-xbtusd",
        state="pending_reconciliation",
        order_id=ORDER_ID,
    )

    normalized, reason = engine._terminal_fill_receipt(receipt, pending)

    assert reason == ""
    assert normalized is not None
    assert normalized["fee"] == pytest.approx(0.26)
    assert normalized["fee_currency"] == "USD"

    provider_order["descr"]["type"] = "sell"
    sell_receipt = client._normalize_order_receipt(
        ORDER_ID,
        provider_order,
        provider_receipt_type="QueryOrders",
        now=observed_now,
    )
    assert sell_receipt["fee_currency"] == "USD"
