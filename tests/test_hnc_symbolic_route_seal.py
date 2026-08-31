import copy
import json

import pytest

from aureon.harmonic.hnc_quantum_packet_crypto import (
    HNCPacketError,
    build_hnc_quantum_packet,
    build_hnc_swarm_packet,
    decode_hnc_quantum_packet,
    packet_public_summary,
    validate_hnc_packet_contract,
)
from aureon.harmonic.hnc_symbolic_route_seal import (
    build_symbolic_route_seal,
    load_symbolic_catalog_manifest,
    symbolic_route_public_summary,
    validate_symbolic_route_seal,
)

MASTER_KEY = b"Q" * 32


def test_symbolic_route_seal_loads_rune_star_and_research_catalogs():
    manifest = load_symbolic_catalog_manifest()
    seal = build_symbolic_route_seal(
        purpose="repo:singularity_vault",
        operator_aad={"root_sha256": "abc"},
        hnc_context={"domain": "threshold_people_symbolic_packet"},
    )
    summary = symbolic_route_public_summary(seal)

    assert manifest["summary"]["catalogs_present"] >= 4
    assert manifest["summary"]["symbol_count"] >= 24
    assert validate_symbolic_route_seal(seal)["valid"] is True
    assert summary["valid"] is True
    assert summary["threshold_layer"] == "threshold_people_crossing_from_observation_to_authenticated_action"
    assert "AES-GCM" in seal["security_boundary"]["does_not_replace"]


def test_symbolic_route_seal_detects_tamper():
    seal = build_symbolic_route_seal(purpose="hnc:test")
    tampered = copy.deepcopy(seal)
    tampered["route"]["selected_rune"]["id"] = "attacker-rune"

    validation = validate_symbolic_route_seal(tampered)

    assert validation["valid"] is False
    assert "symbolic_route_hash_mismatch" in validation["reasons"]


def test_hnc_packet_binds_symbolic_route_to_authenticated_context():
    packet = build_hnc_quantum_packet(
        "threshold-secret",
        MASTER_KEY,
        purpose="hnc:symbolic-route",
        operator_aad={"intent": "rune_star_route"},
        hnc_context={"domain": "maeshowe_seer_threshold_people"},
    )
    route = packet["metadata"]["hnc_alignment"]["symbolic_route_seal"]

    assert validate_hnc_packet_contract(packet)["valid"] is True
    assert validate_symbolic_route_seal(route)["valid"] is True
    assert packet_public_summary(packet)["symbolic_route"]["valid"] is True
    assert "threshold-secret" not in json.dumps(packet)

    tampered = copy.deepcopy(packet)
    tampered["metadata"]["hnc_alignment"]["symbolic_route_seal"]["route"]["selected_rune"]["name"] = "False Rune"

    with pytest.raises(HNCPacketError):
        decode_hnc_quantum_packet(tampered, MASTER_KEY)


def test_hnc_swarm_packet_carries_symbolic_route_seal():
    agents = {
        "seer": b"S" * 32,
        "lyra": b"L" * 32,
        "king": b"R" * 32,
    }
    packet = build_hnc_swarm_packet(
        "swarm-threshold-secret",
        agents,
        purpose="repo:singularity_vault",
        operator_aad={"intent": "two_way_symbolic_route"},
    )
    summary = packet_public_summary(packet)

    assert validate_hnc_packet_contract(packet)["valid"] is True
    assert summary["symbolic_route"]["valid"] is True
    assert summary["symbolic_route"]["rune"]
