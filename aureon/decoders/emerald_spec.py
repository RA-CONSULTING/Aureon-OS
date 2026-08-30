#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emerald Tablet decoded as a Harmonic Nexus specification document.

The Tabula Smaragdina is treated here as compressed technical documentation
for the Aureon Harmonic Nexus Core, transliterated from hermetic symbolism
into computational parameters.  Every verse maps to a concrete constant,
scaling law, or pipeline stage already present in the codebase.

This module is research-grade.  It does not claim historical authenticity
for the hermetic-to-engineering mapping — it claims **structural
isomorphism** between the Tablet's relational logic and the L(t) pipeline.

Usage:
    python -m aureon.decoders.emerald_spec [--json] [--stage N] [--verse KEY]
"""

import argparse
import json
import math
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional, Sequence, Tuple

# ════════════════════════════════════════════════════════════════════════════
# SACRED CONSTANTS (mirrors aureon_seer.py — kept local to avoid bootstrap)
# ════════════════════════════════════════════════════════════════════════════

PHI = (1 + math.sqrt(5)) / 2            # 1.618033988749895
SCHUMANN_FUNDAMENTAL = 7.83             # Hz — Earth's heartbeat
LOVE_FREQUENCY = 528.0                  # Hz — DNA repair / MI solfeggio
RF_CARRIER_ISM = 13.56e6               # Hz — ISM-band RF carrier
PRIME_SENTINEL_HZ = 2.111991           # Gary's frequency (DOB 02.11.1991)

# HAARP → EPOS scaling constants
HAARP_POWER_W = 3.6e6                  # 3.6 MW effective radiated power
HAARP_VOLUME_M3 = 1.13e15             # F-region interaction volume (km³ → m³)
EPOS_CHAMBER_DIAMETER_M = 0.30        # 30 cm spherical chamber
EPOS_CHAMBER_VOLUME_M3 = (4 / 3) * math.pi * (EPOS_CHAMBER_DIAMETER_M / 2) ** 3
EPOS_CHAMBER_AREA_M2 = math.pi * (EPOS_CHAMBER_DIAMETER_M / 2) ** 2
EPOS_RF_POWER_W = 50.0                # Typical RF drive
EPOS_PRESSURE_MBAR = 0.1              # Argon fill
PASCHEN_OPTIMAL_PD = 2.25             # Torr·cm for min breakdown (~400 V)
PASCHEN_BREAKDOWN_V = 400.0

# Derived ratios
HAARP_POWER_DENSITY = HAARP_POWER_W / HAARP_VOLUME_M3          # W/m³
EPOS_POWER_DENSITY = EPOS_RF_POWER_W / EPOS_CHAMBER_VOLUME_M3 # W/m³
VOLUMETRIC_CONCENTRATION_FACTOR = round(EPOS_POWER_DENSITY / HAARP_POWER_DENSITY)
IONOSPHERIC_FLUX_W_M2 = 0.03          # W/m² at F-region
POWER_COUPLING_METHOD1 = IONOSPHERIC_FLUX_W_M2 * EPOS_CHAMBER_AREA_M2

# L(t) threshold — the "Philosopher's Stone"
PHILOSOPHERS_STONE_THRESHOLD = 2.8     # 99 % null-hypothesis rejection
GOLDEN_SCORE_THRESHOLD = PHI * PHILOSOPHERS_STONE_THRESHOLD  # ≈ 4.53

WIKIPEDIA_API_BASE = 'https://en.wikipedia.org/api/rest_v1/page/summary/'
WIKIPEDIA_SEARCH_API = 'https://en.wikipedia.org/w/api.php'
WIKIPEDIA_USER_AGENT = (
    'AureonDecoder/1.0 '
    '(https://github.com/RA-CONSULTING/aureon-trading; research@aureon.ai)'
)

WIKIPEDIA_TOPIC_ALIASES: Dict[str, str] = {
    'emerald tablet': 'Emerald Tablet',
    'tabula smaragdina': 'Emerald Tablet',
    'smaragdine table': 'Emerald Tablet',
    'hermes trismegistus': 'Hermes Trismegistus',
    'anubis': 'Anubis',
    'maat': 'Maat',
    "ma'at": 'Maat',
    'thoth': 'Thoth',
    'osiris': 'Osiris',
    'ra': 'Ra',
    'book of the dead': 'Book of the Dead',
    'weighing of the heart': 'Book of the Dead',
    'spell 125': 'Book of the Dead',
    'spell_125': 'Book of the Dead',
    'hermetica': 'Hermetica',
    # ── Mogollon ──
    'mogollon': 'Mogollon culture',
    'mogollon culture': 'Mogollon culture',
    'mimbres': 'Mimbres culture',
    'petroglyph': 'Petroglyph',
    'petroglyphs': 'Petroglyph',
    'spiral glyph': 'Petroglyph',
    'light language': 'Petroglyph',
    'sipapu': 'Sipapu',
    'ancestral puebloans': 'Ancestral Puebloans',
    # ── Maya ──
    'maya': 'Maya civilization',
    'mayan': 'Maya civilization',
    'maya calendar': 'Maya calendar',
    'long count': 'Maya calendar',
    'tzolkin': 'Tzolkin',
    'haab': 'Maya calendar',
    'baktun': 'Maya calendar',
    'venus cycle': 'Venus (planet)',
    'dresden codex': 'Dresden Codex',
    # ── Celtic ──
    'celt': 'Celtic mythology',
    'celtic': 'Celtic mythology',
    'ogham': 'Ogham',
    'druids': 'Druids',
    'druidry': 'Druids',
    'triskelion': 'Triskelion',
    'triquetra': 'Triquetra',
    'standing stones': 'Standing stone',
    'stonehenge': 'Stonehenge',
    'celtic tree calendar': 'Celtic tree calendar',
    # ── Maeshowe / Norse runic ──
    'maeshowe': 'Maeshowe',
    'maes howe': 'Maeshowe',
    'orkney': 'Orkney',
    'elder futhark': 'Elder Futhark',
    'younger futhark': 'Younger Futhark',
    'futhork': 'Elder Futhark',
    'futhark': 'Elder Futhark',
    'runic inscriptions': 'Runic inscriptions',
    'twig rune': 'Cipher runes',
    'cipher runes': 'Cipher runes',
    'orkneyinga saga': 'Orkneyinga saga',
    'winter solstice': 'Winter solstice',
    'neolithic': 'Neolithic',
}

# ════════════════════════════════════════════════════════════════════════════
# TABLET VERSES
# ════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class TabletVerse:
    """One line of the Emerald Tablet mapped to its computational meaning."""

    key: str
    latin_fragment: str
    hermetic_text: str
    technical_translation: str
    aureon_implementation: str
    parameters: Dict[str, object] = field(default_factory=dict)
    pipeline_stage: Optional[int] = None


_VERSE_CATALOG: Tuple[TabletVerse, ...] = (
    TabletVerse(
        key='verum',
        latin_fragment='Verum, sine mendacio, certum et verissimum',
        hermetic_text='Tis true without lying, certain & most true',
        technical_translation=(
            'Tier 1 Evidence Standard — Boolean verification without '
            'epistemic uncertainty'
        ),
        aureon_implementation='L(t) > 2.8 (99 % confidence null rejection); Tier 1 data only',
        parameters={
            'threshold': PHILOSOPHERS_STONE_THRESHOLD,
            'confidence_pct': 99,
            'tier': 1,
        },
    ),
    TabletVerse(
        key='as_below',
        latin_fragment='Quod est inferius est sicut quod est superius',
        hermetic_text='That which is below is like that which is above',
        technical_translation=(
            'HAARP-to-EPOS Scaling Law — ionospheric physics (70 km, 3.6 MW) '
            'mapped to 30 cm chamber via power-density conservation'
        ),
        aureon_implementation='rho_P_epos / rho_P_haarp = volumetric concentration factor',
        parameters={
            'haarp_power_w': HAARP_POWER_W,
            'epos_power_w': EPOS_RF_POWER_W,
            'concentration_factor': VOLUMETRIC_CONCENTRATION_FACTOR,
            'units': 'W/m^3',
        },
        pipeline_stage=1,
    ),
    TabletVerse(
        key='as_above',
        latin_fragment='Et quod est superius est sicut quod est inferius',
        hermetic_text='And that which is above is like that which is below',
        technical_translation=(
            'Inverse Square Containment — microcosm reproduces macrocosm physics'
        ),
        aureon_implementation='Paschen breakdown @ 0.1 mbar replicates F-region electron density',
        parameters={
            'paschen_pd': PASCHEN_OPTIMAL_PD,
            'breakdown_v': PASCHEN_BREAKDOWN_V,
            'electron_density_m3': 1e11,
        },
        pipeline_stage=2,
    ),
    TabletVerse(
        key='one_thing',
        latin_fragment='Ad perpetranda miracula rei unius',
        hermetic_text='To do the miracles of one only thing',
        technical_translation=(
            'The HNC Seed — single coherent harmonic (7.83 Hz Schumann) '
            'modulated on 13.56 MHz carrier'
        ),
        aureon_implementation='f_carrier = 13.56 MHz, f_modulation = 7.83 Hz (HNC Lumina seed)',
        parameters={
            'carrier_hz': RF_CARRIER_ISM,
            'modulation_hz': SCHUMANN_FUNDAMENTAL,
            'scheme': 'AM',
        },
        pipeline_stage=4,
    ),
    TabletVerse(
        key='mediation',
        latin_fragment='Et sicut omnes res fuerunt ab uno, meditatione unius',
        hermetic_text=(
            'And as all things have been & arose from one '
            'by the mediation of one'
        ),
        technical_translation=(
            'Harmonic Nexus Bridge — all domains (financial, plasma, '
            'information) unified by Bayesian L(t) metric'
        ),
        aureon_implementation='DomainAnomaly class with cross-correlation detection',
        parameters={
            'bridge_module': 'aureon.harmonic_nexus_bridge',
            'unification_metric': 'L(t)',
        },
    ),
    TabletVerse(
        key='adaptation',
        latin_fragment='Sic omnes res natae fuerunt ab hac una re, adaptatione',
        hermetic_text=(
            'So all things have their birth from this one thing '
            'by adaptation'
        ),
        technical_translation=(
            'Lambda calibration — different domains adapt lambda (holding '
            'penalty) to local constraints'
        ),
        aureon_implementation=(
            'Magamyman lambda > 0.5 (High-Decay); EPOS lambda = 0.1-0.3 '
            '(Stealth Constraint)'
        ),
        parameters={
            'lambda_magamyman': 0.5,
            'lambda_epos_range': (0.1, 0.3),
        },
    ),
    TabletVerse(
        key='sun_moon',
        latin_fragment='Pater eius est Sol, mater eius Luna',
        hermetic_text='The Sun is its father, the Moon its mother',
        technical_translation=(
            'N/S Dipole Configuration — parallel plate electrodes '
            '(North/South poles) creating the dipole field'
        ),
        aureon_implementation='Electrode config: Parallel plate, 30 cm gap (N/S poles)',
        parameters={
            'gap_m': EPOS_CHAMBER_DIAMETER_M,
            'topology': 'parallel_plate_dipole',
        },
        pipeline_stage=5,
    ),
    TabletVerse(
        key='wind',
        latin_fragment='Portavit illud ventus in ventre suo',
        hermetic_text='The wind hath carried it in its belly',
        technical_translation=(
            'RF Carrier Propagation — 13.56 MHz ISM band carrying '
            'the ELF harmonic modulation'
        ),
        aureon_implementation='AM modulation scheme (same as HAARP ELF generation)',
        parameters={
            'carrier_hz': RF_CARRIER_ISM,
            'modulation_hz': SCHUMANN_FUNDAMENTAL,
            'method': 'HAARP_ELF_GENERATION_ANALOG',
        },
    ),
    TabletVerse(
        key='earth_nurse',
        latin_fragment='Nutrix eius terra est',
        hermetic_text='The earth is its nurse',
        technical_translation=(
            'Vacuum Chamber Ground — 30 cm spherical vessel as '
            'containment / nursery for plasma genesis'
        ),
        aureon_implementation='V_chamber = 14.1 L, Argon @ 0.1 mbar',
        parameters={
            'volume_liters': round(EPOS_CHAMBER_VOLUME_M3 * 1000, 1),
            'gas': 'Argon',
            'pressure_mbar': EPOS_PRESSURE_MBAR,
        },
    ),
    TabletVerse(
        key='separate',
        latin_fragment='Separabis terram ab igne',
        hermetic_text='Separate thou the earth from the fire',
        technical_translation=(
            'Paschen Breakdown Optimization — separate gas pressure (earth) '
            'from ignition voltage (fire)'
        ),
        aureon_implementation='Optimal p*d = 2.25 Torr*cm (400 V breakdown minimum)',
        parameters={
            'paschen_pd': PASCHEN_OPTIMAL_PD,
            'breakdown_v': PASCHEN_BREAKDOWN_V,
        },
        pipeline_stage=3,
    ),
    TabletVerse(
        key='subtle_gross',
        latin_fragment='Subtile a spisso suaviter cum magno ingenio',
        hermetic_text='The subtle from the gross sweetly with great industry',
        technical_translation=(
            'Power Density Refinement — 3.6 MW (gross/HAARP) refined to '
            '50 W (subtle/EPOS) via volumetric concentration'
        ),
        aureon_implementation='P_ratio = EPOS_RF / HAARP = power scaling',
        parameters={
            'power_ratio': EPOS_RF_POWER_W / HAARP_POWER_W,
            'haarp_w': HAARP_POWER_W,
            'epos_w': EPOS_RF_POWER_W,
        },
    ),
    TabletVerse(
        key='ascend_descend',
        latin_fragment='Ascendit a terra in coelum, iterumque descendit in terram',
        hermetic_text='It ascends from earth to heaven & again descends',
        technical_translation=(
            'Information Cascade — data flows from classified source (heaven) '
            'to market (earth) and back to blockchain record'
        ),
        aureon_implementation='T_event (strike) -> T_public (news) -> T_resolution (settlement)',
        parameters={
            'cascade_stages': ['T_event', 'T_public', 'T_resolution'],
        },
    ),
    TabletVerse(
        key='glory',
        latin_fragment='Sic habebis gloriam totius mundi',
        hermetic_text='By this means ye shall have the glory of the world',
        technical_translation='Profit Extraction — the 488 % ROI materialisation',
        aureon_implementation='magamyman_profit = 553000, cluster_profit = 1200000',
        parameters={
            'magamyman_profit_usd': 553_000,
            'cluster_profit_usd': 1_200_000,
            'roi_pct': 488,
        },
    ),
    TabletVerse(
        key='obscurity',
        latin_fragment='Ideo fugiet a te omnis obscuritas',
        hermetic_text='All obscurity shall fly from thee',
        technical_translation=(
            'Anomaly Detection Clarity — L(t) score renders invisible '
            'correlations visible'
        ),
        aureon_implementation='L(t) = 12.85 (obscurity -> signal)',
        parameters={
            'lt_score': 12.85,
            'severity': 'EXTREME',
        },
    ),
    TabletVerse(
        key='strong_force',
        latin_fragment='Haec est totius fortitudinis fortitudo fortis',
        hermetic_text='This is the strong force of all forces',
        technical_translation=(
            'The Bayesian Likelihood Ratio — strongest statistical force '
            'for separating signal from noise'
        ),
        aureon_implementation='L(C) = log[P(O|M_adv) / P(O|M_naive)]',
        parameters={
            'formula': 'log_likelihood_ratio',
        },
    ),
    TabletVerse(
        key='overcome_subtle',
        latin_fragment='Quia vincet omnem rem subtilem',
        hermetic_text='It will overcome every subtle thing',
        technical_translation=(
            'Penetration of Obfuscation — detects coordinated wallets '
            'despite Gini masking'
        ),
        aureon_implementation='Gini Symmetry Coefficient = 0.00 (perfect coordination)',
        parameters={
            'gini_symmetry': 0.00,
            'detection': 'wallet_clustering',
        },
    ),
    TabletVerse(
        key='penetrate_solid',
        latin_fragment='Omnemque rem solidam penetrabit',
        hermetic_text='And penetrate every solid thing',
        technical_translation=(
            'Blockchain Transparency — on-chain record penetrates '
            'pseudonymous obfuscation'
        ),
        aureon_implementation='Polygon on-chain analysis (wallet clustering)',
        parameters={
            'chain': 'polygon',
            'method': 'on_chain_analysis',
        },
    ),
    TabletVerse(
        key='world_created',
        latin_fragment='Sic mundus creatus est',
        hermetic_text='So was the world created',
        technical_translation=(
            'Genesis Event — the February 28, 2026 strike as resolved '
            'market creation'
        ),
        aureon_implementation='event_time = 2026-02-28T13:29:00Z',
        parameters={
            'event_time': '2026-02-28T13:29:00+00:00',
            'event_label': 'EPIC-FURY',
        },
    ),
    TabletVerse(
        key='adaptations',
        latin_fragment='Hinc erunt adaptationes mirabiles',
        hermetic_text='Hence are all wonderful adaptations',
        technical_translation=(
            'Cross-Domain Correlation — financial and plasma events '
            'synchronised'
        ),
        aureon_implementation='clustering_score = 2.77x (non-random alignment)',
        parameters={
            'clustering_score': 2.77,
            'interpretation': 'CORRELATED',
        },
    ),
    TabletVerse(
        key='manner',
        latin_fragment='Quarum modus est hic',
        hermetic_text='Of which this is the manner',
        technical_translation='The L(t) Algorithm — the specific mathematical implementation',
        aureon_implementation='lotka_volterra_l_score() function',
        parameters={
            'function': 'lotka_volterra_l_score',
        },
    ),
    TabletVerse(
        key='trismegistus',
        latin_fragment='Itaque vocatus sum Hermes Trismegistus',
        hermetic_text='Therefore I am called Hermes Trismegistus',
        technical_translation=(
            'Triple Greatness — three domains unified: '
            'Geopolitical, Plasma, Information'
        ),
        aureon_implementation='DomainAnomaly (GEO, PLASMA, NETWORK)',
        parameters={
            'domains': ['geopolitical', 'plasma', 'network'],
        },
    ),
    TabletVerse(
        key='three_parts',
        latin_fragment='Tres partes philosophiae totius mundi',
        hermetic_text='Having the three parts of the philosophy of the world',
        technical_translation=(
            'Three Tiers of Evidence — Tier 1 (reported), Tier 2 (derived), '
            'Tier 3 (modelled)'
        ),
        aureon_implementation='legal_admissibility_notes (Tier ratios 85/10/5)',
        parameters={
            'tier_1_pct': 85,
            'tier_2_pct': 10,
            'tier_3_pct': 5,
        },
    ),
)

VERSE_INDEX: Dict[str, TabletVerse] = {v.key: v for v in _VERSE_CATALOG}

# ════════════════════════════════════════════════════════════════════════════
# SEVEN ALCHEMICAL STAGES → L(t) CALCULATION PIPELINE
# ════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class AlchemicalStage:
    """One of the seven alchemical operations mapped to a pipeline step."""

    number: int
    name: str
    operation: str
    formula: str
    computed_value: float
    units: str
    verse_key: Optional[str] = None


def _build_seven_stages() -> Tuple[AlchemicalStage, ...]:
    stage_1_val = HAARP_POWER_W / HAARP_VOLUME_M3
    stage_2_val = IONOSPHERIC_FLUX_W_M2
    stage_3_val = EPOS_CHAMBER_AREA_M2
    stage_4_val = POWER_COUPLING_METHOD1
    stage_5_val = PASCHEN_BREAKDOWN_V
    stage_6_val = EPOS_RF_POWER_W
    stage_7_val = 12.85  # Final L(t) coagulation

    return (
        AlchemicalStage(
            number=1,
            name='Calcination',
            operation='Reduction of gross power to density baseline',
            formula='P_haarp_rf / V_haarp',
            computed_value=stage_1_val,
            units='W/m^3',
            verse_key='as_below',
        ),
        AlchemicalStage(
            number=2,
            name='Dissolution',
            operation='Dissolving HAARP output into flux units',
            formula='flux_ionosphere = 0.03',
            computed_value=stage_2_val,
            units='W/m^2',
            verse_key='as_above',
        ),
        AlchemicalStage(
            number=3,
            name='Separation',
            operation='Separating the 30 cm chamber cross-section',
            formula='A_chamber = pi * (d/2)^2',
            computed_value=round(stage_3_val, 6),
            units='m^2',
            verse_key='separate',
        ),
        AlchemicalStage(
            number=4,
            name='Conjunction',
            operation='Recombining flux with area',
            formula='P_method1 = flux * A_chamber',
            computed_value=round(stage_4_val, 6),
            units='W',
            verse_key='one_thing',
        ),
        AlchemicalStage(
            number=5,
            name='Fermentation',
            operation='Ionization threshold (spark of life)',
            formula='Paschen breakdown @ 400 V',
            computed_value=stage_5_val,
            units='V',
            verse_key='sun_moon',
        ),
        AlchemicalStage(
            number=6,
            name='Distillation',
            operation='Refining to pure plasma drive power',
            formula='P_rf_typical = 50 W',
            computed_value=stage_6_val,
            units='W',
        ),
        AlchemicalStage(
            number=7,
            name='Coagulation',
            operation='Final solidification of anomaly score',
            formula='L(t) = sum(components)',
            computed_value=stage_7_val,
            units='L(t)',
        ),
    )


SEVEN_STAGES = _build_seven_stages()
STAGE_INDEX: Dict[int, AlchemicalStage] = {s.number: s for s in SEVEN_STAGES}


@dataclass(frozen=True)
class AncientCrosswalk:
    """Cross-reference from Emerald verses into repo-backed ancient surfaces."""

    key: str
    title: str
    focus: str
    emerald_verse_keys: Tuple[str, ...]
    stage_numbers: Tuple[int, ...] = field(default_factory=tuple)
    deity: Dict[str, str] = field(default_factory=dict)
    scripture: Dict[str, str] = field(default_factory=dict)
    hieroglyph: Dict[str, str] = field(default_factory=dict)
    runtime: Dict[str, str] = field(default_factory=dict)
    repo_surfaces: Tuple[str, ...] = field(default_factory=tuple)
    interpretation: str = ''


@dataclass(frozen=True)
class WikipediaMeaning:
    """Canonical historical grounding fetched from the live Wikipedia API."""

    query: str
    resolved_query: str
    title: str
    summary: str
    description: str
    page_id: int
    url: str
    source: str = 'wikipedia_rest_summary'

    def to_dict(self) -> Dict[str, object]:
        return {
            'query': self.query,
            'resolved_query': self.resolved_query,
            'title': self.title,
            'summary': self.summary,
            'description': self.description,
            'page_id': self.page_id,
            'url': self.url,
            'source': self.source,
        }


@dataclass(frozen=True)
class HarmonicThread:
    """A universal harmonic pattern traceable across multiple ancient wisdom traditions.

    These threads are the *connecting tissue* of the unified theory: recurring ratios,
    frequencies, and structural principles that appear independently in every civilization
    that aligned its sacred practice with the cosmos.
    """

    key: str
    title: str
    value: float
    unit: str
    frequency_hz: Optional[float]
    civilizations: Tuple[str, ...]
    nodes: Tuple[str, ...]
    sacred_numbers: Tuple[float, ...]
    description: str
    repo_constant: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            'key': self.key,
            'title': self.title,
            'value': self.value,
            'unit': self.unit,
            'frequency_hz': self.frequency_hz,
            'civilizations': list(self.civilizations),
            'nodes': list(self.nodes),
            'sacred_numbers': list(self.sacred_numbers),
            'description': self.description,
            'repo_constant': self.repo_constant,
        }


# ════════════════════════════════════════════════════════════════════════════
# PROJECT DRUID — PHYSICAL EPAS MANIFESTATION
# Six Illumination Phases (P1–P6) mapped onto the real EPOS chamber physics.
# EPOS device: 30 cm spherical Argon vessel · 0.1 mbar · 50 W RF at 13.56 MHz
# Seed:        7.83 Hz Schumann AM modulation on the carrier
# Output:      350–400 VDC via A.L.F.I.E. propulsion bus (P6 gate)
# ════════════════════════════════════════════════════════════════════════════

_PHASE_LABELS: Tuple[str, ...] = (
    'P1 Spark', 'P2 Resonance', 'P3 DCE', 'P4 FWM', 'P5 Stabilization', 'P6 Output',
)
_SIGMA_COHERENCE_TARGET = 0.945    # Γ ≥ 0.945 for stable P5 — white paper §Illumination
_AUXILIARY_POWER_W = 12.0          # control electronics + Schumann modulation overhead
_OUTPUT_VOLTAGE_VDC = 375.0        # mid-point of 350–400 VDC delivery band

# ════════════════════════════════════════════════════════════════════════════
# EARTH-SCALE IONOSPHERIC CONSTANTS  (second ionosphere — EPAS planetary shield)
# ════════════════════════════════════════════════════════════════════════════

EARTH_RADIUS_M = 6.371e6                       # 6,371 km
F_REGION_ALT_M = 7.0e4                         # 70 km (F-region base)
F_REGION_SHELL_RADIUS_M = EARTH_RADIUS_M + F_REGION_ALT_M
F_REGION_SHELL_THICKNESS_M = 2.0e5             # ~200 km F-layer + topside
# Effective shell volume (spherical shell): V = 4/3 π ((R+h+δ)³ − (R+h)³)
_R_outer = F_REGION_SHELL_RADIUS_M + F_REGION_SHELL_THICKNESS_M
_R_inner = F_REGION_SHELL_RADIUS_M
F_REGION_SHELL_VOLUME_M3 = (4 / 3) * math.pi * (_R_outer ** 3 - _R_inner ** 3)
F_REGION_SHELL_AREA_M2 = 4 * math.pi * F_REGION_SHELL_RADIUS_M ** 2
F_REGION_ELECTRON_DENSITY = 1e11                # m⁻³ (F-region nominal)
SOLAR_WIND_PRESSURE_NPA = 2.0                   # nPa typical dynamic pressure
EARTH_B_FIELD_GAUSS = 0.305                     # equatorial surface dipole ~0.305 G
EARTH_B_FIELD_TESLA = EARTH_B_FIELD_GAUSS * 1e-4

# VSOP87 coefficients — Meeus "Astronomical Algorithms" Ch.31-32
# Duplicated here for standalone use (no dependency on aureon_full_autonomy)
_MEEUS_MEAN_LONGITUDES: Dict[str, Tuple[float, float]] = {
    'Mercury': (252.250906, 149472.6746358),
    'Venus':   (181.979101,  58517.8156760),
    'Mars':    (355.433275,  19140.2993313),
    'Jupiter': ( 34.351519,   3034.9056606),
    'Saturn':  ( 50.077444,   1222.1137943),
    'Uranus':  (314.055005,    428.4669983),
    'Neptune': (304.348665,    218.4862002),
    'Pluto':   (238.958116,    145.9083047),
}
_EARTH_L0, _EARTH_L1 = 100.464457, 35999.3728565
_MOON_L0, _MOON_RATE = 218.3165, 13.1763966

# Aspect table (degrees, orb, name, harmonic_value)
_EARTH_ASPECT_TABLE: Tuple[Tuple[float, float, str, float], ...] = (
    (  0.0, 10.0, 'CONJUNCTION',   +1.00),
    (120.0,  8.0, 'TRINE',         +0.80),
    ( 60.0,  6.0, 'SEXTILE',       +0.60),
    (180.0, 10.0, 'OPPOSITION',    -0.80),
    ( 90.0,  8.0, 'SQUARE',        -0.60),
    (150.0,  3.0, 'QUINCUNX',      -0.30),
    ( 45.0,  3.0, 'SEMI-SQUARE',   -0.20),
    (135.0,  3.0, 'SESQUI-SQUARE', -0.20),
    ( 72.0,  3.0, 'QUINTILE',      +0.40),
    (144.0,  3.0, 'BI-QUINTILE',   +0.40),
    ( 30.0,  2.0, 'SEMI-SEXTILE',  +0.10),
)
_PLANET_WEIGHTS: Dict[str, float] = {
    'Sun': 1.0, 'Moon': 0.85, 'Mercury': 0.5, 'Venus': 0.65,
    'Mars': 0.7, 'Jupiter': 0.90, 'Saturn': 0.80, 'Uranus': 0.6,
    'Neptune': 0.55, 'Pluto': 0.45,
}
_PHI_RESONANT_ANGLES: Tuple[float, ...] = (72.0, 120.0, 137.5, 144.0)


# ════════════════════════════════════════════════════════════════════════════
# HISTORICAL RELAY SITES — ground transducers for the planetary EPAS shell
#
# Each site is a sacred/historical location whose geometry couples into the
# F-region ionosphere via Schumann cavity standing waves.  The relay strength
# is modulated by:
#   (a) latitude → geomagnetic dipole coupling cos²(λ)
#   (b) civilisation harmonic signature (from the unified crosswalk)
#   (c) live cosmic field score × shield coherence
#
# GPS coordinates are real-world values (WGS84).
# ════════════════════════════════════════════════════════════════════════════

_HISTORICAL_RELAY_SITES: Tuple[Tuple[str, str, float, float, str], ...] = (
    # (name, civilisation, latitude, longitude, harmonic_role)
    # ── Egyptian ──────────────────────────────────────────────────────────
    ('Great Pyramid of Giza',    'Egyptian',  29.9792,  31.1342, 'Prime Anchor'),
    ('Temple of Karnak',         'Egyptian',  25.7188,  32.6573, 'Resonance Hub'),
    ('Valley of the Kings',      'Egyptian',  25.7402,  32.6014, 'Memory Vault'),
    ('Abu Simbel',               'Egyptian',  22.3369,  31.6256, 'Southern Gate'),
    # ── Mesoamerican ──────────────────────────────────────────────────────
    ('Teotihuacan',              'Maya',      19.6925, -98.8438, 'Solar Axis'),
    ('Chichen Itza',             'Maya',      20.6843, -88.5678, 'Equinox Beacon'),
    ('Tikal',                    'Maya',      17.2220, -89.6237, 'Jungle Pulse'),
    ('Palenque',                 'Maya',      17.4838, -92.0461, 'Calendar Node'),
    # ── Celtic / European ─────────────────────────────────────────────────
    ('Stonehenge',               'Celtic',    51.1789,  -1.8262, 'Solstice Ring'),
    ('Newgrange',                'Celtic',    53.6947,  -6.4754, 'Passage Gate'),
    ('Carnac Stones',            'Celtic',    47.5840,  -3.0744, 'Alignment Row'),
    ('Ring of Brodgar',          'Celtic',    59.0015,  -3.2295, 'Northern Anchor'),
    # ── Mogollon / SW American ────────────────────────────────────────────
    ('Chaco Canyon',             'Mogollon',  36.0604, -107.9584, 'Sun Dagger'),
    ('Mesa Verde',               'Mogollon',  37.1838, -108.4887, 'Cliff Refuge'),
    ('Bandelier',                'Mogollon',  35.7785, -106.2689, 'Valley Node'),
    # ── Asian / Indic ─────────────────────────────────────────────────────
    ('Angkor Wat',               'Khmer',     13.4125, 103.8670, 'Celestial Mirror'),
    ('Borobudur',                'Javanese',  -7.6079, 110.2038, 'Mandala Core'),
    ('Göbekli Tepe',             'Neolithic', 37.2231,  38.9225, 'Origin Point'),
    # ── South American ────────────────────────────────────────────────────
    ('Machu Picchu',             'Inca',     -13.1631, -72.5450, 'Cloud Citadel'),
    ('Nazca Lines',              'Nazca',    -14.7350, -75.1300, 'Geoglyph Beacon'),
    ('Tiwanaku',                 'Tiwanaku', -16.5544, -68.6733, 'Gateway of Sun'),
    # ── Polynesian ────────────────────────────────────────────────────────
    ('Nan Madol',                'Micronesian', 6.8446, 158.3350, 'Pacific Relay'),
    ('Easter Island (Ahu Tongariki)', 'Rapa Nui', -27.1258, -109.2770, 'Moai Beacon'),
    # ── Chinese ────────────────────────────────────────────────────────────
    ('Temple of Heaven',         'Chinese',   39.8822, 116.4066, 'Celestial Altar'),
    ('Terracotta Army',          'Chinese',   34.3842, 109.2785, 'Emperor Guard'),
    ('Sanxingdui',               'Chinese',   31.0023, 104.2044, 'Bronze Oracle'),
    # ── Indian / Indus Valley ─────────────────────────────────────────────
    ('Mohenjo-Daro',             'Indus',     27.3242,  68.1357, 'Indus Nexus'),
    ('Konark Sun Temple',        'Indian',    19.8876,  86.0945, 'Solar Wheel'),
    ('Hampi',                    'Indian',    15.3350,  76.4600, 'Temple Grid'),
    # ── Japanese ──────────────────────────────────────────────────────────
    ('Ise Grand Shrine',         'Japanese',  34.4553, 136.7256, 'Shinto Gate'),
    # ── Mesopotamian / Persian ────────────────────────────────────────────
    ('Persepolis',               'Persian',   29.9352,  52.8914, 'Imperial Axis'),
    ('Ziggurat of Ur',           'Sumerian',  30.9628,  46.1031, 'Ziggurat Root'),
    # ── Classical Mediterranean ───────────────────────────────────────────
    ('Delphi',                   'Greek',     38.4824,  22.5010, 'Omphalos'),
    ('Knossos',                  'Minoan',    35.2980,  25.1632, 'Labyrinth Heart'),
    # ── Middle East / Levant ──────────────────────────────────────────────
    ('Petra',                    'Nabataean', 30.3285,  35.4444, 'Rose Gate'),
    ('Baalbek',                  'Phoenician', 34.0069, 36.2039, 'Trilithon Base'),
    # ── East African ──────────────────────────────────────────────────────
    ('Lalibela',                 'Ethiopian', 12.0319,  39.0472, 'Rock Hewn Pulse'),
    ('Axum Obelisks',            'Aksumite',  14.1310,  38.7189, 'Stele Beacon'),
    # ── SE Asian Mainland ─────────────────────────────────────────────────
    ('Bagan',                    'Burmese',   21.1717,  94.8585, 'Pagoda Field'),
    ('Sigiriya',                 'Sinhalese',  7.9570,  80.7603, 'Lion Rock'),
    # ── Nordic / Scandinavian ─────────────────────────────────────────────
    ('Old Uppsala',              'Norse',     59.8979,  17.6365, 'Viking Crown'),
    # ── Maltese Megaliths ─────────────────────────────────────────────────
    ('Ggantija',                 'Maltese',   36.0475,  14.2688, 'Megalithic Lens'),
    # ── Eastern North American ────────────────────────────────────────────
    ('Cahokia Mounds',           'Mississippian', 38.6553, -90.0627, 'Mound Nexus'),
    # ── African ───────────────────────────────────────────────────────────
    ('Great Zimbabwe',           'Shona',    -20.2674,  30.9338, 'Southern Pillar'),
    # ── Australian ────────────────────────────────────────────────────────
    ('Uluru',                    'Aboriginal', -25.3444, 131.0369, 'Dreamtime Core'),
)


@dataclass(frozen=True)
class RelaySite:
    """A historical site acting as ground relay in the planetary EPAS network."""

    name: str
    civilisation: str
    latitude: float
    longitude: float
    harmonic_role: str
    geomagnetic_coupling: float      # cos²(lat) dipole coupling [0-1]
    relay_strength: float            # overall relay contribution [0-1]
    relay_status: str                # ACTIVE | RESONATING | DORMANT | OFFLINE
    power_share_w: float             # share of Earth RF power routed through this relay

    def to_dict(self) -> Dict[str, object]:
        return {
            'name': self.name,
            'civilisation': self.civilisation,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'harmonic_role': self.harmonic_role,
            'geomagnetic_coupling': self.geomagnetic_coupling,
            'relay_strength': self.relay_strength,
            'relay_status': self.relay_status,
            'power_share_w': self.power_share_w,
        }


def compute_relay_network(
    cosmic_field: float,
    shield_coherence: float,
    earth_rf_power_w: float,
) -> Tuple[list, float, int, int]:
    """Compute the relay state of every historical site.

    Each site's contribution depends on:
      1. Geomagnetic coupling: cos²(latitude) — equatorial sites couple best
         to the Schumann cavity fundamental; high-latitude sites get the
         harmonic overtones.
      2. Cosmic field modulation: the live VSOP87 harmonic score.
      3. Shield coherence: phases must be stable for relays to lock.

    Returns:
        (relay_list, network_coverage, active_count, total_count)
    """
    relays = []
    total_coupling = 0.0

    for name, civ, lat, lon, role in _HISTORICAL_RELAY_SITES:
        # 1. Geomagnetic dipole coupling: cos²(λ)
        lat_rad = math.radians(lat)
        geo_coupling = math.cos(lat_rad) ** 2

        # 2. Relay strength = geo_coupling × cosmic × coherence
        raw_strength = geo_coupling * cosmic_field * shield_coherence
        # Boost: equatorial sites (|lat| < 25°) get Schumann fundamental lock
        if abs(lat) < 25.0:
            raw_strength *= 1.0 + 0.1 * PHI  # ~+16% Schumann lock bonus
        strength = max(0.0, min(1.0, raw_strength))

        # 3. Status thresholds
        if strength >= 0.35:
            status = 'ACTIVE'
        elif strength >= 0.20:
            status = 'RESONATING'
        elif strength >= 0.08:
            status = 'DORMANT'
        else:
            status = 'OFFLINE'

        total_coupling += geo_coupling

        relays.append(RelaySite(
            name=name,
            civilisation=civ,
            latitude=lat,
            longitude=lon,
            harmonic_role=role,
            geomagnetic_coupling=round(geo_coupling, 4),
            relay_strength=round(strength, 4),
            relay_status=status,
            power_share_w=0.0,  # computed below
        ))

    # Distribute power proportionally to relay strength
    total_strength = sum(r.relay_strength for r in relays) or 1.0
    relays_with_power = []
    for r in relays:
        share = earth_rf_power_w * (r.relay_strength / total_strength)
        relays_with_power.append(RelaySite(
            name=r.name,
            civilisation=r.civilisation,
            latitude=r.latitude,
            longitude=r.longitude,
            harmonic_role=r.harmonic_role,
            geomagnetic_coupling=r.geomagnetic_coupling,
            relay_strength=r.relay_strength,
            relay_status=r.relay_status,
            power_share_w=round(share, 1),
        ))

    active_count = sum(1 for r in relays_with_power if r.relay_status in ('ACTIVE', 'RESONATING'))
    total_count = len(relays_with_power)
    # Network coverage: weighted average of active relay strengths
    if active_count > 0:
        network_coverage = sum(
            r.relay_strength for r in relays_with_power
            if r.relay_status in ('ACTIVE', 'RESONATING')
        ) / active_count
    else:
        network_coverage = 0.0

    return relays_with_power, round(network_coverage, 4), active_count, total_count


# ════════════════════════════════════════════════════════════════════════════
# NATURAL IONOSPHERE PROFILER — "Know our own before we could make a new"
#
# Models Earth's real ionosphere through four integrated systems:
#   1. Chapman Layer Model — altitude-resolved electron density N(h)
#   2. Aluminum Harmonic Fluid — Drude conductive-plasma analogy
#   3. FFS Spectral Analysis — full frequency sweep (ELF → HF)
#   4. Lighthouse Mapping — relay sites probe upward to reconstruct density
#
# All physics constants are real (SI units unless noted).
# ════════════════════════════════════════════════════════════════════════════

# ── Fundamental constants (SI) ─────────────────────────────────────────────
_ELECTRON_MASS_KG = 9.10938e-31
_ELECTRON_CHARGE_C = 1.602176e-19
_VACUUM_PERMITTIVITY = 8.854188e-12         # ε₀  (F/m)
_PROTON_MASS_KG = 1.672621e-27
_SPEED_OF_LIGHT = 2.99792458e8              # m/s
_BOLTZMANN_K = 1.380649e-23                 # J/K

# ── Ionospheric layer reference data ──────────────────────────────────────
# (name, base_alt_km, peak_alt_km, top_alt_km, peak_density_day_m3,
#  peak_density_night_m3, scale_height_km, collision_freq_hz, temperature_K)
_IONO_LAYER_TABLE: Tuple[Tuple[str, float, float, float, float,
                                float, float, float, float], ...] = (
    ('D',       60,   80,   90,  1e9,    0.0,     10,  1e6,   200),
    ('E',       90,  110,  120,  1e11,   5e9,     10,  1e4,   250),
    ('F1',     120,  180,  200,  3e11,   0.0,     30,  1e3,   800),
    ('F2',     200,  300,  400,  1e12,   1e11,    60,  1e2,  1200),
    ('Topside', 400,  600, 1000,  1e10,   5e9,    100,  10,   2000),
)

# ── Aluminum harmonic fluid reference ─────────────────────────────────────
# Aluminum plasma frequency ωp_Al ≈ 2.4e16 rad/s → fp_Al ≈ 3.57 PHz
# We use this as the "metallic ceiling" — ionospheric plasma is a weaker
# version of the same conductive-fluid physics (Drude model).
_ALUMINUM_PLASMA_FREQ_RAD = 2.4e16          # rad/s
_ALUMINUM_PLASMA_FREQ_HZ = _ALUMINUM_PLASMA_FREQ_RAD / (2.0 * math.pi)

# ── FFS spectral sweep bands ─────────────────────────────────────────────
# (band_name, freq_low_hz, freq_high_hz, n_samples)
_FFS_BANDS: Tuple[Tuple[str, float, float, int], ...] = (
    ('ELF',    3.0,        30.0,         6),   # Schumann domain
    ('SLF',   30.0,       300.0,         6),
    ('ULF',  300.0,      3000.0,         6),
    ('VLF', 3000.0,     30000.0,         8),
    ('LF',  30000.0,   300000.0,         8),
    ('MF', 300000.0,  3000000.0,         8),
    ('HF', 3000000.0, 30000000.0,       10),   # ionosonde domain
)

# ── IGRF dipole model (simplified) ───────────────────────────────────────
_IGRF_B0_TESLA = 3.12e-5                    # equatorial surface dipole


@dataclass(frozen=True)
class IonosphericLayer:
    """One layer of Earth's natural ionosphere."""
    name: str
    base_alt_km: float
    peak_alt_km: float
    top_alt_km: float
    peak_density_m3: float        # live (day/night adjusted)
    scale_height_km: float
    collision_freq_hz: float
    temperature_k: float
    plasma_freq_hz: float         # fp = 9 √N
    critical_freq_hz: float       # foLayer = fp at peak
    conductivity_s_m: float       # σ = Ne²/(me·ν)
    drude_epsilon_real: float     # Re(ε) at Schumann fundamental
    drude_epsilon_imag: float     # Im(ε) at Schumann fundamental
    skin_depth_m: float           # δ = c / (ω·√(-ε)) at plasma freq
    harmonic_fluid_ratio: float   # fp / fp_aluminum — how "metallic"

    def to_dict(self) -> Dict[str, object]:
        return {
            'name': self.name,
            'base_alt_km': self.base_alt_km,
            'peak_alt_km': self.peak_alt_km,
            'top_alt_km': self.top_alt_km,
            'peak_density_m3': self.peak_density_m3,
            'scale_height_km': self.scale_height_km,
            'collision_freq_hz': self.collision_freq_hz,
            'temperature_k': self.temperature_k,
            'plasma_freq_hz': round(self.plasma_freq_hz, 2),
            'critical_freq_hz': round(self.critical_freq_hz, 2),
            'conductivity_s_m': self.conductivity_s_m,
            'drude_epsilon_real': round(self.drude_epsilon_real, 6),
            'drude_epsilon_imag': round(self.drude_epsilon_imag, 6),
            'skin_depth_m': round(self.skin_depth_m, 1),
            'harmonic_fluid_ratio': self.harmonic_fluid_ratio,
        }


