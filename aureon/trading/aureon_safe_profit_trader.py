#!/usr/bin/env python3
"""
AUREON SAFE PROFIT TRADER
═══════════════════════════════════════════════════════════════════════════════
Only enters trades when expected profit after fees is positive.

Strategy:
  - Scan wallet for assets with balance > 0
  - For each asset, find all tradeable pairs
  - For each pair, calculate expected profit after 0.2% fees
  - Only enter trades if expected profit > 0.0%
  - Set stop-loss and take-profit
  - Exit immediately if profit target or stop-loss is hit

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
        logging.FileHandler('safe_profit_trader.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class SafeProfitTrader:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.client = get_binance_client()
        self.fee_pct = 0.004  # 0.4% round-trip (0.2% each side for taker)
        self.take_profit_pct = 0.012  # 1.2% take profit (must beat fees!)
        self.stop_loss_pct = 0.008  # 0.8% stop loss
        self.trade_size_usd = 10.0
        self.max_positions = 3
        self.positions = {}
        self.total_profit = 0.0

    def get_tradeable_pairs(self) -> List[Dict[str, Any]]:
        account = self.client.account()
        balances = {b['asset']: float(b['free']) for b in account['balances'] if float(b['free']) > 0.01}
        info = self.client.exchange_info()
        pairs = []
        for s in info.get('symbols', []):
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
            spread = (bid - ask) / ask
            # Assume we buy at ask, sell at bid
            gross_profit = (bid - ask) / ask
            net_profit = gross_profit - self.fee_pct
            return net_profit * 100
        except Exception as e:
            logger.error(f"Error getting orderbook for {symbol}: {e}")
            return -100.0

    def run(self, duration_sec: int = 600):
        logger.info(f"\n🚀 Starting SAFE PROFIT trading for {duration_sec}s...")
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
                if pair['can_buy']:
                    profit_pct = self.expected_profit_pct(symbol)
                    if profit_pct > 0.0:
                        logger.info(f"🎯 {symbol}: Expected profit after fees: {profit_pct:.3f}%")
                        # Place BUY order
                        if self.dry_run:
                            logger.info(f"📝 DRY-RUN: BUY {symbol} with ${self.trade_size_usd:.2f} {pair['quote']}")
                        else:
                            logger.info(f"🚀 LIVE BUY: {symbol} with ${self.trade_size_usd:.2f} {pair['quote']}")
                            result = self.client.place_market_order(symbol, 'BUY', quote_qty=self.trade_size_usd)
                            logger.info(f"📋 Order result: {result}")
                        self.positions[symbol] = {
                            'entry_time': time.time(),
                            'entry_price': float(self.client.best_price(symbol)['price']),
                            'side': 'BUY',
                            'size': self.trade_size_usd
                        }
            # Check exits
            for symbol in list(self.positions.keys()):
                pos = self.positions[symbol]
                current_price = float(self.client.best_price(symbol)['price'])
                entry_price = pos['entry_price']
                change_pct = (current_price - entry_price) / entry_price * 100
                if change_pct >= self.take_profit_pct * 100:
                    logger.info(f"💰 {symbol}: Take profit hit! {change_pct:.3f}%")
                    if self.dry_run:
                        logger.info(f"📝 DRY-RUN: SELL {symbol}")
                    else:
                        logger.info(f"🚀 LIVE SELL: {symbol}")
                        result = self.client.place_market_order(symbol, 'SELL', quote_qty=self.trade_size_usd)
                        logger.info(f"📋 Order result: {result}")
                    self.total_profit += self.trade_size_usd * change_pct / 100
                    del self.positions[symbol]
                elif change_pct <= -self.stop_loss_pct * 100:
                    logger.info(f"🛑 {symbol}: Stop loss hit! {change_pct:.3f}%")
                    if self.dry_run:
                        logger.info(f"📝 DRY-RUN: SELL {symbol}")
                    else:
                        logger.info(f"🚀 LIVE SELL: {symbol}")
                        result = self.client.place_market_order(symbol, 'SELL', quote_qty=self.trade_size_usd)
                        logger.info(f"📋 Order result: {result}")
                    self.total_profit += self.trade_size_usd * change_pct / 100
                    del self.positions[symbol]
            time.sleep(5)
        logger.info(f"\n🏁 Final Profit: ${self.total_profit:+.2f}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--duration', type=int, default=600)
    args = parser.parse_args()
    if not args.dry_run:
        if os.getenv('CONFIRM_LIVE', '').lower() != 'yes':
            logger.error("❌ Set CONFIRM_LIVE=yes for live trading")
            sys.exit(1)
        logger.warning("⚠️  LIVE TRADING MODE - Real capital at risk!")
    trader = SafeProfitTrader(dry_run=args.dry_run)
    trader.run(duration_sec=args.duration)

if __name__ == "__main__":
    main()
