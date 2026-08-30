from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from aureon.autonomous.aureon_governed_desktop_gateway import WindowInfo
from aureon.operator.governed_window_session import (
    SessionWindowBinding,
    window_sha256,
)
from aureon.operator.hnc_scorm_coherence import (
    ASSESSMENT_CONTROL,
    BOUND_WINDOW_SURFACE,
    COORDINATE_CONTROL,
    FOCUSED_CONTROL,
    FRAME_WAIT,
    NATIVE_ACCESSIBILITY_CONTROL,
    NATIVE_FOCUSED_CONTROL,
    NAVIGATION_CONTROL,
    OWNER_BENCHMARK_ASSERTED,
    PREVIEW_ONLY,
    SIGNED_OWNER_BENCHMARK_LAUNCH_RECEIPT,
    SYNTHETIC_BENCHMARK,
    SCORMActionIntent,
    SCORMFrameEvidence,
    SCORMRunAuthority,
)
from aureon.operator.local_gui_observer import OCRToken, ScreenObservation, WindowRect
from aureon.operator.scorm_cloud_evidence import (
    NativeAddressBarRead,
    NativeControlRead,
    SCORMEvidenceAuthorityError,
    SCORMOwnerBenchmarkEvidenceAuthorizer,
    Win32EdgeNativeTargetProbe,
    Win32EdgeNativeURLProbe,
    owner_benchmark_run_manifest_sha256,
)
from aureon.operator.scorm_cloud_session import (
    ActiveSCORMCloudSession,
    EdgeProfileSpec,
    LaunchedEdgeProcess,
    SCORMEvidenceLedger,
    SCORMPublicPreviewControlGrant,
    build_scorm_cloud_edge_plan,
)

SCORM_URL = "https://cloud.scorm.com/launch/course?token=signed-value-123"
NOW = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)
SESSION_SECRET = b"session-signing-secret-is-distinct-and-long"
HNC_SECRET = b"hnc-signing-secret-is-distinct-and-long-enough"
OWNER_SECRET = b"owner-benchmark-secret-is-distinct-and-long"


def exact_binding() -> SessionWindowBinding:
    window = WindowInfo(
        handle=444,
        title="Course - SCORM Cloud - Microsoft Edge",
        process_id=555,
        left=10,
        top=20,
        width=1200,
        height=800,
    )
    return SessionWindowBinding(
        session_id="scorm-native-url-test",
        binding_id="binding-native-url-test",
        policy_sha256="a" * 64,
        generation=3,
        handoff_count=2,
        bound_at=NOW,
        origin_label="scorm-cloud-launch-context-v1",
        window=window,
        window_sha256=window_sha256(window),
    )


def address_read(**changes: object) -> NativeAddressBarRead:
    values: dict[str, object] = {
        "exact_url": SCORM_URL,
        "window_handle": 444,
        "process_id": 555,
        "automation_id": "view_1001",
        "control_name": "Address and search bar",
    }
    values.update(changes)
    return NativeAddressBarRead(**values)  # type: ignore[arg-type]


def test_native_url_probe_binds_exact_address_bar_to_window_generation() -> None:
    calls: list[tuple[int, int, int]] = []

    def reader(handle: int, process_id: int, maximum: int) -> NativeAddressBarRead:
        calls.append((handle, process_id, maximum))
        return address_read()

    probe = Win32EdgeNativeURLProbe(reader=reader, utc_now=lambda: NOW, max_elements=37)
    binding = exact_binding()
    evidence = probe.capture(binding)

    assert calls == [(444, 555, 37)]
    assert evidence.exact_url == SCORM_URL
    assert evidence.live_origin == "https://cloud.scorm.com"
    assert evidence.window_binding_id == binding.binding_id
    assert evidence.window_generation == binding.generation
    assert evidence.window_identity_sha256 == binding.window_sha256
    assert len(evidence.evidence_sha256) == 64
    encoded_audit = json.dumps(evidence.audit_dict(), sort_keys=True)
    assert SCORM_URL not in encoded_audit
    assert "signed-value-123" not in encoded_audit


