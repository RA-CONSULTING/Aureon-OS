from __future__ import annotations

import hashlib
import json
from dataclasses import fields, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from aureon.operator.hnc_scorm_coherence import (
    ASSESSMENT_CONTROL,
    ASSESSMENT_RESPONSE,
    BOUND_WINDOW_SURFACE,
    CONTINUE,
    COORDINATE_CONTROL,
    CREDENTIAL_COMMIT_CONTROL,
    CREDENTIAL_MUTATION,
    FRAME_WAIT,
    NATIVE_ACCESSIBILITY_CONTROL,
    NAVIGATION,
    NAVIGATION_CONTROL,
    NO_CREDENTIAL_EFFECT,
    OWNER_ATTESTATION_REQUIRED,
    OWNER_BENCHMARK_ASSERTED,
    PREVIEW_ONLY,
    PROVIDER_VERIFIED,
    PUBLIC_PREVIEW,
    READY_FOR_INTENT,
    REAL_IDENTITY_BOUND,
    RESUMABLE_PAUSE,
    SIGNED_BENCHMARK_CONTROL_RECEIPT,
    SIGNED_OWNER_BENCHMARK_LAUNCH_RECEIPT,
    SYNTHETIC_BENCHMARK,
    SYNTHETIC_PERSONA_BENCHMARK,
    HNCScormCoherenceGate,
    SCORMActionIntent,
    SCORMActionReplayLedger,
    SCORMActionTargetEvidence,
    SCORMBenchmarkGrant,
    SCORMCoherenceError,
    SCORMFrameEvidence,
    SCORMGrantContextError,
    SCORMGrantFormatError,
    SCORMGrantSignatureError,
    SCORMOwnerBenchmarkLaunchAuthority,
    SCORMPreflightDecision,
    SCORMProviderAttestationReceipt,
    SCORMProviderContextEvidence,
    SCORMReplayError,
    SCORMRunAuthority,
    SCORMTargetBounds,
    canonical_synthetic_persona_sha256,
    canonical_visible_evidence_sha256,
    canonical_visible_text_sha256,
    classify_visible_prerequisite,
)
from aureon.operator.local_gui_observer import OCRToken

_SECRET = b"hnc-scorm-receipt-secret-distinct-0000000001"
_OWNER_SECRET = b"owner-benchmark-control-secret-00000000000002"
_OTHER_OWNER_SECRET = b"other-owner-control-secret-0000000000000003"
_PROVIDER_PRIVATE_KEY = Ed25519PrivateKey.generate()
_PROVIDER_PUBLIC_KEY = _PROVIDER_PRIVATE_KEY.public_key().public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw,
)
_NOW = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)
_ORIGIN = "https://cloud.scorm.com"


def _h(character: str) -> str:
    return character * 64


def _authority(
    *,
    allowed_origin: str = _ORIGIN,
    run_manifest_sha256: str = _h("1"),
    launch_url_sha256: str = _h("2"),
    launch_plan_sha256: str = _h("3"),
    control_grant_sha256: str = _h("4"),
) -> SCORMRunAuthority:
    return SCORMRunAuthority.issue(
        secret=_SECRET,
        run_id="scorm-run-001",
        run_manifest_sha256=run_manifest_sha256,
        replay_nonce="stable-run-replay-nonce-001",
        allowed_origin=allowed_origin,
        launch_url_sha256=launch_url_sha256,
        launch_plan_sha256=launch_plan_sha256,
        control_grant_sha256=control_grant_sha256,
        allowed_actions=("left_click", "move_mouse", "wait"),
        max_actions=100,
        issued_at=_NOW - timedelta(minutes=5),
        expires_at=_NOW + timedelta(hours=1),
    )


def _owner_launch(
    authority: SCORMRunAuthority,
    *,
    owner_secret: bytes = _OWNER_SECRET,
    native_live_url_sha256: str | None = None,
    synthetic_persona_id: str = "john-brown-synthetic-v1",
    window_binding_id: str = "window-binding-001",
    window_generation: int = 3,
    window_identity_sha256: str = _h("c"),
) -> SCORMOwnerBenchmarkLaunchAuthority:
    return SCORMOwnerBenchmarkLaunchAuthority.issue(
        owner_secret=owner_secret,
        issuer="aureon-owner-benchmark-control",
        key_id="owner-key-001",
        synthetic_persona_id=synthetic_persona_id,
        run_authority=authority,
        native_live_url_sha256=(
            authority.launch_url_sha256
            if native_live_url_sha256 is None
            else native_live_url_sha256
        ),
        native_address_bar_receipt_sha256=_h("6"),
        active_session_id="active-session-001",
        window_binding_id=window_binding_id,
        window_generation=window_generation,
        window_identity_sha256=window_identity_sha256,
        issued_at=_NOW - timedelta(minutes=4),
        expires_at=_NOW + timedelta(minutes=50),
    )


