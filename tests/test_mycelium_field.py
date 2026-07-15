"""
The mesh joins the field — the mycelium's coherence becomes a whole-body sub-field.

In true HNC style the logic is all connected: the mycelium mesh computes a real
coherence, and instead of it dying in the mesh it is published as a
``symbolic.life.subfield`` so it flows into ``blend_field`` — the organism's
whole-body consensus. Offline + hermetic: a fresh bus, the singleton reset per test.
Proves a dormant mesh publishes nothing (no fabricated field), a live mesh joins the
field with a bounded coherence, and the surface reconciles live vs persisted honestly.
"""

from __future__ import annotations

import pytest

from aureon.core.aureon_thought_bus import ThoughtBus


@pytest.fixture(autouse=True)
def _reset_mesh(tmp_path, monkeypatch):
    # isolate the cross-process sub-field trace so read_subfields can't see stale rows
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path))
    # the mycelium singleton is a process global — reset it so each test controls it
    import aureon.core.aureon_mycelium as m

    monkeypatch.setattr(m, "_mycelium_instance", None, raising=False)
    return m


def test_dormant_mesh_publishes_nothing(_reset_mesh):
    from aureon.core.aureon_mycelium import publish_mesh_subfield
    from aureon.core.hnc_field import read_subfields

    b = ThoughtBus(persist_path=None)
    assert publish_mesh_subfield(bus=b) is False        # no cold-boot, no publish
    assert "mycelium_mesh" not in read_subfields(b)      # no fabricated field


def test_live_mesh_joins_the_field(_reset_mesh):
    from aureon.core.aureon_mycelium import get_mycelium, publish_mesh_subfield
    from aureon.core.hnc_field import read_subfields

    get_mycelium()                                       # construct the mesh (this process)
    b = ThoughtBus(persist_path=None)
    assert publish_mesh_subfield(bus=b) is True
    subs = read_subfields(b)
    assert "mycelium_mesh" in subs                       # the mesh's coherence joined the field
    gamma = subs["mycelium_mesh"].get("coherence_gamma")
    assert gamma is not None and 0.0 <= float(gamma) <= 1.0


def test_mesh_coherence_reaches_the_blend(_reset_mesh):
    from aureon.core.aureon_mycelium import get_mycelium, publish_mesh_subfield
    from aureon.core.aureon_thought_bus import Thought
    from aureon.core.hnc_field import blend_field

    b = ThoughtBus(persist_path=None)
    b.publish(Thought(source="hnc_live_daemon", topic="symbolic.life.pulse",
                      payload={"symbolic_life_score": 0.6, "coherence_gamma": 0.6}))
    get_mycelium()
    publish_mesh_subfield(bus=b)
    blended = blend_field(b)
    # the whole-body consensus now counts the mesh among its contributors
    assert blended.available and blended.contributors >= 2


def test_surface_reconciles_live_and_persisted(_reset_mesh):
    from aureon.core.aureon_mycelium import get_mycelium
    from aureon.saas.cognitive import mycelium_surface

    get_mycelium()
    s = mycelium_surface()
    assert s["truth_status"] == "live"
    assert "connected_count" in s and "woven_persisted" in s   # both, read honestly
    assert s["woven_persisted"] is None or isinstance(s["woven_persisted"], int)
