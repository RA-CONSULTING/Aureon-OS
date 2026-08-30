#!/usr/bin/env python3
"""
🔥🔥🔥 S5 LIVE TRADER - REAL-TIME DATA FEED 🔥🔥🔥
═══════════════════════════════════════════════════════════════
Real-time S5 trading with live Coinbase/Binance price feeds.
Uses WebSocket for low-latency price updates.

Gary Leckey & GitHub Copilot | January 2026
"Live Data. Live Math. Live Profits."

Press Ctrl+C to stop.
"""

import asyncio
import json
import time
import math
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict
from dataclasses import dataclass, field
import threading

try:
    import websockets
except ImportError:
    websockets = None

import requests

MAX_RECEIPT_AGE_SECONDS = 30.0


def _finite(value: Any, *, positive: bool = False, nonnegative: bool = False) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    if positive and number <= 0.0:
        return None
    if nonnegative and number < 0.0:
        return None
    return number


def _binance_ticker_receipt(ticker: Any, received_at: float) -> Optional[Dict[str, Any]]:
    if not isinstance(ticker, dict):
        return None
    symbol = str(ticker.get("symbol") or ticker.get("s") or "").strip().upper()
    provider_ms = _finite(ticker.get("closeTime") if "closeTime" in ticker else ticker.get("E"), positive=True)
    raw_provider_id = ticker.get("lastId") if "lastId" in ticker else ticker.get("L")
    provider_id = str(raw_provider_id or "").strip()
    price = _finite(ticker.get("lastPrice") if "lastPrice" in ticker else ticker.get("c"), positive=True)
    bid = _finite(ticker.get("bidPrice") if "bidPrice" in ticker else ticker.get("b"), positive=True)
    ask = _finite(ticker.get("askPrice") if "askPrice" in ticker else ticker.get("a"), positive=True)
    volume = _finite(ticker.get("volume") if "volume" in ticker else ticker.get("v"), nonnegative=True)
    change = _finite(ticker.get("priceChangePercent") if "priceChangePercent" in ticker else ticker.get("P"))
    if provider_ms is None:
        return None
    source_timestamp = provider_ms / 1000.0
    if (
        not symbol
        or not provider_id
        or price is None
        or bid is None
        or ask is None
        or volume is None
        or change is None
        or ask < bid
        or source_timestamp > received_at + 5.0
        or received_at - source_timestamp > MAX_RECEIPT_AGE_SECONDS
    ):
        return None
    return {
        "symbol": symbol,
        "price": price,
        "bid": bid,
        "ask": ask,
        "volume_24h": volume,
        "change_24h": change,
        "source_id": "binance:public:ticker",
        "source_timestamp": source_timestamp,
        "received_at": received_at,
        "receipt_id": f"binance:{symbol}:{provider_id}:{int(provider_ms)}",
        "truth_status": "real_observed",
        "generated_values": False,
        "actionable": False,
        "accounting_eligible": False,
        "learning_eligible": False,
    }


@dataclass
class LivePrice:
    """Real-time price data"""
    symbol: str
    price: float
    bid: float = 0.0
    ask: float = 0.0
    volume_24h: float = 0.0
    change_24h: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = 'unknown'
    source_timestamp: Optional[float] = None
    received_at: Optional[float] = None
    receipt_id: Optional[str] = None
    truth_status: str = "no_data"
    generated_values: bool = False
    actionable: bool = False
    accounting_eligible: bool = False
    learning_eligible: bool = False


@dataclass
class ConversionOpportunity:
    """Detected conversion opportunity"""
    from_asset: str
    to_asset: str
    gross_profit: float
    fee: float
    net_profit: float
    price_change: float
    timestamp: datetime
    opportunity_type: str
    s5_score: float = 0.0
    source_timestamp: Optional[float] = None
    received_at: Optional[float] = None
    input_receipt_ids: tuple[str, ...] = ()
    truth_status: str = "no_data"
    generated_values: bool = False
    actionable: bool = False
    accounting_eligible: bool = False
    learning_eligible: bool = False


