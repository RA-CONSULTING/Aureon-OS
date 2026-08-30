from __future__ import annotations

from datetime import date
from typing import Any

import pytest

import aureon.governance.runtime_voice_suppliers as voice_module
from aureon.governance.celtic_voice_bank import CelticSeatedDruidResolver
from aureon.governance.cognition_gate import CognitionGovernanceRequest
from aureon.governance.runtime_voice_suppliers import (
    CelticCouncilReceiptSupplier,
    bind_celtic_council_receipt_supplier,
    bind_celtic_governance_voice_suppliers,
)
from aureon.swarm.druidic_council import REQUIRED_SEATS

NOW = 1_786_480_000.0
COUNCIL_ID = "resolver:trusted-council-runtime:v1"
CROWN_ID = "resolver:trusted-crown-runtime:v1"


class _NodeResolver:
    def __init__(self) -> None:
        self.calls = 0

    def resolve_auris_node_evidence(self, _seat: str):
        self.calls += 1
        raise AssertionError("binding_must_not_resolve_node_evidence")


class _DruidResolver:
    def __init__(self) -> None:
        self.calls = 0

    def trusted_druid_seat_bindings(self):
        self.calls += 1
        raise AssertionError("binding_must_not_resolve_druid_bindings")

    def resolve_druid_seat_voice(
        self,
        _seat: str,
        _proposal_digest: str,
        _prompt_digest: str,
    ):
        self.calls += 1
        raise AssertionError("binding_must_not_resolve_druid_voice")


class _CrownResolver:
    def __init__(self) -> None:
        self.calls = 0

    def resolve_crown_voice_evidence(
        self,
        _proposal_digest: str,
        _prompt_digest: str,
    ):
        self.calls += 1
        raise AssertionError("binding_must_not_resolve_crown_voice")


class _OmniResolver(_NodeResolver, _DruidResolver, _CrownResolver):
    def __init__(self) -> None:
        self.calls = 0


class _DruidFactory:
    factory_id = "aureon:test:druid-factory"

    def __init__(self, resolver: _DruidResolver) -> None:
        self.resolver = resolver
        self.calls = 0

    def build_druid_seat_resolver(self, request, auris_node_receipts):
        assert request == _request()
        assert len(auris_node_receipts) == 4
        self.calls += 1
        return self.resolver


class _NodeFactory:
    factory_id = "aureon:test:auris-node-factory"

    def __init__(self) -> None:
        self.calls = 0
        self.resolvers: list[_NodeResolver] = []

    def build_auris_node_resolver(self, request):
        assert request == _request()
        self.calls += 1
        resolver = _NodeResolver()
        self.resolvers.append(resolver)
        return resolver


def _request() -> CognitionGovernanceRequest:
    return CognitionGovernanceRequest(
        schema="aureon.cognition-governance-request.v1",
        prompt_digest="b" * 64,
        proposal_digest="a" * 64,
        proposal_json="{}",
        provider_receipt_ids=("provider:one",),
        provider_moment_digest="c" * 64,
        provider_source_timestamp=str(NOW - 2.0),
        target_provider_receipt_ids=("provider:one",),
        target_provider_moment_digest="c" * 64,
        target_provider_source_timestamp=str(NOW - 2.0),
        queen_verdict="APPROVED",
    )


def _bind(
    *,
    node: Any | None = None,
    druid: Any | None = None,
    crown: Any | None = None,
    civil_date_provider=lambda: date(2026, 8, 13),
):
    return bind_celtic_governance_voice_suppliers(
        council_supplier_id=COUNCIL_ID,
        crown_supplier_id=CROWN_ID,
        trusted_council_supplier_ids=frozenset({COUNCIL_ID}),
        trusted_crown_supplier_ids=frozenset({CROWN_ID}),
        auris_node_resolver=node or _NodeResolver(),
        druid_seat_resolver=druid or _DruidResolver(),
        crown_voice_resolver=crown or _CrownResolver(),
        max_age_s=30.0,
        clock=lambda: NOW,
        civil_date_provider=civil_date_provider,
    )


