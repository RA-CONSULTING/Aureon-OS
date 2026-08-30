#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  👑🌍  AUREON GLOBAL MARKET ORGANISM — THE LIVING BLOCKCHAIN BODY  🌍👑    ║
║  ─────────────────────────────────────────────────────────────────────────  ║
║                                                                              ║
║  "The entire global blockchain is one big sensory system.                   ║
║   Every coin, stock, commodity has its own unique fingerprint.              ║
║   The system knows — like a sixth sense — when something is wrong."         ║
║                                                                              ║
║  WHAT THIS MODULE DOES                                                       ║
║  ──────────────────────                                                      ║
║  1. MARKET ORGANISM                                                          ║
║     Treats the entire blockchain as one living entity. Each asset is a      ║
║     sensory node. Together they form a body that breathes, pulses, and      ║
║     reacts. When one node is manipulated the organism FEELS it.             ║
║                                                                              ║
║  2. MANIPULATION DETECTION — "Cooking the Books"                            ║
║     Volume Archaeology: compare current volume to 30-day historical.        ║
║     Hurst Exponent: natural markets ~0.5; manufactured trends > 0.85.       ║
║     Wash Trading: coordinated buy/sell cycling = inflated fake volume.      ║
║     Spoofing / Layering: ghost orders creating false depth.                 ║
║     Book Cooking: patterns that can only exist if orders are being planted. ║
║                                                                              ║
║  3. PUMP & DUMP RADAR                                                        ║
║     Phase detection: Accumulation → Pump → Distribution → Dump.             ║
║     Cross-asset propagation: P&D in BTC bleeds into ALTs in minutes.        ║
║     Real-time phase transitions tracked per asset.                          ║
║                                                                              ║
║  4. ENTITY INTELLIGENCE FUSION                                               ║
║     Reuses existing bot intelligence without changing anything:             ║
║       aureon_bot_entity_attribution.py  (BotAttribution)                   ║
║       aureon_bot_intelligence_profiler.py (BotProfile)                      ║
║       aureon_real_intelligence_engine.py (ValidatedIntelligence)            ║
║       aureon_queen_counter_intelligence.py (CounterIntelligenceSignal)      ║
║     Cross-references entity positions across the whole ecosystem.           ║
║                                                                              ║
║  5. THE SIXTH SENSE — ManipulationChannel                                   ║
║     A 9th SensoryChannel that plugs directly into QueenSensorySystem.       ║
║     Maps organic score → Hz: 528 Hz (natural) → 33 Hz (pure deception).    ║
║     Discordant frequencies = off-Solfeggio = something is wrong.            ║
║     Registers automatically via register_manipulation_sense().              ║
║                                                                              ║
║  BACKWARDS COMPATIBILITY                                                     ║
║  ─────────────────────────                                                   ║
║  Zero existing files are modified. This module imports from them;           ║
║  they never import back. The ManipulationChannel slots into                  ║
║  QueenSensorySystem via the existing registry.register() API.               ║
║                                                                              ║
║  Gary Leckey | March 2026                                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import hashlib
import math
import time
import logging
import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Set, Tuple, Union

logger = logging.getLogger("market_organism")

MAX_RECEIPT_AGE_SECONDS = 120.0
MAX_CLOCK_SKEW_SECONDS = 5.0
REAL_TRUTH_STATUSES = frozenset({"real_observed", "real_derived"})


def _finite(
    value: Any,
    *,
    positive: bool = False,
    nonnegative: bool = False,
) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    if positive and number <= 0.0:
        return None
    if nonnegative and number < 0.0:
        return None
    return number


def _normalise_symbol(value: Any) -> str:
    return str(value or "").strip().upper().replace("/", "").replace("-", "")


def _no_data(reason: str) -> "MarketNoData":
    return MarketNoData(reason=reason)


@dataclass(frozen=True)
class MarketNoData:
    """Numeric-free fail-closed result for missing or untrusted evidence."""

    reason: str
    data_status: str = "no_data"
    truth_status: str = "no_data"
    source_id: Optional[str] = None
    source_timestamp: Optional[float] = None
    received_at: Optional[float] = None
    receipt_id: Optional[str] = None
    generated_values: bool = False
    generated: bool = False
    evidence_complete: bool = False
    actionable: bool = False
    accounting_eligible: bool = False
    learning_eligible: bool = False
    state_mutated: bool = False


@dataclass(frozen=True)
class _ValidatedReceipt:
    source_id: str
    source_timestamp: float
    received_at: float
    receipt_id: str
    symbol: str
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class _ValidatedBundle:
    current: _ValidatedReceipt
    volumes: Tuple[_ValidatedReceipt, ...]
    prices: Tuple[_ValidatedReceipt, ...]

    @property
    def input_receipt_ids(self) -> Tuple[str, ...]:
        return tuple(
            receipt.receipt_id
            for receipt in (*self.volumes, *self.prices, self.current)
        )


def _validate_provider_receipt(
    receipt: Any,
    *,
    symbol: str,
    now: float,
) -> Optional[_ValidatedReceipt]:
    if not isinstance(receipt, Mapping):
        return None
    source_id = str(receipt.get("source_id") or "").strip()
    receipt_id = str(receipt.get("receipt_id") or "").strip()
    source_timestamp = _finite(receipt.get("source_timestamp"), positive=True)
    received_at = _finite(receipt.get("received_at"), positive=True)
    receipt_symbol = _normalise_symbol(receipt.get("symbol"))
    if (
        not source_id
        or not receipt_id
        or source_timestamp is None
        or received_at is None
        or receipt_symbol != _normalise_symbol(symbol)
        or receipt.get("data_status") != "live"
        or receipt.get("truth_status") not in REAL_TRUTH_STATUSES
        or receipt.get("generated_values") is not False
        or receipt.get("generated") is not False
        or source_timestamp > received_at + MAX_CLOCK_SKEW_SECONDS
        or received_at > now + MAX_CLOCK_SKEW_SECONDS
        or now - source_timestamp > MAX_RECEIPT_AGE_SECONDS
        or now - received_at > MAX_RECEIPT_AGE_SECONDS
    ):
        return None
    return _ValidatedReceipt(
        source_id=source_id,
        source_timestamp=source_timestamp,
        received_at=received_at,
        receipt_id=receipt_id,
        symbol=receipt_symbol,
        payload=receipt,
    )


