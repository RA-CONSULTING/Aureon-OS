from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from typing import Sequence

import pytest

from aureon.operator.local_gui_observer import (
    CapturedScreen,
    FrameArtifactReference,
    GatewayObservationRejectedError,
    LocalGUIObserver,
    OCRToken,
    ScreenObservation,
    WindowRect,
)
from aureon.operator.local_gui_runtime import (
    ActionResult,
    ActionValidationError,
    GuiAction,
    LocalGUIRuntime,
    ObservationPredicate,
    PlannerDecision,
    RuntimeLimits,
    RuntimeTransition,
)


def _observation(label: str, sequence: int, text: str = "", vision: str = "") -> ScreenObservation:
    digest = hashlib.sha256(label.encode("utf-8")).hexdigest()
    tokens = (OCRToken(text=text, x=1, y=1, width=80, height=10),) if text else ()
    return ScreenObservation(
        observation_id=hashlib.sha256(f"{label}:{sequence}".encode()).hexdigest(),
        sequence=sequence,
        captured_at_unix=float(sequence),
        screenshot_sha256=digest,
        width=800,
        height=600,
        ocr_tokens=tokens,
        vision_text=vision,
    )


class FakeObserver:
    def __init__(
        self,
        observations: Sequence[ScreenObservation],
        *,
        provide_stable_pairs: bool = True,
    ):
        if provide_stable_pairs:
            expanded: list[ScreenObservation] = []
            for observation in observations:
                first_sequence = observation.sequence * 2 - 1
                second_sequence = observation.sequence * 2
                expanded.extend(
                    [
                        replace(
                            observation,
                            observation_id=hashlib.sha256(
                                f"{observation.observation_id}:settle:1".encode()
                            ).hexdigest(),
                            sequence=first_sequence,
                            captured_at_unix=float(first_sequence),
                        ),
                        replace(
                            observation,
                            observation_id=hashlib.sha256(
                                f"{observation.observation_id}:settle:2".encode()
                            ).hexdigest(),
                            sequence=second_sequence,
                            captured_at_unix=float(second_sequence),
                        ),
                    ]
                )
            self.observations = expanded
        else:
            self.observations = list(observations)
        self.calls = 0

    def observe(self) -> ScreenObservation:
        self.calls += 1
        if not self.observations:
            raise AssertionError("unexpected observation request")
        return self.observations.pop(0)


class ScriptedObserver:
    def __init__(self, events: Sequence[ScreenObservation | BaseException]):
        self.events = list(events)
        self.calls = 0

    def observe(self) -> ScreenObservation:
        self.calls += 1
        if not self.events:
            raise AssertionError("unexpected observation request")
        event = self.events.pop(0)
        if isinstance(event, BaseException):
            raise event
        return event


class FakePlanner:
    locality = "local"

    def __init__(self, decisions: Sequence[PlannerDecision]):
        self.decisions = list(decisions)
        self.calls: list[tuple[str, str, int]] = []

    def plan(
        self,
        goal: str,
        observation: ScreenObservation,
        history: Sequence[RuntimeTransition],
    ) -> PlannerDecision:
        self.calls.append((goal, observation.screenshot_sha256, len(history)))
        if not self.decisions:
            raise AssertionError("unexpected planner request")
        return self.decisions.pop(0)


class FakeExecutor:
    def __init__(self, results: Sequence[ActionResult] | None = None):
        self.results = list(results or [ActionResult(True, "executed")])
        self.actions: list[GuiAction] = []
        self.source_observations: list[ScreenObservation | None] = []

    def execute(
        self,
        action: GuiAction,
        *,
        source_observation: ScreenObservation | None = None,
    ) -> ActionResult:
        self.actions.append(action)
        self.source_observations.append(source_observation)
        if not self.results:
            raise AssertionError("unexpected executor request")
        return self.results.pop(0)


class CapturingSink:
    def __init__(self):
        self.records: list[dict[str, object]] = []

    def record_transition(self, record):
        self.records.append(dict(record))
        return record


def _click_then_complete() -> list[PlannerDecision]:
    return [
        PlannerDecision(
            kind="action",
            reason="Select the only course tile",
            action=GuiAction("left_click", {"x": 120, "y": 80}),
            expected=ObservationPredicate("ocr_contains", "Course complete"),
        ),
        PlannerDecision(
            kind="complete",
            reason="The provider completion text is visible",
            success_predicate=ObservationPredicate("ocr_contains", "Course complete"),
        ),
    ]


