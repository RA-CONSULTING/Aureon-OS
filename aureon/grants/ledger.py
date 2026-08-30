"""Read and reconcile the grant ledger.

The grant operator runs have been producing a real ledger
(``data/research/grants/pipeline.json``, 68 applications) and ~1,100 dated
artifacts beside it. Nothing in the codebase read any of it, so the organism was
blind to its own funding pipeline. This module is the eye.

Read-only by design: it never edits the ledger. Submission and application state
remain the operator's (and Gary's) to change — see the automation policy in
``autopilot_status.json``, which reserves final submission for explicit
human confirmation. This package honours that line.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from aureon.grants.schemas import Application, DeadlineAlert, PipelineState

# Repo root: aureon/grants/ledger.py -> parents[2]
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GRANTS_DIR = REPO_ROOT / "data" / "research" / "grants"
LEDGER_NAME = "pipeline.json"

# Deadline bands, in days remaining.
_SEVERITY_BANDS = ((0.0, "overdue"), (3.0, "critical"), (7.0, "urgent"), (30.0, "approaching"))


def grants_dir() -> Path:
    """Resolve the ledger directory. ``AUREON_GRANTS_DIR`` wins, always.

    This is the first consumer those 40+ AUREON_GRANT_* variables have ever
    had, and wiring it up immediately caught a real fault: the configured path
    pointed at an empty leftover directory from the repo's previous location
    (``aureon-trading``) while the live ledger — 68 applications, 1,100+
    artifacts — sat in the current repo.

    The tempting fix was to silently fall back to the default whenever the
    override held no ledger. That is worse. It makes a caller who asks for
    directory X quietly read directory Y — the fallback reached out of a test's
    tmp_path into the real repo ledger, which is exactly the sort of
    action-at-a-distance that hides faults instead of surfacing them. The
    configured path is honoured verbatim; a missing ledger becomes an
    unavailable pipeline whose blocker names the path it looked in, which is
    loud enough to find. The .env value itself was corrected at the source.
    """
    override = os.getenv("AUREON_GRANTS_DIR", "").strip()
    return Path(override) if override else DEFAULT_GRANTS_DIR


def _severity(days: float) -> str | None:
    for limit, name in _SEVERITY_BANDS:
        if days <= limit:
            return name
    return None


def read_pipeline(now: datetime | None = None, *, directory: Path | None = None) -> PipelineState:
    """Reconcile the ledger into a :class:`PipelineState`. Never raises.

    A missing or malformed ledger yields ``available=False`` with a blocker
    explaining why — never an empty pipeline presented as a healthy one.
    """
    now = now or datetime.now(UTC)
    directory = directory or grants_dir()
    ledger = directory / LEDGER_NAME

    if not ledger.exists():
        return PipelineState(available=False, generated_at=now, blocker=f"ledger not found: {ledger}",
                             ledger_path=str(ledger))
    try:
        raw = json.loads(ledger.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError) as exc:
        return PipelineState(available=False, generated_at=now,
                             blocker=f"ledger unreadable: {type(exc).__name__}", ledger_path=str(ledger))

    entries = raw.get("active_applications")
    if not isinstance(entries, list):
        return PipelineState(available=False, generated_at=now,
                             blocker="ledger has no active_applications list", ledger_path=str(ledger))

    apps = tuple(a for a in (Application.from_ledger(e) for e in entries) if a is not None)
    # Entries that carried no application data are skipped, but the count is
    # kept: the live ledger holds 68 entries of which 2 are bare id strings, and
    # reporting 66 applications without saying 2 were dropped would present a
    # partial read as a complete one.
    skipped = len(entries) - len(apps)

    alerts = []
    for app in apps:
        if not app.is_open:
            continue
        days = app.days_remaining(now)
        if days is None or app.deadline is None:
            continue
        sev = _severity(days)
        if sev:
            alerts.append(DeadlineAlert(application_id=app.id, name=app.name, funder=app.funder,
                                        days_remaining=days, deadline=app.deadline, severity=sev))
    alerts.sort(key=lambda a: a.days_remaining)

    try:
        artifact_count = sum(1 for p in directory.glob("*.json") if p.name != LEDGER_NAME)
    except OSError:
        artifact_count = 0

    return PipelineState(
        available=True,
        generated_at=now,
        applications=apps,
        alerts=tuple(alerts),
        artifact_count=artifact_count,
        ledger_path=str(ledger),
        skipped_entries=skipped,
    )


def configured_routes() -> dict[str, str]:
    """The funding routes configured in the environment.

    Gives the AUREON_GRANT_* / AUREON_IFS_* variables their first consumer.
    Only variables that are actually set are returned — an absent route is
    absent, not an empty placeholder.
    """
    out: dict[str, str] = {}
    for key, value in os.environ.items():
        if not (key.startswith("AUREON_GRANT_") or key.startswith("AUREON_IFS_")):
            continue
        value = (value or "").strip()
        # Never surface secrets, even though these are mostly URLs and statuses.
        if not value or any(t in key for t in ("PASSWORD", "SECRET", "TOKEN", "KEY")):
            continue
        out[key] = value
    return out


__all__ = ["read_pipeline", "configured_routes", "grants_dir", "DEFAULT_GRANTS_DIR"]
