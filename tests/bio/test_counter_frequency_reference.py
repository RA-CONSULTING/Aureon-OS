"""Tests for the counter-frequency reference — the repo's φ/Fibonacci canon.

The φ engine is unchanged. These tests assert the data surface: catalogs of raw
Hz, the distinctive Fibonacci ladder + φ-harmonics, the citation naming the repo
source, and — like the other bio reference modules — that importing trips no
``aureon.harmonic`` import-time baton side effect.
"""

from __future__ import annotations

import subprocess
import sys

from aureon.bio import counter_frequency_reference as cfr


def test_no_source_import_side_effect():
    code = (
        "import sys; import aureon.bio.counter_frequency_reference; "
        "leaked=[m for m in sys.modules "
        "if m.startswith('aureon.harmonic') or m.startswith('aureon.wisdom')]; "
        "print(leaked); sys.exit(1 if leaked else 0)"
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert proc.returncode == 0, f"source module leaked at import: {proc.stdout.strip()}"


def test_catalogs_are_positive_sorted_hz():
    for name in ("counter", "fibonacci", "phi"):
        c = cfr.catalog_hz(name)
        assert len(c) >= 2
        assert all(f > 0 for f in c)
        assert list(c) == sorted(c)


def test_unknown_catalog_raises():
    import pytest

    with pytest.raises(ValueError):
        cfr.catalog_hz("nope")


def test_fibonacci_ladder():
    assert set(cfr.fibonacci_hz()) == {8.0, 13.0, 21.0, 34.0}
    # the ladder is genuinely distinct from the Solfeggio range
    assert max(cfr.fibonacci_hz()) < 100


def test_phi_harmonics():
    phi = cfr.phi_harmonic_hz()
    assert len(phi) == 3
    assert abs(phi[0] - cfr.PHI) < 1e-9          # φ
    assert abs(phi[1] - cfr.PHI * 2) < 1e-9       # 2φ
    assert abs(phi[2] - 24.0 / cfr.PHI) < 1e-9    # 24/φ ≈ 14.83


def test_sacred_frequencies_copied_verbatim():
    d = cfr.SACRED_FREQUENCIES
    assert d["FIBONACCI_8"] == 8.0 and d["FIBONACCI_34"] == 34.0
    assert d["SOLFEGGIO_528"] == 528.0 and d["SCHUMANN_RESONANCE"] == 7.83
    assert abs(d["GOLDEN_CYCLE"] - 24.0 / cfr.PHI) < 1e-9


def test_citation_and_boundary():
    assert "aureon_harmonic_counter_frequency" in cfr.COUNTER_FREQUENCY_CITATION
    low = cfr.COUNTER_FREQUENCY_BOUNDARY.lower()
    assert "not a claim" in low and "unchanged" in low
    assert "no efficacy claim" in low
