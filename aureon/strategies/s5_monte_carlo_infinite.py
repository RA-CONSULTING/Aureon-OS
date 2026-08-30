#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║   🌌 MONTE CARLO INFINITE LABYRINTH 🌌                                        ║
║   A SONG OF SPACE AND TIME                                                    ║
║                                                                               ║
║   Every crypto. Every alt coin. Every path through the labyrinth.             ║
║   Snowball momentum. Speed and math. The song that never ends.                ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import json
import asyncio
import websockets
import signal
import math
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client


@dataclass
class PathNode:
    """A node in the labyrinth - a single market"""
    symbol: str
    binance_symbol: str
    kraken_pair: str
    price: float = 0.0
    price_history: List[tuple] = field(default_factory=list)
    momentum: float = 0.0
    volatility: float = 0.0
    last_trade_time: datetime = None
    trades_count: int = 0
    profit: float = 0.0


class MonteCarloInfiniteLabyrinth:
    """
    THE INFINITE LABYRINTH
    ======================
    - Opens ALL Kraken markets
    - Watches via Binance WebSocket
    - Monte Carlo path selection
    - Snowball momentum trading
    - Never ends, just evolves
    """
    
    # Binance combined stream (max 1024 streams)
    WS_URL = "wss://stream.binance.com:9443/stream?streams="
    
    # ALL THE MARKETS - Map Kraken to Binance
    KRAKEN_TO_BINANCE = {
        # Major coins
        'XXBTZUSD': 'BTCUSDT', 'XETHZUSD': 'ETHUSDT',
        'ATOMUSD': 'ATOMUSDT', 'SOLUSD': 'SOLUSDT', 'DOTUSD': 'DOTUSDT',
        'ADAUSD': 'ADAUSDT', 'XRPUSD': 'XRPUSDT', 'DOGEUSD': 'DOGEUSDT',
        'AVAXUSD': 'AVAXUSDT', 'LINKUSD': 'LINKUSDT', 'MATICUSD': 'MATICUSDT',
        'UNIUSD': 'UNIUSDT', 'LTCUSD': 'LTCUSDT', 'BCHUSD': 'BCHUSDT',
        'XLMUSD': 'XLMUSDT', 'ALGOUSD': 'ALGOUSDT', 'VETUSD': 'VETUSDT',
        'ICPUSD': 'ICPUSDT', 'FILUSD': 'FILUSDT', 'APEUSD': 'APEUSDT',
        'SANDUSD': 'SANDUSDT', 'MANAUSD': 'MANAUSDT', 'AXSUSD': 'AXSUSDT',
        'GRTUSD': 'GRTUSDT', 'EOSUSD': 'EOSUSDT', 'AAVEUSD': 'AAVEUSDT',
        'MKRUSD': 'MKRUSDT', 'SNXUSD': 'SNXUSDT', 'COMPUSD': 'COMPUSDT',
        'YFIUSD': 'YFIUSDT', 'SUSHIUSD': 'SUSHIUSDT', 'ZRXUSD': 'ZRXUSDT',
        'BATUSD': 'BATUSDT', 'ENJUSD': 'ENJUSDT', 'CHZUSD': 'CHZUSDT',
        'ANKRUSD': 'ANKRUSDT', 'CRVUSD': 'CRVUSDT', 'KSMUSD': 'KSMUSDT',
        'DASHUSD': 'DASHUSDT', 'ZECUSD': 'ZECUSDT', 'XMRUSD': 'XMRUSDT',
        'ETCUSD': 'ETCUSDT', 'NEOUSD': 'NEOUSDT', 'QTUMUSD': 'QTUMUSDT',
        'OMGUSD': 'OMGUSDT', 'WAVESUSD': 'WAVESUSDT', 'ICXUSD': 'ICXUSDT',
        'LSKUSD': 'LSKUSDT', 'NANOUSD': 'NANOUSDT', 'SCUSD': 'SCUSDT',
        'ZENDUSD': 'ZENUSDT', 'DGBUSD': 'DGBUSDT', 'RVNUSD': 'RVNUSDT',
        # DeFi
        '1INCHUSD': '1INCHUSDT', 'STORJUSD': 'STORJUSDT', 'OCEANUSD': 'OCEANUSDT',
        'RENDUSD': 'RENUSDT', 'LRCUSD': 'LRCUSDT', 'BANDUSD': 'BANDUSDT',
        'NMRUSD': 'NMRUSDT', 'KNCUSD': 'KNCUSDT', 'OXTUSD': 'OXTUSDT',
        'BALUSD': 'BALUSDT', 'REPV2USD': 'REPUSDT', 'MLNUSD': 'MLNUSDT',
        # Gaming/Metaverse
        'GALAUSD': 'GALAUSDT', 'IMXUSD': 'IMXUSDT', 'ILVUSD': 'ILVUSDT',
        'FLOWUSD': 'FLOWUSDT', 'ROSEUSD': 'ROSEUSDT', 'MINAUSD': 'MINAUSDT',
        # Layer 2
        'OPUSD': 'OPUSDT', 'ARBUSD': 'ARBUSDT',
        # AI coins
        'FETUSD': 'FETUSDT', 'AGIXUSD': 'AGIXUSDT', 'RNRUSD': 'RNRUSDT',
        # Meme coins
        'SHIBUSD': 'SHIBUSDT', 'PEPEUSD': 'PEPEUSDT', 'FLOKIUSD': 'FLOKIUSDT',
        'BONKUSD': 'BONKUSDT',
        # More alts
        'NEARUSD': 'NEARUSDT', 'APTUSD': 'APTUSDT', 'SUIUSD': 'SUIUSDT',
        'SEIUMD': 'SEIUSDT', 'TIAUSD': 'TIAUSDT', 'INJUSD': 'INJUSDT',
        'PYTHUSD': 'PYTHUSDT', 'JUPUSD': 'JUPUSDT', 'WUSD': 'WUSDT',
        'STXUSD': 'STXUSDT', 'RUNEUSD': 'RUNEUSDT', 'KASUSD': 'KASUSDT',
        'ORDIUSD': 'ORDIUSDT', 'BLURUSD': 'BLURUSDT', 'CFXUSD': 'CFXUSDT',
        'APEUSDT': 'APEUSDT', 'LDOUSD': 'LDOUSDT', 'RPLUSD': 'RPLUSDT',
        'GMXUSD': 'GMXUSDT', 'DYDXUSD': 'DYDXUSDT', 'MASKUSD': 'MASKUSDT',
        'ENSUSD': 'ENSUSDT', 'WOOUSD': 'WOOUSDT', 'APTUSD': 'APTUSDT',
        'JASMYUSD': 'JASMYUSDT', 'MAGICUSD': 'MAGICUSDT', 'GMTUSD': 'GMTUSDT',
        'HNTUSD': 'HNTUSDT', 'HBARUSD': 'HBARUSDT', 'QNTUSD': 'QNTUSDT',
        'EGLDUSD': 'EGLDUSDT', 'XTZUSD': 'XTZUSDT', 'THETAUSD': 'THETAUSDT',
        'FTMUSD': 'FTMUSDT', 'KLAYUSD': 'KLAYUSDT', 'ZILUSD': 'ZILUSDT',
        'ONEUSD': 'ONEUSDT', 'HOTUSD': 'HOTUSDT', 'CELOUSD': 'CELOUSDT',
        'IOSTUSD': 'IOSTUSDT', 'ONTUSD': 'ONTUSDT', 'IOTXUSD': 'IOTXUSDT',
        'CKBUSD': 'CKBUSDT', 'SKLUSD': 'SKLUSDT', 'AUDIOUSD': 'AUDIOUSDT',
        'LIVEPEERUSD': 'LPTUSDT', 'API3USD': 'API3USDT', 'CTSIUSD': 'CTSIUSDT',
        'ARUSD': 'ARUSDT', 'JASMYUSD': 'JASMYUSDT',
    }
    
    # Minimum trade sizes for Kraken
    MIN_ORDER_SIZES = {
        'BTC': 0.0001, 'ETH': 0.001, 'SOL': 0.01, 'ATOM': 0.1, 'DOT': 0.1,
        'ADA': 1, 'XRP': 1, 'DOGE': 10, 'SHIB': 100000, 'PEPE': 1000000,
        'DEFAULT': 1  # $1 minimum for most
    }
    
    def __init__(self):
        self.kraken = get_kraken_client()
        
        # The labyrinth - all market paths
        self.paths: Dict[str, PathNode] = {}
        self.active_paths: Set[str] = set()
        
        # Holdings
        self.holdings: Dict[str, float] = {}
        self.usd_balance: float = 0.0
        
        # Monte Carlo state
        self.momentum_scores: Dict[str, float] = defaultdict(float)
        self.path_weights: Dict[str, float] = defaultdict(lambda: 1.0)
        self.exploration_rate: float = 0.3  # 30% explore, 70% exploit
        
        # Stats
        self.running = False
        self.start_time = None
        self.total_trades = 0
        self.total_profit = 0.0
        self.snowball_multiplier = 1.0
        self.trade_log: List[dict] = []
        
        # Async state
        self.ws_connected = False
        self.price_updates = 0
        
        signal.signal(signal.SIGINT, self._stop)
        signal.signal(signal.SIGTERM, self._stop)
    
    def _stop(self, *args):
        print("\n\n🛑 The song pauses... but the labyrinth remains...")
        self.running = False
    
    def banner(self):
        print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║   ███╗   ███╗ ██████╗ ███╗   ██╗████████╗███████╗     ██████╗ █████╗ ██████╗  ║
