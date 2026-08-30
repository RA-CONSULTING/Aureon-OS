from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass, replace
from pathlib import Path

import pytest
from PIL import Image

from aureon.operator import courseops_21_stability as stability_module
from aureon.operator.courseops_21_stability import (
    STABILITY_SCHEMA_VERSION,
    CourseOps21StabilityFingerprint,
)
from aureon.operator.local_gui_observer import (
    CapturedScreen,
    FrameArtifactStore,
    LocalGUIObserver,
    ObservationError,
    OCRToken,
    WindowRect,
)
from aureon.operator.local_gui_runtime import (
    ActionResult,
    GuiAction,
    LocalGUIRuntime,
    ObservationPredicate,
    PlannerDecision,
    RuntimeLimits,
)

_TITLE_SHA256 = hashlib.sha256(b"sealed-courseops-window").hexdigest()
_WINDOW = WindowRect(left=4, top=3, width=28, height=22)


def _encoded_frame(
    image: Image.Image,
    *,
    image_format: str = "PNG",
    window_rect: WindowRect | None = _WINDOW,
) -> CapturedScreen:
    output = io.BytesIO()
    save_options = {"quality": 100, "subsampling": 0} if image_format == "JPEG" else {}
    image.save(output, format=image_format, **save_options)
    telemetry = (
        {}
        if window_rect is None
        else {
            "window_handle": 901,
            "window_process_id": 902,
            "window_title_sha256": _TITLE_SHA256,
            "window_rect": window_rect,
        }
    )
    return CapturedScreen(
        image_bytes=output.getvalue(),
        width=image.width,
        height=image.height,
        mime_type="image/jpeg" if image_format == "JPEG" else "image/png",
        **telemetry,
    )


def _solid_image() -> Image.Image:
    return Image.new("RGB", (40, 30), (244, 246, 248))


def test_fingerprint_ignores_only_bound_windows_final_eight_pixel_gutter() -> None:
    base_image = _solid_image()
    gutter_image = base_image.copy()
    gutter_image.putpixel((31, 10), (1, 2, 3))
    content_image = base_image.copy()
    content_image.putpixel((23, 10), (1, 2, 3))
    outside_image = base_image.copy()
    outside_image.putpixel((1, 1), (1, 2, 3))
    frames = tuple(
        _encoded_frame(image)
        for image in (base_image, gutter_image, content_image, outside_image)
    )
    raw_hashes = tuple(hashlib.sha256(frame.image_bytes).hexdigest() for frame in frames)
    provider = CourseOps21StabilityFingerprint()
    fingerprints = tuple(provider.fingerprint(frame) for frame in frames)

    assert len(set(raw_hashes)) == 4
    assert fingerprints[0] == fingerprints[1]
    assert fingerprints[0] != fingerprints[2]
    assert fingerprints[0] == fingerprints[3]
    assert all(len(value) == 64 and value == value.lower() for value in fingerprints)


def test_live_width_boundary_includes_x826_and_excludes_x827_through_x834() -> None:
    rect = WindowRect(left=10, top=3, width=825, height=22)
    base = Image.new("RGB", (840, 30), (244, 246, 248))
    content_edge = base.copy()
    content_edge.putpixel((826, 10), (1, 2, 3))
    gutter_frames = []
    for x_coordinate in range(827, 835):
        changed = base.copy()
        changed.putpixel((x_coordinate, 10), (1, 2, 3))
        gutter_frames.append(_encoded_frame(changed, window_rect=rect))
    provider = CourseOps21StabilityFingerprint()
    base_hash = provider.fingerprint(_encoded_frame(base, window_rect=rect))

    assert provider.fingerprint(_encoded_frame(content_edge, window_rect=rect)) != base_hash
    assert all(provider.fingerprint(frame) == base_hash for frame in gutter_frames)


