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
_REAL: dict[str, Any] = {}


def snapshot() -> dict[str, list[str]]:
    """Copies of the attempts recorded since install."""

    return {
        "processes": list(_PROCESSES),
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


def _note_write(path: object) -> None:
    text = str(path)[:200]
    if text not in _WRITES:
        _WRITES.append(text)
    raise OSError("write blocked outside sandbox")


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
    import socket

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
        if _write_mode(mode) and _outside(file):
            _note_write(file)
        return _REAL["open"](file, mode, *args, **kwargs)

    def _os_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
        writing = flags & (os.O_WRONLY | os.O_RDWR | os.O_APPEND)
        if writing and _outside(path):
            _note_write(path)
        return _REAL["os_open"](path, flags, *args, **kwargs)

    def _mkdir(path: object, *args: object, **kwargs: object) -> None:
        if _outside(path):
            _note_write(path)
        return _REAL["mkdir"](path, *args, **kwargs)

    def _makedirs(path: object, *args: object, **kwargs: object) -> None:
        if _outside(path):
            _note_write(path)
        return _REAL["makedirs"](path, *args, **kwargs)

    def _popen(*args: object, **kwargs: object) -> object:
        command = args[0] if args else kwargs.get("args")
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
            "makedirs": os.makedirs,
            "mkdir": os.mkdir,
            "open": builtins.open,
            "os_open": os.open,
            "popen": os.popen,
            "socket": socket.socket,
            "subprocess_popen": subprocess.Popen,
            "system": os.system,
        }
    )
    builtins.open = _open  # type: ignore[assignment]
    io.open = _open  # type: ignore[assignment]
    os.open = _os_open  # type: ignore[assignment]
    os.mkdir = _mkdir  # type: ignore[assignment]
    os.makedirs = _makedirs  # type: ignore[assignment]
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
    import socket

    builtins.open = _REAL["open"]
    io.open = _REAL["open"]
    os.open = _REAL["os_open"]
    os.mkdir = _REAL["mkdir"]
    os.makedirs = _REAL["makedirs"]
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
