from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

import aureon.swarm.druidic_council as council_module
from aureon.swarm.druidic_council import (
    PHI,
    PHI_INVERSE,
    PHI_SQUARED,
    PHI_TOPOLOGY,
    REQUIRED_SEATS,
    build_seat_receipt,
    convene_druidic_council,
    validate_council_receipt,
    validate_seat_receipt,
    voice_for_gamma,
)

NOW = 1_786_473_600.0
PROPOSAL = "a" * 64
PROMPT = "b" * 64
HNC = "hnc:live_field:receipt-a"
AURIS = "auris:cosmic_state:receipt-b"
FALSE_FLAGS = (
    "action_eligible",
    "accounting_eligible",
    "learning_eligible",
    "eligible_for_action",
    "eligible_for_accounting",
    "eligible_for_learning",
    "economic_mutation",
)


def _seat_receipts(
    *,
    decisions: Mapping[str, str] | None = None,
    gammas: Mapping[str, float] | None = None,
    proposal_digest: str = PROPOSAL,
) -> list[dict[str, Any]]:
    decisions = decisions or {}
    gammas = gammas or {}
    return [
        build_seat_receipt(
            seat=seat,
            agent_id=f"agent-{seat}",
            decision=decisions.get(seat, "ACCEPT"),
            reason=f"{seat} verified its discipline boundary",
            gamma=gammas.get(seat, 0.90),
            proposal_digest=proposal_digest,
            prompt_digest=PROMPT,
            hnc_receipt_id=HNC,
            auris_receipt_id=AURIS,
            auris_node_receipt_id=f"auris:node:{seat}:receipt",
            source_timestamp=NOW - 5.0,
            derived_at=NOW - 1.0,
        )
        for seat in REQUIRED_SEATS
    ]


