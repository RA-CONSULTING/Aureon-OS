from __future__ import annotations

import base64
import hashlib
import io
import json
import unicodedata
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from aureon.autonomous.aureon_governed_desktop_gateway import (
    DesktopActionResult,
    WindowInfo,
)
from aureon.operator.course_benchmark_ledger import CourseBenchmarkLedger
from aureon.operator.governed_gui_adapter import (
    GatewayScreenshotBackend,
    GovernedGatewayExecutor,
)
from aureon.operator.governed_window_session import SessionWindowBinding
from aureon.operator.hnc_scorm_coherence import (
    ASSESSMENT_CONTROL,
    BOUND_WINDOW_SURFACE,
    COORDINATE_CONTROL,
    CREDENTIAL_COMMIT_CONTROL,
    FOCUSED_CONTROL,
    FRAME_WAIT,
    NATIVE_ACCESSIBILITY_CONTROL,
    NATIVE_FOCUSED_CONTROL,
    NAVIGATION_CONTROL,
    NO_CREDENTIAL_EFFECT,
    PREVIEW_ONLY,
    REAL_IDENTITY_BOUND,
    WINDOW_NAVIGATION,
    HNCScormCoherenceGate,
    SCORMActionReplayLedger,
    SCORMActionTargetEvidence,
    SCORMBenchmarkGrant,
    SCORMOwnerBenchmarkLaunchAuthority,
    SCORMProviderContextEvidence,
    SCORMRunAuthority,
    SCORMTargetBounds,
    canonical_visible_evidence_sha256,
)
from aureon.operator.local_gui_local_backends import (
    FrameArtifactPNGSource,
    LocalOllamaVisionPlanner,
    PlannerImageError,
    PlannerResponseError,
)
from aureon.operator.local_gui_observer import (
    CapturedScreen,
    FrameArtifactStore,
    GatewayObservationRejectedError,
    OCRToken,
    ScreenObservation,
    WindowRect,
)
from aureon.operator.local_gui_organism import (
    ACTOR_ID,
    LocalGUIOrganism,
    LocalGUIOrganismConfig,
    OrganismConfigurationError,
    build_local_organism,
)
from aureon.operator.local_gui_pause import (
    HashOnlyPauseCheckpointStore,
    PauseCheckpointError,
)
from aureon.operator.local_gui_runtime import (
    ActionResult,
    GuiAction,
    LocalGUIRuntime,
    ObservationPredicate,
    PlannerDecision,
    RuntimeLimits,
    RuntimeTransition,
)
from aureon.operator.local_gui_scorm_authority import SCORMVisionRuntimeAuthority
from aureon.operator.scorm_cloud_session import (
    ActiveSCORMCloudSession,
    SCORMPublicPreviewControlGrant,
)

_SCORM_SECRET = b"typed-scorm-runtime-secret-at-least-32-bytes"
_SCORM_OWNER_SECRET = b"distinct-owner-benchmark-secret-32-bytes"
_SCORM_NOW = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)


def _png_bytes(*, width: int = 64, height: int = 32, color=(20, 90, 140)) -> bytes:
    output = io.BytesIO()
    with Image.new("RGB", (width, height), color) as image:
        image.save(output, format="PNG")
    return output.getvalue()


def _observation(
    png: bytes,
    *,
    text: str = "SCORM course home",
    sequence: int = 1,
    identity: str = "observation",
    handle: int = 101,
    artifact=None,
) -> ScreenObservation:
    observation_id = hashlib.sha256(f"{identity}:{sequence}".encode()).hexdigest()
    return ScreenObservation(
        observation_id=observation_id,
        sequence=sequence,
        captured_at_unix=float(sequence),
        screenshot_sha256=hashlib.sha256(png).hexdigest(),
        width=64,
        height=32,
        ocr_tokens=(OCRToken(text, 1, 1, 60, 10, 0.99),),
        mime_type="image/png",
        cursor_x=5,
        cursor_y=5,
        window_handle=handle,
        window_process_id=202,
        window_title_sha256=hashlib.sha256(b"SCORM window").hexdigest(),
        window_rect=WindowRect(0, 0, 64, 32),
        dpi_x=96.0,
        dpi_y=96.0,
        frame_artifact=artifact,
    )


class _ImageSource:
    locality = "local"

    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.calls = 0

    def read_png(self, observation, *, max_bytes):
        self.calls += 1
        assert observation.screenshot_sha256 == hashlib.sha256(self.payload).hexdigest()
        assert max_bytes > 0
        return self.payload


class _Transport:
    def __init__(self, response) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def post_json(self, url, payload, *, timeout_seconds):
        self.calls.append(
            {"url": url, "payload": payload, "timeout_seconds": timeout_seconds}
        )
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def _response(decision: object) -> dict[str, object]:
    return {"message": {"role": "assistant", "content": json.dumps(decision)}}


def _click_response() -> dict[str, object]:
    return _response(
        {
            "kind": "action",
            "reason": "Click the visible control",
            "action": {"name": "left_click", "params": {"x": 20, "y": 20}},
            "expected": {"kind": "screen_changed", "value": ""},
        }
    )


class _WindowSession:
    def __init__(self, binding: SessionWindowBinding) -> None:
        self.binding = binding

    def authorize_active_binding(self) -> SessionWindowBinding:
        return self.binding


