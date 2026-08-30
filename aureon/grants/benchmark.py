"""Grant-organ benchmark — does the organism actually see its own funding pipeline?

Follows the repo's benchmark contract (see :mod:`aureon.design.benchmark` and
``scripts/validation/benchmark_live_multidaemon.py``): a tiered check list, a
``.json`` + ``.md`` pair with the same stem under ``docs/research/benchmarks/``,
and ``status == "pass"`` iff every *critical* check is ok.

It exercises the **real** organ against the **real** ledger — 66 applications and
~1,100 dated artifacts under ``data/research/grants/`` — rather than a fixture.
That is the point: the capability being measured is "can Aureon read its own
pipeline", and a fixture would measure the fixture.

The critical tier is the trust surface, and every check in it is a property the
organ's own docstrings promise:

- the configured ledger is reachable, and reading it **does not change a byte**
  (the whole organ is built on being read-only; submission stays Gary's);
- ``AUREON_GRANTS_DIR`` is honoured verbatim — a wrong path becomes a loud
  blocker, never a silent fallback into the repo ledger;
- absent urgency stays ``None``, because absent and calm are different things;
- alerts only ever describe an open, dated application, at the right severity;
- the breath interval stays inside its bounds and tightens monotonically as the
  deadline nears.

Counts, timings and the current urgency are informational: they are real, they
move between runs, and a change in them is news rather than a failure.

Offline and network-free; safe for nightly CI.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from aureon.grants.daemon import (
    MAX_INTERVAL_S,
    MIN_INTERVAL_S,
    TOPIC_ALERT,
    TOPIC_PULSE,
    breath_interval,
    run_once,
)
from aureon.grants.ledger import LEDGER_NAME, configured_routes, grants_dir, read_pipeline
from aureon.grants.schemas import Application, PipelineState

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORTS_DIR = REPO_ROOT / "docs" / "research" / "benchmarks"
REPORT_STEM = "grant_organ_benchmark"
NAME = "aureon-grant-organ-benchmark"

# The urgency sweep the breath curve is measured across. ``None`` first: an
# unknown pipeline must breathe slowest, not fastest.
URGENCY_SWEEP: tuple[float | None, ...] = (None, 0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0)

# Mirrors ledger._SEVERITY_BANDS. Duplicated deliberately: an independent
# restatement is what makes the band check evidence rather than a tautology.
_EXPECTED_BANDS = ((0.0, "overdue"), (3.0, "critical"), (7.0, "urgent"), (30.0, "approaching"))


class _RecordingBus:
    """A thought bus that only remembers. Enough for ``run_once`` to publish into."""

    def __init__(self) -> None:
        self.thoughts: list[Any] = []

    def publish(self, thought: Any) -> None:
        self.thoughts.append(thought)

    def topics(self) -> list[str]:
        return [getattr(t, "topic", "") for t in self.thoughts]


def _check(
    name: str,
    ok: bool,
    detail: str,
    *,
    critical: bool = True,
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "check": name,
        "ok": bool(ok),
        "critical": bool(critical),
        "detail": detail,
        "metrics": metrics or {},
    }


def _expected_severity(days: float) -> str | None:
    for limit, band in _EXPECTED_BANDS:
        if days <= limit:
            return band
    return None


def _digest(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _display(path: str | Path) -> str:
    """Repo-relative when it is inside the repo, absolute when it is not.

    Keeps the report readable and stable across machines without ever hiding a
    path that points *outside* the repo — which is exactly the case a reader
    needs to see.
    """
    try:
        return Path(path).resolve().relative_to(REPO_ROOT).as_posix()
    except (ValueError, OSError):
        return str(path)


# ─── the checks ────────────────────────────────────────────────────


def _check_ledger_reachable(state: PipelineState, elapsed_ms: float) -> list[dict[str, Any]]:
    """The configured ledger resolves, opens, and parses into applications."""
    checks = [
        _check(
            "ledger_reachable",
            state.available,
            (
                f"read {len(state.applications)} application(s) from {_display(state.ledger_path)}"
                if state.available
                else f"unavailable: {state.blocker}"
            ),
            metrics={
                "ledger_path": _display(state.ledger_path),
                "available": state.available,
                "blocker": state.blocker,
                "read_ms": round(elapsed_ms, 2),
            },
        )
    ]

    identified = [a for a in state.applications if a.id.strip()]
    checks.append(
        _check(
            "applications_carry_identity",
            bool(state.applications) and len(identified) == len(state.applications),
            f"{len(identified)}/{len(state.applications)} application(s) carry a non-empty id",
            metrics={"application_count": len(state.applications), "identified": len(identified)},
        )
    )
    return checks


def _check_readonly(state: PipelineState) -> dict[str, Any]:
    """Reading the pipeline — including a full daemon breath — must not edit it.

    The organ's entire licence to run unattended is that it never touches the
    ledger. This hashes the file, drives ``run_once`` (the daemon's real unit,
    publish and subfield contribution included), and hashes it again.
    """
    ledger = Path(state.ledger_path) if state.ledger_path else grants_dir() / LEDGER_NAME
    before = _digest(ledger)
    if before is None:
        return _check("ledger_read_is_readonly", False, f"could not hash ledger at {ledger}")

    bus = _RecordingBus()
    try:
        run_once(bus)
        read_pipeline()
    except Exception as exc:  # noqa: BLE001 — a raising organ is itself the finding
        return _check("ledger_read_is_readonly", False, f"read raised {type(exc).__name__}: {exc}")

    after = _digest(ledger)
    return _check(
        "ledger_read_is_readonly",
        before == after,
        (
            "ledger byte-identical after a full daemon breath"
            if before == after
            else "LEDGER MUTATED by a read — the read-only guarantee is broken"
        ),
        metrics={"sha256_prefix": before[:16], "unchanged": before == after},
    )


def _check_override_honoured() -> dict[str, Any]:
    """``AUREON_GRANTS_DIR`` is obeyed verbatim — no silent fallback.

    A caller who asks for directory X must not quietly be handed directory Y.
    The failure mode this guards against is real: the configured path once
    pointed at an empty leftover directory while the live ledger sat elsewhere,
    and a fallback would have hidden that instead of surfacing it.
    """
    previous = os.environ.get("AUREON_GRANTS_DIR")
    try:
        with tempfile.TemporaryDirectory(prefix="aureon-grants-bench-") as tmp:
            os.environ["AUREON_GRANTS_DIR"] = tmp
            resolved = grants_dir()
            state = read_pipeline()
            honoured = resolved == Path(tmp)
            refused = (not state.available) and tmp in (state.blocker or "")
            return _check(
                "grants_dir_override_honoured",
                honoured and refused,
                (
                    "AUREON_GRANTS_DIR pointed at an empty directory: resolved verbatim, reported "
                    "unavailable, and the blocker names that exact path — no silent fallback to the repo ledger"
                    if honoured and refused
                    else f"override resolved to {resolved}; available={state.available}; blocker={state.blocker}"
                ),
                metrics={"resolved_verbatim": honoured, "blocker_names_path": refused},
            )
    finally:
        if previous is None:
            os.environ.pop("AUREON_GRANTS_DIR", None)
        else:
            os.environ["AUREON_GRANTS_DIR"] = previous


def _check_absence_is_not_calm() -> dict[str, Any]:
    """An open pipeline with no dated application has urgency ``None``, not 0.0."""
    now = datetime.now(UTC)
    undated = PipelineState(
        available=True,
        generated_at=now,
        applications=(
            Application(id="undated-1", name="No deadline recorded", status="DRAFTING"),
            Application(id="undated-2", name="Also undated", status="IN_PROGRESS"),
        ),
    )
    dated = PipelineState(
        available=True,
        generated_at=now,
        applications=(
            Application(id="dated-1", status="DRAFTING", deadline=now + timedelta(days=15)),
        ),
    )
    absent_ok = undated.urgency is None and undated.open_count == 2
    dated_ok = dated.urgency is not None and 0.49 < dated.urgency < 0.51
    return _check(
        "urgency_absent_is_not_calm",
        absent_ok and dated_ok,
        (
            f"2 open undated applications -> urgency None; one 15-day deadline -> {dated.urgency}"
            if absent_ok
            else f"undated urgency was {undated.urgency!r} (expected None)"
        ),
        metrics={"undated_urgency": undated.urgency, "dated_15d_urgency": dated.urgency},
    )


def _check_alerts_well_formed(state: PipelineState) -> dict[str, Any]:
    """Every alert names an open, dated application at the correct severity band."""
    if not state.available:
        return _check("alerts_well_formed", False, "no pipeline to validate alerts against")

    by_id = {a.id: a for a in state.applications}
    faults: list[str] = []
    for alert in state.alerts:
        app = by_id.get(alert.application_id)
        if app is None:
            faults.append(f"{alert.application_id}: no such application")
            continue
        if not app.is_open:
            faults.append(f"{alert.application_id}: closed ({app.status})")
        if app.deadline is None:
            faults.append(f"{alert.application_id}: alerted without a deadline")
            continue
        expected = _expected_severity(alert.days_remaining)
        if expected != alert.severity:
            faults.append(
                f"{alert.application_id}: {alert.days_remaining:.2f}d banded '{alert.severity}', expected '{expected}'"
            )

    ordered = all(
        state.alerts[i].days_remaining <= state.alerts[i + 1].days_remaining
        for i in range(len(state.alerts) - 1)
    )
    if not ordered:
        faults.append("alerts not sorted by days_remaining")

    return _check(
        "alerts_well_formed",
        not faults,
        (
            f"{len(state.alerts)} alert(s) all open, dated, correctly banded and sorted"
            if not faults
            else "; ".join(faults[:4])
        ),
        metrics={"alert_count": len(state.alerts), "fault_count": len(faults), "sorted": ordered},
    )


def _check_mixed_shapes_tolerated() -> dict[str, Any]:
    """The ledger really does mix dicts and bare strings; neither may raise."""
    hostile = ["a bare string", 42, None, [], {}, {"id": "   "}, {"id": "ok", "amount_requested": "not-a-number"}]
    try:
        built = [Application.from_ledger(entry) for entry in hostile]
    except Exception as exc:  # noqa: BLE001
        return _check("mixed_ledger_shapes_tolerated", False, f"from_ledger raised {type(exc).__name__}: {exc}")

    survivors = [a for a in built if a is not None]
    ok = len(survivors) == 1 and survivors[0].id == "ok" and survivors[0].amount_requested is None
    return _check(
        "mixed_ledger_shapes_tolerated",
        ok,
        (
            "7 malformed entries yielded 1 real application and 6 Nones — no husks with invented fields"
            if ok
            else f"{len(survivors)} survivor(s): {[a.id for a in survivors]}"
        ),
        metrics={"entries": len(hostile), "survivors": len(survivors)},
    )


def _check_breath_curve() -> list[dict[str, Any]]:
    """The φ-scaled breath must stay bounded and tighten as pressure rises."""
    curve = {("unknown" if u is None else f"{u:.2f}"): round(breath_interval(u), 2) for u in URGENCY_SWEEP}
    values = list(curve.values())

    bounded = all(MIN_INTERVAL_S <= v <= MAX_INTERVAL_S for v in values)
    dated = [breath_interval(u) for u in URGENCY_SWEEP if u is not None]
    monotonic = all(dated[i] > dated[i + 1] for i in range(len(dated) - 1))
    unknown_slowest = breath_interval(None) == MAX_INTERVAL_S and breath_interval(None) >= max(dated)
    clamped = breath_interval(-5.0) == breath_interval(0.0) and breath_interval(9.9) == breath_interval(1.0)

    return [
        _check(
            "breath_interval_bounded",
            bounded,
            f"all {len(values)} sampled intervals within [{MIN_INTERVAL_S:.0f}s, {MAX_INTERVAL_S:.0f}s]",
            metrics={"min_s": min(values), "max_s": max(values), "bounds": [MIN_INTERVAL_S, MAX_INTERVAL_S]},
        ),
        _check(
            "breath_tightens_with_urgency",
            monotonic,
            f"strictly decreasing across urgency 0→1: {dated[0]:.0f}s → {dated[-1]:.0f}s",
            metrics={"curve_s": curve},
        ),
        _check(
            "unknown_urgency_breathes_slowest",
            unknown_slowest,
            f"urgency None -> {breath_interval(None):.0f}s (the ceiling), slower than any measured urgency",
        ),
        _check(
            "breath_input_clamped",
            clamped,
            "out-of-range urgency (-5.0, 9.9) clamps to the 0.0 / 1.0 endpoints rather than escaping the curve",
            critical=False,
        ),
        _check(
            "breath_curve_span",
            True,
            f"measured span {min(dated):.0f}s–{max(dated):.0f}s; the {MIN_INTERVAL_S:.0f}s floor is not reached at urgency 1.0",
            critical=False,
            metrics={
                "fastest_measured_s": round(min(dated), 2),
                "slowest_measured_s": round(max(dated), 2),
                "floor_s": MIN_INTERVAL_S,
                "floor_reached": min(dated) <= MIN_INTERVAL_S,
            },
        ),
    ]


def _check_daemon_publishes(state: PipelineState) -> dict[str, Any]:
    """One breath publishes exactly one pulse plus one alert per pressing deadline."""
    bus = _RecordingBus()
    try:
        breathed = run_once(bus)
    except Exception as exc:  # noqa: BLE001
        return _check("daemon_breath_publishes", False, f"run_once raised {type(exc).__name__}: {exc}")

    topics = bus.topics()
    pulses = topics.count(TOPIC_PULSE)
    alerts = topics.count(TOPIC_ALERT)
    pressing = sum(1 for a in breathed.alerts if a.severity in ("overdue", "critical"))
    ok = pulses == 1 and alerts == pressing
    return _check(
        "daemon_breath_publishes",
        ok,
        (
            f"1 × {TOPIC_PULSE} + {alerts} × {TOPIC_ALERT} for {pressing} overdue/critical deadline(s)"
            if ok
            else f"{pulses} pulse(s), {alerts} alert(s), expected 1 and {pressing}"
        ),
        metrics={"pulses": pulses, "alerts_published": alerts, "pressing_deadlines": pressing},
    )


def _informational(state: PipelineState, elapsed_ms: float) -> list[dict[str, Any]]:
    """Counts and timings: real, moving, and news rather than failure."""
    severities: dict[str, int] = {}
    for alert in state.alerts:
        severities[alert.severity] = severities.get(alert.severity, 0) + 1

    soonest = min(
        (a.days_remaining(state.generated_at) for a in state.applications if a.is_open and a.deadline),
        default=None,
    )
    funders = {a.funder for a in state.applications if a.funder}
    routes = configured_routes()

    return [
        _check(
            "pipeline_population",
            True,
            f"{len(state.applications)} application(s) parsed ({state.skipped_entries} ledger "
            f"entry/entries carried no application data): {state.open_count} open, "
            f"{len(state.applications) - state.open_count} closed, across {len(funders)} funder(s). "
            f"{state.unrecognised_status_count} status(es) are free text this code cannot classify, "
            f"so that much of 'open' is the unknown-means-open default, not a measurement",
            critical=False,
            metrics={
                "application_count": len(state.applications),
                "skipped_entries": state.skipped_entries,
                "open_count": state.open_count,
                "closed_count": len(state.applications) - state.open_count,
                "unrecognised_status_count": state.unrecognised_status_count,
                "funder_count": len(funders),
            },
        ),
        _check(
            "artifact_count",
            True,
            f"{state.artifact_count} dated artifact(s) beside the ledger",
            critical=False,
            metrics={"artifact_count": state.artifact_count},
        ),
        _check(
            "pipeline_urgency",
            True,
            (
                f"urgency {state.urgency:.4f}; nearest open deadline {soonest:.2f} day(s) away"
                if state.urgency is not None and soonest is not None
                else "no dated open application — urgency is unknown, not calm"
            ),
            critical=False,
            metrics={
                "urgency": round(state.urgency, 4) if state.urgency is not None else None,
                "soonest_open_deadline_days": round(soonest, 2) if soonest is not None else None,
                "breath_interval_s": round(breath_interval(state.urgency), 2),
                "subfield_life_score": (
                    round(1.0 - state.urgency, 4) if state.urgency is not None else None
                ),
            },
        ),
        _check(
            "alert_severity_distribution",
            True,
            ", ".join(f"{k}={v}" for k, v in sorted(severities.items())) or "no alerts in band",
            critical=False,
            metrics={"severities": severities, "alert_count": len(state.alerts)},
        ),
        _check(
            "configured_routes",
            True,
            f"{len(routes)} AUREON_GRANT_* / AUREON_IFS_* route variable(s) set in this environment",
            critical=False,
            metrics={"route_count": len(routes), "route_keys": sorted(routes)},
        ),
        _check(
            "ledger_read_latency",
            True,
            f"full reconcile of {len(state.applications)} application(s) + "
            f"{state.artifact_count} artifact scan in {elapsed_ms:.1f} ms",
            critical=False,
            metrics={"read_ms": round(elapsed_ms, 2)},
        ),
    ]


# ─── orchestration ─────────────────────────────────────────────────


def _check_alert_path_against_fixture() -> dict[str, Any]:
    """Drive the alert path from a ledger with KNOWN deadlines.

    The live-ledger alert checks pass vacuously when there are no alerts — and
    that is exactly CI's configuration: the committed pipeline.json carries 7
    applications and produces zero. A total regression in banding, ordering or
    emission would still have shipped `status: pass`. This check builds a ledger
    whose every band is populated, so the alert path cannot be green by absence.
    """
    now = datetime(2026, 7, 31, 12, 0, 0, tzinfo=UTC)
    rows = [
        {"id": "FX-OVERDUE", "name": "o", "funder": "f", "status": "DRAFT",
         "deadline": (now - timedelta(days=5)).isoformat()},
        {"id": "FX-CRITICAL", "name": "c", "funder": "f", "status": "DRAFT",
         "deadline": (now + timedelta(days=2)).isoformat()},
        {"id": "FX-URGENT", "name": "u", "funder": "f", "status": "DRAFT",
         "deadline": (now + timedelta(days=5)).isoformat()},
        {"id": "FX-APPROACHING", "name": "a", "funder": "f", "status": "DRAFT",
         "deadline": (now + timedelta(days=20)).isoformat()},
        {"id": "FX-FARFUTURE", "name": "n", "funder": "f", "status": "DRAFT",
         "deadline": (now + timedelta(days=400)).isoformat()},
        {"id": "FX-CLOSED", "name": "s", "funder": "f", "status": "SUBMITTED",
         "deadline": (now - timedelta(days=9)).isoformat()},
    ]
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "pipeline.json").write_text(
            json.dumps({"active_applications": rows}), encoding="utf-8")
        state = read_pipeline(now=now, directory=Path(tmp))

    got = [(a.application_id, a.severity) for a in state.alerts]
    want = [("FX-OVERDUE", "overdue"), ("FX-CRITICAL", "critical"),
            ("FX-URGENT", "urgent"), ("FX-APPROACHING", "approaching")]
    ok = got == want and state.urgency == 1.0
    detail = (f"{len(got)} alert(s) in every band, correctly ordered and banded; "
              f"far-future and closed excluded; urgency={state.urgency}")
    if not ok:
        detail = f"expected {want}, got {got} (urgency={state.urgency})"
    return _check("alert_path_exercised", ok, detail, critical=True,
                  metrics={"alerts": len(got), "expected": len(want)})


def run_grants_benchmark() -> list[dict[str, Any]]:
    """Exercise the real grant organ against the real ledger; return tiered checks.

    Runs with its bus-trace directory redirected to a temporary path. The organ's
    real unit, ``run_once``, publishes an HNC subfield, and ``publish_subfield``
    appends to ``state/symbolic_subfield.jsonl`` — so benchmarking wrote 75 rows
    of source "grants" into the organism's live trace. Worse, the nightly job
    runs this benchmark before the gates one, so the gates panel was reading a
    subfield THIS benchmark had just written and counting it as a live
    measurement. Measuring must not move what is measured.
    """
    with tempfile.TemporaryDirectory() as trace_dir:
        previous = os.environ.get("AUREON_BUS_TRACE_DIR")
        os.environ["AUREON_BUS_TRACE_DIR"] = trace_dir
        try:
            return _collect_grants_checks()
        finally:
            if previous is None:
                os.environ.pop("AUREON_BUS_TRACE_DIR", None)
            else:
                os.environ["AUREON_BUS_TRACE_DIR"] = previous


def _collect_grants_checks() -> list[dict[str, Any]]:
    started = time.perf_counter()
    state = read_pipeline()
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    checks: list[dict[str, Any]] = []
    checks.extend(_check_ledger_reachable(state, elapsed_ms))
    checks.append(_check_readonly(state))
    checks.append(_check_override_honoured())
    checks.append(_check_absence_is_not_calm())
    checks.append(_check_alerts_well_formed(state))
    checks.append(_check_alert_path_against_fixture())
    checks.append(_check_mixed_shapes_tolerated())
    checks.extend(_check_breath_curve())
    checks.append(_check_daemon_publishes(state))
    checks.extend(_informational(state, elapsed_ms))
    return checks


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    """Assemble the canonical report dict from a check list."""
    critical = [c for c in checks if c["critical"]]
    info = [c for c in checks if not c["critical"]]
    critical_passed = sum(1 for c in critical if c["ok"])
    info_passed = sum(1 for c in info if c["ok"])
    return {
        "name": NAME,
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            # A report with no critical checks has proven nothing. `0 == 0` made
            # build_report([]) return "pass", so a benchmark that silently
            # stopped collecting checks would ship green.
            "status": "pass" if critical and critical_passed == len(critical) else "fail",
            "critical_passed": critical_passed,
            "critical_total": len(critical),
            "informational_passed": info_passed,
            "informational_total": len(info),
            "check_count": len(checks),
        },
        "checks": checks,
    }


def _render_markdown(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# Aureon Grant Organ — Benchmark",
        "",
        f"- **Status**: `{s['status']}`",
        f"- **Generated**: {report['generated_at']}",
        f"- **Critical**: {s['critical_passed']}/{s['critical_total']} passed",
        f"- **Informational**: {s['informational_passed']}/{s['informational_total']} passed",
        "",
        "The grant organ reads `data/research/grants/pipeline.json` — the real ledger the",
        "operator runs have been writing for months — and contributes its deadline pressure",
        "to the HNC field as a subfield. This benchmark runs against that live ledger, not a",
        "fixture: the capability under measurement is *can Aureon see its own funding",
        "pipeline*, and a fixture would only measure the fixture.",
        "",
        "Critical checks are the trust surface — the ledger is reachable, a read changes",
        "nothing, a misconfigured path fails loudly instead of silently reading somewhere",
        "else, absent urgency stays absent, and alerts only ever describe an open, dated",
        "application. Informational checks are the live counts and timings, which move",
        "between runs by design.",
        "",
        "| Check | Tier | Result | Detail |",
        "| --- | --- | --- | --- |",
    ]
    for c in report["checks"]:
        tier = "critical" if c["critical"] else "info"
        mark = "✅" if c["ok"] else ("❌" if c["critical"] else "⚠️")
        detail = str(c["detail"]).replace("|", "\\|")
        lines.append(f"| `{c['check']}` | {tier} | {mark} | {detail} |")
    lines.append("")

    curve = next(
        (c["metrics"].get("curve_s") for c in report["checks"] if c["check"] == "breath_tightens_with_urgency"),
        None,
    )
    if curve:
        lines.extend(
            [
                "## Breath curve",
                "",
                "φ-scaled interval between ledger reads, driven by real deadline pressure.",
                "",
                "| Urgency | Interval (s) |",
                "| --- | --- |",
            ]
        )
        lines.extend(f"| {k} | {v} |" for k, v in curve.items())
        lines.append("")

    lines.append("*Generated by `python -m aureon.grants.benchmark`.*")
    lines.append("")
    return "\n".join(lines)


def _write_artifacts(report: dict[str, Any], *, reports_dir: Path | None = None) -> list[str]:
    """Write the ``.json`` + ``.md`` pair; returns the paths written."""
    target = reports_dir or DEFAULT_REPORTS_DIR
    target.mkdir(parents=True, exist_ok=True)
    json_path = target / f"{REPORT_STEM}.json"
    md_path = target / f"{REPORT_STEM}.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    return [str(json_path), str(md_path)]


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint: run, write artefacts, exit non-zero on critical failure."""
    checks = run_grants_benchmark()
    report = build_report(checks)
    written = _write_artifacts(report)
    s = report["summary"]
    print(
        f"{NAME}: {s['status']} — critical {s['critical_passed']}/{s['critical_total']}, "
        f"info {s['informational_passed']}/{s['informational_total']}"
    )
    for c in checks:
        mark = "PASS" if c["ok"] else ("FAIL" if c["critical"] else "warn")
        tier = "  " if c["critical"] else " ~"
        print(f" {tier} [{mark}] {c['check']:34} {c['detail']}")
    for path in written:
        print(f"  wrote {path}")
    return 0 if s["status"] == "pass" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "NAME",
    "REPORT_STEM",
    "DEFAULT_REPORTS_DIR",
    "URGENCY_SWEEP",
    "run_grants_benchmark",
    "build_report",
    "main",
]
