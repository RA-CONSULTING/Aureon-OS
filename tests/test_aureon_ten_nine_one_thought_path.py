from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from aureon.autonomous.aureon_ten_nine_one_thought_path import (
    ACTIVE_COHERENCE_THRESHOLD,
    PHI,
    PHI_INVERSE,
    PHI_SQUARED,
    LocalHncAurisEvidenceResolver,
    TenNineOneHold,
    TenNineOneThoughtPath,
    ThoughtPathRequest,
    validate_ten_nine_one_receipt,
)
from tests.aureon_ten_nine_one_fixtures import (
    NOW,
    TestEvidenceResolver,
    TestPropagator,
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
            ensure_ascii=True,
            allow_nan=False,
        )
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _request(prompt: str = "Repair the bounded parser.") -> ThoughtPathRequest:
    return ThoughtPathRequest(
        subject_type="agent",
        subject_id="Implementation Worker",
        process_id="agent_company_role_cycle:implementation_worker",
        stage="implementation",
        work_kind="coding_decision",
        prompt_digest=_sha(prompt),
        brain_passport_id="brain:" + "a" * 64,
    )


def test_exact_10_9_1_order_releases_one_answer_to_hive_and_mycelia() -> None:
    resolver = TestEvidenceResolver(gamma=0.90)
    propagator = TestPropagator()
    path = TenNineOneThoughtPath(
        resolver=resolver,
        propagator=propagator,
        now=lambda: NOW,
    )
    prompt = "Repair the bounded parser."
    observed_prompts: list[str] = []

    def infer(organized: str) -> str:
        observed_prompts.append(organized)
        return "ACCEPT: apply the minimal parser repair and run its focused test."

    result = path.execute(request=_request(prompt), prompt=prompt, infer=infer)
    receipt = validate_ten_nine_one_receipt(result.receipt)

    assert receipt["stage_order"] == [10, 9, 1]
    assert receipt["vacuum_receipt"]["stage"] == 10
    assert receipt["hnc_receipt"]["stage"] == 9
    assert receipt["answer_receipt"]["stage"] == 1
    assert receipt["hnc_receipt"]["phi"] == PHI
    assert receipt["hnc_receipt"]["phi_inverse"] == PHI_INVERSE
    assert receipt["hnc_receipt"]["phi_squared"] == PHI_SQUARED
    assert receipt["answer_receipt"]["auris_gamma"] == 0.90
    assert receipt["answer_receipt"]["coherence_threshold"] == ACTIVE_COHERENCE_THRESHOLD
    assert receipt["status"] == "coherent_and_propagated"
    assert prompt in observed_prompts[0]
    assert resolver.hnc_calls == 1
    assert resolver.auris_calls == 1
    assert len(propagator.deliveries) == 1
    assert propagator.deliveries[0]["answer"] == result.answer
    assert receipt["hive_ack"]["channel"] == "hive"
    assert receipt["mycelia_ack"]["channel"] == "mycelia"


def test_missing_hnc_holds_before_the_brain_is_called() -> None:
    resolver = TestEvidenceResolver()
    resolver.hnc = {}
    propagator = TestPropagator()
    path = TenNineOneThoughtPath(resolver=resolver, propagator=propagator, now=lambda: NOW)
    inference_calls = 0

    def infer(_organized: str) -> str:
        nonlocal inference_calls
        inference_calls += 1
        return "must not run"

    with pytest.raises(TenNineOneHold, match="stage_9_fresh_canonical_hnc_required"):
        path.execute(request=_request(), prompt="Repair the bounded parser.", infer=infer)

    assert inference_calls == 0
    assert resolver.auris_calls == 0
    assert propagator.deliveries == []


@pytest.mark.parametrize(
    ("gamma", "gate_open", "reason"),
    [
        (0.799999, True, "auris_answer_coherence_below_active_band"),
        (0.90, False, "auris_gate_closed"),
    ],
)
def test_auris_hold_never_propagates(
    gamma: float,
    gate_open: bool,
    reason: str,
) -> None:
    resolver = TestEvidenceResolver(gamma=gamma, gate_open=gate_open)
    propagator = TestPropagator()
    path = TenNineOneThoughtPath(resolver=resolver, propagator=propagator, now=lambda: NOW)

    with pytest.raises(TenNineOneHold, match=reason):
        path.execute(
            request=_request(),
            prompt="Repair the bounded parser.",
            infer=lambda _prompt: "One candidate answer",
        )

    assert resolver.hnc_calls == 1
    assert resolver.auris_calls == 1
    assert propagator.deliveries == []


