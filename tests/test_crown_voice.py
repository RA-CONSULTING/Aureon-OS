from __future__ import annotations

import copy
import inspect
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

import aureon.governance.crown_voice as crown_module
from aureon.governance.crown_voice import (
    ResolvedCrownVoiceEvidence,
    issue_crown_voice_receipt,
    validate_crown_voice_receipt,
)
from aureon.governance.dual_key import join_dual_key
from aureon.swarm.auris_node_receipts import ProviderMoment
from aureon.swarm.druidic_council import (
    REQUIRED_SEATS,
    build_seat_receipt,
    convene_druidic_council,
)

NOW = 1_786_473_600.0
PROPOSAL = "a" * 64
PROMPT = "b" * 64
HNC = "hnc:live_field:crown-hnc"
AURIS = "auris:cosmic_state:crown-auris"
PROVIDERS = ("provider:earth:1", "provider:space:1")
PROVIDER_DIGEST = "c" * 64

FALSE_FLAGS = (
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


def _moment(
    *,
    hnc: str = HNC,
    auris: str = AURIS,
    source_timestamp: Any = NOW - 4.0,
    provider_digest: str = PROVIDER_DIGEST,
) -> ProviderMoment:
    return ProviderMoment(
        hnc_receipt_id=hnc,
        auris_receipt_id=auris,
        source_timestamp=source_timestamp,
        provider_receipt_ids=PROVIDERS,
        provider_moment_digest=provider_digest,
    )


class _Resolver:
    def __init__(
        self,
        *,
        verdict: Any = "APPROVED",
        evaluated: Any = True,
        proposal_digest: str = PROPOSAL,
        prompt_digest: str = PROMPT,
        issuer_id: str = "issuer:queen-runtime",
        crown_identity: str = "queen:conscience",
        verdict_source_id: str = "queen:conscience:evaluator",
        moment: ProviderMoment | None = None,
    ) -> None:
        self.verdict = verdict
        self.evaluated = evaluated
        self.proposal_digest = proposal_digest
        self.prompt_digest = prompt_digest
        self.issuer_id = issuer_id
        self.crown_identity = crown_identity
        self.verdict_source_id = verdict_source_id
        self.moment = moment or _moment()
        self.calls: list[tuple[str, str]] = []

    def resolve_crown_voice_evidence(
        self,
        proposal_digest: str,
        prompt_digest: str,
    ) -> ResolvedCrownVoiceEvidence:
        self.calls.append((proposal_digest, prompt_digest))
        return ResolvedCrownVoiceEvidence(
            resolver_id="resolver:trusted-crown-runtime:v1",
            issuer_id=self.issuer_id,
            crown_identity=self.crown_identity,
            verdict_source_id=self.verdict_source_id,
            queen_verdict=self.verdict,
            queen_evaluated=self.evaluated,
            reason="QueenConscience evaluated purpose, ethics, and authority",
            proposal_digest=self.proposal_digest,
            prompt_digest=self.prompt_digest,
            hnc_evidence={"resolved_moment": self.moment},
            auris_evidence={"resolved_moment": self.moment},
        )


class _MissingResolver:
    def resolve_crown_voice_evidence(
        self,
        proposal_digest: str,
        prompt_digest: str,
    ) -> None:
        return None


class _ErrorResolver:
    def resolve_crown_voice_evidence(
        self,
        proposal_digest: str,
        prompt_digest: str,
    ) -> ResolvedCrownVoiceEvidence:
        raise RuntimeError("queen runtime unavailable")


@pytest.fixture(autouse=True)
def _trusted_provider_moment(monkeypatch: pytest.MonkeyPatch) -> None:
    def validate(
        hnc_evidence: Mapping[str, Any],
        auris_evidence: Mapping[str, Any],
        *,
        now: float,
        max_age_s: float,
    ) -> ProviderMoment:
        assert hnc_evidence["resolved_moment"] is auris_evidence["resolved_moment"]
        assert now == NOW or now == NOW + 17.0
        assert max_age_s == 300.0
        return hnc_evidence["resolved_moment"]

    monkeypatch.setattr(crown_module, "validate_provider_moment", validate)


def _issue(resolver: Any | None = None, *, now: Any = NOW) -> dict[str, Any]:
    return issue_crown_voice_receipt(
        proposal_digest=PROPOSAL,
        prompt_digest=PROMPT,
        resolver=_Resolver() if resolver is None else resolver,
        now=now,
    )


def _assert_numeric_free(value: Any) -> None:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return
    if isinstance(value, Mapping):
        for nested in value.values():
            _assert_numeric_free(nested)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for nested in value:
            _assert_numeric_free(nested)
        return
    assert not isinstance(value, (int, float)), value


def _council() -> dict[str, Any]:
    seats = [
        build_seat_receipt(
            seat=seat,
            agent_id=f"agent-{seat}",
            decision="ACCEPT",
            reason=f"{seat} complete",
            gamma=0.90,
            proposal_digest=PROPOSAL,
            prompt_digest=PROMPT,
            hnc_receipt_id=HNC,
            auris_receipt_id=AURIS,
            auris_node_receipt_id=f"auris:node:{seat}:receipt",
            source_timestamp=NOW - 4.0,
            derived_at=NOW,
        )
        for seat in REQUIRED_SEATS
    ]
    return convene_druidic_council(
        proposal_digest=PROPOSAL,
        prompt_digest=PROMPT,
        hnc_receipt_id=HNC,
        auris_receipt_id=AURIS,
        seat_receipts=seats,
        now=NOW,
    )


def test_public_issuer_cannot_accept_identity_verdict_ids_or_timestamps() -> None:
    parameters = inspect.signature(issue_crown_voice_receipt).parameters

    assert set(parameters) == {
        "proposal_digest",
        "prompt_digest",
        "resolver",
        "now",
        "max_age_s",
    }
    assert not {
        "issuer_id",
        "crown_identity",
        "queen_verdict",
        "receipt_id",
        "source_timestamp",
        "provider_moment_digest",
    }.intersection(parameters)


@pytest.mark.parametrize(
    ("verdict", "decision"),
    [
        ("APPROVED", "APPROVE"),
        ("VETO", "ABORT"),
        ("CONCERNED", "HOLD"),
        ("TEACHING_MOMENT", "HOLD"),
    ],
)
def test_explicit_queen_verdict_maps_to_crown_peer_voice(
    verdict: str,
    decision: str,
) -> None:
    resolver = _Resolver(verdict=verdict)

    receipt = _issue(resolver)

    assert resolver.calls == [(PROPOSAL, PROMPT)]
    assert receipt["decision"] == decision
    assert receipt["queen_verdict"] == verdict
    assert receipt["queen_evaluated"] is True
    assert receipt["hnc_receipt_id"] == HNC
    assert receipt["auris_receipt_id"] == AURIS
    assert receipt["provider_receipt_ids"] == list(PROVIDERS)
    assert receipt["provider_moment_digest"] == PROVIDER_DIGEST
    assert receipt["source_timestamp"] == NOW - 4.0
    assert receipt["verdict_evidence_id"].startswith("queen:verdict:")
    assert receipt["receipt_id"].startswith("queen:governance:")
    assert all(receipt[name] is False for name in FALSE_FLAGS)
    assert validate_crown_voice_receipt(receipt, now=NOW) == receipt


def test_causal_identity_excludes_local_derived_clock() -> None:
    first = _issue(now=NOW)
    second = _issue(now=NOW + 17.0)

    assert first["receipt_id"] == second["receipt_id"]
    assert first["verdict_evidence_id"] == second["verdict_evidence_id"]
    assert first["derived_at"] != second["derived_at"]


@pytest.mark.parametrize(
    "resolver",
    [
        _MissingResolver(),
        _ErrorResolver(),
        _Resolver(verdict="UNKNOWN"),
        _Resolver(verdict=""),
        _Resolver(evaluated=False),
        _Resolver(evaluated=1),
        _Resolver(proposal_digest="d" * 64),
        _Resolver(prompt_digest="e" * 64),
        _Resolver(moment=_moment(source_timestamp=NOW - 400.0)),
        _Resolver(moment=_moment(source_timestamp=True)),
        _Resolver(moment=_moment(hnc="hnc:self-attested")),
        _Resolver(moment=_moment(auris="auris:self-attested")),
        _Resolver(moment=_moment(provider_digest="not-a-digest")),
    ],
)
def test_missing_error_unknown_stale_or_wrong_link_is_numeric_free_no_data(
    resolver: Any,
) -> None:
    receipt = _issue(resolver)

    assert receipt["decision"] == "HOLD"
    assert receipt["data_status"] == "no_data"
    assert receipt["receipt_id"] is None
    assert receipt["input_receipt_ids"] == []
    assert all(receipt[name] is False for name in FALSE_FLAGS)
    _assert_numeric_free(receipt)
    assert validate_crown_voice_receipt(receipt, now=NOW) == receipt


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_timestamp", True),
        ("derived_at", True),
        ("queen_evaluated", 1),
        ("decision", "ABORT"),
        ("actionable", True),
        ("provider_moment_digest", "f" * 64),
        ("issuer_id", "agent-seer"),
    ],
)
def test_strict_validator_rejects_bool_tampering_or_wrong_link(
    field: str,
    value: Any,
) -> None:
    receipt = copy.deepcopy(_issue())
    receipt[field] = value

    with pytest.raises(ValueError):
        validate_crown_voice_receipt(receipt, now=NOW)