def test_binding_is_inert_and_seats_the_canonical_repository_voice_bank() -> None:
    node = _NodeResolver()
    druid = _DruidResolver()
    crown = _CrownResolver()

    suppliers = _bind(node=node, druid=druid, crown=crown)

    assert suppliers.voice_bank_receipt_id.startswith("celtic:voice_bank:")
    assert suppliers.council_receipt_supplier.supplier_id == COUNCIL_ID
    assert suppliers.crown_receipt_supplier.supplier_id == CROWN_ID
    assert node.calls == druid.calls == crown.calls == 0


def test_standalone_council_binder_accepts_only_matching_measurement_identity():
    node_factory = _NodeFactory()
    node_factory.factory_id = COUNCIL_ID
    druid = _DruidResolver()

    council = bind_celtic_council_receipt_supplier(
        council_supplier_id=COUNCIL_ID,
        trusted_council_supplier_ids={COUNCIL_ID},
        auris_resolver_factory=node_factory,
        druid_seat_resolver=druid,
        clock=lambda: NOW,
        civil_date_provider=lambda: date(2026, 8, 13),
    )

    assert isinstance(council, CelticCouncilReceiptSupplier)
    assert council.supplier_id == COUNCIL_ID
    assert node_factory.calls == 0
    assert druid.calls == 0

    node_factory.factory_id = "resolver:wrong-measurement"
    with pytest.raises(
        ValueError,
        match="council_supplier_node_resolver_binding_required",
    ):
        bind_celtic_council_receipt_supplier(
            council_supplier_id=COUNCIL_ID,
            trusted_council_supplier_ids={COUNCIL_ID},
            auris_resolver_factory=node_factory,
            druid_seat_resolver=druid,
        )


