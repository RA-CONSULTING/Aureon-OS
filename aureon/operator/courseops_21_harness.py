"""Loopback-only HTTP and browser harness for the synthetic CourseOps-21 suite.

The HTTP server runs in this process, binds only ``127.0.0.1``, and serves a
small explicit route table.  The complete fixture tree is hashed at startup;
each served file is then checked against that frozen manifest immediately
before it is returned.  This gives the assessment grant and the GUI operator
one shared, content-addressed view of the synthetic course environment.

Browser launch is deliberately opt-in.  Building a launch plan has no side
effects, and the server never launches a browser merely because it starts.
"""

from __future__ import annotations

import ctypes
import hashlib
import hmac
import http.client
import json
import os
import stat
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import TracebackType
from typing import Callable, Mapping, cast
from urllib.parse import urlsplit

from aureon.operator.synthetic_assessment_grant import (
    AssetManifest,
    AssetManifestEntry,
    GrantFormatError,
    build_asset_manifest,
    canonical_asset_root,
)

LOOPBACK_HOST = "127.0.0.1"
COURSEOPS_SCHEMA_VERSION = "aureon-courseops-21-v1"
HARNESS_SCHEMA_VERSION = "aureon-courseops-21-harness-v1"
EXPECTED_PERSONA_ID = "john-brown-synthetic-v1"
EXPECTED_WINDOW_TITLE = "Aureon CourseOps 21"

SERVED_ASSETS = (
    "app.js",
    "benchmark_manifest.json",
    "index.html",
    "styles.css",
)
_ROUTES = {
    "/": "index.html",
    "/app.js": "app.js",
    "/benchmark_manifest.json": "benchmark_manifest.json",
    "/index.html": "index.html",
    "/styles.css": "styles.css",
}
_CONTENT_TYPES = {
    "app.js": "text/javascript; charset=utf-8",
    "benchmark_manifest.json": "application/json; charset=utf-8",
    "index.html": "text/html; charset=utf-8",
    "styles.css": "text/css; charset=utf-8",
}
_SECURITY_HEADERS = {
    "Cache-Control": "no-store, max-age=0",
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'none'; object-src 'none'; "
        "frame-src 'none'; worker-src 'none'; base-uri 'none'; "
        "form-action 'none'; frame-ancestors 'none'"
    ),
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": (
        "camera=(), microphone=(), geolocation=(), payment=(), usb=(), "
        "serial=(), bluetooth=()"
    ),
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}
_ALLOWED_BROWSER_NAMES = frozenset({"chrome", "chrome.exe", "msedge", "msedge.exe"})


class CourseOps21HarnessError(RuntimeError):
    """Base exception for fail-closed harness errors."""


class CourseOps21AssetError(CourseOps21HarnessError):
    """Raised when the fixture or a served asset differs from its frozen hash."""


class CourseOps21BrowserError(CourseOps21HarnessError):
    """Raised when an optional controlled browser cannot be safely launched."""


def _utc_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _validate_port(port: object) -> int:
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65_535:
        raise ValueError("port must be an integer between 0 and 65535")
    return port


def _entry_map(manifest: AssetManifest) -> dict[str, AssetManifestEntry]:
    return {entry.path: entry for entry in manifest.files}


