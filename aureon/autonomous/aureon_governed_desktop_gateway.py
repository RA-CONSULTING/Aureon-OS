"""Fail-closed, evidence-producing local desktop gateway.

This module is deliberately independent from ``LaptopControl``.  It exposes a
small desktop action surface behind an in-memory authorization lease and exact
foreground-window binding.  Importing the module does not import pyautogui or
touch the desktop; the local backend is loaded only when an observation or
action is requested.

The gateway never persists arming state or capability-token plaintext.  Live
authorization expires after at most 24 hours and an emergency-stop epoch
invalidates every lease and window binding issued before it.
"""

from __future__ import annotations

import hashlib
import importlib
import io
import json
import math
import os
import re
import sys
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Deque, Dict, Mapping, Protocol, Sequence, Tuple

if TYPE_CHECKING:
    from aureon.operator.governed_window_session import GatewayWindowBinding

MAX_LEASE_SECONDS = 24 * 60 * 60
MAX_SCROLL_CLICKS = 100
WIN32_WHEEL_DELTA = 120
DEFAULT_EVIDENCE_PATH = (
    Path(__file__).resolve().parents[2] / "state" / "governed_desktop_gateway_evidence.jsonl"
)

ALLOWED_ACTIONS = frozenset(
    {
        "observe",
        "move",
        "click",
        "double_click",
        "right_click",
        "scroll",
        "type",
        "press",
        "hotkey",
    }
)
MUTATING_ACTIONS = ALLOWED_ACTIONS - {"observe"}

_NAMED_KEYS = frozenset(
    {
        "enter",
        "return",
        "tab",
        "escape",
        "esc",
        "backspace",
        "delete",
        "insert",
        "home",
        "end",
        "pageup",
        "pagedown",
        "up",
        "down",
        "left",
        "right",
        "space",
        "ctrl",
        "control",
        "alt",
        "shift",
        "win",
        "command",
        "capslock",
    }
    | {f"f{i}" for i in range(1, 25)}
)


class DesktopGatewayError(RuntimeError):
    """Base exception for control-plane operations such as authorization."""


class AuthorizationError(DesktopGatewayError):
    """Raised when a live authorization lease cannot be issued."""


class EvidenceWriteError(DesktopGatewayError):
    """Raised when append-only evidence cannot be committed."""


class DesktopBackendError(DesktopGatewayError):
    """Raised when the injected/local desktop backend is unavailable or fails."""


@dataclass(frozen=True)
class WindowInfo:
    """Identity and current geometry of a native foreground window."""

    handle: int
    title: str
    process_id: int
    left: int
    top: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height

    def audit_dict(self) -> Dict[str, Any]:
        return {
            "handle": self.handle,
            "title_sha256": _sha256_text(self.title),
            "title_length": len(self.title),
            "process_id": self.process_id,
            "rect": {
                "left": self.left,
                "top": self.top,
                "width": self.width,
                "height": self.height,
            },
        }


class DesktopBackend(Protocol):
    """Minimal injectable backend used by the governed gateway."""

    def capture_screen(self) -> bytes:
        ...

    def screen_size(self) -> Tuple[int, int]:
        ...

    def foreground_window(self) -> WindowInfo:
        ...

    def window_dpi(self, window: WindowInfo) -> Tuple[float, float] | None:
        """Return the native effective DPI for ``window`` when available."""

        ...

    def foreign_occlusion_rects(
        self,
        window: WindowInfo,
    ) -> Tuple[Tuple[int, int, int, int], ...]:
        """Return visible foreign top-level rectangles above ``window``."""

        ...

    def pointer_position(self) -> Tuple[int, int]:
        ...

    def move(self, x: int, y: int, duration: float = 0.0) -> None:
        ...

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> None:
        ...

    def scroll(self, amount: int, x: int, y: int) -> None:
        ...

    def type_text(self, text: str, interval: float = 0.02) -> None:
        ...

    def press(self, key: str) -> None:
        ...

    def hotkey(self, keys: Sequence[str]) -> None:
        ...


