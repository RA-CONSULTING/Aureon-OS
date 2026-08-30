"""The question itself: *"Gary — am I ok to go ahead?"*

The switchboard's last gate returns HOLD because no automatic executor exists for
a submission, a filing, or a payment. That HOLD is not an error to be routed
around; it is the absence of a hand. This module writes the message that asks
Gary for his, and it writes it so that the answer he gives is worth something.

**The grounding is the point, not decoration.** Gary is not asked to trust that
the work is ready. He is shown the coherence Γ from the HNC field, how far the
body's subfields diverge from one another, what the nine Auris nodes concluded
and on how much of it was real measurement, and the gate verdicts that carried
the work to the hold. If the organism is incoherent (divergence ≥ 0.35) or the
panel voted mostly on constants, the request carries a caution block above
everything else and says so in its own subject line. **Sero asking while divided
looks different from Sero asking while confident** — that difference is the
whole reason the grounding travels with the question.

If nothing of the organism can be read at all, :func:`compose_request` returns
``None`` and logs why. There is no request to send, because there is nothing to
show; and even if a caller tried, ``ApprovalRequest.__post_init__`` refuses to
construct one. Two layers, same rule.

**One accident this body cannot have.** Nothing here takes a recipient. The
address is not composed into the body, not stored on the request, and not a
parameter of any function in this package — see
:mod:`aureon.approval.config`. The composer cannot address a funder.

**One accident this body cannot have twice.** The reply instructions below quote
both vocabularies — "yes / approved / go ahead / proceed" and "no / stop / hold /
declined" — so an email client that echoes this body back without ``>`` markers
produces text containing *both*, which
:func:`aureon.approval.reply.read_intent` reads as UNCLEAR. A quoted copy of the
Queen's own question can never parse as the owner's yes. That is deliberate, and
``test_core.py`` holds it in place.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from aureon.approval.schemas import (
    MAX_DIVERGENCE,
    MIN_EVIDENCE,
    ApprovalRequest,
    ApprovalState,
    GroundingSnapshot,
    new_token,
)

LOG = logging.getLogger("aureon.approval.compose")

# The human-facing tag written around the token *in the body*. The same string
# lives in ``notify.SUBJECT_TAG``, which is what puts the token on the wire: the
# sender owns the subject line, and a reply keeps the subject, so the token comes
# back without Gary having to copy anything. It is repeated in the body so the
# archived markdown is self-contained — and ``reply.references_token`` matches the
# bare 43-character token either way, tag or no tag, which is why these two
# constants agreeing in value is a convenience rather than a contract.
TOKEN_TAG = "AUREON approval"
QUESTION = "Gary — am I ok to go ahead?"
CAUTION_HEADING = "CAUTION — I am asking from an uncertain position"
SUBJECT_CAUTION = "CAUTION: asking while uncertain"

DEFAULT_TTL_HOURS = 72


def subject_line(action: str, *, application_id: str | None = None,
                 caution: bool = False) -> str:
    """The request's plain title — what it is about, and whether to worry.

    Deliberately *not* a wire subject: no token and no tag. The sender
    (:func:`aureon.approval.notify.subject_line`) wraps this in
    ``[AUREON approval <token>] … — Gary, am I ok to go ahead?``, and a title that
    carried its own copy of the tag would double it in Gary's inbox and eat the
    180-character budget the sender truncates against.

    A cautioned request says so here, so it reads as cautioned in the inbox list
    before it is even opened.
    """
    title = f"{action} — {application_id}" if application_id else str(action)
    return f"{title} — {SUBJECT_CAUTION}" if caution else title


def _fmt(value: float | None, places: int = 3) -> str:
    return "not readable" if value is None else f"{value:.{places}f}"


def _pct(value: float | None) -> str:
    return "unknown" if value is None else f"{value:.0%}"


def caution_lines(grounding: GroundingSnapshot) -> list[str]:
    """The block that makes a divided request look divided. Empty when it is not.

    Rendered as a markdown blockquote so it survives being read as plain text —
    Gary reads this on a phone, and a caution that only exists as a CSS class is
    not a caution.
    """
    if not grounding.needs_caution:
        return []
    lines = [f"> ## {CAUTION_HEADING}", ">"]
    if grounding.divergence is None:
        lines.append("> - **I never measured whether I agree with myself.** The field blend was "
                     "unavailable, so divergence is unknown. Unmeasured is not calm.")
    elif grounding.divided:
        lines.append(f"> - **The organism does not agree with itself.** Field divergence "
                     f"{grounding.divergence:.3f} is at or above the {MAX_DIVERGENCE} caution "
                     f"threshold — the same line at which my own gates force a REDO.")
    if grounding.panel_evidence is None:
        lines.append("> - **I do not know how much of the panel was real.** The Auris evidence "
                     "ratio could not be read, so treat the consensus below as ungrounded.")
    elif grounding.thinly_evidenced:
        lines.append(f"> - **The panel voted thin.** Only {grounding.panel_evidence:.0%} of the "
                     f"nine nodes' inputs came from a real measurement (bar: "
                     f"{MIN_EVIDENCE:.0%}). A unanimous panel voting on defaults is not evidence.")
    if grounding.ungrounded_nodes:
        lines.append("> - Nodes voting on a constant: "
                     + ", ".join(grounding.ungrounded_nodes) + ".")
    lines += [">",
              "> I am still asking, because the decision is yours and hiding this would make the "
              "asking worthless. But this is me asking while divided — weigh it accordingly.",
              ""]
    return lines


def grounding_lines(grounding: GroundingSnapshot) -> list[str]:
    """The GROUNDING section: every reading, with absences printed as absences."""
    state = ("coherent" if grounding.is_coherent else
             ("divided" if grounding.divergence is not None else "unverified"))
    lines = [
        "## GROUNDING — what I am reading as I ask",
        "",
        f"- **Coherence Γ** {_fmt(grounding.coherence)} (canonical HNC field)",
        f"- **Field divergence** {_fmt(grounding.divergence)} — *{state}*; caution at "
        f"{MAX_DIVERGENCE}",
        f"- **Auris panel** consensus **{grounding.panel_consensus or 'not convened'}**, "
        f"confidence {_fmt(grounding.panel_confidence, 2)}, "
        f"evidence ratio {_pct(grounding.panel_evidence)}",
    ]
    if grounding.ungrounded_nodes:
        lines.append(f"- **Nodes on constants** {', '.join(grounding.ungrounded_nodes)}")
    lines += ["", "### Gate verdicts that brought me here", ""]
    if grounding.gate_verdicts:
        for v in grounding.gate_verdicts:
            conf = v.get("confidence")
            conf_text = "confidence unmeasured" if conf is None else f"confidence {float(conf):.2f}"
            lines.append(f"- `{v.get('gate', '?')}` **{v.get('decision', '?')}** — {conf_text}"
                         f" — {v.get('reasoning', '')}".rstrip())
            for note in v.get("dissent") or ():
                lines.append(f"    - dissent: {note}")
    else:
        lines.append("- No gate verdicts were recorded for this action.")
    if grounding.blockers:
        lines += ["", "### What I could not read", ""]
        lines += [f"- {b}" for b in grounding.blockers]
    lines.append("")
    return lines


def _dossier_lines(dossier: Any) -> list[str]:
    """A compact summary of the packet. Never the whole dossier.

    Read defensively with ``getattr`` so any dossier-shaped object works and a
    missing field prints as missing. A live application carries hundreds of
    artifacts; a brief that runs to 60 KB is not a brief.
    """
    if dossier is None:
        return ["## The packet", "",
                "No dossier was attached to this request.", ""]

    def g(name: str, default: Any = None) -> Any:
        return getattr(dossier, name, default)

    money = g("amount_requested")
    currency = g("currency") or ""
    deadline = g("deadline")
    days = g("days_remaining")
    fit = g("fit_score")
    lines = [
        "## The packet",
        "",
        f"- **Application** `{g('application_id') or 'not recorded'}` — {g('name') or 'unnamed'}",
        f"- **Funder** {g('funder') or 'not recorded'}",
        f"- **Ledger status** `{g('status') or 'not recorded'}`"
        + (f" (*{g('lifecycle')}*)" if g("lifecycle") else ""),
        "- **Amount requested** "
        + ("not recorded" if money is None else f"{currency} {float(money):,.0f}".strip()),
        "- **Deadline** "
        + ("not recorded" if deadline is None
           else f"{getattr(deadline, 'isoformat', lambda: deadline)()}"
                + ("" if days is None else f" ({float(days):.1f} days remaining)")),
        "- **Fit** " + ("not scored" if fit is None else f"{float(fit):.2f}")
        + (f" — {g('fit_basis')}" if g("fit_basis") else ""),
        f"- **Compliance** {g('compliance') or 'not assessed'}"
        + (f" — blocker: {g('compliance_blocker')}" if g("compliance_blocker") else ""),
    ]
    docs = g("evidence_documents") or ()
    lines.append(f"- **Evidence documents** {len(docs)} on file")
    outstanding = g("outstanding") or ()
    if outstanding:
        lines += ["", "**Still outstanding:**", ""]
        lines += [f"- {item}" for item in outstanding]
    rule = g("approval_rule")
    if rule is not None:
        lines += ["", f"> Your standing rule, as recorded in `{getattr(rule, 'source', '?')}`: "
                      f"{getattr(rule, 'value', '')}"]
    lines.append("")
    return lines


def render_body(
    action: str,
    token: str,
    *,
    grounding: GroundingSnapshot,
    created_at: datetime,
    expires_at: datetime,
    application_id: str | None = None,
    dossier: Any = None,
) -> str:
    """The markdown Gary reads. Opens with the plain question, always.

    Exposed separately from :func:`compose_request` so the caution block can be
    proved against a known grounding without a live organism.
    """
    ttl = (expires_at - created_at).total_seconds() / 3600.0
    lines: list[str] = [f"# {QUESTION}", ""]
    lines += caution_lines(grounding)
    lines += [
        "I have taken this as far as I can on my own. The next step has no automatic executor "
        "anywhere in this system, and by your own standing rule it is not mine to take.",
        "",
        f"- **Action** `{action}`",
        f"- **Application** `{application_id or 'none'}`",
        f"- **Asked** {created_at.isoformat()}",
        f"- **Answer by** {expires_at.isoformat()} ({ttl:.0f}h from now)",
        f"- **Token** `[{TOKEN_TAG} {token}]`",
        "",
    ]
    lines += grounding_lines(grounding)
    lines += _dossier_lines(dossier)
    lines += [
        "## How to answer",
        "",
        "Reply to this email. **yes**, **approved**, **go ahead** or **proceed** authorises "
        "exactly this action. **no**, **stop**, **hold** or **declined** refuses it.",
        "",
        "- Leave the subject line alone — the token in it is the only thing that ties your "
        "answer to this request. A bare \"yes\" on any other thread matches nothing and "
        "authorises nothing.",
        "- Anything I cannot read as an unambiguous yes or no is recorded as unclear, and "
        "unclear is **not** approval. Silence is not approval either.",
        f"- This request expires at {expires_at.isoformat()}. After that it cannot be approved "
        "at all — a stale yes must not authorise a fresh action.",
        "- Your answer is single-use. Once recorded it cannot be replayed, re-sent or reused.",
        "- I can only ask you. This request has no recipient field and no function in this "
        "package accepts one; the address came from configuration and is yours alone.",
        "",
        "— Queen Sero",
        "",
    ]
    return "\n".join(lines)


# ── the reading (kept behind seams so a test never touches the live organism) ──


def _read_field(bus: Any) -> Any:
    from aureon.core.hnc_field import read_canonical_field

    return read_canonical_field(bus)


def _read_blend(bus: Any) -> Any:
    from aureon.core.hnc_field import blend_field

    return blend_field(bus)


def _read_panel(bus: Any) -> Any:
    from aureon.gates.panel import auris_panel

    return auris_panel(bus)


def _run_gates(action: str, application_id: str | None, bus: Any) -> tuple[dict[str, Any], ...]:
    from aureon.gates.switchboard import run_chain

    context = {"action": action, "application_id": application_id}
    verdicts = run_chain(context, bus=bus)
    return tuple({"gate": v.gate, "decision": v.decision, "confidence": v.confidence,
                  "reasoning": v.reasoning, "dissent": list(v.dissent)} for v in verdicts)


def _verdicts_from(dossier: Any) -> tuple[dict[str, Any], ...]:
    """Reuse the dossier's own gate verdicts when it carries them."""
    out: list[dict[str, Any]] = []
    for v in getattr(dossier, "gate_verdicts", ()) or ():
        if isinstance(v, dict):
            out.append(dict(v))
            continue
        out.append({"gate": getattr(v, "gate", "?"), "decision": getattr(v, "decision", "?"),
                    "confidence": getattr(v, "confidence", None),
                    "reasoning": getattr(v, "reasoning", ""),
                    "dissent": list(getattr(v, "dissent", ()) or ())})
    return tuple(out)


