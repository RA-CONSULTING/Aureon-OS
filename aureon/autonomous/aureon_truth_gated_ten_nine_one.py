"""Truth-gated 10 -> 9 -> 1 release for controlled Aureon brain paths.

This wrapper leaves the established 10-9-1 implementation untouched.  It
interposes the receipt-backed Kundalini gate after inference and before the
underlying resolver may expose Auris evidence.  A correction or HOLD therefore
causes zero Auris lookups and zero Hive/Mycelia deliveries.

The outer receipt binds the full validated truth result to the full validated
10-9-1 receipt.  Like both inputs, it is evidence-only and grants no action,
learning, accounting, or economic authority.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from collections.abc import Callable, Mapping
from typing import Any, Protocol, runtime_checkable

from aureon.autonomous.aureon_ten_nine_one_thought_path import (
    TenNineOneEvidenceResolver,
    TenNineOneHold,
    TenNineOnePropagator,
    TenNineOneThoughtPath,
    ThoughtPathRequest,
    ThoughtPathResult,
    validate_ten_nine_one_receipt,
)
from aureon.bio.mcp_membrane import MEMBRANE_BOUNDARY, screen_ingress
from aureon.governance.qgita_kundalini_truth_gate import (
    TruthGateRequest,
    validate_truth_gate_result,
)
from aureon.governance.trusted_truth_evidence import (
    TrustedClaimEvidenceAuthority,
    TrustedDiagnosticSignalAuthority,
    evaluate_receipt_backed_truth_gate,
)
from aureon.swarm.auris_node_receipts import DEFAULT_MAX_AGE_S, validate_hnc_evidence

SCHEMA_VERSION = "aureon.truth-gated-10-9-1.v1"
RECEIPT_PREFIX = "thought:10-9-1:truth-gated:"
_FALSE_FLAGS = {
    "operational_eligible": False,
    "provider_eligible": False,
    "action_eligible": False,
    "actionable": False,
    "economic_eligible": False,
    "accounting_eligible": False,
    "learning_eligible": False,
    "eligible_for_action": False,
    "eligible_for_accounting": False,
    "eligible_for_learning": False,
    "action_gate_passed": False,
}


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256(value: Any) -> str:
    material = value if isinstance(value, str) else _canonical_json(value)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _finite(value: Any, label: str) -> float:
    if type(value) not in {int, float}:
        raise ValueError(f"finite_{label}_required")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"finite_{label}_required")
    return result


def _false_flags(payload: Mapping[str, Any]) -> None:
    if any(payload.get(key) is not value for key, value in _FALSE_FLAGS.items()):
        raise ValueError("truth_gated_path_is_evidence_only")


@runtime_checkable
class TenNineOneAnswerTruthGate(Protocol):
    """Exact-answer truth gate injected by the trusted composition root."""

    gate_id: str

    def evaluate_answer(
        self,
        *,
        prompt: str,
        answer: str,
        hnc_evidence: Mapping[str, Any],
        correction_attempt: int,
    ) -> Mapping[str, Any]: ...


class ReceiptBackedTenNineOneTruthGate:
    """Bind a validated HNC moment to independent claim and signal authorities."""

    gate_id = "aureon:receipt-backed-kundalini-truth-gate:v1"

    def __init__(
        self,
        *,
        claim_authority: TrustedClaimEvidenceAuthority,
        diagnostic_authority: TrustedDiagnosticSignalAuthority,
        allowed_claim_authority_ids: frozenset[str],
        allowed_evidence_issuer_ids: frozenset[str],
        allowed_diagnostic_authority_ids: frozenset[str],
        max_age_s: float = DEFAULT_MAX_AGE_S,
        now: Callable[[], float] = time.time,
    ) -> None:
        if not isinstance(claim_authority, TrustedClaimEvidenceAuthority):
            raise ValueError("trusted_claim_evidence_authority_required")
        if not isinstance(diagnostic_authority, TrustedDiagnosticSignalAuthority):
            raise ValueError("trusted_diagnostic_signal_authority_required")
        self._claim_authority = claim_authority
        self._diagnostic_authority = diagnostic_authority
        self._allowed_claim_ids = allowed_claim_authority_ids
        self._allowed_evidence_issuer_ids = allowed_evidence_issuer_ids
        self._allowed_diagnostic_ids = allowed_diagnostic_authority_ids
        self._max_age_s = _finite(max_age_s, "max_age_s")
        if self._max_age_s <= 0:
            raise ValueError("positive_max_age_s_required")
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
                prompt_digest=_sha256(prompt),
                answer_digest=_sha256(answer),
                hnc_receipt_id=hnc["receipt_id"],
                correction_attempt=correction_attempt,
            )
        except (KeyError, TypeError, ValueError):
            raise TenNineOneHold("truth_gate_fresh_hnc_required") from None
        return evaluate_receipt_backed_truth_gate(
            request,
            claim_authority=self._claim_authority,
            diagnostic_authority=self._diagnostic_authority,
            allowed_claim_authority_ids=self._allowed_claim_ids,
            allowed_evidence_issuer_ids=self._allowed_evidence_issuer_ids,
            allowed_diagnostic_authority_ids=self._allowed_diagnostic_ids,
            now=current,
            max_age_s=self._max_age_s,
        )


class _TruthInterceptingResolver:
    """Per-execution resolver that refuses Auris until truth is READY."""

    def __init__(
        self,
        *,
        delegate: TenNineOneEvidenceResolver,
        truth_gate: TenNineOneAnswerTruthGate,
        prompt: str,
        correction_attempt: int,
    ) -> None:
        self._delegate = delegate
        self._truth_gate = truth_gate
        self._prompt = prompt
        self._correction_attempt = correction_attempt
        self._hnc: Mapping[str, Any] | None = None
        self._answer: str | None = None
        self.truth_result: dict[str, Any] | None = None
        self.reply_screen: dict[str, Any] | None = None
        self.resolver_id = f"{delegate.resolver_id}+{truth_gate.gate_id}"

    def resolve_hnc_evidence(self, request: ThoughtPathRequest) -> Mapping[str, Any] | None:
        raw = self._delegate.resolve_hnc_evidence(request)
        self._hnc = dict(raw) if isinstance(raw, Mapping) else None
        return raw

    def record_answer(self, answer: str) -> None:
        self._answer = answer

    def resolve_auris_evidence(
        self,
        request: ThoughtPathRequest,
        *,
        answer_digest: str,
        hnc_receipt_id: str,
    ) -> Mapping[str, Any] | None:
        if self._hnc is None or self._answer is None:
            raise TenNineOneHold("truth_gate_answer_context_required")
        if _sha256(self._answer) != answer_digest or self._hnc.get("receipt_id") != hnc_receipt_id:
            raise TenNineOneHold("truth_gate_answer_lineage_mismatch")
        try:
            verdict = screen_ingress(self._answer, source="ollama_cloud_brain")
        except Exception as exc:  # noqa: BLE001 - membrane failure must hold closed
            raise TenNineOneHold("brain_reply_membrane_unavailable") from exc
        self.reply_screen = {
            "source": verdict.source,
            "contained": verdict.contained,
            "injection_matches": list(verdict.injection_matches),
            "blocked_action_claim": verdict.blocked_action_claim,
            "false_claims": list(verdict.false_claims),
            "boundary": verdict.boundary,
        }
        if verdict.contained:
            raise TenNineOneHold("brain_reply_membrane_contained")
        raw = self._truth_gate.evaluate_answer(
            prompt=self._prompt,
            answer=self._answer,
            hnc_evidence=self._hnc,
            correction_attempt=self._correction_attempt,
        )
        try:
            validated = validate_truth_gate_result(raw)
        except (TypeError, ValueError) as exc:
            raise TenNineOneHold("valid_truth_gate_receipt_required") from exc
        self.truth_result = validated
        if validated["status"] != "READY_FOR_AURIS":
            raise TenNineOneHold(
                "truth_gate_"
                + str(validated["status"]).lower()
                + ":"
                + str(validated["reason"])
            )
        if (
            validated["prompt_digest"] != _sha256(self._prompt)
            or validated["answer_digest"] != answer_digest
            or validated["hnc_receipt_id"] != hnc_receipt_id
        ):
            raise TenNineOneHold("truth_gate_release_lineage_mismatch")
        return self._delegate.resolve_auris_evidence(
            request,
            answer_digest=answer_digest,
            hnc_receipt_id=hnc_receipt_id,
        )


class TruthGatedTenNineOneThoughtPath:
    """Controlled path: HNC -> inference -> truth -> Auris -> Hive/Mycelia."""

    truth_gate_enforced = True

    def __init__(
        self,
        *,
        resolver: TenNineOneEvidenceResolver,
        propagator: TenNineOnePropagator,
        truth_gate: TenNineOneAnswerTruthGate,
        max_age_s: float = DEFAULT_MAX_AGE_S,
        now: Callable[[], float] = time.time,
    ) -> None:
        if not isinstance(resolver, TenNineOneEvidenceResolver):
            raise ValueError("trusted_10_9_1_evidence_resolver_required")
        if not isinstance(propagator, TenNineOnePropagator):
            raise ValueError("10_9_1_hive_mycelia_propagator_required")
        if not isinstance(truth_gate, TenNineOneAnswerTruthGate):
            raise ValueError("trusted_10_9_1_truth_gate_required")
        self._resolver = resolver
        self._propagator = propagator
        self._truth_gate = truth_gate
        self._max_age_s = _finite(max_age_s, "max_age_s")
        if self._max_age_s <= 0:
            raise ValueError("positive_max_age_s_required")
        self._now = now
        self._receipts: list[Mapping[str, Any]] = []

    @property
    def receipts(self) -> tuple[Mapping[str, Any], ...]:
        """Return validated outer receipts through the legacy path interface."""

        return tuple(json.loads(_canonical_json(item)) for item in self._receipts)

    def execute(
        self,
        *,
        request: ThoughtPathRequest,
        prompt: str,
        infer: Callable[[str], str],
        correction_attempt: int = 0,
    ) -> ThoughtPathResult:
        if type(correction_attempt) is not int or correction_attempt not in {0, 1, 2}:
            raise TenNineOneHold("correction_attempt_must_be_int_0_to_2")
        intercept = _TruthInterceptingResolver(
            delegate=self._resolver,
            truth_gate=self._truth_gate,
            prompt=prompt,
            correction_attempt=correction_attempt,
        )
        inner = TenNineOneThoughtPath(
            resolver=intercept,
            propagator=self._propagator,
            max_age_s=self._max_age_s,
            now=self._now,
        )

        def _infer(organized_prompt: str) -> str:
            answer = infer(organized_prompt)
            intercept.record_answer(answer)
            return answer

        result = inner.execute(request=request, prompt=prompt, infer=_infer)
        if intercept.truth_result is None:
            raise TenNineOneHold("truth_gate_receipt_required_before_release")
        if intercept.reply_screen is None:
            raise TenNineOneHold("brain_reply_membrane_receipt_required_before_release")
        inner_receipt = validate_ten_nine_one_receipt(result.receipt)
        truth_receipt = validate_truth_gate_result(intercept.truth_result)
        causal = {
            "schema_version": SCHEMA_VERSION,
            "inner_receipt_id": inner_receipt["receipt_id"],
            "inner_receipt": inner_receipt,
            "truth_gate_receipt": truth_receipt,
            "truth_gate_id": self._truth_gate.gate_id,
            "brain_reply_screen": intercept.reply_screen,
            "prompt_digest": inner_receipt["prompt_digest"],
            "answer_digest": inner_receipt["answer_digest"],
            "hnc_receipt_id": inner_receipt["answer_receipt"]["hnc_receipt_id"],
            "status": "truth_grounded_coherent_and_propagated",
            "derived_at": _finite(self._now(), "derived_at"),
            **_FALSE_FLAGS,
        }
        outer = {**causal, "receipt_id": f"{RECEIPT_PREFIX}{_sha256(causal)}"}
        validated_outer = validate_truth_gated_ten_nine_one_receipt(
            outer,
            now=self._now(),
            max_age_s=self._max_age_s,
        )
        self._receipts.append(validated_outer)
        return ThoughtPathResult(answer=result.answer, receipt=validated_outer)


def validate_truth_gated_ten_nine_one_receipt(
    receipt: Mapping[str, Any],
    *,
    now: float | None = None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
) -> dict[str, Any]:
    expected = {
        "schema_version",
        "receipt_id",
        "inner_receipt_id",
        "inner_receipt",
        "truth_gate_receipt",
        "truth_gate_id",
        "brain_reply_screen",
        "prompt_digest",
        "answer_digest",
        "hnc_receipt_id",
        "status",
        "derived_at",
        *_FALSE_FLAGS,
    }
    if not isinstance(receipt, Mapping) or set(receipt) != expected:
        raise ValueError("exact_truth_gated_10_9_1_receipt_required")
    _false_flags(receipt)
    if (
        receipt.get("schema_version") != SCHEMA_VERSION
        or receipt.get("status") != "truth_grounded_coherent_and_propagated"
    ):
        raise ValueError("truth_gated_10_9_1_status_required")
    derived_at = _finite(receipt.get("derived_at"), "derived_at")
    current = _finite(time.time() if now is None else now, "now")
    maximum = _finite(max_age_s, "max_age_s")
    if maximum <= 0:
        raise ValueError("positive_max_age_s_required")
    age = current - derived_at
    if age < -5.0 or age > maximum:
        raise ValueError("fresh_truth_gated_10_9_1_receipt_required")
    inner = validate_ten_nine_one_receipt(receipt["inner_receipt"])
    truth = validate_truth_gate_result(receipt["truth_gate_receipt"])
    screen = receipt["brain_reply_screen"]
    if (
        not isinstance(screen, Mapping)
        or set(screen)
        != {
            "source",
            "contained",
            "injection_matches",
            "blocked_action_claim",
            "false_claims",
            "boundary",
        }
        or screen.get("source") != "ollama_cloud_brain"
        or screen.get("contained") is not False
        or screen.get("injection_matches") != []
        or screen.get("blocked_action_claim") is not False
        or screen.get("false_claims") != []
        or screen.get("boundary") != MEMBRANE_BOUNDARY
    ):
        raise ValueError("clean_brain_reply_membrane_receipt_required")
    if truth["status"] != "READY_FOR_AURIS":
        raise ValueError("truth_ready_for_auris_required")
    if (
        receipt["inner_receipt_id"] != inner["receipt_id"]
        or receipt["prompt_digest"] != inner["prompt_digest"]
        or receipt["answer_digest"] != inner["answer_digest"]
        or receipt["hnc_receipt_id"] != inner["answer_receipt"]["hnc_receipt_id"]
        or truth["prompt_digest"] != receipt["prompt_digest"]
        or truth["answer_digest"] != receipt["answer_digest"]
        or truth["hnc_receipt_id"] != receipt["hnc_receipt_id"]
    ):
        raise ValueError("truth_gated_10_9_1_lineage_mismatch")
    if not isinstance(receipt["truth_gate_id"], str) or not receipt["truth_gate_id"].strip():
        raise ValueError("truth_gate_id_required")
    causal = {key: receipt[key] for key in expected - {"receipt_id"}}
    if receipt["receipt_id"] != f"{RECEIPT_PREFIX}{_sha256(causal)}":
        raise ValueError("truth_gated_10_9_1_receipt_hash_mismatch")
    return json.loads(_canonical_json(receipt))


__all__ = [
    "RECEIPT_PREFIX",
    "SCHEMA_VERSION",
    "ReceiptBackedTenNineOneTruthGate",
    "TenNineOneAnswerTruthGate",
    "TruthGatedTenNineOneThoughtPath",
    "validate_truth_gated_ten_nine_one_receipt",
]
