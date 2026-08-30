"""Offline fake-session proof for Kraken's last-mile economic guard.

The responses in this module are synthetic and are inventoried as
dry-run-test-demo-only. No request may reach a provider.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

import aureon.exchanges.kraken_client as kraken_module
import aureon.governance.crown_voice as crown_module
import aureon.governance.economic_boundary as boundary_module
from aureon.exchanges.kraken_client import KRAKEN_BASE, KrakenClient
from aureon.governance.cognition_gate import (
    CognitionGovernanceRequest,
    build_cognition_governance_request,
)
from aureon.governance.crown_voice import (
    ResolvedCrownVoiceEvidence,
    issue_crown_voice_receipt,
)
from aureon.governance.dual_key import join_dual_key
from aureon.governance.economic_boundary import (
    EconomicGovernanceBlocked,
    EconomicIntent,
    bind_economic_governance_boundary,
)
from aureon.swarm.auris_node_receipts import ProviderMoment
from aureon.swarm.druidic_council import (
    REQUIRED_SEATS,
    build_seat_receipt,
    convene_druidic_council,
)

NOW = 1_786_473_600.0
HNC = "hnc:live_field:kraken-transport"
AURIS = "auris:cosmic_state:kraken-transport"
ACCOUNT_HASH = "a" * 64
PROVIDER_DIGEST = "b" * 64
POSITION_RECEIPT = "provider:kraken:position:before"
COUNCIL_ID = "resolver:test-kraken-council:v1"
CROWN_ID = "resolver:test-kraken-crown:v1"
CLIENT_ORDER_ID = "0123456789abcdef0123456789abcdef"


def test_nonce_preserves_nanosecond_provider_high_water(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    nonce_path = tmp_path / ".kraken_nonce"
    nonce_path.write_text("1780000000000000000", encoding="utf-8")
    monkeypatch.setattr(kraken_module, "NONCE_FILE", str(nonce_path))
    monkeypatch.setattr(kraken_module, "_nonce_offset_counter", 0)
    monkeypatch.setattr(
        kraken_module.time,
        "time_ns",
        lambda: 1_790_000_000_000_000_000,
    )

    first = kraken_module._get_next_nonce()
    assert first > 1_790_000_000_000_000_000

    nonce_path.write_text("1800000000000000000", encoding="utf-8")
    second = kraken_module._get_next_nonce()
    assert second > 1_800_000_000_000_000_000


class _Clock:
    def __init__(self) -> None:
        self.value = NOW

    def __call__(self) -> float:
        return self.value


class _CouncilSupplier:
    supplier_id = COUNCIL_ID

    def supply_council_evidence(
        self, request: CognitionGovernanceRequest
    ) -> Any:
        raise AssertionError("isolated dual harness owns this test")


class _CrownSupplier:
    supplier_id = CROWN_ID

    def supply_crown_receipt(
        self, request: CognitionGovernanceRequest
    ) -> Any:
        raise AssertionError("isolated dual harness owns this test")


class _CrownResolver:
    def __init__(
        self,
        request: CognitionGovernanceRequest,
        moment: ProviderMoment,
    ) -> None:
        self.request = request
        self.moment = moment

    def resolve_crown_voice_evidence(
        self,
        proposal_digest: str,
        prompt_digest: str,
    ) -> ResolvedCrownVoiceEvidence:
        assert proposal_digest == self.request.proposal_digest
        assert prompt_digest == self.request.prompt_digest
        evidence = {"provider_moment": self.moment}
        return ResolvedCrownVoiceEvidence(
            resolver_id=CROWN_ID,
            issuer_id="issuer:test-independent-kraken-crown",
            crown_identity="queen:test-kraken-conscience",
            verdict_source_id="queen:test-kraken-conscience:evaluation",
            queen_verdict="APPROVED",
            queen_evaluated=True,
            reason="Crown checked the exact synthetic Kraken proposal",
            proposal_digest=proposal_digest,
            prompt_digest=prompt_digest,
            hnc_evidence=evidence,
            auris_evidence=evidence,
        )


def _dual_evaluator(**kwargs: Any) -> dict[str, Any]:
    request = build_cognition_governance_request(
        prompt=kwargs["prompt"],
        answer=kwargs["answer"],
        tool_calls=kwargs["tool_calls"],
        capability=kwargs["capability"],
        bake=kwargs["bake"],
        acquisition=kwargs["acquisition"],
        queen_verdict=kwargs["queen_verdict"],
    )
    source_timestamp = float(request.provider_source_timestamp)
    seats = [
        build_seat_receipt(
            seat=seat,
            agent_id=f"test-kraken-{seat}",
            decision="ACCEPT",
            reason=f"{seat} checked the exact synthetic Kraken proposal",
            gamma=0.95,
            proposal_digest=request.proposal_digest,
            prompt_digest=request.prompt_digest,
            hnc_receipt_id=HNC,
            auris_receipt_id=AURIS,
            auris_node_receipt_id=f"auris:node:test-kraken:{seat}",
            source_timestamp=source_timestamp,
            derived_at=NOW,
        )
        for seat in REQUIRED_SEATS
    ]
    council = convene_druidic_council(
        proposal_digest=request.proposal_digest,
        prompt_digest=request.prompt_digest,
        hnc_receipt_id=HNC,
        auris_receipt_id=AURIS,
        seat_receipts=seats,
        now=NOW,
    )
    moment = ProviderMoment(
        hnc_receipt_id=HNC,
        auris_receipt_id=AURIS,
        source_timestamp=source_timestamp,
        provider_receipt_ids=request.provider_receipt_ids,
        provider_moment_digest=request.provider_moment_digest,
    )
    crown = issue_crown_voice_receipt(
        proposal_digest=request.proposal_digest,
        prompt_digest=request.prompt_digest,
        resolver=_CrownResolver(request, moment),
        now=NOW,
    )
    return join_dual_key(council, crown, now=NOW)


def _boundary(monkeypatch: pytest.MonkeyPatch):
    clock = _Clock()
    monkeypatch.setattr(
        crown_module,
        "validate_provider_moment",
        lambda hnc, auris, **kwargs: hnc["provider_moment"],
    )
    monkeypatch.setattr(
        boundary_module,
        "evaluate_cognition_governance",
        _dual_evaluator,
    )
    boundary = bind_economic_governance_boundary(
        council_receipt_supplier=_CouncilSupplier(),
        crown_receipt_supplier=_CrownSupplier(),
        trusted_council_supplier_ids=frozenset({COUNCIL_ID}),
        trusted_crown_supplier_ids=frozenset({CROWN_ID}),
        clock=clock,
        permit_ttl_s=2.0,
        provider_max_age_s=10.0,
    )
    return boundary, clock


def _intent(
    clock: _Clock,
    *,
    path: str,
    body: dict[str, Any],
) -> EconomicIntent:
    is_add = path == "/0/private/AddOrder"
    body_bindings = {}
    if is_add:
        body_bindings = {
            "order_type": "/ordertype",
            "quantity": "/volume",
            "side": "/type",
            "symbol": "/pair",
        }
        if "cl_ord_id" in body:
            body_bindings["client_order_id"] = "/cl_ord_id"
    return EconomicIntent.build(
        venue="kraken",
        environment="live",
        account_id_hash=ACCOUNT_HASH,
        method="POST",
        path=path,
        operation="MARKET_ORDER" if is_add else "ECONOMIC_MUTATION",
        purpose="ENTRY" if is_add else "ACCOUNT_CONTROL",
        symbol=str(body.get("pair", "ACCOUNT")),
        side=str(body.get("type", "NONE")).upper(),
        order_type=str(body.get("ordertype", "CONTROL")).upper(),
        quantity=str(body["volume"]) if "volume" in body else None,
        quote_quantity=None,
        limit_price=None,
        stop_price=None,
        take_profit=None,
        reduce_only=False,
        client_order_id=str(body.get("cl_ord_id", f"test:{path}")),
        authorization_receipt_id="authorization:test:kraken-transport",
        cycle_id="test-kraken-cycle",
        position_receipt_id=POSITION_RECEIPT,
        hnc_receipt_id=HNC,
        auris_receipt_id=AURIS,
        provider_receipt_ids={
            POSITION_RECEIPT,
            "provider:kraken:account:test",
            "provider:kraken:market:test",
        },
        provider_moment_digest=PROVIDER_DIGEST,
        provider_source_timestamp=str(int(clock.value - 1)),
        body=body,
        body_bindings=body_bindings,
    )


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self.payload


class _FakeSession:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return _FakeResponse(
            {"error": [], "result": {"txid": ["OFFLINE-RECEIPT-123"]}}
        )


def _client(session: _FakeSession) -> KrakenClient:
    client = object.__new__(KrakenClient)
    client.api_key = "test-only-key"
    client.api_secret = "dGVzdC1vbmx5LXNlY3JldA=="
    client.use_testnet = False
    client.dry_run = False
    client.base = KRAKEN_BASE
    client.session = session
    client._private_lock = kraken_module.threading.Lock()
    client._last_private_call = 0.0
    client._min_call_interval = 0.0
    client._private_bucket = None
    client._rate_limit_until = 0.0
    client._rate_limit_backoff = 0.0
    client._consecutive_rate_limits = 0
    client._balance_cache = {}
    client._balance_cache_time = 0.0
    client._economic_dispatch_lock = kraken_module.threading.RLock()
    client._economic_dispatches = {}
    return client


def _consume(
    monkeypatch: pytest.MonkeyPatch,
    client: KrakenClient,
    *,
    path: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    boundary, clock = _boundary(monkeypatch)
    intent = _intent(clock, path=path, body=body)
    permit = boundary.prepare_mutation(intent)
    return boundary.consume_and_call(
        permit,
        method="POST",
        path=path,
        body=json.loads(intent.body_json),
        transport=lambda: client._private(path, dict(body)),
    )


def test_exact_add_order_context_reaches_fake_session_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    client = _client(session)
    body = {
        "pair": "XXBTZUSD",
        "type": "buy",
        "ordertype": "market",
        "volume": "0.1",
        "cl_ord_id": CLIENT_ORDER_ID,
    }
    monkeypatch.setattr(kraken_module, "_get_next_nonce", lambda: 123456789)

    result = _consume(
        monkeypatch,
        client,
        path="/0/private/AddOrder",
        body=body,
    )

    assert result == {"txid": ["OFFLINE-RECEIPT-123"]}
    assert len(session.calls) == 1
    assert session.calls[0]["url"] == f"{KRAKEN_BASE}/0/private/AddOrder"
    assert session.calls[0]["data"] == {**body, "nonce": "123456789"}
    assert client._economic_dispatches == {}


@pytest.mark.parametrize(
    "path,body",
    [
        ("/0/private/CancelOrder", {"txid": "TEST-ORDER"}),
        ("/0/private/EditOrder", {"txid": "TEST-ORDER", "volume": "0.2"}),
        ("/0/private/Withdraw", {"asset": "XBT", "amount": "0.1", "key": "vault"}),
        ("/0/private/WalletTransfer", {"asset": "USD", "amount": "10"}),
        ("/0/private/Earn/Allocate", {"strategy_id": "TEST", "amount": "10"}),
    ],
)
def test_direct_private_mutation_has_zero_fake_session_calls(
    path: str,
    body: dict[str, Any],
) -> None:
    session = _FakeSession()
    client = _client(session)

    with pytest.raises(
        EconomicGovernanceBlocked,
        match="boundary_issued_economic_transport_context_required",
    ):
        client._private(path, body)

    assert session.calls == []


@pytest.mark.parametrize(
    "path,body",
    [
        ("/0/private/CancelOrder", {"txid": "OFFLINE-ORDER-1"}),
        (
            "/0/private/EditOrder",
            {"txid": "OFFLINE-ORDER-1", "volume": "0.2"},
        ),
        (
            "/0/private/Withdraw",
            {"asset": "XBT", "amount": "0.1", "key": "offline-vault"},
        ),
    ],
)
def test_exact_non_add_mutation_context_reaches_fake_session_once(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    body: dict[str, Any],
) -> None:
    session = _FakeSession()
    client = _client(session)
    monkeypatch.setattr(kraken_module, "_get_next_nonce", lambda: 987654321)

    result = _consume(monkeypatch, client, path=path, body=body)

    assert result == {"txid": ["OFFLINE-RECEIPT-123"]}
    assert len(session.calls) == 1
    assert session.calls[0]["url"] == f"{KRAKEN_BASE}{path}"
    assert session.calls[0]["data"] == {**body, "nonce": "987654321"}


def test_path_body_drift_and_replay_are_zero_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    client = _client(session)
    boundary, clock = _boundary(monkeypatch)
    body = {
        "pair": "XXBTZUSD",
        "type": "sell",
        "ordertype": "market",
        "volume": "0.1",
        "cl_ord_id": CLIENT_ORDER_ID,
    }
    intent = _intent(clock, path="/0/private/AddOrder", body=body)
    permit = boundary.prepare_mutation(intent)

    with pytest.raises(
        EconomicGovernanceBlocked,
        match="exact_economic_transport_method_path_body_required",
    ):
        boundary.consume_and_call(
            permit,
            method="POST",
            path="/0/private/AddOrder",
            body=body,
            transport=lambda: client._private(
                "/0/private/AddOrder",
                {**body, "volume": "0.2"},
            ),
        )
    with pytest.raises(
        EconomicGovernanceBlocked,
        match="unknown_consumed_or_replayed_permit",
    ):
        boundary.consume_and_call(
            permit,
            method="POST",
            path="/0/private/AddOrder",
            body=body,
            transport=lambda: client._private("/0/private/AddOrder", body),
        )

    assert session.calls == []


def test_raw_http_chokepoint_rejects_direct_and_replayed_dispatch() -> None:
    session = _FakeSession()
    client = _client(session)
    wire = {
        "pair": "XXBTZUSD",
        "type": "buy",
        "ordertype": "market",
        "volume": "0.1",
        "cl_ord_id": CLIENT_ORDER_ID,
        "nonce": "123",
    }
    headers = {"API-Key": "test-only", "API-Sign": "test-only"}

    with pytest.raises(
        EconomicGovernanceBlocked,
        match="signed_kraken_mutation_dispatch_capability_required",
    ):
        client._private_http_post(
            "/0/private/AddOrder",
            data=wire,
            headers=headers,
            timeout=15,
        )

    drift_dispatch = client._register_economic_dispatch(
        method="POST",
        path="/0/private/AddOrder",
        body_digest=boundary_module._economic_transport_body_digest(
            {name: value for name, value in wire.items() if name != "nonce"}
        ),
    )
    with pytest.raises(
        EconomicGovernanceBlocked,
        match="exact_kraken_mutation_method_path_body_required",
    ):
        client._private_http_post(
            "/0/private/AddOrder",
            data={**wire, "volume": "0.2"},
            headers=headers,
            timeout=15,
            _economic_dispatch=drift_dispatch,
        )

    dispatch = client._register_economic_dispatch(
        method="POST",
        path="/0/private/AddOrder",
        body_digest=boundary_module._economic_transport_body_digest(
            {name: value for name, value in wire.items() if name != "nonce"}
        ),
    )
    client._private_http_post(
        "/0/private/AddOrder",
        data=wire,
        headers=headers,
        timeout=15,
        _economic_dispatch=dispatch,
    )
    with pytest.raises(
        EconomicGovernanceBlocked,
        match="signed_kraken_mutation_dispatch_capability_required",
    ):
        client._private_http_post(
            "/0/private/AddOrder",
            data=wire,
            headers=headers,
            timeout=15,
            _economic_dispatch=dispatch,
        )

    assert len(session.calls) == 1


def test_read_only_private_query_remains_ungated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    client = _client(session)
    monkeypatch.setattr(kraken_module, "_get_next_nonce", lambda: 123456789)

    result = client._private("/0/private/Balance", {})

    assert result == {"txid": ["OFFLINE-RECEIPT-123"]}
    assert len(session.calls) == 1
    assert session.calls[0]["url"] == f"{KRAKEN_BASE}/0/private/Balance"


@pytest.mark.parametrize("unsafe_mode", ["dry_run", "testnet", "wrong_base"])
def test_unsafe_environment_is_zero_call(
    unsafe_mode: str,
) -> None:
    session = _FakeSession()
    client = _client(session)
    if unsafe_mode == "dry_run":
        client.dry_run = True
    elif unsafe_mode == "testnet":
        client.use_testnet = True
    else:
        client.base = "https://example.invalid"

    with pytest.raises(EconomicGovernanceBlocked):
        client._private(
            "/0/private/AddOrder",
            {
                "pair": "XXBTZUSD",
                "type": "buy",
                "ordertype": "market",
                "volume": "0.1",
                "cl_ord_id": CLIENT_ORDER_ID,
            },
        )

    assert session.calls == []


def test_secondary_tp_leg_cannot_reuse_entry_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    client = _client(session)
    client._load_asset_pairs = lambda: None
    client._alt_to_int = {"XBTUSD": "XXBTZUSD"}
    monkeypatch.setattr(kraken_module, "_get_next_nonce", lambda: 123456789)
    entry_body = {
        "pair": "XXBTZUSD",
        "type": "buy",
        "ordertype": "market",
        "volume": "0.1",
        "close[ordertype]": "stop-loss",
        "close[price]": "90",
    }

    # The distinct secondary TP body is not included in the entry permit and
    # therefore cannot reuse its consumed context.
    boundary, clock = _boundary(monkeypatch)
    intent = _intent(
        clock,
        path="/0/private/AddOrder",
        body=entry_body,
    )
    permit = boundary.prepare_mutation(intent)
    result = boundary.consume_and_call(
        permit,
        method="POST",
        path="/0/private/AddOrder",
        body=entry_body,
        transport=lambda: client.place_order_with_tp_sl(
            "XBTUSD",
            "buy",
            "0.1",
            take_profit="110",
            stop_loss="90",
        ),
    )

    assert result["entryOrderId"] == "OFFLINE-RECEIPT-123"
    assert result["takeProfitOrderId"] is None
    assert result["reason"] == "secondary_submission_requires_reconciliation"
    assert result["secondary_submission_error"] == "EconomicGovernanceBlocked"
    assert len(session.calls) == 1
