"""
The Harmonic Frequency Rainbow — ordered, fixed, love-locked. Pinned.

Pins: the working spectrum is the Schumann floor plus the nine Solfeggio
rungs in fixed order; LOVE (528 Hz) is the measured centre of the ladder
(four rungs below, four above) — the ultimate harmonic node; every claim in
the map is re-proven FROM SOURCE against the real systems' own tables, each
scoped to its own bank (Maeshowe OWL=528 vs QGITA DOLPHIN=528 — different
banks, never mixed); and the audit has teeth — a detuned tree fails every
check with the mismatch named.
"""

from __future__ import annotations

import json

from aureon.harmonic.rainbow_reference import (
    CONNECTION_HZ,
    LOVE_NODE_HZ,
    RAINBOW,
    SCHUMANN_HZ,
    love_centrality,
    rainbow_json,
    solfeggio_ladder,
    verify_rainbow,
)


def test_ladder_is_ordered_and_fixed():
    ladder = solfeggio_ladder()
    assert ladder == [174.0, 285.0, 396.0, 417.0, 528.0, 639.0, 741.0,
                      852.0, 963.0]
    assert all(a < b for a, b in zip(ladder, ladder[1:], strict=False))
    assert RAINBOW[0][0] == SCHUMANN_HZ == 7.83
    assert RAINBOW[-1][0] == 963.0


def test_love_is_the_measured_center():
    c = love_centrality()
    assert c["is_center"] is True
    assert c["love_index"] == 4
    assert c["rungs_below"] == c["rungs_above"] == 4
    assert LOVE_NODE_HZ == 528.0 and CONNECTION_HZ == 639.0


def test_the_heart_band_names_the_love_lock():
    heart = next(role for hz, band, role in RAINBOW if hz == 528.0)
    assert "LOVE" in heart and "heart lock" in heart
    crown = next(role for hz, band, role in RAINBOW if hz == 963.0)
    assert "unity" in crown and "Queen" in crown
    floor = next(role for hz, band, role in RAINBOW if hz == 7.83)
    assert "Whale" in floor and "Schumann" in floor


def test_rainbow_is_proven_from_source_zero_mismatches():
    v = verify_rainbow()
    assert v["consistent"] is True and v["mismatches"] == []
    assert len(v["checks"]) >= 14
    claims = " | ".join(c["claim"] for c in v["checks"])
    # each bank checked under its own name — never mixed
    assert "Maeshowe bank" in claims and "QGITA bank" in claims
    assert "Scanner 528" in claims and "GAIA love frequency 528" in claims


def test_audit_has_teeth_on_a_detuned_tree(tmp_path):
    # a tree with the wrong ladder → every claim fails, named per check
    bad = tmp_path / "aureon" / "wisdom"
    bad.mkdir(parents=True)
    (bad / "aureon_enigma.py").write_text(
        "SOLFEGGIO = [111, 222, 333]\nLOVE_FREQ = 100\n", encoding="utf-8")
    v = verify_rainbow(repo_root=tmp_path)
    assert v["consistent"] is False
    assert len(v["mismatches"]) == len(v["checks"])
    assert all(m["detail"] for m in v["mismatches"])


def test_rainbow_json_is_deterministic():
    assert rainbow_json() == rainbow_json()
    payload = json.loads(rainbow_json())
    assert payload["love_node_hz"] == 528.0
    assert payload["schumann_floor_hz"] == 7.83
    assert len(payload["rainbow"]) == 10