def test_native_url_probe_accepts_current_chrome_address_bar_identity() -> None:
    probe = Win32EdgeNativeURLProbe(
        reader=lambda _handle, _process_id, _maximum: address_read(
            automation_id="view_1012",
        ),
        utc_now=lambda: NOW,
    )

    evidence = probe.capture(exact_binding())

    assert evidence.automation_id_sha256 == hashlib.sha256(b"view_1012").hexdigest()


def test_native_url_probe_canonicalizes_chrome_scheme_omitted_display() -> None:
    displayed_url = SCORM_URL.removeprefix("https://")
    probe = Win32EdgeNativeURLProbe(
        reader=lambda _handle, _process_id, _maximum: address_read(
            automation_id="view_1012",
            exact_url=displayed_url,
        ),
        utc_now=lambda: NOW,
    )

    evidence = probe.capture(exact_binding())

    assert evidence.exact_url == SCORM_URL
    assert evidence.live_url_sha256 == hashlib.sha256(SCORM_URL.encode()).hexdigest()
    assert evidence.live_origin == "https://cloud.scorm.com"


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"window_handle": 445}, "window_mismatch"),
        ({"process_id": 556}, "window_mismatch"),
        ({"automation_id": "page-input"}, "identity_invalid"),
        ({"control_name": "Course address field"}, "name_invalid"),
        ({"exact_url": "https://evil.example/launch"}, "origin_not_allowed"),
        ({"exact_url": "https://CLOUD.SCORM.COM/launch"}, "origin_not_allowed"),
        ({"exact_url": "https://cloud.scorm.com:443/launch"}, "origin_not_allowed"),
        ({"exact_url": "cloud.scorm.com.evil.example/launch"}, "origin_not_allowed"),
        ({"exact_url": "cloud.scorm.com@evil.example/launch"}, "origin_not_allowed"),
        ({"exact_url": "cloud.scorm.com:443/launch"}, "origin_not_allowed"),
        ({"exact_url": "CLOUD.SCORM.COM/launch"}, "origin_not_allowed"),
        ({"exact_url": "evil.example/cloud.scorm.com/launch"}, "origin_not_allowed"),
    ],
)
def test_native_url_probe_fails_closed_on_non_exact_ui_evidence(
    changes: dict[str, object],
    reason: str,
) -> None:
    probe = Win32EdgeNativeURLProbe(
        reader=lambda _handle, _pid, _maximum: address_read(**changes),
        utc_now=lambda: NOW,
    )

    with pytest.raises(SCORMEvidenceAuthorityError, match=reason):
        probe.capture(exact_binding())


def test_native_url_evidence_detects_hash_or_binding_tamper() -> None:
    probe = Win32EdgeNativeURLProbe(
        reader=lambda _handle, _pid, _maximum: address_read(),
        utc_now=lambda: NOW,
    )
    evidence = probe.capture(exact_binding())

    with pytest.raises(SCORMEvidenceAuthorityError, match="digest_invalid"):
        replace(evidence, window_generation=evidence.window_generation + 1)
    with pytest.raises(SCORMEvidenceAuthorityError, match="hash_mismatch"):
        replace(evidence, exact_url="https://cloud.scorm.com/other")


def test_native_url_probe_wraps_reader_failure_without_leaking_detail() -> None:
    def broken_reader(_handle: int, _pid: int, _maximum: int) -> NativeAddressBarRead:
        raise RuntimeError(f"secret={SCORM_URL}")

    probe = Win32EdgeNativeURLProbe(reader=broken_reader, utc_now=lambda: NOW)

    with pytest.raises(
        SCORMEvidenceAuthorityError,
        match="^native_address_bar_read_failed$",
    ) as captured:
        probe.capture(exact_binding())
    assert SCORM_URL not in str(captured.value)


