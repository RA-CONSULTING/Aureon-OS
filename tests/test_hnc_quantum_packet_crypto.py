import base64
import copy
import json
import zlib
from pathlib import Path

import pytest

import aureon.harmonic.hnc_quantum_packet_crypto as hnc_crypto
from aureon.core.hnc_params import HNCParams
from aureon.harmonic.hnc_quantum_packet_crypto import (
    DEFAULT_GEOMETRY,
    ENV_PACKET_PREFIX,
    HNC_PACKET_EVIDENCE_WRITE_HOLD,
    HNCPacketError,
    build_hnc_alignment_context,
    build_hnc_packet_evidence,
    build_hnc_quantum_packet,
    build_hnc_swarm_packet,
    canonical_json_bytes,
    decode_env_packet,
    decode_hnc_quantum_packet,
    decode_hnc_swarm_packet,
    encode_env_packet,
    env_packet_summary,
    is_env_packet,
    normalize_hnc_key_material,
    packet_master_key_from_env,
    packet_public_summary,
    reassemble_hnc_probability_fragments,
    run_hnc_packet_breaker_checks,
    run_hnc_swarm_breaker_checks,
    sha256_hex,
    stream_hnc_probability_fragments,
    validate_hnc_packet_contract,
    write_hnc_packet_evidence,
)

MASTER_KEY = b"K" * 32
AGENT_KEYS = {
    "seer": b"S" * 32,
    "lyra": b"L" * 32,
    "king": b"R" * 32,
}
LEGACY_V1_FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures" / "hnc_legacy_v1_known_answers.json").read_text(
        encoding="utf-8"
    )
)


def _base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _fixture_metadata(encoded: str) -> dict[str, object]:
    return json.loads(zlib.decompress(base64.b64decode(encoded)).decode("utf-8"))


def _fixture_key(spec: dict[str, str]) -> bytes | str:
    if spec["key_kind"] == "bytes_b64":
        return base64.b64decode(spec["key_value"])
    return spec["key_value"]


def _legacy_single_fixture(vector: dict[str, str]) -> dict[str, object]:
    fixture = LEGACY_V1_FIXTURES["single"]
    return {
        "magic": "AUREON-HNC-QP",
        "schema_version": 1,
        "metadata": _fixture_metadata(fixture["metadata_zlib_b64"]),
        "operator_aad": fixture["operator_aad"],
        "nonce_b64": fixture["nonce_b64"],
        "ciphertext_b64": vector["ciphertext_b64"],
        "packet_sha256": vector["packet_sha256"],
    }


def _legacy_swarm_fixture() -> tuple[dict[str, object], dict[str, bytes | str]]:
    fixture = LEGACY_V1_FIXTURES["swarm"]
    packet = {
        "magic": "AUREON-HNC-QP",
        "schema_version": 1,
        "metadata": _fixture_metadata(fixture["metadata_zlib_b64"]),
        "operator_aad": fixture["operator_aad"],
        "nonce_b64": fixture["nonce_b64"],
        "ciphertext_b64": fixture["ciphertext_b64"],
        "packet_sha256": fixture["packet_sha256"],
        "swarm_locknotes": fixture["locknotes"],
    }
    keys = {
        agent_id: _fixture_key(spec)
        for agent_id, spec in fixture["agent_keys"].items()
    }
    return packet, keys


def test_hnc_quantum_packet_round_trips_without_exposing_plaintext():
    packet = build_hnc_quantum_packet(
        "kraken-secret-value",
        MASTER_KEY,
        purpose="env:KRAKEN_API_SECRET",
        operator_aad={"env_key": "KRAKEN_API_SECRET"},
    )

    packet_text = json.dumps(packet)
    validation = validate_hnc_packet_contract(packet)
    decoded = decode_hnc_quantum_packet(
        packet,
        MASTER_KEY,
        expected_purpose="env:KRAKEN_API_SECRET",
        expected_operator_aad={"env_key": "KRAKEN_API_SECRET"},
    )

    assert validation["valid"] is True
    assert validation["auris_node_count"] == 9
    assert decoded.text() == "kraken-secret-value"
    assert "kraken-secret-value" not in packet_text
    assert decoded.decode_report["packet_contract"]["valid"] is True


