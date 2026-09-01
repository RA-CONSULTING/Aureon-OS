from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

import pytest

from aureon.harmonic.hnc_quantum_packet_crypto import (
    decode_hnc_quantum_packet,
    validate_hnc_packet_contract,
)
from aureon.plumber.crypto import canonical_json_bytes, domain_hash, sha256_hex
from aureon.plumber.os_protection import (
    MAX_OPERATOR_AAD_BYTES,
    OS_INGRESS_AAD_SCHEMA,
    OS_QUARANTINE_EVIDENCE_PURPOSE,
    AdmittedHNC,
    IngressDisposition,
    LocalOSProtectionBoundary,
    OSProtectionError,
    QuarantinedHNC,
)
from aureon.plumber.star_custody_v02 import (
    LocalDevelopmentStarCustodyV02,
    ProtectedMagicStarPacketV02,
)

NOW = datetime(2030, 3, 14, 15, 9, 26, tzinfo=UTC)
MASTER_KEY = b"local-os-protection-test-key-material"
PURPOSE = "aureon.local.document.import"
SOURCE_ID = "file-drop:test-fixture"
INGRESS_KIND = "document/octet-stream"
CALLER_AAD = {"route": "local-test", "request_id": "request-7"}
SECRET = b"never-include-this-plaintext-canary"


def _boundary(
    *,
    key: bytes | str | None = MASTER_KEY,
    max_ingress_bytes: int = 1024,
    **limits: Any,
) -> LocalOSProtectionBoundary:
    return LocalOSProtectionBoundary(
        boundary_id="test-whole-os-boundary",
        master_key_provider=lambda: key,
        max_ingress_bytes=max_ingress_bytes,
        trusted_now=lambda: NOW,
        **limits,
    )


def _admit(
    boundary: LocalOSProtectionBoundary,
    raw: bytes = SECRET,
    **overrides: Any,
) -> AdmittedHNC | QuarantinedHNC:
    values: dict[str, Any] = {
        "source_id": SOURCE_ID,
        "ingress_kind": INGRESS_KIND,
        "purpose": PURPOSE,
        "operator_aad": CALLER_AAD,
    }
    values.update(overrides)
    return boundary.admit_external(raw, **values)


def test_bounded_ingress_is_hnc_authenticated_behind_opaque_handle() -> None:
    boundary = _boundary()

    outcome = _admit(boundary)

    assert isinstance(outcome, AdmittedHNC)
    assert outcome.disposition is IngressDisposition.ADMITTED_HNC
    assert outcome.content_sha256 == hashlib.sha256(SECRET).hexdigest()
    assert outcome.content_size_bytes == len(SECRET)
    assert outcome.hnc_payload_binding.purpose_commitment == domain_hash(
        "aureon.plumber.purpose.v0",
        PURPOSE,
    )
    public = outcome.public_summary()
    rendered = json.dumps(public, sort_keys=True)
    assert SECRET.decode() not in rendered
    assert outcome.handle.token not in rendered
    assert "ciphertext_b64" not in rendered
    assert "nonce_b64" not in rendered

    # White-box inspection proves that the private carrier binds the exact
    # ingress contract while the public outcome exposes only commitments.
    record = boundary._records[outcome.admission_id]
    validation = validate_hnc_packet_contract(record.packet)
    assert validation["valid"] is True
    aad = record.packet["operator_aad"]
    assert aad == {
        "schema": OS_INGRESS_AAD_SCHEMA,
        "boundary_id": "test-whole-os-boundary",
        "source_id": SOURCE_ID,
        "ingress_kind": INGRESS_KIND,
        "content_sha256": hashlib.sha256(SECRET).hexdigest(),
        "content_size_bytes": len(SECRET),
        "purpose": PURPOSE,
        "purpose_commitment": domain_hash("aureon.plumber.purpose.v0", PURPOSE),
        "caller_aad": CALLER_AAD,
        "source_truth_established_by_local_wrapping": False,
    }
    assert outcome.operator_aad_sha256 == sha256_hex(canonical_json_bytes(aad))


