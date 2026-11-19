"""Headless Chrome/Chromium controller for the in-house tool registry.

The session is a Chrome process started with ``--headless=new`` and a
loopback DevTools port. Commands go over the Chrome DevTools Protocol on a
small stdlib WebSocket client. No Playwright dependency.

URL policy, checked before navigation, again on the settled location, and on
every network request before Chrome sends it:

* ``file://`` only inside the single directory named by
  ``AUREON_BROWSER_FILE_ROOT``. Secret names (``.env*``, ``id_*``, ``*.key``,
  ``*.pem``), keyring/credential directories, the repo ``state/`` tree, and
  run folders (``aureon_run_*``, ``/workspace/aureon_run_*``, the live Chrome
  profile) are refused even when a symlink is used. The check uses the
  resolved real path.
* ``http://127.0.0.1``, ``http://localhost``, and ``http://[::1]`` only.
  ``127.0.0.2`` and every other host are refused unless named in
  ``AUREON_BROWSER_ALLOW_HOSTS`` (comma-separated hostnames, not a pattern;
  ``*`` is ignored).
* CDP Fetch fails a non-allowed request before it is sent. Chrome is also
  started with ``--host-resolver-rules`` mapping every other hostname to
  ``~NOTFOUND``.

Screenshots are written only inside ``state/browser_screens`` (or
``AUREON_BROWSER_SCREENSHOT_DIR``), with a generated name unless the caller
passes a single filename. Existing files and symlinks are refused. Parent
directories outside that folder are not created.

The audit log is ``state/browser_tool_audit.jsonl``. Typed text and page text
are stored as ``text_length`` and ``text_sha256`` only. Cookies, headers, and
plaintext field values are not written. ``AUREON_BROWSER_AUDIT_PATH`` or
``BrowserTool(audit_path=...)`` redirects the log.
"""

from __future__ import annotations

import atexit
import base64
import hashlib
import ipaddress
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_EXACT_LOOPBACK_IPS = frozenset({"127.0.0.1", "::1"})
_BROWSER_ACTIONS = ("open", "read_text", "click", "type", "screenshot")
_AUDIT_ENV = "AUREON_BROWSER_AUDIT_PATH"
_ALLOW_ENV = "AUREON_BROWSER_ALLOW_HOSTS"
_FILE_ROOT_ENV = "AUREON_BROWSER_FILE_ROOT"
_SCREENSHOT_ENV = "AUREON_BROWSER_SCREENSHOT_DIR"
_CHROME_ENV = "AUREON_BROWSER_CHROME"
_SECRET_FILE_RE = re.compile(r"(^\.env($|\.))|(^id_)|(\.(?:key|pem)$)", re.IGNORECASE)
_SECRET_DIR_RE = re.compile(r"^(?:keyrings?|credentials?|secrets?)$", re.IGNORECASE)
_RUN_DIR_RE = re.compile(r"^(?:aureon_run_.*|aureon-browser-.*)$", re.IGNORECASE)
_CHROME_NAMES = (
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "chrome",
)
_CHROME_PATHS = (
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/local/bin/google-chrome",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
)
_MAX_FRAME_BYTES = 20_000_000
_READ_TEXT_CAP = 100_000

BROWSER_TOOL_DESCRIPTION = (
    "Drive the local headless Chrome/Chromium session through the Chrome DevTools Protocol. "
    "action is one of open, read_text, click, type, screenshot. "
    "open requires url. file:// is limited to AUREON_BROWSER_FILE_ROOT and refuses secret, "
    "state, and run paths, including symlink targets. "
    "http is limited to 127.0.0.1, localhost, and [::1] unless AUREON_BROWSER_ALLOW_HOSTS "
    "names the host. Non-allowed requests are failed before they are sent. "
    "click and type require css_selector; type also requires text. "
    "screenshot writes a PNG inside the screenshot directory only. "
    "The audit log records text as length and sha256."
)

_registry_lock = threading.Lock()
_registry_tool: BrowserTool | None = None


class _NavGap(RuntimeError):
    """The page's execution context disappeared mid-navigation."""


def browser_input_schema() -> dict[str, Any]:
    """JSON schema for the ``browser`` tool. One object, one action."""

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["action"],
        "properties": {
            "action": {
                "type": "string",
                "enum": list(_BROWSER_ACTIONS),
                "description": "Which browser action to run on the shared headless session.",
            },
            "url": {
                "type": "string",
                "description": (
                    "Required for open. file://, or http on 127.0.0.1 / localhost / ::1, "
                    "unless AUREON_BROWSER_ALLOW_HOSTS names the host."
                ),
            },
            "css_selector": {
                "type": "string",
                "description": "Required for click and type. CSS selector of the target element.",
            },
            "text": {
                "type": "string",
                "description": "Required for type. Characters inserted into the targeted element.",
            },
            "path": {
                "type": "string",
                "description": (
                    "Optional screenshot filename. A directory, parent segment, or absolute path "
                    "is refused. Omit it and the tool generates a name inside the screenshot directory."
                ),
            },
        },
    }


def default_audit_path() -> Path:
    """Audit log path for this process.

    An explicit ``BrowserTool`` path wins over this. Otherwise
    ``AUREON_BROWSER_AUDIT_PATH`` redirects the log, and the default is
    ``state/browser_tool_audit.jsonl`` relative to the current directory.
    """

    override = os.environ.get(_AUDIT_ENV, "").strip()
    if override:
        return Path(override)
    return Path("state") / "browser_tool_audit.jsonl"


def allow_hosts_from_env() -> frozenset[str]:
    """Hosts named by ``AUREON_BROWSER_ALLOW_HOSTS``. Empty when unset."""

    raw = os.environ.get(_ALLOW_ENV, "")
    return _normalize_hosts(part for part in raw.split(","))


def file_root_from_env() -> Path | None:
    """The one scratch root for ``file://``. Unset means every file URL is refused."""

    raw = os.environ.get(_FILE_ROOT_ENV, "").strip()
    if not raw:
        return None
    return Path(raw).expanduser()