def test_runtime_observes_plans_one_action_observes_again_and_verifies_completion():
    before = _observation("course-list", 1, "Course list")
    after = _observation("completed", 2, "Course complete")
    observer = FakeObserver([before, after])
    planner = FakePlanner(_click_then_complete())
    executor = FakeExecutor()
    sink = CapturingSink()

    result = LocalGUIRuntime(observer, planner, executor, event_sink=sink).run(
        "Complete the authorized sandbox course"
    )

    assert result.status == "completed"
    assert result.success is True
    assert result.action_count == 1
    assert result.verified_changed_transitions == 1
    assert observer.calls == 4
    assert len(executor.actions) == 1
    assert executor.source_observations == [result.transitions[0].before]
    assert result.transitions[0].before.sequence == 2
    assert [call[2] for call in planner.calls] == [0, 1]
    assert sink.records[0]["before_sha256"] == before.screenshot_sha256
    assert sink.records[0]["after_sha256"] == after.screenshot_sha256
    assert sink.records[0]["verified"] is True


def test_transition_receipt_binds_exact_source_cursor_window_and_artifact_metadata():
    before_base = _observation("course-list", 1, "Course list")
    after_base = _observation("completed", 2, "Course complete")

    def with_metadata(
        observation: ScreenObservation,
        *,
        cursor: tuple[int, int],
        handle: int,
    ) -> ScreenObservation:
        artifact = FrameArtifactReference(
            sha256=observation.screenshot_sha256,
            byte_length=128,
            width=observation.width,
            height=observation.height,
            mime_type="image/png",
            png_relative_path=(
                f"screenreel_frames/sha256/{observation.screenshot_sha256[:2]}/"
                f"{observation.screenshot_sha256}.png"
            ),
            metadata_relative_path=(
                f"screenreel_frames/sha256/{observation.screenshot_sha256[:2]}/"
                f"{observation.screenshot_sha256}.json"
            ),
            metadata_sha256=hashlib.sha256(
                f"metadata:{observation.screenshot_sha256}".encode()
            ).hexdigest(),
        )
        return replace(
            observation,
            cursor_x=cursor[0],
            cursor_y=cursor[1],
            window_handle=handle,
            window_process_id=4242,
            window_title_sha256=hashlib.sha256(b"Synthetic Course Window").hexdigest(),
            window_rect=WindowRect(left=0, top=0, width=800, height=600),
            dpi_x=96.0,
            dpi_y=96.0,
            frame_artifact=artifact,
        )

    observer = FakeObserver(
        [
            with_metadata(before_base, cursor=(20, 30), handle=101),
            with_metadata(after_base, cursor=(120, 80), handle=202),
        ]
    )
    executor = FakeExecutor()
    sink = CapturingSink()

    result = LocalGUIRuntime(
        observer,
        FakePlanner(_click_then_complete()),
        executor,
        event_sink=sink,
        sleeper=lambda _seconds: None,
    ).run("ScreenReel receipt test")

    transition = result.transitions[0]
    record = sink.records[0]
    assert executor.source_observations[0] is transition.before
    assert record["action_source_observation_id"] == transition.before.observation_id
    assert record["action_source_sha256"] == transition.before.screenshot_sha256
    assert record["before_frame"]["cursor"] == {"x": 20, "y": 30}
    assert record["before_frame"]["window"]["handle"] == 101
    assert record["after_frame"]["window"]["handle"] == 202
    assert record["before_frame"]["frame_artifact"]["sha256"] == before_base.screenshot_sha256
    assert record["settling"] == {
        "required_consecutive_equal_hashes": 2,
        "before_attempts": 2,
        "after_attempts": 2,
        "after_stable": True,
    }
    serialized = str(record)
    assert "Synthetic Course Window" not in serialized
    assert "image_bytes" not in serialized


