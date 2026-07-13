#!/usr/bin/env python3
"""
AUREON COMPOUND KELLY TRADER
═══════════════════════════════════════════════════════════════════════════════
- Scans all wallet assets, trades A-Z and Z-A
- Low coherence threshold for aggressive entry
- Uses Kelly criterion for position sizing (monte carlo)
- Compounds profits into new trades
- Trades as fast as possible when expected profit > 0.0% after fees

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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('compound_kelly_trader.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class CompoundKellyTrader:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.client = get_binance_client()
        self.fee_pct = 0.002  # 0.2% round-trip
        self.coherence_threshold = 0.05  # Very low for aggressive entry
        self.max_positions = 7
        self.positions = {}
        self.total_profit = 0.0
        self.kelly_fraction = 0.25  # Start with 25% Kelly fraction

    def get_tradeable_pairs(self) -> List[Dict[str, Any]]:
        account = self.client.account()
        balances = {b['asset']: float(b['free']) for b in account['balances'] if float(b['free']) > 0.01}
        info = self.client.exchange_info()
        pairs = []
        # Scan A-Z
        for s in sorted(info.get('symbols', []), key=lambda x: x['symbol']):
            if s['status'] != 'TRADING': continue
            base = s['baseAsset']
            quote = s['quoteAsset']
            symbol = s['symbol']
            can_buy = quote in balances and balances[quote] > 0.01
            can_sell = base in balances and balances[base] > 0.01
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
        # Scan Z-A
        for s in sorted(info.get('symbols', []), key=lambda x: x['symbol'], reverse=True):
            if s['status'] != 'TRADING': continue
            base = s['baseAsset']
            quote = s['quoteAsset']
            symbol = s['symbol']
            can_buy = quote in balances and balances[quote] > 0.01
            can_sell = base in balances and balances[base] > 0.01
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
        return pairs

    def expected_profit_pct(self, symbol: str) -> float:
        try:
            orderbook = self.client.session.get(f"{self.client.base}/api/v3/ticker/bookTicker", params={'symbol': symbol}).json()
            bid = float(orderbook['bidPrice'])
            ask = float(orderbook['askPrice'])
            gross_profit = (bid - ask) / ask
            net_profit = gross_profit - self.fee_pct
            return net_profit * 100
        except Exception as e:
            logger.error(f"Error getting orderbook for {symbol}: {e}")
            return -100.0

    def kelly_size(self, win_prob: float, win_pct: float, loss_pct: float, balance: float) -> float:
        # Kelly formula: f* = (bp - q) / b
        b = win_pct / abs(loss_pct)
        p = win_prob
        q = 1 - p
        f_star = (b * p - q) / b
        f_star = max(0.01, min(f_star, 1.0))  # Clamp between 1% and 100%
        return balance * f_star * self.kelly_fraction

    def run(self, duration_sec: int = 900):
        logger.info(f"\n🚀 Starting COMPOUND KELLY trading for {duration_sec}s...")
        start_time = time.time()
        cycle = 0
        while time.time() - start_time < duration_sec:
            cycle += 1
            logger.info(f"\n🔄 Cycle {cycle} | Positions: {len(self.positions)}/{self.max_positions} | Profit: ${self.total_profit:+.2f}")
            pairs = self.get_tradeable_pairs()
            random.shuffle(pairs)
            for pair in pairs:
                if len(self.positions) >= self.max_positions:
                    break
                symbol = pair['symbol']
                profit_pct = self.expected_profit_pct(symbol)
                if profit_pct > 0.0:
                    # Use Kelly criterion for sizing - pull LIVE win rate from Autonomy Hub
                    win_prob = 0.55  # Default fallback
                    try:
                        from aureon.autonomous.aureon_autonomy_hub import get_autonomy_hub
                        hub_wr = get_autonomy_hub().feedback_loop.get_rolling_win_rate()
                        if hub_wr > 0.0:
                            win_prob = max(0.51, min(0.85, hub_wr))  # Clamp to sane range
                    except Exception:
                        pass  # Use default
                    win_pct = profit_pct / 100
                    loss_pct = self.fee_pct
                    balance = pair['quote_balance'] if pair['can_buy'] else pair['base_balance']
                    size = self.kelly_size(win_prob, win_pct, loss_pct, balance)
                    if size < 0.01: continue
                    logger.info(f"🎯 {symbol}: Expected profit {profit_pct:.3f}% | Kelly size: {size:.4f} {pair['quote' if pair['can_buy'] else 'base']} | Compound mode")
                    if self.dry_run:
                        logger.info(f"📝 DRY-RUN: BUY {symbol} with {size:.4f} {pair['quote' if pair['can_buy'] else 'base']}")
                    else:
                        logger.info(f"🚀 LIVE BUY: {symbol} with {size:.4f} {pair['quote' if pair['can_buy'] else 'base']}")
                        result = self.client.place_market_order(symbol, 'BUY', quote_qty=size)
                        logger.info(f"📋 Order result: {result}")
                    self.positions[symbol] = {
                        'entry_time': time.time(),
                        'entry_price': float(self.client.best_price(symbol)['price']),
                        'side': 'BUY',
                        'size': size
                    }
            # Compound: reinvest profits
            for symbol in list(self.positions.keys()):
                pos = self.positions[symbol]
                current_price = float(self.client.best_price(symbol)['price'])
                entry_price = pos['entry_price']
                change_pct = (current_price - entry_price) / entry_price * 100
                if change_pct >= 0.3:
                    logger.info(f"💰 {symbol}: Take profit hit! {change_pct:.3f}% | Compounding")
                    if self.dry_run:
                        logger.info(f"📝 DRY-RUN: SELL {symbol}")
                    else:
                        logger.info(f"🚀 LIVE SELL: {symbol}")
                        result = self.client.place_market_order(symbol, 'SELL', quote_qty=pos['size'])
                        logger.info(f"📋 Order result: {result}")
                    self.total_profit += pos['size'] * change_pct / 100
                    del self.positions[symbol]
                elif change_pct <= -0.2:
                    logger.info(f"🛑 {symbol}: Stop loss hit! {change_pct:.3f}%")
                    if self.dry_run:
                        logger.info(f"📝 DRY-RUN: SELL {symbol}")
                    else:
                        logger.info(f"🚀 LIVE SELL: {symbol}")
                        result = self.client.place_market_order(symbol, 'SELL', quote_qty=pos['size'])
                        logger.info(f"📋 Order result: {result}")
                    self.total_profit += pos['size'] * change_pct / 100
                    del self.positions[symbol]
            time.sleep(2)
        logger.info(f"\n🏁 Final Profit: ${self.total_profit:+.2f}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--duration', type=int, default=900)
    args = parser.parse_args()
    if not args.dry_run:
        if os.getenv('CONFIRM_LIVE', '').lower() != 'yes':
            logger.error("❌ Set CONFIRM_LIVE=yes for live trading")
            sys.exit(1)
        logger.warning("⚠️  LIVE TRADING MODE - Real capital at risk!")
    trader = CompoundKellyTrader(dry_run=args.dry_run)
    trader.run(duration_sec=args.duration)

if __name__ == "__main__":
    main()
