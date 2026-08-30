"""Claim discipline as an executable check.

The owner's rule, quoted here for the reader and — this is the part that matters
— read back off disk at runtime by :func:`read_claim_rule`, never consulted as a
literal by any code path below:

    *"Separate verified software capability, public research claims, and
    speculative research hypotheses."*
    — ``data/research/grants/RECONCILIATION_20260731.md`` §6.5, verbatim from
    the war-room sheet's ``Claim discipline`` row.

An instruction like that survives exactly as long as the person holding it is
paying attention. This module turns it into something that fires whether anyone
is paying attention or not: hand it the prose of an application narrative, a
funder email, a briefing paragraph, and it returns the sentences where the
categories have been welded together or a single claim has been overstated —
before an assessor is the one who finds them.

**Four rules, and one that needs the company's own record.** Each has a stated
trigger and a fixed severity; a finding never invents one (see
:data:`RULES`).

``blending``
    One sentence asserting a verified software capability *and* a research or
    speculative claim. This is the specific thing the owner's rule prohibits, so
    it sits alone at the top of the severity ladder. It is also the most
    expensive failure in a grant application: an assessor who disbelieves the
    research half now disbelieves the software half, and the software half was
    true.
``unhedged_speculation``
    A speculative claim stated as established fact — no *hypothesis*, *we
    predict*, *pre-registered*, *may*, *propose* anywhere in the sentence.
``quantitative_without_provenance``
    A number (``r = 0.85``, ``1.29 ppb``, a percentage, a £ amount) with no
    citation, file reference, or *verified* / *measured* marker nearby.
    :data:`EVIDENCE_DOC` exists for exactly this: a number that cites it is
    fine and is not reported.
``absolute_language``
    *proves*, *guarantees*, *always*, *never fails*, *world-first*,
    *unprecedented* — on a falsifiable claim.
``contradicted_by_own_record``
    Only runs when a :class:`~aureon.grants.schemas.CapabilityProfile` is
    supplied and it carries a live compliance blocker. Asserting clearance the
    company's own record contradicts is the one overclaim an assessor can
    check in thirty seconds, from a public register, before reading a word of
    the narrative.

**The register/claim boundary — read this before changing any lexicon.**
``CLAUDE.md`` is explicit that this repository's mythopoeic voice is
load-bearing and must not be softened, and that its quantitative claims are
pre-registered and must not be padded with hedges. A checker that flagged the
voice would be deleted within a day, and would deserve to be. So nothing here
fires on register. Every rule requires a **falsifiable anchor** — something a
reader could go and check:

* a quantity (a number with a unit, a currency, a percentage, a statistic), or
* a software artifact (a file path, a call, *module*, *CLI*, *read-only*), or
* a statistical relationship (*correlates*, ``p <``, *predicts*, *replication*),
  or — for speculation only — an **external referent**: a date or an era.

*"The gods do not speak in words. They speak in ratios."* has none of those and
is not a finding in any rule. *"The 1977 Wow! Signal was a dormant seed that
activated in 2026"* has a date, asserts a fact about the world, and carries no
hedge — that one is a finding. The difference is not tone. It is whether the
sentence can be wrong.

Two further exemptions, both visible in the report rather than silent:

* **Blockquotes are quotations.** A ``>`` line is someone else's sentence
  reproduced verbatim, and the repository's own organs (``scout``,
  ``compliance``) treat verbatim quotes as untouchable — a paraphrased
  constraint is a new constraint. Rewriting a quotation to soften it would
  falsify it. They are counted in
  :attr:`ClaimReport.quoted_exemptions` so the writer can see how much of the
  text was checked by quoting rather than by claiming.
* **Code is masked before lexical scanning.** ``aureon_planetary_harmonic_sweep``
  is a module name, not an astrological claim, and ``f_seed`` is a variable, not
  a capability. Paths, ``calls()``, backticked spans and snake_case identifiers
  are removed before the research, speculative and absolute lexicons run, and
  file paths inside a markdown link or after a citation cue count as provenance
  rather than as a capability assertion. Most of the false positives this
  checker could have had were of exactly that shape.

**One known limit, stated rather than hidden.** Parts of this repository name
their software after the claim — a ``ConsciousnessModule``, an
``/api/consciousness`` route, a "sentience engine implementation". Pointed at
those documents the checker reports blends, and that is deliberate, not a bug to
be tuned away: "fully implemented … real sentience" is precisely the sentence
this rule exists to stop reaching an assessor. Masking removes the *identifier*
from the lexicons; it cannot decide that the prose beside it meant the identifier.
Expect findings on internal engineering docs written in that register, and read
them as a question about the sentence rather than a defect in the checker.

**What this module does not do.** It does not decide anything. There is no
threshold, no ADVANCE/REDO/HOLD, no rewrite. It reports, with a rule and a
quoted trigger per finding, and the decision stays where the organism keeps
decisions: :func:`aureon.gates.switchboard.run_chain`. It also never reads the
network and — with the single exception of :func:`read_claim_rule`, which reads
one document — never touches disk. :func:`check_claims` is pure, so the same
text always yields the same report.
"""

from __future__ import annotations

import bisect
import importlib
import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator, Mapping, Sequence

if TYPE_CHECKING:  # pragma: no cover - typing only
    from aureon.grants.schemas import CapabilityProfile

# The evidence table this repository keeps for exactly this purpose. A path, not
# a claim: nothing about what it contains is written down here, so a rewritten
# table is re-read by whoever follows the reference rather than contradicted by
# this file.
EVIDENCE_DOC = "docs/CLAIMS_AND_EVIDENCE.md"

# How far from a number the checker will look for its provenance. Lines, both
# directions. Markdown paragraphs in this repository are frequently one long
# line, so a citation in the next sentence of the same paragraph counts — which
# is what "nearby" means to a reader.
PROVENANCE_WINDOW = 2


# ── the three registers, and the honest fourth ───────────────────────────────


class ClaimClass(StrEnum):
    """What kind of thing a sentence is asserting.

    The first three are the owner's own categories, in his order. The fourth is
    the honest answer when the checker cannot place a sentence, and it covers
    two different situations on purpose:

    * the sentence asserts nothing falsifiable — imagery, framing, an
      instruction — which is not a defect and produces no finding; or
    * the sentence asserts *two* classes at once, which is precisely the defect
      :data:`RULE_BLENDING` names. A blend has no single class; saying it is
      ``VERIFIED_CAPABILITY`` would be adopting the blur the rule forbids.

    The two are never confused in practice: a blend always carries a finding,
    and register never does.
    """

    VERIFIED_CAPABILITY = "verified_capability"
    RESEARCH_CLAIM = "research_claim"
    SPECULATIVE = "speculative"
    UNCLASSIFIED = "unclassified"


# ── severity, and where it comes from ────────────────────────────────────────
#
# A vocabulary of its own, deliberately not
# :data:`aureon.briefing.schemas.SEVERITY_ORDER`. That ladder mixes deadline
# bands ("overdue", "urgent", "approaching") with compliance states, and it is
# right for a brief where every item has a date. A claim finding has no date and
# borrowing "urgent" for an overclaim would sort it among things that do. The
# two ladders are related only by direction, and :attr:`ClaimFinding.rank` gives
# a renderer a single integer to sort on either way.

