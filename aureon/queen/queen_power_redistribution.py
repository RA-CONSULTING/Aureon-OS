#!/usr/bin/env python3
"""
Queen Power Redistribution Engine
Autonomous energy optimization and power growth across all relays.

The Queen uses her built-in intelligence to:
1. Monitor ALL nodes (positions) across ALL relays for energy state
2. Identify nodes with positive energy (unrealized profit)
3. Redistribute profit energy to feed winning nodes or create new nodes
4. KEEP original positions profitable (don't close winners)
5. Move energy between nodes for optimal compound growth
6. Execute ONLY when (gain - drain) > 0
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys, os
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
        if _is_buffer_valid(sys.stdout) and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if _is_buffer_valid(sys.stderr) and not _is_utf8_wrapper(sys.stderr):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import logging

# Import Queen's consciousness
from aureon.utils.aureon_queen_true_consciousness import QueenTrueConsciousnessController

# Import exchange clients
from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
from aureon.exchanges.binance_client import BinanceClient, get_binance_client
from aureon.exchanges.alpaca_client import AlpacaClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class EnergyNode:
    """A position/asset holding representing an energy node."""
    relay: str  # BIN, KRK, ALP, CAP
    symbol: str  # BTC/USD, ETHUSDT, AAPL, etc.
    quantity: float  # Amount held
    entry_price: float  # Average entry price
    current_price: float  # Current market price
    unrealized_pnl: float  # Unrealized profit/loss (the energy state)
    pnl_percentage: float  # PnL as percentage
    position_value_usd: float  # Current USD value
    is_positive_energy: bool  # True if profitable
    energy_available_to_redistribute: float  # Profit we can move without closing
    timestamp: float
    
    def to_dict(self):
        return asdict(self)


@dataclass
class RedistributionOpportunity:
    """A potential energy redistribution opportunity."""
    relay: str
    source_asset: str
    target_asset: str
    idle_energy: float  # USD value available
    expected_gain_pct: float  # Expected gain percentage
    expected_gain_usd: float  # Expected gain in USD
    energy_drain: float  # Total drain from fees/slippage
    net_energy_gain: float  # Expected gain - drain
    momentum_score: float  # Asset momentum (0-1)
    confidence: float  # Queen's confidence (0-1)
    source_node: Optional['EnergyNode']  # Source node if redistributing from position
    timestamp: float
    
    def to_dict(self):
        d = asdict(self)
        if self.source_node:
            d['source_node'] = self.source_node.to_dict()
        return d


@dataclass
class RedistributionDecision:
    """Queen's decision on a redistribution opportunity."""
    opportunity: RedistributionOpportunity
    decision: str  # 'EXECUTE', 'BLOCK', 'WAIT'
    reasoning: str
    queen_confidence: float
    realms_consensus: int  # How many realms agreed (0-5)
    timestamp: float
    
    def to_dict(self):
        d = asdict(self)
        d['opportunity'] = self.opportunity.to_dict()
        return d


@dataclass
class TradeAuditRecord:
    """Unified trade audit record (order IDs + fills)."""
    ts: float
    exchange: str
    action: str
    symbol: str
    order_id: Optional[str]
    client_order_id: Optional[str]
    qty: Optional[float]
    quote_qty: Optional[float]
    avg_fill_price: Optional[float]
    fills: List[Dict]
    fees: Optional[float]
    status: str
    verified: bool
    source: str
    notes: Optional[str] = None

    def to_dict(self):
        return asdict(self)


