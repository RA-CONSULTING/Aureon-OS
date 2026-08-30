"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║     🔶 BINANCE WEBSOCKET CLIENT 🔶                                                   ║
║     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                ║
║                                                                                      ║
║     Real-time market data streaming via Binance WebSocket API                        ║
║                                                                                      ║
║     STREAMS:                                                                         ║
║       • Trades (@trade)     - Real-time trade executions                             ║
║       • Tickers (@ticker)   - 24hr Rolling Window Statistics                         ║
║       • Klines (@kline_1m)  - OHLCV candles                                          ║
║       • Depth (@depth)      - Order book updates                                     ║
║                                                                                      ║
║     Integration with Aureon Ecosystem                                                ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import os
import json
import time
import logging
import threading
import queue
import ssl
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, Set, Union, Tuple
from dataclasses import dataclass, field
from collections import deque

try:
    import websocket
    from websocket import WebSocketApp
except ImportError:
    websocket = None
    WebSocketApp = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 🌊 Harmonic Liquid Aluminium Field - live flowing waveform visualization
try:
    from aureon.harmonic.aureon_harmonic_liquid_aluminium import HarmonicLiquidAluminiumField, FieldSnapshot
    HARMONIC_LIQUID_ALUMINIUM_AVAILABLE = True
except ImportError:
    HARMONIC_LIQUID_ALUMINIUM_AVAILABLE = False
    HarmonicLiquidAluminiumField = None
    FieldSnapshot = None

logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}

# ═══════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════

@dataclass
class WSTrade:
    """Real-time trade data from WebSocket"""
    symbol: str
    price: float
    quantity: float
    timestamp: datetime
    trade_id: int
    is_buyer_maker: bool
    source: str = "binance"
    
@dataclass
class WSTicker:
    """Real-time ticker data from WebSocket"""
    symbol: str
    price_change: float
    price_change_percent: float
    weighted_avg_price: float
    prev_close: float
    last_price: float
    bid_price: float
    ask_price: float
    open_price: float
    high_price: float
    low_price: float
    volume: float
    quote_volume: float
    timestamp: datetime
    source: str = "binance"

@dataclass
class WSBar:
    """Real-time kline/bar data from WebSocket"""
    symbol: str
    interval: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: datetime
    is_closed: bool
    number_of_trades: int
    quote_volume: float
    taker_buy_volume: float
    taker_buy_quote_volume: float
    source: str = "binance"

@dataclass
class WSOrderBook:
    """Real-time order book update from WebSocket"""
    symbol: str
    bids: List[Tuple[float, float]]  # List of (price, qty)
    asks: List[Tuple[float, float]]  # List of (price, qty)
    timestamp: datetime
    first_update_id: int
    final_update_id: int
    source: str = "binance"
    
