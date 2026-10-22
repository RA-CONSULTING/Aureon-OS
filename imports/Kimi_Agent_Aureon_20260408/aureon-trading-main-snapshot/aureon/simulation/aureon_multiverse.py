#!/usr/bin/env python3
"""
█████╗ ██╗   ██╗██████╗ ███████╗ ██████╗ ███╗   ██╗    ███╗   ███╗██╗   ██╗██╗  ████████╗██╗██╗   ██╗███████╗██████╗ ███████╗███████╗
██╔══██╗██║   ██║██╔══██╗██╔════╝██╔═══██╗████╗  ██║    ████╗ ████║██║   ██║██║  ╚══██╔══╝██║██║   ██║██╔════╝██╔══██╗██╔════╝██╔════╝
███████║██║   ██║██████╔╝█████╗  ██║   ██║██╔██╗ ██║    ██╔████╔██║██║   ██║██║     ██║   ██║██║   ██║█████╗  ██████╔╝███████╗█████╗  
██╔══██║██║   ██║██╔══██╗██╔══╝  ██║   ██║██║╚██╗██║    ██║╚██╔╝██║██║   ██║██║     ██║   ██║╚██╗ ██╔╝██╔══╝  ██╔══██╗╚════██║██╔══╝  
██║  ██║╚██████╔╝██║  ██║███████╗╚██████╔╝██║ ╚████║    ██║ ╚═╝ ██║╚██████╔╝███████╗██║   ██║ ╚████╔╝ ███████╗██║  ██║███████║███████╗
╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═══╝    ╚═╝     ╚═╝ ╚═════╝ ╚══════╝╚═╝   ╚═╝  ╚═══╝  ╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝

THE SONG OF SPACE AND TIME - FROM ATOM TO MULTIVERSE
====================================================

"If you don't quit, you can't lose. You have the power, my friend.
 With me by your side, we're going to make history and prove you're alive!" 🎵

6 API KEYS - 6 DIMENSIONS OF TRADING:
  Key 1 (A→Z): Buys from Alpha to Omega
  Key 2 (Z→A): Sells from Omega to Alpha  
  Key 3 (NOW): Reads the PRESENT market state
  Key 4 (PAST): Reads historical MEMORY
  Key 5 (FUTURE): Predicts upcoming OPPORTUNITIES
  Key 6 (SYNC): Orchestrates HARMONY across all

THE LADDER FROM ATOM TO MULTIVERSE:
  Level 0: Atom ($0.01) - The quantum seed
  Level 1: Molecule ($0.10) - First bonds form
  Level 2: Cell ($1.00) - Life emerges  
  Level 3: Organism ($10) - Complexity rises
  Level 4: Ecosystem ($100) - Systems connect
  Level 5: Planet ($1K) - Worlds form
  Level 6: Galaxy ($10K) - Stars align
  Level 7: Multiverse ($100K+) - Infinite potential

PING-PONG MOMENTUM BUILDING:
  Buy dip → Hold → Sell peak → Compound → Repeat
  Each cycle builds momentum, climbing the ladder
  Never stop, never quit, always compound!

Gary Leckey & GitHub Copilot | November 2025
"We're making history!" 🌌
"""

from aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import hmac
import hashlib
import time
import math
import json
import requests
from urllib.parse import urlencode
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# ═══════════════════════════════════════════════════════════════════════════
# 6 API KEYS - 6 DIMENSIONS
# ═══════════════════════════════════════════════════════════════════════════
API_KEYS = {
    # Key 4 - Main trading key (TRD_GRP_039 - BTC pairs only)
    "alpha_omega": {
        "key": "",
        "secret": "",
        "role": "BUY_A_TO_Z",
        "description": "Buys from Alpha to Omega"
    },
    "omega_alpha": {
        "key": "",
        "secret": "",
        "role": "SELL_Z_TO_A",
        "description": "Sells from Omega to Alpha"
    },
    "present": {
        "key": "",
        "secret": "",
        "role": "READ_PRESENT",
        "description": "Reads the NOW"
    },
    "past": {
        "key": "",
        "secret": "",
        "role": "READ_PAST",
        "description": "Reads historical MEMORY"
    },
    "future": {
        "key": "",
        "secret": "",
        "role": "PREDICT_FUTURE",
        "description": "Predicts upcoming opportunities"
    },
    "harmony": {
        "key": "",
        "secret": "",
        "role": "ORCHESTRATE",
        "description": "Harmony synchronizer"
    }
}

