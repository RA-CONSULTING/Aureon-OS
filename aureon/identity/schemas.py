"""Self-knowledge data model.

Three rules hold this model together, and they are the whole point of it:

1. **Every value carries the file it came from.** There is no plain ``str``
   anywhere in :class:`Identity` — only :class:`SourcedFact`, which cannot be
   constructed without a ``source_file``. A fact with no provenance is not
   representable, so it cannot be returned by accident.
2. **Absence is a first-class answer.** A field with no source is ``None`` and
   the reason is recorded in ``blockers``. Nothing is defaulted, inferred, or
   filled in from the model's own training.
3. **Confidence never reaches 1.0.** Every fact here is a claim made by a
   document inside this repository. The repository's own company record says
   the details are verifiable on the public register — which means that
   verification has *not* happened in this process. ``MAX_CONFIDENCE`` is the
   ceiling for anything read from a document; certainty is reserved for facts
   checked against an external authority, and this organ checks none.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

# Ceiling for a document-sourced claim. See rule 3 above.
MAX_CONFIDENCE = 0.99


@dataclass(frozen=True)
class SourcedFact:
    """One value plus the document it was read out of.

    ``corroborated_by`` lists other files stating the same thing;
    ``conflicts`` lists files stating something different, as
    ``(source_file, value)`` pairs. Disagreement between two repository
    documents is surfaced, never silently resolved — the reader picks the
    higher-priority source but the loser is kept visible so a human can
    reconcile the records.
    """

    value: str
    source_file: str
    confidence: float
    corroborated_by: tuple[str, ...] = ()
    conflicts: tuple[tuple[str, str], ...] = ()

    def __str__(self) -> str:
        return self.value

    def cite(self) -> str:
        """A short human-readable provenance string."""
        parts = [f"{self.source_file} · confidence {self.confidence:.2f}"]
        if self.corroborated_by:
            parts.append("corroborated by " + ", ".join(self.corroborated_by))
        if self.conflicts:
            parts.append(
                "disputed by " + ", ".join(f"{src} ({val})" for src, val in self.conflicts)
            )
        return "; ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "source_file": self.source_file,
            "confidence": self.confidence,
            "corroborated_by": list(self.corroborated_by),
            "conflicts": [{"source_file": s, "value": v} for s, v in self.conflicts],
        }


@dataclass(frozen=True)
class Identity:
    """Who she is, what she is for — every field sourced or absent."""

    legal_entity: SourcedFact | None = None
    company_number: SourcedFact | None = None
    registered_office: SourcedFact | None = None
    lead_contact: SourcedFact | None = None
    mission: SourcedFact | None = None
    purpose: SourcedFact | None = None

    # Declaration order == narration order. Not a dataclass field (no annotation).
    FIELDS = (
        "legal_entity",
        "company_number",
        "registered_office",
        "lead_contact",
        "mission",
        "purpose",
    )
    COMPANY_FIELDS = ("legal_entity", "company_number", "registered_office", "lead_contact")

    @property
    def known(self) -> dict[str, SourcedFact]:
        """The fields that were actually found, in declaration order."""
        out: dict[str, SourcedFact] = {}
        for name in self.FIELDS:
            fact = getattr(self, name)
            if fact is not None:
                out[name] = fact
        return out

    @property
    def missing(self) -> tuple[str, ...]:
        return tuple(n for n in self.FIELDS if getattr(self, n) is None)

    @property
    def grounded(self) -> bool:
        """True when at least one field has a source behind it."""
        return bool(self.known)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            name: (fact.to_dict() if fact is not None else None)
            for name, fact in ((n, getattr(self, n)) for n in self.FIELDS)
        }
        out["missing"] = list(self.missing)
        return out


@dataclass(frozen=True)
class SelfKnowledge:
    """A grounded answer to "who am I, what am I working towards, what is this company".

    ``blocker`` is the joined summary of ``blockers``; the reader supplies
    ``blockers`` and the summary is derived, so the two can never drift apart.
    ``identity`` is always an :class:`Identity` — an unavailable read returns one
    whose fields are all ``None``, so a caller reading a field gets an honest
    absence rather than an :class:`AttributeError`.
    """

    available: bool
    identity: Identity
    goals: tuple[SourcedFact, ...] = ()
    blocker: str | None = None
    blockers: tuple[str, ...] = ()
    generated_at: datetime | None = None
    sources_read: tuple[str, ...] = ()
    root: str = ""

    def __post_init__(self) -> None:
        if self.blocker is None and self.blockers:
            object.__setattr__(self, "blocker", "; ".join(self.blockers))

    @property
    def facts(self) -> tuple[SourcedFact, ...]:
        """Every fact this read produced — identity fields and goals alike."""
        return tuple(self.identity.known.values()) + tuple(self.goals)

    def narrate(self) -> str:
        """Answer the three questions in plain text, with citations.

        Unknowns are stated as unknown. This method never composes a sentence
        out of a value it does not hold.
        """
        ident = self.identity
        lines: list[str] = ["WHO I AM"]
        company = [n for n in ident.COMPANY_FIELDS if getattr(ident, n) is not None]
        if company:
            for name in company:
                fact: SourcedFact = getattr(ident, name)
                lines.append(f"  {name.replace('_', ' ')}: {fact.value}  [{fact.cite()}]")
        else:
            lines.append("  unknown — no company record was found in this repository.")

        for name, heading in (("purpose", "WHAT THIS IS"), ("mission", "WHAT I AM FOR")):
            fact = getattr(ident, name)
            lines.append(heading)
            if fact is not None:
                lines.append(f"  {fact.value}  [{fact.cite()}]")
            else:
                lines.append(f"  unknown — no {name} statement was found.")

        lines.append("WHAT I AM WORKING TOWARDS")
        if self.goals:
            for i, goal in enumerate(self.goals, 1):
                lines.append(f"  {i}. {goal.value}  [{goal.cite()}]")
        else:
            lines.append("  unknown — no stated goals were found.")

        if self.blockers:
            lines.append("WHAT I CANNOT ANSWER, AND WHY")
            lines.extend(f"  - {b}" for b in self.blockers)
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "root": self.root,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "identity": self.identity.to_dict(),
            "goals": [g.to_dict() for g in self.goals],
            "blocker": self.blocker,
            "blockers": list(self.blockers),
            "sources_read": list(self.sources_read),
        }


__all__ = ["Identity", "SelfKnowledge", "SourcedFact", "MAX_CONFIDENCE"]
