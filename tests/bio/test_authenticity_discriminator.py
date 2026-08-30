"""Tests for the authenticity discriminator — real vs synthetic, and the clone paradox.

The discriminator classifies a signal by its harmonic (Test A) + geometric (Test B) makeup and a keyed
HMAC provenance seal: a genuine signal passes both structural axes AND carries a valid seal; the three
surface imitations each fail the axis they cannot reproduce; and a perfect structural clone passes both
axes yet is blocked by provenance (the resolved Ditto/Gucci paradox). Synthetic only — no real subject,
never a claim about a person, never a security proof.
"""

from __future__ import annotations

import json

import numpy as np

from aureon.bio import authenticity_discriminator as ad

TRIALS = 24
NULLS = 120
_FORBIDDEN = ("health", "aura", "emotion", "spirit", "diagnos", "disease", "personality")


def _report():
    return ad.compute_authenticity(trials=TRIALS, nulls=NULLS, seed0=0)


# ── provenance seal (the keyed complement to b36's keyless envelope) ──────────────────────────────


def test_provenance_token_verifies_and_is_deterministic():
    tones = ad._structured_tones(2.0, 0)
    key = "unit-test-key"
    token = ad.provenance_token(tones, key=key)
    assert ad.verify_provenance(tones, token, key=key)
    # deterministic: same tones + same key → same token
    assert ad.provenance_token(tones, key=key) == token


def test_provenance_rejects_forged_missing_and_wrong_key():
    tones = ad._structured_tones(2.0, 1)
    key = "the-secret"
    token = ad.provenance_token(tones, key=key)
    # a token issued under a different key does not verify
    forged = ad.provenance_token(tones, key="not-the-secret")
    assert not ad.verify_provenance(tones, forged, key=key)
    # a missing token does not verify
    assert not ad.verify_provenance(tones, None, key=key)
    assert not ad.verify_provenance(tones, "", key=key)
    # a valid token for different tones does not verify (content-bound)
    other = ad._structured_tones(2.0, 2)
    assert not ad.verify_provenance(other, token, key=key)


# ── discrimination: the four classes + the clone paradox ──────────────────────────────────────────


def test_authentic_signal_is_authentic():
    key = ad._default_key()
    tones = ad._authentic_tones(0, 2.0)
    token = ad.provenance_token(tones, key=key)
    r = ad.discriminate(tones, token=token, key=key, nulls=NULLS, seed=0)
    assert r["structure_present"] and r["provenance_valid"] and r["authentic"]


def test_surface_imitations_are_not_authentic_and_fail_the_expected_axis():
    seed = 3
    # coarse mimic reproduces neither axis
    coarse = ad._coarse_mimic_tones(seed, 2.0)
    rc = ad.discriminate(coarse, nulls=NULLS, seed=seed)
    assert not rc["harmonic_present"] and not rc["geometric_present"] and not rc["authentic"]
    # harmonic-only passes the harmonic axis but fails the geometric one
    ho = ad._harmonic_only_tones(seed, 2.0)
    rh = ad.discriminate(ho, nulls=NULLS, seed=seed)
    assert rh["harmonic_present"] and not rh["geometric_present"] and not rh["authentic"]
    # geometric-only passes the geometric axis but fails the harmonic one (axes are independent)
    go = ad._geometric_only_tones(seed, 2.0)
    rg = ad.discriminate(go, nulls=NULLS, seed=seed)
    assert rg["geometric_present"] and not rg["harmonic_present"] and not rg["authentic"]


def test_perfect_clone_passes_structure_but_is_blocked_by_provenance():
    """The headline paradox: a structural clone is genuine by every measurable test, yet not authentic."""
    key = ad._default_key()
    tones = ad._authentic_tones(0, 2.0)  # the EXACT genuine makeup
    forged = ad.provenance_token(tones, key=ad._WRONG_KEY)  # a cloner lacks the secret key
    r = ad.discriminate(tones, token=forged, key=key, nulls=NULLS, seed=0)
    assert r["structure_present"]          # structure alone cannot catch the clone
    assert not r["provenance_valid"]       # the keyed seal can
    assert not r["authentic"]


