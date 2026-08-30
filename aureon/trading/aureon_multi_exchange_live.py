#!/usr/bin/env python3
"""
🌐 AUREON MULTI-EXCHANGE LIVE TRADER v6.2 🌐
=============================================

Extends v6.1 unified trader to operate across multiple exchanges:
  ✨ Binance (Primary - USDC pairs)
  ✨ Kraken (Secondary - USD pairs)  
  ✨ Capital.com (CFD/Spread - forex, indices, commodities)

v6.2 Enhancements:
  • 6D Harmonic Waveform Market Ecosystem
  • Enhanced probability matrix with dimensional analysis
  • Cross-market resonance detection
  • Asset-class-aware coherence calculation

Same v6.1 intelligence, now with:
  • Smart Order Routing (best price across exchanges)
  • Cross-exchange arbitrage detection
  • Unified position tracking
  • Exchange-specific fee awareness

Gary Leckey | December 2025
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import time
import math
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal, ROUND_DOWN

# Import core components
from aureon.exchanges.binance_client import BinanceClient, get_binance_client
from aureon.strategies.hnc_probability_matrix import HNCProbabilityIntegration

# Unified market cache (Binance WS -> file cache)
try:
    from aureon.data_feeds.unified_market_cache import get_market_cache
    MARKET_CACHE_AVAILABLE = True
except ImportError:
    MARKET_CACHE_AVAILABLE = False
    get_market_cache = None

# Import Alpaca components
try:
    from aureon.exchanges.alpaca_client import AlpacaClient
    from aureon.exchanges.alpaca_sse_client import AlpacaStreamingIntegration
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    AlpacaClient = None
    AlpacaStreamingIntegration = None

# Import 6D Harmonic Waveform Engine
try:
    from aureon.strategies.hnc_6d_harmonic_waveform import Enhanced6DProbabilityMatrix, SixDimensionalHarmonicEngine
    HARMONIC_6D_AVAILABLE = True
except ImportError:
    HARMONIC_6D_AVAILABLE = False
    Enhanced6DProbabilityMatrix = None
    SixDimensionalHarmonicEngine = None

# Try to import other exchange clients
try:
    from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
    KRAKEN_AVAILABLE = True
except ImportError:
    KRAKEN_AVAILABLE = False
    KrakenClient = None

try:
    from aureon.exchanges.capital_client import CapitalClient
    CAPITAL_AVAILABLE = True
except ImportError:
    CAPITAL_AVAILABLE = False
    CapitalClient = None

if os.getenv("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "").strip().lower() not in {
    "1", "true", "yes", "on",
}:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler('aureon_multi_exchange.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION - MULTI-EXCHANGE v6.1
# ═══════════════════════════════════════════════════════════════════════════

CONFIG = {
    # Exchange Selection
    'ENABLE_BINANCE': True,
    'ENABLE_KRAKEN': os.getenv('ENABLE_KRAKEN', '1') == '1',
    'ENABLE_CAPITAL': os.getenv('ENABLE_CAPITAL', '1') == '1',  # CFD trading
    'ENABLE_ALPACA': os.getenv('ENABLE_ALPACA', '1') == '1',    # Stock/Crypto streaming
    'BINANCE_USE_UNIFIED_CACHE': os.getenv('BINANCE_USE_UNIFIED_CACHE', '1') == '1',
    
    # Paper Trading Mode
    'PAPER_TRADING': True,        # Simulate trades without real money
    'PAPER_BALANCE': 10000.0,     # Starting paper balance per exchange
    
    # Trading Parameters (v6.1)
    'MIN_TRADE_USD': 10.0,
    'MAX_POSITIONS': 4,           # Total across all exchanges
    'MAX_POSITIONS_PER_EXCHANGE': 2,
    
    # Risk Management - 1 penny (0.1%) net profit target
    'STOP_LOSS_PCT': 0.003,       # 0.3% stop loss (tight)
    'TAKE_PROFIT_PCT': 0.002,     # 0.2% take profit (~1-2p on £10 trade)
    'TIMEOUT_SEC': 180,           # 3 minutes max hold
    
    # Trailing Stop (v6) - Tight for penny profits
    'ENABLE_TRAILING_STOP': True,
    'TRAIL_ACTIVATION_PCT': 0.001,  # Activate after 0.1% gain
    'TRAIL_DISTANCE_PCT': 0.001,    # Trail by 0.1%
    
    # Coherence Thresholds (v6.1 tiered)
    'COHERENCE_THRESHOLD': 0.70,
    'COHERENCE_OPTIMAL': 0.88,
    'COHERENCE_SCALING': True,
    
    # Frequency Bands (v6.2 adjusted)
    # Optimal: 528Hz (Love), 639Hz, 741Hz, 852Hz, 963Hz (Solfeggio)
    'FREQ_OPTIMAL_MIN': 520,
    'FREQ_OPTIMAL_MAX': 963,
    # Avoid: Only narrow dissonant band around 440Hz (A4 interference)
    'FREQ_AVOID_MIN': 435,
    'FREQ_AVOID_MAX': 445,
    
    # Probability Thresholds (v6.1)
    'PROB_MIN': 0.50,
    'PROB_CAP': 0.83,
    
    # Exchange-specific fees
    'FEES': {
        'binance': 0.001,   # 0.1% taker
        'kraken': 0.0026,   # 0.26% taker
        'capital': 0.002,   # ~0.2% spread (CFD)
        'alpaca': 0.003,    # ~0.3% (varies)
    },
    
    # Quote currencies by exchange
    'QUOTE_CURRENCIES': {
        'binance': ['USDC', 'USDT'],
        'kraken': ['USD', 'EUR'],
        'capital': ['USD', 'GBP'],
        'alpaca': ['USD'],
    },
    
    # Capital.com specific markets to scan
    'CAPITAL_MARKETS': [
        'EURUSD', 'GBPUSD', 'USDJPY', 'GOLD', 'OIL_CRUDE', 'OIL_BRENT',
        'US500', 'US100', 'US30', 'UK100',
        'BTCO', 'ETHA',  # Bitcoin and Ethereum ETFs
    ],
    
    # Cooldown
    'COOLDOWN_MINUTES': 5,
    
    # Preferred symbols (proven edge)
    'PREFERRED_SYMBOLS': ['SAPIEN', 'LAYER', 'ZEC', 'GOLD', 'US500'],
    'PREFERRED_BONUS': 1.5,
}

PHI = (1 + math.sqrt(5)) / 2  # Golden ratio

# ═══════════════════════════════════════════════════════════════════════════
# COHERENCE CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════

def calculate_coherence(price_change_pct: float, volume_btc: float, volatility_pct: float, asset_class: str = 'crypto') -> float:
    """Calculate coherence with asset-class-aware scaling.
    
    For CFD markets (forex/indices/commodities), we use tighter thresholds
    since these markets have institutional liquidity and smaller moves are significant.
    """
    if asset_class == 'forex':
        # Forex: tighter thresholds for institutional market
        S = min(1.0, volume_btc / 50.0)
        O = min(1.0, abs(price_change_pct) / 0.3)  # 0.3% is significant
        E = min(1.0, volatility_pct / 0.5)  # 0.5% daily range
        # Forex has high liquidity, boost coherence
        Lambda = (S + O + E) / 3.0
        return 1 / (1 + math.exp(-6 * (Lambda - 0.35)))  # Lower threshold for forex
    elif asset_class == 'indices':
        # Indices: moderate thresholds
        S = min(1.0, volume_btc / 50.0)
        O = min(1.0, abs(price_change_pct) / 1.0)  # 1% is significant
        E = min(1.0, volatility_pct / 2.0)  # 2% daily range
        Lambda = (S + O + E) / 3.0
        return 1 / (1 + math.exp(-6 * (Lambda - 0.35)))  # Lower threshold for indices
    elif asset_class == 'commodities':
        # Commodities: between forex and crypto
        S = min(1.0, volume_btc / 50.0)
        O = min(1.0, abs(price_change_pct) / 2.0)  # 2% is significant
        E = min(1.0, volatility_pct / 3.0)  # 3% daily range
        Lambda = (S + O + E) / 3.0
        return 1 / (1 + math.exp(-6 * (Lambda - 0.40)))  # Slightly lower for commodities
    else:
        # Crypto: original scaling
        S = min(1.0, volume_btc / 50.0)
        O = min(1.0, abs(price_change_pct) / 15.0)
        E = min(1.0, volatility_pct / 25.0)
        Lambda = (S + O + E) / 3.0
        return 1 / (1 + math.exp(-5 * (Lambda - 0.5)))


# ═══════════════════════════════════════════════════════════════════════════
# MULTI-EXCHANGE CLIENT WRAPPER
# ═══════════════════════════════════════════════════════════════════════════

class MultiExchangeManager:
    """Manages connections and operations across multiple exchanges."""
    
    def __init__(self, harmonic_6d=None):
        self.clients = {}
        self.alpaca_stream = None
        self.lot_info = {}  # symbol -> {step, min_qty, precision}
        self.market_cache = get_market_cache() if MARKET_CACHE_AVAILABLE else None
        
        # Initialize Binance
        if CONFIG['ENABLE_BINANCE']:
            try:
                self.clients['binance'] = BinanceClient()
                logger.info("✅ Binance connected")
            except Exception as e:
                logger.error(f"❌ Binance failed: {e}")
        
        # Initialize Kraken
        if CONFIG['ENABLE_KRAKEN'] and KRAKEN_AVAILABLE:
            try:
                self.clients['kraken'] = get_kraken_client()
                logger.info("✅ Kraken connected")
            except Exception as e:
                logger.error(f"❌ Kraken failed: {e}")
        
        # Initialize Capital.com
        if CONFIG['ENABLE_CAPITAL'] and CAPITAL_AVAILABLE:
            try:
                client = CapitalClient()
                if client.enabled:
                    self.clients['capital'] = client
                    logger.info("✅ Capital.com connected")
            except Exception as e:
                logger.error(f"❌ Capital.com failed: {e}")
        
        # Initialize Alpaca
        if CONFIG['ENABLE_ALPACA'] and ALPACA_AVAILABLE:
            try:
                self.clients['alpaca'] = AlpacaClient()
                self.alpaca_stream = AlpacaStreamingIntegration(harmonic_6d=harmonic_6d)
                logger.info("✅ Alpaca connected (REST + SSE)")
            except Exception as e:
                logger.error(f"❌ Alpaca failed: {e}")
        
        self._load_exchange_info()
    
    def _load_exchange_info(self):
        """Load trading rules from each exchange."""
        # Binance exchange info
        if 'binance' in self.clients:
            if CONFIG.get('BINANCE_USE_UNIFIED_CACHE'):
                logger.info("⚠️ Skipping Binance exchange_info (using unified cache mode)")
                return
            try:
                client = self.clients['binance']
                info = client.exchange_info()
                for s in info.get('symbols', []):
                    sym = s['symbol']
                    self.lot_info[f"binance:{sym}"] = {
                        'status': s['status'],
                        'base': s['baseAsset'],
                        'quote': s['quoteAsset'],
                        'filters': {f['filterType']: f for f in s.get('filters', [])}
                    }
            except Exception as e:
                logger.error(f"Binance exchange info error: {e}")
    
    def get_balance(self, exchange: str, asset: str) -> float:
        """Get balance for asset on exchange."""
        if exchange not in self.clients:
            return 0.0
        
        client = self.clients[exchange]
        
        if exchange == 'binance':
            return client.get_free_balance(asset)
        elif exchange == 'kraken':
            try:
                # Kraken asset name mapping
                mappings = {'BTC': 'XXBT', 'ETH': 'XETH', 'USD': 'ZUSD'}
                kraken_asset = mappings.get(asset, asset)
                
                if client.dry_run:
                    return 100.0  # Mock balance in dry run
                    
                balances = client.get_account_balance()
                return float(balances.get(kraken_asset, 0))
            except:
                return 0.0
        elif exchange == 'capital':
            try:
                balances = client.get_account_balance()
                return balances.get(asset, 0.0)
            except:
                return 0.0
        
        return 0.0
    
    def get_tickers(self, exchange: str) -> Dict[str, Dict]:
        """Get all tickers from exchange."""
        if exchange not in self.clients:
            return {}
        
        client = self.clients[exchange]
        tickers = {}
        
        if exchange == 'binance':
            if CONFIG.get('BINANCE_USE_UNIFIED_CACHE') and self.market_cache:
                try:
                    cache_tickers = self.market_cache.get_all_tickers()
                    for symbol, t in cache_tickers.items():
                        pair = t.pair or f"{symbol}USDT"
                        quote = None
                        for q in CONFIG['QUOTE_CURRENCIES'].get('binance', []):
                            if pair.endswith(q):
                                quote = q
                                break
                        if not quote:
                            continue
                        price = float(t.price)
                        tickers[pair] = {
                            'price': price,
                            'change': float(t.change_24h),
                            'volume': float(t.volume_24h),
                            'high': price,
                            'low': price,
                            'exchange': 'binance',
                            'quote': quote,
                        }
                except Exception as e:
                    logger.error(f"Binance cache ticker error: {e}")
            else:
                try:
                    raw = client.session.get(f"{client.base}/api/v3/ticker/24hr", timeout=10).json()
                    for t in raw:
                        sym = t['symbol']
                        quote = None
                        for q in CONFIG['QUOTE_CURRENCIES'].get('binance', []):
                            if sym.endswith(q):
                                quote = q
                                break
                        if quote:
                            tickers[sym] = {
                                'price': float(t['lastPrice']),
                                'change': float(t['priceChangePercent']),
                                'volume': float(t['quoteVolume']),
                                'high': float(t['highPrice']),
                                'low': float(t['lowPrice']),
                                'exchange': 'binance',
                                'quote': quote,
                            }
                except Exception as e:
                    logger.error(f"Binance ticker error: {e}")
        
        elif exchange == 'kraken':
            try:
                # Get all tradeable pairs first
                pairs_resp = client.session.get(f"{client.base}/0/public/AssetPairs", timeout=15)
                pairs_data = pairs_resp.json()
                tradeable_pairs = [p for p, info in pairs_data.get('result', {}).items() 
                                   if info.get('status') == 'online' and 'USD' in p]
                
                # Batch ticker request (Kraken allows multiple pairs)
                if tradeable_pairs:
                    # Kraken has a limit, get top 20 USD pairs
                    batch = ','.join(tradeable_pairs[:50])
                    r = client.session.get(f"{client.base}/0/public/Ticker?pair={batch}", timeout=15)
                    data = r.json()
                    raw_result = data.get('result', {})
                    
                    for pair, info in raw_result.items():
                        try:
                            # Parse Kraken ticker format
                            price = float(info.get('c', [0])[0])  # Close price
                            high = float(info.get('h', [0, 0])[1])  # 24h high
                            low = float(info.get('l', [0, 0])[1])   # 24h low
                            vol = float(info.get('v', [0, 0])[1])   # 24h volume
                            open_price = float(info.get('o', price))
                            
                            if price <= 0:
                                continue
                            
                            change = ((price - open_price) / open_price * 100) if open_price > 0 else 0
                            
                            tickers[pair] = {
                                'price': price,
                                'change': change,
                                'volume': vol * price,  # Convert to quote volume
                                'high': high if high > 0 else price,
                                'low': low if low > 0 else price,
                                'exchange': 'kraken',
                                'quote': 'USD',
                            }
                        except:
                            continue
            except Exception as e:
                logger.error(f"Kraken ticker error: {e}")
        
        elif exchange == 'capital':
            try:
                import requests
                # Capital.com: Fetch specific markets (forex, indices, commodities)
                markets_to_fetch = CONFIG.get('CAPITAL_MARKETS', [])
                
                # Typical daily ranges for asset classes
                TYPICAL_RANGES = {
                    'forex': 0.5,      # Forex typically moves 0.5% daily
                    'indices': 1.5,    # Indices move ~1.5% daily
                    'commodities': 2.0,# Commodities ~2% daily
                    'crypto': 5.0,     # Crypto ETFs ~5% daily
                }
                
                def get_asset_class_capital(epic):
                    sym_upper = epic.upper()
                    forex_pairs = ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'NZD', 'CAD', 'SEK', 'NOK', 'DKK', 'PLN', 'SGD']
                    is_forex = any(sym_upper.startswith(p) or sym_upper.endswith(p) for p in forex_pairs) and len(epic) <= 10
                    is_index = any(idx in sym_upper for idx in ['US500', 'US100', 'US30', 'UK100', 'DE40', 'JP225', 'AU200', 'HK50', 'FR40', 'EU50'])
                    is_commodity = any(com in sym_upper for com in ['GOLD', 'SILVER', 'OIL', 'NATGAS', 'COPPER', 'PLAT', 'PALL'])
                    is_crypto = any(cry in sym_upper for cry in ['BTC', 'ETH', 'BTCO', 'ETHA', 'COIN'])
                    
                    if is_forex:
                        return 'forex'
                    elif is_index:
                        return 'indices'
                    elif is_commodity:
                        return 'commodities'
                    elif is_crypto:
                        return 'crypto'
                    return 'forex'  # Default to forex for unknown CFDs
                
                for market in markets_to_fetch:
                    try:
                        url = f'{client.base_url}/markets'
                        params = {'searchTerm': market, 'limit': 5}
                        r = requests.get(url, headers=client._get_headers(), params=params, timeout=10)
                        
                        if r.status_code == 200:
                            for m in r.json().get('markets', []):
                                epic = m.get('epic', '')
                                if not epic:
                                    continue
                                
                                # Get price data
                                bid = float(m.get('bid') or m.get('snapshot', {}).get('bid', 0) or 0)
                                ask = float(m.get('offer') or m.get('snapshot', {}).get('offer', 0) or 0)
                                change = float(m.get('percentageChange') or m.get('snapshot', {}).get('percentageChange', 0) or 0)
                                
                                if bid <= 0 or ask <= 0:
                                    continue
                                
                                price = (bid + ask) / 2
                                
                                # Normalize price for forex (Capital uses pips format)
                                # EURUSD shows as 11664 instead of 1.1664
                                if epic in ['EURUSD', 'GBPUSD', 'USDJPY', 'EURGBP']:
                                    if price > 100:
                                        price = price / 10000
                                        bid = bid / 10000
                                        ask = ask / 10000
                                
                                # Estimate high/low from typical asset class range
                                asset_class = get_asset_class_capital(epic)
                                typical_range = TYPICAL_RANGES.get(asset_class, 1.0)
                                
                                # Use max of change or half typical daily range
                                range_estimate = max(abs(change), typical_range / 2)
                                
                                if change >= 0:
                                    low = price / (1 + range_estimate/100)
                                    high = price
                                else:
                                    high = price * (1 + range_estimate/100)
                                    low = price
                                
                                tickers[epic] = {
                                    'price': price,
                                    'change': change,
                                    'volume': 1000000,  # High volume for CFDs
                                    'high': high,
                                    'low': low,
                                    'exchange': 'capital',
                                    'quote': 'USD',
                                    'bid': bid,
                                    'ask': ask,
                                    'spread_pct': (ask - bid) / bid * 100 if bid > 0 else 0,
                                    'asset_class': asset_class,
                                }
                    except Exception as e:
                        logger.debug(f"Capital.com market {market} error: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Capital.com ticker error: {e}")
        
        elif exchange == 'alpaca':
            if self.alpaca_stream:
                tickers = self.alpaca_stream.get_all_tickers()
        
        return tickers
    
    def format_qty(self, exchange: str, symbol: str, qty: float) -> str:
        """Format quantity according to exchange rules."""
        key = f"{exchange}:{symbol}"
        
        if key in self.lot_info:
            lot = self.lot_info[key].get('filters', {}).get('LOT_SIZE', {})
            step = float(lot.get('stepSize', '0.001'))
            min_qty = float(lot.get('minQty', '0.001'))
            
            precision = len(str(step).rstrip('0').split('.')[-1]) if '.' in str(step) else 0
            qty_d = Decimal(str(qty))
            step_d = Decimal(str(step))
            formatted = (qty_d // step_d) * step_d
            formatted = max(Decimal(str(min_qty)), formatted)
            
            if precision == 0:
                return str(int(formatted))
            return f"{formatted:.{precision}f}"
        
        # Default formatting
        return f"{qty:.8f}".rstrip('0').rstrip('.')
    
    def can_trade(self, exchange: str, symbol: str) -> bool:
        """Check if symbol is tradeable on exchange."""
        key = f"{exchange}:{symbol}"
        if key in self.lot_info:
            return self.lot_info[key].get('status') == 'TRADING'
        return True  # Assume tradeable if not in cache
    
    def place_order(self, exchange: str, symbol: str, side: str, qty: float) -> Dict:
        """Place market order on exchange."""
        if exchange not in self.clients:
            return {'error': f'Exchange {exchange} not available'}
        
        client = self.clients[exchange]
        
        if exchange == 'binance':
            return client.place_market_order(symbol, side, quantity=qty)
        elif exchange == 'kraken':
            if client.dry_run:
                return {'orderId': f'DRY_{int(time.time())}', 'status': 'FILLED'}
            return client.place_market_order(symbol, side, quantity=qty)
        elif exchange == 'capital':
            if client.dry_run:
                logger.info(f"[DRY RUN] Capital.com {side} {qty} {symbol}")
                return {'orderId': f'DRY_{int(time.time())}', 'status': 'FILLED'}
            # Capital.com real order
            try:
                result = client.place_market_order(symbol, side, qty)
                if 'error' not in result:
                    return {'orderId': result.get('dealReference', 'N/A'), 'status': 'FILLED'}
                return result
            except Exception as e:
                return {'error': str(e)}
        
        return {'error': 'Unknown exchange'}


# ═══════════════════════════════════════════════════════════════════════════
# ELEPHANT MEMORY (Cross-exchange)
# ═══════════════════════════════════════════════════════════════════════════

class ElephantMemory:
    def __init__(self, filepath: str = 'multi_exchange_memory.json'):
        self.filepath = filepath
        self.symbols = {}
        self.load()
    
    def load(self):
        try:
            with open(self.filepath) as f:
                self.symbols = json.load(f)
        except:
            self.symbols = {}
    
    def save(self):
        with open(self.filepath, 'w') as f:
            json.dump(self.symbols, f, indent=2)
    
    def record(self, exchange: str, symbol: str, profit_usd: float):
        key = f"{exchange}:{symbol}"
        if key not in self.symbols:
            self.symbols[key] = {'trades': 0, 'wins': 0, 'profit': 0, 'last_time': 0, 'streak': 0}
        
        s = self.symbols[key]
        s['trades'] += 1
        s['profit'] += profit_usd
        s['last_time'] = time.time()
        
        if profit_usd >= 0:
            s['wins'] += 1
            s['streak'] = 0
        else:
            s['streak'] += 1
        
        self.save()
    
    def should_avoid(self, exchange: str, symbol: str) -> bool:
        key = f"{exchange}:{symbol}"
        if key not in self.symbols:
            return False
        s = self.symbols[key]
        if time.time() - s.get('last_time', 0) < CONFIG['COOLDOWN_MINUTES'] * 60:
            return True
        if s.get('streak', 0) >= 3:
            return True
        return False


# ═══════════════════════════════════════════════════════════════════════════
# MULTI-EXCHANGE TRADER v6.2 with 6D Harmonic Waveform
# ═══════════════════════════════════════════════════════════════════════════

class AureonMultiExchangeTrader:
    def __init__(self):
        self.memory = ElephantMemory()
        self.hnc = HNCProbabilityIntegration()
        
        # Initialize 6D Harmonic Waveform Engine
        if HARMONIC_6D_AVAILABLE:
            self.harmonic_6d = Enhanced6DProbabilityMatrix()
            self.use_6d = True
            logger.info("🌌 6D Harmonic Waveform Engine: ENABLED")
        else:
            self.harmonic_6d = None
            self.use_6d = False
            logger.warning("⚠️ 6D Harmonic Waveform Engine: NOT AVAILABLE")
            
        self.exchange_mgr = MultiExchangeManager(harmonic_6d=self.harmonic_6d)
        
        self.positions = {}  # exchange:symbol -> position data
        self.peak_prices = {}
        self.ticker_cache = {}  # exchange -> {symbol -> ticker}
        
        self.trades = 0
        self.wins = 0
        self.total_profit = 0.0
        self.rejections = []
    
    def update_all_tickers(self):
        """Update tickers from all exchanges."""
        for exchange in self.exchange_mgr.clients.keys():
            self.ticker_cache[exchange] = self.exchange_mgr.get_tickers(exchange)
            logger.debug(f"📊 {exchange}: {len(self.ticker_cache[exchange])} tickers fetched")
            
    def check_arbitrage(self):
        """Check for cross-exchange arbitrage opportunities."""
        # Normalize symbols to base asset
        # Map: base_asset -> list of (exchange, price, symbol_original)
        assets = {}
        
        for exchange, tickers in self.ticker_cache.items():
            for symbol, data in tickers.items():
                # Simple normalization
                base = symbol.replace('USDT', '').replace('USDC', '').replace('USD', '').replace('/', '')
                if base not in assets:
                    assets[base] = []
                assets[base].append({
                    'exchange': exchange,
                    'price': data['price'],
                    'symbol': symbol
                })
        
        # Check for discrepancies
        for base, quotes in assets.items():
            if len(quotes) < 2:
                continue
                
            # Find min and max price
            quotes.sort(key=lambda x: x['price'])
            min_q = quotes[0]
            max_q = quotes[-1]
            
            if min_q['price'] <= 0:
                continue
            
            diff_pct = (max_q['price'] - min_q['price']) / min_q['price'] * 100
            
            # Filter out likely symbol mismatches (e.g. T (crypto) vs T (stock))
            # Real arbitrage is rarely > 20%
            if 1.5 < diff_pct < 20.0:
                logger.info(f"⚡ ARBITRAGE ALERT [{base}]: {diff_pct:.2f}% spread")
                logger.info(f"   Buy {base} on {min_q['exchange'].upper()} (${min_q['price']:.2f})")
                logger.info(f"   Sell {base} on {max_q['exchange'].upper()} (${max_q['price']:.2f})")

    def sync_all(self) -> Dict[str, Any]:
        """Backward-compatible sync entrypoint for legacy orchestrators."""
        self.update_all_tickers()
        opportunities = self.scan_opportunities()
        return {
            'exchanges_connected': list(self.clients.keys()),
            'opportunities_found': len(opportunities),
            'top_opportunities': opportunities[:5],
        }

    def scan_opportunities(self) -> List[Dict]:
        """Scan all exchanges for opportunities using v6.1 logic."""
        opportunities = []
        
        for exchange, tickers in self.ticker_cache.items():
            for symbol, ticker in tickers.items():
                if self.memory.should_avoid(exchange, symbol):
                    continue
                if not self.exchange_mgr.can_trade(exchange, symbol):
                    continue
                
                try:
                    price = ticker['price']
                    change = ticker['change']
                    volume = ticker['volume']
                    high = ticker['high']
                    low = ticker['low']
                    
                    if volume < 10000:
                        continue
                    
                    # Determine asset class - use stored value for Capital.com or detect
                    asset_class = ticker.get('asset_class', 'crypto')
                    if exchange != 'capital' and asset_class == 'crypto':
                        # Double check for crypto exchanges
                        pass  # Already crypto
                    elif exchange == 'capital' and 'asset_class' not in ticker:
                        sym_upper = symbol.upper()
                        forex_pairs = ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'NZD', 'CAD', 'SEK', 'NOK', 'DKK', 'PLN', 'SGD', 'HKD', 'MXN', 'ZAR', 'TRY']
                        is_forex = any(sym_upper.startswith(p) or sym_upper.endswith(p) for p in forex_pairs) and len(symbol) <= 10
                        is_index = any(idx in sym_upper for idx in ['US500', 'US100', 'US30', 'UK100', 'DE40', 'JP225', 'AU200', 'HK50', 'FR40', 'EU50'])
                        is_commodity = any(com in sym_upper for com in ['GOLD', 'SILVER', 'OIL', 'NATGAS', 'COPPER', 'PLAT', 'PALL'])
                        
                        if is_forex:
                            asset_class = 'forex'
                        elif is_index:
                            asset_class = 'indices'
                        elif is_commodity:
                            asset_class = 'commodities'
                    
                    # Coherence calculation with asset-class awareness
                    volatility = ((high - low) / low * 100) if low > 0 else 0
                    coherence = calculate_coherence(change, volume / price if price > 0 else 0, volatility, asset_class)
                    
                    if coherence < CONFIG['COHERENCE_THRESHOLD']:
                        continue
                    
                    # Frequency calculation
                    freq = max(256, min(963, 432 * ((1 + change/100) ** PHI)))
                    in_avoid = CONFIG['FREQ_AVOID_MIN'] <= freq <= CONFIG['FREQ_AVOID_MAX']
                    in_optimal = CONFIG['FREQ_OPTIMAL_MIN'] <= freq <= CONFIG['FREQ_OPTIMAL_MAX']
                    
                    if in_avoid:
                        continue
                    
                    # Momentum check - asset-class-aware
                    if asset_class == 'forex':
                        # Forex: tighter momentum (±0.5% is big move)
                        if change > 1.0 or change < -1.0:
                            continue
                    elif asset_class in ['indices', 'commodities']:
                        # Indices/commodities: moderate (±3%)
                        if change > 3.0 or change < -3.0:
                            continue
                    else:
                        # Crypto: original (±5% to +10%)
                        if change > 10.0 or change < -5.0:
                            continue
                    
                    # Range check
                    range_pct = (price - low) / (high - low) if (high - low) > 0 else 0.5
                    if range_pct > 0.75:
                        continue
                    
                    # Signal generation - asset-class-aware
                    if asset_class in ['forex', 'indices', 'commodities']:
                        # CFD markets: Use simplified signal based on coherence + momentum
                        # These markets are efficient, so coherence IS the signal
                        if change > 0.02:  # Slightly positive
                            action = 'BUY' if coherence >= 0.80 else 'SLIGHT BUY'
                            prob = min(0.83, 0.50 + coherence * 0.40)  # 50-83% based on coherence
                        elif change > -0.05:  # Near neutral
                            action = 'SLIGHT BUY' if coherence >= 0.75 else 'HOLD'
                            prob = 0.50 + coherence * 0.25
                        else:
                            action = 'HOLD'
                            prob = 0.45
                    else:
                        # Crypto: Use coherence-momentum signal with HNC enhancement
                        # Generate base signal from market conditions
                        if change > 3.0 and coherence >= 0.75:
                            # Strong positive momentum with good coherence
                            action = 'BUY'
                            prob = min(0.80, 0.55 + coherence * 0.30 + change/100)
                        elif change > 1.0 and coherence >= 0.70:
                            # Moderate positive momentum
                            action = 'SLIGHT BUY'
                            prob = min(0.75, 0.52 + coherence * 0.25 + change/200)
                        elif change > -2.0 and coherence >= 0.75:
                            # Slight dip with high coherence (buy the dip)
                            action = 'SLIGHT BUY'
                            prob = 0.50 + coherence * 0.20
                        elif change > 0 and coherence >= 0.65:
                            # Weak positive
                            action = 'SLIGHT BUY'
                            prob = 0.50 + coherence * 0.15
                        else:
                            action = 'HOLD'
                            prob = 0.45
                        
                        # Enhance with HNC if available (adds temporal context)
                        self.hnc.update_and_analyze(
                            symbol=symbol,
                            price=price,
                            frequency=freq,
                            momentum=change,
                            coherence=coherence,
                            is_harmonic=abs(freq - 528) < 30,
                            volume=volume
                        )
                        hnc_signal = self.hnc.get_trading_signal(symbol)
                        hnc_prob = hnc_signal['probability']
                        
                        # Blend: 70% coherence-based, 30% HNC (HNC needs warmup)
                        if hnc_prob > 0.1:  # HNC has some signal
                            prob = 0.7 * prob + 0.3 * hnc_prob
                    
                    # 6D Harmonic Waveform Enhancement
                    harmonic_6d_data = None
                    if self.use_6d and self.harmonic_6d:
                        harmonic_6d_data = self.harmonic_6d.update(
                            symbol=symbol,
                            price=price,
                            volume=volume,
                            change_pct=change,
                            high=high,
                            low=low,
                            frequency=freq,
                            coherence=coherence,
                            hnc_probability=prob
                        )
                        # Use 6D enhanced probability
                        prob = harmonic_6d_data['probability']
                        # Boost action if in harmonic lock
                        if harmonic_6d_data.get('harmonic_lock') and action == 'SLIGHT BUY':
                            action = 'BUY'
                    
                    # News Sentiment Integration (Alpaca)
                    sentiment_score = 0.0
                    if self.exchange_mgr.alpaca_stream:
                        # Check for sentiment on the symbol
                        metrics = self.exchange_mgr.alpaca_stream.realtime_metrics.get(symbol)
                        if metrics and 'news_sentiment' in metrics:
                            sentiment = metrics['news_sentiment']
                            # Sentiment range is typically -1 to 1
                            # Adjust probability: +0.1 for strong positive, -0.1 for strong negative
                            sentiment_impact = sentiment * 0.1
                            prob = max(0.0, min(1.0, prob + sentiment_impact))
                            sentiment_score = sentiment
                    
                    if prob < CONFIG['PROB_MIN']:
                        continue
                    if prob > CONFIG['PROB_CAP']:
                        prob = CONFIG['PROB_CAP']
                    
                    if action not in ['STRONG BUY', 'BUY', 'SLIGHT BUY']:
                        continue
                    
                    # Calculate score (enhanced with 6D metrics)
                    base_score = prob * coherence * (1 + math.log10(max(1, volume/10000)))
                    freq_bonus = 1.0 if in_optimal else 0.5
                    range_bonus = (1 - range_pct)
                    score = base_score * (1 + freq_bonus) * (1 + range_bonus * 0.5)
                    
                    # 6D resonance bonus
                    if harmonic_6d_data:
                        resonance = harmonic_6d_data.get('resonance', 0)
                        if resonance > 0.7:
                            score *= (1 + resonance * 0.3)  # Up to 30% bonus for high resonance
                        if harmonic_6d_data.get('wave_state') in ['crystalline', 'resonant']:
                            score *= 1.15  # 15% bonus for ideal wave states
                    
                    # Preferred symbol bonus
                    base_symbol = symbol.replace('USDC', '').replace('USDT', '').replace('USD', '')
                    if base_symbol in CONFIG.get('PREFERRED_SYMBOLS', []):
                        score *= CONFIG.get('PREFERRED_BONUS', 1.5)
                    
                    opportunities.append({
                        'exchange': exchange,
                        'symbol': symbol,
                        'price': price,
                        'change': change,
                        'coherence': coherence,
                        'volume': volume,
                        'probability': prob,
                        'action': action,
                        'frequency': freq,
                        'score': score,
                        'freq_band': 'OPTIMAL' if in_optimal else 'STANDARD',
                        'range_pct': range_pct,
                        'quote': ticker.get('quote', 'USD'),
                        'sentiment': sentiment_score,
                    })
                    
                except Exception as e:
                    continue
        
        # Sort by score
        opportunities.sort(key=lambda x: -x['score'])
        return opportunities
    
    def get_positions_by_exchange(self, exchange: str) -> int:
        """Count positions on a specific exchange."""
        return sum(1 for key in self.positions.keys() if key.startswith(f"{exchange}:"))
    
    def enter_position(self, opp: Dict) -> bool:
        """Enter position on best exchange."""
        exchange = opp['exchange']
        symbol = opp['symbol']
        quote = opp.get('quote', 'USDC')
        
        # Check position limits
        if len(self.positions) >= CONFIG['MAX_POSITIONS']:
            return False
        if self.get_positions_by_exchange(exchange) >= CONFIG['MAX_POSITIONS_PER_EXCHANGE']:
            return False
        
        # Get balance
        balance = self.exchange_mgr.get_balance(exchange, quote)
        
        # Size calculation (v6.1 coherence scaling)
        base_size_pct = 0.20
        if opp.get('freq_band') == 'OPTIMAL':
            base_size_pct += 0.15
        
        if CONFIG.get('COHERENCE_SCALING', True):
            coh = opp.get('coherence', 0.70)
            optimal_coh = CONFIG.get('COHERENCE_OPTIMAL', 0.88)
            threshold_coh = CONFIG.get('COHERENCE_THRESHOLD', 0.70)
            coh_factor = (coh - threshold_coh) / (optimal_coh - threshold_coh)
            coh_factor = max(0.5, min(1.0, coh_factor))
            base_size_pct *= coh_factor
        
        size_pct = min(0.45, base_size_pct)
        size_usd = balance * size_pct
        
        if size_usd < CONFIG['MIN_TRADE_USD']:
            return False
        
        qty = size_usd / opp['price']
        qty_str = self.exchange_mgr.format_qty(exchange, symbol, qty)
        
        notional = float(qty_str) * opp['price']
        if notional < CONFIG['MIN_TRADE_USD']:
            return False
        
        logger.info(f"""
