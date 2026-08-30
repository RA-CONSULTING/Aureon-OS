from __future__ import annotations

import ast
import hashlib
import inspect
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

import aureon.operator.courseops_21_planner as planner_module
from aureon.operator.courseops_21_planner import (
    COURSEOPS_21_COMPLETION_MARKER,
    CourseOps21Planner,
    CourseOps21PlannerError,
)
from aureon.operator.local_gui_observer import OCRToken, ScreenObservation, WindowRect
from aureon.operator.local_gui_runtime import GuiAction, ObservationPredicate, PlannerDecision


def _observation(
    lines: list[tuple[str, int, int]],
    *,
    sequence: int,
    cursor: tuple[int, int] | None = None,
    vision: str = "",
    bound_window: int | None = 7_001,
    dpi: tuple[float, float] | None = (96.0, 96.0),
) -> ScreenObservation:
    tokens: list[OCRToken] = []
    for text, x, y in lines:
        token_x = x
        for word in text.split():
            width = max(14, len(word) * 9)
            tokens.append(OCRToken(text=word, x=token_x, y=y, width=width, height=22))
            token_x += width + 7
    digest = hashlib.sha256(
        f"courseops-screen:{sequence}:{lines!r}:{cursor!r}:{bound_window!r}:{dpi!r}".encode()
    ).hexdigest()
    cursor_x, cursor_y = cursor if cursor is not None else (None, None)
    window = (
        {
            "window_handle": bound_window,
            "window_process_id": 20_800,
            "window_title_sha256": hashlib.sha256(b"courseops-test-window").hexdigest(),
            "window_rect": WindowRect(left=0, top=0, width=1600, height=1000),
        }
        if bound_window is not None
        else {}
    )
    dpi_x, dpi_y = dpi if dpi is not None else (None, None)
    return ScreenObservation(
        observation_id=hashlib.sha256(f"courseops-observation:{sequence}".encode()).hexdigest(),
        sequence=sequence,
        captured_at_unix=float(sequence),
        screenshot_sha256=digest,
        width=1600,
        height=1000,
        ocr_tokens=tuple(tokens),
        vision_text=vision,
        cursor_x=cursor_x,
        cursor_y=cursor_y,
        dpi_x=dpi_x,
        dpi_y=dpi_y,
        **window,
    )


def _token_observation(
    tokens: list[OCRToken],
    *,
    sequence: int,
    cursor: tuple[int, int] | None = None,
    bound_window: int | None = 7_001,
    vision: str = "",
    dpi: tuple[float, float] | None = (96.0, 96.0),
) -> ScreenObservation:
    digest = hashlib.sha256(
        (
            f"courseops-token-screen:{sequence}:{[token.to_dict() for token in tokens]!r}:"
            f"{cursor!r}:{bound_window!r}:{vision}:{dpi!r}"
        ).encode()
    ).hexdigest()
    cursor_x, cursor_y = cursor if cursor is not None else (None, None)
    window = (
        {
            "window_handle": bound_window,
            "window_process_id": 20_800,
            "window_title_sha256": hashlib.sha256(b"courseops-test-window").hexdigest(),
            "window_rect": WindowRect(left=10, top=10, width=825, height=982),
        }
        if bound_window is not None
        else {}
    )
    dpi_x, dpi_y = dpi if dpi is not None else (None, None)
    return ScreenObservation(
        observation_id=hashlib.sha256(f"courseops-token-observation:{sequence}".encode()).hexdigest(),
        sequence=sequence,
        captured_at_unix=float(sequence),
        screenshot_sha256=digest,
        width=1680,
        height=1050,
        ocr_tokens=tuple(tokens),
        vision_text=vision,
        cursor_x=cursor_x,
        cursor_y=cursor_y,
        dpi_x=dpi_x,
        dpi_y=dpi_y,
        **window,
    )


def _transition(
    decision: PlannerDecision,
    *,
    ok: bool = True,
    verified: bool | None = None,
    screen_changed: bool = True,
    code: str | None = None,
):
    return SimpleNamespace(
        decision=decision,
        result=SimpleNamespace(
            ok=ok,
            code=code or ("gateway_executed" if ok else "gateway_failed"),
        ),
        verified=ok if verified is None else verified,
        screen_changed=screen_changed,
    )


def _vision_text(candidates: list[dict], *, schema: str = "aureon-courseops-vision-v1") -> str:
    return json.dumps(
        {"candidates": candidates, "schema_version": schema},
        sort_keys=True,
        separators=(",", ":"),
    )


