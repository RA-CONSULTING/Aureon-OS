"""
Aureon Operator — dataclass schemas.

One ``OperatorResponse`` falls out of the switchboard: the single grounded
answer, plus the full provenance (which lines answered, what the repo grounded
it on, how the answers agreed, and what the conscience said). Every field is
JSON-serialisable via ``.to_dict()`` so the SSE stream and CLI can render it.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ProviderAnswer:
    """One line's reply on the switchboard."""

    provider: str = ""
    model: str = ""
    text: str = ""
    ok: bool = True
    latency_ms: float = 0.0
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "text": self.text,
            "ok": self.ok,
            "latency_ms": round(float(self.latency_ms), 2),
            "error": self.error,
        }


@dataclass
class GroundingContext:
    """What the Aureon repo grounded the prompt on."""

    sources: List[Dict[str, str]] = field(default_factory=list)  # {title, path}
    lane: str = ""
    task_family: str = ""
    system_prompt_chars: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sources": list(self.sources),
            "lane": self.lane,
            "task_family": self.task_family,
            "system_prompt_chars": int(self.system_prompt_chars),
            "source_count": len(self.sources),
        }


@dataclass
class ConsensusReading:
    """How the N provider answers agreed before collapse."""

    n_answers: int = 0
    agreement: float = 0.0            # 0..1 mean pairwise overlap
    winner: str = ""                  # provider name of the collapsed answer
    runner_ups: List[str] = field(default_factory=list)
    synthesized: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_answers": int(self.n_answers),
            "agreement": round(float(self.agreement), 4),
            "winner": self.winner,
            "runner_ups": list(self.runner_ups),
            "synthesized": self.synthesized,
        }


@dataclass
class OperatorResponse:
    """The single colour that falls out of the switchboard prism."""

    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    prompt: str = ""
    submitted_at: float = field(default_factory=time.time)
    session_id: str | None = None

    text: str = ""                       # the grounded, collapsed, vetted answer
    grounding: GroundingContext | None = None
    answers: List[ProviderAnswer] = field(default_factory=list)
    consensus: ConsensusReading | None = None
    conscience_verdict: str = "APPROVED"
    conscience_message: str = ""
    blocked: bool = False                # True when the conscience vetoed
    reply_contained: bool = False        # True when the flagship reply tripped the brain-reply membrane
    phase_thought_ids: Dict[str, str] = field(default_factory=dict)
    elapsed_ms: float = 0.0
    errors: List[Dict[str, Any]] = field(default_factory=list)

    def status(self) -> str:
        """Honest turn classification: ``ok`` | ``honest_unavailable`` | ``fault``.
        Every line down (no provider answered) is the switchboard saying it
        cannot reason right now; a veto stays ``ok`` (``blocked`` carries it)."""
        if self.answers and all(not a.ok for a in self.answers):
            return "honest_unavailable"
        if not self.answers and not self.text:
            return "fault" if self.errors else "honest_unavailable"
        return "ok"

    def envelope(self) -> Dict[str, Any]:
        """The same enforced response envelope the cognition door wears —
        sources named or 'general knowledge, no repo hit' stated, conscience
        verdict, trace id, honest status — so both engines answer in one shape."""
        sources = [dict(s) for s in (self.grounding.sources if self.grounding else [])]
        return {
            "trace_id": self.trace_id,
            "status": self.status(),
            "grounded": bool(sources),
            "sources": sources,
            "sources_statement": (f"{len(sources)} repo packet(s) cited" if sources
                                  else "general knowledge, no repo hit"),
            "conscience": {"verdict": self.conscience_verdict, "blocked": self.blocked},
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "prompt": self.prompt,
            "submitted_at": round(float(self.submitted_at), 3),
            "session_id": self.session_id,
            "text": self.text,
            "grounding": self.grounding.to_dict() if self.grounding else None,
            "answers": [a.to_dict() for a in self.answers],
            "consensus": self.consensus.to_dict() if self.consensus else None,
            "conscience_verdict": self.conscience_verdict,
            "conscience_message": self.conscience_message,
            "blocked": self.blocked,
            "reply_contained": self.reply_contained,
            "phase_thought_ids": dict(self.phase_thought_ids),
            "elapsed_ms": round(float(self.elapsed_ms), 2),
            "errors": list(self.errors),
            "envelope": self.envelope(),
        }


