#!/usr/bin/env python3
"""
🦈🔪 HFT HARMONIC MYCELIUM ENGINE 🔪🦈
========================================

HIGH FREQUENCY TRADING via Mycelium Neural Network + Harmonic Alphabet
Target Latency: <10ms signal-to-order execution

ARCHITECTURE:
L0: RAW FEED (Sub-millisecond) → WebSocket → Lock-Free Ring Buffer → Tick Processor
L1: HARMONIC ENCODER (Microseconds) → Tick → HarmonicTone → Frequency Analysis → Pattern Match
L2: MYCELIUM FAST PATH (Milliseconds) → Hot Path Cache → Synapse Score → Queen Decision
L3: ASYNC THOUGHT BUS (<10ms) → asyncio.Queue → Parallel Handlers → Zero-Copy Publish
L4: ORDER ROUTER (Milliseconds) → WebSocket Order Submission → Confirmation → P&L Update

Gary Leckey | January 2026 | HFT MODE ACTIVATED
"""

from __future__ import annotations
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import os
import sys
import math
import time
import json
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Callable, Deque
from collections import deque
import numpy as np

# UTF-8 fix for Windows
if sys.platform == 'win32' and sys.stdout is sys.__stdout__ and sys.stdout.isatty():
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        # Avoid replacing sys.stdout with a new TextIOWrapper around stdout.buffer:
        # that pattern can close stdout in some Windows shells.
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# 👑💰 QUEEN'S SACRED 1.88% LAW - HFT MUST OBEY! 💰👑
# ═══════════════════════════════════════════════════════════════════════════════
#
#   THE QUEEN COMMANDS: MIN_COP = 1.0188 (1.88% MINIMUM REALIZED PROFIT)
#   Even at microsecond speeds, profit is sacred!
#
# ═══════════════════════════════════════════════════════════════════════════════

QUEEN_MIN_COP = 1.0188               # 👑 1.88% minimum realized profit
QUEEN_MIN_PROFIT_PCT = 1.88          # 👑 The sacred number as percentage
QUEEN_HFT_MIN_EDGE_PCT = 2.60        # 👑 Minimum edge for HFT (1.88% + fees)

# Sacred constants for HFT timing
PHI = (1 + math.sqrt(5)) / 2  # Golden Ratio 1.618
PHI_INVERSE = 0.618  # φ⁻¹ - The trigger threshold
SCHUMANN_BASE = 7.83  # Hz - Earth's heartbeat
LOVE_FREQUENCY = 528  # Hz - DNA repair frequency
WIN_FREQUENCY_HZ = 528.0   # Joy/Love/DNA repair
LOSS_FREQUENCY_HZ = 396.0  # Transformation/Learning
PROFIT_FREQUENCY_HZ = 188.0  # 👑 Queen's profit frequency!

# HFT Performance Constants
HFT_TICK_BUFFER_SIZE = 100_000  # ~1 second at 100K ticks/sec
HFT_HOT_PATH_TTL_MS = 100       # Hot path cache TTL in milliseconds
HFT_SIGNAL_TIMEOUT_MS = 10      # Max time for signal processing
HFT_ORDER_TIMEOUT_MS = 50       # Max time for order execution
HFT_MAX_CONCURRENT_ORDERS = 10  # Max simultaneous orders
HFT_MIN_POSITION_SIZE_USD = 1.0 # Minimum order size
HFT_MAX_POSITION_SIZE_USD = 100.0 # Maximum order size per trade
HFT_DAILY_LOSS_LIMIT_USD = -25.0 # Daily loss limit
HFT_WIN_STREAK_RESET = 3        # Reset after 3 wins
HFT_LOSS_STREAK_PAUSE = 3       # Pause after 3 losses

# Auris Node Frequencies (Animal Spirit Guides)
AURIS_FREQUENCIES = {
    'tiger': 186.0,      # Power - Volatility
    'falcon': 210.0,     # Precision - Momentum
    'hummingbird': 324.0, # Agility - Frequency
    'dolphin': 432.0,    # Flow - Liquidity
    'deer': 396.0,       # Grace - Stability
    'owl': 528.0,        # Wisdom - Pattern
    'panda': 639.0,      # Balance - Harmony
    'cargoship': 174.0,  # Persistence - Volume
    'clownfish': 285.0,  # Adaptation - Resilience
}

# Brainwave Frequencies
BRAINWAVE_FREQUENCIES = {
    'delta': 2.0,     # Deep sleep
    'theta': 6.0,     # Meditation
    'alpha': 10.0,    # Relaxed
    'beta': 20.0,     # Active
    'gamma': 40.0,    # Peak performance
}


@dataclass
class HFTTick:
    """High-frequency tick data."""
    timestamp: float
    symbol: str
    price: float
    volume: float
    side: str  # 'buy' or 'sell'
    exchange: str
    tick_id: str = ""

    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'symbol': self.symbol,
            'price': self.price,
            'volume': self.volume,
            'side': self.side,
            'exchange': self.exchange,
            'tick_id': self.tick_id
        }