def _vision_candidate(
    *,
    label: str = "open_course",
    x: int = 601,
    y: int = 603,
    width: int = 134,
    height: int = 46,
) -> dict:
    return {
        "bounds": {"height": height, "width": width, "x": x, "y": y},
        "center": {"x": x + width // 2, "y": y + height // 2},
        "label": label,
        "source": "pixel_green+ocr",
    }


def _move_and_click(
    planner: CourseOps21Planner,
    observation: ScreenObservation,
    history: list,
) -> tuple[PlannerDecision, PlannerDecision]:
    move = planner.plan("Complete the local synthetic courses", observation, history)
    assert move.kind == "action"
    assert move.action is not None
    assert move.action.name == "move_mouse"
    assert set(move.action.params) == {"duration", "x", "y"}
    history.append(_transition(move))

    click_observation = observation
    if observation.window_handle is not None:
        click_observation = replace(
            observation,
            cursor_x=int(move.action.params["x"]),
            cursor_y=int(move.action.params["y"]),
        )
    click = planner.plan("Complete the local synthetic courses", click_observation, history)
    assert click.kind == "action"
    assert click.action is not None
    assert click.action.name == "left_click"
    assert set(click.action.params) == {"x", "y"}
    history.append(_transition(click))
    return move, click


def _planner_at_radio_assessment() -> tuple[CourseOps21Planner, list, ScreenObservation]:
    planner = CourseOps21Planner()
    lesson = _observation(
        [
            ("Read the full lesson", 100, 100),
            ("The required control is isolate the valve and report the leak", 100, 220),
        ],
        sequence=901,
    )
    lesson_scroll = planner.plan("continue", lesson, [])
    history = [_transition(lesson_scroll)]
    assessment = _observation(
        [
            ("Synthetic certification assessment", 100, 100),
            ("Which control is required?", 100, 180),
            ("A. Ignore the leak", 140, 350),
            ("B. Isolate the valve and report the leak", 140, 430),
            ("C. Increase the pressure", 140, 510),
            ("Submit synthetic answer", 420, 650),
        ],
        sequence=902,
        cursor=(313, 441),
    )
    return planner, history, assessment


def _bound_assessment_observation(
    *,
    sequence: int,
    cursor: tuple[int, int],
    bound_window: int | None = 7_001,
    include_grounded_row: bool = True,
    question: str = "Which control is required?",
    dpi: tuple[float, float] | None = (96.0, 96.0),
    grounded_row_x: int = 140,
) -> ScreenObservation:
    rows = [
        ("A. Ignore the leak", 140, 350),
        ("B. Isolate the valve and report the leak", grounded_row_x, 430),
        ("C. Increase the pressure", 140, 510),
    ]
    if not include_grounded_row:
        rows.pop(1)
    return _observation(
        [
            ("Synthetic certification assessment", 100, 100),
            (question, 100, 180),
            *rows,
            ("Submit synthetic answer", 420, 650),
        ],
        sequence=sequence,
        cursor=cursor,
        bound_window=bound_window,
        dpi=dpi,
    )


def _planner_with_bound_option_move() -> tuple[CourseOps21Planner, list, PlannerDecision]:
    planner = CourseOps21Planner()
    lesson = _observation(
        [
            ("Read the full lesson", 100, 100),
            ("The required control is isolate the valve and report the leak", 100, 220),
        ],
        sequence=950,
    )
    scroll = planner.plan("continue", lesson, [])
    history = [_transition(scroll)]
    assessment = _bound_assessment_observation(sequence=951, cursor=(40, 40))
    move = planner.plan("continue", assessment, history)
    assert move.action is not None and move.action.name == "move_mouse"
    return planner, history, move


def test_planner_navigates_every_courseops_screen_from_ocr_one_action_at_a_time() -> None:
    planner = CourseOps21Planner()
    history: list = []

    welcome = _observation(
        [
            ("Aureon CourseOps 21", 80, 30),
            ("SYNTHETIC TEST ONLY", 80, 80),
            ("Twenty-one local safety courses are ready", 120, 180),
            ("Open local course inbox", 420, 420),
        ],
        sequence=1,
    )
    welcome_move, welcome_click = _move_and_click(planner, welcome, history)
    assert welcome_move.action is not None and welcome_click.action is not None
    assert welcome_move.action.params["x"] == welcome_click.action.params["x"]
    assert welcome_move.action.params["y"] == welcome_click.action.params["y"]

    inbox = _observation(
        [
            ("John Brown synthetic assignments", 100, 130),
            ("0 of 21 complete", 1000, 130),
            ("Assigned not started", 300, 300),
            ("Open course", 1150, 300),
            ("Assigned not started", 300, 390),
            ("Open course", 1150, 390),
        ],
        sequence=2,
    )
    inbox_move, inbox_click = _move_and_click(planner, inbox, history)
    assert inbox_move.action is not None and inbox_click.action is not None
    assert inbox_click.action.params["y"] < 350

    lesson_top = _observation(
        [
            ("Read the full lesson and scroll to the end before continuing", 100, 130),
            ("Recognise the hazard", 100, 240),
            ("Apply the control", 100, 430),
            (
                "Compressed gas cylinders stay secured upright and move with an approved cylinder cart",
                100,
                490,
            ),
        ],
        sequence=3,
    )
    scroll = planner.plan("Complete the local synthetic courses", lesson_top, history)
    assert scroll.kind == "action"
    assert scroll.action is not None
    assert scroll.action.name == "scroll"
    assert scroll.action.params["clicks"] == -7
    history.append(_transition(scroll))

    lesson_end = _observation(
        [
            ("Verify before proceeding", 100, 300),
            ("Confirm the control is in place before work continues", 100, 365),
            ("END OF SYNTHETIC LESSON", 400, 620),
            ("Begin synthetic knowledge check", 390, 730),
        ],
        sequence=4,
    )
    _move_and_click(planner, lesson_end, history)

    assessment = _observation(
        [
            ("Synthetic certification assessment", 100, 130),
            ("Knowledge check", 100, 190),
            ("How should a compressed gas cylinder be stored and moved?", 100, 270),
            ("Choose the best answer from the visible lesson", 100, 330),
            ("A. Leave it loose on the floor", 160, 430),
            ("B. Keep it secured upright and use an approved cylinder cart", 160, 520),
            ("C. Roll it along the ground", 160, 610),
            ("No answer submitted", 100, 720),
            ("Submit synthetic answer", 500, 800),
        ],
        sequence=5,
    )
    option_move, option_click = _move_and_click(planner, assessment, history)
    assert option_move.action is not None and option_click.action is not None
    assert 500 <= option_click.action.params["y"] <= 550

    submit_move, submit_click = _move_and_click(planner, assessment, history)
    assert submit_move.action is not None and submit_click.action is not None
    assert submit_click.action.params["y"] > 780

    course_complete = _observation(
        [
            ("Synthetic course passed", 100, 160),
            ("The visible answer matched the lesson", 100, 240),
            ("Download synthetic test certificate", 430, 390),
            ("Certificate not yet downloaded", 420, 480),
            ("Return to course inbox", 450, 570),
        ],
        sequence=6,
    )
    download_move, download_click = _move_and_click(planner, course_complete, history)
    assert download_move.action is not None and download_click.action is not None
    assert download_click.action.params["y"] < 450

    downloaded = _observation(
        [
            ("Synthetic course passed", 100, 160),
            ("Download synthetic test certificate", 430, 390),
            ("SYNTHETIC TEST ONLY certificate generated for this course", 260, 480),
            ("Return to course inbox", 450, 570),
        ],
        sequence=7,
    )
    return_move, return_click = _move_and_click(planner, downloaded, history)
    assert return_move.action is not None and return_click.action is not None
    assert return_click.action.params["y"] > 540

    final = _observation(
        [
            ("Synthetic benchmark complete", 100, 200),
            (COURSEOPS_21_COMPLETION_MARKER, 260, 320),
            ("Twenty-one watermarked synthetic test certificates were generated locally", 100, 430),
        ],
        sequence=8,
    )
    complete = planner.plan("Complete the local synthetic courses", final, history)
    assert complete.kind == "complete"
    assert complete.action is None
    assert complete.success_predicate is not None
    assert complete.success_predicate.kind == "ocr_contains"
    assert complete.success_predicate.value == COURSEOPS_21_COMPLETION_MARKER


def test_inbox_control_targets_only_open_course_token_span_on_a_mixed_ocr_row() -> None:
    planner = CourseOps21Planner()
    history: list = []
    inbox = _observation(
        [
            ("John Brown synthetic assignments", 100, 120),
            ("LOCAL-MODULE-07", 80, 300),
            ("Assigned not started", 260, 300),
            ("Open course", 620, 300),
        ],
        sequence=1,
    )

    move, click = _move_and_click(planner, inbox, history)

    assert move.action is not None and click.action is not None
    # "Open" spans x=620..656 and "course" spans x=663..717.  The
    # target must be their local centre, not the centre of the whole OCR row.
    assert move.action.params["x"] == 668
    assert move.action.params["y"] == 311
    assert click.action.params["x"] == 668
    assert click.action.params["y"] == 311


@pytest.mark.parametrize("label", ["open_course", "unknown_green_control"])
def test_inbox_uses_bounded_pixel_candidate_when_green_button_ocr_is_missing(label: str) -> None:
    vision = _vision_text([_vision_candidate(label=label)])
    assert vision == (
        '{"candidates":[{"bounds":{"height":46,"width":134,"x":601,"y":603},'
        '"center":{"x":668,"y":626},"label":"'
        f"{label}"
        '","source":"pixel_green+ocr"}],"schema_version":"aureon-courseops-vision-v1"}'
    )
    inbox = _observation(
        [
            ("John Brown synthetic assignments", 100, 120),
            ("LOCAL-MODULE-07", 80, 603),
            ("Assigned not started", 260, 603),
        ],
        sequence=1,
        vision=vision,
    )
    planner = CourseOps21Planner()
    history: list = []

    move, click = _move_and_click(planner, inbox, history)

    assert move.action is not None and click.action is not None
    assert move.action.params["x"] == 668
    assert move.action.params["y"] == 626
    assert click.action.params["x"] == 668
    assert click.action.params["y"] == 626


def test_assigned_courses_heading_classifies_inbox_with_noisy_ocr_and_misspelled_button() -> None:
    inbox = _observation(
        [
            ("Assigned courses", 100, 120),
            ("John Brown synthetic test persona", 100, 180),
            ("assignments assignments", 100, 240),
            ("LOCAL-MODULE-07", 80, 603),
            ("Open coures", 620, 603),
        ],
        sequence=1,
        vision=_vision_text([_vision_candidate()]),
    )

    decision = CourseOps21Planner().plan("continue", inbox, [])

    assert decision.kind == "action"
    assert decision.action is not None
    assert decision.action.name == "move_mouse"
    assert decision.action.params["x"] == 668
    assert decision.action.params["y"] == 626


def test_human_gate_precedes_assigned_courses_screen_classification() -> None:
    inbox = _observation(
        [
            ("Assigned courses", 100, 120),
            ("Authorization required", 100, 220),
            ("Open coures", 620, 603),
        ],
        sequence=1,
        vision=_vision_text([_vision_candidate()]),
    )

    decision = CourseOps21Planner().plan("continue", inbox, [])

    assert decision.kind == "human_required"
    assert decision.human_gate == "authorization"


def test_ocr_control_coordinates_take_precedence_over_pixel_candidate() -> None:
    inbox = _observation(
        [
            ("John Brown synthetic assignments", 100, 120),
            ("Open course", 1100, 500),
        ],
        sequence=1,
        vision=_vision_text([_vision_candidate()]),
    )

    decision = CourseOps21Planner().plan("continue", inbox, [])

    assert decision.action is not None and decision.action.name == "move_mouse"
    assert decision.action.params["x"] == 1148
    assert decision.action.params["y"] == 511


@pytest.mark.parametrize(
    "vision",
    [
        _vision_text([_vision_candidate()], schema="wrong-schema"),
        _vision_text([{**_vision_candidate(), "extra": "rejected"}]),
        _vision_text(
            [
                {
                    **_vision_candidate(),
                    "bounds": {"height": 46, "width": 134, "x": True, "y": 603},
                }
            ]
        ),
        _vision_text(
            [
                {
                    **_vision_candidate(),
                    "center": {"x": 667, "y": 626},
                }
            ]
        ),
        _vision_text([_vision_candidate(x=1550, width=134)]),
    ],
)
def test_invalid_pixel_candidate_is_rejected_without_a_click(vision: str) -> None:
    inbox = _observation(
        [
            ("John Brown synthetic assignments", 100, 120),
            ("Assigned not started", 260, 603),
        ],
        sequence=1,
        vision=vision,
    )

    decision = CourseOps21Planner().plan("continue", inbox, [])

    assert decision.action is not None
    assert decision.action.name == "scroll"


def test_pixel_candidate_never_classifies_an_unknown_screen() -> None:
    observation = _observation(
        [("Unrecognized local page", 100, 120)],
        sequence=1,
        vision=_vision_text([_vision_candidate()]),
    )

    decision = CourseOps21Planner().plan("continue", observation, [])

    assert decision.kind == "abort"
    assert decision.reason == "courseops_screen_state_unknown_or_ambiguous"


def test_scroll_amount_is_context_specific_and_preserves_viewport_overlap() -> None:
    inbox = _observation(
        [
            ("John Brown synthetic assignments", 100, 120),
            ("Synthetic certificate downloaded", 100, 300),
        ],
        sequence=1,
    )
    inbox_decision = CourseOps21Planner().plan("continue", inbox, [])
    assert inbox_decision.action is not None
    assert inbox_decision.action.name == "scroll"
    assert inbox_decision.action.params["clicks"] == -3

    lesson = _observation(
        [
            ("Read the full lesson", 100, 120),
            ("A visible lesson fact", 100, 300),
        ],
        sequence=2,
    )
    lesson_decision = CourseOps21Planner().plan("continue", lesson, [])
    assert lesson_decision.action is not None
    assert lesson_decision.action.name == "scroll"
    assert lesson_decision.action.params["clicks"] == -7


@pytest.mark.parametrize(
    ("action_ok", "transition_verified"),
    [(False, False), (True, False)],
)
def test_ambiguous_option_click_failure_fails_closed_without_replay(
    action_ok: bool,
    transition_verified: bool,
) -> None:
    planner, history, assessment = _planner_at_radio_assessment()
    option_move = planner.plan("continue", assessment, history)
    assert option_move.action is not None and option_move.action.name == "move_mouse"
    history.append(_transition(option_move, screen_changed=False))
    option_click = planner.plan("continue", assessment, history)
    assert option_click.action is not None and option_click.action.name == "left_click"
    assert option_click.action.params["y"] == 441
    assert option_click.expected is not None
    assert option_click.expected.kind == "vision_contains"
    assert option_click.expected.value == "submit_synthetic_answer"
    history.append(
        _transition(
            option_click,
            ok=action_ok,
            verified=transition_verified,
            screen_changed=False,
        )
    )

    decision = planner.plan("continue", assessment, history)
    assert decision.kind == "abort"
    assert decision.reason == "grounded_option_action_outcome_ambiguous"


@pytest.mark.parametrize(
    ("action_ok", "transition_verified"),
    [(False, False), (True, False)],
)
def test_failed_or_unverified_submit_click_repeats_submit_instead_of_aborting(
    action_ok: bool,
    transition_verified: bool,
) -> None:
    planner, history, assessment = _planner_at_radio_assessment()
    _move_and_click(planner, assessment, history)

    submit_move = planner.plan("continue", assessment, history)
    assert submit_move.action is not None and submit_move.action.name == "move_mouse"
    assert submit_move.action.params["y"] == 661
    history.append(_transition(submit_move, screen_changed=False))
    submit_click = planner.plan("continue", assessment, history)
    assert submit_click.action is not None and submit_click.action.name == "left_click"
    assert submit_click.action.params["y"] == 661
    history.append(
        _transition(
            submit_click,
            ok=action_ok,
            verified=transition_verified,
            screen_changed=False,
        )
    )

    retry_move = planner.plan("continue", assessment, history)
    assert retry_move.kind == "action"
    assert retry_move.action is not None
    assert retry_move.action.name == "move_mouse"
    assert retry_move.action.params["y"] == 661
    history.append(_transition(retry_move, screen_changed=False))
    retry_click = planner.plan("continue", assessment, history)
    assert retry_click.action is not None and retry_click.action.name == "left_click"
    assert retry_click.action.params["y"] == 661


@pytest.mark.parametrize(
    ("visible_text", "expected_gate"),
    [
        ("CAPTCHA verify you are human", "captcha"),
        ("Enter the authenticator code for multi-factor authentication", "mfa"),
        ("Confirm your identity before proceeding", "identity_attestation"),
        ("Authorization required to continue", "authorization"),
    ],
)
def test_planner_fails_closed_for_non_delegable_human_gates(
    visible_text: str,
    expected_gate: str,
) -> None:
    observation = _observation(
        [("Synthetic local benchmark", 50, 50), (visible_text, 100, 200)],
        sequence=1,
    )
    decision = CourseOps21Planner().plan("continue", observation, [])
    assert decision.kind == "human_required"
    assert decision.human_gate == expected_gate


def test_non_synthetic_assessment_always_requires_a_human() -> None:
    observation = _observation(
        [
            ("Certification exam", 100, 100),
            ("Knowledge check", 100, 170),
            ("Choose the best answer", 100, 240),
            ("A. first option", 100, 330),
            ("B. second option", 100, 400),
        ],
        sequence=1,
    )
    decision = CourseOps21Planner().plan("continue", observation, [])
    assert decision.kind == "human_required"
    assert decision.human_gate == "certification_assessment"


def test_synthetic_assessment_without_visible_lesson_memory_aborts() -> None:
    assessment = _observation(
        [
            ("Synthetic certification assessment", 100, 100),
            ("Knowledge check", 100, 170),
            ("A. alpha", 100, 300),
            ("B. beta", 100, 370),
        ],
        sequence=1,
    )
    decision = CourseOps21Planner().plan("continue", assessment, [])
    assert decision.kind == "abort"
    assert "no_visible_lesson_memory" in decision.reason


def test_tied_overlap_aborts_instead_of_guessing() -> None:
    planner = CourseOps21Planner()
    lesson = _observation(
        [
            ("Read the full lesson", 100, 100),
            ("Workers use gloves and boots", 100, 200),
        ],
        sequence=1,
    )
    scroll = planner.plan("continue", lesson, [])
    assessment = _observation(
        [
            ("Synthetic knowledge check", 100, 100),
            ("Which equipment is named?", 100, 170),
            ("A. gloves", 100, 300),
            ("B. boots", 100, 370),
            ("Submit synthetic answer", 100, 500),
        ],
        sequence=2,
    )
    decision = planner.plan("continue", assessment, [_transition(scroll)])
    assert decision.kind == "abort"
    assert decision.reason == "assessment_answer_not_grounded_in_visible_lesson"


@pytest.mark.parametrize("option_a_prefix", [") A.", "� A."])
def test_radio_glyph_prefix_before_option_a_is_tolerated_without_affecting_b_or_c(
    option_a_prefix: str,
) -> None:
    planner = CourseOps21Planner()
    lesson = _observation(
        [
            ("Read the full lesson", 100, 100),
            ("Engage the emergency brake and stop the machine", 100, 220),
        ],
        sequence=1,
    )
    scroll = planner.plan("continue", lesson, [])
    assessment = _observation(
        [
            ("Synthetic knowledge check", 100, 100),
            ("Which visible action is required?", 100, 180),
            (f"{option_a_prefix} Engage the emergency brake and stop the machine", 140, 350),
            ("B. Choose the purple triangle", 140, 430),
            ("C. Select the blue square", 140, 510),
            ("Submit synthetic answer", 420, 650),
        ],
        sequence=2,
    )

    decision = planner.plan("continue", assessment, [_transition(scroll)])

    assert decision.kind == "action"
    assert decision.action is not None
    assert decision.action.name == "move_mouse"
    assert decision.action.params["y"] == 361


@pytest.mark.parametrize("radio_glyph", [")", "�"])
def test_radio_glyph_allows_option_a_when_label_punctuation_is_missing(
    radio_glyph: str,
) -> None:
    planner = CourseOps21Planner()
    lesson = _observation(
        [
            ("Read the full lesson", 100, 100),
            (
                "Compressed gas cylinders must be secured upright and moved with an approved cart",
                100,
                220,
            ),
        ],
        sequence=1,
    )
    scroll = planner.plan("continue", lesson, [])
    assessment = _observation(
        [
            ("Synthetic knowledge check", 100, 100),
            ("How should a compressed gas cylinder be stored and moved?", 100, 180),
            (f"{radio_glyph} A Secured upright and moved with an approved cart", 140, 350),
            ("B. Left loose on the floor", 140, 430),
            ("C. Rolled along its base", 140, 510),
            ("Submit synthetic answer", 420, 650),
        ],
        sequence=2,
    )

    decision = planner.plan("continue", assessment, [_transition(scroll)])

    assert decision.kind == "action"
    assert decision.action is not None
    assert decision.action.name == "move_mouse"
    assert decision.action.params["y"] == 361


def test_actual_hover_radio_artifact_keeps_grounded_b_target_stable() -> None:
    toolbar = [
        OCRToken("�", 30, 63, 15, 14),
        OCRToken("G", 67, 63, 14, 14),
        OCRToken("�", 103, 63, 9, 14),
        OCRToken("127.0.0.1:56411", 127, 63, 92, 14),
        OCRToken("we", 616, 62, 52, 16),
        OCRToken("ge", 689, 69, 49, 12),
        OCRToken("hy", 759, 54, 19, 30),
        OCRToken("cat", 789, 65, 23, 9),
    ]
    planner = CourseOps21Planner()
    lesson = _token_observation(
        toolbar
        + [
            OCRToken("Read the full lesson", 80, 300, 220, 20),
            OCRToken(
                "If material may contain asbestos and is damaged stop work leave it undisturbed "
                "and report it through the site process",
                80,
                400,
                650,
                40,
            ),
        ],
        sequence=1,
    )
    scroll = planner.plan("continue", lesson, [])
    assessment_tokens = toolbar + [
        OCRToken("Synthetic certification assessment", 80, 380, 295, 12),
        OCRToken(
            "What is the correct first response to damaged material that may contain asbestos?",
            80,
            481,
            580,
            16,
        ),
        OCRToken("Choose the best answer from the visible lesson", 99, 518, 332, 16),
        OCRToken(")", 132, 581, 5, 18),
        OCRToken("A.", 152, 584, 13, 11),
        OCRToken("Sweep", 171, 584, 45, 15),
        OCRToken("it", 222, 583, 8, 12),
        OCRToken("into", 235, 583, 26, 12),
        OCRToken("a", 267, 587, 7, 8),
        OCRToken("waste", 279, 585, 40, 10),
        OCRToken("bag", 325, 583, 24, 16),
        OCRToken("B.", 153, 656, 11, 11),
        OCRToken("Leave", 170, 656, 39, 11),
        OCRToken("it", 215, 655, 8, 12),
        OCRToken("undisturbed", 228, 655, 84, 12),
        OCRToken("and", 317, 655, 26, 12),
        OCRToken("report", 349, 657, 43, 14),
        OCRToken("it", 397, 655, 8, 12),
        OCRToken("C.", 153, 728, 12, 11),
        OCRToken("Break", 171, 727, 38, 12),
        OCRToken("off", 214, 727, 30, 12),
        OCRToken("a", 239, 717, 6, 32),
        OCRToken("sample", 250, 727, 50, 16),
        OCRToken("Submit synthetic answer", 80, 849, 225, 46),
    ]
    assessment = _token_observation(assessment_tokens, sequence=2)
    history = [_transition(scroll)]

    move = planner.plan("continue", assessment, history)

    assert move.kind == "action"
    assert move.action is not None
    assert move.action.name == "move_mouse"
    assert move.action.params["x"] == 279
    assert move.action.params["y"] == 663
    assert (move.action.params["x"], move.action.params["y"]) != (421, 69)

    # The retained hover frame differs only by Tesseract recognizing the
    # selected radio control as U+00A9 immediately before the unchanged B row.
    hover_tokens = assessment_tokens.copy()
    hover_tokens.insert(len(toolbar) + 21, OCRToken("©", 115, 651, 22, 22))
    hover = _token_observation(hover_tokens, sequence=3, cursor=(279, 663))
    history.append(_transition(move, verified=True, screen_changed=True))

    click = planner.plan("continue", hover, history)

    assert click.kind == "action"
    assert click.action is not None
    assert click.action.name == "left_click"
    assert click.action.params == {"x": 279, "y": 663}


@pytest.mark.parametrize(
    ("content_shift", "expected_kind"),
    [(0, "action"), (1, "abort")],
)
def test_live_compressed_gas_hover_requires_exact_answer_content_geometry(
    content_shift: int,
    expected_kind: str,
) -> None:
    planner = CourseOps21Planner()
    lesson = _token_observation(
        [
            OCRToken("Read the full lesson", 80, 300, 220, 20),
            OCRToken(
                "Compressed gas cylinders must be secured upright and moved by approved cart",
                80,
                400,
                650,
                40,
            ),
        ],
        sequence=1,
    )
    scroll = planner.plan("continue", lesson, [])
    context = [
        OCRToken("Synthetic certification assessment", 80, 380, 295, 12),
        OCRToken(
            "How should a compressed gas cylinder be stored and moved?",
            80,
            481,
            440,
            16,
        ),
        OCRToken("Choose the best answer from the visible lesson", 99, 518, 332, 12),
        OCRToken("Submit synthetic answer", 80, 849, 225, 46),
    ]
    content = [
        OCRToken("Secured", 171, 583, 55, 12),
        OCRToken("upright", 232, 583, 51, 16),
        OCRToken("and", 288, 583, 25, 12),
        OCRToken("moved", 320, 583, 46, 12),
        OCRToken("by", 373, 583, 16, 16),
        OCRToken("approved", 393, 583, 66, 16),
        OCRToken("cart", 465, 585, 26, 10),
    ]
    other_rows = [
        OCRToken("B.", 153, 656, 11, 11),
        OCRToken("Left", 170, 655, 28, 12),
        OCRToken("loose", 204, 655, 39, 12),
        OCRToken("on", 249, 655, 17, 12),
        OCRToken("the", 272, 655, 23, 12),
        OCRToken("floor", 301, 655, 34, 12),
        OCRToken("C.", 153, 728, 12, 11),
        OCRToken("Rolled", 171, 727, 42, 16),
        OCRToken("along", 219, 727, 38, 12),
        OCRToken("its", 263, 727, 19, 12),
        OCRToken("base", 288, 727, 34, 16),
    ]
    before = _token_observation(
        context + [OCRToken(")", 132, 581, 5, 18), OCRToken("A", 152, 584, 13, 11)] + content + other_rows,
        sequence=2,
        cursor=(226, 823),
    )
    history = [_transition(scroll)]

    move = planner.plan("continue", before, history)

    assert move.action is not None
    assert move.action.name == "move_mouse"
    assert move.action.params == {"x": 321, "y": 591, "duration": 0.25}
    history.append(_transition(move, verified=True, screen_changed=True))
    hover_content = [
        replace(token, x=token.x + content_shift) if token.text == "Secured" else token for token in content
    ]
    hover = _token_observation(
        context
        + [OCRToken("�", 115, 579, 22, 22), OCRToken("A", 143, 575, 13, 30)]
        + hover_content
        + other_rows,
        sequence=3,
        cursor=(321, 591),
    )

    decision = planner.plan("continue", hover, history)

    assert decision.kind == expected_kind
    if content_shift == 0:
        assert decision.action is not None
        assert decision.action.name == "left_click"
        assert decision.action.params == {"x": 321, "y": 591}
        assert decision.expected == ObservationPredicate(
            "vision_contains",
            "submit_synthetic_answer",
        )
    else:
        assert decision.reason == "cached_grounded_option_row_not_visible"


def test_retained_hover_cache_retries_stale_move_and_stale_click() -> None:
    toolbar = [
        OCRToken("€", 30, 63, 15, 14),
        OCRToken("G", 67, 63, 14, 14),
        OCRToken("©", 103, 63, 9, 14),
        OCRToken("127.0.0.1:65046", 127, 63, 92, 14),
    ]
    planner = CourseOps21Planner()
    lesson = _token_observation(
        toolbar
        + [
            OCRToken("Read the full lesson", 80, 300, 220, 20),
            OCRToken(
                "Entry requires a permit atmospheric test attendant and rescue plan",
                80,
                400,
                650,
                40,
            ),
        ],
        sequence=1,
    )
    scroll = planner.plan("continue", lesson, [])
    rows_before = [
        OCRToken(")", 132, 581, 5, 18),
        OCRToken("A.A", 152, 584, 13, 11),
        OCRToken("flashlight", 170, 583, 79, 16),
        OCRToken("and", 254, 583, 25, 12),
        OCRToken("verbal", 285, 583, 42, 12),
        OCRToken("permission", 333, 583, 75, 16),
        OCRToken("B.A", 153, 656, 26, 11),
        OCRToken("permit,", 185, 655, 48, 16),
        OCRToken("atmospheric", 238, 655, 87, 16),
        OCRToken("test,", 330, 657, 28, 12),
        OCRToken("attendant,", 364, 655, 70, 14),
        OCRToken("and", 440, 655, 25, 12),
        OCRToken("rescue", 472, 659, 44, 8),
        OCRToken("plan", 522, 655, 28, 16),
        OCRToken("C.", 153, 728, 12, 11),
        OCRToken("Only", 170, 727, 44, 16),
        OCRToken("a", 210, 717, 6, 32),
        OCRToken("mobile", 221, 727, 47, 12),
        OCRToken("phone", 274, 727, 43, 16),
    ]
    assessment_context = toolbar + [
        OCRToken("Synthetic certification assessment", 80, 380, 295, 12),
        OCRToken(
            "Which conditions must exist before confined-space entry?",
            80,
            481,
            408,
            16,
        ),
        OCRToken("Choose the best answer from the visible lesson.", 99, 518, 332, 12),
        OCRToken("Submit synthetic answer", 80, 849, 225, 46),
    ]
    before = _token_observation(
        assessment_context + rows_before,
        sequence=2,
        cursor=(226, 823),
        bound_window=3_868_196,
        dpi=(96.0, 96.0),
    )
    history = [_transition(scroll)]

    move = planner.plan("continue", before, history)

    assert move.action is not None
    assert move.action.name == "move_mouse"
    assert move.action.params["x"] == 351
    assert move.action.params["y"] == 663

    rows_hover = [
        OCRToken("©", 115, 651, 22, 22),
        *[
            OCRToken("8.A", token.x, token.y, token.width, token.height) if token.text == "B.A" else token
            for token in rows_before
        ],
    ]
    hover_after_stale_move = _token_observation(
        assessment_context + rows_hover,
        sequence=3,
        cursor=(226, 823),
        bound_window=3_868_196,
        dpi=(96.0, 96.0),
    )
    assert planner._assessment_options(planner_module._ocr_lines(hover_after_stale_move)) == ()
    history.append(
        _transition(
            move,
            ok=False,
            verified=False,
            screen_changed=True,
            code="gateway_stale_source_frame",
        )
    )

    retry_move = planner.plan("continue", hover_after_stale_move, history)

    assert retry_move.kind == "action"
    assert retry_move.action is not None
    assert retry_move.action.name == "move_mouse"
    assert retry_move.action.params["x"] == 351
    assert retry_move.action.params["y"] == 663
    history.append(_transition(retry_move, verified=True, screen_changed=True))
    hover_at_target = _token_observation(
        assessment_context + rows_hover,
        sequence=4,
        cursor=(351, 663),
        bound_window=3_868_196,
        dpi=(96.0, 96.0),
    )

    stale_click = planner.plan("continue", hover_at_target, history)

    assert stale_click.action is not None
    assert stale_click.action.name == "left_click"
    assert stale_click.action.params == {"x": 351, "y": 663}
    assert stale_click.expected is not None
    assert stale_click.expected.kind == "vision_contains"
    assert stale_click.expected.value == "submit_synthetic_answer"
    history.append(
        _transition(
            stale_click,
            ok=False,
            verified=False,
            screen_changed=True,
            code="gateway_stale_source_frame",
        )
    )
    hover_after_stale_click = _token_observation(
        assessment_context + rows_hover,
        sequence=5,
        cursor=(351, 663),
        bound_window=3_868_196,
        dpi=(96.0, 96.0),
    )

    second_retry_move = planner.plan("continue", hover_after_stale_click, history)

    assert second_retry_move.action is not None
    assert second_retry_move.action.name == "move_mouse"
    assert second_retry_move.action.params["x"] == 351
    assert second_retry_move.action.params["y"] == 663
    history.append(_transition(second_retry_move, verified=True, screen_changed=True))
    second_hover_at_target = _token_observation(
        assessment_context + rows_hover,
        sequence=6,
        cursor=(351, 663),
        bound_window=3_868_196,
        dpi=(96.0, 96.0),
    )

    retry_click = planner.plan("continue", second_hover_at_target, history)

    assert retry_click.action is not None
    assert retry_click.action.name == "left_click"
    assert retry_click.action.params == {"x": 351, "y": 663}
    history.append(_transition(retry_click, verified=True, screen_changed=True))
    selected = _token_observation(
        assessment_context + rows_hover,
        sequence=7,
        cursor=(351, 663),
        bound_window=3_868_196,
        dpi=(96.0, 96.0),
        vision=_vision_text(
            [
                _vision_candidate(
                    label="submit_synthetic_answer",
                    x=80,
                    y=849,
                    width=225,
                    height=46,
                )
            ]
        ),
    )

    submit_move = planner.plan("continue", selected, history)

    assert submit_move.action is not None
    assert submit_move.action.name == "move_mouse"
    assert submit_move.action.params["x"] == 192
    assert submit_move.action.params["y"] == 872


def test_pending_grounded_option_is_not_reused_for_a_different_question() -> None:
    planner, history, move = _planner_with_bound_option_move()
    assert move.action is not None
    target = (move.action.params["x"], move.action.params["y"])
    history.append(_transition(move, verified=True, screen_changed=True))
    different_question = _bound_assessment_observation(
        sequence=903,
        cursor=target,
        question="Which entirely different control is required?",
    )

    decision = planner.plan("continue", different_question, history)

    assert decision.kind == "abort"
    assert decision.reason == "cached_grounded_option_question_changed"


def test_cached_option_fails_closed_when_same_question_row_disappears() -> None:
    planner, history, move = _planner_with_bound_option_move()
    assert move.action is not None
    target = (move.action.params["x"], move.action.params["y"])
    history.append(_transition(move, verified=True, screen_changed=True))
    missing_row = _bound_assessment_observation(
        sequence=952,
        cursor=target,
        include_grounded_row=False,
    )

    decision = planner.plan("continue", missing_row, history)

    assert decision.kind == "abort"
    assert decision.reason == "cached_grounded_option_row_not_visible"


def test_cached_option_fails_closed_on_one_pixel_row_geometry_drift() -> None:
    planner, history, move = _planner_with_bound_option_move()
    assert move.action is not None
    target = (move.action.params["x"], move.action.params["y"])
    history.append(_transition(move, verified=True, screen_changed=True))
    shifted_row = _bound_assessment_observation(
        sequence=960,
        cursor=target,
        grounded_row_x=141,
    )

    decision = planner.plan("continue", shifted_row, history)

    assert decision.kind == "abort"
    assert decision.reason == "cached_grounded_option_row_not_visible"


def test_cached_option_fails_closed_on_one_pixel_interior_token_drift() -> None:
    planner, history, move = _planner_with_bound_option_move()
    assert move.action is not None
    target = (move.action.params["x"], move.action.params["y"])
    history.append(_transition(move, verified=True, screen_changed=True))
    current = _bound_assessment_observation(sequence=963, cursor=target)
    shifted_tokens = tuple(
        replace(token, x=token.x + 1) if token.text == "valve" else token for token in current.ocr_tokens
    )
    shifted_interior = replace(current, ocr_tokens=shifted_tokens)

    decision = planner.plan("continue", shifted_interior, history)

    assert decision.kind == "abort"
    assert decision.reason == "cached_grounded_option_row_not_visible"


def test_cached_option_cannot_swallow_new_short_answer_word_as_label_noise() -> None:
    planner, history, move = _planner_with_bound_option_move()
    assert move.action is not None
    target = (move.action.params["x"], move.action.params["y"])
    history.append(_transition(move, verified=True, screen_changed=True))
    current = _bound_assessment_observation(sequence=964, cursor=target)
    changed_tokens = tuple(
        replace(token, text="B.No") if token.text == "B." else token for token in current.ocr_tokens
    )
    changed_content = replace(current, ocr_tokens=changed_tokens)

    decision = planner.plan("continue", changed_content, history)

    assert decision.kind == "abort"
    assert decision.reason == "cached_grounded_option_row_not_visible"


@pytest.mark.parametrize(
    ("bound_window", "dpi"),
    [(7_002, (96.0, 96.0)), (7_001, (120.0, 120.0))],
)
def test_cached_option_fails_closed_on_window_or_dpi_drift(
    bound_window: int,
    dpi: tuple[float, float],
) -> None:
    planner, history, move = _planner_with_bound_option_move()
    assert move.action is not None
    target = (move.action.params["x"], move.action.params["y"])
    history.append(_transition(move, verified=True, screen_changed=True))
    changed_window = _bound_assessment_observation(
        sequence=953,
        cursor=target,
        bound_window=bound_window,
        dpi=dpi,
    )

    decision = planner.plan("continue", changed_window, history)

    assert decision.kind == "abort"
    assert decision.reason == "cached_grounded_option_window_changed"


@pytest.mark.parametrize(
    ("bound_window", "dpi"),
    [(None, (96.0, 96.0)), (7_001, None)],
)
def test_grounded_option_never_moves_without_complete_window_and_dpi_binding(
    bound_window: int | None,
    dpi: tuple[float, float] | None,
) -> None:
    planner = CourseOps21Planner()
    lesson = _observation(
        [
            ("Read the full lesson", 100, 100),
            ("The required control is isolate the valve and report the leak", 100, 220),
        ],
        sequence=961,
    )
    scroll = planner.plan("continue", lesson, [])
    assessment = _bound_assessment_observation(
        sequence=962,
        cursor=(40, 40),
        bound_window=bound_window,
        dpi=dpi,
    )

    decision = planner.plan("continue", assessment, [_transition(scroll)])

    assert decision.kind == "abort"
    assert decision.reason == "grounded_option_cache_binding_unavailable"


def test_cached_option_fails_closed_when_verified_move_cursor_is_wrong() -> None:
    planner, history, move = _planner_with_bound_option_move()
    history.append(_transition(move, verified=True, screen_changed=True))
    wrong_cursor = _bound_assessment_observation(
        sequence=954,
        cursor=(40, 40),
    )

    decision = planner.plan("continue", wrong_cursor, history)

    assert decision.kind == "abort"
    assert decision.reason == "cached_grounded_option_cursor_mismatch"


def test_cached_option_does_not_replay_an_ambiguous_move_failure() -> None:
    planner, history, move = _planner_with_bound_option_move()
    history.append(
        _transition(
            move,
            ok=False,
            verified=False,
            screen_changed=True,
            code="gateway_backend_error",
        )
    )
    current = _bound_assessment_observation(sequence=955, cursor=(40, 40))

    decision = planner.plan("continue", current, history)

    assert decision.kind == "abort"
    assert decision.reason == "grounded_option_action_outcome_ambiguous"


def test_cached_option_does_not_replay_an_ambiguous_click_failure() -> None:
    planner, history, move = _planner_with_bound_option_move()
    assert move.action is not None
    target = (move.action.params["x"], move.action.params["y"])
    history.append(_transition(move, verified=True, screen_changed=True))
    at_target = _bound_assessment_observation(sequence=956, cursor=target)
    click = planner.plan("continue", at_target, history)
    assert click.action is not None and click.action.name == "left_click"
    history.append(
        _transition(
            click,
            ok=False,
            verified=False,
            screen_changed=True,
            code="gateway_postcapture_failed",
        )
    )
    after_failure = _bound_assessment_observation(sequence=957, cursor=target)

    decision = planner.plan("continue", after_failure, history)

    assert decision.kind == "abort"
    assert decision.reason == "grounded_option_action_outcome_ambiguous"


def test_cached_option_requires_its_exact_vision_success_predicate() -> None:
    planner, history, move = _planner_with_bound_option_move()
    assert move.action is not None
    target = (move.action.params["x"], move.action.params["y"])
    history.append(_transition(move, verified=True, screen_changed=True))
    at_target = _bound_assessment_observation(sequence=958, cursor=target)
    click = planner.plan("continue", at_target, history)
    assert click.action is not None and click.action.name == "left_click"
    tampered_decision = PlannerDecision(
        kind="action",
        reason=click.reason,
        action=click.action,
        expected=ObservationPredicate("screen_changed"),
    )
    history.append(_transition(tampered_decision, verified=True, screen_changed=True))
    current = _bound_assessment_observation(sequence=959, cursor=target)

    decision = planner.plan("continue", current, history)

    assert decision.kind == "abort"
    assert decision.reason == "grounded_option_action_outcome_ambiguous"


@pytest.mark.parametrize(
    "misleading_prefix",
    ["warning A.", "123 A.", "!!! A.", "___ A."],
)
def test_arbitrary_leading_noise_cannot_create_an_option_a(misleading_prefix: str) -> None:
    planner = CourseOps21Planner()
    lesson = _observation(
        [
            ("Read the full lesson", 100, 100),
            ("Engage the emergency brake and stop the machine", 100, 220),
        ],
        sequence=1,
    )
    scroll = planner.plan("continue", lesson, [])
    assessment = _observation(
        [
            ("Synthetic knowledge check", 100, 100),
            ("Which visible action is required?", 100, 180),
            (f"{misleading_prefix} Engage the emergency brake and stop the machine", 140, 350),
            ("B. Choose the purple triangle", 140, 430),
            ("C. Select the blue square", 140, 510),
            ("Submit synthetic answer", 420, 650),
        ],
        sequence=2,
    )

    decision = planner.plan("continue", assessment, [_transition(scroll)])

    assert decision.kind == "abort"
    assert decision.reason == "assessment_answer_not_grounded_in_visible_lesson"


@pytest.mark.parametrize(
    "misleading_prefix",
    ["A", "warning A", "123 A", "!!! A", "___ A"],
)
def test_missing_label_punctuation_requires_a_bounded_radio_glyph_prefix(
    misleading_prefix: str,
) -> None:
    planner = CourseOps21Planner()
    lesson = _observation(
        [
            ("Read the full lesson", 100, 100),
            ("Secured upright and moved with an approved cart", 100, 220),
        ],
        sequence=1,
    )
    scroll = planner.plan("continue", lesson, [])
    assessment = _observation(
        [
            ("Synthetic knowledge check", 100, 100),
            ("How should the cylinder be moved?", 100, 180),
            (f"{misleading_prefix} Secured upright and moved with an approved cart", 140, 350),
            ("B. Choose the purple triangle", 140, 430),
            ("C. Select the blue square", 140, 510),
            ("Submit synthetic answer", 420, 650),
        ],
        sequence=2,
    )

    decision = planner.plan("continue", assessment, [_transition(scroll)])

    assert decision.kind == "abort"
    assert decision.reason == "assessment_answer_not_grounded_in_visible_lesson"


@pytest.mark.parametrize("ordinal", range(21))
def test_twenty_one_generated_assessments_are_grounded_without_course_tables(ordinal: int) -> None:
    planner = CourseOps21Planner()
    unique_rule = f"signal{ordinal} safeguard{ordinal} report{ordinal}"
    lesson = _observation(
        [
            ("Read the full lesson", 100, 100),
            (f"The visible control rule is {unique_rule}", 100, 220),
        ],
        sequence=ordinal * 2 + 1,
    )
    scroll = planner.plan("continue", lesson, [])
    correct_index = ordinal % 3
    choices = [
        f"unrelated{ordinal} distractor alpha",
        f"unrelated{ordinal} distractor beta",
        f"unrelated{ordinal} distractor gamma",
    ]
    choices[correct_index] = unique_rule
    assessment_lines = [
        ("Synthetic knowledge check", 100, 100),
        (f"Which visible rule applies to signal{ordinal}?", 100, 180),
        ("Choose the best answer from the visible lesson", 100, 240),
    ]
    assessment_lines.extend(
        (f"{chr(65 + index)}. {choice}", 140, 340 + index * 90) for index, choice in enumerate(choices)
    )
    assessment_lines.append(("Submit synthetic answer", 400, 700))
    assessment = _observation(assessment_lines, sequence=ordinal * 2 + 2)

    decision = planner.plan("continue", assessment, [_transition(scroll)])
    assert decision.kind == "action"
    assert decision.action is not None
    assert decision.action.name == "move_mouse"
    assert decision.action.params["y"] == 351 + correct_index * 90


def test_typed_synthetic_answer_is_marked_as_assessment_text() -> None:
    planner = CourseOps21Planner()
    history: list = []
    lesson = _observation(
        [
            ("Read the full lesson", 100, 100),
            ("Emergency isolation requires closing the valve and reporting the leak", 100, 220),
        ],
        sequence=1,
    )
    scroll = planner.plan("continue", lesson, history)
    history.append(_transition(scroll))
    assessment = _observation(
        [
            ("Synthetic certification assessment", 100, 100),
            ("What is required for emergency isolation?", 100, 180),
            ("Type your answer", 100, 300),
            ("Submit synthetic answer", 100, 500),
        ],
        sequence=2,
    )
    _move_and_click(planner, assessment, history)
    typed = planner.plan("continue", assessment, history)
    assert typed.kind == "action"
    assert typed.action is not None
    assert typed.action.name == "type_text"
    assert typed.action.params["text_class"] == "assessment_answer"
    assert "emergency isolation" in str(typed.action.params["text"])


def test_only_exact_21_of_21_marker_can_complete() -> None:
    observation = _observation(
        [
            ("John Brown synthetic assignments", 100, 100),
            ("21 of 21 complete", 100, 180),
            ("Synthetic certificate downloaded", 100, 260),
        ],
        sequence=1,
    )
    decision = CourseOps21Planner().plan("continue", observation, [])
    assert decision.kind != "complete"


def test_scroll_limits_are_bounded_and_invalid_limits_are_rejected() -> None:
    with pytest.raises(CourseOps21PlannerError, match="positive integer"):
        CourseOps21Planner(max_lesson_scrolls=0)

    planner = CourseOps21Planner(max_lesson_scrolls=1)
    lesson = _observation(
        [("Read the full lesson", 100, 100), ("A visible fact", 100, 250)],
        sequence=1,
    )
    first = planner.plan("continue", lesson, [])
    assert first.action is not None and first.action.name == "scroll"
    second = planner.plan("continue", lesson, [_transition(first)])
    assert second.kind == "abort"
    assert second.reason == "lesson_scroll_limit_reached_without_assessment"


def test_failed_move_is_not_treated_as_pointer_arrival() -> None:
    planner = CourseOps21Planner()
    welcome = _observation(
        [
            ("Twenty-one local safety courses are ready", 100, 100),
            ("Open local course inbox", 300, 300),
        ],
        sequence=1,
    )
    first = planner.plan("continue", welcome, [])
    assert first.action is not None and first.action.name == "move_mouse"
    retry = planner.plan("continue", welcome, [_transition(first, ok=False)])
    assert retry.action is not None and retry.action.name == "move_mouse"


def test_decisions_depend_on_ocr_and_history_not_cursor_or_hidden_course_data() -> None:
    lines = [
        ("Twenty-one local safety courses are ready", 100, 100),
        ("Open local course inbox", 300, 300),
    ]
    first = CourseOps21Planner().plan(
        "continue",
        _observation(lines, sequence=1, cursor=(2, 2)),
        [],
    )
    second = CourseOps21Planner().plan(
        "continue",
        _observation(lines, sequence=2, cursor=(1500, 900)),
        [],
    )
    assert first.action == second.action

    source = inspect.getsource(planner_module)
    assert "GE-EHS-" not in source
    assert "answer_key" not in source.casefold()
    assert "tests/fixtures" not in source.replace("\\", "/")

    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imported_roots.isdisjoint({"pathlib", "urllib"})
    forbidden_calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "open" not in forbidden_calls


def test_gui_action_contract_remains_explicit() -> None:
    action = GuiAction("move_mouse", {"x": 10, "y": 20, "duration": 0.25})
    assert action.params == {"x": 10, "y": 20, "duration": 0.25}