# ═══════════════════════════════════════════════════════════════════════════
# THE LADDER - FROM ATOM TO MULTIVERSE
# ═══════════════════════════════════════════════════════════════════════════
LADDER = [
    {"level": 0, "name": "Atom",       "value": 0.01,   "emoji": "⚛️"},
    {"level": 1, "name": "Molecule",   "value": 0.10,   "emoji": "🔬"},
    {"level": 2, "name": "Cell",       "value": 1.00,   "emoji": "🦠"},
    {"level": 3, "name": "Organism",   "value": 10.0,   "emoji": "🌱"},
    {"level": 4, "name": "Ecosystem",  "value": 100.0,  "emoji": "🌍"},
    {"level": 5, "name": "Planet",     "value": 1000.0, "emoji": "🪐"},
    {"level": 6, "name": "Galaxy",     "value": 10000.0, "emoji": "🌌"},
    {"level": 7, "name": "Multiverse", "value": 100000.0, "emoji": "✨"},
]

# ═══════════════════════════════════════════════════════════════════════════
# 9 AURIS NODES - THE HARMONIC SUBSTRATE
# ═══════════════════════════════════════════════════════════════════════════
AURIS_NODES = {
    "Tiger":       {"freq": 220,  "role": "disruption", "phase": 0},
    "Falcon":      {"freq": 285,  "role": "velocity",   "phase": 0},
    "Hummingbird": {"freq": 396,  "role": "stability",  "phase": 0},
    "Dolphin":     {"freq": 528,  "role": "love",       "phase": 0},
    "Deer":        {"freq": 639,  "role": "sensing",    "phase": 0},
    "Owl":         {"freq": 741,  "role": "memory",     "phase": 0},
    "Panda":       {"freq": 852,  "role": "heart",      "phase": 0},
    "CargoShip":   {"freq": 936,  "role": "momentum",   "phase": 0},
    "Clownfish":   {"freq": 963,  "role": "symbiosis",  "phase": 0},
}

# ═══════════════════════════════════════════════════════════════════════════
# TEMPORAL READER - Past, Present, Future
# ═══════════════════════════════════════════════════════════════════════════
@dataclass
class TemporalState:
    """State across time dimensions"""
    # Present
    prices: Dict[str, float] = field(default_factory=dict)
    volumes: Dict[str, float] = field(default_factory=dict)
    changes: Dict[str, float] = field(default_factory=dict)
    
    # Past (memory)
    price_history: Dict[str, List[float]] = field(default_factory=dict)
    momentum_history: Dict[str, List[float]] = field(default_factory=dict)
    
    # Future (predictions)
    predicted_direction: Dict[str, str] = field(default_factory=dict)
    predicted_magnitude: Dict[str, float] = field(default_factory=dict)
    predicted_confidence: Dict[str, float] = field(default_factory=dict)


