"""The drafting organ — she writes, gated, and checks her own claims afterwards.

Gary's handoff prompt ends in four asks, and the first is *"draft/sharpen an
application narrative"*. Everything above that line in his prompt is something
this repository can read for itself, and :mod:`aureon.briefing.assemble` now does:
the company record, the decision spine, the positioning line, the live deadlines,
the compliance blocker, the standing rule. This module is the last step — take
that assembled brief and produce prose from it — and it is the step where the
organism can most easily lie, so it is the one wrapped in the most refusals.

Three of them, in order:

**The chain runs before the pen moves.** :func:`draft` asks
:func:`aureon.gates.switchboard.run_chain` about ``draft_narrative`` *before*
generating anything. If the chain says REDO the function returns the verdicts and
no text. She does not write while the organism says the evidence is not there —
that would make the gate decorative.

**An absent model is a blocker, never a paragraph.**
:func:`aureon.inhouse_ai.llm_adapter.build_voice_adapter` does not fail loudly
when there is no backend; it returns an ``AureonStubAdapter`` whose
``health_check()`` is ``True`` and whose ``prompt()`` returns a configuration
message shaped exactly like a completion. Handed straight through, that message
would appear in a DraftResult as Gary's narrative. :func:`draft` recognises it —
by adapter class name, by the response's model name, by the ``[ERROR]``/
``[AUREON]`` prefixes and by ``stop_reason == "error"`` — and returns ``text=None``
with a blocker. There is no code path here that presents a stub as a draft.

**The output is checked against Gary's own rule.**
:func:`aureon.briefing.claims.check_claims` runs over every generated draft and
the report is attached whether it is clean or not. The rule it enforces is read at
runtime from the reconciliation report, verbatim, and is written nowhere in this
package. A ``blending`` finding — one sentence welding a verified software
capability to a research or speculative claim — sets ``needs_revision=True`` with
the reason stated. Handing Gary a draft that breaks his own claim rule is worse
than handing him nothing.

Be blunt about the model, because he asked for blunt
----------------------------------------------------
The live language cortex here is a **small local model** — llama3-class, served
over ``AUREON_LLM_BASE_URL``. It is genuinely useful for structure, for tightening
a paragraph, for a first pass on a section whose facts are already fixed. It is
**not adequate for a competitive Innovate UK narrative**, and this module does not
pretend otherwise: the caveat travels in :attr:`DraftResult.model_caveat` on every
result, not only in this docstring.

So the intended workflow for anything high-stakes is deliberately a two-machine
workflow:

1. :func:`aureon.briefing.assemble.assemble_brief` builds the brief locally.
   **This is the hard part** — every line carries the file or the organ it came
   from, the standing rule and the positioning line are quoted verbatim, the
   deadlines come from the live ledger, the compliance position comes from the
   auditor where unknown means unknown, and nothing that could not be read is
   filled in. No model is involved and none is needed.
2. :func:`export_for_stronger_model` renders that brief as a complete prompt for a
   model strong enough for the job.
3. Bring the narrative back and run
   :func:`aureon.briefing.claims.check_claims` over it. The claim check is
   model-agnostic on purpose: it audits text, not the thing that produced it.

Local drafting is step 1 followed by a weak step 2. Calling that equivalent to the
real thing would be the first fabrication in a module built to prevent them.

Nothing here submits or sends. The standing rule — read, not recited — reserves
external submission, legal representation, filing, payment and email send for
Gary, and this module has no path to any of them: it returns a string.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aureon.briefing.assemble import assemble_brief
from aureon.briefing.claims import (
    BLOCKING,
    CRITICAL,
    RULE_BLENDING,
    ClaimReport,
    check_claims,
)
from aureon.briefing.render import render_prompt
from aureon.briefing.schemas import Brief
from aureon.gates.switchboard import Gate, GateVerdict, is_human_held, run_chain

LOG = logging.getLogger("aureon.briefing.author")

# The action this organ asks the switchboard about. Not human-held —
# ``is_human_held("draft_narrative")`` is False, and it must stay False, because
# drafting is not sending. ``_gate_context`` asserts it on every call.
DRAFT_ACTION = "draft_narrative"

# The chain a draft passes through. ``submit`` is deliberately absent:
# ``DEFAULT_CHAIN`` ends in a human-held gate, so routing a draft through it would
# return HOLD for every ask and the organism would never write a word — a refusal
# that protects nothing, because drafting has an executor and this function is it.
# Sending the result is a different action with a different gate, and it is held
# in :mod:`aureon.approval` rather than fudged here.
DRAFT_CHAIN: tuple[Gate, ...] = (
    Gate("act", "Should I spend the organism's effort drafting this?", min_confidence=0.45),
    Gate("ground", "Is there a real, sourced brief behind it — or would I be inventing?",
         min_confidence=0.55),
)

# Severities that mean "do not hand this to Gary as it stands".
#
# ``blocking`` is the owner's own rule: it is carried by exactly one check,
# ``blending``, which is the blur his claim-discipline row prohibits by name.
# ``critical`` is ``contradicted_by_own_record`` — a sentence asserting compliance
# clearance while the company's own documents carry an open blocker. Both are
# hand-back conditions for the same reason: an assessor reads the public register
# before the narrative. Everything below them is reported and left to a human,
# because "this absolute is strong" is a judgement, not a violation.
REVISION_SEVERITIES: tuple[str, ...] = (BLOCKING, CRITICAL)


# ── the model, and the truth about it ────────────────────────────────────────

# What the environment currently points the voice layer at. Read, not asserted:
# if the operator repoints AUREON_LLM_MODEL the caveat follows it. The judgement
# attached to it does not depend on which small model it happens to be.
_DEFAULT_MODEL_NOTE = "llama3-class local model served over AUREON_LLM_BASE_URL"

MODEL_CAVEAT = (
    "The live language cortex is a small local model ({model}). It is useful for structure and "
    "for tightening prose whose facts are already fixed. It is NOT adequate for a competitive "
    "Innovate UK narrative. For anything high-stakes use export_for_stronger_model(): the brief "
    "is the hard, grounded part and it was assembled locally — take it to a stronger model, then "
    "run check_claims() over what comes back."
)

# Generation parameters. Low temperature because this is evidence-bound prose, not
# invention: the failure mode being guarded against is a model filling a gap in
# the brief with something plausible.
MAX_TOKENS = 2048
TEMPERATURE = 0.2

# The instruction the model is held to. It carries no company fact — every fact
# reaches the model through the rendered brief, and the two binding rules reach it
# quoted verbatim by :func:`aureon.briefing.render.render_prompt`.
SYSTEM_PROMPT = (
    "You are drafting on behalf of the director of a small company. The CONTEXT below was "
    "assembled by that company's own systems from its own documents and organs; every line "
    "names where it came from.\n"
    "Use only what is in the context. Where a fact you need is not there, write \"not in the "
    "brief\" and name what is missing — never supply it from general knowledge.\n"
    "The STANDING RULE and CLAIM DISCIPLINE quoted in the context are binding and are not "
    "yours to relax. Keep verified software capability, public research claims and speculative "
    "hypotheses in separate sentences; never weld a tested capability to a hypothesis.\n"
    "Name every blocker the context lists. A narrative that omits a live blocker is not a "
    "kindness, it is a surprise at the submit button.\n"
    "Nothing in this task is a request to submit, file, pay or send. It is a request for text."
)

_HELD_ASK_NOTE = (
    "\nNOTE: the ask names an action with no automatic executor in this system (submission, "
    "filing, payment, transfer or send). Producing text about it does not perform it, and the "
    "text must not be written as though it had been done."
)


def _model_caveat() -> str:
    configured = (os.getenv("AUREON_LLM_MODEL") or "").strip()
    return MODEL_CAVEAT.format(model=configured or _DEFAULT_MODEL_NOTE)


# An adapter whose class name says stub is a stub. ``build_voice_adapter`` returns
# ``AureonStubAdapter`` when no backend is reachable, and that adapter's
# ``health_check()`` returns True while its ``prompt()`` returns a configuration
# message shaped like a completion — so a health check alone protects nothing.
# Matched on the class name rather than by importing the class, so this module
# does not pull an 82 KB adapter file in to run a guard.
_STUB_CLASS_MARKERS = ("stub",)
# Model names ``build_voice_adapter`` uses to say "there is no model".
_UNAVAILABLE_MODEL_MARKERS = ("stub", "unavailable", "no-backend", "unconfigured")
# Prefixes the adapters use for an error carried in the text field.
_ERROR_PREFIXES = ("[ERROR]", "[AUREON]")


def adapter_blocker(adapter: Any) -> str | None:
    """Why this adapter cannot be used for a draft, or ``None`` if it can be tried.

    Checked before the call, so a known-absent model costs nothing and — more to
    the point — so a stub is never given the chance to answer.
    """
    if adapter is None:
        return "no LLM adapter — build_voice_adapter() returned nothing"
    name = type(adapter).__name__
    if any(m in name.lower() for m in _STUB_CLASS_MARKERS):
        return (f"no local model is reachable — build_voice_adapter() returned {name}, whose "
                "prompt() returns configuration text, not a draft. Start the local model, or "
                "use export_for_stronger_model() and take the brief to a stronger model.")
    if not hasattr(adapter, "prompt"):
        return f"adapter {name} has no prompt() method"
    try:
        healthy = adapter.health_check()
    except Exception as exc:  # noqa: BLE001
        return f"adapter {name} health check raised {type(exc).__name__}"
    if healthy is False:
        return f"adapter {name} reports its backend unreachable"
    return None


def response_blocker(text: str, model: str, stop_reason: str) -> str | None:
    """Why this response is not a draft, or ``None`` if it is one.

    Four independent signals, because any one of them can be the only one
    present: an adapter can be honestly named and still return an error string,
    and a stub can be renamed and still name itself in the response.
    """
    if stop_reason == "error":
        return (f"the model returned an error (stop_reason=error, model={model or 'unknown'}): "
                f"{text[:200] or 'no detail'}")
    if any(m in (model or "").lower() for m in _UNAVAILABLE_MODEL_MARKERS):
        return (f"the response came from {model!r}, which is a placeholder rather than a model — "
                "its text is configuration guidance, not a draft")
    stripped = (text or "").strip()
    if not stripped:
        return f"the model ({model or 'unknown'}) returned no text"
    if stripped.startswith(_ERROR_PREFIXES):
        return f"the model ({model or 'unknown'}) returned an error string: {stripped[:200]}"
    return None


# ── the result ───────────────────────────────────────────────────────────────


@dataclass
class DraftResult:
    """What came back from an attempt to draft — including when nothing did.

    ``text`` is ``None`` in exactly three situations, and each one carries a stated
    reason rather than a substitute paragraph: the chain did not advance, no usable
    model was reachable, or the model returned something that is not a draft.
    There is no fourth branch that fills the gap in.

    ``needs_revision`` is set whenever the claim check found something at a
    severity in :data:`REVISION_SEVERITIES` — a ``blending`` sentence above all —
    and ``revision_reasons`` says which. A draft that violates the author's own
    claim rule is returned *with the objection attached*, never quietly and never
    withheld: he asked to hear it from the organism rather than from an assessor,
    and that requires showing him both the prose and the problem.
    """

    text: str | None = None
    model: str | None = None
    brief_sources: tuple[str, ...] = ()
    claim_report: ClaimReport | None = None
    gate_verdicts: tuple[GateVerdict, ...] = ()
    blocker: str | None = None
    needs_revision: bool = False
    revision_reasons: tuple[str, ...] = ()
    model_caveat: str = ""
    ask: str = ""
    brief_blockers: tuple[str, ...] = ()
    generated_at: datetime | None = None

    @property
    def drafted(self) -> bool:
        """True only when real model text came back."""
        return bool(self.text)

    @property
    def decision(self) -> str | None:
        """The last gate's decision, or ``None`` when the chain never ran."""
        return self.gate_verdicts[-1].decision if self.gate_verdicts else None

    @property
    def advanced(self) -> bool:
        """True when every gate in the chain advanced."""
        return bool(self.gate_verdicts) and all(v.advanced for v in self.gate_verdicts)

    def narrate(self) -> str:
        """The attempt in plain text: what happened, and every objection to it."""
        lines = [f"DRAFT: {'produced' if self.drafted else 'NOT produced'}"
                 f"  (chain {self.decision or 'not run'})"]
        if self.blocker:
            lines.append(f"  blocker: {self.blocker}")
        if self.needs_revision:
            lines.append("  NEEDS REVISION — this draft breaks the author's own claim rule:")
            lines.extend(f"    - {r}" for r in self.revision_reasons)
        for verdict in self.gate_verdicts:
            lines.append(f"  gate {verdict.gate}: {verdict.decision} — {verdict.reasoning}")
        if self.model_caveat:
            lines.append(f"  model: {self.model or 'none'} — {self.model_caveat}")
        if self.brief_blockers:
            lines.append("  the brief could not read:")
            lines.extend(f"    - {b}" for b in self.brief_blockers)
        if self.claim_report is not None:
            report = self.claim_report
            lines.append(f"  claim check: {len(report.findings)} finding(s) over "
                         f"{report.sentences_checked} sentence(s); "
                         f"{report.blended_count} blended; "
                         f"highest severity {report.highest_severity or 'none'}")
            for finding in report.findings:
                lines.append(f"    {finding.severity.upper():<9} {finding.rule}: "
                             f"{finding.sentence}")
            if report.blocker:
                lines.append(f"    claim-check blocker: {report.blocker}")
        if self.text:
            lines.append("")
            lines.append(self.text)
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "drafted": self.drafted,
            "text": self.text,
            "model": self.model,
            "brief_sources": list(self.brief_sources),
            "claim_report": self.claim_report.to_dict() if self.claim_report else None,
            "gate_verdicts": [v.to_dict() for v in self.gate_verdicts],
            "decision": self.decision,
            "blocker": self.blocker,
            "needs_revision": self.needs_revision,
            "revision_reasons": list(self.revision_reasons),
            "model_caveat": self.model_caveat,
            "ask": self.ask,
            "brief_blockers": list(self.brief_blockers),
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
        }


