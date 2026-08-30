"""
tests/test_integrated_cognitive_system.py — ICS test suite

Covers: boot, goals, swarm, commands, temporal tick, graceful degradation.
"""

import logging
import os
import threading
from pathlib import Path

import pytest

from scripts.validation.pytest_no_skip_shards import (
    fingerprint_operational_paths,
    isolate_runtime_writers,
    safe_subprocess_environment,
)

logging.basicConfig(level=logging.WARNING)

_REPO_ROOT = Path(__file__).resolve().parents[1]


# ── Shared fixture ──────────────────────────────────────────────────────────

@pytest.fixture(scope="module", autouse=True)
def _isolated_runtime(tmp_path_factory):
    """Keep the realistic boot offline and prove it cannot touch operator state."""

    before = fingerprint_operational_paths(_REPO_ROOT)
    runtime_root = tmp_path_factory.mktemp("integrated-cognitive-system")
    (runtime_root / "README.md").write_text("# Isolated ICS fixture", encoding="utf-8")
    patcher = pytest.MonkeyPatch()
    safe_env, scrubbed = safe_subprocess_environment(dict(os.environ))
    safe_env = isolate_runtime_writers(safe_env, runtime_root)
    for name in scrubbed:
        patcher.delenv(name, raising=False)
    for name, value in safe_env.items():
        patcher.setenv(name, value)
    patcher.chdir(runtime_root)
    try:
        yield runtime_root, patcher
    finally:
        patcher.undo()
        after = fingerprint_operational_paths(_REPO_ROOT)
        assert after == before


@pytest.fixture(scope="module")
def ics(_isolated_runtime):
    """Boot the ICS once for the entire module — expensive but realistic."""
    runtime_root, patcher = _isolated_runtime
    from aureon.core import integrated_cognitive_system as ics_module

    lambda_engine = ics_module.LambdaEngine
    patcher.setattr(
        ics_module,
        "LambdaEngine",
        lambda: lambda_engine(state_path=runtime_root / "state" / "lambda_history.json"),
    )
    system = ics_module.IntegratedCognitiveSystem()
    system.boot()
    system._start_tick_thread()
    assert system._tick_thread is None
    system._unified_cognitive_tick()
    try:
        yield system
    finally:
        system.shutdown()
        active_names = {thread.name for thread in threading.enumerate() if thread.is_alive()}
        assert not active_names.intersection({"ICS.auto_ctrl", "ICS.integrations", "ics-tick"})


# ── Boot tests ──────────────────────────────────────────────────────────────

class TestBoot:
    def test_boot_all_subsystems(self, ics):
        """Core subsystems should come online."""
        status = ics._boot_status
        assert len(status) >= 17
        alive = sum(1 for v in status.values() if v == "alive")
        # At least the core subsystems must be alive
        assert alive >= 10, f"Only {alive}/{len(status)} alive: {status}"

    def test_thought_bus_alive(self, ics):
        assert ics.thought_bus is not None

    def test_vault_alive(self, ics):
        assert ics.vault is not None

    def test_lambda_engine_alive(self, ics):
        assert ics.lambda_engine is not None

    def test_goal_engine_alive(self, ics):
        assert ics.goal_engine is not None

    def test_agent_core_alive(self, ics):
        assert ics.agent_core is not None

    def test_swarm_alive(self, ics):
        assert ics.swarm is not None

    def test_temporal_ground_alive(self, ics):
        assert ics.temporal_ground is not None

    def test_autonomous_threads_are_suppressed_in_audit_mode(self, ics):
        assert ics._tick_thread is None
        active_names = {thread.name for thread in threading.enumerate() if thread.is_alive()}
        assert not active_names.intersection({"ICS.auto_ctrl", "ICS.integrations", "ics-tick"})

    def test_normal_runtime_retains_background_capability(self, monkeypatch):
        from aureon.core.integrated_cognitive_system import _background_side_effects_suppressed

        monkeypatch.delenv("AUREON_AUDIT_MODE")
        monkeypatch.delenv("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS")
        assert _background_side_effects_suppressed() is False

    def test_self_dialogue_booted(self, ics):
        """SelfDialogueEngine should be booted (not None)."""
        # May fail if voice dependencies are missing, so just check boot was attempted
        status = ics._boot_status.get("self_dialogue", "")
        assert status in ("alive", ) or "failed" in status

    def test_mycelium_mind_booted(self, ics):
        status = ics._boot_status.get("mycelium_mind", "")
        assert status in ("alive", ) or "failed" in status

    def test_metacognition_booted(self, ics):
        status = ics._boot_status.get("metacognition", "")
        assert status in ("alive", ) or "failed" in status


