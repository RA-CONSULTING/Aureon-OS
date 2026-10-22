#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🦈🌍 ORCA GLOBAL HUNTER - THE WORLD NEVER SLEEPS 🌍🦈
═══════════════════════════════════════════════════════════════════════════════

"Why look at a puddle when you can hunt the entire ocean?"

The markets NEVER sleep:
  🌏 ASIA (Tokyo, Hong Kong, Singapore) - Active 00:00-09:00 UTC
  🌍 EUROPE (London, Frankfurt) - Active 07:00-16:00 UTC  
  🌎 AMERICAS (NYSE, NASDAQ) - Active 14:30-21:00 UTC
  🪙 CRYPTO - 24/7/365 ALWAYS

EXCHANGE COVERAGE:
  🐙 KRAKEN: 1,419 crypto pairs (24/7)
  🦙 ALPACA: 62 crypto + 10,000 stocks (crypto 24/7, stocks market hours)
  🟡 BINANCE: 1,565 pairs (24/7 - data only for UK)

TOTAL HUNTING GROUNDS: ~13,000+ opportunities!

Gary Leckey | Orca Never Sleeps | January 2026
═══════════════════════════════════════════════════════════════════════════════
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

# Windows UTF-8 Fix
from aureon.utils.console_utf8 import ensure_utf8_stdout  # noqa: E402

ensure_utf8_stdout()

import time
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# 🌍 MARKET SESSION TRACKING
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MarketSession:
    """A global market session with its active hours."""
    name: str
    region: str
    utc_open: int  # Hour UTC
    utc_close: int  # Hour UTC
    exchanges: List[str]
    asset_types: List[str]  # 'crypto', 'stock', 'forex', 'commodity'
    
    def is_active(self) -> bool:
        """Check if this session is currently active."""
        now = datetime.now(timezone.utc)
        hour = now.hour
        
        # Handle overnight sessions (e.g., 22:00-06:00)
        if self.utc_open > self.utc_close:
            return hour >= self.utc_open or hour < self.utc_close
        else:
            return self.utc_open <= hour < self.utc_close

# Global market sessions
MARKET_SESSIONS = [
    # CRYPTO - Always active!
    MarketSession("Crypto Global", "GLOBAL", 0, 24, ["kraken", "alpaca", "binance"], ["crypto"]),
    
    # Asia Pacific
    MarketSession("Tokyo", "ASIA", 0, 6, ["binance"], ["crypto"]),
    MarketSession("Hong Kong", "ASIA", 1, 8, ["binance"], ["crypto"]),
    MarketSession("Singapore", "ASIA", 1, 9, ["binance"], ["crypto"]),
    
    # Europe
    MarketSession("London", "EUROPE", 8, 16, ["kraken", "binance"], ["crypto"]),
    MarketSession("Frankfurt", "EUROPE", 7, 15, ["kraken", "binance"], ["crypto"]),
    
    # Americas
    MarketSession("New York Pre", "AMERICAS", 13, 14, ["alpaca"], ["stock"]),  # Pre-market
    MarketSession("New York Main", "AMERICAS", 14, 21, ["alpaca"], ["stock", "crypto"]),  # Main
    MarketSession("New York After", "AMERICAS", 21, 24, ["alpaca"], ["stock"]),  # After-hours
]


@dataclass
class GlobalOpportunity:
    """A hunting opportunity from any global market."""
    symbol: str
    exchange: str
    region: str
    
    # Direction and strength
    direction: str  # 'buy' or 'sell'
    momentum_pct: float  # % move that triggered signal
    confidence: float  # 0-1
    
    # Prices
    current_price: float
    entry_price: float
    
    # Costs and profitability
    fee_pct: float
    spread_pct: float
    net_edge: float  # Expected profit after costs
    
    # Metadata
    source: str  # Which scanner found it
    reason: str
    timestamp: float = field(default_factory=time.time)
    
    @property
    def is_profitable(self) -> bool:
        """Check if trade would be profitable after costs."""
        return self.net_edge > 0


