"""Trusted composition root for Aureon's Ollama Cloud coding organism.

The cloud model is an inference engine, never its own truth authority.  This
module assembles the already-strict 10-9-1, receipt-backed truth, HNC/Auris,
and Hive/Mycelia components only when three disjoint identity allowlists are
provided by the process-owned composition root.

No object built here grants tools, file writes, deployment, or economic
authority.  Missing or malformed authority evidence is handled by the inner
truth gate as HOLD before Auris or propagation.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aureon.autonomous.aureon_agent_company_brain_fabric import (
    provision_agent_company_brain_fabric,
)
from aureon.autonomous.aureon_internal_coding_workforce import (
    BrainResolver,
    InternalCodingWorkforce,
    WorkReceipt,
)
from aureon.autonomous.aureon_ten_nine_one_thought_path import (
    CommitmentOnlyHiveMyceliaPropagator,
    LocalHncAurisEvidenceResolver,
    TenNineOneEvidenceResolver,
    TenNineOnePropagator,
    ThoughtBusHiveMyceliaPropagator,
)
from aureon.autonomous.aureon_truth_gated_ten_nine_one import (
    ReceiptBackedTenNineOneTruthGate,
    TruthGatedTenNineOneThoughtPath,
)
from aureon.governance.material_truth_gate import (
    MaterialAwareTenNineOneTruthGate,
)
from aureon.governance.trusted_truth_evidence import (
    TrustedClaimEvidenceAuthority,
    TrustedDiagnosticSignalAuthority,
)
from aureon.swarm.auris_node_receipts import DEFAULT_MAX_AGE_S


@dataclass(frozen=True, slots=True)
class TruthAuthorityBundle:
    """Process-owned identities allowed to ground and diagnose cloud answers."""

    claim_authority: TrustedClaimEvidenceAuthority
    diagnostic_authority: TrustedDiagnosticSignalAuthority
    allowed_claim_authority_ids: frozenset[str]
    allowed_evidence_issuer_ids: frozenset[str]
    allowed_diagnostic_authority_ids: frozenset[str]

    def __post_init__(self) -> None:
        if not isinstance(self.claim_authority, TrustedClaimEvidenceAuthority):
            raise ValueError("trusted_claim_evidence_authority_required")
        if not isinstance(self.diagnostic_authority, TrustedDiagnosticSignalAuthority):
            raise ValueError("trusted_diagnostic_signal_authority_required")
        if self.claim_authority is self.diagnostic_authority:
            raise ValueError("independent_truth_authorities_required")
        sets = (
            self.allowed_claim_authority_ids,
            self.allowed_evidence_issuer_ids,
            self.allowed_diagnostic_authority_ids,
        )
        if any(type(items) is not frozenset or not items for items in sets):
            raise ValueError("nonempty_frozen_truth_authority_allowlists_required")
        normalized = tuple({str(item).casefold() for item in items} for items in sets)
        if any(
            normalized[left] & normalized[right]
            for left, right in ((0, 1), (0, 2), (1, 2))
        ):
            raise ValueError("disjoint_truth_authority_identities_required")
        if self.claim_authority.authority_id not in self.allowed_claim_authority_ids:
            raise ValueError("allowlisted_claim_authority_required")
        if self.diagnostic_authority.authority_id not in self.allowed_diagnostic_authority_ids:
            raise ValueError("allowlisted_diagnostic_authority_required")


def build_local_confidential_self_coder_thought_path(
    authorities: TruthAuthorityBundle | None = None,
    *,
    evidence_resolver: TenNineOneEvidenceResolver | None = None,
    bus: Any = None,
    root: Path | None = None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
    now: Callable[[], float] = time.time,
) -> TruthGatedTenNineOneThoughtPath:
    """Build the local-only, commitment-only path for confidential self-coding.

    The factory never constructs or deserializes truth authorities.  A trusted
    process-owned composition root must supply the already-validated bundle.
    This prevents local prompt material, environment strings, or model output
    from becoming their own truth anchor.
    """

    if authorities is None:
        raise ValueError("authenticated_self_coder_truth_authority_bundle_required")
    if not isinstance(authorities, TruthAuthorityBundle):
        raise ValueError("authenticated_self_coder_truth_authority_bundle_required")
    resolver = evidence_resolver or LocalHncAurisEvidenceResolver(
        bus=bus,
        root=root,
        require_active_pair=True,
        pair_max_age_s=max_age_s,
        clock=now,
    )
    release = CommitmentOnlyHiveMyceliaPropagator(bus=bus)
    gate = ReceiptBackedTenNineOneTruthGate(
        claim_authority=authorities.claim_authority,
        diagnostic_authority=authorities.diagnostic_authority,
        allowed_claim_authority_ids=authorities.allowed_claim_authority_ids,
        allowed_evidence_issuer_ids=authorities.allowed_evidence_issuer_ids,
        allowed_diagnostic_authority_ids=authorities.allowed_diagnostic_authority_ids,
        max_age_s=max_age_s,
        now=now,
    )
    path = TruthGatedTenNineOneThoughtPath(
        resolver=resolver,
        propagator=release,
        truth_gate=gate,
        max_age_s=max_age_s,
        now=now,
    )
    preflight = path.self_coder_confidential_preflight()
    if preflight.get("ready") is not True:
        raise ValueError("confidential_self_coder_thought_path_unavailable")
    return path


def build_truth_gated_cloud_thought_path(
    authorities: TruthAuthorityBundle,
    *,
    evidence_resolver: TenNineOneEvidenceResolver | None = None,
    propagator: TenNineOnePropagator | None = None,
    bus: Any = None,
    root: Path | None = None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
    now: Callable[[], float] = time.time,
) -> TruthGatedTenNineOneThoughtPath:
    """Build the only path permitted to release one cloud answer to the hive."""

    if not isinstance(authorities, TruthAuthorityBundle):
        raise ValueError("truth_authority_bundle_required")
    resolver = evidence_resolver or LocalHncAurisEvidenceResolver(bus=bus, root=root)
    release = propagator or ThoughtBusHiveMyceliaPropagator(bus=bus)
    gate = ReceiptBackedTenNineOneTruthGate(
        claim_authority=authorities.claim_authority,
        diagnostic_authority=authorities.diagnostic_authority,
        allowed_claim_authority_ids=authorities.allowed_claim_authority_ids,
        allowed_evidence_issuer_ids=authorities.allowed_evidence_issuer_ids,
        allowed_diagnostic_authority_ids=authorities.allowed_diagnostic_authority_ids,
        max_age_s=max_age_s,
        now=now,
    )
    return TruthGatedTenNineOneThoughtPath(
        resolver=resolver,
        propagator=release,
        truth_gate=gate,
        max_age_s=max_age_s,
        now=now,
    )


def provision_truth_gated_cloud_agent_company(
    authorities: TruthAuthorityBundle,
    resolver: BrainResolver | None = None,
    *,
    evidence_resolver: TenNineOneEvidenceResolver | None = None,
    propagator: TenNineOnePropagator | None = None,
    bus: Any = None,
    root: Path | None = None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
    now: Callable[[], float] = time.time,
    prior_work_receipts: Sequence[WorkReceipt] = (),
    receipt_sink: Callable[[WorkReceipt], None] | None = None,
) -> InternalCodingWorkforce:
    """Provision all 41 seats and 41 processes on the exact trusted path."""

    thought_path = build_truth_gated_cloud_thought_path(
        authorities,
        evidence_resolver=evidence_resolver,
        propagator=propagator,
        bus=bus,
        root=root,
        max_age_s=max_age_s,
        now=now,
    )
    return provision_agent_company_brain_fabric(
        resolver,
        prior_work_receipts=prior_work_receipts,
        receipt_sink=receipt_sink,
        thought_path=thought_path,
    )


def build_material_truth_gated_cloud_thought_path(
    *,
    evidence_resolver: TenNineOneEvidenceResolver | None = None,
    propagator: TenNineOnePropagator | None = None,
    bus: Any = None,
    root: Path | None = None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
    now: Callable[[], float] = time.time,
) -> TruthGatedTenNineOneThoughtPath:
    """Build the exact-menu local-authority path for bounded decisions."""

    resolver = evidence_resolver or LocalHncAurisEvidenceResolver(bus=bus, root=root)
    release = propagator or ThoughtBusHiveMyceliaPropagator(bus=bus)
    return TruthGatedTenNineOneThoughtPath(
        resolver=resolver,
        propagator=release,
        truth_gate=MaterialAwareTenNineOneTruthGate(
            max_age_s=max_age_s,
            now=now,
        ),
        max_age_s=max_age_s,
        now=now,
    )


def provision_material_truth_gated_cloud_agent_company(
    resolver: BrainResolver | None = None,
    *,
    evidence_resolver: TenNineOneEvidenceResolver | None = None,
    propagator: TenNineOnePropagator | None = None,
    bus: Any = None,
    root: Path | None = None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
    now: Callable[[], float] = time.time,
    prior_work_receipts: Sequence[WorkReceipt] = (),
    receipt_sink: Callable[[WorkReceipt], None] | None = None,
) -> InternalCodingWorkforce:
    """Provision the cloud workforce on exact-menu local truth authority."""

    thought_path = build_material_truth_gated_cloud_thought_path(
        evidence_resolver=evidence_resolver,
        propagator=propagator,
        bus=bus,
        root=root,
        max_age_s=max_age_s,
        now=now,
    )
    return provision_agent_company_brain_fabric(
        resolver,
        prior_work_receipts=prior_work_receipts,
        receipt_sink=receipt_sink,
        thought_path=thought_path,
    )


__all__ = [
    "TruthAuthorityBundle",
    "build_local_confidential_self_coder_thought_path",
    "build_material_truth_gated_cloud_thought_path",
    "build_truth_gated_cloud_thought_path",
    "provision_material_truth_gated_cloud_agent_company",
    "provision_truth_gated_cloud_agent_company",
]
