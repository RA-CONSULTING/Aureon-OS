"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║     🦙 ALPACA SSE STREAMING CLIENT 🦙                                                ║
║     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                ║
║                                                                                      ║
║     Real-time market data streaming via WebSocket push (no polling)                  ║
║                                                                                      ║
║     STREAMS:                                                                         ║
║       • Crypto Trades       - Real-time trade executions                             ║
║       • Crypto Quotes       - Bid/Ask updates                                        ║
║       • Crypto Bars         - OHLCV candles                                          ║
║       • Stock Trades        - US equity trades                                       ║
║       • Stock Quotes        - NBBO quotes                                            ║
║       • News                - Market news events                                     ║
║                                                                                      ║
║     Integration with 6D Harmonic Waveform for enhanced probability                   ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import json
import time
import logging
import threading
import queue
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import deque

try:
    import websockets
    WS_AVAILABLE = True
except ImportError:
    WS_AVAILABLE = False
    websockets = None

# Backward-compat alias: the transport is now WebSocket, but callers that
# gate on SSE_AVAILABLE (e.g. bots/orca_command_center.py dynamic imports)
# keep working.
SSE_AVAILABLE = WS_AVAILABLE

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════

@dataclass
class StreamTrade:
    """Real-time trade data"""
    symbol: str
    price: float
    size: float
    timestamp: datetime
    exchange: str = ""
    conditions: List[str] = field(default_factory=list)
    tape: str = ""
    
@dataclass
class StreamQuote:
    """Real-time quote data"""
    symbol: str
    bid_price: float
    bid_size: float
    ask_price: float
    ask_size: float
    timestamp: datetime
    bid_exchange: str = ""
    ask_exchange: str = ""
    conditions: List[str] = field(default_factory=list)

@dataclass
class StreamBar:
    """Real-time bar/candle data"""
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: datetime
    trade_count: int = 0
    vwap: float = 0.0

@dataclass
class StreamNews:
    """Real-time news data"""
    id: str
    headline: str
    summary: str
    symbols: List[str]
    timestamp: datetime
    source: str = ""
    url: str = ""
    sentiment: float = 0.0  # Will be calculated


