#!/usr/bin/env python3
"""
💰 THE PLAY: NET PROFIT CYCLE TRADER 💰
"A-Z Z-A Sweep + Kelly Compounding"

Strategy:
  - Sweep market A-Z then Z-A to find opportunities
  - Calculate Coherence (Φ) using 9 Auris Nodes
  - Entry: Low Coherence (Aggressive)
  - Sizing: Kelly Criterion (Monte Carlo optimized)
  - Exit: Strict Profit Target or Stop Loss
  - Compounding: Reinvest all profits immediately

Author: Aureon System / Gary Leckey
Date: November 28, 2025
"""
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os, sys, json, time, logging, argparse, random, math
from datetime import datetime
from typing import List, Dict, Any
from aureon.exchanges.binance_client import BinanceClient, get_binance_client

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
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

CONFIG = {
    'ENTRY_COHERENCE': 0.01,      # ULTRA LOW for aggressive action
    'STOP_LOSS_PCT': 0.005,       # 0.5% - Tight Stop
    'TAKE_PROFIT_PCT': 0.008,     # 0.8% - Quick Scalp
    'KELLY_FRACTION': 0.4,        # Very Aggressive Kelly
    'MAX_POSITIONS': 10,          # More concurrent trades
    'FEE_PCT': 0.002,             # 0.2% round trip
    'STAGNATION_SECONDS': 300,    # 5 minutes max hold if not profitable
    'SCAN_BATCH_SIZE': 100        # Scan more pairs per cycle
}

# ═══════════════════════════════════════════════════════════════════════════
# 9 AURIS NODES
# ═══════════════════════════════════════════════════════════════════════════

class AurisNode:
    def __init__(self, name: str, weight: float, compute_fn):
        self.name = name
        self.weight = weight
        self.compute_fn = compute_fn

    def compute(self, snap: Dict) -> float:
        try:
            return self.compute_fn(snap)
        except:
            return 0.0

def create_nodes():
    return [
        AurisNode('Tiger', 1.2, lambda s: s['volatility'] * 0.8 + s['spread'] * 0.5),
        AurisNode('Falcon', 1.1, lambda s: abs(s['momentum']) * 0.7 + s['volume_norm'] * 0.3),
        AurisNode('Hummingbird', 0.8, lambda s: 1 / (s['volatility'] + 0.01) * 0.6),
        AurisNode('Dolphin', 1.0, lambda s: math.sin(s['momentum']) * 0.5),
        AurisNode('Deer', 0.9, lambda s: s['volume_norm'] * 0.2 + s['volatility'] * 0.3 + s['spread'] * 0.2),
        AurisNode('Owl', 1.0, lambda s: math.cos(s['momentum']) * 0.6 + (0.3 if s['momentum'] < 0 else 0)),
        AurisNode('Panda', 0.95, lambda s: s['volume_norm'] * 0.8 if s['volume_norm'] > 0.7 else 0.2),
        AurisNode('CargoShip', 1.3, lambda s: s['volume_norm'] * 1.2 if s['volume_norm'] > 0.8 else 0),
        AurisNode('Clownfish', 0.7, lambda s: abs(s['price'] - s['price'] * 0.999) * 100),
    ]

# ═══════════════════════════════════════════════════════════════════════════
# MASTER EQUATION
# ═══════════════════════════════════════════════════════════════════════════

class MasterEquation:
    def __init__(self):
        self.nodes = create_nodes()
        self.lambda_history = {}

    def compute_coherence(self, symbol: str, snap: Dict) -> float:
        # S(t) Substrate
        total_val = 0
        total_weight = 0
        for node in self.nodes:
            val = node.compute(snap)
            total_val += val * node.weight
            total_weight += node.weight
        
        s_t = (total_val / total_weight) * 0.5 if total_weight > 0 else 0
        
        # O(t) Observer
        last_lambda = self.lambda_history.get(symbol, 0.5)
        o_t = last_lambda * 0.3
        
        # E(t) Echo (simplified)
        e_t = 0.1  # Placeholder for echo
        
        lambda_t = s_t + o_t + e_t
        self.lambda_history[symbol] = lambda_t
        
        # Coherence is derived from Lambda stability (simplified here to be inverse of variance)
        # For this aggressive strategy, we map lambda directly to coherence potential
        coherence = min(max(lambda_t, 0.0), 1.0)
        return coherence

