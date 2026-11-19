"""Pin the real effect of the ``execute_shell`` built-in.

These tests run a real subprocess through the real ``ToolRegistry`` and the
operator toolbelt (``build_operator_tools``). Nothing here fakes the shell:
the command is the current Python interpreter printing a marker, and the
refusal cases point at a real file under ``tmp_path`` that must survive.

They are pinning tests: on main at the time of writing the handler already
runs commands, so they pass there. They fail if the handler is replaced by a
HOLD / no-op, or if the destructive-command refusal is removed.
"""

from __future__ import annotations

import json
import shlex
import sys

from aureon.inhouse_ai.tool_registry import ToolRegistry
from aureon.operator.tools import build_operator_tools

MARKER = "aureon-shell-ok"


def _print_marker_command() -> str:
    return f"{shlex.quote(sys.executable)} -c \"print('{MARKER}')\""


def _assert_real_run(raw: str) -> None:
    out = json.loads(raw)
    assert "error" not in out and not out.get("blocked"), out
    assert out["returncode"] == 0, out
    assert MARKER in out["stdout"], out


def test_builtin_registry_execute_shell_runs_real_command():
    reg = ToolRegistry(include_builtins=True, hnc_coherence_required=False)
    assert "execute_shell" in reg
    _assert_real_run(reg.execute("execute_shell", {"command": _print_marker_command()}))


def test_builtin_execute_shell_reports_nonzero_returncode_and_stderr():
    reg = ToolRegistry(include_builtins=True, hnc_coherence_required=False)
    cmd = (
        f"{shlex.quote(sys.executable)} -c "
        "\"import sys; sys.stderr.write('aureon-shell-err'); sys.exit(3)\""
    )
    out = json.loads(reg.execute("execute_shell", {"command": cmd}))
    assert out["returncode"] == 3, out
    assert "aureon-shell-err" in out["stderr"], out


def test_operator_toolbelt_execute_shell_runs_real_command():
    reg = build_operator_tools(
        allow_writes=False,
        allow_shell=True,
        hnc_coherence_required=False,
    )
    assert "execute_shell" in reg
    _assert_real_run(reg.execute("execute_shell", {"command": _print_marker_command()}))


def test_builtin_blocklist_refuses_and_file_survives(tmp_path):
    victim = tmp_path / "victim.txt"
    victim.write_text("keep")
    reg = ToolRegistry(include_builtins=True, hnc_coherence_required=False)
    out = json.loads(
        reg.execute("execute_shell", {"command": f"rm -f {shlex.quote(str(victim))}"})
    )
    assert "Blocked" in out.get("error", ""), out
    assert "returncode" not in out
    assert victim.read_text() == "keep"


def test_operator_guard_refuses_destructive_and_dir_survives(tmp_path):
    victim_dir = tmp_path / "victim_dir"
    victim_dir.mkdir()
    (victim_dir / "f.txt").write_text("keep")
    reg = build_operator_tools(
        allow_writes=False,
        allow_shell=True,
        hnc_coherence_required=False,
    )
    out = json.loads(
        reg.execute("execute_shell", {"command": f"rm -rf {shlex.quote(str(victim_dir))}"})
    )
    assert out.get("blocked") is True, out
    assert (victim_dir / "f.txt").read_text() == "keep"
    assert any(c.get("tool") == "execute_shell" for c in reg.blocked_calls)
