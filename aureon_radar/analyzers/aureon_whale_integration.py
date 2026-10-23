"""
Integration helpers for other subsystems to query latest whale predictions.

Provides:
- get_latest_prediction(symbol) -> latest prediction payload or None
- subscribe_to_whale_predictions(handler) -> register a callback
"""
from __future__ import annotations
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import logging
from typing import Any, Callable, Dict, Optional

from aureon.core.aureon_thought_bus import get_thought_bus, Thought

logger = logging.getLogger(__name__)

_latest: Dict[str, Dict] = {}
_subscribers: list = []


def _on_predicted(thought: Thought) -> None:
    payload = thought.payload or {}
    symbol = payload.get('symbol') or (payload.get('prediction') or {}).get('symbol')
    prediction = payload.get('prediction') or payload
    if not symbol:
        return
    # Merge with existing latest data, preserve shape if present
    existing = _latest.get(symbol, {})
    existing.update(prediction)
    _latest[symbol] = existing
    for cb in _subscribers:
        try:
            cb(symbol, prediction)
        except Exception:
            logger.debug('Subscriber callback failed')


def _on_shape(thought: Thought) -> None:
    payload = thought.payload or {}
    symbol = payload.get('symbol')
    shape = payload.get('shape') or payload.get('spectrogram')
    if not symbol:
        return
    existing = _latest.get(symbol, {})
    existing['shape'] = shape
    _latest[symbol] = existing
    for cb in _subscribers:
        try:
            cb(symbol, existing)
        except Exception:
            logger.debug('Subscriber callback failed')


def start_integration():
    tb = get_thought_bus()
    try:
        tb.subscribe('whale.behavior.predicted', _on_predicted)
    except Exception:
        logger.debug('Unable to subscribe to whale.behavior.predicted')
    try:
        tb.subscribe('whale.shape.detected', _on_shape)
    except Exception:
        logger.debug('Unable to subscribe to whale.shape.detected')


def get_latest_prediction(symbol: str) -> Optional[Dict]:
    return _latest.get(symbol)


def subscribe_to_whale_predictions(callback: Callable[[str, Dict], None]) -> None:
    _subscribers.append(callback)


# Auto-start on import
try:
    start_integration()
except Exception:
    pass
