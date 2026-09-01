from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

import aureon.plumber.crypto as plumber_crypto
import aureon.plumber.spore_transport as spore_transport
from aureon.plumber.audit import AuditEvent, assert_public_summary_safe
from aureon.plumber.quarantine import QuarantineRecord
from aureon.plumber.schema import DenialCode, SchemaError
from aureon.plumber.spore_transport import fragment_ciphertext, reassemble_ciphertext

DIGESTS = tuple(f"{number:064x}" for number in range(1, 20))
NOW = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)


def _fragments(*, route: str = "route-a"):
    return fragment_ciphertext(
        bytes(range(64)),
        packet_identity="packet-1",
        stream_identity="stream-1",
        temporal_epoch=4,
        route_id=route,
        challenge_commitment=DIGESTS[0],
        expires_at=NOW + timedelta(minutes=5),
        fragment_size=16,
    )


def test_transport_reassembles_shuffled_ciphertext_and_rejects_bad_sets() -> None:
    manifest, fragments = _fragments()
    assert reassemble_ciphertext(
        manifest,
        tuple(reversed(fragments)),
        now=NOW,
    ) == bytes(range(64))
    assert "ciphertext_fragment" not in fragments[0].public_summary()

    with pytest.raises(SchemaError) as caught:
        reassemble_ciphertext(manifest, fragments[:-1], now=NOW)
    assert caught.value.code == DenialCode.FRAGMENT_SET_INCOMPLETE

    _, other_fragments = _fragments(route="route-b")
    mixed = (other_fragments[0], *fragments[1:])
    with pytest.raises(SchemaError) as caught:
        reassemble_ciphertext(manifest, mixed, now=NOW)
    assert caught.value.code == DenialCode.FRAGMENT_INVALID

    with pytest.raises(SchemaError) as caught:
        reassemble_ciphertext(manifest, fragments, now=NOW + timedelta(minutes=5))
    assert caught.value.code == DenialCode.FRAGMENT_EXPIRED


def test_transport_rejects_oversized_fragment_before_decode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _manifest, fragments = _fragments()
    monkeypatch.setattr(spore_transport, "MAX_SPORE_FRAGMENT_BYTES", 8)

    def unexpected_decode(*_args, **_kwargs):
        raise AssertionError("encoded-size preflight must run before base64 decode")

    monkeypatch.setattr(plumber_crypto.base64, "b64decode", unexpected_decode)

    with pytest.raises(SchemaError) as caught:
        spore_transport.SporeFragment.from_dict(fragments[0].to_dict())

    assert caught.value.code == DenialCode.FRAGMENT_INVALID
    assert caught.value.field == "ciphertext_fragment"


def test_transport_rejects_fragment_count_before_decode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _manifest, fragments = _fragments()
    fragment = fragments[0].to_dict()
    fragment["fragment_count"] = 3
    monkeypatch.setattr(spore_transport, "MAX_SPORE_FRAGMENT_COUNT", 2)

    def unexpected_decode(*_args, **_kwargs):
        raise AssertionError("oversized count must be rejected before decoding")

    monkeypatch.setattr(spore_transport, "b64url_decode", unexpected_decode)
    with pytest.raises(SchemaError) as caught:
        spore_transport.SporeFragment.from_dict(fragment)

    assert caught.value.code == DenialCode.FRAGMENT_INVALID
    assert caught.value.field == "fragment_count"


def test_transport_never_leaks_crypto_contract_errors() -> None:
    _manifest, fragments = _fragments()
    invalid = fragments[0].to_dict()
    invalid["ciphertext_fragment"] = "!"

    with pytest.raises(SchemaError) as caught:
        spore_transport.SporeFragment.from_dict(invalid)

    assert caught.value.code == DenialCode.FRAGMENT_INVALID
    assert caught.value.field == "ciphertext_fragment"


def test_transport_rejects_manifest_fragment_count_before_tuple_copy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, _fragments_value = _fragments()
    monkeypatch.setattr(spore_transport, "MAX_SPORE_FRAGMENT_COUNT", 2)

    with pytest.raises(SchemaError) as caught:
        spore_transport.SporeManifest.from_dict(manifest.to_dict())

    assert caught.value.code == DenialCode.FRAGMENT_INVALID
    assert caught.value.field == "fragment_commitments"