def test_report_separates_genuine_from_imitations_and_blocks_the_clone():
    report = _report()
    assert report.n_classes == 5
    assert report.authentic_rate >= 0.8
    assert report.max_surface_imitation_rate <= 0.2
    assert report.clone_structural_rate >= 0.8   # the clone is structurally genuine
    assert report.clone_authentic_rate <= 0.05   # but provenance holds
    assert report.clone_blocked_by_provenance
    assert report.separation > 0.0
    for c in report.classes:
        assert 0.0 <= c.structural_rate <= 1.0
        assert 0.0 <= c.provenance_rate <= 1.0
        assert 0.0 <= c.authentic_rate <= 1.0


def test_compute_is_deterministic():
    assert _report().to_dict() == _report().to_dict()


def test_write_report_writes_md_and_json(tmp_path):
    report = _report()
    out_md = tmp_path / "auth.md"
    out_json = tmp_path / "auth.json"
    rendered = ad.write_authenticity_report(report, out_md, out_json)

    assert out_md.exists() and out_md.stat().st_size > 0
    assert out_json.exists() and out_json.stat().st_size > 0
    assert rendered.out_path == str(out_md)

    md = out_md.read_text(encoding="utf-8")
    assert ad.AUTHENTICITY_BOUNDARY in md
    row_lines = [ln for ln in md.splitlines() if ln.startswith("| ") and "---" not in ln]
    assert len(row_lines) == report.n_classes + 1  # + header row

    loaded = json.loads(out_json.read_text(encoding="utf-8"))
    assert loaded["n_classes"] == report.n_classes
    assert loaded["boundary"] == ad.AUTHENTICITY_BOUNDARY


def test_write_report_is_byte_identical_on_rewrite(tmp_path):
    report = _report()
    a_md, a_json = tmp_path / "a.md", tmp_path / "a.json"
    b_md, b_json = tmp_path / "b.md", tmp_path / "b.json"
    ad.write_authenticity_report(report, a_md, a_json)
    ad.write_authenticity_report(report, b_md, b_json)
    assert a_md.read_bytes() == b_md.read_bytes()
    assert a_json.read_bytes() == b_json.read_bytes()


def test_boundary_present_and_no_subject_claims():
    report = _report()
    d = report.to_dict()
    assert d["boundary"] == ad.AUTHENTICITY_BOUNDARY
    for c in report.classes:
        for key, value in c.to_dict().items():
            if isinstance(value, str):
                low = value.lower()
                for w in _FORBIDDEN:
                    assert w not in low, f"class field {key!r} leaked {w!r}"


def test_module_has_no_person_reading_surface():
    names = [n.lower() for n in dir(ad)]
    for banned in ("face", "speaker", "voice", "pose", "emotion", "identity", "biometric"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface"


def test_emit_publishes_to_bus():
    published = []

    class _Bus:
        def publish(self, thought):
            published.append(thought)

    report = _report()
    payload = ad.emit_authenticity(report, bus=_Bus(), trace=False)
    assert payload["n_classes"] == report.n_classes
    assert len(published) == 1
    assert published[0].topic == ad.AUTH_RUN_TOPIC
    assert published[0].payload["clone_blocked_by_provenance"] == report.clone_blocked_by_provenance
    assert published[0].payload["boundary"] == ad.AUTHENTICITY_BOUNDARY


def test_emit_tolerates_throwing_bus():
    class _BadBus:
        def publish(self, thought):
            raise RuntimeError("bus down")

    report = _report()
    payload = ad.emit_authenticity(report, bus=_BadBus(), trace=False)  # must not raise
    assert payload["n_classes"] == report.n_classes