def test_hnc_packet_rejects_geometry_tamper():
    packet = build_hnc_quantum_packet("secret", MASTER_KEY)
    packet["metadata"]["hnc_alignment"]["geometry"]["profit_anchor_hz"] = 189.0

    with pytest.raises(HNCPacketError):
        decode_hnc_quantum_packet(packet, MASTER_KEY)

    intact = build_hnc_quantum_packet("secret", MASTER_KEY)
    with pytest.raises(HNCPacketError, match="unexpected_packet_purpose"):
        decode_hnc_quantum_packet(intact, MASTER_KEY, expected_purpose="")


def test_env_packet_round_trip_and_summary():
    token = encode_env_packet("binance-secret", MASTER_KEY, env_key="BINANCE_API_SECRET")
    summary = env_packet_summary(token)

    assert token.startswith(ENV_PACKET_PREFIX)
    assert summary["encoded"] is True
    assert summary["valid_contract"] is True
    assert decode_env_packet(token, MASTER_KEY, env_key="BINANCE_API_SECRET") == "binance-secret"
    assert "binance-secret" not in token


def test_evidence_builder_derives_fixed_metadata_without_tokens_or_plaintext():
    plaintext = "credential-value-must-not-escape"
    token = encode_env_packet(plaintext, MASTER_KEY, env_key="BINANCE_API_SECRET")

    evidence = build_hnc_packet_evidence({"BINANCE_API_SECRET": token})
    rendered = json.dumps(evidence, sort_keys=True)

    assert set(evidence) == {"schema_version", "generated_at", "evidence", "secret_policy"}
    assert plaintext not in rendered
    assert token not in rendered
    assert evidence["evidence"]["updated_keys"] == ["BINANCE_API_SECRET"]
    assert evidence["evidence"]["encrypted_keys"] == ["BINANCE_API_SECRET"]
    assert set(evidence["evidence"]["packet_summaries"]["BINANCE_API_SECRET"]) == {
        "encoded",
        "format",
        "valid_contract",
        "purpose",
        "packet_sha256",
        "hnc_alignment_sha256",
        "legacy_key_derivation_profile",
        "blockers",
    }


def test_evidence_writer_holds_before_any_path_creation(tmp_path: Path):
    destination = tmp_path / "must-not-exist" / "evidence.json"

    with pytest.raises(HNCPacketError, match=HNC_PACKET_EVIDENCE_WRITE_HOLD):
        write_hnc_packet_evidence({"arbitrary": "credential-value"}, destination)

    assert not destination.parent.exists()


def test_evidence_builder_rejects_token_relabeling_across_env_keys():
    token = encode_env_packet("secret", MASTER_KEY, env_key="KRAKEN_API_SECRET")

    with pytest.raises(HNCPacketError, match="evidence_env_packet_binding_invalid"):
        build_hnc_packet_evidence({"BINANCE_API_SECRET": token})


def test_breaker_checks_reject_all_tamper_attempts():
    packet = build_hnc_quantum_packet("capital-password", MASTER_KEY, purpose="env:CAPITAL_PASSWORD")
    report = run_hnc_packet_breaker_checks(packet, MASTER_KEY)

    assert report["passed"] is True
    assert {check["name"] for check in report["checks"]} == {
        "ciphertext_bit_flip",
        "geometry_frequency_tamper",
        "purpose_tamper",
        "operator_aad_tamper",
        "packet_hash_tamper",
        "temporal_fragment_missing",
        "temporal_fragment_tamper",
    }


