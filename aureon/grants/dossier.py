"""The approval packet — one page a person can decide from, and the hold that protects it.

The grant organ can already *see* the pipeline (:mod:`aureon.grants.ledger`) and
*feel* its deadlines (:mod:`aureon.grants.daemon`). What it could not do was put
a decision in front of a human. The evidence for any one application was spread
across the ledger, the compliance position, the repository's own company record
and the Queen's gate chain, and nobody was assembling it.

This module assembles it, and does exactly one thing with the result: hands it
to Gary.

**The packet never becomes the decision.** Its action is ``submit_application``,
and ``submit`` is in :data:`aureon.gates.switchboard.HUMAN_HELD` — there is no
executor for it anywhere in this repository. The chain is run for real and its
verdicts are recorded verbatim, but the hold does not depend on how the chain
happens to come out. That is deliberate, and it fixes a real trap:

    ``switchboard.evaluate`` tests *blindness* before it tests *hands*. An
    organism that cannot read its own field returns REDO at the first gate and
    never reaches the human-held branch at all. A caller that read only the
    chain's terminal decision would therefore see REDO — "iterate and come
    back" — where the truth is HOLD — "this was never yours to send". The two
    are not interchangeable: one invites a retry, the other forbids one.

So :func:`build_dossier` asks :func:`~aureon.gates.switchboard.is_human_held`
directly, and the chain's own answer is reported alongside rather than in place
of it. The hold is a statement about which hands exist, not about confidence.

Everything else in the packet is a measurement or an absence:

- the application is read from the ledger, **read-only**, and an id that is not
  in the ledger yields ``None`` rather than an empty packet wearing its name;
- ``fit_score`` is ``None`` unless something real measured it.
  :func:`aureon.grants.scout.score_fit` scores an :class:`Opportunity`'s
  *retrieved call text*, and a ledger row carries no call text — so a caller who
  has a :class:`~aureon.grants.schemas.FitScore` passes it in, and otherwise the
  score is absent with the reason stated. The live ledger's own ``fit`` field is
  a sentence on 12 investor routes and absent on every grant application; that
  prose is preserved as :attr:`Dossier.fit_basis` and is never read as a number.
  A 0.0–1.0 "fit" invented here would be the most plausible-looking fabrication
  in the whole organ;
- the compliance position comes from :func:`aureon.grants.compliance.audit_readiness`,
  whose own contract is that a missing source is ``unknown`` and never ``pass``.
  A packet that cannot see compliance says so; it never renders as clean;
- the approval rule is quoted out of the newest reconciliation document in the
  grants directory rather than written into this file, so the packet cannot go
  on quoting a rule after the rule has changed.

Why the compliance short-circuit is deliberately *not* used
-----------------------------------------------------------
:func:`aureon.grants.compliance.run_gate_chain` refuses to spend the Queen's
chain while a compliance blocker is live, which is exactly right for the
question it answers — *should effort be spent here?*. This packet answers a
different one — *here is the whole position; what do you want to do?* — so it
records the compliance verdict **and** the submission chain side by side.
Suppressing the second because of the first would hide the packet's central
guarantee, which is that submission is human-held whatever else is true.

It writes only ``<grants dir>/dossiers/<application_id>.md``. It never touches
``pipeline.json`` — that ledger is the grant operator's and is written live.
"""

from __future__ import annotations

import json
import logging
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aureon.gates.switchboard import DEFAULT_CHAIN, HOLD, GateVerdict, is_human_held, run_chain
from aureon.grants.ledger import LEDGER_NAME, grants_dir, read_pipeline
from aureon.grants.schemas import Application, FitScore

LOG = logging.getLogger("aureon.grants.dossier")

#: Where packets are written, relative to the grants directory.
DOSSIER_DIRNAME = "dossiers"

#: The action the chain is asked about. Contains "submit" on purpose — see the
#: module docstring. :func:`build_dossier` asks ``is_human_held`` about this
#: constant rather than assuming it, so a rename cannot quietly un-hold a packet.
SUBMIT_ACTION = "submit_application"