def default_screenshot_dir() -> Path:
    """Directory that may receive screenshot PNGs. Parents are not created."""

    override = os.environ.get(_SCREENSHOT_ENV, "").strip()
    if override:
        return Path(override).expanduser()
    return Path("state") / "browser_screens"


def find_chrome_binary() -> str | None:
    """Return a Chrome or Chromium executable, or None when nothing is installed."""

    override = os.environ.get(_CHROME_ENV, "").strip()
    if override and _executable(override):
        return override
    for name in _CHROME_NAMES:
        found = shutil.which(name)
        if found and _executable(found):
            return found
    for candidate in _CHROME_PATHS:
        if _executable(candidate):
            return candidate
    return None


def url_refusal(
    url: str,
    allow_hosts: Iterable[str] | None = None,
    file_root: Path | None | str = None,
    run_dirs: Iterable[Path] | None = None,
) -> str | None:
    """Return a refusal reason, or None when the URL is allowed.

    ``allow_hosts`` replaces the environment host allowlist. None reads
    ``AUREON_BROWSER_ALLOW_HOSTS``. ``file_root`` replaces
    ``AUREON_BROWSER_FILE_ROOT``. Pass ``""`` to force no scratch root.
    """

    raw = str(url or "").strip()
    if not raw or any(char in raw for char in "\r\n\t "):
        return "url refused: empty or contains whitespace"
    try:
        parts = urllib.parse.urlsplit(raw)
    except ValueError as exc:
        return f"url refused: {exc}"
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    extra = allow_hosts_from_env() if allow_hosts is None else _normalize_hosts(allow_hosts)
    if scheme == "file":
        if host and host not in _LOOPBACK_HOSTS:
            return f"file URL host refused: {host}"
        root = _coerce_file_root(file_root)
        return _file_path_refusal(_path_from_file_url(raw), file_root=root, run_dirs=run_dirs or ())
    if scheme not in {"http", "https"}:
        return f"scheme refused: {scheme or '(missing)'}"
    if not host:
        return "host refused: (missing)"
    names = set(_LOOPBACK_HOSTS) | set(extra)
    if host not in names:
        return f"host refused: {host}"
    if host in extra and host not in _LOOPBACK_HOSTS:
        return None
    try:
        ips = _ips_for_host(host)
    except OSError as exc:
        return f"host refused: {host} ({exc.__class__.__name__})"
    if ips and all(_is_exact_loopback(ip) for ip in ips):
        return None if scheme == "http" or host in extra else f"host refused: {host}"
    return f"host refused: {host}"


