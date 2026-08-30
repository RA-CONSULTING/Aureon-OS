"""Read the organism's own identity out of the repository's own documents.

The company record, the charter, the README and the synthesis have always been
here; nothing in the codebase read them, so the organism could describe every
market it watches and not its own name. This module is that eye.

Design constraints, in order of importance:

- **Nothing is hardcoded.** There is not one company name, number, address or
  person in this file. Every value is read at runtime from a document under the
  supplied ``root``. Point this at an empty directory and it returns an honest
  "I do not know", not the answer it gave last time.
- **Nothing is inferred.** A field with no source is ``None`` with a blocker
  naming the files that were searched. A guess with a plausible source attached
  would be worse than silence, because it would look grounded.
- **The configured root is honoured verbatim.** Following the lesson from
  ``aureon.grants.ledger.grants_dir``: a reader that quietly falls back to the
  real repository when the caller's directory comes up empty is a reader that
  hides faults and leaks live data into tests. A missing document becomes a
  blocker, never a fallback.
- **Read-only.** This organ writes nothing, publishes nothing, and never edits
  a source document.

Sources, in the priority order used to resolve each field:

======================  ==========================================================
company facts           ``data/research/grants/autopilot_status.json`` (the
                        ``applicant`` block the grant operator files under),
                        then the company record markdown table
mission + goals         the operating-core charter's MISSION section
purpose                 README, then the synthesis, then the AI-assistant guide
======================  ==========================================================

Live deadline pressure deliberately stays out of here — that is
:mod:`aureon.grants`'s organ, and duplicating it would create a second, staler
answer to the same question.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple

from aureon.identity.schemas import MAX_CONFIDENCE, Identity, SelfKnowledge, SourcedFact

# aureon/identity/reader.py -> parents[2] is the repository root.
REPO_ROOT = Path(__file__).resolve().parents[2]

COMPANY_DOC = "COMPANY.md"
CHARTER_DOC = "AUREON_OPERATING_CORE.md"
README_DOC = "README.md"
SYNTHESIS_DOC = "docs/THE_SYNTHESIS.md"
AGENT_GUIDE_DOC = "CLAUDE.md"
APPLICANT_JSON = "data/research/grants/autopilot_status.json"

# Confidence bands. None is 1.0: see schemas.MAX_CONFIDENCE for why.
CONFIDENCE_STRUCTURED = 0.95  # a keyed value in a machine-written JSON record
CONFIDENCE_TABLE = 0.85  # a labelled cell in a markdown table
CONFIDENCE_PROSE = 0.60  # a paragraph extracted from prose

# Agreement between independent documents raises confidence a little;
# disagreement lowers it more than agreement raises it, because a contradiction
# in the record is a stronger signal than a repetition of it.
CORROBORATION_STEP = 0.05
CONFLICT_PENALTY = 0.15
MIN_CONFIDENCE = 0.10

# Which markdown table labels carry which company fact. Labels are matched
# case-insensitively against the left-hand cell of a two-column table row.
_TABLE_LABELS: dict[str, tuple[str, ...]] = {
    "legal_entity": ("registered name", "legal entity", "legal name", "company name", "registered company"),
    "company_number": ("company number", "company no", "company no.", "registered number", "registration number"),
    "registered_office": ("registered office", "registered address", "office address"),
    "lead_contact": ("director", "lead contact", "principal contact", "contact"),
}

# The JSON applicant block uses these keys directly.
_APPLICANT_KEYS = ("legal_entity", "company_number", "registered_office", "lead_contact")

# Files consulted per field, for the blocker message when nothing is found.
_LOOKED_IN: dict[str, tuple[str, ...]] = {
    "legal_entity": (APPLICANT_JSON, COMPANY_DOC),
    "company_number": (APPLICANT_JSON, COMPANY_DOC),
    "registered_office": (APPLICANT_JSON, COMPANY_DOC),
    "lead_contact": (APPLICANT_JSON, COMPANY_DOC),
    "mission": (CHARTER_DOC,),
    "purpose": (README_DOC, SYNTHESIS_DOC, AGENT_GUIDE_DOC),
}

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_NUMBERED = re.compile(r"^\s*\d+[.)]\s+(.*)$")
_BULLET = re.compile(r"^\s*[-*+]\s+")
_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_HTML_TAG = re.compile(r"<[^>]+>")
_EMPHASIS = re.compile(r"(?<!\w)\*(?!\s)([^*]+?)\*(?!\w)")
_MISSION_HEADING = re.compile(r"\bmission\b", re.IGNORECASE)
# Deliberately generic: the product name is not written into this file, so a
# repository that renames itself is still readable by the same code.
_PURPOSE_HEADING = re.compile(r"^what\b.*\bis\b", re.IGNORECASE)
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


# ── text helpers ─────────────────────────────────────────────────────────────


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _clean_inline(text: str) -> str:
    """Strip markdown decoration without altering the value itself."""
    text = _LINK.sub(r"\1", text)
    text = text.replace("**", "").replace("`", "")
    text = _EMPHASIS.sub(r"\1", text)
    text = _HTML_TAG.sub("", text)
    return _collapse(text)


def _section(text: str, pattern: re.Pattern[str]) -> list[str]:
    """Lines under the first heading matching ``pattern``, to the next peer heading."""
    out: list[str] = []
    level: int | None = None
    for line in text.splitlines():
        match = _HEADING.match(line)
        if match:
            if level is None:
                if pattern.search(match.group(2)):
                    level = len(match.group(1))
                continue
            if len(match.group(1)) <= level:
                break
            out.append(line)  # a deeper subheading belongs to this section
            continue
        if level is not None:
            out.append(line)
    return out


def _lead_paragraph(lines: list[str]) -> str:
    """The first prose paragraph, ignoring tables, quotes, HTML and code fences."""
    para: list[str] = []
    fenced = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            fenced = not fenced
            if para:
                break
            continue
        if fenced:
            continue
        if _HEADING.match(line):
            if para:
                break
            continue
        if _NUMBERED.match(line) or _BULLET.match(line):
            break
        if not stripped:
            if para:
                break
            continue
        if stripped.startswith(("|", ">", "<", "!", "$$")):
            if para:
                break
            continue
        para.append(stripped)
    return _clean_inline(" ".join(para))


def _numbered_items(lines: list[str]) -> list[str]:
    """Ordered items of the first numbered list, with wrapped lines rejoined."""
    items: list[str] = []
    for line in lines:
        match = _NUMBERED.match(line)
        if match:
            items.append(match.group(1).strip())
            continue
        stripped = line.strip()
        if not stripped:
            continue
        if items and line[:1].isspace():
            items[-1] = f"{items[-1]} {stripped}"
            continue
        if items:
            break  # unindented prose after the list ends it
    return [_clean_inline(i) for i in items if _clean_inline(i)]


def _table_pairs(text: str) -> dict[str, str]:
    """Label -> value for every two-column markdown table row in ``text``."""
    pairs: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) != 2:
            continue
        label = _clean_inline(cells[0]).lower().rstrip(":")
        value = _clean_inline(cells[1])
        if not label or not value:
            continue
        if set(value) <= set("-: ") or set(label) <= set("-: "):
            continue  # separator row
        pairs.setdefault(label, value)
    return pairs


def _normalise(value: str) -> str:
    return _NON_ALNUM.sub(" ", value.casefold()).strip()


def _agrees(a: str, b: str) -> bool:
    """True when two documents say the same thing at different specificity.

    Containment counts as agreement: a record giving the bare company number
    and one giving the number plus the register it sits on are not in conflict.
    Two genuinely different addresses are.
    """
    na, nb = _normalise(a), _normalise(b)
    if not na or not nb:
        return False
    return na == nb or na in nb or nb in na


# ── candidate resolution ─────────────────────────────────────────────────────


class _Candidate(NamedTuple):
    value: str
    source: str
    confidence: float


def _resolve(candidates: list[_Candidate], *, compare: bool) -> SourcedFact | None:
    """Pick the best-sourced value and record who agreed and who did not.

    ``compare`` is on only for atomic facts — a name, a number, an address —
    where two documents saying different things is a real contradiction worth
    flagging. It is off for prose: two paragraphs describing the same system in
    different words are not in conflict, and string comparison cannot tell the
    difference, so the runner-up paragraphs are simply not used.
    """
    if not candidates:
        return None
    # Stable sort: equal confidence keeps declaration (priority) order.
    ranked = sorted(candidates, key=lambda c: -c.confidence)
    best = ranked[0]
    if not compare:
        return SourcedFact(
            value=best.value, source_file=best.source, confidence=round(best.confidence, 3)
        )
    corroborated: list[str] = []
    conflicts: list[tuple[str, str]] = []
    for other in ranked[1:]:
        if _agrees(best.value, other.value):
            corroborated.append(other.source)
        else:
            conflicts.append((other.source, other.value))
    confidence = (
        best.confidence
        + CORROBORATION_STEP * len(corroborated)
        - CONFLICT_PENALTY * len(conflicts)
    )
    confidence = max(MIN_CONFIDENCE, min(MAX_CONFIDENCE, confidence))
    return SourcedFact(
        value=best.value,
        source_file=best.source,
        confidence=round(confidence, 3),
        corroborated_by=tuple(corroborated),
        conflicts=tuple(conflicts),
    )


# ── repository access ────────────────────────────────────────────────────────


class _Repo:
    """Guarded, cached access to documents under one root. Never raises."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.read: list[str] = []
        self.problems: list[str] = []
        self._cache: dict[str, str | None] = {}

    def text(self, relative: str) -> str | None:
        if relative in self._cache:
            return self._cache[relative]
        path = self.root / relative
        content: str | None
        if not path.is_file():
            self.problems.append(f"{relative}: not found at {path}")
            content = None
        else:
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                self.problems.append(f"{relative}: unreadable ({type(exc).__name__})")
                content = None
            else:
                if not content.strip():
                    self.problems.append(f"{relative}: empty")
                    content = None
                else:
                    self.read.append(relative)
        self._cache[relative] = content
        return content

    def mapping(self, relative: str) -> dict[str, Any] | None:
        raw = self.text(relative)
        if raw is None:
            return None
        try:
            loaded = json.loads(raw)
        except (ValueError, RecursionError) as exc:  # JSONDecodeError is a ValueError
            self.problems.append(f"{relative}: not valid JSON ({type(exc).__name__})")
            if relative in self.read:
                self.read.remove(relative)
            return None
        if not isinstance(loaded, dict):
            self.problems.append(f"{relative}: JSON root is not an object")
            return None
        return loaded


