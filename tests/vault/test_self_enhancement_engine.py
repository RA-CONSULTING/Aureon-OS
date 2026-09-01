#!/usr/bin/env python3
"""
Tests for aureon.queen.self_enhancement_engine.SelfEnhancementEngine

Tests every layer of the self-improvement pipeline:
  [1]  GapAnalyzer produces gaps from seed list when library is empty
  [2]  GapAnalyzer surfaces failing skills
  [3]  GapAnalyzer de-duplicates and ranks by priority
  [4]  extract_code() parses code from fenced blocks
  [5]  extract_code() falls back to bare def block
  [6]  build_generation_prompt() includes gap description and skill names
  [7]  _normalise_code() fixes function name + adds params/context args
  [8]  _sandbox_test() runs valid code and rejects invalid code
  [9]  enhance_once() end-to-end with a fake LLM — registers a new skill
  [10] enhance_once() handles LLM returning no code gracefully
  [11] enhance_once() handles validation failure gracefully
  [12] EnhancementLog persists and reloads entries
  [13] Singleton get/reset lifecycle
  [14] SelfFeedbackLoop wires enhancement every N ticks (unit, no LLM)
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

import pytest

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from aureon.queen.self_enhancement_engine import (  # noqa: E402
    Gap,
    GapAnalyzer,
    EnhancementLog,
    EnhancementRecord,
    SelfEnhancementEngine,
    extract_code,
    build_generation_prompt,
    reset_self_enhancement_engine,
    get_self_enhancement_engine,
)

PASS = 0
FAIL = 0


def check(condition: bool, msg: str) -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [OK] {msg}")
    else:
        FAIL += 1
        print(f"  [!!] {msg}")


# ─────────────────────────────────────────────────────────────────────────────
# Stubs
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class _FakeSkill:
    name: str
    category: str = "general"
    failure_count: int = 0
    success_count: int = 0
    last_error: Optional[str] = None
    status: str = "active"


class _FakeSkillLibrary:
    def __init__(self, skills=None):
        self._skills: List[_FakeSkill] = list(skills or [])

    def all(self):
        return list(self._skills)

    def get(self, name: str):
        for s in self._skills:
            if s.name == name:
                return s
        return None

    def add(self, skill, persist=True):
        # Replace if name exists, else append.
        for i, s in enumerate(self._skills):
            if s.name == skill.name:
                self._skills[i] = skill
                return skill
        self._skills.append(skill)
        return skill


class _FakeVault:
    def by_category(self, cat, n=None):
        return []

    def ingest(self, topic, payload, category):
        pass


class _FakeValidator:
    def __init__(self, ok=True, errors=None):
        self._ok = ok
        self._errors = errors or []

    def validate(self, proposal):
        return self._ok, self._errors, []


_GOOD_CODE = '''\
def test_skill(params, context):
    x = int(params.get("x", 0))
    y = int(params.get("y", 0))
    return {"ok": True, "result": x + y}
'''

_BAD_CODE = "def test_skill(): import os; os.system('rm -rf /')"

_LLM_WITH_FENCE = f"""
Here is the skill you asked for:

```python
{_GOOD_CODE}
```

