from __future__ import annotations

from typing import Any, cast

import pytest

from aureon.plumber.authorization_chain_v02 import (
    AUTHORIZATION_CHAIN_SCHEMA,
    AuthorizationChainV02,
)
from aureon.plumber.crypto import domain_hash
from aureon.plumber.magic_star_v02 import STAR_SCHEMA, MagicStarV02
from aureon.plumber.recipient_proof_v02 import RecipientEnrollmentV02
from aureon.plumber.release_boundary_v02 import (
    CapabilityPolicyV02,
    CapabilityReleaseResultV02,
)
from aureon.plumber.release_evidence_v02 import (
    RELEASE_EVIDENCE_SCHEMA,
    ReleaseEvidenceV02,
)
from aureon.plumber.release_state_v02 import (
    EPAS_STATE_SCHEMA,
    STATE_SCHEMA,
    EPASChainSnapshot,
    ReleasePhase,
    ReleaseStateSnapshot,
)
from aureon.plumber.star_custody_v02 import (
    PROTECTED_PACKET_MAGIC,
    PROTECTED_PACKET_SCHEMA,
    ProtectedMagicStarPacketV02,
)

_SHA256 = "a" * 64


def _nested(label: str) -> dict[str, Any]:
    return {"label": label, "nested": {"items": [f"{label}-value"]}}


def _assert_nested_is_frozen(value: Any) -> None:
    nested = cast(Any, value["nested"])
    with pytest.raises(TypeError):
        nested["extra"] = "denied"
    with pytest.raises(AttributeError):
        nested["items"].append("denied")


def test_magic_star_defensively_freezes_all_components_and_preserves_commitment() -> None:
    profile = _nested("profile")
    epas = _nested("epas")
    heart = _nested("heart")
    point = _nested("point")
    points: list[dict[str, Any]] = [point]
    seal = _nested("seal")
    expected = {
        "schema": STAR_SCHEMA,
        "profile": _nested("profile"),
        "epas_precondition": _nested("epas"),
        "heart_precondition": _nested("heart"),
        "points": [_nested("point")],
        "seal": _nested("seal"),
    }
    star = MagicStarV02(
        schema=STAR_SCHEMA,
        profile=profile,
        epas_precondition=epas,
        heart_precondition=heart,
        points=cast(Any, points),
        seal=seal,
    )

    before = star.commitment
    profile["nested"]["items"].append("caller-mutation")
    epas["nested"]["changed"] = True
    point["nested"]["items"].clear()
    points.append(_nested("late-point"))
    seal["nested"]["changed"] = True

    assert star.public_dict() == expected
    assert before == domain_hash("AUREON-PLUMBER-V02-MAGIC-STAR", expected)
    assert star.commitment == before
    _assert_nested_is_frozen(star.profile)
    _assert_nested_is_frozen(star.points[0])
    public = star.public_dict()
    public["profile"]["nested"]["items"].append("public-copy-mutation")
    assert star.public_dict() == expected


def test_release_evidence_defensively_freezes_receipts_and_release_proof() -> None:
    receipt = _nested("receipt")
    receipts: list[dict[str, Any]] = [receipt]
    proof = _nested("proof")
    expected = {
        "schema": RELEASE_EVIDENCE_SCHEMA,
        "organ_receipts": [_nested("receipt")],
        "release_proof": _nested("proof"),
    }
    evidence = ReleaseEvidenceV02(
        schema=RELEASE_EVIDENCE_SCHEMA,
        organ_receipts=cast(Any, receipts),
        release_proof=proof,
    )

    before = evidence.commitment
    receipt["nested"]["items"].append("caller-mutation")
    receipts.clear()
    proof["nested"]["changed"] = True

    assert evidence.public_dict() == expected
    assert evidence.commitment == before
    _assert_nested_is_frozen(evidence.organ_receipts[0])
    _assert_nested_is_frozen(evidence.release_proof)


