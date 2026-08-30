"""Canonical process-owned composition root for the Aureon organism.

The repository contains many capable organs and several historical startup
scripts.  This module is the one small ownership contract that tells a process
which concrete objects form *its* organism.  It does not construct provider
clients, call a model, issue an economic permit, or turn repository context
into authority.

An incomplete composition is valid but reports ``HOLD``.  That lets the live
daemon expose exactly which organs are present without pretending that bus
membership is the same as a complete Council/Crown decision path.
"""

from __future__ import annotations

import copy
import json
import math
import re
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from aureon.governance.celtic_voice_bank import (
    read_canonical_celtic_voice_bank,
    validate_celtic_voice_bank_receipt,
)
from aureon.governance.cognition_gate import (
    TrustedCouncilReceiptSupplier,
    TrustedCrownReceiptSupplier,
)
from aureon.governance.economic_mutation_readiness import (
    READINESS_SCHEMA,
    validate_economic_mutation_readiness_receipt,
)

SCHEMA_VERSION = "aureon.organism-composition.v1"
QUEEN_MIND_SCHEMA = "aureon.queen-mind.v1"
QUEEN_MIND_REQUIRED_ROLES = frozenset(
    {"knowledge", "metacognition", "miner", "quantum"}
)
CALIBRATION_PATH = Path(__file__).resolve().parents[2] / "state" / "druidic_live_calibration_latest.json"
CALIBRATION_HOLD_PATH = (
    Path(__file__).resolve().parents[2] / "state" / "druidic_live_calibration_hold_latest.json"
)
REQUIRED_SUBSYSTEMS = frozenset(
    {
        "thought_bus",
        "mycelium",
        "connectome",
        "soul",
        "hnc",
        "auris",
        "celtic_voice_bank",
        "council",
        "crown",
        "brain_switchboard",
        "queen_mind",
    }
)
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_FALSE_FLAGS = {
    "action_eligible": False,
    "accounting_eligible": False,
    "learning_eligible": False,
    "actionable": False,
    "operational_eligible": False,
    "provider_eligible": False,
    "economic_mutation": False,
}


def _nonblank(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}_required")
    return value.strip()


def _canonical_copy(value: Any) -> Any:
    return json.loads(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    )


