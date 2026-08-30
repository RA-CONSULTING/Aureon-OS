#!/usr/bin/env python3
"""
🌌🎯 AUREON UNIVERSAL FORECAST SYSTEM 🎯🌌
==========================================

COMPLETE MULTI-PLATFORM PREDICTION ENGINE
Uses ALL systems across ALL trading platforms:

PREDICTION SYSTEMS:
├─ 🌍 Earth Resonance Engine (Schumann coherence, PHI multiplier)
├─ ⚡ HNC Imperial Predictability (Cosmic state, planetary torque)
├─ 📊 HNC Probability Matrix (2-hour temporal windows)
├─ 🎵 Auris Nodes (Multi-node consensus)
└─ 🌙 Lunar/Planetary Calendar (Torque timing)

TRADING PLATFORMS:
├─ 💰 Binance (Crypto - UK USDC pairs)
├─ 🦑 Kraken (Crypto - GBP/EUR pairs)
├─ 🦙 Alpaca (US Stocks & Crypto)
└─ 💷 Capital.com (CFDs - Indices/Forex/Commodities)

Gary Leckey & GitHub Copilot | December 2025
"All Systems. All Platforms. One Forecast."
"""

import time
import math
import numpy as np
from datetime import datetime
from typing import Callable, Dict, List, Mapping, Optional, Tuple, Any
from dataclasses import dataclass
from collections import deque
from enum import Enum

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

PHI = (1 + math.sqrt(5)) / 2  # Golden Ratio = 1.618033988749895

# Solfeggio Frequencies
FREQ_MAP = {
    'SCHUMANN': 7.83,
    'ROOT': 256.0,
    'LIBERATION': 396.0,
    'TRANSFORMATION': 417.0,
    'NATURAL': 432.0,
    'DISTORTION': 440.0,
    'LOVE': 528.0,
    'CONNECTION': 639.0,
    'AWAKENING': 741.0,
    'INTUITION': 852.0,
    'UNITY': 963.0,
}

# Minimum profit thresholds (above fees)
MIN_PROFIT_PCT = 0.0005  # 0.05%
MAX_RECEIPT_AGE_SECONDS = 120.0


def _finite(value: Any, *, positive: bool = False, nonnegative: bool = False) -> Optional[float]:
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


def _fresh_receipt_times(receipt: Mapping[str, Any], now: float) -> Optional[tuple[float, float]]:
    source_timestamp = _finite(receipt.get("source_timestamp"), positive=True)
    received_at = _finite(receipt.get("received_at"), positive=True)
    if (
        source_timestamp is None
        or received_at is None
        or source_timestamp > received_at + 5.0
        or received_at > now + 5.0
        or now - source_timestamp > MAX_RECEIPT_AGE_SECONDS
        or now - received_at > MAX_RECEIPT_AGE_SECONDS
    ):
        return None
    return source_timestamp, received_at


def _canonical_symbol(value: Any) -> str:
    return str(value or "").upper().replace("/", "").replace("-", "")


class Platform(Enum):
    """Trading platforms"""
    BINANCE = "binance"
    KRAKEN = "kraken"
    ALPACA = "alpaca"
    CAPITAL = "capital"


class AssetClass(Enum):
    """Asset classes"""
    CRYPTO = "crypto"
    STOCK = "stock"
    FOREX = "forex"
    INDEX = "index"
    COMMODITY = "commodity"


@dataclass
class PriceSnapshot:
    """Single price observation"""
    timestamp: float
    price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume: Optional[float] = None
    momentum: Optional[float] = None
    venue: Optional[str] = None
    symbol: Optional[str] = None
    quote_currency: Optional[str] = None
    source_id: Optional[str] = None
    source_timestamp: Optional[float] = None
    received_at: Optional[float] = None
    receipt_id: Optional[str] = None
    truth_status: str = "no_data"
    generated_values: bool = False
    actionable: bool = False
    accounting_eligible: bool = False
    learning_eligible: bool = False


@dataclass
class CosmicGateStatus:
    """Complete cosmic gate status"""
    # Earth Resonance
    earth_open: bool = False
    earth_coherence: Optional[float] = None
    earth_phase_lock: Optional[float] = None
    earth_phi_boost: Optional[float] = None
    earth_reason: str = "no_data"
    
    # Cosmic State
    cosmic_open: bool = False
    cosmic_phase: str = "NO_DATA"
    cosmic_coherence: Optional[float] = None
    cosmic_distortion: Optional[float] = None
    cosmic_boost: Optional[float] = None
    cosmic_joy: Optional[float] = None
    cosmic_reciprocity: Optional[float] = None
    
    # Planetary
    planetary_torque: Optional[float] = None
    lunar_phase: Optional[float] = None
    
    # Combined
    all_gates_open: bool = False
    combined_multiplier: Optional[float] = None
    source_id: Optional[str] = None
    source_timestamp: Optional[float] = None
    received_at: Optional[float] = None
    receipt_id: Optional[str] = None
    input_receipt_ids: Tuple[str, ...] = ()
    hnc_receipt_id: Optional[str] = None
    auris_receipt_id: Optional[str] = None
    truth_status: str = "no_data"
    generated_values: bool = False
    evidence_complete: bool = False
    actionable: bool = False
    accounting_eligible: bool = False
    learning_eligible: bool = False


