"""
Whale Shape Registry

Listens to `whale.shape.detected` Thoughts, records shape events into ElephantMemory
as LearnedPattern entries of type 'whale_shape', and exposes helpers to record outcomes
of shapes (profit/loss) for later learning.

Publishes:
- topic: `whale.shape.recorded` payload: {symbol, pattern_id, subtype, score}
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

logger = logging.getLogger(__name__)


class WhaleShapeRegistry:
    def __init__(self, elephant: Optional[ElephantMemory] = None):
        self.thought_bus = get_thought_bus()
        self.elephant = elephant or ElephantMemory()
        try:
            self.thought_bus.subscribe('whale.shape.detected', self._on_shape_detected)
        except Exception:
            logger.debug('WhaleShapeRegistry: failed to subscribe to whale.shape.detected')

    def _on_shape_detected(self, thought: Thought) -> None:
        payload = thought.payload or {}
        symbol = payload.get('symbol')
        shape = payload.get('shape') or {}
        if not symbol or not shape:
            return
        subtype = shape.get('subtype', 'unknown')
        score = float(shape.get('score', 0.0) or 0.0)

        pid = hashlib.sha1(f"shape:{symbol}:{subtype}:{int(time.time())}".encode('utf-8')).hexdigest()
        lp = LearnedPattern(
            pattern_id=pid,
            pattern_type='whale_shape',
            symbol=symbol,
            timeframe='orderbook_shape',
            conditions={'subtype': subtype, 'score': score, 'spectrogram': payload.get('spectrogram', {})}
        )
        self.elephant.remember_pattern(lp)

        th = Thought(source='whale_shape_registry', topic='whale.shape.recorded', payload={'symbol': symbol, 'pattern_id': pid, 'subtype': subtype, 'score': score})
        try:
            self.thought_bus.publish(th)
        except Exception:
            logger.debug('Failed to publish whale.shape.recorded')

    def record_shape_outcome(self, pattern_id: str, profit: float, is_win: bool) -> None:
        """Record the trade outcome associated with a shape pattern"""
        p = self.elephant.patterns.get(pattern_id)
        if not p:
            logger.debug('Unknown pattern id %s', pattern_id)
            return
        p.update_performance(profit, is_win)
        self.elephant.remember_pattern(p)
        logger.info('Recorded outcome for shape %s profit=%.2f win=%s', pattern_id, profit, is_win)


# Default registry singleton
default_shape_registry: Optional[WhaleShapeRegistry] = None
try:
    default_shape_registry = WhaleShapeRegistry()
except Exception:
    default_shape_registry = None
