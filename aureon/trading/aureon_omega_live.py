#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
      AUREON OMEGA LIVE - REAL TRADING WITH BTC PAIRS (TRD_GRP_039)
═══════════════════════════════════════════════════════════════════════════════

                    Ω(t) = Tr[Ψ(t) × ℒ(t) ⊗ O(t)]

This is the LIVE trading version. It will:
1. Scan all BTC pairs for opportunities
2. Use the OMEGA equation for signal generation
3. Execute REAL trades on Binance

TRD_GRP_039 = BTC pairs ONLY (no USDT)
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

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# API Keys (Key 4 - TRD_GRP_039)
API_KEY = ''
API_SECRET = ''

# Trading parameters
TRADE_AMOUNT_BTC = 0.00008  # ~$7 per trade
MIN_PROFIT_PERCENT = 0.3    # 0.3% minimum profit target
MAX_TRADES_PER_HOUR = 10    # Rate limit
SCAN_INTERVAL = 30          # Seconds between scans

# Sacred constants
PHI = (1 + math.sqrt(5)) / 2  # Golden Ratio ≈ 1.618
LOVE_FREQUENCY = 528  # Hz
SCHUMANN_BASE = 7.83  # Hz

# Primes for position scaling
PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]

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
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
        
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
    
    def get_btc_balance(self) -> float:
        account = self.get_account()
        if 'balances' in account:
            for b in account['balances']:
                if b['asset'] == 'BTC':
                    return float(b['free'])
        return 0.0
    
    def get_all_tickers(self) -> Dict[str, float]:
        tickers = self._request("GET", "/api/v3/ticker/price")
        if isinstance(tickers, list):
            return {t['symbol']: float(t['price']) for t in tickers}
        return {}
    
    def get_24h_stats(self, symbol: str) -> dict:
        return self._request("GET", "/api/v3/ticker/24hr", {"symbol": symbol})
    
    def get_klines(self, symbol: str, interval: str = "15m", limit: int = 50) -> List:
        data = self._request("GET", "/api/v3/klines", {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        })
        return data if isinstance(data, list) else []
    
    def get_exchange_info(self) -> dict:
        return self._request("GET", "/api/v3/exchangeInfo")
    
    def get_btc_pairs(self) -> List[dict]:
        """Get all tradeable BTC pairs with their lot sizes"""
        info = self.get_exchange_info()
        pairs = []
        if 'symbols' in info:
            for s in info['symbols']:
                if s['quoteAsset'] == 'BTC' and s['status'] == 'TRADING':
                    # Get LOT_SIZE filter
                    lot_size = None
                    min_notional = None
                    for f in s['filters']:
                        if f['filterType'] == 'LOT_SIZE':
                            lot_size = {
                                'minQty': float(f['minQty']),
                                'maxQty': float(f['maxQty']),
                                'stepSize': float(f['stepSize'])
                            }
                        if f['filterType'] == 'NOTIONAL':
                            min_notional = float(f.get('minNotional', 0))
                    
                    pairs.append({
                        'symbol': s['symbol'],
                        'baseAsset': s['baseAsset'],
                        'lotSize': lot_size,
                        'minNotional': min_notional
                    })
        return pairs
    
    def place_order(self, symbol: str, side: str, quantity: float) -> dict:
        """Place a market order"""
        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": "MARKET",
            "quantity": f"{quantity:.8f}".rstrip('0').rstrip('.')
        }
        return self._request("POST", "/api/v3/order", params, signed=True)

# ═══════════════════════════════════════════════════════════════════════════════
# OMEGA EQUATION (Simplified for Live Trading)
# ═══════════════════════════════════════════════════════════════════════════════

