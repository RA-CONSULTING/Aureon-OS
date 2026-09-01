"""Synthetic, offline-only receipts for focused 10-9-1 tests."""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping
from typing import Any

from aureon.autonomous.aureon_cloud_brain_composition import (
    TruthAuthorityBundle,
)
from aureon.autonomous.aureon_ten_nine_one_thought_path import (
    CommitmentOnlyHiveMyceliaPropagator,
    LocalHncAurisEvidenceResolver,
    ThoughtPathRequest,
    build_delivery_ack,
)
from aureon.autonomous.aureon_truth_gated_ten_nine_one import (
    ReceiptBackedTenNineOneTruthGate,
    TruthGatedTenNineOneThoughtPath,
)
from aureon.core.aureon_thought_bus import Thought, ThoughtBus
from aureon.governance.qgita_kundalini_truth_gate import TruthGateRequest, _result
from aureon.governance.trusted_truth_evidence import (
    CLAIM_SET_PREFIX,
    CLAIM_SET_SCHEMA,
    DIAGNOSTIC_SIGNAL_PREFIX,
    DIAGNOSTIC_SIGNAL_SCHEMA,
    EVIDENCE_ITEM_PREFIX,
    EVIDENCE_ITEM_SCHEMA,
)

NOW = 1_786_480_000.0

INPUT_FALSE_FLAGS = (
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
)
TRUTH_FALSE_FLAGS = {
    **dict.fromkeys(INPUT_FALSE_FLAGS, False),
    "economic_mutation": False,
}
TEST_CLAIM_AUTHORITY_ID = "aureon:test:self-coder-claim-authority"
TEST_EVIDENCE_ISSUER_ID = "aureon:test:self-coder-evidence-issuer"
TEST_DIAGNOSTIC_AUTHORITY_ID = "aureon:test:self-coder-diagnostic-authority"