def test_native_url_probe_limits_accessibility_inventory() -> None:
    with pytest.raises(ValueError, match="within"):
        Win32EdgeNativeURLProbe(
            reader=lambda _handle, _pid, _maximum: address_read(),
            max_elements=513,
        )


class FakeProcessInspector:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed
        self.calls: list[tuple[int, int]] = []

    def is_same_process_or_descendant(
        self,
        process_id: int,
        *,
        ancestor_process_id: int,
    ) -> bool:
        self.calls.append((process_id, ancestor_process_id))
        return self.allowed


class FakeTargetReader:
    def __init__(self, raw: NativeControlRead) -> None:
        self.raw = raw
        self.at_calls: list[tuple[int, int, int, int, int]] = []
        self.focus_calls: list[tuple[int, int, int]] = []

    def read_at(
        self,
        window_handle: int,
        root_process_id: int,
        x: int,
        y: int,
        max_ancestors: int,
    ) -> NativeControlRead:
        self.at_calls.append(
            (window_handle, root_process_id, x, y, max_ancestors)
        )
        return self.raw

    def read_focused(
        self,
        window_handle: int,
        root_process_id: int,
        max_ancestors: int,
    ) -> NativeControlRead:
        self.focus_calls.append((window_handle, root_process_id, max_ancestors))
        return self.raw


def target_read(**changes: object) -> NativeControlRead:
    values: dict[str, object] = {
        "window_handle": 444,
        "root_process_id": 555,
        "element_process_id": 556,
        "x": 100,
        "y": 120,
        "width": 220,
        "height": 40,
        "role": "RadioButton",
        "name": "B. Safe answer",
        "automation_id": "answer-b",
        "ancestor_depth": 7,
        "focused": False,
    }
    values.update(changes)
    return NativeControlRead(**values)  # type: ignore[arg-type]


def action_intent(name: str, params: dict[str, object]) -> SCORMActionIntent:
    return SCORMActionIntent.from_action(
        name,
        params,
        action_sequence=1,
        source_observation_sha256="b" * 64,
    )


def test_native_target_probe_binds_coordinate_and_accessibility_identity() -> None:
    reader = FakeTargetReader(target_read())
    inspector = FakeProcessInspector()
    probe = Win32EdgeNativeTargetProbe(
        reader=reader,
        process_inspector=inspector,
        max_ancestors=12,
    )
    intent = action_intent("left_click", {"x": 150, "y": 140})

    target = probe.capture(exact_binding(), intent)

    assert reader.at_calls == [(444, 555, 150, 140, 12)]
    assert reader.focus_calls == []
    assert inspector.calls == [(556, 555)]
    assert target.target_surface == COORDINATE_CONTROL
    assert target.target_evidence_kind == NATIVE_ACCESSIBILITY_CONTROL
    assert target.target_bounds is not None
    assert target.target_bounds.contains(intent.coordinates)  # type: ignore[arg-type]
    assert target.accessibility_role_sha256 is not None
    assert target.accessibility_name_sha256 is not None
    assert "Safe answer" not in json.dumps(target.audit_dict())


def test_native_target_probe_requires_exact_focused_control_for_keyboard() -> None:
    reader = FakeTargetReader(
        target_read(role="Edit", name="Response", focused=True)
    )
    probe = Win32EdgeNativeTargetProbe(
        reader=reader,
        process_inspector=FakeProcessInspector(),
    )
    intent = action_intent(
        "type_text",
        {"text": "redacted locally", "text_class": "assessment_answer"},
    )

    target = probe.capture(exact_binding(), intent)

    assert reader.at_calls == []
    assert reader.focus_calls == [(444, 555, 128)]
    assert target.target_surface == FOCUSED_CONTROL
    assert target.target_evidence_kind == NATIVE_FOCUSED_CONTROL

    reader.raw = replace(reader.raw, focused=False)
    with pytest.raises(SCORMEvidenceAuthorityError, match="not_focused"):
        probe.capture(exact_binding(), intent)


