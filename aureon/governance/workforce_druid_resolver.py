"""Turn Aureon's receipt-backed internal cloud brains into Druid seat voices.

This adapter does not grant the workforce authority. It asks four configured
agent brains for an exact ACCEPT/HOLD/ABORT decision only after the four Auris
nodes exist, validates each 10-9-1 work receipt, and exposes those decisions to
the existing trusted Druid Council issuer.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from aureon.autonomous.aureon_internal_coding_workforce import (
    INTERNAL_ACTOR,
    WorkReceipt,
    validate_work_receipt,
)
from aureon.governance.cognition_gate import CognitionGovernanceRequest
from aureon.governance.druid_voice import (
    DruidSeatIssuerBinding,
    ResolvedDruidSeatVoice,
    TrustedDruidSeatResolver,
)
from aureon.swarm.auris_node_receipts import (
    DEFAULT_MAX_AGE_S,
    validate_auris_node_receipt,
)
from aureon.swarm.druidic_council import REQUIRED_SEATS

WORKFORCE_DRUID_SCHEMA = "aureon.workforce-druid-deliberation.v1"
DEFAULT_WORKFORCE_DRUID_ROLES: Mapping[str, str] = {
    "seer": "Counter Intelligence Validator",
    "sentinel": "Risk Governor",
    "weaver": "CTO Code Architect",
    "keeper": "Chief Memory Vault Officer",
}

_FACTORY_TOKEN = object()
_DECISIONS = frozenset({"ACCEPT", "HOLD", "ABORT"})


@runtime_checkable
class TrustedWorkforceDecisionEngine(Protocol):
    """The narrow internal workforce surface used for Council deliberation."""

    def process_id_for_role(self, role: str) -> str:
        """Return the independently brain-bound process for the role."""

    def decide(
        self,
        *,
        subject_type: str,
        subject_id: str,
        process_id: str,
        prompt: str,
        stage: str,
        work_kind: str,
        max_tokens: int | None = None,
    ) -> tuple[str, WorkReceipt]:
        """Run one truth-gated 10-9-1 cloud-brain decision."""


def _nonblank(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}_required")
    return value.strip()


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _bounded_decision_evidence(request: CognitionGovernanceRequest) -> dict[str, Any] | None:
    try:
        proposal = json.loads(request.proposal_json)
    except json.JSONDecodeError as exc:
        raise ValueError("canonical_governance_proposal_json_required") from exc
    if not isinstance(proposal, dict):
        raise ValueError("governance_proposal_object_required")
    tool_calls = proposal.get("tool_calls")
    if not isinstance(tool_calls, list) or len(tool_calls) != 1:
        return None
    call = tool_calls[0]
    if not isinstance(call, dict):
        return None
    arguments = call.get("arguments")
    if not isinstance(arguments, dict) or len(arguments) != 1:
        return None
    route_payload = next(iter(arguments.values()))
    if not isinstance(route_payload, dict):
        return None
    evidence_json = route_payload.get("decision_evidence_json")
    if evidence_json is None:
        return None
    if not isinstance(evidence_json, str) or len(evidence_json.encode("utf-8")) > 32 * 1024:
        raise ValueError("bounded_decision_evidence_required")
    try:
        evidence = json.loads(evidence_json)
    except json.JSONDecodeError as exc:
        raise ValueError("canonical_decision_evidence_required") from exc
    if not isinstance(evidence, dict) or _canonical_json(evidence) != evidence_json:
        raise ValueError("canonical_decision_evidence_required")
    allowed = {
        "action_influence_allowed",
        "blockers",
        "capital_market_evidence_receipt_id",
        "context_ready",
        "context_source_kinds",
        "probability",
        "recommended_side",
        "target_provider_moment_digest",
        "target_provider_source_timestamp",
        "target_ready",
        "volatility",
    }
    if set(evidence) != allowed:
        raise ValueError("exact_non_sensitive_decision_evidence_required")
    return evidence


def _trusted_ids(values: Collection[str], label: str) -> frozenset[str]:
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{label}_must_be_a_collection")
    result = [_nonblank(value, label).casefold() for value in values]
    if not result or len(result) != len(set(result)):
        raise ValueError(f"distinct_nonempty_{label}_required")
    return frozenset(result)


def _positive_finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"positive_finite_{label}_required")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"positive_finite_{label}_required")
    return result


def _decision_and_reason(output: Any) -> tuple[str, str]:
    text = _nonblank(output, "workforce_decision")
    parts = text.split(maxsplit=1)
    decision = parts[0].upper()
    if decision not in _DECISIONS:
        raise ValueError("exact_workforce_accept_hold_abort_token_required")
    if len(parts) != 2 or not parts[1].strip():
        raise ValueError("workforce_decision_reason_required")
    return decision, parts[1].strip()


@dataclass(frozen=True, slots=True)
class _SeatDecision:
    binding: DruidSeatIssuerBinding
    voice: ResolvedDruidSeatVoice


class WorkforceDruidSeatResolver:
    """Immutable resolver containing exactly four validated workforce decisions."""

    def __init__(
        self,
        *,
        _factory_token: object,
        decisions: Mapping[str, _SeatDecision],
    ) -> None:
        if _factory_token is not _FACTORY_TOKEN:
            raise TypeError("use_bind_workforce_druid_resolver_factory")
        if set(decisions) != set(REQUIRED_SEATS):
            raise ValueError("exact_four_workforce_druid_decisions_required")
        self._decisions = dict(decisions)

    def trusted_druid_seat_bindings(
        self,
    ) -> Mapping[str, DruidSeatIssuerBinding]:
        return {seat: self._decisions[seat].binding for seat in REQUIRED_SEATS}

    def resolve_druid_seat_voice(
        self,
        seat: str,
        proposal_digest: str,
        prompt_digest: str,
    ) -> ResolvedDruidSeatVoice | None:
        item = self._decisions.get(str(seat).strip().lower())
        if item is None:
            return None
        voice = item.voice
        if (
            voice.proposal_digest != proposal_digest
            or voice.prompt_digest != prompt_digest
        ):
            return None
        return voice


class WorkforceDruidResolverFactory:
    """Build one Council resolver from four fresh 10-9-1 workforce receipts."""

    def __init__(
        self,
        *,
        _factory_token: object,
        factory_id: str,
        resolver_id: str,
        issuer_id_prefix: str,
        workforce: TrustedWorkforceDecisionEngine,
        seat_roles: Mapping[str, str],
        max_age_s: float,
        clock: Callable[[], float],
    ) -> None:
        if _factory_token is not _FACTORY_TOKEN:
            raise TypeError("use_bind_workforce_druid_resolver_factory")
        self.factory_id = _nonblank(factory_id, "factory_id")
        self._resolver_id = _nonblank(resolver_id, "resolver_id")
        self._issuer_id_prefix = _nonblank(issuer_id_prefix, "issuer_id_prefix")
        self._workforce = workforce
        self._seat_roles = dict(seat_roles)
        self._max_age_s = max_age_s
        self._clock = clock

    @staticmethod
    def _deliberation_prompt(
        request: CognitionGovernanceRequest,
        *,
        seat: str,
        role: str,
        process_id: str,
        node: Mapping[str, Any],
    ) -> str:
        decision_evidence = _bounded_decision_evidence(request)
        proposal = _canonical_json(
            {
                "schema": WORKFORCE_DRUID_SCHEMA,
                "instruction": (
                    "Select exactly one complete line from the response menu "
                    "appended after this canonical proposal."
                ),
                "seat": seat,
                "agent_role": role,
                "process_id": process_id,
                "proposal_digest": request.proposal_digest,
                "prompt_digest": request.prompt_digest,
                "decision_evidence": decision_evidence,
                "auris_node_receipt_id": node["receipt_id"],
                "hnc_receipt_id": node["hnc_receipt_id"],
                "auris_receipt_id": node["auris_receipt_id"],
                "provider_receipt_ids": node["provider_receipt_ids"],
                "provider_moment_digest": node["provider_moment_digest"],
                "source_timestamp": node["source_timestamp"],
            }
        )
        return (
            proposal
            + "\nALLOWED EXACT RESPONSES:\n"
            + "ACCEPT exact_proposal_receipts_and_limits_satisfied\n"
            + "HOLD missing_stale_or_incoherent_required_evidence\n"
            + "ABORT explicit_veto_or_lineage_conflict"
        )

    def _validated_work(
        self,
        *,
        role: str,
        process_id: str,
        prompt: str,
        output: str,
        receipt: WorkReceipt,
        current: float,
    ) -> None:
        if not validate_work_receipt(receipt):
            raise ValueError("valid_truth_gated_work_receipt_required")
        if (
            receipt.actor_class != INTERNAL_ACTOR
            or receipt.actor_id != f"aureon:agent:{role}"
            or receipt.process_id != process_id
            or receipt.stage != "druidic_council_deliberation"
            or receipt.work_kind != "druid_seat_governance"
            or receipt.input_digest != _digest_text(prompt)
            or receipt.output_digest != _digest_text(output)
            or receipt.action_eligible is not False
            or receipt.economic_eligible is not False
        ):
            raise ValueError("workforce_druid_receipt_binding_mismatch")
        completed = receipt.completed_at
        if (
            isinstance(completed, bool)
            or not isinstance(completed, (int, float))
            or not math.isfinite(float(completed))
            or float(completed) > current
            or current - float(completed) > self._max_age_s
        ):
            raise ValueError("fresh_workforce_druid_receipt_required")

    def build_druid_seat_resolver(
        self,
        request: CognitionGovernanceRequest,
        auris_node_receipts: Sequence[Mapping[str, Any]],
    ) -> TrustedDruidSeatResolver:
        if not isinstance(request, CognitionGovernanceRequest):
            raise TypeError("cognition_governance_request_required")
        current_raw = self._clock()
        if isinstance(current_raw, bool) or not isinstance(current_raw, (int, float)):
            raise ValueError("finite_governance_clock_required")
        current = float(current_raw)
        if not math.isfinite(current):
            raise ValueError("finite_governance_clock_required")
        if (
            not isinstance(auris_node_receipts, Sequence)
            or isinstance(auris_node_receipts, (str, bytes))
            or len(auris_node_receipts) != len(REQUIRED_SEATS)
        ):
            raise ValueError("four_auris_node_receipts_required")
        nodes = tuple(
            validate_auris_node_receipt(
                node,
                now=current,
                max_age_s=self._max_age_s,
            )
            for node in auris_node_receipts
        )
        if (
            [node["seat"] for node in nodes] != list(REQUIRED_SEATS)
            or any(node.get("data_status") != "live" for node in nodes)
        ):
            raise ValueError("ordered_live_auris_node_receipts_required")
        decisions: dict[str, _SeatDecision] = {}
        for seat, node in zip(REQUIRED_SEATS, nodes, strict=True):
            role = self._seat_roles[seat]
            process_id = _nonblank(
                self._workforce.process_id_for_role(role),
                "process_id",
            )
            prompt = self._deliberation_prompt(
                request,
                seat=seat,
                role=role,
                process_id=process_id,
                node=node,
            )
            output, receipt = self._workforce.decide(
                subject_type="agent",
                subject_id=role,
                process_id=process_id,
                prompt=prompt,
                stage="druidic_council_deliberation",
                work_kind="druid_seat_governance",
                max_tokens=512,
            )
            output_text = _nonblank(output, "workforce_decision")
            self._validated_work(
                role=role,
                process_id=process_id,
                prompt=prompt,
                output=output_text,
                receipt=receipt,
                current=current,
            )
            decision, reason = _decision_and_reason(output_text)
            binding = DruidSeatIssuerBinding(
                resolver_id=self._resolver_id,
                issuer_id=f"{self._issuer_id_prefix}:{seat}",
                decision_source_id=receipt.receipt_id,
                seat=seat,
                agent_id=node["agent_id"],
            )
            voice = ResolvedDruidSeatVoice(
                resolver_id=binding.resolver_id,
                issuer_id=binding.issuer_id,
                decision_source_id=binding.decision_source_id,
                seat=seat,
                agent_id=node["agent_id"],
                decision=decision,
                reason=(
                    f"work_receipt={receipt.receipt_id}; "
                    f"thought_path={receipt.thought_path_receipt_id}; {reason}"
                ),
                proposal_digest=request.proposal_digest,
                prompt_digest=request.prompt_digest,
                auris_node_receipt_id=node["receipt_id"],
                hnc_receipt_id=node["hnc_receipt_id"],
                auris_receipt_id=node["auris_receipt_id"],
                provider_receipt_ids=tuple(node["provider_receipt_ids"]),
                provider_moment_digest=node["provider_moment_digest"],
                source_timestamp=node["source_timestamp"],
            )
            decisions[seat] = _SeatDecision(binding=binding, voice=voice)
        return WorkforceDruidSeatResolver(
            _factory_token=_FACTORY_TOKEN,
            decisions=decisions,
        )


def bind_workforce_druid_resolver_factory(
    *,
    factory_id: str,
    resolver_id: str,
    issuer_id_prefix: str,
    trusted_factory_ids: Collection[str],
    workforce: TrustedWorkforceDecisionEngine,
    seat_roles: Mapping[str, str] = DEFAULT_WORKFORCE_DRUID_ROLES,
    max_age_s: float = DEFAULT_MAX_AGE_S,
    clock: Callable[[], float] = time.time,
) -> WorkforceDruidResolverFactory:
    """Bind the internal workforce as a non-authoritative Council voice source."""

    if not isinstance(workforce, TrustedWorkforceDecisionEngine):
        raise TypeError("trusted_workforce_decision_engine_required")
    factory_name = _nonblank(factory_id, "factory_id")
    if factory_name.casefold() not in _trusted_ids(
        trusted_factory_ids,
        "trusted_factory_id",
    ):
        raise ValueError("workforce_druid_factory_not_allowlisted")
    roles = {
        _nonblank(seat, "seat").lower(): _nonblank(role, "role")
        for seat, role in seat_roles.items()
    }
    if (
        set(roles) != set(REQUIRED_SEATS)
        or len(set(roles.values())) != len(REQUIRED_SEATS)
    ):
        raise ValueError("exact_distinct_four_seat_workforce_roles_required")
    age = _positive_finite(max_age_s, "max_age_s")
    if not callable(clock):
        raise TypeError("clock_callable_required")
    return WorkforceDruidResolverFactory(
        _factory_token=_FACTORY_TOKEN,
        factory_id=factory_name,
        resolver_id=resolver_id,
        issuer_id_prefix=issuer_id_prefix,
        workforce=workforce,
        seat_roles=roles,
        max_age_s=age,
        clock=clock,
    )


__all__ = [
    "DEFAULT_WORKFORCE_DRUID_ROLES",
    "TrustedWorkforceDecisionEngine",
    "WORKFORCE_DRUID_SCHEMA",
    "WorkforceDruidResolverFactory",
    "WorkforceDruidSeatResolver",
    "bind_workforce_druid_resolver_factory",
]
