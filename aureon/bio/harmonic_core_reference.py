#!/usr/bin/env python3
"""Harmonic-core reference — the HNC's OWN harmonic frequency tables.

The sacred-lattice lanes mapped the sky through Earth's harmonic lattice. This module
goes one level deeper — to the repo's **own core harmonic system**: the frequency
substrate the whole HNC framework is built on. Three repo-native tone systems are
carried here as clean static data so each can be scanned through the **unchanged**
phenolic φ engine:

* **Master Formula Λ(t) modes** — ``aureon/core/aureon_lambda_engine.py::FREQUENCIES`` /
  ``WEIGHTS``: the 6 weighted harmonic modes of the HNC master equation
  ``Λ(t) = Σ wᵢ sin(2πfᵢt + φᵢ) + α·tanh(g·Λ̄(t)) + β·Λ(t−τ)`` — 528 Hz dominant (w=0.30).
  This IS "the harmonic system" the framework centres on, as concrete data.
* **Celtic Ogham tree-tones** — ``aureon/decoders/celtic_ogham.py``: 25 feda across
  5 aicme, each a Solfeggio base tone φ-scaled by its aett rule
  (aicme 1,4 ×1 · aicme 2,5 ×φ · aicme 3 ×φ⁻¹).
* **Ghost Dance ancestral tones** — ``aureon/wisdom/aureon_ghost_dance_protocol.py::
  ANCESTRAL_FREQUENCIES``: the full 9-tone Solfeggio ladder mapped to ancestral
  archetypes.

The literal constants are **copied** here (not imported) for the same reason
``cosmic_reference`` / ``sacred_lattice_reference`` copy theirs: the Ghost Dance module
runs an import-time ``_baton_link`` heartbeat (writes ``logs/…jsonl``, wires Mycelium),
so copying keeps this module pure stdlib + no repo import, no network, no import-time
writes. (The Λ-engine and Ogham modules are themselves import-clean, but their values
are copied too so the whole reference stays uniform and dependency-free.)

Pure stdlib; no repo import, no network.
"""

from __future__ import annotations

import math
from typing import Final

from aureon.bio.human_harmonic_proxy import fold_to_band

__all__ = [
    "HARMONIC_CORE_BOUNDARY",
    "PHI",
    "LAMBDA_MODES",
    "LAMBDA_HZ",
    "OGHAM_FEDA",
    "GHOST_DANCE_TONES",
    "LAMBDA_CITATION",
    "OGHAM_CITATION",
    "GHOST_DANCE_CITATION",
    "catalog_hz",
    "lambda_weighted",
    "ogham_feda",
]

#: Golden ratio — the constant the Ogham aett rule scales by.
PHI: Final[float] = (1 + math.sqrt(5)) / 2  # 1.618033988749895
_PHI_INV: Final[float] = 1.0 / PHI

HARMONIC_CORE_BOUNDARY: Final[str] = (
    "The harmonic-core lanes report statistical structure in a derived tone set built "
    "from the repo's OWN HNC harmonic frequency tables (Master Formula Λ(t) modes, "
    "Celtic Ogham tree-tones, Ghost Dance ancestral Solfeggio), scanned through one "
    "unchanged φ engine - NOT a claim about consciousness, ancestral spirits, sacred "
    "trees, the reality field, or any esoteric effect, and no efficacy claim. Each "
    "verdict is exactly what the pre-registered test returned."
)

# ── Master Formula Λ(t): the 6 weighted harmonic modes (freq_hz, weight) ─────────
#: Copied verbatim from aureon_lambda_engine.FREQUENCIES / WEIGHTS (528 Hz dominant).
LAMBDA_MODES: Final[tuple[tuple[float, float], ...]] = (
    (7.83, 0.25),
    (14.3, 0.15),
    (20.8, 0.10),
    (33.8, 0.05),
    (528.0, 0.30),
    (963.0, 0.15),
)
LAMBDA_HZ: Final[tuple[float, ...]] = tuple(f for f, _w in LAMBDA_MODES)

# ── Celtic Ogham: 25 feda, each a base Solfeggio tone φ-scaled by aett rule ───────
_OGHAM_SOL: Final[tuple[int, ...]] = (174, 285, 396, 417, 528)  # positions 1-5


def _ogham_amp(aicme: int) -> float:
    """Aett amplitude rule: aicme 1,4 ×1.0 · aicme 2,5 ×φ · aicme 3 ×φ⁻¹."""
    return {1: 1.0, 2: PHI, 3: _PHI_INV, 4: 1.0, 5: PHI}.get(aicme, 1.0)