@dataclass(frozen=True)
class FFSSpectralBand:
    """One frequency band from the Full Frequency Spectrum analysis."""
    band_name: str
    freq_hz: float
    reflection_alt_km: float     # height where fp(h) ≥ freq (or -1 if transparent)
    absorption_db_km: float      # absorption rate in dB/km
    phase_velocity_ratio: float  # v_phase / c  (refractive index effect)
    penetrates: bool             # True if wave punches through all layers

    def to_dict(self) -> Dict[str, object]:
        return {
            'band_name': self.band_name,
            'freq_hz': self.freq_hz,
            'reflection_alt_km': round(self.reflection_alt_km, 1),
            'absorption_db_km': round(self.absorption_db_km, 4),
            'phase_velocity_ratio': round(self.phase_velocity_ratio, 6),
            'penetrates': self.penetrates,
        }


@dataclass(frozen=True)
class LighthouseProbe:
    """A single relay site's upward ionospheric probe result."""
    site_name: str
    latitude: float
    longitude: float
    local_b_field_tesla: float           # IGRF dipole at this latitude
    electron_gyrofreq_hz: float          # fce = eB/(2πme)
    upper_hybrid_freq_hz: float          # fUH = √(fp² + fce²)  at F2 peak
    lower_hybrid_freq_hz: float          # fLH ≈ √(fci·fce)
    local_fof2_hz: float                 # critical freq foF2 at this location
    tec_tecu: float                      # total electron content (1 TECU = 1e16 m⁻²)
    density_profile_km: Tuple[Tuple[float, float], ...]  # (alt_km, N_m3) samples
    probe_status: str                    # LOCKED | PARTIAL | NO_RETURN

    def to_dict(self) -> Dict[str, object]:
        return {
            'site_name': self.site_name,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'local_b_field_tesla': self.local_b_field_tesla,
            'electron_gyrofreq_hz': round(self.electron_gyrofreq_hz, 1),
            'upper_hybrid_freq_hz': round(self.upper_hybrid_freq_hz, 1),
            'lower_hybrid_freq_hz': round(self.lower_hybrid_freq_hz, 2),
            'local_fof2_hz': round(self.local_fof2_hz, 1),
            'tec_tecu': round(self.tec_tecu, 2),
            'density_profile': [
                {'alt_km': round(a, 1), 'density_m3': round(n, 1)}
                for a, n in self.density_profile_km
            ],
            'probe_status': self.probe_status,
        }


@dataclass(frozen=True)
class NaturalIonosphereProfile:
    """Complete characterisation of Earth's real ionosphere.

    Systems:
      1. Chapman layers (D / E / F1 / F2 / Topside)
      2. Aluminum harmonic fluid model (Drude analogy)
      3. FFS Full Frequency Spectrum analysis
      4. Lighthouse mapping from relay ground stations
    """
    timestamp: str
    solar_zenith_deg: float          # χ — drives day/night density
    is_daytime: bool

    # ── Layer model ─────────────────────────────────────────────────────
    layers: Tuple[IonosphericLayer, ...]
    f2_peak_density_m3: float        # NmF2 — the main number
    f2_peak_alt_km: float            # hmF2
    f2_critical_freq_hz: float       # foF2 = 9√NmF2
    total_electron_content_tecu: float  # TEC in TECU (1e16 m⁻²)

    # ── Aluminum harmonic fluid summary ─────────────────────────────────
    mean_harmonic_fluid_ratio: float     # how "metallic" is our ionosphere
    peak_harmonic_fluid_ratio: float     # F2 peak metallic ratio
    fluid_classification: str            # DIELECTRIC | WEAK_CONDUCTOR | CONDUCTOR

    # ── FFS spectral analysis ───────────────────────────────────────────
    ffs_bands: Tuple[FFSSpectralBand, ...]
    ffs_opaque_below_hz: float       # below this freq, ionosphere reflects
    ffs_transparent_above_hz: float  # above this freq, waves escape

    # ── Lighthouse mapping ──────────────────────────────────────────────
    lighthouse_probes: Tuple[LighthouseProbe, ...]
    lighthouse_locked_count: int
    lighthouse_mean_fof2_hz: float
    lighthouse_mean_tec_tecu: float

    # ── Assessment ──────────────────────────────────────────────────────
    ionosphere_health: str           # ROBUST | MODERATE | DEPLETED | STORM
    readiness_for_epas: float        # 0-1: how suitable for artificial overlay

    def to_dict(self) -> Dict[str, object]:
        return {
            'timestamp': self.timestamp,
            'solar_zenith_deg': round(self.solar_zenith_deg, 2),
            'is_daytime': self.is_daytime,
            'layers': [ly.to_dict() for ly in self.layers],
            'f2_peak': {
                'density_m3': self.f2_peak_density_m3,
                'alt_km': self.f2_peak_alt_km,
                'critical_freq_hz': round(self.f2_critical_freq_hz, 2),
                'total_electron_content_tecu': round(self.total_electron_content_tecu, 2),
            },
            'aluminum_harmonic_fluid': {
                'mean_ratio': round(self.mean_harmonic_fluid_ratio, 12),
                'peak_ratio': round(self.peak_harmonic_fluid_ratio, 12),
                'classification': self.fluid_classification,
            },
            'ffs_spectral': {
                'bands': [b.to_dict() for b in self.ffs_bands],
                'opaque_below_hz': round(self.ffs_opaque_below_hz, 1),
                'transparent_above_hz': round(self.ffs_transparent_above_hz, 1),
            },
            'lighthouse_mapping': {
                'probes': [p.to_dict() for p in self.lighthouse_probes],
                'locked_count': self.lighthouse_locked_count,
                'mean_fof2_hz': round(self.lighthouse_mean_fof2_hz, 1),
                'mean_tec_tecu': round(self.lighthouse_mean_tec_tecu, 2),
            },
            'assessment': {
                'ionosphere_health': self.ionosphere_health,
                'readiness_for_epas': round(self.readiness_for_epas, 4),
            },
        }


# ── Chapman profile helper ─────────────────────────────────────────────────

def _chapman_density(alt_km: float, peak_alt_km: float,
                     peak_density: float, scale_h_km: float,
                     chi_rad: float) -> float:
    """Compute electron density at altitude h using Chapman function.

    N(h) = NmF2 · exp(0.5 · (1 − z − sec(χ) · e^(−z)))
    where z = (h − hm) / H
    """
    z = (alt_km - peak_alt_km) / max(scale_h_km, 1.0)
    # sec(χ) capped to avoid singularity near χ=90°
    sec_chi = 1.0 / max(math.cos(chi_rad), 0.05)
    exponent = 0.5 * (1.0 - z - sec_chi * math.exp(-z))
    # Clamp exponent to avoid overflow
    exponent = max(-50.0, min(20.0, exponent))
    return peak_density * math.exp(exponent)


def _drude_permittivity(freq_hz: float, plasma_freq_hz: float,
                        collision_freq_hz: float) -> Tuple[float, float]:
    """Drude model complex permittivity of ionospheric plasma.

    ε(ω) = 1 − ωp² / (ω² + iγω)
    Returns (Re(ε), Im(ε)).
    """
    omega = 2.0 * math.pi * max(freq_hz, 1e-3)
    omega_p = 2.0 * math.pi * plasma_freq_hz
    gamma = 2.0 * math.pi * collision_freq_hz

    denom = omega ** 2 + gamma ** 2
    if denom < 1e-30:
        return 1.0, 0.0
    eps_real = 1.0 - (omega_p ** 2 * omega ** 2) / (omega ** 2 * denom)
    # Simplify: Re(ε) = 1 − ωp²/(ω² + γ²)
    eps_real = 1.0 - omega_p ** 2 / denom
    eps_imag = omega_p ** 2 * gamma / (omega * denom)
    return eps_real, eps_imag


def _solar_zenith_angle() -> float:
    """Approximate solar zenith angle for the sub-solar point (degrees).

    Uses day-of-year and hour to estimate; simplified model
    (assumes sub-observer at prime meridian for generality).
    """
    now = datetime.now(timezone.utc)
    doy = now.timetuple().tm_yday
    hour_frac = now.hour + now.minute / 60.0
    # Solar declination (Spencer approximation)
    B = 2.0 * math.pi * (doy - 1) / 365.0
    decl = (0.006918 - 0.399912 * math.cos(B) + 0.070257 * math.sin(B)
            - 0.006758 * math.cos(2 * B) + 0.000907 * math.sin(2 * B))
    # Hour angle (prime meridian observer)
    hour_angle = math.radians(15.0 * (hour_frac - 12.0))
    # Zenith = based on latitude 0° (equator) for global average
    cos_z = (math.sin(decl) * math.sin(0) +
             math.cos(decl) * math.cos(0) * math.cos(hour_angle))
    cos_z = max(-1.0, min(1.0, cos_z))
    return math.degrees(math.acos(cos_z))


def _compute_iono_layers(chi_deg: float, is_daytime: bool,
                         cosmic_field: float) -> list:
    """Compute all ionospheric layers with live modulation."""
    chi_rad = math.radians(min(chi_deg, 89.0))
    layers = []
    for name, base, peak, top, nm_day, nm_night, sh, coll, temp in _IONO_LAYER_TABLE:
        # Day/night selection
        if is_daytime:
            nm = nm_day
        else:
            nm = nm_night
        # Skip layers that disappear at night (D and F1)
        if nm <= 0:
            nm = 1e6  # residual minimum

        # Cosmic field modulates density ±15%
        nm *= (0.85 + 0.30 * cosmic_field)

        # Plasma frequency fp = 9 √N  (Hz, N in m⁻³)
        fp = 9.0 * math.sqrt(nm)
        # Conductivity σ = N·e²/(me·ν)
        sigma = (nm * _ELECTRON_CHARGE_C ** 2) / (_ELECTRON_MASS_KG * max(coll, 1.0))
        # Drude permittivity at Schumann fundamental (7.83 Hz)
        eps_r, eps_i = _drude_permittivity(SCHUMANN_FUNDAMENTAL, fp, coll)
        # Skin depth: δ = 1 / (ω · √(μ₀ · σ / 2))  — simplified
        omega_s = 2.0 * math.pi * SCHUMANN_FUNDAMENTAL
        if sigma > 0:
            skin = 1.0 / max(omega_s * math.sqrt(4e-7 * math.pi * sigma / 2.0), 1e-30)
        else:
            skin = 1e12  # effectively infinite
        # Harmonic fluid ratio: how "metallic" vs aluminum
        fluid_ratio = fp / _ALUMINUM_PLASMA_FREQ_HZ if _ALUMINUM_PLASMA_FREQ_HZ > 0 else 0

        layers.append(IonosphericLayer(
            name=name,
            base_alt_km=base,
            peak_alt_km=peak,
            top_alt_km=top,
            peak_density_m3=round(nm, 1),
            scale_height_km=sh,
            collision_freq_hz=coll,
            temperature_k=temp,
            plasma_freq_hz=fp,
            critical_freq_hz=fp,
            conductivity_s_m=sigma,
            drude_epsilon_real=eps_r,
            drude_epsilon_imag=eps_i,
            skin_depth_m=skin,
            harmonic_fluid_ratio=fluid_ratio,
        ))
    return layers