def _scorm_authority(
    tmp_path: Path,
    *,
    run_id: str = "scorm-test-run",
    binding_id: str = "bound-window",
    target_semantic: str = NAVIGATION_CONTROL,
    grant_enabled: bool = False,
) -> SCORMVisionRuntimeAuthority:
    exact_url = "https://cloud.scorm.com/sc/guest/launch"
    plan_sha256 = hashlib.sha256(b"launch-plan").hexdigest()
    url_sha256 = hashlib.sha256(exact_url.encode()).hexdigest()
    policy_sha256 = hashlib.sha256(b"window-policy").hexdigest()
    run_manifest_sha256 = hashlib.sha256(b"signed-run-manifest").hexdigest()
    allowed_actions = (
        "double_click",
        "hotkey",
        "left_click",
        "move_mouse",
        "press_key",
        "right_click",
        "scroll",
        "type_text",
        "wait",
    )
    control_manifest = SCORMPublicPreviewControlGrant(
        session_id=run_id,
        launch_plan_sha256=plan_sha256,
        launch_url_sha256=url_sha256,
        policy_sha256=policy_sha256,
        allowed_actions=allowed_actions,
        issued_at_unix=int((_SCORM_NOW - timedelta(minutes=5)).timestamp()),
        expires_at_unix=int((_SCORM_NOW + timedelta(hours=1)).timestamp()),
        hmac_sha256=hashlib.sha256(b"control-manifest-signature").hexdigest(),
    )
    control_sha256 = control_manifest.control_grant_sha256
    run_authority = SCORMRunAuthority.issue(
        secret=_SCORM_SECRET,
        run_id=run_id,
        run_manifest_sha256=run_manifest_sha256,
        replay_nonce="typed-runtime-replay-nonce-0001",
        allowed_origin="https://cloud.scorm.com",
        launch_plan_sha256=plan_sha256,
        launch_url_sha256=url_sha256,
        control_grant_sha256=control_sha256,
        allowed_actions=allowed_actions,
        max_actions=100,
        issued_at=_SCORM_NOW - timedelta(minutes=5),
        expires_at=_SCORM_NOW + timedelta(hours=1),
    )
    window = WindowInfo(
        handle=101,
        title="SCORM window",
        process_id=202,
        left=0,
        top=0,
        width=64,
        height=32,
    )
    binding = SessionWindowBinding(
        session_id=run_id,
        binding_id=binding_id,
        policy_sha256=policy_sha256,
        generation=0,
        handoff_count=0,
        bound_at=_SCORM_NOW - timedelta(minutes=1),
        origin_label="scorm-cloud-launch-context-v1",
        window=window,
        window_sha256=hashlib.sha256(b"window-identity").hexdigest(),
    )
    active = ActiveSCORMCloudSession(
        plan=SimpleNamespace(
            session_id=run_id,
            plan_sha256=plan_sha256,
            url_sha256=url_sha256,
            exact_url=exact_url,
            allowed_gui_actions=allowed_actions,
        ),
        launched_process=SimpleNamespace(process_id=202),
        window_session=_WindowSession(binding),  # type: ignore[arg-type]
        initial_binding=binding,
        control_manifest=control_manifest,
        control_grant_sha256=control_sha256,
        _controller=SimpleNamespace(),  # type: ignore[arg-type]
        _process_inspector=SimpleNamespace(),  # type: ignore[arg-type]
        _enumerator=SimpleNamespace(),  # type: ignore[arg-type]
        _ledger=SimpleNamespace(),  # type: ignore[arg-type]
        _launch_baseline_handles=frozenset(),
    )

    def provider_context(
        observation: ScreenObservation,
        current_binding: SessionWindowBinding,
    ) -> SCORMProviderContextEvidence:
        visible_text = unicodedata.normalize(
            "NFC",
            f"{observation.ocr_text}\n{observation.vision_text}".strip(),
        )
        launch_authority = SCORMOwnerBenchmarkLaunchAuthority.issue(
            owner_secret=_SCORM_OWNER_SECRET,
            issuer="aureon-hermetic-owner-benchmark",
            key_id="aureon-hermetic-owner-benchmark-key-v1",
            synthetic_persona_id="john-brown-synthetic-course-benchmark-v1",
            run_authority=run_authority,
            native_live_url_sha256=url_sha256,
            native_address_bar_receipt_sha256=hashlib.sha256(
                b"native-address-bar-receipt"
            ).hexdigest(),
            active_session_id=current_binding.session_id,
            window_binding_id=current_binding.binding_id,
            window_generation=current_binding.generation,
            window_identity_sha256=current_binding.window_sha256,
            issued_at=_SCORM_NOW - timedelta(minutes=2),
            expires_at=_SCORM_NOW + timedelta(minutes=30),
        )
        return SCORMProviderContextEvidence.issue(
            secret=_SCORM_SECRET,
            run_authority=run_authority,
            launch_authority=launch_authority,
            source_observation_sha256=observation.observation_id,
            source_screenshot_sha256=observation.screenshot_sha256,
            visible_evidence_sha256=canonical_visible_evidence_sha256(observation),
            visible_text=visible_text,
            active_session_id=current_binding.session_id,
            live_origin="https://cloud.scorm.com",
            window_binding_id=current_binding.binding_id,
            window_generation=current_binding.generation,
            window_identity_sha256=current_binding.window_sha256,
            issued_at=_SCORM_NOW - timedelta(minutes=1),
            expires_at=_SCORM_NOW + timedelta(minutes=30),
        )

    def action_target(frame, context, intent):
        if intent.coordinates is not None:
            target_surface = COORDINATE_CONTROL
            target_bounds = SCORMTargetBounds(0, 0, 64, 32)
            target_evidence_kind = NATIVE_ACCESSIBILITY_CONTROL
            accessibility_role_sha256 = hashlib.sha256(b"button").hexdigest()
            accessibility_name_sha256 = hashlib.sha256(
                f"{target_semantic}:visible-control".encode()
            ).hexdigest()
        elif intent.name == "wait":
            target_surface = FRAME_WAIT
            target_bounds = None
            target_evidence_kind = BOUND_WINDOW_SURFACE
            accessibility_role_sha256 = None
            accessibility_name_sha256 = None
        else:
            target_surface = FOCUSED_CONTROL
            target_bounds = None
            target_evidence_kind = NATIVE_FOCUSED_CONTROL
            accessibility_role_sha256 = hashlib.sha256(b"focused-control").hexdigest()
            accessibility_name_sha256 = hashlib.sha256(
                f"{target_semantic}:focused-control".encode()
            ).hexdigest()
        semantic = WINDOW_NAVIGATION if intent.name == "wait" else target_semantic
        credential_effect = {
            ASSESSMENT_CONTROL: PREVIEW_ONLY,
            CREDENTIAL_COMMIT_CONTROL: REAL_IDENTITY_BOUND,
            NAVIGATION_CONTROL: NO_CREDENTIAL_EFFECT,
            WINDOW_NAVIGATION: NO_CREDENTIAL_EFFECT,
        }[semantic]
        return SCORMActionTargetEvidence.issue(
            owner_secret=_SCORM_OWNER_SECRET,
            provider_context=context,
            frame=frame,
            intent=intent,
            target_surface=target_surface,
            target_bounds=target_bounds,
            target_evidence_kind=target_evidence_kind,
            target_evidence_sha256=hashlib.sha256(
                f"{intent.action_sha256}:{semantic}:target".encode()
            ).hexdigest(),
            accessibility_role_sha256=accessibility_role_sha256,
            accessibility_name_sha256=accessibility_name_sha256,
            accessibility_automation_id_sha256=None,
            target_semantic=semantic,
            interaction_evidence_kind=f"owner_benchmark_{semantic}",
            interaction_evidence_sha256=hashlib.sha256(
                f"{intent.action_sha256}:{semantic}:interaction".encode()
            ).hexdigest(),
            credential_effect=credential_effect,
            effect_evidence_kind=f"owner_benchmark_{credential_effect}_effect",
            effect_evidence_sha256=hashlib.sha256(
                f"{intent.action_sha256}:{credential_effect}:effect".encode()
            ).hexdigest(),
            issued_at=_SCORM_NOW - timedelta(seconds=30),
            expires_at=_SCORM_NOW + timedelta(minutes=4),
        )

    def benchmark_grant(frame, context, intent, target):
        if not grant_enabled:
            return None
        return SCORMBenchmarkGrant.issue(
            owner_secret=_SCORM_OWNER_SECRET,
            benchmark_id="owner-benchmark-action-v1",
            replay_nonce="frame-grant-replay-nonce-0001",
            run_authority=run_authority,
            provider_context=context,
            frame=frame,
            intent=intent,
            action_target=target,
            issued_at=_SCORM_NOW - timedelta(seconds=20),
            expires_at=_SCORM_NOW + timedelta(minutes=3),
        )

    gate = HNCScormCoherenceGate(
        _SCORM_SECRET,
        owner_benchmark_keys={
            "aureon-hermetic-owner-benchmark-key-v1": _SCORM_OWNER_SECRET
        },
        replay_ledger=SCORMActionReplayLedger(
            tmp_path / "replay",
            marker_secret=_SCORM_SECRET,
        ),
    )
    return SCORMVisionRuntimeAuthority(
        active_session=active,
        coherence_gate=gate,
        run_authority=run_authority,
        provider_context_supplier=provider_context,
        action_target_supplier=action_target,
        benchmark_grant_supplier=benchmark_grant,
        utc_now=lambda: _SCORM_NOW,
    )


