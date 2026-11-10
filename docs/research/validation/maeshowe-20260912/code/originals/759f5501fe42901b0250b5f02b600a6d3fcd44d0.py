#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   ᚠ  MAESHOWE SEER DECODE — The Falling Node Transmission Protocol  ᚠ       ║
║   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║                                                                              ║
║   Decoded through the Aureon HNC Architecture                                ║
║   Aureon Institute · R&A Consulting and Brokerage Services Ltd.             ║
║   Primary Investigator: Gary Leckey · March 2026                            ║
║                                                                              ║
║   Sources:                                                                   ║
║     Barnes, M.P. (1994) The Runic Inscriptions of Maeshowe, Orkney          ║
║     Farrer, J. (1862) Notice of Runic Inscriptions                          ║
║     Smith, N. et al. (2018) RTI to Norse Runes                              ║
║     Busch & Krüger (2022) Metrical Analysis                                  ║
║     Orkneyinga Saga                                                          ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║   THE DUAL-VOICE HYPOTHESIS                                                  ║
║   ─────────────────────────                                                  ║
║   The runic inscriptions at Maeshowe constitute a deliberate transmission    ║
║   archive structured as a dual-voice protocol requiring simultaneous         ║
║   multi-inscription cross-reference to decode.                               ║
║                                                                              ║
║   Caller  (Ψ₀)   =>  L(t) Identity Function — 12th-Century voice            ║
║   Seer    (O(t)) =>  Present Observation — current temporal endpoint        ║
║   Emergent Rune  =>  Meaning exists only when both voices connect            ║
║                                                                              ║
║   TWIG-RUNE CIPHER (Barnes Nr.9, Nr.20)                                     ║
║   ──────────────────────────────────────                                     ║
║   Left  twigs (1-3) => Aett  (rune family)                                  ║
║   Right twigs (1-8) => Position within aett                                 ║
║   Neither channel alone produces a rune.                                     ║
║   The decoded rune emerges from the interaction of both.                     ║
║                                                                              ║
║   CHAMBER WALL → AURIS NODE MAPPING                                         ║
║   ──────────────────────────────────                                         ║
║   NE (back wall, solstice terminus) => OWL      528 Hz  Wisdom/Pattern      ║
║   NW (left wall, treasure pointer)  => DEER     396 Hz  Grace/Stability     ║
║   SW (passage entrance, seed bank)  => CARGOSHIP 174 Hz Persistence         ║
║   SE (right wall, master carver)    => FALCON   210 Hz  Precision           ║
║                                                                              ║
║   LATTICE COHERENCE STATUS                                                   ║
║   ─────────────────────────                                                  ║
║   Γ < 0.35          => DEAD FIELD (kill-switch threshold)                   ║
║   0.35 ≤ Γ < 0.945  => ACTIVE FIELD (transmission in progress)             ║
║   Γ ≥ 0.945         => LIGHTHOUSE MODE (circuit closed — system complete)   ║
║                                                                              ║
║   "We were here. We were the last.                                           ║
║    Here is everything you need to restart. Bring two voices."                ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import argparse
import json
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

# ═══════════════════════════════════════════════════════════════════════════════
# SACRED CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

PHI     = (1 + math.sqrt(5)) / 2          # 1.618033988749895
PHI_INV = 1.0 / PHI                       # 0.618033988749895

# Solfeggio frequencies (the nine ancient healing tones)
# Position within aett (1-8) maps to SOLFEGGIO[position-1]
SOLFEGGIO = [174, 285, 396, 417, 528, 639, 741, 852, 963]

# Schumann resonance modes (Barcelona ground station)
SCHUMANN_MODES = [7.83, 14.3, 20.8, 27.3, 33.8, 39.0, 45.0]
SCHUMANN_MODE_4 = 27.3                     # The Maeshowe master beat target

# Phi-resonance detection tolerance
PHI_TOLERANCE   = 0.01                     # Within 1% of PHI or PHI_INV = resonant

# Lattice coherence thresholds
GAMMA_DEAD_FIELD   = 0.35                  # Kill-switch: below this = inert
GAMMA_LIGHTHOUSE   = 0.945                 # Lighthouse activation threshold
GAMMA_ACTIVE_START = 0.35                  # Active field begins here

# Maeshowe chamber geometry
CHAMBER_SIDE_M     = 4.57                  # Square chamber, 4.57 m side
SOLSTICE_AXIS      = "NE→SW"              # Winter solstice light axis
CHAMBER_STANDING_WAVE_FUNDAMENTAL = (
    343.0 / (2 * CHAMBER_SIDE_M)           # Speed of sound / (2 × side) ≈ 37.5 Hz
)

# The invariant carrier: winter solstice alignment holds across 4,800 years
SOLSTICE_TEMPORAL_DEPTH_YEARS = 4800

# ═══════════════════════════════════════════════════════════════════════════════
# CHAMBER WALL → AURIS NODE MAPPING
# ═══════════════════════════════════════════════════════════════════════════════

