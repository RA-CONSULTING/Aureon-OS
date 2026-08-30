from __future__ import annotations

import copy
import hashlib
import json

import pytest

from aureon.governance.qgita_kundalini_truth_gate import TruthGateRequest
from aureon.governance.trusted_truth_evidence import (
    CLAIM_SET_PREFIX,
    CLAIM_SET_SCHEMA,
    DIAGNOSTIC_SIGNAL_PREFIX,
    DIAGNOSTIC_SIGNAL_SCHEMA,
    EVIDENCE_ITEM_PREFIX,
    EVIDENCE_ITEM_SCHEMA,
    ReceiptBackedDiagnosticResolver,
    ReceiptBackedGroundingResolver,
    evaluate_receipt_backed_truth_gate,
    validate_claim_evidence_set,
    validate_diagnostic_signal_set,
    validate_evidence_item,
)

NOW = 1_800_000_000.0
PROMPT = hashlib.sha256(b"prompt").hexdigest()
ANSWER = hashlib.sha256(b"answer").hexdigest()
HNC = "hnc:live_field:" + "a" * 24
CLAIM_AUTHORITY = "aureon:test:claim-authority"
EVIDENCE_ISSUER = "aureon:test:evidence-issuer"
DIAGNOSTIC_AUTHORITY = "aureon:test:diagnostic-authority"
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


def _with_receipt(causal, prefix):
    digest = hashlib.sha256(_canonical(causal).encode()).hexdigest()
    return {**causal, "receipt_id": prefix + digest}


def _request(attempt=0):
    return TruthGateRequest(PROMPT, ANSWER, HNC, attempt)


def _evidence(*, issuer=EVIDENCE_ISSUER, locator="line:1"):
    return _with_receipt(
        {
            "schema_version": EVIDENCE_ITEM_SCHEMA,
            "issuer_id": issuer,
            "source_kind": "repository_file",
            "source_uri": "repo://aureon/example.py",
            "source_locator": locator,
            "content_digest": hashlib.sha256(b"verified bytes").hexdigest(),
            "source_timestamp": NOW - 2,
            "received_at": NOW - 1,
            "truth_status": "real_observed",
            "generated_values": False,
            **FALSE_FLAGS,
        },
        EVIDENCE_ITEM_PREFIX,
    )


def _claim_set(kind="SUPPORTED", *, authority=CLAIM_AUTHORITY):
    evidence = _evidence()
    links = [] if kind == "MISSING_GROUNDING" else [evidence["receipt_id"]]
    return _with_receipt(
        {
            "schema_version": CLAIM_SET_SCHEMA,
            "authority_id": authority,
            "prompt_digest": PROMPT,
            "answer_digest": ANSWER,
            "hnc_receipt_id": HNC,
            "source_timestamp": NOW - 2,
            "received_at": NOW - 1,
            "truth_status": "real_derived",
            "generated_values": False,
            "evidence_receipts": [evidence],
            "claim_findings": [
                {
                    "claim_id": hashlib.sha256(b"claim").hexdigest(),
                    "failure_kind": kind,
                    "evidence_receipt_ids": links,
                }
            ],
            **FALSE_FLAGS,
        },
        CLAIM_SET_PREFIX,
    )


def _grounding_id(claim_set):
    evidence_ids = [item["receipt_id"] for item in claim_set["evidence_receipts"]]
    causal = {
        "schema_version": "aureon.qgita_kundalini.grounding.v1",
        "resolver_id": "aureon:truth-grounding-resolver:v1",
        "source_claim_set_receipt_id": claim_set["receipt_id"],
        "prompt_digest": PROMPT,
        "answer_digest": ANSWER,
        "hnc_receipt_id": HNC,
        "source_timestamp": claim_set["source_timestamp"],
        "received_at": claim_set["received_at"],
        "truth_status": "real_derived",
        "generated_values": False,
        "evidence_receipt_ids": evidence_ids,
        "claim_findings": claim_set["claim_findings"],
        **FALSE_FLAGS,
    }
    return "grounding:truth:" + hashlib.sha256(_canonical(causal).encode()).hexdigest()


