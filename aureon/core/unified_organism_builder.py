"""Bind the complete cloud-brain organism from already constructed organs.

This is a composition operation only.  It does not call a model, provider, or
exchange and cannot turn a HOLD calibration into readiness.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Collection, Mapping
from datetime import date
from pathlib import Path
from typing import Any

from aureon.autonomous.aureon_agent_company_brain_fabric import (
    company_brain_fabric_report,
    provision_agent_company_brain_fabric,
)
from aureon.autonomous.aureon_internal_coding_workforce import (
    BrainResolver,
    CodingThoughtPath,
    InternalCodingWorkforce,
)
from aureon.core.organism_composition import (
    CALIBRATION_PATH,
    REQUIRED_SUBSYSTEMS,
    GovernanceBindings,
    OrganismComposition,
    bind_canonical_organism_composition,
    configure_canonical_organism_composition,
    load_latest_calibration_status,
)
from aureon.governance.celtic_voice_bank import read_canonical_celtic_voice_bank
from aureon.governance.economic_mutation_readiness import (
    validate_economic_mutation_readiness_receipt,
)
from aureon.governance.hnc_auris_acquisition import (
    ProviderPairLoader,
    bind_hnc_auris_governance_acquisition_supplier,
)
from aureon.governance.legacy_economic_unity import LegacyEconomicCapability
from aureon.governance.live_workforce_calibration import (
    load_latest_active_provider_pair,
    validate_workforce_auris_calibration_report,
)
from aureon.governance.queen_crown_supplier import (
    QueenConscienceCrownSupplier,
    QueenConscienceLike,
    load_local_request_provider_evidence,
)
from aureon.governance.runtime_voice_suppliers import (
    bind_celtic_council_receipt_supplier,
)
from aureon.governance.workforce_auris_resolver_factory import (
    bind_calibrated_workforce_auris_resolver_factory,
)
from aureon.governance.workforce_druid_resolver import (
    DEFAULT_WORKFORCE_DRUID_ROLES,
    bind_workforce_druid_resolver_factory,
)
from aureon.queen.queen_mind import (
    bind_queen_mind,
    configure_canonical_queen_mind,
    discover_queen_faculty_manifest,
)
from aureon.queen.queen_process_roof import (
    bind_queen_process_roof,
    configure_canonical_queen_process_roof,
)
from aureon.trading.unified_exchange_composition import (
    UnifiedExchangeUnityComposition,
    build_unified_exchange_unity_composition,
)


def _read_complete_calibration(path: Path) -> Mapping[str, Any]:
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(payload, Mapping)
        or payload.get("schema") != "aureon.live-druidic-calibration-operation.v1"
        or payload.get("status") != "complete"
    ):
        raise ValueError("complete_druidic_calibration_operation_required")
    return payload


def build_canonical_cloud_organism(
    *,
    brain_resolver: BrainResolver,
    thought_path: CodingThoughtPath,
    conscience: QueenConscienceLike,
    capabilities: Collection[LegacyEconomicCapability],
    present_subsystems: Mapping[str, str],
    economic_readiness_receipt: Mapping[str, Any],
    calibration_path: Path = CALIBRATION_PATH,
    pair_loader: ProviderPairLoader = load_latest_active_provider_pair,
    client_factory: Callable[..., Any] | None = None,
    bus: Any = None,
    max_age_s: float = 30.0,
    clock: Callable[[], float] = time.time,
    civil_date_provider: Callable[[], Any] = date.today,
) -> tuple[OrganismComposition, InternalCodingWorkforce, UnifiedExchangeUnityComposition]:
    """Construct and register the one process-owned organism composition."""

    if not callable(clock):
        raise TypeError("organism_clock_callable_required")
    current = float(clock())
    if not math.isfinite(current):
        raise ValueError("finite_organism_clock_required")
    if set(present_subsystems) != set(REQUIRED_SUBSYSTEMS):
        raise ValueError("complete_canonical_subsystem_map_required")
    capability_set = tuple(capabilities)
    if not capability_set:
        raise ValueError("legacy_capabilities_must_be_nonempty")
    economic_readiness = validate_economic_mutation_readiness_receipt(
        economic_readiness_receipt,
        now=current,
        max_age_s=max_age_s,
    )
    if economic_readiness["status"] != "ready":
        raise ValueError("zero_aligned_economic_mutation_blockers_required")
    calibration_path = Path(calibration_path)
    calibration_status = load_latest_calibration_status(
        complete_path=calibration_path,
        hold_path=calibration_path.with_name(
            f".{calibration_path.name}.no-hold-candidate"
        ),
        now=current,
        max_age_s=max_age_s,
    )
    if calibration_status.get("status") != "complete":
        raise ValueError("valid_fresh_complete_druidic_calibration_required")
    operation = _read_complete_calibration(calibration_path)
    calibration = validate_workforce_auris_calibration_report(
        operation.get("calibration_receipt", {}),
        now=current,
        max_age_s=max_age_s,
    )
    workforce = provision_agent_company_brain_fabric(
        brain_resolver,
        thought_path=thought_path,
    )
    report = company_brain_fabric_report(workforce)
    if report.get("ready") is not True:
        raise ValueError("complete_truth_gated_agent_company_brain_fabric_required")
    council_id = str(calibration["resolver_id"])
    druid_factory = bind_workforce_druid_resolver_factory(
        factory_id="aureon:canonical-workforce-druid-factory",
        resolver_id="aureon:canonical-workforce-druid-resolver",
        issuer_id_prefix="aureon:canonical-workforce-druid-issuer",
        trusted_factory_ids={"aureon:canonical-workforce-druid-factory"},
        workforce=workforce,
        seat_roles=DEFAULT_WORKFORCE_DRUID_ROLES,
        max_age_s=max_age_s,
        clock=clock,
    )
    auris_factory = bind_calibrated_workforce_auris_resolver_factory(
        factory_id=council_id,
        trusted_resolver_ids={council_id},
        calibration_report=calibration,
        pair_loader=lambda request: load_local_request_provider_evidence(
            request,
            now=float(clock()),
            max_age_s=max_age_s,
        ),
        max_age_s=max_age_s,
        clock=clock,
    )
    council = bind_celtic_council_receipt_supplier(
        council_supplier_id=council_id,
        trusted_council_supplier_ids={council_id},
        auris_resolver_factory=auris_factory,
        druid_resolver_factory=druid_factory,
        max_age_s=max_age_s,
        clock=clock,
        civil_date_provider=civil_date_provider,
    )
    crown = QueenConscienceCrownSupplier(
        conscience=conscience,
        max_age_s=max_age_s,
        clock=clock,
    )
    acquisition = bind_hnc_auris_governance_acquisition_supplier(
        supplier_id="aureon:canonical-hnc-auris-acquisition",
        trusted_supplier_ids={"aureon:canonical-hnc-auris-acquisition"},
        pair_loader=pair_loader,
        max_age_s=max_age_s,
        clock=clock,
    )
    governance = GovernanceBindings(
        council_receipt_supplier=council,
        crown_receipt_supplier=crown,
        acquisition_supplier=acquisition,
        voice_bank_receipt=read_canonical_celtic_voice_bank(),
    )
    exchange = build_unified_exchange_unity_composition(
        council_receipt_supplier=council,
        crown_receipt_supplier=crown,
        trusted_council_supplier_ids=frozenset({council.supplier_id}),
        trusted_crown_supplier_ids=frozenset({crown.supplier_id}),
        capabilities=capability_set,
        client_factory=client_factory,
        bus=bus,
        pair_max_age_s=max_age_s,
        clock=clock,
    )
    queen_manifest = discover_queen_faculty_manifest()
    composition = configure_canonical_organism_composition(
        bind_canonical_organism_composition(
            present_subsystems=present_subsystems,
            governance=governance,
            brain_fabric_report=report,
            calibration_status=calibration_status,
            economic_readiness=economic_readiness,
            queen_mind_report=queen_manifest.report(),
        )
    )
    configure_canonical_queen_mind(
        bind_queen_mind(
            composition=composition,
            workforce=workforce,
            conscience=conscience,
            manifest=queen_manifest,
            bus=bus,
            clock=clock,
        )
    )
    configure_canonical_queen_process_roof(
        bind_queen_process_roof(composition=composition)
    )
    return composition, workforce, exchange


__all__ = ["build_canonical_cloud_organism"]