def dispatch_browser_tool(args: Mapping[str, Any] | None) -> str:
    """Run one browser action on the process session and return a JSON string."""

    payload = dict(args) if isinstance(args, Mapping) else {}
    try:
        result = registry_browser().dispatch(payload)
    except Exception as exc:  # noqa: BLE001 — the tool result has to carry the failure
        result = {
            "ok": False,
            "action": str(payload.get("action") or ""),
            "refused": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
    return json.dumps(result, ensure_ascii=False)


def registry_browser() -> BrowserTool:
    """The session built-in handlers share. Created on first use, not at import."""

    global _registry_tool
    with _registry_lock:
        if _registry_tool is None:
            tool = BrowserTool()
            _registry_tool = tool
            atexit.register(tool.close)
        return _registry_tool


def reset_registry_browser() -> None:
    """Close the shared session so the next call starts clean. Used by tests."""

    global _registry_tool
    with _registry_lock:
        tool = _registry_tool
        _registry_tool = None
    if tool is not None:
        tool.close()


class BrowserTool:
    """One headless Chrome session. Actions are serialized on an instance lock."""

    def __init__(
        self,
        audit_path: str | Path | None = None,
        allow_hosts: Iterable[str] | None = None,
        chrome_binary: str | None = None,
        file_root: str | Path | None = None,
        screenshot_dir: str | Path | None = None,
    ) -> None:
        self._audit_path = None if audit_path is None else Path(audit_path)
        self._allow_hosts = None if allow_hosts is None else _normalize_hosts(allow_hosts)
        self._file_root = None if file_root is None else Path(file_root).expanduser()
        self._screenshot_dir = None if screenshot_dir is None else Path(screenshot_dir).expanduser()
        self._chrome_binary = chrome_binary
        self._lock = threading.Lock()
        self._proc: subprocess.Popen[bytes] | None = None
        self._stderr: Any = None
        self._user_data: Path | None = None
        self._ws: _CdPSocket | None = None
        self._session: _PageSession | None = None
        self._closed = False
        self._blocked: list[dict[str, str]] = []
        self._shot_seq = 0

    def __enter__(self) -> BrowserTool:
        return self

    def __exit__(self, *_exc: object) -> bool:
        self.close()
        return False

    @property
    def started(self) -> bool:
        return self._proc is not None

    def close(self) -> None:
        with self._lock:
            self._shutdown_locked()

    def dispatch(self, args: Mapping[str, Any]) -> dict[str, Any]:
        action = str(args.get("action") or "").strip()
        if action not in _BROWSER_ACTIONS:
            return self._locked_finish(
                action or "(missing)",
                ok=False,
                error="action must be one of open, read_text, click, type, screenshot",
            )
        if action == "open":
            url = args.get("url")
            if not isinstance(url, str) or not url.strip():
                return self._locked_finish("open", ok=False, error="url is required")
            return self.open(url)
        if action == "read_text":
            return self.read_text()
        if action == "click":
            selector = args.get("css_selector")
            if not isinstance(selector, str) or not selector.strip():
                return self._locked_finish("click", ok=False, error="css_selector is required")
            return self.click(selector)
        if action == "type":
            selector = args.get("css_selector")
            text = args.get("text")
            if not isinstance(selector, str) or not selector.strip():
                return self._locked_finish("type", ok=False, error="css_selector is required")
            if not isinstance(text, str):
                return self._locked_finish("type", ok=False, error="text is required", css_selector=selector)
            return self.type(selector, text)
        path = args.get("path", "")
        if path is None:
            path = ""
        if not isinstance(path, str):
            return self._locked_finish("screenshot", ok=False, error="path must be a string")
        return self.screenshot(path)

    def open(self, url: str) -> dict[str, Any]:
        with self._lock:
            try:
                return self._open_locked(url)
            except Exception as exc:  # noqa: BLE001 — recorded, not raised into the tool caller
                return self._finish("open", ok=False, error=f"{type(exc).__name__}: {exc}", url=url)

    def read_text(self) -> dict[str, Any]:
        with self._lock:
            try:
                return self._read_text_locked()
            except Exception as exc:  # noqa: BLE001
                return self._finish("read_text", ok=False, error=f"{type(exc).__name__}: {exc}")

    def click(self, css_selector: str) -> dict[str, Any]:
        with self._lock:
            try:
                return self._click_locked(css_selector)
            except Exception as exc:  # noqa: BLE001
                return self._finish(
                    "click",
                    ok=False,
                    error=f"{type(exc).__name__}: {exc}",
                    css_selector=css_selector,
                )

    def type(self, css_selector: str, text: str) -> dict[str, Any]:
        with self._lock:
            try:
                return self._type_locked(css_selector, text)
            except Exception as exc:  # noqa: BLE001
                return self._finish(
                    "type",
                    ok=False,
                    error=f"{type(exc).__name__}: {exc}",
                    css_selector=css_selector,
                    text=text,
                )

    def screenshot(self, path: str = "") -> dict[str, Any]:
        with self._lock:
            try:
                return self._screenshot_locked(path)
            except Exception as exc:  # noqa: BLE001
                return self._finish("screenshot", ok=False, error=f"{type(exc).__name__}: {exc}", path=path)

    def _open_locked(self, url: str) -> dict[str, Any]:
        refusal = self._refusal(url)
        if refusal:
            return self._finish("open", ok=False, refused=True, error=refusal, url=url)
        self._ensure_started()
        assert self._session is not None
        mark = len(self._blocked)
        previous = str(self._evaluate("location.href", missing_ok=True) or "")
        navigated = self._session.call("Page.navigate", {"url": url})
        error_text = str(navigated.get("errorText") or "")
        if error_text:
            return self._finish("open", ok=False, error=error_text, url=url)
        try:
            final = self._wait_for_navigation(previous, url)
        except TimeoutError:
            final = str(self._evaluate("location.href", missing_ok=True) or "")
        self._session.pump(0.6)
        blocked = self._blocked[mark:]
        if blocked:
            return self._finish(
                "open",
                ok=False,
                refused=True,
                blocked=True,
                reason="blocked",
                error="request blocked",
                url=url,
                final_url=final,
            )
        final_refusal = self._refusal(final) if final else "off_host"
        if final_refusal:
            self._blank()
            reason = "off_host" if _is_off_host_reason(final_refusal) else ""
            return self._finish(
                "open",
                ok=False,
                refused=True,
                reason=reason or "refused",
                error=final_refusal if final_refusal != "off_host" else "off_host",
                url=url,
                final_url=final,
            )
        return self._finish("open", ok=True, url=url, final_url=final)

    def _read_text_locked(self) -> dict[str, Any]:
        if self._session is None:
            return self._finish("read_text", ok=False, error="no page open")
        self._session.pump(0.2)
        off = self._location_off_host()
        if off:
            return self._finish("read_text", ok=False, refused=True, reason="off_host", error="off_host")
        raw = self._evaluate(
            "(document.body && (document.body.innerText || document.body.textContent)) || ''"
        )
        text = raw if isinstance(raw, str) else ""
        truncated = len(text) > _READ_TEXT_CAP
        if truncated:
            text = text[:_READ_TEXT_CAP]
        return self._finish("read_text", ok=True, text=text, extra={"truncated": truncated})

    def _click_locked(self, css_selector: str) -> dict[str, Any]:
        if self._session is None:
            return self._finish("click", ok=False, error="no page open", css_selector=css_selector)
        mark = len(self._blocked)
        error = self._click_selector(css_selector)
        if error:
            return self._finish("click", ok=False, error=error, css_selector=css_selector)
        self._session.pump(1.2)
        return self._after_gesture("click", mark, css_selector=css_selector)

    def _type_locked(self, css_selector: str, text: str) -> dict[str, Any]:
        if self._session is None:
            return self._finish(
                "type",
                ok=False,
                error="no page open",
                css_selector=css_selector,
                text=text,
            )
        off = self._location_off_host()
        if off:
            return self._finish(
                "type",
                ok=False,
                refused=True,
                reason="off_host",
                error="off_host",
                css_selector=css_selector,
                text=text,
            )
        mark = len(self._blocked)
        error = self._replace_text(css_selector, text)
        self._session.pump(0.4)
        if error:
            return self._finish("type", ok=False, error=error, css_selector=css_selector, text=text)
        return self._after_gesture("type", mark, css_selector=css_selector, text=text)

    def _screenshot_locked(self, path: str) -> dict[str, Any]:
        name_problem = _screenshot_name_problem(path)
        if name_problem:
            return self._finish("screenshot", ok=False, refused=True, error=name_problem, path=path)
        if self._session is None:
            return self._finish("screenshot", ok=False, error="no page open", path=path)
        target, problem = self._screenshot_target(path)
        if problem or target is None:
            return self._finish("screenshot", ok=False, refused=True, error=problem or "screenshot path refused", path=path)
        off = self._location_off_host()
        if off:
            return self._finish(
                "screenshot",
                ok=False,
                refused=True,
                reason="off_host",
                error="off_host",
                path=str(target),
            )
        captured = self._session.call(
            "Page.captureScreenshot",
            {"format": "png", "fromSurface": True},
        )
        encoded = captured.get("data")
        if not isinstance(encoded, str) or not encoded:
            return self._finish("screenshot", ok=False, error="screenshot returned no data", path=str(target))
        try:
            raw = base64.b64decode(encoded, validate=False)
        except (ValueError, TypeError) as exc:
            return self._finish("screenshot", ok=False, error=f"screenshot decode failed: {exc}", path=str(target))
        if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
            return self._finish("screenshot", ok=False, error="screenshot was not a PNG", path=str(target))
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(target, flags, 0o600)
        except FileExistsError:
            return self._finish("screenshot", ok=False, refused=True, error="screenshot already exists", path=str(target))
        except OSError as exc:
            return self._finish("screenshot", ok=False, refused=True, error=f"screenshot refused: {exc.errno}", path=str(target))
        try:
            os.write(fd, raw)
        finally:
            os.close(fd)
        return self._finish(
            "screenshot",
            ok=True,
            path=str(target),
            extra={"byte_count": len(raw)},
        )

    def _screenshot_target(self, requested: str) -> tuple[Path | None, str]:
        directory = self._screenshot_dir if self._screenshot_dir is not None else default_screenshot_dir()
        if directory.is_symlink() or (directory.exists() and directory.is_symlink()):
            return None, "screenshot dir is a symlink"
        parent = directory.parent
        if not parent.exists() or parent.is_symlink():
            return None, "screenshot dir parent refused"
        try:
            directory.mkdir(exist_ok=True)
        except OSError:
            return None, "screenshot dir refused"
        if directory.is_symlink() or not directory.is_dir():
            return None, "screenshot dir refused"
        name = requested.strip()
        if name:
            bare = Path(name)
            if bare.name != name or name in {".", ".."} or "/" in name or "\\" in name or "\x00" in name:
                return None, "screenshot path refused"
            target = directory / bare.name
        else:
            self._shot_seq += 1
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
            target = directory / f"shot-{stamp}-{self._shot_seq}.png"
        try:
            if target.is_symlink():
                return None, "screenshot symlink refused"
            if target.parent.resolve() != directory.resolve():
                return None, "screenshot path refused"
        except OSError:
            return None, "screenshot path refused"
        return target, ""

    def _after_gesture(self, action: str, mark: int, **fields: Any) -> dict[str, Any]:
        blocked = self._blocked[mark:]
        if blocked:
            return self._finish(
                action,
                ok=False,
                refused=True,
                blocked=True,
                reason="blocked",
                error="request blocked",
                **fields,
            )
        if self._location_off_host():
            return self._finish(action, ok=False, refused=True, reason="off_host", error="off_host", **fields)
        return self._finish(action, ok=True, **fields)

    def _location_off_host(self) -> bool:
        if self._session is None:
            return True
        href = self._evaluate("location.href", missing_ok=True)
        if not isinstance(href, str) or not href:
            return True
        scheme = urllib.parse.urlsplit(href).scheme.lower()
        if scheme in {"about", "blob", "data", "chrome", "chrome-error"}:
            return True
        return self._refusal(href) is not None

    def _blank(self) -> None:
        if self._session is None:
            return
        try:
            self._session.call("Page.navigate", {"url": "about:blank"})
        except (RuntimeError, TimeoutError, ConnectionError, OSError):
            return

    def _refusal(self, url: str) -> str | None:
        return url_refusal(
            url,
            allow_hosts=self._current_allow_hosts(),
            file_root=self._current_file_root() if self._current_file_root() is not None else "",
            run_dirs=self._run_dirs(),
        )

    def _request_reason(self, url: str) -> str | None:
        scheme = urllib.parse.urlsplit(str(url or "")).scheme.lower()
        if scheme in {"about", "data", "blob"}:
            return None
        reason = self._refusal(url)
        if reason:
            return "off_host" if _is_off_host_reason(reason) else "blocked"
        return None

    def _on_request_paused(self, params: Mapping[str, Any]) -> None:
        request = params.get("request") if isinstance(params.get("request"), dict) else {}
        url = str(request.get("url") or "")
        request_id = params.get("requestId")
        if not request_id or self._session is None:
            return
        reason = self._request_reason(url)
        if reason:
            host = (urllib.parse.urlsplit(url).hostname or "").lower()
            self._blocked.append({"host": host, "reason": reason})
            self._session.send_ignored(
                "Fetch.failRequest",
                {"requestId": request_id, "errorReason": "BlockedByClient"},
            )
            return
        self._session.send_ignored("Fetch.continueRequest", {"requestId": request_id})

    def _current_allow_hosts(self) -> frozenset[str]:
        if self._allow_hosts is not None:
            return self._allow_hosts
        return allow_hosts_from_env()

    def _current_file_root(self) -> Path | None:
        if self._file_root is not None:
            return self._file_root
        return file_root_from_env()

    def _run_dirs(self) -> tuple[Path, ...]:
        if self._user_data is None:
            return ()
        return (self._user_data,)

    def _ensure_started(self) -> None:
        if self._session is not None and self._proc is not None and self._proc.poll() is None:
            return
        self._shutdown_locked()
        self._closed = False
        last = "chrome did not start"
        for _attempt in range(2):
            try:
                self._start_once()
                return
            except Exception as exc:  # noqa: BLE001 — one fresh port, then surface the error
                last = f"{type(exc).__name__}: {exc}"
                self._shutdown_locked()
                self._closed = False
        raise RuntimeError(last)

    def _start_once(self) -> None:
        binary = self._chrome_binary or find_chrome_binary()
        if not binary:
            raise RuntimeError("no Chrome/Chromium binary found")
        port = _free_port()
        user_data = Path(tempfile.mkdtemp(prefix="aureon-browser-"))
        stderr_path = user_data / "chrome-stderr.log"
        stderr = stderr_path.open("ab")
        cmd = [
            binary,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-networking",
            "--disable-sync",
            "--disable-translate",
            "--mute-audio",
            "--disable-breakpad",
            "--allow-file-access-from-files",
            f"--host-resolver-rules={_host_resolver_rules(self._current_allow_hosts())}",
            f"--remote-debugging-port={port}",
            "--remote-allow-origins=*",
            f"--user-data-dir={user_data}",
            "--window-size=1280,800",
            "about:blank",
        ]
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(user_data),
            "TMPDIR": os.environ.get("TMPDIR", "/tmp"),
            "LANG": os.environ.get("LANG", "C.UTF-8"),
        }
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=stderr,
            env=env,
            start_new_session=True,
        )
        self._proc = proc
        self._stderr = stderr
        self._user_data = user_data
        self._wait_devtools(port)
        target = self._page_target(port)
        ws_url = str(target.get("webSocketDebuggerUrl") or "")
        if not ws_url.startswith("ws://"):
            raise RuntimeError("page target has no loopback websocket")
        parsed = urllib.parse.urlsplit(ws_url)
        if (parsed.hostname or "").lower() not in _LOOPBACK_HOSTS:
            raise RuntimeError(f"devtools websocket host refused: {parsed.hostname}")
        sock = _CdPSocket(ws_url, timeout=15.0)
        self._ws = sock
        session = _PageSession(sock, on_request=self._on_request_paused)
        self._session = session
        session.call("Page.enable")
        session.call("Runtime.enable")
        session.call(
            "Fetch.enable",
            {"patterns": [{"urlPattern": "*", "requestStage": "Request"}]},
        )
        session.call(
            "Emulation.setDeviceMetricsOverride",
            {"width": 1280, "height": 800, "deviceScaleFactor": 1, "mobile": False},
        )

    def _wait_devtools(self, port: int) -> None:
        deadline = time.monotonic() + 15.0
        url = f"http://127.0.0.1:{port}/json/version"
        last = ""
        while time.monotonic() < deadline:
            if self._proc is not None and self._proc.poll() is not None:
                raise RuntimeError(f"chrome exited {self._proc.returncode}: {self._stderr_tail()}")
            try:
                payload = _http_json(url)
            except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
                last = str(exc)
                time.sleep(0.1)
                continue
            if isinstance(payload, dict) and payload.get("webSocketDebuggerUrl"):
                return
            time.sleep(0.1)
        raise TimeoutError(f"devtools endpoint did not open: {last}; {self._stderr_tail()}")

    def _page_target(self, port: int) -> dict[str, Any]:
        deadline = time.monotonic() + 5.0
        url = f"http://127.0.0.1:{port}/json/list"
        while time.monotonic() < deadline:
            payload = _http_json(url)
            if isinstance(payload, list):
                pages = [
                    item
                    for item in payload
                    if isinstance(item, dict)
                    and item.get("type") == "page"
                    and isinstance(item.get("webSocketDebuggerUrl"), str)
                ]
                blank = [item for item in pages if item.get("url") == "about:blank"]
                if blank:
                    return blank[0]
                if pages:
                    return pages[0]
            time.sleep(0.1)
        raise TimeoutError("chrome exposed no page target")

    def _wait_for_navigation(self, previous: str, requested: str) -> str:
        assert self._session is not None
        deadline = time.monotonic() + 15.0
        last = previous
        while time.monotonic() < deadline:
            try:
                href = self._evaluate("location.href", missing_ok=True)
                state = self._evaluate("document.readyState", missing_ok=True)
            except _NavGap as exc:
                last = str(exc)
                time.sleep(0.05)
                continue
            if isinstance(href, str) and state == "complete" and _navigation_arrived(href, previous, requested):
                return href
            if isinstance(href, str) and href:
                last = href
            time.sleep(0.05)
        raise TimeoutError(f"navigation did not finish ({last})")

    def _evaluate(self, expression: str, *, missing_ok: bool = False) -> Any:
        assert self._session is not None
        try:
            result = self._session.call(
                "Runtime.evaluate",
                {"expression": expression, "returnByValue": True},
            )
        except RuntimeError as exc:
            if missing_ok and _context_gone(str(exc)):
                raise _NavGap(str(exc)) from exc
            raise
        details = result.get("exceptionDetails")
        if details:
            text = _exception_text(details)
            if missing_ok and _context_gone(text):
                raise _NavGap(text)
            raise RuntimeError(text)
        remote = result.get("result") if isinstance(result.get("result"), dict) else {}
        if isinstance(remote, dict) and remote.get("subtype") == "error":
            raise RuntimeError(str(remote.get("description") or "javascript error")[:300])
        if isinstance(remote, dict):
            return remote.get("value")
        return None

    def _click_selector(self, css_selector: str) -> str | None:
        point = self._element_point(css_selector)
        if not point.get("ok"):
            return str(point.get("error") or "selector not found")
        self._mouse_click(float(point["x"]), float(point["y"]))
        return None

    def _element_point(self, css_selector: str) -> dict[str, Any]:
        selector = json.dumps(css_selector)
        expression = (
            "(() => {"
            f"const el = document.querySelector({selector});"
            "if (!el) return {ok:false, error:'selector not found'};"
            "el.scrollIntoView({block:'center', inline:'center'});"
            "const rect = el.getBoundingClientRect();"
            "if (rect.width < 1 || rect.height < 1) return {ok:false, error:'selector has no box'};"
            "return {ok:true, x: rect.left + rect.width / 2, y: rect.top + rect.height / 2};"
            "})()"
        )
        value = self._evaluate(expression)
        if not isinstance(value, dict):
            return {"ok": False, "error": "selector query failed"}
        return value

    def _mouse_click(self, x: float, y: float) -> None:
        assert self._session is not None
        for event_type, buttons in (("mouseMoved", 0), ("mousePressed", 1), ("mouseReleased", 0)):
            self._session.call(
                "Input.dispatchMouseEvent",
                {
                    "type": event_type,
                    "x": x,
                    "y": y,
                    "button": "left",
                    "buttons": buttons,
                    "clickCount": 1,
                    "pointerType": "mouse",
                },
            )

    def _replace_text(self, css_selector: str, text: str) -> str | None:
        error = self._focus(css_selector)
        if error:
            return error
        self._select_all_and_delete()
        if text:
            assert self._session is not None
            self._session.call("Input.insertText", {"text": text})
        if self._input_value(css_selector) == text:
            return None
        error = self._focus(css_selector)
        if error:
            return error
        point = self._element_point(css_selector)
        if point.get("ok"):
            self._mouse_click(float(point["x"]), float(point["y"]))
        self._select_all_and_delete()
        for char in text:
            self._key_char(char)
        actual = self._input_value(css_selector)
        if actual == text:
            return None
        return "typed value mismatch"

    def _focus(self, css_selector: str) -> str | None:
        selector = json.dumps(css_selector)
        expression = (
            "(() => {"
            f"const el = document.querySelector({selector});"
            "if (!el) return {ok:false, error:'selector not found'};"
            "el.focus();"
            "return {ok:true, active: document.activeElement === el};"
            "})()"
        )
        value = self._evaluate(expression)
        if not isinstance(value, dict) or not value.get("ok"):
            return str((value or {}).get("error") if isinstance(value, dict) else "selector not found")
        if value.get("active"):
            return None
        point = self._element_point(css_selector)
        if not point.get("ok"):
            return str(point.get("error") or "selector not found")
        self._mouse_click(float(point["x"]), float(point["y"]))
        return None

    def _input_value(self, css_selector: str) -> str:
        selector = json.dumps(css_selector)
        expression = (
            "(() => {"
            f"const el = document.querySelector({selector});"
            "if (!el) return null;"
            "return ('value' in el) ? String(el.value) : String(el.innerText || '');"
            "})()"
        )
        value = self._evaluate(expression)
        return value if isinstance(value, str) else ""

    def _select_all_and_delete(self) -> None:
        assert self._session is not None
        self._session.call(
            "Input.dispatchKeyEvent",
            {
                "type": "keyDown",
                "modifiers": 2,
                "key": "a",
                "code": "KeyA",
                "windowsVirtualKeyCode": 65,
                "nativeVirtualKeyCode": 65,
            },
        )
        self._session.call(
            "Input.dispatchKeyEvent",
            {
                "type": "keyUp",
                "modifiers": 2,
                "key": "a",
                "code": "KeyA",
                "windowsVirtualKeyCode": 65,
                "nativeVirtualKeyCode": 65,
            },
        )
        self._key_named("Backspace", 8, "Backspace")

    def _key_char(self, char: str) -> None:
        assert self._session is not None
        self._session.call(
            "Input.dispatchKeyEvent",
            {"type": "keyDown", "text": char, "unmodifiedText": char, "key": char},
        )
        self._session.call(
            "Input.dispatchKeyEvent",
            {"type": "char", "text": char, "unmodifiedText": char, "key": char},
        )
        self._session.call("Input.dispatchKeyEvent", {"type": "keyUp", "key": char})

    def _key_named(self, key: str, code: int, physical: str) -> None:
        assert self._session is not None
        for event_type in ("keyDown", "keyUp"):
            self._session.call(
                "Input.dispatchKeyEvent",
                {
                    "type": event_type,
                    "key": key,
                    "code": physical,
                    "windowsVirtualKeyCode": code,
                    "nativeVirtualKeyCode": code,
                },
            )

    def _locked_finish(self, action: str, **fields: Any) -> dict[str, Any]:
        with self._lock:
            return self._finish(action, **fields)

    def _finish(
        self,
        action: str,
        *,
        ok: bool,
        refused: bool = False,
        blocked: bool = False,
        reason: str = "",
        error: str = "",
        url: str = "",
        final_url: str = "",
        css_selector: str = "",
        text: str = "",
        path: str = "",
        extra: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if text and text in error:
            error = error.replace(text, "")
        result: dict[str, Any] = {
            "ok": bool(ok),
            "action": action,
            "refused": bool(refused) or bool(blocked),
            "error": error,
        }
        if blocked:
            result["blocked"] = True
        if reason:
            result["reason"] = reason
        if url:
            result["url"] = _audit_url(url)
        if final_url:
            result["final_url"] = _audit_url(final_url)
        if css_selector:
            result["css_selector"] = css_selector
        if action == "read_text" and ok:
            result["text"] = text
        if action == "type":
            result["text_length"] = len(text)
        if path or action == "screenshot":
            result["path"] = path
        if extra:
            for key, value in extra.items():
                if key in {"text", "cookie", "cookies", "header", "headers", "set-cookie"}:
                    continue
                result[key] = value
        self._audit(
            action=action,
            ok=bool(ok),
            refused=bool(refused) or bool(blocked),
            blocked=bool(blocked),
            reason=reason,
            error=error,
            url=url,
            final_url=final_url,
            css_selector=css_selector,
            text=text if action in {"type", "read_text"} else "",
            path=path,
            include_text_meta=action in {"type", "read_text"},
        )
        return result

    def _audit(
        self,
        *,
        action: str,
        ok: bool,
        refused: bool,
        blocked: bool,
        reason: str,
        error: str,
        url: str,
        final_url: str,
        css_selector: str,
        text: str,
        path: str,
        include_text_meta: bool,
    ) -> None:
        record: dict[str, Any] = {
            "action": action,
            "blocked": blocked,
            "css_selector": css_selector[:300],
            "error": error[:500],
            "final_url": _audit_url(final_url),
            "ok": ok,
            "path": path[:500],
            "reason": reason[:120],
            "refused": refused,
            "ts": datetime.now(UTC).isoformat(),
            "url": _audit_url(url),
        }
        if include_text_meta:
            encoded = text.encode("utf-8")
            record["text_length"] = len(text)
            record["text_sha256"] = hashlib.sha256(encoded).hexdigest()
        line = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
        target = self._audit_path if self._audit_path is not None else default_audit_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(line)

    def _stderr_tail(self) -> str:
        if self._user_data is None:
            return ""
        path = self._user_data / "chrome-stderr.log"
        try:
            data = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
        return data[-400:].replace("\n", " ")

    def _shutdown_locked(self) -> None:
        self._closed = True
        session = self._session
        self._session = None
        sock = self._ws
        self._ws = None
        if session is not None or sock is not None:
            try:
                if sock is not None:
                    sock.close()
            except OSError:
                pass
        proc = self._proc
        self._proc = None
        if proc is not None and proc.poll() is None:
            try:
                os.killpg(proc.pid, 15)
            except (ProcessLookupError, PermissionError, OSError):
                proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, 9)
                except (ProcessLookupError, OSError):
                    proc.kill()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    pass
        stderr = self._stderr
        self._stderr = None
        if stderr is not None:
            try:
                stderr.close()
            except OSError:
                pass
        user_data = self._user_data
        self._user_data = None
        if user_data is not None:
            shutil.rmtree(user_data, ignore_errors=True)


