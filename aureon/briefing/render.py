"""Render the assembled brief — one page for a person, one prompt for a model.

:func:`render_markdown` is for reading. :func:`render_prompt` reproduces the
shape of the owner's own handoff prompt so the brief can be exported to a
stronger model than the one this repository runs locally.

Both renderers obey the same three rules:

1. **A section with no content is omitted, and its absence is visible.** There is
   no branch here that writes a heading and then fills it with a hedge. What
   could not be read is listed under its own heading, once, with the reason the
   assembler recorded.
2. **The standing rule and the claim discipline are printed verbatim.** They are
   emitted as their own lines, unwrapped and unedited, and the citation goes on
   the following line so that not even a bracket lands inside the quoted text. A
   paraphrased constraint is a different constraint, and these two are the ones
   that keep the organism from sending, filing, paying, or overclaiming.
3. **A missing standing rule fails closed.** If the rule could not be read, the
   prompt does not fall silent — silence would read as "no such rule". It states
   that the rule was not readable and that nothing is authorised on the strength
   of the brief. That sentence is an instruction to the reader, marked as such,
   not a quotation attributed to any document.
"""

from __future__ import annotations

from typing import Any, Sequence

from aureon.briefing.schemas import Brief, Capability, Priority, SourcedLine

# An instruction to whoever reads the prompt, not a claim about the world and not
# a quotation from any document. It carries no company detail, and a caller who
# wants a different register passes their own.
BLUNTNESS = (
    "Be blunt. If a route is a poor fit or a claim is too strong, say so — "
    "that is more useful than agreement."
)

# What the prompt says when the standing rule could not be read. Fails closed on
# purpose: an unreadable approval rule must never render as an absent one.
NO_RULE_READ = (
    "STANDING RULE: NOT READ — the approval rule could not be sourced from any document "
    "(see WHAT COULD NOT BE READ). Nothing in this brief authorises an external submission, "
    "legal representation, filing, payment, or email send."
)

_DASH = "—"

# How many test module names one capability line prints. Past this the list stops
# informing and starts being a directory listing — one probed package here holds
# 41 of them. The count not shown is always printed, so the cap narrows the
# rendering and never the measurement.
_MAX_MODULES = 6


def _days(priority: Priority) -> str:
    """Deadline pressure in words, or an honest absence."""
    if priority.days_remaining is None:
        return "no date recorded in the source"
    days = priority.days_remaining
    if days < 0:
        return f"OVERDUE by {abs(days):.1f} days"
    return f"{days:.1f} days remaining"


def _priority_line(priority: Priority) -> str:
    return (f"{priority.label} [{priority.severity}] {_DASH} {_days(priority)}. "
            f"{priority.detail}  [{priority.source}]")


def _capability_line(capability: Capability) -> str:
    shown = capability.test_modules[:_MAX_MODULES]
    modules = ", ".join(shown)
    hidden = len(capability.test_modules) - len(shown)
    if hidden > 0:
        modules += f", +{hidden} more not shown"
    return f"{capability.claim} ({modules})  [{capability.source}]"


def _quoted(line: SourcedLine, label: str) -> list[str]:
    """A verbatim rule as its own block, with the citation kept outside it."""
    return [f"{label}: {line.text}", f"    read from {line.source}", ""]