def _validate_suite_manifest(root: Path) -> None:
    manifest_path = root / "benchmark_manifest.json"
    try:
        raw = manifest_path.read_bytes()
        if len(raw) > 1024 * 1024:
            raise CourseOps21AssetError("benchmark manifest is unexpectedly large")
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CourseOps21AssetError("benchmark manifest is not valid UTF-8 JSON") from exc
    if not isinstance(value, Mapping):
        raise CourseOps21AssetError("benchmark manifest must be an object")
    persona = value.get("persona")
    course_codes = value.get("course_codes")
    if value.get("schema_version") != COURSEOPS_SCHEMA_VERSION:
        raise CourseOps21AssetError("benchmark manifest schema mismatch")
    if not isinstance(persona, Mapping) or persona.get("id") != EXPECTED_PERSONA_ID:
        raise CourseOps21AssetError("benchmark manifest persona mismatch")
    if persona.get("synthetic") is not True:
        raise CourseOps21AssetError("benchmark persona must be explicitly synthetic")
    if value.get("local_only") is not True or value.get("network_policy") != "loopback_fixture_only":
        raise CourseOps21AssetError("benchmark must declare loopback-only operation")
    if value.get("contains_real_provider_content") is not False:
        raise CourseOps21AssetError("real provider content is not accepted")
    if value.get("certificate_class") != "synthetic_test_only":
        raise CourseOps21AssetError("certificate class must be synthetic_test_only")
    if (
        not isinstance(course_codes, list)
        or len(course_codes) != 21
        or len({str(code) for code in course_codes}) != 21
    ):
        raise CourseOps21AssetError("benchmark must contain 21 unique courses")


def _stable_asset_bytes(root: Path, entry: AssetManifestEntry) -> bytes:
    candidate = root / entry.path
    try:
        before = candidate.stat(follow_symlinks=False)
        if candidate.is_symlink() or not stat.S_ISREG(before.st_mode):
            raise CourseOps21AssetError("served asset is no longer a regular file")
        resolved = candidate.resolve(strict=True)
        if resolved.parent != root:
            raise CourseOps21AssetError("served asset escaped the fixture root")
        with candidate.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode):
                raise CourseOps21AssetError("served asset changed type while opening")
            data = handle.read()
            after = os.fstat(handle.fileno())
    except CourseOps21AssetError:
        raise
    except OSError as exc:
        raise CourseOps21AssetError("served asset could not be read") from exc

    identities = {
        (before.st_size, before.st_mtime_ns, before.st_ino),
        (opened.st_size, opened.st_mtime_ns, opened.st_ino),
        (after.st_size, after.st_mtime_ns, after.st_ino),
    }
    if len(identities) != 1:
        raise CourseOps21AssetError("served asset changed while being read")
    if len(data) != entry.size_bytes:
        raise CourseOps21AssetError("served asset size differs from frozen manifest")
    if not hmac.compare_digest(hashlib.sha256(data).hexdigest(), entry.sha256):
        raise CourseOps21AssetError("served asset hash differs from frozen manifest")
    return data


@dataclass(frozen=True)
class CourseOps21ServerContext:
    """Exact runtime context to bind into a synthetic assessment grant."""

    root: str
    host: str
    port: int
    origin: str
    server_pid: int
    started_at_utc: str
    asset_manifest: AssetManifest
    schema_version: str = HARNESS_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "root": self.root,
            "host": self.host,
            "port": self.port,
            "origin": self.origin,
            "server_pid": self.server_pid,
            "started_at_utc": self.started_at_utc,
            "asset_manifest": self.asset_manifest.to_dict(),
            "served_assets": list(SERVED_ASSETS),
        }


@dataclass(frozen=True)
class BrowserLaunchPlan:
    """Side-effect-free description of an isolated CourseOps browser launch."""

    executable: str
    profile_dir: str
    download_dir: str
    url: str
    expected_window_title: str
    command: tuple[str, ...]
    server_pid: int
    asset_manifest_root_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "executable": self.executable,
            "profile_dir": self.profile_dir,
            "download_dir": self.download_dir,
            "url": self.url,
            "expected_window_title": self.expected_window_title,
            "command": list(self.command),
            "server_pid": self.server_pid,
            "asset_manifest_root_sha256": self.asset_manifest_root_sha256,
        }


@dataclass(frozen=True)
class BrowserProcessContext:
    """Observed identity of an opt-in browser process and its visible window."""

    browser_pid: int
    window_handle: int
    window_title: str
    executable: str
    profile_dir: str
    download_dir: str
    url: str
    launched_at_utc: str

    def to_dict(self) -> dict[str, object]:
        return {
            "browser_pid": self.browser_pid,
            "window_handle": self.window_handle,
            "window_title": self.window_title,
            "executable": self.executable,
            "profile_dir": self.profile_dir,
            "download_dir": self.download_dir,
            "url": self.url,
            "launched_at_utc": self.launched_at_utc,
        }