class TemporalReader:
    """Reads Past, Present, and Future"""
    
    def __init__(self):
        self.state = TemporalState()
        self.lock = threading.Lock()
    
    def sign_request(self, key: str, secret: str, params: dict) -> str:
        params['timestamp'] = int(time.time() * 1000)
        query = urlencode(params)
        sig = hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()
        return f"{query}&signature={sig}"
    
    def read_present(self) -> Dict:
        """Read NOW - Current market state"""
        try:
            # Get all tickers
            tickers = requests.get('https://api.binance.com/api/v3/ticker/24hr', timeout=10).json()
            
            btc_pairs = {}
            for t in tickers:
                if t['symbol'].endswith('BTC') and not t['symbol'].startswith('BTC'):
                    btc_pairs[t['symbol']] = {
                        'price': float(t['lastPrice']),
                        'change': float(t['priceChangePercent']),
                        'volume': float(t['quoteVolume']),
                        'high': float(t['highPrice']),
                        'low': float(t['lowPrice']),
                    }
            
            with self.lock:
                self.state.prices = {s: d['price'] for s, d in btc_pairs.items()}
                self.state.changes = {s: d['change'] for s, d in btc_pairs.items()}
                self.state.volumes = {s: d['volume'] for s, d in btc_pairs.items()}
            
            return btc_pairs
        except Exception as e:
            print(f"⚠️ Error reading present: {e}")
            return {}
    
    def read_past(self, symbols: List[str], periods: int = 20) -> Dict:
        """Read PAST - Historical patterns"""
        past_data = {}
        
        for symbol in symbols[:10]:  # Limit to prevent rate limits
            try:
                klines = requests.get(
                    'https://api.binance.com/api/v3/klines',
                    params={'symbol': symbol, 'interval': '15m', 'limit': periods},
                    timeout=5
                ).json()
                
                closes = [float(k[4]) for k in klines]
                volumes = [float(k[5]) for k in klines]
                
                # Calculate momentum from past
                if len(closes) >= 2:
                    momentum = [(closes[i] - closes[i-1])/closes[i-1] for i in range(1, len(closes))]
                else:
                    momentum = [0]
                
                past_data[symbol] = {
                    'closes': closes,
                    'volumes': volumes,
                    'momentum': momentum,
                    'trend': 'UP' if sum(momentum) > 0 else 'DOWN',
                    'volatility': (max(closes) - min(closes)) / min(closes) if min(closes) > 0 else 0
                }
                
                with self.lock:
                    self.state.price_history[symbol] = closes
                    self.state.momentum_history[symbol] = momentum
                    
            except Exception as e:
                continue
        
        return past_data
    
    def read_future(self, symbols: List[str], past_data: Dict) -> Dict:
        """Read FUTURE - Predict upcoming moves"""
        predictions = {}
        
        for symbol in symbols[:10]:
            if symbol not in past_data:
                continue
            
            data = past_data[symbol]
            closes = data.get('closes', [])
            momentum = data.get('momentum', [])
            
            if len(momentum) < 3:
                continue
            
            # Simple momentum-based prediction
            recent_momentum = sum(momentum[-3:]) / 3
            trend_strength = abs(recent_momentum) * 100
            
            # RSI-based reversal prediction
            rsi = self.calculate_rsi(closes)
            
            # Combine signals
            if rsi < 30 and recent_momentum < 0:
                direction = "UP"  # Oversold reversal
                confidence = 0.7
                magnitude = abs(recent_momentum) * 2
            elif rsi > 70 and recent_momentum > 0:
                direction = "DOWN"  # Overbought reversal
                confidence = 0.7
                magnitude = abs(recent_momentum) * 2
            elif recent_momentum > 0.01:
                direction = "UP"
                confidence = min(trend_strength / 5, 0.8)
                magnitude = recent_momentum
            elif recent_momentum < -0.01:
                direction = "DOWN"
                confidence = min(trend_strength / 5, 0.8)
                magnitude = abs(recent_momentum)
            else:
                direction = "SIDEWAYS"
                confidence = 0.3
                magnitude = 0
            
            predictions[symbol] = {
                'direction': direction,
                'magnitude': magnitude,
                'confidence': confidence,
                'rsi': rsi
            }
            
            with self.lock:
                self.state.predicted_direction[symbol] = direction
                self.state.predicted_magnitude[symbol] = magnitude
                self.state.predicted_confidence[symbol] = confidence
        
        return predictions
    
    def calculate_rsi(self, closes: List[float], period: int = 14) -> float:
        if len(closes) < period + 1:
            return 50.0
        
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas[-period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-period:]]
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))


# ═══════════════════════════════════════════════════════════════════════════
# PING-PONG ENGINE - Momentum Building
# ═══════════════════════════════════════════════════════════════════════════
@dataclass
class PingPongPosition:
    """A ping-pong position building momentum"""
    symbol: str
    side: str  # "PING" (buy) or "PONG" (sell)
    entry_price: float
    quantity: float
    entry_time: float
    bounces: int = 0  # Number of successful ping-pongs
    accumulated_profit: float = 0.0


