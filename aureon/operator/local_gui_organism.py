"""Runnable, fully local Aureon GUI organism.

This module is the narrow composition root for Aureon's governed desktop
gateway, local screenshot/OCR observer, loopback-only planner, bounded
observe-plan-act-verify runtime, and append-only course benchmark ledger.

Importing it never touches the desktop or network.  A live run requires an
exact foreground-window title and a one-time capability token supplied through
``AUREON_GUI_CAPABILITY_TOKEN``.  The token is never accepted on the command
line, written to a ledger, or retained after the process exits.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import signal
import sys
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from aureon.autonomous.aureon_governed_desktop_gateway import (
    MAX_LEASE_SECONDS,
    MUTATING_ACTIONS,
    GovernedDesktopGateway,
    WindowBinding,
    get_governed_desktop_gateway,
)
from aureon.operator.course_benchmark_ledger import (
    AUTHORIZED_RUNTIME_LABELS,
    CourseBenchmarkLedger,
)
from aureon.operator.courseops_21_planner import CourseOps21Planner
from aureon.operator.courseops_21_stability import CourseOps21StabilityFingerprint
from aureon.operator.courseops_21_vision import CourseOps21VisionHook
from aureon.operator.governed_gui_adapter import (
    GatewayScreenshotBackend,
    GovernedGatewayExecutor,
)
from aureon.operator.local_fixture_planner import (
    LOCAL_FIXTURE_MANIFEST,
    LOCAL_FIXTURE_MANIFEST_SHA256,
    REQUIRED_GATEWAY_ACTIONS,
    LocalFixturePlanner,
)
from aureon.operator.local_gui_local_backends import (
    FrameArtifactPNGSource,
    LocalOllamaPlanner,
    LocalOllamaVisionPlanner,
    TesseractCLIBackend,
    discover_tesseract_executable,
)
from aureon.operator.local_gui_observer import (
    FrameArtifactStore,
    LocalGUIObserver,
)
from aureon.operator.local_gui_pause import HashOnlyPauseCheckpointStore
from aureon.operator.local_gui_runtime import (
    Executor,
    LocalGUIRuntime,
    LocalPlanner,
    Observer,
    RuntimeLimits,
    RuntimeResult,
)
from aureon.operator.local_gui_scorm_authority import SCORMVisionRuntimeAuthority
from aureon.operator.scorm_hnc_answer_brain import SwitchboardHNCAnswerBrain
from aureon.operator.scorm_player_stability import SCORMPlayerStabilityFingerprint
from aureon.operator.synthetic_assessment_grant import SUPPORTED_ASSESSMENT_ACTIONS
from aureon.operator.synthetic_assessment_runtime import (
    SyntheticAssessmentRuntimeConfig,
    SyntheticAssessmentRuntimeController,
    secret_from_environment,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_DIRECTORY = REPO_ROOT / "state" / "course_benchmarks"
CAPABILITY_TOKEN_ENV = "AUREON_GUI_CAPABILITY_TOKEN"
SYNTHETIC_ASSESSMENT_SECRET_ENV = "AUREON_SYNTHETIC_ASSESSMENT_SECRET"
ACTOR_ID = "aureon-os"
RUNTIME_SCHEMA = "aureon-local-gui-organism-v1"
_GATEWAY_TO_RUNTIME_ASSESSMENT_ACTION = {
    "click": "left_click",
    "move": "move_mouse",
    "press": "press_key",
    "scroll": "scroll",
    "type": "type_text",
}
_GATEWAY_TO_RUNTIME_ACTION = {
    "click": "left_click",
    "double_click": "double_click",
    "hotkey": "hotkey",
    "move": "move_mouse",
    "press": "press_key",
    "right_click": "right_click",
    "scroll": "scroll",
    "type": "type_text",
}

# A goal may navigate ordinary course material, but must never direct the
# organism to answer, solve, select, or submit assessment content for a person.
_ASSESSMENT_DIRECTIVE = re.compile(
    r"\b(?:answer|solve|select|guess|submit|pass|take)\b.{0,80}"
    r"\b(?:quiz|exam|assessment|knowledge[ -]?check|test question)\b"
    r"|\b(?:quiz|exam|assessment|knowledge[ -]?check|test question)\b.{0,80}"
    r"\b(?:answer|solve|select|guess|submit)\b",
    re.IGNORECASE,
)
_IMPERSONATION_DIRECTIVE = re.compile(
    r"\b(?:impersonate|pretend to be|act as|certify as|attest as)\b",
    re.IGNORECASE,
)


class OrganismConfigurationError(ValueError):
    """Raised when a run would cross a local, identity, or authority gate."""


def _required_text(name: str, value: object, *, maximum: int) -> str:
    text = str(value or "").strip()
    if not text or len(text) > maximum or any(char in text for char in "\r\n"):
        raise OrganismConfigurationError(f"{name}_invalid")
    return text


def _valid_sha256(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64 or value != value.lower():
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _reason_evidence(reason: str) -> str:
    """Return non-reversible evidence for a potentially model-authored reason."""

    encoded = str(reason or "").encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}:bytes:{len(encoded)}"


def _build_fingerprint() -> str:
    """Hash the bounded organism source set without invoking Git or a shell."""

    source_paths = (
        Path(__file__),
        REPO_ROOT / "aureon" / "autonomous" / "aureon_governed_desktop_gateway.py",
        REPO_ROOT / "aureon" / "operator" / "governed_gui_adapter.py",
        REPO_ROOT / "aureon" / "operator" / "local_gui_observer.py",
        REPO_ROOT / "aureon" / "operator" / "local_gui_pause.py",
        REPO_ROOT / "aureon" / "operator" / "local_gui_runtime.py",
        REPO_ROOT / "aureon" / "operator" / "local_gui_scorm_authority.py",
        REPO_ROOT / "aureon" / "operator" / "local_gui_local_backends.py",
        REPO_ROOT / "aureon" / "operator" / "hnc_scorm_coherence.py",
        REPO_ROOT / "aureon" / "operator" / "scorm_cloud_session.py",
        REPO_ROOT / "aureon" / "operator" / "course_benchmark_ledger.py",
        REPO_ROOT / "aureon" / "operator" / "courseops_21_planner.py",
        REPO_ROOT / "aureon" / "operator" / "courseops_21_stability.py",
        REPO_ROOT / "aureon" / "operator" / "courseops_21_vision.py",
        REPO_ROOT / "aureon" / "operator" / "synthetic_assessment_grant.py",
        REPO_ROOT / "aureon" / "operator" / "synthetic_assessment_runtime.py",
    )
    digest = hashlib.sha256()
    for path in source_paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


@dataclass(frozen=True)
class LocalGUIOrganismConfig:
    """Validated configuration for exactly one bounded GUI run."""

    goal: str
    expected_window_title: str
    allowed_actions: tuple[str, ...]
    model: str = "llama3:latest"
    endpoint: str = "http://127.0.0.1:11434"
    planner_kind: str = "ollama"
    planner_timeout_seconds: float = 60.0
    authorization_label: str = "sandbox_test"
    live: bool = False
    lease_ttl_seconds: float = 3600.0
    expected_process_id: int | None = None
    max_steps: int = 50
    max_retries_per_action: int = 2
    max_consecutive_unchanged: int = 4
    max_seconds: float = 900.0
    gateway_max_actions_per_window: int = 60
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    state_directory: Path = DEFAULT_STATE_DIRECTORY
    synthetic_assessment_asset_root: Path | None = None
    synthetic_assessment_loopback_port: int | None = None
    synthetic_assessment_server_pid: int | None = None
    synthetic_assessment_nonce: str = ""
    synthetic_assessment_max_actions: int = 4096
    scorm_run_authority_sha256: str = ""
    scorm_control_grant_sha256: str = ""
    scorm_hnc_answer_brain: bool = False

    def __post_init__(self) -> None:
        goal = _required_text("goal", self.goal, maximum=4_000)
        title = _required_text("expected_window_title", self.expected_window_title, maximum=512)
        model = _required_text("model", self.model, maximum=256)
        run_id = _required_text("run_id", self.run_id, maximum=128)
        if not re.fullmatch(r"[A-Za-z0-9._-]+", run_id):
            raise OrganismConfigurationError("run_id_invalid")
        synthetic_mode_requested = any(
            (
                self.synthetic_assessment_asset_root is not None,
                self.synthetic_assessment_loopback_port is not None,
                self.synthetic_assessment_server_pid is not None,
                bool(self.synthetic_assessment_nonce),
            )
        )
        if (
            _ASSESSMENT_DIRECTIVE.search(goal)
            and not synthetic_mode_requested
            and self.planner_kind != "scorm_vision"
        ):
            raise OrganismConfigurationError("certification_assessment_goal_blocked")
        if _IMPERSONATION_DIRECTIVE.search(goal):
            raise OrganismConfigurationError("identity_impersonation_goal_blocked")
        if self.planner_kind not in {"ollama", "fixture", "courseops", "scorm_vision"}:
            raise OrganismConfigurationError("planner_kind_invalid")
        if self.authorization_label not in AUTHORIZED_RUNTIME_LABELS:
            raise OrganismConfigurationError("authorization_label_invalid")
        if (
            self.authorization_label == "owner_benchmark_test"
            and self.planner_kind != "scorm_vision"
        ):
            raise OrganismConfigurationError(
                "owner_benchmark_test_requires_scorm_vision"
            )
        allowed_actions = tuple(dict.fromkeys(self.allowed_actions))
        if not allowed_actions or not set(allowed_actions).issubset(MUTATING_ACTIONS):
            raise OrganismConfigurationError("allowed_actions_invalid")
        if self.planner_kind == "fixture":
            if self.authorization_label != "sandbox_test":
                raise OrganismConfigurationError("fixture_planner_requires_sandbox_test")
            if not REQUIRED_GATEWAY_ACTIONS.issubset(allowed_actions):
                raise OrganismConfigurationError("fixture_planner_action_scope_incomplete")
        if self.planner_kind == "courseops" and not synthetic_mode_requested:
            raise OrganismConfigurationError("courseops_planner_requires_synthetic_assessment")
        if self.planner_kind == "scorm_vision":
            if not _valid_sha256(self.scorm_run_authority_sha256):
                raise OrganismConfigurationError(
                    "scorm_vision_requires_run_authority_sha256"
                )
            if not _valid_sha256(self.scorm_control_grant_sha256):
                raise OrganismConfigurationError(
                    "scorm_vision_requires_control_grant_sha256"
                )
        elif (
            self.scorm_run_authority_sha256
            or self.scorm_control_grant_sha256
        ):
            raise OrganismConfigurationError(
                "pause_and_scorm_authority_require_scorm_vision"
            )
        if not isinstance(self.scorm_hnc_answer_brain, bool):
            raise OrganismConfigurationError("scorm_hnc_answer_brain_invalid")
        if self.scorm_hnc_answer_brain and self.planner_kind != "scorm_vision":
            raise OrganismConfigurationError(
                "scorm_hnc_answer_brain_requires_scorm_vision"
            )
        if synthetic_mode_requested:
            if (
                self.synthetic_assessment_asset_root is None
                or self.synthetic_assessment_loopback_port is None
                or self.synthetic_assessment_server_pid is None
                or not self.synthetic_assessment_nonce
            ):
                raise OrganismConfigurationError("synthetic_assessment_context_incomplete")
            if self.planner_kind not in {"ollama", "courseops"} or (
                self.authorization_label != "sandbox_test"
            ):
                raise OrganismConfigurationError(
                    "synthetic_assessment_requires_local_ollama_sandbox"
                )
            assessment_actions = {
                _GATEWAY_TO_RUNTIME_ASSESSMENT_ACTION[action]
                for action in allowed_actions
                if action in _GATEWAY_TO_RUNTIME_ASSESSMENT_ACTION
            }
            if not assessment_actions.intersection(SUPPORTED_ASSESSMENT_ACTIONS):
                raise OrganismConfigurationError("synthetic_assessment_action_scope_empty")
            if (
                isinstance(self.synthetic_assessment_loopback_port, bool)
                or not isinstance(self.synthetic_assessment_loopback_port, int)
                or not 1 <= self.synthetic_assessment_loopback_port <= 65_535
            ):
                raise OrganismConfigurationError("synthetic_assessment_port_invalid")
            if (
                isinstance(self.synthetic_assessment_server_pid, bool)
                or not isinstance(self.synthetic_assessment_server_pid, int)
                or self.synthetic_assessment_server_pid <= 0
            ):
                raise OrganismConfigurationError("synthetic_assessment_server_pid_invalid")
            if (
                len(self.synthetic_assessment_nonce) < 16
                or not re.fullmatch(r"[A-Za-z0-9._:-]+", self.synthetic_assessment_nonce)
            ):
                raise OrganismConfigurationError("synthetic_assessment_nonce_invalid")
            if (
                isinstance(self.synthetic_assessment_max_actions, bool)
                or not isinstance(self.synthetic_assessment_max_actions, int)
                or not 1 <= self.synthetic_assessment_max_actions <= 10_000
            ):
                raise OrganismConfigurationError("synthetic_assessment_max_actions_invalid")
        if isinstance(self.lease_ttl_seconds, bool):
            raise OrganismConfigurationError("lease_ttl_invalid")
        try:
            ttl = float(self.lease_ttl_seconds)
        except (TypeError, ValueError) as exc:
            raise OrganismConfigurationError("lease_ttl_invalid") from exc
        if not 0 < ttl <= MAX_LEASE_SECONDS:
            raise OrganismConfigurationError("lease_ttl_invalid")
        if self.expected_process_id is not None and (
            isinstance(self.expected_process_id, bool)
            or not isinstance(self.expected_process_id, int)
            or self.expected_process_id <= 0
        ):
            raise OrganismConfigurationError("expected_process_id_invalid")
        limits = RuntimeLimits(
            max_steps=self.max_steps,
            max_retries_per_action=self.max_retries_per_action,
            max_consecutive_unchanged=self.max_consecutive_unchanged,
            max_seconds=self.max_seconds,
        )
        if (
            isinstance(self.gateway_max_actions_per_window, bool)
            or not isinstance(self.gateway_max_actions_per_window, int)
            or not 1 <= self.gateway_max_actions_per_window <= 1_000
        ):
            raise OrganismConfigurationError("gateway_rate_limit_invalid")
        if (
            isinstance(self.planner_timeout_seconds, bool)
            or not isinstance(self.planner_timeout_seconds, (int, float))
            or not math.isfinite(float(self.planner_timeout_seconds))
            or not 0 < float(self.planner_timeout_seconds) <= 300
        ):
            raise OrganismConfigurationError("planner_timeout_invalid")
        if self.planner_kind in {"ollama", "scorm_vision"} and (
            float(self.planner_timeout_seconds) + 5.0 >= float(limits.max_seconds)
        ):
            raise OrganismConfigurationError("planner_timeout_must_fit_runtime")
        if ttl < float(limits.max_seconds) + 5.0:
            raise OrganismConfigurationError("lease_ttl_must_cover_runtime")
        state_directory = Path(self.state_directory).expanduser().resolve()
        if str(state_directory).startswith("\\\\"):
            raise OrganismConfigurationError("state_directory_must_be_local")

        object.__setattr__(self, "goal", goal)
        object.__setattr__(self, "expected_window_title", title)
        object.__setattr__(self, "model", model)
        object.__setattr__(self, "run_id", run_id)
        object.__setattr__(
            self,
            "scorm_run_authority_sha256",
            str(self.scorm_run_authority_sha256).lower(),
        )
        object.__setattr__(
            self,
            "scorm_control_grant_sha256",
            str(self.scorm_control_grant_sha256).lower(),
        )
        object.__setattr__(self, "allowed_actions", allowed_actions)
        object.__setattr__(self, "lease_ttl_seconds", ttl)
        object.__setattr__(
            self,
            "planner_timeout_seconds",
            float(self.planner_timeout_seconds),
        )
        object.__setattr__(self, "state_directory", state_directory)
        if self.synthetic_assessment_asset_root is not None:
            try:
                synthetic_root = Path(self.synthetic_assessment_asset_root).expanduser().resolve(
                    strict=True
                )
            except OSError as exc:
                raise OrganismConfigurationError(
                    "synthetic_assessment_asset_root_invalid"
                ) from exc
            if (
                not synthetic_root.is_dir()
                or synthetic_root.is_symlink()
                or str(synthetic_root).startswith("\\\\")
            ):
                raise OrganismConfigurationError("synthetic_assessment_asset_root_invalid")
            object.__setattr__(self, "synthetic_assessment_asset_root", synthetic_root)
        # Constructing RuntimeLimits above is the single schema validation for
        # all numeric loop bounds; keep the normalized values on this config.
        object.__setattr__(self, "max_seconds", float(limits.max_seconds))

    @property
    def ledger_path(self) -> Path:
        return self.state_directory / f"{self.run_id}.course.jsonl"

    @property
    def desktop_evidence_path(self) -> Path:
        return self.state_directory / f"{self.run_id}.desktop.jsonl"

    @property
    def runtime_limits(self) -> RuntimeLimits:
        return RuntimeLimits(
            max_steps=self.max_steps,
            max_retries_per_action=self.max_retries_per_action,
            max_consecutive_unchanged=self.max_consecutive_unchanged,
            max_seconds=self.max_seconds,
        )

    @property
    def synthetic_assessment_enabled(self) -> bool:
        return self.synthetic_assessment_asset_root is not None

    @property
    def frame_artifact_directory(self) -> Path:
        return self.state_directory / f"{self.run_id}.frames"

    @property
    def pause_checkpoint_path(self) -> Path:
        return self.state_directory / f"{self.run_id}.pause.json"

    @property
    def synthetic_replay_directory(self) -> Path:
        return self.state_directory / ".synthetic-assessment-replay"


ExecutorFactory = Callable[[GovernedDesktopGateway, str], Executor]


class LocalGUIOrganism:
    """Own one authorization/binding/runtime/ledger lifecycle."""

    def __init__(
        self,
        config: LocalGUIOrganismConfig,
        *,
        gateway: GovernedDesktopGateway,
        observer: Observer,
        planner: LocalPlanner,
        ledger: CourseBenchmarkLedger,
        capability_token: str,
        synthetic_assessment_controller: SyntheticAssessmentRuntimeController | None = None,
        pause_checkpoint_store: HashOnlyPauseCheckpointStore | None = None,
        scorm_runtime_authority: SCORMVisionRuntimeAuthority | None = None,
        executor_factory: ExecutorFactory | None = None,
    ) -> None:
        if getattr(planner, "locality", "") != "local":
            raise OrganismConfigurationError("planner_must_be_local")
        self.config = config
        self.gateway = gateway
        self.observer = observer
        self.planner = planner
        self.ledger = ledger
        self.synthetic_assessment_controller = synthetic_assessment_controller
        self.pause_checkpoint_store = pause_checkpoint_store
        if scorm_runtime_authority is not None and not isinstance(
            scorm_runtime_authority,
            SCORMVisionRuntimeAuthority,
        ):
            raise TypeError(
                "scorm_runtime_authority must be SCORMVisionRuntimeAuthority"
            )
        self.scorm_runtime_authority = scorm_runtime_authority
        if (
            self.config.planner_kind == "scorm_vision"
            and self.scorm_runtime_authority is None
        ):
            raise OrganismConfigurationError("scorm_vision_runtime_authority_incomplete")
        if (
            self.config.planner_kind != "scorm_vision"
            and self.scorm_runtime_authority is not None
        ):
            raise OrganismConfigurationError("scorm_runtime_authority_requires_scorm_vision")
        if self.scorm_runtime_authority is not None:
            if self.config.run_id != self.scorm_runtime_authority.run_authority.run_id:
                raise OrganismConfigurationError("scorm_run_id_authority_mismatch")
            if (
                self.config.scorm_run_authority_sha256
                != self.scorm_runtime_authority.run_authority_sha256
            ):
                raise OrganismConfigurationError("scorm_run_authority_sha256_mismatch")
            if (
                self.config.scorm_control_grant_sha256
                != self.scorm_runtime_authority.control_grant_sha256
            ):
                raise OrganismConfigurationError("scorm_control_grant_sha256_mismatch")
        self._capability_token = str(capability_token or "")
        if executor_factory is not None:
            self._executor_factory = executor_factory
        elif self.config.planner_kind == "scorm_vision":
            assert self.scorm_runtime_authority is not None
            scorm_authority = self.scorm_runtime_authority
            self._executor_factory = lambda governed_gateway, _binding_id: (
                GovernedGatewayExecutor(
                    governed_gateway,
                    binding_supplier=scorm_authority.authorize_binding_id,
                    scorm_authority=scorm_authority,
                )
            )
        else:
            self._executor_factory = lambda governed_gateway, binding_id: (
                GovernedGatewayExecutor(
                    governed_gateway,
                    binding_id=binding_id,
                    assessment_action_authorizer=(
                        self.synthetic_assessment_controller.authorize_action
                        if self.synthetic_assessment_controller is not None
                        else None
                    ),
                )
            )
        self._runtime: LocalGUIRuntime | None = None

    def request_emergency_stop(self, reason: str = "operator_signal") -> None:
        """Stop the runtime and invalidate its lease/binding epoch."""

        if self._runtime is not None:
            self._runtime.request_emergency_stop()
        self.gateway.emergency_stop(reason=reason)

    def _gateway_emergency_active(self) -> bool:
        try:
            return bool(self.gateway.status().get("emergency_stopped"))
        except Exception:
            return True

    def _record_scorm_terminal_authority(self, result: RuntimeResult) -> None:
        """Persist only signed/digest SCORM authority at the terminal boundary."""

        if self.scorm_runtime_authority is None:
            return
        terminal_decision = result.terminal_decision
        action_decision = (
            result.transitions[-1].decision if result.transitions else None
        )
        coherence = (
            terminal_decision.scorm_coherence
            if terminal_decision is not None
            and terminal_decision.scorm_coherence is not None
            else (
                action_decision.scorm_coherence
                if action_decision is not None
                else None
            )
        )
        action_authorization = (
            action_decision.action_authorization
            if action_decision is not None
            else None
        )
        coherence_to_dict = getattr(coherence, "to_dict", None)
        action_audit_dict = getattr(action_authorization, "audit_dict", None)
        self.ledger.append(
            "scorm_terminal_authority",
            {
                "run_authority_sha256": (
                    self.scorm_runtime_authority.run_authority_sha256
                ),
                "control_grant_sha256": (
                    self.scorm_runtime_authority.control_grant_sha256
                ),
                "coherence": (
                    coherence_to_dict() if callable(coherence_to_dict) else None
                ),
                "last_action_authorization": (
                    action_audit_dict() if callable(action_audit_dict) else None
                ),
            },
        )

    def run(self) -> RuntimeResult:
        """Run the bounded loop and always discard live authority on exit."""

        if not self.config.live:
            raise OrganismConfigurationError("live_flag_required_for_gui_run")
        if not self._capability_token:
            raise OrganismConfigurationError("capability_token_environment_required")

        if self.config.planner_kind == "scorm_vision":
            if self.pause_checkpoint_store is None:
                raise OrganismConfigurationError("scorm_vision_pause_store_required")
            if self.pause_checkpoint_store.exists:
                raise OrganismConfigurationError(
                    "pause_receipt_exists_fresh_run_id_required"
                )

        self.ledger.append(
            "runtime_start",
            {
                "runtime_schema": RUNTIME_SCHEMA,
                "authorization_label": self.config.authorization_label,
                "goal_sha256": hashlib.sha256(self.config.goal.encode("utf-8")).hexdigest(),
                "goal_length": len(self.config.goal),
                "window_title_sha256": hashlib.sha256(
                    self.config.expected_window_title.encode("utf-8")
                ).hexdigest(),
                "window_title_length": len(self.config.expected_window_title),
                "model": self.config.model,
                "planner_kind": self.config.planner_kind,
                "planner_timeout_seconds": self.config.planner_timeout_seconds,
                "planner_locality": "local",
                "scorm_authority": {
                    "enabled": self.config.planner_kind == "scorm_vision",
                    "run_authority_sha256": (
                        self.config.scorm_run_authority_sha256 or None
                    ),
                    "control_grant_sha256": (
                        self.config.scorm_control_grant_sha256 or None
                    ),
                    "window_binding_owner": (
                        "governed_scorm_session"
                        if self.scorm_runtime_authority is not None
                        else "organism"
                    ),
                    "hnc_answer_brain": self.config.scorm_hnc_answer_brain,
                },
                "prerequisite_pause": {
                    "continuation_mode": (
                        "new_governed_run_after_owner_prerequisite"
                        if self.config.planner_kind == "scorm_vision"
                        else None
                    ),
                    "same_run_resume_supported": False,
                },
                "allowed_actions": list(self.config.allowed_actions),
                "synthetic_assessment": {
                    "enabled": self.config.synthetic_assessment_enabled,
                    "persona_id": "john-brown-synthetic-v1"
                    if self.config.synthetic_assessment_enabled
                    else None,
                    "mode": "sealed_synthetic_only"
                    if self.config.synthetic_assessment_enabled
                    else None,
                },
                "lease_ttl_seconds": self.config.lease_ttl_seconds,
                "limits": {
                    "max_steps": self.config.max_steps,
                    "max_retries_per_action": self.config.max_retries_per_action,
                    "max_consecutive_unchanged": self.config.max_consecutive_unchanged,
                    "max_seconds": self.config.max_seconds,
                    "gateway_max_actions_per_window": (
                        self.config.gateway_max_actions_per_window
                    ),
                },
            },
        )

        terminal_recorded = False
        gateway_binding: WindowBinding | None = None
        try:
            if self.scorm_runtime_authority is None:
                gateway_binding = self.gateway.bind_target_window(
                    self.config.expected_window_title,
                    expected_process_id=self.config.expected_process_id,
                )
                binding_id = gateway_binding.binding_id
            else:
                try:
                    session_binding = self.scorm_runtime_authority.authorize_binding()
                    binding_id = session_binding.binding_id
                    if (
                        not isinstance(binding_id, str)
                        or not binding_id
                        or binding_id.strip() != binding_id
                        or self.gateway.require_single_target_binding_id() != binding_id
                    ):
                        raise OrganismConfigurationError(
                            "scorm_prebound_binding_not_exact"
                        )
                except OrganismConfigurationError:
                    raise
                except Exception as exc:
                    raise OrganismConfigurationError(
                        "scorm_prebound_binding_not_authorized"
                    ) from exc
            if self.synthetic_assessment_controller is not None:
                if gateway_binding is None:
                    raise OrganismConfigurationError(
                        "synthetic_assessment_gateway_binding_missing"
                    )
                self.synthetic_assessment_controller.activate(gateway_binding)
            self.gateway.authorize_live(
                self._capability_token,
                ttl_seconds=self.config.lease_ttl_seconds,
                subject=ACTOR_ID,
                allowed_actions=self.config.allowed_actions,
            )
            executor = self._executor_factory(self.gateway, binding_id)
            self._runtime = LocalGUIRuntime(
                self.observer,
                self.planner,
                executor,
                limits=self.config.runtime_limits,
                event_sink=self.ledger,
                emergency_stop=self._gateway_emergency_active,
                human_gate_authorizer=(
                    self.synthetic_assessment_controller.authorize_gate
                    if self.synthetic_assessment_controller is not None
                    else None
                ),
                planner_handles_human_gates=self.config.planner_kind == "scorm_vision",
                target_window_mismatch_recovery=(
                    self.scorm_runtime_authority.recover_target_window_mismatch
                    if self.scorm_runtime_authority is not None
                    else None
                ),
            )
            result = self._runtime.run(self.config.goal)
            self._record_scorm_terminal_authority(result)
            self.ledger.record_terminal(
                status=result.status,
                reason=_reason_evidence(result.reason),
                verified_changed_transitions=result.verified_changed_transitions,
                success_predicate=result.success_predicate.to_dict()
                if result.success_predicate is not None
                else None,
            )
            terminal_recorded = True
            if result.status == "paused":
                if (
                    self.pause_checkpoint_store is None
                    or result.final_observation is None
                    or not result.pause_kind
                ):
                    raise OrganismConfigurationError("paused_runtime_missing_checkpoint_context")
                checkpoint = self.pause_checkpoint_store.create(
                    result.final_observation,
                    result.transitions,
                    pause_kind=result.pause_kind,
                )
                result = replace(
                    result,
                    pause_receipt_sha256=checkpoint.checkpoint_sha256,
                )
            return result
        except KeyboardInterrupt:
            self.request_emergency_stop(reason="keyboard_interrupt")
            raise
        except Exception as exc:
            if not terminal_recorded:
                self.ledger.record_terminal(
                    status="startup_or_runtime_error",
                    reason=_reason_evidence(type(exc).__name__),
                    verified_changed_transitions=0,
                )
            raise
        finally:
            self._capability_token = ""
            if self.synthetic_assessment_controller is not None:
                self.synthetic_assessment_controller.close()
            if self.scorm_runtime_authority is None:
                self.gateway.disarm(reason="organism_run_finally")
            else:
                self.gateway.revoke_live_authorization(
                    reason="organism_scorm_run_finally"
                )


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001, ANN201
        return None


def probe_local_ollama(
    *,
    model: str,
    endpoint: str,
    timeout_seconds: float = 5.0,
) -> Mapping[str, object]:
    """Verify a model exists through a proxy-free loopback-only GET."""

    planner = LocalOllamaPlanner(
        model=model,
        endpoint=endpoint,
        timeout_seconds=max(1.0, min(float(timeout_seconds), 300.0)),
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    request = urllib.request.Request(
        f"{planner.endpoint}/api/tags",
        headers={"Accept": "application/json"},
        method="GET",
    )
    try:
        with opener.open(request, timeout=timeout_seconds) as response:
            raw = response.read(1024 * 1024 + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"ok": False, "reason": f"loopback_ollama_unavailable:{type(exc).__name__}"}
    if len(raw) > 1024 * 1024:
        return {"ok": False, "reason": "loopback_ollama_response_too_large"}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"ok": False, "reason": "loopback_ollama_invalid_json"}
    models = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(models, list):
        return {"ok": False, "reason": "loopback_ollama_models_missing"}
    names = {
        str(item.get("name") or item.get("model") or "")
        for item in models
        if isinstance(item, dict)
    }
    return {
        "ok": model in names,
        "reason": "ready" if model in names else "configured_model_not_installed",
        "model": model,
        "available_model_count": len({name for name in names if name}),
        "endpoint": planner.endpoint,
    }


def preflight_local_gui(
    *,
    model: str,
    endpoint: str,
    tesseract_executable: str | Path | None = None,
    ollama_probe: Callable[..., Mapping[str, object]] = probe_local_ollama,
) -> dict[str, object]:
    """Check local dependencies without observing or mutating the desktop."""

    checks: dict[str, object] = {
        "schema_version": "aureon-local-gui-preflight-v1",
        "actor": ACTOR_ID,
        "desktop_touched": False,
        "cloud_used": False,
    }
    try:
        tesseract_path = discover_tesseract_executable(tesseract_executable)
        checks["tesseract"] = {
            "ok": True,
            "path": str(tesseract_path),
        }
    except Exception as exc:
        checks["tesseract"] = {
            "ok": False,
            "reason": f"local_tesseract_unavailable:{type(exc).__name__}",
        }

    checks["pyautogui"] = {
        "ok": importlib.util.find_spec("pyautogui") is not None,
        "imported": False,
    }
    try:
        checks["ollama"] = dict(ollama_probe(model=model, endpoint=endpoint))
    except Exception as exc:
        checks["ollama"] = {
            "ok": False,
            "reason": f"loopback_ollama_probe_failed:{type(exc).__name__}",
        }
    def check_passed(name: str) -> bool:
        item = checks.get(name)
        return isinstance(item, Mapping) and item.get("ok") is True

    checks["ok"] = all(check_passed(name) for name in ("tesseract", "pyautogui", "ollama"))
    return checks


def build_local_organism(
    config: LocalGUIOrganismConfig,
    *,
    capability_token: str,
    synthetic_assessment_secret: bytes | None = None,
    tesseract_executable: str | Path | None = None,
    scorm_runtime_authority: SCORMVisionRuntimeAuthority | None = None,
) -> LocalGUIOrganism:
    """Construct the concrete local-only runtime without starting it."""

    config.state_directory.mkdir(parents=True, exist_ok=True)
    gateway = get_governed_desktop_gateway(
        evidence_path=config.desktop_evidence_path,
        max_actions_per_window=config.gateway_max_actions_per_window,
    )
    build_id = _build_fingerprint()
    ledger = CourseBenchmarkLedger(
        config.ledger_path,
        actor=ACTOR_ID,
        runtime_id=RUNTIME_SCHEMA,
        build_id=build_id,
        run_id=config.run_id,
    )
    assessment_controller: SyntheticAssessmentRuntimeController | None = None
    if config.synthetic_assessment_enabled:
        if synthetic_assessment_secret is None:
            raise OrganismConfigurationError("synthetic_assessment_secret_environment_required")
        assert config.synthetic_assessment_asset_root is not None
        assert config.synthetic_assessment_loopback_port is not None
        assert config.synthetic_assessment_server_pid is not None
        assessment_controller = SyntheticAssessmentRuntimeController(
            SyntheticAssessmentRuntimeConfig(
                asset_root=config.synthetic_assessment_asset_root,
                loopback_port=config.synthetic_assessment_loopback_port,
                server_pid=config.synthetic_assessment_server_pid,
                run_id=config.run_id,
                nonce=config.synthetic_assessment_nonce,
                ttl_seconds=config.lease_ttl_seconds,
                allowed_actions=tuple(
                    _GATEWAY_TO_RUNTIME_ASSESSMENT_ACTION[action]
                    for action in config.allowed_actions
                    if action in _GATEWAY_TO_RUNTIME_ASSESSMENT_ACTION
                    and _GATEWAY_TO_RUNTIME_ASSESSMENT_ACTION[action]
                    in SUPPORTED_ASSESSMENT_ACTIONS
                ),
                max_actions=config.synthetic_assessment_max_actions,
                replay_directory=config.synthetic_replay_directory,
            ),
            secret=synthetic_assessment_secret,
            receipt_sink=ledger,
        )
    artifact_store = FrameArtifactStore(config.frame_artifact_directory)
    if (
        scorm_runtime_authority is not None
        and not isinstance(scorm_runtime_authority, SCORMVisionRuntimeAuthority)
    ):
        raise TypeError("scorm_runtime_authority must be SCORMVisionRuntimeAuthority")
    if config.planner_kind == "scorm_vision" and scorm_runtime_authority is None:
        raise OrganismConfigurationError("scorm_vision_window_session_authority_required")
    if config.planner_kind != "scorm_vision" and scorm_runtime_authority is not None:
        raise OrganismConfigurationError("scorm_runtime_authority_requires_scorm_vision")
    if scorm_runtime_authority is not None:
        if config.run_id != scorm_runtime_authority.run_authority.run_id:
            raise OrganismConfigurationError("scorm_run_id_authority_mismatch")
        if (
            config.scorm_run_authority_sha256
            != scorm_runtime_authority.run_authority_sha256
        ):
            raise OrganismConfigurationError("scorm_run_authority_sha256_mismatch")
        if (
            config.scorm_control_grant_sha256
            != scorm_runtime_authority.control_grant_sha256
        ):
            raise OrganismConfigurationError("scorm_control_grant_sha256_mismatch")
        leased_runtime_actions = {
            _GATEWAY_TO_RUNTIME_ACTION[action] for action in config.allowed_actions
        }
        if not leased_runtime_actions.issubset(
            set(scorm_runtime_authority.run_authority.allowed_actions)
        ):
            raise OrganismConfigurationError("scorm_run_authority_action_scope_incomplete")
    binding_supplier = (
        scorm_runtime_authority.authorize_binding_id
        if scorm_runtime_authority is not None
        else None
    )
    observer = LocalGUIObserver(
        GatewayScreenshotBackend(
            gateway,
            binding_supplier=binding_supplier,
        ),
        TesseractCLIBackend(
            executable=tesseract_executable,
            crop_to_bound_window=config.planner_kind in {"courseops", "scorm_vision"},
            page_segmentation_modes=(
                (None, 6) if config.planner_kind == "scorm_vision" else None
            ),
        ),
        vision_hook=CourseOps21VisionHook() if config.planner_kind == "courseops" else None,
        stability_fingerprint=(
            CourseOps21StabilityFingerprint()
            if config.planner_kind == "courseops"
            else SCORMPlayerStabilityFingerprint()
            if config.planner_kind == "scorm_vision"
            else None
        ),
        artifact_store=artifact_store,
    )
    planner: LocalPlanner
    if config.planner_kind == "fixture":
        planner = LocalFixturePlanner(
            LOCAL_FIXTURE_MANIFEST,
            expected_sha256=LOCAL_FIXTURE_MANIFEST_SHA256,
        )
    elif config.planner_kind == "courseops":
        planner = CourseOps21Planner()
    elif config.planner_kind == "scorm_vision":
        assert scorm_runtime_authority is not None
        answer_brain = (
            SwitchboardHNCAnswerBrain(
                receipt_sink=ledger,
                timeout_seconds=min(240.0, config.planner_timeout_seconds),
            )
            if config.scorm_hnc_answer_brain
            else None
        )
        planner = LocalOllamaVisionPlanner(
            model=config.model,
            endpoint=config.endpoint,
            timeout_seconds=config.planner_timeout_seconds,
            image_source=FrameArtifactPNGSource(config.frame_artifact_directory),
            scorm_authority=scorm_runtime_authority,
            answer_brain=answer_brain,
        )
    else:
        planner = LocalOllamaPlanner(
            model=config.model,
            endpoint=config.endpoint,
            timeout_seconds=config.planner_timeout_seconds,
            synthetic_assessment_authorizer=(
                assessment_controller.authorize_observation
                if assessment_controller is not None
                else None
            ),
        )
    pause_checkpoint_store = None
    if config.planner_kind == "scorm_vision":
        pause_checkpoint_store = HashOnlyPauseCheckpointStore(
            config.pause_checkpoint_path,
            run_id=config.run_id,
            build_id=build_id,
            goal=config.goal,
            run_authority_sha256=config.scorm_run_authority_sha256,
            control_grant_sha256=config.scorm_control_grant_sha256,
        )
    return LocalGUIOrganism(
        config,
        gateway=gateway,
        observer=observer,
        planner=planner,
        ledger=ledger,
        capability_token=capability_token,
        synthetic_assessment_controller=assessment_controller,
        pause_checkpoint_store=pause_checkpoint_store,
        scorm_runtime_authority=scorm_runtime_authority,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Aureon's governed, fully local GUI organism",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    preflight = subparsers.add_parser(
        "preflight",
        help="check local dependencies without touching the desktop",
    )
    preflight.add_argument("--model", default="llama3:latest")
    preflight.add_argument("--endpoint", default="http://127.0.0.1:11434")
    preflight.add_argument("--tesseract")

    run = subparsers.add_parser("run", help="run one bounded exact-window benchmark")
    run.add_argument("--goal", required=True)
    run.add_argument("--window-title", required=True)
    run.add_argument("--process-id", type=int)
    run.add_argument("--model", default="llama3:latest")
    run.add_argument("--endpoint", default="http://127.0.0.1:11434")
    run.add_argument(
        "--planner",
        choices=("ollama", "fixture", "courseops", "scorm_vision"),
        default="ollama",
    )
    run.add_argument("--planner-timeout", type=float, default=60.0)
    run.add_argument(
        "--allow-action",
        action="append",
        choices=sorted(MUTATING_ACTIONS),
        required=True,
        help="repeat for each gateway action in the least-privilege lease",
    )
    run.add_argument(
        "--authorization-label",
        choices=sorted(AUTHORIZED_RUNTIME_LABELS),
        default="sandbox_test",
    )
    run.add_argument("--lease-ttl", type=float, default=3600.0)
    run.add_argument("--max-steps", type=int, default=50)
    run.add_argument("--max-retries", type=int, default=2)
    run.add_argument("--max-unchanged", type=int, default=4)
    run.add_argument("--max-seconds", type=float, default=900.0)
    run.add_argument("--gateway-actions-per-minute", type=int, default=60)
    run.add_argument("--run-id")
    run.add_argument("--state-directory", type=Path, default=DEFAULT_STATE_DIRECTORY)
    run.add_argument("--tesseract")
    run.add_argument("--synthetic-suite-root", type=Path)
    run.add_argument("--synthetic-loopback-port", type=int)
    run.add_argument("--synthetic-server-pid", type=int)
    run.add_argument("--synthetic-nonce")
    run.add_argument("--synthetic-max-actions", type=int, default=4096)
    run.add_argument("--scorm-run-authority-sha256", default="")
    run.add_argument("--scorm-control-grant-sha256", default="")
    run.add_argument(
        "--live",
        action="store_true",
        help=f"required; consumes a one-time token from {CAPABILITY_TOKEN_ENV}",
    )
    return parser


def _install_stop_handlers(organism: LocalGUIOrganism) -> list[tuple[int, Any]]:
    prior: list[tuple[int, Any]] = []

    def handle_stop(signum, _frame) -> None:  # noqa: ANN001
        organism.request_emergency_stop(reason=f"signal_{signum}")

    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            prior.append((signum, signal.getsignal(signum)))
            signal.signal(signum, handle_stop)
        except (OSError, RuntimeError, ValueError):
            continue
    return prior


def _restore_stop_handlers(prior: Sequence[tuple[int, Any]]) -> None:
    for signum, handler in prior:
        try:
            signal.signal(signum, handler)
        except (OSError, RuntimeError, ValueError):
            continue


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "preflight":
        preflight_result = preflight_local_gui(
            model=args.model,
            endpoint=args.endpoint,
            tesseract_executable=args.tesseract,
        )
        print(json.dumps(preflight_result, sort_keys=True))
        return 0 if preflight_result.get("ok") is True else 2

    config = LocalGUIOrganismConfig(
        goal=args.goal,
        expected_window_title=args.window_title,
        allowed_actions=tuple(args.allow_action),
        expected_process_id=args.process_id,
        model=args.model,
        endpoint=args.endpoint,
        planner_kind=args.planner,
        planner_timeout_seconds=args.planner_timeout,
        authorization_label=args.authorization_label,
        live=args.live,
        lease_ttl_seconds=args.lease_ttl,
        max_steps=args.max_steps,
        max_retries_per_action=args.max_retries,
        max_consecutive_unchanged=args.max_unchanged,
        max_seconds=args.max_seconds,
        gateway_max_actions_per_window=args.gateway_actions_per_minute,
        run_id=args.run_id or uuid.uuid4().hex,
        state_directory=args.state_directory,
        synthetic_assessment_asset_root=args.synthetic_suite_root,
        synthetic_assessment_loopback_port=args.synthetic_loopback_port,
        synthetic_assessment_server_pid=args.synthetic_server_pid,
        synthetic_assessment_nonce=args.synthetic_nonce or "",
        synthetic_assessment_max_actions=args.synthetic_max_actions,
        scorm_run_authority_sha256=args.scorm_run_authority_sha256,
        scorm_control_grant_sha256=args.scorm_control_grant_sha256,
    )
    synthetic_secret: bytes | None = None
    if config.synthetic_assessment_enabled:
        try:
            synthetic_secret = secret_from_environment(
                SYNTHETIC_ASSESSMENT_SECRET_ENV,
                os.environ,
            )
        except ValueError as exc:
            raise OrganismConfigurationError(str(exc)) from exc
        os.environ.pop(SYNTHETIC_ASSESSMENT_SECRET_ENV, None)
    organism = build_local_organism(
        config,
        capability_token=os.environ.get(CAPABILITY_TOKEN_ENV, ""),
        synthetic_assessment_secret=synthetic_secret,
        tesseract_executable=args.tesseract,
    )
    prior = _install_stop_handlers(organism)
    try:
        runtime_result = organism.run()
    finally:
        _restore_stop_handlers(prior)
    summary = {
        "schema_version": RUNTIME_SCHEMA,
        "run_id": config.run_id,
        "actor": ACTOR_ID,
        "status": runtime_result.status,
        "success": runtime_result.success,
        "human_gate": runtime_result.human_gate,
        "pause_kind": runtime_result.pause_kind,
        "pause_receipt_sha256": runtime_result.pause_receipt_sha256 or None,
        "continuation_mode": (
            "new_governed_run_after_owner_prerequisite"
            if runtime_result.status == "paused"
            else None
        ),
        "action_count": runtime_result.action_count,
        "verified_changed_transitions": runtime_result.verified_changed_transitions,
        "ledger_path": str(config.ledger_path),
        "desktop_evidence_path": str(config.desktop_evidence_path),
        "frame_artifact_directory": str(config.frame_artifact_directory),
        "synthetic_assessment": config.synthetic_assessment_enabled,
        "synthetic_assessment_grant_sha256": (
            organism.synthetic_assessment_controller.grant_sha256
            if organism.synthetic_assessment_controller is not None
            else ""
        ),
        "scorm_run_authority_sha256": config.scorm_run_authority_sha256 or None,
        "scorm_control_grant_sha256": config.scorm_control_grant_sha256 or None,
        "cloud_used": False,
    }
    print(json.dumps(summary, sort_keys=True))
    if runtime_result.success:
        return 0
    if runtime_result.status == "human_required":
        return 3
    return 4


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except OrganismConfigurationError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        raise SystemExit(2) from None


__all__ = [
    "ACTOR_ID",
    "CAPABILITY_TOKEN_ENV",
    "SYNTHETIC_ASSESSMENT_SECRET_ENV",
    "DEFAULT_STATE_DIRECTORY",
    "LocalGUIOrganism",
    "LocalGUIOrganismConfig",
    "OrganismConfigurationError",
    "build_local_organism",
    "main",
    "preflight_local_gui",
    "probe_local_ollama",
]
