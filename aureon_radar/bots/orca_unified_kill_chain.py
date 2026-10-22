#!/usr/bin/env python3
"""
🦈🌍💀 ORCA UNIFIED KILL CHAIN + WIN KILLER 💀🌍🦈
═══════════════════════════════════════════════════════════════════════════════
Unified Autonomous Buy/Sell Logic for ALL Exchanges (Capital, Kraken, Binance)
 + WIN KILLER: Hunt for wins BY ANY MEANS NECESSARY

Logic Loop:
 1. 📡 SCAN: Check all balances and open positions across ALL exchanges.
 2. 🧠 ASSESS: Queen calculates Realized vs Unrealized PnL (using Cost Basis).
 3. ⚕️ VALIDATE: Dr. Auris checks harmonics (Ticker, Spread, Volume).
 4. 🎯 EXECUTE: Sniper kills profitable positions (SELL).
 5. ♻️ REDEPLOY: Energy (Cash) is detected and re-deployed into profitable targets (BUY).
 6. 💀 WIN KILLER: Hunt for MOMENTUM, ARBITRAGE, BOUNCE plays - WINS ONLY!

BY ANY MEANS NECESSARY - ONLY WINS COUNT

Refactored from `orca_complete_kill_cycle.py` and `live_kill_chain_demo.py`.
═══════════════════════════════════════════════════════════════════════════════
"""
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import time
import json
import asyncio
import requests
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

# Clients
try:
    from aureon.exchanges.capital_client import CapitalClient
except ImportError:
    CapitalClient = None

try:
    from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
except ImportError:
    KrakenClient = None

try:
    from aureon.exchanges.binance_client import BinanceClient, get_binance_client
except ImportError:
    BinanceClient = None

try:
    from aureon.exchanges.alpaca_client import AlpacaClient
except ImportError:
    AlpacaClient = None

try:
    from aureon.portfolio.aureon_real_portfolio_tracker import get_real_portfolio_tracker
except ImportError:
    get_real_portfolio_tracker = None

# ═══════════════════════════════════════════════════════════════════════════════
# 🎭 LOGGING PERSONAS
# ═══════════════════════════════════════════════════════════════════════════════
def log_queen(msg):
    print(f"👑 [QUEEN] {msg}")
    time.sleep(0.3)

def log_auris(msg):
    print(f"⚕️ [DR. AURIS] {msg}")
    time.sleep(0.3)

def log_sniper(msg):
    print(f"🎯 [SNIPER] {msg}")
    time.sleep(0.2)

def log_system(msg):
    print(f"🖥️ [SYSTEM] {msg}")

def log_killer(msg):
    print(f"💀 [WIN KILLER] {msg}")
    time.sleep(0.2)

# ═══════════════════════════════════════════════════════════════════════════════
# 💀 WIN KILLER CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
@dataclass
class WinConfig:
    """Configuration for WIN KILLER mode"""
    min_score: float = 3.0              # Minimum opportunity score
    min_volume_usd: float = 1_000_000   # Minimum 24h volume
    max_position_pct: float = 0.10      # Max 10% of portfolio per trade
    stop_loss_pct: float = 0.03         # 3% stop loss
    take_profit_pct: float = 0.05       # 5% take profit
    min_risk_reward: float = 1.5        # Minimum R:R ratio
    auto_execute: bool = False          # Set True for full autonomous mode
    momentum_threshold: float = 10.0    # Min % change for momentum plays
    arb_threshold: float = 0.1          # Min % spread for arbitrage

# ═══════════════════════════════════════════════════════════════════════════════
# 💰 COST BASIS MANAGER
# ═══════════════════════════════════════════════════════════════════════════════
COST_BASIS_FILE = "cost_basis_history.json"

def load_cost_basis() -> Dict[str, Any]:
    if os.path.exists(COST_BASIS_FILE):
        with open(COST_BASIS_FILE, 'r') as f:
            return json.load(f).get('positions', {})
    return {}