class LazyPyAutoGUIBackend:
    """Windows desktop backend that imports pyautogui only on first use.

    ``FAILSAFE`` is restored to ``True`` on every access so another legacy
    module cannot silently disable the physical corner escape after this
    backend has initialized.
    """

    def __init__(
        self,
        pause_seconds: float = 0.05,
        *,
        platform_name: str | None = None,
    ) -> None:
        self._pause_seconds = max(0.0, float(pause_seconds))
        self._platform_name = platform_name or sys.platform
        self._module: Any = None
        self._load_lock = threading.Lock()

    def _pyautogui(self) -> Any:
        with self._load_lock:
            if self._module is None:
                try:
                    self._module = importlib.import_module("pyautogui")
                except Exception as exc:  # pragma: no cover - host dependent
                    raise DesktopBackendError("local_desktop_backend_unavailable") from exc
            try:
                self._module.FAILSAFE = True
                self._module.PAUSE = self._pause_seconds
            except Exception as exc:  # pragma: no cover - defensive
                raise DesktopBackendError("could_not_enable_pyautogui_failsafe") from exc
            return self._module

    def capture_screen(self) -> bytes:
        pg = self._pyautogui()
        try:
            image = pg.screenshot()
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            data = buffer.getvalue()
        except Exception as exc:
            raise DesktopBackendError("screen_capture_failed") from exc
        if not data:
            raise DesktopBackendError("empty_screen_capture")
        return data

    def screen_size(self) -> Tuple[int, int]:
        pg = self._pyautogui()
        try:
            size = pg.size()
            width, height = int(size[0]), int(size[1])
        except Exception as exc:
            raise DesktopBackendError("screen_size_failed") from exc
        if width <= 0 or height <= 0:
            raise DesktopBackendError("invalid_screen_size")
        return width, height

    def foreground_window(self) -> WindowInfo:
        try:
            import ctypes
            import ctypes.wintypes

            user32 = ctypes.windll.user32  # type: ignore[attr-defined]
            handle = int(user32.GetForegroundWindow())
            if handle <= 0:
                raise DesktopBackendError("foreground_window_unavailable")

            title_length = int(user32.GetWindowTextLengthW(handle))
            title_buffer = ctypes.create_unicode_buffer(title_length + 1)
            user32.GetWindowTextW(handle, title_buffer, title_length + 1)

            process_id = ctypes.wintypes.DWORD()
            user32.GetWindowThreadProcessId(handle, ctypes.byref(process_id))

            rect = ctypes.wintypes.RECT()
            if not user32.GetWindowRect(handle, ctypes.byref(rect)):
                raise DesktopBackendError("foreground_window_geometry_unavailable")

            info = WindowInfo(
                handle=handle,
                title=title_buffer.value,
                process_id=int(process_id.value),
                left=int(rect.left),
                top=int(rect.top),
                width=int(rect.right - rect.left),
                height=int(rect.bottom - rect.top),
            )
        except DesktopBackendError:
            raise
        except Exception as exc:  # pragma: no cover - non-Windows/host dependent
            raise DesktopBackendError("foreground_window_query_failed") from exc
        _validate_window_info(info)
        return info

    def window_dpi(self, window: WindowInfo) -> Tuple[float, float] | None:
        """Return Windows' exact effective DPI for the supplied native window."""

        _validate_window_info(window)
        if self._platform_name != "win32":
            return None
        try:
            import ctypes
            import ctypes.wintypes

            user32 = ctypes.windll.user32  # type: ignore[attr-defined]
            get_dpi_for_window = getattr(user32, "GetDpiForWindow", None)
            if get_dpi_for_window is None:
                return None
            get_dpi_for_window.argtypes = [ctypes.wintypes.HWND]
            get_dpi_for_window.restype = ctypes.wintypes.UINT
            dpi = int(get_dpi_for_window(ctypes.wintypes.HWND(window.handle)))
        except DesktopGatewayError:
            raise
        except Exception as exc:  # pragma: no cover - host dependent
            raise DesktopBackendError("window_dpi_query_failed") from exc
        return _validate_window_dpi_pair((dpi, dpi))

    def foreign_occlusion_rects(
        self,
        window: WindowInfo,
    ) -> Tuple[Tuple[int, int, int, int], ...]:
        """Enumerate foreign always-on-top windows before the target in Z order."""

        _validate_window_info(window)
        if self._platform_name != "win32":
            return ()
        try:
            import ctypes
            import ctypes.wintypes

            user32 = ctypes.windll.user32  # type: ignore[attr-defined]
            rectangles: list[Tuple[int, int, int, int]] = []
            found_target = False

            @ctypes.WINFUNCTYPE(
                ctypes.wintypes.BOOL,
                ctypes.wintypes.HWND,
                ctypes.wintypes.LPARAM,
            )
            def collect(handle: int, _lparam: int) -> bool:
                nonlocal found_target
                native_handle = int(handle)
                if native_handle == window.handle:
                    found_target = True
                    return False
                if not user32.IsWindowVisible(handle):
                    return True
                process_id = ctypes.wintypes.DWORD()
                user32.GetWindowThreadProcessId(handle, ctypes.byref(process_id))
                if int(process_id.value) == window.process_id:
                    return True
                rect = ctypes.wintypes.RECT()
                if not user32.GetWindowRect(handle, ctypes.byref(rect)):
                    return True
                left = max(window.left, int(rect.left))
                top = max(window.top, int(rect.top))
                right = min(window.right, int(rect.right))
                bottom = min(window.bottom, int(rect.bottom))
                if left < right and top < bottom:
                    rectangles.append((left, top, right, bottom))
                    if len(rectangles) > 128:
                        return False
                return True

            user32.EnumWindows(collect, 0)
        except Exception as exc:  # pragma: no cover - host dependent
            raise DesktopBackendError("foreign_occlusion_query_failed") from exc
        if not found_target:
            raise DesktopBackendError("target_window_missing_from_z_order")
        if len(rectangles) > 128:
            raise DesktopBackendError("foreign_occlusion_inventory_exceeded")
        return tuple(rectangles)

    def pointer_position(self) -> Tuple[int, int]:
        pg = self._pyautogui()
        try:
            position = pg.position()
            x, y = int(position[0]), int(position[1])
        except Exception as exc:
            raise DesktopBackendError("pointer_position_failed") from exc
        return x, y

    def move(self, x: int, y: int, duration: float = 0.0) -> None:
        self._pyautogui().moveTo(x, y, duration=duration)

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> None:
        self._pyautogui().click(x=x, y=y, button=button, clicks=clicks)

    def scroll(self, amount: int, x: int, y: int) -> None:
        if (
            isinstance(amount, bool)
            or not isinstance(amount, int)
            or amount == 0
            or abs(amount) > MAX_SCROLL_CLICKS
        ):
            raise DesktopBackendError("scroll_amount_out_of_range")
        pg = self._pyautogui()
        pg.moveTo(x, y, duration=0.0)
        # PyAutoGUI 0.9.54's Win32 backend forwards ``clicks`` directly as
        # mouse_event(dwData), whose unit is WHEEL_DELTA (120).  Preserve the
        # gateway's cross-platform contract in logical wheel clicks and convert
        # only at the affected native boundary.  The logical bound above keeps
        # the resulting signed Win32 delta within +/-12,000.
        native_amount = (
            amount * WIN32_WHEEL_DELTA
            if self._platform_name == "win32"
            else amount
        )
        pg.scroll(native_amount)

    def type_text(self, text: str, interval: float = 0.02) -> None:
        self._pyautogui().write(text, interval=interval)

    def press(self, key: str) -> None:
        self._pyautogui().press(key)

    def hotkey(self, keys: Sequence[str]) -> None:
        self._pyautogui().hotkey(*keys)


@dataclass(frozen=True)
class ScreenObservation:
    captured_at: datetime
    sha256: str
    width: int
    height: int
    window: WindowInfo
    cursor_x: int
    cursor_y: int
    image_bytes: bytes = field(repr=False)
    dpi_x: float | None = None
    dpi_y: float | None = None

    def __post_init__(self) -> None:
        _validate_optional_window_dpi(self.dpi_x, self.dpi_y)

    def audit_dict(self) -> Dict[str, Any]:
        result = {
            "captured_at": _utc_iso(self.captured_at),
            "sha256": self.sha256,
            "byte_length": len(self.image_bytes),
            "screen": {"width": self.width, "height": self.height},
            "cursor": {"x": self.cursor_x, "y": self.cursor_y},
            "foreground_window": self.window.audit_dict(),
        }
        if self.dpi_x is not None:
            result["dpi"] = {"x": self.dpi_x, "y": self.dpi_y}
        return result


@dataclass(frozen=True)
class PostconditionResult:
    ok: bool
    detail: str = ""

    def audit_dict(self) -> Dict[str, Any]:
        return {
            "ok": bool(self.ok),
            "detail_sha256": _sha256_text(self.detail),
            "detail_length": len(self.detail),
        }


PostconditionEvaluator = Callable[
    [ScreenObservation, ScreenObservation, Mapping[str, Any]],
    bool | PostconditionResult,
]


@dataclass(frozen=True)
class DesktopActionResult:
    ok: bool
    action: str
    action_id: str
    dry_run: bool
    reason: str
    expected_before_sha256: str = ""
    before_sha256: str = ""
    after_sha256: str = ""
    postcondition: PostconditionResult | None = None
    before: ScreenObservation | None = field(default=None, repr=False)
    after: ScreenObservation | None = field(default=None, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "action": self.action,
            "action_id": self.action_id,
            "dry_run": self.dry_run,
            "reason": self.reason,
            "expected_before_sha256": self.expected_before_sha256,
            "before_sha256": self.before_sha256,
            "after_sha256": self.after_sha256,
            "postcondition": self.postcondition.audit_dict() if self.postcondition else None,
        }


@dataclass(frozen=True)
class AuthorizationLease:
    lease_id: str
    subject: str
    issued_at: datetime
    expires_at: datetime
    epoch: int
    allowed_actions: frozenset[str]
    token_fingerprint: str
    token_digest: str = field(repr=False)

    def public_dict(self) -> Dict[str, Any]:
        return {
            "lease_id": self.lease_id,
            "subject": self.subject,
            "issued_at": _utc_iso(self.issued_at),
            "expires_at": _utc_iso(self.expires_at),
            "epoch": self.epoch,
            "allowed_actions": sorted(self.allowed_actions),
            "token_fingerprint": self.token_fingerprint,
        }


@dataclass(frozen=True)
class WindowBinding:
    binding_id: str
    expected_title: str
    handle: int
    process_id: int
    created_at: datetime
    epoch: int

    def audit_dict(self) -> Dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "expected_title_sha256": _sha256_text(self.expected_title),
            "expected_title_length": len(self.expected_title),
            "handle": self.handle,
            "process_id": self.process_id,
            "created_at": _utc_iso(self.created_at),
            "epoch": self.epoch,
        }