def test_probability_fragments_reassemble_before_decode():
    packet = build_hnc_quantum_packet("superposition-secret", MASTER_KEY, purpose="hnc:test")
    fragments = stream_hnc_probability_fragments(packet, fragment_size=256)

    assert len(fragments) > 1
    assert all(fragment["stream_type"] == "hnc_temporal_probability_fragment" for fragment in fragments)
    assert "superposition-secret" not in json.dumps(fragments)
    assert round(sum(fragment["probability_weight"] for fragment in fragments), 6) == 1.0

    reassembled = reassemble_hnc_probability_fragments(list(reversed(fragments)))
    decoded = decode_hnc_quantum_packet(reassembled, MASTER_KEY, expected_purpose="hnc:test")

    assert reassembled["packet_sha256"] == packet["packet_sha256"]
    assert decoded.text() == "superposition-secret"


def test_probability_fragments_reject_missing_piece():
    packet = build_hnc_quantum_packet("cannot-collapse-yet", MASTER_KEY, purpose="hnc:test")
    fragments = stream_hnc_probability_fragments(packet, fragment_size=256)

    with pytest.raises(HNCPacketError):
        reassemble_hnc_probability_fragments(fragments[:-1])


def test_hnc_swarm_packet_requires_two_agent_locknotes():
    agents = AGENT_KEYS
    packet = build_hnc_swarm_packet(
        "swarm-secret",
        agents,
        purpose="hnc:swarm",
        operator_aad={"intent": "two_way_security"},
    )

    with pytest.raises(HNCPacketError):
        decode_hnc_swarm_packet(packet, {"seer": agents["seer"]}, expected_purpose="hnc:swarm")

    decoded = decode_hnc_swarm_packet(
        packet,
        {"seer": agents["seer"], "lyra": agents["lyra"]},
        expected_purpose="hnc:swarm",
        expected_operator_aad={"intent": "two_way_security"},
    )

    assert decoded.text() == "swarm-secret"
    assert decoded.decode_report["swarm_mode"] == "hnc_swarm_two_way_locknotes_v1"
    assert decoded.decode_report["single_agent_can_decode"] is False
    assert len(packet["swarm_locknotes"]) == 6
    assert "swarm-secret" not in json.dumps(packet)


def test_hnc_swarm_breaker_checks_reject_breach_paths():
    agents = AGENT_KEYS
    packet = build_hnc_swarm_packet("breach-test-secret", agents, purpose="hnc:swarm")
    report = run_hnc_swarm_breaker_checks(packet, agents)

    assert report["passed"] is True
    assert {check["name"] for check in report["checks"]} == {
        "valid_two_agent_pair_decode",
        "single_agent_decode_blocked",
        "wrong_agent_secret_blocked",
        "locknote_tamper_blocked",
        "missing_pair_locknote_blocked",
    }


def test_key_normalization_has_one_unambiguous_32_byte_policy():
    raw = b"Z" * 32
    encoded = _base64url(raw)

    assert normalize_hnc_key_material(raw) == raw
    assert normalize_hnc_key_material(encoded) == raw
    with pytest.raises(HNCPacketError, match="master_key_too_short_minimum_32_bytes"):
        normalize_hnc_key_material(b"Z" * 31)
    with pytest.raises(HNCPacketError, match="master_key_too_short_minimum_32_bytes"):
        normalize_hnc_key_material(_base64url(b"Z" * 31))
    with pytest.raises(
        HNCPacketError,
        match="master_key_string_must_be_canonical_unpadded_base64url",
    ):
        normalize_hnc_key_material(encoded + "=")
    with pytest.raises(
        HNCPacketError,
        match="master_key_string_must_be_canonical_unpadded_base64url",
    ):
        normalize_hnc_key_material("raw textual key material is not accepted")


