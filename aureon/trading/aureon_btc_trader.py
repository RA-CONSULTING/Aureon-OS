#!/usr/bin/env python3
"""
🌊 AUREON QGITA ENGINE - BTC PAIRS MODE 🌊

Your account (TRD_GRP_039) can only trade BTC pairs, not USDT pairs!

Strategy:
  - Sell altcoins via BTC pairs (LINKBTC, ADABTC, etc.)
  - Trade BTC pairs for compounding
  - Use the 9 Auris Nodes for entry/exit signals

Author: Gary Leckey / Aureon System
"""
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os, sys, time, logging, argparse, random, math
from datetime import datetime
from typing import Dict, List, Optional
from decimal import Decimal, ROUND_DOWN
from aureon.exchanges.binance_client import BinanceClient, get_binance_client

# 🪙 PENNY PROFIT ENGINE
try:
    from aureon.trading.penny_profit_engine import check_penny_exit, get_penny_engine
    PENNY_PROFIT_AVAILABLE = True
    _penny_engine = get_penny_engine()
    print("🪙 Penny Profit Engine loaded for BTC Trader")
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
except:
    pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('aureon_btc.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

CONFIG = {
    'ACCOUNT_GROUP': 'TRD_GRP_039',  # Your trading group
    'MIN_BTC_VALUE': 0.0001,         # Minimum trade size in BTC (~$10)
    'MAX_POSITIONS': 8,
    'STOP_LOSS_PCT': 0.015,          # 1.5%
    'TAKE_PROFIT_PCT': 0.025,        # 2.5%
}

# ═══════════════════════════════════════════════════════════════════════════
# LOT SIZE MANAGER
# ═══════════════════════════════════════════════════════════════════════════

class LotSizeManager:
    def __init__(self, client: BinanceClient):
        self.client = client
        self.symbol_info = {}
        self.last_update = 0
        self.account_group = CONFIG['ACCOUNT_GROUP']
    
    def update(self):
        if time.time() - self.last_update < 300:
            return
        try:
            info = self.client.exchange_info()
            for s in info.get('symbols', []):
                symbol = s['symbol']
                perms = s.get('permissionSets', [[]])
                can_trade = any(self.account_group in pset for pset in perms)
                
                self.symbol_info[symbol] = {
                    'status': s.get('status'),
                    'base': s.get('baseAsset'),
                    'quote': s.get('quoteAsset'),
                    'can_trade': can_trade,
                    'filters': {},
                }
                for f in s.get('filters', []):
                    self.symbol_info[symbol]['filters'][f['filterType']] = f
            self.last_update = time.time()
            logger.info(f"📊 Loaded {len(self.symbol_info)} symbols")
        except Exception as e:
            logger.error(f"❌ Failed to load exchange info: {e}")
    
    def can_trade(self, symbol: str) -> bool:
        self.update()
        info = self.symbol_info.get(symbol, {})
        # If permission sets are missing, allow BTC quote symbols by default for this account group
        if 'can_trade' not in info:
            return info.get('quote') == 'BTC' and info.get('status') == 'TRADING'
        return info.get('can_trade', False) and info.get('status') == 'TRADING'
    
    def get_step_size(self, symbol: str) -> float:
        self.update()
        lot = self.symbol_info.get(symbol, {}).get('filters', {}).get('LOT_SIZE', {})
        return float(lot.get('stepSize', '0.00000001'))
    
    def get_min_qty(self, symbol: str) -> float:
        self.update()
        lot = self.symbol_info.get(symbol, {}).get('filters', {}).get('LOT_SIZE', {})
        return float(lot.get('minQty', '0.00000001'))
    
    def format_qty(self, symbol: str, qty: float) -> str:
        step = self.get_step_size(symbol)
        min_qty = self.get_min_qty(symbol)
        
        if step >= 1:
            precision = 0
        else:
            precision = len(str(step).rstrip('0').split('.')[-1])
        
        qty_d = Decimal(str(qty))
        step_d = Decimal(str(step))
        formatted = (qty_d // step_d) * step_d
        formatted = max(Decimal(str(min_qty)), formatted)
        
        if precision == 0:
            return str(int(formatted))
        return f"{formatted:.{precision}f}"

# ═══════════════════════════════════════════════════════════════════════════
# MAIN TRADER
# ═══════════════════════════════════════════════════════════════════════════

class AureonBTCTrader:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.client = get_binance_client()
        self.lot_mgr = LotSizeManager(self.client)
        self.positions = {}
        self.total_profit_btc = 0.0
        self.ticker_cache = {}
        self.last_ticker_update = 0
    
    def update_tickers(self):
        if time.time() - self.last_ticker_update < 2:
            return
        try:
            tickers = self.client.session.get(f"{self.client.base}/api/v3/ticker/24hr").json()
            self.ticker_cache = {t['symbol']: t for t in tickers}
            self.last_ticker_update = time.time()
        except Exception as e:
            logger.error(f"❌ Ticker update failed: {e}")
    
    def get_btc_price(self) -> float:
        if 'BTCUSDT' not in self.ticker_cache:
            self.update_tickers()
        ticker = self.ticker_cache.get('BTCUSDT', {})
        return float(ticker.get('lastPrice', 91000))
    
    def get_balances(self) -> Dict[str, float]:
        account = self.client.account()
        balances = {}
        for b in account['balances']:
            free = float(b['free'])
            if free > 0:
                balances[b['asset']] = free
        return balances
    
    def liquidate_altcoins_to_btc(self):
        """Sell all altcoins via BTC pairs to consolidate into BTC"""
        logger.info("\n🔄 LIQUIDATING ALTCOINS TO BTC...")
        
        balances = self.get_balances()
        btc_price = self.get_btc_price()
        
        # Known alts from your portfolio
        alts_to_sell = ['LINK', 'ADA', 'DOT', 'AXS', 'SKL', 'PHA', 'ZKC']
        
        for asset in alts_to_sell:
            if asset not in balances or balances[asset] <= 0:
                continue
            
            symbol = f"{asset}BTC"
            
            if not self.lot_mgr.can_trade(symbol):
                logger.warning(f"⚠️ Cannot trade {symbol}")
                continue
            
            qty = balances[asset]
            ticker = self.ticker_cache.get(symbol, {})
            price = float(ticker.get('lastPrice', 0))
            
            if price <= 0:
                continue
            
            btc_value = qty * price
            usd_value = btc_value * btc_price
            
            if btc_value < CONFIG['MIN_BTC_VALUE']:
                logger.info(f"⏭️ {asset}: {qty:.4f} (~${usd_value:.2f}) too small, skipping")
                continue
            
            qty_str = self.lot_mgr.format_qty(symbol, qty)
            
            logger.info(f"💰 SELLING {symbol}: {qty_str} @ {price:.8f} BTC (~${usd_value:.2f})")
            
            if self.dry_run:
                logger.info(f"📝 DRY-RUN: Would sell {qty_str} {asset}")
            else:
                try:
                    result = self.client.place_market_order(symbol, 'SELL', quantity=float(qty_str))
                    logger.info(f"✅ Sold {symbol}: {result.get('orderId', 'OK')}")
                    self.total_profit_btc += btc_value * 0.001  # Assume tiny gain from spread
                except Exception as e:
                    logger.error(f"❌ Sell failed {symbol}: {e}")
            
            time.sleep(0.2)  # Rate limit
    
    def scan_btc_pairs(self):
        """Find BTC pairs we can trade and look for opportunities"""
        logger.info("\n🔍 SCANNING TRADEABLE BTC PAIRS...")
        
        self.lot_mgr.update()
        
        tradeable = []
        for symbol, info in self.lot_mgr.symbol_info.items():
            if info.get('can_trade') and info.get('quote') == 'BTC' and info.get('status') == 'TRADING':
                tradeable.append(symbol)
        
        logger.info(f"📊 Found {len(tradeable)} tradeable BTC pairs")
        
        # Get top movers
        btc_pairs = []
        for symbol in tradeable:
            ticker = self.ticker_cache.get(symbol, {})
            try:
                change = float(ticker.get('priceChangePercent', 0))
                volume = float(ticker.get('quoteVolume', 0))
                if volume > 1.0:  # At least 1 BTC volume
                    btc_pairs.append({
                        'symbol': symbol,
                        'change': change,
                        'volume': volume,
                        'price': float(ticker.get('lastPrice', 0)),
                    })
            except:
                continue
        
        # Sort by absolute change (volatility)
        btc_pairs.sort(key=lambda x: abs(x['change']), reverse=True)
        
        # Show top 10
        logger.info("\n📈 TOP MOVERS (BTC PAIRS):")
        for p in btc_pairs[:10]:
            emoji = "🟢" if p['change'] > 0 else "🔴"
            logger.info(f"  {emoji} {p['symbol']}: {p['change']:+.2f}% | Vol: {p['volume']:.2f} BTC")
        
        return btc_pairs
    
    def trade_btc_pairs(self, pairs: List[Dict]):
        """Enter positions on high-momentum BTC pairs"""
        balances = self.get_balances()
        btc_balance = balances.get('BTC', 0)
        btc_price = self.get_btc_price()
        
        logger.info(f"\n💎 BTC Balance: {btc_balance:.8f} (~${btc_balance * btc_price:.2f})")
        
        if btc_balance < CONFIG['MIN_BTC_VALUE']:
            logger.warning("⚠️ Not enough BTC to trade")
            return
        
        # Look for entry opportunities
        for p in pairs[:20]:
            if len(self.positions) >= CONFIG['MAX_POSITIONS']:
                break
            
            symbol = p['symbol']
            if symbol in self.positions:
                continue

            # Skip if the exchange flags the symbol as untradeable for this account
            if not self.lot_mgr.can_trade(symbol):
                continue
            
            # Entry logic: Strong momentum (positive OR negative for scalping)
            if abs(p['change']) > 5.0 and p['volume'] > 2.0:  # >5% move, >2 BTC volume
                size_btc = btc_balance * 0.25  # 25% of BTC per trade
                if size_btc < CONFIG['MIN_BTC_VALUE']:
                    size_btc = min(btc_balance * 0.9, CONFIG['MIN_BTC_VALUE'] * 1.5)
                
                # Calculate quantity
                # MUST use endswith() — .replace() corrupts symbols like BTCB
                base = symbol[:-3] if symbol.endswith('BTC') else symbol
                qty = size_btc / p['price']
                qty_str = self.lot_mgr.format_qty(symbol, qty)
                
                logger.info(f"🎯 BUY {symbol}: {qty_str} @ {p['price']:.8f} ({p['change']:+.2f}%)")
                
                if self.dry_run:
                    logger.info(f"📝 DRY-RUN: Would buy {qty_str} {base}")
                    self.positions[symbol] = {
                        'entry': p['price'],
                        'qty': float(qty_str),
                        'entry_time': time.time(),
                    }
                    btc_balance -= size_btc  # Simulate capital usage
                else:
                    try:
                        result = self.client.place_market_order(symbol, 'BUY', quantity=float(qty_str))
                        self.positions[symbol] = {
                            'entry': p['price'],
                            'qty': float(qty_str),
                            'entry_time': time.time(),
                        }
                        logger.info(f"✅ Bought {symbol}: {result.get('orderId', 'OK')}")
                        btc_balance -= size_btc
                    except Exception as e:
                        logger.error(f"❌ Buy failed {symbol}: {e}")
                
                time.sleep(0.2)
    
    def check_exits(self):
        """Check positions for TP/SL exits using penny profit"""
        for symbol in list(self.positions.keys()):
            pos = self.positions[symbol]
            ticker = self.ticker_cache.get(symbol, {})
            price = float(ticker.get('lastPrice', 0))
            
            if price <= 0:
                continue
            
            # Track cycles for min hold time
            pos['cycles'] = pos.get('cycles', 0) + 1
            
            entry = pos['entry']
            pnl_pct = (price - entry) / entry
            current_value = pos['qty'] * price
            entry_value = pos.get('entry_value', pos['qty'] * entry)
            gross_pnl = current_value - entry_value
            
            should_exit = False
            reason = ""
            
            # 🪙 PENNY PROFIT EXIT LOGIC
            if PENNY_PROFIT_AVAILABLE and _penny_engine is not None:
                action, _ = check_penny_exit('binance', entry_value, current_value)
                threshold = _penny_engine.get_threshold('binance', entry_value)
                
                if action == 'TAKE_PROFIT':
                    should_exit = True
                    reason = f"🪙 PENNY TP (${gross_pnl:.4f} >= ${threshold.win_gte:.4f})"
                elif action == 'STOP_LOSS' and pos['cycles'] >= 5:
                    should_exit = True
                    reason = f"🪙 PENNY SL (${gross_pnl:.4f} <= ${threshold.stop_lte:.4f})"
            else:
                # Fallback to percentage exits
                if pnl_pct >= CONFIG['TAKE_PROFIT_PCT']:
                    should_exit = True
                    reason = f"💰 TP (+{pnl_pct*100:.2f}%)"
                elif pnl_pct <= -CONFIG['STOP_LOSS_PCT'] and pos['cycles'] >= 5:
                    should_exit = True
                    reason = f"🛑 SL ({pnl_pct*100:.2f}%)"
            
            # Stagnation check (keep this)
            if not should_exit and time.time() - pos['entry_time'] > 3600:
                should_exit = True
                reason = f"⏰ STAGNATION ({pnl_pct*100:.2f}%)"
            
            if should_exit:
                logger.info(f"⚡ EXIT {symbol}: {reason}")
                
                qty_str = self.lot_mgr.format_qty(symbol, pos['qty'])
                
                if self.dry_run:
                    logger.info(f"📝 DRY-RUN: Would sell {qty_str}")
                else:
                    try:
                        result = self.client.place_market_order(symbol, 'SELL', quantity=float(qty_str))
                        logger.info(f"✅ Sold {symbol}: {result.get('orderId', 'OK')}")
                        self.total_profit_btc += pos['qty'] * price * pnl_pct
                    except Exception as e:
                        logger.error(f"❌ Sell failed {symbol}: {e}")
                
                del self.positions[symbol]
    
    def run(self, duration_sec: int = 3600):
        logger.info("""
╔════════════════════════════════════════════════════════════╗
║           🌊 AUREON BTC PAIRS TRADER 🌊                    ║
║                                                            ║
║  Your account (TRD_GRP_039) trades BTC pairs only!         ║
║                                                            ║
║  Strategy:                                                 ║
║    1. Liquidate altcoins → BTC                             ║
║    2. Trade high-momentum BTC pairs                        ║
║    3. Compound gains in BTC                                ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
        """)
        
        # Initial liquidation
        self.update_tickers()
        self.liquidate_altcoins_to_btc()
        
        start = time.time()
        cycle = 0
        
        while time.time() - start < duration_sec:
            cycle += 1
            
            btc_price = self.get_btc_price()
            logger.info(f"\n🔄 Cycle {cycle} | Positions: {len(self.positions)} | Profit: {self.total_profit_btc:.8f} BTC (~${self.total_profit_btc * btc_price:.2f})")
            
            self.update_tickers()
            
            # Check exits first
            self.check_exits()
            
            # Scan and trade
            pairs = self.scan_btc_pairs()
            self.trade_btc_pairs(pairs)
            
            time.sleep(5)  # 5 second cycles
        
        logger.info(f"\n🏁 Session complete. Total profit: {self.total_profit_btc:.8f} BTC")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--duration', type=int, default=3600)
    args = parser.parse_args()
    
    if not args.dry_run:
        if os.getenv('CONFIRM_LIVE', '').lower() != 'yes':
            logger.error("❌ Set CONFIRM_LIVE=yes for live trading")
            sys.exit(1)
        logger.warning("⚠️  LIVE TRADING - REAL MONEY")
    
    trader = AureonBTCTrader(dry_run=args.dry_run)
    trader.run(duration_sec=args.duration)

if __name__ == "__main__":
    main()