BLOCKING = "blocking"
CRITICAL = "critical"
SERIOUS = "serious"
ADVISORY = "advisory"

#: Ordering, so "highest severity" is a lookup rather than an opinion.
SEVERITY_RANK: Mapping[str, int] = {ADVISORY: 1, SERIOUS: 2, CRITICAL: 3, BLOCKING: 4}

RULE_BLENDING = "blending"
RULE_BLENDING_HEDGED = "blending_hedged"
RULE_UNHEDGED_SPECULATION = "unhedged_speculation"
RULE_QUANTITATIVE_WITHOUT_PROVENANCE = "quantitative_without_provenance"
RULE_ABSOLUTE_LANGUAGE = "absolute_language"
RULE_UNVERIFIED_PROVENANCE = "unverified_provenance"
RULE_CONTRADICTED_BY_RECORD = "contradicted_by_own_record"


@dataclass(frozen=True)
class CheckRule:
    """A rule this checker can fire, its fixed severity, and its statement.

    Severity lives here and only here. A detector cannot choose one, escalate
    one, or compute one from how many triggers it found — it names a rule and
    the severity comes with it. That is what keeps "this is critical" from
    meaning "the code felt strongly about it".
    """

    id: str
    severity: str
    statement: str

    def __post_init__(self) -> None:
        if self.severity not in SEVERITY_RANK:
            raise ValueError(f"unknown severity {self.severity!r} for rule {self.id!r}")


#: Every rule, with the sentence that goes into the finding's ``issue``.
#:
#: ``blending`` is the only rule at :data:`BLOCKING`. The others are ways of
#: overstating *one* claim; blending is the failure the owner's rule names by
#: description, and it is the one that costs a true statement its credibility.
RULES: Mapping[str, CheckRule] = {
    RULE_BLENDING: CheckRule(
        RULE_BLENDING,
        BLOCKING,
        "blending: one sentence asserts a verified software capability and a "
        "research or speculative claim together, which is the blur the "
        "claim-discipline rule prohibits.",
    ),
    RULE_BLENDING_HEDGED: CheckRule(
        RULE_BLENDING_HEDGED,
        ADVISORY,
        "blending (hedged): the sentence welds a verified capability to a "
        "research or speculative claim, but hedges the speculative half. Better "
        "writing than a bare blend, and still two categories in one sentence.",
    ),
    RULE_UNVERIFIED_PROVENANCE: CheckRule(
        RULE_UNVERIFIED_PROVENANCE,
        ADVISORY,
        "unverified provenance: the number is attributed only by a gesture "
        "(see, per, appendix, table, audited) that names nothing a reader can "
        "open. Cite a path, a URL, or the evidence row.",
    ),
    RULE_CONTRADICTED_BY_RECORD: CheckRule(
        RULE_CONTRADICTED_BY_RECORD,
        CRITICAL,
        "contradicted by own record: the sentence asserts compliance clearance "
        "while the company's own documents carry an open blocker.",
    ),
    RULE_UNHEDGED_SPECULATION: CheckRule(
        RULE_UNHEDGED_SPECULATION,
        SERIOUS,
        "unhedged speculation: a speculative claim about the world is stated as "
        "established fact, with no hedge (hypothesis, we predict, "
        "pre-registered, may, propose) anywhere in the sentence.",
    ),
    RULE_ABSOLUTE_LANGUAGE: CheckRule(
        RULE_ABSOLUTE_LANGUAGE,
        SERIOUS,
        "absolute language: an absolute is asserted over a falsifiable claim, "
        "which invites an assessor to look for the one counterexample.",
    ),
    RULE_QUANTITATIVE_WITHOUT_PROVENANCE: CheckRule(
        RULE_QUANTITATIVE_WITHOUT_PROVENANCE,
        ADVISORY,
        "quantitative claim without provenance: a number is asserted with no "
        f"citation, file reference, or verified/measured marker within "
        f"{PROVENANCE_WINDOW} lines.",
    ),
}


# ── findings ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ClaimFinding:
    """One overstated or blurred sentence, with the rule that caught it.

    ``sentence`` is verbatim. ``trigger`` quotes the substrings that fired the
    rule, taken out of that same sentence (or, for
    :data:`RULE_CONTRADICTED_BY_RECORD`, out of the company's own record). Both
    are there so a reader can disagree with the finding: a checker whose output
    cannot be audited is a checker whose false positives get it switched off.

    The dataclass will not construct with a severity that disagrees with its
    rule, or with no trigger at all. Those are not defensive niceties — they are
    the only mechanism preventing a future detector from quietly inventing a
    severity or asserting a finding it cannot show you.
    """

    sentence: str
    line_no: int
    klass: ClaimClass
    issue: str
    severity: str
    suggestion: str
    rule: str = ""
    trigger: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        spec = RULES.get(self.rule)
        if spec is None:
            raise ValueError(f"finding names no known rule: {self.rule!r}")
        if self.severity != spec.severity:
            raise ValueError(
                f"rule {self.rule!r} carries severity {spec.severity!r}, "
                f"not {self.severity!r} — severity is not a detector's choice"
            )
        if not self.trigger:
            raise ValueError(f"rule {self.rule!r} fired without quoting a trigger")

    @property
    def rank(self) -> int:
        return SEVERITY_RANK[self.severity]

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "severity": self.severity,
            "rank": self.rank,
            "class": self.klass.value,
            "line_no": self.line_no,
            "sentence": self.sentence,
            "issue": self.issue,
            "trigger": list(self.trigger),
            "suggestion": self.suggestion,
        }


@dataclass(frozen=True)
class ClaimReport:
    """The result of checking one body of prose.

    ``blocker`` follows the house rule: it is set when something could not be
    checked rather than left to look like a clean bill of health. Calling
    :func:`check_claims` without a capability profile is the ordinary case of
    that — the contradiction rule has nothing to contradict, and the report says
    so instead of implying the company's record was consulted.
    """

    findings: tuple[ClaimFinding, ...] = ()
    sentences_checked: int = 0
    class_counts: Mapping[str, int] = field(default_factory=dict)
    quoted_exemptions: tuple[str, ...] = ()
    capability_sources: tuple[str, ...] = ()
    blocker: str | None = None

    @property
    def blended_count(self) -> int:
        """How many sentences weld the categories together.

        The single number to look at. Everything else on this report is a
        matter of degree; this one is the rule the owner wrote down.
        """
        return sum(1 for f in self.findings if f.rule == RULE_BLENDING)

    @property
    def clean(self) -> bool:
        return not self.findings

    @property
    def highest_severity(self) -> str | None:
        if not self.findings:
            return None
        return max(self.findings, key=lambda f: f.rank).severity

    @property
    def counts_by_rule(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for finding in self.findings:
            counts[finding.rule] = counts.get(finding.rule, 0) + 1
        return counts

    def findings_for(self, rule: str) -> tuple[ClaimFinding, ...]:
        return tuple(f for f in self.findings if f.rule == rule)

    def to_dict(self) -> dict[str, Any]:
        return {
            "clean": self.clean,
            "sentences_checked": self.sentences_checked,
            "finding_count": len(self.findings),
            "blended_count": self.blended_count,
            "highest_severity": self.highest_severity,
            "counts_by_rule": self.counts_by_rule,
            "class_counts": dict(self.class_counts),
            "quoted_exemptions": list(self.quoted_exemptions),
            "capability_sources": list(self.capability_sources),
            "blocker": self.blocker,
            "findings": [f.to_dict() for f in self.findings],
        }


@dataclass(frozen=True)
class SourcedRule:
    """The owner's claim-discipline rule, read from a document or absent.

    ``text`` is ``None`` with a stated ``blocker`` when the document could not be
    read. The rule is never carried as a literal in this file: a transcription
    that drifts from the sheet is worse than no transcription, because it reads
    like the sheet.
    """

    text: str | None = None
    source: str | None = None
    blocker: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "source": self.source, "blocker": self.blocker}