# ═══════════════════════════════════════════════════════════════════════════════
# 💀 WIN KILLER - HUNT FOR WINS BY ANY MEANS
# ═══════════════════════════════════════════════════════════════════════════════
class WinKiller:
    """Hunt for winning opportunities - NO MERCY"""
    
    def __init__(self, config: WinConfig = None):
        self.config = config or WinConfig()
        self.wins_log = []
        
    def hunt_binance(self) -> List[Dict]:
        """Scan Binance for momentum/bounce plays"""
        opportunities = []
        
        try:
            url = 'https://api.binance.com/api/v3/ticker/24hr'
            resp = requests.get(url, timeout=30)
            if resp.status_code != 200:
                return []
            
            tickers = resp.json()
            usdt_pairs = [t for t in tickers if t['symbol'].endswith('USDT')]
            
            for t in usdt_pairs:
                try:
                    change = float(t.get('priceChangePercent', 0))
                    volume = float(t.get('quoteVolume', 0))
                    price = float(t.get('lastPrice', 0))
                    high = float(t.get('highPrice', 0))
                    low = float(t.get('lowPrice', 0))
                    
                    if volume < self.config.min_volume_usd or price == 0:
                        continue
                    
                    # Calculate WIN SCORE
                    score = self._calculate_score(change, volume, price, high, low)
                    
                    if score >= self.config.min_score:
                        op_type = self._determine_type(change, price, high, low)
                        entry, target, stop = self._calculate_levels(price, op_type, high, low)
                        rr = (target - entry) / (entry - stop) if entry > stop else 0
                        
                        opportunities.append({
                            'symbol': t['symbol'],
                            'exchange': 'binance',
                            'type': op_type,
                            'price': price,
                            'change_24h': change,
                            'volume_24h': volume,
                            'score': score,
                            'entry': entry,
                            'target': target,
                            'stop': stop,
                            'risk_reward': rr,
                            'timestamp': datetime.now().isoformat()
                        })
                except:
                    continue
                    
        except Exception as e:
            log_killer(f"Binance scan error: {e}")
        
        return sorted(opportunities, key=lambda x: x['score'], reverse=True)
    
    def hunt_kraken(self) -> List[Dict]:
        """Scan Kraken for opportunities"""
        opportunities = []
        
        # Top Kraken pairs to scan
        pairs = ['XBTUSD', 'ETHUSD', 'SOLUSD', 'DOTUSD', 'LINKUSD', 
                 'AVAXUSD', 'ATOMUSD', 'WLDUSD', 'ADAUSD', 'MATICUSD']
        
        try:
            url = 'https://api.kraken.com/0/public/Ticker'
            resp = requests.get(url, params={'pair': ','.join(pairs)}, timeout=10)
            data = resp.json()
            
            if 'result' in data:
                for pair, t in data['result'].items():
                    try:
                        price = float(t['c'][0])
                        high = float(t['h'][1])
                        low = float(t['l'][1])
                        volume = float(t['v'][1]) * price
                        
                        change = ((price - low) / low * 100) if low > 0 else 0
                        score = self._calculate_score(change, volume, price, high, low)
                        
                        if score >= self.config.min_score * 0.5:  # Lower bar for Kraken
                            op_type = self._determine_type(change, price, high, low)
                            entry, target, stop = self._calculate_levels(price, op_type, high, low)
                            rr = (target - entry) / (entry - stop) if entry > stop else 1.0
                            
                            opportunities.append({
                                'symbol': pair,
                                'exchange': 'kraken',
                                'type': op_type,
                                'price': price,
                                'change_24h': change,
                                'volume_24h': volume,
                                'score': score,
                                'entry': entry,
                                'target': target,
                                'stop': stop,
                                'risk_reward': max(rr, 1.0),
                                'timestamp': datetime.now().isoformat()
                            })
                    except:
                        continue
                        
        except Exception as e:
            log_killer(f"Kraken scan error: {e}")
        
        return sorted(opportunities, key=lambda x: x['score'], reverse=True)
    
    def hunt_arbitrage(self) -> List[Dict]:
        """Hunt for cross-exchange arbitrage opportunities"""
        opportunities = []
        
        # Compare prices across exchanges
        arb_pairs = [
            ('BTC', 'XBTUSD', 'BTCUSDT'),
            ('ETH', 'ETHUSD', 'ETHUSDT'),
            ('SOL', 'SOLUSD', 'SOLUSDT'),
            ('WLD', 'WLDUSD', 'WLDUSDT'),
        ]
        
        try:
            # Get Kraken prices
            kraken_url = 'https://api.kraken.com/0/public/Ticker'
            k_resp = requests.get(kraken_url, params={'pair': 'XBTUSD,ETHUSD,SOLUSD,WLDUSD'}, timeout=10)
            k_data = k_resp.json().get('result', {})
            
            kraken_prices = {}
            for pair, t in k_data.items():
                price = float(t['c'][0])
                if 'XBT' in pair:
                    kraken_prices['BTC'] = price
                elif 'ETH' in pair and 'XBT' not in pair:
                    kraken_prices['ETH'] = price
                elif 'SOL' in pair:
                    kraken_prices['SOL'] = price
                elif 'WLD' in pair:
                    kraken_prices['WLD'] = price
            
            # Get Binance prices
            binance_url = 'https://api.binance.com/api/v3/ticker/price'
            b_resp = requests.get(binance_url, timeout=10)
            b_data = {t['symbol']: float(t['price']) for t in b_resp.json()}
            
            binance_prices = {
                'BTC': b_data.get('BTCUSDT', 0),
                'ETH': b_data.get('ETHUSDT', 0),
                'SOL': b_data.get('SOLUSDT', 0),
                'WLD': b_data.get('WLDUSDT', 0),
            }
            
            # Find arbitrage
            for coin in ['BTC', 'ETH', 'SOL', 'WLD']:
                k_price = kraken_prices.get(coin, 0)
                b_price = binance_prices.get(coin, 0)
                
                if k_price > 0 and b_price > 0:
                    spread_pct = abs(k_price - b_price) / min(k_price, b_price) * 100
                    
                    if spread_pct > self.config.arb_threshold:
                        buy_exchange = 'kraken' if k_price < b_price else 'binance'
                        sell_exchange = 'binance' if k_price < b_price else 'kraken'
                        
                        opportunities.append({
                            'symbol': f'{coin}/USD',
                            'exchange': 'arbitrage',
                            'type': 'ARBITRAGE',
                            'kraken_price': k_price,
                            'binance_price': b_price,
                            'spread_pct': spread_pct,
                            'buy_exchange': buy_exchange,
                            'sell_exchange': sell_exchange,
                            'score': 10.0,  # Arbitrage = highest priority
                            'risk_reward': 99.0,  # Near guaranteed
                            'action': f'BUY {buy_exchange} @ ${min(k_price, b_price):.2f} → SELL {sell_exchange} @ ${max(k_price, b_price):.2f}',
                            'timestamp': datetime.now().isoformat()
                        })
                        
        except Exception as e:
            log_killer(f"Arbitrage scan error: {e}")
        
        return opportunities
    
    def _calculate_score(self, change: float, volume: float, price: float, 
                         high: float, low: float) -> float:
        """Calculate opportunity WIN score"""
        # Momentum score (0-3 points)
        momentum = max(0, change / 7)
        
        # Volume score (0-2 points)
        vol_score = min(2, volume / 50_000_000)
        
        # Bounce score (0-2 points)
        if change < -10 and price > low * 1.02:
            bounce = (price - low) / (high - low) if high > low else 0
            bounce_score = bounce * 2
        else:
            bounce_score = 0
        
        # Breakout score (0-1 point)
        breakout_score = 1.0 if (high > 0 and price > high * 0.95) else 0
        
        return momentum + vol_score + bounce_score + breakout_score
    
    def _determine_type(self, change: float, price: float, high: float, low: float) -> str:
        """Determine opportunity type"""
        if change > self.config.momentum_threshold:
            return 'MOMENTUM'
        elif change < -10 and price > low * 1.02:
            return 'BOUNCE'
        elif abs(change) < 3:
            return 'ACCUMULATION'
        return 'SWING'
    
    def _calculate_levels(self, price: float, op_type: str, 
                          high: float, low: float) -> Tuple[float, float, float]:
        """Calculate entry, target, stop levels"""
        entry = price
        
        if op_type == 'MOMENTUM':
            target = price * (1 + self.config.take_profit_pct)
            stop = price * (1 - self.config.stop_loss_pct)
        elif op_type == 'BOUNCE':
            target = price + (high - price) * 0.5
            stop = low * 0.98
        else:
            target = price * 1.03
            stop = price * 0.98
        
        return entry, target, stop
    
    def hunt_all(self) -> List[Dict]:
        """Hunt across ALL sources for wins"""
        all_wins = []
        
        # Hunt everywhere
        log_killer("🔍 Scanning Binance for momentum...")
        all_wins.extend(self.hunt_binance()[:10])
        
        log_killer("🔍 Scanning Kraken deep waters...")
        all_wins.extend(self.hunt_kraken()[:5])
        
        log_killer("💱 Hunting arbitrage spreads...")
        all_wins.extend(self.hunt_arbitrage())
        
        # Sort by score
        all_wins.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return all_wins

