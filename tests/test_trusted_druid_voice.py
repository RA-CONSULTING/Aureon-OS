from __future__ import annotations

import copy
import hashlib
import inspect
import json
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from aureon.governance.druid_voice import (
    DruidSeatIssuerBinding,
    ResolvedDruidSeatVoice,
    issue_trusted_druidic_council,
    validate_trusted_druidic_council_receipt,
)
from aureon.swarm.auris_node_receipts import (
    COHERENCE_METHOD,
    NODE_SCHEMA,
    validate_auris_node_receipt,
)
from aureon.swarm.druidic_council import (
    REQUIRED_SEATS,
    TRUSTED_SEAT_SCHEMA,
    build_seat_receipt,
    convene_druidic_council,
    validate_council_receipt,
)

NOW = 1_786_480_000.0
PROPOSAL = "a" * 64
PROMPT = "b" * 64
HNC = "hnc:live_field:trusted-cycle"
AURIS = "auris:cosmic_state:trusted-cycle"
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
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _node(seat: str, *, gamma: float = 0.90) -> dict[str, Any]:
    agent_id = f"agent-{seat}"
    coherence_id = f"auris:coherence_measurement:{seat}-measurement"
    resolver_id = "aureon:trusted-node-runtime:v1"
    causal: dict[str, Any] = {
        "schema": NODE_SCHEMA,
        "receipt_type": "auris_node",
        "seat": seat,
        "agent_id": agent_id,
        "resolver_id": resolver_id,
        "coherence_source_id": f"aureon:coherence-meter:{seat}",
        "seat_binding_digest": _sha(
            {
                "resolver_id": resolver_id,
                "seat": seat,
                "agent_id": agent_id,
            }
        ),
        "gamma": gamma,
        "measurement_method": COHERENCE_METHOD,
        "coherence_measurement_receipt_id": coherence_id,
        "hnc_receipt_id": HNC,
        "auris_receipt_id": AURIS,
        "provider_receipt_ids": list(PROVIDERS),
        "provider_moment_digest": MOMENT_DIGEST,
        "source_timestamp": NOW - 5.0,
        "input_receipt_ids": sorted(
            {HNC, AURIS, coherence_id, *PROVIDERS}
        ),
        "data_status": "live",
        "truth_status": "real_derived",
        "freshness_status": "fresh",
        "equation_inputs_complete": True,
        "generated_values": False,
        "route_authorization_required": True,
        **dict.fromkeys(FALSE_FLAGS, False),
    }
    receipt = dict(causal)
    receipt["receipt_id"] = f"auris:node:{_sha(causal)}"
    receipt["derived_at"] = NOW - 1.0
    assert validate_auris_node_receipt(receipt, now=NOW) == receipt
    return receipt


def _rehash_node(node: dict[str, Any]) -> None:
    causal = {
        key: value
        for key, value in node.items()
        if key not in {"receipt_id", "derived_at"}
    }
    node["receipt_id"] = f"auris:node:{_sha(causal)}"


def _nodes() -> list[dict[str, Any]]:
    return [_node(seat) for seat in REQUIRED_SEATS]