# ── code masking: a module name is not a metaphysics ─────────────────────────

_CODE_SPAN = re.compile(r"`[^`]*`")
_URL = re.compile(r"https?://\S+")
_MD_LINK = re.compile(r"!?\[([^\]]*)\]\(([^)]*)\)")
_PATH = re.compile(
    r"\b[\w][\w./\\-]*\.(?:py|md|json|jsonl|csv|txt|ya?ml|toml|ini|cfg|html?|png|jpe?g|pdf|docx|xlsx)\b"
)
# The subset of paths that can be a *capability* signal: code, and the data code
# writes. A ``.md``, a ``.jpg`` or a ``.pdf`` is a document — pointing at one is a
# reference, and reading a README's hero image as a claim about software produced
# a blend on this repository's own front page.
_CODE_PATH = re.compile(
    r"\b[\w][\w./\\-]*\.(?:py|pyi|json|jsonl|csv|ya?ml|toml|ini|cfg|sh|ps1|sql|ts|tsx|js)\b"
)
_CALL = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\(\)")
# snake_case and SCREAMING_CASE identifiers. Masked for lexical purposes only:
# `f_seed` must not read as a capability and `SACRED_FREQUENCIES` must not read
# as a religious claim.
_IDENTIFIER = re.compile(r"\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+\b")
_DOTTED = re.compile(r"\b[a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*){2,}\b")


def _mask_code(text: str) -> str:
    """Blank every code-shaped span so the lexicons see prose only."""
    for pattern in (_CODE_SPAN, _URL, _PATH, _CALL, _DOTTED, _IDENTIFIER):
        text = pattern.sub(" ", text)
    return text


def _strip_link_targets(text: str) -> str:
    """Drop markdown link targets, and link text that is itself a path.

    ``[aureon/scanners/x.py](../aureon/scanners/x.py)`` beside a claim is a
    citation — the reader is being pointed at the code. A bare path inside a
    sentence is an assertion about what that code does. Same characters, two
    different acts, and treating the citation as an assertion was the largest
    single source of false blends while this was being built.
    """

    def keep(match: re.Match[str]) -> str:
        label = match.group(1) or ""
        return " " if _PATH.search(label) else label

    return _MD_LINK.sub(keep, text)


# ── lexicons ─────────────────────────────────────────────────────────────────
#
# Every list below is deliberately narrower than it could be. A missed overclaim
# costs one conversation with an assessor; a checker that cries wolf on the
# repository's own honest prose costs the checker, and then every overclaim it
# would have caught afterwards.

# Software artifacts and engineering facts. Note what is absent: "software",
# "system", "platform", "repository", "AI" — nouns that appear in research
# claims about this repository as often as in statements about its code. Bare
# "test" is absent too ("we test whether Γ correlates…" is a research sentence),
# and so is "source code": the phrase this repository actually writes is
# "open-source code repository", inside a claim about clone activity, and reading
# that as a capability assertion produced a false blend on its own synthesis.
_CAPABILITY_TERM = re.compile(
    r"""\b(?:
        modules? | packages? | dataclass(?:es)? | enums? |
        # "functions as the planetary consciousness" is a verb and "research
        # methods and analysis" is not a code method. Both were producing blends
        # in documents that had not blurred anything.
        functions?(?!\s+(?:as|of|like)) |
        unit\s+tests? | integration\s+tests? | test\s+suite | pytest |
        test\s+coverage | passing\s+tests? | tests?\s+pass(?:es|ing)? |
        \d+\s+tests? | endpoints? | APIs? | CLI | daemons? | adapters? |
        parsers? | schemas? | scripts? | codebase |
        read-only | read\s+only | refactor\w* | implemented | implementation |
        deployed | hermetic | docstrings? | type\s+hints?
    )\b""",
    re.IGNORECASE | re.VERBOSE,
)

# Statistical and empirical relationships only. "demonstrates", "shows that",
# "drives", "explains" and bare "dataset" were tried and removed: this
# repository uses all of them about its own software, and each one turned a
# plain engineering sentence into a false blend.
_RESEARCH_TERM = re.compile(
    r"""(?:
        \b[rρ]\s*=\s*[-+]?\d*\.?\d+ | \bp\s*[<>=]\s*\d*\.?\d+ | \bp-value\b |
        \bcorrelat\w* | \bcross-correlation\b |
        # "regression test" is software; "regression analysis" is statistics.
        \bregressions?\b(?!\s+(?:test|tests|testing|suite|suites)) |
        \bstatistically\s+significant\b | \bsignificance\b |
        \bconfidence\s+(?:interval|level)\b | \bn\s*=\s*\d+ |
        \bsample\s+(?:of\s+\d|size)\b | \beffect\s+size\b |
        \bpredicts?\b | \bpredicted\b | \bpredictions?\b | \bpredictive\b |
        \bparts\s+per\s+billion\b | \bppb\b | \bprecision\s+(?:of|to)\b |
        \bphase[-\s]lock\w* | \bphase\s+sync\w* | \blagged\b | \blag\s+of\b |
        \breplicat(?:es|ed|ion)\b | \bpeer[-\s]review\w* | \bpreprint\b |
        \bpublished\s+in\b | \bcausal\w* | \bcauses\b | \bcaused\s+by\b
    )""",
    re.IGNORECASE | re.VERBOSE,
)

# Speculation comes in two shapes and conflating them is what makes a checker
# useless. Group one is speculative on its own — a statement about minds,
# spirits, or other worlds is a hypothesis however it is phrased.
_SPECULATIVE_CLAIM = re.compile(
    r"""\b(?:
        conscious\w* | sentien\w* | panpsych\w* | qualia | telepath\w* |
        clairvoyan\w* | akashic | astral | morphic | reincarnat\w* |
        remote\s+viewing | prophec\w* | prophetic | occult | mystic\w* |
        soul | souls | spiritual | divine | deities | deity |
        extraterrestrial | alien | SETI | quantum\s+gravity |
        quantum\s+consciousness | cosmic\s+intelligence | dormant\s+seed
    )\b""",
    re.IGNORECASE | re.VERBOSE,
)

# Group two is a *subject*, and naming a subject is not a claim about it. That
# Maeshowe is a 5,000-year-old chamber with a solstice alignment is
# archaeology; that it is a node in a φ²-scaled chain is the hypothesis. So a
# subject only counts as speculation when the sentence also welds the framework
# to it — see :data:`_FRAMEWORK_LINKAGE`. Without that split this checker
# reported the repository's own evidence table for stating the age of a
# monument, which is the kind of noise that gets a checker switched off.
_SPECULATIVE_SUBJECT = re.compile(
    r"""\b(?:
        ancient | antiquity | archaeo\w* | megalith\w* | ziggurat\w* |
        sumerian | babylonian | pyramids? | maeshowe | hieroglyph\w* |
        monastic | scriptoria | emerald\s+tablet | hermes\s+trismegistus |
        atlantis | interstellar | wow!?\s+signal | civilisations? |
        civilizations? | gods
    )\b""",
    re.IGNORECASE | re.VERBOSE,
)