def _convene(
    seats: Sequence[Mapping[str, Any]],
    *,
    now: float = NOW,
) -> dict[str, Any]:
    return convene_druidic_council(
        proposal_digest=PROPOSAL,
        prompt_digest=PROMPT,
        hnc_receipt_id=HNC,
        auris_receipt_id=AURIS,
        seat_receipts=seats,
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


def _rehash_council(receipt: dict[str, Any]) -> None:
    receipt["receipt_id"] = (
        f"druid:council:"
        f"{council_module._sha256(council_module._council_causal(receipt))}"
    )


@pytest.mark.parametrize(
    ("gamma", "band", "weight"),
    [
        (0.0, "ADVISORY", 0.0),
        (0.799999, "ADVISORY", 0.0),
        (0.80, "ACTIVE", 0.80),
        (0.944999, "ACTIVE", 0.944999),
        (0.945, "LIGHTHOUSE", 0.945),
        (1.0, "LIGHTHOUSE", 1.0),
    ],
)
def test_voice_bands_use_raw_gamma_without_invented_multiplier(
    gamma: float,
    band: str,
    weight: float,
) -> None:
    assert voice_for_gamma(gamma) == (band, weight)


@pytest.mark.parametrize("gamma", [float("nan"), float("inf"), -0.1, 1.1, True])
def test_invalid_gamma_never_mints_a_seat_receipt(gamma: Any) -> None:
    with pytest.raises(ValueError):
        build_seat_receipt(
            seat="seer",
            agent_id="agent-seer",
            decision="ACCEPT",
            reason="complete",
            gamma=gamma,
            proposal_digest=PROPOSAL,
            prompt_digest=PROMPT,
            hnc_receipt_id=HNC,
            auris_receipt_id=AURIS,
            auris_node_receipt_id="auris:node:seer:receipt",
            source_timestamp=NOW - 1.0,
        )


def test_four_stable_peer_seats_accept_with_exact_receipt_lineage() -> None:
    seats = _seat_receipts(gammas={"seer": 0.95, "sentinel": 0.92})
    receipt = _convene(seats)

    assert receipt["decision"] == "ACCEPT"
    assert receipt["reason"] == "phi_weighted_quorum_accept"
    assert [seat["seat"] for seat in receipt["seat_summaries"]] == list(REQUIRED_SEATS)
    assert receipt["driving_seat_count"] == 4
    assert receipt["quorum_passed"] is True
    assert receipt["hnc_receipt_id"] == HNC
    assert receipt["auris_receipt_id"] == AURIS
    assert all(seat["receipt_id"] in receipt["input_receipt_ids"] for seat in seats)
    assert all(
        seat["auris_node_receipt_id"] in receipt["input_receipt_ids"]
        for seat in seats
    )
    assert receipt["source_timestamp"] == NOW - 5.0
    assert receipt["receipt_id"].startswith("druid:council:")
    assert receipt["route_authorization_required"] is True
    assert all(receipt[name] is False for name in FALSE_FLAGS)
    assert validate_council_receipt(receipt, now=NOW) == receipt


def test_phi_ring_is_peer_symmetric_and_hash_bound() -> None:
    receipt = _convene(_seat_receipts())

    assert receipt["schema"] == "aureon.druidic_council.v2"
    assert receipt["phi"] == PHI
    assert receipt["phi_inverse"] == PHI_INVERSE
    assert receipt["phi_squared"] == PHI_SQUARED
    assert receipt["phi_topology"] == PHI_TOPOLOGY
    assert receipt["effective_participation"] == pytest.approx(4.0)
    assert receipt["phi_stability_ratio"] == pytest.approx(4.0 / PHI_SQUARED)
    assert receipt["phi_stability_passed"] is True
    assert receipt["dominance_cap_passed"] is True
    expected_factor = PHI_SQUARED / len(REQUIRED_SEATS)
    for position, seat in enumerate(receipt["seat_summaries"]):
        assert seat["ring_position"] == position
        assert seat["phi_topology_factor"] == pytest.approx(expected_factor)
        assert seat["phi_band_multiplier"] == 1.0
        assert seat["normalized_voice_influence"] == pytest.approx(0.25)


def test_phi_ring_uses_exact_neighbour_and_opposite_couplings() -> None:
    assert council_module._phi_coupling(0, 0) == 1.0
    assert council_module._phi_coupling(0, 1) == pytest.approx(PHI_INVERSE)
    assert council_module._phi_coupling(0, 3) == pytest.approx(PHI_INVERSE)
    assert council_module._phi_coupling(0, 2) == pytest.approx(PHI_INVERSE**2)


def test_phi_influence_is_rotation_covariant_not_seat_ranked() -> None:
    base_values = [1.0, 0.80, 0.79, 0.80]
    rotated_values = [base_values[-1], *base_values[:-1]]
    base = _convene(
        _seat_receipts(gammas=dict(zip(REQUIRED_SEATS, base_values, strict=True)))
    )
    rotated = _convene(
        _seat_receipts(
            gammas=dict(zip(REQUIRED_SEATS, rotated_values, strict=True))
        )
    )
    base_influences = [
        item["normalized_voice_influence"] for item in base["seat_summaries"]
    ]
    rotated_influences = [
        item["normalized_voice_influence"]
        for item in rotated["seat_summaries"]
    ]
    assert rotated_influences == pytest.approx(
        [base_influences[-1], *base_influences[:-1]]
    )


def test_two_voice_harmonic_is_capped_but_cannot_reach_phi_squared() -> None:
    receipt = _convene(
        _seat_receipts(
            gammas={
                "seer": 1.0,
                "sentinel": 0.80,
                "weaver": 0.79,
                "keeper": 0.79,
            }
        )
    )

    assert receipt["max_normalized_voice_influence"] == pytest.approx(PHI_INVERSE)
    assert receipt["dominance_cap_passed"] is True
    assert receipt["effective_participation"] < PHI_SQUARED
    assert receipt["phi_stability_passed"] is False
    assert receipt["quorum_passed"] is False
    assert receipt["decision"] == "HOLD"
    influences = sorted(
        item["normalized_voice_influence"]
        for item in receipt["seat_summaries"]
        if item["normalized_voice_influence"] > 0.0
    )
    assert influences == pytest.approx([PHI_INVERSE**2, PHI_INVERSE])
    assert sum(influences) == pytest.approx(1.0)
    assert validate_council_receipt(receipt, now=NOW) == receipt


def test_phi_squared_stability_holds_a_dominated_three_voice_council() -> None:
    receipt = _convene(
        _seat_receipts(
            gammas={
                "seer": 1.0,
                "sentinel": 0.80,
                "weaver": 0.79,
                "keeper": 0.80,
            }
        )
    )

    assert receipt["structural_quorum_passed"] is True
    assert receipt["effective_participation"] < PHI_SQUARED
    assert receipt["phi_stability_passed"] is False
    assert receipt["decision"] == "HOLD"
    assert receipt["reason"] == "phi_squared_stability_not_satisfied"


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("seat_summaries", 0, "normalized_voice_influence"), 0.99),
        (("phi_squared",), 2.0),
        (("effective_participation",), 99.0),
    ],
)
def test_tampered_phi_policy_fields_fail_validation(
    path: tuple[Any, ...],
    replacement: float,
) -> None:
    receipt = copy.deepcopy(_convene(_seat_receipts()))
    target: Any = receipt
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement

    with pytest.raises(ValueError):
        validate_council_receipt(receipt, now=NOW)


