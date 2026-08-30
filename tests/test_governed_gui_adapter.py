from __future__ import annotations

import hashlib
import io
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from aureon.autonomous.aureon_governed_desktop_gateway import (
    DesktopActionResult,
    GovernedDesktopGateway,
    WindowInfo,
)
from aureon.operator.governed_gui_adapter import (
    GatewayScreenshotBackend,
    GovernedGatewayExecutor,
)
from aureon.operator.local_gui_observer import (
    GatewayObservationRejectedError,
    LocalGUIObserver,
    ObservationError,
    OCRToken,
    ScreenObservation,
)
from aureon.operator.local_gui_runtime import GuiAction


class FakeDesktopBackend:
    def __init__(self) -> None:
        self.width = 640
        self.height = 480
        self.image_bytes = self._png((20, 40, 60, 255))
        self.window = WindowInfo(
            handle=101,
            title="Aureon Test Window",
            process_id=202,
            left=0,
            top=0,
            width=self.width,
            height=self.height,
        )
        self.actions: list[tuple[Any, ...]] = []
        self.cursor = (10, 12)
        self.fail_click = False
        self.dpi: tuple[float, float] | None = (144.0, 144.0)

    def _png(self, color: tuple[int, int, int, int]) -> bytes:
        image = Image.new("RGBA", (self.width, self.height), color)
        output = io.BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()

    def capture_screen(self) -> bytes:
        return self.image_bytes

    def screen_size(self) -> tuple[int, int]:
        return self.width, self.height

    def foreground_window(self) -> WindowInfo:
        return self.window

    def window_dpi(self, window: WindowInfo) -> tuple[float, float] | None:
        assert window.handle == self.window.handle
        return self.dpi

    def pointer_position(self) -> tuple[int, int]:
        return self.cursor

    def _changed(self) -> None:
        value = 20 + len(self.actions)
        self.image_bytes = self._png((value, 40, 60, 255))

    def move(self, x: int, y: int, duration: float = 0.0) -> None:
        self.actions.append(("move", x, y, duration))
        self.cursor = (x, y)
        self._changed()

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> None:
        if self.fail_click:
            raise RuntimeError("backend payload must not escape")
        self.actions.append(("click", x, y, button, clicks))
        self.cursor = (x, y)
        self._changed()

    def scroll(self, amount: int, x: int, y: int) -> None:
        self.actions.append(("scroll", amount, x, y))
        self.cursor = (x, y)
        self._changed()

    def type_text(self, text: str, interval: float = 0.02) -> None:
        self.actions.append(("type", text, interval))
        self._changed()

    def press(self, key: str) -> None:
        self.actions.append(("press", key))
        self._changed()

    def hotkey(self, keys: list[str]) -> None:
        self.actions.append(("hotkey", tuple(keys)))
        self._changed()


class NeverCalledGateway:
    def __init__(self) -> None:
        self.execute_calls = 0

    def execute(self, *_args: object, **_kwargs: object) -> object:
        self.execute_calls += 1
        raise AssertionError("gateway must not be called")


def _gateway(
    tmp_path: Path,
    backend: FakeDesktopBackend,
    *,
    max_actions: int = 100,
    min_action_interval: float = 0.0,
) -> GovernedDesktopGateway:
    return GovernedDesktopGateway(
        backend=backend,
        evidence_path=tmp_path / "gateway-evidence.jsonl",
        max_actions_per_window=max_actions,
        min_action_interval_seconds=min_action_interval,
    )


def _bind(gateway: GovernedDesktopGateway) -> str:
    return gateway.bind_target_window("Aureon Test Window").binding_id


def _authorize(gateway: GovernedDesktopGateway, actions: list[str]) -> None:
    gateway.authorize_live(
        "adapter-test-capability-token-32-bytes-minimum",
        ttl_seconds=3600,
        subject="hermetic-adapter-test",
        allowed_actions=actions,
    )


def _source_observation(
    gateway: GovernedDesktopGateway,
    binding_id: str,
    *,
    sequence: int = 1,
) -> ScreenObservation:
    frame = GatewayScreenshotBackend(gateway, binding_id=binding_id).capture()
    digest = hashlib.sha256(frame.image_bytes).hexdigest()
    return ScreenObservation(
        observation_id=hashlib.sha256(f"{digest}:{sequence}".encode()).hexdigest(),
        sequence=sequence,
        captured_at_unix=float(sequence),
        screenshot_sha256=digest,
        width=frame.width,
        height=frame.height,
        ocr_tokens=(),
        mime_type=frame.mime_type,
    )