def test_mutable_payload_and_nested_aad_are_snapshotted_before_sealing() -> None:
    raw = bytearray(SECRET)
    caller_aad = {"nested": ["original"]}

    def mutating_key_provider() -> bytes:
        raw[:] = b"X" * len(raw)
        caller_aad["nested"][0] = "mutated"
        return MASTER_KEY

    boundary = LocalOSProtectionBoundary(
        boundary_id="snapshot-boundary",
        master_key_provider=mutating_key_provider,
        max_ingress_bytes=1024,
        trusted_now=lambda: NOW,
    )

    outcome = boundary.admit_external(
        raw,
        source_id=SOURCE_ID,
        ingress_kind=INGRESS_KIND,
        purpose=PURPOSE,
        operator_aad=caller_aad,
    )

    assert isinstance(outcome, AdmittedHNC)
    record = boundary._records[outcome.admission_id]
    decoded = decode_hnc_quantum_packet(
        record.packet,
        MASTER_KEY,
        expected_purpose=PURPOSE,
    )
    assert decoded.plaintext == SECRET
    assert record.packet["operator_aad"]["caller_aad"] == {"nested": ["original"]}
    assert outcome.content_sha256 == hashlib.sha256(decoded.plaintext).hexdigest()


def test_simultaneous_duplicate_ingress_has_one_atomic_winner() -> None:
    boundary = _boundary()

    with ThreadPoolExecutor(max_workers=12) as pool:
        outcomes = list(pool.map(lambda _index: _admit(boundary), range(24)))

    admitted = [item for item in outcomes if isinstance(item, AdmittedHNC)]
    quarantined = [item for item in outcomes if isinstance(item, QuarantinedHNC)]
    assert len(admitted) == 1
    assert len(quarantined) == 23
    assert all("ingress_replay_detected" in item.denial_codes for item in quarantined)
    assert len({item.replay_token for item in outcomes}) == 1
    assert boundary.public_summary()["active_opaque_handle_count"] == 1


@pytest.mark.parametrize(
    ("raw", "max_ingress_bytes", "validator", "expected_code"),
    [
        (SECRET, 8, None, "ingress_too_large"),
        (SECRET, 1024, lambda _view: False, "ingress_content_invalid"),
        (SECRET, 1024, lambda _view: "truthy-not-bool", "ingress_content_invalid"),
    ],
)
def test_rejected_material_creates_metadata_only_hnc_quarantine(
    raw: bytes,
    max_ingress_bytes: int,
    validator: Any,
    expected_code: str,
) -> None:
    boundary = _boundary(max_ingress_bytes=max_ingress_bytes)

    outcome = _admit(boundary, raw, content_validator=validator)

    assert isinstance(outcome, QuarantinedHNC)
    assert outcome.disposition is IngressDisposition.QUARANTINED_HNC
    assert expected_code in outcome.denial_codes
    assert outcome.hnc_evidence_binding is not None
    assert boundary._records == {}
    rendered = json.dumps(outcome.public_summary(), sort_keys=True)
    assert raw.decode() not in rendered
    assert outcome.public_summary()["raw_material_retained"] is False

    evidence_packet = boundary._quarantine_packets[outcome.admission_id]
    decoded = decode_hnc_quantum_packet(
        evidence_packet,
        MASTER_KEY,
        expected_purpose=OS_QUARANTINE_EVIDENCE_PURPOSE,
    )
    evidence = json.loads(decoded.plaintext)
    assert evidence["content_sha256"] == hashlib.sha256(raw).hexdigest()
    assert evidence["content_size_bytes"] == len(raw)
    assert evidence["raw_material_retained"] is False
    assert raw not in decoded.plaintext
    assert raw.decode() not in json.dumps(evidence, sort_keys=True)


def test_magic_star_capacity_is_preflighted_before_handle_issue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boundary = _boundary(max_ingress_bytes=2048)
    monkeypatch.setattr(
        "aureon.plumber.star_custody_v02._MAX_INNER_BYTES",
        512,
    )

    outcome = _admit(boundary, b"X" * 1024)

    assert isinstance(outcome, QuarantinedHNC)
    assert "magic_star_inner_capacity_exceeded" in outcome.denial_codes
    summary = boundary.public_summary()
    assert summary["active_opaque_handle_count"] == 0
    assert summary["consumed_opaque_handle_count"] == 0
    assert summary["active_ingress_bytes"] == 0
    assert outcome.public_summary()["raw_material_retained"] is False


