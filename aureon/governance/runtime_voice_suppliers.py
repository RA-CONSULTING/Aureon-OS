"""Composition-root suppliers for Aureon's two independent governance voices.

The Council supplier seats the canonical repository Celtic voice bank on four
fresh Auris node receipts. The Crown supplier independently wraps an explicit
Queen/Chief resolver. Neither supplier invents a decision, coherence sample,
HNC/Auris field, or provider receipt: those values must come from separately
allowlisted resolver objects.
"""

from __future__ import annotations

import copy
import math
import time
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol, runtime_checkable

from aureon.governance.celtic_voice_bank import (
    CelticSeatedDruidResolver,
    read_canonical_celtic_voice_bank,
    seasonal_gate_for_date,
    validate_celtic_voice_bank_receipt,
)
from aureon.governance.cognition_gate import (
    CognitionGovernanceRequest,
    TrustedCouncilEvidence,
    TrustedCouncilReceiptSupplier,
    TrustedCrownReceiptSupplier,
)
from aureon.governance.crown_voice import (
    TrustedCrownVoiceResolver,
    issue_crown_voice_receipt,
)
from aureon.governance.druid_voice import (
    TrustedDruidSeatResolver,
    issue_trusted_druidic_council,
)
from aureon.swarm.auris_node_receipts import (
    DEFAULT_MAX_AGE_S,
    TrustedAurisNodeResolver,
    issue_auris_node_receipt,
)
from aureon.swarm.druidic_council import REQUIRED_SEATS

_FACTORY_TOKEN = object()


@runtime_checkable
class TrustedDruidSeatResolverFactory(Protocol):
    """Build one proposal-scoped resolver after all four nodes exist."""

    factory_id: str

    def build_druid_seat_resolver(
        self,
        request: CognitionGovernanceRequest,
        auris_node_receipts: Sequence[Mapping[str, Any]],
    ) -> TrustedDruidSeatResolver:
        """Return a resolver bound to the exact request and node receipts."""


@runtime_checkable
class TrustedAurisNodeResolverFactory(Protocol):
    """Build one measurement resolver for the request's exact provider moment."""

    factory_id: str

    def build_auris_node_resolver(
        self,
        request: CognitionGovernanceRequest,
    ) -> TrustedAurisNodeResolver:
        """Return four-seat evidence bound to this immutable request."""


def _nonblank(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}_required")
    return value.strip()


def _positive_finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"positive_finite_{label}_required")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"positive_finite_{label}_required")
    return result


def _trusted_ids(values: Collection[str], label: str) -> frozenset[str]:
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{label}_must_be_a_collection")
    canonical = [_nonblank(value, label).casefold() for value in values]
    if not canonical or len(canonical) != len(set(canonical)):
        raise ValueError(f"distinct_nonempty_{label}_required")
    return frozenset(canonical)