@dataclass
class ControlledBrowser:
    """Handle for a browser explicitly launched by :class:`CourseOps21Harness`."""

    context: BrowserProcessContext
    _process: subprocess.Popen[bytes]

    def stop(self, *, timeout_seconds: float = 10.0) -> None:
        if self._process.poll() is not None:
            return
        self._process.terminate()
        try:
            self._process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait(timeout=timeout_seconds)


@dataclass(frozen=True)
class _ServerState:
    root: Path
    entries: Mapping[str, AssetManifestEntry]

    def read_asset(self, name: str) -> bytes:
        entry = self.entries.get(name)
        if entry is None:
            raise CourseOps21AssetError("asset is not in the served manifest")
        return _stable_asset_bytes(self.root, entry)


class _CourseOpsHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, address: tuple[str, int], state: _ServerState) -> None:
        self.courseops_state = state
        super().__init__(address, _CourseOpsRequestHandler)


class _CourseOpsRequestHandler(BaseHTTPRequestHandler):
    server_version = "AureonCourseOps21/1"
    sys_version = ""

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def version_string(self) -> str:
        return self.server_version

    @property
    def _state(self) -> _ServerState:
        return cast(_CourseOpsHTTPServer, self.server).courseops_state

    def end_headers(self) -> None:
        for name, value in _SECURITY_HEADERS.items():
            self.send_header(name, value)
        super().end_headers()

    def _literal_route(self) -> str | None:
        parts = urlsplit(self.path)
        if parts.scheme or parts.netloc or parts.query or parts.fragment:
            return None
        if parts.path != self.path:
            return None
        return _ROUTES.get(parts.path)

    def _plain_response(self, status: int, message: str, *, allow: str | None = None) -> None:
        payload = (message + "\n").encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        if allow:
            self.send_header("Allow", allow)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    def _serve(self, *, include_body: bool) -> None:
        asset_name = self._literal_route()
        if asset_name is None:
            self._plain_response(http.client.NOT_FOUND, "not found")
            return
        try:
            payload = self._state.read_asset(asset_name)
        except CourseOps21AssetError:
            self._plain_response(http.client.SERVICE_UNAVAILABLE, "asset integrity check failed")
            return
        self.send_response(http.client.OK)
        self.send_header("Content-Type", _CONTENT_TYPES[asset_name])
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("ETag", f'"sha256:{self._state.entries[asset_name].sha256}"')
        self.end_headers()
        if include_body:
            self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler hook
        self._serve(include_body=True)

    def do_HEAD(self) -> None:  # noqa: N802 - stdlib handler hook
        self._serve(include_body=False)

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler hook
        self._plain_response(http.client.METHOD_NOT_ALLOWED, "method not allowed", allow="GET, HEAD")

    do_DELETE = do_POST
    do_OPTIONS = do_POST
    do_PATCH = do_POST
    do_PUT = do_POST


def _canonical_launch_directory(path: str | os.PathLike[str]) -> Path:
    supplied = Path(path).expanduser()
    try:
        absolute = supplied if supplied.is_absolute() else supplied.absolute()
        resolved = absolute.resolve(strict=False)
    except OSError as exc:
        raise CourseOps21BrowserError("browser directory cannot be resolved") from exc
    if absolute.exists() and (absolute.is_symlink() or not absolute.is_dir()):
        raise CourseOps21BrowserError("browser path must be a real directory")
    return resolved


def _canonical_browser_executable(path: str | os.PathLike[str]) -> Path:
    supplied = Path(path).expanduser()
    if supplied.is_symlink():
        raise CourseOps21BrowserError("browser executable must not be a symbolic link")
    try:
        resolved = supplied.resolve(strict=True)
    except OSError as exc:
        raise CourseOps21BrowserError("browser executable does not exist") from exc
    if not resolved.is_file() or resolved.name.casefold() not in _ALLOWED_BROWSER_NAMES:
        raise CourseOps21BrowserError("browser must be an exact Chrome or Edge executable")
    return resolved