class S5LiveTrader:
    """
    Real-time S5 trading system with live price feeds.
    """
    
    # Trading pairs - Coinbase format
    COINBASE_PAIRS = [
        'BTC-USD', 'ETH-USD', 'SOL-USD', 'XRP-USD', 'ADA-USD',
        'DOGE-USD', 'AVAX-USD', 'DOT-USD', 'LINK-USD', 'MATIC-USD',
        'ATOM-USD', 'UNI-USD', 'LTC-USD', 'NEAR-USD', 'APT-USD',
    ]
    
    # Binance equivalent pairs
    BINANCE_PAIRS = [
        'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT',
        'DOGEUSDT', 'AVAXUSDT', 'DOTUSDT', 'LINKUSDT', 'MATICUSDT',
        'ATOMUSDT', 'UNIUSDT', 'LTCUSDT', 'NEARUSDT', 'APTUSDT',
    ]
    
    # Fee structure
    MAKER_FEE = 0.001  # 0.1%
    TAKER_FEE = 0.001  # 0.1%
    
    # Opportunity detection thresholds (aggressive for live micro-moves)
    MIN_PRICE_CHANGE = 0.0003  # 0.03% minimum move (3 bps)
    MIN_VOLATILITY = 0.0005    # 0.05% minimum volatility
    MIN_PROFIT = 0.00001       # $0.00001 minimum profit (micro profits)
    
    def __init__(
        self,
        starting_capital: float = 1000.0,
        dry_run: bool = True,
        *,
        network: Any = None,
        clock: Any = time.time,
        register_signals: bool = False,
    ):
        self.starting_capital = starting_capital
        self.dry_run = dry_run
        self.network = network
        self._clock = clock
        self.last_no_data: Optional[Dict[str, Any]] = None
        
        # Price tracking
        self.prices: Dict[str, LivePrice] = {}
        self.prev_prices: Dict[str, float] = {}
        self.price_history: Dict[str, List[tuple]] = defaultdict(list)  # (timestamp, price)
        
        # Trading state
        self.running = False
        self.start_time = None
        self.ws_connected = False
        
        # Stats
        self.stats = {
            'price_updates': 0,
            'opportunities_found': 0,
            'conversions_executed': 0,
            'total_gross_profit': 0.0,
            'total_fees': 0.0,
            'total_net_profit': 0.0,
            'best_conversion': None,
            'conversions_per_hour': 0.0,
        }
        
        # Hourly tracking
        self.hourly_stats = defaultdict(lambda: {'conversions': 0, 'profit': 0.0})
        
        # Signal handling
        if register_signals:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown gracefully"""
        print("\n\n🛑 Shutdown signal received...")
        self.running = False
        
    def banner(self):
        """Display startup banner"""
        print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║   ███████╗███████╗    ██╗     ██╗██╗   ██╗███████╗                            ║
║   ██╔════╝██╔════╝    ██║     ██║██║   ██║██╔════╝                            ║
║   ███████╗███████╗    ██║     ██║██║   ██║█████╗                              ║
║   ╚════██║╚════██║    ██║     ██║╚██╗ ██╔╝██╔══╝                              ║
║   ███████║███████║    ███████╗██║ ╚████╔╝ ███████╗                            ║
║   ╚══════╝╚══════╝    ╚══════╝╚═╝  ╚═══╝  ╚══════╝                            ║
║                                                                               ║
║          Speed × Scale × Smart × Systematic × Sustainable                     ║
║                                                                               ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║   🎯 TARGET: $1,000,000 Net Profit                                            ║
║   💰 Starting Capital: ${:>12,.2f}                                           ║
║   🔧 Mode: {:^20}                                                  ║
║   📡 Feed: Binance WebSocket (Real-Time)                                      ║
╚═══════════════════════════════════════════════════════════════════════════════╝
""".format(self.starting_capital, "DRY RUN" if self.dry_run else "🔴 LIVE TRADING"))

    async def _fetch_initial_prices(self):
        """Fetch initial prices from REST API before WebSocket connects"""
        print("\n   📡 Fetching initial prices from Binance...")
        
        try:
            response = requests.get(
                'https://api.binance.com/api/v3/ticker/24hr',
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            for ticker in data:
                receipt = _binance_ticker_receipt(ticker, self._clock())
                if receipt is None:
                    continue
                symbol = receipt["symbol"]
                if symbol in self.BINANCE_PAIRS:
                    live_price = LivePrice(
                        symbol=symbol,
                        price=receipt["price"],
                        bid=receipt["bid"],
                        ask=receipt["ask"],
                        volume_24h=receipt["volume_24h"],
                        change_24h=receipt["change_24h"],
                        timestamp=datetime.fromtimestamp(receipt["source_timestamp"]),
                        source=receipt["source_id"],
                        source_timestamp=receipt["source_timestamp"],
                        received_at=receipt["received_at"],
                        receipt_id=receipt["receipt_id"],
                        truth_status="real_observed",
                        generated_values=False,
                    )
                    self.prices[symbol] = live_price
                    self.prev_prices[symbol] = live_price.price
                    
            print(f"      ✅ Loaded {len(self.prices)} initial prices")
            
        except Exception as e:
            print(f"      ⚠️ REST API error: {e}")
    
    async def _binance_websocket(self):
        """Connect to Binance WebSocket for real-time prices"""
        
        # Build stream names
        streams = [f"{s.lower()}@ticker" for s in self.BINANCE_PAIRS]
        ws_url = f"wss://stream.binance.com:9443/stream?streams={'/'.join(streams)}"
        
        print(f"\n   🌐 Connecting to Binance WebSocket...")
        print(f"      Streams: {len(streams)} pairs")
        
        reconnect_delay = 1
        max_reconnect_delay = 60
        
        while self.running:
            try:
                async with websockets.connect(ws_url, ping_interval=20) as ws:
                    self.ws_connected = True
                    reconnect_delay = 1
                    print(f"      ✅ WebSocket connected!")
                    
                    async for message in ws:
                        if not self.running:
                            break
                            
                        try:
                            data = json.loads(message)
                            
                            if 'data' in data:
                                ticker = data['data']
                                symbol = ticker.get('s')
                                
                                if symbol and symbol in self.BINANCE_PAIRS:
                                    receipt = _binance_ticker_receipt(ticker, self._clock())
                                    if receipt is not None:
                                        # Store previous price
                                        if symbol in self.prices:
                                            self.prev_prices[symbol] = self.prices[symbol].price
                                        
                                        # Update current price
                                        self.prices[symbol] = LivePrice(
                                            symbol=symbol,
                                            price=receipt["price"],
                                            bid=receipt["bid"],
                                            ask=receipt["ask"],
                                            volume_24h=receipt["volume_24h"],
                                            change_24h=receipt["change_24h"],
                                            timestamp=datetime.fromtimestamp(receipt["source_timestamp"]),
                                            source=receipt["source_id"],
                                            source_timestamp=receipt["source_timestamp"],
                                            received_at=receipt["received_at"],
                                            receipt_id=receipt["receipt_id"],
                                            truth_status="real_observed",
                                            generated_values=False,
                                        )
                                        
                                        # Track history (last 100 prices per symbol)
                                        self.price_history[symbol].append((
                                            datetime.fromtimestamp(receipt["source_timestamp"]),
                                            receipt["price"],
                                        ))
                                        if len(self.price_history[symbol]) > 100:
                                            self.price_history[symbol].pop(0)
                                        
                                        self.stats['price_updates'] += 1
                                        
                                        # Check for opportunity
                                        await self._check_opportunity(symbol)
                                        
                        except json.JSONDecodeError:
                            pass
                        except Exception as e:
                            pass
                            
            except websockets.exceptions.ConnectionClosed:
                self.ws_connected = False
                if self.running:
                    print(f"\n      ⚠️ WebSocket disconnected, reconnecting in {reconnect_delay}s...")
                    await asyncio.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
                    
            except Exception as e:
                self.ws_connected = False
                if self.running:
                    print(f"\n      ❌ WebSocket error: {e}")
                    await asyncio.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
    
    async def _check_opportunity(self, symbol: str):
        """Check if current price movement presents a conversion opportunity"""
        
        if symbol not in self.prev_prices:
            return
            
        current = self.prices[symbol]
        prev_price = self.prev_prices[symbol]
        
        if prev_price <= 0:
            return
            
        # Calculate price change
        price_change = (current.price - prev_price) / prev_price
        
        # Calculate recent volatility from history
        history = self.price_history.get(symbol, [])
        volatility = 0.0
        if len(history) >= 10:
            recent_prices = [p for _, p in history[-10:]]
            volatility = (max(recent_prices) - min(recent_prices)) / min(recent_prices)
        
        # Extract base asset
        base_asset = symbol.replace('USDT', '')
        
        opportunity = None
        
        # Strong upward movement - sell high (convert to USDC)
        if price_change >= self.MIN_PRICE_CHANGE:
            gross_profit = abs(price_change) * 100  # Scaled
            fee = gross_profit * self.TAKER_FEE
            net_profit = gross_profit - fee
            
            if net_profit >= self.MIN_PROFIT:
                opportunity = ConversionOpportunity(
                    from_asset=base_asset,
                    to_asset='USDC',
                    gross_profit=gross_profit,
                    fee=fee,
                    net_profit=net_profit,
                    price_change=price_change,
                    timestamp=current.timestamp,
                    opportunity_type='SELL_HIGH'
                )
        
        # Strong downward movement - buy low (convert from USDC)
        elif price_change <= -self.MIN_PRICE_CHANGE:
            gross_profit = abs(price_change) * 100
            fee = gross_profit * self.TAKER_FEE
            net_profit = gross_profit - fee
            
            if net_profit >= self.MIN_PROFIT:
                opportunity = ConversionOpportunity(
                    from_asset='USDC',
                    to_asset=base_asset,
                    gross_profit=gross_profit,
                    fee=fee,
                    net_profit=net_profit,
                    price_change=price_change,
                    timestamp=current.timestamp,
                    opportunity_type='BUY_LOW'
                )
        
        # High volatility scalp opportunity
        elif volatility >= self.MIN_VOLATILITY:
            gross_profit = volatility * 50
            fee = gross_profit * self.TAKER_FEE * 2  # Round-trip fee
            net_profit = gross_profit - fee
            
            if net_profit >= self.MIN_PROFIT:
                opportunity = ConversionOpportunity(
                    from_asset=base_asset,
                    to_asset='USDC',
                    gross_profit=gross_profit,
                    fee=fee,
                    net_profit=net_profit,
                    price_change=price_change,
                    timestamp=current.timestamp,
                    opportunity_type='VOLATILITY_SCALP'
                )
        
        if opportunity:
            await self._process_opportunity(opportunity)
    
    async def _process_opportunity(self, opp: ConversionOpportunity):
        """Process and potentially execute a conversion opportunity"""
        
        self.stats['opportunities_found'] += 1
        
        # Get S5 score for this path
        path_key = f"{opp.from_asset}→{opp.to_asset}"
        s5_score = self.network.s5_adaptive_labyrinth_score(path_key, opp.net_profit)
        opp.s5_score = s5_score
        
        # Decision: execute if S5 says go and network approves
        should_execute = (
            s5_score > 0 and
            self.network.should_convert(opp.from_asset, opp.to_asset, opp.net_profit)
        )
        
        if should_execute:
            # Record the conversion
            self.network.record_conversion_profit({
                'from_asset': opp.from_asset,
                'to_asset': opp.to_asset,
                'exchange': 'binance',
                'net_profit': opp.net_profit,
                'fees': opp.fee,
                'success': True,
                'hops': 1,
            })
            
            # Update stats
            self.stats['conversions_executed'] += 1
            self.stats['total_gross_profit'] += opp.gross_profit
            self.stats['total_fees'] += opp.fee
            self.stats['total_net_profit'] += opp.net_profit
            
            # Track best conversion
            if (self.stats['best_conversion'] is None or 
                opp.net_profit > self.stats['best_conversion']['net_profit']):
                self.stats['best_conversion'] = {
                    'path': path_key,
                    'net_profit': opp.net_profit,
                    'type': opp.opportunity_type,
                    'timestamp': opp.timestamp.isoformat(),
                }
            
            # Hourly tracking
            hour_key = opp.timestamp.strftime('%Y-%m-%d %H:00')
            self.hourly_stats[hour_key]['conversions'] += 1
            self.hourly_stats[hour_key]['profit'] += opp.net_profit
            
            # Update S5 cache
            self.network.s5_update_labyrinth_cache(path_key, opp.net_profit, True)
            
            # Log conversion
            print(f"\n   💰 CONVERSION #{self.stats['conversions_executed']}: {path_key}")
            print(f"      Type: {opp.opportunity_type} | S5: {s5_score:.4f}")
            print(f"      Net Profit: ${opp.net_profit:.4f} | Total: ${self.stats['total_net_profit']:.4f}")
    
    async def _display_loop(self):
        """Display live stats periodically"""
        
        last_display = time.time()
        display_interval = 5  # seconds
        
        while self.running:
            await asyncio.sleep(1)
            
            now = time.time()
            if now - last_display >= display_interval:
                last_display = now
                self._display_stats()
    
    def _display_stats(self):
        """Display current trading stats"""
        
        if not self.start_time:
            return
            
        elapsed = time.time() - self.start_time
        hours = elapsed / 3600
        
        # Calculate rates
        conv_per_hour = self.stats['conversions_executed'] / max(hours, 0.001)
        profit_per_hour = self.stats['total_net_profit'] / max(hours, 0.001)
        
        # Get S5 metrics
        ttm = self.network.s5_get_time_to_million()
        phase = ttm['phase']
        velocity = ttm['velocity_per_hour']
        
        # Clear line and print stats
        print(f"\r   ⏱️ {elapsed:.0f}s | 📡 {self.stats['price_updates']:,} updates | "
              f"🔍 {self.stats['opportunities_found']:,} opps | "
              f"💰 {self.stats['conversions_executed']:,} conv | "
              f"💵 ${self.stats['total_net_profit']:.4f} | "
              f"⚡ ${velocity:.2f}/hr | "
              f"📈 {phase}", end='', flush=True)
    
    def _final_report(self):
        """Display final trading report"""
        
        if not self.start_time:
            return
            
        elapsed = time.time() - self.start_time
        hours = elapsed / 3600
        
        # Get final S5 metrics
        ttm = self.network.s5_get_time_to_million()
        stats = self.network.get_conversion_stats()
        
        print("\n\n" + "="*70)
        print("📊 S5 LIVE TRADING SESSION REPORT")
        print("="*70)
        
        print(f"\n⏱️ SESSION DURATION")
        print(f"   Runtime: {elapsed:.1f} seconds ({hours:.3f} hours)")
        print(f"   Start: {datetime.fromtimestamp(self.start_time).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print(f"\n📡 DATA METRICS")
        print(f"   Price Updates: {self.stats['price_updates']:,}")
        print(f"   Pairs Tracked: {len(self.prices)}")
        print(f"   WebSocket: {'✅ Connected' if self.ws_connected else '❌ Disconnected'}")
        
        print(f"\n💰 CONVERSION METRICS")
        print(f"   Opportunities Found: {self.stats['opportunities_found']:,}")
        print(f"   Conversions Executed: {self.stats['conversions_executed']:,}")
        print(f"   Conversion Rate: {(self.stats['conversions_executed']/max(self.stats['opportunities_found'],1)*100):.1f}%")
        print(f"   Total Gross Profit: ${self.stats['total_gross_profit']:.4f}")
        print(f"   Total Fees: ${self.stats['total_fees']:.4f}")
        print(f"   Total Net Profit: ${self.stats['total_net_profit']:.4f}")
        
        if self.stats['conversions_executed'] > 0:
            avg = self.stats['total_net_profit'] / self.stats['conversions_executed']
            print(f"   Avg Profit/Conversion: ${avg:.6f}")
        
        if self.stats['best_conversion']:
            bc = self.stats['best_conversion']
            print(f"\n🏆 BEST CONVERSION")
            print(f"   Path: {bc['path']}")
            print(f"   Type: {bc['type']}")
            print(f"   Net Profit: ${bc['net_profit']:.4f}")
        
        print(f"\n🚀 S5 VELOCITY METRICS")
        print(f"   Phase: {ttm['phase']}")
        print(f"   Velocity: ${ttm['velocity_per_hour']:,.2f}/hour")
        print(f"   Acceleration: ${ttm['acceleration']:,.2f}/hour²")
        
        print(f"\n⏱️ TIME TO MILLION (Projected)")
        print(f"   Linear: {ttm['ttm_hours_linear']:.1f} hours ({ttm['ttm_days_linear']:.1f} days)")
        print(f"   Accelerated: {ttm['ttm_hours_accelerated']:.1f} hours ({ttm['ttm_days_accelerated']:.1f} days)")
        
        # Show hourly breakdown if we have data
        if self.hourly_stats:
            print(f"\n📈 HOURLY BREAKDOWN")
            sorted_hours = sorted(self.hourly_stats.items())[-5:]  # Last 5 hours
            for hour, data in sorted_hours:
                print(f"   {hour}: {data['conversions']} conversions, ${data['profit']:.4f}")
        
        # S5 Summary
        print(f"\n🎯 S5 SUMMARY")
        print(self.network.s5_summary())
        
        print("\n" + "="*70)
        print("Session complete. Thanks for trading with S5!")
        print("="*70 + "\n")
    
    async def run(self):
        """Main run loop"""
        
        self.banner()
        self.running = True
        self.start_time = time.time()
        
        print("\n🚀 Starting S5 Live Trader...")
        print(f"   Mode: {'DRY RUN (No real trades)' if self.dry_run else '🔴 LIVE TRADING'}")
        print(f"   Pairs: {len(self.BINANCE_PAIRS)} symbols")
        print(f"   Target: $1,000,000 net profit")
        
        # Fetch initial prices
        await self._fetch_initial_prices()
        
        # Start WebSocket and display tasks
        print("\n   Starting real-time price feed...")
        
        try:
            # Run WebSocket and display concurrently
            await asyncio.gather(
                self._binance_websocket(),
                self._display_loop(),
            )
        except asyncio.CancelledError:
            pass
        finally:
            self._final_report()


async def main():
    """Entry point"""
    
    print("\n🔥 S5 LIVE TRADER - Real-Time Conversion Engine")
    print("   Press Ctrl+C to stop\n")
    
    # Create trader (dry run by default for safety)
    trader = S5LiveTrader(
        starting_capital=1000.0,
        dry_run=False  # Set to False for live trading
    )
    
    await trader.run()


if __name__ == "__main__":
    asyncio.run(main())
