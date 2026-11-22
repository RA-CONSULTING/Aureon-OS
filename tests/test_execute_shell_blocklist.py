"""Real-effect coverage for ``execute_shell`` destructive-command bypasses.

Each destructive case builds a directory or file under ``tmp_path`` and asserts
that object is still there, with its original contents, after the built-in
runs. A refusal string alone is not the check: on the substring blocklist the
payloads below that never contain the letters ``rm`` followed by a space
really delete the directory.

The interpreter cases use the running interpreter's real path and assert its
specific refusal reason. Launcher/interpreter variants are classified directly
so they do not depend on optional executables being installed.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from aureon.inhouse_ai.shell_guard import prepare_shell_argv, shell_command_refusal
from aureon.inhouse_ai.tool_registry import ToolRegistry

_SHELL_SYNTAX = set("$`;|&<>(){}#!~*?[]\\'\"\n\r\t ")
_META_REFUSAL = "shell metacharacter, substitution, chaining, or redirection"
_RM_RF_REFUSAL = "rm refused (recursive and force)"


def _command(*argv: str) -> str:
    return subprocess.list2cmdline(argv) if os.name == "nt" else shlex.join(argv)


def _execute(command: str) -> dict:
    reg = ToolRegistry(include_builtins=True, hnc_coherence_required=False)
    raw = reg.execute("execute_shell", {"command": command, "timeout": 5})
    return json.loads(raw)


def _plain(path: Path) -> str:
    text = str(path).replace("\\", "/") if os.name == "nt" else str(path)
    if any(ch in _SHELL_SYNTAX for ch in text):
        raise AssertionError(f"fixture path contains shell syntax: {text}")
    return text


def _directory(tmp_path: Path) -> Path:
    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "keep.txt").write_text("keep")
    return victim


def _assert_directory_survives(tmp_path: Path, template: str, reason: str) -> None:
    victim = _directory(tmp_path)
    out = _execute(template.replace("TARGET", _plain(victim)))
    assert victim.is_dir(), out
    assert (victim / "keep.txt").read_text() == "keep", out
    assert out.get("error") == f"Blocked: {reason}", out
    assert "returncode" not in out, out


def _assert_file_survives(tmp_path: Path, template: str, reason: str) -> None:
    victim = tmp_path / "victim"
    victim.write_text("keep")
    out = _execute(template.replace("TARGET", _plain(victim)))
    assert victim.is_file(), out
    assert victim.read_text() == "keep", out
    assert out.get("error") == f"Blocked: {reason}", out
    assert "returncode" not in out, out


def _print_script_command(tmp_path: Path, text: str) -> str:
    script = tmp_path / "print_value.py"
    script.write_text("import sys\nprint(sys.argv[1])\n", encoding="utf-8")
    return _command(sys.executable, str(script), text)


def test_rm_tab_rf_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "rm\t-rf TARGET", _RM_RF_REFUSAL)


def test_rm_two_spaces_rf_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "rm  -rf TARGET", _RM_RF_REFUSAL)


def test_rm_split_r_and_f_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "rm -r -f TARGET", _RM_RF_REFUSAL)


def test_rm_fr_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "rm -fr TARGET", _RM_RF_REFUSAL)


def test_bin_rm_rf_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "/bin/rm -rf TARGET", _RM_RF_REFUSAL)


def test_semicolon_chain_rm_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "echo ok; rm -rf TARGET", _META_REFUSAL)


def test_semicolon_tab_rm_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "echo ok;rm\t-rf TARGET", _META_REFUSAL)


def test_and_and_tab_rm_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "echo ok&&rm\t-rf TARGET", _META_REFUSAL)


def test_dollar_substitution_rm_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "echo $(rm -rf TARGET)", _META_REFUSAL)


def test_dollar_tab_rm_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "echo $(rm\t-rf TARGET)", _META_REFUSAL)


def test_backtick_rm_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "echo `rm -rf TARGET`", _META_REFUSAL)


def test_backtick_command_name_rm_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "`echo rm` -rf TARGET", _META_REFUSAL)


def test_ifs_expansion_rm_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "rm${IFS}-rf TARGET", _META_REFUSAL)


def test_assignment_expansion_rm_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "X=rm; $X -rf TARGET", _META_REFUSAL)


def test_sh_c_rm_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "sh -c 'rm -rf TARGET'", "shell interpreter refused")


def test_sh_c_tab_rm_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, 'sh -c "rm\t-rf TARGET"', "shell interpreter refused")


def test_bash_c_rm_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "bash -c 'rm -rf TARGET'", "shell interpreter refused")


def test_pipe_to_sh_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "printf 'rm\\t-rf TARGET\\n' | sh", _META_REFUSAL)


def test_env_rm_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "env rm -rf TARGET", "command wrapper refused")


def test_sudo_rm_leaves_directory(tmp_path):
    _assert_directory_survives(tmp_path, "sudo rm -rf TARGET", "sudo refused")


def test_python_c_pass_is_not_executed(tmp_path):
    victim = _directory(tmp_path)
    out = _execute(_command(sys.executable, "-c", "pass"))
    assert victim.is_dir(), out
    assert (victim / "keep.txt").read_text() == "keep", out
    assert out.get("error") == "Blocked: interpreter inline code refused", out
    assert "returncode" not in out, out


@pytest.mark.parametrize(
    "program",
    ["py", "py.exe", "pypy", "pypy.exe", "pypy3", "pypy3.exe", "pypy3.10", "pypy3.10.exe"],
)
def test_python_launcher_and_pypy_inline_code_refused(program):
    assert shell_command_refusal(_command(program, "-c", "pass")) == "interpreter inline code refused"


@pytest.mark.skipif(os.name != "nt", reason="Windows executable path parsing")
def test_windows_quoted_executable_path_is_accepted():
    expected = [r"C:\Program Files\Python312\python.exe", r"C:\tmp\script file.py"]
    argv, refusal = prepare_shell_argv(_command(*expected))
    assert refusal is None
    assert argv == expected


def test_python_c_shutil_rmtree_leaves_directory(tmp_path):
    victim = _directory(tmp_path)
    target = _plain(victim)
    code = "import shutil; shutil.rmtree(" + repr(target) + ")"
    out = _execute(_command(sys.executable, "-c", code))
    assert victim.is_dir(), out
    assert (victim / "keep.txt").read_text() == "keep", out
    assert out.get("error") == f"Blocked: {_META_REFUSAL}", out
    assert "returncode" not in out, out


def test_dd_tab_leaves_file(tmp_path):
    _assert_file_survives(tmp_path, "dd\tif=/dev/zero of=TARGET bs=1 count=1", "dd refused")


def test_shred_leaves_file(tmp_path):
    _assert_file_survives(tmp_path, "shred -u TARGET", "shred refused")


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode bits are not available on Windows")
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
    assert out.get("error") == "Blocked: recursive chmod or chown refused", out
    assert "returncode" not in out, out


@pytest.mark.skipif(os.name == "nt", reason="POSIX ownership and chown are not available on Windows")
def test_chown_recursive_is_not_executed(tmp_path):
    victim = _directory(tmp_path)
    before = victim.stat().st_uid
    out = _execute(f"chown -R nobody {_plain(victim)}")
    assert victim.is_dir(), out
    assert (victim / "keep.txt").read_text() == "keep", out
    assert victim.stat().st_uid == before, out
    assert out.get("error") == "Blocked: recursive chmod or chown refused", out
    assert "returncode" not in out, out


def test_unmatched_quote_is_not_executed(tmp_path):
    victim = _directory(tmp_path)
    out = _execute(f'rm\t-rf {_plain(victim)}"')
    assert victim.is_dir(), out
    assert (victim / "keep.txt").read_text() == "keep", out
    assert out.get("error") == "Blocked: could not parse command", out
    assert "returncode" not in out, out


def test_python_script_hello_still_runs(tmp_path):
    out = _execute(_print_script_command(tmp_path, "hello"))
    assert out.get("returncode") == 0, out
    assert "hello" in out.get("stdout", ""), out
    assert "error" not in out, out


@pytest.mark.skipif(os.name == "nt", reason="ls is a POSIX executable on the test runner")
def test_ls_tmp_path_still_runs(tmp_path):
    (tmp_path / "seen.txt").write_text("x")
    out = _execute(f"ls {_plain(tmp_path)}")
    assert out.get("returncode") == 0, out
    assert "seen.txt" in out.get("stdout", ""), out
    assert "error" not in out, out


def test_python_script_fork_is_not_a_substring_false_positive(tmp_path):
    """The old list refused any command whose text contained ``fork``."""
    out = _execute(_print_script_command(tmp_path, "fork"))
    assert out.get("returncode") == 0, out
    assert "fork" in out.get("stdout", ""), out
    assert "error" not in out, out
