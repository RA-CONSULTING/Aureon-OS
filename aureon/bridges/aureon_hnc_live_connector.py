#!/usr/bin/env python3
"""
HNC Live Connector
------------------
Periodically reads the websocket price cache (ws_cache/ws_prices.json) and feeds
price ticks into the `HncSurgeDetector`. When a surge is detected, publishes an
`intelligence.surge.hnc` event via the global `RealDataFeedHub`.

Usage:
    python aureon_hnc_live_connector.py --symbols BTC,ETH,SOL --interval 0.5

"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

import time
import json
import hashlib
import math
import argparse
import logging
from pathlib import Path
from collections import deque
from typing import Any, Dict, List, Optional

from aureon.bridges.aureon_hnc_surge_detector import HncSurgeDetector, SurgeWindow
from aureon.data_feeds.aureon_real_data_feed_hub import get_feed_hub

# Integrations: ThoughtBus for pub/sub and QGITA for Lighthouse validation
try:
    from aureon.core.aureon_thought_bus import get_thought_bus, Thought
    THOUGHT_BUS_OK = True
except Exception:
    get_thought_bus = None
    Thought = None
    THOUGHT_BUS_OK = False

try:
    from aureon.wisdom.aureon_qgita_framework import QGITAMarketAnalyzer
    QGITA_OK = True
except Exception:
    QGITAMarketAnalyzer = None
    QGITA_OK = False

logger = logging.getLogger(__name__)

DEFAULT_WS_CACHE = Path(os.getenv('WS_PRICE_CACHE_PATH', 'ws_cache/ws_prices.json'))
MAX_RECEIPT_AGE_SECONDS = 120.0
FUTURE_SKEW_SECONDS = 30.0


class HncLiveConnector:
    def __init__(self, symbols: List[str], ws_cache_path: Path = DEFAULT_WS_CACHE, poll_interval: float = 0.5):
        self.symbols = symbols
        self.ws_cache_path = Path(ws_cache_path)
        self.poll_interval = poll_interval
        # Adjust detector sample_rate to match poll interval (samples per second)
        sample_rate = max(1, int(round(1.0 / self.poll_interval)))
        # Use an analysis window of 10-60 seconds depending on sample rate
        analysis_window_secs = 20
        analysis_window_size = max(32, min(2048, sample_rate * analysis_window_secs))
        self.detector = HncSurgeDetector(sample_rate=sample_rate, analysis_window_size=analysis_window_size)
        self._source_timestamp_history: Dict[str, deque] = {}
        self._receipt_id_history: Dict[str, deque] = {}
        self._last_receipt: Dict[str, Dict[str, Any]] = {}
        self._last_read_ts = 0.0
        self.hub = get_feed_hub()

        # Wire ThoughtBus if available (for cross-system subscriptions)
        try:
            if THOUGHT_BUS_OK:
                self.thought_bus = get_thought_bus()
                logger.info("ThoughtBus: connected for HNC events")
            else:
                self.thought_bus = None
        except Exception:
            self.thought_bus = None

        # Initialize QGITA market analyzer for Lighthouse validation
        if QGITA_OK and QGITAMarketAnalyzer is not None:
            try:
                self.qgita = QGITAMarketAnalyzer()
                logger.info("QGITA: Analyzer initialized for Lighthouse validation")
            except Exception:
                self.qgita = None
        else:
            self.qgita = None

        # Optional: lazy reference to BotShapeScanner (do not auto-start WS)
        try:
            from aureon.bots_intelligence.aureon_bot_shape_scanner import BotShapeScanner
            self.bot_shape_scanner = BotShapeScanner(self.symbols)
            logger.info("BotShapeScanner: available (not auto-started)")
        except Exception:
            self.bot_shape_scanner = None

        logger.info(f"HNC Live Connector initialized (symbols={self.symbols}, cache={self.ws_cache_path}, sample_rate={sample_rate}, window={analysis_window_size})")

        # Subscribe to RealDataFeedHub market topics for live ticks (if available)
        try:
            if hasattr(self.hub, 'subscribe'):
                # Subscribe to common market topic patterns. Callbacks receive (topic, data)
                self.hub.subscribe('market.ticker', self._hub_event_handler)
                self.hub.subscribe('market.ticker.*', self._hub_event_handler)
                self.hub.subscribe('market.price.*', self._hub_event_handler)
                logger.info('Subscribed to RealDataFeedHub market topics for live ticks')
        except Exception as e:
            logger.debug(f'Failed to subscribe to hub market topics: {e}')

    @staticmethod
    def _normalize_symbol(symbol: Any) -> Optional[str]:
        if not isinstance(symbol, str) or not symbol.strip():
            return None
        normalized = symbol.strip().upper()
        if '/' in normalized:
            return normalized
        for quote in ('USDT', 'USD'):
            if normalized.endswith(quote) and len(normalized) > len(quote):
                return f"{normalized[:-len(quote)]}/USD"
        return f"{normalized}/USD"

    @staticmethod
    def _positive_finite(value: Any) -> Optional[float]:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) and number > 0 else None

    def _complete_input_receipt(self, symbol: str, data: Any) -> Optional[Dict[str, Any]]:
        """Accept only fresh provider observations; never turn local time into source time."""
        if not isinstance(data, dict):
            return None
        source_id = data.get('source_id')
        receipt_id = data.get('receipt_id')
        if (
            data.get('data_status') != 'live'
            or data.get('truth_status') != 'real_observed'
            or data.get('generated_values') is not False
            or not isinstance(source_id, str) or not source_id.strip()
            or not isinstance(receipt_id, str) or not receipt_id.strip()
        ):
            return None
        source_timestamp = self._positive_finite(data.get('source_timestamp'))
        received_at = self._positive_finite(data.get('received_at'))
        price = self._positive_finite(
            data.get('price', data.get('lastPrice', data.get('last', data.get('p')))))
        now = time.time()
        if (
            source_timestamp is None or received_at is None or price is None
            or source_timestamp > now + FUTURE_SKEW_SECONDS
            or received_at > now + FUTURE_SKEW_SECONDS
            or received_at < source_timestamp - FUTURE_SKEW_SECONDS
            or now - source_timestamp > MAX_RECEIPT_AGE_SECONDS
        ):
            return None
        return {
            'symbol': symbol,
            'price': price,
            'source_id': source_id,
            'source_timestamp': source_timestamp,
            'received_at': received_at,
            'receipt_id': receipt_id,
        }

    def _record_price_receipt(self, receipt: Dict[str, Any]) -> None:
        """Mutate the detector only after receipt validation succeeds."""
        symbol = receipt['symbol']
        self.detector.add_price_tick(symbol, receipt['price'])
        limit = getattr(self.detector, 'analysis_window_size', 2048)
        self._source_timestamp_history.setdefault(symbol, deque(maxlen=limit)).append(receipt['source_timestamp'])
        self._receipt_id_history.setdefault(symbol, deque(maxlen=limit)).append(receipt['receipt_id'])
        self._last_receipt[symbol] = dict(receipt)

    def _load_prices_from_cache(self) -> Dict[str, Dict[str, Any]]:
        """Load only complete provider receipts and normalize keys once to BASE/USD."""
        if not self.ws_cache_path.exists():
            return {}
        try:
            payload = json.loads(self.ws_cache_path.read_text(encoding='utf-8'))
        except Exception as e:
            logger.debug(f"Failed to read ws cache: {e}")
            return {}

        normalized: Dict[str, Dict[str, Any]] = {}
        # 1) Cache receipts keyed by BASE or BASE/USD.
        prices = payload.get('prices', {}) or {}
        for base, entry in prices.items():
            symbol = self._normalize_symbol(entry.get('symbol') if isinstance(entry, dict) else base)
            if symbol is None:
                continue
            receipt = self._complete_input_receipt(symbol, entry)
            if receipt is not None:
                normalized[symbol] = receipt

        # 2) Alternative cache uses the same complete receipt contract.
        ticker_cache = payload.get('ticker_cache', {}) or {}
        for pair, entry in ticker_cache.items():
            symbol = self._normalize_symbol(entry.get('symbol') if isinstance(entry, dict) else pair)
            if symbol is None:
                continue
            receipt = self._complete_input_receipt(symbol, entry)
            if receipt is not None:
                normalized[symbol] = receipt

        return normalized

    def _map_base_to_symbol(self, base: str) -> str:
        """Map cache base like 'BTC' to symbol 'BTC/USD'"""
        return f"{base}/USD"

    def _derived_envelope(self, symbol: str, fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        receipt = self._last_receipt.get(symbol)
        if not isinstance(receipt, dict):
            return None
        input_receipt_ids = sorted(set(self._receipt_id_history.get(symbol, ())))
        if not input_receipt_ids:
            return None
        digest = hashlib.sha256(
            f"hnc|{symbol}|{'|'.join(input_receipt_ids)}".encode('utf-8')
        ).hexdigest()[:24]
        return {
            **fields,
            'data_status': 'live',
            'truth_status': 'real_derived',
            'source_id': 'aureon.hnc_live_connector',
            'source_timestamp': receipt['source_timestamp'],
            'received_at': time.time(),
            'receipt_id': f'hnc:{symbol}:{digest}',
            'input_receipt_ids': input_receipt_ids,
            'freshness_status': 'fresh',
            'provider_observation': False,
            'input_provider_observation': True,
            'generated_values': False,
            'operational_eligible': False,
            'actionable': False,
            'accounting_eligible': False,
            'learning_eligible': False,
            'eligible_for_action': False,
            'eligible_for_accounting': False,
            'eligible_for_learning': False,
        }

    def _publish_surge(self, surge: SurgeWindow):
        data = self._derived_envelope(surge.symbol, {
            'symbol': surge.symbol,
            'start_time': surge.start_time,
            'end_time': surge.end_time,
            'peak_time': surge.peak_time,
            'intensity': surge.intensity,
            'primary_harmonic': surge.primary_harmonic,
            'contributing_count': len(surge.contributing_events),
        })
        if data is None:
            return False
        # Publish to real feed hub
        try:
            accepted = self.hub._publish_to_bus('intelligence.surge.hnc', data)
            if accepted is not True:
                return False
            logger.info(f"Published HNC surge: {surge.symbol} intensity={surge.intensity:.2f}")
        except Exception as e:
            logger.warning(f"Failed to publish surge to hub: {e}")
            return False

        # Also emit a Thought for cross-system listeners (scanners, Queen, UI)
        try:
            if self.thought_bus is not None and Thought is not None:
                thought = Thought(source='hnc', topic='intelligence.surge.hnc', payload=data)
                self.thought_bus.publish(thought)
                logger.info(f"ThoughtBus: emitted hnc surge thought for {surge.symbol}")
        except Exception as e:
            logger.debug(f"ThoughtBus emit failed: {e}")

        # Attempt QGITA validation via FTCP -> Lighthouse pipeline
        try:
            if self.qgita is not None:
                buf = self.detector.price_history.get(surge.symbol, None)
                if buf and len(buf) >= 20:
                    import numpy as _np
                    values = _np.array(list(buf))
                    timestamps = list(self._source_timestamp_history.get(surge.symbol, ()))
                    if len(timestamps) != len(values):
                        return True
                    times = _np.array(timestamps)

                    # Stage 1: detect FTCPs
                    ftcps = self.qgita.ftcp_detector.detect_ftcps(times, values)
                    if ftcps:
                        strongest = self.qgita.ftcp_detector.get_strongest_ftcp(ftcps)
                        if strongest:
                            # Stage 2: Lighthouse validation
                            lhe = self.qgita.lighthouse.validate_ftcp(strongest, values)
                            if lhe:
                                # Forward the FULL LighthouseEvent — the payload
                                # used to carry only 4 of its 12 fields, dropping
                                # the structural signature (c_linear/c_nonlinear/
                                # c_phi/g_eff/q_anomaly/regimes) every downstream
                                # volatility consumer needs. Original keys are
                                # unchanged; the additions are purely additive.
                                _ftcp = getattr(lhe, 'ftcp', None)
                                lhe_payload = self._derived_envelope(surge.symbol, {
                                    'symbol': surge.symbol,
                                    'lighthouse_intensity': lhe.lighthouse_intensity,
                                    'confidence': lhe.confidence,
                                    'event_type': lhe.event_type.value,
                                    'timestamp': lhe.timestamp,
                                    'c_linear': lhe.c_linear,
                                    'c_nonlinear': lhe.c_nonlinear,
                                    'c_phi': lhe.c_phi,
                                    'g_eff': lhe.g_eff,
                                    'q_anomaly': lhe.q_anomaly,
                                    'regime_before': lhe.regime_before,
                                    'regime_after': lhe.regime_after,
                                    'ftcp': {
                                        'timestamp': getattr(_ftcp, 'timestamp', None),
                                        'curvature': getattr(_ftcp, 'curvature', None),
                                        'g_eff': getattr(_ftcp, 'g_eff', None),
                                        'phi_match': getattr(_ftcp, 'phi_match', None),
                                    } if _ftcp is not None else None,
                                })
                                if lhe_payload is None:
                                    return True
                                # Publish validated Lighthouse event
                                try:
                                    lighthouse_accepted = self.hub._publish_to_bus('intelligence.lighthouse.event', lhe_payload)
                                    if lighthouse_accepted is not True:
                                        return True
                                    logger.info(f"Published Lighthouse event for {surge.symbol}: L={lhe.lighthouse_intensity:.3f}")
                                except Exception:
                                    logger.debug("Failed to publish Lighthouse event to hub")

                                # ThoughtBus emit
                                if self.thought_bus is not None and Thought is not None:
                                    thought = Thought(source='hnc', topic='intelligence.lighthouse.hnc', payload=lhe_payload)
                                    self.thought_bus.publish(thought)

                                # Optional: ping BotShapeScanner to perform immediate micro scan
                                if self.bot_shape_scanner is not None:
                                    try:
                                        # call a lightweight probe (do not start full WS)
                                        # BotShapeScanner provides analysis methods; call internal scan method if present
                                        if hasattr(self.bot_shape_scanner, '_compute_full_spectrum_fingerprint'):
                                            fingerprint = self.bot_shape_scanner._compute_full_spectrum_fingerprint(surge.symbol)
                                            if fingerprint:
                                                fp_payload = {'symbol': surge.symbol, 'fingerprint': repr(fingerprint), 'ts': time.time()}
                                                self.hub._publish_to_bus('intelligence.botshape.snapshot', fp_payload)
                                    except Exception:
                                        logger.debug('BotShapeScanner probe failed')
        except Exception as e:
            logger.debug(f"QGITA validation error: {e}")
        return True

    def run_once(self):
        prices = self._load_prices_from_cache()
        if not prices:
            logger.debug("No prices in cache")
            return

        for symbol, receipt in prices.items():
            if symbol not in self.symbols:
                continue
            self._record_price_receipt(receipt)

            surge = self.detector.detect_surge(symbol)
            if surge:
                print(f"🔔 HNC Surge detected for {symbol}: intensity={surge.intensity:.2f} (peak: {surge.peak_time})")
                self._publish_surge(surge)

    def run_forever(self):
        print("🌊 HNC Live Connector running. Press Ctrl-C to stop.")
        try:
            while True:
                self.run_once()
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            print("Stopping HNC Live Connector")

    # ----- Hub event handler for direct feed subscription -----
    def _hub_event_handler(self, topic: str, data: dict):
        """Handle events published on RealDataFeedHub and extract price ticks."""
        try:
            if not isinstance(data, dict):
                return

            # Common fields used by various producers
            symbol = data.get('symbol') or data.get('s') or data.get('pair')

            symbol = self._normalize_symbol(symbol)
            if symbol is None:
                return

            if symbol not in self.symbols:
                return

            receipt = self._complete_input_receipt(symbol, data)
            if receipt is None:
                return
            self._record_price_receipt(receipt)
            surge = self.detector.detect_surge(symbol)
            if surge:
                print(f"🔔 HNC Surge detected (live hub): {symbol} intensity={surge.intensity:.2f}")
                self._publish_surge(surge)
        except Exception as e:
            logger.debug(f"Hub event handler error: {e}")


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--symbols', default=os.getenv('HNC_SYMBOLS', 'BTC/USD,ETH/USD,SOL/USD'), help='Comma-separated symbols to watch (format BASE/USD)')
    p.add_argument('--interval', type=float, default=float(os.getenv('HNC_POLL_INTERVAL', '0.5')), help='Poll interval (s)')
    p.add_argument('--ws-cache', default=os.getenv('WS_PRICE_CACHE_PATH', 'ws_cache/ws_prices.json'), help='Path to WS price cache JSON')
    return p.parse_args()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s | %(message)s')
    args = parse_args()
    symbols = [s.strip().upper() for s in args.symbols.split(',')]
    connector = HncLiveConnector(symbols=symbols, ws_cache_path=Path(args.ws_cache), poll_interval=args.interval)
    connector.run_forever()