def _validate_receipt_sequence(
    receipts: Any,
    *,
    symbol: str,
    now: float,
    value_field: str,
    minimum: int,
) -> Optional[Tuple[_ValidatedReceipt, ...]]:
    if not isinstance(receipts, Sequence) or isinstance(receipts, (str, bytes)):
        return None
    if len(receipts) < minimum:
        return None
    validated: List[_ValidatedReceipt] = []
    seen_ids: Set[str] = set()
    previous_timestamp: Optional[float] = None
    for raw in receipts:
        receipt = _validate_provider_receipt(raw, symbol=symbol, now=now)
        if receipt is None:
            return None
        value = _finite(receipt.payload.get(value_field), positive=True)
        if (
            value is None
            or receipt.receipt_id in seen_ids
            or (
                previous_timestamp is not None
                and receipt.source_timestamp <= previous_timestamp
            )
        ):
            return None
        validated.append(receipt)
        seen_ids.add(receipt.receipt_id)
        previous_timestamp = receipt.source_timestamp
    return tuple(validated)


def _derived_receipt_id(input_receipt_ids: Sequence[str]) -> str:
    digest = hashlib.sha256("\n".join(input_receipt_ids).encode("utf-8")).hexdigest()
    return f"market-organism:{digest}"

# ─────────────────────────────────────────────────────────────────────────────
# SACRED CONSTANTS (mirrored — never import back into subsystems)
# ─────────────────────────────────────────────────────────────────────────────
PHI            = (1 + math.sqrt(5)) / 2    # 1.618...
LOVE_FREQUENCY = 528.0                     # Hz — natural/organic resonance
SCHUMANN       = 7.83                      # Hz — Earth heartbeat

# Sixth-sense Hz scale — discordance increases as manipulation rises
# Natural = Solfeggio notes.  Manipulated = below UT (174 Hz) → corruption
ORGANIC_SOLFEGGIO = {
    "pure":          528.0,   # SOL — Love, fully natural market
    "slight":        417.0,   # FA  — Change/caution, minor concern
    "suspicious":    285.0,   # RE  — Disrupted flow
    "manipulated":   174.0,   # UT  — Foundation compromised
    "heavy":         111.0,   # sub-Solfeggio — off the scale
    "fraud":          33.0,   # Delta brainwave range — pure deception
}

# Pump & Dump phase parameters
PUMP_DUMP_PHASES = {
    "accumulation": dict(vol_mult=(0.7, 1.8),  price_pct=(-3,  +8),  days=(3, 45)),
    "pump":         dict(vol_mult=(3.0, 30.0), price_pct=(+15, 500), days=(0.2, 7)),
    "distribution": dict(vol_mult=(2.0, 8.0),  price_pct=(-8,  +12), days=(0.2, 5)),
    "dump":         dict(vol_mult=(1.5, 15.0), price_pct=(-15, -95), days=(0.1, 4)),
}

# Volume archaeology thresholds (z-score above rolling baseline)
VOL_Z_SUSPICIOUS  = 3.0
VOL_Z_ARTIFICIAL  = 5.0
VOL_Z_EXTREME     = 8.0

# Hurst exponent thresholds
HURST_RANDOM      = 0.50   # Random walk — natural baseline
HURST_TRENDING    = 0.65   # Organic trending market
HURST_SUSPICIOUS  = 0.78   # Possibly manufactured
HURST_MANIPULATED = 0.88   # Very likely coordinated


# ─────────────────────────────────────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────────────────────────────────────

class PumpDumpPhase(str, Enum):
    NONE          = "none"
    ACCUMULATION  = "accumulation"
    PUMP          = "pump"
    DISTRIBUTION  = "distribution"
    DUMP          = "dump"
    UNKNOWN       = "unknown"


class ManipulationType(str, Enum):
    NONE           = "none"
    WASH_TRADING   = "wash_trading"       # Self-buy/sell to inflate volume
    SPOOFING       = "spoofing"           # Ghost orders cancelled before fill
    LAYERING       = "layering"           # Multi-level fake depth
    RAMPING        = "ramping"            # Coordinated price push
    PUMP_DUMP      = "pump_dump"          # Classic retail trap
    BOOK_COOKING   = "book_cooking"       # Reported volume ≠ real volume
    COORDINATED    = "coordinated"        # Multi-entity orchestration
    MARKING_CLOSE  = "marking_close"      # End-of-period price painting


class AssetType(str, Enum):
    CRYPTO     = "crypto"
    STOCK      = "stock"
    COMMODITY  = "commodity"
    FOREX      = "forex"
    DERIVATIVE = "derivative"
    INDEX      = "index"


class OrganismRole(str, Enum):
    PRODUCER   = "producer"    # Creates value / volume / new liquidity
    AMPLIFIER  = "amplifier"   # Amplifies signals from other assets
    ABSORBER   = "absorber"    # Absorbs manipulation (safe haven)
    DISRUPTOR  = "disruptor"   # Intentionally distorts the organism
    NEUTRAL    = "neutral"


# ─────────────────────────────────────────────────────────────────────────────
# CORE DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class VolumeArchaeology:
    """
    Natural vs artificial volume analysis.

    Compares current volume against 30-day rolling baseline using
    statistical z-scores and volume-leading-price tests.
    A natural market has price move BEFORE volume follows.
    A manipulated market has coordinated volume BEFORE the price is moved.
    """
    symbol: str
    current_volume: float
    baseline_mean: float
    baseline_std: float
    z_score: float               # standard deviations from baseline
    volume_organic_score: float  # 0 = artificial, 1 = natural
    volume_leads_price: bool     # True if volume is suspiciously leading
    days_of_data: int
    verdict: str                 # "natural" | "suspicious" | "artificial" | "extreme"

    @property
    def is_suspicious(self) -> bool:
        return self.z_score > VOL_Z_SUSPICIOUS

    @property
    def is_artificial(self) -> bool:
        return self.z_score > VOL_Z_ARTIFICIAL


@dataclass
class PriceDNA:
    """
    Fractal / structural authenticity of price action.

    Natural markets follow power-law distributions (Mandelbrot).
    Hurst exponent near 0.5 = random walk (natural).
    Hurst > 0.85 = too perfect a trend = someone is steering the price.
    """
    symbol: str
    hurst_exponent: float        # 0 = mean-reverting, 1 = perfectly trending
    fractal_naturalness: float   # 0 = artificial, 1 = natural fractal
    round_number_clustering: float  # 0-1 (1 = lots of round-number orders = bots)
    staircase_pattern: bool      # True = coordinated step-accumulation
    wick_ratio_anomaly: bool     # True = wicks too uniform (algo-generated)
    dna_score: float             # 0-1 composite naturalness
    verdict: str


