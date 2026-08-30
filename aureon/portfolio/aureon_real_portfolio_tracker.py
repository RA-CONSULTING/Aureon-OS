#!/usr/bin/env python3
"""
💰👁️ REAL PORTFOLIO TRACKER - NO PHANTOM NUMBERS! 👁️💰
========================================================

This module tracks ACTUAL balances across all exchanges.
Queen Sero and Orca Intelligence use this to see THE TRUTH.

No more phantom profits. No more fake numbers.
Just cold, hard REALITY.

"The truth shall set you free" - But first it will piss you off.

Gary Leckey | January 2026 | REALITY CHECK SYSTEM
"""

from __future__ import annotations
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import os
import sys
import json
import time
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# UTF-8 fix for Windows
if sys.platform == 'win32' and sys.stdout is sys.__stdout__ and sys.stdout.isatty():
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        if hasattr(sys.stdout, 'buffer') and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if hasattr(sys.stderr, 'buffer') and not _is_utf8_wrapper(sys.stderr):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

logger = logging.getLogger(__name__)

_TRUE_VALUES = {"1", "true", "yes", "on"}


def _operational_io_suppressed() -> bool:
    """Audit/import probes may inspect this module but must not touch providers or state."""
    return any(
        os.getenv(name, "").strip().lower() in _TRUE_VALUES
        for name in ("AUREON_AUDIT_MODE", "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS")
    )


def _suppressed_portfolio_view() -> Dict[str, Any]:
    """Return an explicit no-data envelope without inventing numeric balances."""
    return {
        "status": "NO_DATA",
        "status_emoji": "",
        "total_usd": "NO_DATA",
        "starting_capital": "NO_DATA",
        "cumulative_net": "NO_DATA",
        "floating": "NO_DATA",
        "lifetime_realized": "NO_DATA",
        "pnl": "NO_DATA",
        "pnl_pct": "NO_DATA",
        "total_trades": None,
        "dream_progress": "NO_DATA",
        "treasury": "NO_DATA",
        "exchanges": {
            "alpaca": "NO_DATA",
            "kraken": "NO_DATA",
            "binance": "NO_DATA",
            "capital": "NO_DATA",
        },
        "timestamp": None,
        "data_status": "suppressed",
        "truth_status": "no_data",
        "action_eligible": False,
        "generated_values": False,
        "reason": "audit_or_import_side_effect_suppression",
    }


@dataclass
class ExchangeBalance:
    """Real balance from a single exchange."""
    exchange: str
    total_usd: float
    cash_usd: float
    positions_usd: float
    timestamp: float
    raw_balances: Dict[str, float] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass 
class RealPortfolioSnapshot:
    """Complete snapshot of ACTUAL portfolio value."""
    timestamp: float
    total_usd: float
    
    # Per-exchange breakdown
    alpaca_usd: float = 0.0
    kraken_usd: float = 0.0
    binance_usd: float = 0.0
    capital_usd: float = 0.0
    
    # Historical tracking
    starting_capital: float = 78.51  # ACTUAL starting capital
    
    # 💰 P&L BREAKDOWN (The Truth) 💰
    cumulative_net_pnl: float = 0.0   # Total Equity - Starting Capital
    floating_pnl: float = 0.0         # Unrealized (Open Positions)
    lifetime_realized_pnl: float = 0.0 # Cumulative - Floating (Banked)
    kraken_realized_pnl: float = 0.0   # Kraken-only realized PnL (trade history)
    
    realized_pnl: float = 0.0  # DEPRECATED: Kept for backward compat (Same as cumulative_net_pnl)
    unrealized_pnl: float = 0.0 # DEPRECATED: Kept for compat (Same as floating_pnl)
    
    total_fees_paid: float = 0.0
    total_trades: int = 0
    
    # Win/Loss tracking
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # Queen's dream progress
    dream_target: float = 1_000_000_000.0  # $1 BILLION
    dream_progress_pct: float = 0.0
    
    # Treasury Tracking (Avalanche Harvester)
    treasury_usd: float = 0.0
    harvest_reserve_breakdown: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'total_usd': round(self.total_usd, 2),
            'alpaca_usd': round(self.alpaca_usd, 2),
            'kraken_usd': round(self.kraken_usd, 2),
            'binance_usd': round(self.binance_usd, 2),
            'capital_usd': round(self.capital_usd, 2),
            'treasury_usd': round(self.treasury_usd, 2),
            'harvest_reserves': self.harvest_reserve_breakdown,
            'starting_capital': self.starting_capital,
            'realized_pnl': round(self.realized_pnl, 2),
            'unrealized_pnl': round(self.unrealized_pnl, 2),
            'total_pnl': round(self.realized_pnl + self.unrealized_pnl, 2),
            'kraken_realized_pnl': round(self.kraken_realized_pnl, 2),
            'total_fees_paid': round(self.total_fees_paid, 2),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': round(self.win_rate * 100, 1),
            'dream_progress_pct': self.dream_progress_pct,
            'is_profitable': (self.realized_pnl + self.unrealized_pnl) > 0,
            'net_change_pct': round(((self.total_usd - self.starting_capital) / self.starting_capital) * 100, 2) if self.starting_capital > 0 else 0
        }


