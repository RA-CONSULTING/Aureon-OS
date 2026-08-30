from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from aureon.autonomous.aureon_governed_desktop_gateway import (
    GovernedDesktopGateway,
    WindowInfo,
)
from aureon.operator import scorm_cloud_runner as runner_module
from aureon.operator.governed_window_session import (
    SessionWindowBinding,
    window_sha256,
)
from aureon.operator.hnc_scorm_coherence import (
    ASSESSMENT_CONTROL,
    CONTINUE,
    RESUMABLE_PAUSE,
    SCORMActionReceipt,
    SCORMActionReplayLedger,
    SCORMRunAuthority,
)
from aureon.operator.local_gui_observer import OCRToken, ScreenObservation, WindowRect
from aureon.operator.local_gui_pause import HashOnlyPauseCheckpointStore
from aureon.operator.local_gui_runtime import (
    ActionResult,
    GuiAction,
    ObservationPredicate,
    PlannerDecision,
    RuntimeResult,
    RuntimeTransition,
)
from aureon.operator.local_gui_scorm_authority import SCORMVisionRuntimeAuthority
from aureon.operator.scorm_cloud_evidence import (
    NativeAddressBarRead,
    NativeControlRead,
    Win32EdgeNativeTargetProbe,
    Win32EdgeNativeURLProbe,
    owner_benchmark_run_manifest_sha256,
)
from aureon.operator.scorm_cloud_runner import (
    SCORM_HNC_SIGNING_SECRET_ENV,
    SCORM_LAUNCH_URL_ENV,
    SCORM_OWNER_BENCHMARK_SIGNING_SECRET_ENV,
    SCORM_SESSION_SIGNING_SECRET_ENV,
    SCORMCloudRunConfig,
    SCORMCloudRunnerError,
    SCORMCloudRuntimeDependencies,
    _NativeRuntime,
    entrypoint,
    main,
    run_scorm_cloud,
)
from aureon.operator.scorm_cloud_session import (
    ActiveSCORMCloudSession,
    EdgeProfileSpec,
    LaunchedEdgeProcess,
    SCORMCloudLaunchPlan,
    SCORMEvidenceLedger,
    SCORMPublicPreviewControlGrant,
    build_scorm_cloud_edge_plan,
)

NOW = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)
SCORM_URL = "https://cloud.scorm.com/launch/course?token=signed-value-123"
SESSION_SECRET = b"session-signing-secret-is-distinct-and-long"
HNC_SECRET = b"hnc-signing-secret-is-distinct-and-long-enough"
OWNER_SECRET = b"owner-benchmark-secret-is-distinct-and-long"
CAPABILITY_TOKEN = "one-time-hermetic-capability-token"


class FakeGatewayBackend:
    def foreground_window(self) -> WindowInfo:
        raise AssertionError("hermetic composition must not inspect raw foreground state")


class FakeActiveWindowSession:
    def __init__(self, binding: SessionWindowBinding) -> None:
        self.binding = binding
        self.closed = False

    def authorize_active_binding(self) -> SessionWindowBinding:
        if self.closed:
            raise RuntimeError("closed")
        return self.binding

    def close(self) -> None:
        self.closed = True


class AllowLineage:
    def is_same_process_or_descendant(
        self,
        process_id: int,
        *,
        ancestor_process_id: int,
    ) -> bool:
        return (process_id, ancestor_process_id) in {(555, 555), (556, 555)}


class FakeTargetReader:
    def read_at(
        self,
        window_handle: int,
        root_process_id: int,
        x: int,
        y: int,
        max_ancestors: int,
    ) -> NativeControlRead:
        assert (window_handle, root_process_id, x, y) == (444, 555, 150, 140)
        assert max_ancestors > 0
        return NativeControlRead(
            window_handle=444,
            root_process_id=555,
            element_process_id=556,
            x=100,
            y=120,
            width=220,
            height=40,
            role="RadioButton",
            name="B. Safe answer",
            automation_id="answer-b",
            ancestor_depth=7,
            focused=False,
        )

    def read_focused(
        self,
        window_handle: int,
        root_process_id: int,
        max_ancestors: int,
    ) -> NativeControlRead:
        raise AssertionError("coordinate click must not use focused-control evidence")


class HermeticSessionStarter:
    def __init__(self, ledger: SCORMEvidenceLedger, session_secret: bytes) -> None:
        self.ledger = ledger
        self.session_secret = session_secret
        self.start_calls: list[SCORMCloudLaunchPlan] = []
        self.active: ActiveSCORMCloudSession | None = None

    def start(self, plan: SCORMCloudLaunchPlan) -> ActiveSCORMCloudSession:
        self.start_calls.append(plan)
        window = WindowInfo(
            handle=444,
            title="Course - SCORM Cloud - Microsoft Edge",
            process_id=555,
            left=10,
            top=20,
            width=1200,
            height=800,
        )
        binding = SessionWindowBinding(
            session_id=plan.session_id,
            binding_id="binding-hermetic-cli-composition",
            policy_sha256="a" * 64,
            generation=1,
            handoff_count=0,
            bound_at=NOW,
            origin_label="scorm-cloud-launch-context-v1",
            window=window,
            window_sha256=window_sha256(window),
        )
        control = SCORMPublicPreviewControlGrant.issue(
            signing_secret=self.session_secret,
            plan=plan,
            policy_sha256=binding.policy_sha256,
            issued_at=NOW,
            expires_at=NOW + timedelta(hours=2),
        )
        self.active = ActiveSCORMCloudSession(
            plan=plan,
            launched_process=LaunchedEdgeProcess(
                process_id=555,
                launched_at_utc="2026-08-16T12:00:00Z",
            ),
            window_session=FakeActiveWindowSession(binding),  # type: ignore[arg-type]
            initial_binding=binding,
            control_manifest=control,
            control_grant_sha256=control.control_grant_sha256,
            _controller=object(),  # type: ignore[arg-type]
            _process_inspector=AllowLineage(),
            _enumerator=object(),  # type: ignore[arg-type]
            _ledger=self.ledger,
            _launch_baseline_handles=frozenset(),
        )
        return self.active