def test_frame_artifact_png_source_rebinds_retained_bytes(tmp_path: Path) -> None:
    png = _png_bytes()
    store = FrameArtifactStore(tmp_path.resolve())
    frame = CapturedScreen(image_bytes=png, width=64, height=32)
    artifact = store.retain(frame, screenshot_sha256=hashlib.sha256(png).hexdigest())
    observation = _observation(png, artifact=artifact)

    loaded = FrameArtifactPNGSource(tmp_path.resolve()).read_png(
        observation,
        max_bytes=len(png),
    )

    assert loaded == png


def test_frame_artifact_png_source_rejects_tampered_cas_bytes(tmp_path: Path) -> None:
    png = _png_bytes()
    store = FrameArtifactStore(tmp_path.resolve())
    artifact = store.retain(
        CapturedScreen(image_bytes=png, width=64, height=32),
        screenshot_sha256=hashlib.sha256(png).hexdigest(),
    )
    target = tmp_path / artifact.png_relative_path
    target.write_bytes(_png_bytes(color=(200, 10, 10)))

    with pytest.raises(PlannerImageError, match="hash_mismatch|length_mismatch"):
        FrameArtifactPNGSource(tmp_path.resolve()).read_png(
            _observation(png, artifact=artifact),
            max_bytes=1024 * 1024,
        )


def test_vision_planner_posts_one_bound_base64_png_to_native_loopback_chat(
    tmp_path: Path,
) -> None:
    png = _png_bytes()
    source = _ImageSource(png)
    transport = _Transport(_click_response())
    planner = LocalOllamaVisionPlanner(
        model="local-vision-model",
        image_source=source,
        transport=transport,
        timeout_seconds=7,
        scorm_authority=_scorm_authority(tmp_path),
    )

    decision = planner.plan("Continue the public SCORM preview", _observation(png), [])

    assert decision.kind == "action"
    assert decision.action is not None and decision.action.params == {"x": 20, "y": 20}
    assert source.calls == 1
    assert len(transport.calls) == 1
    call = transport.calls[0]
    assert call["url"] == "http://127.0.0.1:11434/api/chat"
    assert call["timeout_seconds"] == 7.0
    payload = call["payload"]
    assert payload["stream"] is False
    assert payload["options"] == {
        "num_ctx": 8_192,
        "num_predict": 512,
        "temperature": 0,
    }
    assert isinstance(payload["format"], dict)
    user_message = payload["messages"][1]
    assert user_message["images"] == [base64.b64encode(png).decode("ascii")]
    assert not user_message["images"][0].startswith("data:")
    prompt = json.loads(user_message["content"])
    binding = prompt["observation"]["image_binding"]
    assert binding == {
        "byte_length": len(png),
        "encoding": "base64",
        "mime_type": "image/png",
        "sha256": hashlib.sha256(png).hexdigest(),
    }
    assert prompt["observation"]["observation_id"] == _observation(png).observation_id


def test_vision_planner_grounds_required_course_movie_play_control(
    tmp_path: Path,
) -> None:
    png = _png_bytes()
    source = _ImageSource(png)
    planner = LocalOllamaVisionPlanner(
        model="local-vision-model",
        image_source=source,
        transport=_Transport(AssertionError("model must not run")),
        scorm_authority=_scorm_authority(tmp_path),
    )
    observation = replace(
        _observation(png),
        ocr_tokens=(
            OCRToken("Intro Movie", 2, 2, 20, 5, 0.99),
            OCRToken(
                "View all the items on the page to proceed",
                2,
                10,
                60,
                5,
                0.99,
            ),
        ),
    )

    decision = planner.plan("Complete the course", observation, [])

    assert decision.kind == "action"
    assert decision.action == GuiAction(
        "move_mouse", {"x": 18, "y": 18, "duration": 0.15}
    )
    assert decision.reason == "provider-verified-course-play-toggle:move"
    assert source.calls == 0