class AlpacaSSEClient:
    """
    Alpaca SSE Streaming Client for real-time market data.
    
    Provides:
    - Real-time trade/quote/bar streaming
    - News feed with sentiment analysis
    - Integration hooks for trading systems
    - Thread-safe event queues
    """
    
    def __init__(self):
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.secret_key = os.getenv('ALPACA_SECRET_KEY')

        # Stream state
        self.running = False
        self.threads: Dict[str, threading.Thread] = {}
        
        # Event queues (thread-safe)
        self.trade_queue = queue.Queue(maxsize=10000)
        self.quote_queue = queue.Queue(maxsize=10000)
        self.bar_queue = queue.Queue(maxsize=1000)
        self.news_queue = queue.Queue(maxsize=100)
        
        # Latest data cache (for instant access)
        self.latest_trades: Dict[str, StreamTrade] = {}
        self.latest_quotes: Dict[str, StreamQuote] = {}
        self.latest_bars: Dict[str, StreamBar] = {}
        
        # Price history for momentum calculation
        self.price_history: Dict[str, deque] = {}
        self.HISTORY_SIZE = 100
        
        # Callbacks for external systems
        self.on_trade: Optional[Callable[[StreamTrade], None]] = None
        self.on_quote: Optional[Callable[[StreamQuote], None]] = None
        self.on_bar: Optional[Callable[[StreamBar], None]] = None
        self.on_news: Optional[Callable[[StreamNews], None]] = None
        
        # Statistics
        self.stats = {
            'trades_received': 0,
            'quotes_received': 0,
            'bars_received': 0,
            'news_received': 0,
            'errors': 0,
            'reconnects': 0,
            'start_time': None
        }
        
        logger.info("🦙 Alpaca SSE Client initialized")
    
    def _parse_timestamp(self, ts_str: str) -> datetime:
        """Parse ISO timestamp from Alpaca."""
        try:
            # Handle nanosecond precision
            if '.' in ts_str:
                parts = ts_str.split('.')
                # Truncate to microseconds
                if len(parts[1]) > 6:
                    ts_str = f"{parts[0]}.{parts[1][:6]}Z"
            return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except:
            return datetime.utcnow()
    
    def _process_trade(self, data: Dict) -> Optional[StreamTrade]:
        """Process incoming trade event."""
        try:
            trade = StreamTrade(
                symbol=data.get('S', data.get('symbol', '')),
                price=float(data.get('p', data.get('price', 0))),
                size=float(data.get('s', data.get('size', 0))),
                timestamp=self._parse_timestamp(data.get('t', data.get('timestamp', ''))),
                exchange=data.get('x', data.get('exchange', '')),
                conditions=data.get('c', data.get('conditions', [])),
                tape=data.get('z', data.get('tape', ''))
            )
            
            # Update cache
            self.latest_trades[trade.symbol] = trade
            
            # Update price history
            if trade.symbol not in self.price_history:
                self.price_history[trade.symbol] = deque(maxlen=self.HISTORY_SIZE)
            self.price_history[trade.symbol].append({
                'price': trade.price,
                'size': trade.size,
                'time': trade.timestamp
            })
            
            self.stats['trades_received'] += 1
            return trade
        except Exception as e:
            logger.error(f"Error processing trade: {e}")
            self.stats['errors'] += 1
            return None
    
    def _process_quote(self, data: Dict) -> Optional[StreamQuote]:
        """Process incoming quote event."""
        try:
            quote = StreamQuote(
                symbol=data.get('S', data.get('symbol', '')),
                bid_price=float(data.get('bp', data.get('bid_price', 0))),
                bid_size=float(data.get('bs', data.get('bid_size', 0))),
                ask_price=float(data.get('ap', data.get('ask_price', 0))),
                ask_size=float(data.get('as', data.get('ask_size', 0))),
                timestamp=self._parse_timestamp(data.get('t', data.get('timestamp', ''))),
                bid_exchange=data.get('bx', data.get('bid_exchange', '')),
                ask_exchange=data.get('ax', data.get('ask_exchange', '')),
                conditions=data.get('c', data.get('conditions', []))
            )
            
            # Update cache
            self.latest_quotes[quote.symbol] = quote
            self.stats['quotes_received'] += 1
            return quote
        except Exception as e:
            logger.error(f"Error processing quote: {e}")
            self.stats['errors'] += 1
            return None
    
    def _process_bar(self, data: Dict) -> Optional[StreamBar]:
        """Process incoming bar event."""
        try:
            bar = StreamBar(
                symbol=data.get('S', data.get('symbol', '')),
                open=float(data.get('o', data.get('open', 0))),
                high=float(data.get('h', data.get('high', 0))),
                low=float(data.get('l', data.get('low', 0))),
                close=float(data.get('c', data.get('close', 0))),
                volume=float(data.get('v', data.get('volume', 0))),
                timestamp=self._parse_timestamp(data.get('t', data.get('timestamp', ''))),
                trade_count=int(data.get('n', data.get('trade_count', 0))),
                vwap=float(data.get('vw', data.get('vwap', 0)))
            )
            
            # Update cache
            self.latest_bars[bar.symbol] = bar
            self.stats['bars_received'] += 1
            return bar
        except Exception as e:
            logger.error(f"Error processing bar: {e}")
            self.stats['errors'] += 1
            return None
    
    def _process_news(self, data: Dict) -> Optional[StreamNews]:
        """Process incoming news event."""
        try:
            headline = data.get('headline', '')
            summary = data.get('summary', data.get('content', ''))
            
            # Simple sentiment analysis based on keywords
            sentiment = self._analyze_sentiment(headline + " " + summary)
            
            news = StreamNews(
                id=data.get('id', str(time.time())),
                headline=headline,
                summary=summary,
                symbols=data.get('symbols', []),
                timestamp=self._parse_timestamp(data.get('created_at', data.get('timestamp', ''))),
                source=data.get('source', ''),
                url=data.get('url', ''),
                sentiment=sentiment
            )
            
            self.stats['news_received'] += 1
            return news
        except Exception as e:
            logger.error(f"Error processing news: {e}")
            self.stats['errors'] += 1
            return None
    
    def _analyze_sentiment(self, text: str) -> float:
        """Simple keyword-based sentiment analysis."""
        text_lower = text.lower()
        
        positive_words = [
            'surge', 'soar', 'rally', 'gain', 'rise', 'jump', 'climb', 'boost',
            'bullish', 'breakout', 'record', 'high', 'strong', 'growth', 'profit',
            'beat', 'exceed', 'upgrade', 'buy', 'outperform', 'positive'
        ]
        
        negative_words = [
            'drop', 'fall', 'plunge', 'crash', 'decline', 'slip', 'tumble', 'sink',
            'bearish', 'breakdown', 'low', 'weak', 'loss', 'miss', 'downgrade',
            'sell', 'underperform', 'negative', 'warning', 'risk', 'fear'
        ]
        
        pos_count = sum(1 for w in positive_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)
        
        total = pos_count + neg_count
        if total == 0:
            return 0.0
        
        # Sentiment from -1 (bearish) to +1 (bullish)
        return (pos_count - neg_count) / total
    
    # WebSocket endpoints (Alpaca streaming is WebSocket-only; the old
    # GET-based "SSE" URLs return 404 / "bad Upgrade header").
    WS_BASE = "wss://stream.data.alpaca.markets"
    # Free market-data tier carries IEX stock feeds; SIP needs a paid
    # subscription and would 403 on free keys.
    STOCK_WS_PATH = "/v2/iex"
    CRYPTO_WS_PATH = "/v1beta3/crypto/us"
    NEWS_WS_PATH = "/v1beta1/news"

    # One connection per group — Alpaca caps concurrent connections per
    # account (error 406 connection limit exceeded), so channels share.
    GROUP_URLS = {
        'crypto': CRYPTO_WS_PATH,
        'stocks': STOCK_WS_PATH,
        'news': NEWS_WS_PATH,
    }

    def _handle_event(self, data: Dict):
        """Dispatch one decoded Alpaca event by its own type field."""
        kind = data.get('T')
        if kind == 't':
            trade = self._process_trade(data)
            if trade:
                try:
                    self.trade_queue.put_nowait(trade)
                except queue.Full:
                    pass
                if self.on_trade:
                    self.on_trade(trade)
        elif kind == 'q':
            quote = self._process_quote(data)
            if quote:
                try:
                    self.quote_queue.put_nowait(quote)
                except queue.Full:
                    pass
                if self.on_quote:
                    self.on_quote(quote)
        elif kind == 'b':
            bar = self._process_bar(data)
            if bar:
                try:
                    self.bar_queue.put_nowait(bar)
                except queue.Full:
                    pass
                if self.on_bar:
                    self.on_bar(bar)
        elif kind == 'n':
            news = self._process_news(data)
            if news:
                try:
                    self.news_queue.put_nowait(news)
                except queue.Full:
                    pass
                if self.on_news:
                    self.on_news(news)

    async def _ws_stream(self, group: str, symbols: List[str], channels: List[str]):
        """One WebSocket connection attempt: auth -> subscribe -> pump events."""
        import asyncio
        url = f"{self.WS_BASE}{self.GROUP_URLS[group]}"
        async with websockets.connect(url, ping_interval=20, ping_timeout=20,
                                      max_queue=1000) as ws:
            # Auth handshake
            await ws.send(json.dumps({
                "action": "auth",
                "key": self.api_key,
                "secret": self.secret_key,
            }))
            # Wait for auth result before subscribing
            while True:
                raw = await asyncio.wait_for(ws.recv(), timeout=30)
                for msg in json.loads(raw):
                    t = msg.get('T')
                    if t == 'success' and msg.get('msg') == 'authenticated':
                        break
                    if t == 'error':
                        raise RuntimeError(
                            f"Alpaca stream auth error {msg.get('code')}: {msg.get('msg')}")
                else:
                    continue
                break

            sub = {"action": "subscribe"}
            for ch in channels:
                sub[ch] = symbols
            await ws.send(json.dumps(sub))

            # Event pump
            async for raw in ws:
                if not self.running:
                    break
                try:
                    for msg in json.loads(raw):
                        t = msg.get('T')
                        if t in ('success', 'subscription'):
                            logger.info(f"🦙 {group}: {msg.get('msg') or msg}")
                        elif t == 'error':
                            logger.error(f"🦙 {group} stream error: {msg}")
                            self.stats['errors'] += 1
                        else:
                            self._handle_event(msg)
                except json.JSONDecodeError:
                    continue

    def _start_group_stream(self, group: str, symbols: List[str],
                            channels: List[str]) -> bool:
        """Launch (once) a worker thread holding one WS connection for a group."""
        if not self.api_key:
            logger.error("Alpaca API key not configured")
            return False
        if group in self.threads and self.threads[group].is_alive():
            logger.info(f"🦙 {group} stream already running")
            return True

        self.running = True
        if not self.stats['start_time']:
            self.stats['start_time'] = datetime.now()

        t = threading.Thread(target=self._stream_worker,
                             args=(group, symbols, channels),
                             daemon=True)
        t.start()
        self.threads[group] = t
        logger.info(f"🦙 {group} streaming started "
                    f"({','.join(channels)}) for {len(symbols)} symbols")
        return True

    def _stream_worker(self, group: str, symbols: List[str], channels: List[str]):
        """Worker thread for WebSocket streaming (with reconnect)."""
        if not WS_AVAILABLE:
            logger.error("websockets not installed; cannot stream from Alpaca")
            return

        import asyncio
        logger.info(f"Starting WS stream: {group} [{','.join(channels)}] "
                    f"for {len(symbols)} symbols")

        while self.running:
            try:
                asyncio.run(self._ws_stream(group, symbols, channels))
            except RuntimeError as e:
                # Auth/config errors are fatal — reconnecting would just spin.
                logger.error(f"🦙 {group} stream failed permanently: {e}")
                self.stats['errors'] += 1
                break
            except Exception as e:
                if self.running:
                    logger.warning(f"WS stream disconnected: {e}. Reconnecting...")
                    self.stats['reconnects'] += 1
                    time.sleep(1)
    
    def start_crypto_stream(self, symbols: List[str],
                           trades: bool = True,
                           quotes: bool = True,
                           bars: bool = False):
        """Start streaming crypto data (one shared WS connection)."""
        # Format symbols for crypto (e.g., BTC/USD)
        formatted_symbols = []
        for s in symbols:
            if '/' not in s:
                # Convert BTCUSD to BTC/USD format
                if s.endswith('USD'):
                    formatted_symbols.append(f"{s[:-3]}/USD")
                else:
                    formatted_symbols.append(s)
            else:
                formatted_symbols.append(s)

        channels = []
        if trades:
            channels.append('trades')
        if quotes:
            channels.append('quotes')
        if bars:
            channels.append('bars')
        if not channels:
            logger.error("No crypto channels selected")
            return False

        return self._start_group_stream('crypto', formatted_symbols, channels)
    
    def start_stock_stream(self, symbols: List[str],
                          trades: bool = True,
                          quotes: bool = True):
        """Start streaming stock data (one shared WS connection, IEX feed)."""
        channels = []
        if trades:
            channels.append('trades')
        if quotes:
            channels.append('quotes')
        if not channels:
            logger.error("No stock channels selected")
            return False

        return self._start_group_stream('stocks', symbols, channels)

    def start_news_stream(self, symbols: List[str] = None):
        """Start streaming news."""
        symbols = symbols or ['*']  # All news if no symbols specified
        return self._start_group_stream('news', symbols, ['news'])
    
    def stop(self):
        """Stop all streams."""
        self.running = False
        time.sleep(0.5)  # Allow threads to exit gracefully
        self.threads.clear()
        logger.info("🦙 All streams stopped")
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get latest price from cache."""
        if symbol in self.latest_trades:
            return self.latest_trades[symbol].price
        return None
    
    def get_latest_quote(self, symbol: str) -> Optional[Dict]:
        """Get latest quote from cache."""
        if symbol in self.latest_quotes:
            q = self.latest_quotes[symbol]
            return {
                'bid': q.bid_price,
                'ask': q.ask_price,
                'spread': q.ask_price - q.bid_price,
                'spread_pct': (q.ask_price - q.bid_price) / q.bid_price * 100 if q.bid_price > 0 else 0,
                'mid': (q.bid_price + q.ask_price) / 2
            }
        return None
    
    def get_momentum(self, symbol: str, periods: int = 10) -> Optional[float]:
        """Calculate momentum from price history."""
        if symbol not in self.price_history:
            return None
        
        history = list(self.price_history[symbol])
        if len(history) < periods:
            return None
        
        recent = history[-periods:]
        start_price = recent[0]['price']
        end_price = recent[-1]['price']
        
        if start_price > 0:
            return (end_price - start_price) / start_price * 100
        return None
    
    def get_volatility(self, symbol: str, periods: int = 20) -> Optional[float]:
        """Calculate volatility from price history."""
        if symbol not in self.price_history:
            return None
        
        history = list(self.price_history[symbol])
        if len(history) < periods:
            return None
        
        prices = [h['price'] for h in history[-periods:]]
        mean = sum(prices) / len(prices)
        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        
        return (variance ** 0.5) / mean * 100 if mean > 0 else None
    
    def get_stats(self) -> Dict:
        """Get streaming statistics."""
        stats = self.stats.copy()
        if stats['start_time']:
            elapsed = (datetime.now() - stats['start_time']).total_seconds()
            stats['elapsed_seconds'] = elapsed
            stats['trades_per_second'] = stats['trades_received'] / elapsed if elapsed > 0 else 0
            stats['quotes_per_second'] = stats['quotes_received'] / elapsed if elapsed > 0 else 0
        return stats
    
    def get_ticker_data(self, symbol: str) -> Optional[Dict]:
        """Get combined ticker data for a symbol (for trading system integration)."""
        trade = self.latest_trades.get(symbol)
        quote = self.latest_quotes.get(symbol)
        bar = self.latest_bars.get(symbol)
        
        if not trade and not quote:
            return None
        
        price = trade.price if trade else (quote.bid_price + quote.ask_price) / 2
        
        # Get high/low from bar or estimate from price history
        if bar:
            high = bar.high
            low = bar.low
            volume = bar.volume
        else:
            high = price * 1.01  # Estimate
            low = price * 0.99
            volume = trade.size if trade else 0
        
        momentum = self.get_momentum(symbol)
        change = momentum if momentum else 0
        
        return {
            'symbol': symbol,
            'price': price,
            'high': high,
            'low': low,
            'volume': volume,
            'change': change,
            'bid': quote.bid_price if quote else price,
            'ask': quote.ask_price if quote else price,
            'spread_pct': (quote.ask_price - quote.bid_price) / quote.bid_price * 100 if quote and quote.bid_price > 0 else 0,
            'timestamp': trade.timestamp if trade else datetime.utcnow(),
            'exchange': 'alpaca',
            'quote': 'USD'
        }


class AlpacaStreamingIntegration:
    """
    Integration layer between Alpaca SSE streaming and the trading system.
    
    Provides:
    - Real-time ticker updates
    - Momentum/volatility calculations
    - News sentiment signals
    - 6D harmonic waveform updates
    """
    
    def __init__(self, harmonic_6d=None):
        self.sse_client = AlpacaSSEClient()
        self.harmonic_6d = harmonic_6d
        
        # Symbol subscriptions
        self.crypto_symbols: List[str] = []
        self.stock_symbols: List[str] = []
        
        # Real-time metrics
        self.realtime_metrics: Dict[str, Dict] = {}
        
        # Set up callbacks
        self.sse_client.on_trade = self._on_trade
        self.sse_client.on_quote = self._on_quote
        self.sse_client.on_bar = self._on_bar
        self.sse_client.on_news = self._on_news
        
        logger.info("🦙 Alpaca Streaming Integration initialized")
    
    def subscribe_crypto(self, symbols: List[str]):
        """Subscribe to crypto symbols."""
        self.crypto_symbols = symbols
        self.sse_client.start_crypto_stream(symbols, trades=True, quotes=True, bars=True)
    
    def subscribe_stocks(self, symbols: List[str]):
        """Subscribe to stock symbols."""
        self.stock_symbols = symbols
        self.sse_client.start_stock_stream(symbols, trades=True, quotes=True)
    
    def subscribe_news(self, symbols: List[str] = None):
        """Subscribe to news feed."""
        self.sse_client.start_news_stream(symbols)
    
    def _on_trade(self, trade: StreamTrade):
        """Handle trade events - update metrics and 6D waveform."""
        symbol = trade.symbol
        
        # Update real-time metrics
        if symbol not in self.realtime_metrics:
            self.realtime_metrics[symbol] = {
                'trades': 0,
                'volume': 0,
                'last_price': 0,
                'momentum': 0,
                'volatility': 0
            }
        
        metrics = self.realtime_metrics[symbol]
        metrics['trades'] += 1
        metrics['volume'] += trade.size
        metrics['last_price'] = trade.price
        metrics['momentum'] = self.sse_client.get_momentum(symbol) or 0
        metrics['volatility'] = self.sse_client.get_volatility(symbol) or 0

        # Feed into Autonomy Hub (The Big Wheel) for unified data capture
        try:
            from aureon.autonomous.aureon_autonomy_hub import get_autonomy_hub
            hub = get_autonomy_hub()
            hub.data_bridge.ingest_market_tick(
                symbol, trade.price, metrics['momentum'], metrics['volume'], 'alpaca'
            )
        except Exception:
            pass
        
        # Update 6D harmonic waveform if available
        if self.harmonic_6d:
            ticker = self.sse_client.get_ticker_data(symbol)
            if ticker:
                self.harmonic_6d.update(
                    symbol=symbol,
                    price=ticker['price'],
                    volume=ticker['volume'],
                    change_pct=ticker['change'],
                    high=ticker['high'],
                    low=ticker['low'],
                    frequency=432,  # Base frequency
                    coherence=0.7,  # Default
                    hnc_probability=0.5
                )
    
    def _on_quote(self, quote: StreamQuote):
        """Handle quote events."""
        pass  # Quotes are cached automatically
    
    def _on_bar(self, bar: StreamBar):
        """Handle bar events."""
        pass  # Bars are cached automatically
    
    def _on_news(self, news: StreamNews):
        """Handle news events - sentiment can affect probability."""
        logger.info(f"📰 News: {news.headline[:50]}... | Sentiment: {news.sentiment:+.2f}")
        
        # Update metrics for affected symbols
        for symbol in news.symbols:
            if symbol in self.realtime_metrics:
                # Sentiment affects probability
                self.realtime_metrics[symbol]['news_sentiment'] = news.sentiment
    
    def get_all_tickers(self) -> Dict[str, Dict]:
        """Get all ticker data for trading system."""
        tickers = {}
        
        for symbol in self.crypto_symbols + self.stock_symbols:
            ticker = self.sse_client.get_ticker_data(symbol)
            if ticker:
                tickers[symbol] = ticker
        
        return tickers
    
    def get_stats(self) -> Dict:
        """Get streaming statistics."""
        return self.sse_client.get_stats()
    
    def stop(self):
        """Stop all streams."""
        self.sse_client.stop()


# ═══════════════════════════════════════════════════════════════
# DEMO
# ═══════════════════════════════════════════════════════════════

def demo_alpaca_sse():
    """Demo Alpaca SSE streaming."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║     🦙 ALPACA SSE STREAMING DEMO 🦙                                          ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    client = AlpacaSSEClient()
    
    # Check if API keys are configured
    if not client.api_key:
        print("⚠️ ALPACA_API_KEY not set in environment")
        print("   Set ALPACA_API_KEY and ALPACA_SECRET_KEY to enable streaming")
        return
    
    print("Starting crypto stream for BTC, ETH, SOL...")
    
    # Define callback to print trades
    def on_trade(trade: StreamTrade):
        print(f"  💹 {trade.symbol}: ${trade.price:.2f} x {trade.size:.4f}")
    
    def on_news(news: StreamNews):
        sentiment_icon = "📈" if news.sentiment > 0 else "📉" if news.sentiment < 0 else "➡️"
        print(f"  📰 {sentiment_icon} {news.headline[:60]}...")
    
    client.on_trade = on_trade
    client.on_news = on_news
    
    # Start streams
    client.start_crypto_stream(['BTC/USD', 'ETH/USD', 'SOL/USD'])
    client.start_news_stream(['BTCUSD', 'ETHUSD'])
    
    print("\nStreaming for 30 seconds...")
    print("-" * 60)
    
    try:
        time.sleep(30)
    except KeyboardInterrupt:
        pass
    
    # Print stats
    stats = client.get_stats()
    print("\n" + "=" * 60)
    print(f"Streaming Statistics:")
    print(f"  Trades received: {stats['trades_received']}")
    print(f"  Quotes received: {stats['quotes_received']}")
    print(f"  News received: {stats['news_received']}")
    print(f"  Errors: {stats['errors']}")
    print(f"  Reconnects: {stats['reconnects']}")
    
    client.stop()
    print("\n✅ Demo complete")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo_alpaca_sse()