def test_initial_frame_must_settle_to_two_consecutive_equal_hashes():
    observations = [
        _observation("changing-a", 1, "Loading"),
        _observation("changing-b", 2, "Loading"),
        _observation("changing-c", 3, "Loading"),
    ]
    planner = FakePlanner([])
    executor = FakeExecutor()

    result = LocalGUIRuntime(
        FakeObserver(observations, provide_stable_pairs=False),
        planner,
        executor,
        limits=RuntimeLimits(
            stable_frame_max_attempts=3,
            stable_frame_interval_seconds=0,
        ),
        sleeper=lambda _seconds: None,
    ).run("unstable initial frame test")

    assert result.status == "unstable_initial_frame"
    assert result.action_count == 0
    assert planner.calls == []
    assert executor.actions == []
    assert result.final_observation == observations[-1]


def test_pointer_motion_does_not_make_identical_pixels_unstable() -> None:
    base = _observation("same-pixels", 1, "Question 1 of 10")
    first = replace(base, cursor_x=400, cursor_y=300)
    second = replace(
        base,
        observation_id=hashlib.sha256(b"same-pixels:pointer-moved").hexdigest(),
        sequence=2,
        captured_at_unix=2.0,
        cursor_x=427,
        cursor_y=318,
    )
    observer = FakeObserver([first, second], provide_stable_pairs=False)
    planner = FakePlanner([PlannerDecision(kind="abort", reason="test terminal")])

    result = LocalGUIRuntime(
        observer,
        planner,
        FakeExecutor(),
        limits=RuntimeLimits(stable_frame_max_attempts=2),
    ).run("settle an unchanged still despite independent pointer motion")

    assert result.status == "aborted"
    assert observer.calls == 2
    assert result.final_observation is not None
    assert result.final_observation.cursor_x == 427
    assert result.final_observation.cursor_y == 318
    assert result.action_count == 0
    assert len(planner.calls) == 1


def test_post_action_unstable_frames_fail_closed_and_retain_transition_receipt():
    stable_first = _observation("stable-source", 1, "Course")
    stable_second = _observation("stable-source", 2, "Course")
    unstable = [
        _observation("transition-a", 3, "Loading"),
        _observation("transition-b", 4, "Loading"),
        _observation("transition-c", 5, "Loading"),
    ]
    sink = CapturingSink()
    executor = FakeExecutor()
    decision = PlannerDecision(
        kind="action",
        reason="Advance once",
        action=GuiAction("left_click", {"x": 10, "y": 10}),
        expected=ObservationPredicate("screen_changed"),
    )

    result = LocalGUIRuntime(
        FakeObserver(
            [stable_first, stable_second, *unstable],
            provide_stable_pairs=False,
        ),
        FakePlanner([decision]),
        executor,
        event_sink=sink,
        limits=RuntimeLimits(
            stable_frame_max_attempts=3,
            stable_frame_interval_seconds=0,
        ),
        sleeper=lambda _seconds: None,
    ).run("unstable post-action frame test")

    assert result.status == "unstable_post_action_frame"
    assert result.action_count == 1
    assert len(result.transitions) == 1
    assert executor.source_observations == [stable_second]
    assert result.transitions[0].verified is False
    assert result.transitions[0].verification_reason == "stable_frame_not_reached"
    assert sink.records[0]["settling"]["after_stable"] is False
    assert sink.records[0]["settling"]["after_attempts"] == 3


def test_post_action_observer_error_retains_in_flight_transition_receipt():
    stable_first = _observation("stable-source", 1, "Course")
    stable_second = _observation("stable-source", 2, "Course")
    sink = CapturingSink()
    executor = FakeExecutor(
        [
            ActionResult(
                True,
                "gateway_executed",
                dispatch_state="dispatched",
            )
        ]
    )
    decision = PlannerDecision(
        kind="action",
        reason="Advance once",
        action=GuiAction("left_click", {"x": 10, "y": 10}),
        expected=ObservationPredicate("screen_changed"),
    )

    result = LocalGUIRuntime(
        ScriptedObserver(
            [
                stable_first,
                stable_second,
                RuntimeError("hermetic post-action capture failure"),
            ]
        ),
        FakePlanner([decision]),
        executor,
        event_sink=sink,
        limits=RuntimeLimits(stable_frame_interval_seconds=0),
        sleeper=lambda _seconds: None,
    ).run("post-action observer failure test")

    assert result.status == "observer_error"
    assert result.action_count == 1
    assert len(executor.actions) == 1
    assert len(result.transitions) == 1
    assert result.transitions[0].verification_reason == "post_action_observer_failed"
    assert result.transitions[0].to_dict()["in_flight"] is True
    assert sink.records[0]["in_flight"] is True
    assert sink.records[0]["result"]["dispatch_state"] == "dispatched"