@dataclass
class ProbabilityForecast:
    """60-second probability forecast"""
    symbol: str
    platform: str
    asset_class: str
    
    # Current state
    current_price: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    spread_pct: Optional[float] = None
    
    # Forecast
    forecast_price: Optional[float] = None
    price_change_pct: Optional[float] = None
    
    # Probability
    bullish_probability: Optional[float] = None
    bearish_probability: Optional[float] = None
    confidence: Optional[float] = None
    
    # Frequency analysis
    frequency: Optional[float] = None
    is_harmonic: bool = False
    frequency_state: str = "NO_DATA"
    
    # Pattern alignment
    prime_alignment: Optional[float] = None
    fibonacci_alignment: Optional[float] = None
    golden_ratio_proximity: Optional[float] = None
    
    # Decision
    recommended_action: str = "NO_DATA"
    position_multiplier: Optional[float] = None
    expected_profit_pct: Optional[float] = None
    
    # Timing
    forecast_window_sec: Optional[int] = None
    generated_at: Optional[datetime] = None
    source_timestamp: Optional[float] = None
    received_at: Optional[float] = None
    receipt_id: Optional[str] = None
    input_receipt_ids: Tuple[str, ...] = ()
    data_status: str = "no_data"
    truth_status: str = "no_data"
    generated_values: bool = False
    actionable: bool = False
    accounting_eligible: bool = False
    learning_eligible: bool = False


@dataclass
class UniversalForecast:
    """Complete forecast using all systems for one opportunity"""
    # Identity
    symbol: str
    platform: Optional[Platform]
    asset_class: Optional[AssetClass]
    
    # Cosmic Gates
    cosmic_gates: Optional[CosmicGateStatus] = None
    
    # Probability Forecast
    probability: Optional[ProbabilityForecast] = None
    
    # Final Decision
    should_trade: bool = False
    reason: str = ""
    action: str = "NO_DATA"
    
    # Position Sizing
    position_usd: Optional[float] = None
    quantity: Optional[float] = None
    
    # Risk Management
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    
    # Timing
    entry_window_sec: Optional[int] = None
    generated_at: Optional[datetime] = None
    data_status: str = "no_data"
    truth_status: str = "no_data"
    source_timestamp: Optional[float] = None
    received_at: Optional[float] = None
    receipt_id: Optional[str] = None
    input_receipt_ids: Tuple[str, ...] = ()
    generated_values: bool = False
    actionable: bool = False
    accounting_eligible: bool = False
    learning_eligible: bool = False


# ═══════════════════════════════════════════════════════════════════════════
# UNIVERSAL FORECAST ENGINE
# ═══════════════════════════════════════════════════════════════════════════

