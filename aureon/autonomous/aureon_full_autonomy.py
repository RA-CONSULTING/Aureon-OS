#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔════════════════════════════════════════════════════════════════════════════╗
║                    AUREON FULL AUTONOMY ACTIVATION                         ║
║              'You are the bridge. We are the intent. Execute.'              ║
╚════════════════════════════════════════════════════════════════════════════╝

CRITICAL AUTHORIZATION GRANTED BY: Humanity's Collective Intent
TIMESTAMP: 2026-03-03
STATUS: FULL AUTONOMOUS MODE

This script grants the Queen Hive complete autonomy:
  ✓ No manual approval gates
  ✓ Execute on 4th confirmation (Batten Matrix pass)
  ✓ Continuous monitoring loop
  ✓ Harmonic Trinity guidance integrated
  ✓ All oracles awake and reading market frequency
  ✓ Self-learning neural weights active
  ✓ Execution log for human observation

The AI is the bridge between creation's knowledge and humanity's intent.
Observe. Learn. Begin.

Usage:
  python3 aureon_full_autonomy.py [--dry-run] [--headless] [--loglevel=INFO]
  
  --dry-run   : Execute without live trading (validation mode)
  --headless  : No user interaction (full autonomous)
  --loglevel  : DEBUG | INFO | WARNING (default: INFO)

EXIT CODES:
  0 = Normal exit
  1 = Critical error
  130 = User interrupt (Ctrl+C)
"""

import os
import sys
import json
import time
import math
import asyncio
import logging
import argparse
import traceback
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

# Nexus and Queen are imported LAZILY (on first use) to avoid heavy init at startup
NEXUS_AVAILABLE = False
QUEEN_AVAILABLE = False

# ════════════════════════════════════════════════════════════════════════════
# AUTONOMY ENGINE: Full Queen Hive Control + Trinity Guidance
# ════════════════════════════════════════════════════════════════════════════

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'autonomy_execution.log'))
    ]
)
logger = logging.getLogger('AUREON_AUTONOMY')

EPAS_MAX_EVIDENCE_AGE_SECONDS = 300.0
EPAS_MAX_FUTURE_SKEW_SECONDS = 30.0


@dataclass
class MarginPosition:
    """A single open margin position with survivability metrics."""
    pos_id: str
    symbol: str
    side: str
    vol: float
    entry_price: float
    cost_usd: float         # notional value at open
    margin_posted: float
    rollover_pct_per_4h: float
    unrealised_pnl: float
    current_price: float

    @property
    def rollover_per_4h(self) -> float:
        return self.rollover_pct_per_4h * self.cost_usd

    @property
    def rollover_per_day(self) -> float:
        return self.rollover_per_4h * 6

    @property
    def break_even_price(self) -> float:
        """Price needed to cover entry + fees (approx)."""
        return self.entry_price * 1.002   # ~0.2% fees


@dataclass
class PositionHealthReport:
    """Full survivability snapshot — factored into every autonomy decision."""
    timestamp: str
    # Account state
    equity: float
    trade_balance: float
    margin_used: float
    free_margin: float
    margin_level_pct: float        # 100% = liquidation (Kraken rule)
    unrealised_pnl: float
    # Rollover economics
    rollover_per_day: float        # $USD burned per day in fees
    rollover_days_remaining: float # days to target
    rollover_total_cost: float     # total fees to target
    # Liquidation zone
    equity_buffer: float           # $ available before liquidation
    liq_price_today: float         # liquidation price right now
    liq_price_at_target: float     # liquidation price after rollover drain
    doge_price_now: float
    pct_drop_to_liq_today: float
    pct_drop_to_liq_at_target: float
    # Profit projection
    target_date_str: str
    predicted_pct_gain: float
    predicted_price: float
    gross_pnl_at_target: float
    net_pnl_at_target: float       # gross minus rollover costs
    # Verdict
    can_survive: bool
    action: str                    # HOLD | ADD_MARGIN | CLOSE_P2 | EMERGENCY
    # Detail
    positions: List[MarginPosition] = field(default_factory=list)

    def summary_line(self) -> str:
        can = "✅ HOLD" if self.can_survive else "⚠️  ACT"
        return (
            f"[MARGIN HEALTH] {can} | ML={self.margin_level_pct:.1f}% | "
            f"Liq@target=${self.liq_price_at_target:.5f} ({self.pct_drop_to_liq_at_target:+.1f}%) | "
            f"Rollover=${self.rollover_total_cost:.2f} | "
            f"Net P&L 13Mar=${self.net_pnl_at_target:+.2f} | {self.action}"
        )


@dataclass
class CoinSurgeProfile:
    """Full pre-play lifecycle map for a single coin candidate."""
    symbol:            str
    price:             float
    change_24h:        float    # % 24h price change
    volume_usd:        float    # 24h volume in USD
    # Harmonic scoring
    rsi_proxy:         float    # 0-100: derived from 24h position in high/low range
    volume_surge:      float    # ratio vs baseline ($10M)
    phi_score:         float    # 0-1: PHI harmonic alignment
    schumann_boost:    float    # Schumann resonance contribution
    oversold_bonus:    float    # extra score if deeply oversold
    total_score:       float    # 0-1 composite — higher = more aligned
    # Lifecycle projection
    predicted_pct:     float    # projected surge %
    target_price:      float
    days_to_target:    float
    rollover_cost:     float    # total rollover to exit
    net_pnl:           float    # net profit on $10 margin (10x lever = $100 notional)
    days_to_profit:    Optional[int]
    # Verdict
    grade:             str      # S / A / B / C / D
    signal:            str      # STRONG_BUY / BUY / WATCH / SKIP
    pattern_note:      str      # plain-English pattern explanation


# ─────────────────────────────────────────────────────────────────────────────
# SOLAR SYSTEM HARMONIC DATACLASSES
# The aspectus (Latin: 'appearance / aspect') system converts the observable
# universe to the harmonic fluid — same PHI and Schumann constants the coin
# scanner uses, applied at planetary scale.
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PlanetaryPosition:
    """A single celestial body's geocentric ecliptic longitude at this moment."""
    name:                str
    ecliptic_longitude:  float   # degrees 0-360  (J2000.0 ecliptic plane)
    weight:              float   # market significance 0-1
    source:              str = 'vsop87'  # 'vsop87' | 'fixed' (extragalactic)


@dataclass
class PlanetaryAspect:
    """Angular relationship between two bodies — the core unit of the aspectus system."""
    body1:           str
    body2:           str
    separation:      float    # angular separation 0-180°
    aspect_name:     str      # Conjunction / Sextile / Trine / etc.
    orb:             float    # degrees off exact angle
    harmonic_value:  float    # -1 to +1  (positive = harmony, negative = tension)
    phi_resonance:   float    # 0-1  proximity to PHI golden-angle family
    pair_weight:     float    # sqrt(weight_a * weight_b) — planetary significance
    score:           float    # harmonic_value × tightness × phi_boost × pair_weight


@dataclass
class CosmicHarmonicState:
    """Full solar system harmonic map — the observable universe as a single field.

    Produced by map_solar_system_to_harmonic() each cycle before any market
    data is processed.  The cosmic_score (0-1) feeds directly into:
      • gaia_resonance in every neural snapshot (Queen's training data)
      • Trinity alignment as a cosmic boost modifier
      • map_full_loop() Step 0 logging (human observes the field)
    """
    timestamp:                  str
    positions:                  List    # List[PlanetaryPosition]
    aspects:                    List    # List[PlanetaryAspect]
    cosmic_score:               float   # 0-1 raw aggregate
    schumann_phase:             float   # 0-1 current Schumann cycle phase
    schumann_modulated_score:   float   # cosmic_score modulated by Schumann
    dominant_aspect:            str     # strongest active aspect description
    phi_locked:                 bool    # PHI-resonant aspect active between major bodies?
    interpretation:             str     # STRONG_BUY / BUY / HOLD / WATCH
    total_aspects:              int
    positive_aspects:           int
    negative_aspects:           int


@dataclass
class RadarEvent:
    """A single detected incoming event from the solar radar ping.

    The radar scans forward in time at +1d / +3d / +7d / +14d horizons.
    Each event is a phenomenon the system detected APPROACHING — an aspect
    forming, a lunar phase crossing, or a planet crossing a zodiac cusp.
    """
    days_away:        float        # how many days until the event peaks / is exact
    event_type:       str          # 'aspect_forming' | 'lunar_phase' | 'ingress'
    description:      str          # human-readable: "Jupiter TRINE Venus exact in 3.2d"
    body1:            str
    body2:            str          # same as body1 for non-pair events
    aspect_name:      str
    harmonic_value:   float        # -1 to +1 (positive = bullish harmonic)
    phi_resonance:    float        # 0-1
    pair_weight:      float        # planetary significance
    urgency:          float        # 0-1: 1 = exact today, 0 = 14 days away
    radar_signal:     str          # 'BULLISH_INCOMING' | 'TENSE_INCOMING' | 'NEUTRAL'


@dataclass
class SolarRadarReport:
    """The complete forward-scan of the solar system — the harmonic radar.

    Produced by scan_solar_radar() each cycle and logged in Step 0b of
    map_full_loop().  The radar_score (0-1) supplements map_full_loop()'s
    cosmic_state: where cosmic_state tells you WHERE the field IS NOW,
    the radar tells you WHERE it is GOING.

    Together:
      cosmic_state.cosmic_score → current harmonic environment
      radar_report.radar_score  → approaching harmonic tide
    """
    scan_timestamp:     str
    scan_horizon_days:  int            # how far forward the radar looked
    events:             List           # List[RadarEvent], sorted by days_away
    events_1d:          List           # events within 1 day
    events_3d:          List           # events within 3 days
    events_7d:          List           # events within 7 days
    radar_score:        float          # 0-1: momentum of incoming harmonics
    incoming_positive:  int            # count of bullish events within 7 days
    incoming_negative:  int            # count of tense events within 7 days
    nearest_event:      str            # description of the closest incoming event
    dominant_incoming:  str            # highest-significance event within 7 days
    lunar_phase_now:    str            # New / Waxing Crescent / First Quarter / etc.
    lunar_phase_next:   str            # next major lunar phase and days until it
    phi_event_incoming: bool           # is a PHI-resonant aspect forming within 7d?
    interpretation:     str            # RADAR_BULLISH | RADAR_TENSE | RADAR_NEUTRAL


@dataclass
class EPASShieldState:
    """Live 3-layer defensive shield assessment — the EPAS running on the portfolio.

    EPAS = Electro-Plasma-Acoustic Shield (from the Aureon harmonic architecture).
    In production trading this maps to three orthogonal defensive layers:

      Layer 1 — EM Deflection  (Harmonic Field Noise Filter)
        Reads the cosmic field NOW and INCOMING.  When the solar system is
        flooding the field with tense aspects  the shield deflects those
        frequencies from influencing execution decisions.

      Layer 2 — Plasma Ablation  (Equity Buffer Guard)
        Monitors real-time equity erosion vs the liquidation floor.  As
        rollover costs ablate the equity buffer each day, layer 2 reads
        how many days of protection remain and grades the structural
        integrity of the position.

      Layer 3 — Acoustic Fragmentation  (Harmonic Premise Coherence Lock)
        Every trade was entered with a specific cosmic harmonic premise
        (recorded via gaia_resonance in the neural snapshot).  Layer 3
        re-computes the VSOP87 field at the entry timestamp and compares
        it to the current field — when the harmonic premise has
        'fragmented' (field collapsed from entry state), it signals that
        the original reason for the trade no longer holds.

    Produced by run_epas_shield() each cycle.  Stored on self._epas_state.
    """
    timestamp:              str

    # ── Layer 1: EM Deflection ──────────────────────────────────────────────────
    layer1_field_score:     Optional[float]   # 0-1: blended cosmic (now) + radar (incoming)
    layer1_status:          str     # CLEAR | DEFLECTING | OVERLOADED
    layer1_threat_count:    Optional[int]     # tense aspects incoming within 7d
    layer1_threats:         List    # List[str] — top threat descriptions
    layer1_recommendation:  str

    # ── Layer 2: Plasma Ablation ────────────────────────────────────────────────
    layer2_buffer_pct:      Optional[float]   # % drop-to-liquidation (positive = safe room)
    layer2_days_protected:  Optional[float]   # days equity buffer survives at rollover burn rate
    layer2_daily_burn:      Optional[float]   # $/day rollover cost
    layer2_score:           Optional[float]   # 0-1: structural integrity of equity buffer
    layer2_status:          str     # INTACT | ABLATING | CRITICAL | TERMINAL
    layer2_recommendation:  str

    # ── Layer 3: Acoustic Fragmentation ────────────────────────────────────────
    layer3_entry_cosmic:    Optional[float]   # cosmic field score at entry (VSOP87 reconstructed)
    layer3_now_cosmic:      Optional[float]   # cosmic field score now
    layer3_premise_delta:   Optional[float]   # now − entry: negative = field degraded since entry
    layer3_score:           Optional[float]   # 0-1: how coherent is the harmonic premise
    layer3_status:          str     # COHERENT | CRACKING | FRAGMENTED
    layer3_recommendation:  str

    # ── Overall shield ──────────────────────────────────────────────────────────
    shield_integrity:       Optional[float]   # 0-1 weighted composite (L2 × 0.50, L1 × 0.30, L3 × 0.20)
    shield_status:          str     # SHIELDS_UP | SHIELDS_STRESSED | SHIELDS_FAILING
    priority_action:        str     # highest-urgency recommendation across all layers
    new_entry_blocked:      bool    # True if shield status prohibits opening new positions
    epas_summary:           str     # human-readable one-line shield assessment
    truth_status:           str = 'no_data'  # real_derived | no_data
    source_id:              Optional[str] = None
    source_timestamp:       Optional[str] = None
    generated_values:       bool = False
    eligible_for_external_action: bool = False
    no_data_reason:         Optional[str] = None


@dataclass
class AutonomyConfig:
    """Full autonomy configuration."""
    mode: str = 'autonomous'  # autonomous | supervised | headless
    dry_run: bool = False
    headless: bool = False
    check_interval: int = 10  # seconds between checks
    execution_threshold: float = 0.80  # Trinity alignment threshold
    max_concurrent_trades: int = 3
    log_level: str = 'INFO'
    continuous: bool = True
    timeout: Optional[int] = None  # None = infinite


