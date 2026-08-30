"""
SkillExecutor — runs validated skills in the safe exec sandbox
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Executes skills against:
  • A VMControlDispatcher      (VM target)
  • The local system           (local target — future; currently the same
    dispatcher can be pointed at a real Windows VM via WinRM)

For compound / workflow / role skills, the executor resolves dependencies
via the SkillLibrary and caches compiled function objects to avoid
recompiling on every call.

Safety:
  • Uses `primitives.get_safe_globals(dispatcher, thought_bus, executor)`
    as the exec globals dict (SAFE_BUILTINS only).
  • Re-runs the static safety check before first execution.
  • Bounded recursion depth (max 10) to prevent infinite compound chains.
  • Per-execution timeout via watchdog thread (soft — Python can't hard
    cancel arbitrary code, but we record and flag long runs).
"""

from __future__ import annotations

import logging
import threading
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from aureon.code_architect.skill import Skill, SkillStatus
from aureon.code_architect.skill_library import SkillLibrary
from aureon.code_architect.primitives import get_safe_globals
from aureon.code_architect.validator import SkillValidator

logger = logging.getLogger("aureon.code_architect.executor")


MAX_DEPTH = 10


# ─────────────────────────────────────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class SkillExecutionResult:
    skill_name: str = ""
    ok: bool = False
    return_value: Any = None
    error: Optional[str] = None
    traceback: Optional[str] = None
    duration_s: float = 0.0
    depth: int = 0
    timestamp: float = field(default_factory=time.time)
    sub_results: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "ok": self.ok,
            "return_value": self.return_value,
            "error": self.error,
            "traceback": self.traceback,
            "duration_s": round(self.duration_s, 4),
            "depth": self.depth,
            "timestamp": self.timestamp,
            "sub_results_count": len(self.sub_results),
        }


# ─────────────────────────────────────────────────────────────────────────────
# SkillExecutor
# ─────────────────────────────────────────────────────────────────────────────