def _signals(claim_set, *, authority=DIAGNOSTIC_AUTHORITY, grounding_id=None):
    evidence_ids = [item["receipt_id"] for item in claim_set["evidence_receipts"]]
    return _with_receipt(
        {
            "schema_version": DIAGNOSTIC_SIGNAL_SCHEMA,
            "authority_id": authority,
            "grounding_receipt_id": grounding_id or _grounding_id(claim_set),
            "prompt_digest": PROMPT,
            "answer_digest": ANSWER,
            "hnc_receipt_id": HNC,
            "source_timestamp": NOW - 2,
            "received_at": NOW - 1,
            "truth_status": "real_derived",
            "generated_values": False,
            "evidence_receipt_ids": evidence_ids,
            "qgita_diagnostics": {"ftcp_count": 0, "lighthouse_state": "stable"},
            "math_angle_diagnostics": {"phase_offset": 0.0, "relation": "aligned"},
            **FALSE_FLAGS,
        },
        DIAGNOSTIC_SIGNAL_PREFIX,
    )


class ClaimAuthority:
    authority_id = CLAIM_AUTHORITY

    def __init__(self, payload=None):
        self.payload = payload or _claim_set()
        self.calls = 0

    def resolve_claim_evidence(self, request):
        assert request == _request(request.correction_attempt)
        self.calls += 1
        return copy.deepcopy(self.payload)


class DiagnosticAuthority:
    authority_id = DIAGNOSTIC_AUTHORITY

    def __init__(self, claim_set=None, payload=None):
        self.claim_set = claim_set or _claim_set()
        self.payload = payload
        self.calls = 0

    def resolve_diagnostic_signals(self, request, grounding):
        assert request == _request(request.correction_attempt)
        self.calls += 1
        payload = self.payload or _signals(self.claim_set)
        return copy.deepcopy(payload)


def _evaluate(*, kind="SUPPORTED", attempt=0, claim=None, diagnostic=None):
    claim_set = _claim_set(kind)
    claim = claim or ClaimAuthority(claim_set)
    diagnostic = diagnostic or DiagnosticAuthority(claim_set)
    result = evaluate_receipt_backed_truth_gate(
        _request(attempt),
        claim_authority=claim,
        diagnostic_authority=diagnostic,
        allowed_claim_authority_ids=frozenset({CLAIM_AUTHORITY}),
        allowed_evidence_issuer_ids=frozenset({EVIDENCE_ISSUER}),
        allowed_diagnostic_authority_ids=frozenset({DIAGNOSTIC_AUTHORITY}),
        now=NOW,
        max_age_s=30,
    )
    return result, claim, diagnostic


def test_full_receipts_release_only_ready_for_auris():
    result, claim, diagnostic = _evaluate()
    assert result["status"] == "READY_FOR_AURIS"
    assert result["kundalini_stage"] == "Crown"
    assert result["reason"] == "grounding_supported_diagnostics_linked"
    assert claim.calls == diagnostic.calls == 1
    assert all(result[key] is False for key in FALSE_FLAGS)


def test_resolver_receipts_transitively_bind_both_authority_receipts():
    request = _request()
    claim_set = _claim_set()
    claim_authority = ClaimAuthority(claim_set)
    grounding_resolver = ReceiptBackedGroundingResolver(
        authority=claim_authority,
        allowed_authority_ids=frozenset({CLAIM_AUTHORITY}),
        allowed_evidence_issuer_ids=frozenset({EVIDENCE_ISSUER}),
        now=NOW,
        max_age_s=30,
    )
    grounding = grounding_resolver.resolve_grounding(request)
    assert grounding["source_claim_set_receipt_id"] == claim_set["receipt_id"]

    signals = _signals(claim_set, grounding_id=grounding["receipt_id"])
    diagnostic_resolver = ReceiptBackedDiagnosticResolver(
        authority=DiagnosticAuthority(claim_set, signals),
        allowed_authority_ids=frozenset({DIAGNOSTIC_AUTHORITY}),
        now=NOW,
        max_age_s=30,
    )
    diagnostic = diagnostic_resolver.resolve_diagnostics(request, grounding)
    assert diagnostic["source_diagnostic_signal_receipt_id"] == signals["receipt_id"]