def _provider_receipt(
    authority: SCORMRunAuthority,
    *,
    private_key: Ed25519PrivateKey = _PROVIDER_PRIVATE_KEY,
    key_id: str = "provider-key-001",
) -> SCORMProviderAttestationReceipt:
    unsigned = SCORMProviderAttestationReceipt(
        issuer="external-scorm-provider",
        key_id=key_id,
        attestation_type=SIGNED_BENCHMARK_CONTROL_RECEIPT,
        run_id=authority.run_id,
        run_manifest_sha256=authority.run_manifest_sha256,
        run_authority_sha256=authority.run_authority_sha256,
        allowed_origin=authority.allowed_origin,
        launch_url_sha256=authority.launch_url_sha256,
        launch_plan_sha256=authority.launch_plan_sha256,
        control_grant_sha256=authority.control_grant_sha256,
        live_url_sha256=authority.launch_url_sha256,
        native_address_bar_receipt_sha256=_h("6"),
        registration_state=PUBLIC_PREVIEW,
        registration_evidence_kind="provider_public_preview_marker",
        registration_evidence_sha256=_h("7"),
        permitted_credential_effects=tuple(sorted((NO_CREDENTIAL_EFFECT, PREVIEW_ONLY))),
        provider_metadata_sha256=_h("8"),
        issued_at_unix=int((_NOW - timedelta(minutes=4)).timestamp()),
        expires_at_unix=int((_NOW + timedelta(minutes=50)).timestamp()),
        signature_hex="0" * 128,
    )
    payload = json.dumps(
        unsigned.signed_payload(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return replace(unsigned, signature_hex=private_key.sign(payload).hex())


def _provider_bundle(
    *,
    visible_text: str = "External provider lesson",
) -> tuple[
    SCORMRunAuthority,
    SCORMProviderAttestationReceipt,
    SCORMProviderContextEvidence,
    SCORMFrameEvidence,
]:
    authority = _authority()
    receipt = _provider_receipt(authority)
    context = SCORMProviderContextEvidence.issue(
        secret=_SECRET,
        run_authority=authority,
        launch_authority=receipt,
        source_observation_sha256=_h("9"),
        source_screenshot_sha256=_h("a"),
        visible_evidence_sha256=_h("b"),
        visible_text=visible_text,
        active_session_id="active-session-001",
        live_origin=_ORIGIN,
        window_binding_id="window-binding-001",
        window_generation=3,
        window_identity_sha256=_h("c"),
        issued_at=_NOW - timedelta(minutes=1),
        expires_at=_NOW + timedelta(minutes=30),
    )
    return authority, receipt, context, SCORMFrameEvidence.from_context(
        context, visible_text=visible_text
    )


def _bundle(
    *,
    visible_text: str = "SCORM lesson. Continue to the next section.",
    owner_secret: bytes = _OWNER_SECRET,
) -> tuple[
    SCORMRunAuthority,
    SCORMOwnerBenchmarkLaunchAuthority,
    SCORMProviderContextEvidence,
    SCORMFrameEvidence,
]:
    authority = _authority()
    launch_authority = _owner_launch(authority, owner_secret=owner_secret)
    context = SCORMProviderContextEvidence.issue(
        secret=_SECRET,
        run_authority=authority,
        launch_authority=launch_authority,
        source_observation_sha256=_h("9"),
        source_screenshot_sha256=_h("a"),
        visible_evidence_sha256=_h("b"),
        visible_text=visible_text,
        active_session_id="active-session-001",
        live_origin=_ORIGIN,
        window_binding_id="window-binding-001",
        window_generation=3,
        window_identity_sha256=_h("c"),
        issued_at=_NOW - timedelta(minutes=1),
        expires_at=_NOW + timedelta(minutes=30),
    )
    return (
        authority,
        launch_authority,
        context,
        SCORMFrameEvidence.from_context(context, visible_text=visible_text),
    )


def _gate(
    *,
    ledger: SCORMActionReplayLedger | None = None,
) -> HNCScormCoherenceGate:
    return HNCScormCoherenceGate(
        _SECRET,
        owner_benchmark_keys={"owner-key-001": _OWNER_SECRET},
        replay_ledger=ledger,
    )


def _intent(
    frame: SCORMFrameEvidence,
    *,
    name: str = "left_click",
    x: int = 620,
    y: int = 440,
    sequence: int = 1,
) -> SCORMActionIntent:
    params: dict[str, object] = {"seconds": 0.5} if name == "wait" else {"x": x, "y": y}
    return SCORMActionIntent.from_action(
        name,
        params,
        action_sequence=sequence,
        source_observation_sha256=frame.source_observation_sha256,
    )


def _target(
    context: SCORMProviderContextEvidence,
    frame: SCORMFrameEvidence,
    intent: SCORMActionIntent,
    *,
    semantic: str = NAVIGATION_CONTROL,
    credential_effect: str = NO_CREDENTIAL_EFFECT,
    owner_secret: bytes = _OWNER_SECRET,
    target_evidence_sha256: str = _h("d"),
) -> SCORMActionTargetEvidence:
    if intent.name == "wait":
        surface = FRAME_WAIT
        bounds = None
        evidence_kind = BOUND_WINDOW_SURFACE
        role_hash = None
        name_hash = None
    else:
        surface = COORDINATE_CONTROL
        bounds = SCORMTargetBounds(x=580, y=410, width=160, height=70)
        evidence_kind = NATIVE_ACCESSIBILITY_CONTROL
        role_hash = _h("e")
        name_hash = _h("f")
    return SCORMActionTargetEvidence.issue(
        owner_secret=owner_secret,
        provider_context=context,
        frame=frame,
        intent=intent,
        target_surface=surface,
        target_bounds=bounds,
        target_evidence_kind=evidence_kind,
        target_evidence_sha256=target_evidence_sha256,
        accessibility_role_sha256=role_hash,
        accessibility_name_sha256=name_hash,
        accessibility_automation_id_sha256=None,
        target_semantic=semantic,
        interaction_evidence_kind="owner_native_target_semantic",
        interaction_evidence_sha256=_h("0"),
        credential_effect=credential_effect,
        effect_evidence_kind="owner_native_credential_effect",
        effect_evidence_sha256=_h("1"),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=4),
    )


def _grant(
    authority: SCORMRunAuthority,
    context: SCORMProviderContextEvidence,
    frame: SCORMFrameEvidence,
    intent: SCORMActionIntent,
    target: SCORMActionTargetEvidence,
) -> SCORMBenchmarkGrant:
    return SCORMBenchmarkGrant.issue(
        owner_secret=_OWNER_SECRET,
        benchmark_id="preview-assessment-action-v1",
        replay_nonce="per-action-replay-nonce-001",
        run_authority=authority,
        provider_context=context,
        frame=frame,
        intent=intent,
        action_target=target,
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=3),
    )