def test_strict_validator_rejects_extra_fields_and_staleness() -> None:
    receipt = _issue()

    with pytest.raises(ValueError, match="exact_live_crown_schema_required"):
        validate_crown_voice_receipt(
            {**receipt, "custom_eligible": False},
            now=NOW,
        )
    with pytest.raises(ValueError, match="fresh_crown_source_timestamp_required"):
        validate_crown_voice_receipt(receipt, now=NOW + 400.0)


def test_independent_crown_and_council_form_two_rune_harmonic() -> None:
    joined = join_dual_key(_council(), _issue(), now=NOW)

    assert joined["decision"] == "ACCEPT"
    assert joined["rune_voices"] == ["druid_council", "queen_chief"]
    assert joined["voices_present"] == 2
    assert joined["economic_mutation"] is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("issuer_id", "AGENT-SEER"),
        ("crown_identity", "agent-sentinel"),
        ("verdict_source_id", "agent-keeper"),
    ],
)
def test_same_identity_cannot_speak_as_council_and_crown(
    field: str,
    value: str,
) -> None:
    kwargs = {field: value}
    crown = _issue(_Resolver(**kwargs))

    joined = join_dual_key(_council(), crown, now=NOW)

    assert joined["decision"] == "HOLD"
    assert joined["data_status"] == "no_data"
    assert joined["receipt_id"] is None
    _assert_numeric_free(joined)


@pytest.mark.parametrize(
    "moment",
    [
        _moment(hnc="hnc:live_field:other"),
        _moment(auris="auris:cosmic_state:other"),
        _moment(source_timestamp=NOW - 3.0),
    ],
)
def test_wrong_hnc_auris_or_provider_timestamp_cannot_join_council(
    moment: ProviderMoment,
) -> None:
    crown = _issue(_Resolver(moment=moment))

    joined = join_dual_key(_council(), crown, now=NOW)

    assert joined["decision"] == "HOLD"
    assert joined["data_status"] == "no_data"
    assert joined["receipt_id"] is None


def test_no_data_validator_rejects_extra_fields() -> None:
    receipt = _issue(_MissingResolver())

    with pytest.raises(ValueError, match="exact_no_data_crown_schema_required"):
        validate_crown_voice_receipt(
            {**receipt, "source_timestamp": NOW},
            now=NOW,
        )