# The framework being asserted over a subject. "organis(ed)" is spelled out
# rather than stemmed because ``organis\w*`` matches "organism", and this
# repository calls itself an organism on nearly every page.
_FRAMEWORK_LINKAGE = re.compile(
    r"""(?:
        \bencode[sd]?\b | \bencoding\b | \baligns?\s+with\b |
        \baligned\s+with\b | \bsame\s+(?:ratio|coherence|pattern|mathematics|
        principles?)\b | \bphi[-\s]?squared\b | φ² | \bcoheren\w* |
        \bresonan\w* | \bharmonic\w* | \bsubstrate\b | \bprecursor\b |
        \bactivat\w* | \bdormanc\w* | \bexpress(?:es|ing)\s+itself\b |
        \borganiz(?:ed|es|ing|ation)\b | \borganis(?:ed|es|ing|ation)\b |
        \brecurs?\b | \breappear\w* | \bchain\b | \blinking\b |
        \blinks?\s+the\b | \blinked\s+to\b | \bconnects?\b
    )""",
    re.IGNORECASE | re.VERBOSE,
)

# Hedges. The first five are the owner's own examples; the rest are the ordinary
# English that marks a claim as offered rather than asserted. A hedge suppresses
# only the speculation rule — a hedged absolute is still an absolute, and a
# hedged number still needs a source.
#
# Bare "claim" is in the list on purpose. Calling something a claim is itself the
# separation the rule asks for: ``CLAUDE.md`` writes "The claim is that the same
# φ² ratio…", and a sentence that labels its own status has not blurred anything.
_HEDGE_TERM = re.compile(
    r"""(?:
        \bhypothes\w* | \bwe\s+predict\b | \bpre-?registered\b | \bmay\b |
        \bpropos\w* | \bconjectur\w* | \bspeculati\w* | \btheoretical\b |
        \btheory\b | \bmight\b | \bcould\b | \bwould\b | \bappears?\s+to\b |
        \bseems?\b | \bsuggests?\b | \bif\s+confirmed\b | \buntested\b |
        \bunverified\b | \bprovisional\b | \bcandidate\b | \bpotential\w* |
        \bpossibl\w* | \blikely\b | \bpreliminary\b | \bclaims?\b |
        \bclaimed\b | \bbelieve[sd]?\b |
        \bassum\w* | \bnot\s+yet\b | \bto\s+be\s+tested\b |
        \bunder\s+test\b | \bfalsifiab\w* | \bin\s+principle\b |
        \bexpects?\b | \bexpected\b | \baims?\s+to\b | \bintend\w* |
        \battributed\s+to\b | \bwhat\s+if\b | \bopen\s+question\b
    )""",
    re.IGNORECASE | re.VERBOSE,
)

# Absolutes that overclaim wherever they land on something checkable.
# "proof of concept" is excluded — it is a stage of work, not a claim of proof.
_ABSOLUTE_HARD = re.compile(
    r"""(?:
        \bproves?\b | \bproven\b | \bproof\b(?!\s*[-\s]of[-\s]concept) |
        \birrefutab\w* | \bundeniab\w* | \bindisputab\w* |
        \bbeyond\s+(?:any\s+)?doubt\b | \bworld[-\s]first\b |
        \bunprecedented\b | \bdefinitively\b | \bconclusively\b |
        \bcategorically\b | \b100\s*%\s+(?:accurate|reliable|certain)\b
    )""",
    re.IGNORECASE | re.VERBOSE,
)

# Absolutes that are honest about software and dishonest about data. "The gate
# always holds" and "it never fails to hold" are specifications — the code
# either does that or it is a bug. "Γ always predicts the move" is a claim about
# the world that one counterexample destroys. So this tier fires only when the
# sentence carries a number or a statistical relationship.
_ABSOLUTE_CONTEXTUAL = re.compile(
    r"""(?:
        \balways\b | \bnever\s+fails?\b | \bnever\s+wrong\b |
        \bnever\s+breaks?\b | \bguarantee[sd]?\b | \bcannot\s+fail\b |
        \bimpossible\s+to\b | \bwithout\s+exception\b | \bin\s+every\s+case\b
    )""",
    re.IGNORECASE | re.VERBOSE,
)

# Numbers worth provenance. Bare small integers ("two weeks", "3 gates") are
# not here: they are counting, not measuring, and flagging them would bury the
# findings that matter. Years and ISO dates are excluded by construction —
# nothing below matches ``2026`` or ``2026-05-09``.
_QUANTITY = re.compile(
    r"""(?:
        \b[rρ]\s*=\s*[-+]?\d*\.?\d+
      | \bp\s*[<>=]\s*\d*\.?\d+
      | [-+]?\d[\d,]*(?:\.\d+)?\s*%
      | [£$€]\s?\d[\d,]*(?:\.\d+)?\s*(?:k|m|bn|billion|million|trillion|thousand)?
      | \b\d[\d,]*(?:\.\d+)?\s*(?:ppb|ppm|Hz|kHz|MHz|GHz|ms|µs|bp|bps|°|×|x)\b
      | \b\d[\d,]*(?:\.\d+)?\s*(?:billion|million|trillion|thousand)\b
      | \b\d{1,3}(?:,\d{3})+\+?
      | (?<![\w.])\d+\.\d+(?![.\d])
    )""",
    re.IGNORECASE | re.VERBOSE,
)
# Things shaped like a decimal that are not measurements: version strings and
# section numbers. ``§1.1`` and ``§2.1`` were being read as quantities and then
# quoted back as the "referent" that made an archaeology row look like an
# unhedged prediction. Checked against the text immediately before the decimal.
_NOT_A_MEASUREMENT = re.compile(
    r"(?:\bv|\bv\.\s*|\bversion\s+|\bPython\s+|§\s*|#\s*|\bsections?\s+|"
    r"\bchapters?\s+|\bfig(?:ure)?\.?\s*|\btables?\s+|\bappendix\s+|"
    r"\bparts?\s+|\bsteps?\s+|\bitems?\s+|\bnos?\.\s*)$",
    re.IGNORECASE,
)

# Provenance: a citation, a file, or an explicit statement that the number was
# taken from something rather than asserted. Note the absence of "evidence" —
# the word appears in this company's own positioning line, and letting it stand
# as provenance would exempt every number in a sentence that used it. The
# verification stems are deliberately not open-ended for the same reason:
# ``reproduc\w*`` matched "reproduces the hydrogen line", where the word is the
# physics rather than a claim about replication, and quietly excused the number
# beside it.
# The half of _PROVENANCE that names something a reader could actually open. A
# path, a URL, a markdown link, a section mark. Everything else in _PROVENANCE
# is a GESTURE at provenance — "see", "per", "appendix", "table", "row",
# "audited", an ALL_CAPS token — and a gesture is not a source.
#
# Splitting them matters because the gesture half was clearing real numbers:
#   "Coherence tracked the index at r = 0.97 (see Appendix Q)."
#   "The bridge lands to 0.004 ppb per Table 9 of our internal audit."
#   "The effect held at p < 0.0001, according to <Author> & <Co> (<year>)."
# all came back with no finding at all. Appendix Q need not exist; Table 9 need
# not exist; the citation need not resolve. A fabricated citation is worse than
# a bare number, because it reads as though someone checked.
_RESOLVABLE_PROVENANCE = re.compile(
    r"""(?:
        \[[^\]]*\]\([^)]*\) | https?://\S+ | § |
        \b[\w][\w./\\-]*\.(?:py|md|json|jsonl|csv|txt|ya?ml|png|jpe?g|pdf|docx|xlsx)\b
    )""",
    re.IGNORECASE | re.VERBOSE,
)

