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
    phase_thought_ids: Dict[str, str] = field(default_factory=dict)
    elapsed_ms: float = 0.0
    errors: List[Dict[str, Any]] = field(default_factory=list)

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
            "phase_thought_ids": dict(self.phase_thought_ids),
            "elapsed_ms": round(float(self.elapsed_ms), 2),
            "errors": list(self.errors),
        }


@dataclass
class ToolInvocation:
    """One tool the cognition called during its agentic loop."""

    tool: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    blocked: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {"tool": self.tool, "arguments": self.arguments, "blocked": self.blocked}


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
    blocked: bool = False
    grounded: bool = False           # True when a repo source informed the answer
    elapsed_ms: float = 0.0
    errors: List[Dict[str, Any]] = field(default_factory=list)

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
            "blocked": self.blocked,
            "grounded": self.grounded,
            "elapsed_ms": round(float(self.elapsed_ms), 2),
            "errors": list(self.errors),
        }


__all__ = [
    "ProviderAnswer",
    "GroundingContext",
    "ConsensusReading",
    "OperatorResponse",
    "ToolInvocation",
    "CognitionResult",
]
