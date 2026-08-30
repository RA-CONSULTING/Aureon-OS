"""Lint material public claims against explicit evidence states."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from .common import CapabilityInputError, CapabilityResult, finding, require_mapping

SKILL_ID = "claim_state_linter"
_STATES = {"evidenced", "qualified", "research", "vision", "omitted"}
_RISKY = re.compile(
    r"\b(?:certified|customer|deployed|guarantee(?:d)?|peer[ -]reviewed|proven|revenue|validated)\b",
    re.IGNORECASE,
)


def lint_claim_states(
    claims: Sequence[Mapping[str, object]],
    rendered_claim_ids: Sequence[str],
) -> CapabilityResult:
    """Block unsupported high-risk language and incomplete claim-state records."""

    if (
        not claims
        or not rendered_claim_ids
        or any(not isinstance(item, str) or not item for item in rendered_claim_ids)
    ):
        raise CapabilityInputError("claims and rendered_claim_ids must be non-empty and well formed")
    ids: list[str] = []
    malformed: list[str] = []
    unsafe: list[str] = []
    omitted_rendered: list[str] = []
    publishable: list[str] = []
    for index, value in enumerate(claims):
        row = require_mapping(value, f"claims[{index}]")
        claim_id = row.get("id")
        text = row.get("text")
        state = row.get("state")
        if (
            not isinstance(claim_id, str)
            or not claim_id
            or claim_id in ids
            or not isinstance(text, str)
            or not text.strip()
            or state not in _STATES
        ):
            raise CapabilityInputError("claims require unique id, non-empty text, and a canonical state")
        ids.append(claim_id)
        source = row.get("source")
        qualifier = row.get("qualifier")
        rendered = row.get("rendered", True)
        complete = True
        if state in {"evidenced", "qualified", "research"}:
            complete = isinstance(source, str) and source.startswith(("https://", "repo:"))
        if state in {"qualified", "research", "vision"}:
            complete = complete and isinstance(qualifier, str) and bool(qualifier.strip())
        if not complete:
            malformed.append(claim_id)
        if _RISKY.search(text) and state != "evidenced":
            unsafe.append(claim_id)
        if state == "omitted" and rendered is True:
            omitted_rendered.append(claim_id)
        if state != "omitted" and complete and claim_id not in unsafe:
            publishable.append(claim_id)
    unmapped = sorted(set(rendered_claim_ids) - set(ids))
    unrendered_active = sorted(
        claim_id
        for claim_id, row in zip(ids, claims, strict=True)
        if row.get("state") != "omitted" and claim_id not in rendered_claim_ids
    )
    findings = (
        finding(
            "claim-state-completeness",
            not malformed,
            "Every claim state has its required source and qualifier."
            if not malformed
            else f"Incomplete claim records: {', '.join(malformed)}.",
        ),
        finding(
            "high-risk-language",
            not unsafe,
            "High-risk outcome language is bound to evidenced state."
            if not unsafe
            else f"Unsupported high-risk claims: {', '.join(unsafe)}.",
        ),
        finding(
            "omitted-claims-hidden",
            not omitted_rendered,
            "Omitted claims are not rendered."
            if not omitted_rendered
            else f"Omitted claims marked rendered: {', '.join(omitted_rendered)}.",
        ),
        finding(
            "rendered-claims-mapped",
            not unmapped,
            "Every rendered material claim maps to a claim-state record."
            if not unmapped
            else f"Rendered claims missing from ledger: {', '.join(unmapped)}.",
        ),
        finding(
            "active-claims-rendered",
            not unrendered_active,
            "Every non-omitted ledger claim is represented in the rendered inventory."
            if not unrendered_active
            else f"Active claims absent from rendered inventory: {', '.join(unrendered_active)}.",
        ),
    )
    passed = not malformed and not unsafe and not omitted_rendered and not unmapped and not unrendered_active
    return CapabilityResult(
        SKILL_ID,
        findings,
        evidence=tuple(f"claim:{item}" for item in ids),
        metrics={
            "claim_count": len(ids),
            "rendered_claim_count": len(rendered_claim_ids),
            "publishable_count": len(publishable),
        },
        publishable_ids=tuple(publishable) if passed else (),
    )
