"""Offline fake-session proof for Alpaca's economic transport guard."""

from __future__ import annotations

from typing import Any

import pytest
import requests

from aureon.exchanges.alpaca_client import (
    ALPACA_LIVE_BASE,
    ALPACA_PAPER_BASE,
    AlpacaClient,
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


class _Cache:
    def get(self, _key: str):
        return None

    def set(self, _key: str, _value: Any) -> None:
        return None


class _Limiter:
    def __init__(self) -> None:
        self.rate_limits = 0

    def wait_trading(self) -> None:
        return None

    def wait_data(self) -> None:
        return None

    def on_429_error(self) -> None:
        self.rate_limits += 1


class _FakeResponse:
    def __init__(self, status_code: int = 200, payload: Any = None) -> None:
        self.status_code = status_code
        self._payload = payload if payload is not None else {"id": "alpaca-test-order"}
        self.text = "{}"
        self.headers: dict[str, str] = {}

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self) -> Any:
        return self._payload


class _FakeSession:
    def __init__(
        self,
        *,
        status_code: int = 200,
        payload: Any = None,
        error: Exception | None = None,
    ) -> None:
        self.status_code = status_code
        self.payload = payload
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        if self.error is not None:
            raise self.error
        return _FakeResponse(self.status_code, self.payload)


def _client(
    *,
    paper: bool = False,
    dry_run: bool = False,
    session: _FakeSession | None = None,
) -> AlpacaClient:
    client = object.__new__(AlpacaClient)
    client.use_paper = paper
    client.dry_run = dry_run
    client.base_url = ALPACA_PAPER_BASE if paper else ALPACA_LIVE_BASE
    client.data_url = "https://data.alpaca.markets"
    client.session = session or _FakeSession()
    client.timeout_seconds = 1.0
    client.max_retries = 3
    client._closed = False
    client.is_authenticated = True
    client.last_error = None
    client.init_error = ""
    client._response_cache = _Cache()
    client._rate_limiter = _Limiter()
    client._global_rate_budget = None
    client._classify_request_type = None
    client._ensure_economic_dispatch_store()
    return client


def _intent(
    clock,
    *,
    method: str,
    path: str,
    body: dict[str, Any],
) -> EconomicIntent:
    is_order = method == "POST" and path == "/v2/orders"
    bindings: dict[str, str] = {}
    if is_order:
        bindings = {
            "order_type": "/type",
            "quantity": "/qty",
            "side": "/side",
            "symbol": "/symbol",
        }
    return EconomicIntent.build(
        venue="alpaca",
        environment="live",
        account_id_hash=ACCOUNT_HASH,
        method=method,
        path=path,
        operation="MARKET_ORDER" if is_order else "ECONOMIC_MUTATION",
        purpose="ENTRY" if is_order else "ACCOUNT_CONTROL",
        symbol=str(body.get("symbol", "ACCOUNT")),
        side=str(body.get("side", "NONE")).upper(),
        order_type=str(body.get("type", "CONTROL")).upper(),
        quantity=str(body["qty"]) if "qty" in body else None,
        quote_quantity=None,
        limit_price=None,
        stop_price=None,
        take_profit=None,
        reduce_only=False,
        client_order_id="alpaca-test-client-order-id",
        authorization_receipt_id="authorization:test:alpaca-transport",
        cycle_id="test-alpaca-cycle",
        position_receipt_id=POSITION_RECEIPT,
        hnc_receipt_id=HNC,
        auris_receipt_id=AURIS,
        provider_receipt_ids={
            POSITION_RECEIPT,
            "provider:alpaca:account:test",
            "provider:alpaca:market:test",
        },
        provider_moment_digest=PROVIDER_DIGEST,
        provider_source_timestamp=str(int(clock.value - 1)),
        body=body,
        body_bindings=bindings,
    )


def _execute(
    monkeypatch: pytest.MonkeyPatch,
    *,
    method: str = "POST",
    path: str = "/v2/orders",
    body: dict[str, Any] | None = None,
    status_code: int = 200,
    error: Exception | None = None,
):
    economic_body = body or {
        "symbol": "AAPL",
        "qty": "1",
        "side": "buy",
        "type": "market",
        "time_in_force": "day",
    }
    boundary, clock = _boundary(monkeypatch)
    session = _FakeSession(status_code=status_code, error=error)
    client = _client(session=session)
    permit = boundary.prepare_mutation(
        _intent(clock, method=method, path=path, body=economic_body)
    )
    response = boundary.consume_and_call(
        permit,
        method=method,
        path=path,
        body=economic_body,
        transport=lambda: client._request(
            method,
            path,
            data=economic_body,
            request_type="trading",
        ),
    )
    return response, session, boundary, permit, economic_body


