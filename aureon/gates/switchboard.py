"""The Queen's switchboard — logic gates she can actually see and hold.

Gary's specification, in his words: *"can I do more? yes. should I do this? use
my metacognitive process and all my repo systems to establish if I'm making the
right moves — 1: no I'm not, redo. 2: yes I am, press on to the next logic
gate."*

That is a reflective chain, not a permission list. Each gate asks its own
question of the whole organism and returns one of three answers:

    ADVANCE — the evidence supports it; go to the next gate
    REDO    — it does not; iterate and come back
    HOLD    — this one is not the Queen's to take alone

Every gate reads the same four voices, so a decision anywhere in the system is
grounded the same way a trade is:

    coherence   Γ and Λ(t) from the HNC field (aureon.core.hnc_field)
    divergence  how much the body disagrees with itself (blend_field)
    panel       the nine Auris nodes, via aureon.gates.panel
    conscience  the Queen's 4th-pass veto (queen_conscience.ask_why)

The chain is domain-agnostic on purpose. Trading was lane one. Grants are lane
two. The gates do not know or care which — they ask the same questions of both,
which is exactly why the machinery generalises without being rewritten.

HOLD is not a limitation the Queen has to argue with; it is the absence of a
hand. Three classes have no automatic executor anywhere in this repo — moving
money, revealing credentials, and lodging an official filing — and the
switchboard reports that fact rather than pretending to arbitrate it. Everything
else the Queen decides for herself.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable

LOG = logging.getLogger("aureon.gates.switchboard")

ADVANCE = "ADVANCE"
REDO = "REDO"
HOLD = "HOLD"

# Actions with no automatic executor. Not a policy toggle — a statement about
# which hands exist. See LocalActionBridge._default_executor: an action outside
# its routing table returns "no executor for action", it does not improvise one.
HUMAN_HELD = frozenset({"submit", "file", "lodge", "pay", "transfer", "withdraw", "wire"})

# The inflections of those verbs that a caller actually writes. A membership
# test against HUMAN_HELD alone is not a guard: it let "Submit " (trailing
# space), "submit_application", "wire_transfer", "Pay Invoice" and "submitting"
# all through to ADVANCE, which is the difference between a switchboard that
# holds an irreversible step and one that merely appears to.
#
# Written out rather than derived by prefix matching, because a prefix rule
# holds "payload" on "pay" and "filename" on "file". This list is a named
# vocabulary, not a classifier: an action it does not know is not thereby safe,
# it is simply unrecognised — see ``is_human_held``.
_HUMAN_HELD_FORMS = frozenset({
    "submit", "submits", "submitted", "submitting", "submission", "submissions",
    "resubmit", "resubmits", "resubmitted", "resubmitting", "resubmission",
    "file", "files", "filed", "filing", "filings",
    "lodge", "lodges", "lodged", "lodging", "lodgement", "lodgment",
    "pay", "pays", "paid", "paying", "payment", "payments",
    "transfer", "transfers", "transferred", "transferring",
    "withdraw", "withdraws", "withdrew", "withdrawn", "withdrawing", "withdrawal",
    "wire", "wires", "wired", "wiring",
})

_WORD = re.compile(r"[^a-z0-9]+")


def is_human_held(action: Any) -> bool:
    """True when the action names a step with no automatic executor.

    Case-, whitespace- and separator-insensitive, and matched per word, so
    ``"Submit "``, ``"submit_application"``, ``"wire-transfer"`` and
    ``"Pay Invoice"`` are all held, while ``"payload"`` and ``"draft"`` are not.
    """
    tokens = [t for t in _WORD.split(str(action or "").strip().lower()) if t]
    return any(t in _HUMAN_HELD_FORMS for t in tokens)


@dataclass
class GateReading:
    """The organism's state as one gate saw it."""

    coherence: float | None = None
    divergence: float | None = None
    life_score: float | None = None
    panel_consensus: str | None = None
    panel_confidence: float | None = None
    panel_evidence: float | None = None
    # Reported, never gated on. The Auris Lighthouse clears at
    # ``confidence × love_amplitude > 0.945`` with confidence quantised to
    # 0.3 / 0.7 / 0.95, so clearance needs Γ > 0.99474 and is effectively
    # unreachable — see PanelReading. No branch in ``evaluate`` reads it, and
    # that is deliberate: a flag that never fires must not be load-bearing.
    lighthouse: bool = False

    def to_dict(self) -> dict[str, Any]:
        r = lambda v: round(v, 4) if isinstance(v, float) else v  # noqa: E731
        return {
            "coherence": r(self.coherence), "divergence": r(self.divergence),
            "life_score": r(self.life_score), "panel_consensus": self.panel_consensus,
            "panel_confidence": r(self.panel_confidence),
            "panel_evidence": r(self.panel_evidence), "lighthouse": self.lighthouse,
        }