@dataclass
class ToolInvocation:
    """One tool the cognition called during its agentic loop."""

    tool: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    blocked: bool = False
    phase: str = ""
    effect: str = ""
    operation_id: str = ""
    proposal_digest: str = ""
    authorization_digest: str = ""
    governance_receipt_id: str | None = None
    dual_key_receipt_id: str | None = None
    dual_key_receipt: Dict[str, Any] | None = None
    route_authority_receipt_id: str | None = None
    route_authority_request_digest: str | None = None
    route_authority_receipt: Dict[str, Any] | None = None
    hnc_outcome: str = ""
    hnc_decision_receipt_id: str | None = None
    hnc_repair_safe: bool = False
    governance_decision: str = ""
    governance_reason: str = ""
    handler_called: bool = False
    result_digest: str = ""
    governance_eligible: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.tool,
            "arguments": self.arguments,
            "blocked": self.blocked,
            "phase": self.phase,
            "effect": self.effect,
            "operation_id": self.operation_id,
            "proposal_digest": self.proposal_digest,
            "authorization_digest": self.authorization_digest,
            "governance_receipt_id": self.governance_receipt_id,
            "dual_key_receipt_id": self.dual_key_receipt_id,
            "dual_key_receipt": self.dual_key_receipt,
            "route_authority_receipt_id": self.route_authority_receipt_id,
            "route_authority_request_digest": self.route_authority_request_digest,
            "route_authority_receipt": self.route_authority_receipt,
            "hnc_outcome": self.hnc_outcome,
            "hnc_decision_receipt_id": self.hnc_decision_receipt_id,
            "hnc_repair_safe": self.hnc_repair_safe,
            "governance_decision": self.governance_decision,
            "governance_reason": self.governance_reason,
            "handler_called": self.handler_called,
            "result_digest": self.result_digest,
            "governance_eligible": self.governance_eligible,
        }


