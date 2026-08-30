from __future__ import annotations

from hashlib import sha256
from typing import Any

import pytest

from aureon.accounting.hmrc_mutation_boundary import HMRCMutationRegistry
from aureon.governance.legacy_economic_unity import LegacyEconomicCapability
from aureon.governance.legacy_unity_composition import LegacyUnityIntentPlan
from aureon.trading.unified_exchange_composition import (
    build_celtic_unified_exchange_unity_composition,
    build_unified_exchange_unity_composition,
    build_workforce_celtic_unified_exchange_unity_composition,
)


class _CouncilSupplier:
    supplier_id = "aureon:test:council"

    def __init__(self) -> None:
        self.calls = 0

    def supply_council_evidence(self, _request):
        self.calls += 1
        raise AssertionError("composition_must_not_evaluate_council")


class _CrownSupplier:
    supplier_id = "aureon:test:crown"

    def __init__(self) -> None:
        self.calls = 0

    def supply_crown_receipt(self, _request):
        self.calls += 1
        raise AssertionError("composition_must_not_evaluate_crown")


class _EvidenceResolver:
    resolver_id = "aureon:test:10-9-1"

    def __init__(self) -> None:
        self.calls = 0

    def resolve_hnc_evidence(self, _request):
        self.calls += 1
        raise AssertionError("composition_must_not_read_hnc")

    def resolve_auris_evidence(
        self,
        _request,
        *,
        answer_digest: str,
        hnc_receipt_id: str,
    ):
        del answer_digest, hnc_receipt_id
        self.calls += 1
        raise AssertionError("composition_must_not_read_auris")


class _NodeResolver:
    def __init__(self) -> None:
        self.calls = 0

    def resolve_auris_node_evidence(self, _seat):
        self.calls += 1
        raise AssertionError("composition_must_not_read_node_evidence")


class _DruidResolver:
    def __init__(self) -> None:
        self.calls = 0

    def trusted_druid_seat_bindings(self):
        self.calls += 1
        raise AssertionError("composition_must_not_read_druid_bindings")

    def resolve_druid_seat_voice(self, *_args):
        self.calls += 1
        raise AssertionError("composition_must_not_read_druid_voice")


class _CrownVoiceResolver:
    def __init__(self) -> None:
        self.calls = 0

    def resolve_crown_voice_evidence(self, *_args):
        self.calls += 1
        raise AssertionError("composition_must_not_read_crown_voice")


class _CloudWorkforce:
    def __init__(self, *, complete: bool = True) -> None:
        self.complete = complete
        self.calls = 0

    def process_id_for_role(self, role: str) -> str:
        self.calls += 1
        return f"agent_company_role_cycle:{role}"

    def decide(self, **_kwargs: Any):
        self.calls += 1
        raise AssertionError("composition_must_not_call_cloud_brains")

    def report(self) -> dict[str, Any]:
        count = 41 if self.complete else 40
        passports = [
            {
                "receipt_id": f"brain:{index:064x}",
                "subject_type": "agent" if index < 41 else "process",
            }
            for index in range(82)
        ]
        return {
            "brain_fabric_ready": self.complete,
            "all_brains_hnc_routed": self.complete,
            "agent_brain_count": count,
            "process_brain_count": count,
            "hnc_routed_brain_count": count * 2,
            "distinct_hnc_routing_receipt_count": count * 2,
            "distinct_cloud_model_count": 4,
            "provider_mode": "ollama_cloud_primary" if self.complete else "hold",
            "truth_gate_enforced": True,
            "unready_agents": [] if self.complete else ["one-agent"],
            "unready_processes": [] if self.complete else ["one-process"],
            "passports": passports,
        }


def _capability() -> LegacyEconomicCapability:
    return LegacyEconomicCapability(
        capability_id="legacy-capability:unified-exchange:kraken:market-order",
        source_file="aureon/trading/unified_exchange_client.py",
        source_symbol="UnifiedExchangeClient.place_market_order",
        venue="kraken",
        method="POST",
        path="/0/private/AddOrder",
        operation="MARKET_ORDER",
        purpose="ENTRY",
        body_bindings=tuple(
            sorted(
                {
                    "client_order_id": "/cl_ord_id",
                    "order_type": "/ordertype",
                    "quote_quantity": "/volume",
                    "side": "/type",
                    "symbol": "/pair",
                }.items()
            )
        ),
        preserved_operations=("MARKET_ORDER",),
    )


