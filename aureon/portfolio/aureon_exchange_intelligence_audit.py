"""
🧠 AUREON EXCHANGE INTELLIGENCE AUDIT
═══════════════════════════════════════════════════════════════

SMART QUESTIONS FOR EACH EXCHANGE:
1. What have I BOUGHT? (Buy trades)
2. What have I SOLD? (Sell trades)
3. What IDs exist? (Order/Trade IDs)
4. What codes/symbols are there? (All traded pairs)
5. What's the pattern? (Activity timeline)

This is QUEEN-LEVEL INTELLIGENCE - understanding the full picture
by interrogating the APIs for historical data, not just balances.
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys, os
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        def _is_buffer_valid(stream):
            if not hasattr(stream, 'buffer'):
                return False
            try:
                return stream.buffer is not None and not stream.buffer.closed
            except (ValueError, AttributeError):
                return False
        if _is_buffer_valid(sys.stdout) and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if _is_buffer_valid(sys.stderr) and not _is_utf8_wrapper(sys.stderr):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Set
from dataclasses import dataclass, field
from collections import defaultdict

@dataclass
class ExchangeIntelligence:
    """Intelligence gathered from an exchange."""
    exchange: str
    
    # Trade intelligence
    total_buys: int = 0
    total_sells: int = 0
    buy_symbols: Set[str] = field(default_factory=set)
    sell_symbols: Set[str] = field(default_factory=set)
    all_symbols_traded: Set[str] = field(default_factory=set)
    
    # Order intelligence
    total_orders: int = 0
    open_orders: int = 0
    closed_orders: int = 0
    order_ids: List[str] = field(default_factory=list)
    
    # Current holdings
    current_positions: Dict[str, float] = field(default_factory=dict)
    
    # Activity patterns
    first_trade_date: str = None
    last_trade_date: str = None
    most_traded_symbol: str = None
    trade_count_by_symbol: Dict[str, int] = field(default_factory=dict)
    
    # Value metrics
    total_bought_value: float = 0.0
    total_sold_value: float = 0.0
    net_flow: float = 0.0  # bought - sold

class AureonExchangeIntelligenceAudit:
    """
    🧠 Ask smart questions to exchange APIs.
    
    Instead of "What's my balance?"
    Ask: "What have I bought? What sold? What IDs exist? What symbols?"
    """
    
    def __init__(self):
        """Initialize audit system."""
        self.intelligences = {}
    
    def audit_binance(self) -> ExchangeIntelligence:
        """Interrogate Binance for intelligence."""
        intel = ExchangeIntelligence(exchange='binance')
        
        try:
            from aureon.exchanges.binance_client import BinanceClient, get_binance_client
            client = get_binance_client()
            
            print("🔍 Interrogating Binance API...")
            
            # Q1: What positions exist NOW?
            balances = client.get_balance()
            intel.current_positions = {k: v for k, v in balances.items() if v > 0}
            print(f"   ✅ Current positions: {len(intel.current_positions)}")
            
            # Q2: What have I traded? (Check cost basis history)
            try:
                if os.path.exists('cost_basis_history.json'):
                    with open('cost_basis_history.json', 'r') as f:
                        data = json.load(f)
                        positions = data.get('positions', {})
                        
                        # Extract Binance trades
                        for key, pos in positions.items():
                            if 'binance' in key.lower() or pos.get('exchange') == 'binance':
                                symbol = pos.get('symbol', '')
                                trade_count = pos.get('trade_count', 0)
                                
                                if symbol:
                                    intel.all_symbols_traded.add(symbol)
                                    intel.trade_count_by_symbol[symbol] = trade_count
                                    intel.total_buys += trade_count  # Assume buys for now
                                
                                # Check order IDs
                                order_ids = pos.get('order_ids', [])
                                intel.order_ids.extend(order_ids)
                                
                                # Value tracking
                                total_cost = pos.get('total_cost', 0)
                                intel.total_bought_value += total_cost
                
                print(f"   ✅ Symbols traded: {len(intel.all_symbols_traded)}")
                print(f"   ✅ Trade count: {intel.total_buys}")
                print(f"   ✅ Order IDs tracked: {len(intel.order_ids)}")
                
            except Exception as e:
                print(f"   ⚠️  Cost basis read error: {e}")
            
            # Q3: What's the most traded symbol?
            if intel.trade_count_by_symbol:
                intel.most_traded_symbol = max(
                    intel.trade_count_by_symbol.items(),
                    key=lambda x: x[1]
                )[0]
            
            # Q4: Calculate net flow
            intel.net_flow = intel.total_bought_value - intel.total_sold_value
            
        except Exception as e:
            print(f"   ❌ Binance audit error: {e}")
        
        return intel
    
    def audit_kraken(self) -> ExchangeIntelligence:
        """Interrogate Kraken for intelligence."""
        intel = ExchangeIntelligence(exchange='kraken')
        
        try:
            from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
            client = get_kraken_client()
            
            print("🔍 Interrogating Kraken API...")
            
            # Q1: Check state file (more reliable than rate-limited API)
            if os.path.exists('aureon_kraken_state.json'):
                with open('aureon_kraken_state.json', 'r') as f:
                    state = json.load(f)
                    
                    # Current positions
                    positions = state.get('positions', {})
                    for symbol, pos in positions.items():
                        qty = pos.get('quantity', 0)
                        if qty > 0:
                            intel.current_positions[symbol] = qty
                            intel.all_symbols_traded.add(symbol)
                    
                    # Metrics from state
                    intel.total_buys = state.get('total_trades', 0)
                    intel.total_bought_value = state.get('balance', 0)
                    
                    print(f"   ✅ Current positions: {len(intel.current_positions)}")
                    print(f"   ✅ Symbols traded: {len(intel.all_symbols_traded)}")
                    print(f"   ✅ Total trades: {intel.total_buys}")
            
            # Q2: Try to get trade history from API (might rate limit)
            try:
                trades = client.get_trades_history()
                if trades:
                    for trade_id, trade in trades.items():
                        intel.order_ids.append(trade_id)
                        symbol = trade.get('pair', '')
                        trade_type = trade.get('type', '')
                        
                        if symbol:
                            intel.all_symbols_traded.add(symbol)
                        
                        if trade_type == 'buy':
                            intel.total_buys += 1
                            intel.buy_symbols.add(symbol)
                        elif trade_type == 'sell':
                            intel.total_sells += 1
                            intel.sell_symbols.add(symbol)
                    
                    print(f"   ✅ Trade IDs found: {len(intel.order_ids)}")
            except Exception as e:
                print(f"   ⚠️  Trade history unavailable: {e}")
        
        except Exception as e:
            print(f"   ❌ Kraken audit error: {e}")
        
        return intel
    
    def audit_alpaca(self) -> ExchangeIntelligence:
        """Interrogate Alpaca for intelligence."""
        intel = ExchangeIntelligence(exchange='alpaca')
        
        try:
            from aureon.exchanges.alpaca_client import AlpacaClient
            client = AlpacaClient()
            
            print("🔍 Interrogating Alpaca API...")
            
            # Q1: Current positions
            try:
                positions = client.get_positions()
                for pos in positions:
                    symbol = pos.get('symbol', '')
                    qty = float(pos.get('qty', 0))
                    
                    if symbol and qty > 0:
                        intel.current_positions[symbol] = qty
                        intel.all_symbols_traded.add(symbol)
                
                print(f"   ✅ Current positions: {len(intel.current_positions)}")
            except:
                pass
            
            # Q2: Get account info
            try:
                account = client.get_account()
                cash = float(account.get('cash', 0))
                intel.total_bought_value = cash  # Available cash
                print(f"   ✅ Account cash: ${cash:.2f}")
            except:
                pass
            
            # Q3: Check activities/orders
            try:
                # Alpaca has activities endpoint
                activities = client.get_activities()
                if activities:
                    for activity in activities:
                        activity_type = activity.get('activity_type', '')
                        symbol = activity.get('symbol', '')
                        
                        if symbol:
                            intel.all_symbols_traded.add(symbol)
                        
                        if activity_type in ['FILL', 'BUY']:
                            intel.total_buys += 1
                            if symbol:
                                intel.buy_symbols.add(symbol)
                        elif activity_type in ['SELL']:
                            intel.total_sells += 1
                            if symbol:
                                intel.sell_symbols.add(symbol)
                    
                    print(f"   ✅ Activities found: {len(activities)}")
                    print(f"   ✅ Buys: {intel.total_buys}, Sells: {intel.total_sells}")
            except Exception as e:
                print(f"   ⚠️  Activities unavailable: {e}")
        
        except Exception as e:
            print(f"   ❌ Alpaca audit error: {e}")
        
        return intel
    
    def audit_capital(self) -> ExchangeIntelligence:
        """Interrogate Capital.com for intelligence."""
        intel = ExchangeIntelligence(exchange='capital')
        
        try:
            from aureon.exchanges.capital_client import CapitalClient
            client = CapitalClient()
            
            print("🔍 Interrogating Capital.com API...")
            
            # Q1: Current positions
            try:
                positions = client.get_positions()
                for pos_data in positions:
                    pos = pos_data.get('position', {})
                    market = pos_data.get('market', {})
                    
                    symbol = market.get('instrumentName', '')
                    size = float(pos.get('size', 0))
                    deal_id = pos.get('dealId', '')
                    
                    if symbol and size > 0:
                        intel.current_positions[symbol] = size
                        intel.all_symbols_traded.add(symbol)
                    
                    if deal_id:
                        intel.order_ids.append(deal_id)
                
                print(f"   ✅ Current positions: {len(intel.current_positions)}")
                print(f"   ✅ Deal IDs: {len(intel.order_ids)}")
            except:
                pass
            
            # Q2: Account info
            try:
                accounts = client.get_accounts()
                if accounts:
                    balance = float(accounts[0].get('balance', {}).get('balance', 0))
                    intel.total_bought_value = balance
                    print(f"   ✅ Account balance: £{balance:.2f}")
            except:
                pass
        
        except Exception as e:
            print(f"   ❌ Capital.com audit error: {e}")
        
        return intel
    
    def run_full_audit(self):
        """Run intelligence audit on all exchanges."""
        print("\n" + "=" * 80)
        print("🧠 AUREON EXCHANGE INTELLIGENCE AUDIT")
        print("=" * 80)
        print("\nAsking smart questions to every exchange API...\n")
        
        # Audit each exchange
        self.intelligences['binance'] = self.audit_binance()
        print()
        self.intelligences['kraken'] = self.audit_kraken()
        print()
        self.intelligences['alpaca'] = self.audit_alpaca()
        print()
        self.intelligences['capital'] = self.audit_capital()
        
        # Generate intelligence report
        self.print_intelligence_report()
    
    def print_intelligence_report(self):
        """Print comprehensive intelligence report."""
        print("\n" + "=" * 80)
        print("📊 INTELLIGENCE REPORT - WHAT THE QUEEN KNOWS")
        print("=" * 80)
        
        total_symbols = set()
        total_positions = 0
        total_buys = 0
        total_sells = 0
        total_order_ids = 0
        
        for exch, intel in self.intelligences.items():
            print(f"\n🏦 {exch.upper()}")
            print("-" * 80)
            
            # Current state
            print(f"\n   📦 CURRENT HOLDINGS: {len(intel.current_positions)}")
            if intel.current_positions:
                for symbol, qty in list(intel.current_positions.items())[:10]:
                    print(f"      • {symbol:15} {qty:.6f}")
                if len(intel.current_positions) > 10:
                    print(f"      ... and {len(intel.current_positions) - 10} more")
            
            # Trading activity
            print(f"\n   📈 TRADING ACTIVITY:")
            print(f"      Symbols traded:     {len(intel.all_symbols_traded)}")
            print(f"      Buy trades:         {intel.total_buys}")
            print(f"      Sell trades:        {intel.total_sells}")
            print(f"      Net flow:           ${intel.net_flow:,.2f}")
            
            # IDs
            if intel.order_ids:
                print(f"\n   🆔 ORDER/TRADE IDs: {len(intel.order_ids)} tracked")
                print(f"      Latest IDs: {intel.order_ids[:3]}")
            
            # Most active
            if intel.most_traded_symbol:
                count = intel.trade_count_by_symbol.get(intel.most_traded_symbol, 0)
                print(f"\n   🔥 MOST TRADED: {intel.most_traded_symbol} ({count} trades)")
            
            # Symbols
            if intel.all_symbols_traded:
                print(f"\n   💎 ALL SYMBOLS: {', '.join(list(intel.all_symbols_traded)[:15])}")
                if len(intel.all_symbols_traded) > 15:
                    print(f"      ... and {len(intel.all_symbols_traded) - 15} more")
            
            # Aggregate totals
            total_symbols.update(intel.all_symbols_traded)
            total_positions += len(intel.current_positions)
            total_buys += intel.total_buys
            total_sells += intel.total_sells
            total_order_ids += len(intel.order_ids)
        
        # Global intelligence
        print("\n" + "=" * 80)
        print("🌍 GLOBAL INTELLIGENCE")
        print("=" * 80)
        print(f"\n   📊 Total unique symbols traded:    {len(total_symbols)}")
        print(f"   📦 Total current positions:        {total_positions}")
        print(f"   📈 Total buy trades:               {total_buys}")
        print(f"   📉 Total sell trades:              {total_sells}")
        print(f"   🆔 Total order/trade IDs tracked:  {total_order_ids}")
        print(f"   ⚖️  Buy/Sell ratio:                 {total_buys}/{total_sells} = {total_buys/max(total_sells,1):.2f}x")
        
        print("\n" + "=" * 80)
        print("\n✅ QUEEN NOW KNOWS:")
        print("   • What was BOUGHT")
        print("   • What was SOLD")  
        print("   • What IDs exist")
        print("   • What codes/symbols are there")
        print("   • Trading patterns & activity")
        print("\n🧠 This is INTELLIGENCE, not just balance checking!")
        print("=" * 80 + "\n")


###############################################################################
# FIFO FORENSIC AUDIT — THE KING'S ACCOUNTING SYSTEM
###############################################################################
# Every sell matched to its earliest unsold buy. No smoke. Just math and API.
# Cross-verified with deposit/withdrawal ledger for true net P&L.
###############################################################################

import hmac
import hashlib
import base64
import urllib.parse
import requests

@dataclass
class FIFOSymbolResult:
    """FIFO result for a single trading pair."""
    symbol: str
    exchange: str
    total_buys: int = 0
    total_sells: int = 0
    total_volume: float = 0.0
    realized_gross: float = 0.0
    total_fees: float = 0.0
    net_realized: float = 0.0
    remaining_qty: float = 0.0
    remaining_value: float = 0.0
    unrealized_pnl: float = 0.0
    oldest_lot_date: str = None
    oldest_lot_price: float = 0.0
    first_trade: str = None
    last_trade: str = None
    trade_count: int = 0

@dataclass
class ForensicAuditResult:
    """Complete forensic audit result for an exchange."""
    exchange: str
    timestamp: str = ""
    total_buys: int = 0
    total_sells: int = 0
    total_volume: float = 0.0
    total_fees: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    combined_pnl: float = 0.0
    symbols: List = field(default_factory=list)
    deposits_usd: float = 0.0
    withdrawals_usd: float = 0.0
    current_balance_usd: float = 0.0
    ledger_net_pnl: float = 0.0


class FIFOForensicAuditor:
    """
    THE KING'S FORENSIC AUDITOR
    ═══════════════════════════
    Uses FIFO (First-In-First-Out) cost basis matching to calculate
    true realized and unrealized P&L from exchange trade history.
    
    Cross-verifies with deposit/withdrawal ledger for the true
    money-in vs money-out calculation. No smoke. No simulation.
    
    Data sources:
        Binance:  GET /api/v3/account, /api/v3/myTrades, /api/v3/ticker/price
                  GET /sapi/v1/capital/deposit/hisrec, /sapi/v1/capital/withdraw/history
        Kraken:   POST /0/private/Balance, /0/private/TradesHistory, /0/private/Ledgers
                  GET /0/public/Ticker
    """
    
    def __init__(self):
        self._load_env()
    
    def _load_env(self):
        """Load API keys from .env file."""
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        os.environ.setdefault(k.strip(), v.strip())
    
    def _binance_signed(self, endpoint, params=None, method='GET'):
        """Make authenticated Binance API call."""
        api_key = os.environ.get('BINANCE_API_KEY', '')
        api_secret = os.environ.get('BINANCE_API_SECRET', '')
        base_url = 'https://api.binance.com'
        headers = {'X-MBX-APIKEY': api_key}
        
        if params is None:
            params = {}
        params['timestamp'] = str(int(time.time() * 1000))
        query = urllib.parse.urlencode(params)
        sig = hmac.new(api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
        url = f"{base_url}{endpoint}?{query}&signature={sig}"
        
        r = requests.get(url, headers=headers, timeout=15) if method == 'GET' else \
            requests.post(url, headers=headers, timeout=15)
        return r.json() if r.status_code == 200 else {}
    
    def _kraken_private(self, endpoint, data=None):
        """Make authenticated Kraken API call."""
        api_key = os.environ.get('KRAKEN_API_KEY', '')
        api_secret = os.environ.get('KRAKEN_API_SECRET', '')
        
        if data is None:
            data = {}
        url = f'https://api.kraken.com/0/private/{endpoint}'
        data['nonce'] = str(int(time.time() * 1000000))
        postdata = urllib.parse.urlencode(data)
        encoded = (data['nonce'] + postdata).encode()
        message = f'/0/private/{endpoint}'.encode() + hashlib.sha256(encoded).digest()
        sig = hmac.new(base64.b64decode(api_secret), message, hashlib.sha512)
        headers = {
            'API-Key': api_key,
            'API-Sign': base64.b64encode(sig.digest()).decode()
        }
        r = requests.post(url, headers=headers, data=data, timeout=20)
        return r.json()
    
    def _fifo_process(self, trades, prices, quote_assets=('USDT', 'USDC', 'BUSD', 'FDUSD'),
                      is_buyer_key='isBuyer', qty_key='qty', price_key='price',
                      cost_key='quoteQty', fee_key='commission', fee_asset_key='commissionAsset',
                      time_key='time', time_divisor=1000):
        """
        Core FIFO engine. Processes a list of trades for a single symbol.
        Returns (realized_gross, total_fees, buy_queue_remaining, nb, ns, volume).
        """
        buy_queue = []
        realized_gross = 0.0
        total_fees = 0.0
        nb = ns = 0
        volume = 0.0
        
        for t in trades:
            qty = float(t[qty_key])
            price = float(t[price_key])
            cost = float(t.get(cost_key, qty * price))
            fee = float(t.get(fee_key, 0))
            volume += cost
            
            # Convert fee to USD
            if fee_asset_key and t.get(fee_asset_key):
                fa = t[fee_asset_key]
                if fa in quote_assets:
                    fee_usd = fee
                elif f"{fa}USDT" in prices:
                    fee_usd = fee * prices[f"{fa}USDT"]
                elif f"{fa}USDC" in prices:
                    fee_usd = fee * prices[f"{fa}USDC"]
                else:
                    fee_usd = fee * price
            else:
                fee_usd = fee
            total_fees += fee_usd
            
            is_buy = t.get(is_buyer_key, t.get('type') == 'buy')
            
            if is_buy:
                nb += 1
                dt_ts = float(t[time_key]) / time_divisor if time_divisor > 1 else float(t[time_key])
                dt = datetime.utcfromtimestamp(dt_ts).strftime('%Y-%m-%d %H:%M:%S')
                buy_queue.append({'qty': qty, 'price': price, 'date': dt})
            else:
                ns += 1
                sell_remaining = qty
                cost_basis = 0.0
                
                while sell_remaining > 1e-9 and buy_queue:
                    oldest = buy_queue[0]
                    if oldest['qty'] <= sell_remaining + 1e-9:
                        cost_basis += oldest['qty'] * oldest['price']
                        sell_remaining -= oldest['qty']
                        buy_queue.pop(0)
                    else:
                        cost_basis += sell_remaining * oldest['price']
                        oldest['qty'] -= sell_remaining
                        sell_remaining = 0
                
                # Unmatched sell qty = airdrop/transfer (cost basis = 0)
                realized_gross += cost - cost_basis
        
        return realized_gross, total_fees, buy_queue, nb, ns, volume
    
    def audit_binance(self, verbose=True) -> ForensicAuditResult:
        """
        Full FIFO forensic audit of Binance.
        
        API endpoints:
            GET /api/v3/account         — asset balances
            GET /api/v3/myTrades        — full trade history per symbol
            GET /api/v3/ticker/price    — current prices
            GET /sapi/v1/capital/deposit/hisrec   — deposit history
            GET /sapi/v1/capital/withdraw/history  — withdrawal history
        """
        result = ForensicAuditResult(
            exchange='binance',
            timestamp=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        )
        
        if verbose:
            print("\n" + "=" * 90)
            print("  BINANCE — FIFO FORENSIC AUDIT")
            print(f"  Generated: {result.timestamp}")
            print("  Method: FIFO cost basis matching")
            print("=" * 90)
        
        # 1. Get assets with balance
        acc = self._binance_signed('/api/v3/account')
        assets = set()
        for b in acc.get('balances', []):
            if float(b.get('free', 0)) + float(b.get('locked', 0)) > 1e-5:
                assets.add(b['asset'])
        
        # 2. Get current prices
        try:
            pr = requests.get('https://api.binance.com/api/v3/ticker/price', timeout=10)
            prices = {p['symbol']: float(p['price']) for p in pr.json()} if pr.status_code == 200 else {}
        except:
            prices = {}
        
        # 3. Pull trades for every symbol
        traded = {}
        checked = set()
        for asset in sorted(assets):
            for quote in ['USDT', 'USDC']:
                sym = f'{asset}{quote}'
                if sym in checked:
                    continue
                checked.add(sym)
                try:
                    trades = self._binance_signed('/api/v3/myTrades', {'symbol': sym, 'limit': 1000})
                    if isinstance(trades, list) and trades:
                        traded[sym] = sorted(trades, key=lambda x: x['time'])
                    time.sleep(0.05)
                except:
                    pass
        
        if verbose:
            print(f"  Found {len(traded)} symbols with trade history")
        
        # 4. Process each symbol with FIFO
        for sym in sorted(traded.keys()):
            trades = traded[sym]
            realized, fees, queue, nb, ns, vol = self._fifo_process(trades, prices)
            
            net = realized - fees
            rem_qty = sum(b['qty'] for b in queue)
            rem_cost = sum(b['qty'] * b['price'] for b in queue)
            base = sym.replace('USDT', '').replace('USDC', '')
            cp = prices.get(f'{base}USDT', prices.get(f'{base}USDC', 0))
            rem_val = rem_qty * cp
            unrealized = rem_val - rem_cost
            
            sym_result = FIFOSymbolResult(
                symbol=sym, exchange='binance',
                total_buys=nb, total_sells=ns,
                total_volume=vol, realized_gross=realized,
                total_fees=fees, net_realized=net,
                remaining_qty=rem_qty, remaining_value=rem_val,
                unrealized_pnl=unrealized, trade_count=len(trades)
            )
            
            if queue:
                sym_result.oldest_lot_date = queue[0]['date']
                sym_result.oldest_lot_price = queue[0]['price']
            
            first_dt = datetime.utcfromtimestamp(trades[0]['time'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
            last_dt = datetime.utcfromtimestamp(trades[-1]['time'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
            sym_result.first_trade = first_dt
            sym_result.last_trade = last_dt
            
            result.symbols.append(sym_result)
            result.total_buys += nb
            result.total_sells += ns
            result.total_volume += vol
            result.total_fees += fees
            result.realized_pnl += net
            result.unrealized_pnl += unrealized
            
            if verbose and (nb + ns) > 0:
                tag = '  PROFIT' if net > 0.01 else '  LOSS' if net < -0.01 else '  FLAT'
                print(f"    {sym:>15}: {nb:>4}B {ns:>4}S  realized ${net:>+9.2f}{tag}  "
                      f"holding {rem_qty:.4f}=${rem_val:.2f}  unrealized ${unrealized:>+8.2f}")
        
        result.combined_pnl = result.realized_pnl + result.unrealized_pnl
        
        # 5. Deposit/withdrawal ledger
        deposits_resp = self._binance_signed('/sapi/v1/capital/deposit/hisrec')
        withdrawals_resp = self._binance_signed('/sapi/v1/capital/withdraw/history')
        
        for d in (deposits_resp if isinstance(deposits_resp, list) else []):
            coin = d.get('coin', '')
            amt = float(d.get('amount', 0))
            p = prices.get(f'{coin}USDT', prices.get(f'{coin}USDC', 1.0 if coin in ('USDC', 'USDT') else 0))
            result.deposits_usd += amt * p
        
        for w in (withdrawals_resp if isinstance(withdrawals_resp, list) else []):
            coin = w.get('coin', '')
            amt = float(w.get('amount', 0))
            p = prices.get(f'{coin}USDT', prices.get(f'{coin}USDC', 1.0 if coin in ('USDC', 'USDT') else 0))
            result.withdrawals_usd += amt * p
        
        # Current total balance
        for b in acc.get('balances', []):
            total = float(b.get('free', 0)) + float(b.get('locked', 0))
            if total > 1e-5:
                asset = b['asset']
                if asset in ('USDC', 'USDT', 'BUSD', 'FDUSD'):
                    result.current_balance_usd += total
                elif f"{asset}USDT" in prices:
                    result.current_balance_usd += total * prices[f"{asset}USDT"]
                elif f"{asset}USDC" in prices:
                    result.current_balance_usd += total * prices[f"{asset}USDC"]
        
        result.ledger_net_pnl = result.current_balance_usd + result.withdrawals_usd - result.deposits_usd
        
        if verbose:
            self._print_exchange_summary(result)
        
        return result
    
    def audit_kraken(self, verbose=True) -> ForensicAuditResult:
        """
        Full FIFO forensic audit of Kraken.
        
        API endpoints:
            POST /0/private/TradesHistory — full trade history (paginated, 50/page)
            POST /0/private/Balance       — current balances
            POST /0/private/TradeBalance  — Kraken's own valuation
            POST /0/private/Ledgers       — deposit/withdrawal history
            GET  /0/public/Ticker         — current prices
        """
        result = ForensicAuditResult(
            exchange='kraken',
            timestamp=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        )
        
        if verbose:
            print("\n" + "=" * 90)
            print("  KRAKEN — FIFO FORENSIC AUDIT")
            print(f"  Generated: {result.timestamp}")
            print("  Method: FIFO cost basis + ledger cross-verification")
            print("=" * 90)
        
        # 1. Pull ALL trades with pagination
        all_trades = {}
        offset = 0
        while True:
            time.sleep(3)
            resp = self._kraken_private('TradesHistory', {'ofs': offset, 'trades': True})
            if resp.get('error'):
                errs = resp['error']
                if any('Rate' in str(e) for e in errs):
                    if verbose:
                        print(f"    [rate limited at offset {offset}, waiting 10s...]")
                    time.sleep(10)
                    continue
                if any('nonce' in str(e).lower() for e in errs):
                    time.sleep(3)
                    continue
                break
            trades = resp.get('result', {}).get('trades', {})
            if not trades:
                break
            all_trades.update(trades)
            count = resp.get('result', {}).get('count', 0)
            offset += len(trades)
            if verbose:
                print(f"    Fetched {len(all_trades)}/{count} trades...")
            if offset >= count:
                break
        
        # Organize by pair
        pair_trades = defaultdict(list)
        for tid, t in all_trades.items():
            t['_id'] = tid
            pair_trades[t['pair']].append(t)
        for pair in pair_trades:
            pair_trades[pair].sort(key=lambda x: float(x['time']))
        
        # Get current prices
        all_pairs = list(pair_trades.keys())
        try:
            pair_str = ','.join(all_pairs)
            pr = requests.get(f'https://api.kraken.com/0/public/Ticker?pair={pair_str}', timeout=15)
            ticker = pr.json().get('result', {})
        except:
            ticker = {}
        
        # Build price map from ticker
        prices = {}
        for tkey, tval in ticker.items():
            prices[tkey] = float(tval['c'][0])
        
        if verbose:
            print(f"  Found {len(pair_trades)} traded pairs, {len(all_trades)} total trades")
        
        # 2. Process each pair with FIFO
        for pair in sorted(pair_trades.keys()):
            trades = pair_trades[pair]
            buy_queue = []
            realized_gross = 0.0
            fees_total = 0.0
            nb = ns = 0
            vol = 0.0
            
            for t in trades:
                qty = float(t['vol'])
                price = float(t['price'])
                cost = float(t['cost'])
                fee = float(t['fee'])
                fees_total += fee
                vol += cost
                
                if t['type'] == 'buy':
                    nb += 1
                    dt = datetime.utcfromtimestamp(float(t['time'])).strftime('%Y-%m-%d %H:%M:%S')
                    buy_queue.append({'qty': qty, 'price': price, 'date': dt})
                else:
                    ns += 1
                    sell_remaining = qty
                    cost_basis = 0.0
                    while sell_remaining > 1e-9 and buy_queue:
                        oldest = buy_queue[0]
                        if oldest['qty'] <= sell_remaining + 1e-9:
                            cost_basis += oldest['qty'] * oldest['price']
                            sell_remaining -= oldest['qty']
                            buy_queue.pop(0)
                        else:
                            cost_basis += sell_remaining * oldest['price']
                            oldest['qty'] -= sell_remaining
                            sell_remaining = 0
                    realized_gross += cost - cost_basis
            
            net = realized_gross - fees_total
            rem_qty = sum(b['qty'] for b in buy_queue)
            rem_cost = sum(b['qty'] * b['price'] for b in buy_queue)
            
            # Find current price for this pair
            cp = 0
            for tkey in prices:
                if pair in tkey or pair.replace('USD', 'ZUSD') in tkey:
                    cp = prices[tkey]
                    break
            rem_val = rem_qty * cp
            unrealized = rem_val - rem_cost
            
            sym_result = FIFOSymbolResult(
                symbol=pair, exchange='kraken',
                total_buys=nb, total_sells=ns,
                total_volume=vol, realized_gross=realized_gross,
                total_fees=fees_total, net_realized=net,
                remaining_qty=rem_qty, remaining_value=rem_val,
                unrealized_pnl=unrealized, trade_count=len(trades)
            )
            if buy_queue:
                sym_result.oldest_lot_date = buy_queue[0]['date']
                sym_result.oldest_lot_price = buy_queue[0]['price']
            
            first_dt = datetime.utcfromtimestamp(float(trades[0]['time'])).strftime('%Y-%m-%d %H:%M:%S')
            last_dt = datetime.utcfromtimestamp(float(trades[-1]['time'])).strftime('%Y-%m-%d %H:%M:%S')
            sym_result.first_trade = first_dt
            sym_result.last_trade = last_dt
            
            result.symbols.append(sym_result)
            result.total_buys += nb
            result.total_sells += ns
            result.total_volume += vol
            result.total_fees += fees_total
            result.realized_pnl += net
            result.unrealized_pnl += unrealized
            
            if verbose and (nb + ns) > 0:
                tag = '  PROFIT' if net > 0.01 else '  LOSS' if net < -0.01 else '  FLAT'
                print(f"    {pair:>15}: {nb:>4}B {ns:>4}S  realized ${net:>+9.2f}{tag}  "
                      f"holding {rem_qty:.4f}=${rem_val:.2f}  unrealized ${unrealized:>+8.2f}")
        
        result.combined_pnl = result.realized_pnl + result.unrealized_pnl
        
        # 3. Ledger: deposits & withdrawals
        time.sleep(3)
        tb = self._kraken_private('TradeBalance', {'asset': 'ZUSD'})
        if not tb.get('error'):
            result.current_balance_usd = float(tb['result'].get('eb', 0))
        
        for ltype in ['deposit', 'withdrawal']:
            offset = 0
            while True:
                time.sleep(3)
                resp = self._kraken_private('Ledgers', {'type': ltype, 'ofs': offset})
                if resp.get('error'):
                    if any('nonce' in str(e).lower() for e in resp['error']):
                        time.sleep(3)
                        continue
                    if any('rate' in str(e).lower() for e in resp['error']):
                        time.sleep(10)
                        continue
                    break
                ledger = resp.get('result', {}).get('ledger', {})
                if not ledger:
                    break
            for _, entry in ledger.items():
                amount = abs(float(entry['amount']))
                asset = entry['asset']
                # Approximate USD value at current rate
                if asset in ('ZUSD', 'USD'):
                    usd_val = amount
                elif asset in ('USDC', 'USDT'):
                    usd_val = amount
                elif asset == 'ZGBP':
                    usd_val = amount * 1.35
                elif asset == 'ZEUR':
                    usd_val = amount * 1.18
                elif asset == 'XXBT':
                    usd_val = amount * prices.get('XXBTZUSD', 64000)
                elif asset == 'XETH':
                    usd_val = amount * prices.get('XETHZUSD', 1800)
                else:
                    usd_val = 0
                
                if ltype == 'deposit':
                    result.deposits_usd += usd_val
                else:
                    result.withdrawals_usd += usd_val
                
                count = resp.get('result', {}).get('count', 0)
                offset += len(ledger)
                if offset >= count:
                    break
        
        result.ledger_net_pnl = result.current_balance_usd + result.withdrawals_usd - result.deposits_usd
        
        if verbose:
            self._print_exchange_summary(result)
        
        return result
    
    def _print_exchange_summary(self, result: ForensicAuditResult):
        """Print formatted summary for an exchange."""
        print(f"\n  {'=' * 60}")
        print(f"  {result.exchange.upper()} — GRAND TOTALS")
        print(f"  {'=' * 60}")
        print(f"  Trades:          {result.total_buys}B + {result.total_sells}S = {result.total_buys + result.total_sells}")
        print(f"  Volume:          ${result.total_volume:,.2f}")
        print(f"  Fees:            ${result.total_fees:,.4f}")
        print(f"  REALIZED (net):  ${result.realized_pnl:>+,.4f}")
        print(f"  UNREALIZED:      ${result.unrealized_pnl:>+,.4f}")
        print(f"  COMBINED:        ${result.combined_pnl:>+,.4f}")
        print(f"  {'─' * 60}")
        print(f"  Deposited:       ${result.deposits_usd:>,.2f}")
        print(f"  Withdrawn:       ${result.withdrawals_usd:>,.2f}")
        print(f"  Current balance: ${result.current_balance_usd:>,.2f}")
        print(f"  LEDGER NET P&L:  ${result.ledger_net_pnl:>+,.2f}")
        print(f"  {'=' * 60}")
    
    def run_full_forensic_audit(self, verbose=True) -> Dict[str, ForensicAuditResult]:
        """
        Run FIFO forensic audit on all exchanges.
        Returns dict of exchange name -> ForensicAuditResult.
        """
        print("\n" + "=" * 90)
        print("  THE KING'S FORENSIC AUDIT — FIFO COST BASIS")
        print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("  No smoke. Math and API only.")
        print("=" * 90)
        
        results = {}
        
        results['binance'] = self.audit_binance(verbose=verbose)
        results['kraken'] = self.audit_kraken(verbose=verbose)
        
        # Combined summary
        total_realized = sum(r.realized_pnl for r in results.values())
        total_unrealized = sum(r.unrealized_pnl for r in results.values())
        total_deposited = sum(r.deposits_usd for r in results.values())
        total_withdrawn = sum(r.withdrawals_usd for r in results.values())
        total_current = sum(r.current_balance_usd for r in results.values())
        total_trades = sum(r.total_buys + r.total_sells for r in results.values())
        total_volume = sum(r.total_volume for r in results.values())
        total_fees = sum(r.total_fees for r in results.values())
        
        if verbose:
            print(f"\n  {'=' * 90}")
            print(f"  COMBINED — ALL EXCHANGES")
            print(f"  {'=' * 90}")
            print(f"  Total trades:     {total_trades}")
            print(f"  Total volume:     ${total_volume:,.2f}")
            print(f"  Total fees:       ${total_fees:,.2f}")
            print(f"  FIFO Realized:    ${total_realized:>+,.2f}")
            print(f"  FIFO Unrealized:  ${total_unrealized:>+,.2f}")
            print(f"  FIFO Combined:    ${total_realized + total_unrealized:>+,.2f}")
            print(f"  {'─' * 90}")
            print(f"  Total deposited:  ${total_deposited:>,.2f}")
            print(f"  Total withdrawn:  ${total_withdrawn:>,.2f}")
            print(f"  Current balance:  ${total_current:>,.2f}")
            print(f"  LEDGER NET P&L:   ${total_current + total_withdrawn - total_deposited:>+,.2f}")
            print(f"  {'=' * 90}")
            
            # Top winners and losers
            all_syms = []
            for r in results.values():
                all_syms.extend(r.symbols)
            
            by_realized = sorted(all_syms, key=lambda s: s.net_realized, reverse=True)
            
            print(f"\n  TOP WINNERS (by realized P&L):")
            for s in by_realized[:5]:
                if s.net_realized > 0:
                    print(f"    {s.symbol:>15} ({s.exchange}): ${s.net_realized:>+,.2f}  "
                          f"({s.total_buys}B/{s.total_sells}S)")
            
            print(f"\n  TOP LOSERS (by realized P&L):")
            for s in by_realized[-5:]:
                if s.net_realized < 0:
                    print(f"    {s.symbol:>15} ({s.exchange}): ${s.net_realized:>+,.2f}  "
                          f"({s.total_buys}B/{s.total_sells}S)")
            
            print(f"\n  {'=' * 90}")
        
        # Save result to JSON for persistence
        audit_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'method': 'FIFO cost basis + ledger cross-verification',
            'exchanges': {}
        }
        for exch, r in results.items():
            audit_data['exchanges'][exch] = {
                'total_buys': r.total_buys,
                'total_sells': r.total_sells,
                'total_volume': round(r.total_volume, 2),
                'total_fees': round(r.total_fees, 4),
                'realized_pnl': round(r.realized_pnl, 4),
                'unrealized_pnl': round(r.unrealized_pnl, 4),
                'combined_pnl': round(r.combined_pnl, 4),
                'deposits_usd': round(r.deposits_usd, 2),
                'withdrawals_usd': round(r.withdrawals_usd, 2),
                'current_balance_usd': round(r.current_balance_usd, 2),
                'ledger_net_pnl': round(r.ledger_net_pnl, 2),
                'symbols': [
                    {
                        'symbol': s.symbol,
                        'buys': s.total_buys,
                        'sells': s.total_sells,
                        'volume': round(s.total_volume, 2),
                        'realized': round(s.net_realized, 4),
                        'unrealized': round(s.unrealized_pnl, 4),
                        'holding_qty': round(s.remaining_qty, 6),
                        'holding_value': round(s.remaining_value, 2),
                        'first_trade': s.first_trade,
                        'last_trade': s.last_trade,
                    }
                    for s in r.symbols
                ]
            }
        
        # Atomic write
        audit_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'forensic_audit_result.json')
        tmp_path = audit_path + '.tmp'
        with open(tmp_path, 'w') as f:
            json.dump(audit_data, f, indent=2)
        os.replace(tmp_path, audit_path)
        
        if verbose:
            print(f"\n  Audit saved to: forensic_audit_result.json")
        
        return results


def main():
    """Run the intelligence audit or forensic audit."""
    import sys
    
    if '--forensic' in sys.argv or '--fifo' in sys.argv or '--audit' in sys.argv:
        # Run the FIFO forensic audit
        auditor = FIFOForensicAuditor()
        auditor.run_full_forensic_audit(verbose=True)
    else:
        # Run the standard intelligence audit
        audit = AureonExchangeIntelligenceAudit()
        audit.run_full_audit()


if __name__ == '__main__':
    main()
