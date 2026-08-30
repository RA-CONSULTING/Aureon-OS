#!/usr/bin/env python3
"""
🎯 ALPACA OPTIONS CLIENT - OPTIONS TRADING SUPPORT 🎯
═══════════════════════════════════════════════════════════════════════════════

Full options trading integration for Alpaca:
  - Fetch option contracts (calls/puts)
  - Get options quotes and Greeks
  - Place options orders (buy/sell calls/puts)
  - Track options positions
  - Handle exercise/assignment
  - Multi-leg strategies (spreads)

Trading Levels:
  Level 0: Disabled
  Level 1: Covered calls, cash-secured puts
  Level 2: Level 1 + Buy calls/puts  
  Level 3: Levels 1,2 + Call/put spreads

Gary Leckey | January 2026
═══════════════════════════════════════════════════════════════════════════════
"""

try:
    from aureon.core.aureon_baton_link import link_system as _baton_link
    _baton_link(__name__)
except Exception:
    pass
import os
import re
import sys
import threading
import time
import json
import logging
import requests
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from aureon.governance.economic_boundary import (
    EconomicGovernanceBlocked,
    _claim_economic_transport_context,
    _economic_transport_body_digest,
)

# Load .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Windows UTF-8 fix (opt-in only; avoid import-time stdio mutation)
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        def _is_buffer_valid(stream):
            if not hasattr(stream, 'buffer'):
                return False
            try:
                return stream.buffer is not None and not stream.buffer.closed
            except (ValueError, AttributeError):
                return False
        force_stdio_wrap = os.getenv("ALPACA_FORCE_UTF8_STDIO", "false").lower() == "true"
        if force_stdio_wrap and _is_buffer_valid(sys.stdout) and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if force_stdio_wrap and _is_buffer_valid(sys.stderr) and not _is_utf8_wrapper(sys.stderr):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

logger = logging.getLogger(__name__)

ALPACA_OPTIONS_LIVE_BASE = "https://api.alpaca.markets"
ALPACA_OPTIONS_PAPER_BASE = "https://paper-api.alpaca.markets"
_SAFE_ALPACA_PATH_ID = re.compile(r"[A-Za-z0-9._~-]{1,160}")


def _is_alpaca_options_mutation_path(method: str, path: str) -> bool:
    normalized_method = str(method).strip().upper()
    if not isinstance(path, str) or not path.startswith("/"):
        return False
    if "?" in path or "#" in path or "//" in path:
        return False
    if normalized_method == "POST" and path == "/v2/orders":
        return True
    parts = path.split("/")
    if (
        normalized_method == "DELETE"
        and len(parts) == 4
        and parts[1:3] == ["v2", "orders"]
    ):
        return _SAFE_ALPACA_PATH_ID.fullmatch(parts[3]) is not None
    if (
        normalized_method == "POST"
        and len(parts) == 5
        and parts[1:3] == ["v2", "positions"]
        and parts[4] == "exercise"
    ):
        return _SAFE_ALPACA_PATH_ID.fullmatch(parts[3]) is not None
    return False


@dataclass(frozen=True, slots=True)
class _OptionsMutationDispatch:
    method: str
    path: str
    body_digest: str

# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

class OptionType(Enum):
    CALL = "call"
    PUT = "put"


class OptionStyle(Enum):
    AMERICAN = "american"
    EUROPEAN = "european"


class TradingLevel(Enum):
    DISABLED = 0
    COVERED = 1      # Covered calls, cash-secured puts
    BUYING = 2       # Level 1 + Buy calls/puts
    SPREADS = 3      # Levels 1,2 + Call/put spreads