#: (aicme, position, name, tree) for the 25 feda — replicated from celtic_ogham._FEDA.
_OGHAM_NAMES: Final[tuple[tuple[int, int, str, str], ...]] = (
    (1, 1, "Beith", "Birch"), (1, 2, "Luis", "Rowan"), (1, 3, "Fearn", "Alder"),
    (1, 4, "Sail", "Willow"), (1, 5, "Nion", "Ash"),
    (2, 1, "Huath", "Hawthorn"), (2, 2, "Dair", "Oak"), (2, 3, "Tinne", "Holly"),
    (2, 4, "Coll", "Hazel"), (2, 5, "Quert", "Apple"),
    (3, 1, "Muin", "Vine"), (3, 2, "Gort", "Ivy"), (3, 3, "nGetal", "Reed"),
    (3, 4, "Straif", "Blackthorn"), (3, 5, "Ruis", "Elder"),
    (4, 1, "Ailm", "Fir"), (4, 2, "Onn", "Gorse"), (4, 3, "Ur", "Heather"),
    (4, 4, "Edad", "Aspen"), (4, 5, "Idad", "Yew"),
    (5, 1, "Eabhadh", "Grove"), (5, 2, "Or", "Spindle"), (5, 3, "Uilleann", "Honeysuckle"),
    (5, 4, "Ifín", "Gooseberry"), (5, 5, "Eamhancholl", "Twin-of-Hazel"),
)

#: 25 feda as (name, tree, aicme, effective_hz) — freq = base × aett amplitude.
OGHAM_FEDA: Final[tuple[tuple[str, str, int, float], ...]] = tuple(
    (name, tree, aicme, _OGHAM_SOL[position - 1] * _ogham_amp(aicme))
    for aicme, position, name, tree in _OGHAM_NAMES
)

# ── Ghost Dance: the 9-tone Solfeggio ladder → ancestral archetypes ──────────────
#: Copied verbatim from aureon_ghost_dance_protocol.ANCESTRAL_FREQUENCIES.
GHOST_DANCE_TONES: Final[tuple[tuple[float, str], ...]] = (
    (174.0, "foundation_elders"),
    (285.0, "healing_grandmothers"),
    (396.0, "liberation_warriors"),
    (417.0, "transformation_shamans"),
    (528.0, "medicine_people"),
    (639.0, "community_builders"),
    (741.0, "scout_ancestors"),
    (852.0, "visionary_elders"),
    (963.0, "chief_council"),
)

LAMBDA_CITATION: Final[str] = (
    "6 weighted harmonic modes of the HNC Master Formula Λ(t) (528 Hz dominant); "
    "repo: aureon/core/aureon_lambda_engine.FREQUENCIES/WEIGHTS."
)
OGHAM_CITATION: Final[str] = (
    "25 Celtic Ogham tree-tones (Solfeggio base φ-scaled by aett rule); "
    "repo: aureon/decoders/celtic_ogham._FEDA."
)
GHOST_DANCE_CITATION: Final[str] = (
    "9-tone Solfeggio ladder → ancestral archetypes; "
    "repo: aureon/wisdom/aureon_ghost_dance_protocol.ANCESTRAL_FREQUENCIES."
)


_CATALOGS = {
    "lambda": LAMBDA_HZ,
    "ogham": tuple(sorted({round(hz, 6) for _n, _t, _a, hz in OGHAM_FEDA})),
    "ghostdance": tuple(f for f, _label in GHOST_DANCE_TONES),
}


def catalog_hz(name: str) -> tuple[float, ...]:
    """Return a named harmonic-core frequency list (raw Hz).

    'lambda' is the 6 Master-Formula modes; 'ogham' is the deduped φ-scaled tree-tone
    set; 'ghostdance' is the 9-tone ancestral Solfeggio ladder.
    """
    try:
        return _CATALOGS[name]
    except KeyError:
        raise ValueError(
            f"unknown harmonic-core catalog {name!r}; expected one of {sorted(_CATALOGS)}"
        ) from None


def lambda_weighted() -> tuple[tuple[float, float], ...]:
    """The Λ(t) modes as (frequency_hz, weight) pairs — for traceability/reporting."""
    return LAMBDA_MODES


def ogham_feda() -> list[tuple[str, str, int, float]]:
    """The 25 Ogham feda as (name, tree, aicme, effective_hz), with tones folded-in.

    Returned tones are the raw effective Hz; callers fold via ``fold_to_band`` when a
    per-feda banded view is wanted. Names are carried for citation/traceability.
    """
    return list(OGHAM_FEDA)


def _assert_foldable() -> None:  # pragma: no cover - import-time sanity guard
    # every catalog must have >= 2 tones that survive octave-folding into the band
    for name in _CATALOGS:
        folded = [f for f in (fold_to_band(v) for v in catalog_hz(name)) if f is not None]
        if len(folded) < 2:
            raise AssertionError(f"harmonic-core catalog {name!r} folds to < 2 tones")


_assert_foldable()