# ── the export, which is the honest route for high-stakes work ──────────────


def export_for_stronger_model(brief: Brief, ask: str | Any = None) -> str:
    """Render the brief as a complete prompt for a model strong enough for the job.

    This exists because the local model is not, and it is the *intended* route for
    a competitive narrative rather than a fallback from a broken one. The hard part
    has already happened locally: :func:`aureon.briefing.assemble.assemble_brief`
    read the company's own documents and organs, every line names its source, the
    standing rule and the claim-discipline rule are quoted verbatim, and everything
    that could not be read is listed as NOT READ instead of being filled in. That
    is the part no model can do for you.

    Rendering is :func:`aureon.briefing.render.render_prompt` — called, not
    reimplemented, so the exported prompt and the brief's own markdown cannot
    drift apart in what they claim the documents say. The returned string carries
    the standing rule verbatim when it could be read, and an explicit refusal to
    proceed without approval when it could not; it never carries a paraphrase.

    Run :func:`aureon.briefing.claims.check_claims` over whatever comes back. The
    check does not care which model wrote the prose, which is exactly why it is
    still worth running on the output of a better one.
    """
    return render_prompt(brief, ask)


# ── the draft ────────────────────────────────────────────────────────────────


def _gate_context(ask: str, brief: Brief) -> dict[str, Any]:
    """The context the chain decides on.

    ``action`` is fixed to :data:`DRAFT_ACTION` and asserted non-held: drafting
    has an executor — :func:`draft` — and must not be routed into the switchboard
    as though it were a filing. The ask travels under a *different key* precisely
    so that an ask which merely mentions submission cannot silently convert a
    drafting request into a HOLD and hide the fact that no draft was attempted.
    """
    assert not is_human_held(DRAFT_ACTION), "drafting must not be classified human-held"
    return {
        "action": DRAFT_ACTION,
        "requested": str(ask or "").strip(),
        "brief_available": brief.available,
        "brief_sections": list(brief.present),
        "brief_omitted": list(brief.omitted),
        "brief_blockers": list(brief.blockers),
        "standing_rule_read": brief.standing_rule is not None,
        "claim_rule_read": brief.claim_discipline is not None,
        "overdue_count": len(brief.overdue),
    }