def test_screenshot_backend_uses_hash_bound_in_memory_gateway_frame(tmp_path: Path) -> None:
    backend = FakeDesktopBackend()
    backend.window = WindowInfo(
        handle=backend.window.handle,
        title=backend.window.title,
        process_id=backend.window.process_id,
        left=100,
        top=80,
        width=300,
        height=200,
    )
    gateway = _gateway(tmp_path, backend)
    binding_id = _bind(gateway)

    screenshot_backend = GatewayScreenshotBackend(gateway, binding_id=binding_id)
    frame = screenshot_backend.capture()

    assert (frame.width, frame.height) == (640, 480)
    assert frame.mime_type == "image/png"
    assert (frame.dpi_x, frame.dpi_y) == (144.0, 144.0)
    with Image.open(io.BytesIO(frame.image_bytes)) as masked:
        assert masked.size == (640, 480)
        assert masked.getpixel((0, 0)) == (0, 0, 0, 255)
        assert masked.getpixel((150, 100)) == (20, 40, 60, 255)
        assert masked.getpixel((639, 479)) == (0, 0, 0, 255)
    assert screenshot_backend.binding_id == binding_id
    evidence = (tmp_path / "gateway-evidence.jsonl").read_text(encoding="utf-8")
    assert "action_started" in evidence
    assert "action_completed" in evidence


def test_gateway_dpi_flows_through_captured_screen_into_runtime_observation(
    tmp_path: Path,
) -> None:
    class EmptyOCRBackend:
        def recognize(self, _frame):
            return ()

    backend = FakeDesktopBackend()
    gateway = _gateway(tmp_path, backend)
    binding_id = _bind(gateway)
    observer = LocalGUIObserver(
        GatewayScreenshotBackend(gateway, binding_id=binding_id),
        EmptyOCRBackend(),
        clock=lambda: 123.0,
    )

    observation = observer.observe()

    assert (observation.dpi_x, observation.dpi_y) == (144.0, 144.0)
    assert observation.receipt_dict()["dpi"] == {"x": 144.0, "y": 144.0}


def test_screenshot_backend_fails_when_gateway_evidence_cannot_be_written(
    tmp_path: Path,
) -> None:
    backend = FakeDesktopBackend()
    evidence_directory = tmp_path / "not-a-jsonl-file"
    evidence_directory.mkdir()
    gateway = _gateway(tmp_path, backend)
    binding_id = _bind(gateway)
    gateway.evidence_path = evidence_directory

    with pytest.raises(
        GatewayObservationRejectedError,
        match="observation_or_evidence_failed:evidence_start_write_failed",
    ) as rejected:
        GatewayScreenshotBackend(gateway, binding_id=binding_id).capture()
    assert rejected.value.reason == "evidence_start_write_failed"


def test_screenshot_backend_requires_and_latches_one_exact_binding(tmp_path: Path) -> None:
    backend = FakeDesktopBackend()
    gateway = _gateway(tmp_path, backend)
    screenshot_backend = GatewayScreenshotBackend(gateway)

    with pytest.raises(ObservationError, match="exact_target_window_binding_required"):
        screenshot_backend.capture()

    binding_id = _bind(gateway)
    assert screenshot_backend.capture().width == 640
    assert screenshot_backend.binding_id == binding_id
    with pytest.raises(ValueError, match="immutable"):
        screenshot_backend.bind_target("00000000-0000-0000-0000-000000000000")


def test_screenshot_backend_rejects_changed_bound_window(tmp_path: Path) -> None:
    backend = FakeDesktopBackend()
    gateway = _gateway(tmp_path, backend)
    binding_id = _bind(gateway)
    screenshot_backend = GatewayScreenshotBackend(gateway, binding_id=binding_id)
    backend.window = WindowInfo(
        handle=backend.window.handle,
        title="Different Window Title",
        process_id=backend.window.process_id,
        left=0,
        top=0,
        width=backend.width,
        height=backend.height,
    )

    with pytest.raises(
        GatewayObservationRejectedError,
        match="observation_or_evidence_failed:target_window_mismatch",
    ) as rejected:
        screenshot_backend.capture()
    assert rejected.value.reason == "target_window_mismatch"