def _preflight(
    gate: HNCScormCoherenceGate,
    authority: SCORMRunAuthority,
    context: SCORMProviderContextEvidence,
    frame: SCORMFrameEvidence,
) -> SCORMPreflightDecision:
    return gate.classify_preflight(
        frame,
        run_authority=authority,
        provider_context=context,
        now=_NOW,
    )


def test_preflight_is_frame_only_and_ready_decision_cannot_authorize() -> None:
    authority, _attestation_value, context, frame = _bundle()
    with _gate() as gate:
        preflight = _preflight(gate, authority, context, frame)
    assert preflight.kind == READY_FOR_INTENT
    names = {field.name for field in fields(preflight)}
    assert "interaction_kind" not in names
    assert "credential_effect" not in names
    assert "benchmark_grant_sha256" not in names


@pytest.mark.parametrize(
    ("visible_text", "prerequisite"),
    [
        ("Sign in to continue", "login"),
        ("Email Password Continue", "login"),
        ("Enter verification code", "mfa"),
        ("Enter your authenticator verification code", "mfa"),
        ("Complete CAPTCHA", "captcha"),
        ("Identity verification required", "identity"),
        (
            "ERROR The request could not be satisfied. Generated by cloudfront",
            "authorization",
        ),
        (
            "Missing Key-Pair-Id query parameter or cookie value",
            "authorization",
        ),
    ],
)
def test_preflight_shared_prerequisites_pause_resumably(
    visible_text: str,
    prerequisite: str,
) -> None:
    authority, _attestation_value, context, frame = _bundle(visible_text=visible_text)
    with _gate() as gate:
        preflight = _preflight(gate, authority, context, frame)
    assert preflight.kind == RESUMABLE_PAUSE
    assert preflight.prerequisite == prerequisite
    assert classify_visible_prerequisite(visible_text) == prerequisite


def test_cloudfront_prerequisite_requires_exact_error_context() -> None:
    assert (
        classify_visible_prerequisite(
            "The lesson explains why a request could not be satisfied."
        )
        is None
    )
    assert classify_visible_prerequisite("CloudFront architecture overview") is None


def test_visible_text_is_exact_nfc_and_cryptographically_bound() -> None:
    authority, _attestation_value, context, frame = _bundle(visible_text="Café lesson")
    assert context.visible_text_sha256 == canonical_visible_text_sha256("Café lesson")
    with pytest.raises(SCORMGrantContextError, match="visible_text"):
        replace(frame, visible_text="Different lesson")
    changed_text = "Different lesson"
    changed_frame = replace(
        frame,
        visible_text=changed_text,
        visible_text_sha256=canonical_visible_text_sha256(changed_text),
    )
    with _gate() as gate, pytest.raises(SCORMGrantContextError, match="frame does not match"):
        _preflight(gate, authority, context, changed_frame)
    with pytest.raises(SCORMCoherenceError, match="NFC"):
        canonical_visible_text_sha256("Cafe\u0301")


@pytest.mark.parametrize(
    "origin",
    [
        "http://cloud.scorm.com",
        "https://127.0.0.1",
        "https://10.0.0.4",
        "https://localhost",
        "https://training.internal",
        "https://cloud.scorm.com@evil.example",
        "https://user:pass@cloud.scorm.com",
        "https://cloud.scorm.com/path",
    ],
)
def test_run_authority_rejects_nonpublic_or_noncanonical_origin(origin: str) -> None:
    with pytest.raises(SCORMCoherenceError):
        _authority(allowed_origin=origin)


@pytest.mark.parametrize(
    "trap",
    ["https://cloud.scorm.com.evil.example", "https://evil-cloud.scorm.com"],
)
def test_exact_allowed_origin_rejects_public_suffix_and_lookalike_traps(trap: str) -> None:
    authority, _attestation_value, context, frame = _bundle()
    trapped = replace(frame, live_origin=trap)
    with _gate() as gate, pytest.raises(SCORMGrantContextError, match="frame does not match"):
        _preflight(gate, authority, context, trapped)


@pytest.mark.parametrize(
    ("field", "changed"),
    [
        ("run_manifest_sha256", _h("d")),
        ("launch_url_sha256", _h("e")),
        ("launch_plan_sha256", _h("f")),
        ("control_grant_sha256", _h("0")),
    ],
)
def test_exact_run_launch_plan_and_control_hashes_cannot_drift(
    field: str,
    changed: str,
) -> None:
    authority, _attestation_value, context, frame = _bundle()
    changed_frame = replace(frame, **{field: changed})
    with _gate() as gate, pytest.raises(SCORMGrantContextError, match="frame does not match"):
        _preflight(gate, authority, context, changed_frame)


