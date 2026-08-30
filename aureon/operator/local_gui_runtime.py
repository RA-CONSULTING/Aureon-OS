"""Bounded local GUI observe-plan-act-verify runtime.

There is intentionally no concrete executor in this module. A governed action
gateway must be injected by the caller. The runtime executes exactly one action,
captures a fresh observation, and verifies the stated predicate before asking the
local-only planner for another action.
"""

from __future__ import annotations

import hashlib
import json
import math
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Protocol, Sequence, TypeGuard, cast, runtime_checkable

from aureon.operator.local_gui_observer import (
    GatewayObservationRejectedError,
    ScreenObservation,
)


class ActionValidationError(ValueError):
    """Raised when a planner proposes an action outside the strict schema."""


ACTION_NAMES = frozenset(
    {
        "move_mouse",
        "left_click",
        "right_click",
        "double_click",
        "type_text",
        "press_key",
        "hotkey",
        "scroll",
        "wait",
    }
)
TEXT_CLASSES = frozenset({"ordinary", "personal_data", "credential", "assessment_answer"})
HUMAN_GATES = frozenset(
    {
        "captcha",
        "mfa",
        "identity_attestation",
        "certification_assessment",
        "authorization",
        "other",
    }
)
PAUSE_KINDS = frozenset(
    {
        "authorization_prerequisite",
        "captcha",
        "identity_prerequisite",
        "login",
        "mfa",
    }
)
DECISION_KINDS = frozenset({"action", "complete", "pause", "human_required", "abort"})
PREDICATE_KINDS = frozenset(
    {
        "screen_changed",
        "screen_unchanged",
        "observation_fresh",
        "ocr_contains",
        "ocr_absent",
        "vision_contains",
    }
)
SEMANTIC_SUCCESS_PREDICATES = frozenset({"ocr_contains", "vision_contains"})
ACTION_DISPATCH_STATES = frozenset({"not_dispatched", "dispatched", "ambiguous"})
RETRYABLE_PRE_DISPATCH_ACTION_CODES = frozenset({"gateway_stale_source_frame"})

_NAMED_KEYS = frozenset(
    {
        "enter",
        "return",
        "tab",
        "escape",
        "esc",
        "space",
        "backspace",
        "delete",
        "home",
        "end",
        "pageup",
        "pagedown",
        "up",
        "down",
        "left",
        "right",
        "insert",
        "ctrl",
        "control",
        "alt",
        "shift",
        "win",
        "command",
        "capslock",
    }
    | {f"f{i}" for i in range(1, 25)}
)


def _is_number(value: object) -> TypeGuard[int | float]:
    return not isinstance(value, bool) and isinstance(value, (int, float))


def _valid_key(value: object) -> bool:
    if not isinstance(value, str):
        return False
    key = value.strip().lower()
    return (len(key) == 1 and key.isascii() and key.isalnum()) or key in _NAMED_KEYS