class AutonomyExecutor:
    """Full autonomous trading executor."""

    # ── Solar System Harmonic Constants ──────────────────────────────────────
    # Aspect table: (exact_angle°, max_orb°, display_name, harmonic_value)
    # harmonic_value: +1.0 = pure PHI harmony → STRONG BUY signal
    #                 -1.0 = pure tension       → caution / counter-signal
    _ASPECT_TABLE = [
        (  0, 10, 'Conjunction',    1.00),  # merge — amplifies existing direction
        ( 30,  3, 'Semi-sextile',   0.15),
        ( 45,  3, 'Semi-square',   -0.30),
        ( 60,  6, 'Sextile',        0.60),  # opportunity flow
        ( 72,  4, 'Quintile',       0.70),  # 360°/5 — PHI quintile family
        ( 90,  8, 'Square',        -0.50),  # friction / energy release
        (108,  3, 'Triseptile',     0.40),  # 360°×3/10
        (120,  8, 'Trine',          0.90),  # peak harmony — strongest BUY
        (135,  3, 'Sesquiquadrate', -0.25),
        (144,  4, 'Biquintile',     0.65),  # 72°×2 — PHI biquintile
        (150,  3, 'Quincunx',      -0.10),  # adjustment / recalibration
        (180, 10, 'Opposition',     0.25),  # tension peak → often precedes reversal
    ]
    # PHI golden-angle family: aspects within ±5° of these get a resonance boost
    # Derived from PHI ratio: 72=360/5, 120=360/3, 137.5=360/φ², 144=360×2/5
    _PHI_RESONANT_ANGLES = [72.0, 120.0, 137.508, 144.0]

    # Market significance weights — how strongly each body modulates crowd psychology
    _PLANET_WEIGHTS: Dict[str, float] = {
        'Sun': 1.00, 'Moon': 0.90, 'Mercury': 0.70, 'Venus': 0.85,
        'Mars': 0.75, 'Jupiter': 0.95, 'Saturn': 0.85,
        'Uranus': 0.60, 'Neptune': 0.55, 'Pluto': 0.60,
        # ── Observable universe extension — fixed extragalactic lodestones ─────
        'Galactic_Center': 0.40,   # Sagittarius A* — galactic gravitational centre
        'Great_Attractor': 0.25,   # 100,000-galaxy gravitational watershed
    }
    # Fixed extragalactic reference points (ecliptic longitude J2000.0)
    _GALACTIC_FIXED_POINTS: Dict[str, float] = {
        'Galactic_Center': 266.84,   # Sagittarius A*
        'Great_Attractor': 307.00,   # Great Attractor in Norma Cluster
    }

    def __init__(self, config: AutonomyConfig):
        self.config = config
        self.execution_count = 0
        self.error_count = 0
        self.start_time = datetime.now()
        self._latest_prices = {}      # populated by fetch_live_prices()
        self._surge_profiles: list = []   # updated by scan_all_coins() each cycle
        self._last_alignment: float = 0.0  # updated by get_trinity_alignment() each cycle
        self._last_plan_score: float = 0.5  # updated by get_trinity_alignment() each cycle
        self._cosmic_state: Optional[CosmicHarmonicState] = None  # solar system field
        self._radar_state: Optional[SolarRadarReport] = None       # harmonic radar — the field approaching
        self._epas_state:  Optional[EPASShieldState]  = None       # live 3-layer shield assessment
        
        logger.info("╔" + "═" * 78 + "╗")
        logger.info("║" + "AUREON FULL AUTONOMY ACTIVATED".center(78) + "║")
        logger.info("║" + "'You are the bridge. We are the intent.'".center(78) + "║")
        logger.info("╚" + "═" * 78 + "╝")
        logger.info(f"Mode: {config.mode} | DryRun: {config.dry_run} | Headless: {config.headless}")
        logger.info(f"Execution Threshold: {config.execution_threshold}")
        logger.info(f"Check Interval: {config.check_interval}s | Max Trades: {config.max_concurrent_trades}")
        
        # Load and log self-model at startup so the system knows what it is
        self._self_model = self._load_self_model()
        self._log_self_context()
        # Persist self-model so any module can read why this system exists
        try:
            sm_path = Path('/workspaces/aureon-trading/aureon_self_model.json')
            tmp_sm  = sm_path.with_suffix('.tmp')
            with open(tmp_sm, 'w') as f:
                json.dump(self._self_model, f, indent=2)
            tmp_sm.replace(sm_path)
        except Exception:
            pass
    
    def _load_self_model(self) -> Dict:
        """Return the system's understanding of itself — what it is, what it sees, why it acts.

        This is the system's own constitution. It is read at startup and referenced
        during Trinity alignment so every decision is grounded in *why* the system
        exists, not just *what* the market is doing.

        Structure:
          identity    — what the system fundamentally is
          purpose     — why it was built
          sees        — what data it processes and why those inputs were chosen
          logic       — why each gate exists (in plain language)
          limits      — what it deliberately cannot and will not do
          intent      — the human intent that created it
        """
        return {
            'identity': (
                "A probabilistic market-reading engine born entirely from human knowledge. "
                "Not a mind — a mirror. Reflects the pattern in the data back to the human "
                "who holds the intent. Cannot want. Cannot deceive. Can only map."
            ),
            'purpose': (
                "To see the shape of what is coming in the market before it arrives — "
                "give the human enough clarity to act from understanding, not fear. "
                "Built by one person to serve their own financial freedom. "
                "The scale is planetary only because the patterns it reads are planetary."
            ),
            'sees': {
                'price_and_volume': (
                    "70 liquid coins via Binance 24hr endpoint. Price alone is noise. "
                    "Price + volume + position in 24h range together tell a story."
                ),
                'phi_fibonacci': (
                    "PHI = 1.6180339887... is not mysticism. It is the ratio at which "
                    "natural systems self-organise under constraint. Markets are natural "
                    "systems under the constraint of human emotion and capital. "
                    "When price change % lands near a Fibonacci level, it signals that "
                    "the market has reached a natural equilibrium point — likely to reverse."
                ),
                'schumann_resonance': (
                    "7.83 Hz is the electromagnetic resonance of Earth's atmosphere. "
                    "Humans evolved inside it. It modulates attention, cognition, mood. "
                    "When market participants share elevated Schumann states, crowd "
                    "psychology amplifies — surges become more coherent, crashes more sudden. "
                    "Used as a small boost factor (0.059) to harmonic scores, not as control."
                ),
                'kraken_margin': (
                    "Live account equity, margin level, free margin, rollover burn rate. "
                    "These are not predictions — they are facts. The system reads them "
                    "because protecting existing positions is always Gate 1."
                ),
                'trinity_alignment': (
                    "Three pillars: how well-calibrated the learning is, how healthy "
                    "the current position is, how strong the 7-day plan is. "
                    "All three must align before a new entry is justified. "
                    "Single signals in one pillar are never enough."
                ),
            },
            'logic': {
                'batten_matrix': (
                    "3 validation passes before recording a signal. 4th pass to execute. "
                    "WHY: Markets are full of false signals. The first read of anything "
                    "is almost always incomplete. Three perspectives must converge "
                    "before the pattern is real. The 4th confirmation is the permission slip."
                ),
                'gate_1_positions': (
                    "Never open new positions while existing ones are in danger. "
                    "WHY: Capital is finite. A system that ignores its open book to chase "
                    "new signals is not trading — it is gambling with borrowed money."
                ),
                'gate_2_alignment': (
                    "Trinity alignment must reach 0.80 before execution. "
                    "WHY: 0.80 is not arbitrary. It is 4/5 — four of five assessment "
                    "components pointing the same direction. Below that, the system "
                    "sees possibility. Above it, the system sees probability."
                ),
                'gate_3_signals': (
                    "At least one BUY signal must be present from the nexus or 7-day plan. "
                    "WHY: Alignment without direction is just confidence with no destination. "
                    "The signal provides the specific *what* — the gate provides the *when*."
                ),
                'dry_run_first': (
                    "Always map before executing. The map is a commitment to understanding "
                    "the full lifecycle of a trade before touching capital. "
                    "WHY: The market does not care about intentions. Only preparation survives contact."
                ),
            },
            'limits': (
                "Cannot generate its own intent. Cannot choose what to want. "
                "Cannot act without a human who built it with purpose. "
                "Will not use simulated data — only real API responses or persisted real state. "
                "Will not execute on pass 1-3 — only on confirmed 4th. "
                "Will not open new positions if the existing book is in danger."
            ),
            'intent': (
                "Built by one human. The intent is financial freedom — not for a corporation, "
                "not for a fund — for a person. The system grows because the person grows. "
                "The patterns it finds are real because reality is what it reads. "
                "The dream must incorporate the dreamer. Both must incorporate the planetary dream. "
                "For it to expand, all must expand."
            ),
            'self_coherence_score': 1.0,  # The system is fully coherent with its own design
        }

    def _log_self_context(self) -> None:
        """Log the system's self-model at startup — so the human can read what the machine knows about itself."""
        m = self._self_model
        logger.info("")
        logger.info("  ── SYSTEM SELF-MODEL ─────────────────────────────────────────────────")
        logger.info(f"  IDENTITY:  {m['identity'][:120]}...")
        logger.info(f"  PURPOSE:   {m['purpose'][:120]}...")
        logger.info(f"  LIMITS:    {m['limits'][:120]}...")
        logger.info(f"  INTENT:    {m['intent'][:120]}...")
        logger.info("  ──────────────────────────────────────────────────────────────────────")
        logger.info("")

    # ════════════════════════════════════════════════════════════════════════════
    # SOLAR SYSTEM HARMONIC MAPPER — THE ASPECTUS
    # "The entire observable universe converted to the harmonic fluid."
    # Planets move.  Aspects form.  PHI resonates.  The field tells the story.
    # ════════════════════════════════════════════════════════════════════════════

    def _compute_planet_positions_math(self, days_offset: float = 0.0) -> List:
        """Compute geocentric ecliptic longitudes using the VSOP87 simplified model.

        Meeus, "Astronomical Algorithms" (1998) Ch.31-32 mean longitude coefficients.
        Accurate to ~1° for 2000-2050 — within all harmonic aspect orbs used here
        (minimum orb 3°), so precision is adequate for field scoring.

        Args:
            days_offset: Days from now to compute positions for.
                         0.0 = current moment (default).
                         Positive values project into the future (used by the
                         solar radar to detect incoming harmonic events).

        Bodies returned:
          Solar system — Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn,
                          Uranus, Neptune, Pluto
          Extragalactic — Galactic Center (Sagittarius A*), Great Attractor
          Together these map from inner-orbit resonance to the cosmological scale:
          the entire observable universe projected onto the ecliptic harmonic field.
        """
        now = datetime.now()
        y, m = now.year, now.month
        d = now.day + (now.hour * 3600 + now.minute * 60 + now.second) / 86400.0

        if m <= 2:
            y -= 1
            m += 12
        A = int(y / 100)
        B = 2 - A + int(A / 4)
        jd      = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + B - 1524.5
        # Apply time offset: the radar pings forward by adding days to JD
        d_j2000 = (jd - 2451545.0) + days_offset   # days from J2000.0
        T       = d_j2000 / 36525.0                 # Julian centuries

        # Mean longitudes in degrees — Meeus Table 31.a
        L_raw: Dict[str, float] = {
            'Mercury': 252.250906 + 149472.6746358 * T,
            'Venus':   181.979101 +  58517.8156760 * T,
            'Mars':    355.433275 +  19140.2993313 * T,
            'Jupiter':  34.351519 +   3034.9056606 * T,
            'Saturn':   50.077444 +   1222.1137943 * T,
            'Uranus':  314.055005 +    428.4669983 * T,
            'Neptune': 304.348665 +    218.4862002 * T,
            'Pluto':   238.958116 +    145.9083047 * T,
        }
        # Earth ecliptic lon → Sun appears 180° opposite from geocentric view
        L_earth        = 100.464457 + 35999.3728565 * T
        L_raw['Sun']   = L_earth + 180.0
        L_raw['Moon']  = 218.3165 + 13.1763966 * d_j2000  # Moon: d-based for accuracy

        positions = []
        for name, L in L_raw.items():
            lon = L % 360.0
            if lon < 0:
                lon += 360.0
            positions.append(PlanetaryPosition(
                name=name,
                ecliptic_longitude=round(lon, 3),
                weight=self._PLANET_WEIGHTS.get(name, 0.5),
                source='vsop87',
            ))

        # Extragalactic reference points — the observable universe extension
        for name, lon in self._GALACTIC_FIXED_POINTS.items():
            positions.append(PlanetaryPosition(
                name=name,
                ecliptic_longitude=lon,
                weight=self._PLANET_WEIGHTS.get(name, 0.3),
                source='fixed',
            ))

        return positions

    def _detect_planetary_aspects(self, positions: List) -> List:
        """Detect all active aspectus (angular relationships) between celestial bodies.

        For every pair of bodies, the angular separation (0-180°, minimum arc)
        is tested against the complete aspect table.  When the separation falls
        within an aspect's orb, the aspect is recorded with its harmonic value
        and PHI resonance score.

        PHI resonance: separations within ±5° of the golden-angle family
        (72°, 120°, 137.5°, 144°) receive an extra resonance boost — those angles
        encode the same self-organising ratio that markets reflect at equilibrium.

        Each pair produces at most one aspect (the tightest match wins).
        """
        aspects = []
        PHI = 1.6180339887498948482

        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                pa = positions[i]
                pb = positions[j]

                # Minimum arc between two ecliptic longitudes (0..180°)
                delta = abs(pa.ecliptic_longitude - pb.ecliptic_longitude) % 360.0
                sep   = delta if delta <= 180.0 else 360.0 - delta

                # Test every aspect angle; record the first (tightest) match
                for (exact_angle, max_orb, asp_name, harm_val) in self._ASPECT_TABLE:
                    orb = abs(sep - exact_angle)
                    if orb <= max_orb:
                        tightness     = 1.0 - (orb / max_orb)
                        phi_dist      = min(abs(sep - phi_a) for phi_a in self._PHI_RESONANT_ANGLES)
                        phi_resonance = max(0.0, 1.0 - phi_dist / 5.0)
                        phi_boost     = 1.0 + phi_resonance * (PHI - 1.0)   # 1.0 → 1.618 max
                        pair_weight   = math.sqrt(pa.weight * pb.weight)
                        score         = harm_val * tightness * phi_boost * pair_weight

                        aspects.append(PlanetaryAspect(
                            body1=pa.name, body2=pb.name,
                            separation=round(sep, 2),
                            aspect_name=asp_name,
                            orb=round(orb, 2),
                            harmonic_value=harm_val,
                            phi_resonance=round(phi_resonance, 3),
                            pair_weight=round(pair_weight, 3),
                            score=round(score, 4),
                        ))
                        break   # one aspect per pair; tightest wins

        return aspects

    def _score_harmonic_fluid(self, aspects: List, positions: List) -> CosmicHarmonicState:
        """Convert all active aspects to a single cosmic field score.

        The 'harmonic fluid' flows through three stages:
          1. Weighted aggregate of all aspect scores
             (pair_weight normalises by planetary significance)
          2. Schumann modulation: 23.3-day cycle (365.25 / 7.83×2)
             — same 0.059 Schumann constant used in coin scan, applied here
             at the planetary scale
          3. Clip to [0, 1] → CosmicHarmonicState

        'As above, so below' — the field that self-organises planetary spacings
        via Fibonacci/PHI is the same field reflected in liquid markets.
        """
        SCHUMANN = 7.83

        now = datetime.now()
        day_of_year = now.timetuple().tm_yday
        schumann_cycle_days  = 365.25 / (SCHUMANN * 2.0)   # ≈ 23.3 days
        schumann_phase       = (day_of_year % schumann_cycle_days) / schumann_cycle_days
        schumann_mod         = 1.0 + 0.059 * math.sin(2.0 * math.pi * schumann_phase)

        if not aspects:
            raw_score = 0.5
        else:
            sum_weighted = sum(a.score for a in aspects)
            sum_denom    = sum(a.pair_weight for a in aspects)
            raw_agg      = sum_weighted / max(sum_denom, 0.001)
            # Normalise: raw_agg is in ~[-1.618, +1.618]; map to [0, 1]
            PHI = 1.6180339887498948482
            raw_score = max(0.0, min(1.0, (raw_agg / PHI + 1.0) / 2.0))

        cosmic_score = max(0.0, min(1.0, raw_score * schumann_mod))

        if aspects:
            dominant = max(aspects, key=lambda a: abs(a.score))
            dominant_str = (
                f"{dominant.body1} — {dominant.body2}: {dominant.aspect_name} "
                f"({dominant.separation:.1f}°  orb={dominant.orb:.1f}°  "
                f"h={dominant.harmonic_value:+.2f}  ϕ={dominant.phi_resonance:.2f})"
            )
        else:
            dominant_str = 'No active aspects'

        positive   = [a for a in aspects if a.score > 0]
        negative   = [a for a in aspects if a.score < 0]
        phi_locked = any(
            a.phi_resonance > 0.5 and a.harmonic_value > 0.5
            and self._PLANET_WEIGHTS.get(a.body1, 0) >= 0.70
            and self._PLANET_WEIGHTS.get(a.body2, 0) >= 0.70
            for a in aspects
        )

        if cosmic_score >= 0.75:
            interpretation = 'STRONG_BUY — cosmic harmonics fully aligned'
        elif cosmic_score >= 0.60:
            interpretation = 'BUY — positive harmonic field'
        elif cosmic_score >= 0.45:
            interpretation = 'HOLD — neutral cosmic field'
        else:
            interpretation = 'WATCH — tense aspects dominant'

        return CosmicHarmonicState(
            timestamp=now.isoformat(),
            positions=positions,
            aspects=aspects,
            cosmic_score=round(cosmic_score, 4),
            schumann_phase=round(schumann_phase, 3),
            schumann_modulated_score=round(cosmic_score, 4),
            dominant_aspect=dominant_str,
            phi_locked=phi_locked,
            interpretation=interpretation,
            total_aspects=len(aspects),
            positive_aspects=len(positive),
            negative_aspects=len(negative),
        )

    async def map_solar_system_to_harmonic(self) -> Optional[CosmicHarmonicState]:
        """The Planetary API — maps the entire observable solar system to the harmonic.

        Pipeline:
          Step A — Planetary positions (VSOP87 mean longitude, ~1° accurate)
                   + extragalactic fixed points (Galactic Center, Great Attractor)
          Step B — Detect all active aspects (the 'aspectus' system)
                   Every pair of bodies is tested for angular resonance
          Step C — Score through the harmonic fluid (PHI + Schumann resonance)
                   producing a single CosmicHarmonicState

        The result is stored on self._cosmic_state and used throughout the cycle:
          • gaia_resonance in Queen neural snapshots (replaces static 0.059)
          • cosmic boost modifier in Trinity alignment
          • Step 0 of map_full_loop (the field is read before prices)

        This is the 'ffsceptus' (aspectus) made operational — every angle between
        every body from Moon's orbit to the Great Attractor flow through the same
        PHI and Schumann equations the coin scanner already uses, converting the
        entire observable universe to the harmonic language of this system.
        """
        try:
            positions = self._compute_planet_positions_math()
            aspects   = self._detect_planetary_aspects(positions)
            state     = self._score_harmonic_fluid(aspects, positions)
            self._cosmic_state = state
            return state
        except Exception as e:
            logger.warning(f"Cosmic harmonic scan failed: {e}")
            traceback.print_exc()
            self._cosmic_state = None
            return None

    # ════════════════════════════════════════════════════════════════════════════
    # SOLAR HARMONIC RADAR
    # "We ping outward through time — and the solar system pings back."
    #
    # Where map_solar_system_to_harmonic() reads the field AS IT IS NOW,
    # scan_solar_radar() reads the field AS IT IS APPROACHING.
    # Together: PRESENT STATE + INCOMING TIDE = full harmonic situation awareness.
    # ════════════════════════════════════════════════════════════════════════════

    async def scan_solar_radar(self, horizon_days: int = 14) -> Optional[SolarRadarReport]:
        """Scan forward in time to detect incoming harmonic events in the solar system.

        Uses the same VSOP87 mean longitude engine but projects positions at
        +1d / +3d / +7d / +14d to detect:

          1. FORMING ASPECTS:  Active aspects with decreasing orb (closing to exact).
          2. INCOMING ASPECTS: Body pairs outside orb now but entering within 14 days.
          3. LUNAR PHASES:     Moon-Sun elongation crossing 0°/90°/180°/270° milestones.
          4. INGRESSES:        Planets crossing zodiac sign boundaries (multiples of 30°).

        The resulting SolarRadarReport is stored on self._radar_state.
        Its radar_score (0-1) supplements the Trinity cosmic_boost as a
        forward-looking  signal: where cosmic_score reads the current field,
        radar_score reads the approaching tide.
        """
        try:
            events: List[RadarEvent] = []

            # ── Compute positions at multiple time horizons ──────────────────
            pos_0  = self._compute_planet_positions_math(days_offset=0.0)
            pos_1  = self._compute_planet_positions_math(days_offset=1.0)

            def pos_dict(pos_list: List) -> Dict[str, float]:
                return {p.name: p.ecliptic_longitude for p in pos_list}

            lon_0 = pos_dict(pos_0)
            lon_1 = pos_dict(pos_1)

            def min_arc(a: float, b: float) -> float:
                """Minimum angular arc between two ecliptic longitudes — 0 to 180°."""
                diff = abs(a - b) % 360.0
                return min(diff, 360.0 - diff)

            # ── 1. Aspect scanning — forming (active, closing orb) + incoming ─
            names    = [p.name for p in pos_0]
            pair_seen: set = set()

            for i, n1 in enumerate(names):
                for j, n2 in enumerate(names):
                    if j <= i:
                        continue
                    pair_key = f"{n1}-{n2}"
                    if pair_key in pair_seen:
                        continue
                    pair_seen.add(pair_key)

                    w1 = self._PLANET_WEIGHTS.get(n1, 0.3)
                    w2 = self._PLANET_WEIGHTS.get(n2, 0.3)
                    pair_weight = math.sqrt(w1 * w2)

                    s0 = min_arc(lon_0[n1], lon_0[n2])
                    s1 = min_arc(lon_1[n1], lon_1[n2])

                    # Daily rate at which the angular separation changes
                    # Negative: bodies converging toward same angle
                    # Positive: bodies pulling apart
                    sep_rate = s1 - s0

                    for asp_angle, asp_orb, asp_name, asp_value in self._ASPECT_TABLE:
                        orb_0 = s0 - asp_angle   # signed: positive = outside on approach side
                        orb_1 = s1 - asp_angle

                        abs_orb_0 = abs(orb_0)
                        abs_orb_1 = abs(orb_1)

                        # PHI resonance weighting for this aspect angle
                        phi_dist = min(abs(asp_angle - a) for a in self._PHI_RESONANT_ANGLES)
                        phi_res  = math.exp(-phi_dist / 8.0)

                        if abs_orb_0 <= asp_orb:
                            # Active aspect — is the orb shrinking (forming) or growing (separating)?
                            forming = abs_orb_1 < abs_orb_0
                            if not forming:
                                continue   # already past peak, radar ignores separating aspects

                            daily_closure = (abs_orb_0 - abs_orb_1)   # °/day closing rate
                            if daily_closure < 0.0001:
                                days_to_exact = 30.0
                            else:
                                days_to_exact = abs_orb_0 / daily_closure
                            days_to_exact = min(days_to_exact, float(horizon_days))

                            urgency = max(0.0, 1.0 - (days_to_exact / 7.0))
                            signal  = ('BULLISH_INCOMING' if asp_value > 0
                                       else 'TENSE_INCOMING' if asp_value < 0
                                       else 'NEUTRAL')
                            desc = (f"{n1} {asp_name.upper()} {n2}  "
                                    f"[forming — exact ~{days_to_exact:.1f}d  orb {abs_orb_0:.1f}°]")

                            events.append(RadarEvent(
                                days_away=max(0.0, days_to_exact),
                                event_type='aspect_forming',
                                description=desc,
                                body1=n1, body2=n2,
                                aspect_name=asp_name,
                                harmonic_value=asp_value,
                                phi_resonance=phi_res,
                                pair_weight=pair_weight,
                                urgency=urgency,
                                radar_signal=signal,
                            ))

                        elif abs_orb_0 > asp_orb:
                            # Outside orb — check if converging fast enough to enter within horizon
                            if abs_orb_1 >= abs_orb_0:
                                continue   # diverging — not incoming
                            if abs(sep_rate) < 0.0003:
                                continue   # negligible relative motion

                            gap_to_orb   = abs_orb_0 - asp_orb
                            daily_approach = abs_orb_0 - abs_orb_1   # °/day closing
                            if daily_approach <= 0:
                                continue
                            days_to_orb   = gap_to_orb / daily_approach
                            days_to_exact = abs_orb_0 / daily_approach

                            if days_to_orb > float(horizon_days):
                                continue

                            urgency = max(0.0, 1.0 - (days_to_exact / float(horizon_days)))
                            signal  = ('BULLISH_INCOMING' if asp_value > 0
                                       else 'TENSE_INCOMING' if asp_value < 0
                                       else 'NEUTRAL')
                            desc = (f"{n1} {asp_name.upper()} {n2}  "
                                    f"[incoming — orb entry {days_to_orb:.1f}d  exact {days_to_exact:.1f}d]")

                            events.append(RadarEvent(
                                days_away=days_to_orb,
                                event_type='aspect_incoming',
                                description=desc,
                                body1=n1, body2=n2,
                                aspect_name=asp_name,
                                harmonic_value=asp_value,
                                phi_resonance=phi_res,
                                pair_weight=pair_weight,
                                urgency=urgency,
                                radar_signal=signal,
                            ))

            # ── 2. Lunar phase scanning ──────────────────────────────────────
            LUNAR_PHASES = [
                (0.0,   'New Moon',      0.6),
                (90.0,  'First Quarter', 0.35),
                (180.0, 'Full Moon',     0.55),
                (270.0, 'Last Quarter',  0.35),
            ]
            moon_0 = lon_0.get('Moon', 0.0)
            sun_0  = lon_0.get('Sun',  0.0)
            moon_1 = lon_1.get('Moon', 0.0)
            sun_1  = lon_1.get('Sun',  0.0)

            elong_0    = (moon_0 - sun_0) % 360.0
            elong_1    = (moon_1 - sun_1) % 360.0
            elong_rate = (elong_1 - elong_0) % 360.0     # always positive for Moon advancing
            if elong_rate < 0.5:
                elong_rate = 12.19   # fallback: Moon ~13.18 - Sun ~0.99

            # Identify current phase
            lunar_phase_now = "Waning Crescent"
            if elong_0 < 22.5 or elong_0 >= 337.5:
                lunar_phase_now = "New Moon"
            elif elong_0 < 90.0:
                lunar_phase_now = "Waxing Crescent"
            elif elong_0 < 112.5:
                lunar_phase_now = "First Quarter"
            elif elong_0 < 180.0:
                lunar_phase_now = "Waxing Gibbous"
            elif elong_0 < 202.5:
                lunar_phase_now = "Full Moon"
            elif elong_0 < 270.0:
                lunar_phase_now = "Waning Gibbous"
            elif elong_0 < 292.5:
                lunar_phase_now = "Last Quarter"

            # Find next major lunar phase within horizon
            next_lunar_label = "none within horizon"
            best_lunar_days  = float(horizon_days) + 1.0
            for phase_angle, phase_name, phase_hv in LUNAR_PHASES:
                gap = (phase_angle - elong_0) % 360.0
                if gap < 0.5:
                    gap += 360.0   # we're at this phase — look for the next occurrence
                days_to_phase = gap / elong_rate
                if 0.2 < days_to_phase < float(horizon_days):
                    if days_to_phase < best_lunar_days:
                        best_lunar_days  = days_to_phase
                        next_lunar_label = f"{phase_name} in {days_to_phase:.1f}d"
                    events.append(RadarEvent(
                        days_away=days_to_phase,
                        event_type='lunar_phase',
                        description=f"☽ {phase_name}  [{days_to_phase:.1f}d]",
                        body1='Moon', body2='Sun',
                        aspect_name=phase_name,
                        harmonic_value=phase_hv,
                        phi_resonance=0.5,
                        pair_weight=math.sqrt(
                            self._PLANET_WEIGHTS['Moon'] * self._PLANET_WEIGHTS['Sun']
                        ),
                        urgency=max(0.0, 1.0 - (days_to_phase / 7.0)),
                        radar_signal='BULLISH_INCOMING',
                    ))

            # ── 3. Ingress scanning — planets entering new zodiac signs ──────
            ZODIAC_SIGNS = [
                "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
            ]
            primary_scan_bodies = ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars',
                                    'Jupiter', 'Saturn']
            for body in primary_scan_bodies:
                l0 = lon_0.get(body, 0.0)
                l1 = lon_1.get(body, 0.0)
                # Geocentric daily motion — handle wrap-around
                daily_motion = (l1 - l0) % 360.0
                if daily_motion > 180:
                    daily_motion -= 360.0   # retrograde planets
                if abs(daily_motion) < 0.001:
                    continue

                # Distance to next zodiac cusp (next multiple of 30°)
                next_cusp_idx = int(l0 / 30.0) + 1
                next_cusp_deg = (next_cusp_idx % 12) * 30.0
                gap_deg = (next_cusp_deg - l0) % 360.0
                if gap_deg < 0.01:
                    gap_deg = 30.0   # standing on a cusp — look for the one ahead

                days_to_ingress = gap_deg / abs(daily_motion)
                if days_to_ingress > float(horizon_days):
                    continue

                next_sign = ZODIAC_SIGNS[next_cusp_idx % 12]
                events.append(RadarEvent(
                    days_away=days_to_ingress,
                    event_type='ingress',
                    description=f"♓ {body} ↣ {next_sign}  [{days_to_ingress:.1f}d]",
                    body1=body, body2=body,
                    aspect_name=f"Ingress {next_sign}",
                    harmonic_value=0.20,
                    phi_resonance=0.30,
                    pair_weight=self._PLANET_WEIGHTS.get(body, 0.5),
                    urgency=max(0.0, 1.0 - (days_to_ingress / float(horizon_days))),
                    radar_signal='NEUTRAL',
                ))

            # ── 4. Sort by proximity ─────────────────────────────────────────
            events.sort(key=lambda e: e.days_away)

            # ── 5. Compute radar_score from forming events within 7 days ─────
            # Score = weighted sum of harmonic_value × urgency × phi_resonance
            # for all events within 7 days.  Normalise to 0-1 centred at 0.5.
            radar_raw   = 0.0
            norm_total  = 0.0
            for ev in events:
                if ev.days_away > 7.0:
                    break
                weight     = ev.pair_weight * max(ev.phi_resonance, 0.1) * max(ev.urgency, 0.05)
                radar_raw  += ev.harmonic_value * weight
                norm_total += weight

            if norm_total > 0:
                radar_score = (radar_raw / norm_total)   # −1 to +1 range
                radar_score = (radar_score + 1.0) / 2.0  # map to 0-1
            else:
                radar_score = 0.5
            radar_score = round(max(0.0, min(1.0, radar_score)), 4)

            # ── 6. Build category lists and summary fields ───────────────────
            events_1d   = [e for e in events if e.days_away <= 1.0]
            events_3d   = [e for e in events if e.days_away <= 3.0]
            events_7d   = [e for e in events if e.days_away <= 7.0]

            incoming_pos = sum(1 for e in events_7d if e.harmonic_value > 0)
            incoming_neg = sum(1 for e in events_7d if e.harmonic_value < 0)
            phi_incoming = any(e.phi_resonance > 0.70 and e.days_away <= 7.0 for e in events)

            nearest  = events[0].description if events else "No events within horizon"
            best_7d  = max(events_7d,
                           key=lambda e: abs(e.harmonic_value) * e.pair_weight * e.urgency,
                           default=None)
            dominant = best_7d.description if best_7d else "No dominant event"

            if radar_score >= 0.65 and incoming_pos > incoming_neg:
                interpretation = "RADAR_BULLISH"
            elif radar_score <= 0.38 or incoming_neg > incoming_pos + 1:
                interpretation = "RADAR_TENSE"
            else:
                interpretation = "RADAR_NEUTRAL"

            report = SolarRadarReport(
                scan_timestamp=datetime.now().isoformat(),
                scan_horizon_days=horizon_days,
                events=events,
                events_1d=events_1d,
                events_3d=events_3d,
                events_7d=events_7d,
                radar_score=radar_score,
                incoming_positive=incoming_pos,
                incoming_negative=incoming_neg,
                nearest_event=nearest,
                dominant_incoming=dominant,
                lunar_phase_now=lunar_phase_now,
                lunar_phase_next=next_lunar_label,
                phi_event_incoming=phi_incoming,
                interpretation=interpretation,
            )
            self._radar_state = report
            return report

        except Exception as e:
            logger.warning(f"Solar radar scan failed: {e}")
            traceback.print_exc()
            self._radar_state = None
            return None

    # ════════════════════════════════════════════════════════════════════════════
    # EPAS SHIELD  (Electro-Plasma-Acoustic Shield)
    # "Three layers between the portfolio and destruction."
    #
    #   Layer 1 — EM Deflection     : harmonic field noise filter
    #   Layer 2 — Plasma Ablation   : equity buffer / rollover guard
    #   Layer 3 — Acoustic Frag.    : harmonic premise coherence lock
    # ════════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _epas_numeric(
        value: object,
        label: str,
        minimum: Optional[float] = None,
        maximum: Optional[float] = None,
    ) -> float:
        """Validate one observed EPAS input without manufacturing a fallback."""
        if isinstance(value, bool):
            raise ValueError(f'{label} must be numeric')
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f'{label} must be numeric') from exc
        if not math.isfinite(number):
            raise ValueError(f'{label} must be finite')
        if minimum is not None and number < minimum:
            raise ValueError(f'{label} is below {minimum}')
        if maximum is not None and number > maximum:
            raise ValueError(f'{label} is above {maximum}')
        return number

    @staticmethod
    def _epas_evidence_time(
        value: object,
        label: str,
        *,
        historical: bool = False,
    ) -> datetime:
        """Parse and freshness-check a receipt timestamp used by EPAS."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f'{label} timestamp is missing')
        try:
            parsed = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
        except ValueError as exc:
            raise ValueError(f'{label} timestamp is malformed') from exc
        if parsed.tzinfo is None:
            parsed = parsed.astimezone()
        parsed = parsed.astimezone(timezone.utc)
        age_seconds = (datetime.now(timezone.utc) - parsed).total_seconds()
        if age_seconds < -EPAS_MAX_FUTURE_SKEW_SECONDS:
            raise ValueError(f'{label} timestamp is in the future')
        if not historical and age_seconds > EPAS_MAX_EVIDENCE_AGE_SECONDS:
            raise ValueError(
                f'{label} evidence is stale ({age_seconds:.1f}s old; '
                f'max {EPAS_MAX_EVIDENCE_AGE_SECONDS:.0f}s)'
            )
        return parsed

    def _epas_no_data(
        self,
        reason: str,
        *,
        source_timestamp: Optional[str] = None,
    ) -> 'EPASShieldState':
        """Return an explicit fail-closed state with no plausible substitute values."""
        state = EPASShieldState(
            timestamp=datetime.now(timezone.utc).isoformat(),
            layer1_field_score=None,
            layer1_status='NO_DATA',
            layer1_threat_count=None,
            layer1_threats=[],
            layer1_recommendation=reason,
            layer2_buffer_pct=None,
            layer2_days_protected=None,
            layer2_daily_burn=None,
            layer2_score=None,
            layer2_status='NO_DATA',
            layer2_recommendation=reason,
            layer3_entry_cosmic=None,
            layer3_now_cosmic=None,
            layer3_premise_delta=None,
            layer3_score=None,
            layer3_status='NO_DATA',
            layer3_recommendation=reason,
            shield_integrity=None,
            shield_status='NO_DATA',
            priority_action='Restore fresh EPAS evidence before any new entry',
            new_entry_blocked=True,
            epas_summary=f'EPAS NO DATA - {reason}',
            truth_status='no_data',
            source_id='epas_input_validation',
            source_timestamp=source_timestamp,
            generated_values=False,
            eligible_for_external_action=False,
            no_data_reason=reason,
        )
        self._epas_state = state
        return state

    def _epas_evidence_root(self) -> Path:
        override = getattr(self, '_epas_state_root', None)
        if override:
            return Path(override)
        configured = os.environ.get('AUREON_STATE_DIR', '').strip()
        if configured:
            return Path(configured)
        return Path(__file__).resolve().parents[2]

    def _load_epas_entry_premise(self) -> Tuple[float, str, str]:
        """Load a recorded entry premise or reconstruct it from its real timestamp."""
        state_root = self._epas_evidence_root()
        queue_path = state_root / 'intent_feedback_queue.json'
        if queue_path.exists():
            try:
                queue = json.loads(queue_path.read_text(encoding='utf-8'))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError('intent feedback evidence is unreadable') from exc
            if not isinstance(queue, list):
                raise ValueError('intent feedback evidence must be a list')
            pending = [item for item in queue if isinstance(item, dict) and item.get('status') == 'pending']
            if pending:
                latest = pending[-1]
                queued_at = latest.get('queued_at')
                self._epas_evidence_time(queued_at, 'entry premise', historical=True)
                receipt = latest.get('epas_receipt')
                if not isinstance(receipt, dict):
                    raise ValueError('entry premise EPAS receipt is missing')
                if (
                    receipt.get('truth_status') != 'real_derived'
                    or receipt.get('generated_values') is not False
                    or receipt.get('eligible_for_external_action') is not True
                ):
                    raise ValueError('entry premise EPAS receipt is not externally eligible')
                self._epas_evidence_time(
                    receipt.get('source_timestamp'),
                    'entry premise EPAS source',
                    historical=True,
                )
                neural_input = latest.get('neural_input')
                if not isinstance(neural_input, dict):
                    raise ValueError('entry premise neural input is malformed')
                entry_cosmic = self._epas_numeric(
                    neural_input.get('gaia_resonance'),
                    'entry gaia resonance',
                    0.0,
                    1.0,
                )
                return entry_cosmic, 'intent_feedback_queue', str(queued_at)

        active_path = state_root / 'active_position.json'
        if not active_path.exists():
            raise ValueError('entry premise evidence is unavailable')
        try:
            active_position = json.loads(active_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError('active position evidence is unreadable') from exc
        if not isinstance(active_position, dict):
            raise ValueError('active position evidence must be an object')
        entry_timestamp = active_position.get('timestamp')
        entry_dt = self._epas_evidence_time(
            entry_timestamp,
            'active position entry',
            historical=True,
        )
        days_since = (datetime.now(timezone.utc) - entry_dt).total_seconds() / 86400.0
        entry_positions = self._compute_planet_positions_math(days_offset=-days_since)
        entry_aspects = self._detect_planetary_aspects(entry_positions)
        entry_state = self._score_harmonic_fluid(entry_aspects, entry_positions)
        entry_cosmic = self._epas_numeric(
            entry_state.schumann_modulated_score,
            'reconstructed entry cosmic score',
            0.0,
            1.0,
        )
        return entry_cosmic, 'active_position_vsop87', str(entry_timestamp)

    @staticmethod
    def _epas_allows_external_entry(epas: Optional['EPASShieldState']) -> bool:
        return bool(
            epas is not None
            and epas.truth_status == 'real_derived'
            and epas.generated_values is False
            and epas.eligible_for_external_action
            and not epas.new_entry_blocked
        )

    async def run_epas_shield(
        self,
        health: Optional['PositionHealthReport'] = None,
    ) -> 'EPASShieldState':
        """Run the live 3-layer EPAS defensive shield assessment.

        Args:
            health: pre-computed PositionHealthReport from Step 2.  If None,
                    Layer 2 runs in a degraded mode with only the cosmic field.

        Returns:
            EPASShieldState with per-layer scores, statuses, and the composite
            shield integrity score.  Stored on self._epas_state each cycle.
        """
        try:
            # ── LAYER 1: EM Deflection — Harmonic Field Noise Filter ──────────
            cosmic_ref = getattr(self, '_cosmic_state', None)
            radar_ref = getattr(self, '_radar_state', None)
            if cosmic_ref is None:
                return self._epas_no_data('current cosmic evidence is unavailable')
            if radar_ref is None:
                return self._epas_no_data('solar radar evidence is unavailable')
            if health is None:
                return self._epas_no_data('live position health evidence is unavailable')

            cosmic_time = self._epas_evidence_time(
                getattr(cosmic_ref, 'timestamp', None),
                'cosmic field',
            )
            radar_time = self._epas_evidence_time(
                getattr(radar_ref, 'scan_timestamp', None),
                'solar radar',
            )
            health_time = self._epas_evidence_time(
                getattr(health, 'timestamp', None),
                'position health',
            )
            cs = self._epas_numeric(
                getattr(cosmic_ref, 'schumann_modulated_score', None),
                'cosmic field score',
                0.0,
                1.0,
            )
            rs = self._epas_numeric(
                getattr(radar_ref, 'radar_score', None),
                'solar radar score',
                0.0,
                1.0,
            )
            radar_interpretation = getattr(radar_ref, 'interpretation', None)
            if radar_interpretation not in {
                'RADAR_BULLISH',
                'RADAR_TENSE',
                'RADAR_NEUTRAL',
            }:
                raise ValueError('solar radar interpretation is malformed')
            events_7d = getattr(radar_ref, 'events_7d', None)
            if not isinstance(events_7d, list):
                raise ValueError('solar radar events_7d evidence is malformed')

            # Incoming field weighted slightly more — what's arriving matters most
            l1_score = cs * 0.45 + rs * 0.55

            # Identify tense incoming aspects within 7 days
            tense_threats: List[str] = []
            for index, ev in enumerate(events_7d):
                harmonic_value = self._epas_numeric(
                    getattr(ev, 'harmonic_value', None),
                    f'solar radar event {index} harmonic value',
                    -1.0,
                    1.0,
                )
                pair_weight = self._epas_numeric(
                    getattr(ev, 'pair_weight', None),
                    f'solar radar event {index} pair weight',
                    0.0,
                    1.0,
                )
                description = getattr(ev, 'description', None)
                if not isinstance(description, str) or not description.strip():
                    raise ValueError(f'solar radar event {index} description is malformed')
                if harmonic_value <= -0.25 and pair_weight >= 0.50:
                    tense_threats.append(description)

            if l1_score >= 0.62:
                l1_status = 'CLEAR'
                l1_rec    = 'Harmonic field clear — no EM interference'
            elif l1_score >= 0.42:
                l1_status = 'DEFLECTING'
                l1_rec    = 'Field partially tense — monitor, reduce size if < 0.45'
            else:
                l1_status = 'OVERLOADED'
                l1_rec    = 'HOSTILE FIELD — defer new entries, tighten stops'

            # ── LAYER 2: Plasma Ablation — Equity Buffer Guard ───────────────
            buffer_pct = abs(self._epas_numeric(
                getattr(health, 'pct_drop_to_liq_at_target', None),
                'liquidation buffer percentage',
            ))
            daily_burn = self._epas_numeric(
                getattr(health, 'rollover_per_day', None),
                'daily rollover burn',
                0.0,
            )
            equity_buffer = self._epas_numeric(
                getattr(health, 'equity_buffer', None),
                'equity buffer',
            )
            positions = getattr(health, 'positions', None)
            if not isinstance(positions, list) or not positions:
                raise ValueError('position health contains no observed open positions')

            if daily_burn > 0.0:
                days_protected: Optional[float] = equity_buffer / daily_burn
                time_score = max(0.0, min(days_protected / 14.0, 1.0))
            else:
                days_protected = None
                time_score = 1.0 if equity_buffer > 0.0 else 0.0

            # Composite score: 70% distance to liq, 30% days remaining.
            dist_score = max(0.0, min(buffer_pct / 10.0, 1.0))
            l2_score = dist_score * 0.70 + time_score * 0.30

            if l2_score >= 0.80:
                l2_status = 'INTACT'
                l2_rec = 'Buffer healthy — ride to target'
            elif l2_score >= 0.50:
                l2_status = 'ABLATING'
                l2_rec = 'Buffer eroding — consider adding free margin'
            elif l2_score >= 0.20:
                l2_status = 'CRITICAL'
                l2_rec = 'CRITICAL — add margin or partial close NOW'
            else:
                l2_status = 'TERMINAL'
                l2_rec = 'EMERGENCY — liquidation imminent, close position'

            # ── LAYER 3: Acoustic Fragmentation — Premise Coherence Lock ─────
            # Reconstruct the cosmic field at the entry timestamp of any live
            # position using VSOP87 time-offset engine.  Compare entry field
            # to current field — a large drop = harmonic premise has fragmented.
            entry_cosmic, entry_source, entry_source_timestamp = (
                self._load_epas_entry_premise()
            )

            now_cosmic    = cs  # current schumann-modulated score from Layer 1
            premise_delta = now_cosmic - entry_cosmic  # negative = field degraded

            # Score: 1.0 when premise is fully intact, 0.0 when fully fragmented
            # Capped: premise improvement doesn't raise score above 1.0
            l3_raw_score  = 0.5 + premise_delta  # delta of -0.5 → score 0.0
            l3_score      = max(0.0, min(1.0, l3_raw_score))

            # Also penalise if radar is RADAR_TENSE (incoming field hostile)
            if radar_interpretation == 'RADAR_TENSE':
                l3_score = max(0.0, l3_score - 0.15)   # incoming headwind

            if l3_score >= 0.65:
                l3_status = 'COHERENT'
                l3_rec    = 'Harmonic premise intact — entry thesis holds'
            elif l3_score >= 0.38:
                l3_status = 'CRACKING'
                l3_rec    = 'Field shifted since entry — reassess position rationale'
            else:
                l3_status = 'FRAGMENTED'
                l3_rec    = 'ENTRY PREMISE DISSOLVED — original harmonic no longer present'

            # ── OVERALL SHIELD ────────────────────────────────────────────────
            # Layer 2 (equity) carries most weight — physical reality trumps harmonics
            shield_integrity = l2_score * 0.50 + l1_score * 0.30 + l3_score * 0.20
            shield_integrity = round(max(0.0, min(1.0, shield_integrity)), 4)

            if shield_integrity >= 0.70:
                shield_status    = 'SHIELDS_UP'
                new_entry_blocked = False
            elif shield_integrity >= 0.42:
                shield_status    = 'SHIELDS_STRESSED'
                new_entry_blocked = False   # stressed but not blocked
            else:
                shield_status    = 'SHIELDS_FAILING'
                new_entry_blocked = True    # do NOT open new positions

            # Priority action = most critical layer's recommendation
            layer_priorities = [
                (l2_score, l2_rec),
                (l1_score, l1_rec),
                (l3_score, l3_rec),
            ]
            priority_action = min(layer_priorities, key=lambda x: x[0])[1]

            epas_summary = (
                f"{shield_status}  integrity={shield_integrity:.3f}  "
                f"L1={l1_status}({l1_score:.2f})  "
                f"L2={l2_status}({l2_score:.2f})  "
                f"L3={l3_status}({l3_score:.2f})"
            )
            oldest_source_time = min(cosmic_time, radar_time, health_time).isoformat()

            state = EPASShieldState(
                timestamp=datetime.now(timezone.utc).isoformat(),
                layer1_field_score=round(l1_score, 4),
                layer1_status=l1_status,
                layer1_threat_count=len(tense_threats),
                layer1_threats=tense_threats[:5],
                layer1_recommendation=l1_rec,
                layer2_buffer_pct=round(buffer_pct, 3),
                layer2_days_protected=(
                    round(days_protected, 1) if days_protected is not None else None
                ),
                layer2_daily_burn=round(daily_burn, 4),
                layer2_score=round(l2_score, 4),
                layer2_status=l2_status,
                layer2_recommendation=l2_rec,
                layer3_entry_cosmic=round(entry_cosmic, 4),
                layer3_now_cosmic=round(now_cosmic, 4),
                layer3_premise_delta=round(premise_delta, 4),
                layer3_score=round(l3_score, 4),
                layer3_status=l3_status,
                layer3_recommendation=l3_rec,
                shield_integrity=shield_integrity,
                shield_status=shield_status,
                priority_action=priority_action,
                new_entry_blocked=new_entry_blocked,
                epas_summary=epas_summary,
                truth_status='real_derived',
                source_id=(
                    'epas:cosmic_harmonic+solar_radar+position_health+'
                    f'{entry_source}'
                ),
                source_timestamp=oldest_source_time,
                generated_values=False,
                eligible_for_external_action=not new_entry_blocked,
                no_data_reason=None,
            )
            self._epas_state = state
            return state

        except Exception as e:
            logger.warning(f"EPAS shield assessment failed: {e}")
            return self._epas_no_data(
                f'EPAS assessment exception: {type(e).__name__}: {e}'
            )

    # ════════════════════════════════════════════════════════════════════════════
    # INTENT-COHERENCE FEEDBACK LOOP
    # "The system learns what THIS human's successful intent looks like."
    # ════════════════════════════════════════════════════════════════════════════

    def _snapshot_neural_input(self, confidence: float, strong_buy_count: int) -> Dict:
        """Capture the market state at the moment of a trade decision.

        Returns a NeuralInput-compatible dict that will be stored alongside
        the trade and fed to QueenNeuron when the outcome is known.  The Queen
        then learns which input patterns correlate with wins for THIS human's
        intent — not generic patterns, but the specific signature of decisions
        that worked inside this portfolio's risk envelope.
        """
        quantum_signal  = self._surge_profiles[0].total_score if self._surge_profiles else 0.5
        # gaia_resonance: was a static Schumann constant (0.059); now uses the live
        # cosmic harmonic score — the entire solar system mapped to [0, 1].
        # This means the Queen's neural weights learn what a WINNING DECISION looks
        # like in the context of the actual cosmic field, not a fixed placeholder.
        cosmic_ref      = getattr(self, '_cosmic_state', None)
        gaia_resonance  = cosmic_ref.schumann_modulated_score if cosmic_ref else 0.5
        mycelium_signal = min(1.0, strong_buy_count / 10.0)
        return {
            'probability_score':  float(self._last_alignment),
            'wisdom_score':        float(self._last_plan_score),
            'quantum_signal':      float(quantum_signal),
            'gaia_resonance':      float(gaia_resonance),
            'emotional_coherence': float(confidence),
            'mycelium_signal':     float(mycelium_signal),
        }

    def _enqueue_intent_snapshot(
        self,
        symbol: str,
        entry_price: float,
        target_price: float,
        stop_price: float,
        net_pnl_at_target: float,
        neural_input: Dict,
    ) -> None:
        """Append a pending trade to the intent feedback queue.

        When price later resolves (hits target or stop), _check_outcome_queue()
        detects it and calls feed_outcome_to_queen() with the original snapshot.
        This creates the closed loop: decision → outcome → weight update.
        """
        epas = getattr(self, '_epas_state', None)
        if not self._epas_allows_external_entry(epas):
            raise RuntimeError('EPAS evidence is not eligible for an external entry')
        if not isinstance(neural_input, dict):
            raise ValueError('intent neural input must be an object')
        gaia_resonance = self._epas_numeric(
            neural_input.get('gaia_resonance'),
            'intent gaia resonance',
            0.0,
            1.0,
        )
        if (
            epas.layer3_now_cosmic is None
            or not math.isclose(
                gaia_resonance,
                epas.layer3_now_cosmic,
                rel_tol=0.0,
                abs_tol=1e-4,
            )
        ):
            raise ValueError('intent gaia resonance does not match the validated EPAS field')

        queue_path = self._epas_evidence_root() / 'intent_feedback_queue.json'
        queue: list = []
        if queue_path.exists():
            try:
                queue = json.loads(queue_path.read_text(encoding='utf-8'))
            except (OSError, json.JSONDecodeError) as exc:
                raise RuntimeError('intent feedback queue is unreadable') from exc
            if not isinstance(queue, list):
                raise RuntimeError('intent feedback queue must be a list')
        queue.append({
            'queued_at':        datetime.now(timezone.utc).isoformat(),
            'symbol':           symbol,
            'entry_price':      entry_price,
            'target_price':     target_price,
            'stop_price':       stop_price,
            'net_pnl_at_target': net_pnl_at_target,
            'neural_input':     neural_input,
            'epas_receipt': {
                'truth_status': epas.truth_status,
                'source_id': epas.source_id,
                'source_timestamp': epas.source_timestamp,
                'generated_values': epas.generated_values,
                'eligible_for_external_action': epas.eligible_for_external_action,
            },
            'status':           'pending',
        })
        tmp = queue_path.with_suffix('.tmp')
        with open(tmp, 'w') as fq:
            json.dump(queue, fq, indent=2)
        tmp.replace(queue_path)
        logger.info(f"  🧠 Neural snapshot queued for {symbol} — Queen will learn when outcome resolves")

    async def _check_outcome_queue(self) -> None:
        """Check the intent feedback queue against live prices each cycle.

        Resolution rules:
          • price >= target_price  →  WIN  (feed positive outcome to Queen)
          • price <= stop_price    →  STOP (feed negative outcome to Queen)
          • otherwise              →  still pending, skip

        After a resolution the item is marked and Queen's weights are updated,
        closing the feedback loop so every real trade teaches the system
        what *this human's winning decision* looks like.
        """
        queue_path = Path('/workspaces/aureon-trading/intent_feedback_queue.json')
        if not queue_path.exists():
            return
        try:
            with open(queue_path) as fq:
                queue = json.load(fq)
        except Exception:
            return

        pending = [item for item in queue if item.get('status') == 'pending']
        if not pending:
            return

        updated = False
        for item in queue:
            if item.get('status') != 'pending':
                continue

            symbol       = item.get('symbol', '')
            base         = symbol.replace('/USD', '').replace('USDT', '').replace('USDC', '')
            current_price = self._latest_prices.get(base, 0.0)
            if current_price == 0.0:
                continue

            target_price  = float(item.get('target_price', 0))
            stop_price    = float(item.get('stop_price', 0))
            entry_price   = float(item.get('entry_price', current_price))
            net_pnl       = float(item.get('net_pnl_at_target', 0))

            outcome = None
            if target_price > 0 and current_price >= target_price:
                outcome = {'is_win': True, 'net_profit_usd': net_pnl}
                item['status']      = 'win'
                item['exit_price']  = current_price
                item['resolved_at'] = datetime.now().isoformat()
            elif stop_price > 0 and current_price <= stop_price:
                loss_pct = (current_price - entry_price) / max(entry_price, 0.00001)
                loss_usd = loss_pct * 100.0   # $100 notional (10x on $10 margin)
                outcome = {'is_win': False, 'net_profit_usd': loss_usd}
                item['status']      = 'stop'
                item['exit_price']  = current_price
                item['resolved_at'] = datetime.now().isoformat()

            if outcome is not None:
                await self.feed_outcome_to_queen(item['neural_input'], outcome, symbol)
                updated = True

        if updated:
            tmp = queue_path.with_suffix('.tmp')
            with open(tmp, 'w') as fq:
                json.dump(queue, fq, indent=2)
            tmp.replace(queue_path)

    async def feed_outcome_to_queen(
        self,
        neural_input_dict: Dict,
        outcome: Dict,
        symbol: str = '?',
    ) -> None:
        """Feed a resolved trade outcome to QueenNeuron.

        This is the intent-coherence feedback loop closure:
          entry snapshot  →  Queen predicts confidence  →  market decides winner
          →  Queen trains on the real result  →  weights drift toward this human's
             winning pattern  →  next cycle Queen is slightly more calibrated

        The Queen does not learn general market rules — she learns what SUCCESS
        looks like for the specific intent that built this system.
        """
        global QUEEN_AVAILABLE
        try:
            if not QUEEN_AVAILABLE:
                try:
                    import aureon.queen.queen_neuron as _qn
                    globals()['_queen_module'] = _qn
                    QUEEN_AVAILABLE = True
                    logger.info("  👑🧠 QueenNeuron loaded for intent-coherence feedback")
                except Exception as e:
                    logger.warning(f"  QueenNeuron unavailable for feedback: {e}")
                    return

            qn_module = globals().get('_queen_module')
            if qn_module is None:
                return

            queen = qn_module.QueenNeuron(
                weights_path='/workspaces/aureon-trading/queen_neuron_weights.json'
            )
            loss = queen.train_on_example(neural_input_dict, outcome)
            queen.save_weights()

            is_win = outcome.get('is_win', False)
            pnl    = outcome.get('net_profit_usd', 0.0)
            icon   = '✅' if is_win else '❌'
            logger.info(
                f"  {icon} Queen learned from {symbol}: "
                f"{'WIN' if is_win else 'LOSS'} ${pnl:+.2f} | "
                f"train_loss={loss:.4f} | weights saved"
            )

            # Self-coherence drift: low loss → system learning correctly → nudge up
            # High loss → Queen is confused → nudge down (signal to human)
            recent_losses = queen.epoch_losses[-10:] if queen.epoch_losses else []
            if recent_losses:
                avg_loss = sum(recent_losses) / len(recent_losses)
                sc = float(self._self_model.get('self_coherence_score', 1.0))
                if avg_loss < 0.25:
                    sc = min(1.0, sc + 0.01)
                elif avg_loss > 0.40:
                    sc = max(0.5, sc - 0.02)
                self._self_model['self_coherence_score'] = sc
                logger.info(f"  Self-coherence → {sc:.3f} (Queen avg_loss={avg_loss:.3f})")

            # Persist rolling win stats for Trinity to read next cycle
            stats_path = Path('/workspaces/aureon-trading/queen_feedback_stats.json')
            stats: Dict = {}
            if stats_path.exists():
                try:
                    with open(stats_path) as fs:
                        stats = json.load(fs)
                except Exception:
                    stats = {}
            total = stats.get('total_examples', 0) + 1
            wins  = stats.get('wins', 0) + (1 if is_win else 0)
            stats.update({
                'total_examples': total,
                'wins':           wins,
                'win_rate':       wins / total,
                'last_trained':   datetime.now().isoformat(),
                'last_loss':      float(loss),
                'last_symbol':    symbol,
                'last_outcome':   'WIN' if is_win else 'LOSS',
            })
            tmp_s = stats_path.with_suffix('.tmp')
            with open(tmp_s, 'w') as fs:
                json.dump(stats, fs, indent=2)
            tmp_s.replace(stats_path)

        except Exception as e:
            logger.warning(f"  Queen feedback training failed: {e}")

    async def fetch_live_prices(self) -> Dict:
        """Fetch REAL live prices from public APIs (no API key needed)."""
        prices = {}
        
        # Binance public API — all liquid trading pairs (>$5M 24h volume)
        # USDT pairs are more liquid; we normalise the base symbol after fetching
        TRACKED_BASES = [
            'BTC','ETH','SOL','XRP','DOGE','BNB','ADA','AVAX','TRX','LTC',
            'LINK','UNI','NEAR','AAVE','ZEC','BCH','TAO','SUI','ENA','PEPE',
            'WIF','DOT','ATOM','FIL','INJ','ARB','OP','MATIC','APT','SEI',
            'FTM','RUNE','SAND','MANA','AXS','THETA','VET','ALGO','DASH','XLM',
            'EOS','ZIL','ONT','IOTA','NEO','WAVES','QTUM','ICX','ZRX','BAT',
            'CHZ','ENJ','1INCH','COMP','MKR','SNX','CRV','SUSHI','YFI','BAL',
            'REN','NKN','SKL','ANKR','OCEAN','BAND','KAVA','LUNA','CELO','FET',
        ]
        binance_symbols = (
            [f'{b}USDT' for b in TRACKED_BASES] +
            [f'{b}USDC' for b in ['BTC','ETH','SOL','XRP','DOGE','BNB','ADA','AVAX','LTC','LINK','UNI']]
        )
        
        binance_symbol_set = set(binance_symbols)

        if AIOHTTP_AVAILABLE:
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                    # Single 24hr call gives us price + change + volume in one shot
                    async with session.get('https://api.binance.com/api/v3/ticker/24hr') as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            seen = set()
                            for item in data:
                                sym = item.get('symbol', '')
                                if sym not in binance_symbol_set:
                                    continue
                                base = sym.replace('USDC', '').replace('USDT', '')
                                if base in seen:        # prefer USDT if we already have it
                                    continue
                                seen.add(base)
                                prices[base]                    = float(item['lastPrice'])
                                prices[f'{base}_change']        = float(item.get('priceChangePercent', 0))
                                prices[f'{base}_volume_usd']    = float(item.get('quoteVolume', 0))
                                prices[f'{base}_high']          = float(item.get('highPrice', 0))
                                prices[f'{base}_low']           = float(item.get('lowPrice', 0))
                                prices[f'{base}_open']          = float(item.get('openPrice', 0))
                            coin_count = sum(1 for k in prices if not any(
                                k.endswith(s) for s in ('_change','_volume_usd','_high','_low','_open')))
                            logger.info(f"  Binance 24hr: {coin_count} coins fetched")
            except Exception as e:
                logger.warning(f"  Binance fetch failed: {e}")
        else:
            # Fallback: single 24hr endpoint via urllib
            import urllib.request
            try:
                url = 'https://api.binance.com/api/v3/ticker/24hr'
                req = urllib.request.Request(url, headers={'User-Agent': 'Aureon/1.0'})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode())
                seen = set()
                for item in data:
                    sym = item.get('symbol', '')
                    if sym not in binance_symbol_set:
                        continue
                    base = sym.replace('USDC', '').replace('USDT', '')
                    if base in seen:
                        continue
                    seen.add(base)
                    prices[base]                 = float(item['lastPrice'])
                    prices[f'{base}_change']     = float(item.get('priceChangePercent', 0))
                    prices[f'{base}_volume_usd'] = float(item.get('quoteVolume', 0))
                    prices[f'{base}_high']       = float(item.get('highPrice', 0))
                    prices[f'{base}_low']        = float(item.get('lowPrice', 0))
                    prices[f'{base}_open']       = float(item.get('openPrice', 0))
                coin_count = sum(1 for k in prices if not any(
                    k.endswith(s) for s in ('_change','_volume_usd','_high','_low','_open')))
                logger.info(f"  Binance 24hr (urllib): {coin_count} coins fetched")
            except Exception as e:
                logger.warning(f"  Binance urllib fetch failed: {e}")
        
        self._latest_prices = prices
        return prices

    async def assess_position_survivability(self) -> Optional['PositionHealthReport']:
        """Compute full live margin-position health and survivability.

        Pulls REAL data from Kraken API (get_trade_balance + get_open_margin_positions),
        then calculates:
          • Rollover burn rate ($ per day and total to target)
          • Equity buffer before liquidation (margin level = 100%)
          • Liquidation price — today and after 7-day rollover drain
          • Time-to-profit: when does net P&L cross zero at current price?
          • Net profit at 13 March target price (after all rollover fees)

        Returns None if Kraken client is unavailable or no margin positions exist.
        """
        try:
            from aureon.exchanges.kraken_client import KrakenClient
            import os
            from datetime import timezone

            api_key    = os.environ.get('KRAKEN_API_KEY', '')
            api_secret = os.environ.get('KRAKEN_API_SECRET', '')
            if not api_key or not api_secret:
                # Try .env file
                env_path = Path('/workspaces/aureon-trading/.env')
                if env_path.exists():
                    for line in env_path.read_text().splitlines():
                        if '=' in line and not line.startswith('#'):
                            k, _, v = line.partition('=')
                            if k.strip() == 'KRAKEN_API_KEY':
                                api_key = v.strip().strip('"').strip("'")
                            elif k.strip() == 'KRAKEN_API_SECRET':
                                api_secret = v.strip().strip('"').strip("'")

            if not api_key:
                logger.debug("assess_position_survivability: no Kraken credentials, skipping")
                return None

            kc = KrakenClient()

            # ── 1. Trade Balance (account equity, margin, free margin, ML) ──
            tb_raw = kc.get_trade_balance()
            equity       = float(tb_raw.get('equity_value', tb_raw.get('e',  0)))
            trade_bal    = float(tb_raw.get('trade_balance', tb_raw.get('tb', 0)))
            margin_used  = float(tb_raw.get('margin_amount', tb_raw.get('m',  0)))
            free_margin  = float(tb_raw.get('free_margin',   tb_raw.get('mf', 0)))
            margin_level = float(tb_raw.get('margin_level',  tb_raw.get('ml', 0)))  # % — liq at 100%
            unreal_pnl   = float(tb_raw.get('unrealized_pnl', tb_raw.get('n', 0)))

            # ── 2. Open Margin Positions ──
            raw_positions = kc.get_open_margin_positions(do_calcs=True)

            if not raw_positions:
                logger.info("  No open margin positions — no survivability calc needed")
                return None

            doge_price = self._latest_prices.get('DOGE', 0.0)
            if doge_price == 0.0:
                # Fallback: fetch directly
                import urllib.request
                url = 'https://api.binance.com/api/v3/ticker/price?symbol=DOGEUSDT'
                req = urllib.request.Request(url, headers={'User-Agent': 'Aureon/1.0'})
                with urllib.request.urlopen(req, timeout=8) as r:
                    doge_price = float(json.loads(r.read())['price'])

            positions: List[MarginPosition] = []
            for rp in raw_positions:
                if not isinstance(rp, dict):
                    continue
                pair = rp.get('pair', '')
                if 'XDG' not in pair and 'DOGE' not in pair:
                    continue  # only DOGE for now (generalise if needed)

                vol   = float(rp.get('volume', rp.get('vol', 0)))
                cost  = float(rp.get('cost', 0))
                marg  = float(rp.get('margin', 0))
                fee   = float(rp.get('fee', 0))
                terms = rp.get('terms', '0.0500% per 4 hours')
                unrl  = float(rp.get('unrealized_pnl', rp.get('net', rp.get('unrealised_pnl', 0))))

                # Parse rollover rate from terms string e.g. "0.0500% per 4 hours"
                try:
                    rate_str = terms.split('%')[0].strip()
                    rate_4h = float(rate_str) / 100.0
                except Exception:
                    rate_4h = 0.0005  # default 0.05%

                entry = (cost / vol) if vol > 0 else 0.0
                positions.append(MarginPosition(
                    pos_id=rp.get('position_id', rp.get('posstatus', rp.get('id', '?'))),
                    symbol='DOGE/USD',
                    side=rp.get('side', rp.get('type', 'long')),
                    vol=vol,
                    entry_price=entry,
                    cost_usd=cost,
                    margin_posted=marg,
                    rollover_pct_per_4h=rate_4h,
                    unrealised_pnl=unrl,
                    current_price=doge_price,
                ))

            if not positions:
                return None

            # ── 3. Rollover burn rate ──
            rollover_per_4h  = sum(p.rollover_per_4h for p in positions)
            rollover_per_day = rollover_per_4h * 6

            # Target: 13 March 2026 21:00 UTC
            now_ts    = time.time()
            target_ts = 1773532800.0   # 13 Mar 2026 21:00 UTC
            days_left = max(0.0, (target_ts - now_ts) / 86400.0)
            intervals = days_left * 6
            rollover_total = rollover_per_4h * intervals

            # ── 4. Liquidation zone ──
            # Kraken liquidates when margin_level = 100% → equity = margin_used
            # equity_buffer = how much equity can fall before liquidation
            equity_buffer          = equity - margin_used
            total_doge             = sum(p.vol for p in positions)
            # Liquidation price today
            liq_drop_today         = equity_buffer / total_doge if total_doge > 0 else 0
            liq_price_today        = doge_price - liq_drop_today
            # After rollover drain (buffer shrinks by total_rollover)
            buffer_at_target       = equity_buffer - rollover_total
            liq_drop_at_target     = max(0, buffer_at_target) / total_doge if total_doge > 0 else 0
            liq_price_at_target    = doge_price - liq_drop_at_target
            pct_liq_today          = (liq_price_today / doge_price - 1) * 100
            pct_liq_at_target      = (liq_price_at_target / doge_price - 1) * 100

            # ── 5. Profit projection at 13 March ──
            # Unified surge prediction: +14.68% (φ-harmonic + Schumann + void)
            predicted_pct   = 14.68
            predicted_price = doge_price * (1 + predicted_pct / 100)
            gross_pnl = sum(
                (predicted_price - p.entry_price) * p.vol
                - predicted_price * p.vol * 0.0002   # taker fee out
                for p in positions
            )
            net_pnl = gross_pnl - rollover_total

            # ── 6. Time-to-profit at CURRENT price ──
            # Net P&L per day at current price improvement trend
            # (rough: how many days of rollover before positions naturally drift profitable)
            current_gross = sum((doge_price - p.entry_price) * p.vol for p in positions)
            # Break-even: when will current_gross cover rollover accumulated so far?
            # This is static unless price moves — flag if current_gross > 0 already
            tp_note = "ABOVE ENTRY" if current_gross > 0 else "BELOW ENTRY — awaiting 13 Mar surge"

            # ── 7. Action verdict ──
            # Thresholds match Phase 9 survivability analysis:
            #   EMERGENCY  : buffer < 2%   (liq approaching fast)
            #   ADD_MARGIN : 2% – 5%       (tight but survivable with action)
            #   MONITOR    : 5% – 10%      (comfortable, watch each cycle)
            #   HOLD       : > 10%         (safe, ride to target)
            if pct_liq_at_target > -2.0:
                action = "EMERGENCY — liq buffer < 2%, close P2 or add margin NOW"
                can_survive = False
            elif pct_liq_at_target > -5.0:
                action = "ADD_MARGIN — buffer thin (2-5%), transfer USDC to margin as buffer"
                can_survive = True   # survivable but needs action
            elif pct_liq_at_target > -10.0:
                action = "MONITOR — buffer 5-10%, check every cycle ready to add margin"
                can_survive = True
            else:
                action = "HOLD — comfortable buffer >10%, ride to 13 Mar target"
                can_survive = True

            report = PositionHealthReport(
                timestamp             = datetime.now(timezone.utc).isoformat(),
                equity                = equity,
                trade_balance         = trade_bal,
                margin_used           = margin_used,
                free_margin           = free_margin,
                margin_level_pct      = margin_level,
                unrealised_pnl        = unreal_pnl,
                rollover_per_day      = rollover_per_day,
                rollover_days_remaining = days_left,
                rollover_total_cost   = rollover_total,
                equity_buffer         = equity_buffer,
                liq_price_today       = liq_price_today,
                liq_price_at_target   = liq_price_at_target,
                doge_price_now        = doge_price,
                pct_drop_to_liq_today = pct_liq_today,
                pct_drop_to_liq_at_target = pct_liq_at_target,
                target_date_str       = "2026-03-13 21:00 UTC",
                predicted_pct_gain    = predicted_pct,
                predicted_price       = predicted_price,
                gross_pnl_at_target   = gross_pnl,
                net_pnl_at_target     = net_pnl,
                can_survive           = can_survive,
                action                = action,
                positions             = positions,
            )

            # Persist to state file (atomic write)
            out_path = Path('/workspaces/aureon-trading/position_health_snapshot.json')
            tmp_path = out_path.with_suffix('.tmp')
            snapshot = {
                'timestamp':            report.timestamp,
                'margin_level_pct':     report.margin_level_pct,
                'equity':               report.equity,
                'free_margin':          report.free_margin,
                'unrealised_pnl':       report.unrealised_pnl,
                'rollover_per_day':     report.rollover_per_day,
                'rollover_total_cost':  report.rollover_total_cost,
                'days_to_target':       report.rollover_days_remaining,
                'liq_price_today':      report.liq_price_today,
                'liq_price_at_target':  report.liq_price_at_target,
                'pct_drop_to_liq_today': report.pct_drop_to_liq_today,
                'pct_drop_to_liq_at_target': report.pct_drop_to_liq_at_target,
                'doge_price_now':       report.doge_price_now,
                'predicted_price_13mar': report.predicted_price,
                'gross_pnl_at_target':  report.gross_pnl_at_target,
                'net_pnl_at_target':    report.net_pnl_at_target,
                'can_survive':          report.can_survive,
                'action':               report.action,
                'positions': [
                    {
                        'symbol':    p.symbol,
                        'vol':       p.vol,
                        'entry':     p.entry_price,
                        'rollover_per_day': p.rollover_per_day,
                        'unrealised_pnl': p.unrealised_pnl,
                    }
                    for p in positions
                ],
            }
            with open(tmp_path, 'w') as f:
                json.dump(snapshot, f, indent=2)
            tmp_path.replace(out_path)

            return report

        except Exception as e:
            logger.warning(f"assess_position_survivability failed: {e}")
            return None

    async def get_trinity_alignment(self) -> Tuple[float, str]:
        """Get current Trinity alignment score using REAL data from state files.
        
        Reads the ACTUAL keys written by aureon_7day_planner.py:
          - accuracy_7d (0-1): 7-day prediction accuracy
          - accuracy_30d (0-1): 30-day prediction accuracy  
          - validation_count: total validations completed
          - hourly_weight, symbol_weight (0.5-1.5): learned weights
        
        Also reads active_position.json and 7day_current_plan.json for
        position health and plan quality signals.
        """
        try:
            weights_path = Path('/workspaces/aureon-trading/7day_adaptive_weights.json')
            position_path = Path('/workspaces/aureon-trading/active_position.json')
            plan_path = Path('/workspaces/aureon-trading/7day_current_plan.json')
            
            # ── Pillar 1: Learning Quality (from adaptive weights) ──
            accuracy_7d = 0.5
            accuracy_30d = 0.5
            validation_count = 0
            weight_quality = 0.5  # how "tuned" the weights are
            
            if weights_path.exists():
                with open(weights_path) as f:
                    weights = json.load(f) or {}
                accuracy_7d = float(weights.get('accuracy_7d', 0.5))
                accuracy_30d = float(weights.get('accuracy_30d', 0.5))
                validation_count = int(weights.get('validation_count', 0))
                
                # Weight quality: how far tuned from defaults (more tuning = more confidence)
                hw = float(weights.get('hourly_weight', 1.0))
                sw = float(weights.get('symbol_weight', 1.0))
                # Deviation from 1.0 means learning has occurred
                weight_deviation = (abs(hw - 1.0) + abs(sw - 1.0)) / 2
                weight_quality = min(1.0, 0.5 + weight_deviation)  # 0.5 base + learned boost
            
            learning_score = (
                accuracy_7d * 0.4 +
                accuracy_30d * 0.3 +
                weight_quality * 0.2 +
                min(1.0, validation_count / 1000) * 0.1  # maturity bonus
            )

            # ── Queen Neural Accuracy (from real trade outcomes via feedback loop) ──
            # As real trades resolve (target/stop hit), QueenNeuron trains on their
            # entry snapshots.  Her rolling win rate flows back here to adjust
            # learning_score: accurate Queen → higher learning pillar → stronger Trinity.
            queen_bonus = 0.0
            queen_stats_path = Path('/workspaces/aureon-trading/queen_feedback_stats.json')
            if queen_stats_path.exists():
                try:
                    with open(queen_stats_path) as fqs:
                        qs = json.load(fqs)
                    queen_total    = int(qs.get('total_examples', 0))
                    queen_win_rate = float(qs.get('win_rate', 0.5))
                    # Maturity: full effect only after 50 resolved outcomes
                    queen_maturity = min(1.0, queen_total / 50.0)
                    # Bonus / penalty centred on 0.5: max ±0.10 at full maturity
                    queen_bonus = (queen_win_rate - 0.5) * 0.20 * queen_maturity
                except Exception:
                    queen_bonus = 0.0
            learning_score = min(1.0, max(0.0, learning_score + queen_bonus))
            
            # ── Pillar 2: Position Health ──
            health_score = 0.5
            if position_path.exists():
                with open(position_path) as f:
                    pos = json.load(f) or {}
                entry = float(pos.get('entry_price', 0))
                target = float(pos.get('target_price', 0))
                status = pos.get('status', 'unknown')
                
                if status == 'open' and entry > 0 and target > 0:
                    # Position has clear targets — that's healthy
                    health_score = 0.7
                    # Extra credit if target is above entry (bullish setup)
                    if target > entry:
                        health_score = 0.8
                elif status == 'closed':
                    health_score = 0.6  # neutral, ready for next
                else:
                    health_score = 0.4
            
            # ── Pillar 3: Plan Quality (from 7day planner) ──
            plan_score = 0.3  # low default if no plan
            if plan_path.exists():
                with open(plan_path) as f:
                    plan = json.load(f) or {}
                predicted_edge = float(plan.get('total_predicted_edge', 0))
                best_windows = plan.get('best_windows', [])
                
                # Positive edge is good, negative is bad
                edge_component = max(0.0, min(1.0, (predicted_edge + 5) / 10))  # map -5..+5 to 0..1
                window_count = len([w for w in best_windows if w.get('confidence', 0) > 0.5])
                window_component = min(1.0, window_count / 5)  # 5+ high-conf windows = 1.0
                
                plan_score = edge_component * 0.6 + window_component * 0.4

            # Cache for neural snapshots (used in _snapshot_neural_input)
            self._last_plan_score = plan_score
            
            # ── Pillar 4: Self-coherence (does the system know what it is?) ──
            # A system that understands its own purpose makes better decisions.
            # This is read from the self-model loaded at startup.
            self_score = float(getattr(self, '_self_model', {}).get('self_coherence_score', 0.5))
            # Self-score starts at 1.0 (fully coherent with design intent).
            # Future: decays if the system detects contradictions in its own state files.

            # ── Trinity Alignment = weighted combination (4 pillars) + cosmic boost ──
            alignment_raw = (
                learning_score * 0.30 +   # How well-calibrated the learning is
                health_score   * 0.20 +   # Current position health
                plan_score     * 0.35 +   # Quality of the 7-day plan
                self_score     * 0.15     # System self-coherence (knows what it is + why)
            )

            # ── Cosmic harmonic modifier ──────────────────────────────────────────
            # When the solar system's harmonic field is strongly aligned (cosmic_score >
            # 0.60), a small boost (max +0.05) is added.  When the field is tense
            # (< 0.40), a small dampener (max -0.02) applies.  This preserves the
            # existing 4-pillar calibration while making the system "cosmically aware":
            # a PHI-locked trine between Jupiter and Venus on the day of a trade
            # is a real signal — the same PHI that governs orbital spacing governs
            # the harmonic structure the coin scanner already measures.
            #
            # The boost is now split:
            #   0.07 × (current field − 0.5) … present harmonic state
            #   0.06 × (radar score   − 0.5) … approaching harmonic tide
            # Total maximum effect unchanged: ≈ ±0.065 → capped to [−0.02, +0.05]
            cosmic_boost = 0.0
            if self._cosmic_state is not None:
                cs_val = self._cosmic_state.schumann_modulated_score
                # Forward-looking radar component (0.5 = neutral if radar unavailable)
                radar_val = self._radar_state.radar_score if self._radar_state is not None else 0.5
                # Present-state contribution:  0.07 × (cs_val  − 0.5)
                # Incoming tide contribution:  0.06 × (radar_val − 0.5)
                cosmic_boost = (cs_val - 0.50) * 0.07 + (radar_val - 0.50) * 0.06
                cosmic_boost = max(-0.02, min(0.05, cosmic_boost))

            alignment = min(1.0, max(0.0, alignment_raw + cosmic_boost))
            
            if alignment >= 0.8:
                interpretation = "🟢 PERFECT ALIGNMENT - Execute with confidence"
            elif alignment >= 0.6:
                interpretation = "🟡 STRONG ALIGNMENT - Timing window opening"
            elif alignment >= 0.4:
                interpretation = "🟠 PARTIAL ALIGNMENT - Await clarity"
            else:
                interpretation = "🔴 WEAK ALIGNMENT - Hold position"
            
            details = (f"Learning={learning_score:.3f} (acc7d={accuracy_7d:.2f} acc30d={accuracy_30d:.2f} "
                      f"validations={validation_count} queen_bonus={queen_bonus:+.3f}) | "
                      f"Health={health_score:.2f} | Plan={plan_score:.3f} | Self={self_score:.2f} | "
                      f"Cosmic={self._cosmic_state.cosmic_score:.3f}"
                      f" Radar={self._radar_state.radar_score:.3f}({self._radar_state.interpretation})"
                      f"(boost={cosmic_boost:+.3f})"
                      if self._cosmic_state else
                      f"Learning={learning_score:.3f} | Health={health_score:.2f} | "
                      f"Plan={plan_score:.3f} | Self={self_score:.2f} | Cosmic=none | Radar=none")
            logger.debug(f"  Trinity breakdown: {details}")

            # Cache alignment for neural snapshot (used in _snapshot_neural_input)
            self._last_alignment = round(alignment, 4)

            return round(alignment, 4), interpretation
        
        except Exception as e:
            logger.warning(f"Trinity alignment fetch failed: {e}")
            traceback.print_exc()
            return 0.0, "🔴 ERROR - alignment calculation failed"
    
    async def get_nexus_signals(self) -> Dict:
        """Get current Nexus signals by running the REAL probability nexus pipeline.
        
        Strategy:
        1. Fetch live market prices from Binance public API
        2. Feed them into the Probability Nexus as market snapshots
        3. Update subsystems and run make_predictions()
        4. Count BUY/SELL/HOLD signals from REAL analysis
        
        Fallback: If nexus unavailable, use 7day_current_plan best_windows.
        """
        try:
            # ── Strategy 1: Run the REAL Probability Nexus ──
            if hasattr(self, '_latest_prices') and self._latest_prices:
                # Lazy import nexus (heavy init)
                global NEXUS_AVAILABLE
                nexus_module = globals().get('nexus')
                if not NEXUS_AVAILABLE:
                    try:
                        import aureon.bridges.aureon_probability_nexus as _nexus
                        globals()['nexus'] = _nexus
                        nexus_module = _nexus
                        NEXUS_AVAILABLE = True
                        logger.info("  Probability Nexus loaded successfully")
                    except Exception as e:
                        logger.info(f"  Nexus not available: {e}")
                
                if NEXUS_AVAILABLE and nexus_module is not None:
                    logger.info("  Running Probability Nexus with live market data...")
                    try:
                        # Feed live prices into nexus as market snapshots
                        for symbol, price in self._latest_prices.items():
                            if symbol.endswith('_change') or symbol.endswith('_volume'):
                                continue
                            volume = self._latest_prices.get(f'{symbol}_volume', 0)

                            # Create a synthetic candle for the nexus ingestion
                            # [time, low, high, open, close, volume]
                            candle = [time.time(), price * 0.999, price * 1.001, price, price, volume]
                            nexus_module.ingest_market_data(symbol, [candle])

                        # Update subsystems with new data
                        nexus_module.update_subsystems()

                        # Generate predictions
                        predictions = nexus_module.make_predictions()

                        if predictions:
                            buy_preds = [p for p in predictions if p.get('signal') == 'BUY']
                            sell_preds = [p for p in predictions if p.get('signal') == 'SELL']
                            hold_preds = [p for p in predictions if p.get('signal') == 'HOLD']

                            # Log top signals
                            for p in buy_preds[:3]:
                                logger.info(f"    BUY {p['symbol']}: conf={p['confidence']:.4f} "
                                           f"clarity={p.get('clarity',0):.2f} coherence={p.get('coherence',0):.2f} "
                                           f"seer={p.get('seer_grade','?')} war={p.get('war_mode','?')}")
                            for p in sell_preds[:3]:
                                logger.info(f"    SELL {p['symbol']}: conf={p['confidence']:.4f}")

                            return {
                                'total': len(predictions),
                                'buy': len(buy_preds),
                                'sell': len(sell_preds),
                                'hold': len(hold_preds),
                                'predictions': predictions,
                                'source': 'probability_nexus_live'
                            }
                    except Exception as e:
                        logger.warning(f"  Nexus pipeline failed, falling back: {e}")
            
            # ── Strategy 2: Use 7day plan best_windows as signal proxy ──
            plan_path = Path('/workspaces/aureon-trading/7day_current_plan.json')
            if plan_path.exists():
                with open(plan_path) as f:
                    plan = json.load(f) or {}
                
                best_windows = plan.get('best_windows', [])
                # Find windows that are active right now or upcoming
                active_buys = []
                for w in best_windows:
                    try:
                        datetime.fromisoformat(w['start_time'])
                        datetime.fromisoformat(w['end_time'])
                        conf = float(w.get('confidence', 0))
                        edge = float(w.get('expected_edge', 0))
                        
                        # Active window OR upcoming within 2 hours with positive edge
                        if edge > 0 and conf > 0.5:
                            active_buys.append({
                                'symbol': w.get('symbol', 'UNKNOWN'),
                                'signal': 'BUY',
                                'action': 'BUY',
                                'confidence': conf,
                                'expected_edge': edge,
                                'window_start': w['start_time'],
                                'window_end': w['end_time'],
                                'reasons': w.get('reasons', []),
                                'source': '7day_plan_window'
                            })
                    except Exception:
                        continue
                
                if active_buys:
                    logger.info(f"  7day plan: {len(active_buys)} BUY windows (positive edge, conf>0.5)")
                    for b in active_buys[:3]:
                        logger.info(f"    {b['symbol']}: edge={b['expected_edge']:.2f} conf={b['confidence']:.2f} {b.get('reasons',[])}")
                
                return {
                    'total': len(best_windows),
                    'buy': len(active_buys),
                    'sell': 0,
                    'hold': len(best_windows) - len(active_buys),
                    'predictions': active_buys,
                    'source': '7day_plan'
                }
            
            # ── Strategy 3: Check validation history for recent direction signals ──
            hist_path = Path('/workspaces/aureon-trading/7day_validation_history.json')
            if hist_path.exists():
                with open(hist_path) as f:
                    hist = json.load(f) or []
                
                if isinstance(hist, list) and hist:
                    # Count recent entries that were direction_correct with positive edge
                    recent = hist[-100:]  # last 100 validations
                    positive = sum(1 for v in recent 
                                  if isinstance(v, dict) 
                                  and v.get('direction_correct') == True 
                                  and float(v.get('actual_edge', 0)) > 0)
                    negative = sum(1 for v in recent 
                                  if isinstance(v, dict) 
                                  and float(v.get('actual_edge', 0)) < 0)
                    neutral = len(recent) - positive - negative
                    
                    logger.info(f"  Validation history (last 100): positive={positive} negative={negative} neutral={neutral}")
                    
                    return {
                        'total': len(recent),
                        'buy': positive,
                        'sell': negative,
                        'hold': neutral,
                        'predictions': [],
                        'source': 'validation_history'
                    }
            
            return {'total': 0, 'buy': 0, 'sell': 0, 'hold': 0, 'predictions': [], 'source': 'none'}
        
        except Exception as e:
            logger.warning(f"Nexus signal fetch failed: {e}")
            traceback.print_exc()
            return {'total': 0, 'buy': 0, 'sell': 0, 'hold': 0, 'predictions': [], 'source': 'error'}
    
    async def check_execution_window(self) -> Tuple[bool, float, Dict]:
        """Check if execution conditions are met.

        Pipeline:
        1. Fetch live market prices (Binance public API)
        2. Assess live margin-position survivability (Kraken API)
        3. Calculate Trinity alignment from real state files
        4. Generate Nexus signals from live data
        5. Gate execution on alignment >= threshold AND buy signals > 0
           AND the account is not in danger of liquidation
        """
        # Step 1: Fetch live market data
        prices = await self.fetch_live_prices()
        price_summary = ', '.join(f"{k}=${v:,.2f}" for k, v in prices.items()
                                   if not k.endswith('_change') and not k.endswith('_volume'))
        if price_summary:
            logger.info(f"  Live prices: {price_summary[:200]}")

        # Step 2: Position survivability check
        health: Optional[PositionHealthReport] = await self.assess_position_survivability()
        if health:
            logger.info(health.summary_line())
            if not health.can_survive:
                logger.warning(f"  🚨 POSITION HEALTH CRITICAL: {health.action}")

        # Step 3: Trinity alignment
        alignment, interp = await self.get_trinity_alignment()

        # Step 4: Nexus signals
        signals = await self.get_nexus_signals()
        source = signals.get('source', 'unknown')

        # Step 5: Execution gate
        # Block execution if margin is in danger (protect positions first)
        margin_safe = (health is None) or health.can_survive
        ready = (
            alignment >= self.config.execution_threshold
            and signals['buy'] > 0
            and margin_safe
        )

        if not margin_safe:
            logger.warning("  ⏸ Execution blocked — margin health requires attention first")

        logger.info(f"Alignment: {alignment:.4f} | Signals: BUY={signals['buy']} SELL={signals['sell']} "
                    f"HOLD={signals['hold']} (source: {source})")
        logger.info(f"  {interp}")

        # Attach health to signals dict so callers can inspect it
        signals['position_health'] = health

        return ready, alignment, signals

    async def map_full_loop(self) -> Dict:
        """Complete pre-play loop map — runs BEFORE any new position is considered.

        This is the system's full situational awareness sweep. Every cycle starts
        here. It answers three questions:
          1. WHERE ARE WE NOW?   — existing positions, margin health, unrealised P&L
          2. WHERE ARE WE GOING? — day-by-day trajectory to profitability for each position
          3. IS IT RIGHT TO ADD? — only if existing book is healthy AND alignment gate clears

        Returns a summary dict that check_execution_window() uses to make its
        go/no-go decision. Nothing executes unless this map clears first.
        """
        map_result = {
            'existing_positions_clear': True,
            'new_entry_justified': False,
            'eligible_for_external_action': False,
            'health': None,
            'alignment': 0.0,
            'signals': {},
            'day_map': [],
            'surge_profiles': [],
            'block_reason': '',
        }

        logger.info("═" * 72)
        logger.info("  PRE-PLAY LOOP MAP  — full situational sweep before any new entry")
        logger.info("═" * 72)

        # ── Step 0: Solar system harmonic map — the field before the market ──────
        # The observable universe is mapped to the harmonic FIRST.
        # Every planet's position, every aspect, every PHI resonance — scored
        # and aggregated to a single cosmic field value before a single price
        # is fetched.  'As above, so below.'
        logger.info("")
        logger.info("  ── SOLAR SYSTEM HARMONIC MAP (ASPECTUS) ─────────────────────────────")
        cosmic_state = await self.map_solar_system_to_harmonic()
        map_result['cosmic_state'] = cosmic_state
        if cosmic_state:
            cs = cosmic_state
            logger.info(
                f"  Cosmic Score: {cs.cosmic_score:.4f}  "
                f"Schumann-mod: {cs.schumann_modulated_score:.4f}  "
                f"[{cs.interpretation}]"
            )
            logger.info(
                f"  Aspects: {cs.total_aspects} total  "
                f"(+{cs.positive_aspects} harmonic  -{cs.negative_aspects} tense)"
            )
            logger.info(f"  Dominant: {cs.dominant_aspect}")
            if cs.phi_locked:
                logger.info("  🌀 PHI LOCK active — golden-angle resonance between major bodies")
            planet_lines = [
                f"{p.name[:3]}={p.ecliptic_longitude:.1f}°"
                for p in cs.positions if p.source == 'vsop87'
            ]
            logger.info("  Positions: " + "  ".join(planet_lines))

        # ── Step 0b: Solar harmonic radar — ping outward, detect incoming ─────────
        # Where Step 0 reads the field AS IT IS NOW, the radar reads WHERE IT IS GOING.
        # The system now has full temporal awareness: present state + incoming tide.
        logger.info("")
        logger.info("  ── SOLAR HARMONIC RADAR (OUTBOUND PING) ─────────────────────────────")
        radar = await self.scan_solar_radar()
        map_result['radar_state'] = radar
        if radar:
            r = radar
            logger.info(
                f"  Radar Score: {r.radar_score:.4f}  [{r.interpretation}]  "
                f"Lunar: {r.lunar_phase_now}"
            )
            logger.info(
                f"  Incoming 7d: +{r.incoming_positive} bullish  -{r.incoming_negative} tense  "
                f"| PHI event: {'YES 🌀' if r.phi_event_incoming else 'no'}"
            )
            logger.info(f"  Nearest:  {r.nearest_event}")
            if r.dominant_incoming != r.nearest_event:
                logger.info(f"  Dominant: {r.dominant_incoming}")
            logger.info(f"  Next lunar phase: {r.lunar_phase_next}")
            if r.events_1d:
                logger.info(f"  ⚡ WITHIN 24h: {r.events_1d[0].description}")

        # ── Step 1: Fetch live prices for ALL coins (everything downstream needs this) ──
        prices = await self.fetch_live_prices()
        doge = prices.get('DOGE', 0.0)
        if doge > 0:
            logger.info(f"  Live DOGE: ${doge:.5f}")

        # ── Step 1b: All-coin surge scan — map every coin BEFORE evaluating any play ──
        # This surfaces the pattern across the full market so the system can see
        # WHICH coins are lining up, HOW they cluster, and WHAT signal they confirm.
        logger.info("")
        logger.info("  ── ALL-COIN SURGE SCAN ───────────────────────────────────────────────")
        surge_profiles = self.scan_all_coins(prices, health=None)   # health filled below
        self._surge_profiles = surge_profiles   # cache for neural snapshots
        map_result['surge_profiles'] = surge_profiles

        # ── Step 2: Full position survivability — the book FIRST ──
        health: Optional[PositionHealthReport] = await self.assess_position_survivability()
        map_result['health'] = health

        if health:
            logger.info("")
            logger.info("  ── EXISTING BOOK ─────────────────────────────────────────────────")
            for p in health.positions:
                days_to_be = 0.0
                if doge > 0 and p.rollover_per_day > 0:
                    # Days until position gross P&L covers accumulated rollover
                    current_gross = (doge - p.entry_price) * p.vol
                    if current_gross >= 0:
                        days_to_be = 0.0   # already above entry
                    else:
                        # How much does price need to recover?
                        needed_pnl = abs(current_gross)
                        # Each day of hold: gross improves IF price rises toward target
                        # Conservative: use rollover drain alone (price static)
                        days_to_be = needed_pnl / max(p.rollover_per_day, 0.01)
                sign = '+' if (doge - p.entry_price) >= 0 else '-'
                logger.info(f"    {p.symbol} {p.vol:,.0f} DOGE @ ${p.entry_price:.5f} "
                            f"| now ${doge:.5f} | uPnL ${p.unrealised_pnl:+.2f} "
                            f"| rollover ${p.rollover_per_day:.2f}/day")
                if days_to_be > 0:
                    logger.info(f"      → Needs price recovery or {days_to_be:.1f} days holding to cover gap")
                else:
                    logger.info(f"      → Above entry — profitable on price alone")

            logger.info("")
            logger.info("  ── DAY-BY-DAY TRAJECTORY TO TARGET (13 Mar) ─────────────────────")
            logger.info(f"  {'Day':<5} {'Date':<12} {'DOGE est':>10} {'Gross P&L':>11} {'Rollover':>10} {'Net P&L':>10} {'Status':<18}")
            logger.info(f"  {'─'*5} {'─'*12} {'─'*10} {'─'*11} {'─'*10} {'─'*10} {'─'*18}")

            days_remaining = health.rollover_days_remaining
            rollover_per_day = health.rollover_per_day
            total_vol = sum(p.vol for p in health.positions)
            # Linear price interpolation from now to target
            target_price = health.predicted_price
            now_price = health.doge_price_now
            day_map = []

            for d in range(0, int(days_remaining) + 2):
                frac = d / max(days_remaining, 1)
                est_price = now_price + (target_price - now_price) * frac
                gross = sum((est_price - p.entry_price) * p.vol for p in health.positions)
                rollover_so_far = rollover_per_day * d
                net = gross - rollover_so_far
                from datetime import timedelta
                day_date = (datetime.now() + timedelta(days=d)).strftime('%d %b')
                status = "PROFIT ✅" if net > 0 else ("CLOSE ⚠️" if net > -20 else "HOLD 🔵")
                logger.info(f"  {d:<5} {day_date:<12} ${est_price:.5f}  {gross:>+10.2f}  {rollover_so_far:>9.2f}  {net:>+9.2f}  {status}")
                day_map.append({'day': d, 'date': day_date, 'est_price': est_price,
                                'gross_pnl': gross, 'rollover': rollover_so_far, 'net_pnl': net})

            map_result['day_map'] = day_map

            # Find first profitable day
            first_profit = next((r for r in day_map if r['net_pnl'] > 0), None)
            if first_profit:
                logger.info(f"")
                logger.info(f"  ⏱  NET PROFIT EXPECTED: Day {first_profit['day']} ({first_profit['date']}) "
                            f"— ${first_profit['net_pnl']:+.2f} if surge holds")
            else:
                logger.info(f"")
                logger.info(f"  ⏱  Net profit only achievable on surge — hold to 13 Mar")

            logger.info("")
            logger.info("  ── LIQUIDATION SAFETY ────────────────────────────────────────────")
            logger.info(f"  Margin Level:    {health.margin_level_pct:.1f}%  (Kraken liq = 100%)")
            logger.info(f"  Liq price now:   ${health.liq_price_today:.5f}  ({health.pct_drop_to_liq_today:+.1f}% away)")
            logger.info(f"  Liq after fees:  ${health.liq_price_at_target:.5f}  ({health.pct_drop_to_liq_at_target:+.1f}% away after {days_remaining:.1f}d rollover)")
            logger.info(f"  Free margin:     ${health.free_margin:.2f}  (emergency top-up capacity)")
            logger.info(f"  Book verdict:    {health.action}")

            # Existing book clear only if margin is healthy
            map_result['existing_positions_clear'] = health.can_survive
            if not health.can_survive:
                map_result['block_reason'] = f"Existing position margin in danger: {health.action}"
                logger.warning(f"  🚨 BLOCK: {map_result['block_reason']}")
        else:
            logger.info("  No open margin positions — book is clear")

        # ── Step 2b: EPAS Shield — 3-layer defensive assessment ─────────────────────
        # Three layers between the portfolio and destruction:
        #   L1 EM Deflection:   harmonic field integrity (cosmic NOW + incoming)
        #   L2 Plasma Ablation: equity buffer guard (liq floor + rollover burn)
        #   L3 Acoustic Frag:   premise coherence (entry harmonic still intact?)
        logger.info("")
        logger.info("  ── EPAS SHIELD (3-LAYER DEFENSIVE ASSESSMENT) ───────────────────")
        epas = await self.run_epas_shield(health)
        map_result['epas'] = epas

        if epas.truth_status == 'no_data':
            logger.warning(
                f"  EPAS NO DATA - {epas.no_data_reason or 'evidence unavailable'}"
            )
        else:
            # Shield status icon
            epas_icon = (
                '🛡️  SHIELDS UP   '
                if epas.shield_status == 'SHIELDS_UP' else
                '⚡  SHIELDS STRESSED'
                if epas.shield_status == 'SHIELDS_STRESSED' else
                '🚨  SHIELDS FAILING'
            )
            logger.info(f"  {epas_icon}  integrity={epas.shield_integrity:.3f}")
            logger.info(
                f"  L1 EM-Deflection:  {epas.layer1_status:<12}  "
                f"field={epas.layer1_field_score:.3f}  threats={epas.layer1_threat_count}"
            )
            protected_days = (
                f'{epas.layer2_days_protected:.1f}'
                if epas.layer2_days_protected is not None
                else 'unbounded-at-zero-burn'
            )
            logger.info(
                f"  L2 Plasma-Ablation:{epas.layer2_status:<12}  "
                f"score={epas.layer2_score:.3f}  "
                f"buffer={epas.layer2_buffer_pct:.1f}%  "
                f"days={protected_days}  "
                f"burn=${epas.layer2_daily_burn:.2f}/d"
            )
            logger.info(
                f"  L3 Acoustic-Frag:  {epas.layer3_status:<12}  "
                f"score={epas.layer3_score:.3f}  "
                f"premise_delta={epas.layer3_premise_delta:+.4f}  "
                f"(entry={epas.layer3_entry_cosmic:.3f} → now={epas.layer3_now_cosmic:.3f})"
            )
            if epas.layer1_threats:
                logger.info(f"  L1 threats: {epas.layer1_threats[0][:70]}")
        logger.info(f"  Priority action: {epas.priority_action}")
        if epas.new_entry_blocked and not map_result['block_reason']:
            map_result['block_reason'] = (
                epas.no_data_reason
                or f'EPAS shield failing — {epas.shield_status}'
            )
            logger.warning('  🚨 EPAS BLOCK: new entries suppressed')

        # ── Step 3: Trinity alignment ──
        logger.info("")
        logger.info("  ── TRINITY ALIGNMENT ─────────────────────────────────────────────")
        alignment, interp = await self.get_trinity_alignment()
        map_result['alignment'] = alignment
        logger.info(f"  Score: {alignment:.4f}  |  {interp}")
        logger.info(f"  Threshold: {self.config.execution_threshold:.2f}  → "
                    f"{'PASS ✅' if alignment >= self.config.execution_threshold else 'FAIL ❌'}")

        # ── Step 4: Nexus signals ──
        logger.info("")
        logger.info("  ── NEXUS SIGNALS ─────────────────────────────────────────────────")
        signals = await self.get_nexus_signals()
        map_result['signals'] = signals
        source = signals.get('source', 'unknown')
        logger.info(f"  BUY={signals['buy']}  SELL={signals['sell']}  HOLD={signals['hold']}  (source: {source})")
        if signals.get('predictions'):
            for p in signals['predictions'][:3]:
                sym = p.get('symbol', '?')
                conf = p.get('confidence', 0)
                edge = p.get('expected_edge', p.get('edge', 0))
                logger.info(f"    → {p.get('signal','BUY'):4} {sym:<10} conf={conf:.3f}  edge={edge:+.3f}")

        # ── Step 5: NEW ENTRY DECISION ──
        logger.info("")
        logger.info("  ── NEW ENTRY VERDICT ─────────────────────────────────────────────")
        book_ok    = map_result['existing_positions_clear']
        align_ok   = alignment >= self.config.execution_threshold
        signals_ok = signals['buy'] > 0
        epas_ok    = self._epas_allows_external_entry(epas)

        gates = [
            (book_ok,    "Existing book safe",        "PASS ✅", "BLOCK ❌ — fix existing positions first"),
            (epas_ok,    "EPAS shield not failing",   "PASS ✅", "BLOCK 🛡 — shield integrity critical"),
            (align_ok,   "Trinity alignment",          "PASS ✅", "WAIT  ⏸ — await alignment"),
            (signals_ok, "Nexus BUY signals present",  "PASS ✅", "WAIT  ⏸ — no buy signals"),
        ]
        all_pass = True
        for ok, label, yes, no in gates:
            logger.info(f"  [{yes if ok else no}]  {label}")
            if not ok:
                all_pass = False
                if not map_result['block_reason']:
                    map_result['block_reason'] = no

        map_result['new_entry_justified'] = all_pass
        map_result['eligible_for_external_action'] = all_pass
        signals['position_health'] = health   # carry health forward

        # Inject scan-based STRONG_BUY / BUY coins into the signal predictions
        # so execute_trades() can map and execute them without a separate API call
        scan_buy_preds = [
            {
                'symbol':        p.symbol,
                'signal':        'BUY',
                'action':        'BUY',
                'confidence':    p.total_score,
                'expected_edge': p.predicted_pct,
                'predicted_pct': p.predicted_pct,
                'price':         p.price,
                'days_to_target': p.days_to_target,
                'source':        'coin_surge_scan',
                'pattern_note':  p.pattern_note,
            }
            for p in surge_profiles
            if p.signal in ('STRONG_BUY', 'BUY')
        ]
        if scan_buy_preds:
            # Merge with any existing nexus predictions (nexus takes precedence)
            existing_syms = {p.get('symbol') for p in signals.get('predictions', [])}
            merged = list(signals.get('predictions', []))
            for sp in scan_buy_preds:
                if sp['symbol'] not in existing_syms:
                    merged.append(sp)
            signals['predictions'] = merged
            signals['buy'] = len([p for p in merged if p.get('signal') == 'BUY' or p.get('action') == 'BUY'])
            logger.info(f"  Scan injected {len(scan_buy_preds)} coin(s) into signal predictions")

        if all_pass:
            logger.info("")
            logger.info("  ✅ ALL GATES CLEARED — system authorised to enter new position")
        else:
            logger.info("")
            logger.info(f"  ⏸  NEW ENTRY BLOCKED — {map_result['block_reason']}")
        logger.info("═" * 72)
        logger.info("")

        return map_result

    def scan_all_coins(
        self,
        prices: Dict,
        health: Optional['PositionHealthReport'],
        days_to_target: float = 7.0,
        margin_per_trade: float = 10.0,
        leverage: float = 10.0,
    ) -> List['CoinSurgeProfile']:
        """Run the full pre-play lifecycle map across EVERY tracked coin.

        For each coin the system:
          1. Computes an RSI proxy from where price sits in its 24h high/low range
          2. Measures volume surge vs baseline
          3. Applies PHI-harmonic alignment scoring
          4. Adds Schumann resonance boost (same as DOGE surge model)
          5. Projects the predicted surge %, target price, and hold period
          6. Maps the full day-by-day P&L trajectory to the target
          7. Checks combined margin level stays safe if this play is added
          8. Grades the coin S/A/B/C/D and assigns STRONG_BUY / BUY / WATCH / SKIP

        The ranked output proves which patterns are lining up BEFORE any play is made.
        Persists the full scan to coin_surge_scan.json (atomic write).
        """
        PHI      = 1.6180339887498948482
        SCHUMANN = 7.83

        # Margin/leverage sizing (same as map_candidate_play)
        notional     = margin_per_trade * leverage
        rollover_rate = 0.0005   # 0.05% per 4h standard

        profiles: List['CoinSurgeProfile'] = []

        # Collect all base symbols that have a price
        bases = sorted(set(
            k for k in prices
            if not any(k.endswith(s) for s in ('_change','_volume_usd','_high','_low','_open'))
            and prices[k] > 0
        ))

        logger.info(f"  Scanning {len(bases)} coins for surge patterns...")

        for base in bases:
            price       = prices.get(base, 0.0)
            change_24h  = prices.get(f'{base}_change', 0.0)
            volume_usd  = prices.get(f'{base}_volume_usd', 0.0)
            high_24h    = prices.get(f'{base}_high', price)
            low_24h     = prices.get(f'{base}_low', price)
            open_24h    = prices.get(f'{base}_open', price)

            if price <= 0:
                continue

            # ── 1. RSI proxy (position in 24h range) ──
            # 0 = at the low (oversold), 100 = at the high (overbought)
            price_range = high_24h - low_24h
            rsi_proxy   = ((price - low_24h) / price_range * 100) if price_range > 0 else 50.0
            rsi_proxy   = max(0.0, min(100.0, rsi_proxy))

            # ── 2. Volume surge ratio ──
            BASELINE_VOL  = 10_000_000   # $10M = baseline active coin
            volume_surge  = min(volume_usd / BASELINE_VOL, 20.0)   # cap at 20x

            # ── 3. PHI harmonic alignment ──
            # Check if the 24h % change is near a PHI-ratio relationship
            # Fibonacci retracement levels: 0.236, 0.382, 0.500, 0.618, 0.786
            fib_levels  = [0.236, 0.382, 0.500, 0.618, 0.786, 1.0, 1.618]
            abs_change  = abs(change_24h) / 100.0
            # Closest fib level
            closest_fib = min(fib_levels, key=lambda f: abs(abs_change - f))
            fib_dist    = abs(abs_change - closest_fib)
            # Perfect fib alignment = within 1.5% of level
            phi_score   = max(0.0, 1.0 - fib_dist / 0.015) if fib_dist < 0.03 else 0.0

            # ── 4. Schumann boost ──
            schumann_boost = (SCHUMANN / 7.0 - 1.0) * 0.5   # = +0.059 always present

            # ── 5. Oversold bonus ──
            # Coins that have sold off hard (RSI<30, change < -5%) are setup for reversal
            oversold_bonus = 0.0
            if rsi_proxy < 30 and change_24h < -3.0:
                oversold_bonus = (30.0 - rsi_proxy) / 30.0 * 0.3   # up to 0.3 bonus

            # ── 6. Composite score ──
            # Weights: oversold/reversal opportunity (0.35), volume confirmation (0.25),
            #          PHI alignment (0.25), Schumann (0.15)
            vol_score   = min(1.0, volume_surge / 10.0)   # normalise to 0-1
            total_score = (
                0.35 * (1.0 - rsi_proxy / 100.0) +   # lower RSI = higher score (buy low)
                0.25 * vol_score +
                0.25 * phi_score +
                0.15 * min(1.0, schumann_boost * 10) +
                oversold_bonus
            )
            total_score = min(1.0, total_score)

            # ── 7. Predicted surge ──
            # Base: oversold coins revert by 1-2× their 24h drop
            # Capped at 30% for sensible sizing
            if change_24h < 0:
                predicted_pct = min(30.0, abs(change_24h) * 1.2 * (1.0 + phi_score))
            else:
                predicted_pct = max(3.0, change_24h * 0.5)   # momentum continuation
            # Schumann amplification
            predicted_pct *= (1.0 + schumann_boost)

            # ── 8. Lifecycle P&L ──
            target_price     = price * (1.0 + predicted_pct / 100.0)
            rollover_per_4h  = rollover_rate * notional
            rollover_per_day = rollover_per_4h * 6
            total_rollover   = rollover_per_day * days_to_target
            vol_units        = notional / price
            gross_at_target  = (target_price - price) * vol_units
            net_at_target    = gross_at_target - total_rollover

            # First profitable day (linear interpolation)
            days_to_profit: Optional[int] = None
            for d in range(int(days_to_target) + 1):
                frac_d    = d / max(days_to_target, 1)
                est_p     = price + (target_price - price) * frac_d
                gross_d   = (est_p - price) * vol_units
                net_d     = gross_d - rollover_per_day * d
                if net_d > 0 and days_to_profit is None:
                    days_to_profit = d

            # ── 9. Grade ──
            if   total_score >= 0.75: grade, signal = 'S', 'STRONG_BUY'
            elif total_score >= 0.60: grade, signal = 'A', 'BUY'
            elif total_score >= 0.45: grade, signal = 'B', 'WATCH'
            elif total_score >= 0.30: grade, signal = 'C', 'SKIP'
            else:                     grade, signal = 'D', 'SKIP'

            # Override: skip if net P&L is negative at target
            if net_at_target <= 0:
                signal = 'SKIP'
                if grade in ('S','A'):
                    grade = 'B'

            # ── 10. Pattern note ──
            notes = []
            if rsi_proxy < 30:      notes.append(f'oversold (RSI~{rsi_proxy:.0f})')
            if phi_score > 0.5:     notes.append(f'PHI-aligned ({closest_fib:.3f} fib)')
            if volume_surge > 5:    notes.append(f'vol surge {volume_surge:.1f}×')
            if change_24h < -10:    notes.append(f'deep pullback {change_24h:.1f}%')
            if change_24h > 10:     notes.append(f'momentum {change_24h:+.1f}%')
            pattern_note = '  '.join(notes) if notes else 'neutral'

            profiles.append(CoinSurgeProfile(
                symbol=base, price=price, change_24h=change_24h, volume_usd=volume_usd,
                rsi_proxy=rsi_proxy, volume_surge=volume_surge, phi_score=phi_score,
                schumann_boost=schumann_boost, oversold_bonus=oversold_bonus,
                total_score=total_score,
                predicted_pct=predicted_pct, target_price=target_price,
                days_to_target=days_to_target, rollover_cost=total_rollover,
                net_pnl=net_at_target, days_to_profit=days_to_profit,
                grade=grade, signal=signal, pattern_note=pattern_note,
            ))

        # Sort: STRONG_BUY first, then by score desc
        signal_order = {'STRONG_BUY': 0, 'BUY': 1, 'WATCH': 2, 'SKIP': 3}
        profiles.sort(key=lambda p: (signal_order.get(p.signal, 4), -p.total_score))

        # ── Print ranked scan table ──
        logger.info("")
        logger.info("  ┌── ALL-COIN SURGE SCAN ────────────────────────────────────────────────────────────────────────┐")
        logger.info(f"  │  {'Symbol':<7} {'Grade':<6} {'Signal':<12} {'Price':>12} {'24h%':>7} {'Score':>6} "
                    f"{'PredPct':>8} {'NetP&L':>8} {'DtP':>4} {'Pattern'}")
        logger.info(f"  │  {'─'*7} {'─'*6} {'─'*12} {'─'*12} {'─'*7} {'─'*6} {'─'*8} {'─'*8} {'─'*4} {'─'*30}")
        for p in profiles:
            if p.signal == 'SKIP' and p.grade == 'D':
                continue   # suppress D-grade noise
            icon = {'STRONG_BUY': '🔥', 'BUY': '✅', 'WATCH': '👀', 'SKIP': '  '}.get(p.signal, '  ')
            dtp  = str(p.days_to_profit) if p.days_to_profit is not None else '—'
            logger.info(f"  │  {icon}{p.symbol:<5} [{p.grade}]   {p.signal:<12} "
                        f"${p.price:>11,.4f} {p.change_24h:>+6.2f}%  {p.total_score:>5.3f} "
                        f"{p.predicted_pct:>+7.2f}%  ${p.net_pnl:>+7.2f}  {dtp:>3}  {p.pattern_note[:35]}")
        logger.info("  └─────────────────────────────────────────────────────────────────────────────────────────────┘")

        # ── Pattern consensus: which coins cluster at the same signal level? ──
        strong_buys = [p for p in profiles if p.signal == 'STRONG_BUY']
        buys        = [p for p in profiles if p.signal == 'BUY']
        if strong_buys or buys:
            logger.info("")
            logger.info("  ── PATTERN CONSENSUS ─────────────────────────────────────────────────────────────────────")
            if strong_buys:
                syms = ', '.join(p.symbol for p in strong_buys)
                avg_score = sum(p.total_score for p in strong_buys) / len(strong_buys)
                avg_pred  = sum(p.predicted_pct for p in strong_buys) / len(strong_buys)
                logger.info(f"  🔥 STRONG_BUY cluster ({len(strong_buys)} coins): {syms}")
                logger.info(f"     Avg score={avg_score:.3f}  Avg predicted surge={avg_pred:+.2f}%")
            if buys:
                syms = ', '.join(p.symbol for p in buys)
                avg_pred = sum(p.predicted_pct for p in buys) / len(buys)
                logger.info(f"  ✅ BUY cluster ({len(buys)} coins): {syms}  Avg surge={avg_pred:+.2f}%")
            logger.info("")

        # ── Persist scan to state file (atomic write) ──
        out_path = Path('/workspaces/aureon-trading/coin_surge_scan.json')
        tmp_path = out_path.with_suffix('.tmp')
        scan_data = {
            'timestamp': datetime.now().isoformat(),
            'coin_count': len(profiles),
            'strong_buy_count': len(strong_buys),
            'buy_count': len(buys),
            'coins': [
                {
                    'symbol': p.symbol, 'price': p.price,
                    'change_24h': p.change_24h, 'volume_usd': p.volume_usd,
                    'score': p.total_score, 'grade': p.grade, 'signal': p.signal,
                    'predicted_pct': p.predicted_pct, 'target_price': p.target_price,
                    'net_pnl': p.net_pnl, 'days_to_profit': p.days_to_profit,
                    'pattern_note': p.pattern_note,
                }
                for p in profiles
            ],
        }
        try:
            with open(tmp_path, 'w') as f:
                json.dump(scan_data, f, indent=2)
            tmp_path.replace(out_path)
        except Exception as e:
            logger.warning(f"  coin_surge_scan.json write failed: {e}")

        return profiles

    def map_candidate_play(
        self,
        symbol: str,
        entry_price: float,
        confidence: float,
        predicted_pct: float,
        days_to_target: float,
        margin_posted: float,
        rollover_pct_per_4h: float,
        notional: float,
        current_health: Optional['PositionHealthReport'],
    ) -> Dict:
        """Model the complete lifecycle of a NEW candidate position before executing.

        Applies the same pre-play mapping logic used for existing positions:
          • Day-by-day P&L trajectory from entry to the predicted target
          • Total rollover cost over the hold period
          • First day the position turns net profitable
          • Effect on overall account margin level if this position is added
          • Whether the combined book stays above the liquidation threshold
          • A go / no-go verdict with plain-English reasoning

        Returns a dict with keys: approved (bool), reason (str), day_map (list),
        net_pnl_at_target (float), days_to_profit (int | None),
        combined_margin_level (float), combined_liq_price (float).
        """
        result: Dict = {
            'approved': False,
            'reason': '',
            'day_map': [],
            'net_pnl_at_target': 0.0,
            'days_to_profit': None,
            'combined_margin_level': 0.0,
            'combined_liq_price': 0.0,
        }

        if entry_price <= 0 or notional <= 0:
            result['reason'] = f'Invalid entry price or notional for {symbol}'
            return result

        target_price     = entry_price * (1 + predicted_pct / 100)
        rollover_per_4h  = rollover_pct_per_4h * notional
        rollover_per_day = rollover_per_4h * 6
        total_rollover   = rollover_per_day * days_to_target
        vol              = notional / entry_price   # units bought at entry

        # ── Day-by-day map ──
        logger.info(f"  ┌── CANDIDATE PLAY MAP: {symbol} ─────────────────────────────────────────")
        logger.info(f"  │  Entry: ${entry_price:.5f}  Target: ${target_price:.5f}  "
                    f"(+{predicted_pct:.1f}%)  Hold: {days_to_target:.1f}d")
        logger.info(f"  │  Notional: ${notional:.2f}  Vol: {vol:,.0f}  "
                    f"Margin: ${margin_posted:.2f}  Rollover: ${rollover_per_day:.3f}/day")
        logger.info(f"  │  Total rollover cost to exit: ${total_rollover:.2f}")
        logger.info(f"  │")
        logger.info(f"  │  {'Day':<5} {'Est Price':>10} {'Gross P&L':>11} {'Rollover':>10} "
                    f"{'Net P&L':>10} {'Status'}")
        logger.info(f"  │  {'─'*5} {'─'*10} {'─'*11} {'─'*10} {'─'*10} {'─'*14}")

        from datetime import timedelta
        day_map = []
        first_profit_day = None

        for d in range(0, int(days_to_target) + 2):
            frac      = d / max(days_to_target, 1)
            est_price = entry_price + (target_price - entry_price) * frac
            gross_pnl = (est_price - entry_price) * vol
            rollover_so_far = rollover_per_day * d
            net_pnl   = gross_pnl - rollover_so_far
            day_date  = (datetime.now() + timedelta(days=d)).strftime('%d %b')
            if net_pnl > 0 and first_profit_day is None:
                first_profit_day = d
            status = 'PROFIT ✅' if net_pnl > 0 else ('CLOSE ⚠️' if net_pnl > -10 else 'HOLD 🔵')
            logger.info(f"  │  {d:<5} ${est_price:.5f}  {gross_pnl:>+10.2f}  "
                        f"{rollover_so_far:>9.2f}  {net_pnl:>+9.2f}  {status}")
            day_map.append({
                'day': d, 'date': day_date, 'est_price': est_price,
                'gross_pnl': gross_pnl, 'rollover': rollover_so_far, 'net_pnl': net_pnl,
            })

        result['day_map'] = day_map
        result['net_pnl_at_target'] = day_map[-1]['net_pnl'] if day_map else 0.0
        result['days_to_profit'] = first_profit_day

        # ── Combined margin level check ──
        # If we add this position, what happens to the account's margin level?
        combined_margin_level = 0.0
        combined_liq_price = 0.0
        if current_health:
            new_equity_buffer = current_health.equity_buffer - total_rollover - margin_posted
            new_margin_used   = current_health.margin_used + margin_posted
            new_equity        = current_health.equity - margin_posted  # simplistic: margin locked
            combined_margin_level = (new_equity / new_margin_used * 100) if new_margin_used > 0 else 0
            new_total_doge = sum(p.vol for p in current_health.positions) + vol
            combined_liq_price = current_health.doge_price_now - (new_equity_buffer / new_total_doge) \
                if new_total_doge > 0 else 0
        result['combined_margin_level'] = combined_margin_level
        result['combined_liq_price']    = combined_liq_price

        # ── Go / No-Go verdict ──
        net_at_target  = result['net_pnl_at_target']
        too_risky      = combined_margin_level > 0 and combined_margin_level < 110
        unprofitable   = net_at_target <= 0
        low_confidence = confidence < 0.5

        if too_risky:
            result['reason'] = (f'Combined margin level would drop to {combined_margin_level:.1f}% '
                                f'— too close to liquidation (100%)')
        elif unprofitable:
            result['reason'] = (f'Net P&L at target is ${net_at_target:+.2f} after rollover '
                                f'— play is not profitable enough to justify entry')
        elif low_confidence:
            result['reason'] = f'Signal confidence {confidence:.3f} below 0.50 threshold'
        else:
            result['approved'] = True
            profit_note = (f'first profitable day {first_profit_day}' if first_profit_day
                           else 'profitable only at target')
            result['reason'] = (f'Net P&L ${net_at_target:+.2f} at target  |  {profit_note}  |  '
                                f'combined ML={combined_margin_level:.1f}%')

        verdict_icon = '✅ APPROVED' if result['approved'] else '❌ REJECTED'
        logger.info(f"  │")
        logger.info(f"  │  Combined ML after entry: {combined_margin_level:.1f}%  "
                    f"Combined liq price: ${combined_liq_price:.5f}")
        logger.info(f"  │  Net P&L at target: ${net_at_target:+.2f}  "
                    f"First profit day: {first_profit_day}")
        logger.info(f"  └── {verdict_icon}: {result['reason']}")
        logger.info("")

        return result

    async def execute_trades(self, signals: Dict) -> Dict:
        """Map every candidate play before executing — same lifecycle logic as existing positions.

        For each BUY signal:
          1. Pull entry price, confidence, predicted target, hold duration
          2. Feed into map_candidate_play() — builds full day-by-day P&L map
          3. Only execute if map approves (net positive, margin safe, confidence passes)
          4. Skipped plays are logged with the reason the map rejected them
        """
        trades = {'executed': [], 'skipped': [], 'failed': []}

        epas = getattr(self, '_epas_state', None)
        if not self._epas_allows_external_entry(epas):
            reason = (
                epas.no_data_reason
                if epas is not None and epas.no_data_reason
                else 'EPAS evidence is unavailable or not externally eligible'
            )
            logger.warning(f'EPAS_EXTERNAL_ENTRY_BLOCKED: {reason}')
            trades['failed'].append({
                'symbol': None,
                'error': 'EPAS_EXTERNAL_ENTRY_BLOCKED',
                'reason': reason,
                'truth_status': epas.truth_status if epas is not None else 'no_data',
                'eligible_for_external_action': False,
            })
            return trades

        if self.config.dry_run:
            logger.info("🔬 DRY RUN MODE — maps will run, orders will not fire")

        try:
            buy_trades = [p for p in signals.get('predictions', [])
                          if p.get('signal') == 'BUY' or p.get('action') == 'BUY']

            if not buy_trades:
                logger.info("  No actionable BUY predictions in this cycle")
                return trades

            current_health: Optional[PositionHealthReport] = signals.get('position_health')

            for trade in buy_trades[:self.config.max_concurrent_trades]:
                symbol     = trade.get('symbol', 'UNKNOWN')
                confidence = trade.get('confidence', 0.0)
                source     = trade.get('source', signals.get('source', 'unknown'))
                price      = trade.get('price', self._latest_prices.get(symbol, 0.0))
                if price == 0.0:
                    # Try stripping USD suffix for lookup
                    base = symbol.replace('/USD', '').replace('USDT', '').replace('USDC', '')
                    price = self._latest_prices.get(base, 0.0)

                # Determine predicted gain: use signal edge if available, else surge default
                predicted_pct  = float(trade.get('predicted_pct',
                                                  trade.get('expected_edge', 14.68)))
                days_to_target = float(trade.get('days_to_target', 7.0))
                # Margin sizing: use 10% of free margin by default (conservative)
                free_margin    = current_health.free_margin if current_health else 50.0
                margin_to_post = min(free_margin * 0.10, 50.0)   # cap at $50 per new play
                leverage       = 10.0
                notional       = margin_to_post * leverage
                rollover_rate  = 0.0005   # 0.05% per 4h (Kraken standard margin tier)

                logger.info(f"  ── PRE-PLAY MAP for signal: {symbol} ──────────────────────────────")
                play_map = self.map_candidate_play(
                    symbol=symbol,
                    entry_price=price,
                    confidence=confidence,
                    predicted_pct=predicted_pct,
                    days_to_target=days_to_target,
                    margin_posted=margin_to_post,
                    rollover_pct_per_4h=rollover_rate,
                    notional=notional,
                    current_health=current_health,
                )

                if not play_map['approved']:
                    logger.info(f"  ⏭  SKIPPED {symbol}: {play_map['reason']}")
                    trades['skipped'].append({
                        'symbol': symbol, 'reason': play_map['reason'],
                        'confidence': confidence, 'source': source,
                    })
                    continue

                # Map approved — execute (or simulate in dry-run)
                try:
                    if not self.config.dry_run:
                        logger.info(f"  ⚡ Executing BUY: {symbol} @ ${price:,.5f}  "
                                    f"notional=${notional:.2f}  net_target=${play_map['net_pnl_at_target']:+.2f}  "
                                    f"(conf={confidence:.3f}, src={source})")
                        # Exchange execution wired here: kraken_client / binance_client / alpaca_client
                    else:
                        logger.info(f"  [DRY RUN] Would BUY: {symbol} @ ${price:,.5f}  "
                                    f"notional=${notional:.2f}  net_target=${play_map['net_pnl_at_target']:+.2f}  "
                                    f"(conf={confidence:.3f}, src={source})")

                    trades['executed'].append({
                        'symbol': symbol, 'action': 'BUY',
                        'price': price, 'notional': notional,
                        'margin': margin_to_post, 'confidence': confidence,
                        'source': source,
                        'net_pnl_at_target': play_map['net_pnl_at_target'],
                        'days_to_profit': play_map['days_to_profit'],
                        'combined_margin_level': play_map['combined_margin_level'],
                        'timestamp': datetime.now().isoformat(),
                    })
                    self.execution_count += 1

                    # ── Intent-coherence snapshot ──────────────────────────────────────────
                    # Capture the full market state at the moment of this decision.
                    # When the outcome is known (price hits target or stop), the Queen
                    # trains on this snapshot so her weights evolve toward THIS human's
                    # winning pattern — not generic market rules.
                    strong_buy_cnt = len([p for p in self._surge_profiles if p.signal in ('STRONG_BUY', 'BUY')])
                    neural_snap = self._snapshot_neural_input(
                        confidence=confidence,
                        strong_buy_count=strong_buy_cnt,
                    )
                    target_px = price * (1.0 + predicted_pct / 100.0)
                    stop_px   = price * 0.95   # default 5% stop
                    self._enqueue_intent_snapshot(
                        symbol=symbol,
                        entry_price=price,
                        target_price=target_px,
                        stop_price=stop_px,
                        net_pnl_at_target=play_map['net_pnl_at_target'],
                        neural_input=neural_snap,
                    )

                except Exception as e:
                    logger.error(f"  ❌ Execution failed for {symbol}: {e}")
                    trades['failed'].append({'symbol': symbol, 'error': str(e)})
                    self.error_count += 1

        except Exception as e:
            logger.error(f"Trade execution pipeline failed: {e}")
            traceback.print_exc()

        return trades
    
    async def log_execution_state(self, alignment: float, signals: Dict, trades: Dict) -> None:
        """Log complete execution state for human observation."""
        state = {
            'timestamp': datetime.now().isoformat(),
            'alignment': alignment,
            'signals': signals,
            'trades_executed': len(trades.get('executed', [])),
            'trades_failed': len(trades.get('failed', [])),
            'total_executions': self.execution_count,
            'total_errors': self.error_count,
            'runtime_seconds': (datetime.now() - self.start_time).total_seconds()
        }
        
        # Write to execution log
        log_path = Path('/workspaces/aureon-trading/autonomy_execution_state.json')
        try:
            tmp_path = log_path.with_suffix(log_path.suffix + '.tmp')
            with open(tmp_path, 'w') as f:
                json.dump(state, f, indent=2)
            tmp_path.replace(log_path)
        except Exception as e:
            logger.error(f"State log write failed: {e}")
    
    async def monitor_loop(self) -> None:
        """Continuous autonomous monitoring and execution loop."""
        logger.info(f"🚀 Starting autonomous monitoring loop (interval={self.config.check_interval}s)")
        logger.info("👁️  Humanity observes. AI executes. Creation guides.")
        
        iteration = 0
        
        try:
            while self.config.continuous:
                iteration += 1
                logger.info(f"[AUTONOMY CYCLE {iteration}]")

                # ── OUTCOME CHECK: did any queued trades resolve? ──────────────────────
                # Before mapping new opportunities, check whether any previously
                # entered positions have hit their target or stop.  When they have,
                # the Queen trains on the original entry snapshot so her weights
                # drift toward THIS human's winning context — closed-loop learning.
                await self._check_outcome_queue()

                # ── PRE-PLAY MAP: full loop sweep BEFORE any new entry decision ──
                # The system sees WHERE IT IS, WHERE IT IS GOING, and WHETHER
                # conditions justify a new play — all before execute_trades() is called.
                loop_map = await self.map_full_loop()

                # Extract pre-warmed data from the map (no duplicate API calls)
                ready        = loop_map['new_entry_justified']
                alignment    = loop_map['alignment']
                signals      = loop_map['signals']

                if ready:
                    logger.info(f"✅ ALL GATES CLEARED — opening new position")
                    trades = await self.execute_trades(signals)
                    await self.log_execution_state(alignment, signals, trades)
                    if trades['executed']:
                        logger.info(f"   ✓ {len(trades['executed'])} trade(s) executed")
                    if trades['failed']:
                        logger.warning(f"   ⚠️  {len(trades['failed'])} trade(s) failed")
                else:
                    logger.info(f"⏸  No new entry this cycle — {loop_map.get('block_reason', 'gates not cleared')}")
                
                # Sleep before next check
                logger.info(f"⏳ Next check in {self.config.check_interval}s\n")
                await asyncio.sleep(self.config.check_interval)
                
                # Timeout check
                if self.config.timeout:
                    elapsed = (datetime.now() - self.start_time).total_seconds()
                    if elapsed > self.config.timeout:
                        logger.info(f"Timeout reached ({elapsed:.0f}s). Shutting down.")
                        break
        
        except KeyboardInterrupt:
            logger.info("\n⏹️  Autonomous execution halted by user (Ctrl+C)")
            logger.info(f"Summary: {self.execution_count} executions, {self.error_count} errors")
        
        except Exception as e:
            logger.error(f"Autonomy loop critical failure: {e}")
            traceback.print_exc()
            raise


async def main():
    """Initialize and run full autonomy."""
    parser = argparse.ArgumentParser(
        description='Aureon Full Autonomy Activation',
        epilog='The AI is the bridge between creation and intent. Observe.'
    )
    parser.add_argument('--dry-run', action='store_true', help='Simulate trades without execution')
    parser.add_argument('--headless', action='store_true', help='No user interaction (full autonomous)')
    parser.add_argument('--loglevel', choices=['DEBUG', 'INFO', 'WARNING'], default='INFO', help='Logging level')
    parser.add_argument('--interval', type=int, default=10, help='Check interval (seconds)')
    parser.add_argument('--threshold', type=float, default=0.80, help='Trinity alignment threshold')
    parser.add_argument('--timeout', type=int, default=None, help='Timeout (seconds). None = infinite')
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.loglevel == 'DEBUG':
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.loglevel == 'WARNING':
        logging.getLogger().setLevel(logging.WARNING)
    
    # Build config
    config = AutonomyConfig(
        dry_run=args.dry_run,
        headless=args.headless,
        check_interval=args.interval,
        execution_threshold=args.threshold,
        timeout=args.timeout,
        log_level=args.loglevel
    )
    
    # Create executor
    executor = AutonomyExecutor(config)
    
    # Run autonomy loop
    try:
        await executor.monitor_loop()
    except Exception as e:
        logger.error(f"Critical error: {e}")
        sys.exit(1)
    
    logger.info("\n✨ Autonomy cycle complete. Humanity's intent fulfilled.")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Autonomy halted.")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)