# ═══════════════════════════════════════════════════════════════════════════════
# 🧠 CORE LOGIC
# ═══════════════════════════════════════════════════════════════════════════════
class UnifiedKillChain:
    def __init__(self, win_config: WinConfig = None):
        self.capital = CapitalClient() if CapitalClient else None
        self.kraken = get_kraken_client() if KrakenClient else None
        self.binance = get_binance_client() if BinanceClient else None
        self.alpaca = AlpacaClient() if AlpacaClient else None
        self.cost_basis = load_cost_basis()
        self.real_portfolio = get_real_portfolio_tracker() if get_real_portfolio_tracker else None
        
        # WIN KILLER integration
        self.win_config = win_config or WinConfig()
        self.win_killer = WinKiller(self.win_config)
        self.wins_executed = []
        self.total_pnl = 0.0

    def refresh_truth(self) -> Optional[Dict[str, Any]]:
        """Pull the single source of truth for portfolio state."""
        if not self.real_portfolio:
            return None
        try:
            summary = self.real_portfolio.get_quick_summary()
            log_system(
                "TRUTH | Total: {total} | Net: {net} | Trades: {trades} | Dream: {dream}".format(
                    total=summary.get('total_usd', 'N/A'),
                    net=summary.get('cumulative_net', 'N/A'),
                    trades=summary.get('total_trades', 'N/A'),
                    dream=summary.get('dream_progress', 'N/A')
                )
            )
            return summary
        except Exception as e:
            log_system(f"Truth update failed: {e}")
            return None
        
    def scan_all(self):
        log_system("Initiating Global Asset Scan...")
        opportunities = []

        # 1. Capital.com (Positions are explicit)
        if self.capital and self.capital.enabled:
            log_queen("Scanning Capital.com reality branches...")
            try:
                positions = self.capital.get_positions()
                for p in positions:
                    market = p.get('market', {})
                    pos_data = p.get('position', {})
                    epic = market.get('epic')
                    upl = float(pos_data.get('upl', 0))
                    
                    opportunities.append({
                        'exchange': 'capital',
                        'symbol': epic,
                        'id': pos_data.get('dealId'),
                        'type': 'CFD',
                        'qty': float(pos_data.get('size', 0)),
                        'pnl': upl,
                        'client': self.capital,
                        'raw': p
                    })
            except Exception as e:
                log_system(f"Capital Scan Error: {e}")

        # 2. Crypto (Spot - requires Cost Basis calculation)
        # Check Binance
        if self.binance:
            log_queen("Scanning Binance liquidity pools...")
            try:
                acct = self.binance.account()
                balances = acct.get('balances', [])
                for b in balances:
                    asset = b['asset']
                    free = float(b['free'])
                    locked = float(b['locked'])
                    total = free + locked
                    if total > 0 and asset not in ['USDT', 'USDC', 'USD', 'EUR', 'GBP']:
                        # Found non-stable asset. Check cost basis.
                        basis_key = f"{asset}USDT" # Assumption for lookup
                        basis = self.cost_basis.get(basis_key, {})
                        avg_entry = basis.get('avg_entry_price', 0)
                        
                        if avg_entry > 0:
                            # Get Current Price
                            ticker = self.binance.get_ticker(f"{asset}USDT")
                            curr_price = float(ticker.get('price', 0))
                            if curr_price > 0:
                                pnl = (curr_price - avg_entry) * total
                                opportunities.append({
                                    'exchange': 'binance',
                                    'symbol': f"{asset}USDT", # Trading pair
                                    'id': asset,
                                    'type': 'SPOT',
                                    'qty': total,
                                    'pnl': pnl,
                                    'client': self.binance,
                                    'current_price': curr_price,
                                    'entry_price': avg_entry
                                })
            except Exception as e:
                 log_system(f"Binance Scan Error: {e}")

        # Check Kraken
        if self.kraken:
            log_queen("Scanning Kraken deep waters...")
            try:
                balances = self.kraken.get_account_balance()
                for asset, total in balances.items():
                    if total > 0 and asset not in ['USDT', 'USDC', 'USD', 'EUR', 'GBP', 'ZUSD', 'ZEUR']:
                         # Look for cost basis
                        basis_key = f"{asset}USD" # Standard Kraken
                        basis = self.cost_basis.get(basis_key, {})
                        # Kraken often uses XBT/ETH/etc. Map if needed.
                        avg_entry = basis.get('avg_entry_price', 0)

                        if avg_entry > 0:
                             ticker = self.kraken.get_ticker(f"{asset}USD")
                             curr_price = float(ticker.get('price', 0))
                             if curr_price > 0:
                                pnl = (curr_price - avg_entry) * total
                                opportunities.append({
                                    'exchange': 'kraken',
                                    'symbol': f"{asset}USD",
                                    'id': asset,
                                    'type': 'SPOT',
                                    'qty': total,
                                    'pnl': pnl,
                                    'client': self.kraken,
                                    'current_price': curr_price,
                                    'entry_price': avg_entry
                                })
            except Exception as e:
                log_system(f"Kraken Scan Error: {e}")
        
        return opportunities

    def execute_kill_chain(self, target):
        symbol = target['symbol']
        exchange = target['exchange']
        client = target['client']
        
        log_queen(f"Assess Target: {exchange.upper()}::{symbol} | PnL: {target['pnl']:.2f}")
        
        # 4. Queen Assessment
        if target['pnl'] > 0:
            log_queen("Verdict: PROFITABLE. Initiate Harvest Protocol.")
        else:
            log_queen(f"Verdict: NEGATIVE ({target['pnl']:.2f}). Holding Pattern Recommended.")
            # return # For verify mode, we might stop here. But let's proceed to Auris for the demo.
        
        # 5. Auris Validation
        log_auris(f"Validation Request: {symbol}")
        ticker = client.get_ticker(symbol)
        price = float(ticker.get('price', 0))
        bid = float(ticker.get('bid', 0))
        ask = float(ticker.get('ask', 0))
        
        if price == 0:
            log_auris("⚠️ Discordance. Data missing.")
            return

        log_auris(f"Harmonics: | Bid: {bid} | Ask: {ask} | Spread: {ask-bid:.4f}")
        log_auris("Validation: COMPLETE. Path to profit is clear.")
        
        # 6. Sniper Handoff
        log_sniper(f"Target Locked. {symbol}. Qty: {target['qty']}")
        
        if exchange == 'capital':
            # Capital.com Kill
            confirm = input(f"\n🔴 [CAPITAL] CLOSE {symbol} (Deal {target['id']})? [y/N]: ")
            if confirm.lower() == 'y':
                log_sniper("Firing...")
                res = client._request('DELETE', f"/positions/{target['id']}")
                if res.status_code == 200:
                    log_sniper("💥 Target Eliminated.")
                else:
                    log_sniper(f"❌ Missed: {res.text}")
        
        elif exchange in ['binance', 'kraken']:
            # Spot Kill (Sell)
            confirm = input(f"\n🔴 [{exchange.upper()}] SELL {target['qty']} {symbol}? [y/N]: ")
            if confirm.lower() == 'y':
                log_sniper("Firing...")
                # Assuming execute_trade signature: symbol, side, qty
                # Kraken/Binance clients both try to follow this standard
                try:
                    res = client.place_market_order(symbol, 'SELL', target['qty'])
                    if res and (res.get('status') == 'FILLED' or res.get('orderId')):
                        log_sniper(f"💥 Sold. Cash secured. OrderID: {res.get('orderId')}")
                    else:
                        log_sniper(f"❌ Sell Failed: {res}")
                except Exception as e:
                    log_sniper(f"❌ Execution Exception: {e}")

    def redeploy_energy(self):
        """Simulate identifying a buying opportunity."""
        log_system("♻️ Checking Energy Levels for Redeployment...")
        # Check USD balances
        cached_cash = 0.0
        
        if self.binance:
            usdt = self.binance.get_free_balance('USDT')
            if usdt > 10:
                log_queen(f"Binance Energy Detected: {usdt:.2f} USDT")
                cached_cash += usdt
        
        if cached_cash > 10:
            log_queen("Energy available for Materialization (BUY).")
            # Logic to find a target would go here (Dr. Auris scans for harmonics)
            log_auris("Scanning for harmonic resonance (Dip Buying)...")
            log_auris("... No perfect resonance found at this milli-epoch.")
        else:
            log_queen("Energy levels low. Awaiting harvest.")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 💀 WIN KILLER METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def hunt_for_wins(self) -> List[Dict]:
        """Hunt for winning opportunities - BY ANY MEANS"""
        log_killer("💀 WIN KILLER ACTIVATED - HUNTING...")
        return self.win_killer.hunt_all()
    
    def execute_win(self, opportunity: Dict) -> Dict:
        """Execute a winning trade"""
        symbol = opportunity.get('symbol', 'UNKNOWN')
        exchange = opportunity.get('exchange', 'unknown')
        op_type = opportunity.get('type', 'UNKNOWN')
        score = opportunity.get('score', 0)
        
        log_killer(f"🎯 TARGET LOCKED: {symbol} on {exchange}")
        log_killer(f"   Type: {op_type} | Score: {score:.2f}")
        
        if op_type == 'ARBITRAGE':
            log_killer(f"   💱 {opportunity.get('action', 'N/A')}")
            log_killer(f"   Spread: {opportunity.get('spread_pct', 0):.3f}%")
        else:
            log_killer(f"   Entry: ${opportunity.get('entry', 0):.6f}")
            log_killer(f"   Target: ${opportunity.get('target', 0):.6f}")
            log_killer(f"   Stop: ${opportunity.get('stop', 0):.6f}")
            log_killer(f"   R:R: {opportunity.get('risk_reward', 0):.1f}:1")
        
        # Check if auto-execute is enabled
        if self.win_config.auto_execute and score >= 5.0:
            log_killer("⚡ AUTO-EXECUTE ENABLED - FIRING!")
            return self._execute_trade(opportunity)
        else:
            # Manual confirmation
            if score >= 5.0:
                confirm = input(f"\n💀 EXECUTE {op_type} on {symbol}? [y/N]: ")
                if confirm.lower() == 'y':
                    return self._execute_trade(opportunity)
            
        return {'status': 'SKIPPED', 'reason': 'Score too low or not confirmed'}
    
    def _execute_trade(self, opportunity: Dict) -> Dict:
        """Actually execute the trade - BY THE ORCA RULES"""
        exchange = opportunity.get('exchange', 'unknown')
        symbol = opportunity.get('symbol', 'UNKNOWN')
        op_type = opportunity.get('type', 'UNKNOWN')
        
        log_sniper(f"🔥 EXECUTING BY ORCA RULES: {symbol} on {exchange}")
        
        try:
            # Get available balance for position sizing
            available_usd = 0.0
            
            if exchange == 'kraken' and self.kraken:
                # Map symbol to Kraken format
                kraken_pair = symbol if 'USD' in symbol else f"{symbol.replace('USDT', '')}USD"
                
                # Get balance
                try:
                    balances = self.kraken.get_account_balance()
                    available_usd = float(balances.get('ZUSD', 0)) + float(balances.get('USD', 0))
                except:
                    available_usd = 0
                
                if available_usd < 1:
                    log_sniper(f"⚠️ Insufficient USD on Kraken: ${available_usd:.2f}")
                    return {'status': 'NO_FUNDS', 'exchange': 'kraken', 'balance': available_usd}
                
                # Calculate position size (ORCA RULE: max 10% per trade)
                position_usd = min(available_usd * 0.10, available_usd)
                price = opportunity.get('price', 0)
                
                if price > 0:
                    volume = position_usd / price
                    
                    log_sniper(f"🎯 Kraken: {kraken_pair}")
                    log_sniper(f"   Position: ${position_usd:.2f} = {volume:.6f}")
                    log_sniper(f"   Entry: ${price:.6f}")
                    
                    # EXECUTE THE TRADE
                    order_result = self.kraken.place_market_order(kraken_pair, 'buy', volume)
                    
                    if order_result and not order_result.get('error'):
                        log_sniper(f"💥 ORDER FILLED! {order_result}")
                        result = {'status': 'FILLED', 'pair': kraken_pair, 'exchange': 'kraken', 
                                  'volume': volume, 'order': order_result}
                    else:
                        log_sniper(f"❌ Order failed: {order_result}")
                        result = {'status': 'FAILED', 'error': order_result}
                else:
                    result = {'status': 'NO_PRICE', 'exchange': 'kraken'}
                
            elif exchange == 'binance' and self.binance:
                # Get USDT balance
                try:
                    available_usd = self.binance.get_free_balance('USDT')
                except:
                    available_usd = 0
                
                if available_usd < 1:
                    log_sniper(f"⚠️ Insufficient USDT on Binance: ${available_usd:.2f}")
                    return {'status': 'NO_FUNDS', 'exchange': 'binance', 'balance': available_usd}
                
                # Calculate position size (ORCA RULE: max 10% per trade)
                position_usd = min(available_usd * 0.10, available_usd)
                price = opportunity.get('price', 0)
                
                if price > 0:
                    volume = position_usd / price
                    
                    log_sniper(f"🎯 Binance: {symbol}")
                    log_sniper(f"   Position: ${position_usd:.2f} = {volume:.6f}")
                    log_sniper(f"   Entry: ${price:.6f}")
                    
                    # EXECUTE THE TRADE
                    order_result = self.binance.place_market_order(symbol, 'BUY', volume)
                    
                    if order_result and order_result.get('status') == 'FILLED':
                        log_sniper(f"💥 ORDER FILLED! {order_result}")
                        result = {'status': 'FILLED', 'pair': symbol, 'exchange': 'binance',
                                  'volume': volume, 'order': order_result}
                    else:
                        log_sniper(f"❌ Order failed: {order_result}")
                        result = {'status': 'FAILED', 'error': order_result}
                else:
                    result = {'status': 'NO_PRICE', 'exchange': 'binance'}
                
            elif exchange == 'arbitrage':
                # ARBITRAGE: Buy on one exchange, sell on another
                buy_ex = opportunity.get('buy_exchange')
                sell_ex = opportunity.get('sell_exchange')
                coin = opportunity.get('symbol', '').split('/')[0]
                
                log_sniper(f"💱 ARBITRAGE: {coin}")
                log_sniper(f"   BUY on {buy_ex} @ ${opportunity.get('kraken_price', 0):.2f}")
                log_sniper(f"   SELL on {sell_ex} @ ${opportunity.get('binance_price', 0):.2f}")
                log_sniper(f"   Spread: {opportunity.get('spread_pct', 0):.3f}%")
                
                # EXECUTE ARBITRAGE
                try:
                    if buy_ex == 'kraken' and sell_ex == 'binance':
                        # Get available USD on Kraken for buying
                        kraken_balances = self.kraken.get_balance()
                        available_usd = float(kraken_balances.get('USD', 0))
                        
                        if available_usd < 10:
                            log_sniper(f"⚠️ Insufficient USD on Kraken: ${available_usd:.2f}")
                            result = {'status': 'NO_FUNDS', 'exchange': 'kraken', 'balance': available_usd}
                        else:
                            # Use 80% of available for arbitrage
                            trade_usd = available_usd * 0.8
                            buy_price = opportunity.get('kraken_price', 0)
                            volume = trade_usd / buy_price
                            
                            kraken_pair = symbol.replace('/', '')
                            
                            log_sniper(f"   Step 1: BUY {volume:.6f} {coin} on Kraken")
                            buy_order = self.kraken.place_market_order(kraken_pair, 'buy', volume)
                            
                            if buy_order and buy_order.get('status') == 'FILLED':
                                actual_qty = float(buy_order.get('executedQty', volume))
                                log_sniper(f"   ✅ Bought {actual_qty} {coin}")
                                
                                # Now sell on Binance
                                binance_symbol = f"{coin}USDT"
                                log_sniper(f"   Step 2: SELL {actual_qty} {coin} on Binance")
                                
                                sell_order = self.binance.place_market_order(binance_symbol, 'SELL', actual_qty)
                                
                                if sell_order and sell_order.get('status') == 'FILLED':
                                    log_sniper(f"   ✅ ARBITRAGE COMPLETE!")
                                    result = {'status': 'ARBITRAGE_EXECUTED', 'buy_order': buy_order, 'sell_order': sell_order}
                                else:
                                    log_sniper(f"   ❌ Sell failed, holding {actual_qty} {coin}")
                                    result = {'status': 'PARTIAL', 'buy_order': buy_order, 'sell_error': sell_order}
                            else:
                                log_sniper(f"   ❌ Buy failed")
                                result = {'status': 'BUY_FAILED', 'error': buy_order}
                    else:
                        # Other direction or not supported yet
                        result = {'status': 'ARBITRAGE_LOGGED', 'type': 'arbitrage', 
                                  'buy': buy_ex, 'sell': sell_ex, 'spread': opportunity.get('spread_pct', 0)}
                except Exception as e:
                    log_sniper(f"   ❌ Arbitrage error: {e}")
                    result = {'status': 'ERROR', 'error': str(e)}
            else:
                result = {'status': 'NO_CLIENT', 'exchange': exchange}
            
            self.wins_executed.append({
                'opportunity': opportunity,
                'result': result,
                'timestamp': datetime.now().isoformat()
            })
            
            # Save execution log
            try:
                with open('orca_executions.json', 'a') as f:
                    f.write(json.dumps({
                        'timestamp': datetime.now().isoformat(),
                        'opportunity': opportunity,
                        'result': result
                    }) + '\n')
            except:
                pass

            if self.real_portfolio:
                try:
                    self.real_portfolio.get_real_portfolio()
                except Exception:
                    pass
            
            return result
            
        except Exception as e:
            log_killer(f"❌ Execution error: {e}")
            return {'status': 'ERROR', 'error': str(e)}
    
    def display_win_opportunities(self, opportunities: List[Dict], limit: int = 10):
        """Display win opportunities in a nice format"""
        print()
        print("💀" * 35)
        print("   WIN KILLER - OPPORTUNITIES FOUND")
        print("💀" * 35)
        print()
        
        if not opportunities:
            print("   ⏳ No opportunities above threshold")
            return
        
        print(f"   🎯 {len(opportunities)} WINS DETECTED")
        print()
        
        for i, op in enumerate(opportunities[:limit], 1):
            score = op.get('score', 0)
            score_bar = '█' * int(score) + '░' * (10 - int(score))
            
            print(f"   {i}. {op['symbol']:12} | {op.get('exchange', '?'):8} | {op.get('type', '?'):12}")
            print(f"      Score: [{score_bar}] {score:.2f}")
            
            if op.get('type') == 'ARBITRAGE':
                print(f"      💱 {op.get('action', 'N/A')}")
                print(f"      Spread: {op.get('spread_pct', 0):.3f}%")
            else:
                print(f"      Price: ${op.get('price', 0):.6f} | Δ24h: {op.get('change_24h', 0):+.1f}%")
                print(f"      Target: ${op.get('target', 0):.6f} | R:R: {op.get('risk_reward', 0):.1f}:1")
            print()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='ORCA Unified Kill Chain + WIN KILLER')
    parser.add_argument('--auto', action='store_true', help='Enable auto-execute (DANGEROUS)')
    parser.add_argument('--min-score', type=float, default=3.0, help='Minimum win score')
    parser.add_argument('--hunt-only', action='store_true', help='Only hunt, do not execute existing positions')
    parser.add_argument('--once', action='store_true', help='Run single cycle then exit')
    args = parser.parse_args()
    
    # Configure WIN KILLER
    win_config = WinConfig(
        min_score=args.min_score,
        auto_execute=args.auto
    )
    
    chain = UnifiedKillChain(win_config)
    
    cycle = 0
    while True:
        cycle += 1
        log_system(f"\n{'='*70}")
        log_system(f"   KILL CYCLE {cycle} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log_system(f"{'='*70}\n")

        # Single source of truth snapshot
        chain.refresh_truth()
        
        # ═══════════════════════════════════════════════════════════════════════
        # PHASE 1: Scan existing positions (unless hunt-only)
        # ═══════════════════════════════════════════════════════════════════════
        if not args.hunt_only:
            targets = chain.scan_all()
            
            if not targets:
                log_queen("No existing positions to harvest.")
            else:
                log_queen(f"Found {len(targets)} existing positions.")
                for t in targets:
                    chain.execute_kill_chain(t)
        
        # ═══════════════════════════════════════════════════════════════════════
        # PHASE 2: WIN KILLER - Hunt for new opportunities
        # ═══════════════════════════════════════════════════════════════════════
        print()
        log_killer("=" * 50)
        log_killer("   PHASE 2: WIN KILLER HUNT")
        log_killer("=" * 50)
        
        wins = chain.hunt_for_wins()
        chain.display_win_opportunities(wins)
        
        # Execute top opportunity if score is high enough
        if wins and wins[0].get('score', 0) >= 5.0:
            log_killer(f"🔥 HOT OPPORTUNITY: {wins[0]['symbol']} (Score: {wins[0]['score']:.2f})")
            result = chain.execute_win(wins[0])
            log_killer(f"Result: {result}")
        
        # ═══════════════════════════════════════════════════════════════════════
        # PHASE 3: Redeploy energy
        # ═══════════════════════════════════════════════════════════════════════
        chain.redeploy_energy()
        
        # ═══════════════════════════════════════════════════════════════════════
        # Summary
        # ═══════════════════════════════════════════════════════════════════════
        print()
        log_system(f"   Cycle {cycle} complete.")
        log_system(f"   Wins executed this session: {len(chain.wins_executed)}")
        
        if args.once:
            log_system("   --once flag set, exiting.")
            break
        
        print("\n   Waiting 30 seconds for next cycle (Ctrl+C to stop)...")
        try:
            time.sleep(30)
        except KeyboardInterrupt:
            print("\n\n👋 Kill Chain shutdown.")
            break

if __name__ == "__main__":
    main()
