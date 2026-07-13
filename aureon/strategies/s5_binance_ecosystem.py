#!/usr/bin/env python3
"""
S5 BINANCE ECOSYSTEM - FULL CONVERSION LABYRINTH
=================================================
The infinite conversion machine.

Hooks up ALL of Binance:
- Spot trading on 500+ pairs
- Cross-conversion paths (BTC→ETH→SOL→USDT)
- Monte Carlo path selection
- Snowball momentum across the entire ecosystem
- Real-time WebSocket feeds
- UK compliance mode

"A song of space and time" - converting endlessly through the labyrinth
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import json
import asyncio
import websockets
import signal
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aureon.exchanges.binance_client import BinanceClient, BinancePoolClient, get_binance_client


@dataclass
class ConversionPath:
    """A path through the conversion labyrinth"""
    from_asset: str
    to_asset: str
    steps: List[Dict]
    momentum_score: float = 0.0
    last_success: Optional[datetime] = None
    total_conversions: int = 0
    total_profit: float = 0.0


@dataclass  
class AssetState:
    """State of an asset in the ecosystem"""
    symbol: str
    balance: float
    price_usd: float = 0.0
    change_1m: float = 0.0
    change_5m: float = 0.0
    change_24h: float = 0.0
    momentum: float = 0.0
    last_update: datetime = field(default_factory=datetime.now)


class S5BinanceEcosystem:
    """
    THE INFINITE BINANCE LABYRINTH
    
    Every asset. Every path. Every conversion.
    Monte Carlo selection through infinite possibilities.
    Snowball momentum that grows with each successful trade.
    """
    
    WS_URL = "wss://stream.binance.com:9443/stream?streams="
    
    # Quote currencies for conversion paths
    QUOTE_CURRENCIES = ['USDT', 'USDC', 'BTC', 'ETH', 'BNB', 'EUR', 'GBP']
    
    # Minimum values
    MIN_TRADE_USD = 11.0  # Binance min notional ~$10
    MIN_MOVE_PCT = 0.02   # 2 basis points
    
    def __init__(self, dry_run: bool = False):
        # Force dry_run off for real trading
        os.environ['BINANCE_DRY_RUN'] = 'true' if dry_run else 'false'
        
        self.binance = get_binance_client()
        self.pool = BinancePoolClient(self.binance)
        self.dry_run = dry_run
        
        # Ecosystem state
        self.assets: Dict[str, AssetState] = {}
        self.prices: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        self.current_prices: Dict[str, Dict] = {}
        self.conversion_paths: Dict[str, ConversionPath] = {}
        self.tradeable_pairs: Set[str] = set()
        
        # Monte Carlo / Snowball
        self.exploration_rate = 0.3  # 30% explore, 70% exploit
        self.snowball_multiplier = 1.0
        self.momentum_scores: Dict[str, float] = {}
        
        # Stats
        self.running = False
        self.start_time = None
        self.trades_executed = 0
        self.total_profit = 0.0
        self.conversions_executed = 0
        self.trade_log = []
        
        # Rate limiting
        self.last_trade_time: Dict[str, datetime] = {}
        self.trade_cooldown = 60  # seconds between trades per pair
        
        signal.signal(signal.SIGINT, self._stop)
        signal.signal(signal.SIGTERM, self._stop)
    
    def _stop(self, *args):
        print("\n🛑 Stopping ecosystem...")
        self.running = False
    
    async def initialize(self):
        """Initialize the ecosystem - load all available pairs and balances"""
        print("""