def test_packet_and_metadata_schemas_reject_self_rehashed_extensions():
    packet = build_hnc_quantum_packet("secret", MASTER_KEY)
    packet["extension"] = "not authenticated protocol state"
    packet["packet_sha256"] = sha256_hex(
        {key: value for key, value in packet.items() if key != "packet_sha256"}
    )
    assert "packet_schema_mismatch" in validate_hnc_packet_contract(packet)["reasons"]

    packet = build_hnc_quantum_packet("secret", MASTER_KEY)
    packet["metadata"]["extension"] = True
    packet["packet_sha256"] = sha256_hex(
        {key: value for key, value in packet.items() if key != "packet_sha256"}
    )
    assert "metadata_schema_mismatch" in validate_hnc_packet_contract(packet)["reasons"]


def test_packet_requires_symbolic_route_even_after_all_public_hashes_are_recomputed():
    packet = build_hnc_quantum_packet("secret", MASTER_KEY)
    alignment = packet["metadata"]["hnc_alignment"]
    alignment.pop("symbolic_route_seal")
    alignment_hash = sha256_hex(
        {
            "purpose": alignment["purpose"],
            "geometry": alignment["geometry"],
            "symbolic_route_seal": None,
            "hnc_params": alignment["hnc_params"],
            "packet_contract": alignment["packet_contract"],
            "extra": alignment.get("extra", {}),
        }
    )
    alignment["hnc_alignment_sha256"] = alignment_hash
    packet["metadata"]["hnc_alignment_sha256"] = alignment_hash
    packet["packet_sha256"] = sha256_hex(
        {key: value for key, value in packet.items() if key != "packet_sha256"}
    )

    validation = validate_hnc_packet_contract(packet)
    assert validation["valid"] is False
    assert "symbolic_route_seal_required" in validation["reasons"]


def test_base64url_fields_and_env_wrapper_must_be_canonical_unpadded():
    packet = build_hnc_quantum_packet("secret", MASTER_KEY)
    packet["nonce_b64"] += "="
    packet["packet_sha256"] = sha256_hex(
        {key: value for key, value in packet.items() if key != "packet_sha256"}
    )
    assert "cipher_material_invalid" in validate_hnc_packet_contract(packet)["reasons"]
    with pytest.raises(HNCPacketError, match="packet_contract_failed"):
        decode_hnc_quantum_packet(packet, MASTER_KEY)

    token = encode_env_packet("secret", MASTER_KEY, env_key="API_SECRET")
    with pytest.raises(HNCPacketError, match="base64url_encoding_invalid"):
        decode_env_packet(token + "=", MASTER_KEY, env_key="API_SECRET")
    assert is_env_packet(token) is True
    assert is_env_packet(" " + token) is False
    with pytest.raises(HNCPacketError, match="env_packet_encoding_not_canonical"):
        decode_env_packet(" " + token, MASTER_KEY, env_key="API_SECRET")


def test_environment_key_reader_does_not_silently_trim_key_material():
    encoded = _base64url(b"Z" * 32)
    supplied = " " + encoded

    assert packet_master_key_from_env({"AUREON_HNC_PACKET_MASTER_KEY": supplied}) == supplied
    with pytest.raises(
        HNCPacketError,
        match="master_key_string_must_be_canonical_unpadded_base64url",
    ):
        normalize_hnc_key_material(supplied)


def test_env_json_rejects_duplicate_keys_before_contract_validation():
    duplicate_json = b'{"magic":"first","magic":"second"}'
    token = ENV_PACKET_PREFIX + _base64url(duplicate_json)

    with pytest.raises(HNCPacketError, match="json_duplicate_object_key"):
        decode_env_packet(token, MASTER_KEY, env_key="API_SECRET")
    assert env_packet_summary(token)["error"] == "json_duplicate_object_key"


def test_env_wrapper_rejects_packet_json_over_the_configured_bound(monkeypatch):
    monkeypatch.setattr(hnc_crypto, "MAX_ENV_PACKET_JSON_BYTES", 16)
    token = ENV_PACKET_PREFIX + _base64url(b'{"packet":"too-large"}')

    with pytest.raises(HNCPacketError, match="base64url_decoded_value_too_large"):
        decode_env_packet(token, MASTER_KEY, env_key="API_SECRET")


