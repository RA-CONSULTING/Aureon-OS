"""Trusted four-seat Druid voice composition for two-rune governance.

This module is the request boundary for Council formation. The caller supplies
only immutable proposal anchors, four complete Auris-node receipts, and a
composition-root resolver. Agent identity, Gamma, receipt identifiers,
provider timestamps, and seat decisions are derived from those trusted bodies;
none are accepted as scalar request arguments.

Python protocol conformance is not authentication. Production wiring must
construct the resolver from an allowlisted local runtime and must never accept
a resolver implementation from request data or an untrusted plugin.
"""

from __future__ import annotations

import math
import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from aureon.swarm.auris_node_receipts import (
    DEFAULT_MAX_AGE_S,
    validate_auris_node_receipt,
)
from aureon.swarm.druidic_council import (
    REQUIRED_SEATS,
    TRUSTED_SEAT_SCHEMA,
    _build_trusted_seat_receipt,
    _no_data,
    convene_druidic_council,
    validate_council_receipt,
)

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_DECISIONS = frozenset({"ACCEPT", "HOLD", "ABORT"})


@dataclass(frozen=True)
class DruidSeatIssuerBinding:
    """One allowlisted resolver, issuer, source, seat, and agent binding."""

    resolver_id: str
    issuer_id: str
    decision_source_id: str
    seat: str
    agent_id: str


@dataclass(frozen=True)
class ResolvedDruidSeatVoice:
    """One authenticated Druid decision over an exact node/provider moment."""

    resolver_id: str
    issuer_id: str
    decision_source_id: str
    seat: str
    agent_id: str
    decision: str
    reason: str
    proposal_digest: str
    prompt_digest: str
    auris_node_receipt_id: str
    hnc_receipt_id: str
    auris_receipt_id: str
    provider_receipt_ids: tuple[str, ...]
    provider_moment_digest: str
    source_timestamp: float


@runtime_checkable
class TrustedDruidSeatResolver(Protocol):
    """Resolve allowlisted bindings and decisions from authenticated stores."""

    def trusted_druid_seat_bindings(
        self,
    ) -> Mapping[str, DruidSeatIssuerBinding]:
        """Return the fixed allowlist for all four stable Council seats."""

    def resolve_druid_seat_voice(
        self,
        seat: str,
        proposal_digest: str,
        prompt_digest: str,
    ) -> ResolvedDruidSeatVoice | None:
        """Return the trusted seat decision for the exact proposal anchors."""


def _nonblank(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_required")
    return value.strip()


def _digest(value: Any, name: str) -> str:
    text = _nonblank(value, name)
    if _DIGEST_RE.fullmatch(text) is None:
        raise ValueError(f"{name}_must_be_sha256")
    return text


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}_must_be_finite")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name}_must_be_finite")
    return number


def _validated_nodes(
    node_receipts: Sequence[Mapping[str, Any]],
    *,
    now: float,
    max_age_s: float,
) -> dict[str, dict[str, Any]]:
    if (
        not isinstance(node_receipts, Sequence)
        or isinstance(node_receipts, (str, bytes))
        or len(node_receipts) != len(REQUIRED_SEATS)
    ):
        raise ValueError("four_full_auris_node_receipts_required")
    nodes = [
        validate_auris_node_receipt(
            item,
            now=now,
            max_age_s=max_age_s,
        )
        for item in node_receipts
    ]
    if any(node.get("data_status") != "live" for node in nodes):
        raise ValueError("four_live_auris_node_receipts_required")
    by_seat = {node["seat"]: node for node in nodes}
    if set(by_seat) != set(REQUIRED_SEATS) or len(by_seat) != len(REQUIRED_SEATS):
        raise ValueError("exact_stable_auris_node_seats_required")
    if len({node["agent_id"] for node in nodes}) != len(REQUIRED_SEATS):
        raise ValueError("distinct_agent_per_stable_seat_required")
    if len({node["receipt_id"] for node in nodes}) != len(REQUIRED_SEATS):
        raise ValueError("distinct_auris_node_per_stable_seat_required")
    moments = {
        (
            node["hnc_receipt_id"],
            node["auris_receipt_id"],
            tuple(node["provider_receipt_ids"]),
            node["provider_moment_digest"],
            node["source_timestamp"],
        )
        for node in nodes
    }
    if len(moments) != 1:
        raise ValueError("exact_auris_node_provider_moment_required")
    return {seat: by_seat[seat] for seat in REQUIRED_SEATS}


def _validated_bindings(
    resolver: TrustedDruidSeatResolver,
    *,
    nodes: Mapping[str, Mapping[str, Any]],
) -> dict[str, DruidSeatIssuerBinding]:
    raw = resolver.trusted_druid_seat_bindings()
    if not isinstance(raw, Mapping) or set(raw) != set(REQUIRED_SEATS):
        raise ValueError("exact_trusted_druid_seat_allowlist_required")
    bindings: dict[str, DruidSeatIssuerBinding] = {}
    for seat in REQUIRED_SEATS:
        binding = raw[seat]
        if not isinstance(binding, DruidSeatIssuerBinding):
            raise ValueError("typed_trusted_druid_seat_binding_required")
        if (
            binding.seat != seat
            or _nonblank(binding.agent_id, "agent_id") != nodes[seat]["agent_id"]
        ):
            raise ValueError("trusted_druid_seat_binding_mismatch")
        canonical_fields = (
            (binding.resolver_id, "resolver_id"),
            (binding.issuer_id, "issuer_id"),
            (binding.decision_source_id, "decision_source_id"),
            (binding.seat, "seat"),
            (binding.agent_id, "agent_id"),
        )
        if any(value != _nonblank(value, name) for value, name in canonical_fields):
            raise ValueError("canonical_trusted_druid_binding_required")
        bindings[seat] = binding
    if len({binding.resolver_id for binding in bindings.values()}) != 1:
        raise ValueError("single_trusted_council_resolver_required")
    issuer_count = len({binding.issuer_id for binding in bindings.values()})
    if issuer_count not in {1, len(REQUIRED_SEATS)}:
        raise ValueError("issuer_must_be_per_seat_or_single_allowlisted_council")
    if len(
        {binding.decision_source_id for binding in bindings.values()}
    ) != len(REQUIRED_SEATS):
        raise ValueError("distinct_stable_decision_sources_required")
    return bindings


