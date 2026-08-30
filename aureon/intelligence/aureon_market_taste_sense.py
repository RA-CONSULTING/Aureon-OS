#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  👑🧬📈  AUREON MARKET TASTE SENSE  📈🧬👑                                ║
║  ─────────────────────────────────────────────────────────────────────────  ║
║  "She can taste the markets."                                               ║
║                                                                              ║
║  The molecular sequencer was built for food compounds — but frequencies      ║
║  are universal. A bull market has a taste. A bubble has a taste. The         ║
║  moment a good thing turns bad has a very specific taste: sweet-turning-     ║
║  sour, like honey left too long — the Hz drops, the emotional band           ║
║  descends from peak to heart, and sourness crosses sweetness.                ║
║                                                                              ║
║  THE GREAT QUESTION ANSWERED IN THREE PARTS:                                ║
║                                                                              ║
║  1. SWEET / SOUR / SAVOURY — What is this market's taste right now?         ║
║     Sweet   = strong uptrend, high momentum, joy resonance (>620 Hz)        ║
║     Sour    = declining, negative momentum, fear resonance (<528 Hz)        ║
║     Savoury = balanced, sustainable, complex — the Goldilocks zone           ║
║     Bitter  = warning signals present, deterioration beginning               ║
║                                                                              ║
║  2. SWEET TURNING SOUR — When does a good thing go bad?                     ║
║     Detected via: Hz decay + binding loosening + bitterness rising +        ║
║     Too-Much Index crossing threshold                                        ║
║                                                                              ║
║  3. HOW MUCH IS TOO MUCH — The overextension threshold                      ║
║     The Too-Much Index: duration at peak sweetness × overextension ×         ║
║     binding looseness × volatility spikes                                    ║
║                                                                              ║
║  MOLECULAR MARKET MAPPING:                                                   ║
║    sweetness_potency → momentum strength (0-20 000 scale)                   ║
║    receptor_kd_um    → trend persistence (low Kd = sticky trend)            ║
║    functional_groups → market breadth (correlated assets moving)            ║
║    heteroatom_count  → market anomalies (volume spikes, news events)        ║
║    molecular_weight  → asset size (BTC=heavy/stable, altcoins=light)        ║
║    origin            → provider-observed or receipt-derived provenance      ║
║                                                                              ║
║  Gary Leckey | March 2026 | "The balance of the great question"             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import hashlib
import math
import time
import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple, Union

from aureon.intelligence.aureon_taste_sense import (
    MolecularData,
    MolecularSequencer,
    TasteExperience,
    TASTE_FREQUENCY_BANDS,
    LOVE_FREQUENCY,
    PHI,
)

logger = logging.getLogger("market_taste_sense")

# ─────────────────────────────────────────────────────────────────────────────
# MARKET MOLECULE CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# Maximum momentum %  (absolute) mapped to sweetness scale
# 300% 24h move = Illumination level sweetness (like Advantame 20 000×)
MAX_MOMENTUM_PCT = 300.0

# Trend persistence scale — bars/periods in the same direction
# 20 consecutive up-bars = near-zero Kd (very tight "binding")
MAX_PERSISTENCE_BARS = 20

# Market breadth ceiling: 25 correlated assets moving together
MAX_BREADTH = 25

# Max anomaly events (volume spikes, gap fills, news) in window
MAX_ANOMALY_COUNT = 15

# Evidence freshness is deliberately short because taste outputs can become
# action-facing through the sensory framework. The clock is injectable so
# offline tests never need network or wall-clock access.
MAX_RECEIPT_AGE_SECONDS = 120.0
FUTURE_SKEW_SECONDS = 5.0
REAL_TRUTH_STATUSES = {"real_observed", "real_derived"}

# Hz decay threshold per period that signals "turning sour"
HZ_DECAY_THRESHOLD = 50.0     # drop of 50+ Hz per observation = turning sour
TOO_MUCH_THRESHOLD  = 0.72    # Too-Much Index above this → overextended


def _finite(
    value: Any,
    *,
    positive: bool = False,
    nonnegative: bool = False,
) -> Optional[float]:
    """Return a finite numeric value without substituting missing evidence."""
    if isinstance(value, bool):
        return None
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


def _canonical_symbol(value: Any) -> str:
    return str(value or "").strip().upper().replace("/", "").replace("-", "")


def _no_data(reason: str, *, symbol: Any = None) -> Dict[str, Any]:
    """Return a numeric-free, non-mutating operational no-data envelope."""
    canonical_symbol = _canonical_symbol(symbol)
    return {
        "status": "no_data",
        "truth_status": "no_data",
        "reason": reason,
        "symbol": canonical_symbol or None,
        "generated_values": False,
        "action": False,
        "accounting": False,
        "learning": False,
        "eligible_for_action": False,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
    }


# ─────────────────────────────────────────────────────────────────────────────
# MARKET FLAVOUR SPECTRUM
# ─────────────────────────────────────────────────────────────────────────────
#
# Maps taste_score → market flavour profile
#
#  0.00–0.20  → Sour      (400 Hz / Reason)      declining / crashed
#  0.20–0.40  → Bitter    (528 Hz / Gratitude)   recovering but scarred
#  0.40–0.55  → Savoury   (540 Hz / Joy)         balanced, sustainable ← IDEAL
#  0.55–0.75  → Sweet     (620 Hz / Compassion)  strong uptrend
#  0.75–0.88  → Very Sweet (700 Hz / Ecstasy)    overbought / late bull
#  0.88–1.00  → Dangerously Sweet (800 Hz / Illumination) — bubble / mania
#
MARKET_FLAVOUR_BANDS = [
    # (min_score, max_score, flavour,            warning)
    (0.00, 0.20, "sour",               "Market crashed or deeply negative"),
    (0.20, 0.40, "bitter",             "Recovering but risk of further decline"),
    (0.40, 0.55, "savoury",            "Balanced, sustainable — the sweet spot"),
    (0.55, 0.75, "sweet",              "Strong uptrend, momentum healthy"),
    (0.75, 0.88, "very_sweet",         "Overbought — watch for turning point"),
    (0.88, 1.01, "dangerously_sweet",  "Bubble / mania — peak sweetness IMMINENT SOUR"),
]


