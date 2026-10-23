#!/usr/bin/env python3
"""
AUREON LIVE TRADER - Active Trading System
==========================================
Trades BTC pairs using AUREON signals with proper position management.
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import hmac
import hashlib
import time
import requests
from urllib.parse import urlencode
from datetime import datetime
import json
import math

# 🧠 MINER BRAIN INTEGRATION
try:
    from aureon.utils.aureon_miner_brain import MinerBrain
    BRAIN_AVAILABLE = True
except ImportError:
    BRAIN_AVAILABLE = False
    print("⚠️ Miner Brain not available")

# API Configuration
API_KEY = ''
API_SECRET = ''

# Trading Parameters
MIN_TRADE_BTC = 0.00012       # Minimum trade size (~$11)
MAX_TRADE_PCT = 0.25          # Max 25% of BTC per trade
TARGET_PROFIT_PCT = 0.5       # Take profit at 0.5%
STOP_LOSS_PCT = 1.0           # Stop loss at 1%
MAX_POSITIONS = 3             # Max concurrent positions

# Track open positions
POSITIONS_FILE = '/workspaces/aureon-trading/positions.json'

def sign_request(params):
    """Sign a Binance API request"""
    params['timestamp'] = int(time.time() * 1000)
    query = urlencode(params)
    sig = hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
    return f"{query}&signature={sig}"

def get_account():
    """Get account balances"""
    query = sign_request({})
    url = f'https://api.binance.com/api/v3/account?{query}'
    return requests.get(url, headers={'X-MBX-APIKEY': API_KEY}).json()

def get_prices():
    """Get all current prices"""
    resp = requests.get('https://api.binance.com/api/v3/ticker/price').json()
    return {p['symbol']: float(p['price']) for p in resp}

def get_24h_changes():
    """Get 24h price changes"""
    resp = requests.get('https://api.binance.com/api/v3/ticker/24hr').json()
    return {t['symbol']: {
        'change': float(t['priceChangePercent']),
        'volume': float(t['quoteVolume']),
        'high': float(t['highPrice']),
        'low': float(t['lowPrice']),
        'last': float(t['lastPrice'])
    } for t in resp}

def get_klines(symbol, interval='15m', limit=20):
    """Get candlestick data"""
    resp = requests.get(
        f'https://api.binance.com/api/v3/klines',
        params={'symbol': symbol, 'interval': interval, 'limit': limit}
    ).json()
    return [{
        'open': float(k[1]),
        'high': float(k[2]),
        'low': float(k[3]),
        'close': float(k[4]),
        'volume': float(k[5])
    } for k in resp]

def get_symbol_info(symbol):
    """Get trading rules for a symbol"""
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
                'tickSize': float(filters.get('PRICE_FILTER', {}).get('tickSize', 0.00000001))
            }
    return None

def round_step(value, step):
    """Round value to step size"""
    precision = len(str(step).rstrip('0').split('.')[-1]) if '.' in str(step) else 0
    return round(math.floor(value / step) * step, precision)

def place_order(symbol, side, quantity):
    """Place a market order"""
    params = {
        'symbol': symbol,
        'side': side,
        'type': 'MARKET',
        'quantity': str(quantity)
    }
    query = sign_request(params)
    url = f'https://api.binance.com/api/v3/order?{query}'
    return requests.post(url, headers={'X-MBX-APIKEY': API_KEY}).json()

def calculate_rsi(closes, period=14):
    """Calculate RSI"""
    if len(closes) < period + 1:
        return 50
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas[-period:]]
    losses = [-d if d < 0 else 0 for d in deltas[-period:]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_momentum(prices, period=10):
    """Calculate price momentum"""
    if len(prices) < period:
        return 0
    return (prices[-1] - prices[-period]) / prices[-period] * 100

def load_positions():
    """Load open positions from file"""
    try:
        with open(POSITIONS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_positions(positions):
    """Save positions to file"""
    with open(POSITIONS_FILE, 'w') as f:
        json.dump(positions, f, indent=2)

def aureon_score(symbol, klines, ticker_24h):
    """Calculate AUREON trading score (0-100)"""
    if not klines or len(klines) < 15:
        return 0
    
    closes = [k['close'] for k in klines]
    volumes = [k['volume'] for k in klines]
    
    # Components
    rsi = calculate_rsi(closes)
    momentum = calculate_momentum(closes)
    
    # Volume surge
    avg_vol = sum(volumes[:-1]) / len(volumes[:-1]) if len(volumes) > 1 else volumes[0]
    vol_surge = volumes[-1] / avg_vol if avg_vol > 0 else 1
    
    # 24h change
    change_24h = ticker_24h.get('change', 0)
    
    # Scoring
    score = 50  # Base score
    
    # RSI scoring (oversold = bullish)
    if rsi < 30:
        score += 20
    elif rsi < 40:
        score += 10
    elif rsi > 70:
        score -= 15
    
    # Momentum scoring
    if momentum > 2:
        score += 15
    elif momentum > 0.5:
        score += 8
    elif momentum < -2:
        score -= 10
    
    # Volume surge scoring
    if vol_surge > 2:
        score += 15
    elif vol_surge > 1.3:
        score += 8
    
    # 24h trend
    if 0 < change_24h < 3:
        score += 10  # Mild uptrend good
    elif change_24h > 5:
        score -= 5   # Too hot
    elif change_24h < -5:
        score += 5   # Possible reversal
    
    return max(0, min(100, score))

def find_opportunities(prices, tickers, btc_balance):
    """Find trading opportunities"""
    opportunities = []
    
    # Top BTC pairs to scan
    TOP_PAIRS = [
        'SOLBTC', 'ETHBTC', 'XRPBTC', 'DOGEBTC', 'ADABTC', 
        'AVAXBTC', 'DOTBTC', 'LINKBTC', 'MATICBTC', 'LTCBTC',
        'ATOMBTC', 'UNIBTC', 'NEARBTC', 'APTBTC', 'OPBTC',
        'INJBTC', 'SUIBTC', 'SEIBTC', 'ARBBTC', 'TIAABTC'
    ]
    
    for symbol in TOP_PAIRS:
        if symbol not in prices:
            continue
        
        try:
            klines = get_klines(symbol, '15m', 20)
            ticker = tickers.get(symbol, {})
            
            score = aureon_score(symbol, klines, ticker)
            
            if score >= 60:
                opportunities.append({
                    'symbol': symbol,
                    'score': score,
                    'price': prices[symbol],
                    'change_24h': ticker.get('change', 0),
                    'volume': ticker.get('volume', 0)
                })
        except Exception as e:
            continue
    
    # Sort by score
    opportunities.sort(key=lambda x: x['score'], reverse=True)
    return opportunities

def check_positions(prices, btc_price):
    """Check and manage open positions"""
    positions = load_positions()
    closed = []
    
    for symbol, pos in positions.items():
        if symbol not in prices:
            continue
        
        current_price = prices[symbol]
        entry_price = pos['entry_price']
        pnl_pct = (current_price - entry_price) / entry_price * 100
        
        action = None
        reason = None
        
        # Check take profit
        if pnl_pct >= TARGET_PROFIT_PCT:
            action = 'SELL'
            reason = f'✅ TAKE PROFIT ({pnl_pct:.2f}%)'
        # Check stop loss
        elif pnl_pct <= -STOP_LOSS_PCT:
            action = 'SELL'
            reason = f'❌ STOP LOSS ({pnl_pct:.2f}%)'
        
        if action:
            # Get symbol info for proper quantity
            info = get_symbol_info(symbol)
            if not info:
                print(f"\n⚠️ Could not get info for {symbol}")
                continue
                
            qty = round_step(pos['quantity'], info['stepSize'])
            
            # Verify we have enough balance
            account = get_account()
            # MUST use endswith() — .replace() corrupts symbols like BTCB
            asset = symbol[:-3] if symbol.endswith('BTC') else symbol
            actual_balance = 0
            for b in account.get('balances', []):
                if b['asset'] == asset:
                    actual_balance = float(b['free'])
                    break
            
            if actual_balance < qty * 0.99:  # Allow 1% tolerance
                qty = round_step(actual_balance, info['stepSize'])
            
            if qty * current_price < info['minNotional']:
                print(f"\n⚠️ {symbol} below min notional, skipping close")
                continue
            
            result = place_order(symbol, 'SELL', qty)
            
            if 'orderId' in result:
                pnl_btc = (current_price - entry_price) * qty
                pnl_usd = pnl_btc * btc_price
                print(f"\n{reason}")
                print(f"   Sold {qty} {symbol[:-3]} at {current_price:.8f}")
                print(f"   P&L: {pnl_btc:.8f} BTC (${pnl_usd:.2f})")
                closed.append(symbol)
            else:
                print(f"\n⚠️ Failed to close {symbol}: {result}")
    
    # Remove closed positions
    for symbol in closed:
        del positions[symbol]
    save_positions(positions)
    
    return len(positions)

def run_trader():
    """Main trading loop"""
    print("\n" + "="*60)
    print("🚀 AUREON LIVE TRADER - Starting")
    print("="*60)
    
    # Initialize Brain
    brain = None
    if BRAIN_AVAILABLE:
        try:
            brain = MinerBrain()
            print("🧠 Miner Brain initialized and wired in!")
        except Exception as e:
            print(f"⚠️ Failed to start brain: {e}")

    cycle = 0
    
    while True:
        cycle += 1
        print(f"\n{'='*60}")
        print(f"📊 CYCLE {cycle} - {datetime.now().strftime('%H:%M:%S')}")
        print("="*60)
        
        # 🧠 BRAIN CYCLE
        brain_permission = True
        if brain and cycle % 2 == 1:  # Run brain every other cycle
            try:
                print("\n🧠 Consulting Miner Brain...")
                brain.run_cycle()
                pred = brain.get_latest_prediction()
                if pred:
                    print(f"   Brain says: {pred['direction']} (Conf: {pred['confidence']}%)")
                    if pred['direction'] == 'BEARISH' and pred['confidence'] > 70:
                        print("   🛑 Brain VETO: Market too bearish for longs")
                        brain_permission = False
                    
                    # Dream check
                    if hasattr(brain, 'dream_engine'):
                        # Pass default values: 0.0 change, 50 F&G
                        dream = brain.dream_engine.get_prepared_response(0.0, 50)
                        if dream:
                            print(f"   💭 Dream: {dream['action']}")
                            if dream['action'] in ['EXIT_NOW', 'WAIT_FOR_CLARITY']:
                                print("   🛑 Dream VETO: " + dream['reasoning'])
                                brain_permission = False
            except Exception as e:
                print(f"   ⚠️ Brain error: {e}")
        
        try:
            # Get current data
            prices = get_prices()
            tickers = get_24h_changes()
            account = get_account()
            
            btc_price = prices.get('BTCUSDT', 91000)
            
            # Find BTC balance
            btc_balance = 0
            for b in account.get('balances', []):
                if b['asset'] == 'BTC':
                    btc_balance = float(b['free'])
                    break
            
            print(f"\n💰 BTC Balance: {btc_balance:.8f} (${btc_balance * btc_price:.2f})")
            
            # Check existing positions
            positions = load_positions()
            open_count = check_positions(prices, btc_price)
            
            print(f"📈 Open Positions: {open_count}/{MAX_POSITIONS}")
            for sym, pos in positions.items():
                if sym in prices:
                    pnl = (prices[sym] - pos['entry_price']) / pos['entry_price'] * 100
                    print(f"   {sym}: {pos['quantity']} @ {pos['entry_price']:.8f} ({pnl:+.2f}%)")
            
            # Look for new opportunities if we have room
            if open_count < MAX_POSITIONS and btc_balance >= MIN_TRADE_BTC and brain_permission:
                print(f"\n🔍 Scanning for opportunities...")
                
                opportunities = find_opportunities(prices, tickers, btc_balance)
                
                # Filter out symbols we already hold
                opportunities = [o for o in opportunities if o['symbol'] not in positions]
                
                if opportunities:
                    print(f"\n🎯 Top Opportunities:")
                    for opp in opportunities[:5]:
                        print(f"   {opp['symbol']}: Score {opp['score']}, 24h: {opp['change_24h']:+.2f}%")
                    
                    # Take the top opportunity
                    best = opportunities[0]
                    if best['score'] >= 65:
                        symbol = best['symbol']
                        
                        # Calculate position size
                        trade_btc = min(btc_balance * MAX_TRADE_PCT, btc_balance - 0.00005)
                        trade_btc = max(trade_btc, MIN_TRADE_BTC)
                        
                        if trade_btc <= btc_balance:
                            info = get_symbol_info(symbol)
                            if info:
                                price = prices[symbol]
                                qty = trade_btc / price
                                qty = round_step(qty, info['stepSize'])
                                
                                # Check minimum notional
                                if qty * price >= info['minNotional']:
                                    print(f"\n🔥 BUYING {symbol}!")
                                    print(f"   Score: {best['score']}")
                                    print(f"   Qty: {qty} @ {price:.8f}")
                                    print(f"   Cost: {qty * price:.8f} BTC")
                                    
                                    result = place_order(symbol, 'BUY', qty)
                                    
                                    if 'orderId' in result:
                                        print(f"   ✅ Order filled!")
                                        
                                        # Record position
                                        positions[symbol] = {
                                            'quantity': qty,
                                            'entry_price': price,
                                            'entry_time': datetime.now().isoformat(),
                                            'score': best['score']
                                        }
                                        save_positions(positions)
                                    else:
                                        print(f"   ❌ Failed: {result}")
                else:
                    print("   No strong opportunities found")
            
            # Status summary
            positions = load_positions()
            total_position_value = 0
            for sym, pos in positions.items():
                if sym in prices:
                    total_position_value += pos['quantity'] * prices[sym]
            
            total_btc = btc_balance + total_position_value
            print(f"\n💎 Total Value: {total_btc:.8f} BTC (${total_btc * btc_price:.2f})")
            
        except Exception as e:
            print(f"\n⚠️ Error: {e}")
        
        # Wait before next cycle
        print(f"\n⏳ Next scan in 30 seconds...")
        time.sleep(30)

if __name__ == '__main__':
    run_trader()