@pytest.mark.parametrize(
    ("kind", "stage"),
    [
        ("MISSING_GROUNDING", "Root"),
        ("STALE_OR_LINEAGE", "Sacral"),
        ("UNSUPPORTED", "Solar Plexus"),
        ("CONTRADICTED", "Heart"),
        ("SEMANTIC_MISMATCH", "Throat"),
        ("CROSS_CLAIM_CONFLICT", "Third Eye"),
    ],
)
def test_claim_evidence_not_diagnostic_score_selects_kundalini_stage(kind, stage):
    result, _, diagnostic = _evaluate(kind=kind)
    assert result["status"] == "CORRECTION_REQUIRED"
    assert result["kundalini_stage"] == stage
    assert result["failure_kind"] == kind
    assert diagnostic.calls == 1


def test_two_corrections_end_in_numeric_free_hold():
    result, _, diagnostic = _evaluate(kind="CONTRADICTED", attempt=2)
    assert result["status"] == "HOLD"
    assert result["reason"] == "bounded_correction_exhausted"
    assert result["diagnostic_receipt_id"] == ""
    assert result["correction_directive"] == {}
    assert diagnostic.calls == 1


def test_tampered_full_evidence_body_holds_before_diagnostics():
    claim_set = _claim_set()
    claim_set["evidence_receipts"][0]["source_locator"] = "line:999"
    result, claim, diagnostic = _evaluate(
        claim=ClaimAuthority(claim_set),
        diagnostic=DiagnosticAuthority(claim_set),
    )
    assert result["status"] == "HOLD"
    assert result["reason"] == "trusted_evidence_required"
    assert claim.calls == 1
    assert diagnostic.calls == 0


def test_diagnostic_lineage_drift_holds():
    claim_set = _claim_set()
    drifted = _signals(claim_set, grounding_id="grounding:truth:" + "f" * 64)
    result, _, diagnostic = _evaluate(
        claim=ClaimAuthority(claim_set),
        diagnostic=DiagnosticAuthority(claim_set, drifted),
    )
    assert result["status"] == "HOLD"
    assert result["reason"] == "trusted_evidence_required"
    assert diagnostic.calls == 1


def test_same_authority_object_and_overlapping_id_allowlists_hold_without_calls():
    class BothAuthorities(ClaimAuthority):
        def resolve_diagnostic_signals(self, request, grounding):
            raise AssertionError("must not be called")

    both = BothAuthorities()
    result = evaluate_receipt_backed_truth_gate(
        _request(),
        claim_authority=both,
        diagnostic_authority=both,
        allowed_claim_authority_ids=frozenset({CLAIM_AUTHORITY}),
        allowed_evidence_issuer_ids=frozenset({EVIDENCE_ISSUER}),
        allowed_diagnostic_authority_ids=frozenset({CLAIM_AUTHORITY}),
        now=NOW,
        max_age_s=30,
    )
    assert result["status"] == "HOLD"
    assert result["reason"] == "trusted_evidence_required"
    assert both.calls == 0


def test_non_allowlisted_authority_holds_without_authority_call():
    claim = ClaimAuthority()
    result = evaluate_receipt_backed_truth_gate(
        _request(),
        claim_authority=claim,
        diagnostic_authority=DiagnosticAuthority(),
        allowed_claim_authority_ids=frozenset({"aureon:other"}),
        allowed_evidence_issuer_ids=frozenset({EVIDENCE_ISSUER}),
        allowed_diagnostic_authority_ids=frozenset({DIAGNOSTIC_AUTHORITY}),
        now=NOW,
        max_age_s=30,
    )
    assert result["status"] == "HOLD"
    assert claim.calls == 0