╔══════════════════════════════════════════════════════════════════╗
║   🌌 S5 BINANCE ECOSYSTEM - THE INFINITE LABYRINTH 🌌           ║
║   Every asset. Every path. Every conversion.                     ║
║   Monte Carlo × Snowball × Real-time × Infinite                  ║
╚══════════════════════════════════════════════════════════════════╝
""")
        
        # Test connection
        print("🔌 Testing Binance connection...")
        if not self.binance.ping():
            print("   ❌ Cannot reach Binance API!")
            return False
        print("   ✅ Connected!")
        
        # Load tradeable pairs
        await self._load_tradeable_pairs()
        
        # Load account balances
        await self._load_balances()
        
        # Build conversion paths
        await self._build_conversion_paths()
        
        return True
    
    async def _load_tradeable_pairs(self):
        """Load all tradeable pairs from Binance"""
        print("\n📊 Loading tradeable pairs...")
        
        try:
            if self.binance.uk_mode:
                # UK restricted - use allowed pairs
                allowed = self.binance.get_allowed_pairs_uk()
                self.tradeable_pairs = allowed
                print(f"   🇬🇧 UK Mode: {len(allowed)} pairs available")
            else:
                # All pairs
                info = self.binance.exchange_info()
                for sym in info.get('symbols', []):
                    if sym.get('status') == 'TRADING' and sym.get('isSpotTradingAllowed'):
                        self.tradeable_pairs.add(sym['symbol'])
                print(f"   ✅ {len(self.tradeable_pairs)} pairs available")
                
        except Exception as e:
            print(f"   ❌ Error loading pairs: {e}")
    
    async def _load_balances(self):
        """Load account balances"""
        print("\n💰 Loading account balances...")
        
        try:
            account = self.binance.account()
            balances = account.get('balances', [])
            
            for b in balances:
                asset = b['asset']
                free = float(b.get('free', 0))
                locked = float(b.get('locked', 0))
                total = free + locked
                
                if total > 0.00001:
                    # Get USD value
                    usd_value = self._get_usd_value(asset, total)
                    
                    self.assets[asset] = AssetState(
                        symbol=asset,
                        balance=total,
                        price_usd=usd_value / total if total > 0 else 0
                    )
                    
                    if usd_value >= 1.0:
                        print(f"   💎 {asset}: {total:.6f} (${usd_value:.2f})")
            
            total_usd = sum(a.price_usd * a.balance for a in self.assets.values())
            print(f"\n   💼 Total Portfolio: ${total_usd:.2f}")
            
        except Exception as e:
            print(f"   ❌ Error loading balances: {e}")
    
    def _get_usd_value(self, asset: str, amount: float) -> float:
        """Get USD value of an asset amount"""
        if asset in ['USDT', 'USDC', 'BUSD', 'USD', 'TUSD', 'FDUSD']:
            return amount
        
        # Try direct USDT pair
        try:
            for quote in ['USDT', 'USDC', 'USD']:
                pair = f"{asset}{quote}"
                if pair in self.tradeable_pairs or not self.tradeable_pairs:
                    price_info = self.binance.best_price(pair, timeout=2)
                    price = float(price_info.get('price', 0))
                    if price > 0:
                        return amount * price
        except:
            pass
        
        # Multi-hop via BTC
        try:
            btc_pair = f"{asset}BTC"
            btc_price = float(self.binance.best_price(btc_pair, timeout=2).get('price', 0))
            btc_usd = float(self.binance.best_price('BTCUSDT', timeout=2).get('price', 0))
            if btc_price > 0 and btc_usd > 0:
                return amount * btc_price * btc_usd
        except:
            pass
        
        return 0.0
    
    async def _build_conversion_paths(self):
        """Build all possible conversion paths"""
        print("\n🔀 Building conversion paths...")
        
        # Get assets we hold
        held_assets = [a for a, s in self.assets.items() if s.balance * s.price_usd >= 1.0]
        
        # Build paths from each held asset to quote currencies
        paths_built = 0
        
        for asset in held_assets:
            for quote in self.QUOTE_CURRENCIES:
                if asset == quote:
                    continue
                
                path = self.pool.find_conversion_path(asset, quote)
                if path:
                    key = f"{asset}→{quote}"
                    self.conversion_paths[key] = ConversionPath(
                        from_asset=asset,
                        to_asset=quote,
                        steps=path
                    )
                    paths_built += 1
        
        # Also build paths between held assets
        for asset1 in held_assets:
            for asset2 in held_assets:
                if asset1 != asset2:
                    path = self.pool.find_conversion_path(asset1, asset2)
                    if path:
                        key = f"{asset1}→{asset2}"
                        self.conversion_paths[key] = ConversionPath(
                            from_asset=asset1,
                            to_asset=asset2,
                            steps=path
                        )
                        paths_built += 1
        
        print(f"   ✅ {paths_built} conversion paths ready")
    
    def _get_ws_streams(self) -> List[str]:
        """Get WebSocket streams for all relevant pairs"""
        streams = []
        
        # Get pairs involving our assets
        for asset in self.assets.keys():
            for quote in ['USDT', 'USDC', 'BTC', 'ETH', 'BNB']:
                pair = f"{asset}{quote}"
                if pair in self.tradeable_pairs:
                    streams.append(f"{pair.lower()}@ticker")
                
                # Also inverse
                inv_pair = f"{quote}{asset}"
                if inv_pair in self.tradeable_pairs:
                    streams.append(f"{inv_pair.lower()}@ticker")
        
        # Deduplicate and limit
        streams = list(set(streams))[:200]  # Binance limit
        return streams
    
    async def run(self):
        """Main run loop"""
        if not await self.initialize():
            return
        
        if not self.assets:
            print("\n⚠️ No assets found! Deposit some funds first.")
            return
        
        if self.dry_run:
            print("\n🧪 DRY RUN MODE - No real trades will execute")
        else:
            print("\n⚠️  Type 'GO' to start REAL trading: ", end='')
            confirm = input()
            if confirm.strip().upper() != 'GO':
                print("Aborted.")
                return
        
        print("\n🔥 ECOSYSTEM ACTIVATED! 🔥\n")
        
        self.running = True
        self.start_time = datetime.now()
        
        await asyncio.gather(
            self._price_feed(),
            self._conversion_loop(),
            self._status_display(),
        )
        
        self._report()
    
    async def _price_feed(self):
        """WebSocket price feed for all pairs"""
        streams = self._get_ws_streams()
        
        if not streams:
            print("⚠️ No streams to connect to")
            return
        
        url = self.WS_URL + "/".join(streams)
        print(f"📡 Connecting to {len(streams)} price feeds...")
        
        reconnect_delay = 1
        
        while self.running:
            try:
                async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:
                    print(f"   ✅ Connected to {len(streams)} streams!")
                    reconnect_delay = 1
                    
                    while self.running:
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=30)
                            data = json.loads(msg)
                            
                            if 'data' in data:
                                await self._process_ticker(data['data'])
                                
                        except asyncio.TimeoutError:
                            continue
                            
            except Exception as e:
                if self.running:
                    print(f"\n   ⚠️ WS error: {e} - reconnecting in {reconnect_delay}s...")
                    await asyncio.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 2, 30)
    
    async def _process_ticker(self, ticker: Dict):
        """Process incoming ticker data"""
        symbol = ticker.get('s', '')
        price = float(ticker.get('c', 0))
        change_24h = float(ticker.get('P', 0))
        
        if price <= 0:
            return
        
        now = datetime.now()
        
        self.current_prices[symbol] = {
            'price': price,
            'change_24h': change_24h,
            'time': now
        }
        
        # Store price history
        self.prices[symbol].append((now, price))
        
        # Keep 5 minutes of history
        cutoff = now - timedelta(minutes=5)
        self.prices[symbol] = [(t, p) for t, p in self.prices[symbol] if t > cutoff]
        
        # Update momentum scores
        await self._update_momentum(symbol)
    
    async def _update_momentum(self, symbol: str):
        """Calculate momentum score for a symbol"""
        history = self.prices.get(symbol, [])
        
        if len(history) < 10:
            return
        
        current = history[-1][1]
        
        # Calculate multiple timeframe momentum
        momentum = 0.0
        
        # 1 minute momentum
        one_min_ago = datetime.now() - timedelta(minutes=1)
        one_min_prices = [p for t, p in history if t >= one_min_ago]
        if one_min_prices:
            oldest_1m = one_min_prices[0]
            momentum += (current - oldest_1m) / oldest_1m * 100 * 3  # Weight 3x
        
        # 5 minute momentum
        if len(history) > 50:
            oldest_5m = history[0][1]
            momentum += (current - oldest_5m) / oldest_5m * 100
        
        # Store momentum
        self.momentum_scores[symbol] = momentum
    
    async def _conversion_loop(self):
        """Main conversion/trading loop"""
        await asyncio.sleep(10)  # Wait for price data
        
        print("\n🌀 Starting conversion engine...")
        
        while self.running:
            try:
                # Monte Carlo path selection
                selected_path = self._monte_carlo_select()
                
                if selected_path:
                    await self._evaluate_conversion(selected_path)
                
            except Exception as e:
                print(f"\n   ⚠️ Conversion loop error: {e}")
            
            await asyncio.sleep(2)
    
    def _monte_carlo_select(self) -> Optional[ConversionPath]:
        """Monte Carlo weighted path selection"""
        if not self.conversion_paths:
            return None
        
        paths = list(self.conversion_paths.values())
        
        # Exploration vs Exploitation
        if random.random() < self.exploration_rate:
            # Explore: random path
            return random.choice(paths)
        else:
            # Exploit: weight by momentum
            weights = []
            for path in paths:
                # Get momentum of from_asset
                momentum = 0.0
                for quote in ['USDT', 'USDC']:
                    pair = f"{path.from_asset}{quote}"
                    if pair in self.momentum_scores:
                        momentum = abs(self.momentum_scores[pair])
                        break
                
                # Higher momentum = higher weight
                weight = max(0.1, momentum + 1.0) * (1 + path.total_conversions * 0.1)
                weights.append(weight)
            
            # Weighted random selection
            total_weight = sum(weights)
            if total_weight <= 0:
                return random.choice(paths)
            
            r = random.random() * total_weight
            cumulative = 0
            for path, weight in zip(paths, weights):
                cumulative += weight
                if r <= cumulative:
                    return path
            
            return paths[-1]
    
    async def _evaluate_conversion(self, path: ConversionPath):
        """Evaluate and potentially execute a conversion"""
        from_asset = path.from_asset
        to_asset = path.to_asset
        
        # Check cooldown
        key = f"{from_asset}→{to_asset}"
        if key in self.last_trade_time:
            elapsed = (datetime.now() - self.last_trade_time[key]).total_seconds()
            if elapsed < self.trade_cooldown:
                return
        
        # Check if we have enough of from_asset
        if from_asset not in self.assets:
            return
        
        asset_state = self.assets[from_asset]
        usd_value = asset_state.balance * asset_state.price_usd
        
        if usd_value < self.MIN_TRADE_USD:
            return
        
        # Get momentum - are we in a good spot to convert?
        momentum = 0.0
        for quote in ['USDT', 'USDC', 'BTC']:
            pair = f"{from_asset}{quote}"
            if pair in self.momentum_scores:
                momentum = self.momentum_scores[pair]
                break
        
        # Decision: Convert on significant movement
        threshold = self.MIN_MOVE_PCT / self.snowball_multiplier
        
        if abs(momentum) < threshold:
            return
        
        # Calculate conversion amount (25-50% of holding based on momentum)
        pct = min(0.5, 0.25 + abs(momentum) / 10)
        convert_amount = asset_state.balance * pct
        convert_value = convert_amount * asset_state.price_usd
        
        if convert_value < self.MIN_TRADE_USD:
            return
        
        # Direction: sell on up momentum, buy on down momentum
        # If from_asset is going UP, we SELL it (convert to something else)
        # If from_asset is going DOWN, we might want to HOLD or convert to stablecoin
        
        action = "CONVERT" if momentum > 0 else "HEDGE"
        
        print(f"\n   🔄 {action}: {convert_amount:.6f} {from_asset} → {to_asset}")
        print(f"      Momentum: {momentum:+.3f}% | Value: ${convert_value:.2f}")
        print(f"      Path: {' → '.join([s['pair'] for s in path.steps])}")
        
        if self.dry_run:
            print(f"      🧪 DRY RUN - Would execute")
            self._record_trade(path, convert_amount, convert_value, momentum, dry_run=True)
            return
        
        # Execute the conversion
        try:
            result = self.pool.convert_crypto(
                from_asset=from_asset,
                to_asset=to_asset,
                amount=convert_amount
            )
            
            if result.get('success'):
                final_amount = result.get('final_amount', 0)
                
                # Update local state
                self.assets[from_asset].balance -= convert_amount
                if to_asset in self.assets:
                    self.assets[to_asset].balance += final_amount
                else:
                    self.assets[to_asset] = AssetState(
                        symbol=to_asset,
                        balance=final_amount,
                        price_usd=self._get_usd_value(to_asset, 1)
                    )
                
                # Estimate profit (simplified)
                profit_est = convert_value * abs(momentum) / 100
                
                # Update stats
                self.conversions_executed += 1
                self.total_profit += profit_est
                self.snowball_multiplier *= 1.005  # Grow snowball
                
                path.total_conversions += 1
                path.total_profit += profit_est
                path.last_success = datetime.now()
                
                self.last_trade_time[key] = datetime.now()
                
                self._record_trade(path, convert_amount, convert_value, momentum, profit_est)
                
                print(f"      ✅ DONE! Got {final_amount:.6f} {to_asset}")
                print(f"      💰 Est profit: ${profit_est:.4f} | Snowball: {self.snowball_multiplier:.3f}x")
                
            elif result.get('rejected'):
                print(f"      ⚠️ Rejected: {result.get('reason', 'Unknown')}")
            else:
                print(f"      ❌ Failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"      ❌ Error: {e}")
    
    def _record_trade(self, path: ConversionPath, amount: float, value: float, 
                      momentum: float, profit: float = 0, dry_run: bool = False):
        """Record a trade in the log"""
        self.trade_log.append({
            'time': datetime.now().isoformat(),
            'from': path.from_asset,
            'to': path.to_asset,
            'amount': amount,
            'value_usd': value,
            'momentum': momentum,
            'profit_est': profit,
            'dry_run': dry_run,
            'snowball': self.snowball_multiplier
        })
    
    async def _status_display(self):
        """Display status"""
        while self.running:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            hours = max(0.001, elapsed / 3600)
            velocity = self.total_profit / hours
            
            # Count active streams
            active_prices = len([p for p, h in self.prices.items() if h])
            
            # Top momentum
            top_momentum = sorted(
                [(s, m) for s, m in self.momentum_scores.items()],
                key=lambda x: abs(x[1]),
                reverse=True
            )[:3]
            
            momentum_str = " | ".join([f"{s}:{m:+.2f}%" for s, m in top_momentum]) if top_momentum else "Calculating..."
            
            print(f"\r⏱️ {int(elapsed)}s | 🔄 {self.conversions_executed} | "
                  f"💰 ${self.total_profit:.4f} | ⚡${velocity:.2f}/hr | "
                  f"📊 {active_prices} feeds | 🎲 {momentum_str}",
                  end='', flush=True)
            
            await asyncio.sleep(5)
    
    def _report(self):
        """Final report"""
        elapsed = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        print("\n\n" + "="*70)
        print("📊 BINANCE ECOSYSTEM SESSION REPORT")
        print("="*70)
        print(f"⏱️ Runtime: {elapsed:.0f}s ({elapsed/3600:.2f} hours)")
        print(f"🔄 Conversions: {self.conversions_executed}")
        print(f"💰 Est Profit: ${self.total_profit:.4f}")
        print(f"⚡ Velocity: ${self.total_profit/(elapsed/3600) if elapsed > 0 else 0:.2f}/hr")
        print(f"❄️ Snowball: {self.snowball_multiplier:.4f}x")
        
        if self.trade_log:
            print("\n📝 Conversion Log:")
            for t in self.trade_log[-20:]:  # Last 20
                dry = "🧪" if t.get('dry_run') else "✅"
                print(f"   {dry} {t['from']}→{t['to']}: {t['amount']:.6f} (${t['value_usd']:.2f}) [{t['momentum']:+.2f}%]")
        
        # Path stats
        if self.conversion_paths:
            print("\n🔀 Top Conversion Paths:")
            sorted_paths = sorted(
                self.conversion_paths.values(),
                key=lambda p: p.total_conversions,
                reverse=True
            )[:10]
            for p in sorted_paths:
                if p.total_conversions > 0:
                    print(f"   {p.from_asset}→{p.to_asset}: {p.total_conversions} conversions, ${p.total_profit:.4f}")
        
        print("="*70)
        
        # Save state
        try:
            with open('binance_ecosystem_state.json', 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'conversions': self.conversions_executed,
                    'profit': self.total_profit,
                    'snowball': self.snowball_multiplier,
                    'trade_log': self.trade_log[-100:]
                }, f, indent=2)
            print("\n💾 State saved to binance_ecosystem_state.json")
        except Exception as e:
            print(f"\n⚠️ Failed to save state: {e}")


async def main():
    # Check for dry run flag
    dry_run = '--dry-run' in sys.argv or '-d' in sys.argv
    
    ecosystem = S5BinanceEcosystem(dry_run=dry_run)
    await ecosystem.run()


if __name__ == "__main__":
    asyncio.run(main())
