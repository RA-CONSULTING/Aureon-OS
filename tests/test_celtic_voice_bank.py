from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

import pytest

from aureon.governance.celtic_voice_bank import (
    CELTIC_VOICE_BANK_PATH,
    CELTIC_VOICE_BANK_SCHEMA,
    SEASONAL_GATE_ORDER,
    SEAT_PRINCIPLES,
    CelticSeatedDruidResolver,
    celtic_seat_context,
    read_canonical_celtic_voice_bank,
    seasonal_gate_for_date,
    validate_celtic_voice_bank_receipt,
)
from aureon.governance.druid_voice import (
    DruidSeatIssuerBinding,
    ResolvedDruidSeatVoice,
    issue_trusted_druidic_council,
)
from aureon.swarm.auris_node_receipts import COHERENCE_METHOD, NODE_SCHEMA
from aureon.swarm.druidic_council import REQUIRED_SEATS

NOW = 1_786_480_000.0
PROPOSAL = "a" * 64
PROMPT = "b" * 64
HNC = "hnc:live_field:celtic-cycle"
AURIS = "auris:cosmic_state:celtic-cycle"
PROVIDERS = ["provider:hnc:a", "provider:noaa:b", "provider:schumann:c"]
MOMENT_DIGEST = "c" * 64

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


def _sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _node(seat: str, *, gamma: float = 0.90) -> dict[str, Any]:
    agent_id = f"agent-{seat}"
    measurement = f"auris:coherence_measurement:{seat}"
    resolver = "aureon:trusted-node-runtime:v1"
    causal = {
        "schema": NODE_SCHEMA,
        "receipt_type": "auris_node",
        "seat": seat,
        "agent_id": agent_id,
        "resolver_id": resolver,
        "coherence_source_id": f"aureon:coherence-meter:{seat}",
        "seat_binding_digest": _sha(
            {"resolver_id": resolver, "seat": seat, "agent_id": agent_id}
        ),
        "gamma": gamma,
        "measurement_method": COHERENCE_METHOD,
        "coherence_measurement_receipt_id": measurement,
        "hnc_receipt_id": HNC,
        "auris_receipt_id": AURIS,
        "provider_receipt_ids": list(PROVIDERS),
        "provider_moment_digest": MOMENT_DIGEST,
        "source_timestamp": NOW - 5.0,
        "input_receipt_ids": sorted({HNC, AURIS, measurement, *PROVIDERS}),
        "data_status": "live",
        "truth_status": "real_derived",
        "freshness_status": "fresh",
        "equation_inputs_complete": True,
        "generated_values": False,
        "route_authorization_required": True,
        **dict.fromkeys(FALSE_FLAGS, False),
    }
    return {
        **causal,
        "receipt_id": f"auris:node:{_sha(causal)}",
        "derived_at": NOW - 1.0,
    }


def _nodes() -> list[dict[str, Any]]:
    return [_node(seat) for seat in REQUIRED_SEATS]


class _Delegate:
    def __init__(
        self,
        nodes: Sequence[Mapping[str, Any]],
        *,
        decisions: Mapping[str, str] | None = None,
        source_namespace: str = "v1",
    ) -> None:
        self.nodes = {node["seat"]: copy.deepcopy(node) for node in nodes}
        self.decisions = dict(decisions or {})
        self.source_namespace = source_namespace

    def trusted_druid_seat_bindings(
        self,
    ) -> Mapping[str, DruidSeatIssuerBinding]:
        return {
            seat: DruidSeatIssuerBinding(
                resolver_id="aureon:trusted-druid-runtime:v1",
                issuer_id="druid:council:issuer:v1",
                decision_source_id=(
                    f"druid:decision-source:{seat}:{self.source_namespace}"
                ),
                seat=seat,
                agent_id=self.nodes[seat]["agent_id"],
            )
            for seat in REQUIRED_SEATS
        }

    def resolve_druid_seat_voice(
        self,
        seat: str,
        proposal_digest: str,
        prompt_digest: str,
    ) -> ResolvedDruidSeatVoice:
        node = self.nodes[seat]
        return ResolvedDruidSeatVoice(
            resolver_id="aureon:trusted-druid-runtime:v1",
            issuer_id="druid:council:issuer:v1",
            decision_source_id=f"druid:decision-source:{seat}:{self.source_namespace}",
            seat=seat,
            agent_id=node["agent_id"],
            decision=self.decisions.get(seat, "ACCEPT"),
            reason=f"{seat} verified the exact evidence boundary",
            proposal_digest=proposal_digest,
            prompt_digest=prompt_digest,
            auris_node_receipt_id=node["receipt_id"],
            hnc_receipt_id=node["hnc_receipt_id"],
            auris_receipt_id=node["auris_receipt_id"],
            provider_receipt_ids=tuple(node["provider_receipt_ids"]),
            provider_moment_digest=node["provider_moment_digest"],
            source_timestamp=node["source_timestamp"],
        )


def test_canonical_repository_voice_bank_has_exact_seats_triad_and_gates() -> None:
    receipt = read_canonical_celtic_voice_bank()

    assert receipt["schema"] == CELTIC_VOICE_BANK_SCHEMA
    assert receipt["dataset_source"] == "wisdom_data/celtic_wisdom.json"
    assert receipt["dataset_sha256"] == hashlib.sha256(
        CELTIC_VOICE_BANK_PATH.read_bytes()
    ).hexdigest()
    assert [profile["seat"] for profile in receipt["seat_profiles"]] == list(
        REQUIRED_SEATS
    )
    assert [profile["principle"] for profile in receipt["seat_profiles"]] == [
        SEAT_PRINCIPLES[seat] for seat in REQUIRED_SEATS
    ]
    assert receipt["triad_logic"]["required_confirming_voices"] == 3
    assert [gate["gate"] for gate in receipt["seasonal_gates"]] == list(
        SEASONAL_GATE_ORDER
    )
    assert receipt["learned_insight_count"] == 127
    assert receipt["reference_material_status"] == "mixed_repository_reference_only"
    assert all(receipt[name] is False for name in FALSE_FLAGS)