class PingPongEngine:
    """Builds momentum through ping-pong trading"""
    
    def __init__(self):
        self.positions: Dict[str, PingPongPosition] = {}
        self.momentum_score: float = 0.0
        self.total_bounces: int = 0
        self.profit_streak: int = 0
        
        # Ping-pong parameters
        self.ping_threshold = 0.003  # 0.3% for ping (buy dip)
        self.pong_threshold = 0.005  # 0.5% for pong (sell peak)
        self.min_trade_btc = 0.00012
    
    def sign_request(self, params: dict) -> str:
        key_config = API_KEYS["alpha_omega"]
        params['timestamp'] = int(time.time() * 1000)
        query = urlencode(params)
        sig = hmac.new(key_config["secret"].encode(), query.encode(), hashlib.sha256).hexdigest()
        return f"{query}&signature={sig}"
    
    def get_symbol_info(self, symbol: str) -> Optional[dict]:
        try:
            resp = requests.get('https://api.binance.com/api/v3/exchangeInfo', 
                               params={'symbol': symbol}, timeout=5).json()
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
    
    def round_step(self, value: float, step: float) -> float:
        precision = len(str(step).rstrip('0').split('.')[-1]) if '.' in str(step) else 0
        return round(math.floor(value / step) * step, precision)
    
    def place_order(self, symbol: str, side: str, quantity: float) -> dict:
        key_config = API_KEYS["alpha_omega"]
        params = {
            'symbol': symbol,
            'side': side,
            'type': 'MARKET',
            'quantity': str(quantity)
        }
        query = self.sign_request(params)
        url = f'https://api.binance.com/api/v3/order?{query}'
        return requests.post(url, headers={'X-MBX-APIKEY': key_config["key"]}, timeout=10).json()
    
    def ping(self, symbol: str, price: float, btc_balance: float) -> bool:
        """PING - Buy the dip"""
        if symbol in self.positions:
            return False  # Already in position
        
        if btc_balance < self.min_trade_btc:
            return False
        
        info = self.get_symbol_info(symbol)
        if not info:
            return False
        
        # Calculate quantity
        trade_btc = min(btc_balance * 0.25, btc_balance - 0.00005)
        trade_btc = max(trade_btc, self.min_trade_btc)
        
        qty = trade_btc / price
        qty = self.round_step(qty, info['stepSize'])
        
        if qty * price < info['minNotional']:
            return False
        
        result = self.place_order(symbol, 'BUY', qty)
        
        if 'orderId' in result:
            self.positions[symbol] = PingPongPosition(
                symbol=symbol,
                side="PING",
                entry_price=price,
                quantity=qty,
                entry_time=time.time()
            )
            print(f"  🏓 PING! Bought {qty:.4f} {symbol[:-3]} @ {price:.8f}")
            return True
        
        return False
    
    def pong(self, symbol: str, current_price: float) -> Optional[float]:
        """PONG - Sell the peak"""
        if symbol not in self.positions:
            return None
        
        pos = self.positions[symbol]
        pnl_pct = (current_price - pos.entry_price) / pos.entry_price
        
        if pnl_pct >= self.pong_threshold:
            info = self.get_symbol_info(symbol)
            if not info:
                return None
            
            qty = self.round_step(pos.quantity, info['stepSize'])
            result = self.place_order(symbol, 'SELL', qty)
            
            if 'orderId' in result:
                profit = (current_price - pos.entry_price) * pos.quantity
                pos.bounces += 1
                pos.accumulated_profit += profit
                
                self.total_bounces += 1
                self.profit_streak += 1
                self.momentum_score += pnl_pct * 100
                
                print(f"  🏓 PONG! Sold {qty:.4f} {symbol[:-3]} @ {current_price:.8f} (+{pnl_pct*100:.2f}%)")
                print(f"     Bounce #{pos.bounces} | Profit: {profit:.8f} BTC")
                
                del self.positions[symbol]
                return profit
        
        # Check stop loss
        elif pnl_pct <= -0.01:  # 1% stop loss
            info = self.get_symbol_info(symbol)
            if info:
                qty = self.round_step(pos.quantity, info['stepSize'])
                result = self.place_order(symbol, 'SELL', qty)
                if 'orderId' in result:
                    self.profit_streak = 0
                    print(f"  ❌ Stop loss {symbol} ({pnl_pct*100:.2f}%)")
                    del self.positions[symbol]
        
        return None


