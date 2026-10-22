#!/usr/bin/env python3
"""
Multi-Account WebSocket Simulation

Runs N simulated accounts (30 by default), 50 trades per account,
driven by live Binance WebSocket ticker updates. No real orders
are placed; balances and fills are simulated using last price and
exchange filters (LOT_SIZE/NOTIONAL) from REST.

Env:
- SIM_ACCOUNTS_FILE: path to accounts.json (default: accounts.json)
- SIM_SYMBOLS: comma list of symbols (default: BNBBTC,ETHBTC)
- SIM_TRADES_PER_ACCOUNT: default 50
- SIM_ACCOUNTS: default 30 (only used when accounts.json missing)
- BINANCE_TESTNET: true/false for endpoints

Outputs:
- metrics/sim/acc_<index>.jsonl per account trade log
- metrics/sim_summary.json aggregated results
"""
import os
import json
import time
import hmac
import math
import queue
import hashlib
import random
import threading
from datetime import datetime, timezone

import requests
try:
    import websocket
except ImportError:
    raise SystemExit("Missing dependency 'websocket-client'. Install: pip install websocket-client")


TESTNET = os.getenv('BINANCE_TESTNET', 'false').lower() == 'true'
HTTP_BASE = "https://testnet.binance.vision/api" if TESTNET else "https://api.binance.com/api"
WS_BASE = "wss://stream.testnet.binance.vision/stream" if TESTNET else "wss://stream.binance.com:9443/stream"

ACCOUNTS_FILE = os.getenv('SIM_ACCOUNTS_FILE', 'accounts.json')
DEFAULT_SYMBOLS = [s.strip().upper() for s in os.getenv('SIM_SYMBOLS', 'BNBBTC,ETHBTC').split(',') if s.strip()]
TRADES_PER_ACCOUNT = int(os.getenv('SIM_TRADES_PER_ACCOUNT', '50'))
N_ACCOUNTS = int(os.getenv('SIM_ACCOUNTS', '30'))


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def get_exchange_rules(symbol: str):
    try:
        r = requests.get(f"{HTTP_BASE}/v3/exchangeInfo", params={'symbol': symbol}, timeout=10)
        r.raise_for_status()
        info = r.json()
        for s in info.get('symbols', []):
            if s.get('symbol') == symbol:
                base = s.get('baseAsset')
                quote = s.get('quoteAsset')
                min_qty = step = min_notional = 0.0
                for f in s.get('filters', []):
                    if f.get('filterType') == 'LOT_SIZE':
                        min_qty = float(f.get('minQty', '0'))
                        step = float(f.get('stepSize', '0'))
                    if f.get('filterType') in ('MIN_NOTIONAL','NOTIONAL'):
                        min_notional = float(f.get('minNotional', '0'))
                return {'base': base, 'quote': quote, 'minQty': min_qty, 'stepSize': step, 'minNotional': min_notional}
    except Exception:
        pass
    return {'base': None, 'quote': None, 'minQty': 0.0, 'stepSize': 0.0, 'minNotional': 0.0}


def floor_to_step(qty: float, step: float) -> float:
    if step <= 0:
        return qty
    return math.floor(qty / step) * step


class SimAccount:
    def __init__(self, idx: int, symbols):
        self.idx = idx
        self.symbols = symbols
        # Initialize small balances diversified
        self.bal = {'BTC': 0.001, 'BNB': 0.05, 'ETH': 0.002}
        self.equity_usdt = 0.0
        self.wins = 0
        self.losses = 0
        self.trades = 0
        self.log_path = os.path.join('metrics','sim',f'acc_{idx:02d}.jsonl')
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def value_btc(self, px):
        total = self.bal.get('BTC', 0.0)
        if self.bal.get('BNB',0)>0 and 'BNBBTC' in px:
            total += self.bal['BNB'] * px['BNBBTC']
        if self.bal.get('ETH',0)>0 and 'ETHBTC' in px:
            total += self.bal['ETH'] * px['ETHBTC']
        return total

    def value_usdt(self, px):
        if 'BTCUSDT' not in px:
            return 0.0
        return self.value_btc(px) * px['BTCUSDT']

    def decide(self, symbol, px):
        # Simple policy: if BTC low, SELL base to build BTC; otherwise random
        if self.bal.get('BTC',0) < 0.0006:
            return 'SELL'
        return random.choices(['BUY','SELL','HOLD'], [0.4,0.4,0.2])[0]

    def trade_once(self, symbol, px, rules, pos_pct=0.3):
        if symbol not in px:
            return False
        price = px[symbol]
        if price <= 0:
            return False
        side = self.decide(symbol, px)
        if side == 'HOLD':
            return False
        base = rules['base']; quote = rules['quote']
        if not base or not quote:
            return False
        spend_asset = quote if side=='BUY' else base
        avail = self.bal.get(spend_asset, 0.0)
        if avail <= 0:
            return False
        spend_amt = avail * pos_pct
        qty = spend_amt/price if side=='BUY' else spend_amt
        qty = max(qty, rules['minQty'])
        qty = floor_to_step(qty, rules['stepSize']) if rules['stepSize'] else qty
        if qty <= 0:
            return False
        notional = qty*price
        if rules['minNotional'] and notional < rules['minNotional']:
            need_qty = rules['minNotional']/price
            qty2 = floor_to_step(max(need_qty, rules['minQty']), rules['stepSize'])
            if qty2*price < rules['minNotional']:
                return False
            qty = qty2

        # Apply fill: update balances
        before = self.value_usdt(px)
        if side=='BUY':
            cost = qty*price
            if self.bal.get(quote,0) < cost:
                return False
            self.bal[quote] = self.bal.get(quote,0) - cost
            self.bal[base] = self.bal.get(base,0) + qty
        else:
            if self.bal.get(base,0) < qty:
                return False
            self.bal[base] = self.bal.get(base,0) - qty
            self.bal[quote] = self.bal.get(quote,0) + qty*price

        after = self.value_usdt(px)
        pnl = after - before
        self.trades += 1
        if pnl >= 0:
            self.wins += 1
        else:
            self.losses += 1
        with open(self.log_path,'a') as f:
            f.write(json.dumps({
                'ts': now_iso(), 'i': self.idx, 'symbol': symbol, 'side': side,
                'qty': qty, 'price': price, 'pnl': pnl,
                'wins': self.wins, 'losses': self.losses,
                'bal': self.bal
            })+"\n")
        return True