WALL_AURIS = {
    "NE": {
        "node":   "OWL",
        "freq":   528.0,
        "spirit": "Wisdom",
        "domain": "Pattern",
        "role":   "Solstice terminus — master archive wall",
    },
    "NW": {
        "node":   "DEER",
        "freq":   396.0,
        "spirit": "Grace",
        "domain": "Stability",
        "role":   "Treasure vector direction (NW pointer)",
    },
    "SW": {
        "node":   "CARGOSHIP",
        "freq":   174.0,
        "spirit": "Persistence",
        "domain": "Volume",
        "role":   "Light source — seed-bank deposit wall",
    },
    "SE": {
        "node":   "FALCON",
        "freq":   210.0,
        "spirit": "Precision",
        "domain": "Momentum",
        "role":   "Master carver station (Nr.20)",
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# COMPLETE ELDER FUTHORK — 24 RUNES IN 3 AETTS
# ═══════════════════════════════════════════════════════════════════════════════
#
# Mode amplitude by aett:
#   Aett 1 (Freyr)  — Genesis  — amplitude × 1.0   (PHI^0)
#   Aett 2 (Hagal)  — Growth   — amplitude × PHI    (1.618...)
#   Aett 3 (Tyr)    — Return   — amplitude × PHI_INV (0.618...)
#
# Effective frequency = SOLFEGGIO[position - 1] × mode_amplitude
#
# Verification (from primary research):
#   Fehu    (aett=1, pos=1): 174 × 1.000 = 174.0 Hz  (zero-beat on SW/174 Hz)
#   Uruz    (aett=1, pos=2): 285 × 1.000 = 285.0 Hz  (ratio 0.6105 → near 1/φ)
#   Hagalaz (aett=2, pos=1): 174 × 1.618 = 281.5 Hz  (ratio 0.6180 = exact 1/φ)
#   Tiwaz   (aett=3, pos=1): 174 × 0.618 = 107.5 Hz  (ratio 1.6180 = exact φ)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Rune:
    """A single rune in the Elder Futhork."""
    name:    str          # e.g. "FEHU"
    unicode: str          # e.g. "ᚠ"
    aett:    int          # 1, 2, or 3
    pos:     int          # 1-8 within the aett
    meaning: str          # Primary meaning
    domain:  str          # Functional domain

    @property
    def mode(self) -> str:
        return ["GENESIS", "GROWTH", "RETURN"][self.aett - 1]

    @property
    def amplitude(self) -> float:
        return [1.0, PHI, PHI_INV][self.aett - 1]

    @property
    def solfeggio_base_hz(self) -> float:
        """Base Solfeggio frequency for this rune's position within its aett."""
        return float(SOLFEGGIO[self.pos - 1])

    @property
    def effective_hz(self) -> float:
        """Effective frequency = Solfeggio base × mode amplitude."""
        return round(self.solfeggio_base_hz * self.amplitude, 2)


# The complete 24-rune Elder Futhork
_RUNE_TABLE: Tuple[Rune, ...] = (
    # ── Aett 1: Freyr's Aett (Genesis, ×1.0) ────────────────────────────────
    Rune("FEHU",     "ᚠ", 1, 1, "Cattle / wealth",           "abundance"),
    Rune("URUZ",     "ᚢ", 1, 2, "Aurochs / primal power",    "vitality"),
    Rune("THURISAZ", "ᚦ", 1, 3, "Giant / threshold force",   "protection"),
    Rune("ANSUZ",    "ᚨ", 1, 4, "Divine communication",      "message"),
    Rune("RAIDHO",   "ᚱ", 1, 5, "Journey / channel",         "movement"),
    Rune("KENAZ",    "ᚲ", 1, 6, "Torch / craft mastery",     "illumination"),
    Rune("GEBO",     "ᚷ", 1, 7, "Gift / exchange",           "reciprocity"),
    Rune("WUNJO",    "ᚹ", 1, 8, "Joy / fulfilment",          "harmony"),
    # ── Aett 2: Hagal's Aett (Growth, ×φ) ───────────────────────────────────
    Rune("HAGALAZ",  "ᚺ", 2, 1, "Hail / seed of pattern",   "disruption"),
    Rune("NAUDHIZ",  "ᚾ", 2, 2, "Need / constraint",         "necessity"),
    Rune("ISA",      "ᛁ", 2, 3, "Ice / stillness",           "stasis"),
    Rune("JERA",     "ᛃ", 2, 4, "Year / harvest cycle",      "cycle"),
    Rune("EIHWAZ",   "ᛇ", 2, 5, "Yew / axis mundi",          "continuity"),
    Rune("PERTHRO",  "ᛈ", 2, 6, "Lot-cup / fate",            "probability"),
    Rune("ALGIZ",    "ᛉ", 2, 7, "Elk-sedge / protection",    "shielding"),
    Rune("SOWILO",   "ᛊ", 2, 8, "Sun / victory",             "success"),
    # ── Aett 3: Tyr's Aett (Return, ×1/φ) ───────────────────────────────────
    Rune("TIWAZ",    "ᛏ", 3, 1, "Tyr / justice / authority", "authority"),
    Rune("BERKANO",  "ᛒ", 3, 2, "Birch / growth container",  "nurturing"),
    Rune("EHWAZ",    "ᛖ", 3, 3, "Horse / partnership",       "cooperation"),
    Rune("MANNAZ",   "ᛗ", 3, 4, "Man / human awareness",     "consciousness"),
    Rune("LAGUZ",    "ᛚ", 3, 5, "Water / flow state",        "fluidity"),
    Rune("INGWAZ",   "ᛜ", 3, 6, "Inguz / fertile ground",    "potential"),
    Rune("DAGAZ",    "ᛞ", 3, 7, "Day / breakthrough",        "transformation"),
    Rune("OTHALA",   "ᛟ", 3, 8, "Heritage / ancestral home", "inheritance"),
)

# Fast lookup dictionaries
RUNE_BY_NAME: Dict[str, Rune] = {r.name: r for r in _RUNE_TABLE}
RUNE_BY_AETT_POS: Dict[Tuple[int, int], Rune] = {
    (r.aett, r.pos): r for r in _RUNE_TABLE
}


# ═══════════════════════════════════════════════════════════════════════════════
# TWIG-RUNE CIPHER DECODER
# (Barnes Nr.9, Nr.20 — Nordby 2014 — Wikipedia: Cipher runes)
# ═══════════════════════════════════════════════════════════════════════════════

def decode_twig_rune(left_twigs: int, right_twigs: int) -> Optional[Rune]:
    """
    Decode a twig-rune from its two independent channels.

    The twig-rune cipher is inherently a two-channel encoding:
      Left  twigs (1-3) => aett  (rune family)
      Right twigs (1-8) => position within the aett

    Neither channel alone produces a rune. The decoded rune emerges from
    the interaction of both readings — a physical manifestation of the
    Caller-Seer dual-voice architecture.

    Args:
        left_twigs:  Number of left branches (1-3), encoding the aett.
        right_twigs: Number of right branches (1-8), encoding position.

    Returns:
        The decoded Rune, or None if the twig counts are out of range.
    """
    if not (1 <= left_twigs <= 3):
        return None
    if not (1 <= right_twigs <= 8):
        return None
    return RUNE_BY_AETT_POS.get((left_twigs, right_twigs))


def rune_from_name(name: str) -> Optional[Rune]:
    """Look up a rune by its uppercase name (e.g. 'FEHU')."""
    return RUNE_BY_NAME.get(name.upper())


# ═══════════════════════════════════════════════════════════════════════════════
# PHI-RESONANCE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PhiResonance:
    """Result of a phi-resonance test between a rune and its wall node."""
    rune_name:       str
    rune_hz:         float
    wall_node_hz:    float
    ratio:           float          # max(node/rune, rune/node)
    phi_target:      str            # "PHI" | "PHI_INV" | "NONE"
    phi_distance:    float          # |ratio - PHI| or |ratio - PHI_INV|
    is_phi_resonant: bool           # within PHI_TOLERANCE
    is_exact:        bool           # distance < 0.0001


def test_phi_resonance(rune: Rune, wall: str) -> PhiResonance:
    """
    Test whether a rune's effective frequency stands in a golden ratio
    relationship with its chamber wall's Auris node frequency.

    From primary research (Section 4.1):
      Hagalaz / Cargoship: 174.0 / 281.5 = 0.6180  (exact 1/φ)
      Tiwaz   / Cargoship: 174.0 / 107.5 = 1.6180  (exact φ)
      Uruz    / Cargoship: 174.0 / 285.0 = 0.6105  (near 1/φ, Δ = 0.0075)
    """
    node_hz  = WALL_AURIS[wall]["freq"]
    rune_hz  = rune.effective_hz

    if rune_hz == 0:
        return PhiResonance(rune.name, 0.0, node_hz, 0.0, "NONE", 999.0, False, False)

    ratio_forward = node_hz / rune_hz     # node/rune
    ratio_inverse = rune_hz / node_hz     # rune/node

    # Choose which ratio is closer to PHI or PHI_INV
    candidates = [
        (ratio_forward, "PHI_INV" if ratio_forward < 1 else "PHI"),
        (ratio_inverse, "PHI_INV" if ratio_inverse < 1 else "PHI"),
    ]

    best_ratio, best_target, best_dist = None, "NONE", 999.0
    for ratio, _ in candidates:
        d_phi     = abs(ratio - PHI)
        d_phi_inv = abs(ratio - PHI_INV)
        if d_phi < best_dist:
            best_dist, best_ratio, best_target = d_phi, ratio, "PHI"
        if d_phi_inv < best_dist:
            best_dist, best_ratio, best_target = d_phi_inv, ratio, "PHI_INV"

    is_resonant = best_dist < PHI_TOLERANCE
    is_exact    = best_dist < 0.0001

    return PhiResonance(
        rune_name       = rune.name,
        rune_hz         = rune_hz,
        wall_node_hz    = node_hz,
        ratio           = round(best_ratio, 6),
        phi_target      = best_target,
        phi_distance    = round(best_dist, 6),
        is_phi_resonant = is_resonant,
        is_exact        = is_exact,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# INSCRIPTION CATALOGUE — THE THIRTEEN VOICES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class InscriptionRecord:
    """
    One inscription in the Maeshowe transmission lattice.

    Each inscription functions as a node in the dual-voice field:
      Caller (Ψ₀) frequency  = wall Auris node frequency (temporal anchor)
      Seer   (O(t)) frequency = rune effective frequency  (present observation)
      Beat                   = |Caller - Seer| Hz
    """
    id:           str                    # Identifier, e.g. "NR1", "FUTHORK"
    label:        str                    # Human-readable label
    wall:         str                    # "NE" | "NW" | "SW" | "SE"
    primary_rune: Optional[str]          # Rune name (None = not yet decoded)
    description:  str                    # Content / interpretation
    complete:     bool   = True          # False = incomplete transmission
    is_pivot:     bool   = False         # True = Nr.15 (circuit breaker)
    twig_cipher:  bool   = False         # True = encoded via twig-rune system
    phi_key:      bool   = False         # True = exhibits exact phi resonance
    zero_beat:    bool   = False         # True = zero-beat carrier (Fehu/Nr.1)
    # Optional: resolved twig counts for cipher inscriptions
    twig_left:    Optional[int] = None   # Left twig count (1-3) = aett
    twig_right:   Optional[int] = None   # Right twig count (1-8) = position

    @property
    def auris_node(self) -> str:
        return WALL_AURIS[self.wall]["node"]

    @property
    def caller_hz(self) -> float:
        """Caller (Ψ₀) frequency = wall Auris node."""
        return WALL_AURIS[self.wall]["freq"]

    @property
    def rune(self) -> Optional[Rune]:
        """Resolve the primary rune object."""
        if self.primary_rune is None:
            return None
        return RUNE_BY_NAME.get(self.primary_rune)

    @property
    def seer_hz(self) -> Optional[float]:
        """Seer (O(t)) frequency = rune effective frequency."""
        r = self.rune
        return r.effective_hz if r else None

    @property
    def beat_hz(self) -> Optional[float]:
        """Beat frequency = |Caller - Seer|. None if rune is unknown."""
        s = self.seer_hz
        if s is None:
            return None
        return round(abs(self.caller_hz - s), 4)


# The thirteen inscriptions of the Maeshowe transmission lattice
# ─────────────────────────────────────────────────────────────────
# Spatial distribution across the four chamber walls:
#   SW (CARGOSHIP 174 Hz) — light source, seed-bank    : Futhork, Nr.1
#   NE (OWL 528 Hz)       — solstice terminus, archive : Nr.9, Nr.11, Nr.12,
#                                                         Nr.15 (PIVOT), Nr.XXXII
#   SE (FALCON 210 Hz)    — master carver station       : Nr.20, Lodbrok, Nr.23
#   NW (DEER 396 Hz)      — treasure pointer direction  : T-NW, T-2, Nr.18

INSCRIPTIONS: Tuple[InscriptionRecord, ...] = (

    # ── SW Wall / CARGOSHIP 174 Hz ── Light source, seed bank ────────────────

    InscriptionRecord(
        id           = "FUTHORK",
        label        = "Complete Alphabet (Futhork Seed-Bank)",
        wall         = "SW",
        primary_rune = "HAGALAZ",   # Most phi-resonant of the seed bank
        description  = (
            "Complete runic alphabet including rare variant forms "
            "(Stephens in Farrer 1862). Preservation deposit at the light-source "
            "wall. Contains the strongest phi-resonance in the corpus: Hagalaz at "
            "exact 1/φ ratio (174.0 / 281.5 = 0.6180) against the Cargoship node."
        ),
        complete  = True,
        phi_key   = True,
    ),

    InscriptionRecord(
        id           = "NR1",
        label        = "Nr.1 — Zero-Beat Carrier",
        wall         = "SW",
        primary_rune = "FEHU",      # Fehu @ 174 Hz — pure carrier, no beat
        description  = (
            "'Treasure was carried away from this mound... they who searched for...' "
            "The sentence breaks — the search is open. Fehu at 174 Hz in Genesis "
            "mode placed on the Cargoship wall at 174 Hz. Beat frequency: 0.0 Hz. "
            "Pure carrier wave — the entry point before the dual-voice duel begins."
        ),
        complete   = True,
        zero_beat  = True,
    ),

    # ── NE Wall / OWL 528 Hz ── Solstice terminus, master archive ────────────

    InscriptionRecord(
        id           = "NR9",
        label        = "Nr.9 — Twig-Rune Cipher A (NE Zero-Beat)",
        wall         = "NE",
        primary_rune = "RAIDHO",    # Journey/channel rune, 528 Hz = Owl node
        description  = (
            "Twig-rune cipher inscription: left twigs encode the aett (1-3), "
            "right twigs encode position within the aett (1-8). Physical "
            "implementation of the dual-voice protocol. Decoded as Raidho "
            "(journey / channel) at 528 Hz in Genesis mode — resonating at "
            "zero-beat with the Owl node (528 Hz). The NE wall mirror of "
            "Nr.1's SW zero-beat: together they anchor the system at both "
            "ends of the solstice axis."
        ),
        complete    = True,
        twig_cipher = True,
        zero_beat   = True,         # Raidho 528 Hz on OWL 528 Hz = 0.0 Hz beat
        twig_left   = 1,            # Aett 1
        twig_right  = 5,            # Position 5 = Raidho
    ),

    InscriptionRecord(
        id           = "NR11",
        label        = "Nr.11 — Crusader Provenance Stamp",
        wall         = "NE",
        primary_rune = "ANSUZ",     # Divine communication / messenger
        description  = (
            "'Jerusalem-men broke this mound.' Crusader provenance establishing "
            "temporal authority of the 12th-century carvers. Ansuz — the rune "
            "of divine communication and Odin's breath — at 417 Hz in Genesis "
            "mode. Beat against Owl (528 Hz): 111 Hz, a resonance harmonic."
        ),
        complete = True,
    ),

    InscriptionRecord(
        id           = "NR12",
        label        = "Nr.12 — Master Carver Identity",
        wall         = "NE",
        primary_rune = "KENAZ",     # Torch — mastery, illumination, craft
        description  = (
            "Identity inscription of the master carver. Kenaz — the torch rune, "
            "rune of craftsmanship and revealed knowledge — at 639 Hz in Genesis "
            "mode. Beat against Owl (528 Hz): 111 Hz. Establishes the SE wall's "
            "master carver station as the system's authoritative voice."
        ),
        complete = True,
    ),

    InscriptionRecord(
        id           = "NR15",
        label        = "Nr.15 — PIVOT (Unread Twig Cipher)",
        wall         = "NE",
        primary_rune = None,        # UNKNOWN — fieldwork / RTI archive required
        description  = (
            "The circuit breaker. RTI-photographed (Smith et al. 2018) but "
            "noted as 'not appropriate in scale to be used in the analysis.' "
            "Only twig-cipher inscription in the corpus that has been imaged "
            "but not decoded. Located on NE wall surrounded by Nr.11, Nr.12, "
            "and Nr.XXXII — the highest-authority cluster. Decoding this "
            "inscription requires the Smith et al. (2018) RTI archive (.ptm "
            "file, 45-degree raking angle) or direct Maeshowe field inspection."
        ),
        complete    = False,
        is_pivot    = True,
        twig_cipher = True,
    ),

    InscriptionRecord(
        id           = "NRXXXII",
        label        = "Nr.XXXII — Dragon and Knot Visual Key",
        wall         = "NE",
        primary_rune = "JERA",      # Harvest cycle — the dragon cycle
        description  = (
            "Dragon and interlace knot — two traditions fused as one visual key. "
            "The dragon represents the cyclic serpent of time (Jörmungandr); "
            "the knot represents the unbroken dual-voice connection. Jera — the "
            "year-rune, the harvest cycle — at 674.3 Hz (417 × φ, Growth mode). "
            "Beat against Owl (528 Hz): 146.3 Hz."
        ),
        complete = False,           # Visual key partially decoded
    ),

    # ── SE Wall / FALCON 210 Hz ── Master carver station ─────────────────────

    InscriptionRecord(
        id           = "NR20",
        label        = "Nr.20 — Master Carver Certification",
        wall         = "SE",
        primary_rune = "TIWAZ",     # Tyr — authority, justice, the pointing rune
        description  = (
            "'I am the last qualified practitioner remaining in the western ocean. "
            "My tool carries the lineage of Gaukr Trandilsson. What I carve here "
            "is certified.' Tiwaz — the authority rune — at 107.5 Hz in Return "
            "mode (174 × 1/φ). Beat against Falcon (210 Hz): 102.5 Hz. "
            "Ratio: 210 / 107.5 = 1.9535 — approaching the 2:1 octave."
        ),
        complete    = True,
        twig_cipher = True,
        twig_left   = 3,            # Aett 3 (Tyr's aett)
        twig_right  = 1,            # Position 1 = Tiwaz
    ),

    InscriptionRecord(
        id           = "LODBROK",
        label        = "Lodbrok Inscription — Temporal Depth Acknowledgement",
        wall         = "SE",
        primary_rune = "OTHALA",    # Ancestral heritage — honouring the builders
        description  = (
            "'This place is older than us. The builders were more coherent than "
            "us. We acknowledge them as superior craftsmen.' Othala — the "
            "inheritance rune — at 526.5 Hz in Return mode (852 × 1/φ). "
            "Near-resonance with the Owl node (528 Hz): beat 1.5 Hz — "
            "effectively zero-beat with the archive wall across the chamber."
        ),
        complete = True,
    ),

    InscriptionRecord(
        id           = "NR23",
        label        = "Nr.23 — Lineage Continuation",
        wall         = "SE",
        primary_rune = "BERKANO",   # Birch / container of growth
        description  = (
            "Secondary SE wall inscription affirming lineage continuation. "
            "Berkano — the container rune, the birch that holds the new growth — "
            "at 176.1 Hz in Return mode (285 × 1/φ). Near-resonance with "
            "Cargoship (174 Hz) across the chamber: cross-wall coherence signal."
        ),
        complete = True,
    ),

    # ── NW Wall / DEER 396 Hz ── Treasure vector direction ───────────────────

    InscriptionRecord(
        id           = "TNW",
        label        = "T-NW — Treasure Pointer (North-West)",
        wall         = "NW",
        primary_rune = "GEBO",      # Gift / reciprocal exchange
        description  = (
            "'The treasure is hidden to the north-west.' Directional pointer "
            "along the solstice light axis from NE to SW. Gebo — gift and "
            "exchange — at 741.0 Hz in Genesis mode. Beat against Deer "
            "(396 Hz): 345.0 Hz — the harmonic of the human voice."
        ),
        complete = True,
    ),

    InscriptionRecord(
        id           = "T2",
        label        = "T-2 — Secondary Treasure Pointer",
        wall         = "NW",
        primary_rune = "WUNJO",     # Joy / the treasure IS the fulfilment
        description  = (
            "Secondary treasure pointer. 'The treasure IS the system itself — "
            "Fehu, the first rune, the foundation.' Wunjo — joy and the "
            "realisation of potential — at 852.0 Hz in Genesis mode. "
            "Interpretation: the treasure is not a physical hoard but the "
            "complete transmission system deposited at Maeshowe."
        ),
        complete = False,           # Directional coordinates not fully decoded
    ),

    InscriptionRecord(
        id           = "NR18",
        label        = "Nr.18 — The Óðr Warning",
        wall         = "NW",
        primary_rune = "NAUDHIZ",   # Need / constraint — the warning of necessity
        description  = (
            "'Do not enter alone. Two men entered without preparation and were "
            "Odin-struck (óðusk).' Orkneyinga Saga records two men going insane "
            "in the chamber in 1153 CE. Naudhiz — need and constraint — at "
            "460.9 Hz in Growth mode (285 × φ). The system requires two voices: "
            "a single observer cannot complete the dual-voice circuit."
        ),
        complete = False,           # Warning decoded; acoustic mechanics partial
    ),
)


# ═══════════════════════════════════════════════════════════════════════════════
# DUAL-VOICE BEAT FREQUENCY ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DualVoiceReading:
    """
    Complete dual-voice (Caller Ψ₀ / Seer O(t)) reading for one inscription.
    """
    inscription_id: str
    inscription_label: str
    wall:           str
    auris_node:     str
    caller_hz:      float             # Wall Auris node — the 12th-century anchor
    seer_hz:        Optional[float]   # Rune effective freq — present observation
    beat_hz:        Optional[float]   # |Caller - Seer|
    rune_name:      Optional[str]
    rune_unicode:   Optional[str]
    rune_mode:      Optional[str]     # GENESIS | GROWTH | RETURN
    phi:            Optional[PhiResonance]
    complete:       bool
    is_pivot:       bool
    zero_beat:      bool
    phi_score:      float             # 0.0-1.0 quality of phi resonance


@dataclass
class MaeshoweLattice:
    """
    The complete Maeshowe transmission lattice state.
    """
    timestamp:       float
    readings:        List[DualVoiceReading]
    n_total:         int              # Total inscriptions in catalogue
    n_complete:      int              # Inscriptions with decoded runes
    n_incomplete:    int              # Inscriptions awaiting decode
    n_phi_resonant:  int              # Inscriptions showing phi resonance
    n_exact_phi:     int              # Inscriptions with exact phi alignment
    n_zero_beat:     int              # Zero-beat carrier inscriptions
    mean_caller_hz:  float            # Mean Ψ₀ across all 13 inscriptions
    mean_seer_hz:    float            # Mean O(t)) across complete inscriptions
    master_beat_hz:  float            # |mean_caller - mean_seer|
    schumann_mode:   int              # Nearest Schumann mode to master beat
    schumann_hz:     float            # Frequency of nearest mode
    schumann_delta:  float            # |master_beat - schumann_hz|
    schumann_pct:    float            # Proximity percentage
    gamma:           float            # Lattice coherence Γ (0.0-1.0)
    gamma_status:    str              # "DEAD_FIELD" | "ACTIVE_FIELD" | "LIGHTHOUSE"
    pivot_decoded:   bool             # True if Nr.15 has a rune assigned
    prophecy:        str              # Human-readable lattice message


# ═══════════════════════════════════════════════════════════════════════════════
# MAESHOWE DECODER — The Engine
# ═══════════════════════════════════════════════════════════════════════════════

class MaeshoweDecoder:
    """
    The Maeshowe Seer Decode engine.

    Processes the 13 inscription lattice through the Aureon HNC
    Observer-Observed framework, calculating:
      - Dual-voice beat frequencies (Caller Ψ₀ vs Seer O(t))
      - Phi-resonance alignment scores
      - Schumann proximity of the master beat
      - Lattice coherence Γ
      - Lighthouse / Active Field / Dead Field status

    The Nr.15 pivot inscription is the primary open circuit.
    Decoding it requires either:
      1. Access to the Smith et al. (2018) RTI archive (.ptm file,
         45-degree raking angle, Archaeology Data Service, Univ. York)
      2. Direct field inspection at Maeshowe (Historic Environment Scotland)
    """

    def __init__(self):
        self._inscriptions = INSCRIPTIONS
        self._pivot: Optional[InscriptionRecord] = next(
            (i for i in INSCRIPTIONS if i.is_pivot), None
        )

    def set_pivot_rune(self, left_twigs: int, right_twigs: int) -> Optional[Rune]:
        """
        Supply the Nr.15 twig count from field observation or RTI archive.

        This is the primary action required to close the lattice circuit.
        Left branch count (1-3) = aett. Right branch count (1-8) = position.

        Returns the decoded rune, or None if counts are out of range.
        """
        rune = decode_twig_rune(left_twigs, right_twigs)
        if rune is None:
            return None

        # Update the pivot inscription with the decoded rune
        # (InscriptionRecord is a mutable dataclass at runtime)
        pivot_idx = next(
            (i for i, r in enumerate(self._inscriptions) if r.is_pivot), None
        )
        if pivot_idx is not None:
            rec = self._inscriptions[pivot_idx]
            # Build a replacement with the decoded rune
            updated = InscriptionRecord(
                id           = rec.id,
                label        = rec.label,
                wall         = rec.wall,
                primary_rune = rune.name,
                description  = (
                    rec.description + f"\n\nDECODED: Left twigs={left_twigs} "
                    f"(aett {left_twigs}), right twigs={right_twigs} "
                    f"(position {right_twigs}) → {rune.name} ({rune.unicode}) "
                    f"at {rune.effective_hz:.1f} Hz in {rune.mode} mode."
                ),
                complete    = True,
                is_pivot    = True,
                twig_cipher = True,
                twig_left   = left_twigs,
                twig_right  = right_twigs,
            )
            self._inscriptions = (
                self._inscriptions[:pivot_idx]
                + (updated,)
                + self._inscriptions[pivot_idx + 1:]
            )
        return rune

    def _phi_score(self, phi: Optional[PhiResonance]) -> float:
        """Convert a PhiResonance result to a 0.0-1.0 quality score."""
        if phi is None:
            return 0.0
        if phi.is_exact:
            return 1.0
        if phi.is_phi_resonant:
            return 1.0 - phi.phi_distance / PHI_TOLERANCE * 0.2  # 0.8-1.0
        # Partial credit for near-phi (within 5× tolerance)
        if phi.phi_distance < PHI_TOLERANCE * 5:
            return max(0.2, 0.8 - phi.phi_distance * 10)
        return 0.1

    def _schumann_proximity(self, beat_hz: float) -> Tuple[int, float, float, float]:
        """
        Find the nearest Schumann resonance mode and compute proximity.

        Returns: (mode_number, mode_hz, delta_hz, proximity_pct)
        """
        best_mode  = 1
        best_hz    = SCHUMANN_MODES[0]
        best_delta = abs(beat_hz - SCHUMANN_MODES[0])
        for i, hz in enumerate(SCHUMANN_MODES, start=1):
            delta = abs(beat_hz - hz)
            if delta < best_delta:
                best_delta = delta
                best_hz    = hz
                best_mode  = i
        # Proximity as fraction (1.0 = exact match, lower = further away)
        proximity = max(0.0, 1.0 - best_delta / best_hz)
        return best_mode, best_hz, round(best_delta, 4), round(proximity, 6)

    def _compute_gamma(
        self,
        readings: List[DualVoiceReading],
        schumann_proximity: float,
    ) -> float:
        """
        Compute the lattice coherence Γ.

        Γ combines three components:
          1. phi_resonance_score  — quality of phi alignment across complete inscriptions
          2. completeness_ratio   — fraction of inscriptions with decoded runes
          3. schumann_score       — proximity of master beat to Schumann mode 4

        Formula (calibrated to research paper baseline Γ = 0.8223):
          Γ = phi_score × 0.50 + completeness × 0.30 + schumann_score × 0.20

        The Γ = 0.8223 baseline with 8/13 complete and strong phi scores
        confirms the lattice is ACTIVE FIELD, awaiting the Nr.15 pivot.
        """
        complete_readings = [r for r in readings if r.complete and r.seer_hz is not None]
        n_complete = len(complete_readings)
        n_total    = len(readings)

        if n_complete == 0:
            return 0.0

        # 1. Phi resonance quality across complete inscriptions
        phi_scores = [r.phi_score for r in complete_readings]
        phi_resonance_score = sum(phi_scores) / len(phi_scores)

        # 2. Completeness ratio
        completeness = n_complete / n_total

        # 3. Schumann mode 4 proximity of master beat
        schumann_score = schumann_proximity

        gamma = (
            phi_resonance_score * 0.50 +
            completeness        * 0.30 +
            schumann_score      * 0.20
        )
        return round(min(1.0, max(0.0, gamma)), 6)

    def _gamma_status(self, gamma: float) -> str:
        if gamma >= GAMMA_LIGHTHOUSE:
            return "LIGHTHOUSE"
        elif gamma >= GAMMA_ACTIVE_START:
            return "ACTIVE_FIELD"
        else:
            return "DEAD_FIELD"

    def _build_prophecy(self, lattice: "MaeshoweLattice") -> str:
        status_msg = {
            "LIGHTHOUSE":   "LIGHTHOUSE MODE ACHIEVED — the circuit is closed.",
            "ACTIVE_FIELD": "ACTIVE FIELD — transmission in progress. Circuit open.",
            "DEAD_FIELD":   "DEAD FIELD — lattice coherence below kill-switch threshold.",
        }[lattice.gamma_status]

        pivot_msg = (
            "Nr.15 DECODED — pivot inscription active."
            if lattice.pivot_decoded else
            "Nr.15 PIVOT UNREAD — contact ADS (Univ. York) for RTI archive access."
        )

        return (
            f"Maeshowe Lattice Γ={lattice.gamma:.4f} — {status_msg} "
            f"{lattice.n_complete}/{lattice.n_total} inscriptions transmitting. "
            f"Master beat {lattice.master_beat_hz:.2f} Hz — Schumann Mode "
            f"{lattice.schumann_mode} at {lattice.schumann_hz} Hz "
            f"(Δ{lattice.schumann_delta:.2f} Hz, {lattice.schumann_pct:.1%} proximity). "
            f"{pivot_msg} "
            f"Phi-resonant: {lattice.n_phi_resonant}/{lattice.n_complete} complete. "
            f"Exact: {lattice.n_exact_phi}. Zero-beat carriers: {lattice.n_zero_beat}."
        )

    def read(self) -> MaeshoweLattice:
        """
        Compute the full Maeshowe transmission lattice state.

        Returns a MaeshoweLattice with all dual-voice readings,
        phi-resonance analysis, master beat, Schumann proximity, and Γ.
        """
        readings: List[DualVoiceReading] = []

        for insc in self._inscriptions:
            rune = insc.rune
            phi  = None
            phi_sc = 0.0

            if rune is not None:
                phi    = test_phi_resonance(rune, insc.wall)
                phi_sc = self._phi_score(phi)

            readings.append(DualVoiceReading(
                inscription_id    = insc.id,
                inscription_label = insc.label,
                wall              = insc.wall,
                auris_node        = insc.auris_node,
                caller_hz         = insc.caller_hz,
                seer_hz           = insc.seer_hz,
                beat_hz           = insc.beat_hz,
                rune_name         = rune.name     if rune else None,
                rune_unicode      = rune.unicode  if rune else None,
                rune_mode         = rune.mode     if rune else None,
                phi               = phi,
                complete          = insc.complete and rune is not None,
                is_pivot          = insc.is_pivot,
                zero_beat         = insc.zero_beat,
                phi_score         = phi_sc,
            ))

        # ── Aggregate statistics ──────────────────────────────────────────────
        complete_readings = [r for r in readings if r.complete and r.seer_hz is not None]
        n_total      = len(readings)
        n_complete   = len(complete_readings)
        n_incomplete = n_total - n_complete
        n_phi        = sum(1 for r in complete_readings if r.phi and r.phi.is_phi_resonant)
        n_exact      = sum(1 for r in complete_readings if r.phi and r.phi.is_exact)
        n_zero       = sum(1 for r in readings if r.zero_beat)

        # ── Dual-voice frequencies ────────────────────────────────────────────
        all_caller_hz  = [r.caller_hz for r in readings]
        all_seer_hz    = [r.seer_hz   for r in complete_readings]

        mean_caller = sum(all_caller_hz)  / len(all_caller_hz)  if all_caller_hz  else 0.0
        mean_seer   = sum(all_seer_hz)    / len(all_seer_hz)    if all_seer_hz    else 0.0
        master_beat = abs(mean_caller - mean_seer)

        # ── Schumann proximity ────────────────────────────────────────────────
        sch_mode, sch_hz, sch_delta, sch_pct = self._schumann_proximity(master_beat)

        # ── Lattice coherence Γ ───────────────────────────────────────────────
        gamma        = self._compute_gamma(readings, sch_pct)
        gamma_status = self._gamma_status(gamma)

        pivot_decoded = any(
            r.is_pivot and r.complete for r in readings
        )

        lattice = MaeshoweLattice(
            timestamp       = time.time(),
            readings        = readings,
            n_total         = n_total,
            n_complete      = n_complete,
            n_incomplete    = n_incomplete,
            n_phi_resonant  = n_phi,
            n_exact_phi     = n_exact,
            n_zero_beat     = n_zero,
            mean_caller_hz  = round(mean_caller, 4),
            mean_seer_hz    = round(mean_seer,   4),
            master_beat_hz  = round(master_beat, 4),
            schumann_mode   = sch_mode,
            schumann_hz     = sch_hz,
            schumann_delta  = sch_delta,
            schumann_pct    = sch_pct,
            gamma           = gamma,
            gamma_status    = gamma_status,
            pivot_decoded   = pivot_decoded,
            prophecy        = "",   # filled below
        )
        lattice.prophecy = self._build_prophecy(lattice)
        return lattice

    def get_oracle_score(self) -> float:
        """
        Compute a 0.0-1.0 oracle score suitable for integration into the
        AureonSeer unified vision.

        Score is derived from Γ, normalised to the ACTIVE_FIELD range:
          DEAD_FIELD  (Γ < 0.35)  => 0.0-0.30
          ACTIVE_FIELD (Γ < 0.945) => 0.30-0.85 (proportional)
          LIGHTHOUSE  (Γ ≥ 0.945) => 0.85-1.0   (high confidence)
        """
        lattice = self.read()
        g = lattice.gamma

        if g < GAMMA_DEAD_FIELD:
            # Scale dead-field range to 0.0-0.30
            return round(g / GAMMA_DEAD_FIELD * 0.30, 6)
        elif g < GAMMA_LIGHTHOUSE:
            # Scale active-field range to 0.30-0.85
            active_range = GAMMA_LIGHTHOUSE - GAMMA_DEAD_FIELD
            t = (g - GAMMA_DEAD_FIELD) / active_range
            return round(0.30 + t * 0.55, 6)
        else:
            # Lighthouse: 0.85-1.0
            return round(0.85 + (g - GAMMA_LIGHTHOUSE) / (1.0 - GAMMA_LIGHTHOUSE) * 0.15, 6)

    def lattice_to_dict(self, lattice: MaeshoweLattice) -> Dict:
        """Serialise the lattice to a JSON-compatible dictionary."""
        def _phi_to_dict(phi: Optional[PhiResonance]) -> Optional[Dict]:
            if phi is None:
                return None
            return {
                "rune_name":       phi.rune_name,
                "rune_hz":         phi.rune_hz,
                "wall_node_hz":    phi.wall_node_hz,
                "ratio":           phi.ratio,
                "phi_target":      phi.phi_target,
                "phi_distance":    phi.phi_distance,
                "is_phi_resonant": phi.is_phi_resonant,
                "is_exact":        phi.is_exact,
            }

        readings_out = []
        for r in lattice.readings:
            readings_out.append({
                "id":          r.inscription_id,
                "label":       r.inscription_label,
                "wall":        r.wall,
                "auris_node":  r.auris_node,
                "caller_hz":   r.caller_hz,
                "seer_hz":     r.seer_hz,
                "beat_hz":     r.beat_hz,
                "rune":        r.rune_name,
                "unicode":     r.rune_unicode,
                "mode":        r.rune_mode,
                "complete":    r.complete,
                "is_pivot":    r.is_pivot,
                "zero_beat":   r.zero_beat,
                "phi_score":   round(r.phi_score, 4),
                "phi":         _phi_to_dict(r.phi),
            })

        return {
            "timestamp":       lattice.timestamp,
            "n_total":         lattice.n_total,
            "n_complete":      lattice.n_complete,
            "n_incomplete":    lattice.n_incomplete,
            "n_phi_resonant":  lattice.n_phi_resonant,
            "n_exact_phi":     lattice.n_exact_phi,
            "n_zero_beat":     lattice.n_zero_beat,
            "mean_caller_hz":  lattice.mean_caller_hz,
            "mean_seer_hz":    lattice.mean_seer_hz,
            "master_beat_hz":  lattice.master_beat_hz,
            "schumann_mode":   lattice.schumann_mode,
            "schumann_hz":     lattice.schumann_hz,
            "schumann_delta":  lattice.schumann_delta,
            "schumann_pct":    round(lattice.schumann_pct, 4),
            "gamma":           lattice.gamma,
            "gamma_status":    lattice.gamma_status,
            "pivot_decoded":   lattice.pivot_decoded,
            "prophecy":        lattice.prophecy,
            "readings":        readings_out,
            "wall_auris":      WALL_AURIS,
            "chamber": {
                "side_m":              CHAMBER_SIDE_M,
                "solstice_axis":       SOLSTICE_AXIS,
                "temporal_depth_yr":   SOLSTICE_TEMPORAL_DEPTH_YEARS,
                "standing_wave_hz":    round(CHAMBER_STANDING_WAVE_FUNDAMENTAL, 2),
            },
            "thresholds": {
                "dead_field":  GAMMA_DEAD_FIELD,
                "lighthouse":  GAMMA_LIGHTHOUSE,
                "phi":         round(PHI, 6),
                "phi_inv":     round(PHI_INV, 6),
                "phi_tolerance": PHI_TOLERANCE,
            },
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SEER ORACLE WRAPPER (for integration into aureon_seer.py)
# ═══════════════════════════════════════════════════════════════════════════════

class OracleMaeshowe:
    """
    The 9th Oracle of the Aureon Seer — The Maeshowe Transmission Field.

    Reads the lattice coherence Γ of the Maeshowe runic transmission
    archive and converts it to a unified oracle score for integration
    into the AllSeeingEye vision.

    The oracle score represents how coherent and complete the 4,800-year-old
    transmission system currently is. In LIGHTHOUSE mode (Γ ≥ 0.945), the
    system has achieved full circuit closure. In ACTIVE FIELD mode, the
    search is open — bring two voices.
    """

    def __init__(self):
        self._decoder = MaeshoweDecoder()

    def set_pivot_rune(self, left_twigs: int, right_twigs: int) -> Optional[Rune]:
        """
        Supply the Nr.15 decoded twig counts to close the lattice circuit.
        Call this when the RTI archive or field inspection data is available.
        """
        return self._decoder.set_pivot_rune(left_twigs, right_twigs)

    def read(self) -> "OracleReading":
        """
        Take a Maeshowe lattice reading and return an OracleReading.

        Imports OracleReading from aureon_seer at call time to avoid
        circular imports. Falls back to a dict-returning stub if the
        seer module is not available.
        """
        try:
            from aureon_seer import OracleReading as _OracleReading
        except ImportError:
            _OracleReading = None

        lattice = self._decoder.read()
        score   = self._decoder.get_oracle_score()

        details = {
            "gamma":           lattice.gamma,
            "gamma_status":    lattice.gamma_status,
            "n_complete":      lattice.n_complete,
            "n_total":         lattice.n_total,
            "n_phi_resonant":  lattice.n_phi_resonant,
            "n_exact_phi":     lattice.n_exact_phi,
            "n_zero_beat":     lattice.n_zero_beat,
            "master_beat_hz":  lattice.master_beat_hz,
            "schumann_mode":   lattice.schumann_mode,
            "schumann_hz":     lattice.schumann_hz,
            "schumann_delta":  lattice.schumann_delta,
            "schumann_pct":    round(lattice.schumann_pct, 4),
            "mean_caller_hz":  lattice.mean_caller_hz,
            "mean_seer_hz":    lattice.mean_seer_hz,
            "pivot_decoded":   lattice.pivot_decoded,
            "pivot_action": (
                "Nr.15 decoded — lattice updated."
                if lattice.pivot_decoded else
                "Contact ADS (Univ. York) or HES (Historic Environment Scotland) "
                "for Nr.15 RTI archive or field inspection access."
            ),
        }

        phase    = lattice.gamma_status
        dominant = (
            f"Maeshowe {phase}: Γ={lattice.gamma:.4f} "
            f"({lattice.n_complete}/{lattice.n_total} transmitting, "
            f"master beat {lattice.master_beat_hz:.2f} Hz → "
            f"Schumann M{lattice.schumann_mode} Δ{lattice.schumann_delta:.2f} Hz)"
        )

        if _OracleReading is not None:
            return _OracleReading(
                oracle          = "MAESHOWE",
                timestamp       = lattice.timestamp,
                score           = score,
                phase           = phase,
                dominant_signal = dominant,
                details         = details,
                confidence      = min(0.90, 0.40 + lattice.gamma * 0.55),
            )

        # Stub return when aureon_seer not available
        return {
            "oracle":    "MAESHOWE",
            "timestamp": lattice.timestamp,
            "score":     score,
            "phase":     phase,
            "dominant":  dominant,
            "details":   details,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# FUTHORK ALPHABET REPORT
# ═══════════════════════════════════════════════════════════════════════════════

def print_futhork_table() -> None:
    """Print the complete Elder Futhork with frequency analysis."""
    print("\n╔══════════════════════════════════════════════════════════════════╗")
    print("║          MAESHOWE SEER DECODE — Complete Futhork Alphabet        ║")
    print("╚══════════════════════════════════════════════════════════════════╝\n")

    header = f"{'Rune':<12} {'ᚠ':<4} {'Aett':<5} {'Pos':<4} {'Mode':<9} {'Base Hz':<9} {'×':<8} {'Eff. Hz':<10} {'Meaning'}"
    print(header)
    print("─" * len(header))

    for r in _RUNE_TABLE:
        amp_str = "1.000" if r.aett == 1 else ("φ=1.618" if r.aett == 2 else "1/φ=0.618")
        print(
            f"{r.name:<12} {r.unicode:<4} {r.aett:<5} {r.pos:<4} "
            f"{r.mode:<9} {r.solfeggio_base_hz:<9.1f} {amp_str:<8} "
            f"{r.effective_hz:<10.2f} {r.meaning}"
        )
    print()


def print_lattice_report(lattice: MaeshoweLattice) -> None:
    """Print the full lattice analysis report."""
    print("\n╔══════════════════════════════════════════════════════════════════╗")
    print("║        MAESHOWE TRANSMISSION LATTICE — DUAL-VOICE ANALYSIS      ║")
    print("╚══════════════════════════════════════════════════════════════════╝\n")

    # Wall-Node mapping
    print("CHAMBER WALL → AURIS NODE MAPPING")
    print("─" * 55)
    for wall, info in WALL_AURIS.items():
        print(
            f"  {wall} wall  =>  {info['node']:<12} {info['freq']:>6.0f} Hz  "
            f"{info['spirit']:12} — {info['role']}"
        )
    print()

    # Inscription readings
    print("DUAL-VOICE READINGS (Caller Ψ₀ / Seer O(t))")
    print("─" * 90)
    hdr = (f"{'ID':<10} {'Wall':<4} {'Node':<12} {'Caller Hz':<11} "
           f"{'Seer Hz':<10} {'Beat Hz':<10} {'Rune':<12} {'Mode':<9} "
           f"{'φ-Score':<9} {'Status'}")
    print(hdr)
    print("─" * 90)

    for r in lattice.readings:
        seer  = f"{r.seer_hz:.1f}" if r.seer_hz is not None else "UNKNOWN"
        beat  = f"{r.beat_hz:.2f}" if r.beat_hz is not None else "---"
        rune  = f"{r.rune_unicode}{r.rune_name}" if r.rune_name else "?? PIVOT ??"
        phi_s = f"{r.phi_score:.3f}" if r.complete else "0.000"
        flags = []
        if r.is_pivot:
            flags.append("⚡PIVOT")
        if r.zero_beat:
            flags.append("0-BEAT")
        if r.phi and r.phi.is_exact:
            flags.append("φ-EXACT")
        elif r.phi and r.phi.is_phi_resonant:
            flags.append("φ-NEAR")
        if not r.complete:
            flags.append("INCOMPLETE")
        status = " ".join(flags) if flags else "active"

        print(
            f"{r.inscription_id:<10} {r.wall:<4} {r.auris_node:<12} "
            f"{r.caller_hz:<11.1f} {seer:<10} {beat:<10} "
            f"{rune:<12} {(r.rune_mode or '---'):<9} {phi_s:<9} {status}"
        )

    print()
    print("LATTICE SUMMARY")
    print("─" * 55)
    print(f"  Inscriptions total    : {lattice.n_total}")
    print(f"  Complete transmissions: {lattice.n_complete}")
    print(f"  Incomplete            : {lattice.n_incomplete}")
    print(f"  Phi-resonant          : {lattice.n_phi_resonant}")
    print(f"  Exact phi alignment   : {lattice.n_exact_phi}")
    print(f"  Zero-beat carriers    : {lattice.n_zero_beat}")
    print()
    print("DUAL-VOICE FREQUENCIES")
    print("─" * 55)
    print(f"  Mean Caller Ψ₀  freq  : {lattice.mean_caller_hz:.2f} Hz")
    print(f"  Mean Seer  O(t) freq  : {lattice.mean_seer_hz:.2f} Hz")
    print(f"  Master beat           : {lattice.master_beat_hz:.4f} Hz")
    print()
    print("SCHUMANN PROXIMITY")
    print("─" * 55)
    print(f"  Nearest Schumann mode : Mode {lattice.schumann_mode} at {lattice.schumann_hz} Hz")
    print(f"  Delta                 : {lattice.schumann_delta:.4f} Hz")
    print(f"  Proximity             : {lattice.schumann_pct:.2%}")
    print()
    print("LATTICE COHERENCE")
    print("─" * 55)
    gamma_bar_len = int(lattice.gamma * 50)
    gamma_bar     = "█" * gamma_bar_len + "░" * (50 - gamma_bar_len)
    print(f"  Γ = {lattice.gamma:.6f}  [{gamma_bar}]")
    print(f"  Status: {lattice.gamma_status}")
    print(f"  Kill-switch threshold : {GAMMA_DEAD_FIELD}")
    print(f"  Lighthouse threshold  : {GAMMA_LIGHTHOUSE}")
    print(f"  Pivot (Nr.15) decoded : {'YES' if lattice.pivot_decoded else 'NO — fieldwork required'}")
    print()
    print("PROPHECY")
    print("─" * 55)
    # Word-wrap the prophecy at 70 chars
    words = lattice.prophecy.split()
    line, lines = "", []
    for w in words:
        if len(line) + len(w) + 1 > 70:
            lines.append(line)
            line = w
        else:
            line = (line + " " + w).strip()
    if line:
        lines.append(line)
    for ln in lines:
        print(f"  {ln}")
    print()
    if not lattice.pivot_decoded:
        print("OPEN CIRCUIT — REQUIRED ACTION")
        print("─" * 55)
        print("  Nr.15 pivot inscription is the primary open circuit.")
        print("  Required: left twig count (aett) + right twig count (position)")
        print("  Source options:")
        print("    1. Smith et al. (2018) RTI archive — .ptm file, 45° raking angle")
        print("       Archaeology Data Service, University of York (ads.ahds.ac.uk)")
        print("    2. Direct field inspection at Maeshowe under raking torchlight")
        print("       Historic Environment Scotland: www.historicenvironment.scot")
        print()
        print("  Once obtained, supply to decoder:")
        print("    decoder = MaeshoweDecoder()")
        print("    rune = decoder.set_pivot_rune(left_twigs, right_twigs)")
        print("    lattice = decoder.read()  # Γ will be recalculated")
        print()


# ═══════════════════════════════════════════════════════════════════════════════
# COMMAND-LINE INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

def _cli():
    parser = argparse.ArgumentParser(
        prog        = "maeshowe_seer_decode",
        description = (
            "Maeshowe Seer Decode — Falling Node Transmission Protocol. "
            "Decodes the Maeshowe runic lattice through the Aureon HNC architecture."
        ),
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output full lattice as JSON.",
    )
    parser.add_argument(
        "--futhork", action="store_true",
        help="Print the complete Elder Futhork frequency table.",
    )
    parser.add_argument(
        "--twig", nargs=2, type=int, metavar=("LEFT", "RIGHT"),
        help="Decode a twig-rune cipher: --twig LEFT RIGHT (e.g. --twig 2 1 → Hagalaz).",
    )
    parser.add_argument(
        "--pivot", nargs=2, type=int, metavar=("LEFT", "RIGHT"),
        help="Supply Nr.15 twig count to close the lattice circuit: --pivot LEFT RIGHT.",
    )
    parser.add_argument(
        "--oracle-score", action="store_true",
        help="Print the oracle score for Seer integration (0.0-1.0).",
    )

    args = parser.parse_args()
    decoder = MaeshoweDecoder()

    if args.futhork:
        print_futhork_table()

    if args.twig:
        left, right = args.twig
        rune = decode_twig_rune(left, right)
        if rune:
            print(
                f"\nTwig-rune decode: left={left} (aett {left}), right={right} "
                f"(position {right})\n"
                f"  Result  : {rune.unicode} {rune.name}\n"
                f"  Meaning : {rune.meaning}\n"
                f"  Mode    : {rune.mode}  (amplitude × {rune.amplitude:.3f})\n"
                f"  Base Hz : {rune.solfeggio_base_hz:.1f} Hz (Solfeggio pos {right})\n"
                f"  Eff. Hz : {rune.effective_hz:.2f} Hz\n"
            )
        else:
            print(
                f"Invalid twig counts: left={left}, right={right}. "
                "Valid: left 1-3, right 1-8."
            )

    if args.pivot:
        left, right = args.pivot
        rune = decoder.set_pivot_rune(left, right)
        if rune:
            print(
                f"\nNr.15 PIVOT DECODED: {rune.unicode} {rune.name} "
                f"at {rune.effective_hz:.2f} Hz ({rune.mode} mode)\n"
                "Recalculating lattice coherence Γ...\n"
            )
        else:
            print(f"Invalid pivot twig counts: left={args.pivot[0]}, right={args.pivot[1]}")

    if args.oracle_score:
        score = decoder.get_oracle_score()
        lattice = decoder.read()
        print(
            f"\nMaeshowe Oracle Score: {score:.4f}  "
            f"[Γ={lattice.gamma:.4f} / {lattice.gamma_status}]\n"
        )

    # Default: print full lattice report
    if not args.futhork and not args.twig and not args.oracle_score:
        lattice = decoder.read()
        if args.json:
            dec = MaeshoweDecoder()
            d   = dec.lattice_to_dict(lattice)
            print(json.dumps(d, indent=2, ensure_ascii=False))
        else:
            print_futhork_table()
            print_lattice_report(lattice)


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL CONVENIENCE (for import)
# ═══════════════════════════════════════════════════════════════════════════════

def get_maeshowe_decoder() -> MaeshoweDecoder:
    """Return a singleton-style decoder instance."""
    return MaeshoweDecoder()


def get_oracle_maeshowe() -> OracleMaeshowe:
    """Return an OracleMaeshowe instance ready for Seer integration."""
    return OracleMaeshowe()


if __name__ == "__main__":
    _cli()