def _hmrc_capability() -> LegacyEconomicCapability:
    return LegacyEconomicCapability(
        capability_id="legacy-capability:hmrc-vat-submit",
        source_file="Kings_Accounting_Suite/core/hnc_hmrc_api.py",
        source_symbol="HMRCApiClient._post",
        venue="hmrc",
        method="POST",
        path="/organisations/vat/123456789/returns",
        operation="SUBMIT_VAT_RETURN",
        purpose="HMRC_FILING",
        body_bindings=(("period_key", "/periodKey"),),
        preserved_operations=("SUBMIT_VAT_RETURN",),
    )


def _hmrc_plan() -> LegacyUnityIntentPlan:
    return LegacyUnityIntentPlan.create(
        capability_id="legacy-capability:hmrc-vat-submit",
        venue="hmrc",
        environment="sandbox",
        account_id_hash=sha256(b"hmrc-account").hexdigest(),
        method="POST",
        path="/organisations/vat/123456789/returns",
        operation="SUBMIT_VAT_RETURN",
        purpose="HMRC_FILING",
        symbol="VAT_RETURN",
        side="SUBMIT",
        order_type="DECLARATION",
        quantity=None,
        quote_quantity=None,
        limit_price=None,
        stop_price=None,
        take_profit=None,
        reduce_only=False,
        client_order_id="hmrc-vat-24A1",
        authorization_receipt_id="owner-authorization:hmrc-vat-24A1",
        cycle_id="tax-cycle:2026-24A1",
        position_receipt_id="hmrc-preflight:vat-24A1",
        body={
            "finalised": True,
            "periodKey": "24A1",
            "vatDueSales": "12.34",
        },
        body_bindings={"period_key": "/periodKey"},
    )


def test_composition_binds_all_four_layers_without_starting_any_layer() -> None:
    council = _CouncilSupplier()
    crown = _CrownSupplier()
    evidence = _EvidenceResolver()
    client_calls: list[dict[str, Any]] = []

    def client_factory(**kwargs: Any) -> dict[str, Any]:
        client_calls.append(kwargs)
        return {"kind": "fake-unified-exchange"}

    composition = build_unified_exchange_unity_composition(
        council_receipt_supplier=council,
        crown_receipt_supplier=crown,
        trusted_council_supplier_ids=frozenset({council.supplier_id}),
        trusted_crown_supplier_ids=frozenset({crown.supplier_id}),
        capabilities=(_capability(),),
        evidence_resolver=evidence,
        trusted_evidence_resolver_ids=frozenset({evidence.resolver_id}),
        client_factory=client_factory,
    )

    assert composition.client == {"kind": "fake-unified-exchange"}
    assert composition.capability_count == 1
    assert client_calls == [
        {
            "legacy_unity_gateway": composition.legacy_unity_gateway,
            "legacy_invocation_supplier": composition.invocation_supplier,
        }
    ]
    assert composition.legacy_unity_gateway.capabilities == (_capability(),)
    assert composition.council_receipt_supplier is council
    assert composition.crown_receipt_supplier is crown
    assert council.calls == 0
    assert crown.calls == 0
    assert evidence.calls == 0


def test_same_canonical_composition_binds_hmrc_without_evaluating_voices() -> None:
    council = _CouncilSupplier()
    crown = _CrownSupplier()
    evidence = _EvidenceResolver()
    composition = build_unified_exchange_unity_composition(
        council_receipt_supplier=council,
        crown_receipt_supplier=crown,
        trusted_council_supplier_ids=frozenset({council.supplier_id}),
        trusted_crown_supplier_ids=frozenset({crown.supplier_id}),
        capabilities=(_hmrc_capability(),),
        evidence_resolver=evidence,
        trusted_evidence_resolver_ids=frozenset({evidence.resolver_id}),
        client_factory=lambda **_kwargs: {"kind": "shared-organism"},
    )

    registry = composition.bind_hmrc_mutation_registry((_hmrc_plan(),))

    assert isinstance(registry, HMRCMutationRegistry)
    assert registry.route_count == 1
    assert composition.capability_count == 1
    assert council.calls == crown.calls == evidence.calls == 0