def test_vision_planner_grounds_first_unclicked_definition_tab(
    tmp_path: Path,
) -> None:
    png = _png_bytes()
    source = _ImageSource(png)
    planner = LocalOllamaVisionPlanner(
        model="local-vision-model",
        image_source=source,
        transport=_Transport(AssertionError("model must not run")),
        scorm_authority=_scorm_authority(tmp_path),
    )
    observation = replace(
        _observation(png),
        ocr_tokens=(
            OCRToken("Click on each of the tabs", 1, 1, 45, 5, 0.99),
            OCRToken("Energy", 4, 10, 10, 5, 0.99),
            OCRToken("Isolating", 15, 10, 12, 5, 0.99),
            OCRToken("Device", 28, 10, 10, 5, 0.99),
            OCRToken("General", 4, 20, 10, 5, 0.99),
            OCRToken("LOTO", 15, 20, 8, 5, 0.99),
            OCRToken("Lock", 24, 20, 8, 5, 0.99),
        ),
    )

    decision = planner.plan("Complete the course", observation, [])

    assert decision.kind == "action"
    assert decision.action == GuiAction(
        "move_mouse", {"x": 21, "y": 12, "duration": 0.15}
    )
    assert decision.reason.startswith("grounded-course-definition-tab:energy")
    assert source.calls == 0


def test_vision_planner_moves_then_clicks_exact_ocr_grounded_course_arrow(
    tmp_path: Path,
) -> None:
    png = _png_bytes()
    source = _ImageSource(png)
    transport = _Transport(AssertionError("model must not run for grounded navigation"))
    authority = _scorm_authority(tmp_path)
    planner = LocalOllamaVisionPlanner(
        model="local-vision-model",
        image_source=source,
        transport=transport,
        scorm_authority=authority,
    )
    tokens = (
        OCRToken("Page", 2, 2, 12, 5, 0.99),
        OCRToken("1", 15, 2, 3, 5, 0.99),
        OCRToken("of", 20, 2, 5, 5, 0.99),
        OCRToken("54", 27, 2, 6, 5, 0.99),
        OCRToken("Click", 3, 12, 10, 5, 0.99),
        OCRToken("the", 14, 12, 7, 5, 0.99),
        OCRToken("next", 22, 12, 9, 5, 0.99),
        OCRToken("arrow", 32, 12, 11, 5, 0.99),
        OCRToken("to", 44, 12, 5, 5, 0.99),
        OCRToken("proceed", 49, 12, 14, 5, 0.99),
        OCRToken("—", 54, 22, 5, 5, 0.0),
    )
    before = replace(
        _observation(png, sequence=1),
        ocr_tokens=tokens,
        cursor_x=5,
        cursor_y=5,
    )

    move = planner.plan("Complete the SCORM course", before, [])

    assert move.kind == "action"
    assert move.action == GuiAction(
        "move_mouse", {"x": 47, "y": 20, "duration": 0.15}
    )
    assert move.expected == ObservationPredicate("observation_fresh", "")
    assert move.action_authorization is not None
    authority.verify_and_consume_action(move.action_authorization, before, move.action)

    after = replace(
        _observation(png, sequence=2),
        ocr_tokens=tokens,
        cursor_x=47,
        cursor_y=20,
    )
    transition = RuntimeTransition(
        step=1,
        before=before,
        decision=move,
        result=ActionResult(
            ok=True,
            code="executed",
            details={},
            dispatch_state="dispatched",
        ),
        after=after,
        screen_changed=False,
        observation_fresh=True,
        verified=True,
        verification_reason="predicate_satisfied",
    )

    click = planner.plan("Complete the SCORM course", after, [transition])

    assert click.kind == "action"
    assert click.action == GuiAction("left_click", {"x": 47, "y": 20})
    assert click.expected == ObservationPredicate("screen_changed", "")
    assert click.action_authorization is not None
    assert source.calls == 0
    assert transport.calls == []


def test_vision_planner_rejects_nonlocal_image_source(tmp_path: Path) -> None:
    class RemoteSource(_ImageSource):
        locality = "remote"

    with pytest.raises(ValueError, match="local ObservationPNGSource"):
        LocalOllamaVisionPlanner(
            model="local-vision-model",
            image_source=RemoteSource(_png_bytes()),
            transport=_Transport(_click_response()),
            scorm_authority=_scorm_authority(tmp_path),
        )


def test_vision_planner_rejects_image_hash_or_request_limit_before_transport(
    tmp_path: Path,
) -> None:
    png = _png_bytes()
    transport = _Transport(_click_response())
    mismatched = _ImageSource(_png_bytes(color=(1, 2, 3)))
    with pytest.raises((AssertionError, PlannerImageError)):
        LocalOllamaVisionPlanner(
            model="local-vision-model",
            image_source=mismatched,
            transport=transport,
            scorm_authority=_scorm_authority(tmp_path / "mismatch"),
        ).plan("SCORM preview", _observation(png), [])
    assert transport.calls == []

    source = _ImageSource(png)
    with pytest.raises(PlannerImageError, match="request_exceeded"):
        LocalOllamaVisionPlanner(
            model="local-vision-model",
            image_source=source,
            transport=transport,
            max_image_bytes=1024,
            max_request_bytes=1025,
            scorm_authority=_scorm_authority(tmp_path / "limit"),
        ).plan("SCORM preview", _observation(png), [])
    assert transport.calls == []


@pytest.mark.parametrize(
    ("text", "expected_kind"),
    [
        ("Please sign in to continue", "login"),
        ("Email Password Continue", "login"),
        ("Enter your authenticator verification code", "mfa"),
        ("Please complete this CAPTCHA", "captcha"),
        ("Verify your identity to continue", "identity_prerequisite"),
    ],
)
def test_vision_planner_protected_prerequisites_pause_without_model_or_image(
    tmp_path: Path,
    text: str,
    expected_kind: str,
) -> None:
    png = _png_bytes()
    source = _ImageSource(png)
    transport = _Transport(AssertionError("model must not run"))

    decision = LocalOllamaVisionPlanner(
        model="local-vision-model",
        image_source=source,
        transport=transport,
        scorm_authority=_scorm_authority(tmp_path),
    ).plan("Continue the SCORM preview", _observation(png, text=text), [])

    assert decision.kind == "pause"
    assert decision.pause_kind == expected_kind
    assert source.calls == 0
    assert transport.calls == []