def test_stable_sampler_uses_injected_sleeper_between_bounded_attempts():
    first = _observation("loading", 1, "Loading")
    second = _observation("ready", 2, "Ready")
    third = _observation("ready", 3, "Ready")
    sleeps: list[float] = []
    planner = FakePlanner(
        [
            PlannerDecision(
                kind="human_required",
                reason="Stop after proving the stable sampler",
                human_gate="other",
            )
        ]
    )

    result = LocalGUIRuntime(
        FakeObserver([first, second, third], provide_stable_pairs=False),
        planner,
        FakeExecutor(),
        limits=RuntimeLimits(
            stable_frame_max_attempts=3,
            stable_frame_interval_seconds=0.25,
        ),
        sleeper=sleeps.append,
    ).run("stable sampler sleeper test")

    assert result.status == "human_required"
    assert sleeps == [0.25, 0.25]


def test_transient_target_mismatch_resets_post_action_settling_pair():
    initial_first = _observation("initial", 1, "Course")
    initial_second = _observation("initial", 2, "Course")
    post_first = _observation("post-action", 3, "Course")
    post_second = _observation("post-action", 4, "Course")
    post_third = _observation("post-action", 5, "Course")
    observer = ScriptedObserver(
        [
            initial_first,
            initial_second,
            post_first,
            GatewayObservationRejectedError("target_window_mismatch"),
            post_second,
            post_third,
        ]
    )
    planner = FakePlanner(
        [
            PlannerDecision(
                kind="action",
                reason="exercise post-action settling",
                action=GuiAction("left_click", {"x": 120, "y": 80}),
                expected=ObservationPredicate("screen_changed"),
            ),
            PlannerDecision(
                kind="human_required",
                reason="test stop",
                human_gate="other",
            ),
        ]
    )

    result = LocalGUIRuntime(
        observer,
        planner,
        FakeExecutor(),
        limits=RuntimeLimits(
            stable_frame_max_attempts=6,
            stable_frame_interval_seconds=0,
        ),
        sleeper=lambda _seconds: None,
    ).run("bounded transient foreground loss")

    assert result.status == "human_required"
    assert observer.calls == 6
    assert len(result.transitions) == 1
    assert result.transitions[0].verified is True
    assert result.transitions[0].after == post_third
    assert result.transitions[0].after_stable_attempts == 4


@pytest.mark.parametrize(
    ("events", "expected_calls", "expected_reason"),
    [
        (
            [GatewayObservationRejectedError("foreground_window_unavailable")],
            1,
            "foreground_window_unavailable",
        ),
        (
            [GatewayObservationRejectedError("target_window_mismatch") for _ in range(3)],
            3,
            "target_window_mismatch",
        ),
    ],
)
def test_other_or_persistent_gateway_observation_rejections_fail_closed(
    events,
    expected_calls,
    expected_reason,
):
    observer = ScriptedObserver(events)
    planner = FakePlanner([])

    result = LocalGUIRuntime(
        observer,
        planner,
        FakeExecutor(),
        limits=RuntimeLimits(
            stable_frame_max_attempts=3,
            stable_frame_interval_seconds=0,
        ),
        sleeper=lambda _seconds: None,
    ).run("fail closed on gateway observation rejection")

    assert result.status == "observer_error"
    assert observer.calls == expected_calls
    assert expected_reason in result.reason
    assert planner.calls == []


def test_action_schema_has_no_default_coordinates_and_rejects_extra_fields():
    with pytest.raises(ActionValidationError, match="missing_action_params:y"):
        GuiAction("left_click", {"x": 10})
    with pytest.raises(ActionValidationError, match="unexpected_action_params"):
        GuiAction("left_click", {"x": 10, "y": 20, "guess": True})
    with pytest.raises(ActionValidationError, match="action_not_allowlisted"):
        GuiAction("open_url", {"url": "https://example.invalid"})


