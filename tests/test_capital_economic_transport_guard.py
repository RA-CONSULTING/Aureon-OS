"""Offline proof for Capital's final economic mutation transport guard."""

from __future__ import annotations

import time
from typing import Any

import pytest

import aureon.exchanges.capital_client as capital_module
from aureon.exchanges.capital_client import (
    CAPITAL_DEMO_BASE,
    CAPITAL_LIVE_BASE,
    CapitalClient,
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


class _FakeResponse:
    def __init__(self, status_code: int = 200, payload: dict[str, Any] | None = None):
        self.status_code = status_code
        self._payload = payload or {"dealReference": "capital-test-reference"}
        self.text = "{}"
        self.headers: dict[str, str] = {}

    def json(self) -> dict[str, Any]:
        return dict(self._payload)


class _FakeTransport:
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code
        self.calls: list[dict[str, Any]] = []

    def __call__(self, method: str, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        return _FakeResponse(self.status_code)


def _client(*, demo: bool = False, dry_run: bool = False) -> CapitalClient:
    client = object.__new__(CapitalClient)
    client.api_key = "dummy-capital-api-key"
    client.identifier = "dummy-capital-identifier"
    client.password = "dummy-capital-password"
    client.demo_mode = demo
    client.base_url = CAPITAL_DEMO_BASE if demo else CAPITAL_LIVE_BASE
    client.dry_run = dry_run
    client.enabled = True
    client.init_error = ""
    client.cst = "dummy-cst"
    client.x_security_token = "dummy-security-token"
    client.session_start_time = time.time()
    client._rate_limit_until = 0.0
    client._rate_limit_logged = False
    client._session_error_logged = False
    client._next_session_retry_at = 0.0
    client._economic_dispatch_lock = capital_module.threading.RLock()
    client._economic_dispatches = {}
    return client


def _intent(clock, *, method: str, path: str, body: dict[str, Any]) -> EconomicIntent:
    bindings: dict[str, str] = {}
    if path == "/positions":
        bindings = {
            "order_type": "/orderType",
            "quantity": "/size",
            "side": "/direction",
            "symbol": "/epic",
        }
    return EconomicIntent.build(
        venue="capital",
        environment="live",
        account_id_hash=ACCOUNT_HASH,
        method=method,
        path=path,
        operation="MARKET_ORDER" if path == "/positions" else "ECONOMIC_MUTATION",
        purpose="ENTRY" if path == "/positions" else "ACCOUNT_CONTROL",
        symbol=str(body.get("epic", "ACCOUNT")),
        side=str(body.get("direction", "NONE")),
        order_type=str(body.get("orderType", "CONTROL")),
        quantity=str(body["size"]) if "size" in body else None,
        quote_quantity=None,
        limit_price=None,
        stop_price=None,
        take_profit=None,
        reduce_only=False,
        client_order_id="capital-test-client-order-id",
        authorization_receipt_id="authorization:test:capital-transport",
        cycle_id="test-capital-cycle",
        position_receipt_id=POSITION_RECEIPT,
        hnc_receipt_id=HNC,
        auris_receipt_id=AURIS,
        provider_receipt_ids={
            POSITION_RECEIPT,
            "provider:capital:account:test",
            "provider:capital:market:test",
        },
        provider_moment_digest=PROVIDER_DIGEST,
        provider_source_timestamp=str(int(clock.value - 1)),
        body=body,
        body_bindings=bindings,
        body_requires_json_numbers=True,
    )


def _execute(
    monkeypatch: pytest.MonkeyPatch,
    *,
    method: str = "POST",
    path: str = "/positions",
    body: dict[str, Any] | None = None,
    status_code: int = 200,
):
    economic_body = body or {
        "epic": "CS.D.TEST.CFD.IP",
        "direction": "BUY",
        "size": "1",
        "orderType": "MARKET",
    }
    boundary, clock = _boundary(monkeypatch)
    client = _client()
    transport = _FakeTransport(status_code)
    monkeypatch.setattr(capital_module.requests, "request", transport)
    intent = _intent(clock, method=method, path=path, body=economic_body)
    permit = boundary.prepare_mutation(intent)
    response = boundary.consume_capital_and_call(
        permit,
        method=method,
        path=path,
        body=economic_body,
        transport=lambda: client._request(method, path, json_body=economic_body),
    )
    return response, transport, boundary, permit, economic_body


def test_exact_live_capital_permit_reaches_fake_transport_once(monkeypatch):
    response, transport, boundary, permit, body = _execute(monkeypatch)

    assert response.status_code == 200
    assert len(transport.calls) == 1
    assert transport.calls[0]["method"] == "POST"
    assert transport.calls[0]["url"] == f"{CAPITAL_LIVE_BASE}/positions"
    with pytest.raises(EconomicGovernanceBlocked):
        boundary.consume_and_call(
            permit,
            method="POST",
            path="/positions",
            body=body,
            transport=lambda: None,
        )
    assert len(transport.calls) == 1


def test_missing_live_capital_context_blocks_before_http(monkeypatch):
    client = _client()
    transport = _FakeTransport()
    monkeypatch.setattr(capital_module.requests, "request", transport)

    with pytest.raises(EconomicGovernanceBlocked):
        client._request("POST", "/positions", json_body={"size": "1"})
    assert transport.calls == []


@pytest.mark.parametrize(
    ("path", "body", "params"),
    [
        ("/positions?account=other", {"size": "1"}, None),
        ("/positions", {"size": "1"}, {"account": "other"}),
        ("/positions//other", {"size": "1"}, None),
        ("/session", {"identifier": "x"}, None),
    ],
)
def test_noncanonical_or_query_mutation_blocks_before_http(
    monkeypatch, path, body, params
):
    client = _client()
    transport = _FakeTransport()
    monkeypatch.setattr(capital_module.requests, "request", transport)

    with pytest.raises(EconomicGovernanceBlocked):
        client._request("POST", path, params=params, json_body=body)
    assert transport.calls == []


def test_body_drift_burns_context_before_http(monkeypatch):
    boundary, clock = _boundary(monkeypatch)
    client = _client()
    transport = _FakeTransport()
    monkeypatch.setattr(capital_module.requests, "request", transport)
    body = {
        "epic": "CS.D.TEST.CFD.IP",
        "direction": "BUY",
        "size": "1",
        "orderType": "MARKET",
    }
    permit = boundary.prepare_mutation(
        _intent(clock, method="POST", path="/positions", body=body)
    )

    with pytest.raises(EconomicGovernanceBlocked):
        boundary.consume_and_call(
            permit,
            method="POST",
            path="/positions",
            body=body,
            transport=lambda: client._request(
                "POST", "/positions", json_body={**body, "size": "2"}
            ),
        )
    assert transport.calls == []


def test_direct_final_http_seam_requires_private_dispatch(monkeypatch):
    client = _client()
    transport = _FakeTransport()
    monkeypatch.setattr(capital_module.requests, "request", transport)

    with pytest.raises(EconomicGovernanceBlocked):
        client._capital_http_request(
            "DELETE",
            "/positions/DEAL-1",
            headers=client._get_headers(),
            params=None,
            json_body={},
        )
    assert transport.calls == []


def test_live_mutation_401_is_not_automatically_retried(monkeypatch):
    response, transport, *_ = _execute(monkeypatch, status_code=401)

    assert response.status_code == 401
    assert len(transport.calls) == 1


def test_live_mutation_429_records_backoff_without_retry(monkeypatch):
    response, transport, *_ = _execute(monkeypatch, status_code=429)

    assert response.status_code == 429
    assert len(transport.calls) == 1
    assert transport.calls[0]["method"] == "POST"


@pytest.mark.parametrize("dry_run", [False, True])
def test_demo_is_exactly_host_bound_and_dry_run_stays_inert(monkeypatch, dry_run):
    client = _client(demo=True, dry_run=dry_run)
    transport = _FakeTransport()
    monkeypatch.setattr(capital_module.requests, "request", transport)
    if dry_run:
        with pytest.raises(EconomicGovernanceBlocked):
            client._request("DELETE", "/positions/DEMO-1")
        assert transport.calls == []
    else:
        response = client._request("DELETE", "/positions/DEMO-1")
        assert response.status_code == 200
        assert len(transport.calls) == 1


def test_wrong_environment_host_blocks_before_http(monkeypatch):
    client = _client()
    client.base_url = CAPITAL_DEMO_BASE
    transport = _FakeTransport()
    monkeypatch.setattr(capital_module.requests, "request", transport)

    with pytest.raises(EconomicGovernanceBlocked):
        client._request("DELETE", "/positions/DEAL-1")
    assert transport.calls == []


def test_read_only_capital_request_remains_available(monkeypatch):
    client = _client()
    transport = _FakeTransport()
    monkeypatch.setattr(capital_module.requests, "request", transport)

    response = client._request("GET", "/accounts")

    assert response.status_code == 200
    assert len(transport.calls) == 1
    assert transport.calls[0]["url"] == f"{CAPITAL_LIVE_BASE}/accounts"
