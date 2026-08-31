from __future__ import annotations

import math

import pytest

from aureon.plumber.crypto import (
    CryptoContractError,
    b64url_decode,
    b64url_encode,
    canonical_json_bytes,
    decode_canonical_json,
    generate_ed25519_private_key,
    sign_ed25519,
    verify_ed25519,
)
from aureon.plumber.schema import (
    PLUMBER_MAGIC,
    PLUMBER_PACKET_SCHEMA,
    DenialCode,
    PlumberPacketV0,
    SchemaError,
    require_int,
)

DIGEST = "a" * 64


def _packet_values() -> dict[str, object]:
    receipt = {"receipt_hash": DIGEST}
    return {
        "magic": PLUMBER_MAGIC,
        "schema": PLUMBER_PACKET_SCHEMA,
        "schema_version": 0,
        "packet_identity": "packet-1",
        "source_identity": {"identity_commitment": DIGEST},
        "temporal_identity": {"temporal_commitment": DIGEST},
        "requested_purpose": "bounded test purpose",
        "hnc_observer_challenge": DIGEST,
        "canonical_field_receipt": receipt,
        "observer_transcript_commitment": DIGEST,
        "twin_rune_seal": {"seal_commitment": DIGEST},
        "sympathetic_identity_commitment": DIGEST,
        "heart_receipt": receipt,
        "conscience_receipt": receipt,
        "governance_receipt": receipt,
        "quorum_policy": {"policy_commitment": DIGEST},
        "encrypted_payload": {"ciphertext_commitment": DIGEST},
        "spore_manifest": {"manifest_commitment": DIGEST},
        "signatures": {},
    }


def test_canonical_json_rejects_ambiguous_numbers_and_duplicates() -> None:
    assert canonical_json_bytes({"b": 2, "a": 1}) == b'{"a":1,"b":2}'
    assert decode_canonical_json(b'{"a":1,"b":2}', require_mapping=True) == {"a": 1, "b": 2}
    with pytest.raises(CryptoContractError, match="json_duplicate_object_key"):
        decode_canonical_json(b'{"a":1,"a":2}')
    with pytest.raises(CryptoContractError, match="json_encoding_not_canonical"):
        decode_canonical_json(b'{"b":2,"a":1}')
    for value in (-0.0, 0.0, 1.5, math.nan, math.inf, -math.inf):
        with pytest.raises(CryptoContractError, match="json_float_not_supported"):
            canonical_json_bytes({"value": value})
    for raw in (b'{"value":NaN}', b'{"value":Infinity}', b'{"value":-Infinity}'):
        with pytest.raises(CryptoContractError, match="non_finite_json_number"):
            decode_canonical_json(raw)


def test_strict_base64_and_ed25519_round_trip() -> None:
    encoded = b64url_encode(b"opaque-cipher-bytes")
    assert b64url_decode(encoded) == b"opaque-cipher-bytes"
    with pytest.raises(CryptoContractError):
        b64url_decode(f"{encoded}=")
    with pytest.raises(CryptoContractError):
        b64url_decode(encoded, expected_bytes=True)
    key = generate_ed25519_private_key()
    signed = {"counter": 1, "commitment": DIGEST}
    signature = sign_ed25519(key, signed, domain="test.plumber")
    assert verify_ed25519(key.public_key(), signed, signature, domain="test.plumber")
    assert not verify_ed25519(key.public_key(), {"counter": 2}, signature, domain="test.plumber")


def test_packet_schema_is_exact_and_summary_omits_sensitive_fields() -> None:
    packet = PlumberPacketV0.build(**_packet_values())
    assert PlumberPacketV0.from_dict(packet.to_dict()) == packet
    summary = packet.public_summary()
    assert "encrypted_payload" not in summary
    assert "requested_purpose" not in summary
    assert "signatures" not in summary
    assert summary["release_state"] == "not_released"

    unknown = packet.to_dict()
    unknown["extra"] = True
    with pytest.raises(SchemaError) as caught:
        PlumberPacketV0.from_dict(unknown)
    assert caught.value.code == DenialCode.UNKNOWN_FIELD

    tampered = packet.to_dict()
    tampered["packet_commitment"] = "0" * 64
    with pytest.raises(SchemaError) as caught:
        PlumberPacketV0.from_dict(tampered)
    assert caught.value.code == DenialCode.PACKET_COMMITMENT_MISMATCH

    minimal = _packet_values()
    for field in ("magic", "schema", "schema_version", "signatures"):
        minimal.pop(field)
    assert PlumberPacketV0.build(**minimal).magic == PLUMBER_MAGIC


def test_bool_is_not_an_integer_and_packet_version_is_strict() -> None:
    with pytest.raises(SchemaError):
        require_int(True, field="counter")
    values = _packet_values()
    values["schema_version"] = False
    with pytest.raises(SchemaError) as caught:
        PlumberPacketV0.build(**values)
    assert caught.value.code == DenialCode.INVALID_SCHEMA