@dataclass(frozen=True)
class GuiAction:
    """One allowlisted GUI action. Coordinates are always explicit."""

    name: str
    params: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.name not in ACTION_NAMES:
            raise ActionValidationError(f"action_not_allowlisted:{self.name}")
        if not isinstance(self.params, Mapping):
            raise ActionValidationError("action params must be a mapping")
        normalized = dict(self.params)
        self._validate_schema(normalized)
        object.__setattr__(self, "params", normalized)

    def _validate_schema(self, params: dict[str, object]) -> None:
        schemas: dict[str, tuple[set[str], set[str]]] = {
            "move_mouse": ({"x", "y"}, {"duration"}),
            "left_click": ({"x", "y"}, set()),
            "right_click": ({"x", "y"}, set()),
            "double_click": ({"x", "y"}, set()),
            "type_text": ({"text", "text_class"}, {"interval"}),
            "press_key": ({"key"}, set()),
            "hotkey": ({"keys"}, set()),
            "scroll": ({"x", "y", "clicks"}, set()),
            "wait": ({"seconds"}, set()),
        }
        required, optional = schemas[self.name]
        keys = set(params)
        missing = required - keys
        extras = keys - required - optional
        if missing:
            raise ActionValidationError(f"missing_action_params:{','.join(sorted(missing))}")
        if extras:
            raise ActionValidationError(f"unexpected_action_params:{','.join(sorted(extras))}")

        if self.name in {"move_mouse", "left_click", "right_click", "double_click", "scroll"}:
            for key in ("x", "y"):
                if isinstance(params[key], bool) or not isinstance(params[key], int):
                    raise ActionValidationError(f"{key}_must_be_integer")
        if (
            self.name == "move_mouse"
            and "duration" in params
            and (
                not _is_number(params["duration"])
                or not 0.0 <= float(params["duration"]) <= 2.0
            )
        ):
            raise ActionValidationError("duration_out_of_range")
        if self.name == "type_text":
            text = params["text"]
            text_class = params["text_class"]
            if not isinstance(text, str) or not text or len(text) > 4096:
                raise ActionValidationError("text_must_be_1_to_4096_characters")
            if text_class not in TEXT_CLASSES:
                raise ActionValidationError("invalid_text_class")
            if "interval" in params and (
                not _is_number(params["interval"])
                or not 0.0 <= float(params["interval"]) <= 0.5
            ):
                raise ActionValidationError("interval_out_of_range")
        if self.name == "press_key" and not _valid_key(params["key"]):
            raise ActionValidationError("invalid_key")
        if self.name == "hotkey":
            keys_value = params["keys"]
            if not isinstance(keys_value, (list, tuple)) or not 2 <= len(keys_value) <= 4:
                raise ActionValidationError("hotkey_requires_2_to_4_keys")
            if not all(_valid_key(key) for key in keys_value):
                raise ActionValidationError("invalid_hotkey_key")
        if self.name == "scroll":
            clicks = params["clicks"]
            if isinstance(clicks, bool) or not isinstance(clicks, int) or clicks == 0 or abs(clicks) > 20:
                raise ActionValidationError("scroll_clicks_out_of_range")
        if self.name == "wait":
            seconds = params["seconds"]
            if not _is_number(seconds) or not 0.0 <= float(seconds) <= 10.0:
                raise ActionValidationError("wait_seconds_out_of_range")

    def validate_for_screen(self, observation: ScreenObservation) -> None:
        if self.name not in {"move_mouse", "left_click", "right_click", "double_click", "scroll"}:
            return
        x = cast(int, self.params["x"])
        y = cast(int, self.params["y"])
        if not 0 <= x < observation.width or not 0 <= y < observation.height:
            raise ActionValidationError("coordinates_outside_observation")

    def signature(self) -> str:
        encoded = json.dumps(
            {"name": self.name, "params": dict(self.params)},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def to_dict(self) -> dict[str, object]:
        params = dict(self.params)
        if self.name == "type_text":
            text = str(params.pop("text", ""))
            params["text"] = "[REDACTED:TYPED_TEXT]"
            params["text_length"] = len(text)
        return {"name": self.name, "params": params}


@dataclass(frozen=True)
class ObservationPredicate:
    """A deterministic post-action or completion predicate."""

    kind: str
    value: str = ""

    def __post_init__(self) -> None:
        if self.kind not in PREDICATE_KINDS:
            raise ValueError(f"predicate_not_allowlisted:{self.kind}")
        if self.kind in {"ocr_contains", "ocr_absent", "vision_contains"} and not self.value.strip():
            raise ValueError(f"predicate_{self.kind}_requires_value")
        if self.kind not in {"ocr_contains", "ocr_absent", "vision_contains"} and self.value:
            raise ValueError(f"predicate_{self.kind}_does_not_accept_value")

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "value": self.value}


@dataclass(frozen=True)
class PlannerDecision:
    """Strict structured output expected from the injected local planner."""

    kind: str
    reason: str
    action: GuiAction | None = None
    expected: ObservationPredicate | None = None
    success_predicate: ObservationPredicate | None = None
    human_gate: str = ""
    pause_kind: str = ""
    scorm_coherence: object | None = None
    action_authorization: object | None = None

    def __post_init__(self) -> None:
        if self.kind not in DECISION_KINDS:
            raise ValueError(f"decision_not_allowlisted:{self.kind}")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("decision reason is required")
        if self.scorm_coherence is not None:
            from aureon.operator.hnc_scorm_coherence import (
                SCORMActionDecision,
                SCORMPreflightDecision,
            )

            if not isinstance(
                self.scorm_coherence,
                (SCORMPreflightDecision, SCORMActionDecision),
            ):
                raise TypeError(
                    "scorm_coherence must be a preflight or action decision"
                )
        if self.action_authorization is not None:
            from aureon.operator.local_gui_scorm_authority import (
                SCORMActionAuthorization,
            )

            if not isinstance(self.action_authorization, SCORMActionAuthorization):
                raise TypeError(
                    "action_authorization must be SCORMActionAuthorization"
                )
            if self.scorm_coherence is None:
                raise ValueError("SCORM action authorization requires coherence evidence")
            if self.scorm_coherence != self.action_authorization.decision:
                raise ValueError("SCORM action authorization decision mismatch")
        if self.kind == "action":
            if self.action is None or self.expected is None:
                raise ValueError("action decisions require action and expected predicate")
            if self.success_predicate is not None or self.human_gate or self.pause_kind:
                raise ValueError("action decision contains incompatible fields")
        elif self.kind == "complete":
            if self.success_predicate is None:
                raise ValueError("complete decisions require a success predicate")
            if self.success_predicate.kind not in SEMANTIC_SUCCESS_PREDICATES:
                raise ValueError("completion requires a semantic OCR or local-vision predicate")
            if (
                self.action is not None
                or self.expected is not None
                or self.human_gate
                or self.pause_kind
                or self.action_authorization is not None
            ):
                raise ValueError("complete decision contains incompatible fields")
        elif self.kind == "pause":
            if self.pause_kind not in PAUSE_KINDS:
                raise ValueError("pause decision needs a recognized pause kind")
            if (
                self.action is not None
                or self.expected is not None
                or self.success_predicate is not None
                or self.human_gate
                or self.action_authorization is not None
            ):
                raise ValueError("pause decision contains incompatible fields")
        elif self.kind == "human_required":
            if self.human_gate not in HUMAN_GATES:
                raise ValueError("human_required decision needs a recognized human gate")
            if (
                self.action is not None
                or self.expected is not None
                or self.success_predicate is not None
                or self.pause_kind
                or self.action_authorization is not None
            ):
                raise ValueError("human_required decision contains incompatible fields")
        elif (
            self.action is not None
            or self.expected is not None
            or self.success_predicate is not None
            or self.pause_kind
            or self.action_authorization is not None
        ):
            raise ValueError("abort decision contains incompatible fields")