def _validate_queen_mind_report(report: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(report, Mapping):
        raise TypeError("queen_mind_report_mapping_required")
    normalized = _canonical_copy(dict(report))
    status = normalized.get("status")
    if status in {"missing", "hold"}:
        return normalized
    if (
        normalized.get("schema") != QUEEN_MIND_SCHEMA
        or status != "seated"
        or not isinstance(normalized.get("manifest_id"), str)
        or not normalized["manifest_id"].startswith("queen-faculty-manifest:")
        or isinstance(normalized.get("faculty_count"), bool)
        or not isinstance(normalized.get("faculty_count"), int)
        or normalized["faculty_count"] <= 0
        or normalized.get("required_roles")
        != sorted(QUEEN_MIND_REQUIRED_ROLES)
        or normalized.get("action_eligible") is not False
        or normalized.get("economic_mutation") is not False
    ):
        raise ValueError("complete_evidence_only_queen_mind_report_required")
    roles = normalized.get("roles")
    if (
        not isinstance(roles, Mapping)
        or any(
            isinstance(roles.get(role), bool)
            or not isinstance(roles.get(role), int)
            or roles[role] <= 0
            for role in QUEEN_MIND_REQUIRED_ROLES
        )
    ):
        raise ValueError("complete_queen_mind_cognitive_roles_required")
    return normalized


@runtime_checkable
class GovernanceAcquisitionSupplier(Protocol):
    """Process-injected source for one fresh exact HNC/Auris provider moment."""

    supplier_id: str

    def load_governance_acquisition(self) -> Mapping[str, Any]: ...


class CallableGovernanceAcquisitionSupplier:
    """Bind a trusted loader without accepting request-selected callables."""

    def __init__(self, *, supplier_id: str, loader: Callable[[], Mapping[str, Any]]) -> None:
        self.supplier_id = _nonblank(supplier_id, "acquisition_supplier_id")
        if not callable(loader):
            raise TypeError("governance_acquisition_loader_required")
        self._loader = loader

    def load_governance_acquisition(self) -> Mapping[str, Any]:
        raw = self._loader()
        if not isinstance(raw, Mapping):
            raise TypeError("governance_acquisition_mapping_required")
        result = _canonical_copy(dict(raw))
        receipt_ids = result.get("provider_receipt_ids")
        digest = result.get("provider_moment_digest")
        source_timestamp = result.get("provider_source_timestamp")
        if (
            not isinstance(receipt_ids, list)
            or not receipt_ids
            or any(not isinstance(item, str) or not item.strip() for item in receipt_ids)
            or receipt_ids != sorted(set(receipt_ids))
        ):
            raise ValueError("sorted_unique_provider_receipt_ids_required")
        if not isinstance(digest, str) or _DIGEST_RE.fullmatch(digest) is None:
            raise ValueError("provider_moment_digest_required")
        if not isinstance(source_timestamp, str) or not source_timestamp.strip():
            raise ValueError("provider_source_timestamp_required")
        try:
            numeric_timestamp = float(source_timestamp)
        except ValueError as exc:
            raise ValueError("finite_provider_source_timestamp_required") from exc
        if not math.isfinite(numeric_timestamp):
            raise ValueError("finite_provider_source_timestamp_required")
        return result


@dataclass(frozen=True, slots=True)
class SubsystemRegistration:
    subsystem_id: str
    role: str
    truth_status: str
    effect_class: str = "evidence_only"

    def __post_init__(self) -> None:
        _nonblank(self.subsystem_id, "subsystem_id")
        _nonblank(self.role, "subsystem_role")
        if self.truth_status not in {"live", "real_observed", "real_derived", "no_data"}:
            raise ValueError("recognized_subsystem_truth_status_required")
        if self.effect_class not in {"evidence_only", "read_only", "governance", "action_boundary"}:
            raise ValueError("recognized_subsystem_effect_class_required")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GovernanceBindings:
    council_receipt_supplier: TrustedCouncilReceiptSupplier
    crown_receipt_supplier: TrustedCrownReceiptSupplier
    acquisition_supplier: GovernanceAcquisitionSupplier
    voice_bank_receipt: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(self.council_receipt_supplier, TrustedCouncilReceiptSupplier):
            raise TypeError("trusted_council_receipt_supplier_required")
        if not isinstance(self.crown_receipt_supplier, TrustedCrownReceiptSupplier):
            raise TypeError("trusted_crown_receipt_supplier_required")
        if self.council_receipt_supplier is self.crown_receipt_supplier:
            raise ValueError("independent_council_and_crown_suppliers_required")
        if not isinstance(self.acquisition_supplier, GovernanceAcquisitionSupplier):
            raise TypeError("trusted_governance_acquisition_supplier_required")
        council_id = _nonblank(self.council_receipt_supplier.supplier_id, "council_supplier_id")
        crown_id = _nonblank(self.crown_receipt_supplier.supplier_id, "crown_supplier_id")
        acquisition_id = _nonblank(self.acquisition_supplier.supplier_id, "acquisition_supplier_id")
        if len({council_id.casefold(), crown_id.casefold(), acquisition_id.casefold()}) != 3:
            raise ValueError("independent_governance_supplier_identities_required")
        validate_celtic_voice_bank_receipt(self.voice_bank_receipt)

    def cognition_kwargs(self) -> dict[str, Any]:
        return {
            "council_receipt_supplier": self.council_receipt_supplier,
            "crown_receipt_supplier": self.crown_receipt_supplier,
            "governance_acquisition_supplier": self.acquisition_supplier.load_governance_acquisition,
            "governance_enabled": True,
        }


@dataclass(frozen=True, slots=True)
class OrganismComposition:
    """One process's complete or honestly incomplete organism ownership map."""

    registrations: tuple[SubsystemRegistration, ...]
    governance: GovernanceBindings | None
    brain_fabric_report: Mapping[str, Any]
    calibration_status: Mapping[str, Any]
    economic_readiness: Mapping[str, Any]
    voice_bank_receipt: Mapping[str, Any]
    queen_mind_report: Mapping[str, Any]
    schema: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema != SCHEMA_VERSION:
            raise ValueError("organism_composition_schema_mismatch")
        if not self.registrations:
            raise ValueError("organism_subsystem_registrations_required")
        identities = [item.subsystem_id for item in self.registrations]
        if len(identities) != len(set(identities)):
            raise ValueError("unique_organism_subsystem_identities_required")
        economic_status = self.economic_readiness.get("status")
        if self.economic_readiness.get("schema") == READINESS_SCHEMA:
            validate_economic_mutation_readiness_receipt(self.economic_readiness)
        elif economic_status not in {"missing", "hold"}:
            raise ValueError("valid_economic_mutation_readiness_receipt_required")
        canonical_bank = validate_celtic_voice_bank_receipt(self.voice_bank_receipt)
        _validate_queen_mind_report(self.queen_mind_report)
        if self.governance is not None:
            governed_bank = validate_celtic_voice_bank_receipt(
                self.governance.voice_bank_receipt
            )
            if governed_bank["receipt_id"] != canonical_bank["receipt_id"]:
                raise ValueError("one_canonical_celtic_voice_bank_required")

    def cognition_kwargs(self) -> dict[str, Any]:
        if self.governance is None:
            return {"governance_enabled": True}
        return self.governance.cognition_kwargs()

    def status(self) -> dict[str, Any]:
        present = {item.subsystem_id for item in self.registrations}
        missing = sorted(REQUIRED_SUBSYSTEMS - present)
        brain_ready = bool(
            self.brain_fabric_report.get("ready") is True
            and self.brain_fabric_report.get("status") == "brain_fabric_ready"
            and self.brain_fabric_report.get("truth_gate_enforced") is True
            and self.brain_fabric_report.get("provider_mode") == "ollama_cloud_primary"
        )
        calibration_ready = self.calibration_status.get("status") == "complete"
        economic_ready = bool(
            self.economic_readiness.get("schema") == READINESS_SCHEMA
            and self.economic_readiness.get("status") == "ready"
            and self.economic_readiness.get("inventory_aligned") is True
            and self.economic_readiness.get("certified_no_bypass") is True
            and self.economic_readiness.get("blocker_count") == 0
        )
        governance_ready = self.governance is not None
        queen_mind = _validate_queen_mind_report(self.queen_mind_report)
        queen_mind_ready = queen_mind.get("status") == "seated"
        ready = (
            not missing
            and brain_ready
            and calibration_ready
            and economic_ready
            and governance_ready
            and queen_mind_ready
        )
        bank = validate_celtic_voice_bank_receipt(self.voice_bank_receipt)
        return {
            "schema": self.schema,
            "status": "ready" if ready else "hold",
            "reason": None if ready else "complete_canonical_organism_composition_required",
            "registered_subsystem_count": len(self.registrations),
            "registered_subsystem_ids": sorted(present),
            "missing_subsystem_ids": missing,
            "brain_fabric_ready": brain_ready,
            "calibration_status": self.calibration_status.get("status", "missing"),
            "calibration_reason": self.calibration_status.get("reason"),
            "economic_readiness_status": self.economic_readiness.get(
                "status",
                "missing",
            ),
            "economic_readiness_reason": self.economic_readiness.get("reason"),
            "economic_inventory_aligned": self.economic_readiness.get(
                "inventory_aligned",
                False,
            ),
            "economic_no_bypass_certified": self.economic_readiness.get(
                "certified_no_bypass",
                False,
            ),
            "economic_blocker_count": self.economic_readiness.get("blocker_count"),
            "governance_ready": governance_ready,
            "queen_mind_ready": queen_mind_ready,
            "queen_mind_manifest_id": queen_mind.get("manifest_id"),
            "queen_mind_faculty_count": queen_mind.get("faculty_count", 0),
            "queen_mind_required_roles": queen_mind.get(
                "required_roles",
                sorted(QUEEN_MIND_REQUIRED_ROLES),
            ),
            "voice_bank_receipt_id": bank["receipt_id"],
            "voice_bank_dataset_sha256": bank["dataset_sha256"],
            "truth_status": "real_observed" if ready else "no_data",
            "generated_values": False,
            **_FALSE_FLAGS,
        }


def load_latest_calibration_status(
    *,
    complete_path: Path = CALIBRATION_PATH,
    hold_path: Path = CALIBRATION_HOLD_PATH,
    now: float | None = None,
    max_age_s: float = 30.0,
) -> dict[str, Any]:
    """Read and validate the newest local calibration status; never manufacture one."""

    candidates = [path for path in (complete_path, hold_path) if path.exists()]
    if not candidates:
        return {"status": "missing", "reason": "druidic_calibration_receipt_required"}
    path = max(candidates, key=lambda item: item.stat().st_mtime_ns)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "hold", "reason": "valid_druidic_calibration_receipt_required"}
    if not isinstance(payload, Mapping):
        return {"status": "hold", "reason": "valid_druidic_calibration_receipt_required"}
    status = str(payload.get("status") or "hold").lower()
    if status not in {"complete", "hold"}:
        status = "hold"
    if status == "complete":
        try:
            from aureon.governance.live_workforce_calibration import (
                validate_workforce_auris_calibration_report,
            )
            from aureon.swarm.auris_node_receipts import validate_auris_node_receipt
            from aureon.swarm.druidic_council import (
                ACTIVE_THRESHOLD,
                REQUIRED_SEATS,
            )

            current = time.time() if now is None else float(now)
            if (
                payload.get("schema")
                != "aureon.live-druidic-calibration-operation.v1"
                or payload.get("provider_mode") != "ollama_cloud_primary"
                or payload.get("action_eligible") is not False
                or payload.get("economic_mutation") is not False
                or payload.get("exchange_call_count") != 0
                or payload.get("order_call_count") != 0
            ):
                raise ValueError("exact_non_authoritative_calibration_operation_required")
            calibration = validate_workforce_auris_calibration_report(
                payload.get("calibration_receipt", {}),
                now=current,
                max_age_s=max_age_s,
            )
            raw_nodes = payload.get("auris_nodes")
            if not isinstance(raw_nodes, list) or len(raw_nodes) != len(REQUIRED_SEATS):
                raise ValueError("exact_four_calibration_nodes_required")
            nodes = [
                validate_auris_node_receipt(
                    node,
                    now=current,
                    max_age_s=max_age_s,
                )
                for node in raw_nodes
            ]
            final_round = calibration["rounds"][-1]
            if (
                {node["seat"] for node in nodes} != set(REQUIRED_SEATS)
                or any(
                    node["resolver_id"] != calibration["resolver_id"]
                    or node["hnc_receipt_id"] != final_round["hnc_receipt_id"]
                    or node["auris_receipt_id"] != final_round["auris_receipt_id"]
                    or node["provider_moment_digest"]
                    != final_round["provider_moment_digest"]
                    for node in nodes
                )
            ):
                raise ValueError("calibration_node_lineage_mismatch")
            driver_count = sum(
                float(node["gamma"]) >= ACTIVE_THRESHOLD for node in nodes
            )
            if driver_count < 2 or payload.get("node_driver_count") != driver_count:
                raise ValueError("calibration_council_driver_quorum_required")
        except (KeyError, TypeError, ValueError):
            return {
                "status": "hold",
                "reason": "valid_fresh_druidic_calibration_receipt_required",
                "source_path": str(path),
            }
    return {
        "status": status,
        "reason": payload.get("reason"),
        "receipt_id": payload.get("receipt_id")
        or (payload.get("calibration_receipt") or {}).get("receipt_id"),
        "negative_seats": list(payload.get("negative_seats") or []),
        "source_path": str(path),
    }