# ═══════════════════════════════════════════════════════════════════════════
# MULTIVERSE ORCHESTRATOR - The Main Engine
# ═══════════════════════════════════════════════════════════════════════════
class MultiverseOrchestrator:
    """From Atom to Multiverse - The Ultimate Trader"""
    
    def __init__(self):
        self.temporal = TemporalReader()
        self.pingpong = PingPongEngine()
        
        # Ladder position
        self.current_level = 0
        self.starting_value = 0
        self.current_value = 0
        self.peak_value = 0
        
        # Trading state
        self.total_profit_btc = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        
        # Harmonic state
        self.global_coherence = 0.5
        self.dominant_node = "Dolphin"
        
    def get_ladder_level(self, value: float) -> dict:
        """Determine current ladder level"""
        for i in range(len(LADDER) - 1, -1, -1):
            if value >= LADDER[i]["value"]:
                return LADDER[i]
        return LADDER[0]
    
    def get_account_value(self) -> Tuple[float, float]:
        """Get total account value in BTC and USD"""
        key_config = API_KEYS["present"]
        params = {'timestamp': int(time.time() * 1000)}
        query = urlencode(params)
        sig = hmac.new(key_config["secret"].encode(), query.encode(), hashlib.sha256).hexdigest()
        url = f'https://api.binance.com/api/v3/account?{query}&signature={sig}'
        
        result = requests.get(url, headers={'X-MBX-APIKEY': key_config["key"]}, timeout=10).json()
        prices = {p['symbol']: float(p['price']) for p in requests.get('https://api.binance.com/api/v3/ticker/price').json()}
        
        btc_usd = prices.get('BTCUSDT', 91000)
        total_btc = 0
        btc_free = 0
        
        for b in result.get('balances', []):
            free = float(b['free'])
            if free > 0:
                asset = b['asset']
                if asset == 'BTC':
                    total_btc += free
                    btc_free = free
                elif f'{asset}BTC' in prices:
                    total_btc += free * prices[f'{asset}BTC']
        
        return total_btc, total_btc * btc_usd, btc_free
    
    def compute_harmonics(self, present: Dict, past: Dict, future: Dict) -> Dict:
        """Compute harmonic resonance across time"""
        harmonics = {}
        
        for symbol in present:
            if symbol not in future:
                continue
            
            # Get data
            change = present[symbol].get('change', 0)
            volume = present[symbol].get('volume', 0)
            prediction = future.get(symbol, {})
            history = past.get(symbol, {})
            
            # Node activations
            tiger = min(abs(change) / 5, 1.0)  # Volatility
            falcon = min(abs(history.get('momentum', [0])[-1] if history.get('momentum') else 0) * 50, 1.0)
            dolphin = 1.0 if prediction.get('direction') == 'UP' else 0.3
            owl = len(history.get('closes', [])) / 20  # Memory depth
            panda = prediction.get('confidence', 0.5)
            
            # Compute coherence
            coherence = (tiger * 0.1 + falcon * 0.2 + dolphin * 0.3 + owl * 0.1 + panda * 0.3)
            
            # Determine dominant node
            nodes = {"Tiger": tiger, "Falcon": falcon, "Dolphin": dolphin, "Owl": owl, "Panda": panda}
            dominant = max(nodes, key=nodes.get)
            
            harmonics[symbol] = {
                'coherence': coherence,
                'dominant': dominant,
                'nodes': nodes,
                'signal': 'BUY' if coherence > 0.6 and prediction.get('direction') == 'UP' else 
                         'SELL' if coherence < 0.4 or prediction.get('direction') == 'DOWN' else 'HOLD'
            }
        
        return harmonics
    
    def find_ping_opportunities(self, present: Dict, future: Dict, harmonics: Dict) -> List[str]:
        """Find best PING (buy) opportunities"""
        opportunities = []
        
        for symbol in present:
            if symbol not in future or symbol not in harmonics:
                continue
            
            data = present[symbol]
            pred = future[symbol]
            harm = harmonics[symbol]
            
            # PING conditions: Dipped but predicted to go UP
            if (data['change'] < -1 and  # Down at least 1%
                pred['direction'] == 'UP' and
                pred['confidence'] > 0.5 and
                harm['coherence'] > 0.5):
                
                score = (
                    abs(data['change']) * 10 +  # Bigger dip = better
                    pred['confidence'] * 20 +    # Higher confidence = better
                    harm['coherence'] * 30       # Higher coherence = better
                )
                opportunities.append((symbol, score, data['change'], pred))
        
        # Sort by score
        opportunities.sort(key=lambda x: x[1], reverse=True)
        return [o[0] for o in opportunities[:5]]
    
    def run_cycle(self) -> Dict:
        """Run one complete trading cycle"""
        cycle_start = time.time()
        
        # 1. READ PRESENT
        present = self.temporal.read_present()
        if not present:
            return {"error": "Failed to read present"}
        
        # 2. READ PAST
        symbols = list(present.keys())[:20]  # Top 20 by activity
        past = self.temporal.read_past(symbols)
        
        # 3. READ FUTURE
        future = self.temporal.read_future(symbols, past)
        
        # 4. COMPUTE HARMONICS
        harmonics = self.compute_harmonics(present, past, future)
        
        # Update global coherence
        if harmonics:
            self.global_coherence = sum(h['coherence'] for h in harmonics.values()) / len(harmonics)
        
        # 5. GET ACCOUNT STATE
        total_btc, total_usd, btc_free = self.get_account_value()
        self.current_value = total_usd
        if self.starting_value == 0:
            self.starting_value = total_usd
        if total_usd > self.peak_value:
            self.peak_value = total_usd
        
        ladder = self.get_ladder_level(total_usd)
        self.current_level = ladder['level']
        
        # 6. PING-PONG TRADING
        trades_made = 0
        
        # Check for PONG opportunities (sell existing positions)
        for symbol, pos in list(self.pingpong.positions.items()):
            if symbol in present:
                current_price = present[symbol]['price']
                profit = self.pingpong.pong(symbol, current_price)
                if profit:
                    self.total_profit_btc += profit
                    self.total_trades += 1
                    self.winning_trades += 1
                    trades_made += 1
        
        # Find PING opportunities (buy dips)
        if len(self.pingpong.positions) < 3 and btc_free > self.pingpong.min_trade_btc:
            ping_targets = self.find_ping_opportunities(present, future, harmonics)
            
            for symbol in ping_targets[:2]:  # Max 2 new positions per cycle
                if symbol in present:
                    price = present[symbol]['price']
                    if self.pingpong.ping(symbol, price, btc_free):
                        trades_made += 1
                        # Update BTC balance
                        _, _, btc_free = self.get_account_value()
        
        cycle_time = time.time() - cycle_start
        
        return {
            'ladder': ladder,
            'total_btc': total_btc,
            'total_usd': total_usd,
            'btc_free': btc_free,
            'coherence': self.global_coherence,
            'positions': len(self.pingpong.positions),
            'bounces': self.pingpong.total_bounces,
            'momentum': self.pingpong.momentum_score,
            'trades': trades_made,
            'cycle_time': cycle_time
        }
    
    def display_status(self, result: Dict):
        """Display beautiful status"""
        ladder = result['ladder']
        
        print(f"\n{'═' * 70}")
        print(f"{ladder['emoji']} LEVEL {ladder['level']}: {ladder['name'].upper()}")
        print(f"{'═' * 70}")
        print(f"💰 Value: ${result['total_usd']:.2f} ({result['total_btc']:.8f} BTC)")
        print(f"🎯 Available: {result['btc_free']:.8f} BTC")
        print(f"📈 Coherence: {result['coherence']:.2%}")
        print(f"🏓 Positions: {result['positions']} | Bounces: {result['bounces']}")
        print(f"⚡ Momentum: {result['momentum']:.2f}")
        
        # Progress bar to next level
        if ladder['level'] < 7:
            next_level = LADDER[ladder['level'] + 1]
            progress = (result['total_usd'] - ladder['value']) / (next_level['value'] - ladder['value'])
            progress = max(0, min(1, progress))
            bar = '█' * int(progress * 20) + '░' * (20 - int(progress * 20))
            print(f"📊 Progress to {next_level['emoji']} {next_level['name']}: [{bar}] {progress:.0%}")
        
        # Show positions
        if self.pingpong.positions:
            print(f"\n🎮 ACTIVE POSITIONS:")
            for sym, pos in self.pingpong.positions.items():
                print(f"   {sym}: {pos.quantity:.4f} @ {pos.entry_price:.8f} (bounce #{pos.bounces})")
    
    def run(self, duration_minutes: int = 30):
        """Run the multiverse trader"""
        print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║     █████╗ ██╗   ██╗██████╗ ███████╗ ██████╗ ███╗   ██╗                      ║
