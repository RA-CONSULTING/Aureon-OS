from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from aureon.integrations.ollama import HNCModelRoutingReceipt
from aureon.operator.local_gui_observer import OCRToken, ScreenObservation, WindowRect
from aureon.operator.scorm_hnc_answer_brain import (
    HNCAnswerBrainError,
    SwitchboardHNCAnswerBrain,
    extract_grounded_assessment,
)


def _observation(*, assessment: bool = True) -> ScreenObservation:
    texts = (
        (
            ("Assessment", 444, 152, 121, 17),
            ("Question 1 of 10", 446, 191, 178, 20),
            ("Choose the correct answer then click the Next button.", 445, 223, 422, 13),
            (
                "What is the consequence of putting two different wastes in the same container?",
                444,
                267,
                454,
                12,
            ),
            ("The mixture is always easier to treat", 470, 324, 280, 12),
            ("The mixture is always easier to recycle", 470, 348, 300, 12),
            ("Waste treatment regulations may require permits", 469, 372, 360, 12),
            ("It always decreases hazardous waste volume", 470, 396, 320, 12),
            ("Next", 464, 442, 42, 18),
        )
        if assessment
        else (
            ("Hazardous Waste Awareness", 420, 150, 240, 20),
            ("Select Next to continue the lesson", 440, 400, 280, 18),
            ("Next", 464, 442, 42, 18),
        )
    )
    return ScreenObservation(
        observation_id="obs-1",
        sequence=1,
        captured_at_unix=1.0,
        screenshot_sha256="1" * 64,
        width=1389,
        height=784,
        ocr_tokens=tuple(OCRToken(text, x, y, width, height, 0.99) for text, x, y, width, height in texts),
        cursor_x=20,
        cursor_y=20,
        window_handle=100,
        window_process_id=200,
        window_title_sha256="2" * 64,
        window_rect=WindowRect(0, 0, 1389, 784),
        dpi_x=96.0,
        dpi_y=96.0,
    )


def _route_receipt(*, decision: str = "ROUTE") -> HNCModelRoutingReceipt:
    route = HNCModelRoutingReceipt(
        schema_version="aureon-ollama-hnc-nerve-route-v1",
        decision=decision,
        reason=(
            "callable_cloud_model_selected_by_hnc_nerve_profile"
            if decision == "ROUTE"
            else "fresh_canonical_hnc_field_required"
        ),
        nerve_id="scorm-assessment:" + "1" * 24,
        lane="general",
        model="kimi-k3" if decision == "ROUTE" else "",
        provider_mode="ollama_cloud_primary",
        hnc_receipt_id="hnc:live_field:test" if decision == "ROUTE" else "",
        hnc_source_timestamp=1.0 if decision == "ROUTE" else None,
        coherence_gamma=0.9 if decision == "ROUTE" else None,
        consciousness_psi=0.8 if decision == "ROUTE" else None,
        lambda_t=0.7 if decision == "ROUTE" else None,
        coherence_band="active" if decision == "ROUTE" else "no_data",
        catalog_digest="3" * 64 if decision == "ROUTE" else "",
        catalog_size=19,
        candidate_count=3 if decision == "ROUTE" else 0,
        selected_rank=1 if decision == "ROUTE" else None,
        selection_source=(
            "live_probe_passed:hnc_active:ranked_live_catalog"
            if decision == "ROUTE"
            else "no_data"
        ),
        issued_at=2.0,
        action_eligible=False,
        economic_eligible=False,
        receipt_id="",
    )
    causal = asdict(route)
    causal.pop("receipt_id")
    digest = hashlib.sha256(
        json.dumps(
            causal,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode()
    ).hexdigest()
    return HNCModelRoutingReceipt(
        **{**asdict(route), "receipt_id": f"ollama:hnc-route:{digest}"}
    )


class _Bridge:
    def __init__(self, content: str) -> None:
        self.content = content
        self.calls: list[dict[str, object]] = []

    def chat(self, messages, **kwargs):
        self.calls.append({"messages": messages, **kwargs})
        return {"message": {"content": self.content}}


class _Switchboard:
    def __init__(self, content: str, *, decision: str = "ROUTE") -> None:
        self.bridge = _Bridge(content)
        self.route = _route_receipt(decision=decision)
        self.calls = 0

    def capture_hnc_field(self):
        return SimpleNamespace(available=True)

    def bridge_for_nerve(self, lane, *, nerve_id, hnc_field):
        self.calls += 1
        assert lane == "general"
        assert nerve_id == "scorm-assessment:" + "1" * 24
        assert hnc_field.available is True
        return self.bridge, SimpleNamespace(model="kimi-k3"), self.route


class _Sink:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []

    def append(self, event_type, payload):
        self.events.append((event_type, dict(payload)))


def test_extracts_only_visible_question_choices_between_question_and_next() -> None:
    assessment = extract_grounded_assessment(_observation())

    assert assessment is not None
    assert assessment.question.startswith("What is the consequence")
    assert [choice.line_id for choice in assessment.choices] == [
        "choice-1",
        "choice-2",
        "choice-3",
        "choice-4",
    ]
    assert assessment.choices[2].center == (649, 378)
    assert extract_grounded_assessment(_observation(assessment=False)) is None


def test_hnc_switchboard_selects_exact_visible_choice_and_writes_hash_only_receipt() -> None:
    switchboard = _Switchboard(
        json.dumps(
            {
                "kind": "choice",
                "choice_id": "choice-3",
                "confidence": "high",
                "reason": "This is the only option that correctly recognizes regulatory incompatibility.",
            }
        )
    )
    sink = _Sink()
    brain = SwitchboardHNCAnswerBrain(switchboard=switchboard, receipt_sink=sink)

    answer = brain.choose(_observation())

    assert answer is not None
    assert (answer.x, answer.y) == (649, 378)
    assert answer.choice_id == "choice-3"
    assert answer.receipt.model == "kimi-k3"
    assert answer.receipt.receipt_id.startswith("hnc:scorm-answer:")
    assert switchboard.calls == 1
    assert len(switchboard.bridge.calls) == 1
    assert switchboard.bridge.calls[0]["think"] is False
    assert sink.events[0][0] == "hnc_scorm_answer_selected"
    payload = sink.events[0][1]
    assert "question" not in payload
    assert "selected_text" not in payload
    assert payload["selected_choice_id"] == "choice-3"


def test_non_assessment_does_not_touch_switchboard() -> None:
    switchboard = _Switchboard(
        '{"kind":"choice","choice_id":"choice-1","confidence":"high","reason":"x"}'
    )
    brain = SwitchboardHNCAnswerBrain(switchboard=switchboard)

    assert brain.choose(_observation(assessment=False)) is None
    assert switchboard.calls == 0


def test_hnc_hold_and_invented_choice_fail_closed() -> None:
    hold = SwitchboardHNCAnswerBrain(
        switchboard=_Switchboard(
            '{"kind":"choice","choice_id":"choice-1","confidence":"high","reason":"x"}',
            decision="HOLD",
        )
    )
    with pytest.raises(HNCAnswerBrainError, match="hnc_route_hold"):
        hold.choose(_observation())

    invented = SwitchboardHNCAnswerBrain(
        switchboard=_Switchboard(
            '{"kind":"choice","choice_id":"choice-8","confidence":"high","reason":"x"}'
        )
    )
    with pytest.raises(HNCAnswerBrainError, match="choice_not_visible"):
        invented.choose(_observation())
