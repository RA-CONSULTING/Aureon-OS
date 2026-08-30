"""Runtime bridge for the sealed local synthetic-assessment grant.

This module is deliberately narrow: it issues and activates a grant only after
the governed gateway has bound an exact browser window. It then supplies three
fail-closed callbacks for the planner, runtime human-gate boundary, and action
executor. Real or remote assessment contexts never receive an exception.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable, Mapping, Protocol

from aureon.autonomous.aureon_governed_desktop_gateway import WindowBinding
from aureon.operator.local_gui_observer import ScreenObservation
from aureon.operator.local_gui_runtime import GuiAction
from aureon.operator.synthetic_assessment_grant import (
    MAX_ACTIONS_PER_GRANT,
    MAX_GRANT_LIFETIME_SECONDS,
    SUPPORTED_ASSESSMENT_ACTIONS,
    ActiveSyntheticAssessmentSession,
    AssessmentActionContext,
    AssessmentSessionContext,
    AuthorizedAssessmentAction,
    SyntheticAssessmentGrant,
    SyntheticAssessmentReplayGuard,
    activate_synthetic_assessment_grant,
)


class AssessmentReceiptSink(Protocol):
    def append(self, event_type: str, payload: dict[str, object]) -> object:
        """Persist one synthetic-assessment authority event."""


@dataclass(frozen=True)
class SyntheticAssessmentRuntimeConfig:
    """Non-secret parameters for one exact local benchmark run."""

    asset_root: Path
    loopback_port: int
    server_pid: int
    run_id: str
    nonce: str
    ttl_seconds: float
    allowed_actions: tuple[str, ...]
    replay_directory: Path
    max_actions: int = 4096

    def __post_init__(self) -> None:
        root = Path(self.asset_root).expanduser().resolve(strict=True)
        if not root.is_dir() or root.is_symlink() or str(root).startswith("\\\\"):
            raise ValueError("synthetic assessment asset_root must be a local real directory")
        if (
            isinstance(self.loopback_port, bool)
            or not isinstance(self.loopback_port, int)
            or not 1 <= self.loopback_port <= 65_535
        ):
            raise ValueError("synthetic assessment loopback_port is invalid")
        if (
            isinstance(self.server_pid, bool)
            or not isinstance(self.server_pid, int)
            or self.server_pid <= 0
        ):
            raise ValueError("synthetic assessment server_pid is invalid")
        if not self.run_id or not self.nonce:
            raise ValueError("synthetic assessment run_id and nonce are required")
        if (
            isinstance(self.ttl_seconds, bool)
            or not isinstance(self.ttl_seconds, (int, float))
            or not math.isfinite(float(self.ttl_seconds))
            or not 0 < float(self.ttl_seconds) <= MAX_GRANT_LIFETIME_SECONDS
        ):
            raise ValueError("synthetic assessment ttl_seconds must be within 24 hours")
        actions = tuple(sorted(set(self.allowed_actions)))
        if not actions or not set(actions).issubset(SUPPORTED_ASSESSMENT_ACTIONS):
            raise ValueError("synthetic assessment action scope is invalid")
        if (
            isinstance(self.max_actions, bool)
            or not isinstance(self.max_actions, int)
            or not 1 <= self.max_actions <= MAX_ACTIONS_PER_GRANT
        ):
            raise ValueError("synthetic assessment max_actions is invalid")
        replay = Path(self.replay_directory).expanduser().resolve()
        if str(replay).startswith("\\\\"):
            raise ValueError("synthetic assessment replay directory must be local")
        object.__setattr__(self, "asset_root", root)
        object.__setattr__(self, "allowed_actions", actions)
        object.__setattr__(self, "ttl_seconds", float(self.ttl_seconds))
        object.__setattr__(self, "replay_directory", replay)

    @property
    def origin(self) -> str:
        return f"http://127.0.0.1:{self.loopback_port}"


class SyntheticAssessmentRuntimeController:
    """Own the single in-process activation and its sequenced action receipts."""

    def __init__(
        self,
        config: SyntheticAssessmentRuntimeConfig,
        *,
        secret: bytes | bytearray | memoryview,
        receipt_sink: AssessmentReceiptSink | None = None,
        utc_now: Callable[[], datetime] | None = None,
    ) -> None:
        if not isinstance(config, SyntheticAssessmentRuntimeConfig):
            raise TypeError("config must be SyntheticAssessmentRuntimeConfig")
        secret_bytes = bytes(secret)
        if len(secret_bytes) < 32:
            raise ValueError("synthetic assessment secret must contain at least 32 bytes")
        self.config = config
        self._secret = bytearray(secret_bytes)
        self._receipt_sink = receipt_sink
        self._utc_now = utc_now or (lambda: datetime.now(UTC))
        self._session: ActiveSyntheticAssessmentSession | None = None
        self._binding: WindowBinding | None = None
        self._last_grant_sha256 = ""

    @property
    def active(self) -> bool:
        return self._session is not None

    @property
    def grant_sha256(self) -> str:
        return self._last_grant_sha256

    def activate(self, binding: WindowBinding) -> str:
        """Issue and consume the grant only after exact browser binding exists."""

        if self._session is not None:
            raise RuntimeError("synthetic assessment controller is already active")
        if not isinstance(binding, WindowBinding):
            raise TypeError("binding must be a WindowBinding")
        if binding.process_id == self.config.server_pid:
            raise ValueError("synthetic server and browser processes must differ")
        issued_at = self._now()
        expires_at = issued_at + timedelta(seconds=self.config.ttl_seconds)
        try:
            grant = SyntheticAssessmentGrant.issue(
                secret=bytes(self._secret),
                asset_root=self.config.asset_root,
                run_id=self.config.run_id,
                nonce=self.config.nonce,
                loopback_port=self.config.loopback_port,
                server_pid=self.config.server_pid,
                browser_pid=binding.process_id,
                expected_window_binding_id=binding.binding_id,
                issued_at=issued_at,
                expires_at=expires_at,
                allowed_actions=self.config.allowed_actions,
                max_actions=self.config.max_actions,
            )
            context = self._session_context(binding=binding, now=issued_at)
            session = activate_synthetic_assessment_grant(
                grant,
                secret=bytes(self._secret),
                context=context,
                replay_guard=SyntheticAssessmentReplayGuard(self.config.replay_directory),
            )
        finally:
            for index in range(len(self._secret)):
                self._secret[index] = 0
        self._append_receipt(
            "synthetic_assessment_grant_activated",
            {
                "schema_version": "aureon-synthetic-assessment-runtime-v1",
                "grant_sha256": grant.grant_sha256,
                "asset_manifest_root_sha256": grant.asset_manifest.root_sha256,
                "replay_key_sha256": session.replay_key_sha256,
                "activation_context_sha256": session.activation_context_sha256,
                "persona_id": grant.persona_id,
                "synthetic": True,
                "max_actions": grant.max_actions,
            },
        )
        self._binding = binding
        self._session = session
        self._last_grant_sha256 = grant.grant_sha256
        return grant.grant_sha256

    def authorize_observation(
        self,
        observation: ScreenObservation,
        _action: GuiAction | None = None,
    ) -> bool:
        """Non-consuming planner check for the exact active synthetic context."""

        session = self._session
        binding = self._binding
        if session is None or binding is None or not self._observation_matches(observation, binding):
            return False
        try:
            session.validate_context(self._session_context(binding=binding, now=self._now()))
        except Exception:
            return False
        return True

    def authorize_gate(self, observation: ScreenObservation, gate: str) -> bool:
        return gate == "certification_assessment" and self.authorize_observation(observation)

    def authorize_action(
        self,
        observation: ScreenObservation,
        action: GuiAction,
    ) -> AuthorizedAssessmentAction | None:
        """Consume the next sequence and persist its hash-only authority receipt."""

        session = self._session
        binding = self._binding
        if (
            session is None
            or binding is None
            or not isinstance(action, GuiAction)
            or action.name not in self.config.allowed_actions
            or not self._observation_matches(observation, binding)
        ):
            return None
        now = self._now()
        context = AssessmentActionContext(
            **self._session_context(binding=binding, now=now).__dict__,
            action=action.name,
            action_sequence=session.next_action_sequence,
            observation_sha256=observation.screenshot_sha256,
        )
        try:
            authorized = session.authorize_action(context)
            self._append_receipt(
                "synthetic_assessment_action_authorized",
                authorized.to_dict(),
            )
        except Exception:
            return None
        return authorized

    def _session_context(
        self,
        *,
        binding: WindowBinding,
        now: datetime,
    ) -> AssessmentSessionContext:
        return AssessmentSessionContext(
            asset_root=self.config.asset_root,
            origin=self.config.origin,
            server_pid=self.config.server_pid,
            browser_pid=binding.process_id,
            window_binding_id=binding.binding_id,
            run_id=self.config.run_id,
            nonce=self.config.nonce,
            now=now,
        )

    @staticmethod
    def _observation_matches(
        observation: ScreenObservation,
        binding: WindowBinding,
    ) -> bool:
        return bool(
            isinstance(observation, ScreenObservation)
            and observation.window_handle == binding.handle
            and observation.window_process_id == binding.process_id
            and observation.window_title_sha256
            == hashlib.sha256(binding.expected_title.encode("utf-8")).hexdigest()
        )

    def _append_receipt(self, event_type: str, payload: dict[str, object]) -> None:
        if self._receipt_sink is None:
            return
        self._receipt_sink.append(event_type, payload)

    def _now(self) -> datetime:
        now = self._utc_now()
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise ValueError("utc_now must return a timezone-aware datetime")
        return now.astimezone(UTC)

    def close(self) -> None:
        for index in range(len(self._secret)):
            self._secret[index] = 0
        self._session = None
        self._binding = None


def secret_from_environment(name: str, environ: Mapping[str, str]) -> bytes:
    """Load a runtime-only HMAC key without accepting it on the command line."""

    value = str(environ.get(name, ""))
    try:
        encoded = value.encode("utf-8")
    finally:
        value = ""
    if len(encoded) < 32:
        raise ValueError(f"{name} must contain at least 32 UTF-8 bytes")
    return encoded


__all__ = [
    "SyntheticAssessmentRuntimeConfig",
    "SyntheticAssessmentRuntimeController",
    "secret_from_environment",
]
