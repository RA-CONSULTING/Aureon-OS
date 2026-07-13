#!/usr/bin/env python3
"""
🦉 AUREON AURIS TRADER 🦉
═══════════════════════════════════════════════════════════════════════════════
THE 9 NODES OF REALITY TRADING ENGINE
Based on src/core/aurisNodes.ts and aurisSymbolicTaxonomy.ts

"The Dolphin sings the wave. The Hummingbird locks the pulse.
 The Tiger cuts the noise. The Owl remembers. The Panda loves."

STRATEGY:
  - 9 Auris Nodes analyze market texture in real-time
  - Coherence (Γ) is calculated from the weighted sum of nodes
  - Entry: Γ > 0.938 (Heart Coherence)
  - Exit: Γ < 0.934 (Coherence Break) or Target Hit
  - Speed: 500ms loop (Quantum Rapid)

NODES:
  1. 🐅 Tiger (Volatility/Spread) - Cuts noise
  2. 🦅 Falcon (Momentum/Volume) - Speed
  3. 🐦 Hummingbird (Stability) - High-freq lock
  4. 🐬 Dolphin (Waveform) - Emotional carrier
  5. 🦌 Deer (Sensing) - Micro-shifts
  6. 🦉 Owl (Memory) - Pattern recognition
  7. 🐼 Panda (Safety) - Grounding
  8. 🚢 CargoShip (Liquidity) - Momentum buffer
  9. 🐠 Clownfish (Symbiosis) - Connection

Author: Aureon System / Gary Leckey
Date: November 28, 2025
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import time
import math
import logging
import random
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from aureon.exchanges.binance_client import BinanceClient, get_binance_client

# 🪙 PENNY PROFIT ENGINE
try:
    from aureon.trading.penny_profit_engine import check_penny_exit, get_penny_engine
    PENNY_PROFIT_AVAILABLE = True
    _penny_engine = get_penny_engine()
    print("🪙 Penny Profit Engine loaded for Auris Trader")
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
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Trading
TRADE_INTERVAL_MS = 500
RISK_PERCENT = 10.0  # 10% per trade
ENTRY_COHERENCE = 0.938
EXIT_COHERENCE = 0.934
MIN_PROFIT_PCT = 0.8  # 0.8% Net profit target (was 0.2% - need to beat fees!)

# 🔶 PAIRS - Comprehensive Binance trading pairs (70+)
PAIRS = [
    # === TOP TIER ===
    'BTCUSDC', 'ETHUSDC', 'SOLUSDC', 'XRPUSDC', 'ADAUSDC', 'AVAXUSDC', 'BNBUSDC',
    'DOTUSDC', 'ATOMUSDC', 'NEARUSDC', 'ICPUSDC', 'APTUSDC', 'SUIUSDC', 'SEIUSDC',
    # === LAYER 2s ===
    'ARBUSDC', 'OPUSDC', 'MATICUSDC', 'STXUSDC', 'IMXUSDC',
    # === DEFI ===
    'UNIUSDC', 'AAVEUSDC', 'LINKUSDC', 'CRVUSDC', 'SNXUSDC', 'LDOUSDC',
    # === AI & DATA ===
    'FETUSDC', 'RENDERUSDC', 'INJUSDC', 'WLDUSDC',
    # === MEMECOINS ===
    'DOGEUSDC', 'SHIBUSDC', 'PEPEUSDC', 'BONKUSDC', 'FLOKIUSDC', 'WIFUSDC',
    # === MID CAPS ===
    'LTCUSDC', 'FILUSDC', 'XLMUSDC', 'TRXUSDC', 'HBARUSDC', 'RUNEUSDC',
]

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# AURIS NODES IMPLEMENTATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MarketSnapshot:
    symbol: str
    price: float
    volume: float      # Normalized 0-1
    volatility: float  # Normalized 0-1
    momentum: float    # Normalized -1 to 1
    spread: float      # Normalized 0-1
    timestamp: float

class AurisNode:
    def __init__(self, name: str, weight: float, freq: float):
        self.name = name
        self.weight = weight
        self.freq = freq
        self.value = 0.0

    def compute(self, s: MarketSnapshot) -> float:
        return 0.0

# ─── THE 9 NODES ───

class TigerNode(AurisNode):
    """Cuts the noise - Volatility & Spread"""
    def compute(self, s: MarketSnapshot) -> float:
        # Inverse volatility preference (likes calm before storm)
        val = (1.0 - s.volatility) * 0.8 + (1.0 - s.spread) * 0.5
        return max(0.0, min(1.0, val))

class FalconNode(AurisNode):
    """Speed & Attack - Momentum & Volume"""
    def compute(self, s: MarketSnapshot) -> float:
        val = abs(s.momentum) * 0.7 + s.volume * 0.3
        return max(0.0, min(1.0, val))

class HummingbirdNode(AurisNode):
    """Micro-stabilizer - High frequency lock"""
    def compute(self, s: MarketSnapshot) -> float:
        # Likes low volatility, high stability
        val = (1.0 / (s.volatility + 0.01)) * 0.01 * 0.6
        return max(0.0, min(1.0, val))

class DolphinNode(AurisNode):
    """Emotional Carrier - Waveform"""
    def compute(self, s: MarketSnapshot) -> float:
        # Sine wave modulation based on momentum
        val = (math.sin(s.momentum * math.pi) + 1) * 0.5
        return max(0.0, min(1.0, val))

class DeerNode(AurisNode):
    """Subtle Sensing - Micro-shifts"""
    def compute(self, s: MarketSnapshot) -> float:
        # Sensitive to volume/volatility mix
        val = s.volume * 0.2 + s.volatility * 0.3 + s.spread * 0.2
        return max(0.0, min(1.0, val))

class OwlNode(AurisNode):
    """Memory - Pattern Recognition"""
    def compute(self, s: MarketSnapshot) -> float:
        # Cosine of momentum (cyclic)
        val = (math.cos(s.momentum * math.pi) + 1) * 0.3
        if s.momentum > 0: val += 0.3
        return max(0.0, min(1.0, val))

class PandaNode(AurisNode):
    """Love/Grounding - Volume safety"""
    def compute(self, s: MarketSnapshot) -> float:
        # Only active if volume is sufficient
        return s.volume * 0.8 if s.volume > 0.5 else 0.2

class CargoShipNode(AurisNode):
    """Momentum Buffer - Heavy Liquidity"""
    def compute(self, s: MarketSnapshot) -> float:
        # Requires high volume to move
        return s.volume * 1.0 if s.volume > 0.6 else 0.0

class ClownfishNode(AurisNode):
    """Symbiosis - Price stability"""
    def compute(self, s: MarketSnapshot) -> float:
        # Checks if price is holding levels
        return 0.8 if s.volatility < 0.3 else 0.2

# ═══════════════════════════════════════════════════════════════════════════════
# AURIS ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class AurisEngine:
    def __init__(self):
        self.nodes = [
            TigerNode("Tiger", 1.2, 741.0),
            FalconNode("Falcon", 1.1, 285.0),
            HummingbirdNode("Hummingbird", 0.8, 963.0),
            DolphinNode("Dolphin", 1.0, 528.0),
            DeerNode("Deer", 0.9, 396.0),
            OwlNode("Owl", 1.0, 432.0),
            PandaNode("Panda", 0.95, 412.3),
            CargoShipNode("CargoShip", 1.3, 174.0),
            ClownfishNode("Clownfish", 0.7, 639.0)
        ]
        self.total_weight = sum(n.weight for n in self.nodes)

    def calculate_coherence(self, snapshot: MarketSnapshot) -> float:
        weighted_sum = 0.0
        
        # Compute each node
        for node in self.nodes:
            val = node.compute(snapshot)
            weighted_sum += val * node.weight
            
        # Normalize
        coherence = weighted_sum / self.total_weight
        
        # Apply Master Equation Λ(t) bias (simplified)
        # If momentum is positive and volume is high, boost coherence
        if snapshot.momentum > 0 and snapshot.volume > 0.5:
            coherence *= 1.1
            
        return min(1.0, coherence)

# ═══════════════════════════════════════════════════════════════════════════════
# TRADER IMPLEMENTATION
# ═══════════════════════════════════════════════════════════════════════════════

class AurisTrader:
    def __init__(self):
        self.client = get_binance_client()
        self.engine = AurisEngine()
        self.positions = {}
        self.history = {}  # For calculating volatility/momentum
        
    def get_market_snapshot(self, symbol: str) -> Optional[MarketSnapshot]:
        try:
            # Get 24h ticker for volume/change
            ticker = self.client.session.get(
                f'{self.client.base}/api/v3/ticker/24hr',
                params={'symbol': symbol}, timeout=1
            ).json()
            
            # Get order book for spread
            depth = self.client.session.get(
                f'{self.client.base}/api/v3/depth',
                params={'symbol': symbol, 'limit': 5}, timeout=1
            ).json()
            
            price = float(ticker['lastPrice'])
            bid = float(depth['bids'][0][0])
            ask = float(depth['asks'][0][0])
            
            # Metrics
            spread = (ask - bid) / bid
            volume_raw = float(ticker['quoteVolume'])
            change_pct = float(ticker['priceChangePercent'])
            
            # Normalize (Simplified for speed)
            vol_norm = min(1.0, volume_raw / 10_000_000) # Cap at 10M
            spread_norm = min(1.0, spread * 1000)
            momentum_norm = max(-1.0, min(1.0, change_pct / 5.0)) # Cap at 5%
            volatility_norm = abs(momentum_norm) # Proxy
            
            return MarketSnapshot(
                symbol=symbol,
                price=price,
                volume=vol_norm,
                volatility=volatility_norm,
                momentum=momentum_norm,
                spread=spread_norm,
                timestamp=time.time()
            )
            
        except Exception as e:
            # logger.error(f"Snapshot error {symbol}: {e}")
            return None

    def run(self):
        print(f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    🦉 AUREON AURIS TRADER LIVE 🦉                             ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║   Strategy: 9 Nodes of Reality                                                ║
║   Entry Γ:  {ENTRY_COHERENCE}                                                       ║
║   Risk:     {RISK_PERCENT}%                                                          ║
║   Interval: {TRADE_INTERVAL_MS}ms                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════╝
        """)
        
        while True:
            try:
                # 1. Check Exits
                self.check_exits()
                
                # 2. Scan for Entries
                if len(self.positions) < 3:
                    self.scan_and_enter()
                
                # 3. Sleep
                time.sleep(TRADE_INTERVAL_MS / 1000.0)
                
            except KeyboardInterrupt:
                print("\n🛑 Stopping Auris Trader...")
                break
            except Exception as e:
                logger.error(f"Loop error: {e}")
                time.sleep(1)

    def scan_and_enter(self):
        best_opp = None
        best_coherence = 0.0
        
        for symbol in PAIRS:
            if symbol in self.positions: continue
            
            snapshot = self.get_market_snapshot(symbol)
            if not snapshot: continue
            
            coherence = self.engine.calculate_coherence(snapshot)
            
            # Log high coherence
            if coherence > 0.8:
                print(f"   {symbol}: Γ={coherence:.4f} (Mom:{snapshot.momentum:.2f} Vol:{snapshot.volume:.2f})")
            
            if coherence > ENTRY_COHERENCE:
                if coherence > best_coherence:
                    best_coherence = coherence
                    best_opp = snapshot

        if best_opp:
            self.execute_buy(best_opp, best_coherence)

    def execute_buy(self, s: MarketSnapshot, coherence: float):
        usdc = self.client.get_free_balance('USDC')
        trade_size = usdc * (RISK_PERCENT / 100.0)
        
        if trade_size < 5.0:
            # logger.warning("Insufficient funds for trade")
            return

        print(f"🚀 AURIS ENTRY: {s.symbol} @ ${s.price:.4f} | Γ={coherence:.4f}")
        
        # Execute
        try:
            qty = trade_size / s.price
            # Precision handling would go here (using helper from other files)
            # For now, simple market buy
            res = self.client.place_market_order(s.symbol, 'BUY', quantity=qty) # Note: client handles precision if updated
            
            if res:
                self.positions[s.symbol] = {
                    'entry_price': s.price,
                    'quantity': qty,
                    'entry_time': time.time(),
                    'max_coherence': coherence
                }
        except Exception as e:
            logger.error(f"Buy failed: {e}")

    def check_exits(self):
        for symbol in list(self.positions.keys()):
            pos = self.positions[symbol]
            snapshot = self.get_market_snapshot(symbol)
            if not snapshot: continue
            
            # Track cycles for min hold time
            pos['cycles'] = pos.get('cycles', 0) + 1
            
            coherence = self.engine.calculate_coherence(snapshot)
            pnl_pct = (snapshot.price - pos['entry_price']) / pos['entry_price'] * 100
            current_value = pos['quantity'] * snapshot.price
            entry_value = pos.get('entry_value', pos['quantity'] * pos['entry_price'])
            gross_pnl = current_value - entry_value
            
            should_exit = False
            reason = ""
            
            # 🪙 PENNY PROFIT EXIT LOGIC (Priority over Coherence)
            if PENNY_PROFIT_AVAILABLE and _penny_engine is not None:
                action, _ = check_penny_exit('binance', entry_value, current_value)
                threshold = _penny_engine.get_threshold('binance', entry_value)
                
                if action == 'TAKE_PROFIT':
                    should_exit = True
                    reason = f"🪙 PENNY TP (${gross_pnl:.4f} >= ${threshold.win_gte:.4f})"
                elif action == 'STOP_LOSS' and pos['cycles'] >= 5:
                    should_exit = True
                    reason = f"🪙 PENNY SL (${gross_pnl:.4f} <= ${threshold.stop_lte:.4f})"
                elif coherence < EXIT_COHERENCE and pos['cycles'] >= 5:
                    # Only allow coherence break after min hold
                    should_exit = True
                    reason = f"Coherence Break (Γ={coherence:.4f})"
            else:
                # Fallback: Exit Logic
                if coherence < EXIT_COHERENCE and pos['cycles'] >= 5:
                    should_exit = True
                    reason = f"Coherence Break (Γ={coherence:.4f})"
                elif pnl_pct > MIN_PROFIT_PCT * 3:
                    should_exit = True
                    reason = f"Target Hit (+{pnl_pct:.2f}%)"
                elif pnl_pct < -1.0 and pos['cycles'] >= 5:
                    should_exit = True
                    reason = f"Stop Loss (-{pnl_pct:.2f}%)"
                
            if should_exit:
                print(f"📤 AURIS EXIT: {symbol} @ ${snapshot.price:.4f} | {reason}")
                try:
                    # Sell all
                    balance = self.client.get_free_balance(symbol.replace('USDC',''))
                    self.client.place_market_order(symbol, 'SELL', quantity=balance)
                    del self.positions[symbol]
                except Exception as e:
                    logger.error(f"Sell failed: {e}")

if __name__ == "__main__":
    trader = AurisTrader()
    trader.run()