def test_screenshot_backend_does_not_expose_unallowlisted_rejection_reason() -> None:
    class _RejectedGateway:
        def observe(self, *, target_binding_id=None):
            return DesktopActionResult(
                ok=False,
                action="observe",
                action_id="invalid-is-irrelevant-for-a-rejection",
                dry_run=False,
                reason="private backend payload",
            )

    screenshot_backend = GatewayScreenshotBackend(
        _RejectedGateway(),
        binding_id="exact-test-binding",
    )

    with pytest.raises(GatewayObservationRejectedError) as rejected:
        screenshot_backend.capture()
    assert rejected.value.reason == "gateway_rejected"
    assert "private backend payload" not in str(rejected.value)


def test_executor_maps_all_actions_through_live_lease_and_exact_binding(tmp_path: Path) -> None:
    backend = FakeDesktopBackend()
    gateway = _gateway(tmp_path, backend)
    binding_id = _bind(gateway)
    _authorize(
        gateway,
        ["move", "click", "right_click", "double_click", "scroll", "type", "press", "hotkey"],
    )
    executor = GovernedGatewayExecutor(gateway, binding_id=binding_id)
    actions = [
        GuiAction("move_mouse", {"x": 25, "y": 30, "duration": 0.25}),
        GuiAction("left_click", {"x": 25, "y": 30}),
        GuiAction("right_click", {"x": 25, "y": 30}),
        GuiAction("double_click", {"x": 25, "y": 30}),
        GuiAction("scroll", {"x": 25, "y": 30, "clicks": -3}),
        GuiAction(
            "type_text",
            {"text": "ordinary local text", "text_class": "ordinary", "interval": 0.05},
        ),
        GuiAction("press_key", {"key": "enter"}),
        GuiAction("hotkey", {"keys": ["ctrl", "a"]}),
    ]

    results = [
        executor.execute(
            action,
            source_observation=_source_observation(gateway, binding_id, sequence=index),
        )
        for index, action in enumerate(actions, start=1)
    ]

    assert all(result.ok and result.code == "gateway_executed" for result in results)
    assert all(result.details["dry_run"] is False for result in results)
    assert backend.actions == [
        ("move", 25, 30, 0.25),
        ("click", 25, 30, "left", 1),
        ("click", 25, 30, "right", 1),
        ("click", 25, 30, "left", 2),
        ("scroll", -3, 25, 30),
        ("type", "ordinary local text", 0.05),
        ("press", "enter"),
        ("hotkey", ("ctrl", "a")),
    ]
    assert executor.binding_id == binding_id


def test_executor_reports_dry_run_as_not_executed(tmp_path: Path) -> None:
    backend = FakeDesktopBackend()
    gateway = _gateway(tmp_path, backend)
    executor = GovernedGatewayExecutor(gateway, binding_id=_bind(gateway))

    result = executor.execute(
        GuiAction("left_click", {"x": 25, "y": 30}),
        source_observation=_source_observation(gateway, executor.binding_id),
    )

    assert result.ok is False
    assert result.code == "gateway_dry_run"
    assert result.details["dry_run"] is True
    assert backend.actions == []


def test_executor_requires_source_observation_for_every_non_wait_action() -> None:
    gateway = NeverCalledGateway()
    executor = GovernedGatewayExecutor(  # type: ignore[arg-type]
        gateway,
        binding_id="exact-source-binding",
    )

    result = executor.execute(GuiAction("left_click", {"x": 25, "y": 30}))

    assert (result.ok, result.code, result.details) == (
        False,
        "source_observation_required",
        {},
    )
    assert gateway.execute_calls == 0


def test_executor_rejects_stale_source_frame_without_dispatch(tmp_path: Path) -> None:
    backend = FakeDesktopBackend()
    gateway = _gateway(tmp_path, backend)
    binding_id = _bind(gateway)
    _authorize(gateway, ["click"])
    executor = GovernedGatewayExecutor(gateway, binding_id=binding_id)
    source = _source_observation(gateway, binding_id)
    backend.image_bytes = backend._png((99, 40, 60, 255))

    result = executor.execute(
        GuiAction("left_click", {"x": 25, "y": 30}),
        source_observation=source,
    )

    assert (result.ok, result.code) == (False, "gateway_stale_source_frame")
    assert result.dispatch_state == "not_dispatched"
    assert backend.actions == []
    evidence = (tmp_path / "gateway-evidence.jsonl").read_text(encoding="utf-8")
    assert source.screenshot_sha256 in evidence


