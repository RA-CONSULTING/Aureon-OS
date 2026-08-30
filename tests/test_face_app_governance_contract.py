from __future__ import annotations

import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
FACE_SOURCE = REPO_ROOT / "aureon" / "autonomous" / "aureon_face_app.py"
FACE_LAUNCHER = REPO_ROOT / "scripts" / "runners" / "run_aureon_face.cmd"


def test_face_is_loopback_only_and_never_imports_legacy_laptop_control() -> None:
    source = FACE_SOURCE.read_text(encoding="utf-8")
    launcher = FACE_LAUNCHER.read_text(encoding="utf-8")

    assert "from aureon.autonomous.aureon_laptop_control import LaptopControl" not in source
    assert 'host="0.0.0.0"' not in source
    assert 'host="127.0.0.1"' in source
    assert 'cors_allowed_origins="*"' not in source
    assert 'AUREON_DESKTOP_LIVE=true' not in launcher
    assert 'AUREON_DESKTOP_AUTO_ARM=true' not in launcher
    assert "aureon.autonomous.aureon_cognitive_brain import get_brain" not in source


def test_face_blocks_ocr_click_shortcuts_outside_closed_loop_runtime(monkeypatch) -> None:
    pytest.importorskip("flask_socketio")
    from aureon.autonomous import aureon_face_app as face

    class _Agent:
        def execute(self, *_args, **_kwargs):
            raise AssertionError("agent must not be called for legacy OCR click")

    monkeypatch.setattr(face.state, "agent", _Agent())
    payload = json.loads(face._execute_tool("click_text", {"text": "Continue"}))

    assert payload["success"] is False
    assert payload["error"] == "tool_requires_governed_observe_plan_act_verify_runtime"