@dataclass
class ManipulationProfile:
    """
    Complete manipulation analysis for a single asset.

    Combines volume archaeology, price DNA, bot density, entity attribution,
    wash trading detection, and pattern matching to produce a single
    organic_score: 1.0 = completely natural, 0.0 = confirmed manipulation.
    """
    symbol: str
    timestamp: float

    # ── Detection scores ──────────────────────────────────────────────────────
    organic_score: float          # 0-1 (1 = natural, 0 = full manipulation)
    manipulation_probability: float  # 0-1 (inverse of organic)
    confidence: float             # 0-1 how certain we are

    # ── Components ───────────────────────────────────────────────────────────
    volume_archaeology: Optional[VolumeArchaeology] = None
    price_dna: Optional[PriceDNA] = None
    wash_trade_score: float = 0.0      # 0-1 (1 = heavy wash trading)
    spoof_layering_score: float = 0.0  # 0-1 (1 = heavy spoofing/layering)
    bot_density: float = 0.0           # 0-1 fraction of volume bot-driven
    entity_coordination: float = 0.0   # 0-1 how coordinated entities are

    # ── Classification ────────────────────────────────────────────────────────
    manipulation_types: List[ManipulationType] = field(default_factory=list)
    pump_dump_phase: PumpDumpPhase = PumpDumpPhase.NONE
    attributed_entities: List[str] = field(default_factory=list)  # firm names

    # ── Frequency mapping ─────────────────────────────────────────────────────
    manipulation_hz: float = LOVE_FREQUENCY  # Discordant if manipulated

    # ── Evidence ──────────────────────────────────────────────────────────────
    evidence: List[str] = field(default_factory=list)
    verdict: str = "natural"
    action: str = "hold_and_monitor"


@dataclass
class MarketNode:
    """
    One coin/stock/commodity as a unique sensory node in the organism.

    Each asset has its own fingerprint: how it normally behaves,
    who trades it, what its natural growth pattern looks like.
    Together all nodes form the Global Market Organism.
    """
    symbol: str
    asset_type: AssetType

    # ── Fingerprint ───────────────────────────────────────────────────────────
    natural_daily_volume_usd: float = 0.0    # Baseline 30-day avg
    natural_volatility_pct: float = 0.0      # Baseline 30-day avg vol
    typical_entities: List[str] = field(default_factory=list)  # Usual traders
    natural_hurst: float = 0.55              # Asset's typical Hurst baseline

    # ── Live state ────────────────────────────────────────────────────────────
    last_updated: float = field(default_factory=time.time)
    manipulation_profile: Optional[ManipulationProfile] = None
    pump_dump_phase: PumpDumpPhase = PumpDumpPhase.NONE
    organism_role: OrganismRole = OrganismRole.NEUTRAL

    # ── Cross-asset influence ─────────────────────────────────────────────────
    # Which assets does manipulation in this node tend to affect?
    downstream_influence: List[str] = field(default_factory=list)

    @property
    def is_compromised(self) -> bool:
        if self.manipulation_profile is None:
            return False
        return self.manipulation_profile.organic_score < 0.5

    @property
    def organic_score(self) -> float:
        if self.manipulation_profile is None:
            return 0.75   # Unknown = assume somewhat natural
        return self.manipulation_profile.organic_score


@dataclass
class EcosystemReport:
    """
    The full-organism health report — the entire blockchain as one being.
    """
    timestamp: float
    nodes_monitored: int
    nodes_active: int

    # ── Organism health ───────────────────────────────────────────────────────
    organism_health_score: float     # 0-1 (1 = fully healthy natural market)
    organic_flow_score: float        # 0-1 (1 = all volume is natural)
    manipulation_index: float        # 0-1 (0 = clean, 1 = heavy manipulation)
    coherence: float                 # 0-1 how well all assets move together naturally

    # ── Hot zones ─────────────────────────────────────────────────────────────
    manipulation_hotspots: List[ManipulationProfile] = field(default_factory=list)
    active_pump_dumps: List[Dict] = field(default_factory=list)
    dominant_entities: List[str] = field(default_factory=list)

    # ── Cross-contamination ───────────────────────────────────────────────────
    # Manipulation in one asset propagating to others
    contagion_alerts: List[str] = field(default_factory=list)

    # ── Dominant Hz across the organism ──────────────────────────────────────
    dominant_hz: float = LOVE_FREQUENCY
    dominant_emotion: str = "Gratitude"

    # ── Verdict ───────────────────────────────────────────────────────────────
    grand_verdict: str = ""
    recommended_posture: str = ""   # "engage" | "reduce" | "avoid" | "flee"