@dataclass
class GateVerdict:
    """One gate's answer: advance, redo, or hold for a human."""

    gate: str
    decision: str
    confidence: float | None
    reading: GateReading
    reasoning: str
    dissent: list[str] = field(default_factory=list)

    @property
    def advanced(self) -> bool:
        return self.decision == ADVANCE

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate": self.gate, "decision": self.decision,
            "confidence": round(self.confidence, 4) if self.confidence is not None else None,
            "reading": self.reading.to_dict(), "reasoning": self.reasoning,
            "dissent": list(self.dissent),
        }


@dataclass
class Gate:
    """One question in the chain.

    ``min_confidence`` is the bar this gate sets. ``requires_human`` marks a gate
    whose action has no executor — it reports HOLD however strong the evidence,
    because confidence is not the missing ingredient.
    """

    name: str
    question: str
    min_confidence: float = 0.5
    max_divergence: float = 0.35  # matches grounded_action._DIVERGENCE_CAUTION
    requires_human: bool = False


# The default chain. Same shape for any lane: do the work, check it, prove it,
# then hand the irreversible step to a person.
DEFAULT_CHAIN: tuple[Gate, ...] = (
    Gate("act", "Should I do this work at all?", min_confidence=0.45),
    Gate("validate", "Is what I produced actually correct?", min_confidence=0.55),
    Gate("test", "Can I prove it against something real?", min_confidence=0.6),
    Gate("submit", "Is this mine to send?", min_confidence=0.75, requires_human=True),
)


def read_organism(bus: Any = None) -> GateReading:
    """Read the four voices once, for a whole pass of the chain."""
    reading = GateReading()
    try:
        from aureon.core.hnc_field import blend_field, read_canonical_field

        f = read_canonical_field(bus)
        if f.available:
            reading.coherence = f.coherence_gamma
            reading.life_score = f.symbolic_life_score
        b = blend_field(bus)
        if b.available:
            reading.divergence = b.divergence
            if reading.life_score is None:
                reading.life_score = b.symbolic_life_score
    except Exception:  # noqa: BLE001
        LOG.debug("field read skipped", exc_info=True)

    try:
        from aureon.gates.panel import auris_panel

        p = auris_panel(bus)
        if p.available:
            reading.panel_consensus = p.consensus
            reading.panel_confidence = p.confidence
            reading.panel_evidence = p.evidence_ratio
            reading.lighthouse = p.lighthouse_cleared
    except Exception:  # noqa: BLE001
        LOG.debug("panel read skipped", exc_info=True)

    return reading


