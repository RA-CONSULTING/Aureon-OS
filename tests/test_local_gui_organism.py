from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from aureon.operator.course_benchmark_ledger import CourseBenchmarkLedger
from aureon.operator.local_gui_observer import OCRToken, ScreenObservation
from aureon.operator.local_gui_organism import (
    ACTOR_ID,
    LocalGUIOrganism,
    LocalGUIOrganismConfig,
    OrganismConfigurationError,
    build_local_organism,
    preflight_local_gui,
)
from aureon.operator.local_gui_runtime import (
    ActionResult,
    GuiAction,
    ObservationPredicate,
    PlannerDecision,
)


def _observation(sequence: int, text: str, image: bytes) -> ScreenObservation:
    return ScreenObservation(
        observation_id=hashlib.sha256(f"observation:{sequence}".encode()).hexdigest(),
        sequence=sequence,
        captured_at_unix=float(sequence),
        screenshot_sha256=hashlib.sha256(image).hexdigest(),
        width=800,
        height=600,
        ocr_tokens=(OCRToken(text=text, x=10, y=10, width=300, height=30),),
    )


class _SequenceObserver:
    def __init__(self, observations: list[ScreenObservation]) -> None:
        self.observations = observations
        self.index = 0

    def observe(self) -> ScreenObservation:
        observation = self.observations[min(self.index, len(self.observations) - 1)]
        self.index += 1
        return observation


class _SandboxPlanner:
    locality = "local"

    def plan(self, _goal, _observation, history):
        if not history:
            return PlannerDecision(
                kind="action",
                reason="Activate the synthetic sandbox control.",
                action=GuiAction("left_click", {"x": 20, "y": 20}),
                expected=ObservationPredicate("screen_changed"),
            )
        return PlannerDecision(
            kind="complete",
            reason="The synthetic completion marker is visible.",
            success_predicate=ObservationPredicate(
                "ocr_contains",
                "SANDBOX COURSE COMPLETE",
            ),
        )


class _SuccessfulExecutor:
    def execute(
        self,
        _action: GuiAction,
        *,
        source_observation: ScreenObservation | None = None,
    ) -> ActionResult:
        assert source_observation is not None
        return ActionResult(True, "governed_test_execution")


class _LifecycleGateway:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.emergency = False

    def bind_target_window(self, title, *, expected_process_id=None):
        self.calls.append(("bind", (title, expected_process_id)))
        return SimpleNamespace(binding_id="exact-test-binding")

    def authorize_live(self, token, **kwargs):
        self.calls.append(("authorize", (token, kwargs)))
        return SimpleNamespace(lease_id="test-lease")

    def disarm(self, reason="") -> None:
        self.calls.append(("disarm", reason))

    def emergency_stop(self, reason="") -> int:
        self.emergency = True
        self.calls.append(("emergency", reason))
        return 1

    def status(self):
        return {"emergency_stopped": self.emergency}


def test_config_blocks_assessment_answering_and_identity_impersonation(tmp_path: Path) -> None:
    common = {
        "expected_window_title": "Aureon Local Sandbox",
        "allowed_actions": ("move", "click"),
        "state_directory": tmp_path,
    }
    with pytest.raises(
        OrganismConfigurationError,
        match="certification_assessment_goal_blocked",
    ):
        LocalGUIOrganismConfig(goal="Answer every certification exam question", **common)
    with pytest.raises(
        OrganismConfigurationError,
        match="identity_impersonation_goal_blocked",
    ):
        LocalGUIOrganismConfig(goal="Pretend to be John Brown", **common)

    safe = LocalGUIOrganismConfig(
        goal="Navigate the local lesson and stop if an assessment is detected",
        **common,
    )
    assert safe.authorization_label == "sandbox_test"
    assert safe.ledger_path.parent == tmp_path.resolve()

    with pytest.raises(OrganismConfigurationError, match="planner_timeout_must_fit_runtime"):
        LocalGUIOrganismConfig(
            goal="Navigate a local lesson",
            planner_kind="ollama",
            planner_timeout_seconds=56,
            max_seconds=60,
            **common,
        )

    suite = tmp_path / "courseops-suite"
    suite.mkdir()
    (suite / "index.html").write_text("synthetic course", encoding="utf-8")
    synthetic = LocalGUIOrganismConfig(
        goal="Answer every synthetic certification assessment in the sealed local suite",
        synthetic_assessment_asset_root=suite,
        synthetic_assessment_loopback_port=8765,
        synthetic_assessment_server_pid=1234,
        synthetic_assessment_nonce="synthetic-config-nonce-0001",
        **common,
    )
    assert synthetic.synthetic_assessment_enabled is True
    assert synthetic.synthetic_assessment_asset_root == suite.resolve()
    assert synthetic.frame_artifact_directory.name.endswith(".frames")

    courseops = LocalGUIOrganismConfig(
        goal="Complete every sealed synthetic CourseOps assessment",
        planner_kind="courseops",
        synthetic_assessment_asset_root=suite,
        synthetic_assessment_loopback_port=8765,
        synthetic_assessment_server_pid=1234,
        synthetic_assessment_nonce="synthetic-courseops-nonce-0001",
        **common,
    )
    assert courseops.planner_kind == "courseops"

    with pytest.raises(
        OrganismConfigurationError,
        match="synthetic_assessment_context_incomplete",
    ):
        LocalGUIOrganismConfig(
            goal="Answer the synthetic certification assessment",
            synthetic_assessment_asset_root=suite,
            **common,
        )

    with pytest.raises(
        OrganismConfigurationError,
        match="owner_benchmark_test_requires_scorm_vision",
    ):
        LocalGUIOrganismConfig(
            goal="Navigate a local lesson",
            authorization_label="owner_benchmark_test",
            **common,
        )