def _capture_windows_window(
    process_id: int,
    expected_title: str,
    timeout_seconds: float,
) -> tuple[int, str]:
    if sys.platform != "win32":
        raise CourseOps21BrowserError("browser window capture is supported only on Windows")
    if timeout_seconds <= 0:
        raise ValueError("window timeout must be positive")

    user32 = ctypes.windll.user32
    found: list[tuple[int, str]] = []
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def enumerate_once() -> tuple[int, str] | None:
        found.clear()

        @callback_type
        def callback(hwnd: int, _lparam: int) -> bool:
            if not user32.IsWindowVisible(hwnd):
                return True
            owner_pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner_pid))
            if owner_pid.value != process_id:
                return True
            length = int(user32.GetWindowTextLengthW(hwnd))
            if length <= 0:
                return True
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            title = buffer.value
            if title:
                found.append((int(hwnd), title))
            return True

        if not user32.EnumWindows(callback, 0):
            raise CourseOps21BrowserError("Windows could not enumerate browser windows")
        exact = [item for item in found if expected_title.casefold() in item[1].casefold()]
        if exact:
            return exact[0]
        return found[0] if found else None

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        result = enumerate_once()
        if result is not None and expected_title.casefold() in result[1].casefold():
            return result
        time.sleep(0.1)
    raise CourseOps21BrowserError("controlled browser window was not observed before timeout")


