"""Validate render-ready DOI, ORCID, certificate, and ledger objects."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from .common import CapabilityInputError, CapabilityResult, finding, require_mapping

SKILL_ID = "research_object_rendering"
_DOI = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
_KINDS = {"doi", "orcid", "certificate", "ledger"}


def _valid_orcid(value: str) -> bool:
    digits = value.replace("-", "").upper()
    if not re.fullmatch(r"\d{15}[\dX]", digits):
        return False
    total = 0
    for char in digits[:15]:
        total = (total + int(char)) * 2
    remainder = (12 - total % 11) % 11
    expected = "X" if remainder == 10 else str(remainder)
    return digits[-1] == expected


def audit_research_objects(objects: Sequence[Mapping[str, object]]) -> CapabilityResult:
    """Validate provenance fields and identifiers needed for truthful rendering."""

    if not objects:
        raise CapabilityInputError("objects must be non-empty")
    malformed: list[str] = []
    ids: list[str] = []
    for index, value in enumerate(objects):
        row = require_mapping(value, f"objects[{index}]")
        object_id = row.get("id")
        kind = row.get("kind")
        title = row.get("title")
        observed_at = row.get("observed_at")
        source_url = row.get("source_url")
        if not isinstance(object_id, str) or not object_id or object_id in ids:
            raise CapabilityInputError("research object ids must be unique non-empty strings")
        ids.append(object_id)
        valid = (
            kind in _KINDS
            and isinstance(title, str)
            and bool(title.strip())
            and isinstance(observed_at, str)
            and bool(observed_at.strip())
            and isinstance(source_url, str)
            and source_url.startswith("https://")
        )
        identifier = row.get("identifier")
        if kind == "doi":
            valid = valid and isinstance(identifier, str) and bool(_DOI.fullmatch(identifier))
        elif kind == "orcid":
            valid = valid and isinstance(identifier, str) and _valid_orcid(identifier)
        elif kind in {"certificate", "ledger"}:
            valid = valid and isinstance(identifier, str) and bool(identifier.strip())
        if not valid:
            malformed.append(object_id)
    findings = (
        finding(
            "research-object-provenance",
            not malformed,
            "Every research object has a valid identifier and render provenance."
            if not malformed
            else f"Invalid research objects: {', '.join(malformed)}.",
        ),
        finding("research-object-uniqueness", len(ids) == len(set(ids)), "Research object ids are unique."),
    )
    return CapabilityResult(
        SKILL_ID,
        findings,
        evidence=tuple(f"research-object:{item}" for item in ids),
        metrics={"object_count": len(ids)},
        publishable_ids=tuple(ids) if not malformed else (),
    )