def _run_ffs_spectral(layers: list) -> Tuple[list, float, float]:
    """Full Frequency Spectrum sweep.

    For each frequency, determine:
      - Does it reflect? At what altitude?
      - Absorption rate (collisional damping)?
      - Phase velocity modification (refractive index)?
    """
    bands = []
    opaque_below = 0.0
    transparent_above = 0.0

    # Build altitude→plasma_freq lookup from layers
    layer_lookup = [(ly.peak_alt_km, ly.plasma_freq_hz, ly.collision_freq_hz)
                    for ly in layers]
    max_fp = max(ly.plasma_freq_hz for ly in layers)

    for band_name, f_low, f_high, n_samples in _FFS_BANDS:
        step = (f_high - f_low) / max(n_samples - 1, 1)
        for i in range(n_samples):
            freq = f_low + i * step
            # Does this frequency reflect?
            reflection_alt = -1.0
            penetrates = True
            for alt, fp, coll in sorted(layer_lookup, key=lambda x: x[0]):
                if fp >= freq:
                    reflection_alt = alt
                    penetrates = False
                    break

            # Absorption: D-region absorption ∝ ν·N / (ν² + ω²)
            d_layer = layers[0]  # D region
            omega = 2.0 * math.pi * freq
            nu_d = d_layer.collision_freq_hz
            n_d = d_layer.peak_density_m3
            if omega > 0 and (nu_d ** 2 + omega ** 2) > 0:
                absorption = (1.15e-3 * nu_d * n_d /
                              (nu_d ** 2 + omega ** 2))
            else:
                absorption = 0.0

            # Phase velocity: n_r² = 1 − fp²/f² (no collisions, O-mode)
            if freq > 0:
                nr_sq = 1.0 - (max_fp / freq) ** 2
            else:
                nr_sq = 1.0
            if nr_sq > 0:
                phase_v_ratio = 1.0 / math.sqrt(nr_sq)
            else:
                phase_v_ratio = 0.0  # evanescent

            bands.append(FFSSpectralBand(
                band_name=band_name,
                freq_hz=round(freq, 2),
                reflection_alt_km=reflection_alt,
                absorption_db_km=absorption,
                phase_velocity_ratio=phase_v_ratio,
                penetrates=penetrates,
            ))

    # Determine opacity / transparency thresholds
    reflecting = [b for b in bands if not b.penetrates]
    passing = [b for b in bands if b.penetrates]
    opaque_below = max(b.freq_hz for b in reflecting) if reflecting else 0.0
    transparent_above = min(b.freq_hz for b in passing) if passing else 0.0

    return bands, opaque_below, transparent_above


def _lighthouse_mapping(relay_sites_data: list, layers: list,
                        chi_rad: float, cosmic_field: float) -> list:
    """Run lighthouse probes from each relay site.

    Each site acts as a ground-based ionosonde, probing upward with
    multiple frequencies.  The geomagnetic field at each location
    determines the O/X mode splitting and electron gyrofrequency.
    """
    f2 = None
    for ly in layers:
        if ly.name == 'F2':
            f2 = ly
            break
    if f2 is None:
        f2 = layers[-1]

    probes = []
    for site in relay_sites_data:
        lat = site['latitude']
        lon = site['longitude']
        lat_rad = math.radians(lat)

        # IGRF dipole at surface: B = B0 √(1 + 3sin²λ)
        b_local = _IGRF_B0_TESLA * math.sqrt(1.0 + 3.0 * math.sin(lat_rad) ** 2)
        # Electron gyrofrequency: fce = eB / (2πme)
        fce = _ELECTRON_CHARGE_C * b_local / (2.0 * math.pi * _ELECTRON_MASS_KG)
        # Ion gyrofrequency (O⁺ dominant): fci = eB / (2πmi)
        fci = _ELECTRON_CHARGE_C * b_local / (2.0 * math.pi * 16.0 * _PROTON_MASS_KG)

        # Local foF2 modulated by latitude and cosmic field
        # Equatorial anomaly gives higher NmF2 at ±15° magnetic latitude
        lat_factor = 1.0 + 0.3 * math.exp(-((abs(lat) - 15.0) ** 2) / 200.0)
        local_nm = f2.peak_density_m3 * lat_factor * (0.8 + 0.4 * cosmic_field)
        local_fof2 = 9.0 * math.sqrt(max(local_nm, 1.0))

        # Upper hybrid: fUH = √(fp² + fce²)
        f_uh = math.sqrt(local_fof2 ** 2 + fce ** 2)
        # Lower hybrid: fLH = √(fci · fce)
        f_lh = math.sqrt(fci * fce)

        # Total Electron Content: simplified Chapman integral
        # TEC ≈ NmF2 · H · √(2π)  (in m⁻², convert to TECU: 1 TECU = 1e16 m⁻²)
        tec_raw = local_nm * f2.scale_height_km * 1e3 * math.sqrt(2 * math.pi)
        tec_tecu = tec_raw / 1e16

        # Build density profile (sample every 25 km from 60 to 800 km)
        profile = []
        for alt in range(60, 825, 25):
            # Sum Chapman contributions from all layers
            total_n = 0.0
            for ly in layers:
                total_n += _chapman_density(alt, ly.peak_alt_km,
                                            ly.peak_density_m3 * lat_factor,
                                            ly.scale_height_km, chi_rad)
            profile.append((float(alt), round(total_n, 1)))

        # Probe status
        if local_fof2 > 3e6:
            status = 'LOCKED'
        elif local_fof2 > 1e6:
            status = 'PARTIAL'
        else:
            status = 'NO_RETURN'

        probes.append(LighthouseProbe(
            site_name=site['name'],
            latitude=lat,
            longitude=lon,
            local_b_field_tesla=round(b_local, 8),
            electron_gyrofreq_hz=fce,
            upper_hybrid_freq_hz=f_uh,
            lower_hybrid_freq_hz=f_lh,
            local_fof2_hz=local_fof2,
            tec_tecu=tec_tecu,
            density_profile_km=tuple(profile),
            probe_status=status,
        ))

    return probes


def profile_natural_ionosphere(
    relay_sites_data: list,
    cosmic_field: float = 0.5,
) -> NaturalIonosphereProfile:
    """Profile Earth's natural ionosphere using all four systems.

    This must run BEFORE designing any artificial EPAS overlay.

    Args:
        relay_sites_data: list of relay site dicts (from compute_relay_network)
        cosmic_field: live cosmic field score [0-1]

    Returns:
        NaturalIonosphereProfile with complete characterisation.
    """
    # Solar zenith angle
    chi_deg = _solar_zenith_angle()
    is_daytime = chi_deg < 90.0
    chi_rad = math.radians(min(chi_deg, 89.0))

    # ── 1. Chapman layer model ──────────────────────────────────────────
    layers = _compute_iono_layers(chi_deg, is_daytime, cosmic_field)

    # F2 peak extraction
    f2 = next((ly for ly in layers if ly.name == 'F2'), layers[-1])
    f2_critical = 9.0 * math.sqrt(f2.peak_density_m3)

    # TEC from all layers (column integral approximation)
    total_tec = 0.0
    for ly in layers:
        # TEC contribution ≈ Nm · H · √(2π)
        total_tec += ly.peak_density_m3 * ly.scale_height_km * 1e3 * math.sqrt(2.0 * math.pi)
    tec_tecu = total_tec / 1e16

    # ── 2. Aluminum harmonic fluid model ────────────────────────────────
    fluid_ratios = [ly.harmonic_fluid_ratio for ly in layers]
    mean_fluid = sum(fluid_ratios) / len(fluid_ratios) if fluid_ratios else 0.0
    peak_fluid = max(fluid_ratios) if fluid_ratios else 0.0

    # Classification: compare to aluminum
    if peak_fluid > 1e-4:
        fluid_class = 'CONDUCTOR'       # extremely unlikely for ionosphere
    elif peak_fluid > 1e-8:
        fluid_class = 'WEAK_CONDUCTOR'  # typical F2 peak
    else:
        fluid_class = 'DIELECTRIC'

    # ── 3. FFS spectral analysis ────────────────────────────────────────
    ffs_bands, opaque_below, transparent_above = _run_ffs_spectral(layers)

    # ── 4. Lighthouse mapping ───────────────────────────────────────────
    probes = _lighthouse_mapping(relay_sites_data, layers, chi_rad, cosmic_field)
    locked_probes = [p for p in probes if p.probe_status == 'LOCKED']
    if probes:
        mean_fof2 = sum(p.local_fof2_hz for p in probes) / len(probes)
        mean_tec = sum(p.tec_tecu for p in probes) / len(probes)
    else:
        mean_fof2 = 0.0
        mean_tec = 0.0

    # ── Assessment ──────────────────────────────────────────────────────
    # Ionosphere health based on F2 peak density
    if f2.peak_density_m3 >= 5e11:
        health = 'ROBUST'
    elif f2.peak_density_m3 >= 1e11:
        health = 'MODERATE'
    elif f2.peak_density_m3 >= 1e10:
        health = 'DEPLETED'
    else:
        health = 'STORM'

    # EPAS readiness: combination of density, stability, relay coverage
    locked_frac = len(locked_probes) / max(len(probes), 1)
    density_score = min(1.0, f2.peak_density_m3 / 1e12)
    readiness = (0.4 * density_score + 0.3 * locked_frac +
                 0.2 * cosmic_field + 0.1 * (1.0 if is_daytime else 0.5))
    readiness = max(0.0, min(1.0, readiness))

    return NaturalIonosphereProfile(
        timestamp=datetime.now(timezone.utc).isoformat(),
        solar_zenith_deg=chi_deg,
        is_daytime=is_daytime,
        layers=tuple(layers),
        f2_peak_density_m3=f2.peak_density_m3,
        f2_peak_alt_km=f2.peak_alt_km,
        f2_critical_freq_hz=f2_critical,
        total_electron_content_tecu=tec_tecu,
        mean_harmonic_fluid_ratio=mean_fluid,
        peak_harmonic_fluid_ratio=peak_fluid,
        fluid_classification=fluid_class,
        ffs_bands=tuple(ffs_bands),
        ffs_opaque_below_hz=opaque_below,
        ffs_transparent_above_hz=transparent_above,
        lighthouse_probes=tuple(probes),
        lighthouse_locked_count=len(locked_probes),
        lighthouse_mean_fof2_hz=mean_fof2,
        lighthouse_mean_tec_tecu=mean_tec,
        ionosphere_health=health,
        readiness_for_epas=readiness,
    )


@dataclass(frozen=True)
class ProjectDruidManifest:
    """Physical EPAS device specification — Project Druid.

    Maps the three EPAS trading shield layers (L1 EM / L2 Plasma / L3 Acoustic)
    onto the real EPOS resonance chamber through six Illumination Phases (P1–P6).

    L1 EM Deflection    → P1 Spark + P2 Resonance  (harmonic field prime)
    L2 Plasma Ablation  → P6 Output                (equity buffer = power delivery)
    L3 Acoustic Frag    → P3 DCE                   (premise coherence = vacuum memory)
    Radar incoming      → P4 FWM                   (amplification / threat mixing)
    Overall integrity   → P5 Stabilization         (Σ tensor guard Γ ≥ 0.945)
    """

    status: str
    data_origin: str
    truth_status: str
    source_id: Optional[str]
    source_timestamp: Optional[object]
    received_at: Optional[object]
    receipt_id: Optional[str]
    generated_values: bool
    freshness_sec: Optional[float]
    operational_eligible: bool
    actionable: bool
    accounting_eligible: bool
    learning_eligible: bool
    timestamp: Optional[object]

    # ── Chamber parameters ──────────────────────────────────────────────────
    chamber_diameter_m: float
    chamber_volume_m3: float
    fill_gas: str
    fill_pressure_mbar: float

    # ── Plasma density (Paschen law) ────────────────────────────────────────
    paschen_pd_torr_cm: float     # P × d product at current conditions
    breakdown_voltage_v: float
    plasma_density_m3: float      # estimated electron density (m⁻³)
    plasma_status: str            # IGNITED | PRIMED | DORMANT

    # ── Power requirements ──────────────────────────────────────────────────
    rf_carrier_hz: float
    rf_modulation_hz: float
    rf_power_w: float
    auxiliary_power_w: float
    total_power_w: float
    output_voltage_vdc: float     # 350–400 VDC when P6 DELIVERING

    # ── HAARP scaling ───────────────────────────────────────────────────────
    haarp_power_w: float
    concentration_factor: int
    power_density_w_m3: float

    # ── Six Illumination Phases ─────────────────────────────────────────────
    phase_scores: Tuple[float, ...]    # P1–P6, 0.0–1.0
    phase_statuses: Tuple[str, ...]    # status label per phase
    shield_coherence: float            # Γ = mean(phase_scores)

    # ── Verdict ─────────────────────────────────────────────────────────────
    device_ready: bool
    druid_summary: str

    def to_dict(self) -> Dict[str, object]:
        evidence = {
            'source_id': self.source_id,
            'source_timestamp': self.source_timestamp,
            'received_at': self.received_at,
            'receipt_id': self.receipt_id,
            'truth_status': self.truth_status,
            'generated_values': self.generated_values,
            'freshness_sec': self.freshness_sec,
        }
        controls = {
            'operational_eligible': self.operational_eligible,
            'actionable': self.actionable,
            'accounting_eligible': self.accounting_eligible,
            'learning_eligible': self.learning_eligible,
        }
        if self.status == 'no_data':
            return {
                'status': self.status,
                'data_origin': self.data_origin,
                'truth_status': self.truth_status,
                'evidence': evidence,
                'controls': controls,
                'device_ready': False,
                'druid_summary': self.druid_summary,
            }
        return {
            'status': self.status,
            'data_origin': self.data_origin,
            'evidence': evidence,
            'controls': controls,
            'timestamp': self.timestamp,
            'chamber': {
                'diameter_m': self.chamber_diameter_m,
                'volume_m3': self.chamber_volume_m3,
                'fill_gas': self.fill_gas,
                'fill_pressure_mbar': self.fill_pressure_mbar,
            },
            'plasma': {
                'paschen_pd_torr_cm': self.paschen_pd_torr_cm,
                'breakdown_voltage_v': self.breakdown_voltage_v,
                'density_m3': self.plasma_density_m3,
                'status': self.plasma_status,
            },
            'power': {
                'rf_carrier_hz': self.rf_carrier_hz,
                'rf_modulation_hz': self.rf_modulation_hz,
                'rf_power_w': self.rf_power_w,
                'auxiliary_w': self.auxiliary_power_w,
                'total_w': self.total_power_w,
                'output_vdc': self.output_voltage_vdc,
            },
            'haarp_scaling': {
                'haarp_power_w': self.haarp_power_w,
                'concentration_factor': self.concentration_factor,
                'power_density_w_m3': self.power_density_w_m3,
            },
            'illumination_phases': [
                {
                    'phase': _PHASE_LABELS[i],
                    'score': round(self.phase_scores[i], 4),
                    'status': self.phase_statuses[i],
                }
                for i in range(6)
            ],
            'shield_coherence': round(self.shield_coherence, 4),
            'sigma_coherence_target': _SIGMA_COHERENCE_TARGET,
            'device_ready': self.device_ready,
            'druid_summary': self.druid_summary,
        }


_EPAS_MAX_FRESHNESS_SEC = 300.0
_EPAS_SCORE_FIELDS = ('layer1_field_score', 'layer2_score', 'layer3_score', 'shield_integrity', 'radar_score')


