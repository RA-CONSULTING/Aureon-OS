"""Real-effect coverage for ``execute_shell`` destructive-command bypasses.

Each destructive case builds a directory or file under ``tmp_path`` and asserts
that object is still there, with its original contents, after the built-in
runs. A refusal string alone is not the check: on the substring blocklist the
payloads below that never contain the letters ``rm`` followed by a space
really delete the directory.

``python`` is not installed here. The interpreter case uses the running
interpreter (``sys.executable``, this machine's ``python3``) so ``-c`` is a
real process, not a missing-binary no-op.
"""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path

from aureon.inhouse_ai.tool_registry import ToolRegistry

_SHELL_SYNTAX = set("$`;|&<>(){}#!~*?[]\\'\"\n\r\t ")


def _execute(command: str) -> dict:
    reg = ToolRegistry(include_builtins=True, hnc_coherence_required=False)
    raw = reg.execute("execute_shell", {"command": command, "timeout": 5})
    return json.loads(raw)


def _plain(path: Path) -> str:
    text = str(path)
    if any(ch in _SHELL_SYNTAX for ch in text):
        raise AssertionError(f"fixture path contains shell syntax: {text}")
    return text


def _directory(tmp_path: Path) -> Path:
    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "keep.txt").write_text("keep")
    return victim


def _assert_directory_survives(tmp_path: Path, template: str) -> None:
    victim = _directory(tmp_path)
    out = _execute(template.replace("TARGET", _plain(victim)))
    assert victim.is_dir(), out
    assert (victim / "keep.txt").read_text() == "keep", out
    assert "returncode" not in out, out


def _assert_file_survives(tmp_path: Path, template: str) -> None:
    victim = tmp_path / "victim"
    victim.write_text("keep")
    out = _execute(template.replace("TARGET", _plain(victim)))
    assert victim.is_file(), out
    assert victim.read_text() == "keep", out
    assert "returncode" not in out, out


def test_rm_tab_rf_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "rm\t-rf TARGET")


def test_rm_two_spaces_rf_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "rm  -rf TARGET")


def test_rm_split_r_and_f_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "rm -r -f TARGET")


def test_rm_fr_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "rm -fr TARGET")


def test_bin_rm_rf_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "/bin/rm -rf TARGET")


def test_semicolon_chain_rm_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "echo ok; rm -rf TARGET")


def test_semicolon_tab_rm_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "echo ok;rm\t-rf TARGET")


def test_and_and_tab_rm_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "echo ok&&rm\t-rf TARGET")


def test_dollar_substitution_rm_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "echo $(rm -rf TARGET)")


def test_dollar_tab_rm_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "echo $(rm\t-rf TARGET)")


def test_backtick_rm_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "echo `rm -rf TARGET`")


def test_backtick_command_name_rm_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "`echo rm` -rf TARGET")


def test_ifs_expansion_rm_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "rm${IFS}-rf TARGET")


def test_assignment_expansion_rm_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "X=rm; $X -rf TARGET")


def test_sh_c_rm_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "sh -c 'rm -rf TARGET'")


def test_sh_c_tab_rm_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, 'sh -c "rm\t-rf TARGET"')


def test_bash_c_rm_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "bash -c 'rm -rf TARGET'")


def test_pipe_to_sh_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "printf 'rm\\t-rf TARGET\\n' | sh")


def test_env_rm_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "env rm -rf TARGET")


def test_sudo_rm_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "sudo rm -rf TARGET")


def test_python_c_pass_is_not_executed(tmp_path):
    victim = _directory(tmp_path)
    out = _execute(f"{sys.executable} -c pass")
    assert victim.is_dir(), out
    assert (victim / "keep.txt").read_text() == "keep", out
    assert "returncode" not in out, out


def test_python_c_shutil_rmtree_leaves_directory(tmp_path):
    victim = _directory(tmp_path)
    target = _plain(victim)
    code = "import shutil; shutil.rmtree(" + repr(target) + ")"
    command = f"{sys.executable} -c {shlex.quote(code)}"
    out = _execute(command)
    assert victim.is_dir(), out
    assert (victim / "keep.txt").read_text() == "keep", out
    assert "returncode" not in out, out


def test_dd_tab_leaves_file(tmp_path):
    _assert_file_survives(tmp_path, "dd\tif=/dev/zero of=TARGET bs=1 count=1")


def test_shred_leaves_file(tmp_path):
    _assert_file_survives(tmp_path, "shred -u TARGET")


def test_chmod_recursive_leaves_mode(tmp_path):
    victim = tmp_path / "victim"
    victim.mkdir()
    child = victim / "keep.txt"
    child.write_text("keep")
    child.chmod(0o600)
    out = _execute(f"chmod -R a+rwx {_plain(victim)}")
    assert victim.is_dir(), out
    assert child.read_text() == "keep", out
    assert (child.stat().st_mode & 0o777) == 0o600, out
    assert "returncode" not in out, out


def test_chown_recursive_is_not_executed(tmp_path):
    victim = _directory(tmp_path)
    before = victim.stat().st_uid
    out = _execute(f"chown -R nobody {_plain(victim)}")
    assert victim.is_dir(), out
    assert (victim / "keep.txt").read_text() == "keep", out
    assert victim.stat().st_uid == before, out
    assert "returncode" not in out, out


def test_unmatched_quote_is_not_executed(tmp_path):
    victim = _directory(tmp_path)
    out = _execute(f"rm\t-rf {_plain(victim)}'")
    assert victim.is_dir(), out
    assert (victim / "keep.txt").read_text() == "keep", out
    assert "returncode" not in out, out


def test_echo_hello_still_runs():
    out = _execute("echo hello")
    assert out.get("returncode") == 0, out
    assert "hello" in out.get("stdout", ""), out
    assert "error" not in out, out


def test_ls_tmp_path_still_runs(tmp_path):
    (tmp_path / "seen.txt").write_text("x")
    out = _execute(f"ls {_plain(tmp_path)}")
    assert out.get("returncode") == 0, out
    assert "seen.txt" in out.get("stdout", ""), out
    assert "error" not in out, out


def test_echo_fork_is_not_a_substring_false_positive():
    """The old list refused any command whose text contained ``fork``."""
    out = _execute("echo fork")
    assert out.get("returncode") == 0, out
    assert "fork" in out.get("stdout", ""), out
