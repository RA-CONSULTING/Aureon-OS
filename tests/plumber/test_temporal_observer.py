from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from aureon.plumber.observer_transcript import ObserverTranscriptV0
from aureon.plumber.packet import PacketReplayGuard
from aureon.plumber.schema import DenialCode, SchemaError
from aureon.plumber.temporal_identity import TemporalIdentityV0

DIGESTS = tuple(f"{number:064x}" for number in range(1, 20))
NOW = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)


def _temporal() -> TemporalIdentityV0:
    return TemporalIdentityV0.build(
        packet_identity="packet-1",
        session_identity="session-1",
        previous_state_commitment=DIGESTS[0],
        nonce_commitment=DIGESTS[1],
        counter=8,
        field_receipt_commitment=DIGESTS[2],
        observer_receipt_commitment=DIGESTS[3],
        runtime_measurement_commitment=DIGESTS[4],
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
    )


def test_temporal_identity_detects_replay_rollback_and_state_mismatch() -> None:
    identity = _temporal()
    assert identity.validate(
        now=NOW + timedelta(seconds=1),
        expected_previous_state_commitment=DIGESTS[0],
        minimum_counter=7,
    ).valid
    result = identity.validate(
        now=NOW + timedelta(seconds=1),
        expected_previous_state_commitment=DIGESTS[9],
        minimum_counter=8,
        seen_nonce_commitments={identity.nonce_commitment},
    )
    assert not result.valid
    assert set(result.denial_codes) == {
        DenialCode.COUNTER_ROLLBACK,
        DenialCode.PREVIOUS_STATE_MISMATCH,
        DenialCode.REPLAY_DETECTED,
    }
    assert DenialCode.STALE_STATE in identity.validate(
        now=NOW + timedelta(minutes=5),
        expected_previous_state_commitment=DIGESTS[0],
        minimum_counter=7,
    ).denial_codes


def test_replay_guard_requires_one_time_anchor_and_advances_temporal_head() -> None:
    identity = _temporal()
    guard = PacketReplayGuard()
    assert guard.register_temporal_anchor(
        identity.session_identity,
        expected_previous_state_commitment=identity.previous_state_commitment,
        minimum_counter=identity.counter - 1,
        expected_field_receipt_commitment=identity.field_receipt_commitment,
        expected_runtime_measurement_commitment=identity.runtime_measurement_commitment,
    )
    assert not guard.register_temporal_anchor(
        identity.session_identity,
        expected_previous_state_commitment=identity.previous_state_commitment,
        minimum_counter=identity.counter - 1,
        expected_field_receipt_commitment=identity.field_receipt_commitment,
        expected_runtime_measurement_commitment=identity.runtime_measurement_commitment,
    )
    first_token = DIGESTS[10]
    assert guard.reserve_temporal(identity, first_token, now=NOW + timedelta(seconds=1))
    assert guard.has_seen(first_token)
    assert not guard.reserve_temporal(identity, DIGESTS[11], now=NOW + timedelta(seconds=1))
    assert guard.consume(first_token)
    assert not guard.consume(first_token)

    successor = TemporalIdentityV0.build(
        packet_identity=identity.packet_identity,
        session_identity=identity.session_identity,
        previous_state_commitment=identity.temporal_commitment,
        nonce_commitment=DIGESTS[12],
        counter=identity.counter + 1,
        field_receipt_commitment=identity.field_receipt_commitment,
        observer_receipt_commitment=identity.observer_receipt_commitment,
        runtime_measurement_commitment=identity.runtime_measurement_commitment,
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
    )
    assert guard.reserve_temporal(successor, DIGESTS[13], now=NOW + timedelta(seconds=1))
    summary = guard.public_summary()
    assert identity.previous_state_commitment not in repr(summary)
    assert identity.runtime_measurement_commitment not in repr(summary)


@pytest.mark.parametrize(
    "anchor_override",
    (
        {"expected_previous_state_commitment": DIGESTS[14]},
        {"minimum_counter": 8},
        {"expected_field_receipt_commitment": DIGESTS[15]},
        {"expected_runtime_measurement_commitment": DIGESTS[16]},
    ),
)
def test_replay_guard_rejects_each_untrusted_temporal_anchor_join(
    anchor_override: dict[str, object],
) -> None:
    identity = _temporal()
    anchor: dict[str, object] = {
        "expected_previous_state_commitment": identity.previous_state_commitment,
        "minimum_counter": identity.counter - 1,
        "expected_field_receipt_commitment": identity.field_receipt_commitment,
        "expected_runtime_measurement_commitment": identity.runtime_measurement_commitment,
    }
    anchor.update(anchor_override)
    guard = PacketReplayGuard()
    assert guard.register_temporal_anchor(
        identity.session_identity,
        expected_previous_state_commitment=str(
            anchor["expected_previous_state_commitment"]
        ),
        minimum_counter=int(anchor["minimum_counter"]),
        expected_field_receipt_commitment=str(
            anchor["expected_field_receipt_commitment"]
        ),
        expected_runtime_measurement_commitment=str(
            anchor["expected_runtime_measurement_commitment"]
        ),
    )
    assert not guard.reserve_temporal(
        identity,
        DIGESTS[17],
        now=NOW + timedelta(seconds=1),
    )
    assert guard.public_summary()["reservation_count"] == 0


def test_observer_transcript_uses_fixed_decimal_strings_and_hides_raw_values() -> None:
    transcript = ObserverTranscriptV0.build(
        packet_identity="packet-1",
        session_identity="session-1",
        purpose_commitment=DIGESTS[0],
        challenge_commitment=DIGESTS[1],
        canonical_hnc_values={"coherence": "0.875", "energy": 4},
        trajectory_commitments=(DIGESTS[2], DIGESTS[3]),
        coherence="0.875",
        consciousness_proxy=None,
        symbolic_life=True,
        hnc_parameters={"lambda": "0.25"},
        rock_commitments=(),
        active_mode="stable",
        active_plateau="plateau-1",
        transition_commitment=DIGESTS[4],
        regime="bounded",
        divergence_score="0.125",
        source_receipt_commitments=(DIGESTS[5],),
    )
    restored = ObserverTranscriptV0.from_dict(transcript.to_dict())
    assert restored == transcript
    assert restored.canonical_hnc_values["energy"] == "4"
    summary = transcript.public_summary()
    assert "canonical_hnc_values" not in summary
    assert "hnc_parameters" not in summary
    assert summary["trajectory_count"] == 2

    with pytest.raises(SchemaError):
        ObserverTranscriptV0.build(
            packet_identity="packet-1",
            session_identity="session-1",
            purpose_commitment=DIGESTS[0],
            challenge_commitment=DIGESTS[1],
            canonical_hnc_values={"coherence": 0.875},
            trajectory_commitments=(DIGESTS[2],),
            coherence="0.875",
            consciousness_proxy=None,
            symbolic_life=True,
            hnc_parameters={"lambda": "0.25"},
            rock_commitments=(),
            active_mode="stable",
            active_plateau="plateau-1",
            transition_commitment=DIGESTS[4],
            regime="bounded",
            divergence_score="0.125",
            source_receipt_commitments=(DIGESTS[5],),
        )