@pytest.mark.parametrize(
    ("total_limit", "fragment_limit", "expected_field"),
    [
        (32, spore_transport.MAX_SPORE_FRAGMENT_BYTES, "ciphertext_size"),
        (spore_transport.MAX_SPORE_CIPHERTEXT_BYTES, 8, "fragment_capacity"),
    ],
)
def test_transport_rejects_oversized_or_impossible_manifest_before_hashing(
    monkeypatch: pytest.MonkeyPatch,
    total_limit: int,
    fragment_limit: int,
    expected_field: str,
) -> None:
    manifest, _fragments_value = _fragments()
    monkeypatch.setattr(spore_transport, "MAX_SPORE_CIPHERTEXT_BYTES", total_limit)
    monkeypatch.setattr(spore_transport, "MAX_SPORE_FRAGMENT_BYTES", fragment_limit)

    def unexpected_hash(*_args, **_kwargs):
        raise AssertionError("invalid capacity must be rejected before hashing")

    monkeypatch.setattr(spore_transport, "domain_hash", unexpected_hash)
    with pytest.raises(SchemaError) as caught:
        spore_transport.SporeManifest.from_dict(manifest.to_dict())

    assert caught.value.code == DenialCode.FRAGMENT_INVALID
    assert caught.value.field == expected_field


def test_transport_rejects_manifest_with_more_fragments_than_ciphertext_bytes() -> None:
    manifest, _fragments_value = _fragments()
    serialized = manifest.to_dict()
    serialized["ciphertext_size"] = 3

    with pytest.raises(SchemaError) as caught:
        spore_transport.SporeManifest.from_dict(serialized)

    assert caught.value.code == DenialCode.FRAGMENT_INVALID
    assert caught.value.field == "fragment_capacity"


@pytest.mark.parametrize(
    ("bound_name", "bound_value", "expected_field"),
    [
        ("MAX_SPORE_CIPHERTEXT_BYTES", 32, "ciphertext"),
        ("MAX_SPORE_FRAGMENT_COUNT", 2, "fragment_count"),
        ("MAX_SPORE_FRAGMENT_BYTES", 8, "fragment_size"),
    ],
)
def test_fragmenter_enforces_total_count_and_per_fragment_bounds(
    monkeypatch: pytest.MonkeyPatch,
    bound_name: str,
    bound_value: int,
    expected_field: str,
) -> None:
    monkeypatch.setattr(spore_transport, bound_name, bound_value)

    with pytest.raises(SchemaError) as caught:
        _fragments()

    assert caught.value.code == DenialCode.FRAGMENT_INVALID
    assert caught.value.field == expected_field


def test_fragmenter_accepts_exact_tiny_limits_and_rejects_each_plus_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(spore_transport, "MAX_SPORE_CIPHERTEXT_BYTES", 32)
    monkeypatch.setattr(spore_transport, "MAX_SPORE_FRAGMENT_BYTES", 16)
    monkeypatch.setattr(spore_transport, "MAX_SPORE_FRAGMENT_COUNT", 2)

    manifest, fragments = fragment_ciphertext(
        b"X" * 32,
        packet_identity="packet-limit",
        stream_identity="stream-limit",
        temporal_epoch=1,
        route_id="route-limit",
        challenge_commitment=DIGESTS[0],
        expires_at=NOW + timedelta(minutes=5),
        fragment_size=16,
    )
    assert manifest.ciphertext_size == 32
    assert manifest.fragment_count == 2
    assert all(len(plumber_crypto.b64url_decode(item.ciphertext_fragment)) == 16 for item in fragments)

    with pytest.raises(SchemaError) as caught:
        fragment_ciphertext(
            b"X" * 33,
            packet_identity="packet-limit",
            stream_identity="stream-limit",
            temporal_epoch=1,
            route_id="route-limit",
            challenge_commitment=DIGESTS[0],
            expires_at=NOW + timedelta(minutes=5),
            fragment_size=16,
        )
    assert caught.value.field == "ciphertext"

    with pytest.raises(SchemaError) as caught:
        fragment_ciphertext(
            b"X" * 16,
            packet_identity="packet-limit",
            stream_identity="stream-limit",
            temporal_epoch=1,
            route_id="route-limit",
            challenge_commitment=DIGESTS[0],
            expires_at=NOW + timedelta(minutes=5),
            fragment_size=17,
        )
    assert caught.value.field == "fragment_size"

    monkeypatch.setattr(spore_transport, "MAX_SPORE_CIPHERTEXT_BYTES", 48)
    with pytest.raises(SchemaError) as caught:
        fragment_ciphertext(
            b"X" * 48,
            packet_identity="packet-limit",
            stream_identity="stream-limit",
            temporal_epoch=1,
            route_id="route-limit",
            challenge_commitment=DIGESTS[0],
            expires_at=NOW + timedelta(minutes=5),
            fragment_size=16,
        )
    assert caught.value.field == "fragment_count"


