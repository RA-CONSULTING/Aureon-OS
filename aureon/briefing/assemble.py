"""Assemble the context brief from the organs that already know the answers.

The owner wrote a handoff prompt by hand — who he is, what the decision spine
is, what is built, the standing rule, the live deadlines, the positioning, the
claim discipline — and then said: teach Aureon to carry this out. Every one of
those paragraphs already exists inside the organism as a *reading*. Typing them
into a prompt turns a live reading into a stale sentence, and a stale sentence
about a deadline is the most expensive kind of stale there is.

So this module composes; it does not restate. Nothing about the company appears
in this file — not a name, a number, a date, a sector, a positioning phrase.
Point :func:`assemble_brief` at an empty directory and it returns a brief with
no sections and a blocker for each one, which is the correct answer.

Where each section comes from
-----------------------------
============================  =================================================
``identity``                  :func:`aureon.identity.reader.read_identity` —
                              company facts, mission and purpose, each with the
                              document it was read from
``live_priorities``           :func:`aureon.grants.ledger.read_pipeline`'s own
                              deadline alerts (real ``days_remaining``) **plus**
                              every live blocking check from
                              :func:`aureon.grants.compliance.audit_readiness`.
                              The Companies House item therefore appears because
                              a document said so, never because it was typed
``positioning``               the grant thesis, verbatim, via
                              :func:`aureon.grants.scout.read_capability`
``claim_discipline``          the claim-discipline rule, verbatim, same organ
``standing_rule``             :func:`aureon.grants.dossier.read_approval_rule`,
                              which exists to quote that rule verbatim; the
                              auditor's ``human_approval_rule`` check is the
                              fallback because it also reads the applicant record
``spine``                     a live reading — Γ and divergence from
                              :mod:`aureon.core.hnc_field`, consensus and
                              grounding from :mod:`aureon.gates.panel`, the
                              decision vocabulary and chain read off
                              :mod:`aureon.gates.switchboard` itself
``capabilities_built``        a filesystem probe: packages that exist under
                              ``aureon/`` and carry a test module under
                              ``tests/`` — never a list written down here
============================  =================================================

Two rules that shape the whole module
-------------------------------------
**A missing source produces a blocker, not a sentence.** Every section is built
by a helper that returns ``(value, blockers)``; a helper that could not read its
source returns nothing and says why. :func:`render_markdown` and
:func:`render_prompt` then omit the section rather than paper over it.

**The two verbatim rules are never paraphrased.** The standing rule and the
claim discipline are carried as exact strings from the document that states them,
and the renderers print them unwrapped. The one piece of surgery performed on
either is the removal of the auditor's own ``(corroborated by …)`` suffix from
the approval-rule detail — that suffix is the auditor's annotation, not the
owner's words, and the sources it names are preserved in
:attr:`~aureon.briefing.schemas.Brief.sources`.

No LLM is involved. :mod:`aureon.inhouse_ai.llm_adapter` runs a small local
model, and a small local model asked to summarise a compliance blocker will
eventually produce a fluent sentence nobody can source. The brief is assembled
by reading; the *stronger* model is the consumer of the output, not a step in
producing it.

Read-only throughout. Nothing here writes to the ledger, and it never touches
``pipeline.json`` — that file is the grant operator's and is written live.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterable

from aureon.briefing.schemas import Brief, Capability, Priority, SourcedLine, severity_rank

LOG = logging.getLogger("aureon.briefing.assemble")

# aureon/briefing/assemble.py -> parents[2] is the repository root.
REPO_ROOT = Path(__file__).resolve().parents[2]

GRANTS_SUBDIR = ("data", "research", "grants")
PACKAGE_DIR = "aureon"
TESTS_DIR = "tests"

# The auditor's own name for the check that quotes the approval rule. A code-level
# identifier from :mod:`aureon.grants.compliance`, not a phrase from the company's
# documents — the rule's text is always read, never named here.
APPROVAL_CHECK = "human_approval_rule"

# The auditor appends this to a check's detail when a second document agrees. It
# is the auditor's annotation, so it is stripped before the rule is presented as
# verbatim, and the sources it names are kept.
_CORROBORATION = re.compile(r"\s*\(corroborated by (?P<sources>[^)]*)\)\s*$")

# An unambiguous ISO date inside a quoted finding. Used only when the finding
# contains exactly one, so that a date can never be picked out of a list of them.
_ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")

# Organs named as the provenance of a live reading. Paths, so a reader can go and
# look at the code that took the measurement.
FIELD_SOURCE = "aureon/core/hnc_field.py::read_canonical_field"
BLEND_SOURCE = "aureon/core/hnc_field.py::blend_field"
PANEL_SOURCE = "aureon/gates/panel.py::auris_panel"
SWITCHBOARD_SOURCE = "aureon/gates/switchboard.py"
CONSCIENCE_MODULE = "aureon.queen.queen_conscience"

_SPINE_ORGANS = "aureon/gates/switchboard.py::read_organism"


# ── small helpers ────────────────────────────────────────────────────────────


def _rel(path: Any, root: Path) -> str:
    """``path`` relative to ``root`` when it is inside it, else unchanged.

    Provenance has to be findable, and a repo-relative path is findable from any
    machine. A path outside the root is left absolute rather than mangled with
    ``..`` segments, because at that point the absolute form is the honest one.
    """
    try:
        candidate = Path(str(path))
    except (TypeError, ValueError):
        return str(path)
    try:
        return candidate.resolve().relative_to(root.resolve()).as_posix()
    except (ValueError, OSError):
        return str(path)


def _humanise(name: str) -> str:
    return str(name or "").replace("_", " ").strip()


def _single_iso_date(text: str) -> datetime | None:
    """The one ISO date in ``text``, or ``None`` if there is not exactly one.

    Deliberately refuses the ambiguous cases. A finding quoting two dates does
    not tell this code which one is the deadline, and choosing would be inventing
    a measurement; a finding quoting none simply has no date. Both come back
    ``None``, and the priority then carries ``days_remaining=None`` — which the
    model treats as a real answer rather than a gap to fill.
    """
    found = _ISO_DATE.findall(text or "")
    if len(found) != 1:
        return None
    year, month, day = found[0]
    try:
        return datetime(int(year), int(month), int(day), tzinfo=UTC)
    except ValueError:
        return None


def _ledger_dir(root: Path, root_given: bool, grants_directory: Path | str | None) -> Path:
    """Where to look for the ledger, following the auditor's rule exactly.

    An explicit ``grants_directory`` wins. Otherwise, when the caller left
    ``root`` at its default, the operator's configured ``AUREON_GRANTS_DIR`` is
    honoured — that is where the rest of the organ already looks. When ``root``
    *was* supplied the ledger is looked for underneath it and the environment is
    ignored, so a test passing ``tmp_path`` cannot reach the live pipeline. This
    is :func:`aureon.grants.compliance.audit_readiness`'s rule, reused rather
    than re-decided.
    """
    if grants_directory is not None:
        return Path(grants_directory)
    if not root_given:
        try:
            from aureon.grants.ledger import grants_dir

            return grants_dir()
        except Exception:  # noqa: BLE001
            LOG.debug("grants_dir unavailable", exc_info=True)
    return root.joinpath(*GRANTS_SUBDIR)


# ── identity ─────────────────────────────────────────────────────────────────


def identity_lines(root: Path, *, now: datetime) -> tuple[tuple[SourcedLine, ...], list[str], list[str]]:
    """Who this is, read from the repository's own documents.

    Returns ``(lines, sources, blockers)``. One line per fact, labelled with the
    field it answers, so nothing is composed into a sentence the documents did
    not support. A field with no source contributes a blocker naming what the
    identity organ looked in.
    """
    try:
        from aureon.identity.reader import read_identity
    except Exception as exc:  # noqa: BLE001
        return (), [], [f"identity: organ unavailable ({type(exc).__name__}: {exc})"]

    knowledge = read_identity(root, now=now)
    lines: list[SourcedLine] = []
    sources: list[str] = []
    for name, fact in knowledge.identity.known.items():
        lines.append(SourcedLine(text=f"{_humanise(name)}: {fact.value}", source=fact.source_file))
        sources.append(fact.source_file)
    for goal in knowledge.goals:
        lines.append(SourcedLine(text=f"goal: {goal.value}", source=goal.source_file))
        sources.append(goal.source_file)

    blockers = [f"identity: {b}" for b in knowledge.blockers]
    if not lines:
        blockers.append(f"identity: nothing could be read under {root}")
    return tuple(lines), sources, blockers


# ── the decision spine, as a live reading ────────────────────────────────────


def spine_lines(
    bus: Any = None,
    *,
    organism_reader: Callable[[Any], Any] | None = None,
) -> tuple[tuple[SourcedLine, ...], list[str], list[str]]:
    """Describe the spine from what it currently reads, not from prose about it.

    ``organism_reader`` defaults to
    :func:`aureon.gates.switchboard.read_organism`, which already composes the
    field, the blended subfields and the Auris panel into one reading — so the
    panel is convened once per brief, not once per line. It is injectable so a
    test can pin the reading instead of depending on whatever the live organism
    happens to be doing.

    A value that could not be read is stated as unreadable *in the section* and
    recorded as a blocker. That is the one case where a line's text describes an
    absence: a spine section that silently omitted Γ would read as though Γ were
    fine.
    """
    lines: list[SourcedLine] = []
    sources: list[str] = []
    blockers: list[str] = []

    reader = organism_reader
    if reader is None:
        try:
            from aureon.gates.switchboard import read_organism

            reader = read_organism
        except Exception as exc:  # noqa: BLE001
            return (), [], [f"spine: switchboard unavailable ({type(exc).__name__}: {exc})"]

    try:
        reading = reader(bus)
    except Exception as exc:  # noqa: BLE001
        return (), [], [f"spine: reading the organism failed ({type(exc).__name__}: {exc})"]

    coherence = getattr(reading, "coherence", None)
    if coherence is None:
        lines.append(SourcedLine(
            text="HNC coherence Γ: not readable in this pass — the canonical field returned no value",
            source=FIELD_SOURCE,
        ))
        blockers.append(f"spine: coherence Γ unreadable ({FIELD_SOURCE})")
    else:
        lines.append(SourcedLine(text=f"HNC coherence Γ = {coherence:.4f} (live)", source=FIELD_SOURCE))
    sources.append(FIELD_SOURCE)

    life = getattr(reading, "life_score", None)
    if life is not None:
        lines.append(SourcedLine(text=f"symbolic life score = {life:.4f} (live)", source=FIELD_SOURCE))

    divergence = getattr(reading, "divergence", None)
    if divergence is None:
        lines.append(SourcedLine(
            text="field divergence: not measured in this pass — self-agreement was never checked",
            source=BLEND_SOURCE,
        ))
        blockers.append(f"spine: divergence unmeasured ({BLEND_SOURCE})")
    else:
        lines.append(SourcedLine(
            text=f"field divergence = {divergence:.4f} (live; the spread between the organism's subfields)",
            source=BLEND_SOURCE,
        ))
    sources.append(BLEND_SOURCE)

    consensus = getattr(reading, "panel_consensus", None)
    confidence = getattr(reading, "panel_confidence", None)
    evidence = getattr(reading, "panel_evidence", None)
    if consensus is None and confidence is None:
        lines.append(SourcedLine(
            text="Auris panel: could not be convened in this pass",
            source=PANEL_SOURCE,
        ))
        blockers.append(f"spine: panel not convened ({PANEL_SOURCE})")
    else:
        try:
            from aureon.gates.panel import NODE_SLICE, PANEL_INPUTS

            nodes, inputs = len(NODE_SLICE), PANEL_INPUTS
        except Exception:  # noqa: BLE001
            nodes, inputs = 0, 0
        node_text = f"{nodes}-node " if nodes else ""
        parts = [f"Auris {node_text}panel: consensus {consensus or 'not reported'}"]
        if confidence is not None:
            parts.append(f"confidence {confidence:.2f}")
        if evidence is None:
            parts.append("grounding unknown — treated as none by the gates")
            blockers.append(f"spine: panel evidence ratio unknown ({PANEL_SOURCE})")
        elif inputs:
            parts.append(f"{evidence:.0%} of its {inputs} inputs came from a real measurement")
        else:
            parts.append(f"evidence ratio {evidence:.2f}")
        lines.append(SourcedLine(text=", ".join(parts), source=PANEL_SOURCE))
    sources.append(PANEL_SOURCE)

    # Structural facts, read off the switchboard's own objects rather than
    # described. If the vocabulary or the chain changes, this changes with it.
    try:
        from aureon.gates.switchboard import ADVANCE, DEFAULT_CHAIN, HOLD, HUMAN_HELD, REDO

        lines.append(SourcedLine(
            text=f"one decision vocabulary for every lane: {ADVANCE} / {REDO} / {HOLD}",
            source=SWITCHBOARD_SOURCE,
        ))
        chain = " -> ".join(g.name for g in DEFAULT_CHAIN)
        held = [g.name for g in DEFAULT_CHAIN if g.requires_human]
        held_text = (f"; {', '.join(held)} is human-held whatever the evidence" if held else "")
        lines.append(SourcedLine(text=f"gate chain: {chain}{held_text}", source=SWITCHBOARD_SOURCE))
        lines.append(SourcedLine(
            text="steps with no automatic executor anywhere in this repository: "
                 + ", ".join(sorted(HUMAN_HELD)),
            source=SWITCHBOARD_SOURCE,
        ))
        sources.append(SWITCHBOARD_SOURCE)
    except Exception as exc:  # noqa: BLE001
        blockers.append(f"spine: gate vocabulary unreadable ({type(exc).__name__}: {exc})")

    # The conscience is reported as *present*, which is all that was measured.
    # It was not consulted in this pass, and the reading above does not carry a
    # conscience verdict, so no line here claims one.
    origin = _module_origin(CONSCIENCE_MODULE)
    if origin is None:
        blockers.append(f"spine: Queen-conscience module {CONSCIENCE_MODULE} does not resolve")
    else:
        rel = _rel(origin, REPO_ROOT)
        lines.append(SourcedLine(
            text=f"Queen-conscience veto: {CONSCIENCE_MODULE} resolves on this machine "
                 "(present — not consulted by the reading above)",
            source=rel,
        ))
        sources.append(rel)

    return tuple(lines), sources, blockers


def _module_origin(dotted: str) -> str | None:
    """Where the import system says a module lives, or ``None``.

    ``find_spec`` locates without executing. A heavyweight package's import side
    effects are not something a briefing should trigger, and "the module resolves"
    is the only claim made from it.
    """
    try:
        spec = importlib.util.find_spec(dotted)
    except Exception:  # noqa: BLE001 — a broken parent package is a "no", not a crash
        return None
    if spec is None:
        return None
    return spec.origin or None


# ── what is actually built ───────────────────────────────────────────────────


def _import_tree() -> Path | None:
    """The repository root the import system would resolve ``aureon`` inside."""
    try:
        spec = importlib.util.find_spec(PACKAGE_DIR)
    except Exception:  # noqa: BLE001
        return None
    if spec is None or not spec.origin:
        return None
    try:
        return Path(spec.origin).resolve().parent.parent
    except (OSError, ValueError):
        return None


def pytest_runner(root: Path | str, *, timeout: float = 900.0) -> Callable[[str, Path], bool | None]:
    """A real test runner for :func:`probe_capabilities`, opt-in.

    Returns a callable that runs ``pytest -q`` over one package's test directory
    in a subprocess. ``True`` is a clean exit and ``False`` is a real test failure;
    ``None`` covers every case where the question was not answered — pytest
    missing, a timeout, an OS error, an internal error, or nothing collected.
    That distinction is the point: only one of the three is a statement about the
    code, and a brief that turned "could not run" into "failing" would be as wrong
    as one that turned it into "passing".

    The offline environment flags are set explicitly so the probe cannot reach the
    network or trip import side effects, matching how this repository's suite is
    expected to be run.
    """
    root_path = Path(root)

    def run(package: str, test_dir: Path) -> bool | None:
        env = dict(os.environ)
        env.update({
            "AUREON_LLM_OFFLINE": "1",
            "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS": "1",
            "AUREON_AUDIT_MODE": "1",
            "PYTHONIOENCODING": "utf-8",
        })
        try:
            done = subprocess.run(  # noqa: S603 — fixed argv, no shell
                [sys.executable, "-m", "pytest", str(test_dir), "-q"],
                cwd=str(root_path),
                env=env,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        except Exception:  # noqa: BLE001
            LOG.debug("pytest probe for %s could not run", package, exc_info=True)
            return None
        # pytest's own exit vocabulary, mapped rather than reduced to a boolean.
        # 0 is a pass and 1 is a real failure; everything else (interrupted,
        # internal error, usage error, nothing collected) means the question was
        # not answered, and answering it "failing" would be a claim about the code
        # that the run did not make.
        if done.returncode == 0:
            return True
        if done.returncode == 1:
            return False
        LOG.debug("pytest probe for %s exited %s", package, done.returncode)
        return None

    return run


def probe_capabilities(
    root: Path,
    *,
    test_runner: Callable[[str, Path], bool | None] | None = None,
) -> tuple[tuple[Capability, ...], list[str], list[str]]:
    """Find out what this repository actually carries, by looking at it.

    The rule, stated so a reader can check it: a package counts when
    ``<root>/aureon/<name>/__init__.py`` exists **and**
    ``<root>/tests/<name>/`` holds at least one ``test_*.py``. Both halves are
    filesystem facts. There is no list of packages in this file, so a new organ
    with a test directory appears here the day it lands and a deleted one
    disappears — which is the difference between a probe and a claim.

    Importability is measured only when ``root`` is the same tree the import
    system resolves ``aureon`` inside. Under any other root it is reported as
    unmeasured, because importing ``aureon.<name>`` would then be a statement
    about a *different* copy of the code than the one on disk here.

    Pass/fail of the test modules is ``None`` unless ``test_runner`` actually ran
    them. A test file's existence is not a passing test, and this is the section
    where that overstatement would be easiest to make.
    """
    package_root = root / PACKAGE_DIR
    tests_root = root / TESTS_DIR
    blockers: list[str] = []
    if not package_root.is_dir():
        blockers.append(f"capabilities_built: no package directory at {package_root}")
    if not tests_root.is_dir():
        blockers.append(f"capabilities_built: no test directory at {tests_root}")
    if blockers:
        return (), [], blockers

    tree = _import_tree()
    same_tree = tree is not None and tree == root.resolve()
    if same_tree:
        probe = "importlib.util.find_spec — module located, not executed"
    else:
        probe = (f"not measured: {root} is not the tree the import system resolves "
                 f"aureon inside ({tree or 'unresolved'})")

    found: list[Capability] = []
    sources: list[str] = []
    try:
        candidates = sorted(p for p in package_root.iterdir() if p.is_dir())
    except OSError as exc:
        return (), [], [f"capabilities_built: {package_root} unreadable ({type(exc).__name__}: {exc})"]

    for package in candidates:
        if not (package / "__init__.py").is_file():
            continue
        test_dir = tests_root / package.name
        if not test_dir.is_dir():
            continue
        try:
            modules = tuple(sorted(m.name for m in test_dir.glob("test_*.py")))
        except OSError:
            continue
        if not modules:
            continue

        importable: bool | None = None
        if same_tree:
            importable = _module_origin(f"{PACKAGE_DIR}.{package.name}") is not None

        verified: bool | None = None
        verification = ""
        if test_runner is not None:
            try:
                verified = test_runner(package.name, test_dir)
            except Exception as exc:  # noqa: BLE001 — one bad probe must not end the brief
                verified = None
                blockers.append(
                    f"capabilities_built: test probe for {package.name} failed "
                    f"({type(exc).__name__}: {exc})"
                )
            if verified is None:
                verification = "test run attempted but produced no result"
            else:
                verification = f"pytest -q {_rel(test_dir, root)}"

        source = f"{_rel(package, root)}/__init__.py + {_rel(test_dir, root)}/"
        sources.append(source)
        found.append(Capability(
            package=f"{PACKAGE_DIR}.{package.name}",
            test_modules=modules,
            importable=importable,
            probe=probe,
            tests_verified=verified,
            verification=verification,
            source=source,
        ))

    if not found:
        blockers.append(
            f"capabilities_built: no package under {package_root} has a matching test "
            f"directory under {tests_root} — the section is omitted rather than guessed"
        )
    return tuple(found), sources, blockers


# ── the priorities ───────────────────────────────────────────────────────────


def live_priorities(
    root: Path,
    *,
    now: datetime,
    root_given: bool = True,
    grants_directory: Path | str | None = None,
    report: Any = None,
) -> tuple[tuple[Priority, ...], list[str], list[str]]:
    """What is pressing, measured twice over from two different organs.

    The ledger's own deadline alerts supply the dated items — ``days_remaining``
    is the alert's real number, not a re-derivation — and the auditor's live
    blocking checks supply the undated ones. Nothing is merged or deduplicated
    between them: they answer different questions, and an item that appears in
    both is a corroboration a reader should see.

    ``report`` lets a caller pass a compliance report already computed, so the
    audit runs once per brief.
    """
    priorities: list[Priority] = []
    sources: list[str] = []
    blockers: list[str] = []
    ledger_dir = _ledger_dir(root, root_given, grants_directory)

    try:
        from aureon.grants.ledger import read_pipeline
    except Exception as exc:  # noqa: BLE001
        blockers.append(f"live_priorities: ledger organ unavailable ({type(exc).__name__}: {exc})")
    else:
        state = read_pipeline(now, directory=ledger_dir)
        ledger_source = _rel(state.ledger_path, root)
        if not state.available:
            blockers.append(
                f"live_priorities: pipeline unreadable — {state.blocker or 'no reason recorded'}"
            )
        else:
            sources.append(ledger_source)
            for alert in state.alerts:
                detail = f"{alert.application_id}"
                if alert.funder:
                    detail += f" · {alert.funder}"
                detail += f" · deadline {alert.deadline.isoformat()} as recorded in the ledger"
                priorities.append(Priority(
                    label=alert.name or alert.application_id,
                    detail=detail,
                    days_remaining=alert.days_remaining,
                    severity=alert.severity,
                    source=ledger_source,
                ))
            if not state.alerts:
                blockers.append(
                    f"live_priorities: {ledger_source} carries no dated open application inside "
                    "the alerting horizon — no deadline pressure was measured (this is a reading, "
                    "not an assurance)"
                )

    audit = report
    if audit is None:
        try:
            from aureon.grants.compliance import audit_readiness
        except Exception as exc:  # noqa: BLE001
            blockers.append(f"live_priorities: auditor unavailable ({type(exc).__name__}: {exc})")
            audit = None
        else:
            audit = audit_readiness(
                root if root_given else None,
                now=now,
                grants_directory=grants_directory,
            )

    if audit is not None:
        try:
            from aureon.grants.compliance import UNKNOWN
        except Exception:  # noqa: BLE001 — unreachable while a report exists
            UNKNOWN = "unknown"  # the auditor's own vocabulary, mirrored only as a last resort
        for check in audit.blockers:
            # Status maps straight onto severity: a read negative is a blocker, an
            # unread source is an unknown. The auditor's contract is that the
            # second is not clearance, so it is carried as a priority too.
            severity = UNKNOWN if check.status == UNKNOWN else "blocker"
            detail = check.detail
            if check.remedy:
                detail += f" — remedy: {check.remedy}"
                if check.human_held:
                    detail += " (no automatic executor — a person's to take)"
            dated = _single_iso_date(check.detail)
            source = check.source or f"{_rel(getattr(audit, 'ledger_path', ''), root)} (unread)"
            priorities.append(Priority(
                label=_humanise(check.name),
                detail=detail,
                days_remaining=((dated - now).total_seconds() / 86400.0 if dated else None),
                severity=severity,
                source=source,
            ))
            if check.source:
                sources.append(check.source)
        for problem in getattr(audit, "problems", ()):
            blockers.append(f"live_priorities: compliance source unread — {problem}")

    priorities.sort(key=lambda p: (
        severity_rank(p.severity),
        p.days_remaining if p.days_remaining is not None else float("inf"),
        p.label,
    ))
    if not priorities and not blockers:
        blockers.append("live_priorities: nothing measurable was found")
    return tuple(priorities), sources, blockers


# ── the quoted rules ─────────────────────────────────────────────────────────


def standing_rule(
    root: Path,
    *,
    now: datetime,
    root_given: bool = True,
    grants_directory: Path | str | None = None,
    report: Any = None,
) -> tuple[SourcedLine | None, list[str], list[str], Any]:
    """The approval rule, verbatim, out of the document that states it.

    Returns ``(line, sources, blockers, report)`` — the audit report comes back so
    the caller can reuse it for :func:`live_priorities` instead of auditing twice.

    Two organs can answer this and they are tried in a stated order rather than
    merged:

    1. :func:`aureon.grants.dossier.read_approval_rule`, which exists to quote
       this exact rule out of the newest reconciliation document and returns it
       clean, with the filename it came from. Preferred because it needs no
       post-processing to stay verbatim.
    2. the auditor's ``human_approval_rule`` check, which reads the same
       reconciliation *and* the applicant record's automation policy — a document
       the first path does not open. Its ``detail`` may carry the auditor's own
       ``(corroborated by …)`` annotation, which is removed so the quote stays
       exact; the sources it named are kept.

    Only a ``pass`` yields a rule. An ``unknown`` means no document could be read
    stating one, and answering that with a rule of this module's own composition
    would be the fabrication the check exists to prevent — the caller renders a
    fail-closed instruction instead, marked as an instruction.
    """
    ledger_dir = _ledger_dir(root, root_given, grants_directory)
    try:
        from aureon.grants.dossier import read_approval_rule
    except Exception:  # noqa: BLE001
        LOG.debug("dossier approval-rule reader unavailable", exc_info=True)
    else:
        quoted = read_approval_rule(ledger_dir)
        if quoted is not None and str(quoted.value or "").strip():
            return (
                SourcedLine(text=quoted.value.strip(), source=quoted.source),
                [quoted.source],
                [],
                report,
            )

    audit = report
    if audit is None:
        try:
            from aureon.grants.compliance import audit_readiness
        except Exception as exc:  # noqa: BLE001
            return None, [], [f"standing_rule: auditor unavailable ({type(exc).__name__}: {exc})"], None
        audit = audit_readiness(
            root if root_given else None,
            now=now,
            grants_directory=grants_directory,
        )

    check = next((c for c in audit.checks if c.name == APPROVAL_CHECK), None)
    if check is None:
        return None, [], [f"standing_rule: the auditor ran no {APPROVAL_CHECK} check"], audit
    if not check.cleared or not check.source:
        return None, [], [
            f"standing_rule: not readable — {check.detail}"
        ], audit

    match = _CORROBORATION.search(check.detail)
    text = _CORROBORATION.sub("", check.detail).strip()
    sources = [check.source]
    if match:
        sources.extend(s.strip() for s in match.group("sources").split(",") if s.strip())
    if not text:
        return None, [], ["standing_rule: the auditor quoted an empty rule"], audit
    return SourcedLine(text=text, source=check.source), sources, [], audit


def positioning_and_claims(
    root: Path,
) -> tuple[SourcedLine | None, SourcedLine | None, list[str], list[str]]:
    """The positioning line and the claim-discipline rule, both verbatim.

    Both come from :func:`aureon.grants.scout.read_capability`, which reads them
    out of the reconciliation report and carries them exactly. Neither is
    rewritten here, and an absent row yields ``None`` plus a blocker — a
    positioning sentence composed by this module would be a marketing claim
    wearing a citation.
    """
    try:
        from aureon.grants.scout import RECONCILIATION_DOC, read_capability
    except Exception as exc:  # noqa: BLE001
        return None, None, [], [f"positioning: scout unavailable ({type(exc).__name__}: {exc})"]

    profile = read_capability(root)
    sources: list[str] = []
    blockers: list[str] = []

    thesis: SourcedLine | None = None
    if profile.thesis:
        thesis = SourcedLine(text=profile.thesis, source=RECONCILIATION_DOC)
        sources.append(RECONCILIATION_DOC)
    else:
        blockers.append(
            f"positioning: no grant-thesis row could be read from {RECONCILIATION_DOC} "
            f"under {root}"
        )

    claims: SourcedLine | None = None
    if profile.claim_discipline:
        claims = SourcedLine(text=profile.claim_discipline, source=RECONCILIATION_DOC)
        sources.append(RECONCILIATION_DOC)
    else:
        blockers.append(
            f"claim_discipline: no claim-discipline row could be read from "
            f"{RECONCILIATION_DOC} under {root}"
        )

    if profile.blocker:
        blockers.append(f"capability profile: {profile.blocker}")
    return thesis, claims, sources, blockers


# ── the assembly ─────────────────────────────────────────────────────────────


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    """Distinct values, first-seen order preserved."""
    out: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in out:
            out.append(text)
    return tuple(out)


def assemble_brief(
    root: Path | str | None = None,
    bus: Any = None,
    *,
    now: datetime | None = None,
    grants_directory: Path | str | None = None,
    organism_reader: Callable[[Any], Any] | None = None,
    test_runner: Callable[[str, Path], bool | None] | None = None,
    verify_tests: bool = False,
) -> Brief:
    """Assemble the whole brief from live organs. Never raises.

    ``root`` is honoured verbatim — it is never widened to the real repository
    when a document is missing there. That rule is inherited from
    :func:`aureon.grants.ledger.grants_dir`, :func:`aureon.identity.reader.read_identity`
    and :func:`aureon.grants.compliance.audit_readiness`, all of which learned it
    the same expensive way: a reader that reaches for the live repo when the
    caller's directory is bare passes its tests on real company data and hides
    the fault it was meant to expose.

    ``verify_tests`` opts into really running each probed package's test module
    with :func:`pytest_runner`. It is off by default because it is slow, and with
    it off no line in the brief claims a passing test suite.

    The compliance audit runs **once** and is shared between the standing rule
    and the priorities. Two audits of the same documents in one brief could
    disagree if a file changed between them, and a brief that contradicts itself
    is worse than one that is merely incomplete.
    """
    now = now or datetime.now(UTC)
    root_given = root is not None
    root_path = REPO_ROOT if root is None else Path(root)

    sources: list[str] = []
    blockers: list[str] = []

    identity, ident_sources, ident_blockers = identity_lines(root_path, now=now)
    sources += ident_sources
    blockers += ident_blockers

    rule, rule_sources, rule_blockers, report = standing_rule(
        root_path, now=now, root_given=root_given, grants_directory=grants_directory
    )
    sources += rule_sources
    blockers += rule_blockers

    priorities, prio_sources, prio_blockers = live_priorities(
        root_path,
        now=now,
        root_given=root_given,
        grants_directory=grants_directory,
        report=report,
    )
    sources += prio_sources
    blockers += prio_blockers

    thesis, claims, pos_sources, pos_blockers = positioning_and_claims(root_path)
    sources += pos_sources
    blockers += pos_blockers

    spine, spine_sources, spine_blockers = spine_lines(bus, organism_reader=organism_reader)
    sources += spine_sources
    blockers += spine_blockers

    runner = test_runner
    if runner is None and verify_tests:
        runner = pytest_runner(root_path)
    capabilities, cap_sources, cap_blockers = probe_capabilities(root_path, test_runner=runner)
    sources += cap_sources
    blockers += cap_blockers

    return Brief(
        identity=identity,
        spine=spine,
        capabilities_built=capabilities,
        standing_rule=rule,
        live_priorities=priorities,
        positioning=thesis,
        claim_discipline=claims,
        generated_at=now,
        sources=_dedupe(sources),
        blockers=_dedupe(blockers),
    )


__all__ = [
    "APPROVAL_CHECK",
    "REPO_ROOT",
    "assemble_brief",
    "identity_lines",
    "live_priorities",
    "positioning_and_claims",
    "probe_capabilities",
    "pytest_runner",
    "spine_lines",
    "standing_rule",
]
