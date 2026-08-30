from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from aureon.autonomous.vm_control import VMControlDispatcher
from aureon.code_architect.executor import SkillExecutor
from aureon.code_architect.requirement_skill_builder import RequirementSkillBuilder
from aureon.code_architect.skill import Skill, SkillLevel, SkillStatus
from aureon.code_architect.skill_library import SkillLibrary
from aureon.core.aureon_cognitive_authoring_loop import CognitiveAuthoringLoop


def _course_plan(name: str = "complete_training_step") -> dict:
    return {
        "name": name,
        "description": "Rehearse a bounded training-page interaction using GUI primitives.",
        "steps": [
            {"primitive": "screenshot", "params": {}},
            {"primitive": "mouse_move", "params": {"x": 640, "y": 480}},
            {"primitive": "left_click", "params": {"x": 640, "y": 480}},
            {
                "primitive": "type_text",
                "params": {"text": {"input": "response_text", "default": "training response"}},
            },
            {"primitive": "press_key", "params": {"key": "enter"}},
        ],
        "sample_inputs": {"response_text": "simulated answer"},
    }


def test_requirement_builder_renders_validates_and_stages_without_live_activation(tmp_path: Path) -> None:
    library = SkillLibrary(storage_dir=tmp_path / "skills")
    builder = RequirementSkillBuilder(library=library)

    result = builder.build(
        "Create a reusable bounded training-page interaction.",
        plan=_course_plan(),
    )

    assert result["ok"] is True
    assert result["status"] == "validated_pending_approval"
    assert result["validation"]["compile_ok"] is True
    assert result["validation"]["static_safe"] is True
    assert result["validation"]["simulation_ok"] is True
    assert result["live_execution_enabled"] is False

    skill = library.get("complete_training_step")
    assert skill is not None
    assert skill.status is SkillStatus.VALIDATED
    assert "requires_explicit_approval" in skill.tags
    assert "live_execution_disabled" in skill.tags
    assert "execute_shell" not in skill.code
    assert "vm_type_text" in skill.code
    assert skill.execution_count == 0

    dispatcher = VMControlDispatcher()
    session_id = dispatcher.create_session(backend="simulated", make_default=True)
    dispatcher.get_session(session_id).arm(dry_run=False)
    executor = SkillExecutor(library=library, dispatcher=dispatcher)
    held = executor.execute(skill, params={"session_id": session_id})
    assert held.ok is False
    assert held.error == "skill_approval_required"

    approval = builder.approve_skill(skill.name, reviewer="unit-test")
    assert approval["ok"] is True
    assert approval["live_execution_enabled"] is False
    approved = library.get(skill.name)
    assert approved is not None
    rehearsed = executor.execute(approved, params={"session_id": session_id})
    assert rehearsed.ok is True

    live_dispatcher = SimpleNamespace(
        get_session=lambda _session_id=None: SimpleNamespace(
            session=SimpleNamespace(backend="winrm")
        )
    )
    live_executor = SkillExecutor(library=library, dispatcher=live_dispatcher)
    live_held = live_executor.execute(approved)
    assert live_held.ok is False
    assert live_held.error == "skill_live_execution_disabled"

    live_approval = builder.approve_skill(skill.name, reviewer="unit-test", enable_live=True)
    assert live_approval["ok"] is True
    assert live_approval["live_execution_enabled"] is True
    assert "live_execution_disabled" not in library.get(skill.name).tags
    dispatcher.destroy_all()


def test_requirement_builder_rejects_non_json_and_non_allowlisted_actions(tmp_path: Path) -> None:
    library = SkillLibrary(storage_dir=tmp_path / "skills")
    builder = RequirementSkillBuilder(library=library)
    plan = _course_plan("strict_json_skill")

    trailing = builder.build(
        "Build a bounded GUI skill.",
        plan=json.dumps(plan) + "\nPython follows",
    )
    assert trailing["ok"] is False
    assert trailing["reason"] == "strict_json_plan_required"

    unsafe_plan = _course_plan("unsafe_shell_skill")
    unsafe_plan["steps"] = [{"primitive": "execute_shell", "params": {"command": "whoami"}}]
    unsafe = builder.build("Build a bounded GUI skill.", plan=unsafe_plan)
    assert unsafe["ok"] is False
    assert unsafe["reason"] == "step_0_primitive_not_allowlisted"
    assert len(library) == 0