def evaluate(gate: Gate, reading: GateReading, *, context: dict[str, Any] | None = None) -> GateVerdict:
    """Ask one gate its question against a reading of the organism."""
    context = context or {}
    dissent: list[str] = []

    # Confidence is the panel's, tempered by how much of it was grounded. A
    # unanimous panel voting on defaults is not evidence, and saying so here is
    # the difference between deliberation and theatre.
    confidence: float | None = None
    if reading.panel_confidence is not None:
        if reading.panel_evidence is None:
            # Unknown grounding is not zero grounding. It is treated as zero for
            # the arithmetic — an unverifiable panel must not be able to advance
            # anything — but the dissent says "unknown" rather than asserting a
            # 0% that was never measured.
            evidence = 0.0
            dissent.append("panel evidence unknown — treated as none")
        else:
            evidence = reading.panel_evidence
            if evidence < 0.5:
                dissent.append(f"panel ran on {evidence:.0%} real inputs")
        confidence = reading.panel_confidence * evidence

    if reading.coherence is None and reading.panel_confidence is None:
        return GateVerdict(gate.name, REDO, None, reading,
                           "no reading of the organism at all — nothing to decide on",
                           ["self-perception (blind)"])

    # A body of two minds does not get to act, however confident one voice is —
    # and a body that never checked whether it agrees with itself has not earned
    # the benefit of the doubt either. Unmeasured is not the same as calm, which
    # is the same rule PipelineState.urgency follows when it reports None.
    divided = False
    if reading.divergence is None:
        divided = True
        dissent.append("divergence unmeasured — self-agreement was never checked")
    elif reading.divergence >= gate.max_divergence:
        divided = True
        dissent.append(f"divergence {reading.divergence:.2f} >= {gate.max_divergence}")

    if gate.requires_human or is_human_held(context.get("action")):
        return GateVerdict(gate.name, HOLD, confidence, reading,
                           "no automatic executor exists for this step — it is a person's to take",
                           dissent)

    if confidence is None:
        return GateVerdict(gate.name, REDO, None, reading,
                           "the panel could not be convened — gather evidence and return", dissent)

    if divided:
        return GateVerdict(gate.name, REDO, confidence, reading,
                           "the organism does not demonstrably agree with itself — resolve that before acting",
                           dissent)

    if confidence < gate.min_confidence:
        return GateVerdict(gate.name, REDO, confidence, reading,
                           f"confidence {confidence:.2f} below this gate's bar of {gate.min_confidence}",
                           dissent)

    return GateVerdict(gate.name, ADVANCE, confidence, reading,
                       f"{gate.question} yes — confidence {confidence:.2f}", dissent)


def run_chain(
    context: dict[str, Any] | None = None,
    *,
    chain: tuple[Gate, ...] = DEFAULT_CHAIN,
    bus: Any = None,
    on_verdict: Callable[[GateVerdict], None] | None = None,
) -> list[GateVerdict]:
    """Walk the chain, stopping at the first gate that does not advance.

    Returns every verdict reached, so the caller can see exactly where the
    organism stopped and why — that trail is what the Queen reflects on.
    """
    reading = read_organism(bus)
    verdicts: list[GateVerdict] = []
    for gate in chain:
        verdict = evaluate(gate, reading, context=context)
        verdicts.append(verdict)
        if on_verdict:
            try:
                on_verdict(verdict)
            except Exception:  # noqa: BLE001
                LOG.debug("verdict callback failed", exc_info=True)
        _publish(bus, verdict)
        if not verdict.advanced:
            break
    return verdicts


def _publish(bus: Any, verdict: GateVerdict) -> None:
    """Put the verdict on the bus so metacognition can fold it back in."""
    if bus is None:
        return
    try:
        from aureon.core.aureon_thought_bus import Thought

        bus.publish(Thought(source="gate_switchboard", topic=f"gates.{verdict.gate}.verdict",
                            payload=verdict.to_dict()))
    except Exception:  # noqa: BLE001
        LOG.debug("verdict publish skipped", exc_info=True)


__all__ = ["ADVANCE", "REDO", "HOLD", "HUMAN_HELD", "Gate", "GateReading", "GateVerdict",
           "DEFAULT_CHAIN", "evaluate", "is_human_held", "read_organism", "run_chain"]