def test_fresh_screenshot_evidence_bypasses_full_mutation_throttle(tmp_path: Path) -> None:
    backend = FakeDesktopBackend()
    gateway = _gateway(
        tmp_path,
        backend,
        max_actions=1,
        min_action_interval=60.0,
    )
    binding_id = _bind(gateway)
    _authorize(gateway, ["click"])
    executor = GovernedGatewayExecutor(gateway, binding_id=binding_id)

    executed = executor.execute(
        GuiAction("left_click", {"x": 25, "y": 30}),
        source_observation=_source_observation(gateway, binding_id),
    )
    screenshot_backend = GatewayScreenshotBackend(gateway, binding_id=binding_id)
    fresh_frame = screenshot_backend.capture()
    throttled = executor.execute(
        GuiAction("left_click", {"x": 25, "y": 30}),
        source_observation=_source_observation(gateway, binding_id, sequence=2),
    )
    another_fresh_frame = screenshot_backend.capture()

    assert (executed.ok, executed.code) == (True, "gateway_executed")
    assert (throttled.ok, throttled.code) == (False, "gateway_action_rate_min_interval")
    assert fresh_frame.image_bytes == another_fresh_frame.image_bytes
    assert backend.actions == [("click", 25, 30, "left", 1)]


def test_executor_propagates_scope_binding_and_backend_failures(tmp_path: Path) -> None:
    backend = FakeDesktopBackend()
    gateway = _gateway(tmp_path, backend)
    binding_id = _bind(gateway)
    _authorize(gateway, ["click"])
    executor = GovernedGatewayExecutor(gateway, binding_id=binding_id)

    scope_result = executor.execute(
        GuiAction("press_key", {"key": "enter"}),
        source_observation=_source_observation(gateway, binding_id),
    )
    wrong_binding_result = GovernedGatewayExecutor(
        gateway,
        binding_id="00000000-0000-0000-0000-000000000000",
    ).execute(
        GuiAction("left_click", {"x": 25, "y": 30}),
        source_observation=_source_observation(gateway, binding_id, sequence=2),
    )
    backend.fail_click = True
    backend_result = executor.execute(
        GuiAction("left_click", {"x": 25, "y": 30}),
        source_observation=_source_observation(gateway, binding_id, sequence=3),
    )

    assert (scope_result.ok, scope_result.code) == (
        False,
        "gateway_action_outside_lease_scope",
    )
    assert (wrong_binding_result.ok, wrong_binding_result.code) == (
        False,
        "gateway_valid_target_window_binding_required",
    )
    assert (backend_result.ok, backend_result.code) == (False, "gateway_backend_action_failed")
    assert "payload" not in json.dumps(backend_result.to_dict())


@pytest.mark.parametrize("text_class", ["credential", "personal_data"])
def test_executor_never_returns_sensitive_typed_text_in_details(
    tmp_path: Path,
    text_class: str,
) -> None:
    backend = FakeDesktopBackend()
    gateway = _gateway(tmp_path, backend)
    _authorize(gateway, ["type"])
    executor = GovernedGatewayExecutor(gateway, binding_id=_bind(gateway))
    secret_text = f"private-{text_class}-value"

    result = executor.execute(
        GuiAction("type_text", {"text": secret_text, "text_class": text_class}),
        source_observation=_source_observation(gateway, executor.binding_id),
    )

    assert result.ok is True
    serialized_result = json.dumps(result.to_dict(), sort_keys=True)
    assert secret_text not in serialized_result
    assert text_class not in serialized_result
    assert secret_text not in (tmp_path / "gateway-evidence.jsonl").read_text(encoding="utf-8")


def test_assessment_answer_is_human_required_and_never_reaches_gateway() -> None:
    gateway = NeverCalledGateway()
    executor = GovernedGatewayExecutor(gateway, binding_id="exact-assessment-binding")  # type: ignore[arg-type]

    result = executor.execute(
        GuiAction(
            "type_text",
            {
                "text": "an answer that must remain human-only",
                "text_class": "assessment_answer",
            },
        )
    )

    assert (result.ok, result.code, result.details) == (
        False,
        "human_required_certification_assessment",
        {},
    )
    assert gateway.execute_calls == 0


