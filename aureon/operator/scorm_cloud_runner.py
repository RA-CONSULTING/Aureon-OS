"""Concrete local SCORM Cloud browser/operator composition.

The launch URL and all signing/capability material are consumed from process
environment variables, never command-line arguments or evidence.  Importing
this module is inert.  Edge is launched only by :func:`run_scorm_cloud` after
an explicit live configuration and local dependency preflight have succeeded.
An owner prerequisite produces a hash-only pause receipt and closes the exact
owned launch; continuation is always a new governed run after the owner has
satisfied the prerequisite in the owner-controlled profile.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import unicodedata
import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable, Mapping, Protocol, Sequence, cast

from aureon.autonomous.aureon_governed_desktop_gateway import (
    MUTATING_ACTIONS,
    GovernedDesktopGateway,
    get_governed_desktop_gateway,
)
from aureon.operator.hnc_scorm_coherence import (
    OWNER_ATTESTATION_REQUIRED,
    OWNER_BENCHMARK_ASSERTED,
    READY_FOR_INTENT,
    RESUMABLE_PAUSE,
    HNCScormCoherenceGate,
    SCORMActionDecision,
    SCORMActionReceipt,
    SCORMActionReplayLedger,
    SCORMFrameEvidence,
    SCORMOwnerBenchmarkLaunchAuthority,
    SCORMPreflightDecision,
    SCORMProviderContextEvidence,
    SCORMRunAuthority,
    canonical_synthetic_persona_sha256,
    canonical_visible_evidence_sha256,
    canonical_visible_text_sha256,
)
from aureon.operator.local_gui_observer import ScreenObservation
from aureon.operator.local_gui_organism import (
    CAPABILITY_TOKEN_ENV,
    LocalGUIOrganismConfig,
    build_local_organism,
    preflight_local_gui,
)
from aureon.operator.local_gui_pause import HashOnlyPauseCheckpointStore
from aureon.operator.local_gui_runtime import (
    PAUSE_KINDS,
    SEMANTIC_SUCCESS_PREDICATES,
    ActionResult,
    GuiAction,
    ObservationPredicate,
    PlannerDecision,
    RuntimeResult,
    RuntimeTransition,
    evaluate_predicate,
)
from aureon.operator.local_gui_scorm_authority import (
    SCORMActionAuthorization,
    SCORMObservationAuthorization,
    SCORMVisionRuntimeAuthority,
)
from aureon.operator.scorm_cloud_evidence import (
    SCORMOwnerBenchmarkEvidenceAuthorizer,
    Win32EdgeNativeTargetProbe,
    Win32EdgeNativeURLProbe,
    owner_benchmark_run_manifest_sha256,
)
from aureon.operator.scorm_cloud_session import (
    PROFILE_ISOLATED,
    PROFILE_OWNER_EXISTING,
    ActiveSCORMCloudSession,
    EdgeProfileSpec,
    PsutilProcessInspector,
    SCORMCloudLaunchPlan,
    SCORMCloudSessionRunner,
    SCORMEvidenceLedger,
    SubprocessEdgeLauncher,
    Win32EdgeWindowController,
    build_scorm_cloud_edge_plan,
)

SCORM_LAUNCH_URL_ENV = "AUREON_SCORM_LAUNCH_URL"
SCORM_SESSION_SIGNING_SECRET_ENV = "AUREON_SCORM_SESSION_SIGNING_SECRET"
SCORM_HNC_SIGNING_SECRET_ENV = "AUREON_SCORM_HNC_SIGNING_SECRET"
SCORM_OWNER_BENCHMARK_SIGNING_SECRET_ENV = "AUREON_SCORM_OWNER_BENCHMARK_SIGNING_SECRET"
SCORM_OWNER_BENCHMARK_ISSUER = "aureon-owner-benchmark-control"
SCORM_OWNER_BENCHMARK_KEY_ID = "aureon-owner-benchmark-control-v1"
SCORM_SYNTHETIC_PERSONA_ID = "john-brown-synthetic-v1"
SCORM_RUNNER_SCHEMA = "aureon-scorm-cloud-runner-v1"
DEFAULT_TITLE_REGEX = (
    r"^(?:(?:.+ - )?SCORM Cloud(?: - .+)?|"
    r"ERROR: The request could not be satisfied|Access Denied|403 Forbidden)"
    r" - Microsoft Edge$"
)
DEFAULT_GOAL = (
    "Navigate the exact owner-authorized synthetic-persona SCORM benchmark "
    "using only visible local browser controls, and pause at every protected "
    "prerequisite."
)
DEFAULT_GATEWAY_ACTIONS = ("click", "move", "press", "scroll", "type")
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
_SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_MIN_SECRET_BYTES = 32
_RUNTIME_STATUSES = frozenset(
    {
        "aborted",
        "action_rejected",
        "completed",
        "completion_rejected",
        "emergency_stopped",
        "evidence_error",
        "human_required",
        "invalid_action",
        "max_steps",
        "max_time",
        "observer_error",
        "paused",
        "planner_error",
        "post_dispatch_verification_failed",
        "retry_exhausted",
        "stalled",
        "unstable_initial_frame",
        "unstable_post_action_frame",
    }
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
FRESH_RUN_CONTINUATION = "new_governed_run_after_owner_prerequisite"


class SCORMCloudRunnerError(RuntimeError):
    """Stable, non-sensitive composition failure."""

    def __init__(self, code: str) -> None:
        self.code = str(code)
        super().__init__(self.code)


@dataclass(frozen=True)
class SCORMCloudRunConfig:
    """Validated side-effect-free inputs for one bounded live run."""

    edge_executable: Path
    profile: EdgeProfileSpec
    run_id: str
    state_directory: Path
    model: str = "qwen3:8b"
    endpoint: str = "http://127.0.0.1:11434"
    expected_initial_title_regex: str = DEFAULT_TITLE_REGEX
    allowed_title_regex: str = DEFAULT_TITLE_REGEX
    goal: str = DEFAULT_GOAL
    allowed_gateway_actions: tuple[str, ...] = DEFAULT_GATEWAY_ACTIONS
    planner_timeout_seconds: float = 60.0
    lease_ttl_seconds: float = 7_200.0
    max_steps: int = 500
    max_retries_per_action: int = 2
    max_consecutive_unchanged: int = 4
    max_seconds: float = 3_600.0
    gateway_max_actions_per_window: int = 60
    max_handoffs: int = 200
    live: bool = False
    tesseract_executable: Path | None = None
    attach_existing: bool = False
    hnc_answer_brain: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.profile, EdgeProfileSpec):
            raise SCORMCloudRunnerError("edge_profile_required")
        if not isinstance(self.run_id, str) or _SAFE_RUN_ID.fullmatch(self.run_id) is None:
            raise SCORMCloudRunnerError("run_id_invalid")
        actions = tuple(dict.fromkeys(self.allowed_gateway_actions))
        if not actions or not set(actions).issubset(MUTATING_ACTIONS):
            raise SCORMCloudRunnerError("allowed_gateway_actions_invalid")
        if self.profile.mode == PROFILE_OWNER_EXISTING and (self.profile.owner_edge_process_id is None):
            raise SCORMCloudRunnerError("owner_existing_profile_requires_edge_process_id")
        if self.profile.mode == PROFILE_ISOLATED and (self.profile.owner_edge_process_id is not None):
            raise SCORMCloudRunnerError("isolated_profile_forbids_edge_process_id")
        state = Path(self.state_directory).expanduser()
        if state.is_symlink() or str(state).startswith("\\\\"):
            raise SCORMCloudRunnerError("state_directory_must_be_local_regular_path")
        resolved_state = state.resolve(strict=False)
        if resolved_state.parent == resolved_state:
            raise SCORMCloudRunnerError("state_directory_too_broad")
        if not isinstance(self.live, bool):
            raise SCORMCloudRunnerError("live_flag_invalid")
        if not isinstance(self.attach_existing, bool):
            raise SCORMCloudRunnerError("attach_existing_invalid")
        if not isinstance(self.hnc_answer_brain, bool):
            raise SCORMCloudRunnerError("hnc_answer_brain_invalid")
        if self.attach_existing and self.profile.mode != PROFILE_OWNER_EXISTING:
            raise SCORMCloudRunnerError("attach_existing_requires_owner_profile")
        object.__setattr__(self, "edge_executable", Path(self.edge_executable))
        object.__setattr__(self, "state_directory", resolved_state)
        object.__setattr__(self, "allowed_gateway_actions", actions)
        if self.tesseract_executable is not None:
            object.__setattr__(
                self,
                "tesseract_executable",
                Path(self.tesseract_executable),
            )

    @property
    def scorm_evidence_path(self) -> Path:
        return self.state_directory / f"{self.run_id}.scorm.jsonl"

    @property
    def desktop_evidence_path(self) -> Path:
        return self.state_directory / f"{self.run_id}.desktop.jsonl"

    @property
    def replay_directory(self) -> Path:
        return self.state_directory / f"{self.run_id}.scorm-replay"

    @property
    def runtime_actions(self) -> tuple[str, ...]:
        return tuple(
            sorted({"wait", *(_GATEWAY_TO_RUNTIME_ACTION[item] for item in self.allowed_gateway_actions)})
        )


@dataclass(frozen=True)
class SCORMCloudRunResult:
    run_id: str
    status: str
    success: bool
    human_gate: str | None
    pause_kind: str | None
    pause_receipt_sha256: str | None
    continuation_mode: str | None
    action_count: int
    verified_changed_transitions: int
    run_authority_sha256: str
    control_grant_sha256: str
    scorm_evidence_path: str
    desktop_evidence_path: str
    course_ledger_path: str
    frame_artifact_directory: str
    schema_version: str = SCORM_RUNNER_SCHEMA

    def to_dict(self) -> dict[str, object]:
        return dict(self.__dict__)


class _SessionStarter(Protocol):
    def start(self, plan: SCORMCloudLaunchPlan) -> ActiveSCORMCloudSession: ...

    def attach(self, plan: SCORMCloudLaunchPlan) -> ActiveSCORMCloudSession: ...


@dataclass(frozen=True)
class _NativeRuntime:
    session_runner: _SessionStarter
    native_url_probe: Win32EdgeNativeURLProbe
    native_target_probe: Win32EdgeNativeTargetProbe


PreflightProbe = Callable[[SCORMCloudRunConfig], Mapping[str, object]]
GatewayFactory = Callable[[SCORMCloudRunConfig], GovernedDesktopGateway]
NativeRuntimeFactory = Callable[
    [GovernedDesktopGateway, SCORMEvidenceLedger, bytes, Callable[[], datetime]],
    _NativeRuntime,
]
OrganismBuilder = Callable[..., object]


def _production_preflight(config: SCORMCloudRunConfig) -> Mapping[str, object]:
    result = dict(
        preflight_local_gui(
            model=config.model,
            endpoint=config.endpoint,
            tesseract_executable=config.tesseract_executable,
        )
    )
    native_dependencies = {
        name: importlib.util.find_spec(module_name) is not None
        for name, module_name in (
            ("comtypes", "comtypes"),
            ("pillow", "PIL"),
            ("psutil", "psutil"),
        )
    }
    native_dependencies["windows"] = sys.platform == "win32"
    native_check: dict[str, object] = {
        "ok": all(native_dependencies.values()),
        "checks": native_dependencies,
    }
    result["scorm_native"] = native_check
    result["ok"] = result.get("ok") is True and native_check["ok"] is True
    return result


def _production_gateway(config: SCORMCloudRunConfig) -> GovernedDesktopGateway:
    return get_governed_desktop_gateway(
        evidence_path=config.desktop_evidence_path,
        max_actions_per_window=config.gateway_max_actions_per_window,
    )


def _production_native_runtime(
    gateway: GovernedDesktopGateway,
    ledger: SCORMEvidenceLedger,
    session_secret: bytes,
    utc_now: Callable[[], datetime],
) -> _NativeRuntime:
    inspector = PsutilProcessInspector()
    controller = Win32EdgeWindowController()
    return _NativeRuntime(
        session_runner=SCORMCloudSessionRunner(
            launcher=SubprocessEdgeLauncher(),
            window_controller=controller,
            process_inspector=inspector,
            gateway=gateway,
            ledger=ledger,
            signing_secret=session_secret,
            utc_now=utc_now,
        ),
        native_url_probe=Win32EdgeNativeURLProbe(utc_now=utc_now),
        native_target_probe=Win32EdgeNativeTargetProbe(
            process_inspector=inspector,
        ),
    )


@dataclass(frozen=True)
class SCORMCloudRuntimeDependencies:
    """Hermetic construction seam; production defaults are fully concrete."""

    preflight_probe: PreflightProbe = _production_preflight
    gateway_factory: GatewayFactory = _production_gateway
    native_runtime_factory: NativeRuntimeFactory = _production_native_runtime
    organism_builder: OrganismBuilder = build_local_organism
    utc_now: Callable[[], datetime] = lambda: datetime.now(UTC)


def _prelaunch_organism_config(config: SCORMCloudRunConfig) -> LocalGUIOrganismConfig:
    """Validate every organism field before Edge can be launched."""

    return LocalGUIOrganismConfig(
        goal=config.goal,
        expected_window_title="prelaunch-scorm-window",
        expected_process_id=None,
        allowed_actions=config.allowed_gateway_actions,
        model=config.model,
        endpoint=config.endpoint,
        planner_kind="scorm_vision",
        planner_timeout_seconds=config.planner_timeout_seconds,
        authorization_label="owner_benchmark_test",
        live=config.live,
        lease_ttl_seconds=config.lease_ttl_seconds,
        max_steps=config.max_steps,
        max_retries_per_action=config.max_retries_per_action,
        max_consecutive_unchanged=config.max_consecutive_unchanged,
        max_seconds=config.max_seconds,
        gateway_max_actions_per_window=config.gateway_max_actions_per_window,
        run_id=config.run_id,
        state_directory=config.state_directory,
        scorm_run_authority_sha256="0" * 64,
        scorm_control_grant_sha256="0" * 64,
        scorm_hnc_answer_brain=config.hnc_answer_brain,
    )


def _require_secret(name: str, value: bytes) -> bytes:
    if not isinstance(value, bytes) or len(value) < _MIN_SECRET_BYTES:
        raise SCORMCloudRunnerError(f"{name}_invalid")
    return value


def _runtime_projection(
    runtime_result: object,
    *,
    run_authority: SCORMRunAuthority,
    active_session: ActiveSCORMCloudSession,
    replay_ledger: SCORMActionReplayLedger,
    pause_checkpoint_store: HashOnlyPauseCheckpointStore,
    pause_checkpoint_path: Path,
) -> tuple[str, bool, str | None, str | None, str | None, int, int]:
    if not isinstance(runtime_result, RuntimeResult) or type(runtime_result) is not RuntimeResult:
        raise SCORMCloudRunnerError("runtime_result_type_invalid")
    result = runtime_result
    status = result.status
    success = result.success
    action_count = result.action_count
    verified = result.verified_changed_transitions
    human_gate = result.human_gate
    pause_kind = result.pause_kind
    pause_receipt = result.pause_receipt_sha256
    reason = result.reason
    transitions = result.transitions
    terminal_decision = result.terminal_decision
    if not isinstance(reason, str) or not reason.strip():
        raise SCORMCloudRunnerError("runtime_result_reason_invalid")
    if status not in _RUNTIME_STATUSES or not isinstance(status, str):
        raise SCORMCloudRunnerError("runtime_result_status_invalid")
    if not isinstance(success, bool) or success != (status == "completed"):
        raise SCORMCloudRunnerError("runtime_result_success_invalid")
    if (
        not isinstance(action_count, int)
        or isinstance(action_count, bool)
        or action_count < 0
        or not isinstance(verified, int)
        or isinstance(verified, bool)
        or verified < 0
        or verified > action_count
    ):
        raise SCORMCloudRunnerError("runtime_result_counts_invalid")
    if (
        type(transitions) is not tuple
        or len(transitions) != action_count
        or any(type(transition) is not RuntimeTransition for transition in transitions)
    ):
        raise SCORMCloudRunnerError("runtime_result_transition_evidence_invalid")
    if (
        type(run_authority) is not SCORMRunAuthority
        or type(active_session) is not ActiveSCORMCloudSession
        or type(replay_ledger) is not SCORMActionReplayLedger
        or type(pause_checkpoint_store) is not HashOnlyPauseCheckpointStore
        or not isinstance(pause_checkpoint_path, Path)
    ):
        raise SCORMCloudRunnerError("runtime_projection_context_invalid")
    expected_pause_path = pause_checkpoint_path.resolve()
    if pause_checkpoint_store.path != expected_pause_path or pause_checkpoint_store.path.is_symlink():
        raise SCORMCloudRunnerError("runtime_projection_context_invalid")
    plan = active_session.plan
    expected_origin = "https://cloud.scorm.com"
    expected_manifest_sha256 = owner_benchmark_run_manifest_sha256(active_session)
    current_run_context = (
        plan.session_id,
        expected_manifest_sha256,
        run_authority.run_authority_sha256,
        expected_origin,
        plan.url_sha256,
        plan.plan_sha256,
        active_session.control_grant_sha256,
    )
    authority_context = (
        run_authority.run_id,
        run_authority.run_manifest_sha256,
        run_authority.run_authority_sha256,
        run_authority.allowed_origin,
        run_authority.launch_url_sha256,
        run_authority.launch_plan_sha256,
        run_authority.control_grant_sha256,
    )
    if authority_context != current_run_context:
        raise SCORMCloudRunnerError("runtime_projection_context_invalid")
    try:
        active_binding = active_session.authorize_binding()
    except Exception as exc:  # noqa: BLE001 - governed session boundary
        raise SCORMCloudRunnerError("runtime_projection_context_invalid") from exc
    if active_binding.session_id != plan.session_id:
        raise SCORMCloudRunnerError("runtime_projection_context_invalid")
    expected_window_context_sha256 = hashlib.sha256(
        json.dumps(
            {
                "active_session_id": plan.session_id,
                "window_binding_id": active_binding.binding_id,
                "window_generation": active_binding.generation,
                "window_identity_sha256": active_binding.window_sha256,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    expected_persona_sha256 = canonical_synthetic_persona_sha256(SCORM_SYNTHETIC_PERSONA_ID)

    def terminal_frame_context(
        observation: ScreenObservation | None,
    ) -> tuple[str, str, str, str, str] | None:
        if observation is None or type(observation) is not ScreenObservation:
            return None
        obs = cast(ScreenObservation, observation)
        window = active_binding.window
        rect = obs.window_rect
        if (
            rect is None
            or obs.window_handle != window.handle
            or obs.window_process_id != window.process_id
            or obs.window_title_sha256 != hashlib.sha256(window.title.encode("utf-8")).hexdigest()
            or (rect.left, rect.top, rect.width, rect.height)
            != (window.left, window.top, window.width, window.height)
            or obs.dpi_x is None
            or obs.dpi_y is None
        ):
            return None
        visible_text = unicodedata.normalize(
            "NFC",
            f"{obs.ocr_text}\n{obs.vision_text}".strip(),
        )
        try:
            visible_evidence_sha256 = canonical_visible_evidence_sha256(obs)
            visible_text_sha256 = canonical_visible_text_sha256(visible_text)
        except (TypeError, ValueError):
            return None
        return (
            obs.observation_id,
            obs.screenshot_sha256,
            visible_evidence_sha256,
            visible_text_sha256,
            expected_window_context_sha256,
        )

    def terminal_preflight_matches(
        coherence: object,
        observation: ScreenObservation | None,
        *,
        allowed_kinds: frozenset[str],
    ) -> bool:
        frame_context = terminal_frame_context(observation)
        if not isinstance(coherence, SCORMPreflightDecision) or frame_context is None:
            return False
        coherence_decision = cast(SCORMPreflightDecision, coherence)
        return (
            coherence_decision.kind in allowed_kinds
            and coherence_decision.run_authority_sha256
            == run_authority.run_authority_sha256
            and coherence_decision.provenance == OWNER_BENCHMARK_ASSERTED
            and coherence_decision.synthetic_persona_sha256
            == expected_persona_sha256
            and (
                coherence_decision.source_observation_sha256,
                coherence_decision.source_screenshot_sha256,
                coherence_decision.visible_evidence_sha256,
                coherence_decision.visible_text_sha256,
                coherence.window_context_sha256,
            )
            == frame_context
        )

    def terminal_action_matches(
        coherence: object,
        observation: ScreenObservation | None,
        *,
        expected_kind: str,
    ) -> bool:
        frame_context = terminal_frame_context(observation)
        if not isinstance(coherence, SCORMActionDecision) or frame_context is None:
            return False
        coherence_decision = cast(SCORMActionDecision, coherence)
        return (
            coherence_decision.kind == expected_kind
            and coherence_decision.run_authority_sha256 == run_authority.run_authority_sha256
            and coherence_decision.provenance == OWNER_BENCHMARK_ASSERTED
            and coherence_decision.synthetic_persona_sha256 == expected_persona_sha256
            and coherence_decision.source_observation_sha256 == frame_context[0]
            and coherence_decision.intent_source_observation_sha256 == frame_context[0]
            and coherence_decision.visible_evidence_sha256 == frame_context[2]
            and coherence_decision.visible_text_sha256 == frame_context[3]
            and coherence_decision.action_sequence == action_count + 1
        )

    previous_after: ScreenObservation | None = None
    seen_receipt_sha256: set[str] = set()
    seen_replay_nonces: set[str] = set()
    for expected_step, transition in enumerate(transitions, start=1):
        if (
            isinstance(transition.step, bool)
            or not isinstance(transition.step, int)
            or transition.step != expected_step
            or type(transition.before) is not ScreenObservation
            or type(transition.after) is not ScreenObservation
            or type(transition.decision) is not PlannerDecision
            or transition.decision.kind != "action"
            or type(transition.decision.action) is not GuiAction
            or type(transition.decision.expected) is not ObservationPredicate
            or type(transition.decision.scorm_coherence) is not SCORMActionDecision
            or type(transition.decision.action_authorization) is not SCORMActionAuthorization
            or type(transition.result) is not ActionResult
            or type(transition.verified) is not bool
            or type(transition.screen_changed) is not bool
            or type(transition.observation_fresh) is not bool
            or type(transition.after_stable) is not bool
            or isinstance(transition.before_stable_attempts, bool)
            or not isinstance(transition.before_stable_attempts, int)
            or transition.before_stable_attempts < 2
            or isinstance(transition.after_stable_attempts, bool)
            or not isinstance(transition.after_stable_attempts, int)
            or transition.after_stable_attempts < 1
            or (transition.after_stable and transition.after_stable_attempts < 2)
            or (previous_after is not None and transition.before != previous_after)
        ):
            raise SCORMCloudRunnerError("runtime_result_transition_evidence_invalid")
        authorization = transition.decision.action_authorization
        assert isinstance(authorization, SCORMActionAuthorization)
        observation_authorization = authorization.observation_authorization
        receipt = authorization.receipt
        frame = observation_authorization.frame
        provider_context = observation_authorization.provider_context
        launch_authority = provider_context.launch_authority
        if (
            type(observation_authorization) is not SCORMObservationAuthorization
            or type(receipt) is not SCORMActionReceipt
            or type(frame) is not SCORMFrameEvidence
            or type(provider_context) is not SCORMProviderContextEvidence
            or type(launch_authority) is not SCORMOwnerBenchmarkLaunchAuthority
            or transition.decision.scorm_coherence != authorization.decision
            or authorization.intent.action_sequence != expected_step
            or receipt.action_sequence != expected_step
            or authorization.intent.name != transition.decision.action.name
            or authorization.intent.params != dict(transition.decision.action.params)
            or authorization.intent.source_observation_sha256 != transition.before.observation_id
            or frame.source_screenshot_sha256 != transition.before.screenshot_sha256
            or transition.result.details.get("scorm_action_authority") != authorization.audit_dict()
        ):
            raise SCORMCloudRunnerError("runtime_result_transition_evidence_invalid")
        receipt_context = (
            receipt.run_id,
            receipt.run_manifest_sha256,
            receipt.run_authority_sha256,
            receipt.allowed_origin,
            receipt.launch_url_sha256,
            receipt.launch_plan_sha256,
            receipt.control_grant_sha256,
        )
        frame_context = (
            frame.run_id,
            frame.run_manifest_sha256,
            frame.run_authority_sha256,
            frame.allowed_origin,
            frame.launch_url_sha256,
            frame.launch_plan_sha256,
            frame.control_grant_sha256,
        )
        provider_run_context = (
            provider_context.run_id,
            provider_context.run_manifest_sha256,
            provider_context.run_authority_sha256,
            provider_context.allowed_origin,
            provider_context.launch_url_sha256,
            provider_context.launch_plan_sha256,
            provider_context.control_grant_sha256,
        )
        launch_run_context = (
            launch_authority.run_id,
            launch_authority.run_manifest_sha256,
            launch_authority.run_authority_sha256,
            launch_authority.allowed_origin,
            launch_authority.launch_url_sha256,
            launch_authority.launch_plan_sha256,
            launch_authority.control_grant_sha256,
        )
        if (
            receipt_context != current_run_context
            or frame_context != current_run_context
            or provider_run_context != current_run_context
            or launch_run_context != current_run_context
            or frame.active_session_id != plan.session_id
            or provider_context.active_session_id != plan.session_id
            or launch_authority.active_session_id != plan.session_id
            or frame.live_origin != expected_origin
            or provider_context.live_origin != expected_origin
            or receipt.provider_context_sha256 != provider_context.provider_context_sha256
            or frame.provider_context_sha256 != provider_context.provider_context_sha256
            or receipt.launch_authority_sha256 != launch_authority.launch_authority_sha256
            or frame.launch_authority_sha256 != launch_authority.launch_authority_sha256
            or replay_ledger.verify_consumed(receipt) is not True
        ):
            raise SCORMCloudRunnerError("runtime_result_transition_provenance_invalid")
        receipt_sha256 = receipt.receipt_sha256
        replay_nonce = receipt.replay_nonce
        if receipt_sha256 in seen_receipt_sha256 or replay_nonce in seen_replay_nonces:
            raise SCORMCloudRunnerError("runtime_result_transition_replay_invalid")
        seen_receipt_sha256.add(receipt_sha256)
        seen_replay_nonces.add(replay_nonce)
        if transition.result.ok:
            if transition.decision.action.name == "wait":
                successful_result = (
                    transition.result.code == "wait_completed"
                    and transition.result.dispatch_state == "not_dispatched"
                )
            else:
                successful_result = (
                    transition.result.code in {"gateway_executed", "gateway_executed_handoff_required"}
                    and transition.result.dispatch_state == "dispatched"
                )
            if not successful_result:
                raise SCORMCloudRunnerError("runtime_result_transition_evidence_invalid")
        expected_fresh = (
            transition.after.observation_id != transition.before.observation_id
            and transition.after.sequence > transition.before.sequence
        )
        expected_screen_changed = transition.after.screenshot_sha256 != transition.before.screenshot_sha256
        expected_verified = bool(
            transition.result.ok
            and expected_fresh
            and transition.after_stable
            and evaluate_predicate(
                transition.decision.expected,
                before=transition.before,
                after=transition.after,
            )
        )
        if (
            transition.observation_fresh is not expected_fresh
            or transition.screen_changed is not expected_screen_changed
            or transition.verified is not expected_verified
        ):
            raise SCORMCloudRunnerError("runtime_result_transition_evidence_invalid")
        if expected_step < len(transitions) and not transition.verified:
            retryable_stale = (
                transition.result.ok is False
                and transition.result.code == "gateway_stale_source_frame"
                and transition.result.dispatch_state == "not_dispatched"
            )
            if not retryable_stale:
                raise SCORMCloudRunnerError("runtime_result_transition_terminal_failure_invalid")
        previous_after = transition.after
    if replay_ledger.next_sequence(run_authority.run_authority_sha256) != action_count + 1:
        raise SCORMCloudRunnerError("runtime_result_transition_replay_invalid")

    def _observation_payload(observation: ScreenObservation) -> tuple[object, ...]:
        return (
            observation.observation_id,
            observation.sequence,
            observation.captured_at_unix,
            observation.screenshot_sha256,
            observation.width,
            observation.height,
            observation.ocr_text,
            observation.vision_text,
            observation.mime_type,
            observation.window_handle,
            observation.window_process_id,
            observation.window_title_sha256,
            observation.window_rect,
            observation.cursor_x,
            observation.cursor_y,
            observation.dpi_x,
            observation.dpi_y,
            tuple(token.to_dict() for token in observation.ocr_tokens),
            observation.stability_profile,
            observation.stability_sha256,
            None if observation.frame_artifact is None else observation.frame_artifact.to_dict(),
        )

    if transitions:
        final_transition = transitions[-1]
        in_flight_unverified = (
            final_transition.verified is False
            and final_transition.result.dispatch_state in {"dispatched", "ambiguous"}
        )
        allowed_in_flight_statuses = {
            "emergency_stopped",
            "evidence_error",
            "observer_error",
            "post_dispatch_verification_failed",
            "unstable_post_action_frame",
        }
        if in_flight_unverified and status not in allowed_in_flight_statuses:
            raise SCORMCloudRunnerError("runtime_result_terminal_status_invalid")
    exact_verified_changed = sum(
        transition.verified and transition.screen_changed for transition in transitions
    )
    if verified != exact_verified_changed:
        raise SCORMCloudRunnerError("runtime_result_verified_count_invalid")
    if (
        status == "completed"
        and transitions
        and (
            type(result.final_observation) is not ScreenObservation
            or type(transitions[-1].after) is not ScreenObservation
            or result.final_observation is not transitions[-1].after
        )
    ):
        raise SCORMCloudRunnerError("runtime_result_final_observation_invalid")
    if terminal_decision is not None and type(terminal_decision) is not PlannerDecision:
        raise SCORMCloudRunnerError("runtime_result_terminal_decision_invalid")
    if not isinstance(human_gate, str) or not isinstance(pause_kind, str):
        raise SCORMCloudRunnerError("runtime_result_gate_invalid")
    if status == "human_required":
        if human_gate != "identity_attestation" or type(result.final_observation) is not ScreenObservation:
            raise SCORMCloudRunnerError("runtime_result_human_gate_invalid")
        if (
            type(terminal_decision) is not PlannerDecision
            or terminal_decision.reason != reason
            or terminal_decision.kind != "human_required"
            or terminal_decision.human_gate != human_gate
            or not terminal_action_matches(
                terminal_decision.scorm_coherence,
                result.final_observation,
                expected_kind=OWNER_ATTESTATION_REQUIRED,
            )
        ):
            raise SCORMCloudRunnerError("runtime_result_terminal_decision_invalid")
    elif human_gate:
        raise SCORMCloudRunnerError("runtime_result_human_gate_unexpected")
    if status == "completed":
        final_transition = transitions[-1] if transitions else None
        if final_transition is None:
            raise SCORMCloudRunnerError("runtime_result_completion_evidence_invalid")
        final_after = final_transition.after
        if type(final_after) is not ScreenObservation or type(result.final_observation) is not ScreenObservation:
            raise SCORMCloudRunnerError("runtime_result_final_observation_invalid")
        if _observation_payload(result.final_observation) != _observation_payload(final_after):
            raise SCORMCloudRunnerError("runtime_result_final_observation_invalid")
        predicate = result.success_predicate
        if (
            action_count < 1
            or verified < 1
            or not transitions
            or transitions[-1].verified is not True
            or type(predicate) is not ObservationPredicate
            or predicate.kind not in SEMANTIC_SUCCESS_PREDICATES
            or type(terminal_decision) is not PlannerDecision
            or terminal_decision.kind != "complete"
            or terminal_decision.success_predicate != predicate
            or type(result.final_observation) is not ScreenObservation
            or result.final_observation is not final_after
            or not terminal_preflight_matches(
                terminal_decision.scorm_coherence,
                result.final_observation,
                allowed_kinds=frozenset({READY_FOR_INTENT}),
            )
            or evaluate_predicate(
                predicate,
                before=transitions[0].before,
                after=final_after,
            )
            is not True
        ):
            raise SCORMCloudRunnerError("runtime_result_completion_evidence_invalid")
    if not isinstance(pause_receipt, str):
        raise SCORMCloudRunnerError("runtime_result_pause_receipt_invalid")
    if status == "paused":
        if (
            pause_kind not in PAUSE_KINDS
            or _SHA256.fullmatch(pause_receipt) is None
            or type(result.final_observation) is not ScreenObservation
        ):
            raise SCORMCloudRunnerError("runtime_result_pause_receipt_invalid")
        if (
            type(terminal_decision) is not PlannerDecision
            or terminal_decision.reason != reason
            or terminal_decision.kind != "pause"
            or terminal_decision.pause_kind != pause_kind
            or not (
                terminal_preflight_matches(
                    terminal_decision.scorm_coherence,
                    result.final_observation,
                    allowed_kinds=frozenset({READY_FOR_INTENT, RESUMABLE_PAUSE}),
                )
                or terminal_action_matches(
                    terminal_decision.scorm_coherence,
                    result.final_observation,
                    expected_kind=RESUMABLE_PAUSE,
                )
            )
        ):
            raise SCORMCloudRunnerError("runtime_result_terminal_decision_invalid")
        if (
            pause_checkpoint_store.verify_checkpoint(
                result.final_observation,
                transitions,
                pause_kind=pause_kind,
                checkpoint_sha256=pause_receipt,
            )
            is not True
        ):
            raise SCORMCloudRunnerError("runtime_result_pause_checkpoint_invalid")
        public_status = "paused_prerequisite"
    else:
        if pause_kind or pause_receipt:
            raise SCORMCloudRunnerError("runtime_result_pause_context_unexpected")
        public_status = status
    return (
        public_status,
        success,
        human_gate or None,
        pause_kind or None,
        pause_receipt or None,
        action_count,
        verified,
    )


def run_scorm_cloud(
    config: SCORMCloudRunConfig,
    *,
    launch_url: str,
    session_signing_secret: bytes,
    hnc_signing_secret: bytes,
    owner_benchmark_signing_secret: bytes,
    capability_token: str,
    dependencies: SCORMCloudRuntimeDependencies | None = None,
) -> SCORMCloudRunResult:
    """Launch and run the exact governed local stack after all preflight gates."""

    if not isinstance(config, SCORMCloudRunConfig):
        raise TypeError("config must be SCORMCloudRunConfig")
    if config.live is not True:
        raise SCORMCloudRunnerError("live_flag_required")
    if (
        not isinstance(capability_token, str)
        or capability_token != capability_token.strip()
        or len(capability_token) < 32
    ):
        raise SCORMCloudRunnerError("capability_token_invalid")
    session_secret = _require_secret("session_signing_secret", session_signing_secret)
    hnc_secret = _require_secret("hnc_signing_secret", hnc_signing_secret)
    owner_secret = _require_secret(
        "owner_benchmark_signing_secret",
        owner_benchmark_signing_secret,
    )
    if len({session_secret, hnc_secret, owner_secret}) != 3:
        raise SCORMCloudRunnerError("signing_secrets_must_be_distinct")
    deps = dependencies or SCORMCloudRuntimeDependencies()
    prelaunch = _prelaunch_organism_config(config)
    plan = build_scorm_cloud_edge_plan(
        exact_url=launch_url,
        edge_executable=config.edge_executable,
        profile=config.profile,
        local_model=config.model,
        local_model_endpoint=config.endpoint,
        expected_initial_title_regex=config.expected_initial_title_regex,
        allowed_title_regex=config.allowed_title_regex,
        session_id=config.run_id,
        allowed_gui_actions=config.runtime_actions,
        capture_timeout_seconds=30.0,
        policy_ttl_seconds=config.lease_ttl_seconds,
        max_handoffs=config.max_handoffs,
    )
    preflight_result = deps.preflight_probe(config)
    if not isinstance(preflight_result, Mapping) or preflight_result.get("ok") is not True:
        raise SCORMCloudRunnerError("local_dependency_preflight_failed")
    config.state_directory.mkdir(parents=True, exist_ok=True)
    if config.state_directory.is_symlink() or not config.state_directory.is_dir():
        raise SCORMCloudRunnerError("state_directory_creation_failed")
    ledger = SCORMEvidenceLedger(
        config.scorm_evidence_path,
        run_id=config.run_id,
        utc_now=deps.utc_now,
    )
    replay_ledger = SCORMActionReplayLedger(
        config.replay_directory,
        marker_secret=hnc_secret,
    )
    gateway = deps.gateway_factory(config)
    native_runtime = deps.native_runtime_factory(
        gateway,
        ledger,
        session_secret,
        deps.utc_now,
    )

    active: ActiveSCORMCloudSession | None = None
    gate: HNCScormCoherenceGate | None = None
    evidence_authorizer: SCORMOwnerBenchmarkEvidenceAuthorizer | None = None
    try:
        active = (
            native_runtime.session_runner.attach(plan)
            if config.attach_existing
            else native_runtime.session_runner.start(plan)
        )
        now = deps.utc_now().astimezone(UTC)
        run_authority = SCORMRunAuthority.issue(
            secret=hnc_secret,
            run_id=config.run_id,
            run_manifest_sha256=owner_benchmark_run_manifest_sha256(active),
            replay_nonce=f"{config.run_id}-{uuid.uuid4().hex}",
            allowed_origin="https://cloud.scorm.com",
            launch_url_sha256=plan.url_sha256,
            launch_plan_sha256=plan.plan_sha256,
            control_grant_sha256=active.control_grant_sha256,
            allowed_actions=plan.allowed_gui_actions,
            max_actions=config.max_steps,
            issued_at=now,
            expires_at=now + timedelta(seconds=config.lease_ttl_seconds),
        )
        ledger.append(
            "hnc_run_authority_issued",
            {
                "allowed_actions": list(run_authority.allowed_actions),
                "control_grant_sha256": run_authority.control_grant_sha256,
                "launch_plan_sha256": run_authority.launch_plan_sha256,
                "launch_url_sha256": run_authority.launch_url_sha256,
                "run_authority_sha256": run_authority.run_authority_sha256,
                "run_manifest_sha256": run_authority.run_manifest_sha256,
            },
        )
        gate = HNCScormCoherenceGate(
            hnc_secret,
            owner_benchmark_keys={SCORM_OWNER_BENCHMARK_KEY_ID: owner_secret},
            replay_ledger=replay_ledger,
        )
        evidence_authorizer = SCORMOwnerBenchmarkEvidenceAuthorizer(
            active_session=active,
            run_authority=run_authority,
            hnc_signing_secret=hnc_secret,
            session_signing_secret=session_secret,
            owner_benchmark_signing_secret=owner_secret,
            owner_benchmark_issuer=SCORM_OWNER_BENCHMARK_ISSUER,
            owner_benchmark_key_id=SCORM_OWNER_BENCHMARK_KEY_ID,
            synthetic_persona_id=SCORM_SYNTHETIC_PERSONA_ID,
            native_url_probe=native_runtime.native_url_probe,
            native_target_probe=native_runtime.native_target_probe,
            ledger=ledger,
            utc_now=deps.utc_now,
        )
        runtime_authority = SCORMVisionRuntimeAuthority(
            active_session=active,
            coherence_gate=gate,
            run_authority=run_authority,
            provider_context_supplier=evidence_authorizer.issue_provider_context,
            action_target_supplier=evidence_authorizer.issue_action_target,
            benchmark_grant_supplier=evidence_authorizer.issue_benchmark_grant,
            utc_now=deps.utc_now,
        )
        organism_config = replace(
            prelaunch,
            expected_window_title=active.initial_binding.window.title,
            expected_process_id=active.initial_binding.window.process_id,
            scorm_run_authority_sha256=run_authority.run_authority_sha256,
            scorm_control_grant_sha256=active.control_grant_sha256,
        )
        organism = deps.organism_builder(
            organism_config,
            capability_token=capability_token,
            tesseract_executable=config.tesseract_executable,
            scorm_runtime_authority=runtime_authority,
        )
        run_method = getattr(organism, "run", None)
        if not callable(run_method):
            raise SCORMCloudRunnerError("organism_builder_result_invalid")
        runtime_result = run_method()
        pause_checkpoint_store = getattr(
            organism,
            "pause_checkpoint_store",
            None,
        )
        (
            status,
            success,
            human_gate,
            pause_kind,
            pause_receipt,
            action_count,
            verified_changed,
        ) = _runtime_projection(
            runtime_result,
            run_authority=run_authority,
            active_session=active,
            replay_ledger=replay_ledger,
            pause_checkpoint_store=pause_checkpoint_store,
            pause_checkpoint_path=organism_config.pause_checkpoint_path,
        )
        return SCORMCloudRunResult(
            run_id=config.run_id,
            status=status,
            success=success,
            human_gate=human_gate,
            pause_kind=pause_kind,
            pause_receipt_sha256=pause_receipt,
            continuation_mode=(FRESH_RUN_CONTINUATION if status == "paused_prerequisite" else None),
            action_count=action_count,
            verified_changed_transitions=verified_changed,
            run_authority_sha256=run_authority.run_authority_sha256,
            control_grant_sha256=active.control_grant_sha256,
            scorm_evidence_path=str(config.scorm_evidence_path),
            desktop_evidence_path=str(organism_config.desktop_evidence_path),
            course_ledger_path=str(organism_config.ledger_path),
            frame_artifact_directory=str(organism_config.frame_artifact_directory),
        )
    finally:
        if evidence_authorizer is not None:
            evidence_authorizer.close()
        if gate is not None:
            gate.close()
        if active is not None:
            active.close()


def _consume_environment(environ: Mapping[str, str] | os._Environ[str], name: str) -> str:
    raw = environ.get(name)
    try:
        if not isinstance(raw, str) or not raw:
            raise SCORMCloudRunnerError(f"{name.lower()}_required")
        return raw
    finally:
        pop = getattr(environ, "pop", None)
        if callable(pop):
            pop(name, None)


def _profile_from_args(args: argparse.Namespace) -> EdgeProfileSpec:
    if args.profile_mode == PROFILE_ISOLATED:
        return EdgeProfileSpec.isolated(
            args.user_data_dir,
            profile_directory=args.profile_directory,
        )
    return EdgeProfileSpec.owner_existing(
        args.user_data_dir,
        profile_directory=args.profile_directory,
        owner_edge_process_id=args.owner_edge_process_id,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Aureon's governed local SCORM Cloud operator",
    )
    parser.add_argument("--edge-executable", type=Path, required=True)
    parser.add_argument(
        "--profile-mode",
        choices=(PROFILE_ISOLATED, PROFILE_OWNER_EXISTING),
        required=True,
    )
    parser.add_argument("--user-data-dir", type=Path, required=True)
    parser.add_argument("--profile-directory", default="Default")
    parser.add_argument("--owner-edge-process-id", type=int)
    parser.add_argument(
        "--attach-existing",
        action="store_true",
        help="bind the sole exact already-open owner browser window without launching one",
    )
    parser.add_argument(
        "--hnc-answer-brain",
        action="store_true",
        help="route visible assessment choices through the HNC Ollama Cloud switchboard",
    )
    parser.add_argument("--model", default="qwen3:8b")
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434")
    parser.add_argument("--expected-title-regex", default=DEFAULT_TITLE_REGEX)
    parser.add_argument("--allowed-title-regex", default=DEFAULT_TITLE_REGEX)
    parser.add_argument("--goal", default=DEFAULT_GOAL)
    parser.add_argument(
        "--allow-action",
        action="append",
        choices=sorted(MUTATING_ACTIONS),
    )
    parser.add_argument("--planner-timeout", type=float, default=60.0)
    parser.add_argument("--lease-ttl", type=float, default=7_200.0)
    parser.add_argument("--max-steps", type=int, default=500)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--max-unchanged", type=int, default=4)
    parser.add_argument("--max-seconds", type=float, default=3_600.0)
    parser.add_argument("--gateway-actions-per-minute", type=int, default=60)
    parser.add_argument("--max-handoffs", type=int, default=200)
    parser.add_argument("--run-id")
    parser.add_argument("--state-directory", type=Path, required=True)
    parser.add_argument("--tesseract", type=Path)
    parser.add_argument(
        "--live",
        action="store_true",
        help="required; URL, signing material, and capability stay in environment",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | os._Environ[str] | None = None,
    dependencies: SCORMCloudRuntimeDependencies | None = None,
) -> int:
    args = _parser().parse_args(argv)
    env = os.environ if environ is None else environ
    launch_url = _consume_environment(env, SCORM_LAUNCH_URL_ENV)
    session_secret = _consume_environment(env, SCORM_SESSION_SIGNING_SECRET_ENV).encode("utf-8")
    hnc_secret = _consume_environment(env, SCORM_HNC_SIGNING_SECRET_ENV).encode("utf-8")
    owner_secret = _consume_environment(
        env,
        SCORM_OWNER_BENCHMARK_SIGNING_SECRET_ENV,
    ).encode("utf-8")
    capability_token = _consume_environment(env, CAPABILITY_TOKEN_ENV)
    config = SCORMCloudRunConfig(
        edge_executable=args.edge_executable,
        profile=_profile_from_args(args),
        run_id=args.run_id or f"scorm-{uuid.uuid4().hex}",
        state_directory=args.state_directory,
        model=args.model,
        endpoint=args.endpoint,
        expected_initial_title_regex=args.expected_title_regex,
        allowed_title_regex=args.allowed_title_regex,
        goal=args.goal,
        allowed_gateway_actions=tuple(args.allow_action or DEFAULT_GATEWAY_ACTIONS),
        planner_timeout_seconds=args.planner_timeout,
        lease_ttl_seconds=args.lease_ttl,
        max_steps=args.max_steps,
        max_retries_per_action=args.max_retries,
        max_consecutive_unchanged=args.max_unchanged,
        max_seconds=args.max_seconds,
        gateway_max_actions_per_window=args.gateway_actions_per_minute,
        max_handoffs=args.max_handoffs,
        live=args.live,
        tesseract_executable=args.tesseract,
        attach_existing=args.attach_existing,
        hnc_answer_brain=args.hnc_answer_brain,
    )
    result = run_scorm_cloud(
        config,
        launch_url=launch_url,
        session_signing_secret=session_secret,
        hnc_signing_secret=hnc_secret,
        owner_benchmark_signing_secret=owner_secret,
        capability_token=capability_token,
        dependencies=dependencies,
    )
    print(json.dumps(result.to_dict(), sort_keys=True))
    if result.success:
        return 0
    if result.status in {"human_required", "paused_prerequisite"}:
        return 3
    return 4


def entrypoint(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | os._Environ[str] | None = None,
    dependencies: SCORMCloudRuntimeDependencies | None = None,
) -> int:
    """Map every operational failure to stable, non-sensitive CLI output."""

    try:
        return main(argv, environ=environ, dependencies=dependencies)
    except SCORMCloudRunnerError as exc:
        print(json.dumps({"ok": False, "error": exc.code}), file=sys.stderr)
        return 2
    except Exception:
        print(
            json.dumps({"ok": False, "error": "scorm_runtime_failed"}),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(entrypoint())


__all__ = [
    "SCORMCloudRunConfig",
    "SCORMCloudRunResult",
    "SCORMCloudRunnerError",
    "SCORMCloudRuntimeDependencies",
    "SCORM_HNC_SIGNING_SECRET_ENV",
    "SCORM_LAUNCH_URL_ENV",
    "SCORM_OWNER_BENCHMARK_SIGNING_SECRET_ENV",
    "SCORM_SESSION_SIGNING_SECRET_ENV",
    "entrypoint",
    "main",
    "run_scorm_cloud",
]
