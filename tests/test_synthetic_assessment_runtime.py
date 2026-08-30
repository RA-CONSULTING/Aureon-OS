from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from aureon.autonomous.aureon_governed_desktop_gateway import WindowBinding
from aureon.operator.local_gui_observer import OCRToken, ScreenObservation, WindowRect
from aureon.operator.local_gui_runtime import GuiAction
from aureon.operator.synthetic_assessment_grant import GrantReplayError
from aureon.operator.synthetic_assessment_runtime import (
    SyntheticAssessmentRuntimeConfig,
    SyntheticAssessmentRuntimeController,
)

SECRET = b"courseops-owner-runtime-key-32-bytes-minimum"
TITLE = "Aureon CourseOps 21"


class _Sink:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []

    def append(self, event_type: str, payload: dict[str, object]) -> None:
        self.events.append((event_type, dict(payload)))


def _asset_root(tmp_path: Path) -> Path:
    root = tmp_path / "suite"
    root.mkdir()
    (root / "index.html").write_text("synthetic suite", encoding="utf-8")
    return root


def _binding() -> WindowBinding:
    return WindowBinding(
        binding_id="courseops-binding",
        expected_title=TITLE,
        handle=1234,
        process_id=4321,
        created_at=datetime(2026, 8, 16, 16, 0, tzinfo=UTC),
        epoch=1,
    )


def _observation(*, handle: int = 1234, process_id: int = 4321) -> ScreenObservation:
    return ScreenObservation(
        observation_id=hashlib.sha256(b"assessment-observation").hexdigest(),
        sequence=2,
        captured_at_unix=1.0,
        screenshot_sha256=hashlib.sha256(b"assessment-frame").hexdigest(),
        width=1280,
        height=720,
        ocr_tokens=(
            OCRToken(
                "Synthetic certification assessment knowledge check",
                20,
                20,
                500,
                30,
            ),
        ),
        cursor_x=40,
        cursor_y=50,
        window_handle=handle,
        window_process_id=process_id,
        window_title_sha256=hashlib.sha256(TITLE.encode()).hexdigest(),
        window_rect=WindowRect(0, 0, 1280, 720),
    )


def _config(root: Path, replay: Path) -> SyntheticAssessmentRuntimeConfig:
    return SyntheticAssessmentRuntimeConfig(
        asset_root=root,
        loopback_port=8765,
        server_pid=2222,
        run_id="courseops-test-run",
        nonce="courseops-test-nonce-0001",
        ttl_seconds=3600,
        allowed_actions=("left_click", "move_mouse", "scroll"),
        replay_directory=replay,
        max_actions=20,
    )


def test_controller_activates_once_and_authorizes_a_strict_action_sequence(
    tmp_path: Path,
) -> None:
    now = [datetime(2026, 8, 16, 16, 0, tzinfo=UTC)]
    sink = _Sink()
    controller = SyntheticAssessmentRuntimeController(
        _config(_asset_root(tmp_path), tmp_path / "replay"),
        secret=SECRET,
        receipt_sink=sink,
        utc_now=lambda: now[0],
    )

    grant_sha256 = controller.activate(_binding())
    observation = _observation()

    assert len(grant_sha256) == 64
    assert controller.active is True
    assert controller.authorize_observation(observation) is True
    assert controller.authorize_gate(observation, "certification_assessment") is True
    assert controller.authorize_gate(observation, "mfa") is False

    first = controller.authorize_action(
        observation,
        GuiAction("move_mouse", {"x": 100, "y": 100}),
    )
    second = controller.authorize_action(
        observation,
        GuiAction("left_click", {"x": 100, "y": 100}),
    )
    assert first is not None and first.action_sequence == 1
    assert second is not None and second.action_sequence == 2
    assert first.receipt_sha256 != second.receipt_sha256
    assert [event for event, _payload in sink.events] == [
        "synthetic_assessment_grant_activated",
        "synthetic_assessment_action_authorized",
        "synthetic_assessment_action_authorized",
    ]
    assert SECRET.decode() not in repr(sink.events)


def test_controller_rechecks_window_assets_time_and_cross_process_replay(tmp_path: Path) -> None:
    now = [datetime(2026, 8, 16, 16, 0, tzinfo=UTC)]
    root = _asset_root(tmp_path)
    config = _config(root, tmp_path / "replay")
    controller = SyntheticAssessmentRuntimeController(
        config,
        secret=SECRET,
        utc_now=lambda: now[0],
    )
    controller.activate(_binding())

    assert controller.authorize_observation(_observation(handle=9999)) is False
    assert controller.authorize_observation(_observation(process_id=9999)) is False

    (root / "index.html").write_text("drifted suite", encoding="utf-8")
    assert controller.authorize_observation(_observation()) is False
    assert controller.authorize_action(
        _observation(),
        GuiAction("left_click", {"x": 1, "y": 1}),
    ) is None

    with pytest.raises(GrantReplayError):
        SyntheticAssessmentRuntimeController(
            config,
            secret=SECRET,
            utc_now=lambda: now[0] + timedelta(seconds=1),
        ).activate(_binding())


def test_controller_fails_closed_after_expiry_and_on_out_of_scope_action(tmp_path: Path) -> None:
    now = [datetime(2026, 8, 16, 16, 0, tzinfo=UTC)]
    config = _config(_asset_root(tmp_path), tmp_path / "replay")
    controller = SyntheticAssessmentRuntimeController(
        config,
        secret=SECRET,
        utc_now=lambda: now[0],
    )
    controller.activate(_binding())

    assert controller.authorize_action(
        _observation(),
        GuiAction("press_key", {"key": "enter"}),
    ) is None
    now[0] += timedelta(hours=2)
    assert controller.authorize_observation(_observation()) is False
    assert controller.authorize_action(
        _observation(),
        GuiAction("left_click", {"x": 10, "y": 10}),
    ) is None
