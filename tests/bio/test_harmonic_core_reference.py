"""Tests for the harmonic-core reference — the HNC's own harmonic frequency tables.

The φ engine is unchanged. These tests assert the data surface: three catalogs of raw
Hz (Master Formula Λ(t) modes, Celtic Ogham tree-tones, Ghost Dance ancestral Solfeggio),
the Λ weights are the load-bearing normalised vector, the Ogham φ-scaling follows the
aett rule, citations name the repo source, and — like ``cosmic_reference`` — importing
the module trips **no** ``aureon.wisdom`` / ``aureon.core`` import-time baton side effect.
"""

from __future__ import annotations

import subprocess
import sys

from aureon.bio import harmonic_core_reference as hcr


def test_no_source_import_side_effect():
    # importing the reference must not pull in the Ghost Dance (baton_link) module,
    # nor any aureon.wisdom module. Checked in a fresh interpreter to avoid contamination.
    code = (
        "import sys; import aureon.bio.harmonic_core_reference; "
        "leaked=[m for m in sys.modules "
        "if m.startswith('aureon.wisdom') or m=='aureon.core.aureon_lambda_engine']; "
        "print(leaked); sys.exit(1 if leaked else 0)"
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert proc.returncode == 0, f"source module leaked at import: {proc.stdout.strip()}"


def test_catalogs_are_positive_sorted_hz():
    for name in ("lambda", "ogham", "ghostdance"):
        c = hcr.catalog_hz(name)
        assert len(c) >= 2
        assert all(f > 0 for f in c)
        assert list(c) == sorted(c)  # sorted, deduped


def test_unknown_catalog_raises():
    import pytest

    with pytest.raises(ValueError):
        hcr.catalog_hz("nope")


def test_lambda_modes_are_the_master_formula():
    modes = hcr.lambda_weighted()
    assert len(modes) == 6
    freqs = [f for f, _w in modes]
    weights = [w for _f, w in modes]
    # copied verbatim from aureon_lambda_engine.FREQUENCIES / WEIGHTS (528 Hz dominant)
    assert freqs == [7.83, 14.3, 20.8, 33.8, 528.0, 963.0]
    assert abs(sum(weights) - 1.0) < 1e-9
    assert max(modes, key=lambda m: m[1])[0] == 528.0  # 528 Hz dominant


def test_ogham_phi_scaling_by_aett():
    feda = {name: (aicme, hz) for name, _tree, aicme, hz in hcr.ogham_feda()}
    assert len(hcr.ogham_feda()) == 25
    # aicme 1 (×1.0): Beith = base 174
    assert abs(feda["Beith"][1] - 174.0) < 1e-6
    # aicme 2 (×φ): Huath = 174 × φ
    assert abs(feda["Huath"][1] - 174 * hcr.PHI) < 1e-6
    # aicme 3 (×φ⁻¹): Muin = 174 / φ
    assert abs(feda["Muin"][1] - 174 / hcr.PHI) < 1e-6


def test_ghost_dance_is_solfeggio_ladder():
    tones = [f for f, _label in hcr.GHOST_DANCE_TONES]
    assert tones == [174, 285, 396, 417, 528, 639, 741, 852, 963]
    assert all(label for _f, label in hcr.GHOST_DANCE_TONES)  # every tone archetype-labelled


def test_citations_name_repo_source():
    assert "aureon_lambda_engine" in hcr.LAMBDA_CITATION
    assert "celtic_ogham" in hcr.OGHAM_CITATION
    assert "aureon_ghost_dance_protocol" in hcr.GHOST_DANCE_CITATION


def test_boundary_is_honest():
    low = hcr.HARMONIC_CORE_BOUNDARY.lower()
    assert "not a claim" in low
    assert "unchanged" in low
    assert "no efficacy claim" in low
    assert "consciousness" in low  # names the esoteric register it is NOT claiming