def test_native_target_probe_wait_binds_window_without_accessibility_read() -> None:
    reader = FakeTargetReader(target_read())
    probe = Win32EdgeNativeTargetProbe(
        reader=reader,
        process_inspector=FakeProcessInspector(),
    )

    target = probe.capture(exact_binding(), action_intent("wait", {"seconds": 1.0}))

    assert target.target_surface == FRAME_WAIT
    assert target.target_evidence_kind == BOUND_WINDOW_SURFACE
    assert target.target_bounds is None
    assert reader.at_calls == []
    assert reader.focus_calls == []


@pytest.mark.parametrize(
    ("raw", "allowed", "reason"),
    [
        (target_read(window_handle=999), True, "window_mismatch"),
        (target_read(x=50, width=20), True, "outside_target"),
        (target_read(element_process_id=999), False, "process_mismatch"),
        (target_read(x=5), True, "bounds_invalid"),
    ],
)
def test_native_target_probe_rejects_wrong_window_bounds_or_lineage(
    raw: NativeControlRead,
    allowed: bool,
    reason: str,
) -> None:
    probe = Win32EdgeNativeTargetProbe(
        reader=FakeTargetReader(raw),
        process_inspector=FakeProcessInspector(allowed),
    )

    with pytest.raises(SCORMEvidenceAuthorityError, match=reason):
        probe.capture(
            exact_binding(),
            action_intent("left_click", {"x": 150, "y": 140}),
        )


class FakeActiveWindowSession:
    def __init__(self, binding: SessionWindowBinding) -> None:
        self.binding = binding

    def authorize_active_binding(self) -> SessionWindowBinding:
        return self.binding

    def close(self) -> None:
        return None


def active_session(
    tmp_path: Path,
) -> tuple[ActiveSCORMCloudSession, SessionWindowBinding, SCORMEvidenceLedger]:
    executable = tmp_path / "msedge.exe"
    executable.write_bytes(b"hermetic-edge-fixture")
    profile = EdgeProfileSpec.isolated(tmp_path / "fresh-profile")
    plan = build_scorm_cloud_edge_plan(
        exact_url=SCORM_URL,
        edge_executable=executable,
        profile=profile,
        local_model="qwen3:8b",
        local_model_endpoint="http://127.0.0.1:11434",
        expected_initial_title_regex=r"^.+ - SCORM Cloud - Microsoft Edge$",
        allowed_title_regex=r"^.+ - SCORM Cloud - Microsoft Edge$",
        session_id="scorm-public-preview-authority-test",
    )
    window = WindowInfo(
        handle=444,
        title="Course - SCORM Cloud - Microsoft Edge",
        process_id=555,
        left=10,
        top=20,
        width=1200,
        height=800,
    )
    binding = SessionWindowBinding(
        session_id=plan.session_id,
        binding_id="binding-public-preview-authority-test",
        policy_sha256="a" * 64,
        generation=3,
        handoff_count=2,
        bound_at=NOW,
        origin_label="scorm-cloud-launch-context-v1",
        window=window,
        window_sha256=window_sha256(window),
    )
    control = SCORMPublicPreviewControlGrant.issue(
        signing_secret=SESSION_SECRET,
        plan=plan,
        policy_sha256=binding.policy_sha256,
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=10),
    )
    ledger = SCORMEvidenceLedger(
        tmp_path / "authority-evidence.jsonl",
        run_id=plan.session_id,
        utc_now=lambda: NOW,
    )
    active = ActiveSCORMCloudSession(
        plan=plan,
        launched_process=LaunchedEdgeProcess(
            process_id=555,
            launched_at_utc="2026-08-16T12:00:00Z",
        ),
        window_session=FakeActiveWindowSession(binding),  # type: ignore[arg-type]
        initial_binding=binding,
        control_manifest=control,
        control_grant_sha256=control.control_grant_sha256,
        _controller=object(),  # type: ignore[arg-type]
        _process_inspector=FakeProcessInspector({555: None}),
        _enumerator=object(),  # type: ignore[arg-type]
        _ledger=ledger,
        _launch_baseline_handles=frozenset(),
    )
    return active, binding, ledger


