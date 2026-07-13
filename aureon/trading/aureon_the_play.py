#!/usr/bin/env python3
"""
💰 AUREON: THE PLAY - COHERENCE-BASED TRADING SYSTEM 💰
"Master Equation Λ(t) = S(t) + O(t) + E(t)"
"Light Speed Mode: Entry 0.938 | Exit 0.934"

Strategy:
  - Master Equation detects market coherence (Γ)
  - 9 Auris Nodes perceive different market aspects
  - Entry: Γ > 0.938 (Heart Coherence/528 Hz Love)
  - Exit: Γ < 0.934 OR ±0.8% SL / 1.8% TP
  - A-Z/Z-A Sweep eliminates bias
  - Compounding: Reinvest profits immediately

Author: Gary Leckey / Aureon System
Date: November 28, 2025
"""
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os, sys, json, time, logging, argparse, random, math
from datetime import datetime
from typing import List, Dict, Any
from aureon.exchanges.binance_client import BinanceClient, get_binance_client

# 🪙 PENNY PROFIT ENGINE
try:
    from aureon.trading.penny_profit_engine import check_penny_exit, get_penny_engine
    PENNY_PROFIT_AVAILABLE = True
    _penny_engine = get_penny_engine()
    print("🪙 Penny Profit Engine loaded for The Play")
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

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('the_play.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION (AUREON PARAMETERS)
# ═══════════════════════════════════════════════════════════════════════════

CONFIG = {
    'ENTRY_COHERENCE': 0.938,     # Buy when Γ > this (Heart Coherence)
    'EXIT_COHERENCE': 0.934,      # Sell when Γ < this (Coherence Break)
    'STOP_LOSS_PCT': 0.008,       # 0.8% - Hard Stop
    'TAKE_PROFIT_PCT': 0.018,     # 1.8% - Quick Profit
    'KELLY_FRACTION': 0.4,        # Very Aggressive Kelly
    'MAX_POSITIONS': 10,          # Concurrent positions
    'FEE_PCT': 0.002,             # 0.2% round trip
    'SCAN_BATCH_SIZE': 100,       # Scan 100 pairs per cycle
    'LOVE_FREQUENCY': 528,        # Hz - Pure Love
}

# ═══════════════════════════════════════════════════════════════════════════
# 9 AURIS NODES (EXACT SPECIFICATIONS FROM README)
# ═══════════════════════════════════════════════════════════════════════════

class AurisNode:
    def __init__(self, name: str, emoji: str, weight: float, compute_fn):
        self.name = name
        self.emoji = emoji
        self.weight = weight
        self.compute_fn = compute_fn

    def compute(self, snap: Dict) -> float:
        try:
            val = self.compute_fn(snap)
            return max(0.0, min(val, 1.0))  # Clamp to [0, 1]
        except:
            return 0.0

def create_auris_nodes():
    """Create the 9 Auris Nodes with exact weights and formulas from AUREON"""
    return [
        AurisNode('Tiger', '🐯', 1.2, 
                  lambda s: s['volatility'] * 0.8 + s['spread'] * 0.5),
        AurisNode('Falcon', '🦅', 1.1, 
                  lambda s: abs(s['momentum']) * 0.7 + s['volume_norm'] * 0.3),
        AurisNode('Hummingbird', '🐦', 0.8, 
                  lambda s: 1 / (s['volatility'] + 0.01) * 0.6),
        AurisNode('Dolphin', '🐬', 1.0, 
                  lambda s: math.sin(s['momentum'] * math.pi) * 0.5),
        AurisNode('Deer', '🦌', 0.9, 
                  lambda s: s['volume_norm'] * 0.2 + s['volatility'] * 0.3 + s['spread'] * 0.2),
        AurisNode('Owl', '🦉', 1.0, 
                  lambda s: math.cos(s['momentum'] * math.pi) * 0.6 + (0.3 if s['momentum'] < 0 else 0)),
        AurisNode('Panda', '🐼', 0.95, 
                  lambda s: s['volume_norm'] * 0.8 if s['volume_norm'] > 0.7 else 0.2),
        AurisNode('CargoShip', '🚢', 1.3, 
                  lambda s: s['volume_norm'] * 1.2 if s['volume_norm'] > 0.8 else 0),
        AurisNode('Clownfish', '🐠', 0.7, 
                  lambda s: 0.5),  # Micro-change detection
    ]

# ═══════════════════════════════════════════════════════════════════════════
# MASTER EQUATION: Λ(t) = S(t) + O(t) + E(t)
# ═══════════════════════════════════════════════════════════════════════════

class MasterEquation:
    """
    Λ(t) = S(t) + O(t) + E(t)
    
    Where:
      Λ(t) = Lambda - The unified field state at time t
      S(t) = Substrate - 9 Auris nodes respond to market
      O(t) = Observer - Self-referential field awareness
      E(t) = Echo - Memory and momentum from history
      
    Coherence: Γ = 1 - (variance / 10)
    Output Frequency: f = LOVE_FREQUENCY when Γ > 0.9
    """
    def __init__(self):
        self.nodes = create_auris_nodes()
        self.lambda_history = {}  # symbol -> [Λ values]
        self.coherence_history = {}

    def compute_coherence(self, symbol: str, snap: Dict) -> float:
        """
        Compute coherence using Master Equation framework.
        Returns Γ ∈ [0, 1]
        """
        # S(t): Substrate - Weighted average of 9 Auris nodes
        total_val = 0.0
        total_weight = 0.0
        
        for node in self.nodes:
            val = node.compute(snap)
            total_val += val * node.weight
            total_weight += node.weight
        
        s_t = (total_val / total_weight) * 0.5 if total_weight > 0 else 0.0
        
        # O(t): Observer - Self-referential previous state
        lambda_history = self.lambda_history.get(symbol, [])
        last_lambda = lambda_history[-1] if lambda_history else 0.5
        o_t = last_lambda * 0.3
        
        # E(t): Echo - Memory from last 5 states
        if len(lambda_history) >= 5:
            e_t = sum(lambda_history[-5:]) / 5.0 * 0.2
        else:
            e_t = 0.1  # Placeholder
        
        # Master Equation: Λ(t) = S(t) + O(t) + E(t)
        lambda_t = s_t + o_t + e_t
        
        # Store in history
        if symbol not in self.lambda_history:
            self.lambda_history[symbol] = []
        self.lambda_history[symbol].append(lambda_t)
        
        # Keep only last 10 values
        if len(self.lambda_history[symbol]) > 10:
            self.lambda_history[symbol].pop(0)
        
        # Coherence: Γ = normalized lambda
        coherence = min(max(lambda_t, 0.0), 1.0)
        
        # Store coherence
        if symbol not in self.coherence_history:
            self.coherence_history[symbol] = []
        self.coherence_history[symbol].append(coherence)
        
        return coherence

    def get_frequency(self, coherence: float) -> float:
        """
        Rainbow Bridge: Map coherence to frequency
        High coherence (>0.9) locks to 528 Hz (Love Frequency)
        """
        base_freq = 110 + (coherence * 100)
        love_freq = CONFIG['LOVE_FREQUENCY']
        
        # Blend toward love frequency with increasing coherence
        frequency = base_freq * (1 - coherence * 0.3) + love_freq * (coherence * 0.3)
        return frequency

# ═══════════════════════════════════════════════════════════════════════════
# TRADER
# ═══════════════════════════════════════════════════════════════════════════

class AureonThePlayTrader:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.client = get_binance_client()
        self.master_eq = MasterEquation()
        self.positions = {}
        self.total_profit = 0.0
        self.scan_direction = 'AZ'
        self.ticker_cache = {}
        self.last_ticker_update = 0
        self.load_existing_positions()

    def load_existing_positions(self):
        """Load existing balances as positions to manage."""
        logger.info("🔍 Scanning for existing holdings...")
        try:
            account = self.client.account()
            for b in account['balances']:
                asset = b['asset']
                free = float(b['free'])
                if free > 0:
                    try:
                        if asset in ['USDT', 'BUSD', 'USDC', 'LDUSDC']:
                            price = 1.0
                            symbol = asset
                        else:
                            symbol = f"{asset}USDT"
                            ticker = self.client.session.get(f"{self.client.base}/api/v3/ticker/price", params={'symbol': symbol}).json()
                            if 'price' not in ticker: continue
                            price = float(ticker['price'])
                        
                        value = free * price
                        if value > 5.0:
                            logger.info(f"✅ Found existing bag: {asset} ({free:.4f}) ~ ${value:.2f}")
                            if asset == 'LDUSDC': continue
                            
                            trade_symbol = symbol if asset != 'USDT' else None
                            
                            if trade_symbol:
                                self.positions[trade_symbol] = {
                                    'entry_price': price,
                                    'size': free,
                                    'quote': 'USDT',
                                    'entry_time': time.time(),
                                    'is_existing': True,
                                    'entry_coherence': 0.5
                                }
                    except Exception as e:
                        continue
            logger.info(f"📊 Loaded {len(self.positions)} existing positions.")
        except Exception as e:
            logger.error(f"❌ Failed to load positions: {e}")

    def update_ticker_cache(self):
        """Fetch all tickers at once to save API calls."""
        try:
            if time.time() - self.last_ticker_update < 2: return
            
            tickers = self.client.session.get(f"{self.client.base}/api/v3/ticker/24hr").json()
            self.ticker_cache = {t['symbol']: t for t in tickers}
            self.last_ticker_update = time.time()
        except Exception as e:
            logger.error(f"❌ Failed to update ticker cache: {e}")

    def get_market_snapshot(self, symbol: str) -> Dict:
        try:
            ticker = self.ticker_cache.get(symbol)
            if not ticker:
                ticker = self.client.session.get(f"{self.client.base}/api/v3/ticker/24hr", params={'symbol': symbol}).json()
            
            price = float(ticker['lastPrice'])
            high = float(ticker['highPrice'])
            low = float(ticker['lowPrice'])
            volume = float(ticker['quoteVolume'])
            change = float(ticker['priceChangePercent'])
            
            volatility = (high - low) / price if price > 0 else 0
            momentum = change / 100
            volume_norm = min(volume / 1000000, 1.0)
            spread = 0.001
            
            return {
                'price': price,
                'volatility': volatility,
                'momentum': momentum,
                'volume_norm': volume_norm,
                'spread': spread
            }
        except:
            return None

    def get_tradeable_pairs(self) -> List[Dict]:
        account = self.client.account()
        balances = {b['asset']: float(b['free']) for b in account['balances'] if float(b['free']) > 0.01}
        info = self.client.exchange_info()
        pairs = []
        
        all_symbols = info.get('symbols', [])
        if self.scan_direction == 'AZ':
            all_symbols.sort(key=lambda x: x['symbol'])
        else:
            all_symbols.sort(key=lambda x: x['symbol'], reverse=True)
            
        for s in all_symbols:
            if s['status'] != 'TRADING': continue
            base = s['baseAsset']
            quote = s['quoteAsset']
            symbol = s['symbol']
            
            can_buy = quote in balances and balances[quote] > 0.01
            
            if can_buy:
                pairs.append({
                    'symbol': symbol,
                    'base': base,
                    'quote': quote,
                    'balance': balances[quote]
                })
        return pairs

    def kelly_size(self, balance: float, quote_symbol: str) -> float:
        # Kelly Criterion: k = (win% - loss%) / win_ratio
        win_prob = 0.853  # From AUREON specs: 85.3% win rate
        win_ratio = 1.8 / 0.8  # TP/SL = 1.8/0.8 = 2.25
        k = win_prob - (1 - win_prob) / win_ratio
        k = max(0.0, k) * CONFIG['KELLY_FRACTION']
        
        size = balance * k
        
        try:
            if quote_symbol == 'USDT':
                price = 1.0
            elif quote_symbol in ['LDUSDC', 'USDC', 'BUSD']:
                price = 1.0
            else:
                ticker = self.client.session.get(f"{self.client.base}/api/v3/ticker/price", params={'symbol': f"{quote_symbol}USDT"}).json()
                if 'price' not in ticker:
                    return 0.0
                price = float(ticker['price'])
            
            value_usd = size * price
            
            if value_usd < 6.0:
                if balance * price > 6.0:
                    required_qty = 6.0 / price
                    return round(required_qty, 4)
                else:
                    return 0.0
                    
            return round(size, 4)
        except Exception as e:
            logger.error(f"❌ Kelly Size Error: {e}")
            return round(max(size, 6.0), 4) if quote_symbol == 'USDT' else round(size, 4)

    def run(self, duration_sec: int = 3600):
        logger.info(f"\n🚀 AUREON: THE PLAY TRADER")
        logger.info(f"📊 Master Equation: Λ(t) = S(t) + O(t) + E(t)")
        logger.info(f"💚 Entry: Γ > 0.938 | Exit: Γ < 0.934 | TP 1.8% | SL 0.8%")
        logger.info(f"⚡ Light Speed: {CONFIG['SCAN_BATCH_SIZE']} pairs | A-Z/Z-A Sweep")
        
        start_time = time.time()
        cycle = 0
        
        while time.time() - start_time < duration_sec:
            cycle += 1
            self.scan_direction = 'ZA' if self.scan_direction == 'AZ' else 'AZ'
            
            logger.info(f"\n🔄 Cycle {cycle} | Direction: {self.scan_direction} | Positions: {len(self.positions)} | Profit: ${self.total_profit:+.2f}")
            
            # Update Ticker Cache
            self.update_ticker_cache()
            
            # 1. Check Exits (Coherence + Profit Targets)
            self.check_exits()
            
            # 2. Scan and Enter (High Coherence = 528 Hz Love Frequency)
            if len(self.positions) < CONFIG['MAX_POSITIONS']:
                pairs = self.get_tradeable_pairs()
                scan_pairs = pairs[:CONFIG['SCAN_BATCH_SIZE']]
                
                for pair in scan_pairs:
                    if len(self.positions) >= CONFIG['MAX_POSITIONS']: break
                    if pair['symbol'] in self.positions: continue
                    
                    snap = self.get_market_snapshot(pair['symbol'])
                    if not snap: continue
                    
                    coherence = self.master_eq.compute_coherence(pair['symbol'], snap)
                    freq = self.master_eq.get_frequency(coherence)
                    
                    # Entry Logic: Γ > 0.938 (Heart Coherence)
                    if coherence > CONFIG['ENTRY_COHERENCE']:
                        size = self.kelly_size(pair['balance'], pair['quote'])
                        if size <= 0.0: continue
                        
                        if size > pair['balance']: size = pair['balance']
                        
                        logger.info(f"🎯 {pair['symbol']}: BUY (Γ={coherence:.4f} | f={freq:.0f}Hz) | Size: {size:.4f}")
                        
                        if self.dry_run:
                            logger.info(f"📝 DRY-RUN: BUY {pair['symbol']}")
                            self.positions[pair['symbol']] = {
                                'entry_price': snap['price'],
                                'size': size,
                                'quote': pair['quote'],
                                'entry_time': time.time(),
                                'entry_coherence': coherence
                            }
                        else:
                            logger.info(f"🚀 LIVE BUY: {pair['symbol']}")
                            try:
                                res = self.client.place_market_order(pair['symbol'], 'BUY', quote_qty=size)
                                self.positions[pair['symbol']] = {
                                    'entry_price': snap['price'],
                                    'size': size,
                                    'quote': pair['quote'],
                                    'entry_time': time.time(),
                                    'entry_coherence': coherence
                                }
                            except Exception as e:
                                logger.error(f"❌ Buy failed: {e}")

    def check_exits(self):
        for symbol in list(self.positions.keys()):
            pos = self.positions[symbol]
            snap = self.get_market_snapshot(symbol)
            if not snap: continue
            
            # Track cycles for min hold time
            pos['cycles'] = pos.get('cycles', 0) + 1
            
            curr_price = snap['price']
            entry_price = pos['entry_price']
            pnl_pct = (curr_price - entry_price) / entry_price
            current_value = pos.get('qty', 0) * curr_price
            entry_value = pos.get('entry_value', pos.get('qty', 0) * entry_price)
            gross_pnl = current_value - entry_value
            
            coherence = self.master_eq.compute_coherence(symbol, snap)
            freq = self.master_eq.get_frequency(coherence)
            
            # Log status occasionally
            if random.random() < 0.05:
                logger.info(f"📊 {symbol}: Γ={coherence:.4f} f={freq:.0f}Hz | PnL {pnl_pct*100:.2f}%")
            
            # 🪙 PENNY PROFIT EXIT LOGIC (priority over coherence)
            if PENNY_PROFIT_AVAILABLE and _penny_engine is not None and entry_value > 0:
                action, _ = check_penny_exit('binance', entry_value, current_value)
                threshold = _penny_engine.get_threshold('binance', entry_value)
                
                if action == 'TAKE_PROFIT':
                    logger.info(f"🪙 {symbol}: PENNY TP (${gross_pnl:.4f} >= ${threshold.win_gte:.4f})")
                    self.close_position(symbol, pos, curr_price, pnl_pct)
                elif action == 'STOP_LOSS' and pos['cycles'] >= 5:
                    logger.info(f"🪙 {symbol}: PENNY SL (${gross_pnl:.4f} <= ${threshold.stop_lte:.4f})")
                    self.close_position(symbol, pos, curr_price, pnl_pct)
                elif coherence < CONFIG['EXIT_COHERENCE'] and pos['cycles'] >= 5:
                    logger.info(f"⚡ {symbol}: COHERENCE EXIT (Γ={coherence:.4f} < 0.934)")
                    self.close_position(symbol, pos, curr_price, pnl_pct)
            else:
                # Fallback: Exit 1 - Coherence Break
                if coherence < CONFIG['EXIT_COHERENCE'] and pos['cycles'] >= 5:
                    logger.info(f"⚡ {symbol}: COHERENCE EXIT (Γ={coherence:.4f} < 0.934)")
                    self.close_position(symbol, pos, curr_price, pnl_pct)
                    
                # Exit 2: Take Profit
                elif pnl_pct >= CONFIG['TAKE_PROFIT_PCT']:
                    logger.info(f"💰 {symbol}: TAKE PROFIT (+{pnl_pct*100:.2f}%)")
                    self.close_position(symbol, pos, curr_price, pnl_pct)
                    
                # Exit 3: Stop Loss (with min hold)
                elif pnl_pct <= -CONFIG['STOP_LOSS_PCT'] and pos['cycles'] >= 5:
                    logger.info(f"🛑 {symbol}: STOP LOSS ({pnl_pct*100:.2f}%)")
                    self.close_position(symbol, pos, curr_price, pnl_pct)

    def close_position(self, symbol, pos, price, pnl_pct):
        if self.dry_run:
            logger.info(f"📝 DRY-RUN: SELL {symbol}")
        else:
            logger.info(f"🚀 LIVE SELL: {symbol}")
            try:
                if symbol.endswith('USDT'):
                    base = symbol[:-4]
                elif symbol.endswith('BTC'):
                    base = symbol[:-3]
                elif symbol.endswith('BNB'):
                    base = symbol[:-3]
                elif symbol.endswith('ETH'):
                    base = symbol[:-3]
                elif symbol.endswith('DOGE'):
                    base = symbol[:-4]
                else:
                    base = symbol.replace(pos['quote'], '')
                
                bal = self.client.get_free_balance(base)
                val_usd = bal * price
                
                if val_usd < 6.0:
                    logger.warning(f"⚠️ Sell value too low (${val_usd:.2f}), skipping")
                    return

                self.client.place_market_order(symbol, 'SELL', quantity=bal)
            except Exception as e:
                logger.error(f"❌ Sell failed: {e}")
        
        profit = pos['size'] * pnl_pct
        self.total_profit += profit
        if symbol in self.positions:
            del self.positions[symbol]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--duration', type=int, default=3600)
    args = parser.parse_args()
    
    if not args.dry_run:
        if os.getenv('CONFIRM_LIVE', '').lower() != 'yes':
            logger.error("❌ Set CONFIRM_LIVE=yes")
            sys.exit(1)
        logger.warning("⚠️  LIVE TRADING MODE")
        
    trader = AureonThePlayTrader(dry_run=args.dry_run)
    trader.run(duration_sec=args.duration)

if __name__ == "__main__":
    main()
