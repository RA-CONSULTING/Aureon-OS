from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime
from decimal import ROUND_DOWN, Decimal
from pathlib import Path
from typing import Any

import pytest

import aureon.governance.crown_voice as crown_module
import aureon.governance.economic_boundary as boundary_module
from aureon.exchanges.binance_client import BinanceClient
from aureon.governance.cognition_gate import (
    CognitionGovernanceRequest,
    build_cognition_governance_request,
)
from aureon.governance.crown_voice import (
    ResolvedCrownVoiceEvidence,
    issue_crown_voice_receipt,
)
from aureon.governance.dual_key import join_dual_key
from aureon.governance.durable_contingency import (
    bind_durable_contingency_recovery,
)
from aureon.governance.economic_boundary import (
    EconomicGovernanceBlocked,
    EconomicGovernanceBoundary,
    bind_economic_governance_boundary,
)
from aureon.swarm.druidic_council import (
    REQUIRED_SEATS,
    build_seat_receipt,
    convene_druidic_council,
)
from aureon.swarm.auris_node_receipts import ProviderMoment
from aureon.trading.bounded_binance_roundtrip import (
    _ACCOUNT_PERMISSION_TRUE_FLAGS,
    _FALSE_COGNITIVE_ALIASES,
    AUTH_EXPIRES_AT,
    AUTH_ISSUED_AT,
    ENTRY_CUTOFF_AT,
    BoundedBinanceRoundTrip,
    _read_verified_state,
    cycle_state_path,
    expected_confirmation_token,
    main,
)

NOW = datetime.fromisoformat("2026-08-11T12:30:00+00:00").timestamp()
AUTHORIZATION_ID = "gary-leckey-binance-btcusdt-20260811"
INTENT_ID = "one-bounded-btcusdt-roundtrip"
SECRET_SENTINEL = "DO_NOT_PERSIST_PROVIDER_SECRET"
COUNCIL_SUPPLIER_ID = 'resolver:bounded-binance-council:v1'
CROWN_SUPPLIER_ID = 'resolver:bounded-binance-crown:v1'
_DEFAULT_BOUNDARY = object()


class FakeCouncilSupplier:
    supplier_id = COUNCIL_SUPPLIER_ID

    def __init__(self) -> None:
        self.calls = 0

    def supply_council_evidence(
        self,
        request: CognitionGovernanceRequest,
    ) -> None:
        self.calls += 1


class FakeCrownSupplier:
    supplier_id = CROWN_SUPPLIER_ID

    def __init__(self) -> None:
        self.calls = 0

    def supply_crown_receipt(
        self,
        request: CognitionGovernanceRequest,
    ) -> None:
        self.calls += 1


class _ProviderBoundCrownResolver:
    def __init__(
        self,
        request: CognitionGovernanceRequest,
        moment: ProviderMoment,
        decision: str,
    ) -> None:
        self.request = request
        self.moment = moment
        self.decision = decision

    def resolve_crown_voice_evidence(
        self,
        proposal_digest: str,
        prompt_digest: str,
    ) -> ResolvedCrownVoiceEvidence:
        verdict = {
            'ACCEPT': 'APPROVED',
            'HOLD': 'CONCERNED',
            'ABORT': 'VETO',
        }[self.decision]
        evidence = {'provider_moment': self.moment}
        return ResolvedCrownVoiceEvidence(
            resolver_id=CROWN_SUPPLIER_ID,
            issuer_id='issuer:independent-bounded-binance-crown',
            crown_identity='queen:bounded-binance-conscience',
            verdict_source_id='queen:bounded-binance:evaluation',
            queen_verdict=verdict,
            queen_evaluated=True,
            reason='Crown checked the exact bounded mutation',
            proposal_digest=proposal_digest,
            prompt_digest=prompt_digest,
            hnc_evidence=evidence,
            auris_evidence=evidence,
        )


def _request_from_dual_kwargs(
    kwargs: dict[str, Any],
) -> CognitionGovernanceRequest:
    return build_cognition_governance_request(
        prompt=kwargs['prompt'],
        answer=kwargs['answer'],
        tool_calls=kwargs['tool_calls'],
        capability=kwargs['capability'],
        bake=kwargs['bake'],
        acquisition=kwargs['acquisition'],
        queen_verdict=kwargs['queen_verdict'],
    )


