"""
Whale Behavior Predictor

Subscribes to `whale.pattern.classified`, aggregates recent patterns from
ElephantMemory, applies a simple Batten Matrix style 3-pass validation, and
publishes `whale.behavior.predicted` Thoughts with action/confidence/time_horizon.
"""
from __future__ import annotations
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import logging
import math
import time
from typing import Any, Dict, List, Optional

from aureon.core.aureon_thought_bus import get_thought_bus, Thought
from aureon.intelligence.aureon_elephant_learning import ElephantMemory

logger = logging.getLogger(__name__)


class WhaleBehaviorPredictor:
    def __init__(self, elephant: Optional[ElephantMemory] = None):
        self.thought_bus = get_thought_bus()
        self.elephant = elephant or ElephantMemory()
        self.recent: Dict[str, List[Dict[str, Any]]] = {}
        try:
            self.thought_bus.subscribe('whale.pattern.classified', self._on_pattern)
        except Exception:
            logger.debug('WhaleBehaviorPredictor subscription failed')

    def _on_pattern(self, thought: Thought) -> None:
        payload = thought.payload or {}
        symbol = payload.get('symbol')
        pattern = payload.get('pattern')
        if not symbol or not pattern:
            return
        # store minimal recent history
        self.recent.setdefault(symbol, []).append({'ts': time.time(), 'pattern': pattern})
        # compute prediction and publish
        pred = self.predict_next_move(symbol)
        th = Thought(source='whale_behavior_predictor', topic='whale.behavior.predicted', payload={'symbol': symbol, 'prediction': pred})
        try:
            self.thought_bus.publish(th)
        except Exception:
            logger.debug('Failed to publish whale.behavior.predicted')

    def predict_next_move(self, symbol: str) -> Dict[str, Any]:
        # Gather recent patterns (prefer explicit memory but combine both)
        recent = self.recent.get(symbol, [])[-10:]
        # also fetch from elephant memory (patterns may be many)
        historical = [p for p in self.elephant.patterns.values() if p.symbol == symbol and p.pattern_type == 'whale']
        # simple validators
        p1 = self._validate_recent_activity(recent)
        p2 = self._validate_historical_success(historical)
        p3 = self._validate_market_context(symbol)
        p4 = self._validate_shape_history(symbol)

        coherence = 1.0 - (max(p1, p2, p3, p4) - min(p1, p2, p3, p4))
        drift = self._compute_drift(recent)
        lambda_score = math.exp(-0.5 * drift)

        avg = (p1 + p2 + p3 + p4) / 4.0
        final_score = avg * coherence * lambda_score

        action = 'wait'
        if final_score > 0.7:
            action = 'buy' if avg > 0.6 else 'sell'
        elif final_score > 0.5:
            action = 'lean_buy' if avg > 0.55 else 'lean_sell'

        time_horizon = int(max(1, min(60, 30 * final_score)))  # minutes

        return {'symbol': symbol, 'action': action, 'confidence': float(final_score), 'time_horizon_minutes': time_horizon, 'validators': {'p1': p1, 'p2': p2, 'p3': p3, 'p4': p4}, 'coherence': float(coherence), 'lambda': float(lambda_score)}

    def _validate_recent_activity(self, recent: List[Dict]) -> float:
        if not recent:
            return 0.4
        # increase if many accumulation patterns recently
        acc = sum(1 for r in recent if r['pattern'].get('subtype') == 'accumulation')
        dist = sum(1 for r in recent if r['pattern'].get('subtype') == 'distribution')
        man = sum(1 for r in recent if r['pattern'].get('subtype') == 'manipulation')
        score = (acc - dist - man) / max(1, len(recent))
        return float(max(0.0, min(1.0, 0.5 + score)))

    def _validate_historical_success(self, patterns: List[Any]) -> float:
        if not patterns:
            return 0.45
        # weight by pattern confidence and historical win_rate
        total = 0.0
        wsum = 0.0
        for p in patterns[-100:]:
            conf = p.confidence/100.0 if hasattr(p, 'confidence') else 0.5
            win = (p.win_rate/100.0) if hasattr(p, 'win_rate') else 0.5
            total += conf * win
            wsum += conf
        if wsum == 0:
            return 0.5
        return float(max(0.0, min(1.0, total/wsum)))

    def _validate_shape_history(self, symbol: str) -> float:
        """Validate using Whale Shape historical performance."""
        # Gather recent whale_shape patterns from elephant memory
        shapes = [p for p in self.elephant.patterns.values() if p.symbol == symbol and p.pattern_type == 'whale_shape']
        if not shapes:
            return 0.45
        total = 0.0
        wsum = 0.0
        for p in shapes[-200:]:
            conf = p.confidence/100.0 if hasattr(p, 'confidence') else 0.5
            win = (p.win_rate/100.0) if hasattr(p, 'win_rate') else 0.5
            total += conf * win
            wsum += conf
        if wsum == 0:
            return 0.5
        return float(max(0.0, min(1.0, total/wsum)))

    def _validate_market_context(self, symbol: str) -> float:
        # Stub: use simple liquidity check from Elephant asset_performance as proxy
        ap = self.elephant.asset_performance.get(symbol, {})
        trades = ap.get('trades', 0)
        if trades > 1000:
            return 0.6
        if trades > 100:
            return 0.5
        return 0.45

    def _compute_drift(self, recent: List[Dict]) -> float:
        if len(recent) < 2:
            return 0.0
        # simple drift: average time between pattern events (lower = more drift)
        timestamps = [r['ts'] for r in recent]
        diffs = [timestamps[i+1]-timestamps[i] for i in range(len(timestamps)-1)]
        avg = sum(diffs)/len(diffs)
        return float(1.0/(avg + 1e-9))


# Create a default predictor on import
default_predictor: Optional[WhaleBehaviorPredictor] = None
try:
    default_predictor = WhaleBehaviorPredictor()
except Exception:
    default_predictor = None