def test_two_voice_supply_uses_four_stable_nodes_same_request_and_season(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node = _NodeResolver()
    druid = _DruidResolver()
    crown = _CrownResolver()
    suppliers = _bind(node=node, druid=druid, crown=crown)
    issued_nodes: list[tuple[str, float, float]] = []

    def issue_node(*, seat, resolver, now, max_age_s):
        assert resolver is node
        issued_nodes.append((seat, now, max_age_s))
        return {
            "seat": seat,
            "resolver_id": COUNCIL_ID,
            "receipt_id": f"auris:node:{seat}",
        }

    def issue_council(**kwargs):
        assert kwargs["proposal_digest"] == "a" * 64
        assert kwargs["prompt_digest"] == "b" * 64
        assert kwargs["now"] == NOW
        assert kwargs["max_age_s"] == 30.0
        assert [item["seat"] for item in kwargs["auris_node_receipts"]] == list(
            REQUIRED_SEATS
        )
        resolver = kwargs["resolver"]
        assert isinstance(resolver, CelticSeatedDruidResolver)
        assert resolver.delegate is druid
        assert resolver.seasonal_gate == "lughnasadh"
        return {"data_status": "live", "receipt_id": "council:receipt"}

    def issue_crown(**kwargs):
        assert kwargs["proposal_digest"] == "a" * 64
        assert kwargs["prompt_digest"] == "b" * 64
        assert kwargs["resolver"] is crown
        assert kwargs["now"] == NOW
        assert kwargs["max_age_s"] == 30.0
        return {
            "data_status": "live",
            "resolver_id": CROWN_ID,
            "receipt_id": "crown:receipt",
        }

    monkeypatch.setattr(voice_module, "issue_auris_node_receipt", issue_node)
    monkeypatch.setattr(voice_module, "issue_trusted_druidic_council", issue_council)
    monkeypatch.setattr(voice_module, "issue_crown_voice_receipt", issue_crown)

    council_evidence = suppliers.council_receipt_supplier.supply_council_evidence(
        _request()
    )
    crown_receipt = suppliers.crown_receipt_supplier.supply_crown_receipt(_request())

    assert issued_nodes == [(seat, NOW, 30.0) for seat in REQUIRED_SEATS]
    assert council_evidence.council_receipt["receipt_id"] == "council:receipt"
    assert len(council_evidence.auris_node_receipts) == 4
    assert crown_receipt["receipt_id"] == "crown:receipt"
    assert node.calls == druid.calls == crown.calls == 0


def test_live_node_resolver_identity_must_match_council_supplier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    suppliers = _bind()
    monkeypatch.setattr(
        voice_module,
        "issue_auris_node_receipt",
        lambda **kwargs: {
            "seat": kwargs["seat"],
            "resolver_id": "resolver:other",
            "receipt_id": f"auris:node:{kwargs['seat']}",
        },
    )

    with pytest.raises(
        ValueError,
        match="council_supplier_node_resolver_binding_required",
    ):
        suppliers.council_receipt_supplier.supply_council_evidence(_request())


def test_live_crown_resolver_identity_must_match_crown_supplier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    suppliers = _bind()
    monkeypatch.setattr(
        voice_module,
        "issue_crown_voice_receipt",
        lambda **_kwargs: {
            "data_status": "live",
            "resolver_id": "resolver:other",
            "receipt_id": "crown:other",
        },
    )

    with pytest.raises(ValueError, match="crown_supplier_resolver_binding_required"):
        suppliers.crown_receipt_supplier.supply_crown_receipt(_request())


def test_underlying_measurement_council_and_crown_resolvers_must_be_distinct() -> None:
    resolver = _OmniResolver()

    with pytest.raises(
        ValueError,
        match="independent_measurement_council_and_crown_resolvers_required",
    ):
        _bind(node=resolver, druid=resolver, crown=resolver)


def test_supplier_allowlists_must_be_explicit_and_disjoint() -> None:
    with pytest.raises(ValueError, match="council_supplier_not_allowlisted"):
        bind_celtic_governance_voice_suppliers(
            council_supplier_id=COUNCIL_ID,
            crown_supplier_id=CROWN_ID,
            trusted_council_supplier_ids=frozenset({"resolver:other"}),
            trusted_crown_supplier_ids=frozenset({CROWN_ID}),
            auris_node_resolver=_NodeResolver(),
            druid_seat_resolver=_DruidResolver(),
            crown_voice_resolver=_CrownResolver(),
        )

    with pytest.raises(ValueError, match="supplier_allowlists_must_be_disjoint"):
        bind_celtic_governance_voice_suppliers(
            council_supplier_id=COUNCIL_ID,
            crown_supplier_id=CROWN_ID,
            trusted_council_supplier_ids=frozenset({COUNCIL_ID, CROWN_ID}),
            trusted_crown_supplier_ids=frozenset({CROWN_ID}),
            auris_node_resolver=_NodeResolver(),
            druid_seat_resolver=_DruidResolver(),
            crown_voice_resolver=_CrownResolver(),
        )


def test_suppliers_reject_untyped_requests_and_invalid_civil_dates() -> None:
    suppliers = _bind(civil_date_provider=lambda: "2026-08-13")

    with pytest.raises(TypeError, match="cognition_governance_request_required"):
        suppliers.council_receipt_supplier.supply_council_evidence({})  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="cognition_governance_request_required"):
        suppliers.crown_receipt_supplier.supply_crown_receipt({})  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="civil_date_required"):
        suppliers.council_receipt_supplier.supply_council_evidence(_request())


def test_supplier_classes_cannot_be_directly_constructed() -> None:
    with pytest.raises(
        TypeError,
        match="use_bind_celtic_governance_voice_suppliers",
    ):
        CelticCouncilReceiptSupplier(
            _factory_token=object(),
            supplier_id=COUNCIL_ID,
            auris_node_resolver=_NodeResolver(),
            auris_resolver_factory=None,
            druid_seat_resolver=_DruidResolver(),
            druid_resolver_factory=None,
            voice_bank_receipt={},
            max_age_s=30.0,
            clock=lambda: NOW,
            civil_date_provider=lambda: date(2026, 8, 13),
        )


