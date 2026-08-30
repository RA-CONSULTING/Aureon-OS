"""Reconcile multi-source public content while excluding private material."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from .common import CapabilityInputError, CapabilityResult, finding, require_mapping

SKILL_ID = "content_inventory_connectors"
_SOURCES = {"academia", "drive", "github", "gmail", "orcid", "repo", "substack", "zenodo"}
_PUBLIC_VISIBILITY = {"public", "approved-public"}
_PRIVATE_MARKERS = ("internal", "password", "private", "revenue", "secret", "token")


def reconcile_content_inventory(
    records: Sequence[Mapping[str, object]],
    rendered_canonical_ids: Sequence[str],
) -> CapabilityResult:
    """Return only unique, explicitly public canonical content identifiers."""

    if not records or any(not isinstance(item, str) or not item for item in rendered_canonical_ids):
        raise CapabilityInputError("records must be non-empty and rendered_canonical_ids well formed")
    record_ids: list[str] = []
    source_keys: set[tuple[str, str]] = set()
    excluded: list[str] = []
    publishable: list[str] = []
    evidence: list[str] = []
    for index, value in enumerate(records):
        row = require_mapping(value, f"records[{index}]")
        record_id = row.get("id")
        source = row.get("source")
        source_id = row.get("source_id")
        visibility = row.get("visibility")
        observed_at = row.get("observed_at")
        if (
            not isinstance(record_id, str)
            or not record_id
            or record_id in record_ids
            or source not in _SOURCES
            or not isinstance(source_id, str)
            or not source_id
            or not isinstance(visibility, str)
            or not isinstance(observed_at, str)
            or not observed_at
        ):
            raise CapabilityInputError(
                "inventory records require unique ids, canonical source, source_id, visibility, and date"
            )
        source_key = (str(source), source_id)
        if source_key in source_keys:
            raise CapabilityInputError("duplicate source/source_id inventory record")
        source_keys.add(source_key)
        record_ids.append(record_id)
        canonical_id = row.get("canonical_id", record_id)
        if not isinstance(canonical_id, str) or not canonical_id:
            raise CapabilityInputError("canonical_id must be a non-empty string")
        title = row.get("title", "")
        if not isinstance(title, str):
            raise CapabilityInputError("inventory title must be a string")
        private_marker = any(marker in title.lower() for marker in _PRIVATE_MARKERS)
        should_exclude = (
            visibility not in _PUBLIC_VISIBILITY or row.get("contains_secret") is True or private_marker
        )
        if should_exclude:
            excluded.append(record_id)
        elif canonical_id not in publishable:
            publishable.append(canonical_id)
        evidence.append(f"{source}:{source_id}")
    hidden_approved = sorted(set(publishable) - set(rendered_canonical_ids))
    unmapped_rendered = sorted(set(rendered_canonical_ids) - set(publishable))
    findings = (
        finding(
            "private-internal-exclusion",
            True,
            f"Excluded {len(excluded)} private, internal, secret-bearing, or non-public records.",
        ),
        finding(
            "public-content-present",
            bool(publishable),
            "At least one explicitly public content object remains after reconciliation.",
        ),
        finding(
            "source-record-uniqueness",
            len(source_keys) == len(records),
            "Source records are unique and traceable.",
        ),
        finding(
            "approved-work-coverage",
            not hidden_approved,
            "Every approved public work item appears in the rendered coverage matrix."
            if not hidden_approved
            else f"Approved but hidden work: {', '.join(hidden_approved)}.",
        ),
        finding(
            "rendered-work-provenance",
            not unmapped_rendered,
            "Every rendered work item maps to an approved public inventory record."
            if not unmapped_rendered
            else f"Rendered work without approved inventory provenance: {', '.join(unmapped_rendered)}.",
        ),
    )
    return CapabilityResult(
        SKILL_ID,
        findings,
        evidence=tuple(evidence),
        metrics={
            "record_count": len(record_ids),
            "excluded_count": len(excluded),
            "publishable_count": len(publishable),
            "hidden_approved_count": len(hidden_approved),
        },
        publishable_ids=tuple(publishable) if not hidden_approved and not unmapped_rendered else (),
    )