def test_owner_semantics_require_concrete_receipt_and_distinct_trusted_key() -> None:
    authority, launch_authority, context, frame = _bundle()
    assert context.launch_authority is launch_authority
    assert context.provenance == OWNER_BENCHMARK_ASSERTED
    assert context.registration_state == SYNTHETIC_BENCHMARK
    forged = replace(launch_authority, hmac_sha256="0" * 64)
    forged_context = SCORMProviderContextEvidence.issue(
        secret=_SECRET,
        run_authority=authority,
        launch_authority=forged,
        source_observation_sha256=frame.source_observation_sha256,
        source_screenshot_sha256=frame.source_screenshot_sha256,
        visible_evidence_sha256=frame.visible_evidence_sha256,
        visible_text=frame.visible_text,
        active_session_id=frame.active_session_id,
        live_origin=frame.live_origin,
        window_binding_id=frame.window_binding_id,
        window_generation=frame.window_generation,
        window_identity_sha256=frame.window_identity_sha256,
        issued_at=_NOW - timedelta(minutes=1),
        expires_at=_NOW + timedelta(minutes=20),
    )
    forged_frame = SCORMFrameEvidence.from_context(forged_context, visible_text=frame.visible_text)
    with _gate() as gate, pytest.raises(SCORMGrantSignatureError):
        _preflight(gate, authority, forged_context, forged_frame)
    with pytest.raises(ValueError, match="distinct"):
        HNCScormCoherenceGate(
            _SECRET,
            owner_benchmark_keys={"owner-key-001": _SECRET},
        )


def test_owner_launch_authority_binds_exact_native_window_persona_and_scope() -> None:
    authority = _authority()
    with pytest.raises(SCORMGrantContextError, match="native live URL"):
        _owner_launch(authority, native_live_url_sha256=_h("d"))
    launch = _owner_launch(authority)
    assert launch.provenance == OWNER_BENCHMARK_ASSERTED
    assert launch.scope == SYNTHETIC_PERSONA_BENCHMARK
    assert launch.synthetic_persona_sha256 == canonical_synthetic_persona_sha256(
        "john-brown-synthetic-v1"
    )
    assert launch.native_live_url_sha256 == authority.launch_url_sha256
    assert launch.control_grant_sha256 == authority.control_grant_sha256
    with pytest.raises(SCORMGrantContextError, match="session/window"):
        SCORMProviderContextEvidence.issue(
            secret=_SECRET,
            run_authority=authority,
            launch_authority=launch,
            source_observation_sha256=_h("9"),
            source_screenshot_sha256=_h("a"),
            visible_evidence_sha256=_h("b"),
            visible_text="Course preview",
            active_session_id="active-session-001",
            live_origin=_ORIGIN,
            window_binding_id="different-window",
            window_generation=3,
            window_identity_sha256=_h("c"),
            issued_at=_NOW - timedelta(minutes=1),
            expires_at=_NOW + timedelta(minutes=20),
        )
    with pytest.raises(SCORMGrantFormatError, match="persona identifier digest"):
        replace(launch, synthetic_persona_id="different-synthetic-persona")


def test_untrusted_owner_key_cannot_attest_frame_or_action() -> None:
    authority, _launch, context, frame = _bundle(owner_secret=_OTHER_OWNER_SECRET)
    with _gate() as gate, pytest.raises(SCORMGrantSignatureError):
        _preflight(gate, authority, context, frame)


def test_ocr_course_preview_words_never_establish_provider_provenance() -> None:
    authority, launch, context, frame = _bundle(
        visible_text="Course preview public preview unregistered assessment"
    )
    with _gate() as gate:
        preflight = _preflight(gate, authority, context, frame)
    assert preflight.kind == READY_FOR_INTENT
    assert context.launch_authority is launch
    assert frame.provenance == OWNER_BENCHMARK_ASSERTED
    assert frame.registration_state == SYNTHETIC_BENCHMARK
    assert frame.registration_evidence_kind == SIGNED_OWNER_BENCHMARK_LAUNCH_RECEIPT
    assert PROVIDER_VERIFIED not in context.to_json()


def test_provider_verified_requires_external_ed25519_receipt_not_local_hmac() -> None:
    authority, receipt, context, frame = _provider_bundle()
    assert not hasattr(SCORMProviderAttestationReceipt, "issue")
    gate = HNCScormCoherenceGate(
        _SECRET,
        provider_attestation_public_keys={"provider-key-001": _PROVIDER_PUBLIC_KEY},
    )
    preflight = _preflight(gate, authority, context, frame)
    assert preflight.kind == READY_FOR_INTENT
    assert context.launch_authority is receipt
    assert context.provenance == PROVIDER_VERIFIED

    forged_receipt = replace(receipt, signature_hex="0" * 128)
    forged_context = SCORMProviderContextEvidence.issue(
        secret=_SECRET,
        run_authority=authority,
        launch_authority=forged_receipt,
        source_observation_sha256=frame.source_observation_sha256,
        source_screenshot_sha256=frame.source_screenshot_sha256,
        visible_evidence_sha256=frame.visible_evidence_sha256,
        visible_text=frame.visible_text,
        active_session_id=frame.active_session_id,
        live_origin=frame.live_origin,
        window_binding_id=frame.window_binding_id,
        window_generation=frame.window_generation,
        window_identity_sha256=frame.window_identity_sha256,
        issued_at=_NOW - timedelta(minutes=1),
        expires_at=_NOW + timedelta(minutes=20),
    )
    forged_frame = SCORMFrameEvidence.from_context(
        forged_context, visible_text=frame.visible_text
    )
    with pytest.raises(SCORMGrantSignatureError):
        _preflight(gate, authority, forged_context, forged_frame)

    other_public_key = Ed25519PrivateKey.generate().public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    wrong_key_gate = HNCScormCoherenceGate(
        _SECRET,
        provider_attestation_public_keys={"provider-key-001": other_public_key},
    )
    with pytest.raises(SCORMGrantSignatureError):
        _preflight(wrong_key_gate, authority, context, frame)