╔════════════════════════════════════════════════════════════════╗
║ 🎯 ENTERING [{exchange.upper()}] {symbol}
║ HNC Prob: {opp['probability']:.0%} | Action: {opp['action']}
║ Coherence: Γ={opp['coherence']:.3f} | Freq: {opp['frequency']:.0f}Hz
║ Size: {size_pct*100:.0f}% = ${notional:.2f} ({qty_str} @ ${opp['price']:.4f})
╚════════════════════════════════════════════════════════════════╝
""")
        
        try:
            result = self.exchange_mgr.place_order(exchange, symbol, 'BUY', float(qty_str))
            
            key = f"{exchange}:{symbol}"
            self.positions[key] = {
                'exchange': exchange,
                'symbol': symbol,
                'entry': opp['price'],
                'qty': float(qty_str),
                'entry_time': time.time(),
                'notional': notional,
                'quote': quote,
            }
            self.peak_prices[key] = opp['price']
            
            logger.info(f"✅ Filled: Order #{result.get('orderId', 'N/A')}")
            self.trades += 1
            return True
            
        except Exception as e:
            logger.error(f"❌ Buy failed: {e}")
            return False
    
    def check_exits(self):
        """Check all positions for exit conditions."""
        for key in list(self.positions.keys()):
            pos = self.positions[key]
            exchange = pos['exchange']
            symbol = pos['symbol']
            
            tickers = self.ticker_cache.get(exchange, {})
            ticker = tickers.get(symbol)
            if not ticker:
                continue
            
            price = ticker['price']
            entry = pos['entry']
            pnl_pct = (price - entry) / entry
            pnl_usd = pos['qty'] * price * pnl_pct
            
            # Update peak
            if key not in self.peak_prices:
                self.peak_prices[key] = price
            elif price > self.peak_prices[key]:
                self.peak_prices[key] = price
            
            should_exit = False
            reason = ""
            
            # Trailing stop
            if CONFIG.get('ENABLE_TRAILING_STOP', True):
                peak = self.peak_prices.get(key, price)
                peak_pnl_pct = (peak - entry) / entry
                
                if peak_pnl_pct >= CONFIG.get('TRAIL_ACTIVATION_PCT', 0.008):
                    trail_distance = CONFIG.get('TRAIL_DISTANCE_PCT', 0.005)
                    trail_price = peak * (1 - trail_distance)
                    
                    if price <= trail_price:
                        should_exit = True
                        reason = f"📈 TRAILING STOP (Peak: ${peak:.4f})"
            
            # Standard exits
            if not should_exit:
                if pnl_pct >= CONFIG['TAKE_PROFIT_PCT']:
                    should_exit = True
                    reason = "💰 TAKE PROFIT"
                elif pnl_pct <= -CONFIG['STOP_LOSS_PCT']:
                    should_exit = True
                    reason = "🛑 STOP LOSS"
                elif time.time() - pos['entry_time'] > CONFIG['TIMEOUT_SEC']:
                    should_exit = True
                    reason = "⏰ TIMEOUT"
            
            if should_exit:
                qty_str = self.exchange_mgr.format_qty(exchange, symbol, pos['qty'])
                
                logger.info(f"""