@dataclass
class OptionContract:
    """Represents an option contract."""
    id: str
    symbol: str                    # e.g., "AAPL240119C00100000"
    name: str                      # e.g., "AAPL Jan 19 2024 100 Call"
    status: str                    # "active", "inactive"
    tradable: bool
    expiration_date: str           # "2024-01-19"
    root_symbol: str               # "AAPL"
    underlying_symbol: str         # "AAPL"
    underlying_asset_id: str
    option_type: OptionType        # call or put
    style: OptionStyle             # american or european
    strike_price: float
    size: int                      # Contract multiplier (usually 100)
    open_interest: int
    close_price: float
    close_price_date: str
    
    @classmethod
    def from_api(cls, data: Dict) -> 'OptionContract':
        """Create from API response."""
        return cls(
            id=data.get('id', ''),
            symbol=data.get('symbol', ''),
            name=data.get('name', ''),
            status=data.get('status', 'active'),
            tradable=data.get('tradable', False),
            expiration_date=data.get('expiration_date', ''),
            root_symbol=data.get('root_symbol', ''),
            underlying_symbol=data.get('underlying_symbol', ''),
            underlying_asset_id=data.get('underlying_asset_id', ''),
            option_type=OptionType(data.get('type', 'call')),
            style=OptionStyle(data.get('style', 'american')),
            strike_price=float(data.get('strike_price', 0)),
            size=int(data.get('size', 100)),
            open_interest=int(data.get('open_interest', 0) or 0),
            close_price=float(data.get('close_price', 0) or 0),
            close_price_date=data.get('close_price_date', ''),
        )


@dataclass
class OptionQuote:
    """Real-time option quote with Greeks."""
    symbol: str
    bid: float
    ask: float
    bid_size: int
    ask_size: int
    last_price: float
    volume: int
    timestamp: str
    # Greeks (if available)
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    implied_volatility: Optional[float] = None
    
    @property
    def mid_price(self) -> float:
        """Calculate mid price."""
        if self.bid > 0 and self.ask > 0:
            return (self.bid + self.ask) / 2
        return self.last_price or 0
    
    @property
    def spread(self) -> float:
        """Calculate bid-ask spread."""
        if self.bid > 0 and self.ask > 0:
            return self.ask - self.bid
        return 0
    
    @property
    def spread_pct(self) -> float:
        """Calculate spread as percentage."""
        if self.mid_price > 0:
            return (self.spread / self.mid_price) * 100
        return 0


@dataclass
class OptionPosition:
    """Represents an options position."""
    symbol: str
    qty: int
    side: str                      # "long" or "short"
    avg_entry_price: float
    current_price: float
    market_value: float
    cost_basis: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    contract: Optional[OptionContract] = None
    
    @property
    def is_call(self) -> bool:
        return 'C' in self.symbol[-9:-8] if len(self.symbol) > 9 else False
    
    @property
    def is_put(self) -> bool:
        return 'P' in self.symbol[-9:-8] if len(self.symbol) > 9 else False