class OmegaAnalyzer:
    """Analyze market using Omega Equation principles"""
    
    def __init__(self):
        self.history = {}
        
    def analyze_pair(self, symbol: str, klines: List, stats_24h: dict) -> dict:
        """
        Analyze a trading pair using the Omega Equation
        
        Returns analysis with:
        - omega: Reality field strength (0-2)
        - psi: Potential (volatility + momentum)
        - love: Coherence (trend alignment)
        - signal: BUY/SELL/HOLD
        - confidence: 0-1
        """
        if not klines or len(klines) < 10:
            return {"signal": "HOLD", "confidence": 0, "reason": "Insufficient data"}
        
        # Extract OHLCV data
        closes = [float(k[4]) for k in klines]
        highs = [float(k[2]) for k in klines]
        lows = [float(k[3]) for k in klines]
        volumes = [float(k[5]) for k in klines]
        
        current_price = closes[-1]
        
        # ═══════════════════════════════════════════════════════════════════
        # Ψ(t) - POTENTIAL: Volatility + Momentum
        # ═══════════════════════════════════════════════════════════════════
        
        # Volatility (range / price)
        volatility = sum(h - l for h, l in zip(highs[-10:], lows[-10:])) / (10 * current_price)
        
        # Momentum (price change over periods)
        momentum_5 = (closes[-1] - closes[-6]) / closes[-6] if closes[-6] > 0 else 0
        momentum_10 = (closes[-1] - closes[-11]) / closes[-11] if len(closes) > 10 and closes[-11] > 0 else 0
        
        # Psi: combination of volatility and momentum
        psi = abs(momentum_5) * 5 + volatility * 10
        psi = min(1, psi)
        
        # ═══════════════════════════════════════════════════════════════════
        # ℒ(t) - LOVE/COHERENCE: Trend alignment
        # ═══════════════════════════════════════════════════════════════════
        
        # Simple moving averages
        sma_5 = sum(closes[-5:]) / 5
        sma_10 = sum(closes[-10:]) / 10
        sma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else sma_10
        
        # Trend alignment (are SMAs in order?)
        if current_price > sma_5 > sma_10 > sma_20:
            trend_alignment = 1.0  # Perfect uptrend
        elif current_price < sma_5 < sma_10 < sma_20:
            trend_alignment = -1.0  # Perfect downtrend
        else:
            trend_alignment = 0.0  # Mixed
        
        # Volume trend
        vol_sma = sum(volumes[-10:]) / 10
        vol_current = volumes[-1]
        volume_surge = vol_current / vol_sma if vol_sma > 0 else 1
        
        # Love: coherence of trend
        love = abs(trend_alignment) * 0.7 + min(1, volume_surge / 3) * 0.3
        
        # ═══════════════════════════════════════════════════════════════════
        # O(t) - OBSERVER: 24h context
        # ═══════════════════════════════════════════════════════════════════
        
        price_change_24h = float(stats_24h.get('priceChangePercent', 0))
        volume_24h = float(stats_24h.get('volume', 0))
        
        # Observer context
        observer = 0.5 + (price_change_24h / 20)  # Normalize to 0-1 range
        observer = max(0, min(1, observer))
        
        # ═══════════════════════════════════════════════════════════════════
        # Ω(t) = Tr[Ψ × ℒ ⊗ O]
        # ═══════════════════════════════════════════════════════════════════
        
        omega = psi * love * observer + (psi * 0.4 + love * 0.4 + observer * 0.2)
        
        # ═══════════════════════════════════════════════════════════════════
        # SIGNAL GENERATION
        # ═══════════════════════════════════════════════════════════════════
        
        signal = "HOLD"
        confidence = 0
        reason = ""
        
        # Strong uptrend with momentum
        if trend_alignment > 0.5 and momentum_5 > 0.005 and volume_surge > 1.2:
            signal = "BUY"
            confidence = min(0.95, omega * love)
            reason = f"Uptrend +{momentum_5*100:.2f}% vol_surge:{volume_surge:.1f}x"
        
        # Strong downtrend - sell signal
        elif trend_alignment < -0.5 and momentum_5 < -0.005:
            signal = "SELL"
            confidence = min(0.95, omega * abs(love))
            reason = f"Downtrend {momentum_5*100:.2f}%"
        
        # Reversal pattern - potential buy
        elif momentum_5 > 0.01 and momentum_10 < 0 and volume_surge > 1.5:
            signal = "BUY"
            confidence = min(0.8, omega * 0.7)
            reason = f"Reversal +{momentum_5*100:.2f}% from -{abs(momentum_10)*100:.2f}%"
        
        # Golden ratio check (Fibonacci levels)
        fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786]
        high_20 = max(highs[-20:]) if len(highs) >= 20 else max(highs)
        low_20 = min(lows[-20:]) if len(lows) >= 20 else min(lows)
        range_20 = high_20 - low_20
        
        if range_20 > 0:
            price_position = (current_price - low_20) / range_20
            # Check if near Fibonacci level
            for fib in fib_levels:
                if abs(price_position - fib) < 0.03:
                    if momentum_5 > 0:
                        signal = "BUY"
                        confidence = min(0.75, omega * 0.6)
                        reason = f"Fib {fib:.3f} bounce +{momentum_5*100:.2f}%"
                    break
        
        return {
            "symbol": symbol,
            "signal": signal,
            "confidence": confidence,
            "omega": omega,
            "psi": psi,
            "love": love,
            "observer": observer,
            "momentum_5": momentum_5,
            "momentum_10": momentum_10,
            "trend": trend_alignment,
            "volume_surge": volume_surge,
            "price_change_24h": price_change_24h,
            "current_price": current_price,
            "reason": reason
        }

