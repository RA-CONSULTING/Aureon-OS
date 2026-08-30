"""The grant organ.

Aureon has been doing grant work for months — 66 applications and ~1,100 dated
artifacts under ``data/research/grants/`` — but entirely outside itself: authored
by an operator run, read by nothing. The organism could not see its own funding
pipeline, so it could not notice a deadline, feel its pressure, or act on it.

This package makes the pipeline part of the body:

- :mod:`aureon.grants.ledger` reads ``pipeline.json`` and reconciles it (read-only).
- :mod:`aureon.grants.schemas` models applications, deadline alerts, pipeline state.
- :mod:`aureon.grants.daemon` breathes: publishes ``grants.*`` on the thought bus,
  contributes urgency to the HNC field as a subfield, and paces its own interval
  from real deadline pressure — φ-scaled, faster as a deadline nears.
- :mod:`aureon.grants.scout` looks the other way down the pipe — at calls not yet
  applied for. It retrieves them with mandatory provenance, scores the overlap
  against a capability profile read from the company's own documents, and routes
  "should we pursue this?" through the Queen's switchboard rather than deciding.
- :mod:`aureon.grants.compliance` audits: the eligibility and compliance gates a
  funder checks *before* effort is spent, read from real documents so a blocker
  surfaces early rather than at the submit button. A missing source is reported
  as ``unknown``, never as clearance.
- :mod:`aureon.grants.dossier` assembles the approval packet for one
  application — deadline, fit, compliance, evidence, and what is missing — and
  routes it through the Queen's switchboard, where it stops. ``submit`` is
  human-held, so every packet ends in HOLD for Gary.

It never submits. ``autopilot_status.json`` reserves final submission for
explicit human confirmation; this organ raises awareness and holds that line.

One name to know about: re-exporting the ``scout`` *function* below binds the
name ``scout`` on this package, shadowing the ``aureon.grants.scout`` submodule
attribute. ``from aureon.grants.scout import ...`` works normally, but
``import aureon.grants.scout as m`` hands back the function, not the module —
reach for ``importlib.import_module("aureon.grants.scout")`` when you need the
module itself (patching, for instance). The function keeps the plain name
because that is the API callers want.
"""

from aureon.grants.compliance import (
    ComplianceCheck,
    ComplianceReport,
    audit_readiness,
    compliance_verdict,
    run_gate_chain,
)
from aureon.grants.dossier import (
    Dossier,
    build_dossier,
    emit_dossier,
    render_markdown,
    write_dossier,
)
from aureon.grants.ledger import configured_routes, grants_dir, read_pipeline
from aureon.grants.schemas import (
    Application,
    CapabilityProfile,
    DeadlineAlert,
    FitScore,
    Opportunity,
    OpportunityAssessment,
    PipelineState,
    parse_dt,
)
from aureon.grants.scout import (
    SOURCE_DEGRADED_SEARCH,
    assess,
    read_capability,
    score_fit,
    scout,
)


def __getattr__(name: str):
    """Expose the daemon API lazily (PEP 562).

    Importing aureon.grants.daemon here would load it during package init, so
    `python -m aureon.grants.daemon` then executed the module a SECOND time as
    __main__ — the interpreter warns about exactly this, and it means module
    state (the _running flag, signal handlers) exists twice. Deferring the
    import keeps the convenience API without the double execution.
    """
    if name in ("run_once", "breath_interval", "main"):
        from aureon.grants import daemon

        return getattr(daemon, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "Application",
    "CapabilityProfile",
    "ComplianceCheck",
    "ComplianceReport",
    "DeadlineAlert",
    "Dossier",
    "FitScore",
    "Opportunity",
    "OpportunityAssessment",
    "PipelineState",
    "SOURCE_DEGRADED_SEARCH",
    "assess",
    "audit_readiness",
    "breath_interval",
    "build_dossier",
    "compliance_verdict",
    "configured_routes",
    "emit_dossier",
    "grants_dir",
    "parse_dt",
    "read_capability",
    "read_pipeline",
    "render_markdown",
    "run_gate_chain",
    "run_once",
    "score_fit",
    "scout",
    "write_dossier",
]
