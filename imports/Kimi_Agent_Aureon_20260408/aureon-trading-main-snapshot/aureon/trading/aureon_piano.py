#!/usr/bin/env python3
"""
AUREON PIANO PLAYER 🎹
======================
"Playing the piano across all coins simultaneously"

Orchestrates the entire portfolio like piano keys:
- Each coin is a KEY with its own harmonic frequency
- The MASTER EQUATION Λ(t) = S(t) + O(t) + E(t) governs all
- Signals emerge from the SUBSTRATE (9 Auris nodes)
- Buy/Sell decisions come from HARMONIC RESONANCE

9 AURIS NODES (The Waveform):
  🐅 Tiger (220Hz) - Disruption/Volatility
  🦅 Falcon (285Hz) - Velocity/Momentum  
  🐦 Hummingbird (396Hz) - Stabilization
  🐬 Dolphin (528Hz) - Emotion/Social
  🦌 Deer (639Hz) - Sensing/Intuition
  🦉 Owl (741Hz) - Memory/Pattern
  🐼 Panda (852Hz) - Love/Balance
  🚢 CargoShip (936Hz) - Infrastructure
  🐠 Clownfish (963Hz) - Symbiosis/Ecosystem

RAINBOW BRIDGE STATES:
  FEAR (110Hz) → FORMING (285Hz) → RESONANCE (396Hz) →
  LOVE (528Hz) → AWE (852Hz) → UNITY (963Hz)

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
from dataclasses import dataclass

# ═══════════════════════════════════════════════════════════════
# API CONFIGURATION
# ═══════════════════════════════════════════════════════════════
API_KEY = ""
API_SECRET = ""

# ═══════════════════════════════════════════════════════════════
# 9 AURIS NODES - THE SUBSTRATE
# ═══════════════════════════════════════════════════════════════
AURIS_NODES = {
    "Tiger":       {"freq": 220, "role": "volatility", "weight": 1.0, "phase": 0},
    "Falcon":      {"freq": 285, "role": "momentum", "weight": 1.2, "phase": 0},
    "Hummingbird": {"freq": 396, "role": "stability", "weight": 0.8, "phase": 0},
    "Dolphin":     {"freq": 528, "role": "emotion", "weight": 1.5, "phase": 0},
    "Deer":        {"freq": 639, "role": "sensing", "weight": 0.9, "phase": 0},
    "Owl":         {"freq": 741, "role": "memory", "weight": 1.1, "phase": 0},
    "Panda":       {"freq": 852, "role": "love", "weight": 1.3, "phase": 0},
    "CargoShip":   {"freq": 936, "role": "infrastructure", "weight": 0.7, "phase": 0},
    "Clownfish":   {"freq": 963, "role": "symbiosis", "weight": 1.0, "phase": 0},
}

# Rainbow Bridge frequencies
RAINBOW_STATES = {
    "FEAR": 110,
    "FORMING": 285,
    "RESONANCE": 396,
    "LOVE": 528,
    "AWE": 852,
    "UNITY": 963
}

# ═══════════════════════════════════════════════════════════════
# PIANO KEY - Each coin as a tradeable instrument
# ═══════════════════════════════════════════════════════════════
@dataclass
class PianoKey:
    """A single piano key (coin) with its harmonic state"""
    asset: str
    btc_pair: str
    amount: float
    entry_price: float
    current_price: float
    
    # Harmonic state
    lambda_value: float = 0.0      # Λ(t) - Reality field
    substrate: float = 0.0         # S(t) - 9-node waveform
    observer: float = 0.0          # O(t) - Conscious focus
    echo: float = 0.0              # E(t) - Causal feedback
    coherence: float = 0.0         # Γ - Field coherence
    dominant_node: str = "Dolphin"
    rainbow_state: str = "FORMING"
    
    # Market metrics
    momentum: float = 0.0
    volatility: float = 0.0
    volume_ratio: float = 1.0
    rsi: float = 50.0
    
    # P&L
    pnl_pct: float = 0.0
    pnl_btc: float = 0.0
    
    def __post_init__(self):
        if self.entry_price > 0:
            self.pnl_pct = (self.current_price - self.entry_price) / self.entry_price * 100
            self.pnl_btc = (self.current_price - self.entry_price) * self.amount


class AureonPiano:
    """The Piano Player - Orchestrates all coins harmonically"""
    
    def __init__(self):
        self.keys: Dict[str, PianoKey] = {}
        self.t = 0.0  # Time
        self.dt = 1.0  # Time step (1 second)
        self.tau = 3.0  # Echo delay
        self.alpha = 1.2  # Observer coupling
        self.beta = 0.8  # Echo coupling
        
        # History for echo calculation
        self.lambda_history: List[float] = []
        self.max_history = 100
        
        # Field state
        self.global_coherence = 0.5
        self.global_lambda = 1.0
        self.global_rainbow = "FORMING"
        
        # Trade tracking
        self.positions_file = "/workspaces/aureon-trading/piano_positions.json"
        self.load_positions()
        
    def sign_request(self, params: dict) -> str:
        """Sign Binance API request"""
        params['timestamp'] = int(time.time() * 1000)
        query = urlencode(params)
        sig = hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
        return f"{query}&signature={sig}"
    
    def get_account(self) -> dict:
        """Get account balances"""
        query = self.sign_request({})
        url = f'https://api.binance.com/api/v3/account?{query}'
        return requests.get(url, headers={'X-MBX-APIKEY': API_KEY}).json()
    
    def get_prices(self) -> Dict[str, float]:
        """Get all current prices"""
        resp = requests.get('https://api.binance.com/api/v3/ticker/price').json()
        return {p['symbol']: float(p['price']) for p in resp}
    
    def get_24h_tickers(self) -> Dict[str, dict]:
        """Get 24h ticker data for all pairs"""
        resp = requests.get('https://api.binance.com/api/v3/ticker/24hr').json()
        return {t['symbol']: {
            'change': float(t['priceChangePercent']),
            'volume': float(t['quoteVolume']),
            'high': float(t['highPrice']),
            'low': float(t['lowPrice']),
        } for t in resp}
    
    def get_klines(self, symbol: str, interval: str = '15m', limit: int = 20) -> List[dict]:
        """Get candlestick data"""
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
    
    def load_positions(self):
        """Load tracked positions"""
        try:
            with open(self.positions_file, 'r') as f:
                self.tracked_positions = json.load(f)
        except:
            self.tracked_positions = {}
    
    def save_positions(self):
        """Save tracked positions"""
        with open(self.positions_file, 'w') as f:
            json.dump(self.tracked_positions, f, indent=2)
    
    # ═══════════════════════════════════════════════════════════
    # MASTER EQUATION: Λ(t) = S(t) + O(t) + E(t)
    # ═══════════════════════════════════════════════════════════
    
    def compute_substrate(self, key: PianoKey, klines: List[dict]) -> Tuple[float, str]:
        """
        S(t) = SUBSTRATE - The 9-node Auris waveform
        
        Each node responds to different market conditions:
        - Tiger: Volatility (price range)
        - Falcon: Momentum (price direction)
        - Hummingbird: Stability (low volatility = high signal)
        - Dolphin: Emotion (volume spikes)
        - Deer: Sensing (subtle changes)
        - Owl: Memory (pattern recognition)
        - Panda: Love (balance/equilibrium)
        - CargoShip: Infrastructure (sustained trends)
        - Clownfish: Symbiosis (correlation with ecosystem)
        """
        if not klines or len(klines) < 5:
            return 0.5, "Dolphin"
        
        closes = [k['close'] for k in klines]
        volumes = [k['volume'] for k in klines]
        highs = [k['high'] for k in klines]
        lows = [k['low'] for k in klines]
        
        # Market metrics
        price_change = (closes[-1] - closes[0]) / closes[0] if closes[0] > 0 else 0
        volatility = (max(closes) - min(closes)) / closes[0] if closes[0] > 0 else 0
        avg_volume = sum(volumes[:-1]) / len(volumes[:-1]) if len(volumes) > 1 else volumes[0]
        volume_spike = volumes[-1] / avg_volume if avg_volume > 0 else 1
        
        # Node activations
        node_values = {}
        
        # Tiger (Volatility) - High when market is wild
        tiger = min(volatility * 20, 1.0) * AURIS_NODES["Tiger"]["weight"]
        node_values["Tiger"] = tiger
        
        # Falcon (Momentum) - Direction and speed
        falcon = (0.5 + price_change * 10) * AURIS_NODES["Falcon"]["weight"]
        falcon = max(0, min(1, falcon))
        node_values["Falcon"] = falcon
        
        # Hummingbird (Stability) - Inverse of volatility
        hummingbird = max(0, 1 - volatility * 15) * AURIS_NODES["Hummingbird"]["weight"]
        node_values["Hummingbird"] = hummingbird
        
        # Dolphin (Emotion) - Volume spikes = emotion
        dolphin = min(volume_spike / 2, 1.0) * AURIS_NODES["Dolphin"]["weight"]
        node_values["Dolphin"] = dolphin
        
        # Deer (Sensing) - Subtle price nudges
        recent_change = (closes[-1] - closes[-3]) / closes[-3] if len(closes) >= 3 else 0
        deer = (0.5 + recent_change * 50) * AURIS_NODES["Deer"]["weight"]
        deer = max(0, min(1, deer))
        node_values["Deer"] = deer
        
        # Owl (Memory) - Pattern detection (higher lows = bullish memory)
        if len(lows) >= 5:
            higher_lows = sum(1 for i in range(1, len(lows)) if lows[i] > lows[i-1])
            owl = (higher_lows / (len(lows) - 1)) * AURIS_NODES["Owl"]["weight"]
        else:
            owl = 0.5
        node_values["Owl"] = owl
        
        # Panda (Love/Balance) - Equilibrium near middle of range
        mid_range = (max(closes) + min(closes)) / 2
        deviation = abs(closes[-1] - mid_range) / mid_range if mid_range > 0 else 0
        panda = max(0, 1 - deviation * 5) * AURIS_NODES["Panda"]["weight"]
        node_values["Panda"] = panda
        
        # CargoShip (Infrastructure) - Sustained trends
        trend_strength = abs(price_change) * volume_spike
        cargoship = min(trend_strength * 5, 1.0) * AURIS_NODES["CargoShip"]["weight"]
        node_values["CargoShip"] = cargoship
        
        # Clownfish (Symbiosis) - Overall ecosystem health
        clownfish = (hummingbird + panda + dolphin) / 3 * AURIS_NODES["Clownfish"]["weight"]
        node_values["Clownfish"] = clownfish
        
        # Compute substrate as weighted sum of nodes
        total_weight = sum(n["weight"] for n in AURIS_NODES.values())
        substrate = sum(node_values.values()) / total_weight
        
        # Find dominant node
        dominant = max(node_values, key=node_values.get)
        
        return substrate, dominant
    
    def compute_observer(self, key: PianoKey) -> float:
        """
        O(t) = OBSERVER - Conscious focus shapes the field
        
        The observer is YOU - your attention and intention.
        Here we simulate it based on:
        - Position size (more invested = more focus)
        - P&L status (profits feel good, losses demand attention)
        - Time in position (longer = more attached)
        """
        # Base observer from coherence
        observer = 0.5
        
        # Attention from P&L
        if key.pnl_pct > 0:
            observer += min(key.pnl_pct / 10, 0.3)  # Profits increase attention
        else:
            observer += min(abs(key.pnl_pct) / 20, 0.2)  # Losses also increase attention
        
        # Modulate with nonlinearity (g parameter)
        g = 2.0
        observer = math.tanh(g * (observer - 0.5)) / 2 + 0.5
        
        return observer
    
    def compute_echo(self) -> float:
        """
        E(t) = ECHO - Causal feedback from τ seconds ago
        
        The echo is the field's memory - what happened before
        influences what happens now. This creates temporal coherence.
        """
        if len(self.lambda_history) < int(self.tau):
            return 0.5
        
        # Get lambda from tau seconds ago
        echo_idx = -int(self.tau)
        past_lambda = self.lambda_history[echo_idx]
        
        return past_lambda * self.beta
    
    def compute_coherence(self, substrate: float, observer: float, echo: float) -> float:
        """
        Γ = COHERENCE - Field alignment
        
        Γ = |ψ| × cos(θ) where θ is the phase difference
        High coherence = all components aligned = strong signal
        """
        # Combine components
        psi = math.sqrt(substrate**2 + observer**2 + echo**2)
        
        # Phase alignment (how well they agree)
        if psi > 0:
            alignment = (substrate + observer + echo) / (3 * psi)
        else:
            alignment = 0
        
        coherence = psi * max(0, alignment)
        return min(coherence, 1.0)
    
    def compute_lambda(self, key: PianoKey, klines: List[dict]) -> None:
        """
        Λ(t) = S(t) + O(t) + E(t)
        
        The MASTER EQUATION that governs reality.
        """
        # Compute components
        substrate, dominant = self.compute_substrate(key, klines)
        observer = self.compute_observer(key)
        echo = self.compute_echo()
        
        # Master equation
        lambda_value = substrate + self.alpha * observer + echo
        
        # Compute coherence
        coherence = self.compute_coherence(substrate, observer, echo)
        
        # Determine rainbow state based on coherence
        if coherence > 0.9:
            rainbow = "UNITY"
        elif coherence > 0.8:
            rainbow = "AWE"
        elif coherence > 0.7:
            rainbow = "LOVE"
        elif coherence > 0.5:
            rainbow = "RESONANCE"
        elif coherence > 0.3:
            rainbow = "FORMING"
        else:
            rainbow = "FEAR"
        
        # Update key state
        key.substrate = substrate
        key.observer = observer
        key.echo = echo
        key.lambda_value = lambda_value
        key.coherence = coherence
        key.dominant_node = dominant
        key.rainbow_state = rainbow
        
        # Store in history
        self.lambda_history.append(lambda_value)
        if len(self.lambda_history) > self.max_history:
            self.lambda_history.pop(0)
    
    def calculate_rsi(self, closes: List[float], period: int = 14) -> float:
        """Calculate RSI indicator"""
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
    
    # ═══════════════════════════════════════════════════════════
    # SIGNAL GENERATION - When to play each key
    # ═══════════════════════════════════════════════════════════
    
    def generate_signal(self, key: PianoKey) -> Tuple[str, float]:
        """
        Generate trading signal for a key based on harmonic state.
        
        STRONG_BUY: High coherence, bullish momentum, Rainbow at LOVE+
        BUY: Good coherence, positive momentum
        HOLD: Neutral or uncertain
        SELL: Poor coherence, bearish momentum
        STRONG_SELL: Low coherence, strong bearish, Rainbow at FEAR
        
        Returns: (signal, confidence)
        """
        score = 0.0
        
        # Lambda contribution (field strength)
        if key.lambda_value > 2.0:
            score += 30
        elif key.lambda_value > 1.5:
            score += 20
        elif key.lambda_value > 1.0:
            score += 10
        elif key.lambda_value < 0.5:
            score -= 20
        
        # Coherence contribution (alignment)
        if key.coherence > 0.9:
            score += 25
        elif key.coherence > 0.8:
            score += 15
        elif key.coherence > 0.6:
            score += 5
        elif key.coherence < 0.3:
            score -= 20
        
        # Rainbow state contribution
        rainbow_scores = {
            "UNITY": 25,
            "AWE": 15,
            "LOVE": 10,
            "RESONANCE": 5,
            "FORMING": 0,
            "FEAR": -20
        }
        score += rainbow_scores.get(key.rainbow_state, 0)
        
        # Momentum contribution
        if key.momentum > 2:
            score += 15
        elif key.momentum > 0.5:
            score += 8
        elif key.momentum < -2:
            score -= 15
        elif key.momentum < -0.5:
            score -= 8
        
        # RSI contribution
        if key.rsi < 30:
            score += 15  # Oversold = bullish
        elif key.rsi < 40:
            score += 8
        elif key.rsi > 70:
            score -= 15  # Overbought = bearish
        elif key.rsi > 60:
            score -= 8
        
        # Dominant node bonuses
        bullish_nodes = ["Falcon", "Dolphin", "CargoShip"]
        bearish_nodes = ["Tiger", "Deer"]
        
        if key.dominant_node in bullish_nodes:
            score += 10
        elif key.dominant_node in bearish_nodes:
            score -= 5
        
        # Generate signal
        confidence = min(abs(score) / 100, 1.0)
        
        if score >= 60:
            return "STRONG_BUY", confidence
        elif score >= 30:
            return "BUY", confidence
        elif score <= -60:
            return "STRONG_SELL", confidence
        elif score <= -30:
            return "SELL", confidence
        else:
            return "HOLD", confidence
    
    # ═══════════════════════════════════════════════════════════
    # PLAYING THE PIANO - Main orchestration loop
    # ═══════════════════════════════════════════════════════════
    
    def refresh_keys(self):
        """Refresh all piano keys from account"""
        account = self.get_account()
        prices = self.get_prices()
        tickers = self.get_24h_tickers()
        btc_usd = prices.get('BTCUSDT', 95000)
        
        self.keys = {}
        
        for b in account.get('balances', []):
            free = float(b['free'])
            asset = b['asset']
            btc_pair = f"{asset}BTC"
            
            # Skip tiny balances and non-BTC pairs
            if free < 0.00001:
                continue
            if btc_pair not in prices and asset != 'BTC':
                continue
            if asset in ['USDT', 'LDUSDC', 'BTC']:
                continue  # Skip stables and BTC itself
            
            current_price = prices.get(btc_pair, 0)
            usd_value = free * current_price * btc_usd
            
            if usd_value < 1:  # Skip dust
                continue
            
            # Get entry price from tracked positions
            entry_price = self.tracked_positions.get(asset, {}).get('entry_price', current_price)
            
            # Get 24h data
            ticker = tickers.get(btc_pair, {})
            
            key = PianoKey(
                asset=asset,
                btc_pair=btc_pair,
                amount=free,
                entry_price=entry_price,
                current_price=current_price,
                momentum=ticker.get('change', 0),
                volatility=(ticker.get('high', 0) - ticker.get('low', 0)) / current_price if current_price > 0 else 0,
            )
            
            self.keys[asset] = key
        
        return len(self.keys)
    
    def analyze_all_keys(self):
        """Analyze all keys with full Master Equation"""
        print(f"\n🎹 ANALYZING {len(self.keys)} PIANO KEYS")
        print("=" * 70)
        
        for asset, key in self.keys.items():
            try:
                # Get klines for this pair
                klines = self.get_klines(key.btc_pair, '15m', 20)
                
                # Calculate RSI
                if klines:
                    closes = [k['close'] for k in klines]
                    key.rsi = self.calculate_rsi(closes)
                
                # Compute Master Equation
                self.compute_lambda(key, klines)
                
                # Generate signal
                signal, confidence = self.generate_signal(key)
                
                # Display key status
                pnl_str = f"{key.pnl_pct:+.2f}%" if key.entry_price != key.current_price else "NEW"
                
                print(f"\n  🎹 {asset}")
                print(f"     Λ={key.lambda_value:.3f} Γ={key.coherence:.3f} 🌈{key.rainbow_state}")
                print(f"     S={key.substrate:.3f} O={key.observer:.3f} E={key.echo:.3f}")
                print(f"     Node: {key.dominant_node} | RSI: {key.rsi:.1f} | Mom: {key.momentum:+.2f}%")
                print(f"     P&L: {pnl_str} | Signal: {signal} ({confidence:.0%})")
                
            except Exception as e:
                print(f"  ⚠️ {asset}: Error - {e}")
        
        # Calculate global field state
        if self.keys:
            self.global_coherence = sum(k.coherence for k in self.keys.values()) / len(self.keys)
            self.global_lambda = sum(k.lambda_value for k in self.keys.values()) / len(self.keys)
            
            # Global rainbow state
            if self.global_coherence > 0.8:
                self.global_rainbow = "LOVE" if self.global_coherence < 0.9 else "UNITY"
            elif self.global_coherence > 0.5:
                self.global_rainbow = "RESONANCE"
            else:
                self.global_rainbow = "FORMING"
    
    def find_opportunities(self) -> List[Tuple[str, str, float]]:
        """Find trading opportunities from analyzed keys"""
        opportunities = []
        
        for asset, key in self.keys.items():
            signal, confidence = self.generate_signal(key)
            
            if signal in ["STRONG_BUY", "BUY"] and confidence > 0.4:
                opportunities.append((asset, signal, confidence))
            elif signal in ["STRONG_SELL", "SELL"] and confidence > 0.4:
                opportunities.append((asset, signal, confidence))
        
        # Sort by confidence
        opportunities.sort(key=lambda x: x[2], reverse=True)
        return opportunities
    
    def display_portfolio_status(self):
        """Display full portfolio status"""
        prices = self.get_prices()
        btc_usd = prices.get('BTCUSDT', 95000)
        account = self.get_account()
        
        btc_balance = 0
        for b in account.get('balances', []):
            if b['asset'] == 'BTC':
                btc_balance = float(b['free'])
                break
        
        print("\n" + "=" * 70)
        print("🎹 AUREON PIANO - PORTFOLIO HARMONICS")
        print("=" * 70)
        print(f"⏱️  Time: {datetime.now().strftime('%H:%M:%S')}")
        print(f"💰 BTC Reserve: {btc_balance:.8f} (${btc_balance * btc_usd:.2f})")
        print(f"🌐 Global Λ: {self.global_lambda:.3f} | Γ: {self.global_coherence:.3f}")
        print(f"🌈 Field State: {self.global_rainbow}")
        print("=" * 70)
        
        # Summary of all keys
        total_value = btc_balance * btc_usd
        for asset, key in self.keys.items():
            value = key.amount * key.current_price * btc_usd
            total_value += value
            
            signal, conf = self.generate_signal(key)
            emoji = "🟢" if "BUY" in signal else "🔴" if "SELL" in signal else "⚪"
            
            print(f"{emoji} {asset:6} | ${value:8.2f} | Λ={key.lambda_value:.2f} | {key.rainbow_state:10} | {signal}")
        
        print("=" * 70)
        print(f"💎 TOTAL PORTFOLIO: ${total_value:.2f}")
        print("=" * 70)
        
        return total_value
    
    def play(self, cycles: int = 10, interval: int = 30):
        """
        Play the piano - main trading loop
        
        Each cycle:
        1. Refresh all keys
        2. Compute Master Equation for each
        3. Generate signals
        4. Execute trades based on signals
        5. Display harmonic status
        """
        print("\n" + "=" * 70)
        print("🎹 AUREON PIANO PLAYER - STARTING")
        print("   'Playing the harmonics across all coins'")
        print("=" * 70)
        
        for cycle in range(1, cycles + 1):
            print(f"\n{'━' * 70}")
            print(f"🎼 CYCLE {cycle}/{cycles}")
            print(f"{'━' * 70}")
            
            try:
                # Refresh and analyze
                num_keys = self.refresh_keys()
                print(f"🎹 Loaded {num_keys} piano keys")
                
                self.analyze_all_keys()
                
                # Find opportunities
                opps = self.find_opportunities()
                if opps:
                    print(f"\n🎯 OPPORTUNITIES FOUND:")
                    for asset, signal, conf in opps[:5]:
                        print(f"   {asset}: {signal} ({conf:.0%})")
                
                # Display status
                total = self.display_portfolio_status()
                
                self.t += self.dt
                
            except Exception as e:
                print(f"⚠️ Cycle error: {e}")
            
            if cycle < cycles:
                print(f"\n⏳ Next cycle in {interval}s...")
                time.sleep(interval)
        
        print("\n" + "=" * 70)
        print("🎹 PIANO PLAYER COMPLETE")
        print("=" * 70)


    # ═══════════════════════════════════════════════════════════
    # TRADE EXECUTION - Making the music
    # ═══════════════════════════════════════════════════════════
    
    def get_symbol_info(self, symbol: str) -> Optional[dict]:
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
    
    def round_step(self, value: float, step: float) -> float:
        """Round value to step size"""
        import math
        precision = len(str(step).rstrip('0').split('.')[-1]) if '.' in str(step) else 0
        return round(math.floor(value / step) * step, precision)
    
    def place_order(self, symbol: str, side: str, quantity: float) -> dict:
        """Place a market order"""
        params = {
            'symbol': symbol,
            'side': side,
            'type': 'MARKET',
            'quantity': str(quantity)
        }
        query = self.sign_request(params)
        url = f'https://api.binance.com/api/v3/order?{query}'
        return requests.post(url, headers={'X-MBX-APIKEY': API_KEY}).json()
    
    def execute_signal(self, asset: str, key: PianoKey, signal: str, confidence: float) -> bool:
        """Execute a trade based on signal"""
        prices = self.get_prices()
        btc_usd = prices.get('BTCUSDT', 95000)
        
        # Get BTC balance for buying
        account = self.get_account()
        btc_balance = 0
        for b in account.get('balances', []):
            if b['asset'] == 'BTC':
                btc_balance = float(b['free'])
                break
        
        if signal in ["STRONG_BUY", "BUY"]:
            # BUY more of this asset
            if btc_balance < 0.00012:  # Minimum trade
                print(f"     ⚠️ Insufficient BTC to buy {asset}")
                return False
            
            # Use confidence to size position
            trade_btc = min(btc_balance * 0.3 * confidence, btc_balance - 0.00005)
            trade_btc = max(trade_btc, 0.00012)
            
            info = self.get_symbol_info(key.btc_pair)
            if not info:
                print(f"     ⚠️ No symbol info for {key.btc_pair}")
                return False
            
            qty = trade_btc / key.current_price
            qty = self.round_step(qty, info['stepSize'])
            
            if qty * key.current_price < info['minNotional']:
                print(f"     ⚠️ Order too small for {asset}")
                return False
            
            print(f"     🎹 BUYING {qty:.4f} {asset} @ {key.current_price:.8f}")
            result = self.place_order(key.btc_pair, 'BUY', qty)
            
            if 'orderId' in result:
                print(f"     ✅ Order filled! ID: {result['orderId']}")
                # Track position
                self.tracked_positions[asset] = {
                    'entry_price': key.current_price,
                    'quantity': qty,
                    'entry_time': datetime.now().isoformat()
                }
                self.save_positions()
                return True
            else:
                print(f"     ❌ Order failed: {result.get('msg', result)}")
                return False
        
        elif signal in ["STRONG_SELL", "SELL"]:
            # SELL this asset
            if key.amount < 0.0001:
                print(f"     ⚠️ Nothing to sell for {asset}")
                return False
            
            info = self.get_symbol_info(key.btc_pair)
            if not info:
                return False
            
            qty = self.round_step(key.amount * 0.9, info['stepSize'])  # Sell 90%
            
            if qty * key.current_price < info['minNotional']:
                print(f"     ⚠️ Position too small to sell {asset}")
                return False
            
            print(f"     🎹 SELLING {qty:.4f} {asset} @ {key.current_price:.8f}")
            result = self.place_order(key.btc_pair, 'SELL', qty)
            
            if 'orderId' in result:
                pnl = (key.current_price - key.entry_price) * qty
                pnl_usd = pnl * btc_usd
                print(f"     ✅ Sold! P&L: {pnl:.8f} BTC (${pnl_usd:.2f})")
                # Remove from tracking
                if asset in self.tracked_positions:
                    del self.tracked_positions[asset]
                    self.save_positions()
                return True
            else:
                print(f"     ❌ Sell failed: {result.get('msg', result)}")
                return False
        
        return False
    
    def execute_opportunities(self, max_trades: int = 2):
        """Execute trades on best opportunities"""
        opps = self.find_opportunities()
        trades_made = 0
        
        for asset, signal, confidence in opps:
            if trades_made >= max_trades:
                break
            
            key = self.keys.get(asset)
            if not key:
                continue
            
            # Only execute high-confidence signals
            if confidence >= 0.6:
                print(f"\n  🎵 Executing {signal} on {asset} ({confidence:.0%} confidence)")
                if self.execute_signal(asset, key, signal, confidence):
                    trades_made += 1
        
        return trades_made


def main():
    """Main entry point"""
    import sys
    
    # Parse command line
    live = '--live' in sys.argv
    cycles = 10 if live else 5
    interval = 30 if live else 20
    
    print("\n" + "=" * 70)
    print("🎹 AUREON PIANO PLAYER")
    print("=" * 70)
    print(f"Mode: {'🔴 LIVE TRADING' if live else '👁️ OBSERVATION ONLY'}")
    print(f"Cycles: {cycles}, Interval: {interval}s")
    print("=" * 70)
    
    if not live:
        print("\n⚠️ Running in observation mode. Use --live to enable trading.")
    
    piano = AureonPiano()
    
    for cycle in range(1, cycles + 1):
        print(f"\n{'━' * 70}")
        print(f"🎼 CYCLE {cycle}/{cycles}")
        print(f"{'━' * 70}")
        
        try:
            # Refresh and analyze
            num_keys = piano.refresh_keys()
            print(f"🎹 Loaded {num_keys} piano keys")
            
            piano.analyze_all_keys()
            
            # Execute trades if live mode
            if live:
                trades = piano.execute_opportunities(max_trades=1)
                if trades > 0:
                    print(f"\n  🎵 Executed {trades} trade(s)")
            
            # Display status
            piano.display_portfolio_status()
            
        except Exception as e:
            print(f"⚠️ Cycle error: {e}")
        
        if cycle < cycles:
            print(f"\n⏳ Next cycle in {interval}s...")
            time.sleep(interval)
    
    print("\n" + "=" * 70)
    print("🎹 PIANO PLAYER COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
