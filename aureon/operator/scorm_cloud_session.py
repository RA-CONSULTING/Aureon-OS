"""Governed Edge session runner for an owner-supplied SCORM Cloud URL.

This module is deliberately separate from the sealed synthetic CourseOps
harness.  It accepts one exact HTTPS URL on ``cloud.scorm.com``, binds local
model configuration, launches Edge only through an injected launcher, discovers
one newly-created native window, and hands that window to
``GovernedWindowSession``.  Browser/profile secrets are never inspected or
copied.  In particular, an owner-existing Edge profile is used in place; this
module never opens its cookie, preference, history, or login-data files.

Importing or constructing these objects never launches a browser.  The only
launch boundary is :meth:`SCORMCloudSessionRunner.start`.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence
from urllib.parse import urlsplit

from aureon.autonomous.aureon_governed_desktop_gateway import WindowInfo
from aureon.operator.governed_window_session import (
    ExactWindowGateway,
    GovernedWindowSession,
    ProcessInspector,
    SessionWindowBinding,
    WindowCandidate,
    WindowEnumerator,
    WindowSessionPolicy,
    sign_window_session_policy,
)
from aureon.operator.hnc_scorm_coherence import classify_visible_prerequisite

SCORM_CLOUD_HOST = "cloud.scorm.com"
SCORM_CLOUD_ORIGIN_LABEL = "scorm-cloud-launch-context-v1"
SCORM_SESSION_SCHEMA = "aureon-scorm-cloud-session-v1"
SCORM_EVIDENCE_SCHEMA = "aureon-scorm-cloud-evidence-v1"
SCORM_NEUTRAL_CONTROL_SCHEMA = "aureon-scorm-neutral-control-manifest-v2"
SCORM_PUBLIC_PREVIEW_CONTROL_SCHEMA = SCORM_NEUTRAL_CONTROL_SCHEMA
SCORM_ISOLATED_PROFILE_MARKER_SCHEMA = "aureon-scorm-isolated-profile-owner-v1"
SCORM_ISOLATED_PROFILE_MARKER_NAME = ".aureon-scorm-isolated-profile-owner.json"
PROFILE_ISOLATED = "isolated"
PROFILE_OWNER_EXISTING = "owner_existing"
MAX_URL_BYTES = 16_384
MAX_EVIDENCE_BYTES = 32 * 1024 * 1024
MAX_EVIDENCE_ROWS = 100_000
MAX_WINDOW_RECORDS = 4_096
MAX_OWNER_PROCESS_RECORDS = 256
MAX_WINDOW_TITLE = 1_024
MAX_CAPTURE_SECONDS = 120.0
MAX_POLICY_SECONDS = 24 * 60 * 60
MIN_SIGNING_SECRET_BYTES = 32
DEFAULT_GUI_ACTIONS = (
    "double_click",
    "hotkey",
    "left_click",
    "move_mouse",
    "press_key",
    "right_click",
    "scroll",
    "type_text",
    "wait",
)

class SCORMCloudSessionError(RuntimeError):
    """A stable, non-sensitive failure at the external SCORM boundary."""

    def __init__(self, code: str) -> None:
        self.code = str(code)
        super().__init__(self.code)


@dataclass(frozen=True)
class EdgeProfileSpec:
    """One Edge profile strategy without any credential-file access."""

    mode: str
    user_data_dir: str
    profile_directory: str = "Default"
    owner_edge_process_id: int | None = None

    @classmethod
    def isolated(
        cls,
        user_data_dir: str | os.PathLike[str],
        *,
        profile_directory: str = "Default",
    ) -> EdgeProfileSpec:
        root = _canonical_profile_root(user_data_dir, must_exist=False)
        if root.exists():
            raise SCORMCloudSessionError("isolated_profile_must_be_fresh")
        if not root.parent.is_dir() or root.parent.is_symlink():
            raise SCORMCloudSessionError("isolated_profile_parent_invalid")
        return cls(
            mode=PROFILE_ISOLATED,
            user_data_dir=str(root),
            profile_directory=_profile_directory_name(profile_directory),
        )

    @classmethod
    def owner_existing(
        cls,
        user_data_dir: str | os.PathLike[str],
        *,
        profile_directory: str = "Default",
        owner_edge_process_id: int | None = None,
    ) -> EdgeProfileSpec:
        root = _canonical_profile_root(user_data_dir, must_exist=True)
        profile_name = _profile_directory_name(profile_directory)
        profile = root / profile_name
        if not profile.is_dir() or profile.is_symlink():
            raise SCORMCloudSessionError("owner_edge_profile_directory_invalid")
        owner_pid = _optional_positive_int("owner_edge_process_id", owner_edge_process_id)
        return cls(
            mode=PROFILE_OWNER_EXISTING,
            user_data_dir=str(root),
            profile_directory=profile_name,
            owner_edge_process_id=owner_pid,
        )

    def __post_init__(self) -> None:
        if self.mode not in {PROFILE_ISOLATED, PROFILE_OWNER_EXISTING}:
            raise SCORMCloudSessionError("edge_profile_mode_invalid")
        _nonempty_bounded("user_data_dir", self.user_data_dir, 32_768)
        _profile_directory_name(self.profile_directory)
        _optional_positive_int("owner_edge_process_id", self.owner_edge_process_id)
        if self.mode == PROFILE_ISOLATED and self.owner_edge_process_id is not None:
            raise SCORMCloudSessionError("isolated_profile_owner_process_not_allowed")
        root = _canonical_profile_root(
            self.user_data_dir,
            must_exist=self.mode == PROFILE_OWNER_EXISTING,
        )
        if str(root) != self.user_data_dir:
            raise SCORMCloudSessionError("edge_profile_root_not_canonical")
        profile = root / self.profile_directory
        if self.mode == PROFILE_ISOLATED:
            if root.exists():
                raise SCORMCloudSessionError("isolated_profile_must_be_fresh")
            if not root.parent.is_dir() or root.parent.is_symlink():
                raise SCORMCloudSessionError("isolated_profile_parent_invalid")
        elif (
            not profile.is_dir()
            or profile.is_symlink()
            or profile.resolve(strict=True).parent != root
        ):
            raise SCORMCloudSessionError("owner_edge_profile_directory_invalid")

    def audit_dict(self) -> Mapping[str, object]:
        return {
            "mode": self.mode,
            "owner_edge_process_id": self.owner_edge_process_id,
            "profile_directory_sha256": _sha256_text(self.profile_directory),
            "user_data_dir_sha256": _sha256_text(self.user_data_dir),
        }


@dataclass(frozen=True)
class SCORMCloudLaunchPlan:
    """Side-effect-free, hash-bound description of one Edge launch."""

    exact_url: str = field(repr=False)
    edge_executable: str
    profile: EdgeProfileSpec
    local_model: str
    local_model_endpoint: str
    expected_initial_title_regex: str
    allowed_title_regex: str
    session_id: str
    command: tuple[str, ...] = field(repr=False)
    allowed_gui_actions: tuple[str, ...] = DEFAULT_GUI_ACTIONS
    capture_timeout_seconds: float = 30.0
    policy_ttl_seconds: float = 7_200.0
    max_handoffs: int = 200
    schema_version: str = SCORM_SESSION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != SCORM_SESSION_SCHEMA:
            raise SCORMCloudSessionError("scorm_session_schema_invalid")
        _validate_scorm_url(self.exact_url)
        _validate_edge_executable(Path(self.edge_executable))
        if not isinstance(self.profile, EdgeProfileSpec):
            raise SCORMCloudSessionError("edge_profile_spec_required")
        _validate_local_model(self.local_model, self.local_model_endpoint)
        _validate_title_regex("expected_initial_title_regex", self.expected_initial_title_regex)
        _validate_title_regex("allowed_title_regex", self.allowed_title_regex)
        _nonempty_bounded("session_id", self.session_id, 160)
        _validate_actions(self.allowed_gui_actions)
        _bounded_float(
            "capture_timeout_seconds",
            self.capture_timeout_seconds,
            minimum=0.05,
            maximum=MAX_CAPTURE_SECONDS,
        )
        _bounded_float(
            "policy_ttl_seconds",
            self.policy_ttl_seconds,
            minimum=1.0,
            maximum=MAX_POLICY_SECONDS,
        )
        if (
            isinstance(self.max_handoffs, bool)
            or not isinstance(self.max_handoffs, int)
            or not 0 <= self.max_handoffs <= 1_000
        ):
            raise SCORMCloudSessionError("max_handoffs_out_of_range")
        expected_command = _edge_command(
            Path(self.edge_executable),
            self.profile,
            self.exact_url,
        )
        if self.command != expected_command:
            raise SCORMCloudSessionError("edge_launch_command_not_canonical")

    @property
    def url_sha256(self) -> str:
        return _sha256_text(self.exact_url)

    @property
    def plan_sha256(self) -> str:
        return _sha256_json(self.audit_dict())

    def audit_dict(self) -> Mapping[str, object]:
        return {
            "allowed_gui_actions": list(self.allowed_gui_actions),
            "allowed_title_regex_sha256": _sha256_text(self.allowed_title_regex),
            "capture_timeout_seconds": float(self.capture_timeout_seconds),
            "command_sha256": _sha256_json(list(self.command)),
            "edge_executable_sha256": _sha256_text(self.edge_executable),
            "expected_initial_title_regex_sha256": _sha256_text(
                self.expected_initial_title_regex
            ),
            "local_model": self.local_model,
            "local_model_endpoint": self.local_model_endpoint,
            "max_handoffs": self.max_handoffs,
            "policy_ttl_seconds": float(self.policy_ttl_seconds),
            "profile": self.profile.audit_dict(),
            "schema_version": self.schema_version,
            "session_id": self.session_id,
            "url_host": SCORM_CLOUD_HOST,
            "url_length": len(self.exact_url.encode("utf-8")),
            "url_sha256": self.url_sha256,
        }


@dataclass(frozen=True)
class SCORMPublicPreviewControlGrant:
    """Signed neutral policy for one exact external SCORM launch.

    It binds only launch, window-policy, lifetime, and GUI action scope. It does
    not claim provider verification, registration state, assessment status,
    persona, provenance, or credential effects. Those belong to a separately
    signed HNC launch authority after native URL evidence is captured. The
    historical class name is retained for composition compatibility.
    """

    session_id: str
    launch_plan_sha256: str
    launch_url_sha256: str
    policy_sha256: str
    allowed_actions: tuple[str, ...]
    issued_at_unix: int
    expires_at_unix: int
    hmac_sha256: str
    schema_version: str = SCORM_PUBLIC_PREVIEW_CONTROL_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != SCORM_PUBLIC_PREVIEW_CONTROL_SCHEMA:
            raise SCORMCloudSessionError("scorm_control_grant_schema_invalid")
        _nonempty_bounded("control_grant_session_id", self.session_id, 160)
        for name in (
            "launch_plan_sha256",
            "launch_url_sha256",
            "policy_sha256",
            "hmac_sha256",
        ):
            _sha256_hex(name, getattr(self, name))
        _validate_actions(self.allowed_actions)
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in (self.issued_at_unix, self.expires_at_unix)
        ):
            raise SCORMCloudSessionError("scorm_control_grant_time_invalid")
        lifetime = self.expires_at_unix - self.issued_at_unix
        if not 0 < lifetime <= MAX_POLICY_SECONDS:
            raise SCORMCloudSessionError("scorm_control_grant_lifetime_invalid")

    @classmethod
    def issue(
        cls,
        *,
        signing_secret: bytes,
        plan: SCORMCloudLaunchPlan,
        policy_sha256: str,
        issued_at: datetime,
        expires_at: datetime,
    ) -> SCORMPublicPreviewControlGrant:
        if not isinstance(plan, SCORMCloudLaunchPlan):
            raise SCORMCloudSessionError("scorm_launch_plan_required")
        secret = _signing_secret(signing_secret)
        issued = int(_aware_utc(issued_at).timestamp())
        expires = int(_aware_utc(expires_at).timestamp())
        unsigned = cls(
            session_id=plan.session_id,
            launch_plan_sha256=plan.plan_sha256,
            launch_url_sha256=plan.url_sha256,
            policy_sha256=_sha256_hex("policy_sha256", policy_sha256),
            allowed_actions=plan.allowed_gui_actions,
            issued_at_unix=issued,
            expires_at_unix=expires,
            hmac_sha256="0" * 64,
        )
        signature = hmac.new(
            secret,
            _canonical_json(unsigned.signed_payload()).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return cls(**{**unsigned.__dict__, "hmac_sha256": signature})

    def signed_payload(self) -> Mapping[str, object]:
        return {
            "allowed_actions": list(self.allowed_actions),
            "expires_at_unix": self.expires_at_unix,
            "issued_at_unix": self.issued_at_unix,
            "launch_plan_sha256": self.launch_plan_sha256,
            "launch_url_sha256": self.launch_url_sha256,
            "policy_sha256": self.policy_sha256,
            "schema_version": self.schema_version,
            "session_id": self.session_id,
        }

    def to_dict(self) -> Mapping[str, object]:
        return {
            "grant": self.signed_payload(),
            "hmac_sha256": self.hmac_sha256,
        }

    @property
    def control_grant_sha256(self) -> str:
        return _sha256_json(self.to_dict())

    def verify(
        self,
        signing_secret: bytes,
        *,
        plan: SCORMCloudLaunchPlan,
        policy_sha256: str,
        now: datetime,
    ) -> SCORMPublicPreviewControlGrant:
        secret = _signing_secret(signing_secret)
        expected = hmac.new(
            secret,
            _canonical_json(self.signed_payload()).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(self.hmac_sha256, expected):
            raise SCORMCloudSessionError("scorm_control_grant_signature_invalid")
        exact = (
            self.session_id,
            self.launch_plan_sha256,
            self.launch_url_sha256,
            self.policy_sha256,
            self.allowed_actions,
        )
        required = (
            plan.session_id,
            plan.plan_sha256,
            plan.url_sha256,
            _sha256_hex("policy_sha256", policy_sha256),
            plan.allowed_gui_actions,
        )
        if exact != required:
            raise SCORMCloudSessionError("scorm_control_grant_context_mismatch")
        current = int(_aware_utc(now).timestamp())
        if current < self.issued_at_unix or current >= self.expires_at_unix:
            raise SCORMCloudSessionError("scorm_control_grant_expired")
        return self

    def audit_dict(self) -> Mapping[str, object]:
        return {
            "allowed_actions": list(self.allowed_actions),
            "control_grant_sha256": self.control_grant_sha256,
            "expires_at_unix": self.expires_at_unix,
            "issued_at_unix": self.issued_at_unix,
            "launch_plan_sha256": self.launch_plan_sha256,
            "launch_url_sha256": self.launch_url_sha256,
            "policy_sha256": self.policy_sha256,
            "schema_version": self.schema_version,
            "session_id": self.session_id,
        }


SCORMNeutralControlManifest = SCORMPublicPreviewControlGrant


def build_scorm_cloud_edge_plan(
    *,
    exact_url: str,
    edge_executable: str | os.PathLike[str],
    profile: EdgeProfileSpec,
    local_model: str,
    local_model_endpoint: str,
    expected_initial_title_regex: str,
    allowed_title_regex: str,
    session_id: str | None = None,
    allowed_gui_actions: Sequence[str] = DEFAULT_GUI_ACTIONS,
    capture_timeout_seconds: float = 30.0,
    policy_ttl_seconds: float = 7_200.0,
    max_handoffs: int = 200,
) -> SCORMCloudLaunchPlan:
    """Validate and bind a launch plan without launching Edge or touching a profile."""

    validated_url = _validate_scorm_url(exact_url)
    executable = _validate_edge_executable(Path(edge_executable))
    if not isinstance(profile, EdgeProfileSpec):
        raise SCORMCloudSessionError("edge_profile_spec_required")
    identifier = session_id or f"scorm-{uuid.uuid4()}"
    return SCORMCloudLaunchPlan(
        exact_url=validated_url,
        edge_executable=str(executable),
        profile=profile,
        local_model=_nonempty_bounded("local_model", local_model, 128),
        local_model_endpoint=_validate_local_endpoint(local_model_endpoint),
        expected_initial_title_regex=expected_initial_title_regex,
        allowed_title_regex=allowed_title_regex,
        session_id=identifier,
        command=_edge_command(executable, profile, validated_url),
        allowed_gui_actions=tuple(sorted(set(allowed_gui_actions))),
        capture_timeout_seconds=float(capture_timeout_seconds),
        policy_ttl_seconds=float(policy_ttl_seconds),
        max_handoffs=max_handoffs,
    )


@dataclass(frozen=True)
class EdgeWindowRecord:
    """Native browser window plus exact owning executable path."""

    window: WindowInfo
    executable: str

    def __post_init__(self) -> None:
        _validate_window(self.window)
        _nonempty_bounded("window_executable", self.executable, 32_768)


@dataclass(frozen=True)
class LaunchedEdgeProcess:
    process_id: int
    launched_at_utc: str

    def __post_init__(self) -> None:
        _positive_int("launched_process_id", self.process_id)
        _nonempty_bounded("launched_at_utc", self.launched_at_utc, 80)


class EdgeProcessLauncher(Protocol):
    def launch(self, plan: SCORMCloudLaunchPlan) -> LaunchedEdgeProcess:
        ...

    def cleanup(
        self,
        launched: LaunchedEdgeProcess,
        *,
        terminate_owned_process: bool,
    ) -> None:
        ...


class EdgeWindowController(Protocol):
    def snapshot_windows(self) -> Sequence[EdgeWindowRecord]:
        ...

    def foreground_exact(self, window: WindowInfo) -> WindowInfo:
        ...

    def foreground_window(self) -> EdgeWindowRecord:
        ...

    def close_exact(self, window: WindowInfo) -> bool:
        ...


@dataclass(frozen=True)
class SCORMEvidenceReceipt:
    sequence: int
    entry_sha256: str


class SCORMEvidenceLedger:
    """Append-only, hash-chained JSONL evidence without URL/query plaintext."""

    def __init__(
        self,
        path: str | os.PathLike[str],
        *,
        run_id: str,
        utc_now: Callable[[], datetime] | None = None,
    ) -> None:
        self.path = Path(path)
        self.run_id = _nonempty_bounded("run_id", run_id, 160)
        self._utc_now = utc_now or (lambda: datetime.now(UTC))
        self._lock = threading.Lock()

    def append(self, event: str, data: Mapping[str, object]) -> SCORMEvidenceReceipt:
        event_name = _event_name(event)
        safe_data = dict(data)
        _assert_evidence_safe(safe_data)
        with self._lock:
            sequence, previous_sha = self._validated_tail_locked()
            payload: dict[str, object] = {
                "at": _utc_iso(self._utc_now()),
                "data": safe_data,
                "event": event_name,
                "previous_entry_sha256": previous_sha,
                "run_id": self.run_id,
                "schema_version": SCORM_EVIDENCE_SCHEMA,
                "sequence": sequence + 1,
            }
            entry_sha = _sha256_json(payload)
            row = {**payload, "entry_sha256": entry_sha}
            encoded = (_canonical_json(row) + "\n").encode("utf-8")
            if len(encoded) > 64 * 1024:
                raise SCORMCloudSessionError("scorm_evidence_row_too_large")
            self._append_bytes_locked(encoded)
            return SCORMEvidenceReceipt(sequence=sequence + 1, entry_sha256=entry_sha)

    def _validated_tail_locked(self) -> tuple[int, str]:
        if not self.path.exists():
            return 0, "0" * 64
        if self.path.is_symlink() or not self.path.is_file():
            raise SCORMCloudSessionError("scorm_evidence_path_invalid")
        try:
            if self.path.stat().st_size > MAX_EVIDENCE_BYTES:
                raise SCORMCloudSessionError("scorm_evidence_size_limit_exceeded")
            raw = self.path.read_bytes()
        except SCORMCloudSessionError:
            raise
        except OSError as exc:
            raise SCORMCloudSessionError("scorm_evidence_read_failed") from exc
        if not raw:
            return 0, "0" * 64
        if not raw.endswith(b"\n"):
            raise SCORMCloudSessionError("scorm_evidence_truncated")
        lines = raw.splitlines()
        if len(lines) > MAX_EVIDENCE_ROWS:
            raise SCORMCloudSessionError("scorm_evidence_row_limit_exceeded")
        previous = "0" * 64
        for expected_sequence, line in enumerate(lines, 1):
            try:
                row = json.loads(line.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise SCORMCloudSessionError("scorm_evidence_invalid_json") from exc
            if not isinstance(row, dict):
                raise SCORMCloudSessionError("scorm_evidence_row_invalid")
            supplied = row.pop("entry_sha256", None)
            if (
                row.get("schema_version") != SCORM_EVIDENCE_SCHEMA
                or row.get("run_id") != self.run_id
                or row.get("sequence") != expected_sequence
                or row.get("previous_entry_sha256") != previous
                or supplied != _sha256_json(row)
            ):
                raise SCORMCloudSessionError("scorm_evidence_chain_invalid")
            previous = str(supplied)
        return len(lines), previous

    def _append_bytes_locked(self, encoded: bytes) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self.path.parent.is_symlink() or self.path.is_symlink():
                raise SCORMCloudSessionError("scorm_evidence_path_invalid")
            flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
            if hasattr(os, "O_BINARY"):
                flags |= os.O_BINARY
            descriptor = os.open(self.path, flags, 0o600)
            try:
                written = os.write(descriptor, encoded)
                if written != len(encoded):
                    raise OSError("short append")
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        except SCORMCloudSessionError:
            raise
        except OSError as exc:
            raise SCORMCloudSessionError("scorm_evidence_append_failed") from exc


class _OwnedWindowEnumerator(WindowEnumerator):
    """Admit only the active window and one explicitly staged handoff target."""

    def __init__(
        self,
        controller: EdgeWindowController,
        *,
        executable: str,
        initial: WindowInfo,
        origin_label: str,
    ) -> None:
        self._controller = controller
        self._executable = executable
        self._active = initial
        self._origin_label = origin_label
        self._staged: WindowInfo | None = None
        self._lock = threading.RLock()

    def enumerate_windows(self) -> Sequence[WindowCandidate]:
        with self._lock:
            handles = {self._active.handle}
            if self._staged is not None:
                handles.add(self._staged.handle)
            records = _bounded_snapshot(self._controller)
            selected = [
                record
                for record in records
                if record.window.handle in handles
                and _same_executable(record.executable, self._executable)
            ]
            return tuple(
                WindowCandidate(window=record.window, origin_label=self._origin_label)
                for record in selected
            )

    def stage(self, window: WindowInfo) -> None:
        with self._lock:
            self._staged = window

    def commit(self, window: WindowInfo) -> None:
        with self._lock:
            self._active = window
            self._staged = None

    def rollback(self) -> None:
        with self._lock:
            self._staged = None


@dataclass
class _OwnedLaunchCleanup:
    """Idempotent cleanup for resources created by exactly one launch plan."""

    plan: SCORMCloudLaunchPlan
    launched_process: LaunchedEdgeProcess
    launcher: EdgeProcessLauncher = field(repr=False)
    controller: EdgeWindowController = field(repr=False)
    ledger: SCORMEvidenceLedger = field(repr=False)
    isolated_profile_created: bool = False
    _owned_windows: dict[int, WindowInfo] = field(default_factory=dict, init=False, repr=False)
    _closed: bool = field(default=False, init=False, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)

    def register_window(self, window: WindowInfo) -> None:
        _validate_window(window)
        with self._lock:
            if self._closed:
                raise SCORMCloudSessionError("scorm_launch_cleanup_closed")
            prior = self._owned_windows.get(window.handle)
            if prior is not None and prior.process_id != window.process_id:
                raise SCORMCloudSessionError("scorm_owned_window_identity_changed")
            self._owned_windows[window.handle] = window

    def close(self) -> bool:
        """Attempt every bounded cleanup stage without masking a primary failure."""

        with self._lock:
            if self._closed:
                return True
            self._closed = True
            failures: list[str] = []
            windows_released = 0
            for window in reversed(tuple(self._owned_windows.values())):
                try:
                    self.controller.close_exact(window)
                    windows_released += 1
                except Exception:
                    failures.append("exact_window_close_failed")
            terminate_process = self.plan.profile.mode == PROFILE_ISOLATED
            try:
                self.launcher.cleanup(
                    self.launched_process,
                    terminate_owned_process=terminate_process,
                )
            except Exception:
                failures.append("launched_process_cleanup_failed")
            profile_removed = False
            if self.isolated_profile_created:
                try:
                    profile_removed = _remove_owned_isolated_profile(self.plan)
                except Exception:
                    failures.append("isolated_profile_cleanup_failed")
            try:
                self.ledger.append(
                    "browser_launch_cleanup_completed",
                    {
                        "cleanup_ok": not failures,
                        "failure_codes": failures,
                        "isolated_profile_removed": profile_removed,
                        "process_termination_requested": terminate_process,
                        "window_count": len(self._owned_windows),
                        "windows_released": windows_released,
                    },
                )
            except Exception:
                failures.append("cleanup_evidence_failed")
            return not failures


@dataclass
class ActiveSCORMCloudSession:
    """Exact governed session and its stable local-control grant."""

    plan: SCORMCloudLaunchPlan
    launched_process: LaunchedEdgeProcess
    window_session: GovernedWindowSession
    initial_binding: SessionWindowBinding
    control_manifest: SCORMPublicPreviewControlGrant
    control_grant_sha256: str
    _controller: EdgeWindowController = field(repr=False)
    _process_inspector: ProcessInspector = field(repr=False)
    _enumerator: _OwnedWindowEnumerator = field(repr=False)
    _ledger: SCORMEvidenceLedger = field(repr=False)
    _launch_baseline_handles: frozenset[int] = field(repr=False)
    _launch_cleanup: _OwnedLaunchCleanup | None = field(default=None, repr=False)
    _closed: bool = field(default=False, init=False, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)
    _owned_handles: set[int] = field(default_factory=set, init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self._launch_baseline_handles, frozenset) or not all(
            isinstance(handle, int) and not isinstance(handle, bool) and handle > 0
            for handle in self._launch_baseline_handles
        ):
            raise SCORMCloudSessionError("scorm_launch_baseline_handles_invalid")
        if not isinstance(
            self.control_manifest,
            SCORMPublicPreviewControlGrant,
        ):
            raise SCORMCloudSessionError("scorm_control_grant_required")
        manifest_context = (
            self.control_manifest.session_id,
            self.control_manifest.launch_plan_sha256,
            self.control_manifest.launch_url_sha256,
            self.control_manifest.policy_sha256,
            self.control_manifest.allowed_actions,
            self.control_manifest.control_grant_sha256,
        )
        expected_context = (
            self.plan.session_id,
            self.plan.plan_sha256,
            self.plan.url_sha256,
            self.initial_binding.policy_sha256,
            self.plan.allowed_gui_actions,
            self.control_grant_sha256,
        )
        if manifest_context != expected_context:
            raise SCORMCloudSessionError("scorm_control_grant_context_mismatch")
        self._owned_handles.add(self.initial_binding.window.handle)
        if self._launch_cleanup is not None:
            self._launch_cleanup.register_window(self.initial_binding.window)

    def authorize_control(self, observation: object, action: object | None = None) -> bool:
        """Fresh-authorize an organism observation/action against the exact HWND."""

        try:
            binding = self.window_session.authorize_active_binding()
            if not _observation_matches_window(observation, binding.window):
                return False
            return action is None or _action_allowed(action, self.plan.allowed_gui_actions)
        except Exception:
            return False

    def authorize_binding_id(self) -> str:
        """Return the exact current binding id only after fresh session authorization."""

        return self.authorize_binding().binding_id

    def authorize_binding(self) -> SessionWindowBinding:
        """Return one atomically fresh exact binding/generation context."""

        with self._lock:
            if self._closed:
                raise SCORMCloudSessionError("scorm_session_closed")
            try:
                return self.window_session.authorize_active_binding()
            except Exception as exc:
                raise SCORMCloudSessionError("scorm_active_binding_not_authorized") from exc

    def handoff(self, *, target_handle: int) -> SessionWindowBinding:
        """Foreground and atomically bind an exact same-process title/popup change."""

        _positive_int("target_handle", target_handle)
        with self._lock:
            if self._closed:
                raise SCORMCloudSessionError("scorm_session_closed")
            active = self.window_session.active_binding
            if active is None:
                raise SCORMCloudSessionError("scorm_window_session_not_started")
            records = [
                record
                for record in _bounded_snapshot(self._controller)
                if record.window.handle == target_handle
                and _same_executable(record.executable, self.plan.edge_executable)
            ]
            if len(records) != 1:
                raise SCORMCloudSessionError("scorm_handoff_target_not_exact")
            target = records[0].window
            self._assert_handoff_target(active, target)
            return self._commit_handoff(active, target, target_handle=target.handle)

    def handoff_unique_changed_window(self) -> str:
        """Handoff only the sole exact, foreground, policy-bound identity change.

        No title lookup or caller-supplied HWND is used.  The current native
        foreground record must be a newly launched or previously session-owned
        Edge window, must differ from the active identity, and is staged into
        the restricted enumerator before ``GovernedWindowSession`` performs its
        own unique-candidate handoff.
        """

        with self._lock:
            if self._closed:
                raise SCORMCloudSessionError("scorm_session_closed")
            active = self.window_session.active_binding
            if active is None:
                raise SCORMCloudSessionError("scorm_window_session_not_started")
            try:
                foreground_record = self._controller.foreground_window()
            except Exception as exc:
                raise SCORMCloudSessionError("scorm_foreground_window_unavailable") from exc
            if not isinstance(foreground_record, EdgeWindowRecord):
                raise SCORMCloudSessionError("scorm_foreground_window_invalid")
            if not _same_executable(
                foreground_record.executable,
                self.plan.edge_executable,
            ):
                raise SCORMCloudSessionError("scorm_foreground_window_not_edge")
            target = foreground_record.window
            self._assert_handoff_target(active, target)
            return self._commit_handoff(active, target, target_handle=None).binding_id

    def _assert_handoff_target(
        self,
        active: SessionWindowBinding,
        target: WindowInfo,
    ) -> None:
        if target == active.window:
            raise SCORMCloudSessionError("scorm_handoff_identity_unchanged")
        if (
            target.handle in self._launch_baseline_handles
            and target.handle not in self._owned_handles
        ):
            raise SCORMCloudSessionError("scorm_handoff_preexisting_window_not_owned")
        if re.fullmatch(self.plan.allowed_title_regex, target.title) is None:
            raise SCORMCloudSessionError("scorm_handoff_title_not_allowed")
        try:
            in_lineage = self._process_inspector.is_same_process_or_descendant(
                target.process_id,
                ancestor_process_id=self.initial_binding.window.process_id,
            )
        except Exception as exc:
            raise SCORMCloudSessionError("scorm_handoff_lineage_failed") from exc
        if in_lineage is not True:
            raise SCORMCloudSessionError("scorm_handoff_process_not_allowed")

    def _commit_handoff(
        self,
        active: SessionWindowBinding,
        target: WindowInfo,
        *,
        target_handle: int | None,
    ) -> SessionWindowBinding:
        self._ledger.append(
            "window_handoff_authorized",
            {
                "active_window_sha256": active.window_sha256,
                "target_window_sha256": _window_sha256(target),
            },
        )
        foreground = self._controller.foreground_exact(target)
        if not _window_process_stable(target, foreground):
            raise SCORMCloudSessionError("scorm_handoff_foreground_mismatch")
        if self._launch_cleanup is not None:
            # Register the exact current identity before mutating the governed
            # binding. A native Edge navigation commonly changes title/rect in
            # the same HWND; that is safe only while the owning PID is stable.
            self._launch_cleanup.register_window(target)
        self._enumerator.stage(target)
        try:
            binding = self.window_session.handoff(
                expected_active_binding_id=active.binding_id,
                expected_active_window_sha256=active.window_sha256,
                target_handle=target_handle,
            )
        except Exception:
            self._enumerator.rollback()
            raise
        self._enumerator.commit(target)
        self._owned_handles.add(target.handle)
        try:
            self._ledger.append("window_handoff_committed", dict(binding.audit_dict()))
        except Exception:
            self._closed = True
            try:
                self.window_session.close()
            except Exception:
                pass
            if self._launch_cleanup is not None:
                self._launch_cleanup.close()
            raise
        return binding

    def record_access_observation(self, observation: object) -> str:
        """Record only a digest/length and return a stable visible-login blocker."""

        ocr_text = str(getattr(observation, "ocr_text", "") or "")
        vision_text = str(getattr(observation, "vision_text", "") or "")
        status = detect_scorm_access_blocker(ocr_text, vision_text)
        combined = f"{ocr_text}\n{vision_text}"
        self._ledger.append(
            "access_observed",
            {
                "access_status": status,
                "visible_text_length": len(combined),
                "visible_text_sha256": _sha256_text(combined),
            },
        )
        return status

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            try:
                self.window_session.close()
            finally:
                try:
                    if self._launch_cleanup is not None:
                        self._launch_cleanup.close()
                finally:
                    self._ledger.append(
                        "scorm_session_closed",
                        {"control_grant_sha256": self.control_grant_sha256},
                    )


class SCORMCloudSessionRunner:
    """Launch, capture, foreground once, then enter exact governed control."""

    def __init__(
        self,
        *,
        launcher: EdgeProcessLauncher,
        window_controller: EdgeWindowController,
        process_inspector: ProcessInspector,
        gateway: ExactWindowGateway,
        ledger: SCORMEvidenceLedger,
        signing_secret: bytes,
        utc_now: Callable[[], datetime] | None = None,
        monotonic: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        if not isinstance(signing_secret, bytes) or len(signing_secret) < MIN_SIGNING_SECRET_BYTES:
            raise SCORMCloudSessionError("scorm_signing_secret_too_short")
        self._launcher = launcher
        self._window_controller = window_controller
        self._process_inspector = process_inspector
        self._gateway = gateway
        self._ledger = ledger
        self._signing_secret = bytes(signing_secret)
        self._utc_now = utc_now or (lambda: datetime.now(UTC))
        self._monotonic = monotonic or time.monotonic
        self._sleeper = sleeper or time.sleep

    def start(self, plan: SCORMCloudLaunchPlan) -> ActiveSCORMCloudSession:
        if not isinstance(plan, SCORMCloudLaunchPlan):
            raise SCORMCloudSessionError("scorm_launch_plan_required")
        if plan.session_id != self._ledger.run_id:
            raise SCORMCloudSessionError("scorm_ledger_run_id_mismatch")
        _validate_runtime_profile(plan.profile)
        _validate_edge_executable(Path(plan.edge_executable))
        self._ledger.append("launch_plan_accepted", dict(plan.audit_dict()))
        baseline = _bounded_snapshot(self._window_controller)
        baseline_handles = {record.window.handle for record in baseline}
        self._validate_owner_process(plan, baseline)
        self._ledger.append(
            "window_baseline_captured",
            {
                "edge_window_count": sum(
                    _same_executable(record.executable, plan.edge_executable)
                    for record in baseline
                ),
                "window_inventory_sha256": _window_inventory_sha256(baseline),
            },
        )
        isolated_profile_created = self._prepare_isolated_profile(plan)
        self._ledger.append(
            "browser_launch_authorized",
            {
                "command_sha256": _sha256_json(list(plan.command)),
                "plan_sha256": plan.plan_sha256,
            },
        )
        try:
            launched = self._launcher.launch(plan)
        except Exception as exc:
            self._ledger.append("browser_launch_failed", {"reason": "launcher_failed"})
            if isolated_profile_created:
                try:
                    _remove_owned_isolated_profile(plan)
                except Exception:
                    pass
            raise SCORMCloudSessionError("scorm_edge_launch_failed") from exc
        if not isinstance(launched, LaunchedEdgeProcess):
            if isolated_profile_created:
                try:
                    _remove_owned_isolated_profile(plan)
                except Exception:
                    pass
            raise SCORMCloudSessionError("scorm_launcher_receipt_invalid")
        cleanup = _OwnedLaunchCleanup(
            plan=plan,
            launched_process=launched,
            launcher=self._launcher,
            controller=self._window_controller,
            ledger=self._ledger,
            isolated_profile_created=isolated_profile_created,
        )
        try:
            self._ledger.append(
                "browser_process_started",
                {
                    "launched_at_utc": launched.launched_at_utc,
                    "launched_process_id": launched.process_id,
                },
            )
            initial = self._await_initial_window(
                plan,
                launched,
                baseline_handles,
                cleanup=cleanup,
            )
            self._ledger.append(
                "browser_window_captured",
                {
                    "window_sha256": _window_sha256(initial.window),
                    **initial.window.audit_dict(),
                },
            )
            try:
                foreground = self._window_controller.foreground_exact(initial.window)
            except Exception as exc:
                raise SCORMCloudSessionError("scorm_initial_foreground_failed") from exc
            if not _window_process_stable(initial.window, foreground):
                raise SCORMCloudSessionError("scorm_initial_foreground_mismatch")
            self._ledger.append(
                "browser_window_foregrounded",
                {"window_sha256": _window_sha256(initial.window)},
            )
            return self._start_governed_session(
                plan,
                launched,
                foreground,
                baseline_handles=frozenset(baseline_handles),
                launch_cleanup=cleanup,
            )
        except Exception:
            cleanup.close()
            raise

    def attach(self, plan: SCORMCloudLaunchPlan) -> ActiveSCORMCloudSession:
        """Attach to the sole exact, already-open owner browser window.

        This path performs no browser launch and never registers the owner's
        existing window for process/window cleanup.  The signed launch plan,
        owner process/profile proof, exact executable, title policy, native
        URL evidence, and normal governed window binding remain mandatory.
        """

        if not isinstance(plan, SCORMCloudLaunchPlan):
            raise SCORMCloudSessionError("scorm_launch_plan_required")
        if plan.session_id != self._ledger.run_id:
            raise SCORMCloudSessionError("scorm_ledger_run_id_mismatch")
        if plan.profile.mode != PROFILE_OWNER_EXISTING:
            raise SCORMCloudSessionError("scorm_attach_requires_owner_existing_profile")
        _validate_runtime_profile(plan.profile)
        _validate_edge_executable(Path(plan.edge_executable))
        self._ledger.append("attach_plan_accepted", dict(plan.audit_dict()))
        baseline = _bounded_snapshot(self._window_controller)
        baseline_handles = frozenset(record.window.handle for record in baseline)
        self._validate_owner_process(plan, baseline)
        owner_pid = plan.profile.owner_edge_process_id
        if owner_pid is None:
            raise SCORMCloudSessionError("scorm_attach_owner_process_required")
        candidates: list[EdgeWindowRecord] = []
        allowed_existing_handles: set[int] = set()
        for record in baseline:
            if not _same_executable(record.executable, plan.edge_executable):
                continue
            try:
                in_lineage = self._process_inspector.is_same_process_or_descendant(
                    record.window.process_id,
                    ancestor_process_id=owner_pid,
                )
            except Exception as exc:
                raise SCORMCloudSessionError("scorm_attach_process_inspection_failed") from exc
            if in_lineage is not True:
                continue
            if re.fullmatch(plan.allowed_title_regex, record.window.title) is not None:
                allowed_existing_handles.add(record.window.handle)
            if (
                re.fullmatch(plan.expected_initial_title_regex, record.window.title) is None
                or re.fullmatch(plan.allowed_title_regex, record.window.title) is None
            ):
                continue
            candidates.append(record)
        if len(candidates) != 1:
            raise SCORMCloudSessionError(
                "scorm_existing_window_not_unique" if candidates else "scorm_existing_window_not_found"
            )
        initial = candidates[0]
        self._ledger.append(
            "existing_browser_window_captured",
            {
                "allowed_existing_window_count": len(allowed_existing_handles),
                "window_sha256": _window_sha256(initial.window),
                **initial.window.audit_dict(),
            },
        )
        try:
            foreground = self._window_controller.foreground_exact(initial.window)
        except Exception as exc:
            raise SCORMCloudSessionError("scorm_initial_foreground_failed") from exc
        if not _window_process_stable(initial.window, foreground):
            raise SCORMCloudSessionError("scorm_initial_foreground_mismatch")
        self._ledger.append(
            "existing_browser_window_foregrounded",
            {"window_sha256": _window_sha256(initial.window)},
        )
        attached = LaunchedEdgeProcess(
            process_id=owner_pid,
            launched_at_utc=_utc_iso(_aware_utc(self._utc_now())),
        )
        return self._start_governed_session(
            plan,
            attached,
            foreground,
            # Other owner-open windows remain protected as preexisting. Only
            # exact same-lineage windows already admitted by the signed title
            # policy (for example the SCORM player popup) may participate in
            # a later governed handoff.
            baseline_handles=baseline_handles - frozenset(allowed_existing_handles),
            launch_cleanup=None,
        )

    def _validate_owner_process(
        self,
        plan: SCORMCloudLaunchPlan,
        baseline: Sequence[EdgeWindowRecord],
    ) -> None:
        owner_pid = plan.profile.owner_edge_process_id
        if owner_pid is None:
            return
        executable_probe = getattr(self._process_inspector, "process_executable", None)
        profile_probe = getattr(self._process_inspector, "process_profile_matches", None)
        if not callable(executable_probe) or not callable(profile_probe):
            raise SCORMCloudSessionError("owner_edge_process_identity_probe_required")
        try:
            executable = executable_probe(owner_pid)
            profile_matches = profile_probe(
                owner_pid,
                user_data_dir=plan.profile.user_data_dir,
                profile_directory=plan.profile.profile_directory,
            )
        except Exception as exc:
            raise SCORMCloudSessionError("owner_edge_process_inspection_failed") from exc
        if not isinstance(executable, str) or not _same_executable(
            executable,
            plan.edge_executable,
        ):
            raise SCORMCloudSessionError("owner_edge_process_executable_mismatch")
        if profile_matches is not True:
            raise SCORMCloudSessionError("owner_edge_process_profile_mismatch")
        for record in baseline:
            if not _same_executable(record.executable, plan.edge_executable):
                continue
            try:
                self._process_inspector.is_same_process_or_descendant(
                    record.window.process_id,
                    ancestor_process_id=owner_pid,
                )
            except Exception as exc:
                raise SCORMCloudSessionError(
                    "owner_edge_process_inspection_failed"
                ) from exc

    def _prepare_isolated_profile(self, plan: SCORMCloudLaunchPlan) -> bool:
        if plan.profile.mode != PROFILE_ISOLATED:
            return False
        root = Path(plan.profile.user_data_dir)
        created = False
        try:
            root.mkdir(parents=False, exist_ok=False)
            created = True
            marker = root / SCORM_ISOLATED_PROFILE_MARKER_NAME
            marker.write_bytes(
                (_canonical_json(_isolated_profile_marker_payload(plan)) + "\n").encode(
                    "ascii"
                )
            )
            (root / plan.profile.profile_directory).mkdir(parents=False, exist_ok=False)
            marker = root / SCORM_ISOLATED_PROFILE_MARKER_NAME
            if (
                root.is_symlink()
                or marker.is_symlink()
                or (root / plan.profile.profile_directory).is_symlink()
            ):
                raise SCORMCloudSessionError("isolated_edge_profile_became_unsafe")
            if (root / plan.profile.profile_directory).resolve(strict=True).parent != root:
                raise SCORMCloudSessionError("isolated_edge_profile_became_unsafe")
            self._ledger.append(
                "isolated_profile_created",
                {"profile": plan.profile.audit_dict()},
            )
            return True
        except Exception as exc:
            if created:
                try:
                    _remove_owned_isolated_profile(plan)
                except Exception:
                    pass
            if isinstance(exc, SCORMCloudSessionError):
                raise
            raise SCORMCloudSessionError("isolated_edge_profile_creation_failed") from exc

    def _await_initial_window(
        self,
        plan: SCORMCloudLaunchPlan,
        launched: LaunchedEdgeProcess,
        baseline_handles: set[int],
        *,
        cleanup: _OwnedLaunchCleanup,
    ) -> EdgeWindowRecord:
        deadline = float(self._monotonic()) + float(plan.capture_timeout_seconds)
        disallowed_title_seen = False
        while float(self._monotonic()) < deadline:
            created: list[EdgeWindowRecord] = []
            for record in _bounded_snapshot(self._window_controller):
                if record.window.handle in baseline_handles:
                    continue
                if not _same_executable(record.executable, plan.edge_executable):
                    continue
                if self._is_launch_process_allowed(plan, launched, record.window.process_id):
                    created.append(record)
            for record in created:
                # Every exact post-launch Edge delta in the authorized process
                # lineage is session-owned for cleanup purposes. Register the
                # whole set before cardinality/title decisions so fail-closed
                # ambiguity cannot leak plan-created windows.
                cleanup.register_window(record.window)
            if len(created) > 1:
                raise SCORMCloudSessionError("scorm_new_window_ambiguous")
            if created:
                candidate = created[0]
                if (
                    re.fullmatch(
                        plan.expected_initial_title_regex,
                        candidate.window.title,
                    )
                    is None
                    or re.fullmatch(
                        plan.allowed_title_regex,
                        candidate.window.title,
                    )
                    is None
                ):
                    # Chromium exposes a newly created HWND before navigation
                    # has committed its final title. Keep the exact owned
                    # process/window candidate registered for cleanup, but do
                    # not bind or foreground it until its title reaches the
                    # configured policy. A permanently wrong title still
                    # fails closed at the bounded capture deadline.
                    disallowed_title_seen = True
                    self._sleeper(0.05)
                    continue
                return candidate
            self._sleeper(0.05)
        if disallowed_title_seen:
            raise SCORMCloudSessionError("scorm_new_window_title_not_allowed")
        raise SCORMCloudSessionError("scorm_new_window_not_observed")

    def _is_launch_process_allowed(
        self,
        plan: SCORMCloudLaunchPlan,
        launched: LaunchedEdgeProcess,
        candidate_pid: int,
    ) -> bool:
        roots = [launched.process_id]
        if plan.profile.owner_edge_process_id is not None:
            roots.append(plan.profile.owner_edge_process_id)
        for root in roots:
            try:
                if self._process_inspector.is_same_process_or_descendant(
                    candidate_pid,
                    ancestor_process_id=root,
                ) is True:
                    return True
            except Exception as exc:
                raise SCORMCloudSessionError("scorm_launch_process_inspection_failed") from exc
        return False

    def _start_governed_session(
        self,
        plan: SCORMCloudLaunchPlan,
        launched: LaunchedEdgeProcess,
        initial: WindowInfo,
        *,
        baseline_handles: frozenset[int],
        launch_cleanup: _OwnedLaunchCleanup | None,
    ) -> ActiveSCORMCloudSession:
        now = _aware_utc(self._utc_now())
        policy = WindowSessionPolicy(
            session_id=plan.session_id,
            nonce=uuid.uuid4().hex,
            initial_window=initial,
            root_process_id=initial.process_id,
            allowed_title_regex=plan.allowed_title_regex,
            origin_label=_scorm_origin_label(plan),
            issued_at=now,
            expires_at=now + timedelta(seconds=float(plan.policy_ttl_seconds)),
            max_handoffs=plan.max_handoffs,
        )
        signed = sign_window_session_policy(policy, self._signing_secret)
        enumerator = _OwnedWindowEnumerator(
            self._window_controller,
            executable=plan.edge_executable,
            initial=initial,
            origin_label=_scorm_origin_label(plan),
        )
        session = GovernedWindowSession(
            gateway=self._gateway,
            window_enumerator=enumerator,
            process_inspector=self._process_inspector,
            signed_policy=signed,
            signing_secret=self._signing_secret,
            utc_now=self._utc_now,
        )
        self._ledger.append(
            "governed_window_session_authorized",
            {
                "plan_sha256": plan.plan_sha256,
                "policy_sha256": signed.policy_sha256,
            },
        )
        try:
            binding = session.start()
        except Exception as exc:
            raise SCORMCloudSessionError("scorm_governed_window_start_failed") from exc
        control_manifest = SCORMPublicPreviewControlGrant.issue(
            signing_secret=self._signing_secret,
            plan=plan,
            policy_sha256=signed.policy_sha256,
            issued_at=now,
            expires_at=now + timedelta(seconds=float(plan.policy_ttl_seconds)),
        )
        control_grant = control_manifest.control_grant_sha256
        try:
            self._ledger.append(
                "scorm_session_started",
                {
                    "binding": binding.audit_dict(),
                    "control_grant_sha256": control_grant,
                    "control_manifest": control_manifest.audit_dict(),
                },
            )
        except Exception:
            try:
                session.close()
            except Exception:
                pass
            raise
        return ActiveSCORMCloudSession(
            plan=plan,
            launched_process=launched,
            window_session=session,
            initial_binding=binding,
            control_manifest=control_manifest,
            control_grant_sha256=control_grant,
            _controller=self._window_controller,
            _process_inspector=self._process_inspector,
            _enumerator=enumerator,
            _ledger=self._ledger,
            _launch_baseline_handles=baseline_handles,
            _launch_cleanup=launch_cleanup,
        )


class SubprocessEdgeLauncher:
    """Production Edge launcher; inert until its explicit ``launch`` call."""

    def __init__(self, *, cleanup_timeout_seconds: float = 5.0) -> None:
        self._cleanup_timeout = _bounded_float(
            "cleanup_timeout_seconds",
            cleanup_timeout_seconds,
            minimum=0.1,
            maximum=30.0,
        )
        self._processes: dict[tuple[int, str], subprocess.Popen[bytes]] = {}
        self._lock = threading.Lock()

    def launch(self, plan: SCORMCloudLaunchPlan) -> LaunchedEdgeProcess:
        try:
            process = subprocess.Popen(  # noqa: S603 - exact validated executable, shell=False
                list(plan.command),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False,
                close_fds=True,
            )
        except OSError as exc:
            raise SCORMCloudSessionError("scorm_edge_process_start_failed") from exc
        launched = LaunchedEdgeProcess(
            process_id=int(process.pid),
            launched_at_utc=_utc_iso(datetime.now(UTC)),
        )
        with self._lock:
            self._processes[(launched.process_id, launched.launched_at_utc)] = process
        return launched

    def cleanup(
        self,
        launched: LaunchedEdgeProcess,
        *,
        terminate_owned_process: bool,
    ) -> None:
        if not isinstance(launched, LaunchedEdgeProcess):
            raise SCORMCloudSessionError("scorm_launcher_cleanup_receipt_invalid")
        if not isinstance(terminate_owned_process, bool):
            raise SCORMCloudSessionError("scorm_launcher_cleanup_mode_invalid")
        key = (launched.process_id, launched.launched_at_utc)
        with self._lock:
            process = self._processes.pop(key, None)
        if process is None:
            raise SCORMCloudSessionError("scorm_launcher_cleanup_receipt_unknown")
        if not terminate_owned_process or process.poll() is not None:
            return
        descendants: list[Any] = []
        try:
            import psutil

            root = psutil.Process(process.pid)
            descendants = list(reversed(root.children(recursive=True)))
            for descendant in descendants:
                try:
                    descendant.terminate()
                except psutil.NoSuchProcess:
                    pass
        except Exception:
            descendants = []
        try:
            process.terminate()
            process.wait(timeout=self._cleanup_timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            try:
                process.wait(timeout=self._cleanup_timeout)
            except subprocess.TimeoutExpired as exc:
                raise SCORMCloudSessionError(
                    "scorm_owned_edge_process_cleanup_timeout"
                ) from exc
        except OSError as exc:
            raise SCORMCloudSessionError("scorm_owned_edge_process_cleanup_failed") from exc
        if descendants:
            try:
                import psutil

                _gone, alive = psutil.wait_procs(
                    descendants,
                    timeout=self._cleanup_timeout,
                )
                for descendant in alive:
                    try:
                        descendant.kill()
                    except psutil.NoSuchProcess:
                        pass
                if alive:
                    _gone, alive = psutil.wait_procs(
                        alive,
                        timeout=self._cleanup_timeout,
                    )
                if alive:
                    raise SCORMCloudSessionError(
                        "scorm_owned_edge_descendant_cleanup_timeout"
                    )
            except SCORMCloudSessionError:
                raise
            except Exception as exc:
                raise SCORMCloudSessionError(
                    "scorm_owned_edge_descendant_cleanup_failed"
                ) from exc


class PsutilProcessInspector:
    """Lazy local process-lineage adapter; it reads no browser profile data."""

    def is_same_process_or_descendant(
        self,
        process_id: int,
        *,
        ancestor_process_id: int,
    ) -> bool:
        _positive_int("process_id", process_id)
        _positive_int("ancestor_process_id", ancestor_process_id)
        if process_id == ancestor_process_id:
            return True
        try:
            import psutil

            current = psutil.Process(process_id)
            return any(parent.pid == ancestor_process_id for parent in current.parents())
        except Exception as exc:
            raise SCORMCloudSessionError("local_process_lineage_unavailable") from exc

    def process_executable(self, process_id: int) -> str:
        _positive_int("process_id", process_id)
        try:
            import psutil

            executable = psutil.Process(process_id).exe()
        except Exception as exc:
            raise SCORMCloudSessionError("local_process_executable_unavailable") from exc
        return _nonempty_bounded("process_executable", executable, 32_768)

    def process_profile_matches(
        self,
        process_id: int,
        *,
        user_data_dir: str,
        profile_directory: str,
    ) -> bool:
        """Verify exact profile flags without returning or recording command lines."""

        _positive_int("process_id", process_id)
        expected_root = _canonical_profile_root(user_data_dir, must_exist=True)
        expected_profile = _profile_directory_name(profile_directory)
        try:
            import psutil

            root = psutil.Process(process_id)
            processes = [root, *root.children(recursive=True)]
            if len(processes) > MAX_OWNER_PROCESS_RECORDS:
                raise SCORMCloudSessionError("owner_edge_process_tree_too_large")
            user_roots: list[Path] = []
            profiles: list[str] = []
            root_cmdline_read = False
            readable_processes = 0
            for index, process in enumerate(processes):
                try:
                    arguments = tuple(str(item) for item in process.cmdline())
                except (psutil.AccessDenied, psutil.NoSuchProcess) as exc:
                    if index == 0:
                        raise SCORMCloudSessionError(
                            "local_process_profile_root_cmdline_unavailable"
                        ) from exc
                    continue
                readable_processes += 1
                if index == 0:
                    root_cmdline_read = True
                user_roots.extend(
                    Path(value).expanduser().resolve(strict=False)
                    for value in _command_line_option_values(
                        arguments,
                        "--user-data-dir",
                    )
                )
                profiles.extend(
                    _command_line_option_values(
                        arguments,
                        "--profile-directory",
                    )
                )
        except SCORMCloudSessionError:
            raise
        except Exception as exc:
            raise SCORMCloudSessionError("local_process_profile_unavailable") from exc
        if not root_cmdline_read or readable_processes < 1:
            raise SCORMCloudSessionError("local_process_profile_evidence_missing")
        if user_roots:
            if any(root_value != expected_root for root_value in user_roots):
                return False
        else:
            local_app_data = os.environ.get("LOCALAPPDATA", "")
            if not local_app_data:
                return False
            default_root = (
                Path(local_app_data) / "Microsoft" / "Edge" / "User Data"
            ).resolve(strict=False)
            if expected_root != default_root:
                return False
        if profiles:
            return all(value == expected_profile for value in profiles)
        return expected_profile == "Default"


class Win32EdgeWindowController:
    """Bounded Win32 inventory and exact one-window foreground adapter."""

    def __init__(self, *, foreground_timeout_seconds: float = 5.0) -> None:
        self._timeout = _bounded_float(
            "foreground_timeout_seconds",
            foreground_timeout_seconds,
            minimum=0.05,
            maximum=30.0,
        )

    def snapshot_windows(self) -> Sequence[EdgeWindowRecord]:
        if sys.platform != "win32":
            raise SCORMCloudSessionError("win32_window_inventory_requires_windows")
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        records: list[EdgeWindowRecord] = []
        overflow = False
        callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        @callback_type
        def callback(handle: int, _lparam: int) -> bool:
            nonlocal overflow
            if len(records) >= MAX_WINDOW_RECORDS:
                overflow = True
                return False
            if not user32.IsWindowVisible(handle):
                return True
            record = _read_win32_window(int(handle))
            if record is not None:
                records.append(record)
            return True

        completed = bool(user32.EnumWindows(callback, 0))
        if overflow:
            raise SCORMCloudSessionError("win32_window_inventory_limit_exceeded")
        if not completed:
            raise SCORMCloudSessionError("win32_window_inventory_failed")
        return tuple(sorted(records, key=lambda record: record.window.handle))

    def foreground_exact(self, window: WindowInfo) -> WindowInfo:
        if sys.platform != "win32":
            raise SCORMCloudSessionError("win32_foreground_requires_windows")
        before = _find_exact_window(self.snapshot_windows(), window.handle)
        if not _window_process_stable(window, before.window):
            raise SCORMCloudSessionError("win32_foreground_identity_changed")
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        user32.ShowWindow(window.handle, 9)
        user32.SetForegroundWindow(window.handle)
        deadline = time.monotonic() + self._timeout
        while time.monotonic() < deadline:
            if int(user32.GetForegroundWindow()) == window.handle:
                after = _find_exact_window(self.snapshot_windows(), window.handle)
                if not _window_process_stable(window, after.window):
                    raise SCORMCloudSessionError("win32_foreground_identity_changed")
                return after.window
            time.sleep(0.05)
        raise SCORMCloudSessionError("win32_window_did_not_become_foreground")

    def foreground_window(self) -> EdgeWindowRecord:
        if sys.platform != "win32":
            raise SCORMCloudSessionError("win32_foreground_requires_windows")
        handle = int(ctypes.windll.user32.GetForegroundWindow())  # type: ignore[attr-defined]
        if handle <= 0:
            raise SCORMCloudSessionError("win32_foreground_window_unavailable")
        return _find_exact_window(self.snapshot_windows(), handle)

    def close_exact(self, window: WindowInfo) -> bool:
        if sys.platform != "win32":
            raise SCORMCloudSessionError("win32_close_requires_windows")
        records = [
            record
            for record in self.snapshot_windows()
            if record.window.handle == window.handle
        ]
        if not records:
            return False
        if len(records) != 1 or records[0].window != window:
            raise SCORMCloudSessionError("win32_close_identity_changed")
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        if not bool(user32.PostMessageW(window.handle, 0x0010, 0, 0)):
            raise SCORMCloudSessionError("win32_close_dispatch_failed")
        deadline = time.monotonic() + self._timeout
        while time.monotonic() < deadline:
            current = [
                record
                for record in self.snapshot_windows()
                if record.window.handle == window.handle
            ]
            if not current:
                return True
            if len(current) != 1 or current[0].window != window:
                raise SCORMCloudSessionError("win32_close_identity_changed")
            time.sleep(0.05)
        raise SCORMCloudSessionError("win32_window_did_not_close")


def detect_scorm_access_blocker(ocr_text: str, vision_text: str = "") -> str:
    """Classify visible access state without inspecting cookies or browser storage."""

    combined = re.sub(r"\s+", " ", f"{ocr_text} {vision_text}").strip().casefold()
    hard_markers = (
        "access denied",
        "generated by cloudfront",
        "missing key-pair-id query parameter or cookie value",
        "session expired",
        "the request could not be satisfied",
        "unauthorized",
        "forbidden",
    )
    shared_login_prerequisite = classify_visible_prerequisite(
        f"{ocr_text}\n{vision_text}".strip()
    ) == "login"
    scorm_login = "scorm cloud" in combined and any(
        marker in combined for marker in ("log in", "login", "sign in")
    )
    if (
        any(marker in combined for marker in hard_markers)
        or shared_login_prerequisite
        or scorm_login
    ):
        return "signed_session_cookie_or_owner_login_required"
    return "access_not_blocked_by_visible_login_gate"


def _isolated_profile_marker_payload(
    plan: SCORMCloudLaunchPlan,
) -> Mapping[str, str]:
    return {
        "plan_sha256": plan.plan_sha256,
        "schema_version": SCORM_ISOLATED_PROFILE_MARKER_SCHEMA,
        "session_id_sha256": _sha256_text(plan.session_id),
    }


def _remove_owned_isolated_profile(plan: SCORMCloudLaunchPlan) -> bool:
    if plan.profile.mode != PROFILE_ISOLATED:
        raise SCORMCloudSessionError("isolated_profile_cleanup_mode_invalid")
    root = Path(plan.profile.user_data_dir)
    if not root.exists():
        return True
    if root.is_symlink() or root.parent == root:
        raise SCORMCloudSessionError("isolated_profile_cleanup_root_unsafe")
    try:
        resolved = root.resolve(strict=True)
    except OSError as exc:
        raise SCORMCloudSessionError("isolated_profile_cleanup_root_invalid") from exc
    if resolved != root or str(resolved).startswith("\\\\"):
        raise SCORMCloudSessionError("isolated_profile_cleanup_root_unsafe")
    marker = root / SCORM_ISOLATED_PROFILE_MARKER_NAME
    if not marker.is_file() or marker.is_symlink():
        raise SCORMCloudSessionError("isolated_profile_cleanup_marker_missing")
    expected = (_canonical_json(_isolated_profile_marker_payload(plan)) + "\n").encode(
        "ascii"
    )
    try:
        supplied = marker.read_bytes()
    except OSError as exc:
        raise SCORMCloudSessionError("isolated_profile_cleanup_marker_unreadable") from exc
    if not hmac.compare_digest(supplied, expected):
        raise SCORMCloudSessionError("isolated_profile_cleanup_marker_mismatch")
    try:
        shutil.rmtree(root)
    except OSError as exc:
        raise SCORMCloudSessionError("isolated_profile_cleanup_failed") from exc
    if root.exists():
        raise SCORMCloudSessionError("isolated_profile_cleanup_incomplete")
    return True


def _validate_scorm_url(exact_url: object) -> str:
    if not isinstance(exact_url, str) or not exact_url:
        raise SCORMCloudSessionError("scorm_url_required")
    if exact_url != exact_url.strip() or "\\" in exact_url:
        raise SCORMCloudSessionError("scorm_url_not_exact")
    encoded = exact_url.encode("utf-8")
    if len(encoded) > MAX_URL_BYTES or any(ord(char) < 0x20 or ord(char) == 0x7F for char in exact_url):
        raise SCORMCloudSessionError("scorm_url_invalid_characters")
    try:
        parsed = urlsplit(exact_url)
        port = parsed.port
    except ValueError as exc:
        raise SCORMCloudSessionError("scorm_url_invalid") from exc
    if parsed.scheme != "https":
        raise SCORMCloudSessionError("scorm_url_https_required")
    if parsed.netloc != SCORM_CLOUD_HOST or parsed.hostname != SCORM_CLOUD_HOST:
        raise SCORMCloudSessionError("scorm_url_host_not_allowed")
    if parsed.username is not None or parsed.password is not None or port is not None:
        raise SCORMCloudSessionError("scorm_url_authority_not_exact")
    if parsed.path and not parsed.path.startswith("/"):
        raise SCORMCloudSessionError("scorm_url_path_invalid")
    return exact_url


def _validate_edge_executable(path: Path) -> Path:
    supplied = path.expanduser()
    if supplied.is_symlink():
        raise SCORMCloudSessionError("edge_executable_symlink_not_allowed")
    try:
        resolved = supplied.resolve(strict=True)
    except OSError as exc:
        raise SCORMCloudSessionError("edge_executable_not_found") from exc
    if not resolved.is_file() or resolved.name.casefold() not in {
        "chrome.exe",
        "msedge.exe",
    }:
        raise SCORMCloudSessionError("exact_chromium_executable_required")
    return resolved


def _edge_command(
    executable: Path,
    profile: EdgeProfileSpec,
    exact_url: str,
) -> tuple[str, ...]:
    return (
        str(executable),
        "--new-window",
        "--no-first-run",
        "--no-default-browser-check",
        f"--user-data-dir={profile.user_data_dir}",
        f"--profile-directory={profile.profile_directory}",
        exact_url,
    )


def _command_line_option_values(
    arguments: Sequence[str],
    option: str,
) -> list[str]:
    values: list[str] = []
    option_folded = option.casefold()
    for index, argument in enumerate(arguments):
        folded = argument.casefold()
        if folded.startswith(option_folded + "="):
            value = argument[len(option) + 1 :]
        elif folded == option_folded and index + 1 < len(arguments):
            value = arguments[index + 1]
        else:
            continue
        values.append(_nonempty_bounded("edge_process_option", value, 32_768))
    return values


def _canonical_profile_root(
    value: str | os.PathLike[str],
    *,
    must_exist: bool,
) -> Path:
    supplied = Path(value).expanduser()
    if str(supplied).startswith("\\\\") or supplied.is_symlink():
        raise SCORMCloudSessionError("edge_profile_root_must_be_local")
    try:
        resolved = supplied.resolve(strict=must_exist)
    except OSError as exc:
        raise SCORMCloudSessionError("edge_profile_root_invalid") from exc
    if str(resolved).startswith("\\\\"):
        raise SCORMCloudSessionError("edge_profile_root_must_be_local")
    if must_exist and not resolved.is_dir():
        raise SCORMCloudSessionError("edge_profile_root_invalid")
    if not resolved.is_absolute() or resolved.parent == resolved:
        raise SCORMCloudSessionError("edge_profile_root_too_broad")
    return resolved


def _validate_runtime_profile(profile: EdgeProfileSpec) -> None:
    root = _canonical_profile_root(
        profile.user_data_dir,
        must_exist=profile.mode == PROFILE_OWNER_EXISTING,
    )
    if str(root) != profile.user_data_dir:
        raise SCORMCloudSessionError("edge_profile_root_not_canonical")
    if profile.mode == PROFILE_ISOLATED:
        if root.exists():
            raise SCORMCloudSessionError("isolated_profile_must_be_fresh")
        if not root.parent.is_dir() or root.parent.is_symlink():
            raise SCORMCloudSessionError("isolated_profile_parent_invalid")
        return
    target = root / profile.profile_directory
    if (
        not target.is_dir()
        or target.is_symlink()
        or target.resolve(strict=True).parent != root
    ):
        raise SCORMCloudSessionError("owner_edge_profile_directory_invalid")


def _scorm_origin_label(plan: SCORMCloudLaunchPlan) -> str:
    return f"{SCORM_CLOUD_ORIGIN_LABEL}:{plan.plan_sha256}"


def _profile_directory_name(value: object) -> str:
    text = _nonempty_bounded("profile_directory", value, 128)
    if text in {".", ".."} or "/" in text or "\\" in text or ":" in text:
        raise SCORMCloudSessionError("edge_profile_directory_name_invalid")
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._-]*", text) is None:
        raise SCORMCloudSessionError("edge_profile_directory_name_invalid")
    return text


def _validate_local_model(model: object, endpoint: object) -> None:
    model_name = _nonempty_bounded("local_model", model, 128)
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/-]*", model_name) is None:
        raise SCORMCloudSessionError("local_model_name_invalid")
    _validate_local_endpoint(endpoint)


def _validate_local_endpoint(value: object) -> str:
    endpoint = _nonempty_bounded("local_model_endpoint", value, 512)
    try:
        parsed = urlsplit(endpoint)
        port = parsed.port
    except ValueError as exc:
        raise SCORMCloudSessionError("local_model_endpoint_invalid") from exc
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise SCORMCloudSessionError("local_model_endpoint_must_be_loopback")
    if parsed.username is not None or parsed.password is not None or port is None:
        raise SCORMCloudSessionError("local_model_endpoint_invalid")
    if not 1 <= port <= 65_535 or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise SCORMCloudSessionError("local_model_endpoint_invalid")
    return endpoint


def _validate_title_regex(name: str, value: object) -> str:
    pattern = _nonempty_bounded(name, value, 256)
    if not pattern.startswith("^") or not pattern.endswith("$"):
        raise SCORMCloudSessionError(f"{name}_must_be_anchored")
    try:
        re.compile(pattern)
    except re.error as exc:
        raise SCORMCloudSessionError(f"{name}_invalid") from exc
    return pattern


def _validate_actions(actions: object) -> tuple[str, ...]:
    if not isinstance(actions, tuple) or not actions:
        raise SCORMCloudSessionError("allowed_gui_actions_invalid")
    if tuple(sorted(set(actions))) != actions or not set(actions).issubset(DEFAULT_GUI_ACTIONS):
        raise SCORMCloudSessionError("allowed_gui_actions_invalid")
    return actions


def _bounded_snapshot(controller: EdgeWindowController) -> tuple[EdgeWindowRecord, ...]:
    try:
        records = tuple(controller.snapshot_windows())
    except SCORMCloudSessionError:
        raise
    except Exception as exc:
        raise SCORMCloudSessionError("edge_window_inventory_failed") from exc
    if len(records) > MAX_WINDOW_RECORDS:
        raise SCORMCloudSessionError("edge_window_inventory_limit_exceeded")
    if not all(isinstance(record, EdgeWindowRecord) for record in records):
        raise SCORMCloudSessionError("edge_window_inventory_record_invalid")
    handles = [record.window.handle for record in records]
    if len(handles) != len(set(handles)):
        raise SCORMCloudSessionError("edge_window_inventory_handle_duplicated")
    return records


def _same_executable(first: str, second: str) -> bool:
    return os.path.normcase(os.path.normpath(first)) == os.path.normcase(os.path.normpath(second))


def _window_inventory_sha256(records: Sequence[EdgeWindowRecord]) -> str:
    return _sha256_json(
        [
            {
                "executable_sha256": _sha256_text(record.executable),
                "window_sha256": _window_sha256(record.window),
            }
            for record in sorted(records, key=lambda item: item.window.handle)
        ]
    )


def _window_sha256(window: WindowInfo) -> str:
    return _sha256_json(
        {
            "handle": window.handle,
            "process_id": window.process_id,
            "rect": [window.left, window.top, window.width, window.height],
            "title": window.title,
        }
    )


def _validate_window(window: object) -> WindowInfo:
    if not isinstance(window, WindowInfo):
        raise SCORMCloudSessionError("window_info_required")
    _positive_int("window_handle", window.handle)
    _positive_int("window_process_id", window.process_id)
    _nonempty_bounded("window_title", window.title, MAX_WINDOW_TITLE)
    if any(isinstance(value, bool) or not isinstance(value, int) for value in (window.left, window.top)):
        raise SCORMCloudSessionError("window_position_invalid")
    _positive_int("window_width", window.width)
    _positive_int("window_height", window.height)
    return window


def _observation_matches_window(observation: object, window: WindowInfo) -> bool:
    rect = getattr(observation, "window_rect", None)
    return (
        getattr(observation, "window_handle", None) == window.handle
        and getattr(observation, "window_process_id", None) == window.process_id
        and getattr(observation, "window_title_sha256", None) == _sha256_text(window.title)
        and rect is not None
        and getattr(rect, "left", None) == window.left
        and getattr(rect, "top", None) == window.top
        and getattr(rect, "width", None) == window.width
        and getattr(rect, "height", None) == window.height
    )


def _action_allowed(action: object, allowed: Sequence[str]) -> bool:
    name = getattr(action, "name", None)
    if name not in allowed:
        return False
    if name == "type_text":
        params = getattr(action, "params", None)
        if not isinstance(params, Mapping) or params.get("text_class") == "credential":
            return False
    return True


def _read_win32_window(handle: int) -> EdgeWindowRecord | None:
    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    length = int(user32.GetWindowTextLengthW(handle))
    if length <= 0 or length > MAX_WINDOW_TITLE:
        return None
    title_buffer = ctypes.create_unicode_buffer(length + 1)
    if int(user32.GetWindowTextW(handle, title_buffer, length + 1)) <= 0:
        return None
    process_id = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(handle, ctypes.byref(process_id))
    rect = ctypes.wintypes.RECT()
    if not user32.GetWindowRect(handle, ctypes.byref(rect)):
        return None
    width = int(rect.right - rect.left)
    height = int(rect.bottom - rect.top)
    if process_id.value <= 0 or width <= 0 or height <= 0:
        return None
    executable = _win32_process_executable(int(process_id.value))
    if executable is None:
        return None
    return EdgeWindowRecord(
        window=WindowInfo(
            handle=handle,
            title=title_buffer.value,
            process_id=int(process_id.value),
            left=int(rect.left),
            top=int(rect.top),
            width=width,
            height=height,
        ),
        executable=executable,
    )


def _win32_process_executable(process_id: int) -> str | None:
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    open_process = kernel32.OpenProcess
    open_process.argtypes = [ctypes.wintypes.DWORD, ctypes.wintypes.BOOL, ctypes.wintypes.DWORD]
    open_process.restype = ctypes.wintypes.HANDLE
    query_image = kernel32.QueryFullProcessImageNameW
    query_image.argtypes = [
        ctypes.wintypes.HANDLE,
        ctypes.wintypes.DWORD,
        ctypes.wintypes.LPWSTR,
        ctypes.POINTER(ctypes.wintypes.DWORD),
    ]
    query_image.restype = ctypes.wintypes.BOOL
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [ctypes.wintypes.HANDLE]
    close_handle.restype = ctypes.wintypes.BOOL
    process = open_process(0x1000, False, process_id)
    if not process:
        return None
    try:
        capacity = 32_768
        buffer = ctypes.create_unicode_buffer(capacity)
        size = ctypes.wintypes.DWORD(capacity)
        if not query_image(process, 0, buffer, ctypes.byref(size)):
            return None
        return buffer.value
    finally:
        close_handle(process)


def _find_exact_window(records: Sequence[EdgeWindowRecord], handle: int) -> EdgeWindowRecord:
    matching = [record for record in records if record.window.handle == handle]
    if len(matching) != 1:
        raise SCORMCloudSessionError("win32_window_not_exact")
    return matching[0]


def _window_process_stable(expected: WindowInfo, current: WindowInfo) -> bool:
    return expected.handle == current.handle and expected.process_id == current.process_id


def _assert_evidence_safe(value: object, *, key: str = "") -> None:
    forbidden = {"command", "cookie", "exact_url", "password", "query", "secret", "token", "url"}
    if isinstance(value, Mapping):
        for child_key, child_value in value.items():
            name = str(child_key).casefold()
            if name in forbidden:
                raise SCORMCloudSessionError("scorm_evidence_sensitive_field_rejected")
            _assert_evidence_safe(child_value, key=name)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _assert_evidence_safe(item, key=key)
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        raise SCORMCloudSessionError("scorm_evidence_value_invalid")


def _event_name(value: object) -> str:
    name = str(value or "")
    if re.fullmatch(r"[a-z][a-z0-9_]{0,79}", name) is None:
        raise SCORMCloudSessionError("scorm_evidence_event_invalid")
    return name


def _positive_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise SCORMCloudSessionError(f"{name}_must_be_positive_integer")
    return value


def _sha256_hex(name: str, value: object) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise SCORMCloudSessionError(f"{name}_must_be_lowercase_sha256")
    return value


def _signing_secret(value: object) -> bytes:
    if not isinstance(value, bytes) or len(value) < MIN_SIGNING_SECRET_BYTES:
        raise SCORMCloudSessionError("scorm_signing_secret_too_short")
    return value


def _optional_positive_int(name: str, value: object) -> int | None:
    if value is None:
        return None
    return _positive_int(name, value)


def _nonempty_bounded(name: str, value: object, maximum: int) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > maximum:
        raise SCORMCloudSessionError(f"{name}_invalid")
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in value):
        raise SCORMCloudSessionError(f"{name}_invalid")
    return value


def _bounded_float(name: str, value: object, *, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SCORMCloudSessionError(f"{name}_must_be_number")
    number = float(value)
    if number != number or not minimum <= number <= maximum:
        raise SCORMCloudSessionError(f"{name}_out_of_range")
    return number


def _aware_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise SCORMCloudSessionError("scorm_utc_clock_invalid")
    return value.astimezone(UTC)


def _utc_iso(value: datetime) -> str:
    return _aware_utc(value).isoformat().replace("+00:00", "Z")


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


__all__ = [
    "ActiveSCORMCloudSession",
    "EdgeProfileSpec",
    "EdgeWindowRecord",
    "LaunchedEdgeProcess",
    "PsutilProcessInspector",
    "SCORMCloudLaunchPlan",
    "SCORMCloudSessionError",
    "SCORMCloudSessionRunner",
    "SCORMEvidenceLedger",
    "SCORMNeutralControlManifest",
    "SCORMPublicPreviewControlGrant",
    "SubprocessEdgeLauncher",
    "Win32EdgeWindowController",
    "build_scorm_cloud_edge_plan",
    "detect_scorm_access_blocker",
]
