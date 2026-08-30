from __future__ import annotations

import hashlib
import json

import pytest

from aureon.autonomous.aureon_ten_nine_one_thought_path import ThoughtPathRequest
from aureon.autonomous.aureon_truth_gated_ten_nine_one import (
    TruthGatedTenNineOneThoughtPath,
)
from aureon.governance.workforce_auris_node_resolver import (
    bind_truth_gated_workforce_auris_resolver,
    build_truth_gated_coherence_measurement,
)
from aureon.swarm.auris_node_receipts import (
    TRUTH_GATED_COHERENCE_METHOD,
    issue_auris_node_receipt,
    validate_auris_node_receipt,
)
from aureon.swarm.druidic_council import REQUIRED_SEATS
from tests.aureon_ten_nine_one_fixtures import (
    NOW,
    TestEvidenceResolver,
    TestPropagator,
    TestTruthGate,
    valid_auris,
    valid_hnc,
)


def _sha(value) -> str:
    material = (
        value
        if isinstance(value, str)
        else json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _hnc(gamma: float) -> dict:
    payload = valid_hnc()
    payload["coherence_gamma"] = gamma
    fingerprint = {
        "input_receipt_ids": payload["input_receipt_ids"],
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


def _sample(*, agent: str, hnc: dict, answer: str, index: int) -> dict:
    auris = valid_auris(hnc, gamma=0.90)
    path = TruthGatedTenNineOneThoughtPath(
        resolver=TestEvidenceResolver(hnc=hnc, auris=auris),
        propagator=TestPropagator(),
        truth_gate=TestTruthGate(),
        now=lambda: NOW,
    )
    prompt = f"Coherence calibration rung {index} for {agent}."
    request = ThoughtPathRequest(
        subject_type="agent",
        subject_id=agent,
        process_id=f"council-calibration:{agent.casefold().replace(' ', '-')}",
        stage="auris_coherence_probe",
        work_kind="auris_coherence_measurement",
        prompt_digest=_sha(prompt),
        brain_passport_id="brain:" + _sha(agent),
    )
    result = path.execute(request=request, prompt=prompt, infer=lambda _: answer)
    return {
        "answer_text": result.answer,
        "thought_path_receipt": result.receipt,
    }


def _fixture():
    agents = {
        "seer": "Counter Intelligence Validator",
        "sentinel": "Risk Governor",
        "weaver": "CTO Code Architect",
        "keeper": "Chief Memory Vault Officer",
    }
    hnc_rounds = [_hnc(0.81), _hnc(0.85), _hnc(0.90)]
    answers = [
        "x",
        "safe bounded hold",
        "A coherent harmonic answer aligned with truth and evidence.",
    ]
    samples = {
        seat: [
            _sample(agent=agent, hnc=hnc, answer=answer, index=index)
            for index, (hnc, answer) in enumerate(
                zip(hnc_rounds, answers, strict=True),
                start=1,
            )
        ]
        for seat, agent in agents.items()
    }
    current_hnc = hnc_rounds[-1]
    current_auris = valid_auris(current_hnc, gamma=0.90)
    return agents, samples, current_hnc, current_auris


def test_four_truth_gated_nodes_share_exact_current_provider_moment():
    agents, samples, hnc, auris = _fixture()
    resolver = bind_truth_gated_workforce_auris_resolver(
        resolver_id="aureon:workforce-auris-nodes",
        trusted_resolver_ids={"aureon:workforce-auris-nodes"},
        hnc_evidence=hnc,
        auris_evidence=auris,
        seat_agents=agents,
        seat_samples=samples,
        now=NOW,
    )
    nodes = [
        validate_auris_node_receipt(
            issue_auris_node_receipt(seat=seat, resolver=resolver, now=NOW),
            now=NOW,
        )
        for seat in REQUIRED_SEATS
    ]
    assert [node["seat"] for node in nodes] == list(REQUIRED_SEATS)
    assert all(node["measurement_method"] == TRUTH_GATED_COHERENCE_METHOD for node in nodes)
    assert all(node["gamma"] > 0.0 for node in nodes)
    assert len({node["hnc_receipt_id"] for node in nodes}) == 1
    assert len({node["auris_receipt_id"] for node in nodes}) == 1
    assert len({node["provider_moment_digest"] for node in nodes}) == 1


def test_answer_text_tamper_cannot_build_measurement():
    agents, samples, hnc, auris = _fixture()
    sample_window = list(samples["seer"])
    sample_window[0] = {**sample_window[0], "answer_text": "tampered"}
    with pytest.raises(ValueError, match="truth_gated_sample_agent_binding_mismatch"):
        build_truth_gated_coherence_measurement(
            seat="seer",
            agent_id=agents["seer"],
            source_id="aureon:10-9-1:coherence:seer",
            hnc_evidence=hnc,
            auris_evidence=auris,
            samples=sample_window,
            now=NOW,
        )


def test_short_or_negative_window_cannot_drive_a_node():
    agents, samples, hnc, auris = _fixture()
    with pytest.raises(ValueError, match="between_3_and_12"):
        build_truth_gated_coherence_measurement(
            seat="seer",
            agent_id=agents["seer"],
            source_id="aureon:10-9-1:coherence:seer",
            hnc_evidence=hnc,
            auris_evidence=auris,
            samples=samples["seer"][:2],
            now=NOW,
        )


def test_exact_constant_hnc_window_is_silent_not_spuriously_negative():
    agents, _, hnc, auris = _fixture()
    flat_hnc = _hnc(0.85)
    flat_auris = valid_auris(flat_hnc, gamma=0.90)
    samples = {
        seat: [
            _sample(agent=agent, hnc=flat_hnc, answer=answer, index=index)
            for index, answer in enumerate(
                (
                    "A coherent harmonic answer aligned with truth and evidence.",
                    "safe bounded hold",
                    "x",
                ),
                start=1,
            )
        ]
        for seat, agent in agents.items()
    }
    resolver = bind_truth_gated_workforce_auris_resolver(
        resolver_id="aureon:flat-workforce-auris-nodes",
        trusted_resolver_ids={"aureon:flat-workforce-auris-nodes"},
        hnc_evidence=flat_hnc,
        auris_evidence=flat_auris,
        seat_agents=agents,
        seat_samples=samples,
        now=NOW,
    )
    node = validate_auris_node_receipt(
        issue_auris_node_receipt(seat="seer", resolver=resolver, now=NOW),
        now=NOW,
    )
    assert node["data_status"] == "live"
    assert node["gamma"] == 0.0
    negative = [
        _sample(
            agent=agents["seer"],
            hnc=sample_hnc,
            answer=answer,
            index=index,
        )
        for index, (sample_hnc, answer) in enumerate(
            zip(
                [_hnc(0.81), _hnc(0.85), _hnc(0.90)],
                [
                    "A coherent harmonic answer aligned with truth and evidence.",
                    "safe bounded hold",
                    "x",
                ],
                strict=True,
            ),
            start=1,
        )
    ]
    with pytest.raises(ValueError, match="negative_measured_coherence"):
        build_truth_gated_coherence_measurement(
            seat="seer",
            agent_id=agents["seer"],
            source_id="aureon:10-9-1:coherence:seer",
            hnc_evidence=hnc,
            auris_evidence=auris,
            samples=negative,
            now=NOW,
        )