def _require_resolved_voice(
    resolved: ResolvedDruidSeatVoice | None,
    *,
    binding: DruidSeatIssuerBinding,
    node: Mapping[str, Any],
    proposal_digest: str,
    prompt_digest: str,
) -> tuple[str, str]:
    if not isinstance(resolved, ResolvedDruidSeatVoice):
        raise ValueError("resolved_druid_seat_voice_required")
    expected_binding = (
        binding.resolver_id,
        binding.issuer_id,
        binding.decision_source_id,
        binding.seat,
        binding.agent_id,
    )
    resolved_binding = (
        resolved.resolver_id,
        resolved.issuer_id,
        resolved.decision_source_id,
        resolved.seat,
        resolved.agent_id,
    )
    if resolved_binding != expected_binding:
        raise ValueError("resolved_druid_issuer_binding_mismatch")
    if (
        resolved.proposal_digest != proposal_digest
        or resolved.prompt_digest != prompt_digest
        or resolved.auris_node_receipt_id != node["receipt_id"]
        or resolved.hnc_receipt_id != node["hnc_receipt_id"]
        or resolved.auris_receipt_id != node["auris_receipt_id"]
        or tuple(resolved.provider_receipt_ids)
        != tuple(node["provider_receipt_ids"])
        or resolved.provider_moment_digest != node["provider_moment_digest"]
        or _finite(resolved.source_timestamp, "source_timestamp")
        != node["source_timestamp"]
    ):
        raise ValueError("resolved_druid_voice_lineage_mismatch")
    decision = _nonblank(resolved.decision, "decision").upper()
    if decision not in _DECISIONS:
        raise ValueError("recognized_druid_decision_required")
    return decision, _nonblank(resolved.reason, "reason")


def issue_trusted_druidic_council(
    *,
    proposal_digest: str,
    prompt_digest: str,
    auris_node_receipts: Sequence[Mapping[str, Any]],
    resolver: TrustedDruidSeatResolver,
    now: float | None = None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
) -> dict[str, Any]:
    """Issue a Council receipt from four nodes and one trusted seat resolver."""

    try:
        current = _finite(time.time() if now is None else now, "now")
        age_limit = _finite(max_age_s, "max_age_s")
        if age_limit <= 0.0:
            raise ValueError("positive_max_age_required")
        expected_proposal = _digest(proposal_digest, "proposal_digest")
        expected_prompt = _digest(prompt_digest, "prompt_digest")
        if not isinstance(resolver, TrustedDruidSeatResolver):
            raise ValueError("trusted_druid_seat_resolver_required")
        nodes = _validated_nodes(
            auris_node_receipts,
            now=current,
            max_age_s=age_limit,
        )
        bindings = _validated_bindings(resolver, nodes=nodes)
        seat_receipts = []
        for seat in REQUIRED_SEATS:
            resolved = resolver.resolve_druid_seat_voice(
                seat,
                expected_proposal,
                expected_prompt,
            )
            decision, reason = _require_resolved_voice(
                resolved,
                binding=bindings[seat],
                node=nodes[seat],
                proposal_digest=expected_proposal,
                prompt_digest=expected_prompt,
            )
            seat_receipts.append(
                _build_trusted_seat_receipt(
                    decision=decision,
                    reason=reason,
                    proposal_digest=expected_proposal,
                    prompt_digest=expected_prompt,
                    resolver_id=bindings[seat].resolver_id,
                    issuer_id=bindings[seat].issuer_id,
                    decision_source_id=bindings[seat].decision_source_id,
                    auris_node_receipt=nodes[seat],
                    now=current,
                    max_age_s=age_limit,
                )
            )
        first = nodes[REQUIRED_SEATS[0]]
        council = convene_druidic_council(
            proposal_digest=expected_proposal,
            prompt_digest=expected_prompt,
            hnc_receipt_id=first["hnc_receipt_id"],
            auris_receipt_id=first["auris_receipt_id"],
            seat_receipts=seat_receipts,
            now=current,
            max_age_s=age_limit,
        )
        if council.get("data_status") != "live":
            raise ValueError("trusted_druidic_council_not_live")
        return validate_trusted_druidic_council_receipt(
            council,
            now=current,
            max_age_s=age_limit,
        )
    except Exception:
        return _no_data("complete_trusted_linked_druidic_council_required")


def validate_trusted_druidic_council_receipt(
    receipt: Mapping[str, Any],
    *,
    now: float | None = None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
) -> dict[str, Any]:
    """Validate a Council and require four recursively validated trusted seats."""

    council = validate_council_receipt(
        receipt,
        now=now,
        max_age_s=max_age_s,
    )
    seats = council.get("seat_receipts")
    if (
        not isinstance(seats, list)
        or len(seats) != len(REQUIRED_SEATS)
        or any(item.get("schema") != TRUSTED_SEAT_SCHEMA for item in seats)
    ):
        raise ValueError("trusted_druidic_council_receipt_required")
    return council


__all__ = [
    "DruidSeatIssuerBinding",
    "ResolvedDruidSeatVoice",
    "TrustedDruidSeatResolver",
    "issue_trusted_druidic_council",
    "validate_trusted_druidic_council_receipt",
]
