"""Offline fake-session proof for Alpaca options mutation governance."""

from __future__ import annotations

from typing import Any

import pytest

from aureon.exchanges.alpaca_options_client import (
    ALPACA_OPTIONS_LIVE_BASE,
    ALPACA_OPTIONS_PAPER_BASE,
    AlpacaOptionsClient,
)
from aureon.governance.economic_boundary import (
    EconomicGovernanceBlocked,
    EconomicIntent,
)
from tests.test_kraken_economic_transport_guard import (
    ACCOUNT_HASH,
    AURIS,
    HNC,
    POSITION_RECEIPT,
    PROVIDER_DIGEST,
    _boundary,
)


class _Response:
    status_code = 200
    text = "{}"

    def __init__(self, payload: Any = None) -> None:
        self._payload = payload if payload is not None else {
            "id": "option-order-test",
            "status": "accepted",
        }

    def json(self) -> Any:
        return self._payload

    def raise_for_status(self) -> None:
        return None


class _Session:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> _Response:
        self.calls.append({"method": method, "url": url, **kwargs})
        return _Response()


def _client(*, paper: bool = False, dry_run: bool = False) -> AlpacaOptionsClient:
    client = object.__new__(AlpacaOptionsClient)
    client.use_paper = paper
    client.dry_run = dry_run
    client.base_url = (
        ALPACA_OPTIONS_PAPER_BASE if paper else ALPACA_OPTIONS_LIVE_BASE
    )
    client.session = _Session()
    client.timeout = 1.0
    client._economic_dispatch_lock = __import__("threading").RLock()
    client._economic_dispatches = {}
    return client


def _order_body() -> dict[str, Any]:
    return {
        "symbol": "AAPL260821C00200000",
        "qty": "1",
        "side": "buy",
        "type": "limit",
        "time_in_force": "day",
        "limit_price": "1.25",
    }


def _intent(clock, *, method: str, path: str, body: dict[str, Any]) -> EconomicIntent:
    is_order = path == "/v2/orders"
    bindings = (
        {
            "order_type": "/type",
            "quantity": "/qty",
            "side": "/side",
            "symbol": "/symbol",
        }
        if is_order
        else {}
    )
    return EconomicIntent.build(
        venue="alpaca",
        environment="live",
        account_id_hash=ACCOUNT_HASH,
        method=method,
        path=path,
        operation="LIMIT_ORDER" if is_order else "ECONOMIC_MUTATION",
        purpose="ENTRY" if is_order else "ACCOUNT_CONTROL",
        symbol=str(body.get("symbol", "OPTION")),
        side=str(body.get("side", "NONE")).upper(),
        order_type=str(body.get("type", "CONTROL")).upper(),
        quantity=str(body["qty"]) if "qty" in body else None,
        quote_quantity=None,
        limit_price=str(body["limit_price"]) if "limit_price" in body else None,
        stop_price=None,
        take_profit=None,
        reduce_only=False,
        client_order_id="alpaca-options-test-client-order-id",
        authorization_receipt_id="authorization:test:alpaca-options",
        cycle_id="test-alpaca-options-cycle",
        position_receipt_id=POSITION_RECEIPT,
        hnc_receipt_id=HNC,
        auris_receipt_id=AURIS,
        provider_receipt_ids={
            POSITION_RECEIPT,
            "provider:alpaca:options-account:test",
            "provider:alpaca:options-market:test",
        },
        provider_moment_digest=PROVIDER_DIGEST,
        provider_source_timestamp=str(int(clock.value - 1)),
        body=body,
        body_bindings=bindings,
    )


def test_exact_live_option_order_uses_boundary_and_http_once(monkeypatch):
    boundary, clock = _boundary(monkeypatch)
    client = _client()
    body = _order_body()
    permit = boundary.prepare_mutation(
        _intent(clock, method="POST", path="/v2/orders", body=body)
    )

    order = boundary.consume_and_call(
        permit,
        method="POST",
        path="/v2/orders",
        body=body,
        transport=lambda: client.place_order(
            body["symbol"], 1, "buy", "limit", 1.25
        ),
    )

    assert order is not None
    assert order.id == "option-order-test"
    assert len(client.session.calls) == 1
    assert client.session.calls[0]["url"] == f"{ALPACA_OPTIONS_LIVE_BASE}/v2/orders"
    with pytest.raises(EconomicGovernanceBlocked):
        boundary.consume_and_call(
            permit,
            method="POST",
            path="/v2/orders",
            body=body,
            transport=lambda: None,
        )
    assert len(client.session.calls) == 1


