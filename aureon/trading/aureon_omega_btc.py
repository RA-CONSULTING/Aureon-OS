#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
      AUREON OMEGA LIVE - BTC PAIRS TRADING (TRD_GRP_039)
═══════════════════════════════════════════════════════════════════════════════

This system trades on 194 BTC pairs. Strategy:
1. Consolidate all altcoins to BTC first
2. Use BTC to buy promising altcoins
3. Sell altcoins back to BTC when profitable
4. Repeat

The cycle: BTC → ALT → BTC (with profit)
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import math
import time
import hmac
import hashlib
import json
from datetime import datetime
from urllib.parse import urlencode
from typing import Dict, List, Optional, Tuple
import requests
from aureon.exchanges.binance_client import get_binance_client

# 🪙 PENNY PROFIT ENGINE
try:
    import sys
    sys.path.insert(0, '/workspaces/aureon-trading')
    from aureon.trading.penny_profit_engine import check_penny_exit, get_penny_engine
    PENNY_PROFIT_AVAILABLE = True
    _penny_engine = get_penny_engine()
    print("🪙 Penny Profit Engine loaded for Omega BTC")
except ImportError:
    PENNY_PROFIT_AVAILABLE = False
    _penny_engine = None
    print("⚠️ Penny Profit Engine not available")

# 🧠 WISDOM COGNITION ENGINE - 11 Civilizations
try:
    from aureon.utils.aureon_miner_brain import WisdomCognitionEngine
    WISDOM_AVAILABLE = True
    _wisdom_engine = WisdomCognitionEngine()
    print("🧠 Wisdom Engine loaded - 11 civilizations ready")
except ImportError:
    WISDOM_AVAILABLE = False
    _wisdom_engine = None
    print("⚠️ Wisdom Engine not available")

# ═══════════════════════════════════════════════════════════════════════════════
# API KEYS (Key 4)
# ═══════════════════════════════════════════════════════════════════════════════
API_KEY = ''
API_SECRET = ''

# Trading config
MIN_TRADE_BTC = 0.00012  # ~$11 minimum trade (above min notional)
TARGET_PROFIT_PCT = 0.5   # 0.5% profit target
STOP_LOSS_PCT = 1.0       # 1% stop loss
SCAN_INTERVAL = 20        # Seconds between scans

# Sacred constants
PHI = (1 + math.sqrt(5)) / 2

# ═══════════════════════════════════════════════════════════════════════════════
# BINANCE CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

class BinanceClient:
    def __init__(self):
        self.api_key = API_KEY
        self.api_secret = API_SECRET
        self.base_url = "https://api.binance.com"
        
    def _sign(self, params: dict) -> str:
        query_string = urlencode(params)
        return hmac.new(self.api_secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()
        
    def _request(self, method: str, endpoint: str, params: dict = None, signed: bool = False) -> dict:
        url = f"{self.base_url}{endpoint}"
        headers = {"X-MBX-APIKEY": self.api_key}
        
        if params is None:
            params = {}
            
        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params["signature"] = self._sign(params)
            
        try:
            if method == "GET":
                response = requests.get(url, params=params, headers=headers, timeout=10)
            else:
                response = requests.post(url, params=params, headers=headers, timeout=10)
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_account(self) -> dict:
        return self._request("GET", "/api/v3/account", signed=True)
    
    def get_balance(self, asset: str) -> float:
        account = self.get_account()
        if 'balances' in account:
            for b in account['balances']:
                if b['asset'] == asset:
                    return float(b['free'])
        return 0.0
    
    def get_all_balances(self) -> Dict[str, float]:
        account = self.get_account()
        balances = {}
        if 'balances' in account:
            for b in account['balances']:
                free = float(b['free'])
                if free > 0:
                    balances[b['asset']] = free
        return balances
    
    def get_all_tickers(self) -> Dict[str, float]:
        tickers = self._request("GET", "/api/v3/ticker/price")
        if isinstance(tickers, list):
            return {t['symbol']: float(t['price']) for t in tickers}
        return {}
    
    def get_24h_stats(self, symbol: str) -> dict:
        return self._request("GET", "/api/v3/ticker/24hr", {"symbol": symbol})
    
    def get_klines(self, symbol: str, interval: str = "5m", limit: int = 50) -> List:
        data = self._request("GET", "/api/v3/klines", {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        })
        return data if isinstance(data, list) else []
    
    def get_exchange_info(self) -> dict:
        return self._request("GET", "/api/v3/exchangeInfo")
    
    def get_btc_pairs_info(self) -> Dict[str, dict]:
        """Get all BTC pairs with their trading rules"""
        info = self.get_exchange_info()
        pairs = {}
        if 'symbols' in info:
            for s in info['symbols']:
                if s['quoteAsset'] == 'BTC' and s['status'] == 'TRADING':
                    lot_size = {}
                    min_notional = 0
                    for f in s['filters']:
                        if f['filterType'] == 'LOT_SIZE':
                            lot_size = {
                                'minQty': float(f['minQty']),
                                'stepSize': float(f['stepSize'])
                            }
                        if f['filterType'] == 'NOTIONAL':
                            min_notional = float(f.get('minNotional', 0))
                    
                    pairs[s['symbol']] = {
                        'baseAsset': s['baseAsset'],
                        'lotSize': lot_size,
                        'minNotional': min_notional
                    }
        return pairs
    
    def format_quantity(self, quantity: float, step_size: float) -> str:
        """Format quantity to match lot size"""
        if step_size > 0:
            precision = max(0, int(round(-math.log10(step_size))))
            quantity = quantity - (quantity % step_size)
            return f"{quantity:.{precision}f}"
        return f"{quantity:.8f}"
    
    def place_order(self, symbol: str, side: str, quantity: float, step_size: float = 0.001) -> dict:
        """Place a market order"""
        qty_str = self.format_quantity(quantity, step_size)
        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": "MARKET",
            "quantity": qty_str
        }
        result = self._request("POST", "/api/v3/order", params, signed=True)
        return result

