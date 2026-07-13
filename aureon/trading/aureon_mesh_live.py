#!/usr/bin/env python3
"""
AUREON MESH LIVE TRADING ENGINE
═══════════════════════════════════════════════════════════════════════════════
"Trade on Everything" - Dynamic Mesh Trading System

Strategy:
  - Scans wallet for ANY asset with balance > 0
  - Identifies all tradeable pairs for those assets (Base or Quote)
  - Applies Master Equation Λ(t) to each pair
  - High Coherence (Order) -> Move into Base Asset (BUY)
  - Low Coherence (Chaos) -> Move into Quote Asset (SELL)
  - Dynamic position sizing based on available balance

Features:
  - Wallet-aware pair discovery
  - Dynamic "Mesh" execution (Buy/Sell based on what we hold)
  - Real-time P&L tracking
  - Master Equation Coherence Gating (Γ > 0.938 Entry)

Usage:
  export CONFIRM_LIVE=yes
  python3 aureon_mesh_live.py --duration 3600

Author: Aureon System / Gary Leckey
Date: November 28, 2025
"""
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os, sys, json, time, logging, argparse, random
from datetime import datetime
from typing import List, Dict, Any
from aureon.exchanges.binance_client import BinanceClient, get_binance_client

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('mesh_trade.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# 9 AURIS NODES
# ═══════════════════════════════════════════════════════════════════════════════

class AurisNode:
    def __init__(self, name: str, fn, weight: float):
        self.name = name
        self.fn = fn
        self.weight = weight

    def compute(self, data: dict) -> float:
        try:
            return self.fn(data) * self.weight
        except:
            return 0.0

def create_auris_nodes():
    import math
    
    # Enhanced Clownfish v2.0 micro-change state tracking (12 factors)
    _clownfish_state = {
        'price_ticks': {},
        'spread_history': {},
        'volume_ticks': {},
        'velocity_history': {},
        'acceleration_history': {},
        'jerk_history': {},
        'liquidity_flow': {},
        'signal_success': {},
        'pattern_confidence': {}
    }
    
    def clownfish_micro_detect(d):
        """🐠 Enhanced Clownfish v2.0 - 12-Factor Micro-Change Detection for Mesh
        
        FACTORS:
        1-6: Original (momentum, volume, spread, imbalance, divergence, connection)
        7-12: NEW (jerk, fractal, liquidity, harmonic, time-cycle, neural)
        """
        symbol = d.get('symbol', 'unknown')
        PHI = 1.618033988749895  # Golden ratio
        
        # Initialize per-symbol tracking
        if symbol not in _clownfish_state['price_ticks']:
            _clownfish_state['price_ticks'][symbol] = []
            _clownfish_state['spread_history'][symbol] = []
            _clownfish_state['volume_ticks'][symbol] = []
            _clownfish_state['velocity_history'][symbol] = []
            _clownfish_state['acceleration_history'][symbol] = []
            _clownfish_state['jerk_history'][symbol] = []
            _clownfish_state['liquidity_flow'][symbol] = []
            _clownfish_state['signal_success'][symbol] = []
            _clownfish_state['pattern_confidence'][symbol] = 0.5
        
        # Store tick data (keep last 100 for fractal analysis)
        _clownfish_state['price_ticks'][symbol].append(d['price'])
        _clownfish_state['volume_ticks'][symbol].append(d.get('volume', 0))
        if len(_clownfish_state['price_ticks'][symbol]) > 100:
            _clownfish_state['price_ticks'][symbol] = _clownfish_state['price_ticks'][symbol][-100:]
            _clownfish_state['volume_ticks'][symbol] = _clownfish_state['volume_ticks'][symbol][-100:]
        
        prices = _clownfish_state['price_ticks'][symbol]
        volumes = _clownfish_state['volume_ticks'][symbol]
        
        # ═══════════════════════════════════════════════════════════════
        # FACTOR 1-2: Micro-momentum (velocity + acceleration)
        # ═══════════════════════════════════════════════════════════════
        f1_momentum = 0.5
        velocity = 0
        accel = 0
        if len(prices) >= 3:
            vel1 = (prices[-1] - prices[-2]) / prices[-2] if prices[-2] > 0 else 0
            vel2 = (prices[-2] - prices[-3]) / prices[-3] if prices[-3] > 0 else 0
            velocity = vel1
            accel = vel1 - vel2
            _clownfish_state['velocity_history'][symbol].append(velocity)
            _clownfish_state['acceleration_history'][symbol].append(accel)
            if len(_clownfish_state['velocity_history'][symbol]) > 30:
                _clownfish_state['velocity_history'][symbol] = _clownfish_state['velocity_history'][symbol][-30:]
                _clownfish_state['acceleration_history'][symbol] = _clownfish_state['acceleration_history'][symbol][-20:]
            
            if velocity > 0.001 and accel > 0.0001:
                f1_momentum = min(0.95, 0.65 + velocity * 150 + accel * 1000)
            elif velocity > 0.0005 and accel > 0:
                f1_momentum = min(0.9, 0.6 + velocity * 100)
            elif velocity > 0 and accel < 0:
                f1_momentum = 0.55
            elif velocity < -0.001 and accel < -0.0001:
                f1_momentum = 0.15
            elif velocity < 0 and accel > 0:
                f1_momentum = 0.65  # Potential reversal
        
        # ═══════════════════════════════════════════════════════════════
        # FACTOR 3: Volume micro-burst detection
        # ═══════════════════════════════════════════════════════════════
        f2_volume = 0.5
        if len(volumes) >= 5:
            recent_vol = volumes[-1]
            avg_vol = sum(volumes[:-1]) / len(volumes[:-1]) if volumes[:-1] else 1
            vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1
            if 1.15 <= vol_ratio <= 1.3:
                f2_volume = 0.85  # Sweet spot accumulation
            elif 1.3 < vol_ratio <= 1.5:
                f2_volume = 0.8
            elif 1.5 < vol_ratio <= 2.0:
                f2_volume = 0.7
            elif vol_ratio > 3.0:
                f2_volume = 0.4  # Too high - manipulation
            elif vol_ratio < 0.3:
                f2_volume = 0.2  # Volume dead
            elif vol_ratio < 0.5:
                f2_volume = 0.3
        
        # ═══════════════════════════════════════════════════════════════
        # FACTOR 4: Price position (bid-ask imbalance proxy)
        # ═══════════════════════════════════════════════════════════════
        f3_position = 0.5
        if d['price'] > d.get('open', d['price']):
            f3_position = 0.6 + min(0.2, d.get('change', 0) / 10)
        else:
            f3_position = 0.4 - min(0.1, abs(d.get('change', 0)) / 20)
        f3_position = max(0.2, min(0.8, f3_position))
        
        # ═══════════════════════════════════════════════════════════════
        # FACTOR 5: Momentum-Volume Divergence
        # ═══════════════════════════════════════════════════════════════
        f4_divergence = 0.5
        if len(prices) >= 5 and len(volumes) >= 5:
            price_trend = (prices[-1] - prices[0]) / prices[0] if prices[0] > 0 else 0
            vol_trend = (volumes[-1] - volumes[0]) / volumes[0] if volumes[0] > 0 else 0
            # Bullish divergence: price flat/down but volume up
            if price_trend <= 0.001 and vol_trend > 0.15:
                f4_divergence = 0.85
            elif price_trend <= 0.001 and vol_trend > 0.1:
                f4_divergence = 0.8
            # Bearish divergence: price up but volume down
            elif price_trend > 0.015 and vol_trend < -0.15:
                f4_divergence = 0.2
            elif price_trend > 0.01 and vol_trend < -0.1:
                f4_divergence = 0.3
        
        # ═══════════════════════════════════════════════════════════════
        # FACTOR 6: Connection (original)
        # ═══════════════════════════════════════════════════════════════
        change = d.get('change', 0)
        volume = d.get('volume', 0)
        f5_connection = 0.4
        if change > 0 and volume > 100000:
            f5_connection = 0.7 + min(0.3, change / 30)
        elif change > 0:
            f5_connection = 0.5 + min(0.2, change / 20)
        
        # ═══════════════════════════════════════════════════════════════
        # FACTOR 7: JERK (3rd derivative) - NEW v2.0
        # ═══════════════════════════════════════════════════════════════
        f6_jerk = 0.5
        accels = _clownfish_state['acceleration_history'][symbol]
        if len(accels) >= 2:
            jerk = accels[-1] - accels[-2]
            _clownfish_state['jerk_history'][symbol].append(jerk)
            if len(_clownfish_state['jerk_history'][symbol]) > 15:
                _clownfish_state['jerk_history'][symbol] = _clownfish_state['jerk_history'][symbol][-15:]
            
            jerks = _clownfish_state['jerk_history'][symbol]
            if len(jerks) >= 3:
                avg_jerk = sum(jerks[-3:]) / 3
                if avg_jerk > 0.00005:
                    f6_jerk = 0.85
                elif avg_jerk > 0.00001:
                    f6_jerk = 0.7
                elif avg_jerk < -0.00005:
                    f6_jerk = 0.2
                elif avg_jerk < -0.00001:
                    f6_jerk = 0.35
        
        # ═══════════════════════════════════════════════════════════════
        # FACTOR 8: FRACTAL PATTERN - NEW v2.0
        # ═══════════════════════════════════════════════════════════════
        f7_fractal = 0.5
        if len(prices) >= 20:
            patterns = []
            for window in [5, 10, 20]:
                subset = prices[-window:]
                start_p, end_p = subset[0], subset[-1]
                mid_p = subset[len(subset)//2]
                if end_p > start_p * 1.001:
                    pattern = "V" if mid_p < (start_p + end_p) / 2 else "UP"
                elif end_p < start_p * 0.999:
                    pattern = "A" if mid_p > (start_p + end_p) / 2 else "DOWN"
                else:
                    pattern = "FLAT"
                patterns.append(pattern)
            
            # Check for fractal alignment
            if patterns[0] == patterns[1] == patterns[2]:
                if patterns[0] in ("UP", "V"):
                    f7_fractal = 0.9
                elif patterns[0] in ("DOWN", "A"):
                    f7_fractal = 0.1
            elif patterns.count("UP") + patterns.count("V") >= 2:
                f7_fractal = 0.7
            elif patterns.count("DOWN") + patterns.count("A") >= 2:
                f7_fractal = 0.3
        
        # ═══════════════════════════════════════════════════════════════
        # FACTOR 9: LIQUIDITY FLOW - NEW v2.0
        # ═══════════════════════════════════════════════════════════════
        f8_liquidity = 0.5
        if len(prices) >= 2 and len(volumes) >= 1:
            price_change = prices[-1] - prices[-2]
            current_vol = volumes[-1]
            flow = current_vol if price_change > 0 else (-current_vol if price_change < 0 else 0)
            _clownfish_state['liquidity_flow'][symbol].append(flow)
            if len(_clownfish_state['liquidity_flow'][symbol]) > 30:
                _clownfish_state['liquidity_flow'][symbol] = _clownfish_state['liquidity_flow'][symbol][-30:]
            
            flows = _clownfish_state['liquidity_flow'][symbol]
            if len(flows) >= 5:
                net_flow = sum(flows[-10:])
                avg_vol = sum(volumes) / len(volumes) if volumes else 1
                flow_ratio = net_flow / (avg_vol * 10) if avg_vol > 0 else 0
                if flow_ratio > 0.5:
                    f8_liquidity = 0.9
                elif flow_ratio > 0.2:
                    f8_liquidity = 0.75
                elif flow_ratio > 0.05:
                    f8_liquidity = 0.6
                elif flow_ratio < -0.5:
                    f8_liquidity = 0.1
                elif flow_ratio < -0.2:
                    f8_liquidity = 0.25
        
        # ═══════════════════════════════════════════════════════════════
        # FACTOR 10: HARMONIC RESONANCE (639Hz) - NEW v2.0
        # ═══════════════════════════════════════════════════════════════
        f9_harmonic = 0.5
        if len(prices) >= 10:
            oscillations = 0
            for i in range(2, len(prices)):
                if (prices[i] > prices[i-1]) != (prices[i-1] > prices[i-2]):
                    oscillations += 1
            ticks_per_osc = len(prices) / max(oscillations, 1)
            target_period = 639.0 / 100  # Normalized
            alignment = 1.0 - min(1.0, abs(ticks_per_osc - target_period) / target_period)
            phi_mod = alignment ** (1 / PHI)
            if phi_mod > 0.8:
                f9_harmonic = 0.85
            elif phi_mod > 0.6:
                f9_harmonic = 0.7
            elif phi_mod < 0.3:
                f9_harmonic = 0.35
        
        # ═══════════════════════════════════════════════════════════════
        # FACTOR 11: TIME-CYCLE SYNC (Schumann) - NEW v2.0
        # ═══════════════════════════════════════════════════════════════
        f10_timecycle = 0.5
        import datetime
        hour = datetime.datetime.now().hour
        peak_hours = [8, 9, 10, 13, 14, 15, 16, 1, 2, 3]
        if hour in peak_hours:
            f10_timecycle = 0.6
        schumann_period = 1.0 / 7.83
        schumann_phase = (time.time() % schumann_period) / schumann_period
        schumann_alignment = 1.0 - abs(schumann_phase - 0.5) * 2
        f10_timecycle += schumann_alignment * 0.1
        f10_timecycle = max(0.4, min(0.7, f10_timecycle))
        
        # ═══════════════════════════════════════════════════════════════
        # FACTOR 12: NEURAL PATTERN LEARNING - NEW v2.0
        # ═══════════════════════════════════════════════════════════════
        f11_neural = 0.5
        successes = _clownfish_state['signal_success'][symbol]
        if len(successes) >= 5:
            recent = successes[-20:] if len(successes) >= 20 else successes
            success_rate = sum(1 for s in recent if s > 0) / len(recent)
            old_conf = _clownfish_state['pattern_confidence'][symbol]
            new_conf = old_conf + 0.1 * (success_rate - old_conf)
            _clownfish_state['pattern_confidence'][symbol] = new_conf
            if new_conf > 0.7:
                f11_neural = 0.8
            elif new_conf > 0.6:
                f11_neural = 0.65
            elif new_conf < 0.3:
                f11_neural = 0.3
            elif new_conf < 0.4:
                f11_neural = 0.4
        
        # ═══════════════════════════════════════════════════════════════
        # SACRED GEOMETRY WEIGHTED COMBINATION (12 factors)
        # ═══════════════════════════════════════════════════════════════
        weights = {
            'momentum': PHI,      # 1.618
            'volume': PHI,        # 1.618
            'position': 1.0,      # 1.000
            'divergence': 1.0,    # 1.000
            'connection': 0.5,    # 0.500
            'jerk': 1.0,          # 1.000
            'fractal': 1/PHI,     # 0.618
            'liquidity': 1/PHI,   # 0.618
            'harmonic': 1/PHI,    # 0.618
            'timecycle': 0.382,   # PHI^-2
            'neural': 0.618,      # 0.618
        }
        total_w = sum(weights.values())
        
        weighted_sum = (
            f1_momentum * weights['momentum'] +
            f2_volume * weights['volume'] +
            f3_position * weights['position'] +
            f4_divergence * weights['divergence'] +
            f5_connection * weights['connection'] +
            f6_jerk * weights['jerk'] +
            f7_fractal * weights['fractal'] +
            f8_liquidity * weights['liquidity'] +
            f9_harmonic * weights['harmonic'] +
            f10_timecycle * weights['timecycle'] +
            f11_neural * weights['neural']
        )
        
        response = weighted_sum / total_w
        
        # Confidence boost if multiple strong signals
        strong = sum(1 for f in [f1_momentum, f2_volume, f6_jerk, f7_fractal, f8_liquidity] if f > 0.75)
        if strong >= 4:
            response = min(0.98, response * 1.1)
        elif strong >= 3:
            response = min(0.95, response * 1.05)
        
        # Danger suppression
        danger = sum(1 for f in [f4_divergence, f6_jerk, f7_fractal, f8_liquidity] if f < 0.3)
        if danger >= 3:
            response = max(0.1, response * 0.8)
        
        return max(0.0, min(1.0, response))
    
    nodes = {
        'tiger': AurisNode('tiger', 
            lambda d: ((d['high'] - d['low']) / d['price']) * 100 + (0.2 if d['volume'] > 1000000 else 0), 1.2),
        'falcon': AurisNode('falcon',
            lambda d: abs(d['change']) * 0.7 + min(d['volume'] / 10000000, 0.3), 1.1),
        'hummingbird': AurisNode('hummingbird',
            lambda d: 1 / (1 + ((d['high'] - d['low']) / d['price']) * 10), 0.9),
        'dolphin': AurisNode('dolphin',
            lambda d: math.sin(d['change'] * math.pi / 10) * 0.5 + 0.5, 1.0),
        'deer': AurisNode('deer',
            lambda d: (0.6 if d['price'] > d['open'] else 0.4) + (0.2 if d['change'] > 0 else -0.1), 0.8),
        'owl': AurisNode('owl',
            lambda d: math.cos(d['change'] * math.pi / 10) * 0.3 + (0.3 if d['price'] < d['open'] else 0), 0.9),
        'panda': AurisNode('panda',
            lambda d: 0.5 + math.sin(time.time() / 60000) * 0.1, 0.7),
        'cargoship': AurisNode('cargoship',
            lambda d: 0.8 if d['volume'] > 5000000 else (0.5 if d['volume'] > 1000000 else 0.3), 1.0),
        'clownfish': AurisNode('clownfish',
            clownfish_micro_detect, 1.25),  # 🐠 v2.0 12-factor enhanced with boosted weight
    }
    return nodes

# ═══════════════════════════════════════════════════════════════════════════════
# MASTER EQUATION
# ═══════════════════════════════════════════════════════════════════════════════

class MasterEquation:
    def __init__(self):
        self.auris_nodes = create_auris_nodes()
        self.lambda_history = {}
        self.OBSERVER_WEIGHT = 0.3
        self.ECHO_WEIGHT = 0.2
        self.ENTRY_COHERENCE = 0.938
        self.EXIT_COHERENCE = 0.934

    def compute_substrate(self, market_data: dict) -> float:
        total = 0.0
        weight_sum = 0.0
        for node in self.auris_nodes.values():
            val = node.compute(market_data)
            total += val
            weight_sum += node.weight
        return total / weight_sum if weight_sum > 0 else 0.0

    def compute_echo(self, symbol: str) -> float:
        if symbol not in self.lambda_history or len(self.lambda_history[symbol]) == 0:
            return 0.0
        recent = self.lambda_history[symbol][-5:]
        decay = sum(v * (0.9 ** i) for i, v in enumerate(reversed(recent)))
        return decay / len(recent) * self.ECHO_WEIGHT

    def compute_lambda(self, symbol: str, market_data: dict) -> dict:
        if symbol not in self.lambda_history:
            self.lambda_history[symbol] = []
        
        s_t = self.compute_substrate(market_data)
        o_t = self.lambda_history[symbol][-1] * self.OBSERVER_WEIGHT if self.lambda_history[symbol] else 0.0
        e_t = self.compute_echo(symbol)
        lambda_t = s_t + o_t + e_t
        self.lambda_history[symbol].append(lambda_t)
        
        # Coherence Γ
        variance = max(abs(market_data['high'] - market_data['low']) / market_data['price'], 0.001)
        coherence = max(1 - (variance / 10), 0.0)
        
        return {
            'lambda': lambda_t,
            'coherence': coherence,
            'entry_signal': coherence > self.ENTRY_COHERENCE,
            'exit_signal': coherence < self.EXIT_COHERENCE,
        }

# ═══════════════════════════════════════════════════════════════════════════════
# MESH TRADER
# ═══════════════════════════════════════════════════════════════════════════════

class MeshTrader:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.client = get_binance_client()
        self.master_eq = MasterEquation()
        self.min_notional = 10.0
        
    def get_market_snapshot(self, symbol: str) -> dict:
        try:
            ticker = self.client.session.get(
                f"{self.client.base}/api/v3/ticker/24hr",
                params={'symbol': symbol}
            ).json()
            return {
                'symbol': symbol,
                'price': float(ticker['lastPrice']),
                'volume': float(ticker['volume']),
                'high': float(ticker['highPrice']),
                'low': float(ticker['lowPrice']),
                'open': float(ticker['openPrice']),
                'change': float(ticker['priceChangePercent']),
            }
        except:
            return None

    def discover_tradeable_pairs(self) -> List[Dict[str, Any]]:
        """Find all pairs we can trade based on current wallet balances."""
        logger.info("🔍 Scanning wallet for tradeable assets...")
        try:
            account = self.client.account()
            balances = {b['asset']: float(b['free']) for b in account['balances'] if float(b['free']) > 0}
            
            if not balances:
                logger.warning("⚠️  No assets found in wallet!")
                return []

            logger.info(f"💰 Wallet: {', '.join([f'{k}:{v:.4f}' for k,v in balances.items()])}")

            info = self.client.exchange_info()
            pairs = []
            
            for s in info.get('symbols', []):
                if s['status'] != 'TRADING': continue
                
                base = s['baseAsset']
                quote = s['quoteAsset']
                symbol = s['symbol']
                
                # Check if we can trade this pair
                can_buy = quote in balances and balances[quote] > 0
                can_sell = base in balances and balances[base] > 0
                
                if can_buy or can_sell:
                    pairs.append({
                        'symbol': symbol,
                        'base': base,
                        'quote': quote,
                        'can_buy': can_buy,
                        'can_sell': can_sell,
                        'quote_balance': balances.get(quote, 0.0),
                        'base_balance': balances.get(base, 0.0)
                    })
            
            logger.info(f"✅ Found {len(pairs)} tradeable pairs.")
            return pairs
        except Exception as e:
            logger.error(f"Failed to discover pairs: {e}")
            return []

    def execute_mesh_trade(self, pair: Dict, signal: str, coherence: float) -> dict:
        symbol = pair['symbol']
        try:
            price_data = self.client.best_price(symbol)
            price = float(price_data['price'])
            
            if signal == 'BUY' and pair['can_buy']:
                # Buy Base using Quote
                quote_bal = pair['quote_balance']
                # Use up to $15 worth, or all if small
                trade_amount = min(quote_bal, 15.0) # Assuming quote is roughly $1 (USDT/USDC)
                
                # If quote is NOT stablecoin, we need to be careful. 
                # Simplified: Use 10% of holding
                if pair['quote'] not in ['USDT', 'USDC', 'BUSD', 'DAI']:
                     trade_amount = quote_bal * 0.1
                
                if trade_amount < 0.00001: return {} # Too small

                if self.dry_run:
                    logger.info(f"📝 DRY-RUN: BUY {symbol} with {trade_amount:.4f} {pair['quote']} (Γ={coherence:.4f})")
                    return {'dry_run': False}
                
                logger.info(f"🚀 LIVE: BUY {symbol} with {trade_amount:.4f} {pair['quote']} (Γ={coherence:.4f})")
                return self.client.place_market_order(symbol, 'BUY', quote_qty=trade_amount)

            elif signal == 'SELL' and pair['can_sell']:
                # Sell Base for Quote
                base_bal = pair['base_balance']
                # Sell 20% of holding
                trade_amount = base_bal * 0.2
                
                if trade_amount < 0.00001: return {}

                if self.dry_run:
                    logger.info(f"📝 DRY-RUN: SELL {trade_amount:.4f} {pair['base']} (Γ={coherence:.4f})")
                    return {'dry_run': False}
                    
                logger.info(f"🚀 LIVE: SELL {trade_amount:.4f} {pair['base']} (Γ={coherence:.4f})")
                return self.client.place_market_order(symbol, 'SELL', quantity=trade_amount)
                
        except Exception as e:
            logger.error(f"❌ Trade failed for {symbol}: {e}")
            return {'error': str(e)}
        return {}

    def run(self, duration_sec: int = 3600):
        logger.info(f"\n🚀 Starting MESH trading for {duration_sec}s...")
        start_time = time.time()
        cycle = 0
        
        while time.time() - start_time < duration_sec:
            cycle += 1
            logger.info(f"\n🔄 Cycle {cycle} ({int(time.time() - start_time)}s elapsed)")
            
            pairs = self.discover_tradeable_pairs()
            random.shuffle(pairs)
            
            # Check top 20 pairs to avoid rate limits
            for pair in pairs[:20]:
                symbol = pair['symbol']
                snapshot = self.get_market_snapshot(symbol)
                if not snapshot: continue
                
                state = self.master_eq.compute_lambda(symbol, snapshot)
                coherence = state['coherence']
                
                if state['entry_signal'] and pair['can_buy']:
                    logger.info(f"🎯 {symbol}: BUY Signal (Γ={coherence:.4f})")
                    self.execute_mesh_trade(pair, 'BUY', coherence)
                    
                elif state['exit_signal'] and pair['can_sell']:
                    logger.info(f"🚪 {symbol}: SELL Signal (Γ={coherence:.4f})")
                    self.execute_mesh_trade(pair, 'SELL', coherence)
            
            time.sleep(5)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--duration', type=int, default=3600)
    args = parser.parse_args()
    
    if not args.dry_run:
        if os.getenv('CONFIRM_LIVE', '').lower() != 'yes':
            logger.error("❌ Set CONFIRM_LIVE=yes for live trading")
            sys.exit(1)
        logger.warning("⚠️  LIVE TRADING MODE - Real capital at risk!")
    
    trader = MeshTrader(dry_run=args.dry_run)
    trader.run(duration_sec=args.duration)

if __name__ == "__main__":
    main()
