"""The grant organ: reads the real ledger, never invents one.

Hermetic — every test builds its own ledger in tmp_path and points
AUREON_GRANTS_DIR at it, so nothing depends on the repo's live pipeline.json.
Proves the organ reports absence as absence, never fabricates urgency, honours
the read-only contract, and paces its own breath from real deadline pressure.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta, timezone

import pytest

from aureon.grants.daemon import breath_interval, run_once
from aureon.grants.ledger import read_pipeline
from aureon.grants.schemas import Application, parse_dt

NOW = datetime(2026, 7, 31, 12, 0, 0, tzinfo=UTC)


def _ledger(tmp_path, applications):
    (tmp_path / "pipeline.json").write_text(
        json.dumps({"operator": "Aureon", "active_applications": applications}), encoding="utf-8"
    )
    return tmp_path


def _app(app_id, *, status="DRAFT", days=None, name="X", funder="F"):
    out = {"id": app_id, "name": name, "funder": funder, "status": status}
    if days is not None:
        out["deadline"] = (NOW + timedelta(days=days)).isoformat()
    return out


@pytest.fixture(autouse=True)
def _point_at_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_GRANTS_DIR", str(tmp_path))
    return tmp_path


# ── absence is reported as absence ───────────────────────────────────────────

def test_missing_ledger_is_unavailable_not_empty(tmp_path):
    s = read_pipeline(now=NOW)
    assert s.available is False
    assert s.blocker and "not found" in s.blocker
    # An absent ledger must never look like a healthy, empty pipeline.
    assert s.applications == () and s.urgency is None


def test_malformed_ledger_is_unavailable(tmp_path):
    (tmp_path / "pipeline.json").write_text("{not json", encoding="utf-8")
    s = read_pipeline(now=NOW)
    assert s.available is False and "unreadable" in s.blocker


def test_no_dated_open_application_yields_no_urgency(tmp_path):
    _ledger(tmp_path, [_app("A1", status="DRAFT")])  # open, but no deadline
    s = read_pipeline(now=NOW)
    assert s.available is True and s.open_count == 1
    # Unknown pressure is None, never 0.0 — absent and calm are different.
    assert s.urgency is None
    assert s.alerts == ()


# ── the ledger's real shapes ─────────────────────────────────────────────────

def test_non_dict_entries_are_skipped_not_coerced(tmp_path):
    # active_applications genuinely mixes dicts and bare strings.
    _ledger(tmp_path, [_app("A1", days=5), "IFS_PORTAL_PROGRESS_20260710", {"no_id": True}])
    s = read_pipeline(now=NOW)
    assert [a.id for a in s.applications] == ["A1"]


def test_closed_applications_raise_no_alert(tmp_path):
    _ledger(tmp_path, [_app("A1", status="SUBMITTED", days=-30)])
    s = read_pipeline(now=NOW)
    assert s.open_count == 0 and s.alerts == () and s.urgency is None


def test_parse_dt_rejects_junk_rather_than_defaulting_to_now():
    assert parse_dt("not a date") is None
    assert parse_dt("") is None and parse_dt(None) is None
    assert parse_dt("2026-07-31T12:00:00+01:00") is not None
    # Naive stamps are assumed UTC so comparisons never raise.
    assert parse_dt("2026-07-31T12:00:00").tzinfo is not None


# ── severity + urgency are functions of real deadlines ───────────────────────

@pytest.mark.parametrize(
    "days,severity",
    [(-1, "overdue"), (0, "overdue"), (2, "critical"), (5, "urgent"), (20, "approaching")],
)
def test_severity_bands(tmp_path, days, severity):
    _ledger(tmp_path, [_app("A1", days=days)])
    s = read_pipeline(now=NOW)
    assert [a.severity for a in s.alerts] == [severity]


def test_far_future_deadline_raises_no_alert(tmp_path):
    _ledger(tmp_path, [_app("A1", days=120)])
    s = read_pipeline(now=NOW)
    assert s.alerts == () and s.urgency == 0.0


def test_urgency_saturates_when_overdue(tmp_path):
    _ledger(tmp_path, [_app("A1", days=-5)])
    assert read_pipeline(now=NOW).urgency == 1.0


def test_alerts_are_ordered_most_pressing_first(tmp_path):
    _ledger(tmp_path, [_app("A1", days=6), _app("A2", days=-2), _app("A3", days=1)])
    s = read_pipeline(now=NOW)
    assert [a.application_id for a in s.alerts] == ["A2", "A3", "A1"]


# ── the organ paces itself ───────────────────────────────────────────────────

def test_breath_quickens_with_urgency():
    calm, pressed = breath_interval(0.0), breath_interval(1.0)
    assert pressed < calm
    # Unknown pressure must not be mistaken for calm: it breathes slowest.
    assert breath_interval(None) >= calm


def test_breath_is_always_within_bounds():
    from aureon.grants.daemon import MAX_INTERVAL_S, MIN_INTERVAL_S

    for u in (None, -5.0, 0.0, 0.5, 1.0, 99.0):
        assert MIN_INTERVAL_S <= breath_interval(u) <= MAX_INTERVAL_S


# ── read-only contract ───────────────────────────────────────────────────────

def test_run_once_never_writes_to_the_ledger(tmp_path):
    _ledger(tmp_path, [_app("A1", days=-1)])
    ledger = tmp_path / "pipeline.json"
    before = ledger.read_bytes()
    listing_before = sorted(p.name for p in tmp_path.iterdir())

    state = run_once(bus=None, now=NOW)

    assert state.available is True and len(state.alerts) == 1
    # Submission and application state belong to the operator and to Gary.
    assert ledger.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == listing_before


def test_run_once_survives_a_broken_bus(tmp_path):
    _ledger(tmp_path, [_app("A1", days=2)])

    class Exploding:
        def publish(self, *a, **k):
            raise RuntimeError("bus down")

    # Awareness must never crash the organ.
    assert run_once(bus=Exploding(), now=NOW).available is True


def test_application_days_remaining_is_none_without_a_deadline():
    assert Application(id="A1").days_remaining(NOW) is None


# ── regression: audit findings ───────────────────────────────────────────────

def test_urgency_horizon_is_a_horizon_not_a_measurement(tmp_path):
    # 31 days and 1000 days are indistinguishable once past the 30-day horizon.
    # 0.0 therefore means "beyond the horizon", never "no deadline" — that is None.
    _ledger(tmp_path, [_app("A1", days=1000)])
    assert read_pipeline(now=NOW).urgency == 0.0
    _ledger(tmp_path, [_app("A1")])
    assert read_pipeline(now=NOW).urgency is None


def test_urgency_is_continuous_across_the_deadline(tmp_path):
    # No step at zero: a deadline a heartbeat away and one a heartbeat past
    # both read as fully urgent, rather than jumping between bands.
    _ledger(tmp_path, [_app("A1", days=1e-9)])
    assert read_pipeline(now=NOW).urgency == pytest.approx(1.0)
    _ledger(tmp_path, [_app("A1", days=-1e-9)])
    assert read_pipeline(now=NOW).urgency == 1.0


def test_urgency_ignores_undated_applications_but_not_dated_ones(tmp_path):
    # min() over the generator must skip undated entries, not be defeated by them.
    _ledger(tmp_path, [_app("A1"), _app("A2", days=10), _app("A3")])
    assert read_pipeline(now=NOW).urgency == pytest.approx(1.0 - 10 / 30)


def test_one_stale_overdue_application_pins_urgency(tmp_path):
    # Documented behaviour, pinned so a future change is deliberate: urgency 1.0
    # says "something is overdue", not "something is imminent".
    _ledger(tmp_path, [_app("ancient", days=-4000), _app("later", days=25)])
    s = read_pipeline(now=NOW)
    assert s.urgency == 1.0
    assert [a.application_id for a in s.alerts] == ["ancient", "later"]


def test_ledger_entries_that_yield_no_application_are_counted(tmp_path):
    # The live ledger holds 68 entries of which 2 are bare id strings. Reporting
    # 66 applications without saying 2 were dropped presents a partial read as
    # a complete one.
    _ledger(tmp_path, [_app("A1"), "APP-BARE-STRING-ID", {"no_id": True}, 42])
    s = read_pipeline(now=NOW)
    assert len(s.applications) == 1
    assert s.skipped_entries == 3
    assert s.to_dict()["skipped_entries"] == 3


def test_unrecognised_statuses_are_reported_not_silently_called_open(tmp_path):
    # Only exact terminal states are classifiable. The live ledger's compound
    # free-text statuses are not, and open_count must not pass them off as a
    # measurement of openness.
    _ledger(tmp_path, [
        _app("A1", status="SUBMITTED"),
        _app("A2", status="SERAPHIM_CONTACT_SUBMITTED_ROUTE_REQUESTED_WAITING_REPLY"),
        _app("A3", status="FOUNDER_ONLY_FORM_POLICY_GATE_NOT_SUBMITTED_BY_OPERATOR"),
        _app("A4", status="ENTIRELY_NOVEL_STATE_NO_MARKER_MATCHES"),
    ])
    s = read_pipeline(now=NOW)
    # A2/A3 are now genuinely classified live (waiting a reply; not yet
    # submitted), so only the novel A4 remains a default rather than a reading.
    assert s.open_count == 3
    assert s.unrecognised_status_count == 1
    assert s.to_dict()["unrecognised_status_count"] == 1


@pytest.mark.parametrize("status", ["submitted ", "Submitted", " SUBMITTED\t", "sUbMiTtEd"])
def test_closed_state_matching_normalises_case_and_whitespace(status):
    assert Application(id="A1", status=status).is_open is False
    assert Application(id="A1", status=status).status_recognised is True


@pytest.mark.parametrize("status,lifecycle", [
    # Live markers take precedence over terminal ones: a status saying both
    # "submitted" and "waiting reply" is waiting. This is the case that makes
    # naive substring matching wrong, and the reason for the ordering.
    ("SERAPHIM_SPACE_CONTACT_SUBMITTED_DECK_ROUTE_REQUESTED_WAITING_REPLY", "live"),
    ("TECHSTART_OUTBOUND_QUEUE_READY_RAISE_AMOUNT_REQUIRED_NOT_SUBMITTED", "live"),
    ("AIRR_RAPID_ACCESS_RESUBMITTED_RECEIPT_VERIFIED_AWAITING_REVIEW", "live"),
    # Unambiguously terminal — corroborated against the War Room sheet, which
    # confirms AKT 6 expired and the ACTASAP call closed.
    ("AKT6_DEADLINE_PASSED_NO_KB_LEAD_NO_SAFE_SUBMISSION", "closed"),
    ("ACTASAP_CURRENT_CALL_CLOSED_FUTURE_ROUTE_ONLY", "closed"),
    ("QUB_KTP_FINANCE_GATE_NO_APPLICATION_CREATED", "closed"),
    # Neither vocabulary matches: unclassified is a real answer, not "open".
    ("", "unclassified"),
    ("ENTIRELY_NOVEL_STATE_NO_MARKER_MATCHES", "unclassified"),
])
def test_compound_statuses_are_classified_by_marker_precedence(status, lifecycle):
    app = Application(id="A1", status=status)
    assert app.lifecycle == lifecycle
    # is_open stays conservative: only a *classified* terminal state closes it,
    # so an unclassified status still keeps its deadline visible.
    assert app.is_open is (lifecycle != "closed")
    assert app.status_recognised is (lifecycle != "unclassified")


def test_amount_requested_accepts_a_numeric_string_and_rejects_non_amounts():
    assert Application.from_ledger({"id": "x", "amount_requested": "500000"}).amount_requested == 500000.0
    assert Application.from_ledger({"id": "x", "amount_requested": 42}).amount_requested == 42.0
    for junk in (True, False, "nan", "inf", "-inf", "1e400", "£500,000", [1], {"a": 1}):
        got = Application.from_ledger({"id": "x", "amount_requested": junk}).amount_requested
        assert got is None, f"{junk!r} became {got!r} — a fabricated money figure"


def test_amount_requested_survives_json_round_trip():
    # A NaN would serialise as bare `NaN`, which is not valid JSON, so any
    # consumer of to_dict() would produce an unparseable payload.
    app = Application.from_ledger({"id": "x", "amount_requested": "nan"})
    json.loads(json.dumps(app.to_dict()))


def test_breath_curve_reaches_neither_clamp_across_the_real_range():
    from aureon.grants.daemon import BASE_INTERVAL_S, MAX_INTERVAL_S, MIN_INTERVAL_S
    from aureon.harmonic.phi_bridge import PHI

    sampled = [breath_interval(i / 200) for i in range(201)]
    # Strictly decreasing everywhere, and the clamp is monotone so it cannot invert.
    assert all(sampled[i] > sampled[i + 1] for i in range(len(sampled) - 1))
    # The documented band. urgency 1.0 lands on BASE/φ, NOT on MIN_INTERVAL_S —
    # the constants are guard rails, not the operating range, and the docstring
    # must keep saying so.
    assert sampled[0] == pytest.approx(BASE_INTERVAL_S * PHI)
    assert breath_interval(0.5) == pytest.approx(BASE_INTERVAL_S)
    assert sampled[-1] == pytest.approx(BASE_INTERVAL_S / PHI)
    assert min(sampled) > MIN_INTERVAL_S and max(sampled) < MAX_INTERVAL_S
    # Unknown urgency is the only way to reach the ceiling.
    assert breath_interval(None) == MAX_INTERVAL_S