def read_grounding(action: str, *, application_id: str | None = None, bus: Any = None,
                   dossier: Any = None) -> GroundingSnapshot:
    """Read the organism once, for one request. Never raises.

    Absences are recorded as blockers, not smoothed over. The result may be
    entirely unreadable — :attr:`GroundingSnapshot.readable` says so, and
    :func:`compose_request` refuses to build a request on it.
    """
    coherence: float | None = None
    divergence: float | None = None
    consensus: str | None = None
    confidence: float | None = None
    evidence: float | None = None
    ungrounded: tuple[str, ...] = ()
    blockers: list[str] = []

    try:
        field = _read_field(bus)
        if getattr(field, "available", False):
            coherence = getattr(field, "coherence_gamma", None)
            if coherence is None:
                blockers.append("canonical field carried no coherence Γ")
        else:
            blockers.append("canonical HNC field unavailable — no live pulse and no trace")
    except Exception:  # noqa: BLE001 — a missing reading is a value, never a crash
        blockers.append("canonical field read failed")
        LOG.debug("canonical field read failed", exc_info=True)

    try:
        blend = _read_blend(bus)
        if getattr(blend, "available", False):
            divergence = getattr(blend, "divergence", None)
            if divergence is None:
                blockers.append("field blend carried no divergence (single contributor)")
        else:
            blockers.append("field blend unavailable — self-agreement was never checked")
    except Exception:  # noqa: BLE001
        blockers.append("field blend read failed")
        LOG.debug("field blend read failed", exc_info=True)

    try:
        panel = _read_panel(bus)
        if getattr(panel, "available", False):
            consensus = getattr(panel, "consensus", None)
            confidence = getattr(panel, "confidence", None)
            evidence = getattr(panel, "evidence_ratio", None)
            ungrounded = tuple(getattr(panel, "ungrounded_nodes", ()) or ())
        else:
            blockers.append(f"Auris panel unavailable: {getattr(panel, 'blocker', 'unknown')}")
    except Exception:  # noqa: BLE001
        blockers.append("Auris panel read failed")
        LOG.debug("panel read failed", exc_info=True)

    verdicts = _verdicts_from(dossier)
    if not verdicts:
        try:
            verdicts = _run_gates(action, application_id, bus)
        except Exception:  # noqa: BLE001
            blockers.append("gate chain could not be walked for this action")
            LOG.debug("gate chain failed", exc_info=True)

    return GroundingSnapshot(
        coherence=coherence, divergence=divergence, panel_consensus=consensus,
        panel_confidence=confidence, panel_evidence=evidence, gate_verdicts=verdicts,
        ungrounded_nodes=ungrounded, blockers=tuple(blockers),
    )