def assessment_observation(binding: SessionWindowBinding) -> ScreenObservation:
    words = (
        "SCORM",
        "Cloud",
        "Preview",
        "Assessment",
        "No",
        "answer",
        "submitted",
        "B.",
        "Safe",
        "answer",
    )
    tokens = tuple(
        OCRToken(
            text=word,
            x=40 + index * 70,
            y=100 if index < 3 else 140,
            width=60,
            height=20,
            confidence=0.99,
        )
        for index, word in enumerate(words)
    )
    return ScreenObservation(
        observation_id="b" * 64,
        sequence=9,
        captured_at_unix=NOW.timestamp(),
        screenshot_sha256="c" * 64,
        width=1600,
        height=1000,
        ocr_tokens=tokens,
        vision_text="Assessment question with three radio options.",
        window_handle=binding.window.handle,
        window_process_id=binding.window.process_id,
        window_title_sha256=hashlib.sha256(
            binding.window.title.encode("utf-8")
        ).hexdigest(),
        window_rect=WindowRect(
            left=binding.window.left,
            top=binding.window.top,
            width=binding.window.width,
            height=binding.window.height,
        ),
        dpi_x=96.0,
        dpi_y=96.0,
    )


def test_public_preview_authorizer_binds_frame_target_and_per_action_grant(
    tmp_path: Path,
) -> None:
    active, binding, ledger = active_session(tmp_path)
    run_authority = SCORMRunAuthority.issue(
        secret=HNC_SECRET,
        run_id=active.plan.session_id,
        run_manifest_sha256=owner_benchmark_run_manifest_sha256(active),
        replay_nonce="hermetic-replay-nonce-0001",
        allowed_origin="https://cloud.scorm.com",
        launch_url_sha256=active.plan.url_sha256,
        launch_plan_sha256=active.plan.plan_sha256,
        control_grant_sha256=active.control_grant_sha256,
        allowed_actions=active.plan.allowed_gui_actions,
        max_actions=100,
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=10),
    )
    authorizer = SCORMOwnerBenchmarkEvidenceAuthorizer(
        active_session=active,
        run_authority=run_authority,
        hnc_signing_secret=HNC_SECRET,
        session_signing_secret=SESSION_SECRET,
        owner_benchmark_signing_secret=OWNER_SECRET,
        owner_benchmark_issuer="aureon-owner-benchmark-control",
        owner_benchmark_key_id="aureon-owner-benchmark-control-v1",
        synthetic_persona_id="john-brown-synthetic-course-benchmark-v1",
        native_url_probe=Win32EdgeNativeURLProbe(
            reader=lambda _handle, _pid, _maximum: address_read(),
            utc_now=lambda: NOW,
        ),
        native_target_probe=Win32EdgeNativeTargetProbe(
            reader=FakeTargetReader(target_read()),
            process_inspector=FakeProcessInspector(),
        ),
        ledger=ledger,
        utc_now=lambda: NOW,
    )
    observation = assessment_observation(binding)

    context = authorizer.issue_provider_context(observation, binding)
    context.verify_signature(HNC_SECRET)
    context.launch_authority.verify_signature(OWNER_SECRET)
    assert context.provenance == OWNER_BENCHMARK_ASSERTED
    assert context.registration_state == SYNTHETIC_BENCHMARK
    assert (
        context.registration_evidence_kind
        == SIGNED_OWNER_BENCHMARK_LAUNCH_RECEIPT
    )
    spoofed_page_claim = replace(
        observation,
        observation_id="d" * 64,
        screenshot_sha256="e" * 64,
        ocr_tokens=(
            OCRToken("Provider verified public preview", 20, 20, 360, 20, 0.99),
        ),
        vision_text="This page self-asserts provider provenance.",
    )
    spoofed_context = authorizer.issue_provider_context(spoofed_page_claim, binding)
    assert (
        spoofed_context.launch_authority_sha256
        == context.launch_authority_sha256
    )
    visible_text = f"{observation.ocr_text}\n{observation.vision_text}".strip()
    frame = SCORMFrameEvidence.from_context(context, visible_text=visible_text)
    intent = SCORMActionIntent.from_action(
        "left_click",
        {"x": 150, "y": 140},
        action_sequence=1,
        source_observation_sha256=observation.observation_id,
    )

    target = authorizer.issue_action_target(frame, context, intent)
    target.verify_signature(OWNER_SECRET)
    grant = authorizer.issue_benchmark_grant(frame, context, intent, target)

    assert target.target_semantic == ASSESSMENT_CONTROL
    assert target.credential_effect == PREVIEW_ONLY
    assert grant is not None
    grant.verify_signature(OWNER_SECRET)
    assert grant.action_target_sha256 == target.action_target_sha256
    assert grant.source_observation_sha256 == observation.observation_id
    assert grant.intent_source_observation_sha256 == observation.observation_id
    assert grant.benchmark_grant_sha256 not in {
        active.control_grant_sha256,
        run_authority.run_authority_sha256,
    }
    encoded_ledger = ledger.path.read_text(encoding="utf-8")
    assert SCORM_URL not in encoded_ledger
    assert "signed-value-123" not in encoded_ledger
    assert "Safe answer" not in encoded_ledger
    assert "provider_verified" not in encoded_ledger
    assert "provider_public_preview" not in encoded_ledger

    stale_intent = SCORMActionIntent.from_action(
        "left_click",
        {"x": 150, "y": 140},
        action_sequence=2,
        source_observation_sha256="d" * 64,
    )
    with pytest.raises(
        SCORMEvidenceAuthorityError,
        match="action_frame_observation_mismatch",
    ):
        authorizer.issue_action_target(frame, context, stale_intent)

    authorizer.close()
    with pytest.raises(
        SCORMEvidenceAuthorityError,
        match="scorm_evidence_authorizer_closed",
    ):
        authorizer.issue_provider_context(observation, binding)