# ═══════════════════════════════════════════════════════════════════════════
# TRADER
# ═══════════════════════════════════════════════════════════════════════════

class ThePlayTrader:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.client = get_binance_client()
        self.master_eq = MasterEquation()
        self.positions = {}
        self.total_profit = 0.0
        self.scan_direction = 'AZ' # AZ or ZA
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
                    # Check value
                    try:
                        if asset in ['USDT', 'BUSD', 'USDC', 'LDUSDC']:
                            price = 1.0
                            symbol = asset
                        else:
                            # Assume USDT pair for valuation
                            symbol = f"{asset}USDT"
                            ticker = self.client.session.get(f"{self.client.base}/api/v3/ticker/price", params={'symbol': symbol}).json()
                            if 'price' not in ticker: continue
                            price = float(ticker['price'])
                        
                        value = free * price
                        if value > 5.0: # Min threshold (lowered to catch small bags)
                            logger.info(f"✅ Found existing bag: {asset} ({free:.4f}) ~ ${value:.2f}")
                            # We need a trading pair to manage this. Prefer BTC or USDT.
                            # If it's not USDT, we trade against USDT.
                            if asset == 'LDUSDC': continue # Skip Earn assets
                            
                            trade_symbol = symbol if asset != 'USDT' else None
                            
                            if trade_symbol:
                                self.positions[trade_symbol] = {
                                    'entry_price': price, # Use current price as baseline
                                    'size': free,
                                    'quote': 'USDT', # Assumed
                                    'entry_time': time.time(),
                                    'is_existing': True
                                }
                    except Exception as e:
                        continue
            logger.info(f"📊 Loaded {len(self.positions)} existing positions.")
        except Exception as e:
            logger.error(f"❌ Failed to load positions: {e}")

    def update_ticker_cache(self):
        """Fetch all tickers at once to save API calls."""
        try:
            if time.time() - self.last_ticker_update < 2: return # Cache for 2 seconds
            
            tickers = self.client.session.get(f"{self.client.base}/api/v3/ticker/24hr").json()
            self.ticker_cache = {t['symbol']: t for t in tickers}
            self.last_ticker_update = time.time()
        except Exception as e:
            logger.error(f"❌ Failed to update ticker cache: {e}")

    def get_market_snapshot(self, symbol: str) -> Dict:
        try:
            # Use cache if available
            ticker = self.ticker_cache.get(symbol)
            if not ticker:
                # Fallback to direct call
                ticker = self.client.session.get(f"{self.client.base}/api/v3/ticker/24hr", params={'symbol': symbol}).json()
            
            price = float(ticker['lastPrice'])
            high = float(ticker['highPrice'])
            low = float(ticker['lowPrice'])
            volume = float(ticker['quoteVolume'])
            change = float(ticker['priceChangePercent'])
            
            # Derived metrics
            volatility = (high - low) / price if price > 0 else 0
            momentum = change / 100
            volume_norm = min(volume / 1000000, 1.0) # Normalize to 1M USDT
            spread = 0.001 # Estimate
            
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
        # Sort based on scan direction
        if self.scan_direction == 'AZ':
            all_symbols.sort(key=lambda x: x['symbol'])
        else:
            all_symbols.sort(key=lambda x: x['symbol'], reverse=True)
            
        for s in all_symbols:
            if s['status'] != 'TRADING': continue
            base = s['baseAsset']
            quote = s['quoteAsset']
            symbol = s['symbol']
            
            # We can trade if we have quote (BUY) or base (SELL)
            # For "The Play", we focus on BUYING with what we have
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
        # Kelly = W - (1-W)/R
        win_prob = 0.6
        win_ratio = 1.5
        k = win_prob - (1 - win_prob) / win_ratio
        k = max(0.0, k) * CONFIG['KELLY_FRACTION']
        
        # Calculate raw size
        size = balance * k
        
        # Check USD value to ensure min notional
        try:
            # Get quote price in USDT
            if quote_symbol == 'USDT':
                price = 1.0
            elif quote_symbol == 'LDUSDC': # Treat as USDC/USDT
                price = 1.0 
            else:
                ticker = self.client.session.get(f"{self.client.base}/api/v3/ticker/price", params={'symbol': f"{quote_symbol}USDT"}).json()
                if 'price' not in ticker:
                    logger.warning(f"⚠️ Price lookup failed for {quote_symbol}USDT: {ticker}")
                    return 0.0
                price = float(ticker['price'])
            
            value_usd = size * price
            logger.info(f"💰 Kelly Calc: {quote_symbol} | Bal: {balance:.4f} | Price: ${price:.4f} | Size: {size:.4f} | Val: ${value_usd:.2f}")
            
            # If calculated size is too small (< $6)
            if value_usd < 6.0:
                # Check if we have enough balance for min trade
                if balance * price > 6.0:
                    # Bump up to $6 size
                    required_qty = 6.0 / price
                    logger.info(f"⚠️ Bumping size to min notional: {required_qty:.4f} {quote_symbol}")
                    return round(required_qty, 4)
                else:
                    # Balance too low to trade
                    logger.warning(f"⚠️ Balance too low for min notional: ${balance*price:.2f} < $6.00")
                    return 0.0
                    
            return round(size, 4)
        except Exception as e:
            logger.error(f"❌ Kelly Size Error: {e}")
            # Fallback if price check fails: use 6.0 units if USDT, else try to use substantial portion
            return round(max(size, 6.0), 4) if quote_symbol == 'USDT' else round(size, 4)

    def run(self, duration_sec: int = 3600):
        logger.info(f"\n🚀 STARTING 'THE PLAY' TRADER ({self.scan_direction})")
        logger.info(f"Strategy: A-Z/Z-A Sweep | Kelly Compounding | Γ>{CONFIG['ENTRY_COHERENCE']}")
        logger.info(f"⚡ LIGHT SPEED MODE: Batch {CONFIG['SCAN_BATCH_SIZE']} | TP {CONFIG['TAKE_PROFIT_PCT']*100}% | SL {CONFIG['STOP_LOSS_PCT']*100}%")
        
        start_time = time.time()
        cycle = 0
        
        while time.time() - start_time < duration_sec:
            cycle += 1
            # Toggle scan direction every cycle
            self.scan_direction = 'ZA' if self.scan_direction == 'AZ' else 'AZ'
            
            logger.info(f"\n🔄 Cycle {cycle} | Direction: {self.scan_direction} | Positions: {len(self.positions)} | Profit: ${self.total_profit:+.2f}")
            
            # Update Ticker Cache (Bulk Fetch)
            self.update_ticker_cache()
            
            # 1. Check Exits
            self.check_exits()
            
            # 2. Scan and Enter
            if len(self.positions) < CONFIG['MAX_POSITIONS']:
                pairs = self.get_tradeable_pairs()
                # Take top N to scan this cycle
                scan_pairs = pairs[:CONFIG['SCAN_BATCH_SIZE']]
                
                for pair in scan_pairs:
                    if len(self.positions) >= CONFIG['MAX_POSITIONS']: break
                    if pair['symbol'] in self.positions: continue
                    
                    snap = self.get_market_snapshot(pair['symbol'])
                    if not snap: continue
                    
                    coherence = self.master_eq.compute_coherence(pair['symbol'], snap)
                    
                    # Entry Logic
                    if coherence > CONFIG['ENTRY_COHERENCE']:
                        # Calculate Kelly Size
                        size = self.kelly_size(pair['balance'], pair['quote'])
                        if size <= 0.0: continue
                        
                        if size > pair['balance']: size = pair['balance']
                        
                        logger.info(f"🎯 {pair['symbol']}: BUY Signal (Γ={coherence:.3f}) | Size: {size:.4f} {pair['quote']}")
                        
                        if self.dry_run:
                            logger.info(f"📝 DRY-RUN: BUY {pair['symbol']}")
                            self.positions[pair['symbol']] = {
                                'entry_price': snap['price'],
                                'size': size,
                                'quote': pair['quote'],
                                'entry_time': time.time()
                            }
                        else:
                            logger.info(f"🚀 LIVE BUY: {pair['symbol']}")
                            try:
                                res = self.client.place_market_order(pair['symbol'], 'BUY', quote_qty=size)
                                # Assume fill
                                self.positions[pair['symbol']] = {
                                    'entry_price': snap['price'], # Approx
                                    'size': size,
                                    'quote': pair['quote'],
                                    'entry_time': time.time()
                                }
                            except Exception as e:
                                logger.error(f"❌ Buy failed: {e}")

            # No sleep for light speed, just rate limit check implicitly via cache
            # time.sleep(0.1)

    def check_exits(self):
        for symbol in list(self.positions.keys()):
            pos = self.positions[symbol]
            snap = self.get_market_snapshot(symbol)
            if not snap: continue
            
            curr_price = snap['price']
            entry_price = pos['entry_price']
            pnl_pct = (curr_price - entry_price) / entry_price
            duration = time.time() - pos['entry_time']
            
            # Log status occasionally
            if random.random() < 0.05:
                logger.info(f"📊 {symbol}: PnL {pnl_pct*100:.2f}% (Entry: {entry_price:.4f} | Curr: {curr_price:.4f})")
            
            # Take Profit
            if pnl_pct >= CONFIG['TAKE_PROFIT_PCT']:
                logger.info(f"💰 {symbol}: TAKE PROFIT (+{pnl_pct*100:.2f}%)")
                self.close_position(symbol, pos, curr_price, pnl_pct)
                
            # Stop Loss
            elif pnl_pct <= -CONFIG['STOP_LOSS_PCT']:
                logger.info(f"🛑 {symbol}: STOP LOSS ({pnl_pct*100:.2f}%)")
                self.close_position(symbol, pos, curr_price, pnl_pct)
                
            # Stagnation Exit (Jump Jump Jump)
            elif duration > CONFIG['STAGNATION_SECONDS'] and pnl_pct < 0.002:
                logger.info(f"⏱️ {symbol}: STAGNATION EXIT ({duration:.0f}s)")
                self.close_position(symbol, pos, curr_price, pnl_pct)

    def close_position(self, symbol, pos, price, pnl_pct):
        if self.dry_run:
            logger.info(f"📝 DRY-RUN: SELL {symbol}")
        else:
            logger.info(f"🚀 LIVE SELL: {symbol}")
            try:
                # Sell all
                # Need quantity, not quote qty for sell usually, but let's try to get balance first or just sell what we bought
                # Simplified: sell 100% of asset
                # In real implementation need to fetch balance. 
                # For now, assume we sell the value.
                # Better: get balance of base asset
                # Handle cases like SHIBDOGE where quote is DOGE
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
                    # Fallback
                    base = symbol.replace(pos['quote'], '')
                
                bal = self.client.get_free_balance(base)
                
                # Ensure we don't sell dust if it's too small, but we should try
                # Rounding quantity is tricky.
                # For now, try to sell 99% to avoid precision errors or just raw balance
                # Binance usually handles raw balance if it matches step size.
                # Let's try raw balance first.
                
                # Check min notional for sell
                val_usd = bal * price
                if val_usd < 6.0:
                    logger.warning(f"⚠️ Sell value too low (${val_usd:.2f}), skipping sell of {base}")
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
        
    trader = ThePlayTrader(dry_run=args.dry_run)
    trader.run(duration_sec=args.duration)

if __name__ == "__main__":
    main()