@dataclass
class OptionOrder:
    """Represents an options order."""
    id: str
    symbol: str
    qty: int
    side: str                      # "buy" or "sell"
    order_type: str                # "market", "limit", "stop", "stop_limit"
    time_in_force: str             # Must be "day" for options
    limit_price: Optional[float]
    stop_price: Optional[float]
    status: str
    filled_qty: int
    filled_avg_price: float
    created_at: str
    updated_at: str
    
    @classmethod
    def from_api(cls, data: Dict) -> 'OptionOrder':
        """Create from API response."""
        return cls(
            id=data.get('id', ''),
            symbol=data.get('symbol', ''),
            qty=int(data.get('qty', 0)),
            side=data.get('side', ''),
            order_type=data.get('type', 'market'),
            time_in_force=data.get('time_in_force', 'day'),
            limit_price=float(data['limit_price']) if data.get('limit_price') else None,
            stop_price=float(data['stop_price']) if data.get('stop_price') else None,
            status=data.get('status', ''),
            filled_qty=int(data.get('filled_qty', 0) or 0),
            filled_avg_price=float(data.get('filled_avg_price', 0) or 0),
            created_at=data.get('created_at', ''),
            updated_at=data.get('updated_at', ''),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# ALPACA OPTIONS CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

class AlpacaOptionsClient:
    """
    🎯 Complete Alpaca Options Trading Client
    
    Features:
    - Contract discovery and filtering
    - Real-time quotes with Greeks
    - Order placement (market, limit, stop, stop-limit)
    - Position tracking
    - Exercise/assignment handling
    - Multi-leg strategies support
    """
    
    def __init__(self):
        """Initialize the options client."""
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.secret_key = os.getenv('ALPACA_SECRET_KEY')
        self.use_paper = os.getenv('ALPACA_PAPER', 'false').lower() == 'true'
        self.dry_run = os.getenv('ALPACA_DRY_RUN', 'false').lower() == 'true'
        
        if self.use_paper:
            self.base_url = ALPACA_OPTIONS_PAPER_BASE
        else:
            self.base_url = ALPACA_OPTIONS_LIVE_BASE
            
        self.data_url = "https://data.alpaca.markets"
        
        self.session = requests.Session()
        self.session.headers.update({
            'APCA-API-KEY-ID': self.api_key,
            'APCA-API-SECRET-KEY': self.secret_key,
            'Content-Type': 'application/json',
        })
        
        self.timeout = 10.0
        self.trading_level: Optional[TradingLevel] = None
        self._economic_dispatch_lock = threading.RLock()
        self._economic_dispatches: Dict[object, _OptionsMutationDispatch] = {}
        
        # Cache for contracts
        self._contract_cache: Dict[str, OptionContract] = {}
        self._cache_expiry: float = 0
        
        logger.info("🎯 Alpaca Options Client initialized")
        logger.info(f"   Mode: {'PAPER' if self.use_paper else 'LIVE'}")

    def _prepare_options_mutation(
        self,
        *,
        method: str,
        path: str,
        body: Dict[str, Any],
    ) -> object:
        normalized_method = str(method).strip().upper()
        if not _is_alpaca_options_mutation_path(normalized_method, path):
            raise EconomicGovernanceBlocked(
                "canonical_alpaca_options_mutation_method_and_path_required"
            )
        if not isinstance(body, dict):
            raise EconomicGovernanceBlocked(
                "exact_alpaca_options_mutation_body_required"
            )
        if self.dry_run:
            raise EconomicGovernanceBlocked(
                "alpaca_options_dry_run_mutation_transport_forbidden"
            )
        expected_base = (
            ALPACA_OPTIONS_PAPER_BASE
            if self.use_paper
            else ALPACA_OPTIONS_LIVE_BASE
        )
        if self.base_url != expected_base:
            raise EconomicGovernanceBlocked(
                "canonical_alpaca_options_environment_endpoint_required"
            )
        if self.use_paper:
            body_digest = _economic_transport_body_digest(body)
        else:
            body_digest = _claim_economic_transport_context(
                method=normalized_method,
                path=path,
                body=body,
            )
        dispatch = object()
        state = _OptionsMutationDispatch(
            method=normalized_method,
            path=path,
            body_digest=body_digest,
        )
        with self._economic_dispatch_lock:
            self._economic_dispatches[dispatch] = state
        return dispatch

    def _discard_options_mutation_dispatch(self, dispatch: object | None) -> None:
        if dispatch is None:
            return
        with self._economic_dispatch_lock:
            self._economic_dispatches.pop(dispatch, None)

    def _options_mutation_request(
        self,
        method: str,
        path: str,
        *,
        body: Dict[str, Any],
        _economic_dispatch: object | None = None,
    ) -> requests.Response:
        """Burn an exact one-use capability immediately before HTTP."""

        normalized_method = str(method).strip().upper()
        if not _is_alpaca_options_mutation_path(normalized_method, path):
            raise EconomicGovernanceBlocked(
                "canonical_alpaca_options_mutation_method_and_path_required"
            )
        expected_base = (
            ALPACA_OPTIONS_PAPER_BASE
            if self.use_paper
            else ALPACA_OPTIONS_LIVE_BASE
        )
        if self.base_url != expected_base or self.dry_run:
            raise EconomicGovernanceBlocked(
                "canonical_alpaca_options_environment_endpoint_required"
            )
        with self._economic_dispatch_lock:
            state = self._economic_dispatches.pop(_economic_dispatch, None)
        if state is None:
            raise EconomicGovernanceBlocked(
                "alpaca_options_mutation_dispatch_capability_required"
            )
        if not isinstance(body, dict):
            raise EconomicGovernanceBlocked(
                "exact_alpaca_options_mutation_body_required"
            )
        observed = _OptionsMutationDispatch(
            method=normalized_method,
            path=path,
            body_digest=_economic_transport_body_digest(body),
        )
        if observed != state:
            raise EconomicGovernanceBlocked(
                "exact_alpaca_options_mutation_method_path_body_required"
            )
        return self.session.request(
            normalized_method,
            f"{self.base_url}{path}",
            json=body or None,
            timeout=self.timeout,
        )
        
    # ═══════════════════════════════════════════════════════════════════════
    # ACCOUNT & CONFIGURATION
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_trading_level(self) -> TradingLevel:
        """Get the account's options trading level."""
        try:
            resp = self.session.get(
                f"{self.base_url}/v2/account",
                timeout=self.timeout
            )
            resp.raise_for_status()
            data = resp.json()
            
            level = int(data.get('options_trading_level', 0))
            self.trading_level = TradingLevel(level)
            
            logger.info(f"🎯 Options Trading Level: {self.trading_level.name} ({level})")
            return self.trading_level
            
        except Exception as e:
            logger.error(f"Failed to get trading level: {e}")
            return TradingLevel.DISABLED
    
    def get_options_buying_power(self) -> float:
        """Get available options buying power."""
        try:
            resp = self.session.get(
                f"{self.base_url}/v2/account",
                timeout=self.timeout
            )
            resp.raise_for_status()
            data = resp.json()
            
            return float(data.get('options_buying_power', 0) or 0)
            
        except Exception as e:
            logger.error(f"Failed to get options buying power: {e}")
            return 0.0
    
    # ═══════════════════════════════════════════════════════════════════════
    # CONTRACT DISCOVERY
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_contracts(
        self,
        underlying_symbol: str,
        expiration_date: Optional[str] = None,
        expiration_date_gte: Optional[str] = None,
        expiration_date_lte: Optional[str] = None,
        option_type: Optional[OptionType] = None,
        strike_price_gte: Optional[float] = None,
        strike_price_lte: Optional[float] = None,
        limit: int = 100
    ) -> List[OptionContract]:
        """
        Get option contracts for an underlying symbol.
        
        Args:
            underlying_symbol: The stock symbol (e.g., "AAPL")
            expiration_date: Exact expiration date (YYYY-MM-DD)
            expiration_date_gte: Expiration >= this date
            expiration_date_lte: Expiration <= this date
            option_type: Filter by CALL or PUT
            strike_price_gte: Strike price >= this value
            strike_price_lte: Strike price <= this value
            limit: Max contracts to return
            
        Returns:
            List of OptionContract objects
        """
        try:
            params = {
                'underlying_symbols': underlying_symbol.upper(),
                'limit': limit,
            }
            
            if expiration_date:
                params['expiration_date'] = expiration_date
            if expiration_date_gte:
                params['expiration_date_gte'] = expiration_date_gte
            if expiration_date_lte:
                params['expiration_date_lte'] = expiration_date_lte
            if option_type:
                params['type'] = option_type.value
            if strike_price_gte:
                params['strike_price_gte'] = str(strike_price_gte)
            if strike_price_lte:
                params['strike_price_lte'] = str(strike_price_lte)
            
            resp = self.session.get(
                f"{self.base_url}/v2/options/contracts",
                params=params,
                timeout=self.timeout
            )
            resp.raise_for_status()
            data = resp.json()
            
            contracts = []
            for item in data.get('option_contracts', []):
                contract = OptionContract.from_api(item)
                contracts.append(contract)
                self._contract_cache[contract.symbol] = contract
            
            logger.info(f"🎯 Found {len(contracts)} contracts for {underlying_symbol}")
            return contracts
            
        except Exception as e:
            logger.error(f"Failed to get contracts: {e}")
            return []
    
    def get_contract(self, symbol_or_id: str) -> Optional[OptionContract]:
        """Get a specific option contract by symbol or ID."""
        # Check cache first
        if symbol_or_id in self._contract_cache:
            return self._contract_cache[symbol_or_id]
        
        try:
            resp = self.session.get(
                f"{self.base_url}/v2/options/contracts/{symbol_or_id}",
                timeout=self.timeout
            )
            resp.raise_for_status()
            data = resp.json()
            
            contract = OptionContract.from_api(data)
            self._contract_cache[contract.symbol] = contract
            return contract
            
        except Exception as e:
            logger.error(f"Failed to get contract {symbol_or_id}: {e}")
            return None
    
    def find_nearest_expiry(
        self,
        underlying_symbol: str,
        min_days: int = 1,
        max_days: int = 45
    ) -> Optional[str]:
        """Find the nearest expiration date for a symbol."""
        today = datetime.now()
        min_date = (today + timedelta(days=min_days)).strftime('%Y-%m-%d')
        max_date = (today + timedelta(days=max_days)).strftime('%Y-%m-%d')
        
        contracts = self.get_contracts(
            underlying_symbol=underlying_symbol,
            expiration_date_gte=min_date,
            expiration_date_lte=max_date,
            limit=1
        )
        
        if contracts:
            return contracts[0].expiration_date
        return None
    
    def get_chain(
        self,
        underlying_symbol: str,
        expiration_date: str,
        near_money_range: float = 0.1
    ) -> Dict[str, List[OptionContract]]:
        """
        Get the full option chain for a symbol/expiration.
        
        Args:
            underlying_symbol: Stock symbol
            expiration_date: Expiration date (YYYY-MM-DD)
            near_money_range: % range around current price (0.1 = ±10%)
            
        Returns:
            Dict with 'calls' and 'puts' lists
        """
        contracts = self.get_contracts(
            underlying_symbol=underlying_symbol,
            expiration_date=expiration_date,
            limit=1000
        )
        
        calls = [c for c in contracts if c.option_type == OptionType.CALL]
        puts = [c for c in contracts if c.option_type == OptionType.PUT]
        
        # Sort by strike price
        calls.sort(key=lambda x: x.strike_price)
        puts.sort(key=lambda x: x.strike_price)
        
        return {
            'calls': calls,
            'puts': puts,
            'expiration': expiration_date,
            'underlying': underlying_symbol,
        }
    
    # ═══════════════════════════════════════════════════════════════════════
    # MARKET DATA
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_quote(self, symbol: str) -> Optional[OptionQuote]:
        """Get real-time quote for an option contract."""
        try:
            resp = self.session.get(
                f"{self.data_url}/v1beta1/options/quotes/latest",
                params={'symbols': symbol},
                timeout=self.timeout
            )
            resp.raise_for_status()
            data = resp.json()
            
            quote_data = data.get('quotes', {}).get(symbol, {})
            if not quote_data:
                return None
            
            return OptionQuote(
                symbol=symbol,
                bid=float(quote_data.get('bp', 0) or 0),
                ask=float(quote_data.get('ap', 0) or 0),
                bid_size=int(quote_data.get('bs', 0) or 0),
                ask_size=int(quote_data.get('as', 0) or 0),
                last_price=float(quote_data.get('p', 0) or 0),
                volume=int(quote_data.get('v', 0) or 0),
                timestamp=quote_data.get('t', ''),
            )
            
        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            return None
    
    def get_quotes(self, symbols: List[str]) -> Dict[str, OptionQuote]:
        """Get quotes for multiple option contracts."""
        try:
            resp = self.session.get(
                f"{self.data_url}/v1beta1/options/quotes/latest",
                params={'symbols': ','.join(symbols)},
                timeout=self.timeout
            )
            resp.raise_for_status()
            data = resp.json()
            
            quotes = {}
            for sym, quote_data in data.get('quotes', {}).items():
                quotes[sym] = OptionQuote(
                    symbol=sym,
                    bid=float(quote_data.get('bp', 0) or 0),
                    ask=float(quote_data.get('ap', 0) or 0),
                    bid_size=int(quote_data.get('bs', 0) or 0),
                    ask_size=int(quote_data.get('as', 0) or 0),
                    last_price=float(quote_data.get('p', 0) or 0),
                    volume=int(quote_data.get('v', 0) or 0),
                    timestamp=quote_data.get('t', ''),
                )
            
            return quotes
            
        except Exception as e:
            logger.error(f"Failed to get quotes: {e}")
            return {}
    
    # ═══════════════════════════════════════════════════════════════════════
    # ORDER PLACEMENT
    # ═══════════════════════════════════════════════════════════════════════
    
    def place_order(
        self,
        symbol: str,
        qty: int,
        side: str,
        order_type: str = 'limit',
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
    ) -> Optional[OptionOrder]:
        """
        Place an options order.
        
        Args:
            symbol: Option contract symbol (e.g., "AAPL240119C00100000")
            qty: Number of contracts (must be whole number)
            side: "buy" or "sell"
            order_type: "market", "limit", "stop", or "stop_limit"
            limit_price: Limit price (required for limit/stop_limit)
            stop_price: Stop price (required for stop/stop_limit)
            
        Returns:
            OptionOrder if successful, None otherwise
        """
        # Validate inputs
        if qty <= 0 or qty != int(qty):
            logger.error(f"❌ Options qty must be positive whole number: {qty}")
            return None
        
        if order_type in ['limit', 'stop_limit'] and limit_price is None:
            logger.error("❌ Limit price required for limit/stop_limit orders")
            return None
        
        if order_type in ['stop', 'stop_limit'] and stop_price is None:
            logger.error("❌ Stop price required for stop/stop_limit orders")
            return None
        
        try:
            order_data = {
                'symbol': symbol,
                'qty': str(int(qty)),
                'side': side,
                'type': order_type,
                'time_in_force': 'day',  # Options must use 'day'
            }
            
            if limit_price is not None:
                order_data['limit_price'] = str(round(limit_price, 2))
            if stop_price is not None:
                order_data['stop_price'] = str(round(stop_price, 2))
            
            logger.info(f"🎯 Placing options order: {side} {qty}x {symbol}")
            
            dispatch = self._prepare_options_mutation(
                method="POST", path="/v2/orders", body=order_data
            )
            try:
                resp = self._options_mutation_request(
                    "POST",
                    "/v2/orders",
                    body=order_data,
                    _economic_dispatch=dispatch,
                )
            finally:
                self._discard_options_mutation_dispatch(dispatch)
            resp.raise_for_status()
            data = resp.json()
            
            order = OptionOrder.from_api(data)
            logger.info(f"✅ Order placed: {order.id} - {order.status}")
            return order
            
        except EconomicGovernanceBlocked:
            raise
        except requests.exceptions.HTTPError as e:
            error_detail = ""
            try:
                error_detail = e.response.json()
            except:
                error_detail = e.response.text
            logger.error(f"❌ Order failed: {e} - {error_detail}")
            return None
        except Exception as e:
            logger.error(f"❌ Order failed: {e}")
            return None
    
    def buy_call(
        self,
        underlying: str,
        strike: float,
        expiration: str,
        qty: int = 1,
        limit_price: Optional[float] = None
    ) -> Optional[OptionOrder]:
        """
        Buy a call option.
        
        Args:
            underlying: Stock symbol (e.g., "AAPL")
            strike: Strike price
            expiration: Expiration date (YYYY-MM-DD)
            qty: Number of contracts
            limit_price: Limit price (uses mid if not specified)
        """
        # Build option symbol
        symbol = self._build_option_symbol(underlying, expiration, 'C', strike)
        
        if limit_price is None:
            quote = self.get_quote(symbol)
            if quote:
                limit_price = quote.mid_price
            else:
                logger.error(f"❌ Could not get quote for {symbol}")
                return None
        
        return self.place_order(
            symbol=symbol,
            qty=qty,
            side='buy',
            order_type='limit',
            limit_price=limit_price
        )
    
    def buy_put(
        self,
        underlying: str,
        strike: float,
        expiration: str,
        qty: int = 1,
        limit_price: Optional[float] = None
    ) -> Optional[OptionOrder]:
        """Buy a put option."""
        symbol = self._build_option_symbol(underlying, expiration, 'P', strike)
        
        if limit_price is None:
            quote = self.get_quote(symbol)
            if quote:
                limit_price = quote.mid_price
            else:
                logger.error(f"❌ Could not get quote for {symbol}")
                return None
        
        return self.place_order(
            symbol=symbol,
            qty=qty,
            side='buy',
            order_type='limit',
            limit_price=limit_price
        )
    
    def sell_call(
        self,
        underlying: str,
        strike: float,
        expiration: str,
        qty: int = 1,
        limit_price: Optional[float] = None
    ) -> Optional[OptionOrder]:
        """Sell a call option (covered call or naked)."""
        symbol = self._build_option_symbol(underlying, expiration, 'C', strike)
        
        if limit_price is None:
            quote = self.get_quote(symbol)
            if quote:
                limit_price = quote.mid_price
            else:
                return None
        
        return self.place_order(
            symbol=symbol,
            qty=qty,
            side='sell',
            order_type='limit',
            limit_price=limit_price
        )
    
    def sell_put(
        self,
        underlying: str,
        strike: float,
        expiration: str,
        qty: int = 1,
        limit_price: Optional[float] = None
    ) -> Optional[OptionOrder]:
        """Sell a put option (cash-secured put)."""
        symbol = self._build_option_symbol(underlying, expiration, 'P', strike)
        
        if limit_price is None:
            quote = self.get_quote(symbol)
            if quote:
                limit_price = quote.mid_price
            else:
                return None
        
        return self.place_order(
            symbol=symbol,
            qty=qty,
            side='sell',
            order_type='limit',
            limit_price=limit_price
        )
    
    def close_position(self, symbol: str) -> Optional[OptionOrder]:
        """Close an existing options position."""
        position = self.get_position(symbol)
        if not position:
            logger.error(f"❌ No position found for {symbol}")
            return None
        
        # Opposite side to close
        side = 'sell' if position.side == 'long' else 'buy'
        
        return self.place_order(
            symbol=symbol,
            qty=abs(position.qty),
            side=side,
            order_type='market'
        )
    
    # ═══════════════════════════════════════════════════════════════════════
    # POSITIONS
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_positions(self) -> List[OptionPosition]:
        """Get all options positions."""
        try:
            resp = self.session.get(
                f"{self.base_url}/v2/positions",
                timeout=self.timeout
            )
            resp.raise_for_status()
            data = resp.json()
            
            positions = []
            for item in data:
                # Filter for options (symbols are longer and have format like AAPL240119C00100000)
                symbol = item.get('symbol', '')
                if len(symbol) > 10 and ('C' in symbol[-9:-8] or 'P' in symbol[-9:-8]):
                    positions.append(OptionPosition(
                        symbol=symbol,
                        qty=int(item.get('qty', 0)),
                        side=item.get('side', 'long'),
                        avg_entry_price=float(item.get('avg_entry_price', 0)),
                        current_price=float(item.get('current_price', 0)),
                        market_value=float(item.get('market_value', 0)),
                        cost_basis=float(item.get('cost_basis', 0)),
                        unrealized_pnl=float(item.get('unrealized_pl', 0)),
                        unrealized_pnl_pct=float(item.get('unrealized_plpc', 0)) * 100,
                    ))
            
            return positions
            
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []
    
    def get_position(self, symbol: str) -> Optional[OptionPosition]:
        """Get a specific options position."""
        try:
            resp = self.session.get(
                f"{self.base_url}/v2/positions/{symbol}",
                timeout=self.timeout
            )
            resp.raise_for_status()
            item = resp.json()
            
            return OptionPosition(
                symbol=item.get('symbol', ''),
                qty=int(item.get('qty', 0)),
                side=item.get('side', 'long'),
                avg_entry_price=float(item.get('avg_entry_price', 0)),
                current_price=float(item.get('current_price', 0)),
                market_value=float(item.get('market_value', 0)),
                cost_basis=float(item.get('cost_basis', 0)),
                unrealized_pnl=float(item.get('unrealized_pl', 0)),
                unrealized_pnl_pct=float(item.get('unrealized_plpc', 0)) * 100,
            )
            
        except Exception as e:
            logger.error(f"Failed to get position {symbol}: {e}")
            return None
    
    # ═══════════════════════════════════════════════════════════════════════
    # EXERCISE & ASSIGNMENT
    # ═══════════════════════════════════════════════════════════════════════
    
    def exercise(self, symbol: str) -> bool:
        """
        Exercise an options contract.
        
        Note: All available shares of this contract will be exercised.
        By default, Alpaca auto-exercises ITM contracts at expiry.
        """
        try:
            path = f"/v2/positions/{symbol}/exercise"
            body: Dict[str, Any] = {}
            dispatch = self._prepare_options_mutation(
                method="POST", path=path, body=body
            )
            try:
                resp = self._options_mutation_request(
                    "POST", path, body=body, _economic_dispatch=dispatch
                )
            finally:
                self._discard_options_mutation_dispatch(dispatch)
            resp.raise_for_status()
            logger.info(f"✅ Exercised {symbol}")
            return True
            
        except EconomicGovernanceBlocked:
            raise
        except Exception as e:
            logger.error(f"❌ Failed to exercise {symbol}: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════════════
    # ORDERS MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_orders(self, status: str = 'open') -> List[OptionOrder]:
        """Get options orders."""
        try:
            resp = self.session.get(
                f"{self.base_url}/v2/orders",
                params={'status': status},
                timeout=self.timeout
            )
            resp.raise_for_status()
            data = resp.json()
            
            orders = []
            for item in data:
                symbol = item.get('symbol', '')
                # Filter for options
                if len(symbol) > 10:
                    orders.append(OptionOrder.from_api(item))
            
            return orders
            
        except Exception as e:
            logger.error(f"Failed to get orders: {e}")
            return []
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an options order."""
        try:
            path = f"/v2/orders/{order_id}"
            body: Dict[str, Any] = {}
            dispatch = self._prepare_options_mutation(
                method="DELETE", path=path, body=body
            )
            try:
                resp = self._options_mutation_request(
                    "DELETE", path, body=body, _economic_dispatch=dispatch
                )
            finally:
                self._discard_options_mutation_dispatch(dispatch)
            resp.raise_for_status()
            logger.info(f"✅ Cancelled order {order_id}")
            return True
            
        except EconomicGovernanceBlocked:
            raise
        except Exception as e:
            logger.error(f"❌ Failed to cancel order {order_id}: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════════════
    # UTILITY METHODS
    # ═══════════════════════════════════════════════════════════════════════
    
    def _build_option_symbol(
        self,
        underlying: str,
        expiration: str,
        option_type: str,
        strike: float
    ) -> str:
        """
        Build OCC option symbol.
        
        Format: AAPL240119C00100000
        - AAPL: Underlying (padded to 6 chars)
        - 240119: Expiration (YYMMDD)
        - C: Call or P: Put
        - 00100000: Strike price * 1000 (8 digits)
        """
        # Parse expiration
        exp_date = datetime.strptime(expiration, '%Y-%m-%d')
        exp_str = exp_date.strftime('%y%m%d')
        
        # Format strike (multiply by 1000, pad to 8 digits)
        strike_int = int(strike * 1000)
        strike_str = f"{strike_int:08d}"
        
        # Build symbol
        return f"{underlying.upper()}{exp_str}{option_type.upper()}{strike_str}"
    
    def parse_option_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Parse an OCC option symbol.
        
        Returns dict with: underlying, expiration, type, strike
        """
        # Find where the date starts (6 digits after underlying)
        # Underlying can be 1-6 chars
        for i in range(1, 7):
            if symbol[i:i+6].isdigit():
                underlying = symbol[:i]
                exp_str = symbol[i:i+6]
                opt_type = symbol[i+6]
                strike_str = symbol[i+7:]
                
                exp_date = datetime.strptime(exp_str, '%y%m%d')
                strike = int(strike_str) / 1000
                
                return {
                    'underlying': underlying,
                    'expiration': exp_date.strftime('%Y-%m-%d'),
                    'type': 'call' if opt_type == 'C' else 'put',
                    'strike': strike,
                }
        
        return {}


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESSOR
# ═══════════════════════════════════════════════════════════════════════════════

_options_client: Optional[AlpacaOptionsClient] = None

def get_options_client() -> AlpacaOptionsClient:
    """Get or create the global options client instance."""
    global _options_client
    if _options_client is None:
        _options_client = AlpacaOptionsClient()
    return _options_client


# ═══════════════════════════════════════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    client = get_options_client()
    
    print("\n" + "=" * 70)
    print("🎯 ALPACA OPTIONS CLIENT - TEST")
    print("=" * 70)
    
    # Check trading level
    level = client.get_trading_level()
    print(f"\n📊 Trading Level: {level.name} ({level.value})")
    
    # Get buying power
    bp = client.get_options_buying_power()
    print(f"💰 Options Buying Power: ${bp:,.2f}")
    
    # Test contract discovery
    print("\n🔍 Searching for AAPL options...")
    contracts = client.get_contracts(
        underlying_symbol='AAPL',
        option_type=OptionType.CALL,
        limit=5
    )
    
    for c in contracts[:5]:
        print(f"   {c.symbol}: ${c.strike_price} {c.option_type.value} exp {c.expiration_date}")
    
    # Get existing positions
    print("\n📈 Current Options Positions:")
    positions = client.get_positions()
    if positions:
        for p in positions:
            print(f"   {p.symbol}: {p.qty}x @ ${p.avg_entry_price:.2f} | P&L: ${p.unrealized_pnl:.2f}")
    else:
        print("   (No options positions)")
    
    print("\n✅ Options client ready!")
    print("=" * 70)