class CelticCouncilReceiptSupplier:
    """Issue the Council rune from four nodes and the canonical Celtic bank."""

    def __init__(
        self,
        *,
        _factory_token: object,
        supplier_id: str,
        auris_node_resolver: TrustedAurisNodeResolver | None,
        auris_resolver_factory: TrustedAurisNodeResolverFactory | None,
        druid_seat_resolver: TrustedDruidSeatResolver | None,
        druid_resolver_factory: TrustedDruidSeatResolverFactory | None,
        voice_bank_receipt: Mapping[str, Any],
        max_age_s: float,
        clock: Callable[[], float],
        civil_date_provider: Callable[[], date],
    ) -> None:
        if _factory_token is not _FACTORY_TOKEN:
            raise TypeError("use_bind_celtic_governance_voice_suppliers")
        self.supplier_id = _nonblank(supplier_id, "council_supplier_id")
        self._auris_node_resolver = auris_node_resolver
        self._auris_resolver_factory = auris_resolver_factory
        self._druid_seat_resolver = druid_seat_resolver
        self._druid_resolver_factory = druid_resolver_factory
        self._voice_bank_receipt = copy.deepcopy(dict(voice_bank_receipt))
        self._max_age_s = max_age_s
        self._clock = clock
        self._civil_date_provider = civil_date_provider

    @property
    def voice_bank_receipt_id(self) -> str:
        return str(self._voice_bank_receipt["receipt_id"])

    def supply_council_evidence(
        self,
        request: CognitionGovernanceRequest,
    ) -> TrustedCouncilEvidence:
        if not isinstance(request, CognitionGovernanceRequest):
            raise TypeError("cognition_governance_request_required")
        current = self._clock()
        if isinstance(current, bool) or not isinstance(current, (int, float)):
            raise ValueError("finite_governance_clock_required")
        now = float(current)
        if not math.isfinite(now):
            raise ValueError("finite_governance_clock_required")
        civil_day = self._civil_date_provider()
        if not isinstance(civil_day, date):
            raise TypeError("civil_date_required")
        seasonal_gate = seasonal_gate_for_date(civil_day)
        node_resolver = self._auris_node_resolver
        if self._auris_resolver_factory is not None:
            node_resolver = self._auris_resolver_factory.build_auris_node_resolver(
                request
            )
        if not isinstance(node_resolver, TrustedAurisNodeResolver):
            raise TypeError("trusted_auris_node_resolver_required")
        nodes = tuple(
            issue_auris_node_receipt(
                seat=seat,
                resolver=node_resolver,
                now=now,
                max_age_s=self._max_age_s,
            )
            for seat in REQUIRED_SEATS
        )
        if any(node.get("resolver_id") != self.supplier_id for node in nodes):
            raise ValueError("council_supplier_node_resolver_binding_required")
        delegate = self._druid_seat_resolver
        if self._druid_resolver_factory is not None:
            delegate = self._druid_resolver_factory.build_druid_seat_resolver(
                request,
                nodes,
            )
        if not isinstance(delegate, TrustedDruidSeatResolver):
            raise TypeError("trusted_druid_seat_resolver_required")
        seated_resolver = CelticSeatedDruidResolver(
            delegate=delegate,
            voice_bank_receipt=self._voice_bank_receipt,
            seasonal_gate=seasonal_gate,
        )
        council = issue_trusted_druidic_council(
            proposal_digest=request.proposal_digest,
            prompt_digest=request.prompt_digest,
            auris_node_receipts=nodes,
            resolver=seated_resolver,
            now=now,
            max_age_s=self._max_age_s,
        )
        return TrustedCouncilEvidence(
            council_receipt=council,
            auris_node_receipts=nodes,
        )


class CrownVoiceReceiptSupplier:
    """Issue the second rune from an independent trusted Crown resolver."""

    def __init__(
        self,
        *,
        _factory_token: object,
        supplier_id: str,
        resolver: TrustedCrownVoiceResolver,
        max_age_s: float,
        clock: Callable[[], float],
    ) -> None:
        if _factory_token is not _FACTORY_TOKEN:
            raise TypeError("use_bind_celtic_governance_voice_suppliers")
        self.supplier_id = _nonblank(supplier_id, "crown_supplier_id")
        self._resolver = resolver
        self._max_age_s = max_age_s
        self._clock = clock

    def supply_crown_receipt(
        self,
        request: CognitionGovernanceRequest,
    ) -> Mapping[str, Any]:
        if not isinstance(request, CognitionGovernanceRequest):
            raise TypeError("cognition_governance_request_required")
        current = self._clock()
        if isinstance(current, bool) or not isinstance(current, (int, float)):
            raise ValueError("finite_governance_clock_required")
        now = float(current)
        if not math.isfinite(now):
            raise ValueError("finite_governance_clock_required")
        receipt = issue_crown_voice_receipt(
            proposal_digest=request.proposal_digest,
            prompt_digest=request.prompt_digest,
            resolver=self._resolver,
            now=now,
            max_age_s=self._max_age_s,
        )
        if (
            receipt.get("data_status") == "live"
            and receipt.get("resolver_id") != self.supplier_id
        ):
            raise ValueError("crown_supplier_resolver_binding_required")
        return receipt