def test_non_allowlisted_evidence_issuer_holds_before_diagnostics():
    claim_set = _claim_set()
    claim_set["evidence_receipts"] = [_evidence(issuer="aureon:untrusted:issuer")]
    claim_set["claim_findings"][0]["evidence_receipt_ids"] = [
        claim_set["evidence_receipts"][0]["receipt_id"]
    ]
    claim_set["receipt_id"] = _with_receipt(
        {key: value for key, value in claim_set.items() if key != "receipt_id"},
        CLAIM_SET_PREFIX,
    )["receipt_id"]
    result, _, diagnostic = _evaluate(
        claim=ClaimAuthority(claim_set),
        diagnostic=DiagnosticAuthority(claim_set),
    )
    assert result["status"] == "HOLD"
    assert diagnostic.calls == 0


def test_source_kind_uri_mismatch_is_rejected():
    item = _evidence()
    item["source_uri"] = "https://example.test/not-a-repo-source"
    item["receipt_id"] = _with_receipt(
        {key: value for key, value in item.items() if key != "receipt_id"},
        EVIDENCE_ITEM_PREFIX,
    )["receipt_id"]
    with pytest.raises(ValueError, match="source_uri_kind_mismatch"):
        validate_evidence_item(item, now=NOW, max_age_s=30)


def test_stale_claim_set_holds_before_diagnostics():
    claim_set = _claim_set()
    claim_set["source_timestamp"] = NOW - 31
    claim_set["receipt_id"] = _with_receipt(
        {key: value for key, value in claim_set.items() if key != "receipt_id"},
        CLAIM_SET_PREFIX,
    )["receipt_id"]
    result, _, diagnostic = _evaluate(
        claim=ClaimAuthority(claim_set),
        diagnostic=DiagnosticAuthority(claim_set),
    )
    assert result["status"] == "HOLD"
    assert diagnostic.calls == 0


def test_exact_positive_freshness_boundary_is_inclusive():
    item = _evidence()
    item["source_timestamp"] = NOW - 30
    item["receipt_id"] = _with_receipt(
        {key: value for key, value in item.items() if key != "receipt_id"},
        EVIDENCE_ITEM_PREFIX,
    )["receipt_id"]
    assert validate_evidence_item(item, now=NOW, max_age_s=30)["receipt_id"] == item["receipt_id"]
    with pytest.raises(ValueError, match="positive_max_age_s_required"):
        validate_evidence_item(item, now=NOW, max_age_s=0)


def test_direct_validators_reject_authority_and_signal_tampering():
    request = _request()
    claim_set = _claim_set()
    validated = validate_claim_evidence_set(claim_set, request, now=NOW, max_age_s=30)
    grounding = {
        "receipt_id": _grounding_id(claim_set),
        "evidence_receipt_ids": [item["receipt_id"] for item in claim_set["evidence_receipts"]],
    }
    signals = _signals(claim_set)
    assert validate_diagnostic_signal_set(
        signals, request, grounding, now=NOW, max_age_s=30
    )["authority_id"] == DIAGNOSTIC_AUTHORITY
    assert validated["authority_id"] == CLAIM_AUTHORITY
    signals["qgita_diagnostics"]["ftcp_count"] = True
    signals["receipt_id"] = _with_receipt(
        {key: value for key, value in signals.items() if key != "receipt_id"},
        DIAGNOSTIC_SIGNAL_PREFIX,
    )["receipt_id"]
    with pytest.raises(ValueError, match="flat_qgita_diagnostics_required"):
        validate_diagnostic_signal_set(signals, request, grounding, now=NOW, max_age_s=30)