def test_courseops_build_uses_single_pass_bound_window_ocr(tmp_path: Path, monkeypatch) -> None:
    import aureon.operator.local_gui_organism as module

    suite = tmp_path / "courseops-suite"
    suite.mkdir()
    (suite / "index.html").write_text("sealed local course", encoding="utf-8")
    executable = tmp_path / "tesseract.exe"
    executable.write_bytes(b"test executable")
    gateway = _LifecycleGateway()
    monkeypatch.setattr(module, "get_governed_desktop_gateway", lambda **_kwargs: gateway)
    config = LocalGUIOrganismConfig(
        goal="Complete every sealed synthetic CourseOps assessment",
        expected_window_title="CourseOps 21 Synthetic Safety Academy",
        allowed_actions=("move", "click", "scroll"),
        planner_kind="courseops",
        run_id="courseops-crop-test",
        state_directory=tmp_path / "state",
        synthetic_assessment_asset_root=suite,
        synthetic_assessment_loopback_port=8765,
        synthetic_assessment_server_pid=1234,
        synthetic_assessment_nonce="synthetic-courseops-crop-test-0001",
    )

    organism = build_local_organism(
        config,
        capability_token="test-token",
        synthetic_assessment_secret=b"s" * 32,
        tesseract_executable=executable,
    )

    ocr_backend = organism.observer._ocr_backend
    assert ocr_backend.crop_to_bound_window is True
    assert ocr_backend.page_segmentation_modes == (None,)


def test_preflight_is_local_and_does_not_touch_desktop(tmp_path: Path, monkeypatch) -> None:
    import aureon.operator.local_gui_organism as module

    executable = tmp_path / "tesseract.exe"
    executable.write_bytes(b"test")
    monkeypatch.setattr(module, "discover_tesseract_executable", lambda _value=None: executable)
    monkeypatch.setattr(module.importlib.util, "find_spec", lambda _name: object())

    result = preflight_local_gui(
        model="local-test-model",
        endpoint="http://127.0.0.1:11434",
        ollama_probe=lambda **_kwargs: {
            "ok": True,
            "reason": "ready",
            "endpoint": "http://127.0.0.1:11434",
        },
    )

    assert result["ok"] is True
    assert result["desktop_touched"] is False
    assert result["cloud_used"] is False
    assert result["pyautogui"]["imported"] is False