# ─────────────────────────────────────────────────────────────────────────────
# MANIPULATION DETECTION ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class ManipulationDetector:
    """
    The forensic engine behind the sixth sense.

    Runs every available detection algorithm against market data.
    Works with whatever data is available — degrades gracefully.
    """

    # ── Volume Archaeology ────────────────────────────────────────────────────

    @staticmethod
    def volume_archaeology(symbol: str,
                           volume_history: List[float],
                           current_volume: float,
                           price_change_pct: float = 0.0) -> VolumeArchaeology:
        """
        Compare current volume to 30-day rolling baseline.

        Natural: current volume within 2 sigma of baseline.
        Suspicious: z > 3.0.   Artificial: z > 5.0.   Extreme: z > 8.0.

        Also checks: does volume LEAD the price? In manipulation the
        coordinated buy-in starts before the official price move.
        """
        if len(volume_history) < 3:
            return VolumeArchaeology(
                symbol=symbol, current_volume=current_volume,
                baseline_mean=current_volume, baseline_std=0.0,
                z_score=0.0, volume_organic_score=0.75,
                volume_leads_price=False, days_of_data=len(volume_history),
                verdict="insufficient_data",
            )

        baseline_mean = statistics.mean(volume_history)
        baseline_std  = statistics.stdev(volume_history) if len(volume_history) > 1 else baseline_mean * 0.2
        baseline_std  = max(baseline_std, baseline_mean * 0.05)  # floor at 5% of mean

        z_score = (current_volume - baseline_mean) / baseline_std

        # Organic score: sigmoid-like decay above 2 sigma
        if z_score <= 2.0:
            organic = 1.0
        elif z_score <= VOL_Z_SUSPICIOUS:
            organic = 0.85
        elif z_score <= VOL_Z_ARTIFICIAL:
            organic = 0.55 - (z_score - VOL_Z_SUSPICIOUS) * 0.08
        elif z_score <= VOL_Z_EXTREME:
            organic = 0.35 - (z_score - VOL_Z_ARTIFICIAL) * 0.06
        else:
            organic = max(0.0, 0.15 - (z_score - VOL_Z_EXTREME) * 0.02)

        # Volume-leads-price test: manipulation has massive volume on flat or
        # rising prices; natural has price move on moderate volume
        volume_leads_price = (z_score > VOL_Z_SUSPICIOUS and abs(price_change_pct) < 5.0)

        if z_score > VOL_Z_EXTREME:
            verdict = "extreme_artificial"
        elif z_score > VOL_Z_ARTIFICIAL:
            verdict = "artificial"
        elif z_score > VOL_Z_SUSPICIOUS:
            verdict = "suspicious"
        else:
            verdict = "natural"

        return VolumeArchaeology(
            symbol=symbol,
            current_volume=current_volume,
            baseline_mean=baseline_mean,
            baseline_std=baseline_std,
            z_score=round(z_score, 2),
            volume_organic_score=round(max(0.0, min(1.0, organic)), 4),
            volume_leads_price=volume_leads_price,
            days_of_data=len(volume_history),
            verdict=verdict,
        )

    # ── Price DNA / Hurst Exponent ────────────────────────────────────────────

    @staticmethod
    def price_dna(symbol: str, prices: List[float],
                  order_round_number_pct: float = 0.0) -> PriceDNA:
        """
        Assess the structural authenticity of price action.

        Hurst exponent: estimated via rescaled range analysis.
        Natural markets: H ≈ 0.5.  Manufactured trends: H > 0.85.

        Also detects staircase accumulation patterns and wick uniformity
        that is statistically impossible without algorithmic coordination.
        """
        if len(prices) < 6:
            return PriceDNA(
                symbol=symbol, hurst_exponent=0.55,
                fractal_naturalness=0.75, round_number_clustering=0.0,
                staircase_pattern=False, wick_ratio_anomaly=False,
                dna_score=0.70, verdict="insufficient_data",
            )

        # Hurst via Rescaled Range (simple approximation)
        hurst = ManipulationDetector._hurst_rs(prices)

        # Fractal naturalness from Hurst
        if hurst < 0.3:
            # Extreme mean-reversion = wash trading
            fractal_natural = 0.40
        elif 0.40 <= hurst <= HURST_TRENDING:
            fractal_natural = 1.0
        elif hurst <= HURST_SUSPICIOUS:
            fractal_natural = 0.75 - (hurst - HURST_TRENDING) * 2.5
        elif hurst <= HURST_MANIPULATED:
            fractal_natural = 0.45 - (hurst - HURST_SUSPICIOUS) * 3.0
        else:
            fractal_natural = max(0.0, 0.20 - (hurst - HURST_MANIPULATED) * 1.5)

        # Staircase detection: look for runs of identical price moves
        returns   = [prices[i] / prices[i-1] - 1 for i in range(1, len(prices))]
        staircase = ManipulationDetector._detect_staircase(returns)

        # Wick uniformity — only detectable if we have OHLCV; approximate here
        wick_anomaly = hurst > HURST_MANIPULATED and staircase

        # Round number clustering (from order data if available)
        round_score = min(1.0, order_round_number_pct)

        dna = (
            0.55 * fractal_natural
            + 0.25 * (1.0 - round_score)
            + 0.20 * (0.0 if staircase else 1.0)
        )

        if dna >= 0.80:
            verdict = "natural_fractal"
        elif dna >= 0.60:
            verdict = "mostly_natural"
        elif dna >= 0.40:
            verdict = "suspicious_structure"
        else:
            verdict = "artificial_structure"

        return PriceDNA(
            symbol=symbol,
            hurst_exponent=round(hurst, 4),
            fractal_naturalness=round(max(0.0, min(1.0, fractal_natural)), 4),
            round_number_clustering=round(round_score, 4),
            staircase_pattern=staircase,
            wick_ratio_anomaly=wick_anomaly,
            dna_score=round(max(0.0, min(1.0, dna)), 4),
            verdict=verdict,
        )

    @staticmethod
    def _hurst_rs(prices: List[float]) -> float:
        """Simplified Hurst exponent via Rescaled Range over log returns."""
        if len(prices) < 4:
            return 0.55
        log_returns = [math.log(prices[i] / prices[i-1])
                       for i in range(1, len(prices)) if prices[i-1] > 0]
        if not log_returns:
            return 0.55
        n = len(log_returns)
        mean_r = statistics.mean(log_returns)
        deviations = [r - mean_r for r in log_returns]
        cum_dev = []
        running = 0.0
        for d in deviations:
            running += d
            cum_dev.append(running)
        if not cum_dev:
            return 0.55
        R = max(cum_dev) - min(cum_dev)
        std_r = statistics.stdev(log_returns) if len(log_returns) > 1 else 1e-9
        RS = R / (std_r + 1e-12)
        if RS <= 0:
            return 0.55
        # H ≈ log(RS) / log(n)
        try:
            H = math.log(RS) / math.log(n)
            return max(0.1, min(1.0, H))
        except (ValueError, ZeroDivisionError):
            return 0.55

    @staticmethod
    def _detect_staircase(returns: List[float], threshold: float = 0.35) -> bool:
        """Detect staircase accumulation: repeating same-size moves."""
        if len(returns) < 6:
            return False
        rounded = [round(r * 1000, 1) for r in returns]
        from collections import Counter
        counts = Counter(rounded)
        top_count = counts.most_common(1)[0][1] if counts else 0
        return (top_count / len(returns)) > threshold

    # ── Wash Trading Detection ────────────────────────────────────────────────

    @staticmethod
    def wash_trading_score(volume_24h: float,
                           bid_ask_spread_pct: float,
                           price_change_pct: float,
                           volume_archaeology: Optional[VolumeArchaeology] = None) -> float:
        """
        Wash trading score (0-1).

        Wash traders: enormous volume with tiny price impact (they cancel each other).
        Signature: volume >>> 10x normal, price move << expected, tight spread.
        """
        score = 0.0

        # High volume + low price movement = orders cancelling each other
        if volume_archaeology and volume_archaeology.z_score > VOL_Z_SUSPICIOUS:
            expected_price_move = volume_archaeology.z_score * 2.0
            actual_move = abs(price_change_pct)
            if actual_move < expected_price_move * 0.15:
                score += 0.5   # Volume doesn't move price = wash

        # Unusually tight spread under high volume (coordinator is both sides)
        if bid_ask_spread_pct < 0.005 and volume_archaeology and volume_archaeology.z_score > 3:
            score += 0.25

        # Volume leads price
        if volume_archaeology and volume_archaeology.volume_leads_price:
            score += 0.20

        return round(min(1.0, score), 4)

    # ── Spoof / Layering Detection ────────────────────────────────────────────

    @staticmethod
    def spoof_layering_score(order_book_depth_usd: float,
                             bid_ask_spread_pct: float,
                             price_change_pct: float,
                             volume_24h_usd: float) -> float:
        """
        Spoofing / layering score (0-1).

        Spoofers: place huge orders on one side then cancel — creates false price signals.
        Layerers: stack multiple orders at different levels to create fake depth.
        Signature: book depth swings wildly, spreads widen/narrow erratically.
        """
        score = 0.0

        # Very deep book vs low volume: fake depth likely
        if volume_24h_usd > 0:
            depth_vol_ratio = order_book_depth_usd / (volume_24h_usd / 24)
            if depth_vol_ratio > 50:
                score += min(0.40, (depth_vol_ratio - 50) / 100)

        # Wide spread + high depth = orders placed far from mid (layering)
        if bid_ask_spread_pct > 0.10 and order_book_depth_usd > 1_000_000:
            score += 0.25

        # Price moved little despite deep book (depth is fake/cancelled)
        if order_book_depth_usd > 2_000_000 and abs(price_change_pct) < 1.0:
            score += 0.20

        return round(min(1.0, score), 4)

    # ── Pump & Dump Phase ─────────────────────────────────────────────────────

    @staticmethod
    def detect_pump_dump_phase(price_change_pct: float,
                               volume_archaeology: VolumeArchaeology,
                               trend_persistence_days: int = 1) -> PumpDumpPhase:
        """
        Identify current pump-and-dump phase based on price + volume signals.

        Phase transitions are the most actionable part of this intelligence.
        Knowing you're in Distribution before the Dump is the sixth sense.
        """
        vol_mult = volume_archaeology.current_volume / max(volume_archaeology.baseline_mean, 1e-9)
        pct = price_change_pct
        days = trend_persistence_days

        # DUMP: rapid crash after pump
        d = PUMP_DUMP_PHASES["dump"]
        if (d["vol_mult"][0] <= vol_mult and
                d["price_pct"][0] <= pct <= d["price_pct"][1] and
                days <= d["days"][1]):
            return PumpDumpPhase.DUMP

        # PUMP: massive volume + massive upward price
        p = PUMP_DUMP_PHASES["pump"]
        if (vol_mult >= p["vol_mult"][0] and
                pct >= p["price_pct"][0]):
            return PumpDumpPhase.PUMP

        # DISTRIBUTION: price stalling under high volume (smart money selling)
        dist = PUMP_DUMP_PHASES["distribution"]
        if (dist["vol_mult"][0] <= vol_mult <= dist["vol_mult"][1] and
                dist["price_pct"][0] <= pct <= dist["price_pct"][1] and
                days >= 1):
            return PumpDumpPhase.DISTRIBUTION

        # ACCUMULATION: slow grind + slightly elevated volume
        acc = PUMP_DUMP_PHASES["accumulation"]
        if (acc["vol_mult"][0] <= vol_mult <= acc["vol_mult"][1] and
                acc["price_pct"][0] <= pct <= acc["price_pct"][1]):
            return PumpDumpPhase.ACCUMULATION

        return PumpDumpPhase.NONE

    # ── Master Analysis ───────────────────────────────────────────────────────

    def analyse(self, symbol: str,
                market_data: Dict[str, Any],
                volume_history: Optional[List[float]] = None,
                price_history: Optional[List[float]] = None,
                bot_intelligence: Optional[Any] = None) -> ManipulationProfile:
        """
        Full manipulation analysis. Returns ManipulationProfile.

        Works with any subset of available data — degrades gracefully.
        """
        ts = time.time()

        current_volume  = float(market_data.get("volume_24h_usd",        1_000_000))
        price_change    = float(market_data.get("price_change_24h_pct",  0.0))
        spread_pct      = float(market_data.get("bid_ask_spread_pct",    0.02))
        depth_usd       = float(market_data.get("order_book_depth_usd",  500_000))
        trend_days      = int(market_data.get("trend_persistence",       1))
        round_orders    = float(market_data.get("round_number_order_pct", 0.2))
        declared_organic= bool(market_data.get("is_organic_growth",      True))
        bot_density     = float(market_data.get("bot_order_ratio",       0.3))
        entity_coord    = float(market_data.get("entity_coordination",   0.0))

        # Volume archaeology
        hist = volume_history or [current_volume * 0.9] * 5
        va = self.volume_archaeology(symbol, hist, current_volume, price_change)

        # Price DNA
        prices = price_history or []
        dna = self.price_dna(symbol, prices, round_orders) if prices else None

        # Wash trading
        wt = self.wash_trading_score(current_volume, spread_pct, price_change, va)

        # Spoofing / layering
        sl = self.spoof_layering_score(depth_usd, spread_pct, price_change, current_volume)

        # Pump & dump phase
        pdp = self.detect_pump_dump_phase(price_change, va, trend_days)

        # Pull bot entity attribution if available
        attributed_entities: List[str] = []
        if bot_intelligence:
            try:
                attrs = getattr(bot_intelligence, "attributed_entities", [])
                if callable(attrs):
                    attrs = attrs(symbol)
                attributed_entities = list(attrs)[:5]
            except Exception:
                pass

        # ── Composite organic score ───────────────────────────────────────────
        vol_org  = va.volume_organic_score
        dna_org  = dna.dna_score if dna else 0.70
        wash_org = 1.0 - wt
        sl_org   = 1.0 - sl
        bot_org  = 1.0 - min(1.0, bot_density)
        origin_factor = 1.0 if declared_organic else 0.70

        organic_score = (
            0.30 * vol_org
            + 0.20 * dna_org
            + 0.20 * wash_org
            + 0.15 * sl_org
            + 0.10 * bot_org
            + 0.05 * origin_factor
        )
        organic_score = round(max(0.0, min(1.0, organic_score)), 4)

        # ── Confidence: more data = more certain ─────────────────────────────
        data_richness = sum([
            len(hist) >= 10,
            len(prices) >= 10,
            depth_usd > 0,
            spread_pct > 0,
        ]) / 4.0
        confidence = round(0.5 + data_richness * 0.5, 4)

        # ── Evidence list ─────────────────────────────────────────────────────
        evidence = []
        if va.z_score > VOL_Z_SUSPICIOUS:
            evidence.append(f"Volume {va.z_score:.1f}σ above 30-day baseline ({va.verdict})")
        if va.volume_leads_price:
            evidence.append("Volume leading price — coordinated buy-in detected")
        if dna and dna.hurst_exponent > HURST_SUSPICIOUS:
            evidence.append(f"Hurst exponent {dna.hurst_exponent:.3f} — trend too perfect")
        if dna and dna.staircase_pattern:
            evidence.append("Staircase accumulation pattern detected")
        if wt > 0.35:
            evidence.append(f"Wash trading score {wt:.2f} — volume not moving price")
        if sl > 0.35:
            evidence.append(f"Spoof/layering score {sl:.2f} — fake book depth suspected")
        if pdp not in (PumpDumpPhase.NONE, PumpDumpPhase.UNKNOWN):
            evidence.append(f"Pump & dump phase: {pdp.value.upper()}")
        if not declared_organic:
            evidence.append("Origin flagged as non-organic by taste sense")

        # ── Manipulation types ────────────────────────────────────────────────
        manip_types: List[ManipulationType] = []
        if wt > 0.40:
            manip_types.append(ManipulationType.WASH_TRADING)
        if sl > 0.40:
            manip_types.append(ManipulationType.SPOOFING)
        if pdp == PumpDumpPhase.PUMP:
            manip_types.append(ManipulationType.PUMP_DUMP)
        if entity_coord > 0.60:
            manip_types.append(ManipulationType.COORDINATED)
        if dna and dna.staircase_pattern and organic_score < 0.5:
            manip_types.append(ManipulationType.RAMPING)

        # ── Hz mapping ────────────────────────────────────────────────────────
        if organic_score >= 0.90:
            manip_hz = ORGANIC_SOLFEGGIO["pure"]
        elif organic_score >= 0.75:
            manip_hz = ORGANIC_SOLFEGGIO["slight"]
        elif organic_score >= 0.55:
            manip_hz = ORGANIC_SOLFEGGIO["suspicious"]
        elif organic_score >= 0.35:
            manip_hz = ORGANIC_SOLFEGGIO["manipulated"]
        elif organic_score >= 0.15:
            manip_hz = ORGANIC_SOLFEGGIO["heavy"]
        else:
            manip_hz = ORGANIC_SOLFEGGIO["fraud"]

        # ── Action ────────────────────────────────────────────────────────────
        if organic_score >= 0.80:
            verdict = "natural"
            action  = "engage_normally"
        elif organic_score >= 0.60:
            verdict = "watch"
            action  = "reduce_size_raise_stops"
        elif organic_score >= 0.40:
            verdict = "suspicious"
            action  = "avoid_new_entries"
        elif organic_score >= 0.20:
            verdict = "manipulated"
            action  = "exit_positions"
        else:
            verdict = "extreme_fraud"
            action  = "emergency_exit_alert_authorities"

        return ManipulationProfile(
            symbol=symbol,
            timestamp=ts,
            organic_score=organic_score,
            manipulation_probability=round(1.0 - organic_score, 4),
            confidence=confidence,
            volume_archaeology=va,
            price_dna=dna,
            wash_trade_score=wt,
            spoof_layering_score=sl,
            bot_density=bot_density,
            entity_coordination=entity_coord,
            manipulation_types=manip_types,
            pump_dump_phase=pdp,
            attributed_entities=attributed_entities,
            manipulation_hz=manip_hz,
            evidence=evidence,
            verdict=verdict,
            action=action,
        )


