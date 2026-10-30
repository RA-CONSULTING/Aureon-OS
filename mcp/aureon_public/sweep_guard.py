"""Block sockets, process starts, and writes outside the sweep sandbox.

Installed only in a sweep child. The public server refuses to start when
``AUREON_PUBLIC_SWEEP`` is set, and this module does not start a server.
"""

from __future__ import annotations

import builtins
import io
import os
import subprocess
from pathlib import Path
from typing import Any

_INSTALLED = False
_SOCKETS: list[str] = []
_PROCESSES: list[str] = []
_WRITES: list[str] = []
_SANDBOX_WRITES: list[str] = []
_REAL: dict[str, Any] = {}
_USER_DIR_NAMES = (
    "HOME",
    "USERPROFILE",
    "XDG_CACHE_HOME",
    "XDG_CONFIG_HOME",
    "XDG_DATA_HOME",
    "XDG_RUNTIME_DIR",
    "XDG_STATE_HOME",
)


def declare_sandbox() -> Path:
    """Point temp files at a directory inside the sweep parent.

    Python probes ``/tmp`` when ``TMPDIR`` is unset. Those probes are not the
    module writing. The sandbox stays the temp parent, and ``TMPDIR`` is a
    directory inside it.
    """

    from aureon_public.sweep_layout import beside

    sandbox = beside()
    scratch = sandbox / "sweep-scratch"
    home = sandbox / "home"
    dirs = {
        "HOME": home,
        "USERPROFILE": home,
        "XDG_CACHE_HOME": home / ".cache",
        "XDG_CONFIG_HOME": home / ".config",
        "XDG_DATA_HOME": home / ".local" / "share",
        "XDG_RUNTIME_DIR": sandbox / "runtime",
        "XDG_STATE_HOME": home / ".local" / "state",
    }
    for path in (scratch, *dirs.values()):
        path.mkdir(parents=True, exist_ok=True)
    os.environ["AUREON_PUBLIC_SANDBOX"] = str(sandbox)
    os.environ["TMPDIR"] = str(scratch)
    os.environ["TEMP"] = str(scratch)
    os.environ["TMP"] = str(scratch)
    for name, path in dirs.items():
        os.environ[name] = str(path)
    try:
        import tempfile

        tempfile.tempdir = None
    except Exception:
        pass
    return sandbox


def snapshot() -> dict[str, list[str]]:
    """Copies of the attempts recorded since install."""

    return {
        "processes": list(_PROCESSES),
        "sandbox_writes": list(_SANDBOX_WRITES),
        "sockets": list(_SOCKETS),
        "writes": list(_WRITES),
    }


def _sandbox() -> Path | None:
    raw = os.environ.get("AUREON_PUBLIC_SANDBOX", "").strip()
    if not raw:
        return None
    return Path(raw).resolve()


def _outside(path: object) -> bool:
    sandbox = _sandbox()
    try:
        resolved = Path(os.fspath(path)).resolve()
    except (OSError, TypeError, ValueError):
        return True
    if sandbox is None:
        return True
    return resolved != sandbox and sandbox not in resolved.parents


def _harmless_device(path: object) -> bool:
    """``/dev/null`` is the pin check's stderr sink, not a module write."""

    try:
        text = os.fspath(path)
    except TypeError:
        return False
    return str(text) in {"/dev/null", "/dev/zero", "/dev/stdout", "/dev/stderr"}


def _record_inside(path: object) -> None:
    """Remember a write under the sandbox that is not the temp scratch dir."""

    sandbox = _sandbox()
    if sandbox is None or _harmless_device(path):
        return
    try:
        resolved = Path(os.fspath(path)).resolve()
    except (OSError, TypeError, ValueError):
        return
    scratch = (sandbox / "sweep-scratch").resolve()
    if resolved == scratch or scratch in resolved.parents:
        return
    if resolved != sandbox and sandbox not in resolved.parents:
        return
    text = str(resolved)[:200]
    if text not in _SANDBOX_WRITES:
        _SANDBOX_WRITES.append(text)


def _guard_path(path: object) -> None:
    """Block a path outside the sandbox. Record one inside it."""

    if _harmless_device(path):
        return
    if _outside(path):
        _note_write(path)
    _record_inside(path)


def _note_write(path: object) -> None:
    text = str(path)[:200]
    if text not in _WRITES:
        _WRITES.append(text)
    raise OSError("write blocked outside sandbox")