# ═══════════════════════════════════════════════════════════════════════════════
# 🦈 ORCA GLOBAL HUNTER
# ═══════════════════════════════════════════════════════════════════════════════

class OrcaGlobalHunter:
    """
    🦈 THE ORCA GLOBAL HUNTER - Scans ALL markets, ALL exchanges, 24/7
    
    The Orca never sleeps because the world never sleeps.
    When one market closes, another opens.
    There's ALWAYS prey somewhere.
    """
    
    def __init__(self):
        self.exchanges: Dict[str, Any] = {}
        self.universes: Dict[str, Set[str]] = {}
        self.opportunities: List[GlobalOpportunity] = []
        
        # Exchange fee profiles
        self.fees = {
            'kraken': {'maker': 0.0016, 'taker': 0.0026, 'spread': 0.001},
            'alpaca': {'maker': 0.0025, 'taker': 0.0025, 'spread': 0.003},
            'binance': {'maker': 0.001, 'taker': 0.001, 'spread': 0.0005},
        }
        
        # Momentum thresholds (must beat costs!)
        self.min_momentum_pct = 0.5  # 0.5% minimum move
        
        # Stats
        self.total_scanned = 0
        self.scan_count = 0
        
        self._init_exchanges()
        
    def _init_exchanges(self):
        """Initialize connections to all exchanges."""
        print("\n🦈🌍 ORCA GLOBAL HUNTER INITIALIZING...")
        print("=" * 60)
        
        # Kraken (24/7 crypto)
        try:
            from aureon.exchanges.kraken_client import get_kraken_client
            self.exchanges['kraken'] = get_kraken_client()
            if self.exchanges['kraken']:
                pairs = self.exchanges['kraken']._load_asset_pairs()
                self.universes['kraken'] = {p for p in pairs.keys() if not p.endswith('.d')}
                print(f"   🐙 KRAKEN: {len(self.universes['kraken'])} pairs")
        except Exception as e:
            logger.warning(f"Kraken init error: {e}")
            
        # Alpaca (crypto + stocks)
        try:
            from aureon.exchanges.alpaca_client import AlpacaClient
            self.exchanges['alpaca'] = AlpacaClient()
            
            # Crypto universe
            crypto = self.exchanges['alpaca'].list_assets(status='active', asset_class='crypto') or []
            self.universes['alpaca_crypto'] = set()
            for a in crypto:
                sym = a.get('symbol') if isinstance(a, dict) else getattr(a, 'symbol', None)
                if sym:
                    if '/' not in sym:
                        sym = f"{sym}/USD"
                    self.universes['alpaca_crypto'].add(sym)
            print(f"   🦙 ALPACA CRYPTO: {len(self.universes['alpaca_crypto'])} symbols")
            
            # Stock universe (if market hours)
            if self._is_stock_market_open():
                try:
                    from alpaca.trading.requests import GetAssetsRequest
                    from alpaca.trading.enums import AssetClass, AssetStatus
                    
                    api = self.exchanges['alpaca'].trading_client
                    if api:
                        request = GetAssetsRequest(
                            asset_class=AssetClass.US_EQUITY,
                            status=AssetStatus.ACTIVE
                        )
                        assets = api.get_all_assets(request)
                        tradeable = [a for a in assets if a.tradable]
                        self.universes['alpaca_stocks'] = {a.symbol for a in tradeable[:1000]}  # Top 1000
                        print(f"   📈 ALPACA STOCKS: {len(self.universes['alpaca_stocks'])} symbols (market open)")
                except Exception as e:
                    logger.debug(f"Stock universe error: {e}")
                    
        except Exception as e:
            logger.warning(f"Alpaca init error: {e}")
            
        # Binance (data only for UK)
        try:
            from aureon.exchanges.binance_client import BinanceClient, get_binance_client
            self.exchanges['binance'] = BinanceClient()
            info = self.exchanges['binance'].exchange_info()
            symbols = [s['symbol'] for s in info.get('symbols', []) if s.get('status') == 'TRADING']
            self.universes['binance'] = set(symbols)
            print(f"   🟡 BINANCE: {len(self.universes['binance'])} pairs (data only)")
        except Exception as e:
            logger.warning(f"Binance init error: {e}")
            
        # Calculate total
        total = sum(len(u) for u in self.universes.values())
        print(f"\n   🌍 TOTAL HUNTING GROUNDS: {total:,} opportunities!")
        print("=" * 60)
        
    def _is_stock_market_open(self) -> bool:
        """Check if US stock market is open."""
        now = datetime.now(timezone.utc)
        # Mon-Fri 14:30-21:00 UTC (9:30am-4pm EST)
        if now.weekday() < 5:
            hour = now.hour + now.minute / 60
            return 14.5 <= hour < 21
        return False
        
    def get_active_sessions(self) -> List[MarketSession]:
        """Get currently active market sessions."""
        return [s for s in MARKET_SESSIONS if s.is_active()]
        
    def scan_kraken(self, limit: int = 100) -> List[GlobalOpportunity]:
        """
        🐙 Scan Kraken for momentum opportunities.
        
        Kraken has 1,419 pairs - we sample the most active ones.
        """
        opportunities = []
        
        if 'kraken' not in self.exchanges:
            return opportunities
            
        kraken = self.exchanges['kraken']
        
        try:
            # Get tickers for top pairs
            tickers = kraken.get_all_tickers() if hasattr(kraken, 'get_all_tickers') else {}
            
            # Focus on USD pairs for easier comparison
            usd_pairs = [p for p in self.universes.get('kraken', set()) 
                        if 'USD' in p and 'USDC' not in p and 'USDT' not in p]
            
            for pair in usd_pairs[:limit]:
                try:
                    ticker = tickers.get(pair) or kraken.get_ticker(pair)
                    if not ticker:
                        continue
                        
                    # Extract price data
                    price = float(ticker.get('c', [0])[0]) if isinstance(ticker.get('c'), list) else float(ticker.get('last', 0))
                    open_24h = float(ticker.get('o', 0))
                    
                    if not price or not open_24h:
                        continue
                        
                    # Calculate momentum
                    momentum = ((price - open_24h) / open_24h) * 100
                    
                    # Check if significant
                    if abs(momentum) >= self.min_momentum_pct:
                        fees = self.fees['kraken']
                        round_trip = fees['taker'] * 2 + fees['spread']
                        net_edge = abs(momentum) / 100 - round_trip
                        
                        if net_edge > 0:
                            opp = GlobalOpportunity(
                                symbol=pair,
                                exchange='kraken',
                                region='GLOBAL',
                                direction='buy' if momentum > 0 else 'sell',
                                momentum_pct=momentum,
                                confidence=min(abs(momentum) / 5, 1.0),  # Scale 0-1
                                current_price=price,
                                entry_price=price,
                                fee_pct=fees['taker'],
                                spread_pct=fees['spread'],
                                net_edge=net_edge,
                                source='kraken_momentum',
                                reason=f"24h momentum {momentum:+.2f}%"
                            )
                            opportunities.append(opp)
                            
                except Exception as e:
                    logger.debug(f"Kraken {pair} error: {e}")
                    continue
                    
        except Exception as e:
            logger.warning(f"Kraken scan error: {e}")
            
        return opportunities
        
    def scan_alpaca_crypto(self) -> List[GlobalOpportunity]:
        """
        🦙 Scan Alpaca crypto for momentum opportunities.
        """
        opportunities = []
        
        if 'alpaca' not in self.exchanges:
            return opportunities
            
        alpaca = self.exchanges['alpaca']
        
        try:
            symbols = list(self.universes.get('alpaca_crypto', set()))
            
            for symbol in symbols:
                try:
                    # Get current quote
                    ticker = alpaca.get_crypto_quote(symbol.replace('/', ''))
                    if not ticker:
                        continue
                        
                    price = float(ticker.get('ap', 0) or ticker.get('ask', 0))
                    if not price:
                        continue
                        
                    # Get 24h data for momentum
                    bars = alpaca.get_crypto_bars(symbol.replace('/', ''), timeframe='1D', limit=2)
                    if not bars or len(bars) < 2:
                        continue
                        
                    open_price = float(bars[-1].get('o', price))
                    momentum = ((price - open_price) / open_price) * 100
                    
                    if abs(momentum) >= self.min_momentum_pct:
                        fees = self.fees['alpaca']
                        round_trip = fees['taker'] * 2 + fees['spread']
                        net_edge = abs(momentum) / 100 - round_trip
                        
                        if net_edge > 0:
                            opp = GlobalOpportunity(
                                symbol=symbol,
                                exchange='alpaca',
                                region='AMERICAS',
                                direction='buy' if momentum > 0 else 'sell',
                                momentum_pct=momentum,
                                confidence=min(abs(momentum) / 5, 1.0),
                                current_price=price,
                                entry_price=price,
                                fee_pct=fees['taker'],
                                spread_pct=fees['spread'],
                                net_edge=net_edge,
                                source='alpaca_crypto',
                                reason=f"24h momentum {momentum:+.2f}%"
                            )
                            opportunities.append(opp)
                            
                except Exception as e:
                    logger.debug(f"Alpaca {symbol} error: {e}")
                    continue
                    
        except Exception as e:
            logger.warning(f"Alpaca crypto scan error: {e}")
            
        return opportunities
        
    def scan_binance(self, limit: int = 500) -> List[GlobalOpportunity]:
        """
        🟡 Scan Binance for momentum (data only - UK restricted).
        
        We use Binance's massive universe to FIND opportunities,
        then execute on Kraken/Alpaca where the same pair exists.
        """
        opportunities = []
        
        try:
            # Get 24h tickers - use direct API for best data
            import requests
            resp = requests.get('https://api.binance.com/api/v3/ticker/24hr', timeout=10)
            tickers = resp.json()
            
            # Sort by absolute price change % (biggest movers first!)
            tickers.sort(key=lambda x: abs(float(x.get('priceChangePercent', 0))), reverse=True)
            
            # Focus on USDT pairs (most liquid)
            for ticker in tickers[:limit]:
                try:
                    symbol = ticker.get('symbol', '')
                    if not symbol.endswith('USDT'):
                        continue
                        
                    price = float(ticker.get('lastPrice', 0))
                    momentum = float(ticker.get('priceChangePercent', 0))
                    volume = float(ticker.get('quoteVolume', 0))
                    
                    if not price or abs(momentum) < self.min_momentum_pct:
                        continue
                    
                    # Skip very low volume (< $100K daily)
                    if volume < 100000:
                        continue
                        
                    # Map to tradeable exchange
                    base = symbol.replace('USDT', '')
                    tradeable_symbol = f"{base}/USD"
                    
                    # Check if tradeable on our exchanges
                    can_trade_kraken = f"{base}USD" in self.universes.get('kraken', set())
                    can_trade_alpaca = tradeable_symbol in self.universes.get('alpaca_crypto', set())
                    
                    if can_trade_kraken or can_trade_alpaca:
                        exchange = 'kraken' if can_trade_kraken else 'alpaca'
                        fees = self.fees[exchange]
                        round_trip = fees['taker'] * 2 + fees['spread']
                        net_edge = abs(momentum) / 100 - round_trip
                        
                        if net_edge > 0:
                            opp = GlobalOpportunity(
                                symbol=tradeable_symbol,
                                exchange=exchange,
                                region='GLOBAL',
                                direction='buy' if momentum > 0 else 'sell',
                                momentum_pct=momentum,
                                confidence=min(abs(momentum) / 10, 1.0),  # Scale: 10%+ = max conf
                                current_price=price,
                                entry_price=price,
                                fee_pct=fees['taker'],
                                spread_pct=fees['spread'],
                                net_edge=net_edge,
                                source='binance_signal',
                                reason=f"Binance 24h: {momentum:+.2f}% (Vol: ${volume/1e6:.1f}M)"
                            )
                            opportunities.append(opp)
                                
                except Exception as e:
                    continue
                    
        except Exception as e:
            logger.warning(f"Binance scan error: {e}")
            
        return opportunities
        
    def hunt_global(self) -> List[GlobalOpportunity]:
        """
        🦈🌍 HUNT THE ENTIRE GLOBE
        
        Scans ALL exchanges in parallel and returns the best opportunities.
        """
        print("\n" + "=" * 70)
        print("🦈🌍 ORCA GLOBAL HUNT - SCANNING THE WORLD 🌍🦈")
        print("=" * 70)
        
        # Show active sessions
        active = self.get_active_sessions()
        print(f"\n🌐 ACTIVE MARKET SESSIONS:")
        for session in active:
            print(f"   {session.region}: {session.name} ({', '.join(session.exchanges)})")
        
        all_opportunities = []
        
        # Scan all exchanges in parallel
        print(f"\n🔍 SCANNING ALL EXCHANGES...")
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self.scan_kraken, 200): 'kraken',
                executor.submit(self.scan_alpaca_crypto): 'alpaca',
                executor.submit(self.scan_binance, 300): 'binance',
            }
            
            for future in as_completed(futures):
                exchange = futures[future]
                try:
                    opps = future.result()
                    all_opportunities.extend(opps)
                    print(f"   {exchange.upper()}: Found {len(opps)} momentum signals")
                except Exception as e:
                    print(f"   {exchange.upper()}: Error - {e}")
                    
        # Sort by net edge (most profitable first)
        all_opportunities.sort(key=lambda x: x.net_edge, reverse=True)
        
        # Update stats
        self.total_scanned = sum(len(u) for u in self.universes.values())
        self.scan_count += 1
        self.opportunities = all_opportunities
        
        # Summary
        print(f"\n📊 GLOBAL SCAN RESULTS:")
        print(f"   Universe scanned: {self.total_scanned:,} symbols")
        print(f"   Momentum signals: {len(all_opportunities)}")
        
        if all_opportunities:
            print(f"\n🎯 TOP OPPORTUNITIES:")
            for opp in all_opportunities[:10]:
                print(f"   {opp.symbol} ({opp.exchange}): {opp.momentum_pct:+.2f}% "
                      f"→ net edge {opp.net_edge*100:.3f}%")
                      
        print("=" * 70)
        
        return all_opportunities
        
    def get_best_kill(self) -> Optional[GlobalOpportunity]:
        """Get the single best opportunity for immediate execution."""
        if not self.opportunities:
            self.hunt_global()
            
        profitable = [o for o in self.opportunities if o.is_profitable]
        if profitable:
            return profitable[0]
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# 🦈 QUICK FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def orca_hunt_world():
    """🦈🌍 Hunt the entire global market."""
    hunter = OrcaGlobalHunter()
    return hunter.hunt_global()