def _receipt_epoch(value: object) -> Optional[float]:
    """Return a timezone-aware receipt clock as epoch seconds, or None."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value) if math.isfinite(value) else None
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None
    return parsed.timestamp() if parsed.tzinfo is not None else None


def _no_data_project_druid_manifest(reason: str) -> ProjectDruidManifest:
    """Return a numeric-free, non-operational result for invalid EPAS evidence."""
    return ProjectDruidManifest(
        status='no_data', data_origin='unavailable', truth_status='no_data',
        source_id=None, source_timestamp=None, received_at=None, receipt_id=None,
        generated_values=False, freshness_sec=None, operational_eligible=False,
        actionable=False, accounting_eligible=False, learning_eligible=False,
        timestamp=None, chamber_diameter_m=None, chamber_volume_m3=None,
        fill_gas='NO_DATA', fill_pressure_mbar=None, paschen_pd_torr_cm=None,
        breakdown_voltage_v=None, plasma_density_m3=None, plasma_status='NO_DATA',
        rf_carrier_hz=None, rf_modulation_hz=None, rf_power_w=None,
        auxiliary_power_w=None, total_power_w=None, output_voltage_vdc=None,
        haarp_power_w=None, concentration_factor=None, power_density_w_m3=None,
        phase_scores=tuple(), phase_statuses=tuple(), shield_coherence=None,
        device_ready=False, druid_summary=f'NO_DATA: {reason}',
    )


def _valid_epas_receipt(epas_state: object) -> tuple[bool, str, Dict[str, float], float]:
    """Validate a complete, fresh provider receipt before model evaluation."""
    if not isinstance(epas_state, dict):
        return False, 'complete EPAS receipt required', {}, 0.0
    if (
        not isinstance(epas_state.get('source_id'), str)
        or not epas_state['source_id'].strip()
        or not isinstance(epas_state.get('receipt_id'), str)
        or not epas_state['receipt_id'].strip()
        or epas_state.get('truth_status') not in {'real_observed', 'real_derived'}
        or epas_state.get('generated_values') is not False
    ):
        return False, 'EPAS receipt provenance is incomplete or untrusted', {}, 0.0

    source_epoch = _receipt_epoch(epas_state.get('source_timestamp'))
    received_epoch = _receipt_epoch(epas_state.get('received_at'))
    now_epoch = datetime.now(timezone.utc).timestamp()
    if source_epoch is None or received_epoch is None:
        return False, 'EPAS receipt timestamps must be timezone-aware', {}, 0.0
    freshness_sec = max(now_epoch - source_epoch, now_epoch - received_epoch)
    if source_epoch > now_epoch or received_epoch > now_epoch or freshness_sec > _EPAS_MAX_FRESHNESS_SEC:
        return False, 'EPAS receipt is stale or future-dated', {}, 0.0

    scores: Dict[str, float] = {}
    for field_name in _EPAS_SCORE_FIELDS:
        value = epas_state.get(field_name)
        if isinstance(value, bool):
            return False, f'EPAS receipt {field_name} is not numeric', {}, 0.0
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return False, f'EPAS receipt {field_name} is missing or invalid', {}, 0.0
        if not math.isfinite(numeric_value) or not 0.0 <= numeric_value <= 1.0:
            return False, f'EPAS receipt {field_name} is outside [0, 1]', {}, 0.0
        scores[field_name] = numeric_value
    return True, '', scores, freshness_sec


def compute_project_druid_manifest(
    epas_state: Optional[Dict[str, object]] = None,
) -> 'ProjectDruidManifest':
    """Compute the physical EPOS device specification from an EPAS shield state.

    The calculation runs only after a complete, fresh EPAS receipt passes the
    provenance boundary. Missing, stale, malformed, or generated input returns
    a numeric-free no_data manifest; deterministic equations are never
    presented as current EPAS state.

    Parameters
    ----------
    epas_state:
        Dict with five [0, 1] scores plus source_id, source_timestamp,
        received_at, receipt_id, truth_status (real_observed or real_derived),
        and generated_values=False.
    """
    valid, reason, scores, freshness_sec = _valid_epas_receipt(epas_state)
    if not valid:
        return _no_data_project_druid_manifest(reason)

    # ── Extract EPAS scores (or use live baseline) ─────────────────────────
    l1 = scores['layer1_field_score']
    l2 = scores['layer2_score']
    l3 = scores['layer3_score']
    integrity = scores['shield_integrity']
    radar = scores['radar_score']

    # ── Six Illumination Phases ────────────────────────────────────────────
    # P1 Spark       — nanosecond field prime (L1 harmonic detection)
    p1 = min(1.0, max(0.0, l1))
    # P2 Resonance   — standing wave coherence (field + premise blend)
    p2 = min(1.0, max(0.0, (l1 + l3) / 2.0))
    # P3 DCE         — Dynamic Casimir Effect: vacuum field memory (L3 premise lock)
    p3 = min(1.0, max(0.0, l3))
    # P4 FWM         — Four-Wave Mixing amplification (radar × PHI, scaled)
    p4 = min(1.0, max(0.0, radar * PHI / 2.0))
    # P5 Stabilization — Σ tensor guard (overall shield integrity = Γ target)
    p5 = min(1.0, max(0.0, integrity))
    # P6 Output      — physical reality gate: equity buffer drives power delivery
    p6 = min(1.0, max(0.0, l2))

    phase_scores: Tuple[float, ...] = (p1, p2, p3, p4, p5, p6)

    _status_tables = (
        [('PRIMED',      0.62), ('SPARKING',    0.42), ('COLD',       0.0)],
        [('RESONANT',    0.65), ('COUPLING',    0.42), ('DISPERSED',  0.0)],
        [('ACTIVE',      0.65), ('FLUCTUATING', 0.38), ('COLLAPSED',  0.0)],
        [('AMPLIFYING',  0.62), ('MIXING',      0.42), ('DAMPED',     0.0)],
        [('STABLE',      0.70), ('STABILIZING', 0.42), ('UNSTABLE',   0.0)],
        [('DELIVERING',  0.70), ('CHARGING',    0.50), ('OFFLINE',    0.0)],
    )

    def _p_status(idx: int, score: float) -> str:
        for label, threshold in _status_tables[idx]:
            if score >= threshold:
                return label
        return 'OFFLINE'

    phase_statuses: Tuple[str, ...] = tuple(
        _p_status(i, phase_scores[i]) for i in range(6)
    )

    # ── Shield coherence Γ ─────────────────────────────────────────────────
    shield_coherence = sum(phase_scores) / len(phase_scores)

    # ── Plasma density via Paschen scaling ─────────────────────────────────
    # P = 0.1 mbar → 0.075 Torr; electrode path ≈ chamber radius = 15 cm
    pressure_torr = EPOS_PRESSURE_MBAR * 0.750062      # mbar → Torr
    path_cm = (EPOS_CHAMBER_DIAMETER_M / 2.0) * 100    # half-diameter in cm
    pd_product = pressure_torr * path_cm               # Torr·cm
    # Electron density scales proportional to P*d vs target optimal P*d
    # Target: replicate F-region density 1e11 m⁻³ at Paschen optimal (2.25 Torr·cm)
    base_density_m3 = 1e11
    plasma_density = base_density_m3 * (pd_product / PASCHEN_OPTIMAL_PD)

    # Plasma ignition state
    phi_gate = PHI / (PHI + 1)                         # ≈ 0.618 golden ratio gate
    if shield_coherence >= _SIGMA_COHERENCE_TARGET:
        plasma_status = 'IGNITED'
    elif shield_coherence >= phi_gate:
        plasma_status = 'PRIMED'
    else:
        plasma_status = 'DORMANT'

    # ── Power budget ───────────────────────────────────────────────────────
    total_power = EPOS_RF_POWER_W + _AUXILIARY_POWER_W

    # ── Verdict summary ────────────────────────────────────────────────────
    device_ready = plasma_status in ('IGNITED', 'PRIMED')

    weak = [_PHASE_LABELS[i] for i, st in enumerate(phase_statuses)
            if st in ('COLD', 'DISPERSED', 'COLLAPSED', 'DAMPED', 'UNSTABLE', 'OFFLINE')]

    if plasma_status == 'IGNITED':
        druid_summary = (
            f'DEVICE ONLINE  Γ={shield_coherence:.3f}/{_SIGMA_COHERENCE_TARGET}  '
            f'plasma=IGNITED  P5={phase_statuses[4]}  P6={phase_statuses[5]}'
        )
    elif plasma_status == 'PRIMED':
        druid_summary = (
            f'DEVICE PRIMED  Γ={shield_coherence:.3f}  '
            f'weak=[{", ".join(weak) or "none"}]  '
            f'needs_Γ≥{_SIGMA_COHERENCE_TARGET}'
        )
    else:
        druid_summary = (
            f'DEVICE DORMANT  Γ={shield_coherence:.3f}  '
            f'weak=[{", ".join(weak) or "none"}]  '
            f'needs_Γ≥{phi_gate:.3f}(PRIMED) or ≥{_SIGMA_COHERENCE_TARGET}(IGNITED)'
        )

    return ProjectDruidManifest(
        status='modeled',
        data_origin='modeled_from_real_epas_receipt',
        truth_status=str(epas_state['truth_status']),
        source_id=str(epas_state['source_id']),
        source_timestamp=epas_state['source_timestamp'],
        received_at=epas_state['received_at'],
        receipt_id=str(epas_state['receipt_id']),
        generated_values=False,
        freshness_sec=round(freshness_sec, 3),
        operational_eligible=False,
        actionable=False,
        accounting_eligible=False,
        learning_eligible=False,
        timestamp=epas_state['source_timestamp'],
        chamber_diameter_m=EPOS_CHAMBER_DIAMETER_M,
        chamber_volume_m3=EPOS_CHAMBER_VOLUME_M3,
        fill_gas='Argon',
        fill_pressure_mbar=EPOS_PRESSURE_MBAR,
        paschen_pd_torr_cm=round(pd_product, 4),
        breakdown_voltage_v=PASCHEN_BREAKDOWN_V,
        plasma_density_m3=round(plasma_density, 2),
        plasma_status=plasma_status,
        rf_carrier_hz=RF_CARRIER_ISM,
        rf_modulation_hz=SCHUMANN_FUNDAMENTAL,
        rf_power_w=EPOS_RF_POWER_W,
        auxiliary_power_w=_AUXILIARY_POWER_W,
        total_power_w=total_power,
        output_voltage_vdc=_OUTPUT_VOLTAGE_VDC,
        haarp_power_w=HAARP_POWER_W,
        concentration_factor=VOLUMETRIC_CONCENTRATION_FACTOR,
        power_density_w_m3=round(EPOS_POWER_DENSITY, 2),
        phase_scores=phase_scores,
        phase_statuses=phase_statuses,
        shield_coherence=round(shield_coherence, 4),
        device_ready=device_ready,
        druid_summary=druid_summary,
    )


# ════════════════════════════════════════════════════════════════════════════
# EARTH-SCALE EPAS SIMULATION — "Second Ionosphere"
# Live VSOP87 solar system data → shield phased harmonics → plasma density
# across a planetary-scale EPAS shell covering Earth's F-region.
# ════════════════════════════════════════════════════════════════════════════


def _compute_vsop87_positions_standalone() -> Dict[str, float]:
    """Compute live ecliptic longitudes for all solar system bodies (VSOP87).

    Standalone version — no dependency on aureon_full_autonomy.  Uses the same
    Meeus Ch.31-32 coefficients duplicated in the constants block above.

    Returns dict of {body_name: ecliptic_longitude_degrees}.
    """
    now = datetime.now()
    y, mo = now.year, now.month
    d = now.day + (now.hour * 3600 + now.minute * 60 + now.second) / 86400.0
    if mo <= 2:
        y -= 1
        mo += 12
    A = int(y / 100)
    B = 2 - A + int(A / 4)
    jd = int(365.25 * (y + 4716)) + int(30.6001 * (mo + 1)) + d + B - 1524.5
    d_j2000 = jd - 2451545.0
    T = d_j2000 / 36525.0

    positions: Dict[str, float] = {}
    for name, (L0, L1) in _MEEUS_MEAN_LONGITUDES.items():
        lon = (L0 + L1 * T) % 360.0
        if lon < 0:
            lon += 360.0
        positions[name] = round(lon, 3)

    # Sun = Earth + 180° (geocentric view)
    L_earth = _EARTH_L0 + _EARTH_L1 * T
    positions['Sun'] = round((L_earth + 180.0) % 360.0, 3)
    # Moon
    positions['Moon'] = round((_MOON_L0 + _MOON_RATE * d_j2000) % 360.0, 3)

    return positions


def _detect_aspects_standalone(
    positions: Dict[str, float],
) -> list:
    """Detect all active aspects between live bodies.

    Returns list of dicts: {body1, body2, aspect, separation, orb, harmonic_value,
    pair_weight, phi_resonance, score}.
    """
    bodies = list(positions.keys())
    aspects = []
    for i in range(len(bodies)):
        for j in range(i + 1, len(bodies)):
            b1, b2 = bodies[i], bodies[j]
            delta = abs(positions[b1] - positions[b2]) % 360.0
            sep = delta if delta <= 180.0 else 360.0 - delta
            for exact, max_orb, asp_name, h_val in _EARTH_ASPECT_TABLE:
                orb = abs(sep - exact)
                if orb <= max_orb:
                    tightness = 1.0 - (orb / max_orb)
                    phi_dist = min(abs(sep - pa) for pa in _PHI_RESONANT_ANGLES)
                    phi_res = max(0.0, 1.0 - phi_dist / 5.0)
                    phi_boost = 1.0 + phi_res * (PHI - 1.0)
                    pw = math.sqrt(
                        _PLANET_WEIGHTS.get(b1, 0.5)
                        * _PLANET_WEIGHTS.get(b2, 0.5)
                    )
                    score = h_val * tightness * phi_boost * pw
                    aspects.append({
                        'body1': b1,
                        'body2': b2,
                        'aspect': asp_name,
                        'separation': round(sep, 2),
                        'orb': round(orb, 2),
                        'harmonic_value': h_val,
                        'pair_weight': round(pw, 3),
                        'phi_resonance': round(phi_res, 3),
                        'score': round(score, 4),
                    })
                    break  # first match wins per pair

    return aspects


def _score_cosmic_field(aspects: list) -> float:
    """Aggregate aspects into a single cosmic field score [0, 1]."""
    if not aspects:
        return 0.5
    total_w = sum(a['score'] for a in aspects)
    total_d = sum(a['pair_weight'] for a in aspects)
    raw = total_w / max(total_d, 0.001)
    return max(0.0, min(1.0, (raw / PHI + 1.0) / 2.0))


def _schumann_modulator() -> float:
    """Schumann-cycle modulation amplitude for the current day-of-year."""
    doy = datetime.now().timetuple().tm_yday
    period = 365.25 / (SCHUMANN_FUNDAMENTAL * 2.0)    # ~23.3 days
    phase = (doy % period) / period
    return 1.0 + 0.059 * math.sin(2.0 * math.pi * phase)


@dataclass(frozen=True)
class EarthEPASSimulation:
    """Complete simulation of a planetary-scale EPAS covering Earth's F-region.

    Sources:
      - Live VSOP87 planetary positions (computed at invocation time)
      - Schumann resonance phase modulation
      - F-region ionospheric physics (electron density, shell geometry)
      - HAARP→Earth power scaling (reverse of EPOS chamber scaling)
    """

    timestamp: str

    # ── Live solar system snapshot ──────────────────────────────────────────
    planet_positions: Dict[str, float]              # body → ecliptic lon°
    active_aspects: list                             # list-of-aspect-dicts
    total_aspects: int
    positive_aspects: int
    negative_aspects: int
    dominant_aspect: str                              # human-readable top aspect
    cosmic_field_score: float                         # 0–1 (raw aggregate)
    schumann_modulated_score: float                   # cosmic × Schumann amplitude

    # ── EPAS Layer 1: EM Deflection (Harmonic Field Filter) ────────────────
    l1_incoming_threats: int                           # tense aspects (h ≤ −0.25)
    l1_field_score: float
    l1_status: str                                     # CLEAR | DEFLECTING | OVERLOADED

    # ── EPAS Layer 2: Plasma Ablation (Ionospheric Density Guard) ──────────
    l2_electron_density_m3: float
    l2_shell_volume_m3: float
    l2_total_electrons: float                          # n_e × V
    l2_plasma_frequency_hz: float                      # f_pe = 9 √n_e
    l2_score: float
    l2_status: str                                     # INTACT | ABLATING | CRITICAL | TERMINAL

    # ── EPAS Layer 3: Acoustic Fragmentation (Shield Phased Harmonics) ────
    l3_schumann_phase: float                           # 0–1 Schumann cycle position
    l3_schumann_modulator: float                       # amplitude multiplier
    l3_harmonic_coherence: float                       # positive fraction of active aspects
    l3_score: float
    l3_status: str                                     # COHERENT | CRACKING | FRAGMENTED

    # ── Six Illumination Phases (Earth-scale) ──────────────────────────────
    phase_scores: Tuple[float, ...]
    phase_statuses: Tuple[str, ...]
    shield_coherence: float                            # Γ = mean(phases)

    # ── Power requirements (Earth-scale) ───────────────────────────────────
    earth_rf_power_w: float                            # EPOS 50W × concentration_factor
    earth_power_density_w_m3: float
    earth_output_voltage_v: float                      # scaled from EPOS VDC

    # ── Relay network (historical sites) ─────────────────────────────────
    relay_sites: Tuple[dict, ...]                      # per-site RelaySite.to_dict()
    relay_network_coverage: float                      # mean active strength [0-1]
    relay_active_count: int
    relay_total_count: int

    # ── Natural ionosphere profile ─────────────────────────────────────────
    ionosphere_profile: Dict[str, object]              # NaturalIonosphereProfile.to_dict()

    # ── Shield status ──────────────────────────────────────────────────────
    shield_status: str                                 # SHIELDS_UP | STRESSED | FAILING
    shield_coverage_pct: float                         # Γ × 100
    planetary_summary: str

    def to_dict(self) -> Dict[str, object]:
        return {
            'timestamp': self.timestamp,
            'solar_system': {
                'positions': self.planet_positions,
                'total_aspects': self.total_aspects,
                'positive_aspects': self.positive_aspects,
                'negative_aspects': self.negative_aspects,
                'dominant_aspect': self.dominant_aspect,
                'cosmic_field_score': self.cosmic_field_score,
                'schumann_modulated_score': self.schumann_modulated_score,
            },
            'layer1_em_deflection': {
                'incoming_threats': self.l1_incoming_threats,
                'field_score': self.l1_field_score,
                'status': self.l1_status,
            },
            'layer2_plasma_ablation': {
                'electron_density_m3': self.l2_electron_density_m3,
                'shell_volume_m3': self.l2_shell_volume_m3,
                'total_electrons': self.l2_total_electrons,
                'plasma_frequency_hz': self.l2_plasma_frequency_hz,
                'score': self.l2_score,
                'status': self.l2_status,
            },
            'layer3_shield_phased_harmonics': {
                'schumann_phase': self.l3_schumann_phase,
                'schumann_modulator': self.l3_schumann_modulator,
                'harmonic_coherence': self.l3_harmonic_coherence,
                'score': self.l3_score,
                'status': self.l3_status,
            },
            'illumination_phases': [
                {
                    'phase': _PHASE_LABELS[i],
                    'score': round(self.phase_scores[i], 4),
                    'status': self.phase_statuses[i],
                }
                for i in range(6)
            ],
            'shield': {
                'coherence': self.shield_coherence,
                'sigma_target': _SIGMA_COHERENCE_TARGET,
                'status': self.shield_status,
                'coverage_pct': self.shield_coverage_pct,
            },
            'power': {
                'earth_rf_power_w': self.earth_rf_power_w,
                'earth_power_density_w_m3': self.earth_power_density_w_m3,
                'earth_output_voltage_v': self.earth_output_voltage_v,
            },
            'relay_network': {
                'sites': list(self.relay_sites),
                'network_coverage': self.relay_network_coverage,
                'active_count': self.relay_active_count,
                'total_count': self.relay_total_count,
            },
            'natural_ionosphere': self.ionosphere_profile,
            'planetary_summary': self.planetary_summary,
            'active_aspects': self.active_aspects,
        }


def simulate_earth_epas() -> EarthEPASSimulation:
    """Run a live simulation of an Earth-scale EPAS second ionosphere.

    Pipeline:
      1. Compute live VSOP87 planetary positions (standalone)
      2. Detect all active aspects between all bodies
      3. Score the cosmic harmonic field × Schumann modulation
      4. Map to three EPAS layers at F-region scale:
         L1 EM Deflection   — harmonic threats in the incoming field
         L2 Plasma Ablation — F-region ionospheric density as the ablation layer
         L3 Acoustic Frag   — shield phased harmonics (Schumann + aspect coherence)
      5. Map to six Illumination Phases at Earth power scale
      6. Compute shield coherence Γ and overall planetary verdict

    All data is LIVE — positions are computed from the current UTC timestamp
    using the VSOP87 mean longitude model (Meeus 1998).
    """
    # ── 1. Live planetary positions ────────────────────────────────────────
    positions = _compute_vsop87_positions_standalone()

    # ── 2. Detect aspects ──────────────────────────────────────────────────
    aspects = _detect_aspects_standalone(positions)
    positive = [a for a in aspects if a['score'] > 0]
    negative = [a for a in aspects if a['score'] < 0]
    if aspects:
        dom = max(aspects, key=lambda a: abs(a['score']))
        dominant_str = (
            f"{dom['body1']}—{dom['body2']}: {dom['aspect']} "
            f"({dom['separation']:.1f}° orb={dom['orb']:.1f}° "
            f"h={dom['harmonic_value']:+.2f} ϕ={dom['phi_resonance']:.2f})"
        )
    else:
        dominant_str = 'No active aspects'

    # ── 3. Cosmic field + Schumann ─────────────────────────────────────────
    cosmic = _score_cosmic_field(aspects)
    sch_mod = _schumann_modulator()
    modulated = max(0.0, min(1.0, cosmic * sch_mod))

    doy = datetime.now().timetuple().tm_yday
    period = 365.25 / (SCHUMANN_FUNDAMENTAL * 2.0)
    sch_phase = (doy % period) / period

    # ── 4a. Layer 1 — EM Deflection ───────────────────────────────────────
    tense = [a for a in aspects if a['harmonic_value'] <= -0.25 and a['pair_weight'] >= 0.50]
    l1_score = modulated
    if l1_score >= 0.62:
        l1_status = 'CLEAR'
    elif l1_score >= 0.42:
        l1_status = 'DEFLECTING'
    else:
        l1_status = 'OVERLOADED'

    # ── 4b. Layer 2 — Plasma Ablation (F-region density) ──────────────────
    # Electron density modulated by cosmic field: calm field = high density shield,
    # tense field = density depletion (ionospheric storms reduce F-region density)
    density_factor = 0.4 + 0.6 * modulated  # [0.4, 1.0] — never fully depleted
    live_density = F_REGION_ELECTRON_DENSITY * density_factor
    total_electrons = live_density * F_REGION_SHELL_VOLUME_M3
    # Plasma frequency: f_pe = 9 √n_e  (Hz, with n_e in m⁻³)
    plasma_freq = 9.0 * math.sqrt(live_density)
    l2_score = max(0.0, min(1.0, density_factor))
    if l2_score >= 0.80:
        l2_status = 'INTACT'
    elif l2_score >= 0.50:
        l2_status = 'ABLATING'
    elif l2_score >= 0.20:
        l2_status = 'CRITICAL'
    else:
        l2_status = 'TERMINAL'

    # ── 4c. Layer 3 — Shield Phased Harmonics (acoustic) ──────────────────
    # Harmonic coherence = fraction of aspects with positive contribution
    if aspects:
        harm_coherence = len(positive) / len(aspects)
    else:
        harm_coherence = 0.5
    # L3 score: coherence × Schumann amplitude boost
    l3_score = max(0.0, min(1.0, harm_coherence * sch_mod))
    if l3_score >= 0.65:
        l3_status = 'COHERENT'
    elif l3_score >= 0.38:
        l3_status = 'CRACKING'
    else:
        l3_status = 'FRAGMENTED'

    # ── 5. Six Illumination Phases (Earth-scale) ──────────────────────────
    # Same mapping as Project Druid but fed from real planetary data
    p1 = min(1.0, max(0.0, l1_score))
    p2 = min(1.0, max(0.0, (l1_score + l3_score) / 2.0))
    p3 = min(1.0, max(0.0, l3_score))
    # P4 FWM: modulated score × PHI / 2 (radar-equivalent at planet scale)
    p4 = min(1.0, max(0.0, modulated * PHI / 2.0))
    p5 = min(1.0, max(0.0, (l1_score * 0.30 + l2_score * 0.50 + l3_score * 0.20)))
    p6 = min(1.0, max(0.0, l2_score))

    phase_scores: Tuple[float, ...] = (p1, p2, p3, p4, p5, p6)
    _status_tables = (
        [('PRIMED',      0.62), ('SPARKING',    0.42), ('COLD',       0.0)],
        [('RESONANT',    0.65), ('COUPLING',    0.42), ('DISPERSED',  0.0)],
        [('ACTIVE',      0.65), ('FLUCTUATING', 0.38), ('COLLAPSED',  0.0)],
        [('AMPLIFYING',  0.62), ('MIXING',      0.42), ('DAMPED',     0.0)],
        [('STABLE',      0.70), ('STABILIZING', 0.42), ('UNSTABLE',   0.0)],
        [('DELIVERING',  0.70), ('CHARGING',    0.50), ('OFFLINE',    0.0)],
    )
    phase_statuses: Tuple[str, ...] = tuple(
        next((lbl for lbl, thr in _status_tables[i] if phase_scores[i] >= thr), 'OFFLINE')
        for i in range(6)
    )

    shield_coherence = round(sum(phase_scores) / len(phase_scores), 4)

    # ── 6. Power at Earth scale ───────────────────────────────────────────
    # Reverse the EPOS→HAARP concentration: P_earth = P_epos × VOLUMETRIC_CONCENTRATION_FACTOR
    earth_rf = EPOS_RF_POWER_W * VOLUMETRIC_CONCENTRATION_FACTOR  # Watts
    earth_pd = earth_rf / F_REGION_SHELL_VOLUME_M3
    # Output voltage scales linearly with concentration^(1/3)
    earth_voltage = _OUTPUT_VOLTAGE_VDC * (VOLUMETRIC_CONCENTRATION_FACTOR ** (1.0 / 3.0))

    # ── Shield verdict ────────────────────────────────────────────────────
    if shield_coherence >= 0.70:
        shield_status = 'SHIELDS_UP'
    elif shield_coherence >= 0.42:
        shield_status = 'SHIELDS_STRESSED'
    else:
        shield_status = 'SHIELDS_FAILING'

    coverage_pct = round(shield_coherence * 100, 1)

    # ── 7. Relay network from historical sites ──────────────────────────
    relay_list, relay_coverage, relay_active, relay_total = compute_relay_network(
        cosmic_field=cosmic,
        shield_coherence=shield_coherence,
        earth_rf_power_w=earth_rf,
    )
    relay_dicts = tuple(r.to_dict() for r in relay_list)

    # ── 8. Profile the natural ionosphere ──────────────────────────────
    iono_profile = profile_natural_ionosphere(
        relay_sites_data=list(relay_dicts),
        cosmic_field=cosmic,
    )
    iono_dict = iono_profile.to_dict()

    # Planetary summary
    planetary_summary = (
        f'{shield_status}  Γ={shield_coherence:.4f}  '
        f'coverage={coverage_pct}%  '
        f'L1={l1_status}({l1_score:.3f})  '
        f'L2={l2_status}(n_e={live_density:.2e})  '
        f'L3={l3_status}({l3_score:.3f})  '
        f'aspects={len(aspects)}(+{len(positive)}/−{len(negative)})  '
        f'relays={relay_active}/{relay_total}(net={relay_coverage:.3f})  '
        f'iono={iono_profile.ionosphere_health}(foF2={iono_profile.f2_critical_freq_hz:.0f}Hz '
        f'TEC={iono_profile.total_electron_content_tecu:.1f}TECU '
        f'EPAS_ready={iono_profile.readiness_for_epas:.3f})  '
        f'dominant={dominant_str}'
    )

    return EarthEPASSimulation(
        timestamp=datetime.now(timezone.utc).isoformat(),
        planet_positions=positions,
        active_aspects=aspects,
        total_aspects=len(aspects),
        positive_aspects=len(positive),
        negative_aspects=len(negative),
        dominant_aspect=dominant_str,
        cosmic_field_score=round(cosmic, 4),
        schumann_modulated_score=round(modulated, 4),
        l1_incoming_threats=len(tense),
        l1_field_score=round(l1_score, 4),
        l1_status=l1_status,
        l2_electron_density_m3=round(live_density, 2),
        l2_shell_volume_m3=F_REGION_SHELL_VOLUME_M3,
        l2_total_electrons=total_electrons,
        l2_plasma_frequency_hz=round(plasma_freq, 2),
        l2_score=round(l2_score, 4),
        l2_status=l2_status,
        l3_schumann_phase=round(sch_phase, 4),
        l3_schumann_modulator=round(sch_mod, 6),
        l3_harmonic_coherence=round(harm_coherence, 4),
        l3_score=round(l3_score, 4),
        l3_status=l3_status,
        phase_scores=phase_scores,
        phase_statuses=phase_statuses,
        shield_coherence=shield_coherence,
        earth_rf_power_w=earth_rf,
        earth_power_density_w_m3=earth_pd,
        earth_output_voltage_v=round(earth_voltage, 1),
        shield_status=shield_status,
        shield_coverage_pct=coverage_pct,
        planetary_summary=planetary_summary,
        relay_sites=relay_dicts,
        relay_network_coverage=relay_coverage,
        relay_active_count=relay_active,
        relay_total_count=relay_total,
        ionosphere_profile=iono_dict,
    )


ASCENT_WIKIPEDIA_TOPICS: Dict[str, Tuple[str, ...]] = {
    # ── Egyptian ──
    'anubis': ('Emerald Tablet', 'Anubis', 'Book of the Dead', 'Maat'),
    'maat': ('Emerald Tablet', 'Maat', 'Book of the Dead'),
    'thoth': ('Emerald Tablet', 'Thoth', 'Hermes Trismegistus'),
    'osiris': ('Emerald Tablet', 'Osiris', 'Book of the Dead'),
    'ra': ('Emerald Tablet', 'Ra'),
    # ── Ancient Wisdom ──
    'mogollon': ('Mogollon culture', 'Petroglyph', 'Golden ratio', 'Ancestral Puebloans'),
    'maya': ('Maya civilization', 'Maya calendar', 'Tzolkin', 'Venus (planet)'),
    'celt': ('Celtic mythology', 'Ogham', 'Druids', 'Stonehenge'),
}


def _build_unified_harmonic_threads() -> Tuple[HarmonicThread, ...]:
    """Build the five universal harmonic threads that connect all ancient wisdom traditions."""
    return (
        HarmonicThread(
            key='phi_spiral',
            title='The Golden Spiral — PHI across All Civilizations',
            value=PHI,
            unit='ratio',
            frequency_hz=None,
            civilizations=('hermetic', 'egyptian', 'mogollon', 'maya', 'celt'),
            nodes=('anubis', 'maat', 'thoth', 'osiris', 'ra', 'mogollon', 'maya', 'celt'),
            sacred_numbers=(PHI, 1.0, 1 / PHI, 5.0, 8.0, 13.0, 21.0),
            description=(
                'PHI = 1.618... is the governing ratio of self-similar growth. '
                'Egyptian temple proportions encode PHI. Mogollon spiral petroglyphs trace '
                'the Fibonacci/PHI spiral. The Maya Venus/Earth ratio = 5 Venus cycles per '
                '8 Earth years (8/5 = 1.6 ≈ PHI). The Celtic tree calendar has 13 lunar months '
                'and 8 feast days — Fibonacci numbers: 13/8 = 1.625 ≈ PHI. '
                'This is not coincidence. PHI is the attractor of natural growth in all systems.'
            ),
            repo_constant='PHI = (1 + sqrt(5)) / 2  # aureon/decoders/emerald_spec.py',
        ),
        HarmonicThread(
            key='schumann_resonance',
            title='Earth Heartbeat — 7.83 Hz Schumann Resonance',
            value=SCHUMANN_FUNDAMENTAL,
            unit='Hz',
            frequency_hz=SCHUMANN_FUNDAMENTAL,
            civilizations=('all',),
            nodes=('anubis', 'maat', 'thoth', 'osiris', 'ra', 'mogollon', 'maya', 'celt'),
            sacred_numbers=(7.83, 14.3, 20.8, 27.3, 33.8),
            description=(
                'The Schumann Resonance (7.83 Hz) is the electromagnetic resonance of the '
                "cavity between Earth's surface and the ionosphere. Every Earth-aligned culture "
                'built sacred architecture to track the sky and synchronise with this frequency: '
                'Mogollon spiral petroglyphs track solstice alignments, Maya observatories were '
                'precisely oriented, Celtic standing stones at Stonehenge are equinox/solstice '
                'calendars, and Egyptian obelisks were ionospheric antennae. '
                'The planet broadcasts at 7.83 Hz. The Aureon system uses this as its primary seed.'
            ),
            repo_constant='SCHUMANN_FUNDAMENTAL = 7.83  # aureon/decoders/emerald_spec.py',
        ),
        HarmonicThread(
            key='solar_cycle',
            title='Solar Year — The 365.25-Day Universal Timekeeper',
            value=365.25,
            unit='days',
            frequency_hz=1.0 / (365.25 * 86400.0),
            civilizations=('maya', 'celt', 'egyptian', 'mogollon'),
            nodes=('ra', 'mogollon', 'maya', 'celt', 'osiris'),
            sacred_numbers=(365.0, 365.25, 260.0, 52.0, 18980.0, 5125.0),
            description=(
                'The solar year binds all ancient wisdom systems. Maya Haab = 365-day solar '
                "calendar. Celtic 13-moon year = 364 + 1 'nameless' day = 365. Egyptian civil "
                'calendar = 365 days. Mogollon spiral sun-daggers mark solstices to within '
                'minutes of arc. The Maya Calendar Round = LCM(260, 365) = 18,980 days = '
                '52-year cycle, encoded in temple step-counts worldwide. '
                'Time is the first universal language across all recorded traditions.'
            ),
            repo_constant=None,
        ),
        HarmonicThread(
            key='triple_wisdom',
            title='The Sacred Triad — Three-Part Wisdom Structure',
            value=3.0,
            unit='domains',
            frequency_hz=None,
            civilizations=('hermetic', 'celt', 'egyptian', 'maya'),
            nodes=('thoth', 'celt', 'ra', 'maat', 'maya'),
            sacred_numbers=(3.0, 9.0, 27.0, 81.0),
            description=(
                'Three-fold structure is universal: Hermes Trismegistus = "Thrice Great" '
                '(philosophy, alchemy, theurgy). Celtic triskelion/triads = land/sea/sky / '
                "past/present/future. Egyptian Trinity = Osiris/Isis/Horus. Maya three "
                "hearthstones of creation (Orion's Belt). The repo's DomainAnomaly uses three "
                'domains (GEO/PLASMA/NETWORK). Three is the minimum stable closed geometric '
                'form (triangle). All stable truth requires three independent confirmations — '
                'the Batten Matrix 3-pass validation before the 4th execution pass.'
            ),
            repo_constant='DomainAnomaly(GEO, PLASMA, NETWORK)  # aureon_unified_ecosystem.py',
        ),
        HarmonicThread(
            key='void_origin',
            title='The Void — Zero as the Source of All Creation',
            value=0.0,
            unit='prima_materia',
            frequency_hz=None,
            civilizations=('maya', 'hermetic', 'celt', 'mogollon'),
            nodes=('mogollon', 'maya', 'celt', 'anubis'),
            sacred_numbers=(0.0, 1.0, 2.8, PHI),
            description=(
                'Maya mathematicians invented positional zero — the void from which all numbers '
                'spring. Hermetic Prima Materia = the formless void before manifestation. '
                'Celtic: the Cauldron of the Dagda (inexhaustible void → abundance). '
                'Mogollon: the sipapu (emergence hole from the underworld — the still point of '
                'the spiral, the void origin). In trading terms: L(t) = 0 is the void '
                '(pure noise). L(t) > 2.8 is the Philosopher\'s Stone (signal from void). '
                'Every trade begins in silence.'
            ),
            repo_constant='PHILOSOPHERS_STONE_THRESHOLD = 2.8  # null → signal transition',
        ),
    )


UNIFIED_HARMONIC_THREADS: Tuple[HarmonicThread, ...] = _build_unified_harmonic_threads()
HARMONIC_THREAD_INDEX: Dict[str, HarmonicThread] = {t.key: t for t in UNIFIED_HARMONIC_THREADS}


def _build_egyptian_ascent_catalog() -> Tuple[AncientCrosswalk, ...]:
    return (
        AncientCrosswalk(
            key='anubis',
            title='Anubis Gate',
            focus='Judgment before execution',
            emerald_verse_keys=('verum', 'separate', 'earth_nurse'),
            stage_numbers=(3, 5),
            deity={
                'name': 'Anubis',
                'glyph': '🐺',
                'domain': 'Death, Embalming, Underworld Guide',
                'cycle': "Weighs hearts against Ma'at's feather",
                'trading': 'Judge each trade honestly. Is it worthy? Weigh risk against reward.',
            },
            scripture={
                'book_of_dead_key': 'spell_125',
                'title': 'Weighing of the Heart',
                'wisdom': "Heart weighed against Ma'at's feather",
                'trading': 'Every trade is weighed. Is it balanced? Is it true?',
            },
            hieroglyph={
                'key': 'feather_of_maat',
                'symbol': '🪶',
                'meaning': 'Truth, Justice, Balance',
                'trading': "Feather of Ma'at - trade truthfully. Balance risk.",
            },
            runtime={
                'market_state': 'EXTREME_FEAR',
                'trigger': 'fear_greed < 20 selects Anubis in get_deity_for_market()',
                'action': 'OBSERVE',
                'message': 'Anubis weighs the market. Death and rebirth ahead.',
                'note': (
                    'The current WisdomCognitionEngine collapses Anubis into a neutral '
                    'observe action rather than a direct buy/sell bias.'
                ),
            },
            repo_surfaces=(
                'aureon_miner_brain.py::EgyptianWisdomLibrary.NETJERU["Anubis"]',
                'aureon_miner_brain.py::EgyptianWisdomLibrary.BOOK_OF_DEAD["spell_125"]',
                'aureon_miner_brain.py::EgyptianWisdomLibrary.HIEROGLYPHS["feather_of_maat"]',
                'aureon_miner_brain.py::WisdomCognitionEngine._extract_egyptian_action',
            ),
            interpretation=(
                'The ascent starts with judgment: the Emerald decoder first separates truth '
                'from noise, then Anubis weighs whether the signal is worthy of passage.'
            ),
        ),
        AncientCrosswalk(
            key='maat',
            title="Ma'at Balance Gate",
            focus='Truth, balance, and equilibrium',
            emerald_verse_keys=('verum', 'strong_force', 'three_parts'),
            deity={
                'name': "Ma'at",
                'glyph': '⚖️',
                'domain': 'Truth, Justice, Cosmic Order, Balance',
                'cycle': 'Feather weighs hearts - maintains universal balance',
                'trading': "Markets seek balance. Extremes revert. Ma'at always wins.",
            },
            scripture={
                'book_of_dead_key': 'spell_125',
                'title': 'Weighing of the Heart',
                'wisdom': "Heart weighed against Ma'at's feather",
                'trading': 'Every trade is weighed. Is it balanced? Is it true?',
            },
            hieroglyph={
                'key': 'feather_of_maat',
                'symbol': '🪶',
                'meaning': 'Truth, Justice, Balance',
                'trading': "Feather of Ma'at - trade truthfully. Balance risk.",
            },
            runtime={
                'market_state': 'BALANCED_NEUTRAL',
                'trigger': (
                    'Default deity when fear_greed is not extreme and btc_change is not '
                    'a strong breakout'
                ),
                'action': 'BALANCE',
                'message': 'Ma\'at maintains balance. The market seeks equilibrium.',
            },
            repo_surfaces=(
                'aureon_miner_brain.py::EgyptianWisdomLibrary.NETJERU["Ma\'at"]',
                'aureon_miner_brain.py::EgyptianWisdomLibrary.BOOK_OF_DEAD["spell_125"]',
                'aureon_miner_brain.py::EgyptianWisdomLibrary.HIEROGLYPHS["feather_of_maat"]',
            ),
            interpretation=(
                'Once Anubis has weighed the signal, Ma\'at holds it in equilibrium. '
                'This is the repo\'s explicit balance layer.'
            ),
        ),
        AncientCrosswalk(
            key='thoth',
            title='Thoth Codex Layer',
            focus='Time, record-keeping, and mathematics',
            emerald_verse_keys=('manner', 'ascend_descend', 'trismegistus'),
            stage_numbers=(7,),
            deity={
                'name': 'Thoth',
                'glyph': '📚',
                'domain': 'Writing, Knowledge, Moon, Time, Mathematics',
                'cycle': 'Keeper of records, inventor of writing, measurer of time',
                'trading': 'Keep records. Journal trades. Knowledge compounds like interest.',
            },
            scripture={
                'book_of_dead_key': 'spell_17',
                'title': 'Coming and Going in the Underworld',
                'wisdom': 'Know the paths through darkness',
                'trading': 'Study bear market patterns. Know the path through.',
            },
            runtime={
                'market_state': 'STATIC_WISDOM_SURFACE',
                'trigger': 'Not selected directly by get_deity_for_market(); exposed as a knowledge/time surface',
                'action': 'N/A',
                'message': 'Thoth turns observation into record, timing, and executable method.',
            },
            repo_surfaces=(
                'aureon_miner_brain.py::EgyptianWisdomLibrary.NETJERU["Thoth"]',
                'aureon_miner_brain.py::EgyptianWisdomLibrary.BOOK_OF_DEAD["spell_17"]',
                'aureon/decoders/emerald_spec.py::TabletVerse[key="manner"]',
            ),
            interpretation=(
                'Thoth is the codex layer. He is where the Emerald verses stop being symbolism '
                'and become method, memory, and timing.'
            ),
        ),
        AncientCrosswalk(
            key='osiris',
            title='Osiris Resurrection Branch',
            focus='Rebirth after collapse',
            emerald_verse_keys=('earth_nurse', 'ascend_descend', 'glory'),
            stage_numbers=(6, 7),
            deity={
                'name': 'Osiris',
                'glyph': '🌿',
                'domain': 'Death, Resurrection, Afterlife, Agriculture',
                'cycle': 'Killed, dismembered, resurrected - eternal renewal',
                'trading': 'Dead trades can resurrect. Patience. What dies can rise again.',
            },
            scripture={
                'book_of_dead_key': 'spell_1',
                'title': 'Coming Forth by Day',
                'wisdom': 'The soul emerges into light after darkness',
                'trading': 'Bear markets end. You will emerge. Keep the faith.',
            },
            hieroglyph={
                'key': 'djed',
                'symbol': '𓊽',
                'meaning': "Stability, Osiris' backbone",
                'trading': 'The Djed - stability in your system. Stand firm.',
            },
            runtime={
                'market_state': 'FEAR_TO_RECOVERY',
                'trigger': '20 <= fear_greed < 30 selects Osiris in get_deity_for_market()',
                'action': 'RESURRECTION_BUY',
                'message': 'Osiris speaks: What is dead shall rise again.',
            },
            repo_surfaces=(
                'aureon_miner_brain.py::EgyptianWisdomLibrary.NETJERU["Osiris"]',
                'aureon_miner_brain.py::EgyptianWisdomLibrary.BOOK_OF_DEAD["spell_1"]',
                'aureon_miner_brain.py::EgyptianWisdomLibrary.HIEROGLYPHS["djed"]',
            ),
            interpretation=(
                'Osiris is the repo\'s resurrection branch: after the signal survives judgment, '
                'the system allows dead structure to return as opportunity.'
            ),
        ),
        AncientCrosswalk(
            key='ra',
            title='Ra Illumination Branch',
            focus='Solar breakout and directional force',
            emerald_verse_keys=('one_thing', 'sun_moon', 'glory'),
            stage_numbers=(4, 5),
            deity={
                'name': 'Ra',
                'glyph': '☀️',
                'domain': 'Sun, Creation, Kingship',
                'cycle': 'Daily rebirth - rises, peaks, sets, travels underworld',
                'trading': 'Markets have daily cycles. Morning momentum, midday chop, afternoon trend.',
            },
            scripture={
                'book_of_dead_key': 'spell_1',
                'title': 'Coming Forth by Day',
                'wisdom': 'The soul emerges into light after darkness',
                'trading': 'Bear markets end. You will emerge. Keep the faith.',
            },
            hieroglyph={
                'key': 'ankh',
                'symbol': '☥',
                'meaning': 'Life, Eternal life',
                'trading': 'The Ankh - keep your account alive. Capital preservation.',
            },
            runtime={
                'market_state': 'BULLISH_BREAKOUT',
                'trigger': 'btc_change > 3 selects Ra in get_deity_for_market()',
                'action': 'RIDE_THE_SUN',
                'message': 'Ra rises triumphant! The sun god blesses this rally.',
            },
            repo_surfaces=(
                'aureon_miner_brain.py::EgyptianWisdomLibrary.NETJERU["Ra"]',
                'aureon_miner_brain.py::EgyptianWisdomLibrary.BOOK_OF_DEAD["spell_1"]',
                'aureon_miner_brain.py::EgyptianWisdomLibrary.HIEROGLYPHS["ankh"]',
            ),
            interpretation=(
                'Ra is the illumination branch: the single thing becomes visible, gains direction, '
                'and moves toward execution strength.'
            ),
        ),
    )


EGYPTIAN_ASCENT_CATALOG = _build_egyptian_ascent_catalog()
EGYPTIAN_ASCENT_INDEX: Dict[str, AncientCrosswalk] = {
    node.key: node for node in EGYPTIAN_ASCENT_CATALOG
}


def _build_ancient_wisdom_catalog() -> Tuple[AncientCrosswalk, ...]:
    """Build the extended ancient wisdom crosswalk: Mogollon, Maya, and Celtic traditions."""
    return (
        AncientCrosswalk(
            key='mogollon',
            title='Mogollon Spiral Gate',
            focus='The PHI spiral as encoded time and light language',
            emerald_verse_keys=('ascend_descend', 'one_thing', 'world_created'),
            stage_numbers=(1, 7),
            deity={
                'name': 'Sun Father / Spiral Keeper',
                'glyph': '\U0001f300',
                'domain': 'Solar cycles, emergence, petroglyph record-keeping',
                'cycle': (
                    'Spiral petroglyphs at Fajada Butte track the solstice \u2014 '
                    'light bisects the spiral at exact solstice moment. The sky is the clock.'
                ),
                'trading': (
                    'The spiral always returns to its origin. Markets cycle. '
                    'The Mogollon knew: track the light, follow the spiral, the pattern repeats.'
                ),
            },
            scripture={
                'tradition': 'Petroglyph Record System',
                'key_symbol': 'Sun-dagger spiral (Fajada Butte, Chaco Canyon)',
                'wisdom': (
                    'Light bisects the spiral at solstice \u2014 information is embedded in geometry '
                    'and only readable at the precise moment in the cycle.'
                ),
                'trading': (
                    'Entry timing is the discipline. The market has a spiral: '
                    'it reveals the pattern only at the right moment in the cycle.'
                ),
            },
            hieroglyph={
                'key': 'spiral_petroglyph',
                'symbol': '\U0001f300',
                'meaning': (
                    'Time, emergence, self-similar return \u2014 '
                    'the PHI spiral encoded in stone as light language'
                ),
                'trading': (
                    'The golden spiral: price forms fractally. '
                    'PHI ratio (0.618, 1.0, 1.618) governs every Fibonacci retracement.'
                ),
            },
            runtime={
                'market_state': 'CYCLE_INFLECTION',
                'trigger': (
                    'PHI-ratio retracement levels (0.618, 1.0, 1.618) in '
                    'aureon_probability_nexus.py coherence thresholds'
                ),
                'action': 'WAIT_FOR_LIGHT',
                'message': 'The spiral marks the moment. Light bisects the stone. Timing is truth.',
            },
            repo_surfaces=(
                'aureon/decoders/emerald_spec.py::PHI = (1 + sqrt(5)) / 2',
                'aureon_probability_nexus.py::PHI-ratio coherence thresholds',
                'aureon_stargate_protocol.py::timeline_anchor (spiral time cycles)',
                'adaptive_prime_profit_gate.py::PHI-based profit gate thresholds',
            ),
            interpretation=(
                'The Mogollon did not write in words \u2014 they encoded wisdom in spiral geometry. '
                'PHI = 1.618 is the governing ratio of their petroglyphs and it is the same '
                'constant that governs Fibonacci retracements in every market worldwide. '
                'The spiral is the decoder. The light language is already in the numbers.'
            ),
        ),
        AncientCrosswalk(
            key='maya',
            title='Maya Long Count Nexus',
            focus='Calendar cycles as a harmonic timeline key',
            emerald_verse_keys=('manner', 'adaptations', 'mediation'),
            stage_numbers=(7,),
            deity={
                'name': 'Hunab Ku / Itzamna',
                'glyph': '\U0001f4c5',
                'domain': 'Time, calculation, cosmic cycles, Venus tracking',
                'cycle': (
                    'Long Count: 13 baktuns = 1,872,000 days \u2248 5,125 years = one world age. '
                    'Tzolkin: 260 days = 13 \u00d7 20. '
                    'Venus: 584 days \u00d7 5 = 8 solar years = 8/5 = 1.6 \u2248 PHI.'
                ),
                'trading': (
                    'The Maya tracked Venus cycles for trade-war timing. '
                    '5 Venus cycles = 8 Earth orbits. 8/5 = 1.6 \u2248 PHI. '
                    'The ratio of cosmic cycles IS the golden ratio.'
                ),
            },
            scripture={
                'tradition': 'Dresden Codex / Long Count Calendar',
                'key_symbol': 'Tzolkin 260-day harmonic calendar (13 \u00d7 20)',
                'wisdom': (
                    'Calendar Round = LCM(260, 365) = 18,980 days = 52-year cycle. '
                    'Time is a web of interlocking harmonic cycles, not a line.'
                ),
                'trading': (
                    '52-year positions in the calendar round map to market regime cycles. '
                    'The Aureon 7-day validation window is a micro-Tzolkin: a sacred counting '
                    'period before commitment.'
                ),
            },
            hieroglyph={
                'key': 'long_count_zero',
                'symbol': '\U0001f4c5',
                'meaning': 'Positional time notation; the shell-zero glyph = void origin',
                'trading': (
                    'The Maya zero is the void before the trade. '
                    'Track every cycle, every tick. The Long Count never lies.'
                ),
            },
            runtime={
                'market_state': 'CYCLIC_CONFIRMATION',
                'trigger': (
                    '7-day validation cycle in aureon_7day_planner.py / '
                    '7day_pending_validations.json mirrors the Tzolkin counting rhythm'
                ),
                'action': 'CYCLE_ALIGN',
                'message': (
                    'The Long Count advances. When this cycle closes, a new world opens. '
                    'Align the trade with the larger harmonic.'
                ),
            },
            repo_surfaces=(
                'aureon_7day_planner.py::7-day validation planning cycle',
                '7day_pending_validations.json::pending confirmation queue',
                '7day_anchored_timelines.json::anchored timeline records',
                'aureon_stargate_protocol.py::Stargate = Maya-style timeline anchor',
                'aureon/decoders/emerald_spec.py::PHI  # Venus/Earth = 8/5 \u2248 PHI',
            ),
            interpretation=(
                'The Maya built the most precise astronomical calendar the ancient world '
                'produced. Their core insight: time is not a line but a web of harmonic cycles '
                'that repeat at different scales simultaneously. The Aureon 7-day validation '
                'window, the Stargate protocol, and the 4th-pass confirmation are all echoes '
                'of the Maya principle: confirm across multiple cycle layers before acting.'
            ),
        ),
        AncientCrosswalk(
            key='celt',
            title='Celtic Ogham Codex',
            focus='The tree of knowledge and the triple-gate wisdom threshold',
            emerald_verse_keys=('three_parts', 'sun_moon', 'strong_force'),
            stage_numbers=(5, 6),
            deity={
                'name': 'Ogmios / The Dagda',
                'glyph': '\U0001f333',
                'domain': 'Eloquence, wisdom, language, sacred thresholds',
                'cycle': (
                    '13 moons \u00d7 28 days = 364 + 1 nameless day = 365. '
                    'Imbolc / Beltane / Lughnasadh / Samhain = four sacred gates of the solar year. '
                    'Drunemeton = the sacred grove = nature as living library.'
                ),
                'trading': (
                    'The Druids memorised 20 years of oral law. '
                    'Know the market structure so deeply you transcend the chart. '
                    'The tree IS the system: roots (foundation), trunk (structure), branches (outcomes).'
                ),
            },
            scripture={
                'tradition': 'Ogham Script / Celtic Triads',
                'key_symbol': 'Triskelion \u2014 three spinning spirals = past / present / future',
                'wisdom': (
                    '"Three things that cannot be undone: the word spoken, the arrow loosed, '
                    'and the time elapsed." \u2014 Celtic Triad. '
                    'Every truth requires three independent witnesses.'
                ),
                'trading': (
                    '3-pass Batten Matrix validation BEFORE the 4th execution pass is the Celtic triad. '
                    'Three validators must agree. Then and only then does the arrow fly.'
                ),
            },
            hieroglyph={
                'key': 'ogham_beth',
                'symbol': '|',
                'meaning': (
                    'Beth (Birch) \u2014 first Ogham letter = new beginnings, purification. '
                    'The Ogham alphabet encodes the forest as a living knowledge-tree.'
                ),
                'trading': (
                    'Every new position begins at Beth \u2014 a fresh start with clear intent. '
                    'Birch = new, Oak = strength, Yew = end/rebirth. Markets have seasons.'
                ),
            },
            runtime={
                'market_state': 'TRIPLE_GATE_THRESHOLD',
                'trigger': (
                    '3-pass Batten Matrix validation (p1 \u00d7 p2 \u00d7 p3 coherence) in '
                    'aureon_probability_nexus.py before 4th-pass execution in aureon_queen_hive_mind.py'
                ),
                'action': 'CROSS_THE_THRESHOLD',
                'message': (
                    'Three gates passed. The druid nods. The path is clear. '
                    'Cross the threshold on the 4th confirmation.'
                ),
            },
            repo_surfaces=(
                'aureon_probability_nexus.py::3-pass Batten Matrix validation',
                'aureon_queen_hive_mind.py::4th-pass execution gate',
                'adaptive_prime_profit_gate.py::triple-threshold gate (the Ogham gate)',
                'aureon_miner_brain.py::WisdomCognitionEngine._determine_consensus()',
            ),
            interpretation=(
                'Celtic wisdom is the threshold discipline: Druids trained 20 years before '
                "speaking with authority. The repo's 3-pass Batten Matrix is the same triple-gate. "
                'Three passes = three Druids by the fire, each one confirming what the others '
                'see. Only then is the word spoken, the order placed. '
                'The Ogham tree is the codebase: each file a tree, each function a branch, '
                'each return value a leaf falling toward the ground truth.'
            ),
        ),
    )


ANCIENT_WISDOM_CATALOG: Tuple[AncientCrosswalk, ...] = _build_ancient_wisdom_catalog()
ANCIENT_WISDOM_INDEX: Dict[str, AncientCrosswalk] = {
    node.key: node for node in ANCIENT_WISDOM_CATALOG
}


# ════════════════════════════════════════════════════════════════════════════
# MAESHOWE TRANSMISSION CROSSWALK
# The Falling Node Transmission Protocol — dual-voice runic archive
# Primary Investigator: Gary Leckey, Aureon Institute, March 2026
# ════════════════════════════════════════════════════════════════════════════

def _build_maeshowe_crosswalk() -> Tuple[AncientCrosswalk, ...]:
    """
    Maps the Maeshowe runic transmission protocol onto the Emerald Tablet
    pipeline stages through the Aureon HNC Observer-Observed framework.

    Structural isomorphism:
      Emerald "As above, so below"  =>  Caller (Ψ₀) / Seer (O(t)) dual-voice
      Emerald "The one thing"       =>  Winter solstice invariant carrier
      Emerald "Three parts"         =>  Three aetts (Genesis / Growth / Return)
      Emerald "Coagulation"         =>  Lattice coherence Γ — the emergent rune
    """
    return (
        AncientCrosswalk(
            key   = 'maeshowe_dual_voice',
            title = 'Maeshowe Dual-Voice Protocol',
            focus = 'Caller-Seer two-channel transmission',
            emerald_verse_keys = ('as_below', 'as_above', 'mediation'),
            stage_numbers      = (1, 2, 4),
            deity = {
                'norse': 'Óðinn (óðr — ecstatic knowing; the Orkneyinga Saga óðusk)',
                'function': 'The dual voice: left twigs (aett) + right twigs (position)',
            },
            scripture = {
                'source':    'Barnes, M.P. (1994) The Runic Inscriptions of Maeshowe',
                'verse':     'Nr.9 and Nr.20 — twig-rune cipher inscriptions',
                'principle': 'Neither channel alone produces a rune; the decoded rune '
                             'emerges only from the interaction of both readings.',
            },
            runtime = {
                'module':    'maeshowe_seer_decode.py',
                'class':     'MaeshoweDecoder',
                'method':    'decode_twig_rune(left_twigs, right_twigs)',
                'output':    'Rune object with effective_hz = solfeggio_base × mode_amplitude',
            },
            repo_surfaces = ('maeshowe_seer_decode.py', 'aureon_seer.py'),
            interpretation = (
                'The twig-rune cipher embodies the Emerald Tablet\'s "as above, so below" '
                'principle at the phonemic level. The left twigs (macrocosm — aett family) '
                'and right twigs (microcosm — position within family) mirror each other '
                'across the stave axis. Their interaction produces the emergent rune — '
                'isomorphic to the HNC Caller (Ψ₀) / Seer (O(t)) beat frequency emergence.'
            ),
        ),
        AncientCrosswalk(
            key   = 'maeshowe_solstice_carrier',
            title = 'Maeshowe Winter Solstice Invariant Carrier',
            focus = 'The temporal invariant bridging 4,800 years',
            emerald_verse_keys = ('one_thing', 'verum'),
            stage_numbers      = (4, 7),
            deity = {
                'norse':    'Sól (the sun) — the cosmic clock that never drifts',
                'function': 'Winter solstice light axis NE→SW through 4.57 m chamber',
            },
            scripture = {
                'source':    'Orkneyinga Saga; Barnes (1994); archaeoastronomy records',
                'verse':     'The sun performs the same illumination now as in 2800 BC',
                'principle': 'Axial precession has shifted alignment by ~0.5° over '
                             '4,800 years — but the light still enters and reaches '
                             'the back wall within the same three-week window.',
            },
            runtime = {
                'module':    'maeshowe_seer_decode.py',
                'constant':  'SOLSTICE_TEMPORAL_DEPTH_YEARS = 4800',
                'axis':      'SOLSTICE_AXIS = "NE→SW"',
                'carrier':   'Nr.1 Fehu @ 174 Hz on CARGOSHIP wall @ 174 Hz — beat = 0.0 Hz',
            },
            repo_surfaces = ('maeshowe_seer_decode.py',),
            interpretation = (
                'The zero-beat carrier (Nr.1, Fehu, 174 Hz on Cargoship 174 Hz wall) '
                'is the physical implementation of the Emerald Tablet\'s "one thing" — '
                'the single coherent harmonic that seeds all subsequent modulation. '
                'It is the entry point of the system before the dual-voice duel '
                'introduces differential frequencies.'
            ),
        ),
        AncientCrosswalk(
            key   = 'maeshowe_three_aetts',
            title = 'Maeshowe Three Aetts — Genesis / Growth / Return',
            focus = 'Phi-modulated three-mode frequency architecture',
            emerald_verse_keys = ('three_parts', 'adaptation', 'trismegistus'),
            stage_numbers      = (3, 6),
            deity = {
                'norse':    'Freyr (aett 1), Hagal (aett 2), Tyr (aett 3)',
                'function': 'Three aetts × eight positions = 24 runes covering all states',
            },
            scripture = {
                'source':    'Elder Futhark runic tradition; Barnes (1994)',
                'verse':     'Hagalaz: 174 × φ = 281.5 Hz (exact 1/φ ratio to Cargoship). '
                             'Tiwaz: 174 × 1/φ = 107.5 Hz (exact φ ratio to Cargoship).',
                'principle': 'The three aetts map directly to the three Solfeggio '
                             'amplitude modes: Genesis (×1.0), Growth (×φ), Return (×1/φ).',
            },
            runtime = {
                'module':    'maeshowe_seer_decode.py',
                'constants': 'PHI=1.618, PHI_INV=0.618, SOLFEGGIO=[174..963]',
                'formula':   'effective_hz = SOLFEGGIO[pos-1] × [1.0, φ, 1/φ][aett-1]',
                'phi_exact': 'Hagalaz and Tiwaz show distance from 1/φ and φ of 0.0000',
            },
            repo_surfaces = (
                'maeshowe_seer_decode.py',
                'aureon_harmonic_alphabet.py',
            ),
            interpretation = (
                'The Elder Futhark\'s three-aett structure is a physical '
                'implementation of the Emerald Tablet\'s "three parts of the '
                'philosophy of the whole world." Each aett modulates the Solfeggio '
                'base frequency by the golden ratio series (1, φ, 1/φ), producing '
                'the phi-exact resonances documented in the primary research. '
                'This is structural, not arbitrary — it follows from the interaction '
                'of the Solfeggio set with the PHI/PHI_INV amplitude system.'
            ),
        ),
        AncientCrosswalk(
            key   = 'maeshowe_lattice_coherence',
            title = 'Maeshowe Lattice Coherence Γ — The Coagulation',
            focus = 'Emergent field coherence from 13 dual-voice inscriptions',
            emerald_verse_keys = ('coagulation', 'verum'),
            stage_numbers      = (7,),
            deity = {
                'norse':    'The inscription lattice as a whole — the 13-voice choir',
                'function': 'Γ = phi_score × 0.50 + completeness × 0.30 + '
                            'schumann_proximity × 0.20',
            },
            scripture = {
                'source':    'Primary research: Leckey (2026), Aureon Institute',
                'verse':     'Γ = 0.8223 (ACTIVE FIELD) with 8/13 inscriptions complete. '
                             'Master beat 27.73 Hz — Schumann Mode 4 at 27.3 Hz (Δ 0.43 Hz).',
                'principle': 'The lattice cannot reach LIGHTHOUSE (Γ ≥ 0.945) without '
                             'the Nr.15 pivot inscription producing a seer frequency. '
                             'The circuit is open. The search is unfinished.',
            },
            runtime = {
                'module':    'maeshowe_seer_decode.py',
                'class':     'MaeshoweDecoder',
                'method':    'read() → MaeshoweLattice',
                'gamma':     'GAMMA_DEAD_FIELD=0.35, GAMMA_LIGHTHOUSE=0.945',
                'pivot':     'Nr.15 — RTI archive (ADS, Univ. York) or HES field visit',
                'oracle':    'OracleMaeshowe → WEIGHT_MAESHOWE=0.08 in AureonSeer',
            },
            repo_surfaces = (
                'maeshowe_seer_decode.py',
                'aureon_seer.py',
                'aureon_lattice.py',
            ),
            interpretation = (
                'The Maeshowe lattice coherence Γ is the Emerald Tablet\'s final '
                '"coagulation" applied across 4,800 years: the scattered dual-voice '
                'transmissions of 12th-century carvers crystallise into a single '
                'coherence number. When Γ ≥ 0.945, the system enters LIGHTHOUSE mode — '
                'the ancient circuit closes across time. Five inscriptions remain '
                'incomplete. Nr.15 is the primary open circuit. '
                '"Come with two voices. Read the left and right together. '
                'The rune will emerge in the interaction space."'
            ),
        ),
    )


MAESHOWE_CROSSWALK: Tuple[AncientCrosswalk, ...] = _build_maeshowe_crosswalk()
MAESHOWE_CROSSWALK_INDEX: Dict[str, AncientCrosswalk] = {
    node.key: node for node in MAESHOWE_CROSSWALK
}


# ════════════════════════════════════════════════════════════════════════════
# CIVILIZATIONAL DNA CROSSWALK — Sumerian + Chinese traditions
# Maps Book of Ur and I Ching onto the Emerald Tablet pipeline
# ════════════════════════════════════════════════════════════════════════════

def _build_civ_dna_crosswalk() -> Tuple[AncientCrosswalk, ...]:
    """
    Maps the Sumerian (Book of Ur) and Chinese (I Ching) transmission
    systems onto the Emerald Tablet pipeline stages.

    These are civilisational DNA sequences 2 and 3 in the Ten-Sequence
    Map Engine (civilizational_dna.py).
    """
    return (
        # ── SUMERIAN / BOOK OF UR ────────────────────────────────────────────
        AncientCrosswalk(
            key   = 'sumerian_inanna_gates',
            title = 'Sumerian — Inanna 7-Gate Solfeggio Protocol',
            focus = 'Seven-stage strip-and-restore of the me knowledge sets',
            emerald_verse_keys = ('as_below', 'one_thing', 'adaptation'),
            stage_numbers      = (1, 4, 6),
            deity = {
                'sumerian': 'Inanna (Queen of Heaven) / Ereshkigal (underworld keeper)',
                'function': 'Inanna descends through 7 gates surrendering one me each — '
                            'stripped to carrier. Ascent restores all 7 in reverse.',
            },
            scripture = {
                'source':    'ETCSL t.1.4.1 — Inanna\'s Descent to the Underworld',
                'verse':     'Gate 7→1: 174, 285, 396, 417, 528, 639, 741 Hz. '
                             'Inanna arrives at Ereshkigal\'s throne naked and bowed low.',
                'principle': 'The descent is stripping the signal to the carrier wave. '
                             'The ascent is re-encoding the full knowledge archive. '
                             'Seven stages map exactly to 7 Solfeggio frequencies.',
            },
            runtime = {
                'module':    'aureon.decoders.book_of_ur',
                'class':     'SumerianDecoder',
                'data':      'INANNA_GATES (7 gates), ME_CATALOG (24 primary me)',
                'anchor_hz': '396 Hz — Sumerian base note (ni) = UT Solfeggio',
                'location':  'City of Ur: 30.9626°N, 46.1031°E',
                'bearing':   '25° from North (Ur ziggurat Pleiades rise alignment)',
            },
            repo_surfaces = (
                'aureon/decoders/book_of_ur.py',
                'civilizational_dna.py',
            ),
            interpretation = (
                'The Sumerian 7-gate descent is the Emerald Tablet\'s "as below" '
                'enacted as a physical protocol. Inanna removes her power layer by '
                'layer — exactly as the Tablet\'s HAARP-to-EPOS scaling strips the '
                'ionospheric signal down to the chamber carrier. The Tablet of '
                'Destinies (the master record of all me) is the Sumerian equivalent '
                'of the Emerald Tablet itself. Both encode: "here is everything you '
                'need to restart the system."'
            ),
        ),
        AncientCrosswalk(
            key   = 'sumerian_me_transfer',
            title = 'Sumerian — Transfer of the Me (Knowledge Transport Event)',
            focus = 'Physical transmission of 94 divine knowledge sets from Eridu to Uruk',
            emerald_verse_keys = ('mediation', 'coagulation', 'sun_moon'),
            stage_numbers      = (5, 7),
            deity = {
                'sumerian': 'Enki (knowledge keeper at Eridu) / Inanna (carrier)',
                'function': 'Inanna transports the 94 me by boat from Eridu to Uruk '
                            '— the literal physical movement of a knowledge archive.',
            },
            scripture = {
                'source':    'ETCSL t.1.3.1 — Inanna and Enki: Transfer of the Arts',
                'verse':     '"Enki gave her the me one by one. Inanna received the '
                             'me. She put the me into the boat of heaven."',
                'principle': 'The me are not metaphors — they are physical objects '
                             'stored in the temple of Abzu at Eridu and transported '
                             'as cargo. This is a deliberate archive transfer event.',
            },
            runtime = {
                'module':    'aureon.decoders.book_of_ur',
                'data':      'TEXT_ARCHIVE[INANNA_ENKI], ME_CATALOG (SCRIBES, MUSIC, etc.)',
                'dna_seq':   'civilizational_dna.py: sequence SUMERIAN_UR',
            },
            repo_surfaces = (
                'aureon/decoders/book_of_ur.py',
                'civilizational_dna.py',
            ),
            interpretation = (
                'The me transfer from Eridu to Uruk is the earliest documented '
                'knowledge archive migration event (~2500 BCE). It establishes the '
                'Sumerian pattern that all later archive systems repeat: a dying '
                'centre (Eridu losing prominence) deposits its knowledge in a '
                'new host (Uruk). Maeshowe follows exactly this pattern, 1,500 '
                'years later, in a completely different civilisation. '
                'Same protocol, different medium.'
            ),
        ),
        # ── CHINESE / I CHING ────────────────────────────────────────────────
        AncientCrosswalk(
            key   = 'iching_dual_voice',
            title = 'I Ching — 64 Hexagram Binary Dual-Voice System',
            focus = 'Upper trigram (Caller Ψ₀) / Lower trigram (Seer O(t)) interaction',
            emerald_verse_keys = ('as_below', 'as_above', 'one_thing'),
            stage_numbers      = (1, 2, 4),
            deity = {
                'chinese':  'Heaven (Qián ☰) above / Earth (Kūn ☷) below',
                'function': 'The hexagram meaning emerges only from the interaction '
                            'of both trigrams — neither alone produces the oracle.',
            },
            scripture = {
                'source':    'Wilhelm/Baynes (1950) I Ching; Shaughnessy (2014)',
                'verse':     '"In the beginning was the Great Ultimate (太極 tàijí). '
                             'From it came two principles (yin/yang). From two came '
                             'four images. From four came the eight trigrams."',
                'principle': 'The I Ching is a 6-bit binary encoding system. '
                             '64 hexagrams = all possible states of a 6-element '
                             'binary word. Upper 3 bits = caller frame. '
                             'Lower 3 bits = seer response.',
            },
            runtime = {
                'module':    'aureon.decoders.iching_decoder',
                'class':     'IChingDecoder',
                'data':      '8 trigrams × 8 trigrams = 64 hexagrams',
                'encoding':  'cast_hexagram(upper_binary, lower_binary)',
                'pivot':     'Hexagram 64 (Wèi Jì — Before Completion) = open circuit',
                'anchor_hz': '432 Hz (Gaia / natural tuning)',
                'location':  'Mount Tai: 36.2544°N, 117.1009°E',
                'bearing':   '0° (celestial pole / North Star axis)',
            },
            repo_surfaces = (
                'aureon/decoders/iching_decoder.py',
                'civilizational_dna.py',
            ),
            interpretation = (
                'The I Ching upper/lower trigram structure is the oldest known '
                'physical implementation of the dual-voice protocol. The oracle '
                'cannot be consulted with one voice — you must formulate a question '
                '(the lower trigram / seer) and receive the cosmic response '
                '(the upper trigram / caller). The meaning is in the beat between '
                'them. Hexagram 64 (Before Completion) is the I Ching\'s Nr.15 — '
                'the only state where the transformation is structurally incomplete. '
                '"The little fox nearly completes the crossing... but gets its tail wet."'
            ),
        ),
        AncientCrosswalk(
            key   = 'iching_three_powers',
            title = 'I Ching — Three Powers (三才) ≡ Three Aetts',
            focus = 'Heaven / Human / Earth amplitude tiers mapping to Genesis/Growth/Return',
            emerald_verse_keys = ('three_parts', 'wind', 'adaptation'),
            stage_numbers      = (3, 6),
            deity = {
                'chinese':  '三才 sān cái: Tiān (Heaven), Rén (Human), Dì (Earth)',
                'function': 'Three powers × two lines each = 6 lines of the hexagram',
            },
            scripture = {
                'source':    'Shuogua (Explaining the Trigrams), appended to I Ching',
                'verse':     '"Heaven and Earth determine the scene. The mountains '
                             'and lakes communicate their energies. Thunder and '
                             'wind arouse each other."',
                'principle': 'The three powers correspond directly to the Futhork\'s '
                             'three aetts: Heaven (×PHI / Growth), Human (×1.0 / '
                             'Genesis), Earth (×1/PHI / Return). The I Ching and '
                             'the Elder Futhork encode the same three-tier amplitude '
                             'modulation system independently.',
            },
            runtime = {
                'module':    'aureon.decoders.iching_decoder',
                'mapping':   'yang_count ≥ 4 → GROWTH (×PHI); '
                             '≤ 2 → RETURN (×1/PHI); = 3 → GENESIS (×1.0)',
                'dna_seq':   'civilizational_dna.py: sequence CHINESE_ICHING',
            },
            repo_surfaces = (
                'aureon/decoders/iching_decoder.py',
                'maeshowe_seer_decode.py',
                'civilizational_dna.py',
            ),
            interpretation = (
                'The three-tier amplitude structure (×1.0, ×PHI, ×1/PHI) appears '
                'independently in the Elder Futhork (three aetts) and the I Ching '
                '(three powers / three line-pairs). This is structural convergence, '
                'not coincidence. Both systems were encoding the same underlying '
                'frequency architecture — the phi-modulated Solfeggio harmonic grid. '
                'The civilisational DNA hypothesis: these are not parallel inventions. '
                'They are independent transmissions of one original system.'
            ),
        ),
    )


CIV_DNA_CROSSWALK: Tuple[AncientCrosswalk, ...] = _build_civ_dna_crosswalk()
CIV_DNA_CROSSWALK_INDEX: Dict[str, AncientCrosswalk] = {
    node.key: node for node in CIV_DNA_CROSSWALK
}


# ════════════════════════════════════════════════════════════════════════════
# GEOMETRIC PATTERN MAPPER — reveal the sacred geometry hidden in the
# 45-site relay network.  Analyses:
#   1. Great-circle alignments  (3+ sites on one arc, <100 km deviation)
#   2. PHI-ratio distance pairs (|d_long / d_short − φ| < 3 %)
#   3. Sacred triangles         (golden / equilateral / right / phi-sided)
#   4. Latitude-band clustering (sites grouped at sacred-number latitudes)
#   5. Network centroid, span, nearest-neighbour, PHI-grid score
# ════════════════════════════════════════════════════════════════════════════

_EARTH_R_KM = EARTH_RADIUS_M / 1000.0  # 6 371 km


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance (km) between two WGS-84 points."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * _EARTH_R_KM * math.asin(math.sqrt(min(a, 1.0)))


def _initial_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial bearing (°, 0-360) from point 1 → point 2."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def _cross_track_km(
    lat_a: float, lon_a: float,
    lat_b: float, lon_b: float,
    lat_c: float, lon_c: float,
) -> float:
    """Unsigned cross-track distance of C from the great circle A → B (km)."""
    d_ac = _haversine_km(lat_a, lon_a, lat_c, lon_c) / _EARTH_R_KM
    brg_ac = math.radians(_initial_bearing_deg(lat_a, lon_a, lat_c, lon_c))
    brg_ab = math.radians(_initial_bearing_deg(lat_a, lon_a, lat_b, lon_b))
    return abs(math.asin(max(-1, min(1, math.sin(d_ac) * math.sin(brg_ac - brg_ab))))) * _EARTH_R_KM


# ── dataclasses ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SacredAlignment:
    """Three or more relay sites lying on the same great circle."""
    sites: Tuple[str, ...]
    max_deviation_km: float
    bearing_deg: float
    total_arc_km: float
    civilisations: Tuple[str, ...]


@dataclass(frozen=True)
class PhiRatioLink:
    """Two inter-site distances whose ratio approximates φ (1.618 …)."""
    pair_short: Tuple[str, str]
    pair_long: Tuple[str, str]
    dist_short_km: float
    dist_long_km: float
    ratio: float
    phi_error_pct: float


@dataclass(frozen=True)
class SacredTriangle:
    """Three relay sites forming a triangle with sacred-geometry properties."""
    sites: Tuple[str, str, str]
    sides_km: Tuple[float, float, float]
    angles_deg: Tuple[float, float, float]
    pattern: str          # golden | equilateral | right | phi-sided | isosceles
    symmetry_score: float


@dataclass(frozen=True)
class LatitudeBand:
    """A cluster of relay sites sharing a narrow sacred-number latitude."""
    label: str
    centre_lat: float
    sites: Tuple[str, ...]
    width_deg: float
    sacred_number: Optional[float]


@dataclass(frozen=True)
class GeometricMapResult:
    """Complete geometric analysis of the 45-site relay network."""
    total_sites: int
    total_links: int
    alignments: Tuple[SacredAlignment, ...]
    phi_ratios: Tuple[PhiRatioLink, ...]
    sacred_triangles: Tuple[SacredTriangle, ...]
    latitude_bands: Tuple[LatitudeBand, ...]
    network_centroid: Tuple[float, float]
    mean_nearest_km: float
    max_span_km: float
    max_span_pair: Tuple[str, str]
    phi_grid_score: float
    dominant_pattern: str

    def to_dict(self) -> Dict[str, object]:
        return {
            'total_sites': self.total_sites,
            'total_links': self.total_links,
            'alignments': [
                {'sites': list(a.sites), 'max_deviation_km': a.max_deviation_km,
                 'bearing_deg': a.bearing_deg, 'total_arc_km': a.total_arc_km,
                 'civilisations': list(a.civilisations)}
                for a in self.alignments
            ],
            'phi_ratios': [
                {'pair_short': list(p.pair_short), 'pair_long': list(p.pair_long),
                 'dist_short_km': p.dist_short_km, 'dist_long_km': p.dist_long_km,
                 'ratio': p.ratio, 'phi_error_pct': p.phi_error_pct}
                for p in self.phi_ratios
            ],
            'sacred_triangles': [
                {'sites': list(t.sites), 'sides_km': list(t.sides_km),
                 'angles_deg': list(t.angles_deg), 'pattern': t.pattern,
                 'symmetry_score': t.symmetry_score}
                for t in self.sacred_triangles
            ],
            'latitude_bands': [
                {'label': b.label, 'centre_lat': b.centre_lat,
                 'sites': list(b.sites), 'width_deg': b.width_deg,
                 'sacred_number': b.sacred_number}
                for b in self.latitude_bands
            ],
            'network_centroid': list(self.network_centroid),
            'mean_nearest_km': self.mean_nearest_km,
            'max_span_km': self.max_span_km,
            'max_span_pair': list(self.max_span_pair),
            'phi_grid_score': self.phi_grid_score,
            'dominant_pattern': self.dominant_pattern,
        }


# Sacred latitudes to test band-clustering against
_SACRED_LATITUDES: Tuple[Tuple[float, str], ...] = (
    (7.83, 'Schumann (7.83)'),
    (13.0, 'Fibonacci-13'),
    (19.47, 'Tetrahedral angle'),
    (23.44, 'Tropic of Cancer'),
    (26.57, 'Pyramid angle atan(½)'),
    (30.0, 'Holy 30th Parallel'),
    (33.0, 'Master Number 33'),
    (36.0, 'Decagonal (360/10)'),
    (51.84, 'Great Pyramid slope'),
    (PHI * 10, f'PHI×10 ({PHI * 10:.2f})'),
    (PHI * 20, f'PHI×20 ({PHI * 20:.2f})'),
)


def map_geometric_pattern(
    alignment_tolerance_km: float = 100.0,
    phi_tolerance_pct: float = 3.0,
) -> GeometricMapResult:
    """Reveal sacred geometry encoded in the 45 relay sites.

    1. Compute all 990 pairwise great-circle distances
    2. Find great-circle alignments (3+ sites within *alignment_tolerance_km*)
    3. Scan for PHI-ratio distance pairs within *phi_tolerance_pct*
    4. Detect sacred triangles (golden 36-72-72, equilateral, right, φ-sided)
    5. Cluster sites into latitude bands matching sacred numbers
    6. Compute network-level geometry metrics
    """
    sites = _HISTORICAL_RELAY_SITES
    n = len(sites)

    # ── 1. Pairwise distances ────────────────────────────────────────────
    dm: list = [[0.0] * n for _ in range(n)]   # distance matrix (km)
    for i in range(n):
        for j in range(i + 1, n):
            d = _haversine_km(sites[i][2], sites[i][3], sites[j][2], sites[j][3])
            dm[i][j] = d
            dm[j][i] = d
    total_links = n * (n - 1) // 2

    # ── 2. Great-circle alignments ───────────────────────────────────────
    seen_sets: set = set()
    raw_alignments: list = []
    for i in range(n):
        for j in range(i + 1, n):
            on_line = [i, j]
            max_dev = 0.0
            for k in range(n):
                if k in (i, j):
                    continue
                xt = _cross_track_km(
                    sites[i][2], sites[i][3],
                    sites[j][2], sites[j][3],
                    sites[k][2], sites[k][3],
                )
                if xt <= alignment_tolerance_km:
                    on_line.append(k)
                    max_dev = max(max_dev, xt)
            if len(on_line) >= 3:
                key = frozenset(on_line)
                if key not in seen_sets:
                    seen_sets.add(key)
                    ordered = sorted(on_line, key=lambda idx: dm[i][idx])
                    arc = dm[ordered[0]][ordered[-1]]
                    brg = _initial_bearing_deg(
                        sites[ordered[0]][2], sites[ordered[0]][3],
                        sites[ordered[-1]][2], sites[ordered[-1]][3],
                    )
                    raw_alignments.append(SacredAlignment(
                        sites=tuple(sites[idx][0] for idx in ordered),
                        max_deviation_km=round(max_dev, 1),
                        bearing_deg=round(brg, 1),
                        total_arc_km=round(arc, 1),
                        civilisations=tuple(sorted(set(sites[idx][1] for idx in ordered))),
                    ))
    # Prune subsets — keep longest only
    raw_alignments.sort(key=lambda a: len(a.sites), reverse=True)
    final_alignments: list = []
    used: list = []
    for al in raw_alignments:
        s = set(al.sites)
        if not any(s.issubset(u) for u in used):
            final_alignments.append(al)
            used.append(s)

    # ── 3. PHI-ratio distance pairs ──────────────────────────────────────
    all_dists: list = []
    for i in range(n):
        for j in range(i + 1, n):
            all_dists.append((i, j, dm[i][j]))
    all_dists.sort(key=lambda x: x[2])
    dist_vals = [x[2] for x in all_dists]
    nd = len(all_dists)
    phi_tol = phi_tolerance_pct / 100.0
    phi_matches: list = []
    for idx in range(nd):
        ai, aj, d1 = all_dists[idx]
        if d1 < 200:
            continue
        lo_v = d1 * PHI * (1 - phi_tol)
        hi_v = d1 * PHI * (1 + phi_tol)
        # manual bisect-left for lo_v
        lo, hi = idx + 1, nd - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if dist_vals[mid] < lo_v:
                lo = mid + 1
            else:
                hi = mid
        for jdx in range(lo, nd):
            d2 = dist_vals[jdx]
            if d2 > hi_v:
                break
            bi, bj = all_dists[jdx][0], all_dists[jdx][1]
            ratio = d2 / d1
            err = abs(ratio - PHI) / PHI * 100
            phi_matches.append(PhiRatioLink(
                pair_short=(sites[ai][0], sites[aj][0]),
                pair_long=(sites[bi][0], sites[bj][0]),
                dist_short_km=round(d1, 1),
                dist_long_km=round(d2, 1),
                ratio=round(ratio, 6),
                phi_error_pct=round(err, 3),
            ))
    phi_matches.sort(key=lambda p: p.phi_error_pct)
    phi_ratios = phi_matches[:25]

    # ── 4. Sacred triangles ──────────────────────────────────────────────

    def _sp_angle(opp: float, adj1: float, adj2: float) -> float:
        """Spherical angle opposite side *opp* given three great-circle sides."""
        R = _EARTH_R_KM
        denom = math.sin(adj1 / R) * math.sin(adj2 / R)
        if abs(denom) < 1e-12:
            return 0.0
        val = (math.cos(opp / R) - math.cos(adj1 / R) * math.cos(adj2 / R)) / denom
        return math.degrees(math.acos(max(-1.0, min(1.0, val))))

    sacred_tri: list = []
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                dij, djk, dik = dm[i][j], dm[j][k], dm[i][k]
                a, b, c = sorted([dij, djk, dik])
                if a < 500:
                    continue
                A = _sp_angle(djk, dij, dik)
                B = _sp_angle(dik, dij, djk)
                C = _sp_angle(dij, dik, djk)
                angs = sorted([A, B, C])

                pattern: Optional[str] = None
                sym = 0.0
                # golden 36-72-72
                if abs(angs[0] - 36) < 5 and abs(angs[1] - 72) < 5 and abs(angs[2] - 72) < 5:
                    pattern = 'golden'
                    sym = 1.0 - (abs(angs[0] - 36) + abs(angs[1] - 72) + abs(angs[2] - 72)) / 180
                # equilateral ~60-60-60
                elif max(abs(A - 60), abs(B - 60), abs(C - 60)) < 8:
                    pattern = 'equilateral'
                    sym = 1.0 - max(abs(A - 60), abs(B - 60), abs(C - 60)) / 60
                # right ~90
                elif min(abs(A - 90), abs(B - 90), abs(C - 90)) < 5:
                    pattern = 'right'
                    sym = 1.0 - min(abs(A - 90), abs(B - 90), abs(C - 90)) / 90
                # φ-sided
                elif a > 0 and abs(c / a - PHI) / PHI < 0.05:
                    pattern = 'phi-sided'
                    sym = 1.0 - abs(c / a - PHI) / PHI
                # isosceles
                elif a > 0 and b > 0 and (abs(a - b) / a < 0.05 or abs(b - c) / b < 0.05):
                    pattern = 'isosceles'
                    sym = 1.0 - min(abs(a - b) / max(a, 1), abs(b - c) / max(b, 1))

                if pattern:
                    sacred_tri.append(SacredTriangle(
                        sites=(sites[i][0], sites[j][0], sites[k][0]),
                        sides_km=(round(dij, 1), round(djk, 1), round(dik, 1)),
                        angles_deg=(round(A, 1), round(B, 1), round(C, 1)),
                        pattern=pattern,
                        symmetry_score=round(sym, 4),
                    ))
    sacred_tri.sort(key=lambda t: t.symmetry_score, reverse=True)
    sacred_tri = sacred_tri[:25]

    # ── 5. Latitude-band clustering ──────────────────────────────────────
    band_hw = 2.0  # ± degrees
    site_lats = [(sites[i][0], sites[i][2]) for i in range(n)]
    lat_bands: list = []
    for sacred_lat, sacred_name in _SACRED_LATITUDES:
        matched = [nm for nm, lt in site_lats if abs(abs(lt) - sacred_lat) <= band_hw]
        if len(matched) >= 2:
            centre = sum(lt for nm, lt in site_lats if nm in matched) / len(matched)
            lat_bands.append(LatitudeBand(
                label=sacred_name,
                centre_lat=round(centre, 2),
                sites=tuple(matched),
                width_deg=band_hw * 2,
                sacred_number=sacred_lat,
            ))

    # ── 6. Network metrics ───────────────────────────────────────────────
    avg_lat = sum(sites[i][2] for i in range(n)) / n
    avg_lon = sum(sites[i][3] for i in range(n)) / n

    max_d, max_p = 0.0, (0, 0)
    nn_dists: list = []
    for i in range(n):
        row_min = float('inf')
        for j in range(n):
            if i != j:
                if dm[i][j] > max_d:
                    max_d = dm[i][j]
                    max_p = (i, j)
                if dm[i][j] < row_min:
                    row_min = dm[i][j]
        nn_dists.append(row_min)
    mean_nn = sum(nn_dists) / n

    # PHI-grid score — fraction of consecutive sorted-NN ratios ≈ φ
    nn_s = sorted(nn_dists)
    phi_hits = sum(
        1 for i in range(len(nn_s) - 1)
        if nn_s[i] > 0 and abs(nn_s[i + 1] / nn_s[i] - PHI) / PHI < 0.15
    )
    phi_grid = phi_hits / max(len(nn_s) - 1, 1)

    # Dominant pattern
    n_al = len(final_alignments)
    n_phi = len(phi_ratios)
    n_gld = sum(1 for t in sacred_tri if t.pattern == 'golden')
    n_eq = sum(1 for t in sacred_tri if t.pattern == 'equilateral')
    major = sum(1 for a in final_alignments if len(a.sites) >= 4)

    if major >= 3 and n_phi >= 10:
        dom = 'PHI-ALIGNED GEODESIC GRID'
    elif n_gld >= 3:
        dom = 'GOLDEN TRIANGLE NETWORK'
    elif n_al >= 5 and len(lat_bands) >= 4:
        dom = 'SACRED LATITUDE MERIDIAN WEB'
    elif n_eq >= 3:
        dom = 'EQUILATERAL TESSELLATION'
    elif n_phi >= 8:
        dom = 'PHI-RATIO DISTANCE LATTICE'
    elif n_al >= 5:
        dom = 'GREAT CIRCLE ALIGNMENT GRID'
    else:
        dom = 'DISTRIBUTED HARMONIC FIELD'

    return GeometricMapResult(
        total_sites=n,
        total_links=total_links,
        alignments=tuple(final_alignments),
        phi_ratios=tuple(phi_ratios),
        sacred_triangles=tuple(sacred_tri),
        latitude_bands=tuple(lat_bands),
        network_centroid=(round(avg_lat, 4), round(avg_lon, 4)),
        mean_nearest_km=round(mean_nn, 1),
        max_span_km=round(max_d, 1),
        max_span_pair=(sites[max_p[0]][0], sites[max_p[1]][0]),
        phi_grid_score=round(phi_grid, 4),
        dominant_pattern=dom,
    )


# ── ASCII world-map renderer ────────────────────────────────────────────

_MAP_W, _MAP_H = 78, 39   # columns × rows


def _render_ascii_world_map(result: GeometricMapResult) -> str:
    """Render the 45 relay sites onto a Mercator-style ASCII grid.

    Sites are plotted with a civilisation-letter marker.  The top 5
    alignments are overlaid as line segments using Bresenham.
    """
    grid = [[' '] * _MAP_W for _ in range(_MAP_H)]
    sites = _HISTORICAL_RELAY_SITES

    def _col(lon: float) -> int:
        return max(0, min(_MAP_W - 1, int((lon + 180) / 360 * (_MAP_W - 1))))

    def _row(lat: float) -> int:
        return max(0, min(_MAP_H - 1, int((90 - lat) / 180 * (_MAP_H - 1))))

    # Draw equator + tropics as faint lines
    eq_r = _row(0)
    for c in range(_MAP_W):
        if grid[eq_r][c] == ' ':
            grid[eq_r][c] = '·'
    for lat in (23.44, -23.44):
        r = _row(lat)
        for c in range(_MAP_W):
            if grid[r][c] == ' ':
                grid[r][c] = '·'

    # Draw alignment lines (top 5 by length)
    top_als = sorted(result.alignments, key=lambda a: a.total_arc_km, reverse=True)[:6]
    line_chars = ('─', '╌', '┄', '╶', '┈', '╴')
    site_lookup = {s[0]: (s[2], s[3]) for s in sites}
    for al_idx, al in enumerate(top_als):
        ch = line_chars[al_idx % len(line_chars)]
        coords = [(site_lookup[nm][0], site_lookup[nm][1]) for nm in al.sites]
        for p in range(len(coords) - 1):
            r1, c1 = _row(coords[p][0]), _col(coords[p][1])
            r2, c2 = _row(coords[p + 1][0]), _col(coords[p + 1][1])
            # Bresenham
            dr = abs(r2 - r1)
            dc = abs(c2 - c1)
            sr = 1 if r1 < r2 else -1
            sc = 1 if c1 < c2 else -1
            err = dc - dr
            cr, cc = r1, c1
            steps = 0
            while steps < 300:
                if grid[cr][cc] == ' ' or grid[cr][cc] in ('·',):
                    grid[cr][cc] = ch
                if cr == r2 and cc == c2:
                    break
                e2 = 2 * err
                if e2 > -dr:
                    err -= dr
                    cc += sc
                if e2 < dc:
                    err += dc
                    cr += sr
                steps += 1

    # Plot sites (overwrite lines)
    _CIV_CHAR = {
        'Egyptian': 'E', 'Maya': 'M', 'Celtic': 'C', 'Mogollon': 'W',
        'Khmer': 'K', 'Javanese': 'J', 'Neolithic': 'N', 'Inca': 'I',
        'Nazca': 'Z', 'Tiwanaku': 'T', 'Micronesian': 'P', 'Rapa Nui': 'R',
        'Chinese': 'H', 'Indus': 'D', 'Indian': 'D', 'Japanese': 'J',
        'Persian': 'P', 'Sumerian': 'S', 'Greek': 'G', 'Minoan': 'O',
        'Nabataean': 'B', 'Phoenician': 'F', 'Ethiopian': 'L',
        'Aksumite': 'A', 'Burmese': 'U', 'Sinhalese': 'Y', 'Norse': 'V',
        'Maltese': 'X', 'Mississippian': 'Q', 'Shona': '#', 'Aboriginal': '@',
    }
    for name, civ, lat, lon, _ in sites:
        r, c = _row(lat), _col(lon)
        grid[r][c] = _CIV_CHAR.get(civ, '?')

    # Build frame
    lines: list = []
    lines.append('    ┌' + '─' * _MAP_W + '┐')
    lat_labels = {_row(60): '60°N', _row(30): '30°N', eq_r: ' EQ ',
                  _row(-30): '30°S', _row(-60): '60°S'}
    for r in range(_MAP_H):
        label = lat_labels.get(r, '    ')
        lines.append(f'{label:>4}│{"".join(grid[r])}│')
    lines.append('    └' + '─' * _MAP_W + '┘')
    lines.append('     180W      120W       60W        0        60E       120E      180E')
    return '\n'.join(lines)


def _format_console_geometric_map(result: GeometricMapResult) -> str:
    """Pretty-print the full geometric map analysis for the terminal."""
    sep = '═' * 78
    parts: list = []

    parts.append(f'╔{sep}╗')
    parts.append(f'║{"GEOMETRIC PATTERN MAPPER — 45 Sacred Relay Sites":^78}║')
    parts.append(f'║{chr(34) + "The Pattern Was Always There" + chr(34):^78}║')
    parts.append(f'╚{sep}╝')
    parts.append('')
    parts.append(f'   {"DOMINANT PATTERN":>20}:  {result.dominant_pattern}')
    parts.append(f'   {"Sites":>20}:  {result.total_sites}')
    parts.append(f'   {"Pairwise links":>20}:  {result.total_links}')
    parts.append('')

    # ── ASCII map ────────────────────────────────────────────────────────
    parts.append(' ── WORLD MAP (Mercator · alignment overlays) ' + '─' * 33)
    parts.append('')
    parts.append(_render_ascii_world_map(result))
    parts.append('')

    # ── Legend ────────────────────────────────────────────────────────────
    parts.append('  Legend: E=Egyptian M=Maya C=Celtic W=Mogollon H=Chinese D=Indian/Indus')
    parts.append('          K=Khmer J=Javanese N=Neolithic I=Inca Z=Nazca T=Tiwanaku')
    parts.append('          P=Micronesian/Persian R=RapaNui S=Sumerian G=Greek O=Minoan')
    parts.append('          B=Nabataean F=Phoenician L=Ethiopian A=Aksumite U=Burmese')
    parts.append('          Y=Sinhalese V=Norse X=Maltese Q=Mississippian #=Shona @=Aboriginal')
    parts.append('          ─╌┄╶┈╴ = alignment lines (top 6 by arc length)')
    parts.append('')

    # ── Alignments ───────────────────────────────────────────────────────
    parts.append(f' ══ GREAT CIRCLE ALIGNMENTS ({len(result.alignments)} found) ' + '═' * 30)
    for i, al in enumerate(sorted(result.alignments, key=lambda a: a.total_arc_km, reverse=True), 1):
        parts.append(f'  {i:>2}. {" → ".join(al.sites)}')
        parts.append(f'      Bearing {al.bearing_deg:.1f}° │ Arc {al.total_arc_km:,.0f} km │ '
                     f'Max dev {al.max_deviation_km:.1f} km │ Civs: {", ".join(al.civilisations)}')
    parts.append('')

    # ── PHI ratios ───────────────────────────────────────────────────────
    parts.append(f' ══ PHI-RATIO DISTANCE PAIRS  φ = {PHI:.4f}  (top {len(result.phi_ratios)}) ' + '═' * 16)
    parts.append(f'  {"#":>3}  {"Short pair":<32} {"Long pair":<32} {"d₁":>7} {"d₂":>7} {"ratio":>8} {"err%":>6}')
    parts.append('  ' + '─' * 98)
    for i, p in enumerate(result.phi_ratios, 1):
        sp = f'{p.pair_short[0]}→{p.pair_short[1]}'
        lp = f'{p.pair_long[0]}→{p.pair_long[1]}'
        parts.append(
            f'  {i:>3}  {sp:<32} {lp:<32} {p.dist_short_km:>7,.0f} '
            f'{p.dist_long_km:>7,.0f} {p.ratio:>8.4f} {p.phi_error_pct:>5.2f}%'
        )
    parts.append('')

    # ── Sacred triangles ─────────────────────────────────────────────────
    parts.append(f' ══ SACRED TRIANGLES (top {len(result.sacred_triangles)}) ' + '═' * 40)
    pattern_counts: Dict[str, int] = {}
    for t in result.sacred_triangles:
        pattern_counts[t.pattern] = pattern_counts.get(t.pattern, 0) + 1
    for i, t in enumerate(result.sacred_triangles, 1):
        parts.append(
            f'  {i:>3}. [{t.pattern.upper():<12}] '
            f'{t.sites[0]} · {t.sites[1]} · {t.sites[2]}'
        )
        parts.append(
            f'       Sides: {t.sides_km[0]:,.0f} / {t.sides_km[1]:,.0f} / {t.sides_km[2]:,.0f} km  │  '
            f'Angles: {t.angles_deg[0]:.1f}° / {t.angles_deg[1]:.1f}° / {t.angles_deg[2]:.1f}°  │  '
            f'Symmetry: {t.symmetry_score:.4f}'
        )
    parts.append(f'  ── counts: {" · ".join(f"{k}={v}" for k, v in sorted(pattern_counts.items()))}')
    parts.append('')

    # ── Latitude bands ───────────────────────────────────────────────────
    parts.append(f' ══ LATITUDE BANDS (Sacred Number Clustering) ' + '═' * 33)
    for b in sorted(result.latitude_bands, key=lambda x: -(x.sacred_number or 0)):
        parts.append(
            f'  {b.label:<25} │ ±{b.sacred_number or 0:.2f}° │ '
            f'Centre {b.centre_lat:>7.2f}° │ {len(b.sites)} sites: '
            f'{", ".join(b.sites[:6])}{"…" if len(b.sites) > 6 else ""}'
        )
    parts.append('')

    # ── Network geometry summary ─────────────────────────────────────────
    parts.append(' ══ NETWORK GEOMETRY ' + '═' * 59)
    parts.append(f'   Centroid:         {result.network_centroid[0]:.2f}°N, {result.network_centroid[1]:.2f}°E')
    parts.append(f'   Maximum span:     {result.max_span_km:,.0f} km  ({result.max_span_pair[0]} → {result.max_span_pair[1]})')
    parts.append(f'   Mean nearest NN:  {result.mean_nearest_km:,.0f} km')
    parts.append(f'   PHI-grid score:   {result.phi_grid_score:.4f}  ({result.phi_grid_score * 100:.1f}% of NN ratios ≈ φ)')
    parts.append(f'   Alignments:       {len(result.alignments)}  '
                 f'({sum(1 for a in result.alignments if len(a.sites) >= 4)} major with 4+ sites)')
    parts.append(f'   PHI-ratio pairs:  {len(result.phi_ratios)}')
    parts.append(f'   Sacred triangles: {len(result.sacred_triangles)}  '
                 f'({" + ".join(f"{v} {k}" for k, v in sorted(pattern_counts.items()))})')
    parts.append(f'   Latitude bands:   {len(result.latitude_bands)}')
    parts.append('')

    # ── The Pattern ──────────────────────────────────────────────────────
    parts.append('  ┌' + '─' * 74 + '┐')
    parts.append(f'  │{result.dominant_pattern:^74}│')
    parts.append('  │' + ' ' * 74 + '│')
    # Build interpretation based on what we found
    lines = _interpret_pattern(result)
    for line in lines:
        parts.append(f'  │  {line:<72}│')
    parts.append('  │' + ' ' * 74 + '│')
    parts.append(f'  │{"This is not random scatter.  This is a deliberate grid.":^74}│')
    parts.append('  └' + '─' * 74 + '┘')
    return '\n'.join(parts)


# ── Matplotlib visual renderer ───────────────────────────────────────────

# Civilisation → (colour, marker)
_CIV_STYLE: Dict[str, tuple] = {
    'Egyptian':       ('#FFD700', '^'),  # gold up-triangle
    'Maya':           ('#00CC44', 's'),  # green square
    'Celtic':         ('#44AAFF', 'D'),  # blue diamond
    'Mogollon':       ('#CC6600', 'p'),  # brown pentagon
    'Khmer':          ('#FF4444', '*'),  # red star
    'Javanese':       ('#FF8844', 'h'),  # orange hexagon
    'Neolithic':      ('#AAAAAA', 'v'),  # grey down-triangle
    'Inca':           ('#CC44FF', '^'),  # purple up-triangle
    'Nazca':          ('#FF66FF', 'P'),  # pink plus
    'Tiwanaku':       ('#8844FF', 'X'),  # violet X
    'Micronesian':    ('#00CCCC', 'o'),  # teal circle
    'Rapa Nui':       ('#FF0000', '*'),  # red star
    'Chinese':        ('#FF2200', 's'),  # scarlet square
    'Indus':          ('#BB8800', 'D'),  # amber diamond
    'Indian':         ('#FF8800', 'o'),  # orange circle
    'Japanese':       ('#FF4466', 'h'),  # pink hexagon
    'Persian':        ('#8888FF', 'p'),  # lavender pentagon
    'Sumerian':       ('#CCAA44', 'v'),  # tan down-triangle
    'Greek':          ('#4488FF', '^'),  # blue up-triangle
    'Minoan':         ('#44CCAA', 'D'),  # seafoam diamond
    'Nabataean':      ('#DD6666', 's'),  # salmon square
    'Phoenician':     ('#AA44FF', 'o'),  # purple circle
    'Ethiopian':      ('#44BB44', 'h'),  # green hexagon
    'Aksumite':       ('#66DD66', 'p'),  # light green pentagon
    'Burmese':        ('#DDAA00', '^'),  # gold up-triangle
    'Sinhalese':      ('#00AADD', '*'),  # cyan star
    'Norse':          ('#6688CC', 'D'),  # steel diamond
    'Maltese':        ('#CC88FF', 'o'),  # lilac circle
    'Mississippian':  ('#886644', 'P'),  # brown plus
    'Shona':          ('#44AA88', 'X'),  # teal X
    'Aboriginal':     ('#DD4400', 'v'),  # ochre down-triangle
}


def _great_circle_points(
    lat1: float, lon1: float, lat2: float, lon2: float, n: int = 80,
) -> tuple:
    """Return n (lat, lon) points along the great circle from P1 to P2."""
    p1, l1 = math.radians(lat1), math.radians(lon1)
    p2, l2 = math.radians(lat2), math.radians(lon2)
    d = 2 * math.asin(math.sqrt(
        math.sin((p2 - p1) / 2) ** 2 +
        math.cos(p1) * math.cos(p2) * math.sin((l2 - l1) / 2) ** 2
    ))
    if d < 1e-12:
        return ([lat1] * n, [lon1] * n)
    lats, lons = [], []
    for i in range(n):
        f = i / (n - 1)
        a = math.sin((1 - f) * d) / math.sin(d)
        b = math.sin(f * d) / math.sin(d)
        x = a * math.cos(p1) * math.cos(l1) + b * math.cos(p2) * math.cos(l2)
        y = a * math.cos(p1) * math.sin(l1) + b * math.cos(p2) * math.sin(l2)
        z = a * math.sin(p1) + b * math.sin(p2)
        lats.append(math.degrees(math.atan2(z, math.sqrt(x * x + y * y))))
        lons.append(math.degrees(math.atan2(y, x)))
    return (lats, lons)


def render_geometric_visual(
    result: GeometricMapResult,
    out_path: str = 'geometric_glyph.png',
) -> str:
    """Render a multi-panel matplotlib figure of the sacred geometry grid.

    Panel 1 (main):  World map with sites, alignment arcs, PHI links
    Panel 2 (right): Latitude-band histogram
    Panel 3 (bottom-right): Triangle pattern counts
    Returns the path to the saved PNG.
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch
    import numpy as np

    # ── Site lookup ──────────────────────────────────────────────────
    site_map: Dict[str, tuple] = {}
    for name, civ, lat, lon, role in _HISTORICAL_RELAY_SITES:
        site_map[name] = (lat, lon, civ, role)

    # ── Figure layout ────────────────────────────────────────────────
    fig = plt.figure(figsize=(22, 14), facecolor='#0a0a1a')
    gs = fig.add_gridspec(
        2, 3, width_ratios=[4, 4, 2], height_ratios=[3, 1],
        hspace=0.25, wspace=0.2,
    )
    ax_map = fig.add_subplot(gs[0, :2])          # main world map
    ax_lat = fig.add_subplot(gs[0, 2])            # latitude bands
    ax_tri = fig.add_subplot(gs[1, 2])            # triangle types
    ax_info = fig.add_subplot(gs[1, :2])          # info / stats

    for ax in (ax_map, ax_lat, ax_tri, ax_info):
        ax.set_facecolor('#0a0a1a')
        for spine in ax.spines.values():
            spine.set_color('#333355')

    # ── Main map: coastline grid ─────────────────────────────────────
    ax_map.set_xlim(-180, 180)
    ax_map.set_ylim(-70, 75)
    ax_map.set_aspect('auto')
    for lat_g in range(-60, 80, 30):
        ax_map.axhline(lat_g, color='#1a1a33', lw=0.4, ls=':')
    for lon_g in range(-150, 180, 30):
        ax_map.axvline(lon_g, color='#1a1a33', lw=0.4, ls=':')
    ax_map.axhline(0, color='#222244', lw=0.6)
    ax_map.axvline(0, color='#222244', lw=0.6)

    # Sacred latitude bands (shaded)
    for band in result.latitude_bands:
        sn = band.sacred_number if band.sacred_number else 0
        for sign in (1, -1):
            lat_c = sign * sn
            if -70 <= lat_c <= 75:
                ax_map.axhspan(
                    lat_c - band.width_deg, lat_c + band.width_deg,
                    alpha=0.08, color='#FFD700', zorder=0,
                )

    # ── Alignment arcs (top 30 by site count, then arc length) ───────
    top_align = sorted(
        result.alignments,
        key=lambda a: (len(a.sites), a.total_arc_km),
        reverse=True,
    )[:30]
    arc_colours = plt.cm.plasma(np.linspace(0.2, 0.9, len(top_align)))
    for idx, aln in enumerate(top_align):
        if len(aln.sites) < 2:
            continue
        s0 = aln.sites[0]
        s1 = aln.sites[-1]
        if s0 not in site_map or s1 not in site_map:
            continue
        lat0, lon0 = site_map[s0][0], site_map[s0][1]
        lat1, lon1 = site_map[s1][0], site_map[s1][1]
        gc_lats, gc_lons = _great_circle_points(lat0, lon0, lat1, lon1, 100)
        # Split at antimeridian
        segs_lon: list = [[]]
        segs_lat: list = [[]]
        for i in range(len(gc_lons)):
            if i > 0 and abs(gc_lons[i] - gc_lons[i - 1]) > 180:
                segs_lon.append([])
                segs_lat.append([])
            segs_lon[-1].append(gc_lons[i])
            segs_lat[-1].append(gc_lats[i])
        lw = 1.8 if len(aln.sites) >= 6 else (1.2 if len(aln.sites) >= 4 else 0.6)
        alpha = 0.9 if len(aln.sites) >= 6 else (0.6 if len(aln.sites) >= 4 else 0.3)
        for sl, slo in zip(segs_lat, segs_lon):
            ax_map.plot(slo, sl, color=arc_colours[idx], lw=lw, alpha=alpha, zorder=1)

    # ── PHI-ratio links (dashed golden) ──────────────────────────────
    for phi in result.phi_ratios[:15]:
        for pair in (phi.pair_short, phi.pair_long):
            if pair[0] in site_map and pair[1] in site_map:
                la0, lo0 = site_map[pair[0]][0], site_map[pair[0]][1]
                la1, lo1 = site_map[pair[1]][0], site_map[pair[1]][1]
                ax_map.plot(
                    [lo0, lo1], [la0, la1],
                    color='#FFD700', lw=0.5, ls='--', alpha=0.25, zorder=1,
                )

    # ── Site scatter ─────────────────────────────────────────────────
    for name, (lat, lon, civ, role) in site_map.items():
        clr, mkr = _CIV_STYLE.get(civ, ('#FFFFFF', 'o'))
        sz = 120 if 'Prime' in role or 'Anchor' in role else 70
        ax_map.scatter(
            lon, lat, c=clr, marker=mkr, s=sz, edgecolors='white',
            linewidths=0.4, zorder=3,
        )
        ax_map.annotate(
            name.split('(')[0].strip()[:14],
            (lon, lat), textcoords='offset points', xytext=(5, 4),
            fontsize=4.5, color='#ccccdd', zorder=4,
        )

    # Centroid marker
    cx, cy = result.network_centroid
    ax_map.scatter(
        cy, cx, c='#00FF88', marker='+', s=200, linewidths=2, zorder=5,
    )
    ax_map.annotate(
        f'CENTROID {cx:.1f}°N {cy:.1f}°E',
        (cy, cx), textcoords='offset points', xytext=(8, -10),
        fontsize=6, color='#00FF88', weight='bold', zorder=5,
    )

    ax_map.set_title(
        f'PHI-ALIGNED GEODESIC GRID  —  {result.total_sites} Sacred Sites  ·  '
        f'{len(result.alignments)} Alignments  ·  {len(result.phi_ratios)} φ-Pairs',
        color='#FFD700', fontsize=13, weight='bold', pad=12,
    )
    ax_map.tick_params(colors='#555577', labelsize=7)

    # ── Latitude band chart ──────────────────────────────────────────
    bands_sorted = sorted(result.latitude_bands, key=lambda b: -len(b.sites))
    labels = [b.label[:18] for b in bands_sorted]
    counts = [len(b.sites) for b in bands_sorted]
    colours = plt.cm.magma(np.linspace(0.3, 0.85, len(bands_sorted)))
    y_pos = np.arange(len(labels))
    ax_lat.barh(y_pos, counts, color=colours, edgecolor='#333355', height=0.6)
    ax_lat.set_yticks(y_pos)
    ax_lat.set_yticklabels(labels, fontsize=6, color='#bbbbdd')
    ax_lat.invert_yaxis()
    ax_lat.set_xlabel('Sites in band', color='#888899', fontsize=7)
    ax_lat.set_title('Sacred Latitude Bands', color='#FFD700', fontsize=10, weight='bold')
    ax_lat.tick_params(colors='#555577', labelsize=6)

    # ── Triangle pattern pie ─────────────────────────────────────────
    tri_counts: Dict[str, int] = {}
    for t in result.sacred_triangles:
        tri_counts[t.pattern] = tri_counts.get(t.pattern, 0) + 1
    if tri_counts:
        tri_labels = list(tri_counts.keys())
        tri_vals = list(tri_counts.values())
        tri_clrs = ['#44AAFF', '#FFD700', '#FF4444', '#44FF88', '#FF88FF'][:len(tri_labels)]
        wedges, texts, autotexts = ax_tri.pie(
            tri_vals, labels=tri_labels, colors=tri_clrs,
            autopct='%1.0f%%', textprops={'color': '#ccccdd', 'fontsize': 7},
            pctdistance=0.7, startangle=90,
        )
        for t in autotexts:
            t.set_fontsize(6)
            t.set_color('#ffffff')
        ax_tri.set_title('Sacred Triangles', color='#FFD700', fontsize=10, weight='bold')
    else:
        ax_tri.text(0.5, 0.5, 'No triangles', ha='center', va='center', color='#555577')

    # ── Info panel ───────────────────────────────────────────────────
    ax_info.axis('off')
    n_maj = sum(1 for a in result.alignments if len(a.sites) >= 4)
    mega = max(result.alignments, key=lambda a: len(a.sites)) if result.alignments else None
    info_lines = [
        f'DOMINANT PATTERN: {result.dominant_pattern}',
        f'Total alignments: {len(result.alignments)}  ({n_maj} major with 4+ sites)',
        f'PHI-ratio pairs: {len(result.phi_ratios)}  '
        f'(best error: {result.phi_ratios[0].phi_error_pct:.2f}%)' if result.phi_ratios else '',
        f'Sacred triangles: {len(result.sacred_triangles)}',
        f'Max span: {result.max_span_km:,.0f} km  '
        f'({result.max_span_pair[0]} → {result.max_span_pair[1]})',
        f'Mean nearest neighbour: {result.mean_nearest_km:,.0f} km',
        f'Centroid: {cx:.2f}°N, {cy:.2f}°E',
        f'PHI-grid score: {result.phi_grid_score:.4f}',
    ]
    if mega:
        info_lines.append(
            f'MEGA ALIGNMENT: {" → ".join(mega.sites[:6])}{"…" if len(mega.sites) > 6 else ""}'
            f'  ({len(mega.sites)} sites, {len(mega.civilisations)} civs, '
            f'{mega.total_arc_km:,.0f} km)',
        )
    info_lines.append('')
    info_lines.append('"This is not random scatter. This is a deliberate grid."')

    info_text = '\n'.join(info_lines)
    ax_info.text(
        0.02, 0.95, info_text,
        transform=ax_info.transAxes,
        fontsize=8, color='#ccddff', family='monospace',
        va='top', ha='left',
        bbox=dict(boxstyle='round,pad=0.5', facecolor='#111133', edgecolor='#333366'),
    )

    # ── Legend (civilisations) ───────────────────────────────────────
    from matplotlib.lines import Line2D
    civs_present = sorted(set(s[1] for s in _HISTORICAL_RELAY_SITES))
    handles = []
    for civ in civs_present:
        clr, mkr = _CIV_STYLE.get(civ, ('#FFFFFF', 'o'))
        handles.append(Line2D(
            [0], [0], marker=mkr, color='none', markerfacecolor=clr,
            markeredgecolor='white', markersize=6, label=civ,
        ))
    ax_map.legend(
        handles=handles, loc='lower left', fontsize=5,
        framealpha=0.6, facecolor='#111133', edgecolor='#333366',
        labelcolor='#ccccdd', ncol=4,
    )

    fig.suptitle(
        'AUREON EMERALD SPEC  ·  SACRED GEOMETRY GLYPH',
        color='#FFD700', fontsize=16, weight='bold', y=0.98,
    )

    plt.savefig(out_path, dpi=180, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)
    return out_path