def bind_canonical_organism_composition(
    *,
    present_subsystems: Mapping[str, str],
    governance: GovernanceBindings | None = None,
    brain_fabric_report: Mapping[str, Any] | None = None,
    calibration_status: Mapping[str, Any] | None = None,
    economic_readiness: Mapping[str, Any] | None = None,
    queen_mind_report: Mapping[str, Any] | None = None,
) -> OrganismComposition:
    """Bind one root from process-owned components without waking any provider."""

    registrations = tuple(
        SubsystemRegistration(
            subsystem_id=_nonblank(subsystem_id, "subsystem_id"),
            role=_nonblank(role, "subsystem_role"),
            truth_status="real_observed",
            effect_class=(
                "governance"
                if subsystem_id in {"council", "crown"}
                else "evidence_only"
            ),
        )
        for subsystem_id, role in sorted(present_subsystems.items())
    )
    bank = validate_celtic_voice_bank_receipt(read_canonical_celtic_voice_bank())
    return OrganismComposition(
        registrations=registrations,
        governance=governance,
        brain_fabric_report=_canonical_copy(dict(brain_fabric_report or {})),
        calibration_status=_canonical_copy(
            dict(calibration_status or load_latest_calibration_status())
        ),
        economic_readiness=_canonical_copy(
            dict(
                economic_readiness
                or {
                    "status": "missing",
                    "reason": "current_economic_mutation_census_receipt_required",
                }
            )
        ),
        voice_bank_receipt=copy.deepcopy(bank),
        queen_mind_report=_validate_queen_mind_report(
            queen_mind_report
            or {
                "status": "missing",
                "reason": "canonical_queen_mind_manifest_required",
            }
        ),
    )


_COMPOSITION_LOCK = threading.RLock()
_COMPOSITION: OrganismComposition | None = None


def configure_canonical_organism_composition(
    composition: OrganismComposition,
) -> OrganismComposition:
    if not isinstance(composition, OrganismComposition):
        raise TypeError("canonical_organism_composition_required")
    global _COMPOSITION
    with _COMPOSITION_LOCK:
        _COMPOSITION = composition
    return composition


def get_canonical_organism_composition() -> OrganismComposition | None:
    with _COMPOSITION_LOCK:
        return _COMPOSITION


def reset_canonical_organism_composition_for_tests() -> None:
    global _COMPOSITION
    with _COMPOSITION_LOCK:
        _COMPOSITION = None


__all__ = [
    "CallableGovernanceAcquisitionSupplier",
    "GovernanceAcquisitionSupplier",
    "GovernanceBindings",
    "OrganismComposition",
    "QUEEN_MIND_REQUIRED_ROLES",
    "QUEEN_MIND_SCHEMA",
    "SCHEMA_VERSION",
    "SubsystemRegistration",
    "bind_canonical_organism_composition",
    "configure_canonical_organism_composition",
    "get_canonical_organism_composition",
    "load_latest_calibration_status",
]