def test_composition_rejects_empty_legacy_manifest() -> None:
    with pytest.raises(ValueError, match="legacy_capabilities_must_be_nonempty"):
        build_unified_exchange_unity_composition(
            council_receipt_supplier=_CouncilSupplier(),
            crown_receipt_supplier=_CrownSupplier(),
            trusted_council_supplier_ids=frozenset({"aureon:test:council"}),
            trusted_crown_supplier_ids=frozenset({"aureon:test:crown"}),
            capabilities=(),
            evidence_resolver=_EvidenceResolver(),
            client_factory=lambda **_kwargs: object(),
        )


def test_composition_requires_distinct_allowlisted_council_and_crown() -> None:
    council = _CouncilSupplier()
    crown = _CrownSupplier()

    with pytest.raises(ValueError, match="council_supplier_not_allowlisted"):
        build_unified_exchange_unity_composition(
            council_receipt_supplier=council,
            crown_receipt_supplier=crown,
            trusted_council_supplier_ids=frozenset({"aureon:other"}),
            trusted_crown_supplier_ids=frozenset({crown.supplier_id}),
            capabilities=(_capability(),),
            evidence_resolver=_EvidenceResolver(),
            trusted_evidence_resolver_ids=frozenset({"aureon:test:10-9-1"}),
            client_factory=lambda **_kwargs: object(),
        )


def test_client_factory_failure_does_not_fall_back_to_ungoverned_client() -> None:
    council = _CouncilSupplier()
    crown = _CrownSupplier()

    def fail_factory(**_kwargs: Any) -> object:
        raise RuntimeError("client-factory-failed")

    with pytest.raises(RuntimeError, match="client-factory-failed"):
        build_unified_exchange_unity_composition(
            council_receipt_supplier=council,
            crown_receipt_supplier=crown,
            trusted_council_supplier_ids=frozenset({council.supplier_id}),
            trusted_crown_supplier_ids=frozenset({crown.supplier_id}),
            capabilities=(_capability(),),
            evidence_resolver=_EvidenceResolver(),
            trusted_evidence_resolver_ids=frozenset({"aureon:test:10-9-1"}),
            client_factory=fail_factory,
        )


def test_custom_evidence_resolver_is_never_self_allowlisted() -> None:
    council = _CouncilSupplier()
    crown = _CrownSupplier()

    with pytest.raises(ValueError, match="trusted_evidence_resolver_ids_required"):
        build_unified_exchange_unity_composition(
            council_receipt_supplier=council,
            crown_receipt_supplier=crown,
            trusted_council_supplier_ids=frozenset({council.supplier_id}),
            trusted_crown_supplier_ids=frozenset({crown.supplier_id}),
            capabilities=(_capability(),),
            evidence_resolver=_EvidenceResolver(),
            client_factory=lambda **_kwargs: object(),
        )


def test_celtic_composition_binds_voice_bank_and_all_runtime_layers_inertly() -> None:
    node = _NodeResolver()
    druid = _DruidResolver()
    crown = _CrownVoiceResolver()
    evidence = _EvidenceResolver()
    client_calls: list[dict[str, Any]] = []

    def client_factory(**kwargs: Any) -> dict[str, Any]:
        client_calls.append(kwargs)
        return {"kind": "celtic-unified-exchange"}

    composition = build_celtic_unified_exchange_unity_composition(
        council_supplier_id="aureon:test:celtic-council",
        crown_supplier_id="aureon:test:independent-crown",
        trusted_council_supplier_ids=frozenset(
            {"aureon:test:celtic-council"}
        ),
        trusted_crown_supplier_ids=frozenset(
            {"aureon:test:independent-crown"}
        ),
        auris_node_resolver=node,
        druid_seat_resolver=druid,
        crown_voice_resolver=crown,
        capabilities=(_capability(),),
        evidence_resolver=evidence,
        trusted_evidence_resolver_ids=frozenset({evidence.resolver_id}),
        client_factory=client_factory,
    )

    assert composition.client == {"kind": "celtic-unified-exchange"}
    assert composition.capability_count == 1
    assert composition.council_receipt_supplier.supplier_id == (
        "aureon:test:celtic-council"
    )
    assert composition.crown_receipt_supplier.supplier_id == (
        "aureon:test:independent-crown"
    )
    assert client_calls == [
        {
            "legacy_unity_gateway": composition.legacy_unity_gateway,
            "legacy_invocation_supplier": composition.invocation_supplier,
        }
    ]
    assert node.calls == druid.calls == crown.calls == evidence.calls == 0


