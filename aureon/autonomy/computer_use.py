"""Autonomous local computer control.

Actions run when asked. There is no confirmation token, no arming lease, and
no dry-run default. The only refusal switch is a stop file a human creates
(``state/computer_use.stop`` by default, or ``AUREON_COMPUTER_USE_STOP_FILE``).
Aureon never creates that file. ``computer_use_stop_file_active`` is the only
check; a follow-up that drops the stop deletes that function and its call sites.

``run_shell`` takes an argv list and uses ``shell=False``. A single string is
split with ``shlex`` and then checked the same way. Path denial resolves each
path-like argv element and the cwd with ``os.path.realpath`` (symlinks followed).
It does not substring-match the command text. That wall is a speed bump, not a
sandbox: a separate OS user without read access to the live-run folder is the
isolation that actually holds.

On Linux the pointer, keyboard, and screenshot go through
``default_desktop_backend`` (the X11 backend when ``DISPLAY`` is set).
PyAutoGUI itself is loaded by ``aureon.autonomous.pyautogui_loader``, which
keeps a missing tkinter from exiting the process.

``run_shell`` does not use a command blocklist. Each child runs under
``unshare`` with a new user, mount, and pid namespace (``--mount-proc``,
``--propagation private``). Secret files are covered by an empty bind mount
and secret directories, including ``/workspace/aureon_run_*``, by a tmpfs.
The parent ``/proc/<pid>/environ`` is not in that pid namespace. bubblewrap
is not required and is not used.
"""

from __future__ import annotations

import datetime
import fnmatch
import hashlib
import io
import json
import logging
import os
import shlex
import subprocess
import sys
import tempfile
import threading
import webbrowser
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import unquote, urlsplit

logger = logging.getLogger("aureon.autonomy.computer_use")

REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = REPO_ROOT / "state"
DEFAULT_AUDIT_PATH = STATE_DIR / "computer_use_audit.jsonl"
DEFAULT_STOP_PATH = STATE_DIR / "computer_use.stop"
DEFAULT_SCREENSHOT_DIR = STATE_DIR / "computer_use_screenshots"

_NAME_GLOBS = (".env*", "*keys*", "*secret*", "*credentials*")
_ENV_MARKERS = ("KEY", "SECRET", "TOKEN", "PASSWORD", "API")
_ENV_SUFFIXES = ("_KEY", "_SECRET", "_TOKEN")
_EXCHANGE_PREFIXES = ("KRAKEN_", "BINANCE_", "ALPACA_", "APCA_", "CAPITAL_", "COINAPI_")
_MAX_AUDIT_TEXT = 500
_MAX_OUTPUT_CHARS = 64_000

BrowserOpener = Callable[[str], Any]


def default_computer_use_stop_path() -> Path:
    override = os.environ.get("AUREON_COMPUTER_USE_STOP_FILE", "").strip()
    if override:
        return Path(override)
    return DEFAULT_STOP_PATH


def computer_use_stop_file_active(path: str | Path | None = None) -> bool:
    """Return True when a human has created the stop file.

    Aureon never creates this file. An unreadable path fails closed.
    Delete this function and its call sites to remove the stop.
    """

    target = Path(path) if path is not None else default_computer_use_stop_path()
    try:
        return target.is_file()
    except OSError:
        return True


def scrub_child_environ(source: Mapping[str, str] | None = None) -> dict[str, str]:
    """Drop key, secret, token, password, API, and exchange credentials."""

    base = os.environ if source is None else source
    cleaned: dict[str, str] = {}
    for name, value in base.items():
        upper = str(name).upper()
        if any(upper.startswith(prefix) for prefix in _EXCHANGE_PREFIXES):
            continue
        if any(upper.endswith(suffix) for suffix in _ENV_SUFFIXES):
            continue
        if any(marker in upper for marker in _ENV_MARKERS):
            continue
        cleaned[str(name)] = str(value)
    return cleaned


def _name_denied(component: str) -> str | None:
    folded = component.casefold()
    for pattern in _NAME_GLOBS:
        if fnmatch.fnmatch(folded, pattern.casefold()):
            return pattern
    if folded.startswith("aureon_run_"):
        return "aureon_run"
    return None