@dataclass(frozen=True)
class ActionResult:
    """Normalized result returned by the injected governed executor."""

    ok: bool
    code: str
    details: Mapping[str, object] = field(default_factory=dict)
    dispatch_state: str = "ambiguous"

    def __post_init__(self) -> None:
        if not isinstance(self.ok, bool):
            raise TypeError("ActionResult.ok must be boolean")
        if not isinstance(self.code, str) or not self.code.strip():
            raise ValueError("ActionResult.code is required")
        if not isinstance(self.details, Mapping):
            raise TypeError("ActionResult.details must be a mapping")
        if self.dispatch_state not in ACTION_DISPATCH_STATES:
            raise ValueError("ActionResult.dispatch_state is invalid")
        object.__setattr__(self, "details", dict(self.details))

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "code": self.code,
            "details": dict(self.details),
            "dispatch_state": self.dispatch_state,
        }


@dataclass(frozen=True)
class RuntimeTransition:
    step: int
    before: ScreenObservation
    decision: PlannerDecision
    result: ActionResult
    after: ScreenObservation
    screen_changed: bool
    observation_fresh: bool
    verified: bool
    verification_reason: str
    before_stable_attempts: int = 2
    after_stable_attempts: int = 2
    after_stable: bool = True

    def __post_init__(self) -> None:
        for name in ("before_stable_attempts", "after_stable_attempts"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if not isinstance(self.after_stable, bool):
            raise TypeError("after_stable must be boolean")

    def to_dict(self) -> dict[str, object]:
        assert self.decision.action is not None
        assert self.decision.expected is not None
        return {
            "step": self.step,
            "before_observation_id": self.before.observation_id,
            "before_sha256": self.before.screenshot_sha256,
            "after_observation_id": self.after.observation_id,
            "after_sha256": self.after.screenshot_sha256,
            "action_source_observation_id": self.before.observation_id,
            "action_source_sha256": self.before.screenshot_sha256,
            "before_frame": self.before.receipt_dict(),
            "after_frame": self.after.receipt_dict(),
            "action": self.decision.action.to_dict(),
            "scorm_action_authorization": (
                cast(Any, self.decision.action_authorization).audit_dict()
                if self.decision.action_authorization is not None
                else None
            ),
            "scorm_coherence": (
                cast(Any, self.decision.scorm_coherence).to_dict()
                if self.decision.scorm_coherence is not None
                else None
            ),
            "expected": self.decision.expected.to_dict(),
            "result": self.result.to_dict(),
            "in_flight": bool(
                not self.verified
                and self.result.dispatch_state in {"dispatched", "ambiguous"}
            ),
            "screen_changed": self.screen_changed,
            "observation_fresh": self.observation_fresh,
            "verified": self.verified,
            "verification_reason": self.verification_reason,
            "settling": {
                "required_consecutive_equal_hashes": 2,
                "before_attempts": self.before_stable_attempts,
                "after_attempts": self.after_stable_attempts,
                "after_stable": self.after_stable,
            },
        }


@dataclass(frozen=True)
class RuntimeLimits:
    max_steps: int = 50
    max_retries_per_action: int = 2
    max_consecutive_unchanged: int = 4
    max_seconds: float = 900.0
    stable_frame_max_attempts: int = 6
    stable_frame_interval_seconds: float = 0.05

    def __post_init__(self) -> None:
        for name in ("max_steps", "max_consecutive_unchanged"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if (
            isinstance(self.max_retries_per_action, bool)
            or not isinstance(self.max_retries_per_action, int)
            or self.max_retries_per_action < 0
        ):
            raise ValueError("max_retries_per_action must be a non-negative integer")
        if (
            not _is_number(self.max_seconds)
            or not math.isfinite(float(self.max_seconds))
            or float(self.max_seconds) <= 0
        ):
            raise ValueError("max_seconds must be positive and finite")
        if (
            isinstance(self.stable_frame_max_attempts, bool)
            or not isinstance(self.stable_frame_max_attempts, int)
            or self.stable_frame_max_attempts < 2
            or self.stable_frame_max_attempts > 100
        ):
            raise ValueError("stable_frame_max_attempts must be between 2 and 100")
        if (
            not _is_number(self.stable_frame_interval_seconds)
            or not math.isfinite(float(self.stable_frame_interval_seconds))
            or not 0.0 <= float(self.stable_frame_interval_seconds) <= 10.0
        ):
            raise ValueError("stable_frame_interval_seconds must be finite and between 0 and 10")


@dataclass(frozen=True)
class RuntimeResult:
    status: str
    success: bool
    reason: str
    action_count: int
    verified_changed_transitions: int
    final_observation: ScreenObservation | None
    transitions: tuple[RuntimeTransition, ...]
    human_gate: str = ""
    success_predicate: ObservationPredicate | None = None
    pause_kind: str = ""
    pause_receipt_sha256: str = ""
    terminal_decision: PlannerDecision | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "success": self.success,
            "reason": self.reason,
            "action_count": self.action_count,
            "verified_changed_transitions": self.verified_changed_transitions,
            "final_observation": self.final_observation.to_dict() if self.final_observation else None,
            "transitions": [transition.to_dict() for transition in self.transitions],
            "human_gate": self.human_gate,
            "success_predicate": self.success_predicate.to_dict() if self.success_predicate else None,
            "pause_kind": self.pause_kind,
            "pause_receipt_sha256": self.pause_receipt_sha256,
        }


@runtime_checkable
class Observer(Protocol):
    def observe(self) -> ScreenObservation:
        """Return a fresh observation of the current desktop."""


@runtime_checkable
class LocalPlanner(Protocol):
    @property
    def locality(self) -> str:
        """Return exactly ``local``. Any other value is rejected."""

    def plan(
        self,
        goal: str,
        observation: ScreenObservation,
        history: Sequence[RuntimeTransition],
    ) -> PlannerDecision:
        """Propose one action or one terminal decision."""


@runtime_checkable
class Executor(Protocol):
    def execute(
        self,
        action: GuiAction,
        *,
        source_observation: ScreenObservation | None = None,
        action_authorization: object | None = None,
    ) -> ActionResult:
        """Execute one action, CAS-bound to its exact stable source observation."""


@runtime_checkable
class RuntimeEventSink(Protocol):
    def record_transition(self, record: Mapping[str, object]) -> object:
        """Persist one redacted transition record."""


def evaluate_predicate(
    predicate: ObservationPredicate,
    *,
    before: ScreenObservation,
    after: ScreenObservation,
) -> bool:
    """Evaluate an allowlisted predicate without model judgment."""

    changed = before.screenshot_sha256 != after.screenshot_sha256
    if predicate.kind == "screen_changed":
        return changed
    if predicate.kind == "screen_unchanged":
        return not changed
    if predicate.kind == "observation_fresh":
        return after.observation_id != before.observation_id and after.sequence > before.sequence
    needle = predicate.value.casefold()
    if predicate.kind == "ocr_contains":
        return needle in after.ocr_text.casefold()
    if predicate.kind == "ocr_absent":
        return needle not in after.ocr_text.casefold()
    if predicate.kind == "vision_contains":
        return needle in after.vision_text.casefold()
    return False


def detect_human_gate(observation: ScreenObservation) -> str:
    """Detect obvious non-delegable gates before the planner can act on them."""

    text = f"{observation.ocr_text} {observation.vision_text}".casefold()
    patterns = (
        ("captcha", ("captcha", "verify you are human", "prove you are human")),
        (
            "identity_attestation",
            (
                "identity attestation",
                "confirm your identity",
                "i certify that i am",
                "i attest that i am",
            ),
        ),
        (
            "mfa",
            (
                "multi-factor authentication",
                "two-factor authentication",
                "authenticator code",
                "verification code",
            ),
        ),
        (
            "certification_assessment",
            (
                "certification quiz",
                "certification exam",
                "knowledge check",
                "knowledge-check",
                "assessment answer",
                "assessment-answer",
                "assessment question",
                "final assessment",
                "graded assessment",
                "quiz question",
                "exam question",
            ),
        ),
    )
    for gate, phrases in patterns:
        if any(phrase in text for phrase in phrases):
            return gate
    return ""


@dataclass(frozen=True)
class _StableFrameSample:
    observation: ScreenObservation
    attempts: int


class _StableFrameUnavailable(RuntimeError):
    def __init__(
        self,
        *,
        attempts: int,
        last_observation: ScreenObservation | None,
    ) -> None:
        super().__init__("two consecutive equal frame hashes were not observed")
        self.attempts = attempts
        self.last_observation = last_observation


def _stable_frame_key(observation: ScreenObservation) -> tuple[object, ...]:
    """Return the immutable visual/telemetry state required to settle a frame."""

    rect = observation.window_rect
    rect_key = None if rect is None else (rect.left, rect.top, rect.width, rect.height)
    visual_key: tuple[object, ...]
    if observation.stability_sha256 is not None:
        excluded_media = None
        if (
            observation.stability_profile
            == "aureon-scorm-player-stability-pixels-v1"
            and rect is not None
        ):
            from aureon.operator.scorm_player_stability import dynamic_media_region

            excluded_media = dynamic_media_region(
                rect.left, rect.top, rect.width, rect.height
            )
        ocr_key = tuple(
            (
                token.text,
                token.x,
                token.y,
                token.width,
                token.height,
                token.confidence,
            )
            for token in observation.ocr_tokens
            if excluded_media is None
            or not (
                excluded_media[0] <= token.x + token.width // 2 < excluded_media[2]
                and excluded_media[1]
                <= token.y + token.height // 2
                < excluded_media[3]
            )
        )
        visual_key = (
            "canonical_stability",
            observation.stability_profile,
            observation.stability_sha256,
            ocr_key,
            observation.vision_text,
        )
    else:
        visual_key = ("raw_screenshot", observation.screenshot_sha256)
    return (
        visual_key,
        observation.width,
        observation.height,
        observation.mime_type,
        observation.window_handle,
        observation.window_process_id,
        observation.window_title_sha256,
        rect_key,
        observation.dpi_x,
        observation.dpi_y,
    )


def _retryable_pre_dispatch_failure(result: ActionResult) -> bool:
    """Return true only for an exact, executor-proven no-dispatch outcome."""

    return (
        result.ok is False
        and result.dispatch_state == "not_dispatched"
        and result.code in RETRYABLE_PRE_DISPATCH_ACTION_CODES
    )


class LocalGUIRuntime:
    """Execute a bounded, evidence-producing local GUI control loop."""

    def __init__(
        self,
        observer: Observer,
        planner: LocalPlanner,
        executor: Executor,
        *,
        limits: RuntimeLimits | None = None,
        event_sink: RuntimeEventSink | None = None,
        emergency_stop: Callable[[], bool] | None = None,
        human_gate_authorizer: Callable[[ScreenObservation, str], bool] | None = None,
        planner_handles_human_gates: bool = False,
        resume_validator: Callable[[ScreenObservation], bool] | None = None,
        target_window_mismatch_recovery: Callable[[], bool] | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], object] = time.sleep,
    ) -> None:
        if getattr(planner, "locality", "") != "local":
            raise ValueError("planner must declare locality='local'")
        self._observer = observer
        self._planner = planner
        self._executor = executor
        self._limits = limits or RuntimeLimits()
        self._event_sink = event_sink
        self._external_emergency_stop = emergency_stop
        self._human_gate_authorizer = human_gate_authorizer
        if not isinstance(planner_handles_human_gates, bool):
            raise TypeError("planner_handles_human_gates must be boolean")
        if resume_validator is not None and not callable(resume_validator):
            raise TypeError("resume_validator must be callable")
        if target_window_mismatch_recovery is not None and not callable(
            target_window_mismatch_recovery
        ):
            raise TypeError("target_window_mismatch_recovery must be callable")
        self._planner_handles_human_gates = planner_handles_human_gates
        self._resume_validator = resume_validator
        self._target_window_mismatch_recovery = target_window_mismatch_recovery
        self._monotonic = monotonic
        if not callable(sleeper):
            raise TypeError("sleeper must be callable")
        self._sleeper = sleeper
        self._stop_event = threading.Event()

    def request_emergency_stop(self) -> None:
        """Request termination before the next irreversible boundary."""

        self._stop_event.set()

    def _emergency_stopped(self) -> bool:
        if self._stop_event.is_set():
            return True
        if self._external_emergency_stop is None:
            return False
        try:
            return bool(self._external_emergency_stop())
        except Exception:  # noqa: BLE001 - a broken stop signal fails closed
            return True

    def _human_gate_authorized(
        self,
        observation: ScreenObservation,
        gate: str,
    ) -> bool:
        """Permit only an independently authorized synthetic assessment gate."""

        if gate != "certification_assessment" or self._human_gate_authorizer is None:
            return False
        try:
            return self._human_gate_authorizer(observation, gate) is True
        except Exception:  # noqa: BLE001 - authority failures must fail closed
            return False

    def _observe_stable(self) -> _StableFrameSample:
        """Return the second of two fresh, consecutive equal ScreenReel frames."""

        previous: ScreenObservation | None = None
        last: ScreenObservation | None = None
        attempts = 0
        recovery_attempted = False
        for attempts in range(1, self._limits.stable_frame_max_attempts + 1):
            try:
                observed = self._observer.observe()
            except GatewayObservationRejectedError as exc:
                if (
                    exc.reason != "target_window_mismatch"
                    or attempts >= self._limits.stable_frame_max_attempts
                ):
                    raise
                if (
                    self._target_window_mismatch_recovery is not None
                    and not recovery_attempted
                ):
                    recovery_attempted = True
                    try:
                        self._target_window_mismatch_recovery()
                    except Exception:
                        # Recovery is an optional, governed SCORM-only hook.
                        # Its failure never broadens the existing bounded retry.
                        pass
                # A foreground loss breaks consecutiveness. Two new, bound
                # observations must settle after it; no focus or rebind occurs.
                previous = None
                interval = float(self._limits.stable_frame_interval_seconds)
                if interval:
                    self._sleeper(interval)
                continue
            if not isinstance(observed, ScreenObservation):
                raise TypeError("observer returned a non-ScreenObservation value")
            last = observed
            if (
                previous is not None
                and observed.sequence > previous.sequence
                and observed.observation_id != previous.observation_id
                and _stable_frame_key(observed) == _stable_frame_key(previous)
            ):
                return _StableFrameSample(observation=observed, attempts=attempts)
            previous = observed
            if attempts < self._limits.stable_frame_max_attempts:
                interval = float(self._limits.stable_frame_interval_seconds)
                if interval:
                    self._sleeper(interval)
        raise _StableFrameUnavailable(attempts=attempts, last_observation=last)

    def run(self, goal: str) -> RuntimeResult:
        if not isinstance(goal, str) or not goal.strip():
            raise ValueError("goal is required")

        transitions: list[RuntimeTransition] = []
        action_count = 0
        verified_changed = 0
        consecutive_unchanged = 0
        failed_attempts: dict[str, int] = {}
        started = self._monotonic()
        current: ScreenObservation | None = None
        current_stable_attempts = 0

        if self._emergency_stopped():
            return self._result("emergency_stopped", False, "emergency stop was active", 0, 0, None, transitions)

        try:
            initial_sample = self._observe_stable()
            current = initial_sample.observation
            current_stable_attempts = initial_sample.attempts
        except _StableFrameUnavailable as exc:
            return self._result(
                "unstable_initial_frame",
                False,
                "initial screen did not produce two consecutive equal frame hashes",
                0,
                0,
                exc.last_observation,
                transitions,
            )
        except Exception as exc:  # noqa: BLE001 - observer boundary
            return self._result(
                "observer_error", False, f"initial observation failed: {type(exc).__name__}: {exc}",
                0, 0, None, transitions,
            )

        if self._resume_validator is not None:
            try:
                resume_valid = self._resume_validator(current)
            except Exception as exc:  # noqa: BLE001 - resumable checkpoint boundary
                return self._result(
                    "resume_rejected",
                    False,
                    f"resume checkpoint validation failed: {type(exc).__name__}: {exc}",
                    0,
                    0,
                    current,
                    transitions,
                )
            if resume_valid is not True:
                return self._result(
                    "resume_rejected",
                    False,
                    "resume checkpoint validation did not return exact approval",
                    0,
                    0,
                    current,
                    transitions,
                )

        initial = current
        while action_count < self._limits.max_steps:
            if self._emergency_stopped():
                return self._result(
                    "emergency_stopped", False, "emergency stop was requested", action_count,
                    verified_changed, current, transitions,
                )
            if self._monotonic() - started >= self._limits.max_seconds:
                return self._result(
                    "max_time", False, "runtime time limit reached", action_count,
                    verified_changed, current, transitions,
                )

            if not self._planner_handles_human_gates:
                human_gate = detect_human_gate(current)
                if human_gate and not self._human_gate_authorized(current, human_gate):
                    reason = f"detected human-only gate: {human_gate}"
                    terminal = PlannerDecision(
                        kind="human_required",
                        reason=reason,
                        human_gate=human_gate,
                    )
                    return self._result(
                        "human_required",
                        False,
                        reason,
                        action_count,
                        verified_changed,
                        current,
                        transitions,
                        human_gate=human_gate,
                        terminal_decision=terminal,
                    )

            try:
                decision = self._planner.plan(goal, current, tuple(transitions))
            except Exception as exc:  # noqa: BLE001 - planner boundary
                return self._result(
                    "planner_error", False, f"planner failed: {type(exc).__name__}: {exc}",
                    action_count, verified_changed, current, transitions,
                )
            if self._emergency_stopped():
                return self._result(
                    "emergency_stopped", False, "emergency stop was requested after planning",
                    action_count, verified_changed, current, transitions,
                )
            if self._monotonic() - started >= self._limits.max_seconds:
                return self._result(
                    "max_time", False, "runtime time limit reached after planning",
                    action_count, verified_changed, current, transitions,
                )
            if not isinstance(decision, PlannerDecision):
                return self._result(
                    "planner_error", False, "planner returned a non-PlannerDecision value",
                    action_count, verified_changed, current, transitions,
                )

            if decision.kind == "human_required":
                return self._result(
                    "human_required", False, decision.reason, action_count, verified_changed,
                    current, transitions, human_gate=decision.human_gate,
                    terminal_decision=decision,
                )
            if decision.kind == "pause":
                return self._result(
                    "paused",
                    False,
                    decision.reason,
                    action_count,
                    verified_changed,
                    current,
                    transitions,
                    pause_kind=decision.pause_kind,
                    terminal_decision=decision,
                )
            if decision.kind == "abort":
                return self._result(
                    "aborted", False, decision.reason, action_count, verified_changed,
                    current, transitions, terminal_decision=decision,
                )
            if decision.kind == "complete":
                assert decision.success_predicate is not None
                predicate_ok = evaluate_predicate(
                    decision.success_predicate,
                    before=initial,
                    after=current,
                )
                if not predicate_ok:
                    return self._result(
                        "completion_rejected", False, "stated success predicate is not satisfied",
                        action_count, verified_changed, current, transitions,
                        success_predicate=decision.success_predicate,
                        terminal_decision=decision,
                    )
                if verified_changed <= 0:
                    return self._result(
                        "completion_rejected", False,
                        "no verified changed-state transition supports completion",
                        action_count, verified_changed, current, transitions,
                        success_predicate=decision.success_predicate,
                        terminal_decision=decision,
                    )
                return self._result(
                    "completed", True, decision.reason, action_count, verified_changed,
                    current, transitions, success_predicate=decision.success_predicate,
                    terminal_decision=decision,
                )

            assert decision.action is not None
            assert decision.expected is not None
            try:
                decision.action.validate_for_screen(current)
            except ActionValidationError as exc:
                return self._result(
                    "invalid_action", False, str(exc), action_count, verified_changed,
                    current, transitions,
                )

            if self._emergency_stopped():
                return self._result(
                    "emergency_stopped", False, "emergency stop was requested before action",
                    action_count, verified_changed, current, transitions,
                )
            if self._monotonic() - started >= self._limits.max_seconds:
                return self._result(
                    "max_time", False, "runtime time limit reached before action",
                    action_count, verified_changed, current, transitions,
                )

            before = current
            before_stable_attempts = current_stable_attempts
            try:
                if decision.action_authorization is not None:
                    action_result = self._executor.execute(
                        decision.action,
                        source_observation=before,
                        action_authorization=decision.action_authorization,
                    )
                elif decision.action.name == "wait":
                    action_result = self._executor.execute(decision.action)
                else:
                    action_result = self._executor.execute(
                        decision.action,
                        source_observation=before,
                    )
                if not isinstance(action_result, ActionResult):
                    raise TypeError("executor returned a non-ActionResult value")
            except Exception as exc:  # noqa: BLE001 - governed executor boundary
                action_result = ActionResult(
                    ok=False,
                    code="executor_exception",
                    details={"error_type": type(exc).__name__},
                )
            action_count += 1

            try:
                after_sample = self._observe_stable()
                after = after_sample.observation
                after_stable_attempts = after_sample.attempts
            except _StableFrameUnavailable as exc:
                after = exc.last_observation or before
                observation_fresh = (
                    after.observation_id != before.observation_id
                    and after.sequence > before.sequence
                )
                screen_changed = after.screenshot_sha256 != before.screenshot_sha256
                transition = RuntimeTransition(
                    step=action_count,
                    before=before,
                    decision=decision,
                    result=action_result,
                    after=after,
                    screen_changed=screen_changed,
                    observation_fresh=observation_fresh,
                    verified=False,
                    verification_reason="stable_frame_not_reached",
                    before_stable_attempts=before_stable_attempts,
                    after_stable_attempts=exc.attempts,
                    after_stable=False,
                )
                transitions.append(transition)
                if self._event_sink is not None:
                    try:
                        self._event_sink.record_transition(transition.to_dict())
                    except Exception as sink_exc:  # noqa: BLE001 - evidence fails closed
                        return self._result(
                            "evidence_error",
                            False,
                            "unstable transition evidence could not be persisted: "
                            f"{type(sink_exc).__name__}: {sink_exc}",
                            action_count,
                            verified_changed,
                            after,
                            transitions,
                        )
                return self._result(
                    "unstable_post_action_frame",
                    False,
                    "post-action screen did not produce two consecutive equal frame hashes",
                    action_count,
                    verified_changed,
                    after,
                    transitions,
                )
            except Exception as exc:  # noqa: BLE001 - post-action evidence must fail closed
                transition = RuntimeTransition(
                    step=action_count,
                    before=before,
                    decision=decision,
                    result=action_result,
                    after=before,
                    screen_changed=False,
                    observation_fresh=False,
                    verified=False,
                    verification_reason="post_action_observer_failed",
                    before_stable_attempts=before_stable_attempts,
                    after_stable_attempts=1,
                    after_stable=False,
                )
                transitions.append(transition)
                if self._event_sink is not None:
                    try:
                        self._event_sink.record_transition(transition.to_dict())
                    except Exception as sink_exc:  # noqa: BLE001 - evidence fails closed
                        return self._result(
                            "evidence_error",
                            False,
                            "post-action observer failure receipt could not be "
                            f"persisted: {type(sink_exc).__name__}: {sink_exc}",
                            action_count,
                            verified_changed,
                            before,
                            transitions,
                        )
                return self._result(
                    "observer_error", False,
                    f"post-action observation failed: {type(exc).__name__}: {exc}",
                    action_count, verified_changed, before, transitions,
                )

            observation_fresh = (
                after.observation_id != before.observation_id and after.sequence > before.sequence
            )
            screen_changed = after.screenshot_sha256 != before.screenshot_sha256
            predicate_ok = evaluate_predicate(decision.expected, before=before, after=after)
            post_dispatch_handoff = (
                action_result.code == "gateway_executed_handoff_required"
            )
            verified = bool(action_result.ok and observation_fresh and predicate_ok)
            if not action_result.ok:
                verification_reason = f"executor_failed:{action_result.code}"
            elif not observation_fresh:
                verification_reason = "fresh_observation_missing"
            elif not predicate_ok:
                verification_reason = f"predicate_failed:{decision.expected.kind}"
            elif post_dispatch_handoff:
                verification_reason = "verified_after_governed_handoff"
            else:
                verification_reason = "verified"

            transition = RuntimeTransition(
                step=action_count,
                before=before,
                decision=decision,
                result=action_result,
                after=after,
                screen_changed=screen_changed,
                observation_fresh=observation_fresh,
                verified=verified,
                verification_reason=verification_reason,
                before_stable_attempts=before_stable_attempts,
                after_stable_attempts=after_stable_attempts,
            )
            transitions.append(transition)

            if self._event_sink is not None:
                try:
                    self._event_sink.record_transition(transition.to_dict())
                except Exception as exc:  # noqa: BLE001 - missing evidence fails closed
                    return self._result(
                        "evidence_error", False,
                        f"transition evidence could not be persisted: {type(exc).__name__}: {exc}",
                        action_count, verified_changed, after, transitions,
                    )

            if action_result.code == "human_required_certification_assessment":
                reason = (
                    "governed executor requires a human for certification "
                    "assessment content"
                )
                terminal = PlannerDecision(
                    kind="human_required",
                    reason=reason,
                    human_gate="certification_assessment",
                )
                return self._result(
                    "human_required",
                    False,
                    reason,
                    action_count,
                    verified_changed,
                    after,
                    transitions,
                    human_gate="certification_assessment",
                    terminal_decision=terminal,
                )
            if action_result.code == "scorm_control_authorization_required":
                reason = "the exact SCORM control grant or window binding changed"
                terminal = PlannerDecision(
                    kind="pause",
                    reason=reason,
                    pause_kind="authorization_prerequisite",
                )
                return self._result(
                    "paused",
                    False,
                    reason,
                    action_count,
                    verified_changed,
                    after,
                    transitions,
                    pause_kind="authorization_prerequisite",
                    terminal_decision=terminal,
                )
            if post_dispatch_handoff and not verified:
                return self._result(
                    "post_dispatch_verification_failed",
                    False,
                    "a dispatched action changed the governed window but its "
                    "postcondition was not verified; refusing a duplicate retry",
                    action_count,
                    verified_changed,
                    after,
                    transitions,
                )
            if action_result.code in {
                "gateway_active_authorization_lease_required",
                "gateway_action_outside_lease_scope",
            }:
                reason = (
                    "governed executor requires authorization: "
                    f"{action_result.code}"
                )
                terminal = PlannerDecision(
                    kind="human_required",
                    reason=reason,
                    human_gate="authorization",
                )
                return self._result(
                    "human_required",
                    False,
                    reason,
                    action_count,
                    verified_changed,
                    after,
                    transitions,
                    human_gate="authorization",
                    terminal_decision=terminal,
                )
            if action_result.code == "gateway_emergency_stop_active":
                return self._result(
                    "emergency_stopped", False,
                    "governed executor reported an active emergency stop",
                    action_count, verified_changed, after, transitions,
                )

            retryable_pre_dispatch = _retryable_pre_dispatch_failure(action_result)
            if not verified and not retryable_pre_dispatch:
                if action_result.dispatch_state in {"dispatched", "ambiguous"}:
                    return self._result(
                        "post_dispatch_verification_failed",
                        False,
                        "the action was dispatched or its dispatch outcome is "
                        "ambiguous, and its postcondition was not verified; "
                        "refusing a duplicate redispatch",
                        action_count,
                        verified_changed,
                        after,
                        transitions,
                    )
                return self._result(
                    "action_rejected",
                    False,
                    "the executor proved no dispatch, but this failure is not "
                    "allowlisted for automatic replanning",
                    action_count,
                    verified_changed,
                    after,
                    transitions,
                )

            if verified and screen_changed:
                verified_changed += 1
            consecutive_unchanged = 0 if screen_changed else consecutive_unchanged + 1
            current = after
            current_stable_attempts = after_stable_attempts

            if consecutive_unchanged >= self._limits.max_consecutive_unchanged:
                return self._result(
                    "stalled", False, "screen remained unchanged across the bounded stall window",
                    action_count, verified_changed, current, transitions,
                )

            signature = decision.action.signature()
            if verified:
                failed_attempts.pop(signature, None)
            else:
                failed_attempts[signature] = failed_attempts.get(signature, 0) + 1
                allowed_attempts = 1 + self._limits.max_retries_per_action
                if failed_attempts[signature] >= allowed_attempts:
                    return self._result(
                        "retry_exhausted", False,
                        f"action verification failed after {failed_attempts[signature]} attempt(s)",
                        action_count, verified_changed, current, transitions,
                    )

        return self._result(
            "max_steps", False, "runtime action-step limit reached", action_count,
            verified_changed, current, transitions,
        )

    @staticmethod
    def _result(
        status: str,
        success: bool,
        reason: str,
        action_count: int,
        verified_changed: int,
        final_observation: ScreenObservation | None,
        transitions: Sequence[RuntimeTransition],
        *,
        human_gate: str = "",
        success_predicate: ObservationPredicate | None = None,
        pause_kind: str = "",
        pause_receipt_sha256: str = "",
        terminal_decision: PlannerDecision | None = None,
    ) -> RuntimeResult:
        return RuntimeResult(
            status=status,
            success=success,
            reason=reason,
            action_count=action_count,
            verified_changed_transitions=verified_changed,
            final_observation=final_observation,
            transitions=tuple(transitions),
            human_gate=human_gate,
            success_predicate=success_predicate,
            pause_kind=pause_kind,
            pause_receipt_sha256=pause_receipt_sha256,
            terminal_decision=terminal_decision,
        )


__all__ = [
    "ACTION_NAMES",
    "ActionResult",
    "ActionValidationError",
    "Executor",
    "GuiAction",
    "HUMAN_GATES",
    "LocalGUIRuntime",
    "LocalPlanner",
    "ObservationPredicate",
    "Observer",
    "PAUSE_KINDS",
    "PlannerDecision",
    "RuntimeEventSink",
    "RuntimeLimits",
    "RuntimeResult",
    "RuntimeTransition",
    "detect_human_gate",
    "evaluate_predicate",
]
