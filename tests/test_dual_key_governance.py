from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from aureon.governance.dual_key import (
    build_queen_receipt,
    join_dual_key,
    validate_dual_key_receipt,
)
from aureon.swarm.druidic_council import REQUIRED_SEATS, build_seat_receipt, convene_druidic_council

NOW = 1_786_473_600.0
PROPOSAL = "d" * 64
PROMPT = "e" * 64
HNC = "hnc:live_field:dual-key-hnc"
AURIS = "auris:cosmic_state:dual-key-auris"
FALSE_FLAGS = (
    "action_eligible",
    "accounting_eligible",
    "learning_eligible",
    "eligible_for_action",
    "eligible_for_accounting",
    "eligible_for_learning",
    "economic_mutation",
)


def _council(
    *,
    decisions: Mapping[str, str] | None = None,
    gammas: Mapping[str, float] | None = None,
    proposal_digest: str = PROPOSAL,
) -> dict[str, Any]:
    decisions = decisions or {}
    gammas = gammas or {}
    seats = [
        build_seat_receipt(
            seat=seat,
            agent_id=f"agent-{seat}",
            decision=decisions.get(seat, "ACCEPT"),
            reason=f"{seat} complete",
            gamma=gammas.get(seat, 0.90),
            proposal_digest=proposal_digest,
            prompt_digest=PROMPT,
            hnc_receipt_id=HNC,
            auris_receipt_id=AURIS,
            auris_node_receipt_id=f"auris:node:{seat}:receipt",
            source_timestamp=NOW - 4.0,
            derived_at=NOW - 1.0,
        )
        for seat in REQUIRED_SEATS
    ]
    return convene_druidic_council(
        proposal_digest=proposal_digest,
        prompt_digest=PROMPT,
        hnc_receipt_id=HNC,
        auris_receipt_id=AURIS,
        seat_receipts=seats,
        now=NOW,
    )


def _queen(
    decision: str = "APPROVE",
    *,
    proposal_digest: str = PROPOSAL,
    source_timestamp: float = NOW - 4.0,
    derived_at: float = NOW,
) -> dict[str, Any]:
    return build_queen_receipt(
        decision=decision,
        reason="queen and chief verified purpose and authority",
        proposal_digest=proposal_digest,
        prompt_digest=PROMPT,
        hnc_receipt_id=HNC,
        auris_receipt_id=AURIS,
        source_timestamp=source_timestamp,
        derived_at=derived_at,
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


def test_council_and_queen_work_side_by_side_as_required_keys() -> None:
    council = _council()
    queen = _queen()
    joined = join_dual_key(council, queen, now=NOW)

    assert council["decision"] == "ACCEPT"
    assert queen["decision"] == "APPROVE"
    assert joined["decision"] == "ACCEPT"
    assert joined["reason"] == "council_and_queen_dual_key_passed"
    assert joined["council_receipt_id"] == council["receipt_id"]
    assert joined["queen_receipt_id"] == queen["receipt_id"]
    assert joined["provider_receipt_ids"] == []
    assert joined["provider_moment_digest"] is None
    assert joined["provider_source_timestamp"] == str(int(NOW - 4.0))
    assert joined["source_timestamp"] == NOW - 4.0
    assert joined["rune_voices"] == ["druid_council", "queen_chief"]
    assert joined["voices_required"] == 2
    assert joined["voices_present"] == 2
    assert joined["lineage_alignment"] == "exact_proposal_hnc_auris_provider_moment"
    assert joined["harmonic_outcome"] == "CONSTRUCTIVE"
    assert joined["route_authorization_required"] is True
    assert all(joined[name] is False for name in FALSE_FLAGS)
    assert validate_dual_key_receipt(joined, now=NOW) == joined


@pytest.mark.parametrize(
    ("council_decisions", "queen_decision", "expected"),
    [
        ({"seer": "HOLD", "weaver": "HOLD"}, "APPROVE", "HOLD"),
        ({}, "HOLD", "HOLD"),
        ({"sentinel": "ABORT"}, "APPROVE", "ABORT"),
        ({}, "ABORT", "ABORT"),
    ],
)
def test_neither_governance_peer_can_force_the_other_key(
    council_decisions: Mapping[str, str],
    queen_decision: str,
    expected: str,
) -> None:
    joined = join_dual_key(
        _council(decisions=council_decisions),
        _queen(queen_decision),
        now=NOW,
    )

    assert joined["decision"] == expected
    assert joined["economic_mutation"] is False


def test_dual_key_receipt_identity_excludes_local_derived_clock() -> None:
    council = _council()
    queen_a = _queen(derived_at=NOW)
    queen_b = _queen(derived_at=NOW + 15.0)

    assert queen_a["receipt_id"] == queen_b["receipt_id"]
    first = join_dual_key(council, queen_a, now=NOW)
    second = join_dual_key(council, queen_b, now=NOW + 15.0)
    assert first["receipt_id"] == second["receipt_id"]
    assert first["derived_at"] != second["derived_at"]


@pytest.mark.parametrize(
    "failure",
    ["lineage", "provider_moment", "stale", "council_tamper", "queen_tamper"],
)
def test_invalid_or_unlinked_peer_key_is_numeric_free_no_data(failure: str) -> None:
    council = _council()
    queen = _queen()
    if failure == "lineage":
        queen = _queen(proposal_digest="f" * 64)
    elif failure == "provider_moment":
        queen = _queen(source_timestamp=NOW - 3.0)
    elif failure == "stale":
        queen = _queen(source_timestamp=NOW - 400.0)
    elif failure == "council_tamper":
        council = copy.deepcopy(council)
        council["decision"] = "ABORT"
    else:
        queen = copy.deepcopy(queen)
        queen["reason"] = "tampered"

    joined = join_dual_key(council, queen, now=NOW)

    assert joined["decision"] == "HOLD"
    assert joined["data_status"] == "no_data"
    assert joined["receipt_id"] is None
    assert joined["input_receipt_ids"] == []
    assert all(joined[name] is False for name in FALSE_FLAGS)
    _assert_numeric_free(joined)


def test_dual_key_acceptance_is_evidence_not_route_authorization() -> None:
    joined = join_dual_key(_council(), _queen(), now=NOW)

    assert joined["decision"] == "ACCEPT"
    assert joined["route_authorization_required"] is True
    assert joined["action_eligible"] is False
    assert joined["accounting_eligible"] is False
    assert joined["learning_eligible"] is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("voices_present", True),
        ("provider_receipt_ids", ["provider:tampered"]),
        ("provider_moment_digest", "a" * 64),
        ("provider_source_timestamp", "1"),
        ("lineage_alignment", "approximate"),
        ("harmonic_outcome", "HOLD"),
        ("actionable", True),
    ],
)
def test_final_two_rune_receipt_rejects_tampering(field: str, value: Any) -> None:
    joined = copy.deepcopy(join_dual_key(_council(), _queen(), now=NOW))
    joined[field] = value

    with pytest.raises(ValueError):
        validate_dual_key_receipt(joined, now=NOW)