def test_requirement_builder_rejects_failed_simulated_rehearsal(
    tmp_path: Path,
    monkeypatch,
) -> None:
    library = SkillLibrary(storage_dir=tmp_path / "skills")
    builder = RequirementSkillBuilder(library=library)
    monkeypatch.setattr(
        VMControlDispatcher,
        "dispatch",
        lambda *args, **kwargs: {"ok": False, "error": "forced simulated failure"},
    )

    result = builder.build(
        "Create a bounded GUI skill.",
        plan=_course_plan("failed_rehearsal"),
    )

    assert result["ok"] is False
    assert result["status"] == "validation_failed"
    assert result["validation"]["simulation_ok"] is False
    assert result["validation"]["simulation_error"] == "simulated_skill_reported_failure"
    assert library.get("failed_rehearsal") is None


def test_requirement_builder_restores_library_snapshot_when_commit_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    library = SkillLibrary(storage_dir=tmp_path / "skills")
    baseline = Skill(
        name="baseline_skill",
        description="existing",
        level=SkillLevel.TASK,
        code="def baseline_skill(**kwargs):\n    return {'ok': True}\n",
        entry_function="baseline_skill",
        status=SkillStatus.VALIDATED,
    )
    library.add(baseline)
    before = library.library_path.read_bytes()
    builder = RequirementSkillBuilder(library=library)

    def broken_save() -> None:
        library.library_path.write_text("{broken", encoding="utf-8")
        raise OSError("forced save failure")

    monkeypatch.setattr(library, "save", broken_save)
    result = builder.build(
        "Create a bounded GUI skill and preserve the registry on failure.",
        plan=_course_plan("rollback_candidate"),
    )

    assert result["ok"] is False
    assert result["status"] == "library_commit_failed"
    assert result["rolled_back"] is True
    assert library.get("rollback_candidate") is None
    assert library.get("baseline_skill") is not None
    assert library.library_path.read_bytes() == before


def test_requirement_builder_detects_silent_approval_save_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    library = SkillLibrary(storage_dir=tmp_path / "skills")
    builder = RequirementSkillBuilder(library=library)
    built = builder.build("Create a bounded GUI skill.", plan=_course_plan("approval_rollback"))
    assert built["ok"] is True
    before = library.library_path.read_bytes()

    monkeypatch.setattr(library, "save", lambda: None)
    approval = builder.approve_skill("approval_rollback", reviewer="unit-test")

    assert approval["ok"] is False
    assert approval["status"] == "approval_commit_failed"
    assert approval["rolled_back"] is True
    restored = library.get("approval_rollback")
    assert restored is not None
    assert restored.status is SkillStatus.VALIDATED
    assert "live_execution_disabled" in restored.tags
    assert library.library_path.read_bytes() == before


def test_requirement_builder_rejection_removes_staged_skill_atomically(tmp_path: Path) -> None:
    library = SkillLibrary(storage_dir=tmp_path / "skills")
    builder = RequirementSkillBuilder(library=library)
    built = builder.build("Create a bounded GUI skill.", plan=_course_plan("reject_me"))
    assert built["ok"] is True

    rejected = builder.reject_skill("reject_me", reviewer="unit-test", reason="not required")

    assert rejected["ok"] is True
    assert rejected["status"] == "removed_rejected_skill"
    assert library.get("reject_me") is None
    payload = json.loads(library.library_path.read_text(encoding="utf-8"))
    assert all(item["name"] != "reject_me" for item in payload["skills"])