TOPIC_DOSSIER = "grants.dossier.built"

#: Approval state used when the packet's own action is no longer recognised as
#: human-held. Never ``ADVANCE``: an unrecognised action is an unknown, and an
#: unknown must not read as permission.
UNDECIDED = "UNDECIDED"

# The reconciliation report is a dated file (RECONCILIATION_20260731.md). The
# date is not written into this module: the newest matching file wins, so a
# later reconciliation supersedes an earlier one without a code change.
RECONCILIATION_GLOB = "RECONCILIATION_*.md"
_APPROVAL_RULE_LABEL = re.compile(r"approval\s+rule", re.IGNORECASE)
_BLOCKQUOTE = re.compile(r"^\s*>\s*(.+?)\s*$")
# How far past the label to look for its quote. The document puts a blank line,
# a "verbatim:" lead-in and another blank line between the two.
_QUOTE_WINDOW = 8
_MIN_QUOTE_CHARS = 20

# The Queen's own gates, so a compliance verdict sitting in front of them is
# never mistaken for the chain's terminal decision.
_CHAIN_GATES = frozenset(g.name for g in DEFAULT_CHAIN)

# How many evidence documents the *brief* lists. The dossier keeps every one of
# them; only the rendering is capped, and it prints the number it did not show.
# This is not cosmetic: live applications carry hundreds of artifacts each, and
# an approval brief that runs to 60 KB of filenames is not a brief — the one
# thing it must do is be read.
_MAX_DOCUMENTS = 20

# Characters allowed in a written filename. Application ids are already tame
# (APP-IFS-CFI-SEN-2511-20260709), but an id is ledger data, not code, and a
# ledger row carrying "../" must not be able to steer a write out of the
# dossiers directory.
_UNSAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True)
class Cited:
    """A value plus the document it was read out of.

    Deliberately the same shape as
    :class:`aureon.identity.schemas.SourcedFact` without depending on it: this
    module quotes documents the identity organ does not read (the reconciliation
    report), and a fact with no ``source`` is not constructible either way.
    """

    label: str
    value: str
    source: str

    def to_dict(self) -> dict[str, str]:
        return {"label": self.label, "value": self.value, "source": self.source}


@dataclass
class Dossier:
    """Everything a human needs to make one submit / no-submit call.

    Every field is a value read from a real source or ``None`` with the reason
    recorded in :attr:`outstanding`. Nothing here is scored, estimated or
    filled in.
    """

    application_id: str
    name: str
    funder: str
    status: str
    lifecycle: str
    deadline: datetime | None
    days_remaining: float | None
    amount_requested: float | None
    currency: str
    fit_score: float | None
    fit_basis: str | None
    compliance: str | None
    compliance_blocker: str | None
    evidence_documents: tuple[str, ...]
    gate_verdicts: tuple[GateVerdict, ...]
    outstanding: tuple[str, ...]
    approval_state: str
    approval_reasoning: str
    approval_rule: Cited | None
    applicant: tuple[Cited, ...]
    generated_at: datetime
    ledger_path: str

    @property
    def held(self) -> bool:
        """True when this packet is waiting on a person and not on evidence."""
        return self.approval_state == HOLD

    def to_dict(self) -> dict[str, Any]:
        return {
            "application_id": self.application_id,
            "name": self.name,
            "funder": self.funder,
            "status": self.status,
            "lifecycle": self.lifecycle,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "days_remaining": round(self.days_remaining, 2) if self.days_remaining is not None else None,
            "amount_requested": self.amount_requested,
            "currency": self.currency,
            "fit_score": self.fit_score,
            "fit_basis": self.fit_basis,
            "compliance": self.compliance,
            "compliance_blocker": self.compliance_blocker,
            "evidence_documents": list(self.evidence_documents),
            "gate_verdicts": [v.to_dict() for v in self.gate_verdicts],
            "outstanding": list(self.outstanding),
            "approval_state": self.approval_state,
            "approval_reasoning": self.approval_reasoning,
            "approval_rule": self.approval_rule.to_dict() if self.approval_rule else None,
            "applicant": [c.to_dict() for c in self.applicant],
            "generated_at": self.generated_at.isoformat(),
            "ledger_path": self.ledger_path,
        }


