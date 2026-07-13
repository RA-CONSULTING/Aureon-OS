#!/usr/bin/env python3
"""
🚀 AUREON QUANTUM RAPID TRADER 🚀

Based on Quantum Quackers realMoneyLive.ts:
- Trade interval: 500ms
- Risk per trade: 10%
- Multi-pair rotation
- Rapid compounding

This is the FAST trader - no waiting around!
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import time
import math
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from aureon.exchanges.binance_client import BinanceClient, get_binance_client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# QUANTUM QUACKERS CONFIG (from realMoneyLive.ts)
# ═══════════════════════════════════════════════════════════════════════════════

TRADE_INTERVAL_MS = 500  # 500ms between trades
RISK_PERCENT = 10  # 10% of capital per trade
FEE_RATE = 0.001  # 0.1% per side

# Pairs to trade
PAIRS = ['SOLUSDC', 'XRPUSDC', 'ADAUSDC', 'DOGEUSDC', 'AVAXUSDC']

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_lot_size(client: BinanceClient, symbol: str) -> Tuple[float, float]:
    """Get step size and min quantity for a symbol"""
    info = client.exchange_info(symbol)
    for f in info['symbols'][0]['filters']:
        if f['filterType'] == 'LOT_SIZE':
            return float(f['stepSize']), float(f['minQty'])
    return 0.001, 0.001

def round_step(qty: float, step: float) -> float:
    """Round quantity to step size"""
    if step <= 0:
        return qty
    precision = max(0, int(round(-math.log10(step))))
    return round(math.floor(qty / step) * step, precision)

def get_opportunity(client: BinanceClient, symbol: str) -> Optional[Dict]:
    """Check if symbol has a good entry opportunity"""
    try:
        resp = client.session.get(
            f'{client.base}/api/v3/ticker/24hr',
            params={'symbol': symbol},
            timeout=1
        )
        t = resp.json()
        
        price = float(t['lastPrice'])
        high = float(t['highPrice'])
        low = float(t['lowPrice'])
        
        if high <= low:
            return None
        
        position = (price - low) / (high - low)
        range_pct = (high - low) / low * 100
        
        # Only trade if near the LOW (mean reversion)
        if position < 0.30 and range_pct > 1.0:
            target = low + (high - low) * 0.50  # Target middle
            expected = (target - price) / price * 100 - (FEE_RATE * 2 * 100)
            
            if expected > 0.5:  # At least 0.5% expected
                return {
                    'symbol': symbol,
                    'price': price,
                    'position': position,
                    'range_pct': range_pct,
                    'target': target,
                    'expected': expected,
                    'side': 'BUY'
                }
        
        # Also check if near HIGH for SELL
        elif position > 0.70 and range_pct > 1.0:
            target = low + (high - low) * 0.50
            expected = (price - target) / price * 100 - (FEE_RATE * 2 * 100)
            
            if expected > 0.5:
                return {
                    'symbol': symbol,
                    'price': price,
                    'position': position,
                    'range_pct': range_pct,
                    'target': target,
                    'expected': expected,
                    'side': 'SELL'
                }
        
        return None
    except Exception as e:
        return None

# ═══════════════════════════════════════════════════════════════════════════════
# QUANTUM RAPID TRADER
# ═══════════════════════════════════════════════════════════════════════════════

class QuantumRapidTrader:
    def __init__(self):
        self.client = get_binance_client()
        self.positions: Dict[str, Dict] = {}
        self.trades: List[Dict] = []
        self.starting_capital = 0.0
        self.total_pnl = 0.0
        
    def get_capital(self) -> float:
        """Get available USDC capital"""
        return self.client.get_free_balance('USDC')
    
    def get_total_value(self) -> float:
        """Get total portfolio value in USDC"""
        usdc = self.client.get_free_balance('USDC')
        total = usdc
        
        # Add value of positions
        for sym, pos in self.positions.items():
            try:
                price = float(self.client.best_price(sym)['price'])
                total += pos['quantity'] * price
            except:
                pass
        
        return total
    
    def scan_opportunities(self) -> List[Dict]:
        """Scan all pairs for opportunities"""
        opportunities = []
        for symbol in PAIRS:
            opp = get_opportunity(self.client, symbol)
            if opp:
                opportunities.append(opp)
        
        # Sort by expected profit
        opportunities.sort(key=lambda x: x['expected'], reverse=True)
        return opportunities
    
    def execute_trade(self, symbol: str, side: str, usdc_amount: float) -> Optional[Dict]:
        """Execute a trade"""
        try:
            step, min_qty = get_lot_size(self.client, symbol)
            price = float(self.client.best_price(symbol)['price'])
            
            if side == 'BUY':
                quantity = usdc_amount / price
            else:
                # For SELL, get current holding
                asset = symbol.replace('USDC', '')
                quantity = self.client.get_free_balance(asset)
            
            quantity = round_step(quantity, step)
            
            if quantity < min_qty:
                logger.warning(f"Quantity {quantity} below min {min_qty}")
                return None
            
            # Check notional value
            notional = quantity * price
            if notional < 5:  # Binance minimum
                logger.warning(f"Notional ${notional:.2f} below $5 minimum")
                return None
            
            # Execute
            order = self.client.place_market_order(symbol, side, quantity=quantity)
            
            logger.info(f"✅ {side} {quantity:.6f} {symbol} @ ${price:.4f} = ${notional:.2f}")
            
            # Track position
            if side == 'BUY':
                self.positions[symbol] = {
                    'quantity': quantity,
                    'entry_price': price,
                    'entry_time': time.time(),
                    'side': side
                }
            else:
                if symbol in self.positions:
                    del self.positions[symbol]
            
            return order
            
        except Exception as e:
            logger.error(f"Trade failed: {e}")
            return None
    
    def check_exits(self) -> List[Dict]:
        """Check if any positions should be closed"""
        exits = []
        
        for symbol, pos in list(self.positions.items()):
            try:
                current_price = float(self.client.best_price(symbol)['price'])
                entry = pos['entry_price']
                
                pnl_pct = (current_price - entry) / entry * 100
                
                # Exit conditions
                if pnl_pct >= 1.0:  # 1% profit target
                    exits.append({'symbol': symbol, 'reason': 'TARGET', 'pnl': pnl_pct})
                elif pnl_pct <= -0.5:  # 0.5% stop loss
                    exits.append({'symbol': symbol, 'reason': 'STOP', 'pnl': pnl_pct})
                elif time.time() - pos['entry_time'] > 300:  # 5 min timeout
                    exits.append({'symbol': symbol, 'reason': 'TIMEOUT', 'pnl': pnl_pct})
                    
            except Exception as e:
                logger.error(f"Exit check failed for {symbol}: {e}")
        
        return exits
    
    def run(self, max_trades: int = 20, interval_ms: int = TRADE_INTERVAL_MS):
        """Run the rapid trading loop"""
        self.starting_capital = self.get_total_value()
        trade_count = 0
        
        print(f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║              🚀 QUANTUM RAPID TRADER - LIVE MODE 🚀                           ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║   Starting Capital: ${self.starting_capital:.2f}                              ║
║   Trade Interval: {interval_ms}ms                                             ║
║   Risk Per Trade: {RISK_PERCENT}%                                             ║
║   Max Trades: {max_trades}                                                    ║
╚═══════════════════════════════════════════════════════════════════════════════╝
        """)
        
        while trade_count < max_trades:
            cycle_start = time.time()
            
            # Check exits first
            exits = self.check_exits()
            for exit in exits:
                symbol = exit['symbol']
                logger.info(f"📤 Exiting {symbol}: {exit['reason']} ({exit['pnl']:+.2f}%)")
                self.execute_trade(symbol, 'SELL', 0)
                trade_count += 1
            
            # Look for new entries
            if len(self.positions) < 3:  # Max 3 concurrent positions
                capital = self.get_capital()
                trade_size = capital * (RISK_PERCENT / 100)
                
                if trade_size >= 5:  # Minimum $5
                    opportunities = self.scan_opportunities()
                    
                    for opp in opportunities[:1]:  # Take best opportunity
                        if opp['symbol'] not in self.positions:
                            logger.info(f"📥 Entry: {opp['symbol']} @ ${opp['price']:.4f} (expected +{opp['expected']:.2f}%)")
                            result = self.execute_trade(opp['symbol'], 'BUY', trade_size)
                            if result:
                                trade_count += 1
                            break
            
            # Status update
            current_value = self.get_total_value()
            pnl = current_value - self.starting_capital
            pnl_pct = (pnl / self.starting_capital) * 100 if self.starting_capital > 0 else 0
            
            if trade_count % 5 == 0:
                logger.info(f"💰 Value: ${current_value:.2f} | P&L: ${pnl:+.2f} ({pnl_pct:+.2f}%) | Trades: {trade_count}")
            
            # Wait for next interval
            elapsed = (time.time() - cycle_start) * 1000
            sleep_time = max(0, interval_ms - elapsed) / 1000
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        # Final report
        final_value = self.get_total_value()
        total_pnl = final_value - self.starting_capital
        
        print(f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                          SESSION COMPLETE                                     ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║   Starting: ${self.starting_capital:.2f}                                      ║
║   Final:    ${final_value:.2f}                                                ║
║   P&L:      ${total_pnl:+.2f} ({(total_pnl/self.starting_capital)*100:+.2f}%) ║
║   Trades:   {trade_count}                                                     ║
╚═══════════════════════════════════════════════════════════════════════════════╝
        """)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Quantum Rapid Trader')
    parser.add_argument('--trades', type=int, default=20, help='Max trades to execute')
    parser.add_argument('--interval', type=int, default=500, help='Trade interval in ms')
    
    args = parser.parse_args()
    
    trader = QuantumRapidTrader()
    trader.run(max_trades=args.trades, interval_ms=args.interval)