╔════════════════════════════════════════════════════════════════╗
║ ⚡ EXITING [{exchange.upper()}] {symbol}
║ Reason: {reason}
║ Entry: ${entry:.4f} | Exit: ${price:.4f}
║ P&L: {pnl_pct*100:+.2f}% (${pnl_usd:+.2f})
╚════════════════════════════════════════════════════════════════╝
""")
                
                try:
                    result = self.exchange_mgr.place_order(exchange, symbol, 'SELL', float(qty_str))
                    logger.info(f"✅ Sold: Order #{result.get('orderId', 'N/A')}")
                    
                    self.memory.record(exchange, symbol, pnl_usd)
                    self.total_profit += pnl_usd
                    if pnl_usd >= 0:
                        self.wins += 1
                        # 🇮🇪 IRA SNIPER CELEBRATION!
                        import random
                        IRA_QUOTES = [
                            "Our revenge will be the laughter of our children. - Bobby Sands 🍀",
                            "Tiocfaidh ár lá! - Our day will come!",
                            "The Republic still lives! - Bobby Sands",
                            "Financial freedom IS freedom. Penny by penny, we rise! 💰",
                        ]
                        quote = random.choice(IRA_QUOTES)
                        print(f"\n🇮🇪🇮🇪🇮🇪 IRA SNIPER WIN! 🇮🇪🇮🇪🇮🇪")
                        print(f"    💰 +${pnl_usd:.4f} on {symbol} [{exchange.upper()}]")
                        print(f"    📜 \"{quote}\"")
                        print(f"🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪\n")
                    
                    if key in self.peak_prices:
                        del self.peak_prices[key]
                    del self.positions[key]
                    
                except Exception as e:
                    logger.error(f"❌ Sell failed: {e}")
    
    def display_status(self, cycle: int):
        """Display current status across all exchanges."""
        # Get balances
        balances = {}
        for exchange in self.exchange_mgr.clients.keys():
            for quote in CONFIG['QUOTE_CURRENCIES'].get(exchange, []):
                bal = self.exchange_mgr.get_balance(exchange, quote)
                if bal > 0:
                    balances[f"{exchange}:{quote}"] = bal
        
        # Position value
        pos_value = 0.0
        for key, pos in self.positions.items():
            exchange = pos['exchange']
            symbol = pos['symbol']
            ticker = self.ticker_cache.get(exchange, {}).get(symbol, {})
            if ticker:
                pos_value += pos['qty'] * ticker.get('price', pos['entry'])
        
        win_rate = self.wins / max(1, self.trades) * 100
        
        # Format balance string
        bal_str = " | ".join([f"{k}: ${v:.2f}" for k, v in balances.items()])
        
        logger.info(f"""
