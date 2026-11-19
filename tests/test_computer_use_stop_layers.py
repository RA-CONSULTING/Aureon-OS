"""One assertion per stop-file check.

Each test stays green only while its own check is present. Removing the
status check must not turn the execution test red, and the reverse.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


class _Registry:
    def __init__(self) -> None:
        self.executions: list[tuple[str, dict]] = []

    def list_tools(self):
        return [{"name": "read_state"}]

    def execute(self, name, params):
        self.executions.append((name, params))
        return {"status": "ok"}


class _Dispatcher:
    def list_sessions(self):
        return []


def _stop(monkeypatch, tmp_path: Path) -> Path:
    stop = tmp_path / "computer_use.stop"
    stop.write_text("human\n", encoding="utf-8")
    monkeypatch.setenv("AUREON_COMPUTER_USE_STOP_FILE", str(stop))
    return stop


def test_queen_status_reports_dry_run_when_stop_file_is_present(monkeypatch, tmp_path) -> None:
    """Goes red if the status() stop check is removed. The execution check is not read."""

    _stop(monkeypatch, tmp_path)
    from aureon.queen.queen_action_bridge import QueenActionBridge

    bridge = QueenActionBridge(registry=_Registry(), dispatcher=_Dispatcher(), live_default=True)
    status = bridge.status()
    assert status["live"] is False
    assert status["mode"] == "dry_run"


def test_queen_action_is_dry_run_when_stop_file_is_present(monkeypatch, tmp_path) -> None:
    """Goes red if the handle_message stop check is removed. status() is not read."""

    _stop(monkeypatch, tmp_path)
    from aureon.queen.queen_action_bridge import QueenActionBridge

    registry = _Registry()
    bridge = QueenActionBridge(registry=registry, dispatcher=_Dispatcher(), live_default=True)
    reply = bridge.handle_message("show me the state")
    assert len(reply.actions) == 1
    assert reply.actions[0].mode == "dry_run"
    assert reply.actions[0].result.get("simulated") is True
    assert registry.executions == []


def test_pursuit_explicit_zero_is_dry_run_not_armed(monkeypatch, tmp_path) -> None:
    """M7: an explicit 0 must not be treated as armed. Goes red if that happens."""

    monkeypatch.setenv("AUREON_COMPUTER_USE_STOP_FILE", str(tmp_path / "absent.stop"))
    monkeypatch.setenv("AUREON_LOCAL_ACTIONS_ARMED", "0")
    from aureon.core.pursuit import _local_hand

    assert _local_hand() == "dry_run"


def test_pursuit_hand_is_dry_run_when_stop_file_is_present(monkeypatch, tmp_path) -> None:
    """Goes red if pursuit's stop check is removed. Local actions are explicitly armed."""

    _stop(monkeypatch, tmp_path)
    monkeypatch.setenv("AUREON_LOCAL_ACTIONS_ARMED", "1")
    from aureon.core.pursuit import _local_hand

    assert _local_hand() == "dry_run"


def test_local_bridge_default_arming_is_off_when_stop_file_is_present(monkeypatch, tmp_path) -> None:
    """Goes red if only the _default_armed stop check is removed. perform() is not called."""

    _stop(monkeypatch, tmp_path)
    monkeypatch.delenv("AUREON_LOCAL_ACTIONS_ARMED", raising=False)
    from aureon.operator.local_action_bridge import LocalActionBridge

    bridge = LocalActionBridge(join=False, executor=lambda action, params: {"ok": True})
    assert bridge.armed is False


def test_local_bridge_perform_stays_dry_run_when_stop_file_is_present(monkeypatch, tmp_path) -> None:
    """Goes red if only the perform() stop check is removed. armed=True skips _default_armed."""

    _stop(monkeypatch, tmp_path)
    from aureon.operator.grounded_action import GroundedActionGate
    from aureon.operator.local_action_bridge import LocalActionBridge

    calls: list[str] = []
    bridge = LocalActionBridge(
        gate=GroundedActionGate(enable_llm=False),
        join=False,
        armed=True,
        executor=lambda action, params: (calls.append(action), {"ok": True, "result": "ran"})[1],
    )
    result = bridge.perform("list_repo", {"path": "."})
    assert result["dry_run"] is True
    assert result["executed"] is False
    assert calls == []


def test_is_stopped_fails_closed_when_the_disk_cannot_be_read(monkeypatch) -> None:
    """An OSError is a stop, not a pass. Goes red if the except is removed."""

    from aureon.operator import computer_use_stop as stop_mod

    def _boom(self):
        raise OSError("unreadable")

    monkeypatch.setattr(stop_mod.Path, "is_file", _boom)
    assert stop_mod.is_stopped() is True


def test_stop_file_is_seen_from_another_working_directory(tmp_path: Path) -> None:
    """The default path is the repo file, not a relative path from cwd."""

    stop = ROOT / "state" / "computer_use.stop"
    stop.parent.mkdir(parents=True, exist_ok=True)
    already = stop.exists()
    if not already:
        stop.write_text("human\n", encoding="utf-8")
    env = os.environ.copy()
    env.pop("AUREON_COMPUTER_USE_STOP_FILE", None)
    env["PYTHONPATH"] = str(ROOT)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    script = (
        "import os\n"
        f"os.chdir({str(tmp_path)!r})\n"
        "os.environ.pop('AUREON_COMPUTER_USE_STOP_FILE', None)\n"
        "from aureon.operator.computer_use_stop import is_stopped, stop_path\n"
        "path = stop_path()\n"
        "assert path.is_absolute(), path\n"
        "assert is_stopped() is True, path\n"
        "print(path)\n"
    )
    try:
        proc = subprocess.run(
            [sys.executable, "-c", script],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        assert str(stop.resolve()) in proc.stdout
    finally:
        if not already and stop.exists():
            stop.unlink()