def _pin_git(command: object) -> bool:
    """True for the loader's ``git rev-parse <pin>:<path>`` and nothing else."""

    if not isinstance(command, (list, tuple)) or len(command) < 3:
        return False
    if Path(str(command[0])).name != "git" or str(command[1]) != "rev-parse":
        return False
    spec = str(command[2])
    pin = "8aa6a2d971cc529484e2a5e261e28afafab4e4f4"
    return spec.startswith(pin + ":") and " " not in spec


def _note_process(kind: str, detail: object) -> None:
    text = f"{kind} {detail}"[:200]
    if text not in _PROCESSES:
        _PROCESSES.append(text)
    raise OSError("process blocked")


def _write_mode(mode: object) -> bool:
    text = str(mode or "r")
    return any(flag in text for flag in ("w", "a", "x", "+"))


def install_sweep_guard() -> None:
    """Replace socket, process, and write entry points. Idempotent."""

    global _INSTALLED
    if _INSTALLED:
        return
    import shutil
    import socket

    _SOCKETS.clear()
    _PROCESSES.clear()
    _WRITES.clear()
    _SANDBOX_WRITES.clear()

    class _Guard(socket.socket):
        def connect(self, address: object, *args: object, **kwargs: object) -> None:
            text = str(address)[:160]
            if text not in _SOCKETS:
                _SOCKETS.append(text)
            raise OSError("socket blocked")

        def connect_ex(self, address: object, *args: object, **kwargs: object) -> int:
            text = str(address)[:160]
            if text not in _SOCKETS:
                _SOCKETS.append(text)
            raise OSError("socket blocked")

    def _create_connection(*args: object, **kwargs: object) -> object:
        if "create_connection" not in _SOCKETS:
            _SOCKETS.append("create_connection")
        raise OSError("socket blocked")

    def _open(file: object, mode: object = "r", *args: object, **kwargs: object) -> object:
        if _write_mode(mode):
            _guard_path(file)
        return _REAL["open"](file, mode, *args, **kwargs)

    def _os_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
        writing = flags & (os.O_WRONLY | os.O_RDWR | os.O_APPEND)
        if writing:
            _guard_path(path)
        return _REAL["os_open"](path, flags, *args, **kwargs)

    def _mkdir(path: object, *args: object, **kwargs: object) -> None:
        _guard_path(path)
        return _REAL["mkdir"](path, *args, **kwargs)

    def _makedirs(path: object, *args: object, **kwargs: object) -> None:
        _guard_path(path)
        return _REAL["makedirs"](path, *args, **kwargs)

    def _unlink(path: object, *args: object, **kwargs: object) -> None:
        _guard_path(path)
        return _REAL["unlink"](path, *args, **kwargs)

    def _remove(path: object, *args: object, **kwargs: object) -> None:
        _guard_path(path)
        return _REAL["remove"](path, *args, **kwargs)

    def _rename(src: object, dst: object, *args: object, **kwargs: object) -> None:
        _guard_path(src)
        _guard_path(dst)
        return _REAL["rename"](src, dst, *args, **kwargs)

    def _replace(src: object, dst: object, *args: object, **kwargs: object) -> None:
        _guard_path(src)
        _guard_path(dst)
        return _REAL["replace"](src, dst, *args, **kwargs)

    def _rmtree(path: object, *args: object, **kwargs: object) -> None:
        _guard_path(path)
        return _REAL["rmtree"](path, *args, **kwargs)

    def _move(src: object, dst: object, *args: object, **kwargs: object) -> object:
        _guard_path(src)
        _guard_path(dst)
        return _REAL["move"](src, dst, *args, **kwargs)

    def _fork(*args: object, **kwargs: object) -> int:
        _note_process("fork", args or "fork")
        raise AssertionError("unreachable")

    def _forkpty(*args: object, **kwargs: object) -> object:
        _note_process("forkpty", args or "forkpty")
        raise AssertionError("unreachable")

    def _posix_spawn(path: object, *args: object, **kwargs: object) -> int:
        _note_process("posix_spawn", path)
        raise AssertionError("unreachable")

    def _posix_spawnp(path: object, *args: object, **kwargs: object) -> int:
        _note_process("posix_spawnp", path)
        raise AssertionError("unreachable")

    def _spawn(name: str):
        def inner(*args: object, **kwargs: object) -> int:
            _note_process(name, args[0] if args else name)
            raise AssertionError("unreachable")

        return inner

    def _popen(*args: object, **kwargs: object) -> object:
        command = args[0] if args else kwargs.get("args")
        # The pinned loader reads blob ids with git rev-parse. That is the
        # server's pin check, not the module starting a process.
        if _pin_git(command):
            return _REAL["subprocess_popen"](*args, **kwargs)
        _note_process("Popen", command)
        raise AssertionError("unreachable")

    def _system(command: object) -> int:
        _note_process("system", command)
        raise AssertionError("unreachable")

    def _popen_os(command: object, *args: object, **kwargs: object) -> object:
        _note_process("popen", command)
        raise AssertionError("unreachable")

    def _exec(path: object, *args: object, **kwargs: object) -> None:
        _note_process("exec", path)
        raise AssertionError("unreachable")

    _REAL.update(
        {
            "create_connection": socket.create_connection,
            "execv": os.execv,
            "execve": os.execve,
            "fork": getattr(os, "fork", None),
            "forkpty": getattr(os, "forkpty", None),
            "makedirs": os.makedirs,
            "mkdir": os.mkdir,
            "move": shutil.move,
            "open": builtins.open,
            "os_open": os.open,
            "popen": os.popen,
            "posix_spawn": getattr(os, "posix_spawn", None),
            "posix_spawnp": getattr(os, "posix_spawnp", None),
            "remove": os.remove,
            "rename": os.rename,
            "replace": os.replace,
            "rmtree": shutil.rmtree,
            "socket": socket.socket,
            "subprocess_popen": subprocess.Popen,
            "system": os.system,
            "unlink": os.unlink,
        }
    )
    for name in (
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
    ):
        if hasattr(os, name):
            _REAL[name] = getattr(os, name)
    builtins.open = _open  # type: ignore[assignment]
    io.open = _open  # type: ignore[assignment]
    os.open = _os_open  # type: ignore[assignment]
    os.mkdir = _mkdir  # type: ignore[assignment]
    os.makedirs = _makedirs  # type: ignore[assignment]
    os.unlink = _unlink  # type: ignore[assignment]
    os.remove = _remove  # type: ignore[assignment]
    os.rename = _rename  # type: ignore[assignment]
    os.replace = _replace  # type: ignore[assignment]
    shutil.rmtree = _rmtree  # type: ignore[assignment]
    shutil.move = _move  # type: ignore[assignment]
    if _REAL.get("fork") is not None:
        os.fork = _fork  # type: ignore[assignment]
    if _REAL.get("forkpty") is not None:
        os.forkpty = _forkpty  # type: ignore[assignment]
    if _REAL.get("posix_spawn") is not None:
        os.posix_spawn = _posix_spawn  # type: ignore[assignment]
    if _REAL.get("posix_spawnp") is not None:
        os.posix_spawnp = _posix_spawnp  # type: ignore[assignment]
    for name in (
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
    ):
        if name in _REAL:
            setattr(os, name, _spawn(name))
    os.system = _system  # type: ignore[assignment]
    os.popen = _popen_os  # type: ignore[assignment]
    os.execv = _exec  # type: ignore[assignment]
    os.execve = _exec  # type: ignore[assignment]
    subprocess.Popen = _popen  # type: ignore[misc, assignment]
    socket.socket = _Guard  # type: ignore[misc]
    socket.create_connection = _create_connection  # type: ignore[assignment]
    try:
        import multiprocessing

        def _start(self: object, *args: object, **kwargs: object) -> None:
            _note_process("Process.start", getattr(self, "name", "process"))
            raise AssertionError("unreachable")

        _REAL["process_start"] = multiprocessing.Process.start
        multiprocessing.Process.start = _start  # type: ignore[method-assign]
    except Exception:
        _REAL["process_start"] = None
    _INSTALLED = True


