from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import asdict, replace
from decimal import Decimal

import pytest

from aureon.autonomous.aureon_internal_coding_workforce import (
    INTERNAL_ACTOR,
    WORK_SCHEMA_VERSION,
    WorkReceipt,
)
from aureon.autonomous.aureon_ten_nine_one_thought_path import ThoughtPathRequest
from aureon.autonomous.aureon_truth_gated_ten_nine_one import (
    TruthGatedTenNineOneThoughtPath,
)
from aureon.core.organism_composition import load_latest_calibration_status
from aureon.governance.cognition_gate import CognitionGovernanceRequest
from aureon.governance.hnc_auris_acquisition import (
    bind_hnc_auris_governance_acquisition_supplier,
)
from aureon.governance.live_workforce_calibration import (
    DEFAULT_CALIBRATION_PROMPTS,
    WorkforceCalibrationHold,
    bind_pinned_provider_moment_resolver,
    collect_live_workforce_auris_calibration,
    validate_workforce_auris_calibration_report,
)
from aureon.governance.material_truth_gate import extract_allowed_responses
from aureon.governance.runtime_voice_suppliers import TrustedAurisNodeResolverFactory
from aureon.governance.workforce_auris_resolver_factory import (
    bind_calibrated_workforce_auris_resolver_factory,
)
from aureon.governance.workforce_druid_resolver import DEFAULT_WORKFORCE_DRUID_ROLES
from aureon.inhouse_ai.llm_adapter import AureonLocalAdapter
from aureon.swarm.auris_node_receipts import (
    issue_auris_node_receipt,
    validate_provider_moment,
)
from aureon.swarm.druidic_council import ACTIVE_THRESHOLD, REQUIRED_SEATS
from tests.aureon_ten_nine_one_fixtures import (
    NOW,
    TestPropagator,
    TestTruthGate,
    valid_auris,
    valid_hnc,
)


def _canonical(value) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _sha(value) -> str:
    material = value if isinstance(value, str) else _canonical(value)
    return hashlib.sha256(material.encode()).hexdigest()


def _pair(index: int, gamma: float):
    hnc = valid_hnc()
    hnc["coherence_gamma"] = gamma
    hnc["input_receipt_ids"] = sorted(
        {
            *hnc["input_receipt_ids"],
            f"provider:market:{index}",
            f"provider:account:{index}",
        }
    )
    hnc["source_count"] = len(hnc["input_receipt_ids"]) - 1
    fingerprint = {
        "input_receipt_ids": hnc["input_receipt_ids"],
        "source_timestamp": hnc["source_timestamp"],
        "received_at": hnc["received_at"],
        "step": hnc["step"],
        "lambda_t": hnc["lambda_t"],
        "coherence_gamma": hnc["coherence_gamma"],
        "consciousness_psi": hnc["consciousness_psi"],
        "symbolic_life_score": hnc["symbolic_life_score"],
    }
    hnc["receipt_id"] = f"hnc:live_field:{_sha(fingerprint)[:24]}"
    auris = valid_auris(hnc, gamma=0.90)
    return hnc, auris