class _Resolver:
    def __init__(
        self,
        nodes: Sequence[Mapping[str, Any]],
        *,
        issuer_mode: str = "single",
        mutation: str | None = None,
        decisions: Mapping[str, str] | None = None,
    ) -> None:
        self.nodes = {item["seat"]: copy.deepcopy(item) for item in nodes}
        self.issuer_mode = issuer_mode
        self.mutation = mutation
        self.decisions = dict(decisions or {})

    def _issuer(self, seat: str) -> str:
        if self.issuer_mode == "single":
            return "druid:council:issuer:v1"
        if self.issuer_mode == "per-seat":
            return f"druid:{seat}:issuer:v1"
        if self.issuer_mode == "partial":
            return "druid:shared:issuer:v1" if seat in REQUIRED_SEATS[:2] else (
                f"druid:{seat}:issuer:v1"
            )
        raise AssertionError(self.issuer_mode)

    def trusted_druid_seat_bindings(
        self,
    ) -> Mapping[str, DruidSeatIssuerBinding]:
        bindings = {
            seat: DruidSeatIssuerBinding(
                resolver_id="aureon:trusted-druid-runtime:v1",
                issuer_id=self._issuer(seat),
                decision_source_id=f"druid:decision-source:{seat}:v1",
                seat=seat,
                agent_id=self.nodes[seat]["agent_id"],
            )
            for seat in REQUIRED_SEATS
        }
        if self.mutation == "binding_seat":
            bindings["sentinel"] = DruidSeatIssuerBinding(
                resolver_id="aureon:trusted-druid-runtime:v1",
                issuer_id=self._issuer("sentinel"),
                decision_source_id="druid:decision-source:sentinel:v1",
                seat="seer",
                agent_id=self.nodes["sentinel"]["agent_id"],
            )
        return bindings

    def resolve_druid_seat_voice(
        self,
        seat: str,
        proposal_digest: str,
        prompt_digest: str,
    ) -> ResolvedDruidSeatVoice:
        if self.mutation == "exception" and seat == "weaver":
            raise RuntimeError("trusted store unavailable")
        node = self.nodes[seat]
        resolved = ResolvedDruidSeatVoice(
            resolver_id="aureon:trusted-druid-runtime:v1",
            issuer_id=self._issuer(seat),
            decision_source_id=f"druid:decision-source:{seat}:v1",
            seat=seat,
            agent_id=node["agent_id"],
            decision=self.decisions.get(seat, "ACCEPT"),
            reason=f"{seat} verified its discipline boundary",
            proposal_digest=proposal_digest,
            prompt_digest=prompt_digest,
            auris_node_receipt_id=node["receipt_id"],
            hnc_receipt_id=node["hnc_receipt_id"],
            auris_receipt_id=node["auris_receipt_id"],
            provider_receipt_ids=tuple(node["provider_receipt_ids"]),
            provider_moment_digest=node["provider_moment_digest"],
            source_timestamp=node["source_timestamp"],
        )
        if self.mutation == "proposal" and seat == "seer":
            return ResolvedDruidSeatVoice(
                **{**resolved.__dict__, "proposal_digest": "d" * 64}
            )
        if self.mutation == "node_id" and seat == "keeper":
            return ResolvedDruidSeatVoice(
                **{
                    **resolved.__dict__,
                    "auris_node_receipt_id": "auris:node:wrong",
                }
            )
        return resolved