class BinanceWebSocketClient:
    """
    Binance WebSocket Client for real-time market data.
    
    Provides:
    - Robust connection management with auto-reconnect
    - Thread-safe event queues
    - Unified stream management
    - Integration hooks
    """
    
    def __init__(self, testnet: bool = False):
        if not websocket:
            raise ImportError("websocket-client library not installed. Please install it.")

        self.testnet = testnet
        self.base_url = "wss://stream.binance.com:9443/stream?streams=" if not testnet else "wss://stream.binance.vision/stream?streams="
        
        # State
        self.ws: Optional[Any] = None
        self.wst: Optional[threading.Thread] = None
        self.running = False
        self.connected = False
        self.reconnect_count = 0
        
        # Subscriptions
        self.subscriptions: Set[str] = set()
        self.subscribed_streams: List[str] = []
        
        # Event Queues
        self.trade_queue = queue.Queue(maxsize=10000)
        self.ticker_queue = queue.Queue(maxsize=10000)
        self.bar_queue = queue.Queue(maxsize=1000)
        self.depth_queue = queue.Queue(maxsize=1000)
        self.error_queue = queue.Queue(maxsize=100)
        
        # Latest Data Cache
        self.latest_trades: Dict[str, WSTrade] = {}
        self.latest_tickers: Dict[str, WSTicker] = {}
        self.latest_bars: Dict[str, WSBar] = {}
        self.latest_depths: Dict[str, WSOrderBook] = {}
        
        # Callbacks
        self.on_trade: Optional[Callable[[WSTrade], None]] = None
        self.on_ticker: Optional[Callable[[WSTicker], None]] = None
        self.on_bar: Optional[Callable[[WSBar], None]] = None
        self.on_depth: Optional[Callable[[WSOrderBook], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        # 🌊 Harmonic Liquid Aluminium Field - live flowing waveforms
        self.harmonic_field = None
        if HARMONIC_LIQUID_ALUMINIUM_AVAILABLE and HarmonicLiquidAluminiumField:
            try:
                self.harmonic_field = HarmonicLiquidAluminiumField(stream_interval_ms=25)  # 25ms for ultra-fast flow
                logger.info("🌊 Harmonic Liquid Aluminium Field wired; awaiting explicit WebSocket start")
            except Exception as e:
                logger.warning(f"🌊 Harmonic Field init failed: {e}")
        
        # Lock
        self._lock = threading.Lock()
        
        logger.info(f"🔶 Binance WebSocket Client initialized (Testnet: {testnet})")
        
    def start(self, streams: List[str] = None):
        """Start the WebSocket connection."""
        if self.running:
            logger.warning("WebSocket already running")
            return

        if streams:
            self.subscribed_streams = streams
            for s in streams:
                self.subscriptions.add(s)

        self.running = True
        if self.harmonic_field:
            self.harmonic_field.start_streaming()
        try:
            self._connect()
        except Exception:
            self.running = False
            if self.harmonic_field:
                self.harmonic_field.stop_streaming()
            raise
        
    def stop(self):
        """Stop the WebSocket connection."""
        self.running = False
        if self.ws:
            self.ws.close()
        if self.wst and self.wst.is_alive():
            self.wst.join(timeout=2.0)
        if self.harmonic_field:
            self.harmonic_field.stop_streaming()
        logger.info("🔶 Binance WebSocket Client stopped")
        
    def subscribe(self, streams: List[str]):
        """Subscribe to additional streams dynamically."""
        new_streams = [s for s in streams if s not in self.subscriptions]
        if not new_streams:
            return
            
        for s in new_streams:
            self.subscriptions.add(s)
            
        if self.connected and self.ws:
            payload = {
                "method": "SUBSCRIBE",
                "params": new_streams,
                "id": int(time.time() * 1000)
            }
            try:
                self.ws.send(json.dumps(payload))
                logger.info(f"Subscribed to: {new_streams}")
            except Exception as e:
                logger.error(f"Failed to subscribe: {e}")
                self.error_queue.put(f"Subscribe error: {e}")

    def _connect(self):
        """Establish WebSocket connection."""
        if _env_bool("BINANCE_WS_DISABLE", False):
            logger.warning("Binance WebSocket connection disabled by BINANCE_WS_DISABLE")
            return
        
        # Build stream URL
        # Note: If no streams initially, we connect to base path and subscribe later? 
        # Actually /stream endpoint requires streams param or separate subscribe.
        # connecting to just /ws allows raw stream or subscribing. 
        # Using combined stream endpoint pattern is safest.
        
        stream_str = "/".join(self.subscriptions) if self.subscriptions else ""
        url = f"{self.base_url}{stream_str}"
        
        # If no initial subscriptions, use base endpoint 
        if not self.subscriptions:
             url = self.base_url.replace("/stream?streams=", "/ws")

        logger.info(f"Connecting to {url}...")
        
        self.ws = websocket.WebSocketApp(
            url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        
        self.wst = threading.Thread(target=self.ws.run_forever, kwargs={'ping_interval': 20, 'ping_timeout': 10})
        self.wst.daemon = True
        self.wst.start()

    def _on_open(self, ws):
        """Handle connection open."""
        logger.info("🔶 Binance WebSocket Connected")
        self.connected = True
        self.reconnect_count = 0
        
        # Resubscribe if we reconnected and have pending subscriptions that weren't in URL
        # (Though combined stream URL usually handles it, dynamic subs need re-sending if using /ws endpoint)
        # For /stream endpoint, we are good if we rebuilt URL. 
        # But if we added subs dynamically, we might need to send them again.
        # For simplicity, we just rely on URL params for now or send all subscriptions if using raw /ws
        pass

    def _on_close(self, ws, close_status_code, close_msg):
        """Handle connection close."""
        logger.warning(f"🔶 Binance WebSocket Closed: {close_status_code} - {close_msg}")
        self.connected = False
        # Disable auto-reconnect to prevent spam when server unavailable
        # if self.running:
        #     logger.info("Attempting reconnect in 5s...")
        #     time.sleep(5)
        #     self.reconnect_count += 1
        #     self._connect()

    def _on_error(self, ws, error):
        """Handle errors."""
        logger.error(f"🔶 Binance WebSocket Error: {error}")
        self.error_queue.put(str(error))
        if self.on_error:
            try:
                self.on_error(str(error))
            except Exception:
                pass

    def _on_message(self, ws, message):
        """Handle incoming messages."""
        try:
            data = json.loads(message)
            
            # Handle Combined Stream Format: {"stream": "<name>", "data": <payload>}
            if "stream" in data and "data" in data:
                payload = data["data"]
                # stream_name = data["stream"]
            else:
                payload = data
                
            event_type = payload.get("e")
            
            if event_type == "trade":
                self._process_trade(payload)
            elif event_type == "24hrTicker":
                self._process_ticker(payload)
            elif event_type == "kline":
                self._process_kline(payload)
            elif event_type == "depthUpdate":
                self._process_depth(payload)
            elif "id" in payload:
                # Response to subscribe
                pass
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def _process_trade(self, data: Dict):
        """Process trade event."""
        try:
            trade = WSTrade(
                symbol=data["s"],
                price=float(data["p"]),
                quantity=float(data["q"]),
                timestamp=datetime.fromtimestamp(data["T"] / 1000.0),
                trade_id=data["t"],
                is_buyer_maker=data["m"]
            )
            
            self.latest_trades[trade.symbol] = trade
            
            # Put in queue (drop oldest if full)
            try:
                self.trade_queue.put(trade, block=False)
            except queue.Full:
                try:
                    self.trade_queue.get_nowait()
                    self.trade_queue.put(trade, block=False)
                except:
                    pass
                    
            if self.on_trade:
                self.on_trade(trade)
            
            # 🌊 Flow trade into Harmonic Liquid Aluminium Field
            # Individual trades create ripples in the liquid aluminium
            if self.harmonic_field:
                try:
                    self.harmonic_field.add_or_update_node(
                        exchange='binance',
                        symbol=trade.symbol,
                        current_price=trade.price,
                        entry_price=trade.price,  # Trade price as instant snapshot
                        quantity=trade.quantity,
                        asset_class='crypto'
                    )
                except Exception:
                    pass
                
        except Exception as e:
            logger.error(f"Trade parse error: {e}")

    def _process_ticker(self, data: Dict):
        """Process ticker event."""
        try:
            ticker = WSTicker(
                symbol=data["s"],
                price_change=float(data["p"]),
                price_change_percent=float(data["P"]),
                weighted_avg_price=float(data["w"]),
                prev_close=float(data["x"]),
                last_price=float(data["c"]),
                bid_price=float(data["b"]),
                ask_price=float(data["a"]),
                open_price=float(data["o"]),
                high_price=float(data["h"]),
                low_price=float(data["l"]),
                volume=float(data["v"]),
                quote_volume=float(data["q"]),
                timestamp=datetime.fromtimestamp(data["E"] / 1000.0)
            )
            
            self.latest_tickers[ticker.symbol] = ticker
            
            try:
                self.ticker_queue.put(ticker, block=False)
            except queue.Full:
                try:
                    self.ticker_queue.get_nowait()
                    self.ticker_queue.put(ticker, block=False)
                except:
                    pass

            if self.on_ticker:
                self.on_ticker(ticker)
            
            # 🌊 Flow ticker into Harmonic Liquid Aluminium Field
            # Each ticker becomes a dancing particle of liquid aluminium
            if self.harmonic_field:
                try:
                    self.harmonic_field.add_or_update_node(
                        exchange='binance',
                        symbol=ticker.symbol,
                        current_price=ticker.last_price,
                        entry_price=ticker.open_price,  # Use open as baseline for waveform
                        quantity=ticker.volume / 1000 if ticker.volume > 0 else 1.0,  # Normalize volume
                        asset_class='crypto'
                    )
                except Exception:
                    pass
                
        except Exception as e:
            logger.error(f"Ticker parse error: {e}")

    def _process_kline(self, data: Dict):
        """Process kline event."""
        try:
            k = data["k"]
            bar = WSBar(
                symbol=data["s"],
                interval=k["i"],
                open=float(k["o"]),
                high=float(k["h"]),
                low=float(k["l"]),
                close=float(k["c"]),
                volume=float(k["v"]),
                timestamp=datetime.fromtimestamp(k["t"] / 1000.0),
                is_closed=k["x"],
                number_of_trades=k["n"],
                quote_volume=float(k["q"]),
                taker_buy_volume=float(k["V"]),
                taker_buy_quote_volume=float(k["Q"])
            )
            
            self.latest_bars[f"{bar.symbol}_{bar.interval}"] = bar
            
            try:
                self.bar_queue.put(bar, block=False)
            except queue.Full:
                try:
                    self.bar_queue.get_nowait()
                    self.bar_queue.put(bar, block=False)
                except:
                    pass

            if self.on_bar:
                self.on_bar(bar)
                
        except Exception as e:
            logger.error(f"Bar parse error: {e}")
            
    def _process_depth(self, data: Dict):
        """Process depth update event."""
        try:
            depth = WSOrderBook(
                symbol=data["s"],
                bids=[(float(p), float(q)) for p, q in data["b"]],
                asks=[(float(p), float(q)) for p, q in data["a"]],
                timestamp=datetime.fromtimestamp(data["E"] / 1000.0),
                first_update_id=data["U"],
                final_update_id=data["u"]
            )
            
            self.latest_depths[depth.symbol] = depth
            
            try:
                self.depth_queue.put(depth, block=False)
            except queue.Full:
                try:
                    self.depth_queue.get_nowait()
                    self.depth_queue.put(depth, block=False)
                except:
                    pass

            if self.on_depth:
                self.on_depth(depth)
                
        except Exception as e:
            logger.error(f"Depth parse error: {e}")

# Self-test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Example Usage
    client = BinanceWebSocketClient()
    
    def on_trade(t: WSTrade):
        print(f"TRADE: {t.symbol} {t.price} ({t.quantity})")
        
    client.on_trade = on_trade
    
    # Subscribe to BTCUSDT trade and ticker
    streams = ["btcusdt@trade", "btcusdt@ticker"]
    
    print("Starting stream...")
    client.start(streams)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        client.stop()
