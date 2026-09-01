"""Fail-closed tests for SkillExecutorBridge."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from aureon.vault.voice import skill_executor_bridge as bridge_module
from aureon.vault.voice._goal_claims import GoalClaims
from aureon.vault.voice.skill_executor_bridge import (
    SkillExecutorBridge,
    _default_file_executor,
    code_architect_adapter,
    get_skill_executor_bridge,
    reset_skill_executor_bridge,
)


class _Trap:
    def __getattribute__(self, _name: str) -> Any:
        raise AssertionError("release-held skill bridge touched an effect owner")


def test_constructor_is_inert_and_does_not_arm_default_writer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        Path,
        "resolve",
        lambda *_args, **_kwargs: pytest.fail("inert constructor must not resolve paths"),
    )
    bridge = SkillExecutorBridge(
        thought_bus=_Trap(),
        vault=_Trap(),
        conscience=_Trap(),
        output_root=str(tmp_path),
    )
    assert bridge._executor is None
    assert bridge.stats() == {
        "claimed": 0,
        "vetoed": 0,
        "executed": 0,
        "failed": 0,
        "abandoned": 0,
        "status": "HOLD",
        "reason_code": "production_magic_star_release_unavailable",
        "production_ready": False,
        "effect_enabled": False,
        "subscribed": False,
        "output_root": str(tmp_path),
    }
    assert bridge.history() == []
    assert list(tmp_path.iterdir()) == []


def test_default_writer_and_default_executor_closure_are_held(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="skill_executor_bridge_hold"):
        _default_file_executor("unsafe", {"x": 1}, output_root=tmp_path)
    bridge = SkillExecutorBridge(output_root=str(tmp_path))
    default_executor = bridge._build_default_executor()
    with pytest.raises(RuntimeError, match="skill_executor_bridge_hold"):
        default_executor("unsafe", {"x": 1})
    assert list(tmp_path.iterdir()) == []


def test_code_architect_adapter_is_held_before_execute_skill() -> None:
    adapted = code_architect_adapter(_Trap())
    with pytest.raises(RuntimeError, match="skill_executor_bridge_hold"):
        adapted("skill", {"x": 1})


def test_start_and_intake_hold_before_subscription_claim_or_thread(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "aureon.vault.voice.skill_executor_bridge.threading.Thread",
        lambda *_args, **_kwargs: pytest.fail("bridge must not create a thread"),
    )
    bridge = SkillExecutorBridge(
        thought_bus=_Trap(),
        vault=_Trap(),
        executor=_Trap(),
        conscience=_Trap(),
        output_root=str(tmp_path),
    )
    with pytest.raises(RuntimeError, match="skill_executor_bridge_hold"):
        bridge.start()
    GoalClaims.clear()
    with pytest.raises(RuntimeError, match="skill_executor_bridge_hold"):
        bridge._on_aligned_request(_Trap())
    assert GoalClaims.is_claimed("probe-goal") is False
    assert bridge.stats()["claimed"] == 0
    assert bridge.stats()["status"] == "HOLD"
    assert bridge.stats()["subscribed"] is False
    assert bridge.history() == []


@pytest.mark.parametrize(
    "call_name",
    [
        "veto",
        "run_chain",
        "abandon",
        "publish",
        "ingest",
    ],
)
def test_direct_effect_helpers_are_held(call_name: str, tmp_path: Path) -> None:
    bridge = SkillExecutorBridge(
        thought_bus=_Trap(),
        vault=_Trap(),
        executor=_Trap(),
        conscience=_Trap(),
        output_root=str(tmp_path),
    )
    calls = {
        "veto": lambda: bridge._veto_blocks("goal", "persona", {"goal_id": "g"}),
        "run_chain": lambda: bridge._run_chain("g", "persona", "goal", ["skill"]),
        "abandon": lambda: bridge._publish_abandoned("g", "reason"),
        "publish": lambda: bridge._publish("topic", {"x": 1}),
        "ingest": lambda: bridge._ingest_artefacts("p", "g", "s", ["x"]),
    }
    with pytest.raises(RuntimeError, match="skill_executor_bridge_hold"):
        calls[call_name]()
    assert bridge.stats()["executed"] == 0
    assert bridge.history() == []
    assert list(tmp_path.iterdir()) == []


def test_singleton_getter_is_held_and_reset_is_inert() -> None:
    reset_skill_executor_bridge()
    assert bridge_module._singleton is None
    with pytest.raises(RuntimeError, match="skill_executor_bridge_hold"):
        get_skill_executor_bridge(thought_bus=_Trap(), vault=_Trap())
    assert bridge_module._singleton is None
    reset_skill_executor_bridge()