def test_launch_authority_binds_live_url_and_native_address_receipt() -> None:
    authority, _attestation_value, context, frame = _bundle()
    wrong_url = replace(frame, live_url_sha256=_h("d"))
    wrong_receipt = replace(frame, native_address_bar_receipt_sha256=_h("e"))
    with _gate() as gate:
        with pytest.raises(SCORMGrantContextError, match="frame does not match"):
            _preflight(gate, authority, context, wrong_url)
        with pytest.raises(SCORMGrantContextError, match="frame does not match"):
            _preflight(gate, authority, context, wrong_receipt)


def test_navigation_action_requires_exact_owner_attested_target() -> None:
    authority, _attestation_value, context, frame = _bundle()
    intent = _intent(frame)
    target = _target(context, frame, intent)
    with _gate() as gate:
        preflight = _preflight(gate, authority, context, frame)
        decision = gate.classify_action(
            frame,
            preflight,
            intent,
            target,
            run_authority=authority,
            provider_context=context,
            now=_NOW,
        )
    assert decision.kind == CONTINUE
    assert decision.reason == "owner_benchmark_navigation_coherent"
    assert decision.action_target_sha256 == target.action_target_sha256


def test_owner_authority_hash_and_persona_bind_target_grant_decision_and_receipt(
    tmp_path: Path,
) -> None:
    authority, launch, context, frame = _bundle()
    intent = _intent(frame)
    target = _target(
        context,
        frame,
        intent,
        semantic=ASSESSMENT_CONTROL,
        credential_effect=PREVIEW_ONLY,
    )
    grant = _grant(authority, context, frame, intent, target)
    gate = _gate(
        ledger=SCORMActionReplayLedger(tmp_path / "authority-chain", marker_secret=_SECRET)
    )
    preflight = _preflight(gate, authority, context, frame)
    decision = gate.classify_action(
        frame,
        preflight,
        intent,
        target,
        run_authority=authority,
        provider_context=context,
        grant=grant,
        now=_NOW,
    )
    receipt = gate.authorize_action(
        frame,
        preflight,
        decision,
        intent,
        target,
        run_authority=authority,
        provider_context=context,
        grant=grant,
        now=_NOW,
    )
    expected_authority = launch.owner_launch_authority_sha256
    expected_persona = launch.synthetic_persona_sha256
    assert {
        frame.launch_authority_sha256,
        target.launch_authority_sha256,
        grant.launch_authority_sha256,
        decision.launch_authority_sha256,
        receipt.launch_authority_sha256,
    } == {expected_authority}
    assert {
        frame.synthetic_persona_sha256,
        target.synthetic_persona_sha256,
        grant.synthetic_persona_sha256,
        decision.synthetic_persona_sha256,
        receipt.synthetic_persona_sha256,
    } == {expected_persona}
    assert decision.provenance == OWNER_BENCHMARK_ASSERTED
    assert receipt.provenance == OWNER_BENCHMARK_ASSERTED
    assert PROVIDER_VERIFIED not in target.to_json()
    assert PROVIDER_VERIFIED not in grant.to_json()


def test_owner_keyed_target_cannot_claim_provider_provenance() -> None:
    _authority_value, _launch, context, frame = _bundle()
    intent = _intent(frame)
    with pytest.raises(SCORMGrantFormatError, match="cannot claim provider"):
        SCORMActionTargetEvidence.issue(
            owner_secret=_OWNER_SECRET,
            provider_context=context,
            frame=frame,
            intent=intent,
            target_surface=COORDINATE_CONTROL,
            target_bounds=SCORMTargetBounds(x=580, y=410, width=160, height=70),
            target_evidence_kind=NATIVE_ACCESSIBILITY_CONTROL,
            target_evidence_sha256=_h("d"),
            accessibility_role_sha256=_h("e"),
            accessibility_name_sha256=_h("f"),
            accessibility_automation_id_sha256=None,
            target_semantic=NAVIGATION_CONTROL,
            interaction_evidence_kind="provider_attested_target_semantic",
            interaction_evidence_sha256=_h("0"),
            credential_effect=NO_CREDENTIAL_EFFECT,
            effect_evidence_kind="owner_native_credential_effect",
            effect_evidence_sha256=_h("1"),
            issued_at=_NOW,
            expires_at=_NOW + timedelta(minutes=4),
        )