class _CdPSocket:
    """Minimal RFC 6455 client for a loopback CDP websocket. Text frames only."""

    def __init__(self, url: str, timeout: float) -> None:
        parts = urllib.parse.urlsplit(url)
        if parts.scheme != "ws":
            raise ValueError(f"unsupported websocket scheme: {parts.scheme}")
        host = parts.hostname or "127.0.0.1"
        port = parts.port
        if port is None:
            raise ValueError("websocket URL missing port")
        self._sock = socket.create_connection((host, port), timeout=timeout)
        self._sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._sock.settimeout(timeout)
        self._buf = bytearray()
        path = parts.path or "/"
        if parts.query:
            path = f"{path}?{parts.query}"
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        self._sock.sendall(request.encode("ascii"))
        header = self._read_until(b"\r\n\r\n")
        status = header.split(b"\r\n", 1)[0]
        if b" 101 " not in status:
            raise ConnectionError(f"websocket upgrade refused: {status.decode('ascii', 'replace')[:200]}")

    def send_text(self, text: str) -> None:
        payload = text.encode("utf-8")
        mask = os.urandom(4)
        header = bytearray([0x81])
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))
        header.extend(mask)
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        self._sock.sendall(bytes(header) + masked)

    def recv_text(self) -> str:
        fragments: list[bytes] = []
        opcode: int | None = None
        while True:
            first, second = self._read_exact(2)
            fin = first & 0x80
            op = first & 0x0F
            masked = second & 0x80
            length = second & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._read_exact(8))[0]
            if length > _MAX_FRAME_BYTES:
                raise ConnectionError("websocket frame too large")
            mask = self._read_exact(4) if masked else b""
            payload = self._read_exact(length) if length else b""
            if masked:
                payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
            if op == 0x8:
                raise ConnectionError("websocket closed")
            if op == 0x9:
                self._send_control(0xA, payload)
                continue
            if op == 0xA:
                continue
            if op not in (0x0, 0x1):
                raise ConnectionError(f"unsupported websocket opcode {op}")
            if op == 0x1:
                opcode = op
            fragments.append(payload)
            if fin:
                if opcode != 0x1:
                    raise ConnectionError("CDP message was not a text frame")
                return b"".join(fragments).decode("utf-8")

    def set_timeout(self, timeout: float) -> None:
        self._sock.settimeout(timeout)

    def close(self) -> None:
        try:
            self._sock.close()
        except OSError:
            pass

    def _send_control(self, opcode: int, payload: bytes) -> None:
        if len(payload) > 125:
            payload = payload[:125]
        mask = os.urandom(4)
        header = bytearray([0x80 | opcode, 0x80 | len(payload)])
        header.extend(mask)
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        self._sock.sendall(bytes(header) + masked)

    def _read_until(self, marker: bytes) -> bytes:
        while marker not in self._buf:
            chunk = self._sock.recv(4096)
            if not chunk:
                raise ConnectionError("socket closed during websocket handshake")
            self._buf.extend(chunk)
        index = self._buf.index(marker) + len(marker)
        data = bytes(self._buf[:index])
        del self._buf[:index]
        return data

    def _read_exact(self, count: int) -> bytes:
        while len(self._buf) < count:
            chunk = self._sock.recv(max(4096, count - len(self._buf)))
            if not chunk:
                raise ConnectionError("socket closed")
            self._buf.extend(chunk)
        data = bytes(self._buf[:count])
        del self._buf[:count]
        return data