def test_action_schema_matches_governed_gateway_numeric_and_key_bounds():
    GuiAction("move_mouse", {"x": 10, "y": 20, "duration": 2.0})
    GuiAction(
        "type_text",
        {"text": "bounded", "text_class": "ordinary", "interval": 0.5},
    )
    for key in ("a", "9", "return", "esc", "control", "capslock", "f24"):
        GuiAction("press_key", {"key": key})

    with pytest.raises(ActionValidationError, match="duration_out_of_range"):
        GuiAction("move_mouse", {"x": 10, "y": 20, "duration": 2.01})
    with pytest.raises(ActionValidationError, match="interval_out_of_range"):
        GuiAction(
            "type_text",
            {"text": "bounded", "text_class": "ordinary", "interval": 0.51},
        )
    for key in ("!", "é", "f25"):
        with pytest.raises(ActionValidationError, match="invalid_key"):
            GuiAction("press_key", {"key": key})


@pytest.mark.parametrize("max_seconds", [float("nan"), float("inf"), float("-inf")])
def test_runtime_limits_require_finite_max_seconds(max_seconds: float):
    with pytest.raises(ValueError, match="positive and finite"):
        RuntimeLimits(max_seconds=max_seconds)


@pytest.mark.parametrize("attempts", [0, 1, 101, True])
def test_runtime_limits_bound_stable_frame_attempts(attempts):
    with pytest.raises(ValueError, match="stable_frame_max_attempts"):
        RuntimeLimits(stable_frame_max_attempts=attempts)


def test_runtime_rejects_coordinates_outside_fresh_observation_without_execution():
    observer = FakeObserver([_observation("screen", 1, "Course")])
    planner = FakePlanner(
        [
            PlannerDecision(
                kind="action",
                reason="Bad coordinate must fail closed",
                action=GuiAction("left_click", {"x": 801, "y": 20}),
                expected=ObservationPredicate("screen_changed"),
            )
        ]
    )
    executor = FakeExecutor()

    result = LocalGUIRuntime(observer, planner, executor).run("bounded test")

    assert result.status == "invalid_action"
    assert result.action_count == 0
    assert executor.actions == []


def test_runtime_rejects_planner_that_is_not_explicitly_local():
    planner = FakePlanner([])
    planner.locality = "remote"
    with pytest.raises(ValueError, match="locality='local'"):
        LocalGUIRuntime(FakeObserver([]), planner, FakeExecutor())


@pytest.mark.parametrize(
    ("screen_text", "expected_gate"),
    [
        ("Complete the CAPTCHA to continue", "captcha"),
        ("Enter the verification code from your authenticator", "mfa"),
        ("I certify that I am the named employee", "identity_attestation"),
        ("Certification quiz: choose the correct assessment answer", "certification_assessment"),
    ],
)
def test_detected_human_only_gates_are_terminal_without_planning_or_action(
    screen_text: str,
    expected_gate: str,
):
    planner = FakePlanner([])
    executor = FakeExecutor()
    result = LocalGUIRuntime(
        FakeObserver([_observation(expected_gate, 1, screen_text)]),
        planner,
        executor,
    ).run("course benchmark")

    assert result.status == "human_required"
    assert result.human_gate == expected_gate
    assert result.success is False
    assert planner.calls == []
    assert executor.actions == []


def test_runtime_bypasses_only_a_separately_authorized_synthetic_assessment_gate():
    planner = FakePlanner([PlannerDecision(kind="abort", reason="authorization path reached")])
    calls: list[str] = []

    def authorize(_observation: ScreenObservation, gate: str) -> bool:
        calls.append(gate)
        return True

    result = LocalGUIRuntime(
        FakeObserver(
            [
                _observation(
                    "synthetic-assessment",
                    1,
                    "Synthetic certification assessment knowledge check",
                )
            ]
        ),
        planner,
        FakeExecutor(),
        human_gate_authorizer=authorize,
    ).run("sealed local assessment")

    assert result.status == "aborted"
    assert calls == ["certification_assessment"]
    assert len(planner.calls) == 1

    mfa_planner = FakePlanner([])
    mfa = LocalGUIRuntime(
        FakeObserver([_observation("mfa", 1, "Enter the verification code")]),
        mfa_planner,
        FakeExecutor(),
        human_gate_authorizer=lambda _observation, _gate: True,
    ).run("sealed local assessment")
    assert mfa.status == "human_required"
    assert mfa.human_gate == "mfa"
    assert mfa_planner.calls == []


def test_planner_can_explicitly_stop_for_identity_attestation():
    planner = FakePlanner(
        [
            PlannerDecision(
                kind="human_required",
                reason="A human must make this attestation",
                human_gate="identity_attestation",
            )
        ]
    )
    result = LocalGUIRuntime(
        FakeObserver([_observation("attestation-page", 1, "Please continue")]),
        planner,
        FakeExecutor(),
    ).run("course benchmark")
    assert result.status == "human_required"
    assert result.human_gate == "identity_attestation"


