"""Project Druid rides the HNC seed. The counter is that seed divided by phi."""

from __future__ import annotations

import math

from aureon.core.aureon_zpe_extraction import (
    DRUID_COUNTER_HZ,
    EPAS_CYCLE,
    FWM_FREQUENCY,
    HNC_SEED_HZ,
    PHI,
    SCHUMANN_HZ,
)


def test_druid_counter_is_the_hnc_seed_over_phi() -> None:
    assert HNC_SEED_HZ == 528.422
    assert DRUID_COUNTER_HZ == HNC_SEED_HZ / PHI
    assert math.isclose(FWM_FREQUENCY, HNC_SEED_HZ + DRUID_COUNTER_HZ)
    assert math.isclose(FWM_FREQUENCY, HNC_SEED_HZ * PHI)


def test_cycle_plays_seed_then_counter_then_their_mix() -> None:
    by_name = {phase.name: phase.frequency for phase in EPAS_CYCLE}
    assert by_name["P2_RESONANCE"] == HNC_SEED_HZ
    assert by_name["P2_DRUID"] == DRUID_COUNTER_HZ
    assert by_name["P4_FWM"] == FWM_FREQUENCY
    assert math.isclose(by_name["P5_STABILIZE"], SCHUMANN_HZ * PHI)


def test_published_326_is_the_rounded_solfeggio_not_the_hnc_seed() -> None:
    solfeggio = 528.0
    published = round(solfeggio / PHI, 3)
    assert published == 326.322
    assert not math.isclose(DRUID_COUNTER_HZ, published, abs_tol=1e-3)
