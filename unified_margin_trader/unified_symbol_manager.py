"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║  🔤 UNIFIED SYMBOL MANAGER - Multi-Exchange Symbol Normalization & Quantity Precision  ║
║                                                                                         ║
║  Each exchange has different:                                                           ║
║    - Symbol formats (BTC/USD vs BTCUSD vs XXBTZUSD)                                     ║
║    - API calls for getting symbols                                                      ║
║    - Quantity precision requirements                                                    ║
║    - Minimum order sizes                                                                ║
║                                                                                         ║
║  This manager provides:                                                                 ║
║    - Unified symbol lists for each exchange                                             ║
║    - Symbol format conversion between exchanges                                         ║
║    - Quantity precision formatting per exchange/symbol                                  ║
║    - Minimum order validation                                                           ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import time
import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from decimal import Decimal, ROUND_DOWN, InvalidOperation
from dataclasses import dataclass, field, asdict
from pathlib import Path

# Windows UTF-8 fix (MANDATORY)
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════════════
# 📊 SYMBOL FORMAT DEFINITIONS PER EXCHANGE
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class ExchangeSymbolFormat:
    """Defines how an exchange formats its trading pairs."""
    name: str
    separator: str  # '/', '', '-'
    base_prefix: str  # 'X' for Kraken crypto, '' for others
    quote_prefix: str  # 'Z' for Kraken fiat, '' for others
    btc_alias: str  # 'XBT' for Kraken, 'BTC' for others
    case: str  # 'upper', 'lower', 'mixed'
    # Quote currency preferences in order
    preferred_quotes: List[str] = field(default_factory=list)
    # Restrictions
    restricted_quotes: Set[str] = field(default_factory=set)

# Exchange format definitions
EXCHANGE_FORMATS = {
    'kraken': ExchangeSymbolFormat(
        name='kraken',
        separator='',
        base_prefix='',  # Actually X for crypto but handled in _to_kraken
        quote_prefix='',  # Actually Z for fiat but handled
        btc_alias='XBT',
        case='upper',
        preferred_quotes=['USD', 'USDC', 'USDT', 'EUR', 'GBP'],
        restricted_quotes=set()
    ),
    'binance': ExchangeSymbolFormat(
        name='binance',
        separator='',
        base_prefix='',
        quote_prefix='',
        btc_alias='BTC',
        case='upper',
        preferred_quotes=['USDC', 'USDT', 'BTC', 'EUR', 'GBP'],  # USDC first for UK
        restricted_quotes={'USDT'}  # USDT restricted for UK accounts
    ),
    'alpaca': ExchangeSymbolFormat(
        name='alpaca',
        separator='/',
        base_prefix='',
        quote_prefix='',
        btc_alias='BTC',
        case='upper',
        preferred_quotes=['USD', 'USDC'],
        restricted_quotes=set()
    ),
    'capital': ExchangeSymbolFormat(
        name='capital',
        separator='',
        base_prefix='',
        quote_prefix='',
        btc_alias='BTC',
        case='upper',
        preferred_quotes=['USD', 'EUR', 'GBP'],
        restricted_quotes=set()
    )
}

@dataclass
class SymbolInfo:
    """Complete symbol information for trading."""
    exchange: str
    symbol: str  # Exchange-specific format
    base: str  # Base asset (BTC, ETH, etc.)
    quote: str  # Quote asset (USD, USDC, etc.)
    canonical: str  # Canonical format: BASE/QUOTE
    min_qty: float = 0.0
    max_qty: float = float('inf')
    step_size: float = 0.00000001
    min_notional: float = 0.0
    price_precision: int = 8
    qty_precision: int = 8
    lot_decimals: int = 8
    status: str = 'TRADING'
    
    def format_quantity(self, qty: float) -> str:
        """Format quantity to exchange's precision requirements."""
        if qty <= 0:
            return '0'
        
        # Round down to step size
        try:
            d_qty = Decimal(str(qty))
            d_step = Decimal(str(self.step_size))
            
            # Round down to nearest step
            rounded = (d_qty / d_step).to_integral_value(rounding=ROUND_DOWN) * d_step
            
            # Format with appropriate precision
            if self.lot_decimals == 0:
                return str(int(rounded))
            
            format_str = f'{{:.{self.lot_decimals}f}}'
            formatted = format_str.format(float(rounded))
            
            # Strip trailing zeros but keep at least one decimal if needed
            if '.' in formatted:
                formatted = formatted.rstrip('0').rstrip('.')
            
            return formatted or '0'
        except (InvalidOperation, ValueError):
            return str(qty)
    
    def validate_quantity(self, qty: float, price: float = 0.0) -> Tuple[bool, str]:
        """Validate quantity against exchange limits."""
        if qty < self.min_qty:
            return False, f"Quantity {qty} below minimum {self.min_qty}"
        
        if qty > self.max_qty:
            return False, f"Quantity {qty} above maximum {self.max_qty}"
        
        if price > 0 and self.min_notional > 0:
            notional = qty * price
            if notional < self.min_notional:
                return False, f"Notional {notional:.4f} below minimum {self.min_notional}"
        
        return True, "OK"