def test_unchanged_screen_hits_bounded_stall_detector():
    observations = [_observation("same", i, "Waiting") for i in range(1, 4)]
    action = GuiAction("move_mouse", {"x": 20, "y": 30})
    decisions = [
        PlannerDecision(
            kind="action",
            reason="Inspect the hover state",
            action=action,
            expected=ObservationPredicate("observation_fresh"),
        ),
        PlannerDecision(
            kind="action",
            reason="Inspect the hover state once more",
            action=action,
            expected=ObservationPredicate("observation_fresh"),
        ),
    ]
    result = LocalGUIRuntime(
        FakeObserver(observations),
        FakePlanner(decisions),
        FakeExecutor([ActionResult(True, "moved"), ActionResult(True, "moved")]),
        limits=RuntimeLimits(max_consecutive_unchanged=2),
    ).run("bounded stall test")

    assert result.status == "stalled"
    assert result.action_count == 2
    assert result.verified_changed_transitions == 0


def test_post_dispatch_capture_failure_is_never_redispatched():
    observations = [_observation("same", i, "Course") for i in range(1, 3)]
    action = GuiAction("left_click", {"x": 10, "y": 10})
    decisions = [
        PlannerDecision(
            kind="action",
            reason="Try the visible control",
            action=action,
            expected=ObservationPredicate("observation_fresh"),
        ),
        PlannerDecision(
            kind="action",
            reason="Retry the same visible control once",
            action=action,
            expected=ObservationPredicate("observation_fresh"),
        ),
    ]
    executor = FakeExecutor(
        [
            ActionResult(
                False,
                "gateway_post_action_capture_failed",
                {"gateway_action_id": "00000000-0000-0000-0000-000000000001"},
                dispatch_state="dispatched",
            ),
            ActionResult(
                False,
                "gateway_post_action_capture_failed",
                {"gateway_action_id": "00000000-0000-0000-0000-000000000002"},
                dispatch_state="dispatched",
            ),
        ]
    )
    planner = FakePlanner(decisions)
    result = LocalGUIRuntime(
        FakeObserver(observations),
        planner,
        executor,
        limits=RuntimeLimits(max_retries_per_action=5, max_consecutive_unchanged=10),
    ).run("post-dispatch capture failure test")

    assert result.status == "post_dispatch_verification_failed"
    assert result.action_count == 1
    assert len(executor.actions) == 1
    assert len(planner.calls) == 1
    assert len(result.transitions) == 1
    assert result.transitions[0].result.code == "gateway_post_action_capture_failed"
    assert result.transitions[0].to_dict()["in_flight"] is True


def test_proven_stale_source_failure_may_replan_same_action_once():
    before = _observation("before", 1, "Course")
    refreshed = _observation("refreshed", 2, "Course")
    completed = _observation("completed", 3, "Course complete")
    action = GuiAction("left_click", {"x": 10, "y": 10})
    planner = FakePlanner(
        [
            PlannerDecision(
                kind="action",
                reason="Use the visible control",
                action=action,
                expected=ObservationPredicate("screen_changed"),
            ),
            PlannerDecision(
                kind="action",
                reason="Replan against the refreshed source frame",
                action=action,
                expected=ObservationPredicate("ocr_contains", "Course complete"),
            ),
            PlannerDecision(
                kind="complete",
                reason="Completion is visible",
                success_predicate=ObservationPredicate(
                    "ocr_contains",
                    "Course complete",
                ),
            ),
        ]
    )
    executor = FakeExecutor(
        [
            ActionResult(
                False,
                "gateway_stale_source_frame",
                dispatch_state="not_dispatched",
            ),
            ActionResult(
                True,
                "gateway_executed",
                dispatch_state="dispatched",
            ),
        ]
    )

    result = LocalGUIRuntime(
        FakeObserver([before, refreshed, completed]),
        planner,
        executor,
        limits=RuntimeLimits(max_retries_per_action=1),
    ).run("stale-source replan test")

    assert result.status == "completed"
    assert result.action_count == 2
    assert len(executor.actions) == 2
    assert executor.actions == [action, action]
    assert executor.source_observations[0] != executor.source_observations[1]
    assert result.transitions[0].to_dict()["in_flight"] is False
    assert result.transitions[1].verified is True