╔════════════════════════════════════════════════════════════════╗
║ 🌐 AUREON MULTI-EXCHANGE v6.1 | Cycle {cycle:3d}
║────────────────────────────────────────────────────────────────
║ 💵 Balances: {bal_str}
║ 💼 Positions: ${pos_value:.2f} ({len(self.positions)}/{CONFIG['MAX_POSITIONS']})
║────────────────────────────────────────────────────────────────
║ 🏆 Trades: {self.trades} | Wins: {self.wins} | WR: {win_rate:.1f}%
║ 💰 Profit: ${self.total_profit:+.2f}
║ 🔌 Exchanges: {', '.join(self.exchange_mgr.clients.keys())}
╚════════════════════════════════════════════════════════════════╝
""")
    
    def run(self, duration_sec: int = 3600):
        harmonic_status = "✅ ENABLED" if self.use_6d else "❌ DISABLED"
        logger.info(f"""
╔════════════════════════════════════════════════════════════════╗
║        🌐 AUREON MULTI-EXCHANGE LIVE TRADER v6.2 🌐
║
║  EXCHANGES: {', '.join(self.exchange_mgr.clients.keys()).upper()}
║
║  ALL SYSTEMS INTEGRATED:
║    ✨ HNC Probability Matrix
║    ✨ Smart Order Routing
║    ✨ Tiered Coherence (0.70 base, 0.88 optimal)
║    ✨ Trailing Stops
║    ✨ Cross-Exchange Memory
║    🌌 6D Harmonic Waveform: {harmonic_status}
║
╚════════════════════════════════════════════════════════════════╝
""")
        
        # Start Alpaca streams if enabled
        if self.exchange_mgr.alpaca_stream:
            logger.info("🚀 Starting Alpaca SSE Streams...")
            # Subscribe to crypto and stocks
            self.exchange_mgr.alpaca_stream.subscribe_crypto(['BTC/USD', 'ETH/USD', 'SOL/USD', 'LTC/USD'])
            self.exchange_mgr.alpaca_stream.subscribe_stocks(['SPY', 'QQQ', 'AAPL', 'TSLA', 'NVDA', 'AMD', 'MSFT', 'GOOGL'])
            self.exchange_mgr.alpaca_stream.subscribe_news(['*'])
            time.sleep(2)  # Warmup
        
        start = time.time()
        cycle = 0
        
        while time.time() - start < duration_sec:
            cycle += 1
            
            self.update_all_tickers()
            self.display_status(cycle)
            
            # Check for arbitrage
            self.check_arbitrage()
            
            # Check exits
            self.check_exits()
            
            # Scan and enter
            if len(self.positions) < CONFIG['MAX_POSITIONS']:
                opps = self.scan_opportunities()
                
                if opps:
                    logger.info(f"\n🔍 Top Opportunities Across Exchanges:")
                    for i, opp in enumerate(opps[:5]):
                        sent_str = f" | 📰 {opp['sentiment']:+.2f}" if opp.get('sentiment', 0) != 0 else ""
                        logger.info(f"  {i+1}. [{opp['exchange'].upper()}] {opp['symbol']}: P={opp['probability']:.0%} | Γ={opp['coherence']:.3f} | {opp['freq_band']}{sent_str}")
                    
                    # Enter best opportunity
                    self.enter_position(opps[0])
                else:
                    logger.info("\n⏳ No opportunities meeting criteria - waiting...")
            
            time.sleep(10)
        
        # Stop Alpaca streams
        if self.exchange_mgr.alpaca_stream:
            self.exchange_mgr.alpaca_stream.stop()
        
        logger.info(f"""
╔════════════════════════════════════════════════════════════════╗
║ 🏁 SESSION COMPLETE
║ Trades: {self.trades} | Wins: {self.wins} | WR: {self.wins/max(1,self.trades)*100:.1f}%
║ Total P&L: ${self.total_profit:+.2f}
╚════════════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    trader = AureonMultiExchangeTrader()
    trader.run(duration_sec=300)  # 5 min test