# ── locating things ──────────────────────────────────────────────────────────


def grants_directory(root: Path | str | None = None) -> Path:
    """The grants directory for a given repository root.

    ``root=None`` defers to :func:`aureon.grants.ledger.grants_dir`, so the
    packet reads the same ledger the daemon breathes on. An explicit ``root`` is
    honoured verbatim with no environment fallback — the same rule
    ``grants_dir`` follows and for the same reason: a reader that quietly
    reaches out of the caller's tree into the live repository hides faults and
    leaks live data into tests.
    """
    if root is None:
        return grants_dir()
    return Path(root) / "data" / "research" / "grants"


def dossier_path(application_id: str, *, root: Path | str | None = None) -> Path:
    """Where a packet for this id is written. Always inside ``dossiers/``."""
    stem = _UNSAFE_FILENAME.sub("_", str(application_id or "").strip()) or "unnamed"
    # A name of dots alone would resolve to the directory itself or its parent.
    stem = stem.lstrip(".") or "unnamed"
    return grants_directory(root) / DOSSIER_DIRNAME / f"{stem}.md"


def read_approval_rule(directory: Path | str | None = None) -> Cited | None:
    """Quote the approval rule out of the newest reconciliation document.

    The rule is a live operating constraint recorded by a human, not a constant
    of this code. Reading it at runtime means the packet cannot keep quoting a
    superseded rule, and an unreadable source becomes a stated absence rather
    than a silently omitted line.
    """
    directory = Path(directory) if directory is not None else grants_directory()
    try:
        candidates = sorted(directory.glob(RECONCILIATION_GLOB), reverse=True)
    except OSError:
        return None
    for path in candidates:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines):
            if not _APPROVAL_RULE_LABEL.search(line):
                continue
            for candidate in lines[i + 1 : i + 1 + _QUOTE_WINDOW]:
                match = _BLOCKQUOTE.match(candidate)
                if not match:
                    continue
                text = match.group(1).strip().strip('"').strip()
                if len(text) >= _MIN_QUOTE_CHARS:
                    return Cited("approval rule", text, path.name)
    return None


# ── the compliance organ ─────────────────────────────────────────────────────


def _audit(
    root: Path | str | None, directory: Path, now: datetime, supplied: Any
) -> tuple[Any | None, str | None]:
    """Get the compliance position, or say why there isn't one.

    Returns ``(report, blocker)``. ``audit_readiness`` is documented never to
    raise, and its own contract is that a missing source is ``unknown`` rather
    than ``pass`` — so an empty repository yields a real, honestly-failing
    report rather than nothing. The guard here is for the case that contract is
    broken: a compliance organ that explodes must cost the packet its compliance
    section and not the packet.
    """
    if supplied is not None:
        return supplied, None
    try:
        from aureon.grants.compliance import audit_readiness

        return audit_readiness(root, now=now, grants_directory=directory), None
    except Exception as exc:  # noqa: BLE001
        LOG.debug("compliance audit skipped", exc_info=True)
        return None, f"the compliance organ could not be run ({type(exc).__name__}: {exc})"


def _compliance_view(report: Any) -> tuple[str | None, tuple[str, ...], str | None]:
    """Read ``(summary, outstanding items, blocker)`` off a compliance report.

    The summary is derived from :attr:`ComplianceReport.status`, which is a
    property with no setter — there is no code path anywhere, here included,
    that can print ``PASS`` without a check having genuinely passed. Live
    blockers come across with their remedies attached, and sources the auditor
    could not read come across as items in their own right: "we could not check"
    is a finding, not a blank.
    """
    if report is None:
        return None, (), None
    try:
        summary = (
            f"**{str(report.status).upper()}** — {report.passed_count} passed, "
            f"{report.failed_count} failed, {report.unknown_count} unknown; "
            f"{report.blocking_count} live blocker(s)."
        )
        items: list[str] = []
        for check in report.blockers:
            text = f"{check.name}: {check.status} — {check.detail}"
            if check.remedy:
                held = " (no automatic executor — a person's to take)" if check.human_held else ""
                text += f" → {check.remedy}{held}"
            items.append(text)
        items.extend(f"source not read: {p}" for p in report.problems)
    except Exception as exc:  # noqa: BLE001
        LOG.debug("compliance report unreadable", exc_info=True)
        return None, (), f"the compliance report could not be read ({type(exc).__name__}: {exc})"
    return summary, tuple(items), None