@pytest.mark.parametrize(
    ("executor_code", "expected_status", "expected_gate"),
    [
        (
            "human_required_certification_assessment",
            "human_required",
            "certification_assessment",
        ),
        (
            "gateway_active_authorization_lease_required",
            "human_required",
            "authorization",
        ),
        (
            "gateway_action_outside_lease_scope",
            "human_required",
            "authorization",
        ),
        ("gateway_emergency_stop_active", "emergency_stopped", ""),
    ],
)
def test_governed_executor_terminal_codes_do_not_enter_retry_loops(
    executor_code: str,
    expected_status: str,
    expected_gate: str,
):
    action = GuiAction("left_click", {"x": 10, "y": 10})
    planner = FakePlanner(
        [
            PlannerDecision(
                kind="action",
                reason="Attempt the visible control once",
                action=action,
                expected=ObservationPredicate("screen_changed"),
            ),
            PlannerDecision(
                kind="action",
                reason="This retry must never be requested",
                action=action,
                expected=ObservationPredicate("screen_changed"),
            ),
        ]
    )
    executor = FakeExecutor([ActionResult(False, executor_code)])

    result = LocalGUIRuntime(
        FakeObserver(
            [
                _observation("before", 1, "Course page"),
                _observation("after", 2, "Course page changed"),
            ]
        ),
        planner,
        executor,
        limits=RuntimeLimits(max_retries_per_action=5),
    ).run("course benchmark")

    assert result.status == expected_status
    assert result.human_gate == expected_gate
    assert result.action_count == 1
    assert len(planner.calls) == 1
    assert len(executor.actions) == 1


def test_completion_is_rejected_without_verified_changed_state_evidence():
    result = LocalGUIRuntime(
        FakeObserver([_observation("already-complete", 1, "Course complete")]),
        FakePlanner(
            [
                PlannerDecision(
                    kind="complete",
                    reason="Completion text is visible",
                    success_predicate=ObservationPredicate("ocr_contains", "Course complete"),
                )
            ]
        ),
        FakeExecutor(),
    ).run("course benchmark")

    assert result.status == "completion_rejected"
    assert result.success is False
    assert "changed-state" in result.reason


def test_emergency_stop_terminates_before_observation_or_action():
    runtime = LocalGUIRuntime(FakeObserver([]), FakePlanner([]), FakeExecutor())
    runtime.request_emergency_stop()
    result = runtime.run("course benchmark")
    assert result.status == "emergency_stopped"
    assert result.action_count == 0


def test_runtime_time_limit_is_checked_before_planning():
    clock_values = iter([0.0, 6.0])
    planner = FakePlanner([])
    result = LocalGUIRuntime(
        FakeObserver([_observation("screen", 1, "Course")]),
        planner,
        FakeExecutor(),
        limits=RuntimeLimits(max_seconds=5.0),
        monotonic=lambda: next(clock_values),
    ).run("course benchmark")
    assert result.status == "max_time"
    assert planner.calls == []


@pytest.mark.parametrize(
    "clock_values",
    [
        [0.0, 0.0, 6.0],
        [0.0, 0.0, 1.0, 6.0],
    ],
)
def test_runtime_rechecks_deadline_after_planning_and_before_dispatch(clock_values):
    planner = FakePlanner(
        [
            PlannerDecision(
                kind="action",
                reason="Attempt one bounded action",
                action=GuiAction("left_click", {"x": 10, "y": 10}),
                expected=ObservationPredicate("screen_changed"),
            )
        ]
    )
    executor = FakeExecutor()
    values = iter(clock_values)

    result = LocalGUIRuntime(
        FakeObserver([_observation("screen", 1, "Course")]),
        planner,
        executor,
        limits=RuntimeLimits(max_seconds=5.0),
        monotonic=lambda: next(values),
    ).run("course benchmark")

    assert result.status == "max_time"
    assert len(planner.calls) == 1
    assert executor.actions == []


