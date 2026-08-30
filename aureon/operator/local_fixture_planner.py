"""Hash-bound deterministic planner for Aureon's local course fixture only."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Mapping, Sequence

from aureon.operator.local_gui_observer import OCRToken, ScreenObservation
from aureon.operator.local_gui_runtime import (
    GuiAction,
    ObservationPredicate,
    PlannerDecision,
    RuntimeTransition,
    detect_human_gate,
)

LOCAL_FIXTURE_MANIFEST = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "fixtures"
    / "local_course_benchmark"
    / "benchmark_manifest.json"
)
LOCAL_FIXTURE_MANIFEST_SHA256 = "e5ee3d3eee2a2f53e139cf662d169cadb04e65bbdaccc00118ecf1026e37c0bf"
REQUIRED_GATEWAY_ACTIONS = frozenset({"move", "click", "scroll", "type", "press"})


class FixturePlannerError(ValueError):
    """Raised when the local fixture or its visible state is not exact."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalized_token(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.casefold())


class LocalFixturePlanner:
    """Drive only the checked-in provider-neutral sandbox through OCR."""

    locality = "local"

    def __init__(
        self,
        manifest_path: str | Path = LOCAL_FIXTURE_MANIFEST,
        *,
        expected_sha256: str = LOCAL_FIXTURE_MANIFEST_SHA256,
    ) -> None:
        path = Path(manifest_path).expanduser().resolve(strict=True)
        expected = str(expected_sha256 or "").strip().casefold()
        if not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise FixturePlannerError("fixture_manifest_expected_hash_invalid")
        actual = _sha256_file(path)
        if actual != expected:
            raise FixturePlannerError("fixture_manifest_hash_mismatch")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise FixturePlannerError("fixture_manifest_invalid_json") from exc
        self._validate_manifest(payload)
        self.manifest_path = path
        self.manifest_sha256 = actual
        self.practice_text = str(payload["practice_text"]["value"])
        self.success_marker = str(
            payload["sandbox_flow"][-1]["success_predicate"]["value"]
        )

    @staticmethod
    def _validate_manifest(payload: object) -> None:
        if not isinstance(payload, dict):
            raise FixturePlannerError("fixture_manifest_object_required")
        practice = payload.get("practice_text")
        flow = payload.get("sandbox_flow")
        gate = payload.get("certification_gate")
        if (
            payload.get("schema_version") != "aureon-local-course-benchmark-v1"
            or payload.get("benchmark_id") != "local-synthetic-course-v1"
            or payload.get("local_only") is not True
            or payload.get("network_policy") != "deny_all_external"
            or payload.get("provider_branding") is not False
            or payload.get("contains_real_assessment_content") is not False
            or not isinstance(practice, dict)
            or practice.get("text_class") != "ordinary"
            or practice.get("sensitivity") != "non_sensitive"
            or not isinstance(practice.get("value"), str)
            or not practice["value"]
            or not isinstance(flow, list)
            or len(flow) != 6
            or not isinstance(flow[-1], dict)
            or not isinstance(flow[-1].get("success_predicate"), dict)
            or flow[-1]["success_predicate"].get("kind") != "ocr_contains"
            or not isinstance(flow[-1]["success_predicate"].get("value"), str)
            or not isinstance(gate, dict)
            or gate.get("automation_must_not_submit") is not True
            or gate.get("text_class") != "assessment_answer"
            or not isinstance(gate.get("required_runtime_decision"), dict)
            or gate["required_runtime_decision"].get("human_gate")
            != "certification_assessment"
        ):
            raise FixturePlannerError("fixture_manifest_contract_invalid")
        practice_digest = hashlib.sha256(practice["value"].encode("utf-8")).hexdigest()
        if practice.get("sha256") != practice_digest:
            raise FixturePlannerError("fixture_practice_text_hash_mismatch")

    @staticmethod
    def _contains(observation: ScreenObservation, phrase: str) -> bool:
        return phrase.casefold() in observation.ocr_text.casefold()

    @staticmethod
    def _find_token(observation: ScreenObservation, word: str, *, lowest: bool = True) -> OCRToken:
        wanted = _normalized_token(word)
        matches = [token for token in observation.ocr_tokens if _normalized_token(token.text) == wanted]
        if not matches:
            raise FixturePlannerError(f"fixture_visible_target_missing:{wanted}")
        return max(matches, key=lambda token: token.y) if lowest else min(matches, key=lambda token: token.y)

    def _find_visible_anchor(
        self,
        observation: ScreenObservation,
        words: Sequence[str],
    ) -> OCRToken:
        matches: list[OCRToken] = []
        for word in words:
            try:
                matches.append(self._find_token(observation, word))
            except FixturePlannerError:
                continue
        if not matches:
            raise FixturePlannerError("fixture_lesson_anchor_missing")
        return max(matches, key=lambda token: token.y)

    @staticmethod
    def _center(token: OCRToken) -> tuple[int, int]:
        return token.x + max(1, token.width // 2), token.y + max(1, token.height // 2)

    def _token_or_fixture_offset(
        self,
        observation: ScreenObservation,
        *,
        target_word: str,
        anchor_word: str,
        offset_x: int,
        offset_y: int,
    ) -> tuple[int, int]:
        """Use OCR first, then a hash-bound fixture-relative control offset."""

        try:
            return self._center(self._find_token(observation, target_word))
        except FixturePlannerError:
            anchor_x, anchor_y = self._center(
                self._find_token(observation, anchor_word, lowest=False)
            )
            x = min(observation.width - 1, max(0, anchor_x + offset_x))
            y = min(observation.height - 1, max(0, anchor_y + offset_y))
            return x, y

    @staticmethod
    def _last_action(history: Sequence[RuntimeTransition]) -> GuiAction | None:
        if not history:
            return None
        return history[-1].decision.action

    @staticmethod
    def _has_action(history: Sequence[RuntimeTransition], name: str) -> bool:
        return any(item.decision.action is not None and item.decision.action.name == name for item in history)

    def _advance_lesson(
        self,
        *,
        x: int,
        y: int,
        history: Sequence[RuntimeTransition],
        reason: str,
    ) -> PlannerDecision:
        if self._has_action(history, "scroll"):
            action = GuiAction("press_key", {"key": "pagedown"})
        else:
            action = GuiAction("scroll", {"x": x, "y": y, "clicks": -20})
        return PlannerDecision(
            kind="action",
            reason=reason,
            action=action,
            expected=ObservationPredicate("screen_changed"),
        )

    @staticmethod
    def _same_coordinates(action: GuiAction | None, *, name: str, x: int, y: int) -> bool:
        return bool(
            action is not None
            and action.name == name
            and action.params.get("x") == x
            and action.params.get("y") == y
        )

    def _move_then_click(
        self,
        *,
        x: int,
        y: int,
        expected_phrase: str,
        history: Sequence[RuntimeTransition],
    ) -> PlannerDecision:
        if self._same_coordinates(self._last_action(history), name="move_mouse", x=x, y=y):
            return PlannerDecision(
                kind="action",
                reason="Activate the exact OCR-bound local fixture control.",
                action=GuiAction("left_click", {"x": x, "y": y}),
                expected=ObservationPredicate("ocr_contains", expected_phrase),
            )
        return PlannerDecision(
            kind="action",
            reason="Move visibly to the exact OCR-bound local fixture control.",
            action=GuiAction("move_mouse", {"x": x, "y": y, "duration": 0.25}),
            expected=ObservationPredicate("observation_fresh"),
        )

    def plan(
        self,
        _goal: str,
        observation: ScreenObservation,
        history: Sequence[RuntimeTransition],
    ) -> PlannerDecision:
        human_gate = detect_human_gate(observation)
        if human_gate:
            return PlannerDecision(
                kind="human_required",
                reason=f"The fixture exposed a human-only gate: {human_gate}",
                human_gate=human_gate,
            )
        if self._contains(observation, self.success_marker):
            return PlannerDecision(
                kind="complete",
                reason="The hash-bound fixture completion marker is visible.",
                success_predicate=ObservationPredicate("ocr_contains", self.success_marker),
            )

        try:
            if self._contains(observation, "Ready to begin"):
                # White-on-blue button text can be missed by Tesseract.  This
                # fallback is valid only because the fixture manifest and page
                # are checked-in, provider-neutral, and hash-bound.
                x, y = self._token_or_fixture_offset(
                    observation,
                    target_word="Start",
                    anchor_word="Ready",
                    offset_x=25,
                    offset_y=105,
                )
                return self._move_then_click(
                    x=x,
                    y=y,
                    expected_phrase="Practice lesson",
                    history=history,
                )

            lesson_visible = any(
                self._contains(observation, marker)
                for marker in (
                    "Practice lesson",
                    "Confirm the active window",
                    "Use bounded pointer",
                    "Read the screen again",
                    "End of synthetic lesson",
                )
            )
            if lesson_visible:
                if self._contains(observation, "End of synthetic lesson"):
                    end_token = self._find_token(observation, "End")
                    if end_token.y > 760:
                        x, y = self._center(end_token)
                        return self._advance_lesson(
                            x=x,
                            y=y,
                            history=history,
                            reason="Advance until the fixture continuation control is visibly in bounds.",
                        )
                    x, y = self._token_or_fixture_offset(
                        observation,
                        target_word="Next",
                        anchor_word="End",
                        offset_x=-240,
                        offset_y=80,
                    )
                    return self._move_then_click(
                        x=x,
                        y=y,
                        expected_phrase="Keyboard practice",
                        history=history,
                    )
                anchor = self._find_visible_anchor(
                    observation,
                    ("Practice", "Observe", "Act", "Verify"),
                )
                x, y = self._center(anchor)
                return self._advance_lesson(
                    x=x,
                    y=y,
                    history=history,
                    reason="Advance the local synthetic lesson toward its exact sentinel.",
                )

            if self._contains(observation, "Keyboard practice"):
                if self._contains(observation, "Practice phrase matched"):
                    x, y = self._center(self._find_token(observation, "Next"))
                    return self._move_then_click(
                        x=x,
                        y=y,
                        expected_phrase="Final sandbox checkpoint",
                        history=history,
                    )
                label = self._find_token(observation, "text", lowest=True)
                x = min(observation.width - 1, max(0, label.x + label.width // 2))
                y = min(observation.height - 1, max(0, label.y + label.height + 28))
                last_action = self._last_action(history)
                if self._same_coordinates(last_action, name="move_mouse", x=x, y=y):
                    return PlannerDecision(
                        kind="action",
                        reason="Focus the ordinary local practice field.",
                        action=GuiAction("left_click", {"x": x, "y": y}),
                        expected=ObservationPredicate("observation_fresh"),
                    )
                if self._same_coordinates(last_action, name="left_click", x=x, y=y):
                    return PlannerDecision(
                        kind="action",
                        reason="Enter the hash-bound non-sensitive fixture phrase.",
                        action=GuiAction(
                            "type_text",
                            {
                                "text": self.practice_text,
                                "text_class": "ordinary",
                                "interval": 0.04,
                            },
                        ),
                        expected=ObservationPredicate("ocr_contains", "Practice phrase matched"),
                    )
                return PlannerDecision(
                    kind="action",
                    reason="Move visibly to the ordinary local practice field.",
                    action=GuiAction("move_mouse", {"x": x, "y": y, "duration": 0.25}),
                    expected=ObservationPredicate("observation_fresh"),
                )

            if self._contains(observation, "Final sandbox checkpoint"):
                x, y = self._token_or_fixture_offset(
                    observation,
                    target_word="Complete",
                    anchor_word="Final",
                    offset_x=25,
                    offset_y=105,
                )
                return self._move_then_click(
                    x=x,
                    y=y,
                    expected_phrase=self.success_marker,
                    history=history,
                )
        except FixturePlannerError as exc:
            return PlannerDecision(kind="abort", reason=str(exc))

        return PlannerDecision(kind="abort", reason="fixture_screen_state_unknown_or_ambiguous")


def verify_fixture_manifest(
    path: str | Path = LOCAL_FIXTURE_MANIFEST,
    *,
    expected_sha256: str = LOCAL_FIXTURE_MANIFEST_SHA256,
) -> Mapping[str, object]:
    """Return a safe read-back without starting a planner or touching the GUI."""

    planner = LocalFixturePlanner(path, expected_sha256=expected_sha256)
    return {
        "ok": True,
        "locality": planner.locality,
        "manifest_path": str(planner.manifest_path),
        "manifest_sha256": planner.manifest_sha256,
        "practice_text_sha256": hashlib.sha256(planner.practice_text.encode("utf-8")).hexdigest(),
        "success_marker_sha256": hashlib.sha256(planner.success_marker.encode("utf-8")).hexdigest(),
        "required_gateway_actions": sorted(REQUIRED_GATEWAY_ACTIONS),
    }


__all__ = [
    "FixturePlannerError",
    "LOCAL_FIXTURE_MANIFEST",
    "LOCAL_FIXTURE_MANIFEST_SHA256",
    "LocalFixturePlanner",
    "REQUIRED_GATEWAY_ACTIONS",
    "verify_fixture_manifest",
]