class _Workforce:
    def __init__(self, resolver) -> None:
        self.resolver = resolver
        self.receipts = []
        self._thought_receipts = []
        self.calls = []

    @property
    def thought_path_receipts(self):
        return tuple(self._thought_receipts)

    def process_id_for_role(self, role: str) -> str:
        return f"agent_company_role_cycle:{role.lower().replace(' ', '_')}"

    def decide(self, **kwargs):
        prompt = kwargs["prompt"]
        round_index = DEFAULT_CALIBRATION_PROMPTS.index(prompt)
        answer = extract_allowed_responses(prompt)[(0, 0, 2)[round_index]]
        request = ThoughtPathRequest(
            subject_type=kwargs["subject_type"],
            subject_id=kwargs["subject_id"],
            process_id=kwargs["process_id"],
            stage=kwargs["stage"],
            work_kind=kwargs["work_kind"],
            prompt_digest=_sha(prompt),
            brain_passport_id="brain:" + _sha(kwargs["subject_id"]),
        )
        path = TruthGatedTenNineOneThoughtPath(
            resolver=self.resolver,
            propagator=TestPropagator(),
            truth_gate=TestTruthGate(),
            now=lambda: NOW,
        )
        thought = path.execute(
            request=request,
            prompt=prompt,
            infer=lambda _: answer,
        )
        self._thought_receipts.append(thought.receipt)
        work = WorkReceipt(
            schema_version=WORK_SCHEMA_VERSION,
            sequence=len(self.receipts) + 1,
            actor_class=INTERNAL_ACTOR,
            actor_id=f"aureon:agent:{kwargs['subject_id']}",
            process_id=kwargs["process_id"],
            stage=kwargs["stage"],
            work_kind=kwargs["work_kind"],
            input_digest=_sha(prompt),
            output_digest=_sha(answer),
            brain_passport_id=request.brain_passport_id,
            completed_at=NOW,
            action_eligible=False,
            economic_eligible=False,
            receipt_id="",
            thought_path_receipt_id=thought.receipt["receipt_id"],
        )
        causal = asdict(work)
        causal.pop("receipt_id")
        work = replace(work, receipt_id=f"work:{_sha(causal)}")
        self.receipts.append(work)
        self.calls.append(
            {
                "round": round_index + 1,
                "role": kwargs["subject_id"],
                "hnc_receipt_id": thought.receipt["inner_receipt"]["hnc_receipt"][
                    "hnc_receipt_id"
                ],
            }
        )
        return answer, work


def _resolver():
    return bind_pinned_provider_moment_resolver(
        resolver_id="aureon:pinned-calibration-provider-moment",
        trusted_resolver_ids={"aureon:pinned-calibration-provider-moment"},
        clock=lambda: NOW,
    )


def _successful_calibration(gammas=(0.81, 0.85, 0.90)):
    resolver = _resolver()
    workforce = _Workforce(resolver)
    pairs = tuple(_pair(index, gamma) for index, gamma in enumerate(gammas, start=1))
    pair_iterator = iter(pairs)
    calibration = collect_live_workforce_auris_calibration(
        workforce=workforce,
        evidence_resolver=resolver,
        auris_resolver_id="aureon:workforce-auris-nodes",
        trusted_auris_resolver_ids={"aureon:workforce-auris-nodes"},
        pair_loader=lambda: next(pair_iterator),
        clock=lambda: NOW,
        sleep=lambda _value: None,
    )
    return calibration, pairs[-1]


def _timestamp_text(value: float) -> str:
    result = format(Decimal(str(value)), "f")
    if "." in result:
        result = result.rstrip("0").rstrip(".")
    return "0" if Decimal(result) == 0 else result


def _governance_request(pair) -> CognitionGovernanceRequest:
    moment = validate_provider_moment(*pair, now=NOW)
    timestamp = _timestamp_text(moment.source_timestamp)
    return CognitionGovernanceRequest(
        schema="aureon.cognition-governance-request.v1",
        prompt_digest="b" * 64,
        proposal_digest="a" * 64,
        proposal_json="{}",
        provider_receipt_ids=moment.provider_receipt_ids,
        provider_moment_digest=moment.provider_moment_digest,
        provider_source_timestamp=timestamp,
        target_provider_receipt_ids=moment.provider_receipt_ids,
        target_provider_moment_digest=moment.provider_moment_digest,
        target_provider_source_timestamp=timestamp,
        queen_verdict="APPROVED",
    )


def test_three_distinct_rounds_pin_all_four_seats_and_issue_nodes():
    resolver = _resolver()
    workforce = _Workforce(resolver)
    pairs = iter((_pair(1, 0.81), _pair(2, 0.85), _pair(3, 0.90)))
    calibration = collect_live_workforce_auris_calibration(
        workforce=workforce,
        evidence_resolver=resolver,
        auris_resolver_id="aureon:workforce-auris-nodes",
        trusted_auris_resolver_ids={"aureon:workforce-auris-nodes"},
        pair_loader=lambda: next(pairs),
        clock=lambda: NOW,
        sleep=lambda _value: None,
    )

    assert calibration.report["round_count"] == 3
    assert calibration.report["sample_count"] == 12
    assert len(set(calibration.report["provider_moment_digests"])) == 3
    assert all(len(calibration.seat_samples[seat]) == 3 for seat in REQUIRED_SEATS)
    assert len(workforce.calls) == 12
    for round_number in (1, 2, 3):
        calls = [item for item in workforce.calls if item["round"] == round_number]
        assert len(calls) == 4
        assert len({item["hnc_receipt_id"] for item in calls}) == 1
    nodes = [
        issue_auris_node_receipt(
            seat=seat,
            resolver=calibration.node_resolver,
            now=NOW,
        )
        for seat in REQUIRED_SEATS
    ]
    assert all(node["data_status"] == "live" for node in nodes)
    assert all(node["gamma"] > 0.0 for node in nodes)
    assert [node["agent_id"] for node in nodes] == [
        DEFAULT_WORKFORCE_DRUID_ROLES[seat] for seat in REQUIRED_SEATS
    ]