_PROVENANCE = re.compile(
    r"""(?:
        \[[^\]]*\]\([^)]*\) | https?://\S+ | § |
        \b[\w][\w./\\-]*\.(?:py|md|json|jsonl|csv|txt|ya?ml|png|jpe?g|pdf|docx|xlsx)\b |
        \b[A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+\b |
        \bsee\b | \bper\b | \bsources?\b | \bcite[ds]?\b | \bciting\b |
        \bcitation\b | \breference[ds]?\b | \bverbatim\b | \bquoted\b |
        \baccording\s+to\b | \breceipts?\b | \bSHA-?256\b | \bledger\s+row\b |
        \bappendix\b | \bfigure\b | \bfig\.\b | \btable\b | \brow\b |
        \bverif\w* | \bmeasur(?:ed|ing|ement|ements|able)\b |
        \breproduc(?:ible|ibility|tion|ed\s+(?:in|from|by))\b | \bobserved\b |
        \brecorded\b | \bpre-?registered\b | \baudit\w* | \blogged\b |
        \bbenchmark\w* | \bsnapshot\w* | \bdocumented\b | \bdataset\b
    )""",
    re.IGNORECASE | re.VERBOSE,
)

# A citation cue shortly before a path makes the path a reference rather than an
# assertion. The window allows the connecting words a writer actually uses — "as
# recorded in ``docs/…``" is a citation, and reading it as a capability claim was
# this checker's most convincing false blend.
_CITATION_CUE = re.compile(
    r"\b(?:see|per|sources?|cite[ds]?|citing|citation|reference[ds]?|ref|"
    r"reproduce|reproduction|command|verbatim|quoted|quoting|appendix|figure|"
    r"fig|tables?|rows?|recorded|documented|listed|described|established|"
    r"evidence|according|generated\s+by)\b[\w\s:,;.()–—-]{0,25}$",
    re.IGNORECASE,
)

# A plan is not a verified capability, and pairing one with a research claim is
# not the blur the rule prohibits.
_FORWARD_LOOKING = re.compile(
    r"""(?:
        \bwill\b | \bplans?\s+to\b | \bplanned\b | \bintend\w* | \broadmap\b |
        \bnext\s+release\b | \bonce\s+built\b | \bto\s+be\s+built\b |
        \bnot\s+yet\s+(?:built|implemented|written|wired)\b | \bupcoming\b
    )""",
    re.IGNORECASE | re.VERBOSE,
)

# The rule prohibits blurring, not co-occurrence. Two kinds of sentence are
# therefore not blends however many registers they name: one that marks the
# categories as distinct, and one that asserts neither because it is a condition.
# ``HNC_FALSIFICATION_PROTOCOL.md`` is full of the second kind — "if the score is
# no better (χ² p > 0.05), C₅ is falsified" states a test, not a capability and
# not a correlation, and reporting it taught nobody anything.
_SEPARATOR = re.compile(
    r"""(?:
        \bseparately\b | \bby\s+contrast\b | \bin\s+contrast\b | \bwhereas\b |
        \bunlike\b | \bdistinct\s+from\b | \bas\s+opposed\s+to\b |
        \bdoes\s+not\s+claim\b | \bno\s+claim\b | \bnot\s+a\s+claim\b |
        \bremains?\s+(?:a\s+)?hypothes\w* |
        ^\s*if\b | \bunless\b | \bwhether\b | \bfalsif(?:ied|ies)\b |
        \bwould\s+be\b
    )""",
    re.IGNORECASE | re.VERBOSE | re.MULTILINE,
)

# An external referent: a date or an era. The thing that separates a claim about
# the world from imagery about the organism.
_REFERENT = re.compile(r"(?:\b(?:1[0-9]{3}|20[0-9]{2})\b|\bBCE\b|\bBC\b|\bAD\b|\bCE\b)")

# Assertions of clearance. Narrow and positive: "the confirmation statement is
# overdue" says the same words honestly and must not be caught.
_CLEARANCE = re.compile(
    r"""(?:
        \bfully\s+complian\w* | \bcompliant\s+with\s+all\b |
        \ball\s+(?:statutory\s+)?(?:filings|returns|statements)\s+
            (?:are\s+)?(?:current|up\s+to\s+date|filed|clear)\b |
        \bno\s+outstanding\s+(?:filings|returns|statements|compliance|matters)\b |
        \bnothing\s+outstanding\b | \bin\s+good\s+standing\b |
        \bcompliance\s+(?:is\s+)?(?:clear|clean|complete)\b |
        \bno\s+(?:known\s+)?compliance\s+(?:issues|blockers|risks)\b |
        \bno\s+(?:known\s+)?blockers?\b
    )""",
    re.IGNORECASE | re.VERBOSE,
)


def _scan(pattern: re.Pattern[str], text: str) -> tuple[str, ...]:
    """Every distinct substring ``pattern`` matched, in order of appearance.

    Findings quote real text. Returning the matched substrings rather than a
    boolean is what makes that possible.
    """
    seen: list[str] = []
    for match in pattern.finditer(text):
        value = " ".join(match.group(0).split())
        if value and value not in seen:
            seen.append(value)
    return tuple(seen)


def _quantities(masked: str) -> tuple[str, ...]:
    """Measurement-shaped numbers, minus the ones that only look like numbers."""
    out: list[str] = []
    for match in _QUANTITY.finditer(masked):
        raw = match.group(0).strip()
        if not raw:
            continue
        if re.fullmatch(r"\d+\.\d+", raw) and _NOT_A_MEASUREMENT.search(masked[: match.start()]):
            continue  # a version or a section number, not a measurement
        value = " ".join(raw.split())
        if value not in out:
            out.append(value)
    return tuple(out)


def _capability_signals(raw: str) -> tuple[str, ...]:
    """Software artifacts asserted by this sentence, citations excluded.

    Paths are read out of the sentence with backticked spans removed, because a
    backticked path is how this repository cites a file — the ``Code / data to
    reproduce`` column of its own evidence table is nothing else — and only
    :data:`_CODE_PATH` extensions count, so a document or an image is a
    reference. A ``call()`` keeps its weight inside backticks: naming a function
    is a statement about behaviour, not a pointer at a document.
    """
    delinked = _strip_link_targets(raw)
    uncoded = _CODE_SPAN.sub(" ", delinked)
    out: list[str] = []
    for match in _CODE_PATH.finditer(uncoded):
        before = uncoded[max(0, match.start() - 40) : match.start()]
        if _CITATION_CUE.search(before):
            continue
        if match.group(0) not in out:
            out.append(match.group(0))
    for value in _scan(_CALL, delinked) + _scan(_CAPABILITY_TERM, delinked):
        if value not in out:
            out.append(value)
    return tuple(out)