def test_json_contract_rejects_nonfinite_and_excessively_deep_values():
    with pytest.raises(HNCPacketError, match="json_non_finite_number"):
        canonical_json_bytes({"value": float("nan")})

    nested: dict[str, object] = {}
    cursor = nested
    for _index in range(40):
        child: dict[str, object] = {}
        cursor["child"] = child
        cursor = child
    with pytest.raises(HNCPacketError, match="json_maximum_depth_exceeded"):
        canonical_json_bytes(nested)
    with pytest.raises(HNCPacketError, match="json_string_not_valid_utf8"):
        canonical_json_bytes({"value": "\ud800"})
    with pytest.raises(HNCPacketError, match="plaintext_not_valid_utf8"):
        build_hnc_quantum_packet("\ud800", MASTER_KEY)


def test_hnc_parameter_values_are_checked_at_build_and_validation_boundaries():
    with pytest.raises(HNCPacketError, match="hnc_params_tau_invalid"):
        build_hnc_alignment_context(
            purpose="hnc:invalid-params",
            hnc_params=HNCParams(tau=0),
        )

    packet = build_hnc_quantum_packet("secret", MASTER_KEY)
    alignment = packet["metadata"]["hnc_alignment"]
    alignment["hnc_params"]["r_squared"] = 1.1
    alignment_hash = sha256_hex(
        {
            "purpose": alignment["purpose"],
            "geometry": alignment["geometry"],
            "symbolic_route_seal": alignment["symbolic_route_seal"],
            "hnc_params": alignment["hnc_params"],
            "packet_contract": alignment["packet_contract"],
            "extra": alignment.get("extra", {}),
        }
    )
    alignment["hnc_alignment_sha256"] = alignment_hash
    packet["metadata"]["hnc_alignment_sha256"] = alignment_hash
    packet["packet_sha256"] = sha256_hex(
        {key: value for key, value in packet.items() if key != "packet_sha256"}
    )

    assert "hnc_params_r_squared_invalid" in validate_hnc_packet_contract(packet)["reasons"]


def test_single_packet_builder_self_validates_custom_geometry():
    with pytest.raises(HNCPacketError, match="auris_9_node_lattice_missing"):
        build_hnc_quantum_packet(
            "secret",
            MASTER_KEY,
            geometry={},
        )


@pytest.mark.parametrize(
    "geometry",
    [
        {**DEFAULT_GEOMETRY, "auris_nodes": [None] * 9},
        {**DEFAULT_GEOMETRY, "auris_nodes": ["node"] * 9},
        {
            **DEFAULT_GEOMETRY,
            "auris_nodes": [
                {"name": f"node-{index}", "frequency_hz": "not-a-frequency", "texture": "test"}
                for index in range(9)
            ],
        },
        {**DEFAULT_GEOMETRY, "name": "   "},
    ],
    ids=["null_nodes", "string_nodes", "non_numeric_frequencies", "blank_name"],
)
def test_geometry_contract_rejects_fake_nine_entry_auris_lattices(geometry):
    with pytest.raises(HNCPacketError, match="geometry_invalid"):
        build_hnc_quantum_packet("secret", MASTER_KEY, geometry=geometry)


def test_validator_rejects_fake_geometry_after_public_hashes_are_recomputed():
    packet = build_hnc_quantum_packet("secret", MASTER_KEY)
    alignment = packet["metadata"]["hnc_alignment"]
    alignment["geometry"]["auris_nodes"][0]["frequency_hz"] = "not-a-frequency"
    assert DEFAULT_GEOMETRY["auris_nodes"][0]["frequency_hz"] == 186.0
    alignment_hash = sha256_hex(
        {
            "purpose": alignment["purpose"],
            "geometry": alignment["geometry"],
            "symbolic_route_seal": alignment["symbolic_route_seal"],
            "hnc_params": alignment["hnc_params"],
            "packet_contract": alignment["packet_contract"],
            "extra": alignment.get("extra", {}),
        }
    )
    alignment["hnc_alignment_sha256"] = alignment_hash
    packet["metadata"]["hnc_alignment_sha256"] = alignment_hash
    packet["packet_sha256"] = sha256_hex(
        {key: value for key, value in packet.items() if key != "packet_sha256"}
    )

    validation = validate_hnc_packet_contract(packet)

    assert validation["valid"] is False
    assert "geometry_auris_node_0_frequency_invalid" in validation["reasons"]