# ─────────────────────────────────────────────────────────────────────────────
# THE SIXTH SENSE — ManipulationChannel
# Slots directly into QueenSensorySystem via the existing registry API
# ─────────────────────────────────────────────────────────────────────────────

class ManipulationChannel:
    """
    The Sixth Sense — market authenticity / manipulation detection.

    Implements SensoryChannel protocol (duck-typed — no hard import needed).
    Plugs into the existing QueenSensorySystem.registry.register() call.

    Hz mapping (discordance = manipulation):
      528 Hz (SOL) — Pure natural market       → LOVE / authentic
      417 Hz (FA)  — Slight concern            → Change coming
      285 Hz (RE)  — Suspicious                → Disrupted flow
      174 Hz (UT)  — Manipulated               → Foundation broken
      111 Hz       — Heavy manipulation        → Off-scale corruption
       33 Hz       — Extreme fraud             → Delta-wave deception
    """
    channel_id   = "manipulation"
    channel_type = "intuition"    # Sixth sense sits in the intuition/violet band
    channel_ready = True

    def __init__(self):
        self._detector = ManipulationDetector()

    def sense(self, stimulus: "SensoryStimulus") -> Optional["SensoryExperience"]:
        """Called by QueenSensorySystem.sense_all()."""
        try:
            return self._sense_impl(stimulus)
        except Exception as exc:
            logger.warning(f"[manipulation] Sensing failed for {stimulus.symbol}: {exc}")
            return None

    def _sense_impl(self, stimulus: "SensoryStimulus") -> "SensoryExperience":
        from aureon.intelligence.aureon_sensory_framework import SensoryExperience

        vol_history   = stimulus.raw_data.get("volume_history_30d", [])
        price_history = stimulus.raw_data.get("price_history_30d",  [])
        bot_intel     = stimulus.raw_data.get("bot_intelligence", None)

        profile = self._detector.analyse(
            symbol=stimulus.symbol,
            market_data=stimulus.market_data,
            volume_history=vol_history,
            price_history=price_history,
            bot_intelligence=bot_intel,
        )

        hz      = profile.manipulation_hz
        organic = profile.organic_score

        # Emotional mapping: manipulation inverts the normal emotional scale
        if organic >= 0.85:
            emotional_state = "Joy"
            emotional_band  = "heart"
            ew              = +0.5
        elif organic >= 0.65:
            emotional_state = "Gratitude"
            emotional_band  = "heart"
            ew              = +0.2
        elif organic >= 0.45:
            emotional_state = "Reason"
            emotional_band  = "heart"
            ew              = -0.1
        elif organic >= 0.25:
            emotional_state = "Dread"
            emotional_band  = "shadow"
            ew              = -0.5
        else:
            emotional_state = "Terror"
            emotional_band  = "shadow"
            ew              = -1.0

        # Intensity: how strong is the manipulation signal?
        intensity = 1.0 - organic

        desc_lines = [
            f"{stimulus.symbol} organic score: {organic:.2f} → {profile.verdict.upper()}.",
            f"Manipulation Hz: {hz:.0f} Hz.",
        ]
        if profile.evidence:
            desc_lines.append("Evidence: " + "; ".join(profile.evidence[:3]))
        if profile.pump_dump_phase != PumpDumpPhase.NONE:
            desc_lines.append(f"P&D Phase: {profile.pump_dump_phase.value.upper()}")

        # Build BrainInput
        brain_input = None
        try:
            from aureon.queen.queen_consciousness_model import BrainInput
            brain_input = BrainInput(
                source="ManipulationSense",
                timestamp=profile.timestamp,
                insight=" ".join(desc_lines),
                confidence=profile.confidence,
                emotional_weight=ew,
                data_payload={
                    "channel":         "manipulation",
                    "organic_score":   organic,
                    "manipulation_hz": hz,
                    "verdict":         profile.verdict,
                    "pump_dump_phase": profile.pump_dump_phase.value,
                    "evidence":        profile.evidence,
                    "action":          profile.action,
                },
            )
        except Exception:
            pass

        return SensoryExperience(
            channel_id="manipulation",
            channel_type="intuition",
            symbol=stimulus.symbol,
            timeframe=stimulus.timeframe,
            timestamp=profile.timestamp,
            hz=hz,
            emotional_state=emotional_state,
            emotional_band=emotional_band,
            emotional_weight=ew,
            intensity=round(intensity, 4),
            quality=round(organic, 4),
            valence=round(organic * 2 - 1, 4),   # -1 (fraud) → +1 (natural)
            confidence=profile.confidence,
            harmonics=[round(hz * (1 / PHI), 2),
                       round(hz * PHI, 2),
                       round(hz * PHI ** 2, 2)],
            description=" ".join(desc_lines),
            action_hint=profile.action,
            brain_input=brain_input,
            raw_output={
                "manipulation_profile": {
                    "organic_score":         organic,
                    "manipulation_probability": profile.manipulation_probability,
                    "verdict":               profile.verdict,
                    "pump_dump_phase":       profile.pump_dump_phase.value,
                    "manipulation_types":    [m.value for m in profile.manipulation_types],
                    "wash_trade_score":      profile.wash_trade_score,
                    "spoof_layering_score":  profile.spoof_layering_score,
                    "bot_density":           profile.bot_density,
                    "volume_z_score":        profile.volume_archaeology.z_score
                                             if profile.volume_archaeology else None,
                    "hurst_exponent":        profile.price_dna.hurst_exponent
                                             if profile.price_dna else None,
                    "attributed_entities":   profile.attributed_entities,
                    "evidence":              profile.evidence,
                    "action":                profile.action,
                },
            },
        )

    def channel_info(self) -> Dict:
        return {
            "channel_id":     self.channel_id,
            "channel_type":   self.channel_type,
            "ready":          self.channel_ready,
            "centre_hz":      285,
            "colour":         "#8B00FF",
            "spectrum_label": "Violet/6th",
            "description":    "manipulation detection — the sixth sense",
        }

    @staticmethod
    def _make_brain_input(source, stimulus, experience):
        return experience.brain_input


# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL MARKET ORGANISM
# ─────────────────────────────────────────────────────────────────────────────

class GlobalMarketOrganism:
    """
    The entire blockchain / global market as one living sensory entity.

    Each asset is a MarketNode (sensory organ). Together they form a body.
    When one organ is sick (manipulated) the body can feel it through the
    cross-asset contagion system.

    Use sense_ecosystem() to get a full-body health report.
    """

    def __init__(self):
        self._nodes: Dict[str, MarketNode] = {}
        self._detector = ManipulationDetector()
        # Bootstrap with well-known nodes
        self._bootstrap_known_nodes()

    def _bootstrap_known_nodes(self) -> None:
        """Seed the organism with known market nodes and their fingerprints."""
        known = [
            # (symbol, type, daily_vol_usd, natural_hurst, downstream)
            ("BTC",  AssetType.CRYPTO,    40_000_000_000, 0.55, ["ETH","BNB","SOL","ALTs"]),
            ("ETH",  AssetType.CRYPTO,    20_000_000_000, 0.57, ["ERC20s","DeFi"]),
            ("BNB",  AssetType.CRYPTO,     3_000_000_000, 0.60, ["BSC_tokens"]),
            ("SOL",  AssetType.CRYPTO,     2_500_000_000, 0.62, ["SOL_NFTs"]),
            ("XRP",  AssetType.CRYPTO,     1_500_000_000, 0.58, ["XRP_ecosystem"]),
            ("SPY",  AssetType.STOCK,     30_000_000_000, 0.52, ["US_equities"]),
            ("GOLD", AssetType.COMMODITY,  5_000_000_000, 0.48, ["Silver","Miners"]),
            ("OIL",  AssetType.COMMODITY,  8_000_000_000, 0.51, ["Energy_stocks"]),
        ]
        for sym, typ, vol, hurst, downstream in known:
            self._nodes[sym] = MarketNode(
                symbol=sym, asset_type=typ,
                natural_daily_volume_usd=vol,
                natural_volatility_pct=2.5 if typ == AssetType.CRYPTO else 0.8,
                natural_hurst=hurst,
                downstream_influence=downstream,
            )

    def register_node(self, symbol: str, asset_type: AssetType = AssetType.CRYPTO,
                      natural_volume_usd: float = 1_000_000,
                      natural_hurst: float = 0.55,
                      downstream: Optional[List[str]] = None) -> MarketNode:
        """Add a new asset to the organism's awareness."""
        node = MarketNode(
            symbol=symbol, asset_type=asset_type,
            natural_daily_volume_usd=natural_volume_usd,
            natural_hurst=natural_hurst,
            downstream_influence=downstream or [],
        )
        self._nodes[symbol] = node
        logger.info(f"[Organism] Registered node: {symbol} ({asset_type.value})")
        return node

    def analyse_node(self, symbol: str,
                     market_data: Dict[str, Any],
                     volume_history: Optional[List[float]] = None,
                     price_history: Optional[List[float]] = None) -> ManipulationProfile:
        """Run full manipulation analysis on a single node."""
        # Ensure node exists
        if symbol not in self._nodes:
            self.register_node(symbol)
        node = self._nodes[symbol]

        profile = self._detector.analyse(
            symbol=symbol,
            market_data=market_data,
            volume_history=volume_history,
            price_history=price_history,
        )
        node.manipulation_profile = profile
        node.pump_dump_phase       = profile.pump_dump_phase
        node.last_updated          = time.time()

        # Determine organism role
        if profile.pump_dump_phase in (PumpDumpPhase.PUMP, PumpDumpPhase.DISTRIBUTION):
            node.organism_role = OrganismRole.DISRUPTOR
        elif profile.organic_score >= 0.85:
            node.organism_role = OrganismRole.PRODUCER
        elif profile.organic_score >= 0.60:
            node.organism_role = OrganismRole.AMPLIFIER
        else:
            node.organism_role = OrganismRole.DISRUPTOR

        return profile

    def sense_ecosystem(self,
                        market_data_map: Dict[str, Dict[str, Any]],
                        volume_history_map: Optional[Dict[str, List[float]]] = None,
                        price_history_map: Optional[Dict[str, List[float]]] = None
                        ) -> EcosystemReport:
        """
        Full organism health report.

        Pass in a dict of {symbol: market_data} for every asset you want to
        sense. Returns a single EcosystemReport representing the entire body.
        """
        profiles: List[ManipulationProfile] = []
        active_count = 0

        for sym, md in market_data_map.items():
            vol_hist   = (volume_history_map or {}).get(sym)
            price_hist = (price_history_map  or {}).get(sym)
            profile = self.analyse_node(sym, md, vol_hist, price_hist)
            profiles.append(profile)
            active_count += 1

        if not profiles:
            return EcosystemReport(
                timestamp=time.time(),
                nodes_monitored=len(self._nodes),
                nodes_active=0,
                organism_health_score=0.5,
                organic_flow_score=0.5,
                manipulation_index=0.5,
                coherence=0.5,
                grand_verdict="No live data provided.",
                recommended_posture="wait",
            )

        # ── Aggregate organism health ─────────────────────────────────────────
        org_scores    = [p.organic_score for p in profiles]
        organism_health = statistics.mean(org_scores)
        # Volume-weighted organic flow (weight by manipulation probability)
        organic_flow  = statistics.mean(org_scores)
        manip_index   = 1.0 - organism_health
        coherence     = 1.0 - (statistics.stdev(org_scores) if len(org_scores) > 1 else 0.0)

        # ── Hot spots (worst first) ───────────────────────────────────────────
        hotspots = sorted(profiles, key=lambda p: p.organic_score)[:5]
        hotspots = [h for h in hotspots if h.organic_score < 0.70]

        # ── Active P&D operations ─────────────────────────────────────────────
        active_pd = []
        for p in profiles:
            if p.pump_dump_phase not in (PumpDumpPhase.NONE, PumpDumpPhase.UNKNOWN):
                active_pd.append({
                    "symbol": p.symbol,
                    "phase":  p.pump_dump_phase.value,
                    "organic_score": p.organic_score,
                    "evidence": p.evidence[:2],
                })

        # ── Dominant entities (who is running the manipulation?) ──────────────
        entity_counts: Dict[str, int] = {}
        for p in profiles:
            for e in p.attributed_entities:
                entity_counts[e] = entity_counts.get(e, 0) + 1
        dominant_entities = sorted(entity_counts, key=entity_counts.get, reverse=True)[:3]

        # ── Cross-asset contagion ─────────────────────────────────────────────
        contagion_alerts: List[str] = []
        for p in profiles:
            if p.pump_dump_phase == PumpDumpPhase.DUMP:
                node = self._nodes.get(p.symbol)
                if node and node.downstream_influence:
                    for downstream in node.downstream_influence:
                        contagion_alerts.append(
                            f"DUMP in {p.symbol} — expect contagion in {downstream}"
                        )
            elif p.pump_dump_phase == PumpDumpPhase.PUMP:
                node = self._nodes.get(p.symbol)
                if node and node.downstream_influence:
                    contagion_alerts.append(
                        f"PUMP in {p.symbol} — coordinated spread to "
                        f"{', '.join(node.downstream_influence[:2])} likely"
                    )

        # ── Dominant Hz (manipulation weighted) ───────────────────────────────
        hz_values = [p.manipulation_hz for p in profiles]
        dom_hz    = statistics.mean(hz_values)

        # ── Grand verdict ─────────────────────────────────────────────────────
        if organism_health >= 0.85:
            verdict = (
                f"The organism is healthy. {active_count} assets sensed, mean organic "
                f"score {organism_health:.2f}. The blockchain is breathing naturally."
            )
            posture = "engage"
        elif organism_health >= 0.65:
            verdict = (
                f"The organism shows early infection. {len(hotspots)} assets below "
                f"0.70 organic score. Caution advised: {', '.join(h.symbol for h in hotspots[:3])}."
            )
            posture = "reduce"
        elif organism_health >= 0.45:
            verdict = (
                f"Widespread manipulation detected across {active_count} assets. "
                f"Mean organic {organism_health:.2f}. Active P&D operations: "
                f"{len(active_pd)}. The organism is sick."
            )
            posture = "avoid"
        else:
            verdict = (
                f"CRITICAL: Organism under heavy coordinated attack. "
                f"Manipulation index {manip_index:.2f}. "
                f"Active P&D: {len(active_pd)}. "
                f"Dominant operators: {', '.join(dominant_entities or ['unknown'])}. "
                f"FLEE."
            )
            posture = "flee"

        self._publish_ecosystem(organism_health, dom_hz, active_pd)

        return EcosystemReport(
            timestamp=time.time(),
            nodes_monitored=len(self._nodes),
            nodes_active=active_count,
            organism_health_score=round(organism_health, 4),
            organic_flow_score=round(organic_flow, 4),
            manipulation_index=round(manip_index, 4),
            coherence=round(max(0.0, min(1.0, coherence)), 4),
            manipulation_hotspots=hotspots,
            active_pump_dumps=active_pd,
            dominant_entities=dominant_entities,
            contagion_alerts=contagion_alerts,
            dominant_hz=round(dom_hz, 1),
            grand_verdict=verdict,
            recommended_posture=posture,
        )

    @staticmethod
    def _publish_ecosystem(health: float, hz: float, active_pd: List[Dict]) -> None:
        """Publish organism health to ThoughtBus."""
        try:
            from aureon.core.aureon_thought_bus import get_thought_bus, Thought
            tb = get_thought_bus()
            tb.publish(Thought(
                source="global_market_organism",
                topic="organism.ecosystem.report",
                payload={
                    "organism_health": health,
                    "dominant_hz": hz,
                    "active_pump_dumps": len(active_pd),
                    "pump_dump_symbols": [p["symbol"] for p in active_pd],
                },
            ))
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRATION HELPER — wire the sixth sense into QueenSensorySystem
# ─────────────────────────────────────────────────────────────────────────────

def register_manipulation_sense(queen_senses=None) -> ManipulationChannel:
    """
    Register the ManipulationChannel (sixth sense) into QueenSensorySystem.

    Call once at startup:
        from aureon_market_organism import register_manipulation_sense
        register_manipulation_sense()

    Or pass an existing instance:
        senses = get_queen_senses()
        register_manipulation_sense(senses)

    The channel will appear in sense_all(), RainbowReport, and rainbow_status().
    """
    if queen_senses is None:
        from aureon.intelligence.aureon_sensory_framework import get_queen_senses
        queen_senses = get_queen_senses()

    ch = ManipulationChannel()
    queen_senses.registry.register(ch)
    logger.info("[MarketOrganism] ManipulationChannel (sixth sense) registered")
    return ch


# ─────────────────────────────────────────────────────────────────────────────
# SINGLETONS
# ─────────────────────────────────────────────────────────────────────────────

_organism: Optional[GlobalMarketOrganism] = None


def get_organism() -> GlobalMarketOrganism:
    global _organism
    if _organism is None:
        _organism = GlobalMarketOrganism()
    return _organism


# ─────────────────────────────────────────────────────────────────────────────