def executable(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "msedge.exe"
    path.write_bytes(b"hermetic-edge-fixture")
    return path


def run_config(
    tmp_path: Path,
    *,
    live: bool = True,
    run_id: str = "hermetic-scorm-cli-run",
) -> SCORMCloudRunConfig:
    return SCORMCloudRunConfig(
        edge_executable=executable(tmp_path),
        profile=EdgeProfileSpec.isolated(tmp_path / "fresh-edge-profile"),
        run_id=run_id,
        state_directory=tmp_path / "state",
        live=live,
        max_steps=20,
        max_seconds=300.0,
        lease_ttl_seconds=600.0,
        planner_timeout_seconds=30.0,
    )


def project_runtime_result(
    runtime_result: object,
    tmp_path: Path,
) -> tuple[str, bool, str | None, str | None, str | None, int, int]:
    run_id = "hermetic-projection-context"
    plan = build_scorm_cloud_edge_plan(
        exact_url=SCORM_URL,
        edge_executable=executable(tmp_path),
        profile=EdgeProfileSpec.isolated(tmp_path / "projection-profile"),
        local_model="qwen2.5vl:3b",
        local_model_endpoint="http://127.0.0.1:11434",
        expected_initial_title_regex=runner_module.DEFAULT_TITLE_REGEX,
        allowed_title_regex=runner_module.DEFAULT_TITLE_REGEX,
        session_id=run_id,
        allowed_gui_actions=("left_click",),
        policy_ttl_seconds=600.0,
    )
    evidence_ledger = SCORMEvidenceLedger(
        tmp_path / "projection.scorm.jsonl",
        run_id=run_id,
        utc_now=lambda: NOW,
    )
    active = HermeticSessionStarter(evidence_ledger, SESSION_SECRET).start(plan)
    replay_ledger = SCORMActionReplayLedger(
        tmp_path / "projection-replay",
        marker_secret=HNC_SECRET,
    )
    run_authority = SCORMRunAuthority.issue(
        secret=HNC_SECRET,
        run_id=run_id,
        run_manifest_sha256=owner_benchmark_run_manifest_sha256(active),
        replay_nonce="hermetic-projection-replay-nonce",
        allowed_origin="https://cloud.scorm.com",
        launch_url_sha256=plan.url_sha256,
        launch_plan_sha256=plan.plan_sha256,
        control_grant_sha256=active.control_grant_sha256,
        allowed_actions=plan.allowed_gui_actions,
        max_actions=20,
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=10),
    )
    pause_checkpoint_store = HashOnlyPauseCheckpointStore(
        tmp_path / f"{run_id}.pause.json",
        run_id=run_id,
        build_id="hermetic-projection-build",
        goal="hermetic projection",
        run_authority_sha256=run_authority.run_authority_sha256,
        control_grant_sha256=active.control_grant_sha256,
    )
    try:
        return runner_module._runtime_projection(
            runtime_result,
            run_authority=run_authority,
            active_session=active,
            replay_ledger=replay_ledger,
            pause_checkpoint_store=pause_checkpoint_store,
            pause_checkpoint_path=pause_checkpoint_store.path,
        )
    finally:
        active.close()


def observation(
    binding: SessionWindowBinding,
    *,
    words: tuple[str, ...] | None = None,
    vision_text: str = "Assessment question with three radio options.",
) -> ScreenObservation:
    visible_words = words or (
        "SCORM",
        "Cloud",
        "Preview",
        "Assessment",
        "No",
        "answer",
        "submitted",
        "B.",
        "Safe",
        "answer",
    )
    return ScreenObservation(
        observation_id="b" * 64,
        sequence=1,
        captured_at_unix=NOW.timestamp(),
        screenshot_sha256="c" * 64,
        width=1600,
        height=1000,
        ocr_tokens=tuple(
            OCRToken(
                word,
                40 + index * 70,
                100 if index < 3 else 140,
                60,
                20,
                0.99,
            )
            for index, word in enumerate(visible_words)
        ),
        vision_text=vision_text,
        window_handle=binding.window.handle,
        window_process_id=binding.window.process_id,
        window_title_sha256=hashlib.sha256(binding.window.title.encode("utf-8")).hexdigest(),
        window_rect=WindowRect(
            binding.window.left,
            binding.window.top,
            binding.window.width,
            binding.window.height,
        ),
        dpi_x=96.0,
        dpi_y=96.0,
    )


def empty_runtime_result(**changes: object) -> RuntimeResult:
    return replace(
        RuntimeResult(
            status="aborted",
            success=False,
            reason="bounded runtime stopped",
            action_count=0,
            verified_changed_transitions=0,
            final_observation=None,
            transitions=(),
        ),
        **changes,
    )


def completed_result_without_semantic_terminal() -> RuntimeResult:
    before = ScreenObservation(
        observation_id="1" * 64,
        sequence=1,
        captured_at_unix=NOW.timestamp(),
        screenshot_sha256="2" * 64,
        width=100,
        height=100,
        ocr_tokens=(),
        vision_text="assessment in progress",
    )
    after = replace(
        before,
        observation_id="3" * 64,
        sequence=2,
        screenshot_sha256="4" * 64,
        vision_text="assessment completed",
    )
    decision = PlannerDecision(
        kind="action",
        reason="advance the governed page",
        action=GuiAction("left_click", {"x": 10, "y": 10}),
        expected=ObservationPredicate("screen_changed"),
    )
    transition = RuntimeTransition(
        step=1,
        before=before,
        decision=decision,
        result=ActionResult(True, "gateway_executed", dispatch_state="dispatched"),
        after=after,
        screen_changed=True,
        observation_fresh=True,
        verified=True,
        verification_reason="verified",
    )
    return RuntimeResult(
        status="completed",
        success=True,
        reason="forged counts without semantic terminal evidence",
        action_count=1,
        verified_changed_transitions=1,
        final_observation=after,
        transitions=(transition,),
    )


