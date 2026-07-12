"""
🧠 AUREON COGNITION — the agentic mind.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"Ground it in the repo, reach for tools, answer anything — then let the
conscience have the last word."

Where :class:`AureonOperator` fans one question across many models and collapses
them, :class:`AureonCognition` is the single-mind agentic mode: it grounds the
prompt in the whole repo, runs a tool-using loop (write code, search online,
read the repo, check trading state), and answers any domain — particle physics,
cosmology, the meaning of life, dealing with depression, baking a cake.

It is composition of parts that already exist:
  ground   →  repo-wide index (aureon/operator/repo_index) + relaxed persona
  loop     →  AgentRunner + a guarded ToolRegistry (aureon/operator/tools)
  veto     →  hard authority boundary + QueenConscience (aureon_operator)
  fabric   →  thought bus (operator.cognition.*) + mycelium broadcast, one trace_id

Every consequential tool call is vetted BEFORE it runs (GuardedToolRegistry), and
the whole turn is bounded by the same offline/audit guards as the rest of Aureon.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

try:
    from aureon.core.aureon_baton_link import link_system as _baton_link

    _baton_link(__name__)
except Exception:  # noqa: BLE001
    pass

from aureon.inhouse_ai.agent_runner import AgentRunner
from aureon.inhouse_ai.llm_adapter import LLMAdapter
from aureon.operator.aureon_operator import (
    _OPERATOR_PERSONA,
    _hard_boundary_violation,
    broadcast_to_mesh,
    join_organism,
)
from aureon.operator.config import OperatorConfig
from aureon.operator.providers import build_provider_set
from aureon.operator.repo_index import REPO_ROOT, repo_search
from aureon.operator.schemas import CognitionResult, GroundingContext, ToolInvocation
from aureon.operator.tools import build_operator_tools

logger = logging.getLogger("aureon.operator.cognition")

try:
    from aureon.core.aureon_thought_bus import Thought, get_thought_bus

    _HAS_BUS = True
except Exception:  # noqa: BLE001
    get_thought_bus = None  # type: ignore
    Thought = None  # type: ignore
    _HAS_BUS = False

# Grounding gate. A keyword index over 2000+ files gives even off-repo prompts a
# non-trivial TF-IDF sum (common English vocabulary is everywhere), so a single
# absolute floor can't separate "Aureon operator correlation" (155) from "healthy
# ways to deal with stress" (87). We use a hybrid gate instead:
#   ground  IF  top_score >= _HIGH_FLOOR                 (unmistakably Aureon-specific)
#           OR  (top_score >= _MID_FLOOR AND the prompt names an Aureon-domain term)
# Otherwise the prompt is treated as general-domain: answer from general knowledge,
# no repo citation. (A semantic/embedding index would sharpen this; documented as
# a keyword-index heuristic.)
_HIGH_FLOOR = 90.0
_MID_FLOOR = 30.0
_SNIPPET_FLOOR = 30.0
_DOMAIN_TERMS = frozenset((
    "aureon", "hnc", "harmonic", "queen", "operator", "mycelium", "nexus", "phi",
    "schumann", "lambda", "auris", "seer", "lighthouse", "stargate", "ghost",
    "coherence", "sero", "leckey", "ziggurat", "kelly", "veto", "conscience",
    "trade", "trading", "market", "bot", "exchange", "kraken", "binance", "alpaca",
    "repo", "repository", "correlation", "node", "master formula", "falsification",
))


def _has_domain_term(prompt: str) -> bool:
    low = f" {prompt.lower()} "
    return any(term in low for term in _DOMAIN_TERMS)


_QA_PATH = REPO_ROOT / "data" / "datasets" / "aureon_qa_dataset.json"
_TOOL_HINT = (
    "\n\nYou can call tools when they help: repo_search (search the whole Aureon "
    "repo), read_repo_file, list_repo, web_search, web_fetch, code_validate, "
    "write_repo_file, patch_repo_file, read_state/read_positions/read_prices. "
    "Prefer repo_search to ground Aureon-specific claims."
)


class AureonCognition:
    """Single-mind agentic cognition: ground → tool-loop → veto, fully traced."""

    def __init__(
        self,
        adapter: Optional[LLMAdapter] = None,
        *,
        tools=None,
        bus: Any = None,
        conscience: Any = None,
        config: Optional[OperatorConfig] = None,
        allow_writes: bool = True,
        allow_shell: bool = True,
        max_turns: int = 6,
        join_mesh: bool = True,
        source: str = "aureon.cognition",
    ) -> None:
        self.config = config or OperatorConfig.from_env()
        self.adapter = adapter or self._default_adapter()
        self.tools = tools or build_operator_tools(allow_writes=allow_writes, allow_shell=allow_shell)
        self.max_turns = max_turns
        self.source = source
        self._conscience = conscience
        self._conscience_loaded = conscience is not None
        self.last_mesh_message: Dict[str, Any] = {}
        if bus is not None:
            self.bus = bus
        elif _HAS_BUS and get_thought_bus is not None:
            self.bus = get_thought_bus()
        else:
            self.bus = None
        if join_mesh:
            join_organism(self, "aureon_cognition")

    @staticmethod
    def _default_adapter() -> LLMAdapter:
        providers = build_provider_set()
        # Single primary line for the agentic loop (first available).
        return next(iter(providers.values()))

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def reason(self, prompt: str, session_id: Optional[str] = None) -> CognitionResult:
        started = time.time()
        res = CognitionResult(trace_id=uuid.uuid4().hex, prompt=prompt,
                              submitted_at=started, session_id=session_id)
        self._publish(res, "boot", {"prompt": prompt, "tools": self.tools.names()})

        # Prompt-level hard boundary: refuse before any model/tool runs.
        if _hard_boundary_violation(prompt):
            res.blocked = True
            res.conscience_verdict = "VETO"
            res.conscience_message = (
                "This request crosses a hard Aureon authority boundary "
                "(live trading, payment, safety-gate bypass, credential, or filing)."
            )
            res.text = f"🦗 Blocked at the Aureon authority boundary.\nReason: {res.conscience_message}"
            res.elapsed_ms = (time.time() - started) * 1000.0
            self._publish(res, "complete", res.to_dict())
            return res

        system_prompt = self._ground(prompt, res)
        self._run_loop(prompt, system_prompt, res)
        self._veto(prompt, res)

        res.elapsed_ms = (time.time() - started) * 1000.0
        self._publish(res, "complete", res.to_dict())
        broadcast_to_mesh("cognition.answer", {"trace_id": res.trace_id, "grounded": res.grounded,
                                               "verdict": res.conscience_verdict, "blocked": res.blocked})
        return res

    def stream_events(self, prompt: str, session_id: Optional[str] = None) -> Generator[Dict[str, Any], None, None]:
        res = self.reason(prompt, session_id=session_id)
        yield {"type": "grounding", "detail": res.grounding.to_dict() if res.grounding else {}}
        for t in res.tool_calls:
            yield {"type": "tool", "detail": t.to_dict()}
        yield {"type": "veto", "detail": {"verdict": res.conscience_verdict, "blocked": res.blocked}}
        for word in (res.text or "").split(" "):
            yield {"type": "token", "text": word + " "}
        yield {"type": "complete", "response": res.to_dict()}

    # ------------------------------------------------------------------
    # Ground
    # ------------------------------------------------------------------

    def _ground(self, prompt: str, res: CognitionResult) -> str:
        sources: List[Dict[str, str]] = []
        blocks: List[str] = []
        try:
            hits = repo_search(prompt, top_k=4)
            top = hits[0].score if hits else 0.0
            is_grounded = top >= _HIGH_FLOOR or (top >= _MID_FLOOR and _has_domain_term(prompt))
            if is_grounded:
                for s in hits:
                    if s.score < _SNIPPET_FLOOR:
                        continue
                    sources.append({"title": s.doc_id, "path": s.doc_id})
                    blocks.append(f"[{s.doc_id}] {s.text[:400]}")
        except Exception as exc:  # noqa: BLE001
            logger.debug("repo grounding failed: %s", exc)
            res.errors.append({"phase": "ground", "error": str(exc)})

        qa = self._life_questions_snippet(prompt)
        if qa:
            blocks.append(f"[aureon_qa_dataset] {qa}")

        system = _OPERATOR_PERSONA
        if blocks:
            system += "\n\nGrounded Aureon context (cite when relevant):\n" + "\n\n".join(blocks)[:4000]
        system += _TOOL_HINT

        res.grounded = bool(sources)
        res.grounding = GroundingContext(sources=sources, lane="cognition",
                                         task_family="general", system_prompt_chars=len(system))
        self._publish(res, "ground", res.grounding.to_dict())
        return system

    @staticmethod
    def _life_questions_snippet(prompt: str) -> str:
        """Best-effort match against the 106 universal-life-questions dataset."""
        try:
            data = json.loads(_QA_PATH.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return ""
        answers = data.get("answers") or []
        toks = {w for w in prompt.lower().split() if len(w) > 3}
        best, best_score = None, 0
        for item in answers:
            q = str(item.get("question", "")).lower()
            score = sum(1 for t in toks if t in q)
            if score > best_score:
                best, best_score = item, score
        if best and best_score >= 2:
            return f"Q: {best.get('question','')}\nAureon: {str(best.get('answer',''))[:500]}"
        return ""

    # ------------------------------------------------------------------
    # Agentic loop
    # ------------------------------------------------------------------

    def _run_loop(self, prompt: str, system_prompt: str, res: CognitionResult) -> None:
        runner = AgentRunner(self.adapter, tools=self.tools, system_prompt=system_prompt,
                             max_turns=self.max_turns)

        def _on_tool_call(name: str, args: Dict[str, Any]) -> None:
            res.tool_calls.append(ToolInvocation(tool=name, arguments=dict(args or {})))
            self._publish(res, "tool", {"tool": name, "arguments": args})
            broadcast_to_mesh("cognition.tool", {"trace_id": res.trace_id, "tool": name})

        runner.on_tool_call = _on_tool_call
        try:
            text = runner.turn(prompt)
        except Exception as exc:  # noqa: BLE001 — a loop failure must not crash cognition
            logger.warning("agentic loop failed: %s", exc)
            res.errors.append({"phase": "loop", "error": str(exc)})
            text = f"[cognition error] {exc}"

        res.text = (text or "").strip()
        res.turns = getattr(runner, "_turn_count", 0)
        # Reconcile which tool calls were blocked by the guard.
        blocked_tools = {b["tool"] for b in getattr(self.tools, "blocked_calls", [])}
        for tc in res.tool_calls:
            if tc.tool in blocked_tools:
                tc.blocked = True
        self._publish(res, "loop", {"turns": res.turns, "n_tools": len(res.tool_calls)})

    # ------------------------------------------------------------------
    # Veto
    # ------------------------------------------------------------------

    def _veto(self, prompt: str, res: CognitionResult) -> None:
        conscience = self._get_conscience()
        if conscience is None:
            res.conscience_verdict = "APPROVED"
            self._publish(res, "veto", {"verdict": "APPROVED", "available": False})
            return
        try:
            whisper = conscience.ask_why(
                f"answer cognition prompt: {prompt[:160]}",
                {"answer_preview": res.text[:400], "grounded": res.grounded,
                 "tools_used": [t.tool for t in res.tool_calls]},
            )
            verdict = getattr(whisper.verdict, "name", str(whisper.verdict))
            res.conscience_verdict = verdict
            res.conscience_message = str(getattr(whisper, "message", "") or "")
            if verdict == "VETO":
                res.blocked = True
                res.text = f"🦗 The Queen's conscience vetoed this answer.\nReason: {res.conscience_message}"
        except Exception as exc:  # noqa: BLE001
            logger.debug("conscience unavailable: %s", exc)
            res.conscience_verdict = "APPROVED"
            res.errors.append({"phase": "veto", "error": str(exc)})
        self._publish(res, "veto", {"verdict": res.conscience_verdict, "blocked": res.blocked})

    def _get_conscience(self):
        if self._conscience_loaded:
            return self._conscience
        self._conscience_loaded = True
        try:
            from aureon.queen.queen_conscience import QueenConscience

            self._conscience = QueenConscience()
        except Exception as exc:  # noqa: BLE001
            logger.debug("QueenConscience unavailable: %s", exc)
            self._conscience = None
        return self._conscience

    # ------------------------------------------------------------------
    # Mesh + transport
    # ------------------------------------------------------------------

    def receive_mycelium_message(self, message_type: str, payload: Dict[str, Any]) -> None:
        self.last_mesh_message = {"type": message_type, "payload": payload}

    def _publish(self, res: CognitionResult, phase: str, payload: Dict[str, Any]) -> None:
        topic = "cognition.complete" if phase == "complete" else f"operator.cognition.{phase}"
        if self.bus is None or Thought is None:
            return
        try:
            self.bus.publish(Thought(source=self.source, topic=topic, trace_id=res.trace_id,
                                     payload=dict(payload), meta={"phase": phase}))
        except Exception as exc:  # noqa: BLE001
            logger.debug("cognition publish failed (%s): %s", topic, exc)


def run_cognition(prompt: str, **kwargs) -> CognitionResult:
    """Convenience one-shot."""
    return AureonCognition(**kwargs).reason(prompt)


__all__ = ["AureonCognition", "run_cognition"]