║   ████╗ ████║██╔═══██╗████╗  ██║╚══██╔══╝██╔════╝    ██╔════╝██╔══██╗██╔══██╗ ║
║   ██╔████╔██║██║   ██║██╔██╗ ██║   ██║   █████╗      ██║     ███████║██████╔╝ ║
║   ██║╚██╔╝██║██║   ██║██║╚██╗██║   ██║   ██╔══╝      ██║     ██╔══██║██╔══██╗ ║
║   ██║ ╚═╝ ██║╚██████╔╝██║ ╚████║   ██║   ███████╗    ╚██████╗██║  ██║██║  ██║ ║
║   ╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   ╚══════╝     ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ║
║                                                                               ║
║   ██╗███╗   ██╗███████╗██╗███╗   ██╗██╗████████╗███████╗                      ║
║   ██║████╗  ██║██╔════╝██║████╗  ██║██║╚══██╔══╝██╔════╝                      ║
║   ██║██╔██╗ ██║█████╗  ██║██╔██╗ ██║██║   ██║   █████╗                        ║
║   ██║██║╚██╗██║██╔══╝  ██║██║╚██╗██║██║   ██║   ██╔══╝                        ║
║   ██║██║ ╚████║██║     ██║██║ ╚████║██║   ██║   ███████╗                      ║
║   ╚═╝╚═╝  ╚═══╝╚═╝     ╚═╝╚═╝  ╚═══╝╚═╝   ╚═╝   ╚══════╝                      ║
║                                                                               ║
║   🌌 A SONG OF SPACE AND TIME - EVERY CRYPTO, EVERY PATH 🌌                  ║
║   ❄️  SNOWBALL MOMENTUM | SPEED & MATH | NEVER ENDS  ❄️                       ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
""")
    
    def load_all_markets(self):
        """Load ALL available Kraken markets"""
        print("\n   🌌 OPENING ALL PATHS IN THE LABYRINTH...")
        
        # Build paths for all mappable pairs
        for kraken_pair, binance_sym in self.KRAKEN_TO_BINANCE.items():
            base = kraken_pair.replace('USD', '').replace('ZUSD', '').replace('Z', '').replace('X', '')
            self.paths[binance_sym] = PathNode(
                symbol=base,
                binance_symbol=binance_sym,
                kraken_pair=kraken_pair if 'Z' not in kraken_pair else kraken_pair.replace('ZUSD', 'USD'),
            )
        
        print(f"      ✅ Opened {len(self.paths)} paths through the labyrinth")
        return True
    
    def load_holdings(self):
        """Load current holdings from Kraken"""
        print("\n   💰 LOADING YOUR ARSENAL...")
        
        try:
            balance = self.kraken.get_account_balance()
            if not balance:
                print("      ⚠️ Could not load balance")
                return True
            
            total_value = 0.0
            for asset, amount in balance.items():
                if amount > 0.0001:
                    self.holdings[asset] = amount
                    
                    if asset in ['USD', 'ZUSD']:
                        self.usd_balance += amount
                        total_value += amount
                    elif asset in ['USDT', 'USDC', 'TUSD']:
                        total_value += amount
                    else:
                        # Estimate value
                        est = self._estimate_value(asset, amount)
                        total_value += est
                        if est > 0.10:
                            print(f"      💎 {asset}: {amount:.4f} (~${est:.2f})")
            
            print(f"\n      🏦 Total Portfolio: ~${total_value:.2f}")
            print(f"      💵 USD Available: ${self.usd_balance:.2f}")
            
            return True
            
        except Exception as e:
            print(f"      ❌ Error: {e}")
            return True
    
    def _estimate_value(self, asset: str, amount: float) -> float:
        """Rough USD value estimate"""
        prices = {
            'XXBT': 95000, 'XBT': 95000, 'BTC': 95000,
            'XETH': 3400, 'ETH': 3400,
            'SOL': 200, 'ATOM': 9, 'DOT': 7, 'ADA': 0.9, 'XRP': 2.2,
            'DOGE': 0.32, 'SHIB': 0.00002, 'LINK': 22, 'AVAX': 38,
            'LUNA': 0.0001, 'AIR': 0.01, 'MON': 0.05, 'DASH': 42,
        }
        return amount * prices.get(asset, 0.0)
    
    async def run(self):
        """THE INFINITE SONG BEGINS"""
        self.banner()
        self.load_all_markets()
        self.load_holdings()
        
        # Confirmation
        print("\n" + "="*70)
        print("   🌌 THE INFINITE LABYRINTH AWAITS 🌌")
        print("="*70)
        print(f"   Markets: {len(self.paths)} paths")
        print(f"   Strategy: Monte Carlo + Momentum Snowball")
        print(f"   Mode: REAL TRADING")
        print("\n   Type 'INFINITE' to begin the song: ", end='')
        
        confirm = input()
        if confirm.strip().upper() != 'INFINITE':
            print("   The labyrinth sleeps...")
            return
        
        print("\n   🎵🌌 THE SONG OF SPACE AND TIME BEGINS 🌌🎵\n")
        
        self.running = True
        self.start_time = datetime.now()
        
        await asyncio.gather(
            self._multi_price_feed(),
            self._monte_carlo_trader(),
            self._momentum_calculator(),
            self._status_display(),
        )
        
        self._final_report()
    
    async def _multi_price_feed(self):
        """Connect to multiple Binance streams"""
        # Split into chunks (max 200 per connection for stability)
        symbols = list(self.paths.keys())
        chunk_size = 200
        chunks = [symbols[i:i+chunk_size] for i in range(0, len(symbols), chunk_size)]
        
        print(f"   📡 Connecting to {len(chunks)} WebSocket streams...")
        
        # Run multiple WebSocket connections
        tasks = [self._ws_connection(chunk, i) for i, chunk in enumerate(chunks)]
        await asyncio.gather(*tasks)
    
    async def _ws_connection(self, symbols: List[str], conn_id: int):
        """Single WebSocket connection for a chunk of symbols"""
        streams = [f"{s.lower()}@ticker" for s in symbols]
        url = self.WS_URL + "/".join(streams)
        
        while self.running:
            try:
                async with websockets.connect(url, ping_interval=20) as ws:
                    self.ws_connected = True
                    
                    while self.running:
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=10)
                            data = json.loads(msg)
                            
                            if 'data' in data:
                                t = data['data']
                                symbol = t.get('s', '')
                                price = float(t.get('c', 0))
                                change_24h = float(t.get('P', 0))
                                volume = float(t.get('v', 0))
                                
                                if price > 0 and symbol in self.paths:
                                    node = self.paths[symbol]
                                    node.price = price
                                    node.price_history.append((datetime.now(), price))
                                    
                                    # Keep 5 min history
                                    cutoff = datetime.now() - timedelta(minutes=5)
                                    node.price_history = [(t, p) for t, p in node.price_history if t > cutoff]
                                    
                                    # Update momentum
                                    if len(node.price_history) >= 2:
                                        oldest = node.price_history[0][1]
                                        node.momentum = (price - oldest) / oldest * 100
                                    
                                    self.price_updates += 1
                                    self.active_paths.add(symbol)
                                    
                        except asyncio.TimeoutError:
                            continue
                            
            except Exception as e:
                if self.running:
                    await asyncio.sleep(5)
    
    async def _momentum_calculator(self):
        """Calculate momentum scores for Monte Carlo selection"""
        while self.running:
            try:
                for symbol, node in self.paths.items():
                    if len(node.price_history) < 5:
                        continue
                    
                    # Calculate volatility
                    prices = [p for _, p in node.price_history[-20:]]
                    if len(prices) >= 5:
                        node.volatility = (max(prices) - min(prices)) / min(prices) * 100
                    
                    # Momentum score = volatility * abs(momentum)
                    score = node.volatility * (1 + abs(node.momentum))
                    
                    # Boost successful paths (snowball effect)
                    if node.profit > 0:
                        score *= (1 + node.profit * 10)
                    
                    self.momentum_scores[symbol] = score
                    self.path_weights[symbol] = max(0.1, score)
                
                await asyncio.sleep(2)
                
            except Exception:
                await asyncio.sleep(5)
    
    async def _monte_carlo_trader(self):
        """Monte Carlo path selection and trading"""
        await asyncio.sleep(10)  # Wait for price data
        
        while self.running:
            try:
                # Select paths using Monte Carlo
                selected = self._monte_carlo_select(count=10)
                
                for symbol in selected:
                    if symbol not in self.paths:
                        continue
                    
                    node = self.paths[symbol]
                    
                    if not node.price or len(node.price_history) < 5:
                        continue
                    
                    # Rate limit per path
                    if node.last_trade_time:
                        if (datetime.now() - node.last_trade_time).seconds < 30:
                            continue
                    
                    # Check for opportunity
                    opportunity = self._evaluate_opportunity(node)
                    
                    if opportunity:
                        await self._execute_trade(opportunity)
                
                # Adaptive delay based on activity
                await asyncio.sleep(1)
                
            except Exception as e:
                await asyncio.sleep(5)
    
    def _monte_carlo_select(self, count: int = 10) -> List[str]:
        """Select paths using Monte Carlo weighted by momentum"""
        active = [s for s in self.active_paths if self.momentum_scores.get(s, 0) > 0]
        
        if not active:
            return []
        
        # Deterministic ranking over observed momentum/path weights.
        return sorted(
            active,
            key=lambda symbol: (self.path_weights.get(symbol, 1.0), symbol),
            reverse=True,
        )[: min(count, len(active))]
    
    def _evaluate_opportunity(self, node: PathNode) -> Optional[dict]:
        """Evaluate if a path has a trading opportunity"""
        if not node.price_history or len(node.price_history) < 5:
            return None
        
        momentum = node.momentum
        volatility = node.volatility
        
        # Snowball threshold: decreases with success
        threshold = max(0.01, 0.05 / self.snowball_multiplier)
        
        # Strong momentum in either direction
        if abs(momentum) >= threshold:
            side = 'SELL' if momentum > 0 else 'BUY'
            
            # Check if we have the asset to sell
            base_asset = node.symbol
            
            # Map binance symbol to check holdings
            holding_names = [base_asset]
            if base_asset == 'BTC':
                holding_names = ['XXBT', 'XBT', 'BTC']
            elif base_asset == 'ETH':
                holding_names = ['XETH', 'ETH']
            
            have_asset = False
            available = 0.0
            for name in holding_names:
                if name in self.holdings and self.holdings[name] > 0.001:
                    have_asset = True
                    available = self.holdings[name]
                    break
            
            # Also check without prefix for assets like ATOM, DASH
            if not have_asset:
                for h_name, h_amount in self.holdings.items():
                    if base_asset.upper() in h_name.upper() and h_amount > 0.001:
                        have_asset = True
                        available = h_amount
                        break
            
            if side == 'SELL':
                if not have_asset:
                    return None
                
                # Calculate sell amount
                sell_pct = min(0.25, 0.05 + abs(momentum) / 10)
                quantity = available * sell_pct
                value = quantity * node.price
                
                if value < 1.0:  # Kraken minimum
                    return None
                
            else:  # BUY
                if self.usd_balance < 1.0:
                    return None
                
                buy_value = min(self.usd_balance * 0.25, 10.0)  # Max $10 per buy
                quantity = buy_value / node.price
                value = buy_value
            
            return {
                'node': node,
                'side': side,
                'quantity': quantity,
                'value': value,
                'momentum': momentum,
                'volatility': volatility,
            }
        
        return None
    
    def _to_kraken_asset(self, symbol: str) -> str:
        """Convert to Kraken asset name"""
        mappings = {
            'BTC': 'XXBT', 'ETH': 'XETH', 'XRP': 'XXRP',
        }
        return mappings.get(symbol, symbol)
    
    async def _execute_trade(self, opp: dict):
        """Execute a trade through the labyrinth"""
        node = opp['node']
        side = opp['side']
        quantity = opp['quantity']
        value = opp['value']
        
        # Find correct Kraken pair
        kraken_pair = None
        for kp, bs in self.KRAKEN_TO_BINANCE.items():
            if bs == node.binance_symbol:
                kraken_pair = kp.replace('ZUSD', 'USD').replace('XXBT', 'XBT').replace('XETH', 'ETH')
                break
        
        if not kraken_pair:
            return
        
        print(f"\n   🌀 {side} {quantity:.6f} {node.symbol} @ ${node.price:.4f}")
        print(f"      📈 Momentum: {opp['momentum']:+.2f}% | Vol: {opp['volatility']:.2f}%")
        
        try:
            result = self.kraken.place_market_order(
                symbol=kraken_pair,
                side=side.lower(),
                quantity=quantity
            )
            
            if result and 'error' not in str(result).lower():
                self.total_trades += 1
                
                # Estimate profit
                est_profit = value * abs(opp['momentum']) / 100
                self.total_profit += est_profit
                node.profit += est_profit
                node.trades_count += 1
                node.last_trade_time = datetime.now()
                
                # Snowball effect: increase multiplier on success
                self.snowball_multiplier *= 1.01
                
                # Update holdings
                kraken_asset = self._to_kraken_asset(node.symbol)
                if side == 'SELL':
                    if kraken_asset in self.holdings:
                        self.holdings[kraken_asset] -= quantity
                    self.usd_balance += value * 0.997  # Less fees
                else:
                    self.holdings[kraken_asset] = self.holdings.get(kraken_asset, 0) + quantity
                    self.usd_balance -= value
                
                # Boost path weight (reinforcement)
                self.path_weights[node.binance_symbol] *= 1.5
                
                self.trade_log.append({
                    'time': datetime.now().isoformat(),
                    'symbol': node.symbol,
                    'side': side,
                    'quantity': quantity,
                    'price': node.price,
                    'value': value,
                    'momentum': opp['momentum'],
                })
                
                print(f"      ✅ DONE! Est profit: ${est_profit:.4f} | Snowball: {self.snowball_multiplier:.2f}x")
            else:
                # Reduce path weight on failure
                self.path_weights[node.binance_symbol] *= 0.8
                if 'Insufficient' in str(result):
                    print(f"      ⚠️ Insufficient funds")
                else:
                    print(f"      ⚠️ {str(result)[:50]}")
                
        except Exception as e:
            self.path_weights[node.binance_symbol] *= 0.5
            err_msg = str(e)[:50]
            if 'Insufficient' not in err_msg and 'Unknown' not in err_msg:
                print(f"      ❌ {err_msg}")
    
    async def _status_display(self):
        """Display the song's progress"""
        while self.running:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            hours = max(0.001, elapsed / 3600)
            velocity = self.total_profit / hours
            
            active = len(self.active_paths)
            
            # Find top momentum paths
            top_momentum = sorted(
                [(s, self.momentum_scores.get(s, 0)) for s in self.active_paths],
                key=lambda x: abs(x[1]), reverse=True
            )[:3]
            
            top_str = " | ".join([f"{s[:4]}:{m:+.1f}%" for s, m in top_momentum]) if top_momentum else "..."
            
            ws_status = "🟢" if self.ws_connected else "🔴"
            
            print(f"\r   {ws_status} ⏱️ {int(elapsed)}s | 🌌 {active} paths | "
                  f"💰 {self.total_trades} trades | 💵 ${self.total_profit:.4f} | "
                  f"⚡ ${velocity:.2f}/hr | ❄️ {self.snowball_multiplier:.2f}x | 🔥 {top_str}",
                  end='', flush=True)
            
            await asyncio.sleep(5)
    
    def _final_report(self):
        """The song's summary"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        hours = max(0.001, elapsed / 3600)
        
        print("\n\n" + "="*70)
        print("   🌌 THE SONG PAUSES - LABYRINTH REPORT 🌌")
        print("="*70)
        print(f"   ⏱️  Runtime: {elapsed:.0f}s ({hours:.2f} hours)")
        print(f"   🌐 Active Paths: {len(self.active_paths)}")
        print(f"   📊 Price Updates: {self.price_updates:,}")
        print(f"   💰 Total Trades: {self.total_trades}")
        print(f"   💵 Est Profit: ${self.total_profit:.4f}")
        print(f"   ⚡ Velocity: ${self.total_profit/hours:.2f}/hr")
        print(f"   ❄️  Snowball: {self.snowball_multiplier:.2f}x")
        
        # Top performing paths
        if self.trade_log:
            path_profits = defaultdict(float)
            for t in self.trade_log:
                path_profits[t['symbol']] += t['value'] * abs(t['momentum']) / 100
            
            print("\n   🏆 TOP PATHS:")
            for symbol, profit in sorted(path_profits.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"      {symbol}: ${profit:.4f}")
        
        if self.trade_log:
            print("\n   📝 RECENT TRADES:")
            for t in self.trade_log[-10:]:
                print(f"      {t['side']} {t['quantity']:.4f} {t['symbol']} @ ${t['price']:.4f} ({t['momentum']:+.2f}%)")
        
        print("="*70)
        print("   🎵 The labyrinth awaits your return... 🎵")
        print("="*70 + "\n")


async def main():
    labyrinth = MonteCarloInfiniteLabyrinth()
    await labyrinth.run()


if __name__ == "__main__":
    asyncio.run(main())