class _PageSession:
    def __init__(self, sock: _CdPSocket, on_request: Callable[[Mapping[str, Any]], None] | None = None) -> None:
        self._sock = sock
        self._next = 0
        self._events: list[dict[str, Any]] = []
        self._pending: set[int] = set()
        self._on_request = on_request

    def call(self, method: str, params: Mapping[str, Any] | None = None, timeout: float = 20.0) -> dict[str, Any]:
        message_id = self._send(method, params)
        return self._wait(message_id, timeout, method)

    def send_ignored(self, method: str, params: Mapping[str, Any]) -> None:
        self._pending.add(self._send(method, params))

    def pump(self, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            try:
                message = self._recv(min(remaining, 0.15))
            except TimeoutError:
                continue
            self._dispatch(message, waiting_for=None)

    def _send(self, method: str, params: Mapping[str, Any] | None = None) -> int:
        self._next += 1
        message_id = self._next
        body = {"id": message_id, "method": method, "params": dict(params or {})}
        self._sock.send_text(json.dumps(body, ensure_ascii=False))
        return message_id

    def _wait(self, message_id: int, timeout: float, method: str) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"CDP {method} timed out")
            message = self._recv(remaining)
            done = self._dispatch(message, waiting_for=message_id)
            if done is not None:
                return done

    def _recv(self, timeout: float) -> dict[str, Any]:
        self._sock.set_timeout(max(0.01, timeout))
        try:
            raw = self._sock.recv_text()
        except TimeoutError as exc:
            raise TimeoutError("CDP read timed out") from exc
        message = json.loads(raw)
        if not isinstance(message, dict):
            return {}
        return message

    def _dispatch(self, message: Mapping[str, Any], waiting_for: int | None) -> dict[str, Any] | None:
        message_id = message.get("id")
        if isinstance(message_id, int) and message_id in self._pending:
            self._pending.discard(message_id)
            return None
        if waiting_for is not None and message_id == waiting_for:
            if "error" in message:
                err = message["error"]
                detail = err.get("message") if isinstance(err, dict) else err
                raise RuntimeError(f"CDP failed: {detail}")
            result = message.get("result")
            return result if isinstance(result, dict) else {}
        if message.get("method") == "Fetch.requestPaused" and self._on_request is not None:
            params = message.get("params")
            self._on_request(params if isinstance(params, dict) else {})
            return None
        if message.get("method"):
            self._events.append(dict(message))
        return None


