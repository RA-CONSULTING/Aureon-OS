"""
The Waking — a genesis boot signal that wakes the body and carries the thread.

Offline + hermetic: a temp genome path + a fresh bus. Proves the wake increments the
generation across cycles (persisted, with a stable first_awakened_at), signals the
body on the bus, carries real DNA (never fabricated), kicks a bounded move, and that
read_genome() is side-effect-free.
"""

from __future__ import annotations

import json

import pytest

from aureon.core.aureon_thought_bus import get_thought_bus


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_GENESIS_PATH", str(tmp_path / "genesis.json"))
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path))
    monkeypatch.setenv("AUREON_AWAKEN_WEAVE", "0")   # no move by default (bounded/off)
    import aureon.core.aureon_thought_bus as tb

    monkeypatch.setattr(tb, "_thought_bus_instance", None, raising=False)
    return tmp_path


def test_generation_climbs_across_cycles(tmp_path):
    from aureon.core.awakening import awaken, read_genome

    a1 = awaken()
    a2 = awaken()
    assert a1["generation"] == 1 and a2["generation"] == 2
    g = read_genome()
    assert g["generation"] == 2                        # persisted across cycles (the DNA)
    assert g["first_awakened_at"] is not None
    assert g["last_awakened_at"] >= g["first_awakened_at"]


def test_first_awakened_at_is_stable(tmp_path):
    from aureon.core.awakening import awaken, read_genome

    awaken()
    first = read_genome()["first_awakened_at"]
    awaken()
    assert read_genome()["first_awakened_at"] == first   # lineage origin never moves


def test_wake_signals_the_body(tmp_path):
    from aureon.core.awakening import awaken

    awaken()
    sig = get_thought_bus().recall("organism.awakening", limit=1) or []
    assert sig
    payload = sig[-1].get("payload", {})
    assert payload.get("generation") == 1 and "carried" in payload


def test_read_genome_is_side_effect_free(tmp_path):
    from aureon.core.awakening import awaken, read_genome

    awaken()
    assert read_genome()["generation"] == 1
    assert read_genome()["generation"] == 1              # reading never increments


def test_carried_dna_is_honest(tmp_path):
    # carried values are real reads or None — never fabricated
    from aureon.core.awakening import awaken

    carried = awaken()["carried"]
    assert set(carried) >= {"coverage_pct", "woven", "nodes", "automation_index", "ascent_stage",
                            "reproduction_generation", "reproduction_splits"}
    for v in carried.values():
        assert v is None or isinstance(v, (int, float))


def test_reproduction_lineage_carried_when_mesh_live(tmp_path, monkeypatch):
    # The oldest DNA — the budding lineage — is carried when the mesh exists…
    import aureon.core.aureon_mycelium as myc

    class _Net:
        generation = 3
        total_harvested = 0.0
        split_events = [{"a": 1}, {"a": 2}]
        hives = []

    from aureon.core.awakening import _carried_dna

    prev = myc._mycelium_instance
    myc._mycelium_instance = _Net()
    try:
        dna = _carried_dna()
        assert dna["reproduction_generation"] == 3   # the network lineage depth
        assert dna["reproduction_splits"] == 2
    finally:
        myc._mycelium_instance = prev


def test_reproduction_lineage_none_and_no_cold_boot_when_dormant(tmp_path):
    # …and None when dormant, without ever constructing the network.
    import aureon.core.aureon_mycelium as myc
    from aureon.core.awakening import _carried_dna

    prev = myc._mycelium_instance
    myc._mycelium_instance = None
    try:
        dna = _carried_dna()
        assert dna["reproduction_generation"] is None
        assert dna["reproduction_splits"] is None
        assert myc._mycelium_instance is None        # the wake never cold-boots the mesh
    finally:
        myc._mycelium_instance = prev


def test_awaken_kicks_a_bounded_move(tmp_path, monkeypatch):
    # with a weave budget, the wake nudges the connectome once (bounded)
    monkeypatch.setenv("AUREON_AWAKEN_WEAVE", "6")
    calls = {}

    import aureon.core.awakening as aw

    class _Stub:
        def weave_touched(self, limit=None):
            calls["limit"] = limit
            return {"woven": 6, "remaining": 0}

    monkeypatch.setattr(aw, "_carried_dna", lambda: {"coverage_pct": 1.0})
    monkeypatch.setattr("aureon.core.aureon_connectome.get_connectome", lambda: _Stub())
    moved = aw.awaken()["moved"]
    assert calls.get("limit") == 6 and moved["woven"] == 6


def test_awaken_never_raises_when_dormant(tmp_path, monkeypatch):
    import aureon.core.awakening as aw

    def _boom():
        raise RuntimeError("dormant")

    monkeypatch.setattr(aw, "_carried_dna", _boom)   # even a broken gather is survived
    out = aw.awaken()
    assert "generation" in out and isinstance(out["generation"], int)


def test_genome_file_shape(tmp_path):
    from aureon.core.awakening import awaken

    awaken()
    data = json.loads((tmp_path / "genesis.json").read_text())
    assert set(data) == {"generation", "first_awakened_at", "last_awakened_at", "carried"}