def test_exact_synthetic_assessment_authority_allows_bound_click_and_receipts_it(
    tmp_path: Path,
) -> None:
    backend = FakeDesktopBackend()
    gateway = _gateway(tmp_path, backend)
    _authorize(gateway, ["click"])
    binding_id = _bind(gateway)
    source = replace(
        _source_observation(gateway, binding_id),
        ocr_tokens=(
            OCRToken(
                "Synthetic certification assessment knowledge check",
                10,
                10,
                400,
                20,
            ),
        ),
    )
    calls: list[tuple[str, str]] = []

    class Receipt:
        def to_dict(self):
            return {
                "schema_version": "synthetic-test-receipt-v1",
                "action_sequence": 1,
                "grant_sha256": "1" * 64,
                "context_sha256": "2" * 64,
                "receipt_sha256": "3" * 64,
                "private": "must-not-cross",
            }

    def authorize(observation: ScreenObservation, action: GuiAction):
        calls.append((observation.screenshot_sha256, action.name))
        return Receipt()

    executor = GovernedGatewayExecutor(
        gateway,
        binding_id=binding_id,
        assessment_action_authorizer=authorize,
    )
    result = executor.execute(
        GuiAction("left_click", {"x": 100, "y": 100}),
        source_observation=source,
    )

    assert result.ok is True
    assert calls == [(source.screenshot_sha256, "left_click")]
    assert result.details["synthetic_assessment_authority"] == {
        "schema_version": "synthetic-test-receipt-v1",
        "action_sequence": 1,
        "grant_sha256": "1" * 64,
        "context_sha256": "2" * 64,
        "receipt_sha256": "3" * 64,
    }


def test_wait_uses_injected_sleeper_and_fails_closed_above_bound() -> None:
    gateway = NeverCalledGateway()
    sleeps: list[float] = []
    executor = GovernedGatewayExecutor(  # type: ignore[arg-type]
        gateway,
        binding_id="exact-wait-binding",
        sleeper=sleeps.append,
        max_wait_seconds=0.5,
    )

    completed = executor.execute(GuiAction("wait", {"seconds": 0.25}))
    rejected = executor.execute(GuiAction("wait", {"seconds": 0.75}))

    assert (completed.ok, completed.code) == (True, "wait_completed")
    assert (rejected.ok, rejected.code) == (False, "wait_exceeds_adapter_limit")
    assert sleeps == [0.25]
    assert gateway.execute_calls == 0


def test_executor_marks_post_dispatch_handoff_as_executed_not_retryable() -> None:
    class HandoffGateway:
        def execute(self, action, _params, **_kwargs):
            return DesktopActionResult(
                ok=False,
                action=action,
                action_id="00000000-0000-0000-0000-000000000001",
                dry_run=False,
                reason="target_window_changed_after_action_handoff_required",
            )

    observation = ScreenObservation(
        observation_id="1" * 64,
        sequence=1,
        captured_at_unix=1.0,
        screenshot_sha256="2" * 64,
        width=640,
        height=480,
        ocr_tokens=(),
    )
    result = GovernedGatewayExecutor(
        HandoffGateway(),  # type: ignore[arg-type]
        binding_id="scorm-binding-generation-0",
    ).execute(
        GuiAction("left_click", {"x": 25, "y": 30}),
        source_observation=observation,
    )

    assert result.ok is True
    assert result.code == "gateway_executed_handoff_required"
    assert result.dispatch_state == "dispatched"


def test_executor_marks_post_action_capture_failure_as_dispatched() -> None:
    class CaptureFailureGateway:
        def execute(self, action, _params, **_kwargs):
            return DesktopActionResult(
                ok=False,
                action=action,
                action_id="00000000-0000-0000-0000-000000000001",
                dry_run=False,
                reason="post_action_capture_failed",
            )

    observation = ScreenObservation(
        observation_id="1" * 64,
        sequence=1,
        captured_at_unix=1.0,
        screenshot_sha256="2" * 64,
        width=640,
        height=480,
        ocr_tokens=(),
    )

    result = GovernedGatewayExecutor(
        CaptureFailureGateway(),  # type: ignore[arg-type]
        binding_id="scorm-binding-generation-0",
    ).execute(
        GuiAction("left_click", {"x": 25, "y": 30}),
        source_observation=observation,
    )

    assert result.ok is False
    assert result.code == "gateway_post_action_capture_failed"
    assert result.dispatch_state == "dispatched"
    assert result.details["gateway_action_id"] == (
        "00000000-0000-0000-0000-000000000001"
    )
