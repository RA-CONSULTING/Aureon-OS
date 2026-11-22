"""Pin the real effect of the ``execute_shell`` built-in.

These tests run a real subprocess through the real ``ToolRegistry`` and the
operator toolbelt (``build_operator_tools``). Nothing here fakes execution:
the current Python interpreter runs script files that print markers, and the
refusal cases point at real files under ``tmp_path`` that must survive.

They are pinning tests: on main at the time of writing the handler already
runs commands, so they pass there. They fail if the handler is replaced by a
HOLD / no-op, or if the destructive-command refusal is removed.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys

from aureon.inhouse_ai.tool_registry import ToolRegistry
from aureon.operator.tools import build_operator_tools

MARKER = "aureon-shell-ok"


def _command(*argv: str) -> str:
    return subprocess.list2cmdline(argv) if os.name == "nt" else shlex.join(argv)


def _print_marker_command(tmp_path) -> str:
    # Inline ``python -c`` is refused, so the real child runs a script file.
    script = tmp_path / "print_marker.py"
    script.write_text(f"print({MARKER!r})\n", encoding="utf-8")
    return _command(sys.executable, str(script))


def _assert_real_run(raw: str) -> None:
    out = json.loads(raw)
    assert "error" not in out and not out.get("blocked"), out
    assert out["returncode"] == 0, out
    assert MARKER in out["stdout"], out


def test_builtin_registry_execute_shell_runs_real_command(tmp_path):
    reg = ToolRegistry(include_builtins=True, hnc_coherence_required=False)
    assert "execute_shell" in reg
    _assert_real_run(reg.execute("execute_shell", {"command": _print_marker_command(tmp_path)}))


def test_builtin_execute_shell_reports_nonzero_returncode_and_stderr(tmp_path):
    script = tmp_path / "report_err.py"
    script.write_text(
        "import sys\n"
        "sys.stderr.write('aureon-shell-err')\n"
        "sys.exit(3)\n",
        encoding="utf-8",
    )
    reg = ToolRegistry(include_builtins=True, hnc_coherence_required=False)
    out = json.loads(reg.execute("execute_shell", {"command": _command(sys.executable, str(script))}))
    assert out["returncode"] == 3, out
    assert "aureon-shell-err" in out["stderr"], out


def test_operator_toolbelt_execute_shell_runs_real_command(tmp_path):
    reg = build_operator_tools(
        allow_writes=False,
        allow_shell=True,
        hnc_coherence_required=False,
    )
    assert "execute_shell" in reg
    _assert_real_run(reg.execute("execute_shell", {"command": _print_marker_command(tmp_path)}))


def test_builtin_blocklist_refuses_and_file_survives(tmp_path):
    victim = tmp_path / "victim.txt"
    victim.write_text("keep")
    reg = ToolRegistry(include_builtins=True, hnc_coherence_required=False)
    out = json.loads(
        reg.execute("execute_shell", {"command": _command("rm", "-f", str(victim))})
    )
    assert out.get("error") == "Blocked: rm refused (force)", out
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
        reg.execute("execute_shell", {"command": _command("rm", "-rf", str(victim_dir))})
    )
    assert out.get("blocked") is True, out
    assert out.get("reason") == "destructive shell command refused", out
    assert (victim_dir / "f.txt").read_text() == "keep"
    assert any(c.get("tool") == "execute_shell" for c in reg.blocked_calls)