class RealPortfolioTracker:
    """
    💰👁️ THE TRUTH TRACKER 👁️💰
    
    Queen Sero and Orca can ALWAYS see the REAL portfolio state.
    No phantom numbers. No fake profits. JUST TRUTH.
    """
    
    # Persistence file
    STATE_FILE = "real_portfolio_state.json"
    HISTORY_FILE = "real_portfolio_history.json"
    
    def __init__(
        self,
        starting_capital: float = 78.51,
        state_file: Optional[str] = None,
        history_file: Optional[str] = None,
    ):
        """Initialize with REAL starting capital."""
        self.STATE_FILE = state_file or os.getenv("AUREON_PORTFOLIO_STATE_PATH") or type(self).STATE_FILE
        self.HISTORY_FILE = history_file or os.getenv("AUREON_PORTFOLIO_HISTORY_PATH") or type(self).HISTORY_FILE
        self._operational_io_suppressed = _operational_io_suppressed()
        self.starting_capital = starting_capital
        self.last_snapshot: Optional[RealPortfolioSnapshot] = None
        self.history: List[Dict] = []
        self.max_history = 1000
        
        # Exchange clients (lazy loaded)
        self._alpaca_client = None
        self._kraken_client = None
        self._binance_client = None
        self._capital_client = None

        # Kraken trade history cache (avoid heavy calls every cycle)
        self._kraken_trades_cache: List[Dict[str, Any]] = []
        self._kraken_trades_cache_time = 0.0
        self._kraken_trades_cache_ttl = int(os.getenv("KRAKEN_TRADES_CACHE_TTL", "300"))
        self._kraken_trades_since = int(os.getenv("KRAKEN_TRADES_SINCE", "0") or 0)
        
        if not self._operational_io_suppressed:
            self._load_state()
        
        logger.info("💰👁️ Real Portfolio Tracker initialized")
        if self._operational_io_suppressed:
            logger.info("   Provider and state I/O suppressed")
        else:
            logger.info(f"   Starting Capital: ${self.starting_capital:.2f}")

    def set_clients(self, clients: Dict[str, Any]) -> None:
        """Inject existing clients to avoid nonce issues."""
        if 'kraken' in clients:
            self._kraken_client = clients['kraken']
        if 'binance' in clients:
            self._binance_client = clients['binance']
        if 'alpaca' in clients:
            self._alpaca_client = clients['alpaca']
        if 'capital' in clients:
            self._capital_client = clients['capital']
        logger.info("💰👁️ Clients injected into RealPortfolioTracker")
    
    def _load_state(self) -> None:
        """Load previous state from disk."""
        if self._operational_io_suppressed:
            return
        try:
            state_path = Path(self.STATE_FILE)
            if state_path.exists():
                with open(state_path, 'r') as f:
                    data = json.load(f)
                    self.starting_capital = data.get('starting_capital', self.starting_capital)
                    self.history = data.get('history', [])[-self.max_history:]
                    logger.info(f"📂 Loaded portfolio state: {len(self.history)} snapshots")
        except Exception as e:
            logger.warning(f"⚠️ Could not load portfolio state: {e}")
    
    def _save_state(self) -> None:
        """Save state to disk (atomic write - temp file then rename)."""
        if self._operational_io_suppressed:
            return
        try:
            data = {
                'starting_capital': self.starting_capital,
                'last_update': time.time(),
                'history': self.history[-self.max_history:]
            }
            tmp_path = self.STATE_FILE + '.tmp'
            with open(tmp_path, 'w') as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, self.STATE_FILE)
        except Exception as e:
            logger.warning(f"⚠️ Could not save portfolio state: {e}")
    
    def _get_alpaca_balance(self) -> ExchangeBalance:
        """Get REAL Alpaca balance."""
        try:
            if self._alpaca_client is None:
                from aureon.exchanges.alpaca_client import AlpacaClient
                self._alpaca_client = AlpacaClient()
            
            acc = self._alpaca_client.get_account()
            cash = float(acc.get('cash', 0))
            equity = float(acc.get('equity', 0))
            
            return ExchangeBalance(
                exchange='alpaca',
                total_usd=equity,
                cash_usd=cash,
                positions_usd=equity - cash,
                timestamp=time.time(),
                raw_balances={'cash': cash, 'equity': equity}
            )
        except Exception as e:
            logger.error(f"❌ Alpaca balance FAILED: {type(e).__name__}: {e}")
            return ExchangeBalance(
                exchange='alpaca',
                total_usd=0.0,
                cash_usd=0.0,
                positions_usd=0.0,
                timestamp=time.time(),
                error=str(e)
            )
    
    def _price_crypto_holdings(self, raw_balances: Dict[str, float]) -> float:
        """Price crypto holdings via Binance public tickers, then CoinGecko fallback."""
        import urllib.request
        crypto_usd = 0.0
        stables = {'USD', 'USDT', 'USDC', 'ZUSD', 'TUSD', 'DAI', 'BUSD', 'FDUSD'}
        unpriced = {}

        # --- Binance public ticker (fast, no auth) ---
        try:
            req = urllib.request.Request('https://api.binance.com/api/v3/ticker/price')
            resp = urllib.request.urlopen(req, timeout=10)
            tickers = json.loads(resp.read())
            price_map = {t['symbol']: float(t['price']) for t in tickers}
        except Exception:
            price_map = {}

        # Map Kraken tickers to standard symbols
        kraken_map = {
            'XXBT': 'BTC', 'XETH': 'ETH', 'XXRP': 'XRP', 'XXLM': 'XLM',
            'XXDG': 'DOGE', 'XLTC': 'LTC', 'XZEC': 'ZEC', 'XMLN': 'MLN',
            'XREP': 'REP', 'XETC': 'ETC',
        }

        for asset, qty in raw_balances.items():
            if qty < 0.0000001:
                continue
            clean = asset.upper().replace('.S', '').rstrip('0123456789')
            if clean in stables or any(s in clean for s in stables):
                continue  # already counted as cash
            std = kraken_map.get(clean, clean)
            # Try USDT pair then USDC pair
            price = price_map.get(f'{std}USDT') or price_map.get(f'{std}USDC')
            if price:
                crypto_usd += qty * price
            else:
                unpriced[asset] = qty

        if unpriced:
            logger.debug(f"Unpriced crypto assets: {list(unpriced.keys())}")
        return crypto_usd

    def _get_kraken_balance(self) -> ExchangeBalance:
        """Get REAL Kraken balance (stablecoins + crypto priced via tickers)."""
        try:
            if self._kraken_client is None:
                from aureon.exchanges.kraken_client import get_kraken_client
                self._kraken_client = get_kraken_client()
            
            balances = self._kraken_client.get_balance()
            
            cash_usd = 0.0
            raw = {}
            stables = ['USD', 'USDT', 'USDC', 'ZUSD', 'TUSD', 'DAI']
            
            for asset, amount in balances.items():
                amt = float(amount)
                if amt > 0.0001:
                    raw[asset] = amt
                    if any(s in asset.upper() for s in stables):
                        cash_usd += amt
            
            # Price ALL crypto holdings, not just stablecoins
            crypto_usd = self._price_crypto_holdings(raw)
            total_usd = cash_usd + crypto_usd
            
            logger.info(f"🐙 Kraken balance: cash=${cash_usd:.2f} + crypto=${crypto_usd:.2f} = ${total_usd:.2f}")
            
            return ExchangeBalance(
                exchange='kraken',
                total_usd=total_usd,
                cash_usd=cash_usd,
                positions_usd=crypto_usd,
                timestamp=time.time(),
                raw_balances=raw
            )
        except Exception as e:
            logger.error(f"❌ Kraken balance FAILED: {type(e).__name__}: {e}")
            return ExchangeBalance(
                exchange='kraken',
                total_usd=0.0,
                cash_usd=0.0,
                positions_usd=0.0,
                timestamp=time.time(),
                error=str(e)
            )
    
    def _get_binance_balance(self) -> ExchangeBalance:
        """Get REAL Binance balance (stablecoins + crypto priced via tickers)."""
        try:
            if self._binance_client is None:
                from aureon.exchanges.binance_client import get_binance_client
                self._binance_client = get_binance_client()
            
            # get_balance() returns Dict[str, float] = {asset: free_amount}
            balances = self._binance_client.get_balance()
            
            cash_usd = 0.0
            raw = {}
            stables = ['USDT', 'USDC', 'BUSD', 'TUSD', 'DAI', 'FDUSD']
            
            for asset, amount in balances.items():
                amt = float(amount)  # flat float, NOT a dict
                if amt > 0.0001:
                    raw[asset] = amt
                    if asset.upper() in stables:
                        cash_usd += amt
            
            # Price ALL crypto holdings, not just stablecoins
            crypto_usd = self._price_crypto_holdings(raw)
            total_usd = cash_usd + crypto_usd
            
            logger.info(f"🟡 Binance balance: cash=${cash_usd:.2f} + crypto=${crypto_usd:.2f} = ${total_usd:.2f}")
            
            return ExchangeBalance(
                exchange='binance',
                total_usd=total_usd,
                cash_usd=cash_usd,
                positions_usd=crypto_usd,
                timestamp=time.time(),
                raw_balances=raw
            )
        except Exception as e:
            logger.error(f"❌ Binance balance FAILED: {type(e).__name__}: {e}")
            return ExchangeBalance(
                exchange='binance',
                total_usd=0.0,
                cash_usd=0.0,
                positions_usd=0.0,
                timestamp=time.time(),
                error=str(e)
            )
    
    def _get_capital_balance(self) -> ExchangeBalance:
        """Get REAL Capital.com balance."""
        try:
            if self._capital_client is None:
                from aureon.exchanges.capital_client import CapitalClient
                self._capital_client = CapitalClient()
            
            acc = self._capital_client.get_accounts()
            if acc and len(acc) > 0:
                balance = float(acc[0].get('balance', {}).get('balance', 0))
                return ExchangeBalance(
                    exchange='capital',
                    total_usd=balance,
                    cash_usd=balance,
                    positions_usd=0.0,
                    timestamp=time.time()
                )
            return ExchangeBalance(
                exchange='capital',
                total_usd=0.0,
                cash_usd=0.0,
                positions_usd=0.0,
                timestamp=time.time()
            )
        except Exception as e:
            return ExchangeBalance(
                exchange='capital',
                total_usd=0.0,
                cash_usd=0.0,
                positions_usd=0.0,
                timestamp=time.time(),
                error=str(e)
            )
    
    def _get_trade_stats(self) -> Dict:
        """Get trade statistics from cost basis history."""
        try:
            with open('cost_basis_history.json', 'r') as f:
                data = json.load(f)
            
            positions = data.get('positions', {})
            total_trades = 0
            total_fees = 0.0
            
            for _symbol, pos in positions.items():
                total_trades += int(pos.get('trade_count', 0))
                total_fees += float(pos.get('total_fees', 0))
            
            return {
                'total_trades': total_trades,
                'total_fees': total_fees,
                'winning_trades': 0,  # Would need closed trade data
                'losing_trades': 0
            }
        except Exception:
            return {
                'total_trades': 0,
                'total_fees': 0.0,
                'winning_trades': 0,
                'losing_trades': 0
            }
    
    def _get_treasury_state(self) -> Dict:
        """Get Avalanche Treasury state."""
        try:
            treasury_file = Path("state/avalanche_treasury.json")
            if treasury_file.exists():
                with open(treasury_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.debug(f"Could not load treasury state: {e}")
        
        return {
            'total_usd': 0.0,
            'reserves': {}
        }

    def _get_kraken_trades(self) -> List[Dict[str, Any]]:
        if self._kraken_trades_cache and (time.time() - self._kraken_trades_cache_time) < self._kraken_trades_cache_ttl:
            return self._kraken_trades_cache
        if self._kraken_client is None:
            from aureon.exchanges.kraken_client import get_kraken_client
            self._kraken_client = get_kraken_client()
        try:
            trades = self._kraken_client.get_trades_history(
                since=self._kraken_trades_since if self._kraken_trades_since > 0 else None
            )
            self._kraken_trades_cache = trades
            self._kraken_trades_cache_time = time.time()
            return trades
        except Exception as e:
            logger.debug(f"Kraken trade history unavailable: {e}")
            return []

    def _compute_kraken_realized_pnl(self) -> Optional[float]:
        trades = self._get_kraken_trades()
        if not trades:
            return None

        usd_quotes = {"USD", "USDT", "USDC"}
        positions: Dict[str, Dict[str, float]] = {}
        realized = 0.0

        for trade in trades:
            base = trade.get("base", "")
            quote = trade.get("quote", "")
            if not base or quote not in usd_quotes:
                continue

            ttype = trade.get("type", "")
            qty = float(trade.get("vol", 0) or 0)
            cost = float(trade.get("cost", 0) or 0)
            fee = float(trade.get("fee", 0) or 0)
            if qty <= 0:
                continue

            pos = positions.setdefault(base, {"qty": 0.0, "cost": 0.0})
            if ttype == "buy":
                pos["qty"] += qty
                pos["cost"] += cost + fee
            elif ttype == "sell":
                if pos["qty"] <= 0:
                    realized += (cost - fee)
                    continue
                avg_cost = pos["cost"] / pos["qty"] if pos["qty"] > 0 else 0.0
                sell_qty = min(qty, pos["qty"])
                cost_basis = avg_cost * sell_qty
                proceeds = cost - fee
                realized += proceeds - cost_basis
                pos["qty"] -= sell_qty
                pos["cost"] -= cost_basis

        return realized

    def _load_live_profit_source(self) -> Optional[Dict]:
        """
        Load authoritative live profit state from quick_profit_check.py.
        This provides accurately valued positions (including crypto assets).
        """
        try:
            path = Path("live_profit_state.json")
            if path.exists() and time.time() - path.stat().st_mtime < 300: # 5 min fresh
                with open(path, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    def get_real_portfolio(self) -> Optional[RealPortfolioSnapshot]:
        """
        Get REAL portfolio snapshot from ALL exchanges.
        
        This is the TRUTH - what Queen and Orca should see.
        """
        if self._operational_io_suppressed:
            return None

        # Get balances from all exchanges (basic checks)
        alpaca = self._get_alpaca_balance()
        kraken = self._get_kraken_balance()
        binance = self._get_binance_balance()
        capital = self._get_capital_balance()
        
        # 1. Calculate Base Equity (Cash + value)
        # ALWAYS use live exchange balances as primary source of truth.
        # live_profit_state.json is only used as supplementary pricing data,
        # NOT as a replacement for actual exchange API calls.
        total_usd = (
            alpaca.total_usd + 
            kraken.total_usd + 
            binance.total_usd + 
            capital.total_usd
        )
        
        # If live exchange totals are near-zero but live state has data,
        # it means exchange calls failed — use live state as FALLBACK only
        live_state = self._load_live_profit_source()
        if total_usd < 1.0 and live_state and 'totals' in live_state:
            total_usd = float(live_state['totals']['total_value_usd'])
            floating_pnl = float(live_state['totals'].get('total_pnl_usd', 0.0))
        else:
            floating_pnl = 0.0

        # Get trade stats
        trade_stats = self._get_trade_stats()
        
        # Get treasury state
        treasury = self._get_treasury_state()
        treasury_usd = float(treasury.get('total_usd', 0.0))
        
        # 2. Calculate P&L Metaphysics
        cumulative_net_pnl = total_usd - self.starting_capital
        lifetime_realized_pnl = cumulative_net_pnl - floating_pnl

        # Kraken realized PnL from trade history (USD quotes only)
        kraken_realized_pnl = None
        try:
            kraken_realized_pnl = self._compute_kraken_realized_pnl()
        except Exception as e:
            logger.debug(f"Kraken realized PnL calc failed: {e}")

        if kraken_realized_pnl is not None:
            lifetime_realized_pnl = kraken_realized_pnl
            floating_pnl = cumulative_net_pnl - lifetime_realized_pnl
        
        # Create snapshot
        snapshot = RealPortfolioSnapshot(
            timestamp=time.time(),
            total_usd=total_usd,
            alpaca_usd=alpaca.total_usd,
            kraken_usd=kraken.total_usd, # Note: This might be cash-only if live_state used
            binance_usd=binance.total_usd,
            capital_usd=capital.total_usd,
            
            starting_capital=self.starting_capital,
            
            # The TRUTH
            cumulative_net_pnl=cumulative_net_pnl,
            floating_pnl=floating_pnl,
            lifetime_realized_pnl=lifetime_realized_pnl,
            kraken_realized_pnl=kraken_realized_pnl or 0.0,
            
            # Legacy Compat
            realized_pnl=cumulative_net_pnl, 
            unrealized_pnl=floating_pnl,
            
            total_fees_paid=trade_stats['total_fees'],
            total_trades=trade_stats['total_trades'],
            winning_trades=trade_stats['winning_trades'],
            losing_trades=trade_stats['losing_trades'], 
            dream_progress_pct=(total_usd / 1_000_000_000.0) * 100 if total_usd > 0 else 0,
            treasury_usd=treasury_usd,
            harvest_reserve_breakdown=treasury.get('reserves', {})
        )
        
        # Update history
        self.last_snapshot = snapshot
        try:
            self.history.append(snapshot.__dict__) # Serialize
        except:
            # Fallback if __dict__ fails (dataclass normally supports it, but just in case)
            pass

        self._save_state()
        
        return snapshot
    
    def get_quick_summary(self) -> Dict:
        """Get a quick summary for Queen/Orca display."""
        if self._operational_io_suppressed:
            return _suppressed_portfolio_view()
        snapshot = self.get_real_portfolio()
        if snapshot is None:
            return _suppressed_portfolio_view()
        
        # Determine status
        if snapshot.cumulative_net_pnl > 0:
            status = "📈 PROFITABLE"
            status_emoji = "💰"
        elif snapshot.cumulative_net_pnl < -10:
            status = "📉 LOSING"
            status_emoji = "🔴"
        else:
            status = "📊 BREAK-EVEN"
            status_emoji = "🟡"
        
        return {
            'status': status,
            'status_emoji': status_emoji,
            'total_usd': f"${snapshot.total_usd:.2f}",
            'starting_capital': f"${snapshot.starting_capital:.2f}",
            
            # The Three PnLs
            'cumulative_net': f"${snapshot.cumulative_net_pnl:+.2f}",
            'floating': f"${snapshot.floating_pnl:+.2f}",
            'lifetime_realized': f"${snapshot.lifetime_realized_pnl:+.2f}",
            
            'pnl_pct': f"{(snapshot.cumulative_net_pnl / snapshot.starting_capital * 100):+.1f}%",
            'total_trades': snapshot.total_trades,
            'dream_progress': f"{snapshot.dream_progress_pct:.10f}%",
            'treasury': f"${snapshot.treasury_usd:.2f}",
            'exchanges': {
                'alpaca': f"${snapshot.alpaca_usd:.2f}",
                'kraken': f"${snapshot.kraken_usd:.2f}",
                'binance': f"${snapshot.binance_usd:.2f}",
                'capital': f"${snapshot.capital_usd:.2f}"
            },
            'timestamp': datetime.fromtimestamp(snapshot.timestamp).isoformat()
        }
    
    def format_for_queen(self) -> str:
        """Format portfolio for Queen's display."""
        summary = self.get_quick_summary()
        
        lines = [
            "═══════════════════════════════════════════════════════",
            f"     👑💰 QUEEN'S REAL PORTFOLIO STATUS 💰👑",
            "═══════════════════════════════════════════════════════",
            f"  Status: {summary['status_emoji']} {summary['status']}",
            f"  ",
            f"  💵 TOTAL VALUE: {summary['total_usd']}",
            f"  💎 TREASURY: {summary['treasury']}",
            f"  📊 Started With: {summary['starting_capital']}",
            f"  ",
            f"  📈 P&L BREAKDOWN:",
            f"     🌊 Floating (Open):   {summary['floating']}",
            f"     💰 Realized (Banked): {summary['lifetime_realized']}",
            f"     🏆 Cumulative Net:    {summary['cumulative_net']} ({summary['pnl_pct']})",
            f"  ",
            f"  🏦 BY EXCHANGE:",
            f"     🦙 Alpaca:  {summary['exchanges']['alpaca']}",
            f"     🐙 Kraken:  {summary['exchanges']['kraken']}",
            f"     🟡 Binance: {summary['exchanges']['binance']}",
            f"     💼 Capital: {summary['exchanges']['capital']}",
            f"  ",
            f"  📊 Total Trades: {summary['total_trades']}",
            f"  🎯 Dream Progress: {summary['dream_progress']}",
            "═══════════════════════════════════════════════════════"
        ]
        
        return "\n".join(lines)
    
    def format_for_orca(self) -> str:
        """Format portfolio for Orca's hunting display."""
        summary = self.get_quick_summary()
        
        lines = [
            "🦈═══════════════════════════════════════════════════🦈",
            f"        ORCA HUNTING RESOURCES",
            "🦈═══════════════════════════════════════════════════🦈",
            f"  🎯 Available Capital: {summary['total_usd']}",
            f"  📊 Hunt Status: {summary['status']}",
            f"  📈 Season P&L: {summary['pnl']}",
            f"  🔪 Kills (Trades): {summary['total_trades']}",
            "🦈═══════════════════════════════════════════════════🦈"
        ]
        
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# 🌐 SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_tracker_instance: Optional[RealPortfolioTracker] = None


def get_real_portfolio_tracker() -> RealPortfolioTracker:
    """Get the singleton portfolio tracker instance."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = RealPortfolioTracker()
    return _tracker_instance


def get_real_balance() -> Dict:
    """Quick function to get real balance."""
    return get_real_portfolio_tracker().get_quick_summary()


def show_real_portfolio():
    """Print real portfolio to console."""
    tracker = get_real_portfolio_tracker()
    print(tracker.format_for_queen())


# ═══════════════════════════════════════════════════════════════════════════════
# 🧪 TEST / CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Real Portfolio Tracker")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--orca", action="store_true", help="Orca format")
    args = parser.parse_args()
    
    tracker = get_real_portfolio_tracker()
    
    if args.json:
        snapshot = tracker.get_real_portfolio()
        print(json.dumps(snapshot.to_dict(), indent=2))
    elif args.orca:
        print(tracker.format_for_orca())
    else:
        print(tracker.format_for_queen())