# ── the packet ───────────────────────────────────────────────────────────────


def _fit(raw: Any, supplied: FitScore | None) -> tuple[float | None, str | None]:
    """Resolve ``(score, basis)`` — a real measurement, or prose, or nothing.

    A caller who has run :func:`aureon.grants.scout.score_fit` over a retrieved
    call passes the :class:`~aureon.grants.schemas.FitScore` in, and it wins:
    that is the only numeric fit anything in this repository actually measures,
    and it carries its own ``blocker`` when the overlap could not be measured.

    Otherwise the ledger's own ``fit`` is read. It is a *sentence* on 12
    investor routes and absent on every grant application, so it becomes the
    basis and the score stays ``None``. A number is used only when a number is
    what the ledger holds.
    """
    if supplied is not None:
        basis = supplied.blocker
        if supplied.matched_terms:
            shown = ", ".join(supplied.matched_terms[:12])
            more = f" (+{len(supplied.matched_terms) - 12} more)" if len(supplied.matched_terms) > 12 else ""
            overlap = f"overlap on: {shown}{more}"
            basis = f"{basis}; {overlap}" if basis else overlap
        return supplied.score, basis

    value = raw.get("fit") if isinstance(raw, dict) else None
    basis_value = raw.get("fit_basis") if isinstance(raw, dict) else None

    score: float | None = None
    prose: str | None = None
    if isinstance(value, bool):
        # float(True) is 1.0 — a JSON `true` must never become a perfect fit.
        prose = None
    elif isinstance(value, (int, float)):
        # NaN and ±inf are not scores, and neither survives json.dumps as valid
        # JSON — the same rule Application.from_ledger applies to money.
        candidate = float(value)
        score = candidate if math.isfinite(candidate) else None
    elif isinstance(value, str) and value.strip():
        prose = value.strip()

    if prose is None and isinstance(basis_value, str) and basis_value.strip():
        prose = basis_value.strip()
    elif prose is None and isinstance(basis_value, list):
        joined = " ".join(str(b).strip() for b in basis_value if isinstance(b, str) and b.strip())
        prose = joined or None
    return score, prose


def _applicant_facts(root: Path | str | None) -> tuple[tuple[Cited, ...], tuple[str, ...]]:
    """Who the ledger would be submitting as, read from repository documents.

    Not one company detail is written into this file — the identity organ reads
    them at runtime and reports what it could not find. A submission made under
    an entity the organism cannot evidence is exactly the sort of thing an
    approver needs to see before saying yes.
    """
    try:
        from aureon.identity import read_identity

        knowledge = read_identity(root)
    except Exception as exc:  # noqa: BLE001 — self-knowledge must never break the packet
        LOG.debug("identity read skipped", exc_info=True)
        return (), (f"applicant identity could not be read ({type(exc).__name__}: {exc})",)

    facts: list[Cited] = []
    missing: list[str] = []
    identity = knowledge.identity
    for name in identity.COMPANY_FIELDS:
        fact = getattr(identity, name, None)
        label = name.replace("_", " ")
        if fact is None:
            missing.append(f"applicant {label}: no source found in the repository")
        else:
            facts.append(Cited(label, str(fact.value), fact.cite()))
    return tuple(facts), tuple(missing)