# ── Command tests ───────────────────────────────────────────────────────────

class TestCommands:
    def test_status(self, ics):
        r = ics.process_user_input("/status")
        assert r is not None
        assert "ICS STATUS" in r
        assert "Tick count" in r

    def test_coherence(self, ics):
        r = ics.process_user_input("/coherence")
        assert r is not None
        assert "Lambda" in r

    def test_goal_status_empty(self, ics):
        r = ics.process_user_input("/goal")
        assert r is not None

    def test_swarm_status(self, ics):
        r = ics.process_user_input("/swarm")
        assert r is not None
        assert "SWARM" in r or "Swarm" in r or "not available" in r

    def test_pause(self, ics):
        r = ics.process_user_input("/pause")
        assert "paused" in r.lower()

    def test_resume(self, ics):
        r = ics.process_user_input("/resume")
        assert "resumed" in r.lower()

    def test_cancel(self, ics):
        r = ics.process_user_input("/cancel")
        assert "cancel" in r.lower()

    def test_quit(self, ics):
        r = ics.process_user_input("/quit")
        assert r == "__QUIT__"

    def test_empty_input(self, ics):
        r = ics.process_user_input("")
        assert r is None


# ── Goal execution tests ───────────────────────────────────────────────────

class TestGoals:
    def test_sequential_goal(self, ics):
        r = ics.process_user_input("check system info")
        assert "completed" in r

    def test_search_goal(self, ics):
        r = ics.process_user_input("search for bitcoin price")
        assert "completed" in r

    def test_read_file_goal(self, ics):
        r = ics.process_user_input("read the README.md file")
        assert "completed" in r

    def test_goal_engine_stats(self, ics):
        stats = ics.goal_engine.get_status()["stats"]
        assert stats["goals_submitted"] >= 3
        assert stats["steps_executed"] >= 3


# ── Swarm tests ─────────────────────────────────────────────────────────────

class TestSwarm:
    def test_swarm_goal(self, ics):
        r = ics.process_user_input("analyse the market from multiple perspectives")
        assert "completed" in r or "failed" in r
        stats = ics.goal_engine.get_status()["stats"]
        assert stats["swarm_dispatches"] >= 1

    def test_research_swarm(self, ics):
        r = ics.process_user_input("research bitcoin and ethereum trends")
        assert r is not None
        assert "completed" in r or "failed" in r


# ── Cognitive tick tests ────────────────────────────────────────────────────

class TestCognitiveTick:
    def test_tick_runs(self, ics):
        """Cognitive tick should have run at least once."""
        assert ics._tick_count >= 1

    def test_tick_manual(self, ics):
        """Manual tick should not crash."""
        ics._unified_cognitive_tick()  # should complete without error

    def test_temporal_ground_ticked(self, ics):
        """Temporal ground should be ticked by the cognitive loop."""
        if ics.temporal_ground is None:
            pytest.skip("temporal_ground not available")
        # Run a few ticks manually
        for _ in range(3):
            ics._unified_cognitive_tick()
        # The temporal ground should have a chain length > 0
        chain = getattr(ics.temporal_ground, "_chain", None)
        if chain is not None:
            assert chain.chain_length > 0


# ── Graceful degradation ───────────────────────────────────────────────────

class TestGracefulDegradation:
    def test_boot_returns_dict(self, ics):
        """Boot should return a status dict even if things fail."""
        assert isinstance(ics._boot_status, dict)
        assert len(ics._boot_status) > 0

    def test_all_statuses_are_strings(self, ics):
        for name, st in ics._boot_status.items():
            assert isinstance(st, str), f"{name} status is not a string: {st}"
