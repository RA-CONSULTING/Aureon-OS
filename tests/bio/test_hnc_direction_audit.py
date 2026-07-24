"""Tests for the HNC direction audit — is adaptive logic wired to the one canonical field?

The audit reads each adaptive consumer's real source and reports whether it references the canonical-field
wire (``read_canonical_field`` / ``blend_field`` / the ``symbolic.life.pulse`` topic). Deterministic and
offline (source-level); byte-identical artifacts; never a claim about a person.

Probe behaviour is tested against synthetic module trees so it is independent of the live tree's current
wiring state. The ``all_directed`` headline is exercised on a fully-wired synthetic tree; the live-tree
verdict is asserted structurally (it flips true once the un-siloing work lands).
"""

from __future__ import annotations

import json

from aureon.bio import hnc_direction_audit as hda

_FORBIDDEN = ("health", "aura", "emotion", "spirit", "diagnos", "disease", "personality")


def _make_tree(tmp_path, wired: set[str]):
    """Build a synthetic repo root with each spec's module file, wiring only those named in ``wired``."""
    for _name, rel, _note in hda.direction_specs():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if _name in wired:
            path.write_text("from aureon.core.hnc_field import read_canonical_field\n", encoding="utf-8")
        else:
            path.write_text("coherence = 0.5  # private number, no canonical wire\n", encoding="utf-8")
    return tmp_path


# ── the probe ───────────────────────────────────────────────────────────────────────────────────


def test_all_directed_when_every_consumer_is_wired(tmp_path):
    root = _make_tree(tmp_path, wired={n for n, _r, _no in hda.direction_specs()})
    report = hda.compute_hnc_direction(repo_root=root)
    assert report.all_directed
    assert report.n_siloed == 0
    assert report.directed_fraction == 1.0
    assert all(c["via"] == "read_canonical_field" for c in report.consumers)


def test_siloed_when_no_consumer_is_wired(tmp_path):
    root = _make_tree(tmp_path, wired=set())
    report = hda.compute_hnc_direction(repo_root=root)
    assert not report.all_directed
    assert report.n_directed == 0
    assert set(report.siloed_names) == {n for n, _r, _no in hda.direction_specs()}


def test_partial_wiring_is_reported_precisely(tmp_path):
    root = _make_tree(tmp_path, wired={"kelly_gate", "miner_brain"})
    report = hda.compute_hnc_direction(repo_root=root)
    assert report.n_directed == 2
    directed = {c["name"] for c in report.consumers if c["directed"]}
    assert directed == {"kelly_gate", "miner_brain"}


def test_absent_module_is_marked_not_present(tmp_path):
    # empty tree — no files written
    report = hda.compute_hnc_direction(repo_root=tmp_path)
    assert all(not c["present"] for c in report.consumers)
    assert not report.all_directed


def test_counts_are_self_consistent_on_live_tree():
    report = hda.compute_hnc_direction()
    assert report.n_directed + report.n_siloed == report.n_total
    assert report.n_total == len(hda.direction_specs())
    assert 0.0 <= report.directed_fraction <= 1.0


def test_compute_is_deterministic():
    assert hda.compute_hnc_direction().to_dict() == hda.compute_hnc_direction().to_dict()


# ── the report ─────────────────────────────────────────────────────────────────────────────────


def test_write_report_writes_md_and_json(tmp_path):
    report = hda.compute_hnc_direction()
    out_md = tmp_path / "dir.md"
    out_json = tmp_path / "dir.json"
    rendered = hda.write_hnc_direction_report(report, out_md, out_json)
    assert out_md.exists() and out_md.stat().st_size > 0
    assert out_json.exists() and out_json.stat().st_size > 0
    assert rendered.out_path == str(out_md)
    md = out_md.read_text(encoding="utf-8")
    assert hda.HNC_DIRECTION_BOUNDARY in md
    loaded = json.loads(out_json.read_text(encoding="utf-8"))
    assert loaded["all_directed"] == report.all_directed
    assert loaded["boundary"] == hda.HNC_DIRECTION_BOUNDARY


def test_write_report_is_byte_identical_on_rewrite(tmp_path):
    report = hda.compute_hnc_direction()
    a_md, a_json = tmp_path / "a.md", tmp_path / "a.json"
    b_md, b_json = tmp_path / "b.md", tmp_path / "b.json"
    hda.write_hnc_direction_report(report, a_md, a_json)
    hda.write_hnc_direction_report(report, b_md, b_json)
    assert a_md.read_bytes() == b_md.read_bytes()
    assert a_json.read_bytes() == b_json.read_bytes()


def test_boundary_present_and_no_subject_claims():
    low = hda.HNC_DIRECTION_BOUNDARY.lower()
    for w in _FORBIDDEN:
        assert w not in low


def test_module_has_no_person_reading_surface():
    names = [n.lower() for n in dir(hda)]
    for banned in ("face", "speaker", "pose", "biometric"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface"


def test_emit_publishes_to_bus():
    published = []

    class _Bus:
        def publish(self, thought):
            published.append(thought)

    report = hda.compute_hnc_direction()
    payload = hda.emit_hnc_direction(report, bus=_Bus(), trace=False)
    assert payload["all_directed"] == report.all_directed
    assert len(published) == 1
    assert published[0].topic == hda.DIRECTION_RUN_TOPIC
    assert published[0].payload["boundary"] == hda.HNC_DIRECTION_BOUNDARY


def test_emit_tolerates_throwing_bus():
    class _BadBus:
        def publish(self, thought):
            raise RuntimeError("bus down")

    report = hda.compute_hnc_direction()
    payload = hda.emit_hnc_direction(report, bus=_BadBus(), trace=False)  # must not raise
    assert payload["all_directed"] == report.all_directed