@pytest.mark.parametrize(
    ("value", "gate"),
    [
        (date(2026, 1, 1), "samhain"),
        (date(2026, 2, 1), "imbolc"),
        (date(2026, 5, 1), "beltane"),
        (date(2026, 8, 1), "lughnasadh"),
        (date(2026, 10, 31), "samhain"),
    ],
)
def test_fire_festival_gate_boundaries_are_deterministic(
    value: date,
    gate: str,
) -> None:
    assert seasonal_gate_for_date(value) == gate


def test_four_seat_contexts_are_distinct_and_bound_to_one_voice_bank() -> None:
    receipt = read_canonical_celtic_voice_bank()
    contexts = [
        celtic_seat_context(receipt, seat=seat, seasonal_gate="lughnasadh")
        for seat in REQUIRED_SEATS
    ]

    assert len({item["context_digest"] for item in contexts}) == 4
    assert {item["voice_bank_receipt_id"] for item in contexts} == {
        receipt["receipt_id"]
    }
    assert {item["triad_required_confirming_voices"] for item in contexts} == {3}


def test_celtic_seating_preserves_decisions_and_exact_hnc_auris_lineage() -> None:
    nodes = _nodes()
    delegate = _Delegate(nodes, decisions={"sentinel": "HOLD"})
    resolver = CelticSeatedDruidResolver(
        delegate=delegate,
        voice_bank_receipt=read_canonical_celtic_voice_bank(),
        seasonal_gate="samhain",
    )

    original = delegate.resolve_druid_seat_voice("sentinel", PROPOSAL, PROMPT)
    seated = resolver.resolve_druid_seat_voice("sentinel", PROPOSAL, PROMPT)
    assert seated is not None
    assert seated.decision == original.decision == "HOLD"
    assert seated.proposal_digest == original.proposal_digest
    assert seated.prompt_digest == original.prompt_digest
    assert seated.hnc_receipt_id == original.hnc_receipt_id
    assert seated.auris_receipt_id == original.auris_receipt_id
    assert seated.provider_moment_digest == original.provider_moment_digest
    assert seated.source_timestamp == original.source_timestamp
    assert seated.decision_source_id.startswith("celtic:seat_source:")
    assert "celtic_voice[sentinel:otherworld_thresholds:samhain]" in seated.reason

    council = issue_trusted_druidic_council(
        proposal_digest=PROPOSAL,
        prompt_digest=PROMPT,
        auris_node_receipts=nodes,
        resolver=resolver,
        now=NOW,
    )
    assert council["data_status"] == "live"
    assert council["decision"] == "ACCEPT"
    assert next(
        item for item in council["seat_summaries"] if item["seat"] == "sentinel"
    )["decision"] == "HOLD"
    assert sum(
        item["decision"] == "ACCEPT" for item in council["seat_summaries"]
    ) == 3
    assert all(
        item["decision_source_id"].startswith("celtic:seat_source:")
        for item in council["seat_receipts"]
    )
    assert all(council[name] is False for name in FALSE_FLAGS)


def test_celtic_seating_hash_binds_the_delegate_decision_source_receipt() -> None:
    bank = read_canonical_celtic_voice_bank()
    first = CelticSeatedDruidResolver(
        delegate=_Delegate(_nodes(), source_namespace="work-receipt-one"),
        voice_bank_receipt=bank,
        seasonal_gate="lughnasadh",
    )
    second = CelticSeatedDruidResolver(
        delegate=_Delegate(_nodes(), source_namespace="work-receipt-two"),
        voice_bank_receipt=bank,
        seasonal_gate="lughnasadh",
    )

    first_source = first.trusted_druid_seat_bindings()["seer"].decision_source_id
    second_source = second.trusted_druid_seat_bindings()["seer"].decision_source_id

    assert first_source.startswith("celtic:seat_source:")
    assert second_source.startswith("celtic:seat_source:")
    assert first_source != second_source


def test_tampered_voice_bank_cannot_be_seated_even_with_rehashed_receipt() -> None:
    receipt = read_canonical_celtic_voice_bank()
    tampered = copy.deepcopy(receipt)
    tampered["seat_profiles"][0]["description"] = "invented authority"
    causal = {key: value for key, value in tampered.items() if key != "receipt_id"}
    tampered["receipt_id"] = f"celtic:voice_bank:{_sha(causal)}"
    resolver = CelticSeatedDruidResolver(
        delegate=_Delegate(_nodes()),
        voice_bank_receipt=tampered,
        seasonal_gate="beltane",
    )

    with pytest.raises(ValueError, match="canonical_repository_celtic_voice_bank_required"):
        resolver.trusted_druid_seat_bindings()


@pytest.mark.parametrize("flag", FALSE_FLAGS)
def test_voice_bank_cannot_claim_any_governance_or_economic_authority(flag: str) -> None:
    receipt = read_canonical_celtic_voice_bank()
    receipt[flag] = True

    with pytest.raises(ValueError, match="must_be_non_authoritative"):
        validate_celtic_voice_bank_receipt(receipt)