def hermetic_dependencies(
    holder: dict[str, object],
) -> SCORMCloudRuntimeDependencies:
    def gateway_factory(config: SCORMCloudRunConfig) -> GovernedDesktopGateway:
        gateway = GovernedDesktopGateway(
            backend=FakeGatewayBackend(),  # type: ignore[arg-type]
            evidence_path=config.desktop_evidence_path,
            utc_now=lambda: NOW,
        )
        holder["gateway"] = gateway
        return gateway

    def native_factory(
        gateway: GovernedDesktopGateway,
        ledger: SCORMEvidenceLedger,
        session_secret: bytes,
        utc_now,
    ) -> _NativeRuntime:
        assert gateway is holder["gateway"]
        assert utc_now() == NOW
        starter = HermeticSessionStarter(ledger, session_secret)
        holder["starter"] = starter
        return _NativeRuntime(
            session_runner=starter,
            native_url_probe=Win32EdgeNativeURLProbe(
                reader=lambda _handle, _pid, _maximum: NativeAddressBarRead(
                    exact_url=SCORM_URL,
                    window_handle=444,
                    process_id=555,
                    automation_id="view_1001",
                    control_name="Address and search bar",
                ),
                utc_now=lambda: NOW,
            ),
            native_target_probe=Win32EdgeNativeTargetProbe(
                reader=FakeTargetReader(),
                process_inspector=AllowLineage(),
            ),
        )

    def organism_builder(
        config,
        *,
        capability_token: str,
        tesseract_executable,
        scorm_runtime_authority,
    ):
        assert capability_token == CAPABILITY_TOKEN
        assert tesseract_executable is None
        assert config.planner_kind == "scorm_vision"
        assert config.authorization_label == "owner_benchmark_test"
        assert isinstance(scorm_runtime_authority, SCORMVisionRuntimeAuthority)
        holder["organism_config"] = config
        holder["runtime_authority"] = scorm_runtime_authority
        pause_checkpoint_store = HashOnlyPauseCheckpointStore(
            config.pause_checkpoint_path,
            run_id=config.run_id,
            build_id="hermetic-scorm-organism-build",
            goal=config.goal,
            run_authority_sha256=config.scorm_run_authority_sha256,
            control_grant_sha256=config.scorm_control_grant_sha256,
        )
        holder["pause_checkpoint_store"] = pause_checkpoint_store

        class FakeOrganism:
            def __init__(self) -> None:
                self.pause_checkpoint_store = pause_checkpoint_store

            def run(self):
                injected = holder.get("injected_runtime_result")
                if isinstance(injected, RuntimeResult):
                    return injected
                binding = scorm_runtime_authority.authorize_binding()
                frame_observation = observation(binding)
                bundle = scorm_runtime_authority.classify_observation(frame_observation)
                action = GuiAction("left_click", {"x": 150, "y": 140})
                evaluated = scorm_runtime_authority.evaluate_action(
                    bundle,
                    frame_observation,
                    action,
                )
                assert evaluated.decision.kind == CONTINUE
                assert evaluated.authorization is not None
                assert evaluated.authorization.action_target.target_semantic == ASSESSMENT_CONTROL
                authorization = evaluated.authorization
                if holder.get("skip_receipt_consumption") is True:
                    receipt = authorization.receipt
                else:
                    receipt = scorm_runtime_authority.verify_and_consume_action(
                        authorization,
                        frame_observation,
                        action,
                    )
                if holder.get("tamper_receipt_hmac") is True:
                    receipt = replace(receipt, hmac_sha256="0" * 64)
                    authorization = replace(authorization, receipt=receipt)
                holder["receipt"] = receipt
                expected = ObservationPredicate("screen_changed")
                include_authority = holder.get("strip_action_authority") is not True
                action_decision = PlannerDecision(
                    kind="action",
                    reason="exercise exact governed assessment control",
                    action=action,
                    expected=expected,
                    scorm_coherence=evaluated.decision if include_authority else None,
                    action_authorization=(authorization if include_authority else None),
                )
                after = replace(
                    frame_observation,
                    observation_id="d" * 64,
                    sequence=2,
                    screenshot_sha256="e" * 64,
                    vision_text="Assessment question completed successfully.",
                )
                first_failure = holder.get("first_failure")
                if first_failure == "stale":
                    first_result = ActionResult(
                        False,
                        "gateway_stale_source_frame",
                        {"scorm_action_authority": (authorization.audit_dict())},
                        dispatch_state="not_dispatched",
                    )
                elif first_failure == "ambiguous":
                    first_result = ActionResult(
                        False,
                        "gateway_exception",
                        {"scorm_action_authority": (authorization.audit_dict())},
                        dispatch_state="ambiguous",
                    )
                else:
                    first_result = ActionResult(
                        True,
                        "gateway_executed",
                        (
                            {}
                            if holder.get("strip_action_audit") is True
                            else {"scorm_action_authority": (authorization.audit_dict())}
                        ),
                        dispatch_state="dispatched",
                    )
                transition = RuntimeTransition(
                    step=1,
                    before=frame_observation,
                    decision=action_decision,
                    result=first_result,
                    after=after,
                    screen_changed=True,
                    observation_fresh=True,
                    verified=first_result.ok,
                    verification_reason=(
                        "verified" if first_result.ok else f"executor_failed:{first_result.code}"
                    ),
                )
                if holder.get("return_without_transition") is True:
                    result = RuntimeResult(
                        status="aborted",
                        success=False,
                        reason="consumed action omitted from runtime result",
                        action_count=0,
                        verified_changed_transitions=0,
                        final_observation=frame_observation,
                        transitions=(),
                    )
                    holder["runtime_result"] = result
                    return result
                if holder.get("return_unstable") is True:
                    unstable = replace(
                        transition,
                        after_stable=False,
                        verified=False,
                        verification_reason="stable_frame_not_reached",
                    )
                    return RuntimeResult(
                        status="unstable_post_action_frame",
                        success=False,
                        reason="post-action screen did not stabilize",
                        action_count=1,
                        verified_changed_transitions=0,
                        final_observation=after,
                        transitions=(unstable,),
                    )
                if holder.get("return_duplicate_receipt") is True:
                    replayed_after = replace(
                        after,
                        observation_id="5" * 64,
                        sequence=3,
                        screenshot_sha256="6" * 64,
                    )
                    replayed = replace(
                        transition,
                        step=2,
                        before=after,
                        after=replayed_after,
                    )
                    return RuntimeResult(
                        status="aborted",
                        success=False,
                        reason="duplicate consumed authorization",
                        action_count=2,
                        verified_changed_transitions=2,
                        final_observation=replayed_after,
                        transitions=(transition, replayed),
                    )
                if holder.get("return_spliced") is True:
                    unrelated_before = replace(
                        after,
                        observation_id="5" * 64,
                        sequence=3,
                    )
                    unrelated_after = replace(
                        unrelated_before,
                        observation_id="6" * 64,
                        sequence=4,
                        screenshot_sha256="7" * 64,
                    )
                    spliced = replace(
                        transition,
                        step=2,
                        before=unrelated_before,
                        after=unrelated_after,
                    )
                    return RuntimeResult(
                        status="aborted",
                        success=False,
                        reason="spliced transition history",
                        action_count=2,
                        verified_changed_transitions=2,
                        final_observation=unrelated_after,
                        transitions=(transition, spliced),
                    )
                if first_failure in {"stale", "ambiguous"}:
                    second_bundle = scorm_runtime_authority.classify_observation(after)
                    second_evaluated = scorm_runtime_authority.evaluate_action(
                        second_bundle,
                        after,
                        action,
                    )
                    assert second_evaluated.authorization is not None
                    scorm_runtime_authority.verify_and_consume_action(
                        second_evaluated.authorization,
                        after,
                        action,
                    )
                    second_decision = PlannerDecision(
                        kind="action",
                        reason="retry exact governed assessment control",
                        action=action,
                        expected=expected,
                        scorm_coherence=second_evaluated.decision,
                        action_authorization=second_evaluated.authorization,
                    )
                    second_after = replace(
                        after,
                        observation_id="8" * 64,
                        sequence=3,
                        screenshot_sha256="9" * 64,
                    )
                    second_terminal_bundle = scorm_runtime_authority.classify_observation(second_after)
                    second_transition = RuntimeTransition(
                        step=2,
                        before=after,
                        decision=second_decision,
                        result=ActionResult(
                            True,
                            "gateway_executed",
                            {"scorm_action_authority": (second_evaluated.authorization.audit_dict())},
                            dispatch_state="dispatched",
                        ),
                        after=second_after,
                        screen_changed=True,
                        observation_fresh=True,
                        verified=True,
                        verification_reason="verified",
                    )
                    success_predicate = ObservationPredicate(
                        "vision_contains",
                        "completed successfully",
                    )
                    terminal_decision = PlannerDecision(
                        kind="complete",
                        reason="visible completion is present",
                        success_predicate=success_predicate,
                        scorm_coherence=second_terminal_bundle.preflight,
                    )
                    return RuntimeResult(
                        status="completed",
                        success=True,
                        reason=terminal_decision.reason,
                        action_count=2,
                        verified_changed_transitions=1,
                        final_observation=second_after,
                        transitions=(transition, second_transition),
                        success_predicate=success_predicate,
                        terminal_decision=terminal_decision,
                    )
                success_predicate = ObservationPredicate(
                    "vision_contains",
                    "completed successfully",
                )
                terminal_preflight = scorm_runtime_authority.classify_observation(after).preflight
                terminal_decision = PlannerDecision(
                    kind="complete",
                    reason="visible completion is present",
                    success_predicate=success_predicate,
                    scorm_coherence=terminal_preflight,
                )
                result = RuntimeResult(
                    status="completed",
                    success=True,
                    reason=terminal_decision.reason,
                    human_gate="",
                    pause_kind="",
                    pause_receipt_sha256="",
                    action_count=1,
                    verified_changed_transitions=1,
                    final_observation=after,
                    transitions=(transition,),
                    success_predicate=success_predicate,
                    terminal_decision=terminal_decision,
                )
                if holder.get("spoof_final_observation") is True:
                    forged_observation = replace(
                        result.final_observation,
                        screenshot_sha256="9" * 64,
                    )
                    result = replace(result, final_observation=forged_observation)
                elif holder.get("duplicate_final_observation") is True:
                    result = replace(
                        result,
                        final_observation=replace(result.final_observation),
                    )
                elif holder.get("spoof_final_observation_protocol") is True:
                    source = result.final_observation

                    class FakeFinalObservation:
                        def __init__(self, frame: ScreenObservation) -> None:
                            self.observation_id = frame.observation_id
                            self.sequence = frame.sequence
                            self.captured_at_unix = frame.captured_at_unix
                            self.screenshot_sha256 = frame.screenshot_sha256
                            self.width = frame.width
                            self.height = frame.height
                            self.ocr_text = frame.ocr_text
                            self.vision_text = frame.vision_text
                            self.mime_type = frame.mime_type
                            self.window_handle = frame.window_handle
                            self.window_process_id = frame.window_process_id
                            self.window_title_sha256 = frame.window_title_sha256
                            self.window_rect = frame.window_rect
                            self.cursor_x = frame.cursor_x
                            self.cursor_y = frame.cursor_y
                            self.dpi_x = frame.dpi_x
                            self.dpi_y = frame.dpi_y
                            self.ocr_tokens = frame.ocr_tokens
                            self.stability_profile = frame.stability_profile
                            self.frame_artifact = frame.frame_artifact

                        def __eq__(self, _other: object) -> bool:  # pragma: no cover
                            return True

                    forged_observation = FakeFinalObservation(source)
                    result = replace(result, final_observation=forged_observation)
                holder["runtime_result"] = result
                replay_directory = config.state_directory / f"{config.run_id}.scorm-replay"
                markers = tuple(replay_directory.glob("*.json"))
                if holder.get("delete_replay_marker") is True:
                    assert len(markers) == 1
                    markers[0].unlink()
                elif holder.get("forge_replay_marker") is True:
                    assert len(markers) == 1
                    marker = json.loads(markers[0].read_text(encoding="utf-8"))
                    marker["receipt_sha256"] = "0" * 64
                    markers[0].write_text(
                        json.dumps(
                            marker,
                            sort_keys=True,
                            separators=(",", ":"),
                            ensure_ascii=False,
                            allow_nan=False,
                        )
                        + "\n",
                        encoding="utf-8",
                        newline="",
                    )
                return result

        return FakeOrganism()

    return SCORMCloudRuntimeDependencies(
        preflight_probe=lambda _config: {"ok": True, "desktop_touched": False},
        gateway_factory=gateway_factory,
        native_runtime_factory=native_factory,
        organism_builder=organism_builder,
        utc_now=lambda: NOW,
    )


