"""Parse-then-decide gate for the built-in ``execute_shell`` command.

The previous check was ``if "rm " in command``. A tab, ``${IFS}``, a
backtick that never spelled those three characters, or ``python -c`` never
contained that substring, and the shell really ran.

This module tokenizes with :func:`shlex.split` and refuses the command unless
the result is one direct program invocation. Shell metacharacters are refused
before execution, including when they sit inside quotes: this gate does not
try to guess which quoting a shell would honor. Parse errors refuse the
command. Destructive programs are decided from the resolved basename and the
parsed flags, then the caller runs the argv with ``shell=False``.
"""

from __future__ import annotations

import os
import re
import shlex

_SHELL_META = re.compile(r"[$`;|&<>(){}#!~*?\[\]\\]")
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_PATH_PART = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")

_SHELLS = {
    "sh", "bash", "dash", "zsh", "ksh", "ash", "csh", "tcsh", "fish",
    "pwsh", "powershell", "cmd",
}
_SUDO = {"sudo", "su", "doas", "pkexec"}
_WRAPPERS = {
    "env", "nice", "nohup", "timeout", "stdbuf", "ionice", "setsid",
    "xargs", "find", "eval", "exec", "command", "busybox", "toybox",
    "strace", "ltrace", "watch", "flock", "time",
}
_INTERPRETERS = {
    "python", "python2", "python3", "pythonw",
    "perl", "ruby", "node", "nodejs", "deno", "bun",
    "php", "lua", "luajit", "awk", "gawk", "nawk",
}
_SCRIPT_SUFFIXES = (".py", ".pyw", ".pl", ".rb", ".js", ".mjs", ".cjs", ".php", ".lua")
_ALWAYS = {
    "dd": "dd refused",
    "shred": "shred refused",
    "shutdown": "shutdown refused",
    "reboot": "shutdown refused",
    "poweroff": "shutdown refused",
    "halt": "shutdown refused",
    "format": "destructive program refused",
    "del": "destructive program refused",
    "erase": "destructive program refused",
    "unlink": "destructive program refused",
}
_PERM_LONG_OK = {
    "changes", "silent", "quiet", "verbose", "help", "version",
    "no-dereference", "reference", "preserve-root", "no-preserve-root", "from",
}


class _Refuse(Exception):
    pass


def prepare_shell_argv(command: object) -> tuple[list[str] | None, str | None]:
    """Return ``(argv, None)`` to exec, or ``(None, reason)`` to refuse.

    Any unexpected failure refuses the command. The reason is a short label,
    not a copy of the command.
    """
    try:
        return _argv_or_raise(command), None
    except _Refuse as exc:
        return None, str(exc)
    except Exception:
        return None, "shell command could not be classified"


def shell_command_refusal(command: object) -> str | None:
    """Refusal reason, or None when the command may be executed."""
    _argv, refusal = prepare_shell_argv(command)
    if refusal:
        return refusal
    if not _argv:
        return "shell command refused"
    return None


def _argv_or_raise(command: object) -> list[str]:
    if not isinstance(command, str):
        raise _Refuse("command must be a string")
    if command.strip() == "":
        raise _Refuse("empty command")
    if any(ch.isspace() and ch not in " \t" for ch in command):
        raise _Refuse("unsupported whitespace")
    if "\x00" in command:
        raise _Refuse("unsupported whitespace")
    if _SHELL_META.search(command):
        raise _Refuse("shell metacharacter, substitution, chaining, or redirection")
    try:
        argv = shlex.split(command, posix=True)
    except ValueError as exc:
        raise _Refuse("could not parse command") from exc
    if not argv:
        raise _Refuse("empty command")
    index = 0
    while index < len(argv) and _ASSIGNMENT.match(argv[index]):
        index += 1
    if index:
        raise _Refuse("environment assignment")
    program = argv[0]
    if not _program_path_ok(program):
        raise _Refuse("program path is not a plain executable name")
    _refuse_program(_program_name(program), argv)
    return argv


def _program_path_ok(program: str) -> bool:
    if not program or program.startswith("-"):
        return False
    parts = program.split("/")
    if program.startswith("/"):
        parts = parts[1:]
    if not parts:
        return False
    return all(_PATH_PART.fullmatch(part) for part in parts)


