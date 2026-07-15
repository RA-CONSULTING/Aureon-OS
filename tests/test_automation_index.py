"""
Automation progress index — one honest number for "how far to fully automated".

Offline + hermetic. Proves the composite is a weight-renormalized mean of only the
dimensions actually present (a dormant dimension is dropped, never counted as zero);
every fraction is clamped to [0,1] and the index to [0,100] or None; a fully dormant
organism reports index_pct None + no_data (never a fabricated score); and the route
mounts on a bare Flask app and never 500s.
"""

from __future__ import annotations

import pytest

from aureon.observer.real_data_contract import TRUTH_STATUSES
from aureon.saas.automation_index import (
    _WEIGHTS,
    _compose,
    automation_index,
    journey,
    record_journey,
)

_DIMS = {"connectivity", "integration", "consciousness", "surfacing"}


# ── the composition math is honest ────────────────────────────────────────────

def test_compose_full_set_is_weighted_mean():
    fr = {"connectivity": 0.0, "integration": 0.0, "consciousness": 1.0, "surfacing": 1.0}
    idx, included = _compose(fr)
    # (0.20*1 + 0.15*1) / 1.0 = 0.35 → 35.0
    assert idx == 35.0 and set(included) == _DIMS


def test_compose_drops_dormant_and_renormalizes():
    # only integration present → the index is exactly that dimension (weights renormalize),
    # never dragged toward zero by the missing three
    idx, included = _compose({"connectivity": None, "integration": 0.5,
                              "consciousness": None, "surfacing": None})
    assert idx == 50.0 and included == ["integration"]


def test_compose_all_dormant_is_none():
    idx, included = _compose({k: None for k in _WEIGHTS})
    assert idx is None and included == []


def test_weights_sum_to_one():
    assert abs(sum(_WEIGHTS.values()) - 1.0) < 1e-9


# ── the live index is bounded + honest ────────────────────────────────────────

def test_index_shape_and_bounds():
    r = automation_index()
    assert set(r["dimensions"]) == _DIMS
    for d in r["dimensions"].values():
        assert d["fraction"] is None or (0.0 <= d["fraction"] <= 1.0)
        assert d["truth_status"] in TRUTH_STATUSES
    assert r["index_pct"] is None or (0.0 <= r["index_pct"] <= 100.0)
    assert r["truth_status"] in TRUTH_STATUSES
    assert isinstance(r["wired_by_category"], dict)


def test_label_band_matches_index():
    r = automation_index()
    pct = r["index_pct"]
    if pct is None:
        assert r["label"] == "dormant"
    else:
        bands = [(10, "nascent"), (30, "emerging"), (60, "developing"),
                 (85, "maturing"), (101, "near-complete")]
        expected = next(name for edge, name in bands if pct < edge)
        assert r["label"] == expected


def test_index_equals_recomputed_mean():
    # the headline must equal the weighted-renormalized mean of the present dimensions
    r = automation_index()
    fr = {k: v["fraction"] for k, v in r["dimensions"].items()}
    recomputed, _ = _compose(fr)
    assert r["index_pct"] == recomputed


def test_dormant_organism_is_no_data(monkeypatch):
    import aureon.saas.automation_index as ai

    monkeypatch.setattr(ai, "_connectome_fractions", lambda: (None, None, {}))
    monkeypatch.setattr(ai, "_consciousness_fraction", lambda: (None, {}))
    monkeypatch.setattr(ai, "_surfacing_fraction", lambda: (None, {}))
    r = ai.automation_index()
    assert r["index_pct"] is None                 # never a fabricated 0
    assert r["label"] == "dormant"
    assert r["truth_status"] == "no_data"
    assert all(d["truth_status"] == "no_data" for d in r["dimensions"].values())


# ── the journey — the climb is recorded and surfaced ──────────────────────────

@pytest.fixture()
def _isolated_trace(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path))
    return tmp_path


def test_journey_records_and_reads_back(_isolated_trace):
    assert journey() == []                         # nothing recorded yet
    s1 = record_journey()
    s2 = record_journey()
    assert s1 and s2 and set(s1) == {"ts", "index_pct", "dims"}
    j = journey()
    assert len(j) == 2 and all("index_pct" in r for r in j)
    # oldest → newest ordering preserved
    assert j[0]["ts"] <= j[-1]["ts"]


def test_dormant_index_is_not_recorded(_isolated_trace, monkeypatch):
    # a dormant organism must not drop a fabricated point onto the journey
    import aureon.saas.automation_index as ai

    monkeypatch.setattr(ai, "automation_index",
                        lambda: {"index_pct": None, "dimensions": {}, "ts": 1.0})
    assert ai.record_journey() is None
    assert ai.journey() == []


def test_index_payload_includes_journey(_isolated_trace):
    record_journey()
    r = automation_index()
    assert isinstance(r["journey"], list) and len(r["journey"]) >= 1


# ── the route mounts on a bare Flask app and never 500s ───────────────────────

def _saas_client():
    flask = pytest.importorskip("flask", reason="SaaS gateway requires the `.[operator]` extra")
    from aureon.saas.gateway import register_saas_routes

    app = flask.Flask(__name__)
    register_saas_routes(app)
    return app.test_client()


def test_automation_route():
    r = _saas_client().get("/api/automation")
    assert r.status_code == 200
    body = r.get_json()
    assert set(body["dimensions"]) == _DIMS
    assert "provenance" in body and body["truth_status"] in TRUTH_STATUSES
    assert body["index_pct"] is None or (0.0 <= body["index_pct"] <= 100.0)