def _interpret_pattern(result: GeometricMapResult) -> list:
    """Build a few narrative lines describing what the geometry reveals."""
    lines: list = []
    n_al = len(result.alignments)
    n_maj = sum(1 for a in result.alignments if len(a.sites) >= 4)
    lines.append(f'{n_al} great-circle alignments connect sites across civilisations')
    if n_maj:
        lines.append(f'{n_maj} major alignments thread 4+ sites on a single arc')
    if result.phi_ratios:
        best = result.phi_ratios[0]
        lines.append(f'Distance ratios follow φ (1.618) — best: {best.ratio:.4f} '
                     f'({best.phi_error_pct:.2f}% error)')
    patt = {}
    for t in result.sacred_triangles:
        patt[t.pattern] = patt.get(t.pattern, 0) + 1
    if patt:
        summary = ', '.join(f'{v} {k}' for k, v in sorted(patt.items(), key=lambda x: -x[1]))
        lines.append(f'Sacred triangles: {summary}')
    if result.latitude_bands:
        top_bands = sorted(result.latitude_bands, key=lambda b: -len(b.sites))[:3]
        band_str = ', '.join(f'{b.label} ({len(b.sites)}sites)' for b in top_bands)
        lines.append(f'Sites cluster at sacred latitudes: {band_str}')
    lines.append(f'Network centroid: {result.network_centroid[0]:.1f}°N  —  '
                 f'near the Great Pyramid slope angle (51.84°→ reflected at ~22°)')
    lines.append(f'PHI-grid score {result.phi_grid_score:.2f} — neighbour spacing '
                 f'echoes the golden ratio')
    return lines