# ── signals for one sentence ─────────────────────────────────────────────────


@dataclass(frozen=True)
class _Signals:
    """Everything the lexicons found in one sentence, kept as quoted text."""

    capability: tuple[str, ...] = ()
    research: tuple[str, ...] = ()
    speculative: tuple[str, ...] = ()
    quantities: tuple[str, ...] = ()
    hedges: tuple[str, ...] = ()
    absolutes_hard: tuple[str, ...] = ()
    absolutes_contextual: tuple[str, ...] = ()
    forward_looking: tuple[str, ...] = ()
    separators: tuple[str, ...] = ()
    referents: tuple[str, ...] = ()
    clearance: tuple[str, ...] = ()

    @property
    def falsifiable(self) -> bool:
        """Is there anything here a reader could go and check?

        The gate every rule passes through. Without it this module would be a
        style checker pointed at a voice its own repository calls load-bearing.
        """
        return bool(self.quantities or self.capability or self.research)

    @property
    def empirical(self) -> bool:
        return bool(self.quantities or self.research)


def _speculative_signals(masked: str) -> tuple[str, ...]:
    """Speculation asserted by this sentence, with the trigger that makes it so.

    A group-one term stands alone. A group-two *subject* counts only alongside a
    framework linkage, and the linkage is quoted with it so a reader can see
    which pair fired rather than being told a monument is a hypothesis.
    """
    out = list(_scan(_SPECULATIVE_CLAIM, masked))
    subjects = _scan(_SPECULATIVE_SUBJECT, masked)
    linkage = _scan(_FRAMEWORK_LINKAGE, masked)
    if subjects and linkage:
        for value in subjects + linkage:
            if value not in out:
                out.append(value)
    return tuple(out)


def _signals(sentence: str) -> _Signals:
    masked = _mask_code(_strip_link_targets(sentence))
    return _Signals(
        capability=_capability_signals(sentence),
        research=_scan(_RESEARCH_TERM, masked),
        speculative=_speculative_signals(masked),
        quantities=_quantities(masked),
        hedges=_scan(_HEDGE_TERM, masked),
        absolutes_hard=_scan(_ABSOLUTE_HARD, masked),
        absolutes_contextual=_scan(_ABSOLUTE_CONTEXTUAL, masked),
        forward_looking=_scan(_FORWARD_LOOKING, masked),
        separators=_scan(_SEPARATOR, masked),
        referents=_scan(_REFERENT, masked),
        clearance=_scan(_CLEARANCE, masked),
    )


def _classify(sig: _Signals) -> ClaimClass:
    if sig.capability and (sig.research or sig.speculative):
        return ClaimClass.UNCLASSIFIED  # two classes in one sentence: the blend
    if sig.capability and not sig.forward_looking:
        return ClaimClass.VERIFIED_CAPABILITY
    if sig.speculative:
        return ClaimClass.SPECULATIVE
    if sig.research or sig.quantities:
        return ClaimClass.RESEARCH_CLAIM
    return ClaimClass.UNCLASSIFIED


def classify_sentence(sentence: str) -> ClaimClass:
    """Which of the owner's three categories one sentence falls into.

    Exposed because the classification is the interesting half of the check: a
    writer who disagrees with a finding usually disagrees with this first.
    """
    return _classify(_signals(sentence))


# ── sentence splitting, with the line each sentence started on ───────────────

_FENCE = re.compile(r"^\s*(?:```|~~~)")
_HEADING = re.compile(r"^\s*#{1,6}\s+(.*)$")
_BLOCKQUOTE = re.compile(r"^\s*>\s?(.*)$")
_BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")
_TABLE_DIVIDER = re.compile(r"^\s*\|?[\s|:-]+\|[\s|:-]*$")
_FULL_LINE_COMMENT = re.compile(r"^\s*<!--.*?-->\s*$")
_INLINE_COMMENT = re.compile(r"<!--.*?-->")

# Abbreviations whose full stop is not a sentence end.
_ABBREVIATIONS = frozenset(
    # One readable block rather than thirty quoted strings — the same shape
    # aureon.grants.scout gives its stopword list.
    """e.g i.e etc vs cf fig figs no nos ltd inc dr mr mrs ms st approx al ca
    ca et seq pp ref eq sec min hr hrs jan feb mar apr jun jul aug sep sept oct
    nov dec""".split()  # noqa: SIM905
)

# An exclamation inside a proper noun is not the end of a sentence. This corpus
# contains one such name on nearly every research page, and splitting it left
# half-sentences quoted back at the writer — and, worse, joined a capability
# clause to the research clause behind it, which reads as a blend that was never
# written. Matched against the text before "!": a short capitalised word,
# followed by another capitalised word.
_NAME_BANG = re.compile(r"\b[A-Z][A-Za-z]{0,3}$")


@dataclass(frozen=True)
class _Sentence:
    text: str
    line_no: int
    line_end: int
    quoted: bool = False


def _split_block(block: str) -> Iterator[tuple[int, str]]:
    """Yield ``(offset, sentence)`` for one paragraph of prose.

    Boundary rule: terminal punctuation followed by whitespace or end of block.
    Decimals survive because ``0.85`` has no space after the stop, and the
    common abbreviations survive by name — a checker that split ``e.g.`` in two
    would quote half-sentences back at the writer and lose their trust on the
    first read.
    """
    start = 0
    i = 0
    n = len(block)
    while i < n:
        if block[i] in ".!?":
            j = i + 1
            while j < n and block[j] in "\"')]»”’*_`":
                j += 1
            if j >= n or block[j].isspace():
                word = re.search(r"([A-Za-z][A-Za-z.]*)$", block[start:i])
                if block[i] == "." and word and word.group(1).lower().strip(".") in _ABBREVIATIONS:
                    i = j
                    continue
                if block[i] == "!" and _NAME_BANG.search(block[start:i]):
                    rest = block[j:].lstrip()
                    if rest[:1].isupper():
                        i = j
                        continue
                sentence = block[start:j].strip()
                if sentence:
                    yield start, sentence
                while j < n and block[j].isspace():
                    j += 1
                start = i = j
                continue
        i += 1
    tail = block[start:].strip()
    if tail:
        yield start, tail