class QueenPowerRedistribution:
    """
    Queen's autonomous energy redistribution system.
    Connects her intelligence to active execution.
    """
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.state_dir = os.getenv("AUREON_STATE_DIR", ".")
        
        # Initialize Queen consciousness
        logger.info("🐝 Initializing Queen's consciousness...")
        self.queen = QueenTrueConsciousnessController(dry_run=dry_run)
        
        # Initialize exchange clients
        self.kraken = None
        self.binance = None
        self.alpaca = None
        
        # Try to initialize exchanges (gracefully handle missing credentials)
        try:
            self.kraken = get_kraken_client()
        except Exception as e:
            logger.warning(f"Kraken not available: {e}")
        
        try:
            self.binance = get_binance_client()
        except Exception as e:
            logger.warning(f"Binance not available: {e}")
        
        try:
            self.alpaca = AlpacaClient()
        except Exception as e:
            logger.warning(f"Alpaca not available: {e}")
        
        # State tracking
        self.decisions_history: List[RedistributionDecision] = []
        self.executions_history: List[Dict] = []
        self.total_net_energy_gained = 0.0
        self.total_blocked_drains_avoided = 0.0
        self.all_energy_nodes: List[EnergyNode] = []  # All positions across all relays

        # Trade audit file (jsonl)
        self.trade_audit_file = "trade_audit.jsonl"
        
        # Load cost basis data
        self.cost_basis = self.load_state_file('cost_basis_history.json', {})
        cost_basis_positions = self.cost_basis.get('positions', {})
        logger.info(f"📊 Cost Basis Tracker: Loaded {len(cost_basis_positions)} positions from cost_basis_history.json")
        
        # Relay-specific fee profiles (from adaptive_prime_profit_gate.py)
        self.relay_fees = {
            'BIN': {'maker': 0.0010, 'taker': 0.0010, 'spread': 0.0005, 'slippage': 0.0003},  # Binance
            'KRK': {'maker': 0.0025, 'taker': 0.0040, 'spread': 0.0008, 'slippage': 0.0005},  # Kraken
            'ALP': {'maker': 0.0015, 'taker': 0.0025, 'spread': 0.0008, 'slippage': 0.0005},  # Alpaca
            'CAP': {'maker': 0.0000, 'taker': 0.0000, 'spread': 0.0020, 'slippage': 0.0008},  # Capital (spread-based)
        }
        
        # Configuration
        self.min_idle_energy_usd = 0.10  # Min USD to consider redistribution (LOWERED for small accounts)
        self.min_net_gain_usd = 0.01  # Min net gain required (LOWERED to catch micro-profits)
        self.min_positive_energy_to_redistribute = 0.05  # Min profit before we redistribute (LOWERED)
        self.profit_redistribution_percentage = 0.75  # Take 75% of profit to redistribute
        self.scan_interval_seconds = 10  # How often to scan for opportunities
        self.max_redistribution_per_relay = 0.50  # Max 50% of idle energy per cycle
        
        # Momentum scanner integration
        self.momentum_scanner = None
        try:
            from aureon.scanners.aureon_animal_momentum_scanners import AlpacaSwarmOrchestrator
            from aureon.bridges.aureon_alpaca_scanner_bridge import AlpacaScannerBridge
            # Initialize bridge and orchestrator
            bridge = AlpacaScannerBridge(self.alpaca)
            self.momentum_scanner = AlpacaSwarmOrchestrator(self.alpaca, bridge)
            logger.info("🐺 Momentum Scanner integrated - Will find real targets!")
        except Exception as e:
            logger.warning(f"Momentum scanner not available: {e}")
        
        logger.info(f"✅ Queen Power Redistribution initialized (dry_run={dry_run})")

    def _append_trade_audit(self, record: TradeAuditRecord) -> None:
        try:
            with open(self.trade_audit_file, 'a') as f:
                f.write(json.dumps(record.to_dict()) + "\n")
        except Exception as e:
            logger.debug(f"Trade audit write failed: {e}")

    def _get_verified_entry_price(self, symbol: str, exchange: str) -> Optional[float]:
        cost_basis_positions = self.cost_basis.get('positions', {})
        candidates = [
            f"{exchange.lower()}:{symbol}",
            symbol,
            symbol.replace('/', ''),
        ]
        for key in candidates:
            pos = cost_basis_positions.get(key)
            if not pos:
                continue
            if not pos.get('fills_verified'):
                continue
            if not pos.get('last_order_id'):
                continue
            avg_fill_price = pos.get('avg_fill_price') or pos.get('avg_entry_price')
            if avg_fill_price and avg_fill_price > 0:
                return avg_fill_price
        return None
    
    def calculate_relay_energy_drain(self, relay: str, trade_value_usd: float, is_maker: bool = True) -> Dict:
        """
        Calculate total energy drain for a trade on a specific relay.
        CRITICAL: Must be accurate to prevent energy loss!
        
        Returns:
            {
                'maker_fee': float,
                'taker_fee': float,
                'spread_cost': float,
                'slippage': float,
                'total_drain': float,
                'relay': str
            }
        """
        fees = self.relay_fees.get(relay, self.relay_fees['KRK'])  # Default to Kraken (conservative)
        
        fee_rate = fees['maker'] if is_maker else fees['taker']
        
        # Calculate components
        trading_fee = trade_value_usd * fee_rate
        spread_cost = trade_value_usd * fees['spread']
        slippage_cost = trade_value_usd * fees['slippage']
        
        # CRITICAL: We pay fees on BOTH sides of conversion (buy + sell)
        # USD → Asset: pay fee on entry
        # Asset → USD (future): pay fee on exit
        # So we double the trading fee for round-trip
        total_drain = (trading_fee * 2) + spread_cost + slippage_cost
        
        return {
            'maker_fee': trading_fee if is_maker else 0,
            'taker_fee': 0 if is_maker else trading_fee,
            'spread_cost': spread_cost,
            'slippage': slippage_cost,
            'total_drain': total_drain,
            'relay': relay,
            'fee_rate': fee_rate,
            'round_trip_factor': 2.0  # We account for entry + exit
        }
    
    def load_state_file(self, filepath: str, default: Optional[Dict] = None) -> Dict:
        """Load JSON state file with fallback."""
        try:
            if not os.path.isabs(filepath):
                state_path = os.path.join(self.state_dir, filepath)
                if os.path.exists(state_path):
                    with open(state_path, 'r') as f:
                        return json.load(f)
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load {filepath}: {e}")
        return default or {}
    
    def get_relay_idle_energy(self, relay: str) -> Tuple[float, str]:
        """
        Get idle energy (USD/USDT balance) for a relay.
        Returns (amount_usd, asset_symbol).
        
        🔴 CRITICAL: Always prefers LIVE API data. Only falls back to state file
        if fresh (< 5 min old). This prevents stale balance issues.
        """
        STATE_FILE_MAX_AGE_SECONDS = 300  # 5 minutes
        
        if relay == 'BIN':
            # Binance: Check USDT balance
            if self.binance:
                try:
                    balances = self.binance.get_balance()
                    usdt = balances.get('USDT', 0.0)
                    return (usdt, 'USDT')
                except Exception as e:
                    logger.warning(f"BIN balance fetch failed: {e}")
            # Fallback to state file (with TTL check)
            state = self.load_state_file('binance_truth_tracker_state.json', {})
            # Try 'last_update' first, fallback to 'timestamp' key
            last_update = state.get('last_update') or state.get('timestamp', 0)
            if last_update == 0:
                logger.warning(f"⚠️ BIN state file has no timestamp, skipping")
                return (0.0, 'USDT')
            age = time.time() - last_update
            if age > STATE_FILE_MAX_AGE_SECONDS:
                logger.error(f"❌ BIN state file is stale ({age:.0f}s old, max {STATE_FILE_MAX_AGE_SECONDS}s) - returning 0")
                return (0.0, 'USDT')  # Don't use stale data
            usdt = state.get('balances', {}).get('USDT', {}).get('free', 0.0)
            logger.warning(f"⚠️ Using cached BIN balance: ${usdt:.2f} (age: {age:.0f}s)")
            return (usdt, 'USDT')
        
        elif relay == 'KRK':
            # Kraken: Check ZUSD balance
            if self.kraken:
                try:
                    balances = self.kraken.get_balance()
                    usd = balances.get('USD', balances.get('ZUSD', 0.0))
                    return (usd, 'USD')
                except Exception as e:
                    logger.warning(f"KRK balance fetch failed: {e}")
            # Fallback to state file (with TTL check)
            state = self.load_state_file('aureon_kraken_state.json', {})
            # Try 'last_update' first, fallback to 'timestamp' key
            last_update = state.get('last_update') or state.get('timestamp', 0)
            if last_update == 0:
                logger.warning(f"⚠️ KRK state file has no timestamp, skipping")
                return (0.0, 'USD')
            age = time.time() - last_update
            if age > STATE_FILE_MAX_AGE_SECONDS:
                logger.error(f"❌ KRK state file is stale ({age:.0f}s old, max {STATE_FILE_MAX_AGE_SECONDS}s) - returning 0")
                return (0.0, 'USD')  # Don't use stale data
            usd = state.get('balances', {}).get('USD', state.get('balances', {}).get('ZUSD', 0.0))
            logger.warning(f"⚠️ Using cached KRK balance: ${usd:.2f} (age: {age:.0f}s)")
            return (usd, 'USD')
        
        elif relay == 'ALP':
            # Alpaca: Check USD cash
            if self.alpaca:
                try:
                    account = self.alpaca.get_account()
                    cash = float(account.get('cash', 0.0))
                    return (cash, 'USD')
                except Exception as e:
                    logger.warning(f"ALP balance fetch failed: {e}")
            # Fallback to state file (with TTL check)
            state = self.load_state_file('alpaca_truth_tracker_state.json', {})
            # Try 'last_update' first, fallback to 'timestamp' key
            last_update = state.get('last_update') or state.get('timestamp', 0)
            if last_update == 0:
                logger.warning(f"⚠️ ALP state file has no timestamp, skipping")
                return (0.0, 'USD')
            age = time.time() - last_update
            if age > STATE_FILE_MAX_AGE_SECONDS:
                logger.error(f"❌ ALP state file is stale ({age:.0f}s old, max {STATE_FILE_MAX_AGE_SECONDS}s) - returning 0")
                return (0.0, 'USD')  # Don't use stale data
            cash = state.get('cash', 0.0)
            logger.warning(f"⚠️ Using cached ALP balance: ${cash:.2f} (age: {age:.0f}s)")
            return (cash, 'USD')
        
        elif relay == 'CAP':
            # Capital.com: Use hardcoded balance for now (manual tracking)
            # TODO: Integrate with Capital.com API when available
            return (92.66, 'USD')  # Current CAP balance
        
        return (0.0, 'UNKNOWN')
    
    def scan_all_energy_nodes(self) -> List[EnergyNode]:
        """
        Scan ALL positions across ALL relays to find energy nodes.
        Returns list of all positions with their energy states.
        """
        nodes = []
        
        # Scan BIN (Binance) - Get LIVE balances from API
        try:
            binance_api_available = False
            if self.binance:
                logger.info("  🔍 Scanning Binance via LIVE API...")
                balances = self.binance.get_balance()
                binance_api_available = True
                logger.info(f"  📊 BIN: Found {len(balances)} assets")
                
                for asset, qty in balances.items():
                    # Include ALL nodes - dust is quantum entangled energy!
                    # Only skip pure quote currencies (USDT/USDC) - they are the medium, not nodes
                    if asset in ['USDT', 'USDC', 'BUSD']:
                        continue  # Skip pure quote currencies only
                    
                    # Try multiple quote currencies to find a valid pair
                    symbol = None
                    current_price = 0
                    for quote in ['USDT', 'USDC', 'BTC', 'BNB']:
                        try_symbol = f'{asset}{quote}'
                        try:
                            ticker = self.binance.get_ticker(try_symbol)
                            if ticker:
                                price = float(ticker.get('last', ticker.get('price', 0)))
                                if price > 0:
                                    symbol = try_symbol
                                    current_price = price
                                    # Convert BTC/BNB prices to USD
                                    if quote == 'BTC':
                                        btc_ticker = self.binance.get_ticker('BTCUSDT')
                                        if btc_ticker:
                                            current_price = price * float(btc_ticker.get('last', 0))
                                    elif quote == 'BNB':
                                        bnb_ticker = self.binance.get_ticker('BNBUSDT')
                                        if bnb_ticker:
                                            current_price = price * float(bnb_ticker.get('last', 0))
                                    break
                        except:
                            continue
                    
                    # Handle special cases: USD balance, Earn products
                    if not symbol and asset == 'USD':
                        symbol = 'USD'
                        current_price = 1.0  # USD = 1 USD
                    elif not symbol and asset.startswith('LD'):
                        # Binance Earn products (LDUSDC = staked USDC)
                        base_asset = asset[2:]  # Remove 'LD' prefix
                        if base_asset in ['USDC', 'USDT', 'BUSD']:
                            symbol = asset
                            current_price = 1.0  # Stablecoins = $1
                        else:
                            # Try to get price for underlying
                            try:
                                ticker = self.binance.get_ticker(f'{base_asset}USDT')
                                if ticker:
                                    symbol = asset
                                    current_price = float(ticker.get('last', 0))
                            except:
                                pass
                    
                    if not symbol or current_price <= 0:
                        # Still track as unknown quantum node
                        logger.info(f"  🌌 BIN: {asset} | {qty:.6f} units | NO PAIR FOUND (quantum orphan)")
                        continue
                    
                    try:
                        position_value = qty * current_price
                        
                        # Look up cost basis from history
                        entry_price = current_price  # Default if no basis found
                        entry_verified = False
                        cost_basis_positions = self.cost_basis.get('positions', {})

                        verified_entry = self._get_verified_entry_price(symbol, 'binance')
                        if verified_entry and verified_entry > 0:
                            entry_price = verified_entry
                            entry_verified = True
                        
                        # Try different key formats: ASSETUSDC, ASSETUSDT, binance:ASSETUSDC
                        for quote in ['USDC', 'USDT']:
                            basis_key = f'{asset}{quote}'
                            if basis_key in cost_basis_positions:
                                if not entry_verified:
                                    entry_price = cost_basis_positions[basis_key].get('avg_entry_price', current_price)
                                break
                            # Try with exchange prefix
                            basis_key_prefixed = f'binance:{asset}{quote}'
                            if basis_key_prefixed in cost_basis_positions:
                                if not entry_verified:
                                    entry_price = cost_basis_positions[basis_key_prefixed].get('avg_entry_price', current_price)
                                break
                        
                        # Calculate PnL
                        pnl = (current_price - entry_price) * qty
                        pnl_pct = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0.0
                        if entry_verified:
                            is_positive = pnl > self.min_positive_energy_to_redistribute
                            redistributable = (pnl * 0.5) if is_positive else 0.0  # 50% of profit
                        else:
                            # Unverified entry price: treat as not positive for redistribution
                            is_positive = False
                            redistributable = 0.0
                        
                        # ALL nodes included - quantum entanglement doesn't discriminate by size!
                        node = EnergyNode(
                            relay='BIN',
                            symbol=symbol,
                            quantity=qty,
                            entry_price=entry_price,
                            current_price=current_price,
                            unrealized_pnl=pnl,
                            pnl_percentage=pnl_pct,
                            position_value_usd=position_value,
                            is_positive_energy=is_positive,
                            energy_available_to_redistribute=redistributable,
                            timestamp=time.time()
                        )
                        nodes.append(node)
                        # Show entry price + PnL in log - include dust indicator
                        dust_marker = "🌌" if position_value < 0.50 else ""  # Quantum dust marker
                        pnl_indicator = "🟢" if is_positive else ("🔴" if pnl < -0.10 else "⚪")
                        verify_marker = "✅" if entry_verified else "⚠️"
                        logger.info(f"  {pnl_indicator}{dust_marker} BIN: {symbol} | {qty:.6f} units | ${position_value:.4f} | Entry: ${entry_price:.6f} {verify_marker} | PnL: ${pnl:.4f} ({pnl_pct:.1f}%)")
                    except Exception as e:
                        logger.debug(f"  ⚪ BIN {symbol}: {e}")
            else:
                logger.warning("  ⚠️ BIN: Client not available")
            
            # Store Binance API availability for fail-safe checks
            if not hasattr(self, '_exchange_api_status'):
                self._exchange_api_status = {}
            self._exchange_api_status['BIN'] = binance_api_available
            
        except Exception as e:
            logger.warning(f"BIN node scan failed: {e}")
            # Mark Binance API as unavailable on error
            if not hasattr(self, '_exchange_api_status'):
                self._exchange_api_status = {}
            self._exchange_api_status['BIN'] = False
        
        # Scan KRK (Kraken) - Multi-source approach (adapt to data availability)
        try:
            logger.info("  🔍 Scanning Kraken (multi-source: API balance + cost basis + state)...")
            
            # Kraken symbol mapping (internal codes → standard ticker symbols)
            KRAKEN_SYMBOL_MAP = {
                'XBT': 'BTC', 'BT': 'XBT',  # Bitcoin variants
                'XRP': 'XRP', 'RP': 'XRP',  # Ripple
                'XDG': 'DOGE', 'DG': 'XDG', # Dogecoin
                'XXBT': 'XBT', 'XXRP': 'XRP', 'XETH': 'ETH', 'XLTC': 'LTC',
                'ZUSD': 'USD', 'ZEUR': 'EUR', 'ZGBP': 'GBP',
            }
            
            def get_kraken_ticker_symbol(asset: str, quote: str) -> list:
                """Generate possible Kraken ticker symbols to try."""
                # Map internal codes to standard
                mapped_asset = KRAKEN_SYMBOL_MAP.get(asset, asset)
                mapped_quote = KRAKEN_SYMBOL_MAP.get(quote, quote)
                
                # Generate variants to try
                variants = [
                    f'{mapped_asset}{mapped_quote}',
                    f'{asset}{quote}',
                    f'X{mapped_asset}Z{mapped_quote}',  # Kraken format: XXBTZUSD
                    f'X{mapped_asset}{mapped_quote}',
                    f'{mapped_asset}Z{mapped_quote}',
                ]
                # For BTC specifically
                if asset in ['BT', 'XBT', 'BTC']:
                    variants.extend(['XBTUSD', 'XXBTZUSD', 'BTCUSD'])
                # For XRP
                if asset in ['RP', 'XRP']:
                    variants.extend(['XRPUSD', 'XXRPZUSD'])
                # For DOGE
                if asset in ['DG', 'XDG', 'DOGE']:
                    variants.extend(['XDGUSD', 'DOGEUSD'])
                return variants
            
            # Source 1: Try live API balance first (HIGHEST PRIORITY)
            api_balances = {}
            if self.kraken:
                try:
                    api_balances = self.kraken.get_balance()
                    if api_balances:
                        logger.info(f"  📡 KRK API: Found {len(api_balances)} live balances (Source of Truth)")
                except Exception as e:
                    logger.warning(f"  ⚠️ KRK API balance failed: {e}. Will use fallback sources.")
            
            # Source 2: Cost basis history (for entry price and as a fallback for existence)
            cost_basis_positions = {k: v for k, v in self.cost_basis.get('positions', {}).items() 
                                if v.get('exchange') == 'kraken'}
            
            # Source 3: State file (local truth, fallback if API fails)
            krk_state = self.load_state_file('aureon_kraken_state.json', {})
            krk_state_positions = krk_state.get('positions', {})
            
            # --- CORRECTED LOGIC V4: Final Fallback Authority ---
            symbols_to_process = {} # Use a dict to store symbol and its determined source

            # Track API availability for fail-safe checks during execution
            kraken_api_available = bool(api_balances)
            
            if api_balances:
                logger.info(f"  📊 KRK: Using API as primary source for {len(api_balances)} symbols.")
                for symbol, qty in api_balances.items():
                    if qty > 0.000001:
                        symbols_to_process[symbol] = 'api'
            else:
                logger.warning("  ⚠️ KRK: API unavailable. State file is now the SOLE authority for existing positions.")
                logger.warning("  🚫 KRK: BLOCKING ALL KRAKEN TRADES - Cannot verify balances without live API.")
                # When API fails, the state file is the ONLY source of truth for what positions EXIST.
                # Cost basis will be used for entry price lookup ONLY.
                for symbol, data in krk_state_positions.items():
                    if data.get('quantity', 0.0) > 0.000001:
                        symbols_to_process[symbol] = 'state'
                
                logger.info(f"  📊 KRK: Scanning {len(symbols_to_process)} positions EXCLUSIVELY from state file (VIEW ONLY).")

            for symbol, source in symbols_to_process.items():
                qty = 0.0
                entry_price = 0.0
                asset = symbol
                quote = 'USD' # Default quote

                # Get QUANTITY and ENTRY PRICE from the determined source
                if source == 'api':
                    qty = api_balances.get(symbol, 0.0)
                    # Get entry price from cost basis if available, otherwise it's a new position
                    if symbol in cost_basis_positions:
                        entry_price = cost_basis_positions[symbol].get('avg_entry_price', 0.0)
                        asset = cost_basis_positions[symbol].get('asset', symbol)
                        quote = cost_basis_positions[symbol].get('quote', 'USD')
                
                elif source == 'state':
                    state_data = krk_state_positions.get(symbol, {})
                    qty = state_data.get('quantity', 0.0)
                    # The primary source for entry price should still be cost_basis if available
                    if symbol in cost_basis_positions:
                        entry_price = cost_basis_positions[symbol].get('avg_entry_price', 0.0)
                        asset = cost_basis_positions[symbol].get('asset', symbol)
                        quote = cost_basis_positions[symbol].get('quote', 'USD')
                    else:
                        # If not in cost basis, use the state file's entry price
                        entry_price = state_data.get('entry_price', 0.0)
                
                # NOTE: There is no `elif source == 'cost_basis'` anymore. This was the bug.
                # We only iterate over symbols confirmed to exist via API or state file.

                # If quantity is effectively zero after all checks, skip.
                if qty < 0.000001:
                    continue

                # CORRECTED: Get ENTRY PRICE from the most reliable sources.
                # Cost basis is the ultimate source of truth for entry price.
                if symbol in cost_basis_positions:
                    cb_data = cost_basis_positions[symbol]
                    entry_price = cb_data.get('avg_entry_price', 0.0)
                    asset = cb_data.get('asset', symbol)
                    quote = cb_data.get('quote', 'USD')
                elif symbol in krk_state_positions:
                    # Fallback to state file if not in cost basis history
                    entry_price = krk_state_positions[symbol].get('entry_price', 0.0)
                    asset = symbol
                    quote = 'USD'
                else:
                    asset = symbol
                    quote = 'USD'

                # Get current price using symbol mapping
                current_price = 0
                if self.kraken:
                    symbols_to_try = get_kraken_ticker_symbol(asset, quote)
                    symbols_to_try.extend([symbol, f'{asset}USD', f'{asset}USDT'])
                    
                    for try_symbol in set(symbols_to_try):
                        try:
                            ticker = self.kraken.get_ticker(try_symbol)
                            fetched_price = float(ticker.get('price', ticker.get('last', 0)))
                            if fetched_price > 0:
                                current_price = fetched_price
                                break
                        except:
                            continue
                
                if current_price <= 0:
                    current_price = entry_price # Fallback if price fetch fails

                position_value = qty * current_price
                
                pnl = (current_price - entry_price) * qty if entry_price > 0 else 0.0
                pnl_pct = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0.0
                is_positive = pnl > self.min_positive_energy_to_redistribute
                redistributable = (pnl * self.profit_redistribution_percentage) if is_positive else 0.0
                
                if position_value > 0.01:
                    node = EnergyNode(
                        relay='KRK',
                        symbol=symbol,
                        quantity=qty,
                        entry_price=entry_price,
                        current_price=current_price,
                        unrealized_pnl=pnl,
                        pnl_percentage=pnl_pct,
                        position_value_usd=position_value,
                        is_positive_energy=is_positive,
                        energy_available_to_redistribute=redistributable,
                        timestamp=time.time()
                    )
                    nodes.append(node)
                    pnl_indicator = "🟢" if is_positive else ("🔴" if pnl < -0.01 else "⚪")
                    logger.info(f"  {pnl_indicator} KRK: {symbol} | {qty:.6f} units | ${position_value:.4f} | Entry: ${entry_price:.6f} | PnL: ${pnl:.4f} ({pnl_pct:.1f}%)")
            
            # Store API availability status for fail-safe checks during execution
            if not hasattr(self, '_exchange_api_status'):
                self._exchange_api_status = {}
            self._exchange_api_status['KRK'] = kraken_api_available
            
        except Exception as e:
            logger.error(f"CRITICAL KRK node scan failed: {e}", exc_info=True)
        
        # Scan ALP (Alpaca)
        try:
            alp_state = self.load_state_file('alpaca_truth_tracker_state.json', {})
            positions = alp_state.get('positions', [])
            for pos in positions:
                if isinstance(pos, dict):
                    symbol = pos.get('symbol', 'UNKNOWN')
                    qty = float(pos.get('qty', 0.0))
                    entry = float(pos.get('avg_entry_price', 0.0))
                    current = float(pos.get('current_price', entry))
                    pnl = float(pos.get('unrealized_pl', 0.0))
                    pnl_pct = float(pos.get('unrealized_plpc', 0.0)) * 100
                    position_value = float(pos.get('market_value', 0.0))
                    
                    # Include ANY position with non-zero quantity (even small micro-positions)
                    if abs(qty) > 0 and position_value > 0.01:
                        node = EnergyNode(
                            relay='ALP',
                            symbol=symbol,
                            quantity=qty,
                            entry_price=entry,
                            current_price=current,
                            unrealized_pnl=pnl,
                            pnl_percentage=pnl_pct,
                            position_value_usd=position_value,
                            is_positive_energy=pnl > 0,
                            energy_available_to_redistribute=max(0, pnl * self.profit_redistribution_percentage) if pnl > self.min_positive_energy_to_redistribute else 0.0,
                            timestamp=time.time()
                        )
                        nodes.append(node)
                        if node.is_positive_energy:
                            logger.info(f"  🟢 ALP node: {symbol} | +${pnl:.4f} ({pnl_pct:.2f}%) | Redistributable: ${node.energy_available_to_redistribute:.4f}")
        except Exception as e:
            logger.warning(f"ALP node scan failed: {e}")
        
        # Scan CAP (Capital.com) - manual for now
        # TODO: Add Capital.com API integration
        
        self.all_energy_nodes = nodes
        
        positive_nodes = [n for n in nodes if n.is_positive_energy]
        total_positive_energy = sum(n.unrealized_pnl for n in positive_nodes)
        total_redistributable = sum(n.energy_available_to_redistribute for n in positive_nodes)
        
        logger.info(f"📊 Node Scan Complete: {len(nodes)} total nodes, {len(positive_nodes)} with positive energy")
        logger.info(f"💎 Total Positive Energy: ${total_positive_energy:.2f} | Redistributable: ${total_redistributable:.2f}")
        
        return nodes
    
    def find_best_conversion(self, relay: str, idle_usd: float) -> Optional[Tuple[str, float, float]]:
        """
        Find best asset to convert idle energy into.
        Returns (target_asset, expected_gain_pct, momentum_score) or None.
        
        Uses momentum scanner to find high-momentum assets from REAL order books.
        CRITICAL: Only recommend targets where expected_gain > energy_drain!
        """
        # Calculate minimum required gain to cover fees (relay-specific)
        drain_info = self.calculate_relay_energy_drain(relay, idle_usd, is_maker=True)
        min_gain_pct_required = (drain_info['total_drain'] / idle_usd * 100) + 0.5  # +0.5% buffer
        
        logger.debug(f"  {relay}: Min gain required: {min_gain_pct_required:.2f}% to cover ${drain_info['total_drain']:.4f} drain")
        # Use momentum scanner if available
        if self.momentum_scanner and relay == 'ALP':
            try:
                # Get best opportunity from momentum scanner
                best_opp = self.momentum_scanner.get_best_opportunity()
                if best_opp:
                    symbol = best_opp.symbol
                    expected_gain = best_opp.net_pct  # Net after fees
                    momentum = best_opp.volume / 1000  # Normalize volume as momentum score
                    
                    logger.info(f"🎯 Momentum scanner found: {symbol} | {expected_gain:.2f}% net gain | {best_opp.side} signal | {best_opp.reason}")
                    return (symbol, expected_gain, momentum)
            except Exception as e:
                logger.warning(f"Momentum scanner query failed: {e}")
        
        # Fallback: Load scanning system metrics
        scan_metrics = self.load_state_file('power_station_state.json', {})
        
        # Relay-specific asset selection
        if relay == 'BIN':
            # Binance: Look at our WINNING positions as potential targets
            # Strategy: Feed the winners - add more to profitable positions
            winning_bins = [n for n in self.all_energy_nodes 
                          if n.relay == 'BIN' and n.is_positive_energy and n.pnl_percentage > min_gain_pct_required]
            
            if winning_bins:
                # Pick the best performer
                best = max(winning_bins, key=lambda n: n.pnl_percentage)
                logger.info(f"  🎯 BIN: Feed the winner - {best.symbol} is up {best.pnl_percentage:.1f}%")
                return (best.symbol, best.pnl_percentage * 0.5, 0.8)  # Conservative: expect 50% of current gain
            
            # Fallback: No winners to feed, skip
            logger.debug(f"  BIN: No winning positions above {min_gain_pct_required:.2f}% threshold")
            return None
        
        elif relay == 'KRK':
            # Kraken: Look at our WINNING positions as potential targets
            # Strategy: Feed the winners - add more to profitable positions
            winning_krks = [n for n in self.all_energy_nodes 
                          if n.relay == 'KRK' and n.is_positive_energy and n.pnl_percentage > min_gain_pct_required]
            
            if winning_krks:
                # Pick the best performer
                best = max(winning_krks, key=lambda n: n.pnl_percentage)
                logger.info(f"  🎯 KRK: Feed the winner - {best.symbol} is up {best.pnl_percentage:.1f}%")
                return (best.symbol, best.pnl_percentage * 0.5, 0.8)  # Conservative: expect 50% of current gain
            
            # Fallback: Check for validated branches from 7-day system
            validations_data = self.load_state_file('7day_pending_validations.json', {})
            
            # Handle both dict and list formats
            if isinstance(validations_data, list):
                validations = {f"branch_{i}": v for i, v in enumerate(validations_data)}
            else:
                validations = validations_data
            
            # Find branches ready for 4th decision
            for branch_id, branch in validations.items():
                if not isinstance(branch, dict):
                    continue
                if branch.get('relay') == 'KRK' and branch.get('coherence', 0) > 0.618:
                    symbol = branch.get('symbol', '')
                    expected_gain = branch.get('expected_pip_profit_pct', 0.0)
                    momentum = branch.get('coherence', 0.0)
                    
                    if expected_gain > min_gain_pct_required:
                        return (symbol, expected_gain, momentum)
            
            logger.debug(f"  KRK: No winning positions above {min_gain_pct_required:.2f}% threshold")
            return None
        
        elif relay == 'ALP':
            # Alpaca: Check high-momentum stocks
            watchlist = ['TSLA', 'AAPL', 'MSFT', 'NVDA', 'AMD']
            # TODO: Integrate with real scanning data
            return None
        
        return None
    
    async def analyze_redistribution_opportunities(self) -> List[RedistributionOpportunity]:
        """
        Scan all relays for energy redistribution opportunities.
        Queen's first step: Perceive the energy landscape.
        
        TWO SOURCES OF ENERGY:
        1. Idle cash (USD/USDT) in relay accounts
        2. Profit from positive energy nodes (winning positions)
        """
        opportunities = []
        
        # STEP 1: Scan all energy nodes (positions)
        logger.info("🔍 Scanning all energy nodes across relays...")
        all_nodes = self.scan_all_energy_nodes()
        
        # STEP 2: Find opportunities from IDLE CASH
        logger.info("💰 Checking idle cash opportunities...")
        for relay in ['BIN', 'KRK', 'ALP']:
            # Get idle energy
            idle_usd, source_asset = self.get_relay_idle_energy(relay)
            
            if idle_usd < self.min_idle_energy_usd:
                logger.debug(f"{relay}: Idle cash too low (${idle_usd:.2f} < ${self.min_idle_energy_usd})")
                continue
            
            # Cap at max redistribution per cycle
            max_deploy = idle_usd * self.max_redistribution_per_relay
            
            # Find best conversion target
            conversion = self.find_best_conversion(relay, max_deploy)
            if not conversion:
                logger.debug(f"{relay}: No profitable conversions found for idle cash")
                continue
            
            target_asset, expected_gain_pct, momentum_score = conversion
            
            # Calculate expected gain and drain
            expected_gain_usd = max_deploy * (expected_gain_pct / 100.0)
            
            # Calculate energy drain using relay-specific fees
            drain_info = self.calculate_relay_energy_drain(relay, max_deploy, is_maker=True)
            energy_drain = drain_info['total_drain']
            
            # Calculate net energy gain
            net_energy_gain = expected_gain_usd - energy_drain
            
            # Only consider if net positive
            if net_energy_gain > self.min_net_gain_usd:
                opp = RedistributionOpportunity(
                    relay=relay,
                    source_asset=source_asset,
                    target_asset=target_asset,
                    idle_energy=max_deploy,
                    expected_gain_pct=expected_gain_pct,
                    expected_gain_usd=expected_gain_usd,
                    energy_drain=energy_drain,
                    net_energy_gain=net_energy_gain,
                    momentum_score=momentum_score,
                    confidence=0.7,  # Base confidence
                    source_node=None,  # From idle cash
                    timestamp=time.time()
                )
                opportunities.append(opp)
                logger.info(f"✨ {relay} idle cash opportunity: {target_asset}, net gain ${net_energy_gain:.4f}")
            else:
                logger.debug(f"{relay}: Net gain too low (${net_energy_gain:.4f})")
        
        # STEP 3: Find opportunities from POSITIVE ENERGY NODES
        logger.info("🌱 Checking profit redistribution opportunities...")
        positive_nodes = [n for n in all_nodes if n.is_positive_energy and n.energy_available_to_redistribute > 0]
        
        for node in positive_nodes:
            # This node has profit we can redistribute
            redistributable = node.energy_available_to_redistribute
            
            if redistributable < self.min_idle_energy_usd:
                continue
            
            # Find best target in SAME relay (internal redistribution)
            conversion = self.find_best_conversion(node.relay, redistributable)
            if not conversion:
                logger.debug(f"{node.relay} {node.symbol}: No target for profit redistribution")
                continue
            
            target_asset, expected_gain_pct, momentum_score = conversion
            
            # Calculate expected gain and drain
            expected_gain_usd = redistributable * (expected_gain_pct / 100.0)
            
            # Calculate energy drain using relay-specific fees
            drain_info = self.calculate_relay_energy_drain(node.relay, redistributable, is_maker=True)
            energy_drain = drain_info['total_drain']
            
            # Calculate net energy gain
            net_energy_gain = expected_gain_usd - energy_drain
            
            # Only consider if net positive
            if net_energy_gain > self.min_net_gain_usd:
                opp = RedistributionOpportunity(
                    relay=node.relay,
                    source_asset=node.symbol,
                    target_asset=target_asset,
                    idle_energy=redistributable,
                    expected_gain_pct=expected_gain_pct,
                    expected_gain_usd=expected_gain_usd,
                    energy_drain=energy_drain,
                    net_energy_gain=net_energy_gain,
                    momentum_score=momentum_score,
                    confidence=0.8,  # Higher confidence (from winning position)
                    source_node=node,  # From profitable node
                    timestamp=time.time()
                )
                opportunities.append(opp)
                logger.info(f"✨ {node.relay} node profit opportunity: {node.symbol} → {target_asset}, net gain ${net_energy_gain:.4f}")
            else:
                logger.debug(f"{node.relay} {node.symbol}: Net gain too low (${net_energy_gain:.4f})")
        
        return opportunities
    
    async def queen_analyze_and_decide(self, opportunity: RedistributionOpportunity) -> RedistributionDecision:
        """
        Queen analyzes opportunity and makes decision.
        Uses her consciousness to validate across all realms.
        """
        # Ask Queen if trade will be profitable
        is_profitable, reasoning, drain_details = self.queen.will_trade_be_profitable(
            relay=opportunity.relay,
            trade_value=opportunity.idle_energy,
            expected_gain_pct=opportunity.expected_gain_pct
        )
        
        if not is_profitable:
            decision = RedistributionDecision(
                opportunity=opportunity,
                decision='BLOCK',
                reasoning=reasoning,
                queen_confidence=0.0,
                realms_consensus=0,
                timestamp=time.time()
            )
            logger.warning(f"🚫 Queen BLOCKED {opportunity.relay} {opportunity.target_asset}: {reasoning}")
            return decision
        
        # Check if opportunity meets Queen's standards
        if opportunity.net_energy_gain < self.min_net_gain_usd:
            decision = RedistributionDecision(
                opportunity=opportunity,
                decision='BLOCK',
                reasoning=f"Net gain ${opportunity.net_energy_gain:.4f} below minimum ${self.min_net_gain_usd}",
                queen_confidence=0.0,
                realms_consensus=0,
                timestamp=time.time()
            )
            logger.warning(f"🚫 Queen BLOCKED {opportunity.relay} {opportunity.target_asset}: Net gain too low")
            return decision
        
        # Queen approves
        decision = RedistributionDecision(
            opportunity=opportunity,
            decision='EXECUTE',
            reasoning=reasoning,
            queen_confidence=opportunity.confidence,
            realms_consensus=5,  # All realms agree (simplified for now)
            timestamp=time.time()
        )
        
        logger.info(f"✅ Queen APPROVED {opportunity.relay} {opportunity.target_asset}: {reasoning}")
        return decision
    
    async def execute_redistribution(self, decision: RedistributionDecision) -> Dict:
        """
        Execute Queen's decision to redistribute energy.
        """
        opp = decision.opportunity
        
        if decision.decision != 'EXECUTE':
            logger.info(f"⏸️ Skipping execution for {opp.relay} {opp.target_asset} (decision: {decision.decision})")
            return {
                'success': False,
                'reason': decision.reasoning,
                'decision': decision.decision
            }
        
        if self.dry_run:
            logger.info(f"🔶 DRY-RUN: Would execute {opp.relay} {opp.target_asset} with ${opp.idle_energy:.2f}")
            # Simulate success
            result = {
                'success': True,
                'relay': opp.relay,
                'target_asset': opp.target_asset,
                'deployed_usd': opp.idle_energy,
                'expected_gain_usd': opp.expected_gain_usd,
                'net_energy_gain': opp.net_energy_gain,
                'energy_drain': opp.energy_drain,
                'timestamp': time.time(),
                'dry_run': True
            }
            
            # Track simulated gains
            self.total_net_energy_gained += opp.net_energy_gain
            self.executions_history.append(result)
            
            return result
        
        # LIVE EXECUTION (when dry_run=False)
        logger.info(f"⚡ LIVE: Executing {opp.relay} {opp.target_asset} with ${opp.idle_energy:.2f}")
        
        # 🚫 FAIL-SAFE: Block execution if exchange API was unavailable during scan
        if hasattr(self, '_exchange_api_status') and not self._exchange_api_status.get(opp.relay, True):
            logger.error(f"❌ Execution failed for {opp.relay} {opp.target_asset}: Exchange API unavailable (cannot verify balances)")
            result = {
                'success': False,
                'net_energy_gained': 0.0,
                'reason': 'Exchange API unavailable - stale data risk',
                'opportunity': opp
            }
            self.failed_redistributions.append(result)
            return result
        
        try:
            # Execute via appropriate exchange client
            order = None
            if opp.relay == 'BIN' and self.binance:
                # Binance execution - use quote_qty for USD amount
                order = self.binance.place_market_order(
                    symbol=opp.target_asset,
                    side='buy',
                    quote_qty=opp.idle_energy  # USD amount to spend
                )
            
            elif opp.relay == 'KRK' and self.kraken:
                # Kraken execution - use quote_qty for USD amount
                order = self.kraken.place_market_order(
                    symbol=opp.target_asset,
                    side='buy',
                    quote_qty=opp.idle_energy  # USD amount to spend
                )
            
            elif opp.relay == 'ALP' and self.alpaca:
                # Alpaca execution - use quote_qty for USD amount
                order = self.alpaca.place_market_order(
                    symbol=opp.target_asset,
                    side='buy',
                    quote_qty=opp.idle_energy  # USD amount to spend
                )
            
            else:
                raise Exception(f"Exchange client not available for {opp.relay}")
            
            # ✅ CRITICAL: Extract ACTUAL fill price from order response
            actual_fill_price = 0.0
            actual_qty = 0.0
            actual_cost = 0.0
            actual_fee = 0.0
            order_id = None
            
            if order:
                # Kraken format
                if 'actual_price' in order:
                    actual_fill_price = float(order.get('actual_price', 0))
                    actual_qty = float(order.get('actual_qty', 0))
                    actual_cost = float(order.get('actual_cost', 0))
                    actual_fee = float(order.get('actual_fee', 0))
                    order_id = order.get('txid', order.get('orderId', 'unknown'))
                # Binance format
                elif 'fills' in order:
                    # Binance returns array of fills
                    fills = order.get('fills', [])
                    total_qty = 0.0
                    total_cost = 0.0
                    total_fee = 0.0
                    for fill in fills:
                        fill_qty = float(fill.get('qty', 0))
                        fill_price = float(fill.get('price', 0))
                        fill_fee = float(fill.get('commission', 0))
                        total_qty += fill_qty
                        total_cost += fill_qty * fill_price
                        total_fee += fill_fee
                    actual_qty = total_qty
                    actual_cost = total_cost
                    actual_fee = total_fee
                    actual_fill_price = total_cost / total_qty if total_qty > 0 else 0
                    order_id = order.get('orderId', 'unknown')
                # Alpaca format
                elif 'filled_avg_price' in order:
                    actual_fill_price = float(order.get('filled_avg_price', 0))
                    actual_qty = float(order.get('filled_qty', 0))
                    actual_cost = actual_fill_price * actual_qty
                    order_id = order.get('id', 'unknown')
                # Fallback - try to extract from common fields
                else:
                    actual_fill_price = float(order.get('price', order.get('avgPrice', 0)))
                    actual_qty = float(order.get('executedQty', order.get('qty', 0)))
                    order_id = order.get('id', order.get('orderId', 'unknown'))
            
            # Log actual execution vs expected
            expected_vs_actual = ""
            if actual_fill_price > 0:
                expected_vs_actual = f" | Fill: ${actual_fill_price:.6f} | Qty: {actual_qty:.6f} | Cost: ${actual_cost:.2f} | Fee: ${actual_fee:.4f}"
                logger.info(f"✅ {opp.relay} BUY executed: Order #{order_id}{expected_vs_actual}")
            else:
                logger.warning(f"⚠️ {opp.relay} order executed but couldn't extract fill price: {order}")
                logger.info(f"✅ {opp.relay} order executed: {order}")
            
            result = {
                'success': True,
                'relay': opp.relay,
                'target_asset': opp.target_asset,
                'deployed_usd': opp.idle_energy,
                'expected_gain_usd': opp.expected_gain_usd,
                'net_energy_gain': opp.net_energy_gain,
                'energy_drain': opp.energy_drain,
                'order': order,
                'order_id': order_id,
                'actual_fill_price': actual_fill_price,
                'actual_qty': actual_qty,
                'actual_cost': actual_cost,
                'actual_fee': actual_fee,
                'timestamp': time.time(),
                'dry_run': False
            }

            # Trade audit record (order_id + fills)
            try:
                record = TradeAuditRecord(
                    ts=time.time(),
                    exchange=opp.relay,
                    action='BUY',
                    symbol=opp.target_asset,
                    order_id=order.get('orderId') or order.get('order_id') or order.get('txid'),
                    client_order_id=order.get('clientOrderId'),
                    qty=float(order.get('executedQty', 0) or 0),
                    quote_qty=float(order.get('cummulativeQuoteQty', 0) or 0),
                    avg_fill_price=order.get('avg_fill_price'),
                    fills=order.get('fills') or [],
                    fees=float(order.get('fees', order.get('fee', 0)) or 0),
                    status=order.get('status', 'UNKNOWN'),
                    verified=True if order.get('fills_verified') else False,
                    source='queen_power_redistribution',
                    notes=decision.reasoning
                )
                self._append_trade_audit(record)
            except Exception as e:
                logger.debug(f"Audit record failed: {e}")
            
            self.total_net_energy_gained += opp.net_energy_gain
            self.executions_history.append(result)
            
            return result
        
        except Exception as e:
            logger.error(f"❌ Execution failed for {opp.relay} {opp.target_asset}: {e}")
            result = {
                'success': False,
                'relay': opp.relay,
                'target_asset': opp.target_asset,
                'error': str(e),
                'timestamp': time.time()
            }
            self.executions_history.append(result)
            return result
    
    async def harvest_profitable_positions(self) -> Dict:
        """
        CRITICAL: Sell profitable positions to convert back to stablecoins.
        This replenishes the spendable cash pool.
        """
        logger.info("💰 Step 0: Harvesting profitable positions...")
        
        # Scan all positions
        all_nodes = self.scan_all_energy_nodes()
        
        # Filter for profitable positions that meet minimum threshold
        harvestable_nodes = [
            n for n in all_nodes 
            if n.is_positive_energy and n.unrealized_pnl >= self.min_positive_energy_to_redistribute
        ]
        
        if not harvestable_nodes:
            logger.info("💰 No profitable positions to harvest this cycle.")
            return {'harvested_count': 0, 'total_harvested_usd': 0.0}
        
        logger.info(f"💰 Found {len(harvestable_nodes)} profitable positions to harvest")
        
        harvested_count = 0
        total_harvested = 0.0
        
        for node in harvestable_nodes:
            harvest_percentage = self.profit_redistribution_percentage
            harvest_amount_usd = node.unrealized_pnl * harvest_percentage
            
            if self.dry_run:
                logger.info(f"🔶 DRY-RUN: Would sell {node.symbol} on {node.relay} for ${harvest_amount_usd:.2f} profit")
                harvested_count += 1
                total_harvested += harvest_amount_usd
                continue
            
            # LIVE EXECUTION: Sell position
            try:
                # 🚫 FAIL-SAFE: Block execution if exchange API was unavailable during scan
                # This prevents trading on stale state file data
                if hasattr(self, '_exchange_api_status') and not self._exchange_api_status.get(node.relay, True):
                    logger.error(f"❌ BLOCKED: Cannot harvest {node.symbol} on {node.relay} - Exchange API unavailable (stale data risk)")
                    continue
                
                logger.info(f"⚡ HARVESTING: Selling {harvest_percentage*100:.0f}% of {node.symbol} on {node.relay} (${harvest_amount_usd:.2f})")
                
                # Calculate how much of the position to sell
                sell_quantity = node.quantity * harvest_percentage
                
                order = None
                if node.relay == 'BIN' and self.binance:
                    # Binance uses place_market_order with quantity (not quote_qty for sells)
                    order = self.binance.place_market_order(
                        symbol=node.symbol,
                        side='sell',
                        quantity=sell_quantity
                    )
                    
                elif node.relay == 'KRK' and self.kraken:
                    # Kraken uses place_market_order
                    order = self.kraken.place_market_order(
                        symbol=node.symbol,
                        side='sell',
                        quantity=sell_quantity
                    )
                    
                elif node.relay == 'ALP' and self.alpaca:
                    # Alpaca uses place_market_order
                    order = self.alpaca.place_market_order(
                        symbol=node.symbol,
                        side='sell',
                        quantity=sell_quantity
                    )
                
                # ✅ CRITICAL: Verify ACTUAL fill price from order response
                actual_fill_price = 0.0
                actual_proceeds = 0.0
                actual_fee = 0.0
                order_id = None
                
                if order:
                    # Kraken format
                    if 'actual_price' in order:
                        actual_fill_price = float(order.get('actual_price', 0))
                        actual_proceeds = float(order.get('actual_cost', 0))  # For sells, cost = proceeds
                        actual_fee = float(order.get('actual_fee', 0))
                        order_id = order.get('txid', 'unknown')
                    # Binance format
                    elif 'fills' in order:
                        fills = order.get('fills', [])
                        total_proceeds = 0.0
                        total_fee = 0.0
                        for fill in fills:
                            fill_qty = float(fill.get('qty', 0))
                            fill_price = float(fill.get('price', 0))
                            fill_fee = float(fill.get('commission', 0))
                            total_proceeds += fill_qty * fill_price
                            total_fee += fill_fee
                        actual_proceeds = total_proceeds
                        actual_fee = total_fee
                        actual_fill_price = total_proceeds / sell_quantity if sell_quantity > 0 else 0
                        order_id = order.get('orderId', 'unknown')
                    # Alpaca format
                    elif 'filled_avg_price' in order:
                        actual_fill_price = float(order.get('filled_avg_price', 0))
                        actual_qty = float(order.get('filled_qty', 0))
                        actual_proceeds = actual_fill_price * actual_qty
                        order_id = order.get('id', 'unknown')
                
                # Log actual vs expected
                if actual_fill_price > 0:
                    actual_profit = actual_proceeds - actual_fee - (node.cost_basis * harvest_percentage)
                    logger.info(f"✅ {node.relay} SELL: Order #{order_id} | Fill: ${actual_fill_price:.6f} | Proceeds: ${actual_proceeds:.2f} | Fee: ${actual_fee:.4f} | Profit: ${actual_profit:.2f}")
                    # Update actual harvested amount
                    harvested_count += 1
                    total_harvested += actual_proceeds - actual_fee
                else:
                    logger.warning(f"⚠️ {node.relay} sell executed but couldn't verify fill price: {order}")
                    # Use estimated amount
                    harvested_count += 1
                    total_harvested += harvest_amount_usd
                
            except Exception as e:
                logger.error(f"❌ Failed to harvest {node.symbol} on {node.relay}: {e}")
        
        logger.info(f"💰 Harvest complete: {harvested_count} positions, ${total_harvested:.2f} converted to stablecoins")
        
        return {
            'harvested_count': harvested_count,
            'total_harvested_usd': total_harvested
        }
    
    async def run_redistribution_cycle(self) -> Dict:
        """
        Run one complete redistribution cycle.
        Queen's full intelligence in action.
        """
        cycle_start = time.time()
        
        logger.info("=" * 60)
        logger.info("🐝 QUEEN POWER REDISTRIBUTION CYCLE STARTING")
        logger.info("=" * 60)
        
        # STEP 0: Harvest profitable positions first (convert to stablecoins)
        harvest_result = await self.harvest_profitable_positions()
        
        # Calculate total portfolio value (idle cash + all positions)
        total_idle_cash = 0.0
        total_position_value = 0
        all_nodes = self.scan_all_energy_nodes()
        for node in all_nodes:
            total_position_value += node.position_value_usd
        
        total_portfolio_value = total_idle_cash + total_position_value
        
        logger.info(f"💎 Total Portfolio Value: ${total_portfolio_value:.2f} (Cash: ${total_idle_cash:.2f} + Positions: ${total_position_value:.2f})")
        logger.info(f"⚡ Idle Energy Available: ${total_idle_cash:.2f}")
        
        # Update power station state
        power_state = self.load_state_file('power_station_state.json', {})
        power_state['status'] = 'RUNNING'
        power_state['cycles_run'] = power_state.get('cycles_run', 0) + 1
        power_state['total_portfolio_value'] = total_portfolio_value
        power_state['total_idle_cash'] = total_idle_cash
        power_state['total_position_value'] = total_position_value
        power_state['energy_deployed'] = total_position_value
        power_state['net_flow'] = self.total_net_energy_gained
        power_state['efficiency'] = 0.0  # TODO: Calculate
        power_state['last_update'] = time.time()
        power_state['last_harvest'] = harvest_result
        
        with open('power_station_state.json', 'w') as f:
            json.dump(power_state, f, indent=2)
        
        # Step 1: Analyze opportunities
        logger.info("🔍 Step 1: Analyzing opportunities across all relays...")
        opportunities = await self.analyze_redistribution_opportunities()
        logger.info(f"Found {len(opportunities)} potential opportunities")
        
        if not opportunities:
            logger.info("No opportunities found this cycle.")
            return {
                'cycle_duration': time.time() - cycle_start,
                'opportunities_found': 0,
                'decisions_made': 0,
                'executions_attempted': 0,
                'executions_successful': 0,
                'net_energy_gained': 0.0
            }
        
        # Step 2: Queen analyzes and decides
        logger.info("🐝 Step 2: Queen analyzing and making decisions...")
        decisions = []
        for opp in opportunities:
            decision = await self.queen_analyze_and_decide(opp)
            decisions.append(decision)
            self.decisions_history.append(decision)
        
        # Step 3: Execute approved decisions
        logger.info("⚡ Step 3: Executing approved redistributions...")
        executions = []
        for decision in decisions:
            if decision.decision == 'EXECUTE':
                result = await self.execute_redistribution(decision)
                executions.append(result)
            else:
                # Track blocked drains
                self.total_blocked_drains_avoided += decision.opportunity.energy_drain
        
        # Summary
        successful_executions = sum(1 for e in executions if e.get('success'))
        net_energy_this_cycle = sum(e.get('net_energy_gain', 0.0) for e in executions if e.get('success'))
        
        cycle_summary = {
            'cycle_duration': time.time() - cycle_start,
            'positions_harvested': harvest_result['harvested_count'],
            'energy_harvested_usd': harvest_result['total_harvested_usd'],
            'opportunities_found': len(opportunities),
            'decisions_made': len(decisions),
            'executions_attempted': len(executions),
            'executions_successful': successful_executions,
            'net_energy_gained_this_cycle': net_energy_this_cycle,
            'total_net_energy_gained': self.total_net_energy_gained,
            'total_blocked_drains_avoided': self.total_blocked_drains_avoided
        }
        
        logger.info("=" * 60)
        logger.info("🐝 QUEEN POWER REDISTRIBUTION CYCLE COMPLETE")
        logger.info(f"Duration: {cycle_summary['cycle_duration']:.2f}s")
        logger.info(f"Harvested: {cycle_summary['positions_harvested']} positions → ${cycle_summary['energy_harvested_usd']:.2f}")
        logger.info(f"Opportunities: {cycle_summary['opportunities_found']}")
        logger.info(f"Executions: {cycle_summary['executions_successful']}/{cycle_summary['executions_attempted']}")
        logger.info(f"Net Energy Gained This Cycle: ${cycle_summary['net_energy_gained_this_cycle']:.4f}")
        logger.info(f"Total Net Energy Gained: ${cycle_summary['total_net_energy_gained']:.4f}")
        logger.info(f"Total Blocked Drains Avoided: ${cycle_summary['total_blocked_drains_avoided']:.4f}")
        logger.info("=" * 60)
        
        return cycle_summary
    
    async def run_continuous(self):
        """
        Run continuous redistribution cycles.
        Queen's eternal vigilance.
        """
        logger.info("🐝 Queen Power Redistribution: STARTING CONTINUOUS MODE")
        logger.info(f"Scan interval: {self.scan_interval_seconds}s")
        logger.info(f"Dry run: {self.dry_run}")
        
        cycle_count = 0
        
        try:
            while True:
                cycle_count += 1
                logger.info(f"\n📊 CYCLE {cycle_count} @ {datetime.now().strftime('%H:%M:%S')}")
                
                try:
                    summary = await self.run_redistribution_cycle()
                    
                    # Save state
                    self.save_state()
                    
                except Exception as e:
                    logger.error(f"❌ Cycle {cycle_count} failed: {e}", exc_info=True)
                
                # Wait for next cycle
                logger.info(f"⏳ Waiting {self.scan_interval_seconds}s for next cycle...")
                await asyncio.sleep(self.scan_interval_seconds)
        
        except KeyboardInterrupt:
            logger.info("\n🛑 Queen Power Redistribution: STOPPED BY USER")
            self.save_state()
    
    def save_state(self):
        """Save redistribution state to file."""
        state = {
            'last_update': time.time(),
            'total_net_energy_gained': self.total_net_energy_gained,
            'total_blocked_drains_avoided': self.total_blocked_drains_avoided,
            'decisions_count': len(self.decisions_history),
            'executions_count': len(self.executions_history),
            'recent_decisions': [d.to_dict() for d in self.decisions_history[-10:]],
            'recent_executions': self.executions_history[-10:]
        }
        
        try:
            with open('queen_redistribution_state.json', 'w') as f:
                json.dump(state, f, indent=2)
            logger.debug("💾 State saved to queen_redistribution_state.json")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Queen Power Redistribution Engine")
    parser.add_argument('--live', action='store_true', help='Run in LIVE mode (default: dry-run)')
    parser.add_argument('--once', action='store_true', help='Run one cycle then exit')
    parser.add_argument('--interval', type=int, default=30, help='Scan interval in seconds (default: 30)')
    args = parser.parse_args()
    
    dry_run = not args.live
    
    print("=" * 60)
    print("🐝 QUEEN POWER REDISTRIBUTION ENGINE")
    print("=" * 60)
    print(f"Mode: {'🔶 DRY-RUN' if dry_run else '⚡ LIVE'}")
    print(f"Interval: {args.interval}s")
    print("=" * 60)
    
    # Initialize system
    system = QueenPowerRedistribution(dry_run=dry_run)
    system.scan_interval_seconds = args.interval
    
    if args.once:
        # Run one cycle
        summary = await system.run_redistribution_cycle()
        system.save_state()
        
        print("\n" + "=" * 60)
        print("📊 SINGLE CYCLE COMPLETE")
        print(json.dumps(summary, indent=2))
        print("=" * 60)
    else:
        # Run continuously
        await system.run_continuous()


if __name__ == '__main__':
    asyncio.run(main())