@dataclass
class CognitionResult:
    """The output of the agentic cognition: an answer plus its full provenance."""

    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    prompt: str = ""
    submitted_at: float = field(default_factory=time.time)
    session_id: str | None = None

    text: str = ""
    grounding: GroundingContext | None = None
    tool_calls: List[ToolInvocation] = field(default_factory=list)
    turns: int = 0
    conscience_verdict: str = "APPROVED"
    conscience_message: str = ""
    queen_evaluated: bool = False
    queen_evidence: Dict[str, Any] | None = None
    governance: Dict[str, Any] | None = None
    blocked: bool = False
    grounded: bool = False           # True when a repo source informed the answer
    elapsed_ms: float = 0.0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    capability: Dict[str, Any] | None = None   # goal-capability classification
    swarm: Dict[str, Any] | None = None        # routing-council report (complex prompts)
    actualization: Dict[str, Any] | None = None  # Film-Reel ledger: realized vs parked
    bake: Dict[str, Any] | None = None           # bake cycle: completeness + refinement
    acquisition: Dict[str, Any] | None = None    # Borg loop: gaps found → tools reached
    assimilation: Dict[str, Any] | None = None   # controlled write-back verdict
    coherence_gate: Dict[str, Any] | None = None  # the field's capability aperture
    heart: Dict[str, Any] | None = None           # heart charter: alive / love / power

    def knowledge_reach(self) -> List[str]:
        """The knowledge classes this answer MEASURABLY rested on — derived
        from the grounding record and the executed tool ledger, never
        self-reported: repo | web | skills | live_state | tools | general_knowledge."""
        reach: List[str] = []
        if self.grounded:
            reach.append("repo")
        used = {t.tool for t in self.tool_calls if not t.blocked}
        if used & {"web_search", "web_fetch"}:
            reach.append("web")
        if "list_skills" in used:
            reach.append("skills")
        if used & {"read_state", "read_positions", "read_prices"}:
            reach.append("live_state")
        if used - {"web_search", "web_fetch", "list_skills",
                   "read_state", "read_positions", "read_prices"}:
            reach.append("tools")
        return reach or ["general_knowledge"]

    def reach_class(self) -> str:
        """The coarse reach taxonomy: ``local`` (repo/skills/state/tools only),
        ``acquired`` (network only), ``mixed`` (both), ``none`` (model
        knowledge alone) — derived from the measured reach, never self-reported."""
        classes = set(self.knowledge_reach())
        acquired = "web" in classes
        local = bool(classes & {"repo", "skills", "live_state", "tools"})
        if acquired and local:
            return "mixed"
        if acquired:
            return "acquired"
        if local:
            return "local"
        return "none"

    def status(self) -> str:
        """Honest turn classification: ``ok`` | ``honest_unavailable`` | ``fault``.

        A conscience veto or boundary refusal is still ``ok`` — the pipeline
        worked as designed (``blocked`` carries the refusal). ``honest_unavailable``
        is the adapter saying it cannot reason right now (offline/keyless), and
        ``fault`` is the loop itself breaking.
        """
        text = self.text or ""
        if text.startswith("[cognition error]"):
            return "fault"
        if text.startswith("[ERROR]"):
            return "honest_unavailable"
        return "ok"

    def envelope(self) -> Dict[str, Any]:
        """The enforced response envelope: every answer names its sources (or
        states plainly there were none), its coherence, its conscience verdict,
        and its trace — nothing leaves the one door unlabeled."""
        sources = [dict(s) for s in (self.grounding.sources if self.grounding else [])]
        cap = self.capability or {}
        if self.swarm:
            coherence: Dict[str, Any] | None = {
                "source": "swarm_council",
                "gamma_by_cluster": dict(self.swarm.get("clusters", {})),
                "lead_family": self.swarm.get("lead"),
            }
        else:
            coherence = None
        return {
            "trace_id": self.trace_id,
            "status": self.status(),
            "grounded": self.grounded,
            "sources": sources,
            "sources_statement": (f"{len(sources)} repo packet(s) cited" if sources
                                  else "general knowledge, no repo hit"),
            "conscience": {"verdict": self.conscience_verdict, "blocked": self.blocked},
            "queen": {
                "evaluated": self.queen_evaluated,
                "evidence": dict(self.queen_evidence) if self.queen_evidence else None,
            },
            "governance": dict(self.governance) if self.governance else None,
            "capability": {"families": list(cap.get("families", [])),
                           "complex": bool(cap.get("complex", False)),
                           "status": cap.get("status", "unavailable")},
            "coherence": coherence,
            "actualization": dict(self.actualization) if self.actualization else None,
            "bake": dict(self.bake) if self.bake else None,
            "knowledge_reach": self.knowledge_reach(),
            "reach_class": self.reach_class(),
            "acquisition": dict(self.acquisition) if self.acquisition else None,
            "assimilation": ({"assimilated": bool(self.assimilation.get("assimilated"))}
                             if self.assimilation else None),
            "coherence_gate": dict(self.coherence_gate) if self.coherence_gate else None,
            "heart": dict(self.heart) if self.heart else None,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "prompt": self.prompt,
            "submitted_at": round(float(self.submitted_at), 3),
            "session_id": self.session_id,
            "text": self.text,
            "grounding": self.grounding.to_dict() if self.grounding else None,
            "tool_calls": [t.to_dict() for t in self.tool_calls],
            "turns": int(self.turns),
            "conscience_verdict": self.conscience_verdict,
            "conscience_message": self.conscience_message,
            "queen_evaluated": self.queen_evaluated,
            "queen_evidence": dict(self.queen_evidence) if self.queen_evidence else None,
            "governance": dict(self.governance) if self.governance else None,
            "blocked": self.blocked,
            "grounded": self.grounded,
            "elapsed_ms": round(float(self.elapsed_ms), 2),
            "errors": list(self.errors),
            "capability": dict(self.capability) if self.capability else None,
            "swarm": dict(self.swarm) if self.swarm else None,
            "actualization": dict(self.actualization) if self.actualization else None,
            "bake": dict(self.bake) if self.bake else None,
            "acquisition": dict(self.acquisition) if self.acquisition else None,
            "assimilation": dict(self.assimilation) if self.assimilation else None,
            "coherence_gate": dict(self.coherence_gate) if self.coherence_gate else None,
            "heart": dict(self.heart) if self.heart else None,
            "envelope": self.envelope(),
        }


__all__ = [
    "ProviderAnswer",
    "GroundingContext",
    "ConsensusReading",
    "OperatorResponse",
    "ToolInvocation",
    "CognitionResult",
]