class UnifiedSymbolManager:
    """
    Manages symbol lists and formatting across all exchanges.
    
    Features:
        - Fetch and cache symbol lists per exchange
        - Convert symbols between exchange formats
        - Format quantities to exchange precision
        - Validate orders against exchange limits
    """
    
    # Singleton instance
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        
        # Symbol caches per exchange
        self._symbol_cache: Dict[str, Dict[str, SymbolInfo]] = {
            'kraken': {},
            'binance': {},
            'alpaca': {},
            'capital': {}
        }
        
        # Cache timestamps
        self._cache_times: Dict[str, float] = {}
        self._cache_ttl = 300  # 5 minutes
        
        # UK mode for Binance restrictions
        self.uk_mode = os.getenv('BINANCE_UK_MODE', 'true').lower() == 'true'
        
        # Exchange clients (lazy loaded)
        self._kraken = None
        self._binance = None
        self._alpaca = None
        self._capital = None
        
        # Common crypto bases for quick lookup
        self._crypto_bases = {
            'BTC', 'ETH', 'LTC', 'XRP', 'SOL', 'DOGE', 'AVAX', 'DOT', 'LINK', 'UNI',
            'AAVE', 'BCH', 'XLM', 'ATOM', 'ALGO', 'MATIC', 'SHIB', 'PEPE', 'TRUMP',
            'ADA', 'BNB', 'XMR', 'ETC', 'FIL', 'NEAR', 'APT', 'OP', 'ARB', 'CRV',
            'MKR', 'SNX', 'COMP', 'YFI', 'SUSHI', 'GRT', 'BAT', 'ZRX', 'ENJ', 'MANA',
            'SAND', 'AXS', 'GALA', 'IMX', 'LRC', 'XTZ', 'BONK', 'WIF', 'TRX', 'XBT',
            'FLOKI', 'RENDER', 'INJ', 'TIA', 'SEI', 'SUI', 'BLUR', 'JTO', 'PYTH',
            'RNDR', 'FET', 'AGIX', 'OCEAN', 'TAO', 'ORDI', 'WLD', 'STRK', 'MEME',
        }
        
        # Quote currencies
        self._quote_currencies = {'USD', 'USDT', 'USDC', 'EUR', 'GBP', 'BTC', 'ETH', 'BNB'}
        
        logger.info("🔤 Unified Symbol Manager initialized")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 🔌 EXCHANGE CLIENT ACCESS
    # ═══════════════════════════════════════════════════════════════════════════════
    
    @property
    def kraken(self):
        if self._kraken is None:
            try:
                from aureon.exchanges.kraken_client import get_kraken_client
                self._kraken = get_kraken_client()
            except Exception as e:
                logger.debug(f"Kraken client not available: {e}")
        return self._kraken
    
    @property
    def binance(self):
        if self._binance is None:
            try:
                from aureon.exchanges.binance_client import get_binance_client
                self._binance = get_binance_client()
            except Exception as e:
                logger.debug(f"Binance client not available: {e}")
        return self._binance
    
    @property
    def alpaca(self):
        if self._alpaca is None:
            try:
                from aureon.exchanges.alpaca_client import AlpacaClient
                self._alpaca = AlpacaClient()
            except Exception as e:
                logger.debug(f"Alpaca client not available: {e}")
        return self._alpaca
    
    @property
    def capital(self):
        if self._capital is None:
            try:
                from aureon.exchanges.capital_client import CapitalClient
                self._capital = CapitalClient()
            except Exception as e:
                logger.debug(f"Capital client not available: {e}")
        return self._capital
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 📋 SYMBOL LIST LOADING
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def _is_cache_valid(self, exchange: str) -> bool:
        """Check if cache is still valid."""
        cache_time = self._cache_times.get(exchange, 0)
        return time.time() - cache_time < self._cache_ttl
    
    def load_kraken_symbols(self, force_refresh: bool = False) -> Dict[str, SymbolInfo]:
        """Load all tradeable symbols from Kraken."""
        if not force_refresh and self._is_cache_valid('kraken'):
            return self._symbol_cache['kraken']
        
        symbols: Dict[str, SymbolInfo] = {}
        
        try:
            client = self.kraken
            if not client:
                return symbols
            
            # Get asset pairs
            pairs = client._load_asset_pairs() if hasattr(client, '_load_asset_pairs') else {}
            
            for internal, info in pairs.items():
                if internal.endswith('.d'):  # Skip dark pools
                    continue
                
                altname = info.get('altname', internal)
                base_raw = info.get('base', '')
                quote_raw = info.get('quote', '')
                wsname = info.get('wsname', altname)
                
                # Clean up Kraken's X/Z prefixes
                base = base_raw[1:] if len(base_raw) == 4 and base_raw[0] in ('X', 'Z') else base_raw
                quote = quote_raw[1:] if len(quote_raw) == 4 and quote_raw[0] in ('X', 'Z') else quote_raw
                
                # BTC/XBT normalization
                if base == 'XBT':
                    base = 'BTC'
                if quote == 'XBT':
                    quote = 'BTC'
                
                # Get precision info
                lot_decimals = int(info.get('lot_decimals', 8))
                pair_decimals = int(info.get('pair_decimals', 5))
                step_size = 10 ** (-lot_decimals)
                
                ordermin = info.get('ordermin')
                try:
                    min_qty = float(ordermin) if ordermin else step_size
                except:
                    min_qty = step_size
                
                costmin = info.get('costmin')
                try:
                    min_notional = float(costmin) if costmin else 0.5
                except:
                    min_notional = 0.5
                
                canonical = f"{base}/{quote}"
                
                sym_info = SymbolInfo(
                    exchange='kraken',
                    symbol=altname,  # Use altname for API calls
                    base=base,
                    quote=quote,
                    canonical=canonical,
                    min_qty=min_qty,
                    step_size=step_size,
                    min_notional=min_notional,
                    price_precision=pair_decimals,
                    qty_precision=lot_decimals,
                    lot_decimals=lot_decimals
                )
                
                # Index by multiple keys
                symbols[altname] = sym_info
                symbols[internal] = sym_info
                symbols[canonical] = sym_info
                symbols[f"{base}{quote}"] = sym_info
            
            self._symbol_cache['kraken'] = symbols
            self._cache_times['kraken'] = time.time()
            logger.info(f"🐙 Kraken: Loaded {len(pairs)} tradeable pairs")
            
        except Exception as e:
            logger.error(f"Error loading Kraken symbols: {e}")
        
        return symbols
    
    def load_binance_symbols(self, force_refresh: bool = False) -> Dict[str, SymbolInfo]:
        """Load all tradeable symbols from Binance."""
        if not force_refresh and self._is_cache_valid('binance'):
            return self._symbol_cache['binance']
        
        symbols: Dict[str, SymbolInfo] = {}
        
        try:
            client = self.binance
            if not client:
                return symbols
            
            info = client.exchange_info()
            exchange_symbols = info.get('symbols', [])
            
            for sym in exchange_symbols:
                if sym.get('status') != 'TRADING':
                    continue
                if not sym.get('isSpotTradingAllowed', True):
                    continue
                
                symbol = sym.get('symbol', '')
                base = sym.get('baseAsset', '')
                quote = sym.get('quoteAsset', '')
                
                if not symbol or not base or not quote:
                    continue
                
                # Skip USDT pairs for UK mode
                if self.uk_mode and quote == 'USDT':
                    continue
                
                # Parse filters
                min_qty = 0.0
                max_qty = float('inf')
                step_size = 0.00000001
                min_notional = 0.0
                price_precision = 8
                
                for f in sym.get('filters', []):
                    if f.get('filterType') == 'LOT_SIZE':
                        min_qty = float(f.get('minQty', 0))
                        max_qty = float(f.get('maxQty', float('inf')))
                        step_size = float(f.get('stepSize', 0.00000001))
                    elif f.get('filterType') == 'NOTIONAL':
                        min_notional = float(f.get('minNotional', 0))
                    elif f.get('filterType') == 'PRICE_FILTER':
                        tick_size = float(f.get('tickSize', 0.00000001))
                        price_precision = max(0, -int(Decimal(str(tick_size)).as_tuple().exponent))
                
                # Calculate lot decimals from step size
                lot_decimals = max(0, -int(Decimal(str(step_size)).as_tuple().exponent)) if step_size > 0 else 8
                
                canonical = f"{base}/{quote}"
                
                sym_info = SymbolInfo(
                    exchange='binance',
                    symbol=symbol,
                    base=base,
                    quote=quote,
                    canonical=canonical,
                    min_qty=min_qty,
                    max_qty=max_qty,
                    step_size=step_size,
                    min_notional=min_notional,
                    price_precision=price_precision,
                    qty_precision=lot_decimals,
                    lot_decimals=lot_decimals
                )
                
                symbols[symbol] = sym_info
                symbols[canonical] = sym_info
            
            self._symbol_cache['binance'] = symbols
            self._cache_times['binance'] = time.time()
            
            uk_note = " (UK mode - USDT pairs excluded)" if self.uk_mode else ""
            logger.info(f"🟡 Binance: Loaded {len(exchange_symbols)} tradeable pairs{uk_note}")
            
        except Exception as e:
            logger.error(f"Error loading Binance symbols: {e}")
        
        return symbols
    
    def load_alpaca_symbols(self, force_refresh: bool = False) -> Dict[str, SymbolInfo]:
        """Load all tradeable symbols from Alpaca."""
        if not force_refresh and self._is_cache_valid('alpaca'):
            return self._symbol_cache['alpaca']
        
        symbols: Dict[str, SymbolInfo] = {}
        
        try:
            client = self.alpaca
            if not client:
                return symbols
            
            # Get crypto assets
            if hasattr(client, 'get_tradable_crypto_symbols'):
                crypto_symbols = client.get_tradable_crypto_symbols() or []
            else:
                crypto_symbols = []
                try:
                    assets = client.get_assets(status='active', asset_class='crypto') or []
                    for asset in assets:
                        if asset.get('tradable'):
                            crypto_symbols.append(asset.get('symbol', ''))
                except:
                    pass
            
            for sym in crypto_symbols:
                if not sym:
                    continue
                
                # Normalize to slash format
                if hasattr(client, '_normalize_pair_symbol'):
                    normalized = client._normalize_pair_symbol(sym)
                else:
                    normalized = sym
                
                if not normalized or '/' not in normalized:
                    # Try to add slash
                    for quote in ['USDT', 'USDC', 'USD']:
                        if sym.upper().endswith(quote):
                            base = sym.upper()[:-len(quote)]
                            normalized = f"{base}/{quote}"
                            break
                    else:
                        normalized = f"{sym}/USD"
                
                parts = normalized.split('/')
                if len(parts) != 2:
                    continue
                
                base, quote = parts[0].upper(), parts[1].upper()
                canonical = f"{base}/{quote}"
                
                sym_info = SymbolInfo(
                    exchange='alpaca',
                    symbol=normalized,  # Alpaca uses slash format
                    base=base,
                    quote=quote,
                    canonical=canonical,
                    min_qty=0.00001,  # Alpaca default minimums
                    step_size=0.00001,
                    min_notional=1.0,
                    lot_decimals=5
                )
                
                symbols[normalized] = sym_info
                symbols[canonical] = sym_info
                symbols[f"{base}{quote}"] = sym_info
            
            self._symbol_cache['alpaca'] = symbols
            self._cache_times['alpaca'] = time.time()
            logger.info(f"🦙 Alpaca: Loaded {len(crypto_symbols)} tradeable crypto pairs")
            
        except Exception as e:
            logger.error(f"Error loading Alpaca symbols: {e}")
        
        return symbols
    
    def load_capital_symbols(self, force_refresh: bool = False) -> Dict[str, SymbolInfo]:
        """Load all tradeable symbols from Capital.com."""
        if not force_refresh and self._is_cache_valid('capital'):
            return self._symbol_cache['capital']
        
        symbols: Dict[str, SymbolInfo] = {}
        
        try:
            client = self.capital
            if not client or not client.enabled:
                return symbols
            
            markets = client.get_all_markets() or []
            
            for market in markets:
                epic = market.get('epic', '')
                instrument_name = market.get('instrumentName', '')
                
                if not epic:
                    continue
                
                # Capital uses epics like "BTCUSD", "ETHUSD"
                # Parse base/quote
                base = None
                quote = None
                
                for q in ['USD', 'EUR', 'GBP']:
                    if epic.endswith(q):
                        base = epic[:-len(q)]
                        quote = q
                        break
                
                if not base:
                    # Try to guess from instrument name
                    continue
                
                canonical = f"{base}/{quote}"
                
                # Capital.com doesn't expose lot size via API; use sensible defaults
                sym_info = SymbolInfo(
                    exchange='capital',
                    symbol=epic,
                    base=base,
                    quote=quote,
                    canonical=canonical,
                    min_qty=0.001,  # Capital default
                    step_size=0.001,
                    min_notional=10.0,  # Usually $10 minimum
                    lot_decimals=3
                )
                
                symbols[epic] = sym_info
                symbols[canonical] = sym_info
                symbols[f"{base}{quote}"] = sym_info
            
            self._symbol_cache['capital'] = symbols
            self._cache_times['capital'] = time.time()
            logger.info(f"🌐 Capital: Loaded {len(markets)} tradeable markets")
            
        except Exception as e:
            logger.error(f"Error loading Capital symbols: {e}")
        
        return symbols
    
    def load_all_symbols(self, force_refresh: bool = False) -> Dict[str, Dict[str, SymbolInfo]]:
        """Load symbols from all exchanges."""
        return {
            'kraken': self.load_kraken_symbols(force_refresh),
            'binance': self.load_binance_symbols(force_refresh),
            'alpaca': self.load_alpaca_symbols(force_refresh),
            'capital': self.load_capital_symbols(force_refresh)
        }
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 🔄 SYMBOL CONVERSION
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def parse_symbol(self, symbol: str) -> Tuple[str, str]:
        """Parse a symbol into base and quote currency."""
        s = symbol.upper().replace(' ', '').replace('-', '/')
        
        # If already has separator
        if '/' in s:
            parts = s.split('/')
            if len(parts) == 2:
                return parts[0], parts[1]
        
        # Try to find quote currency (longest first)
        for quote in ['USDT', 'USDC', 'USD', 'EUR', 'GBP', 'BTC', 'ETH', 'BNB']:
            if s.endswith(quote) and len(s) > len(quote):
                base = s[:-len(quote)]
                # Handle Kraken's XBT
                if base == 'XBT':
                    base = 'BTC'
                return base, quote
        
        # Last resort: assume USD quote
        return s, 'USD'
    
    def to_canonical(self, symbol: str) -> str:
        """Convert any symbol format to canonical BASE/QUOTE format."""
        base, quote = self.parse_symbol(symbol)
        return f"{base}/{quote}"
    
    def to_exchange_format(self, symbol: str, exchange: str) -> str:
        """Convert a symbol to exchange-specific format."""
        base, quote = self.parse_symbol(symbol)
        exchange = exchange.lower()
        
        fmt = EXCHANGE_FORMATS.get(exchange)
        if not fmt:
            return f"{base}{quote}"
        
        # BTC/XBT handling
        if fmt.btc_alias == 'XBT' and base == 'BTC':
            base = 'XBT'
        
        # Format with separator
        if fmt.separator:
            return f"{base}{fmt.separator}{quote}"
        else:
            return f"{base}{quote}"
    
    def to_kraken(self, symbol: str) -> str:
        """Convert symbol to Kraken format."""
        return self.to_exchange_format(symbol, 'kraken')
    
    def to_binance(self, symbol: str, prefer_usdc: bool = True) -> str:
        """Convert symbol to Binance format."""
        base, quote = self.parse_symbol(symbol)
        
        # For UK mode, prefer USDC over USDT
        if self.uk_mode and quote == 'USDT':
            quote = 'USDC'
        elif self.uk_mode and quote == 'USD':
            quote = 'USDC' if prefer_usdc else 'EUR'
        
        return f"{base}{quote}"
    
    def to_alpaca(self, symbol: str) -> str:
        """Convert symbol to Alpaca format (BASE/QUOTE)."""
        base, quote = self.parse_symbol(symbol)
        
        # Alpaca uses USD for crypto
        if quote in ['USDT', 'USDC']:
            quote = 'USD'
        
        return f"{base}/{quote}"
    
    def to_capital(self, symbol: str) -> str:
        """Convert symbol to Capital.com format."""
        base, quote = self.parse_symbol(symbol)
        
        # Capital uses USD directly
        if quote in ['USDT', 'USDC']:
            quote = 'USD'
        
        return f"{base}{quote}"
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 📊 SYMBOL INFO & QUANTITY FORMATTING
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def get_symbol_info(self, symbol: str, exchange: str) -> Optional[SymbolInfo]:
        """Get symbol info for a specific exchange."""
        exchange = exchange.lower()
        
        # Load symbols if not cached
        if exchange == 'kraken':
            symbols = self.load_kraken_symbols()
        elif exchange == 'binance':
            symbols = self.load_binance_symbols()
        elif exchange == 'alpaca':
            symbols = self.load_alpaca_symbols()
        elif exchange == 'capital':
            symbols = self.load_capital_symbols()
        else:
            return None
        
        # Try direct lookup
        canonical = self.to_canonical(symbol)
        exchange_format = self.to_exchange_format(symbol, exchange)
        
        for key in [symbol, canonical, exchange_format, symbol.upper()]:
            if key in symbols:
                return symbols[key]
        
        return None
    
    def format_quantity(self, qty: float, symbol: str, exchange: str) -> str:
        """Format quantity to exchange's precision requirements."""
        info = self.get_symbol_info(symbol, exchange)
        
        if info:
            return info.format_quantity(qty)
        
        # Fallback: use sensible defaults per exchange
        defaults = {
            'kraken': 8,
            'binance': 8,
            'alpaca': 5,
            'capital': 3
        }
        
        decimals = defaults.get(exchange.lower(), 8)
        
        try:
            d_qty = Decimal(str(qty))
            format_str = f'{{:.{decimals}f}}'
            formatted = format_str.format(float(d_qty))
            if '.' in formatted:
                formatted = formatted.rstrip('0').rstrip('.')
            return formatted or '0'
        except:
            return str(qty)
    
    def validate_order(self, qty: float, symbol: str, exchange: str, price: float = 0.0) -> Tuple[bool, str]:
        """Validate order quantity against exchange limits."""
        info = self.get_symbol_info(symbol, exchange)
        
        if info:
            return info.validate_quantity(qty, price)
        
        # No info available, assume valid
        return True, "OK (no validation data)"
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 🎯 QUICK ACCESS METHODS
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def get_all_symbols(self, exchange: str) -> List[str]:
        """Get all tradeable symbols for an exchange."""
        exchange = exchange.lower()
        
        if exchange == 'kraken':
            symbols = self.load_kraken_symbols()
        elif exchange == 'binance':
            symbols = self.load_binance_symbols()
        elif exchange == 'alpaca':
            symbols = self.load_alpaca_symbols()
        elif exchange == 'capital':
            symbols = self.load_capital_symbols()
        else:
            return []
        
        # Return unique canonical symbols
        seen = set()
        result = []
        for info in symbols.values():
            if info.canonical not in seen:
                seen.add(info.canonical)
                result.append(info.symbol)
        
        return sorted(result)
    
    def find_best_pair(self, base: str, exchange: str, preferred_quotes: List[str] = None) -> Optional[str]:
        """Find the best available trading pair for a base asset."""
        exchange = exchange.lower()
        base = base.upper()
        
        # Default quote preferences per exchange
        if not preferred_quotes:
            if exchange == 'binance' and self.uk_mode:
                preferred_quotes = ['USDC', 'EUR', 'GBP', 'BTC']
            elif exchange == 'binance':
                preferred_quotes = ['USDT', 'USDC', 'BTC', 'EUR']
            elif exchange == 'kraken':
                preferred_quotes = ['USD', 'USDC', 'USDT', 'EUR']
            elif exchange == 'alpaca':
                preferred_quotes = ['USD', 'USDC']
            else:
                preferred_quotes = ['USD', 'EUR', 'GBP']
        
        if exchange == 'kraken':
            symbols = self.load_kraken_symbols()
        elif exchange == 'binance':
            symbols = self.load_binance_symbols()
        elif exchange == 'alpaca':
            symbols = self.load_alpaca_symbols()
        elif exchange == 'capital':
            symbols = self.load_capital_symbols()
        else:
            return None
        
        # Try each preferred quote in order
        for quote in preferred_quotes:
            canonical = f"{base}/{quote}"
            if canonical in symbols:
                return symbols[canonical].symbol
        
        # Fallback: find any pair with this base
        for info in symbols.values():
            if info.base == base:
                return info.symbol
        
        return None
    
    def get_min_order_size(self, symbol: str, exchange: str, price: float = 0.0) -> float:
        """Get minimum order size for a symbol."""
        info = self.get_symbol_info(symbol, exchange)
        
        if not info:
            return 0.0
        
        # Return the larger of min_qty or (min_notional / price)
        min_qty = info.min_qty
        
        if price > 0 and info.min_notional > 0:
            notional_min = info.min_notional / price
            min_qty = max(min_qty, notional_min)
        
        return min_qty
    
    def print_status(self) -> str:
        """Print symbol manager status."""
        lines = [
            "",
            "═" * 80,
            "🔤 UNIFIED SYMBOL MANAGER - STATUS",
            "═" * 80,
            ""
        ]
        
        for exchange in ['kraken', 'binance', 'alpaca', 'capital']:
            symbols = self._symbol_cache.get(exchange, {})
            unique_count = len(set(s.canonical for s in symbols.values())) if symbols else 0
            cache_time = self._cache_times.get(exchange, 0)
            age = int(time.time() - cache_time) if cache_time else 0
            
            icons = {'kraken': '🐙', 'binance': '🟡', 'alpaca': '🦙', 'capital': '🌐'}
            icon = icons.get(exchange, '📊')
            
            if unique_count > 0:
                lines.append(f"   {icon} {exchange.title()}: {unique_count} pairs (cached {age}s ago)")
            else:
                lines.append(f"   {icon} {exchange.title()}: Not loaded")
        
        lines.append("")
        lines.append("=" * 80)
        
        return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════════════════════════════════
