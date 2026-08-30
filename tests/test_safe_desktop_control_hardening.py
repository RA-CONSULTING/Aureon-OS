from __future__ import annotations

import json

from aureon.autonomous import aureon_safe_desktop_control as desktop_module
from aureon.autonomous.aureon_safe_desktop_control import DesktopAction, SafeDesktopControl


class _FakePyAutoGui:
    def __init__(self) -> None:
        self.typed: list[str] = []

    def write(self, text: str, *, interval: float) -> None:
        del interval
        self.typed.append(text)


def _controller(tmp_path, *, dry_run: bool = True) -> SafeDesktopControl:
    return SafeDesktopControl(
        state_path=tmp_path / "desktop.json",
        kill_path=tmp_path / "desktop.stop",
        dry_run=dry_run,
    )


def test_persisted_live_arming_is_never_restored(tmp_path) -> None:
    state = tmp_path / "desktop.json"
    state.write_text(
        json.dumps(
            {
                "armed": True,
                "dry_run": False,
                "require_confirmation": False,
                "auto_approve_live_voice": True,
            }
        ),
        encoding="utf-8",
    )

    control = _controller(tmp_path, dry_run=False)

    assert control.armed is False
    assert control.dry_run is True
    assert control.require_confirmation is True
    assert control.auto_approve_live_voice is False


def test_live_action_requires_explicit_approval(tmp_path) -> None:
    control = _controller(tmp_path)
    control.set_live_mode(True)
    control.arm()

    result = control.execute(DesktopAction(action="left_click", params={"x": 10, "y": 20}))

    assert result.ok is False
    assert result.reason == "explicit_action_approval_required"


def test_voice_source_never_bypasses_live_confirmation(tmp_path, monkeypatch) -> None:
    fake = _FakePyAutoGui()
    monkeypatch.setattr(desktop_module, "HAS_PYAUTOGUI", True)
    monkeypatch.setattr(desktop_module, "pyautogui", fake)
    monkeypatch.setenv("AUREON_DESKTOP_CONFIRM_TOKEN", "ephemeral-token")
    monkeypatch.setenv("AUREON_AUTO_APPROVE_LIVE_VOICE", "1")
    control = _controller(tmp_path)
    control.set_live_mode(True)
    control.arm()

    result = control.execute(
        DesktopAction(
            action="type_text",
            params={"text": "private value"},
            source="voice:test",
            approved=True,
        )
    )

    assert result.ok is False
    assert result.reason == "confirmation_required"
    assert fake.typed == []


def test_live_typing_uses_explicit_approval_and_token_without_persisting_text(tmp_path, monkeypatch) -> None:
    fake = _FakePyAutoGui()
    monkeypatch.setattr(desktop_module, "HAS_PYAUTOGUI", True)
    monkeypatch.setattr(desktop_module, "pyautogui", fake)
    monkeypatch.setenv("AUREON_DESKTOP_CONFIRM_TOKEN", "ephemeral-token")
    control = _controller(tmp_path)
    control.set_live_mode(True)
    control.arm()

    result = control.execute(
        DesktopAction(
            action="type_text",
            params={"text": "private value"},
            confirm_token="ephemeral-token",
            approved=True,
        )
    )

    assert result.ok is True
    assert fake.typed == ["private value"]
    persisted = (tmp_path / "desktop.json").read_text(encoding="utf-8")
    assert "private value" not in persisted
    assert "ephemeral-token" not in persisted
    assert json.loads(persisted)["armed"] is False
    assert json.loads(persisted)["dry_run"] is True