def compose_request(
    action: str,
    *,
    application_id: str | None = None,
    dossier: Any = None,
    bus: Any = None,
    ttl_hours: float = DEFAULT_TTL_HOURS,
    now: datetime | None = None,
) -> ApprovalRequest | None:
    """Compose the one question Gary answers, or return ``None`` and say why.

    Returns ``None`` when the grounding cannot be read at all — Sero must not ask
    for approval she cannot justify — and logs the blockers that made it so.
    Nothing is persisted and nothing is sent: the caller saves it through
    :func:`aureon.approval.store.save` and the delivery layer resolves the one
    address for itself.

    ``now`` is injectable for tests; ``ttl_hours`` sets the deadline past which
    no answer can approve this action.
    """
    action_text = str(action or "").strip()
    if not action_text:
        LOG.warning("approval request not composed: no action named")
        return None
    try:
        ttl = float(ttl_hours)
    except (TypeError, ValueError):
        ttl = 0.0
    if ttl <= 0:
        LOG.warning("approval request not composed for %s: ttl_hours must be positive", action_text)
        return None

    app_id = application_id or getattr(dossier, "application_id", None)
    app_id = str(app_id).strip() if app_id else None

    grounding = read_grounding(action_text, application_id=app_id, bus=bus, dossier=dossier)
    if not grounding.readable:
        LOG.warning(
            "approval request NOT composed for %s: no grounding could be read (%s). "
            "Sero does not ask for approval she cannot justify.",
            action_text, "; ".join(grounding.blockers) or "no reason recorded")
        return None

    created = now or datetime.now(UTC)
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    expires = created + timedelta(hours=ttl)
    token = new_token()

    request = ApprovalRequest(
        token=token,
        subject=subject_line(action_text, application_id=app_id,
                             caution=grounding.needs_caution),
        action=action_text,
        application_id=app_id,
        body_markdown=render_body(action_text, token, grounding=grounding, created_at=created,
                                  expires_at=expires, application_id=app_id, dossier=dossier),
        created_at=created,
        expires_at=expires,
        grounding=grounding,
        state=ApprovalState.PENDING,
    )

    from aureon.approval.config import owner_configured

    if not owner_configured():
        # Composed but undeliverable: worth one loud line, and harmless — with no
        # owner configured, ``config.is_owner`` matches nobody, so no reply to
        # this request could ever approve it.
        LOG.warning("approval request %s composed with no approval address configured — "
                    "it cannot be delivered and no reply can approve it", token[:8])
    LOG.info("approval request %s composed for %s (caution=%s)",
             token[:8], action_text, grounding.needs_caution)
    return request


__all__ = ["CAUTION_HEADING", "DEFAULT_TTL_HOURS", "QUESTION", "SUBJECT_CAUTION", "TOKEN_TAG",
           "caution_lines", "compose_request", "grounding_lines", "read_grounding",
           "render_body", "subject_line"]