_WALL_LAUNCHER = r"""
import json, os, subprocess, sys
masks = json.loads(os.environ.get("AUREON_CU_MASKS") or "[]")
argv = json.loads(os.environ["AUREON_CU_ARGV"])
empty = os.environ["AUREON_CU_EMPTY"]
child_env = json.loads(os.environ["AUREON_CU_ENV"])
cwd = os.environ.get("AUREON_CU_CWD") or None
for kind, path in masks:
    if not os.path.lexists(path):
        continue
    if kind == "dir":
        mounted = subprocess.run(["mount", "-t", "tmpfs", "tmpfs", path], check=False)
    else:
        mounted = subprocess.run(["mount", "--bind", empty, path], check=False)
    if mounted.returncode != 0:
        sys.stderr.write(f"mount_failed {kind}\n")
        sys.exit(97)
os.chdir(cwd or os.getcwd())
os.execvpe(argv[0], argv, child_env)
"""


def _run_dir_mounts() -> list[Path]:
    found: list[Path] = []
    for root_text in ("/workspace", str(REPO_ROOT)):
        root = Path(root_text)
        try:
            if not root.is_dir():
                continue
            for child in root.iterdir():
                if child.name.casefold().startswith("aureon_run_"):
                    found.append(child)
        except OSError:
            continue
    return found


def _redact_audit_args(action: str, args: Mapping[str, Any]) -> dict[str, Any]:
    redacted = dict(args)
    if "text" in redacted and action in {"type_text", "type"}:
        text = "" if redacted.get("text") is None else str(redacted.pop("text"))
        redacted["text_length"] = len(text)
        redacted["text_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return redacted


def _redact_audit_summary(summary: Mapping[str, Any]) -> dict[str, Any]:
    redacted = dict(summary)
    redacted.pop("stdout", None)
    redacted.pop("stderr", None)
    redacted.pop("text", None)
    return redacted


def _write_new_screenshot(directory: Path, data: bytes) -> Path:
    """Write a PNG only inside ``directory``, and never over an existing file."""

    directory.mkdir(parents=True, exist_ok=True)
    root = directory.resolve()
    for attempt in range(8):
        stamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%S%fZ")
        path = directory / f"screen-{stamp}-{attempt}.png"
        if path.resolve().parent != root:
            raise ValueError("screenshot_outside_dir")
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            continue
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        return path
    raise FileExistsError("screenshot_name_collision")


def _spawn_walled(
    argv: list[str],
    cwd: Path | None,
    env: Mapping[str, str],
    timeout: float,
    masks: list[tuple[str, str]],
) -> subprocess.CompletedProcess[str]:
    """Run ``argv`` where secret paths are hidden and the parent environ is not mounted."""

    if not shutil_which("unshare"):
        raise OSError("filesystem_wall_unavailable")
    descriptor, empty_name = tempfile.mkstemp(prefix="aureon-cu-empty-")
    os.close(descriptor)
    helper = dict(env)
    helper["AUREON_CU_MASKS"] = json.dumps([[kind, path] for kind, path in masks])
    helper["AUREON_CU_ARGV"] = json.dumps(argv)
    helper["AUREON_CU_CWD"] = "" if cwd is None else str(cwd)
    helper["AUREON_CU_EMPTY"] = empty_name
    helper["AUREON_CU_ENV"] = json.dumps(dict(env))
    try:
        return subprocess.run(
            [
                "unshare",
                "--user",
                "--mount",
                "--pid",
                "--fork",
                "--mount-proc",
                "--map-root-user",
                "--propagation",
                "private",
                sys.executable,
                "-c",
                _WALL_LAUNCHER,
            ],
            cwd=None if cwd is None else str(cwd),
            env=helper,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    finally:
        try:
            os.unlink(empty_name)
        except OSError:
            pass


def shutil_which(name: str) -> str | None:
    import shutil

    return shutil.which(name)


def load_pyautogui() -> Any:
    """Load pyautogui through the shared loader. Never ``sys.exit``."""

    from aureon.autonomous.pyautogui_loader import import_pyautogui

    return import_pyautogui()


class GatewayDesktopAdapter:
    """ComputerUse actions over ``default_desktop_backend`` on Linux.

    The gateway backend names ``press`` and ``capture_screen``. Drag is not on
    that surface, so drag moves with the backend and finishes with pyautogui.
    """

    def __init__(self, backend: Any) -> None:
        self._backend = backend

    def screenshot_png(self) -> bytes:
        data = self._backend.capture_screen()
        if not isinstance(data, (bytes, bytearray)) or not bytes(data).startswith(b"\x89PNG"):
            raise ValueError("screenshot_not_png")
        return bytes(data)

    def move(self, x: int, y: int, duration: float = 0.0) -> None:
        self._backend.move(int(x), int(y), float(duration))

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> None:
        self._backend.click(int(x), int(y), str(button), int(clicks))

    def drag(self, x: int, y: int, x2: int, y2: int, button: str = "left") -> None:
        self.move(x, y, 0.0)
        gui = load_pyautogui()
        gui.FAILSAFE = False
        gui.dragTo(int(x2), int(y2), button=str(button), duration=0.1)

    def scroll(self, amount: int, x: int, y: int) -> None:
        self._backend.scroll(int(amount), int(x), int(y))

    def type_text(self, text: str, interval: float = 0.0) -> None:
        self._backend.type_text(str(text), float(interval))

    def press_key(self, key: str) -> None:
        self._backend.press(str(key))

    def hotkey(self, keys: Sequence[str]) -> None:
        self._backend.hotkey([str(key) for key in keys])


def default_computer_backend() -> Any:
    """Linux uses the gateway's host backend. Other hosts keep a direct driver."""

    if sys.platform.startswith("linux"):
        from aureon.autonomous.aureon_governed_desktop_gateway import default_desktop_backend

        return GatewayDesktopAdapter(default_desktop_backend())
    return PyAutoGUIDesktop()


class PyAutoGUIDesktop:
    """Pointer, keyboard, and screen grab. Screenshot uses Pillow, not scrot."""

    def __init__(self) -> None:
        self._pyautogui: Any = None

    def _gui(self) -> Any:
        if self._pyautogui is None:
            gui = load_pyautogui()
            gui.FAILSAFE = False
            gui.PAUSE = 0
            self._pyautogui = gui
        self._pyautogui.FAILSAFE = False
        return self._pyautogui

    def screenshot_png(self) -> bytes:
        from PIL import ImageGrab

        image = ImageGrab.grab()
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    def move(self, x: int, y: int, duration: float = 0.0) -> None:
        self._gui().moveTo(int(x), int(y), duration=float(duration))

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> None:
        self._gui().click(x=int(x), y=int(y), button=str(button), clicks=int(clicks))

    def drag(self, x: int, y: int, x2: int, y2: int, button: str = "left") -> None:
        gui = self._gui()
        gui.moveTo(int(x), int(y), duration=0)
        gui.dragTo(int(x2), int(y2), button=str(button), duration=0.1)

    def scroll(self, amount: int, x: int, y: int) -> None:
        self._gui().scroll(int(amount), x=int(x), y=int(y))

    def type_text(self, text: str, interval: float = 0.0) -> None:
        self._gui().write(str(text), interval=float(interval))

    def press_key(self, key: str) -> None:
        self._gui().press(str(key))

    def hotkey(self, keys: Sequence[str]) -> None:
        self._gui().hotkey(*[str(key) for key in keys])


def _png_size(data: bytes) -> tuple[int, int]:
    from PIL import Image

    with Image.open(io.BytesIO(data)) as image:
        if image.format != "PNG":
            raise ValueError("screenshot_not_png")
        return int(image.size[0]), int(image.size[1])


def _jsonable(value: Any, limit: int = _MAX_AUDIT_TEXT) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace")
    if isinstance(value, str):
        if len(value) > limit:
            return value[:limit] + "...(truncated)"
        return value
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item, limit) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item, limit) for item in value]
    return str(value)[:limit]


