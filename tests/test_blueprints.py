"""Unit + smoke tests for the bio↔vibe blueprint generator."""

from __future__ import annotations

from pathlib import Path

import pytest

import blueprints

FIXTURES = Path(__file__).parent / "fixtures"
CODEX = FIXTURES / "weed_phenolic_spectral_map_codex.csv"


def test_cluster_coherence_nodes_running_mean():
    recs = [{"modulation_frequency_hz": f, "molecule": "m"} for f in
            (1000.0, 1010.0, 1020.0, 1500.0, 1505.0)]
    nodes = blueprints.cluster_coherence_nodes(recs, tolerance_hz=25.0)
    assert len(nodes) == 2
    assert nodes[0]["n_peaks"] == 3
    assert nodes[1]["n_peaks"] == 2
    assert nodes[0]["node_id"] == "CN-001"
    assert nodes[0]["molecules"] == ["m"]


def test_cluster_coherence_nodes_empty():
    assert blueprints.cluster_coherence_nodes([]) == []


def test_plant_molecule_map_excludes_non_plant_tokens():
    mapping = blueprints.plant_molecule_map(CODEX)
    assert "many" not in mapping and "widespread" not in mapping
    assert "chicory" in mapping
    assert "chicoric acid" in mapping["chicory"]
    # a real plant maps to real molecules
    assert all(isinstance(m, str) for m in mapping["nettle"])


def test_render_blueprints_smoke(tmp_path):
    pytest.importorskip("matplotlib")
    sources = [CODEX]
    mol_paths = blueprints.render_molecule_blueprints(sources, out_dir=tmp_path, nulls=20, seed=0)
    plant_paths = blueprints.render_plant_harmonic_nodes(sources, out_dir=tmp_path, nulls=20, seed=0)
    for p in (*mol_paths, *plant_paths):
        assert p.exists() and p.stat().st_size > 0
    assert any(p.suffix == ".png" for p in mol_paths)
    assert any(p.suffix == ".png" for p in plant_paths)


def test_main_cli_smoke(tmp_path):
    pytest.importorskip("matplotlib")
    code = blueprints.main(["--sources", str(CODEX), "--out", str(tmp_path), "--nulls", "20"])
    assert code == 0
    assert (tmp_path / "phenolic_molecule_blueprints.png").exists()
    assert (tmp_path / "phenolic_plant_harmonic_nodes.png").exists()