def test_complete_report_persists_and_validates_full_four_seat_windows():
    calibration, _pair_value = _successful_calibration()

    validated = validate_workforce_auris_calibration_report(
        calibration.report,
        now=NOW,
    )

    assert validated["seat_samples"] == {
        seat: list(calibration.seat_samples[seat]) for seat in REQUIRED_SEATS
    }
    assert validated["sample_count"] == 12
    assert validated["action_eligible"] is False
    assert validated["economic_mutation"] is False


def test_rehashed_calibration_with_tampered_answer_still_fails_lineage():
    calibration, _pair_value = _successful_calibration()
    tampered = deepcopy(calibration.report)
    tampered["seat_samples"][REQUIRED_SEATS[0]][0]["answer_text"] = "ACCEPT forged"
    causal = {
        key: value
        for key, value in tampered.items()
        if key not in {"receipt_id", "derived_at"}
    }
    tampered["receipt_id"] = f"aureon:workforce-auris-calibration:{_sha(causal)}"

    with pytest.raises(ValueError, match="calibration_sample_lineage_mismatch"):
        validate_workforce_auris_calibration_report(tampered, now=NOW)


def test_factory_rebuilds_nodes_only_for_exact_calibrated_provider_moment():
    calibration, pair = _successful_calibration()
    factory = bind_calibrated_workforce_auris_resolver_factory(
        factory_id="aureon:workforce-auris-nodes",
        trusted_resolver_ids={"aureon:workforce-auris-nodes"},
        calibration_report=calibration.report,
        pair_loader=lambda _request: pair,
        clock=lambda: NOW,
    )

    assert isinstance(factory, TrustedAurisNodeResolverFactory)
    resolver = factory.build_auris_node_resolver(_governance_request(pair))
    nodes = [
        issue_auris_node_receipt(seat=seat, resolver=resolver, now=NOW)
        for seat in REQUIRED_SEATS
    ]
    assert all(node["data_status"] == "live" for node in nodes)
    assert all(node["resolver_id"] == factory.factory_id for node in nodes)


def test_factory_rejects_request_or_live_pair_outside_calibrated_moment():
    calibration, pair = _successful_calibration()
    factory = bind_calibrated_workforce_auris_resolver_factory(
        factory_id="aureon:workforce-auris-nodes",
        trusted_resolver_ids={"aureon:workforce-auris-nodes"},
        calibration_report=calibration.report,
        pair_loader=lambda _request: pair,
        clock=lambda: NOW,
    )
    wrong_request = replace(
        _governance_request(pair),
        provider_moment_digest="f" * 64,
    )
    with pytest.raises(
        ValueError,
        match="request_provider_moment_must_match_calibration",
    ):
        factory.build_auris_node_resolver(wrong_request)

    newer_pair = _pair(4, 0.93)
    newer_factory = bind_calibrated_workforce_auris_resolver_factory(
        factory_id="aureon:workforce-auris-nodes",
        trusted_resolver_ids={"aureon:workforce-auris-nodes"},
        calibration_report=calibration.report,
        pair_loader=lambda _request: newer_pair,
        clock=lambda: NOW,
    )
    with pytest.raises(
        ValueError,
        match="recalibration_required_for_current_provider_moment",
    ):
        newer_factory.build_auris_node_resolver(_governance_request(newer_pair))