def test_vision_planner_assessment_requires_exact_grant_then_reauthorizes_action(
    tmp_path: Path,
) -> None:
    png = _png_bytes()
    observation = _observation(png, text="Certification exam question")
    denied_transport = _Transport(_click_response())
    denied = LocalOllamaVisionPlanner(
        model="local-vision-model",
        image_source=_ImageSource(png),
        transport=denied_transport,
        scorm_authority=_scorm_authority(
            tmp_path / "denied",
            target_semantic=ASSESSMENT_CONTROL,
        ),
    ).plan("Complete the public preview assessment", observation, [])
    assert denied.kind == "pause"
    assert denied.pause_kind == "authorization_prerequisite"
    assert len(denied_transport.calls) == 1

    allowed_transport = _Transport(_click_response())
    allowed = LocalOllamaVisionPlanner(
        model="local-vision-model",
        image_source=_ImageSource(png),
        transport=allowed_transport,
        scorm_authority=_scorm_authority(
            tmp_path / "allowed",
            target_semantic=ASSESSMENT_CONTROL,
            grant_enabled=True,
        ),
    ).plan("Complete the public preview assessment", observation, [])

    assert allowed.kind == "action"
    assert allowed.action_authorization is not None
    assert (
        allowed.action_authorization.receipt.benchmark_grant_sha256 is not None
    )
    sent = json.loads(allowed_transport.calls[0]["payload"]["messages"][1]["content"])
    assert sent["host_post_intent_target_authorization_required"] is True
    assert "signed_benchmark_assessment_authorized" not in sent


def test_scorm_action_receipt_is_consumed_once_immediately_before_dispatch(
    tmp_path: Path,
) -> None:
    png = _png_bytes()
    observation = _observation(png)
    authority = _scorm_authority(tmp_path)
    decision = LocalOllamaVisionPlanner(
        model="local-vision-model",
        image_source=_ImageSource(png),
        transport=_Transport(_click_response()),
        scorm_authority=authority,
    ).plan("Continue the public preview", observation, [])
    assert decision.action is not None
    assert decision.action_authorization is not None

    class RecordingGateway:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, object], str, str]] = []

        def execute(
            self,
            action,
            params,
            *,
            target_binding_id,
            expected_before_sha256,
        ):
            self.calls.append(
                (
                    action,
                    dict(params),
                    target_binding_id,
                    expected_before_sha256,
                )
            )
            return DesktopActionResult(
                ok=True,
                action=action,
                action_id="00000000-0000-0000-0000-000000000001",
                dry_run=False,
                reason="executed",
            )

    gateway = RecordingGateway()
    executor = GovernedGatewayExecutor(
        gateway,  # type: ignore[arg-type]
        binding_supplier=authority.authorize_binding_id,
        scorm_authority=authority,
    )
    first = executor.execute(
        decision.action,
        source_observation=observation,
        action_authorization=decision.action_authorization,
    )
    replay = executor.execute(
        decision.action,
        source_observation=observation,
        action_authorization=decision.action_authorization,
    )

    assert first.ok is True
    assert first.details["scorm_action_authority"]["receipt_sha256"] == (
        decision.action_authorization.receipt.receipt_sha256
    )
    assert replay.code == "scorm_control_authorization_required"
    assert gateway.calls == [
        (
            "click",
            {"x": 20, "y": 20},
            "bound-window",
            observation.screenshot_sha256,
        )
    ]


def test_owner_attestation_requires_host_proof_and_model_cannot_invent_it(
    tmp_path: Path,
) -> None:
    png = _png_bytes()
    source = _ImageSource(png)
    transport = _Transport(_click_response())
    proven = LocalOllamaVisionPlanner(
        model="local-vision-model",
        image_source=source,
        transport=transport,
        scorm_authority=_scorm_authority(
            tmp_path / "proven",
            target_semantic=CREDENTIAL_COMMIT_CONTROL,
        ),
    ).plan("Continue", _observation(png), [])
    assert proven.kind == "human_required"
    assert proven.human_gate == "identity_attestation"
    assert source.calls == 1
    assert len(transport.calls) == 1

    invented_transport = _Transport(
        _response(
            {
                "kind": "human_required",
                "reason": "invented",
                "human_gate": "identity_attestation",
            }
        )
    )
    with pytest.raises(PlannerResponseError, match="cannot assert owner attestation"):
        LocalOllamaVisionPlanner(
            model="local-vision-model",
            image_source=_ImageSource(png),
            transport=invented_transport,
            scorm_authority=_scorm_authority(tmp_path / "invented"),
        ).plan("Continue", _observation(png), [])


def test_vision_model_pause_is_strict_and_protected_text_action_is_not_dispatched(
    tmp_path: Path,
) -> None:
    png = _png_bytes()
    paused = LocalOllamaVisionPlanner(
        model="local-vision-model",
        image_source=_ImageSource(png),
        scorm_authority=_scorm_authority(tmp_path / "pause"),
        transport=_Transport(
            _response(
                {
                    "kind": "pause",
                    "reason": "Login is required",
                    "pause_kind": "login",
                }
            )
        ),
    ).plan("Continue", _observation(png), [])
    assert paused.kind == "pause" and paused.pause_kind == "login"

    protected = LocalOllamaVisionPlanner(
        model="local-vision-model",
        image_source=_ImageSource(png),
        scorm_authority=_scorm_authority(tmp_path / "protected"),
        transport=_Transport(
            _response(
                {
                    "kind": "action",
                    "reason": "unsafe credential proposal",
                    "action": {
                        "name": "type_text",
                        "params": {"text": "secret", "text_class": "credential"},
                    },
                    "expected": {"kind": "screen_changed", "value": ""},
                }
            )
        ),
    ).plan("Continue", _observation(png), [])
    assert protected.kind == "pause" and protected.pause_kind == "login"


class _StableObserver:
    def __init__(self, observations) -> None:
        self.observations = list(observations)

    def observe(self):
        return self.observations.pop(0)


class _PausePlanner:
    locality = "local"

    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.calls = 0

    def plan(self, _goal, _observation, _history):
        self.calls += 1
        self.events.append("plan")
        return PlannerDecision(
            kind="pause",
            reason="Resume after login",
            pause_kind="login",
        )


class _NoActionExecutor:
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, _action, *, source_observation=None):
        self.calls += 1
        return ActionResult(ok=True, code="unexpected")


