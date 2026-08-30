from __future__ import annotations

import importlib.util
import sys
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import requests

from aureon.accounting.hmrc_mutation_boundary import (
    HMRCMutationHold,
    HMRCMutationRegistry,
    bind_hmrc_mutation_registry,
)
from aureon.governance.legacy_economic_unity import (
    LegacyEconomicCapability,
    LegacyEconomicUnityGateway,
)
from aureon.governance.legacy_unity_composition import (
    LegacyUnityCompositionHold,
    LegacyUnityIntentPlan,
)

ROOT = Path(__file__).resolve().parents[1]
HMRC_SOURCE = ROOT / "Kings_Accounting_Suite" / "core" / "hnc_hmrc_api.py"
CAPABILITY_ID = "legacy-capability:hmrc-vat-submit"
PATH = "/organisations/vat/123456789/returns"
BODY = {"finalised": True, "periodKey": "24A1", "vatDueSales": "12.34"}


def _load_hmrc_module():
    spec = importlib.util.spec_from_file_location("test_hnc_hmrc_api", HMRC_SOURCE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _capability() -> LegacyEconomicCapability:
    return LegacyEconomicCapability(
        capability_id=CAPABILITY_ID,
        source_file="Kings_Accounting_Suite/core/hnc_hmrc_api.py",
        source_symbol="HMRCApiClient._post",
        venue="hmrc",
        method="POST",
        path=PATH,
        operation="SUBMIT_VAT_RETURN",
        purpose="HMRC_FILING",
        body_bindings=(("period_key", "/periodKey"),),
        preserved_operations=("SUBMIT_VAT_RETURN",),
    )


def _plan(**overrides: Any) -> LegacyUnityIntentPlan:
    values: dict[str, Any] = {
        "capability_id": CAPABILITY_ID,
        "venue": "hmrc",
        "environment": "sandbox",
        "account_id_hash": sha256(b"hmrc-account").hexdigest(),
        "method": "POST",
        "path": PATH,
        "operation": "SUBMIT_VAT_RETURN",
        "purpose": "HMRC_FILING",
        "symbol": "VAT_RETURN",
        "side": "SUBMIT",
        "order_type": "DECLARATION",
        "quantity": None,
        "quote_quantity": None,
        "limit_price": None,
        "stop_price": None,
        "take_profit": None,
        "reduce_only": False,
        "client_order_id": "hmrc-vat-24A1",
        "authorization_receipt_id": "owner-authorization:hmrc-vat-24A1",
        "cycle_id": "tax-cycle:2026-24A1",
        "position_receipt_id": "hmrc-preflight:vat-24A1",
        "body": BODY,
        "body_bindings": {"period_key": "/periodKey"},
    }
    values.update(overrides)
    return LegacyUnityIntentPlan.create(**values)


class _Supplier:
    supplier_id = "test:trusted-hmrc-invocation"

    def __init__(self, *, hold: str | None = None) -> None:
        self.hold = hold
        self.calls: list[LegacyUnityIntentPlan] = []

    def supply_legacy_invocation(self, plan: LegacyUnityIntentPlan) -> object:
        self.calls.append(plan)
        if self.hold is not None:
            raise LegacyUnityCompositionHold(self.hold)
        return object()


class _Gateway(LegacyEconomicUnityGateway):
    def __init__(self, *, status: str = "EXECUTED") -> None:
        self.status = status
        self.calls: list[tuple[object, object]] = []
        self.transport_calls = 0

    @property
    def capabilities(self) -> tuple[LegacyEconomicCapability, ...]:
        return (_capability(),)

    def execute(self, invocation: object, *, transport: object) -> object:
        self.calls.append((invocation, transport))
        if self.status == "EXECUTED":
            self.transport_calls += 1
            result = transport()
            return SimpleNamespace(
                status="EXECUTED",
                provider_result=result,
                receipt={"reason": "executed"},
            )
        return SimpleNamespace(
            status=self.status,
            provider_result=None,
            receipt={"reason": "council_or_crown_hold"},
        )


def _registry(
    *,
    gateway: _Gateway | None = None,
    supplier: _Supplier | None = None,
) -> tuple[HMRCMutationRegistry, _Gateway, _Supplier]:
    actual_gateway = gateway or _Gateway()
    actual_supplier = supplier or _Supplier()
    registry = bind_hmrc_mutation_registry(
        gateway=actual_gateway,
        invocation_supplier=actual_supplier,
        plans=(_plan(),),
    )
    return registry, actual_gateway, actual_supplier


def test_registry_cannot_be_constructed_outside_factory() -> None:
    with pytest.raises(TypeError, match="use_bind_hmrc_mutation_registry"):
        HMRCMutationRegistry(
            _factory_token=object(),
            gateway=_Gateway(),
            invocation_supplier=_Supplier(),
            plans=(_plan(),),
        )


def test_exact_plan_runs_supplier_gateway_and_transport_once() -> None:
    registry, gateway, supplier = _registry()
    transport_calls = 0

    def transport() -> dict[str, str]:
        nonlocal transport_calls
        transport_calls += 1
        return {"receipt": "hmrc:sandbox:accepted"}

    result = registry.execute(
        environment="sandbox",
        method="POST",
        path=PATH,
        body=BODY,
        transport=transport,
    )

    assert result == {"receipt": "hmrc:sandbox:accepted"}
    assert supplier.calls == [_plan()]
    assert len(gateway.calls) == 1
    assert gateway.transport_calls == 1
    assert transport_calls == 1


@pytest.mark.parametrize(
    ("environment", "path", "body"),
    [
        ("production", PATH, BODY),
        ("sandbox", "/organisations/vat/other/returns", BODY),
        ("sandbox", PATH, {**BODY, "vatDueSales": "99.99"}),
    ],
)
def test_route_drift_holds_before_any_authority_or_transport(
    environment: str,
    path: str,
    body: dict[str, object],
) -> None:
    registry, gateway, supplier = _registry()
    with pytest.raises(
        HMRCMutationHold,
        match="exact_governed_hmrc_mutation_plan_required",
    ):
        registry.execute(
            environment=environment,
            method="POST",
            path=path,
            body=body,
            transport=lambda: pytest.fail("transport must not run"),
        )
    assert supplier.calls == []
    assert gateway.calls == []
    assert gateway.transport_calls == 0


def test_missing_hnc_auris_evidence_holds_before_gateway_and_transport() -> None:
    supplier = _Supplier(hold="complete_fresh_hnc_evidence_required")
    registry, gateway, _ = _registry(supplier=supplier)

    with pytest.raises(
        HMRCMutationHold,
        match="complete_fresh_hnc_evidence_required",
    ):
        registry.execute(
            environment="sandbox",
            method="POST",
            path=PATH,
            body=BODY,
            transport=lambda: pytest.fail("transport must not run"),
        )
    assert len(supplier.calls) == 1
    assert gateway.calls == []


def test_dual_key_hold_never_calls_transport() -> None:
    gateway = _Gateway(status="HOLD")
    registry, _, supplier = _registry(gateway=gateway)

    with pytest.raises(HMRCMutationHold, match="council_or_crown_hold"):
        registry.execute(
            environment="sandbox",
            method="POST",
            path=PATH,
            body=BODY,
            transport=lambda: pytest.fail("transport must not run"),
        )
    assert len(supplier.calls) == 1
    assert len(gateway.calls) == 1
    assert gateway.transport_calls == 0


def test_hmrc_client_mutations_require_registry_before_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_hmrc_module()
    client = module.HMRCApiClient(module.HMRCConfig(environment="sandbox"))
    calls: list[str] = []
    monkeypatch.setattr(requests, "post", lambda *a, **k: calls.append("POST"))
    monkeypatch.setattr(requests, "put", lambda *a, **k: calls.append("PUT"))
    monkeypatch.setattr(requests, "delete", lambda *a, **k: calls.append("DELETE"))

    for method, args in (
        (client._post, (PATH, BODY)),
        (client._put, (PATH, BODY)),
        (client._delete, (PATH,)),
    ):
        with pytest.raises(
            HMRCMutationHold,
            match="canonical_hmrc_mutation_registry_required",
        ):
            method(*args)
    assert calls == []


def test_hmrc_client_exact_registry_executes_one_sandbox_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_hmrc_module()
    registry, gateway, supplier = _registry()
    client = module.HMRCApiClient(
        module.HMRCConfig(environment="sandbox"),
        mutation_registry=registry,
    )
    client.token = module.OAuthToken(
        access_token="test-token",
        expires_in=3600,
        issued_at=10_000,
    )
    monkeypatch.setattr(module.time, "time", lambda: 10_001)
    calls: list[tuple[str, dict[str, object]]] = []

    class _Response:
        status_code = 201

        @staticmethod
        def json() -> dict[str, str]:
            return {"receipt": "hmrc:sandbox:accepted"}

    def fake_post(url: str, **kwargs: object) -> _Response:
        calls.append((url, kwargs))
        return _Response()

    monkeypatch.setattr(requests, "post", fake_post)
    result = client._post(PATH, BODY)

    assert result == {"receipt": "hmrc:sandbox:accepted"}
    assert len(calls) == 1
    assert calls[0][0] == f"https://test-api.service.hmrc.gov.uk{PATH}"
    assert calls[0][1]["json"] == BODY
    assert len(supplier.calls) == 1
    assert gateway.transport_calls == 1


def test_oauth_token_exchange_is_not_treated_as_filing_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_hmrc_module()
    client = module.HMRCApiClient(module.HMRCConfig(environment="sandbox"))
    calls = 0

    class _Response:
        status_code = 200
        headers = {"content-type": "application/json"}
        text = ""

        @staticmethod
        def json() -> dict[str, object]:
            return {
                "access_token": "test-access",
                "refresh_token": "test-refresh",
                "expires_in": 3600,
            }

    def fake_post(*args: object, **kwargs: object) -> _Response:
        nonlocal calls
        calls += 1
        return _Response()

    monkeypatch.setattr(requests, "post", fake_post)
    token = client._token_request(
        {
            "client_id": "test-client",
            "client_secret": "test-secret",
            "grant_type": "authorization_code",
            "code": "test-code",
        }
    )
    assert token.access_token == "test-access"
    assert calls == 1
