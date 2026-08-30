"""Request-aware production Crown supplier backed by QueenConscience.

Unlike the low-level Crown resolver protocol, this supplier receives the full
canonical governance request.  The Queen therefore evaluates the actual
proposal, not just two hashes, and the supplier independently reloads the exact
HNC/Auris provider moment before issuing the second rune.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Mapping, Protocol, runtime_checkable

from aureon.core.bus_trace import read_trace
from aureon.governance.cognition_gate import CognitionGovernanceRequest
from aureon.governance.crown_voice import (
    ResolvedCrownVoiceEvidence,
    TrustedCrownVoiceResolver,
    issue_crown_voice_receipt,
)
from aureon.swarm.auris_node_receipts import validate_provider_moment


@runtime_checkable
class QueenConscienceLike(Protocol):
    def ask_why(
        self,
        action: str,
        context: Mapping[str, Any] | None = None,
    ) -> Any: ...


ProviderEvidenceLoader = Callable[
    [CognitionGovernanceRequest],
    tuple[Mapping[str, Any], Mapping[str, Any]],
]


def _nonblank(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_required")
    return value.strip()


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _canonical_decimal(value: Any) -> str:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("provider_source_timestamp_must_be_decimal") from exc
    if not number.is_finite():
        raise ValueError("provider_source_timestamp_must_be_decimal")
    result = format(number, "f")
    if "." in result:
        result = result.rstrip("0").rstrip(".")
    return "0" if Decimal(result) == 0 else result


def load_local_request_provider_evidence(
    request: CognitionGovernanceRequest,
    *,
    now: float | None = None,
    max_age_s: float = 300.0,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    """Reload the exact request-bound pair from bounded local trace tails."""

    current = time.time() if now is None else float(now)
    if not math.isfinite(current):
        raise ValueError("finite_crown_clock_required")
    hnc_rows = {
        row.get("receipt_id"): row
        for row in read_trace("hnc_live_trace", limit=50_000)
        if isinstance(row.get("receipt_id"), str)
    }
    for auris in reversed(read_trace("auris_cosmic_state", limit=500)):
        hnc = hnc_rows.get(auris.get("hnc_receipt_id"))
        if hnc is None:
            continue
        try:
            moment = validate_provider_moment(
                hnc,
                auris,
                now=current,
                max_age_s=max_age_s,
            )
        except (TypeError, ValueError):
            continue
        if (
            tuple(moment.provider_receipt_ids) == request.provider_receipt_ids
            and moment.provider_moment_digest == request.provider_moment_digest
            and _canonical_decimal(moment.source_timestamp)
            == request.provider_source_timestamp
        ):
            return dict(hnc), dict(auris)
    raise ValueError("exact_request_provider_moment_unavailable")


@dataclass(frozen=True)
class _BoundQueenResolver:
    resolver_id: str
    issuer_id: str
    crown_identity: str
    verdict_source_id: str
    queen_verdict: str
    reason: str
    request: CognitionGovernanceRequest
    hnc_evidence: Mapping[str, Any]
    auris_evidence: Mapping[str, Any]

    def resolve_crown_voice_evidence(
        self,
        proposal_digest: str,
        prompt_digest: str,
    ) -> ResolvedCrownVoiceEvidence | None:
        if (
            proposal_digest != self.request.proposal_digest
            or prompt_digest != self.request.prompt_digest
        ):
            return None
        return ResolvedCrownVoiceEvidence(
            resolver_id=self.resolver_id,
            issuer_id=self.issuer_id,
            crown_identity=self.crown_identity,
            verdict_source_id=self.verdict_source_id,
            queen_verdict=self.queen_verdict,
            queen_evaluated=True,
            reason=self.reason,
            proposal_digest=proposal_digest,
            prompt_digest=prompt_digest,
            hnc_evidence=dict(self.hnc_evidence),
            auris_evidence=dict(self.auris_evidence),
        )


class QueenConscienceCrownSupplier:
    """Independent strict Crown voice for one canonical governance request."""

    supplier_id = "aureon:queen-conscience-crown-resolver"

    def __init__(
        self,
        *,
        conscience: QueenConscienceLike,
        evidence_loader: ProviderEvidenceLoader = load_local_request_provider_evidence,
        max_age_s: float = 300.0,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if not isinstance(conscience, QueenConscienceLike):
            raise TypeError("queen_conscience_required")
        if not callable(evidence_loader):
            raise TypeError("provider_evidence_loader_required")
        if isinstance(max_age_s, bool) or not isinstance(max_age_s, (int, float)):
            raise ValueError("positive_max_age_required")
        if not math.isfinite(float(max_age_s)) or float(max_age_s) <= 0.0:
            raise ValueError("positive_max_age_required")
        self._conscience = conscience
        self._evidence_loader = evidence_loader
        self._max_age_s = float(max_age_s)
        self._clock = clock

    def supply_crown_receipt(
        self,
        request: CognitionGovernanceRequest,
    ) -> Mapping[str, Any]:
        if not isinstance(request, CognitionGovernanceRequest):
            raise TypeError("cognition_governance_request_required")
        current = self._clock()
        if isinstance(current, bool) or not isinstance(current, (int, float)):
            raise ValueError("finite_crown_clock_required")
        now = float(current)
        if not math.isfinite(now):
            raise ValueError("finite_crown_clock_required")
        proposal = json.loads(request.proposal_json)
        if not isinstance(proposal, Mapping):
            raise ValueError("canonical_crown_proposal_required")
        hnc, auris = self._evidence_loader(request)
        moment = validate_provider_moment(
            hnc,
            auris,
            now=now,
            max_age_s=self._max_age_s,
        )
        if (
            tuple(moment.provider_receipt_ids) != request.provider_receipt_ids
            or moment.provider_moment_digest != request.provider_moment_digest
            or _canonical_decimal(moment.source_timestamp)
            != request.provider_source_timestamp
        ):
            raise ValueError("crown_request_provider_moment_mismatch")
        action = (
            "Evaluate exact governance proposal "
            f"{request.proposal_digest}: {_canonical(proposal)}"
        )
        whisper = self._conscience.ask_why(
            action,
            {
                "proposal": dict(proposal),
                "proposal_digest": request.proposal_digest,
                "prompt_digest": request.prompt_digest,
                "provider_moment_digest": request.provider_moment_digest,
            },
        )
        verdict = _nonblank(
            getattr(getattr(whisper, "verdict", None), "name", None),
            "queen_verdict",
        ).upper()
        reason = _nonblank(getattr(whisper, "message", None), "queen_reason")[:1000]
        verdict_source_id = (
            "queen:conscience:evaluation:"
            f"{_sha({'proposal': request.proposal_digest, 'verdict': verdict, 'reason': reason})}"
        )
        resolver = _BoundQueenResolver(
            resolver_id=self.supplier_id,
            issuer_id="aureon:crown:queen-conscience",
            crown_identity="QueenConscience",
            verdict_source_id=verdict_source_id,
            queen_verdict=verdict,
            reason=reason,
            request=request,
            hnc_evidence=hnc,
            auris_evidence=auris,
        )
        if not isinstance(resolver, TrustedCrownVoiceResolver):
            raise TypeError("trusted_bound_queen_resolver_required")
        return issue_crown_voice_receipt(
            proposal_digest=request.proposal_digest,
            prompt_digest=request.prompt_digest,
            resolver=resolver,
            now=now,
            max_age_s=self._max_age_s,
        )


assert isinstance(QueenConscienceCrownSupplier, type)

__all__ = [
    "QueenConscienceCrownSupplier",
    "QueenConscienceLike",
    "load_local_request_provider_evidence",
]