def test_runtime_scorm_pause_and_resume_validation_dispatch_no_action() -> None:
    png = _png_bytes()
    observations = [
        _observation(png, text="Certification exam", sequence=1, identity="first"),
        _observation(png, text="Certification exam", sequence=2, identity="second"),
    ]
    events: list[str] = []
    planner = _PausePlanner(events)
    executor = _NoActionExecutor()

    def validate(_observation):
        events.append("resume")
        return True

    result = LocalGUIRuntime(
        _StableObserver(observations),
        planner,
        executor,
        limits=RuntimeLimits(stable_frame_interval_seconds=0),
        planner_handles_human_gates=True,
        resume_validator=validate,
        sleeper=lambda _seconds: None,
    ).run("SCORM vision benchmark")

    assert result.status == "paused"
    assert result.pause_kind == "login"
    assert result.action_count == 0
    assert result.transitions == ()
    assert events == ["resume", "plan"]
    assert executor.calls == 0


def test_runtime_legacy_gate_behavior_remains_unchanged() -> None:
    png = _png_bytes()
    planner = _PausePlanner([])
    executor = _NoActionExecutor()
    result = LocalGUIRuntime(
        _StableObserver(
            [
                _observation(png, text="Certification exam", sequence=1, identity="first"),
                _observation(png, text="Certification exam", sequence=2, identity="second"),
            ]
        ),
        planner,
        executor,
        limits=RuntimeLimits(stable_frame_interval_seconds=0),
        sleeper=lambda _seconds: None,
    ).run("legacy planner")
    assert result.status == "human_required"
    assert planner.calls == 0
    assert executor.calls == 0


def test_runtime_rejects_resume_before_planning_or_action() -> None:
    png = _png_bytes()
    planner = _PausePlanner([])
    executor = _NoActionExecutor()
    result = LocalGUIRuntime(
        _StableObserver(
            [
                _observation(png, sequence=1, identity="first"),
                _observation(png, sequence=2, identity="second"),
            ]
        ),
        planner,
        executor,
        limits=RuntimeLimits(stable_frame_interval_seconds=0),
        resume_validator=lambda _observation: False,
        sleeper=lambda _seconds: None,
    ).run("resume")
    assert result.status == "resume_rejected"
    assert planner.calls == 0
    assert executor.calls == 0


def test_runtime_scorm_mismatch_recovery_is_exact_and_bounded() -> None:
    png = _png_bytes()
    recovered: list[str] = []
    events = [
            GatewayObservationRejectedError("target_window_mismatch"),
            _observation(png, sequence=1, identity="settled-a"),
            _observation(png, sequence=2, identity="settled-b"),
        ]

    class ScriptObserver:
        def observe(self):
            event = events.pop(0)
            if isinstance(event, BaseException):
                raise event
            return event

    result = LocalGUIRuntime(
        ScriptObserver(),
        _PausePlanner([]),
        _NoActionExecutor(),
        limits=RuntimeLimits(
            stable_frame_max_attempts=4,
            stable_frame_interval_seconds=0,
        ),
        planner_handles_human_gates=True,
        target_window_mismatch_recovery=lambda: recovered.append("recover") or True,
        sleeper=lambda _seconds: None,
    ).run("SCORM governed handoff")

    assert result.status == "paused"
    assert recovered == ["recover"]


def test_runtime_never_retries_an_action_dispatched_before_window_handoff() -> None:
    png = _png_bytes()
    before_a = _observation(png, sequence=1, identity="before-a")
    before_b = _observation(png, sequence=2, identity="before-b")
    after_a = _observation(png, sequence=3, identity="after-a")
    after_b = _observation(png, sequence=4, identity="after-b")

    class ActionPlanner:
        locality = "local"

        def __init__(self) -> None:
            self.calls = 0

        def plan(self, _goal, _observation, _history):
            self.calls += 1
            return PlannerDecision(
                kind="action",
                reason="Open the governed child window",
                action=GuiAction("left_click", {"x": 20, "y": 20}),
                expected=ObservationPredicate(
                    "ocr_contains",
                    "expected destination",
                ),
            )

    class DispatchedExecutor:
        def __init__(self) -> None:
            self.calls = 0

        def execute(self, _action, *, source_observation=None):
            self.calls += 1
            assert source_observation == before_b
            return ActionResult(True, "gateway_executed_handoff_required")

    planner = ActionPlanner()
    executor = DispatchedExecutor()
    result = LocalGUIRuntime(
        _StableObserver([before_a, before_b, after_a, after_b]),
        planner,
        executor,
        limits=RuntimeLimits(
            max_retries_per_action=5,
            stable_frame_interval_seconds=0,
        ),
        sleeper=lambda _seconds: None,
    ).run("Open the child page")

    assert result.status == "post_dispatch_verification_failed"
    assert executor.calls == 1
    assert planner.calls == 1
    assert result.transitions[0].verification_reason == "predicate_failed:ocr_contains"


def test_dynamic_screenshot_binding_supplier_never_latches_a_stale_id() -> None:
    class RejectedGateway:
        def __init__(self) -> None:
            self.binding_ids: list[str] = []

        def observe(self, *, target_binding_id=None):
            self.binding_ids.append(target_binding_id)
            return DesktopActionResult(
                ok=False,
                action="observe",
                action_id="not-used-for-rejection",
                dry_run=False,
                reason="target_window_mismatch",
            )

    supplied = iter(("binding-generation-0", "binding-generation-1"))
    gateway = RejectedGateway()
    backend = GatewayScreenshotBackend(
        gateway,  # type: ignore[arg-type]
        binding_supplier=lambda: next(supplied),
    )

    for _ in range(2):
        with pytest.raises(GatewayObservationRejectedError) as rejected:
            backend.capture()
        assert rejected.value.reason == "target_window_mismatch"
    assert gateway.binding_ids == ["binding-generation-0", "binding-generation-1"]


def test_dynamic_binding_supplier_failure_routes_only_to_exact_mismatch_recovery() -> None:
    backend = GatewayScreenshotBackend(
        SimpleNamespace(),  # type: ignore[arg-type]
        binding_supplier=lambda: (_ for _ in ()).throw(RuntimeError("expired")),
    )

    with pytest.raises(GatewayObservationRejectedError) as rejected:
        backend.capture()
    assert rejected.value.reason == "target_window_mismatch"