def test_exact_live_alpaca_permit_reaches_fake_session_once(monkeypatch):
    response, session, boundary, permit, body = _execute(monkeypatch)

    assert response["id"] == "alpaca-test-order"
    assert len(session.calls) == 1
    assert session.calls[0]["url"] == f"{ALPACA_LIVE_BASE}/v2/orders"
    with pytest.raises(EconomicGovernanceBlocked):
        boundary.consume_and_call(
            permit,
            method="POST",
            path="/v2/orders",
            body=body,
            transport=lambda: None,
        )
    assert len(session.calls) == 1


def test_missing_live_context_blocks_before_session():
    session = _FakeSession()
    client = _client(session=session)

    with pytest.raises(EconomicGovernanceBlocked):
        client._request(
            "POST",
            "/v2/orders",
            data={"symbol": "AAPL", "qty": "1"},
            request_type="trading",
        )
    assert session.calls == []


@pytest.mark.parametrize(
    ("method", "path", "params", "request_type"),
    [
        ("POST", "/v2/orders?account=other", None, "trading"),
        ("POST", "/v2/orders", {"account": "other"}, "trading"),
        ("DELETE", "/v2/orders//other", None, "trading"),
        ("POST", "/v2/orders", None, "data"),
        ("POST", "/v2/account", None, "trading"),
    ],
)
def test_noncanonical_query_or_nontrading_mutation_blocks(
    method, path, params, request_type
):
    session = _FakeSession()
    client = _client(session=session)

    with pytest.raises(EconomicGovernanceBlocked):
        client._request(
            method,
            path,
            params=params,
            data={"symbol": "AAPL", "qty": "1"},
            request_type=request_type,
        )
    assert session.calls == []


def test_body_drift_burns_context_before_session(monkeypatch):
    boundary, clock = _boundary(monkeypatch)
    session = _FakeSession()
    client = _client(session=session)
    body = {
        "symbol": "AAPL",
        "qty": "1",
        "side": "buy",
        "type": "market",
        "time_in_force": "day",
    }
    permit = boundary.prepare_mutation(
        _intent(clock, method="POST", path="/v2/orders", body=body)
    )

    with pytest.raises(EconomicGovernanceBlocked):
        boundary.consume_and_call(
            permit,
            method="POST",
            path="/v2/orders",
            body=body,
            transport=lambda: client._request(
                "POST",
                "/v2/orders",
                data={**body, "qty": "2"},
                request_type="trading",
            ),
        )
    assert session.calls == []


def test_direct_final_http_seam_requires_private_dispatch():
    session = _FakeSession()
    client = _client(session=session)

    with pytest.raises(EconomicGovernanceBlocked):
        client._alpaca_http_request(
            "DELETE",
            "/v2/orders/ORDER-1",
            request_base=ALPACA_LIVE_BASE,
            params=None,
            body={},
        )
    assert session.calls == []


@pytest.mark.parametrize("status_code", [401, 429])
def test_negative_live_response_is_never_retried(monkeypatch, status_code):
    response, session, *_ = _execute(monkeypatch, status_code=status_code)

    assert response == {}
    assert len(session.calls) == 1


def test_live_timeout_is_never_retried(monkeypatch):
    response, session, *_ = _execute(
        monkeypatch,
        error=requests.exceptions.Timeout("synthetic timeout"),
    )

    assert response == {}
    assert len(session.calls) == 1


@pytest.mark.parametrize("dry_run", [False, True])
def test_paper_is_exactly_host_bound_and_dry_run_stays_inert(dry_run):
    session = _FakeSession()
    client = _client(paper=True, dry_run=dry_run, session=session)
    if dry_run:
        with pytest.raises(EconomicGovernanceBlocked):
            client._request(
                "DELETE", "/v2/orders/PAPER-1", request_type="trading"
            )
        assert session.calls == []
    else:
        response = client._request(
            "DELETE", "/v2/orders/PAPER-1", request_type="trading"
        )
        assert response["id"] == "alpaca-test-order"
        assert len(session.calls) == 1
        assert session.calls[0]["url"].startswith(ALPACA_PAPER_BASE)


def test_wrong_environment_host_blocks_before_session():
    session = _FakeSession()
    client = _client(session=session)
    client.base_url = ALPACA_PAPER_BASE

    with pytest.raises(EconomicGovernanceBlocked):
        client._request("DELETE", "/v2/orders/ORDER-1", request_type="trading")
    assert session.calls == []


def test_exact_position_close_route_is_guarded(monkeypatch):
    response, session, *_ = _execute(
        monkeypatch,
        method="DELETE",
        path="/v2/positions/AAPL",
        body={},
    )

    assert response["id"] == "alpaca-test-order"
    assert len(session.calls) == 1


def test_read_only_alpaca_request_remains_available():
    session = _FakeSession(payload={"status": "ACTIVE"})
    client = _client(session=session)

    response = client._request("GET", "/v2/account", request_type="trading")

    assert response == {"status": "ACTIVE"}
    assert len(session.calls) == 1