@pytest.mark.parametrize(
    ("key", "expected_code"),
    [(None, "master_key_unavailable"), (b"short", "master_key_invalid")],
)
def test_missing_or_invalid_master_key_fails_closed(
    key: bytes | None,
    expected_code: str,
) -> None:
    boundary = _boundary(key=key)

    outcome = _admit(boundary)

    assert isinstance(outcome, QuarantinedHNC)
    assert expected_code in outcome.denial_codes
    assert outcome.hnc_evidence_binding is None
    assert boundary._records == {}
    assert boundary._quarantine_packets == {}
    assert SECRET.decode() not in json.dumps(outcome.public_summary(), sort_keys=True)


def test_invalid_hnc_packet_contract_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boundary = _boundary()

    monkeypatch.setattr(
        "aureon.plumber.os_protection.build_hnc_quantum_packet",
        lambda *_args, **_kwargs: {"invalid": True},
    )
    outcome = _admit(boundary)

    assert isinstance(outcome, QuarantinedHNC)
    assert "hnc_packet_seal_failed" in outcome.denial_codes
    assert "quarantine_hnc_evidence_unavailable" in outcome.denial_codes
    assert outcome.hnc_evidence_binding is None
    assert boundary._records == {}


def test_malformed_non_bytes_input_is_quarantined_without_retaining_it() -> None:
    boundary = _boundary()
    malformed = {"secret": SECRET.decode()}
    malformed_payload: Any = malformed

    outcome = boundary.admit_external(
        malformed_payload,
        source_id=SOURCE_ID,
        ingress_kind=INGRESS_KIND,
        purpose=PURPOSE,
        operator_aad=CALLER_AAD,
    )

    assert isinstance(outcome, QuarantinedHNC)
    assert "ingress_bytes_invalid" in outcome.denial_codes
    assert boundary._records == {}
    assert malformed["secret"] not in json.dumps(outcome.public_summary(), sort_keys=True)


@pytest.mark.parametrize(
    "operator_aad",
    [
        {"oversized": "X" * (MAX_OPERATOR_AAD_BYTES + 1)},
        {"unsupported": 1.5},
        {"too_many_nodes": list(range(5000))},
    ],
)
def test_unbounded_or_noncanonical_operator_aad_is_quarantined(
    operator_aad: dict[str, Any],
) -> None:
    boundary = _boundary()

    outcome = _admit(boundary, operator_aad=operator_aad)

    assert isinstance(outcome, QuarantinedHNC)
    assert "operator_aad_invalid" in outcome.denial_codes
    assert boundary._records == {}


def test_magic_star_handoff_consumes_handle_before_downstream_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boundary = _boundary()
    admitted = _admit(boundary)
    assert isinstance(admitted, AdmittedHNC)
    custody = object.__new__(LocalDevelopmentStarCustodyV02)
    captured: dict[str, Any] = {}

    def fake_protect_carrier(
        _self: LocalDevelopmentStarCustodyV02,
        **kwargs: Any,
    ) -> ProtectedMagicStarPacketV02:
        captured.update(kwargs)
        return ProtectedMagicStarPacketV02(
            magic="test-magic",
            schema="test-schema",
            protocol_id="test-protocol",
            profile_id="test-profile",
            source_profile_commitment="0" * 64,
            packet_id=kwargs["packet_id"],
            purpose=kwargs["purpose"],
            release_context_sha256=kwargs["release_context_sha256"],
            carrier_commitment="1" * 64,
            share_bindings=(),
            nonce_b64="AA",
            ciphertext_b64="AA",
            aad_sha256="2" * 64,
            source_signature={"test_only": True},
        )

    monkeypatch.setattr(LocalDevelopmentStarCustodyV02, "protect_carrier", fake_protect_carrier)
    release_context = hashlib.sha256(b"release-context").hexdigest()

    protected = boundary.protect_for_magic_star(
        admitted.handle,
        custody=custody,
        release_context_sha256=release_context,
    )

    assert protected.packet_id == admitted.admission_id
    assert validate_hnc_packet_contract(captured["legacy_carrier"])["valid"] is True
    assert captured["legacy_master_key"] == MASTER_KEY
    assert boundary.public_summary()["active_opaque_handle_count"] == 0
    assert boundary.public_summary()["consumed_opaque_handle_count"] == 1
    with pytest.raises(
        OSProtectionError,
        match="opaque_hnc_handle_unavailable_or_replayed",
    ):
        boundary.protect_for_magic_star(
            admitted.handle,
            custody=custody,
            release_context_sha256=release_context,
        )