def _sha(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _false_flags() -> dict[str, bool]:
    return dict.fromkeys(INPUT_FALSE_FLAGS, False)


def _truth_receipt(causal: Mapping[str, Any], prefix: str) -> dict[str, Any]:
    return {**causal, "receipt_id": f"{prefix}{_sha(causal)}"}


class _SelfCoderClaimAuthority:
    authority_id = TEST_CLAIM_AUTHORITY_ID

    def resolve_claim_evidence(self, request: TruthGateRequest) -> Mapping[str, Any]:
        evidence = _truth_receipt(
            {
                "schema_version": EVIDENCE_ITEM_SCHEMA,
                "issuer_id": TEST_EVIDENCE_ISSUER_ID,
                "source_kind": "repository_file",
                "source_uri": "repo://tests/confidential-self-coder-fixture",
                "source_locator": "synthetic-focused-test-receipt",
                "content_digest": _sha("focused test source"),
                "source_timestamp": NOW - 2.0,
                "received_at": NOW - 1.0,
                "truth_status": "real_observed",
                "generated_values": False,
                **TRUTH_FALSE_FLAGS,
            },
            EVIDENCE_ITEM_PREFIX,
        )
        return _truth_receipt(
            {
                "schema_version": CLAIM_SET_SCHEMA,
                "authority_id": self.authority_id,
                "prompt_digest": request.prompt_digest,
                "answer_digest": request.answer_digest,
                "hnc_receipt_id": request.hnc_receipt_id,
                "source_timestamp": NOW - 2.0,
                "received_at": NOW - 1.0,
                "truth_status": "real_derived",
                "generated_values": False,
                "evidence_receipts": [evidence],
                "claim_findings": [
                    {
                        "claim_id": _sha(request.answer_digest),
                        "failure_kind": "SUPPORTED",
                        "evidence_receipt_ids": [evidence["receipt_id"]],
                    }
                ],
                **TRUTH_FALSE_FLAGS,
            },
            CLAIM_SET_PREFIX,
        )


class _SelfCoderDiagnosticAuthority:
    authority_id = TEST_DIAGNOSTIC_AUTHORITY_ID

    def resolve_diagnostic_signals(
        self,
        request: TruthGateRequest,
        grounding: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        return _truth_receipt(
            {
                "schema_version": DIAGNOSTIC_SIGNAL_SCHEMA,
                "authority_id": self.authority_id,
                "grounding_receipt_id": grounding["receipt_id"],
                "prompt_digest": request.prompt_digest,
                "answer_digest": request.answer_digest,
                "hnc_receipt_id": request.hnc_receipt_id,
                "source_timestamp": NOW - 2.0,
                "received_at": NOW - 1.0,
                "truth_status": "real_derived",
                "generated_values": False,
                "evidence_receipt_ids": list(grounding["evidence_receipt_ids"]),
                "qgita_diagnostics": {"ftcp_count": 0, "state": "stable"},
                "math_angle_diagnostics": {
                    "phase_offset": 0.0,
                    "relation": "aligned",
                },
                **TRUTH_FALSE_FLAGS,
            },
            DIAGNOSTIC_SIGNAL_PREFIX,
        )


def valid_hnc() -> dict[str, Any]:
    memory_id = "hnc:lambda_history:test-memory"
    links = sorted(["provider:test:hnc-a", "provider:test:hnc-b", memory_id])
    payload: dict[str, Any] = {
        "data_status": "live",
        "source": "hnc_live_daemon",
        "source_id": "aureon:hnc:live_daemon",
        "source_timestamp": NOW - 10.0,
        "received_at": NOW - 2.0,
        "ts": NOW - 10.0,
        "receipt_type": "hnc_live_field",
        "provider_receipt_type": "hnc_live_field",
        "truth_status": "real_derived",
        "generated_values": False,
        "input_receipt_ids": links,
        "memory_receipt_id": memory_id,
        "memory_canonical_hash": "1" * 64,
        "memory_previous_receipt_id": None,
        "freshness_status": "fresh",
        "equation_inputs_complete": True,
        "step": 12,
        "lambda_t": 0.31,
        "coherence_gamma": 0.81,
        "consciousness_psi": 0.63,
        "symbolic_life_score": 0.72,
        "consciousness_level": "CONNECTED",
        "source_count": 2,
        **_false_flags(),
    }
    fingerprint = {
        "input_receipt_ids": links,
        "source_timestamp": payload["source_timestamp"],
        "received_at": payload["received_at"],
        "step": payload["step"],
        "lambda_t": payload["lambda_t"],
        "coherence_gamma": payload["coherence_gamma"],
        "consciousness_psi": payload["consciousness_psi"],
        "symbolic_life_score": payload["symbolic_life_score"],
    }
    payload["receipt_id"] = f"hnc:live_field:{_sha(fingerprint)[:24]}"
    return payload


def _source_receipt(
    *,
    source_id: str,
    receipt_id: str,
    receipt_type: str,
    source_timestamp: float,
    received_at: float = NOW - 1.0,
    input_receipt_ids: list[str] | None = None,
    truth_status: str = "real_observed",
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "source_timestamp": source_timestamp,
        "received_at": received_at,
        "receipt_id": receipt_id,
        "receipt_type": receipt_type,
        "truth_status": truth_status,
        "generated_values": False,
        "input_receipt_ids": sorted(input_receipt_ids or []),
        **_false_flags(),
    }


def valid_auris(
    hnc: Mapping[str, Any],
    *,
    gamma: float = 0.90,
    gate_open: bool = True,
) -> dict[str, Any]:
    schumann = _source_receipt(
        source_id="provider.test.schumann",
        receipt_id="schumann:test:receipt-1",
        receipt_type="provider_measurement",
        source_timestamp=NOW - 8.0,
        input_receipt_ids=["provider:test:schumann-raw"],
    )
    sources = {
        "hnc": _source_receipt(
            source_id=str(hnc["source_id"]),
            receipt_id=str(hnc["receipt_id"]),
            receipt_type=str(hnc["receipt_type"]),
            source_timestamp=float(hnc["source_timestamp"]),
            received_at=float(hnc["received_at"]),
            input_receipt_ids=list(hnc["input_receipt_ids"]),
            truth_status=str(hnc["truth_status"]),
        ),
        "space_weather": _source_receipt(
            source_id="provider.test.space-weather",
            receipt_id="space-weather:test:receipt-1",
            receipt_type="provider_measurement",
            source_timestamp=NOW - 9.0,
            input_receipt_ids=["provider:test:space-weather-raw"],
        ),
        "schumann": schumann,
        "earth_blessing": _source_receipt(
            source_id="aureon:test:earth-blessing",
            receipt_id="earth-blessing:test:receipt-1",
            receipt_type="planetary_earth_blessing",
            source_timestamp=NOW - 7.0,
            input_receipt_ids=[schumann["receipt_id"]],
            truth_status="real_derived",
        ),
        "earth_gate": _source_receipt(
            source_id="aureon:test:earth-gate",
            receipt_id="earth-gate:test:receipt-1",
            receipt_type="earth_resonance_gate_evidence",
            source_timestamp=NOW - 6.0,
            input_receipt_ids=[schumann["receipt_id"]],
            truth_status="real_derived",
        ),
    }
    links = sorted(
        {
            *(item["receipt_id"] for item in sources.values()),
            *(link for item in sources.values() for link in item["input_receipt_ids"]),
        }
    )
    payload: dict[str, Any] = {
        "data_status": "live",
        "source_id": "aureon:auris:throne",
        "source_timestamp": NOW - 6.0,
        "received_at": NOW - 1.0,
        "receipt_type": "auris_cosmic_state",
        "provider_receipt_type": "auris_cosmic_state",
        "truth_status": "real_derived",
        "generated_values": False,
        "data_available": True,
        "input_receipt_ids": links,
        "hnc_receipt_id": hnc["receipt_id"],
        "planetary_receipt_ids": sorted(
            item["receipt_id"] for name, item in sources.items() if name != "hnc"
        ),
        "source_receipts": sources,
        "sources_live": sorted(sources),
        "sources_unavailable": [],
        "equation_inputs_complete": True,
        "gate_open": gate_open,
        "advisory": "PROCEED" if gate_open else "HOLD",
        "reasoning": ["complete synthetic linked evidence"],
        "lambda_t": 1.23,
        "coherence_gamma": gamma,
        "consciousness_psi": 0.40,
        "cosmic_score": 0.74,
        "earth_blessing": 0.82,
        **_false_flags(),
    }
    fingerprint = {
        "input_receipt_ids": links,
        "lambda_t": payload["lambda_t"],
        "coherence_gamma": payload["coherence_gamma"],
        "consciousness_psi": payload["consciousness_psi"],
        "cosmic_score": payload["cosmic_score"],
        "earth_blessing": payload["earth_blessing"],
        "gate_open": payload["gate_open"],
        "advisory": payload["advisory"],
    }
    payload["receipt_id"] = f"auris:cosmic_state:{_sha(fingerprint)[:24]}"
    return payload


class TestEvidenceResolver:
    resolver_id = "test:trusted-hnc-auris"
    __test__ = False

    def __init__(
        self,
        *,
        hnc: Mapping[str, Any] | None = None,
        auris: Mapping[str, Any] | None = None,
        gamma: float = 0.90,
        gate_open: bool = True,
    ) -> None:
        self.hnc = copy.deepcopy(hnc or valid_hnc())
        self.auris = copy.deepcopy(auris or valid_auris(self.hnc, gamma=gamma, gate_open=gate_open))
        self.hnc_calls = 0
        self.auris_calls = 0

    def resolve_hnc_evidence(self, request: ThoughtPathRequest) -> Mapping[str, Any] | None:
        del request
        self.hnc_calls += 1
        return copy.deepcopy(self.hnc)

    def resolve_auris_evidence(
        self,
        request: ThoughtPathRequest,
        *,
        answer_digest: str,
        hnc_receipt_id: str,
    ) -> Mapping[str, Any] | None:
        del request, answer_digest, hnc_receipt_id
        self.auris_calls += 1
        return copy.deepcopy(self.auris)


class TestPropagator:
    propagator_id = "test:hive-mycelia"
    __test__ = False

    def __init__(self) -> None:
        self.deliveries: list[dict[str, Any]] = []

    def propagate(
        self,
        *,
        answer: str,
        answer_receipt: Mapping[str, Any],
    ) -> Mapping[str, Mapping[str, Any]]:
        delivery = {"answer": answer, "answer_receipt_id": answer_receipt["receipt_id"]}
        self.deliveries.append(delivery)
        digest = _sha(delivery)
        return {
            channel: build_delivery_ack(
                channel=channel,
                destination_id=f"test:{channel}",
                answer_receipt_id=str(answer_receipt["receipt_id"]),
                delivery_digest=digest,
            )
            for channel in ("hive", "mycelia")
        }


class TestTruthGate:
    gate_id = "test:receipt-backed-truth-gate"
    __test__ = False

    def __init__(self) -> None:
        self.calls = 0

    def evaluate_answer(self, *, prompt, answer, hnc_evidence, correction_attempt):
        self.calls += 1
        request = TruthGateRequest(
            prompt_digest=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            answer_digest=hashlib.sha256(answer.encode("utf-8")).hexdigest(),
            hnc_receipt_id=str(hnc_evidence["receipt_id"]),
            correction_attempt=correction_attempt,
        )
        return _result(
            status="READY_FOR_AURIS",
            reason="grounding_supported_diagnostics_linked",
            request=request,
            grounding_id="grounding:truth:" + "b" * 64,
            diagnostic_id="diagnostic:qgita-math-angle:" + "c" * 64,
            stage="Crown",
            evidence_ids=["evidence:test:one"],
        )


def build_test_thought_path(
    *,
    gamma: float = 0.90,
    gate_open: bool = True,
    hnc: Mapping[str, Any] | None = None,
    auris: Mapping[str, Any] | None = None,
    commitment_only: bool = False,
) -> TruthGatedTenNineOneThoughtPath:
    propagator: Any = TestPropagator()
    if commitment_only:
        traces: dict[str, dict[str, Any]] = {}

        def append_trace(name: str, payload: dict[str, Any]) -> None:
            traces[name] = dict(payload)

        def read_trace(name: str) -> Mapping[str, Any] | None:
            payload = traces.get(name)
            return None if payload is None else dict(payload)

        propagator = CommitmentOnlyHiveMyceliaPropagator(
            bus=ThoughtBus(persist_path=None),
            append_trace_fn=append_trace,
            read_trace_latest_fn=read_trace,
        )
    return TruthGatedTenNineOneThoughtPath(
        resolver=TestEvidenceResolver(
            hnc=hnc,
            auris=auris,
            gamma=gamma,
            gate_open=gate_open,
        ),
        propagator=propagator,
        truth_gate=TestTruthGate(),
        now=lambda: NOW,
    )


def build_confidential_self_coder_test_thought_path() -> TruthGatedTenNineOneThoughtPath:
    """Build the exact production component types with synthetic local receipts."""

    hnc = valid_hnc()
    auris = valid_auris(hnc)
    bus = ThoughtBus(persist_path=None)
    bus.publish(
        Thought(
            source="test:hnc-producer",
            topic="symbolic.life.pulse",
            payload=copy.deepcopy(hnc),
        )
    )
    bus.publish(
        Thought(
            source="test:auris-producer",
            topic="auris.throne.cosmic_state",
            payload=copy.deepcopy(auris),
        )
    )
    authorities = TruthAuthorityBundle(
        claim_authority=_SelfCoderClaimAuthority(),
        diagnostic_authority=_SelfCoderDiagnosticAuthority(),
        allowed_claim_authority_ids=frozenset({TEST_CLAIM_AUTHORITY_ID}),
        allowed_evidence_issuer_ids=frozenset({TEST_EVIDENCE_ISSUER_ID}),
        allowed_diagnostic_authority_ids=frozenset(
            {TEST_DIAGNOSTIC_AUTHORITY_ID}
        ),
    )
    traces: dict[str, dict[str, Any]] = {}

    def append_trace(name: str, payload: dict[str, Any]) -> None:
        traces[name] = dict(payload)

    def read_trace(name: str) -> Mapping[str, Any] | None:
        payload = traces.get(name)
        return None if payload is None else dict(payload)

    return TruthGatedTenNineOneThoughtPath(
        resolver=LocalHncAurisEvidenceResolver(
            bus=bus,
            require_active_pair=True,
            pair_max_age_s=30.0,
            clock=lambda: NOW,
        ),
        propagator=CommitmentOnlyHiveMyceliaPropagator(
            bus=bus,
            append_trace_fn=append_trace,
            read_trace_latest_fn=read_trace,
        ),
        truth_gate=ReceiptBackedTenNineOneTruthGate(
            claim_authority=authorities.claim_authority,
            diagnostic_authority=authorities.diagnostic_authority,
            allowed_claim_authority_ids=authorities.allowed_claim_authority_ids,
            allowed_evidence_issuer_ids=authorities.allowed_evidence_issuer_ids,
            allowed_diagnostic_authority_ids=authorities.allowed_diagnostic_authority_ids,
            max_age_s=30.0,
            now=lambda: NOW,
        ),
        max_age_s=30.0,
        now=lambda: NOW,
    )


__all__ = [
    "NOW",
    "TestEvidenceResolver",
    "TestPropagator",
    "TestTruthGate",
    "build_confidential_self_coder_test_thought_path",
    "build_test_thought_path",
    "valid_auris",
    "valid_hnc",
]