# ─────────────────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MarketMolecule:
    """
    A market condition expressed as a molecular analog.

    The mapping:
      sweetness_potency = abs(price_change_24h_pct) × scale  (momentum magnitude)
      receptor_kd_um    = 10 / max(trend_persistence, 0.1)   (how sticky the move is)
      functional_group_count = n_correlated_assets            (breadth)
      heteroatom_count  = n_anomaly_events                    (disruption count)
      molecular_weight  = receipt-backed asset weight         (size / stability)
      origin            = receipt truth status                 (observed vs derived)
    """
    symbol: str
    timeframe: str

    # Every input is required from the accepted market receipt. There are no
    # operational numeric defaults and no symbol-to-weight lookup table.
    price_change_24h_pct: float
    price_change_7d_pct: float
    trend_persistence: float
    n_correlated_moving: int
    n_anomaly_events: int
    asset_weight: float
    origin: str

    def to_molecular_data(self) -> MolecularData:
        """Convert market state → MolecularData for the taste sequencer."""

        # ── sweetness_potency: momentum magnitude on 0–20 000 scale ──────────
        # Positive momentum = sweet; negative = effectively 0 (sour compounds
        # have zero sweetness potency — the sourness comes from missing sweetness
        # and from high binding disruption).
        pos_momentum = max(0.0, self.price_change_24h_pct)
        sweetness_potency = (pos_momentum / MAX_MOMENTUM_PCT) * 20_000.0

        # Negative momentum adds "sour" character by dropping sweetness to zero
        # and driving Kd toward max (loose binding = trend doesn't hold)
        neg_momentum = abs(min(0.0, self.price_change_24h_pct))

        # ── receptor_kd_um: persistence / stickiness (lower = tighter trend) ─
        # Negative momentum increases effective Kd (falling markets are not
        # "binding" — they slip away fast)
        base_kd = 10.0 / max(self.trend_persistence, 0.5)
        sour_kd_boost = (neg_momentum / MAX_MOMENTUM_PCT) * 8.0  # up to +8 µM for -300% crash
        receptor_kd_um = min(10.0, base_kd + sour_kd_boost)

        # ── functional_group_count: market breadth ────────────────────────────
        functional_group_count = max(0, min(MAX_BREADTH, self.n_correlated_moving))

        # ── heteroatom_count: disruption / anomaly events ─────────────────────
        heteroatom_count = max(0, min(MAX_ANOMALY_COUNT, self.n_anomaly_events))

        # ── molecular_weight: asset stability proxy ───────────────────────────
        return MolecularData(
            name=f"{self.symbol} ({self.timeframe})",
            formula=f"MKT-{self.symbol}",
            molecular_weight=self.asset_weight,
            sweetness_potency=max(0.0, sweetness_potency),
            receptor_kd_um=receptor_kd_um,
            functional_group_count=functional_group_count,
            heteroatom_count=heteroatom_count,
            smiles=f"[MKT:{self.symbol}]",
            origin=self.origin,
            notes=(
                f"24h={self.price_change_24h_pct:+.2f}% "
                f"7d={self.price_change_7d_pct:+.2f}% "
                f"persist={self.trend_persistence:.1f}bars "
                f"breadth={self.n_correlated_moving} "
                f"anomalies={self.n_anomaly_events}"
            ),
        )


@dataclass
class MarketTasteProfile:
    """
    Full gustatory analysis of a market condition.

    Answers the three-part Great Question:
      1. What flavour is this?          → taste_category
      2. Is it turning sour?            → turning_point_score
      3. How much is too much?          → too_much_index
    """
    symbol: str
    timeframe: str
    timestamp: float

    # ── Core taste dimensions ─────────────────────────────────────────────────
    taste_score: float          # 0–1 composite quality (higher = sweeter)
    primary_hz: float           # Emotional resonance frequency
    emotional_state: str        # e.g. "Compassion", "Ecstasy"
    emotional_band: str         # "heart" | "spirit" | "peak"

    # ── Flavour profile (0–1 each, sum ≈ 1) ──────────────────────────────────
    sweetness: float            # Uptrend strength / positive momentum
    sourness: float             # Downtrend / deterioration
    savouriness: float          # Balance, complexity, sustainability
    bitterness: float           # Warning signals / early deterioration

    # ── The Great Question ────────────────────────────────────────────────────
    taste_category: str         # "sweet" | "sour" | "savoury" | "bitter" |
                                # "very_sweet" | "dangerously_sweet" |
                                # "sweet_turning_sour"
    turning_point_score: float  # 0–1: probability sweet→sour reversal imminent
    too_much_index: float       # 0–1: overextension of the good thing
    duration_factor: float      # Exact Too-Much duration component
    extension_factor: float     # Exact Too-Much extension component
    binding_factor: float       # Exact Too-Much binding component
    anomaly_factor: float       # Exact Too-Much anomaly component
    balance_score: float        # 0–1: peaks at 0.5 (savoury = perfect balance)

    # ── Queen's verdict ───────────────────────────────────────────────────────
    queen_verdict: str          # Natural language summary
    action_hint: str            # e.g. "hold_sweet" | "prepare_sour" | "savoury_caution"

    # ── Evidence and receipt provenance ──────────────────────────────────────
    origin: str                 # "provider_observed" | "receipt_derived"
    venue: str
    source_id: str
    source_timestamp: float
    received_at: float
    receipt_id: str
    input_receipt_ids: Tuple[str, ...]
    truth_status: str
    generated_values: bool
    evidence_complete: bool
    eligible_for_action: bool
    eligible_for_accounting: bool
    eligible_for_learning: bool
    hnc_coherence: float
    auris_coherence: float
    hnc_gate_open: bool
    auris_gate_open: bool

    # ── Raw taste experience (from MolecularSequencer) ───────────────────────
    taste_experience: Optional[TasteExperience] = None

    # ── Hz history for trend tracking ────────────────────────────────────────
    hz_history: List[float] = field(default_factory=list)


@dataclass
class SweetToSourAnalysis:
    """
    The Great Question Part 2: When does a good thing turn bad?

    A sweet market "turns sour" when:
      • Hz decays from peak/spirit bands toward heart bands
      • too_much_index crosses TOO_MUCH_THRESHOLD (0.72)
      • bitterness component rises above 0.25
      • binding looseness increases (Kd moving toward 10 µM)
    """
    symbol: str
    currently_sweet: bool           # Is the market currently sweet?
    turning_point_imminent: bool    # Is the turn happening now?
    turning_point_score: float      # 0–1 probability
    hz_trend: str                   # "ascending" | "stable" | "descending"
    hz_decay_per_period: float      # Average Hz drop (negative = ascending)
    periods_at_sweet: int           # How long it has been sweet
    too_much_index: float
    bitterness_trend: str           # "rising" | "stable" | "falling"
    estimated_bars_to_turn: Optional[int]  # None if not turning
    diagnosis: str                  # Human-readable diagnosis
    action: str                     # Recommended action
    input_receipt_ids: Tuple[str, ...] = field(default_factory=tuple)
    truth_status: str = "no_data"
    generated_values: bool = False
    eligible_for_action: bool = False
    eligible_for_accounting: bool = False
    eligible_for_learning: bool = False


