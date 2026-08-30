"""The grant scout — find funding calls, and say honestly how well they fit.

:mod:`aureon.grants.ledger` reads the applications the company has *already*
made. This module looks the other way down the pipe: at calls that exist in the
world and have not been applied for. It answers two questions and refuses to
answer a third.

**Where did this come from?** Every :class:`~aureon.grants.schemas.Opportunity`
carries a ``source``, and the dataclass will not construct without one. That is
not bookkeeping — the retrieval paths available here are not equally
trustworthy, and the difference is invisible in the result:

``web_fetch``
    Real. ``AureonAgentCore.web_fetch`` is ``requests`` plus BeautifulSoup
    against the URL it was given, and it returns ``success: False`` when it
    fails. What comes back is what the page said.

``web_search``
    **Not real, and it does not tell you.** When html.duckduckgo.com returns no
    parseable results — which is what a bot-blocked scrape returns — the agent
    core falls through to ``_official_learning_search_fallback``, a hardcoded
    catalogue of twelve developer-documentation URLs (docs.python.org,
    pytest.org, the Binance and Kraken API docs …). The return value has the
    same shape as a genuine result set and carries no marker. A grant query
    against it yields whichever of those twelve pages shares the most words
    with the query, presented as a search hit. So any opportunity whose
    discovery went through search is stamped
    :data:`SOURCE_DEGRADED_SEARCH`, its degradation is repeated in the fit
    evidence, and the flag rides along in the switchboard context. Downstream
    can then discount it; nothing downstream has to know this docstring exists.

**How well does it fit?** :func:`score_fit` measures the overlap between the
retrieved call text and a capability profile read at runtime from the company's
own documents. The score is a stated ratio, not a judgement — see
:class:`~aureon.grants.schemas.FitScore` for exactly what it does and does not
mean.

**Should we pursue it?** That one is not this module's to answer, and it does
not try. :func:`assess` hands the question to
:func:`aureon.gates.switchboard.run_chain` with ``action="pursue_opportunity"``
and returns the verdicts beside the score. There is no threshold in this file,
no "if score > x then pursue" — a second decision path would be a second
opinion the Queen never asked for.

Read-only throughout. Nothing here writes to the ledger, and the sheet's rule —
*"No external submission, legal representation, filing, payment, or email send
should happen without Gary approval"* — is upheld structurally: the scout has no
submit path at all, and the chain's final gate is human-held regardless.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from aureon.grants.schemas import (
    CapabilityProfile,
    FitScore,
    Opportunity,
    OpportunityAssessment,
)

LOG = logging.getLogger("aureon.grants.scout")

# aureon/grants/scout.py -> parents[2] is the repository root.
REPO_ROOT = Path(__file__).resolve().parents[2]

# Documents the capability profile is read from. Paths only — not one word of
# what they contain is written into this file, so a repository that rewrites its
# own positioning is re-read, not overridden.
SELF_DESCRIPTION_DOCS: tuple[str, ...] = ("COMPANY.md", "docs/THE_SYNTHESIS.md")
RECONCILIATION_DOC = "data/research/grants/RECONCILIATION_20260731.md"

# Provenance stamps.
SOURCE_DEGRADED_SEARCH = "degraded_search"
SOURCE_FETCH = "web_fetch"
SOURCE_RECORD = "caller_record"

# Discovery routes that go through ``web_search`` and therefore may be the
# hardcoded catalogue wearing a search result's clothes. Matched on the
# caller's ``via`` field.
_DEGRADED_ROUTES = frozenset({"web_search", "search", "duckduckgo", SOURCE_DEGRADED_SEARCH})

# ── document reading ─────────────────────────────────────────────────────────

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
# Deliberately generic. It matches "What the company builds" in COMPANY.md and
# "What This Repository Is" in THE_SYNTHESIS.md without either title being
# written down here, so a renamed section is a re-read rather than a silent
# empty profile — and an unmatched heading yields nothing, never a guess.
_SELF_HEADING = re.compile(r"^what\b.*\b(is|are|builds?|does|do)\b", re.IGNORECASE)
_BLOCKQUOTE = re.compile(r"^\s*>\s?(.*)$")
_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_HTML_TAG = re.compile(r"<[^>]+>")
_URL = re.compile(r"https?://\S+")

# Rows in the reconciliation whose verbatim quote we need. Matched against the
# report's own labels, so the values are read rather than transcribed.
_THESIS_LABEL = re.compile(r"grant thesis", re.IGNORECASE)
_BLOCKER_LABEL = re.compile(r"compliance blocker", re.IGNORECASE)
# The separator is loose because the report writes the label two ways in two
# places — a "Claim-discipline rule" heading and a "row `Claim discipline`" line —
# and both point at the same quote. It deliberately does not match the
# coordination protocol's "Claim rule" or the checklist's "Claims control": those
# are different rules and merging them would put words in the owner's mouth.
_CLAIM_DISCIPLINE_LABEL = re.compile(r"claim[\s-]*discipline", re.IGNORECASE)


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _strip_markup(text: str) -> str:
    text = _HTML_COMMENT.sub(" ", text)
    text = _LINK.sub(r"\1", text)
    text = _HTML_TAG.sub(" ", text)
    return text.replace("**", " ").replace("`", " ")


def _self_description(text: str) -> str:
    """Lines under the first "what … is / builds" heading, to the next peer."""
    out: list[str] = []
    level: int | None = None
    for line in text.splitlines():
        match = _HEADING.match(line)
        if match:
            if level is None:
                title = re.sub(r"[^\w\s]", "", match.group(2)).strip()
                if _SELF_HEADING.search(title):
                    level = len(match.group(1))
                continue
            if len(match.group(1)) <= level:
                break
            continue
        if level is not None:
            out.append(line)
    return "\n".join(out)


def _quoted_after(text: str, label: re.Pattern[str]) -> str | None:
    """The first blockquote line following a line that names ``label``.

    The reconciliation writes each imported rule as ``row `X` — **verbatim:**``
    followed by a ``>`` quote. Reading the quote by position relative to its own
    label keeps the value verbatim and keeps this file free of it.
    """
    armed = False
    for line in text.splitlines():
        quote = _BLOCKQUOTE.match(line)
        if quote:
            if armed:
                body = quote.group(1).strip().strip('"').strip()
                if body:
                    return body
            continue
        if label.search(line):
            armed = True
        elif line.strip() and armed:
            armed = False  # the quote must follow its label, not drift to it
    return None


def _all_quoted_after(text: str, label: re.Pattern[str]) -> tuple[str, ...]:
    """Every verbatim quote whose preceding line names ``label``, in order."""
    found: list[str] = []
    armed = False
    for line in text.splitlines():
        quote = _BLOCKQUOTE.match(line)
        if quote:
            if armed:
                body = quote.group(1).strip().strip('"').strip()
                if body and body not in found:
                    found.append(body)
                armed = False
            continue
        if label.search(line):
            armed = True
        elif line.strip():
            armed = False
    return tuple(found)


# ── capability terms ─────────────────────────────────────────────────────────

# Function words and document furniture. This is a language filter, not data:
# it removes tokens that carry no capability signal in any document, so that
# "the" and "section" cannot inflate an overlap ratio. Nothing sector-specific
# is listed — removing "fintech" or "logistics" here would be editing the
# company's profile from inside the code, which is exactly what this package
# refuses to do.
_STOPWORDS = frozenset("""
about above across after again against also although always among another answer
anything around because been before being below between both cannot could does
doing done down during each either else enough even ever every everything from
further given goes going have having here hers hierarchy however into itself
just keep kept known last later least less like made make makes many more most
much must never next none nothing only onto other others ought over own past
perhaps rather same says seen shall should since some something such take taken
than that theirs them themselves then there these they thing things this those
three through thus together toward under until upon used uses using very what
whatever when where whether which while whole whom whose will with within
without would your yours
document documents detail details file files guide issue issues line lines
overview page pages paragraph paragraphs question questions readme report
reports row rows section sections source sources table tables text value values
""".split())

_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9]{2,}")
_MIN_TERM_LEN = 4


def _terms(text: str) -> set[str]:
    """Content tokens of ``text``: lowercase, >= 4 chars, no function words.

    URLs are dropped first. A link's host and path are not things the company
    said about itself, and ``github``/``docs`` matching a funder's page would be
    overlap with a citation rather than with a capability.
    """
    text = _URL.sub(" ", _strip_markup(text))
    out: set[str] = set()
    for raw in _TOKEN.findall(text):
        token = raw.lower()
        if len(token) >= _MIN_TERM_LEN and token not in _STOPWORDS and not token.isdigit():
            out.add(token)
    return out


def read_capability(root: Path | str | None = None) -> CapabilityProfile:
    """Assemble the capability profile from the repository's own documents.

    ``root`` is honoured verbatim — there is no fallback to :data:`REPO_ROOT`
    when a supplied root turns up empty. That rule is inherited from
    :func:`aureon.grants.ledger.grants_dir`, which learned it the expensive way:
    a reader that quietly reaches for the real repository when the caller's
    directory is bare will pass a test using live company data and hide the
    fault it was meant to expose.

    Three sources, each read for a different thing:

    ==========================  ===============================================
    ``COMPANY.md``              the "what the company builds" section
    ``docs/THE_SYNTHESIS.md``   the "what this repository is" section
    the reconciliation report   the grant thesis, the compliance blockers and
                                the claim-discipline rule — all verbatim
    ==========================  ===============================================

    The self-description sections are used rather than whole documents on
    purpose. Scoring against whole documents was tried and is worse than
    useless: the reconciliation report alone yields 942 distinct tokens, and
    what survives cross-document corroboration is "belfast", "july", "director",
    "ni696693" — the company's identity and the report's own furniture, not its
    capability. Those terms would match a funder's address block and register a
    fit. A narrow, high-signal profile scores lower and means something.

    The sections still carry some editorial prose, and the residue is left in
    rather than hand-pruned: a term the company will never share with a funder
    sits in the denominator and can only push the score *down*. Noise here is
    conservative. Curating it away one word at a time would be this file
    deciding what the company does, which is the thing it exists not to do.
    """
    root = Path(root) if root is not None else REPO_ROOT
    terms: set[str] = set()
    used: list[str] = []
    missing: list[str] = []

    for name in SELF_DESCRIPTION_DOCS:
        text = _read(root / name)
        if text is None:
            missing.append(name)
            continue
        section = _self_description(text)
        section_terms = _terms(section)
        if section_terms:
            terms |= section_terms
            used.append(name)
        else:
            missing.append(f"{name} (no self-description section)")

    thesis: str | None = None
    claim_discipline: str | None = None
    blockers: tuple[str, ...] = ()
    recon = _read(root / RECONCILIATION_DOC)
    if recon is None:
        missing.append(RECONCILIATION_DOC)
    else:
        thesis = _quoted_after(recon, _THESIS_LABEL)
        blockers = _all_quoted_after(recon, _BLOCKER_LABEL)
        # Read, not scored. The claim-discipline rule constrains how a narrative
        # may be *written*, so unlike the thesis it contributes no terms to the
        # profile and unlike the blocker row it changes no score. Its absence is
        # therefore not a caveat on this profile's numbers, and it is left to the
        # consumer that renders it — aureon.briefing — to record the gap as its
        # own blocker. Nothing is defaulted here: unread means None.
        claim_discipline = _quoted_after(recon, _CLAIM_DISCIPLINE_LABEL)
        if thesis:
            terms |= _terms(thesis)
            used.append(f"{RECONCILIATION_DOC} (grant thesis)")
        else:
            missing.append(f"{RECONCILIATION_DOC} (no grant thesis row)")
        # The blocker row needs the same treatment as the thesis row, and its
        # absence is the more dangerous of the two. Without this branch a
        # relabelled or reformatted row left ``compliance_blockers`` empty and
        # ``blocker`` None, so the profile reported itself complete and
        # UNBLOCKED — and score_fit then emitted no compliance line at all,
        # presenting a competitive bid as clean while the live Companies House
        # constraint had simply never been read. An unread blocker row is an
        # unknown, never a clearance.
        if blockers:
            used.append(f"{RECONCILIATION_DOC} (compliance blockers)")
        else:
            missing.append(
                f"{RECONCILIATION_DOC} (no compliance blocker row — "
                "compliance state is UNKNOWN, not clear)"
            )

    blocker: str | None = None
    if not terms:
        blocker = "no capability profile could be read; looked in: " + ", ".join(
            f"{root / n}" for n in (*SELF_DESCRIPTION_DOCS, RECONCILIATION_DOC)
        )
    elif missing:
        # A partial profile is still a real profile, but the reader must know it
        # is partial — a score computed against two thirds of the vocabulary is
        # not comparable with one computed against all of it.
        blocker = "partial profile — not read: " + "; ".join(missing)

    return CapabilityProfile(
        terms=tuple(sorted(terms)),
        sources=tuple(used),
        compliance_blockers=blockers,
        thesis=thesis,
        claim_discipline=claim_discipline,
        blocker=blocker,
    )


# ── fit scoring ──────────────────────────────────────────────────────────────

# Sentences carrying one of these read as an obligation the applicant must meet.
_REQUIREMENT_MARKERS = (
    "must ", "must be", "required", "requirement", "eligib", "mandatory",
    "applicants ", "you will need", "only open to", "restricted to",
    "in order to apply", "we expect", "criteria",
)
_SENTENCE_SPLIT = re.compile(r"(?<=[.;:!?])\s+|\n+")
# More than this and the list stops being a finding and starts being the call
# text pasted back. The cap is reported in the evidence when it bites.
_MAX_REQUIREMENTS = 8
_MIN_REQUIREMENT_TERMS = 3


def _requirement_sentences(text: str, covered: set[str]) -> tuple[list[str], int]:
    """Obligation sentences from the call whose content the profile does not cover.

    A keyword sweep, and it must be read as one. It cannot parse eligibility, it
    does not know that "SMEs based in Northern Ireland" is satisfied or not, and
    a sentence it returns is a prompt for a human to check rather than a finding
    that the company is ineligible. The alternative — an eligibility classifier
    over free-text calls — is the sort of thing that would have to invent its
    confidence, so it is not here.
    """
    out: list[str] = []
    seen: set[str] = set()
    total = 0
    for raw in _SENTENCE_SPLIT.split(text):
        sentence = re.sub(r"\s+", " ", raw).strip()
        if not sentence or len(sentence) > 400:
            continue
        low = sentence.lower()
        if not any(m in low for m in _REQUIREMENT_MARKERS):
            continue
        sentence_terms = _terms(sentence)
        if len(sentence_terms) < _MIN_REQUIREMENT_TERMS:
            continue  # a fragment, not a stated requirement
        if sentence_terms & covered:
            continue  # the profile speaks to this one
        key = low
        if key in seen:
            continue
        seen.add(key)
        total += 1
        if len(out) < _MAX_REQUIREMENTS:
            out.append(sentence)
    return out, total


def score_fit(opportunity: Opportunity, capability: CapabilityProfile) -> FitScore:
    """Measure the overlap between a retrieved call and the capability profile.

    Returns ``score = |matched terms| / |profile terms|`` — the share of what
    the company says it does that this call actually mentions.

    It returns ``None`` rather than a number in exactly two situations, and
    both are the Owner's Rule doing its job:

    * **The call text was never retrieved.** There is nothing to overlap with.
      A zero here would read as "this call wants nothing we offer", which is a
      claim about the call; the truth is a claim about us, that we did not read
      it. The blocker names the URL and the retrieval error.
    * **The profile is empty.** Dividing by nothing is not a score.

    A score of ``0.0`` is a different animal and is returned as a real value:
    the call was read, the profile exists, and they share no vocabulary.
    """
    evidence: list[str] = []

    if not capability.terms:
        return FitScore(
            score=None,
            blocker=capability.blocker or "capability profile is empty — nothing to score against",
            evidence=(f"opportunity {opportunity.id} from {opportunity.source}",),
        )

    if not opportunity.retrieved:
        why = opportunity.retrieval_error or "no call text was retrieved"
        return FitScore(
            score=None,
            blocker=f"call text not retrieved from {opportunity.url or '(no url)'}: {why}",
            evidence=(
                f"opportunity {opportunity.id} from {opportunity.source}",
                f"capability profile: {len(capability.terms)} terms from {', '.join(capability.sources) or 'nothing'}",
            ),
        )

    call_terms = _terms(opportunity.text)
    matched = tuple(sorted(t for t in capability.terms if t in call_terms))
    score = len(matched) / len(capability.terms)

    missing, total_missing = _requirement_sentences(opportunity.text, set(capability.terms))
    requirements = [f"call text: {s}" for s in missing]
    for constraint in capability.compliance_blockers:
        # A standing constraint read from the reconciliation at runtime, carried
        # verbatim with its source attached. It is not specific to this call —
        # it applies to every competitive bid — and it belongs beside the score
        # because that is where the decision gets made.
        requirements.append(f"compliance ({RECONCILIATION_DOC}): {constraint}")

    evidence.append(f"call text: {len(opportunity.text)} chars, {len(call_terms)} distinct terms")
    evidence.append(f"provenance: {opportunity.source}")
    evidence.append(
        f"capability profile: {len(capability.terms)} terms from {', '.join(capability.sources)}"
    )
    evidence.append(f"score = {len(matched)}/{len(capability.terms)} profile terms present in the call")
    if opportunity.source == SOURCE_DEGRADED_SEARCH:
        evidence.append(
            "DEGRADED: discovery went through web_search, which silently falls back to a "
            "hardcoded developer-documentation catalogue — the relevance of this URL is "
            "unverified even though the text below it is real"
        )
    if capability.blocker:
        evidence.append(f"profile caveat: {capability.blocker}")
    if total_missing > len(missing):
        evidence.append(f"{total_missing} uncovered requirement sentences found, {len(missing)} shown")

    return FitScore(
        score=score,
        matched_terms=matched,
        missing_requirements=tuple(requirements),
        blocker=None,
        evidence=tuple(evidence),
    )


# ── retrieval ────────────────────────────────────────────────────────────────

Fetcher = Callable[[str], Mapping[str, Any]]


def _registry_fetch(url: str) -> Mapping[str, Any]:
    """Default fetcher: the real ``web_fetch`` tool, through the tool registry.

    Routed through :class:`~aureon.inhouse_ai.tool_registry.ToolRegistry` rather
    than calling ``AureonAgentCore.web_fetch`` directly so that the scout uses
    the same guarded, schema-declared tool the agents do — scheme checking,
    text bounding and the search-capture audit trail come with it. The import is
    local because loading the registry pulls in the agent core, and this module
    must stay importable (and testable) with no network and no agent stack.
    """
    try:
        from aureon.inhouse_ai.tool_registry import ToolRegistry

        raw = ToolRegistry().execute("web_fetch", {"url": url})
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": f"{type(exc).__name__}: {exc}"}
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return {"success": False, "error": "web_fetch returned unparseable output"}
    return parsed if isinstance(parsed, Mapping) else {"success": False, "error": "web_fetch returned no record"}


_MONTHS = {
    m: i + 1
    for i, m in enumerate(
        "january february march april may june july august september october "
        "november december".split()
    )
}
_MONTHS.update({m[:3]: i for m, i in list(_MONTHS.items())})

_DEADLINE_WORDS = ("deadline", "closes", "closing date", "close date", "submission date",
                   "applications close", "due by", "expressions of interest close")
# Unambiguous date shapes only. ``12/08/2026`` is deliberately absent: it is
# 12 August in the UK and 8 December in the US, the calls this scout reads come
# from both, and picking one convention would manufacture a date rather than
# read one. An unparseable deadline is None, which the ledger already knows how
# to carry.
_ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_DMY_DATE = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})\.?\s+(\d{4})\b")
_MDY_DATE = re.compile(
    r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b")


def _parse_date(line: str) -> datetime | None:
    """First unambiguous calendar date in ``line``, at 00:00 UTC, or None.

    No time of day is stated by a bare date, so none is invented: the date is
    taken at its start rather than its end. That is the conservative direction —
    it can make a deadline look marginally nearer than it is, never later, and a
    deadline that looks later than it is, is the one that costs money.
    """
    iso = _ISO_DATE.search(line)
    if iso:
        try:
            return datetime(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)), tzinfo=timezone.utc)
        except ValueError:
            return None
    dmy = _DMY_DATE.search(line)
    if dmy:
        month = _MONTHS.get(dmy.group(2).lower().rstrip("."))
        if month:
            try:
                return datetime(int(dmy.group(3)), month, int(dmy.group(1)), tzinfo=timezone.utc)
            except ValueError:
                return None
    mdy = _MDY_DATE.search(line)
    if mdy:
        month = _MONTHS.get(mdy.group(1).lower().rstrip("."))
        if month:
            try:
                return datetime(int(mdy.group(3)), month, int(mdy.group(2)), tzinfo=timezone.utc)
            except ValueError:
                return None
    return None


def _extract_deadline(text: str) -> datetime | None:
    """A date is only a deadline if the call says so on the same line."""
    for line in text.splitlines():
        low = line.lower()
        if any(word in low for word in _DEADLINE_WORDS):
            found = _parse_date(line)
            if found:
                return found
    return None


# A per-award marker. Without one in the clause, an amount is not read at all:
# "A £10m fund. Awards of up to £100k per project." states both the programme
# total and the award ceiling, and a rule that took the largest number would
# report that the company could ask for £10m. Refusing the unmarked case costs a
# None and buys a number that is what it claims to be.
_AWARD_WORDS = ("up to", "maximum", "max ", "per project", "per award", "awards of",
                "grants of", "award of", "funding of up to", "value of up to")
# Clause, not line. A funder writes both figures in one paragraph and often in
# one line — the smoke case that caught this was "Awards of up to 500,000 GBP
# per project. Total fund 25m GBP.", where a line-wide scan hands back the fund.
# Sentence enders only: splitting on ":" as well would sever "Deadline:" from
# its date, and "1.5m" from its own decimal point.
_CLAUSE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")

_NUM = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
_MULT = r"k|m|bn|thousand|million|billion"
_CODE = r"GBP|EUR|USD"
# A currency marker is required, on one side or the other. Making it optional
# would let a bare integer qualify, and the first bare integer in "Deadline:
# 12 August 2026, awards up to £50k" is the year.
_AMOUNT = re.compile(
    rf"(?P<sym>[£€$])\s?(?P<num1>{_NUM})\s*(?P<mult1>{_MULT})?\b"
    rf"|\b(?P<code>{_CODE})\s?(?P<num2>{_NUM})\s*(?P<mult2>{_MULT})?\b"
    rf"|\b(?P<num3>{_NUM})\s*(?P<mult3>{_MULT})?\s*(?P<code3>{_CODE})\b",
    re.IGNORECASE,
)
_MULTIPLIERS = {"k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6, "bn": 1e9, "billion": 1e9}
# £ and € name one currency each. "$" names at least USD, CAD, AUD, NZD and SGD,
# and a grant call that writes "$" without a code has not told us which — so the
# amount is kept and the currency is left empty rather than guessed at USD.
_SYMBOL_CURRENCY = {"£": "GBP", "€": "EUR"}


def _extract_award(text: str) -> tuple[float | None, str]:
    """The largest explicitly per-award amount stated in the call, with currency.

    "Largest" only ever ranges over amounts that already carry a per-award
    marker, so it picks the ceiling among stated ceilings rather than the
    biggest number on the page.
    """
    best: float | None = None
    currency = ""
    for clause in _CLAUSE_SPLIT.split(text):
        low = clause.lower()
        if not any(word in low for word in _AWARD_WORDS):
            continue
        for match in _AMOUNT.finditer(clause):
            raw = match.group("num1") or match.group("num2") or match.group("num3")
            try:
                value = float(raw.replace(",", ""))
            except (AttributeError, ValueError):
                continue
            mult = (match.group("mult1") or match.group("mult2") or match.group("mult3") or "").lower()
            value *= _MULTIPLIERS.get(mult, 1.0)
            if best is None or value > best:
                best = value
                code = (match.group("code") or match.group("code3") or "").upper()
                currency = code or _SYMBOL_CURRENCY.get(match.group("sym") or "", "")
    return best, currency


def _first_line(text: str, limit: int = 200) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:limit]
    return ""


def _derive_id(url: str, record_id: Any) -> str:
    """The caller's id when it gave one, else a stable handle for this URL.

    The derived form is a hash, not a plausible-looking reference. An id shaped
    like ``UKRI-2026-0042`` would be a fabricated funder reference the moment
    anyone read it as one; ``OPP-<digest>`` cannot be mistaken for anything the
    funder issued.
    """
    given = str(record_id or "").strip()
    if given:
        return given
    digest = hashlib.sha1(url.encode("utf-8", errors="replace")).hexdigest()[:12]
    return f"OPP-{digest.upper()}"


def scout(
    sources: Iterable[Any],
    fetcher: Fetcher | None = None,
    *,
    now: datetime | None = None,
) -> list[Opportunity]:
    """Retrieve each source and return what was actually found.

    ``sources`` accepts a URL string or a mapping. Recognised mapping keys:

    ==============  ==============================================================
    ``url``         required; anything without one is skipped
    ``id``          the funder's own reference, when the caller has it
    ``title``       ``funder``  metadata the caller already holds
    ``via``         how this URL was discovered — ``"web_search"`` and its
                    aliases stamp the result :data:`SOURCE_DEGRADED_SEARCH`
    ==============  ==============================================================

    ``fetcher`` is injectable and defaults to :func:`_registry_fetch`, the real
    ``web_fetch`` tool. It is given a URL and must return a mapping shaped like
    that tool's result (``success``, ``text``, ``status_code``, ``error``).

    A failed retrieval still returns an Opportunity — with ``text=""`` and the
    error recorded — rather than being dropped. A call that could not be read is
    a fact about the scouting run, and silently returning a shorter list would
    turn that fact into an absence nobody can see.

    ``deadline``, ``max_award`` and ``currency`` are only ever extracted from
    retrieved text, and only where the call states them plainly enough to read
    without guessing — see :func:`_extract_deadline` and :func:`_extract_award`,
    both of which return nothing rather than something plausible. ``title``
    falls back to the first non-empty line of the retrieved page, which is a
    real line from a real document rather than a constructed label.
    """
    fetch = fetcher or _registry_fetch
    discovered_at = now or datetime.now(timezone.utc)
    found: list[Opportunity] = []

    for entry in sources:
        record: Mapping[str, Any]
        if isinstance(entry, Mapping):
            record = entry
        elif isinstance(entry, str):
            record = {"url": entry}
        else:
            LOG.debug("skipping unusable source of type %s", type(entry).__name__)
            continue

        url = str(record.get("url") or "").strip()
        if not url:
            LOG.debug("skipping source with no url: %r", record)
            continue

        via = str(record.get("via") or record.get("discovered_via") or "").strip().lower()
        degraded = via in _DEGRADED_ROUTES
        # The degraded stamp wins over the retrieval route. The fetch that
        # follows is genuine either way; what is in doubt is whether this URL
        # had any business being in the list, and that doubt originates with
        # discovery. Losing it here is how a catalogue hit becomes a grant lead.
        source = SOURCE_DEGRADED_SEARCH if degraded else f"{SOURCE_FETCH}:{url}"

        text = ""
        error: str | None = None
        status: int | None = None
        try:
            result = fetch(url)
        except Exception as exc:  # noqa: BLE001 — one bad URL must not end the run
            result = {"success": False, "error": f"{type(exc).__name__}: {exc}"}
        if isinstance(result, Mapping):
            raw_status = result.get("status_code")
            if isinstance(raw_status, int) and not isinstance(raw_status, bool):
                status = raw_status
            if result.get("success"):
                text = str(result.get("text") or "")
                if not text.strip():
                    error = "fetch succeeded but returned no text"
            else:
                error = str(result.get("error") or "fetch reported failure without a reason")
        else:
            error = f"fetcher returned {type(result).__name__}, expected a mapping"

        deadline = _extract_deadline(text) if text else None
        max_award, currency = _extract_award(text) if text else (None, "")

        found.append(
            Opportunity(
                id=_derive_id(url, record.get("id")),
                title=str(record.get("title") or "").strip() or _first_line(text),
                funder=str(record.get("funder") or "").strip(),
                url=url,
                deadline=deadline,
                max_award=max_award,
                currency=currency,
                source=source,
                discovered_at=discovered_at,
                text=text,
                retrieval_error=error,
                http_status=status,
            )
        )

    return found


# ── the decision ─────────────────────────────────────────────────────────────

PURSUE_ACTION = "pursue_opportunity"


def assess(
    opportunity: Opportunity,
    capability: CapabilityProfile | None = None,
    *,
    bus: Any = None,
    chain: Sequence[Any] | None = None,
    root: Path | str | None = None,
) -> OpportunityAssessment:
    """Score the opportunity, then let the switchboard rule on pursuing it.

    The score is passed into the chain as context and published on the bus with
    every verdict, but it is worth being explicit about what that does and does
    not achieve today: :func:`aureon.gates.switchboard.evaluate` reads only
    ``context["action"]``. The fit score therefore travels as *evidence* — into
    the verdict payloads, into whatever metacognition folds them back in — and
    not as a gate input. Nothing in this module compensates for that with a
    local threshold. Adding one would create a second decision path that
    disagreed with the switchboard sooner or later, and the switchboard is the
    one the Queen can see.

    The chain's last gate is ``submit``, which is ``requires_human`` and returns
    HOLD however strong the evidence. That is the sheet's approval rule holding
    in code: *"No external submission … should happen without Gary approval."*
    """
    from aureon.gates.switchboard import DEFAULT_CHAIN, run_chain

    profile = capability if capability is not None else read_capability(root)
    fit = score_fit(opportunity, profile)

    context = {
        "action": PURSUE_ACTION,
        "opportunity_id": opportunity.id,
        "url": opportunity.url,
        "funder": opportunity.funder,
        "source": opportunity.source,
        "degraded_discovery": opportunity.source == SOURCE_DEGRADED_SEARCH,
        "fit_score": fit.score,
        "fit_blocker": fit.blocker,
        "capability_terms": len(profile.terms),
        "compliance_blockers": list(profile.compliance_blockers),
    }
    verdicts = run_chain(context, chain=tuple(chain) if chain is not None else DEFAULT_CHAIN, bus=bus)
    return OpportunityAssessment(opportunity=opportunity, fit=fit, verdicts=tuple(verdicts))


__all__ = [
    "PURSUE_ACTION",
    "RECONCILIATION_DOC",
    "SELF_DESCRIPTION_DOCS",
    "SOURCE_DEGRADED_SEARCH",
    "SOURCE_FETCH",
    "assess",
    "read_capability",
    "score_fit",
    "scout",
]
