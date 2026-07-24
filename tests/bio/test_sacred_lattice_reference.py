"""Tests for the sacred-lattice reference — the repo's own sky-mapping tone tables.

The φ engine is unchanged. These tests assert the data surface: three catalogs of raw
Hz, 12 positioned ancient-site nodes, citations that name the repo source, and — like
``cosmic_reference`` — that importing the module trips **no** ``aureon.wisdom``
import-time baton side effect. No claim is made about what any lane "should" score.
"""

from __future__ import annotations

import subprocess
import sys

from aureon.bio import sacred_lattice_reference as slr


def test_no_wisdom_import_side_effect():
    # importing the reference module must not pull in any aureon.wisdom module
    # (those run an import-time _baton_link heartbeat that writes logs/…jsonl).
    # Checked in a fresh interpreter so other tests' imports can't contaminate it.
    code = (
        "import sys; import aureon.bio.sacred_lattice_reference; "
        "leaked=[m for m in sys.modules if m.startswith('aureon.wisdom')]; "
        "print(leaked); sys.exit(1 if leaked else 0)"
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert proc.returncode == 0, f"aureon.wisdom leaked at import: {proc.stdout.strip()}"


def test_catalogs_are_positive_hz():
    for name in ("stargate", "maeshowe", "metatron"):
        c = slr.catalog_hz(name)
        assert len(c) >= 2
        assert all(f > 0 for f in c)
        assert list(c) == sorted(c)  # sorted, deduped


def test_unknown_catalog_raises():
    import pytest

    with pytest.raises(ValueError):
        slr.catalog_hz("nope")


def test_stargate_positions_are_geographic():
    pos = slr.stargate_positions()
    assert len(pos) == 12
    for name, lat, lon, tones in pos:
        assert name
        assert -90.0 <= lat <= 90.0
        assert -180.0 <= lon <= 180.0
        assert len(tones) >= 1  # folded harmonic-signature tones


def test_metatron_shape():
    # 13 spheres: 1 centre + 12 φ-scaled icosahedral vertices
    assert len(slr.METATRON_TONES_HZ) == 13
    assert len(slr.METATRON_POSITIONS) == 13
    assert slr.METATRON_POSITIONS[0] == (0.0, 0.0, 0.0)


def test_gobekli_phi_frequency():
    # Göbekli Tepe's resonance is 7.83·φ·10 — the φ-derived tone, natively "the HNC way"
    gobekli = next(n for n in slr.STARGATE_NODES if "Göbekli" in n[0])
    assert abs(gobekli[3] - 7.83 * slr.PHI * 10) < 1e-6


def test_citations_name_repo_source():
    assert "aureon_stargate_protocol" in slr.STARGATE_CITATION
    assert "maeshowe_seer_decode" in slr.MAESHOWE_CITATION
    assert "metatrons_cube" in slr.METATRON_CITATION


def test_boundary_is_honest():
    low = slr.SACRED_LATTICE_BOUNDARY.lower()
    assert "not a claim" in low
    assert "unchanged" in low
    assert "not celestial ra/dec" in low
    assert "no efficacy claim" in low
