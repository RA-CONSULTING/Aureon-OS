from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from aureon.autonomous.aureon_cloud_brain_composition import (
    TruthAuthorityBundle,
    build_local_confidential_self_coder_thought_path,
    build_truth_gated_cloud_thought_path,
)
from aureon.autonomous.aureon_ten_nine_one_thought_path import (
    TenNineOneHold,
    ThoughtPathRequest,
)
from aureon.core.aureon_thought_bus import Thought, ThoughtBus
from aureon.governance.trusted_truth_evidence import (
    CLAIM_SET_PREFIX,
    CLAIM_SET_SCHEMA,
    DIAGNOSTIC_SIGNAL_PREFIX,
    DIAGNOSTIC_SIGNAL_SCHEMA,
    EVIDENCE_ITEM_PREFIX,
    EVIDENCE_ITEM_SCHEMA,
)
from tests.aureon_ten_nine_one_fixtures import (
    NOW,
    TestEvidenceResolver,
    TestPropagator,
    valid_auris,
    valid_hnc,
)

CLAIM_AUTHORITY = "aureon:test:cloud-claim-authority"
EVIDENCE_ISSUER = "aureon:test:repository-evidence-issuer"
DIAGNOSTIC_AUTHORITY = "aureon:test:qgita-diagnostic-authority"
FALSE_FLAGS = {
    "action_eligible": False,
    "accounting_eligible": False,
    "learning_eligible": False,
    "action_gate_passed": False,
    "actionable": False,
    "operational_eligible": False,
    "provider_eligible": False,
    "eligible_for_action": False,
    "eligible_for_accounting": False,
    "eligible_for_learning": False,
    "economic_mutation": False,
}


def _canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _receipt(causal, prefix):
    return {
        **causal,
        "receipt_id": prefix + hashlib.sha256(_canonical(causal).encode()).hexdigest(),
    }


class ClaimAuthority:
    authority_id = CLAIM_AUTHORITY

    def __init__(self, *, malformed: bool = False) -> None:
        self.malformed = malformed
        self.calls = 0

    def resolve_claim_evidence(self, request):
        self.calls += 1
        if self.malformed:
            return {"status": "self_attested"}
        evidence = _receipt(
            {
                "schema_version": EVIDENCE_ITEM_SCHEMA,
                "issuer_id": EVIDENCE_ISSUER,
                "source_kind": "repository_file",
                "source_uri": "repo://aureon/verified_source.py",
                "source_locator": "sha256:full-file",
                "content_digest": hashlib.sha256(b"verified source bytes").hexdigest(),
                "source_timestamp": NOW - 2,
                "received_at": NOW - 1,
                "truth_status": "real_observed",
                "generated_values": False,
                **FALSE_FLAGS,
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
                "source_timestamp": NOW - 2,
                "received_at": NOW - 1,
                "truth_status": "real_derived",
                "generated_values": False,
                "evidence_receipts": [evidence],
                "claim_findings": [
                    {
                        "claim_id": hashlib.sha256(request.answer_digest.encode()).hexdigest(),
                        "failure_kind": "SUPPORTED",
                        "evidence_receipt_ids": [evidence["receipt_id"]],
                    }
                ],
                **FALSE_FLAGS,
            },
            CLAIM_SET_PREFIX,
        )


class DiagnosticAuthority:
    authority_id = DIAGNOSTIC_AUTHORITY

    def __init__(self) -> None:
        self.calls = 0

    def resolve_diagnostic_signals(self, request, grounding):
        self.calls += 1
        return _receipt(
            {
                "schema_version": DIAGNOSTIC_SIGNAL_SCHEMA,
                "authority_id": self.authority_id,
                "grounding_receipt_id": grounding["receipt_id"],
                "prompt_digest": request.prompt_digest,
                "answer_digest": request.answer_digest,
                "hnc_receipt_id": request.hnc_receipt_id,
                "source_timestamp": NOW - 2,
                "received_at": NOW - 1,
                "truth_status": "real_derived",
                "generated_values": False,
                "evidence_receipt_ids": grounding["evidence_receipt_ids"],
                "qgita_diagnostics": {"ftcp_count": 0, "state": "stable"},
                "math_angle_diagnostics": {"phase_offset": 0.0, "relation": "aligned"},
                **FALSE_FLAGS,
            },
            DIAGNOSTIC_SIGNAL_PREFIX,
        )


def _bundle(*, malformed: bool = False) -> TruthAuthorityBundle:
    return TruthAuthorityBundle(
        claim_authority=ClaimAuthority(malformed=malformed),
        diagnostic_authority=DiagnosticAuthority(),
        allowed_claim_authority_ids=frozenset({CLAIM_AUTHORITY}),
        allowed_evidence_issuer_ids=frozenset({EVIDENCE_ISSUER}),
        allowed_diagnostic_authority_ids=frozenset({DIAGNOSTIC_AUTHORITY}),
    )


def _request(prompt: str) -> ThoughtPathRequest:
    return ThoughtPathRequest(
        subject_type="agent",
        subject_id="Implementation Worker",
        process_id="build_execution",
        stage="implementation",
        work_kind="coding_decision",
        prompt_digest=hashlib.sha256(prompt.encode()).hexdigest(),
        brain_passport_id="brain:" + "a" * 64,
    )


