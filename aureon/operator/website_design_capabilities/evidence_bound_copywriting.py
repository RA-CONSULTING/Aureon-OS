"""Cross-check public copy against a structured provenance ledger."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from pathlib import Path

from .common import CapabilityInputError, CapabilityResult, finding, read_text, require_mapping

SKILL_ID = "evidence_bound_copywriting"
_CLAIM_ID = re.compile(r"data-claim-id=[\"']([a-z0-9][a-z0-9._-]*)[\"']", re.IGNORECASE)
_PUBLIC_STATES = {"evidenced", "qualified", "research", "vision"}


def audit_copy_provenance(root: Path, ledger_path: str, html_paths: Sequence[str]) -> CapabilityResult:
    """Require every annotated material claim to have source, date, and public state."""

    if not html_paths:
        raise CapabilityInputError("html_paths must be non-empty")
    ledger_safe, ledger_source = read_text(root, ledger_path, suffixes={".json"})
    try:
        ledger_raw = json.loads(ledger_source)
    except json.JSONDecodeError as exc:
        raise CapabilityInputError("claim ledger must be valid JSON") from exc
    ledger = require_mapping(ledger_raw, "claim ledger")
    records_raw = ledger.get("claims")
    if not isinstance(records_raw, list):
        raise CapabilityInputError("claim ledger claims must be a list")
    records: dict[str, dict[str, object]] = {}
    malformed: list[str] = []
    for index, value in enumerate(records_raw):
        row = require_mapping(value, f"claims[{index}]")
        claim_id = row.get("id")
        if not isinstance(claim_id, str) or not claim_id or claim_id in records:
            raise CapabilityInputError("claim ids must be unique non-empty strings")
        state = row.get("state")
        source = row.get("source")
        observed_at = row.get("observed_at")
        if (
            state not in _PUBLIC_STATES
            or not isinstance(source, str)
            or not source
            or not isinstance(observed_at, str)
            or not observed_at
        ):
            malformed.append(claim_id)
        records[claim_id] = dict(row)
    evidence = [ledger_safe]
    used_ids: list[str] = []
    for item in html_paths:
        safe, source = read_text(root, item, suffixes={".html", ".htm"})
        evidence.append(safe)
        used_ids.extend(_CLAIM_ID.findall(source))
    missing = sorted(set(used_ids) - set(records))
    unused = sorted(set(records) - set(used_ids))
    findings = (
        finding(
            "claim-record-shape",
            not malformed,
            "All ledger claims have a public state, source, and date."
            if not malformed
            else f"Malformed claim records: {', '.join(malformed)}.",
        ),
        finding(
            "copy-claim-binding",
            not missing,
            "Every annotated public claim is present in the ledger."
            if not missing
            else f"Unbound public claims: {', '.join(missing)}.",
        ),
        finding(
            "ledger-usage",
            not unused,
            "All ledger claims are rendered in the supplied pages."
            if not unused
            else f"Unused ledger claims: {', '.join(unused)}.",
            warning=True,
        ),
    )
    return CapabilityResult(
        SKILL_ID,
        findings,
        evidence=tuple(evidence),
        metrics={"rendered_claim_count": len(used_ids), "ledger_claim_count": len(records)},
    )
