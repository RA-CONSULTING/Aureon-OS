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

import logging
import math
import time
import threading
from typing import Any, Dict, Optional
from collections import deque, defaultdict

from aureon.core.aureon_thought_bus import get_thought_bus, Thought

logger = logging.getLogger(__name__)

MAX_TICKER_AGE_SECONDS = 300.0
FUTURE_SKEW_SECONDS = 5.0


def _timestamp_seconds(value: Any) -> Optional[float]:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) and parsed > 0 else None


def _no_data(reason: str) -> Dict[str, Any]:
    """Return an explicit, numeric-free refusal that cannot become a signal."""
    return {
        "status": "no_data",
        "truth_status": "no_data",
        "generated_values": False,
        "eligible_for_action": False,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
        "reason": reason,
    }


class WhaleExchangeTracker:
    """Track whale activity using exchange APIs directly"""
    
    def __init__(
        self,
        threshold_usd: float = 100_000.0,
        poll_interval_seconds: float = 60.0,
        track_balance_changes: bool = True,
        *,
        exchanges: Optional[Dict[str, Any]] = None,
        thought_bus: Optional[Any] = None,
    ):
        # Construction is inert: callers must explicitly supply/configure all
        # provider clients and then call start().  No provider is touched here.
        self.thought_bus = thought_bus
        self.threshold_usd = float(threshold_usd)
        self.poll_interval = poll_interval_seconds
        self.track_balance_changes = track_balance_changes
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Track previous balances to detect deposits/withdrawals
        self._prev_balances: Dict[str, Dict[str, float]] = defaultdict(dict)  # exchange -> {asset: amount}
        
        # Track large trades
        self._seen_trades: deque = deque(maxlen=1000)
        
        self.exchanges: Dict[str, Any] = dict(exchanges or {})

    def configure(self, *, exchanges: Dict[str, Any], thought_bus: Any) -> None:
        """Provide already-authorized clients and the publication sink explicitly."""
        if self._running:
            raise RuntimeError("stop tracker before reconfiguration")
        self.exchanges = dict(exchanges)
        self.thought_bus = thought_bus

    def configure_default_exchanges(self) -> Dict[str, Any]:
        """Explicitly construct the legacy provider clients when an operator asks."""
        if self._running:
            raise RuntimeError("stop tracker before reconfiguration")
        exchanges: Dict[str, Any] = {}
        try:
            from aureon.exchanges.kraken_client import get_kraken_client
            exchanges["kraken"] = get_kraken_client()
        except Exception as exc:  # provider setup remains opt-in and best effort
            logger.debug("Kraken configuration failed: %s", exc)
        try:
            from aureon.exchanges.binance_client import BinanceClient
            exchanges["binance"] = BinanceClient()
        except Exception as exc:
            logger.debug("Binance configuration failed: %s", exc)
        try:
            from aureon.exchanges.alpaca_client import AlpacaClient
            exchanges["alpaca"] = AlpacaClient()
        except Exception as exc:
            logger.debug("Alpaca configuration failed: %s", exc)
        self.exchanges = exchanges
        return dict(exchanges)

    def start(self) -> bool:
        """Start background polling thread"""
        if not self.exchanges or self.thought_bus is None:
            logger.warning("Tracker requires explicitly configured exchanges and ThoughtBus")
            return False
        
        if self._running:
            logger.debug("WhaleExchangeTracker already running")
            return True
        
        self._running = True
        self._thread = threading.Thread(target=self._polling_loop, daemon=True)
        self._thread.start()
        logger.info(f'WhaleExchangeTracker started; monitoring {len(self.exchanges)} exchanges, threshold=${self.threshold_usd:,.0f}')
        return True
    
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
                    # Estimate USD value (simplified - would need price oracle)
                    valuation = self._estimate_usd_value(asset, abs(delta), client)
                    if valuation["status"] != "real_observed":
                        continue
                    if valuation["amount_usd"] >= self.threshold_usd:
                        direction = 'deposit' if delta > 0 else 'withdrawal'
                        self._emit_whale_event(
                            exchange=exchange_name,
                            asset=asset,
                            amount=abs(delta),
                            direction=direction,
                            event_type='balance_change',
                            receipt=valuation["receipt"],
                        )
            
            # Update previous balances
            self._prev_balances[exchange_name] = current_balances.copy()
            
        except Exception as e:
            logger.debug(f"Balance check error on {exchange_name}: {e}")
    
    def _check_large_trades(self, exchange_name: str, client):
        """Check for large recent trades on the exchange"""
        try:
            # For Kraken: check recent trades
            if exchange_name == 'kraken' and hasattr(client, 'get_recent_trades'):
                pairs = ['XXBTZUSD', 'XETHZUSD']  # BTC/USD, ETH/USD
                for pair in pairs:
                    try:
                        trades = client.get_recent_trades(pair, count=50)
                        for trade in trades:
                            trade_id = f"{exchange_name}:{pair}:{trade.get('time', 0)}"
                            if trade_id in self._seen_trades:
                                continue
                            self._seen_trades.append(trade_id)
                            
                            # A raw trade is not publishable without its own
                            # complete provider receipt.
                            volume = float(trade.get('volume', 0))
                            result = self._emit_whale_event(
                                    exchange=exchange_name,
                                    asset=pair,
                                    amount=volume,
                                    direction='trade',
                                    event_type='large_trade',
                                    receipt=trade,
                                    extra={'side': trade.get('type', 'unknown')},
                                )
                    except Exception as e:
                        logger.debug(f"Trade check error for {pair}: {e}")
            
            # For Binance: check recent trades
            elif exchange_name == 'binance' and hasattr(client, 'get_recent_trades'):
                symbols = ['BTCUSDT', 'ETHUSDT']
                for symbol in symbols:
                    try:
                        trades = client.get_recent_trades(symbol, limit=50)
                        for trade in trades.get('data', []):
                            trade_id = f"{exchange_name}:{symbol}:{trade.get('id', 0)}"
                            if trade_id in self._seen_trades:
                                continue
                            self._seen_trades.append(trade_id)
                            
                            qty = float(trade.get('qty', 0))
                            result = self._emit_whale_event(
                                    exchange=exchange_name,
                                    asset=symbol,
                                    amount=qty,
                                    direction='trade',
                                    event_type='large_trade',
                                    receipt=trade,
                                )
                    except Exception as e:
                        logger.debug(f"Trade check error for {symbol}: {e}")
        
        except Exception as e:
            logger.debug(f"Large trade check error on {exchange_name}: {e}")
    
    def _estimate_usd_value(self, asset: str, amount: float, client) -> Dict[str, Any]:
        """Derive USD value only from a fresh, complete provider ticker receipt."""
        if not math.isfinite(amount) or amount <= 0:
            return _no_data("invalid_amount")
        try:
            pair = {
                "BTC": "XXBTZUSD", "XBT": "XXBTZUSD", "XBTC": "XXBTZUSD",
                "ETH": "XETHZUSD", "XETH": "XETHZUSD",
            }.get(asset.upper())
            if not pair or not hasattr(client, "get_ticker"):
                return _no_data("ticker_unavailable")
            return self._valuation_from_receipt(amount, client.get_ticker(pair))
        except Exception as exc:
            logger.debug("Ticker receipt unavailable for %s: %s", asset, exc)
            return _no_data("ticker_unavailable")

    def _valuation_from_receipt(self, amount: float, receipt: Any) -> Dict[str, Any]:
        if not isinstance(receipt, dict):
            return _no_data("malformed_ticker_receipt")
        source_id = receipt.get("source_id")
        receipt_id = receipt.get("receipt_id")
        source_timestamp = _timestamp_seconds(receipt.get("source_timestamp"))
        received_at = _timestamp_seconds(receipt.get("received_at"))
        now = time.time()
        price_value = receipt.get("price", receipt.get("last"))
        if price_value is None and isinstance(receipt.get("c"), list) and receipt["c"]:
            price_value = receipt["c"][0]
        try:
            price = float(price_value)
        except (TypeError, ValueError):
            return _no_data("malformed_ticker_price")
        if (
            not isinstance(source_id, str) or not source_id.strip()
            or not isinstance(receipt_id, str) or not receipt_id.strip()
            or receipt.get("truth_status") != "real_observed"
            or receipt.get("generated_values") is not False
            or source_timestamp is None or received_at is None
            or not math.isfinite(price) or price <= 0
            or source_timestamp > now + FUTURE_SKEW_SECONDS
            or received_at < source_timestamp - FUTURE_SKEW_SECONDS
            or received_at > now + FUTURE_SKEW_SECONDS
            or now - source_timestamp > MAX_TICKER_AGE_SECONDS
        ):
            return _no_data("invalid_or_stale_ticker_receipt")
        amount_usd = amount * price
        if not math.isfinite(amount_usd) or amount_usd <= 0:
            return _no_data("invalid_derived_amount")
        return {
            "status": "real_observed",
            "amount_usd": amount_usd,
            "price": price,
            "source_id": source_id,
            "source_timestamp": source_timestamp,
            "received_at": received_at,
            "receipt_id": receipt_id,
            "truth_status": "real_observed",
            "generated_values": False,
            "receipt": receipt,
        }
    
    def _emit_whale_event(self, exchange: str, asset: str, amount: float,
                          direction: str, event_type: str, receipt: Any,
                          extra: Optional[Dict] = None) -> Dict[str, Any]:
        """Publish only a receipt-backed derived event; otherwise publish nothing."""
        valuation = self._valuation_from_receipt(amount, receipt)
        if valuation["status"] != "real_observed":
            return valuation
        amount_usd = valuation["amount_usd"]
        if amount_usd < self.threshold_usd or self.thought_bus is None:
            return _no_data("below_threshold_or_unconfigured")
        payload = {
            'exchange': exchange,
            'asset': asset,
            'amount': amount,
            'amount_usd': amount_usd,
            'direction': direction,
            'event_type': event_type,
            **(extra or {}),
            'source_id': valuation['source_id'],
            'source_timestamp': valuation['source_timestamp'],
            'received_at': valuation['received_at'],
            'receipt_id': valuation['receipt_id'],
            'truth_status': 'real_derived',
            'generated_values': False,
            'eligible_for_action': False,
            'eligible_for_accounting': False,
            'eligible_for_learning': False,
        }
        
        th = Thought(source='whale_exchange_tracker', topic='whale.onchain.detected', payload=payload)
        try:
            self.thought_bus.publish(th)
            logger.info(f"🐋 Whale {event_type}: {exchange} {asset} ${amount_usd:,.0f} {direction}")
        except Exception as e:
            logger.debug(f'Failed to publish whale.onchain.detected: {e}')
            return _no_data("publication_failed")
        return {"status": "real_derived", "truth_status": "real_derived", "generated_values": False,
                "eligible_for_action": False, "eligible_for_accounting": False,
                "eligible_for_learning": False, "receipt_id": valuation["receipt_id"]}
    
    def simulate_transfer(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Unobserved transfers are never eligible for the production event bus."""
        return _no_data("synthetic_transfer_rejected")


_default_tracker: Optional[WhaleExchangeTracker] = None


def get_exchange_tracker() -> Optional[WhaleExchangeTracker]:
    """Return an explicitly configured tracker, if an owner has registered one."""
    return _default_tracker