def _applicant_block(repo: _Repo) -> dict[str, str]:
    """The applicant record the grant operator files under, if it is there."""
    document = repo.mapping(APPLICANT_JSON)
    if document is None:
        return {}
    block = document.get("applicant")
    if not isinstance(block, dict):
        repo.problems.append(f"{APPLICANT_JSON}: no applicant record")
        return {}
    out: dict[str, str] = {}
    for key in _APPLICANT_KEYS:
        value = block.get(key)
        if isinstance(value, str) and value.strip():
            out[key] = _collapse(value)
    return out


def _company_table(repo: _Repo) -> dict[str, str]:
    """Company fields lifted from the company record's markdown table."""
    raw = repo.text(COMPANY_DOC)
    if raw is None:
        return {}
    pairs = _table_pairs(raw)
    out: dict[str, str] = {}
    for name, labels in _TABLE_LABELS.items():
        for label in labels:
            if label in pairs:
                out[name] = pairs[label]
                break
    return out


# ── the read ─────────────────────────────────────────────────────────────────


def read_identity(root: Path | str | None = None, *, now: datetime | None = None) -> SelfKnowledge:
    """Assemble what this repository says about itself. Never raises.

    ``root`` is honoured verbatim; it is never widened to the real repository
    when a document is missing there. Every returned fact names the file it was
    read from, and every field that could not be sourced is ``None`` with a
    blocker naming where it was looked for.
    """
    now = now or datetime.now(UTC)
    root_path = Path(root) if root is not None else REPO_ROOT
    repo = _Repo(root_path)

    applicant = _applicant_block(repo)
    company = _company_table(repo)

    candidates: dict[str, list[_Candidate]] = {name: [] for name in Identity.FIELDS}

    for name in _APPLICANT_KEYS:
        if name in applicant:
            candidates[name].append(
                _Candidate(applicant[name], APPLICANT_JSON, CONFIDENCE_STRUCTURED)
            )
        if name in company:
            candidates[name].append(_Candidate(company[name], COMPANY_DOC, CONFIDENCE_TABLE))

    # Mission and goals both come out of the charter's MISSION section.
    goals: list[SourcedFact] = []
    charter = repo.text(CHARTER_DOC)
    if charter is not None:
        section = _section(charter, _MISSION_HEADING)
        statement = _lead_paragraph(section)
        if statement:
            candidates["mission"].append(_Candidate(statement, CHARTER_DOC, CONFIDENCE_PROSE))
        for item in _numbered_items(section):
            goals.append(
                SourcedFact(value=item, source_file=CHARTER_DOC, confidence=CONFIDENCE_PROSE)
            )
        if not section:
            repo.problems.append(f"{CHARTER_DOC}: no mission section")

    for doc in (README_DOC, SYNTHESIS_DOC, AGENT_GUIDE_DOC):
        raw = repo.text(doc)
        if raw is None:
            continue
        statement = _lead_paragraph(_section(raw, _PURPOSE_HEADING))
        if statement:
            candidates["purpose"].append(_Candidate(statement, doc, CONFIDENCE_PROSE))

    identity = Identity(
        **{
            name: _resolve(found, compare=name in _APPLICANT_KEYS)
            for name, found in candidates.items()
        }
    )

    blockers = list(repo.problems)
    for name in identity.missing:
        looked = ", ".join(_LOOKED_IN[name])
        blockers.append(f"{name}: no source found (looked in {looked})")
    if not goals:
        blockers.append(f"goals: no source found (looked in {CHARTER_DOC})")

    return SelfKnowledge(
        available=identity.grounded or bool(goals),
        identity=identity,
        goals=tuple(goals),
        blockers=tuple(blockers),
        generated_at=now,
        sources_read=tuple(repo.read),
        root=str(root_path),
    )


__all__ = ["read_identity", "REPO_ROOT"]