@dataclass(frozen=True, slots=True)
class GovernanceVoiceSuppliers:
    """The inseparable, independently allowlisted Council and Crown adapters."""

    council_receipt_supplier: CelticCouncilReceiptSupplier
    crown_receipt_supplier: CrownVoiceReceiptSupplier
    voice_bank_receipt_id: str

    def __post_init__(self) -> None:
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
        _nonblank(self.voice_bank_receipt_id, "voice_bank_receipt_id")


def bind_celtic_council_receipt_supplier(
    *,
    council_supplier_id: str,
    trusted_council_supplier_ids: Collection[str],
    auris_node_resolver: TrustedAurisNodeResolver | None = None,
    auris_resolver_factory: TrustedAurisNodeResolverFactory | None = None,
    druid_seat_resolver: TrustedDruidSeatResolver | None = None,
    druid_resolver_factory: TrustedDruidSeatResolverFactory | None = None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
    clock: Callable[[], float] = time.time,
    civil_date_provider: Callable[[], date] = date.today,
) -> CelticCouncilReceiptSupplier:
    """Bind the Council rune independently from the executive Crown rune."""

    has_static_auris = isinstance(auris_node_resolver, TrustedAurisNodeResolver)
    has_auris_factory = isinstance(
        auris_resolver_factory,
        TrustedAurisNodeResolverFactory,
    )
    if has_static_auris == has_auris_factory:
        raise TypeError("exactly_one_trusted_auris_resolver_or_factory_required")
    has_static_druid = isinstance(druid_seat_resolver, TrustedDruidSeatResolver)
    has_druid_factory = isinstance(
        druid_resolver_factory,
        TrustedDruidSeatResolverFactory,
    )
    if has_static_druid == has_druid_factory:
        raise TypeError("exactly_one_trusted_druid_resolver_or_factory_required")
    auris_authority = (
        auris_node_resolver if has_static_auris else auris_resolver_factory
    )
    druid_authority = (
        druid_seat_resolver if has_static_druid else druid_resolver_factory
    )
    if auris_authority is druid_authority:
        raise ValueError("independent_measurement_and_council_resolvers_required")
    council_id = _nonblank(council_supplier_id, "council_supplier_id")
    allowlist = _trusted_ids(
        trusted_council_supplier_ids,
        "trusted_council_supplier_id",
    )
    if council_id.casefold() not in allowlist:
        raise ValueError("council_supplier_not_allowlisted")
    authority_id = getattr(
        auris_authority,
        "resolver_id" if has_static_auris else "factory_id",
        None,
    )
    if _nonblank(authority_id, "auris_resolver_identity") != council_id:
        raise ValueError("council_supplier_node_resolver_binding_required")
    age = _positive_finite(max_age_s, "max_age_s")
    if not callable(clock):
        raise TypeError("clock_callable_required")
    if not callable(civil_date_provider):
        raise TypeError("civil_date_provider_callable_required")
    voice_bank = validate_celtic_voice_bank_receipt(
        read_canonical_celtic_voice_bank()
    )
    return CelticCouncilReceiptSupplier(
        _factory_token=_FACTORY_TOKEN,
        supplier_id=council_id,
        auris_node_resolver=auris_node_resolver,
        auris_resolver_factory=auris_resolver_factory,
        druid_seat_resolver=druid_seat_resolver,
        druid_resolver_factory=druid_resolver_factory,
        voice_bank_receipt=voice_bank,
        max_age_s=age,
        clock=clock,
        civil_date_provider=civil_date_provider,
    )