Let me know if you need changes.
"""

_LLM_NO_FENCE = _GOOD_CODE

_LLM_EMPTY = "I don't know how to do that."


class _FakeLLMCaller:
    def __init__(self, reply: str = _LLM_WITH_FENCE):
        self._reply = reply
        self.calls = 0

    def call(self, prompt: str) -> str:
        self.calls += 1
        return self._reply


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_gap_analyzer_seed_gaps_when_no_library():
    print("\n[1] GapAnalyzer returns seed gaps when library is None")
    ga = GapAnalyzer(skill_library=None, vault=None)
    gaps = ga.analyse()
    check(len(gaps) > 0, f"seed gaps returned (got {len(gaps)})")
    names = [g.suggested_name for g in gaps]
    check("summarise_recent_vault" in names, "'summarise_recent_vault' in seed gaps")
    check("lambda_trend" in names, "'lambda_trend' in seed gaps")
    check("hnc_stability_check" in names, "'hnc_stability_check' in seed gaps")
    # All should have priority > 0.
    check(all(g.priority > 0 for g in gaps), "all seed gaps have priority > 0")


def test_gap_analyzer_failing_skills():
    print("\n[2] GapAnalyzer surfaces skills with failure_count > 0")
    bad = _FakeSkill(
        name="broken_skill",
        category="trading",
        failure_count=3,
        success_count=0,
        last_error="division by zero",
    )
    lib = _FakeSkillLibrary([bad])
    ga = GapAnalyzer(skill_library=lib, vault=None)
    gaps = ga.analyse()
    names = [g.suggested_name for g in gaps]
    check("broken_skill_v2" in names, "'broken_skill_v2' gap created for failing skill")
    fail_gap = next((g for g in gaps if g.suggested_name == "broken_skill_v2"), None)
    check(fail_gap is not None and fail_gap.priority == 0.9, "failing skill gap has priority=0.9")


def test_gap_analyzer_deduplicates_and_ranks():
    print("\n[3] GapAnalyzer deduplicates and ranks by priority")
    # Library with none of the seed skills.
    lib = _FakeSkillLibrary([])
    ga = GapAnalyzer(skill_library=lib, vault=None)
    gaps = ga.analyse()
    names = [g.suggested_name for g in gaps]
    # No duplicates.
    check(len(names) == len(set(names)), "no duplicate skill names in gaps")
    # Sorted descending by priority.
    priorities = [g.priority for g in gaps]
    check(priorities == sorted(priorities, reverse=True), "gaps sorted by priority desc")


def test_extract_code_fenced_block():
    print("\n[4] extract_code() parses triple-backtick python fence")
    code = extract_code(_LLM_WITH_FENCE)
    check(code is not None, "code extracted (not None)")
    check("def test_skill" in (code or ""), "extracted block contains 'def test_skill'")
    check("return" in (code or ""), "extracted block contains 'return'")


def test_extract_code_no_fence():
    print("\n[5] extract_code() falls back to bare def block")
    code = extract_code(_LLM_NO_FENCE)
    check(code is not None, "code extracted from bare def")
    check("def test_skill" in (code or ""), "bare def found")


def test_extract_code_no_match():
    print("\n[5b] extract_code() returns None when no code present")
    code = extract_code(_LLM_EMPTY)
    check(code is None, "returns None for prose-only reply")


def test_build_generation_prompt():
    print("\n[6] build_generation_prompt() includes gap description and skill names")
    gap = Gap(
        suggested_name="my_test_skill",
        category="cognition",
        description="Compute the harmonic mean of a list of values.",
    )
    existing = ["skill_a", "skill_b"]
    prompt = build_generation_prompt(gap, existing)
    check("my_test_skill" in prompt, "skill name in prompt")
    check("harmonic mean" in prompt, "gap description in prompt")
    check("skill_a" in prompt, "existing skills listed in prompt")
    check("params: dict" in prompt or "params" in prompt, "params in function signature spec")


def test_normalise_code_renames_fn():
    print("\n[7] _normalise_code() renames function and adds params/context")
    engine = SelfEnhancementEngine.__new__(SelfEnhancementEngine)
    code = "def wrong_name(x):\n    return {'ok': True, 'result': x}"
    fixed = engine._normalise_code(code, "right_name")
    check("def right_name(" in fixed, "function renamed to right_name")
    check("params" in fixed or "right_name" in fixed, "params arg present after rename")


def test_sandbox_test_valid_code():
    print("\n[8a] _sandbox_test() remains on production HOLD")
    engine = SelfEnhancementEngine.__new__(SelfEnhancementEngine)
    with pytest.raises(RuntimeError, match="self_enhancement_engine_hold"):
        engine._sandbox_test(_GOOD_CODE, "test_skill")


def test_sandbox_test_bad_code():
    print("\n[8b] unsafe sandbox input is held before execution")
    bad_return = "def test_skill(params, context):\n    return 42"
    engine = SelfEnhancementEngine.__new__(SelfEnhancementEngine)
    with pytest.raises(RuntimeError, match="self_enhancement_engine_hold"):
        engine._sandbox_test(bad_return, "test_skill")


def test_sandbox_test_syntax_error():
    print("\n[8c] malformed sandbox input is held before compilation")
    engine = SelfEnhancementEngine.__new__(SelfEnhancementEngine)
    with pytest.raises(RuntimeError, match="self_enhancement_engine_hold"):
        engine._sandbox_test("def broken(:\n    pass", "broken")


def test_enhance_once_end_to_end_registers():
    print("\n[9] enhance_once() holds before LLM or registration")
    with tempfile.TemporaryDirectory() as tmpdir:
        lib = _FakeSkillLibrary([])
        caller = _FakeLLMCaller(_LLM_WITH_FENCE)
        validator = _FakeValidator(ok=True)

        engine = SelfEnhancementEngine(
            skill_library=lib,
            vault=_FakeVault(),
            validator=validator,
            llm_caller=caller,
            storage_dir=Path(tmpdir),
        )
        with pytest.raises(RuntimeError, match="self_enhancement_engine_hold"):
            engine.enhance_once()
        assert caller.calls == 0
        assert lib.all() == []
        assert engine.recent_log() == []


def test_enhance_once_empty_llm_reply():
    print("\n[10] enhance_once() HOLD precedes even an empty LLM reply")
    with tempfile.TemporaryDirectory() as tmpdir:
        lib = _FakeSkillLibrary([])
        caller = _FakeLLMCaller("")

        engine = SelfEnhancementEngine(
            skill_library=lib,
            vault=_FakeVault(),
            llm_caller=caller,
            storage_dir=Path(tmpdir),
        )
        with pytest.raises(RuntimeError, match="self_enhancement_engine_hold"):
            engine.enhance_once()
        assert caller.calls == 0


def test_enhance_once_validation_failure():
    print("\n[11] enhance_once() HOLD precedes validator and library mutation")
    with tempfile.TemporaryDirectory() as tmpdir:
        lib = _FakeSkillLibrary([])
        caller = _FakeLLMCaller(_LLM_WITH_FENCE)
        validator = _FakeValidator(ok=False, errors=["forbidden call: eval"])

        engine = SelfEnhancementEngine(
            skill_library=lib,
            vault=_FakeVault(),
            validator=validator,
            llm_caller=caller,
            storage_dir=Path(tmpdir),
        )
        with pytest.raises(RuntimeError, match="self_enhancement_engine_hold"):
            engine.enhance_once()
        assert caller.calls == 0
        assert len(lib.all()) == 0


def test_enhancement_log_persist_reload():
    print("\n[12] EnhancementLog is in-memory and persistence is held")
    with tempfile.TemporaryDirectory() as tmpdir:
        log = EnhancementLog(storage_dir=Path(tmpdir))
        r1 = EnhancementRecord(
            record_id="aaa",
            skill_name="skill_a",
            registered=True,
            validation_ok=True,
            sandbox_ok=True,
            latency_s=0.5,
        )
        r2 = EnhancementRecord(
            record_id="bbb",
            skill_name="skill_b",
            registered=False,
            error="sandbox failed",
            latency_s=0.1,
        )
        log.append(r1)
        log.append(r2)

        recent = log.recent(10)
        check(len(recent) == 2, f"2 entries reloaded from disk (got {len(recent)})")
        check(recent[0]["record_id"] == "aaa", "first entry preserved")
        check(recent[1]["skill_name"] == "skill_b", "second entry preserved")

        stats = log.stats()
        check(stats["total_attempts"] == 2, "total_attempts == 2")
        check(stats["total_registered"] == 1, "total_registered == 1")
        check(abs(stats["success_rate"] - 0.5) < 0.01, "success_rate == 0.5")
        assert list(Path(tmpdir).iterdir()) == []
        with pytest.raises(RuntimeError, match="self_enhancement_engine_hold"):
            EnhancementLog(storage_dir=Path(tmpdir), persistence_enabled=True)
        with pytest.raises(RuntimeError, match="self_enhancement_engine_hold"):
            log._load()


def test_singleton_lifecycle():
    print("\n[13] get/reset singleton lifecycle")
    reset_self_enhancement_engine()
    e1 = get_self_enhancement_engine()
    e2 = get_self_enhancement_engine()
    check(e1 is e2, "singleton: same instance returned twice")
    reset_self_enhancement_engine()
    e3 = get_self_enhancement_engine()
    check(e3 is not e1, "reset yields a fresh instance")
    reset_self_enhancement_engine()


def test_feedback_loop_calls_enhance_on_nth_tick():
    print("\n[14] SelfFeedbackLoop self-coding remains on production HOLD")
    from aureon.vault.self_feedback_loop import AureonSelfFeedbackLoop

    with pytest.raises(RuntimeError, match="aureon_self_feedback_loop_hold"):
        AureonSelfFeedbackLoop(enable_self_enhancement=True)


def test_multiple_gaps_cycles_exhaust_seed():
    print("\n[15] repeated enhance_once() calls remain held and inert")
    with tempfile.TemporaryDirectory() as tmpdir:
        lib = _FakeSkillLibrary([])
        caller = _FakeLLMCaller(_LLM_WITH_FENCE)
        validator = _FakeValidator(ok=True)

        engine = SelfEnhancementEngine(
            skill_library=lib,
            vault=_FakeVault(),
            validator=validator,
            llm_caller=caller,
            storage_dir=Path(tmpdir),
        )
        for _ in range(5):
            with pytest.raises(RuntimeError, match="self_enhancement_engine_hold"):
                engine.enhance_once()
        assert caller.calls == 0
        assert lib.all() == []
        assert engine.recent_log(10) == []
        assert engine.status()["cycle_count"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


def main():
    print("=" * 80)
    print("  SELF-ENHANCEMENT ENGINE TEST SUITE")
    print("=" * 80)

    test_gap_analyzer_seed_gaps_when_no_library()
    test_gap_analyzer_failing_skills()
    test_gap_analyzer_deduplicates_and_ranks()
    test_extract_code_fenced_block()
    test_extract_code_no_fence()
    test_extract_code_no_match()
    test_build_generation_prompt()
    test_normalise_code_renames_fn()
    test_sandbox_test_valid_code()
    test_sandbox_test_bad_code()
    test_sandbox_test_syntax_error()
    test_enhance_once_end_to_end_registers()
    test_enhance_once_empty_llm_reply()
    test_enhance_once_validation_failure()
    test_enhancement_log_persist_reload()
    test_singleton_lifecycle()
    test_feedback_loop_calls_enhance_on_nth_tick()
    test_multiple_gaps_cycles_exhaust_seed()

    print()
    print("=" * 80)
    print(f"  RESULT: {PASS} passed, {FAIL} failed")
    print("=" * 80)
    import sys
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