def _checkpoint_store(tmp_path: Path, *, run_authority: str | None = None):
    return HashOnlyPauseCheckpointStore(
        (tmp_path / "run.pause.json").resolve(),
        run_id="run-1",
        build_id="build-1",
        goal="Continue the SCORM benchmark",
        run_authority_sha256=(
            run_authority or hashlib.sha256(b"run-authority").hexdigest()
        ),
        control_grant_sha256=hashlib.sha256(b"control-grant").hexdigest(),
    )


def test_hash_only_pause_checkpoint_is_atomic_bound_and_consumed(tmp_path: Path) -> None:
    png = _png_bytes()
    paused = _observation(png, sequence=3, identity="paused")
    store = _checkpoint_store(tmp_path)

    checkpoint = store.create(paused, (), pause_kind="mfa")

    payload = json.loads(store.path.read_text(encoding="ascii"))
    assert payload["schema_version"] == "aureon-local-gui-pause-v1"
    assert payload["pause_kind"] == "mfa"
    for key, value in payload.items():
        if key not in {"schema_version", "pause_kind"}:
            assert isinstance(value, str) and len(value) == 64
    assert store.load().checkpoint_sha256 == checkpoint.checkpoint_sha256

    fresh = _observation(png, sequence=1, identity="fresh")
    assert store.validate_fresh_observation_and_consume(fresh) is True
    assert not store.path.exists()
    assert len(list(tmp_path.glob("*.consumed.json"))) == 1


def test_pause_checkpoint_requires_exact_context_freshness_and_window(tmp_path: Path) -> None:
    png = _png_bytes()
    paused = _observation(png, sequence=3, identity="paused")
    store = _checkpoint_store(tmp_path)
    store.create(paused, (), pause_kind="login")

    wrong_grant = _checkpoint_store(
        tmp_path,
        run_authority=hashlib.sha256(b"other").hexdigest(),
    )
    with pytest.raises(PauseCheckpointError, match="context_mismatch"):
        wrong_grant.load()

    store.load()
    with pytest.raises(PauseCheckpointError, match="not_fresh"):
        store.validate_fresh_observation_and_consume(paused)
    store.load()
    wrong_window = _observation(png, sequence=4, identity="fresh", handle=999)
    with pytest.raises(PauseCheckpointError, match="window_binding_mismatch"):
        store.validate_fresh_observation_and_consume(wrong_window)
    assert store.path.exists()


def test_pause_checkpoint_tampering_fails_closed(tmp_path: Path) -> None:
    store = _checkpoint_store(tmp_path)
    store.create(_observation(_png_bytes(), sequence=3, identity="paused"), (), pause_kind="captcha")
    payload = json.loads(store.path.read_text(encoding="ascii"))
    payload["window_sha256"] = hashlib.sha256(b"tampered").hexdigest()
    store.path.write_text(json.dumps(payload), encoding="ascii")

    with pytest.raises(PauseCheckpointError, match="digest_mismatch"):
        store.load()


def test_scorm_vision_config_is_explicit_and_grant_bound(tmp_path: Path) -> None:
    run_authority = hashlib.sha256(b"signed-run-authority").hexdigest()
    control_grant = hashlib.sha256(b"control-grant").hexdigest()
    config = LocalGUIOrganismConfig(
        goal="Complete the public preview assessment",
        expected_window_title="Provider SCORM Preview",
        allowed_actions=("move", "click"),
        planner_kind="scorm_vision",
        scorm_run_authority_sha256=run_authority,
        scorm_control_grant_sha256=control_grant,
        state_directory=tmp_path,
        run_id="scorm-vision-run",
    )
    assert config.planner_kind == "scorm_vision"
    assert config.scorm_run_authority_sha256 == run_authority
    assert config.scorm_control_grant_sha256 == control_grant
    assert config.pause_checkpoint_path == tmp_path.resolve() / "scorm-vision-run.pause.json"

    with pytest.raises(
        OrganismConfigurationError,
        match="scorm_vision_requires_run_authority_sha256",
    ):
        LocalGUIOrganismConfig(
            goal="Navigate the public preview",
            expected_window_title="Provider SCORM Preview",
            allowed_actions=("move", "click"),
            planner_kind="scorm_vision",
            state_directory=tmp_path,
        )
    with pytest.raises(
        OrganismConfigurationError,
        match="scorm_vision_requires_control_grant_sha256",
    ):
        LocalGUIOrganismConfig(
            goal="Navigate the public preview",
            expected_window_title="Provider SCORM Preview",
            allowed_actions=("move", "click"),
            planner_kind="scorm_vision",
            scorm_run_authority_sha256=run_authority,
            state_directory=tmp_path,
        )
    with pytest.raises(TypeError, match="resume_from_pause"):
        LocalGUIOrganismConfig(
            goal="Navigate a local sandbox",
            expected_window_title="Sandbox",
            allowed_actions=("move", "click"),
            state_directory=tmp_path,
            **{"resume_from_pause": True},
        )

    import aureon.operator.local_gui_organism as organism_module

    assert "resume" not in organism_module._parser().format_help().casefold()
    with pytest.raises(SystemExit) as rejected:
        organism_module._parser().parse_args(
            [
                "run",
                "--goal",
                "Navigate a local sandbox",
                "--window-title",
                "Sandbox",
                "--allow-action",
                "move",
                "--resume-from-pause",
            ]
        )
    assert rejected.value.code == 2


class _LifecycleGateway:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.binding_id = "bound-window"

    def bind_target_window(self, _title, *, expected_process_id=None):
        self.calls.append("bind")
        return SimpleNamespace(binding_id=self.binding_id)

    def require_single_target_binding_id(self):
        self.calls.append("require-binding")
        return self.binding_id

    def authorize_live(self, _token, **_kwargs):
        self.calls.append("authorize")
        return SimpleNamespace(lease_id="lease")

    def disarm(self, *, reason):
        self.calls.append(f"disarm:{reason}")

    def revoke_live_authorization(self, *, reason):
        self.calls.append(f"revoke:{reason}")

    def status(self):
        return {"emergency_stopped": False}