def bind_celtic_governance_voice_suppliers(
    *,
    council_supplier_id: str,
    crown_supplier_id: str,
    trusted_council_supplier_ids: Collection[str],
    trusted_crown_supplier_ids: Collection[str],
    auris_node_resolver: TrustedAurisNodeResolver | None = None,
    auris_resolver_factory: TrustedAurisNodeResolverFactory | None = None,
    crown_voice_resolver: TrustedCrownVoiceResolver,
    druid_seat_resolver: TrustedDruidSeatResolver | None = None,
    druid_resolver_factory: TrustedDruidSeatResolverFactory | None = None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
    clock: Callable[[], float] = time.time,
    civil_date_provider: Callable[[], date] = date.today,
) -> GovernanceVoiceSuppliers:
    """Bind two voices without resolving evidence or evaluating a proposal."""

    has_static_auris = isinstance(auris_node_resolver, TrustedAurisNodeResolver)
    has_auris_factory = isinstance(
        auris_resolver_factory,
        TrustedAurisNodeResolverFactory,
    )
    if has_static_auris == has_auris_factory:
        raise TypeError("exactly_one_trusted_auris_resolver_or_factory_required")
    if not isinstance(crown_voice_resolver, TrustedCrownVoiceResolver):
        raise TypeError("trusted_crown_voice_resolver_required")
    has_static_druid = isinstance(druid_seat_resolver, TrustedDruidSeatResolver)
    has_druid_factory = isinstance(
        druid_resolver_factory,
        TrustedDruidSeatResolverFactory,
    )
    if has_static_druid == has_druid_factory:
        raise TypeError("exactly_one_trusted_druid_resolver_or_factory_required")
    druid_authority = (
        druid_seat_resolver if has_static_druid else druid_resolver_factory
    )
    auris_authority = (
        auris_node_resolver if has_static_auris else auris_resolver_factory
    )
    resolver_ids = {
        id(auris_authority),
        id(druid_authority),
        id(crown_voice_resolver),
    }
    if len(resolver_ids) != 3:
        raise ValueError(
            "independent_measurement_council_and_crown_resolvers_required"
        )
    council_id = _nonblank(council_supplier_id, "council_supplier_id")
    crown_id = _nonblank(crown_supplier_id, "crown_supplier_id")
    council_allowlist = _trusted_ids(
        trusted_council_supplier_ids,
        "trusted_council_supplier_id",
    )
    crown_allowlist = _trusted_ids(
        trusted_crown_supplier_ids,
        "trusted_crown_supplier_id",
    )
    if council_allowlist.intersection(crown_allowlist):
        raise ValueError("supplier_allowlists_must_be_disjoint")
    if council_id.casefold() not in council_allowlist:
        raise ValueError("council_supplier_not_allowlisted")
    if crown_id.casefold() not in crown_allowlist:
        raise ValueError("crown_supplier_not_allowlisted")
    if council_id.casefold() == crown_id.casefold():
        raise ValueError("independent_council_and_crown_suppliers_required")
    age = _positive_finite(max_age_s, "max_age_s")
    if not callable(clock):
        raise TypeError("clock_callable_required")
    if not callable(civil_date_provider):
        raise TypeError("civil_date_provider_callable_required")
    voice_bank = validate_celtic_voice_bank_receipt(
        read_canonical_celtic_voice_bank()
    )
    council = CelticCouncilReceiptSupplier(
        _factory_token=_FACTORY_TOKEN,
        supplier_id=council_id,
        auris_node_resolver=auris_node_resolver,
        auris_resolver_factory=auris_resolver_factory,
        druid_seat_resolver=druid_seat_resolver,
        druid_resolver_factory=druid_resolver_factory,
        voice_bank_receipt=voice_bank,
        max_age_s=age,
        clock=clock,
        civil_date_provider=civil_date_provider,
    )
    crown = CrownVoiceReceiptSupplier(
        _factory_token=_FACTORY_TOKEN,
        supplier_id=crown_id,
        resolver=crown_voice_resolver,
        max_age_s=age,
        clock=clock,
    )
    return GovernanceVoiceSuppliers(
        council_receipt_supplier=council,
        crown_receipt_supplier=crown,
        voice_bank_receipt_id=council.voice_bank_receipt_id,
    )


__all__ = [
    "CelticCouncilReceiptSupplier",
    "CrownVoiceReceiptSupplier",
    "GovernanceVoiceSuppliers",
    "TrustedAurisNodeResolverFactory",
    "TrustedDruidSeatResolverFactory",
    "bind_celtic_council_receipt_supplier",
    "bind_celtic_governance_voice_suppliers",
]
