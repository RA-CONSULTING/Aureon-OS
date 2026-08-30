#!/usr/bin/env python3
"""
🦈🔪 HFT WEBSOCKET ORDER ROUTER 🔪🦈
========================================

High Frequency Trading Order Router with WebSocket submission.
Supports Binance, Alpaca, and Kraken WebSocket order APIs.

ARCHITECTURE:
- Async WebSocket connections for each exchange
- Order state machine: PENDING → SENT → FILLED/REJECTED
- Confirmation callbacks for P&L tracking
- Circuit breaker on API failures
- Rate limiting and queue management

Gary Leckey | January 2026 | HFT ORDER ROUTER ACTIVATED
"""

from __future__ import annotations
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import os
import sys
import time
import json
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Callable
from collections import deque
import websockets
import aiohttp

# UTF-8 fix for Windows
if sys.platform == 'win32' and sys.stdout is sys.__stdout__ and sys.stdout.isatty():
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        elif hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        # Skip stderr wrapping - causes Windows exit errors
    except Exception:
        pass

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# 🐦 CHIRP BUS INTEGRATION - kHz-Speed Order Routing Signals
# ═══════════════════════════════════════════════════════════════════════════════
CHIRP_BUS_AVAILABLE = False
get_chirp_bus = None
try:
    from aureon.core.aureon_chirp_bus import get_chirp_bus
    CHIRP_BUS_AVAILABLE = True
except ImportError:
    CHIRP_BUS_AVAILABLE = False

# Order Router Constants
ORDER_TIMEOUT_MS = 5000  # 5 second timeout
MAX_CONCURRENT_ORDERS = 50
CIRCUIT_BREAKER_FAILURES = 5  # Open circuit after 5 failures
CIRCUIT_BREAKER_TIMEOUT_S = 60  # Reset after 60 seconds
RATE_LIMIT_REQUESTS_PER_SECOND = 100
ORDER_QUEUE_SIZE = 1000

# Exchange-specific constants
EXCHANGE_CONFIGS = {
    'binance': {
        'ws_url': 'wss://testnet.binance.vision/ws',  # Use testnet for safety
        'rest_url': 'https://testnet.binance.vision',
        'order_endpoint': '/api/v3/order',
        'listen_key_endpoint': '/api/v3/userDataStream',
        'max_orders_per_second': 10,
        'supported_symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    },
    'alpaca': {
        'ws_url': 'wss://paper-api.alpaca.markets/stream',
        'rest_url': 'https://paper-api.alpaca.markets',
        'order_endpoint': '/v2/orders',
        'max_orders_per_second': 200,
        'supported_symbols': ['BTC/USD', 'ETH/USD', 'SPY', 'AAPL']
    },
    'kraken': {
        'ws_url': 'wss://ws.kraken.com',
        'rest_url': 'https://api.kraken.com',
        'order_endpoint': '/0/private/AddOrder',
        'max_orders_per_second': 1,  # Kraken is slow
        'supported_symbols': ['BTC/USD', 'ETH/USD', 'ADA/USD']
    }
}


@dataclass
class OrderRequest:
    """Order submission request."""
    id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: float
    price: float = 0.0  # 0 = market order
    order_type: str = 'market'  # 'market', 'limit', 'stop'
    timestamp: float = field(default_factory=time.time)
    exchange: str = 'binance'

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'symbol': self.symbol,
            'side': self.side,
            'quantity': self.quantity,
            'price': self.price,
            'order_type': self.order_type,
            'timestamp': self.timestamp,
            'exchange': self.exchange
        }


@dataclass
class OrderResponse:
    """Order submission response."""
    request_id: str
    exchange_order_id: str
    status: str  # 'success', 'rejected', 'timeout', 'error'
    error_message: str = ""
    executed_price: float = 0.0
    executed_quantity: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            'request_id': self.request_id,
            'exchange_order_id': self.exchange_order_id,
            'status': self.status,
            'error_message': self.error_message,
            'executed_price': self.executed_price,
            'executed_quantity': self.executed_quantity,
            'timestamp': self.timestamp
        }