def test_factory_rejects_stale_persisted_calibration_before_loading_pair():
    calibration, pair = _successful_calibration()
    pair_calls = [0]

    def pair_loader(_request):
        pair_calls[0] += 1
        return pair

    with pytest.raises(ValueError, match="fresh_workforce_auris_calibration_required"):
        bind_calibrated_workforce_auris_resolver_factory(
            factory_id="aureon:workforce-auris-nodes",
            trusted_resolver_ids={"aureon:workforce-auris-nodes"},
            calibration_report=calibration.report,
            pair_loader=pair_loader,
            max_age_s=30.0,
            clock=lambda: NOW + 31.0,
        )
    assert pair_calls == [0]


def test_acquisition_supplier_loads_and_canonicalizes_each_live_pair():
    pairs = iter((_pair(1, 0.81), _pair(2, 0.85)))
    supplier = bind_hnc_auris_governance_acquisition_supplier(
        supplier_id="aureon:test:hnc-auris-acquisition",
        trusted_supplier_ids={"aureon:test:hnc-auris-acquisition"},
        pair_loader=lambda: next(pairs),
        clock=lambda: NOW,
    )

    first = supplier.load_governance_acquisition()
    second = supplier.load_governance_acquisition()

    assert first["provider_moment_digest"] != second["provider_moment_digest"]
    assert first["provider_receipt_ids"] == sorted(
        set(first["provider_receipt_ids"])
    )
    assert first["provider_source_timestamp"] == _timestamp_text(
        _pair(1, 0.81)[1]["source_timestamp"]
    )


def test_composition_status_requires_fresh_receipt_nodes_and_real_quorum(tmp_path):
    calibration, _pair_value = _successful_calibration((0.81, 0.90, 0.85))
    nodes = [
        issue_auris_node_receipt(
            seat=seat,
            resolver=calibration.node_resolver,
            now=NOW,
        )
        for seat in REQUIRED_SEATS
    ]
    driver_count = sum(float(node["gamma"]) >= ACTIVE_THRESHOLD for node in nodes)
    payload = {
        "schema": "aureon.live-druidic-calibration-operation.v1",
        "status": "complete",
        "reason": None,
        "provider_mode": "ollama_cloud_primary",
        "calibration_receipt": calibration.report,
        "auris_nodes": nodes,
        "node_driver_count": driver_count,
        "action_eligible": False,
        "economic_mutation": False,
        "exchange_call_count": 0,
        "order_call_count": 0,
    }
    complete_path = tmp_path / "complete.json"
    hold_path = tmp_path / "hold.json"
    complete_path.write_text(_canonical(payload), encoding="utf-8")

    status = load_latest_calibration_status(
        complete_path=complete_path,
        hold_path=hold_path,
        now=NOW,
    )
    assert status["status"] == "complete"
    assert status["receipt_id"] == calibration.report["receipt_id"]

    payload["node_driver_count"] = driver_count + 1
    complete_path.write_text(_canonical(payload), encoding="utf-8")
    rejected = load_latest_calibration_status(
        complete_path=complete_path,
        hold_path=hold_path,
        now=NOW,
    )
    assert rejected == {
        "status": "hold",
        "reason": "valid_fresh_druidic_calibration_receipt_required",
        "source_path": str(complete_path),
    }


def test_transient_missing_pair_retries_inside_existing_deadline():
    resolver = _resolver()
    workforce = _Workforce(resolver)
    pairs = iter((_pair(1, 0.81), _pair(2, 0.85), _pair(3, 0.90)))
    attempts = [0]

    def pair_loader():
        attempts[0] += 1
        if attempts[0] == 1:
            raise ValueError("fresh_active_hnc_auris_provider_pair_unavailable")
        return next(pairs)

    calibration = collect_live_workforce_auris_calibration(
        workforce=workforce,
        evidence_resolver=resolver,
        auris_resolver_id="aureon:workforce-auris-nodes",
        trusted_auris_resolver_ids={"aureon:workforce-auris-nodes"},
        pair_loader=pair_loader,
        clock=lambda: NOW,
        sleep=lambda _value: None,
    )

    assert calibration.report["round_count"] == 3
    assert attempts[0] == 4
    assert len(workforce.calls) == 12