def test_explicit_nonce_is_test_only_and_fresh_salt_prevents_key_nonce_reuse():
    nonce = b"N" * 12
    first = build_hnc_quantum_packet("secret", MASTER_KEY, nonce=nonce)
    second = build_hnc_quantum_packet("secret", MASTER_KEY, nonce=nonce)

    assert first["nonce_b64"] == second["nonce_b64"]
    assert first["metadata"]["key_derivation_salt_b64"] != second["metadata"]["key_derivation_salt_b64"]
    assert first["ciphertext_b64"] != second["ciphertext_b64"]
    assert decode_hnc_quantum_packet(first, MASTER_KEY).text() == "secret"
    assert decode_hnc_quantum_packet(second, MASTER_KEY).text() == "secret"


@pytest.mark.parametrize(
    "vector",
    LEGACY_V1_FIXTURES["single"]["vectors"],
    ids=lambda vector: vector["key_kind"],
)
def test_persisted_saltless_v1_known_answers_retain_old_key_semantics(vector):
    packet = _legacy_single_fixture(vector)
    master_key = _fixture_key(vector)
    validation = validate_hnc_packet_contract(packet)
    assert validation["valid"] is True
    assert validation["legacy_key_derivation_profile"] is True
    assert normalize_hnc_key_material(master_key, packet=packet) == (
        base64.b64decode(vector["key_value"])
        if vector["key_kind"] == "bytes_b64"
        else vector["key_value"].encode("utf-8")
    )
    assert decode_hnc_quantum_packet(packet, master_key).text() == "legacy-profile"


def test_public_summaries_identify_read_only_legacy_packets_for_migration():
    packet = _legacy_single_fixture(LEGACY_V1_FIXTURES["single"]["vectors"][0])
    token = ENV_PACKET_PREFIX + _base64url(canonical_json_bytes(packet))

    assert packet_public_summary(packet)["legacy_key_derivation_profile"] is True
    assert env_packet_summary(token)["legacy_key_derivation_profile"] is True
    assert (
        packet_public_summary(build_hnc_quantum_packet("new-write", MASTER_KEY))[
            "legacy_key_derivation_profile"
        ]
        is False
    )


@pytest.mark.parametrize(
    "legacy_key",
    [b"0123456789abcdef", "legacy-key-12345"],
    ids=["bytes16", "raw_text_fallback"],
)
def test_legacy_key_profiles_remain_decode_only(legacy_key):
    with pytest.raises(HNCPacketError):
        build_hnc_quantum_packet("new-write", legacy_key)


def test_persisted_schema_v1_swarm_known_answer_retains_old_agent_key_semantics():
    packet, agent_keys = _legacy_swarm_fixture()

    assert validate_hnc_packet_contract(packet)["valid"] is True
    assert decode_hnc_swarm_packet(packet, agent_keys).text() == "legacy-swarm-profile"
    with pytest.raises(HNCPacketError):
        build_hnc_swarm_packet("new-write", agent_keys)


def test_decode_report_does_not_publish_a_plaintext_fingerprint():
    packet = build_hnc_quantum_packet("fingerprint-sensitive", MASTER_KEY)
    decoded = decode_hnc_quantum_packet(packet, MASTER_KEY)

    assert "plaintext_sha256_runtime_only" not in decoded.decode_report
    assert "fingerprint-sensitive" not in json.dumps(decoded.decode_report)