def test_executor_never_runs_proposed_pending_rejected_or_blocked_statuses(tmp_path: Path) -> None:
    library = SkillLibrary(storage_dir=tmp_path / "skills")
    skill = Skill(
        name="status_gate_skill",
        description="status gate",
        level=SkillLevel.TASK,
        code="def status_gate_skill(**kwargs):\n    return {'ok': True}\n",
        entry_function="status_gate_skill",
    )
    library.add(skill)
    executor = SkillExecutor(library=library)

    for status in (SkillStatus.PROPOSED, "pending", "rejected", SkillStatus.BLOCKED):
        skill.status = status  # type: ignore[assignment]
        result = executor.execute(skill)
        assert result.ok is False
        assert str(result.error).startswith("skill_status_not_executable:")


class _RecordingObserver:
    def __init__(self) -> None:
        self.actions = []

    def record_action(self, **kwargs) -> None:
        self.actions.append(kwargs)


def test_authoring_loop_ingests_each_dispatcher_history_item_once() -> None:
    dispatcher = VMControlDispatcher()
    session_id = dispatcher.create_session(backend="simulated", make_default=True)
    controller = dispatcher.get_session(session_id)
    controller.arm(dry_run=False)
    dispatcher.dispatch("screenshot", session_id=session_id)
    dispatcher.dispatch("mouse_move", {"x": 10, "y": 20}, session_id=session_id)
    observer = _RecordingObserver()
    loop = CognitiveAuthoringLoop()
    loop.architect = SimpleNamespace(
        executor=SimpleNamespace(dispatcher=dispatcher),
        observer=observer,
    )

    assert loop._ingest_dispatcher_history() == 2
    assert loop._ingest_dispatcher_history() == 0
    dispatcher.dispatch("left_click", {"x": 10, "y": 20}, session_id=session_id)
    assert loop._ingest_dispatcher_history() == 1
    assert [item["action"] for item in observer.actions] == ["screenshot", "mouse_move", "left_click"]
    dispatcher.destroy_all()


class _FakeRequirementBuilder:
    def __init__(self) -> None:
        self.build_calls = []
        self.approve_calls = []
        self.reject_calls = []

    def build(self, requirement, **kwargs):
        self.build_calls.append((requirement, kwargs))
        return {"ok": True, "skill_name": "staged_skill", "status": "validated_pending_approval"}

    def approve_skill(self, name, **kwargs):
        self.approve_calls.append((name, kwargs))
        return {"ok": True, "skill_name": name, "live_execution_enabled": kwargs["enable_live"]}

    def reject_skill(self, name, **kwargs):
        self.reject_calls.append((name, kwargs))
        return {"ok": True, "skill_name": name, "status": "removed_rejected_skill"}


def test_authoring_loop_requirement_handlers_are_explicit_and_live_off_by_default() -> None:
    builder = _FakeRequirementBuilder()
    staged_skill = SimpleNamespace(
        name="staged_skill",
        level=SkillLevel.TASK,
        status=SkillStatus.VALIDATED,
        category="requirement_generated",
        queen_verdict="",
        pillar_alignment_score=0.0,
    )
    library = SimpleNamespace(get=lambda name: staged_skill if name == "staged_skill" else None)
    loop = CognitiveAuthoringLoop()
    loop.requirement_builder = builder
    loop.architect = SimpleNamespace(library=library)

    missing_plan = loop.submit({"kind": "requirement_skill", "requirement": "Build a GUI task"})
    assert missing_plan["ok"] is False
    assert builder.build_calls == []

    staged = loop.submit(
        {
            "kind": "requirement_skill",
            "requirement": "Build a GUI task",
            "plan": _course_plan("staged_skill"),
        }
    )
    assert staged["ok"] is True
    assert loop.status.requirement_skills_staged == 1

    approved = loop.submit(
        {"kind": "approve_skill", "name": "staged_skill", "reviewer": "unit-test"}
    )
    assert approved["ok"] is True
    assert approved["live_execution_enabled"] is False
    assert builder.approve_calls[-1][1]["enable_live"] is False

    rejected = loop.submit(
        {"kind": "reject_skill", "name": "staged_skill", "reviewer": "unit-test"}
    )
    assert rejected["ok"] is True
    assert builder.reject_calls[-1][0] == "staged_skill"
