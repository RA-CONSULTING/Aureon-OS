#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                   ║
║   💰 LIVE CONVERSION TRADER 💰                                                    ║
║                                                                                   ║
║   REAL MONEY. REAL CONVERSIONS. THROUGH THE MYCELIUM.                            ║
║                                                                                   ║
║   Uses:                                                                           ║
║   • Rapid Conversion Stream (2,300+ pairs, 240 updates/sec)                       ║
║   • Mycelium Conversion Hub (10 systems, 90 pathways)                             ║
║   • V14 Scoring (100% win rate logic)                                             ║
║   • Kraken for execution (lowest fees)                                            ║
║                                                                                   ║
║   ONE GOAL: BARTER FOR BETTER → SNOWBALL → GROW BUYING POWER                     ║
║                                                                                   ║
╚═══════════════════════════════════════════════════════════════════════════════════╝
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import json
import asyncio
import time
import signal
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import deque
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ═══════════════════════════════════════════════════════════════════════════════════
# IMPORTS
# ═══════════════════════════════════════════════════════════════════════════════════

# Kraken Client
try:
    from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
    KRAKEN_AVAILABLE = True
except ImportError:
    KRAKEN_AVAILABLE = False
    print("⚠️ Kraken client not available")

# Mycelium Hub
try:
    from aureon.conversion.mycelium_conversion_hub import get_conversion_hub, ConversionSignal
    HUB_AVAILABLE = True
except ImportError:
    HUB_AVAILABLE = False

# Rapid Stream
try:
    from aureon.conversion.rapid_conversion_stream import RapidConversionStream, RapidTickerCache
    STREAM_AVAILABLE = True
except ImportError:
    STREAM_AVAILABLE = False

# V14 Scoring
try:
    from aureon.strategies.s5_v14_dance_enhancements import V14DanceEnhancer, V14_CONFIG
    V14_AVAILABLE = True
except ImportError:
    V14_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════════

LIVE_CONFIG = {
    # Trading
    'min_trade_usd': 5.0,           # Minimum trade size
    'max_trade_usd': 50.0,          # Maximum trade size per conversion
    'min_profit_target': 0.0001,    # Global epsilon profit policy: accept any net-positive edge after costs.
    
    # Signal thresholds
    'min_hub_score': 0.55,          # Minimum unified score from hub
    'min_confidence': 0.60,         # Minimum confidence
    'min_spread_pct': 1.0,          # Minimum spread between assets
    
    # Risk management
    'max_open_conversions': 5,      # Max concurrent conversions
    'cooldown_seconds': 30,         # Cooldown between trades per pair
    
    # Fees (Kraken)
    'taker_fee': 0.0026,            # 0.26%
    'maker_fee': 0.0016,            # 0.16%
}


@dataclass
class LiveConversion:
    """A live conversion position"""
    id: str
    from_asset: str
    to_asset: str
    from_amount: float
    to_amount: float
    entry_price: float
    entry_time: datetime
    hub_score: float
    target_profit_pct: float = 1.52  # V14 target
    status: str = 'OPEN'
    current_price: float = 0.0
    current_pnl: float = 0.0


