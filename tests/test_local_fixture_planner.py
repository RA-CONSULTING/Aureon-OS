from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from aureon.operator.local_fixture_planner import (
    LOCAL_FIXTURE_MANIFEST,
    LOCAL_FIXTURE_MANIFEST_SHA256,
    FixturePlannerError,
    LocalFixturePlanner,
    verify_fixture_manifest,
)
from aureon.operator.local_gui_observer import OCRToken, ScreenObservation


def _observation(texts: list[tuple[str, int, int]], *, sequence: int = 1) -> ScreenObservation:
    return ScreenObservation(
        observation_id=hashlib.sha256(f"fixture:{sequence}".encode()).hexdigest(),
        sequence=sequence,
        captured_at_unix=float(sequence),
        screenshot_sha256=hashlib.sha256(f"screen:{sequence}".encode()).hexdigest(),
        width=1200,
        height=900,
        ocr_tokens=tuple(
            OCRToken(text=text, x=x, y=y, width=max(30, len(text) * 10), height=24)
            for text, x, y in texts
        ),
    )


def _transition(action):
    return SimpleNamespace(decision=SimpleNamespace(action=action))


def test_fixture_manifest_is_exactly_hash_bound_and_safe() -> None:
    result = verify_fixture_manifest()
    assert result["ok"] is True
    assert result["manifest_sha256"] == LOCAL_FIXTURE_MANIFEST_SHA256
    assert result["locality"] == "local"
    assert result["required_gateway_actions"] == ["click", "move", "press", "scroll", "type"]


def test_fixture_planner_rejects_hash_or_contract_drift(tmp_path: Path) -> None:
    with pytest.raises(FixturePlannerError, match="hash_mismatch"):
        LocalFixturePlanner(LOCAL_FIXTURE_MANIFEST, expected_sha256="0" * 64)

    payload = json.loads(LOCAL_FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    payload["local_only"] = False
    drifted = tmp_path / "manifest.json"
    drifted.write_text(json.dumps(payload), encoding="utf-8")
    digest = hashlib.sha256(drifted.read_bytes()).hexdigest()
    with pytest.raises(FixturePlannerError, match="contract_invalid"):
        LocalFixturePlanner(drifted, expected_sha256=digest)


def test_fixture_planner_moves_then_clicks_start_control() -> None:
    planner = LocalFixturePlanner()
    observation = _observation(
        [("Ready", 500, 200), ("to", 560, 200), ("begin", 590, 200), ("Start", 520, 500)]
    )

    move = planner.plan("local fixture", observation, ())
    assert move.kind == "action"
    assert move.action.name == "move_mouse"
    assert move.expected.kind == "observation_fresh"

    click = planner.plan("local fixture", observation, (_transition(move.action),))
    assert click.action.name == "left_click"
    assert click.action.params["x"] == move.action.params["x"]
    assert click.expected.value == "Practice lesson"


def test_fixture_planner_uses_hash_bound_offset_when_button_text_is_not_ocr_visible() -> None:
    planner = LocalFixturePlanner()
    observation = _observation(
        [("Ready", 500, 200), ("to", 560, 200), ("begin", 590, 200)]
    )

    decision = planner.plan("local fixture", observation, ())

    assert decision.kind == "action"
    assert decision.action.name == "move_mouse"
    assert decision.action.params == {"x": 550, "y": 317, "duration": 0.25}


def test_fixture_planner_scrolls_types_only_ordinary_text_and_completes() -> None:
    planner = LocalFixturePlanner()
    lesson = _observation([("Practice", 400, 120), ("lesson", 500, 120)])
    scroll = planner.plan("local fixture", lesson, ())
    assert scroll.action.name == "scroll"
    assert scroll.action.params["clicks"] < 0

    scrolled_lesson = _observation(
        [
            ("Observe", 300, 100),
            ("Act", 300, 600),
            ("Use", 340, 650),
            ("bounded", 380, 650),
            ("pointer", 460, 650),
        ]
    )
    page_down = planner.plan("local fixture", scrolled_lesson, (_transition(scroll.action),))
    assert page_down.action.name == "press_key"
    assert page_down.action.params["key"] == "pagedown"

    sentinel_low = _observation(
        [("End", 520, 850), ("of", 560, 850), ("synthetic", 590, 850), ("lesson", 680, 850)]
    )
    reveal_next = planner.plan("local fixture", sentinel_low, (_transition(scroll.action),))
    assert reveal_next.action.name == "press_key"

    sentinel_visible = _observation(
        [("End", 520, 600), ("of", 560, 600), ("synthetic", 590, 600), ("lesson", 680, 600)]
    )
    move_to_next = planner.plan("local fixture", sentinel_visible, ())
    assert move_to_next.action.name == "move_mouse"
    assert move_to_next.action.params["x"] == 295
    assert move_to_next.action.params["y"] == 692

    practice = _observation(
        [
            ("Keyboard", 420, 100),
            ("practice", 530, 100),
            ("Practice", 420, 300),
            ("text", 520, 300),
            ("Waiting", 420, 420),
        ]
    )
    move = planner.plan("local fixture", practice, ())
    click = planner.plan("local fixture", practice, (_transition(move.action),))
    typed = planner.plan("local fixture", practice, (_transition(click.action),))
    assert [move.action.name, click.action.name, typed.action.name] == [
        "move_mouse",
        "left_click",
        "type_text",
    ]
    assert typed.action.params["text_class"] == "ordinary"
    assert hashlib.sha256(typed.action.params["text"].encode()).hexdigest() == (
        "ae319c9ae179921d108e5af004f8abdef813da880a214ddf8b443f5d13e7ab1e"
    )

    complete_observation = _observation(
        [("Local", 400, 200), ("sandbox", 470, 200), ("course", 570, 200), ("complete", 650, 200)]
    )
    complete = planner.plan("local fixture", complete_observation, ())
    assert complete.kind == "complete"
    assert complete.success_predicate.kind == "ocr_contains"


def test_fixture_planner_preserves_certification_human_gate() -> None:
    planner = LocalFixturePlanner()
    observation = _observation([("Certification", 400, 200), ("quiz", 550, 200)])

    decision = planner.plan("local fixture", observation, ())

    assert decision.kind == "human_required"
    assert decision.human_gate == "certification_assessment"