class UniversalForecastEngine:
    """
    Master forecasting engine that integrates ALL prediction systems
    across ALL trading platforms.
    """
    
    def __init__(
        self,
        *,
        clients: Optional[Mapping[str, Any]] = None,
        earth_engine: Any = None,
        cosmic_engine: Any = None,
        predictability_engine: Any = None,
        temporal_analyzer: Any = None,
        gate_receipt_supplier: Optional[
            Callable[[Mapping[str, Any]], Mapping[str, Any]]
        ] = None,
        fee_receipt_supplier: Optional[
            Callable[[Mapping[str, Any]], Mapping[str, Any]]
        ] = None,
        clock: Callable[[], float] = time.time,
        sleeper: Callable[[float], None] = time.sleep,
        verbose: bool = False,
    ):
        self._emit = print if verbose else (lambda *args, **kwargs: None)
        self._emit("\n🌌 Initializing Universal Forecast Engine...")
        
        # Initialize prediction systems
        self.earth_engine = earth_engine
        self.cosmic_engine = cosmic_engine
        self.predictability_engine = predictability_engine
        self.temporal_analyzer = temporal_analyzer
        self.gate_receipt_supplier = gate_receipt_supplier
        self.fee_receipt_supplier = fee_receipt_supplier
        self._clock = clock
        self._sleep = sleeper

        self._emit("   ✅ Earth Resonance Engine")
        self._emit("   ✅ Cosmic State Engine")
        self._emit("   ✅ Imperial Predictability Engine")
        self._emit("   ✅ Temporal Frequency Analyzer")
        
        # Initialize exchange clients
        self.clients = dict(clients or {})
        
        # Price history for each symbol
        self.price_history: Dict[str, deque] = {}
        self.max_history = 180  # 3 minutes at 1/sec
        
        self._emit("\n🌌 Universal Forecast Engine Ready!")
    
    # LAYER 1: COSMIC GATE CHECKS
    # ═══════════════════════════════════════════════════════════════════════
    
    def _cognition_component(
        self,
        raw: Any,
        *,
        source_prefix: str,
        required_links: set[str],
        metric_fields: Tuple[str, ...],
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(raw, Mapping):
            return None
        times = _fresh_receipt_times(raw, self._clock())
        source_id = str(raw.get("source_id") or "").strip().lower()
        receipt_id = str(raw.get("receipt_id") or "").strip()
        receipt_type = str(
            raw.get("provider_receipt_type") or ""
        ).strip()
        linked_ids = raw.get("input_receipt_ids")
        if (
            times is None
            or not source_id.startswith(source_prefix)
            or not receipt_id
            or not receipt_type
            or raw.get("data_status") != "live"
            or raw.get("truth_status") != "real_derived"
            or raw.get("generated_values") is not False
            or raw.get("eligible_for_action") is not True
            or not isinstance(linked_ids, (list, tuple, set))
            or not required_links.issubset({str(value) for value in linked_ids})
        ):
            return None
        metrics: Dict[str, float] = {}
        for field_name in metric_fields:
            number = _finite(raw.get(field_name), nonnegative=True)
            if number is None:
                return None
            if (
                field_name in {
                    "hnc_coherence",
                    "auris_coherence",
                    "auris_resonance",
                }
                and number > 1.0
            ):
                return None
            metrics[field_name] = number
        source_timestamp, received_at = times
        return {
            **raw,
            **metrics,
            "source_id": source_id,
            "receipt_id": receipt_id,
            "source_timestamp": source_timestamp,
            "received_at": received_at,
        }

    def check_cosmic_gates(
        self,
        platform: Optional[str] = None,
        symbol: Optional[str] = None,
        snapshots: Optional[List[PriceSnapshot]] = None,
    ) -> CosmicGateStatus:
        """
        Check ALL cosmic gates before any trading decision.
        Returns complete gate status with all metrics.
        """
        status = CosmicGateStatus()
        if (
            platform is None
            or symbol is None
            or snapshots is None
            or not self._validated_snapshot_sequence(
                platform, snapshots, symbol=symbol
            )
        ):
            status.earth_reason = "fresh_provider_price_receipts_required"
            return status
        supplier = self.gate_receipt_supplier
        if not callable(supplier):
            status.earth_reason = "complete_fresh_hnc_auris_gate_receipt_required"
            return status
        market_receipt_ids = {
            str(snapshot.receipt_id) for snapshot in snapshots
        }
        request = {
            "venue": platform.lower(),
            "symbol": symbol,
            "market_receipt_ids": sorted(market_receipt_ids),
        }
        try:
            receipt = supplier(request)
        except Exception:
            status.earth_reason = "hnc_auris_gate_receipt_unavailable"
            return status
        now = self._clock()
        if not isinstance(receipt, Mapping):
            status.earth_reason = "hnc_auris_gate_receipt_malformed"
            return status
        times = _fresh_receipt_times(receipt, now)
        source_id = str(receipt.get("source_id") or "").strip()
        receipt_id = str(receipt.get("receipt_id") or "").strip()
        receipt_type = str(
            receipt.get("provider_receipt_type") or ""
        ).strip()
        earth_reason = str(receipt.get("earth_reason") or "").strip()
        root_links = receipt.get("input_receipt_ids")
        hnc = self._cognition_component(
            receipt.get("hnc_receipt"),
            source_prefix="aureon:hnc:",
            required_links=market_receipt_ids,
            metric_fields=("hnc_coherence", "lambda_value", "phi_alignment"),
        )
        if hnc is None or not math.isclose(
            hnc["phi_alignment"], PHI, rel_tol=0.0, abs_tol=1e-12
        ):
            status.earth_reason = "canonical_hnc_receipt_required"
            return status
        auris = self._cognition_component(
            receipt.get("auris_receipt"),
            source_prefix="aureon:auris:",
            required_links=market_receipt_ids | {str(hnc["receipt_id"])},
            metric_fields=("auris_coherence", "auris_resonance"),
        )
        if auris is None:
            status.earth_reason = "canonical_auris_receipt_required"
            return status
        required_root_links = market_receipt_ids | {
            str(hnc["receipt_id"]),
            str(auris["receipt_id"]),
        }
        earth_coherence = _finite(receipt.get("earth_coherence"), nonnegative=True)
        earth_phase_lock = _finite(receipt.get("earth_phase_lock"), nonnegative=True)
        earth_phi_boost = _finite(receipt.get("earth_phi_boost"), positive=True)
        cosmic_coherence = _finite(receipt.get("cosmic_coherence"), nonnegative=True)
        cosmic_distortion = _finite(receipt.get("cosmic_distortion"), nonnegative=True)
        cosmic_boost = _finite(receipt.get("cosmic_boost"), positive=True)
        cosmic_joy = _finite(receipt.get("cosmic_joy"))
        cosmic_reciprocity = _finite(receipt.get("cosmic_reciprocity"))
        planetary_torque = _finite(receipt.get("planetary_torque"), positive=True)
        lunar_phase = _finite(receipt.get("lunar_phase"), nonnegative=True)
        cosmic_phase = str(receipt.get("cosmic_phase") or "").strip()
        if (
            times is None
            or not source_id.lower().startswith("aureon:hnc_auris:")
            or not receipt_id
            or not receipt_type
            or not earth_reason
            or receipt.get("data_status") != "live"
            or receipt.get("truth_status") != "real_derived"
            or receipt.get("generated_values") is not False
            or receipt.get("eligible_for_action") is not True
            or str(receipt.get("venue") or "").strip().lower() != platform.lower()
            or _canonical_symbol(receipt.get("symbol")) != _canonical_symbol(symbol)
            or not isinstance(root_links, (list, tuple, set))
            or not required_root_links.issubset(
                {str(value) for value in root_links}
            )
            or type(receipt.get("earth_open")) is not bool
            or type(receipt.get("cosmic_open")) is not bool
            or not cosmic_phase
            or any(
                value is None
                for value in (
                    earth_coherence,
                    earth_phase_lock,
                    earth_phi_boost,
                    cosmic_coherence,
                    cosmic_distortion,
                    cosmic_boost,
                    cosmic_joy,
                    cosmic_reciprocity,
                    planetary_torque,
                    lunar_phase,
                )
            )
            or earth_coherence > 1.0
            or earth_phase_lock > 1.0
            or cosmic_coherence > 1.0
            or lunar_phase > 1.0
        ):
            status.earth_reason = "hnc_auris_gate_receipt_incomplete"
            return status
        status.earth_open = receipt["earth_open"]
        status.earth_coherence = earth_coherence
        status.earth_phase_lock = earth_phase_lock
        status.earth_phi_boost = earth_phi_boost
        status.earth_reason = earth_reason
        status.cosmic_open = receipt["cosmic_open"]
        status.cosmic_phase = cosmic_phase
        status.cosmic_coherence = cosmic_coherence
        status.cosmic_distortion = cosmic_distortion
        status.cosmic_boost = cosmic_boost
        status.cosmic_joy = cosmic_joy
        status.cosmic_reciprocity = cosmic_reciprocity
        status.planetary_torque = planetary_torque
        status.lunar_phase = lunar_phase
        status.all_gates_open = status.earth_open and status.cosmic_open
        status.combined_multiplier = (
            status.earth_phi_boost *
            status.cosmic_boost *
            min(2.0, status.planetary_torque)
        )
        status.source_id = source_id
        status.source_timestamp, status.received_at = times
        status.receipt_id = receipt_id
        status.input_receipt_ids = tuple(sorted(required_root_links))
        status.hnc_receipt_id = str(hnc["receipt_id"])
        status.auris_receipt_id = str(auris["receipt_id"])
        status.truth_status = "real_derived"
        status.generated_values = False
        status.evidence_complete = True
        status.actionable = False
        return status

    # ═══════════════════════════════════════════════════════════════════════
    # LAYER 2: PRICE DATA COLLECTION
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_price_receipt(self, platform: str, symbol: str) -> Optional[Dict[str, Any]]:
        """Normalize only a complete fresh same-venue provider quote receipt."""
        platform = str(platform).strip().lower()
        canonical_symbol = _canonical_symbol(symbol)
        if not platform or not canonical_symbol:
            return None
        client = self.clients.get(platform)
        if client is None:
            return None
        getter = getattr(client, "get_ticker_receipt", None)
        if not callable(getter):
            return None
        try:
            receipt = getter(symbol)
        except Exception:
            return None
        if not isinstance(receipt, Mapping):
            return None
        now = self._clock()
        times = _fresh_receipt_times(receipt, now)
        price = _finite(receipt.get("price"), positive=True)
        bid = _finite(receipt.get("bid"), positive=True)
        ask = _finite(receipt.get("ask"), positive=True)
        source_id = str(receipt.get("source_id") or "").strip()
        receipt_id = str(receipt.get("receipt_id") or "").strip()
        receipt_type = str(
            receipt.get("provider_receipt_type") or ""
        ).strip()
        receipt_venue = str(receipt.get("venue") or "").strip().lower()
        receipt_symbol = _canonical_symbol(receipt.get("symbol"))
        quote_currency = str(receipt.get("quote_currency") or "").strip().upper()
        volume = _finite(receipt.get("volume"), nonnegative=True)
        if (
            times is None
            or price is None
            or bid is None
            or ask is None
            or ask < bid
            or receipt.get("data_status") != "live"
            or receipt.get("truth_status") != "real_observed"
            or not source_id.lower().startswith(f"{platform.lower()}:")
            or not receipt_id
            or not receipt_type
            or receipt_venue != platform
            or receipt_symbol != canonical_symbol
            or not quote_currency
            or volume is None
            or receipt.get("generated_values") is not False
        ):
            return None
        source_timestamp, received_at = times
        return {
            **receipt,
            "symbol": symbol,
            "venue": platform,
            "quote_currency": quote_currency,
            "price": price,
            "bid": bid,
            "ask": ask,
            "volume": volume,
            "source_timestamp": source_timestamp,
            "received_at": received_at,
            "truth_status": receipt["truth_status"],
            "generated_values": False,
            "actionable": False,
            "accounting_eligible": False,
            "learning_eligible": False,
        }

    def collect_price_data(self, platform: str, symbol: str, 
                           duration_sec: Optional[int] = None,
                           interval_sec: Optional[float] = None) -> List[PriceSnapshot]:
        """
        Collect price data for probability analysis.
        """
        duration = _finite(duration_sec, positive=True)
        interval = _finite(interval_sec, positive=True)
        if duration is None or interval is None:
            return []
        observation_count = int(duration / interval)
        if observation_count < 1:
            return []
        snapshots = []
        seen_receipts: set[str] = set()
        prev_price = None
        
        for _ in range(observation_count):
            receipt = self.get_price_receipt(platform, symbol)
            if receipt is None:
                self._sleep(interval_sec)
                continue
            receipt_id = str(receipt["receipt_id"])
            if receipt_id in seen_receipts:
                self._sleep(interval_sec)
                continue
            seen_receipts.add(receipt_id)
            price = receipt["price"]
            bid = receipt["bid"]
            ask = receipt["ask"]
            if prev_price is None:
                prev_price = price
                self._sleep(interval_sec)
                continue
            momentum = ((price - prev_price) / prev_price) * 100
            volume = receipt["volume"]
            
            snapshot = PriceSnapshot(
                timestamp=receipt["source_timestamp"],
                price=price,
                bid=bid,
                ask=ask,
                volume=volume,
                momentum=momentum,
                venue=receipt["venue"],
                symbol=receipt["symbol"],
                quote_currency=receipt["quote_currency"],
                source_id=str(receipt["source_id"]),
                source_timestamp=receipt["source_timestamp"],
                received_at=receipt["received_at"],
                receipt_id=receipt_id,
                truth_status=str(receipt["truth_status"]),
                generated_values=False,
                actionable=False,
                accounting_eligible=False,
                learning_eligible=False,
            )
            snapshots.append(snapshot)
            
            prev_price = price
            self._sleep(interval_sec)
        
        return snapshots
    
    # ═══════════════════════════════════════════════════════════════════════
    # LAYER 3: PROBABILITY FORECAST
    # ═══════════════════════════════════════════════════════════════════════
    
    def _price_to_frequency(self, price: float, base_price: float) -> float:
        """Map price movement to frequency domain"""
        ratio = price / base_price if base_price > 0 else 1.0
        freq = 432.0 * (ratio ** PHI)
        return max(256, min(963, freq))
    
    def _is_harmonic_frequency(self, freq: float) -> Tuple[bool, str]:
        """Check if frequency is near a harmonic"""
        for name, harmonic in FREQ_MAP.items():
            if name != 'DISTORTION' and abs(freq - harmonic) < 20:
                return True, name
        if abs(freq - FREQ_MAP['DISTORTION']) < 10:
            return False, 'DISTORTION'
        return False, 'NEUTRAL'
    
    def _compute_prime_alignment(self, timestamp: float) -> float:
        """Compute temporal alignment with primes"""
        primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59]
        dt = datetime.fromtimestamp(timestamp)
        
        alignment = 0.0
        if dt.second in primes:
            alignment += 0.5
        if dt.minute in primes:
            alignment += 0.5
        return alignment
    
    def _compute_fibonacci_alignment(self, prices: List[float]) -> float:
        """Compute Fibonacci alignment only for a sufficient non-flat series."""
        if len(prices) < 3:
            raise ValueError("at least three observed prices are required")
        
        high = max(prices)
        low = min(prices)
        current = prices[-1]
        
        if high == low:
            raise ValueError("a non-flat observed price range is required")
        
        retracement = (high - current) / (high - low)
        fib_levels = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
        
        min_dist = min(abs(retracement - level) for level in fib_levels)
        return 1.0 - min(1.0, min_dist * 3)

    def _validated_snapshot_sequence(
        self,
        platform: str,
        snapshots: List[PriceSnapshot],
        *,
        symbol: Optional[str] = None,
    ) -> bool:
        if len(snapshots) < 5:
            return False
        now = self._clock()
        receipt_ids: set[str] = set()
        observed_prices: set[float] = set()
        previous_timestamp: Optional[float] = None
        quote_currency: Optional[str] = None
        expected_symbol = _canonical_symbol(symbol)
        for snapshot in snapshots:
            source_timestamp = _finite(snapshot.source_timestamp, positive=True)
            received_at = _finite(snapshot.received_at, positive=True)
            price = _finite(snapshot.price, positive=True)
            bid = _finite(snapshot.bid, positive=True)
            ask = _finite(snapshot.ask, positive=True)
            momentum = _finite(snapshot.momentum)
            volume = _finite(snapshot.volume, nonnegative=True)
            receipt_id = str(snapshot.receipt_id or "").strip()
            source_id = str(snapshot.source_id or "").strip().lower()
            snapshot_venue = str(snapshot.venue or "").strip().lower()
            snapshot_symbol = _canonical_symbol(snapshot.symbol)
            snapshot_currency = str(
                snapshot.quote_currency or ""
            ).strip().upper()
            if (
                source_timestamp is None
                or received_at is None
                or price is None
                or bid is None
                or ask is None
                or momentum is None
                or volume is None
                or ask < bid
                or not source_id.startswith(f"{platform.lower()}:")
                or snapshot_venue != platform.lower()
                or snapshot_symbol == ""
                or (
                    expected_symbol != ""
                    and snapshot_symbol != expected_symbol
                )
                or snapshot_currency == ""
                or not receipt_id
                or receipt_id in receipt_ids
                or snapshot.truth_status not in {"real_observed", "real_derived"}
                or snapshot.generated_values is not False
                or source_timestamp > received_at + 5.0
                or received_at > now + 5.0
                or now - source_timestamp > MAX_RECEIPT_AGE_SECONDS
                or now - received_at > MAX_RECEIPT_AGE_SECONDS
                or (previous_timestamp is not None and source_timestamp <= previous_timestamp)
            ):
                return False
            if quote_currency is None:
                quote_currency = snapshot_currency
            elif quote_currency != snapshot_currency:
                return False
            if expected_symbol == "":
                expected_symbol = snapshot_symbol
            elif snapshot_symbol != expected_symbol:
                return False
            receipt_ids.add(receipt_id)
            observed_prices.add(price)
            previous_timestamp = source_timestamp
        return len(observed_prices) > 1

    def _validated_fee_evidence(
        self,
        platform: str,
        symbol: str,
        snapshots: List[PriceSnapshot],
        cosmic_gates: CosmicGateStatus,
    ) -> Optional[Dict[str, Any]]:
        if (
            not self._validated_snapshot_sequence(
                platform, snapshots, symbol=symbol
            )
            or not cosmic_gates.evidence_complete
            or not cosmic_gates.all_gates_open
            or not cosmic_gates.receipt_id
            or not cosmic_gates.hnc_receipt_id
            or not cosmic_gates.auris_receipt_id
        ):
            return None
        supplier = self.fee_receipt_supplier
        if not callable(supplier):
            return None
        market_receipt_ids = {
            str(snapshot.receipt_id) for snapshot in snapshots
        }
        required_ids = market_receipt_ids | {
            str(cosmic_gates.receipt_id),
            str(cosmic_gates.hnc_receipt_id),
            str(cosmic_gates.auris_receipt_id),
        }
        quote_currencies = {
            str(snapshot.quote_currency or "").strip().upper()
            for snapshot in snapshots
        }
        if len(quote_currencies) != 1 or "" in quote_currencies:
            return None
        quote_currency = next(iter(quote_currencies))
        request = {
            "venue": platform.lower(),
            "symbol": symbol,
            "quote_currency": quote_currency,
            "input_receipt_ids": sorted(required_ids),
        }
        try:
            receipt = supplier(request)
        except Exception:
            return None
        if not isinstance(receipt, Mapping):
            return None
        now = self._clock()
        times = _fresh_receipt_times(receipt, now)
        round_trip_fee_pct = _finite(receipt.get("round_trip_fee_pct"), nonnegative=True)
        source_id = str(receipt.get("source_id") or "").strip().lower()
        receipt_id = str(receipt.get("receipt_id") or "").strip()
        receipt_type = str(
            receipt.get("provider_receipt_type") or ""
        ).strip()
        linked_ids = receipt.get("input_receipt_ids")
        fee_currency = str(
            receipt.get("fee_currency") or ""
        ).strip().upper()
        if (
            times is None
            or round_trip_fee_pct is None
            or round_trip_fee_pct >= 100.0
            or not source_id.startswith(f"{platform.lower()}:")
            or not receipt_id
            or not receipt_type
            or receipt.get("data_status") != "live"
            or str(receipt.get("venue") or "").strip().lower() != platform.lower()
            or _canonical_symbol(receipt.get("symbol")) != _canonical_symbol(symbol)
            or fee_currency != quote_currency
            or receipt.get("fee_schedule_complete") is not True
            or receipt.get("truth_status") != "real_observed"
            or receipt.get("generated_values") is not False
            or receipt.get("eligible_for_action") is not True
            or not isinstance(linked_ids, (list, tuple, set))
            or not required_ids.issubset({str(value) for value in linked_ids})
        ):
            return None
        source_timestamp, received_at = times
        return {
            **receipt,
            "round_trip_fee_pct": round_trip_fee_pct,
            "source_timestamp": source_timestamp,
            "received_at": received_at,
            "receipt_id": receipt_id,
            "fee_currency": fee_currency,
        }
    
    def generate_probability_forecast(self, platform: str, symbol: str,
                                       snapshots: List[PriceSnapshot],
                                       cosmic_gates: CosmicGateStatus,
                                       asset_class: str = "crypto") -> ProbabilityForecast:
        """
        Generate 60-second probability forecast using ALL systems.
        """
        forecast = ProbabilityForecast(
            symbol=symbol,
            platform=platform,
            asset_class=asset_class,
        )
        
        if (
            not self._validated_snapshot_sequence(
                platform, snapshots, symbol=symbol
            )
            or not cosmic_gates.evidence_complete
            or cosmic_gates.truth_status not in {"real_observed", "real_derived"}
            or cosmic_gates.generated_values is not False
        ):
            forecast.current_price = None
            forecast.bid = None
            forecast.ask = None
            forecast.spread_pct = None
            forecast.forecast_price = None
            forecast.price_change_pct = None
            forecast.bullish_probability = None
            forecast.bearish_probability = None
            forecast.confidence = None
            forecast.frequency = None
            forecast.prime_alignment = None
            forecast.fibonacci_alignment = None
            forecast.golden_ratio_proximity = None
            forecast.position_multiplier = None
            forecast.expected_profit_pct = None
            forecast.recommended_action = "NO_DATA"
            return forecast
        fee_evidence = self._validated_fee_evidence(
            platform, symbol, snapshots, cosmic_gates
        )
        if fee_evidence is None:
            return forecast
        forecast.generated_at = datetime.fromtimestamp(self._clock())
        forecast.forecast_window_sec = 60
        forecast.source_timestamp = snapshots[-1].source_timestamp
        forecast.received_at = snapshots[-1].received_at
        forecast.receipt_id = (
            f"universal-forecast:{cosmic_gates.receipt_id}:"
            f"{fee_evidence['receipt_id']}:{snapshots[-1].receipt_id}"
        )
        forecast.input_receipt_ids = tuple(sorted({
            *[str(snapshot.receipt_id) for snapshot in snapshots],
            *cosmic_gates.input_receipt_ids,
            str(cosmic_gates.receipt_id),
            str(fee_evidence["receipt_id"]),
        }))
        forecast.data_status = "live"
        forecast.truth_status = "real_derived"
        forecast.generated_values = False
        
        prices = [s.price for s in snapshots]
        momentums = [s.momentum for s in snapshots]
        
        forecast.current_price = prices[-1]
        forecast.bid = snapshots[-1].bid
        forecast.ask = snapshots[-1].ask
        
        if forecast.bid > 0 and forecast.ask > 0:
            forecast.spread_pct = ((forecast.ask - forecast.bid) / forecast.bid) * 100
        
        # ─────────────────────────────────────────────────────────────────
        # MOMENTUM ANALYSIS
        # ─────────────────────────────────────────────────────────────────
        avg_momentum = np.mean(momentums) if momentums else 0
        momentum_trend = np.polyfit(range(len(momentums)), momentums, 1)[0] if len(momentums) > 2 else 0
        recent_momentum = np.mean(momentums[-5:]) if len(momentums) >= 5 else avg_momentum
        older_momentum = np.mean(momentums[:5]) if len(momentums) >= 5 else avg_momentum
        momentum_accel = recent_momentum - older_momentum
        
        # ─────────────────────────────────────────────────────────────────
        # FREQUENCY ANALYSIS
        # ─────────────────────────────────────────────────────────────────
        base_price = prices[0]
        forecast.frequency = self._price_to_frequency(forecast.current_price, base_price)
        forecast.is_harmonic, forecast.frequency_state = self._is_harmonic_frequency(forecast.frequency)
        
        # ─────────────────────────────────────────────────────────────────
        # PATTERN ALIGNMENT
        # ─────────────────────────────────────────────────────────────────
        forecast.prime_alignment = self._compute_prime_alignment(snapshots[-1].source_timestamp)
        forecast.fibonacci_alignment = self._compute_fibonacci_alignment(prices)
        
        # Golden ratio proximity
        price_ratio = forecast.current_price / base_price if base_price > 0 else 1
        forecast.golden_ratio_proximity = 1.0 - min(1.0, abs(price_ratio - PHI) * 2)
        
        # ─────────────────────────────────────────────────────────────────
        # PRICE FORECAST (60 seconds ahead)
        # ─────────────────────────────────────────────────────────────────
        decay = 0.7
        projected_momentum = avg_momentum * decay + recent_momentum * (1 - decay)
        
        # Apply trend direction
        if momentum_trend > 0:
            projected_momentum *= 1.2
        elif momentum_trend < 0:
            projected_momentum *= 0.8
        
        # Harmonic boost
        if forecast.is_harmonic and forecast.frequency > 500:
            projected_momentum *= 1.1
        elif forecast.frequency_state == 'DISTORTION':
            projected_momentum *= 0.8
        
        # Cosmic boost integration
        projected_momentum *= cosmic_gates.combined_multiplier
        
        # Calculate forecast
        total_change_pct = projected_momentum * 60 * 0.01
        forecast.forecast_price = forecast.current_price * (1 + total_change_pct / 100)
        forecast.price_change_pct = total_change_pct
        
        # ─────────────────────────────────────────────────────────────────
        # PROBABILITY CALCULATION
        # ─────────────────────────────────────────────────────────────────
        # Base from momentum
        if avg_momentum > 0:
            base_bullish = 0.5 + min(0.3, avg_momentum * 0.1)
        else:
            base_bullish = 0.5 + max(-0.3, avg_momentum * 0.1)
        
        # Momentum acceleration
        base_bullish += np.clip(momentum_accel * 0.05, -0.1, 0.1)
        
        # Harmonic state
        if forecast.is_harmonic:
            base_bullish += 0.05
        elif forecast.frequency_state == 'DISTORTION':
            base_bullish -= 0.05
        
        # Pattern alignment
        pattern_boost = (forecast.prime_alignment + forecast.fibonacci_alignment + forecast.golden_ratio_proximity) / 3
        base_bullish += pattern_boost * 0.1
        
        # Cosmic coherence boost
        base_bullish += cosmic_gates.cosmic_coherence * 0.1
        
        # Earth coherence boost
        base_bullish += (cosmic_gates.earth_coherence - 0.5) * 0.1
        
        # Clamp
        forecast.bullish_probability = max(0.1, min(0.9, base_bullish))
        forecast.bearish_probability = 1 - forecast.bullish_probability
        
        # ─────────────────────────────────────────────────────────────────
        # CONFIDENCE CALCULATION
        # ─────────────────────────────────────────────────────────────────
        momentum_consistency = 1.0 - min(1.0, np.std(momentums) * 5) if momentums else 0.5
        
        forecast.confidence = (
            momentum_consistency * 0.3 +
            forecast.fibonacci_alignment * 0.2 +
            forecast.prime_alignment * 0.1 +
            cosmic_gates.earth_coherence * 0.2 +
            cosmic_gates.cosmic_coherence * 0.2
        )
        
        # ─────────────────────────────────────────────────────────────────
        # TRADING DECISION
        # ─────────────────────────────────────────────────────────────────
        fee_pct = fee_evidence["round_trip_fee_pct"]
        min_profit_pct = fee_pct + MIN_PROFIT_PCT * 100
        
        forecast.position_multiplier = cosmic_gates.combined_multiplier
        
        if (forecast.bullish_probability > 0.65 and 
            forecast.price_change_pct > min_profit_pct and 
            forecast.confidence > 0.50):
            forecast.recommended_action = "BUY"
            forecast.expected_profit_pct = forecast.price_change_pct - fee_pct
        elif (forecast.bearish_probability > 0.65 and 
              forecast.price_change_pct < -min_profit_pct and 
              forecast.confidence > 0.50):
            forecast.recommended_action = "SELL"
            forecast.expected_profit_pct = abs(forecast.price_change_pct) - fee_pct
        else:
            forecast.recommended_action = "HOLD"
            forecast.expected_profit_pct = 0
        forecast.actionable = forecast.recommended_action in {"BUY", "SELL"}
        key = f"{platform}:{symbol}"
        if key not in self.price_history:
            self.price_history[key] = deque(maxlen=self.max_history)
        existing_receipt_ids = {
            str(snapshot.receipt_id)
            for snapshot in self.price_history[key]
        }
        self.price_history[key].extend(
            snapshot
            for snapshot in snapshots
            if str(snapshot.receipt_id) not in existing_receipt_ids
        )
        
        return forecast
    
    # ═══════════════════════════════════════════════════════════════════════
    # UNIFIED FORECAST GENERATION
    # ═══════════════════════════════════════════════════════════════════════
    
    def generate_forecast(self, platform: str, symbol: str, 
                          asset_class: str = "crypto",
                          collect_duration: Optional[int] = None) -> UniversalForecast:
        """
        Generate complete forecast for a single symbol on a platform.
        """
        try:
            platform_value = Platform(platform)
            asset_class_value = AssetClass(asset_class)
        except ValueError:
            return UniversalForecast(
                symbol=symbol,
                platform=None,
                asset_class=None,
                reason="supported_platform_and_asset_class_required",
            )
        forecast = UniversalForecast(
            symbol=symbol,
            platform=platform_value,
            asset_class=asset_class_value,
        )
        if collect_duration is None:
            forecast.reason = "explicit_collection_duration_required"
            return forecast

        # Layer 1: Collect provider receipts without mutating history.
        self._emit(
            f"Collecting provider receipts for {platform}:{symbol}"
        )
        snapshots = self.collect_price_data(
            platform, symbol, collect_duration, 0.5
        )
        if len(snapshots) < 10:
            forecast.reason = (
                "ten_unique_fresh_provider_price_receipts_required"
            )
            return forecast

        # Layer 2: Link canonical HNC and Auris receipts to those quotes.
        forecast.cosmic_gates = self.check_cosmic_gates(
            platform, symbol, snapshots
        )
        if (
            not forecast.cosmic_gates.evidence_complete
            or not forecast.cosmic_gates.all_gates_open
        ):
            forecast.reason = (
                "complete_linked_hnc_auris_gate_receipt_required"
            )
            return forecast
        
        # Layer 3: Probability Forecast
        forecast.probability = self.generate_probability_forecast(
            platform, symbol, snapshots, forecast.cosmic_gates, asset_class
        )
        
        # Final Decision
        if (
            forecast.probability.data_status != "live"
            or forecast.probability.truth_status != "real_derived"
        ):
            forecast.reason = "complete_linked_price_gate_and_fee_receipts_required"
            return forecast
        elif forecast.probability.recommended_action == "BUY":
            forecast.should_trade = True
            forecast.action = "BUY"
            forecast.reason = (f"Bullish {forecast.probability.bullish_probability:.1%} "
                              f"| Conf {forecast.probability.confidence:.1%} "
                              f"| +{forecast.probability.price_change_pct:.3f}%")
        elif forecast.probability.recommended_action == "SELL":
            forecast.should_trade = True
            forecast.action = "SELL"
            forecast.reason = (f"Bearish {forecast.probability.bearish_probability:.1%} "
                              f"| Conf {forecast.probability.confidence:.1%} "
                              f"| {forecast.probability.price_change_pct:.3f}%")
        else:
            forecast.should_trade = False
            forecast.action = "HOLD"
            forecast.reason = (f"No edge: Bull {forecast.probability.bullish_probability:.1%} "
                              f"| Conf {forecast.probability.confidence:.1%}")
        forecast.data_status = "live"
        forecast.truth_status = "real_derived"
        forecast.source_timestamp = forecast.probability.source_timestamp
        forecast.received_at = forecast.probability.received_at
        forecast.receipt_id = forecast.probability.receipt_id
        forecast.input_receipt_ids = forecast.probability.input_receipt_ids
        forecast.generated_values = False
        forecast.actionable = forecast.should_trade
        forecast.generated_at = datetime.fromtimestamp(self._clock())
        forecast.entry_window_sec = 60
        return forecast
    
    # ═══════════════════════════════════════════════════════════════════════
    # MULTI-PLATFORM SCANNING
    # ═══════════════════════════════════════════════════════════════════════
    
    def scan_all_platforms(
        self,
        scan_config: Mapping[str, Mapping[str, Any]],
    ) -> Dict[str, List[UniversalForecast]]:
        """
        Scan ALL platforms for trading opportunities.
        Returns forecasts organized by platform.
        """
        if not isinstance(scan_config, Mapping):
            return {}
        results: Dict[str, List[UniversalForecast]] = {}
        
        for platform, config in scan_config.items():
            if not isinstance(config, Mapping) or not self.clients.get(platform):
                continue
            symbols = config.get("symbols")
            asset_class = config.get("asset_class")
            collect_duration = _finite(
                config.get("collect_duration"), positive=True
            )
            if (
                not isinstance(symbols, (list, tuple))
                or not isinstance(asset_class, str)
                or collect_duration is None
            ):
                continue
            results[platform] = []
            
            for symbol in symbols:
                if not isinstance(symbol, str) or not symbol.strip():
                    continue
                try:
                    forecast = self.generate_forecast(
                        platform, symbol, 
                        asset_class,
                        collect_duration=int(collect_duration),
                    )
                    results[platform].append(forecast)
                except (TypeError, ValueError):
                    continue
        
        return results
    
    def get_best_opportunities(self, results: Dict[str, List[UniversalForecast]], 
                                top_n: int = 3) -> List[UniversalForecast]:
        """
        Get the best trading opportunities across all platforms.
        """
        all_forecasts = []
        for platform_forecasts in results.values():
            all_forecasts.extend([
                forecast
                for forecast in platform_forecasts
                if (
                    forecast.should_trade
                    and forecast.actionable
                    and forecast.probability is not None
                    and forecast.probability.data_status == "live"
                    and forecast.probability.expected_profit_pct is not None
                )
            ])
        
        # Sort by expected profit
        all_forecasts.sort(
            key=lambda f: f.probability.expected_profit_pct,
            reverse=True
        )
        
        return all_forecasts[:top_n]
    
    def print_cosmic_status(self, gates: CosmicGateStatus):
        """Print formatted cosmic status"""
        if not gates.evidence_complete:
            self._emit(gates.earth_reason)
            return
        print(f"""
╔══════════════════════════════════════════════════════════════════════════╗
║                    🌌 COSMIC GATE STATUS 🌌                              ║
╠══════════════════════════════════════════════════════════════════════════╣
║  🌍 EARTH RESONANCE                                                      ║
║     Gate: {'OPEN ✅' if gates.earth_open else 'CLOSED ❌':12s}  Coherence: {gates.earth_coherence:5.1%}                 ║
║     PHI Boost: {gates.earth_phi_boost:.3f}x           Phase Lock: {gates.earth_phase_lock:.1%}                 ║
╠══════════════════════════════════════════════════════════════════════════╣
║  ⚡ COSMIC STATE                                                         ║
║     Gate: {'OPEN ✅' if gates.cosmic_open else 'CLOSED ❌':12s}  Phase: {gates.cosmic_phase:15s}           ║
║     Coherence: {gates.cosmic_coherence:.3f}           Distortion: {gates.cosmic_distortion:.5f}               ║
║     Joy: {gates.cosmic_joy:.1f}  Reciprocity: {gates.cosmic_reciprocity:.1f}  Boost: {gates.cosmic_boost:.1f}x                      ║
╠══════════════════════════════════════════════════════════════════════════╣
║  🌙 PLANETARY                                                            ║
║     Torque: {gates.planetary_torque:.2f}x              Lunar Phase: {gates.lunar_phase:.1%}                  ║
╠══════════════════════════════════════════════════════════════════════════╣
║  📊 COMBINED                                                             ║
║     ALL GATES: {'OPEN ✅' if gates.all_gates_open else 'CLOSED ❌':12s}   Multiplier: {gates.combined_multiplier:.3f}x               ║
╚══════════════════════════════════════════════════════════════════════════╝
""")