@pytest.mark.parametrize("field", ["accept_support", "phi_accept_support"])
def test_boolean_cannot_replace_numeric_metric_even_with_valid_hash(field: str) -> None:
    receipt = copy.deepcopy(_convene(_seat_receipts()))
    assert receipt[field] == 1.0
    receipt[field] = True
    _rehash_council(receipt)

    with pytest.raises(ValueError):
        validate_council_receipt(receipt, now=NOW)


@pytest.mark.parametrize('field', ['gamma_dispersion', 'phi_gamma_dispersion'])
def test_negative_zero_cannot_mint_an_alternate_valid_receipt_id(field: str) -> None:
    receipt = copy.deepcopy(_convene(_seat_receipts()))
    assert receipt[field] == 0.0
    original_id = receipt['receipt_id']
    receipt[field] = -0.0
    _rehash_council(receipt)
    assert receipt['receipt_id'] != original_id

    with pytest.raises(ValueError):
        validate_council_receipt(receipt, now=NOW)


def test_boolean_cannot_replace_full_voice_weight_even_with_valid_hash() -> None:
    seat = _seat_receipts(gammas={"seer": 1.0})[0]
    seat["voice_weight"] = True
    seat["receipt_id"] = (
        f"druid:seat:{council_module._sha256(council_module._seat_causal(seat))}"
    )

    with pytest.raises(ValueError):
        validate_seat_receipt(seat, now=NOW)


def test_v1_council_receipt_is_rejected_after_phi_policy_upgrade() -> None:
    receipt = copy.deepcopy(_convene(_seat_receipts()))
    receipt["schema"] = "aureon.druidic_council.v1"
    _rehash_council(receipt)

    with pytest.raises(ValueError):
        validate_council_receipt(receipt, now=NOW)


def test_causal_ids_ignore_local_derived_clock() -> None:
    first = _seat_receipts()
    second = _seat_receipts()
    for item in second:
        item["derived_at"] = NOW + 20.0

    assert [item["receipt_id"] for item in first] == [
        item["receipt_id"] for item in second
    ]
    council_a = _convene(first, now=NOW)
    council_b = _convene(second, now=NOW + 20.0)
    assert council_a["receipt_id"] == council_b["receipt_id"]
    assert council_a["derived_at"] != council_b["derived_at"]


def test_exact_two_thirds_support_passes_with_required_guardian_seats() -> None:
    receipt = _convene(
        _seat_receipts(
            decisions={"keeper": "HOLD"},
            gammas={"seer": 0.90, "sentinel": 0.90, "weaver": 0.79, "keeper": 0.90},
        )
    )

    assert receipt["driving_seat_count"] == 3
    assert receipt["accept_support"] == pytest.approx(2.0 / 3.0)
    assert receipt["decision"] == "ACCEPT"


def test_low_coherence_keeper_is_advisory_and_cannot_form_quorum() -> None:
    receipt = _convene(_seat_receipts(gammas={"keeper": 0.79}))

    keeper = next(item for item in receipt["seat_summaries"] if item["seat"] == "keeper")
    assert keeper["voice_band"] == "ADVISORY"
    assert keeper["voice_weight"] == 0.0
    assert receipt["quorum_passed"] is False
    assert receipt["decision"] == "HOLD"


def test_advisory_abort_is_recorded_but_cannot_force_the_outcome() -> None:
    receipt = _convene(
        _seat_receipts(
            decisions={"seer": "ABORT"},
            gammas={"seer": 0.70},
        )
    )

    seer = next(item for item in receipt["seat_summaries"] if item["seat"] == "seer")
    assert seer["decision"] == "ABORT"
    assert seer["voice_band"] == "ADVISORY"
    assert receipt["decision"] == "ACCEPT"
    assert receipt["economic_mutation"] is False