def test_proposal_scoped_druid_factory_runs_only_after_four_nodes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node = _NodeResolver()
    druid = _DruidResolver()
    druid_factory = _DruidFactory(druid)
    crown = _CrownResolver()
    suppliers = bind_celtic_governance_voice_suppliers(
        council_supplier_id=COUNCIL_ID,
        crown_supplier_id=CROWN_ID,
        trusted_council_supplier_ids=frozenset({COUNCIL_ID}),
        trusted_crown_supplier_ids=frozenset({CROWN_ID}),
        auris_node_resolver=node,
        druid_resolver_factory=druid_factory,
        crown_voice_resolver=crown,
        clock=lambda: NOW,
        civil_date_provider=lambda: date(2026, 8, 13),
    )
    issued: list[str] = []
    monkeypatch.setattr(
        voice_module,
        "issue_auris_node_receipt",
        lambda **kwargs: (
            issued.append(kwargs["seat"])
            or {
                "seat": kwargs["seat"],
                "resolver_id": COUNCIL_ID,
                "receipt_id": f"auris:node:{kwargs['seat']}",
            }
        ),
    )
    monkeypatch.setattr(
        voice_module,
        "issue_trusted_druidic_council",
        lambda **kwargs: {
            "data_status": "live",
            "resolver_is_delegate": kwargs["resolver"].delegate is druid,
        },
    )

    assert druid_factory.calls == 0
    evidence = suppliers.council_receipt_supplier.supply_council_evidence(
        _request()
    )

    assert issued == list(REQUIRED_SEATS)
    assert druid_factory.calls == 1
    assert evidence.council_receipt["resolver_is_delegate"] is True


def test_proposal_scoped_auris_factory_rebinds_each_provider_moment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node_factory = _NodeFactory()
    druid = _DruidResolver()
    crown = _CrownResolver()
    suppliers = bind_celtic_governance_voice_suppliers(
        council_supplier_id=COUNCIL_ID,
        crown_supplier_id=CROWN_ID,
        trusted_council_supplier_ids=frozenset({COUNCIL_ID}),
        trusted_crown_supplier_ids=frozenset({CROWN_ID}),
        auris_resolver_factory=node_factory,
        druid_seat_resolver=druid,
        crown_voice_resolver=crown,
        clock=lambda: NOW,
        civil_date_provider=lambda: date(2026, 8, 13),
    )
    issued_resolvers: list[Any] = []

    def issue_node(**kwargs):
        issued_resolvers.append(kwargs["resolver"])
        return {
            "seat": kwargs["seat"],
            "resolver_id": COUNCIL_ID,
            "receipt_id": f"auris:node:{node_factory.calls}:{kwargs['seat']}",
        }

    monkeypatch.setattr(voice_module, "issue_auris_node_receipt", issue_node)
    monkeypatch.setattr(
        voice_module,
        "issue_trusted_druidic_council",
        lambda **_kwargs: {
            "data_status": "live",
            "receipt_id": f"council:receipt:{node_factory.calls}",
        },
    )

    first = suppliers.council_receipt_supplier.supply_council_evidence(_request())
    second = suppliers.council_receipt_supplier.supply_council_evidence(_request())

    assert node_factory.calls == 2
    assert first.council_receipt["receipt_id"] == "council:receipt:1"
    assert second.council_receipt["receipt_id"] == "council:receipt:2"
    assert issued_resolvers[:4] == [node_factory.resolvers[0]] * 4
    assert issued_resolvers[4:] == [node_factory.resolvers[1]] * 4
    assert node_factory.resolvers[0] is not node_factory.resolvers[1]


def test_static_and_request_scoped_auris_resolvers_are_mutually_exclusive() -> None:
    with pytest.raises(
        TypeError,
        match="exactly_one_trusted_auris_resolver_or_factory_required",
    ):
        bind_celtic_governance_voice_suppliers(
            council_supplier_id=COUNCIL_ID,
            crown_supplier_id=CROWN_ID,
            trusted_council_supplier_ids=frozenset({COUNCIL_ID}),
            trusted_crown_supplier_ids=frozenset({CROWN_ID}),
            auris_node_resolver=_NodeResolver(),
            auris_resolver_factory=_NodeFactory(),
            druid_seat_resolver=_DruidResolver(),
            crown_voice_resolver=_CrownResolver(),
        )