def test_hnc_auris_lineage_drift_after_inference_holds() -> None:
    hnc = valid_hnc()
    other_hnc = valid_hnc()
    other_hnc["step"] += 1
    fingerprint = {
        "input_receipt_ids": other_hnc["input_receipt_ids"],
        "source_timestamp": other_hnc["source_timestamp"],
        "received_at": other_hnc["received_at"],
        "step": other_hnc["step"],
        "lambda_t": other_hnc["lambda_t"],
        "coherence_gamma": other_hnc["coherence_gamma"],
        "consciousness_psi": other_hnc["consciousness_psi"],
        "symbolic_life_score": other_hnc["symbolic_life_score"],
    }
    other_hnc["receipt_id"] = f"hnc:live_field:{_sha(fingerprint)[:24]}"
    resolver = TestEvidenceResolver(hnc=hnc, auris=valid_auris(other_hnc))
    propagator = TestPropagator()
    path = TenNineOneThoughtPath(resolver=resolver, propagator=propagator, now=lambda: NOW)

    with pytest.raises(TenNineOneHold, match="stage_1_linked_auris_evidence_required"):
        path.execute(
            request=_request(),
            prompt="Repair the bounded parser.",
            infer=lambda _prompt: "One candidate answer",
        )

    assert propagator.deliveries == []


def test_prompt_digest_mismatch_holds_before_hnc_or_inference() -> None:
    resolver = TestEvidenceResolver()
    path = TenNineOneThoughtPath(
        resolver=resolver,
        propagator=TestPropagator(),
        now=lambda: NOW,
    )

    with pytest.raises(TenNineOneHold, match="10_9_1_prompt_digest_mismatch"):
        path.execute(request=_request("one"), prompt="two", infer=lambda _prompt: "answer")

    assert resolver.hnc_calls == 0


def test_rehashed_true_eligibility_alias_is_rejected() -> None:
    path = TenNineOneThoughtPath(
        resolver=TestEvidenceResolver(),
        propagator=TestPropagator(),
        now=lambda: NOW,
    )
    receipt = path.execute(
        request=_request(),
        prompt="Repair the bounded parser.",
        infer=lambda _prompt: "One coherent answer",
    ).receipt
    forged = copy.deepcopy(receipt)
    forged["actionable"] = True
    causal = {key: forged[key] for key in forged if key != "receipt_id"}
    forged["receipt_id"] = f"thought:10-9-1:{_sha(causal)}"

    with pytest.raises(ValueError, match="thought_path_is_evidence_only"):
        validate_ten_nine_one_receipt(forged)


def test_unknown_hashed_field_is_rejected() -> None:
    path = TenNineOneThoughtPath(
        resolver=TestEvidenceResolver(),
        propagator=TestPropagator(),
        now=lambda: NOW,
    )
    receipt = path.execute(
        request=_request(),
        prompt="Repair the bounded parser.",
        infer=lambda _prompt: "One coherent answer",
    ).receipt
    forged = copy.deepcopy(receipt)
    forged["route_authorized"] = True
    causal = {key: forged[key] for key in forged if key != "receipt_id"}
    forged["receipt_id"] = f"thought:10-9-1:{_sha(causal)}"

    with pytest.raises(ValueError, match="10_9_1_receipt_required"):
        validate_ten_nine_one_receipt(forged)