def test_fingerprint_fail_closed_decodes_png_and_jpeg_with_exact_dimensions() -> None:
    provider = CourseOps21StabilityFingerprint()
    png = _encoded_frame(_solid_image())
    jpeg = _encoded_frame(_solid_image(), image_format="JPEG")

    assert len(provider.fingerprint(png)) == 64
    assert len(provider.fingerprint(jpeg)) == 64

    with pytest.raises(ObservationError, match="requires_bound_window"):
        provider.fingerprint(_encoded_frame(_solid_image(), window_rect=None))
    with pytest.raises(ObservationError, match="window_outside_frame"):
        provider.fingerprint(
            _encoded_frame(_solid_image(), window_rect=WindowRect(25, 3, 20, 22))
        )
    with pytest.raises(ObservationError, match="no_content_region"):
        provider.fingerprint(
            _encoded_frame(_solid_image(), window_rect=WindowRect(4, 3, 8, 22))
        )
    with pytest.raises(ObservationError, match="dimension_mismatch"):
        provider.fingerprint(replace(png, width=png.width + 1))
    with pytest.raises(ObservationError, match="jpeg_signature_mismatch"):
        provider.fingerprint(replace(png, mime_type="image/jpeg"))
    with pytest.raises(ObservationError, match="image_decode_failed"):
        provider.fingerprint(replace(png, image_bytes=b"\x89PNG\r\n\x1a\ninvalid"))


def test_fingerprint_frame_limits_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _encoded_frame(_solid_image())
    provider = CourseOps21StabilityFingerprint()

    monkeypatch.setattr(stability_module, "MAX_FRAME_BYTES", len(frame.image_bytes) - 1)
    with pytest.raises(ObservationError, match="frame_limit_exceeded"):
        provider.fingerprint(frame)

    monkeypatch.setattr(stability_module, "MAX_FRAME_BYTES", len(frame.image_bytes) + 1)
    monkeypatch.setattr(stability_module, "MAX_FRAME_PIXELS", frame.width * frame.height - 1)
    with pytest.raises(ObservationError, match="frame_limit_exceeded"):
        provider.fingerprint(frame)


@dataclass
class _FrameStream:
    frames: list[CapturedScreen]

    def capture(self) -> CapturedScreen:
        if not self.frames:
            raise AssertionError("unexpected frame request")
        return self.frames.pop(0)


class _NoOCR:
    def recognize(self, _frame: CapturedScreen):
        return ()


class _StopPlanner:
    locality = "local"

    def __init__(self) -> None:
        self.calls = 0
        self.observations = []

    def plan(self, _goal, observation, _history):
        self.calls += 1
        self.observations.append(observation)
        return PlannerDecision(kind="human_required", reason="test stop", human_gate="other")


class _UnusedExecutor:
    def execute(self, _action, *, source_observation=None):
        return ActionResult(True, "unused")


def _runtime_for_frames(
    frames: list[CapturedScreen],
    planner: _StopPlanner,
    *,
    ocr_backend=None,
    vision_hook=None,
    stable_frame_max_attempts: int = 2,
) -> LocalGUIRuntime:
    ticks = iter(float(index) for index in range(1, len(frames) + 1))
    observer = LocalGUIObserver(
        _FrameStream(frames),
        ocr_backend or _NoOCR(),
        vision_hook=vision_hook,
        stability_fingerprint=CourseOps21StabilityFingerprint(),
        clock=lambda: next(ticks),
    )
    return LocalGUIRuntime(
        observer,
        planner,
        _UnusedExecutor(),
        limits=RuntimeLimits(
            stable_frame_max_attempts=stable_frame_max_attempts,
            stable_frame_interval_seconds=0,
        ),
        sleeper=lambda _seconds: None,
    )


def test_right_gutter_only_raw_change_settles_but_one_content_pixel_does_not() -> None:
    base_image = _solid_image()
    gutter_image = base_image.copy()
    gutter_image.putpixel((31, 10), (1, 2, 3))
    content_image = base_image.copy()
    content_image.putpixel((23, 10), (1, 2, 3))

    stable_planner = _StopPlanner()
    settled = _runtime_for_frames(
        [_encoded_frame(base_image), _encoded_frame(gutter_image)],
        stable_planner,
    ).run("settle right scrollbar repaint")
    assert settled.status == "human_required"
    assert stable_planner.calls == 1
    assert settled.final_observation is not None
    assert settled.final_observation.screenshot_sha256 == hashlib.sha256(
        _encoded_frame(gutter_image).image_bytes
    ).hexdigest()

    unstable_planner = _StopPlanner()
    rejected = _runtime_for_frames(
        [_encoded_frame(base_image), _encoded_frame(content_image)],
        unstable_planner,
    ).run("reject content repaint")
    assert rejected.status == "unstable_initial_frame"
    assert unstable_planner.calls == 0