def test_scorm_vision_builder_wires_bound_png_and_pause_store(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import aureon.operator.local_gui_organism as organism_module

    executable = tmp_path / "tesseract.exe"
    executable.write_bytes(b"test executable")
    gateway = _LifecycleGateway()
    monkeypatch.setattr(
        organism_module,
        "get_governed_desktop_gateway",
        lambda **_kwargs: gateway,
    )
    authority = _scorm_authority(
        tmp_path / "authority",
        run_id="scorm-builder",
        binding_id=gateway.binding_id,
    )
    config = LocalGUIOrganismConfig(
        goal="Navigate the provider-authorized SCORM preview",
        expected_window_title="Provider SCORM Preview",
        allowed_actions=("move", "click"),
        planner_kind="scorm_vision",
        scorm_run_authority_sha256=authority.run_authority_sha256,
        scorm_control_grant_sha256=authority.control_grant_sha256,
        state_directory=tmp_path / "state",
        run_id="scorm-builder",
    )

    organism = build_local_organism(
        config,
        capability_token="test-token",
        tesseract_executable=executable,
        scorm_runtime_authority=authority,
    )

    assert isinstance(organism.planner, LocalOllamaVisionPlanner)
    assert organism.observer._ocr_backend.crop_to_bound_window is True
    assert organism.observer._ocr_backend.page_segmentation_modes == (None, 6)
    assert isinstance(organism.pause_checkpoint_store, HashOnlyPauseCheckpointStore)
    assert organism.planner.image_source.artifact_root == config.frame_artifact_directory


def test_organism_persists_pause_receipt_and_requires_fresh_run_id(
    tmp_path: Path,
) -> None:
    png = _png_bytes()
    first_authority = _scorm_authority(
        tmp_path / "authority-first",
        run_id="scorm-pause-resume",
    )
    run_authority = first_authority.run_authority_sha256
    control_grant = first_authority.control_grant_sha256
    base = {
        "goal": "Continue the provider-authorized SCORM preview",
        "expected_window_title": "Provider SCORM Preview",
        "allowed_actions": ("move", "click"),
        "planner_kind": "scorm_vision",
        "scorm_run_authority_sha256": run_authority,
        "scorm_control_grant_sha256": control_grant,
        "state_directory": tmp_path,
        "run_id": "scorm-pause-resume",
        "live": True,
    }
    config = LocalGUIOrganismConfig(**base)
    ledger = CourseBenchmarkLedger(
        config.ledger_path,
        actor=ACTOR_ID,
        runtime_id="test-runtime",
        build_id="test-build",
        run_id=config.run_id,
    )
    store = HashOnlyPauseCheckpointStore(
        config.pause_checkpoint_path,
        run_id=config.run_id,
        build_id="test-build",
        goal=config.goal,
        run_authority_sha256=run_authority,
        control_grant_sha256=control_grant,
    )
    executor = _NoActionExecutor()
    first_gateway = _LifecycleGateway()
    first = LocalGUIOrganism(
        config,
        gateway=first_gateway,  # type: ignore[arg-type]
        observer=_StableObserver(
            [
                _observation(png, sequence=1, identity="first-a"),
                _observation(png, sequence=2, identity="first-b"),
            ]
        ),
        planner=_PausePlanner([]),
        ledger=ledger,
        capability_token="first-token",
        pause_checkpoint_store=store,
        scorm_runtime_authority=first_authority,
        executor_factory=lambda _gateway, _binding: executor,
    ).run()

    assert first.status == "paused"
    assert len(first.pause_receipt_sha256) == 64
    assert config.pause_checkpoint_path.is_file()
    assert executor.calls == 0

    rejected_gateway = _LifecycleGateway()
    second_authority = _scorm_authority(
        tmp_path / "authority-second",
        run_id="scorm-pause-resume",
    )
    with pytest.raises(
        OrganismConfigurationError,
        match="pause_receipt_exists_fresh_run_id_required",
    ):
        LocalGUIOrganism(
            config,
            gateway=rejected_gateway,  # type: ignore[arg-type]
            observer=_StableObserver(
                [
                    _observation(png, sequence=1, identity="rejected-a"),
                    _observation(png, sequence=2, identity="rejected-b"),
                ]
            ),
            planner=_PausePlanner([]),
            ledger=ledger,
            capability_token="second-token",
            pause_checkpoint_store=store,
            scorm_runtime_authority=second_authority,
            executor_factory=lambda _gateway, _binding: executor,
        ).run()

    fresh_authority = _scorm_authority(
        tmp_path / "authority-fresh",
        run_id="scorm-pause-fresh-run",
    )
    fresh_config = LocalGUIOrganismConfig(
        goal=base["goal"],
        expected_window_title=base["expected_window_title"],
        allowed_actions=base["allowed_actions"],
        planner_kind="scorm_vision",
        scorm_run_authority_sha256=fresh_authority.run_authority_sha256,
        scorm_control_grant_sha256=fresh_authority.control_grant_sha256,
        state_directory=tmp_path,
        run_id="scorm-pause-fresh-run",
        live=True,
    )
    fresh_ledger = CourseBenchmarkLedger(
        fresh_config.ledger_path,
        actor=ACTOR_ID,
        runtime_id="test-runtime-fresh",
        build_id="test-build",
        run_id=fresh_config.run_id,
    )
    fresh_store = HashOnlyPauseCheckpointStore(
        fresh_config.pause_checkpoint_path,
        run_id=fresh_config.run_id,
        build_id="test-build",
        goal=fresh_config.goal,
        run_authority_sha256=fresh_authority.run_authority_sha256,
        control_grant_sha256=fresh_authority.control_grant_sha256,
    )
    fresh_gateway = _LifecycleGateway()
    second = LocalGUIOrganism(
        fresh_config,
        gateway=fresh_gateway,  # type: ignore[arg-type]
        observer=_StableObserver(
            [
                _observation(png, sequence=1, identity="fresh-a"),
                _observation(png, sequence=2, identity="fresh-b"),
            ]
        ),
        planner=_PausePlanner([]),
        ledger=fresh_ledger,
        capability_token="fresh-token",
        pause_checkpoint_store=fresh_store,
        scorm_runtime_authority=fresh_authority,
        executor_factory=lambda _gateway, _binding: executor,
    ).run()

    assert second.status == "paused"
    assert len(second.pause_receipt_sha256) == 64
    assert second.pause_receipt_sha256 != first.pause_receipt_sha256
    assert executor.calls == 0
    assert len(list(tmp_path.glob("*.consumed.json"))) == 0
    assert first_gateway.calls == [
        "require-binding",
        "authorize",
        "revoke:organism_scorm_run_finally",
    ]
    assert rejected_gateway.calls == []
    assert fresh_gateway.calls == [
        "require-binding",
        "authorize",
        "revoke:organism_scorm_run_finally",
    ]