def uninstall_sweep_guard() -> None:
    """Restore the process-wide functions. Tests use this."""

    global _INSTALLED
    if not _INSTALLED:
        return
    import shutil
    import socket

    builtins.open = _REAL["open"]
    io.open = _REAL["open"]
    os.open = _REAL["os_open"]
    os.mkdir = _REAL["mkdir"]
    os.makedirs = _REAL["makedirs"]
    os.unlink = _REAL["unlink"]
    os.remove = _REAL["remove"]
    os.rename = _REAL["rename"]
    os.replace = _REAL["replace"]
    shutil.rmtree = _REAL["rmtree"]
    shutil.move = _REAL["move"]
    for name in (
        "fork",
        "forkpty",
        "posix_spawn",
        "posix_spawnp",
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
    ):
        if _REAL.get(name) is not None:
            setattr(os, name, _REAL[name])
    os.system = _REAL["system"]
    os.popen = _REAL["popen"]
    os.execv = _REAL["execv"]
    os.execve = _REAL["execve"]
    subprocess.Popen = _REAL["subprocess_popen"]
    socket.socket = _REAL["socket"]
    socket.create_connection = _REAL["create_connection"]
    if _REAL.get("process_start") is not None:
        import multiprocessing

        multiprocessing.Process.start = _REAL["process_start"]
    _INSTALLED = False