def test_mixed_navigation_frame_cannot_authorize_assessment_click_without_per_action_grant() -> None:
    authority, _attestation_value, context, frame = _bundle(
        visible_text="Lesson content with a visible assessment choice"
    )
    intent = _intent(frame)
    target = _target(
        context,
        frame,
        intent,
        semantic=ASSESSMENT_CONTROL,
        credential_effect=PREVIEW_ONLY,
    )
    with _gate() as gate:
        preflight = _preflight(gate, authority, context, frame)
        missing = gate.classify_action(
            frame,
            preflight,
            intent,
            target,
            run_authority=authority,
            provider_context=context,
            now=_NOW,
        )
        grant = _grant(authority, context, frame, intent, target)
        allowed = gate.classify_action(
            frame,
            preflight,
            intent,
            target,
            run_authority=authority,
            provider_context=context,
            grant=grant,
            now=_NOW,
        )
    assert target.interaction_kind == ASSESSMENT_RESPONSE
    assert missing.kind == RESUMABLE_PAUSE
    assert missing.prerequisite == "benchmark_grant"
    assert allowed.kind == CONTINUE
    assert allowed.benchmark_grant_sha256 == grant.benchmark_grant_sha256


def test_per_action_grant_rejects_coordinate_action_and_target_evidence_drift() -> None:
    authority, _attestation_value, context, frame = _bundle()
    intent = _intent(frame)
    target = _target(
        context,
        frame,
        intent,
        semantic=ASSESSMENT_CONTROL,
        credential_effect=PREVIEW_ONLY,
    )
    grant = _grant(authority, context, frame, intent, target)
    changed_intent = _intent(frame, x=621)
    changed_target = _target(
        context,
        frame,
        changed_intent,
        semantic=ASSESSMENT_CONTROL,
        credential_effect=PREVIEW_ONLY,
        target_evidence_sha256=_h("e"),
    )
    with _gate() as gate:
        preflight = _preflight(gate, authority, context, frame)
        changed = gate.classify_action(
            frame,
            preflight,
            changed_intent,
            changed_target,
            run_authority=authority,
            provider_context=context,
            grant=grant,
            now=_NOW,
        )
    assert changed.kind == RESUMABLE_PAUSE
    assert changed.reason == "per_action_benchmark_grant_invalid"


def test_action_target_must_match_action_digest_sequence_coordinates_and_bounds() -> None:
    authority, _attestation_value, context, frame = _bundle()
    intent = _intent(frame)
    target = _target(context, frame, intent)
    different = _intent(frame, x=621)
    with _gate() as gate:
        preflight = _preflight(gate, authority, context, frame)
        with pytest.raises(SCORMGrantContextError, match="exact frame and intent"):
            gate.classify_action(
                frame,
                preflight,
                different,
                target,
                run_authority=authority,
                provider_context=context,
                now=_NOW,
            )
    with pytest.raises(SCORMGrantFormatError, match="inside exact target bounds"):
        SCORMActionTargetEvidence.issue(
            owner_secret=_OWNER_SECRET,
            provider_context=context,
            frame=frame,
            intent=intent,
            target_surface=COORDINATE_CONTROL,
            target_bounds=SCORMTargetBounds(x=0, y=0, width=10, height=10),
            target_evidence_kind=NATIVE_ACCESSIBILITY_CONTROL,
            target_evidence_sha256=_h("d"),
            accessibility_role_sha256=_h("e"),
            accessibility_name_sha256=_h("f"),
            accessibility_automation_id_sha256=None,
            target_semantic=NAVIGATION_CONTROL,
            interaction_evidence_kind="owner_native_target_semantic",
            interaction_evidence_sha256=_h("0"),
            credential_effect=NO_CREDENTIAL_EFFECT,
            effect_evidence_kind="owner_native_credential_effect",
            effect_evidence_sha256=_h("1"),
            issued_at=_NOW,
            expires_at=_NOW + timedelta(minutes=2),
        )


def test_stale_intent_source_is_rejected_at_target_issue_classify_authorize_and_consume(
    tmp_path: Path,
) -> None:
    authority, _attestation_value, context, frame = _bundle()
    good_intent = _intent(frame)
    stale_intent = SCORMActionIntent.from_action(
        "left_click",
        {"x": 620, "y": 440},
        action_sequence=1,
        source_observation_sha256=_h("f"),
    )
    assert stale_intent.action_sha256 == good_intent.action_sha256
    with pytest.raises(SCORMGrantContextError, match="source observation"):
        _target(context, frame, stale_intent)

    good_target = _target(context, frame, good_intent)
    ledger = SCORMActionReplayLedger(tmp_path / "replay", marker_secret=_SECRET)
    gate = _gate(ledger=ledger)
    preflight = _preflight(gate, authority, context, frame)
    good_decision = gate.classify_action(
        frame,
        preflight,
        good_intent,
        good_target,
        run_authority=authority,
        provider_context=context,
        now=_NOW,
    )
    with pytest.raises(SCORMGrantContextError, match="source observation"):
        gate.classify_action(
            frame,
            preflight,
            stale_intent,
            good_target,
            run_authority=authority,
            provider_context=context,
            now=_NOW,
        )
    with pytest.raises(SCORMGrantContextError, match="source observation"):
        gate.authorize_action(
            frame,
            preflight,
            good_decision,
            stale_intent,
            good_target,
            run_authority=authority,
            provider_context=context,
            now=_NOW,
        )

    receipt = gate.authorize_action(
        frame,
        preflight,
        good_decision,
        good_intent,
        good_target,
        run_authority=authority,
        provider_context=context,
        now=_NOW,
    )
    assert receipt.intent_source_observation_sha256 == frame.source_observation_sha256
    with pytest.raises(SCORMGrantContextError, match="source observation"):
        gate.verify_and_consume_action(
            receipt,
            frame,
            preflight,
            stale_intent,
            good_target,
            run_authority=authority,
            provider_context=context,
            now=_NOW,
        )
    assert gate.next_action_sequence(authority) == 1