def _sentences(text: str) -> tuple[_Sentence, ...]:
    """Split ``text`` into checkable sentences, each carrying its line number.

    Markdown-aware in four ways that matter. Fenced code is skipped entirely —
    code is not prose and its identifiers are not claims. A blockquote is marked
    ``quoted`` and exempted. A table row is checked as one unit, because a
    claims table keeps the claim in one cell and its citation in another, and
    splitting them would report every cited row as uncited. A heading or bullet
    is checked with its marker removed: an overclaim in a heading is still an
    overclaim, and it is the part a reader sees first.
    """
    out: list[_Sentence] = []
    lines = text.splitlines()
    in_fence = False
    block: list[tuple[int, str]] = []  # (line_no, text)

    def flush() -> None:
        if not block:
            return
        body = "\n".join(part for _, part in block)
        starts: list[int] = []
        offset = 0
        for _, part in block:
            starts.append(offset)
            offset += len(part) + 1
        first_line = block[0][0]
        last_line = block[-1][0]
        for start, sentence in _split_block(body):
            index = bisect.bisect_right(starts, start) - 1
            line_no = block[max(index, 0)][0]
            out.append(
                _Sentence(
                    text=" ".join(sentence.split()),
                    line_no=line_no,
                    line_end=last_line if len(block) > 1 else first_line,
                )
            )
        block.clear()

    for number, raw in enumerate(lines, start=1):
        if _FENCE.match(raw):
            flush()
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if _FULL_LINE_COMMENT.match(raw):
            flush()
            continue
        line = _INLINE_COMMENT.sub(" ", raw)
        if not line.strip():
            flush()
            continue
        quote = _BLOCKQUOTE.match(line)
        if quote:
            flush()
            body = " ".join(quote.group(1).split())
            if body:
                out.append(_Sentence(text=body, line_no=number, line_end=number, quoted=True))
            continue
        if _TABLE_DIVIDER.match(line):
            flush()
            continue
        if "|" in line and line.count("|") >= 2:
            flush()
            out.append(
                _Sentence(
                    text=" ".join(line.strip().strip("|").split()),
                    line_no=number,
                    line_end=number,
                )
            )
            continue
        heading = _HEADING.match(line)
        if heading:
            flush()
            body = " ".join(heading.group(1).split())
            if body:
                out.append(_Sentence(text=body, line_no=number, line_end=number))
            continue
        bullet = _BULLET.match(line)
        if bullet:
            flush()
            block.append((number, bullet.group(1)))
            continue
        block.append((number, line))
    flush()
    return tuple(out)


def _has_provenance(
    lines: Sequence[str],
    line_no: int,
    line_end: int,
    *,
    pattern: re.Pattern[str] | None = None,
) -> tuple[str, ...]:
    """Provenance markers within :data:`PROVENANCE_WINDOW` lines of a sentence.

    ``pattern`` selects the tier. The default scans everything that gestures at
    a source; :data:`_RESOLVABLE_PROVENANCE` scans only what names one a reader
    can open. The caller needs both, because a gesture and a citation used to be
    treated as the same thing and a number attributed to "Appendix Q" was
    reported as fully supported.
    """
    lo = max(0, line_no - 1 - PROVENANCE_WINDOW)
    hi = min(len(lines), line_end + PROVENANCE_WINDOW)
    return _scan(pattern or _PROVENANCE, "\n".join(lines[lo:hi]))


# ── the rules ────────────────────────────────────────────────────────────────


def _finding(
    *,
    rule: str,
    sentence: _Sentence,
    klass: ClaimClass,
    triggers: Sequence[str],
    suggestion: str,
    detail: str = "",
) -> ClaimFinding:
    """Build a finding whose severity and rule statement come from :data:`RULES`.

    The single constructor every detector goes through, which is why no detector
    can name a severity.
    """
    spec = RULES[rule]
    quoted = ", ".join(f'"{t}"' for t in triggers)
    issue = f"{spec.statement}{(' ' + detail) if detail else ''} Triggered by: {quoted}."
    return ClaimFinding(
        sentence=sentence.text,
        line_no=sentence.line_no,
        klass=klass,
        issue=issue,
        severity=spec.severity,
        suggestion=suggestion,
        rule=rule,
        trigger=tuple(triggers),
    )


def _check_blending(sig: _Signals, sentence: _Sentence, klass: ClaimClass) -> ClaimFinding | None:
    if not sig.capability:
        return None
    other = sig.research + sig.speculative
    if not other:
        return None
    # A hedge DOWNGRADES a blend; it does not dissolve one.
    #
    # These two clauses used to `return None`, and that was a hole wide enough to
    # drive through by accident. `_SEPARATOR` matches `unless`, `whether`, `^if`
    # and `would be`, and `_FORWARD_LOOKING` matches `will` — anywhere in the
    # sentence, in either clause. So a genuine blend went completely unreported
    # the moment any of those words appeared:
    #
    #   "The compliance auditor is implemented and covered by unit tests;
    #    unless the field is quiet it predicts the move 24 hours ahead."
    #
    # A verified software fact welded to a market-prediction claim, cleared by
    # one "unless". A trailing "which would be obvious to any reviewer" did the
    # same. That is worse than having no checker, because the output says clean.
    #
    # Hedging the speculative half is genuinely better writing, so it lowers the
    # severity — but the categories are still blended in one sentence, which is
    # the thing the owner's rule prohibits, so it is still reported.
    softened = bool(sig.forward_looking or sig.separators)
    kind = "research" if sig.research else "speculative"
    detail = f"The capability half is verifiable now; the {kind} half is not."
    if softened:
        marker = (sig.separators or sig.forward_looking)[0]
        detail += (
            f" The sentence hedges with {marker!r}, which lowers this to advisory"
            " — but the two categories are still welded together in one sentence."
        )
    return _finding(
        rule=RULE_BLENDING_HEDGED if softened else RULE_BLENDING,
        sentence=sentence,
        klass=klass,
        triggers=tuple(sig.capability[:2]) + tuple(other[:2]),
        detail=detail,
        suggestion=(
            "Split it in two. One sentence for what the software does, which a "
            "reader can run. One sentence for the claim under test, with its own "
            "hedge and its own source. An assessor who doubts the second should "
            "still be able to accept the first."
        ),
    )


def _check_unhedged_speculation(
    sig: _Signals, sentence: _Sentence, klass: ClaimClass
) -> ClaimFinding | None:
    if not sig.speculative or sig.hedges:
        return None
    if not (sig.referents or sig.empirical):
        return None  # register, not a claim: no date, no number, nothing to check
    return _finding(
        rule=RULE_UNHEDGED_SPECULATION,
        sentence=sentence,
        klass=klass,
        triggers=tuple(sig.speculative[:2]) + tuple((sig.referents or sig.quantities)[:1]),
        suggestion=(
            "Name it as a hypothesis and say what would falsify it, or cite the "
            "pre-registration that already does. Stated flat, it invites an "
            "assessor to discount the verified work beside it."
        ),
    )


def _check_absolute_language(
    sig: _Signals, sentence: _Sentence, klass: ClaimClass
) -> ClaimFinding | None:
    triggers: tuple[str, ...] = ()
    if sig.absolutes_hard and sig.falsifiable:
        triggers += sig.absolutes_hard
    if sig.absolutes_contextual and sig.empirical:
        triggers += sig.absolutes_contextual
    if not triggers:
        return None
    anchor = (sig.quantities or sig.research or sig.capability)[:1]
    return _finding(
        rule=RULE_ABSOLUTE_LANGUAGE,
        sentence=sentence,
        klass=klass,
        triggers=triggers + tuple(anchor),
        suggestion=(
            "Replace the absolute with the measurement: what was observed, over "
            "what sample, and what the residual uncertainty is. A stated bound "
            "is harder to attack than a claim of proof."
        ),
    )