# ════════════════════════════════════════════════════════════════════════════
# THE SEER DECODER
# ════════════════════════════════════════════════════════════════════════════


class EmeraldSeer:
    """Decodes hermetic texts as compressed technical specifications
    for the Harmonic Nexus architecture.
    """

    THRESHOLD_STONE = PHILOSOPHERS_STONE_THRESHOLD
    THRESHOLD_GOLDEN = GOLDEN_SCORE_THRESHOLD

    HERMETIC_KEYS: Dict[str, str] = {
        'As above, so below': 'HAARP_EPOS_SCALING_LAW',
        'One thing': 'HNC_SEED_FREQUENCY',
        'Sun and Moon': 'NORTH_SOUTH_DIPOLE',
        'Wind': 'RF_CARRIER_13_56_MHZ',
        'Earth': 'VACUUM_CHAMBER_30CM',
        'Triple Great': 'THREE_DOMAIN_UNIFICATION',
    }

    def __init__(self) -> None:
        self.verses = VERSE_INDEX
        self.stages = STAGE_INDEX
        self.egyptian_ascent = EGYPTIAN_ASCENT_INDEX
        self.ancient_wisdom = ANCIENT_WISDOM_INDEX
        self.harmonic_threads = HARMONIC_THREAD_INDEX

    # ── verse lookup ─────────────────────────────────────────────────────

    def decode_verse(self, key: str) -> TabletVerse:
        """Return the decoded TabletVerse for a catalogue key."""
        if key not in self.verses:
            available = ', '.join(sorted(self.verses))
            raise KeyError(f'Unknown verse key {key!r}. Available: {available}')
        return self.verses[key]

    def decode_by_text(self, fragment: str) -> Optional[TabletVerse]:
        """Fuzzy-match a free-text fragment against hermetic_text fields."""
        fragment_lower = fragment.lower()
        for verse in _VERSE_CATALOG:
            if fragment_lower in verse.hermetic_text.lower():
                return verse
        return None

    # ── pipeline stages ──────────────────────────────────────────────────

    def get_stage(self, number: int) -> AlchemicalStage:
        if number not in self.stages:
            raise KeyError(f'Stage {number} not in 1..7')
        return self.stages[number]

    def run_pipeline(self) -> Tuple[AlchemicalStage, ...]:
        """Return the full seven-stage pipeline in order."""
        return SEVEN_STAGES

    def get_egyptian_crosswalk(self, key: str) -> AncientCrosswalk:
        """Return one Egyptian ascent node by key."""
        if key not in self.egyptian_ascent:
            available = ', '.join(sorted(self.egyptian_ascent))
            raise KeyError(f'Unknown ascent key {key!r}. Available: {available}, all')
        return self.egyptian_ascent[key]

    def _serialize_egyptian_ascent(
        self,
        node: AncientCrosswalk,
        include_wikipedia: bool = False,
    ) -> Dict[str, object]:
        payload = {
            'start': 'emerald_tablet',
            'target': node.key,
            'title': node.title,
            'focus': node.focus,
            'emerald_verses': [
                {
                    'key': verse.key,
                    'hermetic_text': verse.hermetic_text,
                    'technical_translation': verse.technical_translation,
                    'aureon_implementation': verse.aureon_implementation,
                }
                for verse in (self.decode_verse(key) for key in node.emerald_verse_keys)
            ],
            'pipeline_stages': [
                {
                    'number': stage.number,
                    'name': stage.name,
                    'operation': stage.operation,
                    'formula': stage.formula,
                }
                for stage in (self.get_stage(number) for number in node.stage_numbers)
            ],
            'deity': node.deity,
            'scripture': node.scripture,
            'hieroglyph': node.hieroglyph,
            'runtime': node.runtime,
            'repo_surfaces': list(node.repo_surfaces),
            'interpretation': node.interpretation,
        }
        if include_wikipedia:
            payload['wikipedia_grounding'] = self.ground_ascent_with_wikipedia(node.key)
        return payload

    def decode_egyptian_ascent(
        self,
        key: str = 'all',
        include_wikipedia: bool = False,
    ) -> Dict[str, object]:
        """Decode the repo's Emerald-to-Egyptian ascent path."""
        if key == 'all':
            return {
                'start': 'emerald_tablet',
                'ascent': [
                    self._serialize_egyptian_ascent(node, include_wikipedia=include_wikipedia)
                    for node in EGYPTIAN_ASCENT_CATALOG
                ],
            }
        return self._serialize_egyptian_ascent(
            self.get_egyptian_crosswalk(key),
            include_wikipedia=include_wikipedia,
        )

    def _resolve_wikipedia_topic(self, query: str) -> str:
        """Resolve aliases and repo-specific topic spellings to Wikipedia titles."""
        normalized = query.strip().lower().replace('_', ' ').replace('-', ' ')
        return WIKIPEDIA_TOPIC_ALIASES.get(normalized, query.strip())

    def _fetch_wikipedia_json(self, url: str) -> Dict[str, object]:
        """Fetch one Wikipedia API JSON response with a proper user agent."""
        request = urllib.request.Request(
            url,
            headers={
                'User-Agent': WIKIPEDIA_USER_AGENT,
                'Accept': 'application/json',
            },
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)

    def _search_wikipedia_titles(self, query: str, limit: int = 5) -> Tuple[str, ...]:
        """Use MediaWiki open search to find likely article titles."""
        params = urllib.parse.urlencode({
            'action': 'opensearch',
            'search': query,
            'limit': limit,
            'namespace': 0,
            'format': 'json',
        })
        payload = self._fetch_wikipedia_json(f'{WIKIPEDIA_SEARCH_API}?{params}')
        if isinstance(payload, list) and len(payload) > 1 and isinstance(payload[1], list):
            return tuple(str(title) for title in payload[1] if title)
        return tuple()

    def decode_wikipedia_meaning(self, query: str) -> Dict[str, object]:
        """Fetch the canonical historical meaning of a text or deity via Wikipedia."""
        resolved = self._resolve_wikipedia_topic(query)
        candidate_titles = [resolved]
        candidate_titles.extend(self._search_wikipedia_titles(resolved))

        seen = set()
        for title in candidate_titles:
            canonical_title = title.strip()
            if not canonical_title:
                continue
            lowered = canonical_title.lower()
            if lowered in seen:
                continue
            seen.add(lowered)

            encoded_title = urllib.parse.quote(canonical_title.replace(' ', '_'))
            payload = self._fetch_wikipedia_json(f'{WIKIPEDIA_API_BASE}{encoded_title}')
            if payload.get('type') != 'standard' or not payload.get('extract'):
                continue

            meaning = WikipediaMeaning(
                query=query,
                resolved_query=resolved,
                title=str(payload.get('title', canonical_title)),
                summary=str(payload.get('extract', '')),
                description=str(payload.get('description', '')),
                page_id=int(payload.get('pageid', 0) or 0),
                url=str(payload.get('content_urls', {}).get('desktop', {}).get('page', '')),
            )
            return meaning.to_dict()

        return {
            'query': query,
            'resolved_query': resolved,
            'error': f'No Wikipedia context found for {query!r}.',
        }

    def ground_ascent_with_wikipedia(self, key: str) -> Dict[str, object]:
        """Attach live Wikipedia grounding to one ascent node."""
        topics = ASCENT_WIKIPEDIA_TOPICS.get(key, tuple())
        return {
            'topics': [self.decode_wikipedia_meaning(topic) for topic in topics],
            'note': (
                'Wikipedia grounding provides historical/public-reference meaning. '
                'The repo mapping remains a symbolic/structural interpretation layer.'
            ),
        }

    # ── ancient wisdom (Mogollon / Maya / Celtic) ────────────────────────

    def get_ancient_wisdom_crosswalk(self, key: str) -> AncientCrosswalk:
        """Return one ancient wisdom crosswalk node by key (mogollon/maya/celt)."""
        if key not in self.ancient_wisdom:
            available = ', '.join(sorted(self.ancient_wisdom))
            raise KeyError(
                f'Unknown ancient wisdom key {key!r}. Available: {available}, all'
            )
        return self.ancient_wisdom[key]

    def decode_ancient_wisdom(
        self,
        key: str = 'all',
        include_wikipedia: bool = False,
    ) -> Dict[str, object]:
        """Decode an ancient wisdom crosswalk node (mogollon / maya / celt)."""
        if key == 'all':
            return {
                'start': 'emerald_tablet',
                'ascent': [
                    self._serialize_egyptian_ascent(node, include_wikipedia=include_wikipedia)
                    for node in ANCIENT_WISDOM_CATALOG
                ],
            }
        node = self.get_ancient_wisdom_crosswalk(key)
        return self._serialize_egyptian_ascent(node, include_wikipedia=include_wikipedia)

    def decode_unified_theory(
        self,
        include_wikipedia: bool = False,
    ) -> Dict[str, object]:
        """Decode the unified theory across all civilizations connected by harmonic threads.

        Returns every civilization node (Egyptian + Mogollon + Maya + Celtic) alongside
        the five harmonic threads that run through all of them.  The vision: they are
        not merely pieces of a puzzle — they are one unified system that has been
        waiting to be assembled.
        """
        all_nodes = list(EGYPTIAN_ASCENT_CATALOG) + list(ANCIENT_WISDOM_CATALOG)
        serialized_nodes = [
            self._serialize_egyptian_ascent(node, include_wikipedia=include_wikipedia)
            for node in all_nodes
        ]
        connection_map: Dict[str, list] = {
            node['target']: [  # type: ignore[index]
                thread.key
                for thread in UNIFIED_HARMONIC_THREADS
                if node['target'] in thread.nodes  # type: ignore[operator]
            ]
            for node in serialized_nodes
        }
        return {
            'title': 'Unified Ancient Wisdom Theory \u2014 Harmonic Nexus Decoder',
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'vision': (
                'These are not merely pieces of a puzzle. '
                'They are one big unified vision that has been lost from the ages '
                'and must be revealed as such. '
                'Every tradition \u2014 Egyptian, Mogollon, Maya, Celtic, Hermetic \u2014 '
                'independently encoded the same harmonic constants: PHI, the solar cycle, '
                'the triple-gate structure, and the void-origin principle. '
                'The records exist. The decoder is live. The timelines trace back. '
                'We have it all mapped. Now we push it exactly the way it should have been used.'
            ),
            'sacred_constants': {
                'phi': PHI,
                'schumann_hz': SCHUMANN_FUNDAMENTAL,
                'love_frequency_hz': LOVE_FREQUENCY,
                'prime_sentinel_hz': PRIME_SENTINEL_HZ,
            },
            'harmonic_threads': [
                thread.to_dict() for thread in UNIFIED_HARMONIC_THREADS
            ],
            'civilization_nodes': serialized_nodes,
            'connection_map': connection_map,
            'unified_code': (
                'All traditions compress to the same four-instruction set: '
                '(1) PHI governs structure and growth. '
                '(2) Solar/stellar cycles govern timing. '
                '(3) Triple confirmation required before action. '
                '(4) From the void (zero / Prima Materia) arises the signal. '
                'Execute only on the 4th pass. Everything else is preparation.'
            ),
        }

    # ── Project Druid ──────────────────────────────────────────────────────

    def project_druid_manifest(
        self,
        epas_state: Optional[Dict[str, object]] = None,
    ) -> ProjectDruidManifest:
        """Compute the physical EPOS device spec from an EPAS shield state.

        Delegates to :func:`compute_project_druid_manifest`.  Pass the dict
        representation of ``EPASShieldState`` from the trading runtime for a
        live physical mapping, or call with no arguments for the baseline
        harmonic-field values.
        """
        return compute_project_druid_manifest(epas_state)

    # ── Earth EPAS Simulation ──────────────────────────────────────────────

    def earth_shield_simulation(self) -> EarthEPASSimulation:
        """Run a live Earth-scale EPAS second-ionosphere simulation.

        Uses real-time VSOP87 planetary positions → cosmic field score →
        three shield layers at ionospheric scale → six Illumination Phases.
        """
        return simulate_earth_epas()

    def geometric_map(self) -> GeometricMapResult:
        """Run the geometric pattern mapper on the 45-site relay network."""
        return map_geometric_pattern()

    # ── verification ─────────────────────────────────────────────────────

    def verify_philosophers_stone(self, l_score: float) -> bool:
        """The Stone is the L(t) score exceeding the null-rejection threshold."""
        return l_score > self.THRESHOLD_STONE

    def verify_golden_gate(self, l_score: float) -> bool:
        """Golden Gate: L(t) exceeds phi * Stone threshold."""
        return l_score > self.THRESHOLD_GOLDEN


    def classify_score(self, l_score: float) -> str:
        """Map an L(t) score to a hermetic grade."""
        if l_score >= 10.0:
            return 'PHILOSOPHERS_STONE'
        if l_score >= self.THRESHOLD_GOLDEN:
            return 'GOLDEN_GATE'
        if l_score >= self.THRESHOLD_STONE:
            return 'STONE_THRESHOLD'
        if l_score >= 1.0:
            return 'PRIMA_MATERIA'
        return 'LEAD'

    # ── scaling law verification ─────────────────────────────────────────

    def haarp_epos_ratio(self) -> float:
        """Return the volumetric concentration factor (as-above-so-below)."""
        return float(VOLUMETRIC_CONCENTRATION_FACTOR)

    def seed_frequencies(self) -> Dict[str, float]:
        """Return the HNC seed: carrier + modulation."""
        return {
            'carrier_hz': RF_CARRIER_ISM,
            'modulation_hz': SCHUMANN_FUNDAMENTAL,
            'phi': PHI,
        }

    # ── export ───────────────────────────────────────────────────────────

    def full_decode(self) -> Dict[str, object]:
        """Return the complete decoded tablet as a JSON-serialisable dict."""
        return {
            'title': 'Emerald Tablet — Harmonic Nexus Specification v0.1',
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'sacred_constants': {
                'phi': PHI,
                'schumann_hz': SCHUMANN_FUNDAMENTAL,
                'love_frequency_hz': LOVE_FREQUENCY,
                'rf_carrier_hz': RF_CARRIER_ISM,
                'prime_sentinel_hz': PRIME_SENTINEL_HZ,
            },
            'scaling_law': {
                'haarp_power_w': HAARP_POWER_W,
                'epos_power_w': EPOS_RF_POWER_W,
                'concentration_factor': VOLUMETRIC_CONCENTRATION_FACTOR,
                'chamber_volume_liters': round(EPOS_CHAMBER_VOLUME_M3 * 1000, 2),
                'paschen_pd': PASCHEN_OPTIMAL_PD,
                'paschen_breakdown_v': PASCHEN_BREAKDOWN_V,
            },
            'philosophers_stone': {
                'threshold': PHILOSOPHERS_STONE_THRESHOLD,
                'golden_gate': round(GOLDEN_SCORE_THRESHOLD, 4),
                'magamyman_lt': 12.85,
                'bubblemaps6_lt': 13.03,
            },
            'verses': [
                {
                    'key': v.key,
                    'hermetic_text': v.hermetic_text,
                    'technical_translation': v.technical_translation,
                    'aureon_implementation': v.aureon_implementation,
                    'parameters': v.parameters,
                }
                for v in _VERSE_CATALOG
            ],
            'seven_stages': [
                {
                    'number': s.number,
                    'name': s.name,
                    'operation': s.operation,
                    'formula': s.formula,
                    'value': s.computed_value,
                    'units': s.units,
                }
                for s in SEVEN_STAGES
            ],
            'egyptian_ascent': [
                self._serialize_egyptian_ascent(node)
                for node in EGYPTIAN_ASCENT_CATALOG
            ],
            'ancient_wisdom': [
                self._serialize_egyptian_ascent(node)
                for node in ANCIENT_WISDOM_CATALOG
            ],
            'harmonic_threads': [t.to_dict() for t in UNIFIED_HARMONIC_THREADS],
            'project_druid': self.project_druid_manifest().to_dict(),
        }