def _capability(root: Path | str | None) -> Any:
    """The capability profile, so the claim check can catch self-contradiction.

    :func:`aureon.briefing.claims.check_claims` needs the verbatim
    ``compliance_blockers`` to run ``contradicted_by_own_record`` — the rule that
    catches a draft asserting clearance while the company's own record carries an
    open blocker. Without it that rule cannot fire, and the report says so rather
    than reading clean. Absence here is therefore reported, never papered over.
    """
    try:
        from aureon.grants.scout import read_capability

        return read_capability(root)
    except Exception:  # noqa: BLE001
        LOG.debug("capability read failed", exc_info=True)
        return None


def draft(ask: str, *, brief: Brief | None = None, root: Path | str | None = None,
          bus: Any = None, adapter: Any = None, now: datetime | None = None) -> DraftResult:
    """Draft a narrative for ``ask``, gated, with the claim check applied to the output.

    The order is the whole design:

    1. Assemble the brief, or take the one supplied. This is the grounded part and
       it happens whether or not a model is available.
    2. Run :func:`aureon.gates.switchboard.run_chain` over :data:`DRAFT_CHAIN` with
       ``action="draft_narrative"``. **If any gate does not ADVANCE, return here**
       — verdicts attached, ``text=None``, adapter never called. She does not write
       while the organism says REDO.
    3. Get a model. An unreachable backend, a stub adapter, an error response or an
       empty one all produce a blocker. None of them produce a paragraph.
    4. Run :func:`aureon.briefing.claims.check_claims` over what came back and
       attach the report. Anything at a severity in :data:`REVISION_SEVERITIES`
       sets ``needs_revision`` and records why.

    Be blunt about step 3, because the docstring is part of the honesty: the live
    model is a small local one and it is **not adequate for a competitive Innovate
    UK narrative**. :attr:`DraftResult.model_caveat` says so on every result, and
    :func:`export_for_stronger_model` is the route that does not pretend otherwise.

    ``adapter`` is injectable so tests never touch a model. ``root`` is honoured
    verbatim by every reader underneath. Never raises.
    """
    now = now or datetime.now(UTC)
    if brief is None:
        brief = assemble_brief(root, bus, now=now)

    result = DraftResult(
        brief_sources=brief.sources, model_caveat=_model_caveat(),
        ask=str(ask or "").strip(), brief_blockers=brief.blockers, generated_at=now,
    )

    # ── 1. the gate, before the pen ──────────────────────────────────────────
    try:
        verdicts = run_chain(_gate_context(ask, brief), chain=DRAFT_CHAIN, bus=bus)
    except Exception as exc:  # noqa: BLE001
        LOG.debug("gate chain failed", exc_info=True)
        result.blocker = f"the gate chain could not be run ({type(exc).__name__}) — no draft"
        return result

    result.gate_verdicts = tuple(verdicts)
    if not verdicts or not all(v.advanced for v in verdicts):
        stopped = next((v for v in verdicts if not v.advanced), None)
        result.blocker = (
            f"the chain did not advance — gate {stopped.gate!r} returned {stopped.decision}: "
            f"{stopped.reasoning}" if stopped else
            "the chain produced no verdict at all — nothing authorised this draft"
        )
        return result

    # ── 2. the model, or an honest absence ───────────────────────────────────
    if adapter is None:
        try:
            from aureon.inhouse_ai.llm_adapter import build_voice_adapter

            adapter = build_voice_adapter()
        except Exception as exc:  # noqa: BLE001
            LOG.debug("adapter build failed", exc_info=True)
            result.blocker = (f"no LLM adapter could be built ({type(exc).__name__}) — "
                              "use export_for_stronger_model() instead")
            return result

    blocker = adapter_blocker(adapter)
    if blocker:
        result.blocker = blocker
        return result

    system = SYSTEM_PROMPT + (_HELD_ASK_NOTE if is_human_held(ask) else "")
    try:
        response = adapter.prompt(
            [{"role": "user", "content": render_prompt(brief, ask)}], system=system,
            max_tokens=MAX_TOKENS, temperature=TEMPERATURE,
        )
    except Exception as exc:  # noqa: BLE001
        LOG.debug("model call failed", exc_info=True)
        result.blocker = (f"the model call raised {type(exc).__name__} — no draft. The brief is "
                          "still assembled; export_for_stronger_model() will render it for a "
                          "model that is up.")
        return result

    text = str(getattr(response, "text", "") or "")
    model = str(getattr(response, "model", "") or "")
    stop_reason = str(getattr(response, "stop_reason", "") or "")
    result.model = model or None

    blocker = response_blocker(text, model, stop_reason)
    if blocker:
        result.blocker = blocker
        return result

    # ── 3. the claim check, over the OUTPUT ──────────────────────────────────
    report = check_claims(text, capability=_capability(root))
    result.claim_report = report
    result.text = text.strip()

    reasons = tuple(
        f"{f.rule} ({f.severity}): {f.issue} — \"{f.sentence}\""
        for f in report.findings if f.severity in REVISION_SEVERITIES
    )
    if reasons:
        result.needs_revision = True
        result.revision_reasons = reasons
    return result


__all__ = [
    "DRAFT_ACTION",
    "DRAFT_CHAIN",
    "MAX_TOKENS",
    "MODEL_CAVEAT",
    "REVISION_SEVERITIES",
    "RULE_BLENDING",
    "SYSTEM_PROMPT",
    "TEMPERATURE",
    "DraftResult",
    "adapter_blocker",
    "assemble_brief",
    "check_claims",
    "draft",
    "export_for_stronger_model",
    "response_blocker",
]