def test_missing_live_context_blocks_before_http():
    client = _client()
    with pytest.raises(EconomicGovernanceBlocked):
        client.place_order("AAPL260821C00200000", 1, "buy", "limit", 1.25)
    assert client.session.calls == []


def test_paper_option_order_is_exact_host_and_one_call():
    client = _client(paper=True)
    order = client.place_order("AAPL260821C00200000", 1, "buy", "limit", 1.25)
    assert order is not None
    assert len(client.session.calls) == 1
    assert client.session.calls[0]["url"] == f"{ALPACA_OPTIONS_PAPER_BASE}/v2/orders"


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/v2/orders?side=buy"),
        ("POST", "/v2/orders/bulk"),
        ("DELETE", "/v2/orders/bad/id"),
        ("POST", "/v2/positions/bad#id/exercise"),
    ],
)
def test_noncanonical_option_paths_block_before_http(method, path):
    client = _client(paper=True)
    with pytest.raises(EconomicGovernanceBlocked):
        client._prepare_options_mutation(method=method, path=path, body={})
    assert client.session.calls == []


@pytest.mark.parametrize("paper", [False, True])
def test_options_dry_run_blocks_before_http(paper):
    client = _client(paper=paper, dry_run=True)
    with pytest.raises(EconomicGovernanceBlocked):
        client.place_order("AAPL260821C00200000", 1, "buy", "limit", 1.25)
    assert client.session.calls == []


def test_direct_options_http_seam_requires_private_dispatch():
    client = _client(paper=True)
    with pytest.raises(EconomicGovernanceBlocked):
        client._options_mutation_request("POST", "/v2/orders", body=_order_body())
    assert client.session.calls == []


def test_body_drift_burns_dispatch_before_http():
    client = _client(paper=True)
    body = _order_body()
    dispatch = client._prepare_options_mutation(
        method="POST", path="/v2/orders", body=body
    )
    drifted = {**body, "qty": "2"}
    with pytest.raises(EconomicGovernanceBlocked):
        client._options_mutation_request(
            "POST",
            "/v2/orders",
            body=drifted,
            _economic_dispatch=dispatch,
        )
    assert client.session.calls == []


def test_options_dispatch_is_one_use():
    client = _client(paper=True)
    body = _order_body()
    dispatch = client._prepare_options_mutation(
        method="POST", path="/v2/orders", body=body
    )
    client._options_mutation_request(
        "POST", "/v2/orders", body=body, _economic_dispatch=dispatch
    )
    with pytest.raises(EconomicGovernanceBlocked):
        client._options_mutation_request(
            "POST", "/v2/orders", body=body, _economic_dispatch=dispatch
        )
    assert len(client.session.calls) == 1


@pytest.mark.parametrize(
    ("operation", "identifier", "expected_method", "expected_path"),
    [
        ("exercise", "AAPL260821C00200000", "POST", "/v2/positions/AAPL260821C00200000/exercise"),
        ("cancel", "order-test-123", "DELETE", "/v2/orders/order-test-123"),
    ],
)
def test_paper_exercise_and_cancel_are_exactly_guarded(
    operation, identifier, expected_method, expected_path
):
    client = _client(paper=True)
    result = (
        client.exercise(identifier)
        if operation == "exercise"
        else client.cancel_order(identifier)
    )
    assert result is True
    assert len(client.session.calls) == 1
    assert client.session.calls[0]["method"] == expected_method
    assert client.session.calls[0]["url"] == f"{ALPACA_OPTIONS_PAPER_BASE}{expected_path}"


def test_wrong_options_environment_host_blocks_before_http():
    client = _client(paper=True)
    client.base_url = ALPACA_OPTIONS_LIVE_BASE
    with pytest.raises(EconomicGovernanceBlocked):
        client.cancel_order("order-test-123")
    assert client.session.calls == []
