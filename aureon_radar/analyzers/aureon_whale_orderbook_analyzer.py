"""
Whale Orderbook Analyzer

Continuously polls exchange orderbooks (via available clients), detects large walls,
layering and potential spoofing signals (best-effort), and publishes compact
ThoughtBus events for downstream pattern mapping and prediction.

Publishes:
- topic: `whale.orderbook.analyzed` payload: {symbol, detected_at, walls, layering, stats}
- topic: `whale.external.detected` (when strong whale activity detected)
"""
from __future__ import annotations
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import hashlib
import logging
import math
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from aureon.core.aureon_thought_bus import get_thought_bus, Thought

try:
    from aureon.bots.whale_metrics import (
        whale_wall_detected_total,
        whale_layering_score,
        whale_depth_imbalance,
    )
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    whale_wall_detected_total = None
    whale_layering_score = None
    whale_depth_imbalance = None

# ════════════════════════════════════════════════════════════════════════════════
# 🐦 CHIRP BUS INTEGRATION - Emit whale wall detections to Orca!
# ════════════════════════════════════════════════════════════════════════════════
CHIRP_BUS_AVAILABLE = False
get_chirp_bus = None
try:
    from aureon.core.aureon_chirp_bus import get_chirp_bus
    CHIRP_BUS_AVAILABLE = True
except ImportError:
    CHIRP_BUS_AVAILABLE = False

# ════════════════════════════════════════════════════════════════════════════════
# 🌐 GLOBAL MARKET INTEGRATION - Exchange Coverage
# ════════════════════════════════════════════════════════════════════════════════
try:
    from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
    KRAKEN_AVAILABLE = True
except ImportError:
    KRAKEN_AVAILABLE = False
    KrakenClient = None

try:
    from aureon.exchanges.binance_ws_client import BinanceWebSocketClient
    BINANCE_WS_AVAILABLE = True
except ImportError:
    BINANCE_WS_AVAILABLE = False
    BinanceWebSocketClient = None

try:
    from aureon.exchanges.capital_client import CapitalClient
    CAPITAL_AVAILABLE = True
except ImportError:
    CAPITAL_AVAILABLE = False
    CapitalClient = None

logger = logging.getLogger(__name__)


@dataclass
class Wall:
    price: float
    size: float
    notional_usd: float
    side: str  # 'bid' or 'ask'