# ═══════════════════════════════════════════════════════════════════════════════
# OMEGA ANALYZER
# ═══════════════════════════════════════════════════════════════════════════════

class OmegaAnalyzer:
    """Analyze market using Omega Equation"""
    
    def analyze(self, klines: List, stats_24h: dict) -> dict:
        """Analyze a pair and return signal"""
        if not klines or len(klines) < 20:
            return {"signal": "HOLD", "score": 0}
        
        closes = [float(k[4]) for k in klines]
        volumes = [float(k[5]) for k in klines]
        highs = [float(k[2]) for k in klines]
        lows = [float(k[3]) for k in klines]
        
        current = closes[-1]
        
        # Momentum
        mom_5 = (closes[-1] - closes[-6]) / closes[-6] if closes[-6] > 0 else 0
        mom_10 = (closes[-1] - closes[-11]) / closes[-11] if closes[-11] > 0 else 0
        
        # Moving averages
        sma_5 = sum(closes[-5:]) / 5
        sma_10 = sum(closes[-10:]) / 10
        sma_20 = sum(closes[-20:]) / 20
        
        # Volume surge
        vol_avg = sum(volumes[-10:]) / 10
        vol_surge = volumes[-1] / vol_avg if vol_avg > 0 else 1
        
        # Trend alignment
        trend = 1 if current > sma_5 > sma_10 else (-1 if current < sma_5 < sma_10 else 0)
        
        # RSI-like oversold/overbought
        gains = [max(0, closes[i] - closes[i-1]) for i in range(1, len(closes))]
        losses = [max(0, closes[i-1] - closes[i]) for i in range(1, len(closes))]
        avg_gain = sum(gains[-14:]) / 14
        avg_loss = sum(losses[-14:]) / 14
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi = 100 - (100 / (1 + rs))
        
        # 24h change
        change_24h = float(stats_24h.get('priceChangePercent', 0))
        
        # Score calculation (Omega-inspired)
        score = 0
        reasons = []
        
        # Momentum signals
        if mom_5 > 0.02 and mom_10 > 0:
            score += 30
            reasons.append(f"Strong momentum +{mom_5*100:.1f}%")
        elif mom_5 > 0.01:
            score += 15
            reasons.append(f"Positive momentum +{mom_5*100:.1f}%")
        
        # Trend alignment
        if trend == 1:
            score += 25
            reasons.append("Uptrend aligned")
        
        # Volume confirmation
        if vol_surge > 1.5:
            score += 20
            reasons.append(f"Volume surge {vol_surge:.1f}x")
        
        # RSI signals (buy oversold, avoid overbought)
        if 30 < rsi < 50 and mom_5 > 0:
            score += 15
            reasons.append(f"RSI recovery {rsi:.0f}")
        elif rsi > 75:
            score -= 20
            reasons.append(f"Overbought RSI {rsi:.0f}")
        
        # 24h context
        if -5 < change_24h < 0 and mom_5 > 0:
            score += 10
            reasons.append("Reversal from dip")
        
        signal = "HOLD"
        if score >= 50:
            signal = "BUY"
        elif score >= 30:
            signal = "WATCH"
        
        return {
            "signal": signal,
            "score": score,
            "momentum_5": mom_5,
            "momentum_10": mom_10,
            "trend": trend,
            "rsi": rsi,
            "vol_surge": vol_surge,
            "change_24h": change_24h,
            "reasons": reasons
        }