class GovernedDesktopGateway:
    """Governed observe/act boundary for a single local desktop process."""

    def __init__(
        self,
        *,
        backend: DesktopBackend | None = None,
        evidence_path: Path | None = None,
        max_actions_per_window: int = 60,
        rate_window_seconds: float = 60.0,
        min_action_interval_seconds: float = 0.05,
        utc_now: Callable[[], datetime] | None = None,
        monotonic: Callable[[], float] | None = None,
    ) -> None:
        if max_actions_per_window <= 0:
            raise ValueError("max_actions_per_window must be positive")
        if rate_window_seconds <= 0:
            raise ValueError("rate_window_seconds must be positive")
        if min_action_interval_seconds < 0:
            raise ValueError("min_action_interval_seconds cannot be negative")

        self._backend: DesktopBackend = backend or LazyPyAutoGUIBackend()
        self.evidence_path = Path(evidence_path or DEFAULT_EVIDENCE_PATH)
        self.max_actions_per_window = int(max_actions_per_window)
        self.rate_window_seconds = float(rate_window_seconds)
        self.min_action_interval_seconds = float(min_action_interval_seconds)
        self._utc_now = utc_now or (lambda: datetime.now(UTC))
        self._monotonic = monotonic or time.monotonic

        self._state_lock = threading.RLock()
        self._action_lock = threading.Lock()
        self._evidence_lock = threading.Lock()
        self._recent_action_times: Deque[float] = deque()
        self._bindings: Dict[str, WindowBinding] = {}
        self._used_token_digests: set[str] = set()
        self._lease: AuthorizationLease | None = None
        self._dry_run = True
        self._emergency_stopped = False
        self._epoch = 0

    # ------------------------------------------------------------------
    # Authorization / safety state
    # ------------------------------------------------------------------
    def authorize_live(
        self,
        capability_token: str,
        *,
        ttl_seconds: float,
        subject: str,
        allowed_actions: Sequence[str] | None = None,
    ) -> AuthorizationLease:
        """Consume a one-time token and issue an in-memory live lease.

        The plaintext token is used only to compute SHA-256 and is never placed
        in gateway state, return values, exceptions, or evidence.
        """

        digest = _capability_digest(capability_token)
        try:
            ttl = float(ttl_seconds)
        except (TypeError, ValueError) as exc:
            raise AuthorizationError("lease_ttl_must_be_finite") from exc
        if ttl != ttl or ttl in (float("inf"), float("-inf")):
            raise AuthorizationError("lease_ttl_must_be_finite")
        if ttl <= 0:
            raise AuthorizationError("lease_ttl_must_be_positive")
        ttl = min(ttl, float(MAX_LEASE_SECONDS))
        subject_value = str(subject or "").strip()
        if not subject_value:
            raise AuthorizationError("lease_subject_required")

        requested = frozenset(sorted(MUTATING_ACTIONS) if allowed_actions is None else allowed_actions)
        if not requested or not requested.issubset(MUTATING_ACTIONS):
            raise AuthorizationError("invalid_lease_action_scope")

        now = self._now()
        with self._state_lock:
            if self._emergency_stopped:
                raise AuthorizationError("emergency_stop_active")
            if digest in self._used_token_digests:
                raise AuthorizationError("capability_token_already_consumed")

            lease = AuthorizationLease(
                lease_id=str(uuid.uuid4()),
                subject=subject_value,
                issued_at=now,
                expires_at=now + timedelta(seconds=ttl),
                epoch=self._epoch,
                allowed_actions=requested,
                token_fingerprint=digest[:12],
                token_digest=digest,
            )
            # Authorization is not committed unless its audit event is durable.
            self._append_event(
                {
                    "event": "authorization_issued",
                    "at": _utc_iso(now),
                    "epoch": self._epoch,
                    "lease": lease.public_dict(),
                }
            )
            self._used_token_digests.add(digest)
            self._lease = lease
            self._dry_run = False
            return lease

    def disarm(self, reason: str = "operator_disarm") -> None:
        """Drop the live lease and every target binding issued before it."""

        with self._state_lock:
            lease_id = self._lease.lease_id if self._lease else None
            invalidated_binding_count = len(self._bindings)
            self._lease = None
            self._dry_run = True
            self._bindings.clear()
            try:
                self._append_event(
                    {
                        "event": "disarmed",
                        "at": _utc_iso(self._now()),
                        "epoch": self._epoch,
                        "lease_id": lease_id,
                        "invalidated_binding_count": invalidated_binding_count,
                        "reason": _safe_label(reason),
                    }
                )
            except EvidenceWriteError:
                # Disarming must succeed even when the evidence disk is failing.
                pass

    def revoke_live_authorization(self, reason: str = "operator_lease_revoke") -> None:
        """Drop only the live lease while preserving externally owned bindings.

        This is the narrow teardown path for a ``GovernedWindowSession`` whose
        exact binding lifecycle is owned by that session.  It never creates,
        replaces, focuses, or releases a window binding.
        """

        with self._state_lock:
            lease_id = self._lease.lease_id if self._lease else None
            preserved_binding_count = len(self._bindings)
            self._lease = None
            self._dry_run = True
            try:
                self._append_event(
                    {
                        "event": "live_authorization_revoked",
                        "at": _utc_iso(self._now()),
                        "epoch": self._epoch,
                        "lease_id": lease_id,
                        "preserved_binding_count": preserved_binding_count,
                        "reason": _safe_label(reason),
                    }
                )
            except EvidenceWriteError:
                # Revocation is a safety action and cannot depend on storage health.
                pass

    def emergency_stop(self, reason: str = "operator_emergency_stop") -> int:
        """Invalidate leases/bindings by advancing the emergency-stop epoch."""

        with self._state_lock:
            self._epoch += 1
            self._emergency_stopped = True
            self._lease = None
            self._dry_run = True
            self._bindings.clear()
            epoch = self._epoch
            try:
                self._append_event(
                    {
                        "event": "emergency_stop",
                        "at": _utc_iso(self._now()),
                        "epoch": epoch,
                        "reason": _safe_label(reason),
                    }
                )
            except EvidenceWriteError:
                # The stop is a safety action and cannot depend on storage health.
                pass
            return epoch

    def clear_emergency_stop(self, reason: str = "operator_clear_emergency_stop") -> None:
        """Clear the stop flag without restoring any prior lease or binding."""

        with self._state_lock:
            if not self._emergency_stopped:
                return
            event = {
                "event": "emergency_stop_cleared",
                "at": _utc_iso(self._now()),
                "epoch": self._epoch,
                "reason": _safe_label(reason),
            }
            # Fail closed: if the clear cannot be audited, remain stopped.
            self._append_event(event)
            self._emergency_stopped = False

    def status(self) -> Dict[str, Any]:
        with self._state_lock:
            lease = self._active_lease_locked()
            return {
                "schema_version": "aureon-governed-desktop-status-v1",
                "dry_run": self._dry_run,
                "live_armed": bool(lease and not self._dry_run),
                "emergency_stopped": self._emergency_stopped,
                "epoch": self._epoch,
                "lease": lease.public_dict() if lease else None,
                "binding_count": len(self._bindings),
                "allowed_actions": sorted(ALLOWED_ACTIONS),
                "evidence_path": str(self.evidence_path),
            }

    def require_single_target_binding_id(self) -> str:
        """Return the sole current binding or fail closed.

        This supports observers that are constructed before the runtime binds
        its target window.  The observer latches the returned identifier and
        continues to present it explicitly on every subsequent capture.
        """

        with self._state_lock:
            current = [
                binding.binding_id
                for binding in self._bindings.values()
                if binding.epoch == self._epoch
            ]
            if len(current) != 1:
                raise DesktopGatewayError("exactly_one_target_window_binding_required")
            return current[0]

    # ------------------------------------------------------------------
    # Target-window binding
    # ------------------------------------------------------------------
    def bind_target_window(
        self,
        expected_title: str,
        *,
        expected_process_id: int | None = None,
    ) -> WindowBinding:
        """Bind future mutations to the exact current foreground handle/PID."""

        expected = str(expected_title or "").strip()
        if not expected:
            raise DesktopGatewayError("expected_window_title_required")

        window = self._backend_foreground_window()
        if window.title.casefold() != expected.casefold():
            raise DesktopGatewayError("target_window_title_mismatch")
        if expected_process_id is not None and window.process_id != int(expected_process_id):
            raise DesktopGatewayError("target_window_process_mismatch")

        now = self._now()
        with self._state_lock:
            if self._emergency_stopped:
                raise DesktopGatewayError("emergency_stop_active")
            binding = WindowBinding(
                binding_id=str(uuid.uuid4()),
                expected_title=expected,
                handle=window.handle,
                process_id=window.process_id,
                created_at=now,
                epoch=self._epoch,
            )
            self._append_event(
                {
                    "event": "target_window_bound",
                    "at": _utc_iso(now),
                    "epoch": self._epoch,
                    "binding": binding.audit_dict(),
                    "window": window.audit_dict(),
                }
            )
            self._bindings[binding.binding_id] = binding
            return binding

    def replace_target_window_binding(
        self,
        *,
        previous_binding_id: str | None,
        window: WindowInfo,
    ) -> GatewayWindowBinding:
        """Atomically replace the sole binding with one exact foreground window.

        This is the production adapter surface used by
        :class:`GovernedWindowSession`.  The supplied native identity must equal
        the current foreground HWND, PID, title *and* rectangle.  The new
        binding is activated only after its evidence record has been durably
        appended; on any failure the prior binding remains unchanged.
        """

        _validate_window_info(window)
        expected_previous = None if previous_binding_id is None else str(previous_binding_id)
        if previous_binding_id is not None and not expected_previous:
            raise DesktopGatewayError("previous_binding_id_required")

        with self._action_lock:
            observed = self._backend_foreground_window()
            if observed != window:
                raise DesktopGatewayError("exact_target_window_mismatch")
            now = self._now()
            with self._state_lock:
                if self._emergency_stopped:
                    raise DesktopGatewayError("emergency_stop_active")
                current = [
                    binding
                    for binding in self._bindings.values()
                    if binding.epoch == self._epoch
                ]
                if len(current) > 1:
                    raise DesktopGatewayError("multiple_target_window_bindings_active")
                active_id = current[0].binding_id if current else None
                if active_id != expected_previous:
                    raise DesktopGatewayError("target_window_binding_compare_and_swap_failed")

                binding = WindowBinding(
                    binding_id=str(uuid.uuid4()),
                    expected_title=window.title,
                    handle=window.handle,
                    process_id=window.process_id,
                    created_at=now,
                    epoch=self._epoch,
                )
                event = {
                    "event": "target_window_binding_replaced",
                    "at": _utc_iso(now),
                    "epoch": self._epoch,
                    "previous_binding_id": active_id,
                    "binding": binding.audit_dict(),
                    "window": window.audit_dict(),
                }
                # Evidence is the commit point.  Do not mutate binding state if
                # this append fails.
                self._append_event(event)
                self._bindings = {binding.binding_id: binding}

        # Imported lazily to avoid a module-import cycle: the handoff module
        # imports WindowInfo from this gateway.
        from aureon.operator.governed_window_session import GatewayWindowBinding

        return GatewayWindowBinding(binding_id=binding.binding_id, window=window)

    def release_target_window_binding(self, binding_id: str) -> None:
        """Release the exact sole binding, remaining safe if evidence fails.

        Deactivation is applied before the append attempt because retaining an
        authorization binding after a storage failure would be the unsafe
        rollback direction.  An evidence failure is still reported to the
        caller after the binding has been invalidated.
        """

        expected = str(binding_id or "")
        if not expected:
            raise DesktopGatewayError("binding_id_required")
        with self._action_lock, self._state_lock:
            current = [
                binding
                for binding in self._bindings.values()
                if binding.epoch == self._epoch
            ]
            if len(current) != 1 or current[0].binding_id != expected:
                raise DesktopGatewayError("target_window_binding_release_mismatch")
            released = current[0]
            del self._bindings[expected]
            self._append_event(
                {
                    "event": "target_window_binding_released",
                    "at": _utc_iso(self._now()),
                    "epoch": self._epoch,
                    "binding": released.audit_dict(),
                }
            )

    # ------------------------------------------------------------------
    # Observe / act
    # ------------------------------------------------------------------
    def execute(
        self,
        action: str,
        params: Mapping[str, Any] | None = None,
        *,
        target_binding_id: str | None = None,
        expected_before_sha256: str | None = None,
        evaluator: PostconditionEvaluator | None = None,
    ) -> DesktopActionResult:
        """Observe or perform one allowlisted action through every safety gate."""

        action_name = str(action or "").strip().lower()
        action_id = str(uuid.uuid4())
        raw_params = dict(params or {})

        with self._state_lock:
            current_dry_run = self._dry_run

        if action_name not in ALLOWED_ACTIONS:
            return self._reject(action_name, action_id, "action_not_allowed", current_dry_run, {})

        expected_hash = ""
        if expected_before_sha256 is not None:
            try:
                expected_hash = _lowercase_sha256(
                    expected_before_sha256,
                    name="expected_before_sha256",
                )
            except DesktopGatewayError as exc:
                return self._reject(
                    action_name,
                    action_id,
                    str(exc),
                    current_dry_run,
                    {},
                )

        try:
            validated = _validate_action_params(action_name, raw_params)
        except DesktopGatewayError as exc:
            return self._reject(
                action_name,
                action_id,
                str(exc),
                current_dry_run,
                _redact_params(action_name, raw_params),
            )

        redacted = _redact_params(action_name, validated)
        with self._action_lock:
            return self._execute_serialized(
                action_name,
                action_id,
                validated,
                redacted,
                target_binding_id=target_binding_id,
                expected_before_sha256=expected_hash,
                evaluator=evaluator,
            )

    def observe(self, *, target_binding_id: str | None = None) -> DesktopActionResult:
        """Capture the desktop, masking outside ``target_binding_id`` when set."""

        return self.execute("observe", target_binding_id=target_binding_id)

    def _execute_serialized(
        self,
        action: str,
        action_id: str,
        params: Dict[str, Any],
        redacted: Dict[str, Any],
        *,
        target_binding_id: str | None,
        expected_before_sha256: str,
        evaluator: PostconditionEvaluator | None,
    ) -> DesktopActionResult:
        binding: WindowBinding | None = None
        lease: AuthorizationLease | None = None
        with self._state_lock:
            if action != "observe" and self._emergency_stopped:
                return self._reject_locked(action, action_id, "emergency_stop_active", self._dry_run, redacted)
            dry_run = self._dry_run
            epoch = self._epoch
            if action == "observe" and target_binding_id is not None:
                binding = self._binding_locked(target_binding_id)
                if binding is None:
                    return self._reject_locked(
                        action,
                        action_id,
                        "valid_target_window_binding_required",
                        dry_run,
                        redacted,
                    )
            elif action != "observe":
                binding = self._binding_locked(target_binding_id)
                if binding is None:
                    return self._reject_locked(action, action_id, "valid_target_window_binding_required", dry_run, redacted)
                if not dry_run:
                    lease = self._active_lease_locked()
                    if lease is None:
                        return self._reject_locked(action, action_id, "active_authorization_lease_required", dry_run, redacted)
                    if action not in lease.allowed_actions:
                        return self._reject_locked(action, action_id, "action_outside_lease_scope", dry_run, redacted)
                    if not expected_before_sha256:
                        return self._reject_locked(
                            action,
                            action_id,
                            "expected_before_sha256_required",
                            dry_run,
                            redacted,
                        )
        try:
            captured_before = self._capture_observation()
        except DesktopGatewayError as exc:
            return self._reject(action, action_id, str(exc), dry_run, redacted)

        if binding is not None:
            binding_error = self._binding_error(binding, captured_before.window)
            if binding_error:
                return self._reject(
                    action,
                    action_id,
                    binding_error,
                    dry_run,
                    redacted,
                    expected_before_sha256=expected_before_sha256,
                )
            try:
                before = _mask_observation_to_window(captured_before)
            except DesktopGatewayError as exc:
                return self._reject(
                    action,
                    action_id,
                    str(exc),
                    dry_run,
                    redacted,
                    expected_before_sha256=expected_before_sha256,
                )
            coordinate_error = _coordinate_gate_error(action, params, before, before.window)
            if coordinate_error:
                return self._reject(
                    action,
                    action_id,
                    coordinate_error,
                    dry_run,
                    redacted,
                    before=before,
                    expected_before_sha256=expected_before_sha256,
                )
        else:
            before = captured_before

        if action != "observe" and expected_before_sha256 and before.sha256 != expected_before_sha256:
            return self._reject(
                action,
                action_id,
                "stale_source_frame",
                dry_run,
                redacted,
                before=before,
                expected_before_sha256=expected_before_sha256,
            )

        # Preserve bounded dry-run simulation accounting. Live mutations defer
        # rate-slot consumption until after the dispatch-linearization capture.
        if action != "observe" and dry_run:
            with self._state_lock:
                rate_error = self._consume_mutation_rate_slot_locked()
                if rate_error:
                    return self._reject_locked(
                        action,
                        action_id,
                        rate_error,
                        dry_run,
                        redacted,
                        before=before,
                        expected_before_sha256=expected_before_sha256,
                    )

        observation_scope = "target_window_masked" if binding is not None else "full_screen"

        started = {
            "event": "action_started",
            "at": _utc_iso(self._now()),
            "action_id": action_id,
            "action": action,
            "mode": "dry_run" if dry_run else "live",
            "epoch": epoch,
            "params": redacted,
            "expected_before_sha256": expected_before_sha256,
            "binding": binding.audit_dict() if binding else None,
            "lease_id": lease.lease_id if lease else None,
            "observation_scope": observation_scope,
            "before": before.audit_dict(),
        }
        try:
            self._append_event(started)
        except EvidenceWriteError:
            return DesktopActionResult(
                ok=False,
                action=action,
                action_id=action_id,
                dry_run=dry_run,
                reason="evidence_start_write_failed",
                expected_before_sha256=expected_before_sha256,
                before_sha256=before.sha256,
                before=before,
            )

        dispatch_error = ""
        dispatch_performed = False
        if action != "observe" and not dry_run:
            with self._state_lock:
                current_lease = self._active_lease_locked()
                if self._emergency_stopped or self._epoch != epoch:
                    dispatch_error = "emergency_epoch_changed_before_dispatch"
                elif not current_lease or not lease or current_lease.lease_id != lease.lease_id:
                    dispatch_error = "authorization_lease_changed_before_dispatch"

            if not dispatch_error and binding is not None:
                try:
                    captured_linearization = self._capture_observation()
                    dispatch_error = self._binding_error(
                        binding,
                        captured_linearization.window,
                    )
                    if not dispatch_error:
                        linearized_before = _mask_observation_to_window(
                            captured_linearization
                        )
                        dispatch_error = _coordinate_gate_error(
                            action,
                            params,
                            linearized_before,
                            captured_linearization.window,
                        )
                        if not dispatch_error and linearized_before.sha256 != before.sha256:
                            before = linearized_before
                            dispatch_error = "stale_source_frame"
                except DesktopGatewayError as exc:
                    dispatch_error = str(exc)

            if not dispatch_error:
                # Linearize the mutation before any emergency stop that can
                # subsequently return to its caller.  Native backends cannot
                # cancel an input syscall already in flight, so the state lock
                # makes the ordering explicit instead of allowing a stop to
                # report success while a newly authorized action begins.
                with self._state_lock:
                    current_lease = self._active_lease_locked()
                    if self._emergency_stopped or self._epoch != epoch:
                        dispatch_error = "emergency_epoch_changed_before_dispatch"
                    elif not current_lease or not lease or current_lease.lease_id != lease.lease_id:
                        dispatch_error = "authorization_lease_changed_before_dispatch"
                    else:
                        rate_error = self._consume_mutation_rate_slot_locked()
                        if rate_error:
                            dispatch_error = rate_error
                        else:
                            try:
                                self._dispatch(action, params)
                                dispatch_performed = True
                            except Exception:
                                dispatch_error = "backend_action_failed"

        try:
            captured_after = before if action == "observe" else self._capture_observation()
            if action != "observe" and binding is not None:
                post_binding_error = self._binding_error(binding, captured_after.window)
                if post_binding_error and not dispatch_error:
                    dispatch_error = (
                        "target_window_changed_after_action_handoff_required"
                        if dispatch_performed and post_binding_error == "target_window_mismatch"
                        else post_binding_error
                    )
                after = (
                    None
                    if post_binding_error
                    else _mask_observation_to_window(captured_after)
                )
            else:
                after = captured_after
        except DesktopGatewayError:
            after = None
            if not dispatch_error:
                dispatch_error = "post_action_capture_failed"

        with self._state_lock:
            if action != "observe" and not dry_run and self._epoch != epoch and not dispatch_error:
                dispatch_error = "emergency_epoch_changed_during_action"

        postcondition: PostconditionResult | None = None
        if evaluator is not None and after is not None and not dispatch_error:
            try:
                evaluated = evaluator(
                    before,
                    after,
                    {
                        "action": action,
                        "action_id": action_id,
                        "dry_run": dry_run,
                        "params": redacted,
                    },
                )
                if isinstance(evaluated, PostconditionResult):
                    postcondition = evaluated
                elif isinstance(evaluated, bool):
                    postcondition = PostconditionResult(evaluated)
                else:
                    dispatch_error = "invalid_postcondition_result"
            except Exception:
                dispatch_error = "postcondition_evaluator_failed"
            if postcondition is not None and not postcondition.ok:
                dispatch_error = "postcondition_failed"

        ok = not dispatch_error
        reason = dispatch_error or ("observed" if action == "observe" else "dry_run" if dry_run else "executed")
        result = DesktopActionResult(
            ok=ok,
            action=action,
            action_id=action_id,
            dry_run=dry_run,
            reason=reason,
            expected_before_sha256=expected_before_sha256,
            before_sha256=before.sha256,
            after_sha256=after.sha256 if after else "",
            postcondition=postcondition,
            before=before,
            after=after,
        )

        completed = {
            "event": "action_completed",
            "at": _utc_iso(self._now()),
            "action_id": action_id,
            "action": action,
            "mode": "dry_run" if dry_run else "live",
            "epoch": epoch,
            "ok": ok,
            "reason": reason,
            "params": redacted,
            "expected_before_sha256": expected_before_sha256,
            "observation_scope": observation_scope,
            "before_sha256": before.sha256,
            "after": after.audit_dict() if after else None,
            "postcondition": postcondition.audit_dict() if postcondition else None,
        }
        try:
            self._append_event(completed)
        except EvidenceWriteError:
            return DesktopActionResult(
                ok=False,
                action=action,
                action_id=action_id,
                dry_run=dry_run,
                reason="evidence_completion_write_failed",
                expected_before_sha256=expected_before_sha256,
                before_sha256=before.sha256,
                after_sha256=after.sha256 if after else "",
                postcondition=postcondition,
                before=before,
                after=after,
            )
        return result

    def _dispatch(self, action: str, params: Mapping[str, Any]) -> None:
        if action == "move":
            self._backend.move(params["x"], params["y"], params["duration"])
        elif action == "click":
            self._backend.click(params["x"], params["y"], button="left", clicks=1)
        elif action == "double_click":
            self._backend.click(params["x"], params["y"], button="left", clicks=2)
        elif action == "right_click":
            self._backend.click(params["x"], params["y"], button="right", clicks=1)
        elif action == "scroll":
            self._backend.scroll(params["amount"], params["x"], params["y"])
        elif action == "type":
            self._backend.type_text(params["text"], params["interval"])
        elif action == "press":
            self._backend.press(params["key"])
        elif action == "hotkey":
            self._backend.hotkey(params["keys"])
        else:  # pragma: no cover - allowlist/validator make this unreachable
            raise DesktopGatewayError("action_not_dispatchable")

    # ------------------------------------------------------------------
    # Internal gates / evidence
    # ------------------------------------------------------------------
    def _now(self) -> datetime:
        value = self._utc_now()
        if value.tzinfo is None or value.utcoffset() is None:
            raise DesktopGatewayError("utc_clock_must_be_timezone_aware")
        return value.astimezone(UTC)

    def _active_lease_locked(self) -> AuthorizationLease | None:
        lease = self._lease
        if lease is None:
            return None
        if lease.epoch != self._epoch or self._emergency_stopped or self._now() >= lease.expires_at:
            self._lease = None
            self._dry_run = True
            return None
        return lease

    def _binding_locked(self, binding_id: str | None) -> WindowBinding | None:
        if not binding_id:
            return None
        binding = self._bindings.get(str(binding_id))
        if binding is None or binding.epoch != self._epoch:
            return None
        return binding

    def _binding_error(self, binding: WindowBinding, current: WindowInfo) -> str:
        if binding.epoch != self._epoch:
            return "target_window_binding_epoch_stale"
        if (
            current.handle != binding.handle
            or current.process_id != binding.process_id
            or current.title.casefold() != binding.expected_title.casefold()
        ):
            return "target_window_mismatch"
        return ""

    def _consume_mutation_rate_slot_locked(self) -> str:
        now = float(self._monotonic())
        cutoff = now - self.rate_window_seconds
        while self._recent_action_times and self._recent_action_times[0] <= cutoff:
            self._recent_action_times.popleft()
        if (
            self._recent_action_times
            and now - self._recent_action_times[-1] < self.min_action_interval_seconds
        ):
            return "action_rate_min_interval"
        if len(self._recent_action_times) >= self.max_actions_per_window:
            return "action_rate_window_exceeded"
        self._recent_action_times.append(now)
        return ""

    def _capture_observation(self) -> ScreenObservation:
        try:
            width, height = self._backend.screen_size()
            width, height = int(width), int(height)
            if width <= 0 or height <= 0:
                raise DesktopBackendError("invalid_screen_size")
            window = self._backend.foreground_window()
            _validate_window_info(window)
            dpi_x, dpi_y = self._backend_window_dpi(window)
            occlusion_rects = self._backend_foreign_occlusion_rects(window)
            image = self._backend.capture_screen()
            cursor = self._backend.pointer_position()
            stable_window = self._backend.foreground_window()
            _validate_window_info(stable_window)
            stable_dpi_x, stable_dpi_y = self._backend_window_dpi(stable_window)
            stable_occlusion_rects = self._backend_foreign_occlusion_rects(stable_window)
        except DesktopGatewayError:
            raise
        except Exception as exc:
            raise DesktopBackendError("desktop_observation_failed") from exc
        if not isinstance(image, (bytes, bytearray)) or not image:
            raise DesktopBackendError("empty_screen_capture")
        if (
            not isinstance(cursor, tuple)
            or len(cursor) != 2
            or any(isinstance(value, bool) or not isinstance(value, int) for value in cursor)
        ):
            raise DesktopBackendError("invalid_pointer_position")
        if (
            stable_window.handle != window.handle
            or stable_window.process_id != window.process_id
            or stable_window.title.casefold() != window.title.casefold()
            or (
                stable_window.left,
                stable_window.top,
                stable_window.width,
                stable_window.height,
            )
            != (window.left, window.top, window.width, window.height)
        ):
            raise DesktopBackendError("foreground_window_changed_during_capture")
        if (stable_dpi_x, stable_dpi_y) != (dpi_x, dpi_y):
            raise DesktopBackendError("foreground_window_dpi_changed_during_capture")
        if stable_occlusion_rects != occlusion_rects:
            raise DesktopBackendError("foreign_occlusion_changed_during_capture")
        image_bytes = _mask_foreign_occlusions(
            bytes(image),
            width=width,
            height=height,
            rectangles=stable_occlusion_rects,
        )
        return ScreenObservation(
            captured_at=self._now(),
            sha256=hashlib.sha256(image_bytes).hexdigest(),
            width=width,
            height=height,
            window=stable_window,
            cursor_x=cursor[0],
            cursor_y=cursor[1],
            image_bytes=image_bytes,
            dpi_x=stable_dpi_x,
            dpi_y=stable_dpi_y,
        )

    def _backend_window_dpi(
        self,
        window: WindowInfo,
    ) -> Tuple[float | None, float | None]:
        provider = getattr(self._backend, "window_dpi", None)
        if provider is None:
            return None, None
        if not callable(provider):
            raise DesktopBackendError("invalid_window_dpi_provider")
        try:
            value = provider(window)
        except DesktopGatewayError:
            raise
        except Exception as exc:
            raise DesktopBackendError("window_dpi_query_failed") from exc
        if value is None:
            return None, None
        return _validate_window_dpi_pair(value)

    def _backend_foreign_occlusion_rects(
        self,
        window: WindowInfo,
    ) -> Tuple[Tuple[int, int, int, int], ...]:
        provider = getattr(self._backend, "foreign_occlusion_rects", None)
        if provider is None:
            return ()
        if not callable(provider):
            raise DesktopBackendError("invalid_foreign_occlusion_provider")
        try:
            value = provider(window)
        except DesktopGatewayError:
            raise
        except Exception as exc:
            raise DesktopBackendError("foreign_occlusion_query_failed") from exc
        if not isinstance(value, tuple) or len(value) > 128:
            raise DesktopBackendError("invalid_foreign_occlusion_rects")
        normalized: list[Tuple[int, int, int, int]] = []
        for item in value:
            if (
                not isinstance(item, tuple)
                or len(item) != 4
                or any(isinstance(part, bool) or not isinstance(part, int) for part in item)
            ):
                raise DesktopBackendError("invalid_foreign_occlusion_rects")
            left, top, right, bottom = item
            if left >= right or top >= bottom:
                raise DesktopBackendError("invalid_foreign_occlusion_rects")
            normalized.append((left, top, right, bottom))
        return tuple(normalized)

    def _backend_foreground_window(self) -> WindowInfo:
        try:
            window = self._backend.foreground_window()
        except DesktopGatewayError:
            raise
        except Exception as exc:
            raise DesktopBackendError("foreground_window_query_failed") from exc
        _validate_window_info(window)
        return window

    def _reject(
        self,
        action: str,
        action_id: str,
        reason: str,
        dry_run: bool,
        redacted: Mapping[str, Any],
        *,
        before: ScreenObservation | None = None,
        expected_before_sha256: str = "",
    ) -> DesktopActionResult:
        with self._state_lock:
            return self._reject_locked(
                action,
                action_id,
                reason,
                dry_run,
                redacted,
                before=before,
                expected_before_sha256=expected_before_sha256,
            )

    def _reject_locked(
        self,
        action: str,
        action_id: str,
        reason: str,
        dry_run: bool,
        redacted: Mapping[str, Any],
        *,
        before: ScreenObservation | None = None,
        expected_before_sha256: str = "",
    ) -> DesktopActionResult:
        safe_reason = _safe_label(reason)
        try:
            self._append_event(
                {
                    "event": "action_rejected",
                    "at": _utc_iso(self._now()),
                    "action_id": action_id,
                    "action": _safe_label(action),
                    "mode": "dry_run" if dry_run else "live",
                    "epoch": self._epoch,
                    "reason": safe_reason,
                    "params": dict(redacted),
                    "expected_before_sha256": expected_before_sha256,
                    "before_sha256": before.sha256 if before else "",
                }
            )
        except EvidenceWriteError:
            safe_reason = f"{safe_reason};evidence_rejection_write_failed"
        return DesktopActionResult(
            ok=False,
            action=action,
            action_id=action_id,
            dry_run=dry_run,
            reason=safe_reason,
            expected_before_sha256=expected_before_sha256,
            before_sha256=before.sha256 if before else "",
            before=before,
        )

    def _append_event(self, event: Mapping[str, Any]) -> None:
        payload = {
            "schema_version": "aureon-governed-desktop-evidence-v1",
            **dict(event),
        }
        line = (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode(
            "utf-8"
        )
        try:
            with self._evidence_lock:
                self.evidence_path.parent.mkdir(parents=True, exist_ok=True)
                flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
                fd = os.open(str(self.evidence_path), flags, 0o600)
                try:
                    written = os.write(fd, line)
                    if written != len(line):
                        raise OSError("short append")
                    os.fsync(fd)
                finally:
                    os.close(fd)
        except Exception as exc:
            raise EvidenceWriteError("append_only_evidence_write_failed") from exc


def _mask_foreign_occlusions(
    image_bytes: bytes,
    *,
    width: int,
    height: int,
    rectangles: Tuple[Tuple[int, int, int, int], ...],
) -> bytes:
    """Replace pixels from foreign top-level occluders with opaque black."""

    if not rectangles:
        return image_bytes
    try:
        from PIL import Image, ImageDraw
    except Exception as exc:  # pragma: no cover - depends on local install
        raise DesktopBackendError("image_masking_unavailable") from exc
    try:
        with Image.open(io.BytesIO(image_bytes)) as source:
            if source.size != (width, height):
                raise DesktopBackendError("screen_image_dimensions_mismatch")
            masked = source.convert("RGBA")
            draw = ImageDraw.Draw(masked)
            for raw_left, raw_top, raw_right, raw_bottom in rectangles:
                left = max(0, raw_left)
                top = max(0, raw_top)
                right = min(width, raw_right)
                bottom = min(height, raw_bottom)
                if left < right and top < bottom:
                    draw.rectangle((left, top, right - 1, bottom - 1), fill=(0, 0, 0, 255))
            buffer = io.BytesIO()
            masked.save(buffer, format="PNG")
            result = buffer.getvalue()
    except DesktopGatewayError:
        raise
    except Exception as exc:
        raise DesktopBackendError("screen_masking_failed") from exc
    if not result:
        raise DesktopBackendError("screen_masking_failed")
    return result


def _mask_observation_to_window(observation: ScreenObservation) -> ScreenObservation:
    """Return a full-screen PNG with non-target pixels replaced by opaque black."""

    try:
        from PIL import Image
    except Exception as exc:  # pragma: no cover - depends on the local backend install
        raise DesktopBackendError("image_masking_unavailable") from exc

    left = max(0, observation.window.left)
    top = max(0, observation.window.top)
    right = min(observation.width, observation.window.right)
    bottom = min(observation.height, observation.window.bottom)
    if left >= right or top >= bottom:
        raise DesktopBackendError("target_window_outside_screen")

    try:
        with Image.open(io.BytesIO(observation.image_bytes)) as source:
            if source.size != (observation.width, observation.height):
                raise DesktopBackendError("screen_image_dimensions_mismatch")
            source_rgba = source.convert("RGBA")
            masked = Image.new("RGBA", source.size, (0, 0, 0, 255))
            masked.paste(source_rgba.crop((left, top, right, bottom)), (left, top))
            buffer = io.BytesIO()
            masked.save(buffer, format="PNG")
            masked_bytes = buffer.getvalue()
    except DesktopGatewayError:
        raise
    except Exception as exc:
        raise DesktopBackendError("screen_masking_failed") from exc
    if not masked_bytes:
        raise DesktopBackendError("screen_masking_failed")

    return ScreenObservation(
        captured_at=observation.captured_at,
        sha256=hashlib.sha256(masked_bytes).hexdigest(),
        width=observation.width,
        height=observation.height,
        window=observation.window,
        cursor_x=observation.cursor_x,
        cursor_y=observation.cursor_y,
        image_bytes=masked_bytes,
        dpi_x=observation.dpi_x,
        dpi_y=observation.dpi_y,
    )


def _validate_window_info(window: WindowInfo) -> None:
    if not isinstance(window, WindowInfo):
        raise DesktopBackendError("invalid_foreground_window_record")
    if window.handle <= 0 or window.process_id <= 0 or not window.title.strip():
        raise DesktopBackendError("invalid_foreground_window_identity")
    if window.width <= 0 or window.height <= 0:
        raise DesktopBackendError("invalid_foreground_window_geometry")


def _validate_window_dpi_pair(value: object) -> Tuple[float, float]:
    if not isinstance(value, tuple) or len(value) != 2:
        raise DesktopBackendError("invalid_window_dpi")
    normalized: list[float] = []
    for component in value:
        if isinstance(component, bool) or not isinstance(component, (int, float)):
            raise DesktopBackendError("invalid_window_dpi")
        numeric = float(component)
        if not math.isfinite(numeric) or not 1.0 <= numeric <= 1_000.0:
            raise DesktopBackendError("invalid_window_dpi")
        normalized.append(numeric)
    return normalized[0], normalized[1]


def _validate_optional_window_dpi(
    dpi_x: float | None,
    dpi_y: float | None,
) -> None:
    if dpi_x is None and dpi_y is None:
        return
    if dpi_x is None or dpi_y is None:
        raise DesktopBackendError("invalid_window_dpi")
    _validate_window_dpi_pair((dpi_x, dpi_y))


def _capability_digest(token: str) -> str:
    if not isinstance(token, str):
        raise AuthorizationError("capability_token_must_be_text")
    if token != token.strip() or len(token) < 32:
        raise AuthorizationError("capability_token_requires_at_least_32_characters")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _lowercase_sha256(value: Any, *, name: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise DesktopGatewayError(f"{name}_invalid")
    return value


def _utc_iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _safe_label(value: Any) -> str:
    text = re.sub(r"[^A-Za-z0-9_.:;-]+", "_", str(value or ""))
    return text[:160] or "unspecified"


def _validate_key(key: Any) -> str:
    value = str(key or "").strip().lower()
    if not value:
        raise DesktopGatewayError("key_required")
    if value in _NAMED_KEYS or re.fullmatch(r"[a-z0-9]", value):
        return value
    raise DesktopGatewayError("key_not_allowed")


def _require_exact_keys(
    params: Mapping[str, Any],
    required: set[str],
    optional: set[str] | None = None,
) -> None:
    optional = optional or set()
    keys = set(params)
    if not required.issubset(keys):
        raise DesktopGatewayError("required_action_parameter_missing")
    if not keys.issubset(required | optional):
        raise DesktopGatewayError("unknown_action_parameter")


def _integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DesktopGatewayError(f"{name}_must_be_integer")
    return int(value)


def _finite_float(value: Any, name: str, minimum: float, maximum: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise DesktopGatewayError(f"{name}_must_be_number") from exc
    if number != number or number in (float("inf"), float("-inf")):
        raise DesktopGatewayError(f"{name}_must_be_finite")
    if number < minimum or number > maximum:
        raise DesktopGatewayError(f"{name}_out_of_range")
    return number


def _validate_action_params(action: str, params: Mapping[str, Any]) -> Dict[str, Any]:
    if action == "observe":
        _require_exact_keys(params, set())
        return {}
    if action == "move":
        _require_exact_keys(params, {"x", "y"}, {"duration"})
        return {
            "x": _integer(params["x"], "x"),
            "y": _integer(params["y"], "y"),
            "duration": _finite_float(params.get("duration", 0.0), "duration", 0.0, 2.0),
        }
    if action in {"click", "double_click", "right_click"}:
        _require_exact_keys(params, {"x", "y"})
        return {"x": _integer(params["x"], "x"), "y": _integer(params["y"], "y")}
    if action == "scroll":
        _require_exact_keys(params, {"x", "y", "amount"})
        amount = _integer(params["amount"], "amount")
        if amount == 0 or abs(amount) > MAX_SCROLL_CLICKS:
            raise DesktopGatewayError("scroll_amount_out_of_range")
        return {
            "x": _integer(params["x"], "x"),
            "y": _integer(params["y"], "y"),
            "amount": amount,
        }
    if action == "type":
        _require_exact_keys(params, {"text"}, {"interval"})
        text = params["text"]
        if not isinstance(text, str):
            raise DesktopGatewayError("text_must_be_string")
        if not text or len(text) > 10_000:
            raise DesktopGatewayError("text_length_out_of_range")
        return {
            "text": text,
            "interval": _finite_float(params.get("interval", 0.02), "interval", 0.0, 0.5),
        }
    if action == "press":
        _require_exact_keys(params, {"key"})
        return {"key": _validate_key(params["key"])}
    if action == "hotkey":
        _require_exact_keys(params, {"keys"})
        keys = params["keys"]
        if isinstance(keys, (str, bytes)) or not isinstance(keys, Sequence):
            raise DesktopGatewayError("hotkey_keys_must_be_sequence")
        normalized = [_validate_key(key) for key in keys]
        if len(normalized) < 2 or len(normalized) > 4:
            raise DesktopGatewayError("hotkey_key_count_out_of_range")
        return {"keys": normalized}
    raise DesktopGatewayError("action_not_allowed")


def _redact_params(action: str, params: Mapping[str, Any]) -> Dict[str, Any]:
    if action == "type":
        text = params.get("text")
        if not isinstance(text, str):
            return {"text_sha256": "", "text_length": 0}
        return {
            "text_sha256": _sha256_text(text),
            "text_length": len(text),
            "interval": params.get("interval", 0.02),
        }
    if action == "hotkey":
        keys = params.get("keys")
        return {"keys": list(keys) if isinstance(keys, Sequence) and not isinstance(keys, (str, bytes)) else []}
    allowed = {"x", "y", "amount", "duration", "key"}
    return {key: params[key] for key in sorted(set(params) & allowed)}


def _coordinate_gate_error(
    action: str,
    params: Mapping[str, Any],
    observation: ScreenObservation,
    window: WindowInfo,
) -> str:
    if action not in {"move", "click", "double_click", "right_click", "scroll"}:
        return ""
    x, y = int(params["x"]), int(params["y"])
    if x < 0 or y < 0 or x >= observation.width or y >= observation.height:
        return "coordinates_outside_screen"
    if x < window.left or y < window.top or x >= window.right or y >= window.bottom:
        return "coordinates_outside_target_window"
    return ""


__all__ = [
    "ALLOWED_ACTIONS",
    "MUTATING_ACTIONS",
    "MAX_LEASE_SECONDS",
    "AuthorizationError",
    "AuthorizationLease",
    "DesktopActionResult",
    "DesktopBackend",
    "DesktopBackendError",
    "DesktopGatewayError",
    "GovernedDesktopGateway",
    "get_governed_desktop_gateway",
    "LazyPyAutoGUIBackend",
    "PostconditionResult",
    "ScreenObservation",
    "WindowBinding",
    "WindowInfo",
]


_gateway_singleton: GovernedDesktopGateway | None = None
_gateway_singleton_lock = threading.Lock()


def get_governed_desktop_gateway(
    *,
    evidence_path: Path | None = None,
    max_actions_per_window: int | None = None,
) -> GovernedDesktopGateway:
    """Return the process-wide governed desktop authority.

    AgentCore, the operator bridge, and the local GUI runtime must share the
    same in-memory lease, emergency epoch, target bindings, and evidence stream.
    """

    global _gateway_singleton
    with _gateway_singleton_lock:
        if _gateway_singleton is None:
            kwargs: Dict[str, Any] = {"evidence_path": evidence_path}
            if max_actions_per_window is not None:
                kwargs["max_actions_per_window"] = max_actions_per_window
            _gateway_singleton = GovernedDesktopGateway(**kwargs)
        elif evidence_path is not None:
            requested = Path(evidence_path).expanduser().resolve()
            existing = _gateway_singleton.evidence_path.expanduser().resolve()
            if requested != existing:
                raise DesktopGatewayError("process_gateway_evidence_path_mismatch")
        if (
            max_actions_per_window is not None
            and _gateway_singleton.max_actions_per_window != max_actions_per_window
        ):
            raise DesktopGatewayError("process_gateway_rate_limit_mismatch")
        return _gateway_singleton
