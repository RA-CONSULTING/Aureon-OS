"""Data model for the assembled context brief.

The brief exists so that Aureon can hand a stronger model — or a person — the
same paragraph of context Gary used to type by hand, without any of it being
typed. That only has value if every line in it can be traced back to the file it
came from, so provenance is not a field a caller may forget:
:class:`SourcedLine` and :class:`Priority` both refuse to construct without a
``source``. The same rule :class:`aureon.grants.schemas.Opportunity` enforces for
retrieval, enforced here for narration.

Three properties of this model are load-bearing:

1. **A line without a source is not representable.** There is no plain ``str``
   in :class:`Brief` other than the section-free bookkeeping (``sources``,
   ``blockers``), so a sentence cannot reach a rendered brief unless something
   read it out of a document or measured it from a live organ.
2. **Absence is a section that is missing, plus a stated reason.** Every field
   defaults to empty. An empty section is never rendered as an assertion; the
   reason it is empty lives in :attr:`Brief.blockers`.
3. **Nothing here is about this company.** Not a name, a number, an address, a
   sector or a positioning phrase. Those arrive at runtime from the organs, and
   this module could describe a different company tomorrow without being edited.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

# Severity ranks used to order :class:`Priority` items. Compliance blockers sort
# above deadlines deliberately: a live eligibility blocker gates every bid, so a
# deadline behind it is effort that may not be spendable at all. ``unknown``
# ranks with them because "we could not check" is not clearance — that is the
# contract :mod:`aureon.grants.compliance` holds, and reordering it here would
# quietly disagree with the auditor.
SEVERITY_ORDER: tuple[str, ...] = (
    "blocker",
    "unknown",
    "overdue",
    "critical",
    "urgent",
    "approaching",
)


def severity_rank(severity: str) -> int:
    """Sort key for a severity. An unrecognised severity sorts last, not first.

    An unknown label must not be able to promote itself to the top of the list
    by accident; if a new band appears upstream it shows up at the bottom, which
    is visible without being alarming.
    """
    try:
        return SEVERITY_ORDER.index(str(severity or "").strip().lower())
    except ValueError:
        return len(SEVERITY_ORDER)


@dataclass(frozen=True)
class SourcedLine:
    """One statement plus the file it was read out of.

    ``source`` may name a document (``COMPANY.md``) or the organ that took the
    measurement (``aureon/core/hnc_field.py::read_canonical_field``). Both are
    real provenance: one is a quote, the other is a reading, and the reader can
    tell which by looking at it.
    """

    text: str
    source: str

    def __post_init__(self) -> None:
        if not str(self.text or "").strip():
            raise ValueError("SourcedLine.text is empty — an empty line is an absence, not a line")
        if not str(self.source or "").strip():
            raise ValueError("SourcedLine.source is mandatory — record WHERE this line came from")

    def __str__(self) -> str:
        return self.text

    def cite(self) -> str:
        """The line with its provenance attached, for a human reading it."""
        return f"{self.text}  [{self.source}]"

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "source": self.source}


@dataclass(frozen=True)
class Priority:
    """One thing that is pressing, and how pressing it measurably is.

    ``days_remaining`` is a real number of days computed from a real date, or
    ``None``. It is never zero-as-a-placeholder: an item with no date in its
    source carries ``None``, because "no deadline was recorded" and "the deadline
    is today" are opposite facts.
    """

    label: str
    detail: str
    days_remaining: float | None
    severity: str
    source: str

    def __post_init__(self) -> None:
        if not str(self.label or "").strip():
            raise ValueError("Priority.label is mandatory")
        if not str(self.severity or "").strip():
            raise ValueError("Priority.severity is mandatory")
        if not str(self.source or "").strip():
            raise ValueError("Priority.source is mandatory — record WHERE this came from")

    @property
    def dated(self) -> bool:
        """True when a real date was available to measure against."""
        return self.days_remaining is not None

    @property
    def overdue(self) -> bool | None:
        """True/False when dated; ``None`` when there is no date to judge by."""
        if self.days_remaining is None:
            return None
        return self.days_remaining < 0

    @property
    def rank(self) -> int:
        return severity_rank(self.severity)

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "detail": self.detail,
            "days_remaining": (round(self.days_remaining, 2)
                               if self.days_remaining is not None else None),
            "severity": self.severity,
            "source": self.source,
            "overdue": self.overdue,
        }


@dataclass(frozen=True)
class Capability:
    """One package the repository actually carries, as probed on disk.

    Every field records *what was measured and how*, because the interesting
    failure here is a claim that overstates itself. ``importable`` is measured
    with :func:`importlib.util.find_spec` — the module is **located, not
    executed** — and ``probe`` says so in the record rather than only in a
    docstring. ``tests_verified`` is ``None`` unless a runner actually ran the
    test module; it is never inferred from the file's existence, so a brief
    cannot claim a passing test suite that nobody ran.
    """

    package: str
    test_modules: tuple[str, ...] = ()
    importable: bool | None = None
    probe: str = ""
    tests_verified: bool | None = None
    verification: str = ""
    source: str = ""

    @property
    def claim(self) -> str:
        """The strongest sentence this record actually supports."""
        count = len(self.test_modules)
        tests = f"{count} test module{'s' if count != 1 else ''} on disk"
        if self.tests_verified is True:
            tests += f" — all passing ({self.verification})"
        elif self.tests_verified is False:
            tests += f" — FAILING ({self.verification})"
        else:
            tests += " — not run in this pass, so no pass/fail is claimed"
        if self.importable is True:
            state = "importable"
        elif self.importable is False:
            state = "NOT importable"
        else:
            state = "importability not measured"
        return f"{self.package}: {state} ({self.probe or 'probe not recorded'}); {tests}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "package": self.package,
            "test_modules": list(self.test_modules),
            "importable": self.importable,
            "probe": self.probe,
            "tests_verified": self.tests_verified,
            "verification": self.verification,
            "source": self.source,
            "claim": self.claim,
        }


@dataclass(frozen=True)
class Brief:
    """The assembled context brief. Every section is sourced or absent.

    Field order is narration order, which is also the order
    :func:`aureon.briefing.render.render_prompt` writes them in.
    """

    identity: tuple[SourcedLine, ...] = ()
    spine: tuple[SourcedLine, ...] = ()
    capabilities_built: tuple[Capability, ...] = ()
    standing_rule: SourcedLine | None = None
    live_priorities: tuple[Priority, ...] = ()
    positioning: SourcedLine | None = None
    claim_discipline: SourcedLine | None = None
    generated_at: datetime | None = None
    sources: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()

    # Declaration order == narration order. Not a dataclass field (no annotation).
    SECTIONS = (
        "identity",
        "spine",
        "capabilities_built",
        "standing_rule",
        "live_priorities",
        "positioning",
        "claim_discipline",
    )

    @property
    def present(self) -> tuple[str, ...]:
        """Sections that carry something real, in narration order."""
        out: list[str] = []
        for name in self.SECTIONS:
            value = getattr(self, name)
            if value is None:
                continue
            if isinstance(value, tuple) and not value:
                continue
            out.append(name)
        return tuple(out)

    @property
    def omitted(self) -> tuple[str, ...]:
        present = set(self.present)
        return tuple(n for n in self.SECTIONS if n not in present)

    @property
    def available(self) -> bool:
        """True when at least one section was assembled from a real source."""
        return bool(self.present)

    @property
    def lines(self) -> tuple[SourcedLine, ...]:
        """Every sourced line in the brief, in narration order."""
        out: list[SourcedLine] = [*self.identity, *self.spine]
        for one in (self.standing_rule, self.positioning, self.claim_discipline):
            if one is not None:
                out.append(one)
        return tuple(out)

    @property
    def overdue(self) -> tuple[Priority, ...]:
        return tuple(p for p in self.live_priorities if p.overdue is True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "available": self.available,
            "identity": [line.to_dict() for line in self.identity],
            "spine": [line.to_dict() for line in self.spine],
            "capabilities_built": [c.to_dict() for c in self.capabilities_built],
            "standing_rule": self.standing_rule.to_dict() if self.standing_rule else None,
            "live_priorities": [p.to_dict() for p in self.live_priorities],
            "positioning": self.positioning.to_dict() if self.positioning else None,
            "claim_discipline": (self.claim_discipline.to_dict()
                                 if self.claim_discipline else None),
            "present_sections": list(self.present),
            "omitted_sections": list(self.omitted),
            "sources": list(self.sources),
            "blockers": list(self.blockers),
        }


__all__ = [
    "SEVERITY_ORDER",
    "Brief",
    "Capability",
    "Priority",
    "SourcedLine",
    "severity_rank",
]
