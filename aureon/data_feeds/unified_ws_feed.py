#!/usr/bin/env python3
"""
🌐⚡ UNIFIED WEBSOCKET FEED MANAGER ⚡🌐
═══════════════════════════════════════════════════════════════

Production-grade WebSocket feed aggregator for multi-exchange data:

📡 EXCHANGE STREAMS:
├─ 🟡 Binance (Spot WS)      wss://stream.binance.com:9443/ws
├─ 🐙 Kraken (WS v2)         wss://ws.kraken.com
├─ 🏛️ Capital.com (WS)       wss://api-streaming.capital.com
├─ 🪙 Coinbase (Advanced)    wss://advanced-trade-ws.coinbase.com
└─ 🦎 CoinGecko (REST poll)  api.coingecko.com/v3 (for reference prices)

🔗 OUTPUTS:
├─ Normalized ticker stream (symbol, bid, ask, last, exchange, ts)
├─ ThoughtBus events for downstream consumers
└─ GlobalFinancialFeed enrichment

Gary Leckey | January 2026
"All data flows through the Queen"
"""

from __future__ import annotations
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import os
import sys
import json
import asyncio
import logging
import math
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict

# Windows UTF-8 fix
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# HFT HARMONIC MYCELIUM INTEGRATION
# ═══════════════════════════════════════════════════════════════

# Lazy load HFT engine for graceful degradation
try:
    from aureon.harmonic.aureon_hft_harmonic_mycelium import get_hft_engine
    HFT_ENGINE_AVAILABLE = True
except ImportError:
    get_hft_engine = None
    HFT_ENGINE_AVAILABLE = False

# 🌊 Harmonic Liquid Aluminium Field - market visualization as dancing waveforms
try:
    from aureon.harmonic.aureon_harmonic_liquid_aluminium import HarmonicLiquidAluminiumField, FieldSnapshot
    HARMONIC_LIQUID_ALUMINIUM_AVAILABLE = True
except ImportError:
    HARMONIC_LIQUID_ALUMINIUM_AVAILABLE = False
    HarmonicLiquidAluminiumField = None
    FieldSnapshot = None

# ═══════════════════════════════════════════════════════════════
# WEBSOCKET ENDPOINTS
# ═══════════════════════════════════════════════════════════════

WS_ENDPOINTS = {
    'binance': 'wss://stream.binance.com:9443/ws',
    'kraken': 'wss://ws.kraken.com',
    'capital': 'wss://api-streaming.capital.com/connect',
    'coinbase': 'wss://advanced-trade-ws.coinbase.com',
}

COINGECKO_API = 'https://api.coingecko.com/api/v3'

# ═══════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════

@dataclass
class NormalizedTick:
    """Unified tick format across all exchanges."""
    symbol: str           # Normalized symbol (e.g., BTC/USD)
    exchange: str         # Source exchange
    bid: float
    ask: float
    last: float
    volume_24h: Optional[float] = None
    change_24h: Optional[float] = None
    source_timestamp: Optional[float] = None
    received_at: float = field(default_factory=time.time)
    raw_symbol: str = ""  # Original exchange symbol

    def __post_init__(self) -> None:
        values = {"bid": self.bid, "ask": self.ask, "last": self.last}
        for name, value in values.items():
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be a finite positive provider value")
        if self.ask < self.bid:
            raise ValueError("ask cannot be below bid")
        if self.volume_24h is not None:
            if not math.isfinite(self.volume_24h) or self.volume_24h < 0:
                raise ValueError("volume_24h must be a finite non-negative provider value")
        if self.change_24h is not None and not math.isfinite(self.change_24h):
            raise ValueError("change_24h must be finite when supplied")
        if self.source_timestamp is not None:
            if not math.isfinite(self.source_timestamp) or self.source_timestamp <= 0:
                raise ValueError("source_timestamp must be a positive provider timestamp")
        if not math.isfinite(self.received_at) or self.received_at <= 0:
            raise ValueError("received_at must be a positive local receipt timestamp")

    @property
    def timestamp(self) -> Optional[float]:
        """Compatibility alias that never substitutes receipt time for source time."""
        return self.source_timestamp

    def is_source_fresh(self, max_age_seconds: float = 60.0, *, now: Optional[float] = None) -> bool:
        """Return true only when a provider timestamp proves the tick is fresh."""
        if self.source_timestamp is None:
            return False
        checked_at = time.time() if now is None else now
        age = checked_at - self.source_timestamp
        return -5.0 <= age <= max_age_seconds
    
    @property
    def spread(self) -> float:
        if self.bid > 0:
            return (self.ask - self.bid) / self.bid
        return 0.0
    
    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2
    
    def to_dict(self) -> Dict:
        payload = asdict(self)
        payload["timestamp"] = self.source_timestamp
        payload["generated_values"] = False
        return payload


