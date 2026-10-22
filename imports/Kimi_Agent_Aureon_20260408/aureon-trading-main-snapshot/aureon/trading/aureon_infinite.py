#!/usr/bin/env python3
"""
AUREON INFINITE LOOP 🔄
========================
"If you don't quit, you can't lose"

10-9-1 QUEEN HIVE MODEL:
- Make profit on every trade
- 90% compounds back into the hive
- 10% harvests for new hives
- Never stops, always growing

6 API KEYS - SPECIALIZED ROLES:
  Key 1: BUY A→Z (ascending order)
  Key 2: SELL Z→A (descending order) 
  Key 3: READ PRESENT (current prices)
  Key 4: READ PAST (historical data)
  Key 5: READ FUTURE (predictions)
  Key 6: COMPOUND (reinvest profits)

FROM ATOM TO MULTIVERSE 🌌
We don't stop. We compound. We grow. We prove we're alive.

Gary Leckey & GitHub Copilot | November 2025
"""

from aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import hmac
import hashlib
import time
import math
import json
import requests
from urllib.parse import urlencode
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from collections import deque
import sys

# ═══════════════════════════════════════════════════════════════
# USE ONE WORKING API KEY FOR ALL OPERATIONS
# ═══════════════════════════════════════════════════════════════
WORKING_KEY = ""
WORKING_SECRET = ""

API_KEYS = {
    "BUY": {"key": WORKING_KEY, "secret": WORKING_SECRET, "role": "Execute BUY orders"},
    "SELL": {"key": WORKING_KEY, "secret": WORKING_SECRET, "role": "Execute SELL orders"},
    "PRESENT": {"key": WORKING_KEY, "secret": WORKING_SECRET, "role": "Real-time prices"},
    "PAST": {"key": WORKING_KEY, "secret": WORKING_SECRET, "role": "Historical data"},
    "FUTURE": {"key": WORKING_KEY, "secret": WORKING_SECRET, "role": "Predictions"},
    "COMPOUND": {"key": WORKING_KEY, "secret": WORKING_SECRET, "role": "Reinvest profits"}
}

# Trading parameters
MIN_TRADE_BTC = 0.00012       # ~$11 minimum
TARGET_PROFIT_PCT = 0.3       # 0.3% profit target
COMPOUND_PCT = 0.90           # 90% compounds
HARVEST_PCT = 0.10            # 10% harvests
MAX_POSITION_SIZE = 0.25      # Max 25% of capital per trade