def test_expected_aad_comparison_preserves_json_boolean_number_types():
    packet = build_hnc_quantum_packet(
        "secret",
        MASTER_KEY,
        operator_aad={"guard": 1},
    )
    with pytest.raises(HNCPacketError, match="operator_aad_mismatch"):
        decode_hnc_quantum_packet(
            packet,
            MASTER_KEY,
            expected_operator_aad={"guard": True},
        )

    swarm = build_hnc_swarm_packet(
        "secret",
        AGENT_KEYS,
        operator_aad={"guard": 1},
    )
    with pytest.raises(HNCPacketError, match="operator_aad_mismatch"):
        decode_hnc_swarm_packet(
            swarm,
            {"seer": AGENT_KEYS["seer"], "lyra": AGENT_KEYS["lyra"]},
            expected_operator_aad={"guard": True},
        )


def test_public_summary_is_total_for_malformed_nested_geometry():
    summary = packet_public_summary(
        {"metadata": {"hnc_alignment": {"geometry": "not-an-object"}}}
    )

    assert summary["valid_contract"] is False
    assert summary["geometry_name"] is None


def test_swarm_secrets_must_be_distinct_after_normalization():
    with pytest.raises(HNCPacketError, match="swarm_agent_secrets_must_be_distinct"):
        build_hnc_swarm_packet(
            "secret",
            {"seer": b"S" * 32, "lyra": b"S" * 32},
        )
    with pytest.raises(HNCPacketError, match="duplicate_normalized_agent_id"):
        build_hnc_swarm_packet(
            "secret",
            {"seer": b"S" * 32, " seer ": b"L" * 32},
        )
    with pytest.raises(HNCPacketError, match="agent_id_invalid"):
        build_hnc_swarm_packet(
            "secret",
            {"\ud800": b"S" * 32, "lyra": b"L" * 32},
        )


def test_swarm_mode_is_reserved_and_validated_in_alignment_context():
    with pytest.raises(HNCPacketError, match="hnc_context_reserved_key:swarm_mode"):
        build_hnc_swarm_packet(
            "secret",
            AGENT_KEYS,
            hnc_context={"swarm_mode": "fake"},
        )

    packet = build_hnc_swarm_packet("secret", AGENT_KEYS)
    alignment = packet["metadata"]["hnc_alignment"]
    alignment["extra"]["swarm_mode"] = "fake"
    alignment_hash = sha256_hex(
        {
            "purpose": alignment["purpose"],
            "geometry": alignment["geometry"],
            "symbolic_route_seal": alignment["symbolic_route_seal"],
            "hnc_params": alignment["hnc_params"],
            "packet_contract": alignment["packet_contract"],
            "extra": alignment["extra"],
        }
    )
    alignment["hnc_alignment_sha256"] = alignment_hash
    packet["metadata"]["hnc_alignment_sha256"] = alignment_hash
    packet["packet_sha256"] = sha256_hex(
        {key: value for key, value in packet.items() if key != "packet_sha256"}
    )

    assert "swarm_alignment_mode_mismatch" in validate_hnc_packet_contract(packet)["reasons"]


def test_swarm_locknote_schema_rejects_self_rehashed_extension():
    packet = build_hnc_swarm_packet("secret", AGENT_KEYS)
    note = packet["swarm_locknotes"][0]
    note["extension"] = "unbound"
    note["locknote_sha256"] = sha256_hex(
        {key: value for key, value in note.items() if key != "locknote_sha256"}
    )
    packet["packet_sha256"] = sha256_hex(
        {key: value for key, value in packet.items() if key != "packet_sha256"}
    )

    assert "swarm_locknote_schema_mismatch" in validate_hnc_packet_contract(packet)["reasons"]
    with pytest.raises(HNCPacketError, match="packet_contract_failed"):
        decode_hnc_swarm_packet(packet, {"seer": AGENT_KEYS["seer"], "lyra": AGENT_KEYS["lyra"]})