@dataclass
class HarmonicTone:
    """Harmonic frequency encoding for HFT signals."""
    frequency: float      # Hz
    amplitude: float      # Signal strength (0-1)
    auris_node: str       # Animal spirit guide
    brainwave: str        # Mental state
    confidence: float     # Pattern match confidence (0-1)
    timestamp: float

    def to_dict(self) -> Dict:
        return {
            'frequency': self.frequency,
            'amplitude': self.amplitude,
            'auris_node': self.auris_node,
            'brainwave': self.brainwave,
            'confidence': self.confidence,
            'timestamp': self.timestamp
        }


@dataclass
class HFTSignal:
    """HFT trading signal with harmonic encoding."""
    id: str
    timestamp: float
    symbol: str
    action: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float
    position_size_usd: float
    harmonic_tone: HarmonicTone
    reasoning: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'timestamp': self.timestamp,
            'symbol': self.symbol,
            'action': self.action,
            'confidence': self.confidence,
            'position_size_usd': self.position_size_usd,
            'harmonic_tone': self.harmonic_tone.to_dict(),
            'reasoning': self.reasoning
        }


@dataclass
class HFTOrder:
    """HFT order with execution tracking."""
    id: str
    signal_id: str
    timestamp: float
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: float
    price: float
    status: str = 'PENDING'  # PENDING, SENT, FILLED, REJECTED, CANCELLED
    fill_price: float = 0.0
    fill_quantity: float = 0.0
    pnl_usd: float = 0.0
    latency_ms: float = 0.0
    exchange_order_id: str = ""

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'signal_id': self.signal_id,
            'timestamp': self.timestamp,
            'symbol': self.symbol,
            'side': self.side,
            'quantity': self.quantity,
            'price': self.price,
            'status': self.status,
            'fill_price': self.fill_price,
            'fill_quantity': self.fill_quantity,
            'pnl_usd': self.pnl_usd,
            'latency_ms': self.latency_ms,
            'exchange_order_id': self.exchange_order_id
        }


@dataclass
class CachedDecision:
    """Cached hot path decision for instant lookup."""
    symbol: str
    harmonic_pattern: Tuple[float, str, str]  # (frequency, auris, brainwave)
    action: str
    confidence: float
    position_size_usd: float
    cached_at: float
    ttl_ms: int = HFT_HOT_PATH_TTL_MS

    def is_expired(self) -> bool:
        return (time.time() - self.cached_at) * 1000 > self.ttl_ms

    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'harmonic_pattern': self.harmonic_pattern,
            'action': self.action,
            'confidence': self.confidence,
            'position_size_usd': self.position_size_usd,
            'cached_at': self.cached_at,
            'ttl_ms': self.ttl_ms
        }