class FakeDualVoiceRuntime:
    def __init__(self) -> None:
        self.outcome = 'ACCEPT'
        self.calls: list[dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        request = _request_from_dual_kwargs(kwargs)
        kwargs['council_receipt_supplier'].supply_council_evidence(request)
        kwargs['crown_receipt_supplier'].supply_crown_receipt(request)
        if self.outcome == 'NO_DATA':
            return {
                'schema': 'aureon.dual_key_governance.v1',
                'receipt_type': 'druid_queen_dual_key',
                'receipt_id': None,
                'decision': 'HOLD',
                'data_status': 'no_data',
            }
        now = float(kwargs['now'])
        source_timestamp = (
            now - 1_000.0
            if self.outcome == 'STALE'
            else float(kwargs['acquisition']['provider_source_timestamp'])
        )
        decision = (
            self.outcome if self.outcome in {'HOLD', 'ABORT'} else 'ACCEPT'
        )
        hnc_receipt_id = kwargs['acquisition']['hnc_receipt_id']
        auris_receipt_id = kwargs['acquisition']['auris_receipt_id']
        seats = [
            build_seat_receipt(
                seat=seat,
                agent_id=f'bounded-binance-agent-{seat}',
                decision=decision,
                reason=f'{seat} checked the exact bounded mutation',
                gamma=0.95,
                proposal_digest=request.proposal_digest,
                prompt_digest=request.prompt_digest,
                hnc_receipt_id=hnc_receipt_id,
                auris_receipt_id=auris_receipt_id,
                auris_node_receipt_id=f'auris:node:bounded:{seat}',
                source_timestamp=source_timestamp,
                derived_at=now,
            )
            for seat in REQUIRED_SEATS
        ]
        council = convene_druidic_council(
            proposal_digest=request.proposal_digest,
            prompt_digest=request.prompt_digest,
            hnc_receipt_id=hnc_receipt_id,
            auris_receipt_id=auris_receipt_id,
            seat_receipts=seats,
            now=now,
        )
        moment = ProviderMoment(
            hnc_receipt_id=hnc_receipt_id,
            auris_receipt_id=auris_receipt_id,
            source_timestamp=source_timestamp,
            provider_receipt_ids=request.provider_receipt_ids,
            provider_moment_digest=request.provider_moment_digest,
        )
        queen = issue_crown_voice_receipt(
            proposal_digest=request.proposal_digest,
            prompt_digest=request.prompt_digest,
            resolver=_ProviderBoundCrownResolver(
                request,
                moment,
                decision,
            ),
            now=now,
        )
        dual = join_dual_key(council, queen, now=now)
        if self.outcome == 'TAMPERED':
            dual['proposal_digest'] = '0' * 64
        return dual


@pytest.fixture(autouse=True)
def dual_harness(
    monkeypatch: pytest.MonkeyPatch,
) -> FakeDualVoiceRuntime:
    runtime = FakeDualVoiceRuntime()
    monkeypatch.setattr(
        crown_module,
        'validate_provider_moment',
        lambda hnc, auris, **kwargs: hnc['provider_moment'],
    )
    monkeypatch.setattr(
        boundary_module,
        'evaluate_cognition_governance',
        runtime,
    )
    return runtime


class MutableClock:
    def __init__(self, value: float = NOW) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


def authorization_receipt() -> dict[str, Any]:
    issued = datetime.fromisoformat(
        AUTH_ISSUED_AT.replace("Z", "+00:00")
    ).timestamp()
    return {
        "source_id": "operator:gary-leckey",
        "source_timestamp": issued,
        "received_at": issued,
        "receipt_id": "operator-auth-receipt-20260811",
        "receipt_type": "owner_live_order_authorization",
        "data_status": "live",
        "truth_status": "real_operator",
        "generated_values": False,
        "authorization_id": AUTHORIZATION_ID,
        "intent_id": INTENT_ID,
        "owner": "Gary Leckey",
        "venue": "binance",
        "account_environment": "live_spot",
        "symbol": "BTCUSDT",
        "side_scope": ["BUY", "SELL"],
        "max_quote_notional": "10",
        "issued_at": AUTH_ISSUED_AT,
        "expires_at": AUTH_EXPIRES_AT,
        "authorized": True,
        "provider_submission_authorized": True,
        "one_cycle": True,
        "containment_exit_authorized": True,
        "leverage_allowed": False,
        "margin_allowed": False,
        "transfers_allowed": False,
        "secret": SECRET_SENTINEL,
    }


class CognitiveEvidence:
    def __init__(self, clock: MutableClock) -> None:
        self.clock = clock
        self.hnc_calls = 0
        self.auris_calls = 0
        self.disabled = False
        self.advisory = "TRADE"
        self.last_hnc: dict[str, Any] | None = None

    def hnc(self) -> dict[str, Any]:
        self.hnc_calls += 1
        if self.disabled:
            raise AssertionError("cognitive supplier must not reopen for exit")
        now = self.clock()
        receipt = {
            "source_id": "aureon:hnc:live",
            "source_timestamp": now - 1,
            "received_at": now,
            "receipt_id": f"hnc:live_field:{self.hnc_calls}",
            "receipt_type": "hnc_live_field",
            "input_receipt_ids": ["hnc-observed-input"],
            "data_status": "live",
            "truth_status": "real_derived",
            "generated_values": False,
            "equation_inputs_complete": True,
            "coherence_gamma": "0.97",
            "symbolic_life_score": "0.88",
            "action": False,
            "accounting": False,
            "learning": False,
            "secret": SECRET_SENTINEL,
        }
        receipt.update({key: False for key in _FALSE_COGNITIVE_ALIASES})
        self.last_hnc = receipt
        return receipt

    def auris(self) -> dict[str, Any]:
        self.auris_calls += 1
        if self.disabled:
            raise AssertionError("cognitive supplier must not reopen for exit")
        assert self.last_hnc is not None
        now = self.clock()
        receipt = {
            "source_id": "aureon:auris:live",
            "source_timestamp": now - 0.5,
            "received_at": now,
            "receipt_id": f"auris:cosmic_state:{self.auris_calls}",
            "receipt_type": "auris_cosmic_state",
            "input_receipt_ids": [
                self.last_hnc["receipt_id"], "planetary-observed-input",
            ],
            "hnc_receipt_id": self.last_hnc["receipt_id"],
            "data_status": "live",
            "truth_status": "real_derived",
            "generated_values": False,
            "equation_inputs_complete": True,
            "gate_open": True,
            "advisory": self.advisory,
            "action": False,
            "accounting": False,
            "learning": False,
            "secret": SECRET_SENTINEL,
        }
        receipt.update({key: False for key in _FALSE_COGNITIVE_ALIASES})
        return receipt


class FakeBinanceClient:
    dry_run = False
    use_testnet = False

    def __init__(
        self,
        clock: MutableClock,
        *,
        fee_rate: str = "0.001",
        balances: dict[str, list[str]] | None = None,
    ) -> None:
        self.clock = clock
        self.fee_rate = fee_rate
        self.balances = balances or {
            "USDT": ["100"],
            "BTC": ["1"],
        }
        self.balance_indexes = {"USDT": 0, "BTC": 0}
        self.calls: list[tuple[Any, ...]] = []
        self.place_calls: list[dict[str, Any]] = []
        self.readback_calls: list[dict[str, Any]] = []
        self.place_responses: list[Any] = []
        self.readback_responses: list[Any] = []
        self._pending_orders: dict[tuple[str, str, bool], dict[str, Any]] = {}
        self.sequence = 0
        self.permission_calls = 0
        self.permission_disabled = False
        self.permission_overrides: dict[str, Any] = {}
        self.permission_endpoint_calls: list[tuple[str, str]] = []

    def _receipt(self, kind: str, truth: str) -> dict[str, Any]:
        self.sequence += 1
        now = self.clock()
        return {
            "source_id": f"binance:{kind}",
            "source_timestamp": now - 1,
            "received_at": now,
            "receipt_id": f"binance:{kind}:{self.sequence}",
            "data_status": "live",
            "truth_status": truth,
            "generated_values": False,
            "secret": SECRET_SENTINEL,
        }

    def get_ticker(self, symbol: str) -> dict[str, Any]:
        self.calls.append(("ticker", symbol))
        return {
            **self._receipt("ticker", "real_observed"),
            "receipt_type": "binance_spot_ticker",
            "symbol": symbol,
            "price": "100000",
            "bid": "99900",
            "ask": "100000",
            "eligible_for_action": True,
        }

    def get_account_permission_receipt(self) -> dict[str, Any]:
        self.permission_calls += 1
        self.calls.append(("account_permission",))
        if self.permission_disabled:
            raise AssertionError(
                "permission supplier must not reopen after BUY submission"
            )
        self.permission_endpoint_calls.extend([
            ("GET", "/api/v3/account"),
            ("GET", "/sapi/v1/account/apiRestrictions"),
            ("GET", "/sapi/v1/account/apiTradingStatus"),
            ("GET", "/api/v3/time"),
        ])
        now = self.clock()
        server_time = int((now - 1) * 1000)
        permissions = ["SPOT", "TRD_GRP_001"]
        safety_flags = {
            name: True for name in _ACCOUNT_PERMISSION_TRUE_FLAGS
        }
        receipt_material = {
            "account_type": "SPOT",
            "permissions": permissions,
            "server_time": server_time,
            **safety_flags,
        }
        receipt_id = "binance:account_permission:" + hashlib.sha256(
            json.dumps(
                receipt_material,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
        receipt = {
            "source_id": (
                "binance:/api/v3/account"
                "+/sapi/v1/account/apiRestrictions"
                "+/sapi/v1/account/apiTradingStatus"
                "+/api/v3/time"
            ),
            "source_timestamp": server_time / 1000,
            "received_at": now,
            "receipt_id": receipt_id,
            "provider_receipt_type": (
                "Account+ApiRestrictions+ApiTradingStatus+Time"
            ),
            "data_status": "live",
            "truth_status": "real_provider",
            "generated_values": False,
            "account_type": "SPOT",
            "permissions": permissions,
            "server_time": server_time,
            **safety_flags,
            "safe_for_bounded_spot_buy": True,
            "eligible_for_action": True,
            "eligible_for_accounting": False,
            "eligible_for_learning": False,
            "action": False,
            "accounting": False,
            "learning": False,
            "secret": SECRET_SENTINEL,
        }
        receipt.update(self.permission_overrides)
        return receipt

    def get_asset_balance(self, asset: str) -> dict[str, Any]:
        self.calls.append(("balance", asset))
        values = self.balances[asset]
        index = self.balance_indexes[asset]
        if index >= len(values):
            raise AssertionError(f"unexpected {asset} balance read")
        self.balance_indexes[asset] += 1
        return {
            **self._receipt(f"balance:{asset}", "real_provider"),
            "receipt_type": "binance_spot_balance",
            "asset": asset,
            "free": values[index],
            "eligible_for_action": True,
        }

    def get_symbol_filters(
        self, symbol: str, force_refresh: bool = False,
    ) -> dict[str, Any]:
        self.calls.append(("filters", symbol, force_refresh))
        return {
            **self._receipt("filters", "real_observed"),
            "provider_receipt_type": "ExchangeInfo+Time",
            "symbol": symbol,
            "base_asset": "BTC",
            "quote_asset": "USDT",
            "step_size": "0.00000001",
            "min_qty": "0.00001",
            "max_qty": "100",
            "min_notional": "5",
            "base_precision": 8,
            "quote_precision": 8,
            "eligible_for_action": True,
        }

    def get_trade_fee_receipt(self, symbol: str) -> dict[str, Any]:
        self.calls.append(("fee", symbol))
        return {
            **self._receipt("fee", "real_provider"),
            "provider_receipt_type": "TradeFee+Time",
            "symbol": symbol,
            "maker_commission": self.fee_rate,
            "taker_commission": self.fee_rate,
            "eligible_for_action": True,
        }

    def adjust_quantity(self, symbol: str, quantity: Any) -> str:
        self.calls.append(("adjust_quantity", symbol, str(quantity)))
        step = Decimal("0.00000001")
        adjusted = (
            Decimal(str(quantity)) / step
        ).to_integral_value(rounding=ROUND_DOWN) * step
        return format(adjusted, "f")

    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: Any = None,
        quote_qty: Any = None,
        client_order_id: str | None = None,
    ) -> dict[str, Any]:
        call = {
            "symbol": symbol, "side": side, "quantity": quantity,
            "quote_qty": quote_qty, "client_order_id": client_order_id,
        }
        self.place_calls.append(call)
        if not self.place_responses:
            raise AssertionError("unexpected order mutation")
        response = self.place_responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response(call) if callable(response) else dict(response)

    def get_order_status(
        self,
        order_id: str | None = None,
        client_order_id: str | None = None,
        *,
        symbol: str | None = None,
        side: str | None = None,
        margin: bool = False,
    ) -> dict[str, Any]:
        call = {
            "order_id": order_id, "client_order_id": client_order_id,
            "symbol": symbol, "side": side, "margin": margin,
        }
        self.readback_calls.append(call)
        if not self.readback_responses:
            raise AssertionError("unexpected order readback")
        response = self.readback_responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response(call) if callable(response) else dict(response)


def terminal_fill(
    clock: MutableClock,
    *,
    side: str,
    client_order_id: str,
    order_id: str,
    qty: str,
    notional: str,
    fee: str,
    fee_asset: str,
) -> dict[str, Any]:
    observed = clock() - 0.25
    price = Decimal(notional) / Decimal(qty)
    return {
        "symbol": "BTCUSDT",
        "side": side,
        "orderId": order_id,
        "provider_order_id": order_id,
        "clientOrderId": client_order_id,
        "provider_client_order_id": client_order_id,
        "status": "FILLED",
        "provider_status": "FILLED",
        "data_status": "live",
        "truth_status": "real_observed",
        "generated_values": False,
        "source_id": f"binance:order:{order_id}:trades",
        "source_timestamp": observed,
        "provider_timestamp": observed,
        "received_at": clock(),
        "receipt_id": f"binance:fill:{order_id}",
        "fills": [{
            "orderId": order_id,
            "tradeId": f"trade-{order_id}",
            "qty": qty,
            "price": format(price, "f"),
            "commission": fee,
            "commissionAsset": fee_asset,
            "source_timestamp": observed,
            "provider_timestamp": observed,
            "truth_status": "real_observed",
            "generated_values": False,
            "secret": SECRET_SENTINEL,
        }],
        "executedQty": qty,
        "filled_qty": qty,
        "cummulativeQuoteQty": notional,
        "filled_notional": notional,
        "avgPrice": format(price, "f"),
        "avg_fill_price": format(price, "f"),
        "filled_avg_price": format(price, "f"),
        "fee": fee,
        "fees": fee,
        "fee_asset": fee_asset,
        "fee_currency": fee_asset,
        "fill_receipt_complete": True,
        "submitted": True,
        "submission_acknowledged": True,
        "reconciliation_required": False,
        "eligible_for_action": False,
        "eligible_for_accounting": True,
        "eligible_for_learning": True,
        "secret": SECRET_SENTINEL,
    }


def acknowledgement(
    clock: MutableClock,
    *,
    side: str,
    client_order_id: str,
) -> dict[str, Any]:
    observed = clock() - 0.25
    return {
        "symbol": "BTCUSDT",
        "side": side,
        "orderId": f"ack-{side.lower()}",
        "clientOrderId": client_order_id,
        "status": "NEW",
        "provider_status": "NEW",
        "data_status": "live",
        "truth_status": "real_observed",
        "generated_values": False,
        "source_id": f"binance:order:ack-{side.lower()}",
        "source_timestamp": observed,
        "received_at": clock(),
        "receipt_id": f"binance:ack:{side.lower()}",
        "fill_receipt_complete": False,
        "submitted": True,
        "submission_acknowledged": True,
        "reconciliation_required": True,
        "eligible_for_action": False,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
        "secret": SECRET_SENTINEL,
    }


def make_runner(
    tmp_path: Path,
    client: FakeBinanceClient,
    clock: MutableClock,
    *,
    cognitive: CognitiveEvidence | None = None,
    economic_boundary: EconomicGovernanceBoundary | None | object = (
        _DEFAULT_BOUNDARY
    ),
) -> tuple[
    BoundedBinanceRoundTrip, Path, CognitiveEvidence, dict[str, Any], str
]:
    cognitive = cognitive or CognitiveEvidence(clock)
    state_path = cycle_state_path(
        tmp_path / "state",
        intent_id=INTENT_ID,
        authorization_id=AUTHORIZATION_ID,
    )
    if economic_boundary is _DEFAULT_BOUNDARY:
        economic_boundary = bind_economic_governance_boundary(
            council_receipt_supplier=FakeCouncilSupplier(),
            crown_receipt_supplier=FakeCrownSupplier(),
            trusted_council_supplier_ids=frozenset({
                COUNCIL_SUPPLIER_ID,
            }),
            trusted_crown_supplier_ids=frozenset({
                CROWN_SUPPLIER_ID,
            }),
            clock=clock,
            permit_ttl_s=2.0,
            warrant_ttl_s=30.0,
            provider_max_age_s=300.0,
            governance_max_age_s=300.0,
        )
    contingency_recovery = (
        bind_durable_contingency_recovery(
            adapter_id='adapter:bounded-binance-recovery:v1',
            trusted_adapter_ids=frozenset({
                'adapter:bounded-binance-recovery:v1',
            }),
            boundary=economic_boundary,
            store_path=state_path.with_name(
                state_path.stem + '.contingency.json'
            ),
            clock=clock,
            claim_ttl_s=5.0,
        )
        if isinstance(economic_boundary, EconomicGovernanceBoundary)
        else None
    )
    runner = BoundedBinanceRoundTrip(
        client,
        state_path=state_path,
        hnc_receipt_supplier=cognitive.hnc,
        auris_receipt_supplier=cognitive.auris,
        economic_boundary=economic_boundary,
        contingency_recovery=contingency_recovery,
        clock=clock,
    )
    authorization = authorization_receipt()
    token = expected_confirmation_token(AUTHORIZATION_ID)
    return runner, state_path, cognitive, authorization, token


def preflight(
    runner: BoundedBinanceRoundTrip,
    authorization: dict[str, Any],
    token: str,
) -> dict[str, Any]:
    return runner.read_only_preflight(
        authorization_receipt=authorization,
        confirmation_token=token,
        max_quote="10",
    )


def test_default_cli_is_inert(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "inert"
    assert payload["provider_calls"] == 0
    assert payload["order_calls"] == 0


def test_wrong_confirmation_rejects_before_all_evidence_calls(
    tmp_path: Path,
) -> None:
    clock = MutableClock()
    client = FakeBinanceClient(clock)
    runner, state_path, cognitive, authorization, _ = make_runner(
        tmp_path, client, clock,
    )

    result = runner.read_only_preflight(
        authorization_receipt=authorization,
        confirmation_token="wrong-token",
        max_quote="10",
    )

    assert result["reason"] == "exact_confirmation_token_required"
    assert client.calls == []
    assert cognitive.hnc_calls == 0
    assert cognitive.auris_calls == 0
    assert not state_path.exists()


def test_missing_economic_boundary_never_reaches_provider(
    tmp_path: Path,
) -> None:
    clock = MutableClock()
    client = FakeBinanceClient(clock)
    runner, state_path, _, authorization, token = make_runner(
        tmp_path,
        client,
        clock,
        economic_boundary=None,
    )
    assert preflight(runner, authorization, token)['status'] == 'prepared'

    result = runner.advance(
        authorization_receipt=authorization,
        confirmation_token=token,
    )
    state = _read_verified_state(state_path)

    assert result['reason'] == (
        'trusted_economic_governance_boundary_required'
    )
    assert client.place_calls == []
    assert state is not None
    assert state['stage'] == 'entry_reserved'


def test_replacement_authorization_receipt_is_not_equivalent(
    tmp_path: Path,
) -> None:
    clock = MutableClock()
    client = FakeBinanceClient(clock)
    runner, _, _, authorization, token = make_runner(
        tmp_path,
        client,
        clock,
    )
    assert preflight(runner, authorization, token)['status'] == 'prepared'
    replacement = dict(authorization)
    replacement['receipt_id'] = 'operator-auth-receipt-replacement'

    result = runner.advance(
        authorization_receipt=replacement,
        confirmation_token=token,
    )

    assert result['reason'] == 'persisted_authorization_scope_mismatch'
    assert client.place_calls == []


@pytest.mark.parametrize(
    'outcome',
    ['HOLD', 'ABORT', 'NO_DATA', 'STALE', 'TAMPERED'],
)
def test_non_accept_stale_or_tampered_dual_voice_calls_no_provider(
    tmp_path: Path,
    dual_harness: FakeDualVoiceRuntime,
    outcome: str,
) -> None:
    clock = MutableClock()
    client = FakeBinanceClient(clock)
    runner, state_path, _, authorization, token = make_runner(
        tmp_path,
        client,
        clock,
    )
    assert preflight(runner, authorization, token)['status'] == 'prepared'
    dual_harness.outcome = outcome

    result = runner.advance(
        authorization_receipt=authorization,
        confirmation_token=token,
    )
    state = _read_verified_state(state_path)
    boundary = runner.economic_boundary

    assert result['reason'] == 'strict_dual_economic_governance_required'
    assert client.place_calls == []
    assert len(dual_harness.calls) == 1
    assert isinstance(boundary, EconomicGovernanceBoundary)
    assert boundary._council_supplier.calls == 1
    assert boundary._crown_supplier.calls == 1
    assert state is not None
    assert state['stage'] == 'entry_governance_blocked'
    assert state['mutation_count'] == 0


def test_exact_accept_binds_and_journals_one_provider_call(
    tmp_path: Path,
    dual_harness: FakeDualVoiceRuntime,
) -> None:
    clock = MutableClock()
    client = FakeBinanceClient(clock)
    runner, state_path, _, authorization, token = make_runner(
        tmp_path,
        client,
        clock,
    )
    client.place_responses = [lambda call: acknowledgement(
        clock,
        side='BUY',
        client_order_id=call['client_order_id'],
    )]
    assert preflight(runner, authorization, token)['status'] == 'prepared'

    result = runner.advance(
        authorization_receipt=authorization,
        confirmation_token=token,
    )
    state = _read_verified_state(state_path)
    boundary = runner.economic_boundary

    assert result['status'] == 'entry_pending'
    assert len(client.place_calls) == 1
    assert len(dual_harness.calls) == 2
    assert isinstance(boundary, EconomicGovernanceBoundary)
    assert boundary._council_supplier.calls == 2
    assert boundary._crown_supplier.calls == 2
    assert state is not None
    intent = state['entry_economic_intent']
    lineage = state['entry_economic_governance']
    assert intent['method'] == 'POST'
    assert intent['path'] == '/api/v3/order'
    assert intent['request_body'] == {
        'symbol': 'BTCUSDT',
        'side': 'BUY',
        'type': 'MARKET',
        'newOrderRespType': 'FULL',
        'newClientOrderId': state['entry_client_order_id'],
        'quoteOrderQty': state['entry_quote_order_qty'],
    }
    assert intent['authorization_receipt_id'] == (
        state['authorization']['receipt_id']
    )
    assert intent['cycle_id'].endswith(state_path.stem)
    assert intent['position_receipt_id'] == (
        state['pre_entry_base_account_receipt']['receipt_id']
    )
    assert intent['hnc_receipt_id'] == state['hnc_receipt']['receipt_id']
    assert intent['auris_receipt_id'] == state['auris_receipt']['receipt_id']
    expected_intent_digest = hashlib.sha256(json.dumps(
        intent,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False,
        allow_nan=False,
    ).encode('utf-8')).hexdigest()
    assert lineage['intent_digest'] == expected_intent_digest
    assert lineage['proposal_digest']
    assert lineage['dual_receipt_id']
    assert lineage['permit_id']
    assert lineage['consume_status'] == 'consumed_transport_returned'
    assert lineage['economic_mutation'] is False
    events = [
        json.loads(line)
        for line in state_path.with_name(
            state_path.stem + '.events.jsonl'
        ).read_text(encoding='utf-8').splitlines()
    ]
    assert events[-1]['economic_lineage']['entry']['intent_digest'] == (
        lineage['intent_digest']
    )
    assert SECRET_SENTINEL not in json.dumps(state)


@pytest.mark.parametrize('drift', ['path', 'body'])
def test_last_mile_path_or_body_drift_burns_without_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    drift: str,
) -> None:
    clock = MutableClock()
    client = FakeBinanceClient(clock)
    runner, state_path, _, authorization, token = make_runner(
        tmp_path,
        client,
        clock,
    )
    assert preflight(runner, authorization, token)['status'] == 'prepared'
    boundary = runner.economic_boundary
    assert isinstance(boundary, EconomicGovernanceBoundary)
    original = boundary.consume_and_call

    def consume_with_drift(
        permit: Any,
        *,
        method: str,
        path: str,
        body: dict[str, Any],
        transport: Any,
    ) -> Any:
        changed_body = dict(body)
        changed_path = path
        if drift == 'path':
            changed_path = '/api/v3/order/other'
        else:
            changed_body['quoteOrderQty'] = '9'
        return original(
            permit,
            method=method,
            path=changed_path,
            body=changed_body,
            transport=transport,
        )

    monkeypatch.setattr(boundary, 'consume_and_call', consume_with_drift)
    result = runner.advance(
        authorization_receipt=authorization,
        confirmation_token=token,
    )
    state = _read_verified_state(state_path)

    assert result['reason'] == 'exact_last_mile_economic_binding_required'
    assert client.place_calls == []
    assert state is not None
    assert state['entry_economic_governance']['consume_status'] == (
        'burned_without_provider_call'
    )


def test_consumed_permit_replay_cannot_call_provider_again(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = MutableClock()
    client = FakeBinanceClient(clock)
    runner, _, _, authorization, token = make_runner(
        tmp_path,
        client,
        clock,
    )
    client.place_responses = [lambda call: acknowledgement(
        clock,
        side='BUY',
        client_order_id=call['client_order_id'],
    )]
    assert preflight(runner, authorization, token)['status'] == 'prepared'
    boundary = runner.economic_boundary
    assert isinstance(boundary, EconomicGovernanceBoundary)
    original = boundary.consume_and_call
    captured: dict[str, Any] = {}

    def capture_consume(
        permit: Any,
        *,
        method: str,
        path: str,
        body: dict[str, Any],
        transport: Any,
    ) -> Any:
        captured.update({
            'permit': permit,
            'method': method,
            'path': path,
            'body': dict(body),
        })
        return original(
            permit,
            method=method,
            path=path,
            body=body,
            transport=transport,
        )

    monkeypatch.setattr(boundary, 'consume_and_call', capture_consume)
    assert runner.advance(
        authorization_receipt=authorization,
        confirmation_token=token,
    )['status'] == 'entry_pending'
    replay_calls: list[bool] = []

    with pytest.raises(EconomicGovernanceBlocked, match='replayed'):
        original(
            captured['permit'],
            method=captured['method'],
            path=captured['path'],
            body=captured['body'],
            transport=lambda: replay_calls.append(True),
        )

    assert len(client.place_calls) == 1
    assert replay_calls == []


def test_observe_advisory_vetoes_entry_without_state_or_order(
    tmp_path: Path,
) -> None:
    clock = MutableClock()
    client = FakeBinanceClient(clock)
    cognitive = CognitiveEvidence(clock)
    cognitive.advisory = "OBSERVE"
    runner, state_path, _, authorization, token = make_runner(
        tmp_path, client, clock, cognitive=cognitive,
    )

    result = preflight(runner, authorization, token)

    assert result["reason"] == "hnc_auris_cognitive_gate_closed"
    assert client.place_calls == []
    assert not state_path.exists()


def test_unsafe_account_permission_receipt_vetoes_preflight(
    tmp_path: Path,
) -> None:
    clock = MutableClock()
    client = FakeBinanceClient(clock)
    client.permission_overrides["safe_for_bounded_spot_buy"] = False
    runner, state_path, _, authorization, token = make_runner(
        tmp_path, client, clock,
    )

    result = preflight(runner, authorization, token)

    assert result["reason"] == (
        "fresh_safe_binance_account_permission_receipt_required"
    )
    assert client.permission_calls == 1
    assert client.permission_endpoint_calls == [
        ("GET", "/api/v3/account"),
        ("GET", "/sapi/v1/account/apiRestrictions"),
        ("GET", "/sapi/v1/account/apiTradingStatus"),
        ("GET", "/api/v3/time"),
    ]
    assert client.place_calls == []
    assert not state_path.exists()


def test_preflight_durably_reserves_fee_inclusive_private_action(
    tmp_path: Path,
) -> None:
    clock = MutableClock()
    client = FakeBinanceClient(clock)
    runner, state_path, _, authorization, token = make_runner(
        tmp_path, client, clock,
    )

    result = preflight(runner, authorization, token)
    state = _read_verified_state(state_path)

    assert result["status"] == "prepared"
    assert state is not None
    assert state["stage"] == "entry_reserved"
    assert state["entry_cutoff_at"] == ENTRY_CUTOFF_AT
    assert state_path.parent.name == "bounded_binance_roundtrip"
    assert len(state_path.stem) == 64
    assert (
        Decimal(state["entry_quote_order_qty"])
        + Decimal(state["reserved_quote_fee"])
        <= Decimal("10")
    )
    assert state["entry_action_receipt"]["eligible_for_action"] is True
    permission = state["account_permission_receipt"]
    permission_id = permission["receipt_id"]
    assert result["account_permission_receipt_id"] == permission_id
    assert permission["safe_for_bounded_spot_buy"] is True
    assert (
        state["entry_action_receipt"]["account_permission_receipt_id"]
        == permission_id
    )
    assert (
        state["entry_action_receipt"]["input_receipt_ids"].count(permission_id)
        == 1
    )
    assert client.permission_calls == 1
    assert state["hnc_receipt"]["eligible_for_action"] is False
    assert state["auris_receipt"]["eligible_for_action"] is False
    assert all(
        state["hnc_receipt"][key] is False
        and state["auris_receipt"][key] is False
        for key in _FALSE_COGNITIVE_ALIASES
    )
    assert SECRET_SENTINEL not in json.dumps(state)
    event_lines = state_path.with_name(
        state_path.stem + ".events.jsonl"
    ).read_text(encoding="utf-8").splitlines()
    assert len(event_lines) == 1


def test_validly_resealed_legacy_state_without_permission_fails_before_buy(
    tmp_path: Path,
) -> None:
    clock = MutableClock()
    client = FakeBinanceClient(clock)
    runner, state_path, _, authorization, token = make_runner(
        tmp_path, client, clock,
    )
    assert preflight(runner, authorization, token)["status"] == "prepared"
    state = _read_verified_state(state_path)
    assert state is not None
    permission_id = state["account_permission_receipt"]["receipt_id"]
    state.pop("account_permission_receipt")
    action = state["entry_action_receipt"]
    action.pop("account_permission_receipt_id")
    action["input_receipt_ids"] = [
        value for value in action["input_receipt_ids"]
        if value != permission_id
    ]
    runner._save(state)

    result = runner.advance(
        authorization_receipt=authorization,
        confirmation_token=token,
    )

    assert result["reason"] == (
        "persisted_account_permission_receipt_required"
    )
    assert client.permission_calls == 1
    assert client.place_calls == []


@pytest.mark.parametrize(
    "mutation", ["stale", "hash_material", "receipt_id"],
)
def test_stale_or_tampered_persisted_permission_fails_before_buy(
    tmp_path: Path,
    mutation: str,
) -> None:
    clock = MutableClock()
    client = FakeBinanceClient(clock)
    runner, state_path, _, authorization, token = make_runner(
        tmp_path, client, clock,
    )
    assert preflight(runner, authorization, token)["status"] == "prepared"
    state = _read_verified_state(state_path)
    assert state is not None
    permission = state["account_permission_receipt"]
    if mutation == "stale":
        permission["source_timestamp"] = clock() - 61
    elif mutation == "hash_material":
        permission["permissions"] = ["MARGIN", "SPOT"]
    else:
        permission["receipt_id"] = "binance:account_permission:tampered"
    runner._save(state)

    result = runner.advance(
        authorization_receipt=authorization,
        confirmation_token=token,
    )

    assert result["reason"] == (
        "persisted_account_permission_receipt_required"
    )
    assert client.permission_calls == 1
    assert client.place_calls == []


@pytest.mark.parametrize("missing_link", ["field", "input"])
def test_buy_action_requires_exact_persisted_permission_link(
    tmp_path: Path,
    missing_link: str,
) -> None:
    clock = MutableClock()
    client = FakeBinanceClient(clock)
    runner, state_path, _, authorization, token = make_runner(
        tmp_path, client, clock,
    )
    assert preflight(runner, authorization, token)["status"] == "prepared"
    state = _read_verified_state(state_path)
    assert state is not None
    permission_id = state["account_permission_receipt"]["receipt_id"]
    action = state["entry_action_receipt"]
    if missing_link == "field":
        action.pop("account_permission_receipt_id")
    else:
        action["input_receipt_ids"] = [
            value for value in action["input_receipt_ids"]
            if value != permission_id
        ]
    runner._save(state)

    result = runner.advance(
        authorization_receipt=authorization,
        confirmation_token=token,
    )

    assert result["reason"] == (
        "entry_action_must_link_account_permission_receipt"
    )
    assert client.permission_calls == 1
    assert client.place_calls == []


def test_ambiguous_entry_restarts_and_reconciles_without_duplicate(
    tmp_path: Path,
) -> None:
    clock = MutableClock()
    first_client = FakeBinanceClient(clock)
    runner, state_path, cognitive, authorization, token = make_runner(
        tmp_path, first_client, clock,
    )
    assert preflight(runner, authorization, token)["status"] == "prepared"
    first_client.place_responses = [TimeoutError("transport ambiguity")]

    pending = runner.advance(
        authorization_receipt=authorization,
        confirmation_token=token,
    )
    state = _read_verified_state(state_path)

    assert pending["status"] == "entry_pending"
    assert len(first_client.place_calls) == 1
    assert state is not None
    client_order_id = state["entry_client_order_id"]
    assert state["mutation_count"] == 1

    restarted_client = FakeBinanceClient(clock)
    restarted_client.readback_responses = [lambda call: terminal_fill(
        clock,
        side="BUY",
        client_order_id=call["client_order_id"],
        order_id="entry-order",
        qty="0.00009980",
        notional="9.98",
        fee="0.00998",
        fee_asset="USDT",
    )]
    restarted, _, _, _, _ = make_runner(
        tmp_path, restarted_client, clock, cognitive=cognitive,
    )

    reconciled = restarted.advance(
        authorization_receipt=authorization,
        confirmation_token=token,
    )
    final_state = _read_verified_state(state_path)

    assert reconciled["status"] == "entry_filled"
    assert restarted_client.place_calls == []
    assert len(restarted_client.readback_calls) == 1
    assert restarted_client.readback_calls[0]["order_id"] is None
    assert (
        restarted_client.readback_calls[0]["client_order_id"]
        == client_order_id
    )
    assert final_state is not None
    assert final_state["mutation_count"] == 1
    assert final_state["order_readback_count"] == 1


def test_ack_remains_pending_and_each_advance_reads_back_at_most_once(
    tmp_path: Path,
) -> None:
    clock = MutableClock()
    client = FakeBinanceClient(clock)
    runner, _, _, authorization, token = make_runner(
        tmp_path, client, clock,
    )
    assert preflight(runner, authorization, token)["status"] == "prepared"
    client.place_responses = [lambda call: acknowledgement(
        clock,
        side="BUY",
        client_order_id=call["client_order_id"],
    )]
    first = runner.advance(
        authorization_receipt=authorization,
        confirmation_token=token,
    )
    client.readback_responses = [lambda call: acknowledgement(
        clock,
        side="BUY",
        client_order_id=call["client_order_id"],
    )]
    second = runner.advance(
        authorization_receipt=authorization,
        confirmation_token=token,
    )

    assert first["status"] == "entry_pending"
    assert second["status"] == "entry_pending"
    assert len(client.place_calls) == 1
    assert len(client.readback_calls) == 1
    assert second["provider_receipt"]["eligible_for_accounting"] is False


@pytest.mark.parametrize('mutation', ['excess', 'wrong_position'])
def test_containment_warrant_rejects_excess_or_wrong_position(
    tmp_path: Path,
    mutation: str,
) -> None:
    clock = MutableClock()
    client = FakeBinanceClient(
        clock,
        balances={
            'USDT': ['100'],
            'BTC': ['1', '1.00009980'],
        },
    )
    runner, state_path, _, authorization, token = make_runner(
        tmp_path,
        client,
        clock,
    )
    client.place_responses = [lambda call: terminal_fill(
        clock,
        side='BUY',
        client_order_id=call['client_order_id'],
        order_id='entry-order',
        qty='0.00009980',
        notional='9.98',
        fee='0.00998',
        fee_asset='USDT',
    )]
    assert preflight(runner, authorization, token)['status'] == 'prepared'
    assert runner.advance(
        authorization_receipt=authorization,
        confirmation_token=token,
    )['status'] == 'entry_filled'
    assert runner.advance(
        authorization_receipt=authorization,
        confirmation_token=token,
    )['status'] == 'exit_prepared'
    state = _read_verified_state(state_path)
    assert state is not None
    if mutation == 'excess':
        observed = (
            Decimal(state['post_entry_base_account_receipt']['free'])
            - Decimal(state['pre_entry_base_account_receipt']['free'])
        )
        state['sell_quantity'] = format(observed * 2, 'f')
    else:
        state['post_entry_base_account_receipt']['receipt_id'] = (
            state['pre_entry_base_account_receipt']['receipt_id']
        )
    runner._save(state)
    calls_before = len(client.place_calls)

    result = runner.advance(
        authorization_receipt=authorization,
        confirmation_token=token,
    )
    final_state = _read_verified_state(state_path)

    assert len(client.place_calls) == calls_before == 1
    assert result['reason'] in {
        'strict_dual_economic_governance_required',
        'exact_economic_intent_lineage_required',
    }
    assert final_state is not None
    assert final_state['stage'] == 'containment_blocked'
    assert final_state['mutation_count'] == 1


def test_full_roundtrip_uses_stored_cognitive_lineage_and_exact_accounting(
    tmp_path: Path,
    dual_harness: FakeDualVoiceRuntime,
) -> None:
    clock = MutableClock()
    client = FakeBinanceClient(
        clock,
        balances={
            "USDT": ["100", "99.97005"],
            "BTC": ["1", "1.00009980", "1"],
        },
    )
    runner, state_path, cognitive, authorization, token = make_runner(
        tmp_path, client, clock,
    )
    client.place_responses = [
        lambda call: terminal_fill(
            clock,
            side="BUY",
            client_order_id=call["client_order_id"],
            order_id="entry-order",
            qty="0.00009980",
            notional="9.98",
            fee="0.00998",
            fee_asset="USDT",
        ),
        lambda call: terminal_fill(
            clock,
            side="SELL",
            client_order_id=call["client_order_id"],
            order_id="exit-order",
            qty="0.00009980",
            notional="9.97",
            fee="0.00997",
            fee_asset="USDT",
        ),
    ]

    assert preflight(runner, authorization, token)["status"] == "prepared"
    assert runner.advance(
        authorization_receipt=authorization,
        confirmation_token=token,
    )["status"] == "entry_filled"
    client.permission_disabled = True
    cognitive.disabled = True
    prepared_exit = runner.advance(
        authorization_receipt=authorization,
        confirmation_token=token,
    )
    assert prepared_exit["status"] == "exit_prepared"
    assert prepared_exit["cognitive_gate_required"] is True
    assert prepared_exit['economic_dual_voice_required'] is True
    assert prepared_exit['contingency_warrant_required'] is True
    assert runner.advance(
        authorization_receipt=authorization,
        confirmation_token=token,
    )["status"] == "exit_filled"
    completed = runner.advance(
        authorization_receipt=authorization,
        confirmation_token=token,
    )
    state = _read_verified_state(state_path)

    assert completed["status"] == "complete"
    assert Decimal(completed["post_exit_btc_delta"]) == Decimal("0")
    assert completed["post_exit_usdt_delta"] == "-0.02995"
    assert completed["quote_net_pnl"] == "-0.02995"
    assert completed["quote_net_pnl_status"] == "complete"
    assert completed["cap_compliant"] is True
    assert cognitive.hnc_calls == 1
    assert cognitive.auris_calls == 1
    assert client.permission_calls == 1
    assert client.permission_endpoint_calls == [
        ("GET", "/api/v3/account"),
        ("GET", "/sapi/v1/account/apiRestrictions"),
        ("GET", "/sapi/v1/account/apiTradingStatus"),
        ("GET", "/api/v3/time"),
    ]
    assert [call["side"] for call in client.place_calls] == ["BUY", "SELL"]
    assert state is not None
    assert state["mutation_count"] == 2
    assert state["exit_action_receipt"]["entry_receipt_id"] == (
        state["entry_receipt"]["receipt_id"]
    )
    assert "account_permission_receipt_id" not in state["exit_action_receipt"]
    assert len(dual_harness.calls) == 2
    boundary = runner.economic_boundary
    assert isinstance(boundary, EconomicGovernanceBoundary)
    assert boundary._council_supplier.calls == 2
    assert boundary._crown_supplier.calls == 2
    entry_lineage = state['entry_economic_governance']
    exit_lineage = state['exit_economic_governance']
    exit_intent = state['exit_economic_intent']
    assert entry_lineage['permit_kind'] == 'fresh_dual_accept'
    assert exit_lineage['permit_kind'] == (
        'durable_contingency_reduction'
    )
    assert entry_lineage['contingency_warrant']['dual_receipt_json']
    assert entry_lineage['contingency_scope'][
        'entry_intent_digest'
    ] == entry_lineage['intent_digest']
    assert entry_lineage['contingency_recovery_record_digest']
    assert entry_lineage[
        'contingency_recovery_route_binding_anchor'
    ]
    assert exit_lineage['contingency_warrant_id']
    assert exit_lineage['contingency_scope_digest']
    assert exit_lineage['consume_status'] == 'consumed_transport_returned'
    assert exit_intent['parent_intent_digest'] == (
        entry_lineage['intent_digest']
    )
    assert exit_intent['entry_receipt_id'] == (
        state['entry_receipt']['receipt_id']
    )
    assert exit_intent['position_receipt_id'] == (
        state['post_entry_base_account_receipt']['receipt_id']
    )
    assert exit_intent['reduce_only'] is True
    assert 'reduceOnly' not in exit_intent['request_body']
    assert Decimal(exit_intent['quantity']) <= Decimal(
        exit_intent['observed_exposure_quantity']
    )
    assert SECRET_SENTINEL not in json.dumps(state)


def test_fresh_restart_recovers_warrant_without_reopening_any_voice(
    tmp_path: Path,
    dual_harness: FakeDualVoiceRuntime,
) -> None:
    clock = MutableClock()
    entry_client = FakeBinanceClient(
        clock,
        balances={'USDT': ['100'], 'BTC': ['1']},
    )
    runner, state_path, cognitive, authorization, token = make_runner(
        tmp_path,
        entry_client,
        clock,
    )
    entry_client.place_responses = [lambda call: terminal_fill(
        clock,
        side='BUY',
        client_order_id=call['client_order_id'],
        order_id='entry-order',
        qty='0.00009980',
        notional='9.98',
        fee='0.00998',
        fee_asset='USDT',
    )]

    assert preflight(runner, authorization, token)['status'] == 'prepared'
    assert runner.advance(
        authorization_receipt=authorization,
        confirmation_token=token,
    )['status'] == 'entry_filled'
    first_boundary = runner.economic_boundary
    assert isinstance(first_boundary, EconomicGovernanceBoundary)
    assert len(dual_harness.calls) == 2
    assert first_boundary._council_supplier.calls == 2
    assert first_boundary._crown_supplier.calls == 2
    cognitive.disabled = True
    entry_client.permission_disabled = True

    exit_client = FakeBinanceClient(
        clock,
        balances={
            'USDT': ['99.97005'],
            'BTC': ['1.00009980', '1'],
        },
    )
    exit_client.permission_disabled = True
    exit_client.place_responses = [lambda call: terminal_fill(
        clock,
        side='SELL',
        client_order_id=call['client_order_id'],
        order_id='exit-order',
        qty='0.00009980',
        notional='9.97',
        fee='0.00997',
        fee_asset='USDT',
    )]
    restarted_cognitive = CognitiveEvidence(clock)
    restarted_cognitive.disabled = True
    restarted, _, _, _, _ = make_runner(
        tmp_path,
        exit_client,
        clock,
        cognitive=restarted_cognitive,
    )
    restarted_boundary = restarted.economic_boundary
    assert isinstance(restarted_boundary, EconomicGovernanceBoundary)

    assert restarted.advance(
        authorization_receipt=authorization,
        confirmation_token=token,
    )['status'] == 'exit_prepared'
    assert restarted.advance(
        authorization_receipt=authorization,
        confirmation_token=token,
    )['status'] == 'exit_filled'
    completed = restarted.advance(
        authorization_receipt=authorization,
        confirmation_token=token,
    )
    state = _read_verified_state(state_path)

    assert completed['status'] == 'complete'
    assert [call['side'] for call in entry_client.place_calls] == ['BUY']
    assert [call['side'] for call in exit_client.place_calls] == ['SELL']
    assert restarted_cognitive.hnc_calls == 0
    assert restarted_cognitive.auris_calls == 0
    assert exit_client.permission_calls == 0
    assert len(dual_harness.calls) == 2
    assert restarted_boundary._council_supplier.calls == 0
    assert restarted_boundary._crown_supplier.calls == 0
    assert state is not None
    assert state['exit_economic_governance']['permit_kind'] == (
        'durable_contingency_reduction'
    )
    assert state['exit_economic_governance']['consume_status'] == (
        'consumed_transport_returned'
    )


def test_nonquote_fees_leave_quote_pnl_uncomputed(
    tmp_path: Path,
) -> None:
    clock = MutableClock()
    client = FakeBinanceClient(
        clock,
        balances={
            "USDT": ["100", "99.99"],
            "BTC": ["1", "1.00009980", "1"],
        },
    )
    runner, _, _, authorization, token = make_runner(
        tmp_path, client, clock,
    )
    client.place_responses = [
        lambda call: terminal_fill(
            clock,
            side="BUY",
            client_order_id=call["client_order_id"],
            order_id="entry-bnb-fee",
            qty="0.00009980",
            notional="9.98",
            fee="0.00001",
            fee_asset="BNB",
        ),
        lambda call: terminal_fill(
            clock,
            side="SELL",
            client_order_id=call["client_order_id"],
            order_id="exit-bnb-fee",
            qty="0.00009980",
            notional="9.97",
            fee="0.00001",
            fee_asset="BNB",
        ),
    ]

    assert preflight(runner, authorization, token)["status"] == "prepared"
    for expected in ("entry_filled", "exit_prepared", "exit_filled"):
        assert runner.advance(
            authorization_receipt=authorization,
            confirmation_token=token,
        )["status"] == expected
    completed = runner.advance(
        authorization_receipt=authorization,
        confirmation_token=token,
    )

    assert completed["status"] == "complete"
    assert completed["quote_net_pnl"] is None
    assert completed["quote_net_pnl_status"] == (
        "no_data_nonquote_fee_conversion_receipt_required"
    )
    assert {row["asset"] for row in completed["nonquote_fees"]} == {"BNB"}


def test_new_entry_cutoff_blocks_preflight_and_reserved_buy(
    tmp_path: Path,
) -> None:
    cutoff = datetime.fromisoformat(
        ENTRY_CUTOFF_AT.replace("Z", "+00:00")
    ).timestamp()
    clock = MutableClock(cutoff)
    client = FakeBinanceClient(clock)
    runner, state_path, cognitive, authorization, token = make_runner(
        tmp_path / "direct", client, clock,
    )

    rejected = preflight(runner, authorization, token)
    assert rejected["reason"] == "new_entry_window_closed"
    assert client.calls == []
    assert cognitive.hnc_calls == 0
    assert not state_path.exists()

    clock.value = NOW
    client2 = FakeBinanceClient(clock)
    runner2, _, _, authorization2, token2 = make_runner(
        tmp_path / "reserved", client2, clock,
    )
    assert preflight(
        runner2, authorization2, token2,
    )["status"] == "prepared"
    clock.value = cutoff
    blocked = runner2.advance(
        authorization_receipt=authorization2,
        confirmation_token=token2,
    )
    assert blocked["reason"] == "new_entry_window_closed"
    assert client2.place_calls == []


def test_high_fee_or_filter_constraint_aborts_without_mutation(
    tmp_path: Path,
) -> None:
    clock = MutableClock()
    client = FakeBinanceClient(clock, fee_rate="0.95")
    runner, state_path, _, authorization, token = make_runner(
        tmp_path, client, clock,
    )

    result = preflight(runner, authorization, token)

    assert result["reason"] == (
        "fee_inclusive_cap_cannot_support_buffered_entry_and_exit"
    )
    assert client.place_calls == []
    assert not state_path.exists()


def test_corrupt_journal_fails_closed_without_provider_or_order_call(
    tmp_path: Path,
) -> None:
    clock = MutableClock()
    client = FakeBinanceClient(clock)
    runner, state_path, _, authorization, token = make_runner(
        tmp_path, client, clock,
    )
    assert preflight(runner, authorization, token)["status"] == "prepared"
    event_path = state_path.with_name(state_path.stem + ".events.jsonl")
    event = json.loads(event_path.read_text(encoding="utf-8"))
    event["recorded_at"] += 1
    event_path.write_text(json.dumps(event) + "\n", encoding="utf-8")

    restarted_client = FakeBinanceClient(clock)
    restarted, _, _, _, _ = make_runner(
        tmp_path, restarted_client, clock,
    )
    result = restarted.advance(
        authorization_receipt=authorization,
        confirmation_token=token,
    )

    assert result["reason"] == "durable_cycle_state_unavailable"
    assert restarted_client.calls == []
    assert restarted_client.place_calls == []
    assert restarted_client.readback_calls == []


def test_pending_snapshot_recursively_allowlists_provider_fill_fields(
    tmp_path: Path,
) -> None:
    clock = MutableClock()
    client = FakeBinanceClient(clock)
    runner, _, _, _, _ = make_runner(tmp_path, client, clock)
    client._pending_orders[("BTCUSDT", "BUY", False)] = {
        "order_id": "pending-order",
        "client_order_id": "AURBpending123",
        "order": {
            "status": "PARTIALLY_FILLED",
            "fills": [{
                "tradeId": "trade-pending",
                "qty": "0.00001",
                "secret": SECRET_SENTINEL,
            }],
            "secret": SECRET_SENTINEL,
        },
    }

    snapshot = runner._pending_snapshot("BUY")

    assert snapshot is not None
    assert SECRET_SENTINEL not in json.dumps(snapshot)
    assert snapshot["order"]["fills"] == [{
        "tradeId": "trade-pending", "qty": "0.00001",
    }]


class FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        self.headers: dict[str, str] = {}
        self.text = "fake provider failure"

    def json(self) -> dict[str, Any]:
        return {"code": -1, "msg": "fake provider failure"}


class FakeSession:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        self.calls = 0

    def request(self, *_: Any, **__: Any) -> FakeResponse:
        self.calls += 1
        return FakeResponse(self.status_code)


def dry_binance_client(monkeypatch: pytest.MonkeyPatch) -> BinanceClient:
    monkeypatch.setenv("BINANCE_DRY_RUN", "true")
    monkeypatch.setenv("BINANCE_UK_MODE", "false")
    monkeypatch.setattr(BinanceClient, "_sync_server_time", lambda self: None)
    return BinanceClient()


@pytest.mark.parametrize("status_code", [429, 500])
def test_binance_post_transport_failure_is_never_replayed(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
) -> None:
    client = dry_binance_client(monkeypatch)
    retries = client.session.get_adapter("https://").max_retries
    assert set(retries.allowed_methods) == {"GET"}
    fake = FakeSession(status_code)
    client.session = fake
    client.max_retries = 3
    client._rate_limiter = None
    monkeypatch.setattr(time, "sleep", lambda _: None)

    with pytest.raises(
        EconomicGovernanceBlocked,
        match="dispatch_capability_required",
    ):
        client._do_request(
            "POST", "/api/v3/order", params={"symbol": "BTCUSDT"},
        )

    assert fake.calls == 0


def test_binance_reconciles_once_by_original_client_order_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = dry_binance_client(monkeypatch)
    client.dry_run = False
    client_id = "AURB1234567890abcdef"
    calls: list[tuple[str, str, dict[str, Any]]] = []

    def signed(
        method: str, path: str, params: dict[str, Any],
    ) -> dict[str, Any]:
        calls.append((method, path, dict(params)))
        now_ms = int(time.time() * 1000)
        return {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "orderId": 12345,
            "clientOrderId": client_id,
            "status": "FILLED",
            "transactTime": now_ms,
            "executedQty": "0.0001",
            "cummulativeQuoteQty": "10",
            "fills": [{
                "tradeId": 9001,
                "qty": "0.0001",
                "price": "100000",
                "commission": "0.01",
                "commissionAsset": "USDT",
                "time": now_ms,
            }],
        }

    monkeypatch.setattr(client, "_signed_request", signed)
    receipt = client.get_order_status(
        None,
        client_id,
        symbol="BTCUSDT",
        side="BUY",
        margin=False,
    )

    assert receipt["status"] == "FILLED"
    assert receipt["clientOrderId"] == client_id
    assert len(calls) == 1
    assert calls[0][0:2] == ("GET", "/api/v3/order")
    assert calls[0][2]["origClientOrderId"] == client_id
    assert "orderId" not in calls[0][2]


def test_binance_ambiguous_post_does_not_fabricate_provider_acceptance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = dry_binance_client(monkeypatch)
    client.dry_run = False
    client.uk_mode = False
    monkeypatch.setattr(
        client,
        "get_symbol_filters",
        lambda symbol: {"min_notional": 5},
    )
    monkeypatch.setattr(
        client, "adjust_quote_qty", lambda symbol, quantity: float(quantity),
    )
    monkeypatch.setattr(
        client,
        "_signed_request",
        lambda method, path, params: (_ for _ in ()).throw(
            TimeoutError("ambiguous transport")
        ),
    )

    receipt = client.place_market_order(
        "BTCUSDT",
        "BUY",
        quote_qty="9",
        client_order_id="AURBambiguous123",
    )

    assert receipt["status"] == "pending_reconciliation"
    assert receipt["truth_status"] == "no_data"
    assert receipt["submitted"] is None
    assert receipt["submission_acknowledged"] is False
    assert receipt["reconciliation_required"] is True
    assert receipt["clientOrderId"] == "AURBambiguous123"


def test_binance_trade_fee_receipt_requires_exact_provider_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = dry_binance_client(monkeypatch)
    now_ms = int(time.time() * 1000)
    monkeypatch.setattr(
        client,
        "_signed_request",
        lambda method, path, params: [{
            "symbol": "BTCUSDT",
            "makerCommission": "0.001",
            "takerCommission": "0.0015",
        }],
    )
    monkeypatch.setattr(
        client, "server_time", lambda: {"serverTime": now_ms},
    )

    receipt = client.get_trade_fee_receipt("BTC/USDT")

    assert receipt["data_status"] == "live"
    assert receipt["truth_status"] == "real_provider"
    assert receipt["maker_commission"] == pytest.approx(0.001)
    assert receipt["taker_commission"] == pytest.approx(0.0015)
    assert receipt["provider_receipt_type"] == "TradeFee+Time"
    assert receipt["eligible_for_action"] is True