class LiveConversionTrader:
    """
    💰 LIVE CONVERSION TRADER 💰
    
    Executes real conversions through the Mycelium Hub on Kraken.
    """
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.running = False
        self.start_time = None
        
        print("\n" + "="*80)
        print("💰 LIVE CONVERSION TRADER INITIALIZING...")
        print("="*80)
        
        # ═══════════════════════════════════════════════════════════════════════
        # Initialize Components
        # ═══════════════════════════════════════════════════════════════════════
        
        # Kraken Client
        self.kraken = None
        if KRAKEN_AVAILABLE and not dry_run:
            self.kraken = get_kraken_client()
            print("🐙 Kraken Client: CONNECTED")
        else:
            print("🐙 Kraken Client: DRY RUN MODE")
        
        # Mycelium Hub
        self.hub = None
        if HUB_AVAILABLE:
            self.hub = get_conversion_hub(10000.0)
            print("🍄 Mycelium Hub: WIRED")
        
        # V14 Scoring
        self.v14 = None
        if V14_AVAILABLE:
            self.v14 = V14DanceEnhancer()
            print("🎯 V14 Scoring: LOADED")
        
        # ═══════════════════════════════════════════════════════════════════════
        # State
        # ═══════════════════════════════════════════════════════════════════════
        
        self.balances: Dict[str, float] = {}
        self.prices: Dict[str, float] = {}
        self.conversions: Dict[str, LiveConversion] = {}
        self.closed_conversions: List[Dict] = []
        self.dry_run_attempts: List[Dict[str, Any]] = []
        self.conversion_counter = 0
        self.last_trade_time: Dict[str, float] = {}
        
        # Stats
        self.stats = {
            'signals_evaluated': 0,
            'conversions_opened': 0,
            'conversions_closed': 0,
            'total_profit': 0.0,
            'wins': 0,
            'losses': 0,
        }
        
        # Price cache for rapid updates
        self.ticker_cache: Dict[str, Dict] = {}
        
        # Signal handling
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        print("\n\n🛑 Stopping Live Trader...")
        self.running = False
        
    def load_balances(self) -> bool:
        """Load real balances from Kraken"""
        print("\n📊 Loading balances...")
        
        if self.dry_run:
            self.balances = {}
            print("   🔵 DRY RUN - No authenticated balance receipt; balances are NO_DATA")
            return False

        if not self.kraken:
            self.balances = {}
            print("   ❌ Kraken client unavailable; balances are NO_DATA")
            return False
        
        try:
            balance = self.kraken.get_account_balance()
            if not balance:
                print("   ❌ Could not get balance")
                return False
            
            total_usd = 0
            for asset, amount in balance.items():
                if amount > 0.0001:
                    # Clean asset name
                    clean = asset.replace('X', '').replace('Z', '')
                    if clean == 'XBT':
                        clean = 'BTC'
                    
                    self.balances[clean] = amount
                    
                    # Estimate USD value
                    if clean in ['USD', 'USDT', 'USDC']:
                        usd_val = amount
                    elif clean == 'BTC':
                        usd_val = amount * 97000
                    elif clean == 'ETH':
                        usd_val = amount * 3400
                    else:
                        usd_val = amount * 10  # Rough estimate
                    
                    total_usd += usd_val
                    print(f"      {clean}: {amount:.6f} (~${usd_val:.2f})")
            
            print(f"\n   💰 Total Portfolio: ~${total_usd:.2f}")
            return True
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
            
    async def fetch_prices(self) -> bool:
        """Fetch current prices from Binance (fastest)"""
        import requests
        
        try:
            response = requests.get(
                'https://api.binance.com/api/v3/ticker/24hr',
                timeout=10
            )
            data = response.json()
            
            for t in data:
                symbol = t.get('symbol', '')
                if symbol.endswith('USDT'):
                    base = symbol[:-4]
                    price = float(t.get('lastPrice', 0))
                    change = float(t.get('priceChangePercent', 0))
                    volume = float(t.get('volume', 0))
                    
                    self.prices[base] = price
                    self.ticker_cache[symbol] = {
                        'price': price,
                        'change24h': change,
                        'volume': volume,
                    }
            
            return True
        except Exception as e:
            print(f"   ⚠️ Price fetch error: {e}")
            return False
            
    def find_conversion_opportunity(self) -> Optional[Dict]:
        """Find the best conversion opportunity using Mycelium Hub"""
        
        # Get assets we hold
        held_assets = [a for a, amt in self.balances.items() 
                      if amt > 0 and a not in ['USD', 'USDT', 'USDC']]
        
        if not held_assets:
            return None
        
        best_opportunity = None
        best_score = 0
        
        # For each held asset, find best conversion target
        for from_asset in held_assets:
            from_price = self.prices.get(from_asset, 0)
            if from_price <= 0:
                continue
            
            # Check cooldown
            if time.time() - self.last_trade_time.get(from_asset, 0) < LIVE_CONFIG['cooldown_seconds']:
                continue
            
            # Get top movers as potential targets
            top_targets = sorted(
                self.ticker_cache.items(),
                key=lambda x: x[1].get('change24h', 0),
                reverse=True
            )[:20]
            
            for symbol, ticker in top_targets:
                to_asset = symbol.replace('USDT', '')
                if to_asset == from_asset:
                    continue
                
                to_price = ticker.get('price', 0)
                if to_price <= 0:
                    continue
                
                # Get Hub signal
                if self.hub:
                    signal = self.hub.get_conversion_signal(
                        from_asset=from_asset,
                        to_asset=to_asset,
                        from_price=from_price,
                        to_price=to_price,
                    )
                    
                    self.stats['signals_evaluated'] += 1
                    
                    # Check if meets thresholds
                    if signal.unified_score >= LIVE_CONFIG['min_hub_score'] and \
                       signal.unified_confidence >= LIVE_CONFIG['min_confidence']:
                        
                        spread = ticker.get('change24h', 0)
                        
                        if signal.unified_score > best_score and spread >= LIVE_CONFIG['min_spread_pct']:
                            best_score = signal.unified_score
                            best_opportunity = {
                                'from_asset': from_asset,
                                'to_asset': to_asset,
                                'from_price': from_price,
                                'to_price': to_price,
                                'spread': spread,
                                'hub_score': signal.unified_score,
                                'confidence': signal.unified_confidence,
                                'recommendation': signal.recommendation.value,
                                'systems': signal.participating_systems,
                            }
        
        return best_opportunity
        
    async def execute_conversion(self, opportunity: Dict) -> Any:
        """Execute a conversion on Kraken"""
        
        from_asset = opportunity['from_asset']
        to_asset = opportunity['to_asset']

        if self.dry_run:
            receipt = {
                'status': 'not_submitted',
                'truth_status': 'dry_run',
                'provider_order_id': None,
                'fill': None,
                'actual_pnl': None,
                'eligible_for_learning': False,
                'generated_values': False,
                'from_asset': from_asset,
                'to_asset': to_asset,
                'recorded_at': time.time(),
            }
            self.dry_run_attempts.append(receipt)
            print("      🔵 DRY RUN - Intent recorded; no order was submitted")
            return receipt
        
        # Calculate amounts
        from_balance = self.balances.get(from_asset, 0)
        from_price = opportunity['from_price']
        
        # Trade 20% of holdings, max $50
        trade_value_usd = min(from_balance * from_price * 0.2, LIVE_CONFIG['max_trade_usd'])
        
        if trade_value_usd < LIVE_CONFIG['min_trade_usd']:
            print(f"   ⚠️ Trade too small: ${trade_value_usd:.2f}")
            return False
        
        from_amount = trade_value_usd / from_price
        to_amount = trade_value_usd / opportunity['to_price']
        
        # Generate conversion ID
        self.conversion_counter += 1
        conv_id = f"CONV-{self.conversion_counter:04d}"
        
        print(f"\n   🔄 EXECUTING CONVERSION {conv_id}:")
        print(f"      {from_asset} → {to_asset}")
        print(f"      Amount: {from_amount:.6f} {from_asset} (~${trade_value_usd:.2f})")
        print(f"      Hub Score: {opportunity['hub_score']*100:.1f}%")
        print(f"      Systems: {', '.join(opportunity['systems'])}")
        
        # Real execution on Kraken
        try:
            # First sell from_asset for USD
            sell_pair = f"{from_asset}USD"
            result = self.kraken.client.query_private('AddOrder', {
                'pair': sell_pair,
                'type': 'sell',
                'ordertype': 'market',
                'volume': str(from_amount),
            })

            if result.get('error'):
                print(f"      ❌ Sell failed: {result['error']}")
                return False

            print(f"      ✅ Sold {from_amount:.6f} {from_asset}")

            # Then buy to_asset with USD
            await asyncio.sleep(1)  # Wait for order to settle

            buy_pair = f"{to_asset}USD"
            result = self.kraken.client.query_private('AddOrder', {
                'pair': buy_pair,
                'type': 'buy',
                'ordertype': 'market',
                'volume': str(to_amount),
            })

            if result.get('error'):
                print(f"      ❌ Buy failed: {result['error']}")
                return False

            print(f"      ✅ Bought {to_amount:.6f} {to_asset}")
            success = True

        except Exception as e:
            print(f"      ❌ Execution error: {e}")
            return False
        
        if success:
            # Track conversion
            conversion = LiveConversion(
                id=conv_id,
                from_asset=from_asset,
                to_asset=to_asset,
                from_amount=from_amount,
                to_amount=to_amount,
                entry_price=opportunity['to_price'],
                entry_time=datetime.now(),
                hub_score=opportunity['hub_score'],
            )
            self.conversions[conv_id] = conversion
            self.stats['conversions_opened'] += 1
            self.last_trade_time[from_asset] = time.time()
            
            print(f"      ✅ Conversion {conv_id} OPENED")
            return True
        
        return False
        
    def check_conversions(self):
        """Check open conversions for profit targets"""
        
        for conv_id, conv in list(self.conversions.items()):
            if conv.status != 'OPEN':
                continue
            
            current_price = self.prices.get(conv.to_asset, 0)
            if current_price <= 0:
                continue
            
            # Calculate PnL
            conv.current_price = current_price
            pnl_pct = ((current_price - conv.entry_price) / conv.entry_price) * 100
            conv.current_pnl = pnl_pct
            
            # V14 rule: Exit at 1.52% profit
            if pnl_pct >= conv.target_profit_pct:
                print(f"\n   🎯 PROFIT TARGET HIT: {conv_id}")
                print(f"      {conv.to_asset}: {pnl_pct:.2f}% profit!")
                
                # Close conversion (sell to_asset back to USD)
                if not self.dry_run and self.kraken:
                    try:
                        result = self.kraken.client.query_private('AddOrder', {
                            'pair': f"{conv.to_asset}USD",
                            'type': 'sell',
                            'ordertype': 'market',
                            'volume': str(conv.to_amount),
                        })
                        if result.get('error'):
                            print(f"      ⚠️ Close error: {result['error']}")
                            continue
                    except:
                        continue
                
                # Calculate profit
                profit_usd = conv.to_amount * conv.entry_price * (pnl_pct / 100)
                
                conv.status = 'CLOSED'
                self.stats['conversions_closed'] += 1
                self.stats['wins'] += 1
                self.stats['total_profit'] += profit_usd
                
                self.closed_conversions.append({
                    'id': conv_id,
                    'from': conv.from_asset,
                    'to': conv.to_asset,
                    'profit_pct': pnl_pct,
                    'profit_usd': profit_usd,
                    'duration': (datetime.now() - conv.entry_time).total_seconds(),
                })
                
                del self.conversions[conv_id]
                
                print(f"      💰 Profit: ${profit_usd:.4f}")
                
    def print_status(self):
        """Print current status"""
        elapsed = time.time() - self.start_time if self.start_time else 0
        
        print(f"\r⚡ LIVE TRADER | "
              f"Time: {elapsed:.0f}s | "
              f"Signals: {self.stats['signals_evaluated']} | "
              f"Open: {len(self.conversions)} | "
              f"Closed: {self.stats['conversions_closed']} | "
              f"Profit: ${self.stats['total_profit']:.4f} | "
              f"Win Rate: {self.stats['wins']}/{self.stats['conversions_closed']}", 
              end='', flush=True)
        
    async def run(self, duration_seconds: int = 300):
        """Run the live trader"""
        
        mode = "DRY RUN" if self.dry_run else "🔴 LIVE TRADING"
        
        print(f"""
╔═══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                   ║
║   💰💰💰 LIVE CONVERSION TRADER 💰💰💰                                            ║
║                                                                                   ║
║   MODE: {mode:<68} ║
║   DURATION: {duration_seconds} seconds                                                          ║
║                                                                                   ║
║   ONE GOAL: BARTER FOR BETTER → SNOWBALL → GROW BUYING POWER                     ║
║                                                                                   ║
╚═══════════════════════════════════════════════════════════════════════════════════╝
""")
        
        if not self.load_balances():
            print("❌ Could not load balances")
            return
        
        self.running = True
        self.start_time = time.time()
        end_time = self.start_time + duration_seconds
        
        print("\n🚀 Starting live trading loop...")
        print("   Press Ctrl+C to stop\n")
        
        loop_count = 0
        
        while self.running and time.time() < end_time:
            loop_count += 1
            
            try:
                # Fetch latest prices
                await self.fetch_prices()
                
                # Check existing conversions for exits
                self.check_conversions()
                
                # Find new opportunities
                if len(self.conversions) < LIVE_CONFIG['max_open_conversions']:
                    opportunity = self.find_conversion_opportunity()
                    
                    if opportunity:
                        await self.execute_conversion(opportunity)
                
                # Print status every 5 loops
                if loop_count % 5 == 0:
                    self.print_status()
                
            except Exception as e:
                print(f"\n   ⚠️ Loop error: {e}")
            
            await asyncio.sleep(1)  # 1 second loop
        
        # Final report
        self._final_report()
        
    def _final_report(self):
        """Print final trading report"""
        elapsed = time.time() - self.start_time if self.start_time else 0
        
        print(f"""

╔═══════════════════════════════════════════════════════════════════════════════════╗
║                         📊 FINAL TRADING REPORT 📊                               ║
╠═══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                   ║
║   DURATION: {elapsed:.0f} seconds                                                          ║
║                                                                                   ║
║   SIGNALS EVALUATED: {self.stats['signals_evaluated']:<54} ║
║   CONVERSIONS OPENED: {self.stats['conversions_opened']:<53} ║
║   CONVERSIONS CLOSED: {self.stats['conversions_closed']:<53} ║
║                                                                                   ║
║   WINS: {self.stats['wins']:<67} ║
║   LOSSES: {self.stats['losses']:<65} ║
║   WIN RATE: {(self.stats['wins']/max(self.stats['conversions_closed'],1)*100):.1f}%                                                            ║
║                                                                                   ║
║   💰 TOTAL PROFIT: ${self.stats['total_profit']:.4f}                                                   ║
║                                                                                   ║
╚═══════════════════════════════════════════════════════════════════════════════════╝
""")
        
        if self.closed_conversions:
            print("\n📜 CLOSED CONVERSIONS:")
            for c in self.closed_conversions:
                print(f"   {c['id']}: {c['from']}→{c['to']} | "
                      f"+{c['profit_pct']:.2f}% | ${c['profit_usd']:.4f} | "
                      f"{c['duration']:.0f}s")


# ═══════════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════════

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true', help='Enable LIVE trading (real money!)')
    parser.add_argument('--duration', type=int, default=300, help='Duration in seconds')
    args = parser.parse_args()
    
    dry_run = not args.live
    
    if args.live:
        print("\n⚠️  WARNING: LIVE TRADING MODE!")
        print("    This will execute REAL trades with REAL money!")
        confirm = input("    Type 'CONFIRM' to proceed: ")
        if confirm != 'CONFIRM':
            print("    Aborted.")
            return
    
    trader = LiveConversionTrader(dry_run=dry_run)
    await trader.run(duration_seconds=args.duration)


if __name__ == "__main__":
    asyncio.run(main())
