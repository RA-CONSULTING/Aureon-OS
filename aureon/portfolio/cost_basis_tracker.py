"""
💰 COST BASIS TRACKER
═══════════════════════════════════════════════════════════════

Tracks real purchase prices for all positions across exchanges.
This data feeds into the ecosystem to prevent selling at a loss.

Features:
- Fetches real trade history from exchanges
- Calculates FIFO/average cost basis
- Persists to JSON for session continuity
- Provides profit/loss checks before any sale

Usage:
    tracker = CostBasisTracker()
    tracker.sync_from_exchanges()  # Fetch real purchase prices
    
    # Before selling:
    can_sell, info = tracker.can_sell_profitably('BTCUSDC', current_price=95000)
    if can_sell:
        # Proceed with sale
    else:
        print(f"Would lose ${info['potential_loss']}")
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import json
import os
import time
import builtins
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
from dotenv import load_dotenv
from dataclasses import dataclass, field

# ═══════════════════════════════════════════════════════════════════════════════
# 🔇 WINDOWS UTF-8 FIX - MUST BE BEFORE ANY PRINT STATEMENTS!
# ═══════════════════════════════════════════════════════════════════════════════
import sys
if sys.platform == 'win32' and sys.stdout is sys.__stdout__ and sys.stderr is sys.__stderr__ and sys.stdout.isatty() and sys.stderr.isatty():
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            """Check if stream is already a UTF-8 TextIOWrapper."""
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        def _is_buffer_valid(stream):
            """Check if stream buffer is valid and not closed."""
            if not hasattr(stream, 'buffer'):
                return False
            try:
                return stream.buffer is not None and not stream.buffer.closed
            except (ValueError, AttributeError):
                return False
        # Only wrap if not already UTF-8 wrapped AND buffer is valid (prevents re-wrapping + closed buffer errors)
        if _is_buffer_valid(sys.stdout) and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if _is_buffer_valid(sys.stderr) and not _is_utf8_wrapper(sys.stderr):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

def _safe_print(*args, **kwargs):
    """Safe print that handles closed stdout/stderr."""
    try:
        builtins.print(*args, **kwargs)
    except (ValueError, OSError, IOError):
        # Silently ignore if stdout/stderr is closed
        pass

load_dotenv()

COST_BASIS_FILE = "cost_basis_history.json"


@dataclass
class Trade:
    """Represents a single buy trade lot."""
    price: float
    quantity: float
    timestamp: float = field(default_factory=time.time)
    fee: float = 0.0
    order_id: Optional[str] = None

class CostBasisTracker:
    """Track real cost basis for all positions.
    
    Singleton pattern: multiple callers share the same in-memory instance
    to avoid loading the JSON file from disk multiple times during startup.
    Call CostBasisTracker() normally — the constructor returns the cached
    instance (refreshing clients if supplied).
    """
    _instance = None  # singleton holder

    def __new__(cls, filepath: str = COST_BASIS_FILE, clients=None):
        if cls._instance is not None:
            # Reuse existing instance; inject new clients if provided
            if clients:
                cls._instance.clients.update(clients)
            return cls._instance
        inst = super().__new__(cls)
        cls._instance = inst
        return inst

    def __init__(self, filepath: str = COST_BASIS_FILE, clients=None):
        if getattr(self, '_initialized', False):
            # Already initialised — just merge clients
            if clients:
                self.clients.update(clients)
            return
        self._initialized = True
        self.filepath = filepath
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.trade_lots: Dict[str, List[Trade]] = {}  # 🆕 For FIFO
        self.last_sync: float = 0
        self.clients = clients or {}
        self._last_reload: float = 0  # timestamp of last full disk reload
        self._load()
        self._last_reload = time.time()

    _RELOAD_INTERVAL_SECS = 120  # re-read disk at most every 2 minutes

    def _reload_if_stale(self):
        """Reload positions from disk if the cache is older than _RELOAD_INTERVAL_SECS."""
        if time.time() - self._last_reload > self._RELOAD_INTERVAL_SECS:
            self._load()
            self._last_reload = time.time()
    
    def set_clients(self, clients):
        """Inject shared exchange clients."""
        self.clients = clients

    @staticmethod
    def _strip_known_quote(symbol: str) -> str:
        """Strip a known quote suffix without using rstrip character semantics."""
        symbol = (symbol or '').replace('/', '')
        for quote in ('USDT', 'USDC', 'ZUSD', 'USD', 'EUR', 'GBP', 'BTC', 'ETH'):
            if symbol.endswith(quote) and len(symbol) > len(quote):
                return symbol[:-len(quote)]
        return symbol

    @staticmethod
    def _normalize_kraken_pair(pair: str) -> str:
        """Convert Kraken pair naming (e.g., XXBTZUSD, XPEPEZUSD) to BTCUSD/PEPEUSD style."""
        raw = (pair or '').upper()
        p = raw.replace('/', '')
        if not p:
            return p

        if '/' in raw:
            base, quote = raw.split('/', 1)
            base = base.lstrip('XZ')
            quote = quote.lstrip('XZ')
            if base in ('XBT', 'BT'):
                base = 'BTC'
            if base in ('XDG', 'DG'):
                base = 'DOGE'
            if quote == 'XBT':
                quote = 'BTC'
            return f"{base}{quote}"

        quotes = ('USDT', 'USDC', 'USD', 'EUR', 'GBP', 'BTC', 'ETH')
        for quote in quotes:
            zq = f"Z{quote}"
            if p.endswith(zq):
                base = p[:-len(zq)]
            elif p.endswith(quote):
                base = p[:-len(quote)]
            else:
                continue

            if base.startswith(('XX', 'ZZ')):
                base = base[2:]
            elif base.startswith(('X', 'Z')):
                base = base[1:]

            if base in ('XBT', 'BT'):
                base = 'BTC'
            if base in ('XDG', 'DG'):
                base = 'DOGE'
            return f"{base}{quote}"

        stripped = p
        if stripped.startswith(('XX', 'ZZ')):
            stripped = stripped[2:]
        elif stripped.startswith(('X', 'Z')):
            stripped = stripped[1:]
        if stripped in ('XBT', 'BT'):
            return 'BTC'
        if stripped in ('XDG', 'DG'):
            return 'DOGE'
        return stripped.replace('XBT', 'BTC')

    def _load(self):
        """Load cost basis data from file."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    data = json.load(f)
                    self.positions = data.get('positions', {})
                    self.last_sync = data.get('last_sync', 0)
                    
                    # 🆕 Load trade lots for FIFO
                    trade_lots_data = data.get('trade_lots', {})
                    self.trade_lots = {
                        k: [Trade(**t) for t in v]
                        for k, v in trade_lots_data.items()
                    }
                    
                    _safe_print(f"📊 Cost Basis Tracker: Loaded {len(self.positions)} positions and {len(self.trade_lots)} trade lots from {self.filepath}")
            except Exception as e:
                _safe_print(f"⚠️ Failed to load cost basis file: {e}")
                self.positions = {}
                self.trade_lots = {}
        
        # 🆕 SYNC with Orca's Tracked Positions
        if os.path.exists("tracked_positions.json"):
            try:
                with open("tracked_positions.json", "r") as f:
                    tracked = json.load(f)
                    added_count = 0
                    for sym, data in tracked.items():
                        # Normalize symbol (remove / for matching)
                        norm_sym = sym.replace('/', '')
                        if norm_sym not in self.positions:
                            self.positions[norm_sym] = {
                                'exchange': data.get('exchange', 'unknown'),
                                'avg_entry_price': data.get('entry_price', 0),
                                'total_quantity': data.get('entry_qty', 0),
                                'total_cost': data.get('entry_cost', 0),
                                'total_fees': 0,
                                'trade_count': 1,
                                'last_trade': data.get('entry_time', time.time()),
                                'synced_at': time.time()
                            }
                            added_count += 1
                    if added_count > 0:
                        _safe_print(f"📊 Cost Basis Tracker: Integrated {added_count} positions from tracked_positions.json")
            except Exception as e:
                _safe_print(f"⚠️ Failed to integrate tracked positions: {e}")
    
    def _save(self):
        """Save cost basis data to file (atomic write: temp → rename)."""
        try:
            # 🆕 Serialize trade lots
            trade_lots_serializable = {
                k: [t.__dict__ for t in v]
                for k, v in self.trade_lots.items()
            }
            
            data = {
                'positions': self.positions,
                'trade_lots': trade_lots_serializable,
                'last_sync': self.last_sync,
                'updated_at': datetime.now().isoformat()
            }
            import tempfile
            tmp_dir = os.path.dirname(os.path.abspath(self.filepath)) or '.'
            fd, tmp_path = tempfile.mkstemp(dir=tmp_dir, suffix='.tmp', prefix='cost_basis_')
            try:
                with os.fdopen(fd, 'w') as f:
                    json.dump(data, f, indent=2)
                os.replace(tmp_path, self.filepath)
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except Exception as e:
            print(f"⚠️ Failed to save cost basis file: {e}")

    def _should_update_position(self, position_key: str, new_cost: float) -> bool:
        """Guard: don't overwrite FIFO-reconciled positions with worse data.
        
        Returns True if the position should be updated, False if the existing
        reconciled data should be preserved.
        """
        existing = self.positions.get(position_key)
        if not existing:
            return True  # New position, always accept
        
        # If existing was reconciled from real trade history, protect it
        if existing.get('source') == 'full_reconcile':
            existing_cost = existing.get('total_cost', 0)
            # Only allow update if new data is strictly better (has real cost and existing is zero)
            if existing_cost > 0 and (new_cost == 0 or new_cost is None):
                return False  # Protect: don't overwrite real cost with zero
        return True
    
    def sync_from_binance(self, symbols: list = None) -> int:
        """Sync cost basis from Binance trade history.
        
        Returns number of positions updated.
        """
        try:
            if self.clients and 'binance' in self.clients:
                client = self.clients['binance']
            else:
                from aureon.exchanges.binance_client import get_binance_client
                client = get_binance_client()
        except Exception as e:
            print(f"⚠️ Failed to initialize Binance client: {e}")
            return 0
        
        # Get current balances to know which symbols to check
        account = client.account()
        balances = account.get('balances', [])
        
        updated = 0
        for bal in balances:
            asset = bal['asset']
            free = float(bal.get('free', 0))
            locked = float(bal.get('locked', 0))
            total = free + locked
            
            if total <= 0:
                continue
            
            # Skip stablecoins and Binance Earn (LD) assets
            if asset in ['USDC', 'USDT', 'USD', 'EUR', 'GBP', 'BUSD', 'FDUSD', 'TUSD'] or asset.startswith('LD'):
                continue
            
            # 🔧 Only try EUR for major coins that Binance actually supports
            BINANCE_EUR_SUPPORTED = {'BTC', 'ETH', 'BNB', 'XRP', 'ADA', 'SOL', 'DOT', 'DOGE', 'SHIB', 'MATIC', 'LTC', 'AVAX', 'LINK', 'ATOM'}
            quote_options = ['USDC', 'USDT']
            if asset in BINANCE_EUR_SUPPORTED:
                quote_options.append('EUR')
            
            # Try different quote currencies
            for quote in quote_options:
                symbol = f"{asset}{quote}"
                try:
                    cost_basis = client.calculate_cost_basis(symbol)
                    if cost_basis and cost_basis['total_quantity'] > 0:
                        position_key = f"binance:{symbol}"
                        if not self._should_update_position(position_key, cost_basis.get('total_cost', 0)):
                            break  # Protected reconciled position
                        self.positions[position_key] = {
                            'exchange': 'binance',
                            'symbol': symbol,
                            'asset': asset,
                            'quote': quote,
                            'avg_entry_price': cost_basis['avg_entry_price'],
                            'total_quantity': cost_basis['total_quantity'],
                            'total_cost': cost_basis['total_cost'],
                            'total_fees': cost_basis['total_fees'],
                            'trade_count': cost_basis['trade_count'],
                            'first_trade': cost_basis['first_trade'],
                            'last_trade': cost_basis['last_trade'],
                            'synced_at': time.time()
                        }
                        updated += 1
                        _safe_print(f"   📦 {position_key}: avg entry ${cost_basis['avg_entry_price']:.6f} "
                              f"({cost_basis['trade_count']} trades)")
                        break
                except Exception as e:
                    continue
        
        self.last_sync = time.time()
        self._save()
        return updated
    
    def sync_from_kraken(self) -> int:
        """Sync cost basis from Kraken trade history."""
        try:
            if self.clients and 'kraken' in self.clients:
                client = self.clients['kraken']
            else:
                from aureon.exchanges.kraken_client import get_kraken_client
                client = get_kraken_client()

            if getattr(client, 'dry_run', False):
                print("   ⚪ Kraken in dry-run mode - skipping")
                return 0
        except Exception as e:
            print(f"   ⚠️ Failed to initialize Kraken client: {e}")
            return 0
        
        # Get trade history
        try:
            trades = client.get_trades_history_dict()
            if not trades:
                print("   ⚪ No Kraken trade history found")
                return 0
        except Exception as e:
            print(f"   ⚠️ Failed to get Kraken trade history: {e}")
            return 0
        
        # Group trades by pair and calculate cost basis
        pair_trades = {}
        for _trade_id, trade in trades.items():
            pair = trade.get('pair', '')
            if pair not in pair_trades:
                pair_trades[pair] = []
            pair_trades[pair].append(trade)
        
        updated = 0
        for pair, pair_trade_list in pair_trades.items():
            # Reset trade lots for this pair to rebuild from history
            symbol_norm = self._normalize_kraken_pair(pair)
            position_key = f"kraken:{symbol_norm}"
            self.trade_lots[position_key] = []

            total_qty = 0.0
            total_cost = 0.0
            total_fees = 0.0
            buy_trades = 0
            first_trade = None
            last_trade = None
            
            for trade in sorted(pair_trade_list, key=lambda x: float(x.get('time', 0))):
                trade_type = trade.get('type', '')
                qty = float(trade.get('vol', 0))
                price = float(trade.get('price', 0))
                fee = float(trade.get('fee', 0))
                timestamp = float(trade.get('time', 0))
                
                if trade_type == 'buy':
                    # Add to lots for FIFO
                    self.trade_lots[position_key].append(Trade(price=price, quantity=qty, fee=fee, timestamp=timestamp))
                    
                    total_qty += qty
                    total_cost += qty * price
                    total_fees += fee
                    buy_trades += 1
                elif trade_type == 'sell':
                    # Apply FIFO logic to lots
                    sell_qty_rem = qty
                    for lot in self.trade_lots.get(position_key, []):
                        if sell_qty_rem <= 0: break
                        take_qty = min(lot.quantity, sell_qty_rem)
                        lot.quantity -= take_qty
                        sell_qty_rem -= take_qty

                    total_qty -= qty
                    if total_qty > 0:
                        # Recalculate average cost from remaining lots
                        new_total_cost = sum(l.price * l.quantity for l in self.trade_lots.get(position_key, []))
                        total_cost = new_total_cost
                
                if first_trade is None or timestamp < first_trade:
                    first_trade = timestamp
                if last_trade is None or timestamp > last_trade:
                    last_trade = timestamp
            
            if total_qty > 0 and buy_trades > 0:
                avg_entry = total_cost / total_qty
                # Normalize pair name without stripping in-symbol X/Z characters
                symbol = self._normalize_kraken_pair(pair)
                position_key = f"kraken:{symbol}"
                if not self._should_update_position(position_key, total_cost):
                    continue  # Protected reconciled position
                self.positions[position_key] = {
                    'exchange': 'kraken',
                    'symbol': symbol,
                    'asset': symbol[:-3] if len(symbol) > 3 else symbol,
                    'quote': symbol[-3:] if len(symbol) > 3 else 'USD',
                    'avg_entry_price': avg_entry,
                    'total_quantity': total_qty,
                    'total_cost': total_cost,
                    'total_fees': total_fees,
                    'trade_count': buy_trades,
                    'first_trade': int(first_trade * 1000) if first_trade else None,
                    'last_trade': int(last_trade * 1000) if last_trade else None,
                    'synced_at': time.time()
                }
                updated += 1
                _safe_print(f"   📦 {position_key}: avg entry ${avg_entry:.6f} ({buy_trades} trades)")
        
        self._save()
        return updated
    
    def sync_from_alpaca(self) -> int:
        """Sync cost basis from Alpaca trade history."""
        try:
            if self.clients and 'alpaca' in self.clients:
                client = self.clients['alpaca']
            else:
                from aureon.exchanges.alpaca_client import AlpacaClient
                client = AlpacaClient()
        except Exception as e:
            print(f"   ⚠️ Failed to initialize Alpaca client: {e}")
            return 0
        
        # Alpaca provides positions with avg_entry_price directly!
        try:
            positions = client.get_positions()
            if not positions:
                print("   ⚪ No Alpaca positions found")
                return 0
        except Exception as e:
            print(f"   ⚠️ Failed to get Alpaca positions: {e}")
            return 0
        
        updated = 0
        for pos in positions:
            symbol = pos.get('symbol', '')
            avg_entry = float(pos.get('avg_entry_price', 0))
            qty = float(pos.get('qty', 0))
            
            if avg_entry > 0 and qty > 0:
                position_key = f"alpaca:{symbol}"
                if not self._should_update_position(position_key, avg_entry * qty):
                    updated += 1
                    continue  # Protected reconciled position
                
                # 🆕 Create a single trade lot for Alpaca positions since it gives aggregates
                self.trade_lots[position_key] = [Trade(price=avg_entry, quantity=qty)]
                
                self.positions[position_key] = {
                    'exchange': 'alpaca',
                    'symbol': symbol,
                    'asset': symbol,
                    'quote': 'USD',
                    'avg_entry_price': avg_entry,
                    'total_quantity': qty,
                    'total_cost': avg_entry * qty,
                    'total_fees': 0,  # Alpaca has zero commission
                    'trade_count': 1,  # Position-based, not trade-based
                    'synced_at': time.time()
                }
                updated += 1
                _safe_print(f"   📦 {position_key}: avg entry ${avg_entry:.6f}")
        
        self._save()
        return updated
    
    def sync_from_capital(self) -> int:
        """Sync cost basis from Capital.com positions."""
        try:
            if self.clients and 'capital' in self.clients:
                client = self.clients['capital']
            else:
                from aureon.exchanges.capital_client import CapitalClient
                client = CapitalClient()
            
            if not getattr(client, 'enabled', False):
                print("   ⚪ Capital.com not authenticated - skipping")
                return 0
        except Exception as e:
            print(f"   ⚠️ Failed to initialize Capital client: {e}")
            return 0
        
        # Capital.com provides positions with entry price
        try:
            positions = client.get_positions()
            if not positions:
                print("   ⚪ No Capital.com positions found")
                return 0
        except Exception as e:
            print(f"   ⚠️ Failed to get Capital.com positions: {e}")
            return 0
        
        updated = 0
        for pos in positions:
            symbol = pos.get('market', {}).get('epic', '') or pos.get('epic', '')
            avg_entry = float(pos.get('position', {}).get('openLevel', 0) or pos.get('openLevel', 0))
            qty = float(pos.get('position', {}).get('size', 0) or pos.get('size', 0))
            
            if avg_entry > 0 and qty != 0:
                position_key = f"capital:{symbol}"
                if not self._should_update_position(position_key, avg_entry * abs(qty)):
                    updated += 1
                    continue  # Protected reconciled position

                # 🆕 Create a single trade lot for Capital positions
                if qty > 0: # Only for LONG positions
                    self.trade_lots[position_key] = [Trade(price=avg_entry, quantity=abs(qty))]

                self.positions[position_key] = {
                    'exchange': 'capital',
                    'symbol': symbol,
                    'asset': symbol,
                    'quote': 'USD',
                    'avg_entry_price': avg_entry,
                    'total_quantity': abs(qty),
                    'total_cost': avg_entry * abs(qty),
                    'total_fees': 0,  # Spread-based
                    'trade_count': 1,
                    'synced_at': time.time(),
                    'direction': 'LONG' if qty > 0 else 'SHORT'
                }
                updated += 1
                direction = '📈' if qty > 0 else '📉'
                _safe_print(f"   {direction} {position_key}: entry ${avg_entry:.4f} x {abs(qty)}")
        
        self._save()
        return updated
    
    def sync_from_exchanges(self) -> int:
        """Sync cost basis from ALL exchanges."""
        print("\n📊 SYNCING COST BASIS FROM ALL EXCHANGES...")
        print("=" * 60)
        
        total = 0
        
        print("\n🟡 Syncing from Binance...")
        total += self.sync_from_binance()
        
        print("\n🐙 Syncing from Kraken...")
        total += self.sync_from_kraken()
        
        print("\n🦙 Syncing from Alpaca...")
        total += self.sync_from_alpaca()
        
        print("\n💼 Syncing from Capital.com...")
        total += self.sync_from_capital()
        
        print(f"\n✅ Synced {total} positions with real cost basis")
        print("=" * 60)
        
        return total
    
    def _find_position(self, symbol: str, exchange: str = None) -> Optional[tuple[Dict[str, Any], str]]:
        """
        🔍 ENHANCED: 5-strategy symbol matching with quote currency swapping.
        
        Returns: (position_dict, matched_key) if found, else (None, None)
        
        Strategies:
        1. Direct match with exchange prefix (binance:SHELL/USDT)
        2. Match without exchange prefix (SHELL/USDT)
        3. Normalized format without slashes (binance:SHELLUSDT, SHELLUSDT)
        4. Quote currency swapping (SHELL/USDT → SHELLUSDC, SHELL/USD)
        5. Deep base asset match (SHELL → any SHELL-based pair)
        """
        pos = None
        _matched_key = None

        def _is_open_position(candidate: Optional[Dict[str, Any]]) -> bool:
            """Ignore stale/closed snapshots so they don't shadow real open positions."""
            if not candidate:
                return False
            try:
                qty = float(candidate.get('total_quantity', 0) or 0)
            except (TypeError, ValueError):
                return False
            return qty > 0.0000001

        def _exchange_matches(candidate_key: str, candidate: Optional[Dict[str, Any]]) -> bool:
            """When exchange context is provided, don't cross-match to another venue."""
            if not exchange:
                return True
            normalized_exchange = exchange.lower()
            if candidate_key.startswith(f"{normalized_exchange}:"):
                return True
            candidate_exchange = str((candidate or {}).get('exchange', '')).lower()
            return candidate_exchange == normalized_exchange
        
        # Strategy 1: Direct match with exchange context
        if exchange:
            position_key = f"{exchange.lower()}:{symbol}"
            pos = self.positions.get(position_key)
            if _is_open_position(pos):
                return (pos, position_key)
        
        # Strategy 2: Try without exchange prefix
        pos = self.positions.get(symbol)
        if _is_open_position(pos) and _exchange_matches(symbol, pos):
            return (pos, symbol)
        
        # Strategy 3: Try normalized (no slashes)
        norm_symbol = symbol.replace('/', '')
        if exchange:
            norm_key = f"{exchange.lower()}:{norm_symbol}"
            pos = self.positions.get(norm_key)
            if _is_open_position(pos):
                return (pos, norm_key)

        pos = self.positions.get(norm_symbol)
        if _is_open_position(pos) and _exchange_matches(norm_symbol, pos):
            return (pos, norm_symbol)
        
        # Strategy 4: Try swapping quote currencies (USDT ↔ USDC ↔ USD)
        # Extract base asset
        if '/' in symbol:
            base = symbol.split('/')[0]
        else:
            base = self._strip_known_quote(symbol)
        
        # Try all quote currency combinations
        for quote_in in ['USDT', 'USDC', 'USD', 'EUR', 'GBP']:
            if symbol.endswith(quote_in) or symbol.endswith(f'/{quote_in}'):
                # Try other quotes
                for quote_out in ['USDT', 'USDC', 'USD', 'ZUSD', 'USDC.P']:
                    # Try with slash and without
                    test_symbols = [
                        f"{base}/{quote_out}",
                        f"{base}{quote_out}",
                    ]
                    
                    for test_symbol in test_symbols:
                        if exchange:
                            test_key = f"{exchange.lower()}:{test_symbol}"
                            pos = self.positions.get(test_key)
                            if _is_open_position(pos):
                                # Debug message
                                # print(f"   ✓ Matched via quote swap: {symbol} → {test_key}")
                                return (pos, test_key)

                        pos = self.positions.get(test_symbol)
                        if _is_open_position(pos) and _exchange_matches(test_symbol, pos):
                            # Debug message
                            # print(f"   ✓ Matched via quote swap: {symbol} → {test_symbol}")
                            return (pos, test_symbol)
        
        # Strategy 5: Deep base asset match
        base_asset = symbol.split('/')[0] if '/' in symbol else symbol
        # Remove common quote assets to find base
        for quote in ['USD', 'USDT', 'USDC', 'EUR', 'GBP', 'BTC', 'ETH']:
            if base_asset.endswith(quote) and len(base_asset) > len(quote):
                base_asset = base_asset[:-len(quote)]
                break
        
        for s, p in self.positions.items():
            stored_symbol = p.get('symbol') or s
            # Strip exchange prefix (e.g., kraken:EUL -> EUL) before base matching
            symbol_part = stored_symbol.split(':', 1)[1] if ':' in stored_symbol else stored_symbol
            normalized_symbol = symbol_part.replace('/', '')
            if (
                normalized_symbol.startswith(base_asset)
                and _is_open_position(p)
                and _exchange_matches(s, p)
            ):
                return (p, s)
        
        # ─── Strategy 6: STALE POSITION FALLBACK ────────────────────────
        # If all strategies above failed (usually because total_quantity == 0
        # from a previous sell), re-run matching WITHOUT the qty check.
        # This recovers entry-price data for positions that were sold and
        # re-bought outside the tracker's visibility (manual buys, buys made
        # before tracker existed, etc.).  The caller gets the LAST KNOWN
        # entry price — better than falling back to current_price.
        def _has_valid_entry(candidate: Optional[Dict[str, Any]]) -> bool:
            if not candidate:
                return False
            try:
                entry = float(candidate.get('avg_entry_price', 0) or 0)
            except (TypeError, ValueError):
                return False
            return entry > 0

        # Try strategies 1-5 again, this time accepting qty==0 positions
        # with a recorded entry price.  Priority: exchange-prefixed → bare.
        if exchange:
            for test_key in [f"{exchange.lower()}:{symbol}",
                             f"{exchange.lower()}:{symbol.replace('/', '')}",
                             symbol,
                             symbol.replace('/', '')]:
                pos = self.positions.get(test_key)
                if _has_valid_entry(pos) and _exchange_matches(test_key, pos):
                    return (pos, test_key)

        # Quote-swap pass (relaxed)
        for quote_in in ['USDT', 'USDC', 'USD', 'EUR', 'GBP']:
            if symbol.endswith(quote_in) or symbol.endswith(f'/{quote_in}'):
                for quote_out in ['USDT', 'USDC', 'USD', 'ZUSD']:
                    for fmt in [f"{base_asset}/{quote_out}", f"{base_asset}{quote_out}"]:
                        for test_key in ([f"{exchange.lower()}:{fmt}", fmt]
                                         if exchange else [fmt]):
                            pos = self.positions.get(test_key)
                            if _has_valid_entry(pos) and _exchange_matches(test_key, pos):
                                return (pos, test_key)
                break  # only first matching quote_in

        # Deep base-asset scan (relaxed)
        for s, p in self.positions.items():
            stored_symbol = p.get('symbol') or s
            symbol_part = stored_symbol.split(':', 1)[1] if ':' in stored_symbol else stored_symbol
            normalized_symbol = symbol_part.replace('/', '')
            if (
                normalized_symbol.startswith(base_asset)
                and _has_valid_entry(p)
                and _exchange_matches(s, p)
            ):
                return (p, s)

        return (None, None)
    
    def get_cost_basis(self, symbol: str, exchange: str = None) -> Optional[Dict[str, Any]]:
        """Get cost basis for a symbol, optionally scoped to an exchange."""
        pos, _matched_key = self._find_position(symbol, exchange)
        return pos

    def get_entry_price(self, symbol: str, exchange: str = None) -> Optional[float]:
        """Get average entry price for a symbol using 5-strategy matching."""
        pos, _matched_key = self._find_position(symbol, exchange)
        if pos:
            # Prefer verified fills when available
            if pos.get('fills_verified') and pos.get('avg_fill_price'):
                return pos.get('avg_fill_price')
            return pos.get('avg_entry_price')
        return None

    def get_verified_entry_price(self, symbol: str, exchange: str = None) -> Optional[float]:
        """Return entry price only if backed by verified fills + order_id."""
        pos, _matched_key = self._find_position(symbol, exchange)
        if not pos:
            return None
        if not pos.get('fills_verified'):
            return None
        if not pos.get('last_order_id'):
            return None
        return pos.get('avg_fill_price') or pos.get('avg_entry_price')
    
    def set_entry_price(self, symbol: str, price: float, quantity: float, 
                       exchange: str = 'binance', fee: float = 0.0, order_id: str = None):
        """Manually set entry price for a position (for new trades)."""
        asset = symbol[:-4] if symbol.endswith(('USDC', 'USDT')) else symbol[:-3]
        quote = symbol[-4:] if symbol.endswith(('USDC', 'USDT')) else symbol[-3:]
        
        # Use a unique key for each position: exchange + symbol
        position_key = f"{exchange.lower()}:{symbol}"
        
        # 🆕 Also add to trade_lots for FIFO
        if position_key not in self.trade_lots:
            self.trade_lots[position_key] = []
        self.trade_lots[position_key].append(Trade(price=price, quantity=quantity, fee=fee, order_id=order_id))

        # 🔧 ALSO store normalized versions for fallback matching
        norm_symbol = symbol.replace('/', '')  # Remove slashes
        norm_key = f"{exchange.lower()}:{norm_symbol}"

        position_data = {
            'exchange': exchange,
            'symbol': symbol,
            'asset': asset,
            'quote': quote,
            'avg_entry_price': price,
            'total_quantity': quantity,
            'total_cost': price * quantity,
            'total_fees': fee,
            'trade_count': 1,
            'first_trade': int(time.time() * 1000),
            'last_trade': int(time.time() * 1000),
            'synced_at': time.time(),
            'source': 'manual',
            'order_ids': [order_id] if order_id else [],
            'last_order_id': order_id,
            'avg_fill_price': price,
            'fills_verified': True if order_id else False,
            'last_fills': []
        }
        
        # Store under BOTH keys for better matching
        self.positions[position_key] = position_data
        if norm_symbol != symbol:
            self.positions[norm_key] = position_data.copy()
            # 🆕 Copy trade lots for normalized key
            self.trade_lots[norm_key] = self.trade_lots[position_key][:]
        
        self._save()
        _safe_print(f"   💾 Logged entry: {position_key} @ ${price:.6f} x {quantity} (Order: {order_id})")
        if norm_symbol != symbol:
            _safe_print(f"      Also indexed as: {norm_key}")
    
    def record_trade(self, symbol: str, side: str, quantity: float, price: float,
                    exchange: str, fee: float = 0.0, order_id: str = None) -> Dict[str, Any]:
        """
        Record a trade using FIFO accounting for cost basis.
        
        This is the central method for all trade recording - handles both buys and sells
        with proper FIFO cost basis calculation.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDC')
            side: 'buy' or 'sell'
            quantity: Quantity traded
            price: Price per unit
            exchange: Exchange name
            fee: Transaction fee
            order_id: Order ID for verification
            
        Returns:
            Dict with trade result info including realized P&L for sells
        """
        if quantity <= 0 or price <= 0:
            return {'error': 'Invalid quantity or price'}
        
        is_buy = side.upper() == 'BUY'
        position_key = f"{exchange.lower()}:{symbol}"
        
        # Initialize position if it doesn't exist
        if position_key not in self.positions:
            self.positions[position_key] = {
                'exchange': exchange,
                'symbol': symbol,
                'asset': symbol.split('/')[0] if '/' in symbol else self._strip_known_quote(symbol),
                'quote': symbol.split('/')[1] if '/' in symbol else symbol[-3:],
                'avg_entry_price': 0,
                'total_quantity': 0,
                'total_cost': 0,
                'total_fees': 0,
                'trade_count': 0,
                'first_trade': int(time.time() * 1000),
                'last_trade': int(time.time() * 1000),
                'synced_at': time.time(),
                'order_ids': [],
                'last_order_id': order_id,
                'avg_fill_price': price,
                'fills_verified': True if order_id else False,
                'last_fills': []
            }
            self.trade_lots[position_key] = []
        
        pos = self.positions[position_key]
        lots = self.trade_lots.get(position_key, [])
        
        result = {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': price,
            'exchange': exchange,
            'fee': fee,
            'order_id': order_id
        }
        
        if is_buy:
            # BUY: Add to lots
            new_lot = Trade(price=price, quantity=quantity, fee=fee, timestamp=time.time(), order_id=order_id)
            lots.append(new_lot)
            
            # Update aggregates
            pos['total_quantity'] += quantity
            pos['total_cost'] += quantity * price
            pos['total_fees'] += fee
            pos['trade_count'] += 1
            pos['avg_entry_price'] = pos['total_cost'] / pos['total_quantity'] if pos['total_quantity'] > 0 else 0
            pos['last_trade'] = int(time.time() * 1000)
            if order_id and order_id not in pos.get('order_ids', []):
                pos['order_ids'].append(order_id)
            pos['last_order_id'] = order_id
            pos['avg_fill_price'] = price
            pos['fills_verified'] = True if order_id else pos.get('fills_verified', False)
            
            result['action'] = 'bought'
            result['new_quantity'] = pos['total_quantity']
            result['new_cost_basis'] = pos['total_cost']
            
        else:
            # SELL: Use FIFO to calculate cost basis of sale
            sell_qty_remaining = quantity
            cost_basis_of_sale = 0.0
            realized_pnl = 0.0
            
            # Process lots in FIFO order (oldest first)
            lots_to_remove = []
            for i, lot in enumerate(lots):
                if sell_qty_remaining <= 0:
                    break
                
                qty_from_lot = min(lot.quantity, sell_qty_remaining)
                cost_from_lot = qty_from_lot * lot.price
                
                cost_basis_of_sale += cost_from_lot
                realized_pnl += qty_from_lot * (price - lot.price)  # Gross P&L
                
                # Reduce lot quantity
                lot.quantity -= qty_from_lot
                sell_qty_remaining -= qty_from_lot
                
                # Mark empty lots for removal
                if lot.quantity <= 0.000001:
                    lots_to_remove.append(i)
            
            # Remove empty lots (in reverse order to maintain indices)
            for i in reversed(lots_to_remove):
                lots.pop(i)
            
            # Account for fees (only exit fee since entry fees are in cost basis)
            exit_fee = quantity * price * 0.001  # Assume 0.1% fee
            realized_pnl -= exit_fee
            
            # Update aggregates
            pos['total_quantity'] -= quantity
            pos['total_cost'] -= cost_basis_of_sale
            pos['total_fees'] += fee
            pos['trade_count'] += 1
            pos['last_trade'] = int(time.time() * 1000)
            if order_id and order_id not in pos.get('order_ids', []):
                pos['order_ids'].append(order_id)
            pos['last_order_id'] = order_id
            
            # Recalculate average entry price for remaining position
            if pos['total_quantity'] > 0.000001:
                pos['avg_entry_price'] = pos['total_cost'] / pos['total_quantity']
            else:
                # Position closed
                pos['total_quantity'] = 0
                pos['total_cost'] = 0
                pos['avg_entry_price'] = 0
            
            result['action'] = 'sold'
            result['cost_basis_of_sale'] = cost_basis_of_sale
            result['realized_pnl'] = realized_pnl
            result['exit_fee'] = exit_fee
            result['remaining_quantity'] = pos['total_quantity']
            result['remaining_cost_basis'] = pos['total_cost']
        
        # Update trade lots
        self.trade_lots[position_key] = lots
        self.positions[position_key] = pos
        
        self._save()
        return result
    
    def update_position(self, symbol: str, new_qty: float, new_price: float,
                       exchange: str, is_buy: bool = True, fee: float = 0.0, order_id: str = None):
        """
        Update position after a trade.
        NOTE: For sells, this now just updates the aggregate. FIFO logic is in `record_trade`.
        """
        position_key = f"{exchange.lower()}:{symbol}"
        pos = self.positions.get(position_key, {})

        old_qty = pos.get('total_quantity', 0)
        old_cost = pos.get('total_cost', 0)
        old_fees = pos.get('total_fees', 0)
        trade_count = pos.get('trade_count', 0)
        order_ids = pos.get('order_ids', [])

        if is_buy:
            # Add to position
            new_total_qty = old_qty + new_qty
            new_total_cost = old_cost + (new_qty * new_price)
            new_avg_price = new_total_cost / new_total_qty if new_total_qty > 0 else 0
            trade_count += 1
            if order_id and order_id not in order_ids:
                order_ids.append(order_id)
        else:
            # Reduce position (keep same avg cost for remaining)
            new_total_qty = max(old_qty - new_qty, 0)
            
            # 🆕 Recalculate from remaining lots for accuracy
            remaining_lots = self.trade_lots.get(position_key, [])
            if remaining_lots:
                new_total_cost = sum(l.price * l.quantity for l in remaining_lots)
                new_total_qty_from_lots = sum(l.quantity for l in remaining_lots)
                new_avg_price = new_total_cost / new_total_qty_from_lots if new_total_qty_from_lots > 0 else 0
                new_total_qty = new_total_qty_from_lots # Ensure consistency
            else: # Fallback if lots are gone
                avg_price = old_cost / old_qty if old_qty > 0 else 0
                new_total_cost = new_total_qty * avg_price
                new_avg_price = avg_price

        if new_total_qty > 0.000001: # Use a small threshold for dust
            asset = symbol[:-4] if symbol.endswith(('USDC', 'USDT')) else symbol[:-3]
            quote = symbol[-4:] if symbol.endswith(('USDC', 'USDT')) else symbol[-3:]

            self.positions[position_key] = {
                'exchange': pos.get('exchange', exchange),
                'symbol': symbol,
                'asset': asset,
                'quote': quote,
                'avg_entry_price': new_avg_price,
                'total_quantity': new_total_qty,
                'total_cost': new_total_cost,
                'total_fees': old_fees + fee,
                'trade_count': trade_count,
                'first_trade': pos.get('first_trade', int(time.time() * 1000)),
                'last_trade': int(time.time() * 1000),
                'synced_at': time.time(),
                'order_ids': order_ids,
                'last_order_id': order_id or pos.get('last_order_id'),
                'avg_fill_price': new_price if is_buy else pos.get('avg_fill_price'),
                'fills_verified': True if order_id else pos.get('fills_verified', False),
                'last_fills': pos.get('last_fills', [])
            }
        else:
            # Position closed
            self.positions.pop(position_key, None)
            self.trade_lots.pop(position_key, None) # 🆕 Also remove lots

        self._save()

    def record_order_execution(
        self,
        *,
        exchange: str,
        symbol: str,
        side: str,
        order_id: str,
        fills: list,
        avg_fill_price: Optional[float],
        fees: float,
        executed_qty: float,
    ) -> None:
        """Record a validated execution using order_id + fills."""
        if not symbol or not exchange:
            return
        if executed_qty <= 0:
            return

        _is_buy = str(side or '').upper() == 'BUY'
        price = float(avg_fill_price or 0)
        if price <= 0:
            return

        # 🆕 Use the new central trade recording method
        self.record_trade(
            symbol=symbol,
            side=side,
            quantity=executed_qty,
            price=price,
            exchange=exchange,
            fee=float(fees or 0),
            order_id=order_id
        )

        position_key = f"{exchange.lower()}:{symbol}"
        pos = self.positions.get(position_key)
        if pos:
            pos['last_order_id'] = order_id
            pos['avg_fill_price'] = price
            pos['fills_verified'] = True if fills else False
            pos['last_fills'] = fills or []
            self.positions[position_key] = pos
            self._save()
    
    def can_sell_profitably(self, symbol: str, current_price: float, 
                           exchange: str = None, quantity: float = None, 
                           fee_pct: float = 0.001) -> Tuple[bool, Dict]:
        """Check if selling would be profitable.
        
        Returns:
            (can_sell: bool, info: dict)
            
        Info contains:
            - entry_price: float
            - current_price: float
            - profit_pct: float
            - net_profit: float (after fees)
            - potential_loss: float (if negative)
            - recommendation: str
        """
        # 🔍 Use the centralized 5-strategy matching logic (reload cache if stale)
        self._reload_if_stale()
        pos, matched_key = self._find_position(symbol, exchange)
        
        # 🚨 NO POSITION FOUND - Critical debugging info
        if not pos:
            _safe_print(f"   🚨 COST BASIS NOT FOUND for {symbol}")
            _safe_print(f"      Exchange: {exchange}")
            
            # Show base asset extraction for debugging
            base = symbol.split('/')[0] if '/' in symbol else self._strip_known_quote(symbol)
            _safe_print(f"      Base asset: {base}")
            
            # Show some available positions that might be close matches
            available = list(self.positions.keys())
            matching_base = [p for p in available if base.upper() in p.upper()]
            if matching_base:
                _safe_print(f"      Possible matches: {matching_base[:5]}")
            else:
                _safe_print(f"      Available positions: {available[:5]}")
            
            # No cost basis data - DON'T SELL! We don't know if it's profitable!
            return False, {
                'entry_price': None,
                'current_price': current_price,
                'profit_pct': 0,
                'net_profit': 0,
                'cost_basis': 0,
                'recommendation': 'NO_DATA - DO NOT SELL (unknown entry price)'
            }
        
        # ✅ FOUND POSITION - Use it for P&L calculation
        avg_entry = float(pos.get('avg_entry_price', 0) or 0)
        lots = self.trade_lots.get(matched_key, [])
        has_lot_cost_data = any((lot.quantity > 0 and lot.price > 0) for lot in lots)

        # Guardrail: a zero entry price is not valid cost-basis data.
        # This previously logged as "found" and produced misleading P&L.
        if avg_entry <= 0 and not has_lot_cost_data:
            _safe_print(f"   🚨 COST BASIS INVALID for {symbol}")
            _safe_print(f"      Matched key: {matched_key}")
            _safe_print("      Stored entry price is zero and no valid trade lots were found")
            return False, {
                'entry_price': None,
                'current_price': current_price,
                'profit_pct': 0,
                'net_profit': 0,
                'cost_basis': 0,
                'recommendation': 'NO_VALID_COST_BASIS - DO NOT SELL'
            }

        _safe_print(f"   ✅ Cost basis found: {matched_key} → entry ${avg_entry:.6f}")
        
        # 🆕 Use FIFO lots to calculate cost of goods for the specific quantity to be sold
        sell_qty = quantity or pos.get('total_quantity', 0)
        cost_basis_of_sale = 0
        
        if matched_key in self.trade_lots:
            lots = sorted(self.trade_lots[matched_key], key=lambda t: t.timestamp)
            qty_to_account_for = sell_qty
            for lot in lots:
                if qty_to_account_for <= 0:
                    break
                qty_from_lot = min(lot.quantity, qty_to_account_for)
                cost_basis_of_sale += qty_from_lot * lot.price
                qty_to_account_for -= qty_from_lot
        
        # Fallback to average cost if no lots found (should not happen)
        if cost_basis_of_sale == 0:
            entry_price = pos['avg_entry_price']
            cost_basis_of_sale = sell_qty * entry_price

        # Calculate P&L
        gross_value = sell_qty * current_price
        gross_profit = gross_value - cost_basis_of_sale
        
        # Account for fees (entry fees are part of cost basis, just add exit fee)
        exit_fee = gross_value * fee_pct
        
        net_profit = gross_profit - exit_fee
        
        # Calculate NET profit percentage
        net_profit_pct = (net_profit / cost_basis_of_sale * 100) if cost_basis_of_sale > 0 else 0
        
        # 💰 PENNY PROFIT RULE: As long as we make $0.01 NET, we are good!
        # Previously required 0.2% margin, but now we align with the Penny Profit Engine.
        is_penny_profitable = net_profit >= 0.01
        
        can_sell = is_penny_profitable
        
        recommendation = ""
        if net_profit_pct >= 2.0:
            recommendation = "🟢 STRONG SELL - Good profit"
        elif net_profit_pct >= 0.5:
            recommendation = "🟡 SELL - Modest profit"
        elif is_penny_profitable:
            recommendation = "⚪ HARVEST - Penny Profit Secured"
        elif net_profit_pct >= -2.0:
            recommendation = "🔴 HOLD - Would realize loss"
        else:
            recommendation = "🔴 HOLD - Significant loss, wait for recovery"
        
        return can_sell, {
            'entry_price': pos['avg_entry_price'], # Still show average entry for info
            'current_price': current_price,
            'quantity': sell_qty,
            'cost_basis': cost_basis_of_sale,
            'gross_value': gross_value,
            'gross_profit': gross_profit,
            'total_fees': exit_fee, # Only shows exit fee as entry is in cost_basis
            'net_profit': net_profit,
            'profit_pct': net_profit_pct, # Return NET profit pct
            'potential_loss': abs(net_profit) if net_profit < 0 else 0,
            'recommendation': recommendation,
            'order_ids': pos.get('order_ids', []),
            'exchange': pos.get('exchange')
        }
    
    # ══════════════════════════════════════════════════════════════════════════════
    # 🧹 CLEANUP & SELL TRACKING - FIX FOR PHANTOM POSITIONS
    # ══════════════════════════════════════════════════════════════════════════════
    
    def record_sell(self, symbol: str, sell_qty: float, sell_price: float, 
                    exchange: str = None, fee: float = 0.0) -> Dict[str, Any]:
        """
        Record a sell and reduce cost basis using FIFO accounting.
        
        This is the KEY method to fix phantom positions - it properly reduces
        cost basis when assets are sold.
        
        DEPRECATION WARNING: This method is being replaced by the more comprehensive
        `record_trade(side='sell', ...)` which uses true FIFO.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDC')
            sell_qty: Quantity sold
            sell_price: Sale price per unit
            exchange: Exchange name (optional, helps with matching)
            fee: Transaction fee paid
            
        Returns:
            Dict with realized P&L and updated position info
        """
        # 🆕 DELEGATE to the new FIFO-based method
        _safe_print("DEPRECATION WARNING: `record_sell` is now an alias for `record_trade(side='sell', ...)`")
        result = self.record_trade(symbol, 'sell', sell_qty, sell_price, exchange, fee)
        
        # Adapt old return format
        if result:
            result['status'] = 'sold' if 'realized_pnl' in result else 'no_position'
            return result
        return {'status': 'error'}
    
    def cleanup_sold_positions(self, min_value_threshold: float = 0.01) -> int:
        """
        Remove positions that have been fully sold (qty ≈ 0).
        
        This cleans up phantom positions that make the cost basis appear
        higher than reality.
        
        Args:
            min_value_threshold: Remove positions worth less than this USD value
            
        Returns:
            Number of positions removed
        """
        removed = 0
        keys_to_remove = []
        
        for key, pos in self.positions.items():
            qty = pos.get('total_quantity', 0)
            cost = pos.get('total_cost', 0)
            
            # 🆕 Also check lots
            lot_qty = sum(l.quantity for l in self.trade_lots.get(key, []))

            # Remove if:
            # 1. Quantity is effectively zero in both aggregates and lots
            # 2. Has zero cost (stale/invalid)
            # 3. Cost is below threshold (dust)
            should_remove = (
                (qty <= 0.0001 and lot_qty <= 0.0001) or
                (qty > 0 and cost == 0 and pos.get('avg_entry_price', 0) == 0) or  # Stale position
                (0 < cost < min_value_threshold)  # Dust value
            )
            
            if should_remove:
                keys_to_remove.append(key)
                _safe_print(f"🗑️ Removing sold position: {key} (qty={qty:.6f}, cost=${cost:.2f})")
        
        for key in keys_to_remove:
            del self.positions[key]
            if key in self.trade_lots:
                del self.trade_lots[key]
            removed += 1
        
        if removed > 0:
            self._save()
            _safe_print(f"✅ Cleaned up {removed} sold/dust positions")
        
        return removed
    
    def verify_against_live_balances(self, live_balances: Dict[str, float], 
                                      exchange: str = None) -> Dict[str, Any]:
        """
        Verify cost basis against actual live exchange balances.
        
        If exchange shows 0 balance but we have cost basis, the position
        was sold outside our tracking - clean it up.
        
        Args:
            live_balances: {asset: quantity} from exchange API
            exchange: Exchange name to filter positions
            
        Returns:
            Dict with verification results and corrections made
        """
        corrections = []
        _removed = []
        
        for key, pos in list(self.positions.items()):
            pos_exchange = pos.get('exchange', '')
            if exchange and pos_exchange.lower() != exchange.lower():
                continue
            
            # Extract base asset from symbol
            asset = pos.get('asset', '')
            if not asset:
                # Try to parse from symbol
                symbol = pos.get('symbol', key)
                # Remove exchange prefix if present
                if ':' in symbol:
                    symbol = symbol.split(':')[1]
                # Extract base asset (before quote currency)
                for quote in ['USDC', 'USDT', 'USD', 'EUR', 'GBP', 'BTC', 'ETH']:
                    if symbol.endswith(quote):
                        asset = symbol[:-len(quote)]
                        break
                else:
                    asset = symbol
            
            tracked_qty = pos.get('total_quantity', 0)
            live_qty = live_balances.get(asset, 0)
            
            # If tracked qty > 0 but live = 0, position was sold externally
            if tracked_qty > 0.0001 and live_qty < 0.0001:
                _safe_print(f"🔄 CORRECTION: {key} tracked {tracked_qty:.6f} but live shows 0")
                pos['total_quantity'] = 0
                pos['total_cost'] = 0
                pos['closed_at'] = time.time()
                pos['correction_note'] = 'Zeroed - live balance is 0'
                self.positions[key] = pos
                if key in self.trade_lots:
                    self.trade_lots[key] = [] # 🆕 Clear lots too
                corrections.append({
                    'key': key,
                    'asset': asset,
                    'was_qty': tracked_qty,
                    'live_qty': live_qty,
                    'action': 'zeroed'
                })
            
            # If live qty is significantly different, update qty but keep cost basis ratio
            elif abs(tracked_qty - live_qty) > 0.0001 and live_qty > 0:
                ratio = live_qty / tracked_qty if tracked_qty > 0 else 0
                old_cost = pos.get('total_cost', 0)
                new_cost = old_cost * ratio
                _safe_print(f"📊 ADJUSTMENT: {key} tracked {tracked_qty:.6f} → live {live_qty:.6f}")
                pos['total_quantity'] = live_qty
                pos['total_cost'] = new_cost
                pos['last_verified'] = time.time()
                self.positions[key] = pos
                
                # 🆕 Adjust lots proportionally
                if key in self.trade_lots:
                    for lot in self.trade_lots[key]:
                        lot.quantity *= ratio

                corrections.append({
                    'key': key,
                    'asset': asset,
                    'was_qty': tracked_qty,
                    'live_qty': live_qty,
                    'action': 'adjusted'
                })
        
        if corrections:
            self._save()
        
        # Also clean up any zero positions
        removed_count = self.cleanup_sold_positions()
        
        return {
            'corrections': corrections,
            'removed_count': removed_count,
            'positions_checked': len(self.positions)
        }
    
    def sync_with_cleanup(self) -> Dict[str, Any]:
        """
        Full sync from exchanges WITH cleanup of sold positions.
        
        This is the proper way to keep cost basis accurate:
        1. Sync fresh data from exchanges (with FIFO sell tracking)
        2. Verify against live balances
        3. Clean up phantom positions
        """
        print("\n" + "=" * 60)
        print("🔄 SYNCING COST BASIS WITH CLEANUP")
        print("=" * 60)
        
        # Step 1: Sync from exchanges
        synced = self.sync_from_exchanges()
        
        # Step 2: Clean up sold positions
        cleaned = self.cleanup_sold_positions()
        
        # Step 3: Get live balances and verify
        live_balances = {}
        verification_results = {}
        
        try:
            # Binance
            if self.clients and 'binance' in self.clients:
                client = self.clients['binance']
            else:
                from aureon.exchanges.binance_client import get_binance_client
                client = get_binance_client()
            
            account = client.account()
            for bal in account.get('balances', []):
                asset = bal['asset']
                qty = float(bal.get('free', 0)) + float(bal.get('locked', 0))
                if qty > 0:
                    live_balances[asset] = qty
            
            verification_results['binance'] = self.verify_against_live_balances(
                live_balances, exchange='binance'
            )
        except Exception as e:
            _safe_print(f"⚠️ Could not verify Binance balances: {e}")
        
        # Step 4: Final cleanup
        final_cleanup = self.cleanup_sold_positions()
        
        result = {
            'synced_positions': synced,
            'initial_cleanup': cleaned,
            'verification': verification_results,
            'final_cleanup': final_cleanup,
            'total_positions': len(self.positions)
        }
        
        print(f"\n✅ Sync complete: {synced} synced, {cleaned + final_cleanup} cleaned")
        print("=" * 60)
        
        return result
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get summary of all tracked positions."""
        total_cost = 0
        total_positions = len(self.positions)
        
        for _symbol, pos in self.positions.items():
            total_cost += pos.get('total_cost', 0)
        
        return {
            'total_positions': total_positions,
            'total_cost_basis': total_cost,
            'last_sync': self.last_sync,
            'positions': list(self.positions.keys())
        }

    # ══════════════════════════════════════════════════════════════════════════════
    # 📜 FULL TRADE HISTORY & RECONCILIATION
    # ══════════════════════════════════════════════════════════════════════════════

    def get_full_trade_history(self) -> List[Dict[str, Any]]:
        """
        Pull ALL trade history from every exchange into a single unified list,
        sorted by timestamp.  Each record carries a consistent schema:

            {
                'exchange': str,
                'symbol': str,      # base+quote (normalised)
                'side': 'buy'|'sell',
                'quantity': float,
                'price': float,
                'cost': float,      # qty * price
                'fee': float,
                'fee_asset': str,
                'timestamp': float,  # unix epoch
                'datetime': str,     # ISO-8601
                'order_id': str,     # exchange-native ID
                'source': str,       # 'trade_history'|'order_fills'|'ledger'
            }
        """
        all_trades: List[Dict[str, Any]] = []

        # ── KRAKEN ────────────────────────────────────────────────────────
        try:
            if self.clients and 'kraken' in self.clients:
                kc = self.clients['kraken']
            else:
                from aureon.exchanges.kraken_client import get_kraken_client
                kc = get_kraken_client()

            if not getattr(kc, 'dry_run', False):
                _safe_print("📜 Pulling Kraken trade history...")
                raw = kc.get_trades_history_dict()  # Dict[trade_id, trade]
                if isinstance(raw, dict):
                    trades_iter = raw.items()
                elif isinstance(raw, list):
                    trades_iter = [(t.get('id', ''), t) for t in raw]
                else:
                    trades_iter = []

                for tid, t in trades_iter:
                    pair = t.get('pair', '')
                    ts = float(t.get('time', 0))
                    all_trades.append({
                        'exchange': 'kraken',
                        'symbol': self._normalize_kraken_pair(pair),
                        'side': t.get('type', ''),
                        'quantity': float(t.get('vol', 0)),
                        'price': float(t.get('price', 0)),
                        'cost': float(t.get('cost', 0)),
                        'fee': float(t.get('fee', 0)),
                        'fee_asset': '',
                        'timestamp': ts,
                        'datetime': datetime.utcfromtimestamp(ts).isoformat() if ts else '',
                        'order_id': tid,
                        'source': 'trade_history',
                    })
                _safe_print(f"   → {len([t for t in all_trades if t['exchange']=='kraken'])} Kraken trades")
        except Exception as e:
            _safe_print(f"⚠️ Kraken trade history fetch failed: {e}")

        # ── BINANCE ───────────────────────────────────────────────────────
        try:
            if self.clients and 'binance' in self.clients:
                bc = self.clients['binance']
            else:
                from aureon.exchanges.binance_client import get_binance_client
                bc = get_binance_client()

            _safe_print("📜 Pulling Binance trade history...")
            all_my = bc.get_all_my_trades(limit_per_symbol=500)
            binance_count = 0
            for sym, trades in all_my.items():
                for t in trades:
                    ts = t.get('time', 0) / 1000.0 if t.get('time', 0) > 1e12 else float(t.get('time', 0))
                    all_trades.append({
                        'exchange': 'binance',
                        'symbol': sym,
                        'side': 'buy' if t.get('isBuyer') else 'sell',
                        'quantity': float(t.get('qty', 0)),
                        'price': float(t.get('price', 0)),
                        'cost': float(t.get('qty', 0)) * float(t.get('price', 0)),
                        'fee': float(t.get('commission', 0)),
                        'fee_asset': t.get('commissionAsset', ''),
                        'timestamp': ts,
                        'datetime': datetime.utcfromtimestamp(ts).isoformat() if ts else '',
                        'order_id': str(t.get('orderId', '')),
                        'source': 'trade_history',
                    })
                    binance_count += 1
            _safe_print(f"   → {binance_count} Binance trades")
        except Exception as e:
            _safe_print(f"⚠️ Binance trade history fetch failed: {e}")

        # ── ALPACA ────────────────────────────────────────────────────────
        try:
            if self.clients and 'alpaca' in self.clients:
                ac = self.clients['alpaca']
            else:
                from aureon.exchanges.alpaca_client import AlpacaClient
                ac = AlpacaClient()

            _safe_print("📜 Pulling Alpaca order fills...")
            orders = ac.get_all_orders(status='closed', limit=500)
            alpaca_count = 0
            for o in orders:
                if o.get('status') != 'filled':
                    continue
                filled_qty = float(o.get('filled_qty', 0) or 0)
                filled_price = float(o.get('filled_avg_price', 0) or 0)
                if filled_qty <= 0 or filled_price <= 0:
                    continue
                filled_at = o.get('filled_at', '') or o.get('updated_at', '') or ''
                ts = 0.0
                if filled_at:
                    try:
                        from dateutil.parser import parse as dtparse  # type: ignore[import]
                        ts = dtparse(filled_at).timestamp()
                    except Exception:
                        pass
                all_trades.append({
                    'exchange': 'alpaca',
                    'symbol': o.get('symbol', ''),
                    'side': o.get('side', ''),
                    'quantity': filled_qty,
                    'price': filled_price,
                    'cost': filled_qty * filled_price,
                    'fee': 0.0,  # Alpaca is commission-free
                    'fee_asset': 'USD',
                    'timestamp': ts,
                    'datetime': filled_at,
                    'order_id': o.get('id', ''),
                    'source': 'order_fills',
                })
                alpaca_count += 1
            _safe_print(f"   → {alpaca_count} Alpaca fills")
        except Exception as e:
            _safe_print(f"⚠️ Alpaca order fill fetch failed: {e}")

        # Sort everything by timestamp
        all_trades.sort(key=lambda t: t.get('timestamp', 0))
        _safe_print(f"\n📊 Total: {len(all_trades)} trades across all exchanges")
        return all_trades

    def full_reconcile(self, backup: bool = True) -> Dict[str, Any]:
        """
        FULL TRADE HISTORY RECONCILIATION
        ═══════════════════════════════════
        Rebuilds cost basis from SCRATCH using real exchange API data.

        Steps:
        1. Backup current cost_basis_history.json
        2. Pull ALL trade history from every exchange
        3. Replay every trade chronologically using FIFO accounting
        4. Cross-reference with live balances
        5. Report full audit findings

        Returns dict with reconciliation results.
        """
        print("\n" + "=" * 70)
        print("🔄 FULL TRADE HISTORY RECONCILIATION")
        print("=" * 70)

        # ── Step 1: Backup ────────────────────────────────────────────────
        if backup and os.path.exists(self.filepath):
            backup_path = self.filepath.replace('.json', f'_backup_{int(time.time())}.json')
            import shutil
            shutil.copy2(self.filepath, backup_path)
            _safe_print(f"💾 Backed up to {backup_path}")

        # ── Step 2: Pull ALL trade history ────────────────────────────────
        all_trades = self.get_full_trade_history()
        if not all_trades:
            _safe_print("⚠️ No trade history found from any exchange")
            return {'status': 'no_data', 'trades': 0}

        # ── Step 3: Replay trades chronologically ─────────────────────────
        _safe_print(f"\n🔄 Replaying {len(all_trades)} trades chronologically...")

        # Clear existing positions and lots for a clean rebuild
        new_positions: Dict[str, Dict[str, Any]] = {}
        new_lots: Dict[str, List[Trade]] = {}

        stats = {
            'total_trades': len(all_trades),
            'buys': 0, 'sells': 0,
            'total_bought': 0.0, 'total_sold': 0.0,
            'total_fees': 0.0,
            'exchanges': {},
            'symbols': {},
        }

        for t in all_trades:
            exchange = t['exchange']
            symbol = t['symbol']
            side = t['side'].lower()
            qty = t['quantity']
            price = t['price']
            fee = t['fee']
            ts = t['timestamp']

            if qty <= 0 or price <= 0:
                continue

            position_key = f"{exchange}:{symbol}"

            # Track stats
            stats['exchanges'].setdefault(exchange, {'buys': 0, 'sells': 0, 'fees': 0.0})
            stats['symbols'].setdefault(position_key, {'buys': 0, 'sells': 0, 'net_qty': 0.0, 'total_cost': 0.0})
            stats['total_fees'] += fee
            stats['exchanges'][exchange]['fees'] += fee

            if position_key not in new_lots:
                new_lots[position_key] = []

            if side == 'buy':
                stats['buys'] += 1
                stats['total_bought'] += qty * price
                stats['exchanges'][exchange]['buys'] += 1
                stats['symbols'][position_key]['buys'] += 1

                new_lots[position_key].append(
                    Trade(price=price, quantity=qty, fee=fee, timestamp=ts)
                )
            elif side == 'sell':
                stats['sells'] += 1
                stats['total_sold'] += qty * price
                stats['exchanges'][exchange]['sells'] += 1
                stats['symbols'][position_key]['sells'] += 1

                # FIFO sell
                sell_rem = qty
                for lot in new_lots.get(position_key, []):
                    if sell_rem <= 0:
                        break
                    take = min(lot.quantity, sell_rem)
                    lot.quantity -= take
                    sell_rem -= take
                # Remove empty lots
                new_lots[position_key] = [l for l in new_lots.get(position_key, []) if l.quantity > 0.000001]

        # ── Step 4: Rebuild positions from remaining lots ─────────────────
        _safe_print("\n📦 Rebuilding positions from remaining lots...")
        for position_key, lots in new_lots.items():
            if not lots:
                continue
            total_qty = sum(l.quantity for l in lots)
            total_cost = sum(l.quantity * l.price for l in lots)
            total_fees = sum(l.fee for l in lots)
            buy_count = len(lots)

            if total_qty < 0.0000001:
                continue

            avg_entry = total_cost / total_qty if total_qty > 0 else 0
            parts = position_key.split(':', 1)
            exchange = parts[0] if len(parts) == 2 else 'unknown'
            symbol = parts[1] if len(parts) == 2 else position_key

            # Try to extract asset/quote
            asset = self._strip_known_quote(symbol)
            quote = symbol[len(asset):] if len(symbol) > len(asset) else 'USD'

            new_positions[position_key] = {
                'exchange': exchange,
                'symbol': symbol,
                'asset': asset,
                'quote': quote,
                'avg_entry_price': avg_entry,
                'total_quantity': total_qty,
                'total_cost': total_cost,
                'total_fees': total_fees,
                'trade_count': buy_count,
                'first_trade': int(lots[0].timestamp * 1000) if lots else None,
                'last_trade': int(lots[-1].timestamp * 1000) if lots else None,
                'synced_at': time.time(),
                'source': 'full_reconcile',
            }
            stats['symbols'][position_key]['net_qty'] = total_qty
            stats['symbols'][position_key]['total_cost'] = total_cost

        # ── Step 5: Merge with Alpaca live positions (they give avg_entry directly) ──
        try:
            if self.clients and 'alpaca' in self.clients:
                ac = self.clients['alpaca']
            else:
                from aureon.exchanges.alpaca_client import AlpacaClient
                ac = AlpacaClient()
            positions = ac.get_positions()
            for pos in (positions or []):
                sym = pos.get('symbol', '')
                avg_entry = float(pos.get('avg_entry_price', 0))
                q = float(pos.get('qty', 0))
                if avg_entry > 0 and q > 0:
                    pk = f"alpaca:{sym}"
                    if pk not in new_positions:
                        new_positions[pk] = {
                            'exchange': 'alpaca',
                            'symbol': sym,
                            'asset': sym,
                            'quote': 'USD',
                            'avg_entry_price': avg_entry,
                            'total_quantity': q,
                            'total_cost': avg_entry * q,
                            'total_fees': 0,
                            'trade_count': 1,
                            'synced_at': time.time(),
                            'source': 'live_position',
                        }
                        new_lots[pk] = [Trade(price=avg_entry, quantity=q)]
        except Exception as e:
            _safe_print(f"⚠️ Could not merge Alpaca live positions: {e}")

        # ── Step 6: Apply ─────────────────────────────────────────────────
        self.positions = new_positions
        self.trade_lots = new_lots
        self.last_sync = time.time()
        self._save()

        # ── Step 7: Report ────────────────────────────────────────────────
        open_positions = {k: v for k, v in new_positions.items()
                         if v.get('total_quantity', 0) > 0.0000001}
        total_invested = sum(v.get('total_cost', 0) for v in open_positions.values())

        print("\n" + "=" * 70)
        print("📊 RECONCILIATION RESULTS")
        print("=" * 70)
        print(f"  Total trades replayed: {stats['total_trades']}")
        print(f"  Buys: {stats['buys']}  |  Sells: {stats['sells']}")
        print(f"  Total bought: ${stats['total_bought']:.2f}")
        print(f"  Total sold:   ${stats['total_sold']:.2f}")
        print(f"  Total fees:   ${stats['total_fees']:.4f}")
        print()
        for ex, ex_stats in stats['exchanges'].items():
            print(f"  {ex.upper()}: {ex_stats['buys']} buys / {ex_stats['sells']} sells / ${ex_stats['fees']:.4f} fees")
        print()
        print(f"  Open positions: {len(open_positions)}")
        print(f"  Total invested: ${total_invested:.2f}")
        print()

        print(f"  {'Position':<30} {'Qty':>15} {'Avg Entry':>12} {'Cost':>10} {'Trades':>7}")
        print("  " + "-" * 76)
        for pk in sorted(open_positions.keys()):
            p = open_positions[pk]
            print(f"  {pk:<30} {p['total_quantity']:>15.6f} ${p['avg_entry_price']:>10.4f} ${p['total_cost']:>9.2f} {p['trade_count']:>6}")
        print("  " + "-" * 76)
        print(f"  {'TOTAL INVESTED':<30} {'':<15} {'':<12} ${total_invested:>9.2f}")
        print("=" * 70)

        stats['open_positions'] = len(open_positions)
        stats['total_invested'] = total_invested
        stats['status'] = 'success'
        return stats

    def print_trade_history_report(self):
        """Print a human-readable report of ALL trades across all exchanges."""
        trades = self.get_full_trade_history()
        if not trades:
            print("No trade history found.")
            return

        print("\n" + "=" * 100)
        print("📜 COMPLETE TRADE HISTORY REPORT")
        print("=" * 100)
        print(f"{'Date':<22} {'Exchange':<9} {'Side':<5} {'Symbol':<16} {'Quantity':>14} {'Price':>12} {'Cost':>10} {'Fee':>8}")
        print("-" * 100)

        by_exchange = {}
        for t in trades:
            dt = t.get('datetime', '')[:19]
            ex = t['exchange']
            side = t['side'].upper()[:4]
            sym = t['symbol'][:15]
            qty = t['quantity']
            price = t['price']
            cost = t['cost']
            fee = t['fee']

            marker = '🟢' if side == 'BUY' else '🔴'
            print(f"{dt:<22} {ex:<9} {marker}{side:<4} {sym:<16} {qty:>14.6f} ${price:>10.4f} ${cost:>9.2f} ${fee:>7.4f}")

            by_exchange.setdefault(ex, {'buys': 0, 'sells': 0, 'buy_vol': 0, 'sell_vol': 0, 'fees': 0})
            if side.startswith('BUY'):
                by_exchange[ex]['buys'] += 1
                by_exchange[ex]['buy_vol'] += cost
            else:
                by_exchange[ex]['sells'] += 1
                by_exchange[ex]['sell_vol'] += cost
            by_exchange[ex]['fees'] += fee

        print("-" * 100)
        print(f"\n{'Exchange':<10} {'Buys':>6} {'Buy Vol':>12} {'Sells':>6} {'Sell Vol':>12} {'Fees':>10} {'Net':>12}")
        print("-" * 62)
        for ex, s in by_exchange.items():
            net = s['buy_vol'] - s['sell_vol']
            print(f"{ex:<10} {s['buys']:>6} ${s['buy_vol']:>10.2f} {s['sells']:>6} ${s['sell_vol']:>10.2f} ${s['fees']:>8.4f} ${net:>10.2f}")
        print("=" * 100)

    
    def print_status(self):
        """Print current cost basis status."""
        print("\n" + "=" * 70)
        print("💰 COST BASIS TRACKER STATUS")
        print("=" * 70)
        
        if not self.positions:
            print("   No positions tracked")
            return
        
        print(f"\n{'Symbol':<25} {'Entry Price':<15} {'Quantity':<20} {'Cost Basis':<15}")
        print("-" * 75)
        
        total_cost = 0
        for symbol, pos in sorted(self.positions.items()):
            entry = pos.get('avg_entry_price', 0)
            qty = pos.get('total_quantity', 0)
            cost = pos.get('total_cost', 0)
            total_cost += cost
            print(f"{symbol:<25} ${entry:<14.6f} {qty:<20.8f} ${cost:<14.2f}")
        
        print("-" * 75)
        print(f"{'TOTAL':<25} {'':<15} {'':<20} ${total_cost:<14.2f}")
        print(f"\nLast sync: {datetime.fromtimestamp(self.last_sync).isoformat() if self.last_sync else 'Never'}")
        print("=" * 75)


# ═══════════════════════════════════════════════════════════════════════════════
# 🔍 COST BASIS TRUTH FINDER
# ═══════════════════════════════════════════════════════════════════════════════
# Finds the REAL cost basis for every position using:
#   1. Exchange trade history APIs (Kraken, Binance, Alpaca)
#   2. Kraken Ledger API (catches conversions, staking, transfers)
#   3. CoinGecko historical price API (fallback for timestamp-based lookup)
# ═══════════════════════════════════════════════════════════════════════════════

# CoinGecko ID mapping for historical price lookups
GECKO_ID_MAP = {
    'BTC': 'bitcoin', 'XBT': 'bitcoin', 'ETH': 'ethereum', 'XRP': 'ripple',
    'SOL': 'solana', 'LINK': 'chainlink', 'XLM': 'stellar', 'ADA': 'cardano',
    'BCH': 'bitcoin-cash', 'ZEC': 'zcash', 'BNB': 'binancecoin', 'TRX': 'tron',
    'USDT': 'tether', 'USDC': 'usd-coin', 'SHIB': 'shiba-inu',
    'ROSE': 'oasis-network', 'PENGU': 'pudgy-penguins', 'LPT': 'livepeer',
    'SSV': 'ssv-network', 'BEAMX': 'beam-2', 'KAIA': 'kaia',
    'AAVE': 'aave', 'ARB': 'arbitrum', 'GHIBLI': 'ghiblification',
    'IN': 'inchain', 'SAHARA': 'sahara-ai', 'MXC': 'mxc',
    'EUL': 'euler', 'FIS': 'stafi', 'CRO': 'crypto-com-chain',
    'FIGHT': 'fight-night', 'ZRO': 'layerzero', 'PYTH': 'pyth-network',
    'NOM': 'nom', 'RESOLV': 'resolv', 'SHELL': 'myshell', 'AVNT': 'advent',
    'TURTLE': 'turtle', 'F': 'formless', 'KITE': 'kiteai', 'LA': 'laion',
    'BANANAS31': 'bananas31', 'SKR': 'sekoia-by-virtuals', 'OPEN': 'openledger',
    'ZRC': 'zircuit', 'DOGE': 'dogecoin', 'DOT': 'polkadot',
    'ATOM': 'cosmos', 'SCRT': 'secret', 'BABY': 'babylon',
    'KTA': 'keeta', 'CHILLHOUSE': 'chill-house',
    'TUSD': 'true-usd', 'DYDX': 'dydx-chain',
    'COTI': 'coti',
}

# Kraken asset name normalization
KRAKEN_ASSET_NORM = {
    'XXBT': 'BTC', 'XXRP': 'XRP', 'XETH': 'ETH', 'ZUSD': 'USD',
    'ZGBP': 'GBP', 'USDT': 'USDT', 'USDC': 'USDC', 'TUSD': 'TUSD',
    'XXLM': 'XLM', 'XZEC': 'ZEC', 'XXDG': 'DOGE', 'XLTC': 'LTC',
    'ETH2': 'ETH', 'ETH2.S': 'ETH',
}


def _gecko_historical_price(coin_id: str, timestamp: float) -> Optional[float]:
    """
    Get historical USD price from CoinGecko for a specific date.
    
    Uses /coins/{id}/history?date=dd-mm-yyyy endpoint.
    Free tier: 10-30 calls/min.
    """
    import urllib.request
    try:
        dt = datetime.utcfromtimestamp(timestamp)
        date_str = dt.strftime('%d-%m-%Y')
        url = (f'https://api.coingecko.com/api/v3/coins/{coin_id}/history'
               f'?date={date_str}&localization=false')
        req = urllib.request.Request(url, headers={
            'Accept': 'application/json', 'User-Agent': 'Aureon/1.0'
        })
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        price = data.get('market_data', {}).get('current_price', {}).get('usd')
        if price and price > 0:
            return float(price)
    except Exception as e:
        _safe_print(f"      [CoinGecko] Failed {coin_id} @ {date_str}: {e}")
    return None


def _gecko_current_price(coin_id: str) -> Optional[float]:
    """Get current USD price from CoinGecko."""
    import urllib.request
    try:
        url = f'https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd'
        req = urllib.request.Request(url, headers={
            'Accept': 'application/json', 'User-Agent': 'Aureon/1.0'
        })
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        return data.get(coin_id, {}).get('usd')
    except Exception:
        return None


def _normalize_kraken_asset(asset: str) -> str:
    """Normalize Kraken asset names: XXBT→BTC, ADA.S→ADA, etc."""
    asset = (asset or '').upper()
    # Check direct mapping
    if asset in KRAKEN_ASSET_NORM:
        return KRAKEN_ASSET_NORM[asset]
    # Return as-is for modern Kraken names (ADA, FIS, GHIBLI, etc.)
    # Only strip X/Z prefix for classic 4-char Kraken names (XXBT, XETH, XXRP)
    if len(asset) == 4 and asset[0] in ('X', 'Z') and asset not in ('ZUSD',):
        stripped = asset[1:]
        if stripped in KRAKEN_ASSET_NORM:
            return KRAKEN_ASSET_NORM[stripped]
        return stripped
    return asset


def _kraken_api_with_retry(client, method_name: str, max_retries: int = 5,
                            initial_wait: float = 15.0, **kwargs):
    """Call a Kraken client method with rate-limit-aware exponential backoff."""
    wait = initial_wait
    for attempt in range(max_retries):
        try:
            method = getattr(client, method_name)
            return method(**kwargs)
        except Exception as e:
            err_str = str(e)
            if 'Rate limit' in err_str or 'EAPI:Rate' in err_str:
                _safe_print(f"      [Kraken] Rate limited on {method_name}, waiting {wait:.0f}s (attempt {attempt+1}/{max_retries})...")
                time.sleep(wait)
                wait = min(wait * 1.5, 120)  # cap at 2 min
            else:
                raise
    _safe_print(f"      [Kraken] {method_name} failed after {max_retries} retries")
    return None


def find_cost_basis_truth(tracker: 'CostBasisTracker' = None) -> dict:
    """
    🔍 COST BASIS TRUTH FINDER
    
    Master function that finds the REAL cost basis for every position by:
    
    1. Getting current real balances from all exchanges
    2. Fetching trade history from exchanges (with rate-limit retry)
    3. Parsing Kraken ledgers for conversions/staking/transfers
    4. Looking up CoinGecko historical prices when exchange data is missing
    5. Reconciling and saving the truth to cost_basis_history.json
    
    Returns dict of {position_key: {entry_price, qty, timestamp, source, ...}}
    """
    if tracker is None:
        tracker = get_cost_basis_tracker()
    
    _safe_print("\n" + "=" * 80)
    _safe_print("🔍 COST BASIS TRUTH FINDER - Finding REAL entry prices for ALL positions")
    _safe_print("=" * 80)
    
    results = {}
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 1: Get current REAL balances from all exchanges
    # ═══════════════════════════════════════════════════════════════════════════
    _safe_print("\n📊 STEP 1: Fetching real balances from all exchanges...")
    
    kraken_balances = {}
    binance_balances = {}
    alpaca_positions = []
    
    # --- Kraken ---
    try:
        from aureon.exchanges.kraken_client import get_kraken_client
        kraken_client = get_kraken_client()
        if not getattr(kraken_client, 'dry_run', False):
            raw_bal = kraken_client.get_balance()
            for asset, amount in raw_bal.items():
                amt = float(amount)
                if amt > 0.0000001:
                    norm = _normalize_kraken_asset(asset)
                    # Keep both raw and normalized
                    kraken_balances[asset] = {'amount': amt, 'normalized': norm}
            _safe_print(f"   🐙 Kraken: {len(kraken_balances)} assets with balance")
    except Exception as e:
        _safe_print(f"   ⚠️ Kraken balance failed: {e}")
    
    # --- Binance ---
    try:
        from aureon.exchanges.binance_client import get_binance_client
        bin_client = get_binance_client()
        account = bin_client.account()
        for bal in account.get('balances', []):
            asset = bal['asset']
            total = float(bal.get('free', 0)) + float(bal.get('locked', 0))
            if total > 0.0000001 and asset not in ('USDC', 'USDT', 'USD', 'BUSD', 'FDUSD'):
                binance_balances[asset] = total
        _safe_print(f"   🟡 Binance: {len(binance_balances)} assets with balance")
    except Exception as e:
        _safe_print(f"   ⚠️ Binance balance failed: {e}")
    
    # --- Alpaca ---
    try:
        from aureon.exchanges.alpaca_client import AlpacaClient
        alp_client = AlpacaClient()
        alpaca_positions = alp_client.get_positions() or []
        _safe_print(f"   🦙 Alpaca: {len(alpaca_positions)} positions")
    except Exception as e:
        _safe_print(f"   ⚠️ Alpaca positions failed: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 2: Fetch Kraken trade history + ledgers
    # ═══════════════════════════════════════════════════════════════════════════
    _safe_print("\n📜 STEP 2: Fetching Kraken trade history & ledgers (rate-limit aware)...")
    
    kraken_trades = {}
    kraken_ledgers = []
    
    try:
        from aureon.exchanges.kraken_client import get_kraken_client  # type: ignore[import]
        kc = get_kraken_client()
        if not getattr(kc, 'dry_run', False):
            # Try trades first
            kraken_trades = _kraken_api_with_retry(kc, 'get_trades_history_dict') or {}
            _safe_print(f"   📦 Kraken trades: {len(kraken_trades)} entries")
            
            if kraken_trades:
                # Wait before hitting ledgers
                time.sleep(5)
            
            # Then ledgers (captures conversions, staking, deposits)
            kraken_ledgers = _kraken_api_with_retry(kc, 'get_ledgers', max_records=2000) or []
            _safe_print(f"   📒 Kraken ledgers: {len(kraken_ledgers)} entries")
    except Exception as e:
        _safe_print(f"   ⚠️ Kraken history fetch: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 3: Build cost basis from Kraken trades
    # ═══════════════════════════════════════════════════════════════════════════
    _safe_print("\n🔨 STEP 3: Building cost basis from trade data...")
    
    # Group Kraken trades by normalized pair
    from collections import defaultdict
    kraken_pair_trades = defaultdict(list)
    for _tid, trade in kraken_trades.items():
        pair = trade.get('pair', '')
        kraken_pair_trades[pair].append(trade)
    
    # Process each Kraken pair
    for pair, trades_list in kraken_pair_trades.items():
        norm_pair = CostBasisTracker._normalize_kraken_pair(pair)
        
        total_qty = 0.0
        total_cost = 0.0
        total_fees = 0.0
        buy_count = 0
        first_ts = None
        last_ts = None
        
        for trade in sorted(trades_list, key=lambda x: float(x.get('time', 0))):
            trade_type = trade.get('type', '')
            qty = float(trade.get('vol', 0))
            price = float(trade.get('price', 0))
            fee = float(trade.get('fee', 0))
            ts = float(trade.get('time', 0))
            
            if trade_type == 'buy':
                total_qty += qty
                total_cost += qty * price
                total_fees += fee
                buy_count += 1
            elif trade_type == 'sell':
                total_qty -= qty
                if total_qty > 0 and (total_qty + qty) > 0:
                    avg = total_cost / (total_qty + qty)
                    total_cost = total_qty * avg
            
            if first_ts is None or ts < first_ts:
                first_ts = ts
            if last_ts is None or ts > last_ts:
                last_ts = ts
        
        if total_qty > 0.0000001 and buy_count > 0:
            avg_entry = total_cost / total_qty
            # Extract base asset from normalized pair
            base = CostBasisTracker._strip_known_quote(norm_pair)
            position_key = f"kraken:{norm_pair}"
            results[position_key] = {
                'exchange': 'kraken',
                'symbol': norm_pair,
                'asset': base,
                'avg_entry_price': avg_entry,
                'total_quantity': total_qty,
                'total_cost': total_cost,
                'total_fees': total_fees,
                'trade_count': buy_count,
                'first_trade': first_ts,
                'last_trade': last_ts,
                'source': 'kraken_trades',
                'synced_at': time.time(),
            }
            _safe_print(f"   ✅ {position_key}: ${avg_entry:.6f} x {total_qty:.4f} ({buy_count} trades)")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 4: Parse Kraken ledgers for conversions, staking, deposits
    # ═══════════════════════════════════════════════════════════════════════════
    _safe_print("\n📒 STEP 4: Parsing Kraken ledgers (conversions, staking, deposits)...")
    
    # Group ledger entries by refid to find conversion pairs
    ledger_by_refid = defaultdict(list)
    for entry in kraken_ledgers:
        refid = entry.get('refid', '')
        if refid:
            ledger_by_refid[refid].append(entry)
    
    # Track which assets we found via ledger (first acquisition timestamp)
    ledger_first_acquisition = {}  # {asset: timestamp}
    
    for refid, entries in ledger_by_refid.items():
        for entry in entries:
            asset_raw = entry.get('asset', '')
            asset = _normalize_kraken_asset(asset_raw)
            amount = float(entry.get('amount', 0))
            ltype = entry.get('type', '')
            ts = float(entry.get('time', 0))
            
            # Track first time we received each asset (positive amount = credit)
            if amount > 0 and ltype in ('trade', 'deposit', 'transfer', 'staking', 'conversion'):
                if asset not in ledger_first_acquisition or ts < ledger_first_acquisition[asset]:
                    ledger_first_acquisition[asset] = ts
    
    _safe_print(f"   📋 First acquisition timestamps for {len(ledger_first_acquisition)} assets")
    
    # For conversions: find pairs where one asset decreases and another increases
    conversion_costs = {}  # {received_asset: {cost_usd, timestamp, from_asset}}
    
    for refid, entries in ledger_by_refid.items():
        if len(entries) < 2:
            continue
        
        inflows = []   # Positive amounts (received)
        outflows = []  # Negative amounts (spent)
        
        for entry in entries:
            asset = _normalize_kraken_asset(entry.get('asset', ''))
            amount = float(entry.get('amount', 0))
            ts = float(entry.get('time', 0))
            ltype = entry.get('type', '')
            
            if amount > 0:
                inflows.append({'asset': asset, 'amount': amount, 'time': ts, 'type': ltype})
            elif amount < 0:
                outflows.append({'asset': asset, 'amount': abs(amount), 'time': ts, 'type': ltype})
        
        # If we spent USD/USDT/USDC/GBP to get something, that's a direct cost basis
        for debit in outflows:
            if debit['asset'] in ('USD', 'USDT', 'USDC', 'GBP', 'EUR'):
                for credit in inflows:
                    if credit['asset'] not in ('USD', 'USDT', 'USDC', 'GBP', 'EUR'):
                        usd_cost = debit['amount']
                        if debit['asset'] == 'GBP':
                            usd_cost *= 1.27  # Approximate GBP→USD
                        elif debit['asset'] == 'EUR':
                            usd_cost *= 1.08  # Approximate EUR→USD
                        
                        if credit['asset'] not in conversion_costs:
                            conversion_costs[credit['asset']] = []
                        conversion_costs[credit['asset']].append({
                            'cost_usd': usd_cost,
                            'quantity': credit['amount'],
                            'price_per_unit': usd_cost / credit['amount'] if credit['amount'] > 0 else 0,
                            'timestamp': credit['time'],
                            'from_asset': debit['asset'],
                            'refid': refid,
                        })
    
    _safe_print(f"   💱 Found conversion/purchase data for {len(conversion_costs)} assets via ledger")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 5: Reconcile Kraken positions — merge trades + ledger + CoinGecko
    # ═══════════════════════════════════════════════════════════════════════════
    _safe_print("\n🎯 STEP 5: Reconciling Kraken positions with truth data...")
    
    gecko_cache = {}  # Cache CoinGecko lookups to avoid repeat calls
    
    for raw_asset, bal_info in kraken_balances.items():
        amount = bal_info['amount']
        norm_asset = bal_info['normalized']
        
        # Skip stablecoins and dust
        if norm_asset in ('USD', 'USDT', 'USDC', 'GBP', 'EUR', 'TUSD'):
            continue
        
        # Determine base asset (strip .S staking suffix)
        is_staking = '.S' in raw_asset
        if is_staking:
            # ADA.S→ADA, SCRT21.S→SCRT, SOL03.S→SOL, TRX.S→TRX
            base_asset = raw_asset.split('.')[0]  # Remove .S suffix
            # Strip numbered staking variants (SCRT21→SCRT, SOL03→SOL)
            for suffix in ('01', '02', '03', '21', '28'):
                if base_asset.endswith(suffix) and len(base_asset) > len(suffix):
                    base_asset = base_asset[:-len(suffix)]
                    break
            base_asset = _normalize_kraken_asset(base_asset)
        else:
            base_asset = norm_asset
        
        position_key = f"kraken:{norm_asset}USD"
        
        # Already have from trade history?
        if position_key in results and results[position_key]['total_quantity'] > 0:
            # Update quantity to match current balance
            results[position_key]['total_quantity'] = amount
            results[position_key]['total_cost'] = results[position_key]['avg_entry_price'] * amount
            continue
        
        # Check if we have conversion data from ledger
        entry_price = None
        entry_ts = None
        source = None
        
        if norm_asset in conversion_costs:
            # Calculate weighted average from all conversions
            conv_list = conversion_costs[norm_asset]
            total_cost = sum(c['cost_usd'] for c in conv_list)
            total_qty = sum(c['quantity'] for c in conv_list)
            if total_qty > 0:
                entry_price = total_cost / total_qty
                entry_ts = conv_list[-1]['timestamp']
                source = f"kraken_ledger_conversion"
                _safe_print(f"   💱 {norm_asset}: Entry ${entry_price:.6f} from {len(conv_list)} conversions (ledger)")
        
        # Also check base asset for staking positions
        if entry_price is None and is_staking and base_asset in conversion_costs:
            conv_list = conversion_costs[base_asset]
            total_cost = sum(c['cost_usd'] for c in conv_list)
            total_qty = sum(c['quantity'] for c in conv_list)
            if total_qty > 0:
                entry_price = total_cost / total_qty
                entry_ts = conv_list[-1]['timestamp']
                source = f"kraken_ledger_staking_base"
                _safe_print(f"   🥩 {norm_asset} (staking): Using base {base_asset} entry ${entry_price:.6f}")
        
        # Still no entry? Try CoinGecko historical price at first acquisition
        if entry_price is None:
            # Find acquisition timestamp
            acq_ts = ledger_first_acquisition.get(norm_asset) or ledger_first_acquisition.get(base_asset)
            
            gecko_id = GECKO_ID_MAP.get(base_asset) or GECKO_ID_MAP.get(norm_asset)
            
            if gecko_id and acq_ts and acq_ts > 1e9:
                cache_key = f"{gecko_id}:{int(acq_ts / 86400)}"
                if cache_key in gecko_cache:
                    entry_price = gecko_cache[cache_key]
                else:
                    time.sleep(1.2)  # CoinGecko rate limit
                    entry_price = _gecko_historical_price(gecko_id, acq_ts)
                    gecko_cache[cache_key] = entry_price
                
                if entry_price:
                    entry_ts = acq_ts
                    acq_date = datetime.utcfromtimestamp(acq_ts).strftime('%Y-%m-%d')
                    source = f"coingecko_historical_{acq_date}"
                    _safe_print(f"   🌐 {norm_asset}: CoinGecko ${entry_price:.6f} on {acq_date}")
            
            # No ledger timestamp? Try CoinGecko current price as last resort
            if entry_price is None and gecko_id:
                if gecko_id not in gecko_cache:
                    time.sleep(1.2)
                    gecko_cache[gecko_id] = _gecko_current_price(gecko_id)
                entry_price = gecko_cache.get(gecko_id)
                if entry_price:
                    entry_ts = time.time()
                    source = "coingecko_current_snapshot"
                    _safe_print(f"   📸 {norm_asset}: CoinGecko current ${entry_price:.6f} (no history found)")
        
        # FALLBACK: Use existing estimated price from cost_basis_history.json
        if entry_price is None or entry_price <= 0:
            # Search multiple key patterns in existing tracker positions
            search_keys = [
                position_key,                        # kraken:GHIBLIUSD
                f"{norm_asset}USD",                   # GHIBLIUSD
                f"kraken:{base_asset}USD",            # kraken:GHIBLIUSD
                f"{base_asset}USD",                   # GHIBLIUSD
                f"kraken:{norm_asset}/USD",            # kraken:GHIBLI/USD
            ]
            # Add raw Kraken name variants (XBTUSD, XXRPUSD)
            search_keys.append(f"{raw_asset}USD")
            search_keys.append(f"kraken:{raw_asset}USD")
            # Reverse-mapping: if norm is BTC, also try XBT
            reverse_map = {'BTC': 'XBT', 'XRP': 'XRP', 'ETH': 'ETH', 'DOGE': 'XDG',
                          'XLM': 'XLM', 'ZEC': 'ZEC', 'LTC': 'LTC'}
            alt_name = reverse_map.get(base_asset)
            if alt_name:
                search_keys.extend([f"{alt_name}USD", f"kraken:{alt_name}USD"])
            # Also check USDC, EUR, GBP pairs (common alternatives)
            for alt_quote in ('USDC', 'EUR', 'GBP'):
                search_keys.extend([
                    f"{base_asset}{alt_quote}",
                    f"{norm_asset}{alt_quote}",
                    f"binance:{base_asset}{alt_quote}",
                    f"kraken:{base_asset}{alt_quote}",
                ])
                if alt_name:
                    search_keys.extend([f"{alt_name}{alt_quote}", f"kraken:{alt_name}{alt_quote}"])
            for sk in search_keys:
                existing_pos = tracker.positions.get(sk)
                if existing_pos:
                    ep = existing_pos.get('avg_entry_price', 0) or 0
                    if ep > 0:
                        entry_price = ep
                        entry_ts = existing_pos.get('first_trade') or existing_pos.get('synced_at') or time.time()
                        source = f"existing_estimated ({existing_pos.get('source', 'unknown')})"
                        _safe_print(f"   📋 {norm_asset}: Using existing estimated ${entry_price:.6f} from {sk}")
                        break
        
        # Store the result
        if entry_price and entry_price > 0:
            results[position_key] = {
                'exchange': 'kraken',
                'symbol': f"{norm_asset}USD",
                'asset': base_asset,
                'quote': 'USD',
                'avg_entry_price': entry_price,
                'total_quantity': amount,
                'total_cost': entry_price * amount,
                'total_fees': 0,
                'trade_count': 1,
                'first_trade': entry_ts,
                'last_trade': entry_ts,
                'source': source,
                'synced_at': time.time(),
            }
        else:
            _safe_print(f"   ❌ {norm_asset}: Could not determine cost basis (qty={amount})")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 6: Sync Binance positions
    # ═══════════════════════════════════════════════════════════════════════════
    _safe_print("\n🟡 STEP 6: Reconciling Binance positions...")
    
    try:
        from aureon.exchanges.binance_client import get_binance_client  # type: ignore[import]
        bc = get_binance_client()
        
        for asset, qty in binance_balances.items():
            if asset.startswith('LD'):
                # Binance Earn — use base asset
                base = asset[2:]
            else:
                base = asset
            
            # Try to get cost basis from Binance trade history
            for quote in ['USDC', 'USDT']:
                symbol = f"{base}{quote}"
                position_key = f"binance:{symbol}"
                
                # Skip if already have good data
                if position_key in results and results[position_key].get('total_quantity', 0) > 0:
                    break
                
                try:
                    cb = bc.calculate_cost_basis(symbol)
                    if cb and cb.get('total_quantity', 0) > 0:
                        results[position_key] = {
                            'exchange': 'binance',
                            'symbol': symbol,
                            'asset': base,
                            'quote': quote,
                            'avg_entry_price': cb['avg_entry_price'],
                            'total_quantity': qty,  # Use CURRENT balance
                            'total_cost': cb['avg_entry_price'] * qty,
                            'total_fees': cb.get('total_fees', 0),
                            'trade_count': cb.get('trade_count', 0),
                            'first_trade': cb.get('first_trade'),
                            'last_trade': cb.get('last_trade'),
                            'source': 'binance_trades',
                            'synced_at': time.time(),
                        }
                        _safe_print(f"   ✅ {position_key}: ${cb['avg_entry_price']:.6f} x {qty:.4f} ({cb.get('trade_count', 0)} trades)")
                        break
                except Exception:
                    continue
            else:
                # Fallback: CoinGecko current price
                gecko_id = GECKO_ID_MAP.get(base)
                if gecko_id:
                    if gecko_id not in gecko_cache:
                        time.sleep(1.2)
                        gecko_cache[gecko_id] = _gecko_current_price(gecko_id)
                    price = gecko_cache.get(gecko_id)
                    if price:
                        position_key = f"binance:{base}USDC"
                        if position_key not in results:
                            results[position_key] = {
                                'exchange': 'binance',
                                'symbol': f"{base}USDC",
                                'asset': base,
                                'quote': 'USDC',
                                'avg_entry_price': price,
                                'total_quantity': qty,
                                'total_cost': price * qty,
                                'total_fees': 0,
                                'trade_count': 0,
                                'source': 'coingecko_current_snapshot',
                                'synced_at': time.time(),
                            }
                            _safe_print(f"   📸 {position_key}: CoinGecko ${price:.6f}")
    except Exception as e:
        _safe_print(f"   ⚠️ Binance reconciliation error: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 7: Sync Alpaca positions (they provide entry price directly!)
    # ═══════════════════════════════════════════════════════════════════════════
    _safe_print("\n🦙 STEP 7: Syncing Alpaca positions...")
    
    for pos in alpaca_positions:
        symbol = pos.get('symbol', '')
        avg_entry = float(pos.get('avg_entry_price', 0))
        qty = float(pos.get('qty', 0))
        
        if avg_entry > 0 and qty > 0:
            position_key = f"alpaca:{symbol}"
            results[position_key] = {
                'exchange': 'alpaca',
                'symbol': symbol,
                'asset': symbol.replace('/USD', '').replace('USD', ''),
                'quote': 'USD',
                'avg_entry_price': avg_entry,
                'total_quantity': qty,
                'total_cost': avg_entry * qty,
                'total_fees': 0,
                'trade_count': 1,
                'source': 'alpaca_positions',
                'synced_at': time.time(),
            }
            _safe_print(f"   ✅ {position_key}: ${avg_entry:.6f} x {qty:.6f}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 8: Merge results into cost_basis_history.json
    # ═══════════════════════════════════════════════════════════════════════════
    _safe_print(f"\n💾 STEP 8: Saving {len(results)} positions to cost_basis_history.json...")
    
    # Load existing data
    existing = tracker.positions.copy()
    
    # Priority merge: new truth data overwrites existing only if it's better
    new_count = 0
    updated_count = 0
    
    for key, data in results.items():
        existing_entry = existing.get(key)
        
        if existing_entry is None:
            # New position — also store without exchange prefix for compat
            existing[key] = data
            new_count += 1
            # Also store bare symbol (e.g., BTCUSD) for backward compatibility
            bare = data.get('symbol', key.split(':', 1)[-1] if ':' in key else key)
            if bare not in existing or (existing[bare].get('total_quantity', 0) or 0) < 0.0000001:
                existing[bare] = data.copy()
        else:
            # Existing — update if new data is better
            old_qty = existing_entry.get('total_quantity', 0) or 0
            old_entry = existing_entry.get('avg_entry_price', 0) or 0
            old_source = existing_entry.get('source', '')
            new_qty = data.get('total_quantity', 0) or 0
            new_entry = data.get('avg_entry_price', 0) or 0
            new_source = data.get('source', '')
            
            # Source quality ranking
            source_rank = {
                'kraken_trades': 5, 'binance_trades': 5, 'alpaca_positions': 5,
                'full_reconcile': 4,
                'kraken_ledger_conversion': 4, 'kraken_ledger_staking_base': 4,
                'manual': 3,
            }
            old_rank = source_rank.get(old_source, 1)
            new_rank = max(source_rank.get(new_source, 1), 
                          3 if new_source.startswith('coingecko_historical') else 1)
            
            should_update = False
            if old_qty < 0.0000001 and new_qty > 0:
                should_update = True  # Was zero qty, now has real qty
            elif old_entry < 0.0000001 and new_entry > 0:
                should_update = True  # Had no entry price, now has one
            elif new_rank > old_rank:
                should_update = True  # Better data source
            
            if should_update:
                existing[key] = data
                updated_count += 1
                # Also update bare symbol
                bare = data.get('symbol', key.split(':', 1)[-1] if ':' in key else key)
                if bare in existing and (existing[bare].get('total_quantity', 0) or 0) < 0.0000001:
                    existing[bare] = data.copy()
    
    # Save
    tracker.positions = existing
    tracker._save()
    
    _safe_print(f"\n{'='*80}")
    _safe_print(f"✅ TRUTH FINDER COMPLETE")
    _safe_print(f"   New: {new_count} | Updated: {updated_count} | Total: {len(existing)}")
    _safe_print(f"   Sources: Kraken trades, Kraken ledger conversions, Binance trades, Alpaca, CoinGecko")
    _safe_print(f"{'='*80}")
    
    # Print summary of all positions with their sources
    _safe_print(f"\n{'Symbol':<30} {'Entry $':<14} {'Qty':<16} {'Source':<30}")
    _safe_print("-" * 90)
    for key in sorted(results.keys()):
        r = results[key]
        _safe_print(f"{key:<30} ${r['avg_entry_price']:<13.6f} {r['total_quantity']:<16.6f} {r.get('source','?')}")
    
    return results


# Singleton instance for ecosystem integration
_tracker_instance: Optional[CostBasisTracker] = None

def get_cost_basis_tracker() -> CostBasisTracker:
    """Get singleton cost basis tracker instance."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = CostBasisTracker()
    return _tracker_instance


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Cost Basis Tracker - Real Exchange Trade Accounting")
    parser.add_argument('--reconcile', action='store_true', help='Full trade history reconciliation (rebuild from scratch)')
    parser.add_argument('--history', action='store_true', help='Print complete trade history report')
    parser.add_argument('--sync', action='store_true', help='Sync from exchanges (incremental)')
    parser.add_argument('--status', action='store_true', help='Print current cost basis status')
    parser.add_argument('--truth', action='store_true', help='🔍 Run Truth Finder - find REAL cost basis for ALL positions')
    parser.add_argument('--no-backup', action='store_true', help='Skip backup during reconcile')
    args = parser.parse_args()

    tracker = get_cost_basis_tracker()

    if args.truth:
        find_cost_basis_truth(tracker)
    elif args.reconcile:
        tracker.full_reconcile(backup=not args.no_backup)
    elif args.history:
        tracker.print_trade_history_report()
    elif args.sync:
        tracker.sync_with_cleanup()
        tracker.print_status()
    elif args.status:
        tracker.print_status()
    else:
        # Default: show status
        tracker.print_status()
        print("\nUsage: python cost_basis_tracker.py --truth|--reconcile|--history|--sync|--status")