def test_held_admission_can_be_burned_without_release_or_decode() -> None:
    boundary = _boundary()
    admitted = _admit(boundary)
    assert isinstance(admitted, AdmittedHNC)

    receipt = boundary.discard_admitted(
        admitted.handle,
        reason_code="production_magic_star_release_unavailable",
    )

    assert receipt["disposition"] == "DISCARDED_HNC"
    assert receipt["carrier_released"] is False
    assert receipt["plaintext_decoded"] is False
    assert boundary.public_summary()["active_opaque_handle_count"] == 0
    assert boundary.public_summary()["active_ingress_bytes"] == 0
    with pytest.raises(
        OSProtectionError,
        match="opaque_hnc_handle_unavailable_or_replayed",
    ):
        boundary.discard_admitted(
            admitted.handle,
            reason_code="replay",
        )


def test_boundary_reports_local_nonproduction_scope() -> None:
    summary = _boundary().public_summary()

    assert LocalOSProtectionBoundary.production_ready is False
    assert summary["scope"] == "in_memory_local_development_only"
    assert summary["persistent"] is False
    assert summary["local_development_only"] is True
    assert summary["production_ready"] is False
    assert summary["raw_material_returned"] is False


def test_active_admission_and_replay_ledgers_are_bounded_fail_closed() -> None:
    boundary = _boundary(
        max_active_handles=1,
        max_active_ingress_bytes=len(SECRET),
        max_replay_tokens=2,
    )

    first = _admit(boundary, b"first")
    second = _admit(boundary, b"second")
    third = _admit(boundary, b"third")

    assert isinstance(first, AdmittedHNC)
    assert isinstance(second, QuarantinedHNC)
    assert "active_admission_capacity_exhausted" in second.denial_codes
    assert isinstance(third, QuarantinedHNC)
    assert "replay_ledger_capacity_exhausted" in third.denial_codes
    summary = boundary.public_summary()
    assert summary["active_opaque_handle_count"] == 1
    assert summary["active_ingress_bytes"] == len(b"first")
    assert summary["seen_replay_count"] == 2


def test_concurrent_unique_ingress_cannot_race_past_active_capacity() -> None:
    payloads = [f"unique-{index:02d}".encode() for index in range(24)]
    boundary = _boundary(
        max_active_handles=4,
        max_active_ingress_bytes=4 * len(payloads[0]),
        max_replay_tokens=len(payloads),
        max_quarantine_evidence=len(payloads),
    )

    with ThreadPoolExecutor(max_workers=12) as pool:
        outcomes = list(
            pool.map(
                lambda raw: _admit(
                    boundary,
                    raw,
                    source_id=f"source:{raw.decode()}",
                ),
                payloads,
            )
        )

    admitted = [item for item in outcomes if isinstance(item, AdmittedHNC)]
    quarantined = [item for item in outcomes if isinstance(item, QuarantinedHNC)]
    assert len(admitted) == 4
    assert len(quarantined) == 20
    assert all(
        "active_admission_capacity_exhausted" in item.denial_codes
        for item in quarantined
    )
    summary = boundary.public_summary()
    assert summary["active_opaque_handle_count"] == 4
    assert summary["active_ingress_bytes"] == 4 * len(payloads[0])


def test_quarantine_evidence_store_is_bounded() -> None:
    boundary = _boundary(max_quarantine_evidence=1)

    first = _admit(boundary, b"", source_id="empty-one")
    second = _admit(boundary, b"", source_id="empty-two")

    assert isinstance(first, QuarantinedHNC)
    assert first.hnc_evidence_binding is not None
    assert isinstance(second, QuarantinedHNC)
    assert "quarantine_evidence_capacity_exhausted" in second.denial_codes
    assert second.hnc_evidence_binding is None
    assert boundary.public_summary()["quarantine_evidence_count"] == 1


@pytest.mark.parametrize(
    ("key", "ready", "reason"),
    [
        (MASTER_KEY, True, "ready"),
        (None, False, "master_key_unavailable"),
        (b"short", False, "master_key_invalid"),
    ],
)
def test_key_preflight_returns_metadata_only(
    key: bytes | None,
    ready: bool,
    reason: str,
) -> None:
    preflight = _boundary(key=key).key_preflight()

    assert preflight["schema"] == "aureon.plumber.os-key-preflight.v0"
    assert preflight["ready"] is ready
    assert preflight["reason_code"] == reason
    assert preflight["key_material_returned"] is False
    assert preflight["admission_authorized"] is False
    assert MASTER_KEY.hex() not in json.dumps(preflight, sort_keys=True)