def render_markdown(brief: Brief) -> str:
    """The brief as one page a person can read in a minute.

    Every line carries its provenance in brackets. Sections the assembler could
    not source are absent from the body and accounted for at the foot, so the
    page cannot be mistaken for a complete picture when it is not.
    """
    generated = brief.generated_at.isoformat() if brief.generated_at else "time not recorded"
    lines: list[str] = [
        "# Aureon context brief",
        "",
        f"Assembled {generated} by `aureon.briefing.assemble` from live organs.",
        "Every line below was read from the file named beside it or measured from a running organ.",
        "Sections whose source could not be read are omitted from the body and listed at the foot.",
        "",
    ]

    if not brief.available:
        lines += [
            "## Nothing could be assembled",
            "",
            "No section had a readable source. The reasons are listed below; none of them "
            "has been filled in with a plausible substitute.",
            "",
        ]

    if brief.identity:
        lines += ["## Who this is", ""]
        lines += [f"- {line.cite()}" for line in brief.identity]
        lines.append("")

    if brief.spine:
        lines += [
            "## The decision spine (live reading)",
            "",
            "One spine serves every lane. The numbers below are this pass's readings, not a "
            "description of the design; a value that could not be read says so.",
            "",
        ]
        lines += [f"- {line.cite()}" for line in brief.spine]
        lines.append("")

    if brief.capabilities_built:
        lines += [
            "## Built and tested",
            "",
            "Probed on disk, not listed by hand: a package counts when it exists under "
            "`aureon/` and carries a test module under `tests/`. Pass/fail is only claimed "
            "where a runner actually ran the tests.",
            "",
        ]
        lines += [f"- {_capability_line(c)}" for c in brief.capabilities_built]
        lines.append("")

    lines += ["## Standing rule", ""]
    if brief.standing_rule:
        lines += [
            f"> {brief.standing_rule.text}",
            "",
            f"Read verbatim from `{brief.standing_rule.source}`.",
            "",
        ]
    else:
        lines += [
            "**Not readable.** No document under this root states the approval rule, so none "
            "is quoted here. Treat every external step as requiring explicit approval; that is "
            "a fail-closed instruction, not a quotation.",
            "",
        ]

    if brief.live_priorities:
        lines += [
            "## Live priorities",
            "",
            "Deadline items carry the ledger's own `days_remaining`. Compliance items carry a "
            "date only when their source quoted exactly one; otherwise the days column is "
            "absent rather than guessed. Blockers sort above deadlines because a live blocker "
            "gates the effort a deadline would consume.",
            "",
        ]
        lines += [f"- {_priority_line(p)}" for p in brief.live_priorities]
        lines.append("")

    if brief.positioning:
        lines += ["## Positioning", ""]
        lines += [f"> {brief.positioning.text}", "",
                  f"Read verbatim from `{brief.positioning.source}`.", ""]

    if brief.claim_discipline:
        lines += ["## Claim discipline", ""]
        lines += [f"> {brief.claim_discipline.text}", "",
                  f"Read verbatim from `{brief.claim_discipline.source}`.", ""]

    if brief.blockers:
        lines += ["## What could not be read", ""]
        lines += [f"- {b}" for b in brief.blockers]
        lines.append("")

    if brief.sources:
        lines += ["## Sources read", ""]
        lines += [f"- `{s}`" for s in brief.sources]
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_prompt(
    brief: Brief,
    ask: str | Sequence[str] | None = None,
    *,
    tone: str | None = BLUNTNESS,
) -> str:
    """The brief in the shape of the owner's handoff prompt, for export.

    ``ask`` is what the receiving model is being asked to do — a single string or
    several. It is the caller's words; nothing here invents an ask, because an ask
    this module made up would be a task nobody requested.

    The two verbatim rules are emitted on their own lines with the citation
    underneath, so the quoted text is byte-for-byte what the document says. If the
    standing rule could not be read the prompt says so and forbids external action
    anyway — see :data:`NO_RULE_READ`.
    """
    generated = brief.generated_at.isoformat() if brief.generated_at else "time not recorded"
    out: list[str] = [
        "CONTEXT (assembled by Aureon from her own organs, not typed by hand)",
        f"Generated {generated}. Every line carries the file or organ it came from. "
        "Anything that could not be read is listed at the end as NOT READ rather than filled in.",
        "",
    ]

    if brief.identity:
        out.append("IDENTITY")
        out += [f"- {line.cite()}" for line in brief.identity]
        out.append("")

    if brief.spine:
        out.append("DECISION SPINE (live reading, this pass)")
        out += [f"- {line.cite()}" for line in brief.spine]
        out.append("")

    if brief.capabilities_built:
        out.append("BUILT AND PROBED ON DISK")
        out += [f"- {_capability_line(c)}" for c in brief.capabilities_built]
        out.append("")

    if brief.standing_rule:
        out += _quoted(brief.standing_rule, "STANDING RULE")
    else:
        out += [NO_RULE_READ, ""]

    if brief.live_priorities:
        out.append("LIVE PRIORITIES")
        out += [f"- {_priority_line(p)}" for p in brief.live_priorities]
        out.append("")

    if brief.positioning:
        out += _quoted(brief.positioning, "POSITIONING")

    if brief.claim_discipline:
        out += _quoted(brief.claim_discipline, "CLAIM DISCIPLINE")

    asks = _asks(ask)
    if asks:
        out.append("ASKS" if len(asks) > 1 else "ASK")
        out += [f"{i}. {a}" for i, a in enumerate(asks, 1)] if len(asks) > 1 else [asks[0]]
        out.append("")

    if brief.blockers:
        out.append("NOT READ (do not treat any of these as clear)")
        out += [f"- {b}" for b in brief.blockers]
        out.append("")

    if tone:
        out += [tone, ""]

    return "\n".join(out).rstrip() + "\n"


def _asks(ask: Any) -> list[str]:
    """Normalise the caller's ask. An empty ask stays empty; none is invented."""
    if ask is None:
        return []
    if isinstance(ask, str):
        text = ask.strip()
        return [text] if text else []
    try:
        items = [str(a).strip() for a in ask]
    except TypeError:
        text = str(ask).strip()
        return [text] if text else []
    return [i for i in items if i]


__all__ = ["BLUNTNESS", "NO_RULE_READ", "render_markdown", "render_prompt"]
