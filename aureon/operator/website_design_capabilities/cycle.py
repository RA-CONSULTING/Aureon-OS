"""Deterministic, side-effect-free orchestration of the HNC design loop."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass

from aureon.operator.website_design_capability_set import (
    EVIDENCE_ROOT,
    HNC_LOOP,
    REQUIRED_SKILL_IDS,
    SKILL_BY_ID,
    require_valid_website_design_capability_set,
)

from .common import CapabilityInputError, CapabilityResult

CYCLE_SCHEMA = "aureon.website-design-cycle-receipt.v1"
_IDENTIFIER = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,99}$")
_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")

STAGE_OWNER: Mapping[str, str] = {
    "Sense": "research_object",
    "Route": "design_director",
    "Constraint": "evidence_copy",
    "Generate": "frontend_implementation",
    "Test": "audit_benchmark",
    "ResonanceCheck": "design_director",
    "Veto": "audit_benchmark",
    "AuthorityGate": "ceo_owner_user",
    "Deploy": "homepl_deploy",
    "ReadBack": "homepl_deploy",
    "Ledger": "audit_benchmark",
    "Expand": "skill_writer",
}


@dataclass(frozen=True)
class AuthorityDecision:
    """Caller-supplied human decision bound to an exact candidate and target."""

    approved: bool
    candidate_hash: str
    target: str
    actor: str = "ceo_owner_user"


@dataclass(frozen=True)
class CycleStageReceipt:
    """One immutable stage decision with exactly one accountable owner."""

    ordinal: int
    stage: str
    owner: str
    outcome: str
    next_stage: str
    capability_ids: tuple[str, ...]
    evidence_paths: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "ordinal": self.ordinal,
            "stage": self.stage,
            "owner": self.owner,
            "outcome": self.outcome,
            "next_stage": self.next_stage,
            "capability_ids": list(self.capability_ids),
            "evidence_paths": list(self.evidence_paths),
        }


@dataclass(frozen=True)
class CycleReceipt:
    """Immutable in-memory receipt; serialisation performs no file write."""

    cycle_id: str
    candidate_hash: str
    target: str
    state: str
    authority_binding_valid: bool
    veto_active: bool
    stages: tuple[CycleStageReceipt, ...]
    evidence_path: str
    receipt_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": CYCLE_SCHEMA,
            "cycle_id": self.cycle_id,
            "candidate_hash": self.candidate_hash,
            "target": self.target,
            "state": self.state,
            "authority_binding_valid": self.authority_binding_valid,
            "veto_active": self.veto_active,
            "stages": [stage.to_dict() for stage in self.stages],
            "evidence_path": self.evidence_path,
            "receipt_sha256": self.receipt_sha256,
            "write_performed": False,
            "release_eligible": False,
            "deployment_authority": "none",
        }


def _validate_results(results: Mapping[str, CapabilityResult]) -> None:
    if set(results) != set(REQUIRED_SKILL_IDS):
        missing = sorted(set(REQUIRED_SKILL_IDS) - set(results))
        unexpected = sorted(set(results) - set(REQUIRED_SKILL_IDS))
        raise CapabilityInputError(
            f"capability result set mismatch; missing={missing}, unexpected={unexpected}"
        )
    for skill_id, result in results.items():
        if not isinstance(result, CapabilityResult) or result.skill_id != skill_id:
            raise CapabilityInputError(f"capability result rebound or invalid: {skill_id}")


def _authority_is_bound(
    decision: AuthorityDecision | None,
    candidate_hash: str,
    target: str,
) -> bool:
    return (
        decision is not None
        and decision.approved
        and decision.actor == "ceo_owner_user"
        and decision.candidate_hash.lower() == candidate_hash
        and decision.target == target
    )


def run_readonly_design_cycle(
    *,
    cycle_id: str,
    candidate_hash: str,
    target: str,
    results: Mapping[str, CapabilityResult],
    authority_decision: AuthorityDecision | None = None,
) -> CycleReceipt:
    """Route all 15 results through HNC gates and return an in-memory receipt.

    Even a valid human decision only records that the exact candidate is ready
    for the separate authenticated deploy operator.  This function never
    performs or authorises that external effect.
    """

    require_valid_website_design_capability_set()
    if not _IDENTIFIER.fullmatch(cycle_id):
        raise CapabilityInputError("cycle_id must be a safe identifier")
    if not _SHA256.fullmatch(candidate_hash):
        raise CapabilityInputError("candidate_hash must be a SHA-256 digest")
    candidate = candidate_hash.lower()
    if not target.startswith(("https://", "homepl:")):
        raise CapabilityInputError("target must be an HTTPS URL or explicit homepl target")
    _validate_results(results)

    veto_active = any(not result.passed for result in results.values())
    authority_bound = not veto_active and _authority_is_bound(authority_decision, candidate, target)
    if veto_active:
        state = "vetoed"
    elif authority_bound:
        state = "authority-recorded-awaiting-external-deployment"
    else:
        state = "awaiting-human-authority"

    stage_receipts: list[CycleStageReceipt] = []
    for ordinal, loop_step in enumerate(HNC_LOOP, start=1):
        capability_ids = tuple(
            skill_id for skill_id in REQUIRED_SKILL_IDS if loop_step.stage in SKILL_BY_ID[skill_id].hnc_stages
        )
        stage_blocked = any(not results[skill_id].passed for skill_id in capability_ids)
        if loop_step.stage == "Veto":
            outcome = "blocked" if veto_active else "clear"
        elif loop_step.stage == "AuthorityGate":
            outcome = (
                "recorded"
                if authority_bound
                else ("blocked-by-veto" if veto_active else "not-supplied-or-not-bound")
            )
        elif loop_step.stage == "Deploy":
            outcome = "external-effect-not-performed" if authority_bound else "blocked"
        elif loop_step.stage == "ReadBack":
            outcome = (
                "verified-captured-input" if results["homepl_deploy_cache_ssl_readback"].passed else "blocked"
            )
        elif loop_step.stage == "Ledger":
            outcome = "immutable-in-memory-receipt-prepared"
        elif stage_blocked or veto_active:
            outcome = "blocked"
        else:
            outcome = "passed"
        paths = tuple(SKILL_BY_ID[skill_id].evidence_path for skill_id in capability_ids)
        stage_receipts.append(
            CycleStageReceipt(
                ordinal=ordinal,
                stage=loop_step.stage,
                owner=STAGE_OWNER[loop_step.stage],
                outcome=outcome,
                next_stage=loop_step.next_stage,
                capability_ids=capability_ids,
                evidence_paths=paths,
            )
        )

    evidence_path = (EVIDENCE_ROOT.parent / "cycle-evidence" / f"{cycle_id}.json").as_posix()
    unsigned: dict[str, object] = {
        "schema": CYCLE_SCHEMA,
        "cycle_id": cycle_id,
        "candidate_hash": candidate,
        "target": target,
        "state": state,
        "authority_binding_valid": authority_bound,
        "veto_active": veto_active,
        "stages": [stage.to_dict() for stage in stage_receipts],
        "evidence_path": evidence_path,
        "write_performed": False,
        "release_eligible": False,
        "deployment_authority": "none",
    }
    canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")
    receipt_hash = hashlib.sha256(canonical).hexdigest()
    return CycleReceipt(
        cycle_id=cycle_id,
        candidate_hash=candidate,
        target=target,
        state=state,
        authority_binding_valid=authority_bound,
        veto_active=veto_active,
        stages=tuple(stage_receipts),
        evidence_path=evidence_path,
        receipt_sha256=receipt_hash,
    )