def _run_gates(
    app: Application, days: float | None, bus: Any, report: Any
) -> tuple[tuple[GateVerdict, ...], str | None]:
    """The compliance verdict and the Queen's chain, side by side.

    Both are run, and that is the deliberate difference from
    :func:`aureon.grants.compliance.run_gate_chain`, which stops at a live
    compliance blocker so the chain is not spent on a bid that cannot be made.
    Correct for *that* question. This packet answers a different one, and an
    approver who is shown only "compliance blocks" would not be shown the thing
    that decides the packet: that submission has no executor here at all.

    Never fatal — a chain that cannot run costs the packet its verdicts and
    says so, rather than costing the packet.
    """
    context = {
        "action": SUBMIT_ACTION,
        "domain": "grants",
        "application_id": app.id,
        "funder": app.funder,
        "deadline": app.deadline.isoformat() if app.deadline else None,
        "days_remaining": days,
    }
    verdicts: list[GateVerdict] = []
    if report is not None:
        try:
            from aureon.grants.compliance import compliance_verdict

            verdicts.append(compliance_verdict(report))
        except Exception:  # noqa: BLE001
            LOG.debug("compliance verdict skipped", exc_info=True)
    try:
        verdicts.extend(run_chain(context, chain=DEFAULT_CHAIN, bus=bus))
    except Exception as exc:  # noqa: BLE001
        LOG.debug("gate chain failed", exc_info=True)
        return tuple(verdicts), f"the gate chain could not be run ({type(exc).__name__}: {exc})"
    return tuple(verdicts), None