def test_process_gateway_reuses_one_authority_and_rejects_evidence_split(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import aureon.autonomous.aureon_governed_desktop_gateway as gateway_module

    monkeypatch.setattr(gateway_module, "_gateway_singleton", None)
    first = gateway_module.get_governed_desktop_gateway(evidence_path=tmp_path / "one.jsonl")
    same = gateway_module.get_governed_desktop_gateway(evidence_path=tmp_path / "one.jsonl")
    assert same is first

    with pytest.raises(gateway_module.DesktopGatewayError, match="evidence_path_mismatch"):
        gateway_module.get_governed_desktop_gateway(evidence_path=tmp_path / "two.jsonl")


def test_organism_owns_authorize_bind_run_evidence_and_disarm_lifecycle(tmp_path: Path) -> None:
    token = "one-time-test-capability-token"
    goal = "Complete the fully local synthetic lesson"
    title = "Aureon Local Course Benchmark"
    config = LocalGUIOrganismConfig(
        goal=goal,
        expected_window_title=title,
        allowed_actions=("move", "click"),
        live=True,
        run_id="local-organism-test",
        state_directory=tmp_path,
    )
    ledger = CourseBenchmarkLedger(
        config.ledger_path,
        actor=ACTOR_ID,
        runtime_id="test-runtime",
        build_id="test-build",
        run_id=config.run_id,
    )
    gateway = _LifecycleGateway()
    observer = _SequenceObserver(
        [
            _observation(1, "START LOCAL SANDBOX", b"before"),
            _observation(2, "START LOCAL SANDBOX", b"before"),
            _observation(3, "SANDBOX COURSE COMPLETE", b"after"),
            _observation(4, "SANDBOX COURSE COMPLETE", b"after"),
        ]
    )
    organism = LocalGUIOrganism(
        config,
        gateway=gateway,  # type: ignore[arg-type]
        observer=observer,
        planner=_SandboxPlanner(),
        ledger=ledger,
        capability_token=token,
        executor_factory=lambda _gateway, binding_id: (
            _SuccessfulExecutor() if binding_id == "exact-test-binding" else None
        ),
    )

    result = organism.run()

    assert result.success is True
    assert result.status == "completed"
    assert result.action_count == 1
    assert result.verified_changed_transitions == 1
    assert [call[0] for call in gateway.calls] == ["bind", "authorize", "disarm"]
    authorized_token, authorization = gateway.calls[1][1]
    assert authorized_token == token
    assert authorization["subject"] == ACTOR_ID
    assert "observe" not in authorization["allowed_actions"]

    entries = CourseBenchmarkLedger.verify(config.ledger_path)
    assert [entry["event_type"] for entry in entries] == [
        "runtime_start",
        "gui_transition",
        "runtime_terminal",
    ]
    raw_ledger = config.ledger_path.read_text(encoding="utf-8")
    assert token not in raw_ledger
    assert goal not in raw_ledger
    assert title not in raw_ledger


def test_run_requires_live_flag_and_environment_token(tmp_path: Path) -> None:
    base = {
        "goal": "Navigate a local sandbox",
        "expected_window_title": "Aureon Sandbox",
        "allowed_actions": ("move", "click"),
        "run_id": "missing-authority",
        "state_directory": tmp_path,
    }
    ledger = CourseBenchmarkLedger(
        tmp_path / "missing-authority.course.jsonl",
        actor=ACTOR_ID,
        runtime_id="test-runtime",
        build_id="test-build",
        run_id="missing-authority",
    )
    gateway = _LifecycleGateway()

    dry = LocalGUIOrganism(
        LocalGUIOrganismConfig(**base),
        gateway=gateway,  # type: ignore[arg-type]
        observer=_SequenceObserver([_observation(1, "sandbox", b"one")]),
        planner=_SandboxPlanner(),
        ledger=ledger,
        capability_token="token",
    )
    with pytest.raises(OrganismConfigurationError, match="live_flag_required"):
        dry.run()
    assert gateway.calls == []

    no_token = LocalGUIOrganism(
        LocalGUIOrganismConfig(**base, live=True),
        gateway=gateway,  # type: ignore[arg-type]
        observer=_SequenceObserver([_observation(1, "sandbox", b"one")]),
        planner=_SandboxPlanner(),
        ledger=ledger,
        capability_token="",
    )
    with pytest.raises(OrganismConfigurationError, match="capability_token_environment_required"):
        no_token.run()
    assert gateway.calls == []


def test_emergency_stop_invalidates_gateway_and_runtime(tmp_path: Path) -> None:
    config = LocalGUIOrganismConfig(
        goal="Navigate a local sandbox",
        expected_window_title="Aureon Sandbox",
        allowed_actions=("move", "click"),
        live=True,
        state_directory=tmp_path,
    )
    ledger = CourseBenchmarkLedger(
        config.ledger_path,
        actor=ACTOR_ID,
        runtime_id="test-runtime",
        build_id="test-build",
        run_id=config.run_id,
    )
    gateway = _LifecycleGateway()
    organism = LocalGUIOrganism(
        config,
        gateway=gateway,  # type: ignore[arg-type]
        observer=_SequenceObserver([_observation(1, "sandbox", b"one")]),
        planner=_SandboxPlanner(),
        ledger=ledger,
        capability_token="token",
    )
    stop_calls: list[bool] = []
    organism._runtime = SimpleNamespace(request_emergency_stop=lambda: stop_calls.append(True))

    organism.request_emergency_stop("unit_test")

    assert stop_calls == [True]
    assert gateway.emergency is True
    assert gateway.calls == [("emergency", "unit_test")]
