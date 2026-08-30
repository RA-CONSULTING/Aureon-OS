"""Deterministic OCR-only planner for the local CourseOps-21 benchmark.

The planner has no fixture, browser, filesystem, or network dependency.  It
derives every coordinate from the current :class:`ScreenObservation` OCR boxes
and remembers only lesson text that was previously visible on screen.  A
synthetic assessment answer is selected by generic token and phrase overlap;
there is deliberately no course identifier or answer table in this module.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from aureon.operator.local_gui_observer import OCRToken, ScreenObservation
from aureon.operator.local_gui_runtime import (
    GuiAction,
    ObservationPredicate,
    PlannerDecision,
    RuntimeTransition,
)

COURSEOPS_21_COMPLETION_MARKER = "COURSEOPS 21 OF 21 COMPLETE"

_MAX_LESSON_LINES = 128
_MAX_LESSON_CHARACTERS = 16_000
_TARGET_TOLERANCE_PIXELS = 14
_INBOX_SCROLL_CLICKS = -3
_LESSON_SCROLL_CLICKS = -7
_VISION_SCHEMA_VERSION = "aureon-courseops-vision-v1"
_VISION_SOURCE = "pixel_green+ocr"
_MAX_VISION_CANDIDATES = 64
_MAX_VISION_TEXT_CHARACTERS = 32_768
_RADIO_OPTION_GLYPHS = frozenset({")", "©", "�"})
_OPTION_LABEL_OCR_CONFUSABLES = {"B": frozenset({"8"})}
_SAFE_OPTION_REPLAY_FAILURE_CODES = frozenset({"gateway_stale_source_frame"})
_OPTION_PREFIX = re.compile(
    r"^\s*(?:[)©�]\s*)?([A-H])\s*[.)\]:-]\s*(.+?)\s*$",
    re.IGNORECASE,
)
_RADIO_OPTION_PREFIX_WITHOUT_LABEL_PUNCTUATION = re.compile(
    r"^\s*[)©�]\s*([A-H])\s+(.+?)\s*$",
    re.IGNORECASE,
)
_WORD = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")

_VISION_LABELS = frozenset(
    {
        "begin_synthetic_assessment",
        "download_synthetic_certificate",
        "open_course",
        "open_local_course_inbox",
        "return_to_course_inbox",
        "submit_synthetic_answer",
        "unknown_green_control",
    }
)

_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "before",
        "best",
        "by",
        "choose",
        "for",
        "from",
        "how",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "only",
        "or",
        "should",
        "that",
        "the",
        "their",
        "this",
        "to",
        "visible",
        "what",
        "when",
        "which",
        "with",
    }
)

_DIRECT_HUMAN_GATES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("captcha", ("captcha", "verify you are human", "prove you are human")),
    (
        "mfa",
        (
            "multi factor authentication",
            "two factor authentication",
            "authenticator code",
            "verification code",
            "security code from your device",
        ),
    ),
    (
        "identity_attestation",
        (
            "identity attestation",
            "confirm your identity",
            "verify your identity",
            "i certify that i am",
            "i attest that i am",
        ),
    ),
    (
        "authorization",
        (
            "authorization required",
            "authorisation required",
            "approval required",
            "permission required",
            "authorize this action",
            "authorise this action",
            "grant access",
        ),
    ),
)

_ASSESSMENT_MARKERS = (
    "assessment question",
    "certification assessment",
    "certification exam",
    "certification quiz",
    "choose the best answer",
    "exam question",
    "final assessment",
    "graded assessment",
    "knowledge check",
    "quiz question",
    "submit answer",
)


class CourseOps21PlannerError(ValueError):
    """Raised for invalid planner construction rather than uncertain screens."""


@dataclass(frozen=True)
class _OCRLine:
    text: str
    tokens: tuple[OCRToken, ...]
    left: int
    top: int
    right: int
    bottom: int

    @property
    def x(self) -> int:
        return self.left + (self.right - self.left) // 2

    @property
    def y(self) -> int:
        return self.top + (self.bottom - self.top) // 2


@dataclass(frozen=True)
class _AssessmentOption:
    label: str
    text: str
    line: _OCRLine
    content_line: _OCRLine
    content_signature: tuple[tuple[str, int, int, int, int], ...]
    score: tuple[int, int, int]


@dataclass(frozen=True)
class _PendingAssessmentTransition:
    action_signature: str
    expected_kind: str
    expected_value: str
    verified_stage: str
    retry_stage: str
    clear_grounded_option_on_verified: bool


@dataclass(frozen=True)
class _PendingGroundedOption:
    question: str
    label: str
    option_text: str
    x: int
    y: int
    left: int
    top: int
    right: int
    bottom: int
    content_left: int
    content_top: int
    content_right: int
    content_bottom: int
    content_signature: tuple[tuple[str, int, int, int, int], ...]
    window_handle: int
    window_process_id: int
    window_title_sha256: str
    window_left: int
    window_top: int
    window_width: int
    window_height: int
    dpi_x: float | None
    dpi_y: float | None


@dataclass(frozen=True)
class _VisionControlCandidate:
    label: str
    line: _OCRLine


@dataclass(frozen=True)
class _OptionContentEvidence:
    line: _OCRLine
    signature: tuple[tuple[str, int, int, int, int], ...]
    label_token_index: int
    last_token_index: int


def _normalized(value: str) -> str:
    return " ".join(_WORD.findall(value.casefold().replace("’", "'")))


def _words(value: str, *, content_only: bool = False) -> tuple[str, ...]:
    words = tuple(_WORD.findall(value.casefold().replace("’", "'")))
    if not content_only:
        return words
    return tuple(word for word in words if len(word) > 1 and word not in _STOP_WORDS)


def _ocr_lines(observation: ScreenObservation) -> tuple[_OCRLine, ...]:
    """Group OCR boxes into deterministic screen-space lines."""

    groups: list[list[OCRToken]] = []
    centers: list[float] = []
    for token in sorted(
        observation.ocr_tokens,
        key=lambda item: (item.y + item.height / 2.0, item.x, item.text.casefold()),
    ):
        center = token.y + token.height / 2.0
        chosen: int | None = None
        chosen_distance = float("inf")
        for index, existing_center in enumerate(centers):
            tallest = max(item.height for item in groups[index])
            tolerance = max(6.0, min(float(tallest), float(token.height)) * 0.6)
            distance = abs(center - existing_center)
            if distance <= tolerance and distance < chosen_distance:
                chosen = index
                chosen_distance = distance
        if chosen is None:
            groups.append([token])
            centers.append(center)
        else:
            groups[chosen].append(token)
            centers[chosen] = sum(item.y + item.height / 2.0 for item in groups[chosen]) / len(groups[chosen])

    lines: list[_OCRLine] = []
    for group in groups:
        ordered = tuple(sorted(group, key=lambda item: (item.x, item.y, item.text.casefold())))
        lines.append(
            _OCRLine(
                text=" ".join(item.text.strip() for item in ordered if item.text.strip()),
                tokens=ordered,
                left=min(item.x for item in ordered),
                top=min(item.y for item in ordered),
                right=max(item.x + item.width for item in ordered),
                bottom=max(item.y + item.height for item in ordered),
            )
        )
    return tuple(sorted(lines, key=lambda line: (line.top, line.left, line.text.casefold())))


def _screen_text(lines: Sequence[_OCRLine]) -> str:
    return _normalized(" ".join(line.text for line in lines))


def _option_target_line(line: _OCRLine) -> _OCRLine:
    """Exclude a separately recognized radio glyph from option hit geometry."""

    if len(line.tokens) < 2 or line.tokens[0].text.strip() not in _RADIO_OPTION_GLYPHS:
        return line
    target_tokens = line.tokens[1:]
    return _OCRLine(
        text=" ".join(token.text.strip() for token in target_tokens if token.text.strip()),
        tokens=target_tokens,
        left=min(token.x for token in target_tokens),
        top=min(token.y for token in target_tokens),
        right=max(token.x + token.width for token in target_tokens),
        bottom=max(token.y + token.height for token in target_tokens),
    )


def _option_label_prefix_matches(prefix: Sequence[str], label: str) -> bool:
    normalized_label = label.upper()
    if normalized_label not in tuple("ABCDEFGH") or len(prefix) != 1:
        return False
    allowed = {normalized_label.casefold()}
    allowed.update(value.casefold() for value in _OPTION_LABEL_OCR_CONFUSABLES.get(normalized_label, ()))
    return prefix[0] in allowed


def _option_content_evidence(
    line: _OCRLine,
    *,
    label: str,
    option_text: str,
) -> _OptionContentEvidence | None:
    """Return exact OCR evidence carrying an option's answer content.

    Radio hover can change the radio glyph and the adjacent A-H label box even
    when the answer words have not moved.  The answer-content span gives cached
    pointer handoff an exact, stable geometry without accepting arbitrary row
    movement.  A label and the first content word may share one OCR token (for
    example ``B.A``), so the token span intentionally includes that token.
    """

    expected_words = _words(option_text)
    if not expected_words:
        return None
    flattened: list[tuple[str, int]] = []
    for token_index, token in enumerate(line.tokens):
        flattened.extend((word, token_index) for word in _words(token.text))
    if len(flattened) <= len(expected_words):
        return None
    actual_words = tuple(word for word, _index in flattened)
    if actual_words[-len(expected_words) :] != expected_words:
        return None
    prefix = actual_words[: -len(expected_words)]
    if not _option_label_prefix_matches(prefix, label):
        return None
    first_token = flattened[len(prefix)][1]
    last_token = flattened[-1][1]
    content_tokens = line.tokens[first_token : last_token + 1]
    content_line = _OCRLine(
        text=" ".join(token.text.strip() for token in content_tokens if token.text.strip()),
        tokens=content_tokens,
        left=min(token.x for token in content_tokens),
        top=min(token.y for token in content_tokens),
        right=max(token.x + token.width for token in content_tokens),
        bottom=max(token.y + token.height for token in content_tokens),
    )
    words_by_token: dict[int, list[str]] = {}
    for word, token_index in flattened[len(prefix) :]:
        words_by_token.setdefault(token_index, []).append(word)
    signature = tuple(
        (
            " ".join(words_by_token.get(token_index, ())),
            token.x,
            token.y,
            token.width,
            token.height,
        )
        for token_index, token in enumerate(line.tokens[first_token : last_token + 1], first_token)
    )
    return _OptionContentEvidence(
        line=content_line,
        signature=signature,
        label_token_index=flattened[len(prefix) - 1][1],
        last_token_index=last_token,
    )


def _grounded_option_target_line(option: _AssessmentOption) -> _OCRLine:
    """Choose a click center proven to lie inside immutable answer content."""

    content = option.content_line
    if content.left <= option.line.x < content.right and content.top <= option.line.y < content.bottom:
        return option.line
    return content


def _contains(text: str, phrase: str) -> bool:
    return _normalized(phrase) in text


def _phrase_token_spans(line: _OCRLine, phrase: str) -> tuple[_OCRLine, ...]:
    """Map a normalized phrase match back to only the OCR boxes that formed it."""

    phrase_words = _words(phrase)
    if not phrase_words:
        return ()
    flattened: list[tuple[str, int]] = []
    for token_index, token in enumerate(line.tokens):
        flattened.extend((word, token_index) for word in _words(token.text))

    spans: list[_OCRLine] = []
    seen_token_ranges: set[tuple[int, int]] = set()
    phrase_length = len(phrase_words)
    for start in range(len(flattened) - phrase_length + 1):
        if tuple(word for word, _index in flattened[start : start + phrase_length]) != phrase_words:
            continue
        first_token = flattened[start][1]
        last_token = flattened[start + phrase_length - 1][1]
        token_range = (first_token, last_token)
        if token_range in seen_token_ranges:
            continue
        seen_token_ranges.add(token_range)
        matched_tokens = line.tokens[first_token : last_token + 1]
        spans.append(
            _OCRLine(
                text=" ".join(token.text.strip() for token in matched_tokens if token.text.strip()),
                tokens=matched_tokens,
                left=min(token.x for token in matched_tokens),
                top=min(token.y for token in matched_tokens),
                right=max(token.x + token.width for token in matched_tokens),
                bottom=max(token.y + token.height for token in matched_tokens),
            )
        )
    return tuple(spans)


def _line_for_phrases(
    lines: Sequence[_OCRLine],
    phrases: Sequence[str],
) -> _OCRLine | None:
    """Return the phrase-local OCR box for the best visible control label."""

    candidates: list[tuple[int, int, int, int, _OCRLine]] = []
    for line in lines:
        line_text = _normalized(line.text)
        for raw_phrase in phrases:
            phrase = _normalized(raw_phrase)
            for span in _phrase_token_spans(line, raw_phrase):
                exact_rank = 0 if line_text == phrase else 1
                candidates.append(
                    (
                        exact_rank,
                        abs(len(line_text) - len(phrase)),
                        span.top,
                        span.left,
                        span,
                    )
                )
    if not candidates:
        return None
    return min(candidates, key=lambda item: item[:4])[4]


def _strict_integer(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _vision_control_candidates(
    observation: ScreenObservation,
) -> tuple[_VisionControlCandidate, ...]:
    """Parse the canonical local pixel-vision envelope or reject it entirely."""

    raw = observation.vision_text
    if not raw or raw != raw.strip() or "\n" in raw or "\r" in raw:
        return ()
    if len(raw) > _MAX_VISION_TEXT_CHARACTERS:
        return ()
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return ()
    if not isinstance(payload, dict) or set(payload) != {"candidates", "schema_version"}:
        return ()
    if payload.get("schema_version") != _VISION_SCHEMA_VERSION:
        return ()
    values = payload.get("candidates")
    if not isinstance(values, list) or len(values) > _MAX_VISION_CANDIDATES:
        return ()
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if canonical != raw:
        return ()

    parsed: list[_VisionControlCandidate] = []
    sort_keys: list[tuple[int, int]] = []
    seen_bounds: set[tuple[int, int, int, int]] = set()
    window = observation.window_rect
    for value in values:
        if not isinstance(value, dict) or set(value) != {"bounds", "center", "label", "source"}:
            return ()
        bounds = value.get("bounds")
        center = value.get("center")
        label = value.get("label")
        if (
            not isinstance(bounds, dict)
            or set(bounds) != {"height", "width", "x", "y"}
            or not isinstance(center, dict)
            or set(center) != {"x", "y"}
            or not isinstance(label, str)
            or label not in _VISION_LABELS
            or value.get("source") != _VISION_SOURCE
        ):
            return ()
        x = _strict_integer(bounds.get("x"))
        y = _strict_integer(bounds.get("y"))
        width = _strict_integer(bounds.get("width"))
        height = _strict_integer(bounds.get("height"))
        center_x = _strict_integer(center.get("x"))
        center_y = _strict_integer(center.get("y"))
        if None in {x, y, width, height, center_x, center_y}:
            return ()
        assert x is not None and y is not None
        assert width is not None and height is not None
        assert center_x is not None and center_y is not None
        if x < 0 or y < 0 or width <= 0 or height <= 0:
            return ()
        right = x + width
        bottom = y + height
        if right > observation.width or bottom > observation.height:
            return ()
        if center_x != x + width // 2 or center_y != y + height // 2:
            return ()
        if window is not None and (
            x < window.left
            or y < window.top
            or right > window.left + window.width
            or bottom > window.top + window.height
        ):
            return ()
        bounds_key = (x, y, width, height)
        if bounds_key in seen_bounds:
            return ()
        seen_bounds.add(bounds_key)
        sort_keys.append((y, x))
        parsed.append(
            _VisionControlCandidate(
                label=label,
                line=_OCRLine(
                    text=label,
                    tokens=(),
                    left=x,
                    top=y,
                    right=right,
                    bottom=bottom,
                ),
            )
        )
    if sort_keys != sorted(sort_keys):
        return ()
    return tuple(parsed)


def _vision_control_line(
    candidates: Sequence[_VisionControlCandidate],
    *,
    label: str,
    unknown_policy: str,
) -> _OCRLine | None:
    labelled = [candidate.line for candidate in candidates if candidate.label == label]
    if labelled:
        return labelled[0]
    unknown = [candidate.line for candidate in candidates if candidate.label == "unknown_green_control"]
    if unknown_policy == "first" and unknown:
        return unknown[0]
    if unknown_policy == "last" and unknown:
        return unknown[-1]
    if unknown_policy == "unique" and len(unknown) == 1:
        return unknown[0]
    return None


def _last_action(history: Sequence[RuntimeTransition]) -> GuiAction | None:
    if not history:
        return None
    decision = getattr(history[-1], "decision", None)
    action = getattr(decision, "action", None)
    return action if isinstance(action, GuiAction) else None


def _last_action_succeeded(history: Sequence[RuntimeTransition]) -> bool:
    if not history:
        return False
    result = getattr(history[-1], "result", None)
    return getattr(result, "ok", False) is True


def _last_action_verified(history: Sequence[RuntimeTransition]) -> bool:
    return bool(
        history and _last_action_succeeded(history) and getattr(history[-1], "verified", False) is True
    )


def _last_action_failed_pre_dispatch(history: Sequence[RuntimeTransition]) -> bool:
    if not history:
        return False
    result = getattr(history[-1], "result", None)
    code = getattr(result, "code", "")
    return bool(
        getattr(result, "ok", True) is False
        and isinstance(code, str)
        and code in _SAFE_OPTION_REPLAY_FAILURE_CODES
    )


def _near(first: int, second: int) -> bool:
    return abs(first - second) <= _TARGET_TOLERANCE_PIXELS


def _action_targets_point(action: GuiAction | None, *, x: int, y: int) -> bool:
    if action is None or action.name not in {"move_mouse", "left_click"}:
        return False
    action_x = action.params.get("x")
    action_y = action.params.get("y")
    return bool(
        isinstance(action_x, int)
        and not isinstance(action_x, bool)
        and isinstance(action_y, int)
        and not isinstance(action_y, bool)
        and _near(action_x, x)
        and _near(action_y, y)
    )


class CourseOps21Planner:
    """Bounded local ScreenReel planner for the synthetic 21-course run."""

    locality = "local"

    def __init__(self, *, max_lesson_scrolls: int = 12, max_inbox_scrolls: int = 24) -> None:
        for name, value in (
            ("max_lesson_scrolls", max_lesson_scrolls),
            ("max_inbox_scrolls", max_inbox_scrolls),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise CourseOps21PlannerError(f"{name} must be a positive integer")
        self._max_lesson_scrolls = max_lesson_scrolls
        self._max_inbox_scrolls = max_inbox_scrolls
        self._last_screen = ""
        self._pending_click: tuple[str, int, int] | None = None
        self._lesson_lines: list[str] = []
        self._lesson_line_keys: set[str] = set()
        self._lesson_characters = 0
        self._lesson_scrolls = 0
        self._inbox_scrolls = 0
        self._assessment_stage = "choose"
        self._assessment_pending: _PendingAssessmentTransition | None = None
        self._pending_grounded_option: _PendingGroundedOption | None = None

    def _human_gate(self, screen_text: str) -> str:
        for gate, phrases in _DIRECT_HUMAN_GATES:
            if any(_contains(screen_text, phrase) for phrase in phrases):
                return gate
        assessment_visible = any(_contains(screen_text, marker) for marker in _ASSESSMENT_MARKERS)
        if assessment_visible and not _contains(screen_text, "synthetic"):
            return "certification_assessment"
        return ""

    def _classify(self, screen_text: str, history: Sequence[RuntimeTransition]) -> str:
        if _contains(screen_text, COURSEOPS_21_COMPLETION_MARKER):
            return "final"
        if any(
            _contains(screen_text, phrase)
            for phrase in (
                "synthetic course passed",
                "certificate not yet downloaded",
                "download synthetic test certificate",
                "return to course inbox",
            )
        ):
            return "course_complete"
        if any(
            _contains(screen_text, phrase)
            for phrase in (
                "assigned courses",
                "synthetic assignments",
                "assigned not started",
                "open course",
                "synthetic certificate downloaded",
            )
        ):
            return "inbox"
        if any(
            _contains(screen_text, phrase)
            for phrase in (
                "read the full lesson",
                "end of synthetic lesson",
                "begin synthetic knowledge check",
                "apply the control",
                "verify before proceeding",
            )
        ):
            return "lesson"
        if any(
            _contains(screen_text, phrase)
            for phrase in (
                "twenty one local safety courses are ready",
                "open local course inbox",
            )
        ):
            return "welcome"
        if any(_contains(screen_text, phrase) for phrase in _ASSESSMENT_MARKERS):
            return "assessment"
        action = _last_action(history)
        if self._last_screen == "lesson" and action is not None and action.name == "scroll":
            return "lesson"
        if self._last_screen == "inbox" and action is not None and action.name == "scroll":
            return "inbox"
        return "unknown"

    def _enter_screen(self, screen: str) -> None:
        if screen == self._last_screen:
            return
        self._pending_click = None
        self._assessment_pending = None
        self._pending_grounded_option = None
        if screen == "lesson":
            self._lesson_lines.clear()
            self._lesson_line_keys.clear()
            self._lesson_characters = 0
            self._lesson_scrolls = 0
            self._assessment_stage = "choose"
        elif screen == "inbox":
            self._inbox_scrolls = 0
            self._assessment_stage = "choose"
        elif screen == "assessment":
            self._assessment_stage = "choose"
        self._last_screen = screen

    def _remember_lesson(self, lines: Sequence[_OCRLine]) -> bool:
        for line in lines:
            raw = " ".join(line.text.split())
            key = _normalized(raw)
            if not key or key in self._lesson_line_keys:
                continue
            if len(self._lesson_lines) >= _MAX_LESSON_LINES:
                return False
            if self._lesson_characters + len(raw) > _MAX_LESSON_CHARACTERS:
                return False
            self._lesson_lines.append(raw)
            self._lesson_line_keys.add(key)
            self._lesson_characters += len(raw)
        return True

    def _moved_to_pending_target(
        self,
        *,
        purpose: str,
        x: int,
        y: int,
        history: Sequence[RuntimeTransition],
    ) -> bool:
        if self._pending_click is None or self._pending_click[0] != purpose:
            return False
        pending_x, pending_y = self._pending_click[1:]
        if not (_near(x, pending_x) and _near(y, pending_y)):
            return False
        action = _last_action(history)
        if action is None or action.name != "move_mouse" or not _last_action_verified(history):
            return False
        action_x = action.params.get("x")
        action_y = action.params.get("y")
        return (
            isinstance(action_x, int)
            and not isinstance(action_x, bool)
            and isinstance(action_y, int)
            and not isinstance(action_y, bool)
            and _near(x, action_x)
            and _near(y, action_y)
        )

    def _move_then_click(
        self,
        *,
        purpose: str,
        line: _OCRLine,
        history: Sequence[RuntimeTransition],
        click_reason: str,
        click_expected: ObservationPredicate | None = None,
    ) -> PlannerDecision:
        x, y = line.x, line.y
        if self._moved_to_pending_target(purpose=purpose, x=x, y=y, history=history):
            self._pending_click = None
            return PlannerDecision(
                kind="action",
                reason=click_reason,
                action=GuiAction("left_click", {"x": x, "y": y}),
                expected=click_expected or ObservationPredicate("screen_changed"),
            )
        self._pending_click = (purpose, x, y)
        return PlannerDecision(
            kind="action",
            reason=f"Move visibly to the OCR-bound {purpose} control.",
            action=GuiAction("move_mouse", {"x": x, "y": y, "duration": 0.25}),
            expected=ObservationPredicate("observation_fresh"),
        )

    def _arm_assessment_transition(
        self,
        decision: PlannerDecision,
        *,
        verified_stage: str,
        retry_stage: str,
        clear_grounded_option_on_verified: bool = False,
    ) -> None:
        if decision.action is None:
            raise RuntimeError("assessment transition requires an action")
        if decision.expected is None:
            raise RuntimeError("assessment transition requires an expected predicate")
        self._assessment_pending = _PendingAssessmentTransition(
            action_signature=decision.action.signature(),
            expected_kind=decision.expected.kind,
            expected_value=decision.expected.value,
            verified_stage=verified_stage,
            retry_stage=retry_stage,
            clear_grounded_option_on_verified=clear_grounded_option_on_verified,
        )

    def _reconcile_assessment_transition(
        self,
        history: Sequence[RuntimeTransition],
    ) -> None:
        pending = self._assessment_pending
        if pending is None:
            return
        action = _last_action(history)
        signature_matches = action is not None and action.signature() == pending.action_signature
        transition_decision = getattr(history[-1], "decision", None) if history else None
        transition_expected = getattr(transition_decision, "expected", None)
        predicate_matches = bool(
            transition_expected is not None
            and getattr(transition_expected, "kind", None) == pending.expected_kind
            and getattr(transition_expected, "value", None) == pending.expected_value
        )
        verified_changed = bool(
            signature_matches
            and predicate_matches
            and getattr(history[-1], "verified", False) is True
            and getattr(history[-1], "screen_changed", False) is True
            and _last_action_succeeded(history)
        )
        if verified_changed:
            self._assessment_stage = pending.verified_stage
        elif pending.clear_grounded_option_on_verified and not (
            signature_matches and predicate_matches and _last_action_failed_pre_dispatch(history)
        ):
            self._assessment_stage = "abort_ambiguous_option"
        else:
            self._assessment_stage = pending.retry_stage
        if verified_changed and pending.clear_grounded_option_on_verified:
            self._pending_grounded_option = None
        self._assessment_pending = None
        if not verified_changed:
            # Re-establish pointer intent before repeating a click.  This keeps
            # retries visible and prevents an unchanged option click from
            # advancing to a still-disabled submit control.
            self._pending_click = None

    @staticmethod
    def _scroll(
        lines: Sequence[_OCRLine],
        *,
        clicks: int,
        reason: str,
    ) -> PlannerDecision:
        if not lines:
            return PlannerDecision(kind="abort", reason="cannot_scroll_without_visible_ocr_anchor")
        anchor = max(lines, key=lambda line: (line.bottom, line.right))
        return PlannerDecision(
            kind="action",
            reason=reason,
            action=GuiAction("scroll", {"x": anchor.x, "y": anchor.y, "clicks": clicks}),
            expected=ObservationPredicate("screen_changed"),
        )

    @staticmethod
    def _cacheable_grounded_option(
        observation: ScreenObservation,
        *,
        question: str,
        option: _AssessmentOption,
    ) -> _PendingGroundedOption | None:
        rect = observation.window_rect
        option_text = _normalized(option.text)
        target = _grounded_option_target_line(option)
        content = option.content_line
        if (
            not question
            or not option_text
            or observation.window_handle is None
            or observation.window_process_id is None
            or observation.window_title_sha256 is None
            or rect is None
            or observation.dpi_x is None
            or observation.dpi_y is None
        ):
            return None
        return _PendingGroundedOption(
            question=question,
            label=option.label,
            option_text=option_text,
            x=target.x,
            y=target.y,
            left=option.line.left,
            top=option.line.top,
            right=option.line.right,
            bottom=option.line.bottom,
            content_left=content.left,
            content_top=content.top,
            content_right=content.right,
            content_bottom=content.bottom,
            content_signature=option.content_signature,
            window_handle=observation.window_handle,
            window_process_id=observation.window_process_id,
            window_title_sha256=observation.window_title_sha256,
            window_left=rect.left,
            window_top=rect.top,
            window_width=rect.width,
            window_height=rect.height,
            dpi_x=observation.dpi_x,
            dpi_y=observation.dpi_y,
        )

    @staticmethod
    def _same_pending_window(
        observation: ScreenObservation,
        pending: _PendingGroundedOption,
    ) -> bool:
        rect = observation.window_rect
        return bool(
            rect is not None
            and observation.window_handle == pending.window_handle
            and observation.window_process_id == pending.window_process_id
            and observation.window_title_sha256 == pending.window_title_sha256
            and rect.left == pending.window_left
            and rect.top == pending.window_top
            and rect.width == pending.window_width
            and rect.height == pending.window_height
            and observation.dpi_x == pending.dpi_x
            and observation.dpi_y == pending.dpi_y
        )

    def _visible_pending_option_row(
        self,
        lines: Sequence[_OCRLine],
        pending: _PendingGroundedOption,
    ) -> _OCRLine | None:
        anchor_bottom = self._assessment_anchor_bottom(lines)
        expected_words = _words(pending.option_text)
        if anchor_bottom is None or not expected_words:
            return None
        candidates: list[_OCRLine] = []
        for line in lines:
            if line.top <= anchor_bottom or not _near(line.y, pending.y):
                continue
            evidence = _option_content_evidence(
                line,
                label=pending.label,
                option_text=pending.option_text,
            )
            if evidence is None:
                continue
            target_tokens = line.tokens[evidence.label_token_index : evidence.last_token_index + 1]
            target = _OCRLine(
                text=" ".join(token.text.strip() for token in target_tokens if token.text.strip()),
                tokens=target_tokens,
                left=min(token.x for token in target_tokens),
                top=min(token.y for token in target_tokens),
                right=max(token.x + token.width for token in target_tokens),
                bottom=max(token.y + token.height for token in target_tokens),
            )
            content = evidence.line
            if (
                _near(target.left, pending.left)
                and _near(target.top, pending.top)
                and _near(target.right, pending.right)
                and _near(target.bottom, pending.bottom)
                and (content.left, content.top, content.right, content.bottom)
                == (
                    pending.content_left,
                    pending.content_top,
                    pending.content_right,
                    pending.content_bottom,
                )
                and evidence.signature == pending.content_signature
                and content.left <= pending.x < content.right
                and content.top <= pending.y < content.bottom
            ):
                candidates.append(target)
        if len(candidates) != 1:
            return None
        return candidates[0]

    def _assessment_options(self, lines: Sequence[_OCRLine]) -> tuple[_AssessmentOption, ...]:
        anchor_bottom = self._assessment_anchor_bottom(lines)
        if anchor_bottom is None:
            return ()
        memory_text = _normalized(" ".join(self._lesson_lines))
        memory_counts = Counter(_words(memory_text, content_only=True))
        options: list[_AssessmentOption] = []
        for line in lines:
            if line.top <= anchor_bottom:
                continue
            match = _OPTION_PREFIX.match(line.text)
            if match is None:
                match = _RADIO_OPTION_PREFIX_WITHOUT_LABEL_PUNCTUATION.match(line.text)
            if match is None:
                continue
            label, option_text = match.groups()
            target_line = _option_target_line(line)
            content_evidence = _option_content_evidence(
                target_line,
                label=label,
                option_text=option_text,
            )
            if content_evidence is None:
                continue
            option_words = _words(option_text, content_only=True)
            overlap = tuple(word for word in option_words if word in memory_counts)
            unique_overlap = len(set(overlap))
            weighted_overlap = sum(min(memory_counts[word], 3) for word in set(overlap))
            longest_phrase = 0
            for size in range(2, min(6, len(option_words) + 1)):
                if any(
                    " ".join(option_words[start : start + size]) in memory_text
                    for start in range(0, len(option_words) - size + 1)
                ):
                    longest_phrase = size
            options.append(
                _AssessmentOption(
                    label=label.upper(),
                    text=option_text.strip(),
                    line=target_line,
                    content_line=content_evidence.line,
                    content_signature=content_evidence.signature,
                    score=(longest_phrase, unique_overlap, weighted_overlap),
                )
            )
        ordered = tuple(sorted(options, key=lambda option: (option.line.top, option.line.left)))
        if not self._coherent_assessment_cluster(ordered):
            return ()
        return ordered

    @staticmethod
    def _assessment_anchor_bottom(lines: Sequence[_OCRLine]) -> int | None:
        instruction = [line for line in lines if _contains(_normalized(line.text), "choose the best answer")]
        if instruction:
            return max(line.bottom for line in instruction)
        questions = [line for line in lines if "?" in line.text]
        if questions:
            return max(line.bottom for line in questions)
        heading = [
            line
            for line in lines
            if any(
                _contains(_normalized(line.text), marker)
                for marker in ("knowledge check", "certification assessment")
            )
        ]
        if heading:
            return max(line.bottom for line in heading)
        return None

    @staticmethod
    def _coherent_assessment_cluster(options: Sequence[_AssessmentOption]) -> bool:
        if not 2 <= len(options) <= 8:
            return False
        labels = tuple(option.label for option in options)
        expected = tuple(chr(ord("A") + index) for index in range(len(options)))
        if labels != expected:
            return False
        first_left = options[0].line.left
        if any(abs(option.line.left - first_left) > 96 for option in options[1:]):
            return False
        for first, second in zip(options, options[1:], strict=False):
            vertical_gap = second.line.y - first.line.y
            if not 20 <= vertical_gap <= 240:
                return False
        return True

    def _best_option(self, lines: Sequence[_OCRLine]) -> _AssessmentOption | None:
        options = self._assessment_options(lines)
        if len(options) < 2:
            return None
        ordered = sorted(options, key=lambda option: option.score, reverse=True)
        if ordered[0].score == (0, 0, 0) or ordered[0].score == ordered[1].score:
            return None
        return ordered[0]

    @staticmethod
    def _question(lines: Sequence[_OCRLine]) -> str:
        questions = [line.text.strip() for line in lines if "?" in line.text]
        return max(questions, key=len, default="")

    def _grounded_text_answer(self, question: str) -> str | None:
        question_terms = set(_words(question, content_only=True))
        candidates: list[tuple[int, int, str]] = []
        for line in self._lesson_lines:
            normalized = _normalized(line)
            terms = set(_words(line, content_only=True))
            if not terms:
                continue
            candidates.append((len(terms & question_terms), len(terms), normalized))
        if not candidates:
            return None
        overlap, _length, answer = max(candidates, key=lambda item: (item[0], item[1], item[2]))
        if question_terms and overlap == 0:
            return None
        return answer[:512]

    def _plan_welcome(
        self,
        lines: Sequence[_OCRLine],
        history: Sequence[RuntimeTransition],
        vision_candidates: Sequence[_VisionControlCandidate],
    ) -> PlannerDecision:
        control = _line_for_phrases(lines, ("Open local course inbox", "Open course inbox"))
        if control is None:
            control = _vision_control_line(
                vision_candidates,
                label="open_local_course_inbox",
                unknown_policy="unique",
            )
        if control is None:
            return PlannerDecision(kind="abort", reason="welcome_inbox_control_not_visible")
        return self._move_then_click(
            purpose="welcome inbox",
            line=control,
            history=history,
            click_reason="Open the visible local synthetic course inbox.",
        )

    def _plan_inbox(
        self,
        lines: Sequence[_OCRLine],
        history: Sequence[RuntimeTransition],
        vision_candidates: Sequence[_VisionControlCandidate],
    ) -> PlannerDecision:
        control = _line_for_phrases(lines, ("Open course",))
        if control is None:
            control = _vision_control_line(
                vision_candidates,
                label="open_course",
                unknown_policy="first",
            )
        if control is not None:
            return self._move_then_click(
                purpose="next incomplete course",
                line=control,
                history=history,
                click_reason="Open the first visible incomplete synthetic course.",
            )
        if self._inbox_scrolls >= self._max_inbox_scrolls:
            return PlannerDecision(kind="abort", reason="inbox_scroll_limit_reached_without_open_course")
        self._inbox_scrolls += 1
        return self._scroll(
            lines,
            clicks=_INBOX_SCROLL_CLICKS,
            reason="Scroll the local inbox to find the next visible incomplete course.",
        )

    def _plan_lesson(
        self,
        lines: Sequence[_OCRLine],
        history: Sequence[RuntimeTransition],
        vision_candidates: Sequence[_VisionControlCandidate],
    ) -> PlannerDecision:
        if not self._remember_lesson(lines):
            return PlannerDecision(kind="abort", reason="visible_lesson_memory_limit_exceeded")
        control = _line_for_phrases(
            lines,
            ("Begin synthetic knowledge check", "Begin knowledge check"),
        )
        if control is None:
            control = _vision_control_line(
                vision_candidates,
                label="begin_synthetic_assessment",
                unknown_policy="unique",
            )
        if control is not None:
            return self._move_then_click(
                purpose="begin synthetic assessment",
                line=control,
                history=history,
                click_reason="Begin the visible synthetic assessment after reading the lesson.",
            )
        if self._lesson_scrolls >= self._max_lesson_scrolls:
            return PlannerDecision(kind="abort", reason="lesson_scroll_limit_reached_without_assessment")
        self._lesson_scrolls += 1
        return self._scroll(
            lines,
            clicks=_LESSON_SCROLL_CLICKS,
            reason="Read the next visible lesson frame and continue toward its assessment control.",
        )

    def _plan_assessment(
        self,
        observation: ScreenObservation,
        lines: Sequence[_OCRLine],
        screen_text: str,
        history: Sequence[RuntimeTransition],
        vision_candidates: Sequence[_VisionControlCandidate],
    ) -> PlannerDecision:
        if not self._lesson_lines:
            return PlannerDecision(kind="abort", reason="synthetic_assessment_has_no_visible_lesson_memory")
        if _contains(screen_text, "not correct"):
            return PlannerDecision(kind="abort", reason="synthetic_answer_was_not_accepted")
        self._reconcile_assessment_transition(history)
        if self._assessment_stage == "awaiting_result":
            return PlannerDecision(kind="abort", reason="synthetic_assessment_did_not_advance")
        if self._assessment_stage == "abort_unverified_type":
            return PlannerDecision(kind="abort", reason="synthetic_typed_answer_was_not_verified")

        question = _normalized(self._question(lines))
        pending_option = self._pending_grounded_option
        if pending_option is not None:
            if not question or question != pending_option.question:
                self._pending_grounded_option = None
                self._pending_click = None
                return PlannerDecision(
                    kind="abort",
                    reason="cached_grounded_option_question_changed",
                )
            if not self._same_pending_window(observation, pending_option):
                self._pending_grounded_option = None
                self._pending_click = None
                return PlannerDecision(
                    kind="abort",
                    reason="cached_grounded_option_window_changed",
                )
            if self._visible_pending_option_row(lines, pending_option) is None:
                self._pending_grounded_option = None
                self._pending_click = None
                return PlannerDecision(
                    kind="abort",
                    reason="cached_grounded_option_row_not_visible",
                )
            if self._assessment_stage == "choose":
                action = _last_action(history)
                if not _action_targets_point(
                    action,
                    x=pending_option.x,
                    y=pending_option.y,
                ):
                    return PlannerDecision(
                        kind="abort",
                        reason="cached_grounded_option_action_target_changed",
                    )
                if action is not None and action.name == "move_mouse" and (_last_action_verified(history)):
                    if (
                        observation.cursor_x is None
                        or observation.cursor_y is None
                        or not _near(observation.cursor_x, pending_option.x)
                        or not _near(observation.cursor_y, pending_option.y)
                    ):
                        return PlannerDecision(
                            kind="abort",
                            reason="cached_grounded_option_cursor_mismatch",
                        )
                    self._pending_click = None
                    decision = PlannerDecision(
                        kind="action",
                        reason="Select the option with the strongest overlap to the visible lesson.",
                        action=GuiAction(
                            "left_click",
                            {"x": pending_option.x, "y": pending_option.y},
                        ),
                        expected=ObservationPredicate(
                            "vision_contains",
                            "submit_synthetic_answer",
                        ),
                    )
                    self._arm_assessment_transition(
                        decision,
                        verified_stage="submit",
                        retry_stage="choose",
                        clear_grounded_option_on_verified=True,
                    )
                    return decision
                if not _last_action_failed_pre_dispatch(history):
                    return PlannerDecision(
                        kind="abort",
                        reason="grounded_option_action_outcome_ambiguous",
                    )
                self._pending_click = (
                    "grounded synthetic option",
                    pending_option.x,
                    pending_option.y,
                )
                return PlannerDecision(
                    kind="action",
                    reason="Re-establish the OCR-grounded synthetic option pointer target.",
                    action=GuiAction(
                        "move_mouse",
                        {"x": pending_option.x, "y": pending_option.y, "duration": 0.25},
                    ),
                    expected=ObservationPredicate("observation_fresh"),
                )
        if self._assessment_stage == "abort_ambiguous_option":
            return PlannerDecision(
                kind="abort",
                reason="grounded_option_action_outcome_ambiguous",
            )

        submit = _line_for_phrases(lines, ("Submit synthetic answer", "Submit answer"))
        if submit is None:
            submit = _vision_control_line(
                vision_candidates,
                label="submit_synthetic_answer",
                unknown_policy="unique",
            )
        if self._assessment_stage == "submit":
            if submit is None:
                return PlannerDecision(kind="abort", reason="synthetic_submit_control_not_visible")
            decision = self._move_then_click(
                purpose="submit synthetic answer",
                line=submit,
                history=history,
                click_reason="Submit the locally grounded synthetic answer.",
            )
            if decision.action is not None and decision.action.name == "left_click":
                self._arm_assessment_transition(
                    decision,
                    verified_stage="awaiting_result",
                    retry_stage="submit",
                )
            return decision

        if self._assessment_stage == "type":
            answer = self._grounded_text_answer(self._question(lines))
            if answer is None:
                return PlannerDecision(kind="abort", reason="typed_answer_not_grounded_in_visible_lesson")
            decision = PlannerDecision(
                kind="action",
                reason="Type the lesson-grounded response into the synthetic assessment field.",
                action=GuiAction(
                    "type_text",
                    {"text": answer, "text_class": "assessment_answer", "interval": 0.04},
                ),
                expected=ObservationPredicate("screen_changed"),
            )
            self._arm_assessment_transition(
                decision,
                verified_stage="submit",
                retry_stage="abort_unverified_type",
            )
            return decision

        option = self._best_option(lines)
        if option is not None:
            cache_candidate = self._cacheable_grounded_option(
                observation,
                question=question,
                option=option,
            )
            if cache_candidate is None:
                self._pending_click = None
                return PlannerDecision(
                    kind="abort",
                    reason="grounded_option_cache_binding_unavailable",
                )
            decision = self._move_then_click(
                purpose="grounded synthetic option",
                line=_grounded_option_target_line(option),
                history=history,
                click_reason="Select the option with the strongest overlap to the visible lesson.",
                click_expected=ObservationPredicate(
                    "vision_contains",
                    "submit_synthetic_answer",
                ),
            )
            if decision.action is not None:
                if decision.action.name == "move_mouse" and question:
                    self._pending_grounded_option = cache_candidate
                elif decision.action.name == "left_click":
                    self._arm_assessment_transition(
                        decision,
                        verified_stage="submit",
                        retry_stage="choose",
                        clear_grounded_option_on_verified=True,
                    )
            return decision

        typed_label = _line_for_phrases(lines, ("Type your answer", "Enter your answer"))
        if typed_label is not None:
            input_line = _OCRLine(
                text="synthetic typed answer field",
                tokens=typed_label.tokens,
                left=typed_label.left,
                top=typed_label.bottom + 8,
                right=typed_label.right,
                bottom=typed_label.bottom + max(36, typed_label.bottom - typed_label.top),
            )
            decision = self._move_then_click(
                purpose="synthetic answer field",
                line=input_line,
                history=history,
                click_reason="Focus the visible synthetic assessment answer field.",
            )
            if decision.action is not None and decision.action.name == "left_click":
                self._arm_assessment_transition(
                    decision,
                    verified_stage="type",
                    retry_stage="choose",
                )
            return decision
        return PlannerDecision(kind="abort", reason="assessment_answer_not_grounded_in_visible_lesson")

    def _plan_course_complete(
        self,
        lines: Sequence[_OCRLine],
        screen_text: str,
        history: Sequence[RuntimeTransition],
        vision_candidates: Sequence[_VisionControlCandidate],
    ) -> PlannerDecision:
        downloaded = _contains(screen_text, "certificate generated") or _contains(
            screen_text, "generated for"
        )
        if downloaded:
            control = _line_for_phrases(lines, ("Return to course inbox", "Return to inbox"))
            if control is None:
                control = _vision_control_line(
                    vision_candidates,
                    label="return_to_course_inbox",
                    unknown_policy="last",
                )
            purpose = "return to course inbox"
            click_reason = "Return to the local inbox after the visible certificate receipt."
        else:
            control = _line_for_phrases(
                lines,
                ("Download synthetic test certificate", "Download test certificate"),
            )
            if control is None:
                control = _vision_control_line(
                    vision_candidates,
                    label="download_synthetic_certificate",
                    unknown_policy="unique",
                )
            purpose = "download synthetic test certificate"
            click_reason = "Download the visible watermarked synthetic test certificate."
        if control is None:
            return PlannerDecision(kind="abort", reason=f"{purpose.replace(' ', '_')}_control_not_visible")
        return self._move_then_click(
            purpose=purpose,
            line=control,
            history=history,
            click_reason=click_reason,
        )

    def plan(
        self,
        _goal: str,
        observation: ScreenObservation,
        history: Sequence[RuntimeTransition],
    ) -> PlannerDecision:
        """Return exactly one local GUI action or a fail-closed terminal decision."""

        lines = _ocr_lines(observation)
        screen_text = _screen_text(lines)
        human_gate = self._human_gate(screen_text)
        if human_gate:
            return PlannerDecision(
                kind="human_required",
                reason=f"The visible screen requires a non-delegable {human_gate} gate.",
                human_gate=human_gate,
            )

        screen = self._classify(screen_text, history)
        self._enter_screen(screen)
        vision_candidates = _vision_control_candidates(observation)
        if screen == "final":
            return PlannerDecision(
                kind="complete",
                reason="The exact OCR-bound CourseOps 21 completion marker is visible.",
                success_predicate=ObservationPredicate(
                    "ocr_contains",
                    COURSEOPS_21_COMPLETION_MARKER,
                ),
            )
        if screen == "welcome":
            return self._plan_welcome(lines, history, vision_candidates)
        if screen == "inbox":
            return self._plan_inbox(lines, history, vision_candidates)
        if screen == "lesson":
            return self._plan_lesson(lines, history, vision_candidates)
        if screen == "assessment":
            return self._plan_assessment(
                observation,
                lines,
                screen_text,
                history,
                vision_candidates,
            )
        if screen == "course_complete":
            return self._plan_course_complete(lines, screen_text, history, vision_candidates)
        return PlannerDecision(kind="abort", reason="courseops_screen_state_unknown_or_ambiguous")


__all__ = [
    "COURSEOPS_21_COMPLETION_MARKER",
    "CourseOps21Planner",
    "CourseOps21PlannerError",
]