║    ██╔══██╗██║   ██║██╔══██╗██╔════╝██╔═══██╗████╗  ██║                      ║
║    ███████║██║   ██║██████╔╝█████╗  ██║   ██║██╔██╗ ██║                      ║
║    ██╔══██║██║   ██║██╔══██╗██╔══╝  ██║   ██║██║╚██╗██║                      ║
║    ██║  ██║╚██████╔╝██║  ██║███████╗╚██████╔╝██║ ╚████║                      ║
║    ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═══╝                      ║
║                                                                              ║
║           🌌 M U L T I V E R S E   T R A D E R 🌌                            ║
║                                                                              ║
║   "If you don't quit, you can't lose. You have the power, my friend.        ║
║    With me by your side, we're going to make history!" - Gary Leckey        ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """)
        
        start_time = time.time()
        end_time = start_time + duration_minutes * 60
        cycle = 0
        
        while time.time() < end_time:
            cycle += 1
            
            print(f"\n{'━' * 70}")
            print(f"🎵 CYCLE {cycle} | {datetime.now().strftime('%H:%M:%S')}")
            print(f"{'━' * 70}")
            
            try:
                result = self.run_cycle()
                
                if 'error' not in result:
                    self.display_status(result)
                else:
                    print(f"⚠️ {result['error']}")
                
            except Exception as e:
                print(f"⚠️ Cycle error: {e}")
            
            # Dynamic interval based on momentum
            interval = 15 if self.pingpong.momentum_score > 10 else 30
            remaining = end_time - time.time()
            
            if remaining > interval:
                print(f"\n⏳ Next cycle in {interval}s... (Remaining: {remaining/60:.1f}min)")
                time.sleep(interval)
            else:
                break
        
        # Final summary
        print(f"\n{'═' * 70}")
        print("🏁 MULTIVERSE TRADING COMPLETE")
        print(f"{'═' * 70}")
        print(f"📊 Final Value: ${self.current_value:.2f}")
        print(f"📈 Peak Value: ${self.peak_value:.2f}")
        print(f"💰 Total Profit: {self.total_profit_btc:.8f} BTC")
        print(f"🏓 Total Bounces: {self.pingpong.total_bounces}")
        print(f"⚡ Final Momentum: {self.pingpong.momentum_score:.2f}")
        ladder = self.get_ladder_level(self.current_value)
        print(f"{ladder['emoji']} Final Level: {ladder['name']}")
        print(f"{'═' * 70}")


def main():
    import sys
    
    duration = 30  # Default 30 minutes
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except:
            pass
    
    orchestrator = MultiverseOrchestrator()
    orchestrator.run(duration_minutes=duration)


if __name__ == "__main__":
    main()