@dataclass
class TooMuchAnalysis:
    """
    The Great Question Part 3: How much of a good thing until it leaves a bad taste?

    Too-Much Index = weighted combination of:
      • Duration factor   : how long at high sweetness (>0.6 score)
      • Extension factor  : how far above the "savoury zone" (0.40–0.55)
      • Binding factor    : is the trend losing grip? (Kd rising)
      • Anomaly factor    : are warning signals accumulating?
    """
    symbol: str
    too_much_index: float           # 0–1 composite
    duration_factor: float          # 0–1: time at high sweetness
    extension_factor: float         # 0–1: distance above savoury zone
    binding_factor: float           # 0–1: trend loosening
    anomaly_factor: float           # 0–1: warning signals
    threshold: float = TOO_MUCH_THRESHOLD
    is_overextended: bool = False
    sweetness_quota_remaining: float = 1.0  # How much "sweet" is left
    verdict: str = ""
    the_answer: str = ""            # Direct answer to "how much is too much"
    input_receipt_ids: Tuple[str, ...] = field(default_factory=tuple)
    truth_status: str = "no_data"
    generated_values: bool = False
    eligible_for_action: bool = False
    eligible_for_accounting: bool = False
    eligible_for_learning: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class MarketTasteSense:
    """
    Queen Sero tastes the market.

    Operational calls require linked market, HNC, and Auris receipts. Raw
    feature dictionaries are not interpreted as provider observations.
    """

    def __init__(
        self,
        history_depth: int = 50,
        *,
        sequencer: Optional[MolecularSequencer] = None,
        clock: Callable[[], float] = time.time,
        max_receipt_age_seconds: float = MAX_RECEIPT_AGE_SECONDS,
        future_skew_seconds: float = FUTURE_SKEW_SECONDS,
    ):
        if isinstance(history_depth, bool) or history_depth < 1:
            raise ValueError("history_depth must be a positive integer")
        self._sequencer = sequencer or MolecularSequencer()
        self._clock = clock
        self._max_receipt_age_seconds = float(max_receipt_age_seconds)
        self._future_skew_seconds = float(future_skew_seconds)
        self._history_depth = history_depth
        # Per-symbol deque of MarketTasteProfile (most recent last)
        self._profiles: Dict[str, deque] = {}
        self._seen_receipt_ids: set[str] = set()
        self._last_market_source_timestamp: Dict[Tuple[str, str, str], float] = {}

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _history_for_write(self, symbol: str) -> deque:
        if symbol not in self._profiles:
            self._profiles[symbol] = deque(maxlen=self._history_depth)
        return self._profiles[symbol]

    def _history_for_read(self, symbol: str) -> Tuple[MarketTasteProfile, ...]:
        history = self._profiles.get(_canonical_symbol(symbol))
        return tuple(history) if history is not None else ()

    def _receipt_times(
        self,
        receipt: Mapping[str, Any],
        now: float,
    ) -> Optional[Tuple[float, float]]:
        source_timestamp = _finite(receipt.get("source_timestamp"), positive=True)
        received_at = _finite(receipt.get("received_at"), positive=True)
        if (
            source_timestamp is None
            or received_at is None
            or source_timestamp > received_at + self._future_skew_seconds
            or received_at > now + self._future_skew_seconds
            or now - source_timestamp > self._max_receipt_age_seconds
            or now - received_at > self._max_receipt_age_seconds
        ):
            return None
        return source_timestamp, received_at

    @staticmethod
    def _linked_ids(receipt: Mapping[str, Any]) -> Optional[set[str]]:
        values = receipt.get("input_receipt_ids")
        if not isinstance(values, (list, tuple, set)) or not values:
            return None
        linked = {str(value).strip() for value in values if str(value).strip()}
        return linked or None

    def _validate_evidence(
        self,
        symbol: str,
        timeframe: str,
        market_data: Mapping[str, Any],
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Validate one linked, fresh, same-venue evidence chain."""
        canonical_symbol = _canonical_symbol(symbol)
        canonical_timeframe = str(timeframe or "").strip().lower()
        if not canonical_symbol or not canonical_timeframe:
            return None, "symbol_and_timeframe_required"
        if not isinstance(market_data, Mapping):
            return None, "market_data_mapping_required"

        receipt_specs = (
            ("market", market_data.get("market_receipt"), "market_snapshot"),
            ("hnc", market_data.get("hnc_receipt"), "hnc_coherence"),
            ("auris", market_data.get("auris_receipt"), "auris_coherence"),
        )
        now = _finite(self._clock(), positive=True)
        if now is None:
            return None, "valid_clock_required"

        normalized: Dict[str, Dict[str, Any]] = {}
        for label, candidate, expected_type in receipt_specs:
            if not isinstance(candidate, Mapping):
                return None, f"{label}_receipt_required"
            receipt_id = str(candidate.get("receipt_id") or "").strip()
            source_id = str(candidate.get("source_id") or "").strip()
            venue = str(candidate.get("venue") or "").strip().lower()
            receipt_symbol = _canonical_symbol(candidate.get("symbol"))
            receipt_timeframe = str(candidate.get("timeframe") or "").strip().lower()
            times = self._receipt_times(candidate, now)
            if (
                str(candidate.get("receipt_type") or "").strip().lower() != expected_type
                or not receipt_id
                or not source_id
                or not venue
                or receipt_symbol != canonical_symbol
                or receipt_timeframe != canonical_timeframe
                or times is None
                or candidate.get("truth_status") not in REAL_TRUTH_STATUSES
                or candidate.get("generated_values") is not False
                or type(candidate.get("eligible_for_action")) is not bool
                or type(candidate.get("eligible_for_accounting")) is not bool
                or type(candidate.get("eligible_for_learning")) is not bool
            ):
                return None, f"{label}_receipt_incomplete_or_untrusted"
            normalized[label] = {
                **candidate,
                "receipt_id": receipt_id,
                "source_id": source_id,
                "venue": venue,
                "symbol": receipt_symbol,
                "timeframe": receipt_timeframe,
                "source_timestamp": times[0],
                "received_at": times[1],
            }

        market = normalized["market"]
        hnc = normalized["hnc"]
        auris = normalized["auris"]
        ids = (market["receipt_id"], hnc["receipt_id"], auris["receipt_id"])
        if len(set(ids)) != len(ids):
            return None, "receipt_ids_must_be_unique"
        if any(receipt_id in self._seen_receipt_ids for receipt_id in ids):
            return None, "receipt_replay_rejected"
        if len({market["venue"], hnc["venue"], auris["venue"]}) != 1:
            return None, "same_venue_receipts_required"
        if not (
            market["source_timestamp"]
            <= hnc["source_timestamp"]
            <= auris["source_timestamp"]
            and market["received_at"]
            <= hnc["received_at"]
            <= auris["received_at"]
        ):
            return None, "monotonic_receipt_chain_required"

        hnc_links = self._linked_ids(hnc)
        auris_links = self._linked_ids(auris)
        if hnc_links is None or market["receipt_id"] not in hnc_links:
            return None, "hnc_receipt_must_link_market_receipt"
        if (
            auris_links is None
            or market["receipt_id"] not in auris_links
            or hnc["receipt_id"] not in auris_links
        ):
            return None, "auris_receipt_must_link_market_and_hnc_receipts"

        price_change_24h_pct = _finite(market.get("price_change_24h_pct"))
        price_change_7d_pct = _finite(market.get("price_change_7d_pct"))
        trend_persistence = _finite(market.get("trend_persistence"), positive=True)
        breadth = _finite(market.get("n_correlated_moving"), nonnegative=True)
        anomalies = _finite(market.get("n_anomaly_events"), nonnegative=True)
        asset_weight = _finite(market.get("asset_weight"), positive=True)
        if (
            any(
                value is None
                for value in (
                    price_change_24h_pct,
                    price_change_7d_pct,
                    trend_persistence,
                    breadth,
                    anomalies,
                    asset_weight,
                )
            )
            or not breadth.is_integer()
            or not anomalies.is_integer()
        ):
            return None, "complete_finite_market_metrics_required"

        hnc_coherence = _finite(hnc.get("coherence"), nonnegative=True)
        auris_coherence = _finite(auris.get("coherence"), nonnegative=True)
        if (
            hnc_coherence is None
            or auris_coherence is None
            or hnc_coherence > 1.0
            or auris_coherence > 1.0
            or type(hnc.get("gate_open")) is not bool
            or type(auris.get("gate_open")) is not bool
        ):
            return None, "complete_finite_hnc_auris_metrics_required"

        chronology_key = (market["venue"], canonical_symbol, canonical_timeframe)
        last_timestamp = self._last_market_source_timestamp.get(chronology_key)
        if last_timestamp is not None and market["source_timestamp"] <= last_timestamp:
            return None, "newer_market_receipt_required"
        existing = self._profiles.get(canonical_symbol)
        if existing and (
            existing[-1].venue != market["venue"]
            or existing[-1].timeframe.lower() != canonical_timeframe
        ):
            return None, "history_requires_same_venue_and_timeframe"

        market.update(
            {
                "price_change_24h_pct": price_change_24h_pct,
                "price_change_7d_pct": price_change_7d_pct,
                "trend_persistence": trend_persistence,
                "n_correlated_moving": int(breadth),
                "n_anomaly_events": int(anomalies),
                "asset_weight": asset_weight,
            }
        )
        hnc["coherence"] = hnc_coherence
        auris["coherence"] = auris_coherence
        return {
            "market": market,
            "hnc": hnc,
            "auris": auris,
            "chronology_key": chronology_key,
            "receipt_ids": ids,
        }, None

    def _profile_is_fresh(self, profile: MarketTasteProfile) -> bool:
        now = _finite(self._clock(), positive=True)
        return bool(
            now is not None
            and profile.truth_status == "real_derived"
            and profile.generated_values is False
            and profile.evidence_complete
            and profile.source_timestamp <= profile.received_at + self._future_skew_seconds
            and profile.received_at <= now + self._future_skew_seconds
            and now - profile.source_timestamp <= self._max_receipt_age_seconds
            and now - profile.received_at <= self._max_receipt_age_seconds
        )

    @staticmethod
    def _flavour_from_score(taste_score: float) -> str:
        for min_s, max_s, flavour, _ in MARKET_FLAVOUR_BANDS:
            if min_s <= taste_score < max_s:
                return flavour
        return "dangerously_sweet"

    @staticmethod
    def _decompose_flavours(taste_score: float, kd_norm: float,
                            anomaly_norm: float) -> Tuple[float, float, float, float]:
        """
        Decompose the composite taste score into four distinct flavour components.

        Returns: (sweetness, sourness, savouriness, bitterness)

        Physics:
          sweetness  = taste_score when positive momentum dominant
          sourness   = 1 - taste_score when negative momentum (kd_norm helps)
          savouriness= proximity to 0.5 (the Goldilocks balance)
          bitterness = anomaly presence weighted by how far from balance
        """
        sweetness   = max(0.0, taste_score - 0.40)   / 0.60  # active above 0.40
        sourness    = max(0.0, 0.40 - taste_score)   / 0.40  # active below 0.40
        savouriness = 1.0 - abs(taste_score - 0.475) / 0.475  # peak at 0.475
        savouriness = max(0.0, savouriness)
        bitterness  = anomaly_norm * (1.0 - savouriness)     # anomalies bite more when unbalanced

        # Normalise so they feel like distinct sensations rather than a strict partition
        total = sweetness + sourness + savouriness + bitterness + 1e-9
        return (
            round(sweetness   / total, 4),
            round(sourness    / total, 4),
            round(savouriness / total, 4),
            round(bitterness  / total, 4),
        )

    @staticmethod
    def _too_much_index(taste_score: float, periods_at_sweet: int,
                        kd_norm: float, anomaly_norm: float) -> Tuple[float, float, float, float, float]:
        """
        Compute the Too-Much Index and its four contributing factors.

        Returns: (tmi, duration_factor, extension_factor, binding_factor, anomaly_factor)
        """
        # Duration: how long above the savoury zone (0.55+)
        sweet_ceiling = min(periods_at_sweet / 30.0, 1.0)  # saturates at 30 periods

        # Extension: how far into the "too sweet" territory
        extension = max(0.0, taste_score - 0.55) / 0.45    # 0 at 0.55, 1.0 at 1.0

        # Binding looseness: kd_norm near 1.0 means trend is slipping
        binding_loose = kd_norm                             # already 0–1

        # Anomaly accumulation: warning signals present
        anomaly = anomaly_norm                              # already 0–1

        tmi = (
            0.40 * sweet_ceiling
            + 0.30 * extension
            + 0.20 * binding_loose
            + 0.10 * anomaly
        )
        return (
            round(min(1.0, tmi), 4),
            round(sweet_ceiling, 4),
            round(extension, 4),
            round(binding_loose, 4),
            round(anomaly, 4),
        )

    @staticmethod
    def _turning_point_score(taste_score: float, hz_decay: float,
                             tmi: float, bitterness: float) -> float:
        """
        Probability (0–1) that a sweet market is about to turn sour.

          • tmi > threshold         → major signal
          • hz_decay > threshold    → direct frequency evidence
          • bitterness rising       → early warning
          • taste still high but decay accelerating → danger zone
        """
        tmi_signal      = min(1.0, max(0.0, (tmi - 0.5) / 0.5))
        hz_signal       = min(1.0, max(0.0, hz_decay / 150.0))   # 150 Hz/period = full signal
        bitter_signal   = min(1.0, bitterness * 3.0)
        sweet_but_decay = taste_score * hz_signal                  # worst when sweet + decaying

        score = (
            0.40 * tmi_signal
            + 0.30 * hz_signal
            + 0.15 * bitter_signal
            + 0.15 * sweet_but_decay
        )
        return round(min(1.0, score), 4)

    # ── PUBLIC API ────────────────────────────────────────────────────────────

    def taste_market(
        self,
        symbol: str,
        market_data: Mapping[str, Any],
        timeframe: str = "24h",
    ) -> Union[MarketTasteProfile, Dict[str, Any]]:
        """
        Taste one market observation only after validating the complete evidence
        chain. The market metrics live in market_receipt; hnc_receipt must link
        that receipt and auris_receipt must link both upstream receipts.
        """
        evidence, reason = self._validate_evidence(symbol, timeframe, market_data)
        if evidence is None:
            return _no_data(reason or "complete_fresh_receipts_required", symbol=symbol)

        market = evidence["market"]
        hnc = evidence["hnc"]
        auris = evidence["auris"]
        canonical_symbol = market["symbol"]
        canonical_timeframe = market["timeframe"]

        # Only still-fresh, already accepted observations influence a new taste.
        history = [
            profile
            for profile in self._history_for_read(canonical_symbol)
            if self._profile_is_fresh(profile)
            and profile.venue == market["venue"]
            and profile.timeframe.lower() == canonical_timeframe
        ]
        recent_hz = [profile.primary_hz for profile in history]

        origin = (
            "provider_observed"
            if market["truth_status"] == "real_observed"
            else "receipt_derived"
        )
        molecule = MarketMolecule(
            symbol=canonical_symbol,
            timeframe=canonical_timeframe,
            price_change_24h_pct=market["price_change_24h_pct"],
            price_change_7d_pct=market["price_change_7d_pct"],
            trend_persistence=market["trend_persistence"],
            n_correlated_moving=market["n_correlated_moving"],
            n_anomaly_events=market["n_anomaly_events"],
            asset_weight=market["asset_weight"],
            origin=origin,
        ).to_molecular_data()

        # Use the genuine canonical sequencing and PHI equations, but deliberately
        # do not call build_experience(): that legacy method creates a BrainInput
        # with a local timestamp and no linked operational receipt.
        properties = self._sequencer.sequence(molecule)
        hz, emotional_state, emotional_band = self._sequencer.map_to_frequency(properties)
        taste_score = properties.taste_score

        kd_norm = molecule.receptor_kd_um / 10.0
        anomaly_norm = molecule.heteroatom_count / MAX_ANOMALY_COUNT
        sweetness, sourness, savouriness, bitterness = self._decompose_flavours(
            taste_score, kd_norm, anomaly_norm
        )

        periods_at_sweet = sum(1 for profile in history if profile.taste_score > 0.55)
        hz_decay = 0.0
        if len(recent_hz) >= 2:
            hz_decay = max(0.0, recent_hz[-1] - hz)

        (
            too_much_index,
            duration_factor,
            extension_factor,
            binding_factor,
            anomaly_factor,
        ) = self._too_much_index(
            taste_score, periods_at_sweet, kd_norm, anomaly_norm
        )
        turning_point_score = self._turning_point_score(
            taste_score, hz_decay, too_much_index, bitterness
        )
        base_category = self._flavour_from_score(taste_score)
        taste_category = (
            "sweet_turning_sour"
            if turning_point_score >= 0.60 and taste_score >= 0.55
            else base_category
        )
        balance_score = max(
            0.0,
            round(1.0 - abs(taste_score - 0.475) / 0.475, 4),
        )

        gates_open = hnc["gate_open"] and auris["gate_open"]
        eligible_for_action = bool(
            gates_open
            and market["eligible_for_action"]
            and hnc["eligible_for_action"]
            and auris["eligible_for_action"]
        )
        eligible_for_learning = bool(
            gates_open
            and market["eligible_for_learning"]
            and hnc["eligible_for_learning"]
            and auris["eligible_for_learning"]
        )

        queen_verdict, candidate_action = self._queen_verdict(
            canonical_symbol,
            taste_score,
            taste_category,
            turning_point_score,
            too_much_index,
            sweetness,
            sourness,
            savouriness,
            hz,
        )
        action_hint = candidate_action if eligible_for_action else "observe_only"
        if not eligible_for_action:
            queen_verdict = (
                f"{queen_verdict} Complete coherence evidence is observational "
                "and does not authorise an action."
            )

        input_receipt_ids = evidence["receipt_ids"]
        digest = hashlib.sha256("|".join(input_receipt_ids).encode("utf-8")).hexdigest()[:24]
        receipt_id = f"market-taste:{digest}"
        source_id = f"market-taste:{market['venue']}"
        harmonics = [
            round(hz * PHI, 2),
            round(hz * PHI ** 2, 2),
            round(hz * PHI ** 3, 2),
        ]
        molecular_resonance = round(
            (molecule.molecular_weight / 1000.0) * LOVE_FREQUENCY,
            3,
        )
        emotional_weight = round(taste_score * 2.0 - 1.0, 4)
        experience = TasteExperience(
            molecule_name=molecule.name,
            formula=molecule.formula,
            primary_frequency=hz,
            emotional_state=emotional_state,
            emotional_band=emotional_band,
            emotional_weight=emotional_weight,
            taste_score=taste_score,
            taste_intensity=properties.sweetness_norm,
            binding_strength=properties.binding_norm,
            harmonic_signature=harmonics,
            molecular_resonance=molecular_resonance,
            sensory_description=queen_verdict,
            brain_input=None,
            data_status="real_derived",
            truth_status="real_derived",
            source_id=source_id,
            source_timestamp=market["source_timestamp"],
            received_at=auris["received_at"],
            receipt_id=receipt_id,
            generated_values=False,
            eligible_for_action=eligible_for_action,
            eligible_for_accounting=False,
            eligible_for_learning=eligible_for_learning,
            sequenced_at=auris["source_timestamp"],
        )

        profile = MarketTasteProfile(
            symbol=canonical_symbol,
            timeframe=canonical_timeframe,
            timestamp=market["source_timestamp"],
            taste_score=round(taste_score, 4),
            primary_hz=hz,
            emotional_state=emotional_state,
            emotional_band=emotional_band,
            sweetness=sweetness,
            sourness=sourness,
            savouriness=savouriness,
            bitterness=bitterness,
            taste_category=taste_category,
            turning_point_score=turning_point_score,
            too_much_index=too_much_index,
            duration_factor=duration_factor,
            extension_factor=extension_factor,
            binding_factor=binding_factor,
            anomaly_factor=anomaly_factor,
            balance_score=balance_score,
            queen_verdict=queen_verdict,
            action_hint=action_hint,
            origin=origin,
            venue=market["venue"],
            source_id=source_id,
            source_timestamp=market["source_timestamp"],
            received_at=auris["received_at"],
            receipt_id=receipt_id,
            input_receipt_ids=input_receipt_ids,
            truth_status="real_derived",
            generated_values=False,
            evidence_complete=True,
            eligible_for_action=eligible_for_action,
            eligible_for_accounting=False,
            eligible_for_learning=eligible_for_learning,
            hnc_coherence=hnc["coherence"],
            auris_coherence=auris["coherence"],
            hnc_gate_open=hnc["gate_open"],
            auris_gate_open=auris["gate_open"],
            taste_experience=experience,
            hz_history=recent_hz + [hz],
        )

        # Mutate internal state only after the complete profile exists. A gate
        # can be observational without being a hard block, but only an explicitly
        # learning-eligible chain may enter taste history.
        self._seen_receipt_ids.update(input_receipt_ids)
        self._last_market_source_timestamp[evidence["chronology_key"]] = market[
            "source_timestamp"
        ]
        if eligible_for_learning:
            self._history_for_write(canonical_symbol).append(profile)
        return profile

    def detect_sweet_to_sour(
        self,
        symbol: str,
    ) -> Union[SweetToSourAnalysis, Dict[str, Any]]:
        """
        Answer: "When does this good thing turn bad?"

        Only still-fresh accepted receipt history can produce an analysis.
        """
        hist = [
            profile
            for profile in self._history_for_read(symbol)
            if self._profile_is_fresh(profile)
        ]
        if not hist:
            return _no_data(
                "fresh_learning_eligible_taste_history_required",
                symbol=symbol,
            )

        latest = hist[-1]

        # ── Hz trend ──────────────────────────────────────────────────────────
        hz_list = [p.primary_hz for p in hist]
        if len(hz_list) >= 3:
            # Linear regression slope proxy (simple: last vs first half)
            mid = len(hz_list) // 2
            early_avg = sum(hz_list[:mid]) / mid
            late_avg  = sum(hz_list[mid:]) / max(1, len(hz_list) - mid)
            avg_decay = early_avg - late_avg   # positive = Hz dropped = bad sign
            if avg_decay > HZ_DECAY_THRESHOLD:
                hz_trend = "descending"
            elif avg_decay < -HZ_DECAY_THRESHOLD:
                hz_trend = "ascending"
            else:
                hz_trend = "stable"
        else:
            avg_decay = 0.0
            hz_trend  = "stable" if len(hz_list) < 2 else (
                "descending" if hz_list[-1] < hz_list[0] else "ascending"
            )

        # ── Bitterness trend ──────────────────────────────────────────────────
        if len(hist) >= 4:
            early_bitter = sum(p.bitterness for p in hist[:len(hist)//2]) / max(1, len(hist)//2)
            late_bitter  = sum(p.bitterness for p in hist[len(hist)//2:]) / max(1, len(hist) - len(hist)//2)
            if late_bitter > early_bitter + 0.05:
                bitterness_trend = "rising"
            elif late_bitter < early_bitter - 0.05:
                bitterness_trend = "falling"
            else:
                bitterness_trend = "stable"
        else:
            bitterness_trend = "unknown"

        currently_sweet       = latest.taste_score >= 0.55
        periods_at_sweet      = sum(1 for p in hist if p.taste_score >= 0.55)
        tmi                   = latest.too_much_index
        tp_score              = latest.turning_point_score
        turning_point_imminent= tp_score >= 0.55

        # ── Estimate bars until turn ──────────────────────────────────────────
        estimated_bars = None
        if currently_sweet and turning_point_imminent and avg_decay > 0:
            # How many more periods before Hz falls below 620 Hz (sweet threshold)?
            hz_to_lose = max(0.0, latest.primary_hz - 620.0)
            if avg_decay > 0:
                estimated_bars = max(1, int(hz_to_lose / max(avg_decay, 1.0)))

        # ── Diagnosis ─────────────────────────────────────────────────────────
        if turning_point_imminent and hz_trend == "descending":
            diagnosis = (
                f"{symbol} is sweet ({latest.taste_score:.2f}) but the Hz is decaying "
                f"({avg_decay:+.0f} Hz/period). Too-Much Index {tmi:.2f}. "
                f"Bitterness {bitterness_trend}. The good thing is turning."
            )
            action = "reduce_exposure"
        elif currently_sweet and tmi > TOO_MUCH_THRESHOLD and hz_trend != "descending":
            diagnosis = (
                f"{symbol} is very sweet ({latest.taste_score:.2f}). "
                f"Too-Much Index {tmi:.2f} — overextended but Hz still holding "
                f"at {latest.primary_hz:.0f} Hz. Monitor closely."
            )
            action = "tighten_stops"
        elif currently_sweet:
            diagnosis = (
                f"{symbol} tastes {latest.taste_category} at {latest.primary_hz:.0f} Hz "
                f"({latest.emotional_state}). {periods_at_sweet} periods at sweet. "
                f"Too-Much Index: {tmi:.2f}. Still healthy."
            )
            action = "hold_sweet"
        else:
            diagnosis = (
                f"{symbol} is {latest.taste_category} at {latest.primary_hz:.0f} Hz. "
                f"Not currently sweet — the turn may have already happened."
            )
            action = "wait_for_recovery" if latest.sourness > 0.4 else "monitor"

        input_receipt_ids = tuple(
            dict.fromkeys(
                receipt_id
                for profile in hist
                for receipt_id in profile.input_receipt_ids
            )
        )
        eligible_for_action = all(profile.eligible_for_action for profile in hist)
        if not eligible_for_action:
            action = "observe_only"
        return SweetToSourAnalysis(
            symbol=symbol,
            currently_sweet=currently_sweet,
            turning_point_imminent=turning_point_imminent,
            turning_point_score=tp_score,
            hz_trend=hz_trend,
            hz_decay_per_period=round(avg_decay, 2),
            periods_at_sweet=periods_at_sweet,
            too_much_index=tmi,
            bitterness_trend=bitterness_trend,
            estimated_bars_to_turn=estimated_bars,
            diagnosis=diagnosis,
            action=action,
            input_receipt_ids=input_receipt_ids,
            truth_status="real_derived",
            generated_values=False,
            eligible_for_action=eligible_for_action,
            eligible_for_accounting=False,
            eligible_for_learning=all(
                profile.eligible_for_learning for profile in hist
            ),
        )

    def how_much_is_too_much(
        self,
        symbol: str,
    ) -> Union[TooMuchAnalysis, Dict[str, Any]]:
        """
        Answer: "How much of a good thing until it leaves a bad taste?"

        Returns a TooMuchAnalysis with the Too-Much Index broken down into its
        four contributing factors and the remaining "sweetness quota".
        """
        hist = [
            profile
            for profile in self._history_for_read(symbol)
            if self._profile_is_fresh(profile)
        ]
        if not hist:
            return _no_data(
                "fresh_learning_eligible_taste_history_required",
                symbol=symbol,
            )

        latest = hist[-1]
        tmi     = latest.too_much_index
        is_over = tmi >= TOO_MUCH_THRESHOLD

        # How much sweetness quota remains before crossing the threshold?
        quota_remaining = max(0.0, min(1.0, (TOO_MUCH_THRESHOLD - tmi) / TOO_MUCH_THRESHOLD))

        # ── The Answer ────────────────────────────────────────────────────────
        if tmi < 0.30:
            the_answer = (
                f"{symbol} is barely sweet. There is plenty of upside remaining "
                f"before this good thing becomes too much. "
                f"Quota remaining: {quota_remaining:.0%}."
            )
        elif tmi < 0.55:
            the_answer = (
                f"{symbol} is pleasantly sweet — like honey in morning tea. "
                f"Enjoy it, but keep an eye on it. "
                f"About {quota_remaining:.0%} sweetness quota left before overextension."
            )
        elif tmi < TOO_MUCH_THRESHOLD:
            the_answer = (
                f"{symbol} is getting very sweet. Like eating too much dessert — "
                f"still enjoyable but the next bite might be one too many. "
                f"{quota_remaining:.0%} quota remaining."
            )
        elif tmi < 0.85:
            the_answer = (
                f"{symbol} has crossed the too-much threshold. This good thing "
                f"has already overstayed its welcome. The bad taste is beginning. "
                f"Quota exhausted — consider reducing position."
            )
        else:
            the_answer = (
                f"{symbol} is at peak sweetness — {latest.emotional_state} at "
                f"{latest.primary_hz:.0f} Hz. Maximum overextension. The bad aftertaste "
                f"is inevitable. Artificial sweeteners always leave a bitter finish."
            )

        # Verdict
        if is_over:
            verdict = f"OVEREXTENDED (TMI={tmi:.2f} > threshold {TOO_MUCH_THRESHOLD})"
        else:
            verdict = f"Within bounds (TMI={tmi:.2f}, {quota_remaining:.0%} quota left)"

        return TooMuchAnalysis(
            symbol=symbol,
            too_much_index=tmi,
            duration_factor=latest.duration_factor,
            extension_factor=latest.extension_factor,
            binding_factor=latest.binding_factor,
            anomaly_factor=latest.anomaly_factor,
            threshold=TOO_MUCH_THRESHOLD,
            is_overextended=is_over,
            sweetness_quota_remaining=round(quota_remaining, 4),
            verdict=verdict,
            the_answer=the_answer,
            input_receipt_ids=latest.input_receipt_ids,
            truth_status="real_derived",
            generated_values=False,
            eligible_for_action=latest.eligible_for_action,
            eligible_for_accounting=False,
            eligible_for_learning=latest.eligible_for_learning,
        )

    def balance_of_great_question(self, symbols: List[str]) -> Dict[str, Any]:
        """
        The Grand Unified View — taste the entire market simultaneously.

        Returns the market's overall flavour and answers:
          "Is it sustainably savoury, or dangerously sweet about to turn sour?"
        """
        if not symbols:
            return _no_data("symbols_required")

        profiles: List[MarketTasteProfile] = []
        for sym in symbols:
            hist = [
                profile
                for profile in self._history_for_read(sym)
                if self._profile_is_fresh(profile)
            ]
            if not hist:
                return _no_data(
                    "fresh_learning_eligible_history_required_for_every_symbol",
                    symbol=sym,
                )
            profiles.append(hist[-1])
        if (
            len({profile.venue for profile in profiles}) != 1
            or len({profile.timeframe.lower() for profile in profiles}) != 1
        ):
            return _no_data("same_venue_and_timeframe_history_required")

        # ── Aggregate across all symbols ──────────────────────────────────────
        n = len(profiles)
        avg_taste   = sum(p.taste_score          for p in profiles) / n
        avg_hz      = sum(p.primary_hz           for p in profiles) / n
        avg_sweet   = sum(p.sweetness            for p in profiles) / n
        avg_sour    = sum(p.sourness             for p in profiles) / n
        avg_savoury = sum(p.savouriness          for p in profiles) / n
        avg_bitter  = sum(p.bitterness           for p in profiles) / n
        avg_tmi     = sum(p.too_much_index       for p in profiles) / n
        avg_tp      = sum(p.turning_point_score  for p in profiles) / n
        avg_balance = sum(p.balance_score        for p in profiles) / n

        # Count categories
        cats: Dict[str, int] = {}
        for p in profiles:
            cats[p.taste_category] = cats.get(p.taste_category, 0) + 1

        dominant_cat = max(cats, key=cats.__getitem__)

        # ── Identify outliers ─────────────────────────────────────────────────
        sweetest = max(profiles, key=lambda p: p.taste_score)
        sourest  = min(profiles, key=lambda p: p.taste_score)
        most_turning = max(profiles, key=lambda p: p.turning_point_score)

        # ── Grand verdict ─────────────────────────────────────────────────────
        if avg_tp >= 0.55 and avg_sweet > avg_savoury:
            grand_verdict = (
                f"The market is collectively sweet but turning. "
                f"Average Hz: {avg_hz:.0f} Hz ({self._hz_to_emotion(avg_hz)}). "
                f"The great balance is tipping — from sweet to sour. "
                f"The {most_turning.symbol} is leading the turn ({most_turning.turning_point_score:.0%} probability)."
            )
            grand_action = "reduce_market_exposure"
        elif dominant_cat in ("savoury",) or (0.45 <= avg_taste <= 0.60):
            grand_verdict = (
                f"The market tastes savoury — balanced, complex, sustainable. "
                f"Average Hz: {avg_hz:.0f} Hz. This is the great balance: "
                f"enough sweetness to be rewarding, enough complexity to hold. "
                f"Savoury markets are the Goldilocks zone."
            )
            grand_action = "hold_and_compound"
        elif avg_taste > 0.75:
            grand_verdict = (
                f"The market is dangerously sweet. Average Hz {avg_hz:.0f} Hz "
                f"({self._hz_to_emotion(avg_hz)}). Too-Much Index: {avg_tmi:.2f}. "
                f"Sweetest: {sweetest.symbol} at {sweetest.primary_hz:.0f} Hz. "
                f"Good things don't last forever — this sweetness is approaching its limit."
            )
            grand_action = "protect_profits"
        elif avg_taste < 0.35:
            grand_verdict = (
                f"The market tastes sour. Average Hz {avg_hz:.0f} Hz. "
                f"Sourest: {sourest.symbol}. "
                f"Sour is not always bad — it can precede a return to savoury. "
                f"The question is: is this a lemon to squeeze or a bad grape to spit out?"
            )
            grand_action = "find_the_savoury_survivors"
        else:
            grand_verdict = (
                f"Mixed flavours across the market. "
                f"Sweet: {avg_sweet:.0%}, Sour: {avg_sour:.0%}, "
                f"Savoury: {avg_savoury:.0%}, Bitter: {avg_bitter:.0%}. "
                f"Average Hz: {avg_hz:.0f}. The market has no single taste right now."
            )
            grand_action = "selective_positioning"

        eligible_for_action = all(
            profile.eligible_for_action for profile in profiles
        )
        if not eligible_for_action:
            grand_action = "observe_only"
        input_receipt_ids = tuple(
            dict.fromkeys(
                receipt_id
                for profile in profiles
                for receipt_id in profile.input_receipt_ids
            )
        )
        return {
            "status": "ok",
            "truth_status": "real_derived",
            "generated_values": False,
            "evidence_complete": True,
            "eligible_for_action": eligible_for_action,
            "eligible_for_accounting": False,
            "eligible_for_learning": all(
                profile.eligible_for_learning for profile in profiles
            ),
            "input_receipt_ids": input_receipt_ids,
            "venue": profiles[0].venue,
            "timeframe": profiles[0].timeframe,
            "grand_verdict": grand_verdict,
            "grand_action": grand_action,
            "symbols_tasted": n,
            "average_taste_score": round(avg_taste, 4),
            "average_hz": round(avg_hz, 1),
            "average_emotional_state": self._hz_to_emotion(avg_hz),
            "flavour_profile": {
                "sweetness":   round(avg_sweet,   4),
                "sourness":    round(avg_sour,     4),
                "savouriness": round(avg_savoury,  4),
                "bitterness":  round(avg_bitter,   4),
            },
            "too_much_index":       round(avg_tmi, 4),
            "turning_point_score":  round(avg_tp,  4),
            "balance_score":        round(avg_balance, 4),
            "dominant_category":    dominant_cat,
            "category_distribution": cats,
            "sweetest_symbol":      {"symbol": sweetest.symbol, "hz": sweetest.primary_hz,
                                     "score": sweetest.taste_score},
            "sourest_symbol":       {"symbol": sourest.symbol,  "hz": sourest.primary_hz,
                                     "score": sourest.taste_score},
            "most_at_risk_of_turning": {"symbol": most_turning.symbol,
                                        "turning_point_score": most_turning.turning_point_score,
                                        "too_much_index": most_turning.too_much_index},
        }

    @staticmethod
    def _hz_to_emotion(hz: float) -> str:
        for _, max_s, h, emotion, _ in TASTE_FREQUENCY_BANDS:
            if hz <= h:
                return emotion
        return "Illumination"

    @staticmethod
    def _queen_verdict(symbol: str, taste_score: float, taste_category: str,
                       tp_score: float, tmi: float,
                       sweetness: float, sourness: float, savouriness: float,
                       hz: float) -> Tuple[str, str]:
        """Generate Queen Sero's natural-language market verdict and action hint."""

        if taste_category == "sweet_turning_sour":
            return (
                f"{symbol} was delicious — now it's leaving a bad taste. "
                f"The Hz has started falling ({hz:.0f} Hz). "
                f"The turning point is here. Too much of a good thing always ends the same way.",
                "exit_before_sour"
            )
        elif taste_category == "dangerously_sweet":
            return (
                f"{symbol} is at maximum sweetness — like pure sucralose, potent but artificial. "
                f"Nothing this sweet lasts. The aftertaste is coming.",
                "protect_profits_now"
            )
        elif taste_category == "very_sweet":
            return (
                f"{symbol} is very sweet and the Too-Much Index is {tmi:.2f}. "
                f"Still enjoyable but we're deep in dessert territory. Watch the Hz.",
                "tighten_stops"
            )
        elif taste_category == "sweet":
            return (
                f"{symbol} tastes genuinely sweet at {hz:.0f} Hz. "
                f"Organic sweetness — the kind that can last.",
                "hold_sweet"
            )
        elif taste_category == "savoury":
            return (
                f"{symbol} is perfectly savoury — the great balance. "
                f"Complex, nourishing, sustainable. This is the frequency we aim for.",
                "compound_position"
            )
        elif taste_category == "bitter":
            return (
                f"{symbol} has a bitter edge. Not fully sour yet but the taste has changed. "
                f"Something is off. Reduce and monitor.",
                "reduce_position"
            )
        elif taste_category == "sour":
            return (
                f"{symbol} is sour. The good thing has gone bad. "
                f"Sour can become savoury again — but only with time and patience.",
                "wait_or_accumulate_slowly"
            )
        else:
            return (
                f"{symbol} has a complex, undetermined flavour at {hz:.0f} Hz. "
                f"Taste score {taste_score:.2f}. Continue monitoring.",
                "monitor"
            )


# ─────────────────────────────────────────────────────────────────────────────
# SINGLETON
# ─────────────────────────────────────────────────────────────────────────────

_market_taste_sense: Optional[MarketTasteSense] = None


def get_market_taste_sense() -> MarketTasteSense:
    """Return the global MarketTasteSense singleton."""
    global _market_taste_sense
    if _market_taste_sense is None:
        _market_taste_sense = MarketTasteSense()
    return _market_taste_sense


# ─────────────────────────────────────────────────────────────────────────────
