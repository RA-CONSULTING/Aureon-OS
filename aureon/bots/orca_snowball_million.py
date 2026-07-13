#!/usr/bin/env python3
"""
🏔️❄️ ORCA SNOWBALL TO MILLION ❄️🏔️

Queen-guided autonomous snowball trading system.
Compounds wins relentlessly until $1,000,000.

NO SMOKE. JUST FIRE. REAL TRADES ONLY.
"""

import os
import sys
import json
import time
import random
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

# === SACRED CONSTANTS ===
PHI = 1.618033988749895  # Golden Ratio
MILLION = 1_000_000
LOVE_FREQUENCY = 528  # Hz

@dataclass
class SnowballState:
    """Current snowball state"""
    starting_value: float = 0
    current_value: float = 0
    trades_executed: int = 0
    wins: int = 0
    losses: int = 0
    total_profit: float = 0
    started_at: str = ""
    last_trade: str = ""
    
def log_snowball(msg: str):
    print(f"❄️ [SNOWBALL] {msg}")

def log_queen(msg: str):
    print(f"👑 [QUEEN] {msg}")

def log_fire(msg: str):
    print(f"🔥 [FIRE] {msg}")

def log_win(msg: str):
    print(f"💰 [WIN] {msg}")

class QueenSnowball:
    """Queen-guided snowball to million"""
    
    def __init__(self):
        self.state = SnowballState()
        self.state.started_at = datetime.now().isoformat()
        
        # Load exchange clients
        from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
        from aureon.exchanges.binance_client import BinanceClient, get_binance_client
        
        self.kraken = get_kraken_client()
        try:
            self.binance = get_binance_client()
        except:
            self.binance = None
            
        # Load Queen systems
        self._wire_queen()
        
    def _wire_queen(self):
        """Wire Queen intelligence systems"""
        log_queen("Wiring Queen Intelligence Systems...")
        
        try:
            from aureon.utils.aureon_queen_hive_mind import QueenHiveMind
            self.queen = QueenHiveMind()
            log_queen("✅ Queen Hive Mind: ONLINE")
        except Exception as e:
            log_queen(f"⚠️ Queen Hive Mind unavailable: {e}")
            self.queen = None
            
        try:
            from aureon.bridges.aureon_probability_nexus import ProbabilityNexus
            self.nexus = ProbabilityNexus()
            log_queen("✅ Probability Nexus: ONLINE")
        except:
            self.nexus = None
            
        try:
            from aureon.utils.aureon_miner_brain import MinerBrain
            self.brain = MinerBrain()
            log_queen("✅ Miner Brain: ONLINE")
        except:
            self.brain = None
            
    def get_total_portfolio_usd(self) -> float:
        """Get total portfolio value in USD"""
        total = 0
        
        # Kraken
        try:
            balances = self.kraken.get_balance()
            for asset, qty in balances.items():
                qty = float(qty)
                if qty <= 0:
                    continue
                    
                if asset in ['USD', 'ZUSD']:
                    total += qty
                elif asset == 'ZGBP':
                    total += qty * 1.27  # GBP to USD
                else:
                    # Get price
                    try:
                        pair = f"{asset}USD"
                        ticker = self.kraken.get_ticker(pair)
                        if ticker and ticker.get('price'):
                            total += qty * float(ticker['price'])
                    except:
                        pass
        except Exception as e:
            log_snowball(f"Kraken balance error: {e}")
            
        # Binance
        if self.binance:
            try:
                balances = self.binance.get_balance()
                for asset, qty in balances.items():
                    qty = float(qty)
                    if qty <= 0:
                        continue
                        
                    if asset in ['USDT', 'USDC', 'BUSD']:
                        total += qty
                    else:
                        try:
                            symbol = f"{asset}USDT"
                            ticker = self.binance.get_24h_ticker(symbol)
                            if ticker:
                                price = float(ticker.get('lastPrice', 0))
                                total += qty * price
                        except:
                            pass
            except:
                pass
                
        return total
        
    def queen_decide(self, opportunities: List[Dict]) -> Optional[Dict]:
        """Let Queen decide best opportunity"""
        if not opportunities:
            return None
            
        # Score each opportunity
        scored = []
        for opp in opportunities:
            score = opp.get('score', 0)
            
            # Queen boost for positive momentum
            if opp.get('change_24h', 0) > 5:
                score *= 1.2
                
            # Queen boost for high volume
            if opp.get('volume', 0) > 1000000:
                score *= 1.1
                
            # Nexus validation
            if self.nexus:
                try:
                    validation = self.nexus.quick_validate(opp.get('symbol', ''))
                    if validation and validation.get('probability', 0) > 0.6:
                        score *= 1.3
                except:
                    pass
                    
            scored.append((score, opp))
            
        # Sort by score
        scored.sort(key=lambda x: x[0], reverse=True)
        
        if scored:
            best_score, best_opp = scored[0]
            if best_score >= 3:  # Minimum threshold
                log_queen(f"👑 Queen selects: {best_opp.get('symbol')} (score: {best_score:.2f})")
                return best_opp
                
        return None
        
    def scan_kraken_opportunities(self) -> List[Dict]:
        """Scan Kraken for opportunities"""
        opportunities = []
        
        # Top pairs to scan
        pairs = ['BTCUSD', 'ETHUSD', 'SOLUSD', 'XRPUSD', 'DOGEUSD', 'ADAUSD', 
                 'AVAXUSD', 'LINKUSD', 'DOTUSD', 'MATICUSD']
        
        for pair in pairs:
            try:
                ticker = self.kraken.get_ticker(pair)
                if not ticker:
                    continue
                    
                price = float(ticker.get('price', 0))
                if price <= 0:
                    continue
                    
                # Get 24h data
                high = float(ticker.get('high', price))
                low = float(ticker.get('low', price))
                
                # Calculate metrics
                range_pct = ((high - low) / low * 100) if low > 0 else 0
                position_in_range = ((price - low) / (high - low) * 100) if (high - low) > 0 else 50
                
                # Score: higher volatility + lower in range = better buy
                score = (range_pct / 10) + ((100 - position_in_range) / 20)
                
                # Momentum check - if near low, good buy opportunity
                if position_in_range < 30:  # In lower 30% of range
                    score += 3
                    
                opportunities.append({
                    'symbol': pair,
                    'exchange': 'kraken',
                    'price': price,
                    'high_24h': high,
                    'low_24h': low,
                    'range_pct': range_pct,
                    'position_in_range': position_in_range,
                    'score': score,
                    'action': 'BUY'
                })
                
            except Exception as e:
                pass
                
        return sorted(opportunities, key=lambda x: x['score'], reverse=True)
        
    def scan_binance_momentum(self) -> List[Dict]:
        """Scan Binance for momentum plays"""
        if not self.binance:
            return []
            
        opportunities = []
        
        try:
            # Get all tickers
            tickers = self.binance.get_24h_tickers()
            
            for ticker in tickers[:100]:  # Top 100
                symbol = ticker.get('symbol', '')
                if not symbol.endswith('USDT'):
                    continue
                    
                change = float(ticker.get('priceChangePercent', 0))
                volume = float(ticker.get('quoteVolume', 0))
                price = float(ticker.get('lastPrice', 0))
                
                if price <= 0 or volume < 100000:
                    continue
                    
                # Check if we can trade it
                if not self.binance.can_trade_symbol(symbol):
                    continue
                    
                # Score momentum
                score = 0
                
                # Strong uptrend
                if 5 < change < 30:
                    score = change / 5
                    
                # High volume confirms
                if volume > 1000000:
                    score *= 1.2
                    
                if score >= 3:
                    opportunities.append({
                        'symbol': symbol,
                        'exchange': 'binance',
                        'price': price,
                        'change_24h': change,
                        'volume': volume,
                        'score': score,
                        'action': 'BUY'
                    })
                    
        except Exception as e:
            log_snowball(f"Binance scan error: {e}")
            
        return sorted(opportunities, key=lambda x: x['score'], reverse=True)
        
    def execute_trade(self, opportunity: Dict) -> Dict:
        """Execute a trade"""
        exchange = opportunity.get('exchange')
        symbol = opportunity.get('symbol')
        action = opportunity.get('action', 'BUY')
        
        log_fire(f"⚡ EXECUTING: {action} {symbol} on {exchange}")
        
        if exchange == 'kraken':
            return self._execute_kraken(opportunity)
        elif exchange == 'binance':
            return self._execute_binance(opportunity)
        else:
            return {'status': 'ERROR', 'error': 'Unknown exchange'}
            
    def _execute_kraken(self, opp: Dict) -> Dict:
        """Execute on Kraken"""
        try:
            symbol = opp['symbol']
            price = opp['price']
            action = opp.get('action', 'BUY')
            
            # Get USD balance
            balances = self.kraken.get_balance()
            usd_balance = float(balances.get('USD', 0))
            
            if action == 'BUY':
                if usd_balance < 5:
                    return {'status': 'NO_FUNDS', 'balance': usd_balance}
                    
                # Use 50% of available USD (snowball rule)
                trade_usd = usd_balance * 0.5
                volume = trade_usd / price
                
                # Round to appropriate decimals
                if price > 1000:
                    volume = round(volume, 5)
                elif price > 10:
                    volume = round(volume, 4)
                else:
                    volume = round(volume, 2)
                    
                log_fire(f"   💵 Using ${trade_usd:.2f} to buy {volume} {symbol}")
                
                result = self.kraken.place_market_order(symbol, 'buy', volume)
                
                if result and result.get('status') == 'FILLED':
                    log_win(f"💥 BOUGHT {volume} {symbol} @ ${price:.2f}")
                    self.state.trades_executed += 1
                    self.state.wins += 1
                    return {'status': 'FILLED', 'order': result, 'volume': volume, 'price': price}
                else:
                    return {'status': 'FAILED', 'error': result}
                    
            elif action == 'SELL':
                # Get asset balance
                asset = symbol.replace('USD', '')
                asset_balance = float(balances.get(asset, 0))
                
                if asset_balance <= 0:
                    return {'status': 'NO_ASSET', 'asset': asset}
                    
                # Sell 50% (snowball - keep compounding)
                sell_qty = asset_balance * 0.5
                
                result = self.kraken.place_market_order(symbol, 'sell', sell_qty)
                
                if result and result.get('status') == 'FILLED':
                    received = float(result.get('receivedQty', 0))
                    log_win(f"💥 SOLD {sell_qty} {symbol} → ${received:.2f}")
                    self.state.trades_executed += 1
                    self.state.wins += 1
                    return {'status': 'FILLED', 'order': result, 'received': received}
                else:
                    return {'status': 'FAILED', 'error': result}
                    
        except Exception as e:
            log_fire(f"❌ Kraken error: {e}")
            return {'status': 'ERROR', 'error': str(e)}
            
    def _execute_binance(self, opp: Dict) -> Dict:
        """Execute on Binance"""
        if not self.binance:
            return {'status': 'NO_CLIENT'}
            
        try:
            symbol = opp['symbol']
            price = opp['price']
            
            # Get USDT balance
            balances = self.binance.get_balance()
            usdt = float(balances.get('USDT', 0)) + float(balances.get('USDC', 0))
            
            if usdt < 5:
                return {'status': 'NO_FUNDS', 'balance': usdt}
                
            # Use 50% for snowball compounding
            trade_usd = usdt * 0.5
            volume = trade_usd / price
            
            # Adjust for Binance lot size
            volume = self.binance.adjust_quantity(symbol, volume)
            
            log_fire(f"   💵 Using ${trade_usd:.2f} to buy {volume} {symbol}")
            
            result = self.binance.place_market_order(symbol, 'BUY', volume)
            
            if result and result.get('status') == 'FILLED':
                log_win(f"💥 BOUGHT {volume} {symbol} @ ${price:.6f}")
                self.state.trades_executed += 1
                self.state.wins += 1
                return {'status': 'FILLED', 'order': result}
            else:
                return {'status': 'FAILED', 'error': result}
                
        except Exception as e:
            log_fire(f"❌ Binance error: {e}")
            return {'status': 'ERROR', 'error': str(e)}
            
    def check_positions_for_profit(self):
        """Check if any positions are in profit to sell"""
        log_snowball("🔍 Checking positions for profit-taking...")
        
        # Check Kraken positions
        try:
            balances = self.kraken.get_balance()
            
            for asset, qty in balances.items():
                qty = float(qty)
                if qty <= 0 or asset in ['USD', 'ZUSD', 'ZGBP', 'TUSD']:
                    continue
                    
                # Get current price
                pair = f"{asset}USD"
                try:
                    ticker = self.kraken.get_ticker(pair)
                    if not ticker:
                        continue
                        
                    price = float(ticker.get('price', 0))
                    value = qty * price
                    
                    if value < 5:
                        continue
                        
                    # Check if in profit (simple check - we'd need cost basis for real P/L)
                    high_24h = float(ticker.get('high', price))
                    low_24h = float(ticker.get('low', price))
                    
                    # If price is in upper 30% of range, take profit
                    if high_24h > low_24h:
                        position = (price - low_24h) / (high_24h - low_24h)
                        
                        if position > 0.7:  # In top 30%
                            log_snowball(f"   📈 {asset}: ${value:.2f} in profit zone ({position*100:.0f}%)")
                            
                            # Sell 50% to lock profit, keep 50% for more upside
                            sell_qty = qty * 0.5
                            
                            result = self.kraken.place_market_order(pair, 'sell', sell_qty)
                            
                            if result and result.get('status') == 'FILLED':
                                received = float(result.get('receivedQty', 0))
                                log_win(f"💰 PROFIT TAKEN: Sold {sell_qty} {asset} → ${received:.2f}")
                                self.state.trades_executed += 1
                                self.state.wins += 1
                                self.state.total_profit += received
                                
                except Exception as e:
                    pass
                    
        except Exception as e:
            log_snowball(f"Position check error: {e}")
            
    def run_cycle(self):
        """Run one snowball cycle"""
        log_snowball("=" * 60)
        log_snowball(f"   SNOWBALL CYCLE - {datetime.now().strftime('%H:%M:%S')}")
        log_snowball("=" * 60)
        
        # Get current portfolio value
        portfolio_value = self.get_total_portfolio_usd()
        self.state.current_value = portfolio_value
        
        if self.state.starting_value == 0:
            self.state.starting_value = portfolio_value
            
        # Progress to million
        progress = (portfolio_value / MILLION) * 100
        doublings_needed = 0
        temp = portfolio_value
        while temp < MILLION:
            temp *= 2
            doublings_needed += 1
            
        log_snowball(f"💰 Portfolio: ${portfolio_value:.2f}")
        log_snowball(f"🎯 Target: ${MILLION:,}")
        log_snowball(f"📊 Progress: {progress:.6f}%")
        log_snowball(f"🔄 Doublings needed: {doublings_needed}")
        
        if portfolio_value >= MILLION:
            log_snowball("🏆🏆🏆 MILLION REACHED! 🏆🏆🏆")
            return True
            
        # Step 1: Check positions for profit-taking
        self.check_positions_for_profit()
        
        # Step 2: Scan for new opportunities
        log_snowball("\n🔍 Scanning markets...")
        
        kraken_opps = self.scan_kraken_opportunities()
        binance_opps = self.scan_binance_momentum()
        
        all_opps = kraken_opps[:5] + binance_opps[:5]
        
        log_snowball(f"   Found {len(all_opps)} opportunities")
        
        # Step 3: Queen decides
        best = self.queen_decide(all_opps)
        
        if best:
            # Step 4: Execute
            result = self.execute_trade(best)
            
            if result.get('status') == 'FILLED':
                log_win("✅ Trade executed successfully!")
            else:
                log_snowball(f"⚠️ Trade result: {result.get('status')}")
        else:
            log_queen("👑 Queen says: Wait for better opportunity")
            
        # Update state
        self.state.last_trade = datetime.now().isoformat()
        self._save_state()
        
        return False
        
    def _save_state(self):
        """Save snowball state"""
        try:
            with open('snowball_state.json', 'w') as f:
                json.dump({
                    'starting_value': self.state.starting_value,
                    'current_value': self.state.current_value,
                    'trades_executed': self.state.trades_executed,
                    'wins': self.state.wins,
                    'losses': self.state.losses,
                    'total_profit': self.state.total_profit,
                    'started_at': self.state.started_at,
                    'last_trade': self.state.last_trade,
                    'updated_at': datetime.now().isoformat()
                }, f, indent=2)
        except:
            pass
            
    def run_forever(self, cycle_seconds: int = 60):
        """Run snowball forever until million"""
        print()
        print("🏔️" + "❄️" * 30 + "🏔️")
        print("   ORCA SNOWBALL TO MILLION")
        print("   Queen-Guided Autonomous Trading")
        print("🏔️" + "❄️" * 30 + "🏔️")
        print()
        
        log_queen("👑 Queen's Snowball Protocol ACTIVATED")
        log_queen(f"   Target: ${MILLION:,}")
        log_queen(f"   Cycle: Every {cycle_seconds}s")
        log_queen("   Strategy: Compound wins relentlessly")
        print()
        
        cycle = 0
        while True:
            cycle += 1
            
            try:
                reached_million = self.run_cycle()
                
                if reached_million:
                    log_snowball("🎉🎉🎉 CONGRATULATIONS! MILLION ACHIEVED! 🎉🎉🎉")
                    break
                    
            except KeyboardInterrupt:
                log_snowball("\n⏸️ Snowball paused by user")
                break
            except Exception as e:
                log_snowball(f"❌ Cycle error: {e}")
                
            # Wait for next cycle
            log_snowball(f"\n⏳ Next cycle in {cycle_seconds}s...")
            time.sleep(cycle_seconds)
            

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Orca Snowball to Million")
    parser.add_argument('--cycle', type=int, default=60, help='Seconds between cycles')
    parser.add_argument('--once', action='store_true', help='Run single cycle')
    args = parser.parse_args()
    
    snowball = QueenSnowball()
    
    if args.once:
        snowball.run_cycle()
    else:
        snowball.run_forever(cycle_seconds=args.cycle)
        

if __name__ == '__main__':
    main()