def _coerce_file_root(file_root: Path | None | str) -> Path | None:
    if file_root is None:
        return file_root_from_env()
    if isinstance(file_root, str):
        if not file_root.strip():
            return None
        return Path(file_root).expanduser()
    return file_root


def _path_from_file_url(url: str) -> Path:
    parts = urllib.parse.urlsplit(url)
    return Path(urllib.parse.unquote(parts.path or ""))


def _file_path_refusal(path: Path, *, file_root: Path | None, run_dirs: Iterable[Path]) -> str | None:
    try:
        real = path.resolve()
    except OSError as exc:
        return f"file URL refused: {exc.__class__.__name__}"
    for candidate in (path, real):
        reason = _secret_or_run_reason(candidate, run_dirs)
        if reason:
            return reason
    if file_root is None:
        return "file URL refused: no scratch root"
    try:
        root = file_root.resolve()
        real.relative_to(root)
    except (OSError, ValueError):
        return "file URL refused: outside scratch root"
    return None


def _secret_or_run_reason(path: Path, run_dirs: Iterable[Path]) -> str | None:
    if _SECRET_FILE_RE.search(path.name):
        return "secret path refused"
    for part in path.parts:
        if _SECRET_DIR_RE.match(part):
            return "secret directory refused"
        if _RUN_DIR_RE.match(part):
            return "run directory refused"
    text = path.as_posix()
    if "/workspace/aureon_run_" in text:
        return "run directory refused"
    try:
        real = path.resolve()
    except OSError:
        real = path
    state = _repo_state_dir()
    try:
        real.relative_to(state.resolve())
        return "repo state path refused"
    except (OSError, ValueError):
        pass
    for run in run_dirs:
        try:
            real.relative_to(Path(run).resolve())
            return "live run directory refused"
        except (OSError, ValueError):
            continue
    return None