def test_repeated_provider_moment_is_not_counted_as_a_new_round():
    resolver = _resolver()
    workforce = _Workforce(resolver)
    pair = _pair(1, 0.81)
    current = [NOW - 0.25]

    def advancing_clock():
        current[0] += 0.25
        return current[0]

    with pytest.raises(ValueError, match="distinct_provider_moment_wait_expired"):
        collect_live_workforce_auris_calibration(
            workforce=workforce,
            evidence_resolver=resolver,
            auris_resolver_id="aureon:workforce-auris-nodes",
            trusted_auris_resolver_ids={"aureon:workforce-auris-nodes"},
            pair_loader=lambda: pair,
            new_pair_wait_s=1.0,
            poll_interval_s=0.1,
            clock=advancing_clock,
            sleep=lambda _value: None,
        )
    assert len(workforce.calls) == 4


def test_distinct_receipt_with_unchanged_hnc_gamma_does_not_spend_cloud_calls():
    resolver = _resolver()
    workforce = _Workforce(resolver)
    first = _pair(1, 0.81)
    unchanged_field = _pair(2, 0.81)
    loaded_first = [False]
    current = [NOW - 0.25]

    def pair_loader():
        if not loaded_first[0]:
            loaded_first[0] = True
            return first
        return unchanged_field

    def advancing_clock():
        current[0] += 0.25
        return current[0]

    with pytest.raises(ValueError, match="distinct_hnc_gamma_wait_expired"):
        collect_live_workforce_auris_calibration(
            workforce=workforce,
            evidence_resolver=resolver,
            auris_resolver_id="aureon:workforce-auris-nodes",
            trusted_auris_resolver_ids={"aureon:workforce-auris-nodes"},
            pair_loader=pair_loader,
            new_pair_wait_s=1.0,
            poll_interval_s=0.1,
            clock=advancing_clock,
            sleep=lambda _value: None,
        )
    assert len(workforce.calls) == 4


def test_unpinned_resolver_has_no_hnc_or_auris_evidence():
    resolver = _resolver()
    request = ThoughtPathRequest(
        subject_type="agent",
        subject_id="Risk Governor",
        process_id="agent_company_role_cycle:risk_governor",
        stage="auris_coherence_probe",
        work_kind="auris_coherence_measurement",
        prompt_digest="a" * 64,
        brain_passport_id="brain:" + "b" * 64,
    )
    assert resolver.resolve_hnc_evidence(request) is None
    assert (
        resolver.resolve_auris_evidence(
            request,
            answer_digest="c" * 64,
            hnc_receipt_id="hnc:live_field:missing",
        )
        is None
    )


def test_negative_window_returns_a_complete_non_authoritative_hold_receipt():
    resolver = _resolver()
    workforce = _Workforce(resolver)
    pairs = iter((_pair(1, 0.90), _pair(2, 0.85), _pair(3, 0.81)))
    with pytest.raises(WorkforceCalibrationHold) as caught:
        collect_live_workforce_auris_calibration(
            workforce=workforce,
            evidence_resolver=resolver,
            auris_resolver_id="aureon:workforce-auris-nodes",
            trusted_auris_resolver_ids={"aureon:workforce-auris-nodes"},
            pair_loader=lambda: next(pairs),
            clock=lambda: NOW,
            sleep=lambda _value: None,
        )
    report = caught.value.report
    assert report["status"] == "hold"
    assert report["reason"] == "negative_measured_coherence_cannot_drive_council"
    assert report["negative_seats"] == list(REQUIRED_SEATS)
    assert report["sample_count"] == 12
    assert all(len(report["seat_samples"][seat]) == 3 for seat in REQUIRED_SEATS)
    assert report["action_eligible"] is False
    assert report["economic_mutation"] is False


def test_exact_menu_stop_is_bound_for_native_and_compatible_ollama_payloads():
    adapter = AureonLocalAdapter.__new__(AureonLocalAdapter)
    adapter.base_url = "http://127.0.0.1:11434/v1"
    adapter._native_root = "http://127.0.0.1:11434"
    adapter._keep_alive = None
    adapter.model = "test-model"
    native = adapter._build_native_payload(
        [{"role": "user", "content": "choose one line"}],
        "system",
        64,
        0.0,
        ["\n"],
    )
    compatible = adapter._build_payload(
        [{"role": "user", "content": "choose one line"}],
        "system",
        None,
        64,
        0.0,
        stop=["\n"],
    )
    assert native["options"]["stop"] == ["\n"]
    assert compatible["stop"] == ["\n"]