def test_cli_composes_v3_authorizer_gate_replay_and_runtime_authority(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    holder: dict[str, object] = {}
    edge = executable(tmp_path)
    environment = {
        SCORM_LAUNCH_URL_ENV: SCORM_URL,
        SCORM_SESSION_SIGNING_SECRET_ENV: SESSION_SECRET.decode(),
        SCORM_HNC_SIGNING_SECRET_ENV: HNC_SECRET.decode(),
        SCORM_OWNER_BENCHMARK_SIGNING_SECRET_ENV: OWNER_SECRET.decode(),
        "AUREON_GUI_CAPABILITY_TOKEN": CAPABILITY_TOKEN,
    }

    exit_code = main(
        [
            "--edge-executable",
            str(edge),
            "--profile-mode",
            "isolated",
            "--user-data-dir",
            str(tmp_path / "fresh-profile"),
            "--run-id",
            "hermetic-cli-main-run",
            "--state-directory",
            str(tmp_path / "state"),
            "--max-steps",
            "20",
            "--max-seconds",
            "300",
            "--lease-ttl",
            "600",
            "--planner-timeout",
            "30",
            "--live",
        ],
        environ=environment,
        dependencies=hermetic_dependencies(holder),
    )

    assert exit_code == 0
    assert environment == {}
    public_result = json.loads(capsys.readouterr().out)
    assert public_result["status"] == "completed"
    assert public_result["success"] is True
    assert SCORM_URL not in json.dumps(public_result)
    assert "signed-value-123" not in json.dumps(public_result)
    starter = holder["starter"]
    assert isinstance(starter, HermeticSessionStarter)
    assert len(starter.start_calls) == 1
    assert starter.active is not None
    assert starter.active._closed is True
    receipt = holder["receipt"]
    assert isinstance(receipt, SCORMActionReceipt)
    assert receipt.action_sequence == 1
    replay_markers = list((tmp_path / "state" / "hermetic-cli-main-run.scorm-replay").glob("*.json"))
    assert len(replay_markers) == 1
    evidence = (tmp_path / "state" / "hermetic-cli-main-run.scorm.jsonl").read_text(encoding="utf-8")
    assert SCORM_URL not in evidence
    assert "signed-value-123" not in evidence
    assert "Safe answer" not in evidence


def test_preflight_and_live_gate_fail_before_session_start(tmp_path: Path) -> None:
    config = run_config(tmp_path)
    native_called = False

    def forbidden_native(*_args):
        nonlocal native_called
        native_called = True
        raise AssertionError("session construction must remain unreachable")

    dependencies = SCORMCloudRuntimeDependencies(
        preflight_probe=lambda _config: {"ok": False},
        gateway_factory=lambda _config: (_ for _ in ()).throw(
            AssertionError("gateway must remain unreachable")
        ),
        native_runtime_factory=forbidden_native,
        organism_builder=lambda *_args, **_kwargs: None,
        utc_now=lambda: NOW,
    )

    with pytest.raises(SCORMCloudRunnerError, match="local_dependency_preflight_failed"):
        run_scorm_cloud(
            config,
            launch_url=SCORM_URL,
            session_signing_secret=SESSION_SECRET,
            hnc_signing_secret=HNC_SECRET,
            owner_benchmark_signing_secret=OWNER_SECRET,
            capability_token=CAPABILITY_TOKEN,
            dependencies=dependencies,
        )
    assert native_called is False
    assert not config.state_directory.exists()

    with pytest.raises(SCORMCloudRunnerError, match="live_flag_required"):
        run_scorm_cloud(
            run_config(tmp_path / "not-live", live=False),
            launch_url=SCORM_URL,
            session_signing_secret=SESSION_SECRET,
            hnc_signing_secret=HNC_SECRET,
            owner_benchmark_signing_secret=OWNER_SECRET,
            capability_token=CAPABILITY_TOKEN,
            dependencies=dependencies,
        )

    for invalid_token in ("short", " " + "x" * 32, "x" * 32 + " "):
        with pytest.raises(SCORMCloudRunnerError, match="capability_token_invalid"):
            run_scorm_cloud(
                config,
                launch_url=SCORM_URL,
                session_signing_secret=SESSION_SECRET,
                hnc_signing_secret=HNC_SECRET,
                owner_benchmark_signing_secret=OWNER_SECRET,
                capability_token=invalid_token,
                dependencies=dependencies,
            )
    assert native_called is False


def test_paused_prerequisite_emits_receipt_and_requires_fresh_run(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    holder: dict[str, object] = {}
    base = hermetic_dependencies(holder)

    class PausedOrganism:
        def __init__(
            self,
            frame: ScreenObservation,
            coherence: object,
            pause_checkpoint_store: HashOnlyPauseCheckpointStore,
        ) -> None:
            self.frame = frame
            self.coherence = coherence
            self.pause_checkpoint_store = pause_checkpoint_store

        def run(self):
            terminal = PlannerDecision(
                kind="pause",
                reason="owner login prerequisite",
                pause_kind="login",
                scorm_coherence=self.coherence,
            )
            checkpoint = self.pause_checkpoint_store.create(
                self.frame,
                (),
                pause_kind="login",
            )
            return RuntimeResult(
                status="paused",
                success=False,
                reason=terminal.reason,
                human_gate="",
                pause_kind="login",
                pause_receipt_sha256=checkpoint.checkpoint_sha256,
                action_count=0,
                verified_changed_transitions=0,
                final_observation=self.frame,
                transitions=(),
                terminal_decision=terminal,
            )

    def paused_builder(
        config,
        *,
        capability_token,
        tesseract_executable,
        scorm_runtime_authority,
    ):
        assert capability_token == CAPABILITY_TOKEN
        assert tesseract_executable is None
        binding = scorm_runtime_authority.authorize_binding()
        cloudfront_frame = observation(
            binding,
            words=(
                "ERROR",
                "The",
                "request",
                "could",
                "not",
                "be",
                "satisfied",
                "Generated",
                "by",
                "cloudfront",
            ),
            vision_text=("ERROR The request could not be satisfied. Generated by cloudfront"),
        )
        classified = scorm_runtime_authority.classify_observation(cloudfront_frame)
        assert classified.preflight.kind == RESUMABLE_PAUSE
        assert classified.preflight.prerequisite == "authorization"
        pause_checkpoint_store = HashOnlyPauseCheckpointStore(
            config.pause_checkpoint_path,
            run_id=config.run_id,
            build_id="hermetic-paused-scorm-build",
            goal=config.goal,
            run_authority_sha256=config.scorm_run_authority_sha256,
            control_grant_sha256=config.scorm_control_grant_sha256,
        )
        holder["pause_checkpoint_store"] = pause_checkpoint_store
        return PausedOrganism(
            cloudfront_frame,
            classified.preflight,
            pause_checkpoint_store,
        )

    dependencies = SCORMCloudRuntimeDependencies(
        preflight_probe=base.preflight_probe,
        gateway_factory=base.gateway_factory,
        native_runtime_factory=base.native_runtime_factory,
        organism_builder=paused_builder,
        utc_now=base.utc_now,
    )
    edge = executable(tmp_path)
    environment = {
        SCORM_LAUNCH_URL_ENV: SCORM_URL,
        SCORM_SESSION_SIGNING_SECRET_ENV: SESSION_SECRET.decode(),
        SCORM_HNC_SIGNING_SECRET_ENV: HNC_SECRET.decode(),
        SCORM_OWNER_BENCHMARK_SIGNING_SECRET_ENV: OWNER_SECRET.decode(),
        "AUREON_GUI_CAPABILITY_TOKEN": CAPABILITY_TOKEN,
    }

    exit_code = main(
        [
            "--edge-executable",
            str(edge),
            "--profile-mode",
            "isolated",
            "--user-data-dir",
            str(tmp_path / "fresh-profile"),
            "--run-id",
            "hermetic-paused-prerequisite",
            "--state-directory",
            str(tmp_path / "state"),
            "--max-seconds",
            "300",
            "--lease-ttl",
            "600",
            "--planner-timeout",
            "30",
            "--live",
        ],
        environ=environment,
        dependencies=dependencies,
    )

    assert exit_code == 3
    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "paused_prerequisite"
    assert summary["pause_kind"] == "login"
    pause_checkpoint_store = holder["pause_checkpoint_store"]
    assert isinstance(pause_checkpoint_store, HashOnlyPauseCheckpointStore)
    assert summary["pause_receipt_sha256"] == pause_checkpoint_store.load().checkpoint_sha256
    assert summary["continuation_mode"] == "new_governed_run_after_owner_prerequisite"
    assert summary["success"] is False
    assert "resume" not in runner_module._parser().format_help().casefold()


@pytest.mark.parametrize(
    "runtime_result,error",
    [
        (
            empty_runtime_result(
                status="paused",
                success=True,
                pause_kind="login",
                pause_receipt_sha256="a" * 64,
            ),
            "runtime_result_success_invalid",
        ),
        (
            empty_runtime_result(
                status="completed",
                success=True,
                action_count=0,
                verified_changed_transitions=1,
            ),
            "runtime_result_counts_invalid",
        ),
        (
            completed_result_without_semantic_terminal(),
            "runtime_result_transition_evidence_invalid",
        ),
        (
            empty_runtime_result(
                status="human_required",
                success=False,
                human_gate="",
            ),
            "runtime_result_human_gate_invalid",
        ),
        (
            empty_runtime_result(
                status="human_required",
                success=False,
                human_gate="invented_gate",
            ),
            "runtime_result_human_gate_invalid",
        ),
        (
            empty_runtime_result(
                status="paused",
                success=False,
                human_gate="identity_attestation",
                pause_kind="login",
                pause_receipt_sha256="a" * 64,
            ),
            "runtime_result_human_gate_unexpected",
        ),
        (
            empty_runtime_result(
                status="paused",
                success=False,
                pause_kind="login",
                pause_receipt_sha256="",
            ),
            "runtime_result_pause_receipt_invalid",
        ),
        (
            empty_runtime_result(
                status="paused",
                success=False,
                pause_kind="invented_pause",
                pause_receipt_sha256="a" * 64,
            ),
            "runtime_result_pause_receipt_invalid",
        ),
        (
            empty_runtime_result(
                status="resume_rejected",
                success=False,
            ),
            "runtime_result_status_invalid",
        ),
    ],
)
def test_runtime_result_projection_fails_closed(
    runtime_result,
    error: str,
    tmp_path: Path,
) -> None:
    with pytest.raises(SCORMCloudRunnerError, match=error):
        project_runtime_result(runtime_result, tmp_path)


def test_runtime_projection_rejects_structural_result_imitation(
    tmp_path: Path,
) -> None:
    with pytest.raises(SCORMCloudRunnerError, match="runtime_result_type_invalid"):
        project_runtime_result(
            SimpleNamespace(
                status="completed",
                success=True,
                reason="forged",
                action_count=1,
                verified_changed_transitions=1,
            ),
            tmp_path,
        )


def test_runtime_projection_recomputes_transition_evidence_from_exact_frames(
    tmp_path: Path,
) -> None:
    result = completed_result_without_semantic_terminal()
    transition = result.transitions[0]
    forged = replace(
        transition,
        step=True,
        result=ActionResult(
            False,
            "gateway_stale_source_frame",
            dispatch_state="not_dispatched",
        ),
        observation_fresh=False,
        screen_changed=True,
        verified=True,
    )

    with pytest.raises(
        SCORMCloudRunnerError,
        match="runtime_result_transition_evidence_invalid",
    ):
        project_runtime_result(
            replace(result, transitions=(forged,)),
            tmp_path,
        )


def test_runtime_projection_rejects_final_observation_identity_spoof(tmp_path: Path) -> None:
    holder: dict[str, object] = {"spoof_final_observation": True}

    with pytest.raises(
        SCORMCloudRunnerError,
        match="runtime_result_final_observation_invalid",
    ):
        run_scorm_cloud(
            run_config(tmp_path),
            launch_url=SCORM_URL,
            session_signing_secret=SESSION_SECRET,
            hnc_signing_secret=HNC_SECRET,
            owner_benchmark_signing_secret=OWNER_SECRET,
            capability_token=CAPABILITY_TOKEN,
        dependencies=hermetic_dependencies(holder),
    )


def test_runtime_projection_rejects_final_observation_protocol_spoof(tmp_path: Path) -> None:
    holder: dict[str, object] = {"spoof_final_observation_protocol": True}

    with pytest.raises(
        SCORMCloudRunnerError,
        match="runtime_result_final_observation_invalid",
    ):
        run_scorm_cloud(
            run_config(tmp_path),
            launch_url=SCORM_URL,
            session_signing_secret=SESSION_SECRET,
            hnc_signing_secret=HNC_SECRET,
            owner_benchmark_signing_secret=OWNER_SECRET,
            capability_token=CAPABILITY_TOKEN,
            dependencies=hermetic_dependencies(holder),
        )


def test_runtime_projection_rejects_final_observation_identity_duplicate(tmp_path: Path) -> None:
    holder: dict[str, object] = {"spoof_final_observation": True, "duplicate_final_observation": True}

    with pytest.raises(
        SCORMCloudRunnerError,
        match="runtime_result_final_observation_invalid",
    ):
        run_scorm_cloud(
            run_config(tmp_path),
            launch_url=SCORM_URL,
            session_signing_secret=SESSION_SECRET,
            hnc_signing_secret=HNC_SECRET,
            owner_benchmark_signing_secret=OWNER_SECRET,
            capability_token=CAPABILITY_TOKEN,
            dependencies=hermetic_dependencies(holder),
        )


def test_runtime_projection_accepts_genuine_scorm_unstable_transition_failure(
    tmp_path: Path,
) -> None:
    holder: dict[str, object] = {"return_unstable": True}

    result = run_scorm_cloud(
        run_config(tmp_path),
        launch_url=SCORM_URL,
        session_signing_secret=SESSION_SECRET,
        hnc_signing_secret=HNC_SECRET,
        owner_benchmark_signing_secret=OWNER_SECRET,
        capability_token=CAPABILITY_TOKEN,
        dependencies=hermetic_dependencies(holder),
    )

    assert result.status == "unstable_post_action_frame"
    assert result.success is False


@pytest.mark.parametrize("stripped_field", ["strip_action_authority", "strip_action_audit"])
def test_runtime_projection_requires_scorm_action_authority_and_consumption_audit(
    tmp_path: Path,
    stripped_field: str,
) -> None:
    holder: dict[str, object] = {stripped_field: True}

    with pytest.raises(
        SCORMCloudRunnerError,
        match="runtime_result_transition_evidence_invalid",
    ):
        run_scorm_cloud(
            run_config(tmp_path),
            launch_url=SCORM_URL,
            session_signing_secret=SESSION_SECRET,
            hnc_signing_secret=HNC_SECRET,
            owner_benchmark_signing_secret=OWNER_SECRET,
            capability_token=CAPABILITY_TOKEN,
            dependencies=hermetic_dependencies(holder),
        )


@pytest.mark.parametrize(
    "holder_flag",
    ["tamper_receipt_hmac", "skip_receipt_consumption"],
)
def test_runtime_projection_requires_current_signed_consumed_receipt(
    tmp_path: Path,
    holder_flag: str,
) -> None:
    holder: dict[str, object] = {holder_flag: True}

    with pytest.raises(
        SCORMCloudRunnerError,
        match="runtime_result_transition_provenance_invalid",
    ):
        run_scorm_cloud(
            run_config(tmp_path),
            launch_url=SCORM_URL,
            session_signing_secret=SESSION_SECRET,
            hnc_signing_secret=HNC_SECRET,
            owner_benchmark_signing_secret=OWNER_SECRET,
            capability_token=CAPABILITY_TOKEN,
            dependencies=hermetic_dependencies(holder),
        )


@pytest.mark.parametrize(
    "holder_flag",
    ["delete_replay_marker", "forge_replay_marker"],
)
def test_runtime_projection_rereads_exact_signed_replay_marker(
    tmp_path: Path,
    holder_flag: str,
) -> None:
    holder: dict[str, object] = {holder_flag: True}

    with pytest.raises(
        SCORMCloudRunnerError,
        match="runtime_result_transition_provenance_invalid",
    ):
        run_scorm_cloud(
            run_config(tmp_path),
            launch_url=SCORM_URL,
            session_signing_secret=SESSION_SECRET,
            hnc_signing_secret=HNC_SECRET,
            owner_benchmark_signing_secret=OWNER_SECRET,
            capability_token=CAPABILITY_TOKEN,
            dependencies=hermetic_dependencies(holder),
        )


def test_runtime_projection_rejects_unreported_consumed_action(
    tmp_path: Path,
) -> None:
    holder: dict[str, object] = {"return_without_transition": True}

    with pytest.raises(
        SCORMCloudRunnerError,
        match="runtime_result_transition_replay_invalid",
    ):
        run_scorm_cloud(
            run_config(tmp_path),
            launch_url=SCORM_URL,
            session_signing_secret=SESSION_SECRET,
            hnc_signing_secret=HNC_SECRET,
            owner_benchmark_signing_secret=OWNER_SECRET,
            capability_token=CAPABILITY_TOKEN,
            dependencies=hermetic_dependencies(holder),
        )


def test_runtime_projection_rejects_genuine_result_from_different_run(
    tmp_path: Path,
) -> None:
    run_a_holder: dict[str, object] = {}
    run_a = run_scorm_cloud(
        run_config(tmp_path / "run-a", run_id="hermetic-run-a"),
        launch_url=SCORM_URL,
        session_signing_secret=SESSION_SECRET,
        hnc_signing_secret=HNC_SECRET,
        owner_benchmark_signing_secret=OWNER_SECRET,
        capability_token=CAPABILITY_TOKEN,
        dependencies=hermetic_dependencies(run_a_holder),
    )
    assert run_a.status == "completed"
    foreign_result = run_a_holder["runtime_result"]
    assert isinstance(foreign_result, RuntimeResult)
    run_b_holder: dict[str, object] = {
        "injected_runtime_result": foreign_result,
    }

    with pytest.raises(
        SCORMCloudRunnerError,
        match="runtime_result_transition_provenance_invalid",
    ):
        run_scorm_cloud(
            run_config(tmp_path / "run-b", run_id="hermetic-run-b"),
            launch_url=SCORM_URL,
            session_signing_secret=SESSION_SECRET,
            hnc_signing_secret=HNC_SECRET,
            owner_benchmark_signing_secret=OWNER_SECRET,
            capability_token=CAPABILITY_TOKEN,
            dependencies=hermetic_dependencies(run_b_holder),
        )


def test_runtime_projection_rejects_spliced_scorm_transition_chain(
    tmp_path: Path,
) -> None:
    holder: dict[str, object] = {"return_spliced": True}
    with pytest.raises(
        SCORMCloudRunnerError,
        match="runtime_result_transition_evidence_invalid",
    ):
        run_scorm_cloud(
            run_config(tmp_path),
            launch_url=SCORM_URL,
            session_signing_secret=SESSION_SECRET,
            hnc_signing_secret=HNC_SECRET,
            owner_benchmark_signing_secret=OWNER_SECRET,
            capability_token=CAPABILITY_TOKEN,
            dependencies=hermetic_dependencies(holder),
        )


def test_runtime_projection_rejects_duplicate_consumed_scorm_receipt(
    tmp_path: Path,
) -> None:
    holder: dict[str, object] = {"return_duplicate_receipt": True}

    with pytest.raises(
        SCORMCloudRunnerError,
        match=("runtime_result_transition_evidence_invalid|runtime_result_transition_replay_invalid"),
    ):
        run_scorm_cloud(
            run_config(tmp_path),
            launch_url=SCORM_URL,
            session_signing_secret=SESSION_SECRET,
            hnc_signing_secret=HNC_SECRET,
            owner_benchmark_signing_secret=OWNER_SECRET,
            capability_token=CAPABILITY_TOKEN,
            dependencies=hermetic_dependencies(holder),
        )


def test_runtime_projection_allows_exact_stale_retry_with_fresh_scorm_sequence(
    tmp_path: Path,
) -> None:
    holder: dict[str, object] = {"first_failure": "stale"}

    result = run_scorm_cloud(
        run_config(tmp_path),
        launch_url=SCORM_URL,
        session_signing_secret=SESSION_SECRET,
        hnc_signing_secret=HNC_SECRET,
        owner_benchmark_signing_secret=OWNER_SECRET,
        capability_token=CAPABILITY_TOKEN,
        dependencies=hermetic_dependencies(holder),
    )

    assert result.status == "completed"
    assert result.action_count == 2
    assert result.verified_changed_transitions == 1


def test_runtime_projection_rejects_ambiguous_failure_followed_by_success(
    tmp_path: Path,
) -> None:
    holder: dict[str, object] = {"first_failure": "ambiguous"}

    with pytest.raises(
        SCORMCloudRunnerError,
        match="runtime_result_transition_terminal_failure_invalid",
    ):
        run_scorm_cloud(
            run_config(tmp_path),
            launch_url=SCORM_URL,
            session_signing_secret=SESSION_SECRET,
            hnc_signing_secret=HNC_SECRET,
            owner_benchmark_signing_secret=OWNER_SECRET,
            capability_token=CAPABILITY_TOKEN,
            dependencies=hermetic_dependencies(holder),
        )


def test_entrypoint_redacts_unexpected_operational_failure(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    edge = executable(tmp_path)
    environment = {
        SCORM_LAUNCH_URL_ENV: SCORM_URL,
        SCORM_SESSION_SIGNING_SECRET_ENV: SESSION_SECRET.decode(),
        SCORM_HNC_SIGNING_SECRET_ENV: HNC_SECRET.decode(),
        SCORM_OWNER_BENCHMARK_SIGNING_SECRET_ENV: OWNER_SECRET.decode(),
        "AUREON_GUI_CAPABILITY_TOKEN": CAPABILITY_TOKEN,
    }

    def unexpected_failure(_config):
        raise RuntimeError("signed-value-123 must never reach stderr")

    exit_code = entrypoint(
        [
            "--edge-executable",
            str(edge),
            "--profile-mode",
            "isolated",
            "--user-data-dir",
            str(tmp_path / "fresh-profile"),
            "--state-directory",
            str(tmp_path / "state"),
            "--live",
        ],
        environ=environment,
        dependencies=SCORMCloudRuntimeDependencies(
            preflight_probe=unexpected_failure,
        ),
    )

    assert exit_code == 2
    error = capsys.readouterr().err
    assert json.loads(error) == {"ok": False, "error": "scorm_runtime_failed"}
    assert "signed-value-123" not in error


def test_production_dependencies_are_concrete() -> None:
    dependencies = SCORMCloudRuntimeDependencies()

    assert dependencies.preflight_probe.__name__ == "_production_preflight"
    assert dependencies.gateway_factory.__name__ == "_production_gateway"
    assert dependencies.native_runtime_factory.__name__ == "_production_native_runtime"
    assert dependencies.organism_builder.__name__ == "build_local_organism"


@pytest.mark.parametrize(
    "title",
    [
        "Course - SCORM Cloud - Microsoft Edge",
        "SCORM Cloud - Sign In - Microsoft Edge",
        "ERROR: The request could not be satisfied - Microsoft Edge",
        "Access Denied - Microsoft Edge",
        "403 Forbidden - Microsoft Edge",
    ],
)
def test_default_title_policy_admits_only_exact_scorm_or_cloudfront_gate(
    title: str,
) -> None:
    assert runner_module.re.fullmatch(runner_module.DEFAULT_TITLE_REGEX, title)


@pytest.mark.parametrize(
    "title",
    [
        "Unrelated Course - Microsoft Edge",
        "Course - SCORM Cloud - Microsoft Edge - injected",
        "ERROR: The request could not be satisfied - Microsoft Edge - injected",
        "prefix ERROR: The request could not be satisfied - Microsoft Edge",
    ],
)
def test_default_title_policy_rejects_unrelated_or_suffixed_titles(title: str) -> None:
    assert runner_module.re.fullmatch(runner_module.DEFAULT_TITLE_REGEX, title) is None


def test_production_preflight_requires_all_native_scorm_dependencies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = run_config(tmp_path)
    monkeypatch.setattr(
        runner_module,
        "preflight_local_gui",
        lambda **_kwargs: {"ok": True, "desktop_touched": False},
    )
    monkeypatch.setattr(runner_module.sys, "platform", "win32")
    monkeypatch.setattr(
        runner_module.importlib.util,
        "find_spec",
        lambda name: None if name == "comtypes" else object(),
    )

    missing = runner_module._production_preflight(config)

    assert missing["ok"] is False
    assert missing["scorm_native"] == {
        "ok": False,
        "checks": {
            "comtypes": False,
            "pillow": True,
            "psutil": True,
            "windows": True,
        },
    }

    monkeypatch.setattr(
        runner_module.importlib.util,
        "find_spec",
        lambda _name: object(),
    )
    assert runner_module._production_preflight(config)["ok"] is True