def _dedupe(items: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = item.strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return tuple(out)


def build_dossier(
    application_id: str,
    *,
    root: Path | str | None = None,
    bus: Any = None,
    now: datetime | None = None,
    compliance: Any = None,
    fit: FitScore | None = None,
) -> Dossier | None:
    """Assemble the approval packet for one application.

    Returns ``None`` when the id is not in the ledger — following
    :meth:`Application.from_ledger`, an unknown id yields nothing rather than a
    husk carrying that id and invented fields. Nothing is written here; see
    :func:`write_dossier` and :func:`emit_dossier`.

    ``compliance`` accepts an already-built
    :class:`~aureon.grants.compliance.ComplianceReport`; when omitted the
    auditor is run over ``root``. ``fit`` accepts a
    :class:`~aureon.grants.schemas.FitScore` from
    :func:`aureon.grants.scout.score_fit`; when omitted the score is absent,
    because nothing in the ledger measures one.

    The packet's purpose is to inform Gary's decision, not to replace it: the
    chain is asked about ``submit_application``, which has no executor in this
    repository, so the packet ends in HOLD however strong the evidence is.
    """
    now = now or datetime.now(UTC)
    directory = grants_directory(root)
    state = read_pipeline(now=now, directory=directory)
    if not state.available:
        LOG.warning("no dossier: %s", state.blocker)
        return None

    wanted = str(application_id or "").strip()
    app = next((a for a in state.applications if a.id == wanted), None)
    if app is None:
        # Exact match only. A near-miss must never produce a packet for the
        # wrong application — an approver reading the right name over the wrong
        # evidence is the worst failure this module could have.
        LOG.warning("no dossier: %r is not in %s", wanted, state.ledger_path)
        return None

    raw = _raw_entry(directory, wanted)
    days = app.days_remaining(now)
    fit_score, fit_basis = _fit(raw, fit)

    report, compliance_blocker = _audit(root, directory, now, compliance)
    summary, compliance_items, view_blocker = _compliance_view(report)
    compliance_blocker = compliance_blocker or view_blocker
    verdicts, gate_blocker = _run_gates(app, days, bus, report)

    applicant, applicant_missing = _applicant_facts(root)
    approval_rule = read_approval_rule(directory)

    # ── what is missing, said out loud ───────────────────────────────────────
    outstanding: list[str] = []
    if compliance_blocker:
        outstanding.append(f"compliance position unknown — {compliance_blocker}")
    outstanding.extend(f"compliance: {item}" for item in compliance_items)
    if app.deadline is None:
        outstanding.append("deadline: the ledger holds no parseable deadline date for this application")
    if not app.documents:
        outstanding.append("evidence documents: none are recorded against this application in the ledger")
    if fit_score is None:
        outstanding.append(
            "fit score: not measured — scout.score_fit scores an opportunity's retrieved call "
            "text, the ledger carries none for this application, and no FitScore was supplied"
            + (". The ledger's own fit note is prose, not a score." if fit_basis else "")
        )
    if app.amount_requested is None:
        outstanding.append("amount requested: not recorded in the ledger")
    if app.lifecycle == "unclassified":
        outstanding.append(
            f"status: {app.status!r} could not be classified as live or closed — treated as open"
        )
    outstanding.extend(applicant_missing)
    if approval_rule is None:
        outstanding.append(
            f"approval rule: no {RECONCILIATION_GLOB} in {directory} carries a quotable rule — "
            "the hold below stands on the switchboard alone"
        )
    # The Queen's own chain, separated from the compliance verdict that precedes
    # it: the hold below is a statement about the *submission*, and reading the
    # compliance gate's decision as the chain's terminal would misattribute it.
    chain_verdicts = [v for v in verdicts if v.gate in _CHAIN_GATES]
    terminal = chain_verdicts[-1] if chain_verdicts else None

    if gate_blocker:
        outstanding.append(gate_blocker)
    elif terminal is not None and not terminal.advanced and terminal.decision != HOLD:
        outstanding.append(
            f"gate chain stopped at '{terminal.gate}' with {terminal.decision}: {terminal.reasoning}"
        )
    # Only the Queen's gates contribute dissent here. The compliance gate's
    # dissent *is* its blocker list, already itemised above, and repeating it
    # under a second heading would make one finding look like two.
    for verdict in chain_verdicts:
        outstanding.extend(f"gate '{verdict.gate}' dissent: {d}" for d in verdict.dissent)

    # ── the hold ────────────────────────────────────────────────────────────
    held = is_human_held(SUBMIT_ACTION)
    if held:
        approval_state = HOLD
        reasoning = (
            f"'{SUBMIT_ACTION}' is a human-held action: no automatic executor for it exists "
            "anywhere in this repository, so the packet is held for Gary's approval regardless "
            "of the evidence."
        )
        if terminal is None:
            reasoning += " The gate chain produced no verdict; the hold does not depend on it."
        elif terminal.decision != HOLD:
            # Reported, not hidden: a blind organism REDOs at the first gate
            # before the human-held branch is ever reached, and REDO must not be
            # mistaken for the hold.
            reasoning += (
                f" The chain itself stopped at '{terminal.gate}' with {terminal.decision} "
                f"({terminal.reasoning}); the hold stands independently of that."
            )
        else:
            reasoning += f" The chain agrees, holding at '{terminal.gate}'."
    else:
        approval_state = UNDECIDED
        reasoning = (
            f"'{SUBMIT_ACTION}' is no longer recognised as a human-held action by the "
            "switchboard. This packet cannot vouch for a submission it does not know is held; "
            "treat it as undecided and check aureon.gates.switchboard.HUMAN_HELD."
        )
        outstanding.append(
            f"approval chain: {SUBMIT_ACTION!r} is not recognised as human-held — "
            "the packet's central guarantee is not in force"
        )

    dossier = Dossier(
        application_id=app.id,
        name=app.name,
        funder=app.funder,
        status=app.status,
        lifecycle=app.lifecycle,
        deadline=app.deadline,
        days_remaining=days,
        amount_requested=app.amount_requested,
        currency=app.currency,
        fit_score=fit_score,
        fit_basis=fit_basis,
        compliance=summary,
        compliance_blocker=compliance_blocker,
        evidence_documents=app.documents,
        gate_verdicts=verdicts,
        outstanding=_dedupe(outstanding),
        approval_state=approval_state,
        approval_reasoning=reasoning,
        approval_rule=approval_rule,
        applicant=applicant,
        generated_at=now,
        ledger_path=state.ledger_path,
    )
    _publish(bus, dossier)
    return dossier


def _raw_entry(directory: Path, application_id: str) -> dict[str, Any]:
    """Re-read the ledger row for fields :class:`Application` does not model.

    ``fit`` and ``fit_basis`` exist on a minority of rows and belong to this
    packet rather than to the shared schema. Read here, guarded, so a ledger
    that cannot be re-read costs the packet its fit basis and nothing else.
    """
    try:
        raw = json.loads((directory / LEDGER_NAME).read_text(encoding="utf-8", errors="replace"))
        entries = raw.get("active_applications")
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict) and str(entry.get("id") or "").strip() == application_id:
                    return entry
    except Exception:  # noqa: BLE001
        LOG.debug("raw ledger row unavailable", exc_info=True)
    return {}


