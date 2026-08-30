"""Audit dated primary-source competitor observations and bounded inference."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from urllib.parse import urlparse

from .common import CapabilityInputError, CapabilityResult, finding, require_mapping

SKILL_ID = "competitor_position_audit"


def audit_competitor_sources(
    records: Sequence[Mapping[str, object]], *, as_of: date, max_age_days: int = 366
) -> CapabilityResult:
    """Require primary, dated sources and separation of observation from inference."""

    if not records or max_age_days <= 0:
        raise CapabilityInputError("records must be non-empty and max_age_days positive")
    ids: list[str] = []
    malformed: list[str] = []
    stale: list[str] = []
    imitation_risk: list[str] = []
    for index, value in enumerate(records):
        row = require_mapping(value, f"records[{index}]")
        record_id = row.get("id")
        if not isinstance(record_id, str) or not record_id or record_id in ids:
            raise CapabilityInputError("competitor record ids must be unique non-empty strings")
        ids.append(record_id)
        source_url = row.get("source_url")
        captured_at = row.get("captured_at")
        name = row.get("competitor")
        observation = row.get("observation")
        inference = row.get("aureon_inference")
        valid_url = (
            isinstance(source_url, str)
            and urlparse(source_url).scheme == "https"
            and bool(urlparse(source_url).netloc)
        )
        try:
            captured = date.fromisoformat(captured_at) if isinstance(captured_at, str) else None
        except ValueError:
            captured = None
        valid = (
            valid_url
            and captured is not None
            and captured <= as_of
            and row.get("source_type") == "primary"
            and isinstance(name, str)
            and name.strip().lower() not in {"aureon", "aureon zorza technologies"}
            and isinstance(observation, str)
            and bool(observation.strip())
            and isinstance(inference, str)
            and bool(inference.strip())
            and observation.strip() != inference.strip()
        )
        if not valid:
            malformed.append(record_id)
        if captured is not None and (as_of - captured).days > max_age_days:
            stale.append(record_id)
        if row.get("copy_instruction") not in {None, False, "do-not-copy"}:
            imitation_risk.append(record_id)
    findings = (
        finding(
            "primary-source-shape",
            not malformed,
            "Every competitor observation has a dated primary source and separate Aureon inference."
            if not malformed
            else f"Malformed competitor records: {', '.join(malformed)}.",
        ),
        finding(
            "source-freshness",
            not stale,
            "All competitor sources are within the permitted age window."
            if not stale
            else f"Stale competitor sources: {', '.join(stale)}.",
        ),
        finding(
            "no-copy-instruction",
            not imitation_risk,
            "Records contain no instruction to copy competitor expression."
            if not imitation_risk
            else f"Copy risk: {', '.join(imitation_risk)}.",
        ),
    )
    return CapabilityResult(
        SKILL_ID,
        findings,
        evidence=tuple(f"competitor-source:{item}" for item in ids),
        metrics={"record_count": len(ids), "stale_count": len(stale)},
    )