def test_intent_source_is_authenticated_in_target_grant_decision_and_receipt(
    tmp_path: Path,
) -> None:
    authority, _attestation_value, context, frame = _bundle()
    intent = _intent(frame)
    target = _target(
        context,
        frame,
        intent,
        semantic=ASSESSMENT_CONTROL,
        credential_effect=PREVIEW_ONLY,
    )
    grant = _grant(authority, context, frame, intent, target)
    ledger = SCORMActionReplayLedger(tmp_path / "replay", marker_secret=_SECRET)
    gate = _gate(ledger=ledger)
    preflight = _preflight(gate, authority, context, frame)
    decision = gate.classify_action(
        frame,
        preflight,
        intent,
        target,
        run_authority=authority,
        provider_context=context,
        grant=grant,
        now=_NOW,
    )
    receipt = gate.authorize_action(
        frame,
        preflight,
        decision,
        intent,
        target,
        run_authority=authority,
        provider_context=context,
        grant=grant,
        now=_NOW,
    )
    expected = frame.source_observation_sha256
    assert target.intent_source_observation_sha256 == expected
    assert grant.intent_source_observation_sha256 == expected
    assert decision.intent_source_observation_sha256 == expected
    assert receipt.intent_source_observation_sha256 == expected

    with pytest.raises(SCORMGrantSignatureError):
        gate.classify_action(
            frame,
            preflight,
            intent,
            replace(target, intent_source_observation_sha256=_h("e")),
            run_authority=authority,
            provider_context=context,
            grant=grant,
            now=_NOW,
        )
    drifted_grant = replace(grant, intent_source_observation_sha256=_h("e"))
    invalid = gate.classify_action(
        frame,
        preflight,
        intent,
        target,
        run_authority=authority,
        provider_context=context,
        grant=drifted_grant,
        now=_NOW,
    )
    assert invalid.reason == "per_action_benchmark_grant_invalid"
    with pytest.raises(SCORMCoherenceError, match="decision digest"):
        replace(decision, intent_source_observation_sha256=_h("e"))
    with pytest.raises(SCORMCoherenceError, match="receipt digest"):
        replace(receipt, intent_source_observation_sha256=_h("e"))


def test_preflight_or_action_target_tamper_is_self_or_signature_rejected() -> None:
    authority, _attestation_value, context, frame = _bundle()
    intent = _intent(frame)
    target = _target(context, frame, intent)
    with _gate() as gate:
        preflight = _preflight(gate, authority, context, frame)
        with pytest.raises(SCORMCoherenceError, match="preflight digest"):
            replace(preflight, reason="tampered")
        forged_target = replace(target, hmac_sha256="0" * 64)
        with pytest.raises(SCORMGrantSignatureError):
            gate.classify_action(
                frame,
                preflight,
                intent,
                forged_target,
                run_authority=authority,
                provider_context=context,
                now=_NOW,
            )


def test_real_identity_target_is_only_owner_attestation_path() -> None:
    authority, _attestation_value, context, frame = _bundle()
    intent = _intent(frame)
    target = _target(
        context,
        frame,
        intent,
        semantic=CREDENTIAL_COMMIT_CONTROL,
        credential_effect=REAL_IDENTITY_BOUND,
    )
    with _gate() as gate:
        preflight = _preflight(gate, authority, context, frame)
        decision = gate.classify_action(
            frame,
            preflight,
            intent,
            target,
            run_authority=authority,
            provider_context=context,
            now=_NOW,
        )
    assert target.interaction_kind == CREDENTIAL_MUTATION
    assert decision.kind == OWNER_ATTESTATION_REQUIRED
    assert decision.reason == "real_identity_bound_credential_mutation"


def test_wait_action_requires_bound_window_target() -> None:
    authority, _attestation_value, context, frame = _bundle()
    intent = _intent(frame, name="wait")
    target = _target(
        context,
        frame,
        intent,
        semantic=NAVIGATION_CONTROL,
        credential_effect=NO_CREDENTIAL_EFFECT,
    )
    assert target.target_surface == FRAME_WAIT
    assert target.target_bounds is None
    with _gate() as gate:
        preflight = _preflight(gate, authority, context, frame)
        decision = gate.classify_action(
            frame,
            preflight,
            intent,
            target,
            run_authority=authority,
            provider_context=context,
            now=_NOW,
        )
    assert decision.kind == CONTINUE


def test_authorize_verify_consume_and_durable_restart(tmp_path: Path) -> None:
    directory = tmp_path / "replay"
    ledger = SCORMActionReplayLedger(directory, marker_secret=_SECRET)
    authority, _attestation_value, context, frame = _bundle()
    intent = _intent(frame)
    target = _target(context, frame, intent)
    gate = _gate(ledger=ledger)
    preflight = _preflight(gate, authority, context, frame)
    decision = gate.classify_action(
        frame,
        preflight,
        intent,
        target,
        run_authority=authority,
        provider_context=context,
        now=_NOW,
    )
    receipt = gate.authorize_action(
        frame,
        preflight,
        decision,
        intent,
        target,
        run_authority=authority,
        provider_context=context,
        now=_NOW,
    )
    gate.verify_and_consume_action(
        receipt,
        frame,
        preflight,
        intent,
        target,
        run_authority=authority,
        provider_context=context,
        now=_NOW,
    )
    assert ledger.verify_consumed(receipt) is True
    assert gate.next_action_sequence(authority) == 2
    gate.close()
    restarted_ledger = SCORMActionReplayLedger(directory, marker_secret=_SECRET)
    restarted = _gate(ledger=restarted_ledger)
    assert restarted_ledger.verify_consumed(receipt) is True
    assert restarted.next_action_sequence(authority) == 2
    with pytest.raises(SCORMReplayError):
        restarted_ledger.consume(receipt, now=_NOW)