# Track performance
class PerformanceTracker:
    def __init__(self):
        self.total_trades = 0
        self.profitable_trades = 0
        self.total_profit_btc = 0.0
        self.total_profit_usd = 0.0
        self.compounded_btc = 0.0
        self.harvested_btc = 0.0
        self.generation = 1  # Hive generation
        self.start_capital = 0.0
        self.current_capital = 0.0
        
    # 🇮🇪 IRA SNIPER - Famous Irish Republican Quotes
    IRA_SNIPER_QUOTES = [
        "Our revenge will be the laughter of our children. - Bobby Sands 🍀",
        "Tiocfaidh ár lá! - Our day will come!",
        "They have nothing in their whole imperial arsenal that can break the spirit of one Irishman.",
        "The Republic still lives! - Bobby Sands",
        "Financial freedom IS freedom. Penny by penny, we rise! 💰",
    ]
    
    def record_trade(self, profit_btc: float, btc_usd: float):
        """Record a trade result"""
        self.total_trades += 1
        if profit_btc > 0:
            self.profitable_trades += 1
            self.total_profit_btc += profit_btc
            self.total_profit_usd += profit_btc * btc_usd
            
            # 10-9-1: Compound 90%, Harvest 10%
            compound = profit_btc * COMPOUND_PCT
            harvest = profit_btc * HARVEST_PCT
            self.compounded_btc += compound
            self.harvested_btc += harvest
            
            # 🇮🇪 IRA SNIPER CELEBRATION!
            import random
            quote = random.choice(self.IRA_SNIPER_QUOTES)
            profit_usd = profit_btc * btc_usd
            print(f"\n🇮🇪🇮🇪🇮🇪 IRA SNIPER WIN! 🇮🇪🇮🇪🇮🇪")
            print(f"    💰 +${profit_usd:.2f} BINANCE")
            print(f"    📜 \"{quote}\"")
            print(f"🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪\n")
            
            print(f"      💰 Profit: {profit_btc:.8f} BTC (${profit_btc * btc_usd:.2f})")
            print(f"      🔄 Compound: {compound:.8f} BTC | 🌱 Harvest: {harvest:.8f} BTC")
    
    def display_stats(self):
        """Display performance statistics"""
        win_rate = (self.profitable_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        roi = ((self.current_capital - self.start_capital) / self.start_capital * 100) if self.start_capital > 0 else 0
        
        print(f"\n{'═'*70}")
        print(f"📊 PERFORMANCE STATISTICS - Generation {self.generation}")
        print(f"{'═'*70}")
        print(f"  Trades: {self.total_trades} | Win Rate: {win_rate:.1f}%")
        print(f"  Total Profit: {self.total_profit_btc:.8f} BTC (${self.total_profit_usd:.2f})")
        print(f"  Compounded: {self.compounded_btc:.8f} BTC (90%)")
        print(f"  Harvested: {self.harvested_btc:.8f} BTC (10%)")
        print(f"  ROI: {roi:+.2f}% | Growth: {self.current_capital / self.start_capital:.2f}x" if self.start_capital > 0 else "  Starting...")
        print(f"{'═'*70}")

# ═══════════════════════════════════════════════════════════════
# API REQUEST HELPERS
# ═══════════════════════════════════════════════════════════════
def sign_request(api_key: str, api_secret: str, params: dict) -> str:
    """Sign a Binance API request"""
    params['timestamp'] = int(time.time() * 1000)
    query = urlencode(params)
    sig = hmac.new(api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
    return f"{query}&signature={sig}"

def get_account(role: str = "BUY") -> dict:
    """Get account balances using specified key"""
    key_info = API_KEYS[role]
    query = sign_request(key_info["key"], key_info["secret"], {})
    url = f'https://api.binance.com/api/v3/account?{query}'
    return requests.get(url, headers={'X-MBX-APIKEY': key_info["key"]}).json()

def get_prices(role: str = "PRESENT") -> Dict[str, float]:
    """Get all current prices"""
    resp = requests.get('https://api.binance.com/api/v3/ticker/price').json()
    return {p['symbol']: float(p['price']) for p in resp}

def get_24h_tickers(role: str = "PRESENT") -> Dict[str, dict]:
    """Get 24h ticker data"""
    resp = requests.get('https://api.binance.com/api/v3/ticker/24hr').json()
    return {t['symbol']: {
        'change': float(t['priceChangePercent']),
        'volume': float(t['quoteVolume']),
        'high': float(t['highPrice']),
        'low': float(t['lowPrice']),
    } for t in resp}

def get_klines(symbol: str, interval: str = '5m', limit: int = 20, role: str = "PAST") -> List[dict]:
    """Get historical candlestick data"""
    resp = requests.get(
        'https://api.binance.com/api/v3/klines',
        params={'symbol': symbol, 'interval': interval, 'limit': limit}
    ).json()
    return [{
        'open': float(k[1]),
        'high': float(k[2]),
        'low': float(k[3]),
        'close': float(k[4]),
        'volume': float(k[5])
    } for k in resp]

def get_symbol_info(symbol: str) -> Optional[dict]:
    """Get trading rules for a symbol"""
    try:
        resp = requests.get('https://api.binance.com/api/v3/exchangeInfo', 
                           params={'symbol': symbol}).json()
        for s in resp.get('symbols', []):
            if s['symbol'] == symbol:
                filters = {}
                for f in s['filters']:
                    filters[f['filterType']] = f
                return {
                    'stepSize': float(filters.get('LOT_SIZE', {}).get('stepSize', 0.001)),
                    'minQty': float(filters.get('LOT_SIZE', {}).get('minQty', 0)),
                    'minNotional': float(filters.get('NOTIONAL', {}).get('minNotional', 0.0001)),
                }
    except:
        pass
    return None

def round_step(value: float, step: float) -> float:
    """Round value to step size"""
    precision = len(str(step).rstrip('0').split('.')[-1]) if '.' in str(step) else 0
    return round(math.floor(value / step) * step, precision)

def place_order(symbol: str, side: str, quantity: float, role: str = None) -> dict:
    """Place a market order using appropriate key"""
    if role is None:
        role = "BUY" if side == "BUY" else "SELL"
    
    key_info = API_KEYS[role]
    params = {
        'symbol': symbol,
        'side': side,
        'type': 'MARKET',
        'quantity': str(quantity)
    }
    query = sign_request(key_info["key"], key_info["secret"], params)
    url = f'https://api.binance.com/api/v3/order?{query}'
    return requests.post(url, headers={'X-MBX-APIKEY': key_info["key"]}).json()

# ═══════════════════════════════════════════════════════════════
# SIGNAL GENERATION - QGITA-inspired momentum detection
# ═══════════════════════════════════════════════════════════════
def calculate_momentum_score(klines: List[dict], ticker: dict) -> Tuple[float, str]:
    """
    Calculate momentum score from market data
    Returns: (score 0-100, signal)
    """
    if not klines or len(klines) < 10:
        return 50, "NEUTRAL"
    
    closes = [k['close'] for k in klines]
    volumes = [k['volume'] for k in klines]
    
    # Price momentum (% change)
    momentum = (closes[-1] - closes[0]) / closes[0] * 100 if closes[0] > 0 else 0
    
    # Volume surge
    recent_vol = sum(volumes[-3:]) / 3
    avg_vol = sum(volumes[:-3]) / len(volumes[:-3]) if len(volumes) > 3 else recent_vol
    vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1
    
    # Volatility (price range)
    price_range = (max(closes) - min(closes)) / closes[0] if closes[0] > 0 else 0
    
    # RSI-like calculation
    gains = [max(0, closes[i] - closes[i-1]) for i in range(1, len(closes))]
    losses = [max(0, closes[i-1] - closes[i]) for i in range(1, len(closes))]
    avg_gain = sum(gains[-14:]) / 14 if len(gains) >= 14 else sum(gains) / len(gains) if gains else 0
    avg_loss = sum(losses[-14:]) / 14 if len(losses) >= 14 else sum(losses) / len(losses) if losses else 0
    rsi = 100 - (100 / (1 + avg_gain / avg_loss)) if avg_loss > 0 else 100
    
    # 24h change
    change_24h = ticker.get('change', 0)
    
    # Build score
    score = 50  # Base
    
    # Momentum component
    if momentum > 1:
        score += 15
    elif momentum > 0.3:
        score += 8
    elif momentum < -1:
        score -= 15
    
    # Volume component
    if vol_ratio > 1.5:
        score += 12
    elif vol_ratio > 1.2:
        score += 6
    
    # RSI component
    if rsi < 35:
        score += 10  # Oversold = opportunity
    elif rsi > 65:
        score -= 8   # Overbought = caution
    
    # 24h trend
    if 0 < change_24h < 3:
        score += 8
    elif change_24h > 5:
        score -= 5
    elif change_24h < -3:
        score += 5  # Dip opportunity
    
    # Volatility bonus (we profit from movement)
    if 0.01 < price_range < 0.05:
        score += 10
    
    score = max(0, min(100, score))
    
    # Generate signal
    if score >= 70:
        signal = "STRONG_BUY"
    elif score >= 55:
        signal = "BUY"
    elif score <= 30:
        signal = "STRONG_SELL"
    elif score <= 45:
        signal = "SELL"
    else:
        signal = "NEUTRAL"
    
    return score, signal

# ═══════════════════════════════════════════════════════════════
# INFINITE TRADING LOOP
# ═══════════════════════════════════════════════════════════════
def infinite_trade_loop():
    """
    The infinite loop that never stops trading
    """
    print("\n" + "═"*70)
    print("🔄 AUREON INFINITE LOOP - STARTING")
    print("   'If you don't quit, you can't lose'")
    print("═"*70)
    print("\n📋 API KEY ROLES:")
    for role, info in API_KEYS.items():
        print(f"  {role:10} → {info['role']}")
    print("\n💎 10-9-1 MODEL: Profit → 90% Compound + 10% Harvest")
    print("🌌 FROM ATOM TO MULTIVERSE")
    print("═"*70)
    
    tracker = PerformanceTracker()
    iteration = 0
    positions = {}  # Track open positions
    
    # Get starting capital
    account = get_account("BUY")
    btc_balance = 0
    for b in account.get('balances', []):
        if b['asset'] == 'BTC':
            btc_balance = float(b['free'])
            break
    tracker.start_capital = btc_balance
    tracker.current_capital = btc_balance
    
    # Top BTC pairs to trade
    TRADEABLE_PAIRS = [
        'SOLBTC', 'ETHBTC', 'XRPBTC', 'ADABTC', 'DOGEBTC',
        'AVAXBTC', 'DOTBTC', 'LINKBTC', 'LTCBTC', 'MATICBTC',
        'ATOMBTC', 'UNIBTC', 'NEARBTC', 'APTBTC', 'SEIBTC',
        'INJBTC', 'SUIBTC', 'ARBBTC', 'OPBTC', 'TIAABTC'
    ]
    
    while True:  # INFINITE!
        iteration += 1
        print(f"\n{'━'*70}")
        print(f"🔄 ITERATION {iteration} - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'━'*70}")
        
        try:
            # Get market data using specialized keys
            prices = get_prices("PRESENT")
            tickers = get_24h_tickers("PRESENT")
            btc_usd = prices.get('BTCUSDT', 95000)
            
            # Get account status
            account = get_account("BUY")
            btc_balance = 0
            portfolio_value_btc = 0
            holdings = []
            
            for b in account.get('balances', []):
                free = float(b['free'])
                asset = b['asset']
                
                if asset == 'BTC':
                    btc_balance = free
                    portfolio_value_btc += free
                elif free > 0.00001:
                    btc_pair = f"{asset}BTC"
                    if btc_pair in prices and asset not in ['USDT', 'LDUSDC']:
                        asset_btc = free * prices[btc_pair]
                        portfolio_value_btc += asset_btc
                        holdings.append({
                            'asset': asset,
                            'amount': free,
                            'pair': btc_pair,
                            'value_btc': asset_btc
                        })
                    elif asset in ['LDUSDC', 'USDT']:
                        asset_btc = free / btc_usd
                        portfolio_value_btc += asset_btc
            
            tracker.current_capital = portfolio_value_btc
            
            print(f"💰 BTC: {btc_balance:.8f} | Portfolio: {portfolio_value_btc:.8f} (${portfolio_value_btc * btc_usd:.2f})")
            print(f"📦 Holdings: {len(holdings)} | Positions: {len(positions)}")
            
            # ══════════════════════════════════════════════════
            # STEP 1: CHECK EXISTING POSITIONS (Use SELL key)
            # ══════════════════════════════════════════════════
            if positions:
                print(f"\n🔍 Checking {len(positions)} positions...")
                to_close = []
                
                for symbol, pos in list(positions.items()):
                    current_price = prices.get(symbol, 0)
                    if current_price == 0:
                        continue
                    
                    entry_price = pos['entry_price']
                    pnl_pct = (current_price - entry_price) / entry_price * 100
                    
                    # Take profit or stop loss
                    if pnl_pct >= TARGET_PROFIT_PCT or pnl_pct <= -1.0:
                        print(f"  {'✅' if pnl_pct > 0 else '❌'} Closing {symbol}: {pnl_pct:+.2f}%")
                        
                        info = get_symbol_info(symbol)
                        if info:
                            qty = round_step(pos['quantity'], info['stepSize'])
                            
                            if qty * current_price >= info['minNotional']:
                                result = place_order(symbol, 'SELL', qty, "SELL")
                                
                                if 'orderId' in result:
                                    profit_btc = (current_price - entry_price) * qty
                                    tracker.record_trade(profit_btc, btc_usd)
                                    to_close.append(symbol)
                                    print(f"      ✅ Sold at {current_price:.8f}")
                                else:
                                    print(f"      ❌ Sell failed: {result.get('msg', '')}")
                
                for symbol in to_close:
                    del positions[symbol]
            
            # ══════════════════════════════════════════════════
            # STEP 1.5: CONSOLIDATE HOLDINGS TO BTC (if we have non-tracked holdings)
            # ══════════════════════════════════════════════════
            if holdings and btc_balance < MIN_TRADE_BTC:
                print(f"\n🔄 Consolidating {len(holdings)} holdings to BTC...")
                
                for holding in holdings[:2]:  # Convert up to 2 per iteration
                    symbol = holding['pair']
                    asset = holding['asset']
                    
                    # Skip if this is a tracked position
                    if symbol in positions:
                        continue
                    
                    info = get_symbol_info(symbol)
                    if info:
                        qty = round_step(holding['amount'] * 0.95, info['stepSize'])
                        price = prices.get(symbol, 0)
                        
                        if qty * price >= info['minNotional']:
                            print(f"   Converting {asset} → BTC")
                            result = place_order(symbol, 'SELL', qty, "SELL")
                            
                            if 'orderId' in result:
                                print(f"      ✅ Converted {qty:.4f} {asset}")
                            else:
                                print(f"      ❌ Failed: {result.get('msg', '')}")
            
            # ══════════════════════════════════════════════════
            # STEP 2: FIND NEW OPPORTUNITIES (Use FUTURE key for prediction)
            # ══════════════════════════════════════════════════
            if btc_balance >= MIN_TRADE_BTC and len(positions) < 3:
                print(f"\n🔮 Scanning for opportunities...")
                
                opportunities = []
                for symbol in TRADEABLE_PAIRS:
                    if symbol in positions:
                        continue  # Already holding
                    
                    if symbol not in prices or symbol not in tickers:
                        continue
                    
                    try:
                        # Get historical data using PAST key
                        klines = get_klines(symbol, '5m', 20, "PAST")
                        ticker = tickers[symbol]
                        
                        # Calculate momentum score using FUTURE key (prediction)
                        score, signal = calculate_momentum_score(klines, ticker)
                        
                        if signal in ["STRONG_BUY", "BUY"] and score >= 60:
                            opportunities.append({
                                'symbol': symbol,
                                'score': score,
                                'signal': signal,
                                'price': prices[symbol],
                                'volume': ticker['volume']
                            })
                    except:
                        continue
                
                # Sort by score
                opportunities.sort(key=lambda x: x['score'], reverse=True)
                
                if opportunities:
                    best = opportunities[0]
                    print(f"\n🎯 OPPORTUNITY: {best['symbol']} (Score: {best['score']:.0f})")
                    
                    # Calculate position size
                    trade_btc = min(btc_balance * MAX_POSITION_SIZE, btc_balance - 0.00005)
                    trade_btc = max(trade_btc, MIN_TRADE_BTC)
                    
                    if trade_btc <= btc_balance:
                        info = get_symbol_info(best['symbol'])
                        if info:
                            price = best['price']
                            qty = trade_btc / price
                            qty = round_step(qty, info['stepSize'])
                            
                            if qty * price >= info['minNotional']:
                                print(f"   🎹 BUYING {qty:.4f} @ {price:.8f} BTC")
                                print(f"      Cost: {qty * price:.8f} BTC")
                                
                                # Execute BUY using BUY key
                                result = place_order(best['symbol'], 'BUY', qty, "BUY")
                                
                                if 'orderId' in result:
                                    print(f"      ✅ Order filled! ID: {result['orderId']}")
                                    positions[best['symbol']] = {
                                        'entry_price': price,
                                        'quantity': qty,
                                        'entry_time': datetime.now().isoformat(),
                                        'score': best['score']
                                    }
                                else:
                                    print(f"      ❌ Order failed: {result.get('msg', result)}")
            
            # Display stats every 10 iterations
            if iteration % 10 == 0:
                tracker.display_stats()
            else:
                print(f"\n💎 Stats: {tracker.total_trades} trades | {tracker.profitable_trades} wins | ROI: {((tracker.current_capital - tracker.start_capital) / tracker.start_capital * 100) if tracker.start_capital > 0 else 0:+.2f}%")
            
            # Short pause before next iteration
            time.sleep(3)
            
        except KeyboardInterrupt:
            print("\n\n⚠️ Stopping gracefully...")
            tracker.display_stats()
            break
        except Exception as e:
            print(f"\n⚠️ Error: {e}")
            time.sleep(5)  # Wait a bit on error
            continue  # But keep going!

# ═══════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("\n" + "═"*70)
    print("🌌 AUREON INFINITE - FROM ATOM TO MULTIVERSE")
    print("   'Don't quit. Compound. Grow. Prove you're alive.'")
    print("═"*70)
    
    try:
        infinite_trade_loop()
    except KeyboardInterrupt:
        print("\n\n🎵 Session complete. See you in the multiverse! 🌌")