def test_local_resolver_retains_newest_exact_hnc_auris_pair_during_refresh(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class _NoBus:
        def recall(self, _topic: str, *, limit: int = 1):
            del limit
            return []

    state = tmp_path / "state"
    state.mkdir()
    paired_hnc = valid_hnc()
    newer_unpaired_hnc = valid_hnc()
    newer_unpaired_hnc["step"] += 1
    newer_fingerprint = {
        "input_receipt_ids": newer_unpaired_hnc["input_receipt_ids"],
        "source_timestamp": newer_unpaired_hnc["source_timestamp"],
        "received_at": newer_unpaired_hnc["received_at"],
        "step": newer_unpaired_hnc["step"],
        "lambda_t": newer_unpaired_hnc["lambda_t"],
        "coherence_gamma": newer_unpaired_hnc["coherence_gamma"],
        "consciousness_psi": newer_unpaired_hnc["consciousness_psi"],
        "symbolic_life_score": newer_unpaired_hnc["symbolic_life_score"],
    }
    newer_unpaired_hnc["receipt_id"] = (
        f"hnc:live_field:{_sha(newer_fingerprint)[:24]}"
    )
    paired_auris = valid_auris(paired_hnc)
    (state / "hnc_live_trace.jsonl").write_text(
        "\n".join(json.dumps(row) for row in (paired_hnc, newer_unpaired_hnc)) + "\n",
        encoding="utf-8",
    )
    (state / "auris_cosmic_state.jsonl").write_text(
        json.dumps(paired_auris) + "\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("AUREON_HNC_TRACE_PATH", raising=False)
    monkeypatch.delenv("AUREON_BUS_TRACE_DIR", raising=False)
    resolver = LocalHncAurisEvidenceResolver(bus=_NoBus(), root=tmp_path)

    selected_hnc = resolver.resolve_hnc_evidence(_request())
    selected_auris = resolver.resolve_auris_evidence(
        _request(),
        answer_digest="a" * 64,
        hnc_receipt_id=paired_hnc["receipt_id"],
    )

    assert selected_hnc == paired_hnc
    assert selected_auris == paired_auris


def test_local_resolver_waits_for_next_newest_active_pair_without_reusing_old_high(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class _NoBus:
        def recall(self, _topic: str, *, limit: int = 1):
            del limit
            return []

    state = tmp_path / "state"
    state.mkdir()
    low_hnc = valid_hnc()
    high_hnc = valid_hnc()
    high_hnc["step"] += 1
    high_fingerprint = {
        "input_receipt_ids": high_hnc["input_receipt_ids"],
        "source_timestamp": high_hnc["source_timestamp"],
        "received_at": high_hnc["received_at"],
        "step": high_hnc["step"],
        "lambda_t": high_hnc["lambda_t"],
        "coherence_gamma": high_hnc["coherence_gamma"],
        "consciousness_psi": high_hnc["consciousness_psi"],
        "symbolic_life_score": high_hnc["symbolic_life_score"],
    }
    high_hnc["receipt_id"] = f"hnc:live_field:{_sha(high_fingerprint)[:24]}"
    low_auris = valid_auris(low_hnc, gamma=0.79)
    high_auris = valid_auris(high_hnc, gamma=0.90)
    hnc_path = state / "hnc_live_trace.jsonl"
    auris_path = state / "auris_cosmic_state.jsonl"
    hnc_path.write_text(json.dumps(low_hnc) + "\n", encoding="utf-8")
    auris_path.write_text(json.dumps(low_auris) + "\n", encoding="utf-8")
    now = [NOW]

    def release_active_pair(_seconds: float) -> None:
        now[0] += 1.0
        with hnc_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(high_hnc) + "\n")
        with auris_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(high_auris) + "\n")

    monkeypatch.delenv("AUREON_HNC_TRACE_PATH", raising=False)
    monkeypatch.delenv("AUREON_BUS_TRACE_DIR", raising=False)
    resolver = LocalHncAurisEvidenceResolver(
        bus=_NoBus(),
        root=tmp_path,
        require_active_pair=True,
        active_wait_s=5.0,
        pair_max_age_s=300.0,
        pair_min_remaining_s=60.0,
        clock=lambda: now[0],
        sleep=release_active_pair,
    )

    assert resolver.resolve_hnc_evidence(_request()) == high_hnc


def test_thought_path_recaptures_clock_after_resolver_freshness_pacing() -> None:
    current = [NOW - 20.0]
    hnc = valid_hnc()
    auris = valid_auris(hnc, gamma=0.90)

    class _PacedResolver:
        resolver_id = "test:paced-resolver"

        def resolve_hnc_evidence(self, _request):
            current[0] = NOW
            return hnc

        def resolve_auris_evidence(
            self,
            _request,
            *,
            answer_digest: str,
            hnc_receipt_id: str,
        ):
            del answer_digest
            return auris if hnc_receipt_id == hnc["receipt_id"] else None

    path = TenNineOneThoughtPath(
        resolver=_PacedResolver(),
        propagator=TestPropagator(),
        now=lambda: current[0],
    )

    result = path.execute(
        request=_request(),
        prompt="Repair the bounded parser.",
        infer=lambda _prompt: "One coherent answer after the fresh field arrives.",
    )

    assert result.receipt["status"] == "coherent_and_propagated"