class WhaleOrderbookAnalyzer:
    """Analyze orderbooks and detect whale/bot signals."""

    def __init__(self, fee_tracker: Optional[Any] = None, poll_symbols: Optional[List[str]] = None,
                 poll_interval: float = 1.0, wall_threshold_usd: float = 100_000.0):
        self.thought_bus = get_thought_bus()
        self.fee_tracker = fee_tracker
        self.poll_interval = float(poll_interval)
        # Bug-hunt 2026-09-07: callers have passed a bare symbol string or a
        # float here (hub probe called the class with (symbol, price)); a
        # float dies in `for s in self.poll_symbols` as 'float' object is not
        # iterable. Normalize to a list of str, fail-closed.
        if poll_symbols is None:
            self.poll_symbols = []
        elif isinstance(poll_symbols, str):
            self.poll_symbols = [poll_symbols]
        elif isinstance(poll_symbols, (list, tuple, set)):
            self.poll_symbols = [str(s) for s in poll_symbols]
        else:
            logger.warning(f"poll_symbols has unexpected type {type(poll_symbols).__name__}; ignoring")
            self.poll_symbols = []
        self.wall_threshold_usd = float(wall_threshold_usd)

        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._recent_analysis: Dict[str, deque] = {}
        
        # 🌐 GLOBAL MARKET CLIENTS
        self.kraken_client: Optional[Any] = None
        self.binance_ws: Optional[Any] = None
        self.capital_client: Optional[Any] = None
        
        # Initialize market connections
        self._init_market_connections()
        
        # 🐦 CHIRP BUS - Emit whale wall detections to Orca
        self.chirp_bus = None
        if CHIRP_BUS_AVAILABLE and get_chirp_bus:
            try:
                self.chirp_bus = get_chirp_bus()
                logger.info("🐦 Whale Orderbook Analyzer → Orca CHIRP BUS connected")
            except Exception as e:
                logger.debug(f"Chirp bus init failed: {e}")

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_loop, name="WhaleOBAnalyzer", daemon=True)
        self._thread.start()
        logger.info("🐋 WhaleOrderbookAnalyzer started (symbols=%d, interval=%.2fs)", len(self.poll_symbols), self.poll_interval)

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("🐋 WhaleOrderbookAnalyzer stopped")

    def _init_market_connections(self):
        """Initialize connections to various exchange clients."""
        if KRAKEN_AVAILABLE and KrakenClient:
            try:
                self.kraken_client = get_kraken_client()
                logger.info("WhaleOrderbookAnalyzer: Kraken client initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize Kraken client: {e}")

        if BINANCE_WS_AVAILABLE and BinanceWebSocketClient:
            try:
                self.binance_ws = BinanceWebSocketClient()
                # Construct stream names like 'btcusdt@depth5'
                streams = [f"{s.lower().replace('/', '')}@depth5" for s in self.poll_symbols]
                self.binance_ws.start(streams=streams)
                logger.info("WhaleOrderbookAnalyzer: Binance WebSocket client started.")
            except Exception as e:
                logger.error(f"Failed to initialize Binance WebSocket client: {e}")

        if CAPITAL_AVAILABLE and CapitalClient:
            try:
                self.capital_client = CapitalClient()
                logger.info("WhaleOrderbookAnalyzer: Capital.com client initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize Capital.com client: {e}")

    def _run_loop(self) -> None:
        while not self._stop.is_set():
            start = time.time()
            for symbol in list(self.poll_symbols):
                try:
                    self.analyze_symbol(symbol)
                except Exception as e:
                    logger.debug("WhaleOBAnalyzer analyze_symbol failed for %s: %s", symbol, e)
            elapsed = time.time() - start
            to_sleep = max(0, self.poll_interval - elapsed)
            time.sleep(to_sleep)

    def analyze_symbol(self, symbol: str) -> Dict[str, Any]:
        """Fetch orderbook and analyze for walls and layering."""
        # Best-effort fetch via provided fee_tracker (Alpaca/bridge), else try ThoughtBus caches
        orderbook = None
        try:
            if self.fee_tracker and hasattr(self.fee_tracker, 'get_orderbook'):
                orderbook = self.fee_tracker.get_orderbook(symbol)
        except Exception:
            orderbook = None

        # Fallback: attempt to query known client modules (AlpacaClient)
        if not orderbook:
            try:
                # lazy import to avoid circular imports
                from aureon.exchanges.alpaca_client import AlpacaClient
                ac = AlpacaClient()
                orderbook = ac.get_crypto_orderbook(symbol) or {}
            except Exception:
                orderbook = None

        bids = self._normalize_side(orderbook.get('bids') or orderbook.get('b') or [])
        asks = self._normalize_side(orderbook.get('asks') or orderbook.get('a') or [])
        exchange = (orderbook or {}).get('exchange') or getattr(self, 'exchange', 'unknown')

        walls: List[Wall] = []
        # Detect walls (single level with notional above threshold)
        for p, s in (bids + asks):
            notional = p * s
            if notional >= self.wall_threshold_usd:
                side = 'bid' if (p, s) in bids else 'ask'
                walls.append(Wall(price=p, size=s, notional_usd=notional, side=side))

        # Layering detection (grid-like placement) - simple heuristic
        layering_score = self._detect_layering(bids if bids else [], asks if asks else [])

        analysis = {
            'symbol': symbol,
            'exchange': exchange,
            'detected_at': time.time(),
            'walls': [w.__dict__ for w in walls],
            'layering_score': layering_score,
            'bids_depth': sum([p*s for p, s in bids[:10]]),
            'asks_depth': sum([p*s for p, s in asks[:10]]),
        }

        # Persist small in-memory history
        self._recent_analysis.setdefault(symbol, deque(maxlen=100)).append(analysis)
        
        # Emit significant walls to Orca for wake riding
        if walls:
            self.emit_whale_wall_to_orca(symbol, walls, exchange)

        # Publish Thought
        th = Thought(source='whale_orderbook_analyzer', topic='whale.orderbook.analyzed', payload=analysis)
        try:
            self.thought_bus.publish(th)
            # Emit metrics
            if METRICS_AVAILABLE and whale_wall_detected_total and whale_layering_score and whale_depth_imbalance:
                try:
                    # Wall detections
                    for wall in walls:
                        whale_wall_detected_total.inc(side=wall.side, symbol=symbol, exchange=exchange)
                    
                    # Layering and depth metrics
                    whale_layering_score.set(layering_score, symbol=symbol, exchange=exchange)
                    
                    # Depth imbalance (-1 to 1, positive = bid heavy)
                    bids_depth = analysis.get('bids_depth', 0)
                    asks_depth = analysis.get('asks_depth', 0)
                    total_depth = bids_depth + asks_depth
                    if total_depth > 0:
                        imbalance = (bids_depth - asks_depth) / total_depth
                        whale_depth_imbalance.set(imbalance, symbol=symbol, exchange=exchange)
                except Exception:
                    logger.debug('Failed to emit whale metrics')
        except Exception:
            logger.debug('Failed to publish whale.orderbook.analyzed')

        # If strong walls found, publish a stronger alert
        if walls and max(w.notional_usd for w in walls) >= self.wall_threshold_usd * 5:
            alert_payload = {'symbol': symbol, 'walls': [w.__dict__ for w in walls], 'layering_score': layering_score}
            ath = Thought(source='whale_orderbook_analyzer', topic='whale.external.detected', payload=alert_payload)
            try:
                self.thought_bus.publish(ath)
            except Exception:
                logger.debug('Failed to publish whale.external.detected')

        return analysis

    @staticmethod
    def _normalize_side(side) -> List[Tuple[float, float]]:
        out: List[Tuple[float, float]] = []
        for lvl in side or []:
            if isinstance(lvl, dict):
                p = float(lvl.get('p', 0) or 0)
                s = float(lvl.get('s', 0) or 0)
            elif isinstance(lvl, (list, tuple)) and len(lvl) >= 2:
                p = float(lvl[0] or 0)
                s = float(lvl[1] or 0)
            else:
                continue
            if p > 0 and s > 0:
                out.append((p, s))
        return out

    @staticmethod
    def _detect_layering(bids: List[Tuple[float, float]], asks: List[Tuple[float, float]]) -> float:
        """Return a layering score 0-1 based on repetitive grid patterns."""
        # simple heuristic: check standard deviation of sizes in top N levels and spacing
        def score_for_side(side):
            if not side:
                return 0.0
            sizes = [s for _, s in side[:12]]
            if len(sizes) < 3:
                return 0.0
            mean = sum(sizes)/len(sizes)
            var = sum((x-mean)**2 for x in sizes)/len(sizes)
            size_stability = 1.0 / (1.0 + math.sqrt(var) / (mean + 1e-9))
            # spacing regularity: check price differences
            prices = [p for p,_ in side[:12]]
            diffs = [abs(prices[i+1]-prices[i]) for i in range(len(prices)-1)]
            if not diffs:
                spacing = 0.0
            else:
                sd = (sum((d - (sum(diffs)/len(diffs)))**2 for d in diffs)/len(diffs))**0.5
                spacing = 1.0 / (1.0 + sd/ (sum(diffs)/len(diffs) + 1e-9))
            return 0.5*(size_stability + spacing)

        bid_score = score_for_side(bids)
        ask_score = score_for_side(asks)
        return float(max(bid_score, ask_score))


# Quick CLI for manual testing
if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('symbol', help='Symbol like BTC/USD')
    ap.add_argument('--interval', type=float, default=1.0)
    args = ap.parse_args()

    analyzer = WhaleOrderbookAnalyzer(poll_symbols=[args.symbol], poll_interval=args.interval)
    analyzer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        analyzer.stop()