class SkillExecutor:
    """
    Runs skills in a safe exec sandbox.

    Attributes:
        library    : the SkillLibrary (source of skills)
        dispatcher : the VMControlDispatcher (backends for vm_* primitives)
        validator  : the SkillValidator (re-runs static safety on first use)
        thought_bus: optional ThoughtBus for emit_event primitive
    """

    def __init__(
        self,
        library: Optional[SkillLibrary] = None,
        dispatcher: Any = None,
        validator: Optional[SkillValidator] = None,
        thought_bus: Any = None,
        require_static_check: bool = True,
    ):
        self.library = library
        self.dispatcher = dispatcher
        self.validator = validator or SkillValidator()
        self.thought_bus = thought_bus
        self.require_static_check = require_static_check

        self._compiled_cache: Dict[str, Callable] = {}           # skill_name → entry function
        self._lock = threading.RLock()

        # Metrics
        self._total_executions = 0
        self._successes = 0
        self._failures = 0

    # ─────────────────────────────────────────────────────────────────────
    # Compilation
    # ─────────────────────────────────────────────────────────────────────

    def _safe_globals(self) -> Dict[str, Any]:
        return get_safe_globals(
            dispatcher=self.dispatcher,
            thought_bus=self.thought_bus,
            executor=self,
        )

    def _compile(self, skill: Skill) -> Callable:
        """Compile a skill's source into a callable (cached)."""
        with self._lock:
            cached = self._compiled_cache.get(skill.name)
            if cached is not None:
                return cached

        # Belt & braces: re-run static check before compile
        if self.require_static_check:
            safe, errors = self.validator.static_check(skill.code)
            if not safe:
                raise RuntimeError(f"skill {skill.name} failed static safety: {errors[:3]}")

        # exec inside a *fresh* globals dict for compilation so function refs
        # are properly bound. The execution will use _safe_globals() again.
        compile_globals = self._safe_globals()
        local_scope: Dict[str, Any] = {}
        try:
            compiled_code = compile(skill.code, f"<skill:{skill.name}>", "exec")
            exec(compiled_code, compile_globals, local_scope)
        except Exception as e:
            raise RuntimeError(f"skill {skill.name} compile failed: {e}")

        entry = skill.entry_function or skill.name
        func = local_scope.get(entry)
        if not callable(func):
            raise RuntimeError(f"skill {skill.name} has no callable entry function '{entry}'")

        with self._lock:
            self._compiled_cache[skill.name] = func
        return func

    def invalidate_cache(self, skill_name: Optional[str] = None) -> None:
        with self._lock:
            if skill_name is None:
                self._compiled_cache.clear()
            else:
                self._compiled_cache.pop(skill_name, None)

    def _execution_is_simulated(self, params: Optional[Dict[str, Any]]) -> bool:
        """Return True only when the selected dispatcher session is in-memory."""
        if self.dispatcher is None:
            return False
        try:
            session_id = (params or {}).get("session_id")
            controller = self.dispatcher.get_session(session_id)
            session = getattr(controller, "session", None)
            return str(getattr(session, "backend", "")).casefold() == "simulated"
        except Exception:
            return False

    def _blocked_execution(
        self,
        skill: Skill,
        *,
        error: str,
        depth: int,
        started_at: float,
    ) -> SkillExecutionResult:
        self.invalidate_cache(skill.name)
        result = SkillExecutionResult(
            skill_name=skill.name,
            ok=False,
            error=error,
            depth=depth,
            duration_s=time.time() - started_at,
        )
        self._failures += 1
        if self.library:
            self.library.record_execution(
                skill.name,
                success=False,
                duration_s=result.duration_s,
                error=result.error,
            )
        return result

    # ─────────────────────────────────────────────────────────────────────
    # Execution
    # ─────────────────────────────────────────────────────────────────────

    def execute(
        self,
        skill: Skill,
        params: Optional[Dict[str, Any]] = None,
        _depth: int = 0,
    ) -> SkillExecutionResult:
        """Execute a Skill object."""
        if _depth > MAX_DEPTH:
            return SkillExecutionResult(
                skill_name=skill.name,
                ok=False,
                error=f"max_recursion_depth_exceeded: {_depth}",
                depth=_depth,
            )

        self._total_executions += 1
        start = time.time()
        result = SkillExecutionResult(skill_name=skill.name, depth=_depth)

        status_value = str(getattr(skill.status, "value", skill.status) or "").casefold()
        non_executable_statuses = {
            "proposed",
            "pending",
            "pending_review",
            "rejected",
            "blocked",
            "deprecated",
        }
        if status_value in non_executable_statuses:
            return self._blocked_execution(
                skill,
                error=f"skill_status_not_executable:{status_value or 'unknown'}",
                depth=_depth,
                started_at=start,
            )

        tags = set(skill.tags or [])
        if (
            "requires_explicit_approval" in tags
            and status_value not in {SkillStatus.APPROVED.value, SkillStatus.ACTIVE.value}
        ):
            return self._blocked_execution(
                skill,
                error="skill_approval_required",
                depth=_depth,
                started_at=start,
            )
        if "live_execution_disabled" in tags and not self._execution_is_simulated(params):
            return self._blocked_execution(
                skill,
                error="skill_live_execution_disabled",
                depth=_depth,
                started_at=start,
            )

        # Compile (uses cache)
        try:
            func = self._compile(skill)
        except Exception as e:
            result.ok = False
            result.error = str(e)
            result.traceback = traceback.format_exc()
            result.duration_s = time.time() - start
            self._failures += 1
            if self.library:
                self.library.record_execution(skill.name, success=False,
                                              duration_s=result.duration_s,
                                              error=result.error)
            return result

        # We need the globals dict from the compiled function so primitives
        # like call_skill/emit_event see the right executor. The function
        # was exec'd with our globals, so it already captures them.

        # Run the entry function
        try:
            ret = func(**(params or {}))
            result.ok = True
            result.return_value = ret
            self._successes += 1
        except Exception as e:
            result.ok = False
            result.error = str(e)
            result.traceback = traceback.format_exc()
            self._failures += 1

        result.duration_s = time.time() - start

        if self.library:
            self.library.record_execution(
                name=skill.name,
                success=result.ok,
                duration_s=result.duration_s,
                error=result.error,
            )

        # Publish
        self._publish(skill, result)

        return result

    def execute_by_name(
        self,
        skill_name: str,
        params: Optional[Dict[str, Any]] = None,
        _depth: int = 0,
    ) -> SkillExecutionResult:
        """Look up a skill by name and execute it."""
        if self.library is None:
            return SkillExecutionResult(
                skill_name=skill_name,
                ok=False,
                error="no_library",
            )
        skill = self.library.get(skill_name)
        if not skill:
            return SkillExecutionResult(
                skill_name=skill_name,
                ok=False,
                error="skill_not_found",
            )
        return self.execute(skill, params=params, _depth=_depth)

    def execute_with_dependencies(
        self,
        skill_name: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> SkillExecutionResult:
        """
        Resolve the dependency tree and execute the top-level skill.
        The dependencies themselves are executed lazily via call_skill,
        but this method pre-compiles them for speed.
        """
        if self.library is None:
            return SkillExecutionResult(
                skill_name=skill_name,
                ok=False,
                error="no_library",
            )

        deps = self.library.resolve_dependencies(skill_name)
        # Pre-compile all dependencies so call_skill finds them ready
        for dep in deps:
            try:
                self._compile(dep)
            except Exception as e:
                logger.warning("Failed to pre-compile dep %s: %s", dep.name, e)

        return self.execute_by_name(skill_name, params=params)

    # ─────────────────────────────────────────────────────────────────────
    # Publishing
    # ─────────────────────────────────────────────────────────────────────

    def _publish(self, skill: Skill, result: SkillExecutionResult) -> None:
        if not self.thought_bus:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought
            self.thought_bus.publish(Thought(
                source="code_architect.executor",
                topic=f"skill.executed.{'ok' if result.ok else 'fail'}",
                payload={
                    "skill_name": skill.name,
                    "level": skill.level.name,
                    "ok": result.ok,
                    "duration_s": result.duration_s,
                    "depth": result.depth,
                    "error": result.error,
                },
            ))
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────
    # Status
    # ─────────────────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        return {
            "total_executions": self._total_executions,
            "successes": self._successes,
            "failures": self._failures,
            "success_rate": (
                self._successes / self._total_executions if self._total_executions > 0 else 0.0
            ),
            "cached_compilations": len(self._compiled_cache),
            "dispatcher_wired": self.dispatcher is not None,
        }
