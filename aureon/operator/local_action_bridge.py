"""
LocalActionBridge — the organism's single grounded path to its own machine.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Every local-machine move flows through one method — :meth:`perform` — which:

  1. grounds the move via :class:`GroundedActionGate` (hard boundary → HNC
     Master-Formula/Auris read → optional Ollama rationale → conscience veto);
  2. if vetoed, abandons it (``local.action.abandoned``) and returns blocked;
  3. if approved but **not armed**, returns a dry-run result (nothing touches
     the machine — this is the default posture);
  4. if approved **and armed**, dispatches to a pluggable executor and publishes
     ``local.action.result``.

Executor contract (duck-typed, same shape as SkillExecutorBridge):
    executor(action: str, params: dict) -> {ok: bool, result, artefacts, error}

The default executor routes file/shell moves to the guarded operator toolbelt
(``GuardedToolRegistry`` — repo-confined, sensitive-path-blocked, AST-checked)
and desktop moves to the ``vm_control`` dispatcher (simulated backend by
default). Anything without a live executor degrades honestly to
``executor unavailable`` — it never fabricates success.

Arming: dry-run unless ``AUREON_LOCAL_ACTIONS_ARMED=1``. The gate runs either
way, so a dry-run still produces a full grounded verdict and bus trace — the
organism senses the move whether or not it executes.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import logging
import os
from collections import deque
from typing import Any, Callable, Deque, Dict

from aureon.operator.aureon_operator import join_organism
from aureon.operator.grounded_action import ActionVerdict, GroundedActionGate

logger = logging.getLogger("aureon.operator.local_action_bridge")

try:  # pragma: no cover - trivial import guard
    from aureon.core.aureon_thought_bus import Thought, get_thought_bus
except Exception:  # noqa: BLE001
    Thought = None  # type: ignore[assignment]
    get_thought_bus = None  # type: ignore[assignment]

Executor = Callable[[str, Dict[str, Any]], Dict[str, Any]]

# Operator toolbelt action names that the guarded registry handles directly.
_FILE_SHELL_ACTIONS = {
    "read_repo_file", "list_repo", "repo_search", "write_repo_file",
    "patch_repo_file", "execute_shell", "code_validate",
}
_DESKTOP_ACTIONS = {
    "screenshot", "mouse_move", "left_click", "right_click", "double_click",
    "type_text", "press_key", "hotkey", "scroll", "cursor_position",
}


def _truthy(name: str, default: str = "0") -> bool:
    return str(os.environ.get(name, default) or default).strip().lower() in {"1", "true", "yes", "on"}


class LocalActionBridge:
    """Grounded chokepoint for all local-machine actions."""

    def __init__(
        self,
        *,
        gate: GroundedActionGate | None = None,
        executor: Executor | None = None,
        bus: Any = None,
        armed: bool | None = None,
        join: bool = True,
    ) -> None:
        self.gate = gate or GroundedActionGate()
        self._executor = executor  # None → lazy default router
        self._bus = bus if bus is not None else (get_thought_bus() if get_thought_bus else None)
        self.armed = _truthy("AUREON_LOCAL_ACTIONS_ARMED") if armed is None else armed
        # rolling record of recent verdicts — feeds the Λ(t) local-action source
        self._recent: Deque[Dict[str, Any]] = deque(maxlen=100)
        if join:
            try:
                join_organism(self, "local_action_bridge")
            except Exception as exc:  # noqa: BLE001
                logger.debug("organism join skipped: %s", exc)

    # ── executor routing (lazy default) ────────────────────────────────
    def _default_executor(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if action in _FILE_SHELL_ACTIONS:
            try:
                from aureon.operator.tools import build_operator_tools

                reg = build_operator_tools(allow_writes=True, allow_shell=True)
                out = reg.execute(action, params)
                return {"ok": True, "result": out, "artefacts": [], "error": None}
            except Exception as exc:  # noqa: BLE001
                return {"ok": False, "result": None, "artefacts": [], "error": str(exc)}
        if action in _DESKTOP_ACTIONS:
            try:
                from aureon.autonomous.aureon_governed_desktop_gateway import (
                    get_governed_desktop_gateway,
                )

                gateway = get_governed_desktop_gateway()
                mapped = {
                    "screenshot": "observe",
                    "mouse_move": "move",
                    "left_click": "click",
                    "right_click": "right_click",
                    "double_click": "double_click",
                    "type_text": "type",
                    "press_key": "press",
                    "hotkey": "hotkey",
                    "scroll": "scroll",
                }.get(action)
                if mapped is None:
                    return {"ok": False, "result": None, "artefacts": [],
                            "error": f"desktop action {action!r} is not governed"}
                action_params = dict(params)
                target_binding_id = str(action_params.pop("target_binding_id", "") or "") or None
                if mapped == "scroll" and "clicks" in action_params and "amount" not in action_params:
                    action_params["amount"] = action_params.pop("clicks")
                out = gateway.execute(
                    mapped,
                    action_params,
                    target_binding_id=target_binding_id,
                )
                nested_ok = bool(out.ok)
                return {
                    "ok": nested_ok,
                    "result": out.to_dict(),
                    "artefacts": [],
                    "error": None if nested_ok else out.reason,
                    "dry_run": bool(out.dry_run),
                }
            except Exception as exc:  # noqa: BLE001
                return {"ok": False, "result": None, "artefacts": [],
                        "error": f"desktop executor unavailable: {exc}"}
        return {"ok": False, "result": None, "artefacts": [],
                "error": f"no executor for action {action!r}"}

    def _dispatch(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        ex = self._executor or self._default_executor
        try:
            outcome = ex(action, params)
            if not isinstance(outcome, dict):
                return {"ok": False, "result": None, "artefacts": [],
                        "error": "executor returned a non-object result"}
            return outcome
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "result": None, "artefacts": [], "error": str(exc)}

    def _publish(self, topic: str, trace_id: str, payload: Dict[str, Any]) -> None:
        if self._bus is None or Thought is None:
            return
        try:
            self._bus.publish(Thought(source="local_action_bridge", topic=topic,
                                      trace_id=trace_id, payload=dict(payload)))
        except Exception as exc:  # noqa: BLE001
            logger.debug("bridge publish failed (%s): %s", topic, exc)

    # ── the one entrypoint ─────────────────────────────────────────────
    def perform(
        self,
        action: str,
        params: Dict[str, Any] | None = None,
        context: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        params = dict(params or {})
        verdict: ActionVerdict = self.gate.ground(action, params, context)
        self._recent.append({"verdict": verdict.verdict, "approved": verdict.approved})

        base = {
            "action": action, "verdict": verdict.verdict, "approved": verdict.approved,
            "reason": verdict.reason, "trace_id": verdict.trace_id,
            "hnc": {
                "symbolic_life_score": verdict.symbolic_life_score,
                "coherence_gamma": verdict.coherence_gamma,
                "cosmic_score": verdict.cosmic_score,
                "gate_open": verdict.gate_open,
            },
            "llm_rationale": verdict.llm_rationale,
        }

        if not verdict.approved:
            self._publish("local.action.abandoned", verdict.trace_id, base)
            return {**base, "ok": False, "blocked": True, "executed": False, "dry_run": False}

        if not self.armed and action not in _DESKTOP_ACTIONS:
            self._publish("local.action.result", verdict.trace_id, {**base, "dry_run": True})
            return {**base, "ok": True, "blocked": False, "executed": False, "dry_run": True,
                    "note": "approved but disarmed — set AUREON_LOCAL_ACTIONS_ARMED=1 to execute"}

        outcome = self._dispatch(action, params)
        outcome_ok = bool(outcome.get("ok"))
        outcome_dry_run = bool(outcome.get("dry_run", False))
        result = {**base, "ok": outcome_ok, "blocked": False,
                  "execution_attempted": True,
                  "executed": outcome_ok and not outcome_dry_run,
                  "dry_run": outcome_dry_run,
                  "result": outcome.get("result"), "error": outcome.get("error")}
        self._publish("local.action.result", verdict.trace_id, result)
        return result

    # ── read side (for the Λ(t) source + /api/action/status) ───────────
    def recent_stats(self) -> Dict[str, Any]:
        n = len(self._recent)
        if n == 0:
            return {"count": 0, "approve_ratio": None, "veto_count": 0}
        approved = sum(1 for r in self._recent if r.get("approved"))
        vetoed = sum(1 for r in self._recent if r.get("verdict") in ("VETOED", "BLOCKED"))
        return {"count": n, "approve_ratio": approved / n, "veto_count": vetoed}


_bridge_singleton: LocalActionBridge | None = None


def get_local_action_bridge() -> LocalActionBridge:
    global _bridge_singleton
    if _bridge_singleton is None:
        _bridge_singleton = LocalActionBridge()
    return _bridge_singleton


__all__ = ["LocalActionBridge", "get_local_action_bridge"]