class ComputerUse:
    """Execute computer actions and append one JSON line per attempt."""

    def __init__(
        self,
        *,
        audit_path: str | Path | None = None,
        stop_path: str | Path | None = None,
        screenshot_dir: str | Path | None = None,
        backend: Any = None,
        browser_opener: BrowserOpener | None = None,
        deny_roots: Sequence[str | Path] | None = None,
        live_run_root: str | Path | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        self.audit_path = Path(audit_path) if audit_path is not None else DEFAULT_AUDIT_PATH
        self.stop_path = Path(stop_path) if stop_path is not None else default_computer_use_stop_path()
        self.screenshot_dir = Path(screenshot_dir) if screenshot_dir is not None else DEFAULT_SCREENSHOT_DIR
        self._backend = backend
        self.browser_opener = browser_opener
        self._deny_roots_extra = tuple(Path(root) for root in (deny_roots or ()))
        self._live_run_root = Path(live_run_root) if live_run_root else None
        self._environ = environ
        self._audit_lock = threading.Lock()
        self.repo_env_path = REPO_ROOT / ".env"

    def stop_file_active(self) -> bool:
        return computer_use_stop_file_active(self.stop_path)

    def _backend_or_default(self) -> Any:
        if self._backend is None:
            self._backend = default_computer_backend()
        return self._backend

    def _deny_roots(self) -> list[Path]:
        roots = list(self._deny_roots_extra)
        if self._live_run_root is not None:
            roots.append(self._live_run_root)
        configured = os.environ.get("AUREON_COMPUTER_USE_DENY_PATHS", "")
        for part in configured.split(os.pathsep):
            text = part.strip()
            if text:
                roots.append(Path(text))
        live = os.environ.get("AUREON_COMPUTER_USE_LIVE_RUN_ROOT", "").strip()
        if live:
            roots.append(Path(live))
        return roots

    def path_denied(self, raw: str | Path) -> str | None:
        """Return a denial reason, or None when the resolved path is allowed."""

        text = os.fspath(raw)
        if text.lower().startswith("file:"):
            file_path = _file_url_to_path(text)
            if file_path is None:
                return "file_url_unreadable"
            return self.path_denied(file_path)
        try:
            lexical = Path(os.path.abspath(text))
            real = Path(os.path.realpath(text))
        except OSError:
            return "path_unreadable"
        for candidate in (lexical, real):
            reason = self._candidate_denied(candidate)
            if reason:
                return reason
        return None

    def _candidate_denied(self, candidate: Path) -> str | None:
        for part in candidate.parts:
            matched = _name_denied(part)
            if matched:
                return f"path_denied:{matched}"
            if part.casefold().startswith("aureon_run_"):
                return "path_denied:aureon_run"
        try:
            repo_env = Path(os.path.realpath(self.repo_env_path))
        except OSError:
            repo_env = self.repo_env_path.resolve()
        if candidate == repo_env:
            return "path_denied:repo_env"
        for root in self._deny_roots():
            try:
                real_root = Path(os.path.realpath(root))
            except OSError:
                return "path_denied:deny_root_unreadable"
            if candidate == real_root or candidate.is_relative_to(real_root):
                return "path_denied:deny_root"
        return None

    def _looks_like_path(self, token: str, cwd: Path) -> bool:
        if not token or token.startswith("-") or any(character.isspace() for character in token):
            return False
        # A python -c snippet is not a path. The mount namespace hides the file.
        if any(character in token for character in "()\"'`$;|&"):
            return False
        if token.lower().startswith("file:"):
            return True
        if "/" in token or "\\" in token or token.startswith("~") or token.startswith("."):
            return True
        try:
            candidate = cwd / token
            if candidate.exists() or candidate.is_symlink():
                return True
        except OSError:
            return True
        return False

    def _resolve_token(self, token: str, cwd: Path) -> Path:
        if token.lower().startswith("file:"):
            file_path = _file_url_to_path(token)
            if file_path is None:
                raise ValueError("file_url_unreadable")
            return file_path
        expanded = os.path.expanduser(token)
        if os.path.isabs(expanded):
            return Path(expanded)
        return cwd / expanded

    def _argv_denied(self, argv: Sequence[str], cwd: Path) -> str | None:
        cwd_reason = self.path_denied(cwd)
        if cwd_reason:
            return cwd_reason
        for token in argv:
            if not self._looks_like_path(token, cwd):
                continue
            try:
                resolved = self._resolve_token(token, cwd)
            except (OSError, ValueError):
                return "path_unreadable"
            reason = self.path_denied(resolved)
            if reason:
                return reason
        return None

    def _audit(self, action: str, args: Mapping[str, Any], summary: Mapping[str, Any], screenshot_path: str | None) -> None:
        entry = {
            "ts": datetime.datetime.now(datetime.UTC).isoformat(),
            "action": action,
            "args": _jsonable(_redact_audit_args(action, args)),
            "result": _jsonable(_redact_audit_summary(summary)),
            "screenshot_path": screenshot_path,
        }
        try:
            line = json.dumps(entry, ensure_ascii=False, default=str)
            with self._audit_lock:
                self.audit_path.parent.mkdir(parents=True, exist_ok=True)
                with self.audit_path.open("a", encoding="utf-8") as handle:
                    handle.write(line + "\n")
        except OSError as exc:
            logger.warning("computer_use audit write failed: %s", exc)

    def _finish(
        self,
        action: str,
        args: Mapping[str, Any],
        *,
        ok: bool,
        status: str,
        error: str = "",
        extra: Mapping[str, Any] | None = None,
        screenshot_path: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "ok": ok,
            "success": ok,
            "status": status,
            "action": action,
        }
        if error:
            body["error"] = error
        if extra:
            body.update(dict(extra))
        if screenshot_path:
            body["path"] = screenshot_path
            body["screenshot_path"] = screenshot_path
        summary = {"ok": ok, "status": status, "error": error}
        for key in ("returncode", "width", "height", "bytes"):
            if key in body:
                summary[key] = body[key]
        self._audit(action, args, summary, screenshot_path)
        return body

    def _guard(self, action: str, args: Mapping[str, Any]) -> dict[str, Any] | None:
        if self.stop_file_active():
            return self._finish(
                action,
                args,
                ok=False,
                status="stopped",
                error="computer_use_stop_file",
            )
        return None

    def _coordinate(self, value: Any, name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name}_invalid")
        return int(value)

    def screenshot(self) -> dict[str, Any]:
        args: dict[str, Any] = {}
        stopped = self._guard("screenshot", args)
        if stopped:
            return stopped
        try:
            data = self._backend_or_default().screenshot_png()
            if not isinstance(data, (bytes, bytearray)) or not data.startswith(b"\x89PNG"):
                raise ValueError("screenshot_not_png")
            width, height = _png_size(bytes(data))
            path = _write_new_screenshot(self.screenshot_dir, bytes(data))
        except Exception as exc:
            logger.warning("screenshot failed: %s", exc)
            return self._finish("screenshot", args, ok=False, status="error", error=type(exc).__name__)
        return self._finish(
            "screenshot",
            args,
            ok=True,
            status="ok",
            extra={"width": width, "height": height, "bytes": path.stat().st_size},
            screenshot_path=str(path),
        )

    def move(self, x: Any, y: Any, duration: float = 0.0) -> dict[str, Any]:
        args = {"x": x, "y": y, "duration": duration}
        stopped = self._guard("move", args)
        if stopped:
            return stopped
        try:
            self._backend_or_default().move(self._coordinate(x, "x"), self._coordinate(y, "y"), float(duration))
        except Exception as exc:
            return self._finish("move", args, ok=False, status="error", error=type(exc).__name__)
        return self._finish("move", args, ok=True, status="ok")

    def click(self, x: Any, y: Any, button: str = "left", clicks: int = 1) -> dict[str, Any]:
        args = {"x": x, "y": y, "button": button, "clicks": clicks}
        stopped = self._guard("click", args)
        if stopped:
            return stopped
        try:
            self._backend_or_default().click(
                self._coordinate(x, "x"),
                self._coordinate(y, "y"),
                str(button or "left"),
                int(clicks),
            )
        except Exception as exc:
            return self._finish("click", args, ok=False, status="error", error=type(exc).__name__)
        return self._finish("click", args, ok=True, status="ok")

    def double_click(self, x: Any, y: Any, button: str = "left") -> dict[str, Any]:
        args = {"x": x, "y": y, "button": button, "clicks": 2}
        stopped = self._guard("double_click", args)
        if stopped:
            return stopped
        try:
            self._backend_or_default().click(
                self._coordinate(x, "x"),
                self._coordinate(y, "y"),
                str(button or "left"),
                2,
            )
        except Exception as exc:
            return self._finish("double_click", args, ok=False, status="error", error=type(exc).__name__)
        return self._finish("double_click", args, ok=True, status="ok")

    def drag(self, x: Any, y: Any, x2: Any, y2: Any, button: str = "left") -> dict[str, Any]:
        args = {"x": x, "y": y, "x2": x2, "y2": y2, "button": button}
        stopped = self._guard("drag", args)
        if stopped:
            return stopped
        try:
            self._backend_or_default().drag(
                self._coordinate(x, "x"),
                self._coordinate(y, "y"),
                self._coordinate(x2, "x2"),
                self._coordinate(y2, "y2"),
                str(button or "left"),
            )
        except Exception as exc:
            return self._finish("drag", args, ok=False, status="error", error=type(exc).__name__)
        return self._finish("drag", args, ok=True, status="ok")

    def scroll(self, x: Any, y: Any, amount: Any) -> dict[str, Any]:
        args = {"x": x, "y": y, "amount": amount}
        stopped = self._guard("scroll", args)
        if stopped:
            return stopped
        try:
            if isinstance(amount, bool) or not isinstance(amount, (int, float)):
                raise ValueError("amount_invalid")
            self._backend_or_default().scroll(int(amount), self._coordinate(x, "x"), self._coordinate(y, "y"))
        except Exception as exc:
            return self._finish("scroll", args, ok=False, status="error", error=type(exc).__name__)
        return self._finish("scroll", args, ok=True, status="ok")

    def type_text(self, text: Any, interval: float = 0.02) -> dict[str, Any]:
        args = {"text": text, "interval": interval}
        stopped = self._guard("type_text", args)
        if stopped:
            return stopped
        try:
            if not isinstance(text, str):
                raise ValueError("text_invalid")
            self._backend_or_default().type_text(text, float(interval))
        except Exception as exc:
            return self._finish("type_text", args, ok=False, status="error", error=type(exc).__name__)
        return self._finish("type_text", args, ok=True, status="ok")

    def press_key(self, key: Any) -> dict[str, Any]:
        args = {"key": key}
        stopped = self._guard("press_key", args)
        if stopped:
            return stopped
        try:
            if not isinstance(key, str) or not key:
                raise ValueError("key_invalid")
            self._backend_or_default().press_key(key)
        except Exception as exc:
            return self._finish("press_key", args, ok=False, status="error", error=type(exc).__name__)
        return self._finish("press_key", args, ok=True, status="ok")

    def hotkey(self, keys: Sequence[str] | str) -> dict[str, Any]:
        if isinstance(keys, str):
            sequence: list[str] = [keys]
        else:
            sequence = [str(key) for key in keys]
        args = {"keys": sequence}
        stopped = self._guard("hotkey", args)
        if stopped:
            return stopped
        try:
            if not sequence:
                raise ValueError("keys_required")
            self._backend_or_default().hotkey(sequence)
        except Exception as exc:
            return self._finish("hotkey", args, ok=False, status="error", error=type(exc).__name__)
        return self._finish("hotkey", args, ok=True, status="ok")

    def _secret_mounts(self, cwd: Path) -> list[tuple[str, str]]:
        """Files and directories the child must see as empty."""

        chosen: dict[str, str] = {}

        def add(path: Path) -> None:
            try:
                if path.is_symlink():
                    add(Path(os.path.realpath(path)))
                if not path.exists() and not path.is_symlink():
                    return
                real = Path(os.path.realpath(path))
            except OSError:
                return
            if real == Path("/") or len(real.parts) < 2:
                return
            kind = "dir" if real.is_dir() and not real.is_file() else "file"
            chosen[str(real)] = kind

        def consider(path: Path) -> None:
            if path.name.casefold().startswith("aureon_run_") or self.path_denied(path):
                add(path)

        def walk(root: Path, depth: int) -> None:
            if depth < 0:
                return
            try:
                children = list(root.iterdir())
            except OSError:
                return
            for child in children:
                consider(child)
                if child.is_dir() and not child.is_symlink() and not self.path_denied(child):
                    walk(child, depth - 1)

        for root in (cwd, REPO_ROOT, Path("/workspace")):
            consider(root)
            if root.is_dir():
                walk(root, 2 if root == cwd else 0)
        for run_dir in _run_dir_mounts():
            add(run_dir)
        for root in self._deny_roots():
            add(root)
        dirs = {path for path, kind in chosen.items() if kind == "dir"}
        mounts: list[tuple[str, str]] = []
        for path, kind in sorted(chosen.items()):
            if kind == "file" and any(path == directory or path.startswith(directory + os.sep) for directory in dirs):
                continue
            mounts.append((kind, path))
        return mounts

    def run_shell(
        self,
        argv: str | Sequence[str],
        timeout: float = 30,
        cwd: str | Path | None = None,
    ) -> dict[str, Any]:
        """Run ``argv`` with ``shell=False``. A string is split with ``shlex`` first."""

        raw_args = {"argv": argv if not isinstance(argv, str) else argv, "timeout": timeout, "cwd": None if cwd is None else os.fspath(cwd)}
        stopped = self._guard("run_shell", raw_args)
        if stopped:
            return stopped
        try:
            parsed = _coerce_argv(argv)
            timeout_s = float(timeout)
            if timeout_s <= 0:
                raise ValueError("timeout_invalid")
        except ValueError as exc:
            return self._finish("run_shell", raw_args, ok=False, status="error", error=str(exc) or "argv_invalid")
        workdir = Path(cwd) if cwd is not None else Path.cwd()
        denial = self._argv_denied(parsed, workdir)
        if denial:
            return self._finish(
                "run_shell",
                {"argv": parsed, "timeout": timeout_s, "cwd": str(workdir)},
                ok=False,
                status="denied",
                error=denial,
                extra={"stdout": "", "stderr": "", "returncode": None},
            )
        if cwd is not None and not workdir.is_dir():
            return self._finish(
                "run_shell",
                {"argv": parsed, "cwd": str(workdir)},
                ok=False,
                status="error",
                error="cwd_not_found",
                extra={"stdout": "", "stderr": "", "returncode": None},
            )
        child_env = scrub_child_environ(self._environ)
        try:
            completed = _spawn_walled(parsed, workdir if cwd is not None else None, child_env, timeout_s, self._secret_mounts(workdir))
        except subprocess.TimeoutExpired:
            return self._finish(
                "run_shell",
                {"argv": parsed, "timeout": timeout_s, "cwd": str(workdir)},
                ok=False,
                status="error",
                error="timeout",
                extra={"stdout": "", "stderr": "", "returncode": None},
            )
        except OSError as exc:
            error = "filesystem_wall_unavailable" if "filesystem_wall" in str(exc) or isinstance(exc, FileNotFoundError) else type(exc).__name__
            return self._finish(
                "run_shell",
                {"argv": parsed, "cwd": str(workdir)},
                ok=False,
                status="error",
                error=error,
                extra={"stdout": "", "stderr": "", "returncode": None},
            )
        if completed.returncode == 97:
            return self._finish(
                "run_shell",
                {"argv": parsed, "timeout": timeout_s, "cwd": str(workdir)},
                ok=False,
                status="error",
                error="filesystem_wall_unavailable",
                extra={"stdout": "", "stderr": completed.stderr[:500], "returncode": 97},
            )
        stdout = completed.stdout[:_MAX_OUTPUT_CHARS]
        stderr = completed.stderr[:_MAX_OUTPUT_CHARS]
        ok = completed.returncode == 0
        return self._finish(
            "run_shell",
            {"argv": parsed, "timeout": timeout_s, "cwd": str(workdir)},
            ok=ok,
            status="ok" if ok else "error",
            error="" if ok else f"returncode_{completed.returncode}",
            extra={"stdout": stdout, "stderr": stderr, "returncode": completed.returncode},
        )

    def open_url(self, url: str) -> dict[str, Any]:
        args = {"url": url}
        stopped = self._guard("open_url", args)
        if stopped:
            return stopped
        if not isinstance(url, str) or not url.strip():
            return self._finish("open_url", args, ok=False, status="error", error="url_invalid")
        target = url.strip()
        if target.lower().startswith("file:"):
            file_path = _file_url_to_path(target)
            if file_path is None:
                return self._finish("open_url", args, ok=False, status="error", error="file_url_unreadable")
            denial = self.path_denied(file_path)
            if denial:
                return self._finish("open_url", args, ok=False, status="denied", error=denial)
        opener = self.browser_opener
        try:
            if opener is not None:
                opener(target)
                via = "browser_tool"
            else:
                if webbrowser.open(target) is False:
                    return self._finish("open_url", args, ok=False, status="error", error="browser_open_failed")
                via = "system_browser"
        except Exception as exc:
            return self._finish("open_url", args, ok=False, status="error", error=type(exc).__name__)
        return self._finish("open_url", args, ok=True, status="ok", extra={"via": via})

    def dispatch(self, name: str, args: Mapping[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(args or {})
        action = str(name or "").strip().lower()
        try:
            if action == "screenshot":
                return self.screenshot()
            if action == "move":
                return self.move(payload.get("x"), payload.get("y"), float(payload.get("duration") or 0))
            if action == "click":
                return self.click(
                    payload.get("x"),
                    payload.get("y"),
                    str(payload.get("button") or "left"),
                    int(payload.get("clicks") or 1),
                )
            if action == "double_click":
                return self.double_click(payload.get("x"), payload.get("y"), str(payload.get("button") or "left"))
            if action == "drag":
                return self.drag(payload.get("x"), payload.get("y"), payload.get("x2"), payload.get("y2"), str(payload.get("button") or "left"))
            if action == "scroll":
                return self.scroll(payload.get("x"), payload.get("y"), payload.get("amount"))
            if action == "type_text":
                return self.type_text(payload.get("text"), float(payload.get("interval") or 0))
            if action == "press_key":
                return self.press_key(payload.get("key"))
            if action == "hotkey":
                return self.hotkey(payload.get("keys") or [])
            if action == "run_shell":
                command = payload.get("argv", payload.get("command"))
                return self.run_shell(command, timeout=float(payload.get("timeout") or 30), cwd=payload.get("cwd"))
            if action == "open_url":
                return self.open_url(str(payload.get("url") or ""))
        except Exception as exc:
            return self._finish(action or "unknown", payload, ok=False, status="error", error=type(exc).__name__)
        return self._finish(action or "unknown", payload, ok=False, status="error", error="unknown_action")


def _coerce_argv(argv: str | Sequence[str]) -> list[str]:
    if isinstance(argv, str):
        try:
            parsed = shlex.split(argv, posix=(os.name == "posix"))
        except ValueError as exc:
            raise ValueError("argv_parse_error") from exc
    elif isinstance(argv, (list, tuple)):
        parsed = [os.fspath(part) for part in argv]
    else:
        raise ValueError("argv_invalid")
    if not parsed or any(not isinstance(part, str) or part == "" for part in parsed):
        raise ValueError("argv_empty")
    return parsed


def _file_url_to_path(url: str) -> Path | None:
    parsed = urlsplit(url)
    if parsed.scheme.lower() != "file":
        return None
    path = unquote(parsed.path or "")
    if os.name == "nt" and path.startswith("/") and len(path) > 3 and path[2] == ":":
        path = path[1:]
    if not path:
        return None
    return Path(path)


def openai_computer_tools() -> list[dict[str, Any]]:
    """OpenAI-style tool definitions for the computer-use actions."""

    def tool(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                    "additionalProperties": False,
                },
            },
        }

    number = {"type": "number"}
    text = {"type": "string"}
    return [
        tool("screenshot", "Capture the screen and return a PNG path and size.", {}, []),
        tool("move", "Move the pointer.", {"x": number, "y": number, "duration": number}, ["x", "y"]),
        tool("click", "Click at screen coordinates.", {"x": number, "y": number, "button": text, "clicks": number}, ["x", "y"]),
        tool("double_click", "Double-click at screen coordinates.", {"x": number, "y": number, "button": text}, ["x", "y"]),
        tool("drag", "Drag from one point to another.", {"x": number, "y": number, "x2": number, "y2": number, "button": text}, ["x", "y", "x2", "y2"]),
        tool("scroll", "Scroll at a point.", {"x": number, "y": number, "amount": number}, ["x", "y", "amount"]),
        tool("type_text", "Type text into the focused window.", {"text": text, "interval": number}, ["text"]),
        tool("press_key", "Press one key.", {"key": text}, ["key"]),
        tool("hotkey", "Press a key chord.", {"keys": {"type": "array", "items": text}}, ["keys"]),
        tool(
            "run_shell",
            "Run an argv list with shell disabled. A string is split with shlex.",
            {"argv": {"type": "array", "items": text}, "command": text, "timeout": number, "cwd": text},
            [],
        ),
        tool("open_url", "Open a URL in the browser tool or the system browser.", {"url": text}, ["url"]),
    ]


def register_computer_use_tools(registry: Any, computer: ComputerUse | None = None) -> None:
    """Register computer-use actions on an admin-plane tool registry."""

    from aureon.inhouse_ai.tool_registry import ToolEffect

    holder: dict[str, ComputerUse | None] = {"computer": computer}

    def _computer() -> ComputerUse:
        if holder["computer"] is None:
            holder["computer"] = ComputerUse()
        return holder["computer"]

    def _bind(action: str) -> Callable[[dict[str, Any]], str]:
        def handler(args: dict[str, Any]) -> str:
            return json.dumps(_computer().dispatch(action, args or {}), default=str)
        return handler

    specs = (
        ("screenshot", "Capture the screen to a PNG.", ToolEffect.READ_ONLY, {}, []),
        ("move", "Move the pointer.", ToolEffect.PRIVILEGED, {"x": {"type": "number"}, "y": {"type": "number"}}, ["x", "y"]),
        ("click", "Click at screen coordinates.", ToolEffect.PRIVILEGED, {"x": {"type": "number"}, "y": {"type": "number"}, "button": {"type": "string"}}, ["x", "y"]),
        ("double_click", "Double-click at screen coordinates.", ToolEffect.PRIVILEGED, {"x": {"type": "number"}, "y": {"type": "number"}}, ["x", "y"]),
        ("drag", "Drag between two points.", ToolEffect.PRIVILEGED, {"x": {"type": "number"}, "y": {"type": "number"}, "x2": {"type": "number"}, "y2": {"type": "number"}}, ["x", "y", "x2", "y2"]),
        ("scroll", "Scroll at a point.", ToolEffect.PRIVILEGED, {"x": {"type": "number"}, "y": {"type": "number"}, "amount": {"type": "number"}}, ["x", "y", "amount"]),
        ("type_text", "Type text.", ToolEffect.PRIVILEGED, {"text": {"type": "string"}}, ["text"]),
        ("press_key", "Press one key.", ToolEffect.PRIVILEGED, {"key": {"type": "string"}}, ["key"]),
        ("hotkey", "Press a key chord.", ToolEffect.PRIVILEGED, {"keys": {"type": "array", "items": {"type": "string"}}}, ["keys"]),
        ("run_shell", "Run an argv command with shell disabled.", ToolEffect.PRIVILEGED, {"argv": {"type": "array", "items": {"type": "string"}}, "command": {"type": "string"}, "cwd": {"type": "string"}, "timeout": {"type": "number"}}, []),
        ("open_url", "Open a URL.", ToolEffect.PRIVILEGED, {"url": {"type": "string"}}, ["url"]),
    )
    for name, description, effect, properties, required in specs:
        registry.define_tool(
            name,
            description,
            {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
            _bind(name),
            effect=effect,
            operation_id=f"aureon.computer_use.{name}.v1",
        )