# 🎯 SINGLETON ACCESS
# ═══════════════════════════════════════════════════════════════════════════════════════

_symbol_manager: Optional[UnifiedSymbolManager] = None

def get_symbol_manager() -> UnifiedSymbolManager:
    """Get the singleton symbol manager instance."""
    global _symbol_manager
    if _symbol_manager is None:
        _symbol_manager = UnifiedSymbolManager()
    return _symbol_manager


# ═══════════════════════════════════════════════════════════════════════════════════════
# 🧪 TEST / DEMO
# ═══════════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n🔤 UNIFIED SYMBOL MANAGER - TEST\n")
    print("=" * 80)
    
    mgr = get_symbol_manager()
    
    # Test symbol parsing
    test_symbols = ['BTCUSD', 'BTC/USD', 'ETHUSDT', 'XBT/USD', 'DOGEUSDC']
    print("\n📊 Symbol Parsing Test:")
    for sym in test_symbols:
        base, quote = mgr.parse_symbol(sym)
        canonical = mgr.to_canonical(sym)
        print(f"   {sym:12} → base={base}, quote={quote}, canonical={canonical}")
    
    # Test format conversion
    print("\n🔄 Format Conversion Test (BTC/USD):")
    for exchange in ['kraken', 'binance', 'alpaca', 'capital']:
        formatted = mgr.to_exchange_format('BTC/USD', exchange)
        print(f"   {exchange:10}: {formatted}")
    
    # Load symbols
    print("\n📋 Loading Symbol Lists...")
    mgr.load_all_symbols()
    print(mgr.print_status())
    
    # Test quantity formatting
    print("\n📏 Quantity Formatting Test (0.123456789 BTC):")
    for exchange in ['kraken', 'binance', 'alpaca', 'capital']:
        formatted = mgr.format_quantity(0.123456789, 'BTC/USD', exchange)
        print(f"   {exchange:10}: {formatted}")
    
    # Find best pairs
    print("\n🎯 Best Pair Discovery:")
    for base in ['BTC', 'ETH', 'SOL', 'DOGE']:
        for exchange in ['kraken', 'binance', 'alpaca']:
            best = mgr.find_best_pair(base, exchange)
            print(f"   {base:5} on {exchange:8}: {best or 'NOT FOUND'}")
    
    print("\n✅ Symbol Manager Test Complete!")
