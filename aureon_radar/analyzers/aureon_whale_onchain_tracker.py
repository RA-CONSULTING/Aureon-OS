"""
Exchange Whale Tracker

Monitors exchange activity for large movements using existing exchange APIs:
- Binance: Recent trades, order history, large orders
- Kraken: Ledger history, trade volume spikes
- Capital.com: Position changes, large flows

Publishes `whale.onchain.detected` for transfers >= threshold.
Note: Uses exchange APIs instead of blockchain providers (no extra API keys needed).
"""
from __future__ import annotations
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import logging
import time
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import deque, defaultdict

from aureon.core.aureon_thought_bus import get_thought_bus, Thought

logger = logging.getLogger(__name__)

# Import exchange clients
try:
    from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
    KRAKEN_AVAILABLE = True
except ImportError:
    KRAKEN_AVAILABLE = False

try:
    from aureon.exchanges.binance_client import BinanceClient, get_binance_client
    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False

try:
    from aureon.exchanges.alpaca_client import AlpacaClient
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False


class WhaleExchangeTracker:
    """Track whale activity using exchange APIs directly"""
    
    def __init__(
        self, 
        threshold_usd: float = 100_000.0,
        poll_interval_seconds: float = 60.0,
        track_balance_changes: bool = True
    ):
        self.thought_bus = get_thought_bus()
        self.threshold_usd = float(threshold_usd)
        self.poll_interval = poll_interval_seconds
        self.track_balance_changes = track_balance_changes
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Track previous balances to detect deposits/withdrawals
        self._prev_balances: Dict[str, Dict[str, float]] = defaultdict(dict)  # exchange -> {asset: amount}
        
        # Track large trades
        self._seen_trades: deque = deque(maxlen=1000)
        
        # Initialize exchange clients
        self.exchanges = {}
        if KRAKEN_AVAILABLE:
            try:
                self.exchanges['kraken'] = get_kraken_client()
                logger.info("✅ Kraken client initialized for whale tracking")
            except Exception as e:
                logger.debug(f"Kraken init failed: {e}")
        
        if BINANCE_AVAILABLE:
            try:
                self.exchanges['binance'] = BinanceClient()
                logger.info("✅ Binance client initialized for whale tracking")
            except Exception as e:
                logger.debug(f"Binance init failed: {e}")
        
        if ALPACA_AVAILABLE:
            try:
                self.exchanges['alpaca'] = AlpacaClient()
                logger.info("✅ Alpaca client initialized for whale tracking")
            except Exception as e:
                logger.debug(f"Alpaca init failed: {e}")
        
        if not self.exchanges:
            logger.warning("⚠️  No exchange clients available for whale tracking")

    def start(self):
        """Start background polling thread"""
        if not self.exchanges:
            logger.warning("No exchanges available; tracker disabled")
            return
        
        if self._running:
            logger.debug("WhaleExchangeTracker already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._polling_loop, daemon=True)
        self._thread.start()
        logger.info(f'WhaleExchangeTracker started; monitoring {len(self.exchanges)} exchanges, threshold=${self.threshold_usd:,.0f}')
    
    def stop(self):
        """Stop polling thread"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("WhaleExchangeTracker stopped")
    
    def _polling_loop(self):
        """Background polling for whale activity"""
        while self._running:
            try:
                for exchange_name, client in self.exchanges.items():
                    if not self._running:
                        break
                    
                    try:
                        # Check for balance changes (deposits/withdrawals)
                        if self.track_balance_changes:
                            self._check_balance_changes(exchange_name, client)
                        
                        # Check for large recent trades
                        self._check_large_trades(exchange_name, client)
                        
                    except Exception as e:
                        logger.debug(f"Error polling {exchange_name}: {e}")
                        continue
                
                time.sleep(self.poll_interval)
                
            except Exception as e:
                logger.error(f"Polling loop error: {e}", exc_info=True)
                time.sleep(10)
    
    def _check_balance_changes(self, exchange_name: str, client):
        """Detect large balance changes (deposits/withdrawals)"""
        try:
            current_balances = client.get_balance()
            prev_balances = self._prev_balances[exchange_name]
            
            for asset, current_amount in current_balances.items():
                if current_amount < 1.0:  # Skip dust
                    continue
                
                prev_amount = prev_balances.get(asset, 0.0)
                delta = current_amount - prev_amount
                
                if abs(delta) > 0:  # Any change
                    # Estimate USD value — None when unpriced; skip (fail-closed)
                    usd_value = self._estimate_usd_value(asset, abs(delta), client)

                    if usd_value is not None and usd_value >= self.threshold_usd:
                        direction = 'deposit' if delta > 0 else 'withdrawal'
                        self._emit_whale_event(
                            exchange=exchange_name,
                            asset=asset,
                            amount=abs(delta),
                            amount_usd=usd_value,
                            direction=direction,
                            event_type='balance_change'
                        )
            
            # Update previous balances
            self._prev_balances[exchange_name] = current_balances.copy()
            
        except Exception as e:
            logger.debug(f"Balance check error on {exchange_name}: {e}")
    
    def _check_large_trades(self, exchange_name: str, client) -> int:
        """Check for large recent trades using real public trade data.

        Exchange client objects do not expose ``get_recent_trades``, so this
        uses the throttled public REST endpoints (no auth, rate-limit friendly)
        via aureon_fusion.api_communion. Zero detections is a valid, honest
        result — alerts are only ever emitted for real trades.
        """
        detected = 0
        try:
            if exchange_name == 'kraken':
                for pair in ('XBTUSD', 'ETHUSD'):
                    detected += self._scan_public_trades(
                        exchange_name, pair,
                        url=f"https://api.kraken.com/0/public/Trades?pair={pair}",
                        parse=lambda t, p=pair: {
                            "price": float(t[0]), "qty": float(t[1]),
                            "side": "buy" if t[3] == "b" else "sell",
                            "ts": float(t[2]),
                        },
                    )
            elif exchange_name == 'binance':
                for symbol in ('BTCUSDT', 'ETHUSDT'):
                    detected += self._scan_public_trades(
                        exchange_name, symbol,
                        url=f"https://api.binance.com/api/v3/trades?symbol={symbol}&limit=100",
                        parse=lambda t, s=symbol: {
                            "price": float(t.get("price", 0)),
                            "qty": float(t.get("qty", 0)),
                            "side": "buy" if t.get("isBuyerMaker") is False else "sell",
                            "ts": float(t.get("time", 0)) / 1000.0,
                            "trade_id": t.get("id"),
                        },
                    )
        except Exception as e:
            logger.debug(f"Large trade check error on {exchange_name}: {e}")
        return detected

    def _scan_public_trades(self, exchange_name: str, asset: str, url: str, parse) -> int:
        """Fetch recent public trades, emit events for those >= threshold_usd."""
        try:
            from analyzers import global_energy_data as ged
        except ImportError:  # standalone: run from inside analyzers/
            import global_energy_data as ged

        body = ged.fetch_json_live(url, ttl_s=ged.BINANCE_TTL_S, timeout=8.0)
        if body is None:
            return 0

        raw_trades: List[Any] = []
        if exchange_name == 'kraken':
            # Kraken wraps payloads as {result: {<pair>: [...]}}
            result = body.get("result", {}) if isinstance(body, dict) else {}
            for v in result.values():
                if isinstance(v, list):
                    raw_trades.extend(v)
                    break
        elif isinstance(body, list):
            raw_trades = body

        detected = 0
        for t in raw_trades:
            try:
                p = parse(t)
            except (TypeError, ValueError, IndexError, KeyError):
                continue
            usd_value = p["price"] * p["qty"]
            if usd_value < self.threshold_usd:
                continue
            dedup = f"{exchange_name}:{asset}:{p.get('trade_id', p['ts'])}"
            if dedup in self._seen_trades:
                continue
            self._seen_trades.append(dedup)
            self._emit_whale_event(
                exchange=exchange_name,
                asset=asset,
                amount=p["qty"],
                amount_usd=usd_value,
                direction=p["side"],
                event_type='large_trade',
                extra={'price': p["price"], 'source': 'public_rest'},
            )
            detected += 1
        return detected

    def run_analysis(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """One throttled whale-analysis pass over real public trade data.

        Returns {"ok", "alerts_emitted", "threshold_usd", "exchanges", "error"}.
        Fail-closed: a venue fetch failure never fabricates an alert; the
        alert list is simply empty for that venue.
        """
        symbols = symbols or ['BTCUSDT', 'ETHUSDT']
        total = 0
        venues = []
        if 'BTCUSDT' in symbols or 'ETHUSDT' in symbols:
            total += self._check_large_trades('binance', self.exchanges.get('binance'))
            venues.append('binance')
        if any(s in ('XBTUSD', 'XXBTZUSD', 'ETHUSD') for s in symbols):
            total += self._check_large_trades('kraken', self.exchanges.get('kraken'))
            venues.append('kraken')

        return {
            "ok": True,
            "ts": time.time(),
            "alerts_emitted": total,
            "threshold_usd": self.threshold_usd,
            "exchanges_scanned": venues,
            "symbols": symbols,
            "error": None,
        }
    
    def _estimate_usd_value(self, asset: str, amount: float, client) -> Optional[float]:
        """Estimate USD value of an asset amount.

        Uses a live ticker price when available. Returns None when no real
        price can be established — the caller MUST NOT emit a whale event for
        an unpriced amount (fail-closed; no fabricated valuation).
        """
        if asset in ['USD', 'USDT', 'USDC', 'ZUSD']:
            return amount

        # Try to get ticker price
        try:
            if hasattr(client, 'get_ticker'):
                # Map asset to trading pair
                pair_map = {
                    'BTC': 'XXBTZUSD',
                    'ETH': 'XETHZUSD',
                    'XBT': 'XXBTZUSD',
                    'XETH': 'XETHZUSD'
                }
                pair = pair_map.get(asset.upper())
                if pair:
                    ticker = client.get_ticker(pair)
                    price = float(ticker.get('c', [0])[0] if isinstance(ticker.get('c'), list) else ticker.get('last', 0))
                    if price > 0:
                        return amount * price
        except Exception:
            pass

        return None
    
    def _emit_whale_event(self, exchange: str, asset: str, amount: float, amount_usd: float, 
                          direction: str, event_type: str, extra: Optional[Dict] = None):
        """Emit whale detection event"""
        payload = {
            'exchange': exchange,
            'asset': asset,
            'amount': amount,
            'amount_usd': amount_usd,
            'direction': direction,
            'event_type': event_type,
            'detected_at': time.time(),
            **(extra or {})
        }
        
        th = Thought(source='whale_exchange_tracker', topic='whale.onchain.detected', payload=payload)
        try:
            self.thought_bus.publish(th)
            logger.info(f"🐋 Whale {event_type}: {exchange} {asset} ${amount_usd:,.0f} {direction}")
        except Exception as e:
            logger.debug(f'Failed to publish whale.onchain.detected: {e}')
    
    def simulate_transfer(self, symbol: str, tx_hash: str, from_addr: str, to_addr: str, amount_usd: float) -> None:
        """Simulate detection of a large transfer (for tests)"""
        payload = {
            'symbol': symbol,
            'tx_hash': tx_hash,
            'from': from_addr,
            'to': to_addr,
            'amount_usd': float(amount_usd),
            'detected_at': time.time(),
            'direction': 'simulated',
            'exchange': 'test',
            'event_type': 'simulated'
        }
        if amount_usd >= self.threshold_usd:
            th = Thought(source='whale_exchange_tracker', topic='whale.onchain.detected', payload=payload)
            try:
                self.thought_bus.publish(th)
            except Exception:
                logger.debug('Failed to publish whale.onchain.detected')
            logger.info('Simulated large transfer detected: %s %s', symbol, amount_usd)


# Default instance — created lazily, NEVER auto-started at import time.
# Background polling only begins on an explicit start() call (opt-in), so
# importing this module never spawns threads or touches exchange APIs.
_default_tracker: Optional[WhaleExchangeTracker] = None


def get_exchange_tracker() -> Optional[WhaleExchangeTracker]:
    """Get (or lazily create) the singleton instance. Polling is NOT started."""
    global _default_tracker
    if _default_tracker is None:
        try:
            _default_tracker = WhaleExchangeTracker()
        except Exception as e:
            logger.debug(f"Failed to initialize WhaleExchangeTracker: {e}")
            _default_tracker = None
    return _default_tracker