def _program_name(program: str) -> str:
    base = os.path.basename(program).lower()
    if base.endswith(".exe"):
        base = base[:-4]
    return base


def _refuse_program(name: str, argv: list[str]) -> None:
    if name in _SHELLS:
        raise _Refuse("shell interpreter refused")
    if name in _SUDO:
        raise _Refuse("sudo refused")
    if name in _WRAPPERS:
        raise _Refuse("command wrapper refused")
    if name == "mkfs" or name.startswith("mkfs."):
        raise _Refuse("mkfs refused")
    if name in _ALWAYS:
        raise _Refuse(_ALWAYS[name])
    if name == "rm":
        raise _Refuse(_rm_reason(argv))
    if name in {"chmod", "chown"} and _permission_change_refused(argv):
        raise _Refuse("recursive chmod or chown refused")
    if _downloader_to_shell(name, argv):
        raise _Refuse("curl or wget piped to a shell refused")
    if _is_interpreter(name) and _interpreter_refused(argv):
        raise _Refuse("interpreter inline code refused")


def _is_interpreter(name: str) -> bool:
    if name in _INTERPRETERS:
        return True
    return name.startswith("python") and (len(name) == 6 or name[6:7].isdigit())


def _interpreter_refused(argv: list[str]) -> bool:
    """Refuse ``-c`` / ``-e`` / any option, and inline text that is not a script file.

    ``python script.py`` stays available so a real interpreter can still be
    pinned without handing it a one-liner. A shell is never allowed this far.
    """
    if len(argv) < 2:
        return True
    if any(arg.startswith("-") for arg in argv[1:]):
        return True
    return not argv[1].lower().endswith(_SCRIPT_SUFFIXES)


def _rm_reason(argv: list[str]) -> str:
    """Recognize ``-r`` / ``-f`` in any cluster, order, or long-option form.

    Plain ``rm file`` unlinks too, so every rm is refused. The label records
    whether the parsed flags were recursive, force, or both.
    """
    recursive = False
    force = False
    end = False
    for arg in argv[1:]:
        if arg == "--" and not end:
            end = True
            continue
        if end or arg == "-" or not arg.startswith("-"):
            continue
        if arg.startswith("--"):
            body = arg[2:].split("=", 1)[0]
            if body == "recursive":
                recursive = True
            elif body == "force":
                force = True
            continue
        letters = arg[1:].split("=", 1)[0]
        if "r" in letters or "R" in letters:
            recursive = True
        if "f" in letters:
            force = True
    if recursive and force:
        return "rm refused (recursive and force)"
    if recursive:
        return "rm refused (recursive)"
    if force:
        return "rm refused (force)"
    return "rm refused"


def _permission_change_refused(argv: list[str]) -> bool:
    """Refuse recursive chmod/chown, a change of ``/``, and unknown options."""
    recursive = False
    root_operand = False
    end = False
    for arg in argv[1:]:
        if end:
            if _is_root_path(arg):
                root_operand = True
            continue
        if arg == "--":
            end = True
            continue
        if arg.startswith("--"):
            body, _sep, value = arg[2:].partition("=")
            if body == "recursive":
                recursive = True
            elif body not in _PERM_LONG_OK:
                return True
            if value and _is_root_path(value):
                root_operand = True
            continue
        if arg.startswith("-") and arg != "-":
            letters = arg[1:]
            if any(ch not in "Rcfv" for ch in letters):
                return True
            if "R" in letters:
                recursive = True
            continue
        if _is_root_path(arg):
            root_operand = True
    return recursive or root_operand


def _is_root_path(token: str) -> bool:
    if token in {"/", "/*", "//", "/.", "/./", "/../"}:
        return True
    if token.startswith("/") and token.strip("/") == "":
        return True
    try:
        return os.path.normpath(token) == "/"
    except (TypeError, ValueError):
        return True


def _downloader_to_shell(name: str, argv: list[str]) -> bool:
    names = {name, *(_program_name(token) for token in argv[1:])}
    return bool(names & {"curl", "wget"}) and bool(names & _SHELLS)