def _issue(
    nodes: Sequence[Mapping[str, Any]],
    resolver: _Resolver,
    *,
    now: float = NOW,
) -> dict[str, Any]:
    return issue_trusted_druidic_council(
        proposal_digest=PROPOSAL,
        prompt_digest=PROMPT,
        auris_node_receipts=nodes,
        resolver=resolver,
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


def test_public_composer_accepts_no_scalar_identity_gamma_ids_or_timestamp() -> None:
    parameters = inspect.signature(issue_trusted_druidic_council).parameters
    assert set(parameters) == {
        "proposal_digest",
        "prompt_digest",
        "auris_node_receipts",
        "resolver",
        "now",
        "max_age_s",
    }
    assert not {
        "seat",
        "agent_id",
        "gamma",
        "issuer_id",
        "hnc_receipt_id",
        "auris_receipt_id",
        "source_timestamp",
    }.intersection(parameters)


@pytest.mark.parametrize("issuer_mode", ["single", "per-seat"])
def test_four_full_nodes_and_allowlisted_issuers_mint_a_valid_council(
    issuer_mode: str,
) -> None:
    nodes = _nodes()
    receipt = _issue(nodes, _Resolver(nodes, issuer_mode=issuer_mode))

    assert receipt["decision"] == "ACCEPT"
    assert receipt["data_status"] == "live"
    assert [item["seat"] for item in receipt["seat_receipts"]] == list(
        REQUIRED_SEATS
    )
    assert all(
        item["schema"] == TRUSTED_SEAT_SCHEMA
        for item in receipt["seat_receipts"]
    )
    embedded = {
        item["seat"]: item["auris_node_receipt"]
        for item in receipt["seat_receipts"]
    }
    assert embedded == {node["seat"]: node for node in nodes}
    assert all(
        link in receipt["input_receipt_ids"]
        for node in nodes
        for link in node["input_receipt_ids"]
    )
    assert all(receipt[name] is False for name in FALSE_FLAGS)
    assert validate_council_receipt(receipt, now=NOW) == receipt
    assert validate_trusted_druidic_council_receipt(receipt, now=NOW) == receipt


def test_gamma_identity_lineage_and_decision_are_derived_from_trusted_bodies() -> None:
    nodes = _nodes()
    nodes[0] = _node("seer", gamma=0.79)
    receipt = _issue(
        nodes,
        _Resolver(nodes, decisions={"seer": "ABORT"}),
    )

    seer = receipt["seat_receipts"][0]
    assert seer["agent_id"] == nodes[0]["agent_id"]
    assert seer["gamma"] == nodes[0]["gamma"]
    assert seer["voice_band"] == "ADVISORY"
    assert seer["voice_weight"] == 0.0
    assert seer["decision"] == "ABORT"
    assert receipt["decision"] == "ACCEPT"


@pytest.mark.parametrize(
    "failure",
    [
        "missing",
        "tampered_node",
        "stale",
        "mixed_moment",
        "duplicate_agent",
        "resolver_exception",
        "resolver_proposal",
        "resolver_node_id",
        "binding_seat",
        "partial_issuer",
    ],
)
def test_missing_tampered_stale_mismatched_or_untrusted_inputs_hold_no_data(
    failure: str,
) -> None:
    nodes = _nodes()
    mutation = None
    issuer_mode = "single"
    now = NOW
    if failure == "missing":
        nodes.pop()
    elif failure == "tampered_node":
        nodes[0]["gamma"] = 0.99
    elif failure == "stale":
        now += 400.0
    elif failure == "mixed_moment":
        nodes[0]["provider_moment_digest"] = "d" * 64
        _rehash_node(nodes[0])
    elif failure == "duplicate_agent":
        nodes[1]["agent_id"] = nodes[0]["agent_id"]
        nodes[1]["seat_binding_digest"] = _sha(
            {
                "resolver_id": nodes[1]["resolver_id"],
                "seat": nodes[1]["seat"],
                "agent_id": nodes[1]["agent_id"],
            }
        )
        _rehash_node(nodes[1])
    elif failure == "resolver_exception":
        mutation = "exception"
    elif failure == "resolver_proposal":
        mutation = "proposal"
    elif failure == "resolver_node_id":
        mutation = "node_id"
    elif failure == "binding_seat":
        mutation = "binding_seat"
    elif failure == "partial_issuer":
        issuer_mode = "partial"
    else:
        raise AssertionError(failure)

    receipt = _issue(
        nodes,
        _Resolver(nodes, mutation=mutation, issuer_mode=issuer_mode),
        now=now,
    )

    assert receipt["decision"] == "HOLD"
    assert receipt["data_status"] == "no_data"
    assert receipt["receipt_id"] is None
    assert receipt["input_receipt_ids"] == []
    assert all(receipt[name] is False for name in FALSE_FLAGS)
    _assert_numeric_free(receipt)


def test_downstream_council_validator_revalidates_embedded_full_node() -> None:
    nodes = _nodes()
    receipt = _issue(nodes, _Resolver(nodes))
    receipt["seat_receipts"][0]["auris_node_receipt"]["gamma"] = 0.99

    with pytest.raises(ValueError):
        validate_council_receipt(receipt, now=NOW)


def test_legacy_council_is_not_accepted_as_trusted_composition() -> None:
    seats = [
        build_seat_receipt(
            seat=seat,
            agent_id=f"legacy-agent-{seat}",
            decision="ACCEPT",
            reason=f"{seat} legacy structural receipt",
            gamma=0.90,
            proposal_digest=PROPOSAL,
            prompt_digest=PROMPT,
            hnc_receipt_id=HNC,
            auris_receipt_id=AURIS,
            auris_node_receipt_id=f"auris:node:legacy-{seat}",
            source_timestamp=NOW - 5.0,
            derived_at=NOW,
        )
        for seat in REQUIRED_SEATS
    ]
    legacy = convene_druidic_council(
        proposal_digest=PROPOSAL,
        prompt_digest=PROMPT,
        hnc_receipt_id=HNC,
        auris_receipt_id=AURIS,
        seat_receipts=seats,
        now=NOW,
    )
    assert validate_council_receipt(legacy, now=NOW) == legacy

    with pytest.raises(ValueError):
        validate_trusted_druidic_council_receipt(legacy, now=NOW)