def orca_best_global_kill():
    """🦈🎯 Get the single best global opportunity."""
    hunter = OrcaGlobalHunter()
    return hunter.get_best_kill()

def orca_global_status():
    """🌍 Show current global market status."""
    print("\n" + "=" * 60)
    print("🌍 GLOBAL MARKET STATUS")
    print("=" * 60)
    
    now = datetime.now(timezone.utc)
    print(f"\n⏰ Current UTC: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print(f"\n📍 ACTIVE SESSIONS:")
    for session in MARKET_SESSIONS:
        status = "🟢 ACTIVE" if session.is_active() else "⚫ CLOSED"
        print(f"   {status} {session.name} ({session.region}) - {', '.join(session.exchanges)}")
        
    print(f"\n🪙 CRYPTO: 24/7 ALWAYS ACTIVE")
    print(f"   Kraken: 1,419 pairs")
    print(f"   Alpaca: 62 symbols")
    print(f"   Binance: 1,565 pairs (data)")
    
    print("=" * 60)


if __name__ == "__main__":
    # Run global hunt
    opportunities = orca_hunt_world()
    
    if opportunities:
        print(f"\n🦈 READY TO STRIKE!")
        best = opportunities[0]
        print(f"   Best target: {best.symbol} on {best.exchange}")
        print(f"   Direction: {best.direction.upper()}")
        print(f"   Momentum: {best.momentum_pct:+.2f}%")
        print(f"   Net edge: {best.net_edge*100:.3f}%")
    else:
        print("\n⏳ No profitable opportunities found - scanning continues...")
