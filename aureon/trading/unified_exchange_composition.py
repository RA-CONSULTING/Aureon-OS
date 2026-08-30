"""Composition root for one HNC/Auris-governed unified exchange organism.

Nothing in this module starts daemons, reads credentials, or calls providers on
import.  An owner-controlled bootstrap supplies the independent Council and
Crown adapters plus the preserved legacy capability manifest.  The resulting
client receives both the authority boundary and the 10-9-1 invocation supplier
as one inseparable pair.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from aureon.autonomous.aureon_agent_company_brain_fabric import (
    CANONICAL_AGENT_COMPANY_ROLE_COUNT,
    company_brain_fabric_report,
)
from aureon.autonomous.aureon_ten_nine_one_thought_path import (
    LocalHncAurisEvidenceResolver,
    TenNineOneEvidenceResolver,
)
from aureon.governance.cognition_gate import (
    TrustedCouncilReceiptSupplier,
    TrustedCrownReceiptSupplier,
)
from aureon.governance.crown_voice import TrustedCrownVoiceResolver
from aureon.governance.druid_voice import TrustedDruidSeatResolver
from aureon.governance.economic_boundary import (
    EconomicGovernanceBoundary,
    bind_economic_governance_boundary,
)
from aureon.governance.legacy_economic_unity import (
    LegacyEconomicCapability,
    LegacyEconomicUnityGateway,
    bind_legacy_economic_unity_gateway,
)
from aureon.governance.legacy_unity_composition import (
    HncAurisLegacyInvocationSupplier,
    bind_hnc_auris_legacy_invocation_supplier,
)
from aureon.governance.runtime_voice_suppliers import (
    TrustedAurisNodeResolverFactory,
    TrustedDruidSeatResolverFactory,
    bind_celtic_governance_voice_suppliers,
)
from aureon.governance.workforce_druid_resolver import (
    DEFAULT_WORKFORCE_DRUID_ROLES,
    TrustedWorkforceDecisionEngine,
    WorkforceDruidResolverFactory,
    bind_workforce_druid_resolver_factory,
)
from aureon.swarm.auris_node_receipts import TrustedAurisNodeResolver


@dataclass(frozen=True, slots=True)
class UnifiedExchangeUnityComposition:
    """The four inseparable runtime pieces of the migrated shared client."""

    client: Any
    economic_boundary: EconomicGovernanceBoundary
    legacy_unity_gateway: LegacyEconomicUnityGateway
    invocation_supplier: HncAurisLegacyInvocationSupplier
    council_receipt_supplier: TrustedCouncilReceiptSupplier
    crown_receipt_supplier: TrustedCrownReceiptSupplier
    capability_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.economic_boundary, EconomicGovernanceBoundary):
            raise TypeError("economic_governance_boundary_required")
        if not isinstance(self.legacy_unity_gateway, LegacyEconomicUnityGateway):
            raise TypeError("legacy_economic_unity_gateway_required")
        if not isinstance(
            self.invocation_supplier,
            HncAurisLegacyInvocationSupplier,
        ):
            raise TypeError("hnc_auris_legacy_invocation_supplier_required")
        if not isinstance(
            self.council_receipt_supplier,
            TrustedCouncilReceiptSupplier,
        ):
            raise TypeError("trusted_council_receipt_supplier_required")
        if not isinstance(
            self.crown_receipt_supplier,
            TrustedCrownReceiptSupplier,
        ):
            raise TypeError("trusted_crown_receipt_supplier_required")
        if self.council_receipt_supplier is self.crown_receipt_supplier:
            raise ValueError("independent_council_and_crown_suppliers_required")
        if type(self.capability_count) is not int or self.capability_count <= 0:
            raise ValueError("positive_legacy_capability_count_required")

    def bind_hmrc_mutation_registry(
        self,
        plans: Collection[Any],
    ) -> Any:
        """Attach exact HMRC filing plans to this same governed organism."""

        from aureon.accounting.hmrc_mutation_boundary import (
            bind_hmrc_mutation_registry,
        )

        return bind_hmrc_mutation_registry(
            gateway=self.legacy_unity_gateway,
            invocation_supplier=self.invocation_supplier,
            plans=plans,
        )


@dataclass(frozen=True, slots=True)
class WorkforceCelticUnityComposition:
    """One complete cloud workforce seated inside the governed exchange unity."""

    exchange: UnifiedExchangeUnityComposition
    workforce: TrustedWorkforceDecisionEngine
    brain_fabric_report: Mapping[str, Any]
    druid_resolver_factory: WorkforceDruidResolverFactory

    def __post_init__(self) -> None:
        if not isinstance(self.exchange, UnifiedExchangeUnityComposition):
            raise TypeError("unified_exchange_unity_composition_required")
        if not isinstance(self.workforce, TrustedWorkforceDecisionEngine):
            raise TypeError("trusted_workforce_decision_engine_required")
        if not isinstance(self.druid_resolver_factory, WorkforceDruidResolverFactory):
            raise TypeError("workforce_druid_resolver_factory_required")
        if not isinstance(self.brain_fabric_report, Mapping):
            raise TypeError("brain_fabric_report_required")
        expected = CANONICAL_AGENT_COMPANY_ROLE_COUNT
        report = self.brain_fabric_report
        if not (
            report.get("ready") is True
            and report.get("status") == "brain_fabric_ready"
            and report.get("canonical_role_count") == expected
            and report.get("agent_brain_count") == expected
            and report.get("process_brain_count") == expected
            and report.get("brain_passport_count") == expected * 2
            and report.get("hnc_routed_brain_count") == expected * 2
            and report.get("distinct_hnc_routing_receipt_count") == expected * 2
            and report.get("all_brains_hnc_routed") is True
            and report.get("truth_gate_enforced") is True
            and report.get("provider_mode") == "ollama_cloud_primary"
            and report.get("decision_authority") == "aureon_internal"
            and report.get("codex_role") == "senior_review_and_veto_only"
            and report.get("codex_implementation_allowed") is False
            and report.get("tools_enabled") is False
            and report.get("action_eligible") is False
            and report.get("economic_eligible") is False
        ):
            raise ValueError("complete_truth_gated_agent_company_brain_fabric_required")


def build_unified_exchange_unity_composition(
    *,
    council_receipt_supplier: TrustedCouncilReceiptSupplier,
    crown_receipt_supplier: TrustedCrownReceiptSupplier,
    trusted_council_supplier_ids: frozenset[str],
    trusted_crown_supplier_ids: frozenset[str],
    capabilities: Collection[LegacyEconomicCapability],
    evidence_resolver: TenNineOneEvidenceResolver | None = None,
    trusted_evidence_resolver_ids: frozenset[str] | None = None,
    client_factory: Callable[..., Any] | None = None,
    bus: Any = None,
    pair_max_age_s: float = 30.0,
    active_wait_s: float = 0.0,
    clock: Callable[[], float] = time.time,
) -> UnifiedExchangeUnityComposition:
    """Bind one fail-closed shared exchange organism without executing it."""

    capability_set = tuple(capabilities)
    if not capability_set:
        raise ValueError("legacy_capabilities_must_be_nonempty")
    boundary = bind_economic_governance_boundary(
        council_receipt_supplier=council_receipt_supplier,
        crown_receipt_supplier=crown_receipt_supplier,
        trusted_council_supplier_ids=trusted_council_supplier_ids,
        trusted_crown_supplier_ids=trusted_crown_supplier_ids,
        provider_max_age_s=pair_max_age_s,
        governance_max_age_s=pair_max_age_s,
        clock=clock,
    )
    gateway = bind_legacy_economic_unity_gateway(
        boundary=boundary,
        capabilities=capability_set,
    )
    resolver = evidence_resolver
    if resolver is None:
        resolver = LocalHncAurisEvidenceResolver(
            bus=bus,
            require_active_pair=True,
            active_wait_s=active_wait_s,
            pair_max_age_s=pair_max_age_s,
        )
        resolver_allowlist = frozenset({resolver.resolver_id})
    else:
        if not trusted_evidence_resolver_ids:
            raise ValueError("trusted_evidence_resolver_ids_required")
        resolver_allowlist = trusted_evidence_resolver_ids
    invocation_supplier = bind_hnc_auris_legacy_invocation_supplier(
        resolver=resolver,
        trusted_resolver_ids=resolver_allowlist,
        max_age_s=pair_max_age_s,
        clock=clock,
    )
    if client_factory is None:
        from aureon.trading.unified_exchange_client import MultiExchangeClient

        client_factory = MultiExchangeClient
    client = client_factory(
        legacy_unity_gateway=gateway,
        legacy_invocation_supplier=invocation_supplier,
    )
    return UnifiedExchangeUnityComposition(
        client=client,
        economic_boundary=boundary,
        legacy_unity_gateway=gateway,
        invocation_supplier=invocation_supplier,
        council_receipt_supplier=council_receipt_supplier,
        crown_receipt_supplier=crown_receipt_supplier,
        capability_count=len(capability_set),
    )


def build_celtic_unified_exchange_unity_composition(
    *,
    council_supplier_id: str,
    crown_supplier_id: str,
    trusted_council_supplier_ids: Collection[str],
    trusted_crown_supplier_ids: Collection[str],
    auris_node_resolver: TrustedAurisNodeResolver | None = None,
    auris_resolver_factory: TrustedAurisNodeResolverFactory | None = None,
    crown_voice_resolver: TrustedCrownVoiceResolver,
    capabilities: Collection[LegacyEconomicCapability],
    druid_seat_resolver: TrustedDruidSeatResolver | None = None,
    druid_resolver_factory: TrustedDruidSeatResolverFactory | None = None,
    evidence_resolver: TenNineOneEvidenceResolver | None = None,
    trusted_evidence_resolver_ids: frozenset[str] | None = None,
    client_factory: Callable[..., Any] | None = None,
    bus: Any = None,
    pair_max_age_s: float = 30.0,
    active_wait_s: float = 0.0,
    clock: Callable[[], float] = time.time,
    civil_date_provider: Callable[[], date] = date.today,
) -> UnifiedExchangeUnityComposition:
    """Seat the canonical Celtic voices, then bind the whole exchange organism."""

    voices = bind_celtic_governance_voice_suppliers(
        council_supplier_id=council_supplier_id,
        crown_supplier_id=crown_supplier_id,
        trusted_council_supplier_ids=trusted_council_supplier_ids,
        trusted_crown_supplier_ids=trusted_crown_supplier_ids,
        auris_node_resolver=auris_node_resolver,
        auris_resolver_factory=auris_resolver_factory,
        druid_seat_resolver=druid_seat_resolver,
        druid_resolver_factory=druid_resolver_factory,
        crown_voice_resolver=crown_voice_resolver,
        max_age_s=pair_max_age_s,
        clock=clock,
        civil_date_provider=civil_date_provider,
    )
    return build_unified_exchange_unity_composition(
        council_receipt_supplier=voices.council_receipt_supplier,
        crown_receipt_supplier=voices.crown_receipt_supplier,
        trusted_council_supplier_ids=frozenset(
            value.casefold() for value in trusted_council_supplier_ids
        ),
        trusted_crown_supplier_ids=frozenset(
            value.casefold() for value in trusted_crown_supplier_ids
        ),
        capabilities=capabilities,
        evidence_resolver=evidence_resolver,
        trusted_evidence_resolver_ids=trusted_evidence_resolver_ids,
        client_factory=client_factory,
        bus=bus,
        pair_max_age_s=pair_max_age_s,
        active_wait_s=active_wait_s,
        clock=clock,
    )


def build_workforce_celtic_unified_exchange_unity_composition(
    *,
    workforce: TrustedWorkforceDecisionEngine,
    workforce_factory_id: str,
    workforce_resolver_id: str,
    workforce_issuer_id_prefix: str,
    trusted_workforce_factory_ids: Collection[str],
    council_supplier_id: str,
    crown_supplier_id: str,
    trusted_council_supplier_ids: Collection[str],
    trusted_crown_supplier_ids: Collection[str],
    auris_node_resolver: TrustedAurisNodeResolver | None = None,
    auris_resolver_factory: TrustedAurisNodeResolverFactory | None = None,
    crown_voice_resolver: TrustedCrownVoiceResolver,
    capabilities: Collection[LegacyEconomicCapability],
    seat_roles: Mapping[str, str] = DEFAULT_WORKFORCE_DRUID_ROLES,
    evidence_resolver: TenNineOneEvidenceResolver | None = None,
    trusted_evidence_resolver_ids: frozenset[str] | None = None,
    client_factory: Callable[..., Any] | None = None,
    bus: Any = None,
    pair_max_age_s: float = 30.0,
    active_wait_s: float = 0.0,
    clock: Callable[[], float] = time.time,
    civil_date_provider: Callable[[], date] = date.today,
) -> WorkforceCelticUnityComposition:
    """Seat a complete 41+41 cloud brain fabric in the governed organism."""

    if not isinstance(workforce, TrustedWorkforceDecisionEngine):
        raise TypeError("trusted_workforce_decision_engine_required")
    report = company_brain_fabric_report(workforce)
    expected = CANONICAL_AGENT_COMPANY_ROLE_COUNT
    if not (
        report.get("ready") is True
        and report.get("status") == "brain_fabric_ready"
        and report.get("canonical_role_count") == expected
        and report.get("agent_brain_count") == expected
        and report.get("process_brain_count") == expected
        and report.get("brain_passport_count") == expected * 2
        and report.get("hnc_routed_brain_count") == expected * 2
        and report.get("distinct_hnc_routing_receipt_count") == expected * 2
        and report.get("all_brains_hnc_routed") is True
        and report.get("truth_gate_enforced") is True
        and report.get("provider_mode") == "ollama_cloud_primary"
        and report.get("action_eligible") is False
        and report.get("economic_eligible") is False
    ):
        raise ValueError("complete_truth_gated_agent_company_brain_fabric_required")
    druid_factory = bind_workforce_druid_resolver_factory(
        factory_id=workforce_factory_id,
        resolver_id=workforce_resolver_id,
        issuer_id_prefix=workforce_issuer_id_prefix,
        trusted_factory_ids=trusted_workforce_factory_ids,
        workforce=workforce,
        seat_roles=seat_roles,
        max_age_s=pair_max_age_s,
        clock=clock,
    )
    exchange = build_celtic_unified_exchange_unity_composition(
        council_supplier_id=council_supplier_id,
        crown_supplier_id=crown_supplier_id,
        trusted_council_supplier_ids=trusted_council_supplier_ids,
        trusted_crown_supplier_ids=trusted_crown_supplier_ids,
        auris_node_resolver=auris_node_resolver,
        auris_resolver_factory=auris_resolver_factory,
        druid_resolver_factory=druid_factory,
        crown_voice_resolver=crown_voice_resolver,
        capabilities=capabilities,
        evidence_resolver=evidence_resolver,
        trusted_evidence_resolver_ids=trusted_evidence_resolver_ids,
        client_factory=client_factory,
        bus=bus,
        pair_max_age_s=pair_max_age_s,
        active_wait_s=active_wait_s,
        clock=clock,
        civil_date_provider=civil_date_provider,
    )
    return WorkforceCelticUnityComposition(
        exchange=exchange,
        workforce=workforce,
        brain_fabric_report=dict(report),
        druid_resolver_factory=druid_factory,
    )


__all__ = [
    "UnifiedExchangeUnityComposition",
    "WorkforceCelticUnityComposition",
    "build_celtic_unified_exchange_unity_composition",
    "build_unified_exchange_unity_composition",
    "build_workforce_celtic_unified_exchange_unity_composition",
]