def test_composition_releases_only_full_grounding_then_auris_and_hive() -> None:
    prompt = "Repair only the receipt-bound source."
    resolver = TestEvidenceResolver()
    propagator = TestPropagator()
    authorities = _bundle()
    path = build_truth_gated_cloud_thought_path(
        authorities,
        evidence_resolver=resolver,
        propagator=propagator,
        max_age_s=30,
        now=lambda: NOW,
    )

    result = path.execute(
        request=_request(prompt),
        prompt=prompt,
        infer=lambda _organized: "Use the verified source receipt and run its focused test.",
    )

    assert result.receipt["truth_gate_receipt"]["status"] == "READY_FOR_AURIS"
    assert result.receipt["receipt_id"].startswith("thought:10-9-1:truth-gated:")
    assert resolver.hnc_calls == resolver.auris_calls == 1
    assert len(propagator.deliveries) == 1
    assert authorities.claim_authority.calls == 1
    assert authorities.diagnostic_authority.calls == 1
    assert path.receipts[0]["receipt_id"] == result.receipt["receipt_id"]


def test_malformed_claim_authority_holds_before_auris_or_hive() -> None:
    resolver = TestEvidenceResolver()
    propagator = TestPropagator()
    path = build_truth_gated_cloud_thought_path(
        _bundle(malformed=True),
        evidence_resolver=resolver,
        propagator=propagator,
        max_age_s=30,
        now=lambda: NOW,
    )

    with pytest.raises(TenNineOneHold, match="truth_gate_hold:trusted_evidence_required"):
        path.execute(
            request=_request("Do not trust the cloud answer."),
            prompt="Do not trust the cloud answer.",
            infer=lambda _organized: "I certify myself.",
        )

    assert resolver.hnc_calls == 1
    assert resolver.auris_calls == 0
    assert propagator.deliveries == []
    assert path.receipts == ()


def test_authority_identities_must_be_allowlisted_and_disjoint() -> None:
    claim = ClaimAuthority()
    diagnostic = DiagnosticAuthority()
    with pytest.raises(ValueError, match="disjoint_truth_authority_identities_required"):
        TruthAuthorityBundle(
            claim_authority=claim,
            diagnostic_authority=diagnostic,
            allowed_claim_authority_ids=frozenset({CLAIM_AUTHORITY}),
            allowed_evidence_issuer_ids=frozenset({CLAIM_AUTHORITY}),
            allowed_diagnostic_authority_ids=frozenset({DIAGNOSTIC_AUTHORITY}),
        )
    with pytest.raises(ValueError, match="allowlisted_claim_authority_required"):
        TruthAuthorityBundle(
            claim_authority=claim,
            diagnostic_authority=diagnostic,
            allowed_claim_authority_ids=frozenset({"aureon:test:other-claim"}),
            allowed_evidence_issuer_ids=frozenset({EVIDENCE_ISSUER}),
            allowed_diagnostic_authority_ids=frozenset({DIAGNOSTIC_AUTHORITY}),
        )


def test_confidential_self_coder_factory_requires_explicit_authorities() -> None:
    with pytest.raises(
        ValueError,
        match="authenticated_self_coder_truth_authority_bundle_required",
    ):
        build_local_confidential_self_coder_thought_path()


def test_confidential_self_coder_factory_persists_only_commitments(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trace_dir = tmp_path / "traces"
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(trace_dir))
    bus = ThoughtBus(persist_path=str(tmp_path / "thoughts.jsonl"))
    hnc = valid_hnc()
    bus.publish(
        Thought(
            source="test:hnc-producer",
            topic="symbolic.life.pulse",
            payload=hnc,
        )
    )
    bus.publish(
        Thought(
            source="test:auris-producer",
            topic="auris.throne.cosmic_state",
            payload=valid_auris(hnc),
        )
    )
    path = build_local_confidential_self_coder_thought_path(
        _bundle(),
        bus=bus,
        max_age_s=30,
        now=lambda: NOW,
    )
    preflight = path.self_coder_confidential_preflight()
    assert preflight == {
        "schema_version": "aureon-self-coder-thought-path-preflight-v2",
        "ready": True,
        "truth_gate_enforced": True,
        "trusted_local_evidence_resolver": True,
        "trusted_receipt_backed_truth_gate": True,
        "commitment_only_propagation": True,
        "raw_answer_bus_persistence_authorized": False,
        "raw_answer_trace_persistence_authorized": False,
        "action_eligible": False,
        "economic_eligible": False,
    }
    private_answer = "PRIVATE_SELF_CODER_DIFF_SENTINEL_4fb53e"
    result = path.execute(
        request=_request("Repair only the locally grounded target."),
        prompt="Repair only the locally grounded target.",
        infer=lambda _organized: private_answer,
    )

    persisted = "\n".join(
        item.read_text(encoding="utf-8")
        for item in tmp_path.rglob("*")
        if item.is_file()
    )
    assert private_answer not in persisted
    assert hashlib.sha256(private_answer.encode()).hexdigest() in persisted
    assert result.answer == private_answer