def _finite_float(value: Any, *, positive: bool = False, non_negative: bool = False) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    if positive and number <= 0:
        return None
    if non_negative and number < 0:
        return None
    return number


def _source_timestamp(value: Any) -> Optional[float]:
    """Parse provider time without ever substituting the local receipt clock."""
    if value is None or value == "":
        return None
    numeric = _finite_float(value, positive=True)
    if numeric is not None:
        if numeric >= 1e18:  # nanoseconds
            numeric /= 1e9
        elif numeric >= 1e15:  # microseconds
            numeric /= 1e6
        elif numeric >= 1e11:  # milliseconds
            numeric /= 1e3
        return numeric
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except (TypeError, ValueError, OverflowError):
        return None


def _build_tick(
    *,
    symbol: Any,
    exchange: str,
    bid: Any,
    ask: Any,
    last: Any,
    volume_24h: Any = None,
    change_24h: Any = None,
    source_timestamp: Any = None,
    received_at: Optional[float] = None,
) -> Optional[NormalizedTick]:
    raw_symbol = str(symbol or "").strip()
    parsed_bid = _finite_float(bid, positive=True)
    parsed_ask = _finite_float(ask, positive=True)
    parsed_last = _finite_float(last, positive=True)
    if not raw_symbol or parsed_bid is None or parsed_ask is None or parsed_last is None:
        return None
    parsed_volume = _finite_float(volume_24h, non_negative=True)
    parsed_change = _finite_float(change_24h)
    receipt_time = time.time() if received_at is None else received_at
    try:
        return NormalizedTick(
            symbol=normalize_symbol(raw_symbol, exchange),
            exchange=exchange,
            bid=parsed_bid,
            ask=parsed_ask,
            last=parsed_last,
            volume_24h=parsed_volume,
            change_24h=parsed_change,
            source_timestamp=_source_timestamp(source_timestamp),
            received_at=receipt_time,
            raw_symbol=raw_symbol,
        )
    except ValueError:
        return None


def parse_binance_tick(data: Dict[str, Any], *, received_at: Optional[float] = None) -> Optional[NormalizedTick]:
    return _build_tick(
        symbol=data.get("s"), exchange="binance", bid=data.get("b"), ask=data.get("a"),
        last=data.get("c"), volume_24h=data.get("v"), change_24h=data.get("P"),
        source_timestamp=data.get("E"), received_at=received_at,
    )


def _array_value(value: Any, index: int = 0) -> Any:
    return value[index] if isinstance(value, (list, tuple)) and len(value) > index else None


def parse_kraken_tick(
    ticker: Dict[str, Any], raw_symbol: Any, *, received_at: Optional[float] = None
) -> Optional[NormalizedTick]:
    return _build_tick(
        symbol=raw_symbol, exchange="kraken", bid=_array_value(ticker.get("b")),
        ask=_array_value(ticker.get("a")), last=_array_value(ticker.get("c")),
        volume_24h=_array_value(ticker.get("v"), 1),
        source_timestamp=ticker.get("timestamp"), received_at=received_at,
    )


def parse_coinbase_tick(data: Dict[str, Any], *, received_at: Optional[float] = None) -> Optional[NormalizedTick]:
    return _build_tick(
        symbol=data.get("product_id"), exchange="coinbase", bid=data.get("best_bid"),
        ask=data.get("best_ask"), last=data.get("price"), volume_24h=data.get("volume_24h"),
        source_timestamp=data.get("timestamp") or data.get("time"), received_at=received_at,
    )


def parse_capital_tick(data: Dict[str, Any], *, received_at: Optional[float] = None) -> Optional[NormalizedTick]:
    return _build_tick(
        symbol=data.get("epic"), exchange="capital", bid=data.get("bid"), ask=data.get("offer"),
        last=data.get("mid"), volume_24h=data.get("volume"),
        source_timestamp=data.get("timestamp"), received_at=received_at,
    )