def _repo_state_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "state"


def _ips_for_host(host: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        return [ipaddress.ip_address(host)]
    except ValueError:
        pass
    found: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for info in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM):
        try:
            found.append(ipaddress.ip_address(info[4][0]))
        except ValueError:
            continue
    return found


def _is_exact_loopback(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return str(ip) in _EXACT_LOOPBACK_IPS


def _host_resolver_rules(allow_hosts: Iterable[str]) -> str:
    excludes = ["127.0.0.1", "localhost", "[::1]"]
    for host in sorted(set(allow_hosts)):
        if host and host not in excludes:
            excludes.append(host)
    parts = ["MAP * ~NOTFOUND"]
    parts.extend(f"EXCLUDE {host}" for host in excludes)
    return ", ".join(parts)


def _is_off_host_reason(reason: str) -> bool:
    return reason == "off_host" or reason.startswith("host refused") or reason.startswith("scheme refused")


def _screenshot_name_problem(requested: str) -> str:
    name = requested.strip()
    if not name:
        return ""
    if name != Path(name).name or name in {".", ".."} or "/" in name or "\\" in name or "\x00" in name:
        return "screenshot path refused"
    return ""


def _executable(path: str) -> bool:
    candidate = Path(path)
    return candidate.is_file() and os.access(candidate, os.X_OK)


def _normalize_hosts(hosts: Iterable[str]) -> frozenset[str]:
    found: set[str] = set()
    for item in hosts:
        text = str(item).strip().lower()
        if not text or text == "*":
            continue
        if "://" in text:
            try:
                text = (urllib.parse.urlsplit(text).hostname or "").lower()
            except ValueError:
                continue
        text = text.strip("[]")
        if text.count(":") == 1:
            host, _, port = text.rpartition(":")
            if port.isdigit() and host:
                text = host
        if text:
            found.add(text)
    return frozenset(found)


def _audit_url(url: str) -> str:
    if not url:
        return ""
    try:
        parts = urllib.parse.urlsplit(url.strip())
    except ValueError:
        return url.strip()[:500]
    host = parts.hostname or ""
    if ":" in host:
        host = f"[{host}]"
    if parts.port and host:
        host = f"{host}:{parts.port}"
    cleaned = urllib.parse.urlunsplit((parts.scheme, host, parts.path, "", ""))
    return cleaned[:500]


def _http_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=2) as response:
        return json.loads(response.read().decode("utf-8"))


def _navigation_arrived(href: str, previous: str, requested: str) -> bool:
    """True once the document has left the previous page for the requested one.

    ``about:blank`` is the session's start page. It is not a successful open
    of a file or http URL, even if a readyState poll races the navigation.
    """

    if not href or href == previous:
        return False
    return href != "about:blank" or requested.startswith("about:")


def _context_gone(text: str) -> bool:
    lowered = text.lower()
    return "context" in lowered or "destroyed" in lowered or "cannot find" in lowered


def _exception_text(details: Any) -> str:
    if not isinstance(details, dict):
        return "javascript exception"
    exc = details.get("exception")
    if isinstance(exc, dict) and exc.get("description"):
        return str(exc["description"]).split("\n", 1)[0][:300]
    return str(details.get("text") or "javascript exception")[:300]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


__all__ = [
    "BROWSER_TOOL_DESCRIPTION",
    "BrowserTool",
    "allow_hosts_from_env",
    "browser_input_schema",
    "default_audit_path",
    "dispatch_browser_tool",
    "find_chrome_binary",
    "registry_browser",
    "reset_registry_browser",
    "url_refusal",
]