def _publish(bus: Any, dossier: Dossier) -> None:
    """Announce the packet on the thought bus. Guarded: never fatal."""
    if bus is None:
        return
    try:
        from aureon.core.aureon_thought_bus import Thought

        bus.publish(Thought(source="grants_dossier", topic=TOPIC_DOSSIER, payload=dossier.to_dict()))
    except Exception:  # noqa: BLE001
        LOG.debug("dossier publish skipped", exc_info=True)


# ── rendering ────────────────────────────────────────────────────────────────


def _money(amount: float | None, currency: str) -> str:
    if amount is None:
        return "not recorded"
    figure = f"{amount:,.0f}" if float(amount).is_integer() else f"{amount:,.2f}"
    return f"{figure} {currency}".strip()


def _pressure(dossier: Dossier) -> str:
    if dossier.deadline is None:
        return "**No parseable deadline in the ledger.** Deadline pressure is unknown, not absent."
    stamp = dossier.deadline.isoformat()
    if dossier.days_remaining is None:
        return f"Deadline {stamp}. Days remaining could not be computed."
    days = dossier.days_remaining
    if days < 0:
        return f"**Deadline {stamp} — passed {abs(days):.1f} days ago.**"
    if days <= 3:
        return f"**Deadline {stamp} — {days:.1f} days remaining.**"
    return f"Deadline {stamp} — {days:.1f} days remaining."