def parse_coingecko_tick(
    coin_id: str, info: Dict[str, Any], *, received_at: Optional[float] = None
) -> Optional[NormalizedTick]:
    """Normalize only observed CoinGecko quotes; the simple-price endpoint has no bid/ask."""
    symbol = {"bitcoin": "BTC", "ethereum": "ETH"}.get(coin_id, coin_id.upper())
    return _build_tick(
        symbol=f"{symbol}/USD", exchange="coingecko", bid=info.get("bid"), ask=info.get("ask"),
        last=info.get("usd"), change_24h=info.get("usd_24h_change"),
        source_timestamp=info.get("last_updated_at"), received_at=received_at,
    )


@dataclass
class ExchangeStatus:
    """Health status for an exchange connection."""
    exchange: str
    connected: bool = False
    last_message: float = 0.0
    message_count: int = 0
    error_count: int = 0
    subscribed_symbols: Set[str] = field(default_factory=set)
    
    @property
    def is_healthy(self) -> bool:
        # Healthy if connected and received message in last 60s
        return self.connected and (time.time() - self.last_message) < 60


# ═══════════════════════════════════════════════════════════════
# SYMBOL NORMALIZATION
# ═══════════════════════════════════════════════════════════════

def normalize_symbol(raw: str, exchange: str) -> str:
    """Convert exchange-specific symbol to unified format (BASE/QUOTE)."""
    raw = raw.upper().strip()
    
    if exchange == 'binance':
        # BTCUSDT -> BTC/USDT
        for quote in ['USDT', 'USDC', 'BUSD', 'USD', 'BTC', 'ETH', 'EUR', 'GBP']:
            if raw.endswith(quote) and len(raw) > len(quote):
                base = raw[:-len(quote)]
                return f"{base}/{quote}"
        return raw
    
    elif exchange == 'kraken':
        # XXBTZUSD -> BTC/USD, XETHZUSD -> ETH/USD
        raw = raw.replace('XXBT', 'BTC').replace('XETH', 'ETH').replace('ZUSD', 'USD')
        raw = raw.replace('ZEUR', 'EUR').replace('ZGBP', 'GBP').replace('ZJPY', 'JPY')
        if '/' in raw:
            return raw
        for quote in ['USD', 'USDT', 'USDC', 'EUR', 'GBP', 'BTC', 'ETH']:
            if raw.endswith(quote) and len(raw) > len(quote):
                base = raw[:-len(quote)]
                return f"{base}/{quote}"
        return raw
    
    elif exchange == 'coinbase':
        # BTC-USD -> BTC/USD
        if '-' in raw:
            return raw.replace('-', '/')
        return raw
    
    elif exchange == 'capital':
        # Already in BTCUSD format typically
        for quote in ['USD', 'EUR', 'GBP']:
            if raw.endswith(quote) and len(raw) > len(quote):
                base = raw[:-len(quote)]
                return f"{base}/{quote}"
        return raw
    
    return raw


def denormalize_symbol(symbol: str, exchange: str) -> str:
    """Convert unified symbol to exchange-specific format."""
    symbol = symbol.upper().replace('/', '')
    
    if exchange == 'binance':
        return symbol  # BTCUSDT
    elif exchange == 'kraken':
        # BTC/USD -> XXBTZUSD (Kraken uses X prefix for crypto, Z for fiat)
        return symbol.replace('BTC', 'XBT')  # Kraken uses XBT
    elif exchange == 'coinbase':
        # BTC/USD -> BTC-USD
        return symbol[:3] + '-' + symbol[3:] if len(symbol) >= 6 else symbol
    elif exchange == 'capital':
        return symbol
    
    return symbol


# ═══════════════════════════════════════════════════════════════
# WEBSOCKET HANDLERS
# ═══════════════════════════════════════════════════════════════