def test_authorization_chain_defensively_freezes_every_join_component() -> None:
    continuity = _nested("continuity")
    snapshot = _nested("snapshot")
    permit = _nested("permit")
    permits: list[dict[str, Any]] = [permit]
    custody = _nested("custody")
    expected = {
        "schema": AUTHORIZATION_CHAIN_SCHEMA,
        "continuity_decision": _nested("continuity"),
        "authorization_snapshot": _nested("snapshot"),
        "permits": [_nested("permit")],
        "custody_authorization": _nested("custody"),
    }
    chain = AuthorizationChainV02(
        schema=AUTHORIZATION_CHAIN_SCHEMA,
        continuity_decision=continuity,
        authorization_snapshot=snapshot,
        permits=cast(Any, permits),
        custody_authorization=custody,
    )

    before = chain.commitment
    continuity["nested"]["items"].clear()
    snapshot["nested"]["changed"] = True
    permit["nested"]["items"].append("caller-mutation")
    permits.clear()
    custody["nested"]["changed"] = True

    assert chain.public_dict() == expected
    assert chain.commitment == before
    _assert_nested_is_frozen(chain.continuity_decision)
    _assert_nested_is_frozen(chain.permits[0])


def test_protected_packet_defensively_freezes_share_bindings_and_signature() -> None:
    binding: dict[str, Any] = _nested("binding")
    bindings: list[dict[str, Any]] = [binding]
    signature = _nested("signature")
    packet = ProtectedMagicStarPacketV02(
        magic=PROTECTED_PACKET_MAGIC,
        schema=PROTECTED_PACKET_SCHEMA,
        protocol_id="protocol",
        profile_id="profile",
        source_profile_commitment=_SHA256,
        packet_id="packet",
        purpose="purpose",
        release_context_sha256=_SHA256,
        carrier_commitment=_SHA256,
        share_bindings=cast(Any, bindings),
        nonce_b64="nonce",
        ciphertext_b64="ciphertext",
        aad_sha256=_SHA256,
        source_signature=signature,
    )
    expected = packet.public_dict()
    before = packet.packet_commitment

    binding["nested"]["items"].append("caller-mutation")
    bindings.clear()
    signature["nested"]["changed"] = True

    assert packet.public_dict() == expected
    assert packet.packet_commitment == before
    _assert_nested_is_frozen(packet.share_bindings[0])
    _assert_nested_is_frozen(packet.source_signature)


def test_release_result_defensively_freezes_result_and_receipt() -> None:
    result = _nested("result")
    receipt = _nested("receipt")
    release = CapabilityReleaseResultV02(
        result=result,
        receipt=receipt,
        release_state=ReleaseStateSnapshot(
            schema=STATE_SCHEMA,
            session_id="session",
            packet_id="packet",
            purpose="purpose",
            live_binding_sha256=_SHA256,
            expires_at_ms=2,
            phase=ReleasePhase.CONSUMED,
            version=1,
        ),
        epas_state=EPASChainSnapshot(
            schema=EPAS_STATE_SCHEMA,
            epoch=1,
            head_sha256=_SHA256,
        ),
    )
    expected = release.public_dict()

    result["nested"]["items"].append("caller-mutation")
    receipt["nested"]["changed"] = True

    assert release.public_dict() == expected
    _assert_nested_is_frozen(release.result)
    _assert_nested_is_frozen(release.receipt)
    public = release.public_dict()
    public["result"]["nested"]["items"].clear()
    assert release.public_dict() == expected


def test_mutable_recipient_and_capability_policy_inputs_are_normalized_to_tuples() -> None:
    channels = [_SHA256]
    purposes = ["purpose"]
    enrollment = RecipientEnrollmentV02(
        recipient_id="recipient",
        principal="principal",
        key_id="key",
        public_key_hex=_SHA256,
        allowed_channel_bindings=cast(Any, channels),
        allowed_purposes=cast(Any, purposes),
    )
    allowed = ["signature_valid"]
    required = ["signature_valid"]
    policy = CapabilityPolicyV02(
        capability_id="capability",
        capability_measurement_sha256=_SHA256,
        allowed_output_keys=cast(Any, allowed),
        output_types_by_key={"signature_valid": "bool"},
        required_output_keys=cast(Any, required),
    )
    policy_commitment = policy.commitment

    channels.append("b" * 64)
    purposes.append("other")
    allowed.append("late_output")
    required.clear()

    assert enrollment.allowed_channel_bindings == (_SHA256,)
    assert enrollment.allowed_purposes == ("purpose",)
    assert policy.allowed_output_keys == ("signature_valid",)
    assert policy.required_output_keys == ("signature_valid",)
    assert policy.commitment == policy_commitment
    with pytest.raises(AttributeError):
        cast(Any, enrollment.allowed_purposes).append("denied")
    with pytest.raises(AttributeError):
        cast(Any, policy.allowed_output_keys).append("denied")