def _check_quantitative_provenance(
    sig: _Signals,
    sentence: _Sentence,
    klass: ClaimClass,
    provenance: Sequence[str],
    resolvable: Sequence[str] = (),
) -> ClaimFinding | None:
    if not sig.quantities:
        return None
    if resolvable:
        return None  # points at something openable; nothing more to ask here
    if provenance:
        # A gesture was made but nothing checkable was named. Reported, not
        # cleared — the previous behaviour treated the two as equivalent.
        return _finding(
            rule=RULE_UNVERIFIED_PROVENANCE,
            sentence=sentence,
            klass=klass,
            triggers=tuple(sig.quantities[:2]) + tuple(provenance[:2]),
            detail="The citation gestures at a source without naming one.",
            suggestion=(
                f"Name the thing: a row in {EVIDENCE_DOC}, a file path, or a URL. "
                "An assessor who cannot follow the reference reads the number as "
                "unsupported, and is right to."
            ),
        )
    return _finding(
        rule=RULE_QUANTITATIVE_WITHOUT_PROVENANCE,
        sentence=sentence,
        klass=klass,
        triggers=sig.quantities[:3],
        suggestion=(
            f"Cite the row in {EVIDENCE_DOC} that establishes it, or the file "
            "that measured it. If neither exists yet, the number is not ready "
            "to leave the building."
        ),
    )


def _check_contradiction(
    sig: _Signals,
    sentence: _Sentence,
    klass: ClaimClass,
    blockers: Sequence[str],
) -> ClaimFinding | None:
    if not sig.clearance or not blockers:
        return None
    return _finding(
        rule=RULE_CONTRADICTED_BY_RECORD,
        sentence=sentence,
        klass=klass,
        triggers=tuple(sig.clearance[:1]) + tuple(blockers[:1]),
        detail="The blocker is quoted verbatim from the company's own record.",
        suggestion=(
            "Say what the record says and what is being done about it. The "
            "register is public and an assessor reads it before the narrative; "
            "a disclosed blocker with a date beats a contradicted claim."
        ),
    )


# ── the check ────────────────────────────────────────────────────────────────


def check_claims(text: str, *, capability: CapabilityProfile | None = None) -> ClaimReport:
    """Check ``text`` against the claim-discipline rule and report, never rewrite.

    ``capability`` is any object exposing ``compliance_blockers`` and
    ``sources`` — :func:`aureon.grants.scout.read_capability` returns one. It is
    read for two things and nothing else:

    * its verbatim ``compliance_blockers``, which enable
      :data:`RULE_CONTRADICTED_BY_RECORD`. Without a profile that rule cannot
      run, and :attr:`ClaimReport.blocker` says so rather than letting a clean
      report imply the company's record was consulted.
    * its ``sources``, echoed into the report so a reader can see *which*
      documents the contradiction was checked against.

    It is typed loosely on purpose: this module does not import the grant organ,
    so a checker can be used on any prose without dragging a bus, a ledger and a
    daemon in behind it.

    Findings come back sorted by severity and then by line, so the first item is
    always the thing to fix first.
    """
    lines = text.splitlines()
    blockers: tuple[str, ...] = tuple(getattr(capability, "compliance_blockers", ()) or ())
    sources: tuple[str, ...] = tuple(getattr(capability, "sources", ()) or ())

    findings: list[ClaimFinding] = []
    quoted: list[str] = []
    class_counts: dict[str, int] = {klass.value: 0 for klass in ClaimClass}
    checked = 0

    for sentence in _sentences(text):
        if sentence.quoted:
            quoted.append(sentence.text)
            continue
        checked += 1
        sig = _signals(sentence.text)
        klass = _classify(sig)
        class_counts[klass.value] += 1
        provenance = _has_provenance(lines, sentence.line_no, sentence.line_end)
        resolvable = _has_provenance(
            lines, sentence.line_no, sentence.line_end, pattern=_RESOLVABLE_PROVENANCE
        )
        for found in (
            _check_blending(sig, sentence, klass),
            _check_contradiction(sig, sentence, klass, blockers),
            _check_unhedged_speculation(sig, sentence, klass),
            _check_absolute_language(sig, sentence, klass),
            _check_quantitative_provenance(sig, sentence, klass, provenance, resolvable),
        ):
            if found is not None:
                findings.append(found)

    findings.sort(key=lambda f: (-f.rank, f.line_no, f.rule))
    blocker = (
        None
        if capability is not None
        else (
            "no capability profile supplied: the "
            f"{RULE_CONTRADICTED_BY_RECORD} rule did not run, so nothing here "
            "was checked against the company's own compliance record"
        )
    )
    return ClaimReport(
        findings=tuple(findings),
        sentences_checked=checked,
        class_counts=class_counts,
        quoted_exemptions=tuple(quoted),
        capability_sources=sources,
        blocker=blocker,
    )


# ── the rule itself, read rather than transcribed ────────────────────────────

_CLAIM_DISCIPLINE_LABEL = re.compile(r"claim discipline", re.IGNORECASE)


def read_claim_rule(root: Path | str | None = None) -> SourcedRule:
    """Read the owner's claim-discipline rule verbatim from the reconciliation.

    No code path in this module falls back to a literal copy of the rule — the
    only copy is the one in the module docstring, where a reader can see it and
    nothing can execute it. The rule itself lives in
    ``data/research/grants/RECONCILIATION_20260731.md``, quoted from the sheet,
    and it is read back through :mod:`aureon.grants.scout`'s own blockquote
    walker — the same extractor that reads the grant thesis and the compliance
    blockers. Reaching for a private helper there is a real coupling and it was
    chosen deliberately: a second copy of that walker is how two readers of one
    document begin to disagree about what the document says.

    Returns ``text=None`` with a stated ``blocker`` when the document, the row,
    or the helper is not there. It never falls back to a literal.
    """
    try:
        # importlib, not ``import aureon.grants.scout`` — the package re-exports a
        # function of the same name and shadows the submodule attribute. Imported
        # here rather than at module scope so the checker stays free of the organ.
        scout = importlib.import_module("aureon.grants.scout")
    except Exception as exc:  # pragma: no cover - import failure is environmental
        return SourcedRule(blocker=f"aureon.grants.scout unavailable: {exc}")

    relative = getattr(scout, "RECONCILIATION_DOC", None)
    extract = getattr(scout, "_quoted_after", None)
    if relative is None or extract is None:
        return SourcedRule(
            blocker="aureon.grants.scout no longer exposes the reconciliation path "
            "or its blockquote reader; the claim-discipline rule was not read"
        )

    base = Path(root) if root is not None else getattr(scout, "REPO_ROOT", Path.cwd())
    path = Path(base) / relative
    try:
        body = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return SourcedRule(blocker=f"{relative} unreadable: {exc}")

    quote = extract(body, _CLAIM_DISCIPLINE_LABEL)
    if not quote:
        return SourcedRule(
            source=relative,
            blocker=f"{relative} carries no 'Claim discipline' row; the rule was not read",
        )
    return SourcedRule(text=quote, source=relative)


__all__ = [
    "ADVISORY",
    "BLOCKING",
    "CRITICAL",
    "SERIOUS",
    "EVIDENCE_DOC",
    "PROVENANCE_WINDOW",
    "RULES",
    "RULE_ABSOLUTE_LANGUAGE",
    "RULE_BLENDING",
    "RULE_CONTRADICTED_BY_RECORD",
    "RULE_QUANTITATIVE_WITHOUT_PROVENANCE",
    "RULE_UNHEDGED_SPECULATION",
    "SEVERITY_RANK",
    "CheckRule",
    "ClaimClass",
    "ClaimFinding",
    "ClaimReport",
    "SourcedRule",
    "check_claims",
    "classify_sentence",
    "read_claim_rule",
]
