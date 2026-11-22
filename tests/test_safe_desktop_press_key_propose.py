"""propose() must queue press_key for confirmation, not auto-run and drop it.

press_key is listed in both AUTO_EXECUTE_ACTIONS and HIGH_RISK_ACTIONS.  On
main, an armed controller's propose() auto-executed it without a confirmation
token, execute() rejected it with ``confirmation_required``, and nothing was
left in the pending queue, so approve_next() with the right token answered
``no_pending_actions``.  The key could never be pressed via propose().
"""

from __future__ import annotations

import pytest

from aureon.autonomous import aureon_safe_desktop_control as desktop_module
from aureon.autonomous.aureon_safe_desktop_control import DesktopAction, SafeDesktopControl

TOKEN = "unit-test-confirm-token"


class _FakePyAutoGui:
    def __init__(self) -> None:
        self.pressed: list[str] = []

    def press(self, key: str) -> None:
        self.pressed.append(key)


def _controller(tmp_path, monkeypatch, *, dry_run: bool) -> SafeDesktopControl:
    monkeypatch.setenv("AUREON_DESKTOP_CONFIRM_TOKEN", TOKEN)
    monkeypatch.delenv("AUREON_DESKTOP_REQUIRE_CONFIRMATION", raising=False)
    return SafeDesktopControl(
        state_path=tmp_path / "desktop.json",
        kill_path=tmp_path / "desktop.stop",
        dry_run=dry_run,
    )


def test_dry_run_propose_press_key_is_queued_then_approvable(tmp_path, monkeypatch) -> None:
    control = _controller(tmp_path, monkeypatch, dry_run=True)
    control.arm_dry_run()

    proposed = control.propose(DesktopAction("press_key", {"key": "enter"}))

    assert proposed["status"] == "pending"
    assert len(control.pending_actions) == 1
    result = control.approve_next(TOKEN)
    assert result.ok is True
    assert result.reason == "dry_run"


def test_live_propose_press_key_is_queued_and_only_runs_with_token(tmp_path, monkeypatch) -> None:
    fake = _FakePyAutoGui()
    monkeypatch.setattr(desktop_module, "pyautogui", fake)
    monkeypatch.setattr(desktop_module, "HAS_PYAUTOGUI", True)
    control = _controller(tmp_path, monkeypatch, dry_run=False)
    control.arm_live()

    proposed = control.propose(DesktopAction("press_key", {"key": "enter"}, approved=True))
    assert proposed["status"] == "pending"
    assert fake.pressed == []

    wrong = control.approve_next("wrong-token")
    assert (wrong.ok, wrong.reason) == (False, "confirmation_required")
    assert fake.pressed == []

    control.propose(DesktopAction("press_key", {"key": "enter"}, approved=True))
    right = control.approve_next(TOKEN)
    assert (right.ok, right.reason) == (True, "executed")
    assert fake.pressed == ["enter"]


@pytest.mark.parametrize("action,params", [("left_click", {"x": 1, "y": 1}), ("move_mouse", {"x": 2, "y": 3})])
def test_low_risk_actions_still_auto_execute_in_dry_run(tmp_path, monkeypatch, action, params) -> None:
    control = _controller(tmp_path, monkeypatch, dry_run=True)
    control.arm_dry_run()

    proposed = control.propose(DesktopAction(action, params))

    assert proposed["status"] == "executed"
    assert control.pending_actions == []


def test_press_key_auto_executes_when_confirmation_is_disabled(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AUREON_DESKTOP_REQUIRE_CONFIRMATION", "0")
    control = SafeDesktopControl(
        state_path=tmp_path / "desktop.json",
        kill_path=tmp_path / "desktop.stop",
        dry_run=True,
    )
    control.arm_dry_run()

    proposed = control.propose(DesktopAction("press_key", {"key": "tab"}))

    assert proposed["status"] == "executed"