def test_driving_seat_abort_stops_actualization() -> None:
    receipt = _convene(_seat_receipts(decisions={"sentinel": "ABORT"}))

    assert receipt["decision"] == "ABORT"
    assert receipt["reason"] == "seat_abort_dominates"


def test_mixed_seat_provider_moments_cannot_form_a_harmonic() -> None:
    seats = _seat_receipts()
    seats[0] = build_seat_receipt(
        seat="seer",
        agent_id="agent-seer",
        decision="ACCEPT",
        reason="seer complete at a different moment",
        gamma=0.90,
        proposal_digest=PROPOSAL,
        prompt_digest=PROMPT,
        hnc_receipt_id=HNC,
        auris_receipt_id=AURIS,
        auris_node_receipt_id="auris:node:seer:receipt",
        source_timestamp=NOW - 6.0,
        derived_at=NOW,
    )

    receipt = _convene(seats)
    assert receipt["data_status"] == "no_data"
    assert receipt["decision"] == "HOLD"
    _assert_numeric_free(receipt)


@pytest.mark.parametrize("duplicate", ["agent", "node"])
def test_one_actor_or_node_cannot_occupy_two_stable_seats(duplicate: str) -> None:
    seats = _seat_receipts()
    seats[1] = build_seat_receipt(
        seat="sentinel",
        agent_id="agent-seer" if duplicate == "agent" else "agent-sentinel",
        decision="ACCEPT",
        reason="sentinel complete",
        gamma=0.90,
        proposal_digest=PROPOSAL,
        prompt_digest=PROMPT,
        hnc_receipt_id=HNC,
        auris_receipt_id=AURIS,
        auris_node_receipt_id=(
            "auris:node:seer:receipt"
            if duplicate == "node"
            else "auris:node:sentinel:receipt"
        ),
        source_timestamp=NOW - 5.0,
        derived_at=NOW,
    )

    receipt = _convene(seats)
    assert receipt["data_status"] == "no_data"
    assert receipt["decision"] == "HOLD"


def test_unknown_true_eligibility_alias_invalidates_a_seat() -> None:
    seats = _seat_receipts()
    seats[0]["custom_eligible"] = True

    receipt = _convene(seats)
    assert receipt["data_status"] == "no_data"
    assert receipt["decision"] == "HOLD"


def test_council_validator_rejects_malformed_summary_without_type_escape() -> None:
    receipt = _convene(_seat_receipts())
    receipt["seat_summaries"][0] = []

    with pytest.raises(ValueError):
        validate_council_receipt(receipt, now=NOW)


def test_nonpositive_freshness_window_fails_closed() -> None:
    receipt = _convene(_seat_receipts())

    with pytest.raises(ValueError):
        validate_council_receipt(receipt, now=NOW, max_age_s=0.0)


@pytest.mark.parametrize(
    "failure",
    ["stale", "mismatch", "tamper", "node_link", "missing"],
)
def test_incomplete_stale_or_unlinked_council_is_numeric_free_no_data(
    failure: str,
) -> None:
    seats = _seat_receipts()
    if failure == "stale":
        result = _convene(seats, now=NOW + 400.0)
    else:
        changed = copy.deepcopy(seats)
        if failure == "mismatch":
            changed[0] = build_seat_receipt(
                seat="seer",
                agent_id="agent-seer",
                decision="ACCEPT",
                reason="mismatched proposal",
                gamma=0.90,
                proposal_digest="c" * 64,
                prompt_digest=PROMPT,
                hnc_receipt_id=HNC,
                auris_receipt_id=AURIS,
                auris_node_receipt_id="auris:node:seer:receipt",
                source_timestamp=NOW - 5.0,
                derived_at=NOW,
            )
        elif failure == "tamper":
            changed[0]["gamma"] = 0.99
        elif failure == "node_link":
            changed[0]["input_receipt_ids"].remove(
                changed[0]["auris_node_receipt_id"]
            )
        else:
            changed.pop()
        result = _convene(changed)

    assert result["decision"] == "HOLD"
    assert result["data_status"] == "no_data"
    assert result["receipt_id"] is None
    assert result["input_receipt_ids"] == []
    assert all(result[name] is False for name in FALSE_FLAGS)
    _assert_numeric_free(result)