def test_fragment_stream_rejects_invalid_slits_and_extension_fields():
    packet = build_hnc_quantum_packet("secret", MASTER_KEY)
    with pytest.raises(HNCPacketError, match="slit_names_invalid"):
        stream_hnc_probability_fragments(packet, slit_names=())

    fragments = stream_hnc_probability_fragments(packet, fragment_size=256)
    extended = copy.deepcopy(fragments)
    extended[0]["extension"] = True
    with pytest.raises(HNCPacketError, match="fragment_schema_mismatch"):
        reassemble_hnc_probability_fragments(extended)

    manifest_extended = copy.deepcopy(fragments)
    manifest_extended[0]["manifest"]["extension"] = True
    with pytest.raises(HNCPacketError, match="manifest_schema_mismatch"):
        reassemble_hnc_probability_fragments(manifest_extended)


def test_fragment_stream_bounds_count_and_decoded_chunk_size(monkeypatch):
    packet = build_hnc_quantum_packet("secret", MASTER_KEY)
    fragments = stream_hnc_probability_fragments(packet, fragment_size=256)

    monkeypatch.setattr(hnc_crypto, "MAX_FRAGMENT_BYTES", 8)
    with pytest.raises(HNCPacketError, match="base64url_decoded_value_too_large"):
        reassemble_hnc_probability_fragments(fragments)

    monkeypatch.setattr(hnc_crypto, "MAX_FRAGMENT_BYTES", 4 * 1024 * 1024)
    monkeypatch.setattr(hnc_crypto, "MAX_FRAGMENT_COUNT", 1)
    with pytest.raises(HNCPacketError, match="fragment_count_limit_exceeded"):
        stream_hnc_probability_fragments(packet, fragment_size=128)


def test_fragment_reassembly_bounds_total_packet_bytes(monkeypatch):
    packet = build_hnc_quantum_packet(b"X" * (2 * 1024 * 1024), MASTER_KEY)
    fragments = stream_hnc_probability_fragments(packet, fragment_size=4 * 1024 * 1024)
    monkeypatch.setattr(hnc_crypto, "MAX_PACKET_JSON_BYTES", 2 * 1024 * 1024)

    with pytest.raises(HNCPacketError, match="reassembled_packet_too_large"):
        reassemble_hnc_probability_fragments(fragments)


def test_fragment_reassembly_rejects_duplicate_key_packet_json():
    packet_bytes = b'{"magic":"first","magic":"second"}'
    packet_sha256 = "2" * 64
    stream_id = sha256_hex(
        {
            "packet_sha256": packet_sha256,
            "chunk_count": 1,
            "slit_names": ["alpha"],
        }
    )
    manifest = {
        "schema_version": 1,
        "stream_type": "hnc_temporal_probability_stream",
        "stream_id": stream_id,
        "packet_sha256": packet_sha256,
        "fragment_count": 1,
        "packet_bytes_sha256": sha256_hex(packet_bytes),
        "slit_names": ["alpha"],
        "reassembly_rule": "all_fragments_required_then_hnc_contract_decode",
        "plaintext_visible_before_reassembly": False,
    }
    fragment = {
        "schema_version": 1,
        "stream_type": "hnc_temporal_probability_fragment",
        "stream_id": stream_id,
        "manifest_sha256": sha256_hex(manifest),
        "manifest": manifest,
        "fragment_index": 0,
        "fragment_count": 1,
        "slit_name": "alpha",
        "probability_weight": 1.0,
        "phase_hint": 1.0,
        "chunk_b64": _base64url(packet_bytes),
        "chunk_sha256": sha256_hex(packet_bytes),
        "secret_policy": "ciphertext_fragment_only_no_plaintext",
    }

    with pytest.raises(HNCPacketError, match="json_duplicate_object_key"):
        reassemble_hnc_probability_fragments([fragment])