def combined_stream_url(symbols):
    streams = '/'.join([f"{s.lower()}@ticker" for s in symbols])
    return f"{WS_BASE}?streams={streams}"


def simulate():
    # Prepare accounts list
    accounts = []
    if os.path.exists(ACCOUNTS_FILE):
        try:
            data = json.load(open(ACCOUNTS_FILE))
            # Use length of provided accounts but simulate balances locally
            accounts = [SimAccount(i, DEFAULT_SYMBOLS) for i,_ in enumerate(data[:N_ACCOUNTS], start=1)]
        except Exception:
            accounts = [SimAccount(i, DEFAULT_SYMBOLS) for i in range(1, N_ACCOUNTS+1)]
    else:
        accounts = [SimAccount(i, DEFAULT_SYMBOLS) for i in range(1, N_ACCOUNTS+1)]

    # Symbol rules cache
    rules = {sym: get_exchange_rules(sym) for sym in DEFAULT_SYMBOLS}
    # Also need BTCUSDT for valuation
    rules['BTCUSDT'] = get_exchange_rules('BTCUSDT')

    # Shared price map
    prices = {s: 0.0 for s in DEFAULT_SYMBOLS}
    prices['BTCUSDT'] = 0.0

    # REST seed for BTCUSDT
    try:
        r = requests.get(f"{HTTP_BASE}/v3/ticker/price", params={'symbol':'BTCUSDT'}, timeout=5)
        if r.status_code == 200:
            prices['BTCUSDT'] = float(r.json()['price'])
    except Exception:
        pass

    # Trade queues to pace accounts
    next_time = {acc.idx: 0.0 for acc in accounts}
    cooldown = 2.0  # seconds between trades per account in sim

    # WebSocket handling
    url = combined_stream_url(DEFAULT_SYMBOLS + ['BTCUSDT'])
    qmsg = queue.Queue()

    def on_message(ws, message):
        try:
            data = json.loads(message)
            payload = data.get('data', {})
            s = payload.get('s')  # symbol
            p = payload.get('c') or payload.get('p')  # last price or close price
            if s and p:
                prices[s] = float(p)
            qmsg.put(1)
        except Exception:
            pass

    def on_error(ws, error):
        print(f"WS error: {error}")

    def on_close(ws, close_status_code, close_msg):
        print("WS closed")

    ws = websocket.WebSocketApp(url, on_message=on_message, on_error=on_error, on_close=on_close)
    t = threading.Thread(target=ws.run_forever, kwargs={'ping_interval':20, 'ping_timeout':10}, daemon=True)
    t.start()

    print(f"🚀 SIM starting: {len(accounts)} accounts, {TRADES_PER_ACCOUNT} trades each; symbols: {','.join(DEFAULT_SYMBOLS)}")
    start = time.time()

    try:
        while True:
            # Ensure we process on incoming ticks or every 0.5s
            try:
                qmsg.get(timeout=0.5)
            except queue.Empty:
                pass

            now = time.time()
            all_done = True
            for acc in accounts:
                if acc.trades >= TRADES_PER_ACCOUNT:
                    continue
                all_done = False
                if now >= next_time[acc.idx]:
                    # pick first symbol with price
                    sym = None
                    for s in acc.symbols:
                        if prices.get(s,0)>0:
                            sym = s; break
                    if not sym:
                        continue
                    ok = acc.trade_once(sym, prices, rules[sym])
                    next_time[acc.idx] = now + cooldown
            if all_done:
                break
    finally:
        try:
            ws.close()
        except Exception:
            pass

    # Summarize
    summary = []
    for acc in accounts:
        eq = acc.value_usdt(prices)
        summary.append({'i': acc.idx, 'wins': acc.wins, 'losses': acc.losses, 'trades': acc.trades, 'equityUSDT': eq})
    os.makedirs('metrics', exist_ok=True)
    with open(os.path.join('metrics','sim_summary.json'),'w') as f:
        json.dump({'updatedAt': now_iso(), 'accounts': summary}, f, indent=2)
    print(f"✅ SIM complete in {time.time()-start:.1f}s. Summary -> metrics/sim_summary.json")


if __name__ == '__main__':
    simulate()
