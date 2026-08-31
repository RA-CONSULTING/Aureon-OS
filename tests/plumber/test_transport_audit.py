from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

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