# ═══════════════════════════════════════════════════════════════════════════════
# POSITION TRACKER
# ═══════════════════════════════════════════════════════════════════════════════

class PositionTracker:
    """Track open positions for profit/loss management"""
    
    def __init__(self):
        self.positions = {}  # {asset: {entry_price, quantity, entry_time}}
        self.load()
    
    def load(self):
        try:
            with open('positions.json', 'r') as f:
                self.positions = json.load(f)
        except:
            self.positions = {}
    
    def save(self):
        with open('positions.json', 'w') as f:
            json.dump(self.positions, f, indent=2)
    
    def add_position(self, asset: str, entry_price: float, quantity: float):
        self.positions[asset] = {
            'entry_price': entry_price,
            'quantity': quantity,
            'entry_time': datetime.now().isoformat()
        }
        self.save()
    
    def remove_position(self, asset: str):
        if asset in self.positions:
            del self.positions[asset]
            self.save()
    
    def get_position(self, asset: str) -> Optional[dict]:
        return self.positions.get(asset)
    
    def check_exit(self, asset: str, current_price: float) -> Tuple[bool, str, float]:
        """Check if position should be closed using penny profit. Returns (should_exit, reason, pnl_pct)"""
        pos = self.get_position(asset)
        if not pos:
            return False, "", 0
        
        entry = pos['entry_price']
        pnl_pct = (current_price - entry) / entry * 100
        
        # Track cycles for min hold time
        pos['cycles'] = pos.get('cycles', 0) + 1
        qty = pos.get('qty', 0)
        current_value = qty * current_price
        entry_value = pos.get('entry_value', qty * entry)
        gross_pnl = current_value - entry_value
        
        # 🪙 PENNY PROFIT EXIT LOGIC
        if PENNY_PROFIT_AVAILABLE and _penny_engine is not None and entry_value > 0:
            action, _ = check_penny_exit('binance', entry_value, current_value)
            threshold = _penny_engine.get_threshold('binance', entry_value)
            
            if action == 'TAKE_PROFIT':
                return True, f"🪙 PENNY TP (${gross_pnl:.4f} >= ${threshold.win_gte:.4f})", pnl_pct
            elif action == 'STOP_LOSS' and pos['cycles'] >= 5:
                return True, f"🪙 PENNY SL (${gross_pnl:.4f} <= ${threshold.stop_lte:.4f})", pnl_pct
        else:
            # Fallback to percentage exits
            if pnl_pct >= TARGET_PROFIT_PCT:
                return True, f"PROFIT +{pnl_pct:.2f}%", pnl_pct
            elif pnl_pct <= -STOP_LOSS_PCT and pos['cycles'] >= 5:
                return True, f"STOP LOSS {pnl_pct:.2f}%", pnl_pct
        
        return False, f"Holding {pnl_pct:+.2f}%", pnl_pct

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN TRADING ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class AureonOmegaTrader:
    def __init__(self):
        self.client = get_binance_client()
        self.analyzer = OmegaAnalyzer()
        self.positions = PositionTracker()
        self.trade_count = 0
        self.profit_total = 0
        
    def consolidate_to_btc(self):
        """Sell all altcoins to BTC"""
        print("\n🔄 CONSOLIDATING ALTCOINS TO BTC...")
        print("=" * 60)
        
        balances = self.client.get_all_balances()
        prices = self.client.get_all_tickers()
        pairs_info = self.client.get_btc_pairs_info()
        
        for asset, amount in balances.items():
            if asset in ['BTC', 'LDUSDC', 'USDT', 'SHIB', 'ZKC']:
                continue  # Skip BTC and non-tradeable
            
            symbol = f"{asset}BTC"
            if symbol not in pairs_info:
                continue
            
            info = pairs_info[symbol]
            price = prices.get(symbol, 0)
            
            if price == 0:
                continue
            
            btc_value = amount * price
            
            # Check if worth selling (above min notional)
            if btc_value < info['minNotional']:
                print(f"   {asset}: {amount:.8f} = {btc_value:.8f} BTC - Too small")
                continue
            
            # Sell it
            step_size = info['lotSize'].get('stepSize', 0.001)
            min_qty = info['lotSize'].get('minQty', 0.001)
            
            if amount < min_qty:
                print(f"   {asset}: Below minimum quantity")
                continue
            
            print(f"   Selling {amount:.8f} {asset} for ~{btc_value:.8f} BTC...")
            
            result = self.client.place_order(symbol, "SELL", amount, step_size)
            
            if 'orderId' in result:
                print(f"   ✅ Sold! Order ID: {result['orderId']}")
                self.positions.remove_position(asset)
            else:
                print(f"   ❌ Failed: {result.get('msg', result)}")
            
            time.sleep(0.5)  # Rate limit
        
        # Show final BTC balance
        btc = self.client.get_balance('BTC')
        btc_usd = btc * prices.get('BTCUSDT', 95000)
        print("=" * 60)
        print(f"💰 BTC Balance: {btc:.8f} (~${btc_usd:.2f})")
        
    def scan_opportunities(self) -> List[dict]:
        """Scan BTC pairs for buying opportunities"""
        print("\n🔍 Scanning BTC pairs...")
        
        pairs_info = self.client.get_btc_pairs_info()
        prices = self.client.get_all_tickers()
        
        opportunities = []
        
        # Get 24h stats for volume filtering
        btc_tickers = []
        for symbol in list(pairs_info.keys())[:100]:  # Top 100 pairs
            try:
                stats = self.client.get_24h_stats(symbol)
                if 'quoteVolume' in stats:
                    vol_btc = float(stats['quoteVolume'])
                    if vol_btc > 5:  # More than 5 BTC daily volume
                        btc_tickers.append((symbol, stats, vol_btc))
            except:
                continue
            time.sleep(0.05)  # Rate limit
        
        # Sort by volume
        btc_tickers.sort(key=lambda x: -x[2])
        
        print(f"   Found {len(btc_tickers)} liquid pairs")
        
        # Analyze top pairs
        for symbol, stats, vol in btc_tickers[:30]:
            try:
                klines = self.client.get_klines(symbol, "5m", 50)
                if not klines:
                    continue
                
                analysis = self.analyzer.analyze(klines, stats)
                
                if analysis['signal'] in ['BUY', 'WATCH'] and analysis['score'] >= 30:
                    analysis['symbol'] = symbol
                    analysis['baseAsset'] = pairs_info[symbol]['baseAsset']
                    analysis['price'] = prices.get(symbol, 0)
                    analysis['volume_btc'] = vol
                    analysis['lotSize'] = pairs_info[symbol]['lotSize']
                    analysis['minNotional'] = pairs_info[symbol]['minNotional']
                    opportunities.append(analysis)
                    
            except Exception as e:
                continue
            
            time.sleep(0.1)
        
        # Sort by score
        opportunities.sort(key=lambda x: -x['score'])
        
        return opportunities[:5]
    
    def check_positions(self):
        """Check existing positions for exit signals"""
        prices = self.client.get_all_tickers()
        balances = self.client.get_all_balances()
        pairs_info = self.client.get_btc_pairs_info()
        
        for asset, pos in list(self.positions.positions.items()):
            if asset not in balances:
                self.positions.remove_position(asset)
                continue
            
            symbol = f"{asset}BTC"
            if symbol not in prices:
                continue
            
            current_price = prices[symbol]
            should_exit, reason, pnl_pct = self.positions.check_exit(asset, current_price)
            
            if should_exit:
                print(f"\n🎯 EXIT SIGNAL: {asset} - {reason}")
                
                quantity = balances[asset]
                info = pairs_info.get(symbol, {})
                step_size = info.get('lotSize', {}).get('stepSize', 0.001)
                
                result = self.client.place_order(symbol, "SELL", quantity, step_size)
                
                if 'orderId' in result:
                    print(f"   ✅ Sold {asset} at {pnl_pct:+.2f}%")
                    self.positions.remove_position(asset)
                    self.profit_total += pnl_pct
                    self.trade_count += 1
                else:
                    print(f"   ❌ Failed: {result.get('msg', result)}")
    
    def execute_buy(self, opp: dict) -> bool:
        """Execute a buy order"""
        symbol = opp['symbol']
        asset = opp['baseAsset']
        price = opp['price']
        
        # Check if we already have a position
        if self.positions.get_position(asset):
            print(f"   Already holding {asset}")
            return False
        
        # Get BTC balance
        btc = self.client.get_balance('BTC')
        
        # Use small portion of BTC
        trade_btc = min(MIN_TRADE_BTC, btc * 0.2)
        
        if trade_btc < opp['minNotional']:
            print(f"   Trade too small: {trade_btc:.8f} BTC < {opp['minNotional']:.8f}")
            return False
        
        # Calculate quantity
        quantity = trade_btc / price
        step_size = opp['lotSize'].get('stepSize', 0.001)
        min_qty = opp['lotSize'].get('minQty', 0.001)
        
        # Format quantity
        quantity = quantity - (quantity % step_size)
        
        if quantity < min_qty:
            print(f"   Quantity too small")
            return False
        
        print(f"\n   🎯 BUYING {symbol}")
        print(f"      Quantity: {quantity:.8f} {asset}")
        print(f"      Price: {price:.8f} BTC")
        print(f"      Value: {trade_btc:.8f} BTC")
        print(f"      Reasons: {', '.join(opp['reasons'])}")
        
        result = self.client.place_order(symbol, "BUY", quantity, step_size)
        
        if 'orderId' in result:
            print(f"      ✅ Order filled! ID: {result['orderId']}")
            self.positions.add_position(asset, price, quantity)
            return True
        else:
            print(f"      ❌ Failed: {result.get('msg', result)}")
            return False
    
    def print_status(self):
        """Print current status"""
        prices = self.client.get_all_tickers()
        balances = self.client.get_all_balances()
        btc_price = prices.get('BTCUSDT', 95000)
        
        btc = balances.get('BTC', 0)
        
        print(f"\n📊 STATUS")
        print(f"   BTC: {btc:.8f} (~${btc * btc_price:.2f})")
        print(f"   Trades: {self.trade_count}")
        print(f"   Total P/L: {self.profit_total:+.2f}%")
        
        if self.positions.positions:
            print(f"\n   Open Positions:")
            for asset, pos in self.positions.positions.items():
                symbol = f"{asset}BTC"
                current = prices.get(symbol, pos['entry_price'])
                pnl = (current - pos['entry_price']) / pos['entry_price'] * 100
                print(f"      {asset}: {pnl:+.2f}% (entry: {pos['entry_price']:.8f})")
    
    def run(self, duration_minutes: int = 60):
        """Run the trading loop"""
        print("""
═══════════════════════════════════════════════════════════════════════════════
      AUREON OMEGA - BTC PAIRS LIVE TRADING
═══════════════════════════════════════════════════════════════════════════════

                    Ω(t) = Tr[Ψ(t) × ℒ(t) ⊗ O(t)]

🔒 TRD_GRP_039: Trading 194 BTC pairs
💰 Strategy: BTC → ALT → BTC (with profit)
🎯 Target: +{:.1f}% per trade
🛑 Stop Loss: -{:.1f}%

Starting in 3 seconds...
""".format(TARGET_PROFIT_PCT, STOP_LOSS_PCT))
        
        time.sleep(3)
        
        # First consolidate
        self.consolidate_to_btc()
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        scan_count = 0
        
        while time.time() < end_time:
            scan_count += 1
            elapsed = (time.time() - start_time) / 60
            remaining = duration_minutes - elapsed
            
            print(f"\n{'='*60}")
            print(f"📡 SCAN #{scan_count} | Elapsed: {elapsed:.1f}m | Remaining: {remaining:.1f}m")
            print(f"{'='*60}")
            
            # Check existing positions first
            self.check_positions()
            
            # Scan for new opportunities
            opportunities = self.scan_opportunities()
            
            if opportunities:
                print(f"\n🌟 Top Opportunities:")
                for opp in opportunities:
                    print(f"   {opp['symbol']}: Score={opp['score']} | {', '.join(opp['reasons'][:2])}")
                
                # Try to execute best opportunity
                best = opportunities[0]
                if best['score'] >= 50:
                    self.execute_buy(best)
            else:
                print("\n   📭 No strong opportunities")
            
            # Print status
            self.print_status()
            
            # Wait for next scan
            print(f"\n⏳ Next scan in {SCAN_INTERVAL}s...")
            time.sleep(SCAN_INTERVAL)
        
        print(f"\n{'='*60}")
        print("SESSION COMPLETE")
        print(f"{'='*60}")
        print(f"Total Scans: {scan_count}")
        print(f"Total Trades: {self.trade_count}")
        print(f"Total P/L: {self.profit_total:+.2f}%")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    
    duration = 60  # Default 60 minutes
    if len(sys.argv) > 1:
        if sys.argv[1] == "--consolidate":
            trader = AureonOmegaTrader()
            trader.consolidate_to_btc()
            sys.exit(0)
        try:
            duration = int(sys.argv[1])
        except:
            pass
    
    trader = AureonOmegaTrader()
    trader.run(duration_minutes=duration)