class CourseOps21Harness:
    """Own a hash-bound CourseOps-21 server and an optional isolated browser."""

    def __init__(self, asset_root: str | os.PathLike[str], *, port: int = 0) -> None:
        self._asset_root = Path(asset_root)
        self._port = _validate_port(port)
        self._server: _CourseOpsHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._context: CourseOps21ServerContext | None = None
        self._lock = threading.RLock()

    @property
    def context(self) -> CourseOps21ServerContext:
        with self._lock:
            if self._context is None:
                raise CourseOps21HarnessError("CourseOps-21 harness is not running")
            return self._context

    def start(self) -> CourseOps21ServerContext:
        with self._lock:
            if self._server is not None:
                raise CourseOps21HarnessError("CourseOps-21 harness is already running")
            try:
                canonical_root = canonical_asset_root(self._asset_root)
                root = Path(canonical_root)
                manifest = build_asset_manifest(root)
            except GrantFormatError as exc:
                raise CourseOps21AssetError("fixture tree is not a safe asset root") from exc
            entries = _entry_map(manifest)
            if any(name not in entries for name in SERVED_ASSETS):
                raise CourseOps21AssetError("fixture is missing a required served asset")
            _validate_suite_manifest(root)
            state = _ServerState(root=root, entries={name: entries[name] for name in SERVED_ASSETS})
            try:
                server = _CourseOpsHTTPServer((LOOPBACK_HOST, self._port), state)
            except OSError as exc:
                raise CourseOps21HarnessError("loopback server could not bind") from exc
            bound_host, bound_port = server.server_address[:2]
            if bound_host != LOOPBACK_HOST:
                server.server_close()
                raise CourseOps21HarnessError("server did not bind the exact loopback host")
            context = CourseOps21ServerContext(
                root=canonical_root,
                host=LOOPBACK_HOST,
                port=int(bound_port),
                origin=f"http://{LOOPBACK_HOST}:{int(bound_port)}",
                server_pid=os.getpid(),
                started_at_utc=_utc_timestamp(),
                asset_manifest=manifest,
            )
            thread = threading.Thread(
                target=server.serve_forever,
                kwargs={"poll_interval": 0.05},
                name=f"aureon-courseops-21-{bound_port}",
                daemon=True,
            )
            self._server = server
            self._thread = thread
            self._context = context
            thread.start()
            return context

    def stop(self, *, timeout_seconds: float = 10.0) -> None:
        with self._lock:
            server = self._server
            thread = self._thread
            self._server = None
            self._thread = None
            self._context = None
        if server is None:
            return
        server.shutdown()
        server.server_close()
        if thread is not None:
            thread.join(timeout=timeout_seconds)
            if thread.is_alive():
                raise CourseOps21HarnessError("loopback server did not stop before timeout")

    def __enter__(self) -> CourseOps21Harness:
        self.start()
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        self.stop()

    def build_browser_launch_plan(
        self,
        executable: str | os.PathLike[str],
        *,
        profile_dir: str | os.PathLike[str],
        download_dir: str | os.PathLike[str],
        expected_window_title: str = EXPECTED_WINDOW_TITLE,
    ) -> BrowserLaunchPlan:
        context = self.context
        browser = _canonical_browser_executable(executable)
        profile = _canonical_launch_directory(profile_dir)
        downloads = _canonical_launch_directory(download_dir)
        if profile == downloads:
            raise CourseOps21BrowserError("profile and download directories must be distinct")
        title = str(expected_window_title).strip()
        if not title or len(title) > 256:
            raise ValueError("expected_window_title must be a non-empty bounded string")
        command = (
            str(browser),
            f"--user-data-dir={profile}",
            "--profile-directory=Default",
            f"--download-default-directory={downloads}",
            "--new-window",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-networking",
            "--disable-component-update",
            "--disable-default-apps",
            "--disable-extensions",
            "--disable-sync",
            "--metrics-recording-only",
            "--host-resolver-rules=MAP * 0.0.0.0, EXCLUDE 127.0.0.1",
            context.origin,
        )
        return BrowserLaunchPlan(
            executable=str(browser),
            profile_dir=str(profile),
            download_dir=str(downloads),
            url=context.origin,
            expected_window_title=title,
            command=command,
            server_pid=context.server_pid,
            asset_manifest_root_sha256=context.asset_manifest.root_sha256,
        )

    def launch_browser(
        self,
        executable: str | os.PathLike[str],
        *,
        profile_dir: str | os.PathLike[str],
        download_dir: str | os.PathLike[str],
        expected_window_title: str = EXPECTED_WINDOW_TITLE,
        window_timeout_seconds: float = 15.0,
        window_capture: Callable[[int, str, float], tuple[int, str]] = _capture_windows_window,
    ) -> ControlledBrowser:
        """Explicitly launch one isolated Edge/Chrome window and capture its binding."""

        plan = self.build_browser_launch_plan(
            executable,
            profile_dir=profile_dir,
            download_dir=download_dir,
            expected_window_title=expected_window_title,
        )
        profile = Path(plan.profile_dir)
        downloads = Path(plan.download_dir)
        profile.mkdir(parents=True, exist_ok=True)
        downloads.mkdir(parents=True, exist_ok=True)
        if profile.is_symlink() or downloads.is_symlink():
            raise CourseOps21BrowserError("browser directories changed into symbolic links")
        try:
            process = subprocess.Popen(
                plan.command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            raise CourseOps21BrowserError("controlled browser failed to launch") from exc
        try:
            handle, title = window_capture(
                process.pid,
                plan.expected_window_title,
                window_timeout_seconds,
            )
        except Exception:
            process.terminate()
            try:
                process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5.0)
            raise
        if process.poll() is not None:
            raise CourseOps21BrowserError("controlled browser exited during window capture")
        context = BrowserProcessContext(
            browser_pid=process.pid,
            window_handle=handle,
            window_title=title,
            executable=plan.executable,
            profile_dir=plan.profile_dir,
            download_dir=plan.download_dir,
            url=plan.url,
            launched_at_utc=_utc_timestamp(),
        )
        return ControlledBrowser(context=context, _process=process)


__all__ = [
    "BrowserLaunchPlan",
    "BrowserProcessContext",
    "ControlledBrowser",
    "CourseOps21AssetError",
    "CourseOps21BrowserError",
    "CourseOps21Harness",
    "CourseOps21HarnessError",
    "CourseOps21ServerContext",
    "HARNESS_SCHEMA_VERSION",
    "LOOPBACK_HOST",
    "SERVED_ASSETS",
]