@pytest.mark.parametrize(
    "stop_values",
    [
        [False, False, True],
        [False, False, False, True],
    ],
)
def test_runtime_rechecks_emergency_after_planning_and_before_dispatch(stop_values):
    planner = FakePlanner(
        [
            PlannerDecision(
                kind="action",
                reason="Attempt one bounded action",
                action=GuiAction("left_click", {"x": 10, "y": 10}),
                expected=ObservationPredicate("screen_changed"),
            )
        ]
    )
    executor = FakeExecutor()
    values = iter(stop_values)

    result = LocalGUIRuntime(
        FakeObserver([_observation("screen", 1, "Course")]),
        planner,
        executor,
        emergency_stop=lambda: next(values),
    ).run("course benchmark")

    assert result.status == "emergency_stopped"
    assert len(planner.calls) == 1
    assert executor.actions == []


def test_runtime_step_limit_prevents_unbounded_action_loop():
    observations = [
        _observation("step-1", 1, "Page one"),
        _observation("step-2", 2, "Page two"),
        _observation("step-3", 3, "Page three"),
    ]
    decisions = [
        PlannerDecision(
            kind="action",
            reason="Advance one page",
            action=GuiAction("left_click", {"x": 10, "y": 10}),
            expected=ObservationPredicate("screen_changed"),
        ),
        PlannerDecision(
            kind="action",
            reason="Advance one more page",
            action=GuiAction("left_click", {"x": 10, "y": 10}),
            expected=ObservationPredicate("screen_changed"),
        ),
    ]
    result = LocalGUIRuntime(
        FakeObserver(observations),
        FakePlanner(decisions),
        FakeExecutor([ActionResult(True, "clicked"), ActionResult(True, "clicked")]),
        limits=RuntimeLimits(max_steps=2),
    ).run("bounded step test")

    assert result.status == "max_steps"
    assert result.action_count == 2
    assert result.success is False


def test_typed_assessment_answer_is_redacted_before_event_sink():
    secret_answer = "the-private-assessment-answer"
    decisions = [
        PlannerDecision(
            kind="action",
            reason="Enter the selected answer",
            action=GuiAction(
                "type_text",
                {"text": secret_answer, "text_class": "assessment_answer"},
            ),
            expected=ObservationPredicate("ocr_contains", "Answer saved"),
        ),
        PlannerDecision(
            kind="complete",
            reason="Authorized sandbox completion is visible",
            success_predicate=ObservationPredicate("ocr_contains", "Answer saved"),
        ),
    ]
    sink = CapturingSink()
    result = LocalGUIRuntime(
        FakeObserver(
            [
                _observation("question", 1, "Question"),
                _observation("saved", 2, "Answer saved"),
            ]
        ),
        FakePlanner(decisions),
        FakeExecutor(),
        event_sink=sink,
    ).run("authorized sandbox assessment")

    serialized = str(sink.records)
    assert result.status == "completed"
    assert secret_answer not in serialized
    assert "[REDACTED:TYPED_TEXT]" in serialized


@dataclass
class StaticScreenshotBackend:
    frame: CapturedScreen

    def capture(self) -> CapturedScreen:
        return self.frame


class StaticOCRBackend:
    def recognize(self, frame: CapturedScreen):
        assert frame.width == 100
        return [OCRToken("Continue", 10, 10, 40, 10, 0.99)]


class StaticVisionHook:
    locality = "local"

    def describe(self, frame: CapturedScreen, tokens):
        return "A course page with one Continue button"


def test_observer_hashes_screen_and_includes_injected_ocr_boxes_and_local_vision():
    frame = CapturedScreen(b"fake-png-bytes", 100, 50)
    observer = LocalGUIObserver(
        StaticScreenshotBackend(frame),
        StaticOCRBackend(),
        vision_hook=StaticVisionHook(),
        clock=lambda: 123.0,
    )

    observed = observer.observe()

    assert observed.screenshot_sha256 == hashlib.sha256(frame.image_bytes).hexdigest()
    assert (observed.width, observed.height) == (100, 50)
    assert observed.ocr_tokens[0].to_dict()["box"] == {
        "x": 10,
        "y": 10,
        "width": 40,
        "height": 10,
    }
    assert "Continue button" in observed.vision_text


def test_observer_rejects_non_local_vision_hook():
    hook = StaticVisionHook()
    hook.locality = "cloud"
    with pytest.raises(ValueError, match="locality='local'"):
        LocalGUIObserver(
            StaticScreenshotBackend(CapturedScreen(b"frame", 10, 10)),
            StaticOCRBackend(),
            vision_hook=hook,
        )
