"""
SkillExecutorBridge — the system actually builds things
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CURRENT RELEASE: the execution design below is unreleased. Subscription,
conscience calls, threads, executors, CodeArchitect calls, bus publication,
vault ingest, and the fallback file writer all hard-HOLD before any effect.

Operator directive: *"we need to ensure that it's building things and
not just talking."*

Until now:
  PersonaMinerBridge  learned which (persona, intent) pairs succeed and
                      which skill chain made them succeed.
  GoalSkillAligner    republished ``goal.submit.request.aligned`` with
                      ``recommended_skills`` attached — but nothing
                      consumed that signal.

This bridge closes the loop. It subscribes to the aligned topic and,
for each recommended skill, calls a pluggable executor that PRODUCES
AN ARTEFACT — a file on disk, a code module, an image — and ingests
the artefact into the vault as a ``skill.execution.output`` card.

Executor contract (duck-typed):
  executor(skill_name: str, params: dict) -> dict
  returning {ok: bool, artefacts: [path, ...], result: Any, error: str}

Default executor writes a markdown artefact under ``data/skill_outputs/``
stamped with skill name, params, and timestamp — so even without the
real CodeArchitect hooked up, the system demonstrably builds files on
disk. A CodeArchitect adapter can be passed to route into the real
skill library.

Safety: the QueenConscience 4th-pass veto from the HNC white paper is
the only gate on this bridge. When ``conscience`` is attached, every
aligned request passes through ``ask_why`` before any skill runs; a
VETO short-circuits to ``goal.abandoned`` with the substrate-coherence
reason. No other rails.

Publishes per execution:
  skill.execution.started   {goal_id, skill_name, params}
  skill.execution.completed {goal_id, skill_name, artefacts, result}
  skill.execution.failed    {goal_id, skill_name, error}
  goal.completed            when all skills in the chain succeed
                            (closes the TemporalCausalityLaw line)
  goal.abandoned            when any skill fails or is vetoed

Gary Leckey · Aureon Institute — April 2026
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from aureon.vault.voice._goal_claims import GoalClaims

logger = logging.getLogger("aureon.vault.voice.skill_executor_bridge")


SKILL_EXECUTOR_RELEASE_HOLD = (
    "skill_executor_bridge_hold:production_magic_star_release_unavailable"
)


# ─────────────────────────────────────────────────────────────────────────────
# Default file-writing executor — the minimum proof of "building things"
# ─────────────────────────────────────────────────────────────────────────────


def _default_file_executor(
    skill_name: str,
    params: Dict[str, Any],
    *,
    output_root: Path,
) -> Dict[str, Any]:
    """Fallback executor: writes a stamped markdown artefact under
    ``output_root`` so there is always a concrete on-disk artefact when
    no real skill library is wired.

    The artefact carries the skill name, params, timestamp, and (if
    supplied in params) an ``intent_text`` and ``persona``. A real
    CodeArchitect adapter can replace this with actual code/image/pdf
    output — the contract stays {ok, artefacts, result, error}."""
    raise RuntimeError(SKILL_EXECUTOR_RELEASE_HOLD)
    try:
        output_root.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in skill_name)
        stamp = time.strftime("%Y%m%dT%H%M%S")
        unique = uuid.uuid4().hex[:6]
        path = output_root / f"{stamp}-{safe}-{unique}.md"
        body_lines = [
            f"# Aureon skill artefact — {skill_name}",
            f"",
            f"*timestamp: {stamp}*",
            f"*unique_id: {unique}*",
            f"",
            f"## Parameters",
            "```json",
            json.dumps(params, indent=2, default=str, sort_keys=True),
            "```",
        ]
        if "intent_text" in params:
            body_lines += ["", f"## Intent", "", str(params["intent_text"])]
        if "persona" in params:
            body_lines += ["", f"*persona: {params['persona']}*"]
        path.write_text("\n".join(body_lines), encoding="utf-8")
        return {
            "ok": True,
            "artefacts": [str(path)],
            "result": {"bytes": path.stat().st_size},
            "error": "",
        }
    except Exception as e:
        return {"ok": False, "artefacts": [], "result": None, "error": str(e)}


def code_architect_adapter(code_architect: Any) -> Callable:
    """Wrap an existing CodeArchitect instance to conform to the
    executor contract the bridge expects."""
    def _exec(skill_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        raise RuntimeError(SKILL_EXECUTOR_RELEASE_HOLD)
        try:
            result = code_architect.execute_skill(skill_name, params=params)
            # SkillExecutionResult has (ok, artefacts, error) conceptually
            return {
                "ok": bool(getattr(result, "success", False)
                           or getattr(result, "ok", False)),
                "artefacts": list(getattr(result, "artefacts", [])
                                   or getattr(result, "outputs", [])),
                "result": getattr(result, "payload", None)
                          or getattr(result, "result", None),
                "error": str(getattr(result, "error", "") or ""),
            }
        except Exception as e:
            return {"ok": False, "artefacts": [], "result": None, "error": str(e)}
    return _exec


# ─────────────────────────────────────────────────────────────────────────────
# SkillExecutorBridge
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class _ExecutionRecord:
    goal_id: str = ""
    persona: str = ""
    skill_name: str = ""
    artefacts: List[str] = field(default_factory=list)
    ok: bool = False
    error: str = ""
    ts: float = field(default_factory=time.time)


class SkillExecutorBridge:
    """Runs the skill chain attached to ``goal.submit.request.aligned``."""

    def __init__(
        self,
        *,
        thought_bus: Any = None,
        vault: Any = None,
        executor: Optional[Callable] = None,
        conscience: Any = None,
        output_root: Optional[str] = None,
        run_in_thread: bool = True,
    ):
        self.thought_bus = thought_bus
        self.vault = vault
        self.conscience = conscience
        self.output_root = Path(output_root or "data/skill_outputs")
        self._run_in_thread = bool(run_in_thread)

        # Default executor wraps the output_root so it writes to the
        # bridge's configured directory.
        self._executor = executor

        self._lock = threading.RLock()
        self._subscribed = False
        self._history: List[_ExecutionRecord] = []
        self._stats = {
            "claimed": 0, "vetoed": 0, "executed": 0,
            "failed": 0, "abandoned": 0,
        }

    def _build_default_executor(self) -> Callable:
        def _exec(skill_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
            raise RuntimeError(SKILL_EXECUTOR_RELEASE_HOLD)
        return _exec

    # ─── lifecycle ───────────────────────────────────────────────────────

    def start(self) -> None:
        raise RuntimeError(SKILL_EXECUTOR_RELEASE_HOLD)
        if self._subscribed or self.thought_bus is None:
            return
        try:
            self.thought_bus.subscribe(
                "goal.submit.request.aligned", self._on_aligned_request,
            )
            self._subscribed = True
        except Exception as e:
            logger.debug("SkillExecutorBridge: subscribe failed: %s", e)

    # ─── handler ─────────────────────────────────────────────────────────

    def _on_aligned_request(self, thought: Any) -> None:
        raise RuntimeError(SKILL_EXECUTOR_RELEASE_HOLD)
        payload = getattr(thought, "payload", {}) or {}
        if not isinstance(payload, dict):
            return
        goal_id = str(payload.get("goal_id") or "")
        if not goal_id:
            return
        # Claim the goal_id so GoalDispatchBridge skips it.
        if not GoalClaims.claim(goal_id, "skill_executor"):
            return
        with self._lock:
            self._stats["claimed"] += 1

        text = str(payload.get("text") or "")
        persona = str(payload.get("proposed_by_persona") or "")
        recommended = list(payload.get("recommended_skills") or [])
        if not recommended:
            self._publish_abandoned(goal_id, "no recommended_skills",
                                    text=text, persona=persona)
            return

        # Conscience gate — same check as GoalDispatchBridge.
        if self._veto_blocks(text, persona, payload):
            with self._lock:
                self._stats["vetoed"] += 1
            return   # abandoned publish handled inside _veto_blocks

        if self._run_in_thread:
            threading.Thread(
                target=self._run_chain,
                args=(goal_id, persona, text, recommended),
                name=f"SkillExecutor-{goal_id}",
                daemon=True,
            ).start()
        else:
            self._run_chain(goal_id, persona, text, recommended)

    def _veto_blocks(
        self,
        text: str,
        persona: str,
        payload: Dict[str, Any],
    ) -> bool:
        raise RuntimeError(SKILL_EXECUTOR_RELEASE_HOLD)
        if self.conscience is None or not hasattr(self.conscience, "ask_why"):
            return False
        try:
            whisper = self.conscience.ask_why(text, {
                "persona": persona,
                "goal_id": payload.get("goal_id"),
                "urgency": payload.get("urgency"),
            })
        except Exception as e:
            logger.debug("SkillExecutorBridge: conscience failed: %s", e)
            return False
        verdict = getattr(whisper, "verdict", None)
        name = getattr(verdict, "name", "") if verdict is not None else ""
        if str(name).upper() == "VETO":
            reason = (getattr(whisper, "message", "")
                      or getattr(whisper, "why_it_matters", "")
                      or "substrate_coherence: conscience vetoed")
            self._publish_abandoned(str(payload.get("goal_id") or ""),
                                    reason=reason, text=text, persona=persona)
            return True
        return False

    # ─── execution ───────────────────────────────────────────────────────

    def _run_chain(
        self,
        goal_id: str,
        persona: str,
        text: str,
        skills: List[str],
    ) -> None:
        """Run each skill in the chain in order. Any failure aborts the
        chain and closes the goal with goal.abandoned. All success →
        goal.completed with a result_summary listing every artefact."""
        raise RuntimeError(SKILL_EXECUTOR_RELEASE_HOLD)
        all_artefacts: List[str] = []
        for skill_name in skills:
            started_payload = {
                "goal_id": goal_id, "skill_name": skill_name,
                "persona": persona, "params": {"intent_text": text,
                                                "persona": persona,
                                                "goal_id": goal_id},
                "ts": time.time(),
            }
            self._publish("skill.execution.started", started_payload)

            params = {"intent_text": text, "persona": persona, "goal_id": goal_id}
            try:
                result = self._executor(skill_name, params)
            except Exception as e:
                result = {"ok": False, "artefacts": [], "result": None,
                          "error": f"{type(e).__name__}: {e}"}

            ok = bool(result.get("ok"))
            artefacts = list(result.get("artefacts") or [])
            error = str(result.get("error") or "")

            self._record(goal_id, persona, skill_name, artefacts, ok, error)

            if ok:
                all_artefacts.extend(artefacts)
                with self._lock:
                    self._stats["executed"] += 1
                self._publish("skill.execution.completed", {
                    "goal_id": goal_id, "skill_name": skill_name,
                    "artefacts": artefacts,
                    "result": result.get("result"),
                    "ts": time.time(),
                })
                # Ingest each artefact into the vault as its own card.
                self._ingest_artefacts(persona, goal_id, skill_name, artefacts)
            else:
                with self._lock:
                    self._stats["failed"] += 1
                self._publish("skill.execution.failed", {
                    "goal_id": goal_id, "skill_name": skill_name,
                    "error": error, "ts": time.time(),
                })
                self._publish_abandoned(
                    goal_id,
                    reason=f"skill '{skill_name}' failed: {error}",
                    text=text, persona=persona,
                )
                return

        # All skills succeeded → close the line.
        summary = (f"built {len(all_artefacts)} artefact(s) via "
                   f"{len(skills)} skill(s): {', '.join(skills)}")
        self._publish("goal.completed", {
            "goal_id": goal_id, "text": text,
            "result_summary": summary,
            "recommended_skills": list(skills),
            "artefacts": all_artefacts,
            "source": "skill_executor_bridge",
            "ts": time.time(),
        })

    def _record(
        self,
        goal_id: str,
        persona: str,
        skill_name: str,
        artefacts: List[str],
        ok: bool,
        error: str,
    ) -> None:
        with self._lock:
            self._history.append(_ExecutionRecord(
                goal_id=goal_id, persona=persona, skill_name=skill_name,
                artefacts=list(artefacts), ok=ok, error=error,
            ))

    # ─── publishing + vault ingest ──────────────────────────────────────

    def _publish_abandoned(
        self,
        goal_id: str,
        reason: str,
        text: str = "",
        persona: str = "",
    ) -> None:
        raise RuntimeError(SKILL_EXECUTOR_RELEASE_HOLD)
        with self._lock:
            self._stats["abandoned"] += 1
        self._publish("goal.abandoned", {
            "goal_id": goal_id, "reason": reason,
            "text": text, "proposed_by_persona": persona,
            "source": "skill_executor_bridge", "ts": time.time(),
        })

    def _publish(self, topic: str, payload: Dict[str, Any]) -> None:
        raise RuntimeError(SKILL_EXECUTOR_RELEASE_HOLD)
        if self.thought_bus is None:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought
            self.thought_bus.publish(Thought(
                source="skill_executor_bridge",
                topic=topic, payload=payload,
            ))
        except Exception as e:
            logger.debug("SkillExecutorBridge: publish %s failed: %s", topic, e)

    def _ingest_artefacts(
        self,
        persona: str,
        goal_id: str,
        skill_name: str,
        artefacts: List[str],
    ) -> None:
        raise RuntimeError(SKILL_EXECUTOR_RELEASE_HOLD)
        if self.vault is None or not hasattr(self.vault, "ingest"):
            return
        for path in artefacts:
            try:
                self.vault.ingest(
                    topic="skill.execution.output",
                    payload={
                        "persona": persona,
                        "goal_id": goal_id,
                        "skill_name": skill_name,
                        "artefact_path": str(path),
                        "ts": time.time(),
                    },
                )
            except Exception as e:
                logger.debug("SkillExecutorBridge: vault ingest failed: %s", e)

    # ─── introspection ───────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return dict(
                self._stats,
                status="HOLD",
                reason_code="production_magic_star_release_unavailable",
                production_ready=False,
                effect_enabled=False,
                subscribed=self._subscribed,
                output_root=str(self.output_root),
            )

    def history(self, n: int = 32) -> List[Dict[str, Any]]:
        with self._lock:
            tail = self._history[-int(max(1, n)):]
        return [
            {
                "ts": r.ts, "goal_id": r.goal_id, "persona": r.persona,
                "skill_name": r.skill_name, "artefacts": list(r.artefacts),
                "ok": r.ok, "error": r.error,
            }
            for r in tail
        ]


# ─────────────────────────────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────────────────────────────


_singleton: Optional[SkillExecutorBridge] = None
_singleton_lock = threading.Lock()


def get_skill_executor_bridge(
    thought_bus: Any = None,
    vault: Any = None,
    executor: Optional[Callable] = None,
    conscience: Any = None,
) -> SkillExecutorBridge:
    raise RuntimeError(SKILL_EXECUTOR_RELEASE_HOLD)
    global _singleton
    with _singleton_lock:
        if _singleton is None:
            _singleton = SkillExecutorBridge(
                thought_bus=thought_bus, vault=vault,
                executor=executor, conscience=conscience,
            )
            _singleton.start()
        else:
            if thought_bus is not None and _singleton.thought_bus is None:
                _singleton.thought_bus = thought_bus
                _singleton.start()
            if vault is not None and _singleton.vault is None:
                _singleton.vault = vault
        return _singleton


def reset_skill_executor_bridge() -> None:
    global _singleton
    with _singleton_lock:
        _singleton = None


__all__ = [
    "SKILL_EXECUTOR_RELEASE_HOLD",
    "SkillExecutorBridge",
    "code_architect_adapter",
    "get_skill_executor_bridge",
    "reset_skill_executor_bridge",
]