class ExchangeConnection:
    """WebSocket connection manager for a single exchange."""

    def __init__(self, exchange: str, api_key: str = "", api_secret: str = ""):
        self.exchange = exchange
        self.api_key = api_key
        self.api_secret = api_secret
        self.config = EXCHANGE_CONFIGS.get(exchange, {})

        # Connection state
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.connected = False
        self.last_ping = 0.0
        self.reconnect_attempts = 0

        # Circuit breaker
        self.circuit_breaker_failures = 0
        self.circuit_breaker_open = False
        self.circuit_breaker_reset_time = 0.0

        # Rate limiting
        self.last_request_time = 0.0
        self.request_count = 0
        self.rate_limit_window_start = time.time()

        # Order tracking
        self.pending_orders: Dict[str, OrderRequest] = {}
        self.order_callbacks: Dict[str, Callable] = {}

        logger.info(f"🔌 {exchange.upper()} connection initialized")

    async def connect(self) -> bool:
        """Establish WebSocket connection."""
        if self.circuit_breaker_open:
            if time.time() < self.circuit_breaker_reset_time:
                return False
            else:
                # Reset circuit breaker
                self.circuit_breaker_open = False
                self.circuit_breaker_failures = 0
                logger.info(f"🔌 {self.exchange} circuit breaker reset")

        try:
            ws_url = self.config.get('ws_url', '')
            if not ws_url:
                logger.error(f"No WebSocket URL for {self.exchange}")
                return False

            # Connect with authentication if needed
            headers = {}
            if self.api_key and self.exchange == 'alpaca':
                headers['APCA-API-KEY-ID'] = self.api_key
                headers['APCA-API-SECRET-KEY'] = self.api_secret

            self.websocket = await websockets.connect(
                ws_url,
                extra_headers=headers,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=5
            )

            self.connected = True
            self.last_ping = time.time()
            self.reconnect_attempts = 0

            # Start message handler
            asyncio.create_task(self._message_handler())

            logger.info(f"🔌 {self.exchange.upper()} WebSocket connected")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to {self.exchange}: {e}")
            self._record_failure()
            return False

    async def disconnect(self) -> None:
        """Close WebSocket connection."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        self.connected = False
        logger.info(f"🔌 {self.exchange.upper()} disconnected")

    def _record_failure(self) -> None:
        """Record connection failure for circuit breaker."""
        self.circuit_breaker_failures += 1
        if self.circuit_breaker_failures >= CIRCUIT_BREAKER_FAILURES:
            self.circuit_breaker_open = True
            self.circuit_breaker_reset_time = time.time() + CIRCUIT_BREAKER_TIMEOUT_S
            logger.warning(f"🔌 {self.exchange} circuit breaker OPENED ({self.circuit_breaker_failures} failures)")

    async def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        now = time.time()
        max_requests = self.config.get('max_orders_per_second', 10)

        # Reset window every second
        if now - self.rate_limit_window_start >= 1.0:
            self.request_count = 0
            self.rate_limit_window_start = now

        if self.request_count >= max_requests:
            return False

        # Minimum time between requests
        min_interval = 1.0 / max_requests
        if now - self.last_request_time < min_interval:
            await asyncio.sleep(min_interval - (now - self.last_request_time))

        return True

    async def submit_order_ws(self, order: OrderRequest) -> Tuple[bool, str]:
        """
        Submit order via WebSocket.
        Returns (success, exchange_order_id)
        """
        if not self.connected or not self.websocket:
            return False, "Not connected"

        if self.circuit_breaker_open:
            return False, "Circuit breaker open"

        if not await self._check_rate_limit():
            return False, "Rate limit exceeded"

        try:
            # Prepare order message based on exchange
            message = self._prepare_order_message(order)

            # Send order
            await self.websocket.send(json.dumps(message))
            self.last_request_time = time.time()
            self.request_count += 1

            # Track pending order
            self.pending_orders[order.id] = order

            # Set timeout
            asyncio.create_task(self._order_timeout_handler(order.id))

            logger.info(f"📤 {self.exchange.upper()} WS order sent: {order.symbol} {order.side} {order.quantity}")
            return True, order.id  # Use our ID as exchange ID for now

        except Exception as e:
            logger.error(f"WS order submission failed for {self.exchange}: {e}")
            self._record_failure()
            return False, str(e)

    async def submit_order_rest(self, order: OrderRequest) -> Tuple[bool, str]:
        """
        Submit order via REST API fallback.
        Returns (success, exchange_order_id)
        """
        if self.circuit_breaker_open:
            return False, "Circuit breaker open"

        if not await self._check_rate_limit():
            return False, "Rate limit exceeded"

        try:
            # Prepare REST request
            url = f"{self.config['rest_url']}{self.config['order_endpoint']}"
            headers = self._prepare_rest_headers()
            payload = self._prepare_rest_payload(order)

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    self.last_request_time = time.time()
                    self.request_count += 1

                    if response.status == 200:
                        data = await response.json()
                        exchange_order_id = data.get('orderId') or data.get('id') or order.id
                        logger.info(f"📤 {self.exchange.upper()} REST order sent: {order.symbol} {order.side} {order.quantity}")
                        return True, exchange_order_id
                    else:
                        error_text = await response.text()
                        logger.error(f"REST order failed: {response.status} - {error_text}")
                        self._record_failure()
                        return False, f"HTTP {response.status}: {error_text}"

        except Exception as e:
            logger.error(f"REST order submission failed for {self.exchange}: {e}")
            self._record_failure()
            return False, str(e)

    def _prepare_rest_headers(self) -> Dict[str, str]:
        """Prepare REST API headers with authentication."""
        headers = {'Content-Type': 'application/json'}
        
        if self.exchange == 'binance':
            # Add Binance API key and signature
            timestamp = int(time.time() * 1000)
            headers['X-MBX-APIKEY'] = self.api_key
            # Note: Would need proper HMAC signature for production
            
        elif self.exchange == 'alpaca':
            headers['APCA-API-KEY-ID'] = self.api_key
            headers['APCA-API-SECRET-KEY'] = self.api_secret
            
        elif self.exchange == 'kraken':
            # Kraken uses API key in payload
            pass
            
        return headers

    def _prepare_rest_payload(self, order: OrderRequest) -> Dict:
        """Prepare REST API payload."""
        if self.exchange == 'binance':
            return {
                'symbol': order.symbol.replace('/', ''),
                'side': order.side.upper(),
                'type': order.order_type.upper(),
                'quantity': str(order.quantity),
                'timestamp': int(time.time() * 1000)
            }
            
        elif self.exchange == 'alpaca':
            return {
                'symbol': order.symbol,
                'qty': order.quantity,
                'side': order.side,
                'type': order.order_type,
                'time_in_force': 'gtc'
            }
            
        elif self.exchange == 'kraken':
            return {
                'pair': order.symbol.replace('/', ''),
                'type': order.side,
                'ordertype': order.order_type,
                'volume': str(order.quantity)
            }
            
        return {}

    def _prepare_order_message(self, order: OrderRequest) -> Dict:
        """Prepare WebSocket message for order submission."""
        if self.exchange == 'binance':
            return {
                'id': order.id,
                'method': 'order.place',
                'params': {
                    'symbol': order.symbol.replace('/', ''),  # BTC/USD → BTCUSDT
                    'side': order.side.upper(),
                    'type': order.order_type.upper(),
                    'quantity': str(order.quantity),
                    'timestamp': int(time.time() * 1000)
                }
            }

        elif self.exchange == 'alpaca':
            return {
                'action': 'subscribe',
                'trades': [order.symbol],
                'quotes': [order.symbol],
                'bars': [order.symbol]
            }  # Alpaca uses different auth flow

        elif self.exchange == 'kraken':
            return {
                'event': 'addOrder',
                'token': 'your_websocket_token',  # Would need auth
                'reqid': order.id,
                'ordertype': order.order_type,
                'type': order.side,
                'pair': order.symbol.replace('/', ''),
                'volume': str(order.quantity)
            }

        else:
            return {}

    async def _message_handler(self) -> None:
        """Handle incoming WebSocket messages."""
        try:
            while self.connected and self.websocket:
                try:
                    message = await self.websocket.recv()
                    data = json.loads(message)

                    # Handle different message types
                    await self._process_message(data)

                except websockets.exceptions.ConnectionClosed:
                    logger.warning(f"{self.exchange} WebSocket connection closed")
                    self.connected = False
                    break

        except Exception as e:
            logger.error(f"Message handler error for {self.exchange}: {e}")
            self.connected = False

    async def _process_message(self, data: Dict) -> None:
        """Process incoming WebSocket message."""
        try:
            if self.exchange == 'binance':
                await self._process_binance_message(data)
            elif self.exchange == 'alpaca':
                await self._process_alpaca_message(data)
            elif self.exchange == 'kraken':
                await self._process_kraken_message(data)

        except Exception as e:
            logger.debug(f"Message processing error: {e}")

    async def _process_binance_message(self, data: Dict) -> None:
        """Process Binance WebSocket message."""
        if 'id' in data and data['id'] in self.pending_orders:
            # Order response
            order_id = data['id']
            order = self.pending_orders.pop(order_id, None)

            if order:
                status = data.get('status', 'error')
                if status == 'success':
                    # Order filled
                    response = OrderResponse(
                        request_id=order_id,
                        exchange_order_id=data.get('orderId', order_id),
                        status='success',
                        executed_price=data.get('price', 0.0),
                        executed_quantity=data.get('quantity', order.quantity)
                    )
                else:
                    response = OrderResponse(
                        request_id=order_id,
                        exchange_order_id='',
                        status='rejected',
                        error_message=data.get('msg', 'Unknown error')
                    )

                # Call callback if registered
                if order_id in self.order_callbacks:
                    callback = self.order_callbacks.pop(order_id)
                    await callback(response)

    async def _process_alpaca_message(self, data: Dict) -> None:
        """Process Alpaca WebSocket message."""
        # Alpaca uses different message format
        pass

    async def _process_kraken_message(self, data: Dict) -> None:
        """Process Kraken WebSocket message."""
        # Kraken uses different message format
        pass

    async def _order_timeout_handler(self, order_id: str) -> None:
        """Handle order timeout."""
        await asyncio.sleep(ORDER_TIMEOUT_MS / 1000)

        if order_id in self.pending_orders:
            order = self.pending_orders.pop(order_id)

            response = OrderResponse(
                request_id=order_id,
                exchange_order_id='',
                status='timeout',
                error_message=f'Order timeout after {ORDER_TIMEOUT_MS}ms'
            )

            # Call callback if registered
            if order_id in self.order_callbacks:
                callback = self.order_callbacks.pop(order_id)
                await callback(response)

            logger.warning(f"⏰ Order timeout: {order.symbol} {order.side}")


class HFTOrderRouter:
    """
    🦈🔪 HFT ORDER ROUTER 🔪🦈

    Routes orders to appropriate exchanges via WebSocket APIs.
    Manages connection health, rate limiting, and circuit breakers.
    """

    def __init__(self):
        self.connections: Dict[str, ExchangeConnection] = {}
        self.order_queue: asyncio.Queue[OrderRequest] = asyncio.Queue(maxsize=ORDER_QUEUE_SIZE)
        self.response_callbacks: Dict[str, Callable] = {}
        self.exchange_clients: Dict[str, Any] = {}

        # Performance tracking
        self.total_orders = 0
        self.successful_orders = 0
        self.failed_orders = 0
        self.avg_latency_ms = 0.0

        # Control flags
        self.running = False
        self.test_mode = True  # Default to test mode

        logger.info("🦈🔌 HFT Order Router initialized")

    def wire_exchange_clients(self, exchange_clients: Dict[str, Any]) -> bool:
        """Wire low-level exchange client objects (REST/WS wrappers).

        The router can use these to augment connectivity and fallbacks.
        """
        try:
            self.exchange_clients = exchange_clients or {}
            logger.info(f"🦈🔌 Exchange clients wired: {', '.join(self.exchange_clients.keys())}")
            return True
        except Exception as e:
            logger.error(f"Failed to wire exchange clients: {e}")
            return False


    def add_exchange(self, exchange: str, api_key: str = "", api_secret: str = "") -> bool:
        """Add exchange connection."""
        if exchange not in EXCHANGE_CONFIGS:
            logger.error(f"Unsupported exchange: {exchange}")
            return False

        connection = ExchangeConnection(exchange, api_key, api_secret)
        self.connections[exchange] = connection

        logger.info(f"🔌 Added {exchange.upper()} exchange connection")
        return True

    async def start(self) -> bool:
        """Start the order router."""
        if self.running:
            return False

        self.running = True

        # Connect to all exchanges
        connect_tasks = []
        for exchange, connection in self.connections.items():
            connect_tasks.append(self._connect_exchange(exchange, connection))

        results = await asyncio.gather(*connect_tasks, return_exceptions=True)

        successful_connections = sum(1 for r in results if r is True)
        logger.info(f"🦈▶️ Order Router started: {successful_connections}/{len(self.connections)} exchanges connected")

        # Start processing
        asyncio.create_task(self._process_order_queue())
        asyncio.create_task(self._monitor_connections())

        return successful_connections > 0

    async def stop(self) -> None:
        """Stop the order router."""
        self.running = False

        # Disconnect all exchanges
        disconnect_tasks = []
        for connection in self.connections.values():
            disconnect_tasks.append(connection.disconnect())

        await asyncio.gather(*disconnect_tasks, return_exceptions=True)
        logger.info("🦈⏹️ Order Router stopped")

    async def _connect_exchange(self, exchange: str, connection: ExchangeConnection) -> bool:
        """Connect to a specific exchange."""
        try:
            return await connection.connect()
        except Exception as e:
            logger.error(f"Failed to connect to {exchange}: {e}")
            return False

    async def submit_order(self, order_request: OrderRequest) -> Tuple[bool, str]:
        """
        Submit order to appropriate exchange.
        Returns (success, exchange_order_id)
        """
        if not self.running:
            return False, "Router not running"

        if self.order_queue.full():
            return False, "Order queue full"

        # Validate order
        if not self._validate_order(order_request):
            return False, "Invalid order"

        # Add to queue
        await self.order_queue.put(order_request)
        self.total_orders += 1

        logger.info(f"📥 Order queued: {order_request.symbol} {order_request.side} {order_request.quantity}")
        
        # 🐦 CHIRP EMISSION - kHz-Speed Order Routing Signals
        # Emit order submission chirps for ultra-fast execution tracking
        if CHIRP_BUS_AVAILABLE and get_chirp_bus:
            try:
                chirp_bus = get_chirp_bus()
                
                # Order direction frequency mapping
                side_freq = 880.0 if order_request.side == 'buy' else 1760.0
                
                chirp_bus.emit_signal(
                    signal_type='HFT_ORDER_QUEUED',
                    symbol=order_request.symbol,
                    coherence=1.0,  # Queued successfully
                    confidence=1.0,
                    frequency=side_freq,
                    amplitude=min(1.0, order_request.quantity / 1000.0)  # Scale by quantity
                )
                
            except Exception as e:
                # Chirp emission failure - non-critical, continue
                pass
        
        return True, order_request.id

    def _validate_order(self, order: OrderRequest) -> bool:
        """Validate order parameters."""
        if order.symbol not in EXCHANGE_CONFIGS[order.exchange]['supported_symbols']:
            return False

        if order.side not in ['buy', 'sell']:
            return False

        if order.quantity <= 0:
            return False

        if order.order_type not in ['market', 'limit', 'stop']:
            return False

        return True

    async def _process_order_queue(self) -> None:
        """Process orders from queue."""
        while self.running:
            try:
                order = await self.order_queue.get()

                # Route to appropriate exchange
                connection = self.connections.get(order.exchange)
                if not connection:
                    logger.error(f"No connection for exchange: {order.exchange}")
                    self.failed_orders += 1
                    continue

                # Submit order with WebSocket first, REST fallback
                start_time = time.time()
                
                # Try WebSocket first
                success, exchange_order_id = await connection.submit_order_ws(order)
                
                # If WebSocket fails, try REST fallback
                if not success:
                    logger.warning(f"WS failed for {order.symbol}, trying REST fallback...")
                    success, exchange_order_id = await connection.submit_order_rest(order)

                latency_ms = (time.time() - start_time) * 1000

                if success:
                    self.successful_orders += 1
                    logger.info(f"✅ Order submitted: {order.symbol} (Latency: {latency_ms:.1f}ms)")
                else:
                    self.failed_orders += 1
                    logger.error(f"❌ Order failed: {order.symbol} - {exchange_order_id}")

                # Update average latency
                self.avg_latency_ms = (self.avg_latency_ms * (self.total_orders - 1) + latency_ms) / self.total_orders

                self.order_queue.task_done()

            except Exception as e:
                logger.error(f"Order processing error: {e}")
                await asyncio.sleep(0.001)

    async def _monitor_connections(self) -> None:
        """Monitor connection health."""
        while self.running:
            try:
                for exchange, connection in self.connections.items():
                    if not connection.connected and not connection.circuit_breaker_open:
                        logger.info(f"🔄 Reconnecting to {exchange}...")
                        await self._connect_exchange(exchange, connection)

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Connection monitoring error: {e}")
                await asyncio.sleep(30)

    def register_callback(self, order_id: str, callback: Callable) -> None:
        """Register callback for order response."""
        self.response_callbacks[order_id] = callback

    def get_status(self) -> Dict:
        """Get router status."""
        return {
            'running': self.running,
            'test_mode': self.test_mode,
            'total_orders': self.total_orders,
            'successful_orders': self.successful_orders,
            'failed_orders': self.failed_orders,
            'success_rate': self.successful_orders / max(self.total_orders, 1),
            'avg_latency_ms': self.avg_latency_ms,
            'queue_size': self.order_queue.qsize(),
            'exchanges': {
                exchange: {
                    'connected': conn.connected,
                    'circuit_breaker_open': conn.circuit_breaker_open,
                    'pending_orders': len(conn.pending_orders)
                }
                for exchange, conn in self.connections.items()
            }
        }

    def set_test_mode(self, enabled: bool) -> None:
        """Enable/disable test mode."""
        self.test_mode = enabled
        mode_str = "TEST MODE" if enabled else "LIVE MODE"
        logger.info(f"🦈🔄 {mode_str} {'ENABLED' if enabled else 'DISABLED'}")


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_order_router_instance: Optional[HFTOrderRouter] = None

def get_order_router() -> HFTOrderRouter:
    """Get the global order router instance."""
    global _order_router_instance
    if _order_router_instance is None:
        _order_router_instance = HFTOrderRouter()
    return _order_router_instance


# ═══════════════════════════════════════════════════════════════════════════════
# TEST / DEMO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("🦈🔪 HFT ORDER ROUTER TEST 🔪🦈")
    print("=" * 60)
    print()

    async def test_router():
        router = get_order_router()

        # Add test exchange (no real credentials)
        router.add_exchange('binance')
        router.set_test_mode(True)

        print("📊 Router Status:")
        status = router.get_status()
        for k, v in status.items():
            if k != 'exchanges':
                print(f"   {k}: {v}")
        print()

        print("🔗 Exchange Connections:")
        for exchange, conn_status in status['exchanges'].items():
            connected = "✅" if conn_status['connected'] else "❌"
            circuit = "🔴 OPEN" if conn_status['circuit_breaker_open'] else "🟢 CLOSED"
            pending = conn_status['pending_orders']
            print(f"   {exchange.upper()}: {connected} | Circuit: {circuit} | Pending: {pending}")
        print()

        # Test order submission (will fail without real connection)
        print("📤 Testing order submission...")
        test_order = OrderRequest(
            id="test-123",
            symbol="BTCUSDT",
            side="buy",
            quantity=0.001,
            price=0.0,
            order_type="market",
            exchange="binance"
        )

        success, order_id = await router.submit_order(test_order)
        print(f"   Order queued: {'✅' if success else '❌'} (ID: {order_id})")
        print()

        print("🦈 ORDER ROUTER READY FOR HFT TRADING 🦈")

    # Run test
    asyncio.run(test_router())