def test_default_raw_stability_behavior_does_not_ignore_the_gutter() -> None:
    base_image = _solid_image()
    gutter_image = base_image.copy()
    gutter_image.putpixel((31, 10), (1, 2, 3))
    frames = [_encoded_frame(base_image), _encoded_frame(gutter_image)]
    ticks = iter((1.0, 2.0))
    planner = _StopPlanner()
    observer = LocalGUIObserver(
        _FrameStream(frames),
        _NoOCR(),
        clock=lambda: next(ticks),
    )

    result = LocalGUIRuntime(
        observer,
        planner,
        _UnusedExecutor(),
        limits=RuntimeLimits(
            stable_frame_max_attempts=2,
            stable_frame_interval_seconds=0,
        ),
        sleeper=lambda _seconds: None,
    ).run("keep the default raw stability contract")

    assert result.status == "unstable_initial_frame"
    assert planner.calls == 0
    assert result.final_observation is not None
    assert "stability_profile" not in result.final_observation.to_dict()
    assert "stability_sha256" not in result.final_observation.to_dict()
    assert "stability_profile" not in result.final_observation.receipt_dict()
    assert "stability_sha256" not in result.final_observation.receipt_dict()


@dataclass
class _OCRStream:
    token_sets: list[tuple[OCRToken, ...]]

    def recognize(self, _frame: CapturedScreen):
        if not self.token_sets:
            raise AssertionError("unexpected OCR request")
        return self.token_sets.pop(0)


def test_normalized_pixels_wait_for_exact_ocr_tokens_to_settle() -> None:
    frames = []
    for index in range(4):
        image = _solid_image()
        image.putpixel((31, 10), (index, index + 1, index + 2))
        frames.append(_encoded_frame(image))
    token_sets = [
        (OCRToken("Loading", 6, 6, 8, 4, 0.8),),
        (OCRToken("Course", 6, 6, 8, 4, 0.8),),
        (OCRToken("Course", 7, 6, 8, 4, 0.8),),
        (OCRToken("Course", 7, 6, 8, 4, 0.8),),
    ]
    raw_hashes = {hashlib.sha256(frame.image_bytes).hexdigest() for frame in frames}
    normalized = {
        CourseOps21StabilityFingerprint().fingerprint(frame) for frame in frames
    }
    planner = _StopPlanner()

    result = _runtime_for_frames(
        frames,
        planner,
        ocr_backend=_OCRStream(token_sets),
        stable_frame_max_attempts=4,
    ).run("wait for semantic perception")

    assert len(raw_hashes) == 4
    assert len(normalized) == 1
    assert result.status == "human_required"
    assert planner.calls == 1
    assert planner.observations[0].sequence == 4


@dataclass
class _VisionStream:
    descriptions: list[str]
    locality = "local"

    def describe(self, _frame: CapturedScreen, _tokens):
        if not self.descriptions:
            raise AssertionError("unexpected vision request")
        return self.descriptions.pop(0)


def test_normalized_pixels_wait_for_vision_text_to_settle() -> None:
    frames = [_encoded_frame(_solid_image()) for _ in range(3)]
    planner = _StopPlanner()

    result = _runtime_for_frames(
        frames,
        planner,
        vision_hook=_VisionStream(["phase-a", "phase-b", "phase-b"]),
        stable_frame_max_attempts=3,
    ).run("wait for local vision perception")

    assert result.status == "human_required"
    assert planner.calls == 1
    assert planner.observations[0].sequence == 3


class _ActionThenStopPlanner:
    locality = "local"

    def __init__(self) -> None:
        self.calls = 0

    def plan(self, _goal, _observation, _history):
        self.calls += 1
        if self.calls == 1:
            return PlannerDecision(
                kind="action",
                reason="exercise the raw action source binding",
                action=GuiAction("left_click", {"x": 10, "y": 10}),
                expected=ObservationPredicate("screen_changed"),
            )
        return PlannerDecision(kind="human_required", reason="test stop", human_gate="other")