@pytest.mark.parametrize(
    (
        "role",
        "name",
        "automation_id",
        "assessment_frame",
        "action_name",
        "action_params",
        "focused",
        "expected_semantic",
    ),
    [
        (
            "Hyperlink",
            "B. Safe answer",
            "answer-b",
            True,
            "left_click",
            {"x": 150, "y": 140},
            False,
            ASSESSMENT_CONTROL,
        ),
        (
            "Button",
            "Continue",
            "assessment-continue",
            True,
            "left_click",
            {"x": 150, "y": 140},
            False,
            ASSESSMENT_CONTROL,
        ),
        (
            "Button",
            "Finish",
            "assessment-finish",
            True,
            "left_click",
            {"x": 150, "y": 140},
            False,
            ASSESSMENT_CONTROL,
        ),
        (
            "Button",
            "Continue",
            "lesson-continue",
            False,
            "left_click",
            {"x": 150, "y": 140},
            False,
            NAVIGATION_CONTROL,
        ),
        (
            "Thumb",
            "",
            "nextBtn",
            False,
            "move_mouse",
            {"x": 150, "y": 140, "duration": 0.15},
            False,
            NAVIGATION_CONTROL,
        ),
        (
            "Thumb",
            "",
            "nextBtn",
            True,
            "left_click",
            {"x": 150, "y": 140},
            False,
            ASSESSMENT_CONTROL,
        ),
        (
            "Text",
            "Energy Isolating Device",
            "definition-tab",
            False,
            "left_click",
            {"x": 150, "y": 140},
            False,
            NAVIGATION_CONTROL,
        ),
        (
            "Edit",
            "Answer response",
            "assessment-response",
            True,
            "type_text",
            {"text": "redacted answer", "text_class": "assessment_answer"},
            True,
            ASSESSMENT_CONTROL,
        ),
        (
            "Edit",
            "Address and search bar",
            "addressEditBox",
            True,
            "type_text",
            {"text": "redacted answer", "text_class": "assessment_answer"},
            True,
            None,
        ),
        (
            "Edit",
            "Answer response",
            "assessment-response",
            False,
            "type_text",
            {"text": "redacted answer", "text_class": "assessment_answer"},
            True,
            None,
        ),
    ],
)
def test_production_target_classifier_binds_assessment_frame_and_exact_control(
    tmp_path: Path,
    role: str,
    name: str,
    automation_id: str,
    assessment_frame: bool,
    action_name: str,
    action_params: dict[str, object],
    focused: bool,
    expected_semantic: str | None,
) -> None:
    active, binding, ledger = active_session(tmp_path)
    run_authority = SCORMRunAuthority.issue(
        secret=HNC_SECRET,
        run_id=active.plan.session_id,
        run_manifest_sha256=owner_benchmark_run_manifest_sha256(active),
        replay_nonce="production-target-replay-nonce-0001",
        allowed_origin="https://cloud.scorm.com",
        launch_url_sha256=active.plan.url_sha256,
        launch_plan_sha256=active.plan.plan_sha256,
        control_grant_sha256=active.control_grant_sha256,
        allowed_actions=active.plan.allowed_gui_actions,
        max_actions=100,
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=10),
    )
    authorizer = SCORMOwnerBenchmarkEvidenceAuthorizer(
        active_session=active,
        run_authority=run_authority,
        hnc_signing_secret=HNC_SECRET,
        session_signing_secret=SESSION_SECRET,
        owner_benchmark_signing_secret=OWNER_SECRET,
        owner_benchmark_issuer="aureon-owner-benchmark-control",
        owner_benchmark_key_id="aureon-owner-benchmark-control-v1",
        synthetic_persona_id="john-brown-synthetic-course-benchmark-v1",
        native_url_probe=Win32EdgeNativeURLProbe(
            reader=lambda _handle, _pid, _maximum: address_read(),
            utc_now=lambda: NOW,
        ),
        native_target_probe=Win32EdgeNativeTargetProbe(
            reader=FakeTargetReader(
                target_read(
                    role=role,
                    name=name,
                    automation_id=automation_id,
                    focused=focused,
                )
            ),
            process_inspector=FakeProcessInspector(),
        ),
        ledger=ledger,
        utc_now=lambda: NOW,
    )
    observation = assessment_observation(binding)
    if not assessment_frame:
        observation = replace(
            observation,
            ocr_tokens=(
                OCRToken(
                    "SCORM Cloud Preview Workplace safety lesson",
                    40,
                    100,
                    440,
                    20,
                    0.99,
                ),
            ),
            vision_text="Ordinary lesson content.",
        )
    if automation_id == "definition-tab":
        observation = replace(
            observation,
            ocr_tokens=(
                OCRToken(
                    "Click on each of the tabs Energy Isolating Device",
                    40,
                    100,
                    440,
                    20,
                    0.99,
                ),
            ),
        )
    context = authorizer.issue_provider_context(observation, binding)
    frame = SCORMFrameEvidence.from_context(
        context,
        visible_text=f"{observation.ocr_text}\n{observation.vision_text}".strip(),
    )
    intent = SCORMActionIntent.from_action(
        action_name,
        action_params,
        action_sequence=1,
        source_observation_sha256=observation.observation_id,
    )

    if expected_semantic is None:
        with pytest.raises(
            SCORMEvidenceAuthorityError,
            match="^native_action_target_semantic_unresolved$",
        ):
            authorizer.issue_action_target(frame, context, intent)
        assert "action_target_issued" not in ledger.path.read_text(
            encoding="utf-8"
        )
        authorizer.close()
        return

    target = authorizer.issue_action_target(frame, context, intent)
    grant = authorizer.issue_benchmark_grant(frame, context, intent, target)

    assert target.target_semantic == expected_semantic
    assert (grant is not None) is (expected_semantic == ASSESSMENT_CONTROL)
    if grant is not None:
        assert grant.action_target_sha256 == target.action_target_sha256
    authorizer.close()