class UnifiedWSFeed:
    """
    Unified WebSocket feed manager for multi-exchange data.
    
    Connects to Binance, Kraken, Capital.com, Coinbase WebSockets
    and normalizes all ticks into a unified format.
    """
    
    def __init__(
        self,
        enable_binance: bool = True,
        enable_kraken: bool = True,
        enable_capital: bool = True,
        enable_coinbase: bool = True,
        enable_coingecko: bool = True,
    ):
        self.enable = {
            'binance': enable_binance,
            'kraken': enable_kraken,
            'capital': enable_capital,
            'coinbase': enable_coinbase,
            'coingecko': enable_coingecko,
        }
        
        # State
        self.status: Dict[str, ExchangeStatus] = {
            ex: ExchangeStatus(exchange=ex) for ex in WS_ENDPOINTS
        }
        self.ticks: Dict[str, NormalizedTick] = {}  # symbol -> latest tick
        self.callbacks: List[Callable[[NormalizedTick], None]] = []
        self._running = False
        self._tasks: List[asyncio.Task] = []
        
        # ThoughtBus integration
        self.thought_bus = None
        try:
            from aureon.core.aureon_thought_bus import ThoughtBus
            self.thought_bus = ThoughtBus(persist_path="ws_feed_thoughts.jsonl")
        except ImportError:
            pass
        
        # 🦈🔪 HFT Harmonic Mycelium Integration
        self.hft_engine = None
        if HFT_ENGINE_AVAILABLE and get_hft_engine is not None:
            try:
                self.hft_engine = get_hft_engine()
                logger.info("🦈🔪 HFT Harmonic Mycelium Engine WIRED to WebSocket Feed")
            except Exception as e:
                logger.warning(f"🦈🔪 HFT Engine initialization failed: {e}")
        
        # 🌊 Harmonic Liquid Aluminium Field - live flowing waveform visualization
        self.harmonic_field = None
        if HARMONIC_LIQUID_ALUMINIUM_AVAILABLE and HarmonicLiquidAluminiumField:
            try:
                self.harmonic_field = HarmonicLiquidAluminiumField(stream_interval_ms=50)  # 50ms for live flow
                logger.info("🌊 Harmonic Liquid Aluminium Field wired; awaiting explicit feed start")
            except Exception as e:
                logger.warning(f"🌊 Harmonic Field initialization failed: {e}")
        
        logger.info("🌐⚡ UnifiedWSFeed initialized")
        for ex, enabled in self.enable.items():
            logger.info(f"   {ex}: {'✅' if enabled else '❌'}")
    
    def on_tick(self, callback: Callable[[NormalizedTick], None]):
        """Register a callback for new ticks."""
        self.callbacks.append(callback)
    
    def _emit(self, tick: NormalizedTick):
        """Emit tick to all callbacks, ThoughtBus, HFT engine, and Harmonic Field."""
        self.ticks[tick.symbol] = tick

        harmonic_ready = tick.is_source_fresh() and tick.volume_24h is not None

        # 🦈🔪 Inject tick into HFT engine for sub-10ms processing
        if harmonic_ready and self.hft_engine and hasattr(self.hft_engine, 'inject_tick'):
            try:
                self.hft_engine.inject_tick(tick)
            except Exception as e:
                logger.debug(f"🦈🔪 HFT tick injection error: {e}")
        
        # 🌊 Flow tick into Harmonic Liquid Aluminium Field
        # Each tick becomes a dancing waveform on the frequency spectrum
        if harmonic_ready and self.harmonic_field:
            try:
                # Feed the harmonic field with live data
                # Volume influences the quantity/energy of the node
                self.harmonic_field.add_or_update_node(
                    exchange=tick.exchange,
                    symbol=tick.symbol,
                    current_price=tick.last,
                    entry_price=tick.last,  # No position, use current as baseline
                    quantity=tick.volume_24h / 1000,
                    asset_class='crypto'
                )
            except Exception as e:
                logger.debug(f"🌊 Harmonic field tick error: {e}")
        
        for cb in self.callbacks:
            try:
                cb(tick)
            except Exception as e:
                logger.warning(f"Tick callback error: {e}")
        
        if self.thought_bus:
            try:
                from aureon.core.aureon_thought_bus import Thought
                self.thought_bus.publish(Thought(
                    source=f"ws_{tick.exchange}",
                    topic="tick",
                    payload=tick.to_dict()
                ))
            except Exception:
                pass
    
    # ─────────────────────────────────────────────────────────────
    # BINANCE HANDLER
    # ─────────────────────────────────────────────────────────────
    
    async def _binance_stream(self, symbols: List[str]):
        """Connect to Binance combined stream for multiple symbols."""
        try:
            import websockets
        except ImportError:
            logger.error("❌ websockets package not installed: pip install websockets")
            return
        
        status = self.status['binance']
        
        # Build combined stream URL
        streams = [f"{s.lower()}@ticker" for s in symbols]
        url = f"{WS_ENDPOINTS['binance']}/{'/'.join(streams[:20])}"  # Max 20 per connection
        
        while self._running:
            try:
                async with websockets.connect(url, ping_interval=20) as ws:
                    status.connected = True
                    status.subscribed_symbols = set(symbols)
                    logger.info(f"🟡 Binance WS connected ({len(symbols)} symbols)")
                    
                    async for msg in ws:
                        if not self._running:
                            break
                        
                        try:
                            data = json.loads(msg)
                            if 'stream' in data:
                                data = data.get('data', data)
                            
                            received_at = time.time()
                            tick = parse_binance_tick(data, received_at=received_at)
                            if tick is None:
                                status.error_count += 1
                                logger.debug("Binance ticker omitted: missing or invalid symbol/bid/ask/last")
                                continue
                            status.last_message = received_at
                            status.message_count += 1
                            self._emit(tick)
                        except Exception as e:
                            status.error_count += 1
                            logger.debug(f"Binance parse error: {e}")
            
            except Exception as e:
                status.connected = False
                status.error_count += 1
                logger.warning(f"🟡 Binance WS error: {e}, reconnecting in 5s...")
                await asyncio.sleep(5)
    
    # ─────────────────────────────────────────────────────────────
    # KRAKEN HANDLER
    # ─────────────────────────────────────────────────────────────
    
    async def _kraken_stream(self, symbols: List[str]):
        """Connect to Kraken WebSocket v2."""
        try:
            import websockets
        except ImportError:
            return
        
        status = self.status['kraken']
        url = WS_ENDPOINTS['kraken']
        
        while self._running:
            try:
                async with websockets.connect(url) as ws:
                    status.connected = True
                    
                    # Subscribe to ticker
                    sub_msg = {
                        "event": "subscribe",
                        "pair": [denormalize_symbol(s, 'kraken') for s in symbols[:50]],
                        "subscription": {"name": "ticker"}
                    }
                    await ws.send(json.dumps(sub_msg))
                    status.subscribed_symbols = set(symbols)
                    logger.info(f"🐙 Kraken WS connected ({len(symbols)} symbols)")
                    
                    async for msg in ws:
                        if not self._running:
                            break
                        
                        try:
                            data = json.loads(msg)
                            
                            # Skip system messages
                            if isinstance(data, dict):
                                continue
                            
                            # Ticker format: [channelID, {...}, "ticker", "XBT/USD"]
                            if isinstance(data, list) and len(data) >= 4 and data[2] == "ticker":
                                ticker = data[1]
                                raw_symbol = data[3]
                                received_at = time.time()
                                tick = parse_kraken_tick(ticker, raw_symbol, received_at=received_at)
                                if tick is None:
                                    status.error_count += 1
                                    logger.debug("Kraken ticker omitted: missing or invalid symbol/bid/ask/last")
                                    continue
                                status.last_message = received_at
                                status.message_count += 1
                                self._emit(tick)
                        except Exception as e:
                            status.error_count += 1
                            logger.debug(f"Kraken parse error: {e}")
            
            except Exception as e:
                status.connected = False
                status.error_count += 1
                logger.warning(f"🐙 Kraken WS error: {e}, reconnecting in 5s...")
                await asyncio.sleep(5)
    
    # ─────────────────────────────────────────────────────────────
    # COINBASE HANDLER
    # ─────────────────────────────────────────────────────────────
    
    async def _coinbase_stream(self, symbols: List[str]):
        """Connect to Coinbase Advanced Trade WebSocket."""
        try:
            import websockets
        except ImportError:
            return
        
        status = self.status['coinbase']
        url = WS_ENDPOINTS['coinbase']
        
        while self._running:
            try:
                async with websockets.connect(url) as ws:
                    status.connected = True
                    
                    # Subscribe message
                    product_ids = [denormalize_symbol(s, 'coinbase') for s in symbols[:50]]
                    sub_msg = {
                        "type": "subscribe",
                        "product_ids": product_ids,
                        "channel": "ticker"
                    }
                    await ws.send(json.dumps(sub_msg))
                    status.subscribed_symbols = set(symbols)
                    logger.info(f"🪙 Coinbase WS connected ({len(symbols)} symbols)")
                    
                    async for msg in ws:
                        if not self._running:
                            break
                        
                        try:
                            data = json.loads(msg)
                            
                            if data.get('type') == 'ticker':
                                received_at = time.time()
                                tick = parse_coinbase_tick(data, received_at=received_at)
                                if tick is None:
                                    status.error_count += 1
                                    logger.debug("Coinbase ticker omitted: missing or invalid symbol/bid/ask/last")
                                    continue
                                status.last_message = received_at
                                status.message_count += 1
                                self._emit(tick)
                        except Exception as e:
                            status.error_count += 1
                            logger.debug(f"Coinbase parse error: {e}")
            
            except Exception as e:
                status.connected = False
                status.error_count += 1
                logger.warning(f"🪙 Coinbase WS error: {e}, reconnecting in 5s...")
                await asyncio.sleep(5)
    
    # ─────────────────────────────────────────────────────────────
    # CAPITAL.COM HANDLER
    # ─────────────────────────────────────────────────────────────
    
    async def _capital_stream(self, symbols: List[str]):
        """Connect to Capital.com WebSocket (requires API key)."""
        api_key = os.getenv("CAPITAL_API_KEY", "")
        if not api_key:
            logger.warning("🏛️ Capital.com: No API key, skipping WS")
            return
        
        try:
            import websockets
        except ImportError:
            return
        
        status = self.status['capital']
        url = WS_ENDPOINTS['capital']
        
        while self._running:
            try:
                async with websockets.connect(url) as ws:
                    # Authenticate
                    auth_msg = {"action": "auth", "apiKey": api_key}
                    await ws.send(json.dumps(auth_msg))
                    
                    # Wait for auth response
                    auth_resp = await ws.recv()
                    auth_data = json.loads(auth_resp)
                    if auth_data.get("status") != "ok":
                        logger.error(f"🏛️ Capital.com auth failed: {auth_data}")
                        await asyncio.sleep(30)
                        continue
                    
                    status.connected = True
                    
                    # Subscribe to prices
                    sub_msg = {
                        "action": "subscribe",
                        "channel": "prices",
                        "epics": [denormalize_symbol(s, 'capital') for s in symbols[:20]]
                    }
                    await ws.send(json.dumps(sub_msg))
                    status.subscribed_symbols = set(symbols)
                    logger.info(f"🏛️ Capital.com WS connected ({len(symbols)} symbols)")
                    
                    async for msg in ws:
                        if not self._running:
                            break
                        
                        try:
                            data = json.loads(msg)
                            
                            if data.get("type") == "price":
                                received_at = time.time()
                                tick = parse_capital_tick(data, received_at=received_at)
                                if tick is None:
                                    status.error_count += 1
                                    logger.debug("Capital ticker omitted: missing or invalid symbol/bid/ask/last")
                                    continue
                                status.last_message = received_at
                                status.message_count += 1
                                self._emit(tick)
                        except Exception as e:
                            status.error_count += 1
                            logger.debug(f"Capital parse error: {e}")
            
            except Exception as e:
                status.connected = False
                status.error_count += 1
                logger.warning(f"🏛️ Capital.com WS error: {e}, reconnecting in 10s...")
                await asyncio.sleep(10)
    
    # ─────────────────────────────────────────────────────────────
    # COINGECKO POLLER (REST fallback)
    # ─────────────────────────────────────────────────────────────
    
    async def _coingecko_poll(self, coin_ids: List[str], interval: int = 30):
        """Poll CoinGecko for reference prices (rate-limited)."""
        import urllib.request
        
        api_key = os.getenv("COINGECKO_API_KEY", "")
        headers = {}
        if api_key:
            headers["x-cg-demo-api-key"] = api_key
        
        while self._running:
            try:
                ids = ",".join(coin_ids[:50])
                url = (
                    f"{COINGECKO_API}/simple/price?ids={ids}"
                    "&vs_currencies=usd&include_24hr_change=true&include_last_updated_at=true"
                )
                
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
                
                received_at = time.time()
                for coin_id, info in data.items():
                    tick = parse_coingecko_tick(coin_id, info, received_at=received_at)
                    if tick is not None:
                        self._emit(tick)
                
                logger.debug(f"🦎 CoinGecko polled {len(data)} coins")
            
            except Exception as e:
                logger.warning(f"🦎 CoinGecko poll error: {e}")
            
            await asyncio.sleep(interval)
    
    # ─────────────────────────────────────────────────────────────
    # START/STOP
    # ─────────────────────────────────────────────────────────────
    
    async def start(
        self,
        symbols: Optional[List[str]] = None,
        coingecko_ids: Optional[List[str]] = None,
    ):
        """Start all enabled WebSocket streams."""
        if self._running:
            return

        if self.harmonic_field:
            self.harmonic_field.start_streaming()

        if symbols is None:
            symbols = [
                "BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD", "DOGE/USD",
                "ADA/USD", "AVAX/USD", "DOT/USD", "MATIC/USD", "LINK/USD",
            ]
        
        if coingecko_ids is None:
            coingecko_ids = [
                "bitcoin", "ethereum", "solana", "ripple", "dogecoin",
                "cardano", "avalanche-2", "polkadot", "matic-network", "chainlink",
            ]
        
        self._running = True
        
        if self.enable.get('binance'):
            binance_symbols = [s.replace('/', '') for s in symbols]
            self._tasks.append(asyncio.create_task(self._binance_stream(binance_symbols)))
        
        if self.enable.get('kraken'):
            self._tasks.append(asyncio.create_task(self._kraken_stream(symbols)))
        
        if self.enable.get('coinbase'):
            self._tasks.append(asyncio.create_task(self._coinbase_stream(symbols)))
        
        if self.enable.get('capital'):
            self._tasks.append(asyncio.create_task(self._capital_stream(symbols)))
        
        if self.enable.get('coingecko'):
            self._tasks.append(asyncio.create_task(self._coingecko_poll(coingecko_ids)))
        
        logger.info(f"🌐⚡ UnifiedWSFeed started with {len(self._tasks)} streams")
    
    async def stop(self):
        """Stop all WebSocket streams."""
        self._running = False
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        self._tasks.clear()

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        if self.harmonic_field:
            self.harmonic_field.stop_streaming()
        
        for status in self.status.values():
            status.connected = False
        
        logger.info("🌐 UnifiedWSFeed stopped")
    
    def get_best_tick(self, symbol: str) -> Optional[NormalizedTick]:
        """Get the best (tightest spread) tick for a symbol across exchanges."""
        symbol = symbol.upper()
        if '/' not in symbol:
            symbol = f"{symbol}/USD"
        
        candidates = [
            t for t in self.ticks.values()
            if t.symbol == symbol and t.is_source_fresh()
        ]
        if not candidates:
            return None
        
        # Return tick with tightest spread
        return min(candidates, key=lambda t: t.spread)
    
    def get_health(self) -> Dict[str, Any]:
        """Return health status of all exchange connections."""
        return {
            ex: {
                'connected': s.connected,
                'healthy': s.is_healthy,
                'msg_count': s.message_count,
                'error_count': s.error_count,
                'last_msg_ago': time.time() - s.last_message if s.last_message else None,
            }
            for ex, s in self.status.items()
        }


