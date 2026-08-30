from __future__ import annotations

import copy
import hashlib
import inspect
import json
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from aureon.swarm.auris_node_receipts import (
    COHERENCE_METHOD,
    COHERENCE_SCHEMA,
    NODE_SCHEMA,
    ResolvedAurisNodeEvidence,
    issue_auris_node_receipt,
    validate_auris_node_receipt,
    validate_provider_moment,
)
from aureon.swarm.druidic_council import (
    REQUIRED_SEATS,
    build_seat_receipt,
    convene_druidic_council,
)

NOW = 1_786_480_000.0
PROPOSAL = "a" * 64
PROMPT = "b" * 64

INPUT_FALSE_FLAGS = (
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
)
ALL_FALSE_FLAGS = (*INPUT_FALSE_FLAGS, "economic_mutation")


def _sha(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _false_flags(*, node: bool = False) -> dict[str, bool]:
    names = ALL_FALSE_FLAGS if node else INPUT_FALSE_FLAGS
    return dict.fromkeys(names, False)


def _hnc() -> dict[str, Any]:
    memory_id = "hnc:lambda_history:memory-1"
    links = sorted(["provider:hnc:a", "provider:hnc:b", memory_id])
    payload: dict[str, Any] = {
        "data_status": "live",
        "source": "hnc_live_daemon",
        "source_id": "aureon:hnc:live_daemon",
        "source_timestamp": NOW - 10.0,
        "received_at": NOW - 2.0,
        "ts": NOW - 10.0,
        "receipt_type": "hnc_live_field",
        "provider_receipt_type": "hnc_live_field",
        "truth_status": "real_derived",
        "generated_values": False,
        "input_receipt_ids": links,
        "memory_receipt_id": memory_id,
        "memory_canonical_hash": "1" * 64,
        "memory_previous_receipt_id": None,
        "freshness_status": "fresh",
        "equation_inputs_complete": True,
        "step": 12,
        "lambda_t": 0.31,
        "coherence_gamma": 0.81,
        "consciousness_psi": 0.63,
        "symbolic_life_score": 0.72,
        "consciousness_level": "CONNECTED",
        "source_count": 2,
        **_false_flags(),
    }
    fingerprint = {
        "input_receipt_ids": links,
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


def _source_receipt(
    *,
    source_id: str,
    receipt_id: str,
    receipt_type: str,
    source_timestamp: float,
    received_at: float = NOW - 1.0,
    input_receipt_ids: list[str] | None = None,
    truth_status: str = "real_observed",
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "source_timestamp": source_timestamp,
        "received_at": received_at,
        "receipt_id": receipt_id,
        "receipt_type": receipt_type,
        "truth_status": truth_status,
        "generated_values": False,
        "input_receipt_ids": sorted(input_receipt_ids or []),
        **_false_flags(),
    }


def _auris(hnc: Mapping[str, Any]) -> dict[str, Any]:
    schumann = _source_receipt(
        source_id="provider.schumann.measurement",
        receipt_id="schumann:provider:receipt-1",
        receipt_type="provider_measurement",
        source_timestamp=NOW - 8.0,
        input_receipt_ids=["provider:schumann:raw-1"],
    )
    sources = {
        "hnc": _source_receipt(
            source_id=hnc["source_id"],
            receipt_id=hnc["receipt_id"],
            receipt_type=hnc["receipt_type"],
            source_timestamp=hnc["source_timestamp"],
            received_at=hnc["received_at"],
            input_receipt_ids=list(hnc["input_receipt_ids"]),
            truth_status=hnc["truth_status"],
        ),
        "space_weather": _source_receipt(
            source_id="provider.noaa.space_weather",
            receipt_id="space-weather:provider:receipt-1",
            receipt_type="provider_measurement",
            source_timestamp=NOW - 9.0,
            input_receipt_ids=["provider:noaa:raw-1"],
        ),
        "schumann": schumann,
        "earth_blessing": _source_receipt(
            source_id="aureon:planetary:earth_blessing",
            receipt_id="earth-blessing:derived:receipt-1",
            receipt_type="planetary_earth_blessing",
            source_timestamp=NOW - 7.0,
            input_receipt_ids=[schumann["receipt_id"]],
            truth_status="real_derived",
        ),
        "earth_gate": _source_receipt(
            source_id="aureon:planetary:earth_gate",
            receipt_id="earth-gate:derived:receipt-1",
            receipt_type="earth_resonance_gate_evidence",
            source_timestamp=NOW - 6.0,
            input_receipt_ids=[schumann["receipt_id"]],
            truth_status="real_derived",
        ),
    }
    links = sorted(
        {
            *(item["receipt_id"] for item in sources.values()),
            *(link for item in sources.values() for link in item["input_receipt_ids"]),
        }
    )
    payload: dict[str, Any] = {
        "data_status": "live",
        "source_id": "aureon:auris:throne",
        "source_timestamp": NOW - 6.0,
        "received_at": NOW - 1.0,
        "receipt_type": "auris_cosmic_state",
        "provider_receipt_type": "auris_cosmic_state",
        "truth_status": "real_derived",
        "generated_values": False,
        "data_available": True,
        "input_receipt_ids": links,
        "hnc_receipt_id": hnc["receipt_id"],
        "planetary_receipt_ids": sorted(
            item["receipt_id"] for name, item in sources.items() if name != "hnc"
        ),
        "source_receipts": sources,
        "sources_live": sorted(sources),
        "sources_unavailable": [],
        "equation_inputs_complete": True,
        "gate_open": True,
        "advisory": "TRADE",
        "reasoning": ["complete linked evidence"],
        "lambda_t": 1.23,
        "coherence_gamma": 0.90,
        "consciousness_psi": 0.40,
        "cosmic_score": 0.74,
        "earth_blessing": 0.82,
        **_false_flags(),
    }
    fingerprint = {
        "input_receipt_ids": links,
        "lambda_t": payload["lambda_t"],
        "coherence_gamma": payload["coherence_gamma"],
        "consciousness_psi": payload["consciousness_psi"],
        "cosmic_score": payload["cosmic_score"],
        "earth_blessing": payload["earth_blessing"],
        "gate_open": payload["gate_open"],
        "advisory": payload["advisory"],
    }
    payload["receipt_id"] = f"auris:cosmic_state:{_sha(fingerprint)[:24]}"
    return payload


def _measurement(
    *,
    seat: str,
    agent_id: str,
    source_id: str,
    hnc: Mapping[str, Any],
    auris: Mapping[str, Any],
    levels: list[float] | None = None,
    magnitudes: list[float] | None = None,
) -> dict[str, Any]:
    moment = validate_provider_moment(hnc, auris, now=NOW)
    operator_levels = levels or [0.1, 0.3, 0.7, 0.9]
    action_magnitudes = magnitudes or [0.2, 0.4, 0.8, 1.0]
    window_material = {
        "operator_levels": operator_levels,
        "action_magnitudes": action_magnitudes,
        "window_size": len(operator_levels),
    }
    payload: dict[str, Any] = {
        "schema": COHERENCE_SCHEMA,
        "receipt_type": "agent_coherence_measurement",
        "receipt_id": None,
        "source_id": source_id,
        "seat": seat,
        "agent_id": agent_id,
        "measurement_method": COHERENCE_METHOD,
        "operator_levels": operator_levels,
        "action_magnitudes": action_magnitudes,
        "window_size": len(operator_levels),
        "sample_count": len(operator_levels),
        "window_digest": _sha(window_material),
        "hnc_receipt_id": moment.hnc_receipt_id,
        "auris_receipt_id": moment.auris_receipt_id,
        "provider_receipt_ids": list(moment.provider_receipt_ids),
        "provider_moment_digest": moment.provider_moment_digest,
        "source_timestamp": moment.source_timestamp,
        "received_at": NOW - 1.0,
        "input_receipt_ids": sorted(
            {
                moment.hnc_receipt_id,
                moment.auris_receipt_id,
                *moment.provider_receipt_ids,
            }
        ),
        "data_status": "live",
        "truth_status": "real_derived",
        "freshness_status": "fresh",
        "equation_inputs_complete": True,
        "generated_values": False,
        **_false_flags(node=True),
    }
    causal = {
        key: payload[key]
        for key in sorted(set(payload) - {"receipt_id", "received_at"})
    }
    payload["receipt_id"] = f"auris:coherence_measurement:{_sha(causal)}"
    return payload


class _Resolver:
    def __init__(
        self,
        *,
        hnc: Mapping[str, Any] | None = None,
        auris: Mapping[str, Any] | None = None,
        levels: list[float] | None = None,
        magnitudes: list[float] | None = None,
        forced_seat: str | None = None,
    ) -> None:
        self.hnc = copy.deepcopy(hnc or _hnc())
        self.auris = copy.deepcopy(auris or _auris(self.hnc))
        self.levels = levels
        self.magnitudes = magnitudes
        self.forced_seat = forced_seat

    def resolve_auris_node_evidence(
        self,
        seat: str,
    ) -> ResolvedAurisNodeEvidence:
        resolved_seat = self.forced_seat or seat
        agent_id = f"agent-{resolved_seat}"
        source_id = f"aureon:coherence-meter:{agent_id}"
        return ResolvedAurisNodeEvidence(
            resolver_id="aureon:trusted-council-runtime:v1",
            coherence_source_id=source_id,
            seat=resolved_seat,
            agent_id=agent_id,
            hnc_evidence=copy.deepcopy(self.hnc),
            auris_evidence=copy.deepcopy(self.auris),
            coherence_evidence=_measurement(
                seat=resolved_seat,
                agent_id=agent_id,
                source_id=source_id,
                hnc=self.hnc,
                auris=self.auris,
                levels=self.levels,
                magnitudes=self.magnitudes,
            ),
        )


class _MutatingResolver(_Resolver):
    def __init__(self, mutation: str) -> None:
        super().__init__()
        self.mutation = mutation

    def resolve_auris_node_evidence(
        self,
        seat: str,
    ) -> ResolvedAurisNodeEvidence:
        resolved = super().resolve_auris_node_evidence(seat)
        hnc = copy.deepcopy(resolved.hnc_evidence)
        auris = copy.deepcopy(resolved.auris_evidence)
        measurement = copy.deepcopy(resolved.coherence_evidence)
        if self.mutation == "hnc_prefix_only":
            hnc = {"receipt_id": "hnc:live_field:self-attested"}
        elif self.mutation == "auris_prefix_only":
            auris = {"receipt_id": "auris:cosmic_state:self-attested"}
        elif self.mutation == "hnc_hash":
            hnc["receipt_id"] = "hnc:live_field:" + "f" * 24
        elif self.mutation == "auris_hash":
            auris["receipt_id"] = "auris:cosmic_state:" + "f" * 24
        elif self.mutation == "self_attested_gamma":
            measurement["gamma"] = 1.0
        elif self.mutation == "measurement_tamper":
            measurement["operator_levels"][0] = 0.99
        elif self.mutation == "provider_moment":
            measurement["provider_moment_digest"] = "f" * 64
        elif self.mutation == "source_time":
            measurement["source_timestamp"] -= 1.0
        else:
            raise AssertionError(self.mutation)
        return ResolvedAurisNodeEvidence(
            resolver_id=resolved.resolver_id,
            coherence_source_id=resolved.coherence_source_id,
            seat=resolved.seat,
            agent_id=resolved.agent_id,
            hnc_evidence=hnc,
            auris_evidence=auris,
            coherence_evidence=measurement,
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


def test_public_issuer_does_not_accept_identity_gamma_ids_or_timestamps() -> None:
    parameters = inspect.signature(issue_auris_node_receipt).parameters
    assert set(parameters) == {"seat", "resolver", "now", "max_age_s"}
    assert not {
        "agent_id",
        "gamma",
        "hnc_receipt_id",
        "auris_receipt_id",
        "source_timestamp",
    }.intersection(parameters)


def test_live_node_derives_gamma_identity_lineage_and_provider_moment() -> None:
    hnc = _hnc()
    auris = _auris(hnc)
    moment = validate_provider_moment(hnc, auris, now=NOW)
    receipt = issue_auris_node_receipt(
        seat="seer",
        resolver=_Resolver(hnc=hnc, auris=auris),
        now=NOW,
    )

    assert receipt["schema"] == NODE_SCHEMA
    assert receipt["data_status"] == "live"
    assert receipt["seat"] == "seer"
    assert receipt["agent_id"] == "agent-seer"
    assert receipt["gamma"] == pytest.approx(1.0)
    assert receipt["source_timestamp"] == moment.source_timestamp
    assert receipt["provider_receipt_ids"] == list(moment.provider_receipt_ids)
    assert receipt["provider_moment_digest"] == moment.provider_moment_digest
    assert receipt["receipt_id"].startswith("auris:node:")
    assert all(receipt[name] is False for name in ALL_FALSE_FLAGS)
    assert receipt["route_authorization_required"] is True
    assert validate_auris_node_receipt(receipt, now=NOW) == receipt


def test_node_id_excludes_only_local_derivation_clock() -> None:
    resolver = _Resolver()
    first = issue_auris_node_receipt(seat="seer", resolver=resolver, now=NOW)
    second = issue_auris_node_receipt(seat="seer", resolver=resolver, now=NOW + 1.0)

    assert first["receipt_id"] == second["receipt_id"]
    assert first["derived_at"] != second["derived_at"]


@pytest.mark.parametrize(
    "mutation",
    [
        "hnc_prefix_only",
        "auris_prefix_only",
        "hnc_hash",
        "auris_hash",
        "self_attested_gamma",
        "measurement_tamper",
        "provider_moment",
        "source_time",
    ],
)
def test_prefix_only_self_attested_tampered_or_unlinked_inputs_are_no_data(
    mutation: str,
) -> None:
    receipt = issue_auris_node_receipt(
        seat="seer",
        resolver=_MutatingResolver(mutation),
        now=NOW,
    )

    assert receipt["data_status"] == "no_data"
    assert receipt["receipt_id"] is None
    assert receipt["provider_receipt_ids"] == []
    assert receipt["input_receipt_ids"] == []
    assert all(receipt[name] is False for name in ALL_FALSE_FLAGS)
    _assert_numeric_free(receipt)
    assert validate_auris_node_receipt(receipt, now=NOW) == receipt


def test_stale_or_negative_coherence_is_numeric_free_no_data() -> None:
    stale = issue_auris_node_receipt(
        seat="seer",
        resolver=_Resolver(),
        now=NOW + 400.0,
    )
    negative = issue_auris_node_receipt(
        seat="seer",
        resolver=_Resolver(
            levels=[0.1, 0.3, 0.7, 0.9],
            magnitudes=[1.0, 0.8, 0.4, 0.2],
        ),
        now=NOW,
    )

    for receipt in (stale, negative):
        assert receipt["data_status"] == "no_data"
        _assert_numeric_free(receipt)


def test_stable_seat_binding_mismatch_fails_closed() -> None:
    receipt = issue_auris_node_receipt(
        seat="sentinel",
        resolver=_Resolver(forced_seat="seer"),
        now=NOW,
    )
    assert receipt["data_status"] == "no_data"
    assert receipt["agent_id"] is None


def test_strict_node_validator_rejects_extra_or_tampered_fields() -> None:
    receipt = issue_auris_node_receipt(
        seat="seer",
        resolver=_Resolver(),
        now=NOW,
    )
    extra = {**receipt, "custom_eligible": False}
    gamma = {**receipt, "gamma": 0.5}

    with pytest.raises(ValueError, match="exact_live_node_schema_required"):
        validate_auris_node_receipt(extra, now=NOW)
    with pytest.raises(ValueError, match="hash_mismatch"):
        validate_auris_node_receipt(gamma, now=NOW)


def test_four_authenticated_nodes_share_one_exact_provider_moment_and_convene() -> None:
    resolver = _Resolver()
    nodes = {
        seat: issue_auris_node_receipt(seat=seat, resolver=resolver, now=NOW)
        for seat in REQUIRED_SEATS
    }
    assert {node["source_timestamp"] for node in nodes.values()} == {NOW - 6.0}
    assert len({node["receipt_id"] for node in nodes.values()}) == len(REQUIRED_SEATS)
    assert len({node["seat_binding_digest"] for node in nodes.values()}) == len(
        REQUIRED_SEATS
    )
    seats = [
        build_seat_receipt(
            seat=seat,
            agent_id=node["agent_id"],
            decision="ACCEPT",
            reason=f"{seat} validated its discipline boundary",
            gamma=node["gamma"],
            proposal_digest=PROPOSAL,
            prompt_digest=PROMPT,
            hnc_receipt_id=node["hnc_receipt_id"],
            auris_receipt_id=node["auris_receipt_id"],
            auris_node_receipt_id=node["receipt_id"],
            source_timestamp=node["source_timestamp"],
            derived_at=NOW,
        )
        for seat, node in nodes.items()
    ]
    council = convene_druidic_council(
        proposal_digest=PROPOSAL,
        prompt_digest=PROMPT,
        hnc_receipt_id=nodes["seer"]["hnc_receipt_id"],
        auris_receipt_id=nodes["seer"]["auris_receipt_id"],
        seat_receipts=seats,
        now=NOW,
    )

    assert council["decision"] == "ACCEPT"
    assert council["data_status"] == "live"
    assert council["route_authorization_required"] is True
