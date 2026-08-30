"""The auditor — the gates a grant office checks *before* effort is spent.

A grant is lost at the eligibility stage far more often than at the writing
stage, and it is lost silently: the blocker was always there, nobody read it,
and the discovery happens at the submit button with a deadline in hours. The
reconciliation of 2026-07-31 found exactly that shape in this company's own
record — a Companies House confirmation statement flagged P0 `Immediate blocker`
in four separate places in the war-room sheet, named as an open dependency on an
application that has *already been submitted*, and encoded nowhere the OS could
read it. Its own recommendation #14 asks for these rules to be made machine
readable. This module is that.

What it is not
--------------
It is not a scoring model and it does not opine on fit. It answers one question
per check — *can this evidence be produced from a real document right now?* —
and it answers ``unknown`` far more readily than it answers ``pass``.

Three rules hold it together
----------------------------
1. **Nothing is hardcoded.** There is no company number, address, or blocker
   string in this file. The Companies House finding is *read* — from the ledger's
   own ``company_compliance_risk_status`` key or from the reconciliation report
   beside it — so if the statement is filed tomorrow and the source updated, this
   code reports it clear without being edited. A hardcoded blocker would be a
   fabricated measurement that happens to be true today.
2. **A missing source is ``unknown``, never ``pass``.** Silence is not clearance.
   This is the trap the module exists to avoid: an auditor that reads nothing and
   reports green is worse than no auditor, because it manufactures confidence.
3. **An all-unknown report cannot read as healthy.** :attr:`ComplianceReport.status`
   is a derived property, not a stored field, and it requires at least one check
   to have *genuinely passed* before it can say ``pass``. There is no assignment
   anywhere that can make an empty audit look clean.

Routing
-------
Decisions leave here through :mod:`aureon.gates.switchboard`, like every other
capability: :func:`compliance_verdict` expresses the audit in the switchboard's
own ADVANCE / REDO / HOLD vocabulary, and :func:`run_gate_chain` refuses to spend
the Queen's chain at all while a blocker is live. HOLD is used where the remedy
has no automatic executor — filing a statutory return is a *filing*, and this
repository has no hand that files.

Read-only. It never edits the ledger, the sheet, or any source document.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aureon.gates.switchboard import (
    ADVANCE,
    DEFAULT_CHAIN,
    HOLD,
    REDO,
    Gate,
    GateReading,
    GateVerdict,
    is_human_held,
    run_chain,
)
from aureon.grants.schemas import Application

LOG = logging.getLogger("aureon.grants.compliance")

# aureon/grants/compliance.py -> parents[2] is the repository root.
REPO_ROOT = Path(__file__).resolve().parents[2]

PASS = "pass"
FAIL = "fail"
UNKNOWN = "unknown"

GRANTS_SUBDIR = ("data", "research", "grants")
LEDGER_NAME = "pipeline.json"
APPLICANT_JSON = "data/research/grants/autopilot_status.json"
COMPANY_DOC = "COMPANY.md"
# Date-stamped, so the newest sorts last. Matched by pattern rather than by a
# fixed filename: pinning ``RECONCILIATION_20260731.md`` here would make this
# module silently stop auditing the day a fresher reconciliation lands.
RECONCILIATION_GLOB = "RECONCILIATION_*.md"

# The ledger's own compliance keys. These are written by the grant operator's
# runs; reading them is a measurement, not an inference.
_LEDGER_RISK_FLAGS = (
    "company_compliance_risk_active",
    "company_confirmation_statement_warning_active",
)
_LEDGER_RISK_STATUS = "company_compliance_risk_status"

_CONFIRMATION = re.compile(r"confirmation statement", re.I)
# Precedence matters and it is not symmetric. The war-room checklist row reads
# "Confirmation statement overdue cleared | Not clear" — it contains the word
# "cleared" while asserting the opposite. So an overdue marker anywhere wins over
# a resolved marker anywhere, the same way ``Application._LIVE_MARKERS`` beats
# ``_TERMINAL_MARKERS`` in schemas.py. Getting this backwards would report a live
# P0 blocker as resolved, which is the single most expensive error available here.
_OVERDUE = re.compile(r"\b(overdue|not clear|action required)\b", re.I)
_RESOLVED = re.compile(r"\b(no longer overdue|filed and accepted|up to date|"
                       r"statement filed|resolution recorded)\b", re.I)
# The one exception to that precedence. "No longer overdue" contains "overdue",
# so without this guard a clearance would be read as the thing it clears — and
# the blocker would then be permanent no matter what the registrar did. The
# guard is deliberately narrow: direct negation of the word itself, nothing more.
# Anything cleverer is a sentiment classifier, and for an ambiguous line the safe
# direction is to leave it reading as a blocker.
_NEGATED_OVERDUE = re.compile(r"\b(?:no longer|not|never)\s+overdue\b", re.I)
_APPROVAL = re.compile(
    r"\bwithout\b[^.]{0,80}\bapproval\b"          # "...without Gary approval."
    r"|\brequires?\b[^.]{0,80}\bconfirmation\b"   # "...require exact action-time confirmation"
    r"|\bapproval authority\b",
    re.I,
)

_MAX_DETAIL = 300
_MAX_IDS = 6
_WHITESPACE = re.compile(r"\s+")
_LEADING_MARKUP = re.compile(r"^[>\s|*_+-]+")


def _quote(line: str) -> str:
    """A source line reduced to readable text, without altering what it says.

    Markdown decoration is stripped; wording is not. Long lines are truncated
    with an ellipsis so a detail string stays legible, and the ``source`` field
    always names the file so the full sentence remains findable.
    """
    text = _LEADING_MARKUP.sub("", line.strip())
    text = text.replace("**", "").replace("`", "").strip().strip('"').strip()
    text = _WHITESPACE.sub(" ", text).strip()
    return text[:_MAX_DETAIL].rstrip() + "…" if len(text) > _MAX_DETAIL else text


def _first_match(text: str, *patterns: re.Pattern[str]) -> str | None:
    """The first line matching every pattern, quoted. None when there is none."""
    for line in text.splitlines():
        if all(p.search(line) for p in patterns):
            return _quote(line)
    return None


def _first_line(text: str, predicate: Any) -> str | None:
    """The first line the predicate accepts, quoted. None when there is none."""
    for line in text.splitlines():
        if predicate(line):
            return _quote(line)
    return None


def _says_overdue(line: str) -> bool:
    """True when this line asserts an outstanding statutory filing."""
    return bool(_CONFIRMATION.search(line)
                and _OVERDUE.search(_NEGATED_OVERDUE.sub(" ", line)))


def _says_resolved(line: str) -> bool:
    """True when this line asserts the filing is made or the risk recorded closed."""
    return bool(_CONFIRMATION.search(line) and _RESOLVED.search(line))


# ── the findings ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ComplianceCheck:
    """One eligibility or compliance question, and what the documents said.

    ``status`` is ``pass`` | ``fail`` | ``unknown``. The three are genuinely
    different answers and are never collapsed: ``fail`` means a document was read
    and it says no; ``unknown`` means no document could answer, which is a
    blocker in its own right whenever ``blocking`` is set.

    ``source`` names the file the finding came from. It is empty exactly when no
    document carried the finding — i.e. on an ``unknown`` — and ``detail`` then
    says where the auditor looked.

    ``remedy`` is an instruction, not a measurement: the action that would clear
    this check. It is phrased in ordinary words so
    :func:`aureon.gates.switchboard.is_human_held` can recognise the ones no
    automatic executor exists for ("file…", "submit…") without a second policy
    list being invented here.
    """

    name: str
    status: str
    detail: str
    source: str = ""
    blocking: bool = False
    remedy: str = ""

    @property
    def cleared(self) -> bool:
        return self.status == PASS

    @property
    def is_live_blocker(self) -> bool:
        """A blocking check that did not pass — *including* one that is unknown.

        Unknown counts. A funder does not accept "we could not check" as an
        answer, and treating it as anything other than a live blocker is how a
        silent audit turns into a green light.
        """
        return self.blocking and self.status != PASS

    @property
    def human_held(self) -> bool:
        """True when clearing this needs a hand the repository does not have."""
        return is_human_held(self.remedy)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
            "source": self.source,
            "blocking": self.blocking,
            "remedy": self.remedy,
            "is_live_blocker": self.is_live_blocker,
            "human_held": self.human_held,
        }


@dataclass(frozen=True)
class ComplianceReport:
    """Every check, and one derived verdict that cannot be faked.

    :attr:`status` is a property with no setter and no stored counterpart, so
    there is no code path — here or in a caller — that can mark a report clean
    without a check having actually passed. That is the structural guarantee the
    docstring at the top of this module promises; an all-``unknown`` report has
    ``passed_count == 0`` and therefore reads ``fail``, always.
    """

    checks: tuple[ComplianceCheck, ...] = ()
    generated_at: datetime | None = None
    root: str = ""
    ledger_path: str = ""
    sources_read: tuple[str, ...] = ()
    problems: tuple[str, ...] = ()

    @property
    def blockers(self) -> tuple[ComplianceCheck, ...]:
        return tuple(c for c in self.checks if c.is_live_blocker)

    @property
    def blocking_count(self) -> int:
        """How many blockers are *live* — blocking checks that failed or are unknown.

        Not "how many checks are marked blocking". A cleared blocking check is
        not a blocker, and counting it as one would make a clean audit look
        obstructed.
        """
        return len(self.blockers)

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.status == PASS)

    @property
    def failed_count(self) -> int:
        return sum(1 for c in self.checks if c.status == FAIL)

    @property
    def unknown_count(self) -> int:
        return sum(1 for c in self.checks if c.status == UNKNOWN)

    @property
    def status(self) -> str:
        """``pass`` only when something genuinely passed and nothing blocks."""
        if self.passed_count == 0:
            return FAIL
        return FAIL if self.blocking_count else PASS

    @property
    def ready(self) -> bool:
        """True when a grant office would let effort proceed."""
        return self.status == PASS

    def narrate(self) -> str:
        """The audit in plain text, blockers first. Unknowns are stated as unknown."""
        lines = [f"COMPLIANCE READINESS: {self.status.upper()}"
                 f"  ({self.passed_count} passed, {self.failed_count} failed, "
                 f"{self.unknown_count} unknown; {self.blocking_count} live blocker(s))"]
        for check in sorted(self.checks, key=lambda c: (not c.is_live_blocker, c.name)):
            mark = "BLOCKER" if check.is_live_blocker else check.status.upper()
            where = f"  [{check.source}]" if check.source else ""
            lines.append(f"  {mark:<7} {check.name}: {check.detail}{where}")
            if check.is_live_blocker and check.remedy:
                held = " (no automatic executor — a person's to take)" if check.human_held else ""
                lines.append(f"          -> {check.remedy}{held}")
        if self.problems:
            lines.append("SOURCES THAT COULD NOT BE READ")
            lines.extend(f"  - {p}" for p in self.problems)
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "ready": self.ready,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "root": self.root,
            "ledger_path": self.ledger_path,
            "checks": [c.to_dict() for c in self.checks],
            "blockers": [c.name for c in self.blockers],
            "blocking_count": self.blocking_count,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "unknown_count": self.unknown_count,
            "sources_read": list(self.sources_read),
            "problems": list(self.problems),
        }


# ── guarded document access ──────────────────────────────────────────────────


class _Docs:
    """Cached, never-raising access to documents. Records what it could not read.

    Paths are used exactly as given. Following the lesson recorded in
    ``ledger.grants_dir`` and ``identity.reader``: a reader that quietly widens
    to the real repository when the caller's directory comes up empty hides
    faults and leaks live data into tests. A missing document is a blocker, never
    a fallback.
    """

    def __init__(self) -> None:
        self.read: list[str] = []
        self.problems: list[str] = []
        self._cache: dict[Path, str | None] = {}

    def text(self, path: Path, label: str) -> str | None:
        if path in self._cache:
            return self._cache[path]
        content: str | None
        if not path.is_file():
            self.problems.append(f"{label}: not found at {path}")
            content = None
        else:
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                self.problems.append(f"{label}: unreadable ({type(exc).__name__})")
                content = None
            else:
                if not content.strip():
                    self.problems.append(f"{label}: empty")
                    content = None
                else:
                    self.read.append(label)
        self._cache[path] = content
        return content

    def mapping(self, path: Path, label: str) -> dict[str, Any] | None:
        raw = self.text(path, label)
        if raw is None:
            return None
        try:
            loaded = json.loads(raw)
        except (ValueError, RecursionError) as exc:  # JSONDecodeError is a ValueError
            self.problems.append(f"{label}: not valid JSON ({type(exc).__name__})")
            if label in self.read:
                self.read.remove(label)
            return None
        if not isinstance(loaded, dict):
            self.problems.append(f"{label}: JSON root is not an object")
            return None
        return loaded


def _unknown(name: str, looked_in: tuple[str, ...], *, blocking: bool, remedy: str) -> ComplianceCheck:
    """The honest answer when no document could speak to a check."""
    return ComplianceCheck(
        name=name,
        status=UNKNOWN,
        detail="no source document answers this (looked in " + ", ".join(looked_in) + ")",
        source="",
        blocking=blocking,
        remedy=remedy,
    )


# ── the individual checks ────────────────────────────────────────────────────


def _identity_check(name: str, fact: Any, looked_in: tuple[str, ...]) -> ComplianceCheck:
    """Is this company fact stated by a document, and do the documents agree?

    A conflict is a ``fail``, not a low-confidence ``pass``. Two repository
    documents giving different registered offices is a real finding: whichever a
    funder reads, one of them is wrong, and an application that quotes the wrong
    one is an application that gets returned.
    """
    remedy = f"record the {name.replace('_', ' ')} in a repository document"
    if fact is None:
        return _unknown(name, looked_in, blocking=True, remedy=remedy)
    conflicts = getattr(fact, "conflicts", ())
    if conflicts:
        disputed = "; ".join(f"{src} says {val!r}" for src, val in conflicts)
        return ComplianceCheck(
            name=name,
            status=FAIL,
            detail=f"{fact.source_file} says {fact.value!r} but {disputed} — "
                   "the record contradicts itself and a funder will read only one of them",
            source=fact.source_file,
            blocking=True,
            remedy=f"reconcile the {name.replace('_', ' ')} across the repository's documents",
        )
    corroboration = (f" (corroborated by {', '.join(fact.corroborated_by)})"
                     if fact.corroborated_by else "")
    return ComplianceCheck(
        name=name,
        status=PASS,
        detail=f"{fact.value}{corroboration}",
        source=fact.source_file,
        blocking=True,
        remedy=remedy,
    )


def _statutory_filings_check(
    recon: tuple[str, str] | None,
    ledger: tuple[str, dict[str, Any]] | None,
    looked_in: tuple[str, ...],
) -> ComplianceCheck:
    """Are the company's statutory filings current?

    This is the check the module was built around, and it is deliberately built
    to be *unable* to hardcode its answer. Two independent real sources are read:

    * the ledger's own ``company_compliance_risk_*`` keys, written by the grant
      operator's runs;
    * the newest ``RECONCILIATION_*.md`` beside it, which quotes the war-room
      sheet verbatim.

    An explicit negative in either source is a ``fail``. An explicit clearance,
    with no negative anywhere, is a ``pass``. Silence — or an absent document —
    is ``unknown``, because "no document mentions it" and "the filing is current"
    are different facts and only one of them was observed.
    """
    name = "statutory_filings_current"
    remedy = "file the outstanding statutory return with the registrar, or record its resolution"
    failures: list[tuple[str, str]] = []
    clearances: list[tuple[str, str]] = []

    if recon is not None:
        label, text = recon
        # Scanned in this order across the whole document, not line by line: an
        # overdue assertion anywhere outranks a clearance anywhere else.
        overdue = _first_line(text, _says_overdue)
        if overdue is not None:
            failures.append((label, overdue))
        else:
            resolved = _first_line(text, _says_resolved)
            if resolved is not None:
                clearances.append((label, resolved))

    if ledger is not None:
        label, raw = ledger
        status_value = raw.get(_LEDGER_RISK_STATUS)
        status_text = status_value if isinstance(status_value, str) else ""
        raised = [k for k in _LEDGER_RISK_FLAGS if raw.get(k) is True]
        lowered = [k for k in _LEDGER_RISK_FLAGS if raw.get(k) is False]
        # The status is SCREAMING_SNAKE in the ledger; underscores become spaces
        # so the same word patterns apply, and the same negation guard with them.
        spaced = _NEGATED_OVERDUE.sub(" ", status_text.replace("_", " "))
        if raised or _OVERDUE.search(spaced):
            detail = status_text or ", ".join(raised)
            failures.append((label, f"{detail} ({', '.join(raised) or _LEDGER_RISK_STATUS})"))
        elif lowered:
            # An explicit ``false`` is a statement; a missing key is not. Only the
            # former clears this check.
            clearances.append((label, f"{', '.join(lowered)} recorded false"))

    if failures:
        source, detail = failures[0]
        others = ", ".join(s for s, _ in failures[1:])
        suffix = f" (corroborated by {others})" if others else ""
        return ComplianceCheck(name=name, status=FAIL, detail=detail + suffix,
                               source=source, blocking=True, remedy=remedy)
    if clearances:
        source, detail = clearances[0]
        return ComplianceCheck(name=name, status=PASS, detail=detail,
                               source=source, blocking=True, remedy=remedy)
    return _unknown(name, looked_in, blocking=True, remedy=remedy)


def _approval_rule_check(
    recon: tuple[str, str] | None,
    applicant: tuple[str, dict[str, Any]] | None,
    looked_in: tuple[str, ...],
) -> ComplianceCheck:
    """Does a real document state that a human must approve an external step?

    A ``pass`` here means the rule was *found and can be quoted*, so the OS can
    honour it. ``unknown`` is blocking on purpose: an automation that cannot see
    its own approval rule must not proceed on the assumption that there isn't
    one. The rule is never assumed into existence either — absence is reported as
    absence, and a human decides what that means.
    """
    name = "human_approval_rule"
    remedy = "record the approval rule in a document the OS can read"
    found: list[tuple[str, str]] = []

    if recon is not None:
        label, text = recon
        quoted = _first_match(text, _APPROVAL)
        if quoted is not None:
            found.append((label, quoted))

    if applicant is not None:
        label, raw = applicant
        policy = raw.get("automation_policy")
        if isinstance(policy, list):
            for item in policy:
                if isinstance(item, str) and _APPROVAL.search(item):
                    found.append((label, _quote(item)))
                    break

    if not found:
        return _unknown(name, looked_in, blocking=True, remedy=remedy)
    source, detail = found[0]
    others = ", ".join(s for s, _ in found[1:])
    suffix = f" (corroborated by {others})" if others else ""
    return ComplianceCheck(name=name, status=PASS, detail=detail + suffix,
                           source=source, blocking=True, remedy=remedy)


def _prior_grant_check(label: str, apps: tuple[Application, ...] | None) -> ComplianceCheck:
    """What prior funding and provider relationships can actually be declared?

    Non-blocking, and that is a judgement worth stating: a first-time applicant
    is eligible everywhere. What a funder gates on is the *accuracy* of the
    declaration — subsidy-control and prior-award questions are answered on the
    form — so the auditor's job is to say what the record supports, not to
    penalise a zero. A zero here is a real reading, not a failure.
    """
    name = "prior_grant_status"
    remedy = "compile the prior-funding declaration from the application ledger"
    if apps is None:
        return _unknown(name, (label,), blocking=False, remedy=remedy)
    submitted = [a for a in apps if a.submitted_at is not None]
    # Exact match, for the same reason CLOSED_STATES is matched exactly in
    # schemas.py: these statuses are free text, and a substring hunt for "award"
    # catches "award terms incomplete" and invents a grant nobody won.
    awarded = [a for a in apps if a.status.strip().upper() == "AWARDED"]
    detail = (f"{len(submitted)} of {len(apps)} ledger applications carry a recorded "
              f"submission timestamp; {len(awarded)} carry an exact AWARDED status")
    if submitted:
        shown = ", ".join(a.id for a in submitted[:_MAX_IDS])
        more = f" (+{len(submitted) - _MAX_IDS} more)" if len(submitted) > _MAX_IDS else ""
        detail += f" — e.g. {shown}{more}"
    return ComplianceCheck(name=name, status=PASS, detail=detail, source=label,
                           blocking=False, remedy=remedy)


def _evidence_completeness_check(label: str, apps: tuple[Application, ...] | None) -> ComplianceCheck:
    """Does every application in a live lifecycle carry an evidence pack?

    ``documents[]`` empty on a live application means there is nothing to attach.
    That is a blocker discovered cheaply here instead of expensively at the
    portal.

    The vacuous case is handled explicitly: with no live application there is
    nothing to measure, so the answer is ``unknown``, not ``pass``. Deriving
    health from an empty set is precisely the failure mode this module exists to
    prevent — and it is non-blocking, because "no live work" is not an
    obstruction, it is just nothing to check.
    """
    name = "application_evidence_complete"
    remedy = "attach the evidence pack to every application in a live lifecycle"
    if apps is None:
        return _unknown(name, (label,), blocking=True, remedy=remedy)
    live = [a for a in apps if a.lifecycle == "live"]
    if not live:
        return ComplianceCheck(
            name=name, status=UNKNOWN,
            detail=f"no application in {label} is in a live lifecycle — "
                   "completeness was not measured rather than assumed",
            source=label, blocking=False, remedy=remedy,
        )
    bare = [a for a in live if not a.documents]
    if bare:
        shown = ", ".join(a.id for a in bare[:_MAX_IDS])
        more = f" (+{len(bare) - _MAX_IDS} more)" if len(bare) > _MAX_IDS else ""
        return ComplianceCheck(
            name=name, status=FAIL,
            detail=f"{len(bare)} of {len(live)} live applications carry no documents: {shown}{more}",
            source=label, blocking=True, remedy=remedy,
        )
    return ComplianceCheck(name=name, status=PASS,
                           detail=f"all {len(live)} live applications carry at least one document",
                           source=label, blocking=True, remedy=remedy)


# ── the audit ────────────────────────────────────────────────────────────────


def _newest_reconciliation(directory: Path) -> Path | None:
    """The most recent dated reconciliation report, or None.

    Filenames are ``RECONCILIATION_YYYYMMDD.md``, so lexical order is
    chronological order. Never raises — an unreadable directory is simply a
    directory with no reconciliation in it, and the caller reports that as
    ``unknown``.
    """
    try:
        found = sorted(p for p in directory.glob(RECONCILIATION_GLOB) if p.is_file())
    except OSError:
        return None
    return found[-1] if found else None


def audit_readiness(
    root: Path | str | None = None,
    *,
    now: datetime | None = None,
    grants_directory: Path | str | None = None,
) -> ComplianceReport:
    """Audit eligibility and compliance readiness from real documents. Never raises.

    ``root`` is the repository root to read company documents from and is honoured
    verbatim — point it at an empty directory and every check comes back
    ``unknown``, which is the correct answer, not a reason to reach for the real
    repository.

    The ledger directory follows the same rule with one deliberate exception:
    when ``root`` is left at its default, the operator's configured
    ``AUREON_GRANTS_DIR`` is honoured (via :func:`aureon.grants.ledger.grants_dir`)
    because that is where the rest of the organ already looks. When ``root`` *is*
    supplied, the ledger is looked for underneath it and the environment is
    ignored — so a test that passes ``tmp_path`` cannot accidentally read the
    live pipeline.
    """
    now = now or datetime.now(UTC)
    root_path = Path(root) if root is not None else REPO_ROOT
    if grants_directory is not None:
        ledger_dir = Path(grants_directory)
    elif root is None:
        from aureon.grants.ledger import grants_dir

        ledger_dir = grants_dir()
    else:
        ledger_dir = root_path.joinpath(*GRANTS_SUBDIR)

    docs = _Docs()
    ledger_path = ledger_dir / LEDGER_NAME
    ledger_raw = docs.mapping(ledger_path, LEDGER_NAME)
    ledger = (LEDGER_NAME, ledger_raw) if ledger_raw is not None else None

    apps: tuple[Application, ...] | None = None
    if ledger_raw is not None:
        entries = ledger_raw.get("active_applications")
        if isinstance(entries, list):
            # Reuses the ledger's own parser rather than re-deriving it: mixed
            # dict/bare-string rows, non-finite amounts and lifecycle precedence
            # are already solved in schemas.Application and must have exactly one
            # implementation.
            apps = tuple(a for a in (Application.from_ledger(e) for e in entries) if a is not None)
        else:
            docs.problems.append(f"{LEDGER_NAME}: no active_applications list")

    recon_path = _newest_reconciliation(ledger_dir)
    recon: tuple[str, str] | None = None
    if recon_path is None:
        docs.problems.append(f"{RECONCILIATION_GLOB}: none found in {ledger_dir}")
    else:
        text = docs.text(recon_path, recon_path.name)
        if text is not None:
            recon = (recon_path.name, text)

    applicant_raw = docs.mapping(root_path / APPLICANT_JSON, APPLICANT_JSON)
    applicant = (APPLICANT_JSON, applicant_raw) if applicant_raw is not None else None

    # Identity is read through the existing organ, which already knows how to
    # resolve a company fact across the applicant record and COMPANY.md, carry
    # its provenance, and surface disagreement between them.
    from aureon.identity.reader import read_identity

    self_knowledge = read_identity(root_path, now=now)
    identity = self_knowledge.identity
    company_sources = (APPLICANT_JSON, COMPANY_DOC)

    recon_label = recon[0] if recon else RECONCILIATION_GLOB
    checks = (
        _identity_check("legal_entity", identity.legal_entity, company_sources),
        _identity_check("company_number", identity.company_number, company_sources),
        _identity_check("registered_office", identity.registered_office, company_sources),
        _statutory_filings_check(recon, ledger, (recon_label, LEDGER_NAME)),
        _approval_rule_check(recon, applicant, (recon_label, APPLICANT_JSON)),
        _prior_grant_check(LEDGER_NAME, apps),
        _evidence_completeness_check(LEDGER_NAME, apps),
    )

    return ComplianceReport(
        checks=checks,
        generated_at=now,
        root=str(root_path),
        ledger_path=str(ledger_path),
        sources_read=tuple(docs.read),
        problems=tuple(docs.problems),
    )


# ── routing through the Queen's switchboard ──────────────────────────────────

COMPLIANCE_GATE = Gate(
    "compliance",
    "Is this company eligible to spend effort on a bid at all?",
    min_confidence=0.0,
)


def compliance_verdict(report: ComplianceReport) -> GateVerdict:
    """The audit, expressed in the switchboard's own vocabulary.

    ADVANCE when the report is clean. Otherwise REDO — *unless* a live blocker's
    remedy is one no automatic executor exists for, in which case HOLD. The
    distinction is the switchboard's and it is not cosmetic: REDO tells the
    organism to iterate and come back, and telling it to iterate on a statutory
    filing it has no hand to make would be an instruction it can only fail.

    ``confidence`` is None throughout. No panel was convened and no field was
    read here; this verdict rests on documents, and reporting a number for it
    would be inventing one.
    """
    reading = GateReading()  # nothing was measured — every field stays None
    if report.status == PASS:
        return GateVerdict(
            COMPLIANCE_GATE.name, ADVANCE, None, reading,
            f"{report.passed_count} compliance checks pass and no blocker is live",
            [],
        )
    blockers = report.blockers
    dissent = [f"{c.name}: {c.status} — {c.detail}" for c in blockers]
    if not blockers:
        # status is FAIL with no live blocker: nothing genuinely passed.
        return GateVerdict(
            COMPLIANCE_GATE.name, REDO, None, reading,
            "no compliance check actually passed — the audit read nothing it could confirm",
            [f"{c.name}: {c.status} — {c.detail}" for c in report.checks],
        )
    held = [c for c in blockers if c.human_held]
    if held:
        return GateVerdict(
            COMPLIANCE_GATE.name, HOLD, None, reading,
            "a live compliance blocker has no automatic executor — "
            + "; ".join(c.remedy for c in held),
            dissent,
        )
    return GateVerdict(
        COMPLIANCE_GATE.name, REDO, None, reading,
        f"{report.blocking_count} live compliance blocker(s) — resolve before spending effort",
        dissent,
    )


def run_gate_chain(
    report: ComplianceReport,
    *,
    bus: Any = None,
    context: dict[str, Any] | None = None,
    chain: tuple[Gate, ...] = DEFAULT_CHAIN,
) -> list[GateVerdict]:
    """Compliance first, then the Queen's chain — and only if compliance advanced.

    Short-circuiting is the whole point of the organ: the chain reads the field,
    convenes the panel and asks the conscience, and none of that changes whether
    a confirmation statement is overdue. Spending it while a blocker is live is
    exactly the wasted effort this module exists to prevent.
    """
    verdict = compliance_verdict(report)
    _publish(bus, verdict)
    if not verdict.advanced:
        return [verdict]
    merged = dict(context or {})
    merged.setdefault("compliance", {
        "status": report.status,
        "blocking_count": report.blocking_count,
        "passed_count": report.passed_count,
        "checks": [c.name for c in report.checks if c.cleared],
    })
    return [verdict, *run_chain(merged, chain=chain, bus=bus)]


def _publish(bus: Any, verdict: GateVerdict) -> None:
    """Mirror the switchboard's own publish so the verdict trail is unbroken."""
    if bus is None:
        return
    try:
        from aureon.core.aureon_thought_bus import Thought

        bus.publish(Thought(source="grants_compliance",
                            topic=f"gates.{verdict.gate}.verdict",
                            payload=verdict.to_dict()))
    except Exception:  # noqa: BLE001
        LOG.debug("compliance verdict publish skipped", exc_info=True)


__all__ = [
    "PASS",
    "FAIL",
    "UNKNOWN",
    "COMPLIANCE_GATE",
    "ComplianceCheck",
    "ComplianceReport",
    "audit_readiness",
    "compliance_verdict",
    "run_gate_chain",
]