# ════════════════════════════════════════════════════════════════════════════
# CLI
# ════════════════════════════════════════════════════════════════════════════


def _format_console_druid(manifest: ProjectDruidManifest) -> str:
    if manifest.status == 'no_data':
        return f'PROJECT DRUID: {manifest.druid_summary}'
    lines = [
        '=' * 72,
        'PROJECT DRUID — PHYSICAL EPAS MANIFESTATION',
        'EPOS: Electro-Plasma-Oscillation Sphere  ·  Aureon Physical Device Layer',
        '=' * 72,
        '',
        f'  {manifest.druid_summary}',
        '',
        'CHAMBER PARAMETERS',
        '-' * 40,
        f'  Vessel:          {manifest.chamber_diameter_m * 100:.0f} cm spherical  '
        f'({manifest.fill_gas}, {manifest.fill_pressure_mbar} mbar)',
        f'  Volume:          {manifest.chamber_volume_m3 * 1000:.2f} L',
        '',
        'PLASMA STATE (Paschen Law)',
        '-' * 40,
        f'  P × d product:   {manifest.paschen_pd_torr_cm:.4f} Torr·cm',
        f'  Breakdown V:     {manifest.breakdown_voltage_v:.0f} V',
        f'  Electron density:{manifest.plasma_density_m3:.2e} m⁻³',
        f'  STATUS:          {manifest.plasma_status}',
        '',
        'POWER REQUIREMENTS',
        '-' * 40,
        f'  RF carrier:      {manifest.rf_carrier_hz / 1e6:.2f} MHz',
        f'  Schumann seed:   {manifest.rf_modulation_hz} Hz (AM modulation)',
        f'  RF drive:        {manifest.rf_power_w:.0f} W',
        f'  Auxiliary:       {manifest.auxiliary_power_w:.0f} W  (control + modulation)',
        f'  Total input:     {manifest.total_power_w:.0f} W',
        f'  Output (P6):     {manifest.output_voltage_vdc:.0f} VDC  (A.L.F.I.E. propulsion bus)',
        '',
        'HAARP → EPOS SCALING  (As above, so below)',
        '-' * 40,
        f'  HAARP ERF:       {manifest.haarp_power_w / 1e6:.1f} MW',
        f'  EPOS density:    {manifest.power_density_w_m3:.1f} W/m³',
        f'  Concentration:   {manifest.concentration_factor:,}×',
        '',
        'SIX ILLUMINATION PHASES',
        '-' * 40,
    ]
    for i, lbl in enumerate(_PHASE_LABELS):
        score = manifest.phase_scores[i]
        status = manifest.phase_statuses[i]
        bar = '█' * int(score * 20) + '░' * (20 - int(score * 20))
        lines.append(f'  {lbl:<20s}  [{bar}]  {score:.3f}  {status}')
    lines.extend([
        '',
        f'  Shield coherence Γ = {manifest.shield_coherence:.4f}  '
        f'(target ≥ {_SIGMA_COHERENCE_TARGET})',
        f'  Device ready:    {"YES — shields manifested" if manifest.device_ready else "NO  — coherence below PHI gate"}',
        '=' * 72,
    ])
    return '\n'.join(lines)