# ═══════════════════════════════════════════════════════════════════════════════
# LIVE TRADING ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class AureonOmegaLive:
    def __init__(self):
        self.client = get_binance_client()
        self.analyzer = OmegaAnalyzer()
        self.trades_this_hour = 0
        self.hour_start = time.time()
        self.trade_log = []
        self.prime_index = 0
        
    def get_prime_multiplier(self) -> float:
        """Get next prime for position scaling"""
        prime = PRIMES[self.prime_index % len(PRIMES)]
        self.prime_index += 1
        return prime * 0.01
        
    def format_quantity(self, quantity: float, step_size: float) -> float:
        """Format quantity to match lot size requirements"""
        if step_size > 0:
            precision = int(round(-math.log10(step_size)))
            return round(quantity - (quantity % step_size), precision)
        return quantity
    
    def scan_opportunities(self) -> List[dict]:
        """Scan all BTC pairs for trading opportunities"""
        print("\n🔍 Scanning BTC pairs...")
        
        btc_pairs = self.client.get_btc_pairs()
        print(f"   Found {len(btc_pairs)} tradeable BTC pairs")
        
        opportunities = []
        
        # Filter to most liquid pairs
        tickers = self.client.get_all_tickers()
        
        for pair in btc_pairs[:50]:  # Check top 50
            symbol = pair['symbol']
            
            try:
                # Get 24h stats
                stats = self.client.get_24h_stats(symbol)
                if 'code' in stats:
                    continue
                    
                volume_btc = float(stats.get('quoteVolume', 0))
                
                # Skip low volume pairs
                if volume_btc < 1:  # Less than 1 BTC daily volume
                    continue
                
                # Get klines
                klines = self.client.get_klines(symbol, "15m", 50)
                if not klines:
                    continue
                
                # Analyze
                analysis = self.analyzer.analyze_pair(symbol, klines, stats)
                
                if analysis['signal'] == 'BUY' and analysis['confidence'] > 0.5:
                    analysis['lot_size'] = pair['lotSize']
                    analysis['min_notional'] = pair['minNotional']
                    analysis['volume_btc'] = volume_btc
                    opportunities.append(analysis)
                    
            except Exception as e:
                continue
        
        # Sort by confidence
        opportunities.sort(key=lambda x: x['confidence'], reverse=True)
        
        return opportunities[:5]  # Top 5 opportunities
    
    def execute_trade(self, opportunity: dict) -> Optional[dict]:
        """Execute a trade based on opportunity"""
        symbol = opportunity['symbol']
        
        # Check rate limit
        if time.time() - self.hour_start > 3600:
            self.trades_this_hour = 0
            self.hour_start = time.time()
            
        if self.trades_this_hour >= MAX_TRADES_PER_HOUR:
            print(f"   ⏸️  Rate limit reached ({MAX_TRADES_PER_HOUR}/hour)")
            return None
        
        # Get BTC balance
        btc_balance = self.client.get_btc_balance()
        
        if btc_balance < TRADE_AMOUNT_BTC:
            print(f"   ⚠️  Insufficient BTC: {btc_balance:.8f} < {TRADE_AMOUNT_BTC:.8f}")
            return None
        
        # Calculate quantity
        price = opportunity['current_price']
        lot_size = opportunity.get('lot_size', {})
        
        raw_quantity = TRADE_AMOUNT_BTC / price
        step_size = lot_size.get('stepSize', 0.001)
        min_qty = lot_size.get('minQty', 0.001)
        
        quantity = self.format_quantity(raw_quantity, step_size)
        
        if quantity < min_qty:
            print(f"   ⚠️  Quantity {quantity} below minimum {min_qty}")
            return None
        
        # Execute BUY
        print(f"\n   🎯 EXECUTING BUY: {symbol}")
        print(f"      Quantity: {quantity:.8f}")
        print(f"      Price: {price:.8f} BTC")
        print(f"      Value: ~{TRADE_AMOUNT_BTC:.8f} BTC")
        print(f"      Reason: {opportunity['reason']}")
        
        result = self.client.place_order(symbol, "BUY", quantity)
        
        if 'orderId' in result:
            self.trades_this_hour += 1
            
            trade_record = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'side': 'BUY',
                'quantity': quantity,
                'price': price,
                'order_id': result['orderId'],
                'confidence': opportunity['confidence'],
                'omega': opportunity['omega'],
                'reason': opportunity['reason']
            }
            self.trade_log.append(trade_record)
            
            print(f"      ✅ Order filled! ID: {result['orderId']}")
            return trade_record
        else:
            print(f"      ❌ Order failed: {result}")
            return None
    
    def run(self, duration_minutes: int = 60):
        """Run the live trading loop"""
        print("""
═══════════════════════════════════════════════════════════════════════════════
      AUREON OMEGA LIVE - REAL TRADING ACTIVATED
═══════════════════════════════════════════════════════════════════════════════

                    Ω(t) = Tr[Ψ(t) × ℒ(t) ⊗ O(t)]

⚠️  LIVE TRADING MODE - REAL MONEY AT RISK
💰 Trade Amount: ~{} BTC per trade
🎯 Min Profit Target: {}%
⏱️  Scan Interval: {}s
🔒 TRD_GRP_039: BTC pairs only

Starting in 5 seconds...
""".format(TRADE_AMOUNT_BTC, MIN_PROFIT_PERCENT, SCAN_INTERVAL))
        
        time.sleep(5)
        
        # Check initial balance
        btc_balance = self.client.get_btc_balance()
        print(f"\n💰 Starting BTC Balance: {btc_balance:.8f} BTC")
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        scan_count = 0
        
        while time.time() < end_time:
            scan_count += 1
            elapsed = (time.time() - start_time) / 60
            remaining = duration_minutes - elapsed
            
            print(f"\n{'='*60}")
            print(f"📊 SCAN #{scan_count} | Elapsed: {elapsed:.1f}m | Remaining: {remaining:.1f}m")
            print(f"{'='*60}")
            
            # Scan for opportunities
            opportunities = self.scan_opportunities()
            
            if opportunities:
                print(f"\n🌟 Found {len(opportunities)} opportunities:")
                for i, opp in enumerate(opportunities, 1):
                    print(f"   {i}. {opp['symbol']}: Ω={opp['omega']:.3f} conf={opp['confidence']:.2f}")
                    print(f"      └─ {opp['reason']}")
                
                # Execute best opportunity
                best = opportunities[0]
                if best['confidence'] > 0.6:
                    self.execute_trade(best)
                else:
                    print(f"\n   ⏸️  Best opportunity confidence too low ({best['confidence']:.2f})")
            else:
                print("\n   📭 No strong opportunities found")
            
            # Show current positions
            account = self.client.get_account()
            if 'balances' in account:
                print(f"\n📈 Current Holdings:")
                for b in account['balances']:
                    total = float(b['free']) + float(b['locked'])
                    if total > 0 and b['asset'] not in ['LDUSDC', 'USDT']:
                        print(f"   {b['asset']}: {total:.8f}")
            
            # Wait for next scan
            print(f"\n⏳ Next scan in {SCAN_INTERVAL}s...")
            time.sleep(SCAN_INTERVAL)
        
        # Final summary
        print(f"\n{'='*60}")
        print("SESSION COMPLETE")
        print(f"{'='*60}")
        print(f"Total Scans: {scan_count}")
        print(f"Total Trades: {len(self.trade_log)}")
        
        btc_balance_end = self.client.get_btc_balance()
        print(f"Final BTC Balance: {btc_balance_end:.8f}")
        
        if self.trade_log:
            print(f"\nTrades executed:")
            for t in self.trade_log:
                print(f"  - {t['timestamp']}: {t['side']} {t['quantity']:.8f} {t['symbol']}")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    
    duration = 30  # Default 30 minutes
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except:
            pass
    
    trader = AureonOmegaLive()
    trader.run(duration_minutes=duration)