def test_reassembly_enforces_current_total_bound_before_fragment_decode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, fragments = _fragments()
    monkeypatch.setattr(spore_transport, "MAX_SPORE_CIPHERTEXT_BYTES", 32)

    def unexpected_decode(*_args, **_kwargs):
        raise AssertionError("oversized manifest must be rejected before decoding")

    monkeypatch.setattr(spore_transport, "b64url_decode", unexpected_decode)
    with pytest.raises(SchemaError) as caught:
        reassemble_ciphertext(manifest, fragments, now=NOW)

    assert caught.value.code == DenialCode.FRAGMENT_INVALID
    assert caught.value.field == "ciphertext_size"


def test_reassembly_rejects_aggregate_size_before_any_fragment_decode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, fragments = _fragments()
    serialized = manifest.to_dict()
    serialized["ciphertext_size"] = 32
    serialized["manifest_commitment"] = spore_transport.domain_hash(
        "aureon.plumber.spore-manifest.v0",
        spore_transport._manifest_payload(serialized),
    )
    smaller = spore_transport.SporeManifest.from_dict(serialized)
    decode_calls = 0
    real_decode = spore_transport.b64url_decode

    def counted_decode(*args, **kwargs):
        nonlocal decode_calls
        decode_calls += 1
        return real_decode(*args, **kwargs)

    monkeypatch.setattr(spore_transport, "b64url_decode", counted_decode)
    with pytest.raises(SchemaError) as caught:
        reassemble_ciphertext(smaller, fragments, now=NOW)

    assert caught.value.code == DenialCode.FRAGMENT_INVALID
    assert caught.value.field == "ciphertext_size"
    assert decode_calls == 0


def test_reassembly_preflights_mutated_oversized_encoding_before_decoder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, fragments = _fragments()
    object.__setattr__(
        fragments[0],
        "ciphertext_fragment",
        "A" * (((4 * spore_transport.MAX_SPORE_FRAGMENT_BYTES + 2) // 3) + 1),
    )

    def unexpected_decode(*_args, **_kwargs):
        raise AssertionError("aggregate preflight must run before base64 decode")

    monkeypatch.setattr(plumber_crypto.base64, "b64decode", unexpected_decode)
    with pytest.raises(SchemaError) as caught:
        reassemble_ciphertext(manifest, fragments, now=NOW)

    assert caught.value.code == DenialCode.FRAGMENT_INVALID
    assert caught.value.field == "ciphertext_fragment"


def test_audit_and_quarantine_records_are_commitment_only() -> None:
    audit = AuditEvent.build(
        event_type="immune_gate",
        trace_id="trace-1",
        packet_identity="packet-1",
        session_identity="session-1",
        outcome="denied",
        denial_codes=(DenialCode.PURPOSE_MISMATCH,),
        evidence_commitments={"gate": DIGESTS[1]},
        recorded_at=NOW,
    )
    assert AuditEvent.from_dict(audit.to_dict()) == audit
    assert_public_summary_safe(audit.public_summary())
    with pytest.raises(SchemaError):
        assert_public_summary_safe({"plaintext": "must-not-cross"})

    quarantine = QuarantineRecord.build(
        quarantine_id="quarantine-1",
        packet_identity="packet-1",
        session_identity="session-1",
        packet_commitment=DIGESTS[2],
        denial_codes=(DenialCode.PURPOSE_MISMATCH,),
        evidence_commitments={"audit": audit.event_commitment},
        quarantined_at=NOW,
    )
    assert QuarantineRecord.from_dict(quarantine.to_dict()) == quarantine
    rendered = repr(quarantine.public_summary())
    assert "plaintext" not in rendered
    assert "private_key" not in rendered