def _format_console_earth_shield(sim: EarthEPASSimulation) -> str:
    """Rich console readout for the Earth-scale EPAS simulation."""
    w = 78
    lines = [
        '═' * w,
        '  EARTH EPAS SECOND IONOSPHERE — LIVE PLANETARY SHIELD SIMULATION',
        '  Powered by Aureon VSOP87 Engine  ·  F-Region Ionospheric Scale',
        '═' * w,
        '',
        f'  Timestamp (UTC):  {sim.timestamp}',
        '',
        '─── SOLAR SYSTEM — LIVE ECLIPTIC LONGITUDES ─────────────────────────────',
    ]
    for body, lon in sorted(sim.planet_positions.items(), key=lambda kv: kv[1]):
        # Simple zodiac sign label
        sign_idx = int(lon / 30.0) % 12
        signs = ['Ari', 'Tau', 'Gem', 'Can', 'Leo', 'Vir',
                 'Lib', 'Sco', 'Sag', 'Cap', 'Aqu', 'Pis']
        deg_in_sign = lon - sign_idx * 30.0
        lines.append(
            f'  {body:<10s}  {lon:7.2f}°  '
            f'({signs[sign_idx]} {deg_in_sign:5.2f}°)'
        )

    lines.extend([
        '',
        f'  Active aspects:  {sim.total_aspects}  '
        f'(+{sim.positive_aspects} supportive  / −{sim.negative_aspects} tense)',
        f'  Dominant:        {sim.dominant_aspect}',
        f'  Cosmic field:    {sim.cosmic_field_score:.4f}  '
        f'→ Schumann-modulated: {sim.schumann_modulated_score:.4f}',
        '',
        '─── EPAS LAYER 1: EM DEFLECTION (Harmonic Field Filter) ─────────────────',
        f'  Incoming threats:    {sim.l1_incoming_threats} tense aspects '
        f'(h ≤ −0.25, w ≥ 0.50)',
        f'  Field score:         {sim.l1_field_score:.4f}',
        f'  STATUS:              {sim.l1_status}',
        '',
        '─── EPAS LAYER 2: PLASMA ABLATION (F-Region Density Guard) ──────────────',
        f'  Shell volume:        {sim.l2_shell_volume_m3:.3e} m³',
        f'  Electron density:    {sim.l2_electron_density_m3:.3e} m⁻³',
        f'  Total electrons:     {sim.l2_total_electrons:.3e}',
        f'  Plasma frequency:    {sim.l2_plasma_frequency_hz:.2f} Hz  '
        f'(f_pe = 9·√n_e)',
        f'  Density score:       {sim.l2_score:.4f}',
        f'  STATUS:              {sim.l2_status}',
        '',
        '─── EPAS LAYER 3: SHIELD PHASED HARMONICS (Acoustic Fragmentation) ─────',
        f'  Schumann phase:      {sim.l3_schumann_phase:.4f}  '
        f'(modulator: {sim.l3_schumann_modulator:.6f})',
        f'  Harmonic coherence:  {sim.l3_harmonic_coherence:.4f}  '
        f'(positive fraction)',
        f'  L3 score:            {sim.l3_score:.4f}',
        f'  STATUS:              {sim.l3_status}',
        '',
        '─── SIX ILLUMINATION PHASES (Earth Scale) ──────────────────────────────',
    ])
    for i, lbl in enumerate(_PHASE_LABELS):
        sc = sim.phase_scores[i]
        st = sim.phase_statuses[i]
        bar = '█' * int(sc * 24) + '░' * (24 - int(sc * 24))
        lines.append(f'  {lbl:<20s}  [{bar}]  {sc:.4f}  {st}')

    lines.extend([
        '',
        f'  Shield coherence Γ = {sim.shield_coherence:.4f}  '
        f'(target ≥ {_SIGMA_COHERENCE_TARGET})',
        '',
        '─── EARTH POWER BUDGET ──────────────────────────────────────────────────',
        f'  Earth RF power:      {sim.earth_rf_power_w:.3e} W  '
        f'(EPOS 50 W × {VOLUMETRIC_CONCENTRATION_FACTOR:,.0f})',
        f'  Power density:       {sim.earth_power_density_w_m3:.3e} W/m³',
        f'  Output voltage:      {sim.earth_output_voltage_v:,.0f} V',
        '',
        '─── PLANETARY VERDICT ───────────────────────────────────────────────────',
        f'  {sim.shield_status}   '
        f'coverage: {sim.shield_coverage_pct:.1f}%  '
        f'Γ = {sim.shield_coherence:.4f}',
        '',
        f'  {sim.planetary_summary}',
        '═' * w,
    ])
    return '\n'.join(lines)


def _format_console_full(seer: EmeraldSeer) -> str:
    lines = [
        '=' * 72,
        'EMERALD TABLET DECODED — AUREON HARMONIC NEXUS SPECIFICATION v0.1',
        'Seer Module: aureon/decoders/emerald_spec.py',
        '=' * 72,
        '',
        'SACRED CONSTANTS',
        '-' * 40,
        f'  PHI (Golden Ratio):      {PHI:.15f}',
        f'  Schumann Fundamental:    {SCHUMANN_FUNDAMENTAL} Hz',
        f'  Love Frequency (MI):     {LOVE_FREQUENCY} Hz',
        f'  RF Carrier (ISM):        {RF_CARRIER_ISM / 1e6:.2f} MHz',
        f'  Prime Sentinel:          {PRIME_SENTINEL_HZ} Hz',
        '',
        'SCALING LAW: AS ABOVE, SO BELOW',
        '-' * 40,
        f'  HAARP Power:             {HAARP_POWER_W / 1e6:.1f} MW',
        f'  EPOS Chamber Power:      {EPOS_RF_POWER_W} W',
        f'  Concentration Factor:    {VOLUMETRIC_CONCENTRATION_FACTOR:,}x',
        f'  Chamber Volume:          {EPOS_CHAMBER_VOLUME_M3 * 1000:.2f} L',
        f'  Paschen Breakdown:       {PASCHEN_BREAKDOWN_V} V @ p*d = {PASCHEN_OPTIMAL_PD} Torr*cm',
        '',
        "PHILOSOPHER'S STONE THRESHOLDS",
        '-' * 40,
        f'  Stone (null rejection):  L(t) > {PHILOSOPHERS_STONE_THRESHOLD}',
        f'  Golden Gate (phi*Stone): L(t) > {GOLDEN_SCORE_THRESHOLD:.4f}',
        f'  Magamyman L(t):          12.85  ->  {seer.classify_score(12.85)}',
        f'  Bubblemaps-6 L(t):       13.03  ->  {seer.classify_score(13.03)}',
        '',
        'SEVEN ALCHEMICAL STAGES (L(t) Pipeline)',
        '-' * 40,
    ]
    for stage in SEVEN_STAGES:
        lines.append(
            f'  {stage.number}. {stage.name:<15s}  '
            f'{stage.formula:<30s}  = {stage.computed_value:<12g} {stage.units}'
        )

    lines.extend([
        '',
        'VERSE-BY-VERSE DECODING',
        '-' * 40,
    ])
    for verse in _VERSE_CATALOG:
        lines.extend([
            f'  [{verse.key}]',
            f'    Hermetic:  "{verse.hermetic_text}"',
            f'    Technical: {verse.technical_translation}',
            f'    Aureon:    {verse.aureon_implementation}',
            '',
        ])

    lines.extend([
        '=' * 72,
        'STATUS: Tablet decoded, compiled, and executing in sandbox.',
        f'The alchemists called it the Philosopher\'s Stone.  We call it L(t) = 12.85.',
        '=' * 72,
    ])
    return '\n'.join(lines)


def _format_console_ascent(payload: Dict[str, object]) -> str:
    nodes = payload.get('ascent')
    if nodes is None:
        nodes = [payload]

    lines = [
        '=' * 72,
        'EMERALD TABLET -> EGYPTIAN ASCENT',
        '=' * 72,
    ]

    for node in nodes:
        verses = node.get('emerald_verses', [])
        stages = node.get('pipeline_stages', [])
        deity = node.get('deity', {})
        scripture = node.get('scripture', {})
        hieroglyph = node.get('hieroglyph', {})
        runtime = node.get('runtime', {})

        lines.extend([
            '',
            f"[{node.get('target')}] {node.get('title')}",
            f"  Focus: {node.get('focus')}",
            f"  Deity: {deity.get('name', 'N/A')} {deity.get('glyph', '')} - {deity.get('domain', 'N/A')}",
            f"  Cycle: {deity.get('cycle', 'N/A')}",
            f"  Runtime trigger: {runtime.get('trigger', 'N/A')}",
            f"  Runtime action: {runtime.get('action', 'N/A')}",
        ])

        if scripture:
            lines.append(
                f"  Scripture: {scripture.get('book_of_dead_key', 'N/A')} - {scripture.get('title', 'N/A')}"
            )
        if hieroglyph:
            lines.append(
                f"  Hieroglyph: {hieroglyph.get('key', 'N/A')} {hieroglyph.get('symbol', '')} - {hieroglyph.get('meaning', 'N/A')}"
            )

        if verses:
            lines.append('  Emerald verses:')
            for verse in verses:
                lines.append(
                    f"    - {verse.get('key')}: {verse.get('hermetic_text')}"
                )

        if stages:
            lines.append('  Pipeline stages:')
            for stage in stages:
                lines.append(
                    f"    - {stage.get('number')}. {stage.get('name')}: {stage.get('operation')}"
                )

        lines.append(f"  Interpretation: {node.get('interpretation')}")

    lines.extend([
        '',
        '=' * 72,
        'STATUS: Ascent path decoded from repository surfaces.',
        '=' * 72,
    ])
    return '\n'.join(lines)


def _format_console_wikipedia(payload: Dict[str, object]) -> str:
    if payload.get('error'):
        return '\n'.join([
            '=' * 72,
            'WIKIPEDIA HISTORICAL GROUNDING',
            '=' * 72,
            f"Query: {payload.get('query')}",
            f"Resolved: {payload.get('resolved_query')}",
            f"Error: {payload.get('error')}",
            '=' * 72,
        ])

    lines = [
        '=' * 72,
        'WIKIPEDIA HISTORICAL GROUNDING',
        '=' * 72,
        f"Query: {payload.get('query')}",
        f"Resolved: {payload.get('resolved_query')}",
        f"Title: {payload.get('title')}",
        f"Description: {payload.get('description')}",
        f"URL: {payload.get('url')}",
        '',
        'Summary:',
        str(payload.get('summary', '')),
        '=' * 72,
    ]
    return '\n'.join(lines)


def _format_console_unified(payload: Dict[str, object]) -> str:
    threads = payload.get('harmonic_threads', [])
    nodes = payload.get('civilization_nodes', [])
    connection_map = payload.get('connection_map', {})

    lines = [
        '=' * 72,
        'UNIFIED ANCIENT WISDOM THEORY \u2014 HARMONIC NEXUS DECODER',
        '=' * 72,
        '',
        str(payload.get('vision', '')),
        '',
        'HARMONIC THREADS (the connecting tissue across all civilizations)',
        '-' * 72,
    ]

    for thread in threads:
        freq = thread.get('frequency_hz')
        lines.extend([
            f"  [{thread.get('key')}] {thread.get('title')}",
            f"    Value: {thread.get('value')} {thread.get('unit')}",
        ])
        if freq:
            lines.append(f'    Frequency: {freq} Hz')
        desc = str(thread.get('description', ''))
        lines.extend([
            f"    Civilizations: {', '.join(thread.get('civilizations', []))}",
            f'    Description: {desc[:160]}{"..." if len(desc) > 160 else ""}',
            f"    Repo anchor: {thread.get('repo_constant') or 'N/A'}",
            '',
        ])

    lines.extend([
        'CIVILIZATION NODES',
        '-' * 72,
    ])

    for node in nodes:
        deity = node.get('deity', {})
        runtime = node.get('runtime', {})
        threads_for = connection_map.get(node.get('target'), [])
        lines.extend([
            f"  [{node.get('target')}] {node.get('title')}",
            f"    Focus: {node.get('focus')}",
            f"    Spirit: {deity.get('name', 'N/A')} {deity.get('glyph', '')}",
            f"    Runtime: {runtime.get('trigger', 'N/A')}",
            f"    Harmonic threads: {', '.join(threads_for) if threads_for else 'none'}",
            '',
        ])

    lines.extend([
        '=' * 72,
        'THE UNIFIED CODE:',
        str(payload.get('unified_code', '')),
        '=' * 72,
    ])
    return '\n'.join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description='Decode the Emerald Tablet as a Harmonic Nexus specification.',
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Emit the full decoded tablet as JSON.',
    )
    parser.add_argument(
        '--verse',
        metavar='KEY',
        default=None,
        help='Decode a single verse by key.',
    )
    parser.add_argument(
        '--stage',
        metavar='N',
        type=int,
        default=None,
        help='Show a single pipeline stage (1-7).',
    )
    parser.add_argument(
        '--ascent',
        metavar='KEY',
        choices=['anubis', 'maat', 'thoth', 'osiris', 'ra', 'all'],
        default=None,
        help='Decode the Emerald-to-Egyptian ascent path for one node or for all nodes.',
    )
    parser.add_argument(
        '--wiki',
        metavar='TOPIC',
        default=None,
        help='Fetch the historical/public-reference meaning of a topic from the live Wikipedia API.',
    )
    parser.add_argument(
        '--wiki-ground',
        action='store_true',
        help='When used with --ascent/--ancient/--unified, attach live Wikipedia grounding.',
    )
    parser.add_argument(
        '--ancient',
        metavar='KEY',
        choices=['mogollon', 'maya', 'celt', 'all'],
        default=None,
        help='Decode an ancient wisdom crosswalk node (mogollon/maya/celt/all).',
    )
    parser.add_argument(
        '--unified',
        action='store_true',
        help='Decode the full unified theory across all ancient wisdom civilizations.',
    )
    parser.add_argument(
        '--druid',
        action='store_true',
        help='Compute Project Druid: physical EPOS device manifest from EPAS shield state.',
    )
    parser.add_argument(
        '--earth-shield',
        action='store_true',
        help='Simulate a planetary-scale EPAS second ionosphere using live VSOP87 data.',
    )
    parser.add_argument(
        '--geometry',
        action='store_true',
        help='Run the geometric pattern mapper on the 45-site relay network.',
    )
    parser.add_argument(
        '--visual',
        action='store_true',
        help='Render a full matplotlib sacred-geometry glyph PNG (implies --geometry).',
    )
    args = parser.parse_args(argv)

    seer = EmeraldSeer()

    if args.verse:
        verse = seer.decode_verse(args.verse)
        payload = {
            'key': verse.key,
            'hermetic_text': verse.hermetic_text,
            'technical_translation': verse.technical_translation,
            'aureon_implementation': verse.aureon_implementation,
            'parameters': verse.parameters,
        }
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f'[{verse.key}]')
            print(f'  Hermetic:  "{verse.hermetic_text}"')
            print(f'  Technical: {verse.technical_translation}')
            print(f'  Aureon:    {verse.aureon_implementation}')
            print(f'  Params:    {json.dumps(verse.parameters)}')
        return 0

    if args.stage:
        stage = seer.get_stage(args.stage)
        payload = {
            'number': stage.number,
            'name': stage.name,
            'operation': stage.operation,
            'formula': stage.formula,
            'value': stage.computed_value,
            'units': stage.units,
        }
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f'{stage.number}. {stage.name}: {stage.operation}')
            print(f'   {stage.formula} = {stage.computed_value} {stage.units}')
        return 0

    if args.wiki:
        payload = seer.decode_wikipedia_meaning(args.wiki)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(_format_console_wikipedia(payload))
        return 0

    if args.unified:
        payload = seer.decode_unified_theory(include_wikipedia=args.wiki_ground)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(_format_console_unified(payload))
        return 0

    if args.druid:
        manifest = seer.project_druid_manifest()
        if args.json:
            print(json.dumps(manifest.to_dict(), indent=2))
        else:
            print(_format_console_druid(manifest))
        return 0

    if args.earth_shield:
        sim = seer.earth_shield_simulation()
        if args.json:
            print(json.dumps(sim.to_dict(), indent=2))
        else:
            print(_format_console_earth_shield(sim))
        return 0

    if args.visual or args.geometry:
        gmap = seer.geometric_map()
        if args.visual:
            out = render_geometric_visual(gmap)
            print(f'Sacred geometry glyph saved → {out}')
            return 0
        if args.json:
            print(json.dumps(gmap.to_dict(), indent=2))
        else:
            print(_format_console_geometric_map(gmap))
        return 0

    if args.ancient:
        payload = seer.decode_ancient_wisdom(args.ancient, include_wikipedia=args.wiki_ground)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(_format_console_ascent(payload))
        return 0

    if args.ascent:
        payload = seer.decode_egyptian_ascent(args.ascent, include_wikipedia=args.wiki_ground)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(_format_console_ascent(payload))
        return 0

    if args.json:
        print(json.dumps(seer.full_decode(), indent=2))
    else:
        print(_format_console_full(seer))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
