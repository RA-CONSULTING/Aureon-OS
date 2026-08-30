"""Local material-aware truth authority for bounded cloud decisions.

Cloud inference may select one response from an exact response menu embedded
in the immutable operator prompt. It may not invent a fourth response or add
claims. The prompt is hashed as observed operator state, while an independent
diagnostic authority derives QGITA/math-angle signals from the exact answer.

This gate grants no action authority. Its strongest result is READY_FOR_AURIS.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from aureon.autonomous.aureon_ten_nine_one_thought_path import TenNineOneHold
from aureon.governance.qgita_kundalini_truth_gate import TruthGateRequest
from aureon.governance.trusted_truth_evidence import (
    CLAIM_SET_PREFIX,
    CLAIM_SET_SCHEMA,
    DIAGNOSTIC_SIGNAL_PREFIX,
    DIAGNOSTIC_SIGNAL_SCHEMA,
    EVIDENCE_ITEM_PREFIX,
    EVIDENCE_ITEM_SCHEMA,
    TrustedClaimEvidenceAuthority,
    TrustedDiagnosticSignalAuthority,
    evaluate_receipt_backed_truth_gate,
)
from aureon.harmonic.harmonic_text_alignment import score_text
from aureon.swarm.auris_node_receipts import (
    DEFAULT_MAX_AGE_S,
    validate_hnc_evidence,
)

ALLOWED_RESPONSE_MARKER = "ALLOWED EXACT RESPONSES:"
CLAIM_AUTHORITY_ID = "aureon:operator-material-claim-authority:v1"
EVIDENCE_ISSUER_ID = "aureon:operator-state-evidence-issuer:v1"
DIAGNOSTIC_AUTHORITY_ID = "aureon:qgita-harmonic-diagnostic-authority:v1"
_FALSE_FLAGS = (
    "action_eligible",
    "accounting_eligible",
    "learning_eligible",
    "action_gate_passed",
    "actionable",
    "operational_eligible",
    "provider_eligible",
    "eligible_for_action",
    "eligible_for_accounting",
    "eligible_for_learning",
    "economic_mutation",
)


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha(value: Any) -> str:
    material = value if isinstance(value, str) else _canonical(value)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _receipt(causal: Mapping[str, Any], prefix: str) -> dict[str, Any]:
    return {**causal, "receipt_id": f"{prefix}{_sha(causal)}"}


def _flags() -> dict[str, bool]:
    return dict.fromkeys(_FALSE_FLAGS, False)


def _nonblank(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label}_required")
    return value


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"finite_{label}_required")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"finite_{label}_required")
    return result


def extract_allowed_responses(prompt: str) -> tuple[str, ...]:
    """Read a bounded response menu; each nonempty following line is exact."""

    text = _nonblank(prompt, "prompt")
    marker_count = text.count(ALLOWED_RESPONSE_MARKER)
    if marker_count != 1:
        raise ValueError("one_allowed_exact_response_marker_required")
    menu = text.split(ALLOWED_RESPONSE_MARKER, 1)[1]
    responses = tuple(line.strip() for line in menu.splitlines() if line.strip())
    if not 2 <= len(responses) <= 6:
        raise ValueError("between_two_and_six_exact_responses_required")
    if len(set(responses)) != len(responses):
        raise ValueError("unique_exact_responses_required")
    if any(
        len(item) > 512
        or item.split(maxsplit=1)[0].upper() not in {"ACCEPT", "HOLD", "ABORT"}
        for item in responses
    ):
        raise ValueError("bounded_accept_hold_abort_responses_required")
    return responses


@dataclass(frozen=True)
class _BoundClaimAuthority:
    prompt: str
    answer: str
    hnc_receipt_id: str
    observed_at: float
    authority_id: str = CLAIM_AUTHORITY_ID

    def resolve_claim_evidence(self, request: TruthGateRequest) -> Mapping[str, Any]:
        if (
            request.prompt_digest != _sha(self.prompt)
            or request.answer_digest != _sha(self.answer)
            or request.hnc_receipt_id != self.hnc_receipt_id
        ):
            raise ValueError("bound_material_request_mismatch")
        responses = extract_allowed_responses(self.prompt)
        supported = self.answer in responses
        evidence = _receipt(
            {
                "schema_version": EVIDENCE_ITEM_SCHEMA,
                "issuer_id": EVIDENCE_ISSUER_ID,
                "source_kind": "operator_state",
                "source_uri": f"state://governance/prompt/{request.prompt_digest}",
                "source_locator": "exact-allowed-response-menu",
                "content_digest": request.prompt_digest,
                "source_timestamp": self.observed_at,
                "received_at": self.observed_at,
                "truth_status": "real_observed",
                "generated_values": False,
                **_flags(),
            },
            EVIDENCE_ITEM_PREFIX,
        )
        return _receipt(
            {
                "schema_version": CLAIM_SET_SCHEMA,
                "authority_id": self.authority_id,
                "prompt_digest": request.prompt_digest,
                "answer_digest": request.answer_digest,
                "hnc_receipt_id": request.hnc_receipt_id,
                "source_timestamp": self.observed_at,
                "received_at": self.observed_at,
                "truth_status": "real_derived",
                "generated_values": False,
                "evidence_receipts": [evidence],
                "claim_findings": [
                    {
                        "claim_id": _sha(
                            {
                                "answer_digest": request.answer_digest,
                                "menu_digest": _sha(responses),
                            }
                        ),
                        "failure_kind": "SUPPORTED" if supported else "UNSUPPORTED",
                        "evidence_receipt_ids": [evidence["receipt_id"]],
                    }
                ],
                **_flags(),
            },
            CLAIM_SET_PREFIX,
        )


@dataclass(frozen=True)
class _BoundDiagnosticAuthority:
    answer: str
    observed_at: float
    authority_id: str = DIAGNOSTIC_AUTHORITY_ID

    def resolve_diagnostic_signals(
        self,
        request: TruthGateRequest,
        grounding: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        if request.answer_digest != _sha(self.answer):
            raise ValueError("bound_diagnostic_answer_mismatch")
        report = score_text(self.answer)
        token = self.answer.split(maxsplit=1)[0].upper()
        return _receipt(
            {
                "schema_version": DIAGNOSTIC_SIGNAL_SCHEMA,
                "authority_id": self.authority_id,
                "grounding_receipt_id": grounding["receipt_id"],
                "prompt_digest": request.prompt_digest,
                "answer_digest": request.answer_digest,
                "hnc_receipt_id": request.hnc_receipt_id,
                "source_timestamp": self.observed_at,
                "received_at": self.observed_at,
                "truth_status": "real_derived",
                "generated_values": False,
                "evidence_receipt_ids": list(grounding["evidence_receipt_ids"]),
                "qgita_diagnostics": {
                    "decision_token": token,
                    "harmonic_coherence": float(report.coherence),
                    "state": "exact_menu_selection",
                },
                "math_angle_diagnostics": {
                    "dominant_mode": str(report.dominant_mode or "none"),
                    "mean_mode": float(report.mean_mode),
                    "mean_phi": float(report.mean_phi),
                },
                **_flags(),
            },
            DIAGNOSTIC_SIGNAL_PREFIX,
        )


class MaterialAwareTenNineOneTruthGate:
    """Per-answer bound local authorities for an exact operator response menu."""

    gate_id = "aureon:material-aware-kundalini-truth-gate:v1"

    def __init__(
        self,
        *,
        max_age_s: float = DEFAULT_MAX_AGE_S,
        now: Callable[[], float] = time.time,
    ) -> None:
        self._max_age_s = _finite(max_age_s, "max_age_s")
        if self._max_age_s <= 0.0:
            raise ValueError("positive_max_age_s_required")
        if not callable(now):
            raise TypeError("clock_callable_required")
        self._now = now

    def evaluate_answer(
        self,
        *,
        prompt: str,
        answer: str,
        hnc_evidence: Mapping[str, Any],
        correction_attempt: int,
    ) -> Mapping[str, Any]:
        current = _finite(self._now(), "now")
        try:
            hnc = validate_hnc_evidence(
                hnc_evidence,
                now=current,
                max_age_s=self._max_age_s,
            )
            request = TruthGateRequest(
                prompt_digest=_sha(_nonblank(prompt, "prompt")),
                answer_digest=_sha(_nonblank(answer, "answer")),
                hnc_receipt_id=hnc["receipt_id"],
                correction_attempt=correction_attempt,
            )
            claim = _BoundClaimAuthority(
                prompt=prompt,
                answer=answer,
                hnc_receipt_id=hnc["receipt_id"],
                observed_at=current,
            )
            diagnostics = _BoundDiagnosticAuthority(
                answer=answer,
                observed_at=current,
            )
            if not isinstance(claim, TrustedClaimEvidenceAuthority) or not isinstance(
                diagnostics,
                TrustedDiagnosticSignalAuthority,
            ):
                raise ValueError("trusted_material_authorities_required")
            return evaluate_receipt_backed_truth_gate(
                request,
                claim_authority=claim,
                diagnostic_authority=diagnostics,
                allowed_claim_authority_ids=frozenset({CLAIM_AUTHORITY_ID}),
                allowed_evidence_issuer_ids=frozenset({EVIDENCE_ISSUER_ID}),
                allowed_diagnostic_authority_ids=frozenset(
                    {DIAGNOSTIC_AUTHORITY_ID}
                ),
                now=current,
                max_age_s=self._max_age_s,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise TenNineOneHold("material_truth_gate_evidence_required") from exc


__all__ = [
    "ALLOWED_RESPONSE_MARKER",
    "CLAIM_AUTHORITY_ID",
    "DIAGNOSTIC_AUTHORITY_ID",
    "EVIDENCE_ISSUER_ID",
    "MaterialAwareTenNineOneTruthGate",
    "extract_allowed_responses",
]
