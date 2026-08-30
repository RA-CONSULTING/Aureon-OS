#!/usr/bin/env python3
"""
💰 DYNAMIC COST ESTIMATOR 💰
============================

Learns actual trading costs from recent executions and provides
conservative, data-driven cost estimates for Monte Carlo approval.

FEATURES:
- Rolling window of recent realized fees/spreads
- Conservative floor/ceiling bounds (never too optimistic)
- Explicit no_data when no provider-receipted execution costs exist
- Per-symbol cost tracking with observed global estimates

Gary Leckey | January 2026 | TRUST THE MATH, LEARN FROM REALITY
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os

# Windows UTF-8 fix
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

import time
import math
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class CostDataUnavailableError(RuntimeError):
    """Raised when no fresh provider-receipted cost observations exist."""


@dataclass
class CostSample:
    """A single cost observation."""
    timestamp: float
    symbol: str
    side: str  # 'buy' or 'sell'
    notional_usd: float
    fee_pct: float
    spread_pct: float
    slippage_pct: float
    total_cost_pct: float
    source_id: str
    source_timestamp: float
    generated_values: bool = False


@dataclass
class CostEstimate:
    """Estimated costs for a trade."""
    symbol: str
    side: str
    estimated_fee_pct: float
    estimated_spread_pct: float
    estimated_slippage_pct: float
    estimated_total_pct: float
    confidence: float  # 0-1 (based on sample count)
    sample_count: int
    source: str  # 'symbol_specific' or 'global_average'
    truth_status: str
    source_id: str
    source_timestamp: float
    generated_values: bool = False


class DynamicCostEstimator:
    """
    Learns from recent trades to provide dynamic cost estimates.
    
    PHILOSOPHY:
    - Use recent data when available
    - Conservative floor (never underestimate costs)
    - Safe ceiling (cap extreme outliers)
    - Refuse to estimate when no observed costs exist
    
    ROLLING WINDOWS:
    - Per-symbol: last 20 samples (symbol-specific learning)
    - Global: last 100 samples (exchange-wide baseline)
    - Window age: samples older than 24h decay in weight
    """
    
    # Conservative bounds (never estimate below/above these)
    MIN_FEE_PCT = 0.10      # 10 bps (tier 8 best case = 10 bps taker)
    MAX_FEE_PCT = 0.30      # 30 bps (tier 1 worst case = 25 bps + buffer)
    MIN_SPREAD_PCT = 0.05   # 5 bps (highly liquid pairs)
    MAX_SPREAD_PCT = 0.20   # 20 bps (less liquid pairs)
    MIN_SLIPPAGE_PCT = 0.01 # 1 bp (market orders on liquid pairs)
    MAX_SLIPPAGE_PCT = 0.65 # 65% (allow extreme slippage learning)
    
    # Window sizes
    SYMBOL_WINDOW_SIZE = 20   # Per-symbol samples
    GLOBAL_WINDOW_SIZE = 100  # Global samples
    SAMPLE_TTL_SECONDS = 86400  # 24 hours
    
    def __init__(self):
        # Per-symbol rolling windows
        self._symbol_samples: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self.SYMBOL_WINDOW_SIZE)
        )
        
        # Global rolling window (all symbols)
        self._global_samples: deque = deque(maxlen=self.GLOBAL_WINDOW_SIZE)
        
        # Stats
        self._total_samples = 0
        self._estimates_served = 0
        
        logger.info("💰 Dynamic Cost Estimator initialized")
        logger.info("   Cost estimates require fresh provider execution receipts")
        logger.info(f"   Symbol window: {self.SYMBOL_WINDOW_SIZE} samples")
        logger.info(f"   Global window: {self.GLOBAL_WINDOW_SIZE} samples")
    
    def add_sample(
        self,
        symbol: str,
        side: str,
        notional_usd: float,
        fee_pct: float,
        spread_pct: float,
        slippage_pct: float,
        source_id: str,
        source_timestamp: float,
    ) -> None:
        """
        Record a new cost sample from an actual execution.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USD')
            side: 'buy' or 'sell'
            notional_usd: Trade size in USD
            fee_pct: Realized fee as percentage (e.g., 0.15 for 15 bps)
            spread_pct: Realized spread as percentage
            slippage_pct: Realized slippage as percentage
            source_id: Provider execution-receipt identifier
            source_timestamp: Provider observation time as Unix seconds
        """
        numeric_values = {
            'notional_usd': notional_usd,
            'fee_pct': fee_pct,
            'spread_pct': spread_pct,
            'slippage_pct': slippage_pct,
            'source_timestamp': source_timestamp,
        }
        if not source_id or not str(source_id).strip():
            raise ValueError('source_id is required for a real cost observation')
        for name, value in numeric_values.items():
            if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise ValueError(f'{name} must be a finite provider observation')
        if float(notional_usd) <= 0 or float(source_timestamp) <= 0:
            raise ValueError('notional_usd and source_timestamp must be positive')
        if any(float(value) < 0 for value in (fee_pct, spread_pct, slippage_pct)):
            raise ValueError('observed cost percentages cannot be negative')
        collected_at = time.time()
        receipt_age = collected_at - float(source_timestamp)
        if receipt_age > self.SAMPLE_TTL_SECONDS:
            raise CostDataUnavailableError('NO_DATA: cost receipt is stale')
        if receipt_age < -300:
            raise ValueError('source_timestamp is more than five minutes in the future')

        total_cost_pct = fee_pct + spread_pct + slippage_pct
        
        sample = CostSample(
            timestamp=collected_at,
            symbol=symbol,
            side=side,
            notional_usd=notional_usd,
            fee_pct=fee_pct,
            spread_pct=spread_pct,
            slippage_pct=slippage_pct,
            total_cost_pct=total_cost_pct,
            source_id=str(source_id),
            source_timestamp=float(source_timestamp),
            generated_values=False,
        )
        
        # Add to both windows
        self._symbol_samples[symbol].append(sample)
        self._global_samples.append(sample)
        self._total_samples += 1
        
        logger.debug(
            f"💰 Cost sample: {symbol} {side} ${notional_usd:.2f} | "
            f"fee={fee_pct:.3f}% spread={spread_pct:.3f}% slip={slippage_pct:.3f}% | "
            f"total={total_cost_pct:.3f}%"
        )
    
    def estimate_cost(
        self,
        symbol: str,
        side: str,
        notional_usd: float
    ) -> CostEstimate:
        """
        Estimate costs for a trade.
        
        Priority:
        1. Symbol-specific data (if enough recent samples)
        2. Global average (if any samples exist)
        3. Explicit no_data error
        
        Returns:
            CostEstimate with breakdown and confidence score
        """
        self._estimates_served += 1
        now = time.time()
        
        # Try symbol-specific estimate
        symbol_samples = list(self._symbol_samples.get(symbol, []))
        if len(symbol_samples) >= 5:  # Need at least 5 samples for confidence
            # Filter recent samples (within TTL)
            recent = [
                sample
                for sample in symbol_samples
                if 0 <= (now - sample.source_timestamp) < self.SAMPLE_TTL_SECONDS
            ]
            if len(recent) >= 3:
                return self._compute_estimate(symbol, side, recent, source='symbol_specific')
        
        # Fall back to global average
        if len(self._global_samples) >= 10:
            recent = [
                sample
                for sample in self._global_samples
                if 0 <= (now - sample.source_timestamp) < self.SAMPLE_TTL_SECONDS
            ]
            if len(recent) >= 5:
                return self._compute_estimate(symbol, side, recent, source='global_average')
        
        raise CostDataUnavailableError(
            f'NO_DATA: no fresh provider-receipted cost samples for {symbol} {side}'
        )
    
    def _compute_estimate(
        self,
        symbol: str,
        side: str,
        samples: List[CostSample],
        source: str
    ) -> CostEstimate:
        """Compute estimate from samples with conservative bounds."""
        if not samples:
            raise CostDataUnavailableError('NO_DATA: empty cost sample set')
        invalid_receipts = [
            sample
            for sample in samples
            if not sample.source_id
            or sample.source_timestamp <= 0
            or sample.generated_values is not False
        ]
        if invalid_receipts:
            raise CostDataUnavailableError(
                'NO_DATA: cost sample set contains observations without valid provenance'
            )

        # Weight recent samples more heavily (exponential decay)
        now = time.time()
        weights = []
        for s in samples:
            age_hours = (now - s.source_timestamp) / 3600
            weight = 2.0 ** (-age_hours / 6)  # Half-life of 6 hours
            weights.append(weight)
        
        total_weight = sum(weights)
        if total_weight <= 0:
            raise CostDataUnavailableError('NO_DATA: cost observation weights are empty')
        
        # Weighted averages
        avg_fee = sum(s.fee_pct * w for s, w in zip(samples, weights)) / total_weight
        avg_spread = sum(s.spread_pct * w for s, w in zip(samples, weights)) / total_weight
        avg_slip = sum(s.slippage_pct * w for s, w in zip(samples, weights)) / total_weight
        
        # Apply conservative bounds (clamp)
        fee_pct = max(self.MIN_FEE_PCT, min(self.MAX_FEE_PCT, avg_fee))
        spread_pct = max(self.MIN_SPREAD_PCT, min(self.MAX_SPREAD_PCT, avg_spread))
        slip_pct = max(self.MIN_SLIPPAGE_PCT, min(self.MAX_SLIPPAGE_PCT, avg_slip))
        
        # Add 10% safety buffer to total (be pessimistic)
        total_pct = (fee_pct + spread_pct + slip_pct) * 1.10
        
        # Confidence based on sample count (more samples = higher confidence)
        confidence = min(1.0, len(samples) / 20)
        
        return CostEstimate(
            symbol=symbol,
            side=side,
            estimated_fee_pct=fee_pct,
            estimated_spread_pct=spread_pct,
            estimated_slippage_pct=slip_pct,
            estimated_total_pct=total_pct,
            confidence=confidence,
            sample_count=len(samples),
            source=source,
            truth_status='real_derived',
            source_id='dynamic_cost_estimator:' + ','.join(
                sorted({sample.source_id for sample in samples})
            ),
            source_timestamp=max(sample.source_timestamp for sample in samples),
            generated_values=False,
        )
    
    def get_stats(self) -> Dict:
        """Get estimator statistics."""
        symbol_count = len(self._symbol_samples)
        symbols_with_data = sum(1 for samples in self._symbol_samples.values() if len(samples) > 0)
        
        return {
            'total_samples': self._total_samples,
            'global_window': len(self._global_samples),
            'symbol_count': symbol_count,
            'symbols_with_data': symbols_with_data,
            'estimates_served': self._estimates_served,
        }
    
    def reset(self) -> None:
        """Clear all samples (for testing or manual reset)."""
        self._symbol_samples.clear()
        self._global_samples.clear()
        self._total_samples = 0
        logger.info("💰 Cost estimator reset - all samples cleared")

    def _draw_total_costs(self, symbol: str, n_samples: int = 1000) -> List[float]:
        """Return an empirical distribution from observed cost receipts.

        Values are repeated deterministically when a caller requests a larger
        distribution. No Gaussian noise or default cost is manufactured.
        """
        now = time.time()
        base = [
            sample
            for sample in self._symbol_samples.get(symbol, [])
            if 0 <= (now - sample.source_timestamp) < self.SAMPLE_TTL_SECONDS
        ]
        if not base:
            base = [
                sample
                for sample in self._global_samples
                if 0 <= (now - sample.source_timestamp) < self.SAMPLE_TTL_SECONDS
            ]
        if not base:
            return []

        observed = sorted(float(sample.total_cost_pct) for sample in base)
        count = max(0, int(n_samples))
        return [observed[index % len(observed)] for index in range(count)]

    def sample_total_cost_distribution(self, symbol: str, side: str, notional_usd: float, n_samples: int = 1000) -> Dict[str, Any]:
        """Summarize the empirical distribution of observed total costs.

        Returns percentiles keyed by 'p5','p50','p90','p95' and a 'samples' list for debugging (truncated).
        """
        draws = self._draw_total_costs(symbol, n_samples=n_samples)
        if not draws:
            return {
                'status': 'no_data',
                'truth_status': 'no_data',
                'p5': None,
                'p50': None,
                'p90': None,
                'p95': None,
                'samples': [],
            }
        draws.sort()
        def pct(p):
            idx = max(0, min(len(draws)-1, int(len(draws)*p/100)))
            return draws[idx]

        return {
            'status': 'ok',
            'truth_status': 'real_derived',
            'p5': pct(5),
            'p50': pct(50),
            'p90': pct(90),
            'p95': pct(95),
            'samples': draws[:10],
        }

    def sample_total_cost_draws(self, symbol: str, side: str, notional_usd: float, n_samples: int = 1000) -> List[float]:
        """Return observed empirical cost values for further analysis."""
        return self._draw_total_costs(symbol, n_samples=n_samples)


# Singleton instance
_instance: Optional[DynamicCostEstimator] = None


def get_cost_estimator() -> DynamicCostEstimator:
    """Get global cost estimator instance."""
    global _instance
    if _instance is None:
        _instance = DynamicCostEstimator()
    return _instance
