"""
Whale Pattern Mapper

Subscribes to `whale.orderbook.analyzed` Thoughts, classifies patterns (accumulation,
distribution, manipulation, support/resistance), stores patterns in Elephant Memory
and publishes `whale.pattern.classified` Thoughts for downstream predictors.
"""
from __future__ import annotations
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import hashlib
import logging
import time
from dataclasses import asdict
from typing import Any, Dict, Optional

from aureon.core.aureon_thought_bus import get_thought_bus, Thought
from aureon.intelligence.aureon_elephant_learning import ElephantMemory, LearnedPattern

try:
    from aureon.bots.whale_metrics import whale_pattern_classified_total, whale_pattern_confidence
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False

logger = logging.getLogger(__name__)


class WhalePatternMapper:
    def __init__(self, elephant: Optional[ElephantMemory] = None):
        self.thought_bus = get_thought_bus()
        self.elephant = elephant or ElephantMemory()
        # subscribe
        try:
            self.thought_bus.subscribe('whale.orderbook.analyzed', self._on_orderbook_analyzed)
        except Exception:
            logger.debug('WhalePatternMapper subscription failed')

    def _on_orderbook_analyzed(self, thought: Thought) -> None:
        payload = thought.payload or {}
        symbol = payload.get('symbol')
        if not symbol:
            return
        pattern = self._classify(payload)
        # Persist as LearnedPattern
        pid = hashlib.sha1(f"{symbol}:{pattern['subtype']}:{int(time.time())}".encode('utf-8')).hexdigest()
        lp = LearnedPattern(
            pattern_id=pid,
            pattern_type='whale',
            symbol=symbol,
            timeframe='orderbook',
            conditions=pattern,
        )
        self.elephant.remember_pattern(lp)

        # Publish classification
        th = Thought(source='whale_pattern_mapper', topic='whale.pattern.classified', payload={'symbol': symbol, 'pattern': pattern, 'pattern_id': pid})
        try:
            self.thought_bus.publish(th)
            # Emit metrics
            if METRICS_AVAILABLE:
                pattern_type = pattern.get('subtype', 'unknown')
                whale_pattern_classified_total.inc(pattern_type=pattern_type, symbol=symbol)
                whale_pattern_confidence.set(pattern.get('score', 0.0), symbol=symbol, pattern_type=pattern_type)
        except Exception:
            logger.debug('Failed to publish whale.pattern.classified')

    def _classify(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Return a classification dict with subtype and score"""
        walls = analysis.get('walls', []) or []
        layering = float(analysis.get('layering_score', 0.0) or 0.0)
        bids_depth = float(analysis.get('bids_depth', 0.0) or 0.0)
        asks_depth = float(analysis.get('asks_depth', 0.0) or 0.0)

        subtype = 'neutral'
        score = 0.0

        # Strong bid walls >> accumulation
        if walls:
            bid_walls = [w for w in walls if w.get('side') == 'bid']
            ask_walls = [w for w in walls if w.get('side') == 'ask']
            if bid_walls and not ask_walls:
                subtype = 'accumulation'
                score = max(w['notional_usd'] for w in bid_walls) / (100000.0)
            elif ask_walls and not bid_walls:
                subtype = 'distribution'
                score = max(w['notional_usd'] for w in ask_walls) / (100000.0)
            else:
                # both sides present - could be manipulation or deep liquidity
                if layering > 0.6:
                    subtype = 'manipulation'
                    score = layering
                else:
                    subtype = 'mixed'
                    score = layering * 0.5
        else:
            # No explicit walls - use depth imbalance
            if bids_depth > asks_depth * 1.5:
                subtype = 'support'
                score = min(0.99, bids_depth / (asks_depth + 1e-9) / 2.0)
            elif asks_depth > bids_depth * 1.5:
                subtype = 'resistance'
                score = min(0.99, asks_depth / (bids_depth + 1e-9) / 2.0)
            else:
                subtype = 'neutral'
                score = 0.0

        return {'subtype': subtype, 'score': float(score), 'layering': layering, 'bids_depth': bids_depth, 'asks_depth': asks_depth}


# If module imported, create a mapper singleton (easy to use)
default_mapper: Optional[WhalePatternMapper] = None
try:
    default_mapper = WhalePatternMapper()
except Exception:
    default_mapper = None
