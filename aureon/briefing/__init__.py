"""The briefing organ — she assembles her own context, then drafts from it.

Gary wrote a handoff prompt to paste into a chat assistant. Almost every line of
its CONTEXT block is something this repository already knows about itself: the
company record, the decision spine, the positioning line, the live deadlines, the
Companies House blocker, the standing rule that no submission or send happens
without him. Having a human retype that each time is the organism failing to use
its own organs.

The package closes that loop in four parts:

- :mod:`aureon.briefing.schemas` models a brief in which a line without a source
  cannot exist.
- :mod:`aureon.briefing.assemble` reads it — identity, the grant ledger
  (read-only), the compliance auditor, the scout's capability profile, the HNC
  field and the Auris panel — with every value carrying the file or the organ it
  came from, and everything unreadable listed as NOT READ rather than filled in.
- :mod:`aureon.briefing.claims` audits prose against Gary's own claim-discipline
  rule, read from the reconciliation report and written nowhere in this package.
- :mod:`aureon.briefing.render` renders the brief as markdown or as the prompt
  itself, with the two binding rules quoted verbatim.
- :mod:`aureon.briefing.author` drafts: it routes ``draft_narrative`` through the
  Queen's switchboard *before* writing a word, refuses to present a stub adapter's
  configuration message as a draft, and runs the claim check over its own output.

The local model is a small one and this package says so on every result. For a
competitive bid the intended route is
:func:`~aureon.briefing.author.export_for_stronger_model`: assemble the brief
locally — the hard, grounded part — then take it to a model strong enough for the
job, and run the claim check over what comes back.

Nothing here submits, files, pays or sends. It returns strings.
"""

from aureon.briefing.assemble import assemble_brief
from aureon.briefing.author import (
    DRAFT_ACTION,
    DRAFT_CHAIN,
    MODEL_CAVEAT,
    REVISION_SEVERITIES,
    SYSTEM_PROMPT,
    DraftResult,
    adapter_blocker,
    draft,
    export_for_stronger_model,
    response_blocker,
)
from aureon.briefing.claims import (
    ADVISORY,
    BLOCKING,
    CRITICAL,
    RULE_ABSOLUTE_LANGUAGE,
    RULE_BLENDING,
    RULE_CONTRADICTED_BY_RECORD,
    RULE_QUANTITATIVE_WITHOUT_PROVENANCE,
    RULE_UNHEDGED_SPECULATION,
    RULES,
    SERIOUS,
    ClaimClass,
    ClaimFinding,
    ClaimReport,
    SourcedRule,
    check_claims,
    classify_sentence,
    read_claim_rule,
)
from aureon.briefing.render import render_markdown, render_prompt
from aureon.briefing.schemas import Brief, Capability, Priority, SourcedLine

__all__ = [
    "ADVISORY",
    "BLOCKING",
    "CRITICAL",
    "DRAFT_ACTION",
    "DRAFT_CHAIN",
    "MODEL_CAVEAT",
    "REVISION_SEVERITIES",
    "RULES",
    "RULE_ABSOLUTE_LANGUAGE",
    "RULE_BLENDING",
    "RULE_CONTRADICTED_BY_RECORD",
    "RULE_QUANTITATIVE_WITHOUT_PROVENANCE",
    "RULE_UNHEDGED_SPECULATION",
    "SERIOUS",
    "SYSTEM_PROMPT",
    "Brief",
    "Capability",
    "ClaimClass",
    "ClaimFinding",
    "ClaimReport",
    "DraftResult",
    "Priority",
    "SourcedLine",
    "SourcedRule",
    "adapter_blocker",
    "assemble_brief",
    "check_claims",
    "classify_sentence",
    "draft",
    "export_for_stronger_model",
    "read_claim_rule",
    "render_markdown",
    "render_prompt",
    "response_blocker",
]