def render_markdown(dossier: Dossier) -> str:
    """One page: what this is, how pressed it is, what is missing, who decides.

    Written for a person who has thirty seconds and a yes/no to give. Every
    unknown is printed as an unknown; there is no section that reads as clean
    because its source was missing.
    """
    title = dossier.name or dossier.application_id
    lines: list[str] = [
        f"# Approval brief — {title}",
        "",
        f"**Application** `{dossier.application_id}`  ",
        f"**Funder** {dossier.funder or 'not recorded'}  ",
        f"**Prepared** {dossier.generated_at.isoformat()} from `{dossier.ledger_path}` (read-only)",
        "",
        "> **This packet exists to inform Gary's decision, not to replace it.**",
        "> Nothing here has been submitted, sent, filed or paid, and nothing in this",
        "> repository can do any of those things. The brief gathers the evidence; the",
        "> call is the director's.",
        "",
        "## What this is",
        "",
        f"- **Ledger status** `{dossier.status or 'not recorded'}` (classified *{dossier.lifecycle}*)",
        f"- **Amount requested** {_money(dossier.amount_requested, dossier.currency)}",
        "",
        "## Deadline pressure",
        "",
        _pressure(dossier),
        "",
        "## Fit",
        "",
    ]

    if dossier.fit_score is not None:
        lines.append(
            f"Fit score **{dossier.fit_score:.2f}** — a measured lexical overlap with the call "
            "text, not a probability of winning."
        )
    else:
        lines.append(
            "**Not scored.** `scout.score_fit` measures overlap against a call's *retrieved "
            "text*, and the ledger carries none for this application; no fit score was supplied "
            "either. No number is reported, because an invented one would be indistinguishable "
            "from a measured one."
        )
    if dossier.fit_basis:
        lines += ["", f"Ledger's own fit note, verbatim: “{dossier.fit_basis}”"]

    lines += ["", "## Compliance", ""]
    if dossier.compliance:
        lines += [
            dossier.compliance,
            "",
            "Live blockers and unread sources are itemised under **Outstanding** below. "
            "An `unknown` check is a blocker: a funder does not accept "
            "\"we could not check\" as an answer.",
        ]
    else:
        lines.append(
            f"**Compliance position could not be read** — {dossier.compliance_blocker or 'reason not recorded'}. "
            "Treat this as unknown, not as clear."
        )

    lines += ["", "## Applicant", ""]
    if dossier.applicant:
        lines += [f"- **{c.label}** {c.value}  \n  *source: {c.source}*" for c in dossier.applicant]
    else:
        lines.append("No applicant identity could be read from this repository's documents.")

    lines += ["", "## Evidence on file", ""]
    if dossier.evidence_documents:
        total = len(dossier.evidence_documents)
        lines.append(f"{total} document(s) recorded against this application in the ledger.")
        lines.append("")
        lines += [f"- `{d}`" for d in dossier.evidence_documents[:_MAX_DOCUMENTS]]
        if total > _MAX_DOCUMENTS:
            lines.append(
                f"- …and {total - _MAX_DOCUMENTS} more, listed in full in the ledger entry."
            )
    else:
        lines.append("None recorded against this application in the ledger.")

    lines += ["", "## Outstanding — what is missing", ""]
    if dossier.outstanding:
        lines += [f"- {item}" for item in dossier.outstanding]
    else:
        lines.append(
            "Nothing was found missing by the checks this packet runs. That is a statement "
            "about what was checked, not a guarantee of completeness."
        )

    lines += [
        "",
        "## Gate chain",
        "",
        "| Gate | Decision | Confidence | Reasoning |",
        "| --- | --- | --- | --- |",
    ]
    if dossier.gate_verdicts:
        for v in dossier.gate_verdicts:
            confidence = "unmeasured" if v.confidence is None else f"{v.confidence:.2f}"
            lines.append(f"| {v.gate} | **{v.decision}** | {confidence} | {v.reasoning} |")
    else:
        lines.append("| — | — | — | the chain produced no verdict |")

    lines += [
        "",
        "## Approval",
        "",
        f"**{dossier.approval_state}.** {dossier.approval_reasoning}",
        "",
    ]
    if dossier.approval_rule:
        lines += [
            f"The operating rule, quoted from `{dossier.approval_rule.source}`:",
            "",
            f"> {dossier.approval_rule.value}",
            "",
        ]
    else:
        lines += [
            "The operating rule could not be read from a reconciliation document in the grants "
            "directory, so it is not quoted here. The hold above does not depend on it.",
            "",
        ]
    lines.append(
        "**Submission requires Gary's approval.** No external submission, filing, payment or "
        "send may be performed by this system. If the answer is yes, a person performs the "
        "submission."
    )
    return "\n".join(lines) + "\n"


# ── writing ──────────────────────────────────────────────────────────────────


def write_dossier(dossier: Dossier | None, *, root: Path | str | None = None) -> Path | None:
    """Write the brief to ``<grants dir>/dossiers/<application_id>.md``.

    ``None`` in, ``None`` out and nothing written — the absent-application case
    reaches here unchanged rather than being turned into an empty file. The only
    path this function ever writes is under ``dossiers/``; ``pipeline.json`` is
    the grant operator's and is never touched.
    """
    if dossier is None:
        return None
    path = dossier_path(dossier.application_id, root=root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown(dossier), encoding="utf-8")
    LOG.info("dossier written: %s", path)
    return path


def emit_dossier(
    application_id: str,
    *,
    root: Path | str | None = None,
    bus: Any = None,
    now: datetime | None = None,
    compliance: Any = None,
    fit: FitScore | None = None,
) -> Path | None:
    """Build and write in one call. ``None`` when the id is not in the ledger."""
    return write_dossier(
        build_dossier(
            application_id, root=root, bus=bus, now=now, compliance=compliance, fit=fit
        ),
        root=root,
    )


__all__ = [
    "Cited",
    "Dossier",
    "DOSSIER_DIRNAME",
    "SUBMIT_ACTION",
    "TOPIC_DOSSIER",
    "UNDECIDED",
    "build_dossier",
    "dossier_path",
    "emit_dossier",
    "grants_directory",
    "read_approval_rule",
    "render_markdown",
    "write_dossier",
]