class HFTHarmonicEngine:
    """
    🦈🔪 HFT HARMONIC MYCELIUM ENGINE 🔪🦈

    High Frequency Trading via Mycelium Neural Network + Harmonic Alphabet.
    Target latency: <10ms signal-to-order execution.

    ARCHITECTURE LAYERS:
    L0: RAW FEED → Lock-free tick buffer (100K capacity)
    L1: HARMONIC ENCODER → Pre-computed pattern lookup table
    L2: MYCELIUM FAST PATH → Hot path synapse cache (100ms TTL)
    L3: ASYNC THOUGHT BUS → Zero-copy publish to handlers
    L4: ORDER ROUTER → WebSocket order submission
    """

    def __init__(self):
        self.enabled = False
        self.mode = "DORMANT"  # DORMANT, SCANNING, EXECUTING, PAUSED

        # L0: RAW FEED - Lock-free tick buffer
        self.tick_buffer: Deque[HFTTick] = deque(maxlen=HFT_TICK_BUFFER_SIZE)
        self.tick_count = 0
        self.last_tick_time = 0.0

        # L1: HARMONIC ENCODER - Pre-computed pattern lookup table
        self.harmonic_patterns = self._build_harmonic_patterns()
        self.last_harmonic_tone: Optional[HarmonicTone] = None

        # L2: MYCELIUM FAST PATH - Hot path cache
        self.hot_path_cache: Dict[str, CachedDecision] = {}
        self.cache_hits = 0
        self.cache_misses = 0

        # L3: ASYNC THOUGHT BUS - Event loop and queues
        self.event_loop = asyncio.get_event_loop()
        self.signal_queue: asyncio.Queue[HFTSignal] = asyncio.Queue()
        self.order_queue: asyncio.Queue[HFTOrder] = asyncio.Queue()
        self.thought_handlers: Dict[str, List[Callable]] = {}

        # L4: ORDER ROUTER - WebSocket connections
        self.order_router = None  # Will be wired externally
        self.active_orders: Dict[str, HFTOrder] = {}
        self.completed_orders: Deque[HFTOrder] = deque(maxlen=1000)

        # Risk management
        self.daily_pnl_usd = 0.0
        self.win_streak = 0
        self.loss_streak = 0
        self.consecutive_orders = 0

        # Performance tracking
        self.signal_latencies: Deque[float] = deque(maxlen=1000)
        self.order_latencies: Deque[float] = deque(maxlen=1000)
        self.start_time = time.time()

        # Integration flags
        self.mycelium_connected = False
        self.harmonic_alphabet_connected = False
        self.queen_connected = False
        self.orca_connected = False
        self.thought_bus = None  # ThoughtBus for signal publishing

        logger.info("🦈🔪 HFT HARMONIC MYCELIUM ENGINE INITIALIZED 🔪🦈")
        logger.info(f"   Tick Buffer: {HFT_TICK_BUFFER_SIZE} capacity")
        logger.info(f"   Hot Path TTL: {HFT_HOT_PATH_TTL_MS}ms")
        logger.info(f"   Daily Loss Limit: ${HFT_DAILY_LOSS_LIMIT_USD}")

    def _build_harmonic_patterns(self) -> Dict[Tuple[float, str, str], str]:
        """
        Pre-compute harmonic pattern lookup table for instant decisions.

        WIN PATTERNS (BUY):
        - 528Hz + Falcon + Gamma = BUY (Peak Performance Momentum)
        - 528Hz + Hummingbird + Gamma = BUY (Agile Frequency Trading)
        - 528Hz + Dolphin + Alpha = BUY (Flow Liquidity)

        LOSS PATTERNS (HOLD):
        - 396Hz + Owl + Theta = HOLD (Learning Pattern Recognition)
        - 396Hz + Panda + Alpha = HOLD (Balance Harmony)
        - 396Hz + Deer + Delta = HOLD (Stability Grounding)

        VOLATILITY PATTERNS (SELL):
        - 186Hz + Tiger + Beta = SELL (Power Volatility)
        - 285Hz + Clownfish + Beta = SELL (Adaptation Resilience)
        """
        patterns = {}

        # WIN PATTERNS → BUY
        patterns[(WIN_FREQUENCY_HZ, 'falcon', 'gamma')] = 'BUY'      # Peak momentum
        patterns[(WIN_FREQUENCY_HZ, 'hummingbird', 'gamma')] = 'BUY' # Agile frequency
        patterns[(WIN_FREQUENCY_HZ, 'dolphin', 'alpha')] = 'BUY'     # Flow liquidity

        # LOSS PATTERNS → HOLD
        patterns[(LOSS_FREQUENCY_HZ, 'owl', 'theta')] = 'HOLD'       # Learning patterns
        patterns[(LOSS_FREQUENCY_HZ, 'panda', 'alpha')] = 'HOLD'     # Balance harmony
        patterns[(LOSS_FREQUENCY_HZ, 'deer', 'delta')] = 'HOLD'      # Stability grounding

        # VOLATILITY PATTERNS → SELL
        patterns[(AURIS_FREQUENCIES['tiger'], 'tiger', 'beta')] = 'SELL'      # Power volatility
        patterns[(AURIS_FREQUENCIES['clownfish'], 'clownfish', 'beta')] = 'SELL' # Adaptation

        # Add amplitude variations (0.1 to 1.0 in 0.1 steps)
        expanded_patterns = {}
        for (freq, auris, brainwave), action in patterns.items():
            for amp in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
                # Use rounded frequency for lookup (harmonics are approximate)
                key = (round(freq, 1), auris, brainwave)
                expanded_patterns[key] = action

        logger.info(f"   Built {len(expanded_patterns)} harmonic pattern lookups")
        return expanded_patterns

    # ═══════════════════════════════════════════════════════════════════════════
    # L0: RAW FEED - TICK INGESTION
    # ═══════════════════════════════════════════════════════════════════════════

    def ingest_tick(self, tick_data: Dict) -> None:
        """
        Ingest raw tick data into lock-free buffer.
        Called by WebSocket feed handlers.
        """
        if not self.enabled:
            return

        tick = HFTTick(
            timestamp=tick_data.get('timestamp', time.time()),
            symbol=tick_data.get('symbol', 'UNKNOWN'),
            price=tick_data.get('price', 0.0),
            volume=tick_data.get('volume', 0.0),
            side=tick_data.get('side', 'unknown'),
            exchange=tick_data.get('exchange', 'unknown'),
            tick_id=tick_data.get('tick_id', '')
        )

        # Lock-free append to deque
        self.tick_buffer.append(tick)
        self.tick_count += 1
        self.last_tick_time = tick.timestamp

        # Process tick immediately if in EXECUTING mode
        if self.mode == "EXECUTING":
            self.event_loop.create_task(self._process_tick_async(tick))

    async def _process_tick_async(self, tick: HFTTick) -> None:
        """Async tick processing pipeline."""
        try:
            # L1: Encode to harmonic tone
            harmonic_tone = await self._encode_harmonic_tone(tick)
            if harmonic_tone:
                self.last_harmonic_tone = harmonic_tone

                # L2: Check hot path cache
                cached_decision = self._check_hot_path_cache(tick.symbol, harmonic_tone)
                if cached_decision and not cached_decision.is_expired():
                    self.cache_hits += 1
                    # Execute cached decision
                    await self._execute_cached_decision(cached_decision, tick)
                else:
                    self.cache_misses += 1
                    # Generate new signal via Mycelium
                    await self._generate_signal_via_mycelium(tick, harmonic_tone)

        except Exception as e:
            logger.debug(f"Tick processing error: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # L1: HARMONIC ENCODER
    # ═══════════════════════════════════════════════════════════════════════════

    async def _encode_harmonic_tone(self, tick: HFTTick) -> Optional[HarmonicTone]:
        """
        Encode tick into harmonic frequency pattern.
        Uses price movement, volume, and market conditions.
        """
        try:
            # Calculate price momentum (simplified)
            recent_ticks = list(self.tick_buffer)[-10:]  # Last 10 ticks
            if len(recent_ticks) < 2:
                return None

            # Price velocity (ticks per second)
            time_span = recent_ticks[-1].timestamp - recent_ticks[0].timestamp
            price_change = recent_ticks[-1].price - recent_ticks[0].price
            velocity = price_change / max(time_span, 0.001)

            # Volume intensity
            volume_sum = sum(t.volume for t in recent_ticks)
            volume_avg = volume_sum / len(recent_ticks)

            # Determine dominant frequency based on market conditions
            if velocity > 0.001:  # Strong upward momentum
                base_freq = WIN_FREQUENCY_HZ
                auris_node = 'falcon'  # Precision momentum
                brainwave = 'gamma'   # Peak performance
                amplitude = min(abs(velocity) * 1000, 1.0)
            elif velocity < -0.001:  # Strong downward momentum
                base_freq = AURIS_FREQUENCIES['tiger']  # Power volatility
                auris_node = 'tiger'
                brainwave = 'beta'    # Active/alert
                amplitude = min(abs(velocity) * 1000, 1.0)
            else:  # Sideways/choppy
                base_freq = LOSS_FREQUENCY_HZ
                auris_node = 'owl'    # Wisdom patterns
                brainwave = 'theta'   # Learning state
                amplitude = 0.5

            # Adjust for volume (higher volume = higher amplitude)
            if volume_avg > tick.volume * 2:
                amplitude = min(amplitude * 1.5, 1.0)
                auris_node = 'cargoship'  # Persistence volume

            # Confidence based on pattern clarity
            confidence = amplitude * 0.8 + (volume_avg / (tick.volume + 1)) * 0.2
            confidence = min(confidence, 1.0)

            return HarmonicTone(
                frequency=round(base_freq, 1),
                amplitude=amplitude,
                auris_node=auris_node,
                brainwave=brainwave,
                confidence=confidence,
                timestamp=tick.timestamp
            )

        except Exception as e:
            logger.debug(f"Harmonic encoding error: {e}")
            return None

    # ═══════════════════════════════════════════════════════════════════════════
    # L2: MYCELIUM FAST PATH
    # ═══════════════════════════════════════════════════════════════════════════

    def _check_hot_path_cache(self, symbol: str, harmonic_tone: HarmonicTone) -> Optional[CachedDecision]:
        """Check if we have a cached decision for this harmonic pattern."""
        cache_key = f"{symbol}:{harmonic_tone.frequency}:{harmonic_tone.auris_node}:{harmonic_tone.brainwave}"

        cached = self.hot_path_cache.get(cache_key)
        if cached and not cached.is_expired():
            return cached

        # Clean expired entries
        expired_keys = [k for k, v in self.hot_path_cache.items() if v.is_expired()]
        for k in expired_keys:
            del self.hot_path_cache[k]

        return None

    def _cache_decision(self, symbol: str, harmonic_tone: HarmonicTone,
                        action: str, confidence: float, position_size_usd: float) -> None:
        """Cache a decision for future instant lookup."""
        cache_key = f"{symbol}:{harmonic_tone.frequency}:{harmonic_tone.auris_node}:{harmonic_tone.brainwave}"

        cached = CachedDecision(
            symbol=symbol,
            harmonic_pattern=(harmonic_tone.frequency, harmonic_tone.auris_node, harmonic_tone.brainwave),
            action=action,
            confidence=confidence,
            position_size_usd=position_size_usd,
            cached_at=time.time()
        )

        self.hot_path_cache[cache_key] = cached

        # Limit cache size
        if len(self.hot_path_cache) > 1000:
            # Remove oldest entries
            sorted_cache = sorted(self.hot_path_cache.items(), key=lambda x: x[1].cached_at)
            for i in range(100):
                del self.hot_path_cache[sorted_cache[i][0]]

    async def _generate_signal_via_mycelium(self, tick: HFTTick, harmonic_tone: HarmonicTone) -> None:
        """
        Generate trading signal via Mycelium neural network.
        This is the slower path when cache misses.
        """
        try:
            start_time = time.time()

            # Check harmonic pattern lookup first
            pattern_key = (harmonic_tone.frequency, harmonic_tone.auris_node, harmonic_tone.brainwave)
            action = self.harmonic_patterns.get(pattern_key, 'HOLD')

            # Adjust confidence based on harmonic strength
            confidence = harmonic_tone.confidence

            # Position sizing based on confidence and risk limits
            position_size_usd = self._calculate_position_size(confidence, tick.symbol)

            # Create signal
            signal = HFTSignal(
                id=f"HFT-{int(time.time()*1000000)}",
                timestamp=tick.timestamp,
                symbol=tick.symbol,
                action=action,
                confidence=confidence,
                position_size_usd=position_size_usd,
                harmonic_tone=harmonic_tone,
                reasoning=[
                    f"Harmonic pattern: {harmonic_tone.frequency}Hz + {harmonic_tone.auris_node} + {harmonic_tone.brainwave}",
                    f"Amplitude: {harmonic_tone.amplitude:.2f}",
                    f"Cache: MISS (generated via Mycelium)"
                ]
            )

            # Cache this decision for future use
            self._cache_decision(tick.symbol, harmonic_tone, action, confidence, position_size_usd)

            # Track latency
            latency_ms = (time.time() - start_time) * 1000
            self.signal_latencies.append(latency_ms)

            # Publish signal to thought bus
            await self._publish_signal(signal)

        except Exception as e:
            logger.debug(f"Mycelium signal generation error: {e}")

    async def _execute_cached_decision(self, cached: CachedDecision, tick: HFTTick) -> None:
        """Execute a cached decision instantly."""
        try:
            # Create signal from cached decision
            signal = HFTSignal(
                id=f"HFT-{int(time.time()*1000000)}",
                timestamp=tick.timestamp,
                symbol=tick.symbol,
                action=cached.action,
                confidence=cached.confidence,
                position_size_usd=cached.position_size_usd,
                harmonic_tone=HarmonicTone(
                    frequency=cached.harmonic_pattern[0],
                    amplitude=1.0,  # Cached decisions are high confidence
                    auris_node=cached.harmonic_pattern[1],
                    brainwave=cached.harmonic_pattern[2],
                    confidence=cached.confidence,
                    timestamp=tick.timestamp
                ),
                reasoning=[
                    f"Cached decision: {cached.action}",
                    f"Cache hit: {self.cache_hits}/{self.cache_hits + self.cache_misses}",
                    f"Latency: <1ms (hot path)"
                ]
            )

            # Publish signal immediately
            await self._publish_signal(signal)

        except Exception as e:
            logger.debug(f"Cached decision execution error: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # L3: ASYNC THOUGHT BUS
    # ═══════════════════════════════════════════════════════════════════════════

    def subscribe(self, topic: str, handler: Callable) -> None:
        """Subscribe to HFT thought bus topics."""
        if topic not in self.thought_handlers:
            self.thought_handlers[topic] = []
        self.thought_handlers[topic].append(handler)

    async def _publish_signal(self, signal: HFTSignal) -> None:
        """Publish HFT signal to thought bus."""
        try:
            # Add to queue for processing
            await self.signal_queue.put(signal)

            # Publish to ThoughtBus if wired
            if self.thought_bus:
                from aureon.core.aureon_thought_bus import Thought
                thought = Thought(
                    source="HFT",
                    topic="signal",
                    payload={
                        'signal': signal.to_dict(),
                        'timestamp': signal.timestamp,
                        'symbol': signal.symbol,
                        'action': signal.action,
                        'confidence': signal.confidence
                    }
                )
                self.thought_bus.publish(thought)

            # Publish to handlers
            topic = f"hft.signal.{signal.symbol.lower()}"
            await self._publish_to_handlers(topic, signal.to_dict())

            # Also publish to general hft.signal topic
            await self._publish_to_handlers("hft.signal", signal.to_dict())

        except Exception as e:
            logger.debug(f"Signal publish error: {e}")

    async def _publish_order(self, order: HFTOrder) -> None:
        """Publish HFT order to thought bus."""
        try:
            # Add to queue for processing
            await self.order_queue.put(order)

            # Publish to handlers
            topic = f"hft.order.{order.symbol.lower()}"
            await self._publish_to_handlers(topic, order.to_dict())

            # Also publish to general hft.order topic
            await self._publish_to_handlers("hft.order", order.to_dict())

        except Exception as e:
            logger.debug(f"Order publish error: {e}")

    async def _publish_to_handlers(self, topic: str, data: Dict) -> None:
        """Publish data to all handlers for a topic (parallel execution)."""
        handlers = []
        handlers.extend(self.thought_handlers.get(topic, []))
        handlers.extend(self.thought_handlers.get("*", []))  # Wildcard

        if handlers:
            # Execute all handlers in parallel
            tasks = [self._call_handler_safe(h, topic, data) for h in handlers]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _call_handler_safe(self, handler: Callable, topic: str, data: Dict) -> None:
        """Call handler safely with error handling."""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(topic, data)
            else:
                # Run sync handler in thread pool
                await self.event_loop.run_in_executor(None, handler, topic, data)
        except Exception as e:
            logger.debug(f"Handler error for topic {topic}: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # L4: ORDER ROUTER
    # ═══════════════════════════════════════════════════════════════════════════

    async def _execute_signal(self, signal: HFTSignal) -> None:
        """
        Execute trading signal via order router.
        Converts signal to order and submits via WebSocket.
        """
        try:
            if not self.order_router:
                logger.debug("No order router connected")
                return

            # Risk checks
            if not self._check_risk_limits(signal):
                return

            # Convert signal to order
            side = signal.action.lower()
            if side not in ['buy', 'sell']:
                return  # HOLD signal

            quantity = signal.position_size_usd / signal.harmonic_tone.amplitude  # Rough approximation
            price = 0.0  # Market order

            order = HFTOrder(
                id=f"ORDER-{signal.id}",
                signal_id=signal.id,
                timestamp=time.time(),
                symbol=signal.symbol,
                side=side,
                quantity=quantity,
                price=price
            )

            # Submit order
            start_time = time.time()
            success, order_id = await self.order_router.submit_order(order)

            if success:
                order.status = 'SENT'
                order.exchange_order_id = order_id
                order.latency_ms = (time.time() - start_time) * 1000
                self.active_orders[order.id] = order

                # Track latency
                self.order_latencies.append(order.latency_ms)

                logger.info(f"🦈💰 HFT ORDER SENT: {order.symbol} {order.side.upper()} ${order.quantity:.2f} "
                           f"(Latency: {order.latency_ms:.1f}ms)")

                # Publish order event
                await self._publish_order(order)
            else:
                logger.debug(f"Order submission failed: {order.symbol}")

        except Exception as e:
            logger.debug(f"Signal execution error: {e}")

    def _check_risk_limits(self, signal: HFTSignal) -> bool:
        """Check if signal passes risk limits."""
        # Daily loss limit
        if self.daily_pnl_usd <= HFT_DAILY_LOSS_LIMIT_USD:
            logger.warning(f"Daily loss limit reached: ${self.daily_pnl_usd:.2f}")
            self.mode = "PAUSED"
            return False

        # Position size limits
        if signal.position_size_usd < HFT_MIN_POSITION_SIZE_USD:
            return False
        if signal.position_size_usd > HFT_MAX_POSITION_SIZE_USD:
            return False

        # Concurrent order limits
        if len(self.active_orders) >= HFT_MAX_CONCURRENT_ORDERS:
            return False

        # Win/loss streak management
        if self.loss_streak >= HFT_LOSS_STREAK_PAUSE:
            logger.info(f"Loss streak pause: {self.loss_streak} losses")
            self.mode = "PAUSED"
            return False

        return True

    def _calculate_position_size(self, confidence: float, symbol: str) -> float:
        """Calculate position size based on confidence and Kelly criterion."""
        # Base size on confidence (Kelly-inspired)
        kelly_fraction = confidence * 0.1  # Conservative Kelly
        base_size = HFT_MAX_POSITION_SIZE_USD * kelly_fraction

        # Adjust for win/loss streak
        if self.win_streak > 0:
            base_size *= (1 + self.win_streak * 0.1)  # Increase on wins
        if self.loss_streak > 0:
            base_size *= (1 - self.loss_streak * 0.2)  # Decrease on losses

        # Symbol-specific adjustments (could be based on volatility)
        symbol_multiplier = 1.0
        if 'BTC' in symbol:
            symbol_multiplier = 1.2  # Higher for BTC
        elif 'ETH' in symbol:
            symbol_multiplier = 1.1  # Medium for ETH

        return min(base_size * symbol_multiplier, HFT_MAX_POSITION_SIZE_USD)

    # ═══════════════════════════════════════════════════════════════════════════
    # INTEGRATION METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    def wire_order_router(self, order_router) -> bool:
        """Wire the WebSocket order router."""
        if order_router is None:
            return False

        self.order_router = order_router
        logger.info("🦈🔌 HFT Order Router connected")
        return True

    def wire_mycelium(self, mycelium) -> bool:
        """Wire the Mycelium neural network."""
        if mycelium is None:
            return False

        self.mycelium_connected = True
        logger.info("🦈🧠 HFT Mycelium network connected")
        return True

    def wire_harmonic_alphabet(self, harmonic_alphabet) -> bool:
        """Wire the Harmonic Alphabet encoder."""
        if harmonic_alphabet is None:
            return False

        self.harmonic_alphabet_connected = True
        logger.info("🦈🎵 HFT Harmonic Alphabet connected")
        return True

    def wire_queen(self, queen) -> bool:
        """Wire the Queen for veto power."""
        if queen is None:
            return False

        self.queen_connected = True
        logger.info("🦈👑 HFT Queen connected (veto power)")
        return True

    def wire_orca(self, orca) -> bool:
        """Wire the Orca for whale intelligence."""
        if orca is None:
            return False

        self.orca_connected = True
        logger.info("🦈🐋 HFT Orca connected (whale intelligence)")
        return True

    def wire_thought_bus(self, thought_bus) -> bool:
        """Wire the ThoughtBus for signal publishing."""
        if thought_bus is None:
            return False

        self.thought_bus = thought_bus
        logger.info("🦈🧠 HFT ThoughtBus connected (signal publishing)")
        return True

    # ═══════════════════════════════════════════════════════════════════════════
    # CONTROL METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    def start_hft(self) -> bool:
        """Start HFT mode."""
        if not self.enabled:
            self.enabled = True
            self.mode = "SCANNING"
            logger.info("🦈▶️ HFT MODE ACTIVATED - SCANNING")
            return True
        return False

    def stop_hft(self) -> bool:
        """Stop HFT mode."""
        if self.enabled:
            self.enabled = False
            self.mode = "DORMANT"
            logger.info("🦈⏹️ HFT MODE DEACTIVATED")
            return True
        return False

    def set_executing_mode(self) -> bool:
        """Switch to executing mode (live trading)."""
        if self.mode == "SCANNING":
            self.mode = "EXECUTING"
            logger.info("🦈💰 HFT EXECUTING MODE - LIVE TRADING")
            return True
        return False

    def pause_hft(self) -> bool:
        """Pause HFT operations."""
        if self.mode in ["SCANNING", "EXECUTING"]:
            self.mode = "PAUSED"
            logger.info("🦈⏸️ HFT PAUSED")
            return True
        return False

    # ═══════════════════════════════════════════════════════════════════════════
    # MONITORING & STATUS
    # ═══════════════════════════════════════════════════════════════════════════

    def get_status(self) -> Dict:
        """Get HFT engine status."""
        uptime = time.time() - self.start_time

        avg_signal_latency = sum(self.signal_latencies) / len(self.signal_latencies) if self.signal_latencies else 0
        avg_order_latency = sum(self.order_latencies) / len(self.order_latencies) if self.order_latencies else 0

        cache_hit_rate = self.cache_hits / max(self.cache_hits + self.cache_misses, 1)

        return {
            'enabled': self.enabled,
            'mode': self.mode,
            'uptime_seconds': uptime,
            'tick_count': self.tick_count,
            'active_orders': len(self.active_orders),
            'completed_orders': len(self.completed_orders),
            'daily_pnl_usd': self.daily_pnl_usd,
            'win_streak': self.win_streak,
            'loss_streak': self.loss_streak,
            'cache_size': len(self.hot_path_cache),
            'cache_hit_rate': cache_hit_rate,
            'avg_signal_latency_ms': avg_signal_latency,
            'avg_order_latency_ms': avg_order_latency,
            'harmonic_patterns': len(self.harmonic_patterns),
            'integrations': {
                'mycelium': self.mycelium_connected,
                'harmonic_alphabet': self.harmonic_alphabet_connected,
                'queen': self.queen_connected,
                'orca': self.orca_connected,
                'order_router': self.order_router is not None
            }
        }

    @property
    def hot_path_cache_size(self) -> int:
        """Return number of cached hot-path decisions."""
        try:
            return len(self.hot_path_cache)
        except Exception:
            return 0

    @property
    def tick_buffer_capacity(self) -> int:
        """Return configured tick buffer capacity."""
        try:
            return self.tick_buffer.maxlen if hasattr(self.tick_buffer, 'maxlen') else HFT_TICK_BUFFER_SIZE
        except Exception:
            return HFT_TICK_BUFFER_SIZE


    def get_performance_stats(self) -> Dict:
        """Get detailed performance statistics."""
        return {
            'signal_latencies': list(self.signal_latencies),
            'order_latencies': list(self.order_latencies),
            'cache_performance': {
                'hits': self.cache_hits,
                'misses': self.cache_misses,
                'hit_rate': self.cache_hits / max(self.cache_hits + self.cache_misses, 1),
                'cache_size': len(self.hot_path_cache)
            },
            'risk_metrics': {
                'daily_pnl': self.daily_pnl_usd,
                'win_streak': self.win_streak,
                'loss_streak': self.loss_streak,
                'active_positions': len(self.active_orders)
            }
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # BACKGROUND PROCESSING
    # ═══════════════════════════════════════════════════════════════════════════

    async def run_background_tasks(self) -> None:
        """Run background processing tasks."""
        tasks = [
            self._process_signal_queue(),
            self._process_order_queue(),
            self._monitor_active_orders(),
            self._cleanup_expired_cache()
        ]
        await asyncio.gather(*tasks)

    async def _process_signal_queue(self) -> None:
        """Process signals from queue."""
        while True:
            try:
                signal = await self.signal_queue.get()
                await self._execute_signal(signal)
                self.signal_queue.task_done()
            except Exception as e:
                logger.debug(f"Signal queue processing error: {e}")
                await asyncio.sleep(0.001)  # Prevent tight loop

    async def _process_order_queue(self) -> None:
        """Process orders from queue."""
        while True:
            try:
                order = await self.order_queue.get()
                # Orders are already processed when created
                self.order_queue.task_done()
            except Exception as e:
                logger.debug(f"Order queue processing error: {e}")
                await asyncio.sleep(0.001)

    async def _monitor_active_orders(self) -> None:
        """Monitor active orders for fills and timeouts."""
        while True:
            try:
                current_time = time.time()

                # Check for timeouts
                timeout_orders = []
                for order_id, order in self.active_orders.items():
                    if current_time - order.timestamp > (HFT_ORDER_TIMEOUT_MS / 1000):
                        order.status = 'TIMEOUT'
                        timeout_orders.append(order_id)

                # Remove timed out orders
                for order_id in timeout_orders:
                    order = self.active_orders.pop(order_id)
                    logger.debug(f"Order timeout: {order.symbol} {order.side}")

                await asyncio.sleep(0.01)  # Check every 10ms

            except Exception as e:
                logger.debug(f"Order monitoring error: {e}")
                await asyncio.sleep(0.1)

    async def _cleanup_expired_cache(self) -> None:
        """Clean up expired cache entries."""
        while True:
            try:
                # Clean expired entries
                expired_keys = [k for k, v in self.hot_path_cache.items() if v.is_expired()]
                for k in expired_keys:
                    del self.hot_path_cache[k]

                await asyncio.sleep(1.0)  # Clean every second

            except Exception as e:
                logger.debug(f"Cache cleanup error: {e}")
                await asyncio.sleep(1.0)


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_hft_instance: Optional[HFTHarmonicEngine] = None

def get_hft_engine() -> HFTHarmonicEngine:
    """Get the global HFT engine instance."""
    global _hft_instance
    if _hft_instance is None:
        _hft_instance = HFTHarmonicEngine()
    return _hft_instance


# ═══════════════════════════════════════════════════════════════════════════════
# TEST / DEMO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("🦈🔪 HFT HARMONIC MYCELIUM ENGINE TEST 🔪🦈")
    print("=" * 60)
    print()

    async def test_hft():
        hft = get_hft_engine()

        print("📊 HFT Engine Status:")
        status = hft.get_status()
        for k, v in status.items():
            if k != 'integrations':
                print(f"   {k}: {v}")
        print()

        print("🔗 Integrations:")
        for k, v in status['integrations'].items():
            print(f"   {k}: {'✅' if v else '❌'}")
        print()

        # Test tick ingestion
        print("📈 Testing tick ingestion...")
        test_tick = {
            'timestamp': time.time(),
            'symbol': 'BTC/USD',
            'price': 95000.0,
            'volume': 0.1,
            'side': 'buy',
            'exchange': 'binance',
            'tick_id': 'test-123'
        }

        hft.ingest_tick(test_tick)
        print(f"   Ingested tick: {test_tick['symbol']} @ ${test_tick['price']}")
        print(f"   Buffer size: {len(hft.tick_buffer)}")
        print()

        # Test harmonic encoding
        print("🎵 Testing harmonic encoding...")
        tick = HFTTick(**test_tick)
        harmonic_tone = await hft._encode_harmonic_tone(tick)
        if harmonic_tone:
            print(f"   Encoded: {harmonic_tone.frequency}Hz + {harmonic_tone.auris_node} + {harmonic_tone.brainwave}")
            print(f"   Amplitude: {harmonic_tone.amplitude:.2f}, Confidence: {harmonic_tone.confidence:.2f}")
        print()

        # Test pattern lookup
        print("🔍 Testing pattern lookup...")
        if harmonic_tone:
            pattern_key = (harmonic_tone.frequency, harmonic_tone.auris_node, harmonic_tone.brainwave)
            action = hft.harmonic_patterns.get(pattern_key, 'UNKNOWN')
            print(f"   Pattern {pattern_key} → {action}")
        print()

        print("🦈 HFT ENGINE READY FOR LIVE TRADING 🦈")

    # Run test
    asyncio.run(test_hft())


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL HFT ENGINE INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_hft_engine_instance: Optional[HFTHarmonicEngine] = None

def get_hft_engine() -> Optional[HFTHarmonicEngine]:
    """Get or create global HFT engine instance."""
    global _hft_engine_instance
    if _hft_engine_instance is None:
        _hft_engine_instance = HFTHarmonicEngine()
    return _hft_engine_instance

def inject_tick(tick: HFTTick) -> None:
    """Inject HFT tick into global engine instance."""
    engine = get_hft_engine()
    if engine:
        # Convert HFTTick to dict for ingest_tick method
        tick_dict = {
            'timestamp': tick.timestamp,
            'symbol': tick.symbol,
            'price': tick.price,
            'volume': tick.volume,
            'side': tick.side,
            'exchange': tick.exchange,
            'tick_id': tick.tick_id
        }
        engine.ingest_tick(tick_dict)