def test_replay_verify_consumed_fails_closed_for_receipt_or_marker_tamper(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "replay"
    ledger = SCORMActionReplayLedger(directory, marker_secret=_SECRET)
    authority, _attestation_value, context, frame = _bundle()
    intent = _intent(frame)
    target = _target(context, frame, intent)
    gate = _gate(ledger=ledger)
    preflight = _preflight(gate, authority, context, frame)
    decision = gate.classify_action(
        frame,
        preflight,
        intent,
        target,
        run_authority=authority,
        provider_context=context,
        now=_NOW,
    )
    receipt = gate.authorize_action(
        frame,
        preflight,
        decision,
        intent,
        target,
        run_authority=authority,
        provider_context=context,
        now=_NOW,
    )
    gate.verify_and_consume_action(
        receipt,
        frame,
        preflight,
        intent,
        target,
        run_authority=authority,
        provider_context=context,
        now=_NOW,
    )
    marker = next(directory.glob("*.json"))
    original = marker.read_bytes()

    assert ledger.verify_consumed(replace(receipt, hmac_sha256="0" * 64)) is False
    marker.unlink()
    assert ledger.verify_consumed(receipt) is False
    marker.write_bytes(original)
    decoded = json.loads(original)
    decoded["receipt_sha256"] = "0" * 64
    marker.write_text(
        json.dumps(
            decoded,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
        newline="",
    )
    assert ledger.verify_consumed(receipt) is False


def test_replay_verify_consumed_rejects_valid_but_unconsumed_receipt(
    tmp_path: Path,
) -> None:
    ledger = SCORMActionReplayLedger(tmp_path / "replay", marker_secret=_SECRET)
    authority, _attestation_value, context, frame = _bundle()
    intent = _intent(frame)
    target = _target(context, frame, intent)
    gate = _gate(ledger=ledger)
    preflight = _preflight(gate, authority, context, frame)
    decision = gate.classify_action(
        frame,
        preflight,
        intent,
        target,
        run_authority=authority,
        provider_context=context,
        now=_NOW,
    )
    receipt = gate.authorize_action(
        frame,
        preflight,
        decision,
        intent,
        target,
        run_authority=authority,
        provider_context=context,
        now=_NOW,
    )

    assert ledger.verify_consumed(receipt) is False


def test_direct_unsigned_receipt_consume_is_rejected(tmp_path: Path) -> None:
    ledger = SCORMActionReplayLedger(tmp_path / "replay", marker_secret=_SECRET)
    authority, _attestation_value, context, frame = _bundle()
    intent = _intent(frame)
    target = _target(context, frame, intent)
    gate = _gate(ledger=ledger)
    preflight = _preflight(gate, authority, context, frame)
    decision = gate.classify_action(
        frame,
        preflight,
        intent,
        target,
        run_authority=authority,
        provider_context=context,
        now=_NOW,
    )
    receipt = gate.authorize_action(
        frame,
        preflight,
        decision,
        intent,
        target,
        run_authority=authority,
        provider_context=context,
        now=_NOW,
    )
    unsigned = replace(receipt, hmac_sha256="0" * 64)
    with pytest.raises(SCORMGrantSignatureError):
        ledger.consume(unsigned, now=_NOW)


def test_well_formed_but_unsigned_durable_marker_is_rejected(tmp_path: Path) -> None:
    directory = tmp_path / "replay"
    directory.mkdir()
    run_hash = _h("a")
    marker = {
        "schema_version": "aureon-hnc-scorm-action-replay-marker-v2",
        "run_authority_sha256": run_hash,
        "action_sequence": 1,
        "receipt_sha256": _h("b"),
        "replay_nonce_sha256": _h("c"),
        "marker_hmac_sha256": "0" * 64,
    }
    encoded = (
        json.dumps(
            marker,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )
    (directory / f"{run_hash}-0000001.json").write_bytes(encoded)
    with pytest.raises(SCORMReplayError, match="signature"):
        SCORMActionReplayLedger(directory, marker_secret=_SECRET)


def test_visible_evidence_digest_preserves_exact_order_geometry_and_vision() -> None:
    tokens = (
        OCRToken("Alpha", 10, 20, 30, 12, 0.91),
        OCRToken("β", 45, 20, 9, 12, None),
    )
    observation = SimpleNamespace(ocr_tokens=tokens, vision_text='{"candidate":"next"}')
    digest = canonical_visible_evidence_sha256(observation)
    assert digest != canonical_visible_evidence_sha256(
        SimpleNamespace(ocr_tokens=tuple(reversed(tokens)), vision_text=observation.vision_text)
    )
    assert digest != canonical_visible_evidence_sha256(
        SimpleNamespace(ocr_tokens=(replace(tokens[0], x=11), tokens[1]), vision_text=observation.vision_text)
    )


def test_no_course_answers_or_answer_tables() -> None:
    source = Path("aureon/operator/hnc_scorm_coherence.py").read_text(encoding="utf-8").casefold()
    assert "correct_answer" not in source
    assert "answer_key" not in source
    assert "course_code" not in source