# ═══════════════════════════════════════════════════════════════
# SINGLETON + INTEGRATION
# ═══════════════════════════════════════════════════════════════

_ws_feed: Optional[UnifiedWSFeed] = None

def get_ws_feed() -> UnifiedWSFeed:
    """Get or create the singleton UnifiedWSFeed instance."""
    global _ws_feed
    if _ws_feed is None:
        _ws_feed = UnifiedWSFeed()
    return _ws_feed


async def start_production_feeds(symbols: Optional[List[str]] = None):
    """Start the unified WS feed for production use."""
    feed = get_ws_feed()
    await feed.start(symbols=symbols)
    return feed


# ═══════════════════════════════════════════════════════════════
# CLI TEST
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    async def main():
        feed = get_ws_feed()
        
        # Print ticks as they arrive
        def on_tick(tick: NormalizedTick):
            print(f"[{tick.exchange:10}] {tick.symbol:12} bid={tick.bid:.4f} ask={tick.ask:.4f} last={tick.last:.4f}")
        
        feed.on_tick(on_tick)
        
        await feed.start()
        
        try:
            # Run for 60 seconds
            await asyncio.sleep(60)
        finally:
            await feed.stop()
            print("\n📊 Final Health:")
            for ex, health in feed.get_health().items():
                print(f"   {ex}: {health}")
    
    asyncio.run(main())