def test_complete_cloud_workforce_is_seated_without_running_any_brain() -> None:
    workforce = _CloudWorkforce()
    node = _NodeResolver()
    crown = _CrownVoiceResolver()
    evidence = _EvidenceResolver()

    composition = build_workforce_celtic_unified_exchange_unity_composition(
        workforce=workforce,
        workforce_factory_id="aureon:test:workforce-druid-factory",
        workforce_resolver_id="aureon:test:workforce-druid-resolver",
        workforce_issuer_id_prefix="aureon:test:workforce-druid-issuer",
        trusted_workforce_factory_ids=frozenset(
            {"aureon:test:workforce-druid-factory"}
        ),
        council_supplier_id="aureon:test:celtic-council",
        crown_supplier_id="aureon:test:independent-crown",
        trusted_council_supplier_ids=frozenset(
            {"aureon:test:celtic-council"}
        ),
        trusted_crown_supplier_ids=frozenset(
            {"aureon:test:independent-crown"}
        ),
        auris_node_resolver=node,
        crown_voice_resolver=crown,
        capabilities=(_capability(),),
        evidence_resolver=evidence,
        trusted_evidence_resolver_ids=frozenset({evidence.resolver_id}),
        client_factory=lambda **_kwargs: {"kind": "workforce-celtic-unity"},
    )

    assert composition.exchange.client == {"kind": "workforce-celtic-unity"}
    assert composition.workforce is workforce
    assert composition.brain_fabric_report["agent_brain_count"] == 41
    assert composition.brain_fabric_report["process_brain_count"] == 41
    assert composition.brain_fabric_report["brain_passport_count"] == 82
    assert composition.druid_resolver_factory.factory_id == (
        "aureon:test:workforce-druid-factory"
    )
    assert workforce.calls == node.calls == crown.calls == evidence.calls == 0


def test_incomplete_cloud_workforce_holds_before_seating_or_client_build() -> None:
    client_calls: list[dict[str, Any]] = []

    with pytest.raises(
        ValueError,
        match="complete_truth_gated_agent_company_brain_fabric_required",
    ):
        build_workforce_celtic_unified_exchange_unity_composition(
            workforce=_CloudWorkforce(complete=False),
            workforce_factory_id="aureon:test:workforce-druid-factory",
            workforce_resolver_id="aureon:test:workforce-druid-resolver",
            workforce_issuer_id_prefix="aureon:test:workforce-druid-issuer",
            trusted_workforce_factory_ids=frozenset(
                {"aureon:test:workforce-druid-factory"}
            ),
            council_supplier_id="aureon:test:celtic-council",
            crown_supplier_id="aureon:test:independent-crown",
            trusted_council_supplier_ids=frozenset(
                {"aureon:test:celtic-council"}
            ),
            trusted_crown_supplier_ids=frozenset(
                {"aureon:test:independent-crown"}
            ),
            auris_node_resolver=_NodeResolver(),
            crown_voice_resolver=_CrownVoiceResolver(),
            capabilities=(_capability(),),
            evidence_resolver=_EvidenceResolver(),
            trusted_evidence_resolver_ids=frozenset({"aureon:test:10-9-1"}),
            client_factory=lambda **kwargs: client_calls.append(kwargs),
        )

    assert client_calls == []
