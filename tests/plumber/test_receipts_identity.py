from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from aureon.plumber.crypto import generate_ed25519_private_key
from aureon.plumber.receipts import ReceiptKind, ReceiptVerdict, SignedReceipt
from aureon.plumber.schema import DenialCode, SchemaError
from aureon.plumber.source_identity import (
    SourceIdentityV0,
    build_source_identity_from_hnc_packet,
    verify_source_identity,
)
from aureon.plumber.sympathetic_identity import SympatheticIdentityV0
from aureon.plumber.twin_rune_seal import TwinRuneSealV0

DIGESTS = tuple(f"{number:064x}" for number in range(1, 20))
NOW = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)


def _receipt() -> SignedReceipt:
    return SignedReceipt.issue(
        kind=ReceiptKind.HEART,
        packet_identity="packet-1",
        session_identity="session-1",
        purpose_commitment=DIGESTS[0],
        source_identity_commitment=DIGESTS[1],
        temporal_identity_commitment=DIGESTS[2],
        observer_transcript_commitment=DIGESTS[3],
        policy_commitment=DIGESTS[4],
        runtime_measurement_commitment=DIGESTS[5],
        verdict=ReceiptVerdict.APPROVED,
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
        signer_id="heart-authority-1",
        private_key=generate_ed25519_private_key(),
    )


def test_signed_receipt_validates_bindings_tamper_and_expiry() -> None:
    receipt = _receipt()
    assert receipt.validate(
        now=NOW + timedelta(seconds=1),
        expected_packet_identity="packet-1",
        expected_session_identity="session-1",
        expected_purpose_commitment=DIGESTS[0],
    ).valid
    assert DenialCode.STALE_STATE in receipt.validate(now=NOW + timedelta(minutes=5)).denial_codes

    tampered = receipt.to_dict()
    tampered["verdict"] = ReceiptVerdict.DENIED
    validation = SignedReceipt.from_dict(tampered).validate(now=NOW + timedelta(seconds=1))
    assert not validation.valid
    assert DenialCode.INVALID_SIGNATURE in validation.denial_codes


def test_source_twin_rune_and_sympathetic_commitments_fail_closed() -> None:
    source = SourceIdentityV0.build(
        source_type="hnc-observer",
        source_locator_commitment=DIGESTS[0],
        source_content_commitment=DIGESTS[1],
        provenance_receipt_commitment=DIGESTS[2],
    )
    assert verify_source_identity(source)
    changed_source = source.to_dict()
    changed_source["source_content_commitment"] = DIGESTS[3]
    with pytest.raises(SchemaError) as caught:
        SourceIdentityV0.from_dict(changed_source)
    assert caught.value.code == DenialCode.SOURCE_IDENTITY_MISMATCH

    seal = TwinRuneSealV0.build(
        source_identity_commitment=source.identity_commitment,
        observer_transcript_commitment=DIGESTS[4],
        temporal_identity_commitment=DIGESTS[5],
        purpose_commitment=DIGESTS[6],
        challenge_commitment=DIGESTS[7],
    )
    assert TwinRuneSealV0.from_dict(seal.to_dict()) == seal

    sympathetic = SympatheticIdentityV0.build(
        source_identity_commitment=source.identity_commitment,
        hardware_identity_commitment=DIGESTS[8],
        operator_identity_commitment=DIGESTS[9],
        temporal_identity_commitment=DIGESTS[10],
        observer_identity_commitment=DIGESTS[11],
        purpose_commitment=DIGESTS[12],
        policy_commitment=DIGESTS[13],
    )
    assert SympatheticIdentityV0.from_dict(sympathetic.to_dict()) == sympathetic


def test_source_identity_layers_over_existing_hnc_packet_validator() -> None:
    from aureon.harmonic.hnc_quantum_packet_crypto import build_hnc_quantum_packet

    packet = build_hnc_quantum_packet(
        b"opaque-test-material",
        b"k" * 32,
        purpose="plumber.source-identity.test",
        nonce=b"n" * 12,
    )
    source = build_source_identity_from_hnc_packet(packet)
    assert source.source_type == "hnc-quantum-packet-v1"
    assert source.source_content_commitment == packet["packet_sha256"]
    assert "ciphertext_b64" not in source.public_summary()

    packet["packet_sha256"] = "0" * 64
    with pytest.raises(SchemaError) as caught:
        build_source_identity_from_hnc_packet(packet)
    assert caught.value.code == DenialCode.SOURCE_IDENTITY_MISMATCH
