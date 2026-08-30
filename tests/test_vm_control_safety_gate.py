from __future__ import annotations

from typing import Any, Dict

from aureon.autonomous.vm_control.base import VMAction, VMController


class _LiveController(VMController):
    def _backend_name(self) -> str:
        return "test-live"

    def _do_screenshot(self, **kwargs) -> Dict[str, Any]:
        return {"pixels": "fixture"}

    def _fixture(self, **kwargs) -> Dict[str, Any]:
        return {"received": kwargs}

    _do_mouse_move = _fixture
    _do_left_click = _fixture
    _do_right_click = _fixture
    _do_middle_click = _fixture
    _do_double_click = _fixture
    _do_triple_click = _fixture
    _do_left_click_drag = _fixture
    _do_scroll = _fixture
    _do_type_text = _fixture
    _do_press_key = _fixture
    _do_hotkey = _fixture
    _do_get_cursor_position = _fixture
    _do_get_screen_size = _fixture
    _do_list_windows = _fixture
    _do_get_active_window = _fixture
    _do_focus_window = _fixture
    _do_execute_shell = _fixture
    _do_execute_powershell = _fixture


def test_non_simulated_live_arm_requires_an_ephemeral_token() -> None:
    control = _LiveController(dry_run=True)

    result = control.arm(dry_run=False)

    assert result == {"ok": False, "error": "live_confirmation_token_required"}
    assert control.session.armed is False


def test_high_risk_live_action_requires_matching_token() -> None:
    control = _LiveController(dry_run=True)
    assert control.arm(dry_run=False, confirmation_token="lease-secret")["ok"] is True

    missing = control.dispatch(VMAction(action="type_text", params={"text": "x"}))
    wrong = control.dispatch(VMAction(action="type_text", params={"text": "x"}, confirm_token="wrong"))
    valid = control.dispatch(VMAction(action="type_text", params={"text": "x"}, confirm_token="lease-secret"))

    assert missing.ok is False and missing.error == "confirmation_required"
    assert wrong.ok is False and wrong.error == "confirmation_required"
    assert valid.ok is True


def test_disarm_invalidates_the_live_token() -> None:
    control = _LiveController(dry_run=True)
    control.arm(dry_run=False, confirmation_token="lease-secret")
    control.disarm()
    control.arm(dry_run=True)

    result = control.dispatch(VMAction(action="type_text", params={"text": "x"}, confirm_token="lease-secret"))

    assert result.ok is True
    assert result.dry_run is True