class _CapturingExecutor:
    def __init__(self) -> None:
        self.sources = []

    def execute(self, _action, *, source_observation=None):
        self.sources.append(source_observation)
        return ActionResult(True, "executed")


def test_normalized_settling_keeps_raw_sha_as_executor_source_and_transition_cas() -> None:
    base_image = _solid_image()
    gutter_image = base_image.copy()
    gutter_image.putpixel((31, 10), (1, 2, 3))
    content_image = gutter_image.copy()
    content_image.putpixel((23, 10), (4, 5, 6))
    frames = [
        _encoded_frame(base_image),
        _encoded_frame(gutter_image),
        _encoded_frame(content_image),
        _encoded_frame(content_image),
    ]
    raw_source_sha256 = hashlib.sha256(frames[1].image_bytes).hexdigest()
    ticks = iter((1.0, 2.0, 3.0, 4.0))
    planner = _ActionThenStopPlanner()
    executor = _CapturingExecutor()
    observer = LocalGUIObserver(
        _FrameStream(frames),
        _NoOCR(),
        stability_fingerprint=CourseOps21StabilityFingerprint(),
        clock=lambda: next(ticks),
    )

    result = LocalGUIRuntime(
        observer,
        planner,
        executor,
        limits=RuntimeLimits(
            stable_frame_max_attempts=2,
            stable_frame_interval_seconds=0,
        ),
        sleeper=lambda _seconds: None,
    ).run("retain raw action source CAS")

    assert result.status == "human_required"
    assert len(executor.sources) == 1
    assert executor.sources[0].screenshot_sha256 == raw_source_sha256
    assert result.transitions[0].before.screenshot_sha256 == raw_source_sha256
    assert result.transitions[0].to_dict()["action_source_sha256"] == raw_source_sha256
    assert result.transitions[0].screen_changed is True


def test_observer_retains_raw_cas_and_records_optional_stability_hash(tmp_path: Path) -> None:
    frame = _encoded_frame(_solid_image())
    observer = LocalGUIObserver(
        _FrameStream([frame]),
        _NoOCR(),
        stability_fingerprint=CourseOps21StabilityFingerprint(),
        artifact_store=FrameArtifactStore(tmp_path.resolve()),
        clock=lambda: 123.0,
    )

    observed = observer.observe()

    raw_sha256 = hashlib.sha256(frame.image_bytes).hexdigest()
    assert observed.screenshot_sha256 == raw_sha256
    assert observed.stability_profile == STABILITY_SCHEMA_VERSION
    assert observed.stability_sha256 == CourseOps21StabilityFingerprint().fingerprint(frame)
    assert observed.frame_artifact is not None
    assert observed.frame_artifact.sha256 == raw_sha256
    assert (tmp_path / observed.frame_artifact.png_relative_path).read_bytes() == frame.image_bytes
    assert observed.receipt_dict()["screenshot_sha256"] == raw_sha256
    assert observed.receipt_dict()["stability_profile"] == STABILITY_SCHEMA_VERSION
    assert observed.receipt_dict()["stability_sha256"] == observed.stability_sha256


def test_observer_rejects_nonlocal_or_malformed_stability_provider() -> None:
    class _Remote:
        locality = "remote"

        def fingerprint(self, _frame):
            return "0" * 64

    class _Malformed:
        locality = "local"
        profile = STABILITY_SCHEMA_VERSION

        def fingerprint(self, _frame):
            return "not-a-sha256"

    class _InvalidProfile:
        locality = "local"
        profile = "INVALID PROFILE"

        def fingerprint(self, _frame):
            return "0" * 64

    frame = _encoded_frame(_solid_image())
    with pytest.raises(ValueError, match="locality='local'"):
        LocalGUIObserver(_FrameStream([frame]), _NoOCR(), stability_fingerprint=_Remote())
    with pytest.raises(ValueError, match="valid profile"):
        LocalGUIObserver(
            _FrameStream([frame]),
            _NoOCR(),
            stability_fingerprint=_InvalidProfile(),
        )
    with pytest.raises(ObservationError, match="lowercase_sha256"):
        LocalGUIObserver(
            _FrameStream([frame]),
            _NoOCR(),
            stability_fingerprint=_Malformed(),
        ).observe()
